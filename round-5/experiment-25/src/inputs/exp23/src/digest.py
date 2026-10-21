#!/usr/bin/env python3
"""Print the headline numbers from results/*.json (used to write README.md)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import ALL_TASKS, PRED_DIR, RESULTS_DIR, read_json


def main() -> None:
    pre = read_json(PRED_DIR / "commit_preban.json")
    bans = read_json(RESULTS_DIR / "bans.json")
    c3a = read_json(RESULTS_DIR / "c3a.json")
    p = c3a["primary"]
    print("task | D | E_t | movable | A_t | C_t | default | other | pass | corr_av | W1..W5")
    for t in ALL_TASKS:
        b = bans[t]
        pt = b["per_template_avoidance"]
        print(f"{t} | {pre['tasks'][t]['D']} | {pre['tasks'][t]['E_t']} | {pre['tasks'][t]['movable']} | {b['A_t']:.2f} | "
              f"{b['C_t']} | {b['default_share']:.2f} | {b['other']:.2f} | {b['pass']:.2f} | "
              f"{b['correct_only_avoidance'] if b['correct_only_avoidance'] is None else round(b['correct_only_avoidance'], 2)} | "
              f"{[round(pt[w], 2) if pt[w] is not None else None for w in ('W1', 'W2', 'W3', 'W4', 'W5')]}")
    print("C3a:", json.dumps({k: p[k] for k in ("verdict", "fisher_p_raw", "fisher_p_bonferroni3", "kendall_tau_b")}),
          json.dumps(p["balanced_accuracy"]), json.dumps(p["fisher"]), json.dumps(p["spearman"]),
          json.dumps(p["bootstrap"]), json.dumps(p["placebo_task_permutation"]))
    print("LOO:", {t: (round(v["BA"], 2) if v["BA"] is not None else None, round(v["rho"], 2) if v["rho"] == v["rho"] else None)
                   for t, v in p["leave_one_task_out"].items()})
    print("sens:", json.dumps(c3a["sensitivities"], default=str))
    rv = read_json(RESULTS_DIR / "rivals.json")
    for k, v in rv.items():
        print("rival", k, {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items()})
    c3b = read_json(RESULTS_DIR / "c3b.json")
    print("c3b summary:", json.dumps(c3b.get("summary")), json.dumps(c3b.get("contest")), c3b.get("verdict"),
          json.dumps(c3b.get("placebo_shuffled_mean_log_score")))
    c1 = read_json(RESULTS_DIR / "c1_prices.json")
    for t, v in c1["per_task"].items():
        print("c1", t, {a: (round(x["pass"], 2), x["hill1_rarefied25"] and round(x["hill1_rarefied25"], 2))
                        for a, x in v["arms"].items()},
              {kn: {h: (round(hh["hill"], 2) if hh["hill"] else None, hh.get("ci95") and [round(c, 2) for c in hh["ci95"]])
                    for h, hh in kv.items()} for kn, kv in v["hull"].items()})
    for f in ("unit_sensitivity", "label_audit", "novelty_audit", "costs", "timing_summary", "rederive"):
        q = RESULTS_DIR / f"{f}.json"
        if q.exists():
            d = read_json(q)
            if f == "novelty_audit":
                d = {k: v for k, v in d.items() if k != "rows"}
            if f == "label_audit":
                d = {k: v for k, v in d.items() if k not in ("rows",)}
            if f == "unit_sensitivity":
                d = {k: v for k, v in d.items() if k != "per_task"}
            print(f, json.dumps(d, default=str)[:1500])


if __name__ == "__main__":
    main()
