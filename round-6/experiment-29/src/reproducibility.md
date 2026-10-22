# Reproducing this artifact

All paths below are relative to this folder. It reproduces what was actually run on 2026-10-22.

## 1. Get the artifact

```bash
git clone <the published repository>   # this workspace is one folder of it
cd <this folder>
```

- **Shipped inputs.** The verified copies of every earlier-artifact input ship with this folder: `vendor/` (code,
  prompts, directions, units, labellers; `vendor/SHA256SUMS`) and `inputs/` (iteration-4/5 rows and results;
  `inputs/MANIFEST.json`). `src/setup_inputs.py` re-creates them from the source artifacts, which are needed only to
  re-verify:
  - art_SHaWv77P1XCI (iteration-4 exp22);
  - art_mWn-MQEnNelg (exp19);
  - art_jR6Pyy3W9xum (exp27);
  - art_hG0QPiaIPNhP (exp28);
  - art_8WbrpoEFslk9 (exp25).
- **Location of the source artifacts.** `setup_inputs.py` reads them from `AII_ITER45_ROOT`, which defaults to the
  sibling folder `../iter45_sources`. Inside it, the expected layout is `iter_4/gen_art/gen_art_experiment_{19,22}`
  and `iter_5/gen_art/gen_art_experiment_{25,27,28}`.
- **Declared dataset.** The dataset art_j3Rm_lr2nzR6 is read only by `src/known6.py`, from `AII_DEP_ART_J3RM`
  (default: the sibling folder `../art_j3Rm_lr2nzR6`).
- **No private inputs.** No user-uploaded file is used.

## 2. System, Python, packages

- **System.** Ubuntu with an NVIDIA driver, run with driver 595.91.07 / CUDA 12.8 wheels. Python 3.12 (3.12.14
  was used) and `uv`.
- **Hardware used.**
  - One NVIDIA RTX 2000 Ada (sm_89, 16 GB); FP8 tensor cores are needed for engine a's native kernel.
  - A 5.1-CPU cgroup quota and a 31 GB RAM limit.
  - No C compiler was installed, so the optional Triton W8A16 kernel fell back to the reference implementation.

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r pyproject.toml     # 82 packages, all pinned (torch==2.8.0+cu128 wheel set,
                                                               # transformers==4.57.6, nvidia-cublas-cu12==12.8.4.1)
```

## 3. Model, keys, environment

- **Model.**
  `hf download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218` puts the bf16 safetensors (16 GB)
  in the HF cache. The code finds the snapshot through `HF_HUB_CACHE`.
- **Labeller judges.** Set `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY` (names only). The judges are
  openai/gpt-4.1-mini for T2 and google/gemini-2.5-flash-lite for T10, called only when the runtime and AST labels
  disagree. Total spend was USD 0.085 against a USD 0.40 cap.
- **Optional.**
  - `AII_JSON_SKILL_DIR` points `finalize.sh` at the aii-json validator; without it, that step is skipped.
  - `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` is needed for the bf16 weight set (set by `method.py`).

## 4. Commands, in the order run

No free randomness is involved:
- every CRN slot uses `u_stream(task, template, k)` (PCG64 of `stable_seed`);
- directions are `rand_<seed>` (seeds 9101–9140; 9004 positive control);
- PN directions use exp19's `stable_seed(task, arm, template, k)`;
- the analysis placebos use seeds 7 and 11.

| # | command | what | runtime here |
|---|---|---|---|
| 1 | `.venv/bin/python src/setup_inputs.py` | copy + sha256 inputs (optional; copies ship) | 30 s |
| 2 | `.venv/bin/python src/cpu_gates.py` | gates C1–C5, iteration-4 relabel → `results/cpu_gates.json` | 30 s |
| 3 | `.venv/bin/python src/make_commit0.py` | COMMIT #0 → `predictions/commit0.json`, `commitments.log` | 1 s |
| 4 | `.venv/bin/python src/label_worker6.py &` | labeller, background, for steps 5–8 (stops on `data/STOP_LABELLER`) | concurrent |
| 5 | `.venv/bin/python src/gpu_q.py --phase q1` | unit tests U1–U5, engine-a REPRO (byte identity vs exp22), exp19 PN check | 8 min |
| 6 | `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True .venv/bin/python src/gpu_b.py --deadline-min 180 --cap 448` | engines d and c: twins, α-2 screen and confirmations, POSCTRL, PN, diagnostics (B = 7 from the memory probe) | 2 h 38 min |
| 7 | `.venv/bin/python src/gpu_q.py --phase q2 --deadline-min 70` | engine b (W8A16, B = 20): twins, screen, PN, diagnostics, confirmations | 70 min |
| 8 | `.venv/bin/python src/gpu_q3.py --deadline-min 13`, then again with `--deadline-min 7` | finish engine b's confirmations (resumable) | 21 min |
| 9 | `./finalize.sh` | analysis, nearest-known pass, re-derivation, figures, `method_out.json` + mini/preview, README tables | 1 min |
| 10 | `python3 -I src/audit_headlines.py` | independent headline audit from raw rows, with placebos | 10 s |

Notes on the table:
- Steps 6–8 ran unattended through `logs/chain.sh`, `logs/chain2.sh` and `logs/chain3.sh`.
- `uv run method.py all` chains steps 1–9 with default deadlines.
- Each GPU step resumes from its done-slot keys, so rerunning one only fills missing slots.

## 5. What you should get

- **Headline verdict.** `results/verdict.json` gives NOT_REPRODUCED_HIGH on T10 and on T2: bf16 escapes nearly as
  often as iteration 4's FP8 engine, at the same absolute dose. Escape fractions at α 2 out of 40 directions:

  | task | a W8A8 | b W8A16 | c W16A8 | d bf16 |
  |---|---|---|---|---|
  | T10 | 0.725 | screen 0.70, confirmation incomplete | 0.600 | 0.650 |
  | T2 | 0.200 | 0.125 | 0.150 | 0.150 |

- **Engine a = iteration 4.** `results/repro_bytes.json` gives 400/400 REPRO rows and 40/40 PN rows byte-identical to
  iteration 4.
- **Per-slot T10 boost.** `results/slot_flips.json` gives T10 screen-slot off-default 0.583 (a) vs 0.532 (d), exact
  McNemar 30:10, p = 0.0022; T2 shows no difference.
- **PN.** `results/pn.json` gives T10 α 2: a 30/50, b 27/50, c 22/50, d 25/50.
- **Checks.**
  - `results/rederive.json` and `results/audit_headlines.json` contain the independent recomputations. They match;
    the engine-swap placebo is non-significant.
  - `commitments.log` verifies with `.venv/bin/python src/commit6.py`.
- **Where the numbers appear.** The README "Results" section and its generated tables (`results/report_tables.md`)
  carry every number, and `figures/` holds the plots.
- **Bitwise reproduction.** Exact token streams reproduce only on the same GPU model, driver and pinned wheels.
  Elsewhere, population-level numbers should agree within sampling error.
