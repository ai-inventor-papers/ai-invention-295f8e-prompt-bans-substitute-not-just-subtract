# Reproducing "Do banned AI coders just rename BFS?" (TP-B, iteration 9)

This file records what was actually run to produce this artifact, in order, and how to repeat it on Ubuntu.
Every path below is relative to this artifact's folder.

There are two levels of reproduction:

- **Level A, re-analysis.** Rerun the tracer, the analyses, the audits, the figures and `method_out.json` from the
  stored generations. This needs no API key and costs nothing. It is deterministic, except for the traces of candidate
  programs that draw unseeded random numbers (random-priority and random-walk programs).
- **Level B, full rerun.** Draw new samples from OpenRouter as well. This costs about USD 3.9. It is not byte-identical:
  the models are served by quantised providers whose outputs vary even with a fixed seed. Seeds and providers are
  recorded on every row.

## 1. Get the artifact

The workspace is published as one folder of a public GitHub repository.

```bash
git clone <URL of the repository>
cd <repository>/<this artifact's folder>     # the folder holding this file, method.py and src/
```

Two things are not in the published folder:

- `.venv/` is rebuilt in step 2.
- `data/trace_cache/` holds per-probe tracer statistics: 179 MB, stored as `<version>_part_NNN.jsonl` parts of at most
  about 45 MB each. It is a cache, so it is listed for exclusion from publication and your copy may lack it. Any stage
  that needs a trace recomputes it. Re-tracing every program takes about 30 CPU-minutes in all. Every class it holds is also
  stored per row in `results/retrace.jsonl` and `data/labelled_v9_*.jsonl`.

## 2. System packages, Python and the environment

- **Operating system.** This run used Linux 6.8 on x86-64 (glibc 2.36). Any recent Ubuntu (22.04 or 24.04) works.
- **System packages.** `git`, `curl`, `coreutils` (for `sha256sum`) and [uv](https://docs.astral.sh/uv/). Install uv
  with `curl -LsSf https://astral.sh/uv/install.sh | sh`. No compiler or GPU driver is needed.
- **Python.** CPython 3.12. This run used 3.12.14. If the system lacks 3.12, `uv python install 3.12` provides it.
- **Sandbox interpreter.** Candidate programs and the tracer child run in a stdlib-only CPython 3.12 subprocess
  started with `-I -S`. The tracer uses `/usr/local/bin/python3.12` when it exists and otherwise the interpreter
  running `method.py`. The test harness (`vendor/exp9/tasks/harness.py`) also honours `$SANDBOX_PYTHON`.
- **Create the environment:**

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
```

`pyproject.toml` pins every package that was installed in `.venv`, at the installed version. The direct imports are
numpy, scipy, pandas, matplotlib, loguru, aiohttp, zss, networkx and pyyaml; the rest are their dependencies.

```
aiohappyeyeballs==2.7.1  aiohttp==3.14.5  aiosignal==1.4.0  attrs==26.1.0  contourpy==1.4.0  cycler==0.12.1
fonttools==4.67.0  frozenlist==1.8.0  idna==3.20  kiwisolver==1.5.1  loguru==0.7.3  matplotlib==3.11.2
multidict==7.1.0  networkx==3.7  numpy==2.5.4  packaging==26.3  pandas==3.1.0  pillow==13.0.0  propcache==0.5.4
pyparsing==3.3.3  python-dateutil==3.0.0  pyyaml==6.0.3  scipy==1.18.1  six==1.17.0  typing-extensions==4.16.0
tzdata==2026.5  yarl==1.25.1  zss==1.2.0
```

To check the environment:

```bash
uv pip check --python .venv/bin/python
.venv/bin/python method.py --help
```

## 3. Inputs, downloads and environment variables

**No model weights or checkpoints are downloaded.** Every language model is called through OpenRouter.

**Prior-artifact inputs.** Every input that a stage after Stage 0 reads is already in `inputs/`: read-only copies of
the prior artifacts' files with `inputs/SHA256SUMS`. To verify them (70 files):

```bash
(cd inputs && sha256sum -c SHA256SUMS)
```

Only two stages read the prior artifacts themselves:

- `stage0` makes the copies;
- `datasets` reads the declared dependency's 96 MB `full_data_out.json` in place.

Each artifact is found through one environment variable. If that variable is unset, the code looks for a sibling
folder of this one named by the artifact id, then for the AI Inventor run layout (`src/common.py`, `_dep_path`).

| Key | Artifact id | What it supplies | Variable |
|---|---|---|---|
| `dataset` | `art_j3Rm_lr2nzR6` (declared dependency; published as a sibling folder) | algorithm-choice source data: implementations for the novelty corpus, CLRS BFS/DFS traces | `TP_DEP_DATASET` |
| `iter8` | `art_R-HSmXq2t97f` | iteration-8 protocol, renderer, labeller, judges, C1-C8 rows | `TP_DEP_ITER8` |
| `exp9` | `art_IVZc3TWCeE9f` | T1 harness, references, iteration-2 labeller, multi:TOP5 rows (C9) and gold rows | `TP_DEP_EXP9` |
| `exp31` | `art_zNyBP6zieI5u` | gemma-3-4b-it TOP5 rows (C10) | `TP_DEP_EXP31` |
| `exp2` | `art_D6Z0Snf09sFL` | ITER1 41-case secondary suite | `TP_DEP_EXP2` |

The last four are not declared dependencies and may be absent from the repository. Their files are already in
`inputs/`, so skip `stage0`; every later stage reads `inputs/`.

**User uploads.** This artifact reads no user-uploaded input. The run's upload folder is private and is not
published.

**Environment variables**, by name only:

| Variable | Needed for | Notes |
|---|---|---|
| `OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY` | Level B only: `stage0` (/key), `smoke`, `sample`, `describe`, `judge_gate`, `gold_judges`, `label` (judges), `novelty` | Use the base URL that belongs to the key |
| `TP_COST_CAP` | the per-artifact USD cap the sampler and judges check | Default 3.5; the final chain ran with 4.0 (deviation D-cap-labelling) |
| `TP_DEP_<KEY>`, `TP_RUNS_DIR` | `stage0` and `datasets` | See the table above |
| `AII_JSON_SKILL` | `run_final.sh`: full/mini/preview files and schema validation | Optional. Folder of the aii-json skill; skipped when unset |
| `AII_DATA_FIG_GEN_SCRIPTS` | `method.py figures`: house style | Optional. Plain matplotlib is used when the skill is absent |
| `SANDBOX_PYTHON` | the test harness | Optional (see step 2) |

## 4. What was run, in order

**Hardware.** 6 CPUs (cgroup quota), 31 GB RAM (cgroup), and an NVIDIA RTX 2000 Ada GPU (16 GB) that was present
but unused. CPU work used a 6-worker process pool. The whole run took about 3 h 10 min of wall-clock time on
2026-10-23, from 09:45 to 12:56 UTC.

**Spend.** USD 3.889 on OpenRouter. Of this, USD 2.096 was sampling; the rest went to judges, gates and smoke calls
(`results/costs.json`).

Each stage is `.venv/bin/python method.py <stage> [args]` (`uv run method.py ...` is equivalent). Stages that write
commitments (`commit1a`, `commit1b`, `commit2`, `commit3`) append to the hash chain in `commitments.log`, so they are
**not** rerun in a re-analysis.

Times come from the logs in `logs/` (log time stamps, or the file time where a log has none).

| # | Command (UTC) | What it does | Time |
|---|---|---|---|
| 1 | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` (09:45) | environment | 1 min |
| 2 | `method.py stage0` (09:58) | hardware record (`predictions/hardware.json`), input copies + `inputs/SHA256SUMS`, GET /key, mocked budget-403 test | 1 min |
| 3 | `method.py smoke` (09:59) | 2 live calls per model and judge (reasoning field, finish_reason, usage.cost, provider pin) | 1 min |
| 4 | `method.py commit1a` (10:01) | pre-registration of the A/E/F-baseline cells (prompts, seeds, N, predictions, thresholds) | <1 min |
| 5 | `method.py sample A E` (10:02, background) | Qwen3-32B and Qwen3-14B cumulative bans k = 1..5 + held-out k = 5: 600 rows, staged 10 then the rest, /key budget gate before each batch | 52 min |
| 6 | `method.py datasets` (10:23) | all 10 datasets of `art_j3Rm_lr2nzR6` (`results/dataset_use.json`) | 1 min |
| 7 | `method.py describe` (10:29) | N3-D name-free descriptions + Qwen3-32B naming check | 1 min |
| 8 | `method.py tracer_gate round0` (10:36), `round1` (10:51), `round2` (11:03) | tracer v9 gate on 15 references, 9 planted controls and 291 non-ban gold programs; the fixes between rounds are logged as D-gate-r1 and D-gate-r2 | 9 min each |
| 9 | `method.py judge_gate` (10:57) | re-gate of the three adjudication judges on 10 controls each | 1 min |
| 10 | `method.py n5sets` (11:14), `method.py gold_judges` (11:16; rerun 11:22 after the parser fix) | N5 distance matrices + committed set rule; blind order-discipline judges on 100 gold programs | 1 min each |
| 11 | `method.py commit1b round2` (11:19) | pre-registration of tracer, probes, gate result and fallback, rotated sets, descriptions, analysis code | <1 min |
| 12 | `method.py sample B C D` (11:20, background) | N5 rotated sets R1-R6 and N3-D on Qwen3-32B: 350 rows | 63 min |
| 13 | `method.py retrace` (11:20) | trace the 580 iteration 1-8 five-name-ban programs | 13 min |
| 14 | `method.py label A` (11:22), `label E` (11:35), `label B C D` (12:19; B_R4 and D_R6 also alone as they completed) | hidden suites, 10-class labeller, judges, adjudication, lexical flags, tracing of the new rows | 24, 21 and 17 min, overlapping with sampling |
| 15 | `method.py sample F_gptoss_base` (11:29), `label F_gptoss_base`, `commit2` (11:33), `sample F_gptoss_ban`, `label F_gptoss_ban` (to 11:43) | gpt-oss-120b scale check: its own top five from its baseline, then that ban | 15 min |
| 16 | `method.py tracer_tests` (11:35) | 21 mutation, renaming and sandbox unit tests | 2 min |
| 17 | `method.py retrace extras` (12:26) | descriptive extras (single:bfs, TOP/ARC/SCATTER, baselines) | 7 min |
| 18 | `.venv/bin/python audit/placebo_shuffled_events.py` | tracer on order-shuffled event streams | 1 min |
| 19 | `AII_JSON_SKILL=<aii-json skill folder> ./run_final.sh` (12:36; sets `TP_COST_CAP=4.0`) | `commit3`, `analyse`, `bounds`, `reads_summary`, `heap_keys`, `export`, `novelty`, `figures`, `python3 audit/rederive.py`, `python3 audit/clrs_check.py`, `outputs`, full/mini/preview + schema validation, `build_readme.py` | 11 min (novelty 9) |
| 20 | Finalisation (14:45): `python3 audit/rederive_headlines.py`, amendment commits #5 (portable dependency paths, pinned environment, headline audit), #6, #7 and #9 (documentation only) and #8 (trace cache stored in parts under 100 MB; verified identical), then `method.py outputs`, the aii-json format script on `method_out.json`, schema validation of the four files and `.venv/bin/python build_readme.py` | no number changes | 5 min |

**Manual reads.** The executor's reads of 76 programs are stored as data in `data/manual_reads_v9.jsonl`;
`src/manual_reads.py` selects which programs are read.

**Seeds and fixed settings.**

- Sampling seed: `1000 * cell_index + slot + 1`, sent with each request (`src/cells_v9.py`).
- Decoding: T 1.0, top_p 1, max_tokens 12,288, thinking on.
- Providers: Qwen3 pinned to DeepInfra fp8 with `allow_fallbacks` false; gpt-oss-120b at reasoning effort medium.
- Probe grids: seed 9009 (`probes/probes_v9.json`, sha256 committed).
- N5 set selection: seed 0.
- Configuration-cluster bootstrap: 10,000 resamples, seed 0.
- Jonckheere-Terpstra Monte-Carlo test: 100,000 permutations, seeds 0, 1 and 2.
- Manual-read sampling: `random.Random(0)`.
- `audit/rederive.py` placebos use seeds 0, 3, 5 and 11; `audit/rederive_headlines.py` uses seeds 0 to 199.

**Level A: re-analysis without an API key.** Run from this folder after step 2:

```bash
(cd inputs && sha256sum -c SHA256SUMS)
for st in analyse bounds reads_summary heap_keys export figures outputs; do .venv/bin/python method.py $st; done
python3 audit/rederive.py && python3 audit/rederive_headlines.py && python3 audit/clrs_check.py
.venv/bin/python audit/placebo_shuffled_events.py
.venv/bin/python build_readme.py
.venv/bin/python -c "import sys; sys.path.insert(0, 'src'); from common import verify_chain; print(verify_chain()[0])"
```

Notes on Level A:

- Without `data/trace_cache/`, three steps recompute the traces they need: `analyse` (the N5 survivors), `figures`
  (F6) and the placebo. This takes up to about 15 minutes on 6 CPUs. The full retrace of the 580 programs takes 13
  minutes (`method.py retrace`); it refills the cache and rewrites `results/retrace.jsonl`.
- `tracer_gate`, `n5sets` and `describe` refuse to run once commit #1b exists, by design. Their results are stored in
  `results/tracer_gate_round*.json`, `predictions/n5_sets.json` and `predictions/n3d_descriptions.json`.
- `novelty` is left out because it calls judges. Its cached answers are in `data/judge_cache.jsonl`, and its result
  is kept in `results/novelty_audit_v9.json`.

**Level B: full rerun.** Export the two OpenRouter variables and run steps 2 to 20 in the order above. Use an empty
`commitments.log`, or a fresh copy of the folder, so the chain starts from the genesis hash
sha256('iter9_TP-B'). `sample` refuses to draw a cell before the commit that governs it exists, and `label` checks that
the commit precedes the cell's first row.

## 5. What you should get

**Output files.**

- `method_out.json` and its `full_`, `mini_` and `preview_` variants, all valid against `exp_gen_sol_out`. They hold
  1,623 examples in five datasets:
  - `tp_retrace`: 580;
  - `tp_cumulative`: 600;
  - `tp_rotated`: 293;
  - `tp_described`: 50;
  - `tp_scale`: 100.

  `tp_rotated` and `tp_scale` are short of plan because of 429 losses (deviation D-n-short) and because the
  Qwen3-235B cells were dropped.
- `results/*.json`: every analysis.
- `figures/F1`–`F8` (PDF and PNG).
- `README.md`.
- `commitments.log`: 10 entries (#1a, #1b, #2, and the amendments #3 to #9); `verify_chain()` returns True.

**Headline numbers.**

| Number | Value | File |
|---|---|---|
| Tracer gate | references 14/15; planted controls 9/9 by class (8/9 counting that a control must itself pass the 48-case suite); gold 182/260 = 0.70 against a bar of 0.90. The gate **failed**, so the committed fallback applies and N1-N3 are descriptive | `results/tracer_gate_round2.json`; figure F7 |
| N1: lexical minus mechanistic compliance, pooled over 10 configurations | 0.697 with the runtime label (primary after the fallback; bootstrap 95% [0.567, 0.825]); 0.608 with the tracer. Positive in 10/10 configurations under both readings | `results/n1.json`, `results/n1_tracer.json`; figures F1, F2 |
| N2: C6 name-level survivors in a banned coarse class | 72/91 = 0.79 (runtime label); 39/91 = 0.43 (tracer) | `results/n2.json`, `results/n2_tracer.json`; figure F4 |
| N3: Qwen3-32B, k = 1..5 | mechanistic compliance (runtime label) 1.00, 0.84, 0.84, 0.24, 0.22; lexical 1.00, 1.00, 1.00, 0.96, 0.89 | `results/n3.json`, `results/n3_tracer.json`; figure F3 |
| Audits | `audit/rederive.py`: 0 mismatches over 26 checks (N1 per configuration, pooled and verdict; N3 rates and JT for both models; N2; N5). `audit/rederive_headlines.py` reproduces the gate, N1, N2 and sampling-spend numbers above, and its placebo (flags swapped at random within each program) gives a pooled gap of about 0 | `results/rederive.json`, `results/rederive_headlines.json` |

**Where the numbers appear.** No paper has been written from this artifact yet. The numbers appear in `README.md`, in
these sections:

- "Bottom line";
- "Status first";
- N1 to N5;
- "Re-derivation and placebos".

They also appear in figures F1–F8. A paper built on this artifact should cite the `results/*.json` files listed above.
