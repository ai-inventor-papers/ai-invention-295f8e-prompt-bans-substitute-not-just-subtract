#!/usr/bin/env python3
"""(G2) Inventory of every iteration-1 input this audit reads: size, sha256, UTC mtime, row count and the distinct
values of task / condition / arm / label. A missing input marks only its own entry 'input_missing'."""
from __future__ import annotations

import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from loguru import logger

from common import EXP, RES, clean, jdump, setup_logging, sha256_file

INPUTS = {
    "exp1": ["data/samples.jsonl", "results/contest.json", "results/event_table.json", "results/s1_sham_control.json",
             "results/landing_table.json", "results/disguised_recurrence.json", "results/mention_effects.json",
             "results/t9_family_test.json", "commitments.log", "predictions/t1_single_bans.json",
             "predictions/t2_single_bans.json", "predictions/t1_succ_step2.json", "predictions/t2_succ_step2.json"],
    "exp2": ["cache/hR_index.jsonl"] + [f"cache/hR_layer{l}.npy" for l in range(8, 29)] +
            ["analysis/geometry.py", "analysis/audit_rederive.py", "results/geometry_b.json",
             "results/manipulation_sensitivity.json", "results/manifold.json", "results/deviations.json",
             "results/contest.json", "results/buy.json", "results/phaseC_events.json", "results/c2_removal.json",
             "results/c3_decomposition.json", "data/samples_phaseA.jsonl", "data/samples_phaseC.jsonl",
             "data/samples_phaseD.jsonl", "predictions/predictions_v1.json", "predictions/commit_log.jsonl"],
    "exp3": [f"states/T{t}_part_{i:03d}.npz" for t in (1, 2) for i in range(1, 6)] +
            ["states/T1_meta.json", "states/T2_meta.json", "analysis/states.py", "generations/pools.jsonl",
             "generations/knob.jsonl", "prereg.json", "logs/states.out", "probes.json", "summaries/next_token.json",
             "summaries/t6_sensitivity.json", "forks.json", "logs/test_engine.json", "knob_table.json"],
    "exp4": ["data/samples.jsonl", "results/buy_table.json", "results/predict_row.json", "results/preregistration.json",
             "results/protocol.json", "results/condition_summaries.json", "results/flips.json",
             "results/dose_response.json", "results/succession_plan.json", "forecast/predict_T1_ban1.json",
             "forecast/predict_T2_ban1.json", "forecast/predict_T1_succ2.json", "forecast/predict_T2_succ2.json",
             "logs/hardware.json"],
    "exp5": ["runs/samples.jsonl", "full_method_out.json", "results/manipulation_R.json", "results/manipulation_S.json",
             "time_log.json", "predictions/predict_modal_ban.json"],
    "exp6": ["results/samples.jsonl", "results/analysis.json", "results/probe_curves.json",
             "forecast/predictions_screen.json"],
}


def describe(exp: str, rel: str) -> dict:
    p = EXP[exp] / rel
    if not p.exists():
        return {"file": f"{exp}/{rel}", "status": "input_missing"}
    st = p.stat()
    d = {"file": f"{exp}/{rel}", "status": "ok", "bytes": st.st_size, "sha256": sha256_file(p),
         "mtime_utc": pd.Timestamp(st.st_mtime, unit="s", tz="UTC").isoformat()}
    if rel.endswith(".jsonl"):
        vals = {k: Counter() for k in ("task", "condition", "arm", "label")}
        n = 0
        with p.open() as fh:
            for line in fh:
                if not line.strip():
                    continue
                r = json.loads(line)
                n += 1
                for k in vals:
                    if k in r:
                        vals[k][str(r[k])] += 1
        d["rows"] = n
        d["distinct"] = {k: dict(v) for k, v in vals.items() if v}
    elif rel.endswith(".json"):
        try:
            obj = json.loads(p.read_text())
            d["rows"] = len(obj) if isinstance(obj, (list, dict)) else 1
        except json.JSONDecodeError:
            d["rows"] = None
    return d


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("inventory")
    jobs = [(e, r) for e, rels in INPUTS.items() for r in rels]
    with ThreadPoolExecutor(max_workers=6) as ex:
        out = list(ex.map(lambda a: describe(*a), jobs))
    miss = [o["file"] for o in out if o["status"] != "ok"]
    jdump(clean({"files": out, "n_files": len(out), "missing": miss}), RES / "inventory.json")
    (RES.parent / "inventory.json").write_text((RES / "inventory.json").read_text())
    logger.info(f"inventory: {len(out)} files, {len(miss)} missing: {miss}")


if __name__ == "__main__":
    main()
