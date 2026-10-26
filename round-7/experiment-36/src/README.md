# Why random nudges stopped changing the algorithm

Iteration 7, step K of a research run on **Qwen/Qwen3-8B** (revision `b968826d…`, bf16, HF transformers 4.57.6,
thinking off). The model nearly always writes one default algorithm per task (union-find for connected components
T10, Dijkstra for weighted shortest paths T2, a full sort for the k-th smallest T03, a hash map for two-sum T05, BFS for
grid paths T1).

**Plan noise (PN)** pushes a fresh, isotropic random direction `u` per sample into the task-specification positions
of decoder blocks 12–23 during the prompt prefill. The edit is displacement-targeted:
`h ← h + (α·n[l,p] − (h − h_twin)·u) u`, so the displacement from the clean twin along `u` is exactly `α·n[l,p]`.

Iteration 4's PN moved T10 off union-find on 25 of 50 programs in bf16 (exp29, engine d). Iteration 5's PN moved it on
1 of 50 (exp27). Reading the code shows that the two designs differ in three ways:

1. **The dose unit.**
   - `U_abs` (iteration 4) is the ban's own per-block, per-position displacement norm `n[l,p]`.
   - `U_bf` (iteration 5) is `‖h_twin[l,p]‖ · r_Q(l)`.
2. **The direction seeds.**
   - `S4` = `PCG64(stable_seed(task,'PN_a<α>',w,k))`.
   - `S5` = `PCG64(stable_seed(task,'PN5',w,k))`.
3. **The decoding path.** Exp27 decoded part of its PN rows left-padded and part on the shared-prefix path. This third
   difference was never crossed.

This artifact crosses unit × seeds on shared common-random-number (CRN) slots, in one engine and on one decoding
path. It reproduces both earlier results as anchors and then asks two more questions: where the dose has to land, and
what plan noise at the design that moves is worth against iteration 5's text-level plan samplers.

## Results

### Bottom line

- **Both anchors reproduce, on the shared-prefix path.**
  - `D1 = U_abs × S4` (exp29's design) attempts an off-default algorithm on 26/50 T10 programs. Exp29 had 25/50
    (Fisher p = 1.0), and the per-slot label agreement with exp29's engine-d rows is 0.98.
  - `D4 = U_bf × S5` (exp27's design) gives 1/50 correct off-default programs. Exp27 also had 1/50 (p = 1.0).
  - So the iteration-5 null is reproduced without any left padding: the decoding path is **not** the cause.
- **The answer is UNIT** (committed decision rule, T10 α 2, Holm over three tests).

  | T10, α 2, N = 50 per design | share Y | 95% CI |
  |---|---|---|
  | D1 = U_abs × S4 | 0.50 | [0.37, 0.63] |
  | D2 = U_abs × S5 | 0.52 | [0.39, 0.65] |
  | D3 = U_bf × S4 | 0.10 | [0.04, 0.21] |
  | D4 = U_bf × S5 | 0.02 | [0.00, 0.10] |
  | unit main effect (RD) | **+0.45** | [0.35, 0.55] |
  | seed main effect (RD) | +0.03 | [−0.07, 0.14] |
  | interaction | −0.10 | [−0.28, 0.08] |

  - The unit effect has exact sign-flip p ≈ 1e-5 (Holm 3e-5). The conditional logit with slot strata gives
    β_unit = 4.34 (p = 1e-4) and β_seed = 1.68 (p = 0.13).
  - The seeds are exchangeable: swapping the 50 S4 draws for the 50 S5 draws changes nothing.
  - T2 (N = 100 per design) replicates it: shares 0.13 / 0.20 / 0.05 / 0.05, unit RD +0.115 [0.06, 0.17], seeds
    −0.035 [−0.10, 0.03].
  - α 1 replicates it too, on both tasks (unit RD +0.12 on T10, +0.14 on T2; seeds ≈ 0).
  - All seven committed S1/S2 predictions hold (table below).
- **Both halves of the unit matter (D5 split, T10).** `U_bf*` keeps `U_bf`'s flat within-block profile but takes
  `U_abs`'s per-block energy (Frobenius norm per block). It moves 14/50 (0.28), between the two units.
  - **Profile at matched energy** (D1 − D5): +0.22 [0.08, 0.36] (McNemar 13:2, p = 0.007).
  - **Energy at the ban-free shape** (D5 − D3): +0.18 [0.06, 0.30] (10:1, p = 0.012).
  - On T2 both parts are small and not significant (+0.05, +0.03).
- **Pushes act where bans write (S2, T10; committed reading met).** All three profile arms carry U_abs's total
  Frobenius norm.
  - **Top quartile vs the rest.** U_abs restricted to its top-quartile cells (81% of its energy) moves 29/50 (0.58).
    Restricted to the other three quartiles it moves 15/50 (0.30): McNemar 18:4, Holm p = 0.009.
  - **The top quartile carries the effect.** The top-quartile-only unit is indistinguishable from the full unit
    (0.58 vs 0.50, p = 0.39).
  - **Position matters.** Permuting the spec positions (same energy and same per-block profile, other tokens) drops
    it to 4/50 (21:0, p ≈ 1e-6).
  - **T2 caveat.** T2's U_abs is dominated by one massive-activation cell: spec position 87, a "0" digit token whose
    residual norm jumps to ~10,290 at block 16. It carries n ≈ 748 at blocks 16–23, 82% of the unit's energy. exp22
    lists it as an outlier but applies no exclusion rule, and exp29's design uses the raw unit, so it is kept here.
    - The rest-cells arm drops that cell and rescales the rest ~5×, which breaks the programs (pass 0.00).
    - The shuffled arm moves the cell's dose onto an ordinary token, 19× that token's residual norm. Programs still
      pass (0.86) and none escape.
    - The T2 profile contrasts therefore test where the dose of one cell goes, not where bans write. T10's unit has
      no such cell (maximum residual norm ≈ 231). Its energy is spread over task tokens such as " a", " the" and
      whitespace (F2).
- **The size of the downstream displacement is not what moves the algorithm.**
  - At α 2 the realised displacement at block 35 is about the same for U_abs and U_bf, both at the read position R
    and at generated position 1 (F3, F4). U_abs still escapes 5–25× more often.
  - Adding the log block-35 norms to the per-sample logit leaves the unit coefficients unchanged on T10 (D3: −2.35 →
    −2.54; D4: −3.31 → −3.49).
  - The top-quartile arm has the *smallest* downstream displacement of all pushed arms and moves the most.
- **Exploratory E1: dose sweep of the ban-free unit.** U_bf needs α ≈ 4 (20/50, pass 0.98) to approach what U_abs does
  at α 2 (25/50).
  - At α 4 it pays 1.8× U_abs's downstream R displacement (423 vs 240).
  - At matched block-12 dose (α 3, 13.6 vs 13.8) it moves only 9/50 (McNemar 1:17 vs D1).
  - At α 6 it breaks the programs (pass 0.46).
  - On T2 it never gets past 5/50 before breaking.
- **Exploratory E2: which samples escape is close to a coin flip per (direction, token stream).**
  - Two different directions on the same CRN token stream (D1 vs D2) agree only weakly: φ = 0.16–0.20 on T10 and
    ≈ 0 on T2.
  - The same direction at α 1 and α 2 is not even monotone: P(escape at α 2 | escape at α 1) = 0.33 (2 of 6)
    against a marginal 0.52.
  - Within U_abs at α 2, neither the size nor the direction of the block-35 displacement predicts which samples
    escape (5-fold CV AUC 0.40–0.53).
  - The unit sets the escape *rate*. Individual outcomes behave like per-sample random variables, as the field
    handbook warns for steering.
- **S3: prices at the design that moves, D\* = D1.** By the committed rule, D2 was within the 0.10 tie band, so D1
  was kept.

  | task | PN\* | base intent | enumerate-and-pick | IFG(1.3, 0.7) | T 1.3 | top-k 10 | PN\* vs base intent |
  |---|---|---|---|---|---|---|---|
  | T03 | **3.22** | 1.73 | 1.77 | 1.09 | 1.09 | 1.09 | WIN (P = 1.00) |
  | T10 | 2.13 | 2.53 | 1.79 | 1.96 | 1.00 | 1.00 | LOSS (P = 0.05) |
  | T2 | 1.21 | 1.45 | 1.28 | 1.00 | 1.00 | 1.00 | LOSS (P = 0.15) |
  | T05 | 1.10 | 1.61 | 1.16 | 1.00 | 1.00 | 1.00 | LOSS (P = 0.00) |
  | T1 | 1.39 | 1.05 | 1.11 | 1.00 | 1.00 | 1.00 | WIN (P = 0.99) |

  - **Against base intent: 2 of 5.** Plan noise matches or beats base-written intent on 2 of 5 tasks (T03, T1); the
    committed prediction was 3.
  - **H5 ≥ 2 on T03 and T10**, as predicted.
  - **Iteration 5's own rule, replayed: still DISCONFIRMED.** PN\* matches or beats the best text sampler on 2 of 5
    tasks (iteration 5: 1 of 5).
  - **But the mean margin moved.** D̄ goes from −0.40 [−0.70, −0.24] in iteration 5 to **+0.12 [−0.18, +0.27]**.
  - **So the correction is partial.** Most of iteration 5's "plan noise loses" came from its ban-free unit. At the
    unit that moves, PN is the best knob on T03 and T1 and competitive on T10. Base-written intent still wins on T10,
    T2 and T05.
- **Re-tag of iteration-5 verdicts** (`results/retag.json`). Iteration 5's plan-sampler verdict and its movability
  verdict get the tag *"ban-free unit and iteration-5 seeds"*. At D\* (α 2):
  - T03 is movable (+0.58).
  - T10 is movable (+0.50).
  - T2 is not: +0.16, and its pass rate drops to 0.62 against the twin's 0.98, which fails the pass clause.
  - T05 (+0.02) and T1 (+0.08) are not movable.
  - T06 was not tested.
- **Novelty audit: 0 novel algorithms.** Five correct "other" programs were audited, all on T03. They share one
  mechanism: a hash-map frequency count, then the sorted distinct keys walked by cumulative count.
  - **Judges.** Two judge families (Mistral, Kimi) were used, with DeepSeek breaking ties. They split between the
    catalogue's counting sort (a labeller miss) and a counting-sort variant; no judge called any of the five NOVEL.
    The manual pass classifies all five as a catalogue variant (counting sort with key compression).
  - **Controls.** 9 of 10 known-class control programs were judged to be their catalogue algorithm; the tenth, an SPFA
    program, was called a variant named SPFA.
  - **Nearest known solutions.** These come from all 10 datasets of the declared dependency (18,237 code
    solutions).
- **Audits.** All of these pass:
  - CPU gates G1–G5;
  - GPU unit tests U1–U6;
  - the stdlib re-derivation, through a separate code path, of every headline number (0 mismatches):
    - the anchors and all 2×2 shares and contrasts;
    - bootstrap CIs and sign-flip p;
    - the D5 split and S2 McNemar counts;
    - E1 counts and E3 contrasts;
    - all five S3 PN\*-vs-base-intent orderings;
    - the novelty count;
    - its placebos: shuffled designs give RD ≈ 0, shuffled S2 McNemar median p is 0.83, and PN\*-as-twin gives
      H5 = twin;
  - the commit-order audit (0 decisive rows before their commit);
  - the hash chain (0 breaks).

  Costs: OpenRouter USD 0.10; GPU time about 0.7 h on one RTX 4090 (all stages, including the exploratory ones).

### Exploratory E3: an internal replication and a third task

E3 was hash-committed before its first row and is not pre-registered (`results/e3_replicate.json`, figure
`E3_replicate`).

- **T10 on 50 fresh slots** (k 10–19, never used by S1/S2), N = 50 per design:

  | design | share Y |
  |---|---|
  | D1 = U_abs × S4 | 0.42 |
  | D2 = U_abs × S5 | 0.60 |
  | D3 = U_bf × S4 | 0.08 |
  | D4 = U_bf × S5 | 0.10 |

  - The unit effect replicates: +0.42 [0.32, 0.52] (Holm p = 3e-5; conditional-logit β_unit 3.18).
  - The seed effect is −0.10 [−0.22, 0.02] and the interaction −0.16 [−0.34, 0.02], both not significant. The
    committed decision rule applied to these slots reads **UNIT**.
  - The profile result replicates too. Top quartile 0.48 vs the rest 0.18 (McNemar 15:0, p = 6e-5). Full unit 0.42
    vs position-shuffled 0.08 (17:0, p = 2e-5). Top quartile vs full unit is not significant (0.48 vs 0.42).
  - Pooled over k 0–19 (N = 100): unit +0.435 [0.36, 0.515], seed −0.035 [−0.115, 0.045].
- **A third task, T03 (k-th smallest), α 2, N = 50:**

  | design | share Y |
  |---|---|
  | D1 | 0.56 |
  | D2 | 0.52 |
  | D3 | 0.28 |
  | D4 | 0.26 |

  - The unit effect is +0.27 [0.18, 0.37] (Holm p = 3e-5); the seed effect is +0.03 [−0.12, 0.18] → **UNIT**.
  - Unlike on T10, the ban-free unit does move T03 (to quickselect and a size-k heap), but only half as often as the
    absolute unit.

### Committed predictions (COMMIT #1, before any S1/S2 row; COMMIT #2, before any S3 row)

| id | prediction | observed | verdict |
|---|---|---|---|
| P-S1a | unit RD on T10 α 2 > 0, CI excludes 0 (point +0.35, range 0.20–0.50) | +0.45 [0.35, 0.55] | confirmed |
| P-S1b | seed RD within ±0.10, CI includes 0 | +0.03 [−0.07, 0.14] | confirmed |
| P-S1c | interaction CI includes 0 | −0.10 [−0.28, 0.08] | confirmed |
| P-S1d | T2 α 2 unit RD on correct programs ≈ +0.10 | +0.115 [0.06, 0.17] | confirmed |
| P-S1e | U_bf\* intermediate, T10 α 2 share 0.05–0.35 | 0.28 | confirmed |
| P-S2a | P_top > P_rest by ≥ 0.10 | T10 0.58 vs 0.30 | confirmed |
| P-S2b | D1 > P_shuf by ≥ 0.10 | T10 0.50 vs 0.08 | confirmed |
| S3 | PN\* matches or beats BINT on 3 of 5 | 2 of 5 (T03, T1 WIN; T10, T2, T05 LOSS) | missed by one |
| S3 | H5(PN\*) ≥ 2 on T03 and T10 | 3.22, 2.13 | confirmed |

### S1 cells (Y = passed and a named catalogue algorithm other than the default; A = valid and off-default)

| task | arm | N | Y (Wilson 95%) | Y_any | A | pass |
|---|---|---|---|---|---|---|
| T10 | TWIN | 50 | 0 [0.00, 0.07] | 0 | 0 | 1.00 |
| T10 | D1 α1 / D2 α1 / D3 α1 / D4 α1 | 50 each | 6 / 7 / 0 / 1 | same | 6 / 7 / 0 / 1 | 1.00 |
| T10 | D1 α2 | 50 | 25 [0.37, 0.63] | 25 | 26 | 0.98 |
| T10 | D2 α2 | 50 | 26 [0.39, 0.65] | 26 | 26 | 1.00 |
| T10 | D3 α2 | 50 | 5 [0.04, 0.21] | 5 | 5 | 1.00 |
| T10 | D4 α2 | 50 | 1 [0.00, 0.10] | 1 | 1 | 1.00 |
| T10 | D5 α2 (U_bf\*) | 50 | 14 [0.17, 0.42] | 14 | 17 | 0.94 |
| T2 | TWIN | 100 | 0 [0.00, 0.04] | 0 | 1 | 0.99 |
| T2 | D1 α1 / D2 α1 / D3 α1 / D4 α1 | 50 each | 7 / 7 / 0 / 0 | same | 12 / 12 / 2 / 0 | 0.84 / 0.88 / 0.96 / 1.00 |
| T2 | D1 α2 | 100 | 13 [0.08, 0.21] | 13 | 41 | 0.66 |
| T2 | D2 α2 | 100 | 20 [0.13, 0.29] | 20 | 38 | 0.74 |
| T2 | D3 α2 | 100 | 5 [0.02, 0.11] | 5 | 9 | 0.96 |
| T2 | D4 α2 | 100 | 5 [0.02, 0.11] | 5 | 10 | 0.95 |
| T2 | D5 α2 (U_bf\*) | 100 | 8 [0.04, 0.15] | 8 | 16 | 0.90 |

Landings are the same algorithms as in iterations 4–6. On T10 the correct off-default programs are DFS, plus a few
BFS. On T2 they are Bellman-Ford/SPFA, and on T2 at α 2 most attempts fail the hidden tests (A ≫ Y). No program was
disputed, and no row hit `max_new`.

### Why the units differ, in activation coordinates (F2, `results/unit_profiles.json`)

`U_abs` is peaky: on T10 its top quartile of cells holds 81% of its energy, on bands of a few task tokens. Its peak
cell dose at α 2 is about 2.1× the residual norm of that cell. `U_bf` is flat by construction: its top quartile holds
42%, and its peak dose is 0.25× the residual norm.

Two simple summaries of their ratio disagree, which is exactly the confound the U_bf\* arm splits:

- the ratio of their per-block mean norms is 0.66–0.78 on T10;
- the mean per-position ratio is about 1.0.

Their total Frobenius ratio is 0.62.

On T2 both units are dominated by the massive-activation cell. U_bf there is ‖h‖·r_Q ≈ 1,000, which is 98% of U_bf's
energy, and the T2 Frobenius ratio is 1.44. On T2 the two units therefore differ mainly away from that cell, which is
consistent with T2's smaller unit effect.

### Figures (`figures/*.pdf|png`)

| figure | content |
|---|---|
| `F1_s1_interaction` | the 2×2 per task and α (unit on x, seed schemes as lines, U_bf\* beside), Wilson 95% |
| `F2_unit_heatmaps` | U_abs, U_bf, U_bf\*, P_top, P_rest, P_shuf and ‖h_twin‖ over blocks 12–23 × T10's spec tokens, in residual-norm units |
| `F3_displacement_blocks` | realised ‖Δh‖ against the clean twin per block (12–35) at the spec mean, the read position and generated position 1, per design (α 2) |
| `F4_escape_vs_disp` | per-sample outcome against the block-35 read-position displacement, per design |
| `F5_pca_disp35` | PCA of the block-35 read-position displacement vectors (actual residual coordinates), colour = realised algorithm, marker = design |
| `F6_price_frontiers` | pass cost against the best correct-only Hill-1 per task, PN\* and the five knobs |
| `F7_escape_axis` | exploratory E2: projection on an escape axis built from U_abs rows against the downstream displacement size |
| `E1_dose_response` | exploratory E1: share and pass against α and against block-35 displacement, U_bf vs U_abs |
| `E3_replicate` | exploratory E3: α-2 shares per design on T10's committed slots, on T10's fresh slots and on T03 |

## Design as run

**Engine.**
- bf16 HF on one RTX 4090 (24 GB; the plan named a 20 GB A4500).
- The vendored exp22 prefill, edit hooks and exact inverse-CDF CRN sampler. Prune is off, the batch shape is constant
  (B = 12, from the memory probe), and generation stops at the fence.
- `max_new` is 1,024 for bench tasks and 1,536 for T1/T2.
- Every row shares the twin's prompt ids, so every row runs on the shared-prefix path.
- Designs are interleaved by slot inside batches. One uniform stream per slot is shared by every arm.

**Cells.**
- **S0.** Twins N 50 on 5 tasks, plus T2 k 10–19.
- **S1.** T10 D1–D4 × α {1, 2} × N 50. T2 D1–D4 at α 2 × N 100 and at α 1 × N 50. D5 on T10 (N 50) and T2 (N 100).
- **S2.** P_top, P_rest and P_shuf on T10 and T2 (α 2, N 50).
- **S3.**
  - PN\* = D1 at α {1, 2} on T03, T05 and T1; T10 and T2 reuse the S1 cells.
  - Base-model intents (Qwen3-8B-Base `49e3418f`): 250 of 250 are identical in text and ids to exp27's.
  - The knob check ran 10 slots per knob per task through exp27's own code paths. 17 of 25 (task, knob) cells
    reproduced exp27's labels 10/10 and reuse exp27's relabelled rows. 8 were regenerated here at k 2–9.
- **Exploratory.** E1 (D3 at α 3/4/6), E2 (geometry, CPU only) and E3 (fresh-slot replicate and a T03 2×2). Each was
  hash-committed before its first row and is never used in a pre-registered test.

**Outcomes.** Invalid and failing programs count as not-target. The attempted share A is reported beside the correct
share.

**Statistics.**
- Slot-cluster bootstrap (2,000).
- Exact sign-flip and McNemar tests.
- Conditional logit with slot strata, or Firth with slot dummies when a cell separates.
- Holm over {unit, seed, interaction}.
- S3 uses exp27's full-simplex hull (vendored unchanged; gate G5 reproduces exp27's H5 2.527 and 1.984 to 4e-4), with
  2,000 slot bootstraps and best-mixture selection inside each replicate.

**Pre-registration.** `commitments.log` is a sha256 chain:
- COMMIT #1 came before the first S1/S2 row and includes `src/analysis_k.py`.
- COMMIT #2 came before the first S3 row and includes `src/s3_prices.py` and `src/knobs_k.py`.
- Three amendments are dated and described in `results/deviations.json`:
  - AMENDMENT 1: the label worker follows the normalised knob rows.
  - AMENDMENT 2 (post hoc, conservative): the Monte-Carlo p is reported as (hits+1)/(N+1), and the mediation is
    restricted to α 1–2.
  - AMENDMENT 3: every committed analysis reads only its committed slots, so the exploratory E3 rows never enter it.
    The numbers are identical to the pre-E3 run, checked field by field.
- The exploratory scripts (`e1_sweep.py`, `e3_replicate.py`) were added to the chain before their first rows.

**Deviations.** The full list is in `results/deviations.json`. The ones that matter:

- **Hardware.** The GPU is an RTX 4090.
- **Engine check against exp30.** Label-and-pass agreement is 15/16 on both T2 and T03 (the planned bar was ≥ 0.95;
  one slot diverged mid-program in each), 40/40 on T10 and T05, and 34/40 on T1 (all BFS; 6 pass flips). This is
  logged as cross-GPU kernel sensitivity.
- **Knob-check agreement** was counted on (label, passed) pairs, which is stricter.
- **The T2 P_rest arm breaks the programs.**

## Layout

| path | what |
|---|---|
| `reproducibility.md` | step-by-step reproduction as actually run: environment, downloads, commands, runtimes, expected numbers |
| `method.py` | entry point: `uv run method.py <step>` runs setup, gates, label, gpu0, commit1, gpu1, commit2, gpu2, knobs, units, e1, analyse, prices, novelty, geometry, figures, report, rederive and outputs, or all of them |
| `src/k_cfg.py`, `src/k_units.py` | paths and constants; dose units, direction seeds (S4/S5), profile masks |
| `src/gen_k.py` | GPU runner: hardware record, memory probe, unit tests U1–U6, S0/S1/D5/S2/S3-PN cells, masked TARGET edits, 36-block displacement logging |
| `src/label_k.py` | label worker: exp22's labeller plus the exp28 T2 re-gate (exp29 version); a judge is called only on runtime/AST disagreement |
| `src/make_commits.py`, `src/commit_k.py`, `commitments.log` | COMMIT #1 / #2 and the hash chain (`commit_k.py verify`) |
| `src/analysis_k.py` | anchors, 2×2 contrasts, bootstrap and sign-flip tests, conditional logit / Firth, decision, D5 split, mediation, S2, D\*, E1 summary |
| `src/knobs_k.py` | S3 knob process running exp27's code paths unchanged: base pass, relabel queue, knob check, reruns |
| `src/s3_prices.py` | S3 hulls and bootstraps, readings, iteration-5 rule replay, re-tag, gate G5 |
| `src/cpu_gates.py` | gates G1–G4 (G5 comes from `s3_prices.py`) |
| `src/novelty_k.py` | nearest-known search over all 10 dependency datasets; two-family judge audit with controls; manual pass |
| `src/dump_units.py`, `src/e1_sweep.py`, `src/e3_replicate.py`, `src/geometry_k.py`, `src/extensions_k.py` | unit dump; exploratory E1, E3 and E2 |
| `src/figures_k.py`, `src/report_k.py`, `src/outputs_k.py`, `src/setup_inputs.py` | figures; engine check, timing, costs, deviations and commit audit; `method_out.json`; input copy with sha256 manifest |
| `audit/rederive.py` | independent stdlib re-derivation and placebos → `results/rederive.json` |
| `data/raw/raw_k.jsonl` | every instruct program generated here: text, token ids, slot, design, α, seeds, realised displacement |
| `data/raw/knobs_raw.jsonl`, `data/raw/knobs_norm.jsonl` | S3 knob programs generated with exp27's code (as written / with integer slot keys) |
| `data/raw/reuse_exp27.jsonl` | exp27's knob rows queued for relabelling (arm `E27:<knob>`) |
| `data/labels.jsonl` | one label per program, keyed `<task>\|<template>\|<arm>\|<k>` |
| `data/samples.jsonl` | one joined row per program (protocol fields, label, Y / Y_any / A, realised-displacement summary, extracted code) |
| `data/realised_disp.jsonl` | 36-block displacement profiles (spec-mean, per-position, R, generated position 1) of every pushed prefill |
| `data/bint_intents.jsonl`, `data/knobs_stages.jsonl` | base-model intents; EAP stage texts |
| `results/` | every analysis as JSON (`s1_2x2`, `s1_clogit`, `s1_mediation`, `displacement`, `anchors`, `s2_profile`, `s3_prices`, `retag`, `e1_sweep`, `e2_geometry`, `e3_replicate`, `novelty_audit`, `cpu_gates`, `unit_tests_gpu`, `engine_check`, `knob_check`, `commit_audit`, `timing`, `costs`, `deviations`, `rederive`) |
| `predictions/` | `commit1.json`, `commit2.json`, `hardware.json` |
| `figures/` | PDF and PNG figures |
| `method_out.json`, `full_/mini_/preview_method_out.json` | `exp_gen_sol_out` output: one example per CRN slot with `predict_<arm>` = `label\|passed` |
| `cache/` | fp16 displacement vectors per pushed row (`cache/disp/`) and dose-unit dumps (`cache/units/`) |
| `inputs/`, `vendor/` | verified copies of every earlier-artifact input and the vendored exp22/exp19/exp28/exp27 code (`inputs/MANIFEST.tsv`: source, size, sha256) |

## How to run

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r pyproject.toml   # torch 2.8.0 (cu128)
hf download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218
hf download Qwen/Qwen3-8B-Base --revision 49e3418fbbbca6ecbdf9608b4d22e5a407081db4
uv run method.py all          # or step by step, e.g. uv run method.py analyse prices figures outputs
```

- **GPU.** The GPU steps need one CUDA GPU with at least about 20 GB (bf16 weights plus the KV cache). One 8B model
  is loaded at a time.
- **Inputs.** `setup` copies the inputs from the earlier run folders: iteration 6 of this run, iterations 2–5 of run
  `run_aRfWvcSWjssb`, and the dependency `art_j3Rm_lr2nzR6`. Override the locations with `AII_ITER6_ROOT`,
  `AII_ITER25_RUN` and `AII_DEP_ART_J3RM`. The verified copies already ship in `inputs/` and `vendor/`.
- **Judges.** The judges use OpenRouter (`OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY`). They are called only on
  runtime/AST disagreement and for the novelty audit. This run spent USD 0.10.
- **Resuming.** Every step resumes by row key, and existing commits are never rewritten.

## Restoring removed files

`.aii/manifest.yaml` marks these paths for deletion after the round:

| path | how to restore |
|---|---|
| `.venv/` (9.9 GB) | `uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r pyproject.toml` |
| `src/__pycache__/`, `vendor/**/__pycache__/` | Python bytecode, rebuilt on import (`.venv/bin/python -m compileall -q src vendor`) |

The model weights were never stored in this folder; they sit in the run's shared Hugging Face cache. Restore them
with the two `hf download` commands above.

`cache/` (64 MB, every file small) is not removed and needs no manifest entry. It stays in place with the per-row
displacement vectors and the unit dumps that F2, F5, F7 and E2 read. Regenerating it needs the GPU stages (`gpu1`,
`gpu2`, `units`, `e1`).
