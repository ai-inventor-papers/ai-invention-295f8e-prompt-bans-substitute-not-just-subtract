# Reproducing TP-G2 (iteration 10, `gen_plan_experiment_5_idx5`)

This file records what was actually run, in the order it was run.

All paths here are relative to this artifact's folder. The folder needs no other repository folder except in the two
optional cases in §3.2. Every expensive or non-deterministic intermediate ships with it:

- the generated programs;
- the instrument and sandbox caches;
- the hand reads;
- the model states.

## 1. Get the artifact

The workspace is published as one folder of a public GitHub repository:

```bash
git clone <the run's repository URL>
cd <repository>/<this artifact's folder>        # the folder that contains this file, method.py and src/
```

Prior artifacts are published as **sibling folders named by artifact id**. Code reads each one through one constant in
`src/tpg2.py`, overridable by an environment variable:

| artifact | id | environment variable (default) |
|---|---|---|
| iteration-9 TP-G | `art_VVA3P0ocZNA2` | `TPG2_E46` (`../art_VVA3P0ocZNA2`) |
| iteration-9 TP-B | `art_8nXdw3_lDAll` | `TPG2_E45` (`../art_8nXdw3_lDAll`) |
| iteration-8 screen | `art_R-HSmXq2t97f` | `TPG2_E44` (`../art_R-HSmXq2t97f`) |
| declared dataset | `art_j3Rm_lr2nzR6` | `TPG2_DS` (`../art_j3Rm_lr2nzR6`) |

`TPG2_DEPS_DIR` moves all four at once. No user-uploaded file was used.

## 2. System, Python and libraries

What the run used:

- **Hardware:** NVIDIA GeForce RTX 4090, 24 GB VRAM. Driver 595.91.07, CUDA 13.2 driver; the torch wheels are cu128.
- **Container:** Debian GNU/Linux 12 (bookworm), Linux 6.8. CPU quota of 7 cores (AMD Ryzen 9 7950X); RAM limit 42 GB.
  Ubuntu 22.04 or 24.04 with a recent NVIDIA driver works the same.
- **Python:** 3.12.14 via `uv`.
- **Sandbox interpreter:** the test harness and tracer run candidate programs with a stdlib-only CPython 3.12, always
  with `-I -S`.
  - The harness (`vendor/exp9/tasks/harness.py`) takes `$SANDBOX_PYTHON`, else the system `python3.12` (the run used
    `/usr/local/bin/python3.12`), else the current interpreter.
  - The tracer (`src/orderclass.py`, `src/instrument.py`) takes the system `python3.12`, else the current
    interpreter.
  - No other system packages are needed.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh          # if uv is missing
bash restore.sh                                          # = uv venv .venv --python=3.12 && uv pip install -r requirements.lock.txt
```

The `.venv` was created this way. `pyproject.toml` pins all 70 packages to exactly the versions in `.venv`, from
`uv pip freeze --python .venv/bin/python`; uv venvs ship no `pip`. `requirements.lock.txt` holds the identical list.
The pins are the same as iteration 9's, and the reproduction gate depends on them: `torch==2.8.0` (cu128),
`transformers==4.57.6`, `bitsandbytes==0.50.2`, `numpy==2.2.6`, `scipy==1.18.1`, `scikit-learn==1.9.1`,
`accelerate==1.15.0` and `huggingface-hub==0.36.2`.

## 3. Downloads, environment variables and keys (names only)

### 3.1 Models

The models download automatically on first use, or up front with `bash restore.sh --models`:

- `Qwen/Qwen3-8B`, revision `b968826d9c46dd6066d109eabc6255188de91218`: bf16, truncated to 20 blocks, about 9 GB VRAM.
- `unsloth/Qwen3-32B-bnb-4bit`, revision `7f721e74a6a8cc9ee352f7e49303a2c1705f9083`: NF4, truncated to 36 blocks,
  about 10 GB VRAM.

`HF_HOME` is optional and sets where the weights are cached.

### 3.2 API keys and sibling artifacts

- **`OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY`:** needed only to regenerate programs (`src/gen_or.py`) or to rerun the
  judge gate (`src/judges.py`). The analysis does not need them.
- **Sibling artifacts:** needed only for two things:
  - re-copying `inputs/` from the original artifacts; `inputs/` already holds verified copies, see
    `inputs/SHA256SUMS`;
  - the novelty-audit known-solution pool, which reads `art_j3Rm_lr2nzR6/full_data_out.json` through `TPG2_DS`.

### 3.3 Iteration 9's cached states

The original files are `art_VVA3P0ocZNA2/cache/states/mcode_{8b,32b}.npz` (200 MB and 369 MB). They are over the
100 MB publish limit.

`cache/e46_states/` ships **bit-identical reduced copies** instead:

- the PRIMARY and SURV rows only;
- blocks L-2 .. L+2;
- all four readouts;
- the frozen `geo_*_mcode_PRIMARY_R1_k{10,15}.npz` files.

Provenance and sha256 are in `cache/e46_states/README.json`. `src/tpg2.py` uses these copies when they are present.
`audit/rederive.py` gives the same output from them as from the originals (0 mismatches, identical JSON).

## 4. Commands, in the order they were run

The entry point `python method.py <stage>` runs the same commands in the same order (`python method.py all`). Times are
for the hardware in §2.

| # | command | what it does | runtime |
|---|---|---|---|
| 1 | `python src/gen_or.py cells` | cell table, prompts, forbidden-word audit, **COMMIT0a** (`commitments.log`, genesis sha256('iter10_tpg2')) | seconds |
| 2 | `python src/gen_or.py gen 0 LEV_DEQ --limit 5`; `python src/gen_or.py gen 0 RLX_ARR --limit 5` | 10-call smoke test | 20 s |
| 3 | `python src/gen_or.py gen 0` | round 0, all 18 cells x 20 | 7.5 min |
| 4 | `python src/gate_instrument.py` (4 runs; the instrument was revised 3 times, deviation D2) → `predictions/commit0b_instrument_gate.json`, **COMMIT0b** | instrument gate | 1.5 min / run |
| 5 | `python src/states10.py gate 8b`; `python src/states10.py gate 32b` | reproduction gate (GPU) | 0.5 min / 1.5 min |
| 6 | `python src/accept.py factorial` | acceptance; rerun after every round, cached by sha256 | 3 min / round |
| 7 | **COMMIT0c**, then `python src/gen_or.py gen 1` | edge-case amendment, then round 1 for all cells | 12 min |
| 8 | `python src/stage_sets.py topups`, `... survivors`, `... covert` | top-up re-adjudication, survivors, covert set | 5 min |
| 9 | `python src/gen_or.py topup jps 0 30`, `... iddfs 0 30`, `... biastar 0 30`, then `... jps 1 30`, `... biastar 1 30` | named top-ups | 3 min |
| 10 | **COMMIT0d**, then `python src/gen_or.py gen 2 LEV_DEQ,LEV_HEAP,LEV_SET,LEV_ARR,DFS_DEQ,DFS_HEAP,HEU_HEAP,HEU_SLIST,HEU_ARR,RLX_ARR,RLX_STK,RLX_HEAP,RND_HEAP,RND_SET,CRD_SLIST` | round 2 (reworded, in-paragraph edge-case order) | 9 min |
| 11 | hand reads with `python src/handread.py show ...` and `python src/handread.py record <reads.json>` | written to `data/hand_reads.jsonl` | about 40 min |
| 12 | `python src/stage_sets.py primary`; `python src/measure_primary.py` | measure the iteration-9 PRIMARY programs | 2 min |
| 13 | `python src/build_frames.py`; `python src/synth_t4.py` | frames and design check; T4 | 0.5 min; 4 min |
| 14 | **COMMIT1** (payload `predictions/commit1.json`) | frames, code hashes, predictions, T4 | seconds |
| 15 | `python src/states10.py extract 8b`; `python src/states10.py extract 32b` | 412 programs per model (GPU) | 70 s + 16 s load; 155 s + 84 s load |
| 16 | `python src/run_analysis.py 8b --boot 1000`; `python src/run_analysis.py 32b --boot 1000` | G1 and G2 | about 7 min / model |
| 17 | `python src/judges.py` | judge gate; no judge passed | 1 min |
| 18 | `python -I audit/rederive.py 8b 32b` | independent re-derivation 1 | 2 min |
| 19 | `python src/figures.py both` | figures | 4 min |
| 20 | `python src/t3_t9_checks.py`; `python src/make_outputs.py`; `python src/add_topup_preds.py` | checks and outputs | 1 min; 10 min; 4 min |
| 21 | `python src/explore_confusion.py`; `python src/explore_dbeh.py`; `python src/synth_t4b.py` | exploratory, after COMMIT1 | 1 min; 6 min; 2 min |
| 22 | `python -I audit/rederive2.py 8b 32b` | independent re-derivation 2, with placebos | about 6 min |
| 23 | aii-json `aii_json_validate_schema.py --format exp_gen_sol_out --file method_out.json` and `aii_json_format_mini_preview.py --input method_out.json` | validation and full / mini / preview variants | seconds |

Notes on the commit steps and the hand reads:

- Commits COMMIT0a-0d and COMMIT1 are written by `tpg2.commit(payload, label, note)`. The steps marked in bold were
  run as short inline Python calls of that function. `results/t9_commitments.json` verifies the chain and the
  timestamps.
- Hand reads are the executor's reads of the scrubbed code, stored with a rationale per program. They cannot be
  regenerated mechanically; `data/hand_reads.jsonl` is the record.

**Seeds and determinism**

- **Generation:** OpenRouter seed = slot + 1, but provider sampling is not bit-reproducible. Re-generating gives
  different programs; reproduce from the shipped `data/raw_factorial.jsonl` and `data/raw_topups_v10.jsonl`.
- **Fixed seeds:** bootstrap resample s uses seed s (0-999); noise-ceiling splits seed 0; T4 datasets seeds 1000+;
  covert stratification seed 0; context variants are seeded round-robin by cell / class / family name.
- **Exact enumeration:** permutation nulls are exact (5,760 within-container discipline permutations; 1,728
  within-discipline container permutations).
- **Re-running from the shipped states:** with `cache/states/tpg2_*.npz` (kept, about 120 MB), steps 16-22 reproduce
  every number exactly.
- **Re-extracting states:** step 15 gives cosine >= 0.99999 against the shipped arrays. That is the reproduction-gate
  tolerance, and NF4 / bf16 kernels can differ by GPU.

## 5. What you should get

| number | value (8B / 32B) | file |
|---|---|---|
| reproduction gate: min cosine, g(UD) | 0.999992 / 0.999999; 7.6744 / 16.6484 (exact) | `results/repro_gate.json` |
| instrument gate | 18/18 planted, 13/15 catalogue, 2/2 mutations | `results/instrument_gate.json` |
| G1 cells / programs | 15 cells, 221 programs (+16 PROBE) | `data/frames.json`, `results/design.json` |
| rho_d (discipline given container), exact within-container p | 0.104, p = 0.053 / 0.090, p = 0.024 | `results/g1_*.json` (`point_model`, `perm`) |
| rho_c (container given discipline) | 0.462 / 0.592 | `results/g1_*.json` |
| rho_d with surface / length / dispersion controls | 0.028 / 0.044 | `results/g1_*.json` |
| noise ceiling (Spearman-Brown) | 0.94 / 0.97 | `results/g1_*.json` |
| baseline rho_d (block 0 / TF-IDF / AST) | 0.146, 0.188, 0.195 / 0.111, 0.188, 0.195 | `results/g1_*.json` |
| G1 verdict | NOT SUPPORTED (8B INTERMEDIATE and FRAGILE, 32B LOW) | `results/verdicts.json` |
| LOO nearest-cell accuracy: model / TF-IDF / AST | 0.70 / 0.66 / 0.43 (8B); 0.79 (32B) | `results/t5_placement.json` |
| Delta(UD-LEV), Delta(BF-RLX) at k = 15 (descriptive: within-container permutation p = 0.33-0.57; norm-matched Gaussian placebo gives similar magnitudes) | -6.49, -8.88 / -20.74, -34.88 | `results/g2_*.json`, `audit/rederive2.json` |
| PROBE nearest cell | RLX_STK 15/16 (both models) | `results/g2_*.json` (`probe`) |
| covert share, nearest banned: F0 / F1 (the F1 share is not diagnostic on 32B: the Gaussian placebo gives 1.0) | 0.87, 0.77 / 0.97, 0.90 | `results/g2_*.json` (`covert`) |
| G2 verdict | NOT SUPPORTED as preregistered (both models, k = 15 and 10) | `results/verdicts.json` |
| independent re-derivations | 0 mismatches | `audit/rederive.json`, `audit/rederive2.json` |
| OpenRouter spend | USD 0.170, 1,230 calls | `results/costs.json` |

The paper's G1 / G2 results paragraphs and its geometry figures use these numbers and the files in `figures/`:

- `g1_forest`;
- `rdm_heatmaps_*`;
- `pca_F1_*`, `isomap_F1_*` and `mds_F1_*`;
- `F0_counts_placed_*`;
- `subframes_UD_BF_*`.

The run left the paper's section numbers to the paper step.
