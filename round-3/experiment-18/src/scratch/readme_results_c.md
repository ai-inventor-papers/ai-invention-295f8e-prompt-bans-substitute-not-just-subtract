### 4c Long-form novelty instructions: lots of claimed novelty, no novel algorithm

The two instructions from the request ("Make a (fully) novel algorithm ... design rationale of about 2,000 words")
were followed by the task description and a format line asking for the rationale first and then one code block.
Thinking-off cells ran in bf16 (T1, T2) or FP8 (bench tasks and the cross-check copy); thinking-on cells ran on FP8
with a 16k thinking cap.

| cell | N | default | other catalogue | off-catalogue | invalid / no code | correct |
|---|---|---|---|---|---|---|
__LF_TABLE__

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
