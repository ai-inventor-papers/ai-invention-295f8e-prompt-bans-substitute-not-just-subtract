## What was done

**Question (Claim L, second family, secondary).** When an activation nudge moves Gemma-3-4b-it off its default
algorithm, which forecast names where the programs land?
- **q_base / r_u**: the base model's (gemma-3-4b-pt) repertoire and its runner-up algorithm (iteration 5's lead: 5 of 7);
- **q_tail / t_u**: the tuned model's OWN minority mode, from 300 twin samples per task (the confound iteration 5's
  review raised);
- **q_lik**: the tuned model's teacher-forced likelihood of each algorithm's 48-token opening under the twin prompts.

Gemma's iteration-5 landings were already seen, so everything here is a **replication**; it is never pooled with the
Qwen confirmation.

**Repairs before any new push (all frozen in commit #1, hash-chained):**
1. **Base support.** Few-shot plain completion (two solved exemplars + the target's stub; even draws use loop-only
   bench exemplars, odd draws two HumanEval+ problems from the declared dependency) adds 100 pt draws per task (stage A)
   and up to 200 more (stages B and C) for the push units still below 20 correct programs (R6, T10, T1, T2 reached the
   300-draw cap). Pooled with exp28's 1,500 pt-chat and 750 pt-plain rows.
2. **Tuned tail.** The it twin goes from 50 to 300 samples per task (200 at T 1.0, 100 at T 1.3) on exp28's exact CRN
   slots.
3. **q_lik.** Up to 10 name-scrubbed, test-passing forced programs per catalogue algorithm, written by gemma-3-4b-it
   itself (filled from the iteration-2 Qwen programs or suite references where Gemma cannot write the algorithm),
   teacher-forced under the 5 twin prompts at batch 1.
4. **Label audit.** A blind two-family judge audit (gemini-2.5-flash, gpt-4.1-mini, deepseek tie-break) of 15 pt
   programs per task, with one revision round.

**Fresh events.** 8 never-run isotropic directions (seeds 63001-63008) at α 2 (N 10, confirmation to N 30) and fresh
per-sample plan noise (PN, α 2, N 50) on the 8 tasks that moved in iteration 5, displacement-targeted at the task-spec
positions of blocks 11-22 during the prefill (exp28's push code and outlier-excluded unit).

**Events (v6).** One event per (unit, nudge type ∈ {FD, PN}), pooling exp28's and the fresh qualifying cells (pass
≥ 0.8 × twin pass); an event needs ≥ 5 correct off-default catalogue programs; the landing is the modal label if it leads
the next by ≥ 15 points.

**Tests (frozen analysis, `predictions/analysis_L_gemma.py`).** Hits of r_u / t_u / q_lik top-1 against per-event
chance 1/(K_u − 1) (exact Poisson-binomial); L1a on TAIL-EMPTY events; L1b sign test on events where r_u ≠ q_lik top-1;
the tail rival sign test; paired per-event log scores (exact Wilcoxon, BCa and unit-cluster bootstrap,
non-inferiority to q_tail at −0.10 nats); a unit-clustered version; the iteration-5 tally rescored; L2-G; a novelty
audit.

## Layout

| Path | What it is |
|---|---|
| `method.py` | pipeline driver (stages in order; `--from <stage>` resumes; starts the background label worker) |
| `src/cfg.py` | exp28's constants + the iteration-6 block at the end (push tasks, seeds 63001-63008, slots, thresholds) |
| `src/stage_inputs6.py` | S0: bench sha256 vs ITER2 commitment, dependency (10 datasets), seed audit, labeller re-check |
| `src/protocol6.py`, `src/amend0b.py` | commit #0 (protocol + frozen analysis + hardware) and commit #0b (KeyError fix) |
| `src/analysis_L.py` → `predictions/analysis_L_gemma.py` | the FROZEN analysis (forecasts, events, tests) |
| `src/prompts6.py` | few-shot pt prompts (F_bench / F_he exemplar rules) and forced prompts on exp28's `prompts.py` |
| `src/gen6.py` | GPU runner: U-tests, engine check, U6 clean states, twin top-up, forced programs, few-shot pt, fresh pushes |
| `src/qlik6.py` | q_lik: forced-program selection, scrubbing, re-labelling, fills; teacher forcing; fp32 subsample |
| `src/audit6.py` | pt label audit (+ revision), it style re-gate, novelty audit (OpenRouter, cached, capped) |
| `src/forecasts6.py` | forecast table, rescored iteration-5 events, push plan, grep audit → commit #1 |
| `src/final6.py` | events + L1 contest + splits + sensitivities, old tally, L2-G, push descriptives, pt repertoire, L3 |
| `src/engine_check6.py`, `src/tests6.py` | engine-check evaluation; CPU tests T1-T12 |
| `src/report6.py`, `src/figures6.py`, `src/outputs6.py`, `src/bookkeeping6.py` | report tables, figures, `method_out.json`, costs/timing/deviations |
| `src/chain6.sh`, `src/chain6b.sh` | the hand-off scripts actually used between GPU stages |
| `src/engine.py`, `src/push.py`, `src/units.py`, `src/prompts.py`, `src/label_worker.py`, `src/regate_rules.py`, `src/regate.py`, `src/novelty_audit.py`, `src/commit.py`, `src/analysis_E.py`, `src/predictors.py`, `src/stage_inputs.py`, `src/tests_cpu.py` | exp28's engine, push, unit, prompts, labellers, judge client and helpers (reused; `label_worker.py` also extracts few-shot rows, `commit.py` uses the iteration-6 genesis) |
| `audit/rederive_l1.py` | independent stdlib-only re-derivation of the headline numbers + placebos |
| `predictions/` | `protocol_G6.json`, `analysis_L_gemma.py`, `hardware.json` (commit #0/#0b; `analysis_L_gemma_commit0.py` is the exact commit-#0 version, sha256-verified, kept because #0b superseded it); `forecasts_G6.json`, `old_events_rescored.json`, `push_plan_G6.json` (commit #1); `forecasts_draft.json` |
| `commitments.log` | sha256 hash chain (genesis sha256('iter6_gemma_L')) |
| `data/raw_*6.jsonl` | every iteration-6 generated row (text, token ids, CRN key, precision, checkpoint, hook sha256, realised displacement) |
| `data/labels.jsonl` | labels of every iteration-6 row; `data/labels_pt_revised.jsonl` revision-round labels (if any) |
| `data/qlik_programs.jsonl`, `data/qlik_tf.jsonl` | the scored forced programs and every teacher-forced pass |
| `data/prompts_fed.jsonl` | every model-fed prompt (grep-audit registry) |
| `data/judge_cache*.jsonl` | judge caches (exp28's, extended) |
| `results/*.json`, `results/report6.md` | all analyses (see Results); `results/commit_chain.json` and `results/integrity6.json` verify the hash chain and that each commit precedes the rows it must precede |
| `docs_head.md`, `docs_static.md`, `src/build_readme.py` | the hand-written parts of this README and the script that assembles it with `results/report6.md` and the deviations |
| `figures/` | fig1-fig4 (PDF + PNG) |
| `inputs/` | sha256-verified copies of every upstream input (`inputs/SHA256SUMS`), incl. `inputs/exp28/` (exp28's rows, labels, results, predictions, src) |
| `method_out.json` | exp_gen_sol_out output (datasets gemma_l1_events, gemma_pt_repertoire, gemma_twin_tail, gemma_qlik, gemma_push_fresh) |

## How to run

`reproducibility.md` lists the exact commands that were run, in order, with seeds and hardware.

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python src/download_models.py         # pinned gemma-3-4b-it / -pt snapshots (gated; HF_TOKEN)
.venv/bin/python method.py                      # full pipeline (about 2.1 GPU-hours on one 23 GB NVIDIA L4)
.venv/bin/python method.py --from final         # re-analyse the stored rows only (CPU)
.venv/bin/python audit/rederive_l1.py           # independent re-derivation of the headline numbers
```

Environment: Python 3.12, torch 2.8.0+cu128, transformers 4.57.6 (`pyproject.toml` pins every package). The HF cache
is the run's shared cache (`HF_HOME`), not this folder. `paths.local.json` (not published) maps upstream artifact names
to their folders; only the preflight stage reads it.

## Restoring removed files

Every `delete` entry of `.aii/manifest.yaml` and the command that brings it back:

| Removed path | Restore with |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` (or `./restore.sh`) |
| `**/__pycache__/` | `.venv/bin/python -m compileall src audit inputs/exp11/bench inputs/exp8/suite` (also recreated by any run) |
| model weights (shared Hugging Face cache, outside this folder) | `.venv/bin/python src/download_models.py` (pinned revisions `093f9f388b31de276ce2de164bdc2081324b9767` / `cc012e0a6d0787b4adcc0fa2c4da74402494554d`; both in `./restore.sh`) |

Nothing heavy is kept outside text files: no activation cache is written (the U6 check reads exp28's cache in place).
