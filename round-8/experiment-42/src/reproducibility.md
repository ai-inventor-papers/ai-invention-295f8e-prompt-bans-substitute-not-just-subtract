# Reproducing "Fair test of Gemma's BFS dial" (iteration 8, claim G)

This file describes what was actually run on 2026-10-23 (UTC) and how to repeat it. Every path is relative to this
folder.

## 1. Get the artifact

This folder is published as one folder of a public GitHub repository. Clone the repository and change into this
artifact's folder:

```bash
git clone <repository URL>
cd <repository>/<this artifact's folder>      # the folder that holds method.py and this file
```

The input artifacts are sibling folders of the same repository, each named by its artifact id. Only the files listed
in `inputs/input_hashes.json` are used, and they are already copied into this folder (sha256-verified), so the
siblings are needed only to re-verify the copies (stage `s0`) or to restore `cache/states/`. The inputs are:

- `art_HY7uYZz-OjRW` (iteration 7's Gemma fork artifact);
- `art_veI9l_Rb9wDY` (iteration 7's Qwen3-8B dormancy artifact);
- `art_j3Rm_lr2nzR6` (the declared dataset dependency).

No user-uploaded file was used: the run's upload folder was empty, so nothing private is needed.

## 2. System, Python and libraries

What was used:

- **OS:** Debian 12 (bookworm) container on Linux 6.8. The same steps work on Ubuntu 22.04 and 24.04.
- **System packages:**
  - `git` and `curl`;
  - a stdlib-only **CPython 3.12** for the hidden-test sandbox. The labeller runs candidate programs with
    `$SANDBOX_PYTHON`, else `/usr/local/bin/python3.12`, else `/usr/bin/python3.12`, else `python3.12` on PATH.
    Ubuntu 24.04 ships it; on 22.04 run `sudo apt install python3.12` from the deadsnakes PPA.
- **uv 0.6.14:** `curl -LsSf https://astral.sh/uv/install.sh | sh`.
- **Python 3.12.14** for the project environment.
- **NVIDIA driver** able to run the CUDA 12.8 wheels of torch 2.8.0 (driver 595.91.07 was used; >= 570 is enough).

Create the environment exactly as it was created:

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
```

`pyproject.toml` pins all 95 installed packages with `==`, identical to `uv pip freeze --python .venv/bin/python`
(the freeze is saved in `logs/pip_freeze.txt`). The packages that matter are:

- torch==2.8.0 (CUDA 12.8 wheels; triton==3.4.0);
- transformers==4.57.6, tokenizers==0.22.2, safetensors==0.8.0, huggingface-hub==0.36.2, accelerate==1.15.0;
- numpy==2.2.6, scipy==1.18.1, pandas==3.0.6, matplotlib==3.11.2;
- openai==3.35.1, loguru==0.7.3, pyyaml==6.0.3.

## 3. Model, data and environment variables (names only)

- **Model:** `google/gemma-3-4b-it`, revision `093f9f388b31de276ce2de164bdc2081324b9767` (bf16, text-only weights of
  the multimodal checkpoint). It is gated on Hugging Face, so accept its licence and set `HF_TOKEN`. The code reads
  the snapshot from `HF_HUB_CACHE` if it is there, else downloads it with `huggingface_hub`. To pre-download:
  `huggingface-cli download google/gemma-3-4b-it --revision 093f9f388b31de276ce2de164bdc2081324b9767`.
- **Input artifact locations.** In code there is one constant per artifact, `method.py: artifact_dir()`. It is looked
  up, in order:
  1. the environment variable below;
  2. the sibling folder named by the artifact id;
  3. the run-volume layout.

  | Artifact | Variable | Used for |
  |---|---|---|
  | `art_HY7uYZz-OjRW` | `AII_ART_HY7UYZZ_OJRW` | source of the copied code, DAS maps, fork states and iteration-7 results |
  | `art_veI9l_Rb9wDY` | `AII_ART_VEI9L_RB9WDY` | source of the copied `dormant.json` |
  | `art_j3Rm_lr2nzR6` | `AII_ART_J3RM_LR2NZR6` | `full_data_out.json`; all 10 datasets are loaded in stages `s0` and `novelty` for the known-solution pool |

- **OpenRouter:** `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY`. They are used by the labeller's blind judge (only
  when runtime and AST disagree), the novelty audit and the style re-gate. This run spent USD 0.0042 in total. The
  judge answers for every program of this run are cached in `data/judge_cache_paths.jsonl`; without a key, a new
  disagreement is labelled `disputed`.
- **Optional:** `SANDBOX_PYTHON`, `HF_HOME` / `HF_HUB_CACHE`, `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` (set
  for every GPU stage in this run).
- **Restore the deleted bulk:** `bash restore.sh`. It rebuilds `.venv/` if missing and copies `cache/states/` (iteration
  7's fork states) from `art_HY7uYZz-OjRW`, then checks their sha256. If that artifact's published copy lacks its
  `cache/states/`, rebuild them there with its own `method.py --stage yv` (about 2 GPU-minutes; a rebuilt copy may
  differ in bf16 bits).

## 4. Commands, in order, as run

Commitments (`predictions/commit*.json`, `commitments.log`) are write-once. Choose one of two modes.

- **Mode A, re-check from the published raw data (CPU only, about 5 minutes).** Keep everything as cloned:
  `bash restore.sh`, then run the last block of commands below (`analysis` through `rederive_raw.py`).
- **Mode B, full regeneration (GPU).** Move `predictions/`, `commitments.log`, `results/`, `figures/`, `data/` (keep
  `data/judge_cache_paths.jsonl`), `cache/decision_states.pt` and `cache/known_pool.json` out of the way, then run
  everything.

```bash
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
.venv/bin/python method.py --stage s0          # 35 s. CPU checks (input sha256 44/44, labeller 12/12 references,
                                               # 5/5 mutants rejected, prompts, slot keys, U5, analysis8 on
                                               # iteration 7's rows: 11 / 42 / 35) and COMMIT #0
nohup .venv/bin/python method.py --stage label --follow > logs/label_worker.out 2>&1 &   # CPU label worker
.venv/bin/python method.py --stage gpu1        # 300 s. Unit tests U1-U4'; engine check; TF stage + dormancy;
                                               # COMMIT #1; G1a/G1b/G1c/P-DAS-dfs/G1d; free twin; REV-DAS/REV-FULL
.venv/bin/python method.py --stage commit2     # 58 s. Waits for labels; decision positions; COMMIT #2
.venv/bin/python method.py --stage fcells      # 192 s. 480 edited free-generation programs; prefix check
.venv/bin/python method.py --stage gpu_extra   # 151 s. COMMIT #3; free forced-BFS prompting, 7 more wordings
.venv/bin/python method.py --stage tf_extra    # 80 s. COMMIT #4; layer sweep of full-state swaps (teacher-forced)
touch data/STOP_LABELLER                       # the label worker exits once its backlog is empty
.venv/bin/python method.py --stage novelty     # 10 s. Known-solution pool rebuild, novelty audit, style re-gate
.venv/bin/python method.py --stage positioning # writes results/positioning.json (search results: logs/positioning/)
.venv/bin/python method.py --stage analysis    # about 50 s (re-runs the hidden tests on failing programs)
.venv/bin/python method.py --stage figures     # about 15 s
.venv/bin/python method.py --stage outputs     # about 30 s: data/samples.jsonl, method_out.json
python3 -I audit/verify_chain.py               # hash chain + commit-before-sample ordering
python3 -I audit/rederive.py                   # 139 re-derived quantities + placebos
.venv/bin/python audit/rederive_raw.py         # headline cells re-scored from raw text (independent runner)
```

Notes on the actual run:

- The positioning searches were run by hand with the aii-web-tools scripts (search, then fetching each arXiv abstract
  page). The raw outputs are in `logs/positioning/`, and the stage only writes the dated record.
- `analysis`, `figures` and `outputs` were re-run several times after figure-layout and reporting fixes. The data and
  the statistics did not change. The published files come from the last runs (02:13 UTC).
- The full/mini/preview variants and the schema checks used the aii-json skill scripts
  (`aii_json_format_mini_preview.py --input method_out.json`, then `aii_json_validate_schema.py --format
  exp_gen_sol_out`). All four files validate.

**Seeds and configuration (fixed in code, frozen in commit #0):**

- **Sampling:** each CRN slot has one uniform stream, PCG64 seeded by sha256 of `('iter7GG2', 'T1', w, k)`. Stream
  index = response index. Decoding is T 1.0, top-p 1, no top-k, max_new 1024, fence stop.
- **Numerics and batching:** one fixed batch shape of 25 rows, bf16 with sdpa attention, fp32 logits, float64 CDF.
- **DAS and baselines:**
  - DAS maps are iteration 7's (fitting seeds 0-2, seed 0 used for generation). Edit at block 17.
  - RAND rank-4 subspace: seed 31337.
  - DiM betas are bisected on this engine (BFS 1379.7, DFS -838.5).
- **Nulls and resampling:**
  - natural-variance null: 1,000 Haar draws per k with generator seed 9 + k;
  - reverse null: 50 Haar subspaces with seed 4243;
  - bootstraps: seed 0 (2,000 base-cluster resamples; 10,000 slot resamples);
  - placebos: seed 0.

**Hardware used:**

- one NVIDIA GeForce RTX 4090 (24 GB);
- AMD Ryzen 9 7950X, 14 CPUs allotted, 56 GB RAM (container).

GPU time is about 13 minutes in all, and the whole pipeline about 45 minutes of wall time. Labelling runs beside the
GPU stages.

**Determinism:**

- On the same GPU model with these versions, generation is token-for-token reproducible: fixed batch shapes and
  deterministic kernels; U1 checks CRN determinism.
- A different GPU changes bf16 numerics. Iteration 7's RTX 2000 Ada and this RTX 4090 agree on 0.94-1.00 of per-slot
  labels, with 54-78% byte-identical programs, so counts can move by a few programs.

## 5. What you should get

| Output | Numbers to find |
|---|---|
| `results/analysis.json` -> `cells` | correct BFS / 50: P-twin 10, G1a 0 (attempted 50, pass 0.00), P-DAS-bfs 39, F-twin 13, G1c 32, F-DAS-r4-bfs-1.0 38 (pass 0.78), F-DiM-bfs 0 (pass 0.00); correct DFS: P-DAS-dfs 50, G1b 50, F-DAS-r4-dfs-1.0 47 |
| `results/analysis.json` -> `tests` | P1b dial vs prompt (prefilled) 39 / 0 discordant, p = 3.6e-12; free dial vs free twin 26 / 1, p = 2.1e-7; free dial vs free prompt 11 / 5, p = 0.21; prefilled vs free dial 2 / 1, p = 1.0; interaction 0.66 (95% 0.50-0.82) |
| `results/analysis.json` -> `scorecard`, `verdicts` | P1 no, P1b no (DIAL BEATS MATCHED PROMPTING), P2 yes (free-generation knob), P3 yes (reach 0.94), P4 no (0.894 / 0.979), P5 account no / low variance yes, P6 yes, P7 yes |
| `results/analysis.json` -> `wording_extension` | free forced-BFS prompting over 8 wordings: 14-49 correct (mean 39.5); F3 49 vs dial 38, p = 0.0034 |
| `results/dormancy.json` -> `summary_by_k` | k = 1/2/4/8: forward recovery 2.04 / 2.36 / 2.54 / 2.79; reverse 1.53 / 1.74 / 2.13 / 2.39; retention 0.28 / 0.23 / 0.21 / 0.18 (twins + forced: 0.62 / 0.53 / 0.46 / 0.39); variance share 0.00088 / 0.0011 / 0.0018 / 0.0053 vs p95 0.00096 / 0.0018 / 0.0027 / 0.0048; verdict DORMANT/OFF-MANIFOLD HANDLE at every k |
| `results/tf_stage.json` | log P(c\* \| forced-BFS) -11.3 to -14.1 nats; p(` queue`) 0.96-0.998 under forced-BFS + c\* |
| `results/layer_sweep.json` | p(` queue`) after a block-17 full-state transplant 0.55; DAS 0.006-0.07; DiM 0.94-0.98 |
| `results/rederive.json`, `results/rederive_raw.json`, `results/verify_chain.json` | 139 checks with 0 mismatches; 8 headline cells re-scored from raw text, identical; chain and ordering all OK |
| `figures/` | F1 2x2, F2 free-dial decomposition, F3 dormancy, F4 geometry (block-17 activation coordinates), F5 seed cosines, F6 fork tokens, F7 layer sweep |
| `method_out.json` (+ `full_`, `mini_`, `preview_`) | exp_gen_sol_out: engine_check, g1_prefill_matched, g2_free_dial, g3_reverse_gen, g3_dormancy |

The paper is written by a later step. It takes these numbers from `README.md` (sections "Short answer" and
"Results"), `results/analysis.json` and `results/dormancy.json`, and uses the figures under the names F1-F7 above.
