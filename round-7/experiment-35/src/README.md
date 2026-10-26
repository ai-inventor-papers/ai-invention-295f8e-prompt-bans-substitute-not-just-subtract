# Where temperature can change the chosen algorithm (iteration 7, claim T, bf16 Qwen3-8B)

Qwen3-8B (revision `b968826d…`, bf16, thinking off) writes one of two algorithms on three coding units:

- **B3**, minimum spanning tree weight: Kruskal 0.80 vs Prim with a heap 0.19;
- **A3**, trapped rain water: prefix/suffix maximum arrays 0.68 vs two pointers 0.31;
- **B6**, valid anagram: sort and compare 0.77 vs a fixed 26-slot count array 0.13 (plus a hash map 0.10).

On four other tasks it writes only one algorithm: T1 grid path (BFS), T2 shortest path (Dijkstra), T10 connected components (union-find) and T03 k-th smallest (full sort).

This artifact asks three questions:

1. Where, token by token, is the algorithm decided?
2. Can the effect of temperature and top-k on the algorithm be **predicted in advance** from the logits at that decision point?
3. Is that decision point linked to the task-specification states that iterations 4-6 showed carry the plan?

All predictions were hash-committed before the first temperature sample (`commitments.log`; COMMIT #0, #1 and #2 verify).

## Results

**In plain terms (is temperature the creativity knob?).** On these coding tasks it is not a knob for new ideas. It is a knob on one token.

- **Where the choice is made.** The model chooses between the algorithms it already knows at a single sampled token: a comment word (`# Prim's…` vs `# Kruskal's…`) or the first statement after the input guard.
- **What temperature does.** It only reweights that token, and the probability of reaching it.
  - Lowering T collapses the output onto the default algorithm, as predicted in advance from the logits.
  - Raising T above 1 does not add the alternative, because it is already at its natural rate.
  - On tasks where the alternative is about 5-17 nats behind, temperature cannot reach it at all.
  - Top-k 10 changed nothing. Across T, ideas stay within the 2-3 known algorithms; only their phrasings multiply.
- **What does move the choice.** The task-specification states. Swapping in the states of a prompt that names the other algorithm gives that algorithm on 30 of 30 seeds, against 0-23% without the swap. The argmax token at the fork flips with it (` Kr` -> ` Prim`).

**Bottom line.**

- **The algorithm is decided by one sampled token, at a predictable place (Test 1: passes on 3 of 3 units).** Prefix resampling finds a sharp fork on every unit. The confirmed forks of the on-opening base paths sit exactly at the first token after the canonical opening (|O|+1).
  - **B3**: the decision is the word that follows `    # ` after the adjacency list is built. ` Kr` (Kruskal's) has probability 0.72 and leads to Kruskal 100%; ` Prim` has 0.27 and leads to Prim 97%.
  - **A3**: after `if not height: return 0`, ` n` leads to prefix/suffix arrays and ` left` to two pointers. In the second opening cluster the split is ` left =` vs ` left_max`.
  - **B6**: after `if len(s) != len(t): return False`, ` return` leads to sorting and ` count` to counting. Fixed array vs hash map is settled a few tokens later.
  - The conditional entropy of the algorithm given the fork token's class is 0.05, 0.15 and 0.19 bits (bootstrap 95% upper bounds 0.10 / 0.20 / 0.24; threshold 0.3).
  - The sampler calibration check passes on every unit: the k = 0 resamples reproduce the twin's minority share (Fisher p 0.58 / 0.20 / 0.19).
- **Temperature acts on that token and on staying on the opening (Test 2: passes on B3 only, so not passed).**
  - The committed prediction function takes the teacher-forced logits along the opening and at the fork, and the token conditionals P(A | t) measured at T 1. It predicted:
    - **B3**: Prim 0.07 / 0.19 / 0.24 / 0.25 at T 0.3 / 0.7 / 1.0 / 1.3. Observed in the same-seed sweep (N = 50 per cell): 0.06 / 0.22 / 0.40 / 0.38.
      - MAE 0.083.
      - Minority drop from T 1.0 to 0.3: 0.34 [0.22, 0.48] (predicted 0.17). Exact McNemar 17:0, p = 1e-5.
      - T 1.0 -> 1.3: observed -0.02 vs predicted +0.01.
      - **Passes.**
    - **A3**: predicted 0.17 / 0.29 / 0.31 / 0.32; observed 0.10 / 0.18 / 0.18 / 0.20. MAE 0.105, drop 0.08 (McNemar 7:3, p = 0.17). **Fails.**
    - **B6**: predicted 0.16 / 0.18 / 0.20 / 0.21; observed 0.18 / 0.14 / 0.12 / 0.18. MAE 0.043, but no drop (-0.06). **Fails the drop criterion.** The prediction itself said there would be no drop of 0.15: B6's W3 template prefers ` count` even greedily, and about 19% of samples leave the opening at every temperature.
  - Pooled B3 + A3 drop: McNemar 24:3, one-sided p = 2.5e-5. This survives Bonferroni 0.05/7, so it is significant both unadjusted and adjusted.
  - The predicted on-opening shares match the observed ones closely. B3 at T 0.3 / 0.7 / 1.0 / 1.3 is 0.99 / 0.87 / 0.72 / 0.55 predicted vs 1.00 / 0.92 / 0.76 / 0.60 observed. The plan's main confound, temperature acting on early phrasing, is therefore carried correctly.
  - **Per seed, the mechanism is almost exact.** The committed per-slot replay walks the opening with each slot's own uniform numbers and reads the class of the fork token it picks. It names the algorithm of an individual sampled program correctly in 0.90-0.98 of the on-opening slots in every cell.
  - Post hoc, on A3 the replay-implied shares of the actual 50 streams (0.08 / 0.18 / 0.18 / 0.16) reproduce the observed sweep (0.10 / 0.18 / 0.18 / 0.20). A3's miss is therefore the gap between a 50-stream cell and its expectation, not a mechanism error. The same sampler at the twin's slots gave 0.32 (Fisher p 0.08 vs the sweep's T 1.0 cell). On B3 the twin's 0.20 vs the sweep's 0.40 at T 1.0 differ at p = 0.011.
- **Raising temperature from 1.0 to 1.3 does not add the minority algorithm, and top-k 10 changes nothing.**
  - Predicted change T 1.0 -> 1.3: +0.01 / +0.01 / +0.01. Observed: -0.02 / +0.02 / +0.06.
  - Above T 1 two effects cancel. The fork distribution, two dominant tokens, flattens only slightly towards the minority. Meanwhile fewer samples stay on the opening, and the programs that leave it are mostly the default.
  - **All 600 same-seed top-k 10 programs are token-for-token identical to their top-p 1 counterparts.** The mass outside the top 10 at the fork is below 3e-4 on every template.
- **The four collapsed tasks are out of temperature's reach (Test 3: passes, 4 of 4).**
  - Fork margins: T1 7.46, T2 4.85, T10 17.04 and T03 6.10 nats (threshold 4).
  - Predicted off-default rate at T 1.3: 0.002, 0.020, 0.000 and 0.009.
  - Bound check (100 continuations at T 1.3 from each fork node): 0/100 off-default on every task.
  - T 1.3 check (N = 20): 1/20 (T1), 1/20 (T2), 0/20 (T10) and 0/20 (T03). T1's single off-default program is unlikely under its margin (binomial p 0.04).
  - The record (797/800 default, no same-seed flips) implies margins of about 6 nats.
- **The fork is where the task-state plan lands (S4).**
  - **S4(b), forced-state exchange.** Take the task-specification states of the prompt 'Implement <minority algorithm> for this task.' and exchange them, at all blocks, into its padding twin, where the instruction is replaced by ' .'. This gives the minority algorithm on **30 of 30 slots on all three units**:
    - B3: Prim 1.00 vs 0.23 for the padding twin, McNemar 23:0, p = 1e-7;
    - A3: 1.00 vs 0.13, 26:0;
    - B6: 1.00 vs 0.00, 30:0.
    - Every exchanged program passes the hidden tests.
    - The matched-norm random exchange gives 0.40 / 0.13 / 0.00.
    - Teacher-forced fork margins move by -4.9 / -5.5 / -22.1 nats under the exchange vs -1.2 / -2.0 / +0.3 under MR.
    - In activation coordinates (F7), the exchanged fork state lands on the minority-token cluster (B3 ` Prim`, A3 ` left`, B6 ` count`). The padding twin stays on the default cluster, and so does MR on B3 and B6. On A3, the single random draw used for the teacher-forced MR state also puts the argmax at ` left`. The 30 generated MR slots each draw their own random states, and 14 of the 15 whose fork is on the main opening take ` n`; only 4/30 MR programs are two pointers.
  - **S4(a), random task-state pushes (descriptive, N = 10 per direction).** Across 8 isotropic pushes at alpha 2, the pushed fork margin predicts the direction of the share change. Spearman rho between the margin change and the minority-share change, with the lower-tail exact permutation p:
    - B3: -0.69 (p 0.027);
    - A3: -0.44 (p 0.12);
    - B6: -0.94 (p 0.0003).
    - The pushed predictions beat a 'no push effect' prediction by +0.05 / +0.11 / +0.16 nats per sample. Their absolute errors are 0.15-0.19.
- **Ideas vs phrasings (the 1a-c question; results/table_1ac.json).** Temperature redistributes samples between the same 2-3 known ideas, and the phrasings within each idea grow with T.
  - No temperature or top-k setting produced an idea outside the catalogue.
  - At T 0.3 with top-k 10, the 10 literal trajectories (slots 20-21 x W1-W5) are 9 Kruskal + 1 Prim on B3, with 3 + 1 phrasing clusters (AST 4-gram Jaccard 0.8). Answer: about 1 idea with a few phrasings, case 1a.
  - At T 1.0-1.3 they are 4 Kruskal + 6 Prim, still 2 ideas, with 2-3 phrasing clusters each.
  - Over 50 programs, Kruskal's phrasing clusters at Jaccard 0.9 grow from 4 (T 0.3) to 6, 10 and 12 (T 1.3). Prim's grow from 1 to 4, 11 and 10.
  - Correct-only Hill-1 diversity (rarefied to 25 programs):
    - B3: 1.25 -> 1.69 -> 1.95 -> 1.92;
    - A3: 1.37 -> 1.58 -> 1.74 -> 1.79;
    - B6: flat at about 1.8.
  - With the seed held fixed, the idea changes across the four temperatures on 20 of 50 slots (B3), 12 (A3) and 11 (B6).
- **No novel algorithm.**
  - Every one of the 2,290 generated programs carries a catalogue label after adjudication.
  - The only correct off-catalogue programs are 40 continuations from one low-probability B6 fork token. They form 2 distinct programs, both the frozen catalogue's named extra mode `alphabet_count_scan` (`s.count(c) == t.count(c)`). My manual read classed both as catalogue variants. Judge controls scored 3/3.

| committed test (COMMIT #2) | result | verdict |
|---|---|---|
| (1) H(A \| fork class) <= 0.3 bits on >= 2 mixed units | 0.050 / 0.153 / 0.189 bits | **pass** (3/3) |
| (2) drop T 1.0 -> 0.3 >= 0.15, MAE <= 0.10, \|dObs - dPred\|(1.0 -> 1.3) <= 0.10, on >= 2 units | B3 passes; A3 (MAE 0.105, drop 0.08) and B6 (drop -0.06) fail | **fail** (1/3) |
| (3) collapsed margins >= 4 nats on all 4 tasks | 7.46 / 4.85 / 17.04 / 6.10 | **pass** |
| disconfirming branches (H > 0.5 bits or MAE > 0.2 on >= 2 units) | none fires | - |
| **claim T** | | **PARTIAL** |
| secondary (Holm family input): pooled B3 + A3 exact one-sided McNemar | 24:3, p = 2.5e-5 | significant unadjusted and at Bonferroni 0.05/7 |

**How to read these results (scope and limits).**

- **Behavioural decision point, not a circuit.** The fork is located by behaviour (prefix resampling with a
  pre-registered change-point rule), so it says where the choice becomes fixed in the token stream, not which
  components compute it.
- **Estimates, not single draws.** Every effect is estimated over 5 prompt templates and many seeds. Fork positions are
  reported per base path; shares carry Wilson or bootstrap intervals; S4(a) is reported per direction.
- **Declared map class (S4(b)).** The exchange is position-wise identity alignment: the forced prompt's residual
  states replace the padding twin's at the same task-specification positions, at every block. It has no fitted
  parameters, and the identity check (twin into twin) is exact. Its control is a matched-norm random replacement at
  the same sites.
- **Actionability with collateral measured.** The exchange is scored on the generated program and on its hidden-test
  pass rate, not on decodability. Every exchanged program passes the hidden tests.
- **What one-token concentration does and does not show.** It shows a single token's class nearly fixes the
  algorithm. It does not show that temperature has no other effects: it changes phrasing and leaving the opening, which
  the predictions model explicitly.
- **Scope.** One model (Qwen3-8B, bf16, thinking off) and three mixed coding units. The collapsed side is four tasks.

**Validity checks.**

- Engine:
  - CRN determinism 10/10 identical;
  - batch size 1 vs 16: 10/10 identical;
  - batch size 10 vs 16: 7/10 identical, a kernel sensitivity, so every same-seed comparison uses one fixed batch composition;
  - replay of the sampler transform: 10,000/10,000 exact;
  - identity hooks: exact;
  - teacher-forced vs incremental logits along every opening: argmax agreement 1.00, maximum difference 1.4 bf16 logits.
- Engine check against iteration 6 (RTX 2000 Ada vs this RTX 4090): per-slot labels agree on 0.95 of slots (T2 and T03), with 17/20 and 19/20 programs token-identical.
- Opening classifier (OC_u): agreement 1.00 and coverage 1.00 on 199-200 programs per unit. Undecided continuations were completed and labelled by the frozen labellers.
- Labeller style re-gate: 30 twin programs per unit (10 minority programs each) went to two blind judges plus a tiebreaker. The adjudicated labels agree with the frozen labellers on 30/30 for every unit (threshold 0.9; `results/regate.json`).
- Independent re-derivation with the standard library only (`src/rederive.py`): 62 checks (tests 1-3, every sweep cell, S4(b) arms and McNemar tests, twin shares), 0 mismatches.
- Separate headline audit (`audit/headline_audit.py`, own softmax, top-k, rank correlation and exact tests, from raw rows and raw logits) reproduces:
  - H(A | C), top-k identity (600/600), replay accuracy, the S4(a) and S4(b) statistics, the collapsed checks, the engine check and all four margins;
  - all 24 committed cell predictions, to within 5e-6.
  - Its placebos (random arm or direction relabelling) reject at about the nominal 5%. Its placebo (temperature labels permuted within slots) passes the drop test in 1% of 500 permutations on B3, so the placebo fails, as it should.
- Hash chain verified.
- Cost: about 0.75 GPU-hours on one RTX 4090 (40 min of GPU stages plus 7 model loads); OpenRouter USD 0.022 (judges only: disagreements, style re-gate, novelty audit).

## What was run

Every arm runs in the iteration-6 bf16 HF engine (`engine5.decode_rows`, reused unchanged): fp64 logits / T -> top-k mask -> inverse CDF over the full vocabulary in token-id order. Every program slot owns one PCG64 uniform stream, so each slot keeps its stream across arms. Labels come from the frozen iteration-5/6 labellers: hidden tests, runtime tracer and AST. Two blind judges plus a tiebreaker see labeller disagreements only.

| part | what | design |
|---|---|---|
| S0 | twins | N = 100 per mixed unit (slots 0-19 x W1-W5, T 1.0, top-p 1); collapsed twins and the engine check N = 20 at iteration-6 keys |
| S1 | fork location | Token trie over the twin programs gives the canonical opening(s) O. Base paths: 12 per unit (8 for B6), at least 2/3 on O. 8 continuations per prefix length k in {0, 4, ..., 96} (to 160 where needed), labelled by OC_u. Bayesian single change point (Dirichlet-multinomial, uniform tau, prior 0.5, P >= 0.9, share jump >= 0.4). Single-token refinement, then confirmation with 20 continuations at f-1, f and controls f-9, f+8. Calibration on the pooled k = 0 resamples. **COMMIT #1** |
| S2 | predictions | Teacher-forced fp32 logits along every opening and at the fork, for every template. P(A \| t) for the top 20 fork tokens (20 continuations under W1 + 5 under each other template) plus a residual bin; persistence at T 1.3. Cell predictions for T in {0.3, 0.7, 1.0, 1.3} x {top-p 1, top-k 10} (on-opening probability explicit); per-slot replay. Collapsed margins with bound checks and the 48-token LLR. S4 teacher-forced margins and shares. **COMMIT #2** (with the scoring code's sha256) |
| S3 | same-seed sweep | 3 units x 4 T x 2 samplers x 50 slots (slots 20-29 x W1-W5), the same 50 streams in all 8 cells: 1,200 programs |
| E2 | collapsed check | T1, T2, T10 and T03 at T 1.3, N = 20 each |
| S4(a) | random task-state pushes | 8 iteration-4 directions (rand_9101..9108) x 10 slots per unit, alpha 2 x the unit's ban displacement n[l,p], blocks 12-23, task-spec positions, prefill only; the twin at the same slots is the control |
| S4(b) | forced-state exchange | 'Implement <A_min>' prompt, its padding twin, the exchange of the forced prompt's task-spec states (all 36 blocks) into the padding twin, and MR (matched-norm random exchange); 30 shared slots per arm |
| F7 | geometry | Block-24 residual at the fork-token position for every candidate fork token, with the pushed, exchanged and MR states, in difference-in-means x PC1 coordinates |
| G | novelty audit | Every correct off-catalogue program: nearest known solutions (unit references and all ten datasets of art_j3Rm_lr2nzR6), two blind judges + tiebreak with known-class controls, manual read |

Figures (`figures/*.pdf|png`):

- `F1_outcome_curves`: own-class share vs prefix length per base path, with forks; `F1b_changepoint_posteriors`;
- `F2_fork_token_probabilities`: fork-token probabilities coloured by P(A_min | t), with the top-10 cut;
- `F3_pred_vs_obs`: committed predictions vs observed shares over T, for both samplers, with Wilson CIs;
- `F4_margins`: fork margins of mixed and collapsed units in nats, with the binary p_T curves;
- `F5_s4a_push`: pushed margin change vs share change;
- `F6_s4b_exchange`: exchange arms;
- `F7_fork_geometry`: actual activation-space coordinates of the fork-token states.

## Deviations from the plan

Every deviation is listed with its reason in `results/deviations.json`. The main ones:

- **GPU and caps.**
  - RTX 4090 (24 GB) instead of the planned RTX A4500, so the whole bf16 model fits on the GPU.
  - max_new is 768 / 640 / 384 tokens for B3 / A3 / B6 instead of 1024. The twins' longest programs are 346 / 168 / 103 tokens, and no program in any arm reached the cap.
  - Arms ran at full size directly instead of 10 -> 100 -> full; per-batch timings are in `results/timing.jsonl`.
- **A_min amendment (B6).** The new twin's runner-up is `fixed_count_array` (13/100), not the planned `hash_count` (10/100). By the plan's rule this was amended before COMMIT #1, and the S4(b) forced prompt names it.
- **COMMIT #0** was written after the S0 twins (reference data) were generated. All thresholds had been fixed in `src/cfg7.py` before the twins ran.
- **B3's twin minority share** (0.19) sits 0.15 below the iteration-5 record (0.34), at the edge of the confirmation signal. The prompts are byte-identical to iteration 5 (sha256 checked).
- **Mode rule caveat.** The plan's share-jump thresholds (>= 0.4 detect, >= 0.5 confirm) can only fire on minority base paths, because a default path starts at about 0.7. So the forks are confirmed on minority paths (5/12, 2/12 and 1/8 base paths). The detect and confirm rules were applied as committed.
- **Collapsed margins (D5).**
  - Each top fork token got 10 continuations; tokens from alternative programs got 20.
  - On T1 and T2 no single token commits off-default. The walk along the runner-up's path stopped at 16 tokens without reaching P(off) >= 0.8, so the reported margin is that 16-token path margin.
- **S4.**
  - Predictions use the main opening cluster plus q_rest.
  - The committed S4(a) permutation p was upper-tail. The lower tail, in the predicted negative direction, is added as a post-commit correction, and both are in `results/s4a.json`.
- **Judges and post hoc.** The judges resolved labeller disagreements after COMMIT #2. Replacing the 'disputed' continuations, which the committed counts treated as 'other', by judged labels leaves every committed prediction unchanged to three decimals (`results/posthoc.json`, labelled POST HOC).

## Layout

| path | content |
|---|---|
| `method.py` | entry point: every stage in order (`.venv/bin/python method.py all`, or a comma list of stages) |
| `src/cfg7.py` | constants, units, slots, CRN keys, committed thresholds |
| `src/vendor_inputs.py` | A1: copies every prior input into `inputs/` with sha256 (`inputs/input_hashes.json`, `inputs/SHA256SUMS`) |
| `src/prompts7.py` | twin / ban / forced / padding prompts and U3 checks -> `prompts/prompts7.jsonl`, `prompts/positions7.json` |
| `src/engine7.py` | the reused iteration-6 engine plus the stop-callback decoder for continuations, teacher forcing and edit hooks |
| `src/gpu7.py`, `src/stages7.py`, `src/stages7b.py` | GPU stages: tests, twins, fork scan (Part C), predictions (Part D), generation (Part E), geometry |
| `src/opening_cls.py` | OC_u, the opening classifier over partial programs |
| `src/label7.py` | label worker (frozen B3/B6, A3 and collapsed-task labellers) |
| `src/forks.py`, `src/predict.py`, `src/replay.py` | trie openings and change points; the committed prediction function; the independent sampler replay |
| `src/predictions7.py` | D3-D6 numbers and COMMIT #2 |
| `src/analysis_T.py` | committed scoring: tests 1-3, verdict, S4(a), S4(b), the 1a-c table |
| `src/rederive.py` | standard-library re-derivation with placebo |
| `audit/headline_audit.py` | independent re-derivation of the remaining headline numbers (own softmax, rank correlation and exact tests) with placebos -> `results/headline_audit.json` |
| `reproducibility.md`, `restore.sh` | step-by-step reproduction of what was run; restore script for every deleted path |
| `src/posthoc7.py` | post-hoc sensitivities (labelled as such) |
| `src/novelty7.py` | dependency extract, blind judges, novelty audit |
| `src/figures7.py`, `src/report7.py`, `src/outputs7.py`, `src/views7.py` | figures, `results/summary.md`, `method_out.json`; engine-check, calibration and top-k views |
| `src/cpu7.py`, `src/commit7.py` | U1-U8 tests, COMMIT #0/#1, the sha256 chain |
| `commitments.log`, `predictions/` | hash chain; `commit0.json`, `commit1_forks.json`, `commit2_predictions.json`, `predictions_raw.json`, `s4_raw.json`, `collapsed_raw.json`, `hardware.json` |
| `data/samples_raw.jsonl`, `data/labels.jsonl` | 2,290 programs (ids, text, slot, cell, CRN key) and their labels |
| `data/continuations.jsonl`, `data/continuation_labels.jsonl` | 12,676 prefix-resampling continuations (OC labels; full labels for undecided ones) |
| `data/collapsed_conts*.jsonl`, `data/judge_labels.jsonl` | collapsed-margin continuations; judge adjudications |
| `results/` | `twins`, `opening_classifier`, `regate`, `engine_check`, `calibration`, `topk_report`, `forks`, `predictions_view`, `test1`, `test2`, `test3`, `verdict`, `s4a`, `s4b`, `table_1ac`, `novelty_audit`, `rederive`, `posthoc`, `gpu_tests`, `tests_cpu`, `timing.jsonl`, `costs`, `deviations` (.json), `summary.md` |
| `figures/` | F1-F7 (.pdf and .png) |
| `restore.sh` | restores every path the manifest deletes (environment, teacher-forced logit cache, __pycache__) and the model weights |
| `cache/` | `geometry_<unit>.npz` (F7 states), `dose_<unit>.npy` (S4(a) n[l,p]), `tf/` (teacher-forced logits; removed after the round, see below) |
| `inputs/` | sha256-verified copies of the prior artifacts this pipeline reads, plus `inputs/dep_extract.json` (195 relevant rows found across all ten datasets of art_j3Rm_lr2nzR6) |
| `method_out.json` (+ `full_`, `mini_`, `preview_`) | exp_gen_sol_out output with datasets twin, sweep, collapsed, s4a, s4b and fork_scan; schema-validated |

Every kept file is under 100 MB and is published with the repository.

## How to run

`reproducibility.md` lists exactly what was run, in order, with seeds, hardware, timings and the expected numbers.

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python src/download_models.py          # Qwen/Qwen3-8B@b968826d into the HF cache
.venv/bin/python method.py all                   # or: vendor,prompts,gputests,twins,cputests,commit0,forkscan,
                                                 #     commit1,predict,commit2,generate,finalize
```

- The GPU stages need one CUDA GPU with at least 20 GB; this run took about 0.75 GPU-hours on an RTX 4090.
- The judges need `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY`.
- Every stage resumes from its files. The commit stages refuse to overwrite an existing commit.

## Restoring removed files

| removed path | restore with |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` |
| `cache/tf/` (teacher-forced logits, about 1.4 GB) | `.venv/bin/python src/gpu7.py predict,s4predict --units B3,A3,B6` (deterministic; existing continuations are reused) |
| `**/__pycache__/` | `.venv/bin/python -m compileall -q src inputs` |
| model weights (shared HF cache, not in this folder) | `.venv/bin/python src/download_models.py` (Qwen/Qwen3-8B@b968826d9c46dd6066d109eabc6255188de91218) |

## Appendix: result tables

All tables are generated by `src/report7.py` into `results/summary.md`. Key extracts follow.

| unit | |O| (clusters, coverage) | fork tokens (pi_1 by template W1-W5) | H (bits) | margin (nats) |
|---|---|---|---|---|
| B3 | 61 (c0 0.51, c1 0.20) | ` Kr` 0.77/0.62/0.77/0.81/0.61 -> Kruskal; ` Prim` 0.22/0.37/0.22/0.18/0.37 -> Prim | 0.050 | 0.99 / 1.38 |
| A3 | 18 (c0 0.48), 19 (c1 0.31) | c0: ` n` 0.90/0.90/0.78/0.73/0.73 -> arrays, ` left` -> two pointers; c1: ` =` -> two pointers, `_max` -> arrays | 0.153 | 1.55 / -1.45 |
| B6 | 23 (c0 0.78) | ` return` 0.68/0.82/0.32/0.97/0.90 -> sort; ` count` 0.32/0.18/0.68/0.03/0.10 -> counting (fixed array 0.8) | 0.189 | 1.45 |

| unit | cell (top-p 1) | predicted A_min | observed [Wilson 95%] | on-opening obs / pred | replay accuracy |
|---|---|---|---|---|---|
| B3 | T 0.3 / 0.7 / 1.0 / 1.3 | 0.068 / 0.193 / 0.237 / 0.247 | 0.06 [0.02, 0.16] / 0.22 [0.13, 0.35] / 0.40 [0.28, 0.54] / 0.38 [0.26, 0.52] | 1.00/0.99, 0.92/0.87, 0.76/0.72, 0.60/0.55 | 0.98 / 0.96 / 0.95 / 0.94 |
| A3 | T 0.3 / 0.7 / 1.0 / 1.3 | 0.166 / 0.285 / 0.311 / 0.319 | 0.10 [0.04, 0.21] / 0.18 [0.10, 0.31] / 0.18 [0.10, 0.31] / 0.20 [0.11, 0.33] | 0.88/0.86, 0.84/0.82, 0.74/0.76, 0.70/0.70 | 0.98 / 0.98 / 0.92 / 0.97 |
| B6 | T 0.3 / 0.7 / 1.0 / 1.3 | 0.161 / 0.182 / 0.200 / 0.212 | 0.18 [0.10, 0.31] / 0.14 [0.07, 0.26] / 0.12 [0.06, 0.24] / 0.18 [0.10, 0.31] | 0.80/0.81, 0.76/0.82, 0.78/0.81, 0.80/0.79 | 0.93 / 0.95 / 0.90 / 0.95 |

The top-k 10 cells are identical to the top-p 1 cells (600/600 programs token-identical).

| S4(b) | forced | padding twin | exchange | MR | exchange vs pad (McNemar) | d margin exchange / MR |
|---|---|---|---|---|---|---|
| B3 (Prim) | 1.00 | 0.23 | 1.00 | 0.40 | 23:0, p 1.2e-7 | -4.87 / -1.25 |
| A3 (two pointers) | 1.00 | 0.13 | 1.00 | 0.13 | 26:0, p 1.5e-8 | -5.50 / -2.00 |
| B6 (fixed array) | 1.00 | 0.00 | 1.00 | 0.00 | 30:0, p 9.3e-10 | -22.12 / +0.26 |
