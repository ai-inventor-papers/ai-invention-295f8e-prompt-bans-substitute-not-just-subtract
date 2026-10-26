#!/usr/bin/env python3
"""S1.6 ENGINE CHECK (positive control, not decisive): this artifact's rows for T03 RAND9002 alpha 1 and T2 RAND9004
alpha 1 (exp17 key convention u_stream(task, w, k), k 0-9 x W1-W5, exp17 FP8 ban norms) and the twins, against the
iteration-3 screen rows on the same slots: compositions, per-slot label and code-hash agreement, pass rates, and
JS(this, screen) against a template-resampling null (2,000 bootstrap resamples of the screen arm's five 10-slot
template blocks). Outside the null's q95 -> 'precision sensitivity of the screen effect'. -> results/engine_check.json
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
from common import dist, js  # noqa: E402


def main() -> None:
    mine = [json.loads(l) for l in open(ROOT / "data/labels.jsonl")]
    e17 = [json.loads(l) for l in open(ROOT / "inputs/exp17/data/labels.jsonl")]
    out = {}
    rng = np.random.default_rng(0)
    for t, a17, a in (("T03", "RAND9002_a1.0", "SCR_d9002_a1.0"), ("T03", "NEUTRAL", "TWIN"),
                      ("T2", "RAND9004_a1.0", "SCR_d9004_a1.0"), ("T2", "NEUTRAL", "TWIN")):
        A = {(r["template"], int(r["sample_id"])): r for r in mine if r["task"] == t and r["arm"] == a
             and int(r["sample_id"]) < 10}
        Bm = {(r["template"], int(r["sample_id"])): r for r in e17 if r["task"] == t and r["arm"] == a17
              and int(r["sample_id"]) < 10}
        keys = sorted(set(A) & set(Bm))
        la = [A[k]["label"] for k in keys]
        lb = [Bm[k]["label"] for k in keys]
        obs = js(dist(la), dist(lb))
        blocks = {w: [Bm[k]["label"] for k in keys if k[0] == w] for w in {k[0] for k in keys}}
        null = []
        ws = sorted(blocks)
        for _ in range(2000):
            pick = rng.choice(ws, len(ws))
            null.append(js(dist(lb), dist([x for w in pick for x in blocks[w]])))
        q95 = float(np.quantile(null, 0.95))
        out[f"{t}|{a}"] = {"n_slots": len(keys), "composition": dict(Counter(la)), "screen_composition": dict(Counter(lb)),
                           "per_slot_label_agreement": sum(x == y for x, y in zip(la, lb)) / max(len(keys), 1),
                           "per_slot_code_sha_agreement": sum(A[k].get("code_sha256") == Bm[k].get("code_sha256")
                                                              for k in keys) / max(len(keys), 1),
                           "pass": sum(A[k]["passed"] for k in keys) / max(len(keys), 1),
                           "screen_pass": sum(Bm[k]["passed"] for k in keys) / max(len(keys), 1),
                           "JS": obs, "null_q95": q95,
                           "reading": "reproduced" if obs <= q95 else "precision sensitivity of the screen effect"}
    (ROOT / "results/engine_check.json").write_text(json.dumps(out, indent=1))
    print({k: (v["per_slot_code_sha_agreement"], v["JS"], v["reading"]) for k, v in out.items()})


if __name__ == "__main__":
    main()
