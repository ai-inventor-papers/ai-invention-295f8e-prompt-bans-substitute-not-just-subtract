#!/usr/bin/env python3
"""S0: recapture the bf16 fork states of Qwen3-8B and Qwen3-8B-Base on iteration 9's one-token path (prefix KV from
cmap9.prefix_kv, then a one-token forward of the fork token at a FIXED batch shape B_ot, row 0 read).

Per prompt and unit (T10, B3) it saves cache/fork_<model>_<unit>.pt with
  h_pre  [4096] bf16  input of model.model.norm at the fork (block-35 output)
  h_fin  [4096] bf16  last_hidden_state at the fork (final-normed)
  mlp_in / mlp_out [36, 4096] bf16  input / output of layers[l].mlp at the fork
  logits [151936] fp32  chunked h_fin.float() @ W[chunk].float().T (never a full fp32 copy of W)
plus the iteration-8 engine check (cmap9.check_margins on CHK_T10 / CHK_B3), a batch-shape sweep (numerics floor) and,
for the instruct model, the top-64 principal subspace of the final-normed residual over all prompt + opening positions
(the RAND_RESID null basis).

Usage: capture10.py qwen|qwen_base [max_prompts]   (one model per process; never two models on the GPU)
"""

from __future__ import annotations

import gc
import sys
import time
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg10 import (B_OT_CANDIDATES, CACHE_DIR, CHUNK_ROWS, I9_RES, N_LAYERS, RESID_PCS, RESULTS_DIR, UNITS_TF,
                   import_iter9, ledger, log_deviation, model_path, partial_status, read_json, setup_logging,
                   utc_now, write_json)

import_iter9()
import cmap9 as CM  # noqa: E402  (vendored iteration-9 engine: prefix_kv, build_cache, check_margins)


def load(which: str) -> tuple[Any, Any, dict[str, Any]]:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    t0 = time.time()
    path = model_path(which)
    tok = AutoTokenizer.from_pretrained(path)
    free0, _ = torch.cuda.mem_get_info(0)
    model = AutoModelForCausalLM.from_pretrained(path, dtype=torch.bfloat16, attn_implementation="sdpa",
                                                 device_map={"": 0}, low_cpu_mem_usage=True)
    model.eval()
    model.requires_grad_(False)
    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.set_per_process_memory_fraction(0.97, 0)
    free, _ = torch.cuda.mem_get_info(0)
    info = {"model": which, "snapshot": path.split("/")[-1], "load_s": round(time.time() - t0, 1),
            "free_vram_before_GB": round(free0 / 1e9, 2), "free_vram_after_GB": round(free / 1e9, 2),
            "gpu": torch.cuda.get_device_name(0), "tie_word_embeddings": bool(model.config.tie_word_embeddings),
            "rms_norm_eps": float(model.config.rms_norm_eps)}
    logger.info(f"loaded {which}: {info}")
    return model, tok, info


@torch.no_grad()
def full_logits(W: torch.Tensor, h: torch.Tensor) -> torch.Tensor:
    """fp32 logits h.float() @ W.float().T over the full vocabulary, CHUNK_ROWS rows at a time. h: [n, d]."""
    hf = h.float()
    out = torch.empty(hf.shape[0], W.shape[0], dtype=torch.float32, device=hf.device)
    for c in range(0, W.shape[0], CHUNK_ROWS):
        out[:, c:c + CHUNK_ROWS] = hf @ W[c:c + CHUNK_ROWS].float().T
    return out


def class_margin(z: torch.Tensor, D: list[int], A: list[int]) -> torch.Tensor:
    return torch.logsumexp(z[..., D], -1) - torch.logsumexp(z[..., A], -1)


@torch.no_grad()
def onetok_states(model: Any, ids: list[int], B: int, kv: list | None = None, want_mlp: bool = True
                  ) -> dict[str, torch.Tensor]:
    """Fork-position states on the one-token path at batch shape B (all rows unpatched; row 0 read)."""
    if kv is None:
        kv = CM.prefix_kv(model, ids)
    st: dict[str, Any] = {"mlp_in": {}, "mlp_out": {}}
    hs = []
    layers = model.model.layers

    def pre_norm(m, args, kwargs):
        x = args[0] if args else kwargs["hidden_states"]
        st["h_pre"] = x[0, -1].detach().to(torch.bfloat16).clone()

    def mlp_hook(l):
        def f(m, inp, out):
            st["mlp_in"][l] = inp[0][0, -1].detach().to(torch.bfloat16).clone()
            st["mlp_out"][l] = out[0, -1].detach().to(torch.bfloat16).clone()
        return f

    hs.append(model.model.norm.register_forward_pre_hook(pre_norm, with_kwargs=True))
    if want_mlp:
        for l in range(N_LAYERS):
            hs.append(layers[l].mlp.register_forward_hook(mlp_hook(l)))
    pos = len(ids) - 1
    try:
        cache = CM.build_cache(kv, B)
        o = model.model(input_ids=torch.full((B, 1), ids[-1], device="cuda", dtype=torch.long),
                        past_key_values=cache, position_ids=torch.full((B, 1), pos, device="cuda"),
                        cache_position=torch.tensor([pos], device="cuda"), use_cache=True)
    finally:
        for h in hs:
            h.remove()
    out = {"h_pre": st["h_pre"].cpu(), "h_fin": o.last_hidden_state[0, -1].detach().to(torch.bfloat16).cpu(),
           "rows_identical": bool(torch.equal(o.last_hidden_state[0, -1], o.last_hidden_state[-1, -1]))}
    if want_mlp:
        out["mlp_in"] = torch.stack([st["mlp_in"][l] for l in range(N_LAYERS)]).cpu()
        out["mlp_out"] = torch.stack([st["mlp_out"][l] for l in range(N_LAYERS)]).cpu()
    del o, cache
    return out


def pick_b_ot(model: Any, ids: list[int]) -> tuple[int, list[dict[str, Any]]]:
    tried = []
    for B in B_OT_CANDIDATES:
        try:
            torch.cuda.empty_cache()
            onetok_states(model, ids, B, want_mlp=False)
            free, _ = torch.cuda.mem_get_info(0)
            tried.append({"B": B, "ok": True, "free_after_GB": round(free / 1e9, 2)})
            return B, tried
        except torch.cuda.OutOfMemoryError:
            tried.append({"B": B, "ok": False})
            gc.collect()
            torch.cuda.empty_cache()
    raise RuntimeError("no one-token batch shape fits")


@torch.no_grad()
def resid_pca(model: Any, units: dict[str, Any], u: str, max_prompts: int | None) -> dict[str, Any]:
    """Top-64 principal subspace (centred) of the instruct final-normed residual over all prompt + opening positions
    of the unit's prompts (one full forward per prompt)."""
    f = units[u]["forks"][0]
    prompts = units[u]["prompts"][:max_prompts] if max_prompts else units[u]["prompts"]
    G = torch.zeros(4096, 4096, dtype=torch.float64)
    s = torch.zeros(4096, dtype=torch.float64)
    n = 0
    for p in prompts:
        ids = p["ids"] + f["opening"]
        o = model.model(input_ids=torch.tensor([ids], device="cuda"), use_cache=False)
        X = o.last_hidden_state[0].float().double()
        G += (X.T @ X).cpu()
        s += X.sum(0).cpu()
        n += X.shape[0]
        del o, X
    mu = s / n
    C = G / n - torch.outer(mu, mu)
    evals, evecs = torch.linalg.eigh(C)
    order = torch.argsort(evals, descending=True)
    evals, evecs = evals[order], evecs[:, order]
    V = evecs[:, :RESID_PCS].T.float().contiguous()          # [64, 4096] orthonormal rows
    return {"basis": V, "eigvals": evals[:RESID_PCS].float(), "mean": mu.float(), "n_positions": n,
            "var_explained_top64": float(evals[:RESID_PCS].sum() / evals.clamp_min(0).sum())}


@torch.no_grad()
def stage(which: str, max_prompts: int | None = None) -> None:
    t0 = time.time()
    tag = "instr" if which == "qwen" else "base"
    ledger(f"S0_capture_{tag}_start")
    model, tok, info = load(which)
    units = read_json(I9_RES / "units.json")
    W = model.lm_head.weight
    rec: dict[str, Any] = {"model": which, "load": info, "utc": utc_now()}
    # batch shape: the largest that fits for the longest unit (B3)
    U3 = units["B3"]
    B_ot, tried = pick_b_ot(model, U3["prompts"][0]["ids"] + U3["forks"][0]["opening"])
    rec["B_ot"] = B_ot
    rec["B_ot_tried"] = tried
    if B_ot != 40:
        log_deviation(f"B_ot_{tag}", f"one-token batch shape {B_ot} (iteration 9 used 40)")
    logger.info(f"B_ot = {B_ot} ({tried})")
    # iteration-8 engine check (base_subarm chat margins), exactly iteration 9's call shape
    try:
        rec["engine_check"] = CM.check_margins(model, tok, units, which)
    except (KeyError, FileNotFoundError, RuntimeError) as e:
        logger.error(f"engine check failed: {e}")
        rec["engine_check"] = {"error": str(e)}
    for u in UNITS_TF:
        U = units[u]
        f = U["forks"][0]
        prompts = U["prompts"][:max_prompts] if max_prompts else U["prompts"]
        caps = []
        for p in prompts:
            ids = p["ids"] + f["opening"]
            c = onetok_states(model, ids, B_ot)
            z = full_logits(W, c["h_fin"].cuda()[None])[0]
            c["logits"] = z.cpu()
            c["m"] = float(class_margin(z, f["D"], f["A"]))
            c["pid"] = p["pid"]
            c["template"] = p["template"]
            c["ids_sha"] = p["sha"]
            c["n_ids"] = len(ids)
            caps.append(c)
            logger.info(f"[{tag} {u}] {p['pid']}: m {c['m']:.4f} (rows identical {c['rows_identical']})")
        torch.save({"unit": u, "model": which, "B_ot": B_ot, "caps": caps}, CACHE_DIR / f"fork_{tag}_{u}.pt")
        rec[u] = [{"pid": c["pid"], "m": c["m"], "rows_identical": c["rows_identical"]} for c in caps]
        partial_status(f"S0_{tag}_{u}", n=len(caps), m_mean=float(np.mean([c["m"] for c in caps])))
        del caps
        gc.collect()
    # batch-shape sweep on 3 T10 prompts (numerics floor)
    f = units["T10"]["forks"][0]
    sweep = []
    for p in units["T10"]["prompts"][:3]:
        ids = p["ids"] + f["opening"]
        kv = CM.prefix_kv(model, ids)
        row = {"pid": p["pid"]}
        for B in sorted({1, 8, B_ot}):
            c = onetok_states(model, ids, B, kv=kv, want_mlp=False)
            row[f"m_B{B}"] = float(class_margin(full_logits(W, c["h_fin"].cuda()[None])[0], f["D"], f["A"]))
        sweep.append(row)
        del kv
    rec["batch_sweep_T10"] = sweep
    logger.info(f"batch sweep: {sweep}")
    # RAND_RESID basis (instruct only)
    if which == "qwen":
        for u in UNITS_TF:
            pca = resid_pca(model, units, u, max_prompts)
            torch.save(pca, CACHE_DIR / f"resid_pca_{u}.pt")
            rec[f"resid_pca_{u}"] = {"n_positions": pca["n_positions"],
                                     "var_explained_top64": pca["var_explained_top64"]}
            logger.info(f"resid PCA {u}: {pca['n_positions']} positions, top-64 explain "
                        f"{pca['var_explained_top64']:.3f}")
    rec["seconds"] = round(time.time() - t0, 1)
    write_json(RESULTS_DIR / f"capture_{tag}.json", rec)
    ledger(f"S0_capture_{tag}_end", seconds=rec["seconds"])


if __name__ == "__main__":
    setup_logging(f"capture10_{sys.argv[1]}")
    mp = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] != "all" else None
    stage(sys.argv[1], mp)
