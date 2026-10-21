# Reproducing panel A (iteration 5, Step 2)

This file records what was actually run, in the order it was run, and what a reader should get. Every path is
relative to the folder that holds this file.

## 1. Get the artifact

This folder is one folder of a public GitHub repository. Clone the repository, then `cd` into the folder that contains
this `reproducibility.md` (and `method.py`, `pyproject.toml`).

```bash
git clone <repository-url>
cd <repository>/<this-folder>
```

The folder ships every input it needs, copied with a sha256 manifest (`inputs/MANIFEST.sha256`):

* `inputs/exp11/bench`, `inputs/exp8/suite`: the iteration-2 bench and path suite with their frozen labellers.
* `inputs/exp19`, `inputs/exp22`, `inputs/exp23`, `inputs/exp13`, `inputs/exp17`, `inputs/exp18`: the iteration-3/4
  engine, prompts, push units, directions and known solutions.
* `inputs/eval3/screen.json`: the frozen screen.
* `inputs/dep_dataset`: the extracts of the dependency dataset `art_j3Rm_lr2nzR6` that this artifact uses.
* `inputs/step1`: Step 1's committed `commit1.json` and its `commitments.log` (sha256 `6adc77a5…`).

The user-upload folder of this run was empty, so no private user input is involved.

## 2. System, Python and libraries (as used)

* OS: Debian GNU/Linux 12 (bookworm) container on Linux 6.8. Any recent Ubuntu works the same way.
* GPU: 1 × NVIDIA GeForce RTX 4090, 24 GB (23.52 GiB visible), driver 595.91.07. The PyTorch wheel is CUDA 12.8
  (`torch==2.8.0+cu128`). CPU: 14 cores (cgroup quota 13.6). RAM: 55 GB (container limit).
* Precision rule (`predictions/precision_rule.json`, committed before any sample): ≥ 19.5 GiB of VRAM → bf16 HF
  for both models. A 16 GB GPU would select FP8 W8A8 instead, which gives different numerics.
* Python 3.12.14, managed with `uv`. A plain `python3.12` must also be on `PATH`: the sandbox runs candidate programs
  in fresh `python3.12 -I -S` subprocesses. `BENCH_SANDBOX_PYTHON` overrides the interpreter.
* Exact environment: `pyproject.toml` and `requirements.lock.txt`, 77 packages pinned (`uv pip freeze`; the uv venv
  has no pip binary). Key pins: torch 2.8.0, transformers 4.57.6, accelerate 1.15.0, numpy 2.2.6, scipy 1.18.1,
  zss 1.2.0, openai 3.35.1, loguru 0.7.3, matplotlib 3.11.2.

```bash
sudo apt-get install -y python3.12      # the sandbox interpreter (or point BENCH_SANDBOX_PYTHON at one)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r requirements.lock.txt
```

## 3. Downloads, environment variables and keys (names only)

Models (public Hugging Face repositories, about 16 GB each in bf16):

```bash
.venv/bin/huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218
.venv/bin/huggingface-cli download Qwen/Qwen3-8B-Base --revision 49e3418fbbbca6ecbdf9608b4d22e5a407081db4
```

Environment variables (all optional except the OpenRouter pair):

* `OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY`: the LLM judges (gold sets, label disagreements, base audits, novelty
  audit). Verdicts are cached in `data/judge_cache*.jsonl`, keyed by (judge, unit, code sha256), so re-labelling the
  same programs makes no new calls.
* `HF_HOME` / `HF_HUB_CACHE`: model cache location. `HF_TOKEN` is not needed for these public models.
* `ART_J3RM_DIR`: the dependency dataset `art_j3Rm_lr2nzR6`. The default is its sibling folder `../art_j3Rm_lr2nzR6`.
  It is needed only to re-extract `inputs/dep_dataset`. The raw LeetCodeDataset snapshot comes from that artifact's
  `restore.sh` (`temp/datasets/leetcodedataset/`).
* `STEP1_COMMIT_FILE`: Step 1's `commit1.json`. The default is the shipped copy `inputs/step1/commit1.json`.
* `AII_DATA_FIG_GEN_SCRIPTS`: the `scripts/` folder of the aii-data-fig-gen chart tools. These are not part of this
  repository and are needed only to re-render `figures/`; the rendered figures and their JSON specs ship in
  `figures/`.

Judge models used, all at temperature 0:

* google/gemini-2.5-flash, openai/gpt-4.1-mini and deepseek/deepseek-chat-v3.1 (third vote): the new units.
* google/gemini-2.5-flash-lite: the iteration-2 frozen judge j1, used on the existing bench tasks.
* openai/gpt-4.1-mini: the path tasks.

Total spend: USD 0.35 (`results/costs.json`).

## 4. Commands, in the order they were run

All seeds are fixed in code:

| What | Seed or key |
|---|---|
| Escape directions | `ESC_SEEDS = 95101..95108` (`rand_dir`: PCG64 standard normal, normalised) |
| CRN uniforms | `u_stream(task, w, k) = PCG64(stable_seed(task, w, k))`, shared by every arm and both models |
| Plan-noise directions | `stable_seed('i5A', 'PN', task, alpha, w, k)` |
| Test generation | `random.Random('i5A|tests|<unit>')` |
| Twin nouns | `stable_seed('i5A', 'noun', unit)` |
| Bootstraps | `BOOT_SEED = 20261021` |

Wall-clock times are from this run.

```bash
# Stage 0 (CPU, ~1 min): precision rule, model ids, LeetCode I/O pairs, dataset extracts, seed check, manifest
.venv/bin/python src/stage0.py
# Stage 2a (~1 min): freeze the A1-A7 specs, pick twin nouns, render and audit every prompt
.venv/bin/python src/specs5.py
# CPU tests (~10 s)
.venv/bin/python -m pytest -q -c pytest.ini tests
# First GPU jobs (tests, engine check, twins, novelty, states, base repertoire, plain completion), then the workers
.venv/bin/python src/manual_steps.py enqueue_initial
.venv/bin/python src/gpu_worker.py &          # long-lived; loads one model at a time (5 loads in this run)
.venv/bin/python src/label_worker5.py &       # labels every raw row once its unit's labeller is frozen
# Commit #0 (protocol, thresholds, seeds, analysis-code sha256) and #E (frozen screen): precede every push sample
.venv/bin/python src/manual_steps.py commit0
.venv/bin/python src/controller.py &          # Extra arm A, push arms after each UNIT_<u> commit, escape top-ups
# Per unit, in order A1 A2 A3 A4 A5 A6 A7 (~5-15 min each): build, gate round 0, freeze, commit
.venv/bin/python -m newbench.common.build5 A1
.venv/bin/python -m newbench.common.gate5 A1
.venv/bin/python src/freeze_unit.py A1 round0
.venv/bin/python src/unit_commit.py A1        # waits for twin/base/novelty labels, association + margin jobs
# A6: round 0 failed; rules revised once, then the holdout round (also failed -> GATE_FAIL, excluded)
.venv/bin/python -m newbench.common.gate5 A6 --holdout && .venv/bin/python src/freeze_unit.py A6 holdout
# Logged extension: reserves A8, A9 (prompts rendered after the planned work had finished)
.venv/bin/python src/manual_steps.py extension
#   A8: build5 / gate5 / freeze_unit round0 / unit_commit, as above
#   A9: build5 / gate5 (failed) / rules revised once / gate5 --holdout (passed) / freeze_unit A9 holdout / unit_commit
# Engine-check T2 twin cell re-run (deviation D-ec-T2-twin)
.venv/bin/python src/manual_steps.py ec_rerun
# After every row was labelled: stop the workers (touch queue/STOP queue/STOP_LABEL), then
.venv/bin/python method.py final
#   = fix_validity, novelty_audit, final_run (frozen analysis on both unit sets + 'half + screen'), assoc_fix (POST HOC),
#     engine_check, recheck (labeller re-check of the 15 existing labellers), external_refs, outputs5, figures5,
#     report5, audit/rederive.py, verify_chain
python3 -I audit/rederive2.py                 # second independent re-derivation + placebos
```

Timeline of this run:

* 11:53 UTC: stage 0.
* 12:14: commits #0 and #E.
* 12:34 to 13:03: the unit commitments A1 to A7.
* 13:10: all planned sampling done.
* 13:14 to 13:35: the extension A8/A9.
* 13:35 to 14:25: analysis and outputs.

GPU batch time was 0.98 h over 8,620 sampled rows (`results/timing_summary.json`).

Notes on exactness:

* bf16 numerics depend slightly on batch composition. Re-running a batch with the same shape on the same GPU type
  reproduced every row byte for byte (GPU test U1). A different GPU or batch shape can change individual rows, so the
  statistics will match only within sampling error.
* The LLM judges run at temperature 0, but the providers' models can drift. Use the cached verdicts in
  `data/judge_cache*.jsonl` to reproduce the labels exactly.
* `method.py setup` re-runs stage 0 and the spec freeze. Use it only in a fresh clone that is meant to redo the
  study: in this folder it would overwrite files already hashed in `commitments.log`.

## 5. What a reader should get

* `results/summary.md`: every number below, generated from the result files.
* `audit/rederive_report.json` and `audit/rederive2_report.json`: 0 mismatches each, with the placebos.
* `python src/verify_chain.py`: 144 lines, 0 chain breaks.

| Result | Value | File |
|---|---|---|
| A1, primary set (A1–A5, A7): ρ(β, E), exact one-sided p | −0.03, 0.56 | `results/a1.json`, fig 1 |
| collapsed-immovable / diverse-immovable shares | 1/1, 2/5 | `results/a1.json` |
| rival ρ(merit runtime, E), ρ(twin modal share, E) | −0.88, −0.70 | `results/a1.json`, fig 5 |
| A1 with the extension (8 units): ρ, p | −0.33, 0.80 | `results/a1_with_extension.json` |
| A2: hits r_u = L_u, Poisson-binomial p | 3/3, 0.019 | `results/a2.json`, fig 3 |
| A2 log scores (base / corrected association / proximity), A1 A3 A7 | −0.06/−0.27/−1.64, −0.05/−0.14/−1.12, −0.63/−2.87/−0.95 | `results/a2_assoc_corrected.json` (POST HOC) |
| 'half + screen' (21 units): ρ, p; existing tasks only | 0.54, 0.0065; 0.59, 0.0096 | `results/half_screen.json` |
| Extra arm A: E for T03 / T10 / the other 13 tasks | 0.25 / 0.125 / 0 | `results/extra_arm_a.json`, fig 4 |
| Per-direction escape outcomes | 16 cells per unit | `results/unit_summaries_with_extension.json`, fig 2 |
| Engine check, per-slot label agreement (T03 twin, T03 push, T2 twin, T2 push) | 1.00, 0.74, 0.98, 0.86 | `results/engine_check.json` |
| Novelty audit | 2 correct 'other' of 6,854 correct, 0 novel | `results/novelty_audit.json` |
| Gates | A1–A5, A7, A8 gated at round 0, A9 after one revision, A6 GATE_FAIL | `results/units_gate.json` |

The paper's panel-A results section is written by a later step from `method_out.json` and these files. Figures 1–5
in `figures/` are the panel-A figures it draws on.
