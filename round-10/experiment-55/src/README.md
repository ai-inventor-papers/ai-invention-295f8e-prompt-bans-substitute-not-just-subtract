# TP-G2: does the LLM's map of path-search programs follow mechanism or code surface?

Iteration 10 of the AI Inventor "LLM creativity" run (plan `gen_plan_experiment_5_idx5`, claims G1 and G2). Earlier
iterations built a map of how Qwen3 represents grid path-search programs. On that map, the programs a model writes when
the five favourite algorithms are banned ("survivors") land next to the banned ones. But the map also tracked code
surface and length about as strongly as behaviour ("behaviour given surface 0.11 / 0.32 / 0.47" in iteration 9).

This artifact separates the two factors by construction. It builds a **factorial set of verified, name-scrubbed
programs** that crosses two things:

- the measured **expansion discipline**: level order (LEV), depth-first (DFS), goal heuristic (HEU), relaxation
  (RLX), random (RND), coordinate key (CRD);
- the **frontier container**: deque (DEQ), stack or recursion (STK), heap (HEAP), 2-D arrays (ARR), set (SET),
  sorted list (SLIST).

Each program is read with iteration 9's frozen readout: R1, the mean block output over the code tokens, at Qwen3-8B
bf16 block 17 and Qwen3-32B NF4 block 33. On that readout the artifact asks two questions:

- **G1:** is the cell geometry organised by discipline once container is held fixed?
- **G2:** where do the survivor families, the covert BFS/DFS programs and a textbook-relaxation surface probe land when
  each is placed alone on the frozen graph?

## Headline results

All numbers come from `results/verdicts.json`, `results/g1_*.json`, `results/g2_*.json` and `results/t5_placement.json`.

| | Qwen3-8B (block 17) | Qwen3-32B (block 33) |
|---|---|---|
| rho_d = partial Spearman(cell RDM, D_disc given D_cont) | **0.104** (boot 95% CI 0.026-0.137) | **0.090** (0.038-0.142) |
| within-container permutation p (exact, 5,760 permutations) / Holm | 0.053 / 0.053 | 0.024 / 0.049 |
| rho_c = partial Spearman(cell RDM, D_cont given D_disc) | **0.462** (0.385-0.536), p = 0.002 | **0.592** (0.549-0.601), p = 0.0006 |
| P_boot(rho_d > rho_c) | 0.000 | 0.000 |
| rho_d with surface, length and dispersion controls | 0.028 (p = 0.36) | 0.044 (p = 0.17) |
| zero-order Kendall tau-a: disc / cont / AST surface / length | 0.008 / 0.19 / 0.58 / 0.52 | -0.007 / 0.25 / 0.52 / 0.49 |
| noise ceiling (split-half, Spearman-Brown) | 0.94 | 0.97 |
| rho_d of the lexical baselines (block 0 / TF-IDF / AST 4-grams) | 0.146 / 0.188 / 0.195 | 0.111 / 0.188 / 0.195 |
| selectivity rho_d(model) - rho_d(TF-IDF) | -0.083 (CI -0.144 to -0.014) | -0.098 |
| leave-one-out nearest-cell accuracy: model / TF-IDF / AST (chance 0.067) | 0.70 / 0.66 / 0.43 | 0.79 / 0.66 / 0.43 |
| G1 verdict (plan rule) | INTERMEDIATE (FRAGILE: full control gives <= 0.1) | LOW (<= 0.1) |

**G1: NOT SUPPORTED.** The cell map is highly reliable (ceiling 0.94-0.97). It is organised by container and by code
surface: AST shingles and length alone explain 0.48 / 0.34 of the rank variance uniquely, and discipline explains
about 0.00.

The discipline effect is about 0.1, below the 0.3 threshold. It carries no more discipline information than the
lexical baselines. Selectivity is negative on every baseline.

The formal DISCONFIRMED rule (rho_d <= 0.1 on both models) misses by 0.004 on 8B. All sensitivities give rho_d between
0.01 and 0.19, and none reaches 0.3: k = 10, the cross-validated centroid RDM, R1g and R2, blocks L +/- 2, excluding
reassigned or disputed programs, adding the PROBE cell, frame F1, and the program-level RDM.

Discipline is still locally decodable (leave-one-out discipline accuracy 0.74 / 0.83). It just does not shape the
between-cell distances.

**G2: NOT SUPPORTED as preregistered** (8B primary, 32B replication, k = 15 and 10). The full prediction set held for
no family. The findings below are the substance; `results/g2_*.json` has the details.

- **Within a container, survivors land at their own discipline's cell.** Unit-weight Dijkstra survivors (UD, measured
  LEV x HEAP) land at LEV_HEAP (36/36 on 8B, 34/36 on 32B). Grid Bellman-Ford survivors (BF, RLX x ARR) land at
  RLX_ARR (29-30/32). Random-priority survivors (RP) land at RND_HEAP (6/10 and 9/10).
- **Across containers, the sign points to surface, but the test is weak.** For every family, Delta < 0: programs sit
  closer to same-container / other-discipline cells than to same-discipline / other-container cells. For example,
  Delta(UD) = -6.5 on 8B and -20.7 on 32B. But:
  - no Delta is significant under the within-container permutation (p = 0.33-0.57);
  - norm-matched Gaussian states give Deltas of the same order (BF -10.5 / -16.6; UD +6.6 / -4.2;
    `audit/rederive2.json`).

  Read the Delta signs as descriptive, not as evidence on their own.
- **The PROBE cell lands with the relaxation surface.** These are FIFO label-correcting programs, measured as level
  order on unit grids. 15 of 16 land at RLX_STK, not at LEV_DEQ, on both models. That is the textbook-name / surface
  reading, not the mechanism reading.
- **Covert BFS/DFS programs land near banned algorithms.** The share whose nearest algorithm is banned is 0.87 / 0.97
  on F0 (binomial p vs the class-size base rate: 0.005 on 8B). The share whose nearest cell has a banned discipline is
  0.77 / 0.90 on F1. The F1 share is not diagnostic on 32B: norm-matched Gaussian states give 1.0 there, and 0.57 on
  8B.
- **The F0 EDGE call does not discriminate.** On F0 every placed survivor lands EDGE, BF included, and the
  family-label placebo cannot move it. On F1, BF is OPPOSITE and UD is EDGE.
- **Iteration 9's UD result reproduces exactly.** On the iteration-9 frame it is 15/15 EDGE on both models (T5).

Geometry is correlational: no intervention was run.

**Exploratory analyses (added after COMMIT1, not preregistered):**

- **Leave-one-out errors are surface errors** (`results/explore_confusion.json`). When a program's nearest cell is
  wrong:
  - the predicted cell shares its container 42/66 times on 8B and 35/47 on 32B, against about 16% by chance
    (binomial p < 1e-6);
  - it shares its discipline 8/66 and 10/47 times, against about 12-14% by chance (p = 0.59 and 0.10).
- **Graded behaviour adds nothing beyond surface** (`results/explore_dbeh.json`). This is the D_beh sensitivity that
  was dropped before COMMIT1.
  - Behavioural distance is 1 - Spearman of first-expansion ranks on 8 probe grids. It tracks discipline (Spearman with
    D_disc 0.40) and not container (0.06).
  - Cell map vs D_beh given container: 0.035 / 0.025 (within-container permutation p = 0.39 / 0.26).
  - At the program level (24,310 pairs), partial Spearman(geodesic, behaviour | AST surface, same container) is
    0.015 / 0.031. Surface given behaviour is 0.47 / 0.48. This answers iteration 9's open "behaviour given surface"
    question: about 0.
- **Bootstrap coverage addendum** (`results/t4b_bootstrap_coverage.json`). Against each synthetic dataset's own expected rho_d (same planted cell structure, 20 fresh noise draws), the within-cell bootstrap CI covers 0.92 of 50 runs (nominal 0.95). The committed T4 figure of 0.56 compared CIs with the across-dataset mean, an estimand that bootstrap cannot target.

## What was done (pipeline)

1. **Inputs and reproduction (Stage 0).**
   - Iteration 9 (E46, E45) and iteration 8 (E44) files were copied into `inputs/` with `inputs/SHA256SUMS`. The large
     iteration-9 npz files were read in place, with hashes in `inputs/LARGE_INPUTS.sha256`.
   - The frozen readout was reproduced on both models: cosine >= 0.99999 against the cached states, and g(UD)
     geodesics identical (`results/repro_gate.json`).
2. **Cells, prompts, instrument (1.1-1.3).**
   - 17 requested cells plus a PROBE cell, each with a words-only instruction in 3 frames. A forbidden-word audit found
     0 hits on 108 prompts (`predictions/cells.json`, COMMIT0a).
   - The name-blind instrument (`src/instrument.py` plus the extended tracer child `src/inst_child.py`) applies an
     ordered rule. It checks sweeps and label-correcting re-push, then RNG sensitivity, goal sensitivity, level order,
     LIFO and coordinate key. The container is read from the runtime selection operation.
   - Gate: 18/18 planted cell references and 13/15 catalogue references correct, and 2/2 mutation tests
     (`results/instrument_gate.json`, COMMIT0b).
3. **Generation (1.4).** 1,020 forced Qwen3-32B calls (DeepInfra fp8, thinking off, T = 1) in 3 rounds of 20 per cell.
   - 61% of round 0 failed the frozen suites on one edge case: start == goal on a wall.
   - Amendments COMMIT0c and COMMIT0d added an edge-case reminder. The second, placed inside the instruction, worked.
4. **Acceptance (1.5).** A program is accepted when all of the following hold:
   - both frozen suites (48 + 41 cases) pass on the raw code and on the scrubbed code;
   - the alias audit finds 0 hits;
   - the instrument's (disc, cont) equals the requested cell, or another planned cell (reassigned and logged);
   - it survives deduplication.

   The executor hand-read every RLX / RND / CRD program and every ARR-cell program, plus 3 random programs per other
   cell: 158 reads in `data/hand_reads.jsonl`, with 0.86 agreement with the instrument.
   - 19 RLX_STK programs re-push improved cells at runtime but compare `new_dist < dist[nb]`. The frozen AST
     relaxation pattern misses that, so the instrument read DFS. The hand read assigns RLX and flags them as disputed.
   - The G1 sensitivity that excludes disputed programs gives 0.096 / 0.072.

   Gated LLM judges failed their 9/10 gate (deepseek 8/10, kimi 6/10, mistral 7/10; all misread the coordinate-keyed
   order), so per plan F4 the hand reads decide.
5. **Factorial set.** 15 cells with at least 10 programs each, capped at 16 (221 programs), plus 16 PROBE programs.
   - LEV_SET (4) and RLX_HEAP (4) were dropped.
   - Most "re-push" RLX_HEAP requests came out as coordinate order with a visited set, and were reassigned to CRD_HEAP.
   - The design is connected, every discipline appears in at least 2 containers, and Spearman(D_disc, D_cont) = -0.15
     (`results/design.json`).
6. **Top-ups, survivors, covert set (1.6-1.8).**
   - Top-ups were re-adjudicated from iteration 9 and new named ones generated, all hand-read:
     - iddfs 10 (F0 total 12);
     - bibfs 7 (F0 total 15);
     - biastar 5 (F0 total 7, below the floor of 10);
     - jps 1 (below the floor).
   - F0 therefore has 3 non-banned classes (plan F7).
   - 114 survivors with hand-read families, split by measured discipline: UD-LEV 36, BF-RLX 32, CK-CRD 20, RP-RND 10,
     FL-RLX 4, RC-RND 4, MX 5, SP 3. No BF program measured LEV, so the sharp BF-LEV test is unavailable.
   - 30 covert BFS/DFS programs.
7. **COMMIT1 (Stage 2)** froze, before any new state was read:
   - frames, analysis code hashes, thresholds, predictions and placebos;
   - the T4 synthetic validation: type-I 0.055, power 0.64, bootstrap coverage 0.56 (a known limitation).
8. **States (Stage 3).** 412 programs per model, R1 / R1g / R2 at blocks [0, L-2 .. L+2], float16. The npz files are
   `cache/states/tpg2_8b.npz` (0.17 s per program) and `cache/states/tpg2_32b.npz` (0.38 s per program).
9. **Analysis (Stages 4-5).** G1 and G2 as frozen. Bootstrap B = 1,000, rebuilding the graph in every resample.
10. **Figures (Stage 6)** in actual activation coordinates (`figures/`).
11. **Independent re-derivation and placebos (Stage 7):** 0 mismatches (`audit/rederive.json`).
12. **Positioning (Stage 8)** against 7 works, with verbatim quotes (`results/positioning.json`).

OpenRouter spend was USD 0.170 over 1,230 calls, with no budget refusals (`results/costs.json`). GPU time was about
0.25 h on one RTX 4090.

## Layout

| path | content |
|---|---|
| `method.py` | entry point: `python method.py all` or `python method.py <stage>`; stages are listed in its docstring |
| `src/tpg2.py` | cell table, prompts, forbidden-word audit, frozen constants, commitment chain |
| `src/gen_or.py` | OpenRouter generation, with GET /key before each batch, cost ledger, 403 stop and rounds |
| `src/instrument.py`, `src/inst_child.py` | name-blind discipline x container instrument (child = iteration 9's tracer plus assignment values, sorted-list marking and seeded runs) |
| `src/gate_instrument.py`, `references/planted/*.py` | instrument gate and the 18 planted cell references |
| `src/accept.py` | acceptance pipeline: suites, scrub, alias audit, instrument, dedupe |
| `src/stage_sets.py`, `src/measure_primary.py` | top-ups, survivors, covert set, PRIMARY-frame measurement |
| `src/handread.py` | compact views and the hand-read ledger |
| `src/build_frames.py` | hand reads applied, design check, frames, state items |
| `src/synth_t4.py` | T4 synthetic validation |
| `src/states10.py` | reproduction gate and state extraction (iteration 9's `states.py` / `stage_mcode.py`, unchanged) |
| `src/analysis_g2.py`, `src/run_analysis.py` | frozen G1 / G2 analysis (hashes in COMMIT1) |
| `src/figures.py`, `src/make_outputs.py`, `src/add_topup_preds.py`, `src/t3_t9_checks.py`, `src/judges.py` | figures, outputs, T3 / T5 / T9 checks, judge gate and novelty audit |
| `src/explore_confusion.py`, `src/explore_dbeh.py`, `src/synth_t4b.py` | exploratory analyses added after COMMIT1 (LOO confusion structure, graded behavioural RDM, bootstrap-coverage addendum) |
| `src/{common,geometry,landing,states,stage_mcode,prompts_tp,programs,label_tp,expansion*,tpg,sample_or}.py` | iteration-9 modules, byte-identical |
| `src/{tracer_v9,orderclass,probes_v9}.py` | iteration-9 tracer, byte-identical |
| `audit/rederive.py`, `audit/rederive.json` | independent re-derivation 1 (stdlib + numpy): G1 rho_d / rho_c / exact permutation p / cell RDM, G2 F0 classes, covert F0 share; placebos |
| `audit/rederive2.py`, `audit/rederive2.json` | independent re-derivation 2 (stdlib + numpy, Floyd-Warshall geodesics): LOO nearest-cell accuracy and error split, PROBE landing, Delta(UD / BF), covert F1 share, AST-baseline rho_d; shuffled-label and Gaussian placebos |
| `predictions/` | `cells.json`; `commit0b_instrument_gate.json`; `commit0c` / `commit0d` amendments; `commit1.json`; `hardware.json` |
| `commitments.log` | hash chain (genesis sha256('iter10_tpg2'); verified in `results/t9_commitments.json`) |
| `data/raw_factorial.jsonl`, `data/raw_topups_v10.jsonl` | every generation call: prompt, content, provider, cost, seed |
| `data/factorial.jsonl` | every factorial program: suites, scrubbed code, instrument fields, acceptance |
| `data/topup_candidates.jsonl`, `data/survivor_candidates.jsonl`, `data/placed_covert.jsonl`, `data/primary_measured.jsonl` | the other program sets |
| `data/hand_reads.jsonl` | executor hand reads with a one-line rationale each |
| `data/frames.json`, `data/state_items.json` | committed frame lists and the programs whose states were read |
| `data/instrument_cache.jsonl`, `data/program_eval_cache.jsonl` | caches keyed by sha256; the eval cache is excluded from the published repo |
| `cache/states/tpg2_8b.npz`, `cache/states/tpg2_32b.npz` | **kept**: R[program, readout (R1, R1g, R2), block, d] float16 for all 412 programs |
| `cache/e46_states/` | **kept**: bit-identical reduced copies of iteration 9's cached M-code states (PRIMARY + SURV rows, blocks L-2..L+2, 4 readouts) and its frozen PRIMARY geodesic npz; provenance in `README.json` |
| `reproducibility.md`, `restore.sh`, `pyproject.toml`, `requirements.lock.txt` | exact reproduction steps, environment rebuild, 70 exact pins |
| `results/` | `g1_*.json`, `g2_*.json`, `verdicts.json`, `design.json`, `repro_gate.json`, `instrument_gate.json`, `t4_synthetic.json`, `t5_placement.json`, `t3_scrub.json`, `t9_commitments.json`, `novelty_audit.json`, `judges.json`, `positioning.json`, `deviations.json`, `costs.json`, `timing.jsonl` |
| `figures/` | see below |
| `method_out.json` (+ `full_` / `mini_` / `preview_`) | exp_gen_sol_out output; see below |
| `inputs/`, `vendor/`, `probes/` | copied iteration-8 / iteration-9 inputs with SHA256SUMS; test harness; probe grids |

Figures, each with PDF and PNG; every axis is in actual activation coordinates:

- `pca_F1_*`: PCA of frame F1, colour = discipline, marker = container;
- `isomap_F1_*`: Isomap at k = 15 and k = 10;
- `mds_F1_*`: classical MDS of the geodesics, with stress-1;
- `F0_counts_placed_*`: F0 catalogue centroids sized by implemented count, baseline vs ban, with survivors and covert
  programs overlaid;
- `subframes_UD_BF_*`: the S_disc and S_cont panels;
- `rdm_heatmaps_*`: the cell RDM next to D_disc, D_cont and D_surf;
- `g1_forest`: rho_d and rho_c with CIs, the permutation null band, the noise ceiling and the baselines.

Datasets in `method_out.json`:

| dataset | rows | output | predictions |
|---|---|---|---|
| `tpg2_factorial` | 237 | measured `disc\|cont` | leave-one-out nearest cell: model 8B, model 32B, TF-IDF baseline, AST baseline |
| `tpg2_topups` | 23 | hand-read class | leave-one-out nearest F0 class |
| `tpg2_placements` | 144 survivors + covert | family / label | class on F0, F1 and S_disc, and nearest cell, for 8B and 32B |
| `tpg2_g1` | 36 | one row per model x representation / sensitivity | |

The metadata holds the verdicts, deviations, commitments, costs and timing.

The two state files stay on the run's volume at the relative paths above. At 54 MB and 68 MB they are under the
100 MB publish limit, so they are also in the repository.

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r requirements.lock.txt
export OPENROUTER_BASE_URL=... OPENROUTER_API_KEY=...      # only for the generation stages
python method.py all          # resumable; stages skip when their outputs exist (--force reruns)
python method.py analysis rederive figures outputs --force   # recompute everything after the states
```

All paths are relative to this folder. Prior artifacts are sibling folders named by artifact id, each read through
one constant in `src/tpg2.py` that an environment variable can override:

- `TPG2_E46` → `../art_VVA3P0ocZNA2`
- `TPG2_E45` → `../art_8nXdw3_lDAll`
- `TPG2_E44` → `../art_R-HSmXq2t97f`
- `TPG2_DS` → `../art_j3Rm_lr2nzR6`

They are only needed to re-copy `inputs/` (already shipped, with `inputs/SHA256SUMS`) and for the novelty-audit pool.

Iteration 9's cached states are over the 100 MB publish limit. Bit-identical reduced copies (PRIMARY and SURV rows,
blocks L-2..L+2) ship in `cache/e46_states/`.

Full step-by-step instructions, with runtimes and expected numbers, are in `reproducibility.md`. `restore.sh` rebuilds
the environment.

## Deviations (full list in `results/deviations.json`)

- **D1.** COMMIT #0 was split: 0a before generation, 0b (the instrument) before any classification.
- **D2.** Instrument gate: 18/18 planted, 13/15 catalogue (JPS and BiA* misses; those classes are hand-read).
- **D3.** Container is read at runtime.
- **D4.** 15 catalogue references, not 25.
- **D5 / D7.** Edge-case prompt amendments (COMMIT0c, COMMIT0d).
- **D6.** Named top-ups carry the edge hint.
- **D8.** Plan F7: 3 non-banned F0 classes.
- **D9.** LEV_SET and RLX_HEAP dropped.
- **D10.** 19 RLX_STK programs disputed (AST-pattern gap; hand read decides).
- **D11.** D_beh sensitivity dropped.
- **D12.** Fresh states for the iteration-8 survivors.
- **D13.** No judge passed the gate.
- **D14.** Optional human-author check and the T7 kill/resume test not run.
- **D15.** `hardware.json` written at the end.
- **D16.** Portability: relative sibling-folder paths, reduced bit-identical iteration-9 state copies, and an edit to one provenance copy (`inputs/PORTABILITY_EDITS.md`).

Known limitations:

- The committed T4 bootstrap coverage was 0.56. The post-COMMIT1 addendum against each dataset's own expected value gives 0.92, so the P_boot statements are approximately calibrated.
- Hand-read and instrument agreement was 0.86, below the 0.90 target.
- All factorial programs share one author, Qwen3-32B. The 32B frame reads its own programs, while 8B reads another
  model's.
- Everything is correlational.

## Restoring removed files

`.aii/manifest.yaml` marks these for deletion after the round:

| deleted path | restore command |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r requirements.lock.txt` (or `bash restore.sh`) |
| `src/__pycache__/` | `python -m compileall src` (also recreated automatically on import) |
| `vendor/exp9/tasks/__pycache__/` | `python -m compileall vendor` (also recreated automatically on import) |

The `.venv` pins are the same as iteration 9's (torch 2.8.0+cu128, transformers 4.57.6, bitsandbytes 0.50.2). The two
binary state folders `cache/states/` and `cache/e46_states/` are **kept** and are not deleted.

Model weights live in the run's shared HF cache, not in this folder. To fetch them:
`huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218` and
`huggingface-cli download unsloth/Qwen3-32B-bnb-4bit --revision 7f721e74a6a8cc9ee352f7e49303a2c1705f9083`.
`data/program_eval_cache.jsonl` is excluded from the published repository. It is rebuilt by
`python method.py accept --force`, which re-runs the sandbox suites.
