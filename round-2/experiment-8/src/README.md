# Where an algorithm ban takes effect

A causal route test (C2) and a compliance-at-R test (C5) for prompt-level algorithm bans in **Qwen/Qwen3-8B**
(bf16, thinking off) on two path-search coding tasks:

- **T1** grid path (`solve(grid, start, goal)`), ban **BFS** ("breadth-first search (BFS)");
- **T2** weighted shortest path (`solve(n, edges, s, t)`), ban **Dijkstra** ("Dijkstra's algorithm").

Task text, hidden tests (48 / 45 cases), the 22 references and the mechanism-level labeller are iteration-1's
canonical suite (exp1), copied byte-identically into `suite/` and re-checked here (see `results/labeller_recheck.json`).

## Results

All numbers below come from `results/analysis.json` (pre-registered analysis), `results/supplementary.json`
(descriptive additions), `results/c5.json`, `results/lens.json` and `results/natural_frlp.json`; 95% intervals are
bootstrap (FRLP: templates x programs, 2,000 replicates) or Wilson (shares).

**1. Pre-registered C2 decision: DECIDED BEFORE WRITING, carried by the prompt route, ROBUST (both tasks give
the same branch).** Primary readout = FRLP drop of the banned algorithm.

| | D_X(a) full ban | D_X(c) prompt route | D_X(d) direct route | F_prompt | F_direct | F_spec | F_R |
|---|---|---|---|---|---|---|---|
| T1 ban BFS | -12.25 [-20.9, -6.9] | -10.65 [-12.4, -9.6] | -0.23 [-3.0, 0.8] | 0.87 [0.55, 1.50] | 0.02 [-0.10, 0.18] | 0.86 | 0.00 |
| T2 ban Dijkstra | -5.78 [-7.9, -3.1] | -4.73 [-6.2, -3.1] | 0.22 [-0.3, 0.8] | 0.82 [0.62, 1.20] | -0.04 [-0.25, 0.05] | 0.81 | 0.02 |
| pooled (ratio of sums) | -18.03 | -15.38 | -0.01 | **0.85 [0.61, 1.20]** | **0.00 [-0.08, 0.12]** | | |

Units are nats. The ban information reaches the generated tokens through the task-specification states, not
through R alone (R-only arm e: about 0; task-spec-only arm f: 0.81 to 0.86). The placebo splice of two neutral
nouns moves L_X by 1.2% (T1) and 0.7% (T2) of the ban effect, and the knockout applied to the neutral prompt
costs only -0.21 / -0.28 nats. All four pre-declared sensitivities give the same branch: unweighted mean
log-likelihood (F_prompt 0.70 / 0.82), correct programs only, the generating paraphrase as denominator, and no
ESS weighting. A template jackknife keeps F_prompt between 0.68 and 0.99.

**2. Behaviour qualifies the T1 result: a second, direct component.** Common random numbers, N = 100 per arm:

| banned share | b neutral | d direct | c prompt | a ban | K0 (suppl.) | K1 | K2 | behavioural F_prompt / F_direct |
|---|---|---|---|---|---|---|---|---|
| T1 (BFS) | 1.00 | 0.70 | 0.57 | 0.14 | 0.47 | 0.16 | 0.19 | 0.50 [0.39, 0.62] / 0.35 [0.25, 0.45] |
| T2 (Dijkstra) | 0.99 | 0.95 | 0.13 | 0.11 | 0.06 | 0.11 | 0.11 | 0.98 [0.89, 1.07] / 0.05 [0.01, 0.09] |

In T2 the prompt-route arm reproduces the ban and the direct-route arm is the baseline. In T1, hiding the
condition span from every generated token (supplementary arm K0) brings BFS back to 0.47 [0.38, 0.57]. That is
close to arm c (McNemar p = 0.13), so generated tokens do read the ban directly in T1. The reading is redundant
over time: blocking only the first 16 generated tokens (K1) or only the rest (K2) leaves the ban intact. Matched
pairs are clean: no sample was banned under the ban but not under its neutral twin (a vs b: 0 / 86 and 0 / 88
discordant).

**3. Where the ban acts: the program's first line.** Under the neutral twin, 99% of programs open with
`from collections import deque` (T1) or `import heapq` (T2). Under the T1 ban, 0 of 100 programs open with an
import line, including the 14 BFS programs that survive the ban; they open with `def solve(...)`. The prompt-route
arm c and every knockout also open with an import line 0% of the time, while the direct-route arm d still does
85% of the time (figure 6). Per-token localisation agrees: the FRLP drop sits in the first 16 tokens (T1: 63%
under a, 90% under c, 95% under K0; T2: about 100%). The signature tokens themselves (deque, heapq, ...) carry
little of it (2.4% / 11.6%). The small T1 direct-route drop lies later in the program (6% in the first 16
tokens). The opening-line veto is therefore carried entirely by the prompt states. The algorithm chosen after
`def solve` in T1 also depends on direct reads of the ban. The likelihood readouts are dominated by the opening
fork, which is why they call T1 prompt-route while its behaviour is mixed.

**4. Supplementary natural-proposal readout.** This re-scores, under every arm, the arm-b BFS/Dijkstra programs,
which are exact draws from p(.|b). It gives the same ordering with a larger direct share: pooled F_prompt 0.57
[0.41, 0.85], F_direct 0.16 [0.11, 0.21] (T1 0.58 / 0.18, T2 0.56 / 0.11), and the two routes are
super-additive (D(a) < D(c) + D(d) in both tasks). Neither likelihood readout is a calibrated probability ratio:
importance-weight ESS is about 1-3 of 30 for T1 arm a (8-20 for T2) and 858 of 1,095 FRLP cells are flagged
ESS < 5 (fallback F6), and exp(D_nat(a)) is 3e-7 in T1 against a behavioural ratio of 0.14. These readouts
measure how strongly typical banned-algorithm programs, which start with the import line, are vetoed. They do
not measure the whole program distribution.

**5. Knockouts (FRLP).** A full condition-span knockout restores 5% (T1) and 6% (T2) of the gap (CIs include 0),
consistent with the prompt route. The layer band 12-23 restores 32% [16%, 56%] in T1 and 15% in T2. Band 0-11
restores about 0 in both tasks. Band 24-35 restores -17% (CI includes 0) in T1 and 9% [2%, 16%] in T2. K1 - K2 is undetermined, so no early or late veto can be called.

**6. Lens.** At the planned commitment token (" collections" / " heapq", right after `from` / `import`), the ban
leaves the banned set's rank unchanged, so a veto layer is never reached (0 of 59 for T1, 0 of 60 for T2): the
fork has already happened at the first token. The T1 substitute (DFS) set rises from layer ~28 (59 of 59; tuned
lens median 27). In arm-a substitute programs the banned set is vetoed late (median layer 30 for T1, 36 for T2).
The tuned lens beat the logit lens on held-out KL at all 11 probed layers (e.g. 0.29 vs 10.6 at layer 21).

**7. C5 (compliance at R): PARTIAL.** The test regresses per-wording banned share on the projection of h_R onto
a leave-one-experiment-out shared ban direction (110 wordings, 12 experiment x task cells). The combined
within-cell Spearman rho is -0.41 [-0.69, -0.17], one-sided stratified-permutation p = 0.0003 (Holm over the
two axes: 0.0006). That is negative and significant but not at the -0.5 bar. The observed rho beats 98.5% of
200 random directions (null mean -0.01), and the split-half ceiling is |rho| about 0.77. Exp4's decommitment
axis is NULL (rho = 0.05, p = 0.68). The DFS share among non-banned samples is not decodable beyond the
projection (delta R2 < 0, permutation p = 0.74; T2 not testable). The recomputed h_R matched the stored
iteration-1 caches (cosine >= 0.9994 for 40 exp2 and 60 exp4 prompts).

**8. Checks.** Labeller: 0.965 agreement with the adjudicated gold set (n = 141), 22/22 references. Engine
tests: spliced caches reproduce the full-ban scores bit-exactly; the knockout attention with nothing blocked
equals stock SDPA (max diff 0); attention mass to blocked columns is exactly 0. Sampling: repeated runs are 100%
identical at a fixed batch shape and only 40% when the shape changes, which is why every arm shares shapes.
`audit/rederive.py` re-derives 49 headline numbers from the raw per-token npz files with 0 mismatches: per-task
D, F, I, the knockout restorations and the C5 projections. `audit/headline_audit.py` is a second, separate
pandas/scipy implementation. It recomputes the behaviour shares (all arms including K0), the behavioural route
fractions, the a-vs-b McNemar p, D_X(a, c, d), F_R, F_spec, the placebo value, the pooled F's, the
natural-proposal D and pooled F's, the opening-line shares, the first-16-token shares and the C5 combined rho,
also with 0 mismatches. Each test fails on placebo or shuffled input, as it should:

- McNemar on randomly swapped arm labels rejects 4.0-4.4% of the time.
- The FRLP ban-effect CI includes 0 for the placebo splice and for label-shuffled data.
- C5 rejects 0 of 40 shuffled data sets.

Not independently re-derived: the bootstrap intervals (only the ban-effect interval was re-bootstrapped, with
different code), the lens summaries, survivor-gain cosines, coverage Jaccards, signature-token shares, and the C5
noise ceiling, random-direction null and substitute decodability. OpenRouter spend was USD 0.32.

**9. Context from the declared dependency** (`results/supplementary.json` -> `dependency_context`; all 10 of its
datasets are inventoried there with their use). Only `concreteness_norms` drives the design (the neutral twins).
In `llm_creativity`, other models spread their non-Dijkstra choices for weighted shortest path across
Bellman-Ford/SPFA (37%), bidirectional search (32%) and other algorithms (23%). Qwen3-8B under the Dijkstra ban
lands on Bellman-Ford/SPFA 97% of the time. Opening with an import line is the norm in LLM-written solutions that
name the algorithm (`kodcode_algorithmic`: BFS 94%, n = 17; Dijkstra 100%, n = 40) but not in human library code
(`thealgorithms_python`: 29%, n = 7, and 17%, n = 12). So the opening line the ban suppresses is the model's
stylistic default for these algorithms.

**Limits.** The results cover two modal-ban events in one model (Qwen3-8B). The neutral twins ('man' / 'guy'
plus companion nouns) follow the frozen rule but read oddly. The T1 likelihood estimates rest on very few
effective programs. The pre-registered decision is reported as committed. Sections 2-4 qualify it with
behaviour and supplementary readouts that were not part of the decision rule.

## Design in one paragraph

Each of 5 frozen ban templates (W1-W5) gets a **neutral twin** that prohibits an irrelevant noun in the same frame
("Do not use man, the house and the baby for this task."), padded with companion nouns until the chat-formatted
prompt has exactly the ban prompt's token length and identical token ids from `Task:` onward. Their KV caches can
then be spliced position by position. Arms: **a** full ban; **b** full neutral (baseline); **c PROMPT ROUTE**
(neutral condition-segment cache + ban task-spec/R cache, ban R logits: generated tokens can only learn about the
ban through states that read it); **d DIRECT ROUTE** (ban condition-segment cache + neutral task-spec/R cache:
generated tokens can only read the ban directly). Decomposition arms: **e** R-only, **f** task-spec-only, **pl**
placebo splice of two neutral nouns, condition-span attention knockouts **K0** (all generated queries), **K1**
(generated index < 16), **K2** (>= 16), layer bands **B1/B2/B3** (0-11/12-23/24-35), and **K0b** (K0 on the neutral
prompt: generic-damage control). The primary readout is the **FRLP drop** of the banned algorithm,
`D_X(arm) = L_X(arm) - L_X(b)`, where `L_j(c) = log mean_m exp(l(p_m|c) - l(p_m|F_j))` over 30 self-written,
name-scrubbed programs of algorithm j teacher-forced on each arm's cache, with the 10-paraphrase forced-prompt
mixture as the importance-sampling proposal. Route fractions `F_direct = D(d)/D(a)`, `F_prompt = D(c)/D(a)` and
the interaction `I = D(a) - D(c) - D(d)` get a two-level (templates x programs) crossed bootstrap. The decision
rule was sha256-committed (`results/prereg.json`, `results/prereg_commit.txt`) before any arm was scored or sampled.
Behaviour: 100 samples per arm per task (5 templates x 20) under **common random numbers** (one PCG64 uniform
stream per sample shared by every arm, inverse-CDF sampling in vocabulary order, constant batch shape), giving
banned shares, landing distributions and matched per-sample flips. C5 regresses the per-wording banned share of
~100 iteration-1 modal-ban wordings (exp1-exp5) plus the 10 new template cells on the projection of the residual at
the read position R onto a leave-one-experiment-out shared ban direction (and on exp4's decommitment axis).

## Layout

| path | what |
|---|---|
| `method.py` | entry point; one subcommand per stage (`s0 s1 s2 prereg tests s4 s4label s5 s6 s7 s8 s9`) |
| `cfg.py` | frozen protocol: display names, W1-W5 templates, forced paraphrases, signature vocabularies, thresholds, paths |
| `snapshot.py` | S0: copies the iteration-1 inputs into `inputs/iter1/` (+ `MANIFEST.sha256`), builds `suite/`, labeller re-check |
| `labelling.py` | canonical exp1 labeller wrapper (runtime tracer primary, AST second, blind judge only on disagreement) |
| `build_prompts.py` | S1: ban / mention / length-matched neutral twins, forced prompts, pre-registration commit |
| `gen_programs.py`, `scrub.py` | S2: forced programs (30 per algorithm), labelling, name scrub with test/label re-verification |
| `engine.py` | S3: HF engine; `ko_sdpa` knockout attention, prefill, KV splice, batch-1 teacher forcing, CRN sampler |
| `arms.py` | arm construction (a, b, c, d, e, f, pl, K0-K2, B1-B3, K0b) |
| `behaviour.py` | S4: CRN behaviour sampling + labelling |
| `frlp.py` | S5: FRLP scoring of every arm and the forced-prompt denominators |
| `lens.py` | S6: logit lens and tuned lens at the commitment token |
| `c5.py` | S7: compliance at R across iteration-1 wordings |
| `analysis.py` | S8: every statistic and the frozen decision (its sha256 is in the pre-registration) |
| `outputs.py` | S9: `method_out.json` (exp_gen_sol_out schema) and `figures/` |
| `supplementary.py` | descriptive additions: per-program shift distributions, opening lines, K0 contrasts -> `results/supplementary.json` |
| `natural_frlp.py` | supplementary natural-proposal FRLP (arm-b programs re-scored under every arm) -> `results/natural_frlp.json` |
| `extra_k0_behaviour.py` | supplementary full-knockout K0 behaviour arm (same CRN streams) |
| `tests/run_tests.py` | U0-U9 tests -> `results/tests.json` |
| `audit/rederive.py` | independent re-derivation of the headline numbers from the raw npz/JSONL -> `results/rederive.json` |
| `audit/headline_audit.py` | second independent audit (pandas/scipy) of every quoted number + placebo and shuffle tests -> `results/headline_audit.json` |
| `reproducibility.md`, `restore.sh` | exact reproduction steps (what was actually run); rebuild of the deleted paths |
| `requirements.lock.txt` | exact package versions of the environment used (`uv pip freeze`) |
| `run_gpu_chain.sh` | the GPU chain used for this run (prereg -> tests -> S4 -> S5 / S4 labelling -> S6 -> S7 -> S8) |
| `prompts/frozen_prompts.json` | every prompt with token ids, positions p0/p1/P, neutral nouns and padding forms |
| `data/frlp_programs.jsonl` | the 323 forced programs (original + scrubbed text, score token ids, labels, generating prompt) |
| `data/frlp_scores.jsonl` | summed log-likelihood of every program under every scored cell |
| `data/token_lp/` | per-token log-probs behind every FRLP number (float32 npz, about 6 MB) |
| `data/frlp_cells.jsonl` | per-cell FRLP rows `{task, model, condition, template, algorithm, L, ess, n_programs, half}` |
| `data/samples.jsonl` | every behaviour sample in the shared schema (+ code, tokens, noun) |
| `data/programs_raw.jsonl` | all S2 generations with labels |
| `results/*.json` | analysis (`analysis.json`), C5 (`c5.json`), lens (`lens.json`), tests, prereg, run logs |
| `figures/` | fig1 FRLP drop per arm, fig2 token localisation, fig3 knockout restoration, fig4 lens curves, fig5 C5 |
| `method_out.json` | all examples + every analysis in `metadata` (`full_`, `mini_`, `preview_` variants beside it) |
| `data/natural_frlp_scores.jsonl` | per-program log-likelihoods of the natural-proposal readout |
| `inputs/` | read-only snapshot of the iteration-1 files used (sha256 manifest) and the neutral-noun candidates |

## How to run

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python method.py s0 s1 s2          # snapshot + labeller check, prompts, forced programs (GPU for s2)
.venv/bin/python method.py prereg            # hash-commit the decision rules before any arm is scored
./run_gpu_chain.sh                           # tests -> s4 -> s5 (+ s4label) -> s6 -> s7 -> s8
.venv/bin/python natural_frlp.py             # supplementary natural-proposal readout (GPU, ~3 min)
.venv/bin/python extra_k0_behaviour.py       # supplementary K0 behaviour arm (GPU, ~4 min) + relabelling
.venv/bin/python method.py s8                # re-run the analysis on the final sample file
.venv/bin/python supplementary.py            # descriptive additions
.venv/bin/python method.py s9                # method_out.json + figures
.venv/bin/python audit/rederive.py           # independent re-derivation (0 mismatches expected)
```

The model is `Qwen/Qwen3-8B` at Hub revision `b968826d9c46dd6066d109eabc6255188de91218`. `BRT_MODEL_PATH` points
to a local copy if you have one. Upstream inputs come from other artifacts and are already snapshotted in
`inputs/`. They are read through one environment variable each (`BRT_DATASET_DIR` for art_j3Rm_lr2nzR6,
`BRT_EXP1_DIR` ... `BRT_EXP5_DIR` for the iteration-1 experiments), and the defaults are the sibling folders of the
published repository. Judge calls go through OpenRouter (`OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY`) and are capped
at USD 0.5. exp1's judge cache is reused, so most labels need no call. `reproducibility.md` lists the exact
commands, hardware, seeds and runtimes.

## Restoring removed files

| removed path | restore with |
|---|---|
| `.venv/` | `./restore.sh` (= `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r requirements.lock.txt`) |
| `work/` (C5 residual cache `c5_hR.npz`) | `./restore.sh --with-c5-cache` (= `.venv/bin/python method.py s7`, GPU) |
| `__pycache__/`, `tests/__pycache__/`, `suite/__pycache__/`, `suite/labeller/__pycache__/`, `suite/tasks/__pycache__/` | Python bytecode, rebuilt automatically on import (or `python -m compileall .`) |

`data/token_lp/` (about 6 MB of compressed per-token scores behind every FRLP number) is small and stays with the
repository. Paths in this README are relative to this folder.
Publishing exclusions: `(^|/)\.venv/`, `(^|/)work/`, `(^|/)__pycache__/`.
