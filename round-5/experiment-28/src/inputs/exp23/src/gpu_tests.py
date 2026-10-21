#!/usr/bin/env python3
"""GPU unit tests U1-U4 and U6 (U5 is the tokenizer-only twin/ban alignment test in tests_cpu) on gemma for T03 W1
and T2 W1, plus a memory probe at the batch sizes and caps the design uses. Writes results/tests_gpu.json."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import BAND, CAPTURE_BLOCKS, QWEN_DEFAULT, RESULTS_DIR, setup_logging, write_json
import engine_gemma as EG
import prompts_gemma as PG
from push import block_hooks
from units import unit_n


def push_spec(B: int, alphas: list[float], dirs: list[np.ndarray | None], clean: dict[str, Any],
              n: dict[int, torch.Tensor]) -> dict[str, Any]:
    U = torch.zeros(B, EG.D_MODEL, dtype=torch.float32, device="cuda")
    for i, d in enumerate(dirs):
        if d is not None:
            U[i] = torch.tensor(d, device="cuda")
    return {"U": U, "alpha": torch.tensor(alphas, dtype=torch.float32, device="cuda"), "n": n,
            "h_ref": {l: clean["S"][l] for l in BAND}, "a": clean["a"], "b": clean["b"], "band": BAND}


@torch.no_grad()
def capture_block(model: Any, ids: list[int], B: int, blocks: list[int], push: dict | None) -> dict[int, torch.Tensor]:
    from push import make_push_edits

    got = {}

    def mk(l):
        def g(h):
            got[l] = h.float().clone()
        return g
    edits = make_push_edits(push["band"], push["a"], push["b"], push["U"], push["alpha"], push["n"],
                            push["h_ref"]) if push else {}
    inp = torch.tensor([ids], device="cuda").expand(B, -1).contiguous()
    with block_hooks(EG.layers(model), edits, {l: mk(l) for l in blocks}):
        model.model(input_ids=inp, use_cache=False)
    return got


def run_tests(tok: Any, model: Any, B: int = 8) -> dict[str, Any]:
    res: dict[str, Any] = {}
    for task in ("T03", "T2"):
        tw = PG.p_twin(task, QWEN_DEFAULT[task], "W1")
        ids, a, b = tw["ids"], tw["spec_start"], tw["spec_end"]
        clean = EG.clean_states(model, ids, a, b, CAPTURE_BLOCKS)
        n = unit_n(clean["S"])
        dirs = [None] * (B // 2) + [EG.seed_dir(9001 + i) for i in range(B - B // 2)]
        alphas = [0.0] * (B // 2) + [1.0 if i % 2 == 0 else 2.0 for i in range(B - B // 2)]
        ps = push_spec(B, alphas, dirs, clean, n)
        pre_push = EG.prefill_single(model, ids, B, push=ps, capture_ref=clean)
        pre_none = EG.prefill_single(model, ids, B, push=None)
        z = list(range(B // 2))
        u1 = bool(torch.equal(pre_push["logits"][z], pre_none["logits"][z]))
        # U2: blocks before the band identical; positions outside the spec identical at the first band block
        c_push = capture_block(model, ids, B, [BAND[0] - 1, BAND[0]], ps)
        c_none = capture_block(model, ids, B, [BAND[0] - 1, BAND[0]], None)
        u2a = bool(torch.equal(c_push[BAND[0] - 1], c_none[BAND[0] - 1]))
        outside = list(range(0, a)) + list(range(b, len(ids)))
        u2b = bool(torch.equal(c_push[BAND[0]][:, outside], c_none[BAND[0]][:, outside]))
        # U3: realised displacement along u equals alpha * n within 1% at every band block
        rel = pre_push["relerr_along"][B // 2:]
        u3 = float(rel.max())
        # realised displacement summary
        dS = pre_push["disp_S"]
        res[task] = {"U1_alpha0_bit_identical_logits": u1, "U2_pre_band_identical": u2a,
                     "U2_outside_spec_identical_at_first_band_block": u2b, "U3_max_rel_err_along_u": u3,
                     "U3_pass": u3 < 0.01, "disp_S_mean_alpha0": float(dS[:B // 2].mean()),
                     "disp_S_first_band_alpha1": float(dS[B // 2, 0]), "unit_n_mean_first_band": float(n[BAND[0]].mean()),
                     "unit_n_mean_last_band": float(n[BAND[-1]].mean()),
                     "residual_norm_mean_first_band": float(clean["S"][BAND[0]].norm(dim=-1).mean()),
                     "massive_top5_share": float(((clean["S"][BAND[6]] ** 2).topk(5, dim=-1).values.sum(-1)
                                                  / (clean["S"][BAND[6]] ** 2).sum(-1)).mean())}
        del pre_push, pre_none, c_push, c_none
        torch.cuda.empty_cache()
        # U4: CRN determinism -- slot 0 in two batches with different batch-mates, same B
        U = np.stack([EG.u_stream(task, "W1", k, n=96) for k in range(B)])
        temps = np.ones(B)
        preA = EG.prefill_single(model, ids, B, push=None)
        outA = EG.decode(model, tok, preA, U, temps, 96, fence_stop=False)
        U2 = U.copy()
        U2[1:] = np.stack([EG.u_stream(task, "W1", 100 + k, n=96) for k in range(1, B)])
        ps2 = push_spec(B, [0.0] + [1.0] * (B - 1), [None] + [EG.seed_dir(9001 + i) for i in range(B - 1)], clean, n)
        preB = EG.prefill_single(model, ids, B, push=ps2)
        outB = EG.decode(model, tok, preB, U2, temps, 96, fence_stop=False)
        res[task]["U4_crn_slot0_identical"] = outA[0]["token_ids"] == outB[0]["token_ids"]
        res[task]["U4_example_text"] = outA[0]["text"][:200]
        logger.info(f"{task}: {res[task]}")
        torch.cuda.empty_cache()
    return res


def speed_memory(tok: Any, model: Any, configs: list[tuple[str, int, int]]) -> dict[str, Any]:
    """U6: time per decode step and peak VRAM at (task, B, max_new) with fence stop off (worst case length)."""
    out = {}
    for task, B, max_new in configs:
        tw = PG.p_twin(task, QWEN_DEFAULT[task], "W1")
        torch.cuda.reset_peak_memory_stats()
        U = np.stack([EG.u_stream(task, "speed", k, n=max_new) for k in range(B)])
        pre = EG.prefill_single(model, tw["ids"], B, push=None)
        # allocate the full-length cache but decode only 128 steps (time per step at the start) ...
        t0 = time.time()
        res = EG.decode(model, tok, pre, U, np.ones(B), 128, fence_stop=False)
        dt = time.time() - t0
        # ... and probe the peak memory of a full-length buffer
        pre = EG.prefill_single(model, tw["ids"], B, push=None)
        from engine_gemma import build_prealloc

        cache = build_prealloc(pre["kv"], pre["P"] + max_new + 1)
        peak = torch.cuda.max_memory_allocated() / 1e9
        del cache, pre
        torch.cuda.empty_cache()
        out[f"{task}_B{B}_max{max_new}"] = {"ms_per_step_first128": 1000 * dt / 128, "peak_alloc_gb_full_buffer": peak,
                                           "P": tw["P"], "example": res[0]["text"][:120]}
        logger.info(f"U6 {task} B={B} max_new={max_new}: {1000 * dt / 128:.1f} ms/step, peak {peak:.2f} GB")
    return out


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("gpu_tests")
    tok, model, info = EG.load_model()
    res = {"model_info": info, "tests": run_tests(tok, model)}
    res["speed_memory"] = speed_memory(tok, model, [("T03", 36, 1024), ("T2", 24, 1536), ("T03", 24, 1024)])
    t = res["tests"]
    res["all_pass"] = all(v["U1_alpha0_bit_identical_logits"] and v["U2_pre_band_identical"]
                          and v["U2_outside_spec_identical_at_first_band_block"] and v["U3_pass"]
                          and v["U4_crn_slot0_identical"] for v in t.values())
    write_json(RESULTS_DIR / "tests_gpu.json", res)
    logger.info(f"GPU tests all_pass={res['all_pass']}")


if __name__ == "__main__":
    main()
