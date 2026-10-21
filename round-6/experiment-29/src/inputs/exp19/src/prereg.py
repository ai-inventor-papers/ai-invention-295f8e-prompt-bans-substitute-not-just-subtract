#!/usr/bin/env python3
"""Plan 4.3: commit the decision rule (predictions/c1_rule.json), the screen-derived forecast
(predictions/screen_forecast.json), the analysis code hashes, the screen hash and the engine-check verdict into the
sha256 chain (commitments.log), then write predictions/COMMITTED so the GPU stage may start stage 100."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import (DEFAULT, E6_TASKS, PRED_DIR, RESULTS_DIR, ROOT, read_json, read_jsonl, setup_logging, sha256_file,
                 utc_now, write_json, DATA_DIR)
from commit import commit

RULE = {
    "claim": "C1 (primary): fresh per-sample plan noise (PN) is the cheapest knob for CORRECT algorithmic diversity",
    "event_set_E6": list(E6_TASKS),
    "statistic": "correct-only Hill-1, rarefied at depth 25; vertices: Step-0 rarefied_hill1 (hypergeometric, "
                 "n_sub 1000, rng default_rng(0)) for knob rows; hull points: population rarefaction (mean exp(Shannon) "
                 "of multinomial(25, q), fixed uniform matrix U[n_sub, 25], n_sub 1000 point / 200 bootstrap)",
    "correct": "passed all hidden tests within limits and label != 'invalid'",
    "price": {"H5": "max Hill on the class's randomisation hull at cost <= 5 pass points",
              "P15": "smallest c >= 0 with max Hill at cost <= c >= 1.5 (bisection/grid to 0.1 points)",
              "P20": "same for 2.0", "cost": "100 x (pass_ref - pass(lambda)); negative costs feasible"},
    "hull": "mixtures over {reference} u settings; search on every pairwise edge, lambda grid 0.025, exact cost-5 "
            "boundary points, golden-section refinement on the best edge (point estimates); full-simplex check "
            "reported (3-vertex faces)",
    "classes": {
        "PN": ["PN_a0.5", "PN_a1", "PN_a2", "PN_a4"],
        "NA": {"TEMP": ["T1.3", "T1.6"], "TOPK10": ["TOPK10"], "NONCE": ["NONCE"], "NOVELTY": ["NOVELTY"],
               "SEMSEED": ["SEMSEED (T1/T2 only)"], "VETO_1SHOT": ["reused one-shot veto"],
               "VETO_PERSIST": ["reused persistent veto"], "VETO_ITER": ["reused iterated rounds 1-3 (dial)"]},
        "excluded": ["band patch", "PN_a8 (dose-response only)", "PNPLAIN_a1 (descriptive)"],
        "reference": "TWIN for this artifact's arms; the reused vetoes' own twin (exp13 'twin' vLLM; exp16 'b' on "
                     "T2); PLAIN for PNPLAIN; T1 vetoes have no iteration-3 twin -> this artifact's TWIN (flagged)"},
    "bootstrap": {"replicates": 2000, "seed": 20261021, "scheme": "programs resampled with replacement within each "
                  "arm, stratified by template; every vertex, class H5/P15/P20 and the max over settings and over NA "
                  "classes recomputed INSIDE each replicate", "n_sub": 200, "intervals": "percentile 95%"},
    "decision": {"D_t": "H5_PN(t) - max_{k in NA} H5_k(t)", "count1": "#{t in E6: H5_PN >= 1.5}",
                 "count2": "#{t in E6: H5_PN > H5_best} (strict)", "D_bar": "mean_t D_t",
                 "task_bootstrap": "2,000 two-stage replicates: resample the 6 tasks with replacement, each drawn "
                                   "task takes an independent program-bootstrap replicate; 95% percentile CI; "
                                   "p_C1 = (1 + #{D_bar* <= 0}) / 2001 (for the cross-artifact Holm family)",
                 "CONFIRMED": "count1 >= 3 AND count2 >= 4 AND CI_low(D_bar) > 0",
                 "DISCONFIRMED": "count1 <= 1 OR #{t: H5_best > H5_PN} >= 4",
                 "PARTIAL": "otherwise, naming each failed threshold",
                 "undecidable": "a never-drop cell missing on an E6 task -> UNDECIDABLE on that task; the rule is "
                                "evaluated on the remaining tasks as a labelled sensitivity"},
    "other_mapping": "correct 'other' programs are audited: LABELLER MISS -> resolved catalogue label; CATALOGUE "
                     "VARIANT -> parent catalogue mode (or its own named-variant category if outside the catalogue); "
                     "DEGENERATE -> excluded from Hill counts, still passed; NOVEL -> own category per algorithm. "
                     "Sensitivities: 'other' excluded; 'other' as one category",
    "sensitivities": {"s1": "twin-segment-only hull", "s2": "MINP (T1.6, T2.0 at min-p 0.1) and VS added to NA",
                      "s3": "dial interpolation of Hill", "s4": "template-cluster bootstrap",
                      "s5": "slot-paired bootstrap (CRN keys resampled jointly)", "s6": "'other' conventions",
                      "s7": "reused vetoes excluded", "s8": "Step-0 hypergeometric vertices only (no mixing)"},
    "descriptive": ["R2 and the 8 non-movable tasks", "PLAIN vs TWIN and PNPLAIN_a1 vs PN_a1", "alpha sweep incl. 8",
                    "ideas vs phrasing clusters", "CRN flip tables", "forecast score", "per-template off-default"],
    "precision": "FP8 W8A8 (device table: 16 GB Ada); the engine check verdict is carried into every C1 statement",
    "max_new": "1024 tokens for every task (the screen's cap; plan's 1,536 for path tasks not used, deviation D-cap)",
}


def forecast() -> dict:
    """Screen-mixture forecast: PN alpha-1 (alpha-2) composition = equal-weight mean of the screen's alpha-1 (alpha-2)
    direction compositions (correct programs per row); H5 on the hull {twin, PN_a1, PN_a2}; H5 of the best
    iteration-3 non-activation knob (exp13 nonce/novelty/vetoes on bench tasks; exp16 vetoes on T1/T2)."""
    from analysis.hull import Hull, fixed_uniforms

    U = fixed_uniforms(1000)
    scr = read_json(RESULTS_DIR / "screen.json")
    reused = read_jsonl(DATA_DIR / "reused_rows.jsonl")
    e13 = read_jsonl(Path(ROOT / "inputs" / "exp13" / "data" / "samples.jsonl"))
    out = {"tasks": {}, "utc": utc_now()}
    for t in E6_TASKS:
        tr = scr["tasks"].get(t)
        if not tr:
            continue
        twin = tr.get("twin_exp17") or tr.get("twin_exp13")
        dirs = tr["directions"]
        cats = sorted({c for d in dirs.values() for c in d["correct_comp"]} | {DEFAULT[t]})
        ci = {c: i for i, c in enumerate(cats)}

        def vec(comp, n):
            v = np.zeros(len(cats))
            for c, k in comp.items():
                v[ci[c]] += k / n
            return v
        V, P, names = [], [], []
        # twin vertex: all correct twin programs are the default in the screen (checked in screen.json)
        tw_n = twin["n"]
        tw_r = np.zeros(len(cats))
        tw_r[ci[DEFAULT[t]]] = twin["pass"]
        V.append(tw_r)
        P.append(twin["pass"])
        names.append("TWIN")
        for al in (1.0, 2.0):
            ds = [d for d in dirs.values() if d["alpha"] == al]
            if not ds:
                continue
            r = np.mean([vec(d["correct_comp"], d["n"]) for d in ds], axis=0)
            p = float(np.mean([d["pass"] for d in ds]))
            V.append(r)
            P.append(p)
            names.append(f"PN_a{al:g}")
        h = Hull(np.array(V), np.array(P), U).summary()
        # iteration-3 non-activation rows
        na = {}
        if t in ("T1", "T2"):
            arms = {}
            for r in reused:
                if r["task"] == t:
                    arms.setdefault(r["arm"], []).append(r)
            ref_rows = arms.get("REUSED_TWIN")
        else:
            arms = {}
            for r in e13:
                if r["task"] == t and r["condition"] in ("twin", "nonce", "novelty", "oneshot", "persistent",
                                                         "iter1", "iter2", "iter3"):
                    arms.setdefault(r["condition"], []).append({"label": r["label"], "passed":
                                                               str(r["passed"]) == "True"})
            ref_rows = arms.get("twin")
        if ref_rows:
            for a, rs in arms.items():
                if a in ("twin", "REUSED_TWIN"):
                    continue
                allr = ref_rows + rs
                cc = sorted({x["label"] for x in allr if x["passed"] and x["label"] != "invalid"})
                if not cc:
                    continue
                cix = {c: i for i, c in enumerate(cc)}

                def rv(rows):
                    v = np.zeros(len(cc))
                    for x in rows:
                        if x["passed"] and x["label"] != "invalid":
                            v[cix[x["label"]]] += 1 / len(rows)
                    return v
                hh = Hull(np.array([rv(ref_rows), rv(rs)]),
                          np.array([np.mean([x["passed"] for x in ref_rows]), np.mean([x["passed"] for x in rs])]),
                          U).summary(with_price=False)
                na[a] = hh["H5"]
        best = max(na.items(), key=lambda x: (x[1] if x[1] is not None else -1)) if na else (None, None)
        out["tasks"][t] = {"vertices": names, "forecast_H5_PN": h["H5"], "forecast_P15_PN": h["P15"],
                           "forecast_comp_PN_a1": dict(zip(cats, np.round(V[1], 3).tolist())) if len(V) > 1 else None,
                           "iter3_na_H5": na, "best_iter3_na": best[0], "forecast_H5_best_na": best[1],
                           "forecast_D_t": (h["H5"] - best[1]) if (h["H5"] is not None and best[1] is not None)
                           else None}
    D = [v["forecast_D_t"] for v in out["tasks"].values() if v["forecast_D_t"] is not None]
    c1 = sum(1 for v in out["tasks"].values() if (v["forecast_H5_PN"] or 0) >= 1.5)
    c2 = sum(1 for v in out["tasks"].values() if v["forecast_D_t"] is not None and v["forecast_D_t"] > 0)
    nb = sum(1 for v in out["tasks"].values() if v["forecast_D_t"] is not None and v["forecast_D_t"] < 0)
    out["forecast_count1"] = c1
    out["forecast_count2"] = c2
    out["forecast_D_bar"] = float(np.mean(D)) if D else None
    out["forecast_implied_C1"] = ("CONFIRMED-if-CI>0" if (c1 >= 3 and c2 >= 4) else
                                  ("DISCONFIRMED" if (c1 <= 1 or nb >= 4) else "PARTIAL"))
    out["note"] = ("FP8 screen rows; the forecast treats fresh per-sample noise as an equal mixture over the screen's "
                   "fixed directions; iteration-3 NA rows use their own twin; temperature/top-k have no iteration-3 "
                   "rows on these tasks and are not forecast")
    return out


def main() -> None:
    setup_logging("prereg")
    write_json(PRED_DIR / "c1_rule.json", {**RULE, "utc": utc_now()})
    fc = forecast()
    write_json(PRED_DIR / "screen_forecast.json", fc)
    logger.info(f"forecast: count1 {fc['forecast_count1']} count2 {fc['forecast_count2']} D_bar "
                f"{fc['forecast_D_bar']} -> {fc['forecast_implied_C1']}")
    files = sorted((ROOT / "src" / "analysis").glob("*.py"))
    lines = [f"{sha256_file(p)}  src/analysis/{p.name}" for p in files]
    (PRED_DIR / "analysis_code.sha256").write_text("\n".join(lines) + "\n")
    ec = read_json(RESULTS_DIR / "engine_check.json")
    write_json(PRED_DIR / "engine_check_verdict.json", {"verdict": ec["verdict"], "utc": utc_now()})
    paths = [PRED_DIR / "c1_rule.json", PRED_DIR / "screen_forecast.json", PRED_DIR / "analysis_code.sha256",
             RESULTS_DIR / "screen.json", PRED_DIR / "engine_check_verdict.json", RESULTS_DIR / "engine_check.json",
             RESULTS_DIR / "unit_tests_gpu.json", RESULTS_DIR / "unit_r2.json"] + files
    recs = commit(paths, "commit1")
    (PRED_DIR / "COMMITTED").write_text(utc_now() + "\n")
    logger.info(f"committed {len(recs)} files; chain head {recs[-1]['chain']}")


if __name__ == "__main__":
    main()
