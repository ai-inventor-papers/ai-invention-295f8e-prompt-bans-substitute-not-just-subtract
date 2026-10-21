# Reproducing artifact E (did 8-bit arithmetic cause the nudge effect?)

Everything below is what was actually run, in order, on one NVIDIA L4. Every path is relative to this folder.

## 1. Get the artifact

This folder is published as one folder of a public GitHub repository:

```bash
git clone <the repository URL>
cd <repository>/<this artifact's folder>        # the folder that holds method.py and this file
```

The code finds the declared dataset dependency **art_j3Rm_lr2nzR6** (the algorithm-choice source data; only
`full_data_out.json` is read, by `src/dep_usage_e.py`) through ONE constant, `cfg.DEP_DATASET_DIR`:

1. the environment variable `ART_J3RM_DIR`, if set;
2. else the published sibling folder `../art_j3Rm_lr2nzR6`;
3. else the run layout.

The read-only inputs from earlier iterations (exp19, exp22, exp23, exp24, exp25, exp27, exp18 and exp19's own
inputs: exp7/8/11/13/16/17 and eval2) are copied into `inputs/`. Their sha256 values are listed in
`predictions/e_inputs.json` (committed in `commitments.log`).

No user-uploaded material is used.

## 2. System, Python and libraries

- Ubuntu/Debian with an NVIDIA driver that supports CUDA 12.8 (this run used driver 595.91.07).
- Python 3.12.
- `uv` (this run used uv 0.6.14). There is no `pip` binary in the venv.

```bash
uv sync --frozen        # creates .venv from uv.lock; pyproject.toml pins every package to the installed version
```

Key pins:

- torch 2.8.0+cu128 (needs `torch.mm(..., out_dtype=torch.float32)` and `torch._scaled_mm`);
- transformers 4.57.6 (exp19's PreallocLayer relies on its Cache internals);
- numpy 2.2.6, scipy 1.18.1, statsmodels 0.15.0, ml-dtypes 0.6.0, openai 3.35.1, loguru 0.7.3.

`logs/uv_pip_freeze.txt` holds the full frozen list (84 packages).

## 3. Model, environment variables and keys (names only)

- Model: `Qwen/Qwen3-8B` at revision `b968826d9c46dd6066d109eabc6255188de91218`, about 16.4 GB of bf16 safetensors.
  Download it with:

  ```bash
  huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218
  ```

  The code resolves the snapshot through `HF_HUB_CACHE` (or `HF_HOME`). `HF_TOKEN` is optional.
- `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY` are needed only for:
  - judge calls on labeller disagreements (exp8 suite and exp11 bench judges; almost all of them hit the copied caches
    `data/judge_cache*.jsonl`);
  - the novelty audit (`src/novelty_e.py`, artifact cap 0.50 USD).
- Hardware used: NVIDIA L4 (sm_89, 23 GB VRAM), 6 CPUs, 57 GB RAM container limit.
  `predictions/device_rule.json` records the device rule; the memory probe picked B = 20.

## 4. Commands, in the order they were run

```bash
export PYTHONPATH=src
uv run src/stage_a.py                 # inputs + sha256 -> predictions/e_inputs.json (commit 'stageA_inputs'),
                                      # results/iter4_reference.json, results/prompt_diff.json, predictions/landing_ref.json
uv run src/label_e.py --recheck       # copied labeller re-labels 450 exp19 + 1,700 exp22 rows: agreement 1.00 / 1.00
uv run src/run_e.py --stage tests     # device rule + memory probe (B = 20) + GPU tests U1-U8 -> results/tests_gpu.json (~3 min)
uv run src/run_e.py --stage smoke     # every arm type end to end -> data/smoke_*.jsonl (~2 min)
uv run src/label_e.py --raw data/smoke_raw.jsonl --out data/smoke_labels.jsonl
uv run src/tests_cpu.py               # CPU tests 1-8 (incl. the synthetic-analysis test) -> results/tests_cpu.json
uv run src/commit0.py                 # commit #0 (2026-10-21T20:32:48Z): predictions, rules, analysis/engine sha256
./run_gpu_pipeline.sh                 # generation queue (src/run_e.py --stage gen), then the mechanism readouts
uv run src/label_e.py --follow-until results/gen_done.flag   # concurrent CPU labelling of every generated row
uv run src/commit1.py                 # commit #1: gate outcomes + timing
uv run src/dep_usage_e.py             # dependency usage + known solutions for the novelty audit
uv run src/analysis_e.py              # Stage G -> results/*.json
uv run src/novelty_e.py               # novelty audit (OpenRouter)
./run_posthoc.sh                      # POST-HOC (not pre-registered): iteration-5 replication cells IT5_a1/IT5_a2
                                      # (exp27's PN5 seeds + per-template ban-free unit) under W16A16 and W8A8, then labels
uv run src/analysis_e.py              # re-run so the post-hoc rows enter factorial.json
uv run src/posthoc_e.py               # results/posthoc.json (replication vs exp27, unit decomposition, unit profiles)
uv run src/rederive_e.py              # independent re-derivation + placebos + commit-chain audit
uv run src/figures_e.py               # figures/F1-F9 (PDF + PNG)
uv run src/report_e.py                # results/summary.md (numbers rendered from JSON)
uv run src/outputs_e.py               # method_out.json (exp_gen_sol_out)
# aii-json skill: aii_json_format_mini_preview.py --input method_out.json -> full_/mini_/preview_method_out.json
uv run src/write_readme.py            # README.md (results section rendered from results/*.json)
uv run src/final_struct.py            # .terminal_claude_agent_struct_out.json (summary numbers read from JSON)
```

`uv run method.py --stage all` runs the same stages in this order. `uv run method.py --stage post` re-runs only the
CPU analysis stages on the rows already on disk.

Seeds and determinism:

- CRN uniforms: `u_stream(task, w, k) = PCG64(stable_seed(task, w, k)).random(1024)`.
- PN directions: `PCG64(stable_seed(task, arm, w, k)).standard_normal(4096)`, normalised.
- The 40 fixed directions are exp22's `rand_9101..9140.npy`.
- Dither noise: `torch.Generator('cuda')` seeded by `stable_seed(task, 'DITHER', variant, w, k, block, input, step)`.
- Bootstrap seed: 20261021 (2,000 replicates).
- The same batch run twice gives identical token ids (U2).

Generation was interrupted and resumed once (deviation D9): rows are keyed by `sample_id` and a batch is skipped only
when all of its rows exist. Generation took 370 batches of 20 rows (7,400 programs, including 400 post-hoc rows) in 1.98 GPU-hours of batch time (results/timing.json; median 18-20 s per batch for the EMU and native cells, 13 s for REAL), plus about 6 minutes of mechanism readouts and about 1 minute per model load. There were zero cap hits. CPU labelling ran concurrently (6 CPUs). OpenRouter spend: about 0.01 USD for the novelty audit plus a few judge calls on labeller disagreements (most hit the copied caches).

## 5. What you should get

- `results/verdict.json`: the frozen verdict and the consequence text.
- `results/primary_E.json`: paired McNemar for W8A8 vs W16A16 on PN alpha 2, T10 and T2; the REAL repeat.
- `results/attribution.json`: AME / WME / INT, slot bootstrap, GEE.
- `results/population40.json`, `unit_cross.json`, `t03_control.json`, `dither.json`, `mechanism.json`,
  `landing.json`, `engine_check.json`.
- `results/rederive.json`: 0 mismatches is the target; both placebos fail to reject.
- `results/summary.md`: every headline table, rendered from the JSON files. The README's Results section reproduces it.
- `method_out.json`, `full_method_out.json`, `mini_method_out.json` and `preview_method_out.json`: per-program
  predictions per precision plus all analyses in their metadata.
- `figures/F1_factorial` (the paper's factorial figure), `F2_flip_matrices`, `F3_divergence_travel`,
  `F4_population40`, `F5_attribution`, `F6_dither`, `F7_landing` and `F8_scale_rerounding`.

Headline numbers (re-derived independently in results/rederive.json, 0 mismatches):

- Frozen verdict: NO PRECISION EFFECT. PN alpha 2, W8A8 vs W16A16:
  - T10: 0.58 vs 0.50 (exact McNemar p 0.22);
  - T2: 0.20 vs 0.18 (p 1).
- Unit cross under W16A16, ban unit vs ban-free unit:
  - T10: 0.50 vs 0.10 (p 1.1e-05);
  - T2: 0.18 vs 0.02 (p 0.021).
- POST-HOC replication of iteration 5 under W16A16, T10: 0.02
  (exp27 0.02; per-slot label agreement 1.00).
- Figures for a paper: F1 (factorial) and F9 (unit decomposition) carry the result; F4 (40 directions) and
  F3/F8 (mechanism readouts) support it.

Bitwise reproduction is expected only on the same card type (L4, sm_89) with the same driver/cuBLAS. On other
cards, kernel choice changes rows near decision boundaries. Compare label shares within their Wilson intervals, not
token ids.
