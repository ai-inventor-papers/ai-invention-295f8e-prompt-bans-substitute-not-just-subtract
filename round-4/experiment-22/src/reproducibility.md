# Reproducing "Where the model's algorithm choice lives" (iteration 4, plan-subspace experiment)

This file describes what was actually run to produce the results in `README.md`, in the order it was run. Every path
is relative to this folder.

## 1. Get the artifact

This workspace is published as one folder of a public GitHub repository. Other artifacts of the same run are
sibling folders.

```bash
git clone <repository URL>
cd <repository>/<this artifact's folder>      # the folder that contains this file, README.md and method.py
```

## 2. System, Python and libraries

The run used the following environment:

- **OS:** Debian GNU/Linux 12 (bookworm), Linux 6.8, in a container. Any recent Ubuntu (22.04 or 24.04) with an
  NVIDIA driver supporting CUDA 12.8 works the same way.
- **Hardware:** 1 × NVIDIA RTX 2000 Ada Generation (16 GB VRAM, compute capability 8.9, driver 595.91.07),
  a 5-CPU cgroup quota (AMD EPYC 7443P), 28 GB RAM.
- **Python:** 3.12.14, managed with `uv`. The uv venv has no `pip` binary, so `uv pip freeze` replaces `pip freeze`.
- **System packages:** `git`, `curl` and a working NVIDIA driver. No compiler is needed: the FP8 kernels are
  `torch._scaled_mm`.
- **Libraries:** 82 packages, every one pinned in `pyproject.toml` to the version installed in `.venv`. The pins
  were checked against `uv pip freeze` (`logs/pip_freeze.txt`) with 0 differences. Key versions: torch 2.8.0
  (CUDA 12.8 wheels from PyPI), transformers 4.57.6, accelerate 1.15.0, numpy 2.2.6, scipy 1.18.1,
  scikit-learn 1.9.1, statsmodels 0.15.0, ripser 0.6.15, matplotlib 3.11.2, openai 3.35.1, loguru 0.7.3.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh          # if uv is missing
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4   # <= the CPU quota (see note below)
```

Note on BLAS threads: unbounded threads oversubscribe a container whose host has many cores, and the CPU analyses
then stall.

## 3. Data, model and environment variables

- **Model:** `Qwen/Qwen3-8B` at revision `b968826d9c46dd6066d109eabc6255188de91218`. The bf16 safetensors are
  about 16.4 GB. At load time the decoder linears are quantised to FP8 E4M3 W8A8 (per-output-channel weight scales,
  per-token activation scales); embeddings, norms and the LM head stay bf16. The weights are read from the Hugging
  Face cache named by `HF_HUB_CACHE`, or downloaded by id:

  ```bash
  huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218
  ```

- **Inputs from earlier artifacts:** these ship with this folder in `inputs/`, and their sha256 are in
  `results/input_hashes.json`. They are read-only copies of:
  - the iteration-2 bench (exp11; verified against its `bench/commitment.json`);
  - the exp8 path-task suite;
  - iteration-3 files from exp17 (`art_pVlCZ272hDV7`), exp13 (`art_1AYTO1Epb_7t`), exp16 (`art__5akZ9W9iZM4`) and
    exp18 (`art_ccAbfJVcv0LO`);
  - the iteration-2 exp7 prompts.

  Re-creating `inputs/` with `src/s0_setup.py` is optional. It needs those artifact folders laid out as
  `$AII_ITER_ROOT/iter_<k>/gen_art/<folder>`.
- **Declared dependency `art_j3Rm_lr2nzR6`** (published as a sibling folder). Only `src/extract_known.py` reads
  its `full_data_out.json`, through the single constant `DEP_ART_J3RM` in `src/cfg4.py`. That constant defaults to
  `../art_j3Rm_lr2nzR6`; set `AII_DEP_ART_J3RM` if the sibling folder has another name. The extracted subset
  (`inputs/dep_art_j3Rm/known_subset.jsonl`, 406 known solutions) ships with this folder.
- **User uploads:** none were used. The run's user-upload folder was empty, and nothing private is needed.
- **Environment variables, by name:**

  | Variable | Needed for |
  |---|---|
  | `OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY` | masked descriptions, the blind labelling judge, the novelty judges |
  | `HF_HUB_CACHE` | optional: the model cache |
  | `AII_ITER_ROOT` | optional: re-creating `inputs/` |
  | `AII_DEP_ART_J3RM` | optional: re-extracting the known-solution subset |
  | `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS` | recommended: bound the BLAS threads |
  | `AII_JSON_SKILL` | optional: lets `finalize.sh` validate `method_out.json` and write its full / mini / preview variants |

## 4. Commands, in the order they were run

Times are wall-clock on the hardware above. `method.py` wraps the same scripts by stage (`python method.py` lists
the stages); the exact invocations are given here.

```bash
PY=.venv/bin/python
# S0 (CPU): inputs + sha256 + bench verification (optional when inputs/ exists), the screen file, labeller re-check
$PY src/s0_setup.py                      # ~1 min; skips sources that are absent and verifies the shipped copies
$PY src/screen.py                        # seconds; results/screen.json (commitments.log entry #0)
$PY src/describe.py                      # 65 OpenRouter calls to openai/gpt-4.1-mini, USD 0.034, ~3 min
$PY src/prompts4.py                      # 4,144 prompts, ~5 min
$PY src/recheck4.py                      # ~2 min: bench references 100%, gates reproduced, exp8 suite 22/22
# S1/S2 (GPU, ~32 min): unit tests (18 s), engine check (3 min), states (18 min), units, realised prefills (12 min)
$PY src/gpu_phase1.py tests engine states units realised
# label worker: started here, ran concurrently until every row was labelled
nohup $PY src/label4.py > logs/label4.out 2>&1 &
# S3/S4 (CPU): tests of the analysis code, plan subspace + predictors, commit #1 (before any population sample)
$PY analysis/tests_cpu.py                # ~1 min, 9/9 pass
OMP_NUM_THREADS=5 $PY src/subspace.py    # ~1.3 min
$PY src/make_commit.py                   # predictions/c2_commit.json + commitments.log
# S5 (GPU): sampling stages; 150.7 min, 665 batches of 20 = 13,300 programs (+10 engine-check batches = 200 rows)
$PY src/gpu_phase2.py --deadline-min 165
# post-sampling GPU (~4 min): opening-ladder log-probs (C3b) + targeted-arm displacement vectors (geometry)
bash logs/post_gpu_chain.sh              # runs src/gpu_phase3.py
touch data/STOP_LABELLER                 # stops the label worker once it is idle (delete the file afterwards)
# S7/S8 (CPU, ~6 min): analyses, figures, costs, both audits, method_out.json + variants, schema checks
./finalize.sh
```

The analysis code itself was not run in this order. `analysis/decomp.py` and `analysis/c2c.py` were hash-committed
before their arms were sampled, and the remaining analysis files before they were first run (see
`commitments.log`). To reproduce from scratch, start from an empty `commitments.log`, `data/` and `states/`. Rerunning
in place appends new chain entries; sampled rows are resumable and skipped.

**Seeds and determinism.**

- Random push directions are `PCG64(seed).standard_normal(4096)`, normalised: seeds 9101–9140 for the population,
  9301–9306 for the C2c random controls, and 9001–9015 for the screen replication.
- The CRN uniforms are `u_stream(task, template, k)`, i.e. PCG64 seeded with sha256 of `task|template|k`. The same
  uniforms are shared by every arm.
- Permutation and bootstrap seeds are fixed in the code: Haar null 4242, permutation tests 0/1, bootstraps 0.
- Decoding is deterministic given the uniforms on this GPU, driver and torch build. Batch-1 prefills are
  bit-identical on repeat, and decode is row-position independent at B = 20. The engine check reproduced the
  iteration-3 screen rows of exp17 with identical program sha256 on 180/180 slots.
- A different GPU architecture can change FP8 GEMM rounding, and with it some sampled tokens. The statistics
  should agree within their intervals, not slot for slot.
- `prompts/descriptions.json` comes from an LLM and is not deterministic. `src/describe.py` reuses the shipped file
  when it exists; keep it to reproduce the prompt states exactly.
- The OpenRouter judges are called only on labeller disagreement and are cached in `data/judge_cache*.jsonl`; the
  novelty judges are cached in `data/novelty_cache.jsonl`. The shipped caches make reruns deterministic and free.

## 5. What you should get

| Output | Where | Value in this run |
|---|---|---|
| C2a primary (ρ of π with y, 6 tasks) | `results/c2a.json`, fig 1–2, README "C2a" | ρ = 0.14, 0.09, 0.08, −0.05, −0.01, −0.06; DISCONFIRM; pooled within-task ρ = 0.03 [−0.03, 0.09] |
| Reliability of y (template split-half ρ) | `results/explore.json` | 0.80 (T03), 0.81 (T2), 0.76 (T05), 0.90 (T10) |
| Confirmed escapes at α 1 / 2 (of 40) | `results/escape.json`, fig 7 | T03 12 / 25, T10 15 / 29, T2 7 / 8, T05 0 / 5, T1 2 / 5, T06 0 / 0; 9 other tasks 0 |
| Decomposition, pooled medians (20 directions) | `results/decomposition.json`, fig 3 | R(u_perp) = 1.00, R(u_P) = 0.32, R(CLAMP) = 1.00 → "P_t not needed" |
| C2c at the midpoint, targeted vs random | `results/c2c.json`, fig 4 | T10 0.48 vs 0.00 (24 / 0 CRN flips, McNemar p = 1.2e-7); 5 of 6 tasks CI ∋ 0 → DISCONFIRM |
| C2b pooled within-task ρ | `results/c2b.json`, fig 5 | 0.27 (π) vs 0.12 (norm) → fails |
| C3b mean log score (gated events) | `results/c3b.json`, fig 8 | PUSH −0.76, LADDER_OPEN −2.39, ASSOCIATE −3.46, PROXIMITY −3.21 |
| Novelty audit | `results/novelty.json` | 0 NOVEL among 10,651 correct push programs |
| Engine check | `results/engine_check.json` | 180/180 slots identical to the iteration-3 screen |
| Audits | `results/rederive.json`, `results/rederive_extra.json` | 0 mismatches; placebos fail |
| Method output | `method_out.json` (+ `full_`, `mini_`, `preview_`) | exp_gen_sol_out; 5 datasets; schema validation passes |
| Cost | `results/costs.json` | 2.51 GPU-hours of sampling; OpenRouter USD 0.20 |

These numbers are the ones the README's Results section reports and that the paper written from this artifact
cites. The paper's figures are `figures/fig1`–`fig9` (PDF and PNG). The fp16 activation tensors in `states/` (about
3 GB, stored as row-wise `<name>.partNNN.npz` parts of < 45 MiB each that `src/npz_parts.py` reassembles) are not in
the published repository. Running `src/gpu_phase1.py states units
realised` regenerates them in about 30 min on the GPU above.
