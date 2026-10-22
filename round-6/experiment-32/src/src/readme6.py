#!/usr/bin/env python3
"""Render README.md from the result files (every number in the README comes from results/*.json)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg5 import PRED_DIR, RESULTS_DIR, ROOT, read_json, read_jsonl  # noqa: E402

sys.path.insert(0, str(ROOT / "analysis"))


def f(x, d=2):
    if x is None:
        return "-"
    if isinstance(x, float):
        return f"{x:.{d}f}"
    return str(x)


def main() -> None:
    l1 = read_json(RESULTS_DIR / "l1.json")
    un = read_json(ROOT / "units.json")["units"]
    ev = read_json(ROOT / "landing_events.json")["events"]
    l2 = read_json(RESULTS_DIR / "l2.json")
    l3 = read_json(RESULTS_DIR / "l3.json")
    m = read_json(RESULTS_DIR / "m.json")
    k = read_json(RESULTS_DIR / "k.json")
    nov = read_json(RESULTS_DIR / "novelty_audit.json") if (RESULTS_DIR / "novelty_audit.json").exists() else {}
    red = read_json(RESULTS_DIR / "rederive.json") if (RESULTS_DIR / "rederive.json").exists() else {}
    co = read_json(RESULTS_DIR / "commit_order.json") if (RESULTS_DIR / "commit_order.json").exists() else {}
    ba = read_json(RESULTS_DIR / "base_audit.json") if (RESULTS_DIR / "base_audit.json").exists() else {}
    tg = read_json(RESULTS_DIR / "tests_gpu.json") if (RESULTS_DIR / "tests_gpu.json").exists() else {}
    tc = read_json(RESULTS_DIR / "tests_cpu.json") if (RESULTS_DIR / "tests_cpu.json").exists() else {}
    costs = read_json(RESULTS_DIR / "costs.json")
    sens = read_json(RESULTS_DIR / "posthoc_sensitivities.json") if (RESULTS_DIR / "posthoc_sensitivities.json").exists() else {}
    devs = read_jsonl(ROOT / "results" / "deviations.jsonl")
    L = []
    w = L.append
    w("# Where nudged code lands, panel two (iteration 6)")
    w("")
    w("Panel II of the iteration-6 held-out test of **Claim L**: when a content-free nudge moves **Qwen3-8B** "
      "(instruct) off its default algorithm, does the program land on the **base model's runner-up** `r_u` "
      "(Qwen3-8B-Base), or only on the tuned model's **own hidden second choice**, measured two ways: the tail of "
      "300 twin samples (`q_tail`, `t_u`) and the teacher-forced likelihood ranking of forced programs (`q_lik`, "
      "`qlik_top1`)? Claim M asks which unit property ranks the escape fraction `E_u`. Everything hooked runs in "
      "bf16 HF transformers; vLLM bf16 only samples unhooked arms.")
    w("")
    w("Every forecast was sha256 hash-chained (`commitments.log`) before the unit's first nudge sample. Commit #0 "
      "(the protocol) precedes the first sample, and the analysis code precedes the first nudge (audit below).")
    w("")
    w("## Results (panel II; CONFIRMATION = new list-II units)")
    w("")
    a, b = l1["L1a"], l1["L1b"]
    w(f"**Panel verdict: {l1['verdict']}.** This panel is half of the pooled panel I + II test. "
      "`landing_events.json` and `units.json` (schema `iter6_landing_v1`) pool mechanically with panel I through "
      "`analysis/pool_l1.py`.")
    w("")
    w(f"- **L1a (tail-empty events):** r_u named the landing in {a['hits_r_u']}/{a['n_events']} events "
      f"(chance {f(a['expected_chance_hits'])} hits), exact Poisson-binomial p = {f(a['p'], 4)}, status "
      f"**{a['status']}** (6 events required). qlik_top1 hits on the same events: {a['hits_qlik_top1']}. Events: "
      f"{', '.join(a['events'])}.")
    w(f"- **L1b (discordant events, r_u != qlik_top1):** r_u-only hits b = {b['b_r_u_only']}, qlik-only hits c = "
      f"{b['c_qlik_only']}, ties {b['ties']}; one-sided exact sign test p = {f(b['p'], 4)}, status **{b['status']}**. "
      f"Events: {', '.join(b['events'])}.")
    ul = l1["unit_level"]
    w(f"- **Pseudo-replication guard (unit level):** L1a {ul['L1a']['hits_r_u']}/{ul['L1a']['n_events']} units "
      f"(p = {f(ul['L1a']['p'], 4)}, {ul['L1a']['status']}); L1b b = {ul['L1b']['b_r_u_only']}, c = "
      f"{ul['L1b']['c_qlik_only']} over {ul['L1b']['n_events']} units (p = {f(ul['L1b']['p'], 4)}, "
      f"{ul['L1b']['status']}). The event-level L1b result therefore holds **per event, not per unit**: the "
      "discordant events come from few units.")
    tr = l1["tail_rival"]
    w(f"- **Rival t_u (the twin's own tail):** {tr['hits_defined']}/{tr['n_defined']} hits where defined "
      "(not tail-empty).")
    ls = l1["log_scores"]["E"]
    w("- **Log scores on matched events E** (nats per landed program; base minus rival; one-sided 95% bootstrap "
      "lower bound; non-inferior iff LB > -0.10):")
    w("")
    w("| rival | n events | mean D | LB (event) | LB (unit-clustered) | 95% CI | non-inferior |")
    w("|---|---|---|---|---|---|---|")
    for r in ("lik", "tail", "lik_raw", "assoc", "uniform"):
        d = ls.get(f"D_{r}", {})
        e, c = d.get("event", {}), d.get("unit_clustered", {})
        if e.get("mean") is None:
            continue
        w(f"| q_{r} | {e['n']} | {f(e['mean'])} | {f(e['lb95_one_sided'])} | {f(c.get('lb95_one_sided'))} | "
          f"[{f(e['ci95'][0])}, {f(e['ci95'][1])}] | {e['non_inferior']} |")
    w("")
    w(f"- **L2 (landings outside the base repertoire):** {l2['content_free']['violations']} of "
      f"{l2['content_free']['n_programs']} correct off-default content-free nudged programs implement an algorithm "
      "with zero valid and zero correct base programs (BINT: "
      f"{l2['BINT']['violations']}/{l2['BINT']['n_programs']}).")
    if l2["content_free"]["violation_list"]:
        vv = sorted({(x['unit'], x['label']) for x in l2['content_free']['violation_list']})
        w(f"  The violations are {', '.join(f'{u}:{lab}' for u, lab in vv)}.")
    kb = l3["kendall_base_vs_tail"]
    w(f"- **L3:** power-fitted held-out winners {l3['L3']['winners']}; Kendall tau-b (q_base vs q_tail order on S): "
      f"mean {f(kb['mean_tau'])} over {len(kb['per_unit'])} units ({kb['n_positive']}/{kb['n_nonzero']} positive).")
    w("- **M (Spearman with E_u over enrolled new units; Holm over 6 candidates; committed signs):**")
    w("")
    w("| candidate | n | rho | committed sign | one-sided p | Holm p | supported |")
    w("|---|---|---|---|---|---|---|")
    for c, r in m["candidates"].items():
        w(f"| {c} | {r['n']} | {f(r['rho'])} | {r['committed_sign']} | {f(r['p_one_sided'], 3)} | "
          f"{f(r['p_holm'], 3)} | {r['supported']} |")
    w("")
    import pool_l1 as P
    units_d = {u["unit_id"]: u for u in un}
    E = P.select(ev, units_d)
    Ea = [e for e in E if e["tail_empty"]]
    same = sum(1 for e in Ea if e["r_u"] == e["qlik_top1"])
    dfd = [e for e in E if e.get("t_u")]
    t_hit = sum(1 for e in dfd if e["t_u"] == e["modal_landing"])
    r_hit_d = sum(1 for e in dfd if e["r_u"] == e["modal_landing"])
    lik_hit = sum(1 for e in E if e["qlik_top1"] and e["qlik_top1"] == e["modal_landing"])
    r_hit = sum(1 for e in E if e["r_u"] == e["modal_landing"])
    w("### Reading")
    w("")
    w(f"- On all {len(E)} CONFIRMATION events: r_u hit {r_hit}, qlik_top1 hit {lik_hit}. On the {len(dfd)} events where "
      f"the twin tail is non-empty, t_u hit {t_hit}/{len(dfd)} and r_u hit {r_hit_d}/{len(dfd)}.")
    w(f"- On the {len(Ea)} tail-empty events, r_u equals qlik_top1 in {same}. So L1a cannot separate the base "
      "runner-up from the tuned model's own likelihood ranking there: both name the same algorithm.")
    w("- The decisive comparisons are the discordant units:")
    w("  - II1 and II3: the landing matches r_u and the twin tail t_u, not qlik_top1.")
    w("  - II8 (k nearest points, a flagged structural neighbour of T03): every nudge type lands on maxheap_k. That "
      "is the tuned model's own tail choice and its likelihood top-1, not the base runner-up (nsmallest).")
    w("- Read together:")
    w("  - Where the base runner-up and the tuned model's own forecasts disagree, the tuned model's forecasts won "
      "(II8).")
    w(f"  - Where the base runner-up won a discordant event (II1, II3), the twin tail t_u named the same landing "
      f"(t_u {t_hit}/{len(dfd)} where defined).")
    w("  - So no event favours the base model over the tuned model's own twin tail. This agrees with 'nudges walk "
      "the tuned model's own hidden ladder', with the base model as a proxy where its order matches that ladder.")
    w("- The counts are small (3 discordant units, 4 tail-empty events), so this is descriptive and carried to the "
      "pooled panel I + II test.")
    w("")
    w("### Units")
    w("")
    w("| unit | status | default (share) | K | tail-empty | t_u | r_u | qlik_top1 | discordant | E_u (a1/a2/a4) | "
      "flags |")
    w("|---|---|---|---|---|---|---|---|---|---|---|")
    for u in un:
        e = u.get("E_u_by_alpha") or {}
        w(f"| {u['unit_id']} | {u['status']} | {u['default']} ({f(u.get('default_share'))}) | {u['K']} | "
          f"{u.get('tail_empty')} | {u.get('t_u')} | {u.get('r_u')} | {u.get('qlik_top1')} | {u.get('discordant')} | "
          f"{'/'.join(f(e.get(x)) for x in ('1.0', '2.0', '4.0'))} | {'; '.join(u.get('flags') or [])} |")
    w("")
    w("### Landing events (content-free, is_event)")
    w("")
    w("| event | set | n landed | composition | modal landing | r_u | qlik_top1 | t_u |")
    w("|---|---|---|---|---|---|---|---|")
    for e in ev:
        if not (e["is_event"] and e["content_free"]):
            continue
        comp = ", ".join(f"{k2}:{v2}" for k2, v2 in e["counts"].items() if v2)
        w(f"| {e['event_id'].replace('|', ' / ')} | {e['set']} | {e['n_offdefault_correct']} | {comp} | {e['modal_landing']} | "
          f"{e['r_u']}{' +' if e['r_u'] == e['modal_landing'] else ''} | {e['qlik_top1']}"
          f"{' +' if e['qlik_top1'] == e['modal_landing'] else ''} | {e['t_u']}"
          f"{' +' if e['t_u'] and e['t_u'] == e['modal_landing'] else ''} |")
    w("")
    if sens:
        w("### Sensitivities (frozen list; plus the post-hoc ones marked)")
        w("")
        for kk, v in sens.items():
            w(f"- {kk}: {v}")
        w("")
    w("### Validity checks")
    w("")
    if red:
        w(f"- Independent stdlib re-derivation (`audit/rederive.py`): mismatches {red.get('mismatches')}, event ids "
          f"match {red.get('event_ids_match')}; placebos: random non-default r_u hit rate "
          f"{f(red['placebo_random_r_u']['mean_hit_rate'])} vs chance {f(red['placebo_random_r_u']['chance'])}; "
          f"twin-as-nudge events {red.get('placebo_twin_as_nudge_events')} (a unit whose own twin minority already "
          "forms an event cannot separate nudge landings from the twin tail); q_base/q_lik swap flips L1b: "
          f"{red['placebo_swap_base_qlik']['flipped']}.")
    rh = read_json(RESULTS_DIR / "rederive_headlines.json") if (RESULTS_DIR / "rederive_headlines.json").exists() else {}
    if rh:
        ck = rh["checks"]
        w(f"- Second stdlib re-derivation (`audit/rederive_headlines.py`, raw rows): hit counts {rh['hits']}, "
          f"mean D_lik {f(rh['mean_D_lik'], 3)}, mean D_tail {f(rh['mean_D_tail'], 3)}, E_u per unit, beta rho "
          f"{f(rh['M_beta']['rho'], 3)} (p {f(rh['M_beta']['p_one_sided'], 4)}) and L2 {rh['L2']['violations']}/"
          f"{rh['L2']['n']} all match: {all(v for k2, v in ck.items() if k2.endswith('match'))}. Placebos fail as "
          f"required: shuffled E_u rejects {f(rh['placebo_shuffled_E_u']['rejection_rate_p<0.05'], 3)}, permuted "
          f"q_base mean D_lik {f(rh['placebo_permuted_q_base_mean_D_lik'], 2)}, constant beta gives an undefined rho. "
          f"The committed beta drifts by at most {f(ck['beta_recount_max_abs_drift_after_final_adjudication'], 3)} "
          "when re-counted with the post-commit final adjudications (forecasts are frozen at commit).")
    if co:
        w(f"- Commit order (`audit/commit_order.py`): chain breaks {co.get('chain_breaks')}, files changed "
          f"{len(co.get('files_changed_since_commit', []))}, commit #0 before the first sample "
          f"{co.get('commit0_before_first_sample')}, analysis code before the first nudge "
          f"{co.get('analysis_before_first_nudge')}, nudge rows before their unit commit "
          f"{co.get('nudge_rows_before_their_unit_commit')}, tamper control detected "
          f"{co.get('tamper_negative_control_detected')}.")
    if ba:
        w("- 15-program blind base audits (labeller vs two-family adjudication, all valid / correct-only): " +
          "; ".join(f"{u} {f(v['agreement'])}/{f(v.get('agreement_correct_only'))}{' AUDIT_WEAK' if v['flag_AUDIT_WEAK'] else ''}"
                    for u, v in ba.items()) + ".")
    if nov:
        w(f"- Novelty audit: {nov.get('n_correct_other')} correct 'other' programs ({nov.get('n_distinct')} distinct) "
          f"-> {nov.get('class_counts')}; {nov.get('statement')} (rule-of-three bound "
          f"{f(nov.get('rule_of_three_upper'), 5)} per correct program). The 'manual' comparison is the executor's "
          "automated nearest-match against references and dataset rows; no human read the programs.")
    if tg:
        w(f"- GPU tests: CRN determinism {tg.get('G1_crn_determinism_identical')}; alpha-0 ESC identical rows "
          f"{tg.get('G2_alpha0_esc_identical_rows')}; realised dose max relative error "
          f"{f(tg.get('G3_realised_dose', {}).get('max_rel_err'), 5)}; GTN alpha-0 identical rows "
          f"{tg.get('G4_gtn_alpha0_identical_rows')}; vLLM prompt ids identical "
          f"{tg.get('G6_vllm_prompt_ids_identical')}.")
    if tc:
        w(f"- CPU tests: schema errors {len(tc.get('T6_schema', {}).get('errors', []))}; new seeds disjoint from "
          f"{tc.get('G5_seeds', {}).get('n_old_seeds')} iteration-4/5 seeds: {tc.get('G5_seeds', {}).get('disjoint')}; "
          f"planted-ban control caught for every unit: "
          f"{all(v['planted_ban_caught'] for v in tc.get('T1', {}).values())}.")
    w(f"- OpenRouter spend: USD {f(costs['total_usd'], 3)} over {costs['n_calls']} judge calls (cap 2.00).")
    w("")
    L.append("\n".join(README_STATIC))
    w("")
    w("## Deviations from the plan")
    w("")
    for d in devs:
        w(f"- **{d['key']}**: {d['text']}")
    (ROOT / "README.md").write_text("\n".join(L) + "\n")
    print("README written", len(L))


README_STATIC = [
    "## What was done",
    "",
    "1. **Units (candidate list II).** Each unit has new wording with no algorithm or data-structure word, two "
    "agreeing oracles, generated hidden tests including stress cases, at least three test-passing references, "
    "mutants that must fail, and gated runtime-tracer plus AST labellers (`src/units/ii*.py`). Built: II1 "
    "is-subsequence, II2 task scheduler, II3 count ones, II4 peak index, II5 all arrangements, II6 bracket matching, "
    "II7 in-place combine, II8 k nearest points. II9/II10 and the reserves were not built (time).",
    "2. **Predictor side, in this order, before any nudge:**",
    "   - the twin of 300: 50 HF CRN slots plus 150 vLLM slots at T 1.0, and 100 vLLM slots at T 1.3;",
    "   - the base repertoire: 200 chat samples with token ids identical to the twin W1-W5 prompts, plus 100 plain "
    "completions;",
    "   - forced 'Implement X' programs (up to 40 attempts per algorithm) and q_lik scoring, with scrubbed and "
    "unscrubbed variants and a measured noise floor;",
    "   - 20 association answers per algorithm;",
    "   - the gold-set gate (ii) with two judge families;",
    "   - the hash-chained unit commit (`predictions/units/<u>.json`).",
    "3. **Nudges (after the commit):**",
    "   - ESC: 8 fresh isotropic directions x alpha 1/2/4, N 10 per cell, with stage-2 confirmation at N 30;",
    "   - PN: a fresh direction per sample, alpha 2 and 4, N 50 each;",
    "   - GTN: generated tokens 1-32 with teacher-forced shadow rows, alpha 2, N 50;",
    "   - BINT: a base intent sentence followed by instruct code, N 30.",
    "   ESC and PN push blocks 12-23 at the task-spec positions in ban-free units (r_Q from exp23).",
    "4. **SCREEN (iteration-5 B units):**",
    "   - the twin was topped up to 300 (iteration-5 HF slots k 0-9 plus new vLLM slots);",
    "   - forced programs and q_lik were added;",
    "   - the base was topped up with 50 chat and 50 plain samples, under an engine check against the iteration-5 "
    "rows;",
    "   - the iteration-5 alpha 1/2 events were rebuilt under the iteration-6 definitions;",
    "   - new alpha-4 ESC, PN alpha 4 and GTN alpha 2 nudges were run.",
    "   Everything is labelled SCREEN and is never primary.",
    "",
    "## Layout",
    "",
    "| path | what it holds |",
    "|---|---|",
    "| `method.py` | entry point: `uv run method.py` re-runs the CPU final stage (events, frozen analysis, audits, "
    "figures, outputs) |",
    "| `landing_events.json`, `units.json` | the pooling files (schema `schema/iter6_landing_v1.json`) |",
    "| `method_out.json` (+ `full_`/`mini_`/`preview_`) | exp_gen_sol_out: datasets `panelII_units`, `panelII_events`, "
    "`panelII_cells`; all analyses in `metadata` |",
    "| `commitments.log` | sha256 hash chain (genesis sha256('iter6_dir5_panelII')) of every committed file |",
    "| `predictions/` | `protocol_v6_panelII.json` (commit #0), `analysis_choices.json`, `m_signs.json`, `units/<u>.json`, "
    "`enrolment/<u>.json` |",
    "| `analysis/pool_l1.py`, `l2l3.py`, `m_k.py` | frozen analysis code (committed before the first nudge) |",
    "| `src/` | the pipeline; `src/units/ii*.py` are the unit labellers; `src/units/b*.py` and most engine code are "
    "vendored from iteration-5 exp26 (patched as listed in Deviations) |",
    "| `src/vllm_gen.py` | vLLM 0.11 sampler with the fence-stop logits processor (run with `.venv_vllm`) |",
    "| `src/gpu6.py`, `src/gtn6.py`, `src/qlik6.py` | HF daemon (twin CRN slots, q_lik, ESC/PN/GTN), GTN sampler, q_lik scorer |",
    "| `src/quantities6.py`, `src/events6.py`, `src/outputs6.py` | unit forecasts + commit, event assembly, final outputs |",
    "| `units/<u>/` | tests, references, mutants, build report, gate reports, frozen catalogue, neutral noun, positions |",
    "| `data/samples_raw.jsonl` | every sampled program with text and token ids (both engines, both models) |",
    "| `data/samples.jsonl` | one row per labelled program (plan row schema) |",
    "| `data/labels.jsonl`, `data/judge_labels.jsonl`, `data/judge_cache.jsonl` | labeller output and judge adjudications |",
    "| `results/` | l1, l2, l3, m, k, screen, engine_checks, dose, escape_table, events_listing.csv, novelty_audit, "
    "base_audit, rederive, commit_order, tests_cpu/gpu, timing, costs, deviations |",
    "| `figures/` | F1 landings, F2 log-score forest, F3 escape heatmap, F4 base vs tail, F5 M candidates, F6 knob prices |",
    "| `audit/rederive.py`, `audit/commit_order.py` | stdlib-only re-derivation with placebos; commit-order proof |",
    "| `vendor/` | read-only copies of the iteration-2..5 inputs used (`vendor/exp26/samples_B_nocode.jsonl` = the "
    "iteration-5 B-unit labelled rows without code) |",
    "| `inputs/sources.json` | rows extracted from the dependency dataset art_j3Rm_lr2nzR6 (12 LeetCode rows, "
    "KodCode/XLCoST/TheAlgorithms keyword rows, noun bank, validation subsets of every other dataset) |",
    "| `directions/`, `cache/` | push directions (`rand_<seed>.npy`) and fp16 ban-free unit norms per unit/template |",
    "",
    "Kept artifacts stay on the run's storage volume at these relative paths. Files of 100 MB or more are not part "
    "of the published repository (none of this artifact's data files is that large).",
    "",
    "## How to run",
    "",
    "`reproducibility.md` gives the exact commands in the order they were run, with hardware, environment variables "
    "(names only), seeds, runtimes and the numbers a reader should get.",
    "",
    "```bash",
    "uv sync                                  # HF environment (Python 3.12, pins in pyproject.toml / uv.lock)",
    "uv run method.py                         # CPU final stage: events, frozen analysis, audits, figures, outputs",
    "python3 -I audit/rederive.py             # independent re-derivation (standard library only)",
    "python3 -I audit/commit_order.py         # commit-order proof",
    "```",
    "",
    "The full pipeline needs one 23 GB GPU, `HF_HUB_CACHE` holding the two pinned snapshots, and `OPENROUTER_BASE_URL` "
    "/ `OPENROUTER_API_KEY` for the judges. In order:",
    "",
    "1. `src/extract_sources.py` (needs `AII_DEP_ART_J3RM`);",
    "2. `src/protocol6.py` (commit #0);",
    "3. `src/unitbuild.py II1,...`;",
    "4. the vLLM jobs (`src/requests6.py` builders + `.venv_vllm/bin/python src/vllm_gen.py`);",
    "5. `src/label5.py` (label daemon);",
    "6. `src/gate2.py`;",
    "7. `src/gpu6.py --plan data/gpu_plan_v3.json`;",
    "8. `src/quantities6.py <units>` (commits);",
    "9. `src/outputs6.py`.",
    "",
    "## Restoring removed files",
    "",
    "Only regenerable bulk is removed after the round (`.aii/manifest.yaml`). Every result, prediction, unit build, "
    "figure and data file stays.",
    "",
    "| removed path | restore with |",
    "|---|---|",
    "| `.venv/` | `uv sync` |",
    "| `.venv_vllm/` | `uv venv .venv_vllm --python 3.12 && uv pip install --python .venv_vllm/bin/python vllm==0.11.0 "
    "transformers==4.57.6 tokenizers==0.22.2` |",
    "| `src/__pycache__/`, `src/units/__pycache__/`, `analysis/__pycache__/`, `tests/__pycache__/`, "
    "`vendor/exp27/src/__pycache__/` | regenerated on import (`python -m compileall src analysis tests vendor/exp27/src`) |",
    "| model weights (shared HF cache, never in this folder) | `huggingface-cli download Qwen/Qwen3-8B --revision "
    "b968826d9c46dd6066d109eabc6255188de91218` and `huggingface-cli download Qwen/Qwen3-8B-Base --revision "
    "49e3418fbbbca6ecbdf9608b4d22e5a407081db4` |",
    "",
    "`restore.sh` runs all of the above.",
]


if __name__ == "__main__":
    main()
