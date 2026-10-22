# Gemma: base runner-up vs the tuned model's own tail

This repository asks one question about `google/gemma-3-4b-it` (tuned) and `google/gemma-3-4b-pt` (base). When an
activation nudge moves the tuned model off its default algorithm on a coding task, which forecast names where the
nudged programs land? Three forecasts compete:
- the **base model's runner-up** algorithm r_u (and its distribution q_base);
- the **tuned model's own minority mode** t_u from 300 un-nudged samples per task (q_tail);
- the **tuned model's teacher-forced likelihood** of each algorithm's 48-token opening (q_lik).

It is iteration 6, step 5, of Claim L. It is the second-family **replication**: Gemma's iteration-5 landings were
already seen, and nothing here is pooled with the Qwen confirmation.

- **Setup.** Both models run bf16 (W16A16), text-only, one at a time on one 23 GB NVIDIA L4. The run produced 9,350
  generated programs and 4,836 teacher-forced passes in about 2.1 GPU-hours, plus USD 0.95 of OpenRouter judges.
- **Reuse.** exp28's engine, CRN sampler, push code, labellers and frozen twin prompts are reused. So are its 12,290
  rows, read from `inputs/exp28/`.
- **Pre-registration.** The hash chain in `commitments.log` holds three commits, all verified:
  - commit #0: protocol and frozen analysis, before any row;
  - commit #0b: a KeyError fix, before commit #1;
  - commit #1: the forecasts, at 23:50:52Z, before the first fresh push row at 23:52:40Z.
- **Corrections.** Holm is applied within this artifact. Holm across the iteration-wide family is left to the
  evaluation step.

## Results

**Bottom line.**

1. **All three forecasts usually name the landing, so the base runner-up shows no edge.** This is the pooled
   replication over 15 (unit, nudge) events, every one with a clear landing:
   - r_u hits **11 of 13** defined events (exact Poisson-binomial p = 5.8e-5 against a mean chance of 0.31). T03's
     r_u is undefined (see 4).
   - t_u hits **10 of 10** where defined (p = 7.9e-7). The 5 TAIL-EMPTY events leave t_u undefined.
   - The q_lik top-1 hits **13 of 15** (p = 3.5e-6).
   - **Where r_u and q_lik disagree, they split 2–2** (L1b sign test p = 0.69). r_u wins R6, where q_lik says
     bisect_module. q_lik wins T10, landing union_find.
   - **Where r_u and t_u disagree, t_u wins both events** (T10).
   - The unit-clustered version agrees: r_u 6/7, t_u 5/5, q_lik 7/8.
2. **L1a (the TAIL-EMPTY events) is DESCRIPTIVE.** r_u hits 5 of 5 (T05 FD, T11 FD and PN, T2 FD and PN;
   p = 0.0052, Holm 0.026). That is one event below the frozen 6-event bar. q_lik also hits all 5, so the base model
   adds nothing here that the tuned model's own likelihood lacks.
3. **The log-score contest is not robust to how the 'other' bin is handled.**
   - **Primary (frozen; each forecast's 'other' bin as defined in the plan).** q_base trails both rivals and is not
     non-inferior to q_tail:
     - q_base − q_tail = **−0.44 nats** per program, BCa 95% CI [−0.97, 0.09];
     - q_base − q_lik = **−0.39 nats** [−1.00, 0.08].
   - **Sensitivity: one fixed 0.02 'other' bin for every forecast.** The sign flips:
     - q_base − q_tail = **+0.19** [−0.07, 0.52], which is non-inferior;
     - q_base − q_lik = **+0.36** [0.07, 0.64], exact Wilcoxon p = 0.015.
   - **Sensitivity: 'other' excluded.** The same picture: +0.19 and +0.38.
   - **What drives the flip.** On T1, T2 and T10 most base attempts are broken code labelled 'other'. That gives
     q_base 0.81–0.87 of its mass on 'other'.
   - **Rivals beaten in every version.** q_base beats exp28's association forecast (+0.66 nats, p = 0.076). It also
     beats the raw-sum q_lik (+0.64), which is far too peaked.
4. **Iteration 5's 5-of-7 tally, rescored under repaired support.**
   - The repaired r_u scores 5/7, or 5/6 on the events where it is defined.
   - **T03's runner-up disappears.** The base model's 53 correct T03 programs are all the default (full_sort), so
     the frozen correct-only rule leaves r_u undefined. Iteration 5's quickselect rested on broken attempts.
   - t_u scores 5/5 where defined, and q_lik scores **6/7** (it misses only R6).
   - The tuned model's own tail and likelihood both name iteration 5's two misses: T03 → size_k_heap and
     T10 → union_find.
5. **Base support repaired, with caveats.**
   - **Support.** Few-shot plain completion lifts the base model to ≥ 20 correct programs on 9 of 15 tasks (for
     example T04 83, T05 54, T03 53, T06 51), against at most 18 in iteration 5. Its per-draw correct rate exceeds
     iteration 5's zero-shot 12% on 8 tasks. The path tasks and R1, R2, R3 stay at 0–3 correct programs, and T10
     reaches 19.
   - **Exemplar priming.** The family contrast is flagged (p < 0.01) on T1, T10, R3, T13 and R6. That makes T10's r_u
     **exemplar-sensitive**: bench exemplars give union_find, the right answer, while HumanEval+ exemplars give bfs.
     Excluding the exemplar-sensitive units T03 and T10, r_u hits 11/11.
6. **Labels.** The blind two-family audit of 225 base programs gives 0.86 (stratum-weighted, κ A–B 0.91). The r_u
   stratum gives only 0.70, so the gate fails.
   - The revision round re-judged 824 rows and relabelled 132.
   - T10 then passes (0.996). T2, R1, R3 and R2 are flagged AUDIT_FAIL; excluding them, r_u hits 9/11.
   - The it-model style re-gate agrees on 29/30.
7. **Fresh pushes are weaker than exp28's but land in the same places.**
   - **Directions.** 8 new directions at α 2 confirm escapes only on R6 and T04 (E_u 0.25) and on T05 and T11 (0.125).
   - **Plan noise.** Fresh per-sample plan noise moves R6 (0.42), T1 (0.38), T10 (0.20) and T04 (0.18).
   - **Fresh-only split** (outcomes unseen at commit #1): 11 events, with r_u 9/10, t_u 6/6 and q_lik 9/11.
8. **No new algorithm appears.**
   - **L2-G.** None of the 1,091 correct nudged off-default programs uses an algorithm absent from the base
     repertoire (rule-of-three bound 0.003).
   - **Novelty audit.** It finds 0 novel programs among 19 correct 'other' it programs (15 degenerate, 4 catalogue
     variants) and 0 among 5 base few-shot programs.

**Reading.** In Gemma, the iteration-5 lead (the base runner-up names the landing) survives as a hit rate. It does
not survive as evidence that the landing is absent from the tuned model. The tuned model's own likelihood ranks the
landing first on 13 of 15 events. Its own 300-sample tail names it whenever the tail is non-empty, including both
cases iteration 5 missed. The base model wins only where the tuned model's forecasts are silent or noisy, and there
q_lik wins as well. The log-score verdict depends on the 'other' bin, so it should be quoted with both scorings. All of
this is a replication on seen units. The LeetCode-derived tasks are memorised by both models, which is harmless for
this within-model comparison but rules out any claim of new capability.

Figures (PDF + PNG):
- `figures/fig1_pt_support.pdf`: base support per task, before and after the top-up;
- `figures/fig2_compositions.pdf`: q_base, q_tail and q_lik against the pooled landing composition per push unit;
- `figures/fig3_logscore_diffs.pdf`: per-event log-score differences, primary scoring;
- `figures/fig4_audit_agreement.pdf`: pt label-audit agreement, iteration 5 against iteration 6.

Integrity:
- **Engine check.** It matches exp28's rows on 0.99 of slots (twin 150/150), with JS 0 and byte identity 0.91.
- **Clean states.** U6 is bit-identical on 40/40.
- **Tests.** GPU tests U1–U9 and CPU tests T1–T12 pass.
- **q_lik checks.** The default ranks first on 13/15 units. The fp32 re-score of a 10% subsample flips no top-1, so
  the bf16 scores stand.
- **Re-derivation.** The stdlib-only `audit/rederive_l1.py` (system Python, no pipeline import) recomputes 36
  headline values from the raw label and teacher-forcing files with 0 mismatches. They include D_u, r_u, t_u,
  the q_lik top-1, the events, all hit counts and p values, both sign tests, both log-score scorings, the
  fresh-only split and the old tally. Placebos fail as required: a random r_u passes in 1.75% of draws, a
  random q_lik top-1 in 4.25%, and a random forecast never beats q_tail by 0.10 nats. Not re-derived: the
  bootstrap CIs, the Wilcoxon and sign-flip p values, and the judge-based audits.
