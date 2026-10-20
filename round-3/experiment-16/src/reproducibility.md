# Reproducibility: where a coding ban takes effect (12 frozen bench tasks, Qwen3-8B)

This file describes what was actually run to produce `results/`, `figures/`, `method_out.json` (and its `full_`,
`mini_` and `preview_` variants). Steps are listed in the order they ran, with hardware, seeds and runtimes. Every
path is relative to this artifact's folder.

## 1. Get the artifact

This workspace is published as one folder of the run's public GitHub repository. Clone the repository and `cd` into
this artifact's folder. In the published layout that is `round-3/experiment-16/src`; the upstream artifacts are sibling
folders, `round-2/experiment-<k>/src` and `round-1/dataset-1/src`.

```bash
git clone <repository-url> repo
cd repo/round-3/experiment-16/src
```

All inputs the code uses are already snapshotted in `inputs/` and published with this folder, together with
`inputs/bench/commitment.json` and `results/input_hashes.json`. The upstream folders are needed only to re-run S0.

## 2. System, Python and libraries

What was used for the reported run:

| item | value |
|---|---|
| OS | Debian GNU/Linux 12 (bookworm) container, Linux kernel 6.8 (any recent Ubuntu works the same way) |
| GPU | 1 x NVIDIA L4, 23 GB VRAM (driver 595.91, CUDA 13.2 driver; torch wheels are cu128), compute capability 8.9 |
| CPU / RAM | 6 CPU cores and 66 GB RAM (container cgroup limits) |
| Python | 3.12.14 (uv-managed) for the project, plus a stdlib CPython 3.12 (`python3.12` on PATH) for the bench sandbox, which runs candidate programs as `python3.12 -I -S` subprocesses |
| package manager | uv 0.6.14; the venv has no pip |
| C compiler | not needed |

Install the exact versions used. All 74 installed packages are pinned identically in `pyproject.toml` and
`requirements.txt`, which come from `uv pip freeze` of the run's `.venv`:

```bash
# system: an NVIDIA driver with CUDA >= 12.8 support; python3.12 on PATH for the sandbox
curl -LsSf https://astral.sh/uv/install.sh | sh          # if uv is missing
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r requirements.txt
```

Key versions: torch 2.8.0, transformers 4.57.6, accelerate 1.15.0, tokenizers 0.22.2, numpy 2.2.6, scipy 1.18.1,
pandas 3.0.6, statsmodels 0.15.0, zss 1.2.0, openai 3.35.1, loguru 0.7.3, matplotlib 3.11.2. `./restore.sh` does
the install and the model download in one go.

## 3. Model, upstream data, keys and environment variables

- **Model:** `Qwen/Qwen3-8B` at Hub revision `b968826d9c46dd6066d109eabc6255188de91218`, bf16 (~16.4 GB), thinking
  off everywhere.
  - It is read from the Hugging Face cache named by `HF_HOME` / `HF_HUB_CACHE`. Set `BRT_MODEL_PATH` to use a local
    copy of that snapshot instead.
  - Download: `.venv/bin/huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218`.
- **Upstream artifacts** are read only by S0 (`src/s0_inputs.py`) and by the dataset check in `src/supplementary.py`.
  There is one environment variable per artifact. Its default is relative to `src/cfg.py`: the run volume's layout if
  present, else the published sibling folders.

  | env var | artifact id | role | published default |
  |---|---|---|---|
  | `BRT_EXP8_DIR` | art_8_ULPE8jJQc_ | HF engine; T1/T2 suite and labeller; frozen T1/T2 prompts; iteration-2 samples; exp8 route F values | `../../../round-2/experiment-8/src` |
  | `BRT_EXP11_DIR` | art_0ndRfWKBWclR | the 12 frozen bench tasks with `commitment.json`; bench labeller and judge (`bench/common`); pilot and forced programs; association answers; neutral nouns | `../../../round-2/experiment-11/src` |
  | `BRT_EXP7_DIR` | art_6zBfl3kDjeiP | frozen templates W1-W5 and the ' .' padding rule; T1/T2 forced programs | `../../../round-2/experiment-7/src` |
  | `BRT_EXP9_DIR` | art_IVZc3TWCeE9f | iteration-2 single-ban draws (screen reference) | `../../../round-2/experiment-9/src` |
  | `BRT_EXP12_DIR` | art_3iv5G76C3yoX | iteration-2 fresh ban pool, raw and labelled (screen reference) | `../../../round-2/experiment-12/src` |
  | `BRT_DATASET_DIR` | art_j3Rm_lr2nzR6 | declared dataset dependency: concreteness norms (noun check) and LeetCode sources | `../../../round-1/dataset-1/src` |

- **Keys (names only):** `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY`. They are used only by the frozen blind judges
  when the runtime and AST labels disagree:
  - bench: `google/gemini-2.5-flash-lite`;
  - T1/T2: exp8's `openai/gpt-4.1-mini`.

  Answers are cached by code hash in `labelling/data/judge_cache.jsonl` (seeded from exp11's cache) and in
  `inputs/exp8/suite/labeller/judge_cache.jsonl`, so a re-run with the same programs needs no calls. This run spent
  USD 0.105 in total, against a cap of USD 0.15 per judge family.
- **Optional variables:**
  - `BENCH_SANDBOX_PYTHON`: the sandbox interpreter.
  - `AII_SKILLS_DIR` or `AII_FIG_GEN`: the aii-data-fig-gen generator for the figures, and the aii-json scripts for
    the JSON variants and schema check.
  - `BRT_BATCH` (40), `BRT_PRUNE_AFTER` (560), `BRT_GPU_DEADLINE` (epoch seconds).
  - `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`, which was set for every GPU process.
- **User uploads:** the run's private upload folder was empty. Nothing private was used, and a reader needs nothing
  extra.

## 4. Commands, in the order they were run

All randomness is seeded:

- **CRN uniforms:** one numpy PCG64 stream per slot, `stable_seed('beh', task, template, k)`. This is exp8's key and
  function; slots k = 0-19, and k = 20-39 for the second draw.
- **Veto redraws:** an independent stream, `stable_seed('beh', task, template, k, 'veto')`.
- **Bootstraps:** `20261020` + fixed offsets (10,000 hierarchical reps).
- **Permutations:** 100,000.
- **Landing nulls:** 2,000 reps.
- **Proximity pairs:** `random.Random(0)`.

`predictions/seeds.json` lists them.

| # | command (from this folder) | what it does | runtime (L4) |
|---|---|---|---|
| 1 | `.venv/bin/python src/s0_inputs.py` | snapshot every input into `inputs/`; verify the 12 bench tasks against `commitment.json` (all ok); write `results/input_hashes.json` | 1 min CPU |
| 2 | `.venv/bin/python src/s0_recheck.py` | labeller re-check: bench references 50/50, gold equal to `gate.json`; exp8 suite 0.957 and 22/22 (`results/labeller_recheck.json`) | 1.5 min CPU, USD 0 |
| 3 | `.venv/bin/python method.py s1` (run as an inline call to `prompts_s1.stage_s1`) | ban / twin_A / twin_B prompts with all alignment asserts (`prompts/prompts.jsonl`) | seconds |
| 4 | `.venv/bin/python src/run_s2.py` (= `method.py s2`) | distinctive n-grams, prefills, opening-veto variant, ASSOCIATE / PROXIMITY (`predictions/*.json`) | 1.5 min CPU |
| 5 | `.venv/bin/python tests/gpu_smoke.py 40`, `.venv/bin/python tests/gpu_timing2.py` | step latency and memory: B=40 cannot hold 1024 forced steps; stock-path 89 / 92 / 101 ms per step at B = 20 / 30 / 40 | 6 min GPU |
| 6 | `cd src && ../.venv/bin/python labelq.py &` | label worker: streams `data/samples_raw.jsonl` into `data/samples.jsonl` | background |
| 7 | `cd src && PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True BRT_BATCH=40 BRT_PRUNE_AFTER=560 BRT_GPU_DEADLINE=<now + 215 min> ../.venv/bin/python gpu.py &` | GPU queue: S3.2 prefix scoring and commit #1 (predictions), then S4 (b + V1), screen round 1, twin-only controls; waits for commit #1 | 78 min GPU in total |
| 8 | `.venv/bin/python tests/test_cpu.py`; `.venv/bin/python tests/test_analysis_smoke.py` | CPU tests T3-T5 (`results/tests_cpu.json`) and the analysis smoke test, run while S4 sampled | 2 min CPU |
| 9 | `.venv/bin/python method.py close1` (run as the equivalent inline call) | append `src/analysis/analysis.py`, `src/gpu.py`, `src/screen.py` and `tests/test_cpu.py` to commit #1 and release the queue; asserts no ban row exists yet | seconds |
| 10 | (same GPU process) | U1-U3 + U9 on T2; commit #2 from the S4 labels; S6 (a, c, d on all 12 tasks); gate; Q2 K0 (gated); Q4 + Q7 prefills (gated); screen round 2 + T2 heapq prefill; S8 log-prob readout; Q6 round 3; Q8 non-gated K0 | (in #7) |
| 11 | `cd src && PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True BRT_BATCH=40 BRT_PRUNE_AFTER=560 ../.venv/bin/python gpu_extras.py &` | extras: controls on every gated task, a second CRN draw (k = 20-39), prefill depth sweep | 26 min GPU |
| 12 | `AII_SKILLS_DIR=<aii skills folder> ./run_final.sh` | analysis, replication, supplementary, figures, `method_out.json`, `audit/rederive.py`, JSON variants and schema check | 3 min CPU |
| 13 | `.venv/bin/python audit/rederive2.py` | second independent re-derivation (see section 5) | 10 s |

Total GPU time was about 1.8 h. The main queue ran 314 batches with 73.6 min of sampling; the extras ran 22.9 min.
Per-batch times are in `results/timing.json` and `results/timing_extras.json`.

What happened on the way, as actually run:

- **Batch size.** The plan's RTX A4500 was an L4, so B = 40 replaced B = 10. All batches sharing a shape class have
  the same shape, so CRN partners are bit-identical when their inputs are (U1, U2 = 1.00).
- **K0.** K0 was implemented as a span-dropped cache rather than an attention mask. An explicit mask disables SDPA's
  native GQA in transformers and costs 50% more per step. U3 checks the equivalence (TV 1.2e-7).
- **Judge failures.** The bench judge returned transient HTTP 429s. The label worker was restarted with retries and
  later with lower caps (USD 0.15 per judge family). Disputed rows are re-judged when the worker is idle.
- **Concurrent label workers.** Each restart command backgrounded `cd src && nohup python ...`, so `$!` was the
  wrapper subshell's PID and the earlier workers kept running.
  - From 18:50 to 20:16 UTC up to three label workers labelled the same rows, giving 24,924 lines for 13,030 uids.
  - The file was compacted to the last row per uid, which every reader used throughout. Labels are deterministic up
    to judge nondeterminism, and the audits find 0 mismatches.
  - To avoid this, start background jobs as `nohup ../.venv/bin/python labelq.py &` from inside `src/`, not in an
    and-list.
- **Amendments.** Three amendments to the committed analysis code are logged with sha256 before and after in
  `results/prereg_amendments.json`: A1 screen reference recount, A2 F5's jackknife-primary rule, A3 the C1 top-1 under
  ties.
- **Timing file.** The extras worker originally overwrote `results/timing.json`. It was rebuilt from
  `logs/gpu_worker.out`, and `src/gpu_extras.py` now writes `timing_extras.json`.

On the same GPU type and library versions, CRN sampling is bit-reproducible at a fixed batch shape. On another GPU,
bf16 kernels differ and individual samples change, so shares and route fractions should agree within their intervals
rather than exactly.

## 5. What a reader should get

| quantity | value | file |
|---|---|---|
| gated tasks (avoidance) | T03 0.99, T10 1.00, T05 0.83, T06 0.79, T13 0.59; 7 others fail the gate | `results/gate.json` |
| pooled F_prompt / F_direct / I / F_K0 (5 gated tasks, ratio of sums) | 0.611 / 0.744 / -0.355 / 0.621 | `results/route.json` -> `route.point` |
| jackknife 95% CI (primary under F5) | F_prompt [0.06, 1.17]; F_direct [0.38, 1.11] | `route.intervals` |
| C2a verdict | DISCONFIRMED under the jackknife, percentile and BCa intervals | `route.verdict_by_interval` |
| per-task F_prompt / F_direct | T03 1.00/0.74, T10 1.00/0.80, T05 0.41/0.96, T06 0.04/0.99, T13 0.39/0.02 | `route.per_task` |
| C2c | all classed HIGH_DIRECT; hit fraction 0.80; rho -0.34, p = 0.30 -> INCONCLUSIVE | `results/c2c.json`, `predictions/c2c.json` |
| prefill P_open (signature / neutral) | 0.98-1.00 / -0.12-0.01 | `results/prefill.json` |
| prefill depth curve | ban intact through the `def` line; undone by the first body token | `results/replication.json` -> `prefill_depth_curve` |
| second CRN draw (pooled F_prompt / F_direct) | 0.64 / 0.74; per-task Spearman 0.89 / 0.90 with the first draw | `results/replication.json` |
| path screen | off-default share 0.00 (T1) and <= 0.01 (T2) in every veto round; iteration-2 references T1 DFS 257/257, T2 BF/SPFA 255/260 | `results/screen_paths.json` |
| controls | placebo splice \|diff\| <= 0.04 and K0b 1.00 on all 6 tasks where they ran | `results/replication.json` -> `controls_all` |
| log-prob readout (descriptive) | F_lp_prompt 0.40, F_lp_direct 0.45 | `results/lp_readout.json` |
| engine validation (T2 vs exp8) | banned a 0, b 20, c 3, d 19 of 20 | `results/engine_validation.json` |

These numbers feed the paper's bench route-test result (C2a, the per-task mechanism split), the veto-sufficiency test
(C2c), the shallow-ban/prefill result and the path veto screen. `README.md` gives the interpretation and caveats, and
`figures/fig1`-`fig6` are the corresponding figures.

**Independent re-derivation.** Two scripts recompute the headlines from the raw per-row files without the analysis
code, each by its own code path.

`audit/rederive.py` (`results/rederive.json`):
- recomputes every share, the gate, the pooled and per-task F values, V_t, the C2c hits and P_open, with 0 mismatches;
- checks U4-U6 on all production rows;
- shuffles arm labels within slots, which destroys the route structure;
- verifies the hash chain and the commit-before-sample ordering.

`audit/rederive2.py` (`results/rederive2.json`) recomputes, all equal to the reported values:
- F_K0 and I;
- the jackknife intervals;
- rho with an exact permutation p;
- the McNemar flip tests, whose same-arm re-paired placebo gives p = 1.0;
- the depth-curve P_open values;
- the second-draw pooled F and the between-draw Spearman correlations;
- the screen shares and the iteration-2 reference counts;
- the template avoidance and W4 share;
- the U9 counts;
- the log-prob readout, from the raw `token_lp/*.npz` arrays.

**Not independently re-derived** (computed only by `src/analysis/analysis.py` or `src/replication.py`):
- the hierarchical-bootstrap percentile and BCa intervals;
- the Bayesian mixed GLM;
- the landing-by-route JS values and their resampling nulls;
- the first-divergence medians;
- the C1 log-scores.
