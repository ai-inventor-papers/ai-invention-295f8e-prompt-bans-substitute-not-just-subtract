#!/usr/bin/env python3
"""EXPLORATORY (after COMMIT1, not preregistered): structure of the leave-one-program-out nearest-cell errors on the
factorial frame. When a program is placed at the wrong cell, is that cell same-container / other-discipline (a
SURFACE confusion) or same-discipline / other-container (a MECHANISM confusion)? Chance rates are the shares of
those cells among all other cells. Writes results/explore_confusion.json."""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scipy.stats import binomtest  # noqa: E402

from tpg2 import RESULTS, ROOT, cell_dc, write_json  # noqa: E402

if __name__ == "__main__":
    mo = json.loads((ROOT / "method_out.json").read_text())
    ex = [e for e in next(d for d in mo["datasets"] if d["dataset"] == "tpg2_factorial")["examples"] if e["metadata_in_g1"]]
    cells = sorted({e["metadata_cell"] for e in ex})
    out = {}
    for key in ("predict_nearest_cell_8b", "predict_nearest_cell_32b", "predict_nearest_cell_baseline_tfidf",
                "predict_nearest_cell_baseline_astngram"):
        n = err = same_c = same_d = neither = 0
        chance_c = chance_d = 0.0
        conf = Counter()
        for e in ex:
            t, p = e["metadata_cell"], e[key]
            n += 1
            if p == t:
                continue
            err += 1
            (dt, ct), (dp, cp) = cell_dc(t), cell_dc(p)
            others = [c for c in cells if c != t]
            chance_c += sum(cell_dc(c)[1] == ct for c in others) / len(others)
            chance_d += sum(cell_dc(c)[0] == dt for c in others) / len(others)
            if cp == ct:
                same_c += 1
            elif dp == dt:
                same_d += 1
            else:
                neither += 1
            conf[f"{t}->{p}"] += 1
        out[key] = {"n": n, "errors": err, "same_container_other_discipline": same_c,
                    "same_discipline_other_container": same_d, "neither": neither,
                    "chance_same_container": chance_c / max(err, 1), "chance_same_discipline": chance_d / max(err, 1),
                    "binom_p_same_container_gt_chance": float(binomtest(same_c, err, chance_c / err, alternative="greater").pvalue) if err else None,
                    "binom_p_same_discipline_gt_chance": float(binomtest(same_d, err, chance_d / err, alternative="greater").pvalue) if err else None,
                    "top_confusions": conf.most_common(8)}
    out["label"] = "EXPLORATORY (post-COMMIT1)"
    write_json(RESULTS / "explore_confusion.json", out)
    for k, v in out.items():
        if isinstance(v, dict):
            print(k, {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items() if kk != "top_confusions"}, v["top_confusions"][:4])
