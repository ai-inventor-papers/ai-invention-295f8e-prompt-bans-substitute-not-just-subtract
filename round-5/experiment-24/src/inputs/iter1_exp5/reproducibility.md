# Reproducing "Did instruction tuning cause the collapse?" (Qwen3-8B-Base vs Qwen3-8B)

This file describes what was **actually run** to produce the numbers in `README.md`, `results/summary.md` and `method_out.json`,
in the order it was run, and two ways to reproduce it:

* **Level 1 — re-derive every reported number from the published per-sample rows** (CPU only, ~5 minutes, no models, no API key).
* **Level 2 — regenerate everything** (one ≥ 24 GB NVIDIA GPU, ~3.5 h wall-clock, ~$0.21 of OpenRouter judge calls).

All paths below are relative to this folder. Nothing in the code depends on an absolute path (every script anchors on its own location).

---

## 1. Get the artifact

This folder is published as one folder of a public GitHub repository. Clone the repository and enter the folder:

```bash
git clone <URL of the published repository>
cd <repository>/<this folder, e.g. gen_art_experiment_5>
```

Not published (regenerable): `.venv/` (≈14 GB) and `src/__pycache__/`. Model weights were never stored in this folder.
Published and needed for Level 1: `runs/` (all raw generations, labelled rows and the scoring / labelling / judge caches),
`data/` (frozen prompts with token ids, hidden tests, reference implementations), `predictions/` (hash-committed forecast),
`activations/` (residual states, deltas, steering vectors; 4 files of 15 MB, the rest smaller), `results/`.
No user-uploaded inputs were used (the run's upload folder was empty) and no other artifact is read.

## 2. System, Python and libraries

What was used:

| item | version / value |
|---|---|
| OS | Linux 6.8 (Debian 12 container), x86_64 |
| GPU | 1× NVIDIA L4, 23 GB VRAM, driver 580.159.04 (CUDA 13.0 driver; PyTorch wheels built for CUDA 12.8) |
| CPU / RAM | 6 vCPU (cgroup quota 5.1 cores), 57 GB RAM limit |
| Python | CPython 3.12.14 |
| package manager | uv 0.6.14 (the venv has no `pip`; use `uv pip`) |
| key libraries | vllm 0.11.0, torch 2.8.0 (+cu128), transformers 4.57.6, numpy 2.2.6, scipy 1.18.1, pandas 3.0.6, openai 3.35.1, matplotlib 3.11.2, loguru 0.7.3 |
| everything | all 168 installed packages pinned exactly in `pyproject.toml` (copy in `results/pip_freeze.txt`) |

System packages: none beyond a working NVIDIA driver for Level 2 (the container had **no C compiler**, which is why vLLM runs with
`enforce_eager=True`; with a compiler present, eager mode is still what was used and should be kept for identical numerics).

```bash
# install uv if needed: curl -LsSf https://astral.sh/uv/install.sh | sh
./install.sh            # = uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
```

## 3. Downloads, environment variables, keys (names only)

* Models (Level 2 only), at the exact snapshot revisions used:
  `Qwen/Qwen3-8B-Base` @ `49e3418fbbbca6ecbdf9608b4d22e5a407081db4` and `Qwen/Qwen3-8B` @ `b968826d9c46dd6066d109eabc6255188de91218`
  (`./install.sh --models`, ≈ 33 GB; stored wherever `HF_HOME` / `HF_HUB_CACHE` point).
* Environment variables:
  * `OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY` — only for the blind LLM judge (`google/gemini-2.5-flash-lite`, second judge
    `deepseek/deepseek-v4.1-flash`). Level 1 needs neither: every judge answer is cached in `runs/judge_cache.jsonl` and re-used.
  * `HF_HOME` / `HF_HUB_CACHE` (optional) — model cache location; `HF_TOKEN` (optional) — Hugging Face token.
  * `MAX_NUM_SEQS` (optional, default 48) — vLLM concurrency; affects speed only.
  * `AII_JSON_SKILL_DIR` (optional) — path to the AI-Inventor `aii-json` skill, used by `finalize.sh` only for the final schema
    check and the mini/preview files; readers without it can skip those two lines.

## 4. What was run, in order (Level 2)

Seeds are deterministic everywhere and need no flags: vLLM request seeds = sha256(arm, task, condition, prompt id, chunk) (vLLM gives
the n=10 children seed+index); HF steering samples use one CUDA generator per (task, paraphrase, sample) = sha256("steer", task,
prompt id, sample) (the same for every arm → coupled samples); random steering directions `numpy.random.default_rng(1|2)`; hidden tests
`random.Random(12345)` (T1) / `random.Random(54321)` (T2); runtime-labeller inputs `random.Random(7|99)`; bootstrap / permutation seeds
are fixed in `src/analysis.py`; judge temperature 0. Decoding for every arm: T = 1.0, top-p 1.0, no top-k, min-p 0, repetition penalty 1,
max 1024 new tokens, thinking off (`enable_thinking=False`); vLLM uses `generation_config="vllm"` so the model's sampling defaults are ignored.

| # | command (as run) | what it does | time on the L4 |
|---|---|---|---|
| 1 | `.venv/bin/python src/prompts.py` | builds `data/prompts.json`; asserts identical token ids across the two tokenizers for all 120 chat prompts | 1 min |
| 2 | `./run_gen_AB.sh` (background) | vLLM phase A (base: A1 template-free N=200/task, A2 chat N=100/task, A3 template-free ban N=100/task) then phase B (instruct: B1 chat N=200/task, B2 template-free N=100/task); staged 10 → 100 → full | 12 + 7 min |
| 3 | `.venv/bin/python src/tasks.py` | hidden tests (`data/tests/t1.json` 47 cases, `t2.json` 46 cases) | seconds |
| 4 | `.venv/bin/python src/calibrate.py` | per-case limits = max(1 s, 10 × median-of-5 reference time); all 15 references pass with ≤ 0.19 × limit; harness probes | 1 min |
| 5 | `.venv/bin/python src/labeller_gate.py` | both labellers on 15 references + 10 mutants (gate passed after 2 rule-revision rounds, see deviations) | 1 min |
| 6 | `.venv/bin/python src/judge.py` | 5-call judge smoke test | seconds |
| 7 | `./run_acts.sh` | HF forward passes, base then instruct → `activations/`, `results/sharpening_direction.json` | 3 min |
| 8 | `.venv/bin/python src/label_score.py runs/raw_base_tf__baseline.jsonl runs/raw_base_chat__baseline.jsonl runs/raw_base_tf__ban.jsonl runs/raw_instruct_chat__baseline.jsonl runs/raw_instruct_tf__baseline.jsonl` | extract → hidden tests → runtime + AST labels → judge → final label | ~15 min CPU |
| 9 | `.venv/bin/python src/predict_commit.py` | forecast written, sha256 appended to `predictions/hash_log.txt`, committed in `predictions/.commit_git` (2026-10-19T17:15:56Z) | seconds |
| 10 | `.venv/bin/python src/steer_hf.py --stage S` | hook unit tests (`results/hook_tests.json`), S0 c=0 and sharpening c=0.5/1.0/1.5 (N=100/task each), manipulation check | 37 min |
| 11 | `./run_gpu_chain.sh` | phase C (instruct under the ban, N=100/task; refuses to start unless the forecast hash matches), stage R (random directions at c* = 0.5), stage X (single-layer δ₁₈ c=0.25/0.5/1.0 N=50/task; R-only sharpening and R-only random control N=100/task) | 4 + 14 + 31 min |
| 12 | `./run_after_chain.sh` | phase A_EXT: base template-free and base chat extended to N=300/task (new seeds) | 13 min |
| 13 | `./run_after_ext.sh` | validation arm: R-only sharpening without the 512-token no-code rule (20 coupled samples/task) | 7 min |
| 14 | `AII_JSON_SKILL_DIR=<path> ./finalize.sh` | label everything (cached), `src/analysis.py --second_judge`, `src/report.py`, `method.py --assemble`, schema check, mini/preview | ~12 min CPU |
| 15 | `.venv/bin/python audit/rederive.py` | independent re-derivation of the headline numbers + placebo tests → `results/audit_rederive.json` | 2 min CPU |

Notes on what happened during the real run (all logged in `results/deviations.json`):
* Step 10 was first launched without the uniform 512-token no-code stop rule; after two batches showed that the sharpening arms emit
  garbage until the 1024-token cap, it was stopped, the rule was added for every HF arm, the 20 already-generated over-long rows were
  truncated post hoc by the same rule (identical to applying it online, because sampling is coupled), and the stage was relaunched with
  `--skip_tests` (the hook tests had passed). A fresh run applies the rule online from the start.
* Steps 8 and 14 call the judge only for programs not yet in `runs/judge_cache.jsonl`.
* **Single-command equivalent:** `.venv/bin/python method.py --all` runs the computations of steps 1–5 and 7–13 plus the analysis,
  report and assembly of step 14 (each GPU phase in its own process; phase C before stage S, which does not change any result because the
  processes are independent and seeded). It skips the judge smoke test (6), the schema check / mini-preview files (end of 14) and the audit
  (15). Total GPU time ≈ 2.1 h (phase sum), ≈ 2.8 h wall-clock including model loads.

## 5. Level 1: re-derive every number from the published rows (no GPU, no key)

```bash
./install.sh
.venv/bin/python src/analysis.py                 # Hill numbers, bootstraps, permutation tests, verdicts, BUY/PREDICT rows, figures
.venv/bin/python src/report.py                   # results/summary.md (the tables in README.md)
.venv/bin/python method.py --assemble            # method_out.json (+ runs/samples.jsonl)
.venv/bin/python audit/rederive.py               # independent re-derivation + placebo checks -> results/audit_rederive.json
```

`src/analysis.py` without `--second_judge` makes no API calls (the second-judge κ is then simply omitted; its value from the real run
is in `results/analysis.json` / README). To recompute labels or test outcomes from scratch instead of the caches, delete
`runs/score_cache.jsonl`, `runs/rt_cache.jsonl` (CPU only) and/or `runs/judge_cache.jsonl` (needs the OpenRouter key) and run
`.venv/bin/python src/label_score.py`. Bit-identical vLLM samples additionally need the same GPU type, driver and library versions
(bf16 numerics and batching); on other hardware the generations differ token-by-token but should match statistically.

## 6. What you should get

Headline numbers (all in `README.md` → *Results*, `results/summary.md`, and `method_out.json → metadata`; re-derived independently in
`results/audit_rederive.json`). This artifact is an experiment screen; a later paper step cites these values from the listed keys.

| claim | value | where |
|---|---|---|
| instruct chat collapse | T1 BFS 200/200 (Hill_cc 1.00); T2 Dijkstra 193/200 (Hill_cc 1.16 [1.03, 1.31]); pass 100 % | `metadata.arms["instruct_chat|t1"]`, `["instruct_chat|t2"]` |
| base model, chat template (N=300/task) | T1 BFS 49/57 correct (Hill_cc 1.58); T2 Dijkstra 63/90 (Hill_cc 2.09) | `metadata.arms["base_chat|t*"]` |
| base model, template-free (N=300/task) | pass 5 % / 8 %; T1 BFS 12/15 (1.65); T2 Bellman-Ford 16/25 (2.18) | `metadata.arms["base_tf|t*"]` |
| weights contrast D_weights | T1 −0.58 [−1.01, −0.15]; T2 −0.93 [−1.38, −0.46]; modal-share gap 14.0 / 26.5 pp | `metadata.collapse_screen.t*.D_weights_cc`, `.verdict_cc` |
| pre-registered verdicts | T1 MIXED (modal gap 14.0 < 15 pp), T2 INSTALLED_BY_POST_TRAINING → alternate passes the screen | `metadata.collapse_screen` |
| sharpening steering | 0/100 parseable at c = 0.5, 1.0, 1.5 (both tasks) → DESTRUCTIVE; S0 100/100 pass | `metadata.steering.t*.knob_verdict` |
| single-layer fallback | c=0.25: pass 94 % / 98 %, no algorithm change → NO_EFFECT_WITHIN_BARS | `metadata.steering.t*` |
| forecast (hash-committed) | top-1 hit on both events (DFS, Bellman-Ford); log score −0.47 / −0.22 vs uniform −1.63 / −1.41 | `metadata.rows.PREDICT` |
| prompting baseline | ban:Dijkstra raises T2 Hill_cc 1.16 → 1.99 at 0 pp pass loss | `metadata.rows.BUY` |
| labeller QA | AST 100 % on references; κ runtime–AST 0.77; inter-judge κ 0.93 | `metadata.labeller_qa` |

Bootstrap CIs depend only on the fixed seeds and the rows, so Level 1 reproduces every number above exactly.
