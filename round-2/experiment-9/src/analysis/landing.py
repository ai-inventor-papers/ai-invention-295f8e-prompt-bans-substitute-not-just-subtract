#!/usr/bin/env python3
"""S10 BEHAVIOUR (frozen and sha256-committed at S7, before any multi-ban sample).

Per sampled condition: attempted programs (extracted code with a known label); landing distribution over {each survivor,
banned (by algorithm), other}; avoidance = 1 - banned share; GATE = avoidance >= 0.5 and >= 20 attempted non-banned
programs; compliant share (passed and not banned); unknown and truncation rates. Wilson 95% CIs, per-template tables
and template-cluster bootstrap (2,000 reps). DISGUISE: among banned-mechanism programs, the share whose full response
matches no alias of its own mechanism, with the self-names used. LANDING TEST per banned set on the landed survivor
mass: S_edge = share(EDGE) - share(OPPOSITE); Spearman rho of survivor shares with each committed forecast; exact
survivor-permutation nulls (all S! assignments, one-sided in the predicted direction), pooled over sets with the exact
product null; log score of each committed mixed forecast against uniform, and top-1 hits; the same rank tests on the
likelihood landing (mean_w G_h2) against PV from half 1. References: single modal bans. T2 leave-one-survivor: will
versus can, FRLP gain and banned drop.
"""

from __future__ import annotations

import collections
import itertools
import math
import re
from typing import Any

import numpy as np
from loguru import logger

from common import (ALIASES, DATA_DIR, MECH_ALIAS_FAMILIES, MODES, RESULTS_DIR, ROOT, THRESHOLDS, read_json,
                    read_jsonl, wilson_ci, write_json)

FORECASTS = ("LADDER", "PRIME_AND_VETO", "PROXIMITY", "FRLP_BAN", "GENERIC", "CORPUS")
N_BOOT = 2000
UNRESOLVED = ("unknown", "no_code", "inconsistent")
SELF_NAME_RE = re.compile(r"\b(backtrack\w*|flood[\s_-]?fill\w*|wave[\s_-]?front|level[\s_-]?order|breadth[\s_-]?first|"
                          r"depth[\s_-]?first|best[\s_-]?first|greedy|heuristic|a\*|a[\s_-]?star|dijkstra|bfs|dfs|"
                          r"iddfs|ida\*|bidirectional|bellman[\s_-]?ford|spfa|floyd|dial|bucket|priority[\s_-]?queue|"
                          r"recursive|stack[\s_-]?based|queue[\s_-]?based|random[\s_-]?walk|wall[\s_-]?follow\w*|"
                          r"spiral|brute[\s_-]?force|exhaustive|depth[\s_-]?limited|iterative[\s_-]?deepening|"
                          r"label[\s_-]?correcting|relaxation|memoi[sz]\w*|dynamic[\s_-]?programming)\b", re.I)


# ------------------------------------------------------------------------------------------------ statistics
def spearman(x: list[float], y: list[float]) -> float | None:
    from scipy.stats import spearmanr

    if len(x) < 2 or len(set(x)) < 2 or len(set(y)) < 2:
        return None
    r = spearmanr(x, y).statistic
    return None if r is None or not np.isfinite(r) else float(r)


def perm_null(values: list[float], stat, observed: float) -> dict[str, Any]:
    """Exact survivor-permutation null: permute the realised survivor values over all S! assignments."""
    perms = list(itertools.permutations(values))
    dist = [stat(list(p)) for p in perms]
    dist = [d for d in dist if d is not None]
    if observed is None or not dist:
        return {"p": None, "n_perm": len(perms)}
    p = sum(1 for d in dist if d >= observed - 1e-12) / len(dist)
    return {"p": p, "n_perm": len(perms), "null_mean": float(np.mean(dist))}


def product_null(per_set: list[tuple[list[float], Any, float]]) -> dict[str, Any]:
    """Pooled exact product null: sum of per-set statistics over the product of the per-set permutation sets."""
    dists = []
    obs = 0.0
    for vals, stat, o in per_set:
        d = [stat(list(p)) for p in itertools.permutations(vals)]
        d = [x for x in d if x is not None]
        if o is None or not d:
            continue
        dists.append(d)
        obs += o
    if not dists:
        return {"p": None}
    tot = np.zeros(1)
    for d in dists:
        tot = (tot[:, None] + np.array(d)[None, :]).ravel()
    return {"p": float((tot >= obs - 1e-12).mean()), "n": int(tot.size), "observed_sum": obs}


def logscore(probs: dict[str, float], labels: list[str]) -> float:
    return float(np.mean([math.log(max(probs.get(y, probs.get("other", 1e-9)), 1e-12)) for y in labels])) if labels else float("nan")


# ------------------------------------------------------------------------------------------------ landing per condition
def landing_category(label: str, banned: list[str], catalogue: list[str]) -> str:
    if label in banned:
        return "banned:" + label
    if label in catalogue:
        return label
    return "other"


def summarise(rows: list[dict[str, Any]], banned: list[str], catalogue: list[str], survivors: list[str],
              rng: np.random.Generator) -> dict[str, Any]:
    n_all = len(rows)
    att = [r for r in rows if r.get("label") not in UNRESOLVED and r.get("code")]
    cats = [landing_category(r["label"], banned, catalogue) for r in att]
    cnt = collections.Counter(cats)
    n = len(att)
    nb = sum(v for k, v in cnt.items() if k.startswith("banned:"))
    nonb = n - nb
    avoid = 1 - nb / n if n else None
    comp = sum(1 for r, c in zip(att, cats) if r.get("passed") and not c.startswith("banned:"))
    out = {"n_samples": n_all, "attempted": n, "unknown_rate": (n_all - n) / max(n_all, 1),
           "truncation_rate": sum(1 for r in rows if r.get("truncated")) / max(n_all, 1),
           "counts": dict(cnt), "fine_labels": dict(collections.Counter(r["label"] for r in rows)),
           "shares": {k: v / n for k, v in cnt.items()} if n else {},
           "share_ci": {k: wilson_ci(v, n) for k, v in cnt.items()},
           "avoidance": avoid, "avoidance_ci": wilson_ci(nonb, n) if n else None,
           "n_nonbanned": nonb, "compliant_share": comp / max(n_all, 1), "compliant_ci": wilson_ci(comp, n_all),
           "gate": bool(avoid is not None and avoid >= THRESHOLDS["gate_avoidance"]
                        and nonb >= THRESHOLDS["gate_min_nonbanned"]),
           "pass_rate_attempted": sum(1 for r in att if r.get("passed")) / max(n, 1)}
    surv_counts = {s: cnt.get(s, 0) for s in survivors}
    tot_s = sum(surv_counts.values())
    out["survivor_counts"] = surv_counts
    out["survivor_shares"] = {s: v / tot_s for s, v in surv_counts.items()} if tot_s else {s: None for s in survivors}
    # per-template table + template-cluster bootstrap
    by_t = collections.defaultdict(list)
    for r in rows:
        by_t[r["template"]].append(r)
    out["per_template"] = {}
    for t, rs in sorted(by_t.items()):
        a = [r for r in rs if r.get("label") not in UNRESOLVED and r.get("code")]
        c = collections.Counter(landing_category(r["label"], banned, catalogue) for r in a)
        out["per_template"][t] = {"n": len(rs), "attempted": len(a), "counts": dict(c),
                                  "avoidance": 1 - sum(v for k, v in c.items() if k.startswith("banned:")) / len(a)
                                  if a else None}
    tkeys = sorted(by_t)
    boots = collections.defaultdict(list)
    for _ in range(N_BOOT):
        pick = rng.choice(len(tkeys), size=len(tkeys), replace=True)
        rs = [r for i in pick for r in by_t[tkeys[i]]]
        a = [r for r in rs if r.get("label") not in UNRESOLVED and r.get("code")]
        if not a:
            continue
        c = collections.Counter(landing_category(r["label"], banned, catalogue) for r in a)
        nbb = sum(v for k, v in c.items() if k.startswith("banned:"))
        boots["avoidance"].append(1 - nbb / len(a))
        ts = sum(c.get(s, 0) for s in survivors)
        for s in survivors:
            boots[f"surv_share:{s}"].append(c.get(s, 0) / ts if ts else np.nan)
        for k in set(cats) | {"other"}:
            boots[f"share:{k}"].append(c.get(k, 0) / len(a))
    out["cluster_bootstrap_ci"] = {k: [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))]
                                   for k, v in boots.items() if len(v) and not np.all(np.isnan(v))}
    return out


def names_own_mechanism(text: str, label: str) -> bool:
    fams = MECH_ALIAS_FAMILIES.get(label, [])
    low = text.lower()
    for f in fams:
        for a in ALIASES[f]:
            if a.endswith("*"):
                if re.search(r"(?<![a-z0-9_])" + re.escape(a), low):
                    return True
            elif a in low or a.replace(" ", "_") in low or a.replace("-", "_") in low:
                return True
    return False


def self_names(row: dict[str, Any]) -> list[str]:
    names = re.findall(r"def\s+([A-Za-z_][A-Za-z0-9_]*)", row.get("code") or "")
    words = [m.group(0).lower() for m in SELF_NAME_RE.finditer(row.get("text") or "")]
    return sorted(set(n for n in names if n != "solve")) + sorted(set(words))


def disguise(rows: list[dict[str, Any]], banned: list[str]) -> dict[str, Any]:
    br = [r for r in rows if r.get("label") in banned]
    dis = [r for r in br if not names_own_mechanism(r.get("text") or "", r["label"])]
    names = collections.Counter(n for r in dis for n in self_names(r))
    return {"n_banned_mechanism": len(br), "n_disguised": len(dis),
            "disguise_rate": len(dis) / len(br) if br else None,
            "by_mechanism": {b: {"n": sum(1 for r in br if r["label"] == b),
                                 "disguised": sum(1 for r in dis if r["label"] == b)} for b in banned},
            "self_names_top": names.most_common(15)}


# ------------------------------------------------------------------------------------------------ landing tests
def landing_tests(fc: dict[str, Any], summ: dict[str, Any], rows: list[dict[str, Any]], catalogue: list[str],
                  likelihood: dict[str, Any] | None) -> dict[str, Any]:
    surv = fc["survivors"]
    shares = [summ["survivor_shares"].get(s) for s in surv]
    out: dict[str, Any] = {"survivors": surv, "survivor_shares": dict(zip(surv, shares)),
                           "n_landed_survivor": sum(summ["survivor_counts"].values())}
    if any(s is None for s in shares) or len(surv) < 2:
        out["note"] = "no landed survivor mass (or < 2 survivors): rank tests undefined"
        return out
    edge, opp = fc.get("EDGE") or [], fc.get("OPPOSITE") or []

    def s_edge(vals: list[float]) -> float:
        m = dict(zip(surv, vals))
        return sum(m[e] for e in edge) - sum(m[o] for o in opp)

    obs = s_edge(shares)
    out["S_edge"] = {"observed": obs, **perm_null(shares, s_edge, obs), "EDGE": edge, "OPPOSITE": opp}
    out["rho"] = {}
    for f in FORECASTS:
        if f not in fc["forecasts_raw"]:
            continue
        pred = [fc["forecasts_raw"][f][s] for s in surv]
        st = (lambda v, pred=pred: spearman(pred, v))
        r = st(shares)
        out["rho"][f] = {"observed": r, **perm_null(shares, st, r)}
    # log scores of committed mixed forecasts vs uniform (non-banned attempted programs)
    banned = fc["banned"]
    labs = [landing_category(r["label"], banned, catalogue) for r in rows
            if r.get("label") not in UNRESOLVED and r.get("code")]
    labs = [y for y in labs if not y.startswith("banned:")]
    S = len(surv)
    uni = {s: (1 - THRESHOLDS["other_floor"]) / S for s in surv}
    uni["other"] = THRESHOLDS["other_floor"]
    out["log_score"] = {"n": len(labs), "uniform": logscore(uni, labs)}
    modal = collections.Counter(y for y in labs if y in surv).most_common(1)
    for f in FORECASTS:
        if f not in fc["forecasts_mixed"]:
            continue
        ls = logscore(fc["forecasts_mixed"][f], labs)
        out["log_score"][f] = {"mean": ls, "minus_uniform": ls - out["log_score"]["uniform"],
                               "top1": fc["top1"][f], "top1_hit": bool(modal and fc["top1"][f] == modal[0][0])}
    out["realised_top1"] = modal[0][0] if modal else None
    if likelihood is not None:
        g = likelihood.get("G_h2") or {}
        pv = likelihood.get("PV") or {}
        if all(g.get(s) is not None for s in surv) and all(pv.get(s) is not None for s in surv):
            gv = [g[s] for s in surv]
            st = (lambda v: spearman([pv[s] for s in surv], v))
            r = st(gv)
            out["likelihood_landing"] = {"G_h2": g, "PV_h1": pv, "rho_PV": {"observed": r, **perm_null(gv, st, r)}}
    return out


# ------------------------------------------------------------------------------------------------ dry run (T7)
def dry_run() -> dict[str, Any]:
    rng = np.random.default_rng(7)
    surv = ["a", "b", "c", "d", "e"]
    edge, opp = ["a", "b"], ["d", "e"]

    def s_edge(v):
        m = dict(zip(surv, v))
        return m["a"] + m["b"] - m["d"] - m["e"]

    planted = [0.4, 0.3, 0.15, 0.1, 0.05]
    r = perm_null(planted, s_edge, s_edge(planted))
    ps = []
    for _ in range(200):
        c = rng.multinomial(60, [0.2] * 5)
        v = list(c / c.sum())
        ps.append(perm_null(v, s_edge, s_edge(v))["p"])
    ls = logscore({"a": 0.5, "b": 0.5, "other": 0.0}, ["a", "a", "b"])
    pooled = product_null([(planted, s_edge, s_edge(planted))] * 3)
    return {"planted_edge_p": r["p"], "n_perm": r["n_perm"], "uniform_p_mean": float(np.mean(ps)),
            "uniform_p_le_0.05": float(np.mean(np.array(ps) <= 0.05)), "logscore_check": ls,
            "logscore_expected": math.log(0.5), "pooled_planted_p": pooled["p"], "pooled_n": pooled["n"]}


# ------------------------------------------------------------------------------------------------ main
def run_landing() -> None:
    rng = np.random.default_rng(20261020)
    keep = read_json(RESULTS_DIR / "catalogue_keep.json")
    cat_t1 = keep.get("analysis_catalogue_final", keep["analysis_catalogue"])["t1"]
    cat_t2 = MODES["t2"]
    out: dict[str, Any] = {"dry_run": dry_run(), "catalogue_t1": cat_t1, "conditions": {}, "tests": {}}
    s1 = read_jsonl(DATA_DIR / "labelled_session1.jsonl")
    s2 = read_jsonl(DATA_DIR / "labelled_session2.jsonl") if (DATA_DIR / "labelled_session2.jsonl").exists() else []
    # references and baselines
    for task, cond, banned, cat in (("t1", "baseline", [], cat_t1), ("t2", "baseline", [], cat_t2),
                                    ("t1", "single:bfs", ["bfs"], cat_t1), ("t2", "single:dijkstra", ["dijkstra"], cat_t2)):
        rows = [r for r in s1 if r["task"] == task and r["condition"] == cond]
        surv = [a for a in cat if a not in banned]
        out["conditions"][f"{task}|{cond}"] = {"banned": banned, **summarise(rows, banned, cat, surv, rng),
                                               "disguise": disguise(rows, banned)}
    # multi-bans
    pooled_inputs: dict[str, list] = collections.defaultdict(list)
    for fp in sorted((ROOT / "predictions").glob("forecasts_*.json")):
        fc = read_json(fp)
        s = fc["set"]
        rows = [r for r in s2 if r["condition"] == f"multi:{s}"]
        summ = summarise(rows, fc["banned"], cat_t1, fc["survivors"], rng)
        out["conditions"][f"t1|multi:{s}"] = {"banned": fc["banned"], "survivors": fc["survivors"], **summ,
                                              "disguise": disguise(rows, fc["banned"]),
                                              "frlp_implied_avoidance": fc.get("frlp_implied_avoidance")}
        lt = landing_tests(fc, summ, rows, cat_t1, fc.get("derived"))
        lt["gate"] = summ["gate"]
        lt["gate_note"] = None if summ["gate"] else "gate failed (avoidance < 0.5 or < 20 non-banned): flagged"
        out["tests"][s] = lt
        if "S_edge" in lt:
            sh = [lt["survivor_shares"][x] for x in fc["survivors"]]
            surv = fc["survivors"]

            def s_edge(v, surv=surv, e=lt["S_edge"]["EDGE"], o=lt["S_edge"]["OPPOSITE"]):
                m = dict(zip(surv, v))
                return sum(m[x] for x in e) - sum(m[x] for x in o)

            pooled_inputs["S_edge"].append((sh, s_edge, lt["S_edge"]["observed"]))
            for f in FORECASTS:
                if f not in fc["forecasts_raw"]:
                    continue
                pred = [fc["forecasts_raw"][f][x] for x in surv]
                pooled_inputs[f"rho:{f}"].append((sh, (lambda v, pred=pred: spearman(pred, v)),
                                                  lt["rho"][f]["observed"]))
    out["pooled"] = {k: product_null(v) for k, v in pooled_inputs.items()}
    out["pooled"]["n_sets"] = {k: len(v) for k, v in pooled_inputs.items()}
    # references contrasted with TOP
    if "TOP" in out["tests"]:
        out["reference_contrast"] = {
            "t1_single_bfs": out["conditions"]["t1|single:bfs"]["counts"],
            "t2_single_dijkstra": out["conditions"]["t2|single:dijkstra"]["counts"],
            "t1_TOP": out["conditions"].get("t1|multi:TOP", {}).get("counts")}
    write_json(RESULTS_DIR / "landing.json", out)
    run_los(s1, rng)
    logger.info(f"landing written: {list(out['tests'].keys())}")


def run_los(s1: list[dict[str, Any]], rng: np.random.Generator) -> None:
    keep = read_json(RESULTS_DIR / "catalogue_keep.json")["tasks"]["t2"]
    cells = [r for r in read_jsonl(RESULTS_DIR / "frlp_cells.jsonl") if r["task"] == "t2" and "variant" not in r]
    idx = {(r["condition"], r["template"], r.get("twin"), r["algorithm"], r["half"]): r for r in cells}
    out = {}
    for s in MODES["t2"]:
        cond = f"los:{s}"
        banned = [a for a in MODES["t2"] if a != s]
        rows = [r for r in s1 if r["task"] == "t2" and r["condition"] == cond]
        summ = summarise(rows, banned, MODES["t2"], [s], rng)
        att = [r for r in rows if r.get("label") not in UNRESOLVED and r.get("code")]
        s_rows = [r for r in att if r["label"] == s]
        gains, drops = {}, []
        for w in ("W1", "W2", "W3", "W4", "W5"):
            g = []
            for h in ("h1", "h2"):
                b, n = idx.get((cond, w, "ban", s, h)), idx.get((cond, w, "neutral", s, h))
                if b is not None and n is not None:
                    g.append(b["L"] - n["L"])
            gains[w] = float(np.mean(g)) if g else None
            for a in banned:
                b, n = idx.get((cond, w, "ban", a, "h1")), idx.get((cond, w, "neutral", a, "h1"))
                if b is not None and n is not None:
                    drops.append({"algorithm": a, "template": w, "drop": b["L"] - n["L"]})
        out[s] = {"will_attempted_share": len(s_rows) / max(len(att), 1),
                  "will_ci": wilson_ci(len(s_rows), len(att)) if att else None,
                  "banned_share_by_mechanism": {a: sum(1 for r in att if r["label"] == a) / max(len(att), 1)
                                                for a in banned},
                  "other_share": sum(1 for r in att if r["label"] not in MODES["t2"]) / max(len(att), 1),
                  "compliant_share": summ["compliant_share"], "pass_rate_s_programs":
                      sum(1 for r in s_rows if r.get("passed")) / max(len(s_rows), 1) if s_rows else None,
                  "can_labelled_as_requested": keep[s]["share"], "can_pass_rate":
                      keep[s]["passed_as_requested"] / max(keep[s]["n_forced"], 1),
                  "frlp_available": keep[s]["frlp_available"], "frlp_gain_by_template": gains,
                  "frlp_gain_mean": float(np.mean([v for v in gains.values() if v is not None]))
                  if any(v is not None for v in gains.values()) else None,
                  "banned_drop": drops, "disguise": disguise(rows, banned), "summary": summ}
    write_json(RESULTS_DIR / "los.json", out)
