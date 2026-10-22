#!/usr/bin/env python3
"""Independent re-derivation (no code shared with analysis/ or pool_l1.py): recompute, from data/samples.jsonl and the
committed predictions/units/<u>.json only, every unit's escape fraction E_u(alpha), every landing event (counts,
existence, modal landing, clear) and the L1a / L1b statistics, and compare them with units.json, landing_events.json
and results/pool_l1_panelI.json (0 mismatches required). Placebos: (1) the forecast replaced by a random non-default
catalogue mode (2,000 draws): the L1a hit rate must fall to chance on average; (2) twin as push: the HF twin rows
scored as if they were a push cell give E_u = 0 for every unit.
Writes results/rederive.json. Usage: python audit/rederive.py"""

from __future__ import annotations

import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load():
    S = [json.loads(l) for l in (ROOT / "data" / "samples.jsonl").read_text().splitlines() if l.strip()]
    P = {p.stem: json.loads(p.read_text()) for p in (ROOT / "predictions" / "units").glob("*.json")}
    return S, P


def seeds_of(u):
    import hashlib
    return [int(hashlib.sha256(f"iter6|panelI|{u}|dir|{k}".encode()).hexdigest()[:8], 16) for k in range(8)]


def share(rows, D, cat):
    rs = [r for r in rows if r["label"] != "disputed"]
    n = len(rs)
    ok = sum(1 for r in rs if r["passed"])
    off = sum(1 for r in rs if r["passed"] and r["label"] in cat and r["label"] != D)
    return n, ok, off


def sf(k, n, p):
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def pb_sf(ps, x):
    # P(X >= x) by convolution, written independently of pool_l1.py
    probs = {0: 1.0}
    for p in ps:
        nxt = defaultdict(float)
        for k, v in probs.items():
            nxt[k] += v * (1 - p)
            nxt[k + 1] += v * p
        probs = nxt
    return sum(v for k, v in probs.items() if k >= x)


def main():
    S, P = load()
    units = json.loads((ROOT / "units.json").read_text())["units"]
    events = json.loads((ROOT / "landing_events.json").read_text())["events"]
    pool = json.loads((ROOT / "results" / "pool_l1_panelI.json").read_text())
    mism = []
    by_u = defaultdict(list)
    for r in S:
        if r["model_tag"] == "instruct" and (r.get("engine") or "").startswith("hf"):
            by_u[r["unit"]].append(r)
    mine_events = []
    for U in units:
        u = U["unit"]
        rec = P[u]
        D, cat = rec["default"], rec["catalogue"]
        R = by_u[u]
        tw = [r for r in R if r["arm"] == "TWINHF"]
        n_t, ok_t, off_t = share(tw, D, cat)
        tpass, toff = ok_t / n_t, off_t / n_t
        E = {}
        pooled = {"ESC": [], "PN": [], "GTN": []}
        for al in (1.0, 2.0, 4.0):
            c = 0
            for s in seeds_of(u):
                arm = f"ESC_d{s}_a{al:g}"
                rows = [r for r in R if r["arm"] == arm]
                if not rows:
                    continue
                n1, ok1, off1 = share([r for r in rows if r["slot"] in (0, 1)], D, cat)
                p1 = n1 and off1 / n1 >= toff + 0.20 and ok1 / n1 >= 0.8 * tpass
                n, ok, off = share(rows, D, cat)
                if p1 and n >= 25 and sf(off, n, (off_t + 0.5) / (n_t + 1)) < 0.05:
                    c += 1
                if n and ok / n >= 0.8 * tpass:
                    pooled["ESC"] += rows
            E[str(al)] = c / 8
        for arm in ("PN_a2", "PN_a4", "GTN_a2"):
            rows = [r for r in R if r["arm"] == arm]
            n, ok, off = share(rows, D, cat)
            if n and ok / n >= 0.8 * tpass:
                pooled[arm.split("_")[0]] += rows
        if any(abs(E[a] - U["E_u_by_alpha"].get(a, -1)) > 1e-12 for a in E):
            mism.append({"unit": u, "what": "E_u", "mine": E, "theirs": U["E_u_by_alpha"]})
        # twin-as-push placebo: the twin's own rows can never exceed the twin by 0.20
        n, ok, off = share(tw, D, cat)
        U["_placebo_twin_E"] = 1.0 if (n and off / n >= toff + 0.20) else 0.0
        for t, rows in pooled.items():
            cnt = Counter(r["label"] for r in rows if r["passed"] and r["label"] in cat and r["label"] != D)
            tot = sum(cnt.values())
            srt = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))
            modal = srt[0][0] if srt else None
            lead = ((srt[0][1] - (srt[1][1] if len(srt) > 1 else 0)) / tot) if tot else 0.0
            ev = {"unit": u, "nudge_type": t, "exists": tot >= 5, "modal": modal, "clear": tot >= 5 and lead >= 0.15,
                  "tot": tot, "K": rec["K"], "r_u": rec["r_u"], "q": rec["q_lik_top1"], "tail_empty": rec["tail_empty"],
                  "discordant": rec["discordant"], "cat": cat, "D": D}
            mine_events.append(ev)
            th = next((e for e in events if e["unit"] == u and e["nudge_type"] == t), None)
            if th is None or th["exists"] != ev["exists"] or th["clear_landing"] != ev["clear"] or \
                    (ev["clear"] and th["modal_landing"] != ev["modal"]) or \
                    th["n_correct_off_default_catalogue"] != tot:
                mism.append({"unit": u, "type": t, "what": "event", "mine": ev, "theirs": th and {
                    k: th[k] for k in ("exists", "clear_landing", "modal_landing", "n_correct_off_default_catalogue")}})
    ex = [e for e in mine_events if e["exists"]]
    A = [e for e in ex if e["tail_empty"]]
    x = sum(1 for e in A if e["clear"] and e["modal"] == e["r_u"])
    pa = pb_sf([1 / (e["K"] - 1) for e in A], x) if A else 1.0
    Bd = [e for e in ex if e["discordant"]]
    b = sum(1 for e in Bd if e["clear"] and e["modal"] == e["r_u"] and e["modal"] != e["q"])
    c = sum(1 for e in Bd if e["clear"] and e["modal"] == e["q"] and e["modal"] != e["r_u"])
    pl = pool["per_event"]
    if (len(A), x) != (pl["L1a"]["n"], pl["L1a"]["hits"]) or abs(pa - pl["L1a"]["p_poisson_binomial"]) > 1e-9:
        mism.append({"what": "L1a", "mine": [len(A), x, pa], "theirs": [pl["L1a"]["n"], pl["L1a"]["hits"],
                                                                       pl["L1a"]["p_poisson_binomial"]]})
    if (len(Bd), b, c) != (pl["L1b"]["n_discordant"], pl["L1b"]["b_base_only"], pl["L1b"]["c_qlik_only"]):
        mism.append({"what": "L1b", "mine": [len(Bd), b, c], "theirs": [pl["L1b"]["n_discordant"],
                                                                       pl["L1b"]["b_base_only"],
                                                                       pl["L1b"]["c_qlik_only"]]})
    rng = random.Random(0)
    hr, ch = [], []
    for _ in range(2000):
        if not A:
            break
        h = 0
        for e in A:
            nd = [m for m in e["cat"] if m != e["D"]]
            f = rng.choice(nd)
            h += int(e["clear"] and e["modal"] == f)
        hr.append(h / len(A))
        ch.append(sum(1 / (e["K"] - 1) for e in A) / len(A))
    clear_share = (sum(1 for e in A if e["clear"]) / len(A)) if A else None
    out = {"n_mismatches": len(mism), "mismatches": mism[:30],
           "L1a": {"n": len(A), "hits": x, "p": pa}, "L1b": {"n": len(Bd), "b": b, "c": c},
           "placebo_random_forecast": {"mean_hit_rate": (sum(hr) / len(hr)) if hr else None,
                                       "mean_chance": (sum(ch) / len(ch)) if ch else None,
                                       "share_events_clear": clear_share,
                                       "note": "a random forecast can hit only clear events: expected hit rate = "
                                               "chance x share of clear events"},
           "placebo_twin_as_push_E": {U["unit"]: U["_placebo_twin_E"] for U in units}}
    (ROOT / "results" / "rederive.json").write_text(json.dumps(out, indent=1))
    print({k: out[k] for k in ("n_mismatches", "L1a", "L1b", "placebo_random_forecast")})


if __name__ == "__main__":
    main()
