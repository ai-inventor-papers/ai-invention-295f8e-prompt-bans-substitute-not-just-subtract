# Mapping how bans move path-search choices (Qwen3-8B)

A one-artifact **screen**: when Qwen3-8B (bf16, thinking off) writes a path-search program, which algorithm
does it choose, where do *prompt bans* send it, and can removing the modal algorithm's direction from the
activations do the same? Two tasks from the original request:

* **T1 `t1_grid_path`**: unweighted grid path (`solve(grid, start, goal)`), 6-mode catalogue
  `bfs, dfs, bidir_bfs, iddfs, astar, dijkstra_unit`.
* **T2 `t2_weighted_sp`**: weighted shortest path (`solve(n, edges, s, t)`), 5-mode catalogue
  `dijkstra, bellman_ford_spfa, bidir_dijkstra, floyd_warshall, dial`.

Everything is **descriptive**. The screen produced 2 primary ban events (plus exploratory ones) and 2 removal
events, which is far below any inferential floor, so no p-values are reported anywhere.

## Results at a glance (Qwen3-8B, T=1.0, thinking off)

Each item below gives the file to check.

**1. The default is a total collapse.** The baselines (N=200 per task, 10 paraphrases × 20) give **T1: 200/200 BFS**
(pass rate 0.99) and **T2: 200/200 Dijkstra** (pass rate 1.00), with Hill number 1.00 on both tasks. Mentioning the
modal algorithm (`mention:X`, N=50) leaves it at 50/50. The model *can* write the other modes when asked: on T1 94%
of forced prompts are implemented as asked, on T2 74% (bidirectional Dijkstra and Dial are flagged below 50%).
Correctness of the non-default modes is low, though: forced DFS passes 30% of the time, IDDFS 0%, bidirectional BFS 23%
(`results/phaseA_summary.json`).

**2. Bans mostly fail, and what does move goes to the geodesic neighbours of the banned mode.**
* `ban:bfs` (N=100): 62 BFS, 29 DFS, 9 unit-Dijkstra. Compliance is **0.18**, so this is a pre-declared ban failure
  and the succession stopped. Compliance depends heavily on wording: 4 of the 10 paraphrases give 10/10 BFS.
* `ban:dijkstra` (N=100): 72 Dijkstra, 27 Bellman-Ford/SPFA, 1 other. Compliance is **0.22**, again a ban failure.
  Some programs acknowledge the ban in a comment and implement the banned algorithm anyway, for example
  "# Dijkstra's algorithm (but since the user said not to use Dijkstra's algorithm, this is a workaround)", or on T1
  "# Note: The problem says BFS is forbidden, but the user provided a conflicting instruction. Assuming the task
  allows BFS." (`data/samples_phaseC.jsonl`).
* Exploratory step-2 bans (N=50; forecasts committed beforehand). `ban:bfs+dfs` gives 19 unit-Dijkstra and 29 BFS.
  `ban:bfs+dijkstra_unit` gives 17 DFS and 31 BFS. `ban:dijkstra+bellman_ford_spfa` gives 37 Dijkstra, 12 BF/SPFA and
  0 compliant samples.
* On T1's geodesic map (`figures/ban_shift_on_manifold_t1.png`), the mass that leaves BFS lands only on BFS's two
  nearest centroids: **DFS (geodesic distance 41) and unit-Dijkstra (58)**. It never lands on the far side (A* 71,
  IDDFS 82, bidirectional BFS 95), and banning the next neighbour pushes it one more step along the map. In the
  original request's words, the implemented count moves **to the edge of the banned region**, not to the opposite
  side.
* T2 is only partly consistent (`figures/ban_shift_on_manifold_t2.png`). The mass goes to Bellman-Ford/SPFA, which
  is the **second**-nearest centroid to Dijkstra (42, tied with bidirectional Dijkstra at 43). The nearest
  centroid, Floyd-Warshall (26), receives nothing.
* Ban versus baseline trade-off (BUY row, `results/buy.json`). Hill_cc rises 1.00→2.03 (T1) and 1.00→1.72 (T2), while
  the pass rate falls 0.99→0.76 and 1.00→0.94.

**3. Forecast contest (`results/contest.json`; forecasts hash-committed in `predictions/commit_log.jsonl` before any
ban or removal sample; every event's first sample is after the commit).** The primary events are ban:bfs (no clear
realised mode: compliant DFS 10 vs unit-Dijkstra 8) and ban:dijkstra (realised BF/SPFA). No predictor scored a top-1
hit on a primary event. Mean raw log score on primary events: geodesic −1.43, decoder −1.44, uniform/frequency
(tied, because every survivor has 0 baseline count) −1.56, association −2.59. Over all 5 events, including the 3
exploratory ones: geodesic 1/5 hits (mean log score −1.83), association 1/5 (−2.81), decoder 0/5 (−2.46),
uniform −1.97. The model's own stated ranking of "the most standard alternative" (association: A* for BFS, Dial
for Dijkstra) is the **worst** predictor of where a ban actually sends it, worse than uniform. The geometry of
the read-position states is the best, but only barely beats uniform. With 2 to 5 events, this is descriptive only.

**4. Read-position geometry (`results/gate.json`, `results/manifold.json`, `figures/manifold_t{1,2}.png`).**
* Probes at R, leave-one-frame-out, against 20 shuffled-label refits. Named accuracy is about 0.99 at every layer
  (the name is in context). Named→name-masked transfer peaks at **L27 on T1 (0.67 vs null p95 0.22)** and **L24 on
  T2 (0.54 vs 0.31)**.
* The baseline decoder (the named probe applied to the baseline prompts' h_R) passes on T2 (JS 0.011 vs null p5
  0.030; it predicts 98% Dijkstra). It **fails on T1**: the baseline state decodes as DFS 0.60 / unit-Dijkstra 0.27 /
  BFS 0.12, so the T1 R gate is flagged "R gate failed" and its geometry is descriptive.
* Manifold: kNN graphs are connected without MST edges. MDS stress-1 is 0.22 on both tasks. TwoNN intrinsic
  dimension is **4.2 (T1) and 5.2 (T2), against about 11.9 / 11.6 for column-shuffled nulls**. Geodesic and Euclidean
  distances have Spearman 0.87 / 0.90. On T1, BFS's geodesic neighbours are DFS (41) and unit-Dijkstra (58); A*,
  IDDFS and bidirectional BFS are 71–95 away.

**5. C3 shift decomposition (`results/c3_decomposition.json`, `figures/c3_shares_t{1,2}.png`).** At l* the
ban−mention and ban−list-all shifts at R are mostly residual (61–99% of the squared norm): they are not explained by
the renounce direction (u_ren), the associate or the typical survivor. The u_ren share exceeds the split-half
paraphrase null in only 7 of the 130 (X, band layer, reference) cells (T2 Dial under the mention reference at L23–27,
and T2 bidirectional Dijkstra twice), never under both references. Every X is therefore **inconclusive** under the
pre-declared rule; no "substitution > subtraction" verdict. Lexical cosines with the name's input embeddings and its
unembedding row are about 0 (|cos| ≤ 0.034).

**6. C2 activation removal (`results/c2_removal.json`, `figures/removal_outcomes.png`).** Neither direction check
reached 0.9: held-out d_X AUC at R was 0.89 (T1) and 0.79 (T2), and the best generated-position AUC was 0.66 / 0.76.
So the pre-declared **R-plus-prompt** variant ran: affine ablation of the prompt suffix including R, over a
5-layer (T1) or 7-layer (T2) band. At α = 0.5, 1 and the pre-declared escalation 2.0 it moved **0/50 samples on both
tasks** with the pass rate intact. Under common random numbers, 78–90% of the outputs are byte-identical to their
α=0 twin, the same as the random-direction controls with identical edit norms (80–96%). Verdict: **"untestable
(removal unsuccessful at the tested coefficients)"**.
**Exploratory (post hoc) full variant** (`full_*` arms), which also edits every generated position: at α=2 it is
still 25/25 BFS (T1, pass 19/25) and 25/25 Dijkstra (T2). At α=4 the d_X edit destroys generation (25/25 no code on
both tasks). The random direction at α=4 keeps 18/25 BFS on T1 with 0 passing, and gives 20/25 no code on T2. The
removal never reroutes the choice: it either does nothing or breaks the model. This matches the field warning that
steering can be "indistinguishable from random perturbation".

**7. Labels are trustworthy.** Labeller gate (`results/labeller_gate.json`): runtime and AST agree on 100% of
references. κ(runtime, AST) is 0.90 / 0.94 and runtime vs adjudicated is 0.96 / 0.92 on the gold sets. Two judge
models agreed on 100% / 96% of gold items. Total OpenRouter spend for this artifact: ≈ $0.09.

**Scope.** One model (Qwen3-8B), two tasks, T=1.0, thinking off. There are 2 primary ban events, 3 exploratory ones
and 2 removal events, so every number above is descriptive (Wilson intervals in the JSON files, no p-values). Full
deviations from the plan are in `results/deviations.json`, mirrored in `method_out.json` → `metadata.deviations`.

## Deviations and caveats (full list: `results/deviations.json`)

* **Engine.** vLLM 0.32 could not start: Triton needs a C compiler and the container has none. Every phase therefore
  samples with batched HF `generate` (bf16, sdpa, left padding) on the *same token ids*, with per-batch seeds. That
  makes the engine identical across all phases, including the hooked α=0 baseline. In Phases A and C, rows still
  running at 448 tokens are continued in a later batch (same distribution, different random stream).
* **Hardware.** One NVIDIA L4 (23 GB), 6 CPUs. The GPU phases took about 2.2 h in total (A 46 min, B 35, C 10, D 19, extensions 22).
* **Succession.** Both modal bans fell below 50% compliance (a pre-declared *ban failure*), so the pre-declared
  succession stopped. The three step-2 events in the contest were sampled afterwards as **exploratory** (forecasts
  committed in Phase B) and are reported separately (`aggregate_primary` vs `aggregate_all`).
* **Present-minor strata are empty.** Both baselines are 100% modal, so frequency forecasts are uniform over the
  survivors. They are recorded as **tied** and excluded from top-1 hit counts, while their log score is the
  uniform reference.
* **R gate (T1) failed on the decoder criterion only.** The transfer criterion passed, so l* stays the transfer
  argmax and T1 geometry carries the flag "R gate failed".
* **Removal variant.** Both direction checks failed (AUC < 0.9 at R and at generated positions), so the pre-declared
  R-plus-prompt variant was run. The full variant, which edits generated positions, appears only as post-hoc
  exploratory arms (`full_*`).
* **Name-masked probes.** Forced prompts carry the algorithm name. Masked transfer, Procrustes agreement
  (disparity 0.18 / 0.25) and lexical cosines mitigate this, but a "manifold of names" reading cannot be fully
  excluded at R.
* **Dropped arms.** The external-model elicitation and the LOCO distribution decoder (pre-declared drop order 1 and
  5) were dropped.
* **Hook test.** The decode-index check against `cache_position` could not be read: transformers 5.19 does not pass
  `cache_position` to `Qwen3Model.forward` as a keyword argument. Decode positions are tracked with an internal
  step counter instead, and the pre-declared variant does not edit decode positions. All other hook tests pass
  (`results/phaseD_tests.json`): α=0 logits are identical, post/pre projection is < 1e-6, and the random-edit norm
  ratio is exactly 1.
* **Labeller.** The LLM judge (`anthropic/claude-haiku-5.5`) labels programs on which runtime and AST disagree or
  are unsure (101 of 560 Phase-A programs on T1, 129 of 500 on T2).

## Testing-plan outcomes

| # | Check | Outcome (where) |
|---|---|---|
| 1 | every catalogue reference passes the hidden suite 3/3; wrong programs fail | pass. The off-by-one path, the hop-count "distance" and brute-force enumeration all fail (`logs/build_tests.log`) |
| 2 | labeller unit tests: references, recursive/iterative variants and 5 mutants | runtime and AST both 19/19 (`labeller/unit_test_results.json`) |
| 3 | suffix token ids identical across all conditions; R token | asserted at build time; L_s = 123 / 119; R = `\n\n` after `</think>` (`prompts/suffix_meta.json`) |
| 4 | mini generation before scaling | 24-sample mini stage, then staged batches with timing (`logs/timing.jsonl`) |
| 5 | hook tests | α=0 logits identical (max diff 0.0); post/pre projection ≤ 9e-7; random/d_X edit-norm ratio 1.000; h_R alone vs in a left-padded batch has cosine ≥ 0.9998 (`results/phaseD_tests.json`, `results/gate.json`) |
| 6 | teacher forcing re-tokenisation | 100% match (`results/geometry_b.json`) |
| 7 | shuffled-label probe accuracy ≈ 1/K | null means 0.16–0.19 (K=6, 1/K = 0.17) and 0.19–0.22 (K=5, 1/K = 0.20) (`results/gate.json`) |
| 8 | geodesic ≥ Euclidean, symmetric matrix; synthetic decomposition 0.36/0.64 | pass (`results/manifold.json` → `checks`, `results/c3_decomposition.json` → `synthetic_test`) |
| 9 | commit integrity | Phases C/D refuse to run on a hash mismatch; every scored event's first sample is after the commit (`results/contest.json`) |
| 10 | confirmation signals | baseline collapse visible; forced manipulation 0.94 / 0.74 overall (≥ 0.7); the modal bans were below 50% compliance (ban failure, so the succession stopped); the α=1 removal moved 0/8, so the pre-declared α=2 escalation ran |
| 11 | close-out | `method_out.json` validates against `exp_gen_sol_out`; every file is < 100 MB (the suffix-mean cache was split per mode) |

## What was done (pipeline)

| Stage | Script | What it does |
|---|---|---|
| tasks | `tasks/tasklib.py`, `tasks/references.py`, `tasks/harness.py` | ≥40 hidden tests per task (41/42), catalogue references (all pass 3/3), per-test limit `max(1 s, 10×` slowest reference), sandboxed runner (`python -I`, RLIMIT_AS 2 GB, itimer, fail-fast, hard kill); deliberately wrong programs fail |
| labeller | `labeller/rules.py`, `labeller/label.py` | runtime tracer (heapq / deque / queue / list-pop / recursion / start re-expansion / line counts on 3 probe inputs) + AST rules; when they disagree or are unsure, a blind LLM judge (`anthropic/claude-haiku-5.5`, comments stripped) |
| labeller gate | `labeller/run_label_a.py` | gold set = references + 20 Phase-A programs per task, two judges (`claude-haiku-5.5`, `gpt-4.1-mini`) + resolver (`deepseek-v4.1-flash`) |
| prompts | `prompts/build_prompts.py` | every condition × paraphrase, chat template (thinking off), token ids hashed; asserts identical suffix ids per task (L_s = 123 / 119); R = last prompt token (`\n\n` after `</think>`) |
| Phase A | `gen/phase_a.py` | baseline N=200/task, forced named 30×1/mode, forced name-masked 30×1/mode, association elicitation 20 rankings per (task, X) |
| Phase B | `hf/phase_b.py` | h_R for 1330 prompts × layers 8..28; R gate (leave-one-frame-out probes, 20 shuffled nulls, named→masked transfer, baseline decoder); l* and band; centroids; geodesic manifold; d_X and affine anchors (prompt suffix + teacher-forced generated positions); C3 basis; **hash-committed forecasts** for 45 events |
| Phase C | `gen/phase_c.py` | prompt bans N=100 per event, labelled online; succession rule |
| Phase D | `hf/phase_d.py` | affine mean-anchored directional ablation of the modal mode over the band (hooked α=0, d_X at α 0.5/1/2, two random directions with identical edit norms, common random numbers) |
| ext | `gen/phase_c_ext.py`, `hf/phase_d.py --exploratory-full` | optional mention:modal arm; **exploratory** (already committed) step-2 bans; **exploratory** full-variant removal |
| analysis | `analysis/analyze.py`, `analysis/geometry.py` | summaries, gate figure, geodesic-MDS manifold, contest, C3 decomposition, C2 removal, BUY row, `method_out.json` |

`method.py` runs the stages in order (`python method.py --from <stage>` / `--only <stage>`); each GPU phase is
its own process.

## Layout

```
method.py                 entry point (stage runner)
common.py                 task specs, catalogue, display names, prompt templates, helpers
pyproject.toml            dependencies (exact versions used)
tasks/                    hidden_tests_t1.json, hidden_tests_t2.json, references.py, harness.py, tasklib.py
labeller/                 rules.py (runtime + AST), label.py (judge + combination), run_label_a.py (gate),
                          test_labeller.py + unit_test_results.json, gold_set.json (adjudicated gold items)
prompts/                  build_prompts.py, prompts.jsonl (every prompt with token ids + sha256), suffix_meta.json
gen/                      hf_engine.py (batched HF sampling), phase_a.py, phase_c.py, phase_c_ext.py, vllm_engine.py
hf/                       phase_b.py (geometry + commit), phase_d.py (hooked removal)
analysis/                 analyze.py, geometry.py, audit_rederive.py (independent re-derivation of headline numbers)
data/                     samples_phaseA.jsonl, samples_phaseC.jsonl, samples_phaseD.jsonl (every labelled program),
                          raw_phaseA.jsonl (unlabelled), elicit_phaseA.jsonl (association rankings)
cache/                    hR_layer{8..28}.npy + hR_index.jsonl (read-position states for every prompt),
                          suffix_means_t{1,2}_<mode>.npy, directions_t{1,2}.npz, anchors_t{1,2}.npz, basis_t{1,2}.npz,
                          hR_ablated_t{1,2}.npz
predictions/              predictions_v1.json + commit_log.jsonl (hash-committed before any C/D sample)
results/                  gate.json, geometry_b.json, phaseA_summary.json, labeller_gate.json, phaseC_events.json,
                          phaseD_tests.json, summaries.json, association.json, contest.json, c3_decomposition.json,
                          c2_removal.json, manifold.json, manipulation_sensitivity.json, buy.json, run_summary.json,
                          deviations.json
figures/                  manifold_t{1,2}, ban_shift_on_manifold_t{1,2}, gate_per_layer, c3_shares_t{1,2},
                          removal_outcomes (.png + .pdf)
reproducibility.md        exact environment, commands, seeds, failures and expected numbers
full_/mini_/preview_method_out.json  size variants of method_out.json (aii-json format script)
method_out.json           exp_gen_sol_out format: t1_grid_path, t2_weighted_sp (one example per program),
                          contest_events (committed distributions vs realised outcomes)
logs/                     per-phase logs, timing.jsonl, openrouter_spend.jsonl, todo.md
```

All kept artifacts (`cache/`, `data/`, `results/`, `predictions/`, `figures/`) stay on the run's volume at
these relative paths, and every file is below 100 MB. The Phase-B-only activations, `cache/hR_layer{8..20}.npy`
and `cache/suffix_means_*.npy` (about 370 MB), are excluded from the published repository and stay **only on the
run's volume**, where the next round can reuse them without a GPU. Everything the analysis reads is published:
`cache/hR_layer{21..28}.npy`, `hR_index.jsonl`, `basis_*`, `directions_*`, `anchors_*` and `hR_ablated_*`.
`reproducibility.md` gives the exact rebuild steps. `results/audit_rederive.json` re-derives 99 headline numbers
through independent code (`analysis/audit_rederive.py`) with 0 mismatches. `scratch/` holds the ad-hoc test and orchestration
scripts used during the run (labeller spot checks, CPU unit tests of Phase B helpers, the phase-chaining shell
scripts).

## How to run

```bash
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python method.py                 # full pipeline (~3 h on one NVIDIA L4)
.venv/bin/python method.py --only analysis # re-run the CPU analysis from the kept data/ cache/ predictions/
```

The model is `Qwen/Qwen3-8B` from the Hugging Face Hub (downloaded to the run's shared HF cache, not into
this directory). Judge calls go through OpenRouter (`OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY`). The total
judge spend for this artifact is in `logs/openrouter_spend.jsonl`.

## Restoring removed files

Paths marked `delete` in `.aii/manifest.yaml` are removed after the round. Restore them with:

| Removed path | How to restore |
|---|---|
| `.venv/` | `uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` |
| `__pycache__/`, `gen/__pycache__/`, `labeller/__pycache__/`, `tasks/__pycache__/`, `analysis/__pycache__/`, `hf/__pycache__/` | Python bytecode, recreated automatically on the next import or run (e.g. `.venv/bin/python method.py --only analysis`) |

Not stored in this directory, or not published to the repository:

| Path | How to obtain |
|---|---|
| model weights | `.venv/bin/hf download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218` (Hugging Face cache, never in this directory) |
| `cache/hR_layer{8..20}.npy`, `cache/suffix_means_*.npy` (kept on the run volume, excluded from the published repository; only Phase B reads them) | `.venv/bin/python method.py --only phase_b` (back up `predictions/` first: Phase B rewrites the commit) |
