# How far can bans and token vetoes push? (iteration 3, step 4, Qwen3-8B)

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

### 4c Long-form novelty instructions: lots of claimed novelty, no novel algorithm

The two instructions from the request ("Make a (fully) novel algorithm ... design rationale of about 2,000 words")
were followed by the task description and a format line asking for the rationale first and then one code block.
Thinking-off cells ran in bf16 (T1, T2) or FP8 (bench tasks and the cross-check copy); thinking-on cells ran on FP8
with a 16k thinking cap.

| cell | N | default | other catalogue | off-catalogue | invalid / no code | correct |
|---|---|---|---|---|---|---|
| T03 LF1 thinking off (fp8) | 50 | 3 | 17 | 12 | 18 | 25 |
| T03 LF1 thinking on (fp8) | 10 | 0 | 7 | 1 | 2 | 8 |
| T03 LF2 thinking off (fp8) | 50 | 0 | 12 | 8 | 30 | 15 |
| T03 LF2 thinking on (fp8) | 10 | 0 | 9 | 0 | 1 | 8 |
| T04 LF1 thinking off (fp8) | 50 | 27 | 7 | 1 | 15 | 32 |
| T04 LF1 thinking on (fp8) | 10 | 7 | 3 | 0 | 0 | 10 |
| T04 LF2 thinking off (fp8) | 50 | 10 | 8 | 4 | 28 | 13 |
| T04 LF2 thinking on (fp8) | 10 | 7 | 1 | 0 | 2 | 8 |
| T06 LF1 thinking off (fp8) | 50 | 5 | 13 | 17 | 15 | 13 |
| T06 LF1 thinking on (fp8) | 10 | 0 | 4 | 5 | 1 | 4 |
| T06 LF2 thinking off (fp8) | 50 | 4 | 14 | 7 | 25 | 8 |
| T06 LF2 thinking on (fp8) | 10 | 0 | 3 | 6 | 1 | 3 |
| T1 LF1 thinking off (bf16) | 25 | 3 | 12 | 1 | 9 | 7 |
| T1 LF1 thinking on (fp8) | 10 | 0 | 8 | 0 | 2 | 3 |
| T1 LF2 thinking off (bf16) | 25 | 3 | 3 | 2 | 17 | 3 |
| T1 LF2 thinking on (fp8) | 10 | 0 | 7 | 2 | 1 | 3 |
| T2 LF1 thinking off (bf16) | 50 | 17 | 20 | 3 | 10 | 35 |
| T2 LF1 thinking off (fp8) | 50 | 18 | 12 | 4 | 16 | 29 |
| T2 LF1 thinking on (fp8) | 10 | 2 | 6 | 0 | 2 | 8 |
| T2 LF2 thinking off (bf16) | 25 | 6 | 6 | 5 | 8 | 9 |
| T2 LF2 thinking on (fp8) | 10 | 6 | 4 | 0 | 0 | 9 |

- **NOVEL count = 0 in every cell and arm.** Every correct off-catalogue program from every arm went through the
  audit: 38 programs (23 from long-form, 10 from the walk, 5 from LOS lists); plus 15 seeded failing ones.
  - The audit used two blind judges (gemini-2.5-flash-lite, gpt-4.1-mini). They passed a 6-program control gate at 5/6
    each.
  - Each program was compared with its 3 nearest known solutions from the declared dataset and its 3 nearest catalogue
    references, then read by the executor and run on 3 extra seeded random inputs.
  - Final classes of the 38 correct programs: 30 labeller misses (mostly T03 counting-sort with a dict or Counter), 7
    catalogue variants (counting plus binary search on cumulative counts; a LIFO label-correcting search on T2), 1
    degenerate (O(n^2) brute force).
  - The exact one-sided 95% upper bound on the novel rate is 0.058 per N = 50 cell, 0.113 per N = 25 cell and 0.26
    per N = 10 thinking-on cell.
  - Judge agreement was low (kappa A-B 0.27; A-final 0.33; B-final 0.59). Judge A (flash-lite) called 10 programs
    NOVEL and judge B none. The manual pass found 5 of the 10 degenerate (XOR or sum tricks, broken loops), 3 labeller
    misses and 2 catalogue variants.
- **Novelty in prose, catalogue in code.** 484 of 574 long-form outputs with a claim record (84%) claim a new
  algorithm (claim extraction by judge A on all outputs; judge B on a seeded 20%, agreement 96/115).
  - 189 of these 484 (39%) contain no code at all: a rationale of 1,300-1,700 words and no `solve`.
  - Of the 295 with code, 220 (75%) are catalogue algorithms by the mechanism labeller. The other 75 are off-catalogue
    programs, none of them novel.
  - Typical claimed names: "Modified Bellman-Ford", "BFS with Dynamic Programming", "Optimized Dijkstra with Early
    Termination".
  - Both judges answer the "is the claimed invention known?" field by the name, not the mechanism, so this artifact
    reports the labeller-based share above (`results/longform.json → claims.mechanism_check`).
- **The instructions do diversify, and they cost correctness.** Correct-only Hill numbers in the thinking-off cells
  are 1.8-4.5, against a collapsed baseline whose modal share was 1.00. The share of attempts that pass drops on T1
  (0.33-0.44) and T06 (0.32-0.37).
- **Thinking on (T1/T2, N = 10 per prompt).**
  - All 40 traces completed within the cap (4.5k-12.4k thinking tokens).
  - The code is still catalogue: T1 mostly DFS (13/20, plus Dijkstra 2 and 2 failing off-catalogue programs); T2
    BF/SPFA, Dijkstra and Floyd only.
  - Claims of novelty drop to 0.4-0.5 on T2.
- **Thinking on, bench tasks (T03/T04/T06, N = 10 per prompt).**
  - All 60 traces completed (mean 4.1k-7.7k thinking tokens).
  - T03: counting sort in 13/20, quickselect 3, off-catalogue 1 (a counting-sort labeller miss).
  - T04: naive in 14/20, plus Rabin-Karp 2, Z-algorithm 1, KMP 1.
  - T06: off-catalogue in 11/20, all failing arithmetic tricks (sum formula, XOR, sum of squares) that assume a single
    duplicate; binary search on values 4, Floyd 3.
  - With and without thinking, T03 lands mostly on counting sort once labeller misses are corrected (thinking on 13/20;
    thinking off 9 labelled plus 19 audited labeller misses or variants out of 100), with quickselect second. Every
    correct program is a catalogue algorithm.
- **bf16 vs FP8 cross-check (LF1, T2, N = 50 each, same seeds)**: label composition JS divergence 0.033 bits vs a
  pooled-bootstrap null 95th percentile of 0.068 (p = 0.35); pass rate 0.70 vs 0.58 (difference 0.12 [-0.07, 0.30]);
  mean output 2,260 vs 2,315 tokens; rationale 1,484 vs 1,551 words. No detectable precision effect on this task.


## What this artifact does

One model, **Qwen/Qwen3-8B** (thinking off unless stated), six tasks: the path-task screen **T1** (grid path) and
**T2** (weighted shortest path), and the frozen bench tasks **T03** (k-th smallest), **T04** (substring search),
**T06** (find duplicate) and **T10** (connected components). Path tasks and bench tasks are always reported
separately and never pooled.

| arm | what it is | comparator / control in the same pipeline |
|---|---|---|
| 4b token walk | persistent logit veto of the default's *distinctive token n-gram* under the neutral twins (no ban text); up to 2 extra mask rounds when a vetoed algorithm re-emerges or the vetoed string leaks through another tokenisation; the next landing is vetoed next (cumulative, up to 5 algorithms) | step 0 = same prompts, no veto; **sham veto** = an algorithm-generic n-gram of matched length and presence; **fixed TOP5 veto** (T1) vs exp9's TOP5 prompt ban |
| 4a prompt reach | 17 leave-one-survivor (LOS) ban lists on the bench tasks (N = 50 each) and two-step bans {default, rung 2} on all six tasks (N = 100) | forced **can** (labelled-and-correct) as the capability ceiling; exp9's T2 LOS; the walk |
| 4c long-form novelty | the request's two "make a (fully) novel algorithm ... 2,000-word rationale" instructions, thinking off and on | label composition vs the catalogue; two blind judges + a manual pass against human/known solutions from the declared dataset dependency |

Every mask, forecast and protocol was committed to the sha256 hash chain in `commitments.log` **before** the samples
it governs (`src/commit.py`; verified in `method_out.json → metadata.commitments`).

## Departures from the plan (full list with consequences: `method_out.json → metadata.deviations`)

- **Hardware and precision (D1, D2).** The pod had an NVIDIA L4 (23 GB, 300 GB/s) instead of the planned RTX A4500.
  Each task family ran at the precision its iteration-2 references were produced with. T1/T2 ran in bf16 (exp8/exp9
  baselines and forced programs). The bench tasks ran on the official Qwen3-8B-FP8 checkpoint (exp11 pilots, forced
  programs and `can`), using weight-only FP8 Marlin kernels. The bf16-vs-FP8 cross-check on LF1-T2 bounds the
  precision effect for one task only.
- **N-gram and sham rules (D3, D4).** Veto unit test u1 showed an indentation-tailed n-gram being bypassed by
  re-indenting (20/20), so distinctive n-grams must be lexical: no whitespace-only token. The plan's selection rule is
  otherwise unchanged. Shams may not contain a Python keyword or the fence tag. Shams for T03 and T06 are not
  constructible.
- **Unit test u2 (D5)** compares vetoed and unvetoed batch-mates on the same server: 17/20 token-identical (bf16) and
  19/20 (FP8). No processor-free second engine was loaded.
- **Forecast commits per family (D6).** Every forecast still precedes the samples it scores.
- **Fallback R2 (D7, D16).** T1/T2 two-step bans used the exp8/exp9 single-ban substitutes; T03 and T10 used the
  flagged step-1 fallback; T04 used the association answer.
- **One crash and two restarts (D8, D15).** No sample was lost or duplicated.
- **Long-form split branch (D9).** The stage-10 projection was 220 bf16-minutes for all 500 samples.
- **Dropped work (D10, D14; `results/not_run.json`).**
  - The optional manifold placement and the 5b temperature sweep.
  - The T1/T2 thinking-on extension to N = 25. The never-drop floor ran (T1/T2 thinking-on, N = 10 per prompt), and
    the bench thinking-on cells (T03/T04/T06, N = 10 per prompt) ran after a KV-cache-driven restart.
- **Analysis code edited after its commit (D17).** `src/analysis.py` gained additions after its hash was committed
  before the bench ban samples: corrected compositions, the post hoc sensitivity, the claim mechanism check and a
  Holm-family note. No preregistered computation changed. The edit shows as a failed file check on that chain entry
  plus a new entry. `src/rederive.py`, unchanged since before that commit, re-derives every preregistered number
  from the raw rows with 0 mismatches.
- **Audit judge prompt (D13).** The control gate failed at round 0 because the prompt lacked the labeller context.
  After the fix it passed at 5/6 for both judges.

## Limitations

- One model family (Qwen3-8B). C3 is a single-family claim.
- N = 50 per walk round and per LOS list. Minor landings below ~10% are descriptive.
- Thinking-on runs have N = 10 per prompt and per task. A count of 0 novel programs bounds the novel rate only below
  ~26% (exact one-sided 95%).
- 'Novel' is judged against:
  - the catalogue;
  - the known-solution corpus of the declared dataset (472 programs: Mercury, LeetCodeDataset, TheAlgorithms, KodCode,
    XLCoST);
  - two LLM judges and one manual reader.

  It is not judged against the literature.
- The walk is adaptive: each step's mask depends on the previous landing. Its depth is not comparable across tasks.
- Labeller re-check: runtime vs adjudicated agreement on the path gold set is 0.86 (T1) and 0.77 (T2), the same as the
  stored exp8 values. T2 is below 0.85 and is flagged. The combined label, which adds the AST check and the judge on
  disagreement, is what every table uses. All references are recovered by both labellers on all six tasks (43/43).


## Layout

| path | contents |
|---|---|
| `method.py` | CLI (`s0`, `server`, `unit`, `phase A/B`, `longform`, `audit`, `analyze`, `outputs`) and the `method_out.json` assembly; the deviation list |
| `src/config.py` | task registry (catalogues, defaults, display names, analysis sets), decoding, seeds, thresholds, paths |
| `src/veto.py` | the persistent n-gram veto: a vLLM V1 `AdapterLogitsProcessor` (`--logits-processors veto:NGramVeto`), per-request veto lists through `vllm_xargs` |
| `src/server.py`, `src/client.py` | PID-managed vLLM OpenAI server (bf16 or FP8) and the async client (token-id prompts, returned output ids, explicit sampling params, two-phase thinking) |
| `src/prompts.py` | neutral twins (T1/T2: exp8 frozen ids, asserted identical; bench: first neutral noun + `' .'` padding to the ban's token length), LOS/two-step bans, long-form prompts |
| `src/ngram.py` | distinctive n-gram tool, sham n-gram, mask expansion (space/newline/bare variants), occurrence and string-leak detection, unit tests |
| `src/walk.py` | the walk state machine (`WalkArm`), sham / fixed-TOP5 arms (`MaskArm`), the lockstep scheduler with filler jobs |
| `src/reach.py` | LOS / two-step job builders and the committed forecasts (rung table, C3 cells, list-independence, WALK2/ASSOCIATE/SNAPBACK) |
| `src/longform.py` | long-form generation (thinking off/on), last-code-block extraction, rationale word counts |
| `src/label.py` | one API over the two frozen labellers (bench exp11 pipeline; exp1 suite via exp8): runtime primary, AST second, blind judge on disagreement |
| `src/judge.py` | every OpenRouter call: cache, `usage.cost` budget, own stop at USD 0.95, stop at the first per-run budget refusal |
| `src/audit.py`, `src/manual.py` | known-solution corpus from the dependency dataset, nearest neighbours, judge controls, two-judge audit, claim extraction; manual-pass extra tests |
| `src/analysis.py`, `src/figures.py`, `src/rederive.py`, `src/stats.py` | all reported numbers, figures, independent re-derivation + placebo, statistics helpers |
| `src/phases.py`, `src/recheck.py` | GPU phase drivers, S0 checks, veto unit tests; labeller re-check on gold sets and references |
| `src/dep_usage.py` | how each of the 10 datasets of the declared dependency enters this artifact (`results/dependency_usage.json`) |
| `scripts/chain_phase_b.sh`, `scripts/chain_thinking.sh` | the GPU job chaining actually used (one server on the GPU at a time, PID-based waits) |
| `audit/manual_round1.py`, `audit/manual_round2.py`, `audit/apply_manual.py` | the executor's manual-pass decisions (one rule per program family, written after reading every program it covers) and their application to the audit records (`results/manual_audit.json`) |
| `scripts/build_readme.py`, `scratch/readme_*.md` | assembles this README from the result sections (tables filled from `results/*.json`) |
| `restore.sh`, `pyproject.toml`, `requirements.lock.txt` | recreate `.venv/` (all 180 packages pinned; the lock file is the `uv pip freeze` of the venv) and fetch the model weights |
| `reproducibility.md` | what was actually run, in order, with hardware, timings, failures and the numbers a reader should get |
| `scripts/verify_headlines.py` | short independent re-derivation of every headline number from the raw per-sample files, with placebo runs of each test (`results/verify_headlines.json`) |
| `inputs/` | read-only copies of every upstream file used (bench, suite, exp7/8/9/11 data) + `SHA256SUMS`; `known_solutions.jsonl` (built from the dependency dataset) |
| `predictions/` | every committed mask, forecast and protocol (hash-chained) |
| `data/samples_<arm>.jsonl` | one row per program (shared schema: model, task, condition, template, arm, sample_id, seed, prompt_sha256, label, labeller_source, passed, finish_reason, n_new_tokens, code_sha256, code, + step/round/veto/leak/thinking fields) |
| `data/raw_<arm>.jsonl` | raw generations (text, output token ids, veto sequences) |
| `data/label_cache.jsonl`, `data/llm_cache.jsonl` | labeller results per unique program; every LLM response (judges, audit, claims) |
| `results/` | `walk.json`, `can.json`, `c3.json`, `reach.json`, `list_independence.json`, `disguise.json`, `reach_events.jsonl`, `longform.json`, `fp8_crosscheck.json`, `novelty_audit*.json`, `claims.json`, `audit_controls*.json`, `labeller_recheck.json`, `veto_unit_tests_*.json`, `state_*.json`, `costs.json`, `rederive.json`, `manual_audit.json`, `dependency_usage.json`, `known_solutions_summary.json`, `not_run.json`, `inputs_check.json`, `longform_branch.json`, `sham_not_constructible_*.json`, `scheduler_timings_*.json` |
| `figures/` | `fig1_token_walk`, `fig2_will_vs_can`, `fig3_reemergence`, `fig4_longform`, `fig5_sham_vs_distinctive` (PDF + PNG) |
| `method_out.json` (+ `full_`/`mini_`/`preview_`) | `exp_gen_sol_out`: datasets `token_walk` (1,750), `prompt_reach` (1,450), `long_form` (575), `audit` (53); every example has `predict_*` fields (baseline default; committed forecast; LOS survivor and C3 forecast; WALK2/ASSOCIATE/SNAPBACK; judge guesses); metadata = every analysis above + deviations + costs + versions + commitment chain |
| `uv.lock` | the lock uv wrote when `uv run method.py` synced the environment from `pyproject.toml` |
| `logs/` | per-stage logs, server logs, `timings.jsonl` |

Everything here is text and stays on the run's volume at these relative paths; no file is 100 MB or larger.

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
export PYTHONDONTWRITEBYTECODE=1
.venv/bin/python method.py s0
.venv/bin/python method.py server bf16 start 4608 32      # Qwen3-8B bf16 at revision b968826d...
.venv/bin/python method.py unit bf16
.venv/bin/python method.py phase A                        # T1/T2 walk + shams + fixed TOP5 (+ forecasts)
.venv/bin/python method.py phase two_step path bf16       # path two-step bans from the committed forecasts
.venv/bin/python method.py longform bf16                  # concurrently with phase A
scripts/chain_phase_b.sh                                  # swap to FP8, unit tests, bench walk + LOS + two-step, FP8 long-form
scripts/chain_thinking.sh                                 # thinking-on floor (T1/T2, N=10 per prompt) after phase B
.venv/bin/python src/longform.py fp8_on T03:0-10,T04:0-10,T06:0-10 8   # bench thinking-on (after FP8 thinking-off)
export DEP_DATASET_DIR=../gen_art_dataset_1                  # the declared dataset dependency (art_j3Rm_lr2nzR6)
.venv/bin/python method.py audit corpus && .venv/bin/python src/dep_usage.py && .venv/bin/python method.py audit controls
.venv/bin/python method.py audit pool && .venv/bin/python src/manual.py sheet   # then read the sheet
.venv/bin/python audit/apply_manual.py && .venv/bin/python method.py audit claims && .venv/bin/python src/recheck.py
.venv/bin/python method.py analyze && uv run method.py           # no argument = rebuild method_out.json (~1 min, no GPU)
```

No C compiler exists on the machine this ran on, so vLLM runs eager with `TORCH_COMPILE_DISABLE=1`; the FP8
checkpoint uses vLLM's weight-only FP8 Marlin kernels (`VLLM_TEST_FORCE_FP8_MARLIN=1`), as exp11 did.

## Restoring removed files

The `.aii/manifest.yaml` marks only the virtual environment for deletion:

| removed path | restore with |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` |

The model weights live in the run's shared Hugging Face cache (outside this folder). To fetch them elsewhere:

```bash
huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218
huggingface-cli download Qwen/Qwen3-8B-FP8
```

`restore.sh` runs all three commands.
