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
