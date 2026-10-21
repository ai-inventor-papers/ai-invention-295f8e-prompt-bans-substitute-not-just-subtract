# How far can bans and token vetoes push? (iteration 3, step 4, Qwen3-8B)

__RESULTS__

## What this artifact does

One model, **Qwen/Qwen3-8B** (thinking off unless stated), six tasks: the path-task screen **T1** (grid path) and
**T2** (weighted shortest path), and the frozen bench tasks **T03** (k-th smallest), **T04** (substring search),
**T06** (find duplicate) and **T10** (connected components). Path tasks and bench tasks are always reported
separately and never pooled.

| arm | what it is | comparator / control in the same pipeline |
|---|---|---|
| 4b token walk | persistent logit veto of the default's *distinctive token n-gram* under the neutral twins (no ban text); up to 2 extra mask rounds when a vetoed algorithm re-emerges or the vetoed string leaks through another tokenisation; the next landing is vetoed next (cumulative, up to 5 algorithms) | step 0 = same prompts, no veto; **sham veto** = an algorithm-generic n-gram of matched length and presence; **fixed TOP5 veto** (T1) vs exp9's TOP5 prompt ban |
| 4a prompt reach | 17 leave-one-survivor (LOS) ban lists on the bench tasks (N = 50 each) and two-step bans {default, rung 2} on all six tasks (N = 100) | forced **can** (labelled-and-correct) as the capability ceiling; exp9's T2 LOS; the walk |
| 4c long-form novelty | the request's two "make a (fully) novel algorithm ... 2,000-word rationale" instructions, thinking off and on | label composition vs the catalogue; two blind judges + a manual pass against human/known solutions from the declared dataset dependency |

Every mask, forecast and protocol was committed to the sha256 hash chain in `commitments.log` **before** the samples
it governs (`src/commit.py`; verified in `method_out.json → metadata.commitments`).

__DETAILS__

## Layout

| path | contents |
|---|---|
| `method.py` | CLI (`s0`, `server`, `unit`, `phase A/B`, `longform`, `audit`, `analyze`, `outputs`) and the `method_out.json` assembly; the deviation list |
| `src/config.py` | task registry (catalogues, defaults, display names, analysis sets), decoding, seeds, thresholds, paths |
| `src/veto.py` | the persistent n-gram veto: a vLLM V1 `AdapterLogitsProcessor` (`--logits-processors veto:NGramVeto`), per-request veto lists through `vllm_xargs` |
| `src/server.py`, `src/client.py` | PID-managed vLLM OpenAI server (bf16 or FP8) and the async client (token-id prompts, returned output ids, explicit sampling params, two-phase thinking) |
| `src/prompts.py` | neutral twins (T1/T2: exp8 frozen ids, asserted identical; bench: first neutral noun + `' .'` padding to the ban's token length), LOS/two-step bans, long-form prompts |
| `src/ngram.py` | distinctive n-gram tool, sham n-gram, mask expansion (space/newline/bare variants), occurrence and string-leak detection, unit tests |
| `src/walk.py` | the walk state machine (`WalkArm`), sham / fixed-TOP5 arms (`MaskArm`), the lockstep scheduler with filler jobs |
| `src/reach.py` | LOS / two-step job builders and the committed forecasts (rung table, C3 cells, list-independence, WALK2/ASSOCIATE/SNAPBACK) |
| `src/longform.py` | long-form generation (thinking off/on), last-code-block extraction, rationale word counts |
| `src/label.py` | one API over the two frozen labellers (bench exp11 pipeline; exp1 suite via exp8): runtime primary, AST second, blind judge on disagreement |
| `src/judge.py` | every OpenRouter call: cache, `usage.cost` budget, own stop at USD 0.95, stop at the first per-run budget refusal |
| `src/audit.py`, `src/manual.py` | known-solution corpus from the dependency dataset, nearest neighbours, judge controls, two-judge audit, claim extraction; manual-pass extra tests |
| `src/analysis.py`, `src/figures.py`, `src/rederive.py`, `src/stats.py` | all reported numbers, figures, independent re-derivation + placebo, statistics helpers |
| `src/phases.py`, `src/recheck.py` | GPU phase drivers, S0 checks, veto unit tests; labeller re-check on gold sets and references |
| `src/dep_usage.py` | how each of the 10 datasets of the declared dependency enters this artifact (`results/dependency_usage.json`) |
| `scripts/chain_phase_b.sh`, `scripts/chain_thinking.sh` | the GPU job chaining actually used (one server on the GPU at a time, PID-based waits) |
| `audit/manual_round1.py`, `audit/manual_round2.py`, `audit/apply_manual.py` | the executor's manual-pass decisions (one rule per program family, written after reading every program it covers) and their application to the audit records (`results/manual_audit.json`) |
| `scripts/build_readme.py`, `scratch/readme_*.md` | assembles this README from the result sections (tables filled from `results/*.json`) |
| `restore.sh`, `pyproject.toml`, `requirements.lock.txt` | recreate `.venv/` (all 180 packages pinned; the lock file is the `uv pip freeze` of the venv) and fetch the model weights |
| `reproducibility.md` | what was actually run, in order, with hardware, timings, failures and the numbers a reader should get |
| `scripts/verify_headlines.py` | short independent re-derivation of every headline number from the raw per-sample files, with placebo runs of each test (`results/verify_headlines.json`) |
| `inputs/` | read-only copies of every upstream file used (bench, suite, exp7/8/9/11 data) + `SHA256SUMS`; `known_solutions.jsonl` (built from the dependency dataset) |
| `predictions/` | every committed mask, forecast and protocol (hash-chained) |
| `data/samples_<arm>.jsonl` | one row per program (shared schema: model, task, condition, template, arm, sample_id, seed, prompt_sha256, label, labeller_source, passed, finish_reason, n_new_tokens, code_sha256, code, + step/round/veto/leak/thinking fields) |
| `data/raw_<arm>.jsonl` | raw generations (text, output token ids, veto sequences) |
| `data/label_cache.jsonl`, `data/llm_cache.jsonl` | labeller results per unique program; every LLM response (judges, audit, claims) |
| `results/` | `walk.json`, `can.json`, `c3.json`, `reach.json`, `list_independence.json`, `disguise.json`, `reach_events.jsonl`, `longform.json`, `fp8_crosscheck.json`, `novelty_audit*.json`, `claims.json`, `audit_controls*.json`, `labeller_recheck.json`, `veto_unit_tests_*.json`, `state_*.json`, `costs.json`, `rederive.json`, `manual_audit.json`, `dependency_usage.json`, `known_solutions_summary.json`, `not_run.json`, `inputs_check.json`, `longform_branch.json`, `sham_not_constructible_*.json`, `scheduler_timings_*.json` |
| `figures/` | `fig1_token_walk`, `fig2_will_vs_can`, `fig3_reemergence`, `fig4_longform`, `fig5_sham_vs_distinctive` (PDF + PNG) |
| `method_out.json` (+ `full_`/`mini_`/`preview_`) | `exp_gen_sol_out`: datasets `token_walk` (1,750), `prompt_reach` (1,450), `long_form` (575), `audit` (53); every example has `predict_*` fields (baseline default; committed forecast; LOS survivor and C3 forecast; WALK2/ASSOCIATE/SNAPBACK; judge guesses); metadata = every analysis above + deviations + costs + versions + commitment chain |
| `uv.lock` | the lock uv wrote when `uv run method.py` synced the environment from `pyproject.toml` |
| `logs/` | per-stage logs, server logs, `timings.jsonl` |

Everything here is text and stays on the run's volume at these relative paths; no file is 100 MB or larger.

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
export PYTHONDONTWRITEBYTECODE=1
.venv/bin/python method.py s0
.venv/bin/python method.py server bf16 start 4608 32      # Qwen3-8B bf16 at revision b968826d...
.venv/bin/python method.py unit bf16
.venv/bin/python method.py phase A                        # T1/T2 walk + shams + fixed TOP5 (+ forecasts)
.venv/bin/python method.py phase two_step path bf16       # path two-step bans from the committed forecasts
.venv/bin/python method.py longform bf16                  # concurrently with phase A
scripts/chain_phase_b.sh                                  # swap to FP8, unit tests, bench walk + LOS + two-step, FP8 long-form
scripts/chain_thinking.sh                                 # thinking-on floor (T1/T2, N=10 per prompt) after phase B
.venv/bin/python src/longform.py fp8_on T03:0-10,T04:0-10,T06:0-10 8   # bench thinking-on (after FP8 thinking-off)
export DEP_DATASET_DIR=../gen_art_dataset_1                  # the declared dataset dependency (art_j3Rm_lr2nzR6)
.venv/bin/python method.py audit corpus && .venv/bin/python src/dep_usage.py && .venv/bin/python method.py audit controls
.venv/bin/python method.py audit pool && .venv/bin/python src/manual.py sheet   # then read the sheet
.venv/bin/python audit/apply_manual.py && .venv/bin/python method.py audit claims && .venv/bin/python src/recheck.py
.venv/bin/python method.py analyze && uv run method.py           # no argument = rebuild method_out.json (~1 min, no GPU)
```

No C compiler exists on the machine this ran on, so vLLM runs eager with `TORCH_COMPILE_DISABLE=1`; the FP8
checkpoint uses vLLM's weight-only FP8 Marlin kernels (`VLLM_TEST_FORCE_FP8_MARLIN=1`), as exp11 did.

## Restoring removed files

The `.aii/manifest.yaml` marks only the virtual environment for deletion:

| removed path | restore with |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` |

The model weights live in the run's shared Hugging Face cache (outside this folder). To fetch them elsewhere:

```bash
huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218
huggingface-cli download Qwen/Qwen3-8B-FP8
```

`restore.sh` runs all three commands.
