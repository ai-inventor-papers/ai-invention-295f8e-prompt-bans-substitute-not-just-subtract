#!/usr/bin/env python3
"""Writes .terminal_claude_agent_struct_out.json from the result files (numbers read, not typed)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "results"


def j(p, d=None):
    p = R / p
    return json.loads(p.read_text()) if p.exists() else d


def f(x, n=2):
    return "n/a" if x is None else (f"{x:.{n}f}" if isinstance(x, (int, float)) else str(x))


def main():
    v = j("n4_verdict.json", {})
    rep = j("repro_mname_32b.json", {})
    lr = j("lexical_regression.json", {})
    geo = j("geometry_all.json", {})
    rsa = j("rsa.json", {})
    pl = j("placement.json", {})
    rd = j("rederive.json", {})
    au = j("audit_states.json", {})
    costs = j("costs.json", {})
    ng = j("naming_gate.json", {})
    sets = json.loads((ROOT / "data" / "mcode_sets.json").read_text())

    def cls(key, k="k15"):
        r = geo.get(key)
        if not r:
            return "not run"
        d = r["L_star"]["describe"][k]
        return f"{d['classes'].get('dijkstra_unit')} (rank {d['udij_rank']}/{len(d['g'])}, g/median {f(d['udij_ratio'])})"

    def rho(key, m):
        x = rsa.get(key, {}).get("models", {}).get(m)
        return f"{x['rho']:.2f} (p {x['p_exact']:.3f})" if x else "n/a"

    gr = rep.get("G_repro", {})
    lm = lr.get("32b|mname", {})
    plc = pl.get("32b|mcode_PRIMARY_R1", {})
    u = plc.get("udij_survivors", {})
    s = (f"TP-G iteration 9 (claim N4). Qwen3-32B nf4 (truncated decoder, iteration 8's code unchanged) and Qwen3-8B "
         f"bf16 ten-algorithm grid manifolds rebuilt four ways with fixed readout/block rule/k/landing code: M-name "
         f"(300 alias prompts), M-desc (name-free descriptions passing a Qwen3-32B naming gate; JPS has none: "
         f"{ng.get('excluded')}), M-lex (alias minus token-matched neutral twin) and M-code (name-scrubbed verified "
         f"programs; PRIMARY counts {sets['counts']['PRIMARY']}; classes over non-banned algorithms with >= 10 "
         f"programs). NAMED OUTCOME: {v.get('named_outcome')}. Unit-Dijkstra (the iteration-8 survivor) class at "
         f"k15: M-name {cls('32b|mname')}; M-lex {cls('32b|mlex')}; M-desc {cls('32b|mdesc')}; M-code R1 "
         f"{cls('32b|mcode_PRIMARY_R1')}; M-code Qwen3-32B-only frame {cls('32b|mcode_M32_R1')}; 8B M-name "
         f"{cls('8b|mname')}, 8B M-desc {cls('8b|mdesc')}, 8B M-code {cls('8b|mcode_PRIMARY_R1')}. Reproduction: "
         f"per-prompt cosine >= 0.9999, g within {f(gr.get('max_abs_g_diff'), 3)}, classes identical, but committed "
         f"gate Spearman {f(gr.get('spearman_vs_geo_C6_nf4_k15_block31'), 3)} < 0.95 (k10: "
         f"{f(rep.get('by_k', {}).get('10', {}).get('spearman_class_geodesic'), 3)}; kNN tie flips), fallback F1. "
         f"Lexical: Spearman(g_alias, L1) on M-name {f(lm.get('k10', {}).get('spearman_L1'))} (k10) / "
         f"{f(lm.get('k15', {}).get('spearman_L1'))} (k15), P4 {lm.get('P4_pass')}. RSA (exact 10! Mantel): M-name "
         f"vs R_lex {rho('32b|mname', 'R_lex')}, vs R_beh {rho('32b|mname', 'R_beh')}; M-desc vs R_beh "
         f"{rho('32b|mdesc', 'R_beh')}; M-code vs R_beh {rho('32b|mcode_PRIMARY_R1', 'R_beh')}, vs R_surface "
         f"{rho('32b|mcode_PRIMARY_R1', 'R_surface')}. Placement on M-code: LOO accuracy "
         f"{f(plc.get('G_place', {}).get('loo_accuracy'))}; uDij survivors EDGE {u.get('n_edge')}/{u.get('n')}. "
         f"Predictions pass: { {p: x.get('pass') for p, x in v.get('predictions', {}).items()} }. Audits: "
         f"rederive.py {rd.get('n_mismatches')} mismatches, audit_states mismatches {au.get('mismatches')}. "
         f"Geometry is correlational. OpenRouter USD {f(costs.get('total_usd'), 3)}. Files: results/n4_verdict.json, "
         f"results/geometry_*.json, rsa.json, lexical_regression.json, placement.json, figures/ (PCA/MDS/Isomap in "
         f"activation coordinates), method_out.json; cache/states/ (states + frozen geodesic graphs geo_*_k10/k15.npz "
         f"for iteration 10) stays on the run volume, not in the repository.")
    out = {"title": "Mapping grid algorithms with and without their names",
           "layman_summary": ("Rebuilds an AI model's internal map of ten path-finding algorithms from names, "
                              "name-free descriptions and name-scrubbed code, to test whether earlier map findings "
                              "were driven by the names alone."),
           "summary": s[:4990],
           "out_expected_files": {"script": "method.py", "full_output": "full_method_out.json",
                                  "mini_output": "mini_method_out.json", "preview_output": "preview_method_out.json",
                                  "reproducibility": "reproducibility.md"},
           "upload_ignore_regexes": ["(^|/)cache/states/", "(^|/)inputs/e44/states/", "(^|/)\\.venv/",
                                     "(^|/)__pycache__/", "(^|/)data/trace_cache/"]}
    (ROOT / ".terminal_claude_agent_struct_out.json").write_text(json.dumps(out, indent=1))
    print(len(s), "chars summary")


if __name__ == "__main__":
    main()
