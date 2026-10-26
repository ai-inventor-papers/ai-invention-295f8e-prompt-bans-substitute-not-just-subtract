# Reproducing the round-one audit

This file describes what was actually run to produce `eval_out.json`. The run made no generations, no LLM calls and no
paid API calls. All paths below are relative to this folder.

## 1. Get the artifact

This folder is published as one folder of a public GitHub repository:

```bash
git clone <repository-url>
cd <repository>/<this-folder>          # the folder that holds this file, eval.py and README.md
```

## 2. System, Python and libraries

What the run used:

| Item | Version or setting |
|---|---|
| OS | Linux 6.8 (Debian 12 container). Any recent Ubuntu works. |
| System packages | `git`, a C toolchain is not needed (all wheels) |
| Python | 3.12.14 (`requires-python = "==3.12.*"`) |
| Environment manager | `uv` 0.6.14. pip was never used. |
| GPU (locus stage only) | NVIDIA GeForce RTX 4090, 24 GB VRAM, driver 595.91.07 |
| CPU and RAM | 7-CPU cgroup quota, 42 GB RAM limit |

Without a GPU the locus solver runs on CPU in float64. That is correct but much slower.

Every package is pinned to the exact installed version in both `pyproject.toml` and `requirements.txt`. These are the
same 71 pins, produced by `uv pip freeze`. Key pins:
- `torch==2.14.1` (PyPI wheel with CUDA 13 runtime packages)
- `numpy==2.5.4`, `scipy==1.18.1`, `pandas==3.0.6`, `scikit-learn==1.9.1`
- `networkx==3.7`, `statsmodels==0.15.0`, `matplotlib==3.11.2`
- `tokenizers==0.23.3`, `loguru==0.7.3`, `joblib==1.6.0`

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh        # if uv is missing
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -c "import torch, sklearn; print(torch.__version__, torch.cuda.is_available(), sklearn.__version__)"
```

## 3. Inputs, downloads and environment variables

**Iteration-1 artifacts (required, read-only).** The run reads the six iteration-1 experiment artifacts through ONE
environment variable, `ITER1_ROOT`. It must name a directory that contains these folders:

| Folder | Artifact id | Role |
|---|---|---|
| `gen_art_experiment_1` | art__skdlFp_o3e9 | association |
| `gen_art_experiment_2` | art_D6Z0Snf09sFL | geometry |
| `gen_art_experiment_3` | art_1yV2vQ0EH4OY | forking token |
| `gen_art_experiment_4` | art_U5UKkFrOgSsE | decommitment |
| `gen_art_experiment_5` | art_HF8nK8B_Lqyy | instruction tuning |
| `gen_art_experiment_6` | art_UoCVh2Qe5RZ0 | decoding |

The repository publishes these artifacts as sibling folders. If their published folder names differ, symlink them to the
names above inside one directory:

```bash
export ITER1_ROOT=../path/to/the/directory/with/the/six/folders
```

When `ITER1_ROOT` is unset, `common.py` falls back to the run-volume layout relative to `common.py`
(`Path(__file__).parents[4]/run_4VFKidE1bxPG/3_invention_loop/iter_1/gen_art`). That layout exists only on the original
server.

The 98 files actually read, with sha256 hashes, are listed in `inventory.json`. The largest inputs are:
- `exp3/states/T{1,2}_part_00{1..5}.npz`: 10 × 82.6 MB, the saved residual states;
- `exp2/cache/hR_layer{8..28}.npy`: 21 × 10.9 MB.

exp2's README notes that its layers 8-20 were kept on its run volume only. If they are absent, the only part affected is
the 0a cosine check at layers below 21. The code records those cells as `input_missing` and does not fail.

**Qwen3-8B tokenizer (optional, decoding only).** Set the environment variable `QWEN3_TOKENIZER_JSON` to a
`tokenizer.json`. The model is public, so you can fetch it with `huggingface-cli download Qwen/Qwen3-8B tokenizer.json`.
The tokenizer is used only to decode the top prefixes in the text-locus section. Without it those strings are omitted
and every number is unchanged.

**Chart generator (optional).** `figures.py` calls the `aii-data-fig-gen` chart generator (`chart_gen.py`) of the AI
Inventor skills tree. Set the environment variable `CHART_GEN` to its path. Without it the JSON-spec figures are logged as
failed, while the geometry heatmap (plain matplotlib) still renders. All numbers are unaffected.

**Other inputs.**
- **API keys:** none. No OpenRouter or other API call is made.
- **User uploads:** none were provided; the uploads folder was empty, so nothing private is needed.
- **Positioning (0h):** this was a dated web check (2026-10-20) of public arXiv abstract pages and one GitHub README. Its raw fetch logs are in `logs/web/`, and `results/positioning.json` is the hand-written record. Re-fetching the same URLs repeats the check, but pages can change.

## 4. Commands actually run, in order

Every random seed is fixed in code:

| What | Seed |
|---|---|
| Locus permutation vectors | `1000 + position` (global), `2000 + position` (within-paraphrase) |
| Locus cluster bootstraps | `seed = layer index` |
| Geometry subsamples | `100 + layer` (forced), `500` (masked) |
| tables RNG | `20261020` |
| Audit seeds | written in `audit.py` and `audit_extra.py` |

Repeated runs reproduced every number exactly. The full `eval.py --rerun` gave identical outputs.

```bash
# 0a smoke test + solver unit test (5 random cells per task vs sklearn lbfgs: identical predictions, rel. coef diff <= 3.9e-5)
.venv/bin/python locus.py --smoke            # one cell, 401 label vectors: 0.94 s on the RTX 4090
.venv/bin/python locus.py --unit-test-only
# 0a full locus probe: 903 cells, 200 + 200 refit nulls on W, 50 on P1/P2      (~7.5 min, RTX 4090)
.venv/bin/python locus.py
# 0b geometry: reproduce exp2, then k x layer x 1000 paraphrase subsamples    (~5.5 min, 6 CPU workers)
.venv/bin/python geometry.py
# G2 inventory of all inputs (sha256)                                          (~1 min)
.venv/bin/python inventory.py
# G3 + 0c-0g: harmonisation, perturbation table, corrections, knob table, PREDICT, BUY, seeds, missing outputs, sham bans (~20 s)
OMP_NUM_THREADS=4 .venv/bin/python tables.py
# figures (PDF + PNG)                                                          (~40 s)
.venv/bin/python figures.py
# independent audits with placebos                                             (~30 s + ~40 s)
.venv/bin/python audit.py
.venv/bin/python audit_extra.py
# assemble eval_out.json + corrections.json (runs any missing stage; --rerun reruns all, ~16 min end to end)
.venv/bin/python eval.py
# full / mini / preview variants and schema validation (AI Inventor aii-json skill scripts)
python aii_json_format_mini_preview.py --input eval_out.json
python aii_json_validate_schema.py --format exp_eval_sol_out --file eval_out.json
```

The last two commands come from the AI Inventor `aii-json` skill and are not part of this repository. The files they
produced (`full_eval_out.json`, `mini_eval_out.json`, `preview_eval_out.json`) are committed.

`OMP_NUM_THREADS` was set because the container had a 7-CPU quota. Without it, BLAS threads oversubscribe the CPUs.

## 5. What you should get

Outputs:
- `eval_out.json`, valid against `exp_eval_sol_out`, with its `full_` / `mini_` / `preview_` variants: 80 metrics in `metrics_agg` and 1,391 examples in 4 datasets.
- `corrections.json`.
- `tables/locus_cells.csv` (903 rows), `tables/geometry_stability.csv` (56), `tables/perturbation_table.csv` (249), `tables/knob_table.csv` (183).
- `figures/*.pdf|png`.

The report's audit section draws these headline values from `eval_out.json#metrics_agg` and the named metadata sections.

### Locus (`metadata.locus`; figures `fig_locus_curves_T*`, `fig_locus_nulls`, `fig_text_locus`)

- **T1:** mechanical verdict R (`locus_T1_verdict_mechanical_is_R` = 1). R reads the within-ban outcome at BA 0.855 (layer 16). The within-paraphrase null absorbs every generated position.
- **T2:** mechanical locus k_pre, qualified POST-COMMIT READOUT (`locus_T2_verdict_code` = 1).
  - BA 0.7625 at layer 8, +0.281 over R.
  - Text control BA 0.756.
  - The text first separates the classes at k = 4 (`text_locus_T2_first_k_ge_0p6` = 4), and BA_text ≥ 0.8 first at k = 8.
- **DiM AUC:** 0.882 (T1) and 0.749 (T2) at k_pre, both below the 0.9 bar.
- **R-compliance Spearman:** 0.63 (T1) and 0.65 (T2).

### Geometry (`metadata.geometry_robustness`; figure `fig_geometry_heatmap`)

- Reproduction of exp2: max |diff| 0.
- `geo_T2_P_FW_nearest_L24_k10` = 1.0 and `geo_T2_P_BF_nearest_L24_k10` = 0.0.
- `geo_T1_P_DFS_nearest_L27_k10` = 1.0, but 0.52 at layer 24.

### Corrections (`metadata.corrections`, `metadata.knob_table`, `metadata.predict_gated`, `metadata.buy`)

- T2 substitutes: BF_SPFA 272/272.
- T1 substitutes: DFS 116/128 = 0.906.
- Cumulative BFS+DFS ban: non-replicating.
- Knob positive target met by no diversity knob or ban on either task.
- `n_gated_events` = 3 (12 under the literal gate).
- No PREDICT family and no BUY knob advances.

### Seeds, sham bans and positioning

- **Seeds** (`metadata.seeds`): T2 semantic seed +66.3 points toward BF_SPFA among correct programs at cosine −0.087; T1 shows +2.15 points at cosine 0.493.
- **Sham bans** (`metadata.sham_promotion`): 2 promotions, both content neighbour and runner-up.
- **Positioning:** `metadata.positioning`.

### Checks and audits

- Recompute-then-compare: 38/40 checks match, and both mismatches are explained.
- `audit.py`: 20/20 independent re-derivations match, and 3 placebos fail.
- `audit_extra.py`: 5/5 match, with the T2 k_pre within-paraphrase p = 0.024 over 40 refits against a placebo p of 0.17. 3 placebos fail.
