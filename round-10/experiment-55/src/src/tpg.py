#!/usr/bin/env python3
"""TP-G shared constants and helpers (iteration 9, gen_plan_experiment_2_idx3).

Everything that is frozen for this artifact lives here: the banned / non-banned split, the model pins, the block
ranges, the verdict settings, the budget, and the absolute locations of the prior artifacts that Stage -1 copies into
inputs/ (read once, never written). The iteration-8 modules (common, prompts_tp, states, geometry, landing, label_tp,
sample_or) are byte-identical copies of art_R-HSmXq2t97f src/ and are imported unchanged; their ROOT resolves to this
artifact's folder because they sit one level below it.
"""

from __future__ import annotations

import os
from pathlib import Path

from common import (CANON_ORDER, CONFIGS, DATA, FIGS, LOGS, PRED, RESULTS, ROOT, STATES, read_json,  # noqa: F401
                    utc_now, write_json)

# ---------------------------------------------------------------------------------------------- catalogue split
B5 = ["bfs", "dfs", "iddfs", "astar", "gbfs"]                       # banned (iteration-8 C6 top five)
NB5 = ["bibfs", "biastar", "idastar", "jps", "dijkstra_unit"]       # non-banned
UDIJ = "dijkstra_unit"
assert set(B5) | set(NB5) == set(CANON_ORDER)

# ---------------------------------------------------------------------------------------------- prior artifacts
# [iteration 10 portability edit: the absolute server defaults of iteration 9 were replaced by sibling folders named
#  by artifact id; these five constants are not used by the iteration-10 pipeline]
RUN0 = ROOT.parent
E44 = Path(os.environ.get("TPG_E44", str(RUN0 / "art_R-HSmXq2t97f")))
EXP9 = Path(os.environ.get("TPG_EXP9", str(RUN0 / "art_IVZc3TWCeE9f")))
EXP2 = Path(os.environ.get("TPG_EXP2", str(RUN0 / "art_D6Z0Snf09sFL")))
EXP8 = Path(os.environ.get("TPG_EXP8", str(RUN0 / "art_8_ULPE8jJQc_")))
DSET = Path(os.environ.get("TPG_DSET", str(RUN0 / "art_j3Rm_lr2nzR6")))
ARTIFACT_IDS = {"E44": "art_R-HSmXq2t97f", "EXP9": "art_IVZc3TWCeE9f", "EXP2": "art_D6Z0Snf09sFL",
                "EXP8": "art_8_ULPE8jJQc_", "DSET": "art_j3Rm_lr2nzR6"}

INPUTS = ROOT / "inputs"
IN_E44 = INPUTS / "e44"
STATES_DIR = STATES                      # cache/states (kept on the run volume)

# ---------------------------------------------------------------------------------------------- models
M32 = {"repo": "unsloth/Qwen3-32B-bnb-4bit", "revision": "7f721e74a6a8cc9ee352f7e49303a2c1705f9083",
       "precision": "nf4", "n_layers": 64, "n_keep": 48, "ext_blocks": list(range(17, 48)),
       "sel_blocks": list(range(19, 46)), "tag": "32b", "engine": "hf-nf4-truncated", "ref_block": 31}
M8 = {"repo": "Qwen/Qwen3-8B", "revision": "b968826d9c46dd6066d109eabc6255188de91218", "precision": "bf16",
      "n_layers": 36, "n_keep": 29, "ext_blocks": list(range(8, 29)), "sel_blocks": list(range(10, 27)),
      "tag": "8b", "engine": "hf-bf16-truncated", "ref_block": 17}
MODELS = {"32b": M32, "8b": M8}

# ---------------------------------------------------------------------------------------------- frozen settings
KS = (5, 10, 15)
K_VERDICT = 15                       # iteration 8's primary k (k 10 is the committed second verdict setting)
K_SECOND = 10
N_BOOT_32B = 1000
N_BOOT_OTHER = 200
OR_CAP_USD = float(os.environ.get("TPG_OR_CAP", "0.40"))
TOPUP_STOP_USD = 0.32
OR_MODEL = "qwen/qwen3-32b"
OR_PIN = {"order": ["DeepInfra"], "allow_fallbacks": False, "quantizations": ["fp8"]}
NAMING_N = 20
NAMING_PASS = 16
TOPUP_TARGET = 24
TOPUP_MAX_ATTEMPTS = 60
MCODE_PER_ALG = 20
MCODE_MIN = 10
LOO_GATE = 0.70
REPRO_GATE = 0.95
RELIABILITY_FLAG = 0.70
SEED = 9009

# Survivors of iteration 8 (C6, Qwen3-32B thinking on): label-level landing input (landing.json / confirmation.json).
SURV_SCREEN = [UDIJ] * 6
SURV_CONFIRM = [UDIJ] * 9


def forced_rates_e44() -> dict[str, float]:
    """Correct-when-forced rates recovered from iteration 8's null_C_probs (p - 0.5/40)."""
    land = read_json(IN_E44 / "results" / "landing.json")
    probs = land["primary"]["null_C_probs"]
    return {a: max(0.0, float(p) - 0.0125) for a, p in probs.items()}


def rel(p: Path) -> str:
    return str(Path(p).resolve().relative_to(ROOT))
