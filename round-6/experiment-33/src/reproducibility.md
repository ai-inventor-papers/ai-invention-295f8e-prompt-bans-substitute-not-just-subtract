# Reproducibility

This file records what was actually run to produce this artifact: Gemma-3-4B, iteration 6, step 5, the Claim L
replication. The steps are in the order they were run, with the commands, seeds, hardware and runtimes. All paths are
relative to this folder.

## 1. Get the artifact

This folder is one directory of the run's public GitHub repository. Each upstream artifact it reads is a sibling folder
named by its artifact id.

```bash
git clone <repository URL>
cd <repository>/<this artifact's folder>
```

Every upstream file the analysis reads is already copied here under `inputs/`, with sha256 sums in `inputs/SHA256SUMS`.
`inputs/exp28/` holds the iteration-5 Gemma artifact art_hG0QPiaIPNhP: its rows, labels, results, predictions and source.

Upstream folders themselves are read in only two places:
- the preflight stage (`src/stage_inputs6.py`);
- the U6 clean-state equality check (`src/gen6.py clean_state_check`), which reads `art_hG0QPiaIPNhP/cache/`.

Both resolve the folders through ONE environment variable, `AII_ARTIFACTS_DIR`. By default it is this folder's parent,
so the sibling folders of the published repository are used:

| Name in code | Artifact id | Used for |
|---|---|---|
| exp28 | art_hG0QPiaIPNhP | iteration-5 Gemma rows, labels, results; `cache/hit_*.pt` for U6 |
| exp11 | art_0ndRfWKBWclR | frozen bench (`bench/commitment.json` sha256 check) |
| exp23 / exp8 / exp7 / exp18 / eval3 | art_k6nzFCDLOjQP / art_8_ULPE8jJQc_ / art_6zBfl3kDjeiP / art_ccAbfJVcv0LO / art_sV0cQ3ef1ZRQ | staged through exp28's verified copies; seed audit |
| art_j3Rm_lr2nzR6 | art_j3Rm_lr2nzR6 | declared dependency `full_data_out.json` (10 datasets; HumanEval+ exemplars, known-solution corpus) |

`paths.local.json` mapped these names to the original server's folders. It is not published, and a reader does not
need it.

No user-uploaded file was used: the run's `user_uploads/` folder was empty.

## 2. System, Python and packages

- **OS.** The run used Debian 12 (bookworm) in a container. Any recent Ubuntu (22.04 or later) with an NVIDIA driver
  for CUDA 12.8 works. The run had driver 595.91.07, reporting CUDA 13.2.
- **System packages.** `git`, `curl` and `uv` (from https://astral.sh/uv). Python 3.12 is fetched by uv. No other
  system libraries are needed: the torch wheels bundle CUDA.
- **Hardware used.** One NVIDIA L4 (23 GB VRAM), a cgroup CPU quota of 5.1 (6 visible CPUs) and 57 GB RAM.
  - Peak VRAM was about 20.4 GB, at B 50 × (P 249 + 1,536) tokens (U9).
  - The fp32 teacher-forcing check needs about 16 GB.

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
```

`pyproject.toml` pins all 84 installed packages exactly, for example:
- torch 2.8.0 (CUDA 12.8 wheels) and transformers 4.57.6;
- numpy 2.2.6, scipy 1.18.1 and openai 3.35.1.

It equals `uv pip freeze --python .venv/bin/python` (the uv venv has no `pip` binary); a copy is in
`logs/pip_freeze.txt`.

## 3. Models, data and environment variables (names only)

```bash
export HF_TOKEN=...            # gated google/gemma-3-4b-* repositories (accept the Gemma licence first)
.venv/bin/python src/download_models.py
```

- **Models.** `google/gemma-3-4b-it@093f9f388b31de276ce2de164bdc2081324b9767` and
  `google/gemma-3-4b-pt@cc012e0a6d0787b4adcc0fa2c4da74402494554d`. They go into the Hugging Face cache (`HF_HOME` /
  `HF_HUB_CACHE`, optional). They load text-only in bf16 with sdpa attention.
- **`OPENROUTER_API_KEY` and `OPENROUTER_BASE_URL`.** These are used by the LLM judges:
  - the inline labeller judges (exp28's frozen j1 = google/gemini-2.5-flash-lite for bench disagreements, and
    openai/gpt-4.1-mini for path tasks);
  - the audits and the novelty audit (google/gemini-2.5-flash, openai/gpt-4.1-mini, tie-break
    deepseek/deepseek-chat-v3.1).

  Judge answers are cached in `data/judge_cache*.jsonl`, so a re-run over the same programs costs nothing. This run
  spent USD 0.95 (`results/costs6.json`).
- **`AII_ARTIFACTS_DIR` (optional).** The parent folder of the sibling artifacts (see section 1).
- **`AII_DATA_FIG_GEN_SCRIPTS` (optional).** The scripts folder of the aii-data-fig-gen skill, for the house figure
  style. Without it, figures use plain matplotlib.

## 4. Commands actually run, in order (UTC times from the logs)

| # | Command | What it did | Runtime |
|---|---|---|---|
| 1 | `.venv/bin/python src/stage_inputs6.py` | S0: bench sha256 vs ITER2 commitment; dependency (10 datasets, full HumanEval+ extract); seed audit (63001-63008 unused in 775 files, 23,100 rows); labeller re-check (13 bench gates, suite 22/22, 300 exp28 rows) | ~14 min CPU |
| 2 | `.venv/bin/python src/tests6.py` | CPU tests T1-T12 → `results/tests_cpu6.json` (all pass) | ~3 min |
| 3 | `.venv/bin/python src/protocol6.py` | commit #0 at 21:41:44Z: `predictions/protocol_G6.json`, `predictions/analysis_L_gemma.py`, `predictions/hardware.json` | 1 min |
| 4 | `.venv/bin/python src/label_worker.py &` | background labeller: `data/raw_*.jsonl` → `data/labels.jsonl` (5 threads, cached judges) | whole run |
| 5 | `.venv/bin/python src/gen6.py it_session` | it model: U1-U9, engine check (160 rows), U6 clean states (40/40 bit-identical), 1,320 forced programs (66 algorithms x 20), twin top-up (3,750 rows: T 1.0 slots 10-39, T 1.3 slots 0-19) | 21:42-22:25 |
| 6 | `.venv/bin/python src/engine_check6.py` | engine check against exp28's rows → `results/engine_check6.json` | <1 min |
| 7 | `.venv/bin/python src/amend0b.py` | commit #0b at 22:37:06Z: KeyError fix in the frozen analysis (deviation D10) | <1 min |
| 8 | `src/chain6.sh <pid of 5>` | `gen6.py forced_topup` (+620 forced programs for the 31 algorithms with < 10 kept, 22:25-22:37) → `qlik6.py select` (CPU) → `gen6.py ptfs` (stopped by PID after 100 T2 draws; deviation D11) | 20 min |
| 9 | `src/chain6b.sh` | `gen6.py ptfs --tasks R6,T04,T05,T10,T03,T11,T1,T2,T06,R1,T08,R3,T13,T14,R2 --bc-tasks <8 push units> --max-stage B` (22:46-23:26); `forecasts6.py draft`; `qlik6.py score` (bf16 teacher forcing + fp32 10% subsample, 23:26-23:34) | 48 min |
| 10 | `src/chain6c.sh <pid of 9>` | `gen6.py ptfs ... --max-stage C` (23:34-23:47); `audit6.py pt` (23:47-23:50); `forecasts6.py commit1` (commit #1 at 23:50:52Z); `gen6.py push6` (23:50-00:05) | 31 min |
| 11 | `.venv/bin/python src/audit6.py it_regate` | it-model style re-gate (30 programs; run at 22:52, between steps 9 and 10) | 1 min |
| 12 | `.venv/bin/python src/final6.py` | events and the L1 contest with the frozen analysis (`predictions/analysis_L_gemma.py`, sha256-checked against the chain) | 2 min |
| 13 | `.venv/bin/python src/audit6.py novelty` | novelty audit | 2 min |
| 14 | `python3 -I audit/rederive_l1.py` | independent stdlib re-derivation and placebos (system Python, no venv) | 2 min |
| 15 | `.venv/bin/python src/bookkeeping6.py` | costs, timing, deviations, chain verification, verdicts, figures, `method_out.json`, `results/report6.md`, `README.md` | 2 min |
| 16 | `aii_json_format_mini_preview.py --input method_out.json --format exp_gen_sol_out` | `full_`, `mini_` and `preview_method_out.json` | <1 min |

`method.py` runs the same stages in the same order and is resumable, so the hand-off scripts are not needed:
- every generation stage skips rows whose `row_id` already exists;
- `.venv/bin/python method.py --from final` re-runs the CPU analysis only.

The GPU time was 1.96 hours of generation batches (`results/timing6.json`) plus about 8 minutes of teacher forcing.
That produced 9,350 programs and 4,836 teacher-forced passes.

**Seeds and slots.** All are frozen in commit #0 (`predictions/protocol_G6.json`):

| Rows | Seed or uniform stream |
|---|---|
| CRN uniforms per (task, template, slot) | `PCG64(stable_seed('iter5E', task, W, slot))` |
| Twin T 1.0 | slots 0-9 are exp28's rows; slots 10-39 are new |
| Twin T 1.3 | slots 0-19, with the same uniforms as T 1.0 |
| Fresh FD directions | seeds 63001-63008: `PCG64(seed)` standard normal, normalised |
| Fresh PN directions | `PCG64(stable_seed('iter6G-PN', task, W, slot))` |
| Few-shot pt draws | `PCG64(stable_seed('iter6G-ptfs', task, k))` |
| Forced programs | `PCG64(stable_seed('iter6G-forced', task, algorithm, k, j))` |
| Audit samples | `random.Random(60)` (round 1), `random.Random(61)` (re-audit), `random.Random(62)` (it re-gate) |

**Configs.**
- Decoding: T 1.0 (twin T 1.3 arm), top-p 1, no top-k.
- Caps: 1,024 new tokens (bench), 1,536 (path tasks), 768 (few-shot plain completion).
- Push: α 2 in exp28's outlier-excluded ban-free unit, at blocks 11-22 × the task-spec positions, during the prefill
  only.

## 5. What a reader should get

| File | Contents | Headline values |
|---|---|---|
| `results/verdicts6.json`, `results/l1_contest.json` | pooled L1 contest (15 events, all clear landings) | see the bullets below |
| `results/old_tally.json` | the 7 iteration-5 events rescored | repaired r_u 5/7 (5/6 defined; T03 undefined); t_u 5/5 defined; q_lik 6/7 |
| `results/rederive_l1.json` | stdlib re-derivation | 36 values compared, 0 mismatches; random-r_u placebo 1.75%, random q_lik top-1 4.25% |
| `results/pt_label_audit6.json` | pt audit | round 1 0.864 (κ A–B 0.909), r_u stratum 0.702; AUDIT_FAIL T2, R1, R3, R2 |
| `results/engine_check6.json` | engine check | label agreement 0.9875, JS 0, byte identity 0.906 |
| `results/commit_chain.json`, `results/integrity6.json` | pre-registration | chain ok; commit #1 (23:50:52Z) before the first push row (23:52:40Z) |
| `method_out.json` (+ `full_`, `mini_`, `preview_`) | exp_gen_sol_out | 5 datasets: 48 event records, 2,300 pt, 3,750 twin, 66 q_lik, 1,200 push programs |

Pooled L1 contest (`results/verdicts6.json`, `results/l1_contest.json`):
- r_u hits 11/13, p = 5.8e-5. t_u hits 10/10 and q_lik top-1 hits 13/15.
- L1a is 5/5, which is DESCRIPTIVE (fewer than 6 events). L1b splits 2–2, sign p = 0.69.
- Log score q_base − q_tail is −0.44 nats (primary) and +0.19 with an equal 'other' bin. q_base − q_lik is −0.39
  (primary) and +0.36 with an equal 'other' bin.

These numbers are the iteration-6 Gemma replication of Claim L. The README's Results section and the run's report cite
them from `results/verdicts6.json` and `results/report6.md`.

Sources of residual nondeterminism:
- **Batch shape.** The CRN sampler is deterministic for a fixed batch shape. A slot regenerated in a different shape
  can change tokens: 8/10 R6 push slots kept their label in the engine check, and all 150 twin slots did.
- **Batch-1 teacher forcing.** It is deterministic on the same GPU type. bf16 against fp32 moves a 48-token window by a
  median of 0.24 nats, with no top-1 flip.
