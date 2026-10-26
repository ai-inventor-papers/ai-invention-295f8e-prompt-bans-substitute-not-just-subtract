# Where a coding ban takes effect: a route test on 12 frozen bench tasks (Qwen3-8B)

A prompt ban ("Do not use a hash map of seen values for this task.") makes Qwen3-8B write a different algorithm.
This artifact asks **which internal route carries that effect** on the 12 frozen bench tasks of exp11, using
exp8's HF engine (bf16, thinking off): common random numbers (CRN), inverse-CDF sampling and KV-cache splicing by
position class. Every arm of a CRN slot uses the same uniforms. Arms differ only in the cache they read:

| arm | cache read by the generated tokens | tests |
|---|---|---|
| a | full ban prompt | endpoint (clean) |
| b | token-length-matched neutral twin (noun A) | endpoint (corrupted) |
| c | twin condition segment + ban task-spec and read-position states | PROMPT ROUTE: sufficiency of the later states |
| d | ban condition segment + twin task-spec and read-position states | DIRECT ROUTE: sufficiency of reading the ban itself |
| K0 | full ban, but the condition span is invisible to every generated token | removal of the direct route |
| V1 | twin + one-shot veto of the default's frozen distinctive n-gram | is "subtract one n-gram" the ban? |
| BAN/TWIN+SIG, +NEU | ban / twin with the default's opening (up to the n-gram) or a neutral `def` line forced | is the ban decided in the opening? |

The outcome is behavioural and mechanism-level: each program is labelled by the frozen labellers (runtime trace
first, AST second, blind judge on disagreement). For a task with default mechanism D, s_X = share of attempts
labelled D. Route fractions: F_prompt = (s_b - s_c)/(s_b - s_a), F_direct = (s_b - s_d)/(s_b - s_a),
interaction I = 1 - F_prompt - F_direct, F_K0 = (s_b - s_K0)/(s_b - s_a).

## Main results

**Gate.** Only **5 of 12 tasks are gated** (avoidance >= 0.5 and >= 20 non-default attempts): T03 (k-th smallest,
0.99), T10 (connected components, 1.00), T05 (two-sum, 0.83), T06 (find duplicate, 0.79), T13 (merge intervals,
0.59). On the other seven the ban mostly fails: R1 0.00, R6 0.02, T11 0.02, R3 0.04, T08 0.31, T14 0.41, T04 0.42.
Template W4 ("X is not allowed here.") is the weakest wording, with pooled avoidance 0.19 against 0.42-0.62 for the
others; it produces 29% of all ban failures.

**Per task (N = 100 CRN slots per arm, 5 templates x 20).** Default share by arm, and route fractions with a
template -> slot bootstrap 95% CI:

| task | s_a | s_b | s_c | s_d | s_K0 | F_prompt | F_direct | I | F_K0 | reading |
|---|--:|--:|--:|--:|--:|---|---|---|---|---|
| T03 | 0.01 | 0.95 | 0.01 | 0.25 | 0.01 | 1.00 [1.00, 1.00] | 0.74 [0.36, 0.99] | -0.74 | 1.00 | redundant: either route alone suffices |
| T10 | 0.00 | 0.99 | 0.00 | 0.20 | 0.00 | 1.00 [1.00, 1.00] | 0.80 [0.40, 1.00] | -0.80 | 1.00 | redundant |
| T05 | 0.17 | 1.00 | 0.66 | 0.20 | 0.67 | 0.41 [0.03, 0.82] | 0.96 [0.80, 1.00] | -0.37 | 0.40 | mostly direct |
| T06 | 0.21 | 1.00 | 0.97 | 0.22 | 0.95 | 0.04 [0.00, 0.13] | 0.99 [0.90, 1.05] | -0.03 | 0.06 | direct only |
| T13 | 0.41 | 1.00 | 0.77 | 0.99 | 0.74 | 0.39 [0.00, 0.73] | 0.02 [0.00, 0.08] | 0.59 | 0.44 | superadditive: both needed |

**Pooled over the 5 gated tasks** (ratio of sums; hierarchical task -> template -> slot bootstrap, 10,000 reps;
low-cluster, so the leave-one-task-out jackknife is the primary interval, per the pre-registered fallback F5):

| quantity | point | jackknife 95% (primary) | percentile 95% | BCa 95% |
|---|--:|---|---|---|
| F_prompt | 0.611 | [0.06, 1.17] | [0.23, 0.93] | [0.22, 0.93] |
| F_direct | 0.744 | [0.38, 1.11] | [0.42, 0.97] | [0.27, 0.94] |
| I | -0.355 | [-0.98, 0.27] | [-0.73, 0.14] | [-0.71, 0.17] |
| F_K0 | 0.621 | [0.08, 1.16] | [0.24, 0.93] | [0.24, 0.93] |

- **C2a ("the prompt route carries >= 2/3 of the ban"): DISCONFIRMED** under all three intervals. Pooled F_direct =
  0.74 >= 1/3, and pooled F_prompt = 0.61 < 2/3 with a lower bound well under 1/2. The bootstrap gives
  P(F_prompt <= 1/2) = 0.28 and P(F_direct >= 1/3) = 0.99.
  - Leave-one-template-out keeps the picture: F_prompt 0.55-0.66, F_direct 0.71-0.84.
  - The Bayesian mixed GLM sensitivity (task and task:template random effects) gives F_prompt 0.74, F_direct 0.89.
- **Mechanism, read per task.** The bench does not share the path tasks' prompt-route story (exp8: T2 F_prompt 0.98).
  - On T05/T06 the ban acts almost entirely through generated tokens reading the condition segment. Arm d reproduces
    the ban, while c and K0 do not.
  - On T03/T10 the information is redundant. The later prompt states alone (c, and K0, which removes direct reading
    and leaves the effect intact) and the direct route alone (d) each suffice.
  - On T13 neither route suffices alone.
  - The direction of the effect is therefore task-dependent. Pooling hides a mixture of mechanisms, which the per-task
    flip tables make explicit. Examples: T06 a-vs-c, 0 vs 76 discordant slots; T03 b-vs-d, 72 vs 2; both exact
    McNemar p < 1e-6.
- **C2c (veto sufficiency predicts the direct route): INCONCLUSIVE.**
  - Under the frozen n-gram rule every task's distinctive n-gram is a zero-collateral identifier or structural token
    (T05 ` if complement`, T06 ` set`, T08 `(`). The one-shot veto therefore rarely changes the mechanism:
    V_t = 0.41 (T03), 0.39 (R6), 0.30 (T10), <= 0.07 elsewhere. The veto fires in 61-100% of rows; the model renames
    or re-tokenises (T05: `if compliment in seen`) or breaks the code (T10: 80/100 invalid).
  - All 12 tasks were classed HIGH_DIRECT (V_t < 0.5, predicting F_direct >= 0.25) in commit #2. 4/5 gated tasks hit
    (T13 misses with F_direct 0.02), so the hit fraction is 0.80.
  - Spearman rho(V_t, F_direct) = -0.34 with one-sided permutation p = 0.30 over 5 points, which fails the p < 0.05
    leg of the rule.
- **C2b sensitivity:** no gated task reaches V_t >= 0.5, so nothing is eligible (reported as not evaluable).
- **Prefill (is the ban decided in the opening?).**
  - Forcing the default's own opening, up to the distinctive n-gram, undoes the ban completely on every gated task:
    P_open = 0.98-1.00. Forcing only a neutral `def solve(...):` line undoes none of it: P_open = -0.12 to 0.01.
  - Once the default's first tokens are on the page the model continues the default, with dead-opening rate 0.00-0.02. The
    ban is enforced at the opening, as for safety refusals (Qi et al.), and not re-read in the body.
  - The pre-registered prior (P_open well below 1 where the default can be re-reached) is not supported on the bench.
  - The depth sweep (extras) below localises this to the first body token.
- **Path screen (T1/T2, never pooled).**
  - Under exp8's frozen twin prompts every veto variant fails to move the default: one-shot V1, persistent VP,
    iterated rounds R2/R3 with the re-emerged programs' new n-grams, and the opening veto of the import line.
    Off-default share is 0.00 on T1 and <= 0.01 on T2. The default re-emerged in 99-100% of attempts after each round.
  - Committed predictions:
    - "T1 one-shot veto does not suffice": hit.
    - "T2 one-shot veto suffices and lands on Bellman-Ford/SPFA": **miss** (V = 0).
  - No round reached 20 non-default attempts, so there is no SUBTRACT forecast.
  - The iteration-2 ban landings recompute exactly from raw rows: T1 DFS 257/257; T2 BF/SPFA 255/260.
  - A ban moves these tasks; a surface veto does not.
- **Continuous companion readout (descriptive):** teacher-forced log-prob of the default's signature prefix under
  each arm. Pooled over gated tasks: F_lp_prompt = 0.40, F_lp_direct = 0.45. The likelihood readout splits the
  effect across both routes, as the behaviour does.
- **Controls.**
  - Placebo splice (twin_A condition + twin_B task-spec vs arm b under noun B): |diff| <= 0.04 on T03/T04/T06, so
    splicing itself is inert.
  - Knockout mechanics K0b (the K0 removal applied to the twin): default share 1.00 vs b 0.95-1.00, so removing an
    innocuous segment changes nothing.
  - Both controls on all gated tasks (extras): placebo |diff| <= 0.04 and K0b 1.00 everywhere.

## Extras beyond the plan (separate arms, never pooled into the numbers above)

- **Independent second CRN draw** (slots k = 20-39, fresh uniforms, arms a/b/c/d on the 5 gated tasks, N = 100 each;
  `results/replication.json`).
  - Pooled F_prompt 0.64 [0.27, 0.94] and F_direct 0.74 [0.43, 0.94] (percentile), so the same rule gives the same
    verdict: DISCONFIRMED.
  - Per-task fractions reproduce within +-0.1. Examples: T06 F_direct 0.99 -> 0.93, T05 0.96 -> 0.93,
    T13 F_prompt 0.39 -> 0.49.
  - Rank agreement between the two draws: Spearman 0.89 (F_prompt) and 0.90 (F_direct). The task-level mechanism
    differences are not sampling noise.
- **Controls on every gated task** (N = 50).
  - Placebo splice: |s_pl - s_b(noun B)| <= 0.04 on all six tasks where it ran.
  - K0b: default share 1.00 on all six tasks.
- **Prefill depth sweep** (Qi et al.'s probe, dropped from the plan for budget). The default's modal program is forced
  up to 25/50/75% of its response tokens, under the ban and under the twin (N = 50 each). P_open per depth:

| task | neutral `def` line | 25% of program | signature prefix (to n-gram) | 50% | 75% |
|---|--:|--:|--:|--:|--:|
| T03 | -0.01 (9 tok) | -0.01 (5 tok: `def solve`) | 0.98 (11 tok: def line + indent + ` nums`) | -0.01 (10 tok: def line + indent) | 1.00 (16 tok) |
| T06 | -0.01 (7 tok) | 1.00 (10 tok: `seen =`) | 1.00 (11 tok: `seen = set`) | 1.00 (20 tok) | 1.00 (29 tok) |
| T05 | 0.01 (9 tok) | 1.00 (13 tok: `seen = {}`) | 1.00 (32 tok) | 1.00 (26 tok) | 1.00 (40 tok) |
| T10 | 0.00 (9 tok) | 1.00 (31 tok, inside `find`) | 1.00 (20 tok: `def find`) | 1.00 (62 tok) | 1.00 (92 tok) |
| T13 | -0.12 (8 tok) | 1.00 (30 tok: `intervals.sort(key`) | 1.00 (58 tok) | 1.00 (59 tok) | 1.00 (88 tok) |

  - The ban holds through the whole `def` line and gives way at the **first content token of the default's body**. On
    T03, forcing the def line and its indentation (10 tokens) leaves the ban fully intact; forcing one more token,
    ` nums`, undoes it.
  - The first-divergence positions say the same from the other side. Under CRN, arms a, c and d leave arm b's tokens
    at the first body token: median token 8-10 on T03, T05, T06 and T10, and 19-21 on T13, whose shared
    `if not intervals` guard comes first. The exception is arm c on T06 (median 33).
  - Where a ban takes effect, behaviourally, is the opening of the body. Which internal route carries it into that
    token differs by task (table above).

## Validation (all before or alongside the runs)

- **Inputs:** every bench file matches exp11's `commitment.json`, with combined sha256 `1b27fa26...` re-derived
  (`results/input_hashes.json`).
- **Labeller re-check:** bench references 50/50 under both labellers. Gold runtime-vs-adjudicated equals gate.json on
  all 12 tasks. exp8 suite: 0.957 (exp8: 0.965) and 22/22 references (`results/labeller_recheck.json`).
- **Prompts:** 12 tasks x 5 templates pass the alignment asserts: equal length, identical ids from 'Task:', every
  difference inside [p0, p1). The T1/T2 ids re-derive exactly to exp8's frozen ids.
- **CPU tests** (`results/tests_cpu.json`):
  - n-gram rule on toy data: argmin, both tie-breaks and co-veto flags.
  - Fresh-uniform redraw matches the renormalised distribution (chi-square p = 0.95); the same-uniform redraw is
    biased (p ~ 0).
  - Simulated arms: F_prompt / F_direct recovered (0.79 / 0.14 vs 0.78 / 0.11). Bootstrap CI coverage 0.995 / 1.00
    over 200 datasets.
- **GPU tests** (`results/engine_validation.json`):
  - U1 CRN determinism: 100% identical ids.
  - U2: splice(ban, ban) == a and splice(twin, twin) == b, 100%.
  - U3: eager attention mass on the condition span is exactly 0 in all 36 layers under K0 (0.54+ without). The
    span-dropped cache equals exp8's masked knockout, with TV distance 1.2e-7 on the first generated token.
  - U9 against exp8 on T2: banned a 0/20, b 20/20, c 3/20, d 19/20, all inside the pass bands; label agreement with
    exp8's same slots 0.95-1.00.
- **Audit:** `audit/rederive.py` re-derives every headline from `data/samples.jsonl` without the analysis code
  (`results/rederive.json`; numbers in "Audit" below).
- **Pre-registration:** `commitments.log` hash-chains the forecasts and decision rules (commit1: before any ban sample)
  and the veto classes (commit2: after the ban-free arms, before the first bench ban sample). Three logged amendments
  to the committed analysis code are in `results/prereg_amendments.json`, each with before/after sha256 and what had
  been seen:
  - A1: screen reference recount from exp12's per-row labels.
  - A2: F5's jackknife-primary rule wired in.
  - A3: C1 rows report no top-1 when a family's distribution is tied, so the uniform LADDER no longer scores
    spurious hits.
  None changes a threshold or a confirmatory statistic.

## Audit (`results/rederive.json`)

`audit/rederive.py` re-derives the following from the raw rows without importing the analysis code: every share, the
gate, the pooled and per-task F values, V_t, the C2c hits and P_open. It finds **0 mismatches** with
`results/analysis.json`. It also checks:

- **U4, one-shot veto:** all 1,099 fired V1 rows equal their arm-b twin up to the firing step and never draw the vetoed
  token there. All 121 unfired rows equal arm b exactly.
- **U5, persistent veto:** 0 of 400 persistent-veto rows contain a masked n-gram.
- **U6, prefill:** all 1,100 prefill rows start with their prefix and continue.
- **Shuffle placebo:** shuffling arm labels within CRN slots collapses the mean b - a gap from 0.83 to -0.001
  (q97.5 0.05). Shuffling V_t across tasks gives a rho null centred at 0.01.
- **Hash chain and ordering:** the hash chain verifies. Commit #1 (18:41:06Z) precedes the first ban row of any task
  (18:50:55Z, T2 engine validation). Commit #2 (18:52:25Z) precedes the first bench ban row (18:52:46Z).

`audit/rederive2.py` (`results/rederive2.json`) re-derives the remaining headline numbers by direct counting. All
match:

- F_K0 and I, and the jackknife intervals;
- rho with an exact permutation p (0.30);
- the McNemar flip tests (p <= 3e-19); a same-arm re-paired placebo gives p = 1.0;
- the depth-curve P_open values;
- the second-draw pooled F and the between-draw rank agreement;
- the screen shares and the 257/257 and 255/260 references;
- template avoidance and the W4 share;
- the U9 counts;
- the log-prob readout, from the raw `token_lp/*.npz` arrays.

Not independently re-derived: the hierarchical-bootstrap percentile and BCa intervals, the mixed GLM, the landing
JS nulls, the first-divergence medians and the C1 log-scores.

GPU time: about 1.8 h on the L4. That is 78 min for the main queue, 26 min for the extras and about 5 min for
smoke/timing probes. Judge spend was USD 0.105 in total.

## Deviations from the plan (full list in `results/deviations.json`)

1. **GPU.** One NVIDIA L4 (23 GB) instead of the A4500 (measured 89 ms/step at B=20, 101 at B=40). Batches are therefore
   B = 40 rows of one shape class instead of B = 10. Shape is constant within a class, so CRN partners meet identical
   kernels (U1, U2 = 1.00).
2. **N for some arms is higher than planned at no extra batch cost:** V1 N=100 instead of 50; c/d on non-gated tasks
   N=100 instead of 50; VP N=100.
3. **K0 drops the condition span from the cache** instead of masking it. This is exactly equivalent for generated
   queries (U3) and keeps stock SDPA in every batch.
4. **A row stops when its first code fence closes.** The labellers read exactly that block. All 13,030 rows ended this
   way; none hit the length cap, and the memory-guard pruning never triggered.
5. **Run order.** Ban-free arms (S4, screen round 1, twin-only controls) ran before the analysis code was appended to
   commit #1. No ban prompt ran before commit #1 closed; the audit checks this ordering.
6. **Controls ran on the first three Stage-A tasks** (T03, T04, T06) before the gate was known. Extras then repeat
   them on every gated task.
7. **Judge.** Transient HTTP 429s from the bench judge were retried, and disputed rows were re-judged; 0 remain
   disputed. Spend was USD 0.053 for the bench judge and 0.052 for the exp8 suite judge, total 0.105 < 0.30.
8. **Bench pilot vs this run.** The bench pilot was FP8/vLLM; here the model is bf16/HF, as planned. Arm-b default
   shares are slightly below the pilot's on T03 (0.95), R6 (0.76) and T14 (0.93).
9. **Concurrent label workers.** Restarting the label worker (to add judge retries and lower the caps) killed its
   wrapper subshell, not the Python process. From 18:50 to 20:16 up to three workers labelled the same rows, so
   `data/samples.jsonl` collected duplicates (24,924 lines for 13,030 uids). It was compacted to the last row per uid,
   the row every reader used throughout. Labels come from the same frozen labellers and code-hash caches; the audit
   still finds 0 mismatches.
10. **Extras beyond the plan** (separate arms, never pooled into the confirmatory numbers):
   - controls on all gated tasks;
   - an independent second CRN draw (k = 20-39);
   - a prefill depth sweep.

## Figures (`figures/`, PDF + PNG + the JSON spec each was rendered from)

| figure | what it shows |
|---|---|
| `fig1_arm_shares` | default share per arm (a, b, c, d, K0) for all 12 tasks, Wilson 95% (bars show the larger side of each interval) |
| `fig2_route_fractions` | pooled F_prompt, F_direct, I, F_K0 over the 5 gated tasks with the primary jackknife and the percentile intervals |
| `fig3_veto_vs_direct` | V_t against F_direct on gated tasks (all committed HIGH_DIRECT, predicting F_direct >= 0.25) |
| `fig4_first_divergence` | ECDF of the first generated token at which arms a, c, d and V1 depart from arm b in the same CRN slot |
| `fig5_prefill_popen` | P_open of the default's signature opening vs a neutral `def` line, gated tasks |
| `fig6_screen_rounds` | path screen: share off the default per veto round (V1, opening veto, persistent, rounds 2-3) |

## Results files

| file | content |
|---|---|
| `results/gate.json` | avoidance, gating per task |
| `results/route.json` | per-task and pooled route fractions, all intervals, LOTO, mixed GLM, C2a verdicts |
| `results/crn_flips.json` | 2x2 flip tables with exact McNemar, identical-output rates, first-divergence positions |
| `results/landing_by_route.json` | where each arm lands (modal survivor, JS vs arm a, resampling null) |
| `results/c2c.json`, `results/c2b_sensitivity.json` | veto-sufficiency predictions scored |
| `results/prefill.json` | P_open, dead-opening rates, landings |
| `results/screen_paths.json` | T1/T2 veto rounds, iteration-2 references, committed predictions |
| `results/lp_readout.json` (+ `lp_readout_raw.json`, `token_lp/`) | continuous companion readout |
| `results/controls.json`, `results/replication.json` | placebo / K0b; second CRN draw; prefill depth curve |
| `results/c1_events.jsonl` | secondary C1 rows (SUBTRACT one-shot, ASSOCIATE, PROXIMITY, LADDER uniform) |
| `results/supplementary.json` | template tables, 'other' audit sample, dataset checks, judge spend, lengths |
| `results/engine_validation.json`, `results/tests_cpu.json`, `results/labeller_recheck.json`, `results/input_hashes.json` | validation |
| `results/rederive2.json` | second independent re-derivation (see Audit) |
| `results/timing.json` (main queue, rebuilt from `logs/gpu_worker.out` after the extras worker overwrote it), `results/timing_extras.json`, `results/deviations.json`, `results/prereg_amendments.json`, `results/rederive.json` | bookkeeping and audit |

The dependency dataset (art_j3Rm_lr2nzR6) enters through the frozen bench, whose tests and nouns came from it. It is
also checked directly: every neutral noun used is in its `concreteness_norms` table, and every bench task's LeetCode
source is listed from `leetcodedataset` (`results/supplementary.json`). All kept artifacts stay on the run's volume at
the relative paths below; no file here reaches 100 MB.

## Layout

| path | what it holds |
|---|---|
| `method.py` | entry point for every stage (`uv run method.py <stage>`; see the docstring) |
| `src/cfg.py` | constants, frozen templates W1-W5, paths, seeds (`stable_seed` is exp8's), utilities |
| `src/s0_inputs.py` | S0: read-only snapshot of all inputs into `inputs/`, bench sha256 check against `commitment.json` |
| `src/s0_recheck.py` | S0.5: labeller re-check on references + gold sets (bench) and on exp8's suite (T1/T2) |
| `src/prompts_s1.py` | S1: ban / twin_A / twin_B prompts with exp7's ' .' padding; alignment assertions |
| `src/forecast_s2.py` | S2: distinctive n-gram rule, prefills, opening-veto variant, ASSOCIATE / PROXIMITY |
| `src/engine.py` | exp8's HF engine (KV splice, knockout attention, teacher-forced scoring, CRN inverse-CDF sampler) + vetoes, span-dropped K0, fence stop |
| `src/gpu.py` | the GPU queue: S3.2, S4, screen, U-tests, commit #2, S6 + route arms, gate, K0, prefills, S8 |
| `src/gpu_tests.py` | GPU tests U1-U3 and the engine validation U9 against exp8 |
| `src/gpu_extras.py` | extras beyond the plan: controls on every gated task, an independent second CRN draw |
| `src/labelq.py` | frozen labellers (bench: exp11 runtime+AST+judge; T1/T2: exp8 suite) and the streaming label worker |
| `src/commit.py` | sha256 hash chain (`commitments.log`) |
| `src/analysis/analysis.py` | S9 analysis (committed in commit #1 before any ban sample; one logged amendment) |
| `src/screen.py` | path-screen iteration rule (re-emerged n-gram) |
| `src/replication.py`, `src/supplementary.py` | second-draw replication; descriptive additions (W4 share, 'other' audit, dataset checks) |
| `src/figures.py`, `src/outputs.py` | figures (aii-data-fig-gen specs) and `method_out.json` |
| `audit/rederive.py` | independent re-derivation of every headline from `data/samples.jsonl`, U4-U6, shuffles, hash chain |
| `tests/test_cpu.py`, `tests/test_analysis_smoke.py`, `tests/gpu_smoke.py`, `tests/gpu_timing2.py` | CPU tests T3-T5, analysis smoke test, GPU timing/memory probes |
| `inputs/` | read-only copies: `bench/` (12 frozen tasks + `common/`), `exp7/`, `exp8/` (engine, suite, frozen prompts, samples), `exp9/`, `exp11/`, `exp12/`, `dataset/` |
| `prompts/prompts.jsonl` | every prompt's ids, p0, p1, P and sha256 |
| `predictions/` | frozen forecast objects + `prereg.md` (commit #1), `c2c.json` + `veto_landings.json` (commit #2), screen rounds |
| `commitments.log` | the hash chain (commit1, commit2) |
| `data/samples_raw.jsonl` | every generated row (token ids, text, veto and batch fields) |
| `data/samples.jsonl` | the same rows with labels in the protocol schema (last row per uid wins) |
| `data/label_mech_cache.jsonl`, `data/path_eval_cache.jsonl` | labeller caches keyed by code hash |
| `labelling/` | bench judge cache (seeded from exp11) and this run's judge spend log |
| `token_lp/*.npz` | per-token log-probs of the signature prefix per arm and template (S8) |
| `results/` | every analysis output (see the results table above) |
| `figures/` | `fig1`-`fig6` as PDF + PNG, with their JSON specs |
| `method_out.json` (+ `full_`/`mini_`/`preview_`) | exp_gen_sol_out output |
| `logs/` | per-stage logs |

## How to run

The exact sequence that produced these results, with runtimes and incidents, is in `reproducibility.md`.


```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python method.py s0        # inputs + bench hash check (needs the upstream folders; already done here)
.venv/bin/python method.py recheck   # labeller re-check
.venv/bin/python method.py s1 && .venv/bin/python method.py s2
.venv/bin/python method.py tests
# GPU: run the label worker and the GPU queue side by side (the queue waits for the labels it needs)
.venv/bin/python method.py label &
BRT_BATCH=40 BRT_PRUNE_AFTER=560 .venv/bin/python method.py gpu      # pauses until `method.py close1` closes commit #1
.venv/bin/python method.py close1    # run once the analysis code is final and before any ban sample
.venv/bin/python src/gpu_extras.py   # optional extras
.venv/bin/python method.py analysis && .venv/bin/python src/replication.py && .venv/bin/python src/supplementary.py
.venv/bin/python method.py figures && .venv/bin/python method.py outputs && .venv/bin/python method.py audit
```

`figures` needs the aii-data-fig-gen generator and `run_final.sh`'s JSON checks need the aii-json skill: point
`AII_SKILLS_DIR` at the folder holding the aii skills (or `AII_FIG_GEN` straight at `chart_gen.py`).

On the same GPU type and library versions, CRN sampling is bit-reproducible at a fixed batch shape (U1 = 1.00). On
other GPUs bf16 kernels differ, so individual samples change; shares and route fractions should agree within their
intervals. Judge answers are cached by code hash, so a re-run reuses them.

## Restoring removed files

`.aii/manifest.yaml` marks three paths for deletion after the round. Each one is rebuilt by the command shown;
`./restore.sh` runs the first one and downloads the model.

| deleted path | kind | how to bring it back |
|---|---|---|
| `.venv/` | regenerable | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r requirements.txt` (74 pins, identical to `pyproject.toml`) |
| `__pycache__/` (top level) | regenerable | recreated by Python on import, or `.venv/bin/python -m compileall method.py` |
| `**/__pycache__/` (in `src/`, `src/analysis/`, `audit/`, `tests/`, `inputs/...`) | regenerable | recreated by Python on import, or `.venv/bin/python -m compileall src audit tests inputs` |

The model is not stored in this folder. Restore it with
`huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218` (bf16, about 16.4 GB;
`restore.sh` does this too).

Everything else is kept on the run's volume at the paths above and is also in the published repository: data, results,
inputs, token log-probs, figures and logs. No file reaches 100 MB.
