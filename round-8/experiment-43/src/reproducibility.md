# Reproducing claim L (iteration 8): what was actually run

Every path below is relative to this folder. Nothing in the code depends on the original server: prior artifacts are read
from `inputs/src_*` copies (sha256 in `inputs/SHA256SUMS`) whenever the original run layout is absent.

## 1. Get the artifact

```bash
git clone <this repository>
cd <repository>/<this artifact's folder>
```

The declared dataset dependency **art_j3Rm_lr2nzR6** (`full_data_out.json`, 96 MB; used by the novelty audit's
known-solution corpus) is published as a sibling folder of this one. The code finds it as `../art_j3Rm_lr2nzR6`, or at the
path in the environment variable `ART_J3RM_DIR`. Every other prior artifact this pipeline reads (art_MZAfDPVhM6Ui,
art_zNyBP6zieI5u, art_HY7uYZz-OjRW, art_lpQalcAXMGr1, art_CcZLW-9NX00l and the iteration-2/5 bench, unit and suite files)
is copied into `inputs/` (`inputs/src_<name>/...`, `inputs/iter*_exp*/...`). No user-uploaded file was used (the run's
upload folder was empty).

## 2. System, Python and libraries

- Hardware used: 1 x NVIDIA RTX A4500 (20 GB VRAM; driver 595.91, CUDA 13.2 runtime), 11 CPU cores (cgroup quota),
  57 GB RAM. Any CUDA GPU with >= 20 GB should run it; exact token-level reproduction needs the same GPU class and batch
  composition (bf16 kernels are batch- and GPU-sensitive; see the engine checks in the README).
- OS: Debian 12 / Ubuntu 22.04 or later, with `git` and `uv` (https://docs.astral.sh/uv/). No other system packages.
- Python 3.12.14 in a uv virtual environment, with the 85 packages pinned in `pyproject.toml` (these are exactly the
  versions installed; `uv pip freeze --python .venv/bin/python` matches the file one-to-one; torch 2.8.0 with CUDA 12.8
  wheels, transformers 4.57.6, numpy 2.2.6, scipy 1.18.1, matplotlib 3.11.2, openai 3.35.1):

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
```

## 3. Downloads, environment variables and keys (names only)

- Model weights (bf16, no quantisation), into the Hugging Face cache (`HF_HOME` / `HF_HUB_CACHE` if you set them):
  `.venv/bin/python src/download_models.py` fetches google/gemma-3-4b-it@093f9f38, meta-llama/Llama-3.1-8B-Instruct@0e9e39f2
  (gated: needs `HF_TOKEN` with access), Qwen/Qwen3-8B@b968826d and Qwen/Qwen3-8B-Base@49e3418f (full hashes in the script).
- Judges (Llama label re-gate, adjudication of 'other'-heavy cells, novelty audit): `OPENROUTER_BASE_URL` and
  `OPENROUTER_API_KEY` (OpenRouter-compatible endpoint). Total spend in this run: about USD 0.05 (`results/costs.json`).
- Optional: `ART_J3RM_DIR` (see 1), `AII_JSON_SKILL_DIR` (schema validation / mini-preview in `finalize.sh`, AI Inventor only),
  `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` (used in every GPU stage).

## 4. Commands, in the order they were run

All randomness is keyed: one PCG64 uniform stream per program slot, seed = sha256 of the slot key (fit twins reuse the
source artifacts' keys; locator, refinement, forced-token, second-decision and sweep streams use the `iter8L-*`
namespaces in `src/cfg8.py`); bootstraps and placebos use seed 20261023 (+ offsets). `method.py all` runs the same
sequence; what was actually run, stage by stage (from `src/`):

```bash
cd src
../.venv/bin/python prompts8.py            # prompt ids + checks -> prompts/prompts8.jsonl, results/prompt_checks.json
../.venv/bin/python tests_cpu.py           # U5/U8/U9/U10/U11, change-point rule, iteration-7 dry run, labeller references
../.venv/bin/python commit0.py             # protocol8L.json + code hashes -> COMMIT #0 (commitments.log)
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
../.venv/bin/python gpu8.py gemma tests,fit,locate,commit1,predict,commit2,sweep      # ~30 min GPU
../.venv/bin/python gpu8.py llama tests,fit,locate,commit1,predict,commit2,sweep      # ~2 h GPU (see below)
../.venv/bin/python gpu8.py qwen  tests,fit,locate,commit1,predict,commit2,sweep      # ~45 min GPU
../.venv/bin/python base_arm.py gpu qwen && ../.venv/bin/python base_arm.py gpu qwen_base   # ~6 min GPU
cd .. && ./finalize.sh   # judges (adjudicate), base-arm analysis, scoring, novelty audit, figures, summary, outputs,
                         # standard-library re-derivation (audit/rederive.py)
```

How the run actually went (all recorded in `results/deviations.json` and the hash chain `commitments.log`):

- Gemma ran first; its predict stage was re-run once (before COMMIT #2) after the entropy-rival rule was corrected.
- Llama: the bench candidates were re-measured in the committed order (T03 and T06 kept, COMMIT #1a); the label
  re-gate ran with two judges (COMMIT #1b). The Llama opening classifiers failed their gates, so locator continuations
  were completed and labelled (thinned grid). The locator was restarted three times while fixing bugs, each fix
  committed as an amendment before any Llama/Qwen commit (amendments 2-4); restarts reuse already-sampled
  continuations by their deterministic id. Under the plan's time box both bench units were dropped, leaving L-T1.
- Qwen and the base sub-arm ran after Llama's COMMIT #2 and sweep.
- `run_chain.sh` is the chain used for Llama -> Qwen -> base; `restore.sh` rebuilds the environment and models.

Approximate wall clock: about 5 h on the A4500 including debugging; the GPU stage times are in `results/timing.jsonl`.

## 5. What you should get

| file | content | values in this run |
|---|---|---|
| `results/verdict.json`, `results/summary.md` | claim-L verdict and every table | **PARTIAL**: 5/6 scored units pass; held-out 2/3 pass, only 3 held-out units scored (< 4 required); 0 held-out units with MAE > 0.2 |
| `results/analysis_L.json` | per-unit MAE of the law and the rivals (top-p 1, N = 100 per cell) | A3 0.029, B6 0.054, B3 0.043, G-T04 0.033, G-R6 0.014, L-T1 0.142 (flat baseline 0.055 / 0.030 / 0.093 / 0.043 / 0.073 / 0.138) |
| `results/locate_<unit>.json`, `predictions/commit1_*.json` | decision tokens | B3 ` Kr`/` Prim` at token 61; A3 ` n`/` left` at 18 + second decision at 19; G-T04 `for`/`try` at 31; G-R6 `first` at 12 + second decision at 24 |
| `results/base_subarm.json` | base vs instruct margins | gain 3.27 / 13.41 / 2.11 nats on T1 / T10 / T2; phrasing entropy difference 0.23-0.31 nats; committed prediction holds |
| `results/novelty_audit.json`, `results/novelty_manual.json` | correct off-catalogue programs | 10 distinct of 4,703 correct programs, 0 novel |
| `results/rederive.json`, `results/sign_test_rederived.json` | independent standard-library re-derivation (`audit/rederive.py`, `audit/sign_test.py`) | hash chain ok, 0 mismatches; sign test L < flat on 4/6 units, p = 0.34 |
| `figures/F1-F6` | locator curves, decision tokens, predicted vs observed, calibration, base vs instruct, replay | |
| `method_out.json` (+ `full_`, `mini_`, `preview_`) | exp_gen_sol_out output | 1,619 examples in 5 datasets |

These numbers feed the paper's claim-L results table (predicted vs observed algorithm shares over temperature,
law vs baselines) and its base-vs-instruct paragraph. With a different GPU class, program-level tokens differ for a
few percent of slots, so cell shares can move by sampling-level amounts (about 0.03-0.05); the committed predictions in
`predictions/` are what the scores in `results/` were computed against.
