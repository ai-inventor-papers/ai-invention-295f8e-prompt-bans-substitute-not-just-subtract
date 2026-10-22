#!/usr/bin/env python3
"""Independent re-derivation of the L1 headline numbers (Python standard library only; no numpy/scipy and no import of
the pipeline's modules). Raw inputs only:
  - labels: inputs/exp28/data/labels.jsonl (exp28 rows), data/labels.jsonl (iteration-6 rows),
    data/labels_pt_revised.jsonl (revision-round pt labels);
  - catalogues: the 'catalogue' lists of predictions/forecasts_G6.json (nothing else is read from it);
  - q_lik: the per-pass teacher-forcing records data/qlik_tf.jsonl (set 'own_bf16'), NOT the aggregated scores;
  - iteration-5 landings: inputs/exp28/results/e_a2.json (the 7 exp28 events).
Recomputes D_u (N 300), r_u, t_u, TAIL-EMPTY, q_lik top-1, the v6 events (pooled and fresh-only), hits of all three
forecasts, exact Poisson-binomial p, the L1b and tail sign tests, the primary and the equal-'other' log-score means,
and the rescored iteration-5 tally; compares every value with results/l1_contest.json and results/old_tally.json;
runs placebos (random r_u, random q_lik top-1, random forecast in the log-score contest), which must fail.
Writes results/rederive_l1.json."""

from __future__ import annotations

import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUSH = ("R6", "T04", "T05", "T10", "T03", "T11", "T1", "T2")
OTHER = 0.02


def jl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def correct(r: dict) -> bool:
    return bool(r.get("passed")) and r.get("label") not in ("invalid", "disputed")


def valid(r: dict) -> bool:
    return bool(r.get("valid")) and r.get("label") not in ("invalid", "disputed")


def is_t10(r: dict) -> bool:
    return abs(float(r.get("temperature") or 1.0) - 1.0) < 1e-9


def load() -> dict:
    labs = {r["row_id"]: r for r in jl(ROOT / "inputs/exp28/data/labels.jsonl")}
    labs.update({r["row_id"]: r for r in jl(ROOT / "data/labels.jsonl")})
    for r in jl(ROOT / "data/labels_pt_revised.jsonl"):
        if r["row_id"] in labs:
            labs[r["row_id"]] = dict(labs[r["row_id"]], **r)
    return labs


def default(twin: list[dict], cat: list[str]):
    c = Counter(r["label"] for r in twin if correct(r))
    n = sum(c.values())
    if not c:
        return None
    top = max(c.values())
    tops = sorted(k for k, v in c.items() if v == top)
    return tops[0] if (tops[0] in cat and top / n >= 0.6 and n >= 10 and len(tops) == 1) else None


def argmax_rule(nd: list[str], keys: list[Counter]):
    rk = sorted(nd, key=lambda m: tuple(-k.get(m, 0) for k in keys) + (m,))
    return rk[0] if rk and keys[0].get(rk[0], 0) > 0 else None


def pb_sf(k: int, ps: list[float]) -> float:
    dist = [1.0] + [0.0] * len(ps)
    for p in ps:
        new = [0.0] * (len(ps) + 1)
        for i, v in enumerate(dist):
            if v:
                new[i] += v * (1 - p)
                new[i + 1] += v * p
        dist = new
    return sum(dist[k:])


def binom_sf(k: int, n: int) -> float | None:
    return None if n == 0 else sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n


def addone(counts: Counter, nd: list[str]) -> dict:
    tot = sum(counts.get(m, 0) for m in nd) + counts.get("other", 0) + len(nd) + 1
    q = {m: (counts.get(m, 0) + 1) / tot for m in nd}
    q["other"] = (counts.get("other", 0) + 1) / tot
    return q


def equal_other(q: dict, nd: list[str]) -> dict:
    tot = sum(q[m] for m in nd)
    out = {m: (1 - OTHER) * q[m] / tot for m in nd}
    out["other"] = OTHER
    return out


def mean_log(q: dict, ys: list[str]) -> float:
    return sum(math.log(q.get(y, q["other"])) for y in ys) / len(ys)


def landing(comp: Counter, order: list[str]):
    n = sum(comp.values())
    if n == 0:
        return None
    o = sorted(comp, key=lambda m: (-comp[m], order.index(m) if m in order else 99, m))
    second = comp[o[1]] if len(o) > 1 else 0
    return o[0] if (comp[o[0]] - second) / n >= 0.15 else None


def qlik_from_passes(nd_of: dict) -> dict:
    """Per (task, algorithm): mean per-token log-prob over the raw passes; top-1 over the unit's non-default set and
    the softmax distribution (x 0.98, 'other' 0.02)."""
    acc = defaultdict(list)
    progs = defaultdict(set)
    for r in jl(ROOT / "data/qlik_tf.jsonl"):
        if r.get("set") == "own_bf16":
            acc[(r["task"], r["mode"])].append(r["norm"])
            progs[(r["task"], r["mode"])].add(r["j"])
    out = {}
    for t, nd in nd_of.items():
        s = {m: sum(acc[(t, m)]) / len(acc[(t, m)]) for m in nd if acc.get((t, m))}
        if len(s) < 2:
            out[t] = {"top1": None, "q": None}
            continue
        top = sorted(s, key=lambda m: (-s[m], m))[0]
        mx = max(s.values())
        e = {m: math.exp(v - mx) for m, v in s.items()}
        z = sum(e.values())
        q = {m: (1 - OTHER) * e[m] / z for m in s}
        miss = [m for m in nd if m not in s]
        if miss:
            floor = min(e.values()) / z
            for m in miss:
                q[m] = (1 - OTHER) * floor
            zz = sum(q.values()) / (1 - OTHER)
            q = {m: v / zz for m, v in q.items()}
        q["other"] = OTHER
        out[t] = {"top1": top, "q": q}
    return out


def build_events(labs: dict, units: dict, which: str) -> list[dict]:
    events = []
    for t in PUSH:
        u = units[t]
        if u["D"] is None:
            continue
        cells = {"FD": defaultdict(list), "PN": defaultdict(list)}
        for r in labs.values():
            if r["task"] != t:
                continue
            st, arm = r.get("stage"), str(r.get("arm") or "")
            if st in ("push", "confirm") and arm.startswith("esc"):
                cells["FD"]["old:" + arm].append(r)
            elif st in ("push6", "confirm6") and arm.startswith("esc"):
                cells["FD"]["fresh:" + arm].append(r)
            elif st == "push" and arm.startswith("pn_a"):
                cells["PN"]["old:" + arm].append(r)
            elif st == "push6" and arm.startswith("pn6"):
                cells["PN"]["fresh:" + arm].append(r)
        for nudge in ("FD", "PN"):
            pooled = []
            for key, rr in cells[nudge].items():
                if which == "fresh" and not key.startswith("fresh:"):
                    continue
                if rr and sum(1 for r in rr if r.get("passed")) / len(rr) >= 0.8 * u["twin_pass"]:
                    pooled += rr
            off = [r for r in pooled if correct(r) and r["label"] != u["D"]]
            comp = Counter(r["label"] for r in off if r["label"] in u["nd"])
            if sum(comp.values()) < 5:
                continue
            ys = [r["label"] if r["label"] in u["nd"] else "other" for r in off]
            events.append({"unit": t, "nudge": nudge, "landing": landing(comp, u["cat"]), "ys": ys,
                           "chance": 1 / len(u["nd"]), "r_u": u["r_u"], "t_u": u["t_u"], "lik": u["lik"],
                           "tail_empty": u["t_u"] is None})
    return events


def hits(events: list[dict], key: str) -> tuple[int, int, float | None]:
    ev = [e for e in events if e["landing"] and e[key]]
    k = sum(1 for e in ev if e[key] == e["landing"])
    return k, len(ev), (pb_sf(k, [e["chance"] for e in ev]) if ev else None)


def main() -> None:
    labs = load()
    fc = json.loads((ROOT / "predictions/forecasts_G6.json").read_text())["units"]
    units = {}
    for t, u0 in fc.items():
        cat = u0["catalogue"]
        twin = [r for r in labs.values() if r["task"] == t and ((r.get("stage") == "twin" and r.get("arm") == "twin")
                                                                or r.get("stage") == "twin6")]
        D = default(twin, cat)
        nd = [m for m in cat if m != D]
        pt = [r for r in labs.values() if r["task"] == t and r.get("stage") in ("ptchat", "ptplain", "ptfs6")]
        cc = Counter(r["label"] for r in pt if correct(r))
        vc = Counter(r["label"] for r in pt if valid(r))
        fsc = Counter(r["label"] for r in pt if r.get("stage") == "ptfs6" and valid(r))
        prim = vc if sum(cc.values()) < 20 else cc
        off = [r for r in twin if correct(r) and r["label"] != D]
        tc = Counter(r["label"] for r in off)
        tv = Counter(r["label"] for r in twin if valid(r) and r["label"] != D)
        t10 = Counter(r["label"] for r in off if is_t10(r))
        tw10 = [r for r in twin if is_t10(r)]
        units[t] = {"D": D, "nd": nd, "cat": cat, "r_u": argmax_rule(nd, [prim, cc, vc, fsc]),
                    "t_u": argmax_rule(nd, [tc, tv, t10]),
                    "q_base": addone(Counter({m: prim.get(m, 0) for m in nd} | {"other": prim.get("other", 0)}), nd),
                    "q_tail": addone(tc, nd),
                    "twin_pass": sum(1 for r in tw10 if r.get("passed")) / len(tw10) if tw10 else 0.0}
    ql = qlik_from_passes({t: u["nd"] for t, u in units.items()})
    for t in units:
        units[t]["lik"] = ql[t]["top1"]
        units[t]["q_lik"] = ql[t]["q"]
    pooled = build_events(labs, units, "pooled")
    fresh = build_events(labs, units, "fresh")
    for e in pooled:
        u = units[e["unit"]]
        e["ls_base"], e["ls_tail"] = mean_log(u["q_base"], e["ys"]), mean_log(u["q_tail"], e["ys"])
        e["ls_lik"] = mean_log(u["q_lik"], e["ys"]) if u["q_lik"] else None
        e["ls_base_eq"] = mean_log(equal_other(u["q_base"], u["nd"]), e["ys"])
        e["ls_tail_eq"] = mean_log(equal_other(u["q_tail"], u["nd"]), e["ys"])
        e["ls_lik_eq"] = mean_log(equal_other(u["q_lik"], u["nd"]), e["ys"]) if u["q_lik"] else None
    clear = [e for e in pooled if e["landing"]]
    te = [e for e in clear if e["tail_empty"] and e["r_u"]]
    disc = [e for e in clear if e["lik"] and e["r_u"] and e["r_u"] != e["lik"]]
    tdisc = [e for e in clear if e["t_u"] and e["r_u"] and e["r_u"] != e["t_u"]]
    b_only = sum(1 for e in disc if e["r_u"] == e["landing"] and e["lik"] != e["landing"])
    l_only = sum(1 for e in disc if e["lik"] == e["landing"] and e["r_u"] != e["landing"])
    tb = sum(1 for e in tdisc if e["r_u"] == e["landing"] and e["t_u"] != e["landing"])
    tt = sum(1 for e in tdisc if e["t_u"] == e["landing"] and e["r_u"] != e["landing"])

    def mean(xs: list) -> float | None:
        xs = [x for x in xs if x is not None]
        return sum(xs) / len(xs) if xs else None
    hr, hl, hq = hits(pooled, "r_u"), hits(pooled, "t_u"), hits(pooled, "lik")
    fr, ft, fq = hits(fresh, "r_u"), hits(fresh, "t_u"), hits(fresh, "lik")
    mine = {"n_events": len(pooled), "n_clear": len(clear),
            "hits_r_u": hr[0], "n_r_u": hr[1], "p_r_u": hr[2], "hits_t_u": hl[0], "n_t_u": hl[1], "p_t_u": hl[2],
            "hits_qlik": hq[0], "n_qlik": hq[1], "p_qlik": hq[2],
            "tail_empty_events": len(te), "tail_empty_hits": sum(1 for e in te if e["r_u"] == e["landing"]),
            "p_tail_empty": pb_sf(sum(1 for e in te if e["r_u"] == e["landing"]), [e["chance"] for e in te]) if te else None,
            "discordant_lik_events": len(disc), "base_only": b_only, "lik_only": l_only,
            "sign_p": binom_sf(b_only, b_only + l_only), "tail_discordant_events": len(tdisc), "tail_base_only": tb,
            "tail_only": tt,
            "mean_base_minus_tail": mean([e["ls_base"] - e["ls_tail"] for e in pooled]),
            "mean_base_minus_lik": mean([e["ls_base"] - e["ls_lik"] for e in pooled if e["ls_lik"] is not None]),
            "mean_base_minus_tail_equal_other": mean([e["ls_base_eq"] - e["ls_tail_eq"] for e in pooled]),
            "mean_base_minus_lik_equal_other": mean([e["ls_base_eq"] - e["ls_lik_eq"] for e in pooled
                                                     if e["ls_lik_eq"] is not None]),
            "fresh_n_events": len(fresh), "fresh_hits_r_u": fr[0], "fresh_n_r_u": fr[1], "fresh_hits_t_u": ft[0],
            "fresh_n_t_u": ft[1], "fresh_hits_qlik": fq[0], "fresh_n_qlik": fq[1]}
    l1 = json.loads((ROOT / "results/l1_contest.json").read_text())
    rep, rf = l1["primary_pooled"], l1["split_fresh_only"]
    c = rep["logscore_contests"]
    ce = rep["logscore_contests_uniform_other"]
    reported = {"n_events": rep["n_events"], "n_clear": rep["n_clear_landing"],
                "hits_r_u": rep["hits_r_u_all"]["hits"], "n_r_u": rep["hits_r_u_all"]["n_events"],
                "p_r_u": rep["hits_r_u_all"]["poisson_binomial_p"],
                "hits_t_u": rep["hits_t_u_all"]["hits"], "n_t_u": rep["hits_t_u_all"]["n_events"],
                "p_t_u": rep["hits_t_u_all"]["poisson_binomial_p"],
                "hits_qlik": rep["hits_qlik_all"]["hits"], "n_qlik": rep["hits_qlik_all"]["n_events"],
                "p_qlik": rep["hits_qlik_all"]["poisson_binomial_p"],
                "tail_empty_events": rep["L1a_tail_empty"]["n_events"], "tail_empty_hits": rep["L1a_tail_empty"]["hits"],
                "p_tail_empty": rep["L1a_tail_empty"]["poisson_binomial_p"],
                "discordant_lik_events": rep["L1b_discordant_lik"]["n_events"],
                "base_only": rep["L1b_discordant_lik"]["base_only"], "lik_only": rep["L1b_discordant_lik"]["rival_only"],
                "sign_p": rep["L1b_discordant_lik"]["sign_test_p_one_sided"],
                "tail_discordant_events": rep["tail_rival_discordant"]["n_events"],
                "tail_base_only": rep["tail_rival_discordant"]["base_only"],
                "tail_only": rep["tail_rival_discordant"]["rival_only"],
                "mean_base_minus_tail": c["base_vs_tail"]["mean_diff_nats"],
                "mean_base_minus_lik": c["base_vs_lik_norm"]["mean_diff_nats"],
                "mean_base_minus_tail_equal_other": ce["base_vs_tail"]["mean_diff_nats"],
                "mean_base_minus_lik_equal_other": ce["base_vs_lik_norm"]["mean_diff_nats"],
                "fresh_n_events": rf["n_events"], "fresh_hits_r_u": rf["hits_r_u_all"]["hits"],
                "fresh_n_r_u": rf["hits_r_u_all"]["n_events"], "fresh_hits_t_u": rf["hits_t_u_all"]["hits"],
                "fresh_n_t_u": rf["hits_t_u_all"]["n_events"], "fresh_hits_qlik": rf["hits_qlik_all"]["hits"],
                "fresh_n_qlik": rf["hits_qlik_all"]["n_events"]}
    # rescored iteration-5 tally (exp28 landings; repaired forecasts re-derived above)
    e_a2 = json.loads((ROOT / "inputs/exp28/results/e_a2.json").read_text())["events"]
    old = {"repaired_r_u": sum(1 for e in e_a2 if units[e["unit"]]["r_u"] == e["landing"]),
           "t_u": sum(1 for e in e_a2 if units[e["unit"]]["t_u"] == e["landing"]),
           "qlik": sum(1 for e in e_a2 if units[e["unit"]]["lik"] == e["landing"]),
           "n_r_u_defined": sum(1 for e in e_a2 if units[e["unit"]]["r_u"] is not None)}
    ot = json.loads((ROOT / "results/old_tally.json").read_text())["all7"]
    mine.update({f"old_{k}": v for k, v in old.items()})
    reported.update({"old_repaired_r_u": ot["hit_repaired"]["hits"], "old_t_u": ot["hit_tail"]["hits"],
                     "old_qlik": ot["hit_qlik"]["hits"], "old_n_r_u_defined": ot["hit_repaired"]["n_defined"]})
    mism = {}
    for k, v in mine.items():
        w = reported.get(k)
        same = (v is None and w is None) or (v is not None and w is not None and abs(float(v) - float(w)) < 1e-9)
        if not same:
            mism[k] = {"rederived": v, "reported": w}
    unit_mism = {t: {"D": [units[t]["D"], fc[t]["D"]], "r_u": [units[t]["r_u"], fc[t]["r_u"]],
                     "t_u": [units[t]["t_u"], fc[t]["t_u"]], "lik": [units[t]["lik"], fc[t]["qlik_top1"]]}
                 for t in fc if (units[t]["D"], units[t]["r_u"], units[t]["t_u"], units[t]["lik"])
                 != (fc[t]["D"], fc[t]["r_u"], fc[t]["t_u"], fc[t]["qlik_top1"])}
    # placebos: the same hit test with a random forecast must reject at <= ~5%; a random forecast must not beat q_tail
    rng = random.Random(0)
    n_pl = 2000
    rej_r, rej_q, wins = 0, 0, 0
    for _ in range(n_pl):
        for key in ("r", "q"):
            ev = [e for e in clear if (e["r_u"] if key == "r" else e["lik"])]
            ks = sum(1 for e in ev if rng.choice(units[e["unit"]]["nd"]) == e["landing"])
            if ev and pb_sf(ks, [e["chance"] for e in ev]) < 0.05:
                if key == "r":
                    rej_r += 1
                else:
                    rej_q += 1
        d = []
        for e in pooled:
            nd = units[e["unit"]]["nd"]
            w = [rng.random() for _ in range(len(nd) + 1)]
            z = sum(w)
            q = {m: x / z for m, x in zip(nd + ["other"], w)}
            d.append(mean_log(q, e["ys"]) - e["ls_tail"])
        if d and sum(d) / len(d) > 0.10:
            wins += 1
    out = {"rederived": mine, "reported": reported, "mismatches": mism, "n_mismatches": len(mism),
           "unit_mismatches": unit_mism, "n_values_compared": len(mine),
           "placebo_random_r_u_rejection_rate": rej_r / n_pl, "placebo_random_qlik_top1_rejection_rate": rej_q / n_pl,
           "placebo_random_forecast_beats_tail_by_0.10_rate": wins / n_pl,
           "not_rederived": ["BCa and unit-cluster bootstrap CIs", "exact Wilcoxon p values", "unit sign-flip p values",
                             "push descriptives", "pt audit agreement (judge outputs)", "novelty classes (judge outputs)"]}
    (ROOT / "results/rederive_l1.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k not in ("rederived", "reported")}, indent=1))


if __name__ == "__main__":
    main()
