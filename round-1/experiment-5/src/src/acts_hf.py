"""Sharpening direction (STEP 5). One process per model, base first.

  .venv/bin/python src/acts_hf.py --model base       -> activations/base_{task}_R.npy, base_{task}_gen.npy
  .venv/bin/python src/acts_hf.py --model instruct   -> activations/instruct_{task}_R.npy, instruct_{task}_gen.npy,
                                                        steer_{task}.npy (band-incremental vectors, layers 8..28),
                                                        results/sharpening_direction.json (diagnostics + logit lens)
Residual states are read with forward hooks on model.model.layers[L] (the same site the steering hook writes to);
index 0 = embedding output, index L+1 = output of decoder layer L.
"""
from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from pathlib import Path

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ACTS, MB, MI, N_LAYERS, RESULTS, RUNS, read_jsonl, setup_logging, time_log  # noqa: E402
from prompts import load_prompts  # noqa: E402

BAND = list(range(8, 29))  # 0-indexed decoder layers 8..28 (21 layers)


def load_model(model_id: str):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(model_id, dtype=torch.bfloat16, device_map="cuda",
                                                 attn_implementation="sdpa")
    model.eval()
    return tok, model


class Recorder:
    """Records the residual stream after the embedding and after every decoder layer for one forward pass."""

    def __init__(self, model):
        self.model = model
        self.handles = []
        self.store: dict[int, "torch.Tensor"] = {}
        emb = model.model.embed_tokens
        self.handles.append(emb.register_forward_hook(self._mk(0)))
        for L, layer in enumerate(model.model.layers):
            self.handles.append(layer.register_forward_hook(self._mk(L + 1)))

    def _mk(self, idx: int):
        def hook(mod, inp, out):
            hs = out[0] if isinstance(out, tuple) else out
            self.store[idx] = hs.detach()
        return hook

    def remove(self) -> None:
        for h in self.handles:
            h.remove()


def chat_ids(prompts: dict, task: str) -> list[list[int]]:
    return [p["token_ids"] for p in prompts["chat"][task]["baseline"]]  # P0..P49


def run_R(model, ids_list: list[list[int]], rec: Recorder) -> np.ndarray:
    import torch
    out = np.zeros((len(ids_list), N_LAYERS + 1, model.config.hidden_size), dtype=np.float32)
    with torch.inference_mode():
        for i, ids in enumerate(ids_list):
            rec.store.clear()
            model(input_ids=torch.tensor([ids], device="cuda"), use_cache=False, logits_to_keep=1)
            for l in range(N_LAYERS + 1):
                out[i, l] = rec.store[l][0, -1].float().cpu().numpy()
    return out


def gen_items(prompts: dict, task: str, tok) -> list[tuple[list[int], int]]:
    """20 B1 completions (samples 0-1 of each paraphrase P0..P9): prompt ids + first 64 completion tokens."""
    rows = [r for r in read_jsonl(RUNS / "raw_instruct_chat__baseline.jsonl") if r["task"] == task]
    pid = {p["id"]: p["token_ids"] for p in prompts["chat"][task]["baseline"]}
    items = []
    for k in range(10):
        sel = sorted([r for r in rows if r["prompt_id"] == f"P{k}"], key=lambda r: r["sample_id"])[:2]
        for r in sel:
            comp = tok(r["text"], add_special_tokens=False)["input_ids"][:64]
            items.append((pid[r["prompt_id"]] + comp, len(comp)))
    return items


def run_gen(model, items: list[tuple[list[int], int]], rec: Recorder) -> np.ndarray:
    import torch
    out = np.zeros((len(items), N_LAYERS + 1, model.config.hidden_size), dtype=np.float32)
    with torch.inference_mode():
        for i, (ids, n_c) in enumerate(items):
            rec.store.clear()
            model(input_ids=torch.tensor([ids], device="cuda"), use_cache=False, logits_to_keep=1)
            for l in range(N_LAYERS + 1):
                out[i, l] = rec.store[l][0, -n_c:].float().mean(0).cpu().numpy()
    return out


def cos(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


def diagnostics(hI: np.ndarray, hB: np.ndarray, gI: np.ndarray | None, gB: np.ndarray | None) -> dict:
    """hI, hB: [50, 37, D] at R (paired, identical tokens)."""
    diff = hI - hB
    delta = diff.mean(0)  # [37, D]
    d1 = diff[:25].mean(0)
    d2 = diff[25:].mean(0)
    per_layer = []
    dgen = (gI - gB).mean(0) if gI is not None and gB is not None else None
    for l in range(hI.shape[1]):
        mI, mB = hI[:, l].mean(0), hB[:, l].mean(0)
        dl = delta[l]
        e = dl ** 2
        top10 = float(np.sort(e)[-10:].sum() / (e.sum() + 1e-12))
        per_layer.append({
            "index": l, "decoder_layer": l - 1,
            "cos_meanI_meanB": cos(mI, mB),
            "mean_per_prompt_cos": float(np.mean([cos(hI[p, l], hB[p, l]) for p in range(hI.shape[0])])),
            "rel_norm_delta": float(np.linalg.norm(dl) / (np.linalg.norm(mB) + 1e-12)),
            "norm_delta": float(np.linalg.norm(dl)),
            "split_half_cos": cos(d1[l], d2[l]),
            "top10_energy_share": top10,
            "cos_delta_R_delta_gen": (cos(dl, dgen[l]) if dgen is not None else None),
        })
    return {"delta": delta, "per_layer": per_layer}


def band_vectors(delta: np.ndarray) -> np.ndarray:
    """v_8 = delta_8, v_L = delta_L - delta_{L-1}; delta indexed by decoder layer -> hidden index L+1."""
    vs = []
    for L in BAND:
        cur = delta[L + 1]
        prev = delta[L] if L > BAND[0] else np.zeros_like(cur)
        vs.append(cur - prev)
    return np.stack(vs).astype(np.float32)  # [21, D]


def logit_lens(model, tok, hI_mean_L: np.ndarray, delta_L: np.ndarray, k: int = 20) -> dict:
    import torch
    with torch.inference_mode():
        norm = model.model.norm
        W = model.lm_head
        x0 = torch.tensor(hI_mean_L, device="cuda", dtype=torch.bfloat16)[None, None]
        x1 = torch.tensor(hI_mean_L - delta_L, device="cuda", dtype=torch.bfloat16)[None, None]
        l0 = W(norm(x0)).float()[0, 0]
        l1 = W(norm(x1)).float()[0, 0]
        d = (l1 - l0).cpu().numpy()
    top = np.argsort(-d)[:k]
    bot = np.argsort(d)[:k]
    return {"promoted_by_minus_delta": [(tok.decode([int(i)]), float(d[i])) for i in top],
            "suppressed_by_minus_delta": [(tok.decode([int(i)]), float(d[i])) for i in bot]}


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=["base", "instruct"])
    ap.add_argument("--skip_gen", action="store_true")
    args = ap.parse_args()
    setup_logging(f"acts_{args.model}")
    import torch
    torch.cuda.set_per_process_memory_fraction(0.95)
    mid = MB if args.model == "base" else MI
    time_log(f"acts_{args.model}_start")
    t0 = time.time()
    prompts = load_prompts()
    tok, model = load_model(mid)
    logger.info(f"loaded {mid} in {time.time() - t0:.0f}s; layers={len(model.model.layers)}")
    rec = Recorder(model)
    # sanity: recorder index 36 must equal the pre-norm residual (differs from HF's normed last hidden state)
    for task in ("t1", "t2"):
        hR = run_R(model, chat_ids(prompts, task), rec)
        np.save(ACTS / f"{args.model}_{task}_R.npy", hR.astype(np.float16))
        logger.info(f"{task}: saved R activations {hR.shape}")
        if not args.skip_gen:
            items = gen_items(prompts, task, tok)
            if items:
                hg = run_gen(model, items, rec)
                np.save(ACTS / f"{args.model}_{task}_gen.npy", hg.astype(np.float16))
                logger.info(f"{task}: saved teacher-forced gen activations {hg.shape}")
    rec.remove()
    if args.model == "instruct":
        out = {"model_pair": [MB, MI], "band_layers": BAND, "tasks": {}}
        deltas = {}
        for task in ("t1", "t2"):
            hI = np.load(ACTS / f"instruct_{task}_R.npy").astype(np.float32)
            hB = np.load(ACTS / f"base_{task}_R.npy").astype(np.float32)
            gIp, gBp = ACTS / f"instruct_{task}_gen.npy", ACTS / f"base_{task}_gen.npy"
            gI = np.load(gIp).astype(np.float32) if gIp.exists() else None
            gB = np.load(gBp).astype(np.float32) if gBp.exists() else None
            dg = diagnostics(hI, hB, gI, gB)
            deltas[task] = dg["delta"]
            np.save(ACTS / f"delta_{task}.npy", dg["delta"].astype(np.float32))
            v = band_vectors(dg["delta"])
            np.save(ACTS / f"steer_{task}.npy", v)
            # cumulative check: sum of increments equals delta at each band layer
            cum = np.cumsum(v, axis=0)
            err = float(max(np.abs(cum[i] - dg["delta"][L + 1]).max() for i, L in enumerate(BAND)))
            ll = logit_lens(model, tok, hI[:, 29].mean(0), dg["delta"][29])
            out["tasks"][task] = {"per_layer": dg["per_layer"], "cumsum_max_abs_err": err, "logit_lens_L28": ll,
                                  "band_increment_norms": [float(np.linalg.norm(x)) for x in v]}
            logger.info(f"{task}: band vectors saved; cum err {err:.2e}; "
                        f"L18 split-half cos {dg['per_layer'][19]['split_half_cos']:.3f}, rel norm "
                        f"{dg['per_layer'][19]['rel_norm_delta']:.3f}")
        out["task_generality_cos"] = [{"index": l, "cos_delta_t1_t2": cos(deltas["t1"][l], deltas["t2"][l])}
                                      for l in range(N_LAYERS + 1)]
        # pooled direction (fallback 5)
        hI_all = np.concatenate([np.load(ACTS / f"instruct_{t}_R.npy").astype(np.float32) for t in ("t1", "t2")])
        hB_all = np.concatenate([np.load(ACTS / f"base_{t}_R.npy").astype(np.float32) for t in ("t1", "t2")])
        pooled = (hI_all - hB_all).mean(0)
        np.save(ACTS / "delta_pooled.npy", pooled.astype(np.float32))
        np.save(ACTS / "steer_pooled.npy", band_vectors(pooled))
        (RESULTS / "sharpening_direction.json").write_text(json.dumps(out, indent=1))
    # special-token embedding norms (STEP 2.5) for this model
    emb = model.model.embed_tokens.weight.detach().float()
    norms = emb.norm(dim=1)
    med = float(norms.median())
    st = {}
    for s in ["<|im_start|>", "<|im_end|>", "<think>", "</think>"]:
        i = tok.convert_tokens_to_ids(s)
        st[s] = {"id": int(i), "norm": float(norms[i]), "ratio_to_median": float(norms[i] / med),
                 "flag_untrained": bool(norms[i] < 0.2 * med)}
    (RESULTS / f"special_token_norms_{args.model}.json").write_text(json.dumps({"median_norm": med, "tokens": st}, indent=1))
    logger.info(f"special-token norms ({args.model}): {st}")
    del model
    gc.collect()
    time_log(f"acts_{args.model}_end", seconds=round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
