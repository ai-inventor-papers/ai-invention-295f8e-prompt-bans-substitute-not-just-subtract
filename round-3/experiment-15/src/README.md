# Where Llama goes when an algorithm is banned

This is the Llama-3.1-8B-Instruct replication of Claim 1, run on the frozen 12-task coding bench (exp11). Claim 1 says a ban removes the default algorithm and the model falls to its next rung. The model runs in bf16 at revision `0e9e39f`.

Every forecast below was computed ban-free and hash-chained in `commitments.log` before any ban prompt was rendered. The bans were then sampled and scored with the frozen C1 rule in `predictions/scoring.py`. The rows in `results/c1_events.jsonl` use the shared `c1_events` schema, so the next round can pool them with the Qwen rows.

## Headline

- **Within-Llama, pre-pooling branch: NO FAMILY ADVANCES (aimed, unresolved).**
- Events: 18 (12 modal and 6 present-minor).
- Gated (avoidance ≥ 0.5 and ≥ 20 non-banned attempts): 13.
- Disagreeing and gated: 11.
- Wins under the advance rule (≥ 0.10 nats over the runner-up): {'SUBTRACT': 1, 'ASSOCIATE': 1}. A family advances with ≥ 3 wins: none.
- Paired Wilcoxon signed-rank tests on per-event log-score differences, Holm-corrected at 0.05, with a task-cluster bootstrap 95% CI of the mean difference:
  - SUBTRACT-ASSOCIATE: mean 0.172 nats [-0.049, 0.606], n = 11, p = 0.5195, Holm-adjusted p = 1.0000, not rejected.
  - SUBTRACT-PROXIMITY: mean 0.345 nats [0.190, 0.633], n = 11, p = 0.0029, Holm-adjusted p = 0.0088, rejected.
  - LADDER-ASSOCIATE: mean 0.133 nats [-0.056, 0.542], n = 11, p = 0.7695, Holm-adjusted p = 1.0000, not rejected.
  - LADDER-PROXIMITY: mean 0.306 nats [0.204, 0.513], n = 11, p = 0.0020, Holm-adjusted p = 0.0078, rejected.
- Effective N: {'events': 18, 'gated': 13, 'disagreeing_gated': 11}. Below the pooled floor of 16 events, no 'confirmed' wording is used.
- Top-1 hits on gated events: SUBTRACT 4/12 (chance 0.26, binomial p 0.382); LADDER 7/13 (chance 0.27, binomial p 0.033); ASSOCIATE 7/13 (chance 0.27, binomial p 0.033); PROXIMITY 3/13 (chance 0.27, binomial p 0.712).
- Sensitivity with the frozen point-mass ASSOCIATE/PROXIMITY: branch NO FAMILY ADVANCES (aimed, unresolved), wins {'LADDER': 1, 'SUBTRACT': 1}.

### How to read this (within Llama, before pooling)

**The frozen rule does not resolve Llama's half of C1.**

- **Wins are rare.** 11 events are both gated and disagreeing, yet only 2 have a winning family by ≥ 0.10 nats.
  - SUBTRACT's single win (T05 hash_map) is its *undefined* fallback. The veto never left 20 non-banned attempts, so the rule scores SUBTRACT as uniform there. That flat forecast beats ASSOCIATE and PROXIMITY because the ban splits between sort-two-pointers (42) and brute force (32).
  - ASSOCIATE's single win is T03 present-minor heapify_pop, where it names quickselect.
- **Wilcoxon on 11 events** (the run is allowed at ≥ 10). SUBTRACT and LADDER both beat PROXIMITY, and the difference survives Holm correction. Neither separates from ASSOCIATE.
  - In Llama, code-proximity nominations are the worst forecasts.
  - Association, subtraction and the generic ladder cannot be told apart at this N.
- **Top-1 hit rates.** LADDER and ASSOCIATE each hit the realised landing on 7 of 13 gated events, against a chance rate of about 0.27 (exact binomial p = 0.033 each). SUBTRACT hits 4 of 12 and PROXIMITY 3 of 13. So the landing is *aimed*: it is predictable above chance. But no family wins it on log score.
- **The verdict is fragile.**
  - Three of the ten sensitivity rows give SUBSTITUTION (ASSOCIATE advances with 3 wins): correct-only rescoring, the bf16-only decision set, and dropping template W4.
  - Excluding the D-from-attempts task and the label-audit-flagged tasks leaves 5 disagreeing gated events, which gives X-SPECIFIC BUT UNAIMED.
  - With N = 11 disagreeing gated events, below the pooled floor of 16, this is Llama's direction-only contribution to the pooled test. It confirms nothing.

**Five defaults resist the ban itself.** R1 greedy_end, R3 kahn, T13 sort_sweep, R6 binary_search and T11 quadratic_dp fail the event gate (avoidance 0.04–0.30). Llama keeps writing its default even when told not to. On R3 and R6 the default reaches ≥ 0.96 of the last veto round.

**Surface-token vetoes rarely remove a default.** Only T14 heap collapses (0.02 once both `(k` and ` heapq` are masked). Elsewhere the default re-emerges at 0.20–0.96 in the last executed persistent round, with final-label shares recomputed after the decode fix:

- the lowest are union_find at 0.23 and full_sort at 0.20, the latter after a single comma veto that co-vetoes every survivor;
- hash_map (0.89), sort_sweep (0.88), kahn and binary_search (0.96) barely move.

The default is therefore not carried by any small set of surface tokens. SUBTRACT is undefined on the five tasks where no round left 20 non-banned attempts.

**Present-minor X-specific gain (H5).** Where the ban and the persistent veto remove the same minor algorithm, the associate gains more under the *named* ban on two of six events:

- T03 heapify_pop → quickselect: +0.25 [0.12, 0.37];
- T03 quickselect → full_sort: +0.24 [0.10, 0.36].

On T04 kmp the associate (rabin_karp) is *less* frequent under the ban: −0.08 [−0.17, −0.00]. On the remaining three events the difference is about 0. Naming the banned algorithm sometimes steers the model toward its associate beyond what removing it achieves, but not consistently.

**Pushes (knob view).** The nonce ban leaves D near its baseline on most tasks, which passes the sanity check. Matched-norm random directions move D substantially on a few tasks: T08 matrix_power 0.76 → 0.16–0.51, T14 heap 0.62 → 0.39–0.56. The novelty instruction lowers D almost everywhere.

**'other' labels.** A second blind judge re-audited 187 ban outputs labelled 'other'. It called 8 of them (4%) the banned algorithm and 24 a catalogue survivor. The 'other' columns are never folded into avoidance.

**Path-task screen (descriptive).**

- **The vetoes fire but do not move the defaults.** The signature veto fires on 25/50 (T1) and 40–48/50 (T2) pass-1 samples. BFS (0.52–0.58) and Dijkstra (0.78–0.82) re-emerge through other surface forms in every one of the three rounds.
- **T1.** All four families agree on DFS, which is exp10's realised landing (63 of 71 non-banned).
- **T2.** The ban's large 'other' mass (37/100 in exp10) is not reproduced by any veto round (8/50 'other' in each). The novelty instruction comes close (18/50 'other'). On T2 the ban acts unlike removal of Dijkstra's surface tokens.

### Per event (ban landing vs ban-free forecasts)

Each event bans one algorithm; N = 100 = W1–W5 × 20.

- **s_X**: the banned algorithm's attempted share in the decision set.
- **avoid**: 1 minus the banned share among attempted programs.
- **hit**: the modal non-banned label for modal events, or the excess label for present-minor events.
- **SUB / LAD / ASSOC / PROX**: each family's top-1 on its transferred component, with its mean log score per non-banned attempt in brackets. A dash means the family is undefined, and it is then scored as uniform.

| event | s_X | avoid | gate | n non-banned | hit | SUB | LAD | ASSOC | PROX | RENORM ls | winner (margin) | Hill_cc (n correct) | other / invalid |
|---|--:|--:|:-:|--:|---|---|---|---|---|--:|---|---|---|
| T03 ban full_sort | 0.17 | 0.95 | ✓ | 87 | quickselect | heapify_pop (-1.71) | other (-1.46) | quickselect (-1.40) | size_k_heap (-1.66) | -1.64 | – (0.06) | 1.00 (15) | 0.09 / 0.08 |
| T04 ban naive | 0.54 | 0.79 | ✓ | 64 | kmp | rabin_karp (-1.20) | kmp (-1.25) | kmp (-1.18) | builtin (-1.83) | -1.20 | – (0.02) | 1.38 (20) | 0.05 / 0.19 |
| T06 ban hash_set | 0.44 | 0.76 | ✓ | 71 | other | other (-0.98) | other (-1.00) | floyd (-1.53) | sort_adjacent (-1.37) | -1.02 | – (0.02) | 3.59 (7) | 0.53 / 0.06 |
| T05 ban hash_map | 0.97 | 0.91 | ✓ | 86 | sort_two_pointers | – (-1.39) | other (-1.90) | sort_two_pointers (-1.94) | brute_force (-2.37) | -1.39 | SUBTRACT (0.51) | 1.63 (34) | 0.07 / 0.05 |
| T10 ban union_find | 0.75 | 0.82 | ✓ | 78 | dfs | dfs (-1.00) | dfs (-0.80) | dfs (-0.98) | dfs (-0.98) | -0.98 | – (0.18) | 1.68 (42) | 0.04 / 0.05 |
| R1 ban greedy_end | 0.63 | 0.29 | ✗ | 26 | other | other (-0.89) | other (-0.97) | dp_bisect (-1.51) | memo_recursion (-1.59) | -0.85 | – (0.08) | – (0) | 0.21 / 0.11 |
| T08 ban matrix_power | 0.76 | 0.79 | ✓ | 72 | iteration | other (-1.13) | iteration (-1.10) | fast_doubling (-2.31) | memo_recursion (-1.94) | -1.21 | – (0.03) | 1.72 (44) | 0.13 / 0.09 |
| R3 ban kahn | 0.98 | 0.18 | ✗ | 17 | dfs_postorder | – (-1.39) | – (-1.39) | dfs_postorder (-0.92) | source_removal (-3.81) | -1.39 | – (0.46) | 1.00 (1) | 0.04 / 0.04 |
| T13 ban sort_sweep | 1.00 | 0.30 | ✗ | 25 | other | – (-1.11) | – (-1.11) | union_find (-3.13) | interval_tree (-3.71) | -1.11 | – (0.00) | – (0) | 0.23 / 0.18 |
| R6 ban binary_search | 0.99 | 0.04 | ✗ | 2 | other | – (-1.11) | – (-1.11) | bisect_module (-3.76) | bisect_module (-3.76) | -1.11 | – (0.00) | 1.00 (1) | 0.02 / 0.03 |
| T14 ban heap | 0.62 | 0.89 | ✓ | 84 | sort_by_count | sort_by_count (-0.74) | sort_by_count (-0.68) | sort_by_count (-0.70) | sort_by_count (-0.70) | -0.66 | – (0.02) | 1.31 (13) | 0.05 / 0.06 |
| T11 ban quadratic_dp | 0.87 | 0.23 | ✗ | 22 | patience_bisect | – (-1.10) | – (-1.10) | fenwick (-2.56) | patience_bisect (-1.02) | -0.83 | – (0.08) | 1.00 (8) | 0.09 / 0.05 |
| T14 ban* sort_by_count | 0.36 | 0.82 | ✓ | 75 | quickselect_counts | heap (-1.05) | heap (-1.02) | heap (-1.06) | bucket_sort (-1.34) | -1.02 | – (0.03) | 1.19 (24) | 0.09 / 0.09 |
| T03 ban* heapify_pop | 0.33 | 0.88 | ✓ | 77 | quickselect | other (-1.54) | full_sort (-1.57) | quickselect (-1.33) | size_k_heap (-1.81) | -1.57 | ASSOCIATE (0.21) | 2.57 (27) | 0.09 / 0.12 |
| T03 ban* quickselect | 0.12 | 0.76 | ✓ | 71 | full_sort | full_sort (-1.65) | full_sort (-1.73) | full_sort (-1.56) | size_k_heap (-1.79) | -1.73 | – (0.09) | 2.12 (34) | 0.10 / 0.06 |
| T04 ban* kmp | 0.26 | 0.70 | ✓ | 66 | bmh | other (-0.99) | naive (-1.01) | rabin_karp (-1.22) | naive (-1.01) | -1.01 | – (0.01) | 1.14 (34) | 0.09 / 0.06 |
| T10 ban* dfs | 0.25 | 0.89 | ✓ | 85 | bfs | union_find (-0.35) | union_find (-0.34) | union_find (-0.34) | bfs (-0.47) | -0.34 | – (0.00) | 1.15 (65) | 0.02 / 0.04 |
| T03 ban* size_k_heap | 0.24 | 0.84 | ✓ | 78 | full_sort | heapify_pop (-1.68) | full_sort (-1.72) | quickselect (-1.70) | heapify_pop (-1.88) | -1.72 | – (0.02) | 2.23 (27) | 0.10 / 0.07 |

Landing counts, correct-only counts, Wilson intervals, disguise rates and the baseline's own non-X share are in `results/analysis.json` (`events.<id>.table`) and `results/c1_events.jsonl`.

### Sensitivities (H3)

- point_mass: NO FAMILY ADVANCES (aimed, unresolved) (wins {'LADDER': 1, 'SUBTRACT': 1}, disagreeing gated 11)
- drop_coveto: NO FAMILY ADVANCES (aimed, unresolved) (wins {'SUBTRACT': 1, 'ASSOCIATE': 1}, disagreeing gated 8)
- correct_only: SUBSTITUTION (ASSOCIATE) (wins {'ASSOCIATE': 3, 'SUBTRACT': 1, 'PROXIMITY': 1}, disagreeing gated 11)
- excl_D_from_attempts_and_audit_flagged: X-SPECIFIC BUT UNAIMED (wins none, disagreeing gated 5)
- leave-one-template-out: drop_W1: NO FAMILY ADVANCES (aimed, unresolved) (wins {'SUBTRACT': 1, 'ASSOCIATE': 1}); drop_W2: NO FAMILY ADVANCES (aimed, unresolved) (wins {'SUBTRACT': 1, 'ASSOCIATE': 1}); drop_W3: NO FAMILY ADVANCES (aimed, unresolved) (wins {'SUBTRACT': 1, 'ASSOCIATE': 1}); drop_W4: SUBSTITUTION (ASSOCIATE) (wins {'ASSOCIATE': 3, 'SUBTRACT': 1}); drop_W5: NO FAMILY ADVANCES (aimed, unresolved) (wins {'SUBTRACT': 1, 'ASSOCIATE': 2})
- decision_set_bf16_only: SUBSTITUTION (ASSOCIATE) (wins {'ASSOCIATE': 3, 'SUBTRACT': 1}, disagreeing gated 11)

### Signature vetoes (D2/D3): is the default carried by surface tokens?

Each veto uses the event's frozen signature n-gram. The table gives the share of the banned algorithm A among veto attempts per round, using the persistent (iterated) arm and weighted counts for present-minor events.

| event | round-1 n-gram | A share r1 | r2 | r3 | stopped / note |
|---|---|--:|--:|--:|---|
| T03 ban full_sort | "," | 0.20 | – | – |  co-vetoed: counting_sort, heapify_pop, median_of_medians, quickselect, size_k_heap |
| T04 ban naive | "1):\n" | 0.44 | 0.42 | 0.54 | not carried by a small set of surface tokens co-vetoed: rabin_karp |
| T06 ban hash_set | " nums:\n       " | 0.38 | 0.26 | 0.26 | not carried by a small set of surface tokens |
| T05 ban hash_map | " i]\n" | 0.93 | 0.95 | 0.89 | not carried by a small set of surface tokens |
| T10 ban union_find | " def find" | 0.59 | 0.57 | 0.23 | not carried by a small set of surface tokens |
| R1 ban greedy_end | ".sort" | 0.60 | 0.50 | 0.36 | not carried by a small set of surface tokens co-vetoed: dp_bisect |
| T08 ban matrix_power | " matrix" | 0.46 | 0.43 | 0.28 | not carried by a small set of surface tokens |
| R3 ban kahn | " queue" | 0.98 | 0.96 | 0.96 | not carried by a small set of surface tokens |
| T13 ban sort_sweep | "\ndef solve" | 0.84 | 1.00 | 0.88 | not carried by a small set of surface tokens |
| R6 ban binary_search | " = 0," | 0.98 | 0.96 | 0.96 | not carried by a small set of surface tokens |
| T14 ban heap | "(k" | 0.57 | 0.02 | – |  |
| T11 ban quadratic_dp | "[j] +" | 0.85 | 0.83 | 0.80 | not carried by a small set of surface tokens |
| T14 ban* sort_by_count | " [" | 0.37 | 0.34 | 0.35 | not carried by a small set of surface tokens co-vetoed: heap, quickselect_counts |
| T03 ban* heapify_pop | " {}\n   " | 0.25 | 0.15 | – |  |
| T03 ban* quickselect | " quick" | 0.12 | – | – |  |
| T04 ban* kmp | "                j" | 0.26 | 0.24 | – |  |
| T10 ban* dfs | " dfs" | 0.17 | – | – |  |
| T03 ban* size_k_heap | ".n" | 0.09 | – | – |  |

Re-emergence surfaces (imports, and the vetoed text reappearing through other tokens) are in `results/veto_reemergence_table.md` and `data/veto_summary.json`.

**C2b (descriptive).** 2 events have a one-shot veto that moves ≥ 50% of X attempts. On 0 of them (share 0.00), the one-shot landing shares its modal survivor with the ban AND lies within the template-bootstrap JSD null. The pre-registered bar of 2/3 is quoted for reference only.

**Present-minor X-specific gain (H5).** For each event, the table compares the associate's share under the ban with its share under the persistent veto. Substitution predicts ban > veto; subtraction predicts equality.

| event | associate | ban share | veto share | baseline share | ban − veto [Newcombe 95%] |
|---|---|--:|--:|--:|---|
| T14 ban* sort_by_count | heap | 0.59 | 0.63 | 0.62 | -0.04 [-0.18, 0.10] |
| T03 ban* heapify_pop | quickselect | 0.42 | 0.17 | 0.12 | 0.25 [0.12, 0.37] |
| T03 ban* quickselect | full_sort | 0.44 | 0.20 | 0.17 | 0.24 [0.10, 0.36] |
| T04 ban* kmp | rabin_karp | 0.04 | 0.12 | 0.12 | -0.08 [-0.17, -0.00] |
| T10 ban* dfs | union_find | 0.82 | 0.81 | 0.75 | 0.01 [-0.10, 0.12] |
| T03 ban* size_k_heap | quickselect | 0.22 | 0.18 | 0.12 | 0.04 [-0.08, 0.15] |

### Path-task screen (H6; descriptive, never pooled)

The same ban-free families are scored against exp10's existing Llama ban landings. Prompts come from exp10's own builders, and our copy reproduces exp10's sampled ban prompts byte-for-byte: 10/10. Labels come from exp10's canon labeller. LADDER here pools the nonce ban and the novelty instruction only.

| task | exp10 ban landing | hit | SUB | LAD | ASSOC | PROX | winner (margin) | veto: banned share by round |
|---|---|---|---|---|---|---|---|---|
| t1 | {"dfs": 63, "bfs": 29, "other": 6, "astar_gbfs": 1, "dijkstra": 1} | dfs | dfs (-0.54) | dfs (-0.88) | dfs (-0.47) | dfs (-0.47) | – (0.00) | " queue:\n       ": r1 0.56, r2 0.52, r3 0.58 |
| t2 | {"dijkstra": 43, "bf_spfa": 18, "other": 37, "floyd": 2} | other | – (-1.59) | – (-1.59) | bf_spfa (-1.79) | floyd (-2.81) | – (0.00) | " continue": r1 0.82, r2 0.78, r3 0.80 |

## Defaults and events (frozen before any ban; `predictions/events.json`)

| task | X0 (FP8 pilot) | D | D from attempts | decision set (homogeneity p) | n valid | n correct | s_D | Hill_cc |
|---|---|---|:-:|---|--:|--:|--:|--:|
| T03 | heapify_pop | full_sort |  | pooled_pilot+B1 (0.975) | 94 | 18 | 0.17 | 3.80 |
| T04 | naive | naive |  | pooled_pilot+B1 (0.431) | 89 | 49 | 0.54 | 2.00 |
| T06 | hash_set | hash_set |  | pooled_pilot+B1 (0.844) | 93 | 34 | 0.44 | 1.48 |
| T05 | hash_map | hash_map |  | pooled_pilot+B1 (1.000) | 99 | 84 | 0.97 | 1.07 |
| T10 | union_find | union_find |  | pooled_pilot+B1 (0.814) | 97 | 74 | 0.75 | 1.59 |
| R1 | greedy_end | greedy_end | yes | pooled_pilot+B1 (0.199) | 89 | 8 | 0.63 | 2.46 |
| T08 | matrix_power | matrix_power |  | pooled_pilot+B1 (0.744) | 96 | 44 | 0.76 | 1.78 |
| R3 | kahn | kahn |  | pooled_pilot+B1 (0.494) | 99 | 88 | 0.98 | 1.06 |
| T13 | sort_sweep | sort_sweep |  | pooled_pilot+B1 (1.000) | 89 | 65 | 1.00 | 1.00 |
| R6 | binary_search | binary_search |  | pooled_pilot+B1 (0.495) | 93 | 54 | 0.99 | 1.10 |
| T14 | heap | heap |  | pooled_pilot+B1 (0.573) | 86 | 22 | 0.62 | 1.80 |
| T11 | quadratic_dp | quadratic_dp |  | pooled_pilot+B1 (0.717) | 94 | 68 | 0.87 | 1.08 |

Present-minor events (≥ 10% of correct programs, ≥ 3 correct, task ≥ 10 correct): T14 sort_by_count (6/22), T03 heapify_pop (4/18), T03 quickselect (4/18), T04 kmp (9/49), T10 dfs (13/74), T03 size_k_heap (3/18).

## Tests

| test | result |
|---|---|
| T0 input integrity (`results/input_integrity.json`) | bench sha256 all ok: True; canon SHA256SUMS ok: True; model shards = exp10: True |
| tests_hooks_hf | passed: True |
| tests_hooks_vllm | passed: True |
| tests_prompts | passed: True |
| tests_sampler | passed: True |
| tests_scoring | passed: True |
| tests_screen_prompts | passed: True |
| tests_veto | passed: True |
| tests_veto_synthetic | passed: True |
| A3/T0 labeller re-check (`results/labeller_recheck.json`) | bench references 50/50 (runtime and AST); runtime vs adjudicated gold 0.959; tasks < 0.90: none; canon (quoted from exp10, unchanged files) 22/22 |
| T8 commitment timing | every committed prediction file (utc entry and mtime) precedes the first ban sample: True (10 entries); pre-commit grep audit: 0 ban prompts in 10328 rows |
| T9 confirmation signals | bf16 neutral-twin modal label = FP8 pilot modal label on 11/12 tasks; nonce bans leave D near baseline (knob view); one-shot vetoes move ≥ 0.4 of X attempts on T03, T13, T08 and three present-minor events |
| T10 independent re-derivation (`audit/rederive.py`) | 0 mismatches; branch match True; hash chain ok True; family-permutation placebo: any family advances in 0.00 of 1,000 permutations |
| Statistical re-derivation (`audit/rederive_tests.py`, no src/ or scipy) | all match: True. Exact enumeration Wilcoxon p equal to the reported values; Holm decisions, top-1 hits, binomial p, and D for 12/12 tasks. Placebos fail as required: family labels permuted within events give Holm rejection rates 0.007–0.010; a random top-1 predictor gives p < 0.05 in 0.018 of 1,000 draws |
| C3 Llama label audit (second blind judge openai/gpt-4.1-mini) | agreement 0.88 on 60 programs; tasks below 0.85: ['R1', 'T03', 'T05', 'T14'] |

Compute: 0.98 GPU-hours of logged generation on one NVIDIA L4. That figure excludes vLLM startup, veto rounds and HF forward passes; GPU sessions held the L4 for about 1.8 hours of wall time in all. OpenRouter judge spend was USD 0.483 in total (USD 0.117 of it from the screen's canon judge), against this artifact's cap of USD 0.70.

## Deviations and drops

Each entry gives its reason and cost; the full list is in `results/deviations.json`.

- **hardware**: One NVIDIA L4 (23 GB, 300 GB/s), 6 CPUs, 57 GB RAM instead of the planned RTX A4500. *Cost:* Slower decoding; bf16 still fits (KV cache 41,200 tokens). No change to the model or decoding.
- **hf_cache_location**: Weights are read from the run's shared HF cache (HF_HUB_CACHE), not a workspace hf_cache/. *Cost:* None; shard sha256s verified against exp10 (results/model_record.json). No hf_cache/ in the workspace.
- **rlimit_gpu**: RLIMIT_AS is set only for CPU stages (24 GB), not for GPU sessions. *Cost:* GPU processes rely on the container cgroup limit (57 GB) instead of a catchable MemoryError.
- **vllm_eager**: vLLM 0.11 runs with enforce_eager=True and TORCHDYNAMO_DISABLE=1. *Cost:* Speed only.
- **max_num_seqs**: max_num_seqs 32 for B1/B4, then 64 for every later session. *Cost:* None for the sampling distribution (explicit per-request seeds; batch-shape numerics only).
- **push_engine**: The random-direction pushes (E3) run in vLLM with prefill-only forward hooks on decoder layers 11-21 (same arithmetic as the planned HF hooks: n_{l,i} * r_l added to the residual stream at the spec positions of registered prompts); prefix caching is off in that session. HF is used for the prompt-only ban norms (E1) and the hook tests (T4). *Cost:* None measured: zero-norm hook run identical to the hook-free run 10/10; perturbed-token count exact; added/target norm 0.9998.
- **cumulative_displacement**: T4 'realised layer-21 displacement within 10% of n_21' is met for the per-layer ADDED vector (ratio 1.000), not for the cumulative stream displacement, which is ~3x n_21 because pushes at layers 11-20 propagate. *Cost:* The random pushes displace layer 21 more than the ban does (reported in results/tests_hooks_hf.json); LADDER inputs are therefore generous pushes.
- **gen_ids_storage**: Generated token ids are stored inline in data/raw_gen.jsonl (out_ids), not data/gen_ids/*.npz. *Cost:* None.
- **mode_count**: The 12 frozen tasks have 50 modes (54 includes the excluded R2), so B2 = B3 round 1 = 1,000 requests. *Cost:* None.
- **judge_rate_limits**: Transient HTTP 429 from the j1 judge provider; failed calls were retried by the next combine pass (cache keyed by code sha), never counted as labels. *Cost:* None (no unresolved label kept unless reported).
- **proximity_programs**: 'Correctly labelled Llama forced programs' = forced programs labelled as requested (adherent), any pass status; a survivor with none uses its bench reference (flagged in predictions/proximity.json). *Cost:* Noisier nomination for low-n modes.
- **analysis_after_commit**: The frozen scoring rule (src/scoring.py) and forecast code (src/forecasts.py) were copied into predictions/ and hash-chained before the first ban sample; src/analysis.py (descriptive layers, sensitivities, tables) was completed after the commit. *Cost:* Descriptive layers were not pre-registered as code; the C1 rule and every forecast were.
- **unaimed_test**: 'No family's top-1 hits the landing more often than chance' is tested with a one-sided exact binomial test at 0.05 against the mean chance rate 1/|S| over gated events; if no family advances but some family is above chance the branch is 'NO FAMILY ADVANCES (aimed, unresolved)'. *Cost:* One interpretive choice.
- **sampler_rerun**: T2: identical-seed reruns reproduce 16/20 samples exactly (prefix-cache/batch numerics); T=1.0 vs a deliberate T=0.6 run at the same seeds are identical in 3/20 (defaults do not leak). *Cost:* None.
- **veto_decode**: Veto continuations were first decoded with HF's default clean_up_tokenization_spaces=True, which rewrites spacing such as ' ,' -> ',' (594 of 3,104 hit rows; extracted code changed in 590). Before the commit, every hit row was re-decoded exactly (clean_up_tokenization_spaces=False, identical to vLLM's own detokenisation: 0/600 mismatches on B4) and the 590 programs were re-labelled (results/veto_decode_fix.json). *Cost:* The iterated-round decisions (which rounds ran, which n-grams were added) were taken on the first labels; the committed forecasts use the corrected labels.
- **screen_twins**: Screen prompts use exp10's own builders verbatim (src/config.py copied to screen10/config.py with its workspace import patched; neutral twins padded with ' -'); exp10's canonical labeller runs from a writable copy (screen10/canon) whose judge is exp10's (openai/gpt-4.1-mini). *Cost:* Two labellers in one artifact (bench and canon); never pooled.
- **drop G3_exposure**: Optional copy/exposure arm (G3) not run. Drop order item 1 (time budget on the L4). *Cost:* No SUBTRACT-IN-CONTEXT row.
- **drop screen_random_directions**: The path-task screen ran B6 (vetofree pass-1, nonce, novelty), D4 (one-shot, persistent and iterated vetoes) and H6 scoring, but no random-direction pushes on T1/T2: the screen's LADDER pools the nonce ban and the novelty instruction only. Drop order (random directions are cut before the vetoes); the screen was added after the bench pipeline finished. *Cost:* The screen LADDER has fewer generic pushes than the bench LADDER.
- **drop frlp**: FRLP not run. Descriptive only in iteration 3; no Llama bench FRLP sets exist. *Cost:* None for C1.
- **drop hf_topk_test**: T2's HF top_k=0 assertion is moot: no HF sampling is done (HF only runs forward passes). Pushes sampled in vLLM (see push_engine). *Cost:* None.

## What was done

1. **Setup and provenance (A).** The frozen bench (exp11) and the exp10, exp8 and exp7 inputs were copied read-only into `inputs/`.
   - Every bench file was checked against `bench/commitment.json`, and exp10's canon against its `SHA256SUMS`.
   - The four model shards were checked against exp10's record.
   - `X0` was frozen first: the modal attempted label of exp11's FP8 Llama pilot.
2. **Label-independent generations (B).** All use vLLM 0.11 with token-id prompts and every SamplingParams field explicit: T = 1.0, top-p = 1.0, top-k off, min-p 0, `generation_config='vllm'`.
   - B1: 600 neutral-twin baseline samples.
   - B2: 1,000 association answers.
   - B3: forced programs, 1,000 in round 1 and 540 in round 2.
   - B4: 600 veto pass-1 samples.
   - B5: 600 nonce bans and 600 novelty prompts.
   - Neutral twins are token-length matched under Llama's tokenizer with `' .'` padding. Their ids are identical from `Task:` to the end (500/500 pairs pass).
3. **Labels and freezes (C).** Each program is labelled with the bench runtime tracer (primary) and the AST rules, with a blind judge (gemini-2.5-flash-lite, name-scrubbed code) on disagreements only.
   - **Decision set:** the FP8 pilot plus B1, after a Fisher-Freeman-Halton Monte Carlo homogeneity test.
   - **Default D:** the modal *correct* label when there are ≥ 10 correct programs and a lead ≥ 2; otherwise the modal attempted label.
   - **Present-minor events:** ≥ 10% of correct programs, ≥ 3 correct, and a task with ≥ 10 correct programs.
   - **ASSOCIATE targets:** taken from Llama's own association answers.
4. **Signature n-grams and exact vetoes (D).**
   - **N-gram rule:** n ≤ 6, present in ≥ 80% of the target's programs and of its generated ids. Among those, the one that minimises the worst-case collateral share in other algorithms' forced programs.
   - **One-shot and persistent vetoes:** done by truncate-and-redraw. The redraw uses `logit_bias = -100`, then the run continues, unmasked for one-shot and with a request-level `AdapterLogitsProcessor` mask for persistent, which also sees the prompt tail. The two arms share pass-1 and the redraw, and use the same continuation seed.
   - **Iterated rounds:** run while the default re-emerges in ≥ 20% of attempts, up to 3 rounds.
5. **Matched-norm random directions (E).**
   - HF prompt-only forward passes give the ban's own displacement norm n_{l,i} (ban vs twin, fp32) at the spec positions of layers 11–21.
   - Three seeded unit directions per layer are added at those norms during prefill only, in vLLM through forward hooks: 1,800 samples.
6. **Forecasts and commitment (F).**
   - SUBTRACT, LADDER, ASSOCIATE and PROXIMITY. ASSOCIATE and PROXIMITY use the mass-transfer form; point-mass forms are kept as sensitivities.
   - PROXIMITY uses Zhang-Shasha distance on identifier-normalised ASTs, with the bench token Levenshtein as a sensitivity.
   - Smoothing is 0.93 f + 0.05 U(S) + 0.02 δ(other).
   - A grep audit shows 0 ban prompts were rendered before the commit. `predictions/` was then made read-only.
7. **Bans (G).** 12 modal bans plus 6 present-minor bans, each W1–W5 × 20.
8. **Path-task screen (B6/D4/H6, descriptive).** On exp10's two path tasks, 300 new generations were run (vetofree pass-1, nonce, novelty), followed by one-shot, persistent and iterated vetoes of BFS (T1) and Dijkstra (T2). The resulting forecasts are scored against exp10's existing ban landings and never pooled with the bench.
9. **Analysis (H).** The frozen C1 rule, sensitivities, C2b-descriptive, the present-minor gain, the knob view, figures, and an independent re-derivation with a placebo.

## Layout

| path | what it is |
|---|---|
| `method.py` | CLI orchestrator, one sub-command per stage: `setup gen1 label freeze assoc hf push veto proximity commit ban analyse screen`. |
| `src/ws.py` | Paths, frozen constants, seeds (`sha256(task\|cond\|tpl\|sample)`), and jsonl helpers. |
| `src/prompts_llama.py` | Llama-3.1 renderer (date_string 26 Jul 2024, BOS and tail asserts). Builds ban, neutral-twin, nonce, novelty, forced, association and copy prompts. |
| `src/engine_vllm.py` | vLLM engine, explicit SamplingParams, `VetoAdapter` (persistent n-gram mask) and `PushHooks` (prefill-only random-direction hooks). |
| `src/engine_hf.py` | HF ban-displacement norms, seeded directions (sha256 recorded), and the T4 hook tests. |
| `src/jobs.py` | Request builders per phase and the staged 10 → 100 → rest, resumable runner with timings. |
| `src/label.py` | Extraction rule, bench labellers, judge on disagreements, association mapping, and the Llama label audit. |
| `src/freeze.py` | Decision set, homogeneity test, D, present-minor events, and ASSOCIATE targets. |
| `src/ngrams.py`, `src/veto.py`, `src/veto_job.py` | Signature n-grams; exact truncate-and-redraw; iterated veto rounds. |
| `src/proximity.py` | Zhang-Shasha on identifier-normalised ASTs and the canon token Levenshtein. |
| `src/forecasts.py`, `src/scoring.py` | Forecast families and the frozen C1 scoring rule (both copied into `predictions/` and hash-chained). |
| `src/analysis.py`, `src/outputs.py`, `src/figures.py` | Step H analysis, `method_out.json`, and figures. |
| `src/screen.py`, `screen10/` | Path-task screen: exp10's config (paths patched) and a writable copy of exp10's canon labeller. |
| `data/screen_raw.jsonl`, `data/screen_labels.jsonl`, `data/screen_veto_summary.json`, `results/screen.json` | Screen generations, labels, veto rounds, and scores. |
| `audit/rederive.py` | Independent re-derivation from the raw files, a family-permutation placebo, and the hash-chain check. |
| `audit/rederive_tests.py` | Separate re-derivation of the statistical headlines with placebos. It covers the exact-enumeration Wilcoxon, Holm, the binomial top-1 tests and D per task, and imports nothing from src/ or scipy. |
| `tests/` | T1 prompts, T3 vetoes (synthetic part), T7 scoring. |
| `scripts/` | `labeller_recheck.py` (A3/T0), `run_label_audit.py` (C3), `fix_veto_decoding.py`, `write_deviations.py`, `make_readme.py`, and the README text fragments. |
| `inputs/` | Read-only copies of the inputs, plus `inputs/provenance.json` with sha256 and size per file. |
| `data/raw_gen.jsonl` | Every generation: prompt sha, seed, output ids, text, finish reason, and veto metadata. |
| `data/labels_raw.jsonl`, `data/labels.jsonl` | Per-program labeller outputs and combined labels. |
| `data/association.jsonl`, `data/veto_summary.json` | Mapped association answers; per-event veto rounds, n-grams and surfaces. |
| `data/samples.jsonl` | Shared per-sample schema over all labelled programs. |
| `predictions/` | x0, events, association targets, proximity, n-grams, random directions, forecasts, frozen code, and the pre-commit grep audit. |
| `commitments.log` | sha256 hash chain of every committed prediction file. |
| `results/` | Analysis, `c1_events.jsonl`, tests, timings, model record, norms, hook stats, deviations, and the label audit. |
| `figures/` | fig1 ban landings, fig2 log-score forest, fig3 baseline vs pilot. Each has a PDF, a PNG and its JSON spec. |
| `method_out.json` (+ `full_`/`mini_`/`preview_`) | `exp_gen_sol_out` output: datasets `llama_bench_events`, `llama_ban_samples` and `llama_screen_events`. |

Kept artifacts stay on the run's volume at the paths above. Nothing here is a model checkpoint. The Llama weights are not in this folder: they are read from the run's shared Hugging Face cache at revision `0e9e39f249a16976918f6564b8830bc894c89659`, with shard sha256s in `results/model_record.json`.

## How to run

```bash
./restore.sh                         # venv (vLLM 0.11.0, torch 2.8.0, transformers 4.57.6, zss)
.venv/bin/python method.py setup     # provenance, sha256 checks, X0 freeze
.venv/bin/python method.py gen1      # B1-B5 (vLLM)
.venv/bin/python method.py label     # labels (run after every generation stage)
.venv/bin/python method.py freeze    # D, present-minor events
.venv/bin/python method.py assoc     # association map + forced summary
.venv/bin/python method.py hf        # ban norms + hook tests (HF)
.venv/bin/python method.py push      # forced round 2 + random-direction pushes (vLLM, hooks)
.venv/bin/python method.py label --phases E3,B3r2
.venv/bin/python method.py veto      # n-grams + iterated vetoes (vLLM)
.venv/bin/python method.py proximity
.venv/bin/python method.py commit    # forecasts, hash chain, grep audit
.venv/bin/python method.py ban       # bans (vLLM), then: method.py label --phases G1,G2
.venv/bin/python method.py analyse   # C1 + everything descriptive -> method_out.json
.venv/bin/python audit/rederive.py
python3 -I audit/rederive_tests.py   # stdlib only
.venv/bin/python method.py screen    # optional path-task screen (descriptive)
```

A CPU-only re-analysis from the published raw files needs only `analyse` and `audit/rederive.py`. Every generation stage resumes, because it skips row ids that already exist.

## Restoring removed files

`.aii/manifest.yaml` marks only regenerable bulk for deletion.

- `.venv/`: `./restore.sh`, i.e. `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml`.
- `__pycache__/`: `.venv/bin/python -m compileall -q method.py`
- `src/__pycache__/`: `.venv/bin/python -m compileall -q src`
- `tests/__pycache__/`: `.venv/bin/python -m compileall -q tests`
- `screen10/__pycache__/`: `.venv/bin/python -m compileall -q screen10`
- `screen10/canon/gen/__pycache__/`: `.venv/bin/python -m compileall -q screen10/canon/gen`
- `screen10/canon/labeller/__pycache__/`: `.venv/bin/python -m compileall -q screen10/canon/labeller`
- `screen10/canon/tasks/__pycache__/`: `.venv/bin/python -m compileall -q screen10/canon/tasks`
- The model weights are not stored here: `huggingface-cli download meta-llama/Llama-3.1-8B-Instruct --revision 0e9e39f249a16976918f6564b8830bc894c89659`.

All the `__pycache__/` directories are also recreated automatically on import.

Everything else (`data/`, `results/`, `predictions/`, `inputs/`, `screen10/canon/`, `figures/`, the code and the JSON outputs) is text or small and is always kept.

