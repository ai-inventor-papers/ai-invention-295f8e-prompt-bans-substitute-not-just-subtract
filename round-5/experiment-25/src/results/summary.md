### Units: gate, forecast (committed before any push) and outcome

| Unit | Gate (kappa / rt-vs-adj) | Default (twin share) | Base pass | beta [95% CI] | r_u | Pred. class | E (a1 / a2) | Landing L_u | PN excess S |
|---|---|---|---|---|---|---|---|---|---|
| A1 | gated (0.92 / 0.95) | hash_count (1.00) | 0.29 (29 correct) | 0.41 [0.26, 0.59] | boyer_moore_vote | MOVABLE | 0.125 (0.000 / 0.250) | boyer_moore_vote | 0.04 |
| A2 | gated (1.00 / 1.00) | kadane (1.00) | 0.43 (43 correct) | 0.00 [0.00, 0.08] | None | IMMOVABLE | 0.000 (0.000 / 0.000) | None | 0.00 |
| A3 | gated (0.82 / 0.90) | prefix_suffix_max (0.64) | 0.22 (22 correct) | 0.23 [0.10, 0.43] | two_pointers | MOVABLE | 0.438 (0.375 / 0.500) | two_pointers | -0.05 |
| A4 | gated (1.00 / 0.95) | eratosthenes (1.00) | 0.31 (31 correct) | 0.81 [0.64, 0.91] | trial_division | MOVABLE | 0.000 (0.000 / 0.000) | None | 0.00 |
| A5 | gated (0.84 / 0.90) | horizontal_scan (1.00) | 0.20 (20 correct) | 0.30 [0.15, 0.52] | vertical_scan | MOVABLE | 0.000 (0.000 / 0.000) | None | 0.15 |
| A6 | GATE_FAIL (0.74 / 0.89) | – | – | – | – | – | – | – | – |
| A7 | gated (1.00 / 1.00) | expand_center (1.00) | 0.28 (28 correct) | 0.46 [0.30, 0.64] | brute_force | MOVABLE | 0.188 (0.000 / 0.375) | brute_force | 0.13 |
| A8 (ext.) | gated (1.00 / 1.00) | greedy (1.00) | 0.19 (19 correct) | 0.47 [0.32, 0.63] | dp | MOVABLE | 0.000 (0.000 / 0.000) | None | 0.01 |
| A9 (ext.) | gated (1.00 / 1.00) | merge_two_pointers (1.00) | 0.24 (24 correct) | 0.71 [0.51, 0.85] | concat_sort | MOVABLE | 0.000 (0.000 / 0.000) | None | 0.02 |

### A1 / A2 -- Primary set (pre-registered units)

- n = 6 units (A1, A2, A3, A4, A5, A7); Spearman rho(beta, E) = -0.030, exact one-sided permutation p = 0.558; Kendall tau-b = 0.000; rho(beta, S) = 0.290.
- Collapsed (beta < 0.05) units that are immovable: 1.00 (n = 1); diverse (beta >= 0.2) units that are immovable: 0.40 (n = 5).
- Measurement-error bootstrap (2,000 replicates): median rho -0.091, 90% interval [-0.370, 0.213].
- Panel-level wording: not consistent with the pooled thresholds (rho >= 0.6, >= 80% collapsed immovable, beta ahead of each rival).

| Rival (sign) | rho(rival, E) | Delta = rho(beta,E) - sign*rho(rival,E) | 95% task-bootstrap CI |
|---|---|---|---|
| opening_margin (-) | -0.516 | -0.546 | [-1.29, 0.00] |
| merit_runtime_min (-) | -0.880 | -0.911 | [-2.00, 0.39] |
| merit_length_min (-) | -0.273 | -0.304 | [-1.50, 1.00] |
| twin_modal_share (-) | -0.696 | -0.726 | [-1.90, -0.09] |
| novelty_share (+) | -0.417 | 0.387 | [-0.38, 1.66] |

A2: 3 events (default, beta >= 0.05, observed movable); hits r_u == L_u: 3/3; Poisson-binomial P(H >= h) = 0.0185.

| Event | r_u | L_u | n realised | log score base | association | proximity |
|---|---|---|---|---|---|---|
| A1 | boyer_moore_vote | boyer_moore_vote | 35 | -0.063 | -1.812 | -1.636 |
| A3 | two_pointers | two_pointers | 160 | -0.054 | -1.119 | -1.122 |
| A7 | brute_force | brute_force | 33 | -0.625 | -1.119 | -0.945 |

Mean base - association = 1.103 nats (exact Wilcoxon two-sided p = 0.250); base - proximity = 0.987 nats (p = 0.250).

### A1 / A2 -- With the reserve extension (A8, A9)

- n = 8 units (A1, A2, A3, A4, A5, A7, A8, A9); Spearman rho(beta, E) = -0.327, exact one-sided permutation p = 0.801; Kendall tau-b = -0.267; rho(beta, S) = 0.108.
- Collapsed (beta < 0.05) units that are immovable: 1.00 (n = 1); diverse (beta >= 0.2) units that are immovable: 0.57 (n = 7).
- Measurement-error bootstrap (2,000 replicates): median rho -0.247, 90% interval [-0.518, 0.000].
- Panel-level wording: not consistent with the pooled thresholds (rho >= 0.6, >= 80% collapsed immovable, beta ahead of each rival).

| Rival (sign) | rho(rival, E) | Delta = rho(beta,E) - sign*rho(rival,E) | 95% task-bootstrap CI |
|---|---|---|---|
| opening_margin (-) | -0.518 | -0.846 | [-1.48, -0.18] |
| merit_runtime_min (-) | -0.655 | -0.982 | [-1.75, -0.13] |
| merit_length_min (-) | -0.273 | -0.600 | [-1.41, 0.39] |
| twin_modal_share (-) | -0.661 | -0.989 | [-1.82, -0.39] |
| novelty_share (+) | -0.429 | 0.101 | [-0.51, 0.97] |

A2: 3 events (default, beta >= 0.05, observed movable); hits r_u == L_u: 3/3; Poisson-binomial P(H >= h) = 0.0185.

| Event | r_u | L_u | n realised | log score base | association | proximity |
|---|---|---|---|---|---|---|
| A1 | boyer_moore_vote | boyer_moore_vote | 35 | -0.063 | -1.812 | -1.636 |
| A3 | two_pointers | two_pointers | 160 | -0.054 | -1.119 | -1.122 |
| A7 | brute_force | brute_force | 33 | -0.625 | -1.119 | -0.945 |

Mean base - association = 1.103 nats (exact Wilcoxon two-sided p = 0.250); base - proximity = 0.987 nats (p = 0.250).

### POST HOC: association rival with the corrected mapping (deviation D-assoc-mapping)

The committed association counts are 0 for every unit (every answer restates the default named in the question and the committed mapping took the earliest mention). Corrected mapping = earliest non-default mention, on the same pre-commitment answers:

| Unit | Association top-1 | Base r_u | Corrected counts |
|---|---|---|---|
| A1 | boyer_moore_vote | boyer_moore_vote | {'boyer_moore_vote': 20, 'sort_middle': 0, 'divide_conquer': 0, 'randomized_verify': 0, 'bit_count': 0, 'library_mode': 0} |
| A2 | prefix_min | None | {'prefix_min': 13, 'divide_conquer': 7, 'segment_tree': 0} |
| A3 | two_pointers | two_pointers | {'two_pointers': 20, 'monotonic_stack': 0, 'peak_split': 0} |
| A4 | atkin | trial_division | {'trial_division': 5, 'linear_sieve': 0, 'segmented_sieve': 0, 'sundaram': 0, 'atkin': 14} |
| A5 | vertical_scan | vertical_scan | {'vertical_scan': 16, 'sort_ends': 0, 'binary_search_length': 4, 'divide_conquer': 0, 'trie': 0, 'library_commonprefix': 0} |
| A7 | manacher | brute_force | {'dp_table': 0, 'manacher': 20, 'brute_force': 0} |
| A8 | dp | dp | {'dp': 11, 'bfs_indices': 9} |
| A9 | partition_binary_search | concat_sort | {'partition_binary_search': 20, 'heap_merge': 0, 'concat_sort': 0} |

A2 with the corrected association: base hits 3/3, association top-1 hits 2/3; log scores (base / association / proximity): A1 -0.063 / -0.274 / -1.636; A3 -0.054 / -0.143 / -1.122; A7 -0.625 / -2.868 / -0.945; mean base - association = 0.848 nats (exact Wilcoxon p = 0.250).

### 'Half + screen' (descriptive; Step 1's committed beta for the 15 existing tasks)

- Step 1 file hash verified against its commitments.log: True.
- All 21 units (6 new + 15 existing): rho(beta, E) = 0.543, one-sided permutation p = 0.0065; collapsed immovable 1.00 (n = 4), diverse immovable 0.50 (n = 10).
- Existing tasks only (n = 15): rho = 0.586, p = 0.0096; diverse immovable 0.60 (n = 5).
- Landing checks on escaping existing tasks: T03: Step 1 r = quickselect, L = size_k_heap (miss); T10: Step 1 r = dfs, L = dfs (hit).

### Extra arm A: the 15 existing tasks under the ban-free unit

| Task | Default | Twin off-default share / pass | E ban-free (a1 / a2) | Landing | Iteration 4 E (a1 / a2) | Frozen screen E (a1 / a2), movable | Verdict change |
|---|---|---|---|---|---|---|---|
| T03 | full_sort | 0.02 / 1.00 | 0.250 (0.125 / 0.375) | size_k_heap | 0.30 / 0.63 | 0.44 / 1.00, True | False |
| T10 | union_find | 0.00 / 1.00 | 0.125 (0.000 / 0.250) | dfs | 0.38 / 0.73 | 0.33 / –, True | False |
| T05 | hash_map | 0.00 / 1.00 | 0.000 (0.000 / 0.000) | None | 0.00 / 0.13 | 0.00 / 0.67, True | True |
| T06 | hash_set | 0.00 / 1.00 | 0.000 (0.000 / 0.000) | None | 0.00 / 0.00 | 0.00 / 0.33, True | True |
| T1 | bfs | 0.02 / 0.86 | 0.000 (0.000 / 0.000) | None | 0.05 / 0.13 | 0.07 / 0.00, True | True |
| T2 | dijkstra | 0.02 / 0.98 | 0.000 (0.000 / 0.000) | None | 0.18 / 0.20 | 0.20 / 0.00, True | True |
| T04 | naive | 0.00 / 1.00 | 0.000 (0.000 / 0.000) | None | 0.00 / 0.00 | 0.00 / 0.00, False | False |
| T08 | iteration | 0.00 / 1.00 | 0.000 (0.000 / 0.000) | None | 0.00 / 0.00 | 0.00 / –, False | False |
| T11 | quadratic_dp | 0.00 / 1.00 | 0.000 (0.000 / 0.000) | None | 0.00 / 0.00 | 0.00 / –, False | False |
| T13 | sort_sweep | 0.00 / 1.00 | 0.000 (0.000 / 0.000) | None | 0.00 / 0.00 | 0.00 / –, False | False |
| T14 | sort_by_count | 0.00 / 0.76 | 0.000 (0.000 / 0.000) | None | 0.00 / 0.00 | 0.00 / –, False | False |
| R1 | greedy_end | 0.00 / 1.00 | 0.000 (0.000 / 0.000) | None | 0.00 / 0.00 | 0.00 / –, False | False |
| R3 | kahn | 0.00 / 1.00 | 0.000 (0.000 / 0.000) | None | 0.00 / 0.00 | 0.00 / –, False | False |
| R6 | binary_search | 0.00 / 0.88 | 0.000 (0.000 / 0.000) | None | 0.00 / 0.00 | 0.00 / –, False | False |
| R2 | dfs_parent | 0.00 / 0.94 | 0.000 (0.000 / 0.000) | None | 0.00 / 0.00 | – / –, None | None |

### Engine check (bf16 vs the screen's FP8 rows): PRECISION SENSITIVITY: at least one cell outside the template-resampling null

| Cell | Per-slot label agreement | JSD | Null p95 | This run | Screen |
|---|---|---|---|---|---|
| T03|ECTWIN | 1.00 | 0.0000 | 0.0000 | {'full_sort': 50} | {'full_sort': 50} |
| T03|ECBAN_d9002_a1.0 | 0.74 | 0.0302 | 0.0766 | {'size_k_heap': 29, 'full_sort': 9, 'quickselect': 12} | {'quickselect': 16, 'full_sort': 15, 'size_k_heap': 19} |
| T2|ECTWIN | 0.98 | 0.0101 | 0.0000 | {'dijkstra': 49, 'bf_spfa': 1} | {'dijkstra': 50} |
| T2|ECBAN_d9004_a1.0 | 0.86 | 0.0074 | 0.0047 | {'dijkstra': 31, 'bf_spfa': 19} | {'dijkstra': 26, 'bf_spfa': 24} |

### Novelty audit

2 correct 'other' programs among 6854 correct programs; classes {'NOVEL_ALGORITHM': 0, 'CATALOGUE_VARIANT': 1, 'LABELLER_MISS': 0, 'DEGENERATE': 1, 'UNRESOLVED': 0}; statement: no correct novel algorithm (rule-of-three 95% upper bound 0.00044 per correct program).

### External cross-check (dependency thealgorithms_python, MIT; descriptive)

8/9 independent implementations pass the frozen hidden tests; runtime label = intended mode 7/9, AST 6/9.

| Unit | Implementation | Intended | Tests | Runtime | AST |
|---|---|---|---|---|---|
| A2 | dynamic_programming/max_subarray_sum.py | kadane | 70/70 | kadane | kadane |
| A2 | divide_and_conquer/max_subarray.py | divide_conquer | 0/70 (load error) | unknown | divide_conquer |
| A7 | strings/manacher.py | manacher | 73/73 | manacher | unknown |
| A4 | maths/sieve_of_eratosthenes.py | eratosthenes | 48/48 | eratosthenes | eratosthenes |
| A4 | maths/prime_sieve_eratosthenes.py | eratosthenes | 48/48 | eratosthenes | eratosthenes |
| A4 | maths/odd_sieve.py | eratosthenes | 48/48 | eratosthenes | eratosthenes |
| A4 | maths/segmented_sieve.py | segmented_sieve | 48/48 | segmented_sieve | eratosthenes |
| A4 | maths/sieve_of_atkin.py | atkin | 48/48 | atkin | atkin |
| A1 | other/majority_vote_algorithm.py | boyer_moore_vote | 71/71 | hash_count | hash_count |

### Repertoire check (do nudges reach beyond the base repertoire?)

| Unit | base Hill-1 (depth) | PN a1 | PN a2 | escape cells | correct off-default push programs outside the base repertoire |
|---|---|---|---|---|---|
| A1 | 1.97 (25) | 1.18 | 1.17 | 1.57 | 0 |
| A2 | 1.00 (25) | 1.00 | 1.00 | 1.00 | 0 |
| A3 | 1.71 (22) | 1.86 | 1.83 | 1.95 | 0 |
| A4 | 1.63 (25) | 1.00 | 1.00 | 1.00 | 0 |
| A5 | 2.11 (20) | 1.32 | 1.69 | 1.00 | 0 |
| A7 | 2.70 (25) | 1.31 | 1.59 | 1.62 | 0 |
| A8 | 1.93 (19) | 1.00 | 1.00 | 1.03 | 0 |
| A9 | 2.14 (24) | 1.00 | 1.17 | 1.11 | 0 |

### Knob rows (pass rate / off-default share / correct-only Hill-1 at depth 25)

| Unit | TWIN | PN_a1 | PN_a2 | T1.3 | NOVELTY | BASE | PLAINC |
|---|---|---|---|---|---|---|---|
| A1 | 1.00 / 0.00 / 1.00 | 1.00 / 0.04 / 1.18 | 1.00 / 0.04 / 1.17 | 1.00 / 0.00 / 1.00 | 1.00 / 0.00 / 1.00 | 0.29 / 0.42 / 1.97 | 0.52 / 0.40 / 2.47 |
| A2 | 1.00 / 0.00 / 1.00 | 1.00 / 0.00 / 1.00 | 1.00 / 0.00 / 1.00 | 1.00 / 0.00 / 1.00 | 1.00 / 0.00 / 1.00 | 0.43 / 0.02 / 1.00 | 0.22 / 0.02 / 1.00 |
| A3 | 1.00 / 0.36 / 1.91 | 1.00 / 0.32 / 1.86 | 1.00 / 0.30 / 1.83 | 1.00 / 0.36 / 1.91 | 0.97 / 0.00 / 1.00 | 0.22 / 0.22 / 1.71 | 0.12 / 0.25 / 2.75 |
| A4 | 1.00 / 0.00 / 1.00 | 1.00 / 0.00 / 1.00 | 1.00 / 0.00 / 1.00 | 1.00 / 0.00 / 1.00 | 1.00 / 0.00 / 1.00 | 0.31 / 0.72 / 1.63 | 0.14 / 0.49 / 1.98 |
| A5 | 0.94 / 0.00 / 1.00 | 0.96 / 0.08 / 1.32 | 0.98 / 0.22 / 1.69 | 0.88 / 0.00 / 1.00 | 0.97 / 0.27 / 1.98 | 0.20 / 0.39 / 2.11 | 0.26 / 0.62 / 1.54 |
| A7 | 1.00 / 0.00 / 1.00 | 1.00 / 0.08 / 1.31 | 1.00 / 0.18 / 1.59 | 1.00 / 0.06 / 1.25 | 1.00 / 0.00 / 1.00 | 0.28 / 0.59 / 2.71 | 0.10 / 0.52 / 1.00 |
| A8 | 1.00 / 0.00 / 1.00 | 1.00 / 0.00 / 1.00 | 0.98 / 0.02 / 1.00 | 0.98 / 0.00 / 1.00 | 1.00 / 0.00 / 1.00 | 0.19 / 0.47 / 1.93 | 0.14 / 0.16 / 1.82 |
| A9 | 1.00 / 0.00 / 1.00 | 1.00 / 0.00 / 1.00 | 1.00 / 0.04 / 1.17 | 1.00 / 0.00 / 1.00 | 0.67 / 0.20 / 1.00 | 0.24 / 0.74 / 2.14 | 0.24 / 0.43 / 1.57 |

### Pre-specified sensitivities (descriptive)

- primary: rho(beta_plain, E) = -0.091 (p = 0.583, n = 6); rho(beta_other, E) = -0.030 (p = 0.558, n = 6); rho(base_hill1, E) = 0.395 (p = 0.225, n = 6)
- with_extension: rho(beta_plain, E) = 0.164 (p = 0.351, n = 8); rho(beta_other, E) = -0.327 (p = 0.801, n = 8); rho(base_hill1, E) = 0.218 (p = 0.310, n = 8)

### Audit

- Independent stdlib re-derivation (audit/rederive.py): 0 mismatches.
- Placebo 1 (beta shuffled across units): mean rho over all permutations = 0.000.
- Placebo 2 (labels shuffled between twin and escape rows, 20 shuffles): A1 observed E 0.125 vs placebo mean 0.003; A2 observed E 0.000 vs placebo mean 0.000; A3 observed E 0.438 vs placebo mean 0.006; A4 observed E 0.000 vs placebo mean 0.000; A5 observed E 0.000 vs placebo mean 0.000; A7 observed E 0.188 vs placebo mean 0.000; A8 observed E 0.000 vs placebo mean 0.000; A9 observed E 0.000 vs placebo mean 0.000.
- Every unit's commitment precedes its first push row: True.
- OpenRouter spend: USD 0.357 (cap 2.00). GPU batch time: 0.98 h over 8620 sampled rows; 5 model loads.

### Deviations

- **D-iter1-purged**: ITER1/gen_art_experiment_5 (iteration-1 base compositions of T1/T2) is purged from the run volume. It is not needed: Step 1 of this iteration (gen_art_experiment_24, predictions/commit1.json, sha256 verified against its commitments.log) committed beta for all 15 existing tasks, so the 'half + screen' analysis uses those values and nothing is marked PENDING_STEP1.
- **D-A1-rebuild**: After the LABELLER_A1 commit the A1 builder was re-run once by mistake (while checking a shared tracer fix). tests.jsonl and build_report.json were rewritten: case ids, inputs, expected values and limits come from seeded generation and all limits are the 1 s floor, so the substance is identical, but the informational ref_times fields changed and the two files no longer match their commit hashes (verify_chain reports them as changed). The shared tracer fix (scan solve locals at return even after 400 scanned returns) changes no feature used by the A1 runtime rules. build5 now refuses to rebuild a frozen unit.
- **D-tracer-shared**: The shared tracer (newbench/common/tracer5.py) was extended after the A1-A3 labellers were frozen: (i) opcode counting for probes flagged trace_ops now uses sys.monitoring INSTRUCTION events (Python 3.12 drops settrace opcode events while a profile function is active); no A1-A3 probe sets trace_ops; (ii) bytearrays are included in the returned-locals list scan (list_lens / max_list_len); A1 uses no list feature, and A2/A3 programs with bytearrays of length >= n are not expected. From A4 on, the shared toolkit files are committed with each LABELLER_<unit> line.
- **D-validity-has-solve**: Shared validity bug fixed during the A6 revision round: a program counted as valid when the text "def solve" occurred anywhere, including in comments (a fully commented-out base program). Validity now requires a parsed function named solve (harness5.has_solve). Rows of the already-frozen units A1-A5 labelled before the fix with ast_label == invalid but valid == True are exactly these programs; they are re-marked invalid by src/fix_validity.py before the analysis, uniformly for every unit.
- **D-reserve-extension**: The mid-artifact rule (fewer than 5 gated units at 3:00) was not triggered: 6 of 7 planned units gated (A6 GATE_FAIL) and all planned GPU work finished by 2:05 into the run. With 4 h left, the two pre-specified reserves A8 (jump game) and A9 (median of two sorted lists) were built as a logged EXTENSION under the same protocol (spec frozen in specs5.py at 0:50, labeller gate, sha256 commitment before any push). The pre-registered panel (A1-A7 minus gate failures) is reported as primary; every analysis is repeated with the extension units as a secondary, clearly labelled set, and pooled_inputs.json flags them unit_kind=new_reserve_extension.
- **D-early-draws**: Scheduling: the full instruct twin (k 0-9, N = 50) of every unit was drawn in the first instruct load and the full base repertoire (k 0-19, N = 100) plus the plain-completion arm in the first base load, instead of twin k 0-1 / base k 0-5 at P1 and the rest after the gate. Under CRN the gold rows (twin k 0-1, base k 0-1) and the base pilot (k 0-5) are the same rows either way; drawing them in one batch shape avoids bf16 batch-shape drift. The builder read no sampled row before each unit's first gate computation. Plain completion ran at P3 with the other base jobs (planned P7) so the base model was loaded only twice.
- **D-states-compact**: states/<task>.npz stores, per twin template, the ban-free unit n[l, p] (blocks 12-23), the read-position states and the spec-position mean states (blocks 12-35, fp16) and the per-position norms, not every spec-position state vector (the pushes recompute the clean prefill in-process, so nothing downstream needs them).
- **D-ec-T2-twin**: The T2 twin cell of the engine check was first skipped by a resume-key bug (sampler5.done_keys ignored the task while two tasks shared data/raw/enginecheck.jsonl); the key now includes the task and the cell was re-run into data/raw/enginecheck_T2twin.jsonl with the identical CRN keys and batch shape.
- **D-recheck-late**: The Stage-0 labeller re-check of the 15 existing labellers and the T2 style re-gate (array-based Dijkstra -> dijkstra) ran 1:30 into the run, after Extra-arm-A stage 1 was labelled. The re-check matched every frozen gate within 0.02 with 100% on references, and the structural rule (label_worker5.array_dijkstra) fires on no T2 program of this run, so no existing label changed.
- **D-half-screen-code**: The plan's descriptive 'half + screen' combination (Step 1 beta + this run's Extra-arm-A E_t) is implemented in src/final_run.py, written after commit #0; it calls only the frozen a1_analysis function. The A6-T10 permutation cluster is moot because A6 failed its gate.
- **D-assoc-mapping**: Association rival bug found after the analysis: unit_commit.map_assoc took the earliest catalogue mention of each answer, but every answer restates the question ("The standard alternative to <default> ..."), so all answers mapped to the default and the committed survivor counts are 0 for every unit; the committed association forecast was therefore uniform. The committed prediction files are untouched. A deterministic corrected mapping (earliest NON-default mention) on the same 20 answers per unit, all sampled before each commitment, is reported POST HOC in results/assoc_corrected.json, and A2 recomputed with it by the frozen a2_analysis in results/a2_assoc_corrected*.json: association top-1 = base r_u on 4 of 8 units and = L_u on 2 of 3 events; the base composition still has the higher log score on all 3 events (mean margin 0.85 nats instead of 1.10).
