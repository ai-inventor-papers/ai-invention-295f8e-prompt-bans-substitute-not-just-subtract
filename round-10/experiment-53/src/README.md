# NOV-T: decision-token branching vs temperature in an LLM search for TSP heuristics

Does forcing an alternative token at the model's most uncertain code position (decision-token branching, **DTB**)
make an LLM-driven program search discover more distinct *behaviours* than simply raising the sampling temperature?
This folder runs that test on the standard constructive-TSP benchmark of automated heuristic design (the ReEvo/EoH
interface `select_next_node(current_node, destination_node, unvisited_nodes, distance_matrix)`), with
Qwen3-8B-FP8 (vLLM 0.11, thinking off) as the mutator inside a FunSearch-style island search.

## Results (seeds 0 and 1, 1,056 calls per arm-seed, 10,812 calls in total)

The search stopped at the hard stop (22:06 UTC) after 33 interleaved rounds, so every arm has exactly 1,056 calls per
seed (COMMIT #2 had projected C* = 2000; generated programs lengthened from ~140 to ~400 tokens and rounds slowed from
60 s to ~300 s). NOSEL reached 252 calls.

**V2-T (the operator claim): DISCONFIRMED by the pre-registered rule.** Behaviour clusters per 1,000 calls (complete
linkage, agreement >= 0.95 on 2,000 probe decisions):

| arm | seed 0 | seed 1 | validity s0 / s1 |
|---|---|---|---|
| T1.0 | 228.2 | 233.9 | 0.55 / 0.68 |
| T1.6 (top-p 0.95) | 88.1 | 104.2 | 0.32 / 0.31 |
| **DTB** | 228.2 | 216.9 | 0.64 / 0.61 |
| RPB (placebo) | 236.7 | 233.0 | 0.62 / 0.58 |
| IDEA | 296.4 | 298.3 | 0.78 / 0.77 |

Pooled ratios: DTB/T1.0 = **0.963** (kill condition R <= 1.0 met), DTB/T1.6 = 2.315, DTB/RPB = 0.948. Per-seed
DTB/T1.0 = 1.00 [0.89, 1.14] and 0.93 [0.83, 1.02] (paired round-block bootstrap 95%); DTB/RPB = 0.96 [0.89, 1.10]
and 0.93 [0.84, 1.06]; DTB/T1.6 = 2.59 [2.28, 2.88] and 2.08 [1.80, 2.35] (T1.6 mostly loses validity). No sensitivity
reverses a sign: secondary count over programs better than NN 0.72 / 3.21 / 0.93 (vs T1.0 / T1.6 / RPB), per million
generated tokens 0.93 / 2.18 / 0.86, rarefied to equal probe-valid N 0.95 / 1.41 / 0.94, pooled linkage 0.97 / 2.16 /
0.96. DTB does branch where intended (median entropy at j* 0.85 / 0.79 nats vs 0.00 for RPB; no-branch 0%), but the
forced token adds no behavioural diversity beyond T1.0 or a random-position forcing, and its held-out best is worse
than T1.0's (DTB - T1.0 paired gap difference +1.2 [0.4, 2.1] and +2.7 [1.3, 4.1] points). The IDEA instruction gave the
most clusters (~1.3x T1.0) and the lowest parent-rename rate (6% vs 18-22% for T1.0).

**V1-T: SUPPORTED.** Every core arm-seed's selection-best (probe-valid) program closes at least 20% of NN's held-out
gap: NN 23.94% at n=200 (bar 19.15%); T1.0 14.48 / 13.98, T1.6 16.29 / 16.49, DTB 15.69 / 16.68, RPB 15.61 / 15.76
(IDEA 13.88 / 16.63); all paired 95% intervals versus NN exclude 0. Extended n=200 and TSPLIB agree (e.g. T1.0 seed 1:
13.85% extended, 10.31% TSPLIB vs NN 25.21% / 28.11%).

**Baselines and corpus on the same instances (held-out n=200 gap %).** NN 23.94; tuned parametric P1 (2,000
evaluations) 17.35; ReEvo/EoH seed rule 13.67; MCTS-AHD appendix heuristics 14.01-20.82; regret-2 24.41; NOSEL
best-of-252 27.87 (vs T1.0's best within its first 252 calls 15.99); tour-length references with another interface:
farthest insertion 8.65, random insertion 11.31, greedy edge 17.81. No searched program beats the published ReEvo/EoH
seed rule on held-out data.

**V3-T (reported).** 32 pooled programs are better than 0.8 x NN and agree on < 0.90 of probe decisions with every
admitted corpus member (T1.0 5, T1.6 8, DTB 6, RPB 7, IDEA 6). Neither judge passed its 10-control gate (DeepSeek 8/10,
Kimi-K2 5/10; USD 0.037), so the written manual-read rule decides: the 12 read candidates are all KNOWN FAMILY, NEW
PARAMETERS (weighted sums of distance to current, destination terms and statistics of distances to the unvisited set);
0/12 NOVEL (rule-of-three 95% upper bound 25%).

**Audit.** `audit/rederive.py` (standard library only) re-derives every cluster count exactly (10/10 arm-seeds), the
ratios, G200 means and both verdicts; its placebos fail as required (shuffled arm labels: ratios 1.03-1.10, V2 not
supported; DTB/T1.0 swapped: not supported; threshold 0 = unique vectors; one cluster per arm: R = 1; NN's G200 replaced
by the best arm's: V1 not supported). 50/50 logged DTB/RPB forcings are re-derived from their logged top-20 log
probabilities and seeds (`results/rederive_forcing_data.json`).

Predictions committed before the search (COMMIT #1) that failed: V2-T SUPPORTED; DTB forced tokens on
identifiers/operators/keywords in >= 60% of branched calls (50% / 62%; numeric literals took 44% / 35%); IDEA rename
rate >= 0.4 (observed 0.06). The NN held-out gap (23.94%) fell just below the predicted 24-28% range; V1-T SUPPORTED
held. Validity guesses: DTB, RPB and IDEA exceeded theirs (0.50 / 0.45 / 0.55); T1.0 (0.55 / 0.68) and T1.6
(0.32 / 0.31) were close to theirs (0.60 / 0.35).


## What was run

- **Task.** A tour is built greedily from city 0 and closed; each call gets a fresh set copy and a fresh writable
  distance-matrix copy (ReEvo semantics). The search sees only 64 SELECTION instances (32 at n=50, 32 at n=100)
  scored against LKH-3 (elkai) tours. Fitness F = 0.5 G50/G50(NN) + 0.5 G100/G100(NN) (NN = 1, lower is better).
  Held-out sets: 32 random n=200 instances (primary), 96 more (extended) and 13 TSPLIB instances (EUC_2D, published
  optima; elkai reaches all 13 optima exactly).
- **Search.** Per (arm, seed): 5 islands seeded with nearest neighbour (NN), best-shot prompts with two parents
  (worse first), cluster softmax with FunSearch's temperature schedule, 2 worst islands reset every 400 calls.
  Arms run interleaved, 32 calls per arm-seed per round, so every arm has matched calls at any stop:
  **T1.0** (T 1, top-p 1), **T1.6** (T 1.6, top-p 0.95), **DTB** (forced rank-2..8 token at the highest-entropy
  code position of the first 48 body tokens, then continue at T 1), **RPB** (same forcing at a random eligible
  position: the placebo), **IDEA** (instruction to use a different idea), and **NOSEL** (no selection, NN-only
  prompt; seed 0). Seeds 0 and 1.
- **Behaviour instrument (name-blind).** Next-city decisions on 2,000 frozen probe states; complete-linkage
  clusters at within-cluster agreement >= 0.95. V2-T compares clusters per 1,000 calls.
- **Baselines / comparators in the same pipeline.** NN (seed program and baseline), tuned parametric rule P1
  (2,000-evaluation random search on SELECTION, comparator at C* evaluations), insertion and greedy-edge tours
  (other interface, references), and a dated corpus of published heuristics re-run on our instances (ReEvo/EoH seed
  rule, LLM4AD template, four MCTS-AHD heuristics from its appendix, textbook rules).
- **Pre-registration.** `commitments.log` hash-chains COMMIT #1 (protocol, predictions, code; before the first
  search call), COMMIT #2 (C* from measured round times) and COMMIT #3 (corpus, before any V3 analysis).

## Layout

| Path | Content |
|---|---|
| `method.py` | Entry point: `python method.py <stage>` (stage0, p1, tests, gpu, commit1, pilot, search, commit2, corpus, analyze, judges, figures, outputs, rederive) |
| `start_vllm.sh` | vLLM 0.11 server launcher (FP8-Marlin, torch.compile + CUDA graphs, prefix caching) |
| `src/tsp_task.py` | Instance sets (fixed seeds), TSPLIB parsing, elkai / OR-Tools references |
| `src/sandbox.py` | Static AST check + fork-per-program sandbox (rlimits, restricted builtins), SELECTION + PROBES in one child |
| `src/probes.py` | The 2,000 frozen probe states |
| `src/baselines.py` | NN program, P1 family, insertion and greedy-edge references |
| `src/prompt.py`, `src/engine.py` | Prompt/prefill/extraction; local completions client (token-id prompts) |
| `src/dtb.py` | DTB/RPB: lexer, entropy, eligible positions, candidate filter, forced-token draw |
| `src/islands.py`, `src/search.py` | FunSearch-style database; resumable round-based driver |
| `src/cstar.py`, `src/commit.py` | COMMIT #2 (C*) and the hash chain |
| `src/analysis.py` | Pre-registered statistics (clusters, rarefaction, bootstraps, verdict rules) |
| `src/analyze_run.py` | Stage-5 driver: summaries, clusters, held-out bests, verdicts, V3 pool |
| `src/corpus.py`, `src/judges.py` | Published-heuristic corpus (COMMIT #3) and gated V3 judges; literature positioning in `results/positioning.json` (raw searches in `data/positioning_raw/`) |
| `src/dep_extract.py` | Scans all 10 datasets of art_j3Rm_lr2nzR6; harness check with HumanEval+ |
| `src/figures.py`, `src/outputs.py` | Figures F1-F6; method_out.json builder |
| `audit/rederive.py` | Standard-library re-derivation of the headline numbers + placebos |
| `tests/` | CPU unit tests T1-T9, GPU mechanics G1-G5, forcing re-derivation test |
| `data/` | `calls.jsonl` (one row per call), `requests/` (raw requests with request-1 top-20 log probs), `probe_decisions.bin` + `probe_index.jsonl`, instances, references, P1 search, corpus raw fetches, pilot |
| `results/` | All analysis JSON (see below) |
| `predictions/` | `protocol.json` (COMMIT #1), `cstar.json` (COMMIT #2), `hardware.json` |
| `figures/` | F1 discovery curves, F2 best-so-far F, F3 held-out gaps, F4 validity/F, F5 DTB diagnostics, F6 tours |
| `method_out.json` (+ `full_`/`mini_`/`preview_`) | exp_gen_sol_out output |

Main results files: `verdict_v1.json`, `verdict_v2.json`, `clusters.json`, `rarefaction.json`, `heldout.json`,
`search_summary.json`, `v3.json`, `judges.json`, `corpus.json`, `baselines.json`, `references.json`,
`positioning.json`, `dependency_usage.json`, `rederive.json`, `rederive_forcing_data.json`, `deviations.json`,
`timing.json`, `gpu_mechanics.json`.

Kept large files (they stay on the run's storage volume; files of 100 MB or more are not pushed to the published
repository): `data/calls.jsonl`, `data/requests/*.jsonl`, `data/probe_decisions.bin`, `full_method_out.json`.

## How to run

See `reproducibility.md` for the exact sequence. In short: create the venv from `requirements.txt`, download the
model, `bash start_vllm.sh compile &`, then `python method.py stage0`, `p1`, `tests`, `gpu`, `commit1`, `pilot`,
`search` (background; `python src/cstar.py HH:MM` after five rounds; `touch data/STOP` to end), `corpus`,
`analyze`, `judges`, `figures`, `rederive`, `outputs`.

## Restoring removed files

The `.aii/manifest.yaml` marks these for deletion after the round; restore them with:

- `.venv/` (regenerable): `uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r requirements.txt`
- `.cache/` (regenerable: vLLM torch.compile, Triton and inductor caches): rebuilt automatically by
  `bash start_vllm.sh compile` on the first server start.
- `scratch/` (regenerable: empty per-process sandbox directories): recreated by `src/sandbox.py`.
- Model weights (kept in the run's shared HF cache, not in this folder):
  `hf download Qwen/Qwen3-8B-FP8 --revision 220b46e3b2180893580a4454f21f22d3ebb187d3`.
