# Do algorithm bans work the same in Llama?

Second-family replication of the iteration-2 ban screen on **meta-llama/Llama-3.1-8B-Instruct** (bf16, default chat
template, `Today Date: 26 Jul 2024`). It uses the frozen SHARED PROTOCOL v2 templates, the canonical exp1 task suite
and labeller, and the dataset artifact's neutral-noun bank re-tokenised under Llama. On two path-search tasks it
measures:

- **FRLP** (forced-ratio latent probability). This is the probability that the model writes each catalogue algorithm
  under a prompt, estimated by importance-weighting name-scrubbed programs the model wrote itself under "Implement X"
  prompts.
- **The C1 share test.** Does a ban's gain profile over the surviving algorithms follow an X-specific pattern or an
  external ladder `u` (nonce ban, matched-norm random edits, novelty instruction)?

Llama is reported on its own, and nothing was tuned to agree with Qwen. Two tasks and one model make **every number
here descriptive**. The FRLP validity gate also **failed**, which by protocol makes the C1 numbers descriptive too.

## Headline results

All numbers below are read from `results/*.json`; the sampled events are in `results/events.json`.

| | T1 grid path (K=6) | T2 weighted shortest path |
|---|---|---|
| Baseline, N=100 (attempted labels) | BFS 77, DFS 20, other 3 (modal share 0.77, Wilson 0.68-0.84): **not collapsed** | Dijkstra 92, BF/SPFA 1, other 7: collapsed |
| Pass rate (hidden tests) | 0.20 | 0.59 |
| Modal ban, N=100 | ban BFS: **DFS 63**, BFS 29, other 6 (avoidance 0.71) | ban Dijkstra: Dijkstra 43, **other 37**, BF/SPFA 18 (avoidance 0.57) |
| Two-step ban (d or s*), N=50 | BFS 21 + DFS 21 banned (avoidance 0.16): fails the event gate | Dijkstra 22 + BF/SPFA 6 banned (avoidance 0.44): fails |
| Non-default bans, N=50 each | ban DFS: BFS 39; ban unit-weight Dijkstra (absent): BFS 30, DFS 18 | ban BF/SPFA: Dijkstra 33; ban Floyd (absent): Dijkstra 25, **BF/SPFA 9** |
| Forced programs kept (M) after up to 120 attempts | 30/28/11/28/30/29 (BFS/DFS/biBFS/IDDFS/A*/Dijkstra) | 30/29/30 (Dijkstra/BF/Floyd); **biDijkstra 2, Dial 1 -> excluded** |
| C1 rows (>= 3 survivors) | 6 rows x 5 survivors | **none** (K=3 leaves 2 survivors) |

**FRLP gate: FAIL.**

- **(a) Calibration** fails on T1. FRLP implies BFS 0.43 / DFS 0.55 against the sampled 0.77 BFS, so the default
  mass is 0.43 < 0.9, and the intent version fails too. T2 passes with Dijkstra mass 0.97 and Σ = 0.87.
- **(b) Beats uniform:** passes, at **0.59 nats/sample** over uniform across 13 events. The T1 ban and mention events
  give 1.0-1.6 nats, the T2 ones 0.1-0.8, and listall is negative on both tasks.
- **(c) Argmax** hits the realised mode in 7/10 clear-mode events (0.70 < 0.8). All 3 misses are on T1, where FRLP
  predicts DFS but sampling lands on BFS.
- Median cell ESS is 2.5, and 76% of cells have ESS < 5.

**C1 (T1 only, so pooled = T1; descriptive):**

| reference | SHARE (95% percentile CI) | V_u / V_s / V_tot | AIM vs exact null | ladder exists | branch |
|---|---|---|---|---|---|
| neutral twin (primary) | 0.80 (0.28-0.94) | 2.0 / 8.2 / 10.1 | 0.067, null q95 0.258, p 0.35 | no (mean cos 0.14) | **not resolved at this N** |
| mention twin (secondary) | 0.78 (0.61-0.91) | 7.1 / 25.5 / 32.6 | -0.28, p 0.96 | no | X-SPECIFIC BUT UNAIMED |

The verdict is **not robust**, because the two references give different branches. The association aim does not
pass either: -0.08 against a null q95 of 0.30.

**Post hoc** (outside the frozen rule; `results/bootstrap_diagnostics.json`, `results/sensitivities.json`):

- The noise is dominated by program-level importance-sampling noise. The bootstrap variance of the mean gain is
  5-11x the replicate Σ that the frozen correction subtracts.
- For the quadratic V statistics the percentile interval sits above the point estimate. The basic interval for the
  neutral V_tot, [-15.1, 10.2], covers 0.
- The X-specific share is fragile. It falls to 0.41 when the 5 audit-disputed forced programs are removed, and to
  0.44 with a raw-mean u.

So the honest reading for Llama is this: no generic ladder, no aim from prime-and-veto or association, and an
X-specific share that the instrument cannot pin down.

**Other findings (descriptive):**

- **Naming an absent algorithm in a ban raises it, in 5 of 6 cases** (own-drop D_X = L_X(ban) - L_X(neutral)). The
  effect is +3.9 nats for biBFS, +7.6 for IDDFS, +1.8 for unit-weight Dijkstra, +4.1 for BF/SPFA and +4.8 for Floyd.
  A* is the exception at -1.2. The mention twin primes these algorithms by +6.7 to +14.4 nats, and the ban's veto
  (-4.9 to -10.1) cancels only part of that. Bans of present algorithms do lower them: BFS -1.7, DFS -3.0,
  Dijkstra (T2) -1.0.
- **Route test** (FRLP-only, 2 modal bans, 20 cells). The ban's own-drop on the default, -27.2 nats summed, travels
  mostly by the prompt route: F_prompt = 0.84 (bootstrap CI 0.62-1.46) and F_direct = -0.21 (-1.03-0.09). On T1 the
  prompt-route arm also reproduces the full ban's redistribution over survivors (cosine 0.98); the direct-route arm
  does not (0.20).
- **Within a row**, the X-specific residual is anti-correlated with code proximity to X (Spearman -0.6 to -0.9 in 5
  of 6 T1 rows). A ban lowers survivors whose code looks like X.
- **Per-sample predictors** (743 attempted non-banned samples; top-1 = realised mechanism label):

  | predictor | all samples | single bans (313) |
  |---|---|---|
  | FRLP top-1 | 0.59 | 0.67 |
  | empirical sampled ladder | **0.70** | 0.67 |
  | free-form association | 0.52 | 0.67 |
  | latent (FRLP-baseline) ladder | 0.51 | 0.63 |

  The FRLP-vs-sampled-ladder difference is significant overall (paired sign-flip test, -0.11, p < 1e-4) and absent on
  single bans (+0.01, p 0.71).

- **Free-form association.** Asked "What is the standard alternative to X?", Llama answers DFS 20/20 for BFS and
  BF/SPFA 19/20 for Dijkstra (T2). Its top-1 answer agrees with exp1's OpenRouter Llama for 9 of 11 algorithms.

**Labeller.** The canonical labeller re-check reproduces exp1 exactly: 22/22 references, combined vs adjudicated 0.966,
κ(runtime, AST) 0.753, and runtime/AST labels identical to the stored ones. The blind audit of 50 Llama programs with
the second gold judge agrees at **0.78** (T1 0.74, T2 0.87; below 0.9, flagged). Most disputes are flawed attempts
that the audit judge calls 'other'.

**Cost.** OpenRouter USD 0.492 in total: judge USD 0.469 and audit USD 0.023, against a USD 0.50 cap. Compute was
0.64 GPU-hours of logged generation and scoring on one RTX 4090 (24 GB): 558k generated tokens and 39,768 program
scores (11.3M tokens).

## Tests (results/*.json)

| test | result |
|---|---|
| T1 labeller re-check (`labeller_recheck.json`), audit (`llama_label_audit.json`) | pass; audit 0.78, flagged |
| T2 prompts (`tests_prompts.json`) | pass: 71/71 texts equal exp1's conditions.json; one BOS, R, identical spec suffix; ban/neutral twins equal length (k <= 13 fillers, no token-level insertion); sampled ids = scored ids (140 conditions) |
| T3 engine agreement (`tests_scoring_B.json`, `t3_token_check.json`) | pass: HF vs vLLM 0.003-0.007 nats/token, sums within 0.14-0.49 nats; 97% single fenced block, 94% exact re-tokenisation |
| T4 KV reuse | **fails 0.02**: mean 0.16, max 0.40 nats per program sum (bf16 batch-shape numerics; fp32 LM head adopted) |
| T5 scrubber (+ `scrub_stress.json` on all 10 dependency datasets) | pass: fixtures; 244/248 forced programs keep pass status and label after the full scrub, 4 after the conservative scrub; 8 unparsable originals dropped. T5b: on ~1,400 external programs every residual is an attribute name (never renamed by rule), and programs naming nothing are byte-identical |
| T6 FRLP sanity (`tests_frlp_sanity.json`) | own-forced L in [-0.7, 0.2] for 91% of forced prompts (all 9 algorithms majority in range); default's L vs log sampled share: T2 within 0.11 nats, T1 off by 0.59 nats (FRLP under-weights BFS) |
| T7 edit hooks (`tests_scoring_D.json`) | rho = 0 exact; no change outside S or before the band; displacement within 4.3% (bf16), not 1e-3 |
| T8 hybrid caches | pass (0.0 difference) |
| T9 analysis on synthetic data (`test_analysis_c1.json`) | pass (LADDER / SUBSTITUTION / PURE SUBTRACTION recovered; uniform AIM p; unbiased under exchangeable noise; biased under crossed noise -> template-mean sensitivity) |
| T11 independent re-derivation (`independent_rederivation.json`) | 34/34 quantities match to 1e-9; placebo p uniform (KS p 0.61) |
| T11b headline re-derivation (`independent_rederivation_headlines.json`, `audit/rederive_headlines.py`) | 63/63 match via a separate code path. Covers event counts, the per-sample predictor accuracies, route fractions, own-drops, audit agreement and spend. Paired sign-flip test: the sampled ladder beats FRLP overall (-0.112, p < 1e-4), and there is no difference on single bans (+0.010, p 0.71). A random-predictor placebo never beats the ladder |

## Layout

| path | what it is |
|---|---|
| `method.py` | Orchestrator: one sub-command per stage, plus `outputs` (writes `method_out.json` and `data/samples.jsonl`). |
| `src/config.py` | Frozen protocol: v2 display names, W1-W5 ban/mention/neutral templates, nonce, novelty, forced (10), listall, free-form, two-step; Llama chat rendering; neutral nouns; ban-length padding. |
| `src/gen_client.py`, `scripts/serve_vllm.sh` | vLLM sessions (A1-A6, C): token-id prompts, explicit SamplingParams, per-request seeds. |
| `src/label_worker.py` | Canonical labeller (`canon/pipeline.py label_rows`), S0.4 re-check, free-form parsing, Llama label audit. |
| `src/names.py`, `src/scrub.py` | Name table and the tokenize/ast name scrubber. |
| `src/forced_set.py` | S2: forced set, halves, scrub + validation, shingle coverage, T3 token check. |
| `src/frlp.py`, `src/score_session.py` | HF scoring engine (prefill once, KV reuse, fp32 head), sessions B and D, random edits, route test, T3/T4/T7/T8. |
| `src/analysis_c1.py`, `src/run_analysis.py` | S6 analysis (frozen in `commitments.log`). |
| `src/test_analysis_c1.py`, `src/test_prompts.py`, `src/test_frlp_sanity.py` | T9, T2 (+ model record), T6. |
| `src/figures.py`, `figures/` | Figures (PDF + PNG; spec JSON beside the generator-made ones): landing composition (fig1a/b) and Wilson bars (fig1c/d), T1 gain heatmap with u (fig2), C1 components (fig3), AIM null (fig4), FRLP-implied vs sampled (fig5), ban cosines (fig6), ESS (fig7), route test (fig8). |
| `src/deviations.py`, `results/deviations.json` | Every interpretation and deviation, with evidence (29 entries). |
| `audit/rederive.py`, `audit/rederive_headlines.py` | T11 independent re-derivations (gate, C1, AIM, branch; and the other headline numbers) with placebos. |
| `canon/` | Read-only copy of exp1's canonical suite (tasks, hidden tests, references, labeller, prompts), with `SHA256SUMS`. |
| `data/raw_gen.jsonl`, `data/labelled.jsonl`, `data/samples.jsonl` | All 1,780 generations (seeded), the labelled program rows, and the shared per-sample schema. |
| `data/free_answers.jsonl`, `data/forced_set.jsonl` | Free-form answers; the 248 scrubbed FRLP programs with token ids and halves. |
| `data/program_eval_cache.jsonl`, `data/judge_cache.jsonl` | Test, probe and judge caches (re-running costs nothing). |
| `frlp/parts/<task>/*.parquet`, `frlp/scores_<task>.parquet`, `frlp/cells.jsonl` | Per-condition program scores, per-task score matrices, and FRLP cells with ESS (5 variants). |
| `results/` | Gate, events, collapse, C1 + bootstrap + nulls, sensitivities, diagnostics, tests, model record, selections, cost. |
| `method_out.json` (+ `full_`/`mini_`/`preview_`) | `exp_gen_sol_out` output: one example per sampled program with `predict_frlp_top1` and three baselines; forced programs; free-form answers; all metadata. |
| `commitments.log`, `results/commitment_audit.json` | Hash-chained sha256 commitments (freeze before the first S5 score, then each recorded fix) and their chain check. |
| `scripts/` | Model download, dependency extraction, scrubber stress test, vLLM server. |
| `reproducibility.md`, `restore.sh` | Full procedure; environment restore. |

The model weights are not in this folder. They were read from the run's shared Hugging Face cache, at revision
`0e9e39f249a16976918f6564b8830bc894c89659`, with shard sha256s in `results/model_record.json`. Everything in this
folder stays on the run's volume. Apart from `.venv/`, which is marked for deletion, no file here is 10 MB or larger,
so everything else is published.

## How to run

See `reproducibility.md`. In short:

- **CPU-only re-analysis from the published raw files:** `./restore.sh`, then
  `.venv/bin/python -m src.run_analysis`, `audit/rederive.py`, `-m src.figures` and `method.py outputs`.
- **Full regeneration:** needs a 20+ GB GPU, the vLLM server script and the stage order given there.

## Restoring removed files

`.aii/manifest.yaml` marks only regenerable bulk for deletion:

- `.venv/`: `./restore.sh`, i.e. `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml`.
- `src/__pycache__/`: `.venv/bin/python -m compileall -q src`. It is also recreated automatically on import.
- `canon/__pycache__/`, `canon/tasks/__pycache__/`, `canon/gen/__pycache__/`, `canon/labeller/__pycache__/`:
  `.venv/bin/python -m compileall -q canon`, which covers all four.
  The individual commands are `-m compileall -q canon/tasks`, `canon/gen` and `canon/labeller`.
- The model weights, which are not stored here: `DOWNLOAD_MODEL=1 ./restore.sh`, i.e.
  `huggingface-cli download meta-llama/Llama-3.1-8B-Instruct --revision 0e9e39f249a16976918f6564b8830bc894c89659`.
