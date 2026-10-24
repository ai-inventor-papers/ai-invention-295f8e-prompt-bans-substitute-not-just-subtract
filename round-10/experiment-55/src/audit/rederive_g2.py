#!/usr/bin/env python3
"""Second stdlib-only audit (separate code path from src/g2.py and src/analysis.py): from the raw per-program class
distances (results/geo_class_dist_<model>.csv, frame 'full') recompute the G2 headline shares and contrasts, and run
the same statistics on placebo inputs (other families; random family labels). Also a stdlib G1 placebo: discipline
labels shuffled across programs (data/factorial_set.jsonl order = pairs_<model>.csv indices) must give rho_dc ~ 0.
Writes results/rederive_g2.json."""

import csv
import json
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANNED_DISC = ("BFSO", "DFSO", "HEUR")
BANNED_ALG = ("bfs", "dfs", "iddfs", "astar", "gbfs")
ALG_DISC = {"bfs": "BFSO", "bibfs": "BFSO", "dfs": "DFSO", "iddfs": "DFSO", "astar": "HEUR", "gbfs": "HEUR",
            "jps": "HEUR", "biastar": "HEUR", "idastar": "HEUR", "dijkstra_unit": "COST"}


def disc(c):
    return c.split("-")[0] if "-" in c else ALG_DISC.get(c, "OTHER")


def load(tag):
    d = defaultdict(dict)
    fam = {}
    with (ROOT / f"results/geo_class_dist_{tag}.csv").open() as fh:
        for row in csv.DictReader(fh):
            if row["frame"] == "full":
                d[row["uid"]][row["class"]] = float(row["d"])
                fam[row["uid"]] = row["family"]
    return d, fam


def nearest(dd):
    return min(dd, key=dd.get)


def share(uids, pred):
    return sum(1 for u in uids if pred(u)) / len(uids) if uids else None


def contrast(dd, a, b):
    return min(dd[c] for c in a) < min(dd[c] for c in b)


def g1_placebo(tag, seed=7):
    """stdlib partial Spearman with discipline labels shuffled across programs (expects ~0)."""
    from rederive import partial
    rows = [json.loads(l) for l in (ROOT / "data/factorial_set.jsonl").read_text().splitlines() if l.strip()]
    disc_lab = [r["discipline"] for r in rows]
    random.Random(seed).shuffle(disc_lab)
    DS, DD, DC = [], [], []
    with (ROOT / f"results/pairs_{tag}.csv").open() as fh:
        for row in csv.DictReader(fh):
            i, j = int(row["i"]), int(row["j"])
            a, b = disc_lab[i], disc_lab[j]
            DS.append(float(row["D_S"]))
            DD.append(0.0 if a == b else (0.5 if {a, b} == {"BFSO", "COST"} else 1.0))
            DC.append(float(row["D_cont"]))
    return partial(DS, DD, DC)


def main():
    import sys
    sys.path.insert(0, str(ROOT / "audit"))
    out = {}
    for tag in ("8b", "32b"):
        p = ROOT / f"results/geo_class_dist_{tag}.csv"
        if not p.exists():
            continue
        d, fam = load(tag)
        by = defaultdict(list)
        for u, f in fam.items():
            by[f].append(u)
        rec = {"n_per_family": {f: len(v) for f, v in by.items()}}
        rec["share_nearest_banned"] = {f: share(v, lambda u: disc(nearest(d[u])) in BANNED_DISC or
                                                nearest(d[u]) in BANNED_ALG) for f, v in by.items()}
        rec["share_nearest_RELAX"] = {f: share(v, lambda u: disc(nearest(d[u])) == "RELAX") for f, v in by.items()}
        rec["share_nearest_BFSO_or_COST"] = {f: share(v, lambda u: disc(nearest(d[u])) in ("BFSO", "COST"))
                                             for f, v in by.items()}
        rec["contrast_heapBFSO/COST_vs_HEUR-HEAP"] = {f: share(v, lambda u: contrast(
            d[u], ("BFSO-HEAP", "COST-HEAP"), ("HEUR-HEAP",))) for f, v in by.items()}
        rec["contrast_RELAX-GRID2D_vs_BFSO/COST-GRID2D"] = {f: share(v, lambda u: contrast(
            d[u], ("RELAX-GRID2D",), ("BFSO-GRID2D", "COST-GRID2D"))) for f, v in by.items()}
        # placebo: random families of the same sizes as F-UD / F-BF / F-COV drawn from all placed programs
        rng = random.Random(11)
        allu = list(fam)
        plc = {}
        for f, stat in (("F-UD", lambda u: contrast(d[u], ("BFSO-HEAP", "COST-HEAP"), ("HEUR-HEAP",))),
                        ("F-BF", lambda u: disc(nearest(d[u])) == "RELAX"),
                        ("F-COV", lambda u: disc(nearest(d[u])) in BANNED_DISC or nearest(d[u]) in BANNED_ALG)):
            vals = []
            for _ in range(500):
                pick = rng.sample(allu, len(by[f]))
                vals.append(share(pick, stat))
            vals.sort()
            plc[f] = {"observed": share(by[f], stat), "placebo_median": vals[250],
                      "placebo_q95": vals[475], "placebo_share_ge_observed": sum(v >= share(by[f], stat)
                                                                                  for v in vals) / 500}
        rec["placebo_random_family"] = plc
        rec["g1_placebo_discipline_shuffled_rho_dc_stdlib"] = g1_placebo(tag)
        out[tag] = rec
    (ROOT / "results/rederive_g2.json").write_text(json.dumps(out, indent=1))
    for tag, r in out.items():
        print(tag, "P-COV share", round(r["share_nearest_banned"].get("F-COV") or -1, 4),
              "| F-BF nearest RELAX", round(r["share_nearest_RELAX"].get("F-BF") or -1, 4),
              "| F-UD contrast", round(r["contrast_heapBFSO/COST_vs_HEUR-HEAP"].get("F-UD") or -1, 4),
              "| placebo", json.dumps(r["placebo_random_family"]),
              "| G1 placebo rho_dc", round(r["g1_placebo_discipline_shuffled_rho_dc_stdlib"], 4))
        print("   contrast by family", {f: round(v, 2) for f, v in r["contrast_heapBFSO/COST_vs_HEUR-HEAP"].items()})


if __name__ == "__main__":
    main()
