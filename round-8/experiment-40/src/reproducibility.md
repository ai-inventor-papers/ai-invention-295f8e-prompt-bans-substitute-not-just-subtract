# Reproducing "Checking for a hidden algorithm switch" (iteration 8, DAS with seven controls)

These are the steps that were ACTUALLY run, in order, including the reruns after crashes. Every path is relative to
this folder.

## 1. Get the artifact

This folder is published as one directory of a public GitHub repository.

```bash
git clone <repository-url>
cd <repository>/<this-artifact-folder>     # the folder that holds README.md, method.py, src/, inputs/
```

The folder already ships its frozen inputs (`inputs/`, sha256 in `inputs/input_hashes.json`), every prompt with its
token ids (`prompts/`), all per-sample rows (`data/`), the fitted maps (`das_maps/`) and every result file
(`results/`). Two kinds of material are not shipped: the activation caches (`cache/`, regenerable) and the
Python environment (`.venv/`).

No user-uploaded files were used: the run's upload folder was empty.

## 2. System, Python and libraries

What the run used:

| item | value |
|---|---|
| OS | Debian GNU/Linux 12 (bookworm) container; Ubuntu 22.04 or later works the same |
| GPU | 1x NVIDIA L4, 23 GB VRAM (driver 595.91, CUDA runtime from the torch wheel: 12.8) |
| CPU and RAM | 6 CPUs (cgroup quota), 57 GB RAM limit |
| Python and uv | Python 3.12.14, uv 0.6.14 |
| libraries | 85 packages pinned with `==` in `pyproject.toml` (identical to `uv pip freeze`) |

Key library versions: torch 2.8.0 (PyPI CUDA 12.8 build), transformers 4.57.6, numpy 2.2.6, scipy 1.18.1,
scikit-learn 1.9.1, matplotlib 3.11.2, loguru 0.7.3, openai 3.35.1.

```bash
sudo apt-get install -y python3.12 git      # or let uv fetch Python 3.12
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
```

## 3. Models, data and environment variables

- **Models** (Hugging Face, pinned revisions), downloaded into the Hugging Face cache:

  ```bash
  hf download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218
  hf download google/gemma-3-4b-it --revision 093f9f388b31de276ce2de164bdc2081324b9767
  ```

- **Environment variables** (names only):
  - `HF_HOME` and `HF_HUB_CACHE`: where the models live. `src/cfg8.py:model_path` reads `HF_HUB_CACHE`.
  - `HF_TOKEN`: the Gemma licence must be accepted on the Hub.
  - `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY`: used only by the novelty audit (`src/novelty8.py`). No call was
    made in this run (0 candidates, USD 0.00).
  - `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`: set by the GPU queue scripts.
  - Optional for S0 only: `AII_ARTIFACTS_DIR` (a folder holding the source artifacts as sibling folders named by id)
    and `ART_J3RM_DIR` (the dataset dependency).
- **Inputs from other artifacts.** `src/s0_inputs.py` copied them into `inputs/`, and they ship with this folder, so
  S0 never has to be re-run. To rebuild `inputs/`, point `AII_ARTIFACTS_DIR` at the published repository root, or
  keep the artifacts as sibling folders. The source artifacts, by id:
  - art_veI9l_Rb9wDY (iteration-7 T10 DAS prompts and code);
  - art_pHL7LWNhpcCS (T10 forks, remeasure);
  - art_HY7uYZz-OjRW (Gemma code, iteration-6 Gemma inputs, iteration-7 subspaces);
  - art_lpQalcAXMGr1 (push outcomes, known solutions, exp22 units and directions);
  - art_rMlbrjVB1c__ (exp30 engine and prompts);
  - art_j3Rm_lr2nzR6, the declared dataset dependency, read through `ART_J3RM_DIR` or `../art_j3Rm_lr2nzR6`.

  One file was added by hand after S0: `inputs/exp13/norms_T10.npz` (the absolute unit n[l,p]), copied from
  art_veI9l_Rb9wDY's `inputs/exp13/results/tensors/norms_T10.npz`.

## 4. Commands in the order they were run (wall clock 00:44-05:30 UTC, 2026-10-23)

All GPU stages load one model at a time; each skips work whose result file exists.

### CPU stages

| step | command | runtime |
|---|---|---|
| S0 inputs | `.venv/bin/python src/s0_inputs.py` (first pass, then rerun with the corrected noun-flag field) | ~1 min |
| S1 prompts | `.venv/bin/python src/prompts8.py` | ~3 min |
| COMMIT #0 | `.venv/bin/python src/commit0.py` | seconds |

S1 produces 290 T10 prompts and 207 GRID prompts. COMMIT #0 runs before any GPU use.

### GPU stages

1. `.venv/bin/python src/run_dec.py --unit T10` (~23 min).
   - What it runs: S3 token maps and adherence; COMMIT #1; caches; U-tests; scan of blocks 0, 2, ..., 34; fits at
     L* = 22; controls c1, c2, c4-c7.
   - The first attempt was stopped at block 2 of the scan to fix a NaN-ordering bug in the L* argmax, then
     restarted.
2. `.venv/bin/python src/run_gen.py --unit T10 --sites dec --minutes 30 --B 16` (~8 min, 419 programs). COMMIT #2
   runs first, and `src/label8.py` labels in the background.
3. `.venv/bin/python src/run_rinit.py --unit T10` (~4 min): c3 on a random-init Qwen3-8B.
4. `.venv/bin/python src/run_dec.py --unit GRID`: crashed in the 2-class label control (no pair survives a
   2-class derangement).
5. `.venv/bin/python src/run_band.py --minutes 35` (~30 min): T10 band, 109 steps per fit.
6. `.venv/bin/python src/run_gen.py --unit T10 --sites band --minutes 18 --B 16` (~9 min).
7. `.venv/bin/python src/run_dec.py --unit GRID`, rerun with the F3 balanced-shuffle control (~12 min). It reuses
   `results/scan_GRID.json` and the seed maps fitted before the crash.
8. `.venv/bin/python src/run_gen.py --unit GRID --sites dec --minutes 16 --B 16` (~4 min, 220 programs).
9. `.venv/bin/python src/run_rinit.py --unit GRID` (~3 min).
10. `.venv/bin/python src/run_rinit.py --unit T10 --band --band_minutes 8` (~4 min).
11. `.venv/bin/python src/run_med.py --minutes 28`: computed the predictor, COMMIT #3 and the Spearman tests, then ran
    out of GPU memory in the clamp rows. The rerun `.venv/bin/python src/run_med.py --minutes 24` (~24 min) ran
    COMMIT #4, the clamp (270 slots) and the prospective set (208 programs).
12. `.venv/bin/python src/run_post.py --unit T10` (~3 min): per-pair label-control test (p_c2) from the saved maps.
13. `.venv/bin/python src/run_dec.py --unit T10 --force_L 24` (~20 min): post-hoc block-24 sensitivity.
14. `.venv/bin/python src/run_rinit.py --unit T10 --force_L 24` (~3 min).
15. `.venv/bin/python src/label8.py --unit T10`: labels the mediation rows.

`scripts/gpu_queue*.sh` hold the exact queues used. Total GPU time was about 3.2 h on the L4.

### Analysis and outputs (CPU)

```bash
.venv/bin/python src/analysis8.py      # verdicts, K2, mediation outcomes -> results/analysis.json
.venv/bin/python src/novelty8.py       # novelty audit (0 candidates -> no API call)
.venv/bin/python src/figures8.py       # figures/F1-F5 (PDF + PNG)
.venv/bin/python src/digest8.py        # results/summary.md (tables straight from the JSONs)
.venv/bin/python src/outputs8.py       # method_out.json
# full_/mini_/preview_method_out.json come from the aii-json skill's format script:
#   aii_json_format_mini_preview.py --input method_out.json --format exp_gen_sol_out
python3 audit/rederive.py              # stdlib-only re-derivation + placebos -> results/rederive.json
.venv/bin/python tests/test_cpu_tiny.py   # CPU equivalence tests (results/unit_tests_cpu.json)
```

`.venv/bin/python method.py` runs the same stage order end to end. `.venv/bin/python method.py --cpu-only` re-runs
only the analysis and output stages from the saved rows.

### Seeds and configuration (all in `src/cfg8.py` and `predictions/commit0.json`)

- **Fits:** fit seeds 0, 1, 2 (init `torch.Generator().manual_seed(1000 + seed)`); Adam, lr 2e-2, 240 steps
  (scan 100; band 109).
- **Early stopping:** inner-validation KL every 20 steps, patience 3.
- **Controls:** random subspaces use Haar seeds 7000-7049; label controls use fit seeds 10-12.
- **Random-init networks:** `torch.manual_seed(0)`, then HF `post_init`.
- **Splits and sampling:** noun split seed 8001; pair sampling seed 8002; bootstrap 2,000 resamples (seed 0 per
  call).
- **Generation:** CRN stream `PCG64(sha256(unit|site|iter8|slot))`; temperature 1.0, top-p 1, no top-k;
  max_new_tokens 512 (T10) and 1,024 (GRID); fence stop.
- **Mediation:** iteration-4 directions `rand_9101`-`rand_9140`, alpha 2; prospective directions 98001-98024 from
  `PCG64(seed)` normalised Gaussians.

## 5. What a reader should get

### Files

| file | contents |
|---|---|
| `results/analysis.json` | verdicts per (unit, site), K2 status and p_K2, mediation outcomes |
| `results/summary.md` | all tables (auto-generated) |
| `results/dec_T10.json` | T10 decision site (L* = 22, k* = 4) |
| `results/band_T10.json` | T10 task band (k* = 2) |
| `results/dec_GRID.json` | GRID decision site (L* = 16, k* = 4) |
| `results/rinit_*.json` | random-init control c3 |
| `results/mediation_T10.json` | mediation |
| `results/dec_T10_L24.json` | post-hoc block-24 sensitivity |

### Headline numbers

All of these are re-derived by `audit/rederive.py` from the raw rows (`results/rederive.json`: 38 checks, all
match), except c3, which is recomputed only from the stored per-site means.

- **Teacher-forced held-out recovery at k*:** T10 decision 8.43 (OFF-MANIFOLD), T10 band 0.82, GRID decision 3.07,
  T10 block 24 (post hoc) 1.22.
- **c2 label-control ratios** (limit 0.10):
  - T10: 0.87, 0.63, 0.77;
  - GRID: 0.11, 0.11, 0.20;
  - T10 block 24: 0.61, 0.57, 0.50.
- **c3 random-init ratios** (limit 0.25): T10 0.69, GRID 0.41, band 0.18, T10 block 24 0.54.
- **Generation**, correct target programs out of 30 (DAS / FULL / RAND / BASE):
  - T10 decision, DFS: 29 / 2 / 0 / 0;
  - T10 decision, BFS: 5 / 0 / 0 / 0, with 29 attempting BFS;
  - T10 band, BFS: 28 / 23 / 0 / 0;
  - T10 band, DFS: 3 / 20 / 0 / 0;
  - GRID decision, BFS: 22 / 10 / 5 / 6.
- **Verdicts:**
  - T10 decision: NO HANDLE (pooled pass ratio 0.72);
  - T10 band: SUFFICIENT HANDLE (fails c2, c5, c7);
  - GRID decision: SUFFICIENT HANDLE (fails c2, c3, c5, c6).
  - K2: DISCONFIRMED, p_K2 = 0.037.
- **Mediation:**
  - retrospective Spearman 0.39 (bar 0.5); prospective 0.09;
  - clamp removal: band subspace -0.01, random 0.02, decision site -0.05 among reached slots.
- **Novelty:** 0 'other' programs among 1,857 correct programs.

### Paper mapping

- The Results tables, verdict table and figures in `README.md` and `results/summary.md` are what the run's report
  and paper cite.
- Geometry figures: `figures/F3_geometry_T10` and `F3_geometry_GRID`.
- Scan: `figures/F1_scan_profile`.
- Recovery by rank: `F2_recovery_by_rank`.
- Generation: `F4_generation`.
- Mediation: `F5_mediation`.

### Reproduction tolerance

Teacher-forced numbers are deterministic up to bf16 kernel differences: the KV path differs from full recompute by
at most 0.25 nats, and every Delta is measured within one path. Generation runs bf16 on a CRN stream, so a different
GPU model or batch shape can change individual slots. Expect counts within a few slots per cell; verdicts can flip
only where a criterion sits near its threshold (for example GRID's pass ratio 0.81 against 0.80).
