#!/usr/bin/env python3
"""HF block (GPU): bf16 Qwen/Qwen3-8B, then bf16 Qwen/Qwen3-8B-Base.

  E2  fresh-pool states (layers L1-L3 at R, k16, k_pre, k_post and the mean over generated tokens 0..c) and the
      attention rows of the k_pre / k_post queries (36 layers x 32 heads), under the ban prompt and its mention and
      neutral twins with the SAME teacher-forced continuation gen[:max(c+1, 17)]; prompt-only passes of the
      ban / mention / neutral / substitute-mention prompts (segment tokens, name tokens, R).
  E1  SAE transfer test: CE over response tokens clean vs with the block-L output (positions >= 1) replaced by the
      SAE reconstruction, for the instruct and the base model (Kissane-style ratio dCE_inst / dCE_base <= 1.5), FVU,
      relative MSE, high-norm share, and the per-token top-50 codes of the instruct corpus (context corpus).
  E4  J-lens gate (top-1 agreement with the model's own next token vs the logit lens) and application at R, k_pre,
      k_post (J-lens and logit lens on the same states).

The 16 GB GPU cannot hold the 16.4 GB checkpoint: embed_tokens stays on the CPU (a gather) and the forward pass is
fed inputs_embeds; every other weight is on the GPU. The SAE of one layer at a time is on the GPU in bf16
(bf16 matmul, top-k on fp32 pre-activations). Attention rows come from a wrapper around the SDPA kernel that
recomputes softmax(q k^T / sqrt(d)) in fp32 for the two query positions only (checked against eager attention).
"""

from __future__ import annotations

import os

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import gc
import json
import time
from typing import Any, Callable

import numpy as np
import torch
from loguru import logger

from core import (EXP1, JLENS_REPO, MODEL_BASE, MODEL_HF, RESULTS, SAE_K, SAE_REPO, TASKS, TEMPLATE_IDS, TENSORS,
                  Timer, add_deviation, read_json, read_jsonl, write_json)

DEV = "cuda"
RAW = RESULTS / "raw"
JL_LAYERS = [9, 18, 21, 22, 23, 24, 25, 26, 27]
POS_KEYS = ["R", "k16", "k_pre", "k_post", "meangen"]
CONDS = ["ban", "mention", "neutral"]
REGIONS = ["segment", "name", "spec", "template", "sink", "generated"]
SEG_MAX = 24
LENS_TOKENS = [" BFS", " DFS", " Dijkstra", " Bellman", " SPFA", " A", " heuristic", " deque", " popleft",
               " heapq", " stack", " queue", " recursion", " visited"]
ATT: dict[str, Any] = {"q": None, "rows": {}}
SFX = {"s": ""}  # "_smoke" in smoke mode: every tensor / json of the smoke run goes to separate files
_ORIG_SDPA: Callable | None = None


def sae_layers() -> list[int]:
    return list(read_json(RESULTS / "layer_probe.json")["choice"]["chosen"])


# ---------------------------------------------------------------- model + hooks
def install_attention_capture() -> None:
    """Wrap the SDPA attention function: outputs unchanged; when ATT['q'] holds query positions, also store the fp32
    attention probabilities of those queries per layer (heads x n_query x keys)."""
    global _ORIG_SDPA
    from transformers.integrations.sdpa_attention import sdpa_attention_forward
    from transformers.modeling_utils import ALL_ATTENTION_FUNCTIONS

    _ORIG_SDPA = sdpa_attention_forward

    def capture_sdpa(module, query, key, value, attention_mask, **kwargs):  # noqa: ANN001
        out = _ORIG_SDPA(module, query, key, value, attention_mask, **kwargs)
        qp = ATT["q"]
        if qp is not None:
            nrep = query.shape[1] // key.shape[1]
            k = key[0].repeat_interleave(nrep, dim=0).float()          # (Hq, S, D), repeat_kv ordering
            q = query[0, :, qp, :].float()                              # (Hq, nq, D)
            scale = kwargs.get("scaling") or module.scaling
            sc = torch.einsum("hqd,hkd->hqk", q, k) * scale
            kpos = torch.arange(k.shape[1], device=q.device)
            qpos = torch.tensor(qp, device=q.device)
            sc = sc.masked_fill(kpos[None, None, :] > qpos[None, :, None], float("-inf"))
            ATT["rows"][module.layer_idx] = sc.softmax(-1)
        return out

    ALL_ATTENTION_FUNCTIONS["sdpa"] = capture_sdpa


def load_model(name: str):
    from transformers import AutoModelForCausalLM

    t0 = time.time()
    # no accelerate dispatch (its hook would copy the CPU embedding to the GPU on every call): load on the CPU,
    # then move everything except embed_tokens to the GPU by hand
    model = AutoModelForCausalLM.from_pretrained(name, dtype=torch.bfloat16, low_cpu_mem_usage=True,
                                                 attn_implementation="sdpa")
    model.eval()
    if model.config.tie_word_embeddings:
        raise RuntimeError("tied embeddings: the CPU-embedding layout assumes an untied lm_head")
    for mod in (model.model.layers, model.model.norm, model.model.rotary_emb, model.lm_head):
        mod.to(DEV)
    gc.collect()
    torch.cuda.empty_cache()
    logger.info(f"loaded {name} in {time.time() - t0:.0f}s; GPU allocated {torch.cuda.memory_allocated() / 2**30:.2f} "
                f"GiB, reserved {torch.cuda.memory_reserved() / 2**30:.2f} GiB")
    return model


@torch.no_grad()
def forward(model, ids: list[int]) -> torch.Tensor:
    """Final (normed) hidden states (1, S, 4096) on the GPU."""
    x = torch.tensor([ids], dtype=torch.long)
    emb = model.model.embed_tokens(x).to(DEV)
    return model.model(inputs_embeds=emb, use_cache=False).last_hidden_state


def _h(out: Any) -> torch.Tensor:
    return out[0] if isinstance(out, tuple) else out


def _replace(out: Any, new: torch.Tensor) -> Any:
    return (new,) + tuple(out[1:]) if isinstance(out, tuple) else new


class Hooks:
    def __init__(self) -> None:
        self.handles: list[Any] = []

    def add(self, module, fn) -> None:  # noqa: ANN001
        self.handles.append(module.register_forward_hook(fn))

    def clear(self) -> None:
        for h in self.handles:
            h.remove()
        self.handles = []


def cap_hook(store: dict, key: Any, pos: list[int] | None = None, mean_range: tuple[int, int] | None = None,
             full_dtype: torch.dtype = torch.bfloat16) -> Callable:
    def f(mod, inp, out):  # noqa: ANN001
        h = _h(out)[0]
        if pos is None:
            store[key] = h.detach().to("cpu", dtype=full_dtype)
        else:
            store[key] = h[pos].detach().float().cpu()
            if mean_range is not None:
                a, b = mean_range
                store[(key, "mean")] = h[a:b].float().mean(0).cpu()
    return f


@torch.no_grad()
def token_ce(model, hfin: torch.Tensor, ids: list[int], start: int, chunk: int = 128) -> np.ndarray:
    """Per-token CE of ids[start+1:] predicted from positions start..S-2."""
    out = []
    S = len(ids)
    for a in range(start, S - 1, chunk):
        b = min(a + chunk, S - 1)
        lg = model.lm_head(hfin[0, a:b]).float()
        tg = torch.tensor(ids[a + 1:b + 1], device=lg.device)
        out.append(torch.nn.functional.cross_entropy(lg, tg, reduction="none"))
    return torch.cat(out).cpu().numpy()


class SAE:
    """Qwen-Scope TopK SAE (model-card math: pre = h W_enc^T + b_enc, keep top-50, recon = z W_dec^T + b_dec)."""

    def __init__(self, L: int) -> None:
        from huggingface_hub import hf_hub_download

        d = torch.load(hf_hub_download(SAE_REPO, f"layer{L}.sae.pt"), map_location="cpu", weights_only=True,
                       mmap=True)
        self.L = L
        self.W_enc = d["W_enc"].to(DEV, torch.bfloat16)
        self.b_enc = d["b_enc"].to(DEV, torch.float32)
        self.W_dec = d["W_dec"].to(DEV, torch.bfloat16)
        self.b_dec = d["b_dec"].to(DEV, torch.float32)
        del d
        gc.collect()

    @torch.no_grad()
    def encode(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        pre = torch.nn.functional.linear(x.to(torch.bfloat16), self.W_enc).float() + self.b_enc
        return pre.topk(SAE_K, dim=-1)

    @torch.no_grad()
    def decode(self, v: torch.Tensor, i: torch.Tensor) -> torch.Tensor:
        z = torch.zeros(v.shape[0], self.W_enc.shape[0], device=DEV, dtype=torch.bfloat16)
        z.scatter_(1, i, v.to(torch.bfloat16))
        return torch.nn.functional.linear(z, self.W_dec).float() + self.b_dec

    @torch.no_grad()
    def recon(self, x: torch.Tensor, chunk: int = 128) -> torch.Tensor:
        out = []
        for a in range(0, x.shape[0], chunk):
            v, i = self.encode(x[a:a + chunk])
            out.append(self.decode(v, i))
        return torch.cat(out)

    def free(self) -> None:
        del self.W_enc, self.W_dec, self.b_enc, self.b_dec
        gc.collect()
        torch.cuda.empty_cache()


def splice_hook(fn: Callable[[torch.Tensor], torch.Tensor]) -> Callable:
    """Replace the block output at positions >= 1 (position 0 = '<|im_start|>' attention sink is kept)."""
    def f(mod, inp, out):  # noqa: ANN001
        h = _h(out)
        r = fn(h[0, 1:]).to(h.dtype)
        return _replace(out, torch.cat([h[:, :1], r.unsqueeze(0)], dim=1))
    return f


# ---------------------------------------------------------------- inputs
def transfer_corpus(tok) -> list[dict[str, Any]]:  # noqa: ANN001
    """200 exp1 sequences (random_state 0): 50 t1 baseline, 50 t1 ban:bfs, 50 t2 baseline, 50 t2 ban:dijkstra;
    chat prompt (thinking off) + ```python code``` + <|im_end|>."""
    rows = read_jsonl(EXP1 / "data" / "samples.jsonl")
    cond = json.loads((EXP1 / "prompts" / "conditions.json").read_text())
    im_end = tok.convert_tokens_to_ids("<|im_end|>")
    rng = np.random.default_rng(0)
    out = []
    for t, c in (("t1", "baseline"), ("t1", "ban:bfs"), ("t2", "baseline"), ("t2", "ban:dijkstra")):
        cand = [r for r in rows if r["task"] == t and r["condition"] == c and r.get("code")]
        for j in sorted(rng.choice(len(cand), 50, replace=False).tolist()):
            r = cand[j]
            prompt = [p for p in cond["tasks"][t]["conditions"][c]
                      if int(p["paraphrase_id"]) == int(r["paraphrase_id"])][0]["prompt"]
            p_ids = list(tok.apply_chat_template([{"role": "user", "content": prompt}], tokenize=True,
                                                 add_generation_prompt=True, enable_thinking=False))
            resp = tok("```python\n" + r["code"].strip("\n") + "\n```", add_special_tokens=False)["input_ids"]
            out.append({"task": t, "condition": c, "paraphrase_id": r["paraphrase_id"], "sample_id": r["sample_id"],
                        "ids": p_ids + list(resp) + [im_end], "start": len(p_ids) - 1})
    return out


def lens_token_ids(tok) -> dict[str, int]:  # noqa: ANN001
    return {s: tok(s, add_special_tokens=False)["input_ids"][0] for s in LENS_TOKENS}


def load_jlens() -> dict[int, torch.Tensor]:
    from huggingface_hub import hf_hub_download

    d = torch.load(hf_hub_download(JLENS_REPO, "Qwen3-8B/lens.pt"), map_location="cpu", weights_only=False,
                   mmap=True)
    J = {int(k): (v if torch.is_tensor(v) else torch.as_tensor(v)) for k, v in d["J"].items()}
    return J


# ---------------------------------------------------------------- E2
def region_index(spans: dict[str, list[int]], plen: int, S: int) -> dict[str, list[int]]:
    tmpl = [i for i in spans.get("template", []) if i != 0]
    return {"segment": spans.get("segment", []), "name": spans.get("name", []), "spec": spans.get("spec", []),
            "template": tmpl, "sink": [0], "generated": list(range(plen, S))}


@torch.no_grad()
def run_e2(model, tok, P: dict[str, Any], layers: list[int], limit: int | None = None) -> None:  # noqa: ANN001
    from labelling import commitment

    pool = sorted(read_jsonl(RAW / "c1_fresh_pool.jsonl"), key=lambda r: (r["task"], r["template"], r["sample_id"]))
    if limit:
        pool = pool[:limit // 2] + pool[-(limit - limit // 2):]
    n = len(pool)
    nL = len(layers)
    st = np.full((n, len(CONDS), len(POS_KEYS), nL, 4096), np.nan, dtype=np.float16)
    mass = np.full((n, len(CONDS), 2, 36, 32, len(REGIONS)), np.nan, dtype=np.float32)
    segtok = np.full((n, len(CONDS), 36, 32, SEG_MAX), np.nan, dtype=np.float16)
    jl_states = {L: np.full((n, 3, 4096), np.nan, dtype=np.float32) for L in JL_LAYERS}  # ban: R, k_pre, k_post
    meta = []
    argmax_ok = []
    t0 = time.time()
    for i, r in enumerate(pool):
        c_info = commitment(r["task"], r["gen_token_ids"], r["text"])
        c = c_info["commit_idx"]
        gen = r["gen_token_ids"]
        n_keep = max((c + 1) if c is not None else 0, 17)
        m = {"i": i, "task": r["task"], "template": r["template"], "sample_id": r["sample_id"], "seed": r["seed"],
             "commit_idx": c, "evidence_term": c_info.get("evidence_term"), "n_keep": min(n_keep, len(gen)),
             "plen": {}}
        for ci, cond in enumerate(CONDS):
            key = f"{r['task']}|{cond}|{r['template']}"
            pr = P["prompts"][key]["nothink"]
            p_ids = pr["ids"]
            ids = p_ids + gen[:n_keep]
            S = len(ids)
            pl = len(p_ids)
            m["plen"][cond] = pl
            pos = {"R": pl - 1, "k16": min(pl - 1 + 16, S - 1)}
            if c is not None and pl + c < S:
                pos["k_pre"], pos["k_post"] = pl - 1 + c, pl + c
            plist = [pos.get(k, pos["R"]) for k in POS_KEYS[:4]]
            store: dict[Any, torch.Tensor] = {}
            H = Hooks()
            mr = (pl - 1, pl + c) if c is not None else None
            for L in layers:
                H.add(model.model.layers[L], cap_hook(store, L, plist, mr))
            if cond == "ban":
                for L in JL_LAYERS:
                    if L not in layers:
                        H.add(model.model.layers[L], cap_hook(store, ("jl", L), plist))
            ATT["q"] = [pos["k_pre"], pos["k_post"]] if "k_pre" in pos else None
            ATT["rows"] = {}
            hfin = forward(model, ids)
            H.clear()
            for li, L in enumerate(layers):
                v = store[L].numpy()
                for pj, k in enumerate(POS_KEYS[:4]):
                    if k in pos:
                        st[i, ci, pj, li] = v[pj]
                if (L, "mean") in store:
                    st[i, ci, 4, li] = store[(L, "mean")].numpy()
            if cond == "ban":
                for L in JL_LAYERS:
                    v = (store[L] if L in layers else store[("jl", L)]).numpy()
                    jl_states[L][i, 0] = v[0]
                    if "k_pre" in pos:
                        jl_states[L][i, 1] = v[2]
                        jl_states[L][i, 2] = v[3]
                if "k_pre" in pos:
                    argmax_ok.append(int(model.lm_head(hfin[0, pos["k_pre"]]).argmax().item() == gen[c]))
            if ATT["rows"]:
                reg = region_index(pr["spans"], pl, S)
                segpos = pr["spans"].get("segment", [])[:SEG_MAX]
                for L, pr_rows in ATT["rows"].items():
                    for ri, rn in enumerate(REGIONS):
                        idx = reg[rn]
                        if idx:
                            mass[i, ci, :, L, :, ri] = pr_rows[:, :, idx].sum(-1).T.cpu().numpy()
                        else:
                            mass[i, ci, :, L, :, ri] = 0.0
                    if segpos:
                        segtok[i, ci, L, :, :len(segpos)] = pr_rows[:, 0, segpos].cpu().numpy()
                if i < 3 and ci == 0:
                    tot = torch.stack([v.sum(-1) for v in ATT["rows"].values()])
                    logger.info(f"attention rows sum: min {tot.min().item():.5f} max {tot.max().item():.5f}")
            ATT["q"] = None
            ATT["rows"] = {}
        meta.append(m)
        if i == 9:
            dt = time.time() - t0
            logger.info(f"E2: 10 runs x 3 conditions in {dt:.1f}s -> extrapolated {dt / 10 * n / 60:.1f} min for {n}")
    np.savez_compressed(TENSORS / f"e2_states{SFX['s']}.npz", states=st, layers=np.array(layers), pos_keys=np.array(POS_KEYS),
                        conds=np.array(CONDS))
    np.savez_compressed(TENSORS / f"e2_attention{SFX['s']}.npz", mass=mass, segtok=segtok, regions=np.array(REGIONS))
    np.savez_compressed(TENSORS / f"e2_jlens_states{SFX['s']}.npz", **{f"L{L}": v.astype(np.float16) for L, v in jl_states.items()})
    write_json(RESULTS / f"e2_meta{SFX['s']}.json", {"runs": meta, "argmax_at_k_pre_equals_gen_c": float(np.mean(argmax_ok))
                                          if argmax_ok else None, "n_argmax": len(argmax_ok),
                                          "layers": layers, "pos_keys": POS_KEYS, "conds": CONDS})
    logger.info(f"E2 done: {n} runs; argmax(k_pre)==gen[c] rate {np.mean(argmax_ok) if argmax_ok else None}")


@torch.no_grad()
def run_prompt_only(model, P: dict[str, Any], layers: list[int]) -> None:  # noqa: ANN001
    """Prompt-only passes: residuals at every condition-segment token and at R (L1-L3), plus J-lens layers at R."""
    out: dict[str, np.ndarray] = {}
    meta = {}
    for t in TASKS:
        for w in TEMPLATE_IDS:
            for cond in ("ban", "mention", "neutral", "submention"):
                key = f"{t}|{cond}|{w}"
                pr = P["prompts"][key]["nothink"]
                ids = pr["ids"]
                seg = pr["spans"].get("segment", [])
                plist = seg + [len(ids) - 1]
                store: dict[Any, torch.Tensor] = {}
                H = Hooks()
                for L in sorted(set(layers) | set(JL_LAYERS)):
                    H.add(model.model.layers[L], cap_hook(store, L, plist))
                forward(model, ids)
                H.clear()
                arr = np.stack([store[L].numpy() for L in layers], axis=1)  # (n_pos, nL, 4096)
                out[key] = arr.astype(np.float16)
                out[key + "|jlR"] = np.stack([store[L].numpy()[-1] for L in JL_LAYERS]).astype(np.float32)
                meta[key] = {"segment_positions": seg, "name_positions": pr["spans"].get("name", []),
                             "R": len(ids) - 1, "segment_tokens": [P["_tok"].decode([ids[p]]) for p in seg]}
    np.savez_compressed(TENSORS / f"prompt_only_states{SFX['s']}.npz", **{k.replace("|", "__"): v for k, v in out.items()})
    write_json(RESULTS / f"prompt_only_meta{SFX['s']}.json", {"layers": layers, "jl_layers": JL_LAYERS, "prompts": meta})
    logger.info(f"prompt-only passes: {len(meta)} prompts")


# ---------------------------------------------------------------- J-lens
@torch.no_grad()
def lens_logits(model, h: torch.Tensor, J: torch.Tensor | None, orient: str = "Jh") -> torch.Tensor:  # noqa: ANN001
    x = h.to(DEV, torch.bfloat16)
    if J is not None:
        x = x @ (J.T if orient == "Jh" else J)
    return model.lm_head(model.model.norm(x)).float()


@torch.no_grad()
def jlens_gate(model, gate_states: dict[int, torch.Tensor], own_next: torch.Tensor, J: dict[int, torch.Tensor]
               ) -> dict[str, Any]:  # noqa: ANN001
    res: dict[str, Any] = {"n_positions": int(own_next.numel()), "layers": {}}
    own = own_next.to(DEV)
    for L in JL_LAYERS:
        h = gate_states[L]
        JL = J[L].to(DEV, torch.bfloat16)
        rec = {}
        for name, Jm, orient in (("logit_lens", None, "Jh"), ("jlens_Jh", JL, "Jh"), ("jlens_JTh", JL, "JTh")):
            hits, hits5 = 0, 0
            for a in range(0, h.shape[0], 256):
                lg = lens_logits(model, h[a:a + 256], Jm, orient)
                top = lg.topk(5, dim=-1).indices
                hits += int((top[:, 0] == own[a:a + 256]).sum())
                hits5 += int((top == own[a:a + 256, None]).any(-1).sum())
            rec[name] = {"top1": hits / h.shape[0], "top5": hits5 / h.shape[0]}
        res["layers"][str(L)] = rec
        del JL
    torch.cuda.empty_cache()
    best = "Jh" if np.mean([res["layers"][str(L)]["jlens_Jh"]["top1"] for L in JL_LAYERS if L >= 18]) >= np.mean(
        [res["layers"][str(L)]["jlens_JTh"]["top1"] for L in JL_LAYERS if L >= 18]) else "JTh"
    res["orientation"] = best
    deep = [L for L in JL_LAYERS if L >= 18]
    wins = sum(res["layers"][str(L)][f"jlens_{best}"]["top1"] >= res["layers"][str(L)]["logit_lens"]["top1"]
               for L in deep)
    res["n_deep_layers_jlens_ge_logit_lens"] = wins
    res["gate_pass"] = bool(wins > len(deep) / 2)
    return res


@torch.no_grad()
def jlens_apply(model, J: dict[int, torch.Tensor], orient: str, tok_ids: dict[str, int], tok) -> dict[str, Any]:  # noqa: ANN001
    """Ranks/probabilities of name and signature tokens under the J-lens and the logit lens at R (prompt-only
    ban / mention / neutral) and at k_pre / k_post of the fresh pool (ban prompt)."""
    ids = torch.tensor(list(tok_ids.values()), device=DEV)
    names = list(tok_ids)
    po = np.load(TENSORS / f"prompt_only_states{SFX['s']}.npz")
    e2 = np.load(TENSORS / f"e2_jlens_states{SFX['s']}.npz")
    out: dict[str, Any] = {"tokens": names, "token_ids": tok_ids, "orientation": orient, "R": {}, "fresh": {}}

    def stats(h: np.ndarray, L: int, use_j: bool) -> tuple[np.ndarray, np.ndarray, list[list[str]]]:
        x = torch.tensor(h, dtype=torch.float32)
        lg = lens_logits(model, x, J[L].to(DEV, torch.bfloat16) if use_j else None, orient)
        lp = torch.log_softmax(lg, -1)
        tgt = lg[:, ids]
        ranks = torch.stack([(lg > tgt[:, j:j + 1]).sum(-1) for j in range(tgt.shape[1])], dim=1)  # (n, n_tok)
        top5 = lg.topk(5, -1).indices.cpu().tolist()
        return lp[:, ids].exp().cpu().numpy(), ranks.cpu().numpy(), [[tok.decode([t]) for t in row] for row in top5]

    for t in TASKS:
        for cond in ("ban", "mention", "neutral"):
            H = np.stack([po[f"{t}__{cond}__{w}__jlR"] for w in TEMPLATE_IDS])  # (5, 9, 4096)
            for li, L in enumerate(JL_LAYERS):
                for lens in ("jlens", "logit_lens"):
                    p, rk, top = stats(H[:, li], L, lens == "jlens")
                    out["R"][f"{t}|{cond}|L{L}|{lens}"] = {"mean_prob": dict(zip(names, p.mean(0).tolist())),
                                                         "median_rank": dict(zip(names, np.median(rk, 0).tolist())),
                                                         "top5_first_template": top[0]}
    meta = read_json(RESULTS / f"e2_meta{SFX['s']}.json")["runs"]
    for L in JL_LAYERS:
        A = e2[f"L{L}"].astype(np.float32)  # (n, 3, 4096): R, k_pre, k_post (ban prompt)
        for pj, pname in ((1, "k_pre"), (2, "k_post")):
            ok = np.isfinite(A[:, pj, 0])
            for lens in ("jlens", "logit_lens"):
                p, rk, top = stats(A[ok, pj], L, lens == "jlens")
                out["fresh"][f"L{L}|{pname}|{lens}"] = {"run_index": np.where(ok)[0].tolist(),
                                                       "prob": p.astype(np.float32).round(6).tolist(),
                                                       "rank": rk.tolist(), "top5_first3": top[:3]}
    out["n_fresh_runs"] = len(meta)
    torch.cuda.empty_cache()
    return out


# ---------------------------------------------------------------- E1
@torch.no_grad()
def run_transfer(model, corpus: list[dict[str, Any]], layers: list[int], tag: str, want_codes: bool,
                 jl_gate: bool) -> dict[str, Any]:  # noqa: ANN001
    res: dict[str, Any] = {"model_tag": tag, "n_seq": len(corpus), "layers": {}}
    states = {L: [] for L in layers}
    ce_clean = []
    gate_states: dict[int, list[torch.Tensor]] = {L: [] for L in JL_LAYERS}
    own_next: list[torch.Tensor] = []
    t0 = time.time()
    for si, s in enumerate(corpus):
        store: dict[Any, torch.Tensor] = {}
        H = Hooks()
        for L in layers:
            H.add(model.model.layers[L], cap_hook(store, L))
        gpos = None
        if jl_gate and si < 50:
            resp = list(range(s["start"], len(s["ids"]) - 1))
            gpos = [resp[int(j)] for j in np.linspace(0, len(resp) - 1, min(40, len(resp)))]
            for L in JL_LAYERS:
                H.add(model.model.layers[L], cap_hook(store, ("g", L), gpos))
        hfin = forward(model, s["ids"])
        H.clear()
        ce_clean.append(token_ce(model, hfin, s["ids"], s["start"]))
        for L in layers:
            states[L].append(store[L])  # (S, 4096) bf16 on the CPU
        if gpos is not None:
            for L in JL_LAYERS:
                gate_states[L].append(store[("g", L)])
            own_next.append(model.lm_head(hfin[0, gpos]).argmax(-1).cpu())
        if si == 9:
            logger.info(f"E1[{tag}] clean: 10 seqs in {time.time() - t0:.1f}s")
    res["ce_clean_per_seq"] = [float(c.mean()) for c in ce_clean]
    res["n_tokens_scored"] = int(sum(len(c) for c in ce_clean))
    if jl_gate:
        res["_gate_states"] = {L: torch.cat(v) for L, v in gate_states.items()}
        res["_own_next"] = torch.cat(own_next)
    for L in layers:
        with Timer(f"E1_{tag}_L{L}", gpu=True, n=len(corpus)):
            # GPU budget: model 14.1 GiB + SAE 1.0 GiB leaves ~0.3 GiB on the 15.6 GiB card, so lm_head (1.16 GiB)
            # goes to the CPU while the SAE is loaded; spliced final states are kept and CE is computed afterwards.
            model.lm_head.to("cpu")
            torch.cuda.empty_cache()
            sae = SAE(L)
            err = tot2 = 0.0
            sumx = torch.zeros(4096, device=DEV, dtype=torch.float64)
            ntok = 0
            rel, cos, norms = [], [], []
            codes_idx, codes_val, offsets = [], [], [0]
            for x_cpu in states[L]:
                x = x_cpu[1:].to(DEV).float()
                r = sae.recon(x)
                err += float(((x - r) ** 2).sum())
                tot2 += float((x.double() ** 2).sum())
                sumx += x.double().sum(0)
                ntok += x.shape[0]
                rel.append((((x - r) ** 2).sum(1) / (x ** 2).sum(1)).cpu())
                cos.append(torch.nn.functional.cosine_similarity(x, r, dim=1).cpu())
                norms.append(x.norm(dim=1).cpu())
                if want_codes:
                    v, i = sae.encode(x)
                    codes_idx.append(i.cpu().numpy().astype(np.uint16))
                    codes_val.append(v.cpu().numpy().astype(np.float16))
                    offsets.append(offsets[-1] + x.shape[0])
            mean = sumx / ntok
            var_tot = tot2 - ntok * float((mean ** 2).sum())
            nrm = torch.cat(norms)
            med = float(nrm.median())
            rec: dict[str, Any] = {"fvu": err / var_tot, "rel_mse_mean": float(torch.cat(rel).mean()),
                                   "cos_mean": float(torch.cat(cos).mean()), "n_tokens": ntok,
                                   "norm_median": med, "share_norm_gt_5x_median": float((nrm > 5 * med).float().mean()),
                                   "sae_weights": "bf16 on GPU (fp32 pre-activations and top-k)"}
            if want_codes:
                np.savez_compressed(TENSORS / f"context_codes_L{L}{SFX['s']}.npz", idx=np.concatenate(codes_idx),
                                    val=np.concatenate(codes_val), offsets=np.array(offsets),
                                    seq_task=np.array([s["task"] for s in corpus]),
                                    seq_cond=np.array([s["condition"] for s in corpus]))
            finals = []
            t1 = time.time()
            for si, s in enumerate(corpus):
                H = Hooks()
                H.add(model.model.layers[L], splice_hook(sae.recon))
                hfin = forward(model, s["ids"])
                H.clear()
                finals.append(hfin[0, s["start"]:len(s["ids"]) - 1].to("cpu"))
                del hfin
                if si == 9:
                    logger.info(f"E1[{tag}] L{L} splice: 10 seqs in {time.time() - t1:.1f}s")
            sae.free()
            model.lm_head.to(DEV)
            ce_sp = []
            for s, hs in zip(corpus, finals):
                tg = torch.tensor(s["ids"][s["start"] + 1:], device=DEV)
                ce = []
                for a in range(0, hs.shape[0], 128):
                    lg = model.lm_head(hs[a:a + 128].to(DEV)).float()
                    ce.append(torch.nn.functional.cross_entropy(lg, tg[a:a + 128], reduction="none"))
                ce_sp.append(float(torch.cat(ce).mean()))
            del finals
            rec["ce_splice_per_seq"] = ce_sp
            rec["dce_per_seq"] = [a - b for a, b in zip(ce_sp, res["ce_clean_per_seq"])]
            rec["dce_mean"] = float(np.mean(rec["dce_per_seq"]))
            res["layers"][str(L)] = rec
            logger.info(f"E1[{tag}] L{L}: CE clean {np.mean(res['ce_clean_per_seq']):.4f} splice {np.mean(ce_sp):.4f} "
                        f"dCE {rec['dce_mean']:.4f} FVU {rec['fvu']:.3f} relMSE {rec['rel_mse_mean']:.3f} "
                        f"cos {rec['cos_mean']:.3f} high-norm share {rec['share_norm_gt_5x_median']:.4f}")
    del states
    gc.collect()
    return res


@torch.no_grad()
def splice_sanity(model, corpus: list[dict[str, Any]], L: int) -> dict[str, Any]:  # noqa: ANN001
    out = []
    for s in corpus[:2]:
        clean = float(token_ce(model, forward(model, s["ids"]), s["ids"], s["start"]).mean())
        H = Hooks()
        H.add(model.model.layers[L], splice_hook(lambda x: x))
        ident = float(token_ce(model, forward(model, s["ids"]), s["ids"], s["start"]).mean())
        H.clear()
        H.add(model.model.layers[L], splice_hook(lambda x: torch.zeros_like(x)))
        zero = float(token_ce(model, forward(model, s["ids"]), s["ids"], s["start"]).mean())
        H.clear()
        out.append({"ce_clean": clean, "ce_identity_splice": ident, "ce_zero_splice": zero})
    ok = all(abs(o["ce_identity_splice"] - o["ce_clean"]) < 1e-4 and o["ce_zero_splice"] > o["ce_clean"] + 1.0
             for o in out)
    logger.info(f"splice sanity at L{L}: {out} -> pass={ok}")
    return {"layer": L, "rows": out, "pass": ok}


@torch.no_grad()
def eager_check(model, P: dict[str, Any]) -> dict[str, Any]:  # noqa: ANN001
    """Wrapped-SDPA attention rows vs eager attention probabilities, and sdpa vs eager logits, on 3 prompts."""
    res = []
    try:
        for key in ("t1|ban|W1", "t2|ban|W3", "t1|neutral|W5"):
            ids = P["prompts"][key]["nothink"]["ids"]
            qp = [len(ids) - 2, len(ids) - 1]
            ATT["q"], ATT["rows"] = qp, {}
            h_s = forward(model, ids)
            rows = {L: v.clone() for L, v in ATT["rows"].items()}
            ATT["q"] = None
            lg_s = model.lm_head(h_s[0, -1]).float()
            model.set_attn_implementation("eager")
            emb = model.model.embed_tokens(torch.tensor([ids])).to(DEV)
            o = model.model(inputs_embeds=emb, use_cache=False, output_attentions=True)
            lg_e = model.lm_head(o.last_hidden_state[0, -1]).float()
            diffs = [float((o.attentions[L][0][:, qp, :].float() - rows[L]).abs().max()) for L in (0, 17, 35)]
            res.append({"prompt": key, "max_abs_attn_diff_L0_17_35": diffs,
                        "max_abs_logit_diff": float((lg_s - lg_e).abs().max()),
                        "argmax_equal": bool(lg_s.argmax() == lg_e.argmax())})
            model.set_attn_implementation("sdpa")
            del o
            torch.cuda.empty_cache()
    except Exception as e:  # noqa: BLE001 - the check is reported, not required
        logger.warning(f"eager check failed: {e!r}")
        try:
            model.set_attn_implementation("sdpa")
        except Exception:  # noqa: BLE001
            pass
        res.append({"error": repr(e)[:300]})
    install_attention_capture()
    logger.info(f"eager check: {res}")
    return {"rows": res}


def run_stage_hf(smoke: bool = False) -> None:
    from transformers import AutoTokenizer

    from prompts import build_prompts

    layers = sae_layers()
    tok = AutoTokenizer.from_pretrained(MODEL_HF)
    P = build_prompts()
    P["_tok"] = tok
    corpus = transfer_corpus(tok)
    if smoke:
        SFX["s"] = "_smoke"
        corpus = corpus[:2] + corpus[100:101]
    logger.info(f"layers {layers}; transfer corpus {len(corpus)} seqs, mean len "
                f"{np.mean([len(s['ids']) for s in corpus]):.0f}")
    install_attention_capture()
    out_path = RESULTS / f"transfer_test{SFX['s']}.json"
    TT = read_json(out_path, {})
    model = load_model(MODEL_HF)
    with Timer("E2_checks", gpu=True):
        TT["splice_sanity"] = splice_sanity(model, corpus, layers[0])
        TT["eager_check"] = eager_check(model, P)
        write_json(out_path, TT)
    if not (TENSORS / f"e2_states{SFX['s']}.npz").exists():
        with Timer("E2_fresh_pool" + SFX["s"], gpu=True):
            run_e2(model, tok, P, layers, limit=4 if smoke else None)
        with Timer("E2_prompt_only", gpu=True):
            run_prompt_only(model, P, layers)
    with Timer("E1_instruct_clean", gpu=True, n=len(corpus)):
        inst = run_transfer(model, corpus, layers, "instruct", want_codes=True, jl_gate=True)
    TT["instruct"] = {k: v for k, v in inst.items() if not k.startswith("_")}
    write_json(out_path, TT)
    try:
        run_jlens(model, inst, tok)
    except Exception as e:  # noqa: BLE001 - the lens is optional (F10); the transfer test must survive
        logger.exception(f"J-lens step failed: {e!r}")
        write_json(RESULTS / f"jlens{SFX['s']}.json", {"status": f"failed: {e!r}"[:400]})
    inst.pop("_gate_states", None)
    inst.pop("_own_next", None)
    del model
    gc.collect()
    torch.cuda.empty_cache()
    if smoke:
        logger.info("smoke run complete (base model skipped)")
        return
    model = load_model(MODEL_BASE)
    with Timer("E1_base", gpu=True, n=len(corpus)):
        TT["base"] = run_transfer(model, corpus, layers, "base", want_codes=False, jl_gate=False)
    TT["corpus"] = [{k: s[k] for k in ("task", "condition", "paraphrase_id", "sample_id", "start")} |
                    {"len": len(s["ids"])} for s in corpus]
    write_json(out_path, TT)
    add_deviation("D08", "HF readouts keep embed_tokens on the CPU and the Qwen-Scope SAE weights on the GPU in bf16 "
                  "(fp32 pre-activations and top-k); attention rows come from a wrapped SDPA kernel.",
                  "bf16 Qwen3-8B (16.4 GB) plus a 2.1 GB fp32 SAE do not fit on the 16 GB GPU.",
                  "SAE codes differ from fp32 codes by bf16 rounding of W_enc / W_dec; checked by FVU / relative "
                  "MSE / spliced CE, and attention rows are checked against eager attention.")
    logger.info("HF stage complete")


def run_jlens(model, inst: dict[str, Any], tok) -> None:  # noqa: ANN001
    with Timer("E4_jlens", gpu=True):
        J = load_jlens()
        gate = jlens_gate(model, inst.pop("_gate_states"), inst.pop("_own_next"), J)
        logger.info(f"J-lens gate: pass={gate['gate_pass']} orientation={gate['orientation']} "
                    f"{ {L: (round(v['logit_lens']['top1'], 3), round(v['jlens_' + gate['orientation']]['top1'], 3)) for L, v in gate['layers'].items()} }")
        JLR: dict[str, Any] = {"gate": gate, "lens_file": f"{JLENS_REPO}/Qwen3-8B/lens.pt",
                               "lens_meta": "fit on fineweb sample-10BT, 1000 prompts, source layers 9,18,21-27, "
                                            "decoder block output hook (= model.model.layers[l] output)"}
        JLR["application"] = jlens_apply(model, J, gate["orientation"], lens_token_ids(tok), tok)
        JLR["application"]["gated"] = gate["gate_pass"]
        write_json(RESULTS / f"jlens{SFX['s']}.json", JLR)
        del J
        gc.collect()

