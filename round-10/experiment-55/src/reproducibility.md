# Reproducing TP-G2 (iteration 10)

This file records exactly what was run, in order, on the machine that produced the results. Every path is relative to
this folder.

## 1. Get the artifact

```bash
git clone <the published repository URL>
cd <repository>/<this artifact's folder>        # the folder that holds method.py and this file
```

Prior artifacts are read through one relative constant, `DEPS_DIR`, defined in `src/v10.py` and
`scripts/setup_inputs.py`. It defaults to the parent folder (`..`), where the repository publishes every artifact as a
sibling folder named by its artifact id:

| artifact id | what is read |
|---|---|
| `art_VVA3P0ocZNA2` | iteration 9 gen_art_experiment_46: readout code, geometry/landing code, M-code sets, frozen states `cache/states/mcode_{8b,32b}.npz` |
| `art_8nXdw3_lDAll` | iteration 9 gen_art_experiment_45: tracer, probes, survivors, manual reads, retrace rows |
| `art_R-HSmXq2t97f` | iteration 8 gen_art_experiment_44: C6 baseline / ban / confirm rows |
| `art_IVZc3TWCeE9f` | iteration 2 gen_art_experiment_9: references and labeller (cross-check) |
| `art_D6Z0Snf09sFL` | iteration 1 gen_art_experiment_2: 41-case suite (cross-check) |
| `art_j3Rm_lr2nzR6` | declared dependency: `full_data_out.json` (IDF corpus for S5) |

Use `TPG_DEPS_DIR=<folder>` to point at another parent, or `TPG_DEP_<id>` to point at one artifact (with `-` written
as `_`, e.g. `TPG_DEP_art_R_HSmXq2t97f`).

- `scripts/setup_inputs.py` copied the small inputs into `inputs/`, `src/` and `vendor/`, so those copies ship here
  with sha256 in `inputs_manifest.json`.
- The 0.6 GB frozen state caches of `art_VVA3P0ocZNA2` and the dependency's `full_data_out.json` were read in place.
  Their sha256 is in `inputs_manifest.json` under `in_place`.
- No user-uploaded file was used. The run's `user_uploads` folder is private and is not published.

## 2. System, Python and packages

- OS: Debian GNU/Linux 12 (bookworm) container on Linux 6.8. Any recent Ubuntu works.
- Python 3.12.14 at `/usr/local/bin/python3.12`. The vendored hidden-test and tracer sandboxes run candidate programs
  with a stdlib-only CPython 3.12 (`-I -S`). They use `/usr/local/bin/python3.12` or `/usr/bin/python3.12` if present,
  else `python3.12` on PATH. `SANDBOX_PYTHON=<interpreter>` overrides this for `vendor/exp9/tasks/harness.py`.
- uv (any recent version) creates the venv:

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r requirements.lock.txt      # 70 exact pins, identical to pyproject.toml
```

Key pins (all in `pyproject.toml` / `requirements.lock.txt`):

| package | version |
|---|---|
| torch | 2.8.0 (cu128 wheel) |
| transformers | 4.57.6 |
| accelerate | 1.15.0 |
| bitsandbytes | 0.50.2 |
| numpy | 2.2.6 |
| scipy | 1.18.1 |
| scikit-learn | 1.9.1 |
| matplotlib | 3.11.2 |
| aiohttp | 3.14.5 |
| loguru | 0.7.3 |
| huggingface-hub | 0.36.2 |

## 3. Downloads, environment variables, keys

Environment variables (names only):

| variable | purpose |
|---|---|
| `OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY` | generation (`src/gen.py`); only needed to regenerate programs |
| `HF_HOME` / `HF_HUB_CACHE` | where the model shards go (optional) |
| `HF_TOKEN` | optional |
| `TPG_DEPS_DIR` / `TPG_DEP_<id>` | prior artifacts (section 1) |
| `AII_DATA_FIG_GEN_SCRIPTS` | optional: folder of the aii-data-fig-gen `chart_style.py` for the house style; without it the figures use plain matplotlib |

Models (pinned revisions):

```bash
.venv/bin/python scripts/download_full.py
# Qwen/Qwen3-8B@b968826d9c46dd6066d109eabc6255188de91218 (bf16; blocks 0-26 are used)
# unsloth/Qwen3-32B-bnb-4bit@7f721e74a6a8cc9ee352f7e49303a2c1705f9083 (NF4; blocks 0-39 are used)
```

## 4. What was run, in order

The hardware was an NVIDIA RTX 2000 Ada Generation (16 GB VRAM), 6 CPUs (cgroup quota) and 28 GB RAM (cgroup limit).
Set `OMP_NUM_THREADS=1` (`src/analysis.py`, `src/outputs.py` and `src/figures.py` set it themselves): multithreaded
BLAS on a 6-CPU box made the first G1 attempt about 40x slower.

| # | command | what it does | wall time |
|---|---|---|---|
| 1 | `python3 scripts/setup_inputs.py` | copy inputs, sha256, 25 cross-checks (all equal) | 1 min |
| 2 | `.venv/bin/python src/gen.py smoke` | 2 OpenRouter calls: thinking off (1 reasoning token), provider DeepInfra, usage.cost present | 1 min |
| 3 | `.venv/bin/python src/gen.py pilot` | 72-call feasibility pilot, tagged `pilot` and excluded everywhere | 3 min |
| 4 | `.venv/bin/python tests/test_verifiers.py` | T5 verifier unit tests: 34/34 (`results/verifier_unit_tests.json`) | 2 min |
| 5 | COMMIT1a | `predictions/commit1.json` written and chained with `v10.commit(...)` from a Python one-liner; payloads + `commitments.log` ship here | — |
| 6 | `.venv/bin/python src/gen.py main --deadline-min 75` | wave A (12 per cell, 20 per top-up class) and wave B (to 12 verified, caps 48/100) with one repair turn | about 30 min |
| 7 | `.venv/bin/python src/r0.py` | R0 gate: unit-weight Dijkstra g/median 0.6296 (8B) and 0.6725 (32B), 113/113 placements, 15/15 EDGE (`results/r0_reproduction.json`) | 1 min |
| 8 | `.venv/bin/python src/assemble.py`, then COMMIT1b (`predictions/commit1b.json`) | 351 placed programs (`data/placed_programs.jsonl`) | 1 min |
| 9 | `.venv/bin/python src/extract.py 8b repro placed refs` | hook check 0.0; reproduction min cosine 0.99981 | 3 min |
| 10 | `.venv/bin/python src/extract.py 32b repro placed refs` | min cosine 0.99990 | 8 min |
| 11 | hand reads with `scripts/hand_sheet.py <cell>` and `scripts/hand_record.py '<uid>\|ACCEPT\|<reason>'` | 139 rows in `data/hand_reads_v10.jsonl` | about 25 min |
| 12 | `.venv/bin/python src/gen.py paraphrase --deadline-min 25` | top-up fallback: JPS 12/12 and BiA* 6/12 are paraphrases | 2 min |
| 13 | COMMIT1c (`predictions/commit1c.json`), then `.venv/bin/python src/freeze.py factorial` | 287 programs, context variant i mod 5, reliability copy (i+1) mod 5 | 1 min |
| 14 | `scripts/run_states.sh` | 8B factorial + ctx2 (0.42 s/program), RANDNET (seed 0), 32B factorial (2.9 s/program) | 20 min |
| 15 | `.venv/bin/python scripts/order_matrix.py` | measured expansion-order matrix (S7) | 15 min |
| 16 | `.venv/bin/python src/freeze.py topups`, then `scripts/run_states_topups.sh` | 48 top-ups, 32B and 8B states | 8 min |
| 17 | `.venv/bin/python tests/test_analysis.py` | T7 synthetic G1 checks (null rejection 3.5%) and T8 placement checks: pass | 10 min |
| 18 | `.venv/bin/python src/analysis.py g1 8b` and `g1 32b` (run in parallel) | G1 with all sensitivities | 1 min each |
| 19 | `.venv/bin/python src/analysis.py g2 8b` and `g2 32b` | G2 with frame LOO | about 3 min each |
| 20 | `.venv/bin/python src/analysis.py robust 8b 32b` | 12-cell robustness grid | about 35 min |
| 21 | `.venv/bin/python src/outputs.py` | placebos, G1 verdict, verification summary, hardware, `method_out.json` | 6 min |
| 22 | `.venv/bin/python src/figures.py` | F1–F8 (PDF + PNG) | 3 min |
| 23 | `python3 -I audit/rederive.py` and `python3 -I audit/rederive_g2.py` | stdlib re-derivations: 0 mismatches; placebos fail as required | 1 min |
| 24 | aii-json `aii_json_format_mini_preview.py --input method_out.json` and the `exp_gen_sol_out` validation | full / mini / preview; all pass | 1 min |

Steps 18–24 can be rerun from the shipped `data/` and `cache/states_v10/` with
`.venv/bin/python method.py all-analysis`. `method.py` lists every stage. `cache/states_v10/` stays on the run volume
(its files are ≥ 100 MB); rebuild it with steps 9, 10, 14 and 16.

### Seeds and determinism

- **Generation** uses `seed = int(sha256(f"{cell}|{slot}|{wave}")[:8], 16)`, T 1.0 and top_p 1.0. OpenRouter does not
  guarantee bitwise determinism, so regenerating will not reproduce the same programs. The frozen programs are in
  `data/programs_v10.jsonl` and `data/factorial_set.jsonl`; analyses run on them.
- **States are deterministic** given the programs, up to GPU bf16 numerics: the cosine against iteration 9's RTX 5090
  states is 0.9998–0.99999.
- **Statistics** use fixed seeds:
  - G1 bootstrap seed 0; permutations seeds 1 and 2; cell-cluster bootstrap seed 3; sensitivities seed 7; crossed
    core seed 11;
  - S2 bootstrap seed 5;
  - G2 family bootstrap `hash(family) % 1000`. Python's string hash is salted per process, so these CIs can vary
    slightly between runs; the point estimates do not;
  - placebos seed 13; family-shuffle placebo seed 3.
- **Costs:** OpenRouter spend was USD 0.251 for 1,138 calls (`results/costs_v10.json`).

## 5. What you should get

| file | number |
|---|---|
| `results/g1_8b.json` | primary ρ_dc 0.226 [0.186, 0.265], ρ_cd 0.300 [0.251, 0.351], δ −0.074 [−0.133, −0.018]; crossed core ρ_dc 0.280; E0 0.169; RANDNET 0.072; noise ceiling 0.944 |
| `results/g1_32b.json` | ρ_dc 0.285 [0.252, 0.321], ρ_cd 0.414 [0.363, 0.462], δ −0.129 [−0.193, −0.060]; crossed core ρ_dc 0.336, ρ_cd 0.545 |
| `results/g1_verdict.json` | INDETERMINATE on both models |
| `results/g2_8b.json` / `g2_32b.json` | class LOO 0.68 / 0.83; P-COV banned-nearest 0.993 / 0.978; F-BF nearest RELAX 30/32 / 31/32; F-BF r_F 0.86 (EDGE) / 1.03 (OPPOSITE, robust); F-UD r_F 0.90 / 0.98 |
| `results/robustness.json` | P-COV 12/12 cells; P-BF 8/12; P-UD full-frame EDGE 12/12 with the full rule met in 6/12 |
| `results/rederive.json` | 0 mismatches against G1 and r_F |
| `results/rederive_g2.json` | independent shares; the 8B P-UD contrast is non-specific (placebo median 1.0) |
| `figures/F1`–`F8` | the paper's geometry, bar, violin, layer and heatmap figures |

The README's Results section is the paper-facing summary. `results/deviations.json` lists every departure from the
plan.
