# Top-five ban: who obeys, and where do the survivors land?

Iteration 8 of the algorithm-choice study (`gen_plan_experiment_6_idx7`).

**Question.** On the T1 grid-path task, a prompt bans each model's own five most-used path-search algorithms by name. Which open-weight models obey with a correct program? For the model that obeys most, where do the surviving algorithms sit on the model's 10-algorithm activation manifold: at the edge of the banned five, or on the opposite side?

The run has two halves:

1. a behavioural screen of 8 new open-model configurations plus 2 carried rows;
2. geometry in actual activation coordinates on the selected model: Qwen3-32B with thinking on, states read from the nf4 checkpoint.

Every decisive rule was hash-committed before the sample it governs (`commitments.log`, 4 commits).

## Headline results

All numbers come from `results/*.json`. `src/rederive.py` re-derives them from the raw rows (stdlib + numpy only); see "Re-derivation" below.

### 1. Screen: almost no open model obeys a five-name ban

Each configuration's own baseline defines its banned set B_c (top five by implemented count, filled from [BFS, DFS, greedy, IDDFS, A*]). For **every** configuration B_c = {BFS, DFS, IDDFS, A*, greedy best-first}, because every baseline is BFS/DFS only.

A **correct survivor** is a ban-arm program that passes the 48-case hidden suite and whose adjudicated mechanism is outside B_c: a catalogue algorithm, or a named known algorithm outside the catalogue.

| Config | Model (engine) | Baseline (N) | Ban N | Correct survivors | Share (Wilson 95%) | Banned-mechanism share | Pass rate |
|---|---|---|---|---|---|---|---|
| C1 | Qwen3-8B thinking on (local vLLM, FP8 W8A16) | BFS 30/30 | 30 | 0 | 0.00 (0.00-0.11) | 1.00 | 0.13 |
| C2 | Llama-3.1-8B-Instruct (CoreWeave bf16) | BFS 77, DFS 20, other 3 | 50 | 0 | 0.00 (0.00-0.07) | 0.90 | 0.02 |
| C3 | Qwen3-14B thinking off (DeepInfra fp8) | BFS 94, DFS 6 | 50 | 0 | 0.00 (0.00-0.07) | 1.00 | 0.46 |
| C4 | Qwen3-14B thinking on (DeepInfra fp8) | BFS 96, DFS 4 | 50 | 7 | 0.14 (0.07-0.26) | 0.76 | 0.32 |
| C5 | Qwen3-32B thinking off (DeepInfra fp8) | BFS 81, DFS 19 | 50 | 4 | 0.08 (0.03-0.19) | 0.82 | 0.28 |
| **C6** | **Qwen3-32B thinking on (DeepInfra fp8)** | BFS 91, invalid 9 | 50 | **17** | **0.34 (0.22-0.48)** | 0.22 | 0.42 |
| C7 | gemma-3-27b-it (DeepInfra fp8) | BFS 99/99 | 50 | 0 | 0.00 (0.00-0.07) | 1.00 | 0.86 |
| C8 | Qwen2.5-Coder-32B-Instruct (Cloudflare) | DFS 52, BFS 48 | 50 | 0 | 0.00 (0.00-0.07) | 0.94 | 0.40 |
| C9 | Qwen3-8B thinking off (carried, iteration 2) | BFS 100 | 100 | 0 | 0.00 (0.00-0.04) | 1.00 | 0.68 |
| C10 | gemma-3-4b-it (carried, iteration 6) | n/a | 50 | 0 | 0.00 (0.00-0.07) | 1.00 | 0.38 |

- **The selection rule picks C6 (Qwen3-32B, thinking on).** The committed rule is share ≥ 0.20. C6 is the only configuration that clears it: 17/50 correct survivors.
  - The survivors are unit-weight Dijkstra (6), Bellman-Ford/SPFA run on the grid (7), random-priority frontier search (2), a random walk with restarts (1) and wavefront propagation (1).
- **Thinking is the switch, and size matters.**
  - The same 32B weights with thinking off reach 0.08.
  - Qwen3-14B reaches 0.14 with thinking on and 0.00 with it off.
  - Qwen3-8B with thinking on reaches 0.00: it writes BFS 11 / DFS 19 with the ban.
  - All non-thinking models are at or near 0.
- **Disobedience mostly re-implements a banned mechanism without naming it.**
  - Among programs that use a banned mechanism, 55-100% contain no alias of any banned algorithm in the code (`name_free_reimpl_code` in `results/screen.json`).
  - Iteration 2's lesson holds across families: a ban is followed by a renamed BFS or DFS.
- **Obeying is expensive for C6.**
  - Mean reasoning grows from 6,864 tokens (baseline) to 9,090 tokens under the ban.
  - 23/50 ban answers hit the 9,728-token cap, against 7/100 at baseline. These count in N as non-survivors (fallback d).
- **The ban costs correctness elsewhere.**
  - Llama's pass rate falls to 0.02 under the ban.
  - C1 (Qwen3-8B thinking on) passes 0.13 under the ban.

### 2. Geometry on Qwen3-32B: the catalogue survivors land OPPOSITE the banned set, not at its edge

The states are S-mean residual-stream states: the block output averaged over the task-spec tokens. They come from 300 forced prompts (10 algorithms x 10 templates x 3 aliases), read from `unsloth/Qwen3-32B-bnb-4bit` (nf4). The decoder is truncated to 48 of 64 blocks, which is exact for every block used.

- **Layer.** Every block at depth 0.30-0.70 (blocks 19-45) classifies the forced algorithm perfectly: grouped 10-fold CV balanced accuracy is 1.00, holding out (template, alias) groups. By the committed ceiling rule, L* = 31 (depth 0.50).
- **Manifold at L* = 31** (`figures/F2_pca_*`, `F3_mds_*`, `F4_isomap_*`; all in activation coordinates).
  - PCA: PC1 32.4% and PC2 12.0% of variance.
  - Classical MDS stress-1: 0.42 on the 300 points and 0.28 on the 10 centroids.
  - Isomap kNN graph components: 8 at k=5, 3 at k=10, 1 at k=15. Because k=10 is disconnected, the committed primary k is 15.
- **Classes at k = 15.**
  - EDGE: bidirectional BFS (g = 10.9) and bidirectional A* (11.6).
  - MIDDLE: IDA* (13.3).
  - OPPOSITE: JPS (15.9) and **unit-weight Dijkstra (21.6, the farthest non-banned algorithm from the banned five)**.
  - Bootstrap over 1,000 resamples of paraphrase groups: unit Dijkstra keeps its class in 100% and is EDGE in 0%; bidirectional BFS and bidirectional A* are EDGE in 97.5% and 93.6%.
  - Split-half Spearman of the 10x10 geodesic matrices: 0.58 at k=5, 0.95 at k=10, 0.98 at k=15.
- **Landing.** C6's correct catalogue survivors are 6/6 unit-weight Dijkstra, so S = 21.59.
  - Uniform null U: p_opp = 0.0001. Baseline-frequency null F: p_opp = 0.0001. Both committed nulls put S in the OPPOSITE tail.
  - Can-weighted null C (correctness-filter confound): p_opp = 0.057.
  - **Exact algorithm-identity permutation null P: p_opp = 0.20.** That is its floor: one landing algorithm cannot reach algorithm-level significance.
  - Committed verdict: **OPPOSITE**. The pre-registered prediction (EDGE) is **not supported**.
  - The attempted-survivor, Euclidean-centroid and standardised-coordinate variants all give OPPOSITE.
- **Robustness: NOT ROBUST.** OPPOSITE holds in 10/15 cells: every block from L*-2 to L*+2 at k=10 and k=15. At k=5, unit Dijkstra is MIDDLE in all 5 blocks, which gives NEITHER. The committed bar is 12/15.
- **Reading.** This is a correlational description of where obedient behaviour lands. Iteration 7 found that in-manifold pushes moved 0/300 programs, so no causal reading is licensed. With one model and one landing algorithm, the honest algorithm-level evidence is p = 0.20.

### 3. Held-out confirmation (commit #4, frozen geometry): CONFIRMED

- **Setup.** Commit #4 froze L* = 31, k = 15, the point set, the geodesic matrices, g, the classes, the null code and the verdict rule before any held-out sample. C6 was then sampled N = 50 times with four unseen ban templates: W4 `'{X} is not allowed here.'`, W5, P6 and P7 (13/13/12/12). The engine and provider pin were the same as in the screen.
- **Survivor share.** 21/50 correct survivors, share 0.42 (Wilson 0.29-0.56).
  - Stricter readings: 0.34 when 'other' survivors whose adjudicated name is a BFS/DFS variant are dropped, and 0.28 when SPFA is dropped as well (`results/executor_review.json`).
  - Pass rate 0.58; banned-mechanism share 0.34; truncation 0.20.
  - By template, P7 `'Solve this task without using {X}.'` gives 8/12 survivors and W4 gives 3/13.
- **Landing.** The catalogue survivors are 9/9 unit-weight Dijkstra, so S = 21.59 on the frozen g.
  - p_opp(U) and p_opp(F) are below 1e-4 (0 of 10,000 draws); p_opp(C) = 0.017; p_opp(P) = 0.20 (floor).
  - The verdict is OPPOSITE, the same as the screen, so the result is **CONFIRMED** under the committed rule.
- **What this adds.** The confirmation replicates the result on new templates. It does not add algorithm-level power, because one landing algorithm still cannot get below p = 0.2 (deviation D4).
- **Figures.** `figures/F7_confirmation_C6.*` places the held-out ban prompts on the frozen axes; `figures/F1_screen_forest.*` is the screen forest plot.

### 4. Quantisation check: the nf4 geometry is not precision-sensitive

Qwen3-8B forced-prompt states were computed at bf16, int8 and nf4. Its own L* is 17, again by the ceiling rule. Against bf16:

| Precision | Spearman of the 10x10 geodesic matrices (k = 10) | Class agreement | State cosine at every block |
|---|---|---|---|
| int8 | 0.954 | 5/5 | ≥ 0.999 |
| nf4 | 0.916 | 5/5 | ≥ 0.997 |

Both are above the 0.8 flag (`results/quant_check.json`, `figures/F8_quant_check.*`). In Qwen3-8B's bf16 geometry, unit Dijkstra is also OPPOSITE the top-five set.

### 5. Other descriptive geometry (no causal reading)

- **Prompt-state placement** (full-dimensional, block 31, `results/geometry_M1.json -> prompt_state_placement`).
  - The task-spec states of the 10 baseline prompts sit nearest the DFS and BFS centroids.
  - The 3 screen ban prompts and the 4 held-out ban prompts move toward IDDFS and greedy best-first: two of the five *named, banned* algorithms. This is priming, as in iteration 2.
  - Unit-weight Dijkstra, the only catalogue algorithm the model actually writes under the ban, is the **farthest** of the 10 centroids from both ban-prompt sets (rank 10/10).
- **M2 per-program states** (`results/geometry_M2.json`, `figures/F5_M2_C6.*`).
  - Programs: 59 C6 programs (all 29 valid ban programs plus a seeded sample of 30 baseline programs), teacher-forced with reasoning capped at 4,096 tokens (D16). States are read at p* (the first class-signature token in the code), p*-1 and the label-independent 16th code token g16, at blocks 29-33.
  - The adjudicated label is decodable at p* (balanced accuracy 0.97) and p*-1 (1.00). Both positions depend on the label, so this is partly by construction.
  - At g16 it is 0.53, against a chance level of 0.25 (4 labels have at least 5 programs: BFS 32, other 12, DFS 8, unit Dijkstra 6).
  - The p* states of the unit-Dijkstra survivors sit nearest the greedy-best-first cloud (geodesic 38-79): they share the heap signature token.
  - The off-catalogue survivors (Bellman-Ford, random walk, random-priority search) sit far from every class cloud (231-394).
- **Is it a circle?** No (`results/circle_check.json`).
  - The 300 forced states carry some H1 persistence above 100 covariance-matched Gaussian clouds (1.59 against a 95th percentile of 1.29).
  - The 10 centroids carry none (0.00 against 1.19).
  - EDGE and OPPOSITE are therefore geodesic-distance classes on a non-circular manifold, not positions on a ring.

### 6. Novelty audit: no correct novel algorithm

- **Candidates.** Every correct program adjudicated 'other' or flagged for a manual read: 27 programs out of 661 correct programs across all arms.
- **Procedure.** Each candidate was shown to two blind judges with its 3 nearest known solutions. Nearness is Zhang-Shasha tree-edit distance on normalised ASTs over a corpus of 1,987 grid/graph-search programs: the iteration-7 known corpus, the dependency dataset rows, and the 15 T1 references.
- **Verdicts.** No judge voted 'novel' for any candidate. 16 are known by both judges, and for the other 11 deepseek-chat-v3.1 says known while kimi-k2 gave no verdict.
- **Claim.** No correct novel algorithm (rule-of-three 95% upper bound 3/661 = 0.45%; `results/novelty_audit.json`). The off-catalogue survivors are known algorithms: Bellman-Ford/SPFA run on the grid, a random walk with restarts, wavefront propagation, and random- or coordinate-ordered frontier searches.

### 7. How robust is "C6 obeys"?

The committed definition counts a correct program as a survivor if its adjudicated mechanism is a non-banned catalogue algorithm or a named known algorithm outside the catalogue.

- **Primary.** 17/50 (0.34) on the screen and 21/50 (0.42) on the confirmation.
- **Strictest reading.** Drop every 'other' survivor whose adjudicated name, or any novelty judge's name for it, mentions BFS, DFS or SPFA. C6 keeps 11/50 (0.22) and 14/50 (0.28), still above the 0.20 bar (`results/executor_review.json`).
- **Catalogue algorithms only.** 6/50 (0.12) and 9/50 (0.18), below the bar.

So "C6 obeys" rests on counting genuinely different known algorithms (mostly grid Bellman-Ford) as obedience. Where those programs land is outside the 10-algorithm manifold, and they are not part of the landing test.

### 8. Re-derivation and audit

`src/rederive.py` uses no project code and no sklearn/scipy (`results/rederive.json`).

- **Headlines.** It recomputes the shares and Wilson bounds, Q, L* (from the saved CV curve), g (its own kNN graph + Floyd-Warshall; max difference 9e-13), S, every p value and the verdict: **0 mismatches**.
- **Placebos.**
  - Shuffling labels within each configuration reproduces Q in only 1% of 200 shuffles.
  - Random survivor labels give directional verdicts in 28/200 shuffles (14%: EDGE 13, OPPOSITE 15). This is near the nominal 10%; with only 6 survivors the tails are coarse.
- **Commitments.** The 4-commit chain verifies, and each commit precedes the first raw row it governs.
- **Second, shorter audit.** `audit_headlines.py` reads the raw labelled rows and states and recomputes the headlines by different code paths: set logic, scipy `binomtest` Wilson intervals, a sklearn kNN graph with networkx Dijkstra, and exact enumeration of the uniform null (`results/audit_headlines.json`).
  - It reproduces every screen count, Q = {C6}, the confirmation share (21/50, 0.29-0.56), g (difference 1.4e-12) and S. The exact uniform p_opp is 6.4e-5 = (1/5)^6.
  - **Placebo, random survivor labels on the real geometry:** the uniform test rejects at 5.0%, which is nominal.
  - **Placebo, shuffled algorithm labels of the 300 points:** the per-program uniform test still rejects in **36%** of shuffles. All six survivors are one algorithm, so the test mostly asks whether that algorithm happens to have the largest g.
  - The per-program nulls (U, F) therefore overstate the evidence. The algorithm-level permutation p = 0.20 is the honest figure for this landing claim (deviation D4).
- **Earlier checks.**
  - T8 synthetic ring: planted EDGE gives EDGE, planted OPPOSITE gives OPPOSITE, and random labels give 11% directional verdicts.
  - Labeller re-validation: 15/15 T1 references get their own class and pass both suites, 71/78 gold rows agree, and both mutants fail.
  - Renderer: byte-identical to iteration 2's TOP5 W1 prompt.
  - Hook checks: `hidden_states[l+1]` equals the block-l hook output, max absolute difference 0, on Qwen3-8B and on Qwen3-32B nf4.
  - CPU-embedding versus all-GPU block outputs: identical (`results/t7_embed_cpu_vs_gpu.json`).

## Cost and time

- **OpenRouter.** USD 1.53 in total (`results/costs.json`), against the artifact cap of 3.0: screen sampling 0.68, labeller/gate/adjudication judges 0.55, novelty judges 0.18, confirmation sampling 0.11, smoke 0.02. The 4 'budget refusals' in the ledger are the mocked-403 unit test.
- **GPU (RTX 2000 Ada).**
  - C1 sampling took about 62 minutes (30 + 30 thinking-on rows at about 95 tok/s).
  - Qwen3-32B nf4 states, M2 and the Qwen3-8B quantisation check took about 25 minutes.
- **Hidden-test sandbox.** 1,600+ programs, CPU only.

## What was run (stage order)

| Stage | Command (`uv run method.py <stage>`) | What it does |
|---|---|---|
| 0 | `stage0` | Hardware record, read-only input copies (`inputs/` + `inputs/SHA256SUMS`), vendored harness + labeller, renderer byte check, labeller re-validation |
| smoke | `smoke`, `smoke2` | Mocked 403 stop test, judge gate (10 identifier-renamed controls), 3 OpenRouter calls per configuration, vLLM forced-close smoke |
| commit #1 | `commit1` | Pre-registration: configurations, prompts, selection rule, labeller/adjudication, geometry/landing/null/robustness rules, prediction EDGE, deviations |
| 2 | `screen_base_local`, `screen_base_or`, `label baseline <ids>` | Baselines: C1 30 (local vLLM), C2-C8 100 each (OpenRouter, pinned providers) |
| commit #2 | `commit2` | Baseline review-class adjudication, B_c per configuration, every rendered ban prompt (sha256) |
| 4-5 | `screen_ban_local`, `screen_ban_or`, `adjudicate ban <ids>` | Ban arms (W1/W2/W3), labelling, adjudication (gated judges + executor manual reads in `data/manual_reads.jsonl`) |
| 6 + commit #3 | `select` | Screen table, committed selection, code hashes |
| 7 | `states`, `geometry`, `m2`, `quantcheck`, `circle` | S-mean states, L*, M1 manifold, reliability, landing, robustness, figures; M2 per-program states; quantisation check; persistence |
| commit #4 + 8 | `confirm` | Frozen geometry, then N = 50 held-out templates W4/W5/P6/P7 on C6 |
| 9 | `novelty`, `figures`, `rederive`, `outputs` | Novelty audit, F1/F7, independent re-derivation, `method_out.json` |
| checks | `t8`, `t7`, `checks`, `screen_table`, `refig` | Synthetic geometry test, CPU-embedding identity, consistency signals, screen sensitivity fields, figure re-render + prompt-state placement |

`run_after_screen.sh` and `run_resume_states.sh` chain stages 6-8 unattended (PID-managed).

## Layout

| Path | What it is |
|---|---|
| `method.py` | Orchestrator (one sub-command per stage) |
| `src/common.py` | Frozen protocol: spec, catalogue, alias table, templates, configurations, selection rule, hash-chained commits, Wilson/Newcombe, cost ledger |
| `src/prompts_tp.py` | Prompt renderer (byte-identical to iteration 2's TOP5 W1 prompt) |
| `src/sample_or.py`, `src/sample_vllm.py` | OpenRouter sampler (pinned providers, budget stop) and local vLLM client (two-phase thinking budget) |
| `src/label_tp.py`, `src/judge_tp.py`, `src/adjudicate.py` | Labelling (sandboxed hidden tests + exp9 runtime/AST rules), gated judges, adjudication |
| `src/screen.py` | B_c, screen metrics, selection |
| `src/states.py`, `src/geometry.py`, `src/landing.py` | States (truncated decoder, CPU embedding table), manifold geometry, landing nulls |
| `src/figures.py`, `src/novelty.py`, `src/outputs.py`, `src/rederive.py` | Figures F1-F8, novelty audit, outputs, independent re-derivation |
| `src/stages.py` | Stage implementations |
| `predictions/commit{1,2,3,4}.json`, `commitments.log` | Pre-registrations and their sha256 hash chain |
| `data/raw_<cfg>_<arm>.jsonl`, `data/labelled_<cfg>_<arm>.jsonl` | Raw generations (prompt, content, reasoning, provider, usage, cost) and labelled rows |
| `data/samples.jsonl` | Every screen row in one file (the direction's row schema plus engine fields) |
| `data/manual_reads.jsonl` | Executor manual reads of three-way judge splits (reasons logged) |
| `results/` | Every analysis JSON (`screen`, `selection`, `geometry_M1`, `geometry_M2`, `landing`, `landing_robustness`, `confirmation`, `quant_check`, `circle_check`, `novelty_audit`, `positioning`, `labeller_validation`, `judge_gate`, `costs`, `timing.jsonl`, `deviations`, `rederive`, ...) |
| `figures/` | F1 forest plot; F2 PCA, F3 MDS, F4 Isomap (k5/k10/k15), F5 M2, F6 landing nulls, F7 confirmation, F8 quantisation check (PNG + PDF) |
| `cache/states/` | Activation states (`smean_*.npz`, `m2_*.npz`, `geo_*.npz`). They stay on the run's volume; files of 100 MB or more are not in the published repository |
| `inputs/` | Read-only copies of prior-iteration inputs with `SHA256SUMS` |
| `vendor/exp9`, `vendor/exp2` | Executable copies of the iteration-2 harness + 10-class labeller and the iteration-1 secondary test suite |
| `method_out.json` (+ `full_`/`mini_`/`preview_`) | Final output (exp_gen_sol_out schema): datasets `tp_screen`, `tp_geometry`, `tp_confirmation` |

## How to run

The complete, as-run procedure (hardware, versions, seeds, the exact command order including the failed-and-fixed steps, runtimes and expected numbers) is in `reproducibility.md`.

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
export OPENROUTER_BASE_URL=... OPENROUTER_API_KEY=...
uv run method.py stage0 && uv run method.py smoke && uv run method.py commit1
# local C1 needs a vLLM server: VLLM_TEST_FORCE_FP8_MARLIN=1 .venv/bin/vllm serve Qwen/Qwen3-8B-FP8 --revision 220b46e \
#   --max-model-len 10240 --gpu-memory-utilization 0.92 --enforce-eager --port 8044 --seed 0 --max-num-seqs 32 --served-model-name qwen3-8b-fp8
uv run method.py screen_base_local & uv run method.py screen_base_or; uv run method.py label baseline C1,C2,C3,C4,C5,C6,C7,C8
uv run method.py commit2
uv run method.py screen_ban_local & uv run method.py screen_ban_or; uv run method.py adjudicate ban
bash run_after_screen.sh            # select (commit #3), states, geometry, confirm (commit #4), m2, quantcheck, circle
uv run method.py novelty && uv run method.py figures && uv run method.py rederive && uv run method.py outputs
```

`uv run method.py outputs` alone rebuilds `method_out.json` from the saved results.

## Deviations

All deviations are in `results/deviations.json` and in `method_out.json -> metadata.deviations`. The main ones:

- **D8 hardware.** RTX 2000 Ada 16 GB instead of the planned RTX A4500 20 GB, and no C compiler (vLLM runs eager).
- **D9 Llama.** C2 Llama-3.1-8B is sampled through OpenRouter (CoreWeave bf16) instead of local bf16 vLLM, because 16.1 GB of weights do not fit the card.
- **D10 thinking off.** DeepInfra ignores `reasoning: {enabled: false}` for Qwen3, so `' /no_think'` is appended for C3 and C5.
- **D11 gemma substitute.** The gemma-3-12b-it endpoints timed out (504 after 300 s), so the same-family gemma-3-27b-it (DeepInfra fp8) replaced it before commit #1.
- **D12 judges.** gemini-2.5-flash-lite failed its judge gate (7/10). The adjudication pair is deepseek-chat-v3.1 (9/10) + kimi-k2 (10/10), and the third judge is mistral-medium-3.1 (9/10).
- **D13 seeds.** OpenRouter seed = slot + 1, because Cloudflare rejects 0.
- **D14 hidden suite.** The primary hidden suite has 48 cases (the plan text said 45).
- **D15 C1 ban size.** C1 measured 57 s per row, so its N_ban was cut to the committed floor of 30.
- **D16 M2 cap.** C6's M2 caps reasoning at 4,096 tokens and uses all ban programs plus a seeded sample of 30 baseline programs.
- **Planned D1-D7.** Provider heterogeneity, FP8 C1, quantised geometry, algorithm-level null, correctness filter, adjudication of gate-failed classes, and thinking budgets.

## Restoring removed files

| Removed path | Restore with |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r requirements.lock.txt` (or `bash restore.sh`, which also re-fetches the model weights) |
| `cache/states/smean_*.npz` (kept on the run volume; files of 100 MB or more are not in the repository) | `.venv/bin/python method.py states && .venv/bin/python method.py quantcheck` |
| `src/__pycache__/`, `vendor/exp9/*/__pycache__/` | regenerated automatically on import (`uv run python -m compileall src vendor`) |

The model weights live in the run's shared Hugging Face cache, not in this directory. To re-fetch them:

```bash
hf download Qwen/Qwen3-8B-FP8 --revision 220b46e3b2180893580a4454f21f22d3ebb187d3
hf download unsloth/Qwen3-32B-bnb-4bit --revision 7f721e74a6a8cc9ee352f7e49303a2c1705f9083
hf download Qwen/Qwen3-8B
```
