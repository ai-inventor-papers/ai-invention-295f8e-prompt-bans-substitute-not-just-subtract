#!/usr/bin/env python3
"""Analysis of the COMMIT #3 amendment (pass-filtered fork dose A9f/A10f on T10 and G): observed vs committed shares
(MAE, replay MAE), pass cost, correct Hill-1, and the same paired slot bootstrap as K1(b) (best filtered setting under
the 5-point cost constraint vs each comparator family, selection inside each replicate). Secondary, post-amendment.
Writes results/amendment.json."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg8 import BOOT_SEED, N_BOOT, PRED_DIR, RESULTS_DIR, read_json, utc_now, write_json  # noqa: E402
import analysis_k1 as AK  # noqa: E402

FILT = ["A9f", "A10f"]


def main() -> None:
    c3 = read_json(PRED_DIR / "commit3_amendment.json")
    adj_p = RESULTS_DIR / "adjudicated_labels.json"
    data = AK.load_rows(read_json(adj_p) if adj_p.exists() else None)
    out = {"utc": utc_now(), "units": {}}
    for unit, e in c3["units"].items():
        arms = data.get(unit, {})
        if not all(a in arms for a in FILT):
            continue
        tw = arms["A0"]
        cells = {a: AK.cell_measures(unit, arms[a], tw, None, e["classes"]) for a in FILT}
        mae = {a: AK.mae(cells[a]["attempted"], e["arms"][a]["attempted"], e["classes"]) for a in FILT}
        rmae = {a: AK.mae(cells[a]["attempted"], e["arms"][a]["replay"]["attempted"], e["classes"]) for a in FILT}
        slots = sorted(s for s in tw if all(s in arms[a] for a in FILT))
        rng = np.random.default_rng(BOOT_SEED)
        fams = {**AK.COMP_FAMILIES, **AK.PLACEBOS, "fork_primary": AK.FORK}
        diffs = {f: [] for f in fams}
        full = np.arange(len(slots))
        point = {"filtered": AK.boot_family_best(arms, tw, FILT, full, slots)}
        point.update({f: AK.boot_family_best(arms, tw, n, full, slots) for f, n in fams.items()})
        for _ in range(N_BOOT):
            idx = rng.integers(0, len(slots), len(slots))
            fb = AK.boot_family_best(arms, tw, FILT, idx, slots)
            for f, n in fams.items():
                diffs[f].append(fb - AK.boot_family_best(arms, tw, n, idx, slots))
        out["units"][unit] = {
            "dose": e["dose"], "cells": {a: {k: cells[a][k] for k in ("attempted", "correct", "pass_rate", "pass_cost",
                                                                     "pass_cost_ci95", "hill1_correct_r25",
                                                                     "changed_decision", "breakage")} for a in FILT},
            "pred": {a: {k: e["arms"][a][k] for k in ("attempted", "pass_cost", "off_default_attempted")} for a in FILT},
            "mae": mae, "mae_replay": rmae, "point_best_hill": point,
            "bootstrap_vs": {f: {"mean_diff": float(np.mean(v)), "lb_97_5": float(np.percentile(v, 2.5)),
                                 "p_one_sided": float((np.sum(np.array(v) <= 0) + 1) / (len(v) + 1))}
                             for f, v in diffs.items()}}
    write_json(RESULTS_DIR / "amendment.json", out)
    for u, x in out["units"].items():
        print(u, {a: (round(x["cells"][a]["pass_cost"], 3), x["cells"][a]["hill1_correct_r25"]) for a in FILT},
              "mae", x["mae"], "best", x["point_best_hill"])


if __name__ == "__main__":
    main()
