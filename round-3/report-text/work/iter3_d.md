## 3.5 Llama bench experiment: the same forecast contest in a second model family

**Why.** Llama-3.1-8B-Instruct [22] is less collapsed than Qwen3-8B on the bench pilot, so it supplies present minor bans, where a correct minor algorithm already exists and subtraction makes a non-trivial prediction. This experiment [ARTIFACT:art_Q-qh-9HhPoWo] replicated the frozen forecast contest on the 12 bench tasks in bf16 (revision 0e9e39f), with every forecast computed without ban text and hash chained before any ban prompt was rendered (a grep audit found 0 ban prompts in the 10,328 rows generated before the commit).

**Design.** The default of each task was frozen from a decision set (the 8-bit Llama pilot pooled with 600 bf16 neutral twin samples after a homogeneity test) as the modal correct label when at least 10 programs were correct, else the modal attempted label (Table 101). Present minor events required at least 10% of correct programs, at least 3 correct, and at least 10 correct programs on the task. The forecasts were the subtraction forecast (exact one-shot, persistent and iterated signature vetoes by truncate and redraw), the ladder (nonce ban, novelty instruction and three matched-norm random directions added at the task specification positions of layers 11 to 21 during prefill), association (Llama's own frozen answers) and proximity (Zhang-Shasha distance [64]), in a form that transfers the default's mass, with point mass forms as sensitivities. Then 1,800 bans were sampled (12 modal and 6 present minor events, 5 templates by 20) and labelled with the bench labellers; references were recovered 50 of 50, and gold agreement was 0.959. A second blind judge audited 60 Llama programs at 0.88 agreement, below 0.85 on four tasks (nonoverlapping intervals, kth smallest, two sum, top-k frequent).

**Table 101.** Llama defaults and events, frozen before any ban (decision set: 8-bit pilot plus bf16 neutral twins). Source: Llama bench experiment `README.md`, `predictions/events.json`.

| Task | Pilot mode | Default | Default from attempts | Valid programs | Correct programs | Default share | Hill_cc |
|-|-|-|-|-|-|-|-|
| kth smallest | heapify and pop | full sort | | 94 | 18 | 0.17 | 3.80 |
| substring search | naive | naive | | 89 | 49 | 0.54 | 2.00 |
| find duplicate | hash set | hash set | | 93 | 34 | 0.44 | 1.48 |
| two sum | hash map | hash map | | 99 | 84 | 0.97 | 1.07 |
| connected components | union find | union find | | 97 | 74 | 0.75 | 1.59 |
| nonoverlapping intervals | greedy by end | greedy by end | yes | 89 | 8 | 0.63 | 2.46 |
| Fibonacci | matrix power | matrix power | | 96 | 44 | 0.76 | 1.78 |
| topological order | Kahn | Kahn | | 99 | 88 | 0.98 | 1.06 |
| merge intervals | sort and sweep | sort and sweep | | 89 | 65 | 1.00 | 1.00 |
| first and last position | binary search | binary search | | 93 | 54 | 0.99 | 1.10 |
| top-k frequent | heap | heap | | 86 | 22 | 0.62 | 1.80 |
| longest increasing subsequence | quadratic DP | quadratic DP | | 94 | 68 | 0.87 | 1.08 |

Present minor events: top-k frequent sort by count (6 of 22 correct), kth smallest heapify and pop (4 of 18), kth smallest quickselect (4 of 18), substring search KMP (9 of 49), connected components DFS (13 of 74), kth smallest size-k heap (3 of 18).

**The contest does not resolve in Llama.** Thirteen of 18 events passed the gate and 11 were gated and disagreeing, but only 2 had a winner by 0.10 nats (Table 102): the subtraction forecast on two sum, through its undefined forecast scored as uniform (the ban split between sort and two pointers, 42, and brute force, 32), and association on kth smallest heapify and pop. No family advances; the preregistered branch is "NO FAMILY ADVANCES (aimed, unresolved)". The landing is aimed: the ladder and association each named the realised landing on 7 of 13 gated events, against a chance rate of about 0.27 (exact binomial p = 0.033 each); subtraction hit 4 of 12 (p = 0.38) and proximity 3 of 13 (p = 0.71). Five defaults resisted the ban itself (nonoverlapping intervals, topological order, merge intervals, first and last position, longest increasing subsequence; avoidance 0.04 to 0.30).

**Table 102.** Every Llama ban event (N = 100). s_X is the banned algorithm's share of attempts in the decision set before the ban; † marks a present minor event. Each family's top-1 is given with its mean log score per attempt not banned in parentheses; "undefined" is scored as uniform. Source: Llama bench experiment `README.md`, `results/c1_events.jsonl`.

| Event | s_X | Avoidance | Gate | Attempts not banned | Modal landing | Subtraction | Ladder | Association | Proximity | Renormalised baseline | Winner (margin) | Hill_cc (correct programs) | Other / invalid |
|-|-|-|-|-|-|-|-|-|-|-|-|-|-|
| kth smallest, ban full sort | 0.17 | 0.95 | pass | 87 | quickselect | heapify and pop (-1.71) | other (-1.46) | quickselect (-1.40) | size-k heap (-1.66) | -1.64 | none (0.06) | 1.00 (15) | 0.09 / 0.08 |
| substring search, ban naive | 0.54 | 0.79 | pass | 64 | KMP | Rabin-Karp (-1.20) | KMP (-1.25) | KMP (-1.18) | built-in find (-1.83) | -1.20 | none (0.02) | 1.38 (20) | 0.05 / 0.19 |
| find duplicate, ban hash set | 0.44 | 0.76 | pass | 71 | other | other (-0.98) | other (-1.00) | Floyd cycle detection (-1.53) | sort and adjacent check (-1.37) | -1.02 | none (0.02) | 3.59 (7) | 0.53 / 0.06 |
| two sum, ban hash map | 0.97 | 0.91 | pass | 86 | sort and two pointers | undefined (-1.39) | other (-1.90) | sort and two pointers (-1.94) | brute force (-2.37) | -1.39 | subtraction (0.51) | 1.63 (34) | 0.07 / 0.05 |
| connected components, ban union find | 0.75 | 0.82 | pass | 78 | DFS | DFS (-1.00) | DFS (-0.80) | DFS (-0.98) | DFS (-0.98) | -0.98 | none (0.18) | 1.68 (42) | 0.04 / 0.05 |
| nonoverlapping intervals, ban greedy by end | 0.63 | 0.29 | fail | 26 | other | other (-0.89) | other (-0.97) | DP with bisect (-1.51) | memoised recursion (-1.59) | -0.85 | none (0.08) | n/a (0) | 0.21 / 0.11 |
| Fibonacci, ban matrix power | 0.76 | 0.79 | pass | 72 | iteration | other (-1.13) | iteration (-1.10) | fast doubling (-2.31) | memoised recursion (-1.94) | -1.21 | none (0.03) | 1.72 (44) | 0.13 / 0.09 |
| topological order, ban Kahn | 0.98 | 0.18 | fail | 17 | DFS postorder | undefined (-1.39) | undefined (-1.39) | DFS postorder (-0.92) | source removal (-3.81) | -1.39 | none (0.46) | 1.00 (1) | 0.04 / 0.04 |
| merge intervals, ban sort and sweep | 1.00 | 0.30 | fail | 25 | other | undefined (-1.11) | undefined (-1.11) | union find (-3.13) | interval tree (-3.71) | -1.11 | none (0.00) | n/a (0) | 0.23 / 0.18 |
| first and last position, ban binary search | 0.99 | 0.04 | fail | 2 | other | undefined (-1.11) | undefined (-1.11) | bisect module (-3.76) | bisect module (-3.76) | -1.11 | none (0.00) | 1.00 (1) | 0.02 / 0.03 |
| top-k frequent, ban heap | 0.62 | 0.89 | pass | 84 | sort by count | sort by count (-0.74) | sort by count (-0.68) | sort by count (-0.70) | sort by count (-0.70) | -0.66 | none (0.02) | 1.31 (13) | 0.05 / 0.06 |
| longest increasing subsequence, ban quadratic DP | 0.87 | 0.23 | fail | 22 | patience sorting | undefined (-1.10) | undefined (-1.10) | Fenwick tree (-2.56) | patience sorting (-1.02) | -0.83 | none (0.08) | 1.00 (8) | 0.09 / 0.05 |
| top-k frequent, ban sort by count † | 0.36 | 0.82 | pass | 75 | quickselect on counts | heap (-1.05) | heap (-1.02) | heap (-1.06) | bucket sort (-1.34) | -1.02 | none (0.03) | 1.19 (24) | 0.09 / 0.09 |
| kth smallest, ban heapify and pop † | 0.33 | 0.88 | pass | 77 | quickselect | other (-1.54) | full sort (-1.57) | quickselect (-1.33) | size-k heap (-1.81) | -1.57 | association (0.21) | 2.57 (27) | 0.09 / 0.12 |
| kth smallest, ban quickselect † | 0.12 | 0.76 | pass | 71 | full sort | full sort (-1.65) | full sort (-1.73) | full sort (-1.56) | size-k heap (-1.79) | -1.73 | none (0.09) | 2.12 (34) | 0.10 / 0.06 |
| substring search, ban KMP † | 0.26 | 0.70 | pass | 66 | Boyer-Moore-Horspool | other (-0.99) | naive (-1.01) | Rabin-Karp (-1.22) | naive (-1.01) | -1.01 | none (0.01) | 1.14 (34) | 0.09 / 0.06 |
| connected components, ban DFS † | 0.25 | 0.89 | pass | 85 | BFS | union find (-0.35) | union find (-0.34) | union find (-0.34) | BFS (-0.47) | -0.34 | none (0.00) | 1.15 (65) | 0.02 / 0.04 |
| kth smallest, ban size-k heap † | 0.24 | 0.84 | pass | 78 | full sort | heapify and pop (-1.68) | full sort (-1.72) | quickselect (-1.70) | heapify and pop (-1.88) | -1.72 | none (0.02) | 2.23 (27) | 0.10 / 0.07 |

The Wilcoxon tests (exact enumeration over the 11 gated disagreeing events, Holm corrected) separate the families from proximity but not from each other: subtraction minus proximity +0.345 nats [0.190, 0.633] (p = 0.0029, Holm 0.0088) and ladder minus proximity +0.306 [0.204, 0.513] (p = 0.0020, Holm 0.0078) are rejected; subtraction minus association +0.172 [-0.049, 0.606] (p = 0.52) and ladder minus association +0.133 [-0.056, 0.542] (p = 0.77) are not. In Llama, code proximity is the worst forecast, and association, subtraction and the ladder cannot be told apart at this N, which is below the pooled floor of 16 events.

The verdict is fragile. Of ten preregistered sensitivity rows, three return substitution with association advancing on 3 wins: rescoring on correct programs only, the bf16-only decision set, and dropping the fourth template. Excluding the task whose default came from attempts and the tasks the label audit flagged leaves 5 disagreeing gated events and reads "X specific but unaimed". The point mass forms, dropping co-vetoed survivors and dropping any other single template all keep "no family advances".

**Signature vetoes rarely remove a Llama default either (Table 103).** Only the heap of top-k frequent collapsed (0.02 once `(k` and ` heapq` were both masked). Elsewhere the default re-emerged at 0.20 to 0.96 in the last persistent round; hash map (0.89), sort and sweep (0.88), Kahn and binary search (0.96) barely moved.

**Table 103.** Share of the banned algorithm among veto attempts per round (persistent, iterated arm; weighted counts for present minor events). Source: Llama bench experiment `README.md`.

| Event | Round-1 n-gram | Round 1 | Round 2 | Round 3 | Note |
|-|-|-|-|-|-|
| kth smallest, ban full sort | `","` | 0.20 | | | co-vetoes every survivor |
| substring search, ban naive | `"1):\n"` | 0.44 | 0.42 | 0.54 | not carried by a small set of surface tokens; co-vetoes Rabin-Karp |
| find duplicate, ban hash set | `" nums:\n       "` | 0.38 | 0.26 | 0.26 | not carried by surface tokens |
| two sum, ban hash map | `" i]\n"` | 0.93 | 0.95 | 0.89 | not carried by surface tokens |
| connected components, ban union find | `" def find"` | 0.59 | 0.57 | 0.23 | not carried by surface tokens |
| nonoverlapping intervals, ban greedy by end | `".sort"` | 0.60 | 0.50 | 0.36 | not carried by surface tokens; co-vetoes DP with bisect |
| Fibonacci, ban matrix power | `" matrix"` | 0.46 | 0.43 | 0.28 | not carried by surface tokens |
| topological order, ban Kahn | `" queue"` | 0.98 | 0.96 | 0.96 | not carried by surface tokens |
| merge intervals, ban sort and sweep | `"\ndef solve"` | 0.84 | 1.00 | 0.88 | not carried by surface tokens |
| first and last position, ban binary search | `" = 0,"` | 0.98 | 0.96 | 0.96 | not carried by surface tokens |
| top-k frequent, ban heap | `"(k"` | 0.57 | 0.02 | | removed |
| longest increasing subsequence, ban quadratic DP | `"[j] +"` | 0.85 | 0.83 | 0.80 | not carried by surface tokens |
| top-k frequent, ban sort by count † | `" ["` | 0.37 | 0.34 | 0.35 | not carried by surface tokens; co-vetoes heap and quickselect on counts |
| kth smallest, ban heapify and pop † | `" {}\n   "` | 0.25 | 0.15 | | |
| kth smallest, ban quickselect † | `" quick"` | 0.12 | | | |
| substring search, ban KMP † | `"                j"` | 0.26 | 0.24 | | |
| connected components, ban DFS † | `" dfs"` | 0.17 | | | |
| kth smallest, ban size-k heap † | `".n"` | 0.09 | | | |

Of the two events where the one-shot veto moved at least half of the banned algorithm's attempts, neither shared the ban's modal survivor within the template bootstrap null (0 of 2, against a preregistered bar of two thirds, quoted for reference only). The test that matters most for substitution is the present minor gain (Table 104): if a named ban only removes Y, the associate's share under the ban should equal its share under the persistent veto of Y. On two of six events the associate gains more under the named ban (kth smallest heapify and pop to quickselect, +0.25 [0.12, 0.37]; kth smallest quickselect to full sort, +0.24 [0.10, 0.36]); on substring search KMP the associate (Rabin-Karp) is less frequent under the ban (-0.08 [-0.17, -0.00]); on three it is unchanged. Naming the banned algorithm sometimes steers Llama toward its associate beyond what removing it does, but not consistently.

**Table 104.** Present minor events: the associate's share under the named ban against the persistent veto of the same algorithm (Newcombe 95% intervals [42]). Source: Llama bench experiment `README.md`.

| Event | Associate | Ban share | Veto share | Baseline share | Ban minus veto |
|-|-|-|-|-|-|
| top-k frequent, ban sort by count | heap | 0.59 | 0.63 | 0.62 | -0.04 [-0.18, 0.10] |
| kth smallest, ban heapify and pop | quickselect | 0.42 | 0.17 | 0.12 | 0.25 [0.12, 0.37] |
| kth smallest, ban quickselect | full sort | 0.44 | 0.20 | 0.17 | 0.24 [0.10, 0.36] |
| substring search, ban KMP | Rabin-Karp | 0.04 | 0.12 | 0.12 | -0.08 [-0.17, -0.00] |
| connected components, ban DFS | union find | 0.82 | 0.81 | 0.75 | 0.01 [-0.10, 0.12] |
| kth smallest, ban size-k heap | quickselect | 0.22 | 0.18 | 0.12 | 0.04 [-0.08, 0.15] |

**Pushes.** The nonce ban left the default near its baseline on most tasks. Matched-norm random directions moved the default substantially on a few tasks (Fibonacci matrix power 0.76 to 0.16 to 0.51; top-k frequent heap 0.62 to 0.39 to 0.56), and the novelty instruction lowered the default almost everywhere. The realised layer-21 displacement of the random pushes was about three times the ban's, because pushes at layers 11 to 20 propagate, so the ladder inputs are generous pushes. A second blind judge re-audited 187 ban outputs labelled other and called 8 (4%) the banned algorithm and 24 a catalogue survivor; other is never folded into avoidance.

**The path task screen (descriptive, never pooled).** On the iteration-2 Llama path tasks, the same ban-free families were scored against the Llama replication's existing ban landings, using that experiment's own prompt builders (10 of 10 prompts reproduced byte for byte) and labeller (Table 105). The vetoes fired (25 of 50 grid and 40 to 48 of 50 shortest path pass-1 samples) but BFS (0.52 to 0.58) and Dijkstra (0.78 to 0.82) re-emerged through other surface forms in every round. On the grid task all four families named DFS, the realised landing. On the shortest path task, the ban's large other share (37 of 100) was not reproduced by any veto round (8 of 50 other each); the novelty instruction came close (18 of 50 other).

**Table 105.** Path task screen in Llama. Source: Llama bench experiment `README.md`.

| Task | Ban landing (Llama replication) | Modal | Subtraction | Ladder | Association | Proximity | Winner | Veto: banned share by round |
|-|-|-|-|-|-|-|-|-|
| Grid | DFS 63, BFS 29, other 6, A* 1, unit weight Dijkstra 1 | DFS | DFS (-0.54) | DFS (-0.88) | DFS (-0.47) | DFS (-0.47) | none (0.00) | `" queue:\n       "`: 0.56, 0.52, 0.58 |
| Shortest path | Dijkstra 43, Bellman-Ford/SPFA 18, other 37, Floyd-Warshall 2 | other | undefined (-1.59) | undefined (-1.59) | Bellman-Ford/SPFA (-1.79) | Floyd-Warshall (-2.81) | none (0.00) | `" continue"`: 0.82, 0.78, 0.80 |

**Checks.** Input integrity, hooks, prompts, sampler, scoring and veto tests passed; every committed file preceded the first ban sample; an independent rederivation matched the gate, landings, log scores, wins and branch, and a family permutation placebo advanced a family in 0.00 of 1,000 permutations; the exact Wilcoxon p values, Holm decisions and binomial tests were rederived without the project code. Not rederived: the sensitivity rows, the bootstrap intervals, the one-shot veto comparison, the present minor gain and the screen scores. GPU time was 0.98 hours of logged generation on one L4 (about 1.8 hours held), judge spend USD 0.48.

## 3.6 Bench route experiment: which internal route carries a ban, task by task (Qwen3-8B)

**Why.** Iteration 2 found on the two path tasks that the ban is carried mostly by the prompt states. The hypothesis update made that the second claim of the title account: if a ban only removes the default, the removal should be applied by the task specification states before the first generated token, with generated tokens reading the ban directly only where the one-shot veto does not suffice. This experiment [ARTIFACT:art__5akZ9W9iZM4] measured the route in behaviour on the 12 bench tasks, with the iteration-2 engine.

**Design.** Qwen3-8B ran in bf16 under HF with common random numbers (one uniform per row and step, inverse CDF sampling) and cache splicing by position class, on one NVIDIA L4 with batches of 40 rows of one shape class. Each slot ran the full ban (a), the token-length matched neutral twin (b), the prompt route (c: twin condition segment with the ban's task specification and read position states), the direct route (d: the ban's condition segment with the twin's later states), the full knockout (K0: the condition span removed from the cache seen by generated tokens), the one-shot signature veto of the default under the twin (V1), and prefills of the default's opening or of a neutral `def` line under the ban and the twin. N was 100 slots per arm (5 templates by 20); 13,030 samples were labelled by the frozen bench labellers. Route fractions are defined on the default's share of attempts s as F_prompt = (s_b - s_c) / (s_b - s_a), F_direct = (s_b - s_d) / (s_b - s_a), the interaction I = 1 - F_prompt - F_direct, and F_K0 = (s_b - s_K0) / (s_b - s_a). The decision rule (prompt route at least two thirds, with the interval above one half; disconfirmed if the direct route reaches one third) was hash committed before any ban sample.

**Only five bench bans take.** Table 106 gives the default's share in every arm for all 12 tasks. The gate passed on kth smallest (avoidance 0.99), connected components (1.00), two sum (0.83), find duplicate (0.79) and merge intervals (0.59), the same five tasks as in the bench forecast experiment. The fourth template was again the weakest (pooled avoidance 0.19 against 0.42 to 0.62 for the others) and produced 29% of all ban failures.

**Table 106.** The default's share of attempts by arm (N attempted in parentheses), and the ban's landing. Source: bench route experiment `results/shares.json`.

| Task | Full ban (a) | Twin (b) | Prompt route (c) | Direct route (d) | Knockout (K0) | One-shot veto (V1) | Ban landing (attempts off the default) |
|-|-|-|-|-|-|-|-|
| kth smallest | 0.01 (100) | 0.95 (100) | 0.01 (100) | 0.25 (100) | 0.01 (100) | 0.59 (100) | quickselect 70, size-k heap 28, heapify and pop 1 |
| connected components | 0.00 (100) | 0.99 (100) | 0.00 (100) | 0.20 (100) | 0.00 (100) | 0.70 (20) | BFS 75, DFS 25 |
| two sum | 0.17 (100) | 1.00 (100) | 0.66 (100) | 0.20 (100) | 0.67 (100) | 1.00 (100) | brute force 83 |
| find duplicate | 0.21 (100) | 1.00 (100) | 0.97 (100) | 0.22 (100) | 0.95 (100) | 1.00 (100) | index marking 77, Floyd cycle detection 1, other 1 |
| merge intervals | 0.41 (100) | 1.00 (100) | 0.77 (100) | 0.99 (100) | 0.74 (100) | 1.00 (69) | other 44, union find 15 |
| substring search | 0.58 (100) | 1.00 (100) | 1.00 (100) | 0.89 (100) | 1.00 (50) | 1.00 (94) | KMP 18, built-in find 17, Boyer-Moore-Horspool 5, Rabin-Karp 2 |
| top-k frequent | 0.59 (100) | 0.93 (100) | 0.97 (100) | 0.77 (100) | 0.94 (50) | 0.93 (100) | heap 30, quickselect on counts 10, other 1 |
| Fibonacci | 0.69 (100) | 1.00 (100) | 0.99 (100) | 0.72 (100) | 0.96 (50) | 1.00 (100) | other 31 |
| topological order | 0.96 (100) | 1.00 (100) | 1.00 (100) | 1.00 (100) | 1.00 (50) | 1.00 (46) | DFS postorder 4 |
| longest increasing subsequence | 0.98 (100) | 1.00 (100) | 1.00 (100) | 1.00 (100) | 1.00 (50) | 1.00 (42) | other 1, patience sorting 1 |
| first and last position | 0.98 (100) | 0.76 (100) | 1.00 (100) | 0.76 (100) | 1.00 (50) | 0.61 (62) | other 1, bisect module 1 |
| nonoverlapping intervals | 1.00 (100) | 1.00 (100) | 1.00 (100) | 1.00 (100) | 1.00 (50) | 1.00 (97) | none |

**The route is task dependent, and pooled it is not the prompt route.** On the five gated tasks the mechanisms differ (Table 107). On kth smallest and connected components the information is redundant: the prompt route alone and the knockout (which removes direct reading) each reproduce the ban, and the direct route alone does most of it as well. On two sum and find duplicate the ban acts almost entirely through generated tokens reading the condition segment: the direct route arm reproduces the ban, while the prompt route and the knockout do not (find duplicate: 0 against 76 discordant slots between the full ban and the prompt route; exact McNemar p below 1e-6). On merge intervals neither route suffices alone. Pooled over the five tasks, the prompt route carries 0.61 and the direct route 0.74 (Table 108), so the preregistered route claim is disconfirmed under all three intervals: the direct route exceeds one third, and the prompt route falls below two thirds with a lower bound far under one half (bootstrap probability that F_prompt is at most one half 0.28, that F_direct is at least one third 0.99). Leaving one template out kept F_prompt between 0.55 and 0.66 and F_direct between 0.71 and 0.84; a Bayesian mixed logistic sensitivity gave 0.74 and 0.89.

**Table 107.** Route fractions on the gated bench tasks (template then slot bootstrap 95% intervals). Source: bench route experiment `results/route.json`.

| Task | F_prompt | F_direct | Interaction | F_K0 | Reading |
|-|-|-|-|-|-|
| kth smallest | 1.00 [1.00, 1.00] | 0.74 [0.36, 0.99] | -0.74 | 1.00 | redundant: either route suffices |
| connected components | 1.00 [1.00, 1.00] | 0.80 [0.40, 1.00] | -0.80 | 1.00 | redundant |
| two sum | 0.41 [0.03, 0.82] | 0.96 [0.80, 1.00] | -0.37 | 0.40 | mostly direct |
| find duplicate | 0.04 [0.00, 0.13] | 0.99 [0.90, 1.05] | -0.03 | 0.06 | direct only |
| merge intervals | 0.39 [0.00, 0.73] | 0.02 [0.00, 0.08] | 0.59 | 0.44 | superadditive: both needed |

**Table 108.** Pooled route fractions over the five gated tasks (ratio of sums; hierarchical task, template and slot bootstrap with 10,000 replicates; the leave-one-task-out jackknife is primary because there are only five clusters). Source: bench route experiment `results/route.json`.

| Quantity | Point | Jackknife 95% (primary) | Percentile 95% | BCa 95% [68] |
|-|-|-|-|-|
| F_prompt | 0.611 | [0.06, 1.17] | [0.23, 0.93] | [0.22, 0.93] |
| F_direct | 0.744 | [0.38, 1.11] | [0.42, 0.97] | [0.27, 0.94] |
| Interaction | -0.355 | [-0.98, 0.27] | [-0.73, 0.14] | [-0.71, 0.17] |
| F_K0 | 0.621 | [0.08, 1.16] | [0.24, 0.93] | [0.24, 0.93] |

[FIGURE:fig_bench_route]

An independent second draw with fresh uniforms (slots 20 to 39, arms a to d on the five gated tasks, N = 100 each) reproduced the picture: pooled F_prompt 0.64 [0.27, 0.94] and F_direct 0.74 [0.43, 0.94], per-task fractions within about 0.1 (find duplicate F_direct 0.99 then 0.93; two sum 0.96 then 0.93; merge intervals F_prompt 0.39 then 0.49), and Spearman rank agreement between the draws of 0.89 and 0.90. The task differences are not sampling noise. A continuous companion readout (the teacher forced log probability of the default's signature prefix under each arm) split the effect across both routes as behaviour does (pooled 0.40 prompt, 0.45 direct).

**Veto sufficiency does not predict the route.** The update predicted that the direct share would be small where the one-shot veto suffices and large where it does not. The frozen n-gram rule picked identifier or structural tokens with zero collateral (two sum `' if complement'`, find duplicate `' set'`, Fibonacci `'('`), so the one-shot veto rarely changed the mechanism: veto avoidance V_t was 0.41 on kth smallest, 0.39 on first and last position, 0.30 on connected components and at most 0.07 elsewhere. The veto fired in 61% to 100% of rows, and the model renamed or retokenised (two sum: `if compliment in seen`) or broke the code (connected components: 80 of 100 invalid). Every task was classed as needing a large direct route (V_t below 0.5, predicting F_direct of at least 0.25) in the second commit; 4 of 5 gated tasks hit (merge intervals missed with F_direct 0.02), and the Spearman correlation between V_t and F_direct was -0.34 with a one-sided permutation p of 0.30 over five points, which fails the rule. The test is inconclusive, and the comparison of the one-shot veto's landing with the ban's had no eligible task.

**The ban is decided at the opening of the body.** Forcing the default's own opening, up to its distinctive n-gram, undid the ban completely on every gated task (the share of the ban effect undone, P_open, 0.98 to 1.00), while forcing only a neutral `def solve(...):` line undid none of it (-0.12 to 0.01). The depth sweep (Table 109) localises this: the ban holds through the whole `def` line and gives way at the first content token of the default's body. On kth smallest, forcing the `def` line and its indentation (10 tokens) leaves the ban intact, and forcing one more token, ` nums`, undoes it. Under common random numbers, arms a, c and d leave the twin's tokens at that first body token (median token 8 to 10 on kth smallest, two sum, find duplicate and connected components; 19 to 21 on merge intervals, whose shared `if not intervals` guard comes first). Once the first tokens of the default's body are on the page, the model continues the default; the ban is applied at the opening and not re-read in the body, as Qi et al. found for safety refusals [63].

**Table 109.** Share of the ban effect undone by forcing a prefix (P_open), by prefix: a neutral `def` line, or the default's modal program forced to 25%, 50% or 75% of its tokens or up to its distinctive n-gram (forced tokens in parentheses; N = 50 per cell, under the ban and the twin). Source: bench route experiment `README.md`, `results/replication.json`.

| Task | Neutral `def` line | 25% of the program | Up to the distinctive n-gram | 50% | 75% |
|-|-|-|-|-|-|
| kth smallest | -0.01 (9 tokens) | -0.01 (5: `def solve`) | 0.98 (11: `def` line, indent, ` nums`) | -0.01 (10: `def` line and indent) | 1.00 (16) |
| find duplicate | -0.01 (7) | 1.00 (10: `seen =`) | 1.00 (11: `seen = set`) | 1.00 (20) | 1.00 (29) |
| two sum | 0.01 (9) | 1.00 (13: `seen = {}`) | 1.00 (32) | 1.00 (26) | 1.00 (40) |
| connected components | 0.00 (9) | 1.00 (31, inside `find`) | 1.00 (20: `def find`) | 1.00 (62) | 1.00 (92) |
| merge intervals | -0.12 (8) | 1.00 (30: `intervals.sort(key`) | 1.00 (58) | 1.00 (59) | 1.00 (88) |

[FIGURE:fig_prefill_depth]

**The path task screen.** Under the iteration-2 twin prompts, every veto variant failed to move either path default: one-shot, persistent, iterated rounds with the re-emerged programs' new n-grams, and a veto of the import line itself. The share off the default was 0.00 on the grid task and at most 0.01 on the shortest path task, and the default re-emerged in 99% to 100% of attempts after each round. The committed prediction "the grid one-shot veto does not suffice" hit; "the shortest path one-shot veto suffices and lands on Bellman-Ford/SPFA" missed (V = 0). The iteration-2 ban landings recomputed exactly from raw rows (grid DFS 257 of 257; shortest path Bellman-Ford/SPFA 255 of 260). A ban moves these tasks; a surface veto does not.

**Controls and checks.** A placebo splice (one twin's condition segment with another twin's later states) moved the default's share by at most 0.04 on all six tasks where it ran, so splicing itself is inert; the knockout applied to the twin left the default at 1.00 on six tasks. GPU unit tests confirmed common random number determinism, splice identities (splicing a prompt with itself reproduces it in 100% of rows) and zero attention mass on the condition span under the knockout in all 36 layers. A reproduction of the iteration-2 shortest path arms gave banned shares of 0 of 20, 20 of 20, 3 of 20 and 19 of 20 for arms a to d, inside their pass bands. Two audit scripts rederived every headline from raw rows with no mismatch, and shuffling arm labels within slots collapsed the mean gap between twin and ban from 0.83 to -0.001. A worker restart briefly ran three labelling workers on the same rows; duplicates were compacted to the last row per sample, which every reader used. GPU time was about 1.8 hours on one L4, judge spend USD 0.105.

