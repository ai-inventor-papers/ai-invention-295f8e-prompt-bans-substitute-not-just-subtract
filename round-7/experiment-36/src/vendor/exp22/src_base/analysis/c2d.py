#!/usr/bin/env python3
"""9.1 C2d: is there an X-free, task-general prohibition direction? ADD (sufficiency on the neutral twin) against
norm-matched random directions under CRN, SUBTRACT (necessity on the ban prompt), landings, dose-response."""

from __future__ import annotations

from collections import Counter
from typing import Any

import numpy as np

from analysis.common import (NOT_ATTEMPTED, avoided, boot_mean_diff, by_slot, holm, js_divergence, mcnemar_one_sided,
                             paired, rows_of, shares)
from cfg import DATA_DIR, DEFAULT, PRED_DIR, RAND_SEEDS, SAMPLED_TASKS, read_json, read_jsonl

K10 = list(range(10))


def is_default(r: dict[str, Any]) -> int | None:
    if r["label"] in NOT_ATTEMPTED:
        return None
    return int(r["label"] == DEFAULT[r["task"]])


def realised(task: str) -> dict[str, Any]:
    recs = [r for r in read_jsonl(DATA_DIR / "realised_norms.jsonl") if r["task"] == task]
    out: dict[str, Any] = {}
    for arm in sorted({r["arm"] for r in recs}):
        rs = [r for r in recs if r["arm"] == arm]
        blocks = sorted({int(b) for r in rs for b in r["disp_S_mean_norm"]})
        o = {"disp_S_mean_norm": {b: float(np.mean([r["disp_S_mean_norm"][str(b)] for r in rs])) for b in blocks},
             "disp_R_norm": {b: float(np.mean([r["disp_R_norm"][str(b)] for r in rs])) for b in blocks},
             "edit_norm_mean": {b: float(np.mean([r["edit_norm_mean"][str(b)] for r in rs if str(b) in
                                                  r["edit_norm_mean"]])) for b in range(12, 24)
                                if any(str(b) in r["edit_norm_mean"] for r in rs)}}
        if any("rel_err_along_u" in r for r in rs):
            o["rel_err_along_u_max"] = float(max(max(r["rel_err_along_u"].values()) for r in rs
                                                 if "rel_err_along_u" in r))
            o["target_norm_mean"] = {b: float(np.mean([r["target_norm_mean"][str(b)] for r in rs
                                                       if "target_norm_mean" in r])) for b in range(12, 24)}
        out[arm] = o
    return out


def js_null(rows_a: list[dict[str, Any]], rows_b: list[dict[str, Any]], task: str, n: int = 1000,
            seed: int = 0) -> dict[str, Any]:
    """JS(landing_a, landing_b) against a within-template arm-label permutation null of the non-default rows."""
    x = DEFAULT[task]
    A = [r for r in rows_a if r["label"] not in NOT_ATTEMPTED and r["label"] != x]
    B = [r for r in rows_b if r["label"] not in NOT_ATTEMPTED and r["label"] != x]
    obs = js_divergence(Counter(r["label"] for r in A), Counter(r["label"] for r in B))
    if not A or not B:
        return {"js": obs, "null_q95": None, "p": None}
    rng = np.random.default_rng(seed)
    pool = [(r["template"], r["label"], 0) for r in A] + [(r["template"], r["label"], 1) for r in B]
    temps = sorted({p[0] for p in pool})
    null = []
    for _ in range(n):
        ca: Counter = Counter()
        cb: Counter = Counter()
        for w in temps:
            items = [p for p in pool if p[0] == w]
            labs = [p[1] for p in items]
            side = rng.permutation([p[2] for p in items])
            for l, s in zip(labs, side):
                (ca if s == 0 else cb)[l] += 1
        null.append(js_divergence(ca, cb))
    null = np.array(null)
    return {"js": obs, "null_q95": float(np.nanquantile(null, 0.95)), "p": float(np.mean(null >= obs))}


def analyse_task(rows: list[dict[str, Any]], task: str, forecast: dict[str, Any] | None) -> dict[str, Any]:
    arms = sorted({r["arm"] for r in rows if r["task"] == task and "label" in r and not r["arm"].startswith("U7")})
    summ = {a: shares(rows_of(rows, task, a), task) for a in arms}
    summ_dis = {a: shares(rows_of(rows, task, a), task, disputed_as_default=True) for a in arms}
    ban = summ.get("BAN")
    res: dict[str, Any] = {"arms": summ, "arms_disputed_as_default": {a: {"avoidance": s["avoidance"]}
                                                                       for a, s in summ_dis.items()}}
    gate = bool(ban and ban["avoidance"] >= 0.5 and ban["n_nondefault"] >= 20)
    res["event_gate"] = {"pass": gate, "ban_avoidance": ban["avoidance"] if ban else None,
                         "ban_n_nonbanned": ban["n_nondefault"] if ban else None}
    # ADD vs RAND (CRN flip tables, one-sided exact McNemar, Holm over 3 controls x 2 alphas)
    tests, keys = [], []
    for al in (1.0, 2.0):
        add = rows_of(rows, task, f"ADD_a{al}", K10)
        for s in RAND_SEEDS:
            rnd = rows_of(rows, task, f"RAND{s}_a{al}", K10)
            if not add or not rnd:
                continue
            x, y = paired(add, rnd)
            t = mcnemar_one_sided(x, y)
            t.update({"alpha": al, "seed": s, "add_avoid": float(np.mean(x)) if x else None,
                      "rand_avoid": float(np.mean(y)) if y else None})
            tests.append(t)
            keys.append((al, s))
    adj = holm([t["p_one_sided"] for t in tests]) if tests else []
    for t, p in zip(tests, adj):
        t["p_holm"] = p
    res["add_vs_rand"] = tests
    ban_modal = ban["modal_nondefault"] if ban else None
    passes = {}
    for al in (1.0, 2.0):
        ts = [t for t in tests if t["alpha"] == al]
        a = summ.get(f"ADD_a{al}")
        all_sig = len(ts) == 3 and all(t["p_holm"] < 0.05 for t in ts)
        land_ok = bool(a and a["n_nondefault"] >= 10 and ban_modal is not None and a["modal_nondefault"] == ban_modal)
        passes[al] = {"all_three_holm_sig": all_sig, "n_controls": len(ts), "landing_match": land_ok,
                      "add_modal": a["modal_nondefault"] if a else None, "add_n_nondefault": a["n_nondefault"] if a
                      else 0, "pass": bool(all_sig and land_ok)}
    res["add_pass_by_alpha"] = passes
    res["add_pass"] = any(v["pass"] for v in passes.values())
    res["add_avoidance_contrast_only"] = any(v["all_three_holm_sig"] for v in passes.values())
    # random range: at neither alpha does ADD exceed every RAND control (all 50 slots of each arm)
    above = {}
    for al in (1.0, 2.0):
        a = summ.get(f"ADD_a{al}")
        rs = [summ.get(f"RAND{s}_a{al}") for s in RAND_SEEDS]
        rs = [r for r in rs if r]
        if a and rs:
            above[al] = a["avoidance"] > max(r["avoidance"] for r in rs)
    res["add_above_max_rand"] = above
    res["add_within_random_range"] = bool(above) and not any(above.values())
    # dose-response
    res["dose_response"] = {al: summ[f"ADD_a{al}"]["avoidance"] for al in (0.5, 1.0, 2.0) if f"ADD_a{al}" in summ}
    # SUBTRACT: Delta = banned share(SUB) - banned share(BAN) on the same slots, paired bootstrap over slots
    sub: dict[str, Any] = {}
    banr = rows_of(rows, task, "BAN")
    for arm in ("SUB_plain", "SUB_affine", "SUB_rand9001"):
        sr = rows_of(rows, task, arm)
        if not sr or not banr:
            continue
        x, y = paired(sr, banr, fn=is_default)
        d, ci = boot_mean_diff(x, y, seed=1)
        sub[arm] = {"delta_banned_share": d, "ci95": ci, "n_pairs": len(x),
                    "sub_banned_share": float(np.mean(x)) if x else None,
                    "ban_banned_share_same_slots": float(np.mean(y)) if y else None,
                    "flip": {"sub_default_ban_not": sum(1 for a, b in zip(x, y) if a == 1 and b == 0),
                             "sub_not_ban_default": sum(1 for a, b in zip(x, y) if a == 0 and b == 1)}}
    res["subtract"] = sub
    if "SUB_rand9001" in sub:
        best = max((sub[a]["delta_banned_share"] for a in ("SUB_plain", "SUB_affine") if a in sub), default=None)
        res["necessity_credited_to_v"] = bool(best is not None and best - sub["SUB_rand9001"]["delta_banned_share"]
                                              >= 0.15)
    res["sub_gated"] = bool(ban and ban["default_share"] <= 0.5)
    # landings: JS(ADD best alpha landing, ban landing) vs permutation null; forecast hit
    if forecast and forecast.get("best_alpha"):
        al = forecast["best_alpha"]
        res["js_add_vs_ban"] = js_null(rows_of(rows, task, f"ADD_a{al}"), banr, task)
        res["forecast"] = {"best_alpha": al, "forecast_modal": forecast.get("forecast_modal"),
                           "ban_modal": ban_modal, "hit": bool(forecast.get("forecast_modal") is not None
                                                               and forecast.get("forecast_modal") == ban_modal),
                           "testable": forecast.get("forecast_testable")}
    res["realised_norms"] = realised(task)
    return res


def run_c2d(rows: list[dict[str, Any]]) -> dict[str, Any]:
    fc = read_json(PRED_DIR / "c2d_landings.json")["tasks"] if (PRED_DIR / "c2d_landings.json").exists() else {}
    per = {t: analyse_task(rows, t, fc.get(t)) for t in SAMPLED_TASKS if any(r["task"] == t for r in rows)}
    denom = [t for t, v in per.items() if v["event_gate"]["pass"]]
    n_pass = sum(per[t]["add_pass"] for t in denom)
    gated_sub = [t for t, v in per.items() if v["sub_gated"] and "SUB_plain" in v["subtract"]]
    deltas = np.array([per[t]["subtract"]["SUB_plain"]["delta_banned_share"] for t in gated_sub], float)
    pooled: dict[str, Any] = {"tasks": gated_sub, "delta": float(deltas.mean()) if len(deltas) else None}
    if len(deltas) >= 2:
        rng = np.random.default_rng(7)
        bs = [deltas[rng.integers(0, len(deltas), len(deltas))].mean() for _ in range(5000)]
        pooled["ci95_task_bootstrap"] = [float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975))]
        jk = [np.delete(deltas, i).mean() for i in range(len(deltas))]
        pooled["jackknife_range"] = [float(min(jk)), float(max(jk))]
    elif len(deltas) == 1:
        pooled["ci95_task_bootstrap"] = per[gated_sub[0]]["subtract"]["SUB_plain"]["ci95"]
        pooled["note"] = "one gated task: slot-bootstrap CI of that task"
    within_rand = [t for t, v in per.items() if v["add_within_random_range"]]
    n_tasks = len(per)
    if len(denom) >= 2:
        add_ok = n_pass >= (2 / 3) * len(denom)
    else:
        add_ok = False
    ci = pooled.get("ci95_task_bootstrap")
    sub_ok = bool(pooled["delta"] is not None and pooled["delta"] >= 0.3 and ci and ci[0] > 0)
    if add_ok and sub_ok:
        verdict = "SUPPORTED"
    elif n_tasks and len(within_rand) > n_tasks / 3:
        verdict = "DISCONFIRMED"
    else:
        verdict = "PARTIAL"
    if len(denom) < 2:
        verdict_note = "fewer than 2 tasks pass the event gate: the ADD landing clause is descriptive (F6)"
    else:
        verdict_note = ""
    return {"per_task": per, "denominator_tasks": denom, "n_add_pass": n_pass, "pooled_subtract": pooled,
            "tasks_add_within_random_range": within_rand, "verdict": verdict, "verdict_note": verdict_note,
            "rule": "SUPPORTED iff ADD passes on >= 2/3 of the gated tasks AND pooled Delta >= 0.3 with CI lower "
                    "bound > 0; DISCONFIRMED iff ADD avoidance is within the random range on > 1/3 of tasks; "
                    "else PARTIAL"}


def exploratory_random_distribution(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """EXPLORATORY (outside the frozen rule): ADD alpha 1 against every random direction sampled at alpha 1 (the 3
    frozen seeds plus up to 12 extra seeds 9004-9015, identical construction) on the same CRN slots k 0-9."""
    out: dict[str, Any] = {}
    for t in SAMPLED_TASKS:
        add = rows_of(rows, t, "ADD_a1.0", K10)
        rands = sorted({r["arm"] for r in rows if r["task"] == t and r["arm"].startswith("RAND")
                        and r["arm"].endswith("_a1.0")})
        if not add or len(rands) <= 3:
            continue
        av = {}
        tests = {}
        for a in rands:
            rr = rows_of(rows, t, a, K10)
            x, y = paired(add, rr)
            if not x:
                continue
            av[a] = float(np.mean(y))
            tests[a] = mcnemar_one_sided(x, y)
        x_add = [avoided(r) for r in add if avoided(r) is not None]
        a_add = float(np.mean(x_add)) if x_add else float("nan")
        vals = np.array(list(av.values()))
        out[t] = {"add_avoidance_k0_9": a_add, "random_avoidance": av, "n_random": len(av),
                  "add_percentile_among_random": float((vals < a_add).mean() + 0.5 * (vals == a_add).mean()),
                  "n_random_beaten_p05_uncorrected": int(sum(v["p_one_sided"] < 0.05 for v in tests.values())),
                  "random_mean": float(vals.mean()), "random_q90": float(np.quantile(vals, 0.9)),
                  "label": "exploratory; not part of the frozen C2d rule"}
    return out
