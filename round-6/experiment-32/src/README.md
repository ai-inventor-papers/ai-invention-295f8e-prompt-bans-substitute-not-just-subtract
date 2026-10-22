# Where nudged code lands, panel two (iteration 6)

Panel II of the iteration-6 held-out test of **Claim L**: when a content-free nudge moves **Qwen3-8B** (instruct) off its default algorithm, does the program land on the **base model's runner-up** `r_u` (Qwen3-8B-Base), or only on the tuned model's **own hidden second choice**, measured two ways: the tail of 300 twin samples (`q_tail`, `t_u`) and the teacher-forced likelihood ranking of forced programs (`q_lik`, `qlik_top1`)? Claim M asks which unit property ranks the escape fraction `E_u`. Everything hooked runs in bf16 HF transformers; vLLM bf16 only samples unhooked arms.

Every forecast was sha256 hash-chained (`commitments.log`) before the unit's first nudge sample. Commit #0 (the protocol) precedes the first sample, and the analysis code precedes the first nudge (audit below).

## Results (panel II; CONFIRMATION = new list-II units)

**Panel verdict: DESCRIPTIVE.** This panel is half of the pooled panel I + II test. `landing_events.json` and `units.json` (schema `iter6_landing_v1`) pool mechanically with panel I through `analysis/pool_l1.py`.

- **L1a (tail-empty events):** r_u named the landing in 3/4 events (chance 1.33 hits), exact Poisson-binomial p = 0.1042, status **DESCRIPTIVE** (6 events required). qlik_top1 hits on the same events: 3. Events: II4|ESC, II5|ESC, II5|PN, II7|GTN.
- **L1b (discordant events, r_u != qlik_top1):** r_u-only hits b = 6, qlik-only hits c = 3, ties 0; one-sided exact sign test p = 0.2539, status **FAIL**. Events: II1|ESC, II1|PN, II1|GTN, II3|ESC, II3|PN, II3|GTN, II8|ESC, II8|PN, II8|GTN.
- **Pseudo-replication guard (unit level):** L1a 2/3 units (p = 0.2917, DESCRIPTIVE); L1b b = 2, c = 1 over 3 units (p = 0.5000, DESCRIPTIVE). The event-level L1b result therefore holds **per event, not per unit**: the discordant events come from few units.
- **Rival t_u (the twin's own tail):** 9/9 hits where defined (not tail-empty).
- **Log scores on matched events E** (nats per landed program; base minus rival; one-sided 95% bootstrap lower bound; non-inferior iff LB > -0.10):

| rival | n events | mean D | LB (event) | LB (unit-clustered) | 95% CI | non-inferior |
|---|---|---|---|---|---|---|
| q_lik | 13 | 0.31 | 0.07 | -0.07 | [0.02, 0.61] | True |
| q_tail | 13 | 0.01 | -0.25 | -0.40 | [-0.30, 0.29] | False |
| q_lik_raw | 13 | 0.53 | -0.01 | -0.38 | [-0.11, 1.23] | True |
| q_assoc | 13 | -0.19 | -0.40 | -0.54 | [-0.43, 0.07] | False |
| q_uniform | 13 | 0.39 | 0.23 | 0.20 | [0.20, 0.56] | True |

- **L2 (landings outside the base repertoire):** 6 of 940 correct off-default content-free nudged programs implement an algorithm with zero valid and zero correct base programs (BINT: 0/45).
  The violations are II1:bisect_positions.
- **L3:** power-fitted held-out winners {'base': 5, 'tail': 2, 'assoc': 4, 'uniform': 1}; Kendall tau-b (q_base vs q_tail order on S): mean 0.61 over 3 units (2/2 positive).
- **M (Spearman with E_u over enrolled new units; Holm over 6 candidates; committed signs):**

| candidate | n | rho | committed sign | one-sided p | Holm p | supported |
|---|---|---|---|---|---|---|
| beta | 7 | 0.95 | + | 0.002 | 0.010 | True |
| replacement_class | 7 | 0.21 | + | 0.429 | 0.464 | False |
| runtime_merit | 7 | 0.56 | + | 0.098 | 0.464 | False |
| twin_modal_share | 7 | -0.48 | - | 0.133 | 0.464 | False |
| K | 7 | 0.59 | + | 0.093 | 0.464 | False |
| fork_margin | 6 | -0.41 | - | 0.222 | 0.464 | False |

### Reading

- On all 13 CONFIRMATION events: r_u hit 9, qlik_top1 hit 6. On the 9 events where the twin tail is non-empty, t_u hit 9/9 and r_u hit 6/9.
- On the 4 tail-empty events, r_u equals qlik_top1 in 4. So L1a cannot separate the base runner-up from the tuned model's own likelihood ranking there: both name the same algorithm.
- The decisive comparisons are the discordant units:
  - II1 and II3: the landing matches r_u and the twin tail t_u, not qlik_top1.
  - II8 (k nearest points, a flagged structural neighbour of T03): every nudge type lands on maxheap_k. That is the tuned model's own tail choice and its likelihood top-1, not the base runner-up (nsmallest).
- Read together:
  - Where the base runner-up and the tuned model's own forecasts disagree, the tuned model's forecasts won (II8).
  - Where the base runner-up won a discordant event (II1, II3), the twin tail t_u named the same landing (t_u 9/9 where defined).
  - So no event favours the base model over the tuned model's own twin tail. This agrees with 'nudges walk the tuned model's own hidden ladder', with the base model as a proxy where its order matches that ladder.
- The counts are small (3 discordant units, 4 tail-empty events), so this is descriptive and carried to the pooled panel I + II test.

### Units

| unit | status | default (share) | K | tail-empty | t_u | r_u | qlik_top1 | discordant | E_u (a1/a2/a4) | flags |
|---|---|---|---|---|---|---|---|---|---|---|
| II1 | enrolled | two_pointers (0.99) | 3 | False | iterator_consumption | iterator_consumption | bisect_positions | True | 0.00/0.12/0.38 |  |
| II2 | excluded_no_default | NO_DEFAULT (0.00) | 3 | None | None | None | None | None | -/-/- | NO_DEFAULT |
| II3 | enrolled | shift_mask (0.61) | 4 | False | library_count | library_count | kernighan | True | 0.00/0.25/0.62 | ENGINE_SPLIT |
| II4 | enrolled | binary_search_slope (1.00) | 3 | True | None | linear_scan | linear_scan | False | 0.00/0.12/0.12 |  |
| II5 | enrolled | backtracking_used (1.00) | 5 | True | None | library_permutations | library_permutations | False | 0.00/0.25/0.88 |  |
| II6 | enrolled | stack (1.00) | 3 | True | None | replace_pairs | None | False | 0.00/0.00/0.00 | QLIK_UNDEFINED_ON_S |
| II7 | enrolled | backward_fill (1.00) | 4 | True | None | concat_sort | concat_sort | False | 0.00/0.00/0.00 |  |
| II8 | enrolled | full_sort (0.66) | 4 | False | maxheap_k | nsmallest | maxheap_k | True | 0.25/0.25/0.00 |  |
| B1 | enrolled | arithmetic_sum (1.00) | 5 | True | None | hash_set | hash_set | False | -/-/0.00 |  |
| B2 | enrolled | hash_count (0.88) | 4 | False | xor_fold | xor_fold | sort_pair_scan | True | -/-/0.25 |  |
| B3 | enrolled | kruskal (0.69) | 4 | False | prim_heap | prim_heap | prim_heap | False | -/-/0.12 |  |
| B4 | enrolled | binary_search (1.00) | 6 | True | None | linear_scan | linear_scan | False | -/-/0.50 |  |
| B5 | enrolled | backtracking (1.00) | 4 | True | None | iterative_doubling | iterative_doubling | False | -/-/0.12 |  |
| B6 | enrolled | sort_compare (0.72) | 3 | False | fixed_count_array | hash_count | fixed_count_array | True | -/-/0.38 |  |
| B7 | enrolled | merge_sort_count (1.00) | 4 | True | None | sorted_insertion_bisect | sorted_insertion_bisect | False | -/-/0.00 | twin_pass_below_0.7(0.07) |

### Landing events (content-free, is_event)

| event | set | n landed | composition | modal landing | r_u | qlik_top1 | t_u |
|---|---|---|---|---|---|---|---|
| II1 / ESC | CONFIRMATION | 21 | iterator_consumption:15, bisect_positions:6 | iterator_consumption | iterator_consumption + | bisect_positions | iterator_consumption + |
| II1 / PN | CONFIRMATION | 15 | iterator_consumption:15 | iterator_consumption | iterator_consumption + | bisect_positions | iterator_consumption + |
| II1 / GTN | CONFIRMATION | 5 | iterator_consumption:5 | iterator_consumption | iterator_consumption + | bisect_positions | iterator_consumption + |
| II3 / ESC | CONFIRMATION | 307 | library_count:228, kernighan:79 | library_count | library_count + | kernighan | library_count + |
| II3 / PN | CONFIRMATION | 55 | library_count:47, kernighan:8 | library_count | library_count + | kernighan | library_count + |
| II3 / GTN | CONFIRMATION | 27 | library_count:25, kernighan:2 | library_count | library_count + | kernighan | library_count + |
| II4 / ESC | CONFIRMATION | 33 | linear_scan:33 | linear_scan | linear_scan + | linear_scan + | None |
| II5 / ESC | CONFIRMATION | 216 | swap_backtracking:12, library_permutations:204 | library_permutations | library_permutations + | library_permutations + | None |
| II5 / PN | CONFIRMATION | 26 | swap_backtracking:2, library_permutations:24 | library_permutations | library_permutations + | library_permutations + | None |
| II7 / GTN | CONFIRMATION | 10 | forward_copy:6, concat_sort:4 | forward_copy | concat_sort | concat_sort | None |
| II8 / ESC | CONFIRMATION | 122 | maxheap_k:121, nsmallest:1 | maxheap_k | nsmallest | maxheap_k + | maxheap_k + |
| II8 / PN | CONFIRMATION | 33 | maxheap_k:32, nsmallest:1 | maxheap_k | nsmallest | maxheap_k + | maxheap_k + |
| II8 / GTN | CONFIRMATION | 22 | maxheap_k:22 | maxheap_k | nsmallest | maxheap_k + | maxheap_k + |
| B2 / ESC | SCREEN | 47 | xor_fold:46, set_sum_identity:1 | xor_fold | xor_fold + | sort_pair_scan | xor_fold + |
| B2 / PN | SCREEN | 13 | xor_fold:13 | xor_fold | xor_fold + | sort_pair_scan | xor_fold + |
| B2 / GTN | SCREEN | 13 | xor_fold:13 | xor_fold | xor_fold + | sort_pair_scan | xor_fold + |
| B2 / ESC / iter5 | SCREEN | 161 | xor_fold:161 | xor_fold | xor_fold + | sort_pair_scan | xor_fold + |
| B2 / PN / iter5 | SCREEN | 29 | xor_fold:29 | xor_fold | xor_fold + | sort_pair_scan | xor_fold + |
| B3 / ESC | SCREEN | 21 | prim_heap:21 | prim_heap | prim_heap + | prim_heap + | prim_heap + |
| B3 / PN | SCREEN | 5 | prim_heap:5 | prim_heap | prim_heap + | prim_heap + | prim_heap + |
| B3 / GTN | SCREEN | 10 | prim_heap:10 | prim_heap | prim_heap + | prim_heap + | prim_heap + |
| B3 / ESC / iter5 | SCREEN | 72 | prim_heap:72 | prim_heap | prim_heap + | prim_heap + | prim_heap + |
| B3 / PN / iter5 | SCREEN | 39 | prim_heap:39 | prim_heap | prim_heap + | prim_heap + | prim_heap + |
| B4 / ESC | SCREEN | 103 | library_isqrt:42, float_sqrt:5, linear_scan:56 | NO_CLEAR_LANDING | linear_scan | linear_scan | None |
| B4 / PN | SCREEN | 17 | library_isqrt:5, float_sqrt:5, linear_scan:7 | NO_CLEAR_LANDING | linear_scan | linear_scan | None |
| B4 / ESC / iter5 | SCREEN | 35 | newton:2, linear_scan:33 | linear_scan | linear_scan + | linear_scan + | None |
| B4 / PN / iter5 | SCREEN | 6 | linear_scan:6 | linear_scan | linear_scan + | linear_scan + | None |
| B5 / ESC | SCREEN | 27 | bitmask_enumeration:9, itertools_combinations:18 | itertools_combinations | iterative_doubling | iterative_doubling | None |
| B5 / PN / iter5 | SCREEN | 5 | bitmask_enumeration:5 | bitmask_enumeration | iterative_doubling | iterative_doubling | None |
| B6 / ESC | SCREEN | 87 | hash_count:30, fixed_count_array:57 | fixed_count_array | hash_count | fixed_count_array + | fixed_count_array + |
| B6 / PN | SCREEN | 19 | hash_count:11, fixed_count_array:8 | hash_count | hash_count + | fixed_count_array | fixed_count_array |
| B6 / GTN | SCREEN | 18 | hash_count:9, fixed_count_array:9 | NO_CLEAR_LANDING | hash_count | fixed_count_array | fixed_count_array |
| B6 / ESC / iter5 | SCREEN | 8 | hash_count:5, fixed_count_array:3 | hash_count | hash_count + | fixed_count_array | fixed_count_array |
| B6 / PN / iter5 | SCREEN | 29 | hash_count:9, fixed_count_array:20 | fixed_count_array | hash_count | fixed_count_array + | fixed_count_array + |
| B7 / ESC / iter5 | SCREEN | 23 | fenwick_tree:1, sorted_insertion_bisect:22 | sorted_insertion_bisect | sorted_insertion_bisect + | sorted_insertion_bisect + | None |
| B7 / PN / iter5 | SCREEN | 5 | fenwick_tree:2, sorted_insertion_bisect:3 | sorted_insertion_bisect | sorted_insertion_bisect + | sorted_insertion_bisect + | None |

### Sensitivities (frozen list; plus the post-hoc ones marked)

- drop_LOW_CORRECT: L1a 3/4 (p 0.10416666666666667, DESCRIPTIVE); L1b b 6 c 3 ties 0 (p 0.25390625, FAIL); mean D_lik 0.3109379610959711; mean D_tail 0.0054578371811730714
- drop_qlik_gap_below_2x_noise: L1a 1/1 (p 0.5, DESCRIPTIVE); L1b b 3 c 0 ties 0 (p 0.125, DESCRIPTIVE); mean D_lik 0.7186232669423112; mean D_tail 0.3243876980543559
- qlik_unscrubbed_top1: L1a 3/4 (p 0.10416666666666667, DESCRIPTIVE); L1b b 2 c 3 ties 0 (p 0.8125, DESCRIPTIVE); mean D_lik 0.1978582290293885; mean D_tail 0.0054578371811730714
- qlik_raw_top1: L1a 3/4 (p 0.10416666666666667, DESCRIPTIVE); L1b b 6 c 3 ties 0 (p 0.25390625, FAIL); mean D_lik 0.5263863074775298; mean D_tail 0.0054578371811730714
- drop_flagged_neighbours_II8_II12: L1a 3/4 (p 0.10416666666666667, DESCRIPTIVE); L1b b 6 c 0 ties 0 (p 0.015625, PASS); mean D_lik 0.5140267905467538; mean D_tail 0.26855613503804554
- other_dominant_as_no_clear_landing: L1a 3/4 (p 0.10416666666666667, DESCRIPTIVE); L1b b 6 c 3 ties 0 (p 0.25390625, FAIL); mean D_lik 0.3109379610959711; mean D_tail 0.0054578371811730714
- priority_subset: L1a 3/4 (p 0.10416666666666667, DESCRIPTIVE); L1b b 6 c 3 ties 0 (p 0.25390625, FAIL); mean D_lik 0.3109379610959711; mean D_tail 0.0054578371811730714
- SCREEN_included (never primary): L1a 7/12 (p 0.028967901234567918, FAIL); L1b b 13 c 5 ties 1 (p 0.048126220703125, PASS); mean D_lik 0.2275335634813419; mean D_tail -0.06209034698467919
- SCREEN_only (never primary): L1a 4/8 (p 0.13528888888888893, FAIL); L1b b 7 c 2 ties 1 (p 0.08984375, FAIL); mean D_lik 0.1803919474382905; mean D_tail -0.10026975542624787
- POST-HOC drop AUDIT_WEAK units ['II1', 'II4', 'II5', 'II7']: L1a 0/0 (p None, DESCRIPTIVE); L1b b 3 c 3 ties 0 (p 0.65625, FAIL); mean D_lik 0.3048615369891434; mean D_tail -0.311740652165428
- POST-HOC ESC events only: L1a 2/2 (p 0.125, DESCRIPTIVE); L1b b 2 c 1 ties 0 (p 0.5, DESCRIPTIVE); mean D_lik 0.042783376453229514; mean D_tail 0.13107578286729774

### Validity checks

- Independent stdlib re-derivation (`audit/rederive.py`): mismatches [], event ids match True; placebos: random non-default r_u hit rate 0.37 vs chance 0.37; twin-as-nudge events 2 (a unit whose own twin minority already forms an event cannot separate nudge landings from the twin tail); q_base/q_lik swap flips L1b: True.
- Second stdlib re-derivation (`audit/rederive_headlines.py`, raw rows): hit counts {'r_u': 9, 'qlik_top1': 6, 't_u': 9}, mean D_lik 0.311, mean D_tail 0.005, E_u per unit, beta rho 0.946 (p 0.0016) and L2 6/940 all match: True. Placebos fail as required: shuffled E_u rejects 0.027, permuted q_base mean D_lik -0.77, constant beta gives an undefined rho. The committed beta drifts by at most 0.034 when re-counted with the post-commit final adjudications (forecasts are frozen at commit).
- Commit order (`audit/commit_order.py`): chain breaks 0, files changed 0, commit #0 before the first sample True, analysis code before the first nudge True, nudge rows before their unit commit {}, tamper control detected True.
- 15-program blind base audits (labeller vs two-family adjudication, all valid / correct-only): II1 0.40/0.57 AUDIT_WEAK; II3 0.87/1.00; II4 0.73/1.00 AUDIT_WEAK; II5 0.80/1.00 AUDIT_WEAK; II6 1.00/1.00; II7 0.73/1.00 AUDIT_WEAK; II8 1.00/1.00.
- Novelty audit: 33 correct 'other' programs (33 distinct) -> {'CATALOGUE_VARIANT': 31, 'KNOWN_TECHNIQUE_OUTSIDE_CATALOGUE': 1, 'LABELLER_MISS': 1}; no correct novel algorithm (rule-of-three bound 0.00023 per correct program). The 'manual' comparison is the executor's automated nearest-match against references and dataset rows; no human read the programs.
- GPU tests: CRN determinism True; alpha-0 ESC identical rows 20/20; realised dose max relative error 0.00161; GTN alpha-0 identical rows 10/10; vLLM prompt ids identical {'identical': 5700, 'different': 0}.
- CPU tests: schema errors 0; new seeds disjoint from 5713 iteration-4/5 seeds: True; planted-ban control caught for every unit: True.
- OpenRouter spend: USD 0.332 over 1468 judge calls (cap 2.00).

## What was done

1. **Units (candidate list II).** Each unit has new wording with no algorithm or data-structure word, two agreeing oracles, generated hidden tests including stress cases, at least three test-passing references, mutants that must fail, and gated runtime-tracer plus AST labellers (`src/units/ii*.py`). Built: II1 is-subsequence, II2 task scheduler, II3 count ones, II4 peak index, II5 all arrangements, II6 bracket matching, II7 in-place combine, II8 k nearest points. II9/II10 and the reserves were not built (time).
2. **Predictor side, in this order, before any nudge:**
   - the twin of 300: 50 HF CRN slots plus 150 vLLM slots at T 1.0, and 100 vLLM slots at T 1.3;
   - the base repertoire: 200 chat samples with token ids identical to the twin W1-W5 prompts, plus 100 plain completions;
   - forced 'Implement X' programs (up to 40 attempts per algorithm) and q_lik scoring, with scrubbed and unscrubbed variants and a measured noise floor;
   - 20 association answers per algorithm;
   - the gold-set gate (ii) with two judge families;
   - the hash-chained unit commit (`predictions/units/<u>.json`).
3. **Nudges (after the commit):**
   - ESC: 8 fresh isotropic directions x alpha 1/2/4, N 10 per cell, with stage-2 confirmation at N 30;
   - PN: a fresh direction per sample, alpha 2 and 4, N 50 each;
   - GTN: generated tokens 1-32 with teacher-forced shadow rows, alpha 2, N 50;
   - BINT: a base intent sentence followed by instruct code, N 30.
   ESC and PN push blocks 12-23 at the task-spec positions in ban-free units (r_Q from exp23).
4. **SCREEN (iteration-5 B units):**
   - the twin was topped up to 300 (iteration-5 HF slots k 0-9 plus new vLLM slots);
   - forced programs and q_lik were added;
   - the base was topped up with 50 chat and 50 plain samples, under an engine check against the iteration-5 rows;
   - the iteration-5 alpha 1/2 events were rebuilt under the iteration-6 definitions;
   - new alpha-4 ESC, PN alpha 4 and GTN alpha 2 nudges were run.
   Everything is labelled SCREEN and is never primary.

## Layout

| path | what it holds |
|---|---|
| `method.py` | entry point: `uv run method.py` re-runs the CPU final stage (events, frozen analysis, audits, figures, outputs) |
| `landing_events.json`, `units.json` | the pooling files (schema `schema/iter6_landing_v1.json`) |
| `method_out.json` (+ `full_`/`mini_`/`preview_`) | exp_gen_sol_out: datasets `panelII_units`, `panelII_events`, `panelII_cells`; all analyses in `metadata` |
| `commitments.log` | sha256 hash chain (genesis sha256('iter6_dir5_panelII')) of every committed file |
| `predictions/` | `protocol_v6_panelII.json` (commit #0), `analysis_choices.json`, `m_signs.json`, `units/<u>.json`, `enrolment/<u>.json` |
| `analysis/pool_l1.py`, `l2l3.py`, `m_k.py` | frozen analysis code (committed before the first nudge) |
| `src/` | the pipeline; `src/units/ii*.py` are the unit labellers; `src/units/b*.py` and most engine code are vendored from iteration-5 exp26 (patched as listed in Deviations) |
| `src/vllm_gen.py` | vLLM 0.11 sampler with the fence-stop logits processor (run with `.venv_vllm`) |
| `src/gpu6.py`, `src/gtn6.py`, `src/qlik6.py` | HF daemon (twin CRN slots, q_lik, ESC/PN/GTN), GTN sampler, q_lik scorer |
| `src/quantities6.py`, `src/events6.py`, `src/outputs6.py` | unit forecasts + commit, event assembly, final outputs |
| `units/<u>/` | tests, references, mutants, build report, gate reports, frozen catalogue, neutral noun, positions |
| `data/samples_raw.jsonl` | every sampled program with text and token ids (both engines, both models) |
| `data/samples.jsonl` | one row per labelled program (plan row schema) |
| `data/labels.jsonl`, `data/judge_labels.jsonl`, `data/judge_cache.jsonl` | labeller output and judge adjudications |
| `results/` | l1, l2, l3, m, k, screen, engine_checks, dose, escape_table, events_listing.csv, novelty_audit, base_audit, rederive, commit_order, tests_cpu/gpu, timing, costs, deviations |
| `figures/` | F1 landings, F2 log-score forest, F3 escape heatmap, F4 base vs tail, F5 M candidates, F6 knob prices |
| `audit/rederive.py`, `audit/commit_order.py` | stdlib-only re-derivation with placebos; commit-order proof |
| `vendor/` | read-only copies of the iteration-2..5 inputs used (`vendor/exp26/samples_B_nocode.jsonl` = the iteration-5 B-unit labelled rows without code) |
| `inputs/sources.json` | rows extracted from the dependency dataset art_j3Rm_lr2nzR6 (12 LeetCode rows, KodCode/XLCoST/TheAlgorithms keyword rows, noun bank, validation subsets of every other dataset) |
| `directions/`, `cache/` | push directions (`rand_<seed>.npy`) and fp16 ban-free unit norms per unit/template |

Kept artifacts stay on the run's storage volume at these relative paths. Files of 100 MB or more are not part of the published repository (none of this artifact's data files is that large).

## How to run

`reproducibility.md` gives the exact commands in the order they were run, with hardware, environment variables (names only), seeds, runtimes and the numbers a reader should get.

```bash
uv sync                                  # HF environment (Python 3.12, pins in pyproject.toml / uv.lock)
uv run method.py                         # CPU final stage: events, frozen analysis, audits, figures, outputs
python3 -I audit/rederive.py             # independent re-derivation (standard library only)
python3 -I audit/commit_order.py         # commit-order proof
```

The full pipeline needs one 23 GB GPU, `HF_HUB_CACHE` holding the two pinned snapshots, and `OPENROUTER_BASE_URL` / `OPENROUTER_API_KEY` for the judges. In order:

1. `src/extract_sources.py` (needs `AII_DEP_ART_J3RM`);
2. `src/protocol6.py` (commit #0);
3. `src/unitbuild.py II1,...`;
4. the vLLM jobs (`src/requests6.py` builders + `.venv_vllm/bin/python src/vllm_gen.py`);
5. `src/label5.py` (label daemon);
6. `src/gate2.py`;
7. `src/gpu6.py --plan data/gpu_plan_v3.json`;
8. `src/quantities6.py <units>` (commits);
9. `src/outputs6.py`.

## Restoring removed files

Only regenerable bulk is removed after the round (`.aii/manifest.yaml`). Every result, prediction, unit build, figure and data file stays.

| removed path | restore with |
|---|---|
| `.venv/` | `uv sync` |
| `.venv_vllm/` | `uv venv .venv_vllm --python 3.12 && uv pip install --python .venv_vllm/bin/python vllm==0.11.0 transformers==4.57.6 tokenizers==0.22.2` |
| `src/__pycache__/`, `src/units/__pycache__/`, `analysis/__pycache__/`, `tests/__pycache__/`, `vendor/exp27/src/__pycache__/` | regenerated on import (`python -m compileall src analysis tests vendor/exp27/src`) |
| model weights (shared HF cache, never in this folder) | `huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218` and `huggingface-cli download Qwen/Qwen3-8B-Base --revision 49e3418fbbbca6ecbdf9608b4d22e5a407081db4` |

`restore.sh` runs all of the above.

## Deviations from the plan

- **bint_precommit**: BINT code rows (30 per new unit, unhooked, vLLM) were drawn with the committed base intents BEFORE the unit commits; BINT is content_free = false and enters only the K prices and descriptive tables, never a forecast or an L/M test.
- **ii3_engine_split**: II3: the HF-vs-vLLM twin engine check failed (JS above the template-resampling null q95); its twin baseline for the escape gate uses the 50 HF CRN slots only, and q_tail committed from all 300 twin samples is reported beside an HF-only sensitivity; II3 is not tail-empty, so L1a is unaffected (plan F4).
- **tracer_heapq_counters**: After the II1-II6 commits the tracer gained counters for heapq.merge / nsmallest / nlargest (pure-Python helpers that emit no c_call event) so that the II7/II8 labellers can see them; no committed II1-II6 or B-unit rule reads these counters, so their labels are unchanged.
- **gpu_l4**: The pod has an NVIDIA L4 (23 GB, cc 8.9) instead of the planned RTX A4500; the frozen precision rule selects W16A16 bf16 (VRAM >= 19.5 GiB). HF hooked arms ran in batches of B = 20 rows (exp26 convention), at about 7-14 s per batch.
- **entry_point_solve**: Specs ask for 'def solve(...)' instead of LeetCode's 'class Solution' entry point, so the iteration-5 sandbox, tracer, plain-completion template and labeller backbone apply unchanged (the FORMAT_LINE of every iteration-5 unit names solve).
- **analysis_commit_timing**: Commit #0 (protocol, every rule in prose) preceded the first sample; the analysis code (analysis/pool_l1.py, l2l3.py, m_k.py), the M signs, the frozen operational choices, the schema and the test log were hash-committed at 22:11:51Z, after the predictor-side samples but before the first nudge sample (22:18:33Z) -- outcomes are the nudge arms only (exp26 convention).
- **models_shared_cache**: Model weights were read from the run's shared HF cache (HF_HUB_CACHE), not WS/hf_cache; nothing to delete in the workspace.
- **no_dryrun_T03**: The mini end-to-end dry run on DRYRUN_T03 was not run; the pipeline was exercised on the committed units' own data, and the placebos of audit/rederive.py (random r_u, twin-as-nudge, base/lik swap) were run on the real events instead.
- **A_units_not_topped_up**: SCREEN units A1-A5, A7-A9 (exp25 newbench framework) were NOT topped up (no fresh twin of 300, q_lik or base top-up) for lack of time: integrating the second labeller framework did not fit the 6-hour budget. Their iteration-5 confirmed landing counts are reported descriptively in results/screen.json with the iteration-5 forecasts only. This misses a never-drop item of the plan; the B units (exp26 framework) were fully topped up.
- **screen_bint_dropped**: BINT on the iteration-5 units was dropped (drop order item 1); GTN alpha 2, PN alpha 4 and ESC alpha 4 ran on all seven B units.
- **ii9_ii10_not_built**: II9 (longest palindrome) and II10 (palindrome integer) were not built (time); reserves II11/II12 were not needed (five units had passed both gates by T+2:00). Eight list-II units were built; seven have a default and were enrolled.
- **ii2_no_default**: II2 (task scheduler): the instruct twin writes the frame formula without the count of maximum-frequency letters in 249/250 programs (twin pass 0/150 at T 1.0), so the unit has NO_DEFAULT and enters no L or M test; its base and BINT samples are reported only.
- **forced_compliance**: Forced 'Implement X' prompts often return the default algorithm (e.g. II4 index_of_max 0 verified of 40 attempts, II6 replace_pairs and recursive_descent 0 of 40, II5 insertion_build 0 of 40); q_lik is undefined for such algorithms and they receive the frozen floor of the add-one smoothed softmax (predictions/analysis_choices.json). II6 has no scored algorithm in S, so qlik_top1 is None and II6 cannot be discordant. results/... forced_compliance per unit is in units.json.
- **labeller_revisions**: One revision round each, before the unit commits: II6 runtime rule (the tracer's patched deque reports '_patch.<locals>.deque.append', so pushes/pops are matched by method name) and II7 (heap insertion and insert-at-front shifting are 'other'; asserts are ignored by the AST rule; backward fill needs a hot index-decrement line). Both re-gated: kappa 1.0, holdout 6/6; every row of the unit was relabelled with the revised rules before its commit.
- **gold_set_instruct**: Gate (ii) instruct gold programs are the first 10 valid twin programs (vLLM slots k >= 10) rather than separate gate draws; base gold programs are the first 10 valid base-pilot programs (chat k 0-5).
- **base_audit_weak**: 15-program base audits: labeller vs two-family adjudication below 0.85 on all valid programs for II1 (0.40), II4 (0.73), II5 (0.80) and II7 (0.73), mostly on failing base programs; on correct base programs agreement is 1.0 except II1 (4/7). These units are flagged AUDIT_WEAK and a post-hoc sensitivity drops them.
- **scheduler_bug_no_data**: A readiness bug briefly scheduled ESC confirmation tasks before any ESC stage-1 sample existed; they found no stage-1 passers and wrote nothing. The daemon was fixed (confirmation waits for the complete stage-1 population) and restarted before the first ESC sample.
- **twin_hf_pads**: HF twin batches (k 0-9 per template) are padded to B = 20 with TWIN_EXTRA slots k 10-19; these rows are engine-check material only and never enter a decisive cell or the twin of 300.
- **vllm_no_crn**: vLLM rows use per-request seeds (sha256-derived) and are not CRN-paired with HF rows; the HF-vs-vLLM twin engine check (JS vs template-resampling null) passed for every unit except II3 (ENGINE_SPLIT).
- **screen_twin_baseline**: SCREEN B units' twin of 300 = the iteration-5 HF CRN slots k 0-9 (RTX 4090, vendored labels) + 150 new vLLM T 1.0 slots + 100 vLLM T 1.3 slots; their alpha-4 escape gate uses the same T 1.0 twin. The HF re-draw of the iteration-5 slots on this GPU is the engine check (per-slot agreement in results/engine_checks.json).
- **ii1_stress_queries**: II1 keeps the single-query signature solve(s, t); the plan's batch of 200 s-queries in the stress cases (to favour the position-list method) was not added. Every reference passes at <= 0.25 x the 1 s limit and the LCS table exceeds it.
- **no_staged_scaling**: Arms were not run in 10 -> 100 -> full stages: vLLM measured 7-34k programs/h and HF 7-14 s per 20-row batch in the first jobs (logs/vllm_*.log, results/timing.jsonl), and every planned arm then fit without drops except those listed here.
