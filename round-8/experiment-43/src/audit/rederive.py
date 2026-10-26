#!/usr/bin/env python3
"""Independent standard-library re-derivation of every headline of claim L from raw rows and COMMITTED predictions.

Reads only: data/samples_raw.jsonl, data/labels.jsonl, data/adjudicated_labels.jsonl (if any),
predictions/commit1_<family>.json, predictions/commit2_<family>.json, commitments.log, results/base_tf_*.json.
Recomputes: the hash chain; per unit and temperature the observed attempted-label shares; MAE (mean TVD over the four
top-p-1 temperatures) of L, B0, B1, B2, BH; the drop T 1.0 -> 0.3 McNemar counts and exact one-sided p; the unit and
claim verdicts; H(A | classes) as committed; the base-arm margin gains. Placebos (must fail): (1) temperature labels
shuffled within slots (the drop test should reject at about the nominal rate); (2) predictions assigned to the wrong
unit (MAE should rise). Writes results/rederive.json with every check and mismatch against results/analysis_L.json.
"""

import hashlib
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPS = (0.3, 0.7, 1.0, 1.3)


def jl(p):
    p = Path(p)
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def chain():
    prev = hashlib.sha256(b"iter8_L").hexdigest()
    ok = True
    names = []
    for line in (ROOT / "commitments.log").read_text().splitlines():
        if not line.strip():
            continue
        utc, name, h, c = line.split("  ")
        f = ROOT / "predictions" / f"{name}.json"
        c2 = hashlib.sha256((prev + h).encode()).hexdigest()
        ok &= f.exists() and sha(f) == h and c2 == c
        prev = c
        names.append(name)
    return {"ok": ok, "commits": names}


def tvd(p, q):
    return 0.5 * sum(abs(a - b) for a, b in zip(p, q))


def binom_tail_ge(k, n):
    return sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n if n else 1.0


def main():
    rows = jl(ROOT / "data" / "samples_raw.jsonl")
    labs = {r["sid"]: r for r in jl(ROOT / "data" / "labels.jsonl")}
    for r in jl(ROOT / "data" / "adjudicated_labels.jsonl"):
        if r.get("label") and r["sid"] in labs:
            labs[r["sid"]] = dict(labs[r["sid"]], label=r["label"])
    preds, locs = {}, {}
    for fam in ("gemma", "llama", "qwen"):
        p2 = ROOT / "predictions" / f"commit2_{fam}.json"
        p1 = ROOT / "predictions" / f"commit1_{fam}.json"
        if p2.exists():
            preds.update(json.loads(p2.read_text())["units"])
        if p1.exists():
            locs.update(json.loads(p1.read_text())["units"])
    an_p = ROOT / "results" / "analysis_L.json"
    an = json.loads(an_p.read_text()) if an_p.exists() else {"units": {}}
    out = {"chain": chain(), "units": {}, "mismatches": []}
    units_rows = {}
    for r in rows:
        if r["arm"] == "sweep":
            units_rows.setdefault(r["unit"], []).append(r)
    rng = random.Random(20261023)
    for u, pr in preds.items():
        if u not in units_rows:
            continue
        bins = pr["bins"]

        def lab_of(sid):
            l = labs.get(sid, {}).get("label")
            if l in bins:
                return l
            return "invalid" if l in ("invalid", "no_code") else "other"
        obs = {}
        slot = {}
        for T in TEMPS:
            rr = [r for r in units_rows[u] if abs(r["T"] - T) < 1e-9]
            c = {b: 0 for b in bins}
            for r in rr:
                l = lab_of(r["sid"])
                c[l] += 1
                slot[(T, r["template"], r["slot"])] = l
            n = len(rr)
            obs[T] = [c[b] / n for b in bins] if n else None
        if any(obs[T] is None for T in TEMPS):
            continue
        mae = {m: sum(tvd(pr["cells"][f"p1|{T}"][m], obs[T]) for T in TEMPS) / 4 for m in ("L", "B0", "B1", "B2", "BH")}
        loc = locs.get(u, {})
        mino = loc.get("minority")
        drop = None
        if mino:
            keys = {(w, s) for (T, w, s) in slot if T == 1.0}
            b = sum(slot.get((1.0, w, s)) == mino and slot.get((0.3, w, s)) != mino for w, s in keys)
            c = sum(slot.get((1.0, w, s)) != mino and slot.get((0.3, w, s)) == mino for w, s in keys)
            drop = {"b": b, "c": c, "p_one_sided": binom_tail_ge(b, b + c)}
            # placebo 1: temperature labels shuffled within slots
            rej = 0
            for _ in range(300):
                bb = cc = 0
                for w, s in keys:
                    labsT = [slot.get((T, w, s)) for T in TEMPS]
                    rng.shuffle(labsT)
                    bb += labsT[2] == mino and labsT[0] != mino
                    cc += labsT[2] != mino and labsT[0] == mino
                rej += binom_tail_ge(bb, bb + cc) < 0.05
            drop["placebo_reject_rate"] = rej / 300
        H = loc.get("H_unit_bits")
        boundary = loc.get("boundary")
        passes = mae["L"] <= 0.10 and (boundary or (H is not None and H <= 0.3))
        rec = {"mae": mae, "drop": drop, "H": H, "pass": passes, "held_out": u.startswith(("G-", "L-"))}
        a = an["units"].get(u)
        if a:
            for m in mae:
                if abs(a["mae"]["p1"][m] - mae[m]) > 1e-9:
                    out["mismatches"].append(f"{u} MAE {m}: {a['mae']['p1'][m]} vs {mae[m]}")
            if a.get("drop") and drop and a["drop"]["mcnemar_b_c"] != [drop["b"], drop["c"]]:
                out["mismatches"].append(f"{u} McNemar {a['drop']['mcnemar_b_c']} vs {[drop['b'], drop['c']]}")
            if a["pass"] != passes:
                out["mismatches"].append(f"{u} pass {a['pass']} vs {passes}")
        out["units"][u] = rec
    # placebo 2: predictions of another unit with the same bins length (MAE must rise)
    us = list(out["units"])
    pl = []
    for u in us:
        others = [v for v in us if v != u and len(preds[v]["bins"]) == len(preds[u]["bins"])]
        if not others:
            continue
        v = others[0]
        bins = preds[u]["bins"]
        o = []
        for T in TEMPS:
            rr = [r for r in units_rows[u] if abs(r["T"] - T) < 1e-9]
            c = {b: 0 for b in bins}
            for r in rr:
                l = labs.get(r["sid"], {}).get("label")
                c[l if l in bins else ("invalid" if l == "invalid" else "other")] += 1
            o.append(tvd(preds[v]["cells"][f"p1|{T}"]["L"], [c[b] / len(rr) for b in bins]))
        pl.append({"unit": u, "pred_from": v, "mae_wrong_unit": sum(o) / 4, "mae_true": out["units"][u]["mae"]["L"]})
    out["placebo_wrong_unit"] = pl
    scored = out["units"]
    held = {u: r for u, r in scored.items() if r["held_out"]}
    n_pass = sum(r["pass"] for r in scored.values())
    out["verdict"] = {"n_scored": len(scored), "n_pass": n_pass, "n_heldout_scored": len(held),
                      "n_heldout_pass": sum(r["pass"] for r in held.values()),
                      "claim_pass": len(scored) > 0 and n_pass / len(scored) >= 0.7 and
                      sum(r["pass"] for r in held.values()) >= 3 and len(held) >= 4,
                      "disconfirmed": sum(r["mae"]["L"] > 0.2 for r in held.values()) >= 3}
    v = an.get("verdict")
    if v and (v["n_pass"] != n_pass or v["n_heldout_pass"] != out["verdict"]["n_heldout_pass"]):
        out["mismatches"].append(f"verdict counts {v['n_pass']}/{v['n_heldout_pass']} vs {n_pass}/"
                                 f"{out['verdict']['n_heldout_pass']}")
    # base arm margins
    bi, bb = ROOT / "results" / "base_tf_qwen.json", ROOT / "results" / "base_tf_qwen_base.json"
    if bi.exists() and bb.exists():
        I, B = json.loads(bi.read_text()), json.loads(bb.read_text())
        out["base_margin_gain"] = {t: sum(I["decision"][t][f"{w}|chat"]["margin"] - B["decision"][t][f"{w}|chat"]["margin"]
                                          for w in ("W1", "W2", "W3", "W4", "W5")) / 5 for t in I["decision"]
                                   if t in B["decision"]}
    out["n_checks"] = len(out["units"]) * 7 + 2
    out["n_mismatches"] = len(out["mismatches"])
    (ROOT / "results" / "rederive.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({"chain": out["chain"]["ok"], "units": len(out["units"]), "mismatches": out["mismatches"],
                      "verdict": out["verdict"]}, indent=1))


if __name__ == "__main__":
    main()
