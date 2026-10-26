#!/usr/bin/env python3
"""S-9b: run the second independent spot-check (audit/spotcheck.py, isolated interpreter) and record its result."""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

from loguru import logger

from io_util import ROOT, save_stage


def run() -> dict[str, Any]:
    r = subprocess.run([sys.executable, "-I", str(ROOT / "audit" / "spotcheck.py")], capture_output=True, text=True,
                       timeout=600)
    logger.info(r.stdout[-2000:])
    if r.returncode != 0:
        logger.error(r.stderr[-4000:])
        raise RuntimeError(f"audit/spotcheck.py exited {r.returncode}")
    a = json.loads((ROOT / "audit" / "spotcheck.json").read_text())
    pb, pg = a["placebo"], a["placebo_pooled_gap"]
    metrics = {"n_checks": a["n_checks"], "n_mismatches": a["n_mismatches"], "placebo_observed_p": pb["observed_p"],
               "placebo_share_p_below_0_05": pb["share_placebo_p_below_0.05"], "placebo_median_p": pb["median_placebo_p"],
               "pooled_gap_placebo_mean": pg["mean_placebo"], "pooled_gap_placebo_max_abs": pg["max_abs_placebo"],
               "pooled_gap_placebo_share_ge_observed": pg["share_placebo_ge_observed"]}
    ex = [{"input": f"spot-check {c['metric']}",
           "output": json.dumps({"spotcheck": c["spotcheck"], "pipeline": c["pipeline"]}),
           "predict_pipeline": json.dumps(c["pipeline"]), "predict_spotcheck": json.dumps(c["spotcheck"]),
           "metadata_compared_against": a["compared_against"], "eval_match": float(c["match"])} for c in a["checks"]]
    save_stage("s9b_spotcheck", {"status": "DONE" if a["n_mismatches"] == 0 else "MISMATCHES",
                                 "spotcheck": {k: v for k, v in a.items() if k != "checks"}, "metrics": metrics,
                                 "examples": {"spotcheck_rows": ex}})
    return a
