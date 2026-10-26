# Reproducibility: mapping the ten grid algorithms with and without their names (TP-G, iteration 9)

This file describes what was **actually run**, in order, on the machine that produced the results. Every path is
relative to this artifact's folder.

## 1. Getting the artifact

This workspace is published as one folder of the run's public GitHub repository:

```bash
git clone <repository-url>
cd <repository>/<this-artifact-folder>          # the folder that contains method.py and this file
```

The folder contains everything the analysis reads except the activation-state files (`cache/states/`, about 0.5 GB),
which stay on the run's storage volume and are excluded from the repository; they are rebuilt by the `mname`,
`states` and `analyse` stages (section 4). The run's `user_uploads` folder was empty; no user-uploaded input is used.

Prior artifacts are read **only** by Stage -1 (`method.py inputs`), which copies them into `inputs/` and `vendor/`
with `inputs/SHA256SUMS`. Their locations are environment variables with sibling-folder defaults in `src/tpg.py`:
`TPG_E44` (art_R-HSmXq2t97f, iteration 8), `TPG_EXP9` (art_IVZc3TWCeE9f, iteration 2: forced programs, harness,
references), `TPG_EXP2` (art_D6Z0Snf09sFL: 41-case suite), `TPG_EXP8` (art_8_ULPE8jJQc_: twin frames) and
`TPG_DSET` (art_j3Rm_lr2nzR6, the declared dependency: 718 neutral nouns). Every later stage reads `inputs/` and
`vendor/` only, so a clone can rerun every stage after Stage -1 without the prior artifacts.

## 2. System, Python and libraries

| Item | What was used |
|---|---|
| OS | Debian GNU/Linux 12 container on Linux 6.8 (Ubuntu 22.04/24.04 works the same way) |
| GPU | 1x NVIDIA GeForce RTX 5090, 32 GB VRAM (driver 595.91.07, CUDA 12.8 wheels) |
| CPU / RAM | 14 vCPU (cgroup quota, AMD Ryzen 9 9950X), 85 GB RAM (cgroup limit) |
| Python | CPython 3.12.14; the sandboxes run candidates with `/usr/local/bin/python3.12 -I -S` (override: `SANDBOX_PYTHON`) |
| Package manager | uv (the venv has no pip) |
| Libraries | 70 packages pinned in `pyproject.toml` and `requirements.lock.txt` (identical lists): torch 2.8.0, transformers 4.57.6, bitsandbytes 0.50.2, accelerate 1.15.0, scikit-learn 1.9.1, scipy 1.18.1, numpy 2.2.6, networkx 3.7, matplotlib 3.11.2, aiohttp 3.14.5, loguru 0.7.3 - the same versions as iteration 8 for every shared package (`predictions/hardware.json -> matches_e44_pins`) |

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r requirements.lock.txt
```

## 3. Downloads, environment variables and keys (names only)

Model weights (Hugging Face Hub, pinned revisions; `scripts/download_models.py` downloads both into the HF cache):

| Repo | Revision | Used for |
|---|---|---|
| `unsloth/Qwen3-32B-bnb-4bit` | `7f721e74a6a8cc9ee352f7e49303a2c1705f9083` | all Qwen3-32B states (nf4, decoder truncated to 48 of 64 blocks; exact for blocks 0-47) |
| `Qwen/Qwen3-8B` | `b968826d9c46dd6066d109eabc6255188de91218` | Qwen3-8B states (bf16, truncated to 29 of 36 blocks) |

OpenRouter (only `qwen/qwen3-32b`, provider pinned to DeepInfra fp8 with `allow_fallbacks: false`, thinking off via
`reasoning.enabled=false` plus the ` /no_think` soft switch, T 1.0, top_p 1.0):

| Variable | Needed for |
|---|---|
| `OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY` | naming gate and top-ups (stages `naming`, `topups`) |
| `HF_HOME` / `HF_HUB_CACHE` | optional: where the weights are cached |
| `TPG_E44`, `TPG_EXP9`, `TPG_EXP2`, `TPG_EXP8`, `TPG_DSET` | only for Stage -1 (re-copying `inputs/`) |
| `TPG_OR_CAP` | optional: artifact OpenRouter cap in USD (default 0.40) |
| `TPG_WORKERS` | optional: process-pool size for the analysis (default 12) |

## 4. Commands in the order they were run

Each stage is `.venv/bin/python method.py <stage> [args]`. Seeds: probe grids and set selection 9009; bootstrap
seeds 0..999 per k; landing nulls seed 0 (iteration 8's code). Approximate wall times on the hardware above.

| # | Command | Time | Notes |
|---|---|---|---|
| 0 | `.venv/bin/python scripts/download_models.py` | 1 min | weights into the shared HF cache |
| 1 | `method.py inputs` | 2 min | inputs + `inputs/SHA256SUMS` + `predictions/hardware.json` |
| 2 | `method.py commit0` | <1 min | COMMIT0 |
| 3 | `method.py mname 32b` | 11 min | 300 forced prompts, hook check, sdpa-vs-eager check, reproduction (`results/repro_mname_32b.json`) |
| 4 | `method.py cpu` | 4 min | probe grids, tracer, behavioural RDM, lexical, descriptions, M-lex twins, contexts; COMMIT1a |
| 5 | `method.py states 32b mlex ban` | 5 min | first attempt failed on a duplicated npz key (fixed, re-run) |
| 6 | `method.py naming` | 9 min | 840 calls, USD 0.008 |
| 7 | `method.py topups` | 34 min | 600 calls (2 waves of 30 per algorithm), USD 0.085 |
| 8 | `method.py pools` | 29 min | first run: COMMIT1b |
| 9 | `method.py states 8b mname mlex ban` | 4 min | + Qwen3-8B reproduction (`results/repro_mname_8b.json`) |
| 10 | `method.py states 32b mdesc mcode` | 2 min | M-desc extracted; M-code stopped on a too-strict code-span check (no M-code state written) |
| 11 | `method.py pools COMMIT1b-r1` | 21 min | G-scrub fix before any M-code state (deviation D-gscrub-fix); COMMIT1b-r1 |
| 12 | `method.py states 8b mdesc` | 5 min | |
| 13 | `./run_chain.sh 0` | see `logs/chain.out` | `states 32b mcode`, `states 8b mcode`, `blocks` (COMMIT2), `analyse`, `figures`, `outputs`, `audit/rederive.py` |
| 14 | `.venv/bin/python audit/audit_states.py` | 3 min | state-level audit |
| 15 | aii-json format script on `method_out.json`; `scripts/make_readme.py` | <1 min | full/mini/preview variants, README |

The hash chain is in `commitments.log` (COMMIT0, COMMIT1a, COMMIT1b, COMMIT1b-r1, COMMIT2); `common.verify_chain()`
checks it and `method_out.json -> metadata.commitments` records the result.

## 5. What a reader should get

| Output | Where |
|---|---|
| Named outcome, P1-P8 pass/fail, secondary statistics | `results/n4_verdict.json` |
| Per-manifold geometry (PCA EVR, MDS stress-1, Isomap components, g, classes, landing nulls, bootstrap, robustness grid, crossnobis, z-scored) | `results/geometry_<model>_<manifold>.json`, `results/geometry_all.json` |
| Reproduction of iteration 8 | `results/repro_mname_32b.json`, `results/repro_mname_8b.json` |
| Lexical regression (alias level) | `results/lexical_regression.json` |
| RSA with exact Mantel p, noise ceilings, name evocation | `results/rsa.json` |
| Per-program placement | `results/placement.json`, `data/placements.jsonl` |
| Behavioural RDM, G-tracer | `results/behavioural_distance.json`, `results/g_tracer.json` |
| Naming gate, acceptance, scrub gate | `results/naming_gate.json`, `results/acceptance.json`, `results/g_scrub.json` |
| Figures (activation coordinates) | `figures/pca_*`, `figures/mds_*`, `figures/isomap_*`, `figures/class_table.*`, `figures/rdms.*`, `figures/behavioural_mds.*`, `figures/lexical_alias_level_32b.*` |
| Independent re-derivations | `results/rederive.json`, `results/audit_states.json` |
| Pipeline output | `method_out.json` (+ `full_`/`mini_`/`preview_` variants) |

The README's headline section is generated from these files by `scripts/make_readme.py`; every number in it can be
traced to one of them.
