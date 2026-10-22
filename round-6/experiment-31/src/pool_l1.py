#!/usr/bin/env python3
"""pool_l1.py -- FROZEN pooled test of Claim L (iteration 6, protocol v6). Standard library only.

Inputs: one or more (landing_events.json, units.json) pairs in schema iter6_landing_v1 (panel I now; panels I + II
next round, concatenated). Confirmation set = rows with unit_kind == 'new' (SCREEN rows are never pooled).

Event = a (unit, nudge type in {ESC, PN, GTN}) row with exists == True (>= 5 correct off-default CATALOGUE programs in
the cells whose pass rate >= 0.8 x the HF twin's). A forecast f HITS an event iff clear_landing and modal_landing == f.
  L1a  on tail_empty events: hit = clear landing AND modal == r_u; p_e = 1/(K_u - 1); exact Poisson-binomial by DP,
       p = P(X >= x). PASS iff n >= 6, x/n >= 2/3 and p < 0.05; n < 6 -> DESCRIPTIVE.
  L1b  on discordant events (r_u != q_lik top-1): b = #(r_u hits, q_lik top-1 misses), c = the reverse;
       one-sided p = sum_{i >= b} C(b+c, i) / 2^(b+c) (p = 1 if b + c = 0). PASS iff n_discordant >= 6 and p < 0.05.
  LS   on matched events: LS_f(e) = mean over the event's correct off-default catalogue programs of log q_f(label),
       each forecast renormalised over the non-default catalogue modes ('other' removed, its count reported); an
       undefined forecast scores as uniform (defined-only result beside). D = LS_base - LS_rival for rival in
       {q_lik, q_lik_raw, q_tail}; 10,000 event-bootstrap replicates (seed 0); NON-INFERIOR iff the one-sided 95%
       lower bound > -0.10.
  t_u  top-1 hit rate where t_u is defined.
  UNIT-CLUSTERED: each unit's ESC + PN + GTN counts pooled into one landing (same existence and 15-point lead rules);
       L1a / L1b rerun on unit landings; cluster (unit) bootstrap for D. If only the per-event version passes the
       verdict reads 'per event, not per unit'.
Usage: python pool_l1.py --events landing_events.json [more ...] --units units.json [more ...] --out out.json
"""

from __future__ import annotations

import argparse
import json
import math
import random
from typing import Any

SCHEMA = "iter6_landing_v1"
MIN_EVENT = 5
LEAD = 0.15
NI_MARGIN = -0.10
N_BOOT = 10000


def poisson_binomial_sf(ps: list[float], x: int) -> float:
    """P(X >= x) for X = sum of independent Bernoulli(p_i), exact by dynamic programming."""
    dist = [1.0]
    for p in ps:
        new = [0.0] * (len(dist) + 1)
        for k, v in enumerate(dist):
            new[k] += v * (1 - p)
            new[k + 1] += v * p
        dist = new
    return float(min(1.0, sum(dist[x:])))


def sign_test_p(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    return float(min(1.0, sum(math.comb(n, i) for i in range(b, n + 1)) / 2 ** n))


def landing(counts: dict[str, int]) -> tuple[str | None, float, bool, int]:
    """(modal mode, lead in share points, clear, total) over correct off-default catalogue programs."""
    tot = sum(counts.values())
    if tot == 0:
        return None, 0.0, False, 0
    srt = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    top, n1 = srt[0]
    n2 = srt[1][1] if len(srt) > 1 else 0
    lead = (n1 - n2) / tot
    return top, lead, (tot >= MIN_EVENT and lead >= LEAD), tot


def renorm(vec: dict[str, float] | None, modes: list[str]) -> dict[str, float] | None:
    if not vec:
        return None
    v = {m: float(vec.get(m, 0.0) or 0.0) for m in modes}
    z = sum(v.values())
    if z <= 0:
        return None
    return {m: x / z for m, x in v.items()}


def log_score(vec: dict[str, float] | None, counts: dict[str, int], modes: list[str]) -> tuple[float, bool]:
    q = renorm(vec, modes)
    defined = q is not None
    if q is None:
        q = {m: 1.0 / len(modes) for m in modes}
    tot = sum(counts.get(m, 0) for m in modes)
    if tot == 0:
        return float("nan"), defined
    s = sum(counts.get(m, 0) * math.log(max(q[m], 1e-12)) for m in modes)
    return s / tot, defined


def hit(ev: dict[str, Any], f: str | None) -> bool:
    return bool(f is not None and ev["clear_landing"] and ev["modal_landing"] == f)


def l1a(events: list[dict[str, Any]]) -> dict[str, Any]:
    E = [e for e in events if e["tail_empty"]]
    ps = [1.0 / max(e["K"] - 1, 1) for e in E]
    x = sum(hit(e, e["r_u"]) for e in E)
    n = len(E)
    p = poisson_binomial_sf(ps, x) if n else 1.0
    verdict = "DESCRIPTIVE" if n < 6 else ("PASS" if (x / n >= 2 / 3 and p < 0.05) else "FAIL")
    return {"n": n, "hits": x, "hit_rate": x / n if n else None, "chance_mean": sum(ps) / n if n else None,
            "p_poisson_binomial": p, "verdict": verdict,
            "events": [{"unit": e["unit"], "nudge_type": e["nudge_type"], "r_u": e["r_u"],
                        "modal": e["modal_landing"], "clear": e["clear_landing"], "hit": hit(e, e["r_u"]),
                        "p_e": 1.0 / max(e["K"] - 1, 1)} for e in E]}


def l1b(events: list[dict[str, Any]]) -> dict[str, Any]:
    E = [e for e in events if e["discordant"]]
    b = sum(1 for e in E if hit(e, e["r_u"]) and not hit(e, e["q_lik_top1"]))
    c = sum(1 for e in E if hit(e, e["q_lik_top1"]) and not hit(e, e["r_u"]))
    p = sign_test_p(b, c)
    verdict = "DESCRIPTIVE" if len(E) < 6 else ("PASS" if p < 0.05 else "FAIL")
    return {"n_discordant": len(E), "b_base_only": b, "c_qlik_only": c, "p_sign": p, "verdict": verdict,
            "events": [{"unit": e["unit"], "nudge_type": e["nudge_type"], "r_u": e["r_u"],
                        "q_lik_top1": e["q_lik_top1"], "modal": e["modal_landing"], "clear": e["clear_landing"]}
                       for e in E]}


def scores(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for e in events:
        modes = [m for m in e["catalogue"] if m != e["default"]]
        cnt = {m: int(e["correct_off_default_counts"].get(m, 0)) for m in modes}
        row = {"unit": e["unit"], "nudge_type": e["nudge_type"], "n_other_correct": e.get("n_other_correct", 0)}
        for f in ("q_base", "q_lik", "q_lik_raw", "q_tail"):
            s, d = log_score(e.get(f), cnt, modes)
            row[f"LS_{f}"] = s
            row[f"defined_{f}"] = d
        out.append(row)
    return out


def boot_lower(diffs: list[float], clusters: list[str] | None, seed: int = 0) -> tuple[float, float]:
    """(mean, one-sided 95% lower bound) of the mean difference; event or cluster bootstrap."""
    if not diffs:
        return float("nan"), float("nan")
    rng = random.Random(seed)
    mean = sum(diffs) / len(diffs)
    reps = []
    if clusters is None:
        n = len(diffs)
        for _ in range(N_BOOT):
            s = [diffs[rng.randrange(n)] for _ in range(n)]
            reps.append(sum(s) / n)
    else:
        groups: dict[str, list[float]] = {}
        for d, c in zip(diffs, clusters):
            groups.setdefault(c, []).append(d)
        keys = sorted(groups)
        for _ in range(N_BOOT):
            s: list[float] = []
            for _k in keys:
                s.extend(groups[keys[rng.randrange(len(keys))]])
            reps.append(sum(s) / len(s))
    reps.sort()
    return mean, reps[int(0.05 * N_BOOT)]


def ls_tests(rows: list[dict[str, Any]], clustered: bool) -> dict[str, Any]:
    out = {}
    for rival in ("q_lik", "q_lik_raw", "q_tail"):
        res = {}
        for subset in ("all", "defined_only"):
            R = [r for r in rows if not math.isnan(r["LS_q_base"]) and not math.isnan(r[f"LS_{rival}"]) and
                 (subset == "all" or (r["defined_q_base"] and r[f"defined_{rival}"]))]
            d = [r["LS_q_base"] - r[f"LS_{rival}"] for r in R]
            mean, lo = boot_lower(d, [r["unit"] for r in R] if clustered else None)
            res[subset] = {"n": len(d), "mean_D": mean, "lower95": lo,
                           "non_inferior": bool(d and lo > NI_MARGIN)}
        out[rival] = res
    return out


def unit_landings(events_all: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by: dict[str, list[dict[str, Any]]] = {}
    for e in events_all:
        by.setdefault(e["unit"], []).append(e)
    out = []
    for u, es in sorted(by.items()):
        e0 = es[0]
        cnt: dict[str, int] = {}
        for e in es:
            for m, v in e["correct_off_default_counts"].items():
                cnt[m] = cnt.get(m, 0) + int(v)
        modal, lead, clear, tot = landing(cnt)
        out.append({**{k: e0[k] for k in ("unit", "unit_kind", "default", "K", "catalogue", "r_u", "q_lik_top1",
                                          "t_u", "tail_empty", "discordant", "q_base", "q_lik", "q_lik_raw",
                                          "q_tail")},
                    "nudge_type": "UNIT", "correct_off_default_counts": cnt, "modal_landing": modal, "margin": lead,
                    "clear_landing": clear, "exists": tot >= MIN_EVENT,
                    "n_other_correct": sum(int(e.get("n_other_correct", 0)) for e in es)})
    return out


def run(event_files: list[str], unit_files: list[str]) -> dict[str, Any]:
    evs, units = [], []
    for f in event_files:
        d = json.load(open(f))
        assert d.get("schema") == SCHEMA, f"{f}: schema {d.get('schema')} != {SCHEMA}"
        evs += d["events"]
    for f in unit_files:
        d = json.load(open(f))
        assert d.get("schema") == SCHEMA, f"{f}: schema {d.get('schema')} != {SCHEMA}"
        units += d["units"]
    new_all = [e for e in evs if e["unit_kind"] == "new"]
    E = [e for e in new_all if e["exists"]]
    sc = scores(E)
    tu = [e for e in E if e.get("t_u")]
    UL = [e for e in unit_landings(new_all) if e["exists"]]
    usc = scores(UL)
    res = {"schema": SCHEMA, "n_units": len({u["unit"] for u in units if u.get("unit_kind") == "new"}),
           "n_events": len(E), "per_event": {"L1a": l1a(E), "L1b": l1b(E), "log_scores": ls_tests(sc, False),
                                             "t_u_top1": {"n": len(tu), "hits": sum(hit(e, e["t_u"]) for e in tu)},
                                             "r_u_top1_all_events": {"n": len(E),
                                                                     "hits": sum(hit(e, e["r_u"]) for e in E)},
                                             "event_scores": sc},
           "unit_clustered": {"n_unit_landings": len(UL), "L1a": l1a(UL), "L1b": l1b(UL),
                              "log_scores_cluster_bootstrap": ls_tests(sc, True),
                              "log_scores_unit_landings": ls_tests(usc, False)}}
    pe = res["per_event"]["L1a"]["verdict"] == "PASS" or res["per_event"]["L1b"]["verdict"] == "PASS"
    pu = res["unit_clustered"]["L1a"]["verdict"] == "PASS" or res["unit_clustered"]["L1b"]["verdict"] == "PASS"
    res["note"] = "per event, not per unit" if (pe and not pu) else ("per event and per unit" if pe and pu else
                                                                    "no inferential pass")
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", nargs="+", required=True)
    ap.add_argument("--units", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    res = run(a.events, a.units)
    with open(a.out, "w") as fh:
        json.dump(res, fh, indent=1)
    print(json.dumps({k: res[k] for k in ("n_units", "n_events", "note")}))


if __name__ == "__main__":
    main()
