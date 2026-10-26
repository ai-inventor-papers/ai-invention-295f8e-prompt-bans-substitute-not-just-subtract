#!/usr/bin/env python3
"""Smoke test of the S9 analysis functions on synthetic rows that carry every field the real rows carry."""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "analysis"))
import analysis as an  # noqa: E402
from cfg import DEFAULT  # noqa: E402

rng = np.random.default_rng(5)
tasks = ["T03", "T04", "T06", "T05"]
alt = {"T03": "quickselect", "T04": "kmp", "T06": "sort_adjacent", "T05": "sort_two_pointers"}
true = {"a": 0.1, "b": 0.95, "c": 0.3, "d": 0.9, "K0": 0.5, "V1": 0.6, "BAN+SIG": 0.5, "TWIN+SIG": 0.97,
        "BAN+NEU": 0.2, "TWIN+NEU": 0.95}
rows = []
for t in tasks:
    for w in ["W1", "W2", "W3", "W4", "W5"]:
        for k in range(20):
            base = list(rng.integers(0, 1000, 30))
            for a, s in true.items():
                lab = DEFAULT[t] if rng.random() < s else (alt[t] if rng.random() < 0.8 else "other")
                ids = base if a in ("b", "d") and lab == DEFAULT[t] else base[:5] + list(rng.integers(0, 1000, 25))
                rows.append({"uid": f"{t}|{a}|{w}|{k}", "task": t, "template": w, "k": k, "arm": a, "label": lab,
                             "passed": bool(rng.random() < 0.9), "token_ids": ids, "stage": "S6",
                             "veto_fired": a == "V1", "gen_text": "```python\ndef solve(): pass\n```"})
gated = tasks
shares = an.shares_table(rows)
route = an.route_analysis(rows, gated)
print("route", route["verdict"], {k: round(v, 3) for k, v in route["point"].items()},
      {k: [round(x, 3) for x in v["percentile"]] for k, v in route["intervals"].items()})
print("verdicts", route["verdict_by_interval"], "glm", {k: route["mixed_glm"].get(k) for k in ("F_prompt_glm", "F_direct_glm", "error")})
crn = an.crn_analysis(rows, tasks)
print("crn", list(crn["T03"]["flip_tables"].keys()), crn["T03"]["first_divergence"].get("a", {}).get("median"))
land = an.landing_by_route(rows, tasks)
print("landing", {X: (v.get("modal"), round(v.get("JS_vs_a", 0), 3), v.get("within_null")) for X, v in land["T03"].items() if X != "a"})
c2c = {t: {"V": float(v), "class": c, "fire_rate": 0.9, "V_fired": 0.5} for t, v, c in
       zip(tasks, [0.9, 0.3, 0.6, 0.85], ["LOW_DIRECT", "HIGH_DIRECT", "NONE", "LOW_DIRECT"])}
print("c2c", {k: v for k, v in an.c2c_analysis(route, gated, c2c).items() if k != "rows"})
print("c2b", an.c2b_analysis(rows, gated, c2c)["n_hold"])
print("prefill", {t: {k: round(v["P_open"], 3) for k, v in x.items()} for t, x in an.prefill_analysis(shares, gated, rows).items()})
print("OK")
