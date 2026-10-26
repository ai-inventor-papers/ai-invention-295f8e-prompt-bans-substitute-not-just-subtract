# Review of the iteration-6 research record (REVIEW_REPORT step)

This folder holds an adversarial audit of the run's internal research report after iteration 6. The report records a
study of algorithm choice ("creativity") in open-weight code models (Qwen3-8B, Llama-3.1-8B-Instruct, gemma-3-4b-it,
Qwen2.5-7B-Instruct). The audit checks completeness, traceability, what each iteration learned, and whether the claims
stay within their evidence.

## What was done

1. Read the report and the previous (blocking) review, and checked each of its must-fix items against iteration 6.
2. Walked the six iteration-6 artifacts (record audit `art_aRTQM6CQ0Dre`, engine control `art_lpQalcAXMGr1`, exchange and
   site experiment `art_rMlbrjVB1c__`, Gemma feature experiment `art_zNyBP6zieI5u`, NLA experiment `art_dbUtqBjT0tPf`,
   positioning audit `art_OUuQUYQn5voE`) and compared their result files with the report's tables.
3. Recomputed the headline numbers from the artifacts' raw rows with independent scripts (`recompute/`), for example:
   - engine-control escape fractions, screen passes, per-slot paired flips and plan-noise counts;
   - Stage A cell counts per exchange band, on attempts and on correct programs;
   - the movability Spearman correlation, its Bonett-Wright interval and the frozen rivals.
4. Checked the not-run direction (`experiment_iter6_dir4`) is named as planned and not run.
5. Wrote the structured review (`.terminal_claude_agent_struct_out.json`).

## Layout

| Path | Content |
|---|---|
| `.terminal_claude_agent_struct_out.json` | The review (scores, strengths, critiques, coverage, blocking flag) |
| `build_review.py` | Builds the review JSON; asserts the blocking rule (soundness <= 1 or results not reported) |
| `recompute/recompute_engine.py`, `.out.txt` | Engine control: two-stage escape rule re-implemented from its docstring; E per engine and task at alpha 2 |
| `recompute/slotflips.py`, `.out.txt` | Engine control: common-random-number paired flips between engines on the 400 screen slots |
| `recompute/pn_counts.py`, `.out.txt` | Engine control: per-sample plan-noise counts on valid attempts and on correct programs |
| `recompute/stagea.py`, `.out.txt` | Exchange experiment: Stage A counts per task, cell and band (Y on attempts and on correct programs) |
| `recompute/mov.py`, `.out.txt` | Record audit: movability Spearman, Bonett-Wright interval, permutation p, rival correlations |
| `.aii/manifest.yaml` | Storage manifest (nothing heavy in this folder) |

## How to run

The scripts need only the Python 3.12 standard library. Each reads one artifact folder, located by an environment
variable. The default is the artifact's sibling folder in the published repository:

```bash
export EXP29_DIR=../art_lpQalcAXMGr1     # engine control
export EXP30_DIR=../art_rMlbrjVB1c__     # exchange and site experiment
export EVAL5_DIR=../art_aRTQM6CQ0Dre     # iteration-6 record audit
cd recompute
for f in recompute_engine slotflips pn_counts stagea mov; do python3 -I $f.py > $f.out.txt; done
cd .. && python3 -I build_review.py
```

## Restoring removed files

Nothing in this folder is marked for deletion: it holds only small text and code files. The inputs are the artifacts
named above, which live in their own folders.
