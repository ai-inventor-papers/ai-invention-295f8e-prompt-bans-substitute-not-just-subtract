# Reproducing "Where noise must go to change the idea"

This file records what was actually run on 2026-10-21 (UTC), in the order it was run, including the incremental
steps. Every path is relative to this folder. Clock times below are UTC on the day of the run.

## 1. Get the artifact

This folder is one folder of a public GitHub repository. Clone the repository and `cd` into this folder, the one
that holds `method.py`, `README.md` and `pyproject.toml`:

```bash
git clone <repository-url>
cd <repository>/<this-artifact-folder>
```

Everything the code reads from earlier artifacts of this run is already in `inputs/`, as read-only copies with
sha256s in `inputs/SHA256SUMS`:

| Folder | Source artifact | What is used |
|---|---|---|
| `inputs/exp17` | `art_pVlCZ272hDV7` | engine, hooks, prompts, `prompts/prompts.jsonl`, fixed directions `rand_9002`/`rand_9004`, FP8 units, the screen rows `data/labels.jsonl` |
| `inputs/exp13` | `art_1AYTO1Epb_7t` | FP8 units (cross-check), `data/samples.jsonl` (screen rows) |
| `inputs/exp11` | `art_0ndRfWKBWclR` | frozen bench (T03/T05/T06/T10 specs, hidden tests, labellers, gold sets, `commitment.json`) |
| `inputs/exp8` | `art_8_ULPE8jJQc_` | canonical T1/T2 suite (hidden tests, harness, tracer, labeller) |
| `inputs/exp9` | `art_IVZc3TWCeE9f` | forced prompts, extended / K=7 labeller, catalogue keep rule |
| `inputs/exp7` | `art_6zBfl3kDjeiP` | forced paraphrases (`prompts/prompts_v2.json`) |
| `inputs/exp18` | `art_ccAbfJVcv0LO` | novelty-audit builder and judges, `known_solutions_summary.json` |

The one declared dependency, the dataset artifact **`art_j3Rm_lr2nzR6`**, is not copied (96 MB). It is read through
ONE setting: the environment variable `ART_J3RM_DIR`. Its default is the sibling folder `../art_j3Rm_lr2nzR6`, which
is where the repository publishes it. Only `src/audit.py` reads it: the known-solution index and the dependency-usage
summary. No user-uploaded (private) file was used; the run's upload folder was empty.

## 2. System, Python and libraries

Hardware actually used:

- 1 x NVIDIA RTX 2000 Ada Generation, 16 GB VRAM, compute capability 8.9 (driver 595.91.07, CUDA 13.2 driver
  runtime);
- 6 CPU cores (cgroup quota 5.1);
- 28 GB RAM container limit, Debian 12 container (Ubuntu 22.04/24.04 works the same way).

The engine quantises Qwen3-8B's decoder linears to FP8 E4M3 at load time and multiplies with `torch._scaled_mm`. That
needs a GPU with FP8 support (compute capability >= 8.9) and >= 16 GB. Nothing is compiled, and no system packages
are needed beyond a standard Ubuntu image. The stress tests and labellers run candidate programs with the system
CPython 3.12 (`/usr/bin/python3.12` or `/usr/local/bin/python3.12`; override with `SANDBOX_PYTHON`) in isolated mode
(`-I -S`).

Python 3.12.14 and uv 0.6.14. All 83 packages are pinned in `pyproject.toml` (equal to `uv pip freeze` of the `.venv`
actually used; the uv venv has no `pip` binary), and `uv.lock` was produced by `uv run`. Key pins: torch 2.8.0
(cu128 wheel), transformers 4.57.6, numpy 2.2.6, scipy 1.18.1, scikit-learn 1.9.1, statsmodels 0.15.0, ripser 0.6.15,
openai 3.35.1, ijson 3.4.0.

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
```

## 3. Model, data and environment variables

The model is read from the Hugging Face cache named by `HF_HUB_CACHE` (or `HF_HOME`):

```bash
huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218
```

Environment variables (names only):

- `HF_HUB_CACHE` / `HF_HOME`: the model cache.
- `OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY`: used in two places, both for judges.
  - Labelling: blind judges called only when the runtime and AST labels disagree (gpt-4.1-mini for T1/T2 and the K=7
    labeller; gemini-2.5-flash-lite for bench tasks).
  - The novelty audit: gemini-2.5-flash-lite and gpt-4.1-mini, with deepseek-chat-v3.1 as tie-break.
  - Every answer is cached (`data/judge_cache*.jsonl`, `data/k7_judge_cache.jsonl`, `data/llm_cache_audit.jsonl`), so a
    rerun on identical programs makes no paid call. Spend in this run: USD 0.19.
- `ART_J3RM_DIR` (optional): see section 1.
- `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` (set by `method.py` for the GPU stages).
- `SANDBOX_PYTHON` (optional): see section 2.

## 4. Commands, in the order they were run

Seeds and keys (all deterministic; `stable_seed(*parts)` = sha256 of the '|'-joined parts, mod 2^63):

- token uniforms: `u_stream(task, template, k)` (exp17's key);
- random directions: `PCG64(stable_seed('PN4', task, template, k)).standard_normal(4096)`, normalised;
- bootstrap streams: seed 1000 + task index;
- hull draws: seed 0;
- rarefaction: seed 0;
- placebos: seeds 0/7/12345.

Sampling settings: temperature 1.0, top-p 1, no top-k, thinking off, at most 1,024 new tokens, fence stop, and a
fixed batch of 20 rows of one (task, template).

1. **Environment and inputs**, about 10 min. Create `.venv` (section 2) and copy the input files listed in section 1
   (already done in the repository).
2. **GPU driver**, launched once in the background; it holds the model for the whole run:
   `uv run method.py gpu` (= `cd src && python gpu_main.py --stage all --budget-hours 3.3`). Started 03:40.
   - It writes, in order: `results/hardware.json` (precision rule -> `fp8_w8a8`); `results/positions.json`;
     `units/units_<task>.npz` (03:43, about 20 s); `results/engine_dirs.json`; the C3d geometry
     (`directions/u_top5.npz`, `directions/plan_geometry_T1.npz`, 03:45, about 2 min); GPU tests
     (`results/unit_tests_gpu.json`, 03:48, about 3 min).
   - It then waits for commit #0.
3. **Screen file and commit #0** (CPU): `uv run method.py screen` (run twice; identical sha256), then
   `uv run method.py commit0`, at 03:46:50.
4. **Engine check and smoke** (GPU, automatic after commit #0, about 4 min).
   - Engine check: T03 rand_9002 and T2 rand_9004 at alpha 1, k 0-9, with the twin rows k 0-9.
   - Smoke: slots k 100-103 for every arm type on T03 and T1.
   - The driver then waits for commit #1.
5. **Label worker** (CPU, background, concurrent with sampling): `uv run method.py label`.
6. **CPU unit tests**: `uv run method.py tests-cpu` -> `results/unit_tests_cpu.json` (all pass).
7. **Commit #1** (predictions, rules, hull and decision code): `uv run method.py commit1`, at 03:55:02. Decisive
   sampling starts immediately: 260 batches in priority order P1-P9, 4,510 programs + 540 S3 shadow rows + 150 filler
   twin rows, finished at 05:36 (1.69 h; 1.74 GPU-hours of batch time including tests, engine check and smoke).
8. **While sampling ran** (CPU), in this order:
   - commit #2 of the analysis code (04:16);
   - `python src/recheck.py` (inputs `SHA256SUMS`, bench vs `commitment.json`, labeller re-check);
   - `python src/audit.py index` (known-solution index: 472 rows matching exp18, + 42 T05 rows);
   - `uv run method.py deps`;
   - `uv run method.py k7`, run incrementally (it is resumable).
9. **After sampling**: `bash tools/post_sampling.sh`, which runs the following.
   - It waits for the label worker to drain.
   - It runs the K=7 labeller on the remaining T1 rows, in parallel with the GPU follow-up diagnostic
     `python tests/u4_diagnostic.py` (about 3 min).
   - Commit #3 of the final analysis code (05:37).
   - `cd src && python analysis.py 2000 5`: 2,000 bootstrap replicates on 5 worker processes, about 17 min.
   - `python src/audit.py run`: stress tests, judge controls, blind judges and tie-break, about 1 min.
10. **Manual pass**: `python tools/manual_view.py --neigh` prints every stress-passing audit program beside its three
    nearest known solutions. The executor read each one and wrote `audit/manual_pass.jsonl`; there is one program.
11. **Summaries, re-derivations and outputs.**
    - `uv run method.py audit-summary`.
    - `python audit/rederive.py`: independent re-derivation + placebos, about 9 min.
    - `python tools/overlap_check.py`.
    - `python src/finalize.py`: deviations, timing, commit-order audit, merged `data/samples.jsonl`.
    - `uv run method.py figures` and `uv run method.py outputs` (`method_out.json`).
    - The aii-json `aii_json_format_mini_preview.py` and `aii_json_validate_schema.py --format exp_gen_sol_out`
      (`full_` / `mini_` / `preview_method_out.json`, all valid).
    - `python audit/rederive_headlines.py`: second re-derivation, about 1 min.
    - `python tools/build_readme.py`.
    - Commit #4 of the final code state (06:13-06:42).

A full rerun from an empty `data/` takes about 2.5 h on this GPU. Every stage skips finished work.

## 5. What you should get

Numbers are from `results/` (and `method_out.json` metadata). They are reported in the README's results section and
belong to the paper's site-sweep (C1-site), boundary (C3c) and top-five (C3d) results.

- **Engine check** (`results/engine_check.json`): 50/50 byte-identical programs to the exp17 screen on T03 rand_9002
  and on T2 rand_9004; JS = 0.000.
- **C1-site** (`results/c1_site.json`, `results/hull.json`, README table; fig 1). H5 per site and task, with S0 best on
  T03 (2.61), T1 (1.29) and T2 (1.66), S3 on T05/T06, and S4 on T10.
  - Count 3 of 6, raw p = 0.0623, verdict **PARTIAL**.
  - P(S0 argmax) 0.59 / 0.38 / 0.31 / 0.33 / 0.67 / 0.97 for T03 / T05 / T06 / T10 / T1 / T2.
- **Inert sites**: 0 correct off-default programs at S1 (of 526) and S2 (of 527); S5 6 of 521.
- **Transmission** (`results/transmission.json`): S0 indicator +2.15 [1.79, 2.51] on the logit at matched
  displacement at R. The hand-computed Mantel-Haenszel re-derivation gives OR 5.72 [3.94, 8.30].
- **Paired flips** (`results/paired_flips.json`, fig 3): e.g. S0 vs S1 at alpha 2 on T10 18:0 (p = 7.6e-6).
- **Boundary** (`results/boundary.json`, fig 5): pass 0.00 at alpha 8 on all six tasks; correct-only Hill peaks at
  alpha 2 (3 tasks) or 4 (3 tasks).
- **Novelty** (`results/novelty_audit.json`): 1 correct 'other' program (T06, `nums.count`) and 0 confirmed novel
  algorithms among 3,555 correct analysed programs (rule-of-three bound 0.08%).
- **C3d** (`results/c3d.json`, fig 6): TOP5 plan push avoidance 0.00 at alpha 1 (30/30 BFS) and alpha 2 (19/19 BFS);
  0 correct at alpha 4.
- **Checks**:
  - `results/unit_tests_gpu.json`: U1, U2, U3, U6 and U7 pass; U4 fails and is explained by
    `results/u4_diagnostic.json`.
  - `results/unit_tests_cpu.json`: all pass.
  - `results/labeller_recheck.json`: 100% reproduced.
  - `results/rederive.json`: 0 mismatches.
  - `results/rederive_headlines.json`: all headlines reproduced, every placebo fails.
  - `commitments.log`: 0 chain breaks, 0 decisive rows before commit #1.

Because sampling uses common random numbers and a fixed batch shape, a rerun on the same GPU type and the same
library versions reproduces the token ids exactly (`results/unit_tests_gpu.json` U1 and the engine check). FP8
numerics are path-sensitive across GPU generations (deviation D4), so on other hardware expect the same
compositions only up to sampling noise.
