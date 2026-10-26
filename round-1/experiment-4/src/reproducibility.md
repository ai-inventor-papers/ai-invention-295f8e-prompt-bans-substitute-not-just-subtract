# Reproducing the de-commitment steering screen

This file describes what was actually run to produce the results in this folder (artifact
`gen_plan_experiment_4_idx5`). Every path below is relative to this folder.

## 1. Get the artifact

The workspace is published as one folder of a public GitHub repository.

```bash
git clone <repository-url>
cd <repository>/<this-artifact-folder>        # the folder that contains method.py and this file
```

The published folder leaves out the content-addressed caches (`cache/labels*/`, `cache/tests*/`,
`cache/judge/`), the R-state arrays (`cache/hR_*.npy`) and `.engine_cache/`. All of them are regenerated
by the commands below. Note that the judge outputs come from paid LLM calls, so a re-run produces new
judge outputs rather than the original ones.

## 2. System, Python and libraries

What was used:

* Debian 12 container on Linux 6.8, which behaves the same as Ubuntu for these steps.
* NVIDIA driver 595.91 (CUDA 13.2 driver); the torch wheels are CUDA 12.8 builds.
* No compiler. Because of that, torch inductor cannot run, so vLLM runs in eager mode.
* Python 3.12.14 and uv 0.6.14.

```bash
# system: an NVIDIA driver that supports CUDA 12.8 wheels; curl; uv (https://docs.astral.sh/uv/)
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r requirements.txt     # 177 exact pins, identical to pyproject.toml
```

Key pins (all 177 are in `requirements.txt` and `pyproject.toml`): vllm==0.11.0, torch==2.8.0,
transformers==4.57.1, numpy==2.2.6, scipy==1.18.1, scikit-learn==1.9.1, statsmodels==0.15.0,
matplotlib==3.11.2, loguru==0.7.3, openai==3.35.1. uv first resolved transformers 5.x for vllm 0.11.0,
and it was then pinned back to 4.57.1 by hand. The pins above reproduce the final environment.

## 3. Model, data and credentials

* Model: `Qwen/Qwen3-8B`, snapshot `b968826d9c46dd6066d109eabc6255188de91218` (about 16 GB):
  `.venv/bin/hf download Qwen/Qwen3-8B` (or `huggingface-cli download Qwen/Qwen3-8B`). The code finds it
  in the Hugging Face cache (`HF_HOME`), and `env.sh` sets `HF_HUB_OFFLINE=1` for the GPU stages.
* No dataset downloads. The two tasks, their hidden tests and the reference programs are generated in
  `tasks/` with fixed seeds. No other artifact's outputs are used. The run's user-upload folder was empty,
  so no private input is needed.
* Environment variables, by name only:
  * `OPENROUTER_API_KEY` and `OPENROUTER_BASE_URL`, for the LLM judge (`labeller/judge.py`,
    `labeller/gate.py`). The judge cost was $0.06.
  * `HF_HOME` (optional cache location) and `HF_TOKEN` (optional).
  * `AII_DATA_FIG_GEN_SCRIPTS` (optional). This points at a house-style matplotlib helper; without it,
    the figures fall back to plain matplotlib.

## 4. Commands, in the order they were run

Hardware: one NVIDIA RTX A4500 (20 GB), an 11-CPU cgroup quota and 57 GB RAM. GPU stages read
`source env.sh`, which keeps the engine caches inside `.engine_cache/`.

| # | command | what it does | wall time |
|---|---|---|---|
| 1 | `.venv/bin/python prompts/make_paraphrases.py` | writes `prompts/paraphrases.json` (deterministic templates) | seconds |
| 2 | `source env.sh && .venv/bin/python gpu/hf_states.py` | R-states for 930 prompts → `cache/hR_*.npy`; hook layer test | 1.6 min |
| 3 | `.venv/bin/python tasks/build_tests.py` | hidden tests (seed 20261019) + time limits from reference timings; R0 gate; labeller unit tests | 1.5 min |
| 4 | `.venv/bin/python analysis/directions.py` (then `--commitment-only`) | `directions/`, `results/layer_selection.json` (L* = 18), diagnostics, commitment test | 7 min CPU |
| 5 | `source env.sh && .venv/bin/python gpu/vllm_gen.py --session s1` | baseline N = 200 + enumerate N = 100 per task | 28 min (12.7 min lost to the failed compiled start) |
| 6 | `.venv/bin/python labeller/daemon.py &` | background labelling (tests + tracer + AST) during all GPU stages | — |
| 7 | `source env.sh && .venv/bin/python gpu/hf_steer.py --budget-min 125` | hook tests, stage 10, layer rule, dc grid, c* + bisection, rand1/rand2, placebo, breadth, transfer | 78.6 min |
| 8 | `.venv/bin/python labeller/judge.py --bulk --cap 0.80` | judge for runtime/AST disagreements (run after every labelling wave) | < 1 min each |
| 9 | `.venv/bin/python labeller/gate.py` | labeller gate. It failed on T2 at first; revision round 2 was applied, the caches were cleared, `tasks/build_tests.py --reuse-limits` was re-run, everything was re-labelled, and then the gate passed | 1 min |
| 10 | `.venv/bin/python analysis/forecast.py modal` then `commit-ban` | modal modes and sha256-committed ban forecasts | seconds |
| 11 | `source env.sh && .venv/bin/python gpu/vllm_gen.py --session s2 --with-mention` | ban:X_t + mention:X_t, N = 100 each (the guard checks the commit log) | 8.7 min |
| 12 | `.venv/bin/python analysis/forecast.py commit-succ` | realised modes → committed succession forecasts | seconds |
| 13 | `source env.sh && .venv/bin/python gpu/vllm_gen.py --session s3` | succession:2, N = 100 per task | 5.9 min |
| 14 | `.venv/bin/python labeller/daemon.py --once && .venv/bin/python labeller/judge.py --bulk` | final labels | 1 min |
| 15 | `.venv/bin/python method.py --stages analyze` | record_meta, sha verification, `analysis/analyze.py`, `analysis/figures.py`, `analysis/method_out.py` | 6 min |
| 16 | `.venv/bin/python tests/test_screen.py`; `source env.sh && .venv/bin/python gpu/vllm_determinism.py` | CPU checks; vLLM same-seed check | 1 + 4 min |
| 17 | `.venv/bin/python analysis/audit_rederive.py`; `.venv/bin/python analysis/audit_commitment_perm.py` | independent re-derivation and shuffle / exact-permutation checks | 1 min |

The single command `.venv/bin/python method.py` runs stages 1–15 in order. It skips every stage whose
outputs already exist, so it also resumes an interrupted run.

Seeds and configuration:

* Seeds come from `stable_hash`, which takes the first 8 hex digits of a sha256 of the joined parts:
  * vLLM engine seed 1234; per-request seed `stable_hash(task, condition, paraphrase_id)`.
  * HF uses `torch.manual_seed(stable_hash(task, paraphrase_id))` before every batch of every arm
    (common random numbers).
  * Random directions use `stable_hash("rand", k, task, layer)`.
  * Bootstrap seeds are fixed in the code.
* Decoding everywhere: temperature 1.0, top-p 1.0, top-k disabled, min-p 0, repetition penalty 1.0.
  Max tokens are 1024 (vLLM), 1536 (enumerate) and 768 (HF).

Known sources of non-reproducibility:

* vLLM text is not bit-for-bit reproducible even with the same per-request seed: the check failed on T1
  and passed on T2 (`results/vllm_determinism.json`).
* HF generations depend on the GPU and kernel versions.
* Hidden-test time limits are derived from reference timings on the machine that runs `build_tests.py`.
* A fresh run makes new judge calls.

Re-running therefore reproduces the distributions and the statistics up to sampling noise, not the
individual samples. The stored `data/raw/` and `cache/judge/` reproduce the reported numbers exactly
through step 15.

## 5. What you should get

* `results/screen_verdict.json` → `overall = "PARTIAL"`.
  * T1: S_flat false, all-BFS at every arm except the bans.
  * T2: S_flat true, rarefied ΔHill +0.65 with 90 % cluster CI ≈ [0.31, 0.97]. S_specific false,
    because dc − rand1 = +0.07 [−0.26, 0.39].
* `results/cstar.json` → c* = 0.1 (T1, pass 0.98) and c* = 0.25 (T2, pass 0.78). T2 at c = 0 has
  pass 0.95.
* `results/condition_summaries.json` / `results/buy_table.csv` give every arm's pass rate, label counts
  and ΔHill:
  * T2 dc@0.25: bf/spfa 54, dijkstra 23, other 1.
  * T2 rand1: dijkstra 53, bf/spfa 26.
  * T2 ban: dijkstra 49, bf/spfa 38, ΔHill +0.79.
  * enumerate: ΔHill 0.00 (T1) and −0.08 (T2).
* `results/commitment_test.json` → δκ(ban − mention) = +0.039 (T1) and +0.053 (T2); positive control
  +0.54 / +0.58. `results/audit_commitment_perm.json` → exact permutation p = 0.021 / 0.007.
* `results/predict_row.json` → T2 ban event: dc log score −0.058, freq_vllm −0.219, uniform −1.406. The
  T1 forecasts tie because they are degenerate.
* Gates: `results/r0_gate.json` (PASS / PASS), `results/labeller_gate.json` (PASS / PASS),
  `results/engine_check.json` (PASS / PASS), `results/steer_state.json → hook_tests` (all true),
  `results/unit_tests.json` (all true), `results/vllm_determinism.json` (FAILED on T1).
* Figures `figures/fig1_dose_response`, `fig2_label_distributions`, `fig3_tv_vs_delta_hill`,
  `fig4_commitment_kappa` and `fig5_layer_profiles` (PDF + PNG). These are the figures the paper's
  results section draws on: dose-response, label shifts, move-versus-flatten, commitment coordinate and
  direction diagnostics.
* `method_out.json` (exp_gen_sol_out schema) and its `full_` / `mini_` / `preview_` variants.
