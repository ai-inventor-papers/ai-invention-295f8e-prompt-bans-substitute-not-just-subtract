#!/usr/bin/env python3
"""Committed cluster ratios of the bin-packing replication (art_dq4MiqNM89Go) under each stored sensitivity.

Reviewer check for Section 10.4. Reads results/analysis_clusters.json (per_arm_seed) and recomputes, per seed and
pooled over seeds 2 and 3, branching's cluster ratio to temperature 1.0, temperature 1.6 and the placebo for the
primary count and for every sensitivity count the artifact stored (stochastic programs excluded, clusters with
F < 1, informative probe states, rescored programs, error-5 exclusion, rarefied counts).

Usage: python checks/replication_sensitivities.py --exp-dir <gen_art_experiment_52 dir> --out results/x.json
"""

import argparse
import json
import sys
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent.parent
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(ROOT / "logs" / "replication_sensitivities.log", rotation="30 MB", level="DEBUG")

SEEDS = ["S2", "S3"]
ARMS = ["T1.0", "T1.6", "DTB", "RPB", "IDEA"]
COUNTS = ["clusters", "sens_excl_stochastic", "clusters_F_below_1", "sens_informative", "sens_fs_rescored",
          "sens_excl_err5", "rarefied_mean"]


def count(row: dict, key: str) -> float:
    return float(row["rarefied_clusters"]["mean"]) if key == "rarefied_mean" else float(row[key])


def ratio(a: float, b: float) -> float | None:
    return a / b if b else None


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp-dir", type=Path, required=True, help="path to gen_art_experiment_52")
    ap.add_argument("--out", type=Path, default=ROOT / "results" / "replication_sensitivities.json")
    args = ap.parse_args()
    pas = json.loads((args.exp_dir / "results" / "analysis_clusters.json").read_text())["per_arm_seed"]
    out: dict = {"stochastic_share_valid": {f"{s}-{a}": pas[f"{s}-{a}"]["desc"]["stochastic_share_valid"]
                                            for s in SEEDS for a in ARMS}, "counts": {}, "ratios": {}}
    for key in COUNTS:
        c = {f"{s}-{a}": count(pas[f"{s}-{a}"], key) for s in SEEDS for a in ARMS}
        pooled = {a: sum(c[f"{s}-{a}"] for s in SEEDS) for a in ARMS}
        out["counts"][key] = {"per_seed": c, "pooled": pooled}
        r = {}
        for ref in ["T1.0", "T1.6", "RPB"]:
            r[f"DTB/{ref}"] = {"pooled": ratio(pooled["DTB"], pooled[ref]),
                               **{s: ratio(c[f"{s}-DTB"], c[f"{s}-{ref}"]) for s in SEEDS}}
        out["ratios"][key] = r
        logger.info(f"{key}: pooled DTB {pooled['DTB']:.1f}, RPB {pooled['RPB']:.1f}, T1.0 {pooled['T1.0']:.1f}, "
                    f"T1.6 {pooled['T1.6']:.1f}; ratios "
                    + ", ".join(f"{k} {v['pooled']:.3f}" if v["pooled"] is not None else f"{k} n/a"
                                for k, v in r.items()))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2))
    logger.info(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
