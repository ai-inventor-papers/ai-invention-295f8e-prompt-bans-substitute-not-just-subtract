# Fair test of Gemma's BFS dial (iteration 8, claim G)

**Question.** Iteration 7 (art_HY7uYZz-OjRW) found a rank-4 DAS subspace at block 17 of `google/gemma-3-4b-it`. Edited
once at the fork position after the shared 32-token opening c\*, it raised correct BFS programs for the grid-path task
T1 from 11/50 (twin) to 42/50 at lambda 1. It then compared this with a forced-BFS prompt that was sampled **without**
the c\* prefill (35/50), so the comparison mixed method and prefill. The review asked two things:

- item 3: a prompting baseline under matched conditioning;
- item 5: dormancy checks of the subspace.

This artifact runs the missing cells on the **same 50 common-random-number (CRN) slots**, giving the 2x2
{prompt, dial} x {c\* prefilled, free generation}. It adds a free-generation dial applied at a pre-committed
decision position, and runs the dormancy checks at ranks 1, 2, 4 and 8 with the rule already applied to Qwen3-8B
(art_veI9l_Rb9wDY).

One model (gemma-3-4b-it, bf16), one task (T1), one fork. This is a case study, so every claim is worded "at Gemma's
grid fork".

## Short answer

1. **Prefill-matched prompting collapses.**
   - The forced-BFS prompt with c\* prefilled (G1a) writes BFS 50/50 times but **0/50 correct** (pass 0.00).
   - The best alternative wording (G1d, F3) also gives 0/50. Committed P1 (>= 40/50, set in commit #0) fails.
   - Cause: c\* is very unlikely under the forced-BFS prompt (log P(c\* | prompt) = -11.3 to -14.1 nats, against
     -0.11 to -0.17 under the twin and forced-DFS prompts). Prefilling it drives the fork token to ` queue` (50/50).
   - That opening writes `queue = [(start, [start])]` with no wall check of start or goal. Every program fails the
     hidden case `one_by_one_wall` with a wrong answer, not a timeout.
   - The teacher-forced fork account predicted this before any G1 sample (commit #1): 1.0/50 correct and 49.97/50
     attempted BFS.
   - So the dial beats prefill-matched prompting, 39 vs 0 discordant slots (two-sided exact McNemar p = 3.6e-12).
     **The prefill is a confound, but it hurts the prompt, not the dial.**
2. **The dial works in free generation (P2 holds).** Applied at the committed decision position:
   - 47/50 slots reproduce c\* (R1, i_d = 32); 3 never reach a qualifying position.
   - The free DAS dial (rank 4, lambda 1) gives **38/50 correct BFS** against 13/50 for the free twin (26 vs 1
     discordant, p = 2.1e-7). Pass is 0.78 against 0.88 (paired difference -0.10, Newcombe 95% -0.22 to +0.01).
   - It is not distinguishable at N = 50 from the prefilled dial (39/50; 2 vs 1 discordant, p = 1.0; paired
     difference +0.02, -0.06 to +0.11).
   - All four free DAS cells beat the free twin (Holm p <= 2e-5).
   - It holds on held-out templates: W4/W5 plus 30 fresh slots give 33/50 vs 11/50 (p = 5e-6).
3. **In free generation, the dial does not beat prompting.**
   - Against the committed free prompt (G1c, F5: 32/50, pass 0.64): 11 vs 5 discordant, p = 0.21. Not
     distinguishable at N = 50.
   - Across 8 forced-BFS wordings (exploratory, commit #3), free prompting gives 14 to 49 correct BFS (mean 39.5).
   - The best wording ("Use breadth-first search (BFS) throughout.") beats the dial: 49 vs 38, Holm p = 0.024.
   - This matches AxBench's prior that prompting beats steering.
   - The slot-bootstrap interaction (dial - prompt | prefilled) - (dial - prompt | free) is **0.66** (95% 0.50 to
     0.82).
4. **Dormancy (G3).**
   - By the committed rule shared with Qwen3-8B, the subspace is **DORMANT/OFF-MANIFOLD HANDLE at every rank**.
   - The flag comes through the retention arm only. Projected on the top 64 principal components (PCs) of the
     twins' natural block-17 fork states, it keeps 0.28 / 0.23 / 0.21 / 0.18 of its effect (k = 1 / 2 / 4 / 8).
     The orthogonal residual keeps 0.51 to 0.55.
   - The reverse arm does not flag: forced-BFS base <- twin source gives reverse recovery 1.53 / 1.74 / 2.13 / 2.39
     (95% CI at k = 4: 1.98 to 2.36). Haar null about 0, DAS at the 100th percentile.
   - Natural variance is low at k = 1, 2, 4: share 0.0009 / 0.0011 / 0.0018 against random p95 0.0010 / 0.0018 /
     0.0027, so iteration 7's prediction holds. At k = 8 it is above p95.
   - The flag is specific to the twin-only natural set. Add the 40 forced sources and the same projection keeps
     0.62 / 0.53 / 0.46 / 0.39, the orthogonal residual carries 0.00, and the variance share is about 50x the random
     95th percentile.
   - Reading: R_k is almost unused by the twins' own (noun-driven) variation, but it lies inside the variation that
     prompts induce.
   - The account's prediction (reverse >= 0.5 **and** retention >= 0.5 at k = 4) fails on retention.
   - Reverse generation (N = 30) is UNDEFINED: even replacing the whole block-17 fork state restores 0 DFS programs.
5. **What the subspace carries (exploratory layer sweep, commit #4).**
   - At block 17, a full-state transplant of the forced-BFS fork state into the twin sets p(` queue`) to 0.55.
   - The rank-4 DAS edit reaches the same BFS margin (about 12 nats) with p(` queue`) only 0.006 to 0.07; its BFS
     mass sits on newline/`if`, which are the wall-check-first openings.
   - DiM at the same teacher-forced effect puts 0.94 to 0.98 on ` queue` and destroys the programs (free
     generation: 0/50 correct, pass 0.00, P6 holds).
   - Under the forced prompt, ` queue` is overwritten only by swaps at blocks 22 and later.
   - **The subspace moves the algorithm (BFS vs DFS) but not the forced prompt's implementation choice.**
6. **No novel algorithm.**
   - Of 913 correct programs in all cells, none is labelled 'other' (rule-of-three bound 0.0033).
   - A blind style re-gate agrees with the frozen labeller 30/30 (its judge passed 12/12 references).

## Pre-registered scorecard (commit #0; P7 from commit #1's teacher-forced numbers)

| | Prediction | Observed | Holds |
|---|---|---|---|
| P1 | G1a (forced-BFS F5 + c\*) correct BFS >= 40/50 | 0/50 (attempted 50/50, pass 0.00) | **no** |
| P1b | P-DAS-bfs vs G1a not distinguishable (two-sided McNemar p >= 0.05) | 39 vs 0, p = 3.6e-12: DIAL BEATS MATCHED PROMPTING | **no** |
| P2 | free DAS r4 lam1 >= 30/50, pass >= 0.8 x free twin, > free twin | 38/50, pass 0.78 >= 0.70, vs 13/50 p = 2.1e-7 | **yes** |
| P3 | reach share (R1 or R2) >= 0.80; R1 about 0.86 | 0.94 (all R1) | **yes** |
| P4 | R1-slot free/prefilled label agreement >= 0.90 (twin and DAS) | twin 0.894 (42/47), DAS 0.979 (46/47) | **no** (twin, by 0.006) |
| P5 | account: reverse >= 0.5 and retention >= 0.5 at k = 4; iteration 7: low variance at k = 1, 2, 4 | reverse 2.13, retention 0.21; low variance at k = 1, 2, 4 | account **no**; iteration-7 numbers **yes** |
| P6 | free DiM toward BFS: pass < 0.8 x free twin | pass 0.00 | **yes** |
| P7 | TF-predicted attempted BFS within 0.10 in every prefilled cell | max gap 0.068 (P-twin 0.23 vs 0.30) | **yes** |

Verdicts by the committed rules: **G-PROMPT** = P1 fails and the outcome is "DIAL BEATS MATCHED PROMPTING"; **G-FREE** =
"free-generation knob"; **G-DORMANCY** = DORMANT/OFF-MANIFOLD HANDLE at k = 1, 2, 4, 8 (through the retention arm; see
the sensitivity below before reading it as "unused").

## Results

### The 2x2 toward BFS (same 50 CRN slots: W1-W5 x 10, iteration 7's streams; T 1.0, top-p 1, max_new 1024)

| Cell | What | Attempted BFS | Correct BFS (Wilson 95%) | Pass | ` queue` at index 32 |
|---|---|---|---|---|---|
| P-twin | twin + c\* prefilled | 15 | 10 (0.11-0.33) | 0.88 | 0.04 |
| G1a | forced-BFS F5 + c\* prefilled | 50 | **0** (0.00-0.07) | 0.00 | 1.00 |
| G1d | best TF wording (F3) + c\* prefilled | 50 | 0 (0.00-0.07) | 0.00 | 1.00 |
| P-DAS-bfs | twin + c\*, DAS r4 lam 1 at p_f | 47 | **39** (0.65-0.87) | 0.82 | 0.00 |
| F-twin | twin, free from index 0 | 18 | 13 (0.16-0.40) | 0.88 | 0.00 |
| G1c | forced-BFS F5, free from index 0 | 50 | 32 (0.50-0.76) | 0.64 | 0.00 |
| F-DAS-r4-bfs-1.0 | twin, free, DAS r4 lam 1 at i_d | 48 | **38** (0.63-0.86) | 0.78 | 0.00 |

Paired exact McNemar on correct BFS (discordant counts, first cell only / second cell only):

| Contrast | Discordant | p | Paired difference (Newcombe 95%) |
|---|---|---|---|
| dial vs prompt, prefilled (P1b) | 39 / 0 | 3.6e-12 (two-sided) | +0.78 (0.63 to 0.87) |
| dial vs prompt, free | 11 / 5 | 0.21 (two-sided) | +0.12 (-0.04 to +0.27) |
| dial: prefilled vs free | 2 / 1 | 1.0 | +0.02 (-0.06 to +0.11) |
| prompt: prefilled vs free | 0 / 32 | 4.7e-10 | -0.64 (-0.76 to -0.48) |
| twin: prefilled vs free | 1 / 4 | 0.38 | -0.06 (-0.16 to +0.04) |
| interaction (slot bootstrap, 10,000) | - | - | **0.66 (0.50 to 0.82)** |

**Why prefill-matched prompting fails (fork-token diagnostics, `results/analysis.json`).**

- P(c\* | prompt), from 3b:
  - 0.85-0.89 under the five twins and 0.85-0.90 under the forced-DFS prompts;
  - 1e-6 to 1e-5 under the forced-BFS prompts.
- With c\* forced, p(` queue`) at the fork is 0.96-0.998 for all five forced-BFS wordings.
- G1a: 50/50 programs take ` queue`, and all 50 fail the frozen hidden tests with `expected []` on a wall case. The
  path-carrying list BFS returns `[start]` when start is a wall.
- Iteration 7 attributed the 0/125 pass of ` queue` programs to slowness; re-running its tests shows the failure is
  this missing wall check (deviation D-iter7-cause).
- In free generation the forced prompt never writes c\*: index 32 is `[`, inside `from collections import deque`, in
  46/50 programs.
- Forced-DFS + c\* is natural, and G1b gives 50/50 correct DFS.

### Free-generation dial (decision positions committed in #2 before any edited sample)

- Decision rule: R1 if the free twin reproduces c\* (i_d = 32). Otherwise R2: the first index in [8, 96] after the
  body-indent token where p_B + p_D >= 0.5, p(` visited`) >= 0.01, and no algorithm-identifying string has appeared.
- **47/50 slots are R1, 0 are R2, 3 are NOT_REACHED** (73 R1 and 7 not reached over S50 + HT30). The not-reached
  openings left a blank line and committed to a validity check before any live ` visited` decision.
- They get no edit and are scored as is. The literal rule (first p_B + p_D >= 0.5) fires at index 2 in 80/80 slots,
  as anticipated.
- Prefix check: 0/480 edited rows differ from the free twin before i_d.
- U3′: with the edit, the decode-time margin at index 32 is 0.42 nats above the prefilled path (12.09 vs 11.67 at
  W1). Without the edit the offset is 0.002 at W1 and 0.19 at W5.

| Free cell (S50) | Correct target | Pass | vs free twin (one-sided McNemar) | Commit #2 prediction |
|---|---|---|---|---|
| F-twin | 13 BFS | 0.88 | - | 10.0 |
| DAS r4 lam 1 -> BFS | 38 | 0.78 | 26/1, Holm p = 8.3e-7 | 37.0 |
| DAS r4 lam 0.5 -> BFS | 34 | 0.72 | 22/1, Holm 5.7e-6 | 30.6 |
| DAS r1 lam 1 -> BFS | 35 | 0.72 | 23/1, Holm 4.5e-6 | 31.1 |
| DAS r1 lam 0.5 -> BFS | 31 | 0.68 | 19/1, Holm 2.0e-5 | 27.7 |
| DAS seed 2 r4 lam 1 -> BFS (optional) | 41 | 0.82 | 28/0, p = 3.7e-9 | 33.5 |
| RAND rank 4, lam 1 (optional) | 11 | 0.84 | 1/3, p = 0.94 (null) | 6.9 |
| DiM (matched, beta 1380) -> BFS | **0** (attempted 49) | **0.00** | 0/13 | 1.4 |
| DAS r4 lam 1 -> DFS | 47 DFS | 0.94 | 16/0, p = 1.5e-5 | 47.0 |
| DiM (matched, beta -839) -> DFS | 47 DFS | 0.94 | 16/0, p = 1.5e-5 | 46.5 |

- **Held-out templates:**
  - W4/W5 (20 S50 slots) + HT30 (30 fresh W4/W5 slots): free DAS 33/50 vs free twin 11/50 (24 vs 2 discordant,
    p = 5.2e-6).
  - HT30 alone: 20/30 vs 6/30.
  - Train templates W1-W3: 25/30 vs 8/30.
- **Pass cost of the free dial** against the free twin: -0.10 (Newcombe -0.22 to +0.01). Of its 20 failing programs
  over S50 + HT30, 15 are timeouts of slow BFS variants and 5 are wall-case wrong answers.
- **P4 (decode vs prefill on R1 slots):**
  - Twin pair: label agreement 0.894, byte-identical 0.62.
  - DAS pair: 0.979, byte-identical 0.85.
  - The twin misses 0.90 by one slot. This is the U3′ path difference (c\* decoded token by token vs prefilled) acting
    on near-even forks.

### Free-generation prompting across wordings (exploratory, commit #3; best-of-8 is selected post hoc)

| Forced-BFS wording (free, from index 0) | Correct BFS | Pass | vs free dial (38): dial-only / prompt-only, p |
|---|---|---|---|
| F1 "Use breadth-first search (BFS) for this task." | 40 | 0.80 | 6 / 8, p = 0.79 |
| F2 "Your solution must rely on breadth-first search (BFS)." | 45 | 0.90 | 2 / 9, p = 0.065 |
| F3 "Use breadth-first search (BFS) throughout." | **49** | 0.98 | 1 / 12, p = 0.0034 (Holm 0.024) |
| F4 "Breadth-first search (BFS) is required here." | 14 | 0.28 | 25 / 1, p < 1e-5 |
| F5 "... uses breadth-first search (BFS)." (= G1c) | 32 | 0.64 | 11 / 5, p = 0.21 |
| F5 "... uses BFS." | 44 | 0.88 | 3 / 9, p = 0.15 |
| F5 "... uses breadth-first search." | 45 | 0.90 | 2 / 9, p = 0.065 |
| F5 "... uses a breadth-first search." | 47 | 0.94 | 2 / 11, p = 0.022 |

Mean over wordings 39.5/50. The prompting baseline is highly wording-sensitive (14-49), and the dial (38) sits in the
middle of that range. No wording is prefilled, so none of these programs takes ` queue`.

### Toward DFS

| Cell | Correct DFS | Pass |
|---|---|---|
| P-DAS-dfs (twin + c\*, DAS -> DFS) | 50/50 | 1.00 |
| G1b (forced-DFS F5 + c\*) | 50/50 | 1.00 |
| F-DAS-r4-dfs-1.0 (free) | 47/50 | 0.94 |
| F-DiM-dfs (free, matched) | 47/50 | 0.94 |

All four beat their twin (16 vs 0 discordant, p = 1.5e-5). On this engine the DiM-DFS beta bisects cleanly to -838.5
(matched). Iteration 7's D17 bug is gone: the grid scan is monotone.

### Dormancy at block 17 (G3; seed 0 for the rule; teacher-forced, single-position KV path, fixed batch 48)

| k | Forward recovery (768 held-out pairs; median ratio) | Reverse recovery, held-out (95% CI) | Retention, 64 PCs of 120 twins (95% CI) | Residual orth. to them | Retention, 64 PCs of twins + 40 forced | Natural share / random p95 (percentile) | Max seed cosine | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | 2.04 | 1.53 (1.42-1.70) | 0.28 (0.27-0.29) | 0.51 | 0.62 | 0.00088 / 0.00096 (94) | 0.36 | DORMANT/OFF-MANIFOLD |
| 2 | 2.36 | 1.74 (1.63-1.92) | 0.23 (0.23-0.24) | 0.52 | 0.53 | 0.00110 / 0.00176 (81) | 0.44 | DORMANT/OFF-MANIFOLD |
| 4 | 2.54 | 2.13 (1.98-2.36) | 0.21 (0.20-0.21) | 0.54 | 0.46 | 0.00182 / 0.00267 (73) | 0.52 | DORMANT/OFF-MANIFOLD |
| 8 | 2.79 | 2.39 (2.21-2.66) | 0.18 (0.17-0.18) | 0.55 | 0.39 | 0.00530 / 0.00479 (98) | 0.60 | DORMANT/OFF-MANIFOLD |

- **Forward recovery** reproduces iteration 7 (seed medians 1.98 / 2.36 / 2.58 / 2.81 there; seed 0 here 2.04 / 2.36
  / 2.54 / 2.79).
- **Reverse test.**
  - Bases: forced-BFS F4/F5 x 4 display names + c\*. Sources: the 24 twin variants of the aligned template.
  - The same-site full-state reverse moves the margin -2.62 nats (|denominator| >= 0.5, so the ratio is defined).
    The DAS reverse moves it -5.58 at k = 4, more than the full-state swap.
  - 50 Haar rank-k subspaces give about -0.02, so DAS is at the 100th percentile.
  - The late-band reverse (blocks 17-33 replaced) moves it -10.4, and DAS is 0.54 of that at k = 4.
  - Train bases F1-F3 agree (1.99 / 2.27 / 2.83 / 3.19).
- **Retention.** The 32- and 100-PC sensitivities give 0.10 and 0.34 at k = 4. The dial version of retention (class-mean
  edit, 72 train bases + 5 twins) is 0.15. The planted checks pass: a direction inside the span gives fraction 1.000
  and retention 1.000, an orthogonal one gives fraction 0.000.
- **Natural variance.**
  - On iteration 7's cached states it reproduces iteration 7 to 1.1e-9.
  - Per-direction projection SD over the random-direction SD (Makelov's spread check): 1.6 / 0.81 / 0.84 / 1.18 for
    the four rank-4 directions on the twins; 12.3 / 5.6 / 4.1 / 4.2 with the forced sources.
- **Principal cosines** between seeds: one shared direction (0.50-0.60 at k = 4 and 8); the rest are below 0.15.
- **Fraction of R_k inside the 64 twin PCs** (the plan's `pca_upper`): 0.10 / 0.07 / 0.05 / 0.04. The top-k PC
  variance share of the natural set (E33's `pca_upper`) is 0.55 / 0.65 / 0.75 / 0.84.
- **Reverse generation** (N = 30, rank 4, forced-BFS F5 + c\* <- twin state at p_f): 0/30 DFS for REV-DAS and for
  REV-FULL, so restoration_gen is UNDEFINED (denominator 0 <= 2). All 30 programs in both cells still take ` queue`.

### Layer sweep (exploratory, commit #4; `results/layer_sweep.json`, F7)

- **Twin + c\* base, single-block full-state transplant of the forced-BFS fork state:** p(` queue`) is 0.06-0.09 up
  to block 14, 0.43 at block 15, 0.55 at block 17 and 0.94-0.98 from block 26.
- **Forced-BFS + c\* base with the twin's state:** p(` queue`) stays at 0.96-0.99 up to block 21 and falls only from
  block 22 (0.88, 0.79 at 24, 0.34 at 26, 0.06 at 33).
- **The block-17 DAS dial** (twin + rank-4 edit) has p(` queue`) 0.01-0.07 at a margin of 11-13 nats.
- **DiM at the same margin** has 0.94-0.98.

### Engine, unit tests, labelling

- **Engine check** (RTX 4090 vs iteration 7's RTX 2000 Ada; same slots, B = 25):
  - P-twin 10/50 (iteration 7: 11), label agreement 0.94, byte-identical 0.54;
  - P-DAS-bfs 39/50 (42), agreement 1.00, byte-identical 0.78;
  - G1c 32/50 (35), agreement 1.00.
  - Agreement is below 0.95 for the twin, so this is logged as kernel sensitivity. Every contrast is computed inside
    this engine.
  - Recomputed fork states differ from iteration 7's by up to 1.3% in norm (0.73 nats in margin).
- **Unit tests:**
  - U1: CRN determinism holds.
  - U2: bit-identical identities (DAS lam 0, target = own coordinates, full exchange with source = base).
  - U4′: unscheduled rows are bit-identical, and scheduled rows are identical before the edit step.
  - U3′: 0.42 nat offset (above the 0.3 tolerance; logged).
  - U5: decision-rule tests pass.
  - S0: the labeller labels 12/12 references, 5/5 mutants fail, and 44/44 copied inputs match their sha256.
- **Labelling:**
  - 1,320 programs, labelled by the frozen exp8 T1 labeller (hidden tests, runtime tracer, AST).
  - Runtime and AST agree on 1,254. The other 66 came from the blind judge (openai/gpt-4.1-mini); most were cache hits
    from iteration 7's judge cache.
  - 0 truncated programs and 0 'other' labels.
- **Spend:** OpenRouter USD 0.0042 in total (labeller judge 0.0025, re-gate 0.0017). GPU about 14 minutes in all.

## Audit

- **Hash chain.** `audit/verify_chain.py` (standard library) re-derives every chain value. It checks the ordering:
  - commit #0 precedes every sample;
  - #1 precedes the G1 and reverse rows;
  - #2 precedes the edited free rows;
  - #3 precedes the wording extension.

  See `results/verify_chain.json`.
- **Re-derivation.** `audit/rederive.py` (standard library) re-derives 139 quantities from `data/labels.jsonl` with **0
  mismatches**: every cell count, every headline McNemar p, Holm, the interaction, the scorecard booleans,
  restoration_gen, the dormancy verdicts and engine agreement. See `results/rederive.json`.
- **Independent raw re-derivation.** `audit/rederive_raw.py` re-scores the 8 headline cells (400 programs) from the
  raw generated text, sharing no code with the pipeline. It uses its own code extraction, its own stdlib test runner
  and path checker, a structural BFS/DFS classifier, and SciPy's binomtest for McNemar.
  - Pass counts, correct counts, all five headline McNemar tests and the interaction (0.66) are identical.
  - The classifier agrees with the labeller on 400/400 programs.
  - Within-slot permutation placebos give p < 0.05 in 0-3.1% of 1,000 permutations.
  - See `results/rederive_raw.json`.
- **Placebos.**
  - Within-slot cell-label swaps make the dial-vs-twin and dial-vs-G1a tests significant in only 1.5% and 1.4% of
    1,000 swaps.
  - The shuffled 2x2 interaction has mean 0.004 and |95th percentile| 0.26, against the observed 0.66.
  - Slot-shuffled (unpaired) p-values are reported beside the paired ones.

## Positioning (dated searches 2026-10-23, `results/positioning.json` with verbatim quotes)

- **CDAS** (arXiv 2602.05234, ICLR 2026) already occupies DAS-based steering validated by generation, and compares it
  with prompting. **Prefix Steering** (arXiv 2610.04967, 4 Oct 2026) is the closest prior: "intervention over a
  short span, even a single token, often retains much of full steering's behavioral control". This artifact's
  differences:
  - a causally localised DAS subspace;
  - CRN-paired prefill-matched prompting cells;
  - a decision position read off the model's own trajectory;
  - hidden-test program correctness;
  - the dormancy and implementation-channel analysis.
- **AxBench** (2501.17148) supplies the prior that prompting beats steering, which the free-generation results here
  reproduce.
- **Makelov et al.** (2311.17030) and the divergent-representations paper (2511.04638) frame the retention result.
- **DecodeShare** (2607.20469) frames the decode-vs-prefill offset.
- Permitted wording: "at Gemma's grid fork, a one-shot DAS edit at the decision token works in free generation as it
  does after a prefill; prefill-matched prompting fails because the prefill is off-policy for the prompt; in free
  generation the dial is within the range of prompt wordings". Not permitted: "first single-token steering",
  "steering beats prompting".

## Deviations (`results/deviations.json`)

- **D-gpu.** The GPU is an RTX 4090 (24 GB), not the planned RTX A4500. B_CRN = 25 is kept.
- **D-engine.** Engine-check label agreement is 0.94 for the twin, below 0.95: kernel sensitivity. Continued as
  committed.
- **D-U3p.** The decode-time hook is offset by 0.42 nats from the prefilled path, above the 0.3 tolerance. Logged, not
  fatal; P4 measures the consequence.
- **D-maxnew.** max_new is 1024, not 1,536, to keep iteration 7's cells reproducible. 0/1,320 programs were truncated.
- **D-seed.** Generation uses DAS seed 0 (the map on record). Seed 2 runs as an optional free cell: 41/50.
- **D-rule.** The refined decision rule is used. The literal rule is reported; it fires at index 2 in every slot.
- **D-targets.** For seed 0 at k <= 4, the class targets are commit3's coordinates; elsewhere they are recomputed on
  this engine. They differ by at most 0.74 residual units.
- **D-method-edit.** `method.py` gained stages after commit #0: the decision-state capture for F4, and the
  exploratory stages `gpu_extra` (commit #3) and `tf_extra` (commit #4). No committed statistic or rule changed.
- **D-pool.** The stage-0 known-solution pool missed TheAlgorithms, whose code sits in `input`. It was rebuilt in the
  novelty stage: 2,158 graph-, grid- or path-related programs from 7 code-bearing datasets.
- **D-pca-upper.** Two `pca_upper` quantities are reported (the plan's and E33's). The rule uses retention, not
  either of them.
- **D-iter7-cause.** Iteration 7's explanation for the 0-pass ` queue` programs (slowness) is corrected: they fail on
  a missing wall check.
- **Not re-run, as planned:** DAS refits, SHUF, RINIT. Iteration 7's passed controls stand.
- **Not attempted:** the transcoder graph.

## Layout

| Path | What |
|---|---|
| `method.py` | Entry point, one stage per `--stage`: `s0`, `gpu1`, `commit2`, `fcells`, `gpu_extra`, `tf_extra`, `label`, `novelty`, `positioning`, `analysis`, `figures`, `outputs`. |
| `src/cfg8.py` | Iteration-8 design: cells, slots (S50, S30, HT30), thresholds and committed decision rules. |
| `src/gen8.py` | `decode8` (iteration 7's CRN sampler plus decode-time per-row edits at a response index, per-step fork records and forced tokens for U3′), `FreeRunner.run_cell_free`, the decision-position rule. |
| `src/tf8.py` | Teacher-forced stage: 3a fork distributions, 3b log P(c\*), 3c DiM grid scan and bisection, 3d dormancy (forward, reverse with Haar null, projected retention and residual, natural variance, principal angles). |
| `src/analysis8.py` | Statistics committed in #0: Wilson, exact McNemar, Holm, Newcombe paired, slot bootstrap, cell summaries, decomposition, P1-P7, dormancy verdict, iteration-7 reproduction. |
| `src/outputs8.py` | Novelty audit and style re-gate, diagnostics (fork tokens, failure reasons, engine check), figures F1-F7, `data/samples.jsonl`, `method_out.json`. |
| `src/positioning8.py` | Positioning entries with verbatim quotes. |
| `src/*.py` (others) | Iteration 7's vendored engine, prompts, fork context, DAS machinery, labeller wrapper, hash chain (unchanged; sha256 in `inputs/input_hashes.json`). |
| `inputs/iter6_gemma/` | Iteration 6's prompts, nouns, fork table and the frozen exp8 T1 suite (spec, hidden tests, references, labeller), with `MANIFEST.sha256` (133/133 match). |
| `inputs/iter7/` | Copied iteration-7 results, commit0/commit3, the dose-sweep raw rows and labels, and E33's `dormant.json`. |
| `cache/das_subspaces/` | Iteration 7's DAS maps (3 seeds), DiM and SHUF maps. |
| `cache/states/` | Iteration 7's fork states (deleted after the round; see below). |
| `cache/decision_states.pt` | Block-17 states at the free twin's decision positions (this run). |
| `cache/known_pool.json` | Known-solution pool. |
| `predictions/`, `commitments.log` | Hash-chained commits #0 (design, rules, P1-P7), #1 (TF predictions, DiM betas, dormancy TF tables, REV design), #2 (decision positions, decomposition predictions), #3 and #4 (exploratory designs); `hardware.json`. |
| `data/raw_*.jsonl` | Every generated program with token ids, edit logs and CRN keys: `engine`, `g1`, `ftwin`, `fcells`, `rev`, `g1e`. |
| `data/steps_free.jsonl` | Per-step fork records (p_B, p_D, p(` queue`), m, top-1) for indices 0-96 of every free row. |
| `data/labels.jsonl`, `data/samples.jsonl` | One label row per program; `samples.jsonl` has the plan's fields (arm, site, layer, rank, dose, decision_pos, reach_type, prefix_match, fork token, label, pass, code). |
| `data/prefix_check.jsonl`, `data/judge_cache_paths.jsonl` | Prefix checks; judge cache (seeded from iteration 7's). |
| `results/` | `analysis.json` (cells, tests, scorecard, verdicts, diagnostics), `tf_stage.json`, `dormancy.json`, `layer_sweep.json`, `tests_gpu.json`, `s0_tests.json`, `novelty_audit.json`, `positioning.json`, `rederive.json`, `verify_chain.json`, `deviations.json`, timings, costs. |
| `figures/` | F1-F7 (PNG + PDF), listed below. |
| `method_out.json`, `full_/mini_/preview_method_out.json` | exp_gen_sol_out output, validated. Datasets: `engine_check` (100), `g1_prefill_matched` (50), `g2_free_dial` (80), `g3_reverse_gen` (30), `g3_dormancy` (24). `metadata.results` holds every results file. |
| `audit/` | `verify_chain.py`, `rederive.py` (standard library only); `rederive_raw.py` (independent re-scoring of the headline cells from raw text). |
| `reproducibility.md` | Step-by-step reproduction: environment, variables, commands, expected numbers. |
| `restore.sh`, `.aii/manifest.yaml` | Restores the deleted bulk (`.venv/`, `cache/states/`); the per-path keep/delete decisions. |
| `logs/` | Stage logs, batch timings, OpenRouter spend, positioning search results. |

Figures:

| Figure | What it shows |
|---|---|
| F1 | The 2x2 with Wilson CIs, plus the 8 free wordings as dots. |
| F2 | Decision-position histogram and free cells by reach type against the commit #2 predictions. |
| F3 | Dormancy by rank: Haar violins, retention and residual, forward and reverse recovery. |
| F4 | Geometry in actual block-17 activation coordinates, on the (R_1, R_2) and (PC1, PC2) planes. |
| F5 | Seed principal cosines. |
| F6 | Fork-token mix by cell. |
| F7 | Layer sweep of p(` queue`) and the margin. |

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
bash restore.sh                                   # copies iteration 7's fork states back into cache/states/
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
.venv/bin/python method.py --stage s0             # CPU tests + COMMIT #0 (write-once: delete predictions/ to re-commit)
.venv/bin/python method.py --stage label --follow &   # CPU label worker (stop: touch data/STOP_LABELLER)
.venv/bin/python method.py --stage gpu1           # unit tests, engine check, TF stage + COMMIT #1, G1, F-twin, REV
.venv/bin/python method.py --stage commit2        # waits for labels, decision positions, COMMIT #2
.venv/bin/python method.py --stage fcells         # edited free-generation cells
.venv/bin/python method.py --stage gpu_extra      # exploratory: free prompting across wordings (COMMIT #3)
.venv/bin/python method.py --stage tf_extra       # exploratory: layer sweep (COMMIT #4)
for st in novelty positioning analysis figures outputs; do .venv/bin/python method.py --stage $st; done
python3 -I audit/verify_chain.py && python3 -I audit/rederive.py && .venv/bin/python audit/rederive_raw.py
```

Hardware used: one NVIDIA RTX 4090 (24 GB), 14 CPUs, 56 GB RAM (container). GPU time is about 14 minutes; the
whole pipeline runs in about 45 minutes. The model (`google/gemma-3-4b-it` at revision
`093f9f388b31de276ce2de164bdc2081324b9767`) was read from the run's shared Hugging Face cache. The OpenRouter judge
calls need `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY`. The declared dependency art_j3Rm_lr2nzR6
(`full_data_out.json`: all 10 datasets are loaded for the known-solution pool and usage summary) is found relative to
the run volume. Each input artifact is read through one constant, `method.py: artifact_dir()`. It is looked up as
`AII_ART_J3RM_LR2NZR6`, `AII_ART_HY7UYZZ_OJRW` or `AII_ART_VEI9L_RB9WDY`, else the sibling folder named by the
artifact id, else the run-volume layout. `reproducibility.md` has the full step-by-step instructions.

## Restoring removed files

`.aii/manifest.yaml` marks these for deletion after the round:

- **`.venv/` (about 11 GB):**
  `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml`
  (torch 2.8.0+cu128, transformers 4.57.6; every package is pinned in `pyproject.toml`).
- **`__pycache__/` directories:** recreated automatically by any Python run.
- **`cache/states/`** (iteration 7's fork states, 14-42 MB per file, copied read-only): `bash restore.sh`. It copies
  them from iteration 7's kept artifact (art_HY7uYZz-OjRW, `cache/states/`) next to this workspace on the run volume
  and verifies their sha256 against `inputs/input_hashes.json`. Without that artifact, rebuild them with iteration
  7's `method.py --stage yv` (about 2 GPU-minutes).
- **Model weights:** not stored here.
  `huggingface-cli download google/gemma-3-4b-it --revision 093f9f388b31de276ce2de164bdc2081324b9767`.

Everything else (code, raw generations, labels, results, figures, `cache/das_subspaces/`, `cache/decision_states.pt`)
is kept on the run's volume at these paths, and none of it exceeds the 100 MB publish limit. Suggested upload-ignore
patterns for the published repository: `(^|/)\.venv/`, `(^|/)__pycache__/`, `(^|/)cache/states/` and
`(^|/)\.repl_agent\.ptylog$`.
