#!/usr/bin/env python3
"""T7: forecast/scoring tests on synthetic events (run before the commit)."""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np  # noqa: E402
from scipy.stats import wilcoxon  # noqa: E402

from src import scoring as SC  # noqa: E402
from src.forecasts import mass_transfer  # noqa: E402
from src.ws import RESULTS, write_json  # noqa: E402


def main() -> None:
    res = {}
    S = ["a", "b", "c"]
    labels = ["a"] * 6 + ["b"] * 3 + ["other"]
    land = {"a": 0.6, "b": 0.3, "c": 0.0, "other": 0.1}
    q_land = SC.smooth(land, S)
    q_uni = SC.smooth(None, S)
    res["landing_beats_uniform"] = SC.log_score(q_land, labels) > SC.log_score(q_uni, labels)
    pm = {"a": 1.0, "b": 0.0, "c": 0.0, "other": 0.0}
    q = SC.smooth(pm, S)
    hand_a = 0.93 + 0.05 / 3
    hand_b = 0.05 / 3
    hand_o = 0.02
    hand = (6 * math.log(hand_a) + 3 * math.log(hand_b) + math.log(hand_o)) / 10
    res["point_mass_by_hand"] = abs(SC.log_score(q, labels) - hand) < 1e-12
    B = {"a": 0.2, "b": 0.5, "c": 0.2, "other": 0.1}
    mt = mass_transfer(B, 1.0, "c", S)
    res["mass_transfer_equals_point_mass_at_sX_1"] = all(abs(mt[k] - (1.0 if k == "c" else 0.0)) < 1e-12 for k in mt)
    res["undefined_is_uniform"] = all(abs(SC.smooth(None, S)[k] - SC.smooth(SC.uniform(S), S)[k]) < 1e-12 for k in S + ["other"])
    res["q_sums_to_one"] = abs(sum(q.values()) - 1) < 1e-12
    # advance rule: synthetic 4 disagreeing gated events where SUBTRACT wins 3 by >= 0.1
    rows = []
    for i in range(4):
        ls = {"SUBTRACT": -0.5, "LADDER": -1.0, "ASSOCIATE": -0.65 if i < 3 else -0.45, "PROXIMITY": -2.0}
        sc = {"gate": {"gate_pass": True}, "disagreeing": True, "logscore": ls, "top1_hit": {f: None for f in SC.FAMILIES},
              "chance": 1 / 3}
        srt = sorted(ls.items(), key=lambda kv: -kv[1])
        sc["best"], sc["margin"] = srt[0][0], srt[0][1] - srt[1][1]
        sc["winner"] = sc["best"] if sc["margin"] >= SC.ADV_MARGIN else None
        rows.append({"task": f"t{i}", "scored": sc})
    agg = SC.aggregate(rows)
    res["advance_counts"] = agg["wins"]
    res["advance_rule_ok"] = agg["advances"]["SUBTRACT"] and not agg["advances"]["ASSOCIATE"] and agg["wins"].get("SUBTRACT") == 3
    res["branch_synthetic"] = agg["branch"]
    v = np.array([0.3, -0.1, 0.5, 0.2, 0.25, -0.05, 0.4, 0.15, 0.35, 0.1, 0.05])
    res["wilcoxon_scipy_p"] = float(wilcoxon(v).pvalue)
    h = SC.holm({"x": 0.01, "y": 0.04, "z": 0.03})
    res["holm"] = h
    res["holm_ok"] = h["x"]["reject"] and not h["y"]["reject"] and not h["z"]["reject"] and abs(h["x"]["p_adj"] - 0.03) < 1e-12
    res["passed"] = all(res[k] for k in ("landing_beats_uniform", "point_mass_by_hand",
                                         "mass_transfer_equals_point_mass_at_sX_1", "undefined_is_uniform",
                                         "q_sums_to_one", "advance_rule_ok", "holm_ok"))
    write_json(RESULTS / "tests_scoring.json", res)
    print(res)
    assert res["passed"]


if __name__ == "__main__":
    main()
