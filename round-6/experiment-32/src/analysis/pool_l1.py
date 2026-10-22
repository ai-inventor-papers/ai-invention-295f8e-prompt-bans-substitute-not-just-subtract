#!/usr/bin/env python3
"""Frozen L1 analysis (plan Stage 6), hash-committed before the first nudge sample of any unit.

Inputs: landing_events.json and units.json (schema iter6_landing_v1). Mechanical: the same code pools panel I + II
next round (pass several --events/--units files).

E   = events with is_event, content_free, set == CONFIRMATION and a default.
L1a = on tail-empty events, hits of r_u on the modal landing; exact Poisson-binomial tail with per-event chance
      1/(K_e - 1); PASS iff |Ea| >= 6, hits/|Ea| >= 2/3 and p < 0.05 (|Ea| < 6 -> DESCRIPTIVE).
L1b = on discordant events, exact one-sided sign test of r_u vs qlik_top1 (ties excluded and counted);
      PASS iff |Eb| >= 6 and p < 0.05.
Log scores on matched events, D_lik and D_tail with 10,000-resample percentile bootstraps (default_rng(20261021)),
event-level and unit-clustered; the pseudo-replication guard; sensitivities; the panel verdict.
NO_CLEAR_LANDING is a miss for every top-1 forecast; an undefined forecast is scored as uniform (defined-only beside).
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

SEED = 20261021
NONINF_MARGIN = -0.10
FORECASTS = ("base", "lik", "lik_raw", "tail", "assoc", "uniform")
FKEY = {"base": "q_base", "lik": "q_lik", "lik_raw": "q_lik_raw", "tail": "q_tail", "assoc": "assoc"}


# ------------------------------------------------------------------ exact tests
def poisson_binomial_tail(ps: list[float], k: int) -> float:
    """P(X >= k) for X = sum of independent Bernoulli(p_i), exact DP convolution."""
    dist = np.zeros(len(ps) + 1)
    dist[0] = 1.0
    for p in ps:
        dist[1:] = dist[1:] * (1 - p) + dist[:-1] * p
        dist[0] *= (1 - p)
    return float(dist[k:].sum()) if k <= len(ps) else 0.0


def sign_test_one_sided(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    return float(sum(math.comb(n, i) for i in range(b, n + 1)) / 2 ** n)


# ------------------------------------------------------------------ helpers
def S_of(ev: dict) -> list[str]:
    return [a for a in ev["catalogue"] if a != ev["default"]]


def forecast(ev: dict, f: str) -> dict[str, float] | None:
    S = S_of(ev)
    if f == "uniform":
        return {a: 1.0 / len(S) for a in S}
    q = ev.get(FKEY[f])
    if not q:
        return None
    tot = sum(q.get(a, 0.0) for a in S)
    if tot <= 0:
        return None
    return {a: q.get(a, 0.0) / tot for a in S}


def log_score(ev: dict, f: str, undefined_as_uniform: bool = True) -> float | None:
    q = forecast(ev, f)
    if q is None:
        if not undefined_as_uniform:
            return None
        q = forecast(ev, "uniform")
    n = sum(ev["counts"].get(a, 0) for a in S_of(ev))
    if n == 0:
        return None
    return sum(c * math.log(max(q[a], 1e-12)) for a, c in ev["counts"].items() if a in q) / n


def hit(ev: dict, pred: str | None) -> bool:
    return pred is not None and ev["modal_landing"] not in (None, "NO_CLEAR_LANDING") and pred == ev["modal_landing"]


def boot(vals: list[float], groups: list[str] | None = None, reps: int = 10000) -> dict[str, Any]:
    v = np.array(vals, float)
    if len(v) == 0:
        return {"n": 0, "mean": None}
    rng = np.random.default_rng(SEED)
    if groups is None:
        idx = rng.integers(0, len(v), size=(reps, len(v)))
        bs = v[idx].mean(1)
    else:
        ug = sorted(set(groups))
        gi = {g: np.where(np.array(groups) == g)[0] for g in ug}
        bs = np.empty(reps)
        for r in range(reps):
            pick = rng.integers(0, len(ug), size=len(ug))
            ii = np.concatenate([gi[ug[j]] for j in pick])
            bs[r] = v[ii].mean()
    return {"n": int(len(v)), "mean": float(v.mean()), "lb95_one_sided": float(np.quantile(bs, 0.05)),
            "ci95": [float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975))],
            "non_inferior": bool(np.quantile(bs, 0.05) > NONINF_MARGIN)}


# ------------------------------------------------------------------ core
def l1a(events: list[dict]) -> dict[str, Any]:
    Ea = [e for e in events if e["tail_empty"]]
    hits = sum(hit(e, e["r_u"]) for e in Ea)
    ps = [1.0 / (e["K"] - 1) for e in Ea]
    p = poisson_binomial_tail(ps, hits) if Ea else None
    res = {"n_events": len(Ea), "hits_r_u": hits, "rate": hits / len(Ea) if Ea else None, "p": p,
           "expected_chance_hits": float(sum(ps)), "hits_qlik_top1": sum(hit(e, e["qlik_top1"]) for e in Ea),
           "events": [e["event_id"] for e in Ea]}
    if len(Ea) < 6:
        res["status"] = "DESCRIPTIVE"
    else:
        res["status"] = "PASS" if (hits / len(Ea) >= 2 / 3 - 1e-12 and p < 0.05) else "FAIL"
    return res


def l1b(events: list[dict]) -> dict[str, Any]:
    Eb = [e for e in events if e["discordant"]]
    b = sum(1 for e in Eb if hit(e, e["r_u"]) and not hit(e, e["qlik_top1"]))
    c = sum(1 for e in Eb if hit(e, e["qlik_top1"]) and not hit(e, e["r_u"]))
    ties = len(Eb) - b - c
    p = sign_test_one_sided(b, c) if Eb else None
    res = {"n_events": len(Eb), "b_r_u_only": b, "c_qlik_only": c, "ties": ties, "p": p,
           "events": [e["event_id"] for e in Eb]}
    res["status"] = "DESCRIPTIVE" if len(Eb) < 6 else ("PASS" if p < 0.05 else "FAIL")
    return res


def tail_rival(events: list[dict]) -> dict[str, Any]:
    dfd = [e for e in events if e.get("t_u")]
    exp_all = sum((1.0 if hit(e, e["t_u"]) else 0.0) if e.get("t_u") else 1.0 / (e["K"] - 1) for e in events)
    return {"n_defined": len(dfd), "hits_defined": sum(hit(e, e["t_u"]) for e in dfd),
            "rate_defined": (sum(hit(e, e["t_u"]) for e in dfd) / len(dfd)) if dfd else None,
            "n_all": len(events), "expected_hits_all_undefined_at_chance": exp_all}


def log_scores(events: list[dict]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    ls = {f: [log_score(e, f) for e in events] for f in FORECASTS}
    ls_def = {f: [log_score(e, f, False) for e in events] for f in FORECASTS}
    out["mean_LS"] = {f: (float(np.mean([x for x in v if x is not None])) if any(x is not None for x in v) else None)
                      for f, v in ls.items()}
    groups = [e["unit_id"] for e in events]
    for rival in ("lik", "tail", "lik_raw", "assoc", "uniform"):
        diffs, g = [], []
        diffs_def = []
        for i, e in enumerate(events):
            if ls["base"][i] is not None and ls[rival][i] is not None:
                diffs.append(ls["base"][i] - ls[rival][i])
                g.append(groups[i])
            if ls_def["base"][i] is not None and ls_def[rival][i] is not None:
                diffs_def.append(ls_def["base"][i] - ls_def[rival][i])
        out[f"D_{rival}"] = {"event": boot(diffs), "unit_clustered": boot(diffs, g),
                             "defined_only": boot(diffs_def), "per_event": diffs}
    return out


def unit_level(events: list[dict], units: dict[str, dict]) -> dict[str, Any]:
    """Pseudo-replication guard: pool each unit's content-free events, re-derive the unit modal landing (15-point
    rule) and re-run L1a / L1b over units."""
    by = defaultdict(list)
    for e in events:
        by[e["unit_id"]].append(e)
    ues = []
    for u, es in by.items():
        cnt = Counter()
        for e in es:
            cnt.update({a: c for a, c in e["counts"].items() if a in S_of(e)})
        tot = sum(cnt.values())
        top = cnt.most_common(2)
        if tot == 0:
            continue
        lead = top[0][1] / tot - (top[1][1] / tot if len(top) > 1 else 0.0)
        modal = top[0][0] if lead >= 0.15 - 1e-12 else "NO_CLEAR_LANDING"
        e0 = es[0]
        ues.append({**{k: e0[k] for k in ("default", "K", "r_u", "qlik_top1", "t_u", "tail_empty", "discordant",
                                           "catalogue", "unit_id")},
                    "event_id": f"{u}|UNIT", "counts": dict(cnt), "modal_landing": modal})
    return {"n_units": len(ues), "L1a": l1a(ues), "L1b": l1b(ues),
            "units": [{"unit": x["unit_id"], "modal": x["modal_landing"], "r_u": x["r_u"],
                       "qlik_top1": x["qlik_top1"]} for x in ues]}


def analyse(events: list[dict], units: dict[str, dict]) -> dict[str, Any]:
    res = {"n_events": len(events), "L1a": l1a(events), "L1b": l1b(events), "tail_rival": tail_rival(events),
           "log_scores": {"E": log_scores(events), "Ea": log_scores([e for e in events if e["tail_empty"]]),
                          "Eb": log_scores([e for e in events if e["discordant"]])},
           "unit_level": unit_level(events, units)}
    return res


def verdict(r: dict[str, Any]) -> str:
    a, b = r["L1a"], r["L1b"]
    if a["status"] == "PASS" and b["status"] == "PASS":
        return "SUPPORTED-IN-PANEL"
    dl = r["log_scores"]["E"].get("D_lik", {}).get("event", {}).get("mean")
    dt = r["log_scores"]["E"].get("D_tail", {}).get("event", {}).get("mean")
    if ((dl is not None and dl <= 0) or (dt is not None and dt <= 0)) and a["n_events"] >= 6 and \
            a["p"] is not None and a["p"] >= 0.05:
        return "DISCONFIRMED-IN-PANEL"
    return "DESCRIPTIVE"


def select(events: list[dict], units: dict[str, dict], include_screen: bool = False) -> list[dict]:
    out = []
    for e in events:
        if not e.get("is_event") or not e.get("content_free"):
            continue
        if e.get("default") in (None, "NO_DEFAULT"):
            continue
        if e["set"] != "CONFIRMATION" and not include_screen:
            continue
        out.append(e)
    return out


def sensitivities(events: list[dict], units: dict[str, dict]) -> dict[str, Any]:
    out = {}
    out["drop_LOW_CORRECT"] = analyse([e for e in events if not units.get(e["unit_id"], {}).get("low_correct")],
                                      units)
    nf = {u: (v.get("q_lik_noise_floor") or 0.0) for u, v in units.items()}
    out["drop_qlik_gap_below_2x_noise"] = analyse(
        [e for e in events if e.get("qlik_top2_gap") is None or e["qlik_top2_gap"] >= 2 * nf.get(e["unit_id"], 0.0)],
        units)
    for alt in ("qlik_unscrubbed_top1", "qlik_raw_top1"):
        ev2 = []
        for e in events:
            e2 = dict(e)
            e2["qlik_top1"] = e.get(alt)
            e2["discordant"] = e2["qlik_top1"] is not None and e2["r_u"] != e2["qlik_top1"]
            if alt == "qlik_unscrubbed_top1" and e.get("q_lik_unscrubbed"):
                e2["q_lik"] = e["q_lik_unscrubbed"]
            if alt == "qlik_raw_top1":
                e2["q_lik"] = e.get("q_lik_raw")
            ev2.append(e2)
        out[alt] = analyse(ev2, units)
    out["drop_flagged_neighbours_II8_II12"] = analyse([e for e in events if e["unit_id"] not in ("II8", "II12")],
                                                      units)
    ev3 = []
    for e in events:
        e3 = dict(e)
        if e.get("other_dominant"):
            e3["modal_landing"] = "NO_CLEAR_LANDING"
        ev3.append(e3)
    out["other_dominant_as_no_clear_landing"] = analyse(ev3, units)
    return out


def run(events_all: list[dict], units_all: dict[str, dict]) -> dict[str, Any]:
    E = select(events_all, units_all)
    res = analyse(E, units_all)
    res["verdict"] = verdict(res)
    pri = [e for e in E if units_all.get(e["unit_id"], {}).get("priority")]
    res["priority_subset"] = analyse(pri, units_all)
    res["sensitivities"] = sensitivities(E, units_all)
    res["screen_included"] = analyse(select(events_all, units_all, include_screen=True), units_all)
    res["screen_only"] = analyse([e for e in select(events_all, units_all, include_screen=True)
                                  if e["set"] == "SCREEN"], units_all)
    res["event_ids"] = [e["event_id"] for e in E]
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", nargs="+", required=True)
    ap.add_argument("--units", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    events, units = [], {}
    for p in a.events:
        events += json.loads(Path(p).read_text())["events"]
    for p in a.units:
        for u in json.loads(Path(p).read_text())["units"]:
            units[u["unit_id"]] = u
    res = run(events, units)
    Path(a.out).write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps({k: res[k] for k in ("verdict", "L1a", "L1b")}, indent=1, default=float)[:3000])


if __name__ == "__main__":
    main()
