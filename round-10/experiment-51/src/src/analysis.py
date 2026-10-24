#!/usr/bin/env python3
"""Committed verdict rules V1, V2, V3, V6 (plan NOV-B1) plus their intervals, placebos and data loaders.

Thresholds: 0.8 (V1 bar = 0.8 x best fit), 1.5 (R1, R2), 1.2 (R3), 1.0 (per-seed ratios, disconfirm bound),
0.95 (behaviour-cluster / rename agreement), 0.9 (max corpus agreement for NB), 0.4 / 0.2 / 0.1 (V6)."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

import cluster

ROOT = Path(__file__).resolve().parent.parent
BF_FSW5K, BF_OR3 = 3.9843042559613666, 5.367793240556666
THR_FSW5K, THR_OR3 = 0.8 * BF_FSW5K, 0.8 * BF_OR3
CORE = ["T1.0", "T1.6", "DTB", "RPB"]
THRESHOLDS = {"v1_rule": 0.8, "R1_R2": 1.5, "R3": 1.2, "per_seed": 1.0, "disconfirm": 1.0, "cluster": 0.95,
              "nb_corpus": 0.9, "v6_support": 0.4, "v6_disconfirm": 0.2, "v6_margin": 0.1}
NEW_IDEA_RX = r"new|novel|different|alternative|instead|unlike|another approach|fresh"


# ----------------------------------------------------------------------------------------------- loaders
def load_rows(run: str) -> list[dict]:
    p = ROOT / "data" / run / "programs.jsonl"
    return [json.loads(ln) for ln in p.read_text().splitlines()] if p.exists() else []


def load_decisions(run: str, seed: int, arm: str) -> np.ndarray:
    p = ROOT / "data" / run / "decisions" / f"{seed}_{arm}.u16"
    a = np.fromfile(p, dtype=np.uint16) if p.exists() else np.zeros(0, dtype=np.uint16)
    return a.reshape(-1, cluster.N_STATES)


def stream_rows(rows: list[dict], seed: int, arm: str, c_s: int | None = None) -> list[dict]:
    rs = sorted((r for r in rows if r["seed"] == seed and r["arm"] == arm), key=lambda r: r["call_id"])
    return rs if c_s is None else [r for r in rs if r["call_id"] < c_s]


def valid(r: dict) -> bool:
    return r["error_type"] == "ok" and r.get("F") is not None


# ----------------------------------------------------------------------------------------------- V1
def v1(best: dict[str, dict]) -> dict:
    """best[arm] = {'exc_FSW5k': %, 'exc_OR3': %, ...} for the better-by-F of the arm's two seed-bests."""
    per = {}
    for a in CORE:
        b = best.get(a) or {}
        fs, o3 = b.get("exc_FSW5k"), b.get("exc_OR3")
        p_fs = fs is not None and fs <= THR_FSW5K
        p_o3 = o3 is not None and o3 <= THR_OR3
        per[a] = {"exc_FSW5k": fs, "exc_OR3": o3, "pass_FSW5k": p_fs, "pass_OR3": p_o3, "pass": p_fs and p_o3}
    if all(v["pass"] for v in per.values()):
        verdict = "SUPPORTED"
    elif not any(v["pass_FSW5k"] or v["pass_OR3"] for v in per.values()):
        verdict = "DISCONFIRMED"
    else:
        verdict = "PARTIAL"
    return {"verdict": verdict, "per_arm": per, "thr_FSW5k_pct": THR_FSW5K, "thr_OR3_pct": THR_OR3}


# ----------------------------------------------------------------------------------------------- V2
def rho(b: dict) -> float | None:
    if b.get("exc_FSW5k") is None or b.get("exc_OR3") is None:
        return None
    return 0.5 * (b["exc_FSW5k"] / BF_FSW5K + b["exc_OR3"] / BF_OR3)


def v2(D: dict[tuple[str, int], int], C: dict[int, int], best: dict[str, dict]) -> dict:
    """D[(arm, seed)] = complete-linkage clusters in stream (arm, seed); C[seed] = completed calls per stream."""
    rate = {a: 1000.0 * (D[(a, 0)] + D[(a, 1)]) / (C[0] + C[1]) for a in CORE}
    R1 = rate["DTB"] / rate["T1.0"] if rate["T1.0"] else math.inf
    R2 = rate["DTB"] / rate["T1.6"] if rate["T1.6"] else math.inf
    R3 = rate["DTB"] / rate["RPB"] if rate["RPB"] else math.inf
    r = {f"r_s{s}_{X}": (D[("DTB", s)] / D[(X, s)] if D[(X, s)] else math.inf) for s in (0, 1) for X in ("T1.0", "T1.6")}
    rh = {a: rho(best.get(a) or {}) for a in CORE}
    conds = {"R1>=1.5": R1 >= 1.5, "R2>=1.5": R2 >= 1.5, "all_per_seed_r>1": all(v > 1 for v in r.values()),
             "R3>=1.2": R3 >= 1.2,
             "rho_DTB<=min(rho_T1.0,rho_T1.6)": (rh["DTB"] is not None and rh["T1.0"] is not None and
                                                  rh["T1.6"] is not None and rh["DTB"] <= min(rh["T1.0"], rh["T1.6"]))}
    if all(conds.values()):
        verdict = "SUPPORTED"
    elif R1 <= 1.0 or R2 <= 1.0:
        verdict = "DISCONFIRMED"
    else:
        verdict = "PARTIAL"
    return {"verdict": verdict, "rates_per_1000_calls": rate, "R1": R1, "R2": R2, "R3": R3, "per_seed": r,
            "rho": rh, "conditions": conds, "failed": [k for k, v in conds.items() if not v]}


def round_block_bootstrap(labels: dict[tuple[str, int], np.ndarray], rounds: dict[tuple[str, int], np.ndarray],
                          n_rounds: dict[int, int], B: int = 2000, seed: int = 20261026) -> dict:
    """Paired round-block bootstrap: the same resampled round indices for all arms within a seed; the count is the
    number of distinct full-run cluster labels among the resampled rows."""
    rng = np.random.default_rng(seed)
    out = {k: np.zeros(B) for k in ("R1", "R2", "R3")}
    for b in range(B):
        res = {s: rng.integers(0, n_rounds[s], size=n_rounds[s]) for s in (0, 1)}
        cnt = {}
        for a in CORE:
            tot = 0
            for s in (0, 1):
                lab, rd = labels[(a, s)], rounds[(a, s)]
                picked = np.isin(rd, res[s])
                tot += len(np.unique(lab[picked])) if picked.any() else 0
            cnt[a] = tot
        out["R1"][b] = cnt["DTB"] / cnt["T1.0"] if cnt["T1.0"] else np.nan
        out["R2"][b] = cnt["DTB"] / cnt["T1.6"] if cnt["T1.6"] else np.nan
        out["R3"][b] = cnt["DTB"] / cnt["RPB"] if cnt["RPB"] else np.nan
    return {k: {"p2.5": float(np.nanpercentile(v, 2.5)), "p50": float(np.nanpercentile(v, 50)),
                "p97.5": float(np.nanpercentile(v, 97.5))} for k, v in out.items()}


def rarefied(decs: dict[str, np.ndarray], n: int, reps: int = 200, seed: int = 20261027) -> dict[str, float]:
    """Mean complete-linkage cluster count over `reps` random subsets of size n (valid offspring) per arm."""
    rng = np.random.default_rng(seed)
    out = {}
    for a, D in decs.items():
        if len(D) < n or n == 0:
            out[a] = float("nan")
            continue
        out[a] = float(np.mean([cluster.complete_linkage(D[rng.choice(len(D), n, replace=False)])[1]
                                for _ in range(reps)]))
    return out


def shuffle_placebo(lab_a: dict[int, np.ndarray], lab_b: dict[int, np.ndarray], decs_a: dict[int, np.ndarray],
                    decs_b: dict[int, np.ndarray], n_shuffles: int = 200, seed: int = 20261028) -> dict:
    """Within-seed arm-label shuffles of DTB and T1.0 rows: how often does the shuffled R1 reach 1.5?"""
    rng = np.random.default_rng(seed)
    hits, vals = 0, []
    for _ in range(n_shuffles):
        da, db = 0, 0
        for s in (0, 1):
            pool = np.concatenate([decs_a[s], decs_b[s]])
            perm = rng.permutation(len(pool))
            na = len(decs_a[s])
            da += cluster.complete_linkage(pool[perm[:na]])[1]
            db += cluster.complete_linkage(pool[perm[na:]])[1]
        r1 = da / db if db else np.nan
        vals.append(r1)
        hits += int(r1 >= 1.5)
    return {"n": n_shuffles, "share_R1_ge_1.5": hits / n_shuffles, "R1_shuffled_p50": float(np.nanmedian(vals)),
            "R1_shuffled_p97.5": float(np.nanpercentile(vals, 97.5))}


# ----------------------------------------------------------------------------------------------- V3
def v3(audited: list[dict], n_nb: int) -> dict:
    """audited: representatives with final 'cls' in {NOVEL, KNOWN, KNOWN_FAMILY_NEW_PARAMETERS, DEGENERATE}."""
    novel = [c for c in audited if c.get("cls") == "NOVEL"]
    n = len(audited)
    out = {"n_nb_set": n_nb, "n_audited": n, "n_novel": len(novel), "novel_ids": [c["anon_id"] for c in novel]}
    if novel:
        out["verdict"] = "SUPPORTED"
    else:
        out["verdict"] = "DISCONFIRMED"
        out["rule_of_three_upper_95"] = (3.0 / n) if n else None
    return out


# ----------------------------------------------------------------------------------------------- V6
def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def newcombe(k1: int, n1: int, k2: int, n2: int) -> tuple[float, float]:
    """Newcombe (1998) hybrid-score CI for p1 - p2."""
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    d = p1 - p2
    return (d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2))


def v6(k_idea: int, n_idea: int, k_t10: int, n_t10: int) -> dict:
    r_i = k_idea / n_idea if n_idea else float("nan")
    r_t = k_t10 / n_t10 if n_t10 else float("nan")
    if r_i >= 0.4 and r_i >= r_t - 0.1:
        verdict = "SUPPORTED"
    elif r_i < 0.2:
        verdict = "DISCONFIRMED"
    else:
        verdict = "PARTIAL"
    return {"verdict": verdict, "rate_IDEA": r_i, "rate_T1.0": r_t, "n_IDEA": n_idea, "n_T1.0": n_t10,
            "wilson_IDEA": wilson(k_idea, n_idea), "wilson_T1.0": wilson(k_t10, n_t10),
            "newcombe_IDEA_minus_T1.0": newcombe(k_idea, n_idea, k_t10, n_t10) if n_idea and n_t10 else None}
