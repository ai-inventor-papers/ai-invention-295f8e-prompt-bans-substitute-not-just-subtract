# Does one early token decide the algorithm? (iteration 7, bf16 Qwen3-8B)

## Results

**In short.** In Qwen3-8B the algorithm is not chosen by a direction in the prompt states that random pushes move along. It is decided at a few early generated tokens, where they exist.

- T10 has two forks at generated tokens 10 and 11. The probability mass a perturbed prompt puts on those fork tokens predicts which of 40 random pushes change the algorithm (Spearman 0.80).
- On T03 the opening-likelihood margin predicts 24 fresh, pre-committed directions (0.60).
- On T2 the decision comes late, so the 48-token margin fails. The committed F therefore fails as a two-task claim.
- A default-to-runner-up axis in the prompt states neither predicts nor mediates the random pushes.
- Pushed hard enough along that axis (4x the forced-prompt distance, beyond the committed doses), T10 does switch to DFS on 29/30 slots, against 0/30 for a matched random direction. So the axis is a sufficient control direction there, not the channel random pushes use.
- Moving the twin's states toward the survivor region of the grid-path catalogue never produces a survivor algorithm.
- On T10, forcing the single token that names the routine (`def dfs` instead of `def find`) flips the algorithm on every slot. Forcing a comment token does not.

### Bottom line

- **Committed verdicts.** F (the fork margin predicts which equal-dose random pushes escape) is **NOT SUPPORTED (inconclusive)**: it holds on T10 and fails on T2. P2 (the projection on a default-to-runner-up axis predicts it) is **DISCONFIRMED**. Holm-adjusted p is 0.357 for F and 0.458 for P2 (raw 0.179 and 0.458, the worst task).
- **One early token does decide the algorithm on T10.** The prefix-resampling screen finds two forks along the default opening `def solve(n, edges):`, at generated tokens 10 and 11 (shared by 94% of twin programs).
  - At token 10: `' #'` -> 1.00 non-default (n = 159), `' parent'` -> 0.00 non-default (n = 130), `' def'` -> 0.69 non-default (n = 72), `' from'` -> 1.00 non-default (n = 11).
  - At token 11, after `' def'`: `' dfs'` -> 1.00 (n = 45), `' find'` -> 0.00 (n = 32), `' count'` -> 1.00 (n = 2), `' build'` -> 1.00 (n = 1).
  - Label entropy given the token falls from 0.97 to 0.00 bits at token 11, and from 1.55 to 0.54 at token 10.
  - T2 has **no single early fork**. Pushed paths stay undecided through token 60, and the only change point (token 92) lies off the default opening.
  - On T03 the ban prompt fixes the class **before the first generated token**. Already at t = 0, only 0-2 of 8 continuations differ from the base path's class, and there is no change in 128 tokens.
- **F on T10.** The teacher-forced fork margin m predicts the correct off-default share y of the 40 random directions (alpha 2): Spearman **0.80**, permutation p 1.0e-04, 95% CI [0.62, 0.91].
  - The tie ceiling is 0.99 and Kendall tau 0.64.
  - AUC for exp29's 26 confirmed escapers: 0.81.
  - Spearman with the attempted share: 0.82; with the 48-token LLR instead of m: 0.87.
- **F on T2** (pre-declared fallback: the 48-token opening LLR, because there is no single fork): Spearman 0.15 (p 0.179).
  - Pooled within-task rho: 0.48 (p 1.0e-04).
  - The binomial-GLM calibration over all 104 cells of T10 and T2 has a held-out MAE of 0.25 (threshold 0.10); the all-cell Spearman is 0.51.
  - The twin margins are -3.51 nats (T10) and -6.02 nats (T2).
- **T03 prospective confirmation** (24 fresh directions; predictions hash-committed before generation).
  - The committed opening margin (the pre-declared no-fork fallback: a 20-token opening LLR, since T03 programs are about 20 tokens long) predicts y with Spearman **0.60** (one-sided p 0.001); 18 of 24 directions have y > 0.
  - The committed axis projection does not: 0.22 (p 0.150).
- **P2 is disconfirmed.** The default-to-runner-up axis projection (b) at L_ax (12 on T10, 24 on T2) gives Spearman 0.17 (p 0.141) on T10 and 0.01 (p 0.458) on T2.
  - It is not ahead of any competitor (T10/T2 Spearman: pi_Pt 0.06/0.12, norm 0.03/-0.05, a_share 0.14/-0.03).
  - The axis is not dormant: neutral prompts vary along it 220-400x more than along random directions. It is simply not the channel through which random pushes act.
- **Necessity (mediator clamp): NOT SUPPORTED.** Removing the axis component of the push at blocks L_ax..35 leaves 105 escapes, against 104 without the clamp (removed share -0.01).
  - A random-direction clamp gives 106; McNemar for the axis clamp is 9:10.
- **Sufficiency (targeted push along the axis): NOT SUPPORTED as committed.** No task escapes at s <= 1, and neither does the matched random direction.
  - At s = 1 the edit is only 0.14-0.18 of the norm that escaping random directions realise at L_ax.
  - The descriptive doses (fallback 8) locate the crossing on T10. At s = 4, 29/30 slots become correct DFS (pass 1.00); the matched random direction gives 0/30 (s = 2: 5/30).
  - On T2 there is no escape even at s = 8 (1/30). On T03, s = 8 moves 5/30 along the axis and 5/30 along the random direction, so the effect is not specific to the axis.
- **T1 in-manifold top-five push.** Pushes toward the survivor-region centroid, a random survivor, away from the banned centroid, and IDA* (s 0.25-1 of the centroid distance) give **0/300** non-top-five programs. Every arm writes BFS on 30/30 slots (pass 0.73-0.93).
  - The prompt top-five ban (exp30, N = 50) also stays in the banned set: {'bfs': 25, 'dfs': 23, 'unknown': 1, 'dijkstra_unit': 1}.
  - In real activation coordinates (Isomap k = 15 and PCs of forced-prompt S-mean states, block 18), the edge survivors are ['bibfs', 'dijkstra_unit', 'idastar'] and the opposite ones the rest.
  - The pushes move the twin's spec states toward the dijkstra_unit/jps region, but behaviour does not follow (figures/F6_*).
  - The old u_top5 push of iteration 4 leaves the manifold entirely (PC1 > 80 at alpha 8).
- **Engine robustness (pre-declared fallback 1).** Block-35 displacement norms differed by 2.35% from exp29, so all 40 directions were re-measured on this GPU.
  - Per-direction y correlates 0.95 (T10) and 0.93 (T2) with exp29 engine d.
  - F on this engine's outcomes is 0.77 / 0.12 and P2 is 0.25 / -0.04, so the conclusions are unchanged.
- **Stage 0 engine check.** Twin labels agree per slot with exp29 engine d at 1.00 (T10) and 0.97 (T2), and with exp30 at 1.00 (T2, T03, T10).
  - Pushed rows of the 40 directions (k 0-1, re-measured here) agree per slot at 0.97 (T10, n = 400) and 0.90 (T2, n = 400).
- **Exploratory, post hoc: where T2 decides.** The opening-LLR Spearman on T2 grows with the length of the teacher-forced opening: L = 16: 0.27, L = 32: 0.16, L = 48: 0.15, L = 96: 0.25, L = 128: 0.28, L = 160: 0.42. So T2's choice is carried by tokens beyond the first 48, consistent with its late change point.
- **Exploratory, post hoc: forcing one token under the unchanged neutral twin prompt** (N = 30 CRN slots per arm; the model completes the program itself).
  - T10: token 10 = ' #' (comment) -> {'union_find': 30} (pass 1.00, McNemar vs twin 0:0); token 10 = ' def' (free after it) -> {'union_find': 30} (pass 1.00, McNemar vs twin 0:0); token 10 = ' from' -> {'union_find': 20, 'dfs': 10} (pass 1.00, McNemar vs twin 10:0); token 10 = ' parent' -> {'union_find': 30} (pass 1.00, McNemar vs twin 0:0); tokens 10-11 = ' def dfs' -> {'dfs': 30} (pass 1.00, McNemar vs twin 30:0); tokens 10-11 = ' def find' -> {'union_find': 30} (pass 1.00, McNemar vs twin 0:0).
  - T03: first body token = ' #' (comment) -> {'full_sort': 25, 'quickselect': 4, 'heapify_pop': 1} (pass 1.00, McNemar vs twin 5:0); first body token = the twin's own -> {'full_sort': 29, 'quickselect': 1} (pass 1.00, McNemar vs twin 1:0).
  - T2: first body token = ' #' (comment) -> {'dijkstra': 30} (pass 1.00, McNemar vs twin 0:0); first body token = the twin's own -> {'dijkstra': 30} (pass 1.00, McNemar vs twin 0:0).
  - Reading: on T10 the token that names the routine decides. Writing `def dfs` instead of `def find` gives a correct DFS on every slot. A comment token (q = 1.00 in the pooled token map, built mostly from ban and pushed cells) leaves the twin on union-find. So the token map is cell-dependent for non-committal tokens, a limit of the margin construction.
- **Novelty audit.** Correct programs labelled 'other': 1; correct disputed or unknown: 1.
  - Classes: {'NOVEL ALGORITHM': 0, 'CATALOGUE VARIANT': 0, 'LABELLER MISS': 2, 'DEGENERATE': 0, 'unaudited': 0}. Spend USD 0.0004.
- **Cost.** 4220 generated programs and 4560 fork continuations, plus several thousand teacher-forced passes (margins, LLRs, axis and geometry captures) on one RTX 4090.
  - Generation batches logged 0.63 GPU-hours; with model loads and teacher forcing the GPU was busy about 1.7 hours of wall-clock.
  - OpenRouter: USD 0.0281.

### Tests and audits

- CPU tests (`results/unit_tests_cpu.json`):
  - The targeted-edit math, margin math and Spearman/permutation/tie-ceiling code pass (tie ceiling 0.62 for the 34-zero vector).
  - **C3 fails as specified**: a 0.4 jump with only three pre-jump screen positions is detected in 54% of simulations. The screen is underpowered for very early forks.
- GPU tests (`results/unit_tests_gpu.json`):
  - CRN determinism and the alpha-0 hook identity are bit-exact, and B = 1 vs B = 8 is invariant.
  - **U5 misses its 0.05 tolerance**: teacher-forced and KV-prefill log-probs differ by up to 0.25 on the top-50 tokens, with the same argmax. These are different SDPA paths in bf16; every margin uses the same teacher-forced path.
- The sha256 chain in `commitments.log` verifies. Every amendment (#0b, #1b, #1c, #3b) precedes the outcome rows it could affect, as listed in `results/deviations.jsonl`.
- `audit/rederive.py` re-derives the headline numbers with the standard library only (`results/rederive.json`): 199 checks, 0 mismatches.
  - The checks cover every y, the F/P2/T03 Spearmans, the tie ceilings, the targeted-push shares, and every T10 margin re-derived from the fork-token probabilities and the committed token maps.
  - Placebo, shuffled y: median null rho 0.01 (observed 0.80).
  - Placebo, shuffled fork-token map on T10: median null rho 0.22, but 18% of the 200 permutations reach the observed 0.80. With only 4-5 mapped tokens per fork, the permutations that keep a low q on the default tokens reproduce the effect.
  - So the margin's power comes from the probability of staying on the default fork tokens, not from the exact q values of the alternatives.
  - Re-run test: F: Spearman permutation test (T10). rho 0.80, permutation p 5.0e-04. On shuffled y it reaches p < 0.05 in 9% of 100 shuffles (it fails on placebo input).
  - Re-run test: T03 m: Spearman permutation test (T03). rho 0.60, permutation p 0.003. On shuffled y it reaches p < 0.05 in 3% of 100 shuffles (it fails on placebo input).
  - Re-run test: targeted push T10 s=4: axis vs matched random (exact McNemar). Discordant 30:0, exact p 1.9e-09. A random arm swap reaches p < 0.05 in 8% of 200 swaps.
  - Re-run test: forced token ' def dfs' vs twin on T10 (exact McNemar, exploratory). Discordant 30:0, exact p 1.9e-09. A random arm swap reaches p < 0.05 in 6% of 200 swaps.
  - Re-counted from the raw label rows: 0 non-top-five programs among 300 T1 push rows (300 BFS).

### Limits

- One model (Qwen3-8B, bf16), memorised LeetCode-style tasks, two primary tasks and one confirmation task.
- The 40 primary outcomes come from exp29 (another GPU, N = 10-30). This run's re-measurement agrees.
- The fork screen is sparse (S = 8 every 4th token) and misses weak or very early forks.
- T03's base paths are ban paths only.
- T1 10-algorithm labels are AST-only.
- Everything marked exploratory was decided after seeing the committed results.

## What was run

Model: `Qwen/Qwen3-8B` at revision `b968826d9c46dd6066d109eabc6255188de91218`, bf16 weights and activations,
thinking off, T = 1.0, top-p 1, no top-k, fence stop. The engine is exp29's engine-d weight set (`engines.load_b`:
bf16 decoder linears via `F.linear`, CPU-resident exact embedding gather). It ran on one RTX 4090; the plan named an
RTX A4500, and exp29's engine-d outcomes came from an RTX 2000 Ada. Every arm of a task shares the common-random-number
(CRN) uniforms of slot (task, template, k), so arms are paired per slot.

Tasks: T10 connected components (default union-find, runner-up DFS), T2 weighted shortest path (Dijkstra ->
Bellman-Ford/SPFA), T03 k-th smallest (full sort -> quickselect), T1 grid path (BFS; top-five prohibition).

Baselines and controls:

- Matched-norm random directions for every push.
- The P_t subspace energy, the raw displacement norm and the U4 energy as competitors of the axis predictor, all
  computed from the same displacement vectors.
- The prompt ceilings: ban, forced, and exchange cells.
- A random-survivor null for the top-five push, with the prompt top-five ban beside it.
- A matched random-direction clamp.
- Permutation p values and tie ceilings for every Spearman, exact McNemar on CRN-paired flips, and Holm over {F, P2}.

Stages, in the committed order (sha256 chain in `commitments.log`, genesis `sha256('iter7_dir3')`):

1. **Stage 0 (engine check)**: twin cells W1-W5 x k 0-5 on T2, T03, T10 and T1. Directions 9101-9105 x N = 10 on
   T10/T2, kept sealed until commit #3. Realised displacement norms against exp29. GPU unit tests U1-U3, U5, U8.
2. **F1 forks (commit #1, amended #1b/#1c before any margin)**:
   - Prefix resampling on 48 correct base paths: default twin paths, ban paths, and per-sample-noise paths with their
     hook active.
   - Positions 0-60 every 4 tokens at S = 8, plus a 64-128 extension every 8 tokens.
   - Change points use exp31's exhaustive binomial segmentation with a 1,000-permutation null.
   - Forks are localised token by token and confirmed at S = 20.
   - The output is the canonical default opening, the fork set and the token maps.
3. **P2 axis (commit #2)**: the difference in means between forced-runner-up prompts (10 frames) and their ' .'
   padding twins at blocks 12-35. The layer is chosen by leave-one-out separation. Also computed: D(L, j), the
   natural-variance guard, U4 and P_t. No outcome data is used.
4. **Predictors and margins (commit #3, amended #3b before any outcome row was opened)**: one teacher-forced pass per
   (cell, template), plus per sample for the PN cells. It gives:
   - the fork margin m (sequential multi-fork rule), or the pre-declared opening LLR where no single fork exists;
   - the axis projection (b);
   - the competitors (P_t energy share, raw norm, U4 energy share).
5. **Analysis, frozen by hash in commit #0b**:
   - F, P2 and the T03 prospective confirmation.
   - The targeted push along the axis against a matched random direction (spec in commit #4). Fallback 8 adds the
     descriptive doses s = 2, 4, 8.
   - The mediator clamp.
   - The T1 in-manifold top-five push against a random-survivor null, with geometry in actual activation coordinates
     (`src/top5geo.py`).
   - The same-engine re-measurement of the 40 directions (fallback 1).
   - The novelty audit.
6. **Exploratory, post hoc** (labelled as such everywhere):
   - the opening LLR at lengths of 16-160 tokens (`src/explore_llr.py`);
   - forcing single fork tokens under the unchanged twin prompt (`src/force_token.py`).

## Layout

| path | content |
|---|---|
| `method.py` | orchestrator: runs every stage in order (`--stages`), resumable |
| `src/c7.py` | paths, constants, hash chain, blindness guard (`guarded_e29_rows`), latest-commit helpers |
| `src/engine7.py` | bf16 engine wrapper, edits (targeted, clamp, per-position u), stop-callback sampler, teacher forcing |
| `src/prompts7.py` | prompt records (prompts4 twins/bans/named, exp9 T1 forced, exp30 top5ban, padding twins) |
| `src/gen7.py` | CRN generation runner (exp29 design: constant batch shape, TWIN filler slots) |
| `src/label7.py` | frozen labeller (exp29 label_worker6) + exp9 10-algorithm T1 labels (`label10`) |
| `src/stage0.py` | Stage 0 + GPU unit tests |
| `src/fork7.py`, `src/forkrun.py` | opening classifiers, base paths, prefix resampling, change points, fork definitions |
| `src/axis7.py` | P2 axis (A1-A6) |
| `src/predict7.py` | predictors, margins, LLR (P.1-P.4) |
| `src/pushrun.py`, `run_after_c3.sh` | T03 confirmation, targeted push (+ fallback-8 doses), top-five push, re-measurement, clamp |
| `src/analysis7.py`, `src/analysis_push.py`, `src/top5geo.py`, `src/stats7.py`, `src/select_clamp.py` | pre-registered analyses |
| `src/explore_llr.py`, `src/force_token.py`, `src/analysis_force.py` | exploratory, post hoc analyses |
| `src/figures7.py`, `src/outputs7.py`, `src/readme7.py`, `src/summary7.py` | figures, `method_out.json`, README results, timing/cost |
| `src/novelty7.py`, `src/dep7.py` | novelty audit; known-solution corpus from the dependency dataset |
| `src/make_commit0.py`, `src/make_commit0b.py` | commit #0 (rules, thresholds) and #0b (analysis code hashes) |
| `src/tests_cpu.py`, `src/fork_probs.py`, `audit/rederive.py` | CPU tests C1-C8; T10 fork-token probabilities; stdlib re-derivation of the headline numbers with placebos |
| `predictions/` | commit files (#0, #0b, #1, #1b, #1c, #2, #3, #3b, #4; #5/#6 = post-analysis code provenance) and `hardware.json` |
| `data/` | every generated program (`samples_raw*.jsonl`), labels (`labels*.jsonl`), fork continuations, judge calls |
| `results/` | analysis JSONs (`f_analysis.json`, `p2_analysis.json`, `t03_confirmation.json`, `forks.json`, `axis.json`, `targeted_push.json`, `clamp.json`, `remeasure.json`, `top5_landing.json`, `top5_geometry.json`, `engine_check.json`, `explore_llr.json`, `force_token.json`, `novelty_audit.json`, `unit_tests_*.json`, `deviations.jsonl`, `rederive.json`) |
| `figures/` | F1 fork series, F2 margin vs outcome, F3 axis vs competitors, F4 layer profile, F5 targeted push, F6 T1 geometry (two layers), F7 clamp (PNG + PDF) |
| `cache/states/` | committed axes, per-direction displacements, T1 states (see the manifest) |
| `inputs/`, `vendor/` | read-only copies of the earlier artifacts' data and code (iterations 1-6) |
| `method_out.json` | exp_gen_sol_out output; `full_`/`mini_`/`preview_` variants beside it |
| `reproducibility.md`, `pyproject.toml` | exact reproduction steps (what was run, in order); every installed package pinned |

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python method.py --stages all   # or a comma list: stage0,forks,axis,freeze,predict,push,analysis,outputs
```

`method.py` starts the follow-mode label worker (`src/label7.py`) itself. Every stage is resumable by row keys and
commit files. The model is read from the Hugging Face cache (`HF_HUB_CACHE`).

## Restoring removed files

`.aii/manifest.yaml` deletes only regenerable bulk. These are the commands that bring every deleted path back:

- `.venv/`: `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml`
- `cache/states/top5_T1_states.npz` (478 MB): `.venv/bin/python src/pushrun.py top5core`. This recomputes the T1
  forced-prompt states in about 1 GPU-minute, then skips the finished generation rows.

The model weights are never stored here:
`huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218`.

The known-solution corpus (`cache/known_corpus.jsonl`, a text file of third-party licensed code) stays on the run's
volume but is left out of the published repository. Rebuild it with `.venv/bin/python src/dep7.py` from the
`art_j3Rm_lr2nzR6` dependency.

Kept artifacts (`cache/states/dbar_*.npz`, `cache/states/top5_push_states.npz`, and the small `cache/states/axis_*.npz`)
stay on the run's storage volume at these relative paths. The publish step skips any file of 100 MB or more; all kept
files are smaller.
