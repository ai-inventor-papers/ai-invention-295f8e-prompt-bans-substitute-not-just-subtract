"""Print the headline numbers from results/*.json (used to write the README results section)."""
import json
from pathlib import Path

R = Path(__file__).resolve().parent.parent / "results"
L = lambda n: json.loads((R / n).read_text())  # noqa: E731
v1, v2, cl, held, ss = L("verdict_v1.json"), L("verdict_v2.json"), L("clusters.json"), L("heldout.json"), L(
    "search_summary.json")
print("V1", v1["verdict"], "bar", round(v1["bar_0.8xNN"], 3), "NN", round(v1["G200_NN"], 3), v1["failing"])
for k, v in v1["per_arm_seed"].items():
    print("  G200", k, round(v, 3))
print("V2", v2["verdict"], v2["branches"], {k: round(x, 3) for k, x in v2["R"].items()})
print("  r", {k: round(x, 3) for k, x in v2["r"].items()})
print("  secondary", {k: round(x, 3) for k, x in v2["secondary"].items()}, "per1M", {k: round(x, 3) for k, x in v2["per_1M_tokens"].items()})
print("  rarefied", {k: round(x, 3) for k, x in v2["rarefied"].items()}, "pooled", {k: round(x, 3) for k, x in v2["pooled_linkage"].items()})
print("  sign reversals", v2["sign_reversals_in_sensitivities"], "single_run", v2["single_run"], v2["criteria"], v2["mean_G200"])
for k, v in cl["ratios_per_seed"].items():
    b = v["boot95"]
    print("  ratio DTB/", k, round(v["ratio"], 3), "CI", b["lo"] and round(b["lo"], 3), b["hi"] and round(b["hi"], 3))
for k, v in cl["per_arm_seed"].items():
    print("CL", k, v["calls"], v["probe_valid"], v["unique_vectors"], v["primary_clusters"], v["secondary_clusters"],
          round(v["rate_per_1000_calls"], 1), round(v["shannon"], 2), v["min_within_agreement"])
print("pooled", cl["pooled"]["mode"], cl["pooled"]["n_unique"], cl["pooled"].get("n_pooled_clusters"))
for k, v in cl["pooled"]["per_arm_seed"].items():
    print("  pooled", k, v)
for k, v in ss["per_arm_seed"].items():
    print("SS", k, v["calls"], "valid", round(v["validity"], 3), "pv", round(v["probe_valid_share"], 3), "bestF",
          v["best_F"] and round(v["best_F"], 3), "trunc", round(v["truncated_share"], 3), "gen", v["gen_tokens"],
          "betterNN", round(v["better_than_NN_share"], 3), "dup", round(v["ast_cache_dup_share"], 3))
for k, v in ss["dtb_rpb_diagnostics"].items():
    print("DG", k, "nobranch", v["no_branch_share"], "Hmed", v["H_j_star_median"] and round(v["H_j_star_median"], 3),
          "idopkw", v["id_op_kw_share"] and round(v["id_op_kw_share"], 3), "eq", v["forced_eq_sampled_share"],
          "vbr", {a: round(b, 2) for a, b in v["validity_by_forced_rank"].items()})
for k, v in ss["idea_rename_rate"].items():
    print("RN", k, v)
for k, v in held["arm_best"].items():
    print("HB", k, "F", round(v["F"], 3), "G200", v.get("G200") and round(v["G200"], 3), "EXT",
          v.get("G200_ext") and round(v["G200_ext"], 3), "TSPLIB", v.get("tsplib_mean") and round(v["tsplib_mean"], 3),
          "ciNN", v.get("ci_vs_NN") and {a: round(b, 3) for a, b in v["ci_vs_NN"].items() if a != "n"})
for k, v in held.get("paired_DTB_vs", {}).items():
    print("PD", k, {a: round(b, 3) for a, b in v.items() if a != "n"})
for k, v in held.get("others", {}).items():
    print("OT", k, v.get("kind"), "F", v.get("F") and round(v["F"], 3), "G200", round(v["G200"], 3), "EXT",
          v.get("G200_ext") and round(v["G200_ext"], 3), "TSPLIB", v.get("tsplib_mean") and round(v["tsplib_mean"], 3))
try:
    v3 = L("v3.json")
    print("V3 pool", len(v3["pool"]), "candidates", len(v3["candidates"]), v3["n_candidates_per_arm"])
    for c in v3["candidates"][:12]:
        print("  cand", c["arm_seed"], c["call_idx"], round(c["G200"], 3), round(c["max_corpus_agreement"], 3), c["nearest_corpus"][:1])
except FileNotFoundError:
    pass
