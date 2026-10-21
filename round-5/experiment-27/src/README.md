# Plan noise against plan-first prompting (iteration 5)

This artifact studies Qwen3-8B (pinned revision `b968826d…`) writing Python solutions to algorithm tasks. The model
nearly always picks one default algorithm per task: a full sort for the k-th smallest element, a hash map for
two-sum, Dijkstra for weighted shortest paths. The artifact answers two questions.

**F — the literal cell.** Take the shortest-path task T2 with thinking ON, top-k 10 and the same token seed. Does
moving the temperature over {0.3, 0.7, 1.0, 1.3} ever change the algorithm?

- The cell runs on vLLM 0.11 with the official FP8 checkpoint and exp21's two-pass thinking runner.
- It uses exp21's 20 seeds, so it pairs slot for slot with exp21's top-p-1 run.
- A repeat at T 0.7 measures the run-to-run noise floor.

**C — plan noise against plan-first prompting.** Per-sample plan noise (PN) is an isotropic random direction
added at the task-specification positions of decoder blocks 12–23. It is applied during the prompt prefill only,
on the ban-free unit, at α ∈ {1, 2}. Is PN still a competitive practical knob for buying *correct* algorithmic
diversity? It is compared against:

- **The text-level plan samplers**, all frame-matched: the twin's neutral sentence comes first, then the sampler
  instruction.
  - **IFG**: the intent is sampled hot, the code cool. Two settings: the direction's (1.3, 0.7) and the paper's
    tuned (0.73, 0.60).
  - **PlanSearch-lite**: 5 observations, then a random pair of them, then a plan, then code. T 0.9 / top-p 0.95.
  - **Enumerate-and-pick (EAP)**: the model lists up to 8 algorithms and an external RNG picks one.
  - **Base intent (BINT)**: Qwen3-8B-Base writes the intent and the instruct model writes the code.
- **Departure-matched decoding (DMD)**: a temperature on generated tokens 1–32. It is bisected so that its mean
  per-token KL from the twin equals PN's own, measured on calibration-only prefixes.

Shared machinery:

- **Engine and coupling.** Every knob arm runs in one HF bf16 engine with exact inverse-CDF common random numbers:
  all arms of a slot share the code-stage uniform stream.
- **Labels.** Every program is labelled by the frozen, gated mechanism labellers (runtime trace + AST, with a blind
  judge only on disagreement).
- **Pricing.** Each knob is priced on a full-simplex randomisation hull:
  - **H5**: the largest correct-only Hill-1 (rarefied at depth 25) reachable at a cost of at most 5 pass points.
  - **P15 / P20**: the cheapest cost that reaches Hill 1.5 / 2.0.
  - **Uncertainty**: slot bootstraps that re-select the best mixture inside every replicate.
- **Committed rule.** SUPPORTED if H5(PN) ≥ the best text sampler's H5 on ≥ 3 of the 5 decisive tasks (T03,
  T10, T2, T05, T1); otherwise DISCONFIRMED.

## Results

**Bottom line.**

- **F — the literal cell never changes the algorithm.**
  - 0 of 20 seeds change their final-code algorithm across T ∈ {0.3, 0.7, 1.0, 1.3}. The Clopper-Pearson one-sided
    95% upper bound is 0.14, so the committed prediction C_T ≤ 1 holds.
  - All 100 traces completed. Every final program is heap-based Dijkstra, and every trace names Dijkstra first.
  - Temperature changes the tokens but not the idea. The T 0.7 repeat is byte-identical on only 4 of 20 traces. The
    traces share a median of only 34 tokens with exp21's same-seed top-p-1 traces, yet the labels agree on all 100
    pairs.
- **C — DISCONFIRMED under the committed rule.** Per-sample plan noise (ban-free unit, α ≤ 2) matches or beats the
  best text-level plan sampler on only 1 of the 5 decisive tasks. That task is T03, with H5 1.98 against 1.83 for
  enumerate-and-pick, and P(PN ≥ best) = 0.58, so it is flagged UNRESOLVED.
  - On T10, T2 and T05, the **base-written intent** (Qwen3-8B-Base writes the intent sentence, the instruct model
    writes the code) beats PN: 2.53 / 1.45 / 1.61 against 1.09 / 1.18 / 1.17.
  - On T1 nothing moves much (PN 1.06, EAP 1.08; UNRESOLVED).
  - The mean margin D̄ = −0.40, 95% CI [−0.70, −0.24]. Only 1.8% of 2,000 bootstrap replicates reach the 3-win
    threshold.
  - Every sensitivity gives the same verdict except one. With the left-padded multi-stage samplers dropped (BINT,
    PlanSearch-lite, EAP), the only text sampler left is IFG, and PN beats it on 4 of 5 tasks. The disconfirmation
    therefore rests on the base-intent and enumerate-and-pick samplers.
  - IFG was weak. Its cooler code temperature (0.7) collapses T1's pass rate to 0.12: 50/50 BFS programs, most
    sharing one buggy special case.
- **PN vs departure-matched decoding.** DMD applies a temperature to tokens 1–32, chosen so that its KL from the twin
  equals PN's.
  - At α 2, PN moves the algorithm and DMD does not. Over D5, 19 slots are correct-off-default under PN only and 3
    under DMD only (exact p = 0.0009; T03 alone 13/0, p = 0.0002).
  - At α 1 there is no difference (4 vs 3). DMD's H5 is at most 1.25 on every decisive task.
  - So PN's effect is not its token-level departure. As a practical knob, though, PN loses to two text samplers.
- **The other knobs.**
  - Enumerate-and-pick buys the most raw diversity: Hill 2.9–4.7 per cell on D5. It pays 16–62 pass points for it,
    and 40% of its rows are invalid on T1.
  - Temperature 1.3 and top-k 10 buy none (H5 ≤ 1.09).
  - PN plain vs PN twin shows no significant paired difference on any task.
- **Engine and audits.**
  - The engine check against exp19's FP8 rows is PRECISION-SENSITIVE: twin cells agree per slot at 0.98–1.00, pushed
    cells at 0.74–0.86. No iteration-4 row is reused.
  - Novelty audit: 0 novel algorithms among 12 correct 'other' programs (10 labeller misses, 1 degenerate,
    1 unresolved).
  - The style re-gate flags only T14 (non-decisive).
  - OpenRouter spend: USD 0.12.

**Independent re-derivation** (`audit/rederive.py`, `results/rederive.json`; pandas plus a direct-simulation hull,
sharing no code with the analysis):

- Exact matches: the literal-cell C_T and noise floor; all 10 PN-vs-DMD McNemar counts and p-values; the Claim-C
  verdict.
- The independent hull's H5 values are within 0.08 of the committed hull's. Its win count is 2 rather than 1, a
  near-tie on T1 under Monte-Carlo noise, and still DISCONFIRMED.
- Placebos:
  - Relabelling PN rows as TWIN gives D_t ≤ 0 on all five tasks.
  - Shuffling arm labels within tasks gives win counts centred at 1.6, with ≥ 3 wins in 3 of 20 shuffles. The
    5-task count rule on its own is only weakly selective, which is why the bootstrap win probabilities are
    reported beside it.
- The hash chain has 0 breaks, and no committed file has changed since its last commit.

### Claim F — the literal cell (T2, thinking on, top-k 10, same seed, T ∈ {0.3, 0.7, 1.0, 1.3})

- **C_T = 0 of 20 seeds** change their final-code algorithm across temperature (Clopper-Pearson one-sided 95% upper bound 0.14); the committed prediction C_T ≤ 1 is met.
- First approach named in the thinking: 0 of 20 seeds change.

| T | completed | final labels (completed) | first approach | median think tokens | Dijkstra style |
|---|---|---|---|---|---|
| LIT_T0.3 | 20/20 | {'dijkstra': 20} | {'dijkstra': 20} | 3754.50 | {'heap': 20} |
| LIT_T0.7 | 20/20 | {'dijkstra': 20} | {'dijkstra': 20} | 3962.00 | {'heap': 20} |
| LIT_T1.0 | 20/20 | {'dijkstra': 20} | {'dijkstra': 20} | 3576.00 | {'heap': 20} |
| LIT_T1.3 | 20/20 | {'dijkstra': 20} | {'dijkstra': 20} | 4149.00 | {'heap': 20} |
| LIT_REP_T0.7 | 20/20 | {'dijkstra': 20} | {'dijkstra': 20} | 3500.00 | {'heap': 20} |

- Noise floor (T 0.7 vs its repeat, same seed): byte-identical thinking 4/20, label agreement 1.00, median common prefix 309.50 tokens.
- Paired with exp21's top-p-1 traces at the same (seed, T): label agreement 1.00 on 100 pairs; median common token prefix 34.00 tokens (top-k 10 vs top-k 0 diverge early, yet the algorithm never changes).
- Lexicon audit: judge agreement 1.00 on 19 traces.

### Claim C — plan noise vs text-level plan samplers: **DISCONFIRMED** (PN wins 1 of 5 decisive tasks; threshold 3)

| Task | H5 PN | H5 IFG | H5 PSL-lite | H5 EAP | H5 BINT | best text | PN wins | P(PN ≥ best) | flag | H5 DMD |
|---|---|---|---|---|---|---|---|---|---|---|
| T03 | 1.98 | 1.19 | 1.09 | 1.83 | 1.73 | EAP | yes | 0.58 | UNRESOLVED | 1.10 |
| T10 | 1.09 | 1.96 | 1.50 | 1.88 | 2.53 | BINT | no | 0.00 |  | 1.25 |
| T2 | 1.18 | 1.00 | 1.07 | 1.24 | 1.45 | BINT | no | 0.06 |  | 1.09 |
| T05 | 1.17 | 1.00 | 1.00 | 1.27 | 1.61 | BINT | no | 0.01 |  | 1.00 |
| T1 | 1.06 | 1.00 | 1.00 | 1.08 | 1.04 | EAP | no | 0.38 | UNRESOLVED | 1.00 |

D̄ = mean(H5_PN − best_text) = -0.40, 95% CI ['-0.70', '-0.24']; replicate win-count distribution {'1': 983, '2': 486, '0': 495, '3': 35, '4': 1} (2000 replicates).

| Sensitivity | verdict | wins | D̄ |
|---|---|---|---|
| IFG_hot_only | DISCONFIRMED | 1/5 | -0.40 |
| PN_plus | DISCONFIRMED | 2/5 | -0.40 |
| edge_restricted_hull | DISCONFIRMED | 1/5 | -0.40 |
| leftpad_arms_dropped | SUPPORTED | 4/5 | 0.07 |
| style_regate_flagged_excluded | DISCONFIRMED | 1/5 | -0.40 |
| novelty_audit_relabelled | DISCONFIRMED | 1/5 | -0.40 |

### PN vs departure-matched decoding (DMD), correct off-default share of N

| Task | α | T_dmd | K_PN | f_on | PN | DMD | TWIN | McNemar PN vs DMD (PN-only/DMD-only, p) |
|---|---|---|---|---|---|---|---|---|
| T03 | 1 | 1.46 | 0.0179 | 0.0200 | 0.08 | 0.02 | 0.02 | 3/0, p=0.25 |
| T03 | 2 | 1.64 | 0.0774 | 0.0707 | 0.28 | 0.02 | 0.02 | 13/0, p=0.000244 |
| T10 | 1 | 1.84 | 0.0096 | 0.0110 | 0.02 | 0.04 | 0.00 | 1/2, p=1 |
| T10 | 2 | 2.22 | 0.0333 | 0.0370 | 0.02 | 0.06 | 0.00 | 1/3, p=0.625 |
| T2 | 1 | 2.01 | 0.0254 | 0.0244 | 0.00 | 0.02 | 0.00 | 0/1, p=1 |
| T2 | 2 | 2.66 | 0.1113 | 0.1230 | 0.04 | 0.00 | 0.00 | 2/0, p=0.5 |
| T05 | 1 | 1.52 | 0.0036 | 0.0039 | 0.00 | 0.00 | 0.00 | 0/0, p=1 |
| T05 | 2 | 1.81 | 0.0100 | 0.0104 | 0.04 | 0.00 | 0.00 | 2/0, p=0.5 |
| T1 | 1 | 2.15 | 0.0505 | 0.0442 | 0.00 | 0.00 | 0.00 | 0/0, p=1 |
| T1 | 2 | 2.47 | 0.1554 | 0.1246 | 0.02 | 0.00 | 0.00 | 1/0, p=1 |

Pooled exact test over D5: {'1': {'PN_only': 4, 'DMD_only': 3, 'p_exact': 1.0}, '2': {'PN_only': 19, 'DMD_only': 3, 'p_exact': 0.0008554458618164062}}

### PN plain vs PN twin (same direction, same stream)

| Task | PN plain-only / PN twin-only (p) | pass plain | pass twin | Hill plain | Hill twin |
|---|---|---|---|---|---|
| T03 | 0/3 (p=0.25) | 1.00 | 0.98 | 1.09 | 1.33 |
| T10 | 0/1 (p=1) | 1.00 | 1.00 | 1.00 | 1.09 |
| T2 | 0/0 (p=1) | 1.00 | 1.00 | 1.00 | 1.00 |
| T05 | 0/0 (p=1) | 1.00 | 1.00 | 1.00 | 1.00 |
| T1 | 0/0 (p=1) | 0.86 | 0.80 | 1.00 | 1.00 |
| T04 | 0/0 (p=1) | 1.00 | 1.00 | 1.00 | 1.00 |
| T06 | 0/0 (p=1) | 1.00 | 1.00 | 1.00 | 1.00 |
| T08 | 0/0 (p=1) | 0.97 | 1.00 | 1.00 | 1.00 |
| T11 | 0/0 (p=1) | 1.00 | 1.00 | 1.00 | 1.00 |
| T13 | 0/0 (p=1) | 1.00 | 1.00 | 1.00 | 1.00 |
| T14 | 0/0 (p=1) | 0.73 | 0.80 | 1.00 | 1.00 |
| R1 | 0/0 (p=1) | 0.90 | 0.87 | 1.00 | 1.00 |
| R2 | 0/0 (p=1) | 0.80 | 0.87 | 1.00 | 1.00 |
| R3 | 0/0 (p=1) | 1.00 | 1.00 | 1.00 | 1.00 |
| R6 | 0/1 (p=1) | 0.90 | 0.87 | 1.00 | 1.17 |

### Engine check (bf16 here vs exp19's FP8 W8A8): **PRECISION-SENSITIVE**

| Cell | byte-identical | per-slot label agreement | JSD | null p95 |
|---|---|---|---|---|
| T03|NEUTRAL | 45/50 | 1.00 | 0.00 | 0.00 |
| T03|RAND9002_a1.0 | 32/50 | 0.74 | 0.03 | 0.15 |
| T2|NEUTRAL | 35/50 | 0.98 | 0.01 | 0.00 |
| T2|RAND9004_a1.0 | 10/50 | 0.86 | 0.01 | 0.01 |
| T03|T1.3 | 0/10 | 1.00 | 0.00 | – |
| T03|TOPK10 | 0/10 | 1.00 | 0.00 | – |
| T2|T1.3 | 0/10 | 0.90 | 0.05 | – |
| T2|TOPK10 | 0/10 | 0.90 | 0.05 | – |

- Novelty audit: 12 unique correct 'other' programs, classes {'LABELLER MISS': 10, 'null': 1, 'DEGENERATE': 1}; novel = 0.
- Style re-gate: 250 programs; flagged tasks ['T14']; per-task agreement {'T03': '1.00', 'T2': '1.00', 'T10': '1.00', 'T05': '1.00', 'T1': '1.00', 'T04': '1.00', 'T06': '1.00', 'T08': '0.90', 'T11': '0.90', 'T13': '1.00', 'T14': '0.80', 'R1': '1.00', 'R2': '1.00', 'R3': '1.00', 'R6': '0.90'}.
- GPU: 8576 HF rows in 1.88 GPU-hours of batch time + literal cell 15.11 min on vLLM; OpenRouter spend USD 0.12.

Post hoc (A4): with the iteration-1 base label names harmonised, the landing mass outside base support is 0.11 for T1|EAP (bibfs) and 0 for every T2 landing (`results/landings_harmonised.json`); the committed unharmonised values are inflated by label-name mismatches.


## What was run (and what changed from the plan)

| Stage | What | Where |
|---|---|---|
| S0 | input copies + sha256 (`inputs/SHA256SUMS`), bench files vs `commitment.json`, screen sha256, seed registry (0 collisions), labeller re-check (all references pass, gold within 0.02 of every gate), precision rule | `src/s0.py`, `predictions/precision_rule.json`, `results/input_hashes.json`, `results/labeller_recheck.json`, `results/seed_collisions.json` |
| S0.6 | 430 stage-1 prompts; spec token ids identical across kinds; forced `Intent:` ids stable; W-template alias audit clean | `src/prompts5.py`, `prompts/prompts.jsonl`, `results/prompt_report.json` |
| commits | `commit0F` (literal cell) → `commit0C` (Claim C) → `commit1` (DMD temperatures, pilot) → `amend1`, `amend3` | `commitments.log`, `predictions/commit*.json`, `src/prereg5.py` |
| S2 | literal cell: 100 traces (20 seeds × 4 T + repeat), 100/100 completed | `src/vllm_literal.py`, `data/literal_raw.jsonl`, `results/literal_cell.json` |
| S3 | 550 base intents (Qwen3-8B-Base, T 1.3, ≤ 2 resamples) | `data/base_intents.jsonl` |
| tests | GPU U1–U5, U7 all pass; CPU tests all pass (incl. exp19's T03 PN H5 re-derived 2.73 vs 2.72) | `results/unit_tests_gpu.json`, `results/tests_cpu.json`, `results/u6_vllm.json` |
| S4 | DMD calibration on all 15 tasks × α ∈ {1, 2}; format pilot (v1 failed → one wording revision → pass) | `predictions/dmd_temperatures.json`, `predictions/format_pilot*.json` |
| S1 | engine check vs exp19's FP8 rows (run after commit0C) | `data/engine_check_*.jsonl`, `results/engine_check.json` |
| S5 | knob queue: stage 10 → stage 100 → committed drop order → full queue; then the dropped cells were restored in reverse drop order until the deadline (amendment A2) | `src/gen5.py`, `src/gen5_restore.py`, `data/samples_raw.jsonl`, `results/timing_*.json` |
| S6/S7 | labels; style re-gate; novelty audit; lexicon audit | `src/label5.py`, `src/audit5.py`, `data/labels.jsonl`, `audit/` |
| S8 | Claim C, PN vs DMD, PN plain vs twin, unit ratio, landings, knob table | `src/analysis_c.py`, `results/*.json` |
| S9 | figures, method_out.json, independent re-derivation + placebos | `src/figures5.py`, `src/outputs5.py`, `audit/rederive.py` |

**Deviations.** Every deviation is in `results/deviations.jsonl`, with its reason and its direction of effect. The
important ones:

- **D-bf16**: the 24 GB RTX 4090 selects the bf16 HF engine. Iteration-4 FP8 rows are therefore not reused slot for
  slot. T1.3, TOPK10 and NOVELTY are rerun on D5, and SEMSEED on T1 and T2.
- **D-commit**: commit #0 was split by claim.
- **D-pilot**: the plan's one allowed wording revision. In v1 the model obeyed the spec's code-block line and wrote
  code at once, so stage 1 now states the step structure.
- **D-parser**: the parser accepts the literal `<1>. <Name>:` form.
- **D-PN5**: one PN direction per slot is shared by PN_a1, PN_a2 and PNPLAIN_a1.
- **D-drop**: the committed drop order fired after stage 100.
- **A1**: cells with N < 30 (D5) or < 15 (ND10) are excluded from hulls. This was decided after a dry run, and it
  favours PN on T03; the unamended result is reported.
- **A2**: the dropped cells were restored after the queue finished early.
- **A3**: bootstrap caching. This is computation only.

Departures inherited from the plan:

- PlanSearch is "lite": a single path, with no second-order observations, flip or pseudocode.
- The IFG intent is one zero-shot sentence.
- DMD matches the KL against the T = 1 twin, not departure from greedy decoding.
- There are 5 decisive tasks, so Claim C is a count rule.
- N is 50 on decisive cells and 20–30 on non-decisive cells.
- There is one model family, and the tasks are memorised LeetCode-style tasks.

## Layout

| Path | What it holds |
|---|---|
| `method.py` | orchestrator: `.venv/bin/python method.py <stage>` (s0, prompts, commit0F, literal, label_f, gpu, commit0C, commit1, label, audit, analyze, figures, outputs, rederive) |
| `src/cfg.py` | exp19's constants and utilities, verbatim (`stable_seed`, W1–W5 templates, blocks, paths) |
| `src/cfg5.py` | iteration-5 constants: D5/ND10, the arm table, frozen instructions (v1 and v2), drop order, DMD and analysis constants |
| `src/engine_v4.py`, `src/hooks.py`, `src/sampling_v4.py`, `src/prompts_v4.py`, `src/label_worker_v4.py`, `src/commit.py` | exp19 code, unchanged (prefill with block-output edits, inverse-CDF CRN sampler, displacement-targeted edits, frozen labellers, hash chain) |
| `src/engine5.py` | one decoder for every arm: per-row prefilled KV (left-padded when lengths differ), temperature schedules (DMD), top-k/top-p, the IFG intent-phase stream switch, fence stop; calibration decode and teacher forcing; KL helpers |
| `src/prompts5.py` | stage-1 prompts + multi-turn rendering with verbatim assertions |
| `src/parsers.py` | intent / observation / enumeration parsers, pair and pick rules |
| `src/gen5.py` | GPU stages: base intents, unit tests, DMD calibration + pilot, engine check, knob queue with the drop order |
| `src/gen5_restore.py`, `src/after_queue.sh` | post-queue restoration of dropped cells (amendment A2) |
| `src/vllm_literal.py`, `src/lexicon.py` | the literal cell on vLLM; the first-approach lexicon |
| `src/hull_exp20.py`, `src/hull_full.py` | exp20's CRN hull sampler (verbatim) and the full-simplex extension |
| `src/analysis_f.py`, `src/analysis_c.py`, `src/analysis_ec.py` | committed analyses: literal cell, Claim C (+ all S8 analyses), engine check |
| `src/audit5.py` | lexicon audit, style re-gate, novelty audit (OpenRouter, cached, cost-capped) |
| `src/tests_cpu.py`, `src/figures5.py`, `src/outputs5.py`, `src/report5.py` | CPU tests, figures, method_out.json, the summary tables |
| `audit/rederive.py` | independent re-derivation (pandas + direct-simulation hull) with placebos |
| `src/pilot_debug.py`, `src/posthoc5.py`, `src/finalize.sh` | format-pilot diagnosis (raw stage-A texts), post-hoc label-vocabulary harmonisation (A4), the post-generation chain |
| `data/` | raw rows (`samples_raw.jsonl`, `literal_raw.jsonl`, `stages.jsonl`, `base_intents.jsonl`, `engine_check_raw.jsonl`), labels, realised displacements |
| `results/` | every analysis output (see `results/summary.md`) |
| `predictions/` | pre-registered files: precision rule, commit0F/0C/1, DMD temperatures, format pilots, batch probe, model revisions |
| `prompts/prompts.jsonl` | the 430 rendered stage-1 prompts with token ids and sha256 |
| `inputs/` | read-only copies of earlier artifacts' inputs + `SHA256SUMS` |
| `figures/` | F1 literal cell, F2 hull frontiers, F3 compositions, F4 PN vs DMD, F5 PN plain vs twin, F6 landings (PDF + PNG) |
| `method_out.json` (+ `full_`/`mini_`/`preview_`) | exp_gen_sol_out: datasets `literal_cell`, `knob_slots`, `engine_check`, `dmd_calibration`; everything else in `metadata` |
| `reproducibility.md` | exact commands in the order they were run, hardware, versions, seeds, runtimes |

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
uv venv .venv_vllm --python=3.12 && uv pip install --python .venv_vllm/bin/python -r env/requirements_vllm.txt
.venv/bin/python src/download_models.py          # Qwen3-8B, Qwen3-8B-FP8, Qwen3-8B-Base at pinned revisions
.venv/bin/python method.py s0,prompts,commit0F,literal,label_f
.venv/bin/python method.py gpu &                 # blocks on commit0C / commit1
.venv/bin/python method.py label &
.venv/bin/python method.py commit0C,commit1      # once results/calib_done.flag exists
.venv/bin/python method.py audit,analyze,figures,outputs,rederive
```

Requirements:

- One GPU with at least 24 GB. A 16 GB Ada card switches the HF engine to FP8 W8A8 by the precision rule.
- `HF_HOME` / `HF_HUB_CACHE` naming the model cache.
- `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY` for the judges. Judge answers are cached in `data/judge_cache*.jsonl`
  and `audit/llm_cache.jsonl`.

The trained or generated bulk all stays in this folder. Nothing here is a large binary: the biggest files are
JSONL rows.

## Restoring removed files

The paths below are deleted after the round (`.aii/manifest.yaml`); everything else (data, results, predictions,
audit, inputs, figures) is text or small and stays in the folder.

| Removed path | Restore with |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` |
| `.venv_vllm/` | `uv venv .venv_vllm --python=3.12 && uv pip install --python .venv_vllm/bin/python -r env/requirements_vllm.txt` |
| `audit/__pycache__/`, `src/__pycache__/`, `src/analysis/__pycache__/`, `inputs/exp8/suite/__pycache__/`, `inputs/exp8/suite/labeller/__pycache__/`, `inputs/exp8/suite/tasks/__pycache__/`, `inputs/exp11/bench/__pycache__/`, `inputs/exp11/bench/common/__pycache__/` | regenerated automatically by Python on the next run of any script (or `python -m compileall src audit inputs`) |
| model weights (shared HF cache, never in this folder) | `.venv/bin/python src/download_models.py` (Qwen/Qwen3-8B@b968826d…, Qwen/Qwen3-8B-FP8@220b46e3…, Qwen/Qwen3-8B-Base@49e3418f…) |
