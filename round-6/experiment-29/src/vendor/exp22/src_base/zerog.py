#!/usr/bin/env python3
"""9.4 0g: Qwen-Scope SAE transfer, recomputed as the fraction of CE loss recovered against zero-ablation, per model on
its OWN outputs, in a 2x2 (model x text source) design.

Instruct text = exp12's transfer corpus (exp1 instruct programs; 25 per (task, condition) group, the first 25 of
exp12's 50 in corpus order). Base text = Qwen3-8B-Base outputs generated here on the same prompts (chat template,
thinking off, T=1.0, max 512 new tokens). Hook = exp12's: block-L output (model.model.layers[L]), L in {15, 20, 27};
splice at positions >= 1 excluding chat special tokens. CE over response tokens. Conditions: clean, SAE-spliced,
zero-ablated, mean-ablated (mean over that model's own-corpus positions). Companions: FR_mean, KL(clean||spliced),
dCE, FVU, L0, displacement preservation of the ban-minus-twin displacement (S2 states). Also encodes the saved
C2e states with each SAE for 5a. Only one model is in memory at a time.
"""

from __future__ import annotations

import gc
import json
import time
from typing import Any

import numpy as np
import torch
from loguru import logger

import states_io
from cfg import (BASE_MODEL_ID, DIR_DIR, E12, IM_END, RESULTS_DIR, SAE_REPO, SAMPLED_TASKS, STATES_DIR,
                 read_json, read_jsonl, write_json)

SAE_LAYERS = [15, 20, 27]
SAE_K = 50
N_PER_GROUP = 25
SPECIAL_MIN = 151643
OUT = RESULTS_DIR / "sae_transfer_raw.json"


class SAE:
    """Qwen-Scope TopK SAE (exp12 class, model-card math: pre = h W_enc^T + b_enc, keep top-50, recon = z W_dec^T +
    b_dec); bf16 weights on the GPU, fp32 pre-activations."""

    def __init__(self, L: int, dev: torch.device) -> None:
        from huggingface_hub import hf_hub_download

        d = torch.load(hf_hub_download(SAE_REPO, f"layer{L}.sae.pt"), map_location="cpu", weights_only=True,
                       mmap=True)
        self.L, self.dev = L, dev
        self.W_enc = d["W_enc"].to(dev, torch.bfloat16)
        self.b_enc = d["b_enc"].to(dev, torch.float32)
        self.W_dec = d["W_dec"].to(dev, torch.bfloat16)
        self.b_dec = d["b_dec"].to(dev, torch.float32)
        del d
        gc.collect()

    @torch.no_grad()
    def encode(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        pre = torch.nn.functional.linear(x.to(torch.bfloat16), self.W_enc).float() + self.b_enc
        return pre.topk(SAE_K, dim=-1)

    @torch.no_grad()
    def decode(self, v: torch.Tensor, i: torch.Tensor) -> torch.Tensor:
        z = torch.zeros(v.shape[0], self.W_enc.shape[0], device=self.dev, dtype=torch.bfloat16)
        z.scatter_(1, i, v.to(torch.bfloat16))
        return torch.nn.functional.linear(z, self.W_dec).float() + self.b_dec

    @torch.no_grad()
    def recon(self, x: torch.Tensor, chunk: int = 256) -> torch.Tensor:
        return torch.cat([self.decode(*self.encode(x[a:a + chunk])) for a in range(0, x.shape[0], chunk)])

    def free(self) -> None:
        del self.W_enc, self.W_dec, self.b_enc, self.b_dec
        gc.collect()
        torch.cuda.empty_cache()


def inst_corpus(tok: Any) -> list[dict[str, Any]]:
    corpus = read_json(E12 / "results" / "transfer_test.json")["corpus"]
    rows = {(r["task"], r["condition"], int(r["paraphrase_id"]), int(r["sample_id"])): r
            for r in read_jsonl(E12 / "exp1" / "data" / "samples.jsonl")}
    cond = read_json(E12 / "exp1" / "prompts" / "conditions.json")
    out, seen = [], {}
    for c in corpus:
        g = (c["task"], c["condition"])
        if seen.get(g, 0) >= N_PER_GROUP:
            continue
        seen[g] = seen.get(g, 0) + 1
        r = rows[(c["task"], c["condition"], int(c["paraphrase_id"]), int(c["sample_id"]))]
        prompt = [p for p in cond["tasks"][c["task"]]["conditions"][c["condition"]]
                  if int(p["paraphrase_id"]) == int(c["paraphrase_id"])][0]["prompt"]
        p_ids = list(tok.apply_chat_template([{"role": "user", "content": prompt}], tokenize=True,
                                             add_generation_prompt=True, enable_thinking=False))
        resp = tok("```python\n" + r["code"].strip("\n") + "\n```", add_special_tokens=False)["input_ids"]
        ids = p_ids + list(resp) + [IM_END]
        assert len(ids) == c["len"] and len(p_ids) - 1 == c["start"], "exp12 corpus not reproduced"
        out.append({"task": c["task"], "condition": c["condition"], "sample_id": c["sample_id"], "p_ids": p_ids,
                    "ids": ids, "start": len(p_ids) - 1, "source": "instruct (exp1 programs, exp12 corpus)"})
    return out


@torch.no_grad()
def gen_base(model: Any, tok: Any, corpus: list[dict[str, Any]], max_new: int = 512, bs: int = 25) -> list[dict]:
    torch.manual_seed(20261020)
    out = []
    pad = tok.pad_token_id if tok.pad_token_id is not None else IM_END
    for a in range(0, len(corpus), bs):
        part = corpus[a:a + bs]
        L = max(len(c["p_ids"]) for c in part)
        inp = torch.full((len(part), L), pad, dtype=torch.long)
        am = torch.zeros((len(part), L), dtype=torch.long)
        for i, c in enumerate(part):
            inp[i, L - len(c["p_ids"]):] = torch.tensor(c["p_ids"])
            am[i, L - len(c["p_ids"]):] = 1
        g = model.generate(input_ids=inp.to(model.device), attention_mask=am.to(model.device), do_sample=True,
                           temperature=1.0, top_p=1.0, top_k=0, max_new_tokens=max_new,
                           eos_token_id=[IM_END, 151643], pad_token_id=pad)
        for i, c in enumerate(part):
            resp = g[i, L:].tolist()
            if IM_END in resp:
                resp = resp[:resp.index(IM_END) + 1]
            elif 151643 in resp:
                resp = resp[:resp.index(151643) + 1]
            out.append({**{k: c[k] for k in ("task", "condition", "sample_id", "p_ids")},
                        "ids": c["p_ids"] + resp, "start": len(c["p_ids"]) - 1, "source": "base (generated here)",
                        "text": tok.decode(resp, skip_special_tokens=False)[:2000], "n_gen": len(resp)})
        logger.info(f"0g base generation {a + len(part)}/{len(corpus)}")
    return out


def _splice_hook(fn, mask: torch.Tensor):
    def f(mod, inp, out):
        h = out[0] if isinstance(out, tuple) else out
        new = h.clone()
        x = h[0, mask].float()
        new[0, mask] = fn(x).to(h.dtype)
        return (new,) + tuple(out[1:]) if isinstance(out, tuple) else new
    return f


@torch.no_grad()
def ce_design(model: Any, corpus: list[dict[str, Any]], saes: dict[int, SAE], means: dict[int, torch.Tensor] | None,
              tag: str) -> dict[str, Any]:
    """Per sequence: clean CE + per layer {sae, zero, mean} CE and KL(clean || spliced); FVU/L0 on clean states."""
    dev = model.device
    want_means = means is None
    sums = {L: torch.zeros(4096, dtype=torch.float64, device=dev) for L in SAE_LAYERS}
    cnt = 0
    acc: dict[str, list[float]] = {}
    fvu_num = {L: 0.0 for L in SAE_LAYERS}
    tot2 = {L: 0.0 for L in SAE_LAYERS}
    sumx = {L: torch.zeros(4096, dtype=torch.float64, device=dev) for L in SAE_LAYERS}
    l0 = {L: [] for L in SAE_LAYERS}
    states_cache: list[dict[int, torch.Tensor]] = []
    t0 = time.time()
    # pass 1: clean CE, clean states (for FVU / L0 / means)
    clean_lp: list[torch.Tensor] = []
    for si, s in enumerate(corpus):
        ids = torch.tensor([s["ids"]], device=dev)
        cap: dict[int, torch.Tensor] = {}
        hs = [model.model.layers[L].register_forward_hook(
            lambda m, i, o, L=L: cap.__setitem__(L, (o[0] if isinstance(o, tuple) else o)[0].float()))
            for L in SAE_LAYERS]
        h = model.model(input_ids=ids, use_cache=False).last_hidden_state
        for x in hs:
            x.remove()
        st = s["start"]
        lp = torch.log_softmax(model.lm_head(h[0, st:-1]).float(), -1)
        tg = ids[0, st + 1:]
        ce = -lp.gather(-1, tg[:, None])[:, 0]
        acc.setdefault("clean", []).append(float(ce.mean()))
        tv, ti = lp.topk(256, dim=-1)  # KL(clean || spliced) over the clean top-256 support (mass reported)
        clean_lp.append((tv.cpu(), ti.cpu()))
        acc.setdefault("clean_top256_mass", []).append(float(tv.exp().sum(-1).mean()))
        mask = torch.tensor([i >= 1 and t < SPECIAL_MIN for i, t in enumerate(s["ids"])], device=dev)
        for L in SAE_LAYERS:
            x = cap[L][mask]
            if want_means:
                sums[L] += x.double().sum(0)
            r = saes[L].recon(x)
            fvu_num[L] += float(((x - r) ** 2).sum())
            tot2[L] += float((x.double() ** 2).sum())
            sumx[L] += x.double().sum(0)
            v, _ = saes[L].encode(x)
            l0[L].append(float((v > 0).float().sum(-1).mean()))
        cnt += int(mask.sum())
        del cap, h
    if want_means:
        means = {L: (sums[L] / max(cnt, 1)).float() for L in SAE_LAYERS}
    out: dict[str, Any] = {"tag": tag, "n_seq": len(corpus), "ce_clean": acc["clean"], "layers": {},
                           "clean_top256_mass_mean": float(np.mean(acc["clean_top256_mass"]))}
    for L in SAE_LAYERS:
        mu = sumx[L] / max(cnt, 1)
        var = tot2[L] - cnt * float((mu ** 2).sum())
        out["layers"][L] = {"fvu": fvu_num[L] / var, "l0_positive_mean": float(np.mean(l0[L])), "l0_topk": SAE_K}
    # pass 2: spliced conditions
    for L in SAE_LAYERS:
        fns = {"sae": saes[L].recon, "zero": lambda x: torch.zeros_like(x),
               "mean": lambda x, L=L: means[L][None].expand_as(x)}
        for cond, fn in fns.items():
            ces, kls = [], []
            for si, s in enumerate(corpus):
                ids = torch.tensor([s["ids"]], device=dev)
                mask = torch.tensor([i >= 1 and t < SPECIAL_MIN for i, t in enumerate(s["ids"])], device=dev)
                hk = model.model.layers[L].register_forward_hook(_splice_hook(fn, mask))
                h = model.model(input_ids=ids, use_cache=False).last_hidden_state
                hk.remove()
                st = s["start"]
                lp = torch.log_softmax(model.lm_head(h[0, st:-1]).float(), -1)
                tg = ids[0, st + 1:]
                ces.append(float((-lp.gather(-1, tg[:, None])[:, 0]).mean()))
                tv, ti = clean_lp[si]
                tv, ti = tv.to(dev), ti.to(dev)
                kls.append(float((tv.exp() * (tv - lp.gather(-1, ti))).sum(-1).mean()))
                del h, lp
            out["layers"][L][f"ce_{cond}"] = ces
            out["layers"][L][f"kl_{cond}"] = kls
        logger.info(f"0g {tag} L{L}: CE clean {np.mean(acc['clean']):.4f} sae {np.mean(out['layers'][L]['ce_sae']):.4f} "
                    f"zero {np.mean(out['layers'][L]['ce_zero']):.3f} mean {np.mean(out['layers'][L]['ce_mean']):.3f} "
                    f"({time.time() - t0:.0f}s)")
    out["means"] = {L: means[L].cpu().numpy().tolist() for L in SAE_LAYERS} if want_means else None
    return out


def sanity(model: Any, corpus: list[dict[str, Any]], L: int = 15) -> dict[str, Any]:
    rows = []
    for s in corpus[:2]:
        ids = torch.tensor([s["ids"]], device=model.device)
        mask = torch.tensor([i >= 1 for i in range(len(s["ids"]))], device=model.device)
        res = {}
        for name, fn in (("clean", None), ("identity", lambda x: x), ("zero", lambda x: torch.zeros_like(x))):
            hk = model.model.layers[L].register_forward_hook(_splice_hook(fn, mask)) if fn else None
            with torch.no_grad():
                h = model.model(input_ids=ids, use_cache=False).last_hidden_state
            if hk:
                hk.remove()
            st = s["start"]
            lp = torch.log_softmax(model.lm_head(h[0, st:-1]).float(), -1)
            res[name] = float((-lp.gather(-1, ids[0, st + 1:][:, None])[:, 0]).mean())
        rows.append(res)
    return {"layer": L, "rows": rows, "identity_equals_clean": all(abs(r["identity"] - r["clean"]) < 1e-4 for r in rows),
            "zero_ce_mean": float(np.mean([r["zero"] for r in rows]))}


@torch.no_grad()
def displacement_preservation(saes: dict[int, SAE], dev: torch.device) -> dict[str, Any]:
    z = np.load(DIR_DIR / "sae_pos_states.npz")
    out: dict[str, Any] = {}
    for L in SAE_LAYERS:
        cs, nr = {}, {}
        for t in SAMPLED_TASKS:
            c_t, n_t = [], []
            for w in ("W1", "W2", "W3", "W4", "W5"):
                hb = torch.tensor(z[f"{t}|{w}|{L}|ban"], device=dev).float()
                ht = torch.tensor(z[f"{t}|{w}|{L}|twin"], device=dev).float()
                d = hb - ht
                ds = saes[L].recon(hb) - saes[L].recon(ht)
                c_t += torch.nn.functional.cosine_similarity(ds, d, dim=-1).tolist()
                n_t += (ds.norm(dim=-1) / d.norm(dim=-1).clamp(min=1e-6)).tolist()
            cs[t] = float(np.mean(c_t))
            nr[t] = float(np.median(n_t))
        out[L] = {"cos_mean_by_task": cs, "norm_ratio_median_by_task": nr,
                  "cos_mean_all": float(np.mean(list(cs.values())))}
    return out


@torch.no_grad()
def encode_states(saes: dict[int, SAE], dev: torch.device) -> dict[str, Any]:
    """5a: SAE codes of saved states (positions S-mean, k1, k2, k3) for BAN and NEUTRAL of every sampled task."""
    from states import POS_NAMES

    pos = [POS_NAMES.index(p) for p in ("Smean", "k1", "k2", "k3")]
    info = {}
    for t in SAMPLED_TASKS:
        for arm in ("BAN", "NEUTRAL"):
            if not states_io.exists(STATES_DIR / f"{t}_{arm}"):
                continue
            X = states_io.load(STATES_DIR / f"{t}_{arm}")
            meta = json.load(open(STATES_DIR / f"{t}_{arm}_meta.json"))
            blocks = meta["blocks"]
            codes = {}
            for L in SAE_LAYERS:
                bi = blocks.index(L)
                x = torch.tensor(np.asarray(X[:, pos, bi]), device=dev).float()  # [n, 4, D]
                n = x.shape[0]
                v, i = saes[L].encode(x.reshape(-1, 4096))
                r = saes[L].decode(v, i)
                xf = x.reshape(-1, 4096)
                fvu = float(((xf - r) ** 2).sum() / ((xf - xf.mean(0)) ** 2).sum())
                codes[f"idx_L{L}"] = i.reshape(n, 4, SAE_K).cpu().numpy().astype(np.int32)
                codes[f"val_L{L}"] = v.reshape(n, 4, SAE_K).cpu().numpy().astype(np.float16)
                info[f"{t}_{arm}_L{L}_fvu"] = fvu
            np.savez_compressed(STATES_DIR / f"sae_codes_{t}_{arm}.npz", **codes, positions=np.array(["Smean", "k1", "k2", "k3"]))
    return info


def stage_zerog(deadline: float) -> None:
    from engine import free, load_model

    t0 = time.time()
    raw = json.loads(OUT.read_text()) if OUT.exists() else {}
    dev = torch.device("cuda", 0)
    # ---- base model: generate own text, CE on own text (means) and on instruct text
    if "base_own" not in raw:
        from transformers import AutoTokenizer

        from cfg import model_path

        _, model = load_model(BASE_MODEL_ID, revision=None)
        tok = AutoTokenizer.from_pretrained(model_path())  # instruct tokenizer: identical vocabulary, exp12's template
        corp_i = inst_corpus(tok)
        base_c = gen_base(model, tok, corp_i)
        with open(RESULTS_DIR / "sae_base_corpus.jsonl", "w") as fh:
            for c in base_c:
                fh.write(json.dumps({k: v for k, v in c.items() if k != "p_ids"}) + "\n")
        saes = {L: SAE(L, dev) for L in SAE_LAYERS}
        raw["sanity_base"] = sanity(model, corp_i)
        raw["base_own"] = ce_design(model, base_c, saes, None, "base_on_base")
        means_b = {L: torch.tensor(raw["base_own"]["means"].get(L, raw["base_own"]["means"].get(str(L))), device=dev)
                   for L in SAE_LAYERS}
        raw["base_on_inst"] = ce_design(model, corp_i, saes, means_b, "base_on_inst")
        OUT.write_text(json.dumps(raw))
        for s in saes.values():
            s.free()
        free(model)
        del model
        gc.collect()
        torch.cuda.empty_cache()
        logger.info(f"0g base done ({time.time() - t0:.0f}s)")
    # ---- instruct model: CE on own text (means), on base text; displacement preservation; 5a codes
    if "inst_own" not in raw:
        tok, model = load_model()
        corp_i = inst_corpus(tok)
        base_c = [json.loads(l) for l in open(RESULTS_DIR / "sae_base_corpus.jsonl")]
        saes = {L: SAE(L, dev) for L in SAE_LAYERS}
        raw["sanity_inst"] = sanity(model, corp_i)
        raw["inst_own"] = ce_design(model, corp_i, saes, None, "inst_on_inst")
        means_i = {L: torch.tensor(raw["inst_own"]["means"].get(L, raw["inst_own"]["means"].get(str(L))), device=dev)
                   for L in SAE_LAYERS}
        raw["inst_on_base"] = ce_design(model, base_c, saes, means_i, "inst_on_base")
        raw["displacement_preservation"] = displacement_preservation(saes, dev)
        raw["state_code_fvu"] = encode_states(saes, dev)
        OUT.write_text(json.dumps(raw))
        for s in saes.values():
            s.free()
        logger.info(f"0g instruct done ({time.time() - t0:.0f}s)")
