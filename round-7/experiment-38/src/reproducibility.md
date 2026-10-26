# Reproducibility: Circuit and dose dial at Gemma's BFS-vs-DFS fork (iteration 7)

This file was written after the run, from the workspace contents (`method.py`, `src/`, `README.md`,
`pyproject.toml`, `logs/`, `results/`). Where the workspace records nothing, this file says so.

## 1. Get the artifact

The workspace is published as one folder of a public GitHub repository. The repository URL is not
recorded in the workspace. Use the URL you got this artifact from:

```bash
git clone <REPOSITORY_URL> repo
cd repo/<this-artifact-folder>        # the folder holding method.py, pyproject.toml, README.md
```

All paths below are relative to that folder. The code resolves paths from `Path(__file__)`
(`method.py`: `ROOT = Path(__file__).resolve().parent`; `src/cfg.py`: `ROOT = Path(__file__).resolve().parents[1]`).

**Upstream input.** The single input from another artifact is read through one constant,
`I6 = ROOT / "inputs" / "iter6_gemma"` (`src/cfg.py`). It is a read-only copy of artifact
**art_zNyBP6zieI5u** (iteration 6, the Gemma artifact; see `paths.local.json`), vendored inside this folder
with `inputs/iter6_gemma/MANIFEST.sha256`. It holds iteration 6's code, results and raw T1 rows, plus the
inputs that artifact staged: the exp8 T1 suite, extracts of dependency art_j3Rm_lr2nzR6, and exp7/exp9/exp11/exp23 files.
No input was uploaded by the user. Stage `s0` checks the copy against its manifest (133/133 sha256 match).

## 2. System, Python and environment

- OS: Ubuntu Linux (container). Python **3.12** (`requires-python = "==3.12.*"`; `logs/venv.log` shows CPython 3.12.14).
- Installer: `uv`. The main venv holds 95 packages, all pinned with `==` in `pyproject.toml`, for example
  `torch==2.8.0` (CUDA 12.8 wheels, `nvidia-*-cu12` pins), `transformers==4.57.6`, `accelerate==1.15.0`,
  `numpy==2.2.6`, `scipy==1.18.1`, `scikit-learn==1.9.1`, `sentence-transformers==5.1.2`, `openai==3.35.1`,
  `loguru==0.7.3`, `matplotlib==3.11.2`, `statsmodels==0.15.0`, `ruptures==1.1.10`, `pyarrow==21.0.0`.
  Use `pyproject.toml` as the full list.
- No system packages beyond an NVIDIA driver that supports CUDA 12.8 are recorded. The container had no C compiler.
  That only matters for the optional G1-T attempt below, which works around it.

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml        # ~4 min (logs/venv.log)
# optional, only for the G1-T circuit-tracer attempt (separate env):
uv venv .venv_ct --python=3.12
uv pip install --python .venv_ct/bin/python "circuit-tracer @ git+https://github.com/safety-research/circuit-tracer@255d989e93be1299d53d67b59e9fd76a0e274b14"
```

`.venv_ct` was not pinned to a lockfile beyond that commit. Its versions are not recorded, except that a ziglang
wheel was installed in it (`logs/ziglang_install*.log`) for `scratch/bin/cc`.

## 3. Models, downloads, environment variables

- Model: `google/gemma-3-4b-it`, revision `093f9f388b31de276ce2de164bdc2081324b9767`, bf16. This is a gated
  Hugging Face model, so you must accept its licence and be logged in (`huggingface-cli login`, or set `HF_TOKEN`).
- Transcoders (G1-T only): `mwhanna/gemma-scope-2-4b-it`, revision `61cb16ec74f348f4a8643fe3a0157be9dc8a851d`,
  `transcoder_all/width_16k_l0_big_affine/*`.
- The code downloads both on first use. To pre-fetch them:
  ```bash
  huggingface-cli download google/gemma-3-4b-it --revision 093f9f388b31de276ce2de164bdc2081324b9767
  huggingface-cli download mwhanna/gemma-scope-2-4b-it --revision 61cb16ec74f348f4a8643fe3a0157be9dc8a851d \
      --include "transcoder_all/width_16k_l0_big_affine/*.safetensors" "transcoder_all/width_16k_l0_big_affine/config.yaml"
  ```
- Environment variables (names only):
  - `OPENROUTER_API_KEY` and `OPENROUTER_BASE_URL`: the labeller's blind judge (openai/gpt-4.1-mini, via the
    vendored exp8 `judge.py`) and the novelty audit/style re-gate (`src/novelty.py`). Spend is capped at USD 0.50 in code.
  - Optional: `HF_HUB_CACHE` (read by `src/cfg.py`), `HF_TOKEN`.
  - `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` (set during the run).
- Judge answers are cached in `data/judge_cache_paths.jsonl`. On a rerun over the same programs, the cache is used
  instead of new API calls.

## 4. Commands as run, in order

Entry point: `.venv/bin/python method.py --stage <name>`. The CLI flags are `--stage` (required), `--follow`,
`--n_cal` (default 25), `--quick` and `--part` (default `all`). The run used only `--stage` and `--follow`.

```bash
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
.venv/bin/python method.py --stage label --follow &      # CPU label worker; stops when data/STOP_LABELLER exists
for st in s0 engine yv g3a g3b g2 g2r g2d g2pairs g1p g1v g1gen; do .venv/bin/python method.py --stage $st; done
# G1-T attempt (failed with OOM on 16 GB; result recorded in results/g1t_graphs.json)
.venv/bin/python src/prep_ct.py scratch/ct_input.json && \
  CC=$(pwd)/scratch/bin/cc timeout 720 .venv_ct/bin/python src/ct_graph.py scratch/ct_input.json results/g1t_graphs.json
touch data/STOP_LABELLER
for st in novelty analysis figures outputs; do .venv/bin/python method.py --stage $st; done
python3 audit/verify_chain.py && python3 audit/rederive.py
```

In the actual run, the stages ran through the chain scripts `scratch/chain*.sh` (`logs/chain*.out`). The order was
s0 → engine → yv → g2smoke → g3a → g3b → g1p → g2 → g2r → g2d → g1p (re-run after commit #2 was superseded by
#2b, deviation D07) → g1v → g1gen → g2pairs → ct → novelty → analysis → figures → outputs. `g2smoke` (a smoke test)
and an early killed `g3b`/`g2` attempt are part of that history. Pre-registered commits #0, #1, #2b and #3 are written to
`commitments.log` and `predictions/` by stages s0, g3a, g1v (via g1p) and g2d before the samples they predict.

**Seeds / randomness.** Common random numbers (CRN): every generation slot gets its own uniform stream,
`PCG64(stable_seed(*key))`, where `stable_seed` is a sha256 of the key parts (`src/cfg.py`). Slots reproduced from
iteration 6 use iteration 6's own keys. The DAS seeds are {0, 1, 2}, with ranks {1, 2, 4, 8}. The random baseline
uses `torch.Generator().manual_seed(0)`. Generations are deterministic given the seeds, but bf16 kernels and batch
shape matter (U3 differs by up to 0.27 nats; D05). Reproduce on the same batch size (B_CRN = 25) and expect small
numerical drift on other GPUs.

**Hardware.** One NVIDIA RTX 2000 Ada (16 GB VRAM), 6 CPUs, 28 GB RAM (deviation D01: planned A4500 20 GB).
max_new = 1024 tokens.

**Runtime** (`results/timing.json`, seconds): s0 135, engine 1130, yv 129, g3a 109, g3b 345, g1p 444 (two runs),
g2 2803, g2r 282, g2d 1412, g1v 1397, g1gen 292, g2pairs 111, novelty 22, analysis 49, figures 46, outputs 61.
The CPU label worker ran in parallel for 5684 s. GPU time is about 2.5 h, and the wall clock was about 4 h
(16:11-19:58 UTC, 2026-10-22).

## 5. Expected outputs and numbers

- `results/*.json`: every analysis. `figures/F1`-`F7` (`.png` and `.pdf`). `method_out.json` and its
  `full_`/`mini_`/`preview_` variants. `full_method_out.json` metadata records `analysis_status` all `"ok"` and a total
  cost of USD 0.04368 (labeller judge 0.036419 over 88 calls; novelty and re-gate 0.00726).
- Audits: `results/verify_chain.json` `chain_ok: true`; `results/rederive.json` 52 checks, 0 mismatches.
- Headline numbers (README.md "Short answer"; this workspace contains no paper, so README sections stand in for it):
  - **G3** (`results/g3_predictions.json`, `results/g3_sweep.json`, F6/F7): predicted vs observed BFS share at top-p 1:
    T0.3 0.015 vs 0.02; T0.7 0.17 vs 0.24; T1.0 0.32 vs 0.34; T1.3 0.45 vs 0.46 (MAE 0.026). H(label | class) = 0.15 bits.
    From T 1.0 to 0.3, 16/50 CRN pairs switch to DFS (p = 1.5e-5). Top-k 10 leaves every program unchanged.
  - **G2** (`results/g2_das.json`, `g2_decisions.json`, `g2_rinit.json`, `g2_dose.json`, F3-F5): L* = 17, rank 4,
    held-out IIA 1.00, dy 7.6 nats; RAND 0.00, SHUF -0.30. Correct BFS programs (N = 50) are 11 (twin) and
    20/27/31/37/38/42 at lambda 0.1-1. DiM breaks the programs (pass 0.70 → 0.00).
  - **G1** (`results/g1_pathpatch.json`, `g1_validation.json`, `g1_generation.json`, F1/F2): 1,224 nodes screened.
    7/10 nodes pass under ABLATE and 8/10 under STEER. Steering the top-5 raises correct BFS 8 → 16 (N = 30).
  - **Engine check** (`results/engine_check.json`): twin 19/50 BFS (0.38), 0.94 per-slot agreement with iteration 6.
  - **Novelty** (`results/novelty_audit.json`, `regate.json`): 0 of 2,325 correct programs labelled 'other'.
  - **DAS toy** (`results/das_toy.json`): DAS principal cosines 0.963/0.813 (held-out KL 0.297), shuffled 0.693/0.651,
    lr 2e-3 0.277/0.020. `pass: false`, which motivated deviation D04 (lr 2e-2).
- All deviations are listed in `results/deviations.json`.

**Not recorded:** the repository URL, the exact NVIDIA driver/CUDA driver version, and the package versions of
`.venv_ct` (beyond the circuit-tracer commit). `cache/states/` and `cache/das_subspaces/` may be absent from the
published copy. Rebuild them with `--stage yv` (~2 GPU-min) and then `--stage g2` (~47 GPU-min).
