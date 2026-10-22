# Reproducing claim S (Gemma Scope 2 readout and steering of gemma-3-4b-it's BFS/DFS fork)

This file describes what was **actually run**, in order, on 2026-10-22 (UTC), including the interruptions and the
re-runs. Every path below is relative to this folder.

## 1. Get the artifact

The workspace is published as one folder of a public GitHub repository.

```bash
git clone <URL of the run's repository>
cd <repository>/<this artifact's folder>        # the folder that holds this file
```

- **Upstream inputs are already copied into `inputs/`** (exp28 engine and data, exp23 units and ratios, exp8 T1
  suite and labeller, exp11 bench for T04/R6, exp7 nouns, exp9 TOP5 text and forced templates, exp18 index, and the
  files extracted from the declared dependency). `inputs/MANIFEST.sha256` hashes every copy, and
  `inputs/exp28_staged_SHA256SUMS` is the verified list from iteration 5 that the copies were checked against
  (`results/s0_inputs.json`: 384/384 match, bench 25/25 match its `commitment.json`).
- **Declared dependency** `art_j3Rm_lr2nzR6` (dataset, published as a sibling folder of this one). Only
  `src/extract_dep.py` reads it, through its single command-line argument (the path to that folder's
  `full_data_out.json`). Its outputs are already in `inputs/dep_extract/`, so re-running it is optional.
- **Upstream artifacts read at staging time** (iteration 2-5 experiments exp7, exp8, exp9, exp11, exp18, exp23, exp28)
  are not needed to re-run anything; their copies are in `inputs/`.
- **No user-uploaded input was used.** The run's user-uploads folder was empty.

## 2. System, Python and libraries

- **OS:** Debian GNU/Linux 12 (bookworm) in a container; any recent Ubuntu works.
- **GPU:** one NVIDIA RTX 2000 Ada Generation, 16 GB VRAM (70 W), driver 595.91.07; CUDA 12.8 runtime from the torch
  wheel. bf16 supported. (The plan expected an RTX A4500; see deviation D1 in `results/deviations.json`.)
- **CPU and RAM:** 6 vCPU (cgroup quota 5.1 cores), 28 GB RAM (cgroup limit).
- **Python 3.12** and **uv** (no pip inside the venv). The frozen labellers run candidate programs in fresh
  `python3.12 -I -S` subprocesses (system CPython 3.12 on `PATH`).

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
```

`pyproject.toml` pins all 95 installed packages with `==` (identical to `uv pip freeze --python .venv/bin/python`,
also saved in `logs/pip_freeze.txt`). Main versions: torch 2.8.0 (cu128), transformers 4.57.6, tokenizers 0.22.2,
huggingface-hub 0.36.2, safetensors 0.8.0, numpy 2.2.6, scipy 1.18.1, scikit-learn 1.9.1, sentence-transformers 5.1.2,
pyarrow 21.0.0, matplotlib 3.11.2, openai 3.35.1, loguru 0.7.3. Note: installing `sentence-transformers` without a pin
upgrades transformers to 5.x, which breaks the engine; the pinned file avoids that.

## 3. Models, data downloads, environment variables (names only)

| Name | Needed for |
|---|---|
| `HF_TOKEN` | the gated `google/gemma-3-4b-it` weights (accept the Gemma licence first) |
| `HF_HOME`, `HF_HUB_CACHE` | where weights go (the run used a shared cache outside this folder) |
| `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL` | LLM judges: T1 labeller disagreements (gpt-4.1-mini), bench judge (gemini-2.5-flash-lite), S13 novelty audit and style re-gate (gemini-2.5-flash, deepseek-chat, gpt-4.1-mini) |

Pinned downloads (all fetched by the code on first use through `huggingface_hub`):
- `google/gemma-3-4b-it` @ `093f9f388b31de276ce2de164bdc2081324b9767` (text decoder loaded from the multimodal checkpoint)
- `google/gemma-scope-2-4b-it` @ `3e94b68be95290aada5b7525cf431d3040f81bb1`, files
  `resid_post/layer_{9,17,22,29}_width_16k_l0_medium/{config.json,params.safetensors}` (JumpReLU, loaded directly by
  `src/sae.py`; sae-lens and circuit-tracer were not installed)
- `Salesforce/wikitext` dataset file `wikitext-103-raw-v1/test-00000-of-00001.parquet` (gate reference corpus)
- `sentence-transformers/all-MiniLM-L6-v2` (CPU; the text-only control of the cross-prompt readout)

## 4. Commands actually run, in order

All commands from this folder. Times are wall-clock on the GPU above.

| # | Command | What it does | Wall time |
|---|---|---|---|
| 1 | `.venv/bin/python method.py --stage s0` | verify staged inputs and bench hashes, record hardware and instrument ids, write **commit #0** (`predictions/commit0.json`, `commitments.log`) | 45 s |
| 2 | `.venv/bin/python method.py --stage gen1` | U1/U2 GPU unit tests; S3 natural splits T1, T04, R6 (5 templates x 40 slots each; slots 0-9 = exp28 CRN keys = engine check); contrast arms (forced BFS/DFS F1-F5, ban BFS/DFS W1-W5, TOP5 and its twin; 10 slots each) | 14 min |
| 3 | `.venv/bin/python method.py --stage label --follow` (background, CPU, ran until the end) | labels every `data/raw_*.jsonl` row with the frozen labellers into `data/labels.jsonl` | continuous |
| 4 | `.venv/bin/python src/extract_dep.py <dependency folder>/full_data_out.json` | writes `inputs/dep_extract/*` from the declared dependency (all 10 datasets used; see `dataset_usage.json`) | 1 min |
| 5 | `.venv/bin/python method.py --stage fork` | S4: U8 partial-labeller validation, 24 base paths x 16 prefix lengths x 8 continuations (3,072) + single-token refinement (8 paths x 5 tokens x 16), change points | 45 min |
| 6 | fork re-finalisation on CPU (same `stage_fork` code with the generation step stubbed, all continuations cached in `data/fork_cont.jsonl`) | applied the corrected global fork-index rule (deviation D2) before any variant state or commit #1; re-running step 5 with the current code reproduces `results/fork.json` without new generation | 1 min |
| 7 | `src/chain_gpu.sh <fork pid>` = `method.py --stage tfgate`, `variants`, `select`, `clamps` | S3 teacher-forced states + S2 gate (19 min); S5 variants, contrast states, sampling validation (7 min); S7 selection + **commit #1** (3 min); S8 logit sweep (11,280 forward rows) + 15 generation cells + canonical twin (94 min, of which ~55 min were a 10x host slowdown) | 2 h 2 min |
| 8 | `.venv/bin/python method.py --stage analysis --parts s6a` / `s6b,s6c` / `geo` / `s3,s8` (CPU, partly in parallel with 7) | S6 decodability and readout, S6c, S11 geometry figures, S3 compositions, engine check, TOP5, S8 tests and figures | 6 + 3 + 21 + 1 min |
| 9 | `src/chain_gpu2.sh` = `method.py --stage das` then `--stage attrib` | `das` FAILED (an autograd error from reused KV buffers; the buffers are now detached at every step); `attrib` = S10 first-order fallback: top-5 nodes validated by real-model ablation/steering + joint ablation/steering cells (N = 30 each) | 2 + 5 min |
| 10 | `src/chain_gpu3.sh` = `method.py --stage clamps` (picks up `results/extra_cells.json`, written from `results/matched_pass_dose.json`: the two matched-dy DiM cells of the matched-pass rule) then `--stage das` (fixed code; this is the run that produced `results/das.json`) | extra S8 cells (4 min); S9 DAS k = 1, 2, 4 + generation N = 50 for the best k (15 min). A duplicate DAS launched by hand at the same time was killed after 45 s and wrote nothing. | 19 min |
| 11 | `.venv/bin/python method.py --stage analysis --parts s3,s6c,s8,s13` (a first attempt was killed by a 15-min timeout inside S6c; S6c was switched to leave-one-out nearest-class-mean and re-run), then `--parts s8` again after a figure fix | final S8 tests incl. extra/DAS/node cells and secondary attempted-class tests; S6c; S13 novelty audit + style re-gate (OpenRouter, USD 0.034 in total) | 2 min |
| 12 | `.venv/bin/python method.py --stage outputs` | `method_out.json` (+ `full_`/`mini_`/`preview_` variants via the aii-json format script, schema `exp_gen_sol_out` validated), `results/costs.json`, `results/timing.json` | 1 min |
| 13 | `python3 audit/verify_chain.py`; `python3 audit/rederive.py`; `.venv/bin/python audit/rederive_headlines.py` | hash chain + ordering (all ok); stdlib re-derivation (32 checks, 0 mismatches; placebos); independent re-derivation of the readout, sampling validation, dose-response and TOP5 numbers with placebos | 4 min |

Total GPU wall time about 4 h 10 min (of which about 55 min was a 10x host slowdown during the clamp cells).

Seeds and keys: every sample's uniforms are `PCG64(stable_seed(prefix, task, template, slot))` (`src/cfg.py`,
`src/engine.py`), prefix `iter5E` for slots 0-9 and `iter6S` otherwise; fork continuations use
`('iter6S-fork', tag, base row, t, j)`; RANDF/ISO directions use `stable_seed('randf'|'iso', site, layer, k)`; CV and
permutation seeds are fixed in `src/analysis_S.py`. Decoding: temperature 1.0, top-p 1.0, no top-k, fence stop,
max_new 1,536 (T1) or 1,024 (T04, R6); coupled single-prompt batches have the fixed shape B_CRN = 20.

## 5. What a reader should get

- `results/natural_split.json`: T1 DFS 139 / BFS 61 of 200 (pass 0.86, default DFS); T04 naive 173 / builtin 27;
  R6 linear 170 / binary 29 / other 1.
- `results/engine_check.json`: label agreement with exp28 T1 0.94 (47/50), T04 1.00.
- `results/gate.json`: layers 22 and 29 pass, 9 and 17 fail (descriptive only).
- `results/fork.json`: fork at response token index 32 after the shared 32-token opening; next token `visited`
  -> DFS (P(BFS) 0.011), `\n`/`if`/`queue`/`q` -> BFS (0.95-1.0).
- `results/readout.json`, `results/sampling_validation.json`, `results/decodability_within.json`,
  `results/clamps.json`, `results/logit_sweep_summary.json`, `results/top5.json`, `results/geometry.json`,
  `results/attribution.json`, `results/das.json`, `results/novelty_audit.json`: the remaining headline numbers, all
  summarised in `README.md` and in `method_out.json` metadata.
- Figures in `figures/` (PNG + PDF): `fork_trajectories`, `geometry_{raw,sae}_L{17,22}`, `generated_panel_L22`,
  `clamp_cells`, `dose_response`.

Small numeric differences are expected on another GPU or batch shape (bf16 kernels; see the engine check), but every
contrast in this artifact is computed within one engine, so the paired comparisons are internally consistent.
