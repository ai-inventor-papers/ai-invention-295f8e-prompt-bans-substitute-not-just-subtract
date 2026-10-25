# Which weights hold the default algorithm (iteration 10, BASE-W)

Iteration 9 found that when Qwen3-8B writes a program it commits to an algorithm at one **fork token**, and
that post-training sharpened that choice relative to Qwen3-8B-Base. Its component patching was non-specific:
matched random late-layer sets closed 81% of the MST gap.

This artifact moves the question from activations to **weights**. It asks whether the instruct default is stored
in the fork-class **unembedding rows** (W1) or in the **late-MLP weights** (W2). It also repeats the row test on
Gemma-3-4b (W3, descriptive).

Every arm is compared with matched-norm nulls, and the readout arm is tested again in free generation with
common random numbers. All decisive predictions were sha256-chained before the computation they govern
(`commitments.log`).

Units, prompts, openings, fork-class tokens, the generation engine and the frozen labellers come from iteration 9
(`inputs/iter9/`):
* **CC (T10, primary):** connected components, D = {' find'} (union-find) vs A = {' dfs', ' bfs'}, 20 prompts.
* **MST (B3, beside):** Kruskal-class vs Prim-class tokens, 20 prompts.

Margin `m = lse(z[D]) - lse(z[A])` is read at the fork. A share is the fraction of the instruct-minus-base margin gap
closed, `share = sum_p (m_I - m_arm) / sum_p (m_I - m_B)`, a ratio of sums over prompts with a 95% prompt bootstrap.

## Headline results (numbers from `results/*.json`; `results/summary.json` collects them)

### Stage 0: recapture on an RTX 4090 (iteration 9 ran on an L4)

| | T10 (CC) | B3 (MST) |
|---|---|---|
| gap m_I - m_B (nats) [95% CI] | 4.56 [3.58, 5.60] (iter 9: 4.52) | 2.09 [1.98, 2.21] (iter 9: 2.06) |
| mean m_I here / iter 9 | 4.516 / 4.455 (diff **0.061 > 0.05**) | 1.320 / 1.311 |
| mean m_B here / iter 9 | -0.042 / -0.064 | -0.770 / -0.748 |
| CPU decomposition, unembedding-only share (target 0.85 / 0.43 +- 0.03) | **0.842** | **0.416** |
| rms(h_pre, g) recompute vs captured h_fin (G1) | bit-exact (20/20) | bit-exact (20/20) |

The reproduction rule passes for B3's means and for both decompositions. It fails for the T10 instruct mean
(0.061 > 0.05) and for the per-prompt Spearman (0.98 / 0.90 < 0.99).

Debug round 1 checked the obvious causes and found none:
* Ids and sha256 match `units.json`.
* The stack is the same (pins, sdpa, B_ot = 40).
* On this GPU, the instruct T10 margin varies by a mean 0.27 and a maximum 0.55 nats across numerically equivalent
  paths: B = 1, 8, 16, 24, 40 and a full forward (`results/s0_debug.json`).

So the cross-GPU differences are the size of the bf16 numerics floor. Fallback F1 applies: every share below uses
this run's own m_I / m_B from the same cached states. The headline wording is "own-capture reproduction failed by
0.061 nats on the T10 instruct mean".

### W1: restoring the base fork-class rows on the instruct residual (exact CPU readout on cached fork states)

| arm (instruct residual throughout) | T10 share [95% CI] | B3 share [95% CI] |
|---|---|---|
| **ROWS_ALL** (all S = D u A rows from the base model) — PRIMARY | **0.548 [0.440, 0.707]** | 1.249 [1.180, 1.323] |
| ROWS_D (default rows only) | 0.060 [0.047, 0.078] | 0.009 |
| ROWS_A (alternative rows only) | 0.489 [0.392, 0.629] | 1.240 |
| NORM (base final-norm gain) | -0.000 | 0.006 |
| ROWS_NORM (rows + gain = readout upper bound for the class margin) | 0.547 | 1.254 |
| FULL_UNEMB (all 151,936 rows) | 0.548 (identical to ROWS_ALL by construction) | 1.249 |
| SIGN (lambda = -1) | -0.548 | -1.185 |
| DOSE lambda = 0.25 / 0.5 / 0.75 / 1.25 / 1.5 | 0.14 / 0.27 / 0.41 / 0.69 / 0.82 | 0.31 / 0.62 / 0.94 / 1.56 / 1.88 |
| null RAND_ISO (50 isotropic, matched norm): median / p95 / max; empirical p | 0.044 / 0.138 / 0.210; **p = 0.020** (= 1/51 floor) | 0.051 / 0.720 / 0.942; p = 0.020 |
| null DELTA_SWAP (50 real deltas of other tokens): median / p95 / max; p | 0.085 / 0.405 / 0.625; p = 0.059 | 0.055 / 1.169 / 1.511; p = 0.059 |
| null RAND_RESID (50 random directions in the residual's top-64 PCs): median / p95 / max; p | 0.181 / **1.252** / 2.328; p = 0.373 | 0.113 / 5.394 / 6.224; p = 0.275 |
| 2x2 factorial interaction m_II - m_IB - m_BI + m_BB (nats) [95% CI] | -1.337 [-1.39, -1.29] | +1.748 [1.72, 1.77] |

* **W1 verdict (T10, committed rule): SUPPORTED.** ROWS_ALL is 0.548, at least 0.50. The median RAND_ISO is 0.044,
  at most 0.15. ROWS_ALL is above the RAND_ISO maximum of 0.210.
  * The bootstrap CI's lower end (0.44) lies below 0.50.
  * The committed specificity qualifier gives **"readout-level but not token-specific"**. ROWS_ALL clears the
    DELTA_SWAP p95 (0.405) but sits inside the RAND_RESID distribution (p = 0.37).
* **Shape of the effect.**
  * The restoration is linear in dose: share 0.137 per 0.25 lambda.
  * The sign flip widens the gap by the same amount.
  * The final-norm gain contributes nothing.
  * Almost all of the effect is in the **alternative** rows: ROWS_A 0.489 vs ROWS_D 0.060.
  * The base rows raise the fork logits of ' dfs' by +2.23 and ' bfs' by +3.14 nats, and change ' find' by only
    -0.27 (`per_token_logit_change`).
  * So post-training wrote the CC default mainly by **suppressing the alternatives' readout rows**, not by boosting
    the default's.
* **Delta geometry** (`results/delta_geometry.json`).
  * The ' dfs' / ' bfs' deltas point where the fork residual lives. Their logit leverage |h.Delta| / (|h||Delta|) is
    0.069 / 0.085, close to the RAND_RESID medians (0.085 / 0.093) and 7-9x the isotropic value (0.010).
  * The ' find' delta is isotropic with respect to the residual subspace. 1.6% of its energy lies in the top-64 PCs,
    which is exactly the isotropic expectation 64/4096.
  * This is why RAND_RESID out-levers the real deltas: equal-norm edits aimed entirely at the residual subspace have
    more leverage than the real ones.
* **B3 (descriptive)** shows a different structure.
  * The base rows read on the instruct residual overshoot the base margin (1.25 of the gap).
  * Iteration 9's CPU decomposition put only 0.42 of the gap in the unembedding when it reads the **base** residual.
  * The interaction is large and opposite in sign to CC (+1.75 vs -1.34 nats). Readout and residual are not additive
    at either fork.
* The audit's D/A-identity shuffle placebo does not fail on T10 (median 0.44 vs the true 0.55). This agrees with
  "readout-level, not token-specific": restoring all three rows moves any contrast among them toward the base readout.

### W1 generation (30 common-random-number slots per arm; fork-only difference; frozen hidden-test labellers)

Correct = label 'dfs' and passes the hidden tests (T10), or label in {prim_heap, prim_array} and passes (B3). Each
predicted count was committed in COMMIT #2 (#4 and #5 for the extensions) before any token was generated.
McNemar tests are exact two-sided tests on CRN pairs.

| arm | T10 correct DFS / 30 (predicted) | vs TWIN | B3 correct Prim / 30 (predicted) | vs TWIN | pass rate |
|---|---|---|---|---|---|
| TWIN (instruct readout, fp32) | 1 (1.1) | — | 0 (5.9) | — | 30/30, 30/30 |
| **ROWS** (base S rows at the fork) | **5 (6.2)** | 4:0, p = 0.125 | **24 (22.9)** | 24:0, p = 1.2e-7 | 30/30, 30/30 |
| RAND_MED / RAND_MAX / RAND_0 (committed isotropic draws) | 1 / 1 / 0 | RAND_MED 0:0 | 0 / 19 / 10 | RAND_MED 0:0 | 30/30 |
| FPD (base fork logits; Cantarero et al.) | 15 (13.4) | 14:0, p = 1.2e-4 | 17 (18.7) | 17:0, p = 1.5e-5 | 27/30, 30/30 |
| ROWS_ALLSTEPS (rows swapped for every step) | 5 | identical to ROWS (0:0) | 24 | identical to ROWS | 30/30 |

* **W1-GEN verdict (T10, committed rule): NOT SUPPORTED.**
  * ROWS gives 5/30, below the registered 10/30 bar.
  * ROWS vs TWIN and ROWS vs RAND_MED are both 4:0, p = 0.125 (Holm 0.25).
  * The committed note had warned that 10/30 needs a slot-prompt share of about 0.75. The observed share was 0.57 and
    the predicted count 6.2.
* **Power extension (pre-registered, COMMIT #7):** 60 more CRN slots (seeds 9131–9190), pooled with the committed 30
  into 90 pairs. The effect at λ = 1 is real but too small for the registered bar.
  * T10: ROWS **21/90** correct DFS (predicted 18.6) vs TWIN 4/90. ROWS vs TWIN is 17:0, p = 1.5e-5, and ROWS vs
    RAND_MED (4/90) is also 17:0, p = 1.5e-5.
  * B3: ROWS 72/90 vs TWIN 17/90 (55:0, p = 5.6e-17); RAND_MED is 18/90.
  * Results: `results/w1_generation_power.json`.
* FPD reproduces iteration 9's direction: 15/30 here vs 18/30, and 14:0 here vs 18:1.
* On MST, restoring the rows flips 24/30 programs to correct Prim. One of the three isotropic draws, the one with the
  maximum teacher-forced share, flips 19/30.
* Swapping the rows for all later steps changes nothing beyond the fork.
* No correct program was labelled 'other', so no novelty judge was called (USD 0).

**Extension, pre-registered (COMMIT #4 / #5): can a stronger edit of these rows steer what the model writes?**

| fork rows at the fork step | T10 correct DFS / 30 (pred.) | B3 correct Prim / 30 (pred.) |
|---|---|---|
| ROWS x2 (w_I + 2 Delta) | **21** (16.8); vs TWIN 20:0, p = 1.9e-6 | 27 (29.3) |
| ROWS x3 | **30** (27.3); vs TWIN 29:0, p = 3.7e-9 | 27 (29.9) |
| RAND_MED x2 / x3 (median isotropic draw, same dose) | 1 / 1 | 3 / 3 |
| RAND_RESID median draw x3 / max draw x3 | 6 / 30 | 28 / 27 |
| DELTA_SWAP median draw x3 / max draw x3 | 3 / 30 | 22 / 27 |

* Every program in every arm passes the hidden tests (30/30), so the edit costs no correctness.
* On CC, the base-row delta at ×3 beats the *median* strong-null draws: ROWS×3 vs RAND_RESID-median×3 is 24:0
  (p = 1.2e-7), and vs DELTA_SWAP-median×3 27:0.
* It ties the *best* of 50 draws of each null (0:0).
* On MST, almost any large edit of these rows flips the fork. Even the median residual-subspace draw ×3 gives 28/30.

### W2: late-MLP weights swapped to base (all positions, in place; teacher forced)

| | T10 share [95% CI] | B3 share [95% CI] |
|---|---|---|
| W_late_joint (MLPs 26-35 base) | **-0.145 [-0.31, -0.03]** | 0.313 [0.28, 0.34] |
| E_joint (Hungarian-matched early MLPs 13..4, delta scaled by c = 1.19) | **0.461 [0.29, 0.59]** | 0.317 [0.28, 0.36] |
| late - early [95% CI] | -0.606 [-0.78, -0.48] | -0.004 [-0.06, 0.05] |
| RANDDELTA_joint (3 same-layer random deltas, matched per-matrix norm) | -0.36, 0.21, -0.29 | 0.59, -0.54, -0.01 |
| late attention 26-35 / late blocks (attn + MLP) | 0.324 / -0.027 | 0.239 / 0.389 |
| joint: late MLPs + base readout (DECOMP) / late blocks + base readout | 0.621 / 0.874 | 1.380 / 1.081 |
| decomposition: readout 0.547, late MLPs -0.145, interaction +0.219, remainder 0.379 (T10) | | readout 1.254, late MLPs 0.313, interaction -0.188, remainder -0.380 (B3) |
| best singles (share; matched early; 3 random deltas) | L30 0.236 (E9 0.205; <= 0.02), L28 0.197 (E11 -0.48), L35 -0.332 | L32 0.545 (E7 -0.13; <= 0.19), L34 0.540 (E5 0.10) |

* **W2 rule (T10, secondary, committed): does not hold.**
  * The late MLPs do not beat Frobenius-matched early swaps: the early swaps close more, and the late joint swap
    slightly widens the gap.
  * Same-layer random deltas of the same norm move the margin by comparable amounts in both directions.
* The weight-level answer to "is it these MLPs, or any MLP edited by that much?" is **any**, at this resolution.
* Single late layers L30 / L28 (CC) and L32 / L34 (MST) exceed their own same-layer random deltas. But a matched
  early layer can do almost as much (E9 0.205 next to L30's 0.236), and the late singles do not add up in the joint
  swap. This is the same redundant, non-additive picture iteration 9 saw with activations.
* **Bridge to iteration 9:** the fork-only scope reproduces iteration 9's W arm within 0.008 on all 12 checks.
  * T10 W28 0.210 vs 0.214, W30 0.227 vs 0.232, W_all(5) 0.379 vs 0.383.
  * B3 W32 0.419 vs 0.426, W_all(5) 0.227 vs 0.227.

### W3: Gemma-3-4b grid fork, output-only untying (descriptive)

* **Setup.** The gap is 1.84 nats. Instruct P(D) 0.675 and base 0.088 reproduce iteration 9's 0.671 / 0.089.
  Mean margins agree within 0.04 nats.
* **Result.** The base rows **widen** the gap:
  * ROWS_ALL share is -0.253 [-0.41, -0.12].
  * ROWS_D is +0.376 and ROWS_A -0.629.
  * The sign flip closes 1.43.
* In Gemma the post-training row changes push *against* the instruct DFS default, so the default sits in the
  residual. This is consistent with Miyashita's report that lm_head structure depends on the model family.
* **Nulls.**
  * RAND_ISO: median 0.165, max 1.92.
  * DELTA_SWAP: median -0.58. It is partly degenerate, because the '\n' row's norm-matched pool holds a single token.

### What this means for the run's question ("can we make the model pick a different, less default solution?")

At the decision token, post-training stored a large part of Qwen's default as a **readout** change. It suppressed
the alternatives' unembedding rows ('dfs' / 'bfs', 'Prim' class) more than it promoted the default. Restoring those
few rows (3 of 151,936 on CC) brings back part of the base model's spread: correct DFS rises from 4/90 to 21/90
programs over 90 CRN pairs.

Pushing further along the same row delta (×2–3) makes Qwen write the alternative algorithm in 21–30 of 30 CC
programs and 27 of 30 MST programs, with every program still passing the hidden tests. That is a cheap,
inference-free lever over **which known algorithm** gets written.

Two limits apply:
* **Not unique.** The most effective of 50 random or transplanted row edits of the same size (picked by
  teacher-forced share) does as well, and on MST almost any large edit flips the fork. So the lever is "edit the alternatives' readout rows", not "the post-training delta is
  special".
* **Not novelty.** No edit produced a correct program outside the known classes.

The late MLPs are not where the default is held in any specific way.

## Design notes

* **The class margin depends only on the fork-class rows and the final-normed residual.** So every W1 arm and null is
  exact arithmetic on cached fp32 fork states, and "full base unembedding" equals the fork-class rows for the margin
  (FULL_UNEMB = ROWS_ALL to 0.0). The readout upper bound is rows + final-norm gain (ROWS_NORM). In generation, the
  full-unembedding fork arm differs from ROWS by a total variation of only 0.0000 (T10) and 0.0005 (B3). It was
  therefore not run, as committed.
* **Held constant:** token ids, positions, the prefilled instruct opening, GEMM batch shapes, common random numbers
  and the labeller.
  * The one-token path uses B_ot = 40 rows, the same shape as iteration 9.
  * Generation uses B = 6 for every arm.
  * Every arm, TWIN included, uses an fp32 full-vocabulary readout at the fork.
* **Nulls draw independent rows:** each null draw moves every S row with its own `np.random.default_rng([seed, token
  id])` stream (seeds 101000 / 102000 / 103000 + 100 × unit + k). DELTA_SWAP never repeats a token within a draw, and
  never picks S or tokens whose string contains a class string.
* **Weight swaps are exact and reversible:** `param.data.copy_` from CPU copies, with `torch.equal` asserted after
  every arm. The TWIN margin was re-checked bit-exactly against stage 0 every 10 arms (all equal).

## Pre-registration (`commitments.log`, hash chain from genesis sha256('iter10_basew'); verified in `results/tests_cpu.json`)

| commit | before | content |
|---|---|---|
| #0 `commit0_protocol` | any model forward | `predictions/commit0_protocol.json` (every arm, null, threshold, verdict rule, seed, figure), code snapshot `predictions/code_commit0/`, `inputs_manifest.json`, labeller gate |
| #1 `commit1_stage0_nulls` | any W1 arm scored | stage-0 table, every `cache/fork_*.pt`, residual PCA, `results/null_draws_*.npz` |
| #2 `commit2_w1tf_genplan` | any generated token | W1-TF results, the 3 generation random draws, predicted counts per arm and slot prompt, McNemar list, the 10/30-bar note |
| #3 `commit3_w2_matching` | any W2 forward | Hungarian matching (26→13, 27→12, …, 35→4) and c = 1.192 |
| #4 / #5 | the extension tokens | dose-response and strong-null generation plans with predicted counts |
| #7 `commit7_power_gen` | the 60 extra slots | power-extension plan and predicted counts |
| #8 `commit8_code_final` | — | snapshot of the final code (`predictions/code_final/`); #6 is unused |
| #9 `commit9_code_final_v2` | — | code snapshot v2 (`predictions/code_final_v2/`). It supersedes #8, because `tests_cpu10.py` gained the history-aware chain check after #8. |
| #10 `commit10_code_final_v3` | — | code snapshot v3 (`predictions/code_final_v3/`). It supersedes #9 and adds `depcheck10.py` and its wiring. |
| #11 `commit11_code_final_v4` | — | code snapshot v4 (`predictions/code_final_v4/`). Input locations come from environment variables with workspace-relative defaults, so the published code holds no absolute server path. |
| #12 `commit12_code_final_v5` | — | **final** code snapshot (`predictions/code_final_v5/`). It resolves inputs from the published sibling folder named by artifact id and adds `audit/rederive_headline.py`. |

**Provenance records.** The committed provenance records (`inputs_manifest.json` and the earlier code snapshots) keep the
original absolute source locations on the run volume. They are records, not code paths: editing them would break the
chain.

**Chain status.** All links verify. Two file hashes, both from COMMITs #4 and #5, no longer match:
* They point at the live `src/w1_dose_gen.py`, which was later extended. Functions for the two later extensions were
  appended, breaking the rule not to edit a committed file.
* The committed versions were reconstructed byte-exactly and match their committed sha256:
  `predictions/code_history/commit4_w1_dose_gen.py` and `commit5_w1_dose_gen.py`.
* `results/tests_cpu.json` reports both checks: strict `T5_strict_chain_ok = false`, history-aware `T5_pass = true`.

## Checks and audit

* **CPU unit tests** (`results/tests_cpu.json`, all pass):
  * readout equivalence, 1.2e-5;
  * identities: λ = 0 equals TWIN, FULL_UNEMB equals ROWS_ALL, the sign flip, share(TWIN) = 0 and share(m_B) = 1;
  * null reproducibility and norms;
  * one-to-one matching and exact c;
  * chain verification;
  * the audit self-test.
* **GPU tests** (`results/tests_gpu.json`):
  * G1: bit-exact rms recompute.
  * G2: numerics floor of up to 0.55 nats (T10 instruct).
  * G3: swap/restore bit-identical.
  * G4: fork-only hook vs CPU fp32, 1.7e-3 (bf16 rounding).
  * G5: generation determinism and the λ = 0 CRN identity.
  * G6: lm_head row restore bit-exact.
  * G7: Gemma CPU readout within bf16 logit quantisation (max 0.125).
* **Labeller gate:** label_k3.py reproduces iteration 9's 240 labels on 240/240 (`results/labeller_gate.json`).
* **Declared-dependency check** (`src/depcheck10.py` → `results/depcheck_leetcode.json`). Every generated CC program
  was re-run against the parsed LeetCode I/O pairs of problems 323 and 547 from the declared dependency
  `art_j3Rm_lr2nzR6`: 71 + 57 = 128 cases, 547 converted to edge lists.
  * 627/630 programs pass all 128 cases, and 627/630 pass the frozen labeller's hidden tests.
  * Agreement is 1.000, so the correctness counts do not depend on one test suite.
  * The plan otherwise reserved this dataset for the REBUILD fallback, which did not trigger.
* **Independent stdlib audit** (`audit/rederive.py` → `results/rederive.json`): 425 checks, 0 mismatches. It re-derives every
  share, null median / p95 / max / empirical p, verdict, correct count, Wilson interval and McNemar b / c / p.
* **Independent headline re-derivation** (`audit/rederive_headline.py` → `results/rederive_headline.json`).
  * It works in float64 NumPy, with no imports from `src/`. It reads the raw cached fork states, the raw safetensors
    lm_head rows, the committed null draws, the raw program labels and the raw W2 rows.
  * It reproduces every W1 share within 4.4e-7, the RAND_ISO median / max / p, all generation counts and McNemar
    b / c / p, and the W2 late / early shares.
  * Its placebos fail as they should:
    * each RAND_ISO draw treated as "observed" reaches p ≤ 0.05 in 4% of cases, close to the nominal 5%;
    * a constant arm gives share 0;
    * label swaps within CRN pairs give median McNemar p of 0.50–0.79.
* **Placebos:**
  * Noise-only arms: |share| ≤ 0.017. Fails to reproduce an effect, as it should.
  * Random label swaps within CRN pairs: median p 0.63 / 0.54. Fails, as it should.
  * D/A shuffle: see W1 above.

## Deviations (full list with severities: `results/deviations.json`)

* **Hardware.** The machine is an RTX 4090 (24 GB), not the planned A4500, so B_ot = 40 fits.
* **Stage 0** only partly reproduces; fallback F1 applies (above).
* **T1/T2 were dropped**, second in the drop order. Their planned single-position margin is degenerate:
  * every fork token has phat_off < 0.5;
  * so the runner-up segment's first token is itself a D token (A ⊂ D);
  * only iteration 8's 16-token path margin is defined there.
* **Code placement and commits.**
  * The vendored iteration-9 code lives at `inputs/iter9/src` (verbatim), not `src/vendor9`.
  * COMMIT #0 snapshots the code that existed before the first forward. The final snapshot is commit #12.
  * The live `src/w1_dose_gen.py` committed in #4 and #5 was later extended. Its committed versions are reconstructed
    byte-exactly in `predictions/code_history/`.
* **Test ordering.** The CPU tests ran after the GPU stages.
* **W2 smoke test.** A 2-prompt smoke test ran before the full W2 run, and its rows were deleted. The smoke test's G4
  check was mis-ordered and was fixed.
* **RAND_RESID storage.** Only the top-64 basis was stored.
* **Gemma null.** The DELTA_SWAP '\n' pool holds 1 token.
* **Extensions.** Three generation extensions beyond the plan (doses, strong nulls, 60 extra slots for power), all
  pre-registered.

Not run: FULL_UNEMB_FORK generation (committed TV < 0.05), the novelty judges (no correct 'other' program), and T1/T2.
OpenRouter spend: USD 0.

## Layout

| path | content |
|---|---|
| `method.py` | stage CLI (`--stages s_1,s0,w1tf,w1gen,ext,w2,w3,out` or `all`); every stage script runs in its own process, PIDs in `logs/pids.jsonl` |
| `src/cfg10.py` | constants, seeds, thresholds, paths, utilities, hash-chained commitments |
| `src/inputs10.py` | vendoring + sha256 manifest, hardware/env record, labeller gate, labeller subprocess wrapper |
| `src/protocol10.py` | COMMIT #0 protocol (`predictions/commit0_protocol.json`) |
| `src/capture10.py` | S0 one-token fork-state capture (h_pre, h_fin, MLP in/out, fp32 fork logits), engine check, batch sweep, residual PCA |
| `src/debug_s0.py` | S0 debug round: per-prompt margin spread over equivalent paths |
| `src/w1_tf.py` | stage-0 report, null draws (COMMIT #1), every W1 arm / null / factorial (COMMIT #2 with generation predictions) |
| `src/w1_gen.py` | W1 generation engine (CRN, fixed B = 6, fp32 fork readout), G5, labelling, McNemar analysis |
| `src/w1_dose_gen.py` | pre-registered generation extensions: dose-response (COMMIT #4), strong nulls at ×3 (COMMIT #5), 60 extra CRN slots for power (COMMIT #7) |
| `src/w2_swap.py` | Hungarian matching (COMMIT #3), in-place weight swaps (all-position and fork-only), W2 summary + decomposition |
| `src/w3_gemma.py` | Gemma-3-4b it/pt fork capture and the output-untied row test |
| `src/analysis10.py` | delta geometry and `results/summary.json` |
| `src/figures10.py` | figures F1-F8 |
| `src/outputs10.py`, `src/positioning10.py`, `src/tests_cpu10.py` | `method_out.json`, dated literature verdicts, CPU unit tests |
| `src/depcheck10.py` | independent correctness check of the CC programs on the declared dependency's LeetCode 323/547 I/O pairs |
| `audit/rederive.py` | independent standard-library re-derivation with placebos |
| `audit/rederive_headline.py` | short float64 re-derivation of the headline numbers from the raw files, with placebos |
| `reproducibility.md` | what was run, in order, with versions, seeds, hardware, runtimes and expected numbers |
| `inputs/art_j3Rm_lr2nzR6/` | declared dependency (iteration-1 dataset): its preview / mini files, reproducibility notes, and the LeetCode 323/547 subset of `full_data_out.json` used by `depcheck10.py` (source sha256 inside) |
| `inputs/iter9/` | verbatim copy of iteration 9's artifact inputs (units, summaries, labels, samples, vendored labeller tree, code); sha256 in `inputs_manifest.json` |
| `predictions/` | committed payloads (`commit*.json`), code snapshots, hardware and environment records |
| `commitments.log` | the hash chain |
| `results/` | `stage0.json`, `s0_debug.json`, `w1_tf_rows.jsonl` / `w1_tf_summary.json`, `null_draws_*.npz`, `w1_generation.json`, `w2_rows.jsonl` / `w2_summary.json` / `w2_matching.json`, `decomposition.json`, `w3_rows.jsonl` / `w3_summary.json`, `delta_geometry.json`, `positioning.json`, `rederive.json`, `tests_*.json`, `deviations.json`, `summary.json`, `partial_status.json`, `w1_generation_power.json`, `depcheck_leetcode.json`, `labeller_gate.json`, `null_meta.json`, `w3_capture.json`, `w1_tf_zS.jsonl` |
| `data/` | generated programs (`gen_samples.jsonl`, 1,260 programs) and their labels (`gen_labels.jsonl`) |
| `figures/` | F1 shares + null histograms, F2 per-prompt shares, F3 dose-response, F4 generation, F5 fork states on the readout plane, F6 PCA of block-35 outputs, F7 W2 swaps + decomposition, F8 Gemma (PDF + PNG) |
| `cache/` | fork-state caches (see below) |
| `method_out.json`, `full_/mini_/preview_method_out.json` | per-example outputs (exp_gen_sol_out): `w1_tf`, `w1_generation`, `w2_tf`, `w3_tf` |
| `logs/` | stage logs, `time_ledger.jsonl`, `pids.jsonl`, positioning greps |

## How to run

The input locations default to the vendored copies. On the original volume they can be set with
`ART_CDBA8_DIR` (iteration-9 artifact) and `ART_J3RM_DIR` (declared dataset). Set `AII_JSON_SKILL_DIR` to let
`method.py` validate the schema and write the mini/preview variants.

```bash
bash restore.sh                       # uv environment + pinned model weights into $HF_HUB_CACHE
.venv/bin/python method.py --stages all
```

About 1 GPU-hour on one 24 GB GPU (S0 about 5 min, W1 generation about 8 min, W2 about 6 min, Gemma about 3 min,
the extensions about 8 min).

The CPU-only re-analysis (tests, audit, summary, figures, outputs) reruns from `cache/` and `results/` without a GPU:
`--stages out`. Re-running a committing stage (`s0`, `w1tf`, `w2`, `ext`) rewrites files that are already committed.
It appends new commits, and the old chain entries then show hash mismatches, as expected for a re-run.

## Restoring removed files

`.aii/manifest.yaml` marks these paths `delete`. `restore.sh` rebuilds them.

* `.venv/` (uv environment, about 10 GB):
  `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml`
* `src/__pycache__/`, `inputs/**/__pycache__/` (Python bytecode): rebuilt automatically on import, or
  `python -m compileall src inputs/iter9/src`.

The model weights are not inside this folder. They live in the shared Hugging Face cache. Re-download them with
`bash scripts/download_models.sh`, which runs `hf download <repo> --revision <sha>` for:
* Qwen/Qwen3-8B b968826d9c46dd6066d109eabc6255188de91218
* Qwen/Qwen3-8B-Base 49e3418fbbbca6ecbdf9608b4d22e5a407081db4
* google/gemma-3-4b-it 093f9f388b31de276ce2de164bdc2081324b9767
* google/gemma-3-4b-pt cc012e0a6d0787b4adcc0fa2c4da74402494554d

Gemma needs an HF token with Gemma access.

## Kept artifacts

These stay on the run's volume at these relative paths:
* `cache/` (about 140 MB): fork states of all four models, the residual PCA basis and the lm_head row norms. Every
  file is under 100 MB.
* `results/`, including `results/null_draws_B3.npz` (39 MB, committed in COMMIT #1).

They are also small enough to be in the published repository. Everything else is text, code or small figures.
