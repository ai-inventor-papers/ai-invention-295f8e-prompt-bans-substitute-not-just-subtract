#!/usr/bin/env python3
"""Independent stdlib-only re-derivation (testing plan T11): its own average-rank, OLS-residual and Pearson code
recomputes rho_dc, rho_cd and delta from results/pairs_<model>.csv; r_F and the EDGE/OPPOSITE verdicts from
results/geo_class_dist_<model>.csv; the frozen cell counts from data/factorial_set.jsonl and data/programs_v10.jsonl.
Compares with results/g1_<model>.json and results/g2_<model>.json; writes results/rederive.json. No numpy."""

import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOL = 1e-9


def ranks(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def resid(y, z):
    """Residuals of y on [1, z] by closed-form simple OLS."""
    n = len(y)
    my, mz = sum(y) / n, sum(z) / n
    szz = sum((a - mz) ** 2 for a in z)
    szy = sum((a - mz) * (b - my) for a, b in zip(z, y))
    b1 = szy / szz if szz > 0 else 0.0
    b0 = my - b1 * mz
    return [b - (b0 + b1 * a) for a, b in zip(z, y)]


def pearson(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    sab = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    saa = sum((x - ma) ** 2 for x in a)
    sbb = sum((y - mb) ** 2 for y in b)
    return sab / math.sqrt(saa * sbb) if saa > 0 and sbb > 0 else float("nan")


def partial(y, x, z):
    ry, rx, rz = ranks(y), ranks(x), ranks(z)
    return pearson(resid(ry, rz), resid(rx, rz))


def main():
    out = {"g1": {}, "g2": {}, "counts": {}, "mismatches": []}
    for tag in ("8b", "32b"):
        p = ROOT / f"results/pairs_{tag}.csv"
        if not p.exists():
            continue
        DS, DD, DC = [], [], []
        with p.open() as fh:
            for row in csv.DictReader(fh):
                DS.append(float(row["D_S"]))
                DD.append(float(row["D_disc"]))
                DC.append(float(row["D_cont"]))
        rdc, rcd = partial(DS, DD, DC), partial(DS, DC, DD)
        ref = json.loads((ROOT / f"results/g1_{tag}.json").read_text())["primary"]
        rec = {"rho_dc": rdc, "rho_cd": rcd, "delta": rdc - rcd, "ref_rho_dc": ref["rho_dc"],
               "ref_rho_cd": ref["rho_cd"], "ref_delta": ref["delta"], "n_pairs": len(DS)}
        for k in ("rho_dc", "rho_cd", "delta"):
            d = abs(rec[k] - rec["ref_" + k])
            rec[f"absdiff_{k}"] = d
            if d > 1e-6:          # pairs CSV stores D_S at 10 significant digits
                out["mismatches"].append(f"g1 {tag} {k}: {rec[k]} vs {rec['ref_' + k]}")
        out["g1"][tag] = rec
        # ---- G2 r_F from per-program class distances (full frame)
        q = ROOT / f"results/geo_class_dist_{tag}.csv"
        g2ref = json.loads((ROOT / f"results/g2_{tag}.json").read_text())
        per = defaultdict(lambda: {"fam": None, "g": math.inf, "med": None})
        with q.open() as fh:
            for row in csv.DictReader(fh):
                if row["frame"] != "full":
                    continue
                e = per[row["uid"]]
                e["fam"] = row["family"]
                e["med"] = float(row["frame_median"])
                if row["is_banned"] == "1":
                    e["g"] = min(e["g"], float(row["d"]))
        fams = defaultdict(list)
        med = None
        for u, e in per.items():
            fams[e["fam"]].append(e["g"])
            med = e["med"]
        rf = {}
        for f, gs in fams.items():
            r = statistics.median(gs) / med
            rf[f] = {"r_F": r, "verdict": "EDGE" if r < 1 else ("OPPOSITE" if r > 1 else "MIDDLE"),
                     "ref_r_F": g2ref["families_full"][f]["r_F"], "ref_verdict": g2ref["families_full"][f]["verdict"]}
            if abs(r - rf[f]["ref_r_F"]) > 1e-6 or rf[f]["verdict"] != rf[f]["ref_verdict"]:
                out["mismatches"].append(f"g2 {tag} {f}: {r} vs {rf[f]['ref_r_F']}")
        out["g2"][tag] = rf
    # ---- counts
    fac = [json.loads(l) for l in (ROOT / "data/factorial_set.jsonl").read_text().splitlines() if l.strip()]
    cnt = defaultdict(int)
    for r in fac:
        cnt[r["cell"]] += 1
    frz = json.loads((ROOT / "data/frame_freeze.json").read_text())["counts"]
    out["counts"]["factorial_cells"] = dict(cnt)
    for c, n in frz.items():
        if cnt.get(c) != n:
            out["mismatches"].append(f"count {c}: {cnt.get(c)} vs freeze {n}")
    progs = [json.loads(l) for l in (ROOT / "data/programs_v10.jsonl").read_text().splitlines() if l.strip()]
    uids = {r["uid"] for r in progs}
    missing = [r["uid"] for r in fac if r["uid"] not in uids]
    out["counts"]["factorial_uids_missing_from_programs_v10"] = missing
    if missing:
        out["mismatches"].append(f"{len(missing)} frozen uids missing from programs_v10.jsonl")
    out["n_mismatches"] = len(out["mismatches"])
    (ROOT / "results/rederive.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({"n_mismatches": out["n_mismatches"], "g1": {t: {k: v for k, v in r.items()
                                                                       if k.startswith(("rho", "delta"))}
                                                                   for t, r in out["g1"].items()}}, indent=1))


if __name__ == "__main__":
    main()
