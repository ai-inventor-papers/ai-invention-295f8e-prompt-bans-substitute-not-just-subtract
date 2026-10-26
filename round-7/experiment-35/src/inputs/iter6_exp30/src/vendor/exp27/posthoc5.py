#!/usr/bin/env python3
"""Post hoc (amendment A4, logged): the iteration-1 base compositions (exp5) use an older label vocabulary than the
exp8-suite labeller (bellman_ford_spfa / floyd_warshall / astar_greedy / dijkstra_unit vs bf_spfa / floyd / astar_gbfs
/ dijkstra), so the committed 'landing mass outside base support' counts name mismatches as new support. This file
recomputes it after harmonising the base names -> results/landings_harmonised.json."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import RESULTS_DIR, append_deviation, read_json, write_json

MAP = {"bellman_ford_spfa": "bf_spfa", "floyd_warshall": "floyd", "astar_greedy": "astar_gbfs", "dijkstra_unit": "dijkstra"}
land = read_json(RESULTS_DIR / "landings.json")
base = {t: {} for t in ("T1", "T2")}
for t, comp in land["base_compositions_iter1"].items():
    for k, v in comp.items():
        kk = "other" if k.startswith("other") else MAP.get(k, k)
        base[t][kk] = base[t].get(kk, 0) + v
out = {"base_harmonised": base, "mapping": MAP, "moves": {}}
for key, v in land["moves"].items():
    t = key.split("|")[0]
    if t in ("T1", "T2") and v.get("moves"):
        ls = v["landing_set"]
        sup = set(base[t])
        outside = sum(n for k, n in ls.items() if k not in sup)
        out["moves"][key] = {"landing_set": ls, "outside_base_support_harmonised": outside / max(sum(ls.values()), 1),
                             "outside_labels": sorted(k for k in ls if k not in sup),
                             "committed_value_unharmonised": v.get("landing_mass_outside_base_support")}
write_json(RESULTS_DIR / "landings_harmonised.json", out)
append_deviation("A4-landing-vocab", "post hoc: base compositions of iteration 1 use an older label vocabulary; "
                 "results/landings_harmonised.json recomputes the landing mass outside base support after mapping "
                 f"{MAP}; the committed (unharmonised) value is kept beside it")
print(json.dumps(out["moves"], indent=1))
