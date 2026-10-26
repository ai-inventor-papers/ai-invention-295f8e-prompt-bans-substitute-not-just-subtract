#!/usr/bin/env python3
"""S-9: run the independent stdlib re-derivation (audit/rederive.py, isolated interpreter) and record its result."""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

from loguru import logger

from io_util import ROOT, save_stage


def run() -> dict[str, Any]:
    r = subprocess.run([sys.executable, "-I", str(ROOT / "audit" / "rederive.py")], capture_output=True, text=True,
                       timeout=3000)
    logger.info(r.stdout[-2000:])
    if r.returncode != 0:
        logger.error(r.stderr[-4000:])
        raise RuntimeError(f"audit/rederive.py exited {r.returncode}")
    a = json.loads((ROOT / "audit" / "rederive.json").read_text())
    pb = a["placebos"]
    metrics = {"n_checks": a["n_checks"], "n_mismatches": a["n_mismatches"],
               "placebos_failing_as_required": a["placebos_failing_as_required"], "n_placebos": a["n_placebos"],
               "P1_share_differs": pb["P1_family_shuffle"]["share_differs"],
               "P2_share_broken": pb["P2_placement_shuffle"]["share_broken"],
               "P3_mean_pooled_gap": pb["P3_swap_placebo"]["mean_pooled_gap"],
               "P6_mismatches_on_planted_copy": pb["P6_planted_value"]["mismatches_on_planted_copy"]}
    ex = [{"input": f"placebo {k}", "output": json.dumps({kk: vv for kk, vv in v.items() if kk != "example"}),
           "metadata_placebo": k, "eval_fails_as_required": float(bool(v["fails_as_required"]))} for k, v in pb.items()]
    save_stage("s9_audit", {"status": "DONE" if a["n_mismatches"] == 0 else "MISMATCHES", "audit": {
        k: v for k, v in a.items() if k in ("n_checks", "n_mismatches", "mismatches", "placebos",
                                            "placebos_failing_as_required", "mc_draws_10_classes")},
        "metrics": metrics, "examples": {"audit_placebos": ex}})
    return a
