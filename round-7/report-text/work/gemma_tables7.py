"""Print Tables 364b, 364c and 365b of Section 7.8 from the Gemma experiment's result files.

These three tables were added to work/iter7_part3.md as static text in the second pass over the section;
this script regenerates them for checking (standard library only, read-only on the artifact).
"""
import json
from pathlib import Path

G = Path(__file__).resolve().parents[3] / "round-7/experiment-38/src/results"
d = json.loads((G / "g2_decisions.json").read_text())
das = json.loads((G / "g2_das.json").read_text())
dose = json.loads((G / "g2_dose.json").read_text())["cells"]


def f(x, n=2):
    return f"{x:.{n}f}"


sl, nat = d["second_layer"]["22"], d["natural_variance"]
print("Table 364b: rank | recovery (seeds) | directional effect | IIA | random | permuted | random-init | natural variance | block 22")
for k in ["1", "2", "4", "8"]:
    v = d["per_k"][k]
    print(k, f(v["das_recovery_seed_median"]), [f(x) for x in v["das_recovery_by_seed"]], f(v["trained_dy_dir_mean"]),
          f(v["iia_seed_median"]), v["rand_recovery"], f(v["shuf_heldout_recovery_median"]), f(v["rinit_dy_dir_mean"]),
          f"{nat[k]['share']:.5f} ({nat[k]['random_p95']:.5f})", f(sl["per_k_recovery_seed_median"][k]),
          f(sl["per_k_dy_dir_seed_median"][k]), sl["rand_recovery"][k])
print("Table 364c: block | full-state BFS | full-state DFS | share >= 1 nat | rank-1 CV recovery")
for L in sorted(das["full_state_ceiling_by_layer"], key=int):
    v = das["full_state_ceiling_by_layer"][L]
    s = das["layer_scan"]["by_layer"].get(L)
    print(L, f"{v['dy_full_bfs_src_mean']:+.2f}", f"{v['dy_full_dfs_src_mean']:+.2f}", f(v["share_abs_ge_1"]),
          f(s["cv_median_recovery"]) if s else "not scanned")
print("Table 365b: cell | attempted DFS | correct DFS | pass | McNemar")
for key in ["twin"] + [f"DAS|dfs|{x}" for x in ["0.1", "0.2", "0.35", "0.5", "0.75", "1.0"]] + ["DiM|dfs|1.0"]:
    x = dose[key]
    print(key, x.get("labels", {}).get("dfs") if key == "twin" else x["attempted_target"],
          x.get("correct_target"), f(x["pass_rate"]), x.get("mcnemar_correct"))
