#!/usr/bin/env python3
"""Plan 6.6 descriptive analyses (each in its own results file); run after analysis.run_all.

(a) nonmovable.json   R2 and the 8 non-movable tasks vs the E6 distribution
(b) plain_vs_twin.json PLAIN vs TWIN; PNPLAIN_a1 vs PN_a1 paired by (w, k) with slot-paired bootstrap CIs
(c) alpha_sweep.json  alpha 0 / 0.5 / 1 / 2 / 4 / 8 on E6: pass, invalid, cap hits, off-default, Hill, displacement
(d) ideas_phrasings.json ideas vs phrasing clusters (exp6 identifier-normalised AST 4-gram shingles, Jaccard >= theta)
(e) flips.json        CRN flips against TWIN at the same (task, w, k)
(f) forecast_score.json the committed screen-mixture forecast against the realised PN alpha 1 / 2
(g) per_template.json off-default share per template for every arm on E6
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analysis.core import E6, step0_hill
from analysis.engine_check import jsd
from cfg import DATA_DIR, DEFAULT, E6 as E6_DIR, PRED_DIR, RESULTS_DIR, read_json, read_jsonl, setup_logging, utc_now, \
    write_json


ALPHA_ARMS = [("TWIN", 0.0), ("PN_a0.5", 0.5), ("PN_a1", 1.0), ("PN_a2", 2.0), ("PN_a4", 4.0), ("PN_a8", 8.0)]


def by_task_arm(rows: list[dict[str, Any]]) -> dict[str, dict[str, list[dict[str, Any]]]]:
    out: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        out[r["task"]][r["arm"]].append(r)
    return out


def correct(r: dict[str, Any]) -> bool:
    return bool(r.get("passed")) and r.get("label") != "invalid"


def offd(rs: list[dict[str, Any]], task: str) -> float:
    return sum(1 for r in rs if r["label"] not in (DEFAULT[task], "invalid")) / max(len(rs), 1)


def cell(rs: list[dict[str, Any]], task: str) -> dict[str, Any]:
    cc = Counter(r["label"] for r in rs if correct(r))
    return {"n": len(rs), "pass": float(np.mean([correct(r) for r in rs])) if rs else None,
            "invalid_share": sum(r["label"] == "invalid" for r in rs) / max(len(rs), 1),
            "cap_hit_share": sum(r.get("finish_reason") == "length" for r in rs) / max(len(rs), 1),
            "off_default_share": offd(rs, task),
            "off_default_share_invalid_counts": sum(1 for r in rs if r["label"] != DEFAULT[task]) / max(len(rs), 1),
            "correct_comp": dict(cc.most_common()),
            "attempted_comp": dict(Counter(r["label"] for r in rs).most_common()),
            "hill25_step0": step0_hill(cc) if sum(cc.values()) else None}


def nonmovable(T: dict, prices: dict) -> dict[str, Any]:
    e6_pn = [prices[t]["PN"]["H5"] for t in E6 if t in prices and "PN" in prices[t] and prices[t]["PN"]["H5"]]
    out = {"E6_H5_PN": {"min": min(e6_pn) if e6_pn else None, "median": float(np.median(e6_pn)) if e6_pn else None,
                        "max": max(e6_pn) if e6_pn else None}, "tasks": {}}
    for t in sorted(T):
        if t in E6:
            continue
        arms = T[t]
        pn = [r for a in ("PN_a0.5", "PN_a1", "PN_a2") for r in arms.get(a, [])]
        tw = arms.get("TWIN", [])
        out["tasks"][t] = {"held_out": t == "R2",
                           "arms": {a: cell(rs, t) for a, rs in sorted(arms.items())},
                           "PN_alpha_le2_off_default_excess": (offd(pn, t) - offd(tw, t)) if pn and tw else None,
                           "H5": {c: v.get("H5") for c, v in prices.get(t, {}).items()},
                           "P15": {c: v.get("P15") for c, v in prices.get(t, {}).items()}}
    return out


def paired(a_rows, b_rows, task, B=2000, seed=11) -> dict[str, Any]:
    ka = {(r["template"], r["slot"]): r for r in a_rows}
    kb = {(r["template"], r["slot"]): r for r in b_rows}
    keys = sorted(set(ka) & set(kb))
    if not keys:
        return {}
    rng = np.random.default_rng(seed)

    def stats(ks):
        A = [ka[k] for k in ks]
        Bb = [kb[k] for k in ks]
        ha = step0_hill(Counter(r["label"] for r in A if correct(r)))
        hb = step0_hill(Counter(r["label"] for r in Bb if correct(r)))
        return (offd(A, task) - offd(Bb, task), np.mean([correct(r) for r in A]) - np.mean([correct(r) for r in Bb]),
                ha - hb)
    pt = stats(keys)
    bs = np.array([stats([keys[i] for i in rng.integers(0, len(keys), len(keys))]) for _ in range(B)])
    ci = np.nanpercentile(bs, [2.5, 97.5], axis=0)
    return {"n_pairs": len(keys), "d_off_default": pt[0], "d_pass": pt[1], "d_hill": pt[2],
            "ci95_off_default": ci[:, 0].tolist(), "ci95_pass": ci[:, 1].tolist(), "ci95_hill": ci[:, 2].tolist()}


def alpha_sweep(T: dict, realised: list[dict[str, Any]]) -> dict[str, Any]:
    disp = defaultdict(list)
    for r in realised:
        disp[(r["task"], r["arm"])].append(r)
    out = {}
    for t in E6:
        if t not in T:
            continue
        tw = cell(T[t].get("TWIN", []), t)
        rows = []
        for arm, al in ALPHA_ARMS:
            rs = T[t].get(arm)
            if not rs:
                continue
            c = cell(rs, t)
            rec = disp.get((t, arm), [])
            if rec:
                c["disp_S_mean_b24_35"] = float(np.mean([np.mean([x["disp_S"][str(l)] if str(l) in x["disp_S"] else
                                                                  x["disp_S"][l] for l in range(24, 36)]) for x in rec]))
                c["disp_R_b35"] = float(np.mean([x["disp_R"].get("35", x["disp_R"].get(35)) for x in rec]))
                c["disp_S_b12_over_target"] = float(np.mean([x["disp_S"].get("12", x["disp_S"].get(12)) /
                                                             max(x["target_mean"].get("12", x["target_mean"].get(12)),
                                                                 1e-9) for x in rec]))
            c["alpha"] = al
            rows.append(c)
        brk = next((c["alpha"] for c in rows if c["pass"] is not None and tw["pass"] and
                    c["pass"] < 0.8 * tw["pass"]), None)
        out[t] = {"sweep": rows, "breakage_alpha": brk}
    return out


def ideas_phrasings(T: dict, n_sub: int = 200, depth: int = 20, seed: int = 5) -> dict[str, Any]:
    from analysis.metrics_exp6 import clusters, jaccard_matrix, normalise_tokens, shingles  # exp6 metrics.py, verbatim

    # unit test on 3 program pairs: identical, renamed identifiers, different algorithm
    p1 = "def solve(nums, k):\n    nums.sort()\n    return nums[k-1]\n"
    p2 = "def solve(arr, kk):\n    arr.sort()\n    return arr[kk-1]\n"
    p3 = "import heapq\ndef solve(nums, k):\n    return heapq.nsmallest(k, nums)[-1]\n"
    sh = [shingles(normalise_tokens(p) or []) for p in (p1, p1, p2, p3)]
    J = jaccard_matrix(sh)
    test = {"identical": float(J[0, 1]), "renamed": float(J[0, 2]), "different": float(J[0, 3]),
            "pass": bool(J[0, 1] == 1.0 and J[0, 2] == 1.0 and J[0, 3] < 0.5)}
    rng = np.random.default_rng(seed)
    out = {"unit_test": test, "cells": {}}
    for t in sorted(T):
        D = DEFAULT[t]
        for arm, rs in sorted(T[t].items()):
            cr = [r for r in rs if correct(r) and r.get("code")]
            if not cr:
                continue
            ideas = Counter(r["label"] for r in cr)
            rec: dict[str, Any] = {"n_correct": len(cr), "n_ideas": len(ideas), "hill_ideas": step0_hill(ideas)}
            dflt = [r for r in cr if r["label"] == D]
            if len(dflt) >= 2:
                shs = [shingles(normalise_tokens(r["code"]) or []) for r in dflt]
                Jd = jaccard_matrix(shs)
                k = min(depth, len(dflt))
                for th in (0.7, 0.8, 0.9):
                    vals = []
                    for _ in range(n_sub if len(dflt) > k else 1):
                        idx = rng.choice(len(dflt), size=k, replace=False)
                        vals.append(len(set(clusters(Jd[np.ix_(idx, idx)], th, "single").tolist())))
                    rec[f"default_phrasings_theta{th}"] = float(np.mean(vals))
                rec["default_depth"] = k
                rec["default_depth_flag"] = k < depth
            per_idea = {}
            for m, c in ideas.items():
                if c >= 10:
                    rr = [r for r in cr if r["label"] == m]
                    shs = [shingles(normalise_tokens(r["code"]) or []) for r in rr]
                    Jm = jaccard_matrix(shs)
                    vals = []
                    for _ in range(50):
                        idx = rng.choice(len(rr), size=10, replace=False)
                        vals.append(len(set(clusters(Jm[np.ix_(idx, idx)], 0.8, "single").tolist())))
                    per_idea[m] = float(np.mean(vals))
            rec["phrasings_per_idea_depth10_theta0.8"] = per_idea
            out["cells"][f"{t}|{arm}"] = rec
    return out


def flips(T: dict) -> dict[str, Any]:
    out = {}
    for t in sorted(T):
        tw = {(r["template"], r["slot"]): r for r in T[t].get("TWIN", [])}
        for arm, rs in sorted(T[t].items()):
            if arm == "TWIN" or arm.startswith(("VETO", "REUSED")):
                continue
            pairs = [(r, tw[(r["template"], r["slot"])]) for r in rs if (r["template"], r["slot"]) in tw]
            if not pairs:
                continue
            cd = [a.get("code_sha256") != b.get("code_sha256") for a, b in pairs]
            ld = [a["label"] != b["label"] for a, b in pairs]
            n_cd = sum(cd)
            out[f"{t}|{arm}"] = {"n": len(pairs), "P_code_differs": n_cd / len(pairs),
                                 "P_label_differs": sum(ld) / len(pairs),
                                 "P_label_differs_given_code_differs": (sum(1 for c, l in zip(cd, ld) if c and l) /
                                                                        n_cd) if n_cd else None}
    return out


def forecast_score(T: dict, prices: dict, c1: dict | None) -> dict[str, Any]:
    fc = read_json(PRED_DIR / "screen_forecast.json")
    rng = np.random.default_rng(9)
    out = {"tasks": {}}
    for t, f in fc["tasks"].items():
        if t not in T:
            continue
        rec = {"forecast_H5_PN": f["forecast_H5_PN"], "realised_H5_PN": prices.get(t, {}).get("PN", {}).get("H5"),
               "forecast_D_t": f["forecast_D_t"],
               "realised_D_t": (c1 or {}).get("primary", {}).get("per_task", {}).get(t, {}).get("D_t")}
        comp_f = f.get("forecast_comp_PN_a1")
        rs = T[t].get("PN_a1", [])
        if comp_f and rs:
            real = Counter(r["label"] for r in rs if correct(r))
            fcnt = Counter({k: v for k, v in comp_f.items() if v > 0})
            j = jsd(fcnt, real)
            byw = defaultdict(list)
            for r in rs:
                if correct(r):
                    byw[r["template"]].append(r["label"])
            ws = sorted(byw)
            null = [jsd(Counter(x for w in rng.choice(ws, len(ws)) for x in byw[w]),
                        Counter(x for w in rng.choice(ws, len(ws)) for x in byw[w])) for _ in range(2000)]
            rec.update({"JSD_forecast_vs_realised_PN_a1": j, "null_p95": float(np.nanpercentile(null, 95)),
                        "within_null": bool(j <= np.nanpercentile(null, 95))})
        out["tasks"][t] = rec
    out["forecast_implied_C1"] = fc.get("forecast_implied_C1")
    out["realised_C1"] = (c1 or {}).get("primary", {}).get("verdict")
    return out


def vs_dispatch(T: dict) -> dict[str, Any]:
    """Programs that pick an algorithm at run time (random.choices / random.choice dispatch) per task x arm."""
    import re

    pat = re.compile(r"random\.choices?\(")
    out = {}
    for t in sorted(T):
        for arm, rs in sorted(T[t].items()):
            withc = [r for r in rs if r.get("code")]
            disp = [r for r in withc if pat.search(r["code"])]
            if not disp:
                continue
            out[f"{t}|{arm}"] = {"n_with_code": len(withc), "n_random_dispatch": len(disp),
                                 "n_dispatch_correct": sum(1 for r in disp if correct(r)),
                                 "correct_dispatch_labels": dict(Counter(r["label"] for r in disp if correct(r))
                                                                 .most_common())}
    return out


def per_template(T: dict) -> dict[str, Any]:
    out = {}
    for t in E6:
        if t not in T:
            continue
        for arm, rs in sorted(T[t].items()):
            byw = defaultdict(list)
            for r in rs:
                byw[str(r["template"])].append(r)
            out[f"{t}|{arm}"] = {w: round(offd(v, t), 3) for w, v in sorted(byw.items())}
    return out


def main() -> None:
    setup_logging("descriptive")
    rows = read_jsonl(DATA_DIR / "samples.jsonl")
    T = by_task_arm(rows)
    prices = read_json(RESULTS_DIR / "prices.json")
    c1 = read_json(RESULTS_DIR / "c1.json") if (RESULTS_DIR / "c1.json").exists() else None
    realised = read_jsonl(DATA_DIR / "realised.jsonl")
    write_json(RESULTS_DIR / "nonmovable.json", nonmovable(T, prices))
    pv = {}
    for t in sorted(T):
        if "PLAIN" in T[t] and "TWIN" in T[t]:
            pv[t] = {"PLAIN_minus_TWIN": paired(T[t]["PLAIN"], T[t]["TWIN"], t)}
            if "PNPLAIN_a1" in T[t] and "PN_a1" in T[t]:
                pv[t]["PNPLAIN_a1_minus_PN_a1"] = paired(T[t]["PNPLAIN_a1"], T[t]["PN_a1"], t)
    write_json(RESULTS_DIR / "plain_vs_twin.json", pv)
    write_json(RESULTS_DIR / "alpha_sweep.json", alpha_sweep(T, realised))
    write_json(RESULTS_DIR / "flips.json", flips(T))
    write_json(RESULTS_DIR / "per_template.json", per_template(T))
    write_json(RESULTS_DIR / "vs_dispatch.json", vs_dispatch(T))
    write_json(RESULTS_DIR / "forecast_score.json", forecast_score(T, prices, c1))
    write_json(RESULTS_DIR / "ideas_phrasings.json", ideas_phrasings(T))
    logger.info("descriptive analyses written")


if __name__ == "__main__":
    main()
