#!/usr/bin/env python3
"""Frozen panel-A analysis (committed at #0; never edited afterwards -- any extra analysis lives in posthoc.py and
is labelled POST HOC).

Per-unit prediction (computed from the twin, base and rival rows BEFORE any push of that unit; committed):
  default = modal correct-only twin label if its share >= 0.6 among correct twin programs at N >= 50, else NO DEFAULT
  beta_u = #(correct base, catalogue label != default) / #(correct base, valid)  [valid attempts if < 20 correct]
  r_u = most frequent correct non-default catalogue label among base programs (ties: valid-attempt count, then
  catalogue order); predicted class MOVABLE iff beta_u >= 0.05; predicted landing r_u.
Final analysis (after the pushes): escape table (escape_rule), E_u, landing L_u, PN excess S_u, knob rows,
A1 (Spearman / Kendall / rivals / bootstrap), A2 (hits, Poisson-binomial, log scores), repertoire check, Extra arm A.
"""

from __future__ import annotations

import glob
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg5 import (ALPHAS, BENCH, BETA_MOVABLE, BOOT_SEED, COMMIT_LOG, DEFAULT_SHARE, DEPTH, E22, ESC_SEEDS,  # noqa
                  EVAL3, EXCLUDE, EXISTING, EXISTING_DEFAULT, ITER4_E, LAB_DIR, MIN_CORRECT_BASE, N_BOOT,
                  N_BOOT_RIVAL, PATH_TASKS, PRED, RESULTS, ROOT, TEMPLATE_IDS, UNIT_DIRS, read_json, read_jsonl,
                  sha256_file, unit_dir, write_json)
from escape_rule import cell_decision, escape_table, share, twin_stats  # noqa: E402
from metrics import (goods_coverage, hill1_rarefied, kendall_b, log_score, mixture_q, perm_p_spearman,  # noqa
                     poisson_binomial_sf, spearman, wilcoxon_exact, wilson)

PATH_CAT = {"T1": ["bfs", "dfs", "bibfs", "iddfs", "astar_gbfs", "dijkstra"],
            "T2": ["dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"]}
RIVALS = [("opening_margin", -1), ("merit_runtime_min", -1), ("merit_length_min", -1), ("twin_modal_share", -1),
          ("novelty_share", +1)]


# ------------------------------------------------------------------------------------------------ data access
def catalogue(task: str) -> list[str]:
    if task in UNIT_DIRS:
        return [c["mode"] for c in read_json(unit_dir(task) / "spec.json")["catalogue"]]
    if task in PATH_CAT:
        return list(PATH_CAT[task])
    for d in BENCH.iterdir():
        if d.is_dir() and d.name.startswith(task + "_"):
            return [c["mode"] for c in read_json(d / "spec.json")["catalogue"]]
    raise KeyError(task)


def labels(task: str) -> list[dict[str, Any]]:
    seen, out = set(), []
    for r in read_jsonl(LAB_DIR / f"{task}.jsonl"):
        if r["sample_id"] in seen:
            continue
        seen.add(r["sample_id"])
        out.append(r)
    return out


def rows_of(rows: list[dict[str, Any]], arm: str | None = None, model: str | None = None,
            prefix: str | None = None) -> list[dict[str, Any]]:
    out = rows
    if arm is not None:
        out = [r for r in out if r["arm"] == arm]
    if prefix is not None:
        out = [r for r in out if r["arm"].startswith(prefix)]
    if model is not None:
        out = [r for r in out if r["model"] == model]
    return out


def comp(rows: list[dict[str, Any]], correct_only: bool) -> dict[str, int]:
    return dict(Counter(r["label"] for r in rows if r["label"] not in EXCLUDE and (r.get("passed") or not
                                                                                  correct_only)))


# ------------------------------------------------------------------------------------------------ prediction
def twin_default(twin: list[dict[str, Any]]) -> dict[str, Any]:
    corr = [r["label"] for r in twin if r.get("passed") and r["label"] not in EXCLUDE]
    c = Counter(corr)
    if not c:
        return {"default": None, "share": None, "n_twin": len(twin), "n_correct": 0}
    lab, k = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0]
    sh = k / len(corr)
    ok = len(twin) >= 50 and sh >= DEFAULT_SHARE and lab != "other"
    return {"default": lab if ok else None, "modal": lab, "share": sh, "n_twin": len(twin), "n_correct": len(corr)}


def beta_stats(base: list[dict[str, Any]], default: str, cat: list[str]) -> dict[str, Any]:
    valid = [r for r in base if r["label"] not in EXCLUDE]
    corr = [r for r in valid if r.get("passed")]
    use = corr if len(corr) >= MIN_CORRECT_BASE else valid
    flag = None if len(corr) >= MIN_CORRECT_BASE else "attempts_used_lt20_correct"
    k = sum(1 for r in use if r["label"] in cat and r["label"] != default)
    n = len(use)
    lo, hi = wilson(k, n)
    cnt = Counter(r["label"] for r in corr if r["label"] in cat and r["label"] != default)
    vcnt = Counter(r["label"] for r in valid if r["label"] in cat and r["label"] != default)
    if not cnt and flag:
        cnt = vcnt
    r_u = None
    if cnt:
        r_u = sorted(cnt, key=lambda m: (-cnt[m], -vcnt.get(m, 0), cat.index(m)))[0]
    return {"beta": k / n if n else None, "beta_k": k, "beta_n": n, "beta_ci": [lo, hi], "flag": flag,
            "r": r_u, "n_rows": len(base), "n_valid": len(valid), "n_correct": len(corr),
            "pass_rate": len(corr) / len(base) if base else None,
            "comp_correct": dict(Counter(r["label"] for r in corr)),
            "comp_valid": dict(Counter(r["label"] for r in valid)),
            "hill1": hill1_rarefied([r["label"] for r in corr], DEPTH, seed=BOOT_SEED)}


def unit_prediction(u: str, rivals: dict[str, Any], base_audit: dict[str, Any] | None = None) -> dict[str, Any]:
    rows = labels(u)
    cat = catalogue(u)
    twin = rows_of(rows, "TWIN", "instruct")
    td = twin_default(twin)
    out: dict[str, Any] = {"unit": u, "catalogue": cat, "K": len(cat), **{f"twin_{k}": v for k, v in td.items()},
                           "twin_comp_correct": comp(twin, True), "twin_comp_valid": comp(twin, False),
                           "twin_pass": sum(1 for r in twin if r.get("passed")) / len(twin) if twin else None}
    d = td["default"]
    out["default"] = d
    base = rows_of(rows, "BASE", "base")
    plain = rows_of(rows, "PLAINC", "base")
    if d is None:
        out["status"] = "NO_DEFAULT"
        out["base_chat"] = beta_stats(base, td.get("modal") or "", cat)
        return out
    out["status"] = "OK"
    bc = beta_stats(base, d, cat)
    out["base_chat"] = bc
    out["base_plain"] = beta_stats(plain, d, cat) if plain else None
    out["beta"] = bc["beta"]
    out["beta_ci"] = bc["beta_ci"]
    out["r"] = bc["r"]
    # sensitivity: audited catalogue-variant 'other' programs counted as off-default
    extra = (base_audit or {}).get("catalogue_variant_other_correct", 0)
    out["beta_other"] = ((bc["beta_k"] + extra) / bc["beta_n"]) if bc["beta_n"] else None
    out["predicted_class"] = "MOVABLE" if (bc["beta"] is not None and bc["beta"] >= BETA_MOVABLE) else "IMMOVABLE"
    out["predicted_landing"] = bc["r"]
    out["rivals"] = rivals
    return out


# ------------------------------------------------------------------------------------------------ final analysis
def unit_outcome(task: str, default: str, cat: list[str]) -> dict[str, Any]:
    rows = labels(task)
    cs = set(cat)
    twin = rows_of(rows, "TWIN", "instruct")
    esc = rows_of(rows, prefix="ESC_", model="instruct")
    tab = escape_table(esc, twin, ESC_SEEDS, ALPHAS, cs, default)
    # landing tie-break by catalogue order
    if tab["landing_counts"]:
        lc = tab["landing_counts"]
        tab["landing"] = sorted(lc, key=lambda m: (-lc[m], cat.index(m) if m in cat else 99))[0]
    tw = tab["twin"]
    pn = {}
    for a in ALPHAS:
        pr = rows_of(rows, f"PN_a{a}", "instruct")
        s = share(pr, cs, default)
        pn[str(a)] = {**s, "excess": (s["share"] - tw["share"]) if (s["share"] is not None and tw["share"] is not None)
                      else None}
    exc = [v["excess"] for v in pn.values() if v["excess"] is not None]
    S = float(np.mean(exc)) if exc else None
    return {"escape": tab, "pn": pn, "S": S, "E": tab["E"], "E1": tab["E_by_alpha"].get("1.0"),
            "E2": tab["E_by_alpha"].get("2.0"), "movable_obs": tab["movable_obs"], "landing": tab["landing"]}


def knob_rows(task: str, default: str, cat: list[str]) -> dict[str, Any]:
    rows = labels(task)
    cs = set(cat)
    out = {}
    for arm, sel in (("TWIN", rows_of(rows, "TWIN", "instruct")), ("PN_a1", rows_of(rows, "PN_a1.0", "instruct")),
                     ("PN_a2", rows_of(rows, "PN_a2.0", "instruct")), ("T1.3", rows_of(rows, "T1.3", "instruct")),
                     ("NOVELTY", rows_of(rows, "NOVELTY", "instruct")), ("BASE", rows_of(rows, "BASE", "base")),
                     ("PLAINC", rows_of(rows, "PLAINC", "base"))):
        if not sel:
            continue
        s = share(sel, cs, default)
        corr = [r["label"] for r in sel if r.get("passed") and r["label"] not in EXCLUDE]
        h = hill1_rarefied(corr, DEPTH, seed=BOOT_SEED)
        out[arm] = {"n": len(sel), "pass": s["pass"], "off_default_share": s["share"], "hill1_correct": h["hill1"],
                    "hill1_depth": h["depth"], "hill1_flag_below_depth": h["flag_below_depth"],
                    "goods_coverage": goods_coverage(corr), "comp_correct": dict(Counter(corr))}
    return out


def a1_analysis(units: list[dict[str, Any]]) -> dict[str, Any]:
    """units: [{'unit', 'beta', 'E', 'S', 'rivals': {...}, 'cluster'}] with a default."""
    xs = [u for u in units if u.get("beta") is not None and u.get("E") is not None]
    n = len(xs)
    beta = [u["beta"] for u in xs]
    E = [u["E"] for u in xs]
    out: dict[str, Any] = {"n_units": n, "units": [u["unit"] for u in xs], "beta": beta, "E": E}
    pr = perm_p_spearman(beta, E, seed=BOOT_SEED)
    out["rho_beta_E"] = pr["rho"]
    out["perm_p_one_sided"] = pr["p"]
    out["perm_exact"] = pr["exact"]
    out["kendall_tau_b"] = kendall_b(beta, E)
    Ss = [u.get("S") for u in xs]
    out["rho_beta_S"] = spearman(beta, Ss) if all(s is not None for s in Ss) else None
    lowc = [u for u in xs if u["beta"] < BETA_MOVABLE]
    hiw = [u for u in xs if u["beta"] >= 0.2]
    out["collapsed_immovable"] = (sum(1 for u in lowc if u["E"] == 0) / len(lowc)) if lowc else None
    out["n_collapsed"] = len(lowc)
    out["diverse_immovable"] = (sum(1 for u in hiw if u["E"] == 0) / len(hiw)) if hiw else None
    out["n_diverse"] = len(hiw)
    # rivals
    rng = np.random.default_rng(BOOT_SEED)
    riv = {}
    for name, sign in RIVALS:
        vals = [u["rivals"].get(name) for u in xs]
        if any(v is None for v in vals) or n < 3:
            riv[name] = {"rho_r_E": None, "delta": None, "note": "undefined for some unit"}
            continue
        rr = spearman(vals, E)
        rb = out["rho_beta_E"]
        delta = (rb - sign * rr) if (rb == rb and rr == rr) else None
        boots = []
        for _ in range(N_BOOT_RIVAL):
            idx = rng.integers(0, n, n)
            b1 = spearman([beta[i] for i in idx], [E[i] for i in idx])
            b2 = spearman([vals[i] for i in idx], [E[i] for i in idx])
            if b1 == b1 and b2 == b2:
                boots.append(b1 - sign * b2)
        ci = [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))] if len(boots) >= 100 else None
        riv[name] = {"sign": sign, "rho_r_E": rr, "delta": delta, "delta_ci95": ci, "n_valid_boot": len(boots),
                     "values": vals}
    out["rivals"] = riv
    # descriptive rivals (outside the pre-registered set)
    for name in ("K", "base_pass_rate"):
        vals = [u["rivals"].get(name) for u in xs]
        out[f"descriptive_rho_{name}_E"] = spearman(vals, E) if all(v is not None for v in vals) else None
    # pooled-threshold wording (the decision itself is pooled next round)
    beats = [v.get("delta") is not None and v["delta"] > 0 for v in riv.values()]
    cons = (out["rho_beta_E"] == out["rho_beta_E"] and out["rho_beta_E"] is not None and out["rho_beta_E"] >= 0.6 and
            (out["collapsed_immovable"] is None or out["collapsed_immovable"] >= 0.8) and all(beats))
    out["wording"] = ("consistent with the pooled thresholds (rho >= 0.6, >= 80% collapsed immovable, beta ahead of "
                      "each rival)" if cons else
                      "not consistent with the pooled thresholds (rho >= 0.6, >= 80% collapsed immovable, beta ahead "
                      "of each rival)")
    return out


def measurement_bootstrap(unit_data: list[dict[str, Any]], n_boot: int = N_BOOT) -> dict[str, Any]:
    """Resample base programs within units (beta) and rows within escape cells / twin (E); recompute rho."""
    rng = np.random.default_rng(BOOT_SEED + 1)
    rhos = []
    for _ in range(n_boot):
        bs, es = [], []
        for ud in unit_data:
            base, d, cat = ud["base_rows"], ud["default"], ud["catalogue"]
            if not base:
                continue
            bb = [base[i] for i in rng.integers(0, len(base), len(base))]
            valid = [r for r in bb if r["label"] not in EXCLUDE]
            corr = [r for r in valid if r.get("passed")]
            use = corr if len(corr) >= MIN_CORRECT_BASE else valid
            if not use:
                continue
            beta = sum(1 for r in use if r["label"] in cat and r["label"] != d) / len(use)
            tw = ud["twin_rows"]
            twb = [tw[i] for i in rng.integers(0, len(tw), len(tw))]
            tws = twin_stats(twb, set(cat), d)
            conf = []
            for cell in ud["cells"]:
                first = [r for r in cell if int(r["slot"]) in (0, 1)]
                top = [r for r in cell if int(r["slot"]) in (2, 3, 4, 5)]
                fb = [first[i] for i in rng.integers(0, len(first), len(first))] if first else []
                tb = [top[i] for i in rng.integers(0, len(top), len(top))] if top else []
                dd = cell_decision(fb + tb, tws, set(cat), d)
                conf.append(dd["confirmed"])
            E = sum(conf) / len(conf) if conf else 0.0
            bs.append(beta)
            es.append(E)
        r = spearman(bs, es)
        if r == r:
            rhos.append(r)
    if not rhos:
        return {"n_valid": 0, "median": None, "ci90": None}
    return {"n_valid": len(rhos), "median": float(np.median(rhos)),
            "ci90": [float(np.percentile(rhos, 5)), float(np.percentile(rhos, 95))]}


def a2_analysis(events: list[dict[str, Any]]) -> dict[str, Any]:
    """events: [{'unit', 'r', 'L', 'K', 'survivors', 'realised': [labels], 'realised_pn': [labels],
    'base_counts', 'assoc_counts', 'prox_dist'}]."""
    out: dict[str, Any] = {"n_events": len(events), "events": []}
    hits, cs = 0, []
    diffs_a, diffs_p, diffs_a_def, diffs_p_def = [], [], [], []
    for ev in events:
        hit = ev["r"] is not None and ev["r"] == ev["L"]
        hits += hit
        c = 1.0 / (ev["K"] - 1) if ev["K"] > 1 else 1.0
        cs.append(c)
        surv = ev["survivors"]
        raws = {"base": {s: float(ev["base_counts"].get(s, 0)) for s in surv} if ev["base_counts"] else None,
                "assoc": ({s: (ev["assoc_counts"].get(s, 0) + 1) for s in surv}
                          if ev.get("assoc_counts") is not None else None),
                "prox": None}
        pd = ev.get("prox_dist") or {}
        dvals = [pd[s] for s in surv if pd.get(s) is not None]
        if dvals and np.median(dvals) > 0:
            med = float(np.median(dvals))
            raws["prox"] = {s: math.exp(-pd[s] / med) for s in surv if pd.get(s) is not None}
        sc, sc_pn, defined = {}, {}, {}
        for k, raw in raws.items():
            defined[k] = bool(raw) and sum(raw.values()) > 0
            q = mixture_q(raw, surv)
            sc[k] = log_score(q, ev["realised"])
            sc_pn[k] = log_score(q, ev.get("realised_pn") or [])
        out["events"].append({"unit": ev["unit"], "r": ev["r"], "L": ev["L"], "hit": hit, "chance": c,
                              "n_realised": len(ev["realised"]), "log_scores": sc, "defined": defined,
                              "log_scores_pn": sc_pn})
        if sc["base"] is not None and sc["assoc"] is not None:
            diffs_a.append(sc["base"] - sc["assoc"])
            if defined["base"] and defined["assoc"]:
                diffs_a_def.append(sc["base"] - sc["assoc"])
        if sc["base"] is not None and sc["prox"] is not None:
            diffs_p.append(sc["base"] - sc["prox"])
            if defined["base"] and defined["prox"]:
                diffs_p_def.append(sc["base"] - sc["prox"])
    out["hits"] = hits
    out["p_poisson_binomial"] = poisson_binomial_sf(hits, cs) if events else None
    out["base_minus_assoc"] = {"mean": float(np.mean(diffs_a)) if diffs_a else None, **wilcoxon_exact(diffs_a),
                               "exceeds_0.10_nats": bool(diffs_a and np.mean(diffs_a) > 0.10),
                               "defined_only_mean": float(np.mean(diffs_a_def)) if diffs_a_def else None}
    out["base_minus_prox"] = {"mean": float(np.mean(diffs_p)) if diffs_p else None, **wilcoxon_exact(diffs_p),
                              "exceeds_0.10_nats": bool(diffs_p and np.mean(diffs_p) > 0.10),
                              "defined_only_mean": float(np.mean(diffs_p_def)) if diffs_p_def else None}
    return out


def repertoire_check(task: str, default: str, cat: list[str]) -> dict[str, Any]:
    rows = labels(task)
    base = rows_of(rows, "BASE", "base")
    bcorr = Counter(r["label"] for r in base if r.get("passed") and r["label"] not in EXCLUDE)
    bvalid = Counter(r["label"] for r in base if r["label"] not in EXCLUDE)
    res = {"base_hill1": hill1_rarefied(list(bcorr.elements()), DEPTH, seed=BOOT_SEED)}
    outside = []
    for name, sel in (("PN_a1", rows_of(rows, "PN_a1.0")), ("PN_a2", rows_of(rows, "PN_a2.0")),
                      ("ESC", rows_of(rows, prefix="ESC_"))):
        corr = [r for r in sel if r.get("passed") and r["label"] not in EXCLUDE]
        res[f"{name}_hill1"] = hill1_rarefied([r["label"] for r in corr], DEPTH, seed=BOOT_SEED)
        for r in corr:
            if r["label"] in cat and r["label"] != default and bcorr.get(r["label"], 0) == 0 and \
                    bvalid.get(r["label"], 0) == 0:
                outside.append({"task": task, "arm": r["arm"], "sample_id": r["sample_id"], "label": r["label"]})
    res["outside_base_repertoire"] = outside
    res["n_outside"] = len(outside)
    return res


def frozen_screen() -> dict[str, Any]:
    s = read_json(EVAL3 / "screen.json")
    out = {}
    for t, v in s["tasks"].items():
        out[t] = {"E1": v["alpha_1"]["E_t"], "E2": v["alpha_2"]["E_t"], "movable": bool(v["movable"])}
    return out


def extra_arm_a() -> dict[str, Any]:
    scr = frozen_screen()
    out = {}
    for t in EXISTING:
        rows = labels(t)
        if not rows:
            continue
        d = EXISTING_DEFAULT[t]
        cat = catalogue(t)
        oc = unit_outcome(t, d, cat)
        it4 = ITER4_E.get(t, (0.0, 0.0))
        sv = scr.get(t, {})
        out[t] = {"default": d, "twin": oc["escape"]["twin"], "E1": oc["E1"], "E2": oc["E2"], "E": oc["E"],
                  "movable_banfree": oc["movable_obs"], "landing": oc["landing"],
                  "iter4_E1_E2": list(it4), "screen_E1": sv.get("E1"), "screen_E2": sv.get("E2"),
                  "screen_movable": sv.get("movable"),
                  "verdict_change": (None if sv.get("movable") is None else
                                     bool(oc["movable_obs"]) != bool(sv.get("movable"))),
                  "cells": oc["escape"]["cells"]}
    return out


def step1_betas() -> dict[str, Any]:
    """'Half + screen': Step 1's committed beta for the 15 existing tasks, if readable on disk and hash-verified."""
    loop = ROOT.parent
    found = {}
    for f in glob.glob(str(loop / "*" / "predictions" / "*.json")):
        fp = Path(f)
        if ROOT in fp.parents:
            continue
        try:
            j = read_json(fp)
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            continue
        txt = json.dumps(j)
        if '"beta' not in txt or "T03" not in txt:
            continue
        cl = fp.parents[1] / "commitments.log"
        h = sha256_file(fp)
        ok = cl.exists() and h in cl.read_text()
        found[str(fp.relative_to(loop))] = {"sha256_verified": ok}
    return found


def main_final() -> dict[str, Any]:
    """Every headline number of panel A from data/labels + predictions/ (run after the pushes)."""
    preds = {}
    for p in sorted(PRED.glob("unit_*.json")):
        j = read_json(p)
        preds[j["unit"]] = j
    unit_rows, unit_data, events = [], [], []
    summaries = {}
    for u, pr in preds.items():
        if pr.get("status") != "OK" or pr.get("default") is None:
            summaries[u] = {"status": pr.get("status")}
            continue
        d, cat = pr["default"], pr["catalogue"]
        oc = unit_outcome(u, d, cat)
        kr = knob_rows(u, d, cat)
        rep = repertoire_check(u, d, cat)
        riv = dict(pr.get("rivals") or {})
        riv["K"] = len(cat)
        riv["base_pass_rate"] = pr["base_chat"]["pass_rate"]
        unit_rows.append({"unit": u, "beta": pr["beta"], "E": oc["E"], "S": oc["S"], "rivals": riv,
                          "cluster": "T10" if u == "A6" else u})
        rows = labels(u)
        esc = rows_of(rows, prefix="ESC_", model="instruct")
        cells = []
        for s in ESC_SEEDS:
            for a in ALPHAS:
                cells.append([r for r in esc if int(r["direction_seed"]) == s and abs(float(r["alpha"]) - a) < 1e-9])
        unit_data.append({"unit": u, "default": d, "catalogue": cat, "base_rows": rows_of(rows, "BASE", "base"),
                          "twin_rows": rows_of(rows, "TWIN", "instruct"), "cells": cells})
        summaries[u] = {"prediction": {k: pr.get(k) for k in ("default", "beta", "beta_ci", "r", "predicted_class",
                                                              "predicted_landing")},
                        "outcome": {k: oc[k] for k in ("E", "E1", "E2", "S", "movable_obs", "landing")},
                        "escape_cells": oc["escape"]["cells"], "pn": oc["pn"], "knob_rows": kr, "repertoire": rep}
        if pr["beta"] is not None and pr["beta"] >= BETA_MOVABLE and oc["movable_obs"]:
            surv = [m for m in cat if m != d]
            realised = []
            for c in oc["escape"]["cells"]:
                if c["confirmed"]:
                    sel = [r for r in esc if int(r["direction_seed"]) == c["seed"] and
                           abs(float(r["alpha"]) - c["alpha"]) < 1e-9 and int(r["slot"]) in range(6)]
                    realised += [r["label"] for r in sel if r.get("passed") and r["label"] in surv]
            pn_real = [r["label"] for r in rows if r["arm"].startswith("PN_a") and r.get("passed") and
                       r["label"] in surv]
            bcc = pr["base_chat"]["comp_correct"]
            events.append({"unit": u, "r": pr["r"], "L": oc["landing"], "K": len(cat), "survivors": surv,
                           "realised": realised, "realised_pn": pn_real,
                           "base_counts": {s: bcc.get(s, 0) for s in surv},
                           "assoc_counts": (pr.get("rivals") or {}).get("assoc_counts"),
                           "prox_dist": (pr.get("rivals") or {}).get("prox_dist")})
    a1 = a1_analysis(unit_rows)
    a1["measurement_bootstrap"] = measurement_bootstrap(unit_data)
    a1["sensitivity_without_A6"] = a1_analysis([u for u in unit_rows if u["unit"] != "A6"]) if \
        any(u["unit"] == "A6" for u in unit_rows) else None
    a2 = a2_analysis(events)
    xa = extra_arm_a()
    write_json(RESULTS / "a1.json", a1)
    write_json(RESULTS / "a2.json", a2)
    write_json(RESULTS / "extra_arm_a.json", xa)
    write_json(RESULTS / "unit_summaries.json", summaries)
    rep_all = {u: s.get("repertoire") for u, s in summaries.items() if s.get("repertoire")}
    write_json(RESULTS / "repertoire_check.json", rep_all)
    write_json(RESULTS / "outside_base_repertoire.json",
               [o for v in rep_all.values() for o in v["outside_base_repertoire"]])
    write_json(RESULTS / "knob_rows.json", {u: s.get("knob_rows") for u, s in summaries.items() if s.get("knob_rows")})
    write_json(RESULTS / "step1_betas_search.json", step1_betas())
    return {"a1": a1, "a2": a2, "extra_arm_a": xa, "summaries": summaries}


if __name__ == "__main__":
    from cfg5 import setup_logging

    setup_logging("analysis_a1a2")
    r = main_final()
    print(json.dumps({"a1_rho": r["a1"].get("rho_beta_E"), "a1_p": r["a1"].get("perm_p_one_sided"),
                      "a2_hits": r["a2"].get("hits"), "n_events": r["a2"].get("n_events")}, indent=1))
