# Pricing plan noise against temperature (iteration 4, Step 1 / Claim 1)

Qwen3-8B (pinned revision `b968826d…`, thinking off) writes Python solutions to algorithm tasks. Most of the time it
writes one default algorithm (full sort for the k-th smallest element, a hash map for two-sum, Dijkstra for weighted
shortest paths, …). This repository asks a pricing question: **which knob buys CORRECT algorithmic diversity most
cheaply?** The candidate is **fresh per-sample plan noise (PN)**. For each sample, one isotropic unit direction (a
fresh seed per sample) is added at the task-specification positions of decoder blocks 12–23, during the prompt
prefill only. The edit is displacement-targeted, and its size alpha is measured in "ban units" per block and position.
PN is priced against:

- temperature (1.3, 1.6, untruncated) and top-k 10;
- the nonce ban ("Do not use the Zorblax method…");
- the novelty instruction and the semantic seed (path tasks);
- the iteration-3 signature vetoes (one-shot, persistent, iterated; reused rows);
- as pre-registered sensitivities, min-p 0.1 at T 1.6 / 2.0 and a verbalized-sampling prompt.

Every knob is scored with the same statistic and price convention:

- **Statistic:** correct-only Hill-1, rarefied at depth 25.
- **H5:** the largest Hill reachable at a pass cost of at most 5 points, on the knob's randomisation hull (mixtures of
  the reference arm and the knob's settings).
- **P15 and P20:** the cheapest cost at which Hill reaches 1.5 or 2.
- **Uncertainty:** 2,000-replicate bootstraps, with the best-setting choice made inside every replicate.

All arms share exact common random numbers (CRN): the same uniform stream per (task, template, slot).

## Results

**Design actually run.**

- 10,100 labelled programs, every cell at N = 50 (5 templates × 10 CRN slots). No cell was dropped: the time rule kept the whole queue.
- E6 + R2: 7 tasks × up to 17 arms.
- The 8 non-movable bench tasks: 11 arms each.
- Engine: Qwen3-8B FP8 W8A8 on a 16 GB RTX 2000 Ada; 2.53 GPU-hours of batch time.
- Judge and audit spend: USD 0.23.

**Bottom line.** Under the pre-registered rule, C1 is **PARTIAL**. Plan noise is not the uniformly cheapest knob.

**Where PN wins.** On 4 of the 6 decisive tasks, PN buys more correct diversity at a cost of at most 5 pass points than
any non-activation knob:

- T03 (k-th smallest): H5 2.72 against 1.96 for the novelty instruction; PN is ahead in every bootstrap replicate.
- T10 (connected components): 2.09 against 1.96 for the iterated veto; PN is ahead in 91% of replicates.
- T05 and T1: small, uncertain edges. T05: 1.29 vs 1.24; T1: 1.42 vs 1.34.

On T03 and T10, PN reaches Hill 1.5 and Hill 2 at zero pass cost.

**Where PN loses, and why the rule is not met.** PN loses decisively on two tasks:

- T06 (find duplicate): PN does not move hash_set at all at alpha <= 2. The reused iterated veto reaches 2.73.
- T2 (weighted shortest path): the semantic seed reaches 1.93 against PN's 1.35. PN's Bellman–Ford/SPFA programs
  cost 14–26 pass points.

The pooled margin D̄ is therefore −0.22 (task-bootstrap 95% CI [−0.89, 0.30]). Only 2 tasks reach H5 ≥ 1.5, against
the 3 required, and the CI includes 0. Every pre-registered sensitivity gives the same PARTIAL verdict (s1–s8):

- twin-segment hull;
- min-p and verbalized sampling added to the comparison set;
- dial interpolation;
- template-cluster and slot-paired bootstraps;
- both 'other' conventions;
- reused vetoes excluded;
- Step-0 vertices only.

With the reused iteration-3 vetoes excluded (s7), D̄ turns positive: +0.20, 95% CI [−0.19, 0.60]. Without them, PN
loses only to the semantic seed on T2.

**What the comparison knobs did.**

- **Temperature (1.3, 1.6), top-k 10 and the nonce ban buy no correct algorithmic diversity on any E6 task** (H5 ≤ 1.09
  everywhere).
- Min-p at T 1.6 / 2.0 stays at H5 ≤ 1.17.
- The novelty instruction switches T03 wholesale to quickselect. That gives Hill 1.0 on its own, and 1.96 only when
  mixed with the twin.
- The verbalized-sampling (VS) prompt mostly produces *programs that choose an algorithm at run time*: 46–49 of 50 on
  every bench task and T1 call `random.choice(s)` inside `solve()`. Their mechanism label is whichever branch the
  labeller's trace happened to execute, so VS "diversity" is partly a measurement artifact
  (`results/vs_dispatch.json`).

**Ideas vs phrasings (CRN flips).**

- Temperature rewrites code without changing the algorithm. On T1, T1.6 changes the code in 88% of CRN slots and the
  label in 2%; it raises phrasing clusters within BFS from 13.6 to 18.5 (20 programs, Jaccard ≥ 0.8).
- PN changes the algorithm. At alpha 2 the label differs from the twin's in 50% (T03), 60% (T10) and 54% (T2) of slots.
- Top-k 10 never changed a single token sequence: the model's top-10 mass is essentially 1 on these prompts.

**Dose-response.** Off-default share rises monotonically with alpha up to 2 on T03, T10, T1 and T2; T05 and T06 stay
pinned to their default until alpha 4. The breakage point (pass below 0.8 × the twin's) is alpha 4 on T03, T06, T10
and T1, alpha 2 on T2 and alpha 8 on T05; at alpha 8 almost nothing passes. The realised displacement at block 12 is within 0.15% of its target on
all 3,220 PN rows (relative error along u at most 0.0017).

**Held-out task and non-movable tasks.**

- R2 (cycle detection, held out) barely moves under PN: an off-default excess of 0.01 at alpha ≤ 2, H5 1.09, and
  P15 = 29 points.
- On the 8 non-movable bench tasks, PN at alpha ≤ 2 moves almost nothing: off-default excess ≤ 0.04, and H5 between 1.00 and 1.14. The exception is R6, at 1.37, where temperature also reaches 1.42. This agrees with the screen's classification. The strongest knob there is the novelty instruction on T04 (substring search, H5 2.57); the table is below.

**The neutral twin's prohibition frame is inert for algorithm choice.** PLAIN (specification only) and the twin have
identical off-default shares on 5 of the 6 E6 tasks (T2: +0.02), although the frame costs 18 pass points on T1 and
adds 22 on R2.

**Screen forecast** (committed before stage 100). The forecast treated fresh noise as an equal mixture of the screen's
fixed directions. It predicted the C1 outcome correctly (PARTIAL) and the PN alpha-1 composition within the
resampling null on 5 of 6 tasks. It over-predicted T06 (1.76 forecast against 1.00 realised) and T05, and
under-predicted T10.

**Engine and labeller checks.**

- **Engine:** reproduction is bit-exact. Two exp17 screen rows were re-run with the screen's own keys: per-slot label
  agreement 1.00 on all 4 cells, JSD 0 (REPRODUCED).
- **GPU unit tests U1–U6:** all pass. This includes exact alpha-0 coupling (20/20 and 10/10 with other batch-mates),
  displacement accuracy (relative error along u ≤ 0.001), and fence-stop invariance (20/20 bench, 20/20 path).
- **Labeller re-check:** bench labellers recover 100% of references on all 13 tasks, and gold agreement is within 0.02
  of every gate.
- **Novelty audit:** every correct 'other' program is a labeller miss; **0 novel algorithms**. Controls: 10/10 for both
  judges.
- **Label-validity audit:** judge–labeller agreement is 1.00 everywhere except T03 (0.80 for PN and for the novelty
  arm). Re-scoring T03 with the judge's labels leaves D_t at +0.71 (vs +0.76).
- **Placebos:**
  - Replacing every PN setting by the TWIN rows gives D_t ≤ 0 on all 6 tasks.
  - Arm labels shuffled within tasks (100 shuffles): the full committed rule, with the reused vetoes in the comparison set and the bootstrap CI, never returns CONFIRMED (0/100; the count criteria fire in 2/100; `results/placebo_full_rule.json`).
  - The independent re-derivation's stricter counts-only version, without the vetoes, fires in 8/100. That is above the 5% target: the count criteria alone are not selective under exchangeable arms, partly because PN has 4 settings against 1–3 per comparison class. The CI criterion is what keeps the rule specific.
- **Independent re-derivation** (`audit/rederive.py`): 12/12 checks match (counts, every D_t, engine-check JSD), and the hash chain is unbroken. Commit #1 (05:05:55Z) precedes the first row beyond stage 10 (05:06:15Z).

**Precision caveat (carried into every C1 statement).** This machine has a 16 GB GPU, so all rows ran with the FP8 W8A8
engine of the screen (`load_model(fp8=True)`), not the planned bf16. The engine check therefore shows that the
screen's engine is reproduced exactly. It does not measure an FP8-vs-bf16 gap.

### Numbers (generated from the result files: `results/summary.md`)

**C1 (pre-registered rule): PARTIAL** (failed: count1>=3, CI_low>0).
count1 = #{t: H5_PN >= 1.5} = 2/6; count2 = #{t: H5_PN > H5_best} = 4/6; best NA knob beats PN on 2 tasks; D_bar = -0.218 (task bootstrap 95% CI [-0.893, 0.304], one-sided p_C1 = 0.7576); exact sign test over the 6 D_t: p = 0.3438.

| Task (default) | H5 PN | best NA knob | H5 best NA | D_t [95% CI] | P(H5_PN > H5_best) | P15 PN | P20 PN |
|---|---|---|---|---|---|---|---|
| T03 (full_sort) | 2.72 | NOVELTY | 1.96 | 0.76 [0.21, 1.16] | 1.00 | 0.0 | 0.0 |
| T05 (hash_map) | 1.29 | NOVELTY | 1.24 | 0.05 [-0.20, 0.37] | 0.67 | 11.1 | – |
| T06 (hash_set) | 1.00 | VETO_ITER | 2.73 | -1.73 [-2.06, -1.39] | 0.00 | – | – |
| T10 (union_find) | 2.09 | VETO_ITER | 1.96 | 0.13 [-0.00, 0.37] | 0.91 | 0.0 | 0.0 |
| T1 (bfs) | 1.42 | NOVELTY | 1.34 | 0.07 [-0.57, 0.41] | 0.49 | 18.0 | 49.8 |
| T2 (dijkstra) | 1.35 | SEMSEED | 1.93 | -0.58 [-0.69, -0.14] | 0.00 | 9.3 | – |

H5 per knob class on E6 (randomisation hull, cost <= 5 points; 95% bootstrap CI in results/c1.json `class_ci`):

| Task | PN | TEMP | TOPK10 | NONCE | NOVELTY | SEMSEED | VETO_1SHOT | VETO_PERSIST | VETO_ITER | MINP | VS |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T03 | 2.72 | 1.09 | 1.00 | 1.00 | 1.96 | – | 1.90 | 1.88 | 1.89 | 1.16 | 1.29 |
| T05 | 1.29 | 1.00 | 1.00 | 1.00 | 1.24 | – | 1.00 | 1.00 | 1.00 | 1.00 | 1.04 |
| T06 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | – | 1.00 | 1.00 | 2.73 | 1.00 | 1.01 |
| T10 | 2.09 | 1.00 | 1.00 | 1.00 | 1.17 | – | 1.02 | 1.03 | 1.96 | 1.09 | 1.02 |
| T1 | 1.42 | 1.00 | 1.00 | 1.00 | 1.34 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| T2 | 1.35 | 1.09 | 1.00 | 1.00 | 1.24 | 1.93 | 1.00 | 1.00 | 1.00 | 1.17 | 1.00 |

Sensitivities (each re-evaluates the full rule):

| Sensitivity | verdict | count1 | count2 | D_bar [95% CI] |
|---|---|---|---|---|
| s1_twin_segment_hull | PARTIAL | 2 | 3 | -0.266 [-0.905, 0.246] |
| s2_minp_vs_added | PARTIAL | 2 | 4 | -0.218 [-0.897, 0.314] |
| s2b_minp_only_added | PARTIAL | 2 | 4 | -0.218 [-0.863, 0.305] |
| s3_dial_interpolation | PARTIAL | 2 | 4 | -0.022 [-0.710, 0.607] |
| s4_template_cluster_bootstrap | PARTIAL | 2 | 4 | -0.218 [-0.866, 0.329] |
| s5_slot_paired_bootstrap | PARTIAL | 2 | 4 | -0.218 [-0.893, 0.322] |
| s6_other_exclude | PARTIAL | 2 | 4 | -0.243 [-0.892, 0.263] |
| s6_other_one | PARTIAL | 2 | 4 | -0.219 [-0.892, 0.326] |
| s7_reused_vetoes_excluded | PARTIAL | 2 | 4 | 0.202 [-0.188, 0.600] |
| s8_step0_vertices_only | PARTIAL | 2 | 3 | -0.134 [-0.721, 0.512] |

Engine check: **REPRODUCED** — per-slot label agreement T03|NEUTRAL 1.00, T03|RAND9002_a1.0 1.00, T2|NEUTRAL 1.00, T2|RAND9004_a1.0 1.00.
Novelty audit: 12 unique correct 'other' programs, classes {'LABELLER MISS': 12}; confirmed NOVEL = 0; judges A/B agree on 8/10 (Cohen's kappa 0.00 is uninformative when one class dominates); controls 10/10; complete = True.
Label-validity audit (judge vs labeller agreement): T03|PN_alpha_le2 0.80 (n 10), T03|best_NA 0.80 (n 10), T05|PN_alpha_le2 1.00 (n 1), T05|best_NA 1.00 (n 3), T06|best_NA 1.00 (n 10), T10|PN_alpha_le2 1.00 (n 10), T10|best_NA 1.00 (n 10), T1|PN_alpha_le2 1.00 (n 5), T1|best_NA 1.00 (n 9), T2|PN_alpha_le2 1.00 (n 10), T2|best_NA 1.00 (n 10).

R2 (held out) and the 8 non-movable bench tasks (E6 H5_PN for comparison: min 1.00, median 1.38, max 2.72):

| Task | PN off-default excess (alpha <= 2) | H5 PN | H5 TEMP | H5 NONCE | H5 NOVELTY | P15 PN |
|---|---|---|---|---|---|---|
| R1 | 0.00 | 1.00 | 1.00 | 1.00 | 1.00 | – |
| R2 (held out) | 0.01 | 1.09 | 1.00 | 1.00 | 1.37 | 29.0 |
| R3 | 0.00 | 1.00 | 1.00 | 1.00 | 1.00 | – |
| R6 | -0.08 | 1.37 | 1.42 | 1.21 | 1.20 | – |
| T04 | 0.00 | 1.00 | 1.00 | 1.00 | 2.57 | – |
| T08 | 0.01 | 1.00 | 1.00 | 1.00 | 1.04 | – |
| T11 | 0.03 | 1.01 | 1.00 | 1.00 | 1.05 | – |
| T13 | 0.00 | 1.00 | 1.00 | 1.00 | 1.00 | – |
| T14 | 0.04 | 1.14 | 1.00 | 1.00 | 1.00 | – |

Independent re-derivation: 12/12 checks match; arm-shuffle placebo fires 8/100; PN-replaced-by-TWIN placebo D_t <= 0: True; hash chain breaks 0, commit precedes stage 1: True.
GPU: 10100 rows in 640 batches, 2.53 GPU-hours of batch time; 67 rows hit the 1,024-token cap.
OpenRouter spend: USD 0.227 (cap 1.00).

## What was run

| Stage | What | Where |
|---|---|---|
| 0 | input copies + sha256 (`inputs/SHA256SUMS`), bench files vs `bench/commitment.json`, labeller re-check (13 bench tasks + exp8 suite) | `src/s0_checks.py`, `results/input_hashes.json`, `results/labeller_recheck.json` |
| 0.5 | screen file from iteration-3 rows (exp17 FP8 random directions, exp13 rand1–3), escape / confirmed-escape per direction, reconciliation | `src/screen.py`, `results/screen.json` (+ `.sha256`) |
| 0.6 | 205 prompts (twin, plain, nonce, novelty, semantic seed, verbalized sampling); identical task-spec ids across arms asserted; R2 alias audit (0 hits) | `src/prompts_v4.py`, `data/prompts.jsonl`, `results/prompt_report.json` |
| 0.7 | ban unit `n[l,p]`: exp13 norms (bench), exp17 norms (T1/T2), R2 ban-free unit from the median norm ratio of 12 tasks (+ leave-one-task-out calibration) | `results/unit_r2.json`, `results/unit_R2.npy` |
| 1 | engine = exp17 FP8 engine + per-row T / top-k / min-p + exp16 fence stop + one prefill per PN row | `src/engine_v4.py`, `src/hooks.py` (exp17, unchanged), `src/sampling_v4.py` |
| 2 | GPU unit tests U1–U6 (CRN determinism, exact alpha-0 coupling, displacement accuracy, memory, fence-stop invariance, sampler masks) | `src/gpu_stage.py`, `results/unit_tests_gpu.json` |
| 3 | engine check: two exp17 screen rows reproduced with the screen's own CRN keys | `src/analysis/engine_check.py`, `results/engine_check.json` |
| 4 | stage 10 → hash commit (rule, forecast, code, screen, engine verdict) → stage 100 → timing rule → full priority queue | `src/prereg.py`, `commitments.log`, `predictions/`, `results/timing_plan.json` |
| 5 | labelling (frozen runtime/AST labellers, blind judge on disagreement), reused veto rows | `src/label_worker_v4.py`, `data/labels.jsonl`, `data/reused_rows.jsonl` |
| 6 | analysis: knob rows, hull prices, bootstraps, C1 + sensitivities s1–s8, descriptive (a)–(g) | `src/analysis/`, `results/` |
| 7 | novelty audit of every correct 'other' program; label-validity audit | `src/audit_llm.py`, `audit/` |
| 8 | figures, `method_out.json`, independent re-derivation + placebos | `src/figures.py`, `src/outputs.py`, `audit/rederive.py` |

## Layout

| Path | What it holds |
|---|---|
| `method.py` | orchestrator: `prompts`, `inputs`, `screen`, `gpu`, `label`, `label_ec`, `commit`, `audit`, `analyze`, `validity`, `report` |
| `src/cfg.py` | constants, arms (decoding / prompt / alpha per arm), paths, utilities, seeds |
| `src/engine_v4.py` | FP8 W8A8 loader, hooked prefill, CRN inverse-CDF sampler (`sample_exp17` kept verbatim for the unit test), the extended `sample()` |
| `src/hooks.py` | exp17 displacement-targeted edits (`make_edits('RAND', …)`), unchanged |
| `src/prompts_v4.py` | prompt rendering and assertions |
| `src/sampling_v4.py` | task context (clean / edited prefills, realised displacement), batch runner, priority queue |
| `src/gpu_stage.py` | unit tests, R2 unit, engine check, stages 10 / 100, timing rule, full queue |
| `src/label_worker_v4.py` | labeller (exp17 worker adapted; 13 bench tasks + T1/T2) |
| `src/screen.py` | screen file, reused rows |
| `src/prereg.py`, `src/commit.py` | commitment (rule + forecast + hashes) and the sha256 chain |
| `src/analysis/hull.py` | randomisation hull, population-rarefied Hill, H5 / P15 / P20, unit tests |
| `src/analysis/core.py` | knob classes, vertices, knob rows, bootstraps, the C1 rule |
| `src/analysis/run_all.py` | the full analysis (prices, bootstraps, C1 + s1–s8) |
| `src/analysis/descriptive.py` | descriptive analyses (a)–(g) |
| `src/analysis/stats_step0.py` | the Step-0 `rarefied_hill1` / `boot_rarefied_hill1`, byte-identical copy of the iteration-3 evaluation's `common/stats.py` |
| `src/analysis/metrics_exp6.py` | exp6 identifier-normalised AST shingles and threshold clustering, verbatim |
| `src/audit_llm.py` | novelty audit + label-validity audit (OpenRouter) |
| `src/dep_usage.py` | the declared dataset dependency: known-solution corpus for every task, external T2 comparator, noun provenance |
| `src/figures.py`, `src/outputs.py` | figures; `method_out.json` and its mini/preview variants |
| `audit/rederive.py` | independent recomputation of the headline numbers, placebos, hash-chain check |
| `audit/placebo_full_rule.py` | the full committed rule (counts + bootstrap CI) under 100 arm-label shuffles |
| `audit/rederive_extra.py` | second raw-file check (engine-check per-slot agreement, N = 50 in all 202 cells, T03 compositions) |
| `reproducibility.md` | exact commands in the order they were run (with the restarts), hardware, versions, seeds, runtimes |
| `audit/manual_pass.json` | the executor's manual pass over every audited 'other' program |
| `finalize.sh` | the post-generation pipeline (audit → analysis → validity audit → figures → outputs → re-derivation → README) |
| `src/report_numbers.py`, `src/readme_results.md` | generated headline tables (`results/summary.md`) and the README results text |
| `data/samples_raw.jsonl` | every generated row (text, token ids, seeds, decoding, realised displacement summary) |
| `data/labels.jsonl` | one label row per sample |
| `data/samples.jsonl` | merged per-sample rows (the file every analysis reads) |
| `data/realised.jsonl` | realised displacement of every PN prefill (blocks 12–35, spec mean and read position, error along u) |
| `data/reused_rows.jsonl` | iteration-3 veto rows and their own twins (engine-flagged) |
| `data/engine_check_*.jsonl` | the engine-check rows and labels |
| `predictions/` | `c1_rule.json`, `screen_forecast.json`, `analysis_code.sha256`, `engine_check_verdict.json`, `amendments/` |
| `commitments.log` | sha256 chain (commit1 → amend1 → commit2 …) |
| `results/` | every analysis file (see "Results files" below) |
| `audit/` | `novelty_audit.json`, `other_map.json`, `label_validity.json`, LLM cache/spend, `rederive.py` |
| `figures/` | fig1–fig6 (PDF + PNG) |
| `inputs/` | read-only copies of the iteration-1/2/3 inputs (+ `SHA256SUMS`) |
| `method_out.json` (+ `full_`/`mini_`/`preview_`) | exp_gen_sol_out: datasets `knob_rows` and `samples`, everything else in `metadata` |

## Results files

| File | Content |
|---|---|
| `results/c1.json` | C1 decision: primary + s1–s8 (+ labelled post-hoc s2b), per-task D_t with bootstrap CIs, P(PN > best), class CIs |
| `results/prices.json` | point estimates per task × class: H5, P15, P20, hull edge/lambda, twin-segment hull, dial interpolation, Step-0 vertices, triangle-face check, vertex gap |
| `results/knob_rows.jsonl` | one row per (task, arm): N, pass, pass cost, correct composition, Step-0 Hill-1 at depth 25 with 90% CI (merge-ready for the next evaluation) |
| `results/bootstrap_primary.json`, `results/boot_cache/` | per-replicate H5/P15/P20 per task × class (2,000 replicates) |
| `results/engine_check.json` | engine check per cell (screen vs this run, per-slot agreement, JSD vs template-resampling null) |
| `results/unit_tests_gpu.json`, `results/hull_unit_tests.json` | GPU unit tests U1–U6; hull unit tests (a)–(d) + SLSQP diagnostic |
| `results/labeller_recheck.json`, `results/input_hashes.json` | labeller re-check; input hashes vs the bench commitment |
| `results/screen.json` (+ `.sha256`) | screen escapes, confirmed escapes, E_t, push-landing distribution, reconciliation |
| `results/unit_r2.json`, `results/unit_R2.npy` | R2 ban-free unit and its leave-one-task-out calibration |
| `results/alpha_sweep.json` | alpha 0–8 dose-response on E6 (pass, invalid, cap hits, off-default, Hill, realised displacement, breakage) |
| `results/flips.json` | CRN flips vs TWIN: P(code differs), P(label differs), P(label differs given code differs) |
| `results/ideas_phrasings.json` | ideas (Hill) vs phrasing clusters within the default idea (theta 0.7/0.8/0.9, equal depth 20) |
| `results/plain_vs_twin.json` | PLAIN vs TWIN and PNPLAIN_a1 vs PN_a1, slot-paired bootstrap CIs |
| `results/nonmovable.json` | R2 and the 8 non-movable bench tasks |
| `results/forecast_score.json` | committed screen-mixture forecast vs realised PN |
| `results/per_template.json`, `results/vs_dispatch.json` | off-default share per template; run-time random-dispatch programs per arm |
| `results/dependency_usage.json` | use of every dataset of `art_j3Rm_lr2nzR6` |
| `results/timing_plan.json`, `results/timing_batches.jsonl`, `results/timing_summary.json`, `results/queue_result.json` | stage-100 extrapolation and the time rule; per-batch timing; not-run cells |
| `results/costs.json` | OpenRouter spend by ledger |
| `results/deviations.jsonl` | every deviation and amendment, with its reason |
| `results/rederive.json` | independent re-derivation, placebos, hash-chain check |
| `results/summary.md` | the generated headline tables used in this README |

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218
.venv/bin/python method.py prompts
.venv/bin/python method.py inputs
.venv/bin/python method.py screen
.venv/bin/python method.py gpu --deadline-utc <ISO time to stop starting batches> &   # waits for the commit
.venv/bin/python method.py label_ec                     # after the engine-check rows exist
.venv/bin/python method.py label &                      # follows data/samples_raw.jsonl until the GPU finishes
.venv/bin/python method.py commit                       # rule + forecast + hashes; releases stage 100
# after the GPU stage and the labeller finish:
.venv/bin/python method.py audit
.venv/bin/python method.py analyze
.venv/bin/python method.py validity
.venv/bin/python method.py report
```

Requirements:

- A GPU with FP8 support (compute capability 8.9 or higher) and at least 16 GB of memory. The engine quantises the
  pinned bf16 weights to FP8 at load time.
- `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY` for the judges and audits. Their answers are cached in `data/` and
  `audit/`, so a re-run with the caches makes no new calls.
- `HF_HUB_CACHE`, which names the model cache.

## Restoring removed files

| Removed path (`.aii/manifest.yaml`) | Restore with |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` |
| `__pycache__/` (any) | regenerated automatically by Python |
| Qwen3-8B weights (shared cache, never in this folder) | `huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218` |

Everything else (data, results, predictions, audit, inputs) is kept, and none of it is a large binary.
