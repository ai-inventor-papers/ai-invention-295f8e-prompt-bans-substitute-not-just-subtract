#!/usr/bin/env python3
"""Shared paths, IO helpers, harmonisation maps and interval statistics for the round-one audit.

Inputs are the six iteration-1 experiment workspaces, read in place (read-only). Their root is taken from the
ITER1_ROOT environment variable, else resolved relative to this file (sibling run on the same volume), so no
absolute server path is written into any published file. Sources are cited as expN/<relative path>.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from loguru import logger
from scipy import stats

HERE = Path(__file__).resolve().parent
_RUNS = HERE.parents[4]  # .../runs
ITER1_ROOT = Path(os.environ.get("ITER1_ROOT", _RUNS / "run_4VFKidE1bxPG" / "." / "round-1" / "."))
EXP = {f"exp{i}": ITER1_ROOT / f"gen_art_experiment_{i}" for i in range(1, 7)}
EXP_ROLE = {"exp1": "association", "exp2": "geometry", "exp3": "forking_token", "exp4": "decommitment",
            "exp5": "instruction_tuning", "exp6": "decoding"}
EXP_ART = {"exp1": "art__skdlFp_o3e9", "exp2": "art_D6Z0Snf09sFL", "exp3": "art_1yV2vQ0EH4OY",
           "exp4": "art_U5UKkFrOgSsE", "exp5": "art_HF8nK8B_Lqyy", "exp6": "art_UoCVh2Qe5RZ0"}
TOKENIZER_GLOB = "run_4VFKidE1bxPG/.shared_cache/hf/hub/models--Qwen--Qwen3-8B/snapshots/*/tokenizer.json"

RES = HERE / "results"
TAB = HERE / "tables"
FIG = HERE / "figures"
LOG = HERE / "logs"
for _d in (RES, TAB, FIG, LOG):
    _d.mkdir(exist_ok=True)


def setup_logging(name: str) -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(LOG / f"{name}.log", rotation="30 MB", level="DEBUG")


def cite(exp: str, rel: str, extra: str = "") -> str:
    return f"{exp}/{rel}" + (f"#{extra}" if extra else "")


def read_jsonl(p: Path) -> list[dict]:
    out = []
    with p.open() as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def sha256_file(p: Path, chunk: int = 1 << 22) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def jdump(obj: Any, p: Path) -> None:
    p.write_text(json.dumps(obj, indent=1, default=_json_default))


def _json_default(o: Any) -> Any:
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, Path):
        return str(o)
    if isinstance(o, set):
        return sorted(o)
    raise TypeError(f"not serialisable: {type(o)}")


def clean(o: Any) -> Any:
    """Recursively replace NaN/inf by None so the JSON is strict."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (float, np.floating)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    if isinstance(o, np.bool_):
        return bool(o)
    return o


# ----------------------------------------------------------------------------------------------- harmonisation
TASK_MAP = {"t1": "T1", "T1": "T1", "grid": "T1", "grid_path": "T1", "t2": "T2", "T2": "T2",
            "shortest_path": "T2", "weighted_shortest_path": "T2"}
T1_MAP = {"bfs": "BFS", "dfs": "DFS", "bidir_bfs": "BIDIR_BFS", "bidirectional_bfs": "BIDIR_BFS", "iddfs": "IDDFS",
          "astar": "ASTAR", "a_star": "ASTAR", "a*": "ASTAR", "dijkstra_unit": "UNIT_DIJKSTRA",
          "unit_dijkstra": "UNIT_DIJKSTRA"}
T2_MAP = {"dijkstra": "DIJKSTRA", "bellman_ford_spfa": "BF_SPFA", "bellman_ford": "BF_SPFA", "spfa": "BF_SPFA",
          "bidir_dijkstra": "BIDIR_DIJKSTRA", "bidirectional_dijkstra": "BIDIR_DIJKSTRA", "floyd_warshall": "FW",
          "dial": "DIAL", "dag_dp": "DAG_DP"}
NOT_ATTEMPTED_RAW = {None, "", "none", "None", "no_code", "unparseable", "not_attempted", "NOT_ATTEMPTED",
                     "parse_error", "no code", "nan"}
CATALOGUE = {"T1": ["BFS", "DFS", "BIDIR_BFS", "IDDFS", "ASTAR", "UNIT_DIJKSTRA"],
             "T2": ["DIJKSTRA", "BF_SPFA", "BIDIR_DIJKSTRA", "FW", "DIAL"]}
DEFAULT = {"T1": "BFS", "T2": "DIJKSTRA"}
RUNNER_UP = {"T1": "DFS", "T2": "BF_SPFA"}
UNMAPPED: dict[str, int] = {}


def h_task(t: Any) -> str | None:
    if t is None:
        return None
    return TASK_MAP.get(str(t).strip(), TASK_MAP.get(str(t).strip().lower()))


def h_label(task: str, raw: Any) -> str:
    """Mechanism-level label; anything unmapped -> OTHER (recorded), no code -> NOT_ATTEMPTED."""
    if raw is None or (isinstance(raw, float) and math.isnan(raw)):
        return "NOT_ATTEMPTED"
    s = str(raw).strip()
    if s in NOT_ATTEMPTED_RAW or s.lower() in NOT_ATTEMPTED_RAW:
        return "NOT_ATTEMPTED"
    key = s.lower().replace("-", "_").replace(" ", "_")
    m = (T1_MAP if task == "T1" else T2_MAP).get(key)
    if m is None:
        # accept already-harmonised names
        if s.upper() in CATALOGUE.get(task, []) or s.upper() in ("DAG_DP",):
            return s.upper()
        UNMAPPED[f"{task}:{s}"] = UNMAPPED.get(f"{task}:{s}", 0) + 1
        return "OTHER"
    return m


def to_bool(v: Any) -> bool | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        if isinstance(v, float) and math.isnan(v):
            return None
        return bool(v)
    s = str(v).strip().lower()
    if s in ("true", "1", "yes", "pass", "passed"):
        return True
    if s in ("false", "0", "no", "fail", "failed"):
        return False
    return None


# ----------------------------------------------------------------------------------------------- intervals
Z95 = 1.959963984540054


def wilson(k: float, n: float, z: float = Z95) -> tuple[float, float]:
    if n <= 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def newcombe(k1: float, n1: float, k2: float, n2: float, z: float = Z95) -> tuple[float, float, float]:
    """Newcombe (1998) hybrid-score interval for p1 - p2 (independent). Returns (diff, lo, hi)."""
    if n1 <= 0 or n2 <= 0:
        return (float("nan"),) * 3
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1, z)
    l2, u2 = wilson(k2, n2, z)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return (d, max(-1.0, lo), min(1.0, hi))


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    if n <= 0:
        return (float("nan"), float("nan"))
    lo = 0.0 if k == 0 else float(stats.beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(stats.beta.ppf(1 - alpha / 2, k + 1, n - k))
    return (lo, hi)


def prop(k: int, n: int, exact_if_small: bool = False) -> dict:
    ci = clopper_pearson(k, n) if (exact_if_small and n <= 30) else wilson(k, n)
    return {"k": int(k), "n": int(n), "p": (k / n if n else None), "ci": [ci[0], ci[1]],
            "ci_method": "clopper_pearson" if (exact_if_small and n <= 30) else "wilson"}


def balanced_accuracy(y: np.ndarray, pred: np.ndarray) -> float:
    y = np.asarray(y).astype(int)
    pred = np.asarray(pred).astype(int)
    if (y == 1).sum() == 0 or (y == 0).sum() == 0:
        return float("nan")
    tpr = ((pred == 1) & (y == 1)).sum() / (y == 1).sum()
    tnr = ((pred == 0) & (y == 0)).sum() / (y == 0).sum()
    return float(0.5 * (tpr + tnr))


def auc(y: np.ndarray, s: np.ndarray) -> float:
    y = np.asarray(y).astype(int)
    s = np.asarray(s, dtype=float)
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    r = stats.rankdata(np.concatenate([pos, neg]))
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def cluster_boot_weights(groups: np.ndarray, n_boot: int = 1000, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Multinomial cluster multiplicities (n_boot x n_clusters) and the cluster index of each row."""
    ug, gi = np.unique(groups, return_inverse=True)
    rng = np.random.default_rng(seed)
    W = rng.multinomial(len(ug), np.full(len(ug), 1 / len(ug)), size=n_boot).astype(float)
    return W, gi


def boot_ba(y: np.ndarray, pred: np.ndarray, groups: np.ndarray, n_boot: int = 1000, seed: int = 0) -> np.ndarray:
    W, gi = cluster_boot_weights(groups, n_boot, seed)
    nc = W.shape[1]
    y = np.asarray(y).astype(int)
    pred = np.asarray(pred).astype(int)
    tp = np.bincount(gi, weights=((y == 1) & (pred == 1)).astype(float), minlength=nc)
    p = np.bincount(gi, weights=(y == 1).astype(float), minlength=nc)
    tn = np.bincount(gi, weights=((y == 0) & (pred == 0)).astype(float), minlength=nc)
    n = np.bincount(gi, weights=(y == 0).astype(float), minlength=nc)
    with np.errstate(invalid="ignore", divide="ignore"):
        return 0.5 * ((W @ tp) / (W @ p) + (W @ tn) / (W @ n))


def boot_auc(y: np.ndarray, s: np.ndarray, groups: np.ndarray, n_boot: int = 1000, seed: int = 0) -> np.ndarray:
    W, gi = cluster_boot_weights(groups, n_boot, seed)
    y = np.asarray(y).astype(int)
    s = np.asarray(s, dtype=float)
    ip, ineg = np.where(y == 1)[0], np.where(y == 0)[0]
    if len(ip) == 0 or len(ineg) == 0:
        return np.full(n_boot, np.nan)
    ind = (s[ip][:, None] > s[ineg][None, :]).astype(float) + 0.5 * (s[ip][:, None] == s[ineg][None, :])
    wr = W[:, gi]  # n_boot x n_rows
    wp, wn = wr[:, ip], wr[:, ineg]
    num = np.einsum("bi,ij,bj->b", wp, ind, wn)
    den = wp.sum(1) * wn.sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return num / den


def pct_ci(a: np.ndarray, lo: float = 2.5, hi: float = 97.5) -> list[float]:
    a = np.asarray(a, dtype=float)
    a = a[np.isfinite(a)]
    if len(a) == 0:
        return [float("nan"), float("nan")]
    return [float(np.percentile(a, lo)), float(np.percentile(a, hi))]


def hill1(labels: Iterable[str]) -> float:
    labels = list(labels)
    if not labels:
        return float("nan")
    _, c = np.unique(labels, return_counts=True)
    p = c / c.sum()
    return float(np.exp(-(p * np.log(p)).sum()))


def rarefied_hill1(labels: list[str], depth: int, n_draws: int, rng: np.random.Generator) -> float:
    """Mean over draws of exp(Shannon) of `depth` labels drawn without replacement."""
    if len(labels) < depth:
        return float("nan")
    ul, codes = np.unique(np.asarray(labels), return_inverse=True)
    if len(ul) == 1:
        return 1.0
    keys = rng.random((n_draws, len(codes)))
    idx = np.argpartition(keys, depth - 1, axis=1)[:, :depth]
    sub = codes[idx]
    cnt = np.stack([(sub == j).sum(1) for j in range(len(ul))], 1).astype(float)
    p = cnt / depth
    with np.errstate(divide="ignore", invalid="ignore"):
        H = -np.nansum(np.where(p > 0, p * np.log(p), 0.0), axis=1)
    return float(np.exp(H).mean())


def fisher_p(k1: int, n1: int, k2: int, n2: int) -> float:
    return float(stats.fisher_exact([[k1, n1 - k1], [k2, n2 - k2]])[1])


def find_tokenizer() -> Path | None:
    """Qwen3-8B tokenizer.json: QWEN3_TOKENIZER_JSON env var, else the sibling run's HF cache (decoding only)."""
    env = os.environ.get("QWEN3_TOKENIZER_JSON")
    if env and Path(env).exists():
        return Path(env)
    hits = sorted(_RUNS.glob(TOKENIZER_GLOB))
    return hits[0] if hits else None


def rel_to_exp(p: Path) -> str:
    """Cite a path inside an experiment workspace as expN/<relative path>."""
    p = Path(p)
    for k, base in EXP.items():
        try:
            return f"{k}/{p.relative_to(base)}"
        except ValueError:
            continue
    try:
        return str(p.relative_to(HERE))
    except ValueError:
        return p.name
