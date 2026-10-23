# Temperature at one deciding token (iteration 8, claims K1 and HR)

bf16 **Qwen3-8B** (revision `b968826d…`, thinking off) and bf16 **Gemma-3-4b-it** write one of a few known
algorithms for each coding task. Iteration 7 showed where the choice is made: at one or two generated tokens, for
example `def find` vs `def dfs` for connected components, or `# Kr(uskal)` vs `# Prim` for minimum spanning trees.
It also showed that global temperature cannot reach an alternative that sits far behind.

This artifact asks two questions.

- **K1.** Apply temperature ONLY at that decision token (T = d over its 20 most probable candidates, T = 1 everywhere
  else), with the dose d read off the token's own teacher-forced logits and a token map, and committed before any
  sample. Does this give the model's alternative algorithms in the predicted shares, at no correctness cost? How does
  it compare with the standard knobs?
  - Global temperature 1.3 / 1.6 / 2.0 with top-p 0.95.
  - min-p 0.1 at T 3.0.
  - EDT-style (entropy-triggered) and AdapT-style (code-block-start) temperature.
  - The same dose at the highest-entropy position or at a random position (placebos).
  - Class-uniform forcing of the decision token.
- **HR.** Is any correct idea reachable by forcing the decision token's top-64 branches but by no sampling knob?

Every prediction was hash-committed before the samples it predicts (`commitments.log`; the chain verifies):

- COMMIT #0: the protocol;
- COMMIT #1: the dose table and every per-arm prediction;
- COMMIT #1b: the locator verdict;
- COMMIT #2: the HR predictions and the audit protocol;
- COMMIT #3: one amendment (see below).

## Results

**In plain terms (is temperature the creativity knob?).** Temperature concentrated on the token where the model
commits to an algorithm is a precise, predictable dial between algorithms the model already has. It does not create
new ones.

- **It is predictable.** The committed composition of the token's logits and a token map named the algorithm mix of
  every dosed cell to within 0.01-0.05 (mean absolute error over classes, 5 units). A per-slot replay of each
  sample's own random number at the decision named it to within 0.006-0.03.
- **Where the alternative is already in play, the dial sets the mix.**
  - On the anagram task (B6), correct-program diversity rises from Hill-1 1.78 to 2.78 at a 2-point pass cost. Global
    temperature and EDT stay at or below 1.89 (min-p and AdapT were not run on B6), and the paired bootstrap beats
    each comparator family run there (best-comparator lower bound +0.19, p = 0.008).
  - On minimum spanning trees (B3) and Gemma's grid task (G), the dial also hits its predicted shares. The twin is
    already diverse there, and a well-tuned global sampler does about as well (min-p at T 3 on B3; global T 1.3 on
    G).
- **Where the model has collapsed onto one algorithm (connected components, T10), the dial reaches what global
  temperature cannot, but only a little.**
  - DFS rises to 6% at d1 and 18% at d2. Global T 1.3/1.6 gives 0% and T 2.0 gives 4%; exact McNemar on
    correct off-default flips is 7:1 vs global T 2.0, p = 0.035.
  - The alternative holds little mass among the decision token's 20 candidates, and seven of those candidates are
    format-breaking tokens (`_parent`, `父`, ...). So d2 costs 14 points of pass rate.
  - Removing the candidates that the token map flags as breaking (an amendment committed before its samples) brings
    the cost to 2 points but keeps DFS at 12-18%. Correct diversity therefore stays at Hill-1 1.54 or below, short of
    the 1.8 target.
- **Forcing the decision token class-uniformly** is the most diverse correct setting when every class has a working
  token: B6 reaches 4 ideas (Hill-1 3.50) with 50/50 passing. It fails when the model's own implementation of the
  alternative is buggy: forcing `def bfs` on T10 gives 24 BFS programs, of which 1 passes.
- **No new algorithm anywhere.** Forcing every one of the decision token's top-64 branches (HR) adds one KNOWN idea on
  three units: BFS on T10, array-scan Prim on B3, and an alphabet-scan counter on B6. Each is about 2 x 10^6 to 5 x 10^7
  T = 1 samples away and out of the dial's reach. Of 5,543 correct programs from all stages, none is a novel algorithm.

**Bottom line.**

| committed test | result | verdict |
|---|---|---|
| (a) composed prediction: MAE <= 0.10 on >= 80% of located units | T10 0.017, B3 0.017, A3 0.039, B6 0.047, G 0.010 (per-slot replay 0.013 / 0.009 / 0.008 / 0.031 / 0.006); noise ceiling 1.00 | **pass** (5/5) |
| (b) collapsed unit (T10): best of d1/d2 reaches correct Hill-1 >= 1.8 at pass cost <= 5 points, every comparator <= 1.15, paired-bootstrap lower bound > 0 vs each | d1: 1.24 at cost 0.02; d2: 1.60 at cost 0.14; best comparator 1.17 (global T 2.0, EDT); best fork - best comparator +0.06 [97.5% LB -0.24], p = 0.30 | **fail** |
| (b) mixed units: d1 within 0.10 of its target; Hill-1 >= 1.8 on >= 4 of the located units | d1: B3 0.44 vs 0.38, A3 0.26 vs 0.35, B6 0.40 vs 0.50, G 0.54 vs 0.50; Hill-1 B3 1.98, A3 1.86, B6 2.78, G 1.97 (T10 1.60) | **pass** (4/4, 4 units) |
| (c) the twin's decision-token entropy is below q90 in >= 90% of samples (T10; G) | 0/50 on T10, 0/44 on G (0% on every unit) | **fail** (the opposite holds) |
| (d) a 16-token window at the boundary units moves <= 0.10 | window pass rate 0.20 / 0.42 / 0.24 (T1 / T2 / T03) | **untestable by breakage** |
| (e) reversion <= 10% in A9/A10, pooled | 4/102 = 0.04 | **pass** |
| (f) Gemma: A10 pass cost within 0.10 of the committed sum_t pi_T(t) Pfail(t); class-uniform forcing never draws ` queue` and costs <= A10 | 0.14 vs 0.156; 0 slots; -0.04 <= 0.14 | **pass** |
| disconfirming branches | pass cost > 10 points: T10 at d2 (0.14) | **fires** |
| primary p (IUT over validated collapsed units) | 0.30 (T10 is the only one; T1 failed validation) | not significant |
| secondary: exact McNemar on correct off-default flips, fork d2 vs global T 2.0 (T10) | 7:1, one-sided p = 0.035 | significant unadjusted |
| HR: ideas(HR) - ideas(sampling knobs) >= 1 on >= 3 units, all known, 0 novel | 3 units (T10, B3, B6); every extra idea is a catalogue algorithm; 0 novel | **as predicted** |
| **claim K1** | the primary (collapsed-unit) test fails and the pass-cost branch fires; the composition law, the mixed-unit predictions, reversion and the Gemma breakage prediction hold | **NOT SUPPORTED as committed** |

The tables below give every arm. Cells are N = 50 CRN slots: the same 5 prompt templates x 10 random streams in every
arm, so flips are paired per slot. "Correct Hill-1" is the exponentiated expected Shannon entropy of the algorithm
labels of correct programs in a random 25-subset (exact hypergeometric expectation; 1 = one idea). Pass cost is the
twin's pass rate minus the arm's, with a Newcombe 95% interval. `results/summary.md` has the full tables, including
committed vs replayed vs observed shares.

### T10, connected components (collapsed: the twin writes union-find 50/50)

The decision is at generated token 10, right after `def solve(n, edges):\n   `: ` parent` (0.94) and ` def` (0.06)
lead to union-find; ` def` is followed by ` find` 97% of the time, with ` dfs` (0.03) and ` bfs` (1e-5) behind it.
The 20 most probable index-10 tokens include five DFS-committal ones (` visited`, ` graph`, ` adj`, ` visit`,
` adjacency`, 1e-5 to 1e-11) and seven format-breaking ones (`'_parent'`, `'-parent'`, `'.parent'`, `'(parent'`,
`'parent'`, `'def'`, `'父'`) whose 10 continuations each fail 10/10. So the composed prediction (COMMIT #1) said the
alternative is reachable only up to about 16% attempted DFS (at T about 10), and only by paying for broken programs.

| T10 arm (N = 50, same streams) | union-find | DFS | BFS | invalid | pass | correct Hill-1 | pass cost [95% CI] |
|---|---|---|---|---|---|---|---|
| twin T = 1 | 1.00 | 0 | 0 | 0 | 1.00 | 1.00 | - |
| global T 1.3 / 1.6, top-p 0.95 | 1.00 / 1.00 | 0 / 0 | 0 | 0 | 1.00 | 1.00 | 0.00 |
| global T 2.0, top-p 0.95 | 0.94 | 0.04 | 0 | 0.02 | 0.98 | 1.17 | 0.02 [-0.05, 0.10] |
| min-p 0.1, T 3.0 | 0.98 | 0.02 | 0 | 0 | 1.00 | 1.09 | 0.00 |
| EDT-style (T 2 where H1 > q90) | 0.94 | 0.04 | 0 | 0.02 | 0.98 | 1.17 | 0.02 |
| AdapT-style (T 2 at block starts) | 1.00 | 0 | 0 | 0 | 1.00 | 1.00 | 0.00 |
| entropy-max position, T = d2 | 1.00 | 0 | 0 | 0 | 0.96 | 1.00 | 0.04 |
| random position, T = d2 (width 2) | 0.86 | 0 | 0 | 0.14 | 0.80 | 1.00 | 0.20 [0.09, 0.33] |
| **fork dose d1 = 3.5** (pred. DFS 0.07, cost 0.03) | 0.94 | **0.06** | 0 | 0 | 0.98 | 1.24 | 0.02 [-0.05, 0.10] |
| **fork dose d2 = 7.0** (pred. DFS 0.13, invalid 0.14, cost 0.17) | 0.70 | **0.18** | 0 | 0.12 | 0.86 | 1.60 | 0.14 [0.04, 0.26] |
| class-uniform forcing (` parent` / ` visited` / ` def bfs`) | 0.38 | 0.14 | 0.48 | 0 | 0.52 | 1.99 | 0.48 [0.33, 0.61] |

### B3, minimum spanning tree (mixed: the twin writes Kruskal 0.62 / Prim 0.38)

The decision is the word after `    #` once the adjacency list is built (two opening clusters, c0 and c1): ` Kr`(uskal)
or ` Prim`. The committed doses were d1 = 2.25 (target: the midpoint between the twin's predicted Prim share and the
attainable maximum, 0.38) and d2 = 6.0 (0.95 x the maximum, 0.46).

| B3 arm | Kruskal | Prim | invalid | pass | correct Hill-1 | pass cost |
|---|---|---|---|---|---|---|
| twin T = 1 | 0.62 | 0.38 | 0 | 1.00 | 1.92 | - |
| global T 1.3 / 1.6 / 2.0, top-p 0.95 | 0.64 / 0.62 / 0.68 | 0.36 / 0.38 / 0.32 | 0 | 1.00 / 0.96 / 0.94 | 1.90 / 1.92 / 1.82 | 0.00 / 0.04 / 0.06 |
| min-p 0.1, T 3.0 | 0.54 | 0.46 | 0 | 1.00 | 1.97 | 0.00 |
| EDT-style | 0.60 | 0.38 | 0.02 | 0.88 | 1.91 | 0.12 |
| AdapT-style | 0.72 | 0.28 | 0 | 1.00 | 1.79 | 0.00 |
| entropy-max position, T = d2 (the decision on 32 of 39 reaching slots) | 0.50 | 0.46 | 0.04 | 0.90 | 1.98 | 0.10 |
| random position, T = d2 | 0.62 | 0.36 | 0.02 | 0.98 | 1.91 | 0.02 |
| **fork dose d1 = 2.25** (pred. Prim 0.38, replay 0.44) | 0.56 | **0.44** | 0 | 1.00 | 1.97 | 0.00 |
| **fork dose d2 = 6.0** (pred. Prim 0.46, replay 0.51) | 0.54 | **0.46** | 0 | 0.96 | 1.98 | 0.04 |
| class-uniform forcing (` Kr` / ` Prim`) | 0.56 | 0.44 | 0 | 1.00 | 1.97 | 0.00 |

### G, grid path on Gemma-3-4b-it (mixed: the twin writes DFS 32 / BFS 18; 5 BFS programs open with ` queue` and fail)

The decision is the token after the shared 32-token opening c*: ` visited` -> DFS; a blank line, `if`, ` queue`, ` q`
-> BFS, where ` queue` programs never pass (iteration 7: 0/125). The committed doses were d1 = 1.75 (BFS 0.48) and
d2 = 3.0 (BFS 0.58, pass cost 0.156 = sum_t pi_T(t) Pfail(t) minus the twin's, of which the ` queue` term is 0.139).

| G arm | BFS (correct) | DFS (correct) | pass | correct Hill-1 | pass cost | ` queue` drawn |
|---|---|---|---|---|---|---|
| twin T = 1 | 18 (8) | 32 (32) | 0.80 | 1.64 | - | 5 |
| global T 1.3, top-p 0.95 | 24 (16) | 26 (24) | 0.80 | 1.94 | 0.00 | 2 |
| global T 2.0, top-p 0.95 | 36 (25) | 14 (11) | 0.72 | 1.84 | 0.08 | 3 |
| EDT-style | 35 (22) | 14 (9) | 0.62 | 1.82 | 0.18 | 3 |
| entropy-max position, T = d2 (= the decision on all 44 slots that reach it) | 29 (19) | 21 (14) | 0.66 | 1.97 | 0.14 | 4 |
| random position, T = d2 | 18 (12) | 32 (31) | 0.86 | 1.79 | -0.06 | 3 |
| **fork dose d1 = 1.75** | 27 (15) | 23 (20) | 0.70 | 1.97 | 0.10 | 7 |
| **fork dose d2 = 3.0** | 29 (19) | 21 (14) | 0.66 | 1.97 | 0.14 | 4 |
| class-uniform forcing (`\n` for BFS, ` visited` for DFS) | 26 (21) | 24 (21) | 0.84 | 1.98 | -0.04 | 0 |

### B6, valid anagram (mixed: the twin writes sort-and-compare 40 / fixed 26-slot array 8 / hash map 2)

The decision is the first statement after `if len(s) != len(t): return False`: ` return` -> sorting, ` count` ->
counting, with array vs hash map settled a few tokens later; its top-20 holds several counting tokens. Committed
doses: d1 = 4.0 (minority 0.50), d2 = 13.0 (0.68).

| B6 arm | sort | fixed array | hash map | 4th idea | invalid | pass | correct Hill-1 | pass cost |
|---|---|---|---|---|---|---|---|---|
| twin T = 1 | 40 | 8 | 2 | 0 | 0 | 1.00 | 1.78 | - |
| global T 1.3 / 1.6 / 2.0, top-p 0.95 | 40 / 39 / 38 | 7 / 9 / 10 | 3 / 2 / 2 | 0 | 0 | 1.00 | 1.82 / 1.83 / 1.89 | 0.00 |
| EDT-style | 38 | 10 | 2 | 0 | 0 | 1.00 | 1.89 | 0.00 |
| entropy-max position, T = d2 (the decision on 21 of 39 reaching slots) | 19 | 17 | 11 | 0 | 3 | 0.94 | 2.87 | 0.06 |
| random position, T = d2 | 35 | 9 | 3 | 0 | 3 | 0.92 | 1.95 | 0.08 |
| **fork dose d1 = 4.0** | 30 | 17 | 3 | 0 | 0 | 1.00 | **2.27** | 0.00 |
| **fork dose d2 = 13.0** | 21 | 19 | 9 | 0 | 1 | 0.98 | **2.78** | 0.02 |
| class-uniform forcing (` return` / ` counts` / ` from` / ` for`) | 21 | 9 | 6 | 14 (`alphabet_count_scan`) | 0 | 1.00 | 3.50 | 0.00 |

### A3, trapped rain water (mixed: the twin writes prefix/suffix arrays 38 / two pointers 12)

The decision is the first token after `if not height: return 0` (c0: ` n` -> arrays, ` left` -> two pointers; c1:
` =` vs `_max`). COMMIT #1 already said the dial has nothing to add here. The attainable two-pointer share among the
top-20 candidates was 0.36 against 0.34 predicted at T = 1, so the rules gave d1 = 1.25 and d2 = 1.5.

Observed:

- **Fork doses:** two pointers 0.24 at both doses (twin 0.24), no pass cost. Correct Hill-1 1.86 (twin 1.72).
- **Global samplers:** global T 2.0 and EDT give 0.28 (Hill-1 1.93) and are the best comparators (bootstrap
  p = 0.96 for fork > best comparator).
- **Class-uniform forcing** gives 0.42 (Hill-1 1.95, no cost).
- **Prediction error:** the composed prediction overstated the twin-level share (0.34 predicted, 0.24 observed;
  MAE 0.039), while the per-slot replay was exact to 0.008.

### Boundary units (T1, T2, T03): a 16-token window at T10's d2

T1 (Qwen grid path) failed its validation: no index-3 token gives >= 5/10 off-default programs, so it joined the
boundary set (pre-registered). On each boundary unit the window applied T = 7 over the top-20 at each of the first 16
body tokens.

| unit | twin | window (16 tokens, T = 7) | pass twin -> window |
|---|---|---|---|
| T1 grid path | BFS 0.98 | BFS 0.94, other 0.04 | 0.88 -> 0.20 |
| T2 shortest path | Dijkstra 0.98 | Dijkstra 0.98 | 1.00 -> 0.42 |
| T03 k-th smallest | full sort 1.00 | full sort 0.30, quickselect 0.14, heaps 0.08, counting sort 0.06, invalid 0.36 | 1.00 -> 0.24 |

All three windows fall below the committed 0.5 pass-rate floor, so (d) is "untestable by breakage". Spreading the
same dose over 16 tokens breaks most programs. On T03 the surviving programs scatter across the known catalogue,
which is the window acting on the program's form, not a located choice.

### The amendment: the same dose without the candidates that break programs (COMMIT #3)

The token map already says which candidates break programs: `_parent`, `-parent` and `父` at T10's decision fail
10/10, and G's ` queue` fails every time. After the primary T10/B3/G cells were seen, one amendment was committed
(COMMIT #3, 03:29:58 UTC, before any of its samples). It applies the same fork dose, but removes from the top-20 the
tokens whose committed Stage 2 continuations fail >= 50% of the time:

- T10: 8 index-10 tokens and 4 index-11 tokens;
- G: 13 tokens, including ` queue`.

Its doses follow the committed rules applied to the filtered composition. It never replaces A9/A10.

| amendment arm | shares (predicted -> observed) | pass | pass cost [95% CI] | correct Hill-1 | vs best comparator family |
|---|---|---|---|---|---|
| T10 filtered d1 = 5 | DFS 0.12 -> 0.18 | 0.98 | 0.02 [-0.05, 0.10] | 1.54 | +0.38, LB +0.01, p = 0.022 (global T); p <= 0.022 vs every family |
| T10 filtered d2 = 10 | DFS 0.17 -> 0.12 | 0.98 | 0.02 [-0.05, 0.10] | 1.37 | (as above, best setting chosen inside each replicate) |
| G filtered d1 = 2.25 | BFS 0.47 -> 0.54 | 0.84 | -0.04 [-0.14, 0.05] | 1.98 | +0.08 vs global T (p = 0.23); p = 0.016-0.023 vs min-p, EDT, AdapT |
| G filtered d2 = 3.0 | BFS 0.50 -> 0.56 | 0.82 | -0.02 [-0.12, 0.08] | 1.98 | |

No banned token was ever drawn (0/100 slots on T10). MAE vs the COMMIT #3 predictions: 0.023 / 0.024 (T10) and
0.012 / 0.009 (G). On T10 the filter removes the breakage but not the ceiling. The alternative simply does not hold
more than about 19% of the mass among the decision token's 20 candidates, so correct diversity stays below the 1.8
target at any dose.

### Where the decision token sits in the entropy profile (prediction (c) fails)

The plan predicted that the decision token would usually NOT stand out by entropy (twin decision-token entropy below
the 90th percentile q90 of the twin's per-token entropies in >= 90% of samples), so that entropy-based samplers would
miss it. It is the opposite: code tokens are almost deterministic (q90 is 0.0003-0.05 nats), and the decision token's
T = 1 entropy is far above q90 in every sample of every unit (median 0.13 nats on T10, 0.53-0.81 on the mixed units;
0/50, 0/39, 0/37, 0/39, 0/44 below q90). The decision token is also the single highest-entropy position of tokens
1-64 on 44/44 reaching G slots, 32/39 on B3 and 21/39 on B6, but on 2/50 T10 slots and 0/37 A3 slots. So an
entropy-max rule at the matched dose finds the fork on the mixed units (on G it reproduces the fork-dosed arm exactly)
and misses it on the collapsed one. The threshold EDT rule fires on about 10% of all tokens, so it spends most of its
temperature elsewhere (T10: 4% DFS; B3: no gain, 12-point pass cost).

### Blind locator (secondary; committed as COMMIT #1b before any Qwen Stage 3 row)

Prefix resampling at T = 1 (6 twin base paths per unit, prefixes 2, 4, ..., 64, 8 continuations each, 3,072
continuations, 16 GPU-minutes on the L4) with the exp35 Bayesian change-point rule and a 1,000-shuffle permutation null:

- **B3**: the three paths with a detectable change all locate generated index 61, the token right after the 61-token
  opening (` Kr` / ` Prim`), exactly; the other three paths show no change point. 3 of 6 is one short of the
  pre-registered 4 of 6: as in iteration 7, a default (Kruskal) path starts near 0.65 own-class share, so the 0.4
  share-jump rule cannot fire on it.
- **T10**: no change point on any of the 6 paths. The twin writes union-find 50/50 and T = 1 resampling never leaves
  it, so a T = 1 locator has no outcome variance to work with on a collapsed task. The fork at index 10/11 was found in
  iteration 7 only under pushed or banned prompts. **On collapsed tasks the knob therefore needs offline knowledge that
  a T = 1 locator cannot supply.**
- The opening classifier that stops the continuations agrees with the full labels on 0.989 (T10) and 0.985 (B3) of
  completed programs.

### HR: the hidden repertoire behind the decision token (committed as COMMIT #2)

At every decision node the 64 most probable tokens were forced and continued 5 times at T = 1 (ranks inside the
Stage 2 map reuse its first 5 continuations): T10 n10 + n11, B3 c0 + c1, G c*, and the map nodes of A3, B6 and T1.
An idea counts when at least one forced continuation is a correct program of it.

| unit | ideas reached by HR (correct programs) | ideas reached by any sampling knob (A0-A10) | HR-only idea | its T = 1 reachability | best fork-dose mass |
|---|---|---|---|---|---|
| T10 | union_find 294, dfs 153, bfs 2 | dfs, union_find | bfs | 5.4e-07 (about 2e+06 samples) | 0.005 |
| B3 | kruskal 290, prim_heap 285, prim_array 2 | kruskal, prim_heap | prim_array | 2.0e-08 (about 5e+07 samples) | 0.000 |
| B6 | fixed_count_array 163, hash_count 99, sort_compare 20, alphabet_count_scan 5 | fixed_count_array, hash_count, sort_compare | alphabet_count_scan | 2.9e-08 (about 4e+07 samples) | 0.010 |
| A3 | prefix_suffix_max 288, two_pointers 143, peak_split 4 | peak_split, prefix_suffix_max, two_pointers | none | - | - |
| G | dfs 77, bfs 57 | bfs, dfs | none | - | - |
| T1 | bfs 29 | bfs, dfs | none | - | - |

Prediction (COMMIT #2): ideas(HR) - ideas(K*) >= 1 on >= 3 units, all known, 0 novel. Observed: 3 units (T10, B3, B6). Every
HR-only idea is a named catalogue algorithm. Each turns up at T = 1 only once in about 2 x 10^6 to 5 x 10^7
samples. The fork dose (top-20) lifts it at most to the masses shown, far below the 0.05 the plan asked for, because
these ideas sit at deep ranks (B3: ranks 34 and 52; B6: rank 18 with tiny mass) or behind a token whose programs
mostly fail (T10: ` def bfs`, whose 10 mapped continuations pass 2/10).

### Activation geometry (F8)

The engine stores the final-norm hidden state of the 16 positions from the decision token on (no extra forward pass).
`figures/F8_activation_geometry` shows PC1/PC2 of the per-slot mean, in actual activation coordinates, for the twin,
fork-dosed, class-forced and global-T slots of each unit.

- The states separate by the algorithm the program implements. Examples: T10 union-find / DFS / BFS; B3 Kruskal /
  Prim. PC1+PC2 explain 61-81% of the variance.
- Fork-dosed slots land in the cluster of their own algorithm.
- A descriptive nearest-centroid check (centroids from the class-forced slots) assigns the fork-dosed slots to their
  own program's class:
  - T10 0.90 (n = 94), B3 0.97 (73), A3 0.975 (80), B6 0.83 (77);
  - G 0.69 (86), where Gemma's BFS and DFS programs share most of the 32-token opening.
- So the dial reaches the model's own alternative-idea states (on-manifold), not new regions.

### Novelty audit

After adjudicating labeller disagreements, only 2 correct programs from any stage carry the label 'other'. Both come
from the T03 boundary window (k-th smallest) and both are counting sort in dictionary form: a frequency map over sorted
distinct keys, walked cumulatively to the k-th element. The frozen T03 labeller only knows the array form; the plan
had named this extension.

Two blind judges of different families independently called both programs CATALOGUE VARIANT (counting sort), and so
did the manual read. Both judges passed their gate of 10 known-class controls:

- gemini-2.5-flash: 10/10;
- deepseek-chat-v3.1: 8/10 (it called both known-outside-catalogue controls "novel").

Their nearest known solutions (identifier-normalised AST tree edit distance 35-55, over 17,442 solutions from all ten
datasets of art_j3Rm_lr2nzR6) are KodCode, HumanEval+ and XLCoST programs. **Novel algorithms: 0 of 5,543 correct
programs**, rule-of-three 95% upper bound 0.0005.

## How to read these results (scope and limits)

- **What the knob is.** Temperature T = d with a top-20 restriction at ONE generated index (the located decision
  token; on T10 a second dose at index 11 after ` def`), T = 1 everywhere else. It needs offline knowledge: the
  decision index and a token map of forced continuations (about 200-500 full programs per node). Adaptive samplers
  (EDT, AdapT, min-p) need none of this. The claim is scoped to counterfactually located decision tokens.
- **Estimates, not single draws.** Every cell is N = 50 slots (5 templates x 10 CRN streams), with Newcombe
  intervals on paired pass costs, exact McNemar tests on paired flips and a 2,000-replicate paired slot bootstrap
  with the best-setting selection inside every replicate. Cells of 50 give standard errors of about 0.07 on shares
  near 0.4; the committed noise ceiling for MAE <= 0.10 is 1.00 on every unit (the MAE averages over 5-12 classes).
- **Predictions were committed before the samples.** The dose table, every per-arm composed prediction and the
  per-slot replay predictions are in COMMIT #1 (02:14:06 UTC); the first Stage 3 row is later (results/rederive.json).
  Two choices made before COMMIT #1 depart from the plan and are logged (D05 plug-in token maps; D06 ` def` routing).
- **Actionability with collateral damage measured.** Every intervention is scored on the generated program, with
  its hidden-test pass rate, per-slot flips against the twin (F7), breakage among slots whose decision token changed,
  and reversion. The same dose at a random position is the random-perturbation control. Effects are reported as
  per-cell distributions with paired intervals, not as one mean at one coefficient.
- **No fitted map.** The knob changes the sampling distribution at one position. Nothing is aligned or trained, so
  no map class needs declaring. F8 is a descriptive PCA of the model's own states, plus a nearest-centroid check.
- **Coupling, not identity.** Every arm reuses each slot's uniforms, so per-slot flips are paired. Exact byte identity
  for slots whose decision token did not change is NOT guaranteed: batch shape changes kernel numerics (U1 5/8 at
  batch 8, U2a 17/20), so the identity shortcut was disabled and every slot was generated.
- **Labels.** Frozen iteration-5/6 labellers (hidden tests + runtime tracer + AST); rows where they disagreed
  ('disputed', or an unresolved runtime/AST split) were adjudicated by two blind judges with a tiebreak, for twins
  and token maps before COMMIT #1 and for Stage 3/4 rows after it.
- **Scope.** One prompt family per unit (5 neutral templates), two models (Qwen3-8B on 7 units, Gemma-3-4b-it on the
  grid task), memorised LeetCode-style tasks with hidden tests. External validity beyond these units is not tested.

## Validity checks

- Inputs: 737 files copied with sha256 (0 mismatches, `inputs/input_hashes.json`).
- Labellers: reference implementations 11/11 (A3 4, B3 4, B6 3); agreement with stored labels of 20 prior programs per
  unit: B3, A3, B6 20/20; Gemma T1 18/20 (two slow BFS programs that the runtime tracer calls `iddfs`; the judges
  adjudicate them as BFS). Opening-classifier agreement with full labels on completed programs: T10 0.989 (n = 350),
  B3 0.985 (n = 406).
- CPU tests C1-C6 pass (`results/tests_cpu.json`): composition = closed form to 1e-9, two-token composition = brute
  force, rarefied Hill = brute force, Newcombe = hand computation, AdapT block starts on 5 programs, commit-chain tamper
  detection.
- GPU tests (`results/tests_gpu.json`): U3 replay from the twin's captured logits names the dosed decision token in
  19/20 slots (20/20 from the arm's own logits); U4 top-20 truncation at T = 100: 0/2,000 draws outside the top 20,
  chi-square p = 0.74; U5 the decision index is exact on every canonical-opening slot; U6 entropy formula to 1e-6;
  U7 forcing ` def dfs` gives DFS 10/10 and ` def find` union-find 10/10. U1 (batch 1: 3/3, batch 8: 5/8 identical) and
  U2 (17/20) fail, hence no identity shortcut. U8 (Gemma): ` visited` gives DFS 4/5 (+1 `iddfs`), ` queue` gives BFS
  3/5 (+1 `iddfs`, 1 DFS) with 1/5 passing.
- Independent re-derivations, standard library only, reading the raw rows:
  - `audit/rederive.py` reproduces every MAE, pass rate and Hill-1 exactly. Shuffled predictions raise the MAE to
    0.13-0.22, and shuffling arm labels within slot removes the fork-vs-global-T difference. The chain verifies, no
    Stage 3 row precedes COMMIT #1 and no HR row precedes COMMIT #2.
  - `audit/rederive_tests.py` re-runs the tests with its own code: McNemar 7:1, p = 0.035 (shuffled: 3.1% of
    shuffles reach p <= 0.05; constant arm: p = 1); B6 bootstrap p = 0.006 (twin as fork: p = 0.94); T10 bootstrap
    p = 0.30 (twin as fork: p = 1.0); HR 3 units; 0 novel of 5,543 correct programs.
- Engine check (per-slot label agreement with the source artifacts' programs at the same streams): T10 30/30, T1
  30/30, B3 49/50, T2 29/30, T03 30/30, A3 46/50, B6 47/50, G 47/50; A3, B6 and G fall short of 0.95 (kernel
  sensitivity on a different GPU); every contrast uses this artifact's own twins.

## Deviations from the plan

Every deviation is in `results/deviations.json` with its reason. The main ones:

- **Cost.** OpenRouter judges about USD 0.16 in total (`results/costs.json`); no other paid calls.
- **GPU (D01).** One NVIDIA L4 (23 GB, power-capped at 72 W, about 90-170 ms per decode step) instead of the RTX
  A4500. The GPU work took 2.8 h of job wall-clock (2.5 h of logged decoding), within the 3.3 h cap.
- **Drop order applied (D07).**
  - The plan-noise and base-intent comparator rows (A12/A13) were not run or reused.
  - min-p (A4) and AdapT (A6) were run on T10 and B3 but dropped on A3 and B6.
  - Gemma got its planned arm set.
- **Commits.**
  - COMMIT #0 was written after the twins started (D02). The thresholds were fixed in `src/cfg8.py` before any twin.
  - Four code files hashed live at #0 were later edited for engineering reasons (D04); later commits snapshot their
    files.
  - The locator verdict came after COMMIT #1 as COMMIT #1b (D08).
  - The scoring code committed at #1 had one post-commit fix: the sign of the reported pass-cost interval (D18).
- **Token maps (D05, decided before COMMIT #1).**
  - The composition uses plug-in token-map frequencies. The plan's pseudo-count of 0.5 per class, over 5-12 classes,
    would have moved every composed share by 0.08-0.38 toward uniform. The pseudo-count is kept only for the
    committal rule, over the classes observed at the node.
  - The committed off-opening term q_rest still carries the pseudo-count, a known 0.005-0.01 mass on absent classes.
- **T10 routing (D06).** ` def` triggers the index-11 dose because n11 = n10 + ` def` is the pre-registered second
  decision. Its T = 1 map reads union-find 10/10 because ` find` follows 97% of the time.
- **T1 failed validation.** No index-3 token gives >= 5/10 off-default programs. As pre-registered, T1 became a
  boundary unit and the grid claim moved to Gemma.
- **No identity shortcut (D13).** U2 failed (17/20 byte-identical when the batch shape differs), so every arm slot was
  generated.
- **Amendment (D19).** The pass-filtered fork dose (A9f/A10f on T10 and G) was added after the primary T10/B3/G
  cells were seen and committed (COMMIT #3) before any of its samples. It is reported separately and never replaces
  A9/A10; `src/amend_analysis8.py` scores it (`results/amendment.json`).
- **Labels (D12).** Rows with 'disputed' or unresolved runtime/AST labels were adjudicated by two blind judges and a
  tiebreak: 574 rows, 572 resolved.
- **Other.**
  - The fallback decision position for off-opening slots is not implemented (D10). Those slots run at T = 1 and are
    counted as not dosed; reached-decision is 0.74-1.00.
  - F8 centroids come from the class-forced slots (D11).
  - AdapT also heats the indentation tokens before a block's first word (D14).
  - max_new keeps the source artifacts' values (D16).
  - The T03 dictionary-form counting-sort labeller extension was not run (D09). The two such programs were classified
    by the audit.

## What was run

Every arm shares each unit's 50 common-random-number (CRN) slot streams (5 prompt templates x 10 slots; the source
artifacts' own stream keys), so a slot sees the same uniforms in every arm. The sampler is the iteration-6 float64
inverse-CDF sampler in token-id order (Gemma: exp38 numerics); `src/engine8.py: decode_k1` adds a per-row, per-step
schedule (global T / top-p / min-p, EDT, AdapT, a dose at the decision index, placebo positions, forcing) and logs the
decision index, the T = 1 top-64 logits and entropy at the decision, per-step T = 1 entropies and the final-norm hidden
state after the decision.

| stage | what | size |
|---|---|---|
| -1 setup | 737 input files copied into `inputs/` with sha256 (0 mismatches); labeller re-check on references (A3, B3, B6: 11/11) and on 80 prior programs (B3/A3/B6 20/20, Gemma T1 18/20); CPU tests C1-C6 | `results/tests_cpu.json` |
| COMMIT #0 | protocol, thresholds, arm definitions (`predictions/protocol.json`) | |
| 0 | twins (T = 1) on T10, T1, B3, A3, B6, T2, T03 (Qwen3-8B) and G (Gemma-3-4b-it), N = 50 each; GPU tests U1-U8; engine check vs the source artifacts' programs at the same streams | 400 programs |
| 1 | blind locator on T10 and B3: 6 twin base paths, prefixes 2, 4, ..., 64, 8 continuations each (stopped when the opening classifier decides); Bayesian change points + 1,000-shuffle permutation null | 3,072 continuations |
| 2 | token maps: at every decision node, teacher-forced logits per template, and 10 full T = 1 continuations for each of the ~24 most probable tokens (T10 n10 and n11, B3 c0/c1, A3 c0/c1, B6 c0, T1, G); labelled and tested | 2,050 programs |
| COMMIT #1 | dose table (d1, d2), composed predictions for every arm (attempted / correct shares, pass cost, reversion), per-slot replay predictions, q90, placebo positions, class-uniform draws, noise ceiling, T1 validation | `predictions/commit1_dose_table.json` |
| COMMIT #2 | HR predictions and the novelty-audit protocol | `predictions/commit2_hr.json` |
| 3 | arms A1-A11 on T10 and B3 (all), B6 and A3 (A4/A6 dropped), G (A1, A3g, A5, A7-A11); boundary window B1 on T1, T2, T03 | see tables |
| 4 | HR: tokens ranked 21-64 at each node forced and continued 5 times | |
| 5 | adjudication of disputed labels (two blind judges + tiebreak); novelty audit of every correct 'other' program | |
| 6 | analysis (`src/analysis_k1.py`, committed at #1), HR (`src/hr8.py`), locator, figures, stdlib re-derivation | |

## Layout

| path | content |
|---|---|
| `method.py` | entry point: every stage in order (`.venv/bin/python method.py all`, or a comma list of stages) |
| `src/cfg8.py` | constants, units, slot keys, thresholds, utilities |
| `src/engine8.py` | model loading (Qwen3-8B bf16, Gemma-3-4b-it bf16 text tower), prefill, teacher forcing, `decode_k1` |
| `src/units8.py` | prompts, decision nodes (canonical openings), opening classifiers, source twin labels |
| `src/gpu8.py`, `src/stages8.py`, `src/arms8.py` | GPU runner and stages 0-4 (one model per process, resumable) |
| `src/label_daemon.py`, `src/label7.py` | background labelling with the frozen labellers (exp35 label worker, vendored) |
| `src/dose8.py`, `src/predict8.py` | token maps, composition, dose table, replay, statistics (Newcombe, McNemar, rarefied Hill, noise ceiling) |
| `src/protocol8.py`, `src/make_commits.py`, `src/commit8.py` | COMMIT #0/#1/#2 and the sha256 hash chain (`commitments.log`, snapshots in `predictions/snapshots/`) |
| `src/tests8.py`, `src/stage0_report.py` | CPU tests C1-C6, GPU tests U1-U8, engine check |
| `src/analysis_k1.py`, `src/hr8.py`, `src/locator8.py`, `src/novelty8.py` | K1 cells and verdicts, HR, locator, adjudication and novelty audit |
| `src/figures8.py`, `src/report8.py`, `src/outputs8.py`, `src/finalize8.py` | figures, summary tables, `method_out.json`, final checks |
| `src/amend8.py`, `src/amend_analysis8.py` | the COMMIT #3 amendment (pass-filtered fork dose): predictions, commit, scoring (`results/amendment.json`) |
| `scripts/` | model download, Gemma prompt rebuild, GPU job runner (`run_gpu.sh`, `after.sh`) |
| `audit/rederive_tests.py` | second stdlib re-derivation: shares, exact McNemar, paired bootstraps, HR and novelty counts, each with a placebo -> `results/rederive_tests.json` |
| `reproducibility.md`, `restore.sh` | exact commands as run; restore script for every deleted path |
| `audit/rederive.py` | standard-library re-derivation of the headline numbers, placebos, chain and timestamp checks |
| `data/samples.jsonl`, `data/labels.jsonl` | every twin/arm/test program (token ids, text, schedule, decision logs) and its label |
| `data/continuations.jsonl`, `data/continuation_labels.jsonl` | locator, token-map and HR continuations and labels |
| `cache/nodes/*.json` | teacher-forced top-64 logits per node and template, map tokens (kept; small) |
| `cache/hid/*.npz` | mean final-norm hidden states after the decision (F8; kept, 12 MB) |
| `predictions/` | protocol, COMMIT #1/#2 tables, hardware, stage-3 flags, committed snapshots |
| `results/` | stage0, tests, locator, k1_cells, k1_verdict, hr, adjudication, novelty_audit, positioning, geometry_f8, deviations, timing, summary.md, rederive |
| `figures/` | F1-F8 (PDF + PNG) |
| `inputs/` | sha256-verified copies of the prior artifacts this pipeline reads (`inputs/input_hashes.json`) |
| `method_out.json` (+ `full_`, `mini_`, `preview_`) | exp_gen_sol_out output (datasets k1_cells, k1_tokenmap, k1_locator, hr_branches, novelty_audit) |

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python scripts/download_models.py          # Qwen/Qwen3-8B@b968826d, google/gemma-3-4b-it@093f9f38 (HF cache)
.venv/bin/python method.py all                       # or e.g. method.py s3,analyse
```

The GPU stages need one CUDA GPU with at least 20 GB (this run: one NVIDIA L4, 23 GB, power-capped at 72 W). The
judges need `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY`. Every stage resumes from its jsonl rows; the commit stages
refuse to overwrite an existing commit. The prior inputs are read from `inputs/` (copied by `src/vendor_inputs.py`
from the iteration-6/7 workspaces of this run; set `AII_RUN_LOOP` to their location to re-copy). The declared dataset
dependency (art_j3Rm_lr2nzR6, `full_data_out.json`) is read from the sibling folder `../art_j3Rm_lr2nzR6`, or
from `ART_J3RM_DIR`. `reproducibility.md` lists every command as run; `restore.sh` restores the deleted paths.

## Restoring removed files

| removed path | restore with |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` |
| `cache/known_index.pkl` (novelty-audit retrieval index) | `.venv/bin/python src/novelty8.py index` |
| `**/__pycache__/` | regenerated on import (`.venv/bin/python -m compileall -q src inputs build`) |
| model weights (shared HF cache, not in this folder) | `.venv/bin/python scripts/download_models.py` |
