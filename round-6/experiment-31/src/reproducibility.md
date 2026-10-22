# Reproducing panel I (iteration 6, Step 3)

This file describes what was actually run, in the order it was run, including the restarts and fixes. Every path
below is relative to this artifact's folder.

## 1. Get the artifact

The workspace is published as one folder of a public GitHub repository.

```bash
git clone <repository-url>
cd <repository>/<this-artifact-folder>        # the folder that holds this file, method.py and pool_l1.py
```

The only declared input is the dataset artifact **art_j3Rm_lr2nzR6** (`full_data_out.json`, 96 MB). The repository
publishes it as a sibling folder; the code reads it through one environment variable, `AII_DEP_ART_J3RM`, whose
default is the sibling folder `../art_j3Rm_lr2nzR6` (see `src/extract_sources6.py`). The rows this artifact uses are
already extracted into `inputs/sources.json`, so the dependency is needed only to redo stage S1. No user-uploaded
file was used (the run's upload folder was empty).

## 2. System, Python and libraries

- Ubuntu 22.04-class container, NVIDIA driver with CUDA >= 12.8 support (the run had driver 595.91, CUDA 13.2).
- Python 3.12.14 and `uv` 0.6.14 (uv virtual environments have no `pip`; `uv pip freeze` was used to pin).
- Environment (exact pins in `requirements.lock.txt`, mirrored in `pyproject.toml`):

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r requirements.lock.txt
```

Key versions: vllm 0.11.0, torch 2.8.0, transformers 4.57.6, tokenizers 0.22.2, numpy 2.2.6, scipy 1.18.1,
matplotlib 3.11.2, openai 3.35.1, loguru 0.7.3, accelerate 1.15.0, pandas 3.0.6, xformers 0.0.32.post1.

## 3. Models, data and environment variables (names only)

- Models (pinned revisions), downloaded with `huggingface_hub.snapshot_download` into the Hugging Face cache:
  - `Qwen/Qwen3-8B` revision `b968826d9c46dd6066d109eabc6255188de91218` (instruct)
  - `Qwen/Qwen3-8B-Base` revision `49e3418fbbbca6ecbdf9608b4d22e5a407081db4` (base)

  ```bash
  huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218
  huggingface-cli download Qwen/Qwen3-8B-Base --revision 49e3418fbbbca6ecbdf9608b4d22e5a407081db4
  ```
- `HF_HUB_CACHE` (where the snapshots live; `src/cfg6.py:model_path` resolves the pinned snapshot folder there),
  optionally `HF_TOKEN`.
- `OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY`: blind LLM judges (openai/gpt-4.1-mini, google/gemini-2.5-flash,
  deepseek/deepseek-chat-v3.1). Judge answers are cached in `data/judge_cache.jsonl`, so the gate, adjudication and
  label-QA steps replay without new calls; the novelty audit calls its judges again (3 calls, about USD 0.001).
- `AII_DEP_ART_J3RM`: folder of the dependency dataset (default `../art_j3Rm_lr2nzR6`).

## 4. Hardware and what was run, in order

Hardware: one NVIDIA L4 (22.0 GiB usable, compute capability 8.9), 48 CPU cores. Wall clock about 4 h; GPU time about
1 h 45 min (vLLM 31.5 min, HF engine 71 min). OpenRouter spend USD 0.34 over 1,411 calls.

Seeds: there is no global seed. Every random stream is derived from the sha256 rules in `src/cfg6.py` (directions,
plan noise, GTN, the CRN uniform streams of the HF engine and the per-request vLLM seeds), the hidden tests use
`random.Random(<LeetCode id>)`, and every bootstrap / permutation uses seed 0.

| step | command (run from this folder with `.venv/bin/python`) | notes, runtime |
|---|---|---|
| 1 | `src/extract_sources6.py` | dependency rows -> `inputs/sources.json`, `results/dependency_usage.json` (seconds) |
| 2 | `src/build_prompts6.py` | 444 prompts, grep audit, base-tokenizer identity (1 min) |
| 3 | commit #0: `python -c` calling `src/commit6.py:commit([...], 'commit0')` on `predictions/protocol_v6_panelI.json`, `src/units_spec6.py`, `src/cfg6.py`, `src/prompts6.py`, `data/prompts.jsonl`, `results/grep_audit.json`, `src/vllm6.py`, `src/commit6.py`, `inputs/sources.json` | first line of `commitments.log` |
| 4 | `src/vllm6.py --phase instruct --units I1,I2,I3,I4,I5,I6,I7,I8,I9,I10 --deadline-min 70` | 4,435 rows, 4.8 min |
| 5 | `src/unitbuild6.py I1`, then I2..I10 (in parallel), then `src/unitbuild6.py I2`, `I4`, `I5`, `I6`, `I8`, `I10` again sequentially | stage (i) after the rule fixes listed in README deviations `stage_i_build_fixes` |
| 6 | `src/vllm6.py --phase base --units I1,...,I10 --deadline-min 75` | the first engine start failed; the built-in fallback (enforce_eager, max_model_len 1792, utilisation 0.97) ran; 3,300 rows, 25.2 min |
| 7 | `src/label6.py --follow` (background) | restarted once after the sandbox stdout fix (`sandbox_stdout`) |
| 8 | `src/hf6.py all --units I1,...,I10 --stop-at-utc 2026-10-22T00:25:00Z` (background) | first start stopped at G6; restarted with batch-1 teacher forcing; memory probe B = 12, GPU tests, HF twin (500 rows), then waits for steps 10-12 |
| 9 | `src/gate6.py I1` ... `I10` (in parallel); I10 failed, its rules were revised (`i10_revision_round`), its labels moved to `data/labels_superseded_I10_gate1.jsonl` and relabelled by the worker; `src/gate6.py I10 --revision` | gate (ii) |
| 10 | `src/gate6.py I1,I2,I3,I4,I5,I6,I7,I8,I9 --post`; `src/forced6.py I1,...,I9`; `src/forced6.py I10`; `python -c` calling `src/labels_view6.py:adjudicate_pending()` | adjudication, base audits, forced verification; the HF runner then computed q_lik |
| 11 | addendum 1: `python -c` calling `commit([...], 'addendum1_pre_nudge_analysis_code')` on `pool_l1.py`, `tests/test_pool_l1.py`, `results/pool_l1_synthetic_tests.json` and the `src/` engine, labeller and instrument code | before the first nudge |
| 12 | `src/instruments6.py commit I1,...,I10`; `src/instruments6.py enrol I1,...,I10 --final` | per-unit commits and the enrolment hash; the HF runner then nudged the 10 units (22:24-23:29 UTC, 71 min of HF time in total) |
| 13 | `src/bint6.py --units I1,...,I10` | 300 BINT rows on vLLM, 1.5 min |
| 14 | `python -c` calling `adjudicate_pending()`; `src/gate6.py I10 --post` | remaining adjudications; I10 base audit |
| 15 | `analysis/build_events.py`; `pool_l1.py --events landing_events.json --units units.json --out results/pool_l1_panelI.json`; `analysis/secondary.py`; `analysis/novelty.py`; `analysis/label_qa.py`; `analysis/harness_check.py`; `analysis/figures.py`; `analysis/outputs.py`; `analysis/summary.py`; `audit/rederive.py`; `audit/rederive_headlines.py`; `audit/commit_order.py`; `tests/test_cpu.py` | about 10 min on CPU |
| 16 | `python -c` calling `commit([...], 'final_results')`, then `commit([analysis/novelty.py, results/deviations.jsonl], 'amendment_novelty_cost_logging')` | final chain entries |

`uv run method.py --stage all` runs the same stages in the same order without the interactive restarts;
`uv run method.py` (default stage `analysis`) re-runs step 15 only and needs no GPU.

Reproducibility limits: the HF engine is byte-deterministic on the same GPU and software (GPU test G1), and vLLM rows
use per-request seeds, but bf16 kernels can produce different token trajectories on another GPU type or driver.
Judge models behind OpenRouter can change; the cache makes the reported labels replayable.

## 5. Output files and the numbers a reader should get

| file | what to check |
|---|---|
| `results/pool_l1_panelI.json` | 7 landing events of 30 (unit, nudge type) pairs; L1a n = 1, 1 hit, p = 0.333 (DESCRIPTIVE); L1b n = 6, b = 4, c = 2, sign-test p = 0.344 (FAIL under the frozen rule); unit-clustered L1b 2 vs 1 (DESCRIPTIVE); log-score D = base - q_lik +0.951 nats (event-bootstrap lower bound +0.32), base - q_tail +0.253 (lower bound -0.05 per event, -0.16 per unit cluster) |
| `landing_events.json`, `units.json` | the inputs of `pool_l1.py` for pooling with panel II (schema `iter6_landing_v1`); r_u named the landing in 5/7 events, t_u in 5/6 |
| `results/l2.json`, `results/novelty.json` | L2: 0 of 477 correct nudged off-default programs in base-absent modes; novelty: 1 distinct correct 'other' program among 8,936 correct programs, a catalogue variant |
| `results/m.json` | twin modal share vs E_u rho -0.89 (Holm p 0.016); beta rho +0.71 (one-sided p 0.014, Holm 0.07) |
| `results/k.json` | rarefied Hill-1 vs pass cost per knob and unit (table in README) |
| `results/rederive.json`, `results/rederive_headlines.json` | 0 mismatches; every headline number re-derived from the raw row files; placebos fail (random r_u: L1b p < 0.05 in 0% of draws; permuted E_u: 3.5%; random forecast never reaches the observed log-score gain) |
| `results/commit_order.json`, `results/cpu_tests.json`, `results/gpu_tests.json` | integrity proof, CPU tests (pass), GPU tests (G1-G5 pass, G6 fail with the batch-1 fallback) |
| `method_out.json` (+ `full_`/`mini_`/`preview_`) | exp_gen_sol_out, validated with the aii-json schema |
| `figures/F1..F6` | the panel-I figures (PDF + PNG) |

These are the numbers the paper's panel-I results should cite; README.md ("Results (panel I)") states them with
their reading, and `results/summary.md` holds every table.
