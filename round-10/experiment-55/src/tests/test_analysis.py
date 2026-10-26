#!/usr/bin/env python3
"""T7 (G1 code on synthetic data with the real cell layout) and T8 (placement code) -> results/analysis_unit_tests.json."""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import cells  # noqa: E402
import g1  # noqa: E402
import g2  # noqa: E402

t0 = time.time()
disc, cont = [], []
for c in cells.all_cells():
    d, k = c.split("-")
    for _ in range(4):
        disc.append(d)
        cont.append(k)
res = {"layout": "24 committed cells x 4 synthetic programs", "T7": g1.t7(disc, cont, n_null=200), "T8": g2.t8()}
res["pass"] = res["T7"]["pass"] and res["T8"]["pass"]
res["seconds"] = round(time.time() - t0, 1)
(ROOT / "results/analysis_unit_tests.json").write_text(json.dumps(res, indent=1, default=str))
print(json.dumps({k: v for k, v in res["T7"].items()}, indent=1, default=str)[:2500])
print("T8", res["T8"], "PASS" if res["pass"] else "FAIL", res["seconds"], "s")
