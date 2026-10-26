# Review of the iteration-8 research record (Step 3.5, REVIEW_REPORT)

This folder holds an adversarial audit of the run's internal research report, covering iterations 1 to 8. The
report studies how algorithm choice ("creativity") shows up inside open-weight code models, and how it can be
moved. The audit checked four things:

- every iteration-8 artifact is reported;
- each headline number reproduces from that artifact's own result files;
- the record covers the user's original request;
- the conclusions agree with the run's own evidence.

## Verdict

| Field | Value |
|-|-|
| Results reported (headline numbers recomputed from executed artifacts) | yes |
| Coverage of the original request | full |
| Soundness / presentation / contribution (1-4) | 1 / 3 / 3 |
| Overall score (1-10) / confidence (1-5) | 4 / 4 |
| Blocking | yes: soundness 1, derived by rule |

The review blocks for one reason: three conclusions in the synthesis (Section 8.10, Table 414 and the closing)
contradict outcomes the run committed to:

1. The fork circuit is said to have "the same shape as Gemma's". The committed motif test reads DIFFERENT
   MOTIF (condition share 0.01; depth 0.86).
2. DAS is said to find "a handle in both families". The committed verdict at Qwen3-8B's fork is NO HANDLE:
   the edit toward BFS writes BFS in 29 of 30 programs, but 24 of them fail.
3. The fork is said to be "the highest-entropy position in every sample". Section 8.3 measures 2 of 50 and
   0 of 37 slots on two units.

The other critiques:

- **Circuit validation (unreported detail):** the circuit's held-out validation never edited the layer-0
  condition-span node; all ten of its held-out effects are exactly zero.
- **Novelty:** two published works that partly cover the base-versus-instruct result are missing
  (Cantarero et al., NeurIPS 2026 workshop; Sparse but Critical, ICLR 2026).
- **Prohibition manifold:** it is built from prompts that name the algorithms, with no control that masks
  the names.
- **Gemma comparisons:** the filtered dial is said to beat min-p and block-start temperature, neither of
  which ran on Gemma.
- **Figures:** several geometry plots from iteration 8 have no figure markers.

The full review, with the evidence and a concrete action for each critique, is in
`.terminal_claude_agent_struct_out.json`.

## Layout

| Path | What it is |
|-|-|
| `.terminal_claude_agent_struct_out.json` | The review (ReviewerFeedback schema): assessment, strengths, dimension scores, critiques, flags |
| `README.md` | This file |
| `.aii/manifest.yaml` | Storage manifest; empty, because this step created nothing heavy |
| `.aii_claude_session.json`, `.repl_agent.ptylog` | Session bookkeeping written by the agent harness |

## How the checks were run

Every check is a read-only command over the run's own files. Paths below are relative to the run directory
(`$RUN`), written as `$RUN/3_invention_loop/iter_8/...`. The ids in brackets are the artifacts' report tags.

| Check | Source file (under `gen_art/`) | What to compare |
|-|-|-|
| Report text | `gen_report_text/gen_report_text/paper_draft.md` | Sections 8.1 to 8.11 and the closing "What we have learned so far" |
| Chronology | `gen_art_evaluation_7/report_corrected.md` | Diff its lines 1-8390 against the draft's; only one marked iteration-8 note should differ |
| Record audit [art_vjtPMtWGMjsB] | `gen_art_evaluation_7/tables/recovery_by_source.csv` | Pool DAS gain over full-state gain for task T03 at ranks 1, 4 and 16: 81/80, 80/80, 79/80 |
| Fork dosing [art_vnyi0Fm5SyNH] | `gen_art_experiment_39/results/{k1_verdict,amendment,k1_cells}.json` | MAE per unit, K1c entropy hits (T10 2/50, A3 0/37), Gemma comparator fallbacks (1.636) |
| DAS [art_e-_q5mSJGrSb] | `gen_art_experiment_40/results/{analysis.json,summary.md,rinit_*.json,scan_*.json}` | `verdicts.T10-dec.verdict` = NO HANDLE; controls; clamp counts |
| Circuit [art_18XvfcJJZi1O] | `gen_art_experiment_41/results/summary.json` | `motif.primary_comparison.label` = DIFFERENT MOTIF; `validation.C1forced.per_node` held-out d of `mlp\|L0\|H-1\|COND` |
| Gemma dial [art_FJMIE9T9_PMv] | `gen_art_experiment_42/results/{analysis,dormancy}.json` | 2x2 cells, wording extension, retention and reverse recovery |
| Temperature law [art_lzuosbrb34wB] | `gen_art_experiment_43/results/{verdict,analysis_L,base_subarm,positioning}.json` | MAE on top-p-1 cells; the positioning file's "PARTLY OCCUPIED" row |
| Prohibition [art_R-HSmXq2t97f] | `gen_art_experiment_44/results/*.json`, `src/common.py` | Screen, landing and robustness counts; `ALIAS_TABLE`; `geometry_M2.json` decodability |

Example, the circuit check that found the held-out zero:

```bash
python3 -c "
import json
s = json.load(open('gen_art_experiment_41/results/summary.json'))
for x in s['validation']['C1forced']['per_node']['ablate']:
    print(x['node'], x['mean_d_pair_prompts'], x['mean_d_heldout'], x['p_sign_flip_heldout'])
"
```

Run it from `$RUN/3_invention_loop/iter_8/gen_art`. Nothing needs installing beyond Python 3.

## Restoring removed files

Nothing was removed. The manifest has no `delete` entries, so there is nothing to download or rebuild.
