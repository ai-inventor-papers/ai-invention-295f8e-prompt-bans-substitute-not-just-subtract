#!/usr/bin/env python3
"""Engine check (positive control, not decisive): this artifact's engine (L4, bf16) vs exp23's rows (RTX 2000 Ada,
bf16) on exp23's own slot keys, direction 9003 and 640-token cap. Per-slot label agreement, JS divergence of the twin
compositions against a template-resampling null (1,000 draws) and reproduction of the iteration-4 T1 esc9003 alpha-1
shift (off-default share within 0.15). PASS gates Stage 1."""

from __future__ import annotations

import collections
import sys
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import DATA_DIR, E23, RESULTS_DIR, TEMPLATE_IDS, read_jsonl, setup_logging, write_json
from analysis_E import js_divergence


def comp(rows: list[dict[str, Any]]) -> dict[str, float]:
    c = collections.Counter(r["label"] for r in rows if r["label"] not in ("invalid", "disputed"))
    return {k: float(v) for k, v in c.items()}


def null_js(rows_a: list[dict[str, Any]], rows_b: list[dict[str, Any]], n: int = 1000, seed: int = 0) -> np.ndarray:
    """Template-resampling null: pool both engines' rows; each draw builds two pseudo-samples by resampling the 5
    templates with replacement (all rows of a drawn template) and returns their JS divergence."""
    rng = np.random.default_rng(seed)
    pool = rows_a + rows_b
    by_t = collections.defaultdict(list)
    for r in pool:
        by_t[r["template"]].append(r)
    ts = sorted(by_t)
    out = []
    for _ in range(n):
        A = [r for t in rng.choice(ts, len(ts)) for r in rng.choice(by_t[t], len(by_t[t]) // 2, replace=False)]
        B = [r for t in rng.choice(ts, len(ts)) for r in rng.choice(by_t[t], len(by_t[t]) // 2, replace=False)]
        out.append(js_divergence(comp(A), comp(B)))
    return np.array(out)


def main() -> None:
    setup_logging("engine_check_eval")
    ours = [r for r in read_jsonl(DATA_DIR / "labels.jsonl") if r.get("stage") == "engine_check"]
    e23 = [r for r in read_jsonl(E23 / "data" / "samples.jsonl") if r["task"] in ("T1", "T2")
           and r.get("stage") in ("A", "B") and r["arm"] in ("twin", "esc9003_a1")]
    key23 = {(r["task"], r["arm"], r["template"], int(r["slot"])): r for r in e23}
    res: dict[str, Any] = {}
    for task, arm23, arm in (("T1", "twin", "e23_twin"), ("T1", "esc9003_a1", "e23_esc9003_a1"), ("T2", "twin", "e23_twin")):
        mine = [r for r in ours if r["task"] == task and r["arm"] == arm]
        theirs = [key23[(task, arm23, r["template"], int(r["slot"]))] for r in mine
                  if (task, arm23, r["template"], int(r["slot"])) in key23]
        pairs = [(r, key23[(task, arm23, r["template"], int(r["slot"]))]) for r in mine
                 if (task, arm23, r["template"], int(r["slot"])) in key23]
        agree = sum(1 for a, b in pairs if a["label"] == b["label"]) / max(len(pairs), 1)
        tok_same = None
        D = "dfs" if task == "T1" else "dijkstra"
        off_m = sum(1 for r in mine if r["label"] not in (D, "invalid", "disputed")) / max(len(mine), 1)
        off_t = sum(1 for r in theirs if r["label"] not in (D, "invalid", "disputed")) / max(len(theirs), 1)
        js = js_divergence(comp(mine), comp(theirs))
        nul = null_js(mine, theirs) if arm == "e23_twin" else None
        res[f"{task}_{arm23}"] = {"n_ours": len(mine), "n_exp23_matched": len(pairs), "per_slot_label_agreement": agree,
                                  "composition_ours": comp(mine), "composition_exp23": comp(theirs),
                                  "off_default_share_ours": off_m, "off_default_share_exp23": off_t,
                                  "pass_ours": float(np.mean([bool(r.get("passed")) for r in mine])) if mine else None,
                                  "pass_exp23": float(np.mean([bool(r.get("passed")) for r in theirs])) if theirs else None,
                                  "js": js, "null_js_p95": float(np.nanpercentile(nul, 95)) if nul is not None else None,
                                  "null_js_mean": float(np.nanmean(nul)) if nul is not None else None,
                                  "token_identical_slots": tok_same}
    esc = res["T1_esc9003_a1"]
    crit_esc = abs(esc["off_default_share_ours"] - esc["off_default_share_exp23"]) <= 0.15
    crit_js = all((v["js"] <= v["null_js_p95"] + 1e-12) for k, v in res.items() if v["null_js_p95"] is not None)
    res["criteria"] = {"esc9003_shift_reproduced_within_0.15": crit_esc, "twin_js_within_null_p95": crit_js}
    res["PASS"] = bool(crit_esc and crit_js)
    res["note"] = ("exp23 rows were generated in mixed-arm batches of B = 36 on an RTX 2000 Ada; here single-prompt "
                   "batches of B = 16 (T1) / 10 (T2) on an L4: not byte-identical by design")
    write_json(RESULTS_DIR / "engine_check.json", res)
    logger.info(f"engine check PASS={res['PASS']} criteria={res['criteria']}")
    for k, v in res.items():
        if isinstance(v, dict) and "js" in v:
            logger.info(f"{k}: agree {v['per_slot_label_agreement']:.2f} off {v['off_default_share_ours']:.2f} vs "
                        f"{v['off_default_share_exp23']:.2f}; JS {v['js']:.3f} (null p95 {v['null_js_p95']}) "
                        f"ours {v['composition_ours']} exp23 {v['composition_exp23']}")


if __name__ == "__main__":
    main()
