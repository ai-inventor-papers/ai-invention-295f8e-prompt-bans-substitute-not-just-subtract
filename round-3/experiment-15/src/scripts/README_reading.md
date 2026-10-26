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
