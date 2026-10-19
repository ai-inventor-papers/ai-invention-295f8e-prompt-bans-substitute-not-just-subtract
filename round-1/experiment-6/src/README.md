# Temperature and seeds: new ideas or rewording?

A screen on **Qwen3-8B** (thinking off and on) over two path-search coding tasks:

- **T1:** unweighted 4-connected grid path search. Any valid path is accepted, so BFS is not forced.
- **T2:** weighted single-pair shortest path on a directed graph.

It asks whether sampling **temperature** and random **context seeds** change *which algorithm* the model writes (an
"idea knob") or only *how the code is worded* (a "phrasing knob").

- **Baseline.** Every cue is compared with a no-cue baseline at matched decoding. Arm A0 is the baseline for seeds
  and instructions; the same baseline preambles serve the whole temperature grid.
- **Labelling.** Each program is labelled by execution:
  - hidden tests decide correctness;
  - a runtime-signature tracer and AST rules decide the algorithm;
  - a blind LLM judge settles disagreements between the two.
- **Analysis.** Phrasings are clusters of identifier-normalised AST 4-gram shingles. Read-position (R) and
  generated-position hidden states are analysed in a mode subspace taken from forced-implementation prompts.
- **Forecast.** Predictions were hash-committed before sampling (`forecast/predictions_screen.json`, sha256 in
  `logs/forecast_sha256.txt`).

## Main results (Qwen3-8B, N = 100 per cell)

| Question | Result |
|---|---|
| BFS share on T1 (classified programs), thinking off, T ∈ {0.3, 0.7, 1.0, 1.3} × {top-k=10, top-p=0.95} | **797/800**; every cell ≥ 0.99 (Wilson 95% lower bound ≥ 0.946) |
| BFS share on T1, thinking on (8 cells) | **800/800** |
| Dijkstra share on T2, thinking off / on | **797/800** / **800/800** |
| Entropy seed `seed=d32qxk4nt43` / word seed `seed=(horse chair roof love)`, shift of the modal share vs A0 | T1 +1.0 / +1.0 pp; T2 0.0 / 0.0 pp. All 90% cluster-bootstrap CIs lie within ±15 pp |
| Semantic seed (a story implying the approach, never naming it) | T2: Bellman-Ford share **+66 pp** (Dijkstra −67 pp, one-sided cluster-permutation p = 0.0004). T1: bidirectional BFS +2.2 pp (p = 0.078) |
| Instructions ("fully novel", "list 10 then implement") | T2 Dijkstra −14.6 / −10.7 pp. T1 at most −3.7 pp |
| Gen-then-select (an external RNG picks 1 of 10 listed approaches) | DA_idea@25 3.98 (T1) / 3.00 (T2) vs A0 1.26 / 1.00, but pass rate 55% / 75% |
| Phrasings vs ideas over T (θ=0.8, single linkage) | T1 thinking off: phrasing clusters 3–4 at T=0.3 → 24–36 at T=1.3, while ideas stay 1–2. Slope of log PPI +1.27 (top-k) / +1.22 (top-p) per unit T, paired CI > 0 |
| Read-position displacement in the mode subspace (ratio to baseline-paraphrase noise; 1.5× equivalence bound) | Entropy seed 0.73 (T1) / 1.16 (T2). Word seed **1.56** [1.27, 1.87] (T1) / 1.01 (T2). Neutral insert 0.81 / 1.29. Semantic seed **3.42 / 3.70** |
| Trajectory variance (first 64 generated tokens) vs T | Complement variance rises steeply. Raw mode-subspace share is flat on T1 (slope −0.0004, CI [−0.005, 0.005]) and rises slightly on T2 (+0.014). Excess over the data-matched null rises on both |
| Thinking traces | 100% hit the 2,048-token thinking cap. The first approach mentioned is BFS / Dijkstra in ≥ 98% of traces and equals the implemented one |
| Overall verdict (applied mechanically) | **MIXED.** Failing sub-claims: the variance-share slope (S-T6), and random-seed equivalence at R (the word seed on T1) |
| Forecast | 6/8 hits (P5 and P7 missed) |

**Labeller gate (strict criteria): failed on both tasks.** Both tasks carry `labeller_gate_failed` and all results are
**descriptive**. Details:

- Runtime/AST agreement on the 16 reference implementations: 100%.
- Population kappa(runtime, AST): 0.88 (T1) and 0.85 (T2).
- Gold-set kappa: 0.34 and 0.11. It is low by construction, because the gold set oversamples disagreements.
- Final-vs-adjudicated agreement: 93% (T1) and 70% (T2).
- Agreement on *correct* gold programs: 92% on both tasks.
- Every T2 gold disagreement is a broken implementation, labelled by its attempted structure where the gold judges
  say "other".
- Forced-label agreement on A5: 0.90 (T1) and 0.82 (T2).

**Headline numbers were re-derived independently.** `verify_headlines.py` re-extracts code from the raw generations
and applies its own label rule, its own permutation test and its own QR-based subspace. All placebo tests are
non-significant (p = 0.49–1.0), and the placebo displacement ratio is about 1. See `results/verify_headlines.json`.

## Layout

| Path | Contents |
|---|---|
| `method.py` | Orchestrator: `setup`, `smoke`, `generate`, `label`, `gate`, `hooks`, `analyze`, `output`, `all`. It also builds `method_out.json` |
| `common.py` | Paths, task texts, algorithm catalogue, alias lexicon, seeds, JSONL I/O |
| `tasks/t1_grid.py`, `tasks/t2_sssp.py` | Hidden-test generators (fixed RNG), path checker, scipy oracle |
| `tests/` | `t1_hidden.json` (41 cases), `t2_hidden.json` (39 cases), per-case time limits, reference-gate report |
| `references/` | One reference per catalogue mode, plus labeller-test variants (16 files) |
| `harness/run_tests.py`, `harness/_driver.py` | `python -I` subprocess harness: 2 GB RLIMIT_AS, worker thread, per-case wall-clock limit |
| `labeller/_trace_driver.py`, `labeller/tracer.py` | Runtime-signature tracer: heapq/deque/queue instrumentation, AST pop/append rewrite, settrace, crafted inputs, rules |
| `labeller/ast_rules.py` | AST rules on docstring- and comment-free code |
| `labeller/judge.py` | Blind OpenRouter judge with a cost cap and stop-on-budget-refusal |
| `labeller/label.py` | Labelling pipeline; writes `results/samples.jsonl` |
| `labeller/gold.py` | Gold set, two judges plus adjudicator, gate; writes `results/labeller_gate.json` |
| `labeller/test_rewrite.py` | Check that the AST rewrite leaves reference outputs unchanged |
| `prompts/build.py` | Paired prompt scaffold, seeds, instructions, forced and described prompts, tail-identity assertions |
| `prompts/prompts.json`, `prompts/assertions.json` | All 552 prompts; token counts and assertion report |
| `gen/arms.py` | vLLM arms A0–A6, staged and resumable, two-pass thinking budget forcing |
| `hooks/states.py` | HF hook block: R states at all 36 layers, probes, l*, teacher-forced trajectory states |
| `analysis/` | `metrics.py` (DA@K, Hill, Wilson, normalisation, clustering), `behaviour.py` (8a/8c/8g/8h), `phrasing.py` (8b), `subspace.py` (8d/8e), `thinking.py` (8f), `verdicts.py` (8i), `figures.py`, `run_all.py`, `test_metrics.py` |
| `verify_headlines.py` | Independent re-derivation of the headline numbers, with placebo tests |
| `forecast/predictions_screen.json` | Hash-committed predictions P1–P8 |
| `results/raw/<arm>.jsonl` | Every generation: prompt and output token ids, text, decoding, seed |
| `results/samples.jsonl` | One row per sample in the shared screen schema: labels, tests, code, decoding |
| `results/analysis.json` | All analysis outputs (8a–8i), verdicts, forecast check |
| `results/summaries.json` | Per condition: label counts, pass rate, Wilson CI, Hill number |
| `results/labeller_gate.json` | Gate metrics, confusion matrices, revisions, forced-label agreement |
| `results/probe_curves.json` | Per-layer leave-one-frame-out accuracy, transfer accuracy and shuffled-label nulls |
| `figures/fig1`–`fig6` (`.png`, `.pdf`) | BFS/Dijkstra share vs T; ideas vs phrasings; R displacement ratios; variance split; MDS of R centroids; label mix by condition |
| `method_out.json` (+ `full_`, `mini_`, `preview_`) | `exp_gen_sol_out` schema: 5,220 examples, plus all results and deviations under `metadata` |
| `logs/` | Capacity probe, generation stats, labelling, hooks, analysis and OpenRouter cost logs |
| `states/` | Hidden-state arrays, float16 (about 0.8 GB). Trajectory states are split into `eval_<task>_l<layer>_part_NNN.npy` files of under 45 MB each, written by `common.save_npy_parts` and read by `common.load_npy_parts`. **Deleted after the round; regenerate with `method.py hooks`** |

Every kept artifact stays on the run's storage volume at the relative paths above. Files of 100 MB or more are not
published to GitHub. All result files here are below that size; the `states/*.npy` arrays are regenerable.

## How to run

```bash
uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
huggingface-cli download Qwen/Qwen3-8B            # or let HF_HUB_OFFLINE=0 download on first use
export OPENROUTER_API_KEY=...  OPENROUTER_BASE_URL=...   # judge calls (about $0.07 in total for this run)
.venv/bin/python method.py all                    # setup -> generate -> label -> gate -> hooks -> analyze -> output
.venv/bin/python verify_headlines.py              # independent re-derivation + placebos
```

Single stages: `.venv/bin/python method.py <stage>`. Generation resumes from `results/raw/<arm>.jsonl`. See
`reproducibility.md` for the exact sequence that was run, with runtimes.

## Restoring removed files

Every `delete` entry in `.aii/manifest.yaml` can be restored as follows:

| Removed path | Restore command |
|---|---|
| `.venv/` | `uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` |
| `states/` | `.venv/bin/python method.py hooks` (needs the model and about 18 min on one GPU; reads `results/raw/A1.jsonl` and `A5.jsonl`) |
| `__pycache__/`, `*/__pycache__/` | Nothing to run: Python rebuilds the bytecode on the next import (for example `.venv/bin/python method.py --help`) |

Everything else in this folder is kept.

The model weights were read from the run's shared Hugging Face cache, not from this folder. Restore them with
`huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218`.
