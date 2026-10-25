# Reproducing NOV-R (banned bin-packing rules: lexical vs behavioural compliance)

This file describes what was actually run, in order, including the container crash and the restart. All paths are
relative to this folder.

## 1. Get the artifact

The workspace is published as one folder of a public GitHub repository:

```bash
git clone <repository-url>
cd <repository>/<this-artifact-folder>
```

The declared dependency `art_j3Rm_lr2nzR6` (the algorithm-choice source dataset) is published as a sibling folder.
Its human-written xlcost_python first/best/worst-fit programs are hand-adapted inline in `src/gate_instr.py`, and its
small files are copied into `inputs/dep_j3Rm/`, so nothing reads the sibling at run time. `src/setup_inputs.py` finds it
through `NOVR_DEP_ART_J3RM` (default `../art_j3Rm_lr2nzR6`). The reused iteration-8/9 inputs (bin-packing harness,
instances, sampler, templates) are already copied into `inputs/`, `src/`, `data/instances/`, `ext/` and `tools/`, with
their sha256 in `inputs/inputs_manifest_public.json`. The original sources lived on the run volume and are not needed.
No user-uploaded file is used.

## 2. System and Python environment

* Ubuntu (Linux 6.8 container), Python **3.12.14**, [uv](https://github.com/astral-sh/uv), `git`, `curl`, NVIDIA driver
  with CUDA (GPU only to re-sample Qwen3-8B).
* Create the environment with the exact versions that were installed (all 177 packages are pinned in `pyproject.toml`;
  `logs/pip_freeze.txt` is the raw freeze):

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r pyproject.toml
```

  Key pins: vllm 0.11.0, torch 2.8.0, transformers 4.57.1, numpy 2.2.6, scipy 1.18.1, scikit-learn 1.9.1,
  statsmodels 0.15.0, matplotlib 3.11.2, aiohttp 3.14.5, requests 2.34.2, loguru 0.7.3, ziglang 0.17.0 (`tools/cc`
  is a ziglang C-compiler shim for Triton).
* `restore.sh` runs the two install commands above and the model download.

## 3. Downloads, environment variables and keys (names only)

* Model for the local engine: `huggingface-cli download Qwen/Qwen3-8B-FP8 --revision 220b46e3b2180893580a4454f21f22d3ebb187d3`
  (into the Hugging Face cache named by `HF_HOME` / `HF_HUB_CACHE`; `start_vllm.sh` reads the snapshot from there).
* OpenRouter (Qwen3-14B and Qwen3-32B samples, naming checks, any P3 judges): `OPENROUTER_BASE_URL`,
  `OPENROUTER_API_KEY`. Provider pinned to DeepInfra fp8 with `allow_fallbacks: false`.
* Optional run controls (values used are in section 4): `NOVR_STOP_OR_H`, `NOVR_STOP_LOCAL_H`, `NOVR_OR_WORKERS`,
  `NOVR_EVAL_WORKERS`, `NOVR_QUALITY_STOP_H`. Input-copy step only: `NOVR_ITER9_GEN_ART`, `NOVR_ITER8_GEN_ART`,
  `NOVR_DEP_ART_J3RM`. Positioning queries only: `AII_WEB_TOOLS_DIR` (the aii-web-tools skill folder).

## 4. Commands, in the order they were run

Hardware: first container NVIDIA RTX 4000 Ada (20 GB), 7.65-CPU cgroup quota, 50 GB RAM (`predictions/hardware.json`).
After the crash: NVIDIA RTX A4500 (20 GB), 10.2-CPU quota, 62 GB RAM. No GPU work was needed after the restart because
Qwen3-8B was complete. Elapsed times are hours from the start (`logs/time_ledger.jsonl`, start 2026-10-24T17:46Z).

| Step | Command | When / runtime |
|---|---|---|
| S0 setup: input copy and hash check (`src/setup_inputs.py`, stdlib only), venv install, key check, smoke calls | `.venv/bin/python method.py --stage s0` | 0.0-0.84 h |
| S1 harness gate (BF 5.37% OR3, 3.98% Weibull 5k; c12 3.11%; c14 0.68%) | `.venv/bin/python method.py --stage s1` | 1 min |
| S3 probes P10 (rng 20261024; 1,000 trace + 1,000 uniform states) | `.venv/bin/python method.py --stage s3` | 3 min |
| S4/S5 corpus (427 members, tuned ab-FF(5,25)) and instrument gate | `.venv/bin/python method.py --stage s45` (run twice: the first gate run caught an RNG-patch bug, fixed before commit #1, deviation D8) | 2 x 7 min |
| S6 unit tests U4-U8/U10 and commit #1 (hash chain genesis sha256('nov_r_iter10')) | `.venv/bin/python method.py --stage s6` | at 3.15 h |
| Local engine | `bash start_vllm.sh` (vLLM 0.11, FP8 Marlin, max-model-len 6144) | about 5 min to load |
| S7 engine smoke tests | not run as a separate stage: the OpenRouter smoke calls ran in S0 (`results/smoke.json`), and the local no-`<think>` check is the first BASE_10 batch of S8 (`--stage s7` exists) | - |
| S9 evaluator (beside S8) | `NOVR_EVAL_WORKERS=5 .venv/bin/python method.py --stage s9` | continuous |
| S8 sampler, first run | `NOVR_STOP_OR_H=4.45 NOVR_STOP_LOCAL_H=4.55 NOVR_OR_WORKERS=12 .venv/bin/python method.py --stage s8` | 3.26-4.2 h |
| (container crash at about 4.2 h; restart) | single-instance locks added; 5 duplicate rows moved aside | 5.9 h |
| S9 evaluator, restart | `NOVR_EVAL_WORKERS=8 NOVR_QUALITY_STOP_H=8.6 .venv/bin/python method.py --stage s9` | 5.97-7.6 h |
| S8 sampler, restart (clean naming rerun -> commit #3, then remaining cells) | `NOVR_STOP_OR_H=7.5 NOVR_STOP_LOCAL_H=7.5 NOVR_OR_WORKERS=16 .venv/bin/python method.py --stage s8 --models q32,q14` | 5.97-7.55 h |
| Positioning queries | `.venv/bin/python src/positioning_search.py` (verdicts hand-written into `results/positioning.json`) | 1 min |
| S11 P3 audit (0 candidates, so no judge call) | `.venv/bin/python method.py --stage s11` | seconds |
| S10 analysis + figures (JT with 100,000 permutations, seed 20261026) | `.venv/bin/python method.py --stage s10` | 1-12 min, depending on CPU load |
| Independent re-derivation (stdlib only) | `python3 -I audit/rederive.py` | about 2 min |
| S12 outputs | `.venv/bin/python method.py --stage s12` | 1 min |
| Output variants and validation | aii-json `aii_json_format_mini_preview.py --input method_out.json`; `aii_json_validate_schema.py --format exp_gen_sol_out` | seconds |

Seeds: sample seed = 1000 x cell index + slot + 1 (T 1.0, top-p 1.0); naming-check seeds 900000 + 100 x rule + 20 x
version + slot + 1; harness probe seeds 0 and 1 (plus 2 and 3 for stochastic programs), with np.random.seed((1000003 s + i)
mod 2^32) before state i. Samples are not byte-reproducible: OpenRouter/DeepInfra and vLLM FP8 generations vary even
with a fixed seed. Re-running S8 therefore gives new samples; S9-S12 and `audit/rederive.py` on the shipped `data/`
reproduce the numbers below exactly.

To reproduce only the analysis from the shipped data (no GPU, no API):

```bash
.venv/bin/python method.py --stage s10 && python3 -I audit/rederive.py && .venv/bin/python method.py --stage s12
```

## 5. What you should get

* `results/p1.json` -> verdict **PARTIAL**: the k = 5 lexical-minus-mechanistic gap is +0.40 [0.21, 0.55] for Qwen3-8B,
  +0.04 [-0.12, 0.20] for Qwen3-14B and -0.13 [-0.31, 0.04] for Qwen3-32B (paired Newcombe). JT permutation p is 0.54,
  0.038 and 0.38.
* `results/p2.json` -> **DISCONFIRMED** (described-minus-named difference 0.03, 0.00, 0.00; only first fit's description
  passed the naming check).
* `results/p3.json` -> **SUPPORTED** (0 of 1,143 samples are better than best fit on both held-out sets; 186 are novel
  by behaviour, and none of those is better).
* `results/rename_table.json`: Qwen3-8B NAME_1 rename rate 14/35 = 0.40; Qwen3-14B 0/28; Qwen3-32B 0/26.
* `results/cells.json`: per model x cell N, VALID, L1 and mechanistic rates with Wilson intervals, and class composition
  (Qwen3-14B BASE 50/50 best fit; Qwen3-32B 48/49; "Make a new algorithm" 28/29 and 28/28 best fit).
* `results/rederive.json`: `n_mismatches_total` 0 and `placebos_all_fail_as_required` true. The hash-chain entries show
  `payload_ok` false for `commit2_q14` and `commit2_q32`, because their payload files were overwritten by the duplicate
  orchestrator (see README).
* Figures F1-F6 in `figures/` (F1 compliance vs k; F3 MDS map in decision space). These are the paper's compliance,
  class-composition and behaviour-map figures.
* Spend: USD 1.42 of OpenRouter in total (`results/costs.json`; the per-row sum is in `method_out.json` ->
  `metadata.cost_from_raw_rows_usd`).
