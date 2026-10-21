**Bottom line (Qwen3-8B, 6 tasks, about 3,800 generated programs).** No knob in this artifact reached deeper into the
algorithm repertoire or produced a novel algorithm.

- **Token vetoes stall.** Persistent token vetoes of the default's distinctive n-gram stalled at the default (rung 1)
  on 5 of 6 tasks, and at rung 2 on T06. The vetoed ids never appeared. The model renamed, respelled, or wrote broken
  code instead. A matched sham veto left the default untouched.
- **C3 is disconfirmed.** C3 says a prompt ban cannot elicit an algorithm the walk ranks rung >= 3 that the model can
  write on request: will <= 0.10 wherever can >= 0.7.
  - It fails on T10: BFS will = 1.00 in its leave-one-survivor list.
  - It also fails on T03: quickselect will = 1.00, but that cell depends on a fallback rung.
  - It holds in 4 other cells.
- **Novelty instructions produce claims, not new algorithms.** The two long-form "make a novel algorithm"
  instructions made 84% of 575 outputs claim novelty and produced 0 correct novel programs. The exact 95% upper bound
  on the novel rate is 0.058 per N = 50 cell.

## Main results

### 4b Token walk: a persistent veto of the default's distinctive n-gram never moved the model past rung 2

Under the neutral twins (no ban text), each step vetoes, for every generated token, the distinctive token n-gram of
the algorithm the model last landed on (the plan's rule: present in >= 80% of that algorithm's programs, minimum
collateral on the other algorithms' forced programs; lexical tokens only, see D3). Up to two extra mask rounds add
the observed leak spans or the re-emerged programs' own distinctive n-gram. N = 50 per round (10 per template W1-W5).

| task | step 0 (no veto) | vetoed n-grams (rounds) | final round of the last step | status |
|---|---|---|---|---|
| T1 grid (bf16) | BFS 50/50 | `' c, path = queue.p'` → `' queue.append(start'` → `'None for'` | BFS 6, DFS 1, **invalid 43** | STALLED at step 1 |
| T2 weighted SP (bf16) | Dijkstra 50/50 | `' heap = [(0, s'` → `' current_dist,'` → `' dist[u]:\n'` | Dijkstra 27, invalid 23 (pass 0.30) | STALLED at step 1 |
| T03 k-th smallest (FP8) | full sort 45, quickselect 5 | `' nums.sort'` → `'_sorted'` → `' sorted(nums'` | full sort 23, counting 10, quickselect 6, invalid 10 | STALLED at step 1 |
| T04 substring (FP8) | naive 50/50 | `'+len'` → `'[i:i +'` → leak span | naive 50/50 | STALLED at step 1 |
| T06 duplicate (FP8) | hash set 50/50 | `' set'`, `' seen'`, leak spans → **rung 2 = sort+adjacent (37/50)** → `'.sort'` + 5 leak spans | sort-adjacent 20, other 13, hash set 10 | STALLED at step 2 |
| T10 components (FP8) | union-find 47, DFS 3 | `' parent'` + 8 leak spans (`(parent`, `parents`, `.parent`, `\tparent`, ...) | union-find 44, DFS 6 | STALLED at step 1 |

- **The veto is exact, the algorithm is not carried by it.** No banned id sequence ever occurred in a vetoed
  generation (0 occurrences in every round). The default nevertheless came back by **renaming** (T1: `current_row`/
  `current_col` replace `r, c` in 63% of re-emerged BFS programs, vs 7% of references; T2: `current_distinct` and `d`
  replace `current_dist`), by **non-canonical spellings** of the vetoed string (string-leak rates up to 0.86 on T10
  and 0.80 on T06 step 2), or the code **degenerated into near-miss syntax** (T1 `queue popleft()`: 66-86% invalid).
  API-level surfaces (imports, calls) barely changed: the re-routing is lexical, not algorithmic (`results/walk.json →
  steps[].surfaces_ext`).
- **Sham control.** Vetoing an algorithm-generic n-gram of matched length/presence kept the default: T1 50/50
  (`' start == goal:\n'`), T2 50/50 (`' u, v, w'`), T04 49/50 (`' len'`), T10 44/44 attempted (`' range'`; 6 of 50 invalid); the
  prediction (default share >= 0.9) holds on all four. Shams for T03 and T06 are not constructible (no generic n-gram
  in their 3-6-line default programs). The distinctive veto cost correctness the sham did not: T2 pass rate 0.41 vs
  1.00 (Newcombe difference 0.59 [0.43, 0.72]), T1 0.76 vs 0.96.
- **Fixed TOP5 veto (T1)**: vetoing the distinctive n-grams of BFS, DFS, IDDFS and A*/greedy at once left BFS 13,
  DFS 2, **invalid 35** after two extra rounds; exp9's TOP5 prompt ban gave avoidance 0.00 (BFS 63, DFS 36). Neither
  knob reaches the rest of the catalogue.
- Verdict per the plan's rule: **"not decided at any single token; vetoes are bypassed"** on all six tasks. Only T06
  moved one rung (to sort+adjacent), the same single-rung move prompt bans produce.

### 4a Prompt reach: C3 is disconfirmed (T10 robustly, T03 through the rung rule)

C3 predicted will <= 0.10 at every rung >= 3 algorithm with can >= 0.7 (disconfirmed by will >= 0.30). `can` =
labelled-and-correct share of plain forced attempts (`results/can.json`; the analysis sets recompute exactly as
planned). Qualifying cells (rung table committed after walk step 1):

| cell | rung | can | will (LOS, N = 50) | 95% CI | cell verdict |
|---|---|---|---|---|---|
| T2 Floyd-Warshall (exp9 LOS, not re-run) | >= 3 | 1.00 | 0.00 | [0.00, 0.04] | confirm |
| T03 quickselect | >= 3 (flagged R2) | 0.95 | **1.00** | [0.93, 1.00] | **disconfirm** |
| T03 size-k heap | >= 3 | 0.75 | 0.00 | [0.00, 0.07] | confirm |
| T03 heapify-and-pop | >= 3 | 0.70 | 0.00 | [0.00, 0.07] | confirm |
| T06 binary search on values | >= 3 | 0.78 | 0.00 | [0.00, 0.07] | confirm |
| T06 Floyd cycle detection | >= 3 | 0.70 | 0.14 | [0.07, 0.26] | neither |
| T10 BFS | >= 3 (flagged R2) | 1.00 | **1.00** | [0.93, 1.00] | **disconfirm** |

- **Overall: DISCONFIRMED** (T03 and T10); T2 CONFIRMED; T06 MIXED; T04 UNTESTABLE (no rung >= 3 algorithm has
  can >= 0.7). Both disconfirming cells got "rung >= 3" because the walk stalled at step 1 and the fallback chain
  set R2 (T03 counting sort, T10 DFS). A post hoc sensitivity with rung 2 := the association answer for the default
  keeps the verdict DISCONFIRMED through T10 (association says DFS, so BFS stays rung >= 3), while T03 quickselect
  becomes rung 2 (`results/c3.json → sensitivity_association_rung2`). On T10 the two traversals are interchangeable
  alternatives (LOS(bfs) 50/50 BFS, LOS(dfs) 49/50 DFS), so a single-chain rung order does not describe the
  repertoire.
- **Quickselect is T03's universal answer to a list ban**: every LOS list that bans the full sort yields quickselect in
  44-50 of 50 programs, including the lists that ban quickselect itself (LOS(size_k_heap), LOS(heapify_pop): 50/50
  quickselect, disguise 0.00-0.08). A placebo (labels permuted within task) leaves C3 DISCONFIRMED for this reason
  (`results/rederive.json`): the T03 cell reflects a task-level preference, not list-specific compliance.
- **Sanity check T4 (the list that leaves only the default)**: LOS(default) will is 1.00 on T04, 0.86 on T06 and 0.94
  on T10. On T03 it is **0.00**. The prompts were re-inspected and are correct ("Do not use a size-k heap,
  heapify-and-pop, quickselect, median of medians or counting sort for this task."), yet all 50 programs implement
  quickselect, 48 of them in a function named `quickselect`. Without the list, under the neutral twins, full sort is 45/50.
  Naming the alternatives in a ban primes the named one. This is the starkest negative-constraint priming in this run.
- **Forced 'can' underestimates some modes**: T06 index marking has forced adherence 0.03, yet the model writes it
  in 34-40 of 50 programs under LOS bans that forbid it (disguise 1.00).
- **Two-step bans {default, R2}** (N = 100): T1 {BFS, DFS} compliance 0.02 [0.01, 0.07] (DFS 82, BFS 16); T2
  {Dijkstra, BF/SPFA} 0.01 (BF/SPFA 67, Dijkstra 32); T04 {naive, KMP} 0.14 (naive 74 = snap-back); but T03 {full
  sort, counting} 1.00 (quickselect 63, size-k heap 37), T06 {hash set, sort} 0.96 (index marking 52, Floyd 42), T10
  {union-find, DFS} 1.00 (BFS 100). The path two-step failures replicate iteration 1. WALK2 forecast top-1 hit on T06
  (index marking); ASSOCIATE hit on T03 (quickselect) and T10 (BFS); SNAPBACK hit on T04.
- **List independence (preregistered here)**: on T04 the naive share among naive/KMP programs differs across the
  lists that ban both (0.82 in LOS(rabin_karp) vs 0.98 in LOS(builtin); permutation chi-square p = 0.033, largest
  difference 0.16 [0.04, 0.30]): the prediction (p >= 0.05) **fails** (placebo with shuffled group membership: p = 0.61, 0.56, 0.06); T06 is descriptive only (fewer than 3 groups
  with >= 10 programs; p = 1.0); T03 and T10 have no programs labelled D or R2 under those bans.
- Disguise (banned-mechanism programs naming none of the banned algorithms): 0.44-1.00 across two-step bans and most
  LOS lists (`results/disguise.json`).
