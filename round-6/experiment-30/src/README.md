# Where in the prompt the algorithm is chosen (iteration 6, bf16 Qwen3-8B)

Qwen3-8B (revision `b968826d…`, bf16, thinking off) almost always writes one default algorithm per coding task: a full
sort for the k-th smallest element (T03), union-find for connected components (T10), Dijkstra for weighted shortest
paths (T2), BFS on the grid (T1), a hash map for two-sum (T05), a hash set for find-duplicate (T06). A prompt that bans
the default ("Do not use a full sort for this task.") moves the model to a substitute Y. This artifact asks **where in
the prompt's internal states that choice is carried**, and whether earlier noise-based localisations survive in bf16.

## Results

**Bottom line.**

- **Where the choice is carried (Stage A, the method).**
  - *Prompt-route tasks.* The ban's effect is carried in the task-specification residual states, mostly at blocks
    12-23. On T2, exchanging the full ban's spec states into the neutral twin moves 24 of 30 slots from Dijkstra to
    Bellman-Ford/SPFA (transfer 0.80; McNemar 24:0, Holm p 7e-7; pass ratio 0.90). The condition-span KV splice
    moves none of them.
  - *Direct-route tasks.* The condition-span splice alone reproduces the full ban: T05 1.00, T06 0.90. The
    read-position exchange transfers nothing on any of the six tasks.
  - *Controls.* A matched-norm random exchange transfers at most 0.13, and the placebo twin at most 0.03. So the
    transfer is carried by the ban's information, not by the size of the perturbation. X_0-35 beats MR_0-35 on T2
    (23:0), T03 (16:2) and T10 (11:0).
  - *Committed verdicts.* P1 is **NOT SUPPORTED**: T2 and T03 transfer at least 0.5, but T05's spec states also
    transfer 0.43, above the predicted 0.2. On T10 every slot leaves union-find (off-default transfer 1.00), but only
    0.37 land on the ban's BFS. The secondary route check (COND >= 0.5 on T05/T06 and <= 0.2 on T2; RPOS <= 0.2
    everywhere), the placebo prediction and the MR prediction all **hold**.
- **Where noise acts (ST, bf16).**
  - Isotropic noise at the task-spec positions moves the algorithm in bf16. T03: S0 (blocks 12-23) 0.37 correct
    off-default at alpha 2. T10: S4 (blocks 0-11) 0.33 at alpha 4.
  - The same noise at the read position (S1), the condition span (S2/S2E) or the late spec blocks (S5) barely moves
    it. On T03, S0 beats S1 in paired slots 24:5 (MH OR at matched log D_R 4.6, [1.9, 11.3]) and S2 22:0.
  - The committed rule nevertheless gives **WITHDRAWN** (the site of the choice stays open), for two reasons:
    - the condition-span arm never reaches S0's downstream displacement, so it has no common support with S0;
    - at alpha 8 the S0 programs all fail (pass 0) and S4's nearly all do (0.10-0.13), while S1 starts moving
      (T10: 0.30); this erases the S1 contrast in the pre-registered model.
  - A post-hoc pre-breakage sensitivity (alpha <= 4) puts S1 clearly below S0 at matched displacement on both tasks:
    beta -3.8 and -5.0, cluster-bootstrap CIs [-8.2, -1.4] and [-11.5, -1.5].
- **State noise vs KL-matched temperature: not established.**
  - At alpha 2, S3 (noise on generated tokens 1-32) leads DMD (a temperature tuned to the same per-token KL, T 2.06
    and 2.72) in discordant flips: 12:6 on T03 and 7:3 on T10. Neither is significant (p 0.24, 0.34).
- **Top-five plan push (T1): no landing to place.** It breaks programs before it moves the algorithm (pass
  0.67 -> 0.30 -> 0.03 -> 0.00 at alpha 1-8), with at most 1 correct non-BFS program per cell.
  - In actual activation coordinates (F5), the push leaves the forced-prompt manifold. Already at alpha 1 it moves
    farther along PC1 than the whole spread of the ten algorithm centroids.
  - The prompt top-five ban moves the spec states from below the centroid cloud into it, between the banned
    (dfs, gbfs) and the surviving (bibfs, idastar, biastar) centroids. Behaviour stays inside the banned set: 25 BFS
    and 23 DFS of 50.
- **Engine and audits.**
  - Engine: per-slot twin labels agree with exp27's bf16 engine on 0.975 of T03 and T2 slots (39/40 each) and on
    1.00 for T10, T05 and T1, so the engine agrees.
  - U-tests: U1, U2, U4 and U5 are byte-exact. U3 (spec-span exchange = KV splice) is top-1 equal with a 0.5 bf16 logit
    gap and 10/10 equal labels.
  - Independent stdlib re-derivation from the raw rows (`audit/rederive.py`): 295 checks, 0 mismatches. A placebo
    version of every headline test fails, as it should: within-pair label swaps give Stage A p 0.33-1.0 (observed
    p <= 0.001), ST S0-vs-S1 p 0.46 (observed 5.5e-4), and L 4:5, p 0.75 (observed 8:1, p 0.020).
  - Novelty audit: both correct 'other' programs are catalogue variants; 0 novel.
  - Cost: about 2.7 GPU-hours on one RTX 2000 Ada (4,320 generated programs + 1,220 teacher-forced passes);
    OpenRouter USD 0.05491 (judges only on labeller disagreement).
- **Positive instructions are carried the same way (extensions).**
  - A forced "Implement Bellman-Ford or SPFA for this task." (T2) gives Bellman-Ford/SPFA on 30 of 30 slots. Its
    padding twin, the same prompt with the instruction tokens replaced by ' .', stays on Dijkstra (29 of 30).
  - Exchanging only the forced prompt's spec-position states (all blocks) into the padding twin gives Bellman-Ford/SPFA
    on **30 of 30**. On T10, forced BFS gives 28 of 30 (padding twin: union-find 30 of 30).
  - The T2 semantic seed paragraph does not move the algorithm at all (Dijkstra 30 of 30), and neither does its
    exchange (2 of 30).
  - The W4 template, held out of every other cell, replicates the ban exchange: T2 0.70, T03 0.60 on Y (1.00 off-default),
    T10 0.70; N = 10 each.
- **Landing forecasts (L): the base model's runner-up beats the instruct model's own opening ranking.**
  - Over the 21 recorded push-landing events, the base runner-up names the landing on 17. The instruct twin's
    teacher-forced opening ranking (OPEN) names it on 10.
  - On the 9 events where the two disagree, BASE wins 8:1 (exact one-sided sign test p 0.020; the published minimum
    was 5 of 5). Mean log score is higher by 1.62 nats (Wilcoxon p 0.032).
  - Where the twin itself wrote an alternative (7 events), the twin's own minority does as well as the base
    (6 of 7; log-score difference 0.02, p 0.69).
  - Caveats: the comparison is retrospective (the landings were known when the rule was frozen), and OPEN rests on
    1-6 programs per algorithm.

| committed test | verdict |
|---|---|
| P1 (Stage A: >= 0.5 on 2 of T2/T03/T10, <= 0.2 on T05/T06) | NOT SUPPORTED (T05 transfers 0.43) |
| route check (COND, RPOS) | holds |
| PLACEBO (\|transfer\| <= 0.1) | holds |
| X_0-35 beats MR_0-35 where P1 transfers | holds (T2, T03) |
| ST prefill-site rule (S1 and S2 below S0 at matched displacement) | WITHDRAWN (no common support for S2; alpha-8 breakage) |
| S3 vs KL-matched temperature, alpha 2, both tasks | not established |
| top-five push landing test | not computable (0 correct survivor programs) |
| L sign test BASE > OPEN | supported (8:1, p 0.020) |
| engine check (>= 0.95 per-slot agreement with exp27) | agrees (0.975, 0.975) |

Figures: `figures/F1_stageA_transfer`, `F2_site_grid`, `F3_indicator_coefficients`, `F4_state_vs_token`,
`F5_top5_geometry` (activation-space geometry), `F6_landing_forecasts` (.pdf and .png). All result tables are in
the appendix below and in `results/summary.md`; every number is re-derived by `audit/rederive.py` (295 checks,
0 mismatches).


## What was run

Every arm runs in one HF bf16 engine (exp27's float64 inverse-CDF sampler with exact common random numbers: every arm
of a CRN slot shares the slot's uniform stream; fence stop; one fixed batch size per task so GEMM shapes are identical
in every arm). Programs are labelled by the frozen, gated mechanism labellers (runtime tracer + AST; a blind judge only
on disagreement; exp28's re-gated array-Dijkstra rule for T2). Every rule was hash-committed before its first decisive
sample (`commitments.log`, `predictions/commit0.json`).

| block | what | design |
|---|---|---|
| Stage A (method) | full-state exchange of the full ban's residual states into the token-length-matched neutral twin | per block band (0-11, 12-23, 24-35, 0-35) at the task-specification positions (X_b); KV splice of the condition span (COND = the direct route); read-position exchange at all 36 blocks (RPOS); six tasks, N = 30 per cell on paired CRN slots |
| Stage A controls (baselines) | neutral twin (N = 50); matched-norm random exchange MR_0-35 / MR_12-23 (h <- h_twin + \|\|h_ban - h_twin\|\| u, fresh u per slot, block, position); PLACEBO (a second neutral twin as the source); identity exchange (U2); X_0-35 = KV splice of the spec span (U3) | same slots, same engine |
| ST | iteration 4's noise-site grid rerun in bf16 on T03/T10 | sites S0 (spec, blocks 12-23), S4 (spec, 0-11), S5 (spec, 24-35), S1 (read position), S2 (condition span), S3 (generated tokens 1-32), energy-matched S1E/S2E; alpha 1/2/4/8; ban-free unit; one fresh direction per sample; Firth indicator model at matched downstream displacement |
| state vs token | S3 state noise against a temperature on generated tokens 1-32, bisected to the same per-token KL (DMD) | N = 50 paired slots, exact McNemar on discordant correct off-default flips |
| top-five push | T1, exp20's u_top5 direction at alpha 1/2/4/8 (N = 30) + the prompt top-five ban (N = 50) | landing placed on the forced-prompt geometry in actual activation coordinates |
| L | retrospective forecast contest on the 21 recorded push-landing events | base runner-up vs the instruct model's own teacher-forced opening ranking vs the twin's minority; exact sign test |
| extensions | forced 'Implement Y' sources (T2 Bellman-Ford/SPFA, T10 BFS) and the T2 semantic seed exchanged at band 0-35 into their padding twins; W4 template at band 0-35 (N = 10) | reported separately |

## Deviations from the plan

- **GPU.** This machine has an RTX 2000 Ada (16 GB), not the planned A4500 (20 GB). bf16 Qwen3-8B (16.4 GB) does not
  fit whole, so, as the plan's memory rule prescribes, the input-embedding table stays in CPU RAM (exact row gather,
  copied to the GPU); lm_head and all 36 blocks run on the GPU in bf16 (`src/engine6.py`). Batch sizes: 10 (bench),
  8 (T2), 6 (T1).
- **Generation caps** 384 (bench) / 512 (T2) / 640 (T1) tokens instead of 1024/1536: exp27's 99th-percentile lengths
  are at most 250 / 227 / 437 tokens; truncations are counted per cell.
- **A3/B3 Stage A** (drop-order item 4) was not run (time budget of this GPU).
- **Commit order.** The analysis code was frozen in an amendment commit before scoring (not in commit #0); the L event
  table was frozen in commit #1 before any teacher-forced opening pass.
- **L base support.** For the seven existing-task Qwen events no base-model composition is on disk (only exp22's
  runner-up), so BASE is a runner-up-weighted forecast there; the primary sign test uses top-1 only.
- **ST rule arms.** On both tasks the raw condition-span arm (S2) never reaches S0's downstream displacement, so by
  the plan's fallback the energy-matched S2E arm stands in for S2 in the rule model; S1E never overlaps S0 (it
  overshoots). The alpha <= 4 model is a post-hoc sensitivity (amendment commit 4), labelled as such.
- **Top-five landing test** is run only on landings on survivor algorithms; the prompt top-five ban's correct
  non-BFS programs are DFS, which the prompt bans.
- **L OPEN programs.** Bench tasks use up to 6 reference + forced programs per algorithm; the panel A/B units have 1
  reference per algorithm and the path tasks 2 (flagged in `predictions/commit1b_L_forecasts.json`). The FP8 events'
  opening ranking is computed in this bf16 engine.
- **Novelty-audit prompt.** After a one-program smoke test, the judge instructions were refined so that a library call
  implementing a catalogue algorithm (e.g. `sorted()`) counts as that algorithm, not as degenerate.
- Smaller items are listed in `results/deviations.jsonl` and `predictions/commit0.json` (planned_deviations).

## Layout

| path | content |
|---|---|
| `method.py` | entry point: runs every stage below in order (`.venv/bin/python method.py all`) |
| `src/engine6.py` | bf16 Qwen3-8B loader with the CPU-resident input embedding |
| `src/gpu6.py` | GPU stages: U-tests, twins + Stage A, ST grid, S3/DMD, top-five push, extensions |
| `src/prompts6.py` | twin / ban / placebo / top-five-ban prompts with positions; dependency extract |
| `src/prereg6.py`, `src/commit6.py` | commit #0 and the sha256 commitment chain |
| `src/label6.py` | label worker (frozen labellers, T2 re-gate) |
| `src/analysis6.py`, `src/stats6.py` | every analysis; Firth logistic, profile CI, cluster bootstrap, exact tests |
| `src/lcontest.py` | L: event table, teacher-forced opening ranking (Qwen, Gemma), forecasts and scoring |
| `src/novelty6.py` | two-family novelty audit of correct 'other' programs |
| `src/figures6.py`, `src/report6.py`, `src/outputs6.py`, `src/bookkeeping6.py` | figures, tables, method_out.json, CPU tests and bookkeeping |
| `src/vendor/exp27/` + byte-identical copies in `src/` (`cfg.py`, `engine_v4.py`, `engine5.py`, `sampling_v4.py`, `hooks.py`, `prompts_v4.py`, `label_worker_v4.py`, …) | reused code of earlier artifacts; `src/regate_rules.py` is exp28's |
| `audit/rederive.py` | independent stdlib re-derivation of every headline from the raw rows, with placebo tests |
| `reproducibility.md` | step-by-step reproduction of exactly what was run |
| `schemas/exp_gen_sol_out.json`, `src/format_outputs6.py` | output schema and the portable full/mini/preview writer + validator |
| `scripts/run_gpu_main.sh`, `scripts/run_gpu_after.sh`, `scripts/finalize.sh` | the GPU queue as it was run (main queue with a deadline; extensions + L), and the post-GPU pipeline |
| `src/download_models6.py`, `src/probe_gpu.py`, `src/commit_analysis.py` | model download, the memory/throughput probe, the analysis-code amendment commits |
| `commitments.log` | the sha256 commitment chain (7 commits: commit0, commit1_L_events, amendment2_dmd_temperatures, amendment3_analysis_code, amendment4_analysis_code_posthoc, commit1b_L_forecasts, amendment5_presentation_code; verified by `src/commit6.py`) |
| `logs/` | run logs of every stage |
| `prompts/` | `prompts6.jsonl` (all prompts), `positions.json`, exp27's `prompts.jsonl` |
| `data/samples_raw.jsonl` | one row per generated program (text, token ids, slot, cell, realised displacement, S3 KL) |
| `data/labels.jsonl` | one label row per program; `data/l_events.json`, `data/tf_scores.jsonl` (L); `data/unit_tests_raw.jsonl` + `data/labels_unit_tests_raw.jsonl` (U-tests); `data/dep_extract.json` (dependency) |
| `results/*.json` | analyses (`stage_a`, `site_grid`, `state_vs_token`, `top5_push`, `landing_forecast`, `engine_check`, `novelty_audit`, `rederive`, `tests_cpu`, …), `summary.md` (all tables) |
| `figures/F1-F6.{pdf,png}` | figures |
| `predictions/` | commits (commit0, L events and forecasts, DMD temperatures), hardware, model revisions |
| `cache/` | bf16 geometry states of the top-five push (`geometry_T1_states.npz`) and its unit |
| `inputs/`, `inputs_extra/` | read-only copies of the prior artifacts this pipeline reads (sha256 in `inputs/SHA256SUMS`, `results/inputs_available.json`) |
| `method_out.json` (+ `full_`/`mini_`/`preview_`) | exp_gen_sol_out output: one example per (task, cell, slot) |

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python src/download_models6.py                # Qwen/Qwen3-8B@b968826d, google/gemma-3-4b-it@093f9f38
.venv/bin/python method.py all                          # or stage by stage: prompts utest commit0 gpu ext lgpu label analysis novelty figures outputs audit
```

`reproducibility.md` lists exactly what was run, in order, with seeds, hardware, timings and the expected numbers.
The GPU stages need one CUDA GPU with at least 16 GB; the label worker and the novelty audit need
`OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY` (judges are called only on labeller disagreement).

## Restoring removed files

| removed path | restore with |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` |
| `__pycache__/` (top level) | regenerated automatically on import (or `.venv/bin/python -m py_compile method.py`) |
| `**/__pycache__/` (src/, inputs/) | regenerated automatically on import (or `.venv/bin/python -m compileall -q src inputs`) |
| model weights (not in this folder; shared HF cache) | `.venv/bin/python src/download_models6.py` (Qwen/Qwen3-8B@b968826d9c46dd6066d109eabc6255188de91218, google/gemma-3-4b-it@093f9f388b31de276ce2de164bdc2081324b9767) |

## Appendix: all result tables (generated by `src/report6.py`)

### Engine check and unit tests

- T03: per-slot label agreement with exp27's bf16 twin 0.975 (40 pairs) (decisive).
- T2: per-slot label agreement with exp27's bf16 twin 0.975 (40 pairs) (decisive).
- T10: per-slot label agreement with exp27's bf16 twin 1.000 (40 pairs).
- T05: per-slot label agreement with exp27's bf16 twin 1.000 (40 pairs).
- T1: per-slot label agreement with exp27's bf16 twin 1.000 (40 pairs).
- Verdict: ENGINE AGREES (>= 0.95).
- U-tests: {'U1': True, 'U2': True, 'U3': False, 'U4': True, 'U5': True}; U3 max |logit diff| at R {'W1': '0.500', 'W2': '0.445'}, U3 label equality {'n': 10, 'equal': 10}, U4 max relative error along u 6.9e-04.

### Stage A: full-state exchange (N = 30 per cell, paired CRN slots 0-29)

**T03** (default full_sort, Y = quickselect, route class of iterations 2-3: prompt). Twin (slots 0-29): Y share 0.00, off-default 0.00, pass 1.00; twin correct composition: full_sort 30.

| cell | n | Y share [CP 95%] | transfer | off-default transfer | pass ratio | recovery | slot IIA | McNemar b:c (p, Holm) | correct composition |
|---|---|---|---|---|---|---|---|---|---|
| BAN | 30 | 0.67 [0.47, 0.83] | 0.67 | 1.00 | 0.93 | 1.00 | 1.00 | 20:0 (1.9e-06, 1.9e-06) | quickselect 18, size_k_heap 10 |
| X_0-11 | 30 | 0.40 [0.23, 0.59] | 0.40 | 0.53 | 1.00 | 0.60 | 0.33 | 12:0 (4.9e-04, 0.003) | full_sort 14, quickselect 12, size_k_heap 4 |
| X_12-23 | 30 | 0.57 [0.37, 0.75] | 0.57 | 1.00 | 0.93 | 0.85 | 0.90 | 17:0 (1.5e-05, 7.6e-05) | quickselect 15, size_k_heap 13 |
| X_24-35 | 30 | 0.03 [8.4e-04, 0.17] | 0.03 | 0.03 | 1.00 | 0.05 | 0.03 | 1:0 (1.000, 1.000) | full_sort 29, quickselect 1 |
| X_0-35 | 30 | 0.57 [0.37, 0.75] | 0.57 | 1.00 | 0.97 | 0.85 | 0.90 | 17:0 (1.5e-05, 7.6e-05) | quickselect 16, size_k_heap 13 |
| COND | 30 | 0.93 [0.78, 0.99] | 0.93 | 1.00 | 0.90 | 1.40 | 0.60 | 28:0 (7.5e-09, 3.7e-08) | quickselect 25, size_k_heap 2 |
| RPOS | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | full_sort 30 |
| MR_0-35 | 30 | 0.10 [0.02, 0.27] | 0.10 | 0.10 | 1.00 | 0.15 | 0.03 | 3:0 (0.250, 0.750) | full_sort 27, quickselect 3 |
| MR_12-23 | 30 | 0.13 [0.04, 0.31] | 0.13 | 0.13 | 1.00 | 0.20 | 0.00 | 4:0 (0.125, 0.375) | full_sort 26, quickselect 4 |
| PLACEBO | 30 | 0.03 [8.4e-04, 0.17] | 0.03 | 0.03 | 1.00 | 0.05 | 0.00 | 1:0 (1.000, 1.000) | full_sort 29, quickselect 1 |

X_0-35 vs MR_0-35 on Y: 16:2 discordant, exact p 0.0013 (Holm 0.0020).

**T10** (default union_find, Y = bfs, route class of iterations 2-3: prompt). Twin (slots 0-29): Y share 0.00, off-default 0.00, pass 1.00; twin correct composition: union_find 30.

| cell | n | Y share [CP 95%] | transfer | off-default transfer | pass ratio | recovery | slot IIA | McNemar b:c (p, Holm) | correct composition |
|---|---|---|---|---|---|---|---|---|---|
| BAN | 30 | 0.90 [0.73, 0.98] | 0.90 | 1.00 | 1.00 | 1.00 | 1.00 | 27:0 (1.5e-08, 3.0e-08) | bfs 27, dfs 3 |
| X_0-11 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.87 | 0.70 | 0.00 | 0.10 | 0:0 (1.000, 1.000) | dfs 17, union_find 4 |
| X_12-23 | 30 | 0.47 [0.28, 0.66] | 0.47 | 1.00 | 1.00 | 0.52 | 0.43 | 14:0 (1.2e-04, 4.9e-04) | dfs 16, bfs 14 |
| X_24-35 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.63 | 1.00 | 0.00 | 0.10 | 0:0 (1.000, 1.000) | dfs 19, union_find 11 |
| X_0-35 | 30 | 0.37 [0.20, 0.56] | 0.37 | 1.00 | 1.00 | 0.41 | 0.40 | 11:0 (9.8e-04, 0.002) | dfs 19, bfs 11 |
| COND | 30 | 0.10 [0.02, 0.27] | 0.10 | 1.00 | 1.00 | 0.11 | 0.20 | 3:0 (0.250, 0.500) | dfs 27, bfs 3 |
| RPOS | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | union_find 30 |
| MR_0-35 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.07 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | union_find 28, dfs 2 |
| MR_12-23 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.03 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | union_find 29, dfs 1 |
| PLACEBO | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.03 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | union_find 29, dfs 1 |

X_0-35 vs MR_0-35 on Y: 11:0 discordant, exact p 9.8e-04 (Holm 0.0020).

**T2** (default dijkstra, Y = bf_spfa, route class of iterations 2-3: prompt). Twin (slots 0-29): Y share 0.00, off-default 0.00, pass 1.00; twin correct composition: dijkstra 30.

| cell | n | Y share [CP 95%] | transfer | off-default transfer | pass ratio | recovery | slot IIA | McNemar b:c (p, Holm) | correct composition |
|---|---|---|---|---|---|---|---|---|---|
| BAN | 30 | 0.97 [0.83, 1.00] | 0.97 | 0.97 | 1.00 | 1.00 | 1.00 | 29:0 (3.7e-09, 1.5e-08) | bf_spfa 29, dijkstra 1 |
| X_0-11 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.03 | 0:0 (1.000, 1.000) | dijkstra 30 |
| X_12-23 | 30 | 0.60 [0.41, 0.77] | 0.60 | 0.60 | 0.73 | 0.62 | 0.63 | 18:0 (7.6e-06, 4.6e-05) | dijkstra 11, bf_spfa 11 |
| X_24-35 | 30 | 0.37 [0.20, 0.56] | 0.37 | 0.37 | 1.00 | 0.38 | 0.40 | 11:0 (9.8e-04, 0.006) | dijkstra 19, bf_spfa 11 |
| X_0-35 | 30 | 0.80 [0.61, 0.92] | 0.80 | 0.80 | 0.90 | 0.83 | 0.83 | 24:0 (1.2e-07, 7.2e-07) | bf_spfa 21, dijkstra 6 |
| COND | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.03 | 0:0 (1.000, 1.000) | dijkstra 30 |
| RPOS | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.03 | 0:0 (1.000, 1.000) | dijkstra 30 |
| MR_0-35 | 30 | 0.03 [8.4e-04, 0.17] | 0.03 | 0.03 | 0.97 | 0.03 | 0.07 | 1:0 (1.000, 1.000) | dijkstra 29 |
| MR_12-23 | 30 | 0.03 [8.4e-04, 0.17] | 0.03 | 0.03 | 0.93 | 0.03 | 0.07 | 1:0 (1.000, 1.000) | dijkstra 28 |
| PLACEBO | 30 | 0.03 [8.4e-04, 0.17] | 0.03 | 0.03 | 1.00 | 0.03 | 0.07 | 1:0 (1.000, 1.000) | dijkstra 29, bf_spfa 1 |

X_0-35 vs MR_0-35 on Y: 23:0 discordant, exact p 2.4e-07 (Holm 7.2e-07).

**T05** (default hash_map, Y = brute_force, route class of iterations 2-3: direct). Twin (slots 0-29): Y share 0.00, off-default 0.00, pass 1.00; twin correct composition: hash_map 30.

| cell | n | Y share [CP 95%] | transfer | off-default transfer | pass ratio | recovery | slot IIA | McNemar b:c (p, Holm) | correct composition |
|---|---|---|---|---|---|---|---|---|---|
| BAN | 30 | 1.00 [0.88, 1.00] | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 30:0 (1.9e-09, 1.1e-08) | brute_force 30 |
| X_0-11 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | hash_map 30 |
| X_12-23 | 30 | 0.43 [0.25, 0.63] | 0.43 | 0.43 | 1.00 | 0.43 | 0.43 | 13:0 (2.4e-04, 7.3e-04) | hash_map 17, brute_force 13 |
| X_24-35 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | hash_map 30 |
| X_0-35 | 30 | 0.43 [0.25, 0.63] | 0.43 | 0.43 | 1.00 | 0.43 | 0.43 | 13:0 (2.4e-04, 7.3e-04) | hash_map 17, brute_force 13 |
| COND | 30 | 1.00 [0.88, 1.00] | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 30:0 (1.9e-09, 1.1e-08) | brute_force 30 |
| RPOS | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | hash_map 30 |

**T06** (default hash_set, Y = index_marking, route class of iterations 2-3: direct). Twin (slots 0-29): Y share 0.00, off-default 0.00, pass 1.00; twin correct composition: hash_set 30.

| cell | n | Y share [CP 95%] | transfer | off-default transfer | pass ratio | recovery | slot IIA | McNemar b:c (p, Holm) | correct composition |
|---|---|---|---|---|---|---|---|---|---|
| BAN | 30 | 0.97 [0.83, 1.00] | 0.97 | 1.00 | 0.87 | 1.00 | 1.00 | 29:0 (3.7e-09, 1.5e-08) | index_marking 25, floyd 1 |
| X_0-11 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | hash_set 30 |
| X_12-23 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.10 | 1.00 | 0.00 | 0.03 | 0:0 (1.000, 1.000) | hash_set 27, floyd 3 |
| X_24-35 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | hash_set 30 |
| X_0-35 | 30 | 0.03 [8.4e-04, 0.17] | 0.03 | 0.13 | 1.00 | 0.03 | 0.07 | 1:0 (1.000, 1.000) | hash_set 26, floyd 2, index_marking 1, sort_adjacent 1 |
| COND | 30 | 0.90 [0.73, 0.98] | 0.90 | 0.90 | 0.97 | 0.93 | 0.90 | 27:0 (1.5e-08, 6.0e-08) | index_marking 26, hash_set 3 |
| RPOS | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | hash_set 30 |

**T1** (default bfs, Y = dfs, route class of iterations 2-3: prompt). Twin (slots 0-29): Y share 0.00, off-default 0.00, pass 0.90; twin correct composition: bfs 27.

| cell | n | Y share [CP 95%] | transfer | off-default transfer | pass ratio | recovery | slot IIA | McNemar b:c (p, Holm) | correct composition |
|---|---|---|---|---|---|---|---|---|---|
| BAN | 30 | 1.00 [0.88, 1.00] | 1.00 | 1.00 | 0.44 | 1.00 | 1.00 | 30:0 (1.9e-09, 1.1e-08) | dfs 12 |
| X_0-11 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.11 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | bfs 30 |
| X_12-23 | 30 | 0.37 [0.20, 0.56] | 0.37 | 0.37 | 0.63 | 0.37 | 0.37 | 11:0 (9.8e-04, 0.002) | bfs 15, dfs 2 |
| X_24-35 | 30 | 0.03 [8.4e-04, 0.17] | 0.03 | 0.03 | 0.81 | 0.03 | 0.03 | 1:0 (1.000, 1.000) | bfs 22 |
| X_0-35 | 30 | 0.47 [0.28, 0.66] | 0.47 | 0.47 | 0.59 | 0.47 | 0.47 | 14:0 (1.2e-04, 4.9e-04) | bfs 13, dfs 3 |
| COND | 30 | 0.33 [0.17, 0.53] | 0.33 | 0.33 | 0.89 | 0.33 | 0.33 | 10:0 (0.002, 0.006) | bfs 17, dfs 7 |
| RPOS | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 0.96 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | bfs 26 |

- **P1 (committed)**: NOT SUPPORTED. Prompt-route tasks transferring at band 0-35 (transfer >= 0.5, pass ratio >= 0.8): ['T2', 'T03'] (need 2 of T2, T03, T10). T05/T06 transfer at band 0-35: {'T05': '0.43', 'T06': '0.03'} (upper 95%: {'T05': '0.63', 'T06': '0.17'}; prediction <= 0.2).
- **Route check (secondary)**: COND transfer T05/T06 {'T05': '1.00', 'T06': '0.90'} (predicted >= 0.5), T2 0.00 (predicted <= 0.2) -> True; RPOS <= 0.2 everywhere -> True.
- **PLACEBO** |transfer| <= 0.1: {'T2': '0.03', 'T03': '0.03', 'T10': '0.00'} -> True.
- **X_0-35 beats MR_0-35 where P1 transfers**: {'T2': True, 'T03': True}.

U6 (COND vs exp16 route arm d): T05: recovery 1.00, off-default transfer 1.00, exp16 F_direct 0.96; T06: recovery 0.93, off-default transfer 0.90, exp16 F_direct 0.99; T03: recovery 1.40, off-default transfer 1.00, exp16 F_direct 0.74; T10: recovery 0.11, off-default transfer 1.00, exp16 F_direct 0.80

### ST: noise-site grid in bf16 (T03, T10; N = 30 per cell)

**T03** (twin correct off-default 0.00).

| site | alpha | n | correct off-default | off-default | pass | median D_R (b35) | median D_g1 (b35) | correct composition |
|---|---|---|---|---|---|---|---|---|
| S0 | 1 | 30 | 0.13 | 0.13 | 1.00 | 1.708 | 1.315 | full_sort 26, quickselect 3, size_k_heap 1 |
| S0 | 2 | 30 | 0.37 | 0.37 | 1.00 | 3.353 | 2.478 | full_sort 19, quickselect 8, size_k_heap 3 |
| S0 | 4 | 30 | 0.33 | 0.40 | 0.87 | 6.293 | 4.628 | full_sort 16, size_k_heap 5, quickselect 5 |
| S0 | 8 | 30 | 0.00 | 0.10 | 0.00 | 12.230 | 7.135 | - |
| S1 | 1 | 30 | 0.03 | 0.03 | 1.00 | 1.876 | 0.628 | full_sort 29, quickselect 1 |
| S1 | 2 | 30 | 0.03 | 0.03 | 1.00 | 3.591 | 1.201 | full_sort 29, quickselect 1 |
| S1 | 4 | 30 | 0.00 | 0.00 | 1.00 | 6.840 | 2.290 | full_sort 30 |
| S1 | 8 | 30 | 0.13 | 0.13 | 0.93 | 10.654 | 3.466 | full_sort 24, quickselect 3, size_k_heap 1 |
| S1E | 2 | 30 | 0.07 | 0.07 | 0.77 | 16.426 | 3.870 | full_sort 21, quickselect 1, size_k_heap 1 |
| S1E | 4 | 30 | 0.03 | 0.07 | 0.93 | 25.287 | 3.845 | full_sort 27, heapify_pop 1 |
| S2 | 1 | 30 | 0.00 | 0.00 | 1.00 | 0.303 | 0.245 | full_sort 30 |
| S2 | 2 | 30 | 0.07 | 0.07 | 1.00 | 0.415 | 0.289 | full_sort 28, quickselect 2 |
| S2 | 4 | 30 | 0.03 | 0.03 | 1.00 | 0.674 | 0.424 | full_sort 29, quickselect 1 |
| S2 | 8 | 30 | 0.00 | 0.00 | 1.00 | 1.056 | 0.606 | full_sort 30 |
| S2E | 2 | 30 | 0.00 | 0.00 | 1.00 | 1.220 | 0.664 | full_sort 30 |
| S2E | 4 | 30 | 0.00 | 0.00 | 1.00 | 1.110 | 0.646 | full_sort 30 |
| S3 | 1 | 30 | 0.17 | 0.17 | 1.00 | - | - | full_sort 25, quickselect 5 |
| S3 | 2 | 50 | 0.26 | 0.34 | 0.94 | - | - | full_sort 33, quickselect 12, size_k_heap 1, other 1 |
| S3 | 4 | 50 | 0.18 | 0.42 | 0.50 | - | - | full_sort 15, quickselect 4, heapify_pop 3, size_k_heap 2 |
| S3 | 8 | 30 | 0.00 | 0.00 | 0.13 | - | - | full_sort 4 |
| S4 | 1 | 30 | 0.03 | 0.03 | 1.00 | 0.956 | 0.728 | full_sort 29, quickselect 1 |
| S4 | 2 | 30 | 0.17 | 0.17 | 1.00 | 1.832 | 1.320 | full_sort 25, quickselect 3, size_k_heap 2 |
| S4 | 4 | 30 | 0.37 | 0.37 | 1.00 | 3.576 | 2.512 | full_sort 19, size_k_heap 9, quickselect 2 |
| S4 | 8 | 30 | 0.00 | 0.13 | 0.10 | 16.027 | 8.332 | full_sort 3 |
| S5 | 1 | 30 | 0.00 | 0.00 | 1.00 | 0.909 | 0.654 | full_sort 30 |
| S5 | 2 | 30 | 0.03 | 0.03 | 1.00 | 1.777 | 1.261 | full_sort 29, size_k_heap 1 |
| S5 | 4 | 30 | 0.03 | 0.03 | 1.00 | 3.270 | 2.307 | full_sort 29, quickselect 1 |
| S5 | 8 | 30 | 0.10 | 0.10 | 1.00 | 5.119 | 3.323 | full_sort 27, quickselect 3 |

Firth indicator model (n 387, events 48, common support 387 of 720 rows):

| term | beta | profile 95% CI | cluster bootstrap 95% CI |
|---|---|---|---|
| S4 | 0.24 | [-0.54, 1.01] | - |
| S5 | -1.52 | [-2.74, -0.51] | - |
| S1 | -0.17 | [-2.64, 2.33] | [-2.58, 2.21] |
| S2 | -0.73 | [-5.71, 1.84] | [-2.12, 1.10] |
| logDR | -1.92 | [-4.76, 0.77] | - |
| logDg1 | 1.97 | [-0.99, 5.03] | - |

Rule model: fallback: energy-matched arms {'S1': 'S1', 'S2': 'S2E'} (raw arm without common support with S0 on log D_R); no energy dummy; converged: True.
- post-hoc sensitivity, alpha <= 4 only (n 295, events 43, converged True): S1 -3.76 profile [-7.29, -0.47] boot [-8.18, -1.40]; S2 -1.70 profile [-6.82, 1.16] boot [-3.96, 0.42]; S4 0.11 profile [-0.75, 0.94]; S5 -2.03 profile [-3.71, -0.75]
- sensitivity, log D_R only: design not identifiable (collinear columns, e.g. S2 == energy when only S2E rows remain)
- primary design on all trimmed rows: design not identifiable (collinear columns, e.g. S2 == energy when only S2E rows remain)

Mantel-Haenszel OR within log D_R quintiles: S0_vs_S1: 4.61 [1.87, 11.34]; S0_vs_S2: - [-, -]; S0_vs_S1E: 0.00 [-, -]; S0_vs_S2E: - [-, -]

Paired site flips (S0-only : other-only, exact McNemar p): S0_vs_S1 24:5 (5.5e-04); S0_vs_S2 22:0 (4.8e-07); S0_vs_S4 17:9 (0.169); S0_vs_S5 23:3 (8.8e-05); S0_vs_S3 21:18 (0.749)

**T10** (twin correct off-default 0.00).

| site | alpha | n | correct off-default | off-default | pass | median D_R (b35) | median D_g1 (b35) | correct composition |
|---|---|---|---|---|---|---|---|---|
| S0 | 1 | 30 | 0.00 | 0.00 | 1.00 | 1.694 | 1.315 | union_find 30 |
| S0 | 2 | 30 | 0.07 | 0.07 | 1.00 | 3.281 | 2.537 | union_find 28, dfs 2 |
| S0 | 4 | 30 | 0.17 | 0.17 | 1.00 | 6.322 | 4.829 | union_find 25, dfs 3, bfs 2 |
| S0 | 8 | 30 | 0.00 | 0.13 | 0.00 | 12.977 | 7.182 | - |
| S1 | 1 | 30 | 0.00 | 0.00 | 1.00 | 1.800 | 0.606 | union_find 30 |
| S1 | 2 | 30 | 0.00 | 0.00 | 1.00 | 3.700 | 1.197 | union_find 30 |
| S1 | 4 | 30 | 0.03 | 0.03 | 1.00 | 7.200 | 2.234 | union_find 29, dfs 1 |
| S1 | 8 | 30 | 0.30 | 0.30 | 0.93 | 10.392 | 3.645 | union_find 19, dfs 8, bfs 1 |
| S1E | 2 | 30 | 0.03 | 0.03 | 0.77 | 15.570 | 4.091 | union_find 22, dfs 1 |
| S1E | 4 | 30 | 0.07 | 0.07 | 0.83 | 22.781 | 4.019 | union_find 23, dfs 2 |
| S2 | 1 | 30 | 0.00 | 0.00 | 1.00 | 0.285 | 0.238 | union_find 30 |
| S2 | 2 | 30 | 0.00 | 0.00 | 1.00 | 0.395 | 0.278 | union_find 30 |
| S2 | 4 | 30 | 0.00 | 0.00 | 1.00 | 0.620 | 0.371 | union_find 30 |
| S2 | 8 | 30 | 0.00 | 0.00 | 1.00 | 0.931 | 0.557 | union_find 30 |
| S2E | 2 | 30 | 0.00 | 0.00 | 1.00 | 1.003 | 0.568 | union_find 30 |
| S2E | 4 | 30 | 0.00 | 0.00 | 1.00 | 1.163 | 0.618 | union_find 30 |
| S3 | 1 | 30 | 0.00 | 0.00 | 1.00 | - | - | union_find 30 |
| S3 | 2 | 50 | 0.14 | 0.20 | 0.92 | - | - | union_find 39, dfs 7 |
| S3 | 4 | 50 | 0.16 | 0.40 | 0.38 | - | - | union_find 11, dfs 6, bfs 2 |
| S3 | 8 | 30 | 0.00 | 0.00 | 0.17 | - | - | union_find 5 |
| S4 | 1 | 30 | 0.03 | 0.03 | 1.00 | 0.910 | 0.747 | union_find 29, dfs 1 |
| S4 | 2 | 30 | 0.20 | 0.20 | 1.00 | 1.717 | 1.308 | union_find 24, dfs 6 |
| S4 | 4 | 30 | 0.33 | 0.37 | 0.97 | 3.315 | 2.467 | union_find 19, dfs 6, bfs 4 |
| S4 | 8 | 30 | 0.13 | 0.33 | 0.13 | 16.291 | 9.122 | bfs 3, dfs 1 |
| S5 | 1 | 30 | 0.00 | 0.00 | 1.00 | 0.930 | 0.647 | union_find 30 |
| S5 | 2 | 30 | 0.00 | 0.00 | 1.00 | 1.789 | 1.225 | union_find 30 |
| S5 | 4 | 30 | 0.00 | 0.00 | 1.00 | 3.267 | 2.278 | union_find 30 |
| S5 | 8 | 30 | 0.03 | 0.03 | 1.00 | 5.089 | 3.429 | union_find 29, dfs 1 |

Firth indicator model (n 374, events 32, common support 376 of 720 rows):

| term | beta | profile 95% CI | cluster bootstrap 95% CI |
|---|---|---|---|
| S4 | 2.51 | [1.39, 3.80] | - |
| S5 | -0.72 | [-3.03, 0.94] | - |
| S1 | 1.14 | [-1.30, 3.64] | [-1.07, 3.24] |
| S2 | 2.38 | [-2.72, 5.40] | [0.69, 5.18] |
| logDR | 0.02 | [-2.94, 2.92] | - |
| logDg1 | 1.22 | [-1.87, 4.36] | - |

Rule model: fallback: energy-matched arms {'S1': 'S1', 'S2': 'S2E'} (raw arm without common support with S0 on log D_R); no energy dummy; converged: True.
- post-hoc sensitivity, alpha <= 4 only (n 292, events 23, converged True): S1 -4.98 profile [-9.77, -0.89] boot [-11.48, -1.53]; S2 -0.56 profile [-6.15, 3.41] boot [-4.93, 2.91]; S4 1.94 profile [0.80, 3.27]; S5 -2.10 profile [-7.02, 0.28]
- sensitivity, log D_R only: design not identifiable (collinear columns, e.g. S2 == energy when only S2E rows remain)
- primary design on all trimmed rows (n 376, events 32, converged True): S1 1.14 profile [-1.30, 3.64]; S2 2.55 profile [-3.12, 8.22]; S4 2.51 profile [1.39, 3.80]; S5 -0.72 profile [-3.03, 0.94]

Mantel-Haenszel OR within log D_R quintiles: S0_vs_S1: 0.82 [0.31, 2.18]; S0_vs_S2: - [-, -]; S0_vs_S1E: 0.00 [-, -]; S0_vs_S2E: - [-, -]

Paired site flips (S0-only : other-only, exact McNemar p): S0_vs_S1 7:10 (0.629); S0_vs_S2 7:0 (0.016); S0_vs_S4 4:18 (0.004); S0_vs_S5 7:1 (0.070); S0_vs_S3 7:9 (0.804)

- **RULE (committed)**: WITHDRAWN as FP8-specific: the site of the choice is open

### State noise (S3) vs departure-matched temperature (DMD), N = 50 paired slots

| task, alpha | K_S3 (nats/token) | T_dmd | f_on | S3-only : DMD-only flips | exact p | S3 flip share | DMD flip share | S3 pass | DMD pass |
|---|---|---|---|---|---|---|---|---|---|
| T03|a2 | 0.3883 | 2.06 | 0.3762 | 12:6 | 0.2379 | 0.26 | 0.14 | 0.94 | 0.98 |
| T03|a4 | 2.3336 | 3.00 | 1.7734 | 8:3 | 0.2266 | 0.18 | 0.08 | 0.50 | 0.82 |
| T10|a2 | 0.2315 | 2.72 | 0.2310 | 7:3 | 0.3438 | 0.14 | 0.06 | 0.92 | 0.92 |
| T10|a4 | 3.0926 | 3.00 | 0.8178 | 8:1 | 0.0391 | 0.16 | 0.02 | 0.38 | 0.70 |

- **Verdict (alpha 2, both tasks, p < 0.05)**: not established at alpha 2 on both tasks (threshold p < 0.05, min 6:0)

### T1 top-five plan push (exp20 u_top5, displacement-targeted at spec, blocks 12-23)

| cell | n | pass | BFS share | correct non-BFS | landing composition | landing test |
|---|---|---|---|---|---|---|
| TWIN | 50 | 0.92 | 1.00 | 0 | - | - (n on survivors -)  |
| BAN | 30 | 0.40 | 0.00 | 12 | dfs 12 | - (n on survivors -)  |
| TOP5_a1 | 30 | 0.67 | 0.97 | 1 | dfs 1 | not computable (< 5 correct programs on survivor algorithms); correct non-BFS programs land on banned algorithms {'dfs': 1} (n on survivors 0)  |
| TOP5_a2 | 30 | 0.30 | 1.00 | 0 | - | not computable (< 5 correct programs on survivor algorithms) (n on survivors 0)  |
| TOP5_a4 | 30 | 0.03 | 0.97 | 0 | - | not computable (< 5 correct programs on survivor algorithms) (n on survivors 0)  |
| TOP5_a8 | 30 | 0.00 | 0.07 | 0 | - | not computable (< 5 correct programs on survivor algorithms) (n on survivors 0)  |
| TOP5BAN | 50 | 0.62 | 0.50 | 10 | dfs 10 | not computable (< 5 correct programs on survivor algorithms); correct non-BFS programs land on banned algorithms {'dfs': 10} (n on survivors 0)  |

Geometry: PCA plane of the 10 forced-prompt centroids (PC1 36%, PC2 25% of centroid variance); points = this artifact's bf16 spec-mean states.

### L: retrospective landing-forecast contest (21 recorded push-landing events)

| event | landing | BASE top-1 | TWINMIN top-1 | OPEN top-1 | log score BASE / OPEN / TWINMIN |
|---|---|---|---|---|---|
| qwen_fp8|T03 | quickselect | quickselect ✓ | -  | quickselect ✓ | -1.36 / -1.67 / - |
| qwen_fp8|T10 | dfs | dfs ✓ | -  | dfs ✓ | -0.84 / -0.78 / - |
| qwen_fp8|T2 | bf_spfa | bf_spfa ✓ | -  | floyd ✗ | -0.96 / -4.59 / - |
| qwen_fp8|T05 | brute_force | brute_force ✓ | -  | brute_force ✓ | -0.73 / -0.05 / - |
| qwen_fp8|T1 | dfs | dfs ✓ | -  | bibfs ✗ | -1.14 / -1.14 / - |
| qwen_bf16|T03 | size_k_heap | quickselect ✗ | quickselect ✗ | quickselect ✗ | -1.50 / -2.64 / -1.50 |
| qwen_bf16|T10 | dfs | dfs ✓ | -  | dfs ✓ | -0.73 / -0.05 / - |
| qwen_panelA|A1 | boyer_moore_vote | boyer_moore_vote ✓ | -  | sort_middle ✗ | -0.38 / -4.95 / - |
| qwen_panelA|A3 | two_pointers | two_pointers ✓ | two_pointers ✓ | monotonic_stack ✗ | -0.33 / -4.38 / -0.14 |
| qwen_panelA|A7 | brute_force | brute_force ✓ | -  | brute_force ✓ | -0.69 / -0.97 / - |
| qwen_panelB|B2 | xor_fold | xor_fold ✓ | xor_fold ✓ | set_sum_identity ✗ | -0.18 / -4.39 / -0.38 |
| qwen_panelB|B3 | prim_heap | prim_heap ✓ | prim_heap ✓ | prim_heap ✓ | -0.44 / -0.05 / -0.15 |
| qwen_panelB|B4 | linear_scan | float_sqrt ✗ | -  | linear_scan ✓ | -1.13 / -0.56 / - |
| qwen_panelB|B7 | sorted_insertion_bisect | sorted_insertion_bisect ✓ | -  | segment_tree ✗ | -0.59 / -4.37 / - |
| gemma|T1 | bfs | bfs ✓ | bfs ✓ | bibfs ✗ | -0.42 / -4.53 / -0.23 |
| gemma|T03 | size_k_heap | quickselect ✗ | -  | quickselect ✗ | -1.70 / -4.80 / - |
| gemma|T04 | builtin | builtin ✓ | builtin ✓ | builtin ✓ | -0.13 / -0.05 / -0.50 |
| gemma|T05 | brute_force | brute_force ✓ | -  | brute_force ✓ | -0.48 / -0.05 / - |
| gemma|T10 | union_find | bfs ✗ | -  | bfs ✗ | -0.96 / -4.39 / - |
| gemma|R6 | binary_search | binary_search ✓ | binary_search ✓ | exponential_search ✗ | -0.12 / -4.38 / -0.38 |
| gemma|T11 | quadratic_dp | quadratic_dp ✓ | -  | quadratic_dp ✓ | -0.06 / -0.04 / - |

- Hits: BASE {'hits': 17, 'n_defined': 21, 'qwen_FP8': [5, 5], 'qwen_bf16': [7, 9], 'gemma_bf16': [5, 7]}, OPEN {'hits': 10, 'n_defined': 21, 'qwen_FP8': [3, 5], 'qwen_bf16': [4, 9], 'gemma_bf16': [3, 7]}, OPEN (1/rank) {'hits': 10, 'n_defined': 21, 'qwen_FP8': [3, 5], 'qwen_bf16': [4, 9], 'gemma_bf16': [3, 7]}, TWINMIN {'hits': 6, 'n_defined': 7, 'qwen_bf16': [3, 4], 'gemma_bf16': [3, 3]}.
- **Primary sign test (BASE > OPEN)**: 8:1 on 9 discordant events (top-1 differ on 9), one-sided p 0.0195; minimum for p < 0.05 is 5 of 5. Verdict: the base runner-up adds information beyond the instruct model's own opening ranking.
- Log scores: BASE - OPEN {'n': 21, 'mean_diff': 1.61598765143499, 'wilcoxon_p_two_sided': 0.03191947937011719}; BASE - TWINMIN {'n': 7, 'mean_diff': 0.02278126482582273, 'wilcoxon_p_two_sided': 0.6875}.

### Extensions (forced sources, semantic seed, W4)

| task | cell | n | Y / default share | off-default share | pass | composition |
|---|---|---|---|---|---|---|
| T03 | BAN_W4 | 10 | 0.30 (quickselect) / 0.00 | 1.00 | 1.00 | size_k_heap 7, quickselect 3 |
| T03 | TWIN_W4 | 10 | 0.00 (quickselect) / 1.00 | 0.00 | 1.00 | full_sort 10 |
| T03 | X_0-35_W4 | 10 | 0.60 (quickselect) / 0.00 | 1.00 | 0.80 | quickselect 6, size_k_heap 4 |
| T10 | BAN_W4 | 10 | 0.80 (bfs) / 0.00 | 1.00 | 1.00 | bfs 8, dfs 2 |
| T10 | FORCED | 30 | 1.00 (bfs) / 0.00 | 1.00 | 1.00 | bfs 30 |
| T10 | FORCEDPAD | 30 | 0.00 (bfs) / 1.00 | 0.00 | 1.00 | union_find 30 |
| T10 | FORCEDX_0-35 | 30 | 0.93 (bfs) / 0.00 | 1.00 | 0.87 | bfs 28, dfs 2 |
| T10 | TWIN_W4 | 10 | 0.00 (bfs) / 1.00 | 0.00 | 1.00 | union_find 10 |
| T10 | X_0-35_W4 | 10 | 0.70 (bfs) / 0.00 | 1.00 | 1.00 | bfs 7, dfs 3 |
| T2 | BAN_W4 | 10 | 0.70 (bf_spfa) / 0.30 | 0.70 | 1.00 | bf_spfa 7, dijkstra 3 |
| T2 | FORCED | 30 | 1.00 (bf_spfa) / 0.00 | 1.00 | 0.90 | bf_spfa 30 |
| T2 | FORCEDPAD | 30 | 0.03 (bf_spfa) / 0.97 | 0.03 | 0.97 | dijkstra 29, bf_spfa 1 |
| T2 | FORCEDX_0-35 | 30 | 1.00 (bf_spfa) / 0.00 | 1.00 | 1.00 | bf_spfa 30 |
| T2 | SEED | 30 | 0.00 (bf_spfa) / 1.00 | 0.00 | 0.93 | dijkstra 30 |
| T2 | SEEDPAD | 30 | 0.03 (bf_spfa) / 0.97 | 0.03 | 0.97 | dijkstra 29, bf_spfa 1 |
| T2 | SEEDX_0-35 | 30 | 0.07 (bf_spfa) / 0.93 | 0.07 | 0.87 | dijkstra 28, bf_spfa 2 |
| T2 | TWIN_W4 | 10 | 0.00 (bf_spfa) / 1.00 | 0.00 | 1.00 | dijkstra 10 |
| T2 | X_0-35_W4 | 10 | 0.70 (bf_spfa) / 0.30 | 0.70 | 1.00 | bf_spfa 7, dijkstra 3 |

### Novelty audit

- 2 correct 'other' programs; classes {'CATALOGUE_VARIANT': 2}; cost USD 0.00114.

### Independent re-derivation: 295 checks, 0 mismatches.

