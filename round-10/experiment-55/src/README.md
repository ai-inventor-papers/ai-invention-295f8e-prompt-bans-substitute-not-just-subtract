# TP-G2: do code-LM program maps track search behaviour or storage style?

Iteration 10 of the TP-G line (plan `gen_plan_experiment_5_idx5`; it continues iteration 9's `art_VVA3P0ocZNA2` /
`art_8nXdw3_lDAll`). The question is whether the program-state geometry that earlier rounds read as "the path-search
manifold" separates programs by **expansion discipline** (FIFO order, LIFO order, goal-heuristic order, path-cost
order, relaxation rounds, random order) once **storage container** (deque, list, recursion, heapq, 2-D arrays, set) is
held fixed by design. A second question is where the survivor families of the five-name ban land on a frame built
from that factorial.

## What was done

1. **Factorial program set (G1 stimuli).** Qwen3-32B (OpenRouter, DeepInfra, thinking off, T 1.0) wrote grid path
   programs for 24 implementable discipline x container cells. Each prompt has three wordings, describes the
   mechanics step by step and names no algorithm (lint: 0 hits over 144 prompts). Every program passed:
   - the 48-case and 41-case hidden suites;
   - an AST container check;
   - a discipline check: the iteration-9 tracer for BFSO/DFSO/HEUR/COST, a two-seed runtime check for RAND, and
     an AST repeat-sweep check plus a ≥ 2-pass runtime check for RELAX. GRID2D cells used AST checks plus a hand
     read (amendment F7, committed before wave A);
   - name scrubbing (`programs.scrub`) followed by a re-run of the 48-case suite.

   Failed programs got one repair turn. The freeze took the first 12 verified programs per cell in completion
   order, 287 programs in all (RELAX-SET has 11). Top-ups (12 each) were frozen for bidirectional BFS, IDDFS and
   bidirectional A*. All 12 JPS top-ups are paraphrases of the reference `jps4.py`.
2. **States.** Each program was teacher-forced under iteration 9's neutral-twin contexts (W1–W5), using iteration 9's
   frozen readout code (`stage_mcode.build` / `forward_readouts`, unchanged) and its exact truncated decoder:
   - Qwen3-8B bf16 (block 17) and Qwen3-32B NF4 (block 33);
   - readouts R1, R1g, R2 and R3;
   - baselines: E0 (mean input embedding over the code tokens) and RANDNET (random-init truncated Qwen3-8B).

   Checks:
   - the hook check is exact;
   - re-extracting 10 cached iteration-9 programs gives cosine ≥ 0.9998 and equal token counts;
   - the R0 gate reproduces iteration 9's frames bit for bit: unit-weight Dijkstra g/median is 0.6296 (8B) and
     0.6725 (32B), and 113/113 placements match.
3. **G1:** partial Spearman of the program-state RDM with the discipline RDM given container (ρ_dc), and the reverse
   (ρ_cd).
   - Inference: a program bootstrap (1,000 resamples) and restricted permutations within strata (2,000). Discipline
     labels are permuted within container strata and container labels within discipline strata.
   - Committed sensitivities:
     - S1, the crossed 3x4 core;
     - S2, rank regression with surface, length and context RDMs;
     - S3–S5, alternative discipline, container and surface RDMs (IDF weights come from all Python-bearing datasets
       of the dependency);
     - S6, other readouts, the layer curve and a geodesic D_S;
     - S7, the E0 and RANDNET baselines, and the measured expansion order used as D_disc;
     - S8, the cell-cluster bootstrap;
     - S9, the noise ceiling;
     - S10, without repair rows;
     - S11, Kendall τ-a.
4. **G2.** 351 placed programs were placed out of sample on a 464-program frame (24 cells + catalogue). The
   placement uses iteration 9's kNN-geodesic code (`geometry.py`, `oos` unchanged).
   - Placed families:
     - F-UD: 38 unit-weight Dijkstra;
     - F-BF: 32 grid Bellman-Ford;
     - F-CK: 18 coordinate-key heaps;
     - F-RF: 14 random frontiers;
     - F-RS: 4 raster sweeps;
     - F-SF: 3 set frontiers;
     - F-OTH: 8 other;
     - F-COV: 136 covert BFS/DFS from the five-name ban;
     - F-COVX: 98 covert BFS/DFS from other ban sets.
   - Frames: the full frame, the HEAP / GRID2D / SET / DEQUE+LIST container-held-fixed frames, and the BFSO+COST /
     RELAX / DFSO discipline-held-fixed frames.
5. **Pre-registration.** `commitments.log` is a sha256 hash chain whose genesis is `sha256('iter10_tpg2')`. It holds:
   - COMMIT1a: cells, prompts, verifiers, every rule and prediction (before wave A);
   - COMMIT1b: family lists (before any placed-program state);
   - COMMIT1c: the g1/g2 code (before any G1/G2 output);
   - the factorial and top-up freezes (before their states).

## Results (numbers from `results/`)

**G1 verdict: INDETERMINATE on both models (`results/g1_verdict.json`).** Discipline is encoded, but container is
encoded more strongly, and token surface more strongly than either.

| model (block, R1) | ρ_dc [95% CI] | ρ_cd [95% CI] | δ = ρ_dc − ρ_cd [CI] | perm p (dc / cd) |
|---|---|---|---|---|
| Qwen3-8B (17) | 0.226 [0.186, 0.265] | 0.300 [0.251, 0.351] | −0.074 [−0.133, −0.018] | 0.0005 / 0.0005 |
| Qwen3-32B (33) | 0.285 [0.252, 0.321] | 0.414 [0.363, 0.462] | −0.129 [−0.193, −0.060] | 0.0005 / 0.0005 |
| 8B crossed core 3x4 | 0.280 [0.218, 0.357] | 0.366 [0.293, 0.457] | −0.086 [−0.182, 0.008] | 0.0005 / 0.0005 |
| 32B crossed core 3x4 | 0.336 [0.288, 0.392] | 0.545 [0.482, 0.611] | −0.209 [−0.295, −0.118] | 0.0005 / 0.0005 |

- **Baselines.** The E0 bag-of-tokens baseline gives ρ_dc 0.169 (8B) and 0.156 (32B). RANDNET gives 0.072. The
  trained states therefore carry discipline information beyond token identity, but less than the 0.30 threshold.
- **Surface dominates.**
  - Rank regression (S2), semi-partial r on 8B: D_surf 0.32, D_len 0.30, D_cont 0.13, D_disc 0.10, D_ctx 0.02.
  - The same on 32B: D_surf 0.41, D_len 0.23, D_cont 0.20, D_disc 0.13.
  - Partialling the token-surface RDM out leaves ρ_dc 0.13–0.15 (8B) and 0.18–0.21 (32B).
- **Robustness.**
  - The noise ceiling across context variants is 0.94 (8B).
  - The cell-cluster bootstrap widens the δ CI to include 0.
  - Readouts: R2 (token after the first pop) gives ρ_dc 0.09 and R3 (16th code token) gives 0.04–0.05.
  - The layer curve is flat: ρ_dc 0.20–0.26 on 8B and 0.25–0.30 on 32B.
- **Placebos fail as required:** discipline labels shuffled give ρ_dc 0.006; container labels shuffled within
  discipline give ρ_cd 0.006.

**G2 (`results/g2_<model>.json`).** The frame's class-level LOO accuracy is 0.68 (8B) / 0.83 (32B), and its
discipline-level LOO accuracy 0.83 / 0.91, against a chance level of 0.03. The false-inside rate is 0.46 / 0.47, with
banned classes making up 53% of the frame's classes.

| prediction | Qwen3-8B | Qwen3-32B |
|---|---|---|
| P-UD (EDGE on full + HEAP frames; nearest discipline BFSO/COST; contrast) | r_F 0.90 [0.77, 1.00] EDGE, HEAP 0.99 EDGE (both not robust); 76% nearest BFSO/COST (COST 27/38); contrast 38/38 (p 4e-12) → rule met, not robust | r_F 0.98 EDGE, HEAP 1.03 **OPPOSITE** (not robust); 68% BFSO/COST; contrast 38/38 → not supported |
| P-BF (OPPOSITE; nearest RELAX; RELAX-GRID2D on GRID2D frame) | r_F 0.86 **EDGE** (robust) → full-frame part fails; nearest RELAX 30/32; GRID2D frame RELAX-GRID2D 30/32; contrast 29/32 | r_F 1.03 [1.01, 1.07] **OPPOSITE robust**; nearest RELAX 31/32; contrast 31/32 → supported |
| P-COV (≥ 0.8 banned nearest class) | 0.993 [0.960, 0.999]; BFS→BFSO 0.92, DFS→DFSO 0.85 → supported | 0.978 [0.937, 0.992]; 0.93 / 0.87 → supported |

**Independent audit (`audit/rederive_g2.py`, stdlib, results/rederive_g2.json).** The G2 shares were recomputed
from the raw class-distance CSVs and compared with random families of the same size drawn from all placed programs.
- F-BF nearest RELAX: 0.94 (8B) and 0.97 (32B), against a placebo median of 0.09.
- P-COV banned-nearest: 0.99 and 0.98, against a placebo median of 0.78 (q95 0.82).
- The P-UD contrast (BFSO/COST-HEAP closer than HEUR-HEAP) is **not specific on 8B**: every family, and every random
  draw, scores 1.0 there, so the 8B 38/38 sign test passes vacuously. On 32B it is specific: 1.0 against a placebo
  median of 0.47.
- A stdlib G1 placebo with discipline labels shuffled gives ρ_dc 0.0003 (8B) and 0.0075 (32B).

**Caveat on r_F.** Every family is EDGE on 8B, and so is every random draw of 38 placed programs (placebo:
1000/1000). The r_F point verdict therefore does not discriminate families on 8B. The family-specific evidence is the
nearest-class pattern and the pre-committed contrasts: Bellman-Ford survivors sit with RELAX cells; unit-weight
Dijkstra survivors sit with COST-HEAP / BFSO-HEAP rather than HEUR-HEAP; covert BFS/DFS sit with their own discipline.

The robustness grid ({8B, 32B} x {k15, k10} x {R1, R1g, R2}; 12 cells) is in `results/robustness.json`.
- **P-COV** holds in 12/12 cells, with a share of 0.96–1.00.
- **P-UD:** the full-frame verdict is EDGE in 12/12 cells, but the HEAP frame turns OPPOSITE in 6/12. The complete
  P-UD rule holds in 6/12 cells: 8B R1 and R2 at both k, and 32B R2 at both k.
- **P-BF** holds in 8/12 cells: every 32B cell, plus 8B R2 at both k and 8B k10 R1g. It fails at the 8B primary
  setting.

## Interpretation limits

These follow the mechanistic-interpretability handbook.
- **Geometry is correlational.** Nothing here moves a model's output; iteration 7's in-manifold pushes moved 0/300.
  "Decodable is not actionable."
- **The map class is declared and frozen:** iteration 9's readout, block, k and landing code, with no fitted
  alignment.
- **Effects are reported as distributions:** program bootstrap, cell-cluster bootstrap and restricted permutations.
  Random-network (RANDNET) and bag-of-tokens (E0) baselines sit beside every G1 number.
- **The authorship confound remains.** Every factorial program has one author (Qwen3-32B), while survivors and covert
  programs come from several authors. Placement of non-Qwen programs is therefore weaker evidence; the per-author
  breakdowns are in `results/g2_*.json` (P-COV `by_author`).

## Layout

- `method.py`: orchestrator for every stage (`.venv/bin/python method.py <stage>`; see its docstring).
- `src/`:
  - `cells.py`: cell table and prompts;
  - `verify.py` and `probe_child.py`: the verifiers;
  - `gen.py`: OpenRouter generation, repair and paraphrase;
  - `assemble.py`: placed families;
  - `freeze.py`;
  - `extract.py`: states;
  - `g1.py` and `g2.py`: the statistics, frozen in COMMIT1c;
  - `analysis.py`: the G1/G2 drivers;
  - `outputs.py`;
  - `figures.py`;
  - `r0.py`: the reproduction gate;
  - `v10.py`: constants and the commitment chain.
  - Reused unchanged from iteration 9: `common.py`, `states.py`, `stage_mcode.py`, `geometry.py`, `landing.py`,
    `programs.py`, `expansion*.py`, `prompts_tp.py`, `tpg.py`, `label_tp.py`, `judge_tp.py`, `sample_or.py`,
    `tracer_v9.py`, `orderclass.py`, `probes_v9.py`.
- `vendor/`: hidden-test harnesses, the 48-case and 41-case suites, the 15 T1 references and the labeller (copied,
  sha256 in `inputs_manifest.json`). `probes/` holds the tracer's 40 probe grids.
- `inputs/`: copies of the prior artifacts' data and results that this round reads.
- `tests/`: `test_verifiers.py` (34/34 pass: references, 12 planted hard-cell programs, 4 negative controls,
  idastar rejected in every cell), `test_analysis.py` (T7 synthetic G1 checks, T8 placement checks), and the
  planted and negative programs.
- `data/`:
  - `programs_v10.jsonl`: every verified generation;
  - `gen_raw_v10.jsonl`: every API call;
  - `hand_reads_v10.jsonl`: 139 hand reads;
  - `factorial_set.jsonl`, `topups_set.jsonl`, `placed_programs.jsonl`;
  - `frame_freeze.json`, `topup_freeze.json`, `order_matrix_factorial.npz`.
- `results/`:
  - `g1_8b.json`, `g1_32b.json`, `g1_verdict.json`, `g2_8b.json`, `g2_32b.json`, `robustness.json`;
  - `placebos.json`, `r0_reproduction.json`, `state_checks_*.json`, `verifier_unit_tests.json`,
    `analysis_unit_tests.json`;
  - `verification_summary.json`, `costs_v10.json`, `deviations.json`, `rederive.json`;
  - `pairs_<model>.csv`: per-pair RDM entries for the audit;
  - `geo_class_dist_<model>.csv`: per-program class geodesics.
- `figures/` (PDF + PNG, actual activation coordinates):
  - `F1_factorial_8b` / `F2_factorial_32b`: PCA, Isomap and MDS of the factorial frame;
  - `F3_full_frame_*`: implemented counts at baseline vs under the ban, with families overlaid;
  - `F4_heldfixed_8b`: the HEAP and GRID2D frames;
  - `F5_g1_bars`, `F6_family_g_*`, `F7_layer_curve`, `F8_placement_heatmap_8b`.
- `audit/rederive.py`: a stdlib-only re-derivation of ρ_dc, ρ_cd, δ, r_F and the cell counts (0 mismatches).
- `predictions/`: the commitment payloads (`commit1.json`, `commit1b.json`, `commit1c.json`) and `hardware.json`.
  `commitments.log` holds the hash chain.
- `method_out.json` (+ `full_` / `mini_` / `preview_`): exp_gen_sol_out with four datasets: `tpg2_factorial` (287),
  `tpg2_topups` (48), `tpg2_placements` (351) and `tpg2_g1_rows`.
- `cache/states_v10/` **stays on the run's volume, not in the published repository** (files ≥ 100 MB are not
  pushed). It holds the program states (`<model>_<set>.npz` plus a `.jsonl` index) and the G2 frame coordinates
  (`g2frame_<model>.npz`). Later rounds read these.

## Hand-read rule

The executor read every RELAX and GRID2D program, every tracer/AST disagreement and every top-up program. The verdict
is ACCEPT if and only if the code implements the cell's storage AND selection rule as specified (or, for a top-up, its
mechanics). A program that passes the automatic checks but whose search loop is driven by a different container or
order is REJECT. There were 4 REJECTs:
- a RELAX-SET program that shrinks its sweep set;
- a BFSO-HEAP program whose popped entry overwrites the global counter;
- two bidirectional A* programs that are effectively one-directional.

The reading depth is recorded per row; see `results/deviations.json` (D-hand-read-depth).

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r requirements.lock.txt
.venv/bin/python scripts/download_full.py          # Qwen/Qwen3-8B and unsloth/Qwen3-32B-bnb-4bit at pinned revisions
.venv/bin/python method.py setup r0 tests          # inputs, reproduction gate, verifier + analysis tests
.venv/bin/python method.py generate assemble freeze states order   # needs OPENROUTER_BASE_URL / OPENROUTER_API_KEY
.venv/bin/python method.py all-analysis            # g1, g2, robustness, outputs, figures, audit
```

Generation is resumable from `data/gen_raw_v10.jsonl`, so re-running it on the shipped data makes no API calls.
OpenRouter spend for this artifact was USD 0.25 for 1,138 calls (`results/costs_v10.json`).

## Deviations

Every deviation is in `results/deviations.json`. The main ones:
- The hardware was smaller than planned, so fewer blocks were kept.
- Commit #1 was split into 1a/1b/1c.
- F-COV has 136 programs, not ~294. The rest come from other ban sets and form F-COVX.
- The state-reproduction cosine is 0.9998 rather than 0.9999 (different GPU).
- JPS consists only of paraphrases of the reference.
- Sensitivity bootstraps used 200 resamples.
- `results/positioning.json` is a title-level screen of 6 scholarly queries, with no verbatim quotes.

## Restoring removed files

| removed path (`.aii/manifest.yaml` delete entry) | how to restore |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r requirements.lock.txt` |
| `src/__pycache__/` | regenerated automatically by any `.venv/bin/python method.py <stage>` run |
| `audit/__pycache__/` | regenerated automatically by `python3 audit/rederive_g2.py` |
| `vendor/exp9/tasks/__pycache__/` | regenerated automatically by `.venv/bin/python method.py tests` |

Not in this folder at all, but needed to rerun the state extraction:
- **Model weights** live in the shared Hugging Face cache. Restore them with `.venv/bin/python scripts/download_full.py`
  (Qwen/Qwen3-8B@b968826d9c46dd6066d109eabc6255188de91218, unsloth/Qwen3-32B-bnb-4bit@7f721e74a6a8cc9ee352f7e49303a2c1705f9083).
- **`cache/states_v10/`** is kept on the run's volume and is not in the published repository (files ≥ 100 MB). Rebuild
  it with `.venv/bin/python method.py states` (see `reproducibility.md`, steps 9, 10, 14 and 16).
