# Brainstorm steering to diversify algorithms: a de-commitment screen on Qwen3-8B

This repository screens **alternate 1 (de-commitment)** of the algorithm-monoculture hypothesis. We take
**Qwen3-8B** with thinking off and two path-search tasks that have known algorithm catalogues. We build a
*list-versus-implement* difference-of-means direction `d_dc` at the read position R (the last prompt token).
We add it as `c·||h||·d̂` at R and at every generated token, then ask whether this raises the
**correctness-conditioned diversity** of the algorithms the model writes (the Hill-1 number of labels among
programs that pass hidden tests). Every arm, method and baseline alike, runs through the same scaffold,
decoding (T = 1, top-p = 1, top-k off) and labeller.

**Screen verdict: `PARTIAL`** (decided by the pre-registered rules in `results/preregistration.json`).

* **T1 (grid path, `solve(grid, start, goal)`).** The model writes BFS 100 % of the time (N = 200).
  Steering never changes this. At the correctness-preserving `c* = 0.1` the arm is 98 % BFS. At
  c = 0.25 the pass rate falls to 0.57, and every program that still passes is BFS. Hill-1 = 1 at every c.
  S_flat fails.
* **T2 (weighted shortest path, `solve(n, edges, s, t)`).** At `c* = 0.25` the pass rate is 0.78 against
  0.95 at c = 0. Correct programs shift from Dijkstra (88 Dijkstra / 7 Bellman-Ford) to mostly
  Bellman-Ford (54 / 23). Rarefied Hill-1 gains **+0.65** (paraphrase-cluster 90 % CI [0.31, 0.97]), so
  S_flat holds on T2. The gain is **not direction-specific**, however. Random direction `rand1` at the
  same strength also moves Dijkstra toward Bellman-Ford (+0.59, CI [0.21, 0.85]), and
  dc − rand1 = +0.07, CI [−0.26, 0.39]. The gain does exceed `rand2` (+0.70 [0.38, 1.01]) and the
  variable-name placebo (+0.47 [0.01, 0.84]). S_specific fails.
* **Prompting.** The enumeration prompt ("list 10 approaches, then implement one") changes nothing on
  either task (T1 100 % BFS; T2 ΔHill −0.08). The modal ban buys diversity much more cheaply than steering
  on T2 (+0.79 [0.60, 0.90] at a 1.5-point pass cost, against +0.65 at a 17-point cost for steering). Most
  banned samples still use the banned algorithm (T1 46/64 correct programs are BFS; T2 49/87 are
  Dijkstra).
* **Commitment test (forward pass only).** Ban-minus-mention moves R along `d_dc` by **+0.04 / +0.05**
  of the LIST–IMPLEMENT distance (T1 / T2). That is outside the pre-registered paraphrase-split null band
  (±0.024), so the pre-registered label is "de-commits". The audit found that band too narrow. Exact
  permutation tests give p = 0.021 / 0.007 (label permutation) and 0.025 / 0.016 (paired sign-flip), with
  8 of 10 pairs positive on each task. The pre-registered band test reported p = 0.0005. The direction of
  the shift holds at α = 0.05, but the evidence is modest. The shift is also tiny next to the enumeration
  positive control
  (+0.54 / +0.58), and its share along `d_dc` is unremarkable against a top-50-PC null (78th / 87th
  percentile). This is decodability-level evidence only.
* **PREDICT row.** On T2 the de-committed forecast scored best on the ban samples: mean log score
  −0.058 against −0.219 for the vLLM frequency forecast and −1.41 for uniform, with a top-1 hit on
  Bellman-Ford. That is one event in which all 38 compliant samples carry one label, so it is a forecast
  record, not evidence of a mechanism. On T1 every forecast was degenerate (no non-BFS correct sample
  existed anywhere before the ban), so they tie.

## Independent audit of the headline numbers

`analysis/audit_rederive.py` recomputes the headline numbers straight from `data/raw/*.jsonl` and the
per-sample label files, through different code (scipy entropy, a vectorised paired cluster bootstrap).
Output goes to `results/audit_rederivation.json`.

* Every pass rate and label count in the table below matches.
* T2 rarefied ΔHill is +0.651 [0.32, 0.98], and dc − rand1 is +0.07 [−0.24, 0.40].
* δκ(T2) is 0.0527 and the T2 PREDICT dc log score is −0.0584.
* Shuffle checks behave as a valid test should:
  * With arm labels permuted within paraphrase, all 5 shuffled ΔHill CIs include 0.
  * `analysis/audit_commitment_perm.py` gives the exact permutation p-values quoted above
    (`results/audit_commitment_perm.json`).
* Not independently re-derived: the per-sample labels and pass/fail outcomes themselves. These come from
  the sandbox labeller, which is validated by R0 and the labeller gate instead.

## Main numbers

Pass rate with 95 % Wilson CI. Hill-1 is computed over correct programs. ΔHill is rarefied to a common
depth, with a paraphrase-cluster 90 % CI against the reference: HF c = 0 for steering arms, the vLLM
baseline for prompt arms.

| task | arm | pass | correct-label counts | ΔHill (rarefied) |
|---|---|---|---|---|
| T1 | vLLM baseline (N=200) | 1.00 [0.98, 1.00] | bfs 200 | — |
| T1 | HF c=0 (hook, zero) | 1.00 | bfs 100 | — |
| T1 | dc c*=0.1 | 0.98 | bfs 98 | 0.00 [0.00, 0.00] |
| T1 | dc c=0.25 | 0.57 | bfs 57 | 0.00 |
| T1 | rand1 / rand2 / placebo / breadth @c* | 0.98 / 1.00 / 1.00 / 0.99 | all bfs | 0.00 |
| T1 | enumerate | 1.00 | bfs 100 | 0.00 |
| T1 | ban: BFS | 0.64 | bfs 46, dfs 16, dijkstra_unit 2 | +0.99 [0.55, 1.34] |
| T1 | succession: no BFS or DFS | 0.88 | bfs 65, dijkstra_unit 13, dfs 7, astar 3 | +1.27 [0.64, 1.80] |
| T2 | vLLM baseline (N=200) | 0.89 [0.83, 0.92] | dijkstra 169, bf/spfa 8 | — |
| T2 | HF c=0 | 0.95 | dijkstra 88, bf/spfa 7 | — |
| T2 | **dc c*=0.25** | 0.78 [0.69, 0.85] | **bf/spfa 54, dijkstra 23, other 1** | **+0.65 [0.31, 0.97]** |
| T2 | dc c=0.375 (bisection) | 0.67 | bf/spfa 47, dijkstra 19 | +0.65 [0.29, 0.94] |
| T2 | rand1 @c* | 0.79 | dijkstra 53, bf/spfa 26 | +0.59 [0.21, 0.85] |
| T2 | rand2 @c* | 0.87 | dijkstra 82, bf/spfa 5 | −0.05 [−0.31, 0.20] |
| T2 | placebo (long vs short names) @c* | 0.66 | dijkstra 60, dial 3, bf 2 | +0.19 [−0.30, 0.70] |
| T2 | breadth (list vs name-one) @c* | 0.60 | bf/spfa 31, dijkstra 28, dial 1 | +0.85 [0.46, 1.17] |
| T2 | T1's d_dc (transfer, N=50) @c* | 0.72 | bf/spfa 28, dijkstra 8 | +0.40 [−0.01, 0.69] |
| T2 | enumerate | 0.82 | dijkstra 80, bf/spfa 2 | −0.08 [−0.27, 0.13] |
| T2 | ban: Dijkstra | 0.87 | dijkstra 49, bf/spfa 38 | +0.79 [0.60, 0.90] |
| T2 | succession: no Dijkstra or BF | 0.68 | bf/spfa 34, dijkstra 33, other 1 | +0.93 [0.66, 1.17] |

At c ≥ 1.0 every task collapses: pass 0, broken format, and 28–85 % of samples truncated. Per-sample flips
against c = 0 under common random numbers (T2): dc 0.66, rand1 0.42, placebo 0.22, rand2 0.18. Hill-2 is
reached on T2 at c ≈ 0.40 for a 34.5-point pass-rate cost. Hill-3 is not reached in the tested range.
Full tables: `results/buy_table.csv`, `results/condition_summaries.json`.

## Gates (all reported in `method_out.json → metadata.gates`)

* **R0.** All 12 catalogue references pass 100 % of the hidden tests (43 for T1, 39 for T2). All 6
  deliberately wrong programs fail. Runtime **and** AST both give every reference its own label.
* **Labeller gate.** Gold set = 10 baseline + 6 steered programs + references + 2 off-catalogue programs
  per task. Two judges (gemini-2.5-flash-lite, gpt-4.1-mini) label it, with claude-haiku-4.5 resolving
  their disagreements. T1: κ(runtime, AST) = 1.00, runtime-vs-adjudicated agreement 1.00. T2: κ = 0.82
  (95 % CI [0.61, 1.0]), runtime-vs-adjudicated 0.92, final pipeline label vs adjudicated 1.00. T2 passed
  only after labeller revision round 2 (see deviations).
* **Engine check (vLLM baseline vs HF c=0).** T1 is identical (all BFS). T2: TV = 0.03, Fisher p = 0.40,
  pass-rate difference CI [−0.14, 0.01]. The check passes, so cross-engine comparisons are allowed.
* **Hook tests.** The layer index is exact (hook output = `hidden_states[L]`). At c = 0 the hook is a
  no-op (token-identical output). The hook fires once at prefill and then once per decode step, and the
  norm and cosine change at c = 0.5 match the analytic values.
* **Commitment positive control.** The enumerate shift lies far outside its null band on both tasks.
* **Sampling and scaffold.** Every vLLM `SamplingParams` repr and the HF generation kwargs are logged and
  asserted (T = 1, top-p = 1, top-k off, no penalty), so neither inherits Qwen3's 0.6 / 20 / 0.95
  defaults. The CPU checks in `results/unit_tests.json` all pass (specs are 140 / 120 tokens).
* **vLLM same-seed determinism (FAILED on T1).** Two calls with the same per-request seed gave identical
  text on T2 but not on T1 (`results/vllm_determinism.json`). The likely cause is prefix-cache or
  batch-shape numerics at T = 1. vLLM arms are therefore reproducible in distribution, not bit for bit.
  Every common-random-number analysis (flips, paired specificity) uses only HF arms, whose c = 0 no-op
  test is token-identical.

## Direction diagnostics (L* = 18 of 36)

Held-out AUC saturates at 1.00 on every layer from 9 to 28. L* = 18 is the tie-break by held-out d′
(8.55). The stage-10 mini-sweep at L* ± 4 kept L* (c = 1.0 changed 20/20 samples at L*). At L*:
‖d‖/‖h_R‖ = 0.21 (T1) and 0.19 (T2); split-half cosine 0.99; per-pair difference consistency 0.77;
cross-task cosine 0.98; cos(d_dc, d_breadth) = 0.53/0.55; cos(d_dc, d_placebo) = −0.08/−0.04;
cos(d_dc, enumerate shift) = 0.59/0.62 (`results/direction_diagnostics.json`).

## Layout

| path | what |
|---|---|
| `method.py` | end-to-end orchestrator (stages skip work already on disk, GPU stages run in their own processes) |
| `common.py` | constants (specs, catalogues, lexicon), paths, seeds, logging, resource helpers |
| `env.sh` | environment for GPU stages (offline HF, engine caches kept inside the workspace) |
| `prompts/make_paraphrases.py`, `prompts/paraphrases.json` | all instruction sets (baseline 20, enumerate 10, ban 10, mention 20, listall 10, 5 direction frames × 50) |
| `prompts/scaffold.py` | chat-template prompt builder, with the identical-suffix assertion before R |
| `tasks/t1_grid.py`, `tasks/t2_wsp.py` | test generators, checkers, tracer probes |
| `tasks/tests_T1.json`, `tasks/tests_T2.json` | hidden tests with per-case limits (`max(1 s, 10 × slowest reference median)`) |
| `tasks/references/` | 12 catalogue reference implementations (Bellman-Ford and SPFA share one label) |
| `tasks/wrong/` | deliberately wrong programs for R0 |
| `tasks/build_tests.py` | builds tests and limits, runs R0 and the labeller unit tests → `results/r0_gate.json` |
| `labeller/harness.py` | code extraction, `format_ok`, `enumerated`, `names_mentioned` |
| `labeller/runner.py` | sandbox (`python -I`, RLIMIT_AS 2 GB, per-test alarms): hidden tests, then the traced re-execution on the probes |
| `labeller/tracer.py` | instrumented heapq / deque / queue / bisect / traced lists, plus `sys.setprofile`; runtime rules |
| `labeller/ast_rules.py` | independent static rules |
| `labeller/label.py`, `labeller/daemon.py` | combine runtime + AST, caches, background labelling during GPU runs |
| `labeller/judge.py`, `labeller/gate.py` | OpenRouter judge for disagreements (with a cost cap and 403 stop); labeller gate |
| `gpu/hf_states.py` | HF pass 1: R-states for every frame and condition → `cache/hR_*.npy` |
| `gpu/vllm_gen.py` | vLLM sessions s1 (baseline, enumerate), s2 (ban, mention, behind the commit guard), s3 (succession) |
| `gpu/hf_steer.py` | steering hook, CRN batches, stage 10, layer rule, dc grid, c* + bisection, controls, extensions |
| `analysis/directions.py` | directions, layer selection, diagnostics, commitment test |
| `analysis/forecast.py` | modal modes, hash-committed forecasts, succession plan, sha verification |
| `analysis/stats.py`, `analysis/analyze.py` | statistics; every result table and the screen verdict |
| `analysis/figures.py`, `figures/` | fig1 dose-response, fig2 label distributions, fig3 TV vs ΔHill, fig4 commitment κ, fig5 layer profiles |
| `analysis/method_out.py`, `method_out.json` | output in the `exp_gen_sol_out` schema (one example per CRN slot; `output` = HF c=0 label, `predict_<arm>` = `label\|pass/fail`) |
| `analysis/record_meta.py`, `analysis/peek.py` | protocol/deviation records; quick per-arm summary |
| `analysis/audit_rederive.py`, `analysis/audit_commitment_perm.py` | independent re-derivation of the headline numbers + shuffle / exact-permutation checks → `results/audit_*.json` |
| `full_method_out.json`, `mini_method_out.json`, `preview_method_out.json` | full / 3-per-dataset / truncated variants of `method_out.json` |
| `pyproject.toml`, `requirements.txt` | the 177 exact pins of the environment that produced the results |
| `reproducibility.md`, `restore.sh` | step-by-step reproduction (commands actually run, seeds, runtimes, expected numbers); environment + model restore |
| `tests/test_screen.py` | CPU checks: specs ≥ 50 tokens, identical suffix / R token over 930 prompts, empty think block, forecast guard, sha256 re-verification, statistics self-test → `results/unit_tests.json` |
| `gpu/vllm_determinism.py` | same per-request seed → identical vLLM text → `results/vllm_determinism.json` |
| `data/raw/*.jsonl` | raw generations per engine × task × condition |
| `data/samples.jsonl` | 2,940 labelled samples in the shared per-sample schema |
| `directions/` | `d_dc_<task>_L<l>.npy` (l = 8..28), random, placebo and breadth directions, metadata |
| `forecast/` | `predict_<task>_{ban1,succ2}.json` and `commit_log.jsonl` (sha256 of each forecast, committed before its samples existed) |
| `gold/gold_set.jsonl` | adjudicated gold set with judge rationales |
| `results/` | gates, `preregistration.json`, `protocol.json`, `deviations.json`, `cstar.json`, `buy_table.{json,csv}`, `predict_row.json`, `commitment_test.json`, `engine_check.json`, `flips.json`, `dose_response.json`, `move_vs_flatten.json`, `screen_verdict.json` |
| `cache/` | `hR_*.npy` R-states (150 MB); label / test / judge caches (`labels_round1/`, `tests_round1/` = audit trail of revision round 1) |
| `logs/` | stage logs, `timing.jsonl`, `openrouter_cost.jsonl` (total $0.06) |

The kept artefacts (`cache/hR_*.npy`, `directions/`, `data/`, `forecast/`, `gold/`, `results/`) stay on
the run's storage volume at these relative paths. The content-addressed label, test and judge caches and
the R-state arrays are excluded from the published repository and remain on the volume only.

## How to run

```bash
uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r requirements.txt
hf download Qwen/Qwen3-8B                       # into the HF cache (HF_HOME); ~16 GB
.venv/bin/python method.py                      # every stage; resumes from whatever is on disk
.venv/bin/python method.py --stages analyze     # CPU-only re-analysis of the stored samples
```

Hardware used: one RTX A4500 (20 GB), 11 CPUs, 57 GB RAM. GPU time was about 2.1 h: HF R-states 1.6 min;
vLLM sessions 28 + 9 + 6 min, including 3–13 min of engine start-up; HF steering 79 min. The OpenRouter
judge cost $0.06. Python 3.12, torch 2.8.0+cu128, transformers 4.57.1, vLLM 0.11.0.

## Deviations from the plan (all logged in `results/deviations.json`)

* vLLM ran with `enforce_eager=True` at `gpu_memory_utilization` 0.95. The compiled 0.92 configuration
  crashed because torch inductor finds no C compiler on this machine.
* The model weights were read from the run's shared HF cache, not from a workspace `hf_cache/`, so no
  duplicate 16 GB copy exists. GPU processes run without RLIMIT_AS, because the CUDA driver fails under
  it.
* There were two labeller revision rounds, and everything was re-labelled after each.
  * Round 1 (before the gate) fixed three problems:
    * T2 `(dist, node)` FIFO items were being read as the node.
    * Bellman-Ford over adjacency lists and arg-min-scan Dijkstra were falling to `other` without
      reaching the judge.
    * The Q2 probe weights were scaled ×10.
  * Round 2 (after the first gate failed on T2, 0.83) made three rule changes:
    * SPFA must re-process a re-enqueued node.
    * The runtime Floyd-Warshall rule needs a real triple loop.
    * A runtime rule was added for heap-less array Dijkstra.
* Decisions use the paraphrase-cluster bootstrap; the sample bootstrap is reported alongside. Steering
  arms are resampled jointly with HF c = 0, because they share prompts and seeds. Prompt arms are
  resampled independently of the baseline, because their paraphrase texts differ. Hill-1 is
  rarefied to 0.85 × the smaller correct count of each comparison, so that bootstrap replicates stay
  defined.
* `listall` is a held-out "list all approaches, do not implement" frame. Its κ is 0.82/0.81, which shows
  the direction generalises.
* The forecasts were hash-committed and enforced by a generation guard. They were not git-committed,
  because the workspace is not a git repository.

## Limitations

The screen covers two tasks and one model, and each claim is per task. T1 has no diversity at all: the
baseline, enumeration and every steering arm are 100 % BFS. The T2 effect is a single Dijkstra →
Bellman-Ford shift. Because one of the two random directions reproduces it, this looks more like a
fragile commitment exposed by any perturbation of about 25 % of the residual norm than like a specific
"de-commitment" axis. The commitment test is decodability-level evidence. The PREDICT row rests on one
informative event.

## Restoring removed files

These manifest entries are deleted after the round. Each comes back with one command:

| removed path | restore with |
|---|---|
| `.venv/` | `uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r requirements.txt` |
| `__pycache__/`, `analysis/__pycache__/`, `labeller/__pycache__/`, `prompts/__pycache__/`, `tasks/__pycache__/`, `tasks/references/__pycache__/`, `gpu/__pycache__/` | Python bytecode, recreated automatically on import (e.g. `.venv/bin/python -c 'import common'`) |

The model weights were never stored in this folder; they live in the Hugging Face cache. Fetch them with
`.venv/bin/hf download Qwen/Qwen3-8B` (or `huggingface-cli download Qwen/Qwen3-8B`). `restore.sh` runs
both the environment and the model steps.
