#!/usr/bin/env python3
"""Independent re-derivation (Python standard library only; shares no code with src/): recomputes the headline numbers
from the raw rows and compares them with the reported ones; runs the placebos, which must fail.

  TF   recovery at k* (seed 0) = mean(Delta_DAS) / mean(Delta_FULL) over held-out pairs with |Delta_FULL| >= 1
       (data/tf_<unit>_<site>.jsonl) vs results/dec_<unit>.json / band_T10.json
  GEN  correct-target counts per (site, arm, class) from data/samples_<unit>.jsonl + data/labels_<unit>.jsonl vs
       results/analysis.json; generation recovery and pass ratio recomputed
  PLACEBO-GEN  DAS and RAND outcomes swapped by a fair coin per slot: the DAS-RAND discordance must vanish (|a-b| small)
  PLACEBO-MED  a randomly permuted mediation predictor: |Spearman rho| must be < 0.3
Usage: python3 audit/rederive.py   (writes results/rederive.json)
"""

import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
DATA = ROOT / "data"


def jl(p):
    out = []
    if not p.exists():
        return out
    for line in p.read_text().splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def jr(p):
    return json.loads(p.read_text()) if p.exists() else None


def ranks(x):
    order = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and x[order[j + 1]] == x[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(x, y):
    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else 0.0


def tf_check(unit, site, rep_path, rtag=""):
    rows = jl(DATA / f"tf_{unit}_{site}{rtag}.jsonl")
    rep = jr(rep_path)
    if not rows or rep is None:
        return None
    k = rep["k_star"]
    sel = [r for r in rows if r["fit"] == "seed0" and r["rank_k"] == k and abs(r["delta_full"]) >= 1.0]
    if not sel:
        return None
    rec = (sum(r["delta"] for r in sel) / len(sel)) / (sum(r["delta_full"] for r in sel) / len(sel))
    return {"rederived": rec, "reported": rep["main"]["recovery"], "n": len(sel),
            "match": abs(rec - rep["main"]["recovery"]) < 1e-6}


def gen_check(unit):
    samples = {r["sample_id"]: r for r in jl(DATA / f"samples_{unit}.jsonl")}
    labels = {}
    for r in jl(DATA / f"labels_{unit}.jsonl"):
        labels.setdefault(r["sample_id"], r)
    an = jr(RES / "analysis.json") or {}
    out = {}
    for site in ("dec", "band"):
        cm = jr(ROOT / "predictions" / f"commit2_{unit}_{site}.json")
        if cm is None:
            continue
        rep = an.get(f"gen_{unit}_{site}", {}).get("classes", {})
        site_out = {}
        for c, slots in cm["slot_map"].items():
            for arm in ("BASE", "FULL", "DAS", "RAND"):
                n = next((x[3] for x in cm["cells"] if x[0] == site and x[1] == arm and x[2] == c), 0)
                k = 0
                m = 0
                for s in range(n):
                    sid = (f"{unit}|{site}|BASE|{slots[s]['base']}|{s}" if arm == "BASE" else
                           f"{unit}|{site}|{arm}|{c}|{s}")
                    l = labels.get(sid)
                    if l is None or sid not in samples:
                        continue
                    m += 1
                    k += int(l["label"] == c and bool(l.get("passed")))
                r = (rep.get(c, {}).get("arms", {}).get(arm) or {}).get("correct_target")
                site_out[f"{c}|{arm}"] = {"rederived": k, "n": m, "reported": r, "match": r == k}
            # placebo: swap DAS / RAND outcomes by a fair coin per slot
            rng = random.Random(7)
            a = b = 0
            for s in range(30):
                d = labels.get(f"{unit}|{site}|DAS|{c}|{s}")
                q = labels.get(f"{unit}|{site}|RAND|{c}|{s}")
                if not d or not q:
                    continue
                x = int(d["label"] == c and bool(d.get("passed")))
                y = int(q["label"] == c and bool(q.get("passed")))
                if rng.random() < 0.5:
                    x, y = y, x
                a += int(x and not y)
                b += int(y and not x)
            site_out[f"{c}|placebo_swap_DAS_RAND"] = {"a_only": a, "b_only": b,
                                                      "fails_as_expected": abs(a - b) <= max(3, 0.5 * (a + b))}
        out[site] = site_out
    return out


def med_placebo():
    m = jr(RES / "mediation_T10.json")
    if not m:
        return None
    d = [v for v in m["directions"].values() if v.get("escape_pooled") is not None]
    x = [v["pi"] for v in d]
    y = [v["escape_pooled"] for v in d]
    rho = spearman(x, y)
    rng = random.Random(11)
    xp = x[:]
    rng.shuffle(xp)
    rp = spearman(xp, y)
    return {"rho_rederived": rho, "rho_reported": (m.get("spearman_escape_pooled") or {}).get("rho"),
            "placebo_rho": rp, "placebo_fails_as_expected": abs(rp) < 0.3}


def binom_one_sided(a, b):
    """P(X >= a) for X ~ Binomial(a + b, 0.5): exact one-sided McNemar on discordant counts."""
    n = a + b
    if n == 0:
        return 1.0
    return sum(math.comb(n, k) for k in range(a, n + 1)) / 2 ** n


def c2_check(unit, rep_path, L, rtag=""):
    """c2 ratio = recovery(perm map) / recovery(true map), both over held-out pairs with |Delta_FULL| >= 1, from the
    per-pair rows (tf_<unit>_dec<rtag>.jsonl for the true map and Delta_FULL; tf_<unit>_dec_perm_L<L>.jsonl)."""
    rep = jr(rep_path)
    true = jl(DATA / f"tf_{unit}_dec{rtag}.jsonl")
    perm = jl(DATA / f"tf_{unit}_dec_perm_L{L}.jsonl")
    if rep is None or not true or not perm:
        return None
    k = rep["k_star"]
    full = {(r["src"], r["base"]): r["delta_full"] for r in true if r["fit"] == "seed0" and r["rank_k"] == k}
    dtrue = {(r["src"], r["base"]): r["delta"] for r in true if r["fit"] == "seed0" and r["rank_k"] == k}
    keys = [q for q in full if abs(full[q]) >= 1.0]
    mf = sum(full[q] for q in keys) / len(keys)
    rec_true = (sum(dtrue[q] for q in keys) / len(keys)) / mf
    out = {}
    fits = sorted({r["fit"] for r in perm})
    for f in fits:
        d = {}
        for r in perm:
            if r["fit"] == f:
                d[(r["src"], r["base"])] = r["delta"]       # last write wins (a refit row set replaces an earlier one)
        if not all(q in d for q in keys):
            continue
        rec = (sum(d[q] for q in keys) / len(keys)) / mf
        name = f.replace("perm_", "")
        reported = (rep["c2"].get(name) or {}).get("ratio_to_true_fit")
        out[name] = {"rederived_ratio": rec / rec_true, "reported_ratio": reported,
                     "match_0.02": reported is not None and abs(rec / rec_true - reported) < 0.02,
                     "fails_threshold_0.1": rec / rec_true > 0.10}
    return out


def mediation_check():
    an = jr(RES / "analysis.json") or {}
    med = jr(RES / "mediation_T10.json")
    if not med:
        return None
    labels = {}
    for r in jl(DATA / "labels_T10.jsonl"):
        labels.setdefault(r["sample_id"], r)
    esc = lambda r: bool(r) and bool(r.get("passed")) and r.get("label") in ("bfs", "dfs", "label_propagation")
    top = med["top10_escaping"]
    out = {}
    for arm in ("TASK", "RAND"):
        a = b = n = ep = ec = 0
        for sd in top:
            for s in range(30):
                x, y = labels.get(f"T10|med|PUSH|{sd}|{s}"), labels.get(f"T10|med|{arm}|{sd}|{s}")
                if not x or not y:
                    continue
                n += 1
                ex, ey = esc(x), esc(y)
                ep += ex
                ec += ey
                a += int(ex and not ey)
                b += int(ey and not ex)
        rem = 1 - ec / ep if ep else None
        rep = (an.get("mediation") or {}).get(f"clamp_{arm}", {})
        out[arm] = {"pairs": n, "escapes_push": ep, "escapes_clamp": ec, "removal_rederived": rem,
                    "removal_reported": rep.get("removal"), "match": rep.get("removal") is not None and rem is not None
                    and abs(rep["removal"] - rem) < 1e-9, "mcnemar_push_gt_clamp_p": binom_one_sided(a, b)}
    # prospective Spearman from the committed predictor (#4) and the raw labels
    c4 = jr(ROOT / "predictions" / "commit4_prospective.json")
    xs, ys = [], []
    for sd, v in (c4 or {}).get("pi", {}).items():
        rows = [labels.get(f"T10|pro|PUSH|{sd}|{s}") for s in range(10)]
        rows = [r for r in rows if r]
        if rows:
            xs.append(v["pi"])
            ys.append(sum(esc(r) for r in rows) / len(rows))
    rho = spearman(xs, ys) if len(xs) > 3 else None
    rep = ((an.get("mediation") or {}).get("prospective") or {}).get("spearman", {}).get("rho")
    out["prospective"] = {"n": len(xs), "rho_rederived": rho, "rho_reported": rep,
                          "match": rho is not None and rep is not None and abs(rho - rep) < 1e-9}
    return out


def mcnemar_check():
    """Exact one-sided McNemar DAS > RAND per (unit, site, class) from raw labels; placebo = DAS vs DAS-shuffled."""
    out = {}
    for unit in ("T10", "GRID"):
        labels = {}
        for r in jl(DATA / f"labels_{unit}.jsonl"):
            labels.setdefault(r["sample_id"], r)
        for site in ("dec", "band"):
            cm = jr(ROOT / "predictions" / f"commit2_{unit}_{site}.json")
            if not cm:
                continue
            for c in cm["slot_map"]:
                a = b = 0
                for s in range(30):
                    d = labels.get(f"{unit}|{site}|DAS|{c}|{s}")
                    q = labels.get(f"{unit}|{site}|RAND|{c}|{s}")
                    if not d or not q:
                        continue
                    x = d["label"] == c and bool(d.get("passed"))
                    y = q["label"] == c and bool(q.get("passed"))
                    a += int(x and not y)
                    b += int(y and not x)
                out[f"{unit}|{site}|{c}"] = {"das_only": a, "rand_only": b, "p_one_sided": binom_one_sided(a, b)}
    return out


def k2_check():
    """K2 from the per-site control flags in the raw result JSONs: disconfirmed iff a decision site fails c2 or c3."""
    res = {}
    for unit in ("T10", "GRID"):
        d = jr(RES / f"dec_{unit}.json")
        r = jr(RES / f"rinit_{unit}.json")
        if not d or not r:
            continue
        c2_fail = any(isinstance(v, dict) and "ratio_to_true_fit" in v and (v["ratio_to_true_fit"] or 0) > 0.10
                      for v in d["c2"].values())
        c3_fail = (r["mean_delta_rinit"] / r["mean_delta_trained"]) > 0.25
        res[unit] = {"c2_fail": c2_fail, "c3_fail": c3_fail,
                     "c3_ratio_from_means": r["mean_delta_rinit"] / r["mean_delta_trained"]}
    disc = any(v["c2_fail"] or v["c3_fail"] for v in res.values())
    rep = ((jr(RES / "analysis.json") or {}).get("K2") or {}).get("status")
    return {"by_unit": res, "status_rederived": "DISCONFIRMED" if disc else "NOT DISCONFIRMED", "status_reported": rep}


def main():
    out = {"tf": {"T10_dec": tf_check("T10", "dec", RES / "dec_T10.json"),
                  "T10_band": tf_check("T10", "band", RES / "band_T10.json"),
                  "GRID_dec": tf_check("GRID", "dec", RES / "dec_GRID.json"),
                  "T10_dec_L24": tf_check("T10", "dec", RES / "dec_T10_L24.json", "_L24")},
           "gen": {"T10": gen_check("T10"), "GRID": gen_check("GRID")},
           "mediation": med_placebo(),
           "c2": {"T10_L22": c2_check("T10", RES / "dec_T10.json", 22),
                  "GRID_L16": c2_check("GRID", RES / "dec_GRID.json", 16),
                  "T10_L24": c2_check("T10", RES / "dec_T10_L24.json", 24, "_L24")},
           "mediation_clamp_prospective": mediation_check(),
           "mcnemar_das_vs_rand": mcnemar_check(),
           "K2": k2_check()}
    flat = []
    for v in out["tf"].values():
        if v:
            flat.append(v["match"])
    for u in out["gen"].values():
        for site in u.values():
            for k, v in site.items():
                if "match" in v:
                    flat.append(v["match"])
    for grp in out["c2"].values():
        for v in (grp or {}).values():
            flat.append(v["match_0.02"])
    mc = out["mediation_clamp_prospective"] or {}
    for k in ("TASK", "RAND", "prospective"):
        if k in mc:
            flat.append(mc[k]["match"])
    if out["mediation"]:
        flat.append(abs(out["mediation"]["rho_rederived"] - out["mediation"]["rho_reported"]) < 1e-9)
    flat.append(out["K2"]["status_rederived"] == out["K2"]["status_reported"])
    out["all_match"] = all(flat) if flat else None
    out["n_checks"] = len(flat)
    (RES / "rederive.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({"all_match": out["all_match"], "n_checks": out["n_checks"]}))


if __name__ == "__main__":
    main()
