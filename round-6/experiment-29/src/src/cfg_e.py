#!/usr/bin/env python3
"""Constants of artifact E (iteration 6): did 8-bit arithmetic cause the plan-noise effect?

Everything iteration 4 (exp19) held fixed is held fixed here -- prompts, per-sample plan-noise seeds, exp22's 40 fixed
directions, the logged ban units n[l,p], exp19's hook code (hooks.make_edits 'RAND'), the inverse-CDF CRN streams
u_stream(task, w, k) and the 1,024-token cap. Only the arithmetic precision of the decoder linears varies:

  W8A8    e4m3 weights (per output channel) x e4m3 activations (per row)    EMU backend (the factorial's FP8 backend)
  W8A16   e4m3 weights x bf16 activations                                   EMU backend
  W16A8   bf16 weights x e4m3 activations                                   EMU backend
  W16A16  bf16 weights x bf16 activations, HF native nn.Linear              the iteration-5 engine
  W16A16mm  bf16 x bf16 through the EMU GEMM path, quantisers off           kernel-only floor (readouts and U6 only)
  W8A8REAL  exp19's FP8Linear unchanged (torch._scaled_mm, cuBLASLt)        sm_89+ only: engine check / REAL cell

exp19's modules (cfg, engine_v4, hooks, sampling_v4, prompts_v4, label_worker_v4, commit) are copied unchanged into
src/ and imported from there; this file only adds the artifact's own constants.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cfg import (DATA_DIR, INPUTS, LOG_DIR, MODEL_ID, MODEL_REVISION, PRED_DIR, RESULTS_DIR, ROOT, V_BLOCKS,
                 stable_seed)

FIG_DIR = ROOT / "figures"
STATES_DIR = ROOT / "states"
for _d in (FIG_DIR, STATES_DIR):
    _d.mkdir(parents=True, exist_ok=True)

E19 = INPUTS / "exp19"
E22 = INPUTS / "exp22"
E23 = INPUTS / "exp23"
E24 = INPUTS / "exp24"
E25 = INPUTS / "exp25"
E27 = INPUTS / "exp27"
E18 = INPUTS / "exp18"

RAW_E = DATA_DIR / "samples_raw.jsonl"        # one row per generated program (token ids + text)
LABELS_E = DATA_DIR / "labels.jsonl"          # one label row per sample_id
SAMPLES_E = DATA_DIR / "samples.jsonl"        # merged per-row output (plan PER-ROW OUTPUT), no token ids
REALISED_E = DATA_DIR / "realised.jsonl"      # realised displacement per pushed prefill
TIMING_E = RESULTS_DIR / "timing_batches.jsonl"
COMMIT_LOG = ROOT / "commitments.log"

TASKS_DEC = ("T10", "T2")          # decisive tasks
TASK_CTRL = "T03"                  # positive control
TASKS_E = ("T2", "T10", "T03")     # generation order (T2 first: it holds the gate)
DEFAULT_E = {"T10": "union_find", "T2": "dijkstra", "T03": "full_sort"}

PRECISIONS = ("W8A8", "W8A16", "W16A8", "W16A16")
FAMILY = {"W8A8": "W8", "W8A16": "W8", "W16A8": "W16", "W16A16": "W16", "W16A16mm": "W16", "W8A8REAL": "REAL"}
ENGINE_VARIANT = {"W8A8": "EMU", "W8A16": "EMU", "W16A8": "EMU", "W16A16": "native", "W16A16mm": "mm32",
                  "W8A8REAL": "REAL"}
GEMM_BACKEND = {
    "EMU": "torch.mm(bf16 operands holding exact e4m3 values, out_dtype=float32) * fp32 scales -> one bf16 cast",
    "native": "torch.nn.Linear bf16 (cuBLAS, bf16 out)",
    "mm32": "torch.mm(bf16, out_dtype=float32) -> one bf16 cast (quantisers off)",
    "REAL": "torch._scaled_mm float8_e4m3fn x float8_e4m3fn (cuBLASLt rowwise scales) -> bf16",
}
QUANT_DESC = {
    "W8A8": "e4m3 weights per output channel (s=absmax/448) x e4m3 activations per row (xs=absmax/448)",
    "W8A16": "e4m3 weights per output channel x bf16 activations",
    "W16A8": "bf16 weights x e4m3 activations per row",
    "W16A16": "bf16 weights x bf16 activations",
    "W16A16mm": "bf16 weights x bf16 activations (EMU GEMM path)",
    "W8A8REAL": "exp19 FP8Linear: e4m3 weights per output channel x e4m3 activations per row, _scaled_mm",
}

ALPHA_PN = {"PN_a0.5": 0.5, "PN_a1": 1.0, "PN_a2": 2.0}
POP_SEEDS = list(range(9101, 9141))     # exp22's 40 fresh directions (exp17 construction)
POP_ALPHA = 2.0
N_DITHER_DECODE = 32                    # dither variant (ii): first 32 decode steps
DITHER_BLOCKS = list(range(12, 36))     # dither blocks 12-35
K10 = list(range(10))
B_DEFAULT = 20                          # exp19's batch shape; the memory probe may lower it (device rule)

# 15-point landing rule and the base runner-up expected from exp24 (verified at Stage A, never assumed)
EXPECTED_RUNNER_UP = {"T10": "dfs", "T2": "bellman_ford_spfa", "T03": "quickselect"}
HOLM_ALPHA_SMALLEST = 0.0125            # 4-claim Holm threshold of the iteration's primary family
N_BOOT_E = 2000
BOOT_SEED_E = 20261021
JUDGE_CAP_USD_E = 0.50
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
CHECKPOINT = f"{MODEL_ID}@{MODEL_REVISION}"

# iteration-4 summary counts quoted in the plan (used only if exp19's rows are unavailable: fallback F6)
PLAN_ITER4_COUNTS = {("T10", "PN_a2"): 30, ("T2", "PN_a2"): 27, ("T10", "PN_a1"): 6, ("T2", "PN_a1"): 13,
                     ("T03", "PN_a2"): 25, ("T03", "PN_a1"): 14}


def arm_def(arm: str) -> dict[str, Any]:
    """Decode an arm name into its intervention. Names:
    TWIN | PN_a{0.5,1,2} (per-sample direction, ban unit) | POP_d{seed}_a2.0 (exp22 fixed direction, ban unit) |
    PNF_a{1,2} (PN seeds of PN_a1/PN_a2 at the ban-free unit) | DITHER_TWIN_v{1,2} | DITHER_PN2_v{1,2}."""
    if arm == "TWIN":
        return {"kind": "clean", "alpha": None, "unit": None, "dither": None}
    if arm in ALPHA_PN:
        return {"kind": "pn", "alpha": ALPHA_PN[arm], "seed_arm": arm, "unit": "ban", "dither": None}
    if arm.startswith("POP_d"):
        seed = int(arm.split("_")[1][1:])
        alpha = float(arm.split("_a")[1])
        return {"kind": "pop", "alpha": alpha, "dir_seed": seed, "unit": "ban", "dither": None}
    if arm.startswith("PNF_a"):
        a = arm.split("_a")[1]
        return {"kind": "pn", "alpha": float(a), "seed_arm": f"PN_a{a}", "unit": "banfree", "dither": None}
    if arm.startswith("IT5_a"):        # POST-HOC (not pre-registered): exp27's exact PN5 seeds + per-template ban-free unit
        return {"kind": "pn5", "alpha": float(arm.split("_a")[1]), "unit": "banfree_template", "dither": None}
    if arm.startswith("DITHER_TWIN_v"):
        return {"kind": "clean", "alpha": None, "unit": None, "dither": int(arm[-1]), "per_row_prefill": True}
    if arm.startswith("DITHER_PN2_v"):
        return {"kind": "pn", "alpha": 2.0, "seed_arm": "PN_a2", "unit": "ban", "dither": int(arm[-1])}
    raise ValueError(arm)


def pop_arm(seed: int, alpha: float = POP_ALPHA) -> str:
    return f"POP_d{seed}_a{alpha}"


def sample_id(task: str, precision: str, arm: str, w: str, k: int) -> str:
    return f"{task}|{precision}|{arm}|{w}|{k}"


def crn_seed(task: str, w: str, k: int) -> int:
    return stable_seed(task, w, k)


def write_json_e(p: Path, obj: Any) -> None:
    from cfg import write_json

    write_json(p, obj)


def load_json(p: Path) -> Any:
    return json.loads(Path(p).read_text())


__all__ = ["V_BLOCKS", "LOG_DIR", "PRED_DIR"]
