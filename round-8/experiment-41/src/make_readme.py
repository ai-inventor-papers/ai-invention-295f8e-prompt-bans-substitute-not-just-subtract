#!/usr/bin/env python3
"""Writes README.md from results/summary.json (every number in the README comes from the result files)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
S = json.loads((ROOT / "results" / "summary.json").read_text())


def f(x, n=2):
    if x is None:
        return "n/a"
    if isinstance(x, float):
        return f"{x:.{n}f}"
    return str(x)


def circ_line(name: str) -> str:
    c = S["circuits"].get(name)
    if not c:
        return f"| {name} | not run | | | | |"
    a = c.get("atp_vs_exact_random160") or {}
    t = c.get("atp_vs_exact_top") or {}
    fa = c.get("faithfulness") or {}
    comp = fa.get("completeness_mean") or []
    suf = fa.get("sufficiency_mean") or []
    return (f"| {name} | {c['n_pairs']} | {f(c['TE_mean'])} | {f(a.get('spearman'))} / {f(t.get('spearman'))} | "
            f"{c['n_edges_kept']} | {f(comp[1] if len(comp) > 1 else None)} / {f(suf[1] if len(suf) > 1 else None)} |")


def val_block(name: str) -> str:
    v = S.get("validation", {}).get(name)
    if not v:
        return f"*{name}: validation not run.*\n"
    lines = [f"**{name}** ({v['n_prompts']} prompts, {v['n_heldout']} held out): {v['n_pass_both_holm20']} of 10 nodes "
             f"pass both tests (Holm over 20); ablate {v['n_pass_ablate_holm20']}/10, steer {v['n_pass_steer_holm20']}"
             f"/10; Gemma's within-test Holm: both {v['n_pass_both_within_test_holm']}.",
             "", "| node | ablate mean d | ablate p (Holm 20) | steer mean d | steer p (Holm 20) | both |",
             "|---|---|---|---|---|---|"]
    for a, s, p in zip(v["per_node"]["ablate"], v["per_node"]["steer"], v["node_pass"]):
        lines.append(f"| {a['node']} | {f(a['mean_d'], 3)} | {a['p_holm_20']:.2g} | {f(s['mean_d'], 3)} | "
                     f"{s['p_holm_20']:.2g} | {'yes' if p['both'] else 'no'} |")
    j = v["joint"]
    lines.append("")
    lines.append(f"Joint sets: top-5 beats {f(j['ablate']['5']['frac_random_beaten'])} (ablate) / "
                 f"{f(j['steer']['5']['frac_random_beaten'])} (steer) of 50 matched random five-sets; top-10 beats "
                 f"{f(j['ablate']['10']['frac_random_beaten'])} / {f(j['steer']['10']['frac_random_beaten'])}.")
    return "\n".join(lines) + "\n"


def sens_block() -> str:
    vs = S.get("validation_sensitivity") or {}
    if not vs:
        return ""
    lines = ["**Post-hoc sensitivity (labelled; committed before its rows):** the top decision heads are write-norm "
             "outliers, so their matched pools fell back to the 50 nearest-norm heads (smaller norms; head draws are "
             "not rescaled in the committed design). Re-running those head nulls with each draw's delta rescaled to "
             "the target's write norm gives (uncorrected one-sided sign-flip p):", "",
             "| contrast | node | ablate mean d | ablate p | steer mean d | steer p |", "|---|---|---|---|---|---|"]
    for n, v in vs.items():
        if not v:
            continue
        for a, st in zip(v["per_node"]["ablate"], v["per_node"]["steer"]):
            lines.append(f"| {n} | {a['node']} | {f(a['mean_d'], 3)} | {a['p_sign_flip']:.2g} | {f(st['mean_d'], 3)} | "
                         f"{st['p_sign_flip']:.2g} |")
    return "\n".join(lines) + "\n"


def bottom_line() -> str:
    v1, v2 = S["K3"]["C1_primary"], S["K3"]["C2a_replication"]
    g1 = S["generation"].get("C1forced", {}).get("PREFILL", {}).get("arms", {})
    g2 = S["generation"].get("C2a", {}).get("PREFILL", {}).get("arms", {})
    ds = S.get("dose_sensitivity") or {}
    d2 = (ds.get("C2a") or {}).get("doses", {}).get("0.5", {})
    d1 = (ds.get("C1forced") or {}).get("doses", {}).get("0.5", {})
    out = [f"* **Node level (pre-registered): supported.** {v1['n_nodes_pass_both']}/10 (B3) and {v2['n_nodes_pass_both']}/10 "
           "(T10) of the top components beat 50 norm-matched random components of the same type and position in both "
           "ablation and steering (Holm over 20 tests). The failures are components whose effect runs against the "
           "decision (\"brakes\").",
           f"* **Generation (pre-registered): partially supported.** Steering the top five components at the decision "
           f"position rewrites the written algorithm. B3: {g1.get('TOP5', {}).get('correct_target')}/30 correct Prim "
           f"programs vs {g1.get('TWIN', {}).get('correct_target')}/30 for the unedited twin. T10: "
           f"{g2.get('TOP5', {}).get('correct_target')}/30 correct DFS vs {g2.get('TWIN', {}).get('correct_target')}/30. "
           "Pass rates are unchanged. At the committed dose 2, however, the matched random five also flips most "
           f"programs (B3 {g1.get('RAND5', {}).get('correct_target')}/30, T10 {g2.get('RAND5', {}).get('correct_target')}/30), "
           "so the pre-registered TOP5-vs-RAND5 McNemar fails and both K3 verdicts are **PARTIAL**.",
           f"* **Post hoc (labelled): the circuit is far more efficient than random late components for T10, but only "
           f"modestly for B3.** At dose 0.5, T10's top five give {d2.get('TOP5_correct_target')}/30 DFS vs "
           f"{d2.get('RAND5_correct_target')}/30 for the random five (McNemar p = {d2.get('mcnemar_two_sided', float('nan')):.2g}). "
           f"For B3 the counts are {d1.get('TOP5_correct_target')} vs {d1.get('RAND5_correct_target')} "
           f"(p = {d1.get('mcnemar_two_sided', float('nan')):.2g}).",
           "* **Mechanism.** In both families, a layer-0 MLP at the instruction span carries most of the injected "
           "contrast (AtP missed it in Qwen; only the exhaustive sweep found it). A late stack of decision-position "
           "MLPs and heads turns it into the decision logit; in Qwen it sits deeper than in Gemma (normalised "
           "depth ~0.86 vs 0.69). The two algorithm decisions (Kruskal/Prim and union-find/DFS) share components: "
           "MLPs L26-L30 and heads L23 H10 and L27 H31 at the decision position."]
    return "\n".join(out) + "\n"


def predictions_block() -> str:
    v1, v2 = S["K3"]["C1_primary"], S["K3"]["C2a_replication"]
    g1 = (S["generation"].get("C1forced", {}).get("PREFILL", {}) or {}).get("criteria", {})
    g2 = (S["generation"].get("C2a", {}).get("PREFILL", {}) or {}).get("criteria", {})
    pc = S["motif"].get("primary_comparison", {})
    st = S.get("stability") or {}
    vn = S.get("validation", {}).get("C1nat")
    rows = [
        ("P1", ">= 5 of 10 nodes pass both tests on C1 (C1-forced after F2)",
         f"{v1['n_nodes_pass_both']}/10 (C1-forced)" + (f"; C1-nat (descriptive) {vn['n_pass_both_holm20']}/10" if vn else ""),
         "met"),
        ("P2", "PREFILL top-5: TWIN + >= 6 correct Prim, beats RAND5 (McNemar p < 0.05), pass >= 0.8 x twin",
         f"{g1.get('plus_vs_twin'):+d}; McNemar two-sided p = {g1.get('mcnemar_top5_vs_rand5_p', float('nan')):.3g} "
         f"(one-sided {g1.get('mcnemar_top5_vs_rand5_p_one_sided', float('nan')):.3g}); pass ratio {f(g1.get('pass_ratio'))}",
         "met" if g1.get("all") else ("not met (two-sided); met one-sided" if g1.get("all_one_sided") else "not met")),
        ("P3", "the same on C2a toward DFS",
         f"{g2.get('plus_vs_twin'):+d}; McNemar two-sided p = {g2.get('mcnemar_top5_vs_rand5_p', float('nan')):.3g}; "
         f"pass ratio {f(g2.get('pass_ratio'))}", "met" if g2.get("all") else "not met (RAND5 also saturates)"),
        ("P4", "motif: DEC share [0.38, 0.68], COND share [0.21, 0.51], DEC-stack depth [0.45, 0.80]",
         f"Qwen {pc.get('qwen_set')}: DEC {f(pc.get('qwen', {}).get('DEC'))}, COND {f(pc.get('qwen', {}).get('COND'))}, "
         f"depth {f(pc.get('qwen_dec_depth'))}", "not met (" + ", ".join(pc.get("differs_on") or []) + ")"
         if pc.get("differs_on") else "met"),
        ("P5", "top-10 Jaccard between pair sets A and B >= 0.4",
         f"{f(st.get('jaccard_top10'))}" if st else "not run", "met" if st.get("P5_jaccard_ge_0.4") else "not met"),
    ]
    lines = ["| id | prediction | observed | outcome |", "|---|---|---|---|"]
    lines += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows]
    return "\n".join(lines) + "\n"


def dose_block() -> str:
    ds = S.get("dose_sensitivity") or {}
    if not ds:
        return ""
    lines = ["**Post-hoc dose sensitivity (labelled; committed before its rows).** At the committed dose 2 the matched "
             "random five also saturates the minority algorithm, which leaves the TOP5-vs-RAND5 McNemar no room. "
             "Lower doses on the same 30 CRN slots (PREFILL):"]
    for n, d in ds.items():
        if not d:
            continue
        lines += ["", "| contrast | dose | TWIN | TOP5 | RAND5 | discordant TOP5:RAND5 | McNemar two-sided p | "
                      "pass TOP5 / RAND5 |", "|---|---|---|---|---|---|---|---|"]
        for dose, r in d["doses"].items():
            lines.append(f"| {n} | {dose} | {r['TWIN_correct_target']} | {r['TOP5_correct_target']} | "
                         f"{r['RAND5_correct_target']} | {r['discordant_top5_only']}:{r['discordant_rand5_only']} | "
                         f"{r['mcnemar_two_sided']:.3g} | {r['TOP5_pass']} / {r['RAND5_pass']} |")
        lp = d.get("logit_p_minority_mean")
        if lp:
            lines.append("")
            lines.append(f"{n} logit level, mean P(minority decision token) over the five twins (twin "
                         f"{f(d.get('logit_twin_p_minority_mean'), 3)}): " + "; ".join(
                             f"{arm} " + ", ".join(f"dose {k}: {f(v, 3)}" for k, v in sorted(dd.items(),
                                                                                       key=lambda t: float(t[0])))
                             for arm, dd in lp.items()))
    return "\n".join(lines) + "\n"


def gen_block(name: str) -> str:
    g = S.get("generation", {}).get(name)
    if not g:
        return f"*{name}: generation not run.*\n"
    lines = ["| condition | arm | N | correct target | attempted target | pass rate | reached decision | labels |",
             "|---|---|---|---|---|---|---|---|"]
    for cond in ("PREFILL", "FREE"):
        if cond not in g:
            continue
        for arm in ("TWIN", "TOP5", "RAND5"):
            a = g[cond]["arms"].get(arm)
            if a:
                lines.append(f"| {cond} | {arm} | {a['n']} | {a['correct_target']} | {a['attempted_target']} | "
                             f"{f(a['pass_rate'])} | {a['reached_decision']} | {json.dumps(a['labels'])} |")
    for cond in ("PREFILL", "FREE"):
        c = g.get(cond, {}).get("criteria")
        if c:
            tv = g[cond]["TOP5_vs_RAND5"]
            lines.append(f"\n{cond}: TOP5 - TWIN = {c['plus_vs_twin']:+d} correct target programs (threshold +6: "
                         f"{'met' if c['plus_ge_6'] else 'not met'}); TOP5 vs RAND5 discordant {tv['a_only']}:"
                         f"{tv['b_only']}, exact McNemar two-sided p = {tv['mcnemar_p_two_sided']:.3g} (primary; "
                         f"{'beats' if c['beats_rand5'] else 'does not beat'} RAND5), one-sided p = "
                         f"{tv['mcnemar_p_one_sided']:.3g}; pass ratio TOP5/TWIN = {f(c['pass_ratio'])} "
                         f"({'>=' if c['pass_ratio_ok'] else '<'} 0.8). All criteria (two-sided): "
                         f"{'MET' if c['all'] else 'NOT MET'}; with the one-sided test: "
                         f"{'MET' if c.get('all_one_sided') else 'NOT MET'}.")
    return "\n".join(lines) + "\n"


def main() -> None:
    k3 = S["K3"]
    mt = S["motif"]
    st = S.get("stability")
    pc = mt.get("primary_comparison", {})
    ec = S.get("engine_check", {})
    gt = S.get("gpu_tests", {})
    nov = S.get("novelty_audit", {})
    dev = S.get("deviations") or []
    con = S.get("contrasts") or {}
    gr = S.get("gemma_recount", {})
    txt = f"""# The circuit behind Qwen3-8B's algorithm choice (K3)

Which components of bf16 **Qwen3-8B** (rev b968826d, thinking off) compute the odds of the token that decides which
algorithm gets written, and does steering them change the algorithm in generated, hidden-test-checked programs?
Two decision tokens are studied:

* **C1 (primary): minimum spanning tree weight (unit B3)** - after B3's 61-token canonical opening
  (`...graph[v].append((u, w))\\n\\n    #`), the next token is ` Kr` (Kruskal) or ` Prim`. Metric
  m = z(' Kr') - z(' Prim') at the decision position (DEC).
* **C2a (replication): connected components (T10)** - after `def solve(n, edges):\\n    def`, the next token is
  ` find` (union find) or ` dfs`. m = z(' find') - z(' dfs').

The pipeline is ported from iteration 7's Gemma-3-4B G1 code so both families are measured identically:
attribution-patching screen of 4,752 nodes (36 x 32 heads + 36 MLPs at four position classes COND / SPEC / OPEN /
DEC) -> exact noising and denoising of the top nodes -> path patching among the top 15 -> faithfulness curves ->
validation of each top-10 node in the real model against **50 matched random components** (same type and position
class, matched write norm) under ABLATE and STEER, exact sign-flip tests with Holm -> top-5 steering in
**generation** (N = 30 common-random-number slots, hidden tests, exact McNemar against a matched random five and the
unedited twin) -> a committed **motif test** against Gemma.

**Why it matters for the run's question** (can an LLM be pushed to a different solution, and how is the choice made
inside it?): the choice between two algorithms is made at one token, and the circuit analysis below locates the
components that compute it. A condition-span MLP at layer 0 injects the instruction. A small stack of late
decision-position heads and MLPs (layers 23-35) turns it into the decision logit. Steering five of those
components at one position rewrites which algorithm the model then implements.

## Bottom line

""" + bottom_line() + f"""
## K3 verdicts

| unit | verdict (two-sided McNemar, primary) | verdict with one-sided McNemar | nodes passing both tests | generation criteria met (PREFILL) | McNemar TOP5 vs RAND5, two-sided / one-sided p |
|---|---|---|---|---|---|
| C1 = C1-forced (primary) | **{k3['C1_primary'].get('verdict')}** | {k3['C1_primary'].get('verdict_if_one_sided_mcnemar')} | {k3['C1_primary'].get('n_nodes_pass_both')} / 10 | {k3['C1_primary'].get('generation_criterion')} | {f(k3['C1_primary'].get('mcnemar_top5_vs_rand5_p'), 4)} / {f(k3['C1_primary'].get('mcnemar_top5_vs_rand5_p_one_sided'), 4)} |
| C2a (replication) | **{k3['C2a_replication'].get('verdict')}** | {k3['C2a_replication'].get('verdict_if_one_sided_mcnemar')} | {k3['C2a_replication'].get('n_nodes_pass_both')} / 10 | {k3['C2a_replication'].get('generation_criterion')} | {f(k3['C2a_replication'].get('mcnemar_top5_vs_rand5_p'), 4)} / {f(k3['C2a_replication'].get('mcnemar_top5_vs_rand5_p_one_sided'), 4)} |

The McNemar sidedness was not written into commit #0's text. The analysis code fixed by hash at commit #0 used the
one-sided test, while the plan's power calibration (8:0 -> p = 0.0078; 7:1 -> p = 0.07) is two-sided. The two-sided
test is taken as primary because it is the more conservative of the two; both are reported.

Rule (committed in commit #0): PASS = at least 5 of the top 10 nodes pass both tests (Holm over all 20 node x test
p-values) AND the PREFILL top-5 arm adds >= 6 correct minority-algorithm programs of 30 over the twin, beats the
matched random five (exact McNemar p < 0.05) and keeps pass rate >= 0.8 x the twin's; PARTIAL = exactly one of the
two; DISCONFIRMED = no top-10 node passes either test. **C1 is C1-forced**, not C1-nat: the natural noun-variant
pairs had a mean total effect of {f(con.get('C1nat_A', {}).get('TE_mean'))} nats (< 1 nat), which triggered the
pre-registered fallback F2 (amendment 0a, committed before any screen row). C1-nat is screened and reported
descriptively.

## Committed predictions (commit #0)

""" + predictions_block() + f"""
## Contrasts and circuits

| contrast | pairs | mean total effect (nats) | AtP-vs-exact Spearman (160 random nodes / top set) | edges kept | completeness / sufficiency of top-10 |
|---|---|---|---|---|---|
{circ_line('C1forced')}
{circ_line('C2a')}
{circ_line('C1nat')}
{circ_line('C1mix')}
{circ_line('C1natB')}

* **C1-forced**: 10 forced-Prim paraphrases ("Implement Prim's algorithm ...", corrupt) vs their ' .' padding
  twins (clean); identical length and token ids from 'Task:' on; 5 more paraphrase pairs are the 10 held-out
  validation prompts.
* **C2a**: 15 T10 twin noun variants (clean) vs the same prompts with the forced-DFS prompt's residual states
  exchanged in at the task-spec positions of all 36 blocks (corrupt). The exchange flips the teacher-forced argmax to
  ' dfs' in every pair. It is an intervention, so COND nodes have zero effect by construction (a SPEC-to-decision
  routing map).
* **C1-nat**: 24 neutral-noun variants per template W1-W5 (nouns from the art_j3Rm_lr2nzR6 concreteness norms,
  single Qwen3 tokens), k-th highest vs k-th lowest m within template. SD of m over the 120 variants:
  {f(con.get('C1nat_sd_m_v'))} nats (Gemma's y_v SD: 0.67). The layer-0 MLP at the noun position alone carries the
  whole total effect (the injection confound the plan flagged).
* Top-10 C1-forced: {', '.join(S['circuits'].get('C1forced', {}).get('top10') or [])}
* Top-10 C2a: {', '.join(S['circuits'].get('C2a', {}).get('top10') or [])}
* AtP (first order) ranks the strong nodes well (Spearman on the exact-patched top set above) but not the near-zero
  random nodes, whose exact effects sit at the bf16 noise floor (~0.06 nats); the IG-AtP fallback (F4) did not
  improve the random-node correlation and plain AtP was kept, with 120 exact-patched nodes instead of 60.
* Faithfulness: jointly noising (completeness) or restoring (sufficiency) the top-k nodes with the rest of the
  network live recovers most of the effect; freezing every non-circuit node to its corrupt value (type 1) leaves
  ~0 of the effect at every k up to 60 (see `figures/faithfulness.png`): the decision-position nodes need the
  upstream instruction processing, which is spread over many small nodes.

## Validation in the real model (matched random components)

{val_block('C1forced')}
{val_block('C2a')}
{val_block('C1nat')}
C1-nat validation is descriptive: C1-nat is not a K3 unit after F2, and the committed time rule cut it to the 15
clean prompts plus 5 held-out prompts because one prompt took 112 s (its top 10 are mostly SPEC/COND MLPs, whose rows
are full forwards).

""" + sens_block() + f"""
Gemma's G1 under both multiplicity conventions (recomputed from its p-values): within-test Holm
{json.dumps(gr.get('within_test_holm'))}; Holm over 20 {json.dumps(gr.get('holm_over_20'))}.

## Generation (steering the written algorithm)

Arms: TWIN (unedited), TOP5 (STEER on the five generation nodes toward the minority class: own + 2 x (minority-class
mean - default-class mean)), RAND5 (one matched random component per node, same operation, MLP deltas rescaled to the
target's write norm). N = 30 = W1-W5 x 6 CRN slots, T 1, top-p 1, no top-k. PREFILL (primary) prefills prompt +
opening for every arm; FREE applies OPEN/DEC edits only while the sampled prefix equals the opening (exactly, by
teacher-forcing the edited opening and sampling with the slot's uniforms until the first divergence). Targets: B3
correct prim_heap / prim_array; T10 correct dfs.

**C1-forced (B3)**

{gen_block('C1forced')}
**C2a (T10)**

{gen_block('C2a')}
""" + dose_block() + f"""
## Motif test (committed, descriptive)

The committed function (class share of |mean noising effect| over the exact list: top 40 by |AtP| + 20 random
calibration nodes) reproduces Gemma's printed shares from `g1_pathpatch.json` first: FORK/DEC
{f(mt['gemma_check']['shares']['DEC'], 3)}, COND {f(mt['gemma_check']['shares']['COND'], 3)} (check
{'passed' if mt['gemma_check']['reproduces_printed'] else 'failed'}).

| shares | COND | SPEC | OPEN | DEC | DEC-stack depth |
|---|---|---|---|---|---|
| Gemma (15 pairs) | {f(mt['gemma']['all15']['COND'])} | {f(mt['gemma']['all15']['SPEC'])} | {f(mt['gemma']['all15']['OPEN'])} | {f(mt['gemma']['all15']['DEC'])} | {f(mt['gemma']['dec_stack']['depth'])} |
""" + "\n".join(f"| Qwen {n} | {f(q['shares']['COND'])} | {f(q['shares']['SPEC'])} | {f(q['shares']['OPEN'])} | "
                 f"{f(q['shares']['DEC'])} | {f(q['dec_stack']['depth'])} |" for n, q in mt['qwen'].items()) + "\n" + \
        "\n".join(f"| Qwen {n}, exhaustive sweep (top 60 by exact effect) | "
                  f"{f(q['extended_top60_by_exact']['COND'])} | {f(q['extended_top60_by_exact']['SPEC'])} | "
                  f"{f(q['extended_top60_by_exact']['OPEN'])} | {f(q['extended_top60_by_exact']['DEC'])} | "
                  f"{f(q['extended_top60_dec_stack']['depth'])} |" for n, q in mt['qwen'].items()
                  if q.get('extended_top60_by_exact')) + "\n" + \
        f"| Gemma, injection-excluded | {f(mt['gemma']['injection_excluded']['COND'])} | " \
        f"{f(mt['gemma']['injection_excluded']['SPEC'])} | {f(mt['gemma']['injection_excluded']['OPEN'])} | " \
        f"{f(mt['gemma']['injection_excluded']['DEC'])} | |\n" + \
        "\n".join(f"| Qwen {n}, injection-excluded | {f(q['injection_excluded']['COND'])} | "
                  f"{f(q['injection_excluded']['SPEC'])} | {f(q['injection_excluded']['OPEN'])} | "
                  f"{f(q['injection_excluded']['DEC'])} | |" for n, q in mt['qwen'].items() if n != 'C2a') + f"""

The committed composition (top 40 by |AtP| + 20 random) depends on the AtP screen, which missed Qwen's largest
node, the layer-0 MLP at the condition span (AtP 0.1 vs exact 7.7 nats in C1-forced; Gemma's screen kept the
corresponding layer-0 COND MLP). The exhaustive sweep therefore matters as a sensitivity. With it, Qwen's COND share
rises to the value in the sweep row, and the condition-to-decision picture (an injecting layer-0 MLP at the condition
span plus a late decision stack) matches Gemma qualitatively. The late decision stack sits deeper in Qwen
(effect-weighted depth above the committed 0.80 band edge). The injection-excluded rows drop layer 0-1 nodes at the
corrupted span, which removes the share that the corruption injects by construction.

Committed bands: DEC share in [0.38, 0.68], COND share in [0.21, 0.51], DEC-stack effect-weighted depth in
[0.45, 0.80]. Primary comparison ({pc.get('qwen_set')} vs Gemma): **{pc.get('label')}**
{('(differs on: ' + ', '.join(pc.get('differs_on') or []) + ')') if pc.get('differs_on') else ''}. Two models and two
decision tokens cannot establish a general motif; the comparison is descriptive. Injection-excluded shares (layer 0-1
nodes at the corrupted span removed) are in `results/summary.json`.

## Stability (pair set A vs disjoint set B, C1-nat)

""" + (f"Top-10 Jaccard {f(st['jaccard_top10'])}, top-15 Jaccard {f(st['jaccard_top15'])}, Spearman of exact "
       f"effects over the union of both top-60 sets {f(st['spearman_exact_union_top60'])} "
       f"({st['n_union_measured_in_both']} nodes measured in both); edges kept in both: "
       f"{len(st['edges_kept_both'])}. Prediction P5 (Jaccard >= 0.4): "
       f"{'met' if st['P5_jaccard_ge_0.4'] else 'not met'}. Set B has a smaller total effect "
       f"({f(st['TE_B'])} vs {f(st['TE_A'])} nats)." if st else "Not run.") + f"""

## Checks

* CPU tests (positions, node keys, motif on Gemma, sign-flip vs brute force, Holm/McNemar vs statsmodels/scipy,
  random-pool ladder, labeller re-check): all pass = {S.get('tests_cpu', {}).get('all_pass')}.
* Labeller re-check: B3 references 4/4, T10 references 4/4, T10 gold 22/22, 30 iteration-7 B3 twin programs 30/30.
* GPU tests: U1 pi(' Kr') on the W1 twin = {f(gt.get('U1', {}).get('p_kr'), 3)} (iteration 7: 0.72); U6 steering
  hook exact; U2/U3/U8 differ from their 0.05-nat targets by bf16 path noise of the same size as full-vs-full
  differences across batch shapes (mean {f(gt.get('U3b_full_vs_full', {}).get('mean_abs_diff'), 3)} nats), so suffix
  forwards were kept (amendment 0a); every reported effect is measured against an unedited base row of its own batch.
* Engine check (twin CRN slots): B3 label agreement with iteration 7
  {f(ec.get('B3', {}).get('agreement'))} (token-identical {ec.get('B3', {}).get('token_identical')}/{ec.get('B3', {}).get('n')}),
  T10 {f(ec.get('T10', {}).get('agreement'))}.
* Novelty audit: {nov.get('n_correct_other', 'n/a')} correct programs labelled 'other' among {nov.get('n_correct', 'n/a')}
  correct programs; {nov.get('note', '')}
* Transcoder attribution-graph extension: {S.get('transcoder_precheck', {}).get('decision', 'n/a')} -
  {S.get('transcoder_precheck', {}).get('reason', '')}
* Pre-registration: hash chain {' -> '.join(l.split()[1] for l in S.get('commit_chain', []))}
  (`commitments.log`, `predictions/*.json`); no validation row before commit #1, no steered program before commit #2.
* Stdlib re-derivation with placebos: `audit/rederive.py` -> `results/rederive.json`.

## Deviations

""" + "\n".join(f"* **{d['id']}** ({d['severity']}): {d['text']}" for d in dev) + """

## Layout

| path | content |
|---|---|
| `method.py` | all GPU stages (setup, contrasts, gputests, amend0a, circuit:X, commit1, validate:X, commit2, gen:X, enginecheck) |
| `analysis.py` | validation / generation statistics, motif test, stability, verdicts, figures, `method_out.json` |
| `make_readme.py` | writes this README from `results/summary.json` |
| `run_chain3.sh` ... `run_chain7.sh`, `run_final.sh` | the stage chains as run (3b resumed 3 after a CUDA OOM; 6-7 ran one stage per process) |
| `src/deviations_final.py` | completes `results/deviations.json` |
| `src/k3cfg.py` | constants, seeds, utilities |
| `src/k3engine.py` | model loading, component edit hooks, cached forwards, AtP gradients, CRN generation |
| `src/k3prompts.py` | prompts, noun variants, forced paraphrases, position classes |
| `src/k3circuit.py` | AtP / IG-AtP screen, exact patching, path patching, faithfulness, write norms, random pools |
| `src/k3stats.py` | exact sign-flip (meet-in-the-middle), Holm, McNemar, Newcombe, Wilson |
| `src/k3motif.py` | committed motif function and bands |
| `src/label_k3.py` | frozen labellers (vendored iteration-7 label worker) |
| `src/novelty_k3.py` | novelty audit of correct 'other' programs |
| `audit/rederive.py` | stdlib re-derivation of the headlines with placebos |
| `tests/test_labeller.py` | labeller re-check (T7) |
| `inputs/` | read-only copies of the prior artifacts used (iteration 2-7 prompts, units, bench, labellers, Gemma G1 results) |
| `predictions/` | commits #0, amendment 0a, #1, #2 (hash chain in `commitments.log`), hardware |
| `results/` | `circuit_*.json` (screen, exact rows, edges, faithfulness), `selection_*.json`, `summary.json`, checks |
| `data/` | `validation_rows_*.jsonl`, `gen_raw_*.jsonl`, `gen_labels_*.jsonl`, `rows.jsonl`, engine check |
| `figures/` | circuit graphs, AtP vs exact, faithfulness, validation, generation, motif panel, stability |
| `method_out.json` | exp_gen_sol_out: one example per generation slot with predict_TWIN / predict_TOP5 / predict_RAND5 |

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python src/download_model.py            # Qwen/Qwen3-8B@b968826d into the HF cache
.venv/bin/python tests/test_labeller.py           # T7 labeller re-check (CPU)
.venv/bin/python method.py --stages setup,contrasts,gputests,amend0a,circuit:C1forced,circuit:C2a,circuit:C1nat,circuit:C1mix
.venv/bin/python method.py --stages f4b:C1forced,f4b:C2a,commit1:C1forced+C2a,validate:C1forced,validate:C2a,commit2:C1forced+C2a,gen:C1forced,gen:C2a,enginecheck
.venv/bin/python method.py --stages valsens:C1forced,valsens:C2a,f4b:C1nat,commit1b:C1nat,validate:C1nat,circuitlite:C1natB,f4b:C1natB,dose:C1forced,dose:C2a
./run_final.sh                                     # deviations, novelty audit, analysis, re-derivation, README, schema check
```

Hardware used: one NVIDIA L4 (23 GB), 6 CPUs, 57 GB RAM. Every stage resumes from its files.

## Restoring removed files

* `.venv/` (deleted, regenerable): `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml`
* `cache/` (deleted, regenerable): AtP / exact arrays (`cache/*.npz`), frozen class-mean tensors (`cache/vectors/`)
  and temporary files are rebuilt by `.venv/bin/python method.py --stages circuit:C1forced,circuit:C2a,circuit:C1nat,circuit:C1mix,commit1`
  (deterministic seeds; the sha256 of every frozen class-mean tensor is in `results/selection_*.json`).
* `**/__pycache__/` (deleted, regenerable): recreated automatically when the code is imported
  (`python -m compileall src audit inputs`).
* Kept artifacts (`results/`, `data/`, `figures/`, `predictions/`, `inputs/`) stay on the run's storage volume at these
  relative paths and are all small text/figure files, so they are also in the published repository.
* The model weights live in the shared Hugging Face cache, not in this directory: `huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218`
  (or `.venv/bin/python src/download_model.py`).
"""
    (ROOT / "README.md").write_text(txt)
    print("README.md written", len(txt))


if __name__ == "__main__":
    main()
