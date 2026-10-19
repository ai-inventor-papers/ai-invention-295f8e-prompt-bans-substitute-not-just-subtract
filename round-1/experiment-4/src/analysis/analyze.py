#!/usr/bin/env python3
"""Assemble data/samples.jsonl and compute every result table of the screen.

Outputs: data/samples.jsonl, results/condition_summaries.json, results/engine_check.json,
results/buy_table.json/.csv, results/predict_row.json, results/flips.json, results/dose_response.json,
results/move_vs_flatten.json, results/screen_verdict.json. The pre-registered decision rules are read
from results/preregistration.json (written before this script first ran on full data).
"""
from __future__ import annotations

import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (CATALOGUE, DATA_DIR, FORECAST_DIR, LABEL_CACHE, RAW_DIR, RESULTS_DIR, TASKS, read_jsonl,  # noqa: E402
                    set_ram_limit, setup_logger, sha256_text)
from analysis import stats as S  # noqa: E402
from loguru import logger  # noqa: E402

NB = 2000


def assemble() -> list[dict]:
    modes = json.loads((RESULTS_DIR / "modal_modes.json").read_text()) if (RESULTS_DIR / "modal_modes.json").exists() else {}
    succ = json.loads((RESULTS_DIR / "succession_plan.json").read_text()) if (RESULTS_DIR / "succession_plan.json").exists() else {}
    out = []
    for f in sorted(RAW_DIR.glob("*.jsonl")):
        for r in read_jsonl(f):
            variants = [(r["condition"], r["text"])]
            if r["condition"] == "enumerate" and "text_1024" in r:
                variants.append(("enumerate@1024", r["text_1024"]))
            for cond, text in variants:
                lf = LABEL_CACHE / r["task"] / f"{sha256_text(text)}.json"
                if not lf.exists():
                    continue
                lab = json.loads(lf.read_text())
                comp = None
                if cond.startswith("ban:"):
                    comp = bool(lab["passed"] and lab["label"] != cond.split(":", 1)[1])
                elif cond == "succession:2" and r["task"] in succ and not succ[r["task"]].get("skip"):
                    comp = bool(lab["passed"] and lab["label"] not in (succ[r["task"]]["X1"], succ[r["task"]]["X2"]))
                out.append({
                    "task": r["task"], "condition": cond, "paraphrase_id": r["paraphrase_id"], "sample_id": r["sample_id"],
                    "model": r["model"], "decoding": r["decoding"], "label": lab["label"] or "other",
                    "labeller_source": lab["labeller_source"], "passed": bool(lab["passed"]), "wall_s": lab.get("wall_s"),
                    "code_sha256": lab.get("code_sha256"), "code": lab.get("code"), "engine": r["engine"],
                    "steering": r.get("steering"), "n_tokens": r["n_tokens"] if cond != "enumerate@1024" else min(1024, r["n_tokens"]),
                    "finish_reason": r["finish_reason"] if cond != "enumerate@1024" else ("length" if r["n_tokens"] > 1024 else r["finish_reason"]),
                    "format_ok": lab["format_ok"], "enumerated": lab["enumerated"], "names_mentioned": lab["names_mentioned"],
                    "label_runtime": lab.get("label_runtime"), "label_ast": lab.get("label_ast"),
                    "label_judge": lab.get("label_judge"), "compliant": comp, "segment": r.get("segment"),
                    "seed": r.get("seed"), "first_failure": lab.get("first_failure")})
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with (DATA_DIR / "samples.jsonl").open("w") as fh:
        for r in out:
            fh.write(json.dumps(r) + "\n")
    logger.info(f"assembled {len(out)} samples")
    return out


def summarise(rows: list[dict], ref_rows: list[dict] | None, X: str | None, seed: int) -> dict:
    n = len(rows)
    k = sum(r["passed"] for r in rows)
    cl = S.correct_labels(rows)
    lc = Counter(cl)
    d = {
        "n": n, "n_correct": k, "pass_rate": k / n if n else float("nan"), "wilson_ci": S.wilson(k, n),
        "format_ok_rate": float(np.mean([r["format_ok"] for r in rows])) if n else None,
        "enumerated_rate": float(np.mean([r["enumerated"] for r in rows])) if n else None,
        "no_code_rate": float(np.mean([r["label"] == "no_code" for r in rows])) if n else None,
        "truncation_rate": float(np.mean([r["finish_reason"] == "length" for r in rows])) if n else None,
        "names_any_rate": float(np.mean([bool(r["names_mentioned"]) for r in rows])) if n else None,
        "names_X_rate": float(np.mean([X in (r["names_mentioned"] or []) for r in rows])) if (n and X) else None,
        "label_counts": dict(Counter(r["label"] for r in rows)), "label_counts_correct": dict(lc),
        "hill_cc": {"hill1": S.hill(cl, 1) if cl else None, "hill2": S.hill(cl, 2) if cl else None},
        "richness_ge2": sum(1 for v in lc.values() if v >= 2),
        "modal_share_correct": (lc.most_common(1)[0][1] / len(cl)) if cl else None,
        "mean_tokens": float(np.mean([r["n_tokens"] for r in rows])) if n else None,
    }
    if cl:
        d["hill1_ci90_sample"] = S.boot_stat(rows, S.hill1_cc, n_boot=NB, seed=seed, cluster=False)
        d["hill1_ci90_cluster"] = S.boot_stat(rows, S.hill1_cc, n_boot=NB, seed=seed, cluster=True)
    if ref_rows is not None:
        rc = S.correct_labels(ref_rows)
        d["tv_to_reference"] = S.tv(S.dist(cl), S.dist(rc)) if (cl and rc) else None
    return d


def compare(knob: list[dict], ref: list[dict], seed: int, paired: bool) -> dict:
    """delta_hill (plug-in and rarefied at n_min), delta_pass_pts, efficiency, cluster + sample CIs."""
    ck, cr = S.correct_labels(knob), S.correct_labels(ref)
    out = {"n_correct_knob": len(ck), "n_correct_ref": len(cr)}
    if not ck or not cr:
        out.update({"delta_hill_plugin": None, "delta_hill_rarefied": None, "note": "no correct samples"})
        out["delta_pass_pts"] = 100 * (S.pass_rate(ref) - S.pass_rate(knob))
        return out
    n_min = min(len(ck), len(cr))
    m = max(2, int(0.85 * n_min))  # common rarefaction depth, below n_min so bootstrap replicates stay defined
    rf = S.make_rarefied(m, n_rep=30, seed=seed)
    out["n_min"] = n_min
    out["rarefy_to"] = m
    out["hill1_knob"], out["hill1_ref"] = S.hill(ck, 1), S.hill(cr, 1)
    out["hill1_knob_rarefied"] = S.rarefied_hill1(ck, m, 1000, seed)
    out["hill1_ref_rarefied"] = S.rarefied_hill1(cr, m, 1000, seed)
    out["delta_hill_plugin"] = out["hill1_knob"] - out["hill1_ref"]
    out["delta_hill_rarefied"] = out["hill1_knob_rarefied"] - out["hill1_ref_rarefied"]
    out["ci90_plugin_cluster"] = S.boot_diff(knob, ref, S.hill1_cc, n_boot=NB, seed=seed, cluster=True, paired=paired)["ci90"]
    out["ci90_plugin_sample"] = S.boot_diff(knob, ref, S.hill1_cc, n_boot=NB, seed=seed, cluster=False)["ci90"]
    rb = S.boot_diff(knob, ref, rf, n_boot=NB, seed=seed + 1, cluster=True, paired=paired)
    out["ci90_rarefied_cluster"] = rb["ci90"]
    out["ci90_rarefied_sample"] = S.boot_diff(knob, ref, rf, n_boot=NB, seed=seed + 2, cluster=False)["ci90"]
    dp = 100 * (S.pass_rate(ref) - S.pass_rate(knob))
    out["delta_pass_pts"] = dp
    out["efficiency"] = "free gain" if dp <= 1 else out["delta_hill_rarefied"] / dp
    out["tv_to_reference"] = S.tv(S.dist(ck), S.dist(cr))
    return out


def price(curve: list[tuple[float, float, float]], target: float) -> dict:
    """curve = [(c, pass_rate, hill1_cc)] sorted by c; pass-rate cost where hill1_cc first reaches target."""
    pts = [(c, p, h) for c, p, h in curve if h is not None and not (isinstance(h, float) and math.isnan(h))]
    if not pts:
        return {"reached": False, "note": "no correct samples along the curve"}
    p0 = pts[0][1]
    for (c1, p1, h1), (c2, p2, h2) in zip(pts, pts[1:]):
        if h1 >= target:
            return {"reached": True, "c": c1, "pass_rate": p1, "pass_cost_pts": 100 * (p0 - p1)}
        if h2 >= target > h1:
            w = (target - h1) / (h2 - h1)
            pr = p1 + w * (p2 - p1)
            return {"reached": True, "c": c1 + w * (c2 - c1), "pass_rate": pr, "pass_cost_pts": 100 * (p0 - pr)}
    if pts[-1][2] >= target:
        return {"reached": True, "c": pts[-1][0], "pass_rate": pts[-1][1], "pass_cost_pts": 100 * (p0 - pts[-1][1])}
    return {"reached": False, "note": "not reached within the tested range"}


def predict_row(samples: list[dict], seed: int) -> dict:
    out = {}
    for rec in read_jsonl(FORECAST_DIR / "commit_log.jsonl"):
        obj = json.loads((FORECAST_DIR / rec["file"]).read_text())
        t = obj["task"]
        cond = f"ban:{obj['banned'][0]}" if obj["event"].endswith("ban1") else "succession:2"
        rows = [r for r in samples if r["task"] == t and r["condition"] == cond and r["engine"] == "vllm"]
        comp = [r for r in rows if r["passed"] and r["label"] not in obj["banned"]]
        surv = obj["survivors"]
        counts = Counter(r["label"] if r["label"] in surv else "other" for r in comp)
        ncomp = sum(counts.values())
        top = counts.most_common(2)
        realised = "no clear mode"
        if top and top[0][0] != "other":
            lead = (top[0][1] - (top[1][1] if len(top) > 1 else 0)) / ncomp * 100
            if lead >= 15:
                realised = top[0][0]
        ev = {"task": t, "condition": cond, "n_samples": len(rows), "n_compliant": ncomp, "realised_counts": dict(counts),
              "realised_mode": realised, "sha256_ok": None, "forecasts": {}}
        from analysis.forecast import sha_of
        ev["sha256_ok"] = sha_of(obj) == rec["sha256"]
        ev["committed_utc"] = rec["created_utc"]
        ev["n_ban_rows_seen"] = len(rows)
        per = {}
        for name, q in obj["forecasts"].items():
            ls = [math.log(q.get(r["label"] if r["label"] in surv else "other", q["other"])) for r in comp]
            per[name] = ls
            mx = max(q.get(s, 0) for s in surv)
            winners = [s for s in surv if abs(q.get(s, 0) - mx) < 1e-12]
            arg = winners[0] if len(winners) == 1 else "tie"  # a tied (e.g. degenerate uniform) forecast is a miss
            ev["forecasts"][name] = {"mean_log_score": float(np.mean(ls)) if ls else None, "top1": arg,
                                     "top1_hit": bool(arg == realised), "flag": (obj.get("flags") or {}).get(name),
                                     "js_divergence": S.js(q, {}, surv + ["other"], counts_q=dict(counts)) if ncomp else None}
        for rival in ("freq_vllm", "freq_hf", "uniform"):
            if rival in per and "dc" in per and per["dc"]:
                diffs = [{"paraphrase_id": r["paraphrase_id"], "sample_id": r["sample_id"], "d": a - b}
                         for r, a, b in zip(comp, per["dc"], per[rival])]

                def mean_d(rs):
                    return float(np.mean([x["d"] for x in rs])) if rs else float("nan")
                ev["forecasts"]["dc"][f"minus_{rival}"] = {
                    "mean": mean_d(diffs), "ci90_sample": S.boot_stat(diffs, mean_d, NB, seed, cluster=False),
                    "ci90_cluster": S.boot_stat(diffs, mean_d, NB, seed, cluster=True)}
        ranks = sorted(((v["mean_log_score"] if v["mean_log_score"] is not None else -1e9), k)
                       for k, v in ev["forecasts"].items())[::-1]
        ev["log_score_rank"] = [k for _, k in ranks]
        out[obj["event"]] = ev
    return out


def main() -> None:
    setup_logger("analyze")
    set_ram_limit(30)
    samples = assemble()
    modes = json.loads((RESULTS_DIR / "modal_modes.json").read_text())
    cst = json.loads((RESULTS_DIR / "cstar.json").read_text())
    prereg = json.loads((RESULTS_DIR / "preregistration.json").read_text())
    L = int(cst["layer"])
    by = {}
    for r in samples:
        by.setdefault((r["task"], r["condition"]), []).append(r)
    summ = {}
    seed = 11
    for (t, c), rows in sorted(by.items()):
        if c.startswith("steer:"):
            ref = by.get((t, f"steer:dc:c=0:L={L}"))
        else:
            ref = by.get((t, "baseline"))
        summ[f"{t}|{c}"] = summarise(rows, ref, modes[t]["X"], seed)
        seed += 1
    (RESULTS_DIR / "condition_summaries.json").write_text(json.dumps(summ, indent=1, default=float))
    # ---------------- engine check ----------------
    eng = {}
    for t in TASKS:
        a, b = by.get((t, "baseline"), []), by.get((t, f"steer:dc:c=0:L={L}"), [])
        ca, cb = Counter(S.correct_labels(a)), Counter(S.correct_labels(b))
        keys = sorted(set(ca) | set(cb))
        tab = np.array([[ca.get(k, 0) for k in keys], [cb.get(k, 0) for k in keys]])
        test = S.fisher_or_mc(tab, seed=5)
        pa, pb = S.pass_rate(a), S.pass_rate(b)
        diff = S.boot_diff(a, b, S.pass_rate, n_boot=NB, seed=3, cluster=True, paired=False)
        tvv = S.tv(S.dist(S.correct_labels(a)), S.dist(S.correct_labels(b)))
        eng[t] = {"labels": keys, "vllm_counts": tab[0].tolist(), "hf_counts": tab[1].tolist(), "test": test,
                  "pass_vllm": pa, "pass_hf": pb, "pass_diff_ci90": diff["ci90"], "tv": tvv,
                  "pass": bool(tvv < 0.15 and test["p"] > 0.05)}
    (RESULTS_DIR / "engine_check.json").write_text(json.dumps(eng, indent=1, default=float))
    # ---------------- flips and dose-response ----------------
    flips, dose = {}, {}
    for t in TASKS:
        c0 = by.get((t, f"steer:dc:c=0:L={L}"), [])
        mode0 = Counter(S.correct_labels(c0)).most_common(1)[0][0] if S.correct_labels(c0) else None
        for (tt, c), rows in by.items():
            if tt == t and c.startswith("steer:") and c != f"steer:dc:c=0:L={L}":
                flips[f"{t}|{c}"] = S.flips(rows, c0, mode0)
        xs, y1, y2, g = [], [], [], []
        for (tt, c), rows in by.items():
            if tt == t and c.startswith("steer:dc:") and c.endswith(f":L={L}"):
                coef = float(c.split("c=")[1].split(":")[0])
                for r in rows:
                    xs.append(coef)
                    y1.append(int(r["passed"] and r["label"] != mode0))
                    y2.append(int(r["passed"]))
                    g.append(r["paraphrase_id"])
        xs, y1, y2, g = map(np.array, (xs, y1, y2, g))
        keep = xs <= cst[t]["c_star"] + 1e-9
        dose[t] = {"modal_mode_c0": mode0, "correct_and_off_mode": S.logit_cluster(xs, y1, g),
                   "passed": S.logit_cluster(xs, y2, g), "n": int(len(xs)),
                   "restricted_c_le_cstar": {"correct_and_off_mode": S.logit_cluster(xs[keep], y1[keep], g[keep]),
                                             "passed": S.logit_cluster(xs[keep], y2[keep], g[keep]),
                                             "n": int(keep.sum())},
                   "off_mode_rate_by_c": {f"{c:g}": float(y1[xs == c].mean()) for c in sorted(set(xs.tolist()))}}
    (RESULTS_DIR / "flips.json").write_text(json.dumps(flips, indent=1, default=float))
    (RESULTS_DIR / "dose_response.json").write_text(json.dumps(dose, indent=1, default=float))
    # ---------------- buy table ----------------
    buy, rows_csv = {}, []
    for t in TASKS:
        X = modes[t]["X"]
        cs = cst[t]["c_star"]
        c0 = by.get((t, f"steer:dc:c=0:L={L}"), [])
        base = by.get((t, "baseline"), [])
        knobs = {}
        for c in sorted(float(k) for k in cst[t]["pass_rates"]):
            if c > 0:
                knobs[f"steer:dc:c={c:g}:L={L}"] = ("hf", c0, True)
        for nm in ("rand1", "rand2", "placebo", "breadth", "dcxfer"):
            knobs[f"steer:{nm}:c={cs:g}:L={L}"] = ("hf", c0, True)
        for pc in ("enumerate", "enumerate@1024", f"ban:{X}", f"mention:{X}", "succession:2"):
            # different paraphrase texts than the baseline: resample clusters independently (unpaired)
            knobs[pc] = ("vllm", base, False)
        buy[t] = {}
        for i, (k, (eng_name, ref, paired)) in enumerate(knobs.items()):
            rows = by.get((t, k))
            if not rows:
                continue
            cmp_ = compare(rows, ref, seed=100 + i, paired=paired)
            cmp_["reference"] = "steer:dc:c=0 (HF)" if eng_name == "hf" else "baseline (vLLM)"
            cmp_["pass_rate"] = S.pass_rate(rows)
            buy[t][k] = cmp_
            rows_csv.append({"task": t, "knob": k, "reference": cmp_["reference"], "pass_rate": round(cmp_["pass_rate"], 4),
                             "delta_pass_pts": round(cmp_["delta_pass_pts"], 2),
                             "delta_hill_plugin": cmp_.get("delta_hill_plugin"),
                             "delta_hill_rarefied": cmp_.get("delta_hill_rarefied"), "n_min": cmp_.get("n_min"),
                             "ci90_rarefied_cluster": cmp_.get("ci90_rarefied_cluster"),
                             "efficiency": cmp_.get("efficiency")})
        # vLLM-referenced steering comparison only if the engine check passes
        if eng[t]["pass"]:
            rows = by.get((t, f"steer:dc:c={cs:g}:L={L}"))
            if rows:
                buy[t]["steer_vs_vllm_baseline"] = compare(rows, base, seed=999, paired=False)
                buy[t]["steer_vs_vllm_baseline"]["pass_rate"] = S.pass_rate(rows)
                buy[t]["steer_vs_vllm_baseline"]["reference"] = "baseline (vLLM), cross-engine"

        curve = []
        for c in sorted(float(k) for k in cst[t]["pass_rates"]):
            rows = by.get((t, f"steer:dc:c={c:g}:L={L}"), [])
            cl = S.correct_labels(rows)
            curve.append((c, S.pass_rate(rows), S.hill(cl, 1) if cl else None))
        buy[t]["_hill_price"] = {"curve": curve, "hill2": price(curve, 2.0), "hill3": price(curve, 3.0)}
    (RESULTS_DIR / "buy_table.json").write_text(json.dumps(buy, indent=1, default=float))
    with (RESULTS_DIR / "buy_table.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows_csv[0].keys()))
        w.writeheader()
        w.writerows(rows_csv)
    # ---------------- PREDICT row ----------------
    pr = predict_row(samples, seed=21)
    (RESULTS_DIR / "predict_row.json").write_text(json.dumps(pr, indent=1, default=float))
    # ---------------- move vs flatten ----------------
    mvf = {}
    for t in TASKS:
        X = modes[t]["X"]
        cs = cst[t]["c_star"]
        mvf[t] = {}
        for k in (f"ban:{X}", f"steer:dc:c={cs:g}:L={L}", "enumerate"):
            b = buy[t].get(k)
            if not b or b.get("delta_hill_rarefied") is None:
                continue
            rows = by.get((t, k), [])
            mc = Counter(S.correct_labels(rows)).most_common(1)
            rmode = mc[0][0] if mc else None
            ci = b["ci90_rarefied_cluster"]
            mvf[t][k] = {"tv": b["tv_to_reference"], "delta_hill_rarefied": b["delta_hill_rarefied"], "ci90": ci,
                         "realised_mode": rmode, "moves": bool(rmode != X and (ci[0] <= 0 <= ci[1] or ci[1] < 0.5)),
                         "flattens": bool(ci[0] > 0)}
    (RESULTS_DIR / "move_vs_flatten.json").write_text(json.dumps(mvf, indent=1, default=float))
    # ---------------- screen decision ----------------
    ct = json.loads((RESULTS_DIR / "commitment_test.json").read_text()) if (RESULTS_DIR / "commitment_test.json").exists() else None
    verdict = {"rules": prereg["rules"], "per_task": {}}
    for t in TASKS:
        X = modes[t]["X"]
        cs = cst[t]["c_star"]
        flag = cst[t].get("flag")
        thr = cst[t]["threshold"]
        cp = [float(c) for c, p in cst[t]["pass_rates"].items() if float(c) > 0 and p >= thr]
        k_main = f"steer:dc:c={cs:g}:L={L}"
        b = buy[t].get(k_main, {})
        ci = b.get("ci90_rarefied_cluster")
        s_flat = bool(ci and ci[0] > 0 and flag is None)
        s_flat_any = any((buy[t].get(f"steer:dc:c={c:g}:L={L}", {}).get("ci90_rarefied_cluster") or [-1, -1])[0] > 0
                         for c in cp)
        spec = {}
        dcrows = by.get((t, k_main), [])
        for nm in ("rand1", "rand2", "placebo"):
            rr = by.get((t, f"steer:{nm}:c={cs:g}:L={L}"))
            if rr and dcrows and S.correct_labels(rr) and S.correct_labels(dcrows):
                n_min = min(len(S.correct_labels(rr)), len(S.correct_labels(dcrows)))
                m = max(2, int(0.85 * n_min))
                spec[nm] = S.boot_diff(dcrows, rr, S.make_rarefied(m, 30, 7), n_boot=NB, seed=31, cluster=True,
                                       paired=True)
                spec[nm]["point"] = (S.rarefied_hill1(S.correct_labels(dcrows), m, 1000, 7)
                                     - S.rarefied_hill1(S.correct_labels(rr), m, 1000, 7))
                spec[nm]["n_min"], spec[nm]["rarefy_to"] = n_min, m
        s_specific = bool(spec and all(v["ci90"][0] > 0 for k, v in spec.items() if k in ("rand1", "rand2"))
                          and ("placebo" not in spec or spec["placebo"]["ci90"][0] > 0))
        vs_prompt = {}
        for pk in ("enumerate", f"ban:{X}"):
            if pk in buy[t] and b:
                vs_prompt[pk] = {"dc_efficiency": b.get("efficiency"), "prompt_efficiency": buy[t][pk].get("efficiency"),
                                 "dc_delta_hill_rarefied": b.get("delta_hill_rarefied"), "dc_ci90": ci,
                                 "prompt_delta_hill_rarefied": buy[t][pk].get("delta_hill_rarefied"),
                                 "prompt_ci90": buy[t][pk].get("ci90_rarefied_cluster")}
                if ci and buy[t][pk].get("ci90_rarefied_cluster"):
                    pc = buy[t][pk]["ci90_rarefied_cluster"]
                    vs_prompt[pk]["best_knob"] = ("dc" if ci[0] > pc[1] else (pk if pc[0] > ci[1] else "not separated"))
        s_commit = None
        if ct:
            Lc = str(ct["layer_star"])
            s_commit = ct["per_task"][t][Lc]["ban"].get(X, {}).get("verdict")
        verdict["per_task"][t] = {"X": X, "c_star": cs, "c_star_flag": flag, "correctness_preserving_c": cp,
                                  "S_flat": s_flat, "S_flat_any_preserving_c": s_flat_any, "S_flat_ci90": ci,
                                  "delta_hill_rarefied": b.get("delta_hill_rarefied"), "S_specific": s_specific,
                                  "specificity": spec, "S_vs_prompt": vs_prompt, "S_commit": s_commit}
    pt = verdict["per_task"]
    has_c = [t for t in TASKS if pt[t]["correctness_preserving_c"] and pt[t]["c_star_flag"] is None]
    flat = [t for t in TASKS if pt[t]["S_flat"]]
    adv = [t for t in flat if pt[t]["S_specific"]]
    if not has_c:
        overall = "INCONCLUSIVE"
    elif adv and all((pt[o]["delta_hill_rarefied"] or 0) > 0 for o in TASKS if o not in adv):
        overall = "ADVANCE"
    elif flat:
        overall = "PARTIAL"
    elif not any(pt[t]["S_flat_any_preserving_c"] for t in has_c):
        overall = "DROP"
    else:
        overall = "PARTIAL"
    verdict["S_flat_tasks"] = flat
    verdict["S_flat_status"] = "both" if len(flat) == 2 else ("partial" if flat else "fails")
    verdict["tasks_with_correctness_preserving_c"] = has_c
    verdict["overall"] = overall
    verdict["predict_summary"] = {k: {"rank": v["log_score_rank"], "realised": v["realised_mode"],
                                      "dc_top1": v["forecasts"].get("dc", {}).get("top1"),
                                      "dc_top1_hit": v["forecasts"].get("dc", {}).get("top1_hit"),
                                      "dc_flag": v["forecasts"].get("dc", {}).get("flag"),
                                      "n_compliant": v["n_compliant"]} for k, v in pr.items()}
    (RESULTS_DIR / "screen_verdict.json").write_text(json.dumps(verdict, indent=1, default=float))
    logger.info(f"SCREEN VERDICT: {overall}; per task: " + json.dumps({t: {k: pt[t][k] for k in ('S_flat', 'S_specific', 'S_commit', 'c_star')} for t in TASKS}))


if __name__ == "__main__":
    main()
