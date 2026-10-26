# Pre-registration (commit #1) — where a coding ban takes effect, 12 frozen bench tasks, Qwen3-8B

Frozen before any ban prompt of any task is sampled. Files hash-chained with this one in `commitments.log` (commit1):
`ngrams.json` (distinctive n-gram per task, frozen rule), `prefills.json` (signature / neutral prefills, path opening-veto
variant, T2 heapq prefill), `associate_proximity.json` (ASSOCIATE / PROXIMITY nominations), `seeds.json`; the analysis
code (`src/analysis/*.py`) is appended to the same commit before the first ban sample (`work/commit1_closed`).

## Arms (per bench task; CRN slot = (task, template W1..W5, k))
a full ban; b neutral twin (noun A); c PROMPT ROUTE = twin cache [0, p1) + ban cache [p1, P) with the ban's R logits;
d DIRECT ROUTE = ban cache [0, p1) + twin cache [p1, P) with the twin's R logits; K0 = ban cache whose condition span
[p0, p1) is invisible to every generated token (all layers); V1 = one-shot veto of the default's distinctive n-gram under
the twin (same uniforms as b; masked draw redrawn from the renormalised distribution with an independent uniform).
Prefills: BAN+SIG / TWIN+SIG (default's opening up to the n-gram), BAN+NEU / TWIN+NEU (`def solve(...):`).

## Readouts and decision rules
- s_X = #(label == D_t) / #attempted (attempted excludes invalid / no-code / judge-disputed).
- GATE: avoidance_t = 1 - s_a >= 0.5 AND #non-default attempts >= 20.
- F_prompt = (s_b - s_c)/(s_b - s_a); F_direct = (s_b - s_d)/(s_b - s_a); I = 1 - F_prompt - F_direct;
  F_K0 = (s_b - s_K0)/(s_b - s_a). POOLED = ratio of sums over gated tasks.
- C2a: SUPPORTED if pooled F_prompt >= 2/3 AND the 95% CI lower bound > 1/2 (hierarchical bootstrap task -> template ->
  CRN slot, 10,000 reps, percentile primary; BCa and leave-one-task-out jackknife reported beside it).
  DISCONFIRMED if pooled F_direct >= 1/3. Both or neither -> MIXED. Both conditions are checked under all three
  intervals. Pre-stated power note: with ~10 gated tasks and between-task SD ~0.2 the pooled SE is ~0.07, enough to
  separate 2/3 from 1/2 only if the mean sits near 0.75 or above.
- C2c (veto sufficiency predicts the direct route; this artifact's operationalisation, committed here):
  class per task from commit #2: LOW_DIRECT if V_t >= 0.8 (predicts F_direct <= 0.15), HIGH_DIRECT if V_t < 0.5
  (predicts F_direct >= 0.25), NONE otherwise, UNDEFINED if no n-gram or the veto fired in < 50% of V1 rows.
  A hit = the point F_direct on the predicted side. Decision: SUPPORTED if hit fraction >= 2/3 AND Spearman
  rho(V_t, F_direct,t) < 0 with one-sided permutation p < 0.05 (100,000 permutations) over gated tasks;
  DISCONFIRMED if rho >= 0 or hit fraction < 1/2; otherwise INCONCLUSIVE. Non-gated tasks are descriptive only.
- C2b sensitivity: on gated tasks with V_t >= 0.5, the veto lands like the ban if the modal survivor of V1 (co-vetoed
  modes removed) equals arm a's AND JS(V1, a) < the q95 of a matched-size resampling null of arm a (template ->
  program, 2,000 reps, 0.5 pseudocount). Holds if true on >= 2/3 of eligible tasks.
- PREFILL: P_open = (s_ban+sig - s_a)/(s_twin+sig - s_a); near 1: the opening is the decision; near 0: the ban is
  also read in the body. Same for the neutral prefill.
- C1 rows (secondary): smoothing 5% uniform over survivors and a 2% 'other' floor; SUBTRACT = one-shot veto landing
  (flag oneshot_not_iterated); LADDER undefined (scored uniform, flagged). No decision here.

## Predictions (path SCREEN, T1/T2 under exp8's frozen twin prompts; never pooled with the bench)
- T2: the one-shot veto suffices (V >= 0.8) and lands on bellman_ford_spfa (bf_spfa).
- T1: the one-shot veto does not suffice (V < 0.5).
- Prior for the prefill (iteration 1: the T1 ban survived a cut after the deque import): on tasks whose default can be
  re-reached after its opening, P_open is well below 1.

## Drop order (binding)
Q9 (placebo / K0b / heapq extras), then Q8 (non-gated K0), Q7 (twin prefill references), Q6 (screen round 3),
Q5 (non-gated route arms). Never dropped: b, V1, a, Q1 (c, d on gated tasks), Q2 (K0 gated), Q3 (screen), Q4 (ban prefills).

## Known deviations at commit time (all logged in results/deviations.json)
- GPU is an NVIDIA L4 (23 GB, ~1/3 of the 4090's bandwidth), not the planned A4500: batches are B = 40 rows
  (constant shape within each prompt-length class) instead of B = 10; consequently V1 runs at N = 100 (k 0-19) and
  K0 at N = 100. Rows past step 560 of a batch are pruned for memory (logged per batch; affects only very long rows).
- K0 is implemented by dropping the condition span from the cache (exactly equivalent attention for every generated
  query; checked against exp8's masked knockout in U3) so that all batches run stock SDPA.
- Generation of a row stops once its first fenced code block is closed (the labellers extract exactly that block).
- Ban-free arms (S4 b/V1, path screen round 1, twin-only controls) are sampled before the analysis code is appended to
  commit #1; no ban prompt is sampled before it.
