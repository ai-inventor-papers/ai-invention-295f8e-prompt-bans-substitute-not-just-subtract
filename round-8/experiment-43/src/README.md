# Predicting how temperature shifts code ideas (iteration 8, claim L)

**Question.** Is sampling temperature a "creativity knob" for which *algorithm* a language model writes, and if it
acts on the algorithm at all, can its effect be predicted *in advance* from a handful of tokens? Iteration 7 found, on
one model (Qwen3-8B), that the algorithm is fixed by a single sampled "decision token" and that a law over that token's
tempered probability predicted the temperature sweep on one unit of three. This artifact turns that into a
pre-registered test across **three model families**, with **held-out units that were never used to build the law**.

**What is predicted.** For each unit (a coding task on one model) the pipeline:

1. finds the decision token(s) *blind*: prefix resampling along stratified base programs, a pre-registered Bayesian
   change-point rule, single-token refinement, and forced-token confirmation (each of the 20 most likely tokens at the
   decision position is forced and its continuations are labelled), with a second decision searched inside any impure
   branch (the plan's composition level);
2. commits, by sha256 hash chain and before any temperature sample, the law's prediction of the attempted-label
   distribution at T 0.3 / 0.7 / 1.0 / 1.3 under top-p 1 and top-k 10, computed only from teacher-forced logits along
   the openings and at the decision token(s) plus the T-1 token conditionals P(A | token):

   P_T(A) = sum over openings c of w_T(O_c) * [sum_t pi_T(t | O_c) G_T(t, A) + residual] + (1 - sum_c w_T(O_c)) q_rest(A),
   where G_T(t, A) = P(A | t), or, when a second decision follows t, the same mixture over the second token after the
   intermediate tokens O2;

3. commits four rivals: **B0** the fit twin's shares at every T (no temperature effect), **B1** the shares tempered as if
   the algorithm were one token (q(A)^(1/T)), **B2** the single-decision law (no second level) and **BH** the same law at
   the highest-entropy position (the entropy-fork rival of the RLVR/forking-token literature);
4. samples the same 100 fresh random streams at every temperature (common random numbers, exact McNemar pairing) and
   scores MAE = mean over temperatures of the total-variation distance between predicted and observed label
   distributions. A unit passes at MAE <= 0.10 with H(algorithm | decision classes) <= 0.3 bits; the claim passes on
   >= 70% of scored units including >= 3 held-out units (>= 4 scored).

Units: Qwen3-8B A3 trapped rain water, B6 valid anagram, B3 minimum spanning tree weight (law-development units);
held-out gemma-3-4b-it T04 substring search and R6 first-and-last position, and Llama-3.1-8B-Instruct T1 grid path
(the two Llama bench units selected from its pilot, T03 and T06, were dropped under the plan's time box; their fit
twins, selection and label re-gate stay in the data). All in bf16, no quantisation, one RTX A4500.

## Results

All numbers below are generated into `results/summary.md` by `src/report8.py` and re-derived with the standard library
by `audit/rederive.py` (0 mismatches). Predictions were hash-committed before every temperature sample
(`commitments.log`, chain verified).

**In plain terms (is temperature the creativity knob?).** Temperature does not add new ideas here. In every unit it
re-weights the 2-3 algorithms the model already knows, and it does so through one or two specific tokens in the
program's opening (a loop keyword, a `try`, a variable name). Where those tokens were found, the committed law
predicted the temperature response of the algorithm mix in advance, on units and a model family it had never seen.

**Answer to the claim.** 5 of 6 scored units pass (MAE <= 0.10 and H <= 0.3 bits), including both held-out Gemma
units, where the law was never developed. The held-out Llama grid unit fails: its decision token exists (` visited`
vs ` queue`, as in Gemma) but sits behind openings that cover only 2% of programs, and at T 1.3 Llama's programs
degenerate. With 3 held-out units scored instead of the required 4 (two Llama bench units were dropped under the
plan's time box), the verdict is **PARTIAL**, not PASS; no disconfirming branch fires.

### Held-out family 1: gemma-3-4b-it (both units pass)

- **Gemma (held-out family 1) - both units pass, and the composition level matters.**
  - **T04 substring search.** The blind locator puts the decision at generated token 31, right after
    `if len(needle) > len(haystack): return -1`: `for` (T-1 probability 0.73) and a blank line (0.17) lead to the naive
    window scan, `try` (0.10) leads to `haystack.index` (built-in). H(algorithm | class) = 0.001 bits.
    Built-in share predicted 0.034 / 0.078 / 0.096 / 0.107 at T 0.3 / 0.7 / 1.0 / 1.3; observed 0.01 / 0.11 / 0.11 / 0.16.
    MAE 0.033 (flat B0 0.043, tempering B1 0.023, single-decision B2 0.033, entropy rival BH 0.036).
    Drop T 1.0 -> 0.3: 10 slots leave the built-in, none join (exact McNemar p = 0.001).
  - **R6 first and last position.** First decision at token 12: `first` (0.95) vs `left`/`def`/`low` (binary search).
    But `first` is impure (9 linear : 1 binary), so the second-decision search runs inside it and finds token 24, after
    ` = -1\n    last = -1\n    `: `for` -> linear scan, `left`/`l`/`low` -> binary search. Composed H = 0.001 bits.
    Binary-search share predicted 0.004 / 0.073 / 0.161 / 0.255; observed 0.00 / 0.08 / 0.13 / 0.24. MAE 0.014, against
    0.051 for the same law without the second level (B2), 0.073 flat, 0.018 tempering, 0.017 entropy rival.
    Drop 13:0 (p = 1.2e-4).

### Held-out family 2: Llama-3.1-8B-Instruct

- **Llama T1 grid path - fails, for a reason outside the law's scope at T 1.3.**
  - Llama's opening classifier could not pass its gate (the frozen labeller calls some path-storing BFS programs
    'iddfs'), so every locator continuation was completed and labelled (3,276 continuations; plan rule: 4 base paths,
    every 4th token beyond k = 32).
  - The locator finds real decision tokens of the same kind as Gemma's: after a 52-token opening, ` visited` (0.45)
    and ` stack` (0.15) lead to DFS, ` queue` (0.25) to BFS. But Llama reaches that position through many different
    openings: the two confirmed openings cover only about 2% of the fit twin, so the committed law is almost the fit
    twin's flat shares (DFS 0.26 / 0.25 / 0.23 / 0.23 predicted). H(A | classes) = 0.63 bits inside the opening
    ('decision spread'), so the unit fails the H criterion as well.
  - Observed (N = 100 per cell): BFS 0.76 / 0.66 / 0.61 and DFS 0.12 / 0.24 / 0.21 at T 0.3 / 0.7 / 1.0. At T 1.3 the
    programs degenerate: 72 of 100 run to the 1,536-token cap, the pass rate falls to 0.04 and the frozen labeller calls
    87 of them 'other'. That cell exceeds the pre-registered 20% 'other' bar, so it was adjudicated by two judge
    families + tiebreak (43 BFS, 15 DFS, 29 other) and the adjudicated column is primary: BFS 0.53, DFS 0.16, other 0.29.
  - MAE 0.142 for the law, and every rival fails as well (flat 0.138, tempering 0.143, single decision 0.142, entropy
    rival 0.134). With the frozen labels the MAEs are 0.28-0.29 for every predictor. The miss is the T 1.3 collapse into
    unusable programs, which no algorithm-level law (and no baseline) predicts.
  - Below T 1.3 the twin's shares hold (cells within about 0.1 of the prediction); the drop of DFS from T 1.0 to 0.3
    (0.21 -> 0.12; McNemar 18:9, p = 0.06) was not predicted (the law's opening carries too little mass).
  - Under top-k 10 the degeneration is largely cut off (law MAE 0.102, flat 0.100), but Llama's top-k shadow cells
    failed their validation (1 of 20 directly sampled T-1.3 programs token-identical after divergence), so the top-k
    cells of Llama are reported but not used for any claim.
  - The Llama bench units were dropped under the plan's time box (see deviations), so only 3 held-out units are scored.

### Law-development family: Qwen3-8B

- **A3 trapped rain water - passes; the blind locator rebuilds iteration 7's structure.** Two 18-token openings (the
  two clusters): ` n` (0.80) leads to prefix/suffix arrays, ` left` (0.20, or 0.62 in the second cluster) mostly to two
  pointers but impure, so a second decision is found at token 19: ` =` -> two pointers, `_max` -> arrays (iteration 7's
  ` left =` vs ` left_max`). Composed H < 0.001 bits. Two-pointer share predicted 0.163 / 0.279 / 0.307 / 0.322;
  observed 0.17 / 0.27 / 0.26 / 0.27. MAE 0.029 (flat 0.055, tempering 0.070, single decision 0.038, entropy rival
  0.037). Iteration 7's A3 miss (MAE 0.105 on 50 streams) does not recur on 100 fresh streams. Drop T 1.0 -> 0.3:
  14:5 on paired slots (p = 0.03; observed 0.09, predicted 0.14).
- **B6 valid anagram - passes, but the flat baseline is better.** The decision found is inside the counting branch
  (token 24): ` =` -> 26-slot count array, `_s` -> mostly hash map, resolved by a second decision at token 26 (`{}`,
  `dict` -> hash map; `[` -> array). The sort-vs-count choice before it enters through the opening's path probability.
  The law predicts an almost flat count-array share (0.188 / 0.178 / 0.181 / 0.183); observed 0.19 / 0.13 / 0.15 /
  0.13. MAE 0.054 (flat 0.030, tempering 0.091, single decision 0.054, entropy rival 0.071). As in iteration 7,
  temperature barely moves B6.
- **B3 minimum spanning tree weight - passes; iteration 7's T-1 lean was a stream artefact.** Decision at token 61
  (` Kr` -> Kruskal, ` Prim` -> Prim), H = 0.004 bits. Prim share predicted 0.087 / 0.198 / 0.231 / 0.235; observed
  0.07 / 0.17 / 0.25 / 0.31 on 100 fresh streams. MAE 0.043 (flat 0.093, tempering 0.058). Drop 18:0 (p = 3.8e-6;
  observed 0.18, predicted 0.14). Fresh-stream T-1 Prim share 25/100 vs predicted 0.231 (binomial p = 0.64), vs
  iteration 7's sweep 20/50 (Fisher p = 0.09) and its twin 19/100 (p = 0.39).
- Per-slot replay with each slot's own uniforms names the algorithm of 0.87-0.99 of on-opening Qwen slots in every
  cell (Gemma 0.94-1.00). Top-k 10 changes almost nothing on Qwen and Gemma (0-5 regenerated programs per cell; the
  shadow construction matched 20/20 directly sampled programs on A3 and on G-T04).

### Verdict

| unit | family | held-out | MAE law L | flat B0 | tempering B1 | single decision B2 | entropy rival BH | H (bits) | pass |
|---|---|---|---|---|---|---|---|---|---|
| A3 | Qwen3-8B | no | **0.029** | 0.055 | 0.070 | 0.038 | 0.037 | <0.001 | yes |
| B6 | Qwen3-8B | no | 0.054 | **0.030** | 0.091 | 0.054 | 0.071 | <0.001 | yes |
| B3 | Qwen3-8B | no | **0.043** | 0.093 | 0.058 | 0.043 | 0.045 | 0.004 | yes |
| T04 | gemma-3-4b-it | yes | 0.033 | 0.043 | **0.023** | 0.033 | 0.036 | 0.001 | yes |
| R6 | gemma-3-4b-it | yes | **0.014** | 0.073 | 0.018 | 0.051 | 0.017 | 0.001 | yes |
| T1 | Llama-3.1-8B-Instruct | yes | 0.142 | 0.138 | 0.143 | 0.142 | **0.134** | 0.63 | no |

- **Claim L: PARTIAL.** 5 of 6 scored units pass (0.83 >= 0.70) and 2 of 3 held-out units pass, but the claim also
  needs >= 4 held-out units scored and >= 3 passing; after the time-box drops of the two Llama bench units only 3 were
  scored, so the held-out criterion is underpowered rather than met. No held-out unit has MAE > 0.2, so the
  disconfirming branch does not fire.
- **Against the rivals.** The law has the lowest MAE on 3 of 6 units and beats the flat baseline on 4/6, tempering on
  5/6, the entropy rival on 5/6 and the single-decision law on 3/6 (it equals it where no second decision exists).
  Holm input (exact one-sided sign test, MAE_L < MAE_B0 over units): p = 0.34. Slot-bootstrap 95% CIs of MAE_L - MAE_B0
  exclude 0 on B3 [-0.050, -0.025], R6 [-0.081, -0.018] and T04 [-0.041, -0.002]; MAE_L - MAE_B2 excludes 0 on R6
  [-0.051, -0.011], where the second decision is needed.
- **Placebos.** Permuting the predictions across temperatures puts the true summed error below the 5th percentile on
  A3, B3 and R6 (not on T04 and B6, whose responses are nearly flat, nor on L-T1). Shuffling P(A | token) across tokens
  raises the error (p <= 0.02 on A3, B6, B3, R6; 0.10 on T04). The temperature-label shuffle rejects the drop test at
  the nominal rate (0.02-0.04).
- **Mechanism vs realisation.** The replay-implied shares (each slot's own uniforms through the committed token
  classes) are within TVD 0.00-0.04 of the observed cells on every passing unit; the remaining error is the law's
  expectation vs the 100 realised streams.

### Base vs instruct ("is the model's answer the mean answer?")

The plan's 'mean answer' question: is the instruct model's algorithm choice simply the base model's average answer?
Qwen3-8B and Qwen3-8B-Base were teacher-forced on identical chat-templated token ids (`results/base_subarm.json`,
figure F5).

| task | decision margin instruct (nats, 5 templates) | base | gain | gain without chat tokens | mean H_base - H_instr at 64 phrasing positions [95% CI] | JS divergence decision / phrasing / entropy-matched / random |
|---|---|---|---|---|---|---|
| T1 grid path (collapsed, BFS) | 4.9-7.4 | 2.9-3.3 | **3.27** | 5.31 | 0.31 [0.29, 0.33] | 0.51 / 0.05 / 0.27 / 0.04 |
| T10 components (collapsed, union-find) | 10.5-18.7 | 2.4-2.7 | **13.41** | 11.05 | 0.28 [0.27, 0.28] | 0.31 / 0.04 / 0.20 / 0.09 |
| T2 shortest path (collapsed, Dijkstra) | 4.9-6.2 | 3.4-3.6 | **2.11** | 2.69 | 0.23 [0.22, 0.24] | 0.44 / 0.04 / 0.29 / 0.05 |
| B3 (mixed, descriptive) | 0.5-1.5 | -0.8 | 1.84 | 1.69 | 0.34 [0.33, 0.35] | 0.34 / 0.05 / 0.34 / 0.02 |
| A3 (mixed, descriptive) | 1.0-2.5 | -0.2-0.1 | 1.53 | 1.91 | 0.21 [0.20, 0.22] | 0.11 / 0.03 / 0.20 / 0.04 |

- **Committed predictions hold on all three collapsed tasks:** post-training widened the decision-token margin by
  >= 2 nats (2.1, 3.3 and 13.4) while the phrasing positions' entropy moved by less than 0.5 nats (0.23-0.31; the base
  model is uniformly a little less certain). The same holds without chat tokens (gains 2.7-11.1), so it is not a
  template-format artefact.
- **The shift concentrates at the decision tokens.** Jensen-Shannon divergence between the two models is 6-10x larger
  at the decision position than at phrasing positions, and 1.5-1.9x larger than at phrasing positions of the same base
  entropy decile on the collapsed tasks (equal on B3, lower on A3); random positions show no excess. At phrasing
  positions the instruct token is the base model's top token at 89-95% of positions (URIAL categories), but at the
  decision position it is mostly the base model's second or third choice.
- **So the instruct model's default is not the base model's mean.** On B3 the base model's own fork distribution,
  pushed through the instruct model's P(A | token), would give Prim 0.68 (the instruct model writes Kruskal 0.78); on
  A3 two pointers 0.37 vs 0.29. Post-training moved and sharpened one token; the repertoire of ideas stayed the same.
  This is adjacent to, and partly occupied by, Cantarero et al. (NeurIPS 2026 workshop; RLVR vs base on math): we add
  the counterfactually located, often low-entropy decision token and the algorithm-level outcome on code.

### Ideas vs phrasings (the 1a-c question) and novelty

- **Temperature is not an idea knob here.** Across 4,800 sweep programs and every temperature, no unit produced an
  algorithm outside its catalogue. The novelty audit read every correct program labelled outside the catalogue
  (10 distinct among 4,703 correct programs, checked against the 18,305-solution corpus built from the dependency
  art_j3Rm_lr2nzR6 plus references; two judge families with 3/3 known-class controls; a manual read): 8 labeller misses
  of catalogue algorithms, 1 catalogue variant, 1 known brute force outside the catalogue, **0 novel** (rule-of-three
  upper bound 0.0006).
- **1a-c (tight temperature with top-k 10 vs looser temperature).** At T 0.3 the sweep is essentially one idea with one
  to four phrasing clusters (identifier-normalised AST 4-gram Jaccard 0.8): R6 100 linear scans in 2 clusters, B3 93
  Kruskal in 4 + 7 Prim in 2, A3 83 arrays in 1 + 17 two pointers in 1 (case 1a). Loosening T does not add ideas; it
  moves mass to the second known idea at the predicted rate and multiplies its phrasings: at T 1.3 B3 has 66 Kruskal in
  22 clusters + 31 Prim in 7, R6 76 linear in 2 + 24 binary search in 8 (case 1c, the 'more phrasings of the same 2-3
  ideas' branch). Correct-only Hill-1 diversity rises accordingly (B3 1.29 -> 2.06, R6 1.00 -> 1.68). Top-k 10 is
  token-identical to top-p 1 on every Qwen and Gemma cell except 6 of B3's 400 programs (regenerated after a divergence).

## How to read these results (scope and limits)

- **A behavioural decision point, not a circuit.** The decision tokens are located by resampling with a pre-registered
  change-point rule; they say where the algorithm becomes fixed in the token stream, not which components compute it.
- **Attempted labels from frozen labellers.** The outcome is the algorithm the program attempts (runtime tracer + AST,
  judges only on disagreements and for 'other'-heavy cells); correct shares are reported beside it. Llama's programs
  often fail the hidden tests, and its label re-gate was weak (see deviations), so the Llama unit speaks to structural
  choice more than to correct idea choice.
- **Scope.** Six scored units in three families (three Qwen law-development units, three held-out units), N = 100
  fresh streams per cell, bf16 on one GPU class. Per-family statements are descriptive. The held-out evidence for the
  law rests on two Gemma units; the Llama unit shows where it breaks (diverse openings, degeneration at T 1.3).
- **Tempering the twin's shares (B1) is a strong rival.** It beats the law on Gemma T04 and comes close on R6 and B3:
  much of the temperature response is 'sharpen or flatten the known mix'. The law's added value is largest where an
  impure first token needs the second decision (R6, A3) and where the default's share is not the one being sharpened
  (B3: B1 0.058 vs L 0.043).
- **What the law assumes.** P(A | token) is measured at T 1 and carried to other temperatures (one-token concentration).
  Error from tempering after the decision stays visible as the replay-vs-observed gap.

## Validity checks

- **Integrity.** The hash chain (`commitments.log`) verifies end to end: COMMIT #0 (protocol and code hashes) before any
  sample; per family COMMIT #1 (decision tokens) and COMMIT #2 (predictions, replay predictions, the scoring code's
  sha256) before any sweep sample of that family; amendments (adjudication rule in scoring, locator nested-opening fix,
  content-addressed continuation ids, not-found second decisions) each committed before the samples they govern, with
  the affected units named. The held-out families' predictions were committed and swept before any Qwen sample.
- **CPU tests** (`results/tests_cpu.json`): U5, U8 (inherited), U9 (two-level tree, exact to 1e-9), U10 (top-k shadow =
  direct top-k on 1,000 synthetic sequences, 733 of which diverge), U11 (replay = analytic opening probability within
  3 SE) all pass; the change-point rule has a 0.00 false-positive rate on 200 null series and 0.865 power on planted
  TV-0.4 jumps; the scoring code applied to iteration 7's committed predictions reproduces its minority MAEs exactly
  (B3 0.083, A3 0.105, B6 0.043); every bench/unit reference program gets its own label (43/43).
- **Prompts.** Gemma prompt ids reproduce exp31's sha256 on all 10 templates; Llama T1 prompt lengths match exp10 on all
  5 paraphrases. Sweep streams are disjoint from every iteration-7 and exp31 key (0 overlaps among 1,300 seeds).
- **Engine.** CRN determinism 10/10 identical (every family); batch 10 vs 20: 8/10 identical (kernel sensitivity, so
  every same-stream comparison uses one fixed batch composition); teacher-forced vs incremental argmax agreement 1.00
  (Gemma; max logit difference 2.0) and 0.997 (Llama; 0.25).
- **Engine check against earlier GPUs.** Gemma fit twins at exp31's keys: per-slot labels agree on 0.98 (T04) and 0.97
  (R6) of slots; 95 and 93 of 100 programs are token-identical. Llama has no CRN precedent: the bf16 T1 twin
  (BFS 60 / DFS 23 / IDDFS 14 / other 3) differs from iteration 2's FP8-vLLM twin (BFS 77 / DFS 20 / other 3;
  Fisher p = 0.015 on the BFS share), so every Llama contrast stays within this engine.
- **Top-k shadow sampling.** Validated on 20 directly sampled top-k-10 programs per family at T 1.3 (Gemma 20/20
  token-identical).
- **Qwen engine check against iteration 7 (RTX 4090 -> RTX A4500, batch 20 instead of 32-50):** per-slot labels agree on
  0.92 (A3, below the 0.95 expectation: kernel sensitivity, reported), 0.95 (B6) and 0.98 (B3) of slots; 72, 90 and 62
  of 100 programs token-identical. All Qwen contrasts stay within this engine.
- **Independent re-derivation** (`audit/rederive.py`, standard library only, from raw rows and the committed predictions):
  the hash chain, every unit's MAE for L/B0/B1/B2/BH, the McNemar counts and the verdict reproduce with 0 mismatches;
  its placebos behave (temperature labels shuffled within slots reject the drop test at about the nominal rate;
  predictions of the wrong unit raise the error).
- **Judges and cost:** OpenRouter USD 0.05 in total (re-gate, adjudication, novelty audit), no budget refusal.

## What was run

Everything runs in one bf16 Hugging Face engine (`src/engine8.py`) with the iteration-6 sampler transform: float64
softmax(logits / T), an optional top-k mask, then the inverse CDF over the full vocabulary in token-id order. Each
program slot owns one PCG64 uniform stream, so a slot keeps its stream across every temperature and sampler (common
random numbers). Fit twins and sweeps use one fixed batch composition per (unit, template) at every temperature.
Prefix-resampling continuations are independent samples, so finished rows are dropped from the cache.

| stage | what | design |
|---|---|---|
| S0 | setup | prompts rebuilt from the source artifacts and checked (Gemma ids sha256 = exp31; Llama prompt lengths = exp10); seed disjointness; CPU tests U5/U8/U9/U10/U11, change-point rule, scoring dry run on iteration-7 data, labeller references; **COMMIT #0** (protocol + code hashes) |
| S1 | per family: load, GPU tests, fit twin | CRN determinism, batch-size sensitivity, teacher-forced vs incremental logits; fit twin N = 100 (20 slots x W1-W5, T 1) at the source keys (Qwen = iteration-7 twin keys, Gemma = exp31 keys) so it doubles as an engine check; Llama bench candidates re-measured in the committed order until two have a second algorithm >= 0.10 (**COMMIT #1a**); Llama label re-gate with two blind judges + tiebreak (**COMMIT #1b**) |
| S3 | blind decision-token locator | token-trie clusters, 6 stratified base paths, 8 continuations per prefix length k in {0, 2, ..., 62} + {64, 68, ..., W_u}, Bayesian single change point (P >= 0.9, TV >= 0.25), 16-continuation single-token refinement; forced-token confirmation (top 20 tokens of the template-averaged T-1 distribution x 10 continuations); second decisions inside impure branches (resampling every token d+1..d+24, forced top-10 at d2); entropy-located rival BH; **COMMIT #1-family** |
| S4 | predictions | teacher-forced fp32 logits per template along every opening, at d and at d2; the law L, B0 (flat), B1 (algorithm-level tempering), B2 (single decision), BH; per-slot replay of every sweep slot; internal-consistency gate; **COMMIT #2-family** (with the scoring code's sha256) |
| S5 | same-stream sweep | per unit 100 fresh streams ('iter8L-sweep', disjoint from every earlier key) x T in {0.3, 0.7, 1.0, 1.3} at top-p 1; top-k 10 cells by exact shadow sampling on the same uniforms (validated on 20 directly sampled slots per family) |
| S6 | base sub-arm | Qwen3-8B and Qwen3-8B-Base teacher-forced on identical chat-templated ids at the decision positions (T1, T10, T2 forks from art_MZAfDPVhM6Ui; B3, A3 from COMMIT #1-qwen) and at 64 phrasing positions of 20 programs per task; URIAL rank categories; JS divergence with entropy-matched and random-position controls; template-free sensitivity |
| S7 | scoring | `src/analysis_L.py` (frozen; hash in COMMIT #2 + one pre-sweep amendment): MAE, McNemar drops, replay accuracy and gaps, H, verdict, placebos, diversity and phrasing clusters |
| S8 | judges | Llama re-gate, adjudication of cells with > 20% 'other', novelty audit of every correct off-catalogue program against the 18k-solution corpus built from the dependency art_j3Rm_lr2nzR6 |

## Layout

| path | content |
|---|---|
| `method.py` | entry point: runs every stage in order (`.venv/bin/python method.py all`) or a comma list |
| `src/cfg8.py` | constants: units, families, keys, thresholds, paths to the prior artifacts (with fallback to `inputs/src_*`) |
| `src/prompts8.py` | prompt ids per (unit, template) -> `prompts/prompts8.jsonl`, `results/prompt_checks.json` |
| `src/engine8.py` | the bf16 engine: loaders (Gemma text-only, Qwen/Llama with CPU embedding when < 18 GiB free), CRN decoder (coupled / free), top-k shadow, teacher forcing |
| `src/oc8.py`, `src/opening_cls.py` | opening classifiers (iteration-7 rules for B3/A3/B6, new keyword rules for the other units) and their gate |
| `src/label8.py`, `src/label7.py` | label worker (frozen labellers of iterations 5-6; persistent `--serve` mode) |
| `src/locate8.py`, `src/forks.py` | locator functions (clusters, base paths, grid, change points, classes, H) |
| `src/predict8.py`, `src/predict.py`, `src/replay.py` | the law (two-level composition), baselines, unit tests U5-U11; iteration-7 law and replay reused unchanged |
| `src/gpu8.py` | per-family GPU driver (tests, fit, select, locate, commit1, predict, commit2, sweep) |
| `src/commit0.py`, `src/commit8.py` | COMMIT #0 and the sha256 hash chain (`commitments.log`, `predictions/*.json`) |
| `src/analysis_L.py` | committed scoring -> `results/analysis_L.json`, `results/verdict.json` |
| `src/base_arm.py` | base sub-arm (GPU teacher forcing for both models; analysis -> `results/base_subarm.json`) |
| `src/novelty8.py` | judges: re-gate, adjudication, novelty audit -> `results/regate.json`, `results/adjudication.json`, `results/novelty_audit.json` |
| `src/tests_cpu.py`, `src/vendor_inputs.py` | CPU tests -> `results/tests_cpu.json`; input copies + `inputs/SHA256SUMS` |
| `src/figures8.py`, `src/report8.py`, `src/outputs8.py` | figures F1-F6, `results/summary.md`, `method_out.json` |
| `audit/rederive.py` | standard-library re-derivation of every headline with placebos -> `results/rederive.json` |
| `protocol8L.json`, `commitments.log`, `predictions/` | the committed protocol, hash chain and commit payloads |
| `data/samples_raw.jsonl`, `data/labels.jsonl` | every program (fit twins, sweeps, top-k cells, top-k validation) with ids, text, slot, cell, seed; labels |
| `data/continuations.jsonl` | every locator / refinement / forced-token / second-decision continuation with its label |
| `data/judge_cache.jsonl`, `data/adjudicated_labels.jsonl` | judge calls (cached) and adjudicated labels |
| `results/` | per-unit `fit_*`, `locate_*`, `predict_*`, `sweep_*` JSON; analysis, verdict, engine checks, GPU tests, timing, deviations, costs, positioning, summary.md |
| `figures/` | F1-F6 (PDF + PNG) |
| `inputs/` | sha256-checked copies of the prior artifacts this pipeline reads (`inputs/SHA256SUMS`) |
| `method_out.json` (+ `full_`, `mini_`, `preview_`) | exp_gen_sol_out output (datasets law_sweep, fit_twins, locator, forced_tokens, base_subarm) |
| `run_chain.sh`, `finalize.sh`, `restore.sh` | the GPU chain as run (Llama -> Qwen -> base sub-arm), the CPU finalisation (judges, scoring, figures, outputs, re-derivation, schema check) and the restore script |
| `results/positioning.json`, `results/novelty_manual.json` | dated literature positioning with quotes and verdicts; the manual read of every correct off-catalogue program |
| `docs/` | the README's source parts (assembled by `src/assemble_readme.py`) |
| `data/continuations_superseded.jsonl` | 984 L-T1 forced/second-decision continuations sampled before amendment 3 (index-tagged ids), kept for transparency and never read by the pipeline |

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python src/download_models.py            # the four model revisions into the HF cache
.venv/bin/python method.py all                     # or a comma list of stages, see method.py
```

The GPU stages need one CUDA GPU with at least 20 GB (this run: RTX A4500). The judges need `OPENROUTER_BASE_URL` and
`OPENROUTER_API_KEY`. Every stage resumes from its result file; the commit stages refuse to overwrite a commit.

## Deviations from the plan

Every deviation is recorded with its time in `results/deviations.json` (severity in brackets).

- **analysis_code_commit** [minor]: analysis_L.py (scoring) did not exist at COMMIT #0; its sha256 is committed in the first family COMMIT #2, before any sweep sample of any family exists. Thresholds, MAE definition and verdict rules are fixed in protocol8L.json at COMMIT #0.
- **gpu** [none]: GPU is an RTX A4500 (20 GB) as planned; Qwen/Llama keep the input embedding on the CPU (exact lookup).
- **bh_rule** [minor]: BH rival rule corrected before COMMIT #2 (no sweep sample existed): d_H is the argmax of the base paths' mean T-1 entropy over every prefix length < 64 that has locator or refinement continuations (the COMMIT #1 version only searched even grid positions per path and kept the shortest opening). BH openings are committed at COMMIT #2.
- **oc_fail_L-T1** [minor]: L-T1: opening classifier failed its gate ({'unit': 'L-T1', 'n_programs': 37, 'decided_prefixes': 1140, 'decided_agreement': 0.8649122807017544, 'full_agreement': 0.8648648648648649, 'coverage_full': 0.8648648648648649, 'first_decision_p90': 184.0, 'gate_pass': False}); continuations are completed and labelled by the frozen labeller.
- **thin_L-T1** [minor]: L-T1: the opening classifier failed its gate, so every continuation is completed and labelled by the frozen labeller; the extrapolated locator cost exceeded 25 GPU-minutes, so (plan rule) the grid is thinned to 4 base paths and every 4th token beyond k = 32, and continuations are capped at 539 new tokens (1.5 x the fit twin's p90 length + 32; capped continuations are labelled as they stand).
- **regate_primary** [major]: Llama style re-gate: L-T03 agreement 0.10 and L-T06 0.71 (< 0.9). The plan makes the adjudicated column primary for such units; adjudicating every continuation that feeds the law was not feasible in the time box, so primary scoring stays on the frozen labeller (one label space for the law's inputs and outcomes) and the judge-adjudicated sweep labels are reported as a sensitivity. Main disagreement: Llama's T03 programs that count frequencies, push every (count, value) pair into a heap and pop k-1 times are 'heapify_pop' to the frozen AST/runtime labeller but 'other' or 'size_k_heap' to the judges.
- **drop_L-T06** [major]: Time box (plan drop order item 2): L-T06 dropped after the Llama locators had to run with completion labelling (opening classifiers failed their gates). L-T03 kept (first in the committed selection order) so that 4 held-out units are scored. Its fit twin, selection and re-gate rows stay in the data.
- **oc_fail_L-T03** [minor]: L-T03: opening classifier failed its gate ({'unit': 'L-T03', 'n_programs': 33, 'decided_prefixes': 537, 'decided_agreement': 0.5977653631284916, 'full_agreement': 0.7272727272727273, 'coverage_full': 0.7272727272727273, 'first_decision_p90': 80.0, 'gate_pass': False}); continuations are completed and labelled by the frozen labeller.
- **thin_L-T03** [minor]: L-T03: the opening classifier failed its gate, so every continuation is completed and labelled by the frozen labeller; the extrapolated locator cost exceeded 25 GPU-minutes, so (plan rule) the grid is thinned to 4 base paths and every 4th token beyond k = 32, and continuations are capped at 411 new tokens (1.5 x the fit twin's p90 length + 32; capped continuations are labelled as they stand).
- **second_paths_completion** [minor]: For units whose opening classifier failed its gate (completion labelling: L-T1, L-T03), each second-decision search used 2 base paths (1 per leading algorithm) instead of 4 (cost); at most 2 searches per unit (largest class mass x opening coverage first).
- **cont_cache** [none]: Locator restarts reuse already-sampled continuations by their deterministic id (same prefix, same seed, same engine), so a restarted locator reproduces the same series; no continuation was resampled with a different stream.
- **amend2_locator** [minor]: Locator nested-opening rule fixed before the Llama/Qwen commits (amendment 2 in the hash chain); Gemma openings are identical under both rules.
- **amend3_cache_ids** [minor]: Content-addressed ids for forced/second-decision continuations (amendment 3); superseded L-T1 rows kept in data/continuations_superseded.jsonl.
- **drop_L-T03** [major]: Plan time box: Llama bench units dropped (L-T03 after L-T06) because COMMIT #2-L with them projected past 3.5 h elapsed; the held-out set is therefore G-T04, G-R6 and L-T1 (3 units scored), so the held-out criterion (>= 4 scored) is reported as underpowered rather than passed.
- **second_cap_L-T1** [minor]: L-T1: 3 classes met the second-decision trigger; only the 2 with the largest T-1 mass x opening coverage were searched (cost cap); the rest keep their empirical Phat.
- **amend4_predict** [minor]: predict8 bug fix (not-found second decisions keep their empirical Phat), amendment 4, before COMMIT #2-llama.
- **topk_val_llama** [major]: Llama top-k shadow validation failed (1/20 token-identical at T 1.3: 100 of 100 programs in that cell diverge from top-p and the regenerated tails differ under a different batch composition). The plan fallback (direct top-k cells at N = 50) did not fit the time box; Llama top-k cells are reported but not used for any claim.
- **max_new** [minor]: Generation caps: Qwen fit twins use iteration 7's caps (A3 640, B6 384, B3 768) so they double as engine checks; sweeps use min(1,024 or 1,536 for the path task, 2 x longest fit program + 8). Only Llama T1 hit its cap (72 programs at T 1.3, degenerate rambling; reported).
- **base_programs** [minor]: Base sub-arm phrasing programs for T1, T10 and T2 are the 20 stored iteration-7 Qwen3-8B twin programs (art_MZAfDPVhM6Ui, same prompts and model) instead of 20 regenerated ones; B3/A3 use this run's fit twins. T2's margin uses iteration 7's 16-token runner-up path (not the 48-token LLR).
- **disputed_bin** [minor]: Frozen-labeller 'disputed' labels (runtime and AST disagree) are counted in the 'other' bin, as in iteration 7; every correct 'disputed' program the novelty audit listed (8, A3 and B3) was read and is a catalogue algorithm.
- **post_run_portability** [none]: After all samples and scoring: src/cfg8.py resolves the dependency art_j3Rm_lr2nzR6 through ART_J3RM_DIR or the sibling folder ../art_j3Rm_lr2nzR6 (portable paths), finalize.sh takes the aii-json skill folder from AII_JSON_SKILL_DIR, and server paths were scrubbed from logs/. No computed quantity changes; the code hashes in COMMIT #0 refer to the earlier versions.

## Restoring removed files

The manifest (`.aii/manifest.yaml`) deletes only regenerable bulk after the round. Everything else (data, results,
commits, figures, inputs) is kept on the run's volume at the paths above and is under 100 MB per file, so it is also
published with the repository.

| removed path | restore with |
|---|---|
| `.venv/` (about 10 GB: torch, transformers and CUDA wheels) | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` |
| `**/__pycache__/` (bytecode caches under `src/` and `inputs/`) | `.venv/bin/python -m compileall -q src inputs` |
| model weights (shared HF cache, never in this folder) | `.venv/bin/python src/download_models.py` (google/gemma-3-4b-it@093f9f38, meta-llama/Llama-3.1-8B-Instruct@0e9e39f2, Qwen/Qwen3-8B@b968826d, Qwen/Qwen3-8B-Base@49e3418f; full hashes in `src/download_models.py`) |

`restore.sh` runs the first two commands and the model download.
