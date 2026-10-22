#!/usr/bin/env python3
"""Iteration-6 constants: where in the prompt the algorithm is chosen (bf16 Qwen3-8B on a 16 GB RTX 2000 Ada).

Builds on exp27's src/cfg.py (vendored byte-for-byte next to this file; ROOT = this workspace, INPUTS = inputs/,
a byte copy of exp27's inputs/ folder). Conventions added here:

- CRN slot s (0-49) of a task maps to (template w, stream index k) by SLOT_MAP; its uniform stream is exp27's
  u_stream(task, w, k, n=1536), so slots with k <= 9 pair with exp27's TWIN rows slot for slot.
- dir_seed(task, site, alpha, slot) = int(sha256('iter6_dir3|task|site|alpha|slot')[:8], 16): one fresh isotropic
  direction per sample (PCG64 normal, normalised), shared across the hooked blocks and positions of that sample.
- Bands are BLOCK OUTPUTS (exp13 band-patch convention): block l's output is HF hidden_states[l + 1].
- Positions: SPEC = [p1, spec_end) from the first 'Task:' token to the last user token; COND = the token span where the
  ban and its length-matched neutral twin differ; R = P - 1 (the read position).
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

import numpy as np

from cfg import D_MODEL, INPUTS, PRED_DIR, RESULTS_DIR, ROOT, read_json

# ------------------------------------------------------------------------------------------------ prior artifacts
# Inputs of other artifacts are read through ONE relative constant each (env vars override them):
# - the declared dataset dependency art_j3Rm_lr2nzR6: ART_J3RM_DIR, else the sibling folder ../art_j3Rm_lr2nzR6 of the
#   published repository, else the run layout on the original server (only data/dep_extract.json is needed to rerun;
#   it is published here);
# - the read-only prior artifacts of iterations 2-5 (run run_aRfWvcSWjssb): every file this code reads is mirrored
#   byte-for-byte in inputs/ (exp27's inputs copy) and inputs_extra/expN/; AII_PRIOR_LOOP points at the original
#   <run>/3_invention_loop folder, used only by the STEP-0 availability gate.
RUNS_DIR = ROOT.parents[4]
PRIOR_RUN = Path(os.environ.get("AII_PRIOR_LOOP", RUNS_DIR / "run_aRfWvcSWjssb" / "."))
ITER = {i: PRIOR_RUN / f"iter_{i}" / "." for i in (2, 3, 4, 5)}
_DEP_SIBLING = ROOT.parent / "art_j3Rm_lr2nzR6"
DEP_DIR = Path(os.environ.get("ART_J3RM_DIR") or (_DEP_SIBLING if _DEP_SIBLING.exists() else
                                                  RUNS_DIR / "run_4VFKidE1bxPG" / "." / "round-1" /
                                                  "." / "gen_art_dataset_1"))
_EXP_ITER = {8: 2, 11: 2, 7: 2, 13: 3, 16: 3, 18: 3, 19: 4, 20: 4, 22: 4, 23: 4, 25: 5, 26: 5, 27: 5, 28: 5}
EXP_ORIG = {n: ITER[i] / f"gen_art_experiment_{n}" for n, i in _EXP_ITER.items()}   # original locations (gate only)
EXP = {n: (ROOT / "inputs_extra" / f"exp{n}" if (ROOT / "inputs_extra" / f"exp{n}").exists() else EXP_ORIG[n])
       for n in _EXP_ITER}                                                           # workspace mirrors first
VENDOR = ROOT / "src" / "vendor"
PROMPTS6 = ROOT / "prompts" / "prompts6.jsonl"
POSITIONS = ROOT / "prompts" / "positions.json"
SAMPLES = ROOT / "data" / "samples_raw.jsonl"
LABELS = ROOT / "data" / "labels.jsonl"
STATES_DIR = ROOT / "cache"
COMMITS = ROOT / "commitments.log"

# ------------------------------------------------------------------------------------------------ tasks
TASKS6 = ("T03", "T10", "T2", "T05", "T06", "T1")
BENCH6 = ("T03", "T10", "T05", "T06")
PATH6 = ("T1", "T2")
ST_TASKS = ("T03", "T10")
DEFAULT6 = {"T03": "full_sort", "T10": "union_find", "T2": "dijkstra", "T05": "hash_map", "T06": "hash_set",
            "T1": "bfs"}
# Y = the recorded substitute the full ban lands on (frozen in commit #0 from iterations 2-5); T2 Bellman-Ford/SPFA
# carries the exp8 suite label "bf_spfa"
Y6 = {"T2": "bf_spfa", "T03": "quickselect", "T10": "bfs", "T1": "dfs", "T05": "brute_force",
      "T06": "index_marking"}
# route classes of iterations 2-3 (bf16 route arms c/d): prompt route (the ban is read into the task-spec states)
# versus direct route (generated tokens read the condition span)
ROUTE_CLASS = {"T2": "prompt", "T03": "prompt", "T10": "prompt", "T1": "prompt", "T05": "direct", "T06": "direct"}
TEMPLATES6 = ("W1", "W2", "W3", "W5")
EXP8_TASK6 = {"T1": "t1", "T2": "t2"}

# ------------------------------------------------------------------------------------------------ slots
_SLOT_SPEC = [("W1", range(0, 8)), ("W2", range(0, 8)), ("W3", range(0, 7)), ("W5", range(0, 7)),     # 0-29
              ("W1", range(8, 10)), ("W2", range(8, 10)), ("W3", range(7, 10)), ("W5", range(7, 10)),  # 30-39
              ("W1", range(10, 13)), ("W2", range(10, 13)), ("W3", range(10, 12)), ("W5", range(10, 12))]  # 40-49
SLOT_MAP: list[tuple[str, int]] = [(w, k) for w, ks in _SLOT_SPEC for k in ks]
assert len(SLOT_MAP) == 50 and len(set(SLOT_MAP)) == 50
SLOT_MAP += [("W4", k) for k in range(10)]  # slots 50-59: the W4 template, reported separately (extension)
N_W4 = tuple(range(50, 60))
SLOT_OF = {wk: s for s, wk in enumerate(SLOT_MAP)}
N30 = tuple(range(30))
N50 = tuple(range(50))

# ------------------------------------------------------------------------------------------------ engine
N_LAYERS6 = 36
ALL_BLOCKS = list(range(N_LAYERS6))
BANDS = {"0-11": list(range(0, 12)), "12-23": list(range(12, 24)), "24-35": list(range(24, 36)),
         "0-35": list(range(0, 36))}
LOG_BLOCKS = list(range(12, 36))           # realised displacement logged at blocks 12-35
MAX_NEW6 = {"T03": 384, "T10": 384, "T05": 384, "T06": 384, "T2": 512, "T1": 640}
BATCH6 = {"T03": 10, "T10": 10, "T05": 10, "T06": 10, "T2": 8, "T1": 6}   # fixed per task family (GEMM shapes)
PRECISION6 = "bf16"
ENGINE6 = "hf_bf16_cpu_embed"

# ------------------------------------------------------------------------------------------------ ST grid
SITES = ("S0", "S4", "S5", "S1", "S2", "S3")
SITE_BLOCKS6 = {"S0": list(range(12, 24)), "S4": list(range(0, 12)), "S5": list(range(24, 36)),
                "S1": list(range(12, 24)), "S2": list(range(12, 24)), "S3": list(range(12, 24)),
                "S1E": list(range(12, 24)), "S2E": list(range(12, 24)), "TOP5": list(range(12, 24))}
SITE_POS6 = {"S0": "S", "S4": "S", "S5": "S", "S1": "R", "S2": "COND", "S3": "GEN", "S1E": "R", "S2E": "COND",
             "TOP5": "S"}
PREFILL_SITES = ("S0", "S4", "S5", "S1", "S2", "S1E", "S2E")
ST_ALPHAS = (1.0, 2.0, 4.0, 8.0)
S3_STEPS6 = 32
DMD_STEPS6 = 32
DMD_T_CAP = 3.0
DMD_TOL = 0.10
D_OFFSET = 1e-3

# ------------------------------------------------------------------------------------------------ OpenRouter
JUDGE_CAP_LABELS = 0.60
JUDGE_CAP_NOVELTY = 0.15
BUDGET_MSG6 = "AI Inventor per-run OpenRouter budget"


def dir_seed(task: str, site: str, alpha: float | str, slot: int) -> int:
    s = "iter6_dir3|" + task + "|" + site + "|" + str(alpha) + "|" + str(slot)
    return int(hashlib.sha256(s.encode()).hexdigest()[:8], 16)


def unit_dir(seed: int, n: int = D_MODEL) -> np.ndarray:
    x = np.random.Generator(np.random.PCG64(seed)).standard_normal(n)
    return (x / np.linalg.norm(x)).astype(np.float32)


def r_q_table() -> tuple[np.ndarray, np.ndarray]:
    q = read_json(INPUTS / "exp23" / "results" / "qwen_ratio.json")["r_Q"]
    d = np.array([v["depth"] for v in q.values()])
    r = np.array([v["median"] for v in q.values()])
    o = np.argsort(d)
    return d[o], r[o]


_RQ: dict[str, Any] = {}


def r_at(l: int) -> float:
    """exp27 cfg5/gen5 r_Q interpolation over relative depth (block l -> (l + 1) / 36)."""
    if "t" not in _RQ:
        _RQ["t"] = r_q_table()
    d, r = _RQ["t"]
    return float(np.interp((l + 1) / 36, d, r))


def sample_id(task: str, arm: str, slot: int) -> str:
    w, k = SLOT_MAP[slot]
    return f"{task}|{arm}|{w}|{k}"


def max_new6(task: str) -> int:
    return MAX_NEW6[task]


def fence6(task: str) -> str:
    return "path" if task in PATH6 else "bench"


def hardware_file() -> Path:
    return PRED_DIR / "hardware.json"


def results(name: str) -> Path:
    return RESULTS_DIR / name
