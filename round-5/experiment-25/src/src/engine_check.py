#!/usr/bin/env python3
"""Engine check (P0): this run's bf16 rows of the iteration-4 engine-check cells (T03 twin + rand_9002 at alpha 1,
T2 twin + rand_9004 at alpha 1, exp17 ban unit, same CRN keys) against exp19's FP8 W8A8 rows (= the screen's).
Reported: compositions, pass rates, per-slot label agreement and Jensen-Shannon divergence against a
template-resampling null (resample the 5 templates' rows within the FP8 cell, 1,000 draws, JSD of each resample
with the cell itself; p95). Under bf16 a difference is precision sensitivity, never hidden."""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg5 import E19, LAB_DIR, RESULTS, read_jsonl, utc_now, write_json  # noqa: E402
from metrics import js_divergence  # noqa: E402

ARM_MAP = {"ECTWIN": "NEUTRAL", "ECBAN_d9002_a1.0": "RAND9002_a1.0", "ECBAN_d9004_a1.0": "RAND9004_a1.0"}


def main() -> None:
    mine = read_jsonl(LAB_DIR / "enginecheck.jsonl") + read_jsonl(LAB_DIR / "enginecheck_T2twin.jsonl")
    ref = read_jsonl(E19 / "data" / "engine_check_labels.jsonl")
    rng = np.random.default_rng(7)
    out = {"utc": utc_now(), "engine": "bf16 HF (this run) vs FP8 W8A8 (exp19 = screen)", "cells": {}}
    for task in ("T03", "T2"):
        for arm, rarm in ARM_MAP.items():
            a = {(r["template"], int(r["slot"])): r for r in mine if r["task"] == task and r["arm"] == arm}
            b = {(r["template"], int(r["slot"])): r for r in ref if r["task"] == task and r["arm"] == rarm}
            if not a or not b:
                continue
            keys = sorted(set(a) & set(b))
            ca = Counter(a[k]["label"] for k in keys)
            cb = Counter(b[k]["label"] for k in keys)
            agree = sum(a[k]["label"] == b[k]["label"] for k in keys) / len(keys)
            same_tokens = sum(a[k].get("code_sha256") == b[k].get("code_sha256") for k in keys) / len(keys)
            jsd = js_divergence(dict(ca), dict(cb))
            # template-resampling null on the FP8 cell
            by_w = {}
            for k in keys:
                by_w.setdefault(k[0], []).append(b[k]["label"])
            ws = sorted(by_w)
            null = []
            for _ in range(1000):
                pick = rng.choice(len(ws), len(ws), replace=True)
                labs = [l for i in pick for l in by_w[ws[i]]]
                null.append(js_divergence(dict(Counter(labs)), dict(cb)))
            p95 = float(np.percentile(null, 95))
            out["cells"][f"{task}|{arm}"] = {
                "n": len(keys), "this_run_composition": dict(ca), "screen_composition": dict(cb),
                "this_run_pass": sum(bool(a[k].get("passed")) for k in keys) / len(keys),
                "screen_pass": sum(bool(b[k].get("passed")) for k in keys) / len(keys),
                "per_slot_label_agreement": agree, "identical_code_share": same_tokens, "JSD": jsd,
                "null_p95": p95, "JSD_within_null": bool(jsd <= p95 + 1e-12)}
    out["verdict"] = ("REPRODUCED within the resampling null" if out["cells"] and
                      all(v["JSD_within_null"] for v in out["cells"].values()) else
                      "PRECISION SENSITIVITY: at least one cell outside the template-resampling null")
    write_json(RESULTS / "engine_check.json", out)
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk in ("per_slot_label_agreement", "JSD", "null_p95",
                                                                     "this_run_composition", "screen_composition")}
                      for k, v in out["cells"].items()}, indent=1))
    print(out["verdict"])


if __name__ == "__main__":
    main()
