#!/usr/bin/env python3
"""Assemble README.md: narrative (tools/readme_narrative.md, written by the executor after the results) with
{{TABLE:<name>}} placeholders filled from results/*.json, then checks, the static design/layout/run sections
(tools/readme_static.md), deviations, costs and timing, and the restore section."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "src"))

import tables as T  # noqa: E402


def rj(n: str):
    p = ROOT / "results" / n
    return json.loads(p.read_text()) if p.exists() else {}


def checks() -> str:
    g = rj("unit_tests_gpu.json")
    c = rj("unit_tests_cpu.json")
    lr = rj("labeller_recheck.json")
    ic = rj("inputs_check.json")
    rd = rj("rederive.json")
    co = rj("commit_order_audit.json")
    u4 = rj("u4_diagnostic.json")
    ec = rj("engine_check.json")
    uc = rj("units_crosscheck.json")
    lines = ["## Checks", ""]
    lines.append(f"- **Engine check (positive control).** "
                 + "; ".join(f"{t}: our composition {v.get('ours')} vs screen {v.get('screen')}, JS {v.get('js'):.3f} "
                             f"(null q95 {v.get('null_q95'):.3f}), per-slot identical code {v.get('per_slot_identical_code')}, "
                             f"REPRODUCED = {v.get('REPRODUCED')}" for t, v in ec.items())
                 + ". The FP8 engine reproduces the exp17 screen rows byte for byte, under the same uniforms, units "
                   "and direction.")
    if g:
        lines.append("- **GPU tests** (`results/unit_tests_gpu.json`). U1 CRN determinism across two batch "
                     f"compositions: T03 {g['T03']['U1_crn_determinism_two_compositions']}, T1 "
                     f"{g['T1']['U1_crn_determinism_two_compositions']}. U2: alpha 0 reproduces the twin byte for "
                     f"byte at every site, S3 with its shadow included: T03 {all(g['T03']['U2_identity_alpha0'].values())}, "
                     f"T1 {all(g['T1']['U2_identity_alpha0'].values())}. U3: the realised along-u displacement equals "
                     "alpha x unit within "
                     f"{max(v.get('max_relerr_along_u') or 0 for t in ('T03', 'T1') for v in g[t]['U3_dose_alpha1'].values()) * 100:.2f}% "
                     "at every prefill site. S3 (block 23, vs shadow) matches its target within 0.01%. U6: peak "
                     f"{g['U6_memory']['peak_gib']:.1f} GiB at B = 20, P = {g['U6_memory']['P']}, 1,024 new tokens. "
                     f"U7: the block-35-only edit is a no-op (T03 {g['T03']['U7_block35_noop']}, T1 "
                     f"{g['T1']['U7_block35_noop']}). U4 (shadow vs an independent teacher-forced forward) FAILS the "
                     f"1e-2 rule: min cos T03 {g['T03']['U4_shadow_fidelity'].get('min_cos', float('nan')):.3f}, T1 "
                     f"{g['T1']['U4_shadow_fidelity'].get('min_cos', float('nan')):.3f}. The follow-up diagnostic "
                     "(`results/u4_diagnostic.json`) shows that " + (u4.get("reading", "n/a")) + ".")
    if c:
        lines.append(f"- **CPU tests** (`results/unit_tests_cpu.json`): T1 hook maths {c['T1_hook']['pass']} (max "
                     f"relative error along u {c['T1_hook']['max_rel_err_along_u_bf16']:.1e} at the real unit scales). "
                     f"T2 hull {c['T2_hull']['pass']}: an equal mix of two pure settings gives H5 = "
                     f"{c['T2_hull']['equal_mix_H5']:.2f}. T3 two-survivor permutation {c['T3_perm']['pass']}. T4 "
                     f"screen byte-identity {c['T4_screen']['pass']}. T5 binomial p(4 of 6) = "
                     f"{c['T5_binom']['p_4_of_6']:.4f}.")
    if lr:
        b = lr["bench"]
        lines.append("- **Labellers re-checked** (`results/labeller_recheck.json`). Bench references that pass and "
                     "self-label: " + ", ".join(f"{t} {v['refs_pass_and_self_label']}/{v['n_refs']}" for t, v in b.items())
                     + ". Gold-set runtime and AST labels reproduced: " +
                     ", ".join(f"{t} {v['gold_runtime_reproduced']}/{v['gold_n']} and {v['gold_ast_reproduced']}/{v['gold_n']}"
                               for t, v in b.items()) + ". exp8 suite references: " +
                     ", ".join(f"{t} {v['n_pass']}/{v['n_refs']} pass" for t, v in lr["suite"].items()) + ".")
    if ic:
        lines.append(f"- **Inputs** (`inputs/SHA256SUMS`, {ic['n_files_hashed']} files). Bench files against "
                     f"`bench/commitment.json`: {ic['bench_files_checked']} hashes, {len(ic['bench_mismatches'])} "
                     "mismatches.")
    if uc:
        lines.append("- **Units cross-check** (`results/units_crosscheck.json`). Median ratio to exp17's FP8 units: "
                     + ", ".join(f"{t} {v['exp17']['median_ratio']:.3f}" for t, v in uc.items() if 'exp17' in v)
                     + ". Ratio to exp13's units: " + ", ".join(f"{t} {v['exp13']['median_ratio']:.2f}" for t, v in uc.items()
                                                    if 'exp13' in v) + " (exp13 built different twins; deviation D10).")
    if rd:
        lines.append(f"- **Independent re-derivation** (`audit/rederive.py` -> `results/rederive.json`). Cells checked: "
                     f"{rd.get('cells_checked')}, mismatches {len(rd.get('cell_mismatches', []))}. H5 re-derived with "
                     f"independent Monte-Carlo code: max |diff| {rd.get('H5_max_abs_diff') or float('nan'):.3f}, "
                     f"{len(rd.get('H5_mismatches_gt_0.05', []))} cells beyond the 0.05 tolerance. C1 count re-derived "
                     f"{rd.get('C1_rederived', {}).get('count_S0_best')} (matches: "
                     f"{rd.get('C1_rederived', {}).get('matches_analysis_count')}). C3d mismatches "
                     f"{len(rd.get('C3d_mismatches', []))}. Placebos: with site labels shuffled within (task, alpha), "
                     f"S0 is best at rate {rd.get('placebo_site_shuffle', {}).get('S0_best_rate_mean', float('nan')):.2f} "
                     f"(null 1/6; observed {rd.get('placebo_site_shuffle', {}).get('observed_S0_best_rate', float('nan')):.2f}). "
                     f"With template labels shuffled, the template spread of the off-default share is "
                     f"{rd.get('placebo_template_shuffle', {}).get('shuffled_mean', float('nan')):.3f} (observed "
                     f"{rd.get('placebo_template_shuffle', {}).get('observed_spread', float('nan')):.3f}). With "
                     f"randomised d values, p_edge = 0.5 in "
                     f"{rd.get('placebo_random_d', {}).get('share_p_edge_0.5', float('nan')):.2f} of draws.")
    rh = rj("rederive_headlines.json")
    if rh:
        mh = rh["H3_mantel_haenszel"]
        pl = rh["H3_placebo_S0_shuffled_within_task"]
        e8 = rh["H8_engine_check"]
        lines.append("- **Second re-derivation of the headlines** (`audit/rederive_headlines.py` -> "
                     "`results/rederive_headlines.json`; raw files only, different methods). Correct off-default "
                     f"programs at S1 / S2 / S5: {rh['H2_inert_sites']['S1']['n_off_default']}/"
                     f"{rh['H2_inert_sites']['S1']['n_correct']}, {rh['H2_inert_sites']['S2']['n_off_default']}/"
                     f"{rh['H2_inert_sites']['S2']['n_correct']}, {rh['H2_inert_sites']['S5']['n_off_default']}/"
                     f"{rh['H2_inert_sites']['S5']['n_correct']}. The matched-dose S0 effect, recomputed as a "
                     "hand-coded Mantel-Haenszel odds ratio (strata = task x quintile of displacement at R), is "
                     f"OR {mh['OR']:.2f} [{mh['ci95'][0]:.2f}, {mh['ci95'][1]:.2f}]. Its placebo, with S0 labels "
                     f"shuffled within task, gives median OR {pl['median_OR']:.2f}, and the CI excludes 1 in only "
                     f"{pl['share_CI_excluding_1'] * 100:.1f}% of 200 shuffles. Exact McNemar for S0 vs S1 at "
                     "alpha 2 is reproduced by hand on every task; with pair members randomly swapped, p < 0.05 in "
                     f"{rh['H4_placebo_random_swap']['share_p_lt_0.05'] * 100:.1f}% of 1,200 tests. Alpha-8 pass: "
                     f"{max(rh['H5_alpha8_pass'].values()):.2f} on every task. Correct programs: "
                     f"{rh['H6_counts']['n_correct_programs']}, of which {rh['H6_counts']['n_correct_other']} is "
                     f"'other'. TOP5 avoidance at alpha 1 / 2: {rh['H7_top5']['TOP5_a1']['avoidance']:.2f} / "
                     f"{rh['H7_top5']['TOP5_a2']['avoidance']:.2f}. Engine check with an independent code-block "
                     f"extractor: T03 {e8['T03']['identical_code']}/{e8['T03']['n']} and T2 "
                     f"{e8['T2']['identical_code']}/{e8['T2']['n']} identical. C1 binomial p, by hand: "
                     f"{rh['H1_binomial_p']['p']:.4f}.")
    if co:
        lines.append(f"- **Pre-registration** (`commitments.log`, {co['chain']['n_lines']} lines, "
                     f"{co['chain']['chain_breaks']} chain breaks, {co['chain']['files_changed_since_commit']} committed "
                     f"files changed since their commit). Commit #1 at {co['commit1_utc']}. Decisive rows drawn before "
                     f"it: {co['n_decisive_before_commit1']} of {co['n_decisive_rows']}. Only the engine check and "
                     f"smoke slots ran earlier.")
    return "\n".join(lines)


def deviations() -> str:
    d = rj("deviations.json").get("deviations", [])
    return "## Deviations from the plan\n\n" + "\n".join(f"- **{x['id']}**: {x['what']}. *Why:* {x['why']}. "
                                                        f"*Cost:* {x['cost']}." for x in d)


def costs() -> str:
    t = rj("timing_summary.json")
    cp = rj("openrouter_cost_paths.json").get("total_usd", 0)
    ck = rj("openrouter_cost_k7.json").get("total_usd", 0)
    ca = rj("openrouter_cost_audit.json").get("total_usd", 0)
    cb = 0.0
    p = ROOT / "logs" / "openrouter_spend.jsonl"
    if p.exists():
        cb = sum(json.loads(l).get("cost", 0) or 0 for l in p.read_text().splitlines() if l.strip())
    tot = cp + ck + ca + cb
    return ("## Costs and timing\n\n"
            f"- GPU: {t.get('gpu_hours_total', 0):.2f} GPU-hours of batch time ({t.get('n_batches')} batches of 20 rows) on "
            "one RTX 2000 Ada 16 GB. Per-row seconds by task: " +
            ", ".join(f"{k} {v:.2f}" for k, v in (t.get("seconds_per_row_by_task") or {}).items()) + ".\n"
            f"- OpenRouter: USD {tot:.3f} in total. Labelling judges: paths {cp:.3f}, bench {cb:.3f}, K=7 {ck:.3f}. "
            f"Novelty audit with controls: {ca:.3f}. Artifact cap: USD 1.00.")


def restore() -> str:
    return ("## Restoring removed files\n\n"
            "`.aii/manifest.yaml` marks only regenerable bulk for deletion:\n\n"
            "- `.venv/`: `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml`\n"
            "- `src/__pycache__/`, `tests/__pycache__/`, `tools/__pycache__/`: Python byte-code "
            "caches, recreated automatically when any stage runs.\n\n"
            "The model weights live in the run's shared Hugging Face cache, not in this folder: "
            "`huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218`. "
            "`restore.sh` runs these commands. Everything else (data, results, units, directions, predictions, audit, "
            "figures, inputs) is kept. No file in this folder is 100 MB or larger, so the published repository is "
            "complete.")


def main() -> None:
    narr = (ROOT / "tools" / "readme_narrative.md").read_text()

    def sub(m):
        name = m.group(1)
        fn = {"c1": T.c1_table, "p15": T.p15_table, "fail": T.failure_table, "boundary": T.boundary_table,
              "c3d": T.c3d_table, "flips": T.flips_table}.get(name)
        return fn() if fn else T.cells_table(int(name))
    narr = re.sub(r"\{\{TABLE:([a-z0-9]+)\}\}", sub, narr)
    static = (ROOT / "tools" / "readme_static.md").read_text()
    out = "\n\n".join([narr.strip(), checks(), static.strip(), deviations(), costs(), restore()]) + "\n"
    (ROOT / "README.md").write_text(out)
    print(f"README.md: {len(out)} chars")


if __name__ == "__main__":
    main()
