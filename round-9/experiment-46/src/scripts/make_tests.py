#!/usr/bin/env python3
"""results/tests.json: the plan's unit tests U1-U11. Collects the checks the stages already ran (hook checks, span
checks, scrubber, tracer, twins, commitments) and runs the cheap synthetic ones here (U6 planted lexical test, U7
out-of-sample placement). Tests that were not run are listed as such."""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(1, str(ROOT / "vendor" / "exp9"))
R = ROOT / "results"


def j(p, d=None):
    p = R / p
    return json.loads(p.read_text()) if p.exists() else d


def main():
    import geometry
    from common import verify_chain
    from scipy.stats import spearmanr

    from stage_analysis import oos

    t = {}
    hc = [j("states_mname_32b.json", {}).get("hook_check")] + [j(p.name, {}).get("hook_check")
                                                               for p in sorted(R.glob("load_*.json"))]
    t["U1_hook_exactness"] = {"checks": hc, "pass": all(h and h.get("pass") for h in hc)}
    sc = j("states_mname_32b.json", {}).get("span_checks", [])
    t["U2_spec_span"] = {"mname_span_checks": sc, "pass": all(c.get("decoded_equals_spec") and c.get("span_equal")
                                                              for c in sc),
                         "note": "every S-mean family asserts decoded span == SPEC and identical span/prefix with the "
                                 "thinking switch off (stage_states.smean_family); M-lex asserts identical SPEC ids"}
    mc = j("states_mcode_32b.json", {})
    t["U3_code_span"] = {"n_programs": mc.get("n"), "r2_rules": mc.get("r2_rules"),
                         "pass": bool(mc.get("n")),
                         "note": "every program asserts that the overlapping code-span tokens decode to the code; R3 is "
                                 "the 16th code token"}
    gs = j("g_scrub.json", {})
    t["U4_scrubber"] = {"planted": {k: v for k, v in gs.get("planted", {}).items() if k != "scrubbed"},
                        "n_pass": gs.get("n_pass"), "n_checked": gs.get("n_checked"),
                        "pass": bool(gs.get("planted", {}).get("clean") and gs.get("planted", {}).get("passes"))}
    gt = j("g_tracer.json", {})
    t["U5_tracer"] = {"g_tracer": f"{gt.get('n_pass')}/{gt.get('n')}", "planted": gt.get("planted_controls"),
                      "pass": bool(gt.get("planted_controls", {}).get("bfs_as_stack_reads_lifo") and
                                   gt.get("planted_controls", {}).get("dijkstra_with_manhattan_sets_heuristic")),
                      "failing_references": [r["file"] for r in gt.get("rows", []) if not r["pass"]]}
    # U6 planted lexical test: centroids at distances set by L1 -> Spearman(g, L1) near -1; shuffled L1 near 0
    rng = np.random.default_rng(0)
    L1 = np.array([1, 1, 1, 1, 1, 1, 1, 2, 1, 0, 0, 0, 0, 0, 0], dtype=float)
    banned_c = rng.normal(size=(5, 20))
    X, lab = [], []
    for b in range(5):
        X.append(banned_c[b] + 0.05 * rng.normal(size=(30, 20)))
        lab += [f"b{b}"] * 30
    for i, l1 in enumerate(L1):
        c = banned_c[i % 5] + (4.0 - 1.5 * l1) * rng.normal(size=20) / np.sqrt(20)
        X.append(c + 0.05 * rng.normal(size=(10, 20)))
        lab += [f"a{i}"] * 10
    X, lab = np.vstack(X), np.array(lab)
    geo, _ = geometry.geodesics(X, 10)
    g = np.array([min(geo[np.ix_(lab == f"a{i}", lab == f"b{b}")].mean() for b in range(5)) for i in range(15)])
    rho = float(spearmanr(g, L1).statistic)
    rho_sh = float(np.mean([spearmanr(g, rng.permutation(L1)).statistic for _ in range(200)]))
    t["U6_planted_lexical"] = {"spearman_planted": rho, "mean_spearman_shuffled": rho_sh,
                               "pass": rho < -0.6 and abs(rho_sh) < 0.15,
                               "note": "iteration 8's t8 synthetic ring was not re-run here"}
    # U7 out-of-sample placement
    C = rng.normal(size=(4, 30)) * 3
    F = np.vstack([C[i] + rng.normal(size=(25, 30)) for i in range(4)])
    fl = np.repeat(np.arange(4), 25)
    geoF, _ = geometry.geodesics(F, 10)
    hits = 0
    for i in range(4):
        for _ in range(10):
            x = C[i] + rng.normal(size=30)
            dv = oos(x, F, geoF, 10)
            hits += int(np.argmin([dv[fl == a].mean() for a in range(4)]) == i)
    node = oos(F[3], F, geoF, 10)
    t["U7_out_of_sample"] = {"held_out_own_cluster_share": hits / 40,
                             "graph_node_max_abs_diff": float(np.abs(node - geoF[3]).max()),
                             "pass": hits / 40 >= 0.95 and float(np.abs(node - geoF[3]).max()) < 1e-9}
    rd = j("rederive.json", {})
    t["U8_landing_placebo"] = {"random_survivor_labels_share_NEITHER":
                               rd.get("placebos", {}).get("random_survivor_labels_share_NEITHER"),
                               "exact_U_null_matches_landing_py": rd.get("n_mismatches") == 0,
                               "pass": (rd.get("placebos", {}).get("random_survivor_labels_share_NEITHER") or 0) >= 0.85}
    ml = json.loads((ROOT / "data" / "mlex_prompts.json").read_text())
    t["U9_twins"] = {"checks": ml.get("checks"), "n_pairs": ml.get("n"), "pass": all(ml.get("checks", {}).values())}
    keys = [json.loads(l) for l in (R / "openrouter_key_checks.jsonl").read_text().splitlines()] \
        if (R / "openrouter_key_checks.jsonl").exists() else []
    t["U10_openrouter"] = {"key_checks_logged": len(keys), "costs": j("costs.json"),
                           "pass": len(keys) > 0,
                           "note": "provider and usage.cost recorded on every row; the simulated-403 dry run was not "
                                   "repeated here (iteration 8's sample_or stop logic is reused; no 403 occurred)"}
    ok, problems, entries = verify_chain()
    t["U11_commitments"] = {"chain_ok": ok, "problems": problems, "labels": [e["label"] for e in entries],
                            "pass": ok}
    (R / "tests.json").write_text(json.dumps(t, indent=1, default=str))
    print({k: v.get("pass") for k, v in t.items()})


if __name__ == "__main__":
    main()
