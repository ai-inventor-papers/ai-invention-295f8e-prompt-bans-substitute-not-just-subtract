# Reproducing "Temperature at one deciding token" (iteration 8, claims K1 and HR)

This file describes what was actually run, in order, on 2026-10-23, and how to rerun it on Ubuntu. Every path is
relative to this folder. All analysis numbers reproduce exactly from the shipped `data/*.jsonl` and `predictions/`.
Re-generating the programs on another GPU reproduces them up to batch-shape kernel sensitivity (see section 6).

## 1. Get the artifact

This folder is one folder of a public GitHub repository.

```bash
git clone <repository-url>
cd <repository>/<this-folder>          # the folder that contains method.py and this file
```

The declared dataset dependency **art_j3Rm_lr2nzR6** (`full_data_out.json`, used only by the novelty audit's
known-solution index) is published as a sibling folder `../art_j3Rm_lr2nzR6`. Elsewhere, point `ART_J3RM_DIR` at it.

Every other prior input (prompts, unit specs, hidden tests, frozen labellers, the iteration-6 engine, and iteration-7
rows and results) is already shipped in `inputs/`, with sha256 in `inputs/input_hashes.json` and `inputs/SHA256SUMS`.
`src/vendor_inputs.py` re-copied these from the iteration-6/7 workspaces of the original run; that step is not needed
from the repository.

No user-uploaded material was used (the run's upload folder was empty).

## 2. System, Python and packages

- OS used: Debian GNU/Linux 12 container (Ubuntu 22.04/24.04 works the same), NVIDIA driver with CUDA >= 12.8.
- System packages: `git`, `curl`, a C toolchain is not needed. Install `uv`:
  `curl -LsSf https://astral.sh/uv/install.sh | sh`.
- Python 3.12.14 (uv downloads it).
- Exact library versions: `pyproject.toml` pins all 93 installed packages, produced by
  `uv pip freeze --python .venv/bin/python`. Key pins: torch 2.8.0 (PyPI CUDA 12.8 wheel), transformers 4.57.6,
  numpy 2.2.6, scipy 1.18.1, matplotlib 3.11.2, zss 1.2.0, aiohttp 3.13.1, loguru 0.7.3.

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python -c "import torch, transformers; print(torch.__version__, transformers.__version__, torch.cuda.is_available())"
```

## 3. Models, downloads and environment variables (names only)

```bash
export HF_TOKEN=...            # Gemma-3 is gated on the Hugging Face Hub: accept its licence first
.venv/bin/python scripts/download_models.py           # Qwen/Qwen3-8B@b968826d9c46dd6066d109eabc6255188de91218
                                                      # google/gemma-3-4b-it@093f9f388b31de276ce2de164bdc2081324b9767
```

| variable | used by | needed when |
|---|---|---|
| `HF_TOKEN`, optionally `HF_HOME` / `HF_HUB_CACHE` | model download and loading | GPU stages |
| `OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY` | judge adjudication and novelty audit (`src/novelty8.py`) | stage 5 |
| `ART_J3RM_DIR` | novelty-audit retrieval index (`src/novelty8.py index`) | only if `../art_j3Rm_lr2nzR6` is not a sibling |
| `AII_RUN_LOOP` | `src/vendor_inputs.py` (re-copy inputs) | never, from the repository |
| `AII_JSON_SKILL_DIR` | optional schema validation in `src/finalize8.py` | optional |

The judges cost about USD 0.16 in total (`results/costs.json`).

## 4. What was run, in order

Hardware:

- GPU: one NVIDIA L4 (23 GB VRAM, power-capped at 72 W), at about 90-190 ms per decode step for batch 25-50.
- CPU and RAM: 5 CPUs (cgroup quota), 57 GB RAM.

All GPU work took 2.8 h of process wall-clock, including about 40 s per Qwen load and 16 s per Gemma load.
`method.py` chains the same steps (`.venv/bin/python method.py all`). These are the commands as they were run:

```bash
# background labeller (frozen labellers; follows data/samples.jsonl and data/continuations.jsonl)
.venv/bin/python src/label_daemon.py &

# Stage 0: twins + GPU unit tests (Qwen, then Gemma)                      ~4 min + ~2 min
.venv/bin/python src/gpu8.py qwen s0
# Stage 2: token maps (teacher-forced node logits + 10 continuations x ~24 tokens per node)   ~35 min
.venv/bin/python src/gpu8.py qwen s2 --units T10,B3,T1,A3,B6
# COMMIT #0 (written after the twins started; deviation D02)
.venv/bin/python src/protocol8.py
.venv/bin/python src/commit8.py commit COMMIT0_protocol predictions/protocol.json src/cfg8.py src/engine8.py \
    src/predict8.py src/units8.py src/gpu8.py src/stages8.py
.venv/bin/python src/tests8.py cpu          # C1-C6 -> results/tests_cpu.json
.venv/bin/python src/gpu8.py gemma s0,s2    # Gemma twin, U8 test, token map           ~6 min
.venv/bin/python src/tests8.py gpu          # U1-U8 -> results/tests_gpu.json, predictions/stage3_flags.json
.venv/bin/python src/stage0_report.py       # engine check -> results/stage0.json
.venv/bin/python src/novelty8.py adjudicate # judges resolve 'disputed'/unjudged labels (before COMMIT #1)
.venv/bin/python src/make_commits.py c1     # COMMIT #1: dose table and every per-arm prediction
.venv/bin/python src/make_commits.py c2     # COMMIT #2: HR predictions and audit protocol
# Stage 1: blind locator (T10, B3)                                         ~16 min
.venv/bin/python src/gpu8.py qwen s1 --units T10,B3
.venv/bin/python src/locator8.py
.venv/bin/python src/commit8.py commit COMMIT1b_locator results/locator.json src/locator8.py
# Stage 3 arms and Stage 4 HR
.venv/bin/python src/gpu8.py qwen s3,s4 --units T10,B3        # ~44 min
.venv/bin/python src/gpu8.py gemma s3,s4 --units G            # ~11 min
.venv/bin/python src/gpu8.py qwen s3 --units B6,T2,T03,T1     # ~9 min
.venv/bin/python src/gpu8.py qwen s4 --units B6,A3            # ~9 min
.venv/bin/python src/gpu8.py qwen s3 --units A3               # ~6 min
# Amendment (COMMIT #3) and its arms
.venv/bin/python src/novelty8.py adjudicate
.venv/bin/python src/amend8.py
.venv/bin/python src/gpu8.py qwen s3x --units T10             # ~2 min
.venv/bin/python src/gpu8.py gemma s3x --units G              # ~2 min
touch data/STOP_LABELLER                                      # the labeller exits when nothing is left
# Analysis, audit, figures, outputs (CPU, ~10 min)
.venv/bin/python src/novelty8.py adjudicate
.venv/bin/python src/stage0_report.py
.venv/bin/python src/analysis_k1.py            # results/k1_cells.json, results/k1_verdict.json
.venv/bin/python src/amend_analysis8.py        # results/amendment.json
.venv/bin/python src/hr8.py                    # results/hr.json
.venv/bin/python src/locator8.py               # results/locator.json
.venv/bin/python src/novelty8.py index         # cache/known_index.pkl (17,442 known solutions)
.venv/bin/python src/novelty8.py audit         # results/novelty_audit.json (manual reads: results/manual_reads.json)
.venv/bin/python src/figures8.py               # figures/F1-F8 (.pdf/.png), results/geometry_f8.json
.venv/bin/python src/report8.py                # results/summary.md
.venv/bin/python src/outputs8.py               # method_out.json
python3 -I audit/rederive.py                   # stdlib re-derivation + placebos + chain/timestamp checks
python3 -I audit/rederive_tests.py             # stdlib re-derivation of the tests, HR and novelty counts
```

Notes on what actually happened:

- The very first Stage 0 attempt hit an out-of-memory handler bug, which stalled the A3 twin at batch size 1. The bug
  was fixed and the run resumed from its rows; 16 A3 twin rows carry batch-1 numerics (deviation D03).
- The two programs the novelty audit read manually were classed in `results/manual_reads.json`. `src/novelty8.py`
  maps them to counting sort in `results/adjudicated_labels.json`.

**Seeds and stream keys.** Every program slot owns a PCG64 uniform stream keyed by `stable_seed(*ukey)` (sha256 of the
'|'-joined key):

- T10 / T1 / T2 / T03: `(unit, W, j)`;
- B3 / A3 / B6: `('iter7T', unit, W, 20 + j)`;
- G: `('iter7GG3', 'T1', W, j)`, for W in W1-W5 and j in 0-9.

Continuation and placebo seeds:

- token maps `('iter8map', unit, node, token, k)`;
- locator `('iter8loc', 7700000 + ...)`;
- HR `('iter8hr', 6600000 + ...)`;
- random window 8,800,000 + slot;
- class-uniform draws 9,900,000 + slot.

Statistics seeds: bootstrap 20261023 (2,000 replicates); noise ceiling 20261023 (10,000 draws).

## 5. What a reader should get

| output | headline number(s) |
|---|---|
| `results/k1_verdict.json` -> `K1a` | composed-prediction MAE: T10 0.017, B3 0.017, A3 0.039, B6 0.047, G 0.010 (replay 0.013 / 0.009 / 0.008 / 0.031 / 0.006) |
| `results/k1_cells.json` -> `T10` | DFS 0/50 at global T 1.3/1.6, 2/50 at T 2.0, 3/50 at fork d1 = 3.5, 9/50 at fork d2 = 7 (pass 0.86, correct Hill-1 1.60) |
| `results/k1_verdict.json` -> `K1b`, `primary_p_IUT`, `secondary_mcnemar_A10_vs_A3g` | T10 fails (no fork arm reaches Hill-1 1.8 within 5 points); IUT p = 0.30; McNemar 7:1, p = 0.035; B6 fork vs best comparator lower bound +0.19, p = 0.008 |
| `results/k1_cells.json` -> `B6` | correct Hill-1: twin 1.78, fork d1 2.27, fork d2 2.78, class-uniform 3.50 |
| `results/amendment.json` | T10 filtered dose: pass 0.98, Hill-1 1.54 (d1 = 5); G: pass 0.84, Hill-1 1.98 |
| `results/hr.json` | 3 units gain one known idea (T10 BFS, B3 prim_array, B6 alphabet_count_scan) |
| `results/novelty_audit.json` | 0 novel algorithms among 5,543 correct programs |
| `results/rederive.json`, `results/rederive_tests.json` | stdlib re-derivations matching the above; placebos fail |
| `figures/F1`-`F8` | dose-response, quality-diversity, entropy, token maps, HR branch maps, locator, flip matrices, activation geometry |
| `method_out.json` (+ `full_`, `mini_`, `preview_`) | exp_gen_sol_out datasets k1_cells, k1_tokenmap, k1_locator, hr_branches, novelty_audit |

These numbers are the ones reported in `README.md` (Results, Bottom line, and the per-unit tables). A paper built on
this artifact draws its K1/HR results section from them.

## 6. Determinism caveats

- **Re-running the analysis** from the shipped rows is exact (`audit/rederive.py` reproduces every MAE, pass rate
  and Hill value to the last digit).
- **Re-generating programs** on a different GPU or batch shape changes a few CRN-coupled programs. On this L4, a
  different batch shape left 5/8 and 17/20 programs byte-identical (U1, U2). Per-slot label agreement with iteration
  7's programs at the same streams was 0.92-1.00 (results/stage0.json).
- **Judges.** The adjudication and novelty-audit responses are cached in `cache/judge_cache.jsonl`, so reruns
  reproduce them without new calls.
