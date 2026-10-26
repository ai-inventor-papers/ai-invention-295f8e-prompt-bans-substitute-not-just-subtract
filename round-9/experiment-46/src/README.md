# Mapping the ten grid algorithms with and without their names (TP-G, iteration 9)

Does Qwen3-32B's internal map of ten path-search algorithms reflect what the algorithms *do*, or only their *names*? Iteration 8 found that the algorithm Qwen3-32B writes when its top five are banned (unit-weight Dijkstra) sits OPPOSITE the banned five on a manifold built from prompts that *name* each algorithm. This artifact rebuilds that manifold four ways, holding the model, readout, block rule, k and landing code fixed: **M-name** (iteration 8's 300 alias prompts, reproduced), **M-desc** (name-free mechanism descriptions that Qwen3-32B can name), **M-lex** (name-only sentences minus token-length-matched neutral-noun twins) and **M-code** (name-scrubbed, verified programs, teacher-forced). All geometry is correlational: The geometry is correlational: it describes where representations and survivors sit, not whether the model uses this geometry to choose an algorithm (iteration 7's in-manifold pushes moved 0/300).

**Named outcome (pre-registered rule): MIXED.** M-code class of unit Dijkstra at k 15: EDGE; M-desc: OPPOSITE; M-code source robustness: ROBUST; k-sensitive: False.

## Headline results

### 1. M-name reproduces iteration 8's classes, but not its committed rank gate

- Per-prompt cosine with iteration 8's cached states: >= 0.99998 at every block (17-47).
- g of the five non-banned algorithms: max |difference| 0.030; classes identical ({'bibfs': 'EDGE', 'biastar': 'EDGE', 'idastar': 'MIDDLE', 'jps': 'OPPOSITE', 'dijkstra_unit': 'OPPOSITE'}).
- Committed gate (Spearman of the 45 class-geodesic entries, k 15, block 31) = 0.894 < 0.95: **G-repro fails**; at k 10 the same statistic is 0.997. Near-tied kNN edges among the banned clusters flip at k 15 (float16 storage was ruled out: 0.9999). Fallback F1 applies: the new states are used throughout and iteration 8's verdict (OPPOSITE) is reported beside.
- Qwen3-8B bf16 M-name against iteration 8's cached states: Spearman 0.994 (k 15), unit Dijkstra OPPOSITE at every k.

### 2. Verdict table (where the 15 unit-Dijkstra survivors land)

| Manifold (model) | L* | N | non-banned used | class(uDij) k10 | class(uDij) k15 | rank (1 = nearest) | g/median | nearest banned | landing verdict k15 | bootstrap P(EDGE) | split-half (S-B) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 32b|mname | 31 | 300 | bibfs, biastar, idastar, jps, dijkstra_unit | OPPOSITE | OPPOSITE | 5 | 1.63 | astar | OPPOSITE | 0.00 | 0.99 |
| 32b|mdesc | 31 | 260 | bibfs, biastar, idastar, dijkstra_unit | OPPOSITE | OPPOSITE | 3 | 1.08 | astar | OPPOSITE | 0.01 | 0.99 |
| 32b|mlex | 31 | 300 | bibfs, biastar, idastar, jps, dijkstra_unit | OPPOSITE | OPPOSITE | 4 | 1.20 | astar | OPPOSITE | 0.00 | 0.99 |
| 32b|mcode_PRIMARY_R1 | 33 | 117 | idastar, dijkstra_unit | EDGE | EDGE | 1 | 0.67 | gbfs | EDGE | 1.00 | 0.99 |
| 32b|mcode_PRIMARY_R2 | 21 | 117 | idastar, dijkstra_unit | EDGE | EDGE | 1 | 0.32 | astar | EDGE | 1.00 | 0.91 |
| 32b|mcode_M32_R1 | 31 | 113 | idastar, dijkstra_unit | EDGE | EDGE | 1 | 0.79 | gbfs | EDGE | 1.00 | 0.99 |
| 8b|mname | 17 | 300 | bibfs, biastar, idastar, jps, dijkstra_unit | OPPOSITE | OPPOSITE | 4 | 1.17 | astar | OPPOSITE | 0.01 | 0.98 |
| 8b|mdesc | 17 | 260 | bibfs, biastar, idastar, dijkstra_unit | OPPOSITE | OPPOSITE | 3 | 1.01 | astar | OPPOSITE | 0.49 | 0.98 |
| 8b|mcode_PRIMARY_R1 | 17 | 117 | idastar, dijkstra_unit | EDGE | EDGE | 1 | 0.63 | gbfs | EDGE | 1.00 | 0.98 |

Classes use iteration 8's relative rule (EDGE below the median of the non-banned g values, OPPOSITE above). A class over fewer than five non-banned algorithms is reported but weaker (see M-desc and M-code exclusions below).

### 3. Names drive the alias-level geometry (P4)

- 32b|mname: Spearman(g_alias, L1) = -0.74 (k 10, permutation p 0.0010) and -0.65 (k 15, p 0.0052); partial given alias length -0.67; within-algorithm exact p (L2, 7,776 permutations) 0.157. P4 (<= -0.6 at both k): True.
- 8b|mname: Spearman(g_alias, L1) = -0.70 (k 10, permutation p 0.0026) and -0.78 (k 15, p 0.0005); partial given alias length -0.78; within-algorithm exact p (L2, 7,776 permutations) 0.551. P4 (<= -0.6 at both k): True.
- 32b|mlex: Spearman(g_alias, L1) = -0.59 (k 10, permutation p 0.0111) and -0.65 (k 15, p 0.0054); partial given alias length -0.75; within-algorithm exact p (L2, 7,776 permutations) 0.326. P4 (<= -0.6 at both k): False.

### 4. RSA against model RDMs (exact label-permutation Mantel p)

| Neural RDM | R_lex | R_beh | R_surface | R_len | noise ceiling (upper) |
|---|---|---|---|---|---|
| 32b|mname (10 classes) | 0.46 (p 0.003) | 0.24 (p 0.091) | 0.20 (p 0.128) | 0.07 (p 0.297) | 1.00 |
| 32b|mdesc (9 classes) | 0.57 (p 0.000) | 0.12 (p 0.252) | 0.02 (p 0.463) | 0.01 (p 0.426) | 1.00 |
| 32b|mlex (10 classes) | 0.47 (p 0.001) | 0.29 (p 0.034) | -0.13 (p 0.785) | 0.33 (p 0.027) | 0.99 |
| 32b|mcode_PRIMARY_R1 (6 classes) | 0.29 (p 0.164) | 0.64 (p 0.018) | 0.67 (p 0.010) | 0.78 (p 0.007) | 1.00 |
| 32b|mcode_PRIMARY_R2 (6 classes) | -0.01 (p 0.451) | 0.59 (p 0.050) | 0.66 (p 0.039) | 0.49 (p 0.081) | 0.96 |
| 32b|mcode_M32_R1 (6 classes) | 0.10 (p 0.372) | 0.73 (p 0.008) | 0.70 (p 0.010) | 0.77 (p 0.007) | 1.00 |
| 8b|mname (10 classes) | 0.48 (p 0.002) | 0.27 (p 0.071) | -0.12 (p 0.715) | 0.28 (p 0.058) | 0.99 |
| 8b|mdesc (9 classes) | 0.25 (p 0.079) | 0.25 (p 0.087) | 0.33 (p 0.040) | 0.46 (p 0.008) | 0.99 |
| 8b|mcode_PRIMARY_R1 (6 classes) | 0.10 (p 0.360) | 0.88 (p 0.001) | 0.87 (p 0.001) | 0.88 (p 0.001) | 0.99 |

Name evocation: a probe trained on M-name (block 31) classifies M-desc at balanced accuracy 0.69 (chance 0.11) and M-code R1 at 0.17.

### 5. Behavioural anchor (P6) and stimulus gates

- Behavioural RDM from expansion-order traces of the 15 T1 references on 40 probe grids: d_beh to BFS {'bibfs': 0.72, 'biastar': 0.86, 'idastar': 1.12, 'jps': 1.06, 'dijkstra_unit': 0.31}; unit Dijkstra nearest BFS: True (true by construction for the order term). Behavioural classes: {'bibfs': 'OPPOSITE', 'biastar': 'EDGE', 'idastar': 'OPPOSITE', 'jps': 'MIDDLE', 'dijkstra_unit': 'EDGE'}. G-tracer 13/15 (biA* shows no second frontier because its forward side always wins ties on these grids; IDA* rarely restarts because the Manhattan bound is tight).
- Naming gate (Qwen3-32B, 20 namings per description, >= 16/20): passing descriptions per algorithm {'bfs': 3, 'dfs': 3, 'bibfs': 2, 'iddfs': 3, 'astar': 3, 'gbfs': 3, 'dijkstra_unit': 3, 'idastar': 3, 'jps': 0, 'biastar': 3}; excluded [['bibfs|2', 0.15], ['jps|0', 0.7], ['jps|1', 0.6], ['jps|2', 0.45]]. **JPS has no nameable name-free description**, so M-desc classes run over the other four non-banned algorithms.
- M-code program sets (PRIMARY / Qwen3-32B-only M32 / Qwen3-8B-only M8): {'PRIMARY': {'bfs': 20, 'dfs': 20, 'bibfs': 8, 'iddfs': 2, 'astar': 20, 'gbfs': 20, 'dijkstra_unit': 20, 'idastar': 17, 'jps': 0, 'biastar': 2}, 'M32': {'bfs': 20, 'dfs': 20, 'bibfs': 2, 'iddfs': 0, 'astar': 20, 'gbfs': 20, 'dijkstra_unit': 20, 'idastar': 13, 'jps': 0, 'biastar': 1}, 'M8': {'bfs': 20, 'dfs': 17, 'bibfs': 4, 'iddfs': 0, 'astar': 11, 'gbfs': 20, 'dijkstra_unit': 9, 'idastar': 3, 'jps': 0, 'biastar': 0}}; algorithms below the 10-program floor are excluded: {'PRIMARY': ['bibfs', 'iddfs', 'jps', 'biastar'], 'M32': ['bibfs', 'iddfs', 'jps', 'biastar'], 'M8': ['bibfs', 'iddfs', 'dijkstra_unit', 'idastar', 'jps', 'biastar']}.
- G-scrub (name scrubbing preserves AST modulo names, expansion sequences, labels and suite outcomes): 449/470; planted 'def bfs' test clean=True.

### 6. Per-program placement on M-code

- 32b|mcode_PRIMARY_R1 (block 33, k 15): leave-one-out placement accuracy 0.85 (gate 0.70: True); unit-Dijkstra survivors EDGE 15/15, nearest-algorithm counts {gbfs: 2, dijkstra_unit: 13}; BASE programs placed on their own label: 1.00.
- 32b|mcode_PRIMARY_R2 (block 21, k 15): leave-one-out placement accuracy 0.67 (gate 0.70: False); unit-Dijkstra survivors EDGE 15/15, nearest-algorithm counts {gbfs: 1, dijkstra_unit: 14}; BASE programs placed on their own label: 0.98.
- 32b|mcode_M32_R1 (block 31, k 15): leave-one-out placement accuracy 0.89 (gate 0.70: True); unit-Dijkstra survivors EDGE 10/15, nearest-algorithm counts {astar: 1, dijkstra_unit: 14}; BASE programs placed on their own label: 1.00.
- 8b|mcode_PRIMARY_R1 (block 17, k 15): leave-one-out placement accuracy 0.83 (gate 0.70: True); unit-Dijkstra survivors EDGE 15/15, nearest-algorithm counts {gbfs: 3, dijkstra_unit: 12}; BASE programs placed on their own label: 0.92.

### 7. Pre-registered predictions

- P1: pass = False
- P2: pass = False
- P3: pass = True
- P4: pass = True
- P5: pass = descriptive
- P6: pass = True
- P7: pass = descriptive
- P8: pass = True

### 8. Independent re-derivation

- `audit/rederive.py` (standard library only, from the JSON class matrices and alias rows): 0 mismatches; placebos {'random_survivor_labels_share_NEITHER': 0.9333333333333333, 'shuffled_labels_share_udij_OPPOSITE': 0.366, 'permuted_L1_mean_rho': -0.009264500449452597, 'permuted_L1_share_as_extreme_as_observed': 0.006}.
- `audit/audit_states.py` (sklearn kNN + networkx Dijkstra on the raw state files, no project geometry code): mismatches []; 32b|mname: classes equal True, max |dg| 3.73e-13, placebo share 0.40; 32b|mdesc: classes equal True, max |dg| 1.53e-13, placebo share 0.65; 32b|mlex: classes equal True, max |dg| 1.78e-15, placebo share 0.20; 32b|mcode_PRIMARY_R1: classes equal True, max |dg| 1.39e-13, placebo share 0.45

## Cost

OpenRouter: USD 0.094 for 1440 calls ({'naming_gate': 0.008386, 'topups': 0.085323}); cap 0.40.

## Deviations (results/deviations.json)

- **F1-repro**: M-name reproduction rho=0.894 (0.85-0.95: proceed with new states)
- **D-desc-checks**: descriptions outside the checks: [('bibfs', 'D3', 19, None)]
- **D-accept-B**: M-code sets use tier-B acceptance (mechanism labels + committed AST rules + trace check + valid paths on >= 38/40 probe grids) instead of the two hidden suites, for every source and algorithm alike: under tier A (committed ACCEPT) 4 of 5 non-banned classes have < 10 programs, mostly IDDFS/IDA*-style timeouts on the 30x30 hidden cases; tier-A counts are reported in results/acceptance.json
- **F9-S1-bibfs**: 19/40 labeller disagreements for S1 bibfs (excluded; no manual adjudication within the time box)
- **F9-S1-dijkstra_unit**: 13/40 labeller disagreements for S1 dijkstra_unit (excluded; no manual adjudication within the time box)
- **F9-S1-idastar**: 33/50 labeller disagreements for S1 idastar (excluded; no manual adjudication within the time box)
- **F9-S1-jps**: 25/50 labeller disagreements for S1 jps (excluded; no manual adjudication within the time box)
- **F9-S1-biastar**: 36/50 labeller disagreements for S1 biastar (excluded; no manual adjudication within the time box)
- **F9-S2-bibfs**: 36/60 labeller disagreements for S2 bibfs (excluded; no manual adjudication within the time box)
- **F9-S2-idastar**: 32/60 labeller disagreements for S2 idastar (excluded; no manual adjudication within the time box)
- **F9-S2-jps**: 36/60 labeller disagreements for S2 jps (excluded; no manual adjudication within the time box)
- **F9-S2-biastar**: 44/60 labeller disagreements for S2 biastar (excluded; no manual adjudication within the time box)
- **D-gscrub-fix**: G-scrub re-run before any M-code state: the first run required tier-B programs to pass the hidden suites after scrubbing (they were never required to pass them); the check is now 'suites outcome unchanged' (placement SURV/BASE still must pass); the code-span check counts boundary-straddling tokens; commit COMMIT1b-r1
- **F10-time**: analysis restricted to the 32B manifolds M-name, M-desc, M-lex, M-code PRIMARY R1/R2 and the Qwen3-32B-only M-code frame, and to M-name, M-desc, M-code R1 on Qwen3-8B; dropped for time: M8 frame, R1g and R3 readouts, Qwen3-8B M-lex (their states are kept in cache/states)

## How it was run

Every stage is `.venv/bin/python method.py <stage> [args]`; logs go to `logs/`, timings to `results/timing.jsonl`,
OpenRouter spend to `results/costs.json`. Stages in run order:

| Stage | Command | What it does |
|---|---|---|
| -1 | `inputs` | Copies the prior-artifact inputs into `inputs/` (+ `inputs/SHA256SUMS`), vendors the harness and labeller, writes `predictions/hardware.json` |
| 0 | `commit0` | Predictions P1-P8, gates, definitions, named outcomes; hash-committed before any state (`commitments.log`) |
| 1 | `mname 32b` | Qwen3-32B nf4 S-mean states of iteration 8's 300 forced prompts + the reproduction gate |
| 2 | `cpu` | 40 probe grids, expansion tracer on the 15 T1 references (G-tracer), behavioural RDM, lexical measures, descriptions v0, M-lex prompts with token-matched neutral twins, M-code contexts; COMMIT #1a |
| 3a | `naming` | Qwen3-32B (OpenRouter, DeepInfra fp8, thinking off) names each description 20 times; <= 2 rewrites |
| 3b | `topups` | 600 forced Qwen3-32B programs (60 per algorithm) |
| 4 | `pools` | ACCEPT (tier A committed, tier B used), scrub + G-scrub, M-code sets PRIMARY / M32 / M8, placement sets SURV / BASE / DISOBEY, M-desc prompts; COMMIT #1b |
| 5 | `states 32b mlex ban`, `states 8b mname mlex ban`, `states 32b mdesc mcode`, `states 8b mdesc mcode` | S-mean and code-token states |
| 6 | `blocks` | Label-only block selection (iteration 8's layer rule) for every model x manifold; COMMIT #2 |
| 7-10 | `analyse` | Geometry, verdicts, landing, bootstrap, robustness grid, crossnobis / z-scored sensitivities, frozen geodesics, lexical regression, exact-permutation RSA, name evocation, out-of-sample placement |
| 11 | `figures` | PCA / MDS / Isomap figures in activation coordinates, class table, RDM heatmaps, behavioural MDS |
| 12 | `outputs` | `data/points.jsonl`, `data/placements.jsonl`, `results/n4_verdict.json`, `method_out.json` |
| audit | `audit/rederive.py`, `audit/audit_states.py` | Independent re-derivations (stdlib-only from JSON; independent kNN/Dijkstra from raw states) with placebos |

`run_chain.sh` runs stages 5 (mdesc/mcode) to the audit unattended.

## Layout

| Path | What it is |
|---|---|
| `method.py` | Orchestrator, one sub-command per stage |
| `src/common.py`, `src/prompts_tp.py`, `src/states.py`, `src/geometry.py`, `src/landing.py`, `src/label_tp.py`, `src/sample_or.py`, `src/judge_tp.py` | Iteration 8's modules (art_R-HSmXq2t97f), byte-identical copies, imported unchanged |
| `src/e44/` | Unedited archive of iteration 8's whole `src/` |
| `src/tpg.py` | This artifact's frozen constants (banned split, model pins, blocks, k, budgets, gates) |
| `src/stage_setup.py` | Stage -1 and commit #0 |
| `src/stage_states.py`, `src/stage_mcode.py` | State extraction (S-mean families; M-code readouts R1 / R1g / R2 / R3) |
| `src/stage_cpu.py`, `src/expansion.py`, `src/expansion_child.py` | Probe grids, expansion tracer (child runs sandboxed, stdlib only), behavioural RDM, lexical measures, descriptions, M-lex twins, M-code contexts |
| `src/stage_or.py` | OpenRouter naming gate and top-ups (pinned provider, cost ledger, 403 stop) |
| `src/programs.py`, `src/stage_pools.py` | ACCEPT, scrubber, G-scrub, program and placement sets |
| `src/stage_analysis.py` | Block selection, geometry, landing, bootstrap, robustness, lexical regression, RSA, placement |
| `src/stage_figures.py`, `src/stage_outputs.py` | Figures and outputs |
| `audit/` | Independent re-derivations |
| `predictions/commit{0,1a,1b,2}.json`, `commitments.log` | Pre-registrations and their sha256 hash chain |
| `inputs/` | Prior-artifact inputs copied at Stage -1 (+ `SHA256SUMS`) |
| `vendor/exp9/`, `vendor/exp2/` | Iteration-2 harness, hidden suites, references and labeller (via iteration 8) |
| `data/` | Probe grids, descriptions, naming calls, top-ups, program sets, M-lex prompts, points and placements rows, sandbox cache |
| `results/` | Every analysis JSON |
| `figures/` | PDF + PNG figures; `figures/coords/` holds the 2-D coordinates they were drawn from |
| `cache/states/` | Activation states and frozen geodesic graphs. **Kept on the run's storage volume, not in the published repository** (files of 100 MB or more are not published; the whole directory is excluded from upload) |

## Restoring removed files

The manifest (`.aii/manifest.yaml`) marks three things for deletion after the round; each is restorable:

```bash
# .venv/ (regenerable)
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r requirements.lock.txt
# inputs/e44/states/ (regenerable: copies of the iteration-8 states; needs the art_R-HSmXq2t97f artifact folder,
# located by the TPG_E44 environment variable)
.venv/bin/python method.py inputs
# __pycache__/ (regenerable): created on import
```

Model weights are not stored in this folder. They are downloaded into the Hugging Face cache by
`.venv/bin/python scripts/download_models.py` (`unsloth/Qwen3-32B-bnb-4bit@7f721e74a6a8cc9ee352f7e49303a2c1705f9083`,
`Qwen/Qwen3-8B@b968826d9c46dd6066d109eabc6255188de91218`).
`cache/states/` is kept on the run volume; to rebuild it from scratch run the `mname`, `states` and `analyse` stages
(about 30 GPU-minutes on one RTX 5090).

