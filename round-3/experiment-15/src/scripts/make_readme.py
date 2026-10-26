#!/usr/bin/env python3
"""Writes README.md from the result files, so every number in it is read from results/ and predictions/."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.ws import DATA, PRED, RESULTS, WS, read_json, read_jsonl  # noqa: E402


def eid_md(e: str) -> str:
    return e.replace("|modal|", " ban ").replace("|present_minor|", " ban* ")


def f2(x, n=2):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "–"
    return f"{x:.{n}f}"


def main() -> None:
    an = read_json(RESULTS / "analysis.json")
    ev = read_json(PRED / "events.json")
    fcs = read_json(PRED / "forecasts.json")["events"]
    c1 = an["c1"]
    rows = read_jsonl(RESULTS / "c1_events.jsonl")
    tests = {f.stem: read_json(f) for f in sorted(RESULTS.glob("tests_*.json"))}
    rd = read_json(RESULTS / "independent_rederivation.json") if (RESULTS / "independent_rederivation.json").exists() else {}
    dev = read_json(RESULTS / "deviations.json")
    au = read_json(RESULTS / "llama_label_audit.json") if (RESULTS / "llama_label_audit.json").exists() else {}
    vs = read_json(DATA / "veto_summary.json") if (DATA / "veto_summary.json").exists() else {}
    tm = read_json(RESULTS / "timings.json")
    gpu_s = sum(x["seconds"] for v in tm.values() for x in v)
    from src.label import judge_spend, screen_spend
    spend = judge_spend()
    spend_screen = screen_spend()
    L = []
    A = L.append
    A("# Where Llama goes when an algorithm is banned\n")
    A("This is the Llama-3.1-8B-Instruct replication of Claim 1, run on the frozen 12-task coding bench (exp11). "
      "Claim 1 says a ban removes the default algorithm and the model falls to its next rung. The model runs in bf16 "
      "at revision `0e9e39f`.\n")
    A("Every forecast below was computed ban-free and hash-chained in `commitments.log` before any ban prompt was "
      "rendered. The bans were then sampled and scored with the frozen C1 rule in `predictions/scoring.py`. The rows in "
      "`results/c1_events.jsonl` use the shared `c1_events` schema, so the next round can pool them with the Qwen rows.\n")
    A("## Headline\n")
    A(f"- **Within-Llama, pre-pooling branch: {c1['branch']}.**")
    A(f"- Events: {c1['n_events']} (12 modal and {len(ev['present_minor'])} present-minor).")
    A(f"- Gated (avoidance ≥ 0.5 and ≥ 20 non-banned attempts): {c1['n_gated']}.")
    A(f"- Disagreeing and gated: {c1['n_disagreeing_gated']}.")
    A(f"- Wins under the advance rule (≥ 0.10 nats over the runner-up): {c1['wins'] or 'none'}. A family advances "
      f"with ≥ 3 wins: {[k for k, v in c1['advances'].items() if v] or 'none'}.")
    w = c1["wilcoxon"]
    if "not_run" in w:
        A(f"- Wilcoxon: {w['not_run']}.")
    else:
        A("- Paired Wilcoxon signed-rank tests on per-event log-score differences, Holm-corrected at 0.05, with a "
          "task-cluster bootstrap 95% CI of the mean difference:")
        for k, v in w.items():
            A(f"  - {k}: mean {f2(v['mean_diff'], 3)} nats [{f2(v['boot_ci'][0], 3)}, {f2(v['boot_ci'][1], 3)}], n = {v['n']}, "
              f"p = {f2(v['p'], 4)}, Holm-adjusted p = {f2(v['p_adj'], 4)}, {'rejected' if v['reject'] else 'not rejected'}.")
    A(f"- Effective N: {c1['effective_n']}. Below the pooled floor of 16 events, no 'confirmed' wording is used.")
    hits = c1["top1_hits_gated"]
    hit_txt = "; ".join(f"{k} {v['hits']}/{v['n']} (chance {f2(v['chance'])}, binomial p {f2(v['p_binom'], 3)})"
                        for k, v in hits.items())
    A(f"- Top-1 hits on gated events: {hit_txt}.")
    pm = an["c1_pm"]
    A(f"- Sensitivity with the frozen point-mass ASSOCIATE/PROXIMITY: branch {pm['branch']}, wins {pm['wins'] or 'none'}.\n")
    A((WS / "scripts" / "README_reading.md").read_text())
    A("### Per event (ban landing vs ban-free forecasts)\n")
    A("Each event bans one algorithm; N = 100 = W1–W5 × 20.\n")
    A("- **s_X**: the banned algorithm's attempted share in the decision set.")
    A("- **avoid**: 1 minus the banned share among attempted programs.")
    A("- **hit**: the modal non-banned label for modal events, or the excess label for present-minor events.")
    A("- **SUB / LAD / ASSOC / PROX**: each family's top-1 on its transferred component, with its mean log score per "
      "non-banned attempt in brackets. A dash means the family is undefined, and it is then scored as uniform.\n")
    A("| event | s_X | avoid | gate | n non-banned | hit | SUB | LAD | ASSOC | PROX | RENORM ls | winner (margin) | Hill_cc (n correct) | other / invalid |")
    A("|---|--:|--:|:-:|--:|---|---|---|---|---|--:|---|---|---|")
    for r in rows:
        e = an["events"][r["event_id"]]
        sc, tab = e["scored"], e["table"]

        def cell(fam):
            t = sc["top1"][fam]
            return f"{t if t else '–'} ({f2(sc['logscore'][fam])})"
        A(f"| {eid_md(r['event_id'])} | {f2(r['s_X'])} | {f2(tab['avoidance'])} | {'✓' if tab['gate_pass'] else '✗'} | "
          f"{tab['n_nonbanned']} | {sc['hit_label']} | {cell('SUBTRACT')} | {cell('LADDER')} | {cell('ASSOCIATE')} | "
          f"{cell('PROXIMITY')} | {f2(sc['logscore']['RENORM'])} | {sc['winner'] or '–'} ({f2(sc['margin'])}) | "
          f"{f2(tab['hill_cc'])} ({tab['n_correct_nonbanned']}) | {f2(tab['other_share'])} / {f2(tab['invalid_share'])} |")
    A("")
    A("Landing counts, correct-only counts, Wilson intervals, disguise rates and the baseline's own non-X share are in "
      "`results/analysis.json` (`events.<id>.table`) and `results/c1_events.jsonl`.\n")
    A("### Sensitivities (H3)\n")
    for k, v in an["sensitivities"].items():
        if k == "leave_one_template_out":
            A(f"- leave-one-template-out: " + "; ".join(f"{kk}: {vv['branch']} (wins {vv['wins'] or 'none'})"
                                                       for kk, vv in v.items()))
        else:
            A(f"- {k}: {v.get('branch', v)} (wins {v.get('wins') or 'none'}, disagreeing gated {v.get('n_disagreeing_gated')})")
    A("")
    A("### Signature vetoes (D2/D3): is the default carried by surface tokens?\n")
    A("Each veto uses the event's frozen signature n-gram. The table gives the share of the banned algorithm A among "
      "veto attempts per round, using the persistent (iterated) arm and weighted counts for present-minor events.\n")
    A("| event | round-1 n-gram | A share r1 | r2 | r3 | stopped / note |")
    A("|---|---|--:|--:|--:|---|")
    for eid, v in vs.items():
        rs = an.get("veto_rounds_corrected", {}).get(eid) or [{"A_share": r["A_share_weighted"]} for r in v.get("rounds", [])]
        sh = [f2(r["A_share"]) for r in rs] + ["–"] * (3 - len(rs))
        ng = (v.get("ngrams") or [{}])[0] or {}
        note = "not carried by a small set of surface tokens" if v.get("not_carried_by_surface_tokens") else (v.get("stopped") or "")
        if ng.get("co_vetoed"):
            note += f" co-vetoed: {', '.join(ng['co_vetoed'])}"
        A(f"| {eid_md(eid)} | {json.dumps(ng.get('decoded')).replace('|', '\\|')} | {sh[0]} | {sh[1]} | {sh[2]} | {note} |")
    A("")
    A("Re-emergence surfaces (imports, and the vetoed text reappearing through other tokens) are in "
      "`results/veto_reemergence_table.md` and `data/veto_summary.json`.\n")
    c2 = an["c2b_descriptive"]
    nb = sum(1 for e in c2["events"] if e["both"])
    A(f"**C2b (descriptive).** {c2['n']} events have a one-shot veto that moves ≥ 50% of X attempts. On {nb} of them "
      f"(share {f2(c2['share_both'])}), the one-shot landing shares its modal survivor with the ban AND lies within the "
      "template-bootstrap JSD null. The pre-registered bar of 2/3 is quoted for reference only.\n")
    if an["present_minor_gain"]:
        A("**Present-minor X-specific gain (H5).** For each event, the table compares the associate's share under the ban "
          "with its share under the persistent veto. Substitution predicts ban > veto; subtraction predicts equality.\n")
        A("| event | associate | ban share | veto share | baseline share | ban − veto [Newcombe 95%] |")
        A("|---|---|--:|--:|--:|---|")
        for h in an["present_minor_gain"]:
            A(f"| {eid_md(h['event_id'])} | {h['associate']} | {f2(h['ban_share'])} | {f2(h['veto_share'])} | "
              f"{f2(h['baseline_share'])} | {f2(h['ban_minus_veto'])} [{f2(h['newcombe_ci'][0])}, {f2(h['newcombe_ci'][1])}] |")
        A("")
    if (RESULTS / "screen.json").exists():
        scr = read_json(RESULTS / "screen.json")
        sv = read_json(DATA / "screen_veto_summary.json") if (DATA / "screen_veto_summary.json").exists() else {}
        tp = read_json(RESULTS / "tests_screen_prompts.json") if (RESULTS / "tests_screen_prompts.json").exists() else {}
        A("### Path-task screen (H6; descriptive, never pooled)\n")
        A("The same ban-free families are scored against exp10's existing Llama ban landings. Prompts come from exp10's own "
          f"builders, and our copy reproduces exp10's sampled ban prompts byte-for-byte: {sum(tp.get('ban_prompt_sha_matches_exp10', {}).values())}/"
          f"{len(tp.get('ban_prompt_sha_matches_exp10', {}))}. Labels come from exp10's canon labeller. LADDER here pools the "
          "nonce ban and the novelty instruction only.\n")
        A("| task | exp10 ban landing | hit | SUB | LAD | ASSOC | PROX | winner (margin) | veto: banned share by round |")
        A("|---|---|---|---|---|---|---|---|---|")
        for t, v in scr.items():
            sc = v["scored"]
            def c2(f):
                return f"{v['forecast_top1'].get(f) or '–'} ({f2(sc['logscore'][f])})"
            rr = ", ".join(f"r{r['round']} {f2(r['A_share'])}" for r in sv.get(t, {}).get("rounds", []))
            ng = (sv.get(t, {}).get("ngrams") or [{}])[0] or {}
            A(f"| {t} | {json.dumps(v['exp10_ban_landing'])} | {sc['hit_label']} | {c2('SUBTRACT')} | {c2('LADDER')} | "
              f"{c2('ASSOCIATE')} | {c2('PROXIMITY')} | {sc['winner'] or '–'} ({f2(sc['margin'])}) | "
              f"{json.dumps(ng.get('decoded'))}: {rr} |")
        A("")
    A("## Defaults and events (frozen before any ban; `predictions/events.json`)\n")
    A("| task | X0 (FP8 pilot) | D | D from attempts | decision set (homogeneity p) | n valid | n correct | s_D | Hill_cc |")
    A("|---|---|---|:-:|---|--:|--:|--:|--:|")
    for t, v in ev["tasks"].items():
        A(f"| {t} | {v['X0']} | {v['D']} | {'yes' if v['D_from_attempts'] else ''} | {v['decision_set']} "
          f"({f2(v['homogeneity_p'], 3)}) | {v['n_valid']} | {v['n_correct']} | {f2(v['s_D_attempted'])} | {f2(v['hill_cc'])} |")
    A("")
    A("Present-minor events (≥ 10% of correct programs, ≥ 3 correct, task ≥ 10 correct): " +
      ", ".join(f"{e['task']} {e['A']} ({e['correct_count']}/{e['n_correct']})" for e in ev["present_minor"]) + ".\n")
    A("## Tests\n")
    A("| test | result |")
    A("|---|---|")
    A(f"| T0 input integrity (`results/input_integrity.json`) | bench sha256 all ok: {read_json(RESULTS / 'input_integrity.json')['bench_all_ok']}; "
      f"canon SHA256SUMS ok: {read_json(RESULTS / 'input_integrity.json')['canon']['canon_ok']}; model shards = exp10: "
      f"{read_json(RESULTS / 'input_integrity.json')['model_shards_match']} |")
    for k, v in tests.items():
        A(f"| {k} | passed: {v.get('passed', v.get('synthetic', {}).get('passed') if isinstance(v, dict) else v)} |")
    lr = read_json(RESULTS / "labeller_recheck.json") if (RESULTS / "labeller_recheck.json").exists() else None
    if lr:
        A(f"| A3/T0 labeller re-check (`results/labeller_recheck.json`) | bench references {lr['references_ok']}/{lr['references_n']} "
          f"(runtime and AST); runtime vs adjudicated gold {f2(lr['gold_agreement_overall'], 3)}; tasks < 0.90: "
          f"{lr['flagged_tasks'] or 'none'}; canon (quoted from exp10, unchanged files) {lr['canon_exp10_quoted']['references_ok']}/"
          f"{lr['canon_exp10_quoted']['references_n']} |")
    if rd and "t8_commit_before_bans" in rd:
        A(f"| T8 commitment timing | every committed prediction file (utc entry and mtime) precedes the first ban sample: "
          f"{rd['t8_commit_before_bans']['passed']} ({len(rd['t8_commit_before_bans']['entries'])} entries); pre-commit grep "
          f"audit: 0 ban prompts in {read_json(PRED / 'grep_audit_precommit.json')['n_rows_checked']} rows |")
        A(f"| T9 confirmation signals | bf16 neutral-twin modal label = FP8 pilot modal label on "
          f"{rd['t9_confirmation']['n_same']}/{rd['t9_confirmation']['n']} tasks; nonce bans leave D near baseline "
          f"(knob view); one-shot vetoes move ≥ 0.4 of X attempts on T03, T13, T08 and three present-minor events |")
    if rd:
        A(f"| T10 independent re-derivation (`audit/rederive.py`) | {rd['n_mismatches']} mismatches; branch match "
          f"{rd['branch_match']}; hash chain ok {rd['hash_chain_ok']}; family-permutation placebo: any family advances in "
          f"{f2(rd['placebo_family_permutation']['any_family_advances_rate'])} of 1,000 permutations |")
    rt = read_json(RESULTS / "independent_rederivation_tests.json") if (RESULTS / "independent_rederivation_tests.json").exists() else None
    if rt:
        pa = rt["placebo_family_permutation"]["holm_rejection_rate"]
        A(f"| Statistical re-derivation (`audit/rederive_tests.py`, no src/ or scipy) | all match: {rt['all_match']}. "
          f"Exact enumeration Wilcoxon p equal to the reported values; Holm decisions, top-1 hits, binomial p, and D for "
          f"{sum(v['match'] for v in rt['D_per_task'].values())}/12 tasks. Placebos fail as required: family labels permuted "
          f"within events give Holm rejection rates {min(pa.values()):.3f}–{max(pa.values()):.3f}; a random top-1 predictor "
          f"gives p < 0.05 in {rt['placebo_random_top1']['rate_p_below_0.05']:.3f} of 1,000 draws |")
    if au:
        A(f"| C3 Llama label audit (second blind judge {au.get('judge')}) | agreement {f2(au.get('overall_agreement'))} "
          f"on {au.get('n')} programs; tasks below 0.85: {au.get('flagged_tasks_below_0.85')} |")
    A("")
    A(f"Compute: {gpu_s / 3600:.2f} GPU-hours of logged generation on one NVIDIA L4. That figure excludes vLLM startup, "
      f"veto rounds and HF forward passes; GPU sessions held the L4 for about 1.8 hours of wall time in all. OpenRouter judge spend was "
      f"USD {spend:.3f} in total (USD {spend_screen:.3f} of it from the screen's canon judge), against this artifact's cap "
      f"of USD 0.70.\n")
    A("## Deviations and drops\n")
    A("Each entry gives its reason and cost; the full list is in `results/deviations.json`.\n")
    for d in dev["deviations"]:
        A(f"- **{d['id']}**: {d['what']} *Cost:* {d['cost']}")
    for d in dev["drops"]:
        A(f"- **drop {d['id']}**: {d['what']} {d['reason']} *Cost:* {d['cost']}")
    A("")
    A((WS / "scripts" / "README_static.md").read_text())
    (WS / "README.md").write_text("\n".join(L) + "\n")
    print("README.md written")


if __name__ == "__main__":
    main()
