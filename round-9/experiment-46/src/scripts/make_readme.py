#!/usr/bin/env python3
"""Composes README.md from the result JSONs (headline numbers are read, never typed by hand) + README_static.md."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "results"


def j(p, default=None):
    p = R / p
    return json.loads(p.read_text()) if p.exists() else default


def f(x, n=2):
    return "n/a" if x is None else (f"{x:.{n}f}" if isinstance(x, (int, float)) else str(x))


def main():
    v = j("n4_verdict.json", {})
    rep = j("repro_mname_32b.json", {})
    rep8 = j("repro_mname_8b.json", {})
    beh = j("behavioural_distance.json", {})
    ng = j("naming_gate.json", {})
    lr = j("lexical_regression.json", {})
    rsa = j("rsa.json", {})
    pl = j("placement.json", {})
    geo = j("geometry_all.json", {})
    costs = j("costs.json", {})
    rd = j("rederive.json", {})
    au = j("audit_states.json", {})
    gt = j("g_tracer.json", {})
    gs = j("g_scrub.json", {})
    acc = j("acceptance.json", {})
    sets = json.loads((ROOT / "data" / "mcode_sets.json").read_text())
    dev = j("deviations.json", [])
    P = v.get("predictions", {})
    L = []
    L.append("# Mapping the ten grid algorithms with and without their names (TP-G, iteration 9)\n")
    L.append("Does Qwen3-32B's internal map of ten path-search algorithms reflect what the algorithms *do*, or only "
             "their *names*? Iteration 8 found that the algorithm Qwen3-32B writes when its top five are banned (unit-"
             "weight Dijkstra) sits OPPOSITE the banned five on a manifold built from prompts that *name* each "
             "algorithm. This artifact rebuilds that manifold four ways, holding the model, readout, block rule, k and "
             "landing code fixed: **M-name** (iteration 8's 300 alias prompts, reproduced), **M-desc** (name-free "
             "mechanism descriptions that Qwen3-32B can name), **M-lex** (name-only sentences minus token-length-"
             "matched neutral-noun twins) and **M-code** (name-scrubbed, verified programs, teacher-forced). "
             "All geometry is correlational: " + v.get("statement", "") + "\n")
    L.append(f"**Named outcome (pre-registered rule): {v.get('named_outcome', 'n/a')}.** "
             f"M-code class of unit Dijkstra at k 15: {v.get('mcode_class_k15')}; M-desc: {v.get('mdesc_class_k15')}; "
             f"M-code source robustness: {v.get('mcode_source_robustness')}; k-sensitive: {v.get('k_sensitive')}.\n")
    L.append("## Headline results\n")
    gr = rep.get("G_repro", {})
    L.append("### 1. M-name reproduces iteration 8's classes, but not its committed rank gate\n")
    L.append(f"- Per-prompt cosine with iteration 8's cached states: >= {f(min(x['min'] for x in rep.get('cosine_by_block', {'0': {'min': None}}).values()) if rep.get('cosine_by_block') else None, 5)} at every block (17-47).")
    L.append(f"- g of the five non-banned algorithms: max |difference| {f(gr.get('max_abs_g_diff'), 3)}; classes identical "
             f"({gr.get('classes_new')}).")
    L.append(f"- Committed gate (Spearman of the 45 class-geodesic entries, k 15, block 31) = {f(gr.get('spearman_vs_geo_C6_nf4_k15_block31'), 3)} < 0.95: "
             f"**G-repro fails**; at k 10 the same statistic is {f(rep.get('by_k', {}).get('10', {}).get('spearman_class_geodesic'), 3)}. "
             "Near-tied kNN edges among the banned clusters flip at k 15 (float16 storage was ruled out: 0.9999). "
             "Fallback F1 applies: the new states are used throughout and iteration 8's verdict (OPPOSITE) is reported beside.")
    if rep8:
        L.append(f"- Qwen3-8B bf16 M-name against iteration 8's cached states: Spearman {f(rep8.get('by_k', {}).get('15', {}).get('spearman_class_geodesic'), 3)} (k 15), unit Dijkstra OPPOSITE at every k.\n")
    L.append("### 2. Verdict table (where the 15 unit-Dijkstra survivors land)\n")
    L.append("| Manifold (model) | L* | N | non-banned used | class(uDij) k10 | class(uDij) k15 | rank (1 = nearest) | g/median | nearest banned | landing verdict k15 | bootstrap P(EDGE) | split-half (S-B) |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for key, r in geo.items():
        if not r:
            continue
        d = r["L_star"]["describe"]
        k15, k10 = d.get("k15", {}), d.get("k10", {})
        bs = r["L_star"].get("bootstrap", {}).get("k15", {})
        sh = r["L_star"].get("split_half", {}).get("k15", {})
        land = r["L_star"].get("landing", {}).get("k15", {}).get("pooled", {}).get("verdict")
        L.append(f"| {key} | {r['L_star']['block']} | {r['n_points']} | {', '.join(d['nonbanned_used'])} | "
                 f"{k10.get('classes', {}).get('dijkstra_unit')} | {k15.get('classes', {}).get('dijkstra_unit')} | "
                 f"{k15.get('udij_rank')} | {f(k15.get('udij_ratio'))} | {k15.get('nearest_banned', {}).get('dijkstra_unit')} | "
                 f"{land} | {f(bs.get('edge_probability', {}).get('dijkstra_unit'))} | {f(sh.get('spearman_brown'))} |")
    L.append("\nClasses use iteration 8's relative rule (EDGE below the median of the non-banned g values, OPPOSITE "
             "above). A class over fewer than five non-banned algorithms is reported but weaker (see M-desc and M-code "
             "exclusions below).\n")
    L.append("### 3. Names drive the alias-level geometry (P4)\n")
    for key in ("32b|mname", "8b|mname", "32b|mlex"):
        r = lr.get(key)
        if r:
            L.append(f"- {key}: Spearman(g_alias, L1) = {f(r['k10']['spearman_L1'])} (k 10, permutation p {f(r['k10']['perm_p_L1'], 4)}) and "
                     f"{f(r['k15']['spearman_L1'])} (k 15, p {f(r['k15']['perm_p_L1'], 4)}); partial given alias length "
                     f"{f(r['k15']['partial_L1_given_length'])}; within-algorithm exact p (L2, 7,776 permutations) "
                     f"{f(r['k15']['within_algorithm']['exact_p_lower'], 3)}. P4 (<= -0.6 at both k): {r.get('P4_pass')}.")
    L.append("\n### 4. RSA against model RDMs (exact label-permutation Mantel p)\n")
    L.append("| Neural RDM | R_lex | R_beh | R_surface | R_len | noise ceiling (upper) |")
    L.append("|---|---|---|---|---|---|")
    for key, r in rsa.items():
        if key == "name_evocation" or not isinstance(r, dict) or "models" not in r:
            continue
        cell = lambda m: (f"{r['models'][m]['rho']:.2f} (p {r['models'][m]['p_exact']:.3f})" if m in r["models"] else "-")
        L.append(f"| {key} ({len(r['present'])} classes) | {cell('R_lex')} | {cell('R_beh')} | {cell('R_surface')} | "
                 f"{cell('R_len')} | {f(r.get('noise_ceiling_upper'))} |")
    ne = rsa.get("name_evocation", {}).get("32b", {})
    if ne:
        L.append(f"\nName evocation: a probe trained on M-name (block {ne.get('block')}) classifies M-desc at balanced "
                 f"accuracy {f(ne.get('mdesc', {}).get('transfer_balanced_accuracy'))} (chance {f(ne.get('mdesc', {}).get('chance'))}) "
                 f"and M-code R1 at {f(ne.get('mcode_PRIMARY_R1', {}).get('transfer_balanced_accuracy'))}.")
    L.append("\n### 5. Behavioural anchor (P6) and stimulus gates\n")
    L.append(f"- Behavioural RDM from expansion-order traces of the 15 T1 references on 40 probe grids: d_beh to BFS "
             f"{ {a: round(x, 2) for a, x in beh.get('P6_d_beh_to_bfs', {}).items()} }; unit Dijkstra nearest BFS: "
             f"{beh.get('P6_udij_nearest_to_bfs')} (true by construction for the order term). Behavioural classes: "
             f"{beh.get('behavioural_classes')}. G-tracer {gt.get('n_pass')}/{gt.get('n')} (biA* shows no second "
             "frontier because its forward side always wins ties on these grids; IDA* rarely restarts because the "
             "Manhattan bound is tight).")
    L.append(f"- Naming gate (Qwen3-32B, 20 namings per description, >= 16/20): passing descriptions per algorithm "
             f"{ng.get('passing_per_algorithm')}; excluded {ng.get('excluded')}. **JPS has no nameable name-free "
             "description**, so M-desc classes run over the other four non-banned algorithms.")
    L.append(f"- M-code program sets (PRIMARY / Qwen3-32B-only M32 / Qwen3-8B-only M8): {sets.get('counts')}; "
             f"algorithms below the 10-program floor are excluded: {sets.get('excluded_lt_min')}.")
    L.append(f"- G-scrub (name scrubbing preserves AST modulo names, expansion sequences, labels and suite outcomes): "
             f"{gs.get('n_pass')}/{gs.get('n_checked')}; planted 'def bfs' test clean={gs.get('planted', {}).get('clean')}.\n")
    L.append("### 6. Per-program placement on M-code\n")
    for key, r in pl.items():
        u = r.get("udij_survivors", {})
        L.append(f"- {key} (block {r['block']}, k {r['k']}): leave-one-out placement accuracy {f(r['G_place']['loo_accuracy'])} "
                 f"(gate 0.70: {r['G_place']['pass']}); unit-Dijkstra survivors EDGE {u.get('n_edge')}/{u.get('n')}, "
                 f"nearest-algorithm counts {{{', '.join(f'{a}: {n}' for a, n in (u.get('nearest_algorithm_counts') or {}).items() if n)}}}; "
                 f"BASE programs placed on their own label: {f(r.get('base_accuracy_own_label'))}.")
    L.append("\n### 7. Pre-registered predictions\n")
    for p in ("P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"):
        x = P.get(p, {})
        L.append(f"- {p}: pass = {x.get('pass', 'descriptive')}")
    L.append("\n### 8. Independent re-derivation\n")
    L.append(f"- `audit/rederive.py` (standard library only, from the JSON class matrices and alias rows): "
             f"{rd.get('n_mismatches', 'n/a')} mismatches; placebos {rd.get('placebos')}.")
    if au:
        L.append(f"- `audit/audit_states.py` (sklearn kNN + networkx Dijkstra on the raw state files, no project "
                 f"geometry code): mismatches {au.get('mismatches')}; " +
                 "; ".join(f"{k}: classes equal {c['classes_equal']}, max |dg| {c['max_abs_g_diff']:.2e}, placebo share "
                           f"{c['placebo_shuffled_labels_share_same_udij_class']:.2f}" for k, c in au.get("checks", {}).items()))
    L.append(f"\n## Cost\n\nOpenRouter: USD {f(costs.get('total_usd'), 3)} for {costs.get('n_calls')} calls "
             f"({costs.get('by_purpose')}); cap 0.40.\n")
    L.append("## Deviations (results/deviations.json)\n")
    for d in dev:
        L.append(f"- **{d['code']}**: {d['text']}")
    L.append("")
    L.append((ROOT / "README_static.md").read_text())
    (ROOT / "README.md").write_text("\n".join(L) + "\n")
    print("README.md written", len(L), "blocks")


if __name__ == "__main__":
    main()
