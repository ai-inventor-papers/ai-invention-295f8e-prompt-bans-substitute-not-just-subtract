# Review of the iteration-7 research record (REVIEW_REPORT step)

This folder holds an adversarial audit of the run's internal research report after iteration 7. The audit checks
whether every executed artifact is written up, whether the numbers trace to artifact files, and whether the
conclusions stay within what the artifacts show. It is a review, not an experiment: no model was run.

## What was done

1. The iteration-7 sections (7.1 to 7.11 and the closing) were read against the seven iteration-7 artifacts:
   the record audit (art_LzP2qPwUrANz), DAS (art_veI9l_Rb9wDY), forks (art_pHL7LWNhpcCS), temperature
   (art_MZAfDPVhM6Ui), dose unit (art_8O5eaNc5gxJs), evolutionary search (art_VhaHGe7SxV95) and Gemma
   (art_HY7uYZz-OjRW).
2. Sections 1 to 6 of the current report were diffed against the record audit's corrected text
   (`report_corrected.md` in art_LzP2qPwUrANz). The only differences are rewordings inside iteration-7
   corrections, so the chronology is intact.
3. The headline numbers the review cites were re-derived from the artifacts' own result and row files by
   `recompute_checks.py`, which uses the standard library only. Its output is saved in `recompute_checks_output.txt`.
4. The findings are written to `.terminal_claude_agent_struct_out.json` in the ReviewerFeedback schema.

## Layout

| Path | Content |
|-|-|
| `.terminal_claude_agent_struct_out.json` | The review: assessment, strengths, dimension scores, critiques, flags and score |
| `recompute_checks.py` | Re-derives the cited numbers from the iteration-7 artifacts: DAS per-source recovery, the counting-sort labels and audit classes, fork-margin and axis Spearman, the unit-by-seed 2x2, level-b clusters in the search, and the Gemma prefill asymmetry and prediction gaps |
| `recompute_checks_output.txt` | The script's output at review time |
| `.aii/manifest.yaml` | Storage decisions (no heavy files) |

## How to run

```bash
# From this folder, in the run layout (<run>/round-7/review):
python3 -I recompute_checks.py
# Elsewhere, point the script at the iteration-7 gen_art folder:
AII_GEN_ART=/path/to/iter_7/gen_art python3 -I recompute_checks.py
```

The script needs only Python 3.10+ and read access to the artifact folders.

## Restoring removed files

None. This folder holds no heavy or regenerable files, and nothing is marked for deletion.
