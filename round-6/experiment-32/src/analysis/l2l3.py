#!/usr/bin/env python3
"""Frozen L2 / L3 analysis (plan Stage 6), hash-committed before the first nudge sample.

L2: over CORRECT S-labelled nudged programs (content-free primary; BINT separately), violations = programs whose
    algorithm has base valid == 0 and base correct == 0 (support from units.json); rule-of-three bound 3/N if 0.
L3: events with >= 10 correct S programs: 10 random half-splits (seed 20261021 + i); on half A fit one power gamma
    in 0:0.05:8 by maximum likelihood for q_base^g, q_tail^g and assoc^g (each renormalised on S); uniform has no
    parameter; held-out log score on half B averaged over splits; winner per event; Wilcoxon signed-rank of base vs
    each rival (descriptive). Kendall tau-b per unit between the q_base and q_tail orders on S (|S| >= 2 and
    non-uniform q_tail); pooled mean tau and a sign test over units with nonzero tau."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import kendalltau, wilcoxon

GRID = np.round(np.arange(0.0, 8.0 + 1e-9, 0.05), 4)
FAMS = {"base": "q_base", "tail": "q_tail", "assoc": "assoc"}


def l2(programs: list[dict], units: dict[str, dict]) -> dict[str, Any]:
    out = {}
    for name, sel in (("content_free", lambda p: p["content_free"]), ("BINT", lambda p: not p["content_free"])):
        ps = [p for p in programs if sel(p)]
        viol = []
        for p in ps:
            sup = units.get(p["unit_id"], {}).get("support", {}).get(p["label"], {})
            if sup.get("valid", 0) == 0 and sup.get("correct", 0) == 0:
                viol.append({"unit": p["unit_id"], "label": p["label"], "key": p.get("key")})
        n = len(ps)
        out[name] = {"n_programs": n, "violations": len(viol), "violation_list": viol[:50],
                     "rule_of_three_upper": (3 / n) if (n and not viol) else None}
    return out


def _vec(q: dict[str, float], S: list[str]) -> np.ndarray:
    v = np.array([max(q.get(a, 0.0), 1e-12) for a in S], float)
    return v / v.sum()


def fit_gamma(q: np.ndarray, counts: np.ndarray) -> float:
    best, bg = -np.inf, 1.0
    for g in GRID:
        p = q ** g
        p = p / p.sum()
        ll = float((counts * np.log(np.maximum(p, 1e-300))).sum())
        if ll > best + 1e-12:
            best, bg = ll, float(g)
    return bg


def l3(events: list[dict]) -> dict[str, Any]:
    rows = []
    for e in events:
        S = [a for a in e["catalogue"] if a != e["default"]]
        labs = [a for a, c in e["counts"].items() if a in S for _ in range(c)]
        if len(labs) < 10:
            continue
        rec = {"event_id": e["event_id"], "n": len(labs), "scores": {}, "gammas": {}}
        for f, key in list(FAMS.items()) + [("uniform", None)]:
            if key is not None and not e.get(key):
                continue
            q = _vec(e[key], S) if key else np.full(len(S), 1.0 / len(S))
            hs, gs = [], []
            for i in range(10):
                rng = np.random.default_rng(20261021 + i)
                perm = rng.permutation(len(labs))
                A = [labs[j] for j in perm[:len(labs) // 2]]
                Bh = [labs[j] for j in perm[len(labs) // 2:]]
                ca = np.array([A.count(a) for a in S], float)
                cb = np.array([Bh.count(a) for a in S], float)
                g = fit_gamma(q, ca) if key else 1.0
                p = q ** g
                p = p / p.sum()
                hs.append(float((cb * np.log(np.maximum(p, 1e-300))).sum() / max(cb.sum(), 1)))
                gs.append(g)
            rec["scores"][f] = float(np.mean(hs))
            rec["gammas"][f] = float(np.median(gs))
        rec["winner"] = max(rec["scores"], key=rec["scores"].get)
        rows.append(rec)
    tests = {}
    for rival in ("tail", "assoc", "uniform"):
        d = [r["scores"]["base"] - r["scores"][rival] for r in rows if "base" in r["scores"] and rival in r["scores"]]
        tests[rival] = {"n": len(d), "mean_diff": float(np.mean(d)) if d else None,
                        "wilcoxon_p": float(wilcoxon(d).pvalue) if len(d) >= 5 and any(x != 0 for x in d) else None}
    return {"events": rows, "base_vs": tests,
            "winners": {f: sum(1 for r in rows if r["winner"] == f) for f in ("base", "tail", "assoc", "uniform")}}


def kendall(units: dict[str, dict]) -> dict[str, Any]:
    taus = {}
    for u, v in units.items():
        if v.get("default") in (None, "NO_DEFAULT") or not v.get("q_base") or not v.get("q_tail"):
            continue
        S = [a for a in v["catalogue"] if a != v["default"]]
        if len(S) < 2:
            continue
        qt = [v["q_tail"].get(a, 0) for a in S]
        if max(qt) - min(qt) < 1e-12:
            continue
        t = kendalltau([v["q_base"].get(a, 0) for a in S], qt, variant="b").statistic
        taus[u] = None if (t is None or math.isnan(t)) else float(t)
    vals = [t for t in taus.values() if t is not None]
    nz = [t for t in vals if abs(t) > 1e-12]
    pos = sum(1 for t in nz if t > 0)
    n = len(nz)
    p = float(sum(math.comb(n, i) for i in range(pos, n + 1)) / 2 ** n) if n else None
    return {"per_unit": taus, "mean_tau": float(np.mean(vals)) if vals else None, "n_nonzero": n, "n_positive": pos,
            "sign_test_p_one_sided": p}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", required=True)
    ap.add_argument("--units", required=True)
    ap.add_argument("--programs", required=True, help="JSON list of correct S-labelled nudged programs")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ev = json.loads(Path(a.events).read_text())["events"]
    un = {u["unit_id"]: u for u in json.loads(Path(a.units).read_text())["units"]}
    progs = json.loads(Path(a.programs).read_text())
    E = [e for e in ev if e["is_event"] and e["content_free"] and e["set"] == "CONFIRMATION"
         and e.get("default") not in (None, "NO_DEFAULT")]
    res = {"L2": l2(progs, un), "L3": l3(E), "kendall_base_vs_tail": kendall(
        {u: v for u, v in un.items() if v.get("unit_kind") == "new_unit"}),
        "kendall_base_vs_tail_screen": kendall({u: v for u, v in un.items() if v.get("unit_kind") == "iter5_screen"})}
    Path(a.out).write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
