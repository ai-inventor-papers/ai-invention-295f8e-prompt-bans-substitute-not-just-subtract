#!/usr/bin/env python3
"""Placebo of the FULL committed C1 rule (counts AND the bootstrap CI) under exchangeable arm labels.

This artifact's arms (TWIN, PN x 4, T1.3, T1.6, TOPK10, NONCE, NOVELTY, SEMSEED) have their rows shuffled across arm
labels within each E6 task (100 shuffles, seed 0); the reused veto rows stay as they are (they belong to the NA set
of the rule). For every shuffle the committed analysis code prices each class (point estimates); where the counts part
fires (count1 >= 3 AND count2 >= 4) the class bootstrap (200 replicates, stratified) and the committed c1_decide give
the full verdict. The rule passes the placebo if CONFIRMED appears in fewer than 5 of 100 shuffles.

Usage (from this folder): .venv/bin/python audit/placebo_full_rule.py   -> results/placebo_full_rule.json
"""

from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from analysis.core import NA_PRIMARY, TaskData, c1_decide, class_price, run_bootstrap  # noqa: E402
from analysis.hull import fixed_uniforms  # noqa: E402
from analysis.run_all import load_other_map, task_rows  # noqa: E402
from cfg import DATA_DIR, RESULTS_DIR, read_jsonl, utc_now, write_json  # noqa: E402

E6 = ("T03", "T05", "T06", "T10", "T1", "T2")
MINE = ["TWIN", "PN_a0.5", "PN_a1", "PN_a2", "PN_a4", "T1.3", "T1.6", "TOPK10", "NONCE", "NOVELTY", "SEMSEED"]
CLASSES = ["PN"] + NA_PRIMARY


def main() -> None:
    samples = read_jsonl(DATA_DIR / "samples.jsonl")
    reused = read_jsonl(DATA_DIR / "reused_rows.jsonl")
    omap = load_other_map()
    U = fixed_uniforms(300)
    by = defaultdict(lambda: defaultdict(list))
    for r in samples:
        by[r["task"]][r["arm"]].append(r)
    rng = random.Random(0)
    out = {"n_shuffles": 100, "shuffles": [], "utc": utc_now()}
    n_conf = 0
    for s in range(100):
        tds, point = {}, {}
        for t in E6:
            arms = [a for a in MINE if by[t].get(a)]
            pool = [r for a in arms for r in by[t][a]]
            rng.shuffle(pool)
            rows, pos = [], 0
            for a in arms:
                n = len(by[t][a])
                rows += [dict(r, arm=a) for r in pool[pos:pos + n]]
                pos += n
            # keep every other arm of the task (sensitivity arms, reused rows) unchanged
            rows += [r for r in samples if r["task"] == t and r["arm"] not in arms]
            td = TaskData(t, task_rows(rows, reused, t), omap)
            tds[t] = td
            point[t] = {}
            for c in CLASSES:
                p = class_price(td, c, U, refine=False, with_price=False)
                point[t][c] = p["H5"] if p else None
        c1c = c2c = 0
        for t in E6:
            pn = point[t].get("PN")
            best = max([v for c, v in point[t].items() if c != "PN" and v is not None], default=None)
            if pn is None or best is None:
                continue
            c1c += pn >= 1.5
            c2c += pn > best
        rec = {"shuffle": s, "count1": c1c, "count2": c2c, "counts_fire": bool(c1c >= 3 and c2c >= 4)}
        if rec["counts_fire"]:
            boot = run_bootstrap(tds, CLASSES, 200, 777 + s, workers=6)
            d = c1_decide(point, boot, E6, NA_PRIMARY, 2000, 888 + s)
            rec.update({"verdict": d["verdict"], "D_bar": d["D_bar"], "D_bar_ci95": d["D_bar_ci95"]})
            n_conf += d["verdict"] == "CONFIRMED"
        out["shuffles"].append(rec)
        print(s, rec, flush=True)
    out["n_counts_fire"] = sum(r["counts_fire"] for r in out["shuffles"])
    out["n_confirmed"] = n_conf
    out["pass"] = n_conf < 5
    write_json(RESULTS_DIR / "placebo_full_rule.json", out)
    print(json.dumps({k: v for k, v in out.items() if k != "shuffles"}))


if __name__ == "__main__":
    main()
