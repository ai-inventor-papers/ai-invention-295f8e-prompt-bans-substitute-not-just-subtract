# Reproducibility: Where an algorithm ban takes effect

This file describes exactly what was run to produce the numbers in `results/`, `method_out.json` and `figures/`,
in the order it was run, on what hardware, with which seeds. Every path below is relative to this artifact's
folder.

## 1. Get the artifact

This workspace is published as one folder of the run's public GitHub repository. Clone the repository and `cd`
into this artifact's folder. In the published layout it is `round-2/experiment-8/src`; upstream artifacts are its
siblings under `round-1/`.

```bash
git clone <repository-url> repo
cd repo/round-2/experiment-8/src
```

## 2. System, Python and libraries

What was used for the reported run:

| item | value |
|---|---|
| OS | Debian GNU/Linux 12 (bookworm) container, Linux kernel 6.8 (any recent Ubuntu works the same way) |
| GPU | 1 x NVIDIA GeForce RTX 4090, 24 GB VRAM (driver 595.91, CUDA 13.2 driver; torch wheels are cu128) |
| CPU / RAM | 11 CPU cores and 57 GB RAM (container limits) |
| Python | 3.12 (uv-managed) for the project; a stdlib-only CPython 3.12 (`python3.12` on PATH) runs candidate programs in the sandbox harness |
| package manager | uv 0.6.14 (the venv has no pip) |
| C compiler | none was present; this is why vLLM could not start (see section 4) |

Install the exact versions used (all 172 are pinned in `pyproject.toml`; the same list is in `requirements.lock.txt`):

```bash
# system: an NVIDIA driver with CUDA >= 12.8 support, plus python3.12 on PATH for the sandbox harness
curl -LsSf https://astral.sh/uv/install.sh | sh          # if uv is missing
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r requirements.lock.txt   # identical pins to pyproject.toml
```

Key versions: torch 2.8.0, transformers 4.57.6, accelerate 1.15.0, numpy 2.2.6, scipy 1.18.1, pandas 3.0.6,
scikit-learn 1.9.1, matplotlib 3.11.2, loguru 0.7.3, openai 3.35.1, vllm 0.11.0. vllm is installed but was not used.
For the record, the run built the venv from iteration 1's pinned list plus `scikit-learn`, then added `accelerate`
when HF loading needed it; the freeze above is the final state.

`./restore.sh` rebuilds `.venv/` and the deleted C5 residual cache (`work/c5_hR.npz`).

## 3. Model, upstream data and keys

- **Model**: `Qwen/Qwen3-8B` at Hub revision `b968826d9c46dd6066d109eabc6255188de91218` (bf16, ~16.4 GB), downloaded
  automatically on first use into the Hugging Face cache (`HF_HOME` / `HF_HUB_CACHE`). Set `BRT_MODEL_PATH` to use a
  local copy of that snapshot instead. Thinking mode is off (`enable_thinking=False`) everywhere.
- **Upstream artifacts**: these are needed only to re-run S0's snapshot. Everything used from them is already copied
  into `inputs/` (with `inputs/iter1/MANIFEST.sha256`) and published with this folder. Each is read through one
  environment variable whose default is the sibling folder in the published layout:

  | artifact id | role | env var (default) |
  |---|---|---|
  | art_j3Rm_lr2nzR6 | dataset; `concreteness_norms` -> the 718 neutral-noun candidates | `BRT_DATASET_DIR` (`../../../round-1/dataset-1/src`) |
  | art__skdlFp_o3e9 | iteration-1 exp1: canonical task suite, hidden tests, labeller, gold set | `BRT_EXP1_DIR` (`../../../round-1/experiment-1/src`) |
  | art_D6Z0Snf09sFL | iteration-1 exp2 (C5 wordings, h_R cross-check cache) | `BRT_EXP2_DIR` |
  | art_1yV2vQ0EH4OY | iteration-1 exp3 (C5 wordings) | `BRT_EXP3_DIR` |
  | art_U5UKkFrOgSsE | iteration-1 exp4 (C5 wordings, decommitment axis, h_R cache) | `BRT_EXP4_DIR` |
  | art_HF8nK8B_Lqyy | iteration-1 exp5 (C5 wordings) | `BRT_EXP5_DIR` |

  `BRT_UPSTREAM_ROOT` (default `../../../round-1`) moves all six at once.
- **Keys** (names only): `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY`. They are used only by the canonical blind
  judge when the runtime and AST labels disagree. Judgments are cached by code hash in `suite/labeller/judge_cache.jsonl`
  (exp1's cache plus this run's additions), so a re-run reuses them. This run spent USD 0.32 (cap USD 0.5).
- **Optional**: `SANDBOX_PYTHON` names the stdlib CPython 3.12 used for candidate programs.
- **User uploads**: the run's private upload folder was empty; nothing private was used, and a reader needs nothing extra.

## 4. Commands, in the order they were run

All randomness is seeded through sha256-derived seeds (`cfg.stable_seed`):

- S2 sampling: one PCG64 stream per (`frlp`, task, algorithm, prompt kind, prompt index, sample index).
- S4 behaviour: one PCG64 stream per (`beh`, task, template, sample) shared by every arm (common random numbers).
- Bootstraps in `analysis.py`: `RNG_SEED = 20261020` plus fixed offsets.
- C5 random directions: seed 11. Natural-proposal bootstrap: seed 99. Audits: seed 2026.

| # | command | what it does | runtime (RTX 4090) |
|---|---|---|---|
| 1 | `.venv/bin/python method.py s0` | snapshot upstream files -> `inputs/`, build `suite/`, labeller re-check (0.965 vs gold, 22/22 refs) | 0.8 min (CPU) |
| 2 | `.venv/bin/python method.py s1` | frozen prompts, length-matched neutral twins -> `prompts/frozen_prompts.json` | 1.6 min (CPU) |
| 3 | `.venv/bin/python method.py s2` | 323 forced programs (HF sampler), labelling, name scrub | 22 min (GPU) |
| 4 | `.venv/bin/python method.py prereg` | sha256-commit of decision rules, prompts and `analysis.py` -> `results/prereg_commit.txt` | seconds |
| 5 | `./run_gpu_chain.sh` | `tests` (U0-U9 gate) -> `s4` behaviour -> `s5` FRLP scoring (with `s4label` in parallel) -> `s6` lens -> `s7` C5 -> `s8` analysis | 2.8 + 14.9 + 14.5 (+1.8) + 4.7 + 3.1 + 1.3 min |
| 6 | `.venv/bin/python natural_frlp.py` | supplementary natural-proposal readout -> `results/natural_frlp.json` | ~4 min (GPU) |
| 7 | `.venv/bin/python extra_k0_behaviour.py` | supplementary K0 behaviour arm (100 samples per task) + relabelling of all samples | ~4 min (GPU) |
| 8 | `.venv/bin/python method.py s8` | analysis re-run on the final sample file (identical numbers) | 1.2 min |
| 9 | `.venv/bin/python supplementary.py` | descriptive additions -> `results/supplementary.json` | ~1 min |
| 10 | `.venv/bin/python method.py s9` | `method_out.json` + `figures/` | 0.3 min |
| 11 | `.venv/bin/python audit/rederive.py` | independent re-derivation from the raw npz -> `results/rederive.json` (49 checks, 0 mismatches) | ~1 min |
| 12 | `.venv/bin/python audit/headline_audit.py` | independent re-derivation of every quoted number + placebo/shuffle tests -> `results/headline_audit.json` | ~4 min |
| 13 | `aii_json_format_mini_preview.py --input method_out.json` (aii-json skill) | `full_` / `mini_` / `preview_method_out.json` | seconds |

Total GPU time was about 70 minutes.

What happened on the way, as actually run:

- The first `s2` attempt used vLLM 0.11, which failed to start: torch-inductor needs a C compiler and none was
  installed. The pre-registered fallback F2 then generated the programs with the HF engine's inverse-CDF sampler,
  which is what `gen_programs.py` now does.
- `accelerate` was added after the first HF load asked for it.
- The first `tests` run stopped on an out-of-memory in the U5 marginal check. It also showed that bf16 kernel choice
  depends on batch shape. Before any arm data existed, scoring was switched to batch 1 and sampling to unpruned,
  constant-shape batches, and the chain was re-run.
- After the commit, one bug in `analysis.py` (the ROBUST check compared dicts) was fixed without changing any rule;
  it is logged with both hashes in `results/prereg_amendments.json`.
- The model was read from a local copy of the pinned snapshot.

On the same GPU type and versions, common-random-numbers sampling is bit-reproducible at fixed batch shape (U5: 100%
identical repeats). On other GPUs, bf16 kernels may differ, so individual samples can change. Aggregate shares and
FRLP values should then agree within their intervals rather than exactly.

## 5. What a reader should get

| quantity | value | file |
|---|---|---|
| pre-registered C2 decision | DECIDED BEFORE WRITING (prompt route), ROBUST | `results/analysis.json` -> `route_frlp.pooled.branch` |
| pooled F_prompt / F_direct (FRLP) | 0.853 [0.61, 1.20] / 0.001 [-0.08, 0.12] | same, `route_frlp.pooled` |
| per task F_prompt / F_direct | T1 0.870 / 0.019; T2 0.818 / -0.038 | `route_frlp.per_task` |
| D_X(a) full-ban FRLP drop | T1 -12.25 nats; T2 -5.78 nats | `route_frlp.per_task.*.D.a` |
| behaviour banned share a / b / c / d | T1 0.14 / 1.00 / 0.57 / 0.70; T2 0.11 / 0.99 / 0.13 / 0.95 | `behaviour.per_task` |
| K0 behaviour (supplementary) | T1 0.47; T2 0.06 | `results/supplementary.json` -> `behaviour_contrasts` |
| import-first opening share a / b / c / d | T1 0.00 / 0.99 / 0.00 / 0.85 | `supplementary.json` -> `opening_lines` |
| natural-proposal pooled F_prompt / F_direct | 0.574 / 0.156 | `results/natural_frlp.json` -> `pooled` |
| C5 combined Spearman, p (one-sided), decision | -0.411, 0.0003, PARTIAL | `results/c5.json`, `analysis.json` -> `c5` |
| decommitment axis | rho 0.052, p 0.68, NULL | same |
| audits | 0 mismatches; every placebo/shuffle test fails | `results/rederive.json`, `results/headline_audit.json` |

The figures are `figures/fig1_frlp_drop_per_arm`, `fig2_token_localisation`, `fig3_knockout_restoration`,
`fig4_lens_curves`, `fig5_c5_scatter` and `fig6_behaviour_opening_line`, each as .png and .pdf. These numbers and
figures are what the paper's route-test (C2) and compliance-at-R (C5) results cite. `README.md` gives the full
interpretation and caveats.
