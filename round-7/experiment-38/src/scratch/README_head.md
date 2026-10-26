# Circuit and dose dial at Gemma's BFS-vs-DFS fork (iteration 7)

**Question.** `google/gemma-3-4b-it` writes one of two algorithms for the same grid-path task (T1). Every program opens
with the same 32 tokens c* (```` ```python ````, `def solve(grid, start, goal):`, `rows = len(grid)`,
`cols = len(grid[0])`, indent). The next token, at response index 32, decides the algorithm: ` visited` leads to depth-first
search (DFS), while a blank line, `if`, `queue` or `q` lead to breadth-first search (BFS). This artifact asks three questions at
that fork:

- **G1.** Which components compute the fork margin m = logsumexp(z[B]) - z['visited']?
- **G2.** Does a controlled low-rank subspace (DAS) carry the choice, and is there a dose that adds correct BFS
  programs without breaking them?
- **G3.** Does the fork margin alone predict what temperature does?

It reuses iteration 6's engine, prompts, c*, fork-token table and labeller (Branch A, `inputs/iter6_gemma/`).

**Short answer (one model, one task, one natural fork; a case study, not a general circuit claim).**

SHORT_ANSWER_PLACEHOLDER

## What was run

| Part | What | Key output |
|---|---|---|
| S0 | inputs (133/133 sha256 match); labeller on the 12 T1 references (12/12); checker rejects 5/5 mutants; token ids, c*, prompt alignment; CRN; DAS toy; instrument ids; batch-shape time test (B = 25); **commit #0** | `results/s0_tests.json`, `results/das_toy.json` |
| S1 | U1 CRN determinism, U2 identity hooks (5 kinds, bit-identical), U3 single-position KV path, U4 top-k sampler | `results/tests_gpu_s1.json` |
| S1 | engine check (twin N = 50, iteration 6's keys), U6 re-run with diagnosis (200 + 200), G3-cal (4 fork tokens x 125) | `results/engine_check.json`, `results/u6.json`, `results/g3_cal.json` |
| G3 | predictions from teacher-forced logits (**commit #1**), then the same-seed sweep T in {0.3, 0.7, 1.0, 1.3} x {top-p 1, top-k 10}, N = 50 per cell | `results/g3_predictions.json`, `results/g3_sweep.json`, F6, F7 |
| yv | fork margin and fork states (all 34 blocks) for 120 twin variants, 40 forced sources, 5 twins | `results/yv.json`, `cache/states/` |
| G1-P | AtP screen of 1,224 nodes (272 heads + 34 MLPs x 4 position classes) on 15 pairs; exact noising/denoising for 60 nodes; edge path patching among the top 15; selection and matched nulls (**commit #2b**) | `results/g1_pathpatch.json`, F1 |
| G1 validation | ABLATE/STEER of the top 10 nodes on 24 prompts vs 50 matched random nodes each; joint top-5/top-10 vs 50 random sets; generation arms N = 30 | `results/g1_validation.json`, `results/g1_generation.json`, F2 |
| G2 | full-state ceiling by layer (17-29); rank-1 layer scan with 3-fold leave-one-template-out CV; nested DAS k in {1, 2, 4, 8} x 3 seeds at L* = 17 and L22; RAND (50), SHUF (3), DiM, natural variance; RINIT (random-init Gemma) | `results/g2_das.json`, `results/g2_layer_scan.json`, `results/g2_rinit.json`, `results/g2_decisions.json`, F3, F4 |
| G2 dose | **commit #3**; DAS and DiM (matched teacher-forced dy) toward BFS and DFS at 6 doses, twin, forced-BFS ceiling, RAND, logit-only DAS (G2-L); N = 50 per cell, CRN | `results/g2_dose.json`, `results/g2_dose_tf_pred.json`, F5 |
| G1-T | timed circuit-tracer attempt (nnsight backend, Gemma Scope 2 width-16k transcoders) | `results/g1t_graphs.json` |
| Audit | novelty audit and style re-gate (OpenRouter), hash chain, independent re-derivation with placebos | `results/novelty_audit.json`, `results/regate.json`, `results/verify_chain.json`, `results/rederive.json` |
