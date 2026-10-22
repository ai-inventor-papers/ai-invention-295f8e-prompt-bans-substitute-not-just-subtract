#!/usr/bin/env python3
"""Frozen M and K analysis (plan Stage 6), hash-committed before the first nudge sample.

M: over enrolled new units with a default, Spearman rho of each candidate (beta, replacement_class, runtime_merit,
   twin_modal_share, K, fork_margin) with E_u; one-sided p in the COMMITTED direction (predictions/m_signs.json) by
   exact permutation enumeration (n <= 9) or 100,000 permutations; Holm over the 6 candidates; SUPPORTED iff rho >= 0.5
   in the committed direction and Holm p < 0.05. The iteration-5 screen ranking is reported beside.
K: per new unit, H5 / P15 / P20 of BINT, PN alpha 2 and PN alpha 4 on the full-simplex randomisation hull (exp27
   hull_full.py, vendored) with 2,000 bootstrap replicates (max over settings inside each replicate); the
   edge-restricted hull (max_nonzero 2) as a sensitivity; correct-only rarefied Hill-1 at depth 25 (flag below 25
   correct); pass-rate cost with Newcombe CIs."""

from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import rankdata, spearmanr

CANDS = ["beta", "replacement_class", "runtime_merit", "twin_modal_share", "K", "fork_margin"]


def spearman(x: list[float], y: list[float]) -> float | None:
    if len(x) < 3 or len(set(x)) < 2 or len(set(y)) < 2:
        return None
    return float(spearmanr(x, y).statistic)


def perm_p(x: list[float], y: list[float], sign: int, n_perm: int = 100000) -> float | None:
    r0 = spearman(x, y)
    if r0 is None:
        return None
    obs = sign * r0
    n = len(x)
    rx = rankdata(x)
    ry = rankdata(y)
    cnt = tot = 0
    if n <= 9:
        for perm in itertools.permutations(range(n)):
            r = np.corrcoef(rx, ry[list(perm)])[0, 1]
            cnt += (sign * r >= obs - 1e-12)
            tot += 1
    else:
        rng = np.random.default_rng(20261021)
        for _ in range(n_perm):
            r = np.corrcoef(rx, rng.permutation(ry))[0, 1]
            cnt += (sign * r >= obs - 1e-12)
            tot += 1
    return cnt / tot


def holm(ps: dict[str, float | None]) -> dict[str, float | None]:
    items = sorted([(p, k) for k, p in ps.items() if p is not None])
    m = len(items)
    out: dict[str, float | None] = {k: None for k in ps}
    run = 0.0
    for i, (p, k) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        out[k] = run
    return out


def m_test(units: list[dict], signs: dict[str, str]) -> dict[str, Any]:
    us = [u for u in units if u.get("E_u") is not None and u.get("default") not in (None, "NO_DEFAULT")]
    res: dict[str, Any] = {"n_units": len(us), "candidates": {}}
    ps = {}
    for c in CANDS:
        pairs = [(u["m_candidates"].get(c), u["E_u"]) for u in us if u["m_candidates"].get(c) is not None]
        x = [float(a) for a, _ in pairs]
        y = [float(b) for _, b in pairs]
        sg = 1 if signs.get(c, "+") == "+" else -1
        rho = spearman(x, y)
        p = perm_p(x, y, sg) if rho is not None else None
        ps[c] = p
        res["candidates"][c] = {"n": len(pairs), "rho": rho, "committed_sign": signs.get(c), "p_one_sided": p,
                                "values": {u["unit_id"]: u["m_candidates"].get(c) for u in us}}
    hp = holm(ps)
    for c in CANDS:
        r = res["candidates"][c]
        r["p_holm"] = hp[c]
        sg = 1 if signs.get(c, "+") == "+" else -1
        r["supported"] = bool(r["rho"] is not None and sg * r["rho"] >= 0.5 and hp[c] is not None and hp[c] < 0.05)
    res["E_u"] = {u["unit_id"]: u["E_u"] for u in us}
    return res


def hill1_rarefied(labels: list[str], depth: int = 25, reps: int = 2000, seed: int = 20261021) -> dict[str, Any]:
    n = len(labels)
    if n == 0:
        return {"hill1": None, "n": 0, "flag_below_depth": True}
    rng = np.random.default_rng(seed)
    d = min(depth, n)
    vals = []
    arr = np.array(labels)
    for _ in range(reps):
        sub = rng.choice(arr, size=d, replace=False)
        _, c = np.unique(sub, return_counts=True)
        p = c / c.sum()
        vals.append(float(np.exp(-(p * np.log(p)).sum())))
    return {"hill1": float(np.mean(vals)), "n": n, "depth": d, "flag_below_depth": n < depth}


def newcombe_diff(k1: int, n1: int, k2: int, n2: int) -> list[float] | None:
    def wil(k, n, z=1.959963984540054):
        if n == 0:
            return (float("nan"), float("nan"))
        p = k / n
        den = 1 + z * z / n
        c = (p + z * z / (2 * n)) / den
        h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
        return (c - h, c + h)
    if n1 == 0 or n2 == 0:
        return None
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wil(k1, n1)
    l2, u2 = wil(k2, n2)
    d = p1 - p2
    return [d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)]


def k_prices(settings_by_unit: dict[str, dict[str, Any]], hull_dir: str, n_boot: int = 2000) -> dict[str, Any]:
    """settings_by_unit[u] = {'TWIN': {'pass': .., 'n': .., 'correct_labels': [...]}, 'BINT': ..., 'PN_a2.0': ...}"""
    sys.path.insert(0, hull_dir)
    from hull_full import hull_prices_full  # noqa: E402
    out = {}
    for u, st in settings_by_unit.items():
        tw = st.get("TWIN")
        if tw is None:
            continue
        rec: dict[str, Any] = {}
        for arm in ("BINT", "PN_a2.0", "PN_a4.0"):
            s = st.get(arm)
            if s is None or s["n"] == 0:
                continue
            settings = [{"name": "TWIN", "pass": tw["pass"], "correct_labels": tw["correct_labels"]},
                        {"name": arm, "pass": s["pass"], "correct_labels": s["correct_labels"]}]
            full = hull_prices_full(settings, n_draws=n_boot, seed=20261021)
            edge = hull_prices_full(settings, n_draws=n_boot, seed=20261021, max_nonzero=2)
            rec[arm] = {"H5": full.get("H5"), "P15": full.get("P15"), "P20": full.get("P20"),
                        "edge_H5": edge.get("H5"), "hill1_correct": hill1_rarefied(s["correct_labels"]),
                        "pass": s["pass"], "n": s["n"],
                        "pass_cost": tw["pass"] - s["pass"],
                        "pass_cost_newcombe95": newcombe_diff(round(tw["pass"] * tw["n"]), tw["n"],
                                                              round(s["pass"] * s["n"]), s["n"])}
        rec["TWIN_hill1_correct"] = hill1_rarefied(tw["correct_labels"])
        out[u] = rec
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--units", required=True)
    ap.add_argument("--signs", required=True)
    ap.add_argument("--settings", required=True)
    ap.add_argument("--hull-dir", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    un = [u for u in json.loads(Path(a.units).read_text())["units"] if u.get("unit_kind") == "new_unit"
          and u.get("status") == "enrolled"]
    signs = json.loads(Path(a.signs).read_text())["signs"]
    res = {"M": m_test(un, signs), "K": k_prices(json.loads(Path(a.settings).read_text()), a.hull_dir)}
    Path(a.out).write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
