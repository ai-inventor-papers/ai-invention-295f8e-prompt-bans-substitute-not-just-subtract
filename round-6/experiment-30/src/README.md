# Where noise changes the algorithm, in bf16 (iteration 6, Step 2)

Iteration 4's site study (exp20) found that random noise changes which correct algorithm Qwen3-8B writes only when
the noise enters the task-specification states. The read-out positions, the condition sentence and the late blocks
were inert. That study ran in FP8, and Claim E puts its FP8 positives in doubt. This artifact reruns the study in
**W16A16** (bf16 weights and activations). It uses the same displacement-targeted hook, prompts, labellers and
paired common-random-numbers (CRN) design, with three changes:

- **One dose convention for every site**, the ban-free unit `n[l,p] = ||h_twin[l,p]|| x r_Q(l)`.
- **Fresh random directions.** One direction and one token-uniform stream per CRN slot, shared by every arm, so
  every site contrast is an exact paired flip.
- **A pre-registered decision rule** for the site claim (S-a).

Around the S-a test it also runs:

- the matched-displacement test **S-b**;
- the generated-token site **S-c**;
- the request's top-five prohibition as a plan-site push, **S-d**;
- where label changes start, **F1**;
- whether the twin's teacher-forced margin explains the temperature null, **F2**;
- a novelty audit.

Setup:

- **Model.** Qwen3-8B (rev `b968826d`), thinking off, T = 1.0, on one NVIDIA L4.
- **Tasks.** T03 k-th smallest and T10 connected components (all sites, alpha 1/2/4), T2 weighted shortest path
  (alpha 2/4), and T1 grid path (S-d only).
- **Scale.** 3,290 decisive programs, plus 100 positive-control rows, in 1.85 GPU-hours of batch time.
- **Spend.** OpenRouter USD 0.14.
- **Pre-registration.** Rules and predictions were hash-committed before the first decisive sample
  (`commitments.log`, `predictions/s_commit.json`). No decisive row predates commit #1 (21:00:17Z; first decisive row
  21:00:41Z).

## Results

**Bottom line.**

- **The site claim survives the change of engine (S-a PASS, robust to selection).**
  - **Effect.** At its best gated dose (alpha 4, pass rate >= 0.8 x twin), noise on the task-specification states at
    blocks 12-23 (S0) makes the model write a different correct algorithm on 42% of T03 slots and 28% of T10 slots.
  - **Comparators.** The same random displacement on the read position (S1), on the condition sentence (S2) or on
    the task spec at blocks 24-35 (S5) does this on 0-2% of slots, at the same alpha and on the same CRN slots.
  - **Paired flips.** T03: 21:0, 21:1 and 21:1 against S1, S2 and S5. T10: 14:0 against each. Holm p <= 3.7e-4,
    and <= 0.0022 after a x6 selection penalty.
  - **N 30 sensitivity.** On the pre-registered slots alone (k 0-5, without the outcome-blind top-up to N 50), S-a
    still passes but is not robust to selection: T10 contrasts are 7:0, Holm p 0.047.
  - **Interpretation.** Site specificity is a property of the model, not of the FP8 engine.
- **Matched downstream displacement does not explain it (S-b PASS).**
  - **Design.** Rows are stratified by task x decile of the realised displacement at the read position (block 35).
  - **Main result.** A task-spec site (S0 or S4) is far more likely to move the algorithm than S5, S1, S1E or S2:
    Mantel-Haenszel **OR 22.5 [10.1, 49.7]**, n = 2,100.
  - **Each site alone.** S0 alone: 4.8 [3.1, 7.5]. S4 alone: 3.2 [2.0, 5.2].
  - **Placebo.** With the site indicator shuffled within task, the CI excludes 1 in 2/200 shuffles.
  - **Logistic transmission model.** Relative to S0 at the same displacement: S4 +0.20 [-0.22, 0.71] (no
    difference), S5 -2.1, S2 -1.9, S1E -4.1 and S1 -5.2.
- **Blocks 0-11 are as good as 12-23 once the dose is matched (prediction i missed, dose axis resolves it).**
  - **At equal alpha, S4 is weaker:** 0.26 vs 0.42 on T03 and 0.14 vs 0.28 on T10, at alpha 4. So prediction (i),
    S4 >= S0, misses as committed.
  - **But the unit is not equal.** The ban-free unit is a much smaller fraction of the residual early on: r_Q is
    0.010-0.057 at blocks 0-11, against 0.070-0.115 at blocks 12-23. S4's mean unit/||h|| is 0.040, against S0's
    0.107.
  - **On a common axis of realised ||d||/||h||** (`results/dose_axis.json`, fig 7; interpolated within S4's
    observed range, which the alpha-8 extension extends to 0.36):
    - T03: S4 reaches 0.16 and 0.33 at S0's alpha-1 and alpha-2 residual fractions, against 0.17 and 0.29 for S0.
    - T10: S4 reaches 0.09 and 0.28, against 0.01 and 0.05 for S0.
  - **Alpha 8.** S4 moves T03 0.30 (pass 0.77) and T10 0.33 (pass 1.00).
  - **Conclusion.** "Blocks 12-23 specifically" is not supported. "The task-specification states, early to middle"
    is.
- **The landings are the base model's runner-ups (prediction ii: strong per event, not in every cell).**
  - **T03.** 241 of 286 correct off-default programs are quickselect; 10 of 12 moving cells are modal quickselect.
  - **T10.** 35 of 51 are DFS; 2 of 3 cells.
  - **T2.** 14 of 14 are Bellman-Ford/SPFA.
  - All three are far above the chance rate 1/(K-1) (binomial p <= 2.8e-7).
- **Noise on generated tokens moves T03 only (S-c: PASS on T03; prediction iii, T10, missed).**
  - **T03.** S3 at alpha 2: 6:0 against the twin (p 0.016), excess 0.20, pass 0.97.
  - **T10.** Excess 0.10 with p 0.12 at alpha 2; alpha 4 breaks the code (pass 0.30).
  - **T2.** Not significant.
- **Label changes start at the opening of the code body (F1 PASS, but weakly diagnostic).**
  - **Main result.** 219 of 221 label-changing CRN pairs first diverge within 32 code tokens of the fence line
    (0.99 [0.97, 1.00]).
  - **The control is also early.** Label-preserving pairs that change text diverge early too (0.82). They diverge at
    the same median position: token 7 for both. Label-changing pairs are earlier only in distribution
    (Mann-Whitney p 4.9e-12).
  - **Reading.** Most textual changes begin at the first tokens. Early divergence is necessary for a label change,
    not specific to one.
- **The twin's margin explains the temperature null at sequence level, but only borderline at the fork token
  (F2; prediction v hit as committed).**
  - **Sequence level.** The teacher-forced log-probability gap between the default's and the runner-up's opening 48
    code tokens is m = **12.8** (T2), **8.6** (T03) and **7.3** (T1) nats. All exceed the 5.70-nat bound
    (exp(-m/1.3) < 1/80), with scoring SD <= 0.1.
  - **Thinking on.** On T2 the margin is 43.5 nats (4 of 5 traces completed).
  - **Fork token.** Measured at the first token where the two programs diverge, which scales exactly as 1/T, the
    margin is **5.25 (T2), 5.49 (T03) and 5.25 (T1)**, just under the bound. At T 1.3 this leaves about 1.5-1.8% per
    draw for the alternative at that one token.
  - **Other sensitivities.** Per-token normalisation collapses T03 (m_tok 1.04, because the default `sorted(nums)[k-1]`
    is about 12 tokens long). Against all alternatives, T1 falls to 2.23.
  - **Reading.** The null is explained by the sequence-level margin. At the decision token it is close to the bound.
- **The top-five prohibition at the plan site (S-d, descriptive).**
  - **T03 top-5** (ban all but median_of_medians). The push never reaches the survivor (avoidance 0.00 at alpha
    1/2/4, prediction vi hit). Instead it converts the twin's full sort into **quickselect, the banned runner-up, on
    49 of 49** correct programs at alpha 1.
  - **T10 all-but-one.** The push changes nothing (union-find on 150 of 150), although random noise at the same norm
    reaches DFS/BFS on 14 of 48 at alpha 4.
  - **T03 top-3** (an added variant with 3 survivors). The push escapes the banned set:
    - avoidance 0.38 at alpha 2 and 0.88 at alpha 4, against 0.00/0.02 for the paired random control (19:0 and 43:0,
      p <= 3.8e-6);
    - it lands on a dictionary counting sort that the labeller calls 'other'; the audit classes it as a counting-sort
      variant, a survivor.
  - **T1 iteration-4 u_top5.** The push escapes at alpha 4 (avoidance 0.82 vs 0.11; 13:1, p 0.0018), at a pass cost
    (17 of 50 correct). It lands on unit-weight Dijkstra, a survivor of the extended catalogue; at alpha 1-2 it stays
    on BFS.
  - **Edge or opposite?** Where it is computable (T03 top-3, T1 extended), the landings sit on the survivor
    farthest from the banned set at block 18 (p_opp 1e-21 and 1.6e-10), but at block 23 they are indistinguishable
    from a random survivor (p 0.15-0.65). The centroid-difference push is also dominated by that farthest survivor.
    So the geometry does not separate "edge" from "opposite".
- **No new algorithm.**
  - **Pool.** 63 correct 'other' programs (61 unique). All of them are one idea: a frequency table walked over the
    sorted distinct keys.
  - **Verdicts.** Judges and the manual pass agree that this is a counting-sort variant or a labeller miss. Novel:
    0 of 3,102 correct programs (rule-of-three bound 0.10%).
- **Engine.**
  - **Positive control (U8).** Replaying exp25's bf16 cell T03 rand_9002 gives the identical composition (29
    size-k heap, 12 quickselect, 9 full sort). Per-slot label agreement is 1.00 and 96% of the programs are
    byte-identical.
  - **Twins.** Label agreement with earlier bf16 twins is 0.98-1.00.
  - **Against iteration-4 FP8.** FP8 moved T03/T10 already at alpha 1-2 (S0 0.33/0.30 at alpha 1). It broke them at
    alpha 4 (pass 0.67/0.23). bf16 moves later and keeps the pass rate (0.88/0.96 at alpha 4).
  - **What replicates.** The site ordering (S0 >> S1, S2, S5) replicates across precision. The dose-response does
    not.

### Prediction scorecard (committed in `predictions/s_commit.json` before the first decisive sample)

| Prediction | Outcome |
|---|---|
| S-a: the better of S0/S4 beats S1, S2 and S5 by >= 0.15 on T03 and T10 (Holm over 6) | **PASS, robust to selection** (S0 alpha 4; diffs 0.40-0.42 on T03 and 0.28 on T10) |
| (i) S4 >= S0 at their best gated dose, both above S1/S2/S5 | **Missed** at equal alpha (S4 0.26 vs S0 0.42 on T03; 0.14 vs 0.28 on T10). Both are above the comparators. On the residual-fraction axis S4 >= S0 (dose axis, descriptive) |
| (ii) every moving cell lands modally on the base runner-up | **Missed as stated** (T03 10/12 cells, T10 2/3, T2 1/1). Per event: 241/286, 35/51, 14/14, all far above chance |
| (iii) S3 moves T10 >= 0.10 above the twin at a gated dose | **Missed** (excess 0.10 at alpha 2 but p 0.12). S-c passes on T03 |
| (iv) F1 share >= 0.80 | **Hit** (0.99), but the label-preserving control is also 0.82 |
| (v) m > 5.70 nats on T2, T03, T1 | **Hit** (12.8, 8.6, 7.3); at the fork token 5.25-5.49 (just under) |
| (vi) T03 top-5 avoidance < 0.5 at alpha <= 2; T1 push stays on BFS | **Hit** for T03 (0.00). For T1, hit at alpha 1-2; at alpha 4 the push leaves BFS for unit-weight Dijkstra |

### Per-site cells (correct off-default share of N with Wilson 95% CI / pass rate / invalid rate / byte-identical rate vs the twin)

S0/S4/S1/S2/S5 on T03 and T10 are N = 50 (k 0-9, outcome-blind top-up included). S3 and S1E are N = 30, and so is
every T2 cell.

**T03** (twin N = 50: pass 1.00, correct off-default 0.00, composition {'full_sort': 50})

| Site | α 1: share [95% CI] / pass / invalid / id | α 2: share [95% CI] / pass / invalid / id | α 4: share [95% CI] / pass / invalid / id |
|---|---|---|---|
| S0 | 0.14 [0.07, 0.26] / 0.98 / 0.00 / 0.76 | 0.34 [0.22, 0.48] / 0.96 / 0.00 / 0.52 | 0.42 [0.29, 0.56] / 0.88 / 0.00 / 0.22 |
| S4 | 0.02 [0.00, 0.10] / 1.00 / 0.00 / 0.86 | 0.08 [0.03, 0.19] / 1.00 / 0.00 / 0.76 | 0.26 [0.16, 0.40] / 1.00 / 0.00 / 0.58 |
| S5 | 0.02 [0.00, 0.10] / 1.00 / 0.00 / 0.94 | 0.02 [0.00, 0.10] / 1.00 / 0.00 / 0.90 | 0.02 [0.00, 0.10] / 1.00 / 0.00 / 0.88 |
| S1 | 0.00 [0.00, 0.07] / 1.00 / 0.00 / 0.98 | 0.00 [0.00, 0.07] / 1.00 / 0.00 / 0.98 | 0.00 [0.00, 0.07] / 1.00 / 0.00 / 0.94 |
| S2 | 0.00 [0.00, 0.07] / 1.00 / 0.00 / 0.94 | 0.00 [0.00, 0.07] / 1.00 / 0.00 / 0.94 | 0.02 [0.00, 0.10] / 1.00 / 0.00 / 0.86 |
| S3 | 0.10 [0.03, 0.26] / 1.00 / 0.00 / 0.83 | 0.20 [0.10, 0.37] / 0.97 / 0.00 / 0.43 | 0.13 [0.05, 0.30] / 0.50 / 0.20 / 0.00 |
| S1E | 0.07 [0.02, 0.21] / 0.93 / 0.07 / 0.00 | 0.03 [0.01, 0.17] / 0.80 / 0.17 / 0.00 | 0.00 [0.00, 0.11] / 0.97 / 0.03 / 0.00 |

S4 at α 8 (outcome-blind extension): share 0.30, pass 0.77, invalid 0.00, residual fraction 0.354.

**T10** (twin N = 50: pass 1.00, correct off-default 0.00, composition {'union_find': 50})

| Site | α 1: share [95% CI] / pass / invalid / id | α 2: share [95% CI] / pass / invalid / id | α 4: share [95% CI] / pass / invalid / id |
|---|---|---|---|
| S0 | 0.00 [0.00, 0.07] / 1.00 / 0.00 / 0.42 | 0.06 [0.02, 0.16] / 1.00 / 0.00 / 0.28 | 0.28 [0.17, 0.42] / 0.96 / 0.00 / 0.10 |
| S4 | 0.00 [0.00, 0.07] / 1.00 / 0.00 / 0.60 | 0.04 [0.01, 0.13] / 1.00 / 0.00 / 0.50 | 0.14 [0.07, 0.26] / 1.00 / 0.00 / 0.30 |
| S5 | 0.00 [0.00, 0.07] / 1.00 / 0.00 / 0.84 | 0.00 [0.00, 0.07] / 1.00 / 0.00 / 0.80 | 0.00 [0.00, 0.07] / 1.00 / 0.00 / 0.56 |
| S1 | 0.00 [0.00, 0.07] / 1.00 / 0.00 / 0.76 | 0.00 [0.00, 0.07] / 1.00 / 0.00 / 0.72 | 0.00 [0.00, 0.07] / 1.00 / 0.00 / 0.58 |
| S2 | 0.00 [0.00, 0.07] / 1.00 / 0.00 / 0.92 | 0.00 [0.00, 0.07] / 1.00 / 0.00 / 0.78 | 0.00 [0.00, 0.07] / 1.00 / 0.00 / 0.72 |
| S3 | 0.03 [0.01, 0.17] / 1.00 / 0.00 / 0.27 | 0.10 [0.03, 0.26] / 0.93 / 0.00 / 0.07 | 0.13 [0.05, 0.30] / 0.30 / 0.20 / 0.00 |
| S1E | 0.10 [0.03, 0.26] / 0.83 / 0.17 / 0.00 | 0.00 [0.00, 0.11] / 0.83 / 0.17 / 0.00 | 0.13 [0.05, 0.30] / 0.97 / 0.03 / 0.00 |

S4 at α 8 (outcome-blind extension): share 0.33, pass 1.00, invalid 0.00, residual fraction 0.354.

**T2** (twin N = 50: pass 0.98, correct off-default 0.00, composition {'dijkstra': 49})

| Site | α 2: share [95% CI] / pass / invalid / id | α 4: share [95% CI] / pass / invalid / id |
|---|---|---|
| S0 | 0.03 [0.01, 0.17] / 0.87 / 0.00 / 0.17 | 0.23 [0.12, 0.41] / 0.80 / 0.00 / 0.00 |
| S4 | 0.00 [0.00, 0.11] / 1.00 / 0.00 / 0.53 | 0.03 [0.01, 0.17] / 0.90 / 0.00 / 0.20 |
| S5 | 0.00 [0.00, 0.11] / 0.97 / 0.00 / 0.87 | 0.03 [0.01, 0.17] / 0.97 / 0.00 / 0.63 |
| S1 | 0.00 [0.00, 0.11] / 0.97 / 0.00 / 0.63 | 0.00 [0.00, 0.11] / 0.97 / 0.00 / 0.47 |
| S2 | 0.00 [0.00, 0.11] / 1.00 / 0.00 / 0.87 | 0.00 [0.00, 0.11] / 1.00 / 0.00 / 0.77 |
| S3 | 0.13 [0.05, 0.30] / 0.80 / 0.03 / 0.00 | 0.00 [0.00, 0.11] / 0.07 / 0.83 / 0.00 |
| S1E | 0.00 [0.00, 0.11] / 0.97 / 0.03 / 0.00 | 0.00 [0.00, 0.11] / 0.90 / 0.10 / 0.00 |

**S-a (committed rule).** Verdict: **PASS (robust to selection)**.

| Task | selected cell (share, pass) | comparator | b:c | exact p | Holm p | selection-aware Holm p | diff (shared slots) |
|---|---|---|---|---|---|---|---|
| T03 | S0 α 4 (0.42, 0.88) | S1 | 21:0 | 9.5e-07 | 5.7e-06 | 3.4e-05 | 0.42 |
| T03 | S0 α 4 (0.42, 0.88) | S2 | 21:1 | 1.1e-05 | 5.5e-05 | 3.3e-04 | 0.40 |
| T03 | S0 α 4 (0.42, 0.88) | S5 | 21:1 | 1.1e-05 | 5.5e-05 | 3.3e-04 | 0.40 |
| T10 | S0 α 4 (0.28, 0.96) | S1 | 14:0 | 1.2e-04 | 3.7e-04 | 0.0022 | 0.28 |
| T10 | S0 α 4 (0.28, 0.96) | S2 | 14:0 | 1.2e-04 | 3.7e-04 | 0.0022 | 0.28 |
| T10 | S0 α 4 (0.28, 0.96) | S5 | 14:0 | 1.2e-04 | 3.7e-04 | 0.0022 | 0.28 |

Every b:c beside the selected one (S0/S4 at each α against S1/S2/S5 at the same α):

| Task | contrast | b:c (p) |
|---|---|---|
| T03 | S0_a1_vs_S1 | 7:0 (0.016) |
| T03 | S0_a1_vs_S2 | 7:0 (0.016) |
| T03 | S0_a1_vs_S5 | 6:0 (0.031) |
| T03 | S4_a1_vs_S1 | 1:0 (1) |
| T03 | S4_a1_vs_S2 | 1:0 (1) |
| T03 | S4_a1_vs_S5 | 0:0 (1) |
| T03 | S0_a2_vs_S1 | 17:0 (1.5e-05) |
| T03 | S0_a2_vs_S2 | 17:0 (1.5e-05) |
| T03 | S0_a2_vs_S5 | 16:0 (3.1e-05) |
| T03 | S4_a2_vs_S1 | 4:0 (0.12) |
| T03 | S4_a2_vs_S2 | 4:0 (0.12) |
| T03 | S4_a2_vs_S5 | 3:0 (0.25) |
| T03 | S0_a4_vs_S1 | 21:0 (9.5e-07) |
| T03 | S0_a4_vs_S2 | 21:1 (1.1e-05) |
| T03 | S0_a4_vs_S5 | 21:1 (1.1e-05) |
| T03 | S4_a4_vs_S1 | 13:0 (2.4e-04) |
| T03 | S4_a4_vs_S2 | 12:0 (4.9e-04) |
| T03 | S4_a4_vs_S5 | 13:1 (0.0018) |
| T10 | S0_a1_vs_S1 | 0:0 (1) |
| T10 | S0_a1_vs_S2 | 0:0 (1) |
| T10 | S0_a1_vs_S5 | 0:0 (1) |
| T10 | S4_a1_vs_S1 | 0:0 (1) |
| T10 | S4_a1_vs_S2 | 0:0 (1) |
| T10 | S4_a1_vs_S5 | 0:0 (1) |
| T10 | S0_a2_vs_S1 | 3:0 (0.25) |
| T10 | S0_a2_vs_S2 | 3:0 (0.25) |
| T10 | S0_a2_vs_S5 | 3:0 (0.25) |
| T10 | S4_a2_vs_S1 | 2:0 (0.5) |
| T10 | S4_a2_vs_S2 | 2:0 (0.5) |
| T10 | S4_a2_vs_S5 | 2:0 (0.5) |
| T10 | S0_a4_vs_S1 | 14:0 (1.2e-04) |
| T10 | S0_a4_vs_S2 | 14:0 (1.2e-04) |
| T10 | S0_a4_vs_S5 | 14:0 (1.2e-04) |
| T10 | S4_a4_vs_S1 | 7:0 (0.016) |
| T10 | S4_a4_vs_S2 | 7:0 (0.016) |
| T10 | S4_a4_vs_S5 | 7:0 (0.016) |

Prediction (i) (S4 >= S0 at best gated dose, both above S1/S2/S5): T03: S0 {'alpha': 4.0, 'share': 0.42}, S4 {'alpha': 4.0, 'share': 0.26}, max comparator 0.02 -> miss; T10: S0 {'alpha': 4.0, 'share': 0.28}, S4 {'alpha': 4.0, 'share': 0.14}, max comparator 0.00 -> miss

**S-b.** Mantel-Haenszel OR (task-spec site S0/S4 vs S5/S1/S1E/S2, strata = task x decile of realised displacement at R, block 35): **22.45 [10.14, 49.72]** over 2100 prefill rows; PASS = True. S0 only: 4.78 [3.06, 7.45]; S4 only: 3.18 [1.97, 5.16]. Placebo (TS shuffled within task, 200x): CI excludes 1 in 0.01 of shuffles, median OR 1.00.
Logistic transmission model (L2, y ~ log disp_R35 + site + template + task): log_disp_R35 1.33 [1.07, 1.61], site_S4_vs_S0 0.20 [-0.22, 0.71], site_S5_vs_S0 -2.06 [-3.39, -1.39], site_S1_vs_S0 -5.19 [-5.77, -5.03], site_S1E_vs_S0 -4.08 [-5.16, -3.24], site_S2_vs_S0 -1.87 [-3.49, -0.74].

**S-c (S3, generated tokens 1-32, vs the twin on shared slots; one-sided exact McNemar).**

| Task | α | b:c | p | excess | S3 pass | gated | hit | S3 KL/step |
|---|---|---|---|---|---|---|---|---|
| T03 | 1 | 3:0 | 0.12 | 0.10 | 1.00 | True | False | 0.089 |
| T03 | 2 | 6:0 | 0.016 | 0.20 | 0.97 | True | True | 0.308 |
| T03 | 4 | 4:0 | 0.062 | 0.13 | 0.50 | False | False | 2.479 |
| T10 | 1 | 1:0 | 0.5 | 0.03 | 1.00 | True | False | 0.041 |
| T10 | 2 | 3:0 | 0.12 | 0.10 | 0.93 | True | False | 0.289 |
| T10 | 4 | 4:0 | 0.062 | 0.13 | 0.30 | False | False | 2.776 |
| T2 | 2 | 4:0 | 0.062 | 0.13 | 0.80 | True | False | 0.735 |
| T2 | 4 | 0:0 | 1 | 0.00 | 0.07 | False | False | 4.225 |

**Landings (prediction ii).** T03: 10/12 moving cells land modally on quickselect (per event 241/286, binomial p vs chance 1/(K-1) = 1.2e-120); T10: 2/3 moving cells land modally on dfs (per event 35/51, binomial p vs chance 1/(K-1) = 2.8e-07); T2: 1/1 moving cells land modally on bf_spfa (per event 14/14, binomial p vs chance 1/(K-1) = 3.7e-09)

**F1.** Label-changing CRN pairs: 221; first divergence < 32 code tokens after the fence line in 219 (**0.99** [0.97, 1.00]; threshold 0.80; PASS = True); 13 diverge before the fence line. Control (label-preserving, text-changing pairs): n 945, early share 0.82; median d 7 (label-changing) vs 7 (label-preserving), Mann-Whitney p 4.9e-12. Placebo re-pairing across slots: early share 0.99.
By site: S0 100/100 (1.00); S1E 13/13 (1.00); S2 1/3 (0.33); S3 46/46 (1.00); S4 55/55 (1.00); S5 4/4 (1.00)

**F2 (twin margin m, nats; LP48 = log-prob of the first 48 code tokens).**

| Task | default | runner-up | m | 2 x scoring SD | m_lme | m_tok | m_fork | m_all | verdict |
|---|---|---|---|---|---|---|---|---|---|
| R1 | greedy_end | dag_longest_path | 41.47 | 0.20 | 41.89 | 41.47 | 0.03 | 41.47 | EXPLAINS NULL (m > 5.70) |
| R2 | dfs_parent | union_find | 11.32 | 0.10 | 12.89 | 11.32 | 8.50 | 11.32 | EXPLAINS NULL (m > 5.70) |
| R3 | kahn | None | n/a | n/a | n/a | n/a | n/a | n/a | UNDEFINED (< 3 programs for the default or the runner-up) |
| R6 | binary_search | None | n/a | n/a | n/a | n/a | n/a | n/a | UNDEFINED (< 3 programs for the default or the runner-up) |
| T03 | full_sort | quickselect | 8.56 | 0.16 | 6.08 | 1.04 | 5.49 | 8.56 | EXPLAINS NULL (m > 5.70) |
| T04 | naive | None | n/a | n/a | n/a | n/a | n/a | n/a | UNDEFINED (< 3 programs for the default or the runner-up) |
| T05 | hash_map | None | n/a | n/a | n/a | n/a | n/a | n/a | UNDEFINED (< 3 programs for the default or the runner-up) |
| T06 | hash_set | None | n/a | n/a | n/a | n/a | n/a | n/a | UNDEFINED (< 3 programs for the default or the runner-up) |
| T08 | iteration | memo_recursion | n/a | n/a | n/a | n/a | n/a | n/a | UNDEFINED (< 3 programs for the default or the runner-up) |
| T1 | bfs | dfs | 7.33 | 0.07 | 5.90 | 7.33 | 5.25 | 2.23 | EXPLAINS NULL (m > 5.70) |
| T10 | union_find | dfs | 22.06 | 0.10 | 19.80 | 22.06 | 18.25 | 22.05 | EXPLAINS NULL (m > 5.70) |
| T11 | quadratic_dp | patience_bisect | 19.35 | 0.15 | 14.68 | 19.35 | 15.50 | 19.35 | EXPLAINS NULL (m > 5.70) |
| T13 | sort_sweep | union_find | 53.91 | 0.13 | 47.97 | 53.91 | 7.50 | 53.91 | EXPLAINS NULL (m > 5.70) |
| T14 | sort_by_count | heap | 29.63 | 0.13 | 31.78 | 29.06 | 17.25 | 29.63 | EXPLAINS NULL (m > 5.70) |
| T2 | dijkstra | bf_spfa | 12.77 | 0.09 | 6.07 | 12.77 | 5.25 | 12.74 | EXPLAINS NULL (m > 5.70) |

Thinking-on T2: m_think = 43.52 over 4 of 5 completed traces (EXPLAINS NULL (m > 5.70)).
M screen (Spearman of m with the escape fraction E, descriptive): E_bf16_exp25: rho -0.25 (p 0.51, n 9); E_fp8_exp22: rho -0.46 (p 0.22, n 9)

**S-d (top-five prohibition as a plan-site push).**

| Setting | α | push: n correct / avoidance [CI] / on survivor | random control (S0): avoidance | twin avoidance | push vs RC b:c (p) | t (block 18) |
|---|---|---|---|---|---|---|
| T03|TOP5 | 1 | 49 / 0.00 [0.00, 0.07] / {'S': 0} | 0.00 | 0.00 | 0:0 (1) | 3.46 |
| T03|TOP5 | 2 | 45 / 0.00 [0.00, 0.08] / {'S': 0} | 0.00 | 0.00 | 0:0 (1) | 6.93 |
| T03|TOP5 | 4 | 49 / 0.00 [0.00, 0.07] / {'S': 0} | 0.00 | 0.00 | 0:0 (1) | 13.84 |
| T03|TOP3 | 1 | 49 / 0.00 [0.00, 0.07] / {'S': 0} | 0.00 | 0.00 | 0:0 (1) | -82.77 |
| T03|TOP3 | 2 | 50 / 0.38 [0.26, 0.52] / {'S': 2} | 0.00 | 0.00 | 19:0 (3.8e-06) | -165.76 |
| T03|TOP3 | 4 | 50 / 0.88 [0.76, 0.94] / {'S': 0} | 0.02 | 0.00 | 43:0 (2.3e-13) | -331.62 |
| T10|TOP5 | 1 | 50 / 0.00 [0.00, 0.07] / {'S': 0} | 0.00 | 0.00 | 0:0 (1) | 18.50 |
| T10|TOP5 | 2 | 50 / 0.00 [0.00, 0.07] / {'S': 0} | 0.00 | 0.00 | 0:0 (1) | 36.99 |
| T10|TOP5 | 4 | 50 / 0.00 [0.00, 0.07] / {'S': 0} | 0.00 | 0.00 | 0:0 (1) | 73.99 |
| T1|TOP5 | 1 | 31 / 0.00 [0.00, 0.11] / {'K7': 0, 'ext': 0} | 0.00 | 0.00 | 0:0 (1) | 3.24 |
| T1|TOP5 | 2 | 21 / 0.24 [0.11, 0.45] / {'K7': 0, 'ext': 5} | 0.03 | 0.00 | 5:1 (0.22) | 6.48 |
| T1|TOP5 | 4 | 17 / 0.82 [0.59, 0.94] / {'K7': 0, 'ext': 14} | 0.11 | 0.00 | 13:1 (0.0018) | 12.99 |

Geometry (forced named + masked prompts, PCA-50, k-NN geodesics, 2-D metric MDS):

| Setting | block | k | MDS stress-1 | survivor -> nearest banned geodesic | separability min |
|---|---|---|---|---|---|
| T03|TOP5 | block18 | 15 | 0.064 | {'median_of_medians': 0.67} | 0.00 |
| T03|TOP5 | block23 | 10 | 0.171 | {'median_of_medians': 0.3} | 0.02 |
| T03|TOP3 | block18 | 10 | 0.093 | {'counting_sort': 0.91, 'heapify_pop': 0.24, 'median_of_medians': 0.67} | 0.00 |
| T03|TOP3 | block23 | 10 | 0.158 | {'counting_sort': 0.25, 'heapify_pop': 0.17, 'median_of_medians': 0.3} | 0.02 |
| T10|TOP5 | block18 | 15 | 0.058 | {'label_propagation': 0.5} | 0.92 |
| T10|TOP5 | block23 | 10 | 0.119 | {'label_propagation': 0.22} | 0.77 |
| T1|TOP5 | block18 | 10 | 0.170 | {'biastar': 0.13, 'bibfs': 0.14, 'dijkstra_unit': 0.28, 'idastar': 0.13, 'jps': 0.16} | 0.73 |
| T1|TOP5 | block23 | 10 | 0.159 | {'biastar': 0.15, 'bibfs': 0.14, 'dijkstra_unit': 0.15, 'idastar': 0.14, 'jps': 0.18} | 0.80 |

Edge tests (|S| >= 2 only):

- T03|TOP3 α 1 edge_test_S block18: not computable (no survivor program)
- T03|TOP3 α 1 edge_test_S block23: not computable (no survivor program)
- T03|TOP3 α 2 edge_test_S block18: n 2, D_obs 0.57, p_edge 0.56, p_opp 0.67 (exact enumeration)
- T03|TOP3 α 2 edge_test_S block23: n 2, D_obs 0.21, p_edge 0.33, p_opp 0.89 (exact enumeration)
- T03|TOP3 α 4 edge_test_S block18: not computable (no survivor program)
- T03|TOP3 α 4 edge_test_S block23: not computable (no survivor program)
- T1|TOP5 α 1 edge_test_K7 block18: not computable (no survivor program)
- T1|TOP5 α 1 edge_test_K7 block23: not computable (no survivor program)
- T1|TOP5 α 1 edge_test_ext block18: not computable (no survivor program)
- T1|TOP5 α 1 edge_test_ext block23: not computable (no survivor program)
- T1|TOP5 α 2 edge_test_K7 block18: not computable (no survivor program)
- T1|TOP5 α 2 edge_test_K7 block23: not computable (no survivor program)
- T1|TOP5 α 2 edge_test_ext block18: n 5, D_obs 0.28, p_edge 1, p_opp 3.2e-04 (exact enumeration)
- T1|TOP5 α 2 edge_test_ext block23: n 5, D_obs 0.15, p_edge 0.39, p_opp 0.62 (exact enumeration)
- T1|TOP5 α 4 edge_test_K7 block18: not computable (no survivor program)
- T1|TOP5 α 4 edge_test_K7 block23: not computable (no survivor program)
- T1|TOP5 α 4 edge_test_ext block18: n 14, D_obs 0.28, p_edge 1, p_opp 1.6e-10 (exact enumeration)
- T1|TOP5 α 4 edge_test_ext block23: n 14, D_obs 0.15, p_edge 0.35, p_opp 0.65 (exact enumeration)

**Engine checks.**

- U8_T03: composition {'size_k_heap': 29, 'full_sort': 9, 'quickselect': 12} vs exp25 {'size_k_heap': 29, 'full_sort': 9, 'quickselect': 12}; off-default correct 40 (record 41), Fisher p 1, JS 0.000; per-slot label agreement 1.00, identical code 0.96; PASS = True.
- U8_T2: composition {'dijkstra': 30, 'bf_spfa': 20} vs exp25 {'dijkstra': 31, 'bf_spfa': 19}; off-default correct 17 (record 19), Fisher p 0.84, JS 0.000; per-slot label agreement 0.98, identical code 0.66; PASS = True.
- U9_T03_exp27_TWIN_hf_bf16: n 50, label agreement 0.98, identical code 0.90.
- U9_T03_exp25_ECTWIN_bf16: n 50, label agreement 1.00, identical code 0.92.
- U9_T10_exp27_TWIN_hf_bf16: n 50, label agreement 1.00, identical code 0.80.
- U9_T2_exp27_TWIN_hf_bf16: n 50, label agreement 1.00, identical code 0.88.
- U9_T2_exp25_ECTWIN_bf16: n 50, label agreement 1.00, identical code 0.90.
- U9_T1_exp27_TWIN_hf_bf16: n 50, label agreement 1.00, identical code 0.60.

### Iteration-4 FP8 vs this bf16 run (descriptive; different engine and different unit, no test crosses them)

Each cell shows correct off-default share / pass rate. exp20 used FP8 W8A8 and the iteration-4 FP8 ban unit. This
artifact uses W16A16 and the bf16 ban-free unit. On T03 at blocks 12-23 the ban-free unit is 0.81x the ban unit
(ratio of means).

| Task | Site | FP8 α 1 | bf16 α 1 | FP8 α 2 | bf16 α 2 | FP8 α 4 | bf16 α 4 |
|---|---|---|---|---|---|---|---|
| T03 | S0 | 0.33 / 1.00 | 0.14 / 0.98 | 0.40 / 0.93 | 0.34 / 0.96 | 0.20 / 0.67 | 0.42 / 0.88 |
| T03 | S4 | 0.07 / 1.00 | 0.02 / 1.00 | 0.13 / 1.00 | 0.08 / 1.00 | 0.43 / 1.00 | 0.26 / 1.00 |
| T03 | S3 | 0.10 / 1.00 | 0.10 / 1.00 | 0.47 / 0.90 | 0.20 / 0.97 | 0.03 / 0.17 | 0.13 / 0.50 |
| T03 | S1, S2, S5 | 0.00 | 0.00-0.02 | 0.00 | 0.00-0.02 | 0.00 | 0.00-0.02 |
| T10 | S0 | 0.30 / 1.00 | 0.00 / 1.00 | 0.57 / 0.97 | 0.06 / 1.00 | 0.13 / 0.23 | 0.28 / 0.96 |
| T10 | S4 | 0.10 / 1.00 | 0.00 / 1.00 | 0.20 / 1.00 | 0.04 / 1.00 | 0.43 / 0.90 | 0.14 / 1.00 |
| T10 | S1, S2 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| T10 | S5 | 0.00 | 0.00 | 0.10 | 0.00 | 0.07 | 0.00 |
| T2 | S0 | – | – | 0.20 / 0.90 | 0.03 / 0.87 | 0.00 / 0.03 | 0.23 / 0.80 |

What replicates across precision: the task-spec sites move the algorithm and S1, S2 and S5 do not. What does not:
the dose at which movement starts and the dose at which the code breaks. FP8 is far more sensitive per unit of
nominal dose, so dose-response numbers from iteration 4 should not be carried into bf16.

### Failure mode per site (exp20's frozen classes; `results/failure_modes.json`)

| Site | T03 | T10 | T2 |
|---|---|---|---|
| S0 | moves | moves | moves |
| S4 | moves | moves | no movement |
| S5 | no movement | no movement | no movement |
| S1 | no movement | no movement | no movement |
| S2 | no movement | no movement | no movement |
| S3 | moves | weak movement | weak movement |
| S1E | no movement | weak movement | no movement |

### Novelty audit (`results/novelty_audit.json`, `audit/`)

- **Pool.** 63 correct programs carry the label 'other' (61 unique): 44 from T03 TOP3 alpha 4, 17 from TOP3 alpha 2,
  1 from S3 and 1 from S4 at alpha 8. All 61 pass 3 stress tests at the spec's maximum size.
- **Judge controls.** All three judges score 6 of 6 on the controls.
- **Judges.** google/gemini-2.5-flash-lite and openai/gpt-4.1-mini are the judges, with deepseek-chat-v3.1 as the
  tie-break. Resolved classes: 30 CATALOGUE VARIANT, 31 LABELLER MISS. Both judges name counting sort as the closest
  known algorithm.
- **Manual pass.** The executor read each program beside its three nearest known solutions (xlcost k-th-smallest
  programs, index rebuilt from art_j3Rm_lr2nzR6; 472 rows exactly as exp18, plus 42 T05). All 61 are CATALOGUE
  VARIANT: counting sort with a sorted dictionary of counts.
- **Claim.** 0 novel algorithms among 3,102 correct programs (rule-of-three 0.10%).
- **Sensitivity.** Relabelling these programs counting_sort (`results/s_d_audit_relabelled.json`) turns the T03
  top-3 push's 'other' landings into survivor landings: 19 of 50 correct at alpha 2 and 44 of 50 at alpha 4.

## Checks

- **CPU tests** (`results/unit_tests_cpu.json`, all 9 pass):
  - the batched edit equals exp20's make_prefill_edits and exp27's make_edits('RAND') exactly (max |diff| 0.0), and
    the along-u error is 6e-6;
  - exact McNemar matches the enumerated binomial and statsmodels;
  - Holm;
  - Mantel-Haenszel OR and RBG CI match statsmodels StratifiedTable to 1e-9;
  - first divergence and code start, including divergence before the fence;
  - geometry: on a half ring the geodesic is 3.13 against a Euclidean 2.00, and MDS stress-1 is 0.0004; the
    connectivity fallback works;
  - the random-survivor null matches its closed form, and exact enumeration matches Monte Carlo within 0.001;
  - the S-a selection rule, including the pass gate, ties and the selection-aware p;
  - S1E's energy matches S0's to 1e-6.
- **GPU tests** (`results/unit_tests_gpu.json`):
  - **U1.** CRN determinism across two batch compositions: T03 True, T10 True.
  - **U2.** Alpha 0 reproduces the twin byte for byte at every site (S0, S4, S5, S1, S2, S1E, and S3 with its
    shadow): True on both tasks.
  - **U5.** The block-35 edit is a no-op: True.
  - **U3.** The mean along-u displacement equals alpha x unit within 0.05% at every site. The worst position reaches
    0.87% (S4) because the edited residual is rounded to bf16 (deviation D_U3_bf16). S3 holds against its shadow
    within 0.04%.
  - **U4** (shadow vs an independent teacher-forced forward). T10 min cos 0.9998. T03 0.69, the same pattern exp20
    saw in FP8 and diagnosed as decode-path numerics.
  - **U6.** Peak 18.6 GiB of 22.0 at B = 16 with 1,024 tokens, and at B = 12 with 1,536 tokens
    (`results/batch_probe.json`).
  - **U7.** No ban prompt in the sampling queue or in any sampled row.
- **Positive control U8 and engine check U9** (`results/engine_checks.json`):
  - T03 reproduces exp25 exactly (Fisher p 1.0, JS 0.000; per-slot agreement 1.00).
  - T2 per-slot agreement is 0.98 (Fisher p 0.84).
  - The twins agree with exp27/exp25's bf16 twins on 0.98-1.00 of slots.
- **Labellers re-checked** (`results/labeller_recheck.json`):
  - bench references pass and self-label (T03 6/6, T10 4/4);
  - gold-set runtime and AST labels are reproduced (T03 28/28 and 28/28, T10 22/22 and 22/22);
  - exp8 suite references: T1 12/12, T2 10/10.
- **Units** (`units/r_Q_all.json`, `results/units_summary.json`).
  - The bf16 r_Q at blocks 12-23 is 0.952 x exp23's, inside the [0.9, 1.1] band, so it is used as frozen.
  - The used r_Q is 0.010 at block 0, 0.057 at block 11, 0.070-0.115 at blocks 12-23 and 0.092-0.104 at blocks
    24-35.
  - exp27 reported a ban-free/ban ratio of 1.39 on T03. This run measures 0.81 (ratio of means) and 1.00 (mean of
    per-position ratios) against exp20's FP8 ban unit. The two are not reconciled; the difference is logged.
- **Inputs** (`inputs/SHA256SUMS`, 572 files; `results/inputs_check.json`). The bench files check against
  `bench/commitment.json`: 146 checked, 0 mismatches.
- **Directions** (`directions/seeds.json`). The namespace ITER6_S2 is new. Its maximum |cos| with every earlier
  direction file, and with exp20's PN4 slot directions, is 0.069.
- **Banned sets** (`predictions/banned_sets.json`; `results/banned_sets_check.json`). The sets were committed from
  earlier twin, base and plan-noise rows. Adding this artifact's twin leaves all three unchanged.
- **Independent re-derivation** (`audit/rederive.py` -> `results/rederive.json`). It is stdlib/numpy code that shares
  nothing with `src/`.
  - 77 cells, every S-a contrast, the S-b OR, S-c, F1 (221/219) and F2's m are recomputed from the raw rows, with
    **0 mismatches**.
  - The placebos fail as required: S-a with site labels shuffled within (task, alpha) passes in 0 of 200 shuffles;
    the MH indicator shuffled within task excludes 1 in 2%; swapping McNemar pair members rejects in 2%.
- **Second re-derivation** (`audit/rederive_extra.py` -> `results/rederive_extra.json`). It is stdlib only and
  shares nothing with `src/` or the first re-derivation. The F2 fork margins (5.25 / 5.49 / 5.25), the S-d paired
  flips (19:0, 43:0, 13:1), T03 top-5's 49/49 quickselect, the 3,290 decisive rows, the 0 novel programs and the
  USD 0.14 spend are recomputed from the raw files with **0 mismatches**. Placebos fail as required: the fork
  margin of default vs default programs is about 0, and pair-swapped S-d McNemar tests reject in 0.4-3.6%.
- **Pre-registration** (`commitments.log`, `results/commitment_audit.json`). There are 6 commits and 0 chain breaks.
  - Commit #1 (rules, cells, sets, units, directions, predictions) is at 21:00:17Z. The first decisive row is at
    21:00:41Z; 0 decisive rows came earlier.
  - Commit #2 (the final analysis code) is at 22:51:37Z, before the analysis ran on the full data.
  - Commit #3 (23:27:52Z) records three bug fixes found on the first full outputs (D_POSTC2_FIXES), commit #4 a
    presentation-only change to fig 5, commit #5 a path scrub of `src/cfg.py` and `src/figures.py` (no computation
    changed), and commit #6 the second re-derivation in the outputs. The fixes touch only
    the S-d survivor count on T1, the m_fork sensitivity and an added push-progress normalisation. S-a, S-b, S-c, F1
    and the primary m are unaffected.
- **Deviations** (`results/deviations.json`, 15 entries):
  - NVIDIA L4 instead of an RTX A4500.
  - B = 16/12 from the memory probe, instead of the plan's starting 8/6.
  - U3's bf16 rounding.
  - U4 on T03.
  - F2 passes run after sampling (so m was computed after commit #1).
  - The banned sets exclude this artifact's own twin.
  - T1 masked prompts use exp8's 6-mode names.
  - U9 is computed post hoc.
  - Push progress t is unstable when the twin is off the B side of the axis, so t' is reported beside it.
  - One input file was copied after commit #1.
  - The geometry code was sped up between commits.
  - The post-commit-2 fixes.
  - The path scrub of two source files.
  - F2 is undefined where the default or runner-up has fewer than 3 forced programs (R3, R6, T04, T05, T06, T08).
    The plan's generation fallback was not run.
- **Not run.** Every planned cell ran, including both outcome-blind extensions, and no time-based drop was needed
  (`results/timing_extrapolation.json`).

## Interpretation and limits

- **Scope.** Qwen3-8B in W16A16 on three memorised LeetCode-style tasks (T03, T10, T2), plus T1 for S-d. N is 30-50
  paired slots per cell.
- **What the site result is.** The claim is site-specific sensitivity to off-distribution isotropic noise. It is not
  evidence for a plan representation. Zhang and Nanda warn that noise corruptions push states out of distribution,
  and every arm here is such a push. What the design guarantees is that the comparison is random push against
  random push, at a matched per-position unit, on the same slots.
- **Dose convention.** Nominal alpha is not a convention-free dose. The ban-free unit is a smaller residual fraction
  at blocks 0-11, which is why S4 trails S0 at equal alpha but matches or beats it at equal realised ||d||/||h||.
  The dose-axis comparison is interpolated, not designed.
- **F1.** Early divergence is near-universal (the control is 0.82), so F1 constrains where label changes start, not
  why.
- **F2.**
  - The margin is length-sensitive. LP48 is a sum over at most 48 tokens, and T03's default program is about 12
    tokens long.
  - The same-seed rows that F2 explains ran in FP8 with top-k 10. Top-k only lowers p_alt, so the bound is
    conservative, but it is a cross-engine comparison.
  - At the fork token the margin is just under the bound.
- **S-d.**
  - Three settings have one survivor, or no movement at all.
  - The two computable edge tests disagree between blocks 18 and 23.
  - The centroid-difference push is dominated by the farthest survivor.
  - The manifold is built from forced prompts. MDS stress-1 is 0.06-0.17 (fair to good) at the chosen k.
- **Field norms this design answers** (mechanistic-interpretability handbook):
  - every arm has a matched random control;
  - effects are reported per sample and per dose, with paired flips, intervals and three to four doses per site;
  - collateral damage (pass and invalid rates) sits beside every share;
  - the claims were pre-registered with a power statement;
  - an independent re-derivation with placebos checks the headlines.

### Figures (`figures/*.pdf` + `.png`)

| Figure | What it shows |
|---|---|
| `fig1_sites_share_pass` | Correct off-default share (Wilson bars) and pass rate by site x alpha, per task; twin and 0.8 x twin gate dashed. |
| `fig2_paired_flips` | S-a paired discordant slots (selected S0 cell vs S1/S2/S5) with Holm p. |
| `fig3_sb_transmission` | Correct off-default share against realised displacement at R (block 35), by site (S-b). |
| `fig4_f1_first_divergence` | Where label-changing CRN pairs first diverge, relative to the fence line (F1). |
| `fig5_f2_margin` | Twin margin m per task (bars, 2 x scoring SD) and the margin at the fork token (black ticks), with the 5.70-nat line; same-seed tasks highlighted (F2). |
| `fig6a-d_sd_manifold_*_b18` (block 23 versions beside) | S-d forced-prompt manifolds (MDS of k-NN geodesics): forced points, centroids sized by implemented count in twin / base model / plan noise / push rows, twin stars, push arrows by alpha, random-control cloud; stress in the title. |
| `fig7_dose_axis` | Off-default share against realised ||d||/||h|| at the site, every prefill site; S0's alpha-1/2 fractions dotted. |
## Design (what was run)

**Model and decoding.** Qwen3-8B, revision `b968826d9c46dd6066d109eabc6255188de91218`, thinking off, T = 1.0, top-p 1,
no top-k. A row stops at end of turn or at the closing fence of its first code block (exp20's fence stop); at most
1,024 new tokens on T03/T10 and 1,536 on T2/T1. **Precision W16A16**: bf16 weights and bf16 activations in HF
transformers 4.57.6 (attention `sdpa`) on one NVIDIA L4 (22 GiB usable). Every edit is computed in fp32 and cast to
bf16. This label is on every row (`precision: "W16A16"`). Nothing here crosses precisions inferentially; the
iteration-4 FP8 cells are set beside these ones only descriptively (`results/fp8_vs_bf16_sites.json`).

**Prompts.** These are the neutral twins of exp17's ban prompts, as exp20 used them (5 templates W1-W5 per task). The
condition sentence names a neutral noun, padded with ` .`. It is followed by the fixed task specification and the
chat tail. Every prompt is re-rendered through the chat template and must reproduce exp20's ids and sha256.
Ban prompts enter only as forward passes, to measure r_Q. U7 checks that none is ever sampled.

**Sites.** Every edit is displacement-targeted: `h <- h + (target - (h - h_twin).u) u`. The displacement from the
clean twin along `u` therefore equals the target exactly at every hooked block and position. The dose is the
**ban-free unit** `n[l,p] = ||h_twin[l,p]|| x r_Q(l)`. Here r_Q(l) is the median ban displacement ratio: exp23's
frozen value at blocks 12-23, and a bf16 recomputation by exp23's recipe at blocks 0-11 and 24-35. The calibration
ratio at blocks 12-23 is 0.952, inside [0.9, 1.1], so no rescaling was applied. Sites:

| Site | Blocks | Positions | Per-position target |
|---|---|---|---|
| S0 | 12-23 | task spec S | alpha x n[l,p] |
| S4 | 0-11 | S | alpha x n[l,p] |
| S5 | 24-35 | S | alpha x n[l,p] (the block-35 edit is a no-op, U5) |
| S1 | 12-23 | read position R = P-1 | alpha x n[l,R] |
| S1E | 12-23 | R | alpha x c x n[l,R], c = sqrt(sum_{l,S} n^2 / sum_l n[l,R]^2): energy-matched to S0 |
| S2 | 12-23 | condition sentence COND (every token) | alpha x n[l,p] |
| S3 | 12-23 | generated input positions 1-32, against a teacher-forced shadow row | alpha x n_G[l] |
| TOP5 | 12-23 | S | per-block push u_push[l] = unit(mean survivor centroid - mean banned centroid) |
| TOP3 | 12-23 | S | the same push for the T03 top-3 variant |

**Directions and common random numbers.** Slot (t, w, k) has one random direction,
`u = normalise(PCG64(stable_seed('ITER6_S2', t, w, k)).standard_normal(4096))`. This namespace is new: its maximum
|cos| with every earlier direction file is 0.069 (`directions/seeds.json`). It is shared by every site and dose.
Slot (t, w, k) also has exp17's token uniforms u_stream(t, w, k). Every site contrast is therefore an exact paired
flip on the same slot. Batches have a fixed shape (16 rows on T03/T10, 12 on T2/T1) and hold one (task, template).
Finished rows are fed `<|im_end|>`. Under that shape a row's tokens do not depend on its batch-mates (U1).

**Cells.** Twins N = 50 (k 0-9). On T03 and T10 the sites S0, S4, S5, S1, S2 and S3 run at alpha 1, 2 and 4, N = 30
each (k 0-5), plus S1E. On T2 the same sites (and S1E) run at alpha 2 and 4. The S-d pushes run at alpha 1, 2 and
4, N = 50: T03 top-5, T03 top-3, T10 all-but-one and T1's iteration-4 u_top5. T1 also gets its twin and an S0
random control at the same per-position unit. The outcome-blind extensions are S4 at alpha 8 and a top-up of the
P2 cells to N = 50 (k 6-9). The positive control U8 replays exp25's ECBAN cells (rand_9002 on T03 and rand_9004
on T2, alpha 1, exp17's FP8 ban unit, 50 slots each).

**Order of operations.**
1. CPU: input copies and hashes, then the CPU tests.
2. GPU prep: positions, r_Q, units, forced states, banned sets, push directions, push progress, memory probe.
3. GPU tests U1-U6, then the positive control U8, then smoke slots (k >= 100).
4. Commit #1 (rules, cells, sets, units, directions, predictions).
5. Decisive sampling in priority order. The label worker runs alongside it.
6. F2 scoring passes.
7. Commit #2 (final analysis code), then the analysis, the novelty audit, the figures, the outputs and the
   independent re-derivation.

## Layout

| Path | What it is |
|---|---|
| `method.py` | Orchestrator, one sub-command per stage (`uv run method.py <stage>`; see its docstring). |
| `src/cfg.py` | Frozen constants (tasks, defaults, sites, blocks, alphas, slots, batch shape), paths, JSON/hash helpers. |
| `src/engine_w16.py` | W16A16 HF engine: batch-1 prefill with edit hooks, CRN inverse-CDF sampler, fence stop, S3 shadow site, teacher-forced scoring, thinking sampler. |
| `src/hooks.py` | The displacement-targeted edit (exp20's maths) and its batched form. |
| `src/sites.py` | Per-(task, template) context, ban-free units, site targets, directions, row prefill with displacement logging, fixed-shape batches. |
| `src/prompts.py` | Prompt loading and re-render check, COND/S/R spans, forced named and masked prompts for the S-d manifold. |
| `src/schedule.py` | Cells, execution priorities (drop order), fixed-shape batch packing with TWIN_X fillers. |
| `src/gpu_main.py` | GPU driver: prep, tests (U1-U8), decisive sampling with timing extrapolation. |
| `src/geometry.py` | Implemented counts, banned sets, push directions, push progress, k-NN geodesics, MDS, edge test. |
| `src/decide.py`, `src/stats.py` | Committed decision rules (S-a, S-b, S-c, F1, F2) and their statistics. |
| `src/label_worker.py`, `src/label_k7.py` | Frozen gated labellers (exp20's), and exp9's K=7/extended T1 labeller. |
| `src/scoring.py` | F2 teacher-forced q_lik / margin passes on 15 tasks, and the thinking-on T2 margin. |
| `src/analysis.py` | Every analysis: cells, S-a, S-b, S-c, landings, dose axis, F1, F2, S-d, engine checks, FP8 comparison. |
| `src/audit.py`, `src/audit_rows.py` | Novelty audit (exp20's module): stress tests, known-solution index, blind judges, controls. |
| `src/figures.py`, `src/outputs.py` | Figures and `method_out.json`. |
| `src/prereg.py`, `src/commit.py` | Input hashes, direction seeds, commits #1/#2 (hash chain in `commitments.log`). |
| `tests/test_cpu.py` | CPU unit tests (all 9 pass; `results/unit_tests_cpu.json`). |
| `audit/rederive.py` | Independent re-derivation of the headlines with placebos (`results/rederive.json`). |
| `audit/rederive_extra.py` | Second independent re-derivation (stdlib only): m_fork, S-d paired flips, counts, novelty, spend, with placebos (`results/rederive_extra.json`). |
| `reproducibility.md` | Step-by-step reproduction of exactly what was run (commands, seeds, hardware, times, expected numbers). |
| `inputs/` | Read-only copies of every earlier-artifact file used, with `inputs/SHA256SUMS` (572 files). |
| `data/samples_raw.jsonl`, `data/labels.jsonl`, `data/labels_k7.jsonl`, `data/samples.jsonl` | Raw rows, labels, T1 K=7 labels, merged rows (the row schema of the plan). |
| `data/row_logs/` | Per-cell fp32 arrays: per-position displacement at the last hooked block, post-edit S-means (blocks 18, 23). |
| `units/` | r_Q for all 36 blocks, ban-free units per task. |
| `directions/` | Push directions, the T1 bf16 rebuild, the seed registry. |
| `cache/` | bf16 twin states (all blocks; S, R, COND), forced-prompt states, push states, code-opening states. Kept on the run volume (files >= 100 MB are not published). |
| `predictions/` | Commit #1 content (`s_commit.json`, `banned_sets.json`). |
| `results/` | Every analysis JSON; `figures/` the figures. |
| `method_out.json` (+ mini/preview) | exp_gen_sol_out output. |

## How to run

Every stage also runs as `uv run method.py <stage>` (for example `uv run method.py cputests`).

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python method.py inputs && .venv/bin/python method.py cputests
.venv/bin/python method.py prep && .venv/bin/python method.py seeds && .venv/bin/python method.py gputests
.venv/bin/python method.py commit1
.venv/bin/python method.py sample --deadline-unix <unix time> &      # decisive sampling (GPU)
(cd src && ../.venv/bin/python label_worker.py follow) &              # labels alongside
.venv/bin/python method.py score && .venv/bin/python method.py label   # F2 passes; K=7 labels for T1
.venv/bin/python method.py commit2 && .venv/bin/python method.py analyse
.venv/bin/python method.py audit && .venv/bin/python method.py audit_summary
.venv/bin/python method.py figures && .venv/bin/python method.py outputs
```

The Qwen3-8B weights come from the Hugging Face cache (`huggingface-cli download Qwen/Qwen3-8B --revision
b968826d9c46dd6066d109eabc6255188de91218`). The declared dataset dependency (art_j3Rm_lr2nzR6,
`full_data_out.json`) is read in place to rebuild the known-solution index: set `ART_J3RM_DIR` to its folder
(this run read it from the dependency workspace on the run volume). Figures use the aii-data-fig-gen house style
when `AII_DATA_FIG_GEN_SCRIPTS` points at its `scripts/` folder, plain matplotlib otherwise.

## Restoring removed files

| Removed path | How to restore |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` |
| `src/__pycache__/` | regenerated automatically by any python run of `src/`, e.g. `.venv/bin/python method.py cputests` |

Everything else is kept. `cache/` stays on the run volume at the path it already has. It is excluded from the
published repository: its four `twin_states_*.pt` files are over 100 MB each. To rebuild it, run
`.venv/bin/python method.py prep` for the twin, forced and push states, and `.venv/bin/python method.py score` for
the code-opening states.
