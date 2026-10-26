#!/usr/bin/env python3
"""Iteration-4 constants for the same-seed 2x2: temperature vs plan noise (C1-seed), Qwen3-8B.

Builds on exp17's src/cfg.py (copied verbatim next to this file; its ROOT is this workspace). Conventions:
- SEED (the replication unit) = slot (task, template w, k), w in W1-W5, k in 0-3 -> 20 seeds per task. Its token noise is
  u_stream(task, w, k) (PCG64 uniforms, inverse-CDF coupling) or, for the Gumbel replicate, a per-row CUDA generator
  seeded with stable_seed(task, w, k, 'gumbel') (exponential race = Gumbel-max coupling).
- CONDITION strings (the `arm` field of every row): NOPN_T<t>, TOPK10_T0.7, FILLER_T1.0, PN_D<seed>_a<alpha>_T<t>,
  EC_NEUTRAL_T1.0 / EC_RAND<seed>_a1.0_T1.0 (engine check), GB_* (Gumbel replicate), MINP_T2.0, TPN_* (thinking-on PN
  probe), THINK_T<t> / THINK_REP_T0.7 (vLLM thinking on), FP8X_T1.0 (vLLM FP8 cross-check), SMOKE_* (never analysed).
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Any

from loguru import logger

from cfg import ROOT  # noqa: F401  (re-exported)

RUN_DIR = Path(os.environ.get("AII_RUN_DIR", str(ROOT.parents[3])))   # the run volume (inputs are copied from it)
ITER3 = RUN_DIR / "." / "round-3" / "."
ITER2 = RUN_DIR / "." / "round-2" / "."
ITER4 = RUN_DIR / "." / "round-4" / "."
DEP_DATASET = RUN_DIR.parent / "run_4VFKidE1bxPG" / "." / "round-1" / "." / "dataset-1/src"

TASKS4 = ("T2", "T03", "T1")                       # sampling order (plan S7)
DEFAULT4 = {"T1": "bfs", "T2": "dijkstra", "T03": "full_sort"}
TEMPS = (0.3, 0.7, 1.0, 1.3)
TOPK_T, TOPK_K = 0.7, 10
PN_TEMPS = (0.7, 1.0)
PN_ALPHAS = (1.0, 2.0)
PN_SEEDS = (46001, 46002, 46003, 46004, 46005, 46006)   # D1-D6 (collision check in S0)
SEED_K = (0, 1, 2, 3)
MAX_NEW4 = {"T03": 1024, "T1": 1536, "T2": 1536}
MINP_T, MINP_P = 2.0, 0.1
TPN_MAX_NEW = 2048                                 # optional arm (ii): thinking-on PN probe cap
TPN_T, TPN_ALPHA = 0.7, 2.0
THINK_CAP = 16384
ANSWER_MAX = 1536
MAX_MODEL_LEN = 18432
THINK_START = 151667
THINK_END = 151668
EARLY_EXIT = ("\n\nConsidering the limited time by the user, I have to give the solution based on the thinking "
              "directly now.\n</think>\n\n")
FP8_MODEL_ID = "Qwen/Qwen3-8B-FP8"
FP8_REVISION = "220b46e3b2180893580a4454f21f22d3ebb187d3"
KV_BYTES_PER_TOKEN = 147_456                       # 36 layers x 8 KV heads x 128 x 2 (K,V) x 2 bytes
JUDGE_CAP_TOTAL = 0.30
LEXICON_CAP, NOVELTY_CAP, SPEND_CAP = 0.10, 0.10, 0.50
C1_EVENT_SET = ["T03", "T05", "T06", "T10", "T1", "T2"]   # frozen C1 event set, recorded verbatim (plan S1)

# first approach named in a thinking trace (case-insensitive earliest match); order = priority on ties
FIRST_APPROACH_LEXICON = [
    ("dijkstra", r"dijkstra"),
    ("bellman_ford", r"bellman[- ]?ford"),
    ("spfa", r"spfa|shortest path faster"),
    ("floyd_warshall", r"floyd|warshall"),
    ("a_star", r"a-star|astar|(?<![A-Za-z0-9_])A\*"),
    ("bidirectional", r"bidirectional"),
    ("dial_bucket", r"(?<![a-z])dial(?![a-z])|bucket"),
    ("bfs", r"(?<![a-z])bfs(?![a-z])|breadth[- ]first"),
    ("dfs", r"(?<![a-z])dfs(?![a-z])|depth[- ]first"),
    ("topological_dag", r"topolog|(?<![a-z])dag(?![a-z])"),
]


def fmt_t(t: float) -> str:
    return f"{float(t):.1f}"


def cond_nopn(t: float) -> str:
    return f"NOPN_T{fmt_t(t)}"


def cond_pn(seed: int, alpha: float, t: float) -> str:
    return f"PN_D{seed}_a{float(alpha):.1f}_T{fmt_t(t)}"


def parse_cond(arm: str) -> dict[str, Any]:
    """CONDITION string -> {family, T, top_k, min_p, dir_seed, alpha, coupling, thinking, repeat}."""
    out: dict[str, Any] = {"arm": arm, "family": None, "T": None, "top_k": 0, "min_p": 0.0, "dir_seed": None,
                           "alpha": None, "coupling": "invcdf", "thinking": False, "repeat": False}
    a = arm
    if a.startswith("GB_"):
        out["coupling"] = "gumbel"
        a = a[3:]
    if a.startswith("TPN_"):
        out["thinking"] = True
        a = a[4:]
    parts = a.split("_")
    tpart = [p for p in parts if p.startswith("T") and p[1:].replace(".", "").isdigit()]
    if tpart:
        out["T"] = float(tpart[-1][1:])
    if a.startswith("NOPN"):
        out["family"] = "nopn"
    elif a.startswith("TOPK10"):
        out["family"], out["top_k"] = "topk", TOPK_K
    elif a.startswith("FILLER"):
        out["family"], out["repeat"] = "nopn", True
    elif a.startswith("MINP"):
        out["family"], out["min_p"] = "minp", MINP_P
    elif a.startswith("PN_D"):
        out["family"] = "pn"
        out["dir_seed"] = int(parts[1][1:])
        out["alpha"] = float(parts[2][1:])
    elif a.startswith("EC_NEUTRAL"):
        out["family"] = "ec_neutral"
    elif a.startswith("EC_RAND"):
        out["family"] = "ec_rand"
        out["dir_seed"] = int(parts[1][4:])
        out["alpha"] = float(parts[2][1:])
    elif a.startswith("THINK_REP"):
        out["family"], out["thinking"], out["repeat"], out["coupling"] = "think", True, True, "exp_race_vllm"
    elif a.startswith("THINK"):
        out["family"], out["thinking"], out["coupling"] = "think", True, "exp_race_vllm"
    elif a.startswith("FP8X"):
        out["family"], out["coupling"] = "fp8x", "exp_race_vllm"
    elif a.startswith("SMOKE"):
        out["family"] = "smoke"
    return out


class MemWatch:
    """cgroup-v1/v2 RAM watchdog for GPU processes (RLIMIT_AS breaks CUDA's address-space reservations): logs usage
    and hard-exits the process before the container limit would OOM-kill everything on the box."""

    def __init__(self, limit_gb: float = 26.0, every_s: float = 5.0):
        self.limit = limit_gb * 1e9
        self.every = every_s
        self.peak = 0.0
        self._stop = threading.Event()

    @staticmethod
    def usage() -> float:
        """Working set = usage - inactive file cache (page cache is reclaimed before an OOM kill; reading the
        checkpoints from network storage fills it with ~20 GB of reclaimable pages)."""
        for p, stat, key in (("/sys/fs/cgroup/memory/memory.usage_in_bytes", "/sys/fs/cgroup/memory/memory.stat",
                              "total_inactive_file"),
                             ("/sys/fs/cgroup/memory.current", "/sys/fs/cgroup/memory.stat", "inactive_file")):
            try:
                u = float(Path(p).read_text().strip())
            except (FileNotFoundError, ValueError):
                continue
            inactive = 0.0
            try:
                for line in Path(stat).read_text().splitlines():
                    k, v = line.split()
                    if k == key:
                        inactive = float(v)
                        break
            except (FileNotFoundError, ValueError):
                pass
            return max(0.0, u - inactive)
        return 0.0

    def _run(self) -> None:
        while not self._stop.wait(self.every):
            u = self.usage()
            self.peak = max(self.peak, u)
            if u > self.limit:
                logger.error(f"container RAM {u / 1e9:.1f} GB > {self.limit / 1e9:.1f} GB: aborting process")
                os._exit(3)

    def start(self) -> "MemWatch":
        threading.Thread(target=self._run, daemon=True).start()
        return self

    def stop(self) -> None:
        self._stop.set()


def wall_guard(t0_file: Path) -> float:
    """Seconds elapsed since the module's t0 (results/t0.json written at setup)."""
    import json
    try:
        t0 = json.loads(t0_file.read_text())["t0_unix"]
    except (FileNotFoundError, KeyError, ValueError):
        return 0.0
    return time.time() - t0
