# Reproducing this artifact

This file records what was actually run on 2026-10-20, in order, and how to reproduce it on Ubuntu.

There are two ways to reproduce the results:

- **Path A, re-analysis (CPU only, minutes).** This recomputes every reported number exactly from the per-sample data
  shipped in `data/`. It needs no GPU, no model and no API key.
- **Path B, full re-run (one ≥ 24 GB GPU, about 1 h).** This regenerates all samples. vLLM and HF sampling are not
  bit-reproducible across batch compositions and kernels, so a re-run reproduces the numbers only up to sampling noise.

All paths below are relative to this artifact's folder.

## 1. Get the artifact

This folder is one folder of the run's public GitHub repository.

```bash
git clone <repository-url> repo
cd repo/<path-of-this-folder>   # the folder that contains this file, method.py and src/
```

Inputs produced by other artifacts are read through one constant each, defined in `src/common.py`. Each can be
overridden with an environment variable:

| artifact id | role | default location (relative to this folder) | override |
|---|---|---|---|
| `art_0ndRfWKBWclR` | frozen bench (exp11) | `../../../iter_2/gen_art/gen_art_experiment_11` (sibling folder in the repository) | `AII_EXP11_DIR` |
| `art_6zBfl3kDjeiP` | template/padding file and the stored scores for the scorer gate (exp7) | `../../../iter_2/gen_art/gen_art_experiment_7` | `AII_EXP7_DIR` |
| `art_8_ULPE8jJQc_` | engine sources, provenance copy only (exp8) | `../../../iter_2/gen_art/gen_art_experiment_8` | `AII_EXP8_DIR` |
| `art_j3Rm_lr2nzR6` | iteration-1 dataset of another run; test-id provenance check only (skipped if absent) | `inputs/art_j3Rm_lr2nzR6` | `AII_DEP_DATASET_DIR` |

Only two stages read these folders:

- the **setup** stage, which copies the bench, the exp7 file, the exp8 sources and exp11's FRLP cells into `inputs/`;
- the **FRLP rescoring**.

Every other stage reads the copies already shipped in `inputs/`. No user-uploaded material was used: the run's
upload folder was empty.

## 2. System, Python and libraries

What was used:

- **Hardware.**
  - One NVIDIA GeForce RTX 4090 (24 GB VRAM, driver 595.91.07).
  - AMD Ryzen 9 7950X, with a container quota of 14 CPUs and 56 GB RAM.
  - Debian 12 container; Ubuntu works the same way.
  - **No C compiler** was installed, so Triton/Inductor could not build. That is why vLLM runs with `enforce_eager=True`
    and `TORCH_COMPILE_DISABLE=1`.
- **Python.** CPython **3.12.14**, provided by `uv`.
- **Libraries.** Every package in the venv is pinned in `requirements.txt` (178 packages, from `uv pip freeze`).
  `pyproject.toml` carries the same list; uv venvs have no `pip` binary.
  - Key versions: `vllm==0.11.0`, `torch==2.8.0`, `transformers==4.57.1`, `accelerate==1.15.0`, `numpy==2.2.6`,
    `scipy==1.18.1`, `pandas==3.0.6`, `statsmodels==0.15.0`, `zss==1.2.0`, `apted==1.0.3`, `pyarrow==26.0.0`,
    `matplotlib==3.11.2`, `openai==3.35.1`, `loguru==0.7.3`, `huggingface-hub==0.36.2`.

```bash
# system: an NVIDIA driver with CUDA 12.8 support; curl; git
curl -LsSf https://astral.sh/uv/install.sh | sh          # installs uv
uv venv .venv --python=3.12                              # CPython 3.12.14 was used
uv pip install --python .venv/bin/python -r requirements.txt
# equivalently: bash restore.sh   (venv + bytecode + model download)
```

The run actually installed the same set in two steps:

1. exp11's pinned requirements, together with `vllm==0.11.0 transformers==4.57.1 accelerate==1.15.0 zss apted
   statsmodels pandas pyyaml matplotlib`;
2. later, `pyarrow`, which is needed to read exp7's parquet scores.

`requirements.txt` is the freeze taken after both steps.

## 3. Model, data and credentials

- **Model.** `Qwen/Qwen3-8B` at Hub revision `b968826d9c46dd6066d109eabc6255188de91218` (bf16, about 16 GB).
  - It was downloaded with
    `uvx --from 'huggingface_hub[hf_xet]==0.36.2' hf download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218`.
  - The download goes into the Hugging Face cache named by `HF_HUB_CACHE` (or `HF_HOME`); `src/common.py:model_path()`
    reads the snapshot from there.
- **Environment variables, by name.**
  - `HF_HUB_CACHE` or `HF_HOME`: the model cache.
  - `HF_TOKEN`: optional.
  - `TORCH_COMPILE_DISABLE=1`: set automatically by the vLLM stages.
  - `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY`: the blind LLM judge (`google/gemini-2.5-flash-lite`). It is called
    only when the runtime and AST labellers disagree.
  - `BENCH_SANDBOX_PYTHON`: optional. It names the interpreter for the test sandbox; the default is `python3.12` on
    `PATH`.
  - `AII_EXP11_DIR`, `AII_EXP7_DIR`, `AII_EXP8_DIR`, `AII_DEP_DATASET_DIR`: see §1.
- **Judge cache.** Judge answers are cached in `data/judge_cache.jsonl`, keyed by judge model, task and code hash.
  Exp11's cache was copied in at setup. With the shipped cache, Path A makes **no** API calls. The original run spent
  USD 0.0244 on 344 judge calls (`logs/openrouter_spend.jsonl`), and the code caps judge spend at USD 0.60.

## 4. What was run, in order

The commands are the ones actually executed. Times are wall-clock on the hardware above.

| # | command (from this folder) | what it does | time |
|---|---|---|---|
| 1 | `.venv/bin/python src/setup_inputs.py` | copy inputs; verify 146 bench hashes; provenance line in `commitments.log`; `results/env.json`; dependency test-id check (528/528) | 5 s |
| 2 | `cd src && ../.venv/bin/python labelpool.py` | labeller re-check vs `gate.json` (12/12 pass) | 1 min |
| 3 | `cd src && ../.venv/bin/python prompts.py` | 192 prompts (12 tasks × 5 ban, 5 twin, 5 nonce and 1 novelty), token alignment asserted | 10 s |
| 4 | `cd src && ../.venv/bin/python ngrams.py` | n-gram unit tests and derivation (deterministic, run twice) | 1 min |
| 5 | `cd src && ../.venv/bin/python proximity.py` | AST tree-edit-distance nominees (zss = apted on 50/50 pairs) | 30 s |
| 6 | `cd src && ../.venv/bin/python vllm_stage.py A --smoke` | smoke test (T03 and T05; veto unit tests) into `data/smoke/` | 4 min |
| 7 | `cd src && ../.venv/bin/python vllm_stage.py A` | **process A**: twin, one-shot, sham, persistent, nonce, novelty, iterated rounds 1-3 | 6 min (+1 min load) |
| 8 | `cd src && ../.venv/bin/python forecasts.py nominees` | ASSOCIATE and FRLP_FP8 nominees | 1 s |
| 9 | `cd src && ../.venv/bin/python hf_stage.py B --smoke` | hook unit tests (first attempt failed: capture order and clean-state path; both fixed, then rerun, all pass) | 2 min |
| 10 | `cd src && ../.venv/bin/python hf_stage.py B` | **process B**: norms, 3 random directions × 50, HF twin × 50 per task | 8 min |
| 11 | `cd src && ../.venv/bin/python forecasts.py dryrun`; `../.venv/bin/python analyze.py --dryrun`; `.venv/bin/python tests/dryrun_full.py` (run from this folder) | dry runs before the seal (scratch log, tamper test, novelty/nonce as stand-in ban; no ban sampled) | 2 min |
| 12 | `cd src && ../.venv/bin/python score.py && ../.venv/bin/python c2b.py && ../.venv/bin/python forecasts.py build && ../.venv/bin/python forecasts.py commit` | scoring and C2b unit tests; final forecasts; 17 committed files; `SEAL_BEFORE_BANS` at 18:50:57Z | 1 min |
| 13 | `cd src && ../.venv/bin/python vllm_stage.py C` | **process C**: guard, then 1,200 modal-ban samples (first request at 18:55:16Z), labels | 4.5 min |
| 14 | `cd src && ../.venv/bin/python hf_stage.py D` | **process D**: band-patch control, 600 samples | 5 min |
| 15 | `cd src && ../.venv/bin/python analyze.py && ../.venv/bin/python posthoc.py && ../.venv/bin/python sanity.py && ../.venv/bin/python outputs.py`; `.venv/bin/python audit/rederive.py` | committed analysis, post-hoc, sanity, outputs, audit | 1 min |
| 16 | `cd src && ../.venv/bin/python frlp_rescore.py` | **process D2**: fp32 FRLP rescoring (scorer gate passed: 0.021 nats) | 8 min |
| 17 | `.venv/bin/python method.py analyze posthoc sanity figures outputs audit` | full CPU re-analysis via the CLI (byte-identical results) | 1 min |
| 18 | `.venv/bin/python audit/rederive_raw.py` | second independent audit from the raw label files, with placebos | 30 s |

The step-17 stages can also be run as a single command: `.venv/bin/python method.py all` runs steps 1-18 in this
order. The Hugging Face cache must hold the model, and the sibling artifacts must be present for `setup` and `frlp`.

**Seeds and configuration.**
- Every per-request seed is `int(sha256('iter3|exp|task|arm|template|idx')[:8], 16)`.
- Veto redraw and continuation seeds are `stable_seed('veto', seed, round, n_vetoes, 'r'|'c')`.
- HF common random numbers come from `PCG64(stable_seed('u', task, arm, template, idx))`.
- Random direction k at layer l is a normalised `N(0, I_4096)` from `default_rng(int(sha256('rand{k}|L{l}')[:16], 16))`.
- The C2b null uses seed 20261021 with 2,000 replicates; the vLLM engine seed is 0.
- Decoding: T = 1.0, top-p 1.0, top-k off, min-p 0, max 1,024 new tokens, thinking off.
- vLLM settings: `gpu_memory_utilization=0.90, max_model_len=2048, max_num_seqs=64, max_num_batched_tokens=4096,
  enable_prefix_caching=True, generation_config='vllm', enforce_eager=True`.
- HF settings: bf16 with SDPA attention; batch 20; patch layers 12-23 at the task-spec positions.
- Every seed is listed in `predictions/seeds.json`, and every frozen constant in `predictions/constants.json`.

**Commitment and the one post-ban change.**
- `commitments.log` is a sha256 hash chain: provenance → 17 forecast/analysis-code commitments → `SEAL_BEFORE_BANS`.
- After the bans, `src/common.py` had its absolute input paths replaced by the relative constants of §1. Nothing else
  in it changed; the diff is `audit/sealed_files/common_py_post_ban_revision.diff`.
- This change is appended to the log as a `post_ban_revision` line (and a `post_ban_note`). The sealed bytes are kept
  in `audit/sealed_files/src_common.py.sealed`, an archival copy that still contains the original paths and is never
  executed; its sha256 equals the committed hash.
- `vllm_stage.guard()` verifies the chain, every committed file, and this documented revision.

### Path A: re-analysis only (exact)

```bash
.venv/bin/python method.py analyze posthoc sanity figures outputs audit
.venv/bin/python audit/rederive_raw.py
```

### Path B: full re-run

Keep `data/judge_cache.jsonl` and remove the generated state. `method.py commit` refuses to re-seal an already sealed
log.

```bash
mv commitments.log commitments.original.log
rm -rf data/raw data/labels data/smoke data/samples.jsonl predictions prompts results figures scratch
.venv/bin/python method.py all            # needs the GPU, the model cache and the judge credentials
# without the sibling artifacts: skip 'setup' and 'frlp' (inputs/ already holds the copies), e.g.
# .venv/bin/python method.py recheck prompts ngrams proximity nominees gen_a hf_b forecasts commit gen_c hf_d \
#                            analyze posthoc sanity figures outputs audit
```

Without `setup`, the chain starts at the forecast commitments; the provenance line is skipped.

## 5. What a reader should get

The table below lists what Path A reproduces exactly. The same numbers are re-derived independently by
`audit/rederive_raw.py` (written to `results/rederive_raw.json`).

| quantity | value | file |
|---|---|---|
| gated modal bans (avoidance ≥ 0.5 and ≥ 20 non-banned attempts) | 5 of 12: T03, T06, T05, T10, T13 | `results/c1_events.jsonl` |
| ban avoidance per task | T03 0.97, T04 0.40, T06 0.79, T05 0.86, T10 1.00, R1 0.00, T08 0.34, R3 0.08, T13 0.58, R6 0.03, T14 0.48, T11 0.02 | same |
| C1 frozen verdict / wins | SUBTRACTION/LADDER (LADDER): LADDER 3, PROXIMITY 2, SUBTRACT 0, ASSOCIATE 0 | `results/analysis.json → c1` |
| post-hoc defined-only wins | LADDER 1, PROXIMITY 2: no family advances | `results/posthoc_sensitivity.json` |
| mean log score minus uniform (gated) | LADDER +0.06, SUBTRACT −0.69, PROXIMITY −1.53, ASSOCIATE −1.78 | same |
| C2b (one-shot) | UNDETERMINED, 0 eligible. Descriptive last-iterated round: T06 and T10 land elsewhere (JS 0.766, 0.584) | `results/analysis.json → c2b` |
| template effect | LR 374.1, df 4, p ≈ 1.1e-79; shuffled-template placebo LR 4.1, p 0.39 | `results/template_effect.json`, `results/rederive_raw.json` |
| task-shuffled placebo | mean wins ≈ 0.5-1.0 per family (vs 3 / 2 observed) | `results/rederive.json`, `results/rederive_raw.json` |
| band-patch avoidance | T03 1.00, T10 1.00, T05 0.22, T13 0.14 | `results/analysis.json → descriptives` |
| FRLP fp32 vs FP8 | 50 cells; median \|ΔL_corr\| 0.88 nats, max 9.05; argmax unchanged 12/12 | `results/frlp_rescore.json` |
| re-emergence / leaks / disguise | D in every veto round 9/12; one-shot fire 0.95, text leak 0.23 (0.54 by round 2); disguise 0.88-1.00 | `results/analysis.json → descriptives` |

No paper exists yet; it is written downstream. It should take these numbers from `method_out.json → metadata` (`c1`,
`c2b`, `descriptives`, `template_effect`, `posthoc_sensitivity`, `frlp_rescore`, `rederive`) and from the README
tables. The candidate results figures are `figures/logscores_by_family_v2.png`, `figures/avoidance_by_arm.png`,
`figures/composition_per_task.png` and `figures/template_task_banned_share.png`.

Two numbers have no independent second code path:

- the mixed-GLM variance-component SDs (template ≈ 2.0, template×task ≈ 1.25 logits);
- the descriptive C2b null 95th percentiles (≈ 0.09).

Both come from the single statsmodels path and the seeded resampling path in the committed analysis. The template
effect itself is confirmed by the independent logistic likelihood-ratio test and its placebo.
