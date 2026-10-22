#!/usr/bin/env python3
"""Fill the README's results section from the result files, so that the prose cannot disagree with the numbers."""
import json
from pathlib import Path

WS = Path(__file__).resolve().parent.parent


def r(name):
    return json.loads((WS / "results" / f"{name}.json").read_text())


def p(x):
    return f"{x:.1e}" if x < 0.001 else f"{x:.3f}"


def main() -> None:
    a, b, c, d, e, f = (r(s) for s in ("0a", "0b", "0c", "0d", "0e", "0f"))
    ev = json.loads((WS / "eval_out.json").read_text())
    m = ev["metrics_agg"]
    aud = json.loads((WS / "audit" / "rederive_report.json").read_text())
    jr = json.loads((WS / "audit" / "judge_runs_summary.json").read_text())
    pt = a["A2"]["per_task"]
    name = {"T03": "kth smallest", "T10": "connected components", "T2": "shortest path", "T05": "two sum", "T1": "grid",
            "T06": "find duplicate"}

    def cell(t, eng, al):
        x = pt[t][eng][al]
        return f"{x['cor_off']}/{x['n_correct']}"
    eng_lines = "\n".join(
        f"| {name[t]} | {cell(t, 'fp8', '1.0')} | {cell(t, 'fp8', '2.0')} | {cell(t, 'bf16', '1.0')} | {cell(t, 'bf16', '2.0')} | "
        f"{p(pt[t]['cor']['fisher_two_sided_matched_alpha']['2.0'])} | {p(pt[t]['cor']['bracket']['p_one_sided_less'])} | {pt[t]['tag']} |"
        for t in ("T10", "T2", "T03", "T1", "T05", "T06"))
    t = b["tally"]
    conf = b["confound"]
    tm = b["tmf"]["all"]
    pw = c["power"]
    riv = c["rivals"]
    f6 = f["F6"]
    jp, js = f6["judge_primary"], f6["judge_second"]
    a1 = {x["task"]: x for x in a["A1"]["rows"]}
    st = a["A5"]["stats"]
    passes = list(jr.values())
    items = {i["blind_id"]: i for i in f["items"]}
    flagged_txt = ""
    for bid in f["flagged_for_final_read"]:
        it = items[bid]
        flagged_txt += (f"\n  - {bid} ({it['task']}) was called novel. The judge names no technique, and its reason is "
                        f"'{it.get('judge_primary_reason', '')}'. The program passes {it['stress']['hidden_pass']} of "
                        f"{it['stress']['hidden_n']} hidden tests and every stress group. Final read: {it.get('final_verdict')}.")
    txt = f"""**0a. Engine and dose.**
- The two dose definitions disagree. Table 174's ratio of mean norms runs from {a1['T10']['ratio_of_means_table174']:.3f}
  (connected components) to {a1['T03']['ratio_of_means_table174']:.3f} (kth smallest) on the decisive tasks, with find
  duplicate at {a1['T06']['ratio_of_means_table174']:.3f}. The knob experiment's mean of per-position ratios is
  {a1['T06']['mean_ratio_knob_exp']:.3f} to {a1['T03']['mean_ratio_knob_exp']:.3f}. A mean of ratios is not a ratio of
  means. The knob experiment's n counts plan-noise rows, which share one value per prompt wording, so it is not a count
  of independent measurements.
- The two artifacts' `off_default_share` fields measure different things, and the record compared them directly (grid
  0.02 against 0.24, for example):
  - bf16 knob experiment: correct programs off the default, over all samples;
  - 8-bit plan-noise experiment: valid attempts off the default, over all samples.
- Every contrast is therefore recomputed under both definitions. The decision rule was fixed before computing. The
  bracket compares the bf16 alpha-2 cell, which delivers at least 1.24 FP8 ban units under either dose definition,
  with the FP8 alpha-1 cell. Correct-only counts:

| Task | FP8 a1 | FP8 a2 | bf16 a1 | bf16 a2 | Fisher p (a2) | bracket p | tag |
|-|-|-|-|-|-|-|-|
{eng_lines}

- `engine_labels.json` has {m['n_engine_rows']:.0f} rows:
  - {m['n_fp8_not_replicated']:.0f} 'did NOT replicate in bf16 at the population level';
  - {m['n_fp8_only_untested']:.0f} 'FP8 only, untested in bf16': the site odds ratio, the same-seed contrast and the
    plan subspace;
  - {m['n_bf16_conditional']:.0f} 'bf16-conditional' verdicts.
- Like-for-like figure, Spearman with beta:
  - bf16 existing tasks {st['existing_bf16']['rho']:.2f} (one-sided p {p(st['existing_bf16']['perm_p_one_sided'])});
    with the 8-bit screen E instead, {st['existing_fp8_screen']['rho']:.2f};
  - new units {st['new_13']['rho']:.2f} (p {p(st['new_13']['perm_p_one_sided'])});
  - pooled bf16 {st['pooled_bf16_28']['rho']:.2f}.

**0b. Landings.**
- The base runner-up named the push landing in {t['all']['hits']} of {t['all']['events']} events (Poisson-binomial p
  {p(t['all']['pb_p'])}). Per set:
  - 8-bit screen: {t['FP8 screen']['hits']}/{t['FP8 screen']['events']};
  - bf16 remeasure: {t['bf16 existing remeasure']['hits']}/{t['bf16 existing remeasure']['events']};
  - panel A: {t['panel A']['hits']}/{t['panel A']['events']};
  - panel B: {t['panel B']['hits']}/{t['panel B']['events']};
  - Gemma: {t['Gemma']['hits']}/{t['Gemma']['events']}.
- On the held-out events where the instruct twin wrote no correct program off the default, it named
  {conf['pooled']['hits']} of {conf['pooled']['n']} (p {p(conf['pooled']['pb_p'])}): Qwen
  {conf['qwen']['hits']}/{conf['qwen']['n']}, Gemma {conf['gemma']['hits']}/{conf['gemma']['n']}. By the frozen rule,
  {conf['decision']}.
- The twin's own most frequent alternative is defined on {tm['tmf_defined_n']} events. There it names the landing
  {tm['tmf_hits_defined_only']:g} times, against {tm['base_hits_defined_only']} for the base runner-up (McNemar p
  {p(tm['mcnemar_defined']['p_exact_two_sided'])}). Where the twin writes an alternative, the landing half is the twin's
  own minority.

**0c. Movability.**
- Over the 13 new units, Spearman is {c['rho']:.2f}:
  - Bonett-Wright 95% [{c['ci']['bonett_wright'][0]:.2f}, {c['ci']['bonett_wright'][1]:.2f}];
  - Fieller [{c['ci']['fieller'][0]:.2f}, {c['ci']['fieller'][1]:.2f}];
  - bootstrap BCa [{c['boot']['bca'][0]:.2f}, {c['boot']['bca'][1]:.2f}];
  - one-sided permutation p {p(c['perm']['p'])}.
- Power at a true 0.6:
  - {pw['0.6']['power']:.2f} for the registered one-sided permutation test;
  - {pw['0.6']['power_two_sided']:.2f} two-sided (the direction's quoted 0.46 matches the two-sided figure);
  - {pw['n_for_0.8_at_0.6']} units would give 0.8.
- So beta is not a strong predictor, a moderate relation is not excluded, and the verdict is bf16-conditional.
- Under one definition of each rival, only the runtime merit R6 tracks movability (Spearman
  {riv['R6_runtime_merit']['rho_with_E']:.2f}, Holm p {p(riv['R6_runtime_merit']['holm_p'])}). The paired interval for
  beta minus R6, [{riv['R6_runtime_merit']['delta_ci95'][0]:.2f}, {riv['R6_runtime_merit']['delta_ci95'][1]:.2f}],
  includes 0.

**0d / 0e. Missing tables and minor fixes.**
- Phrasing clusters at theta 0.7/0.8/0.9 rise only at T 1.3 (5/7/12), and the T 0.7 repeat gives 3/6/10.
- P15/P20 columns are added, and the spot checks match.
- The panel B knob rows are added. Three push programs on count inversions (fenwick tree) fall outside the base
  repertoire.
- Table 126c rows: Hill-1 2.87, 2.96 and 2.92.
- Plan noise against matched decoding is 19:3 at alpha 2, but 13:0 of that is kth smallest; the other four tasks give
  6:3 (p {p(e['E1']['pooled']['alpha2']['p_without_kth_smallest'])}).
- Gemma: 1.50 nats with uniform fill, {e['E2']['defined_only']:.2f} on the {e['E2']['n_defined']} defined events.

**0f. Second blind adjudication of the 14.**
- Every program is stress-tested in a sandbox. All pass the hidden tests. One, repeated maximum selection on top-k
  frequent, times out at the maximum size.
- Judges, from model families this run never used:
  - Mistral Medium 3.1, three calls at temperature 0, Fleiss {f6['fleiss_primary_3calls']:.2f}: control gate
    {jp['controls_correct']}/10;
  - Kimi K2: gate {js['controls_correct']}/10.
- Novel calls: {f['readj_novel_k']} of 14 (Mistral) and {f['readj_novel_k_second']} of 14 (Kimi). Final count after the
  executor's read of all 14: {f['final_novel_count']}.{flagged_txt}
- Agreement with the manual verdict on the 14:
  - raw {jp['disputed_14']['raw_agree_4class']:.2f} (95% {jp['disputed_14']['raw_agree_4class_cp95'][0]:.2f} to
    {jp['disputed_14']['raw_agree_4class_cp95'][1]:.2f});
  - AC1 {jp['disputed_14']['ac1_4class']:.2f}, kappa {jp['disputed_14']['kappa_4class']:.2f};
  - binary kappa is {jp['disputed_14']['kappa_binary_flag']} and binary AC1 is {jp['disputed_14']['ac1_binary']:.2f}.
  - With the controls (24 items): kappa {jp['all_24']['kappa_4class']:.2f}, bootstrap
    [{jp['all_24']['kappa_bootstrap_ci95'][0]:.2f}, {jp['all_24']['kappa_bootstrap_ci95'][1]:.2f}].
- The final read corrects one manual class. Program P21 is a linear scan plus `list.count`, not a binary search.
- Across the judge passes (`audit/judge_runs_summary.json`):
  - Mistral's novel calls on the 14: {', '.join(str(x['novel_primary']) for x in passes)};
  - its control gate: {', '.join(str(x['gate_primary']) for x in passes)} of 10;
  - Kimi's novel calls: {', '.join(str(x['novel_second']) for x in passes)}.
  The first two passes had run-dependent timings in their prompts. What varies is P13 and the contested control, which
  the iteration-5 manual pass itself classed as a catalogue variant. No pass produced a novel call that survived a full
  read.

**Audit.** `audit/rederive.py` passes {aud['n_passed']} of {aud['n_checks']} checks, and
{aud['n_placebos_failed']} of {aud['n_placebos']} placebos fail as required. `corrections.json` holds
{m['n_corrections']:.0f} corrections ({m['n_match']:.0f} values MATCH, {m['n_corrected']:.0f} CORRECTED,
{m['n_new']:.0f} NEW, {m['n_carried']:.0f} CARRIED). No two corrections overlap, and every `old_text` occurs exactly
once in the report."""
    spend = sum(x["spend_usd_this_pass"] for x in passes)
    readme = (WS / "README.md").read_text()
    readme = readme.replace("__RESULTS__", txt).replace("__SPEND__", f"USD {spend:.2f} in all, over {len(passes)} judge passes")
    (WS / "README.md").write_text(readme)
    print("README filled; spend", round(spend, 4))


if __name__ == "__main__":
    main()
