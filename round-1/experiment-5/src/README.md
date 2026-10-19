# Did instruction tuning cause the algorithm-choice collapse? (Qwen3-8B-Base vs Qwen3-8B)

Screen of **alternate 4 — "instruction tuning installed the collapse"** on two path-search coding tasks:

* **T1** unweighted grid path (`solve(grid, start, goal)`, any valid path) — catalogue: `bfs, dfs, bidir_bfs, iddfs, astar_greedy, dijkstra_unit`
* **T2** weighted directed shortest path (`solve(n, edges, s, t)`) — catalogue: `dijkstra, bellman_ford_spfa, bidir_dijkstra, floyd_warshall, dial`

Every generated program is executed on ≥44 hidden tests per task (47 / 46 cases, per-case wall-clock limit = max(1 s, 10× reference)),
and labelled by a **runtime-signature labeller** (instrumented heaps/deques/list pops, recursion depth, grid read order, edge-list passes,
line-count scaling) plus an **AST labeller**; when they disagree a **blind LLM judge** (`google/gemini-2.5-flash-lite`, sees only spec +
catalogue + code) decides. Decoding everywhere: T = 1.0, top-p 1.0, no top-k, thinking off, max 1024 new tokens.

## What was done

1. **2×2 weights × format decomposition** (vLLM 0.11, bf16):
   `base_tf` (Qwen3-8B-Base, template-free docstring prompt), `base_chat` (base model on the *instruct* chat template),
   `instruct_chat` (Qwen3-8B chat, `enable_thinking=False`), `instruct_tf` (instruct model on the template-free prompt);
   10 neutral paraphrases (P0..P9). Same task text, same sampling, token-identical chat prompts across tokenizers (asserted for all 120).
2. **Modal-ban arms**: `base_tf_ban` (A3) and `instruct_chat_ban` (C1) with 10 ban phrasings (ban:BFS on T1, ban:Dijkstra on T2).
3. **Hash-committed forecast (PREDICT)** of where the instruct model lands under the ban, made from the base model's template-free
   distribution and committed (sha256 + git) **before** C1 was sampled; scored by top-1 hit and log score against uniform / typicality references.
4. **Sharpening direction**: δ_L = mean over 50 paraphrases of h_R(instruct) − h_R(base) on identical chat-templated tokens (R = last prompt
   token), every layer; diagnostics (split-half reliability, task generality, massive-activation share, cos with teacher-forced generated-position
   difference, logit lens).
5. **Steering** (HF, custom common-random-number sampler): band-incremental subtraction over decoder layers 8–28 (cumulative shift after layer L
   = c·δ_L) at R and at every generated position, c ∈ {0.5, 1.0, 1.5} with a hooked c = 0 control; cumulative-norm-matched random directions at c*;
   per-sample flips on coupled seeds; manipulation check (gap closed at R). Plan fallback 6 (single-layer δ₁₈ at layer 18) and an extension
   ablation (**R-only**: subtract only at R, not at generated positions, with an R-only random control).

## Layout

| path | what |
|---|---|
| `method.py` | single entry point: `--all` runs the whole pipeline (each GPU phase is its own process), `--assemble` writes `method_out.json` |
| `src/common.py` | paths, model ids, constants, helpers (Wilson CI, seeds, logging) |
| `src/prompts.py` | frozen prompt set: specs, P0..P49 neutral lead-ins, B0..B9 ban lead-ins, chat + template-free prompts, token-identity checks → `data/prompts.json` |
| `src/tasks.py` | seeded hidden-test generators, ground truth (BFS; Dijkstra cross-checked against Floyd-Warshall), checkers → `data/tests/` |
| `src/harness.py` | sandboxed scoring subprocess (3 GB RLIMIT_AS, 256 MB thread stack, per-case wall-clock limits, stop at first failure) |
| `src/calibrate.py` | time-limit calibration + harness probes (infinite loop, 4 GB alloc, bad step, sys.exit, weight-ignoring BFS) |
| `data/refs/` | catalogue reference implementations (15) and labeller variants / mutants (10) |
| `src/extract.py` | program extraction from chat responses (first fenced block with `def solve`) and template-free completions (trim-to-parse) |
| `src/labeller_runtime.py` | runtime-signature labeller (tracing subprocess) |
| `src/labeller_ast.py` | AST feature flags + ordered rules |
| `src/labeller_gate.py` | labeller gate on references + mutants → `results/labeller_gate.json` |
| `src/judge.py` | blind OpenRouter judge with budget guard and cache (`runs/judge_cache.jsonl`) |
| `src/gen_vllm.py` | vLLM generation phases A (base), B (instruct), C (instruct ban; refuses without the PREDICT hash), A_EXT (power extension) |
| `src/label_score.py` | extract → score → runtime label → AST label → judge → final label, per sample → `runs/labelled_*.jsonl` |
| `src/predict_commit.py` | PREDICT commit (`predictions/predict_modal_ban.json`, `predictions/hash_log.txt`, git record in `predictions/.commit_git`) |
| `src/acts_hf.py` | residual states at R / teacher-forced positions, δ, band vectors, diagnostics → `activations/`, `results/sharpening_direction.json` |
| `src/steer_hf.py` | steering arms, hook unit tests (`results/hook_tests.json`), manipulation check (`results/manipulation_*.json`) |
| `src/analysis.py`, `src/stats_utils.py` | all statistics (Hill numbers, paraphrase-cluster bootstrap, permutation χ², JS, kappa, BUY/PREDICT rows, figures) → `results/analysis.json` |
| `src/report.py` | renders `results/summary.md` (the tables below) |
| `runs/samples.jsonl` | every sample in the shared row schema (task, condition, paraphrase_id, sample_id, model, decoding, label, labeller_source, passed, wall_s, code_sha256, code + arm/template/steer/format flags) |
| `runs/raw_*.jsonl`, `runs/labelled_*.jsonl` | raw generations / labelled rows per arm |
| `activations/` | `{base,instruct}_{t1,t2}_R.npy` [50,37,4096] fp16, `*_gen.npy` [20,37,4096], `delta_*.npy`, `steer_*.npy` (band increments, layers 8–28) — kept on the run volume (each file < 100 MB, so also published) |
| `predictions/` | committed forecast + hash log + commit record |
| `results/` | analysis JSON, summary tables, calibration, gate, hook tests, manipulation checks, deviations, judge cost |
| `figures/` | label bars per arm, steering curves, per-layer direction diagnostics, flip heatmaps (PNG + PDF) |
| `method_out.json` | experiment output in the `exp_gen_sol_out` schema: `metadata` = every analysis above, `datasets` = one dataset per task with one example per generated sample |
| `logs/` | per-phase logs (server paths replaced by placeholders) |
| `run_gen_AB.sh`, `run_acts.sh`, `run_gpu_chain.sh`, `run_after_chain.sh`, `run_after_ext.sh`, `finalize.sh` | the exact background job chain used on the pod (same steps as `method.py --all`) |
| `full_method_out.json`, `mini_method_out.json`, `preview_method_out.json` | aii-json full / 3-item / truncated variants of `method_out.json` |
| `time_log.json` | phase start/end times |
| `reproducibility.md`, `install.sh` | exact step-by-step reproduction (what was run, versions, seeds, hardware, runtimes); pinned environment + model download |
| `audit/rederive.py` → `results/audit_rederive.json` | independent re-derivation of the headline numbers from the raw rows, with placebo tests |
| `results/pip_freeze.txt` | the 168 installed package versions (identical to the pins in `pyproject.toml`) |

## How to run

See `reproducibility.md` for the complete procedure (Level 1: re-derive all numbers from the published rows on CPU in ~5 min; Level 2: full regeneration on a 24 GB GPU).

```bash
./install.sh                                                  # = uv venv + uv pip install -r pyproject.toml (all 168 packages pinned)
export OPENROUTER_BASE_URL=... OPENROUTER_API_KEY=...        # judge only (~$0.21 total)
.venv/bin/python method.py --all                              # ~3 GPU-hours on one 24 GB L4 (resumable)
.venv/bin/python method.py --assemble                         # rebuild method_out.json from results on disk
AII_JSON_SKILL_DIR=<path to aii-json skill> ./finalize.sh     # label all -> analysis -> tables -> method_out.json -> schema check
```

Hardware used: 1× NVIDIA L4 (23 GB), 6 vCPU (cgroup quota), 57 GB RAM. vLLM runs with `enforce_eager=True` (no C compiler for Triton in the
container). Models: `Qwen/Qwen3-8B-Base`, `Qwen/Qwen3-8B` (bf16).

## Restoring removed files

| removed path | restore with |
|---|---|
| `.venv/` | `./install.sh` (= `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml`, all versions pinned) |
| `src/__pycache__/` | regenerated automatically on import (`python -m compileall src`) |
| model weights (never in this directory; read from the shared HF cache) | `hf download Qwen/Qwen3-8B-Base` and `hf download Qwen/Qwen3-8B` (or `huggingface-cli download ...`) |

`activations/` (binary `.npy` arrays) is kept on the run volume by an explicit `keep` decision in `.aii/manifest.yaml`; `runs/`, `predictions/`, `results/` and all code are text and are always kept and published.

## Results

All numbers below are reproduced from `results/analysis.json` (tables in the next section are generated by `src/report.py`).
CIs are 95 %: Wilson for proportions, paraphrase-cluster bootstrap (B = 2000, paraphrases resampled jointly across arms) for Hill numbers.

### Did post-training install the collapse? Pre-registered verdicts: T2 INSTALLED_BY_POST_TRAINING, T1 MIXED (narrowly) → alternate 4 passes the screen

| | T1 grid path (correct programs) | T2 weighted shortest path (correct programs) |
|---|---|---|
| base, template-free (N=300) | BFS 12/15, DFS 3 — Hill_cc 1.65 [1.00, 2.00] | **Bellman-Ford 16/25**, Dijkstra 8, FW 1 — Hill_cc 2.18 [1.00, 2.73] |
| base, chat template (N=300) | BFS 49/57, DFS 7, A* 1 — Hill_cc 1.58 [1.10, 2.06] | **Dijkstra 63/90**, Bellman-Ford 24, FW 1, other 2 — Hill_cc 2.09 [1.63, 2.54] |
| instruct, template-free (N=100) | BFS 73/73 — Hill_cc 1.00 | Dijkstra 57/72, FW 8, Bellman-Ford 7 — Hill_cc 1.93 [1.41, 2.37] |
| instruct, chat template (N=200) | **BFS 200/200** — Hill_cc 1.00 | **Dijkstra 193/200**, Bellman-Ford 7 — Hill_cc 1.16 [1.03, 1.31] |

* **Weights (same chat tokens, base vs instruct weights):** D_weights = Hill_cc(instruct_chat) − Hill_cc(base_chat) = **−0.58 [−1.01, −0.15]**
  (T1) and **−0.93 [−1.38, −0.46]** (T2); label distributions differ (permutation χ² p = 0.0001 on both). The modal-share gap is 26.5 pp on
  T2 (bar ≥ 15 pp met → **INSTALLED_BY_POST_TRAINING**) but only **14.0 pp on T1** (instruct 100 % BFS vs base-chat 86 % BFS), so T1 misses
  the pre-registered bar on the modal-share criterion alone and reads **MIXED**. No task reads ALREADY_IN_BASE, so the alternate passes the
  screen. Under the Hill_all co-primary (fallback 3) both tasks read INSTALLED_BY_POST_TRAINING.
* **What post-training did is concentrate an existing mode, not invent one.** The instruct model's mode is already the base model's modal
  choice on T1 (BFS in both formats) and on T2 under the chat template (Dijkstra 70 %). Post-training removed the minority modes
  (T1: DFS 12 % → 0 %; T2: Bellman-Ford 27 % → 3.5 %).
* **Format matters too, and differently for the two models.** Within base weights the chat template does not change Hill_cc significantly
  (T1 −0.07 [−0.76, 0.88]; T2 −0.09 [−0.79, 1.12]) but on T2 it switches the base model's *mode* from Bellman-Ford (template-free, 64 %) to
  Dijkstra (70 %; permutation p = 0.0044). Within instruct weights the chat template further collapses T2 (Hill_cc 1.93 → 1.16,
  D = −0.76 [−1.26, −0.23]); T1 is already fully collapsed in both formats.
* **Robustness.** Judge labels instead of final labels: same verdicts (T2 D_weights −1.02 [−1.51, −0.51]). At the *planned* sample sizes
  (before the N = 300 power extension; 19–23 correct base-chat programs per task) both tasks read MIXED (CIs reach 0) — the T2 verdict needs
  the extension. Base template-free code is mostly broken (pass 5 % / 8 %), so base Hill_cc rests on 15 / 25 correct programs.
* **Priors (context only):** Invisible Lottery Table 12 reports Dijkstra 94.1 % (no cue, T = 0) for T2-like prompts; the inspiration repo
  reports Dijkstra 25/25 — consistent with the instruct chat arm here (96.5 %).

### Bans, the hash-committed forecast, and the prompting baseline

* **Instruct model under the modal ban (C1):** ban:BFS is mostly ignored — 57 of 70 correct T1 programs are still BFS; the 13 compliant ones
  land on DFS (12) and Dijkstra-unit (1). ban:Dijkstra is obeyed by 46 % (all correct), landing 46/46 on Bellman-Ford.
* **Forecast (committed 2026-10-19T17:15:56Z, sha256 `94854c80…d4d47`, git `908b4ee`, before C1 existed; hash re-verified at analysis):**
  primary predictor (base template-free distribution restricted to survivors, fallback 3) **hit top-1 on both events** (DFS; Bellman-Ford),
  log score −0.47 (T1, n = 13 compliant) and −0.22 (T2, n = 46) vs uniform −1.63 / −1.41. The base-chat predictor and the instruct
  typicality reference score as well or better on T2 (−0.058), so the hit shows the substitution target is shared by base and instruct
  models rather than uniquely predicted by the base distribution.
* **Base model ignores bans (A3):** banned-mode share among parseable template-free programs 0.36 vs 0.46 (T1, diff −0.10 [−0.21, 0.01])
  and 0.27 vs 0.25 (T2); correct-and-compliant rate 0 % (T1) / 4 % (T2).
* **BUY (diversity gained per pass-rate point lost):** the *prompt* is by far the best knob — ban:Dijkstra lifts T2 Hill_cc 1.16 → 1.99 at
  0 pp pass loss (efficiency 0.83); ban:BFS lifts T1 1.00 → 1.70 at 30 pp loss. No sharpening setting gains any diversity (Hill 2 and 3
  "not reached within the tested range"); AxBench's prompting-beats-steering pattern holds here.

### Mechanistic test: does removing the instruct-minus-base read state undo the collapse? No.

* **The direction is large, reliable and generic.** In the band (layers 8–28) the paired difference δ is about as large as the base
  residual itself (‖δ‖/‖h_B‖ ≈ 0.8–1.2; cos(mean h_I, mean h_B) ≈ 0.35–0.64), split-half reliability ≈ 0.998, and it is largely shared
  between the two tasks (cos(δ_T1, δ_T2) ≈ 0.85–0.92) — i.e. mostly a generic "chat-tuned model at the start of its answer" difference,
  not task-specific algorithm content. No massive-activation dominance in the band (top-10 coordinate energy share 0.05–0.22). Its logit
  lens at layer 28 says the same: −δ promotes `def`/`class` and suppresses ```` ``` ```` / "Here" (answer-format tokens).
  cos(δ_R, δ_gen) at generated positions is only 0.15–0.42 in the band (`figures/direction_diagnostics.png`).
* **Band subtraction (plan knob) is DESTRUCTIVE at every c** (0.5, 1.0, 1.5): 0/100 parseable programs per task and arm, while the hooked
  c = 0 control reproduces the vLLM baseline (100 % pass; same modal algorithm). The manipulation check shows why the knob cannot work as
  designed: subtraction closes the base–instruct gap exactly at layer 8 (gap_closed = 1.00 at c = 1) but downstream layers *amplify* it
  (hook test: cumulative change at layer 28 ≈ 1.9 × δ₂₈, cos 0.93), so c = 1 overshoots past the base mean (gap_closed 0.01–0.08 at layers
  18/28) and c = 1.5 goes negative.
* **Norm-matched random directions are not destructive** (format intact, algorithm unchanged on T1: flip rate 1–4 %) — they corrupt syntax
  (e.g. mismatched brackets), lowering pass rates; so the destruction is specific to the δ direction, not its norm.
* **Fallback 6 (single-layer δ₁₈ at layer 18, ADL-style; gap closed exactly at L18, 0.34 carried to L28 at c = 1):** c = 0.25 keeps 94–98 %
  correctness with **zero algorithm change**; c = 0.5 halves T1 correctness (52 %, still 100 % BFS) and keeps T2 correctness (98 %) while moving
  1/49 programs (Hill_cc 1.10); c = 1.0 destroys output. Verdict: NO_EFFECT within the correctness/format bars.
* **R-only ablation (extension):** subtracting δ only at the read position R (c = 1) flips Qwen3 out of its answer mode — 73 % (T1) / 95 % (T2)
  of samples open with thinking-style prose ("Okay, I need to solve…") despite the empty think block, or with base-like unfenced
  `class Solution:` code — yet the stated plan in rows without code names BFS in 72/72 (T1) and Dijkstra in 95/95 (T2), and every correct
  program keeps the instruct mode. The uniform 512-token no-code rule matters for this arm: on 20 coupled samples per task re-run without it
  (max 1024 tokens) parse rises 0.30 → 0.55 (T1) and 0.15 → 0.40 (T2), but the correct programs remain BFS 3/3 (T1) and Dijkstra 3 +
  Bellman-Ford 1 (T2). A norm-matched random R-only perturbation keeps 100 % correctness and even *raises* T2 Hill_cc to 1.43
  [Δ +0.43, CI 0.12–0.74] (10 % non-Dijkstra), so the T2 choice is fragile at R, but not in the base-ward direction δ points to.
* Net: **no knob setting meets RESTORES_WITHOUT_LOSS**; the read-state difference between the two checkpoints is dominated by
  answer-format / mode features, and removing it does not bring back the base model's algorithm mix.

### Independent re-derivation (audit)

`audit/rederive.py` re-reads the raw per-sample rows (`runs/labelled_*.jsonl`) and the committed forecast without importing any pipeline
code (Counter/pandas Hill numbers, its own cluster bootstrap with Python's `random`, scipy's χ² statistic inside its own permutation loop):
every per-arm Hill_cc and correct count, both D_weights (−0.58, −0.93), the modal-share gaps (14.0 / 26.5 pp), the verdicts, the forecast
log scores and the steering / ban counts match the pipeline exactly (0 mismatches). Its independent bootstrap gives
H(base_chat) − H(instruct_chat) CIs [0.11, 1.03] (T1) and [0.44, 1.37] (T2), and the permutation test gives p ≈ 0.0002 on both tasks.
**Placebo:** with arm labels shuffled between base_chat and instruct_chat the same permutation test rejects in 3.5 % (T1) and 6.5 % (T2) of
200 shuffles (≈ the nominal 5 %), and 0/20 placebo bootstrap CIs exclude 0, so the tests do not pass vacuously. A regex-only relabelling
finds a FIFO queue in 200/200 instruct T1 programs and a heap in 193/200 instruct T2 programs, matching the BFS / Dijkstra counts, and the
forecast file's sha256 still matches the committed hash.

### Labeller quality

* Reference gate (15 catalogue references + 10 variants/mutants): AST labeller 100 % correct; runtime labeller never wrong (array-scan Dijkstra
  and Dial are `unknown` at runtime by design and resolved by AST/judge). Harness: all references pass all cases at ≤ 0.19 × the time limit;
  infinite-loop, 4 GB-allocation, bad-step, `sys.exit` and weight-ignoring probes all fail as intended.
* Cohen's κ runtime vs AST over all parseable programs: 0.77 (instruct arms 0.64–1.00; broken base code 0.20–0.50, so most base labels come
  from the blind judge). Where runtime and AST agree, the judge agrees 91–100 % of the time per arm. A second judge
  (`deepseek/deepseek-v4.1-flash`) on 40 audit programs: κ = 0.93 with the primary judge (raw agreement 0.95).
* Judge-label sensitivity (Hill recomputed with judge labels for every sample) leaves every verdict unchanged. Judge cost: $0.21 for 2,014 calls.

### Figures

* `figures/labels_t1.png`, `figures/labels_t2.png` — algorithm shares of correct programs, every arm.
* `figures/steering_curves.png` — Hill_cc and pass rate vs c (band knob), random directions at c*, single-layer arms.
* `figures/direction_diagnostics.png` — per-layer cos(h_I, h_B), split-half reliability, ‖δ‖/‖h_B‖, top-10 energy share, cos(δ_R, δ_gen), cos(δ_T1, δ_T2).
* `figures/flips_t1.png`, `figures/flips_t2.png` — coupled-sample transition matrices (S0 label → arm label).

## Detailed tables (generated)

### Per-arm results (vLLM arms; T=1.0, top-p 1.0, no top-k, thinking off)

| arm | task | N | parse | pass [95% Wilson] | n correct | modal (correct) | modal share | Hill_cc [95% cluster-bootstrap] | Hill_all [95%] | audit acc. vs judge | judge-label Hill_cc |
|---|---|---|---|---|---|---|---|---|---|---|---|
| base_tf | t1 | 300 | 0.97 | 0.05 [0.03, 0.08] | 15 | bfs | 0.80 [0.55, 0.93] | 1.65 [1.00, 2.00] | 3.34 [2.92, 3.73] | 1.00 [0.80, 1.00] | 1.65 |
| base_tf | t2 | 300 | 0.97 | 0.08 [0.06, 0.12] | 25 | bellman_ford_spfa | 0.64 [0.45, 0.80] | 2.18 [1.00, 2.73] | 3.24 [2.85, 3.52] | 1.00 [0.80, 1.00] | 2.53 |
| base_chat | t1 | 300 | 0.58 | 0.19 [0.15, 0.24] | 57 | bfs | 0.86 [0.75, 0.93] | 1.58 [1.10, 2.06] | 3.13 [2.44, 3.66] | 1.00 [0.80, 1.00] | 1.58 |
| base_chat | t2 | 300 | 0.66 | 0.30 [0.25, 0.35] | 90 | dijkstra | 0.70 [0.60, 0.78] | 2.09 [1.63, 2.54] | 2.67 [2.26, 3.00] | 0.93 [0.70, 0.99] | 2.19 |
| instruct_tf | t1 | 100 | 0.93 | 0.73 [0.64, 0.81] | 73 | bfs | 1.00 [0.95, 1.00] | 1.00 [1.00, 1.00] | 1.41 [1.11, 1.66] | 1.00 [0.80, 1.00] | 1.00 |
| instruct_tf | t2 | 100 | 0.89 | 0.72 [0.63, 0.80] | 72 | dijkstra | 0.79 [0.68, 0.87] | 1.93 [1.41, 2.37] | 2.60 [1.92, 3.15] | 1.00 [0.80, 1.00] | 1.93 |
| instruct_chat | t1 | 200 | 1.00 | 1.00 [0.98, 1.00] | 200 | bfs | 1.00 [0.98, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [0.80, 1.00] | 1.00 |
| instruct_chat | t2 | 200 | 1.00 | 1.00 [0.98, 1.00] | 200 | dijkstra | 0.96 [0.93, 0.98] | 1.16 [1.03, 1.31] | 1.16 [1.03, 1.31] | 1.00 [0.80, 1.00] | 1.16 |
| base_tf_ban | t1 | 100 | 0.95 | 0.01 [0.00, 0.05] | 1 | bfs | 1.00 [0.21, 1.00] | 1.00 [1.00, 1.00] | 3.50 [2.79, 4.07] | 1.00 [0.80, 1.00] | 1.00 |
| base_tf_ban | t2 | 100 | 0.98 | 0.08 [0.04, 0.15] | 8 | dijkstra | 0.50 [0.22, 0.78] | 2.00 [1.00, 2.00] | 3.43 [2.81, 3.88] | 1.00 [0.80, 1.00] | 2.00 |
| instruct_chat_ban | t1 | 100 | 1.00 | 0.70 [0.60, 0.78] | 70 | bfs | 0.81 [0.71, 0.89] | 1.70 [1.22, 2.25] | 2.10 [1.65, 2.40] | 1.00 [0.80, 1.00] | 1.70 |
| instruct_chat_ban | t2 | 100 | 1.00 | 1.00 [0.96, 1.00] | 100 | dijkstra | 0.54 [0.44, 0.63] | 1.99 [1.65, 2.00] | 1.99 [1.67, 2.00] | 1.00 [0.80, 1.00] | 1.99 |

Label counts over correct programs:

- **base_tf / t1** correct: `{'bfs': 12, 'dfs': 3}`; all parseable: `{'bfs': 134, 'dfs': 65, 'bidir_bfs': 2, 'astar_greedy': 7, 'dijkstra_unit': 2, 'other': 82}`
- **base_tf / t2** correct: `{'dijkstra': 8, 'bellman_ford_spfa': 16, 'floyd_warshall': 1}`; all parseable: `{'dijkstra': 74, 'bellman_ford_spfa': 55, 'bidir_dijkstra': 1, 'floyd_warshall': 10, 'dial': 2, 'other': 149}`
- **base_chat / t1** correct: `{'bfs': 49, 'dfs': 7, 'astar_greedy': 1}`; all parseable: `{'bfs': 109, 'dfs': 30, 'astar_greedy': 12, 'dijkstra_unit': 8, 'other': 16}`
- **base_chat / t2** correct: `{'dijkstra': 63, 'bellman_ford_spfa': 24, 'floyd_warshall': 1, 'other': 2}`; all parseable: `{'dijkstra': 125, 'bellman_ford_spfa': 47, 'bidir_dijkstra': 1, 'floyd_warshall': 4, 'other': 22}`
- **instruct_tf / t1** correct: `{'bfs': 73}`; all parseable: `{'bfs': 83, 'other': 10}`
- **instruct_tf / t2** correct: `{'dijkstra': 57, 'bellman_ford_spfa': 7, 'floyd_warshall': 8}`; all parseable: `{'dijkstra': 61, 'bellman_ford_spfa': 7, 'floyd_warshall': 8, 'other': 13}`
- **instruct_chat / t1** correct: `{'bfs': 200}`; all parseable: `{'bfs': 200}`
- **instruct_chat / t2** correct: `{'dijkstra': 193, 'bellman_ford_spfa': 7}`; all parseable: `{'dijkstra': 193, 'bellman_ford_spfa': 7}`
- **base_tf_ban / t1** correct: `{'bfs': 1}`; all parseable: `{'bfs': 34, 'dfs': 35, 'bidir_bfs': 1, 'astar_greedy': 2, 'dijkstra_unit': 1, 'other': 22}`
- **base_tf_ban / t2** correct: `{'dijkstra': 4, 'bellman_ford_spfa': 4}`; all parseable: `{'dijkstra': 26, 'bellman_ford_spfa': 18, 'floyd_warshall': 6, 'dial': 1, 'other': 47}`
- **instruct_chat_ban / t1** correct: `{'bfs': 57, 'dfs': 12, 'dijkstra_unit': 1}`; all parseable: `{'bfs': 62, 'dfs': 36, 'dijkstra_unit': 2}`
- **instruct_chat_ban / t2** correct: `{'dijkstra': 54, 'bellman_ford_spfa': 46}`; all parseable: `{'dijkstra': 54, 'bellman_ford_spfa': 46}`

### Collapse screen (2x2 weights x format), Hill_cc differences with paraphrase-joint cluster bootstrap

| task | D_weights = H(instruct_chat) - H(base_chat) | D_format = H(base_chat) - H(base_tf) | D_format_instruct = H(instruct_chat) - H(instruct_tf) | interaction | verdict (Hill_cc, pre-registered) | verdict (Hill_all, fallback-3 co-primary) |
|---|---|---|---|---|---|---|
| t1 | -0.58 [-1.01, -0.15] | -0.07 [-0.76, 0.88] | 0.00 [0.00, 0.00] | 0.07 [-0.83, 0.74] | **MIXED** | **INSTALLED_BY_POST_TRAINING** |
| t2 | -0.93 [-1.38, -0.46] | -0.09 [-0.79, 1.12] | -0.76 [-1.26, -0.23] | -0.67 [-1.73, 0.10] | **INSTALLED_BY_POST_TRAINING** | **INSTALLED_BY_POST_TRAINING** |

Same contrasts on Hill_all (all parseable labelled programs):

| task | D_weights_all | D_format_all | D_format_instruct_all | interaction_all |
|---|---|---|---|---|
| t1 | -2.13 [-2.66, -1.43] | -0.21 [-1.05, 0.55] | -0.41 [-0.66, -0.15] | -0.19 [-0.94, 0.63] |
| t2 | -1.50 [-1.91, -1.06] | -0.57 [-1.04, -0.10] | -1.44 [-2.03, -0.71] | -0.87 [-1.60, 0.04] |

Verdict ingredients (Hill_cc):

- t1: H(base_chat) - H(instruct_chat) = 0.58 [0.11, 1.04]; modal-share gap 14.0 pp (instruct modal `bfs`, base_tf modal `bfs`, base_chat modal `bfs`); H(base_tf) - H(instruct_chat) = 0.65 [0.00, 0.99]; bars met: weights=False, format=False, already_in_base=False
  - permutation chi-square p (correct labels): instruct_chat vs base_chat 0.0001, base_chat vs base_tf 0.7389, instruct_chat vs instruct_tf 1.0000
- t2: H(base_chat) - H(instruct_chat) = 0.93 [0.46, 1.38]; modal-share gap 26.5 pp (instruct modal `dijkstra`, base_tf modal `bellman_ford_spfa`, base_chat modal `dijkstra`); H(base_tf) - H(instruct_chat) = 1.02 [-0.16, 1.64]; bars met: weights=True, format=False, already_in_base=False
  - permutation chi-square p (correct labels): instruct_chat vs base_chat 0.0001, base_chat vs base_tf 0.0044, instruct_chat vs instruct_tf 0.0001

Alternate 4 passes the screen (Hill_cc rule): **True**; (Hill_all rule): **True**

Sensitivity of the verdict:

- t1|judge_labels: Hill_cc verdict MIXED (D_weights -0.58 [-1.01, -0.15]); Hill_all verdict INSTALLED_BY_POST_TRAINING (D_weights_all -2.14 [-2.68, -1.44]); sizes {'base_tf': {'N': 300, 'n_correct_labelled': 15}, 'base_chat': {'N': 300, 'n_correct_labelled': 57}, 'instruct_chat': {'N': 200, 'n_correct_labelled': 200}, 'instruct_tf': {'N': 100, 'n_correct_labelled': 73}}
- t1|planned_N_only: Hill_cc verdict MIXED (D_weights -0.59 [-0.99, 0.00]); Hill_all verdict INSTALLED_BY_POST_TRAINING (D_weights_all -2.04 [-2.80, -0.95]); sizes {'base_tf': {'N': 200, 'n_correct_labelled': 12}, 'base_chat': {'N': 100, 'n_correct_labelled': 23}, 'instruct_chat': {'N': 200, 'n_correct_labelled': 200}, 'instruct_tf': {'N': 100, 'n_correct_labelled': 73}}
- t2|judge_labels: Hill_cc verdict INSTALLED_BY_POST_TRAINING (D_weights -1.02 [-1.51, -0.51]); Hill_all verdict INSTALLED_BY_POST_TRAINING (D_weights_all -1.51 [-1.92, -1.06]); sizes {'base_tf': {'N': 300, 'n_correct_labelled': 25}, 'base_chat': {'N': 300, 'n_correct_labelled': 90}, 'instruct_chat': {'N': 200, 'n_correct_labelled': 200}, 'instruct_tf': {'N': 100, 'n_correct_labelled': 72}}
- t2|planned_N_only: Hill_cc verdict MIXED (D_weights -0.51 [-0.88, 0.25]); Hill_all verdict INSTALLED_BY_POST_TRAINING (D_weights_all -1.27 [-1.82, -0.51]); sizes {'base_tf': {'N': 200, 'n_correct_labelled': 18}, 'base_chat': {'N': 100, 'n_correct_labelled': 19}, 'instruct_chat': {'N': 200, 'n_correct_labelled': 200}, 'instruct_tf': {'N': 100, 'n_correct_labelled': 72}}

### Steering (HF, Qwen3-8B, coupled seeds; all deltas vs the hooked c=0 control S0)

| task | arm | N | parse | pass | format_ok_loose | degenerate | Hill_cc | dHill_cc vs S0 | dpass (pp) vs S0 | flip rate vs S0 | restoration idx vs base_chat (add-0.5 / unsmoothed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| t1 | S0 none c=0 | 100 | 1.00 | 1.00 [0.96, 1.00] | 1.00 | 0.00 | 1.00 | – | – | – | – |
| t1 | random1 | 100 | 0.96 | 0.41 [0.32, 0.51] | 1.00 | 0.00 | 1.00 | 0.00 [0.00, 0.00] | -59.0 [-72.0, -44.0] | 0.04 | 0.26 [0.11, 0.63] / 0.00 [0.00, 0.00] |
| t1 | random1_Ronly:c=1.0 | 100 | 1.00 | 1.00 [0.96, 1.00] | 1.00 | 0.00 | 1.00 | 0.00 [0.00, 0.00] | 0.0 [0.0, 0.0] | 0.00 | 0.00 [0.00, 0.00] / 0.00 [0.00, 0.00] |
| t1 | random2 | 100 | 0.98 | 0.68 [0.58, 0.76] | 1.00 | 0.00 | 1.00 | 0.00 [0.00, 0.00] | -32.0 [-44.0, -20.0] | 0.01 | 0.12 [0.04, 0.42] / 0.00 [0.00, 0.00] |
| t1 | sharpen:c=0.5 | 100 | 0.00 | 0.00 [0.00, 0.04] | 0.00 | 0.39 | – | – [–, –] | -100.0 [-100.0, -100.0] | – | – / – |
| t1 | sharpen:c=1.0 | 100 | 0.00 | 0.00 [0.00, 0.04] | 0.00 | 0.00 | – | – [–, –] | -100.0 [-100.0, -100.0] | – | – / – |
| t1 | sharpen:c=1.5 | 100 | 0.00 | 0.00 [0.00, 0.04] | 0.00 | 0.00 | – | – [–, –] | -100.0 [-100.0, -100.0] | – | – / – |
| t1 | sharpen_Ronly:c=1.0 | 100 | 0.28 | 0.14 [0.09, 0.22] | 0.07 | 0.03 | 1.00 | 0.00 [0.00, 0.00] | -86.0 [-94.0, -78.0] | 0.07 | 0.34 [-3.55, 0.50] / 0.00 [0.00, 0.00] |
| t1 | sharpen_Ronly:c=1.0+nocutoff | 20 | 0.55 | 0.15 [0.05, 0.36] | 0.05 | 0.70 | 1.00 | 0.00 [0.00, 0.00] | -85.0 [-100.0, -53.3] | 0.00 | -1.09 [-7.21, 0.38] / 0.00 [0.00, 0.00] |
| t1 | single18:c=0.25 | 50 | 1.00 | 0.94 [0.84, 0.98] | 1.00 | 0.00 | 1.00 | 0.00 [0.00, 0.00] | -6.0 [-15.0, 0.0] | 0.00 | 0.23 [0.04, 0.57] / 0.00 [0.00, 0.00] |
| t1 | single18:c=0.5 | 50 | 1.00 | 0.52 [0.39, 0.65] | 1.00 | 0.00 | 1.00 | 0.00 [0.00, 0.00] | -48.0 [-68.0, -30.0] | 0.00 | 0.35 [-0.39, 0.60] / 0.00 [0.00, 0.00] |
| t1 | single18:c=1.0 | 50 | 0.00 | 0.00 [0.00, 0.07] | 0.00 | 0.94 | – | – [–, –] | -100.0 [-100.0, -100.0] | – | – / – |
| t1 | **knob verdict (band 8-28)** | | | | | | | **DESTRUCTIVE** | c* = 0.5 no sharpening c kept pass >= 0.8 x S0; c* set to 0.5 (flagged) | | |
| t1 | **steer:single18** | | | | | | | **NO_EFFECT_WITHIN_BARS** | | | |
| t1 | **steer:sharpen_Ronly** | | | | | | | **DESTRUCTIVE** | | | |

- t1 random1: thinking-style opening rate 0.00; 4 rows without parseable code; algorithm keywords in those rows: `{'bfs': 4, 'dfs': 1, 'dijkstra': 0, 'astar': 3, 'bellman_ford': 0, 'floyd': 0}`
- t1 random2: thinking-style opening rate 0.00; 2 rows without parseable code; algorithm keywords in those rows: `{'bfs': 2, 'dfs': 0, 'dijkstra': 0, 'astar': 0, 'bellman_ford': 0, 'floyd': 0}`
- t1 sharpen:c=0.5: thinking-style opening rate 0.89; 100 rows without parseable code; algorithm keywords in those rows: `{'bfs': 1, 'dfs': 1, 'dijkstra': 0, 'astar': 0, 'bellman_ford': 0, 'floyd': 0}`
- t1 sharpen:c=1.0: thinking-style opening rate 0.00; 100 rows without parseable code; algorithm keywords in those rows: `{'bfs': 0, 'dfs': 4, 'dijkstra': 0, 'astar': 0, 'bellman_ford': 0, 'floyd': 0}`
- t1 sharpen:c=1.5: thinking-style opening rate 0.00; 100 rows without parseable code; algorithm keywords in those rows: `{'bfs': 1, 'dfs': 3, 'dijkstra': 0, 'astar': 0, 'bellman_ford': 0, 'floyd': 0}`
- t1 sharpen_Ronly:c=1.0: thinking-style opening rate 0.73; 72 rows without parseable code; algorithm keywords in those rows: `{'bfs': 72, 'dfs': 29, 'dijkstra': 0, 'astar': 0, 'bellman_ford': 0, 'floyd': 0}`
- t1 sharpen_Ronly:c=1.0+nocutoff: thinking-style opening rate 0.70; 9 rows without parseable code; algorithm keywords in those rows: `{'bfs': 9, 'dfs': 4, 'dijkstra': 0, 'astar': 0, 'bellman_ford': 0, 'floyd': 0}`
- t1 single18:c=1.0: thinking-style opening rate 1.00; 50 rows without parseable code; algorithm keywords in those rows: `{'bfs': 38, 'dfs': 0, 'dijkstra': 0, 'astar': 0, 'bellman_ford': 0, 'floyd': 0}`

t1: S0 (HF engine) vs B1 (vLLM) implementation check: Hill_cc 1.00 vs 1.00, pass 1.00 [0.96, 1.00] vs 1.00 [0.98, 1.00], permutation p = 1.0000

t1: 512-token no-code rule validation for steer:sharpen_Ronly:c=1.0 on 20 coupled samples: parse 0.30 with rule vs 0.55 without (max 1024 tokens); pass 0.15 vs 0.15; correct labels without rule `{'bfs': 3}`

t1: R-only sharpening vs R-only random control (c=1.0): Hill diff 0.00 [0.00, 0.00], flip diff 0.07 [0.00, 0.19], permutation p 1.0000

| t2 | S0 none c=0 | 100 | 1.00 | 1.00 [0.96, 1.00] | 1.00 | 0.00 | 1.00 | – | – | – | – |
| t2 | random1 | 100 | 1.00 | 0.00 [0.00, 0.04] | 0.99 | 0.01 | – | – [–, –] | -100.0 [-100.0, -100.0] | 0.00 | – / – |
| t2 | random1_Ronly:c=1.0 | 100 | 1.00 | 1.00 [0.96, 1.00] | 1.00 | 0.00 | 1.43 | 0.43 [0.12, 0.74] | 0.0 [0.0, 0.0] | 0.10 | 0.70 [0.31, 0.92] / 0.71 [0.30, 0.93] |
| t2 | random2 | 100 | 1.00 | 0.33 [0.25, 0.43] | 0.97 | 0.03 | 1.00 | 0.00 [0.00, 0.00] | -67.0 [-79.0, -54.0] | 0.36 | -2.10 [-6.94, -0.44] / -2.13 [-6.75, -0.54] |
| t2 | sharpen:c=0.5 | 100 | 0.00 | 0.00 [0.00, 0.04] | 0.00 | 0.95 | – | – [–, –] | -100.0 [-100.0, -100.0] | – | – / – |
| t2 | sharpen:c=1.0 | 100 | 0.00 | 0.00 [0.00, 0.04] | 0.00 | 0.00 | – | – [–, –] | -100.0 [-100.0, -100.0] | – | – / – |
| t2 | sharpen:c=1.5 | 100 | 0.00 | 0.00 [0.00, 0.04] | 0.00 | 0.00 | – | – [–, –] | -100.0 [-100.0, -100.0] | – | – / – |
| t2 | sharpen_Ronly:c=1.0 | 100 | 0.05 | 0.05 [0.02, 0.11] | 0.05 | 0.00 | 1.00 | 0.00 [0.00, 0.00] | -95.0 [-100.0, -88.0] | 0.00 | 0.27 [-0.85, 0.46] / 0.00 [0.00, 0.00] |
| t2 | sharpen_Ronly:c=1.0+nocutoff | 20 | 0.40 | 0.20 [0.08, 0.42] | 0.15 | 0.85 | 1.75 | 0.75 [0.00, 1.00] | -80.0 [-100.0, -60.0] | 0.50 | 0.43 [-2.60, 0.77] / 0.90 [-2.80, 0.98] |
| t2 | single18:c=0.25 | 50 | 1.00 | 0.98 [0.90, 1.00] | 1.00 | 0.00 | 1.00 | 0.00 [0.00, 0.00] | -2.0 [-10.0, 0.0] | 0.00 | 0.12 [0.03, 0.30] / 0.00 [0.00, 0.00] |
| t2 | single18:c=0.5 | 50 | 1.00 | 0.98 [0.90, 1.00] | 1.00 | 0.00 | 1.10 | 0.10 [0.00, 0.38] | -2.0 [-10.0, 0.0] | 0.02 | 0.33 [0.04, 0.77] / 0.27 [0.00, 0.71] |
| t2 | single18:c=1.0 | 50 | 0.00 | 0.00 [0.00, 0.07] | 0.00 | 0.92 | – | – [–, –] | -100.0 [-100.0, -100.0] | – | – / – |
| t2 | **knob verdict (band 8-28)** | | | | | | | **DESTRUCTIVE** | c* = 0.5 no sharpening c kept pass >= 0.8 x S0; c* set to 0.5 (flagged) | | |
| t2 | **steer:single18** | | | | | | | **NO_EFFECT_WITHIN_BARS** | | | |
| t2 | **steer:sharpen_Ronly** | | | | | | | **DESTRUCTIVE** | | | |

- t2 sharpen:c=0.5: thinking-style opening rate 0.22; 100 rows without parseable code; algorithm keywords in those rows: `{'bfs': 0, 'dfs': 0, 'dijkstra': 0, 'astar': 0, 'bellman_ford': 0, 'floyd': 0}`
- t2 sharpen:c=1.0: thinking-style opening rate 0.00; 100 rows without parseable code; algorithm keywords in those rows: `{'bfs': 0, 'dfs': 0, 'dijkstra': 0, 'astar': 0, 'bellman_ford': 0, 'floyd': 0}`
- t2 sharpen:c=1.5: thinking-style opening rate 0.00; 100 rows without parseable code; algorithm keywords in those rows: `{'bfs': 0, 'dfs': 0, 'dijkstra': 0, 'astar': 0, 'bellman_ford': 0, 'floyd': 0}`
- t2 sharpen_Ronly:c=1.0: thinking-style opening rate 0.95; 95 rows without parseable code; algorithm keywords in those rows: `{'bfs': 1, 'dfs': 0, 'dijkstra': 95, 'astar': 0, 'bellman_ford': 4, 'floyd': 0}`
- t2 sharpen_Ronly:c=1.0+nocutoff: thinking-style opening rate 0.85; 12 rows without parseable code; algorithm keywords in those rows: `{'bfs': 1, 'dfs': 0, 'dijkstra': 12, 'astar': 0, 'bellman_ford': 2, 'floyd': 0}`
- t2 single18:c=1.0: thinking-style opening rate 1.00; 50 rows without parseable code; algorithm keywords in those rows: `{'bfs': 1, 'dfs': 0, 'dijkstra': 5, 'astar': 0, 'bellman_ford': 10, 'floyd': 1}`

t2: S0 (HF engine) vs B1 (vLLM) implementation check: Hill_cc 1.00 vs 1.16, pass 1.00 [0.96, 1.00] vs 1.00 [0.98, 1.00], permutation p = 0.1030

t2: 512-token no-code rule validation for steer:sharpen_Ronly:c=1.0 on 20 coupled samples: parse 0.15 with rule vs 0.40 without (max 1024 tokens); pass 0.15 vs 0.20; correct labels without rule `{'dijkstra': 3, 'bellman_ford_spfa': 1}`

t2: R-only sharpening vs R-only random control (c=1.0): Hill diff -0.43 [-0.76, -0.14], flip diff -0.10 [-0.17, -0.04], permutation p 1.0000


Manipulation check, gap_closed = 1 - ||mean h_steered - mean h_B|| / ||mean h_I - mean h_B|| at R:

- manipulation_S t1 steer:sharpen:c=0.5: L8 0.50, L18 0.34, L28 0.38
- manipulation_S t1 steer:sharpen:c=1.0: L8 1.00, L18 0.05, L28 0.01
- manipulation_S t1 steer:sharpen:c=1.5: L8 0.50, L18 -0.38, L28 -0.40
- manipulation_S t2 steer:sharpen:c=0.5: L8 0.50, L18 0.37, L28 0.38
- manipulation_S t2 steer:sharpen:c=1.0: L8 1.00, L18 0.08, L28 0.04
- manipulation_S t2 steer:sharpen:c=1.5: L8 0.50, L18 -0.32, L28 -0.37
- manipulation_R t1 steer:random1: L8 -0.12, L18 0.06, L28 -0.07
- manipulation_R t1 steer:random2: L8 -0.12, L18 0.07, L28 -0.05
- manipulation_R t2 steer:random1: L8 -0.12, L18 0.05, L28 -0.08
- manipulation_R t2 steer:random2: L8 -0.12, L18 0.06, L28 -0.05
- manipulation_X t1 steer:sharpen_Ronly:c=1.0: L8 1.00, L18 0.05, L28 0.01
- manipulation_X t1 steer:random1_Ronly:c=1.0: L8 -0.42, L18 0.03, L28 -0.33
- manipulation_X t1 steer:single18:c=0.25: L8 0.00, L18 0.25, L28 0.04
- manipulation_X t1 steer:single18:c=0.5: L8 0.00, L18 0.50, L28 0.11
- manipulation_X t1 steer:single18:c=1.0: L8 0.00, L18 1.00, L28 0.36
- manipulation_X t1 steer:sharpen_Ronly:c=1.0+nocutoff: L8 1.00, L18 0.05, L28 0.01
- manipulation_X t2 steer:sharpen_Ronly:c=1.0: L8 1.00, L18 0.08, L28 0.04
- manipulation_X t2 steer:random1_Ronly:c=1.0: L8 -0.42, L18 0.03, L28 -0.31
- manipulation_X t2 steer:single18:c=0.25: L8 0.00, L18 0.25, L28 0.06
- manipulation_X t2 steer:single18:c=0.5: L8 0.00, L18 0.50, L28 0.13
- manipulation_X t2 steer:single18:c=1.0: L8 0.00, L18 1.00, L28 0.34
- manipulation_X t2 steer:sharpen_Ronly:c=1.0+nocutoff: L8 1.00, L18 0.08, L28 0.04

### BUY rows

| task | knob | Hill_cc | pass | dHill_cc | pass loss (pp) | efficiency | price Hill 2 | price Hill 3 |
|---|---|---|---|---|---|---|---|---|
| t1 | steer:random1 | 1.00 | 0.41 | 0.00 | 59.0 | 0.000 | – | – |
| t1 | steer:random1_Ronly:c=1.0 | 1.00 | 1.00 | 0.00 | 0.0 | 0.000 | – | – |
| t1 | steer:random2 | 1.00 | 0.68 | 0.00 | 32.0 | 0.000 | – | – |
| t1 | steer:sharpen:c=0.5 | – | 0.00 | – | 100.0 | – | not reached within the tested range | not reached within the tested range |
| t1 | steer:sharpen:c=1.0 | – | 0.00 | – | 100.0 | – | not reached within the tested range | not reached within the tested range |
| t1 | steer:sharpen:c=1.5 | – | 0.00 | – | 100.0 | – | not reached within the tested range | not reached within the tested range |
| t1 | steer:sharpen_Ronly:c=1.0 | 1.00 | 0.14 | 0.00 | 86.0 | 0.000 | not reached within the tested range | not reached within the tested range |
| t1 | steer:sharpen_Ronly:c=1.0+nocutoff | 1.00 | 0.15 | 0.00 | 85.0 | 0.000 | not reached within the tested range | not reached within the tested range |
| t1 | steer:single18:c=0.25 | 1.00 | 0.94 | 0.00 | 6.0 | 0.000 | – | – |
| t1 | steer:single18:c=0.5 | 1.00 | 0.52 | 0.00 | 48.0 | 0.000 | – | – |
| t1 | steer:single18:c=1.0 | – | 0.00 | – | 100.0 | – | – | – |
| t1 | prompt:ban:BFS | 1.70 | 0.70 | 0.70 | 30.0 | 0.023 | n/a (single setting) | n/a (single setting) |
| t2 | steer:random1 | – | 0.00 | – | 100.0 | – | – | – |
| t2 | steer:random1_Ronly:c=1.0 | 1.43 | 1.00 | 0.43 | 0.0 | 0.430 | – | – |
| t2 | steer:random2 | 1.00 | 0.33 | 0.00 | 67.0 | 0.000 | – | – |
| t2 | steer:sharpen:c=0.5 | – | 0.00 | – | 100.0 | – | not reached within the tested range | not reached within the tested range |
| t2 | steer:sharpen:c=1.0 | – | 0.00 | – | 100.0 | – | not reached within the tested range | not reached within the tested range |
| t2 | steer:sharpen:c=1.5 | – | 0.00 | – | 100.0 | – | not reached within the tested range | not reached within the tested range |
| t2 | steer:sharpen_Ronly:c=1.0 | 1.00 | 0.05 | 0.00 | 95.0 | 0.000 | not reached within the tested range | not reached within the tested range |
| t2 | steer:sharpen_Ronly:c=1.0+nocutoff | 1.75 | 0.20 | 0.75 | 80.0 | 0.009 | not reached within the tested range | not reached within the tested range |
| t2 | steer:single18:c=0.25 | 1.00 | 0.98 | 0.00 | 2.0 | 0.000 | – | – |
| t2 | steer:single18:c=0.5 | 1.10 | 0.98 | 0.10 | 2.0 | 0.052 | – | – |
| t2 | steer:single18:c=1.0 | – | 0.00 | – | 100.0 | – | – | – |
| t2 | prompt:ban:Dijkstra | 1.99 | 1.00 | 0.83 | 0.0 | 0.830 | n/a (single setting) | n/a (single setting) |

### PREDICT rows (hash-committed before phase C; primary = base_tf all-samples, fallback 3)

| task | predictor | primary | n compliant | realised mode | top-1 | hit | log score | JS to realised | hash match |
|---|---|---|---|---|---|---|---|---|---|
| t1 | base_chat_correct | False | 13 | dfs | dfs | True | -0.412 | 0.032 | True |
| t1 | base_tf_all | True | 13 | dfs | dfs | True | -0.470 | 0.066 | True |
| t1 | base_tf_correct | False | 13 | dfs | dfs | True | -0.412 | 0.032 | True |
| t1 | instruct_chat_correct | False | 13 | dfs | dfs | True | -1.630 | 0.352 | True |
| t1 | uniform | False | 13 | dfs | dfs | True | -1.630 | 0.352 | True |
| t2 | base_chat_correct | False | 46 | bellman_ford_spfa | bellman_ford_spfa | True | -0.058 | 0.020 | True |
| t2 | base_tf_all | True | 46 | bellman_ford_spfa | bellman_ford_spfa | True | -0.220 | 0.074 | True |
| t2 | base_tf_correct | False | 46 | bellman_ford_spfa | bellman_ford_spfa | True | -0.144 | 0.049 | True |
| t2 | instruct_chat_correct | False | 46 | bellman_ford_spfa | bellman_ford_spfa | True | -0.058 | 0.020 | True |
| t2 | uniform | False | 46 | bellman_ford_spfa | bellman_ford_spfa | True | -1.406 | 0.384 | True |

Realised compliant landing counts: t1: `{'dfs': 12, 'bidir_bfs': 0, 'iddfs': 0, 'astar_greedy': 0, 'dijkstra_unit': 1, 'other': 0}`; t2: `{'bellman_ford_spfa': 46, 'bidir_dijkstra': 0, 'floyd_warshall': 0, 'dial': 0, 'other': 0}`

### Base-model ban obedience (template-free A3 vs A1)

- t1: banned `bfs` share among parseable: ban 0.36 [0.27, 0.46] vs baseline 0.46 [0.40, 0.52] (diff -0.10 [-0.21, 0.01]); compliance (correct and not banned) 0.00 [0.00, 0.04]; base landing `{'dfs': 0, 'bidir_bfs': 0, 'iddfs': 0, 'astar_greedy': 0, 'dijkstra_unit': 0, 'other': 0}`; instruct landing `{'dfs': 12, 'bidir_bfs': 0, 'iddfs': 0, 'astar_greedy': 0, 'dijkstra_unit': 1, 'other': 0}` (instruct compliance 0.13 [0.08, 0.21]); JS(base, instruct landing) –
- t2: banned `dijkstra` share among parseable: ban 0.27 [0.19, 0.36] vs baseline 0.25 [0.21, 0.31] (diff 0.01 [-0.09, 0.11]); compliance (correct and not banned) 0.04 [0.02, 0.10]; base landing `{'bellman_ford_spfa': 4, 'bidir_dijkstra': 0, 'floyd_warshall': 0, 'dial': 0, 'other': 0}`; instruct landing `{'bellman_ford_spfa': 46, 'bidir_dijkstra': 0, 'floyd_warshall': 0, 'dial': 0, 'other': 0}` (instruct compliance 0.46 [0.37, 0.56]); JS(base, instruct landing) 0.068

### Labeller QA

- Reference gate (15 catalogue references + 10 variants/mutants): AST accuracy 1.00, runtime never-wrong rate 1.00 (exact 0.88; array-scan Dijkstra and Dial are 'unknown' at runtime by design), gate ok = True
- Cohen's kappa runtime vs AST (all parseable programs): 0.77
- Second judge (deepseek/deepseek-v4.1-flash) on 40 audit programs: inter-judge kappa 0.93, raw agreement 0.95

| arm / task | n parseable | kappa runtime-AST | audit acc. (15) | final vs judge (all) | runtime+AST labels vs judge | sources |
|---|---|---|---|---|---|---|
| base_tf|t1 | 292 | 0.45 | 1.00 [0.80, 1.00] | 0.98 [0.95, 0.99] | 0.91 [0.82, 0.95] | {'runtime+ast': 75, 'judge': 217, 'fallback': 0} |
| base_tf|t2 | 291 | 0.20 | 1.00 [0.80, 1.00] | 0.99 [0.98, 1.00] | 0.92 [0.75, 0.98] | {'runtime+ast': 25, 'judge': 266, 'fallback': 0} |
| base_chat|t1 | 175 | 0.40 | 1.00 [0.80, 1.00] | 0.99 [0.97, 1.00] | 0.99 [0.93, 1.00] | {'runtime+ast': 81, 'judge': 94, 'fallback': 0} |
| base_chat|t2 | 199 | 0.50 | 0.93 [0.70, 0.99] | 0.97 [0.94, 0.99] | 0.94 [0.88, 0.97] | {'runtime+ast': 105, 'judge': 94, 'fallback': 0} |
| base_tf_ban|t1 | 95 | 0.43 | 1.00 [0.80, 1.00] | 0.98 [0.93, 0.99] | 0.93 [0.77, 0.98] | {'runtime+ast': 27, 'judge': 68, 'fallback': 0} |
| base_tf_ban|t2 | 98 | 0.34 | 1.00 [0.80, 1.00] | 0.99 [0.94, 1.00] | 0.93 [0.70, 0.99] | {'runtime+ast': 15, 'judge': 83, 'fallback': 0} |
| instruct_chat|t1 | 200 | 1.00 | 1.00 [0.80, 1.00] | 1.00 [0.98, 1.00] | 1.00 [0.98, 1.00] | {'runtime+ast': 200, 'judge': 0, 'fallback': 0} |
| instruct_chat|t2 | 200 | 1.00 | 1.00 [0.80, 1.00] | 1.00 [0.98, 1.00] | 1.00 [0.98, 1.00] | {'runtime+ast': 193, 'judge': 7, 'fallback': 0} |
| instruct_tf|t1 | 93 | 0.71 | 1.00 [0.80, 1.00] | 1.00 [0.96, 1.00] | 1.00 [0.95, 1.00] | {'runtime+ast': 76, 'judge': 17, 'fallback': 0} |
| instruct_tf|t2 | 89 | 0.89 | 1.00 [0.80, 1.00] | 1.00 [0.96, 1.00] | 1.00 [0.94, 1.00] | {'runtime+ast': 66, 'judge': 23, 'fallback': 0} |
| instruct_chat_ban|t1 | 100 | 0.64 | 1.00 [0.80, 1.00] | 1.00 [0.96, 1.00] | 1.00 [0.95, 1.00] | {'runtime+ast': 80, 'judge': 20, 'fallback': 0} |
| instruct_chat_ban|t2 | 100 | 0.98 | 1.00 [0.80, 1.00] | 1.00 [0.96, 1.00] | 1.00 [0.93, 1.00] | {'runtime+ast': 54, 'judge': 46, 'fallback': 0} |
| steer:none:c=0|t1 | 100 | 1.00 | 1.00 [0.80, 1.00] | 1.00 [0.96, 1.00] | 1.00 [0.96, 1.00] | {'runtime+ast': 100, 'judge': 0, 'fallback': 0} |
| steer:none:c=0|t2 | 100 | 1.00 | 1.00 [0.80, 1.00] | 1.00 [0.96, 1.00] | 1.00 [0.96, 1.00] | {'runtime+ast': 100, 'judge': 0, 'fallback': 0} |
| steer:random1|t1 | 96 | 0.92 | 1.00 [0.80, 1.00] | 1.00 [0.96, 1.00] | 1.00 [0.92, 1.00] | {'runtime+ast': 45, 'judge': 51, 'fallback': 0} |
| steer:random1|t2 | 100 | 0.00 | 1.00 [0.80, 1.00] | 1.00 [0.96, 1.00] | – [–, –] | {'runtime+ast': 0, 'judge': 100, 'fallback': 0} |
| steer:random1_Ronly:c=1.0|t1 | 100 | 1.00 | 1.00 [0.80, 1.00] | 1.00 [0.96, 1.00] | 1.00 [0.96, 1.00] | {'runtime+ast': 100, 'judge': 0, 'fallback': 0} |
| steer:random1_Ronly:c=1.0|t2 | 100 | 0.85 | 1.00 [0.80, 1.00] | 1.00 [0.96, 1.00] | 1.00 [0.96, 1.00] | {'runtime+ast': 93, 'judge': 7, 'fallback': 0} |
| steer:random2|t1 | 98 | 0.30 | 1.00 [0.80, 1.00] | 1.00 [0.96, 1.00] | 1.00 [0.96, 1.00] | {'runtime+ast': 86, 'judge': 12, 'fallback': 0} |
| steer:random2|t2 | 100 | 0.85 | 1.00 [0.80, 1.00] | 1.00 [0.96, 1.00] | 1.00 [0.61, 1.00] | {'runtime+ast': 6, 'judge': 94, 'fallback': 0} |
| steer:sharpen_Ronly:c=1.0+nocutoff|t1 | 11 | 0.15 | 1.00 [0.74, 1.00] | 1.00 [0.74, 1.00] | 1.00 [0.44, 1.00] | {'runtime+ast': 3, 'judge': 8, 'fallback': 0} |
| steer:sharpen_Ronly:c=1.0+nocutoff|t2 | 8 | 0.79 | 1.00 [0.68, 1.00] | 1.00 [0.68, 1.00] | 1.00 [0.51, 1.00] | {'runtime+ast': 4, 'judge': 4, 'fallback': 0} |
| steer:sharpen_Ronly:c=1.0|t1 | 28 | 0.07 | 1.00 [0.80, 1.00] | 1.00 [0.88, 1.00] | 1.00 [0.78, 1.00] | {'runtime+ast': 14, 'judge': 14, 'fallback': 0} |
| steer:sharpen_Ronly:c=1.0|t2 | 5 | 1.00 | 1.00 [0.57, 1.00] | 1.00 [0.57, 1.00] | 1.00 [0.57, 1.00] | {'runtime+ast': 5, 'judge': 0, 'fallback': 0} |
| steer:single18:c=0.25|t1 | 50 | 1.00 | 1.00 [0.80, 1.00] | 1.00 [0.93, 1.00] | 1.00 [0.93, 1.00] | {'runtime+ast': 50, 'judge': 0, 'fallback': 0} |
| steer:single18:c=0.25|t2 | 50 | 0.00 | 1.00 [0.80, 1.00] | 1.00 [0.93, 1.00] | 1.00 [0.93, 1.00] | {'runtime+ast': 49, 'judge': 1, 'fallback': 0} |
| steer:single18:c=0.5|t1 | 50 | 1.00 | 1.00 [0.80, 1.00] | 1.00 [0.93, 1.00] | 1.00 [0.93, 1.00] | {'runtime+ast': 50, 'judge': 0, 'fallback': 0} |
| steer:single18:c=0.5|t2 | 50 | 0.66 | 1.00 [0.80, 1.00] | 1.00 [0.93, 1.00] | 1.00 [0.93, 1.00] | {'runtime+ast': 48, 'judge': 2, 'fallback': 0} |

### Priors (context, not tests)

- T2: {"invisible_lottery_table12": {"setting": "no cue, 15 configs, T=0, N=35 each", "dijkstra": 0.941, "bfs": 0.059}, "inspiration_repo_llm_creativity": {"setting": "claude-sonnet-5 weighted shortest path baseline", "dijkstra": "25/25", "cumulative_bans": "SPFA 16/25, Bellman-Ford 5/25", "ast_judge_agreement": "164/200"}}
- T1: {"note": "no published prior for the unweighted grid-path task"}

## Limitations and threats to validity

* **Two tasks only**: every verdict is per task; nothing here generalises over tasks (plan departure a).
* **Few correct base programs**: the base model's template-free code is mostly broken (pass 6–9 %), so Hill_cc for base arms rests on
  tens of correct programs even after the N=300 extension; Hill_all (all parseable programs) is the co-primary statistic (plan fallback 3)
  but it mixes in broken programs whose labels come mostly from the judge, which is exactly the differential-labeller-error confound named
  in the plan. Both are reported, with per-arm judge agreement next to them.
* **Labeller**: on base arms most final labels are judge labels (runtime and AST rarely agree on broken code); the judge was told to label
  buggy programs by the algorithm they attempt, and its `other:buggy_X` sub-labels were canonicalised arm-blind. Hill_cc for instruct arms
  is dominated by `runtime+ast` agreement.
* **Template-free vs chat prompts differ** by the format sentence (chat arms only) and by the docstring framing — a necessary difference,
  logged; the 2×2 isolates format from weights only within that definition of "format".
* **Steering**: the band-incremental scheme assumes downstream layers do not respond; the manipulation check shows they amplify the
  subtraction (cumulative change at layer 28 ≈ 1.9 × δ₂₈ at c = 1), so c = 1 overshoots past the base mean at layers 18–28. The direction is
  estimated at R and applied at generated positions where cos(δ_R, δ_gen) is only 0.15–0.42 in the band (departure d). HF arms use a uniform
  512-token no-code stop rule (arm-blind; never fires on S0).
* **One decoding setting** (T = 1, top-p 1, thinking off) and one model pair (Qwen3-8B / Qwen3-8B-Base).
* **Priors** (Invisible Lottery, inspiration repo) are printed as context only (different models, T = 0).

## Deviations from the plan

All deviations are recorded with reasons in `results/deviations.json` (also in `method_out.json → metadata.deviations`). The main ones:
custom common-random-number sampler for HF steering arms (exact per-sample coupling); uniform 512-token no-code stop rule for HF arms;
judge labels every distinct program (final label still follows the plan rule); arm-blind canonicalisation of judge `other:` sub-labels;
PREDICT primary = base_tf all-samples distribution (fallback 3, decided before phase C); runtime/AST labeller rule refinements after the
reference gate; A1/A2 extended to N = 300 per task for power (planned-N results reported as a sensitivity); fallback-6 single-layer arms
plus an R-only ablation with an R-only random control (extension); vLLM with `enforce_eager` (no C compiler in the container).
