"""Print the key numbers of every results file (for the README)."""
import json
from pathlib import Path
R = Path("results")
def j(n):
    p = R / n
    return json.loads(p.read_text()) if p.exists() else None
d = j("g2_dose.json")
if d:
    print("== G2 dose")
    for n, c in d["cells"].items():
        print(f"{n:16s} n {c['n']:3d} att {c['attempted_target']:3d} cor {c['correct_target']:3d} pass {c['pass_rate']:.2f} "
              f"p_cor {c.get('p_correct_one_sided', float('nan')):.2e} holm {c.get('p_correct_holm', float('nan')):.2e} "
              f"p_att {c.get('p_attempted_one_sided', float('nan')):.2e} tf {c.get('tf_pred_attempted_bfs', float('nan')):.2f} {c['labels']}")
    print(json.dumps(d["knob"], indent=0))
g = j("g1_generation.json")
if g:
    print("== G1 gen")
    for a, c in g["arms"].items():
        print(a, c["n"], "att", c["attempted_target"], "cor", c["correct_target"], "pass", round(c["pass_rate"], 2), c["labels"])
    for a, t in g["tests"].items():
        print(" ", a, {k: (round(v, 5) if isinstance(v, float) else v) for k, v in t.items()})
v = j("g1_validation.json")
if v:
    print("== G1 validation")
    for mode, recs in v["per_node"].items():
        for r in recs:
            print(mode, r["node"], "mean_d", round(r["mean_d"], 3), "median_d", round(r["median_d"], 3), "p", round(r["p_sign_flip"], 5),
                  "holm", round(r["p_holm"], 4), "frac95", round(r["frac_prompts_above_null_p95"], 2), "claim", r["NODE_CLAIM"],
                  "forced", [round(x, 2) for x in r["forced_prompts_dm_oriented"] if x is not None])
        print(mode, "joint5", round(v["joint"][mode]["5"]["median_node_set"], 3), v["joint"][mode]["5"]["frac_random_beaten"],
              "joint10", round(v["joint"][mode]["10"]["median_node_set"], 3), v["joint"][mode]["10"]["frac_random_beaten"])
    print("claims", v["n_node_claims"], "distributed", v["distributed_circuit"], v.get("matching"))
p = j("g1_pathpatch.json")
if p:
    print("== G1-P smoke", p["smoke"])
    print("total", round(p["total_effect_mean"], 3), "atp", p["atp_error_vs_exact"], "class", p["atp_class_mass"])
    for r in p["exact"][:12]:
        print(r["node"], round(r["noise_mean"], 3), round(r["noise_sd"], 3), round(r["denoise_mean"], 3), round(r["atp_mean"], 3), round(r["noise_sign_consistency"], 2))
    print("top10", p["top10"])
    for e in p["edges_kept"][:16]:
        print("  edge", e["sender"], "->", e["receiver"], round(e["dm_mean"], 3), round(e["dm_sd"], 3))
x = j("g1_extras.json")
if x:
    print("== G1 extras", {k: v for k, v in x.items() if k not in ("top20_natural", "top20_forced", "iter6_first_order_nodes")})
t = j("g1t_graphs.json")
if t:
    print("== G1-T", t.get("status"), t.get("load_seconds"), t.get("vram_after_load_gb"))
    for r in t.get("prompts", []):
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k not in ("top_features",)})
for n in ("novelty_audit.json", "regate.json", "verify_chain.json", "rederive.json", "costs.json"):
    o = j(n)
    if o:
        print("==", n, json.dumps({k: v for k, v in o.items() if k not in ("items", "checks", "entries")})[:600])
