#!/usr/bin/env python3
"""Independent re-derivation of the panel-II headlines (Python standard library only; no code shared with src/ or
analysis/). Inputs: data/samples.jsonl (one row per program), predictions/units/<u>.json (the committed forecasts),
results/l1.json (the frozen analysis output to check against). Re-derives the twin baseline, every cell's
qualification, every CONFIRMATION landing event, L1a (hits, exact Poisson-binomial p) and L1b (b, c, sign-test p);
counts mismatches. Placebos that must fail: (1) r_u replaced by a random non-default algorithm per unit (hit rate
must sit at chance), (2) the twin itself treated as a nudge (no event), (3) q_base and q_lik swapped (L1b flips)."""

import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load():
    rows = [json.loads(l) for l in (ROOT / "data" / "samples.jsonl").read_text().splitlines() if l.strip()]
    units = {}
    for p in sorted((ROOT / "predictions" / "units").glob("II*.json")):
        units[p.stem] = json.loads(p.read_text())
    return rows, units


def pb_tail(ps, k):
    dist = [1.0] + [0.0] * len(ps)
    for p in ps:
        new = [0.0] * (len(ps) + 1)
        for i, v in enumerate(dist):
            if v:
                new[i] += v * (1 - p)
                if i + 1 <= len(ps):
                    new[i + 1] += v * p
        dist = new
    return sum(dist[k:])


def sign_p(b, c):
    n = b + c
    return 1.0 if n == 0 else sum(math.comb(n, i) for i in range(b, n + 1)) / 2 ** n


def events_for(rows, u, c):
    d = c["default"]
    S = [a for a in c["catalogue"] if a != d]
    eng_ok = (c.get("engine_check_twin") or {}).get("pass", True)
    tw = [r for r in rows if r["unit"] == u and r["arm"] == "TWIN" and r["model_tag"] == "instruct" and
          ((r["engine"] == "hf" and r["slot"] < 10) or (eng_ok and r["engine"] == "vllm"))]
    tpass = sum(1 for r in tw if r["passed"]) / len(tw)
    cells = defaultdict(list)
    for r in rows:
        if r["unit"] == u and r["family"] in ("ESC", "PN", "GTN"):
            cells[(r["family"], r["arm"])].append(r)
    by_nudge = defaultdict(Counter)
    for (fam, arm), rr in cells.items():
        if fam == "ESC":
            s30 = [r for r in rr if r["slot"] <= 5]
            use = s30 if len(s30) >= 30 else [r for r in rr if r["slot"] <= 1]
        else:
            if fam == "PN" and arm not in ("PN_a2.0", "PN_a4.0"):
                continue
            if fam == "GTN" and arm != "GTN_a2.0":
                continue
            use = rr
        if not use:
            continue
        if sum(1 for r in use if r["passed"]) / len(use) < 0.8 * tpass - 1e-12:
            continue
        by_nudge[fam].update(r["label"] for r in use if r["passed"] and r["label"] in S)
    out = []
    for fam, cnt in by_nudge.items():
        n = sum(cnt.values())
        if n < 5:
            continue
        srt = sorted(S, key=lambda a: (-cnt.get(a, 0), S.index(a)))
        lead = cnt.get(srt[0], 0) / n - (cnt.get(srt[1], 0) / n if len(srt) > 1 else 0)
        modal = srt[0] if lead >= 0.15 - 1e-12 else "NO_CLEAR_LANDING"
        out.append({"event_id": f"{u}|{fam}", "modal": modal, "K": c["K"], "r_u": c["r_u"], "qlik": c["qlik_top1"],
                    "tail_empty": c["tail_empty"], "discordant": c["discordant"], "S": S})
    return out


def l1(events, key_r="r_u", key_q="qlik"):
    Ea = [e for e in events if e["tail_empty"]]
    hits = sum(1 for e in Ea if e["modal"] == e[key_r])
    pa = pb_tail([1 / (e["K"] - 1) for e in Ea], hits) if Ea else None
    Eb = [e for e in events if e["discordant"]]
    b = sum(1 for e in Eb if e["modal"] == e[key_r] and e["modal"] != e[key_q])
    c = sum(1 for e in Eb if e["modal"] == e[key_q] and e["modal"] != e[key_r])
    return {"n_a": len(Ea), "hits": hits, "p_a": pa, "n_b": len(Eb), "b": b, "c": c, "p_b": sign_p(b, c) if Eb else None}


def main():
    rows, units = load()
    events = []
    for u, c in units.items():
        if c["default"] == "NO_DEFAULT":
            continue
        events += events_for(rows, u, c)
    mine = l1(events)
    frozen = json.loads((ROOT / "results" / "l1.json").read_text())
    ref = {"n_a": frozen["L1a"]["n_events"], "hits": frozen["L1a"]["hits_r_u"], "p_a": frozen["L1a"]["p"],
           "n_b": frozen["L1b"]["n_events"], "b": frozen["L1b"]["b_r_u_only"], "c": frozen["L1b"]["c_qlik_only"],
           "p_b": frozen["L1b"]["p"]}
    mism = [k for k in ref if (ref[k] is None) != (mine[k] is None) or
            (ref[k] is not None and abs(float(ref[k]) - float(mine[k])) > 1e-9)]
    ev_ids = sorted(e["event_id"] for e in events)
    frozen_ids = sorted(frozen.get("event_ids", []))
    # placebo 1: random non-default r_u per unit, 2,000 draws
    rng = random.Random(20261021)
    rates, chance = [], []
    for _ in range(2000):
        pick = {e["event_id"].split("|")[0]: None for e in events}
        for u in pick:
            S = next(e["S"] for e in events if e["event_id"].startswith(u + "|"))
            pick[u] = rng.choice(S)
        hits = sum(1 for e in events if e["modal"] == pick[e["event_id"].split("|")[0]])
        rates.append(hits / max(len(events), 1))
    chance = sum(1 / (e["K"] - 1) for e in events) / max(len(events), 1)
    # placebo 2: twin-as-nudge (the twin's own correct S programs pooled like a nudge cell)
    twin_events = 0
    for u, c in units.items():
        if c["default"] == "NO_DEFAULT":
            continue
        S = [a for a in c["catalogue"] if a != c["default"]]
        tw = [r for r in rows if r["unit"] == u and r["arm"] == "TWIN" and r["engine"] == "hf" and r["slot"] < 10]
        n = sum(1 for r in tw if r["passed"] and r["label"] in S)
        twin_events += n >= 5
    # placebo 3: swap q_base and q_lik predictions
    swapped = l1(events, key_r="qlik", key_q="r_u")
    out = {"rederived": mine, "frozen": ref, "mismatches": mism, "event_ids_match": ev_ids == frozen_ids,
           "events": ev_ids, "placebo_random_r_u": {"mean_hit_rate": sum(rates) / len(rates),
                                                    "chance": chance},
           "placebo_twin_as_nudge_events": twin_events,
           "placebo_swap_base_qlik": {"b": swapped["b"], "c": swapped["c"], "p_b": swapped["p_b"],
                                      "flipped": swapped["b"] == mine["c"] and swapped["c"] == mine["b"]}}
    (ROOT / "results" / "rederive.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("rederived", "mismatches", "event_ids_match", "placebo_random_r_u",
                                          "placebo_twin_as_nudge_events", "placebo_swap_base_qlik")}, indent=1))
    sys.exit(0)


if __name__ == "__main__":
    main()
