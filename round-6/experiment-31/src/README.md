# Panel I: does the base model forecast where content-free nudges move Qwen3-8B's algorithm?

Iteration 6, Step 3 (Claim **L** primary, **M** and **K** secondary), panel I of two, on **Qwen3-8B** (instruct,
revision `b968826d`) and **Qwen3-8B-Base** (revision `49e3418f`). Every row is W16A16 (bf16), thinking off, and both
models read the identical chat-templated token ids.

**Claim L.** When a content-free push (an isotropic random direction added to the task-specification states at
blocks 12-23, or noise on the first 32 generated tokens) moves the instruct model off its default algorithm, the
algorithm it lands on is the one the **base model** ranks next (its runner-up `r_u` / composition `q_base`), better
than rivals built from the tuned model itself: its own sampled minority modes (`q_tail`, `t_u`) and its likelihood
ranking of the alternatives (`q_lik`, teacher-forced openings of verified forced programs). Chance is uniform over the
surviving algorithms. All forecasts of a unit were sha256-committed (`commitments.log`) before that unit's first nudge
row. With one panel of about ten units, L1a, L1b and M are **descriptive here**; the frozen `pool_l1.py` pools panels I
and II next round.

## Results (panel I)

**What happened.** All ten list-I units were built, gated and enrolled (nine passed gate (ii) at the first attempt,
I10 after its single revision round); no unit, arm or N was dropped by the clock. The instruct model is strongly
collapsed: 7 of the 10 units have an **empty tail** (zero correct non-default programs among 300 twin samples). Pushes
rarely moved it: only **7 of the 30** (unit, nudge type) pairs produced a landing event (>= 5 correct off-default
catalogue programs in pass-rate-gated cells), on four units (I2, I5, I6, I7); the escape fraction E_u is 0 for six
units.

- **Where nudges did land, the base runner-up named the landing in 5 of 7 events** (I2 ESC, I6 ESC, I7 ESC/PN/GTN).
  The two misses (I5 ESC and PN) landed on `min_heap_ends`, which is the tuned model's own minority mode (t_u) and its
  q_lik top-1, while the base runner-up was `sweep_events`. t_u named the landing in 5 of the 6 events where it is
  defined.
- **L1a (tail-empty events):** only 1 event (I6 ESC, a hit; Poisson-binomial p = 0.33). DESCRIPTIVE.
- **L1b (base vs q_lik where they disagree):** 6 discordant events; the base forecast alone hit 4 (I6 ESC, I7 ESC, PN,
  GTN), q_lik alone hit 2 (I5 ESC, PN); exact sign test p = 0.34. Under the frozen rule (n >= 6) this is a **FAIL**
  (not significant). The 6 events come from only 3 units; the unit-clustered version is 2 vs 1 (DESCRIPTIVE).
- **Log scores on the 7 matched events:** the base composition beats q_lik by +0.95 nats per program (one-sided 95%
  event-bootstrap lower bound +0.32; unit-cluster bound 0.00) and q_lik_raw by +16 nats (the raw-score softmax is
  near-degenerate). Against q_tail the mean is +0.25 nats, lower bound -0.05 per event (non-inferior at the -0.10
  margin) but -0.16 under the unit-cluster bootstrap (**not** non-inferior per unit).
- **L2:** 0 of 477 correct nudged off-default programs fell in a mode the base model never produced (rule-of-three upper
  bound 0.006). **Novelty:** 1 distinct correct 'other' program among 8,936 correct programs, judged a catalogue
  variant: no correct novel algorithm (bound 3/N = 0.00034 per correct program).
- **M (descriptive):** E_u is ranked by the frozen candidates twin modal share (Spearman -0.89, Holm p = 0.016, meets
  the frozen criterion) and base off-default share beta (+0.71, one-sided p = 0.014, Holm 0.07); E_u has six ties at
  0, so these rest on four moving units.
- **K:** plan noise at alpha 2 is nearly free (pass cost <= 4 points) but adds diversity mainly on the movable units
  (rarefied Hill-1 1.95 on I5 and 1.67 on I7, 1.10 on I1, 1.00 elsewhere); alpha 4 and the base-intent knob (BINT) raise rarefied Hill-1 on more units at larger pass costs (e.g. I1
  BINT 1.94 at 33 points, I8 BINT 2.06 at 10 points).

**Reading.** Panel I cannot decide Claim L. Its decisive ingredient, landing events on tail-empty units, almost never
occurred: content-free pushes of up to 0.41 x ||h|| left the default intact on six of the seven tail-empty units.
Where landings occurred, the base runner-up was right more often than q_lik (4 vs 2 discordant wins, 5/7 overall),
but the tuned model's own minority mode was right just as often (5/6), and the per-unit comparison with q_tail does
not clear the non-inferiority margin. The counts go to the pooled panel I + II test through `landing_events.json` and
`units.json` (schema `iter6_landing_v1`).

## Tables

### Units (forecasts committed before each unit's first nudge row)

| unit | default D_u | K | base runner-up r_u | q_lik top-1 | tail t_u | tail-empty | discordant | E_u (a=1/2/4) | HF twin pass | gate (kappa / rt-vs-adj) | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| I1 | set_start_walk | 5 | sort_scan | sort_scan | - | yes | no | 0.00/0.00/0.00 | 1.00 | 0.92 / 0.96 (gate) | - |
| I2 | sorted_key | 4 | count_key | count_key | sort_then_group | no | no | 0.00/0.00/0.12 | 1.00 | 1.00 / 0.96 (gate) | - |
| I3 | seen_set | 4 | known_loop | floyd | - | yes | yes | 0.00/0.00/0.00 | 0.98 | 1.00 / 0.96 (gate) | - |
| I4 | sort_scan | 4 | counting_levels | counting_levels | - | yes | no | 0.00/0.00/0.00 | 1.00 | 1.00 / 0.96 (gate) | - |
| I6 | dutch_flag | 4 | counting_overwrite | builtin_sort | - | yes | yes | 0.00/0.00/0.12 | 0.98 | 1.00 / 0.96 (gate) | - |
| I7 | per_number_loop | 5 | builtin_count | dp_half | builtin_count | no | yes | 0.00/0.38/0.38 | 1.00 | 0.94 / 0.92 (gate) | - |
| I8 | hash_set_scan | 5 | sort_scan | cyclic_placement | - | yes | yes | 0.00/0.00/0.00 | 1.00 | 1.00 / 0.92 (gate) | - |
| I9 | hash_count | 4 | count_array | sort_two_index | - | yes | yes | 0.00/0.00/0.00 | 1.00 | 0.86 / 1.00 (gate) | - |
| I10 | running_min | 4 | suffix_max | suffix_max | - | yes | no | 0.00/0.00/0.00 | 1.00 | 1.00 / 1.00 (gate_revision) | - |
| I5 | two_sorted_lists | 4 | sweep_events | min_heap_ends | min_heap_ends | no | yes | 0.25/0.62/0.38 | 0.98 | 1.00 / 1.00 (gate) | - |

### Landing events (cells with pass rate >= 0.8 x twin pooled per nudge type)

| unit | nudge | n attempts | pass | correct off-default catalogue programs | other (correct) | exists | modal | lead | clear | r_u hit | q_lik hit | t_u hit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| I1 | ESC | 160 | 0.97 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I1 | PN | 50 | 0.96 | sort_scan 1 | 0 | no | sort_scan | 1.00 | no | - | - | - |
| I1 | GTN | 0 | - | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I2 | ESC | 260 | 1.00 | count_key 11 | 0 | yes | count_key | 1.00 | yes | yes | yes | no |
| I2 | PN | 100 | 0.96 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I2 | GTN | 50 | 0.98 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I3 | ESC | 240 | 0.97 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I3 | PN | 100 | 0.96 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I3 | GTN | 50 | 0.92 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I4 | ESC | 230 | 0.99 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I4 | PN | 100 | 0.94 | counting_levels 2 | 0 | no | counting_levels | 1.00 | no | - | - | - |
| I4 | GTN | 50 | 0.90 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I6 | ESC | 180 | 0.97 | counting_overwrite 7 | 0 | yes | counting_overwrite | 1.00 | yes | yes | no | no |
| I6 | PN | 50 | 0.94 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I6 | GTN | 0 | - | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I7 | ESC | 320 | 0.99 | builtin_count 126 | 0 | yes | builtin_count | 1.00 | yes | yes | no | yes |
| I7 | PN | 100 | 0.99 | builtin_count 31, dp_half 1 | 0 | yes | builtin_count | 0.94 | yes | yes | no | yes |
| I7 | GTN | 50 | 0.98 | builtin_count 21 | 0 | yes | builtin_count | 1.00 | yes | yes | no | yes |
| I8 | ESC | 230 | 0.98 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I8 | PN | 50 | 0.98 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I8 | GTN | 50 | 0.82 | cyclic_placement 1 | 0 | no | cyclic_placement | 1.00 | no | - | - | - |
| I9 | ESC | 240 | 0.99 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I9 | PN | 100 | 0.99 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I9 | GTN | 50 | 1.00 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I10 | ESC | 240 | 1.00 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I10 | PN | 100 | 1.00 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I10 | GTN | 50 | 1.00 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I5 | ESC | 380 | 0.93 | min_heap_ends 147, sweep_events 29 | 0 | yes | min_heap_ends | 0.67 | yes | no | yes | yes |
| I5 | PN | 100 | 0.89 | min_heap_ends 46, sweep_events 6 | 0 | yes | min_heap_ends | 0.77 | yes | no | yes | yes |
| I5 | GTN | 0 | - | 0 | 0 | no | - | 0.00 | no | - | - | - |

### Claim L tests (pool_l1.py, frozen; panel I alone is descriptive below n = 6)

| test | scope | n | statistic | p | verdict |
|---|---|---|---|---|---|
| L1a (tail-empty events) | per event | 1 | 1 hits (chance mean 0.33) | 0.333 | DESCRIPTIVE |
| L1b (discordant events) | per event | 6 | b = 4, c = 2 | 0.344 | FAIL |
| L1a | unit-clustered | 1 | 1 hits | 0.333 | DESCRIPTIVE |
| L1b | unit-clustered | 3 | b = 2, c = 1 | 0.500 | DESCRIPTIVE |

All existing events: r_u named the modal landing in 5/7; t_u (tuned model's own minority mode) in 5/6 events where t_u is defined. Verdict note: no inferential pass.

| log-score difference D = LS_base - LS_rival | events | mean D (nats) | one-sided 95% lower bound | non-inferior (> -0.10) | defined-only n / mean D |
|---|---|---|---|---|---|
| base vs q_lik (event bootstrap) | 7 | 0.95 | 0.32 | yes | 7 / 0.95 |
| base vs q_lik (unit-cluster bootstrap) | 7 | 0.95 | 0.00 | yes | - |
| base vs q_lik_raw (event bootstrap) | 7 | 16.06 | 8.28 | yes | 7 / 16.06 |
| base vs q_lik_raw (unit-cluster bootstrap) | 7 | 16.06 | 1.80 | yes | - |
| base vs q_tail (event bootstrap) | 7 | 0.25 | -0.05 | yes | 7 / 0.25 |
| base vs q_tail (unit-cluster bootstrap) | 7 | 0.25 | -0.16 | no | - |

**L2:** 0 of 477 correct nudged off-default programs fall in a mode with 0 valid and 0 correct base programs (rule-of-three upper bound 0.006).

**L3 (held-out log score of the nudged off-default programs, mean over 10 splits; units with >= 4 programs):**

| unit | n | q_base^gamma | uniform | association | q_tail | Kendall tau(base, tail) |
|---|---|---|---|---|---|---|
| I1 | 7 | -2.13 | -1.39 | -0.80 | -1.39 | - |
| I2 | 11 | -0.00 | -1.10 | -0.51 | -1.39 | -0.82 |
| I3 | 0 | - | - | - | - | - |
| I4 | 2 | - | - | - | - | - |
| I6 | 19 | -0.03 | -1.10 | -0.11 | -1.10 | - |
| I7 | 179 | -0.06 | -1.39 | -3.15 | -0.57 | 0.77 |
| I8 | 6 | -1.44 | -1.39 | -1.27 | -1.39 | - |
| I9 | 0 | - | - | - | - | - |
| I10 | 0 | - | - | - | - | - |
| I5 | 253 | -0.93 | -1.10 | -0.56 | -0.57 | 0.00 |

Pooled Kendall tau mean -0.01; sign test over units 1 positive / 1 negative, p = 0.750.

**M (movability candidates vs E_u; one panel, descriptive):**

| candidate | direction | n | Spearman rho | one-sided p | Holm p | supported |
|---|---|---|---|---|---|---|
| beta | + | 10 | 0.71 | 0.014 | 0.070 | no |
| replacement | - | 10 | 0.46 | 0.901 | 1.000 | no |
| runtime_merit | - | 10 | 0.03 | 0.532 | 1.000 | no |
| twin_modal_share | - | 10 | -0.89 | 0.003 | 0.016 | yes |
| K | + | 10 | -0.04 | 0.581 | 1.000 | no |
| m | - | 9 | -0.08 | 0.419 | 1.000 | no |

**K (correct-only rarefied Hill-1 at depth 25; pass cost = twin pass rate minus knob pass rate, points):**

| unit | Hill-1 twin | PN a2 (cost) | PN a4 (cost) | BINT (cost) | H5 / P15 / P20 (full hull) |
|---|---|---|---|---|---|
| I1 | 1.00 | 1.10 (4) | 1.35 (24) | 1.94 (33) | 1.22 / 1.63 / 1.76 |
| I2 | 1.01 | 1.00 (0) | 1.00 (8) | 1.27 (0) | 1.29 / 1.29 / 1.29 |
| I3 | 1.00 | 1.00 (3) | 1.00 (3) | 1.27 (-1) | 1.30 / 1.30 / 1.30 |
| I4 | 1.00 | 1.00 (2) | 1.18 (10) | 1.00 (13) | 1.10 / 1.21 / 1.21 |
| I6 | 1.00 | 1.00 (2) | 1.79 (26) | 1.15 (2) | 1.26 / 1.58 / 1.72 |
| I7 | 1.04 | 1.67 (2) | 1.96 (0) | 2.38 (23) | 2.07 / 2.28 / 2.39 |
| I8 | 1.00 | 1.00 (2) | 1.24 (24) | 2.06 (10) | 1.60 / 2.15 / 2.15 |
| I9 | 1.00 | 1.00 (0) | 1.00 (2) | 1.14 (0) | 1.17 / 1.17 / 1.17 |
| I10 | 1.00 | 1.00 (0) | 1.00 (0) | 1.00 (0) | 1.00 / 1.00 / 1.00 |
| I5 | 1.31 | 1.95 (1) | 2.59 (3) | 1.79 (-2) | 2.61 / 2.61 / 2.61 |

**Novelty audit:** 1 distinct correct 'other' programs among 8936 correct programs; classes {'CATALOGUE_VARIANT': 1}; no correct novel algorithm (rule-of-three bound 0.00034 per correct program).


## Validity checks

- **Gates (stage ii):** references 100% under both labellers on every unit; Cohen's kappa(runtime, AST) 0.86-1.00 and
  runtime vs adjudicated 0.92-1.00 on the gold sets (I10 after the revision round, holdout kappa 1.00).
  Style re-gate (10 nudged programs per unit, two judge families): 0% disagreement on every unit.
- **Base audits (15 programs per unit):** raw agreement of the final labels with each judge 0.53-1.00; most
  disagreements are 'other' (ours) vs 'invalid' (judges) on broken plain completions; with those merged, agreement is
  0.60-1.00. Relabelling the audited rows with the judges' joint label changes no unit's r_u
  (`results/label_qa.json`). Units below 0.8 are flagged in `units/<u>/base_audit.json`.
- **Engine check:** HF-50 vs vLLM-50 label composition inside the template-resampling null (2,000 resamples) on all ten
  units, so D_u, q_tail and p0 use the pooled twin rows as planned.
- **GPU tests** (`results/gpu_tests.json`): G1 CRN determinism, G2 batch-companion invariance, G3 alpha = 0 push equals
  the twin, G4 push rel_err < 1e-3 at every edited block, G5 GTN alpha = 0 equals the twin and the shadow tokens equal
  the GTN tokens inside the window: all pass. **G6 failed:** right-padded B-row teacher forcing differs from batch-1 by
  up to 1.26 nats per 48-token program (bf16 batch-shape noise), so q_lik and the fork margin use batch-1 teacher
  forcing (exact per sequence).
- **Realised displacement:** ESC/PN prefill pushes hit their target along u with relative error <= 8.4e-4; the target
  is 0.10 / 0.21 / 0.41 x ||h_twin|| at alpha 1 / 2 / 4; GTN rows <= 5.5e-4.
- **Integrity** (`results/commit_order.json`): 0 chain breaks; commit #0 precedes the first sample; the analysis-code
  addendum (pool_l1.py) and the enrolment hash precede the first nudge row; every unit's commit precedes its first
  nudge row; no nudge row predates the enrolment.
- **Re-derivation** (`audit/rederive.py`, no shared code): 0 mismatches for E_u, every landing event, L1a and L1b.
  Placebos: a random non-default forecast hits 0.338 of the L1a events against a chance of 0.333; the twin scored as a
  push gives E_u = 0 on every unit.
- **Sandbox harness check (dependency rows):** the docstring examples of 24 HumanEval+/EnAMEL canonical solutions run
  through the same sandbox: 30/38 cases pass; the 8 others return exactly the documented values but are rejected by the
  integer-only list rule of the `exact` checker (built for I7) or because JSON turns tuples into lists, which no list-I
  unit relies on (`results/harness_check.json`). All ten dependency datasets are accounted for in
  `results/dependency_usage.json`.
- **Headline re-derivation** (`audit/rederive_headlines.py`, reads the raw row files, labels and adjudications directly): the event count, r_u / t_u hits, L1a, L1b, both log-score differences, L2 and the two M correlations all match; placebos fail (random r_u: L1b p < 0.05 in 0% of 2,000 draws; E_u permuted across units: the M test reaches p < 0.05 in 3.5% of 200 permutations; a random Dirichlet forecast averages -0.19 nats against q_lik and never reaches the observed +0.95).
- **Spend and compute:** OpenRouter USD 0.34 over 1,411 judge calls (cap 2.00). One NVIDIA L4: vLLM 31.5 min (instruct
  4.8, base 25.2, BINT 1.5), HF CRN engine 71 min (twin 6.0, ESC stage 1 29.6, confirmations 7.2, PN 16.2, GTN 11.8).

## What was done

1. **Units (S1).** Ten new LeetCode-derived units in new wording with no algorithm or data-structure word
   (`src/units_spec6.py`; the grep audit and its planted-ban control are in `results/grep_audit.json`): I1 longest
   consecutive run, I2 group anagrams, I3 happy number, I4 h-index, I5 meeting rooms, I6 three values in place, I7 one
   counts 0..n, I8 first missing positive, I9 common values with repeats, I10 best single trade (reserves I11, I12:
   cards only, not needed).
2. **Unhooked sampling on vLLM bf16 (S2-S3).** Instruct: forced programs (5 wordings x 5 seeds per mode), 250 twin
   rows (150 at T 1.0, 100 at T 1.3), association answers. Base: 200 chat twin rows, 100 plain completions, 30 base
   intents. Per-request seeds from the frozen rule.
3. **Build and gate (S4).** Hidden tests checked by two independent oracles, one reference per mode at <= 0.25 x the
   limit, >= 3 mutants, excluded brute force that exceeds the limit; a runtime tracer built on `sys.monitoring`
   (opcode profile with BINARY_OP by operator, calls with argument sizes, input-list access counters, user-call depth)
   as the primary labeller and AST rules second; blind judges only on disagreement.
4. **HF CRN engine (S5).** Memory probe (B = 12), GPU tests, HF twin (50 per unit), q_lik passes; per-unit forecasts
   committed; enrolment order hashed.
5. **Nudges (S7)**, in enrolment order: ESC 8 fixed directions x alpha 1/2/4 x N 10 with confirmation to N 30, plan
   noise (a fresh direction per sample) at alpha 2 and 4 (N 50 each), generated-token noise at alpha 2 (N 50, shadow
   rows), and the BINT knob (N 30, vLLM).
6. **Analysis (S10)**: `pool_l1.py` (frozen), L2, L3, M, K, novelty audit, label QA, figures, independent
   re-derivation and the commit-order proof.

## Design constants (frozen in commit #0, `predictions/protocol_v6_panelI.json`)

| item | value |
|---|---|
| decoding | T 1.0 (twin T 1.3 rows on vLLM), top-p 1, no top-k, thinking off, max 1,024 new tokens, fence stop |
| HF engine | bf16 sdpa, CRN inverse-CDF sampler (float64 softmax(logits / T)), B = 12 rows of one (unit, template) prompt, prune = False |
| push | `h <- h + (alpha n[l,p] - (h - h_twin).u) u`, blocks 12-23, task-spec positions, prefill only; `n = r_Q(l) ||h_twin||` |
| GTN | generated tokens 1..32, blocks 12-23, teacher-forced shadow row as reference, alpha 2 |
| seeds | directions `sha256('iter6|panelI|'+unit+'|dir|'+k)[:8]`; PN / GTN per (unit, alpha, template, slot); CRN `sha256('iter6|panelI|'+unit+'|'+w+'|'+k)[:16]` |
| escape rule | stage 1 (N 10): share >= twin + 0.20 and pass >= 0.8 x twin; confirmed at N 30 with one-sided exact binomial p < 0.05 vs p0 = (k_twin + 0.5)/(n_twin + 1) |
| landing event | pass-gated cells of one nudge type pooled; >= 5 correct off-default catalogue programs; clear iff the modal mode leads by 15 points |
| default | modal correct twin label with share >= 0.6 over the 300 twin rows |

## Deviations from the plan

- **g6_batch1_teacher_forcing**: G6 failed: right-padded B-row teacher forcing differs from batch-1 by up to 1.26 nats per 48-token program (bf16 batch-shape noise, above the 0.05-nat bound); q_lik and the fork margin are computed with batch-1 teacher forcing (exact per sequence, independent of batch composition)
- **models_shared_cache**: Model weights live in the run's shared HF cache (HF_HUB_CACHE), not in a workspace hf_cache/ folder, per the run's storage rules; nothing to delete in the workspace.
- **gpu_l4**: The pod has one NVIDIA L4 (22.0 GiB usable, cc 8.9). bf16 fits (no FP8 anywhere); the memory probe chose B = 12 (peak 16.2 GiB, 5.9 GiB headroom).
- **vllm_base_fallback**: vLLM base phase: the first engine start failed (instruct engine memory not yet released); the plan fallback (enforce_eager, max_model_len 1792, gpu_memory_utilization 0.97) was used. Longest prompt 289 tokens + 1024 new < 1792.
- **vendor_ported**: Optional iteration-5 files were not imported as modules: exp26's engine, context, sampling, prompt, sandbox, gate, judge and labeller code was PORTED into src/*6.py (copies of the sources in vendor/exp26/src with sha256 in vendor/SHA256SUMS); r_Q, templates, FORMAT_LINE, TEMPLATE_TAIL and the exp7 noun exclusions are the in-plan constants (identical to vendor/exp23/qwen_ratio.json and vendor/exp7/frozen/templates_nouns_padding.json). VENDOR_MISSING (not used): exp20 GTN hook, exp27 base-intent code, exp22 directions/, exp11 bench, exp8 suite, exp24 base rows, exp25 landings, exp18 known solutions.
- **gtn_reimplemented**: GTN uses the teacher-forced shadow-row re-implementation stated in the plan (exp20's S3 hook not vendored); its hook hash (sha256 of src/engine6.py + src/ctx6.py, logged per row) differs from iteration 4. Matters only for cross-artifact GTN comparisons, never for L1 (events pooled within this artifact).
- **pool_l1_addendum**: pool_l1.py and its synthetic tests were hash-committed in addendum 1 (before the first nudge row) rather than in commit #0; commit #0 froze its full specification verbatim (predictions/protocol_v6_panelI.json). The labeller/engine/instrument code was committed in the same addendum.
- **secondary_analysis_code_late**: analysis/*.py (event builder, L2/L3/M/K, novelty, figures, outputs) and audit/*.py were written while the nudges ran and were exercised on partial nudge data for debugging; they implement the rules frozen in commit #0 and are hash-committed in addendum 2. The primary test (pool_l1.py) predates every nudge row.
- **assoc_prompt_wording**: Association prompts are rendered as in iteration 5: the task description followed by the association question (the FORMAT_LINE is omitted because the requested answer is one sentence).
- **bint_on_vllm**: BINT rows are generated on vLLM bf16 (unhooked, per-request seed) because every BINT slot has its own prompt (its own base intent) while the HF CRN engine batches one shared prompt; BINT is a knob only and never enters L1.
- **forced_topup_not_run**: The HF unhooked forced top-up (up to 40 attempts) was not run: modes with fewer than 10 verified programs are flagged in units/<u>/forced_verified.json; q_lik uses the >= 3 available, and a mode with < 3 verified programs is undefined (uniform share).
- **s8_screen_not_run**: S8 (15 existing tasks as SCREEN units, screen rescoring of the iteration-5 landings) NOT RUN: it needs the vendored bench labellers, the exp8 suite and exp24 base rows integrated into this pipeline, which did not fit the time left after the new-unit arms; the new-unit confirmation is unaffected (screen rows are never pooled).
- **s9_wi_not_run**: S9 weight interpolation (first in the drop order) NOT RUN on time; K is reported without the interpolation baseline, a stated gap.
- **s5_base_engine_check_not_run**: The optional S5(0) HF-base vs vLLM-base check was dropped on time (plan: optional, dropped on time).
- **stage_i_build_fixes**: Gate stage (i) build fixes before any gate (ii): runtime rules of I2 (sorted() on a range), I5 (two sorted generator inputs), I6 (two-pass loop threshold 1.3n), I10 (descending index runs) were corrected, and I2/I4/I5/I6/I8/I10 were rebuilt sequentially because 9 parallel builds inflated reference timings beyond 0.25 x the limit. No sampled program was looked at for these fixes.
- **sandbox_stdout**: Mid-labelling, a model program printed a '{...}' line that broke the sandbox protocol; user stdout now goes to /dev/null and sandbox records carry a marker prefix. Rows labelled before the fix were unaffected (the parse error only crashed the worker).
- **i10_revision_round**: I10 failed gate (ii) (kappa 0.72); one revision round: runtime rule detects descending index runs (prefix-min/suffix-max arrays), AST fallback 'other' without a scan loop, a parameterless solve is invalid; all I10 rows were relabelled with the revised rules (old labels kept in data/labels_superseded_I10_gate1.jsonl) and the fresh holdout (base valid rows 10..19 + twin k 12, 13) passed (kappa 1.0, runtime vs adjudicated 1.0).
- **attempts_definition**: Cell shares: attempts = rows minus 'disputed'; 'invalid' rows count as failed attempts (so degenerate pushed cells fail the 0.8 x twin pass-rate gate); pass rate = passed / attempts.
- **kappa_degenerate**: Gate kappa: computed over traceable items (runtime label defined); when kappa is undefined because one label dominates, raw agreement >= 0.9 is required instead (iteration-5 convention).
- **staged_scaling**: Staged scaling on the first enrolled unit was run as 1 batch (12 rows) -> 8 batches (~100 rows) -> full, with results/timing_extrapolation.json written before the full run.
- **labelling_before_gate**: For throughput, raw rows were labelled by the runtime and AST labellers as soon as a unit's stage (i) build passed, before gate (ii); no label was used for any decision (default, forecasts, enrolment) before the unit's gate (ii) passed, and I10's rows were relabelled with its revised rules after the revision round.
- **l3_all_nudged_rows**: L3 scores the forecasts against every correct nudged off-default program of the unit (ESC + PN + GTN, all cells), not only the pass-rate-gated cells that define landing events; units with fewer than 4 such programs have no L3 score.
- **i10_base_audit_late**: I10's post-gate base audit ran after its revision round (after the nudges); it is QA only and enters no statistic.
- **novelty_cost_amendment**: analysis/novelty.py was amended after addendum 2 so that its judge calls are written to the cost ledger (results/costs.jsonl); the classification prompt and rules are unchanged. The amended file is a new chain entry (tag amendment_novelty_cost_logging); the addendum-2 entry therefore reports the file as changed in commit6.verify().

## Layout

| path | what it holds |
|---|---|
| `reproducibility.md` | the exact commands run, in order, with hardware, timings, env-var names and expected numbers |
| `method.py` | entry point: `uv run method.py` re-runs the CPU-only analysis stage; `--stage all` runs every stage in order |
| `pool_l1.py` | the frozen, stdlib-only pooled test of Claim L (committed before the first nudge) |
| `landing_events.json`, `units.json` | panel-I inputs to `pool_l1.py` (schema `iter6_landing_v1`) |
| `method_out.json` (+ `full_`/`mini_`/`preview_`) | exp_gen_sol_out: `panelI_units`, `panelI_events`, `panelI_cells`, each with predict_base / predict_qlik / predict_tail |
| `commitments.log` | sha256 hash chain (genesis sha256('iter6|panelI')): commit #0, analysis addenda, unit commits, enrolment |
| `predictions/` | `protocol_v6_panelI.json` (frozen protocol), `units/<u>.json` (committed forecasts), `enrolment.json` |
| `src/cfg6.py`, `src/units_spec6.py`, `src/prompts6.py`, `src/build_prompts6.py`, `src/extract_sources6.py` | constants and seed rules, unit cards, prompt rendering and grep audit, dependency extraction |
| `src/vllm6.py`, `src/bint6.py` | unhooked vLLM sampling (instruct, base, BINT) |
| `src/engine6.py`, `src/ctx6.py`, `src/hf6.py` | HF bf16 CRN engine with push and GTN hooks, memory probe, GPU tests, q_lik passes, nudge scheduler |
| `src/units/i1.py ... i10.py`, `src/unitlib6.py`, `src/sandbox_tests6.py`, `src/sandbox_trace6.py`, `src/unitbuild6.py` | per-unit tests, oracles, references, mutants, probes and rules; sandboxed test runner and runtime tracer; stage (i) |
| `src/label6.py`, `src/judge6.py`, `src/labels_view6.py`, `src/gate6.py`, `src/forced6.py` | labelling, blind judges, final labels, gate (ii) and base audits, forced-program verification |
| `src/instruments6.py`, `src/commit6.py` | L instruments, engine check, per-unit commit, enrolment; hash chain |
| `analysis/` | event builder, secondary analyses (L2, L3, M, K), novelty audit, label QA, sandbox harness check, figures, outputs, summary |
| `audit/rederive.py`, `audit/rederive_headlines.py`, `audit/commit_order.py` | independent re-derivations with placebos (from samples.jsonl, and from the raw row files); integrity proof |
| `tests/test_cpu.py`, `tests/test_pool_l1.py` | CPU tests (builds, grep audit, tokenizer identity, chain tamper) and pool_l1 synthetic tests |
| `units/<u>/` | tests.jsonl, references/, mutants/, build report, gates, base audit, forced_verified.json, neutral noun, positions |
| `data/` | `raw_vllm.jsonl`, `raw_hf.jsonl` (every generation with token ids), `labels.jsonl`, `adjudications.jsonl`, `judge_cache.jsonl`, `samples.jsonl` (one row per program), `prompts.jsonl`, `realised_disp.jsonl` |
| `results/` | pool_l1_panelI, l2, l3, m, k, novelty, label_qa, cells, gpu_tests, hf_batch, grep_audit, commit_order, rederive, cpu_tests, qlik/, nudge_runs/, timing, costs, deviations, summary.md |
| `figures/` | F1 base forecast vs landings, F2 event table, F3 escape heatmap, F4 log-score differences, F5 M vs E_u, F6 knobs (PDF + PNG) |
| `vendor/` | read-only copies of the iteration-5 files the code was ported from, with `vendor/SHA256SUMS` |
| `directions/` | the push directions `rand_<seed>.npy` (kept on the run's volume) |
| `inputs/` | rows extracted from the dependency dataset (`sources.json`) |

Every kept artifact stays on the run's storage volume at these relative paths; no file here reaches 100 MB.

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r requirements.lock.txt
uv run method.py                    # analysis, audits, figures, outputs (CPU, ~10 min, a few judge calls)
uv run method.py --stage all        # the whole pipeline (one >= 20 GB GPU, OPENROUTER_* variables)
python pool_l1.py --events landing_events.json <panel II events> --units units.json <panel II units> --out pooled.json
```

Environment variables: `HF_HUB_CACHE` (the two pinned model snapshots), `OPENROUTER_BASE_URL` and
`OPENROUTER_API_KEY` (blind judges, cached in `data/judge_cache.jsonl`), `AII_DEP_ART_J3RM` (folder of the dependency
dataset `art_j3Rm_lr2nzR6`, holding `full_data_out.json`).

## Restoring removed files

Only regenerable bulk is removed after the round (`.aii/manifest.yaml`); every result, prediction, unit build, figure
and data file stays.

| removed path | restore with |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r requirements.lock.txt` |
| `__pycache__/`, `src/__pycache__/`, `src/units/__pycache__/` | regenerated on import, or `python -m compileall . src src/units` |
| model weights (shared Hugging Face cache, never in this folder) | `huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218` and `huggingface-cli download Qwen/Qwen3-8B-Base --revision 49e3418fbbbca6ecbdf9608b4d22e5a407081db4` |
