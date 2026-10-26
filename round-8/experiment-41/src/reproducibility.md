# Reproducibility: Qwen3-8B algorithm-choice circuit (K3)

This file was written after the run, from what the workspace holds: `method.py`, `src/*.py`, `run_*.sh`,
`pyproject.toml`, `README.md`, `logs/`, `results/stage_timing.jsonl`, `predictions/hardware.json` and the result files.
Every path below is relative to this folder.

## 1. Get the artifact

```bash
git clone <URL of the published repository>
cd <repository>/gen_art_experiment_41      # this folder
```

The repository URL was not recorded in the workspace.

## 2. System, Python and libraries

* OS: Ubuntu (Linux 6.8 kernel). The exact Ubuntu release was not recorded. You need `uv` and an NVIDIA driver that
  supports CUDA 12.8 (the run used driver 595.91.07).
* Python **3.12.14** (`requires-python = "==3.12.*"`).
* Every library is pinned in `pyproject.toml` to the exact version installed in the run's `.venv`. Key pins:
  `torch==2.8.0` (PyPI CUDA 12.8 build, `+cu128`), `transformers==4.57.6`, `accelerate==1.15.0`,
  `huggingface-hub==0.36.2`, `tokenizers==0.22.2`, `safetensors==0.8.0`, `numpy==2.2.6`, `scipy==1.18.1`,
  `scikit-learn==1.9.1`, `statsmodels==0.15.0`, `pandas==3.0.6`, `matplotlib==3.11.2`, `networkx==3.7`,
  `openai==3.35.1`, `loguru==0.7.3`, `triton==3.4.0`. The `nvidia-*-cu12` wheels are pinned there as well.

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
```

## 3. Model, data and keys

* Model: `Qwen/Qwen3-8B` at revision `b968826d9c46dd6066d109eabc6255188de91218`. It runs in bf16 with thinking off.
  Download it into the Hugging Face cache with:
  ```bash
  .venv/bin/python src/download_model.py     # writes predictions/model_revisions.json
  ```
  `src/k3cfg.py:model_path` uses the snapshot under `$HF_HUB_CACHE` when that variable is set. Otherwise it loads by
  model id from the default HF cache.
* Environment variables, by name only:
  * `HF_HUB_CACHE` (optional).
  * `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` (set by `run_chain3b.sh`, `run_chain5.sh`, `run_chain6.sh` and
    `run_chain7.sh`).
  * `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY`, needed only by `src/novelty_k3.py`, the LLM-judge novelty audit.
    The run recorded `openrouter_usd = 0.0` in `results/summary.json`.
* Inputs from earlier artifacts are vendored read-only under `inputs/` (exp34, exp35, exp38, iter2_exp7,
  iter2_exp11, iter3_exp18, iter4_exp22, iter5_exp25, iter5_exp26, iter6_exp29, iter6_exp30, dep_*.json). Their
  hashes are in `inputs/SHA256SUMS` and `inputs/input_hashes.json`, and the code reads them through
  `INPUTS = ROOT / "inputs"` in `src/k3cfg.py`.
* **Portability caveat: some paths are still absolute.**
  * `method.py` `stage_enginecheck` (lines ~1676-1688) reads
    `.../round-7/experiment-35/src/data/labels.jsonl` and `samples_raw.jsonl`, plus
    `.../round-7/experiment-34/src/data/labels.jsonl`, by absolute `/ai-inventor/...` paths. These are the
    iteration-7 artifacts **gen_art_experiment_35** and **gen_art_experiment_34**.
  * `src/novelty_k3.py` reads `full_data_out.json` of artifact **gen_art_dataset_1** (from a different run, iter_1)
    by an absolute path.
  * `run_final.sh` calls the `aii-json` skill scripts at `../../../tools/aii-json`, which are not part
    of the repository.

  To rerun these steps, point those constants at the sibling artifact folders in the published repository, or skip
  the steps. Their outputs are already saved (`results/engine_check.json`, `results/novelty_audit.json`).
  No user-uploaded private input is used.

## 4. Commands, in the order run

Hardware (`predictions/hardware.json`): one **NVIDIA L4, 23 GB VRAM** (23034 MiB), 6 CPUs, ~62 GB RAM limit,
CUDA 12.8, torch 2.8.0+cu128. Total GPU time recorded: **8464 s (~2.35 h)** (`gpu_seconds_total` in
`results/summary.json`). The logs span 01:21 to 04:20 UTC on 2026-10-23, about 3 h of wall time. The time per stage
is in `results/stage_timing.jsonl`. The longest stage was `validate:C1nat` at 2262 s.

Seeds (fixed in `src/k3cfg.py`):

| constant | value | used for |
|---|---|---|
| `SEED_HELDOUT` | 8301 | held-out prompts |
| `SEED_POOL` | 8302 | the matched random pool |
| `SEED_RAND5` | 8303 | the RAND5 arm |
| `SEED_REL` | 8304 | random nodes for reliability |
| `SEED_CAL` | 8305 | calibration nodes |

Other fixed settings: `STEER_DOSE = 2.0` and `TE_MIN = 0.2`. Generation uses common-random-number uniforms per slot
(PCG64 of a stable key), T = 1, top-p = 1 and no top-k.

`method.py` takes `--stages` (comma list), `--max-prompts` and `--no-free`. These are the commands as actually run
(`logs/run_s0..s2.log` cover the first line):

```bash
.venv/bin/python tests/test_labeller.py        # CPU labeller re-check (T7)
.venv/bin/python method.py --stages setup,contrasts,gputests,amend0a,circuit:C1forced,circuit:C2a,circuit:C1nat,circuit:C1mix
# (the logs show setup/contrasts/gputests were restarted twice before the circuit stages; see logs/run_s0-s2.log)
./run_chain3.sh <PID>     # f4b, commit1, validate, commit2, gen, enginecheck, C1nat... ; exited 1 (CUDA OOM)
./run_chain4.sh <PID>     # valsens:C1forced,valsens:C2a
./run_chain3b.sh          # resume: validate:C1forced,validate:C2a,commit2,gen:C1forced,gen:C2a,enginecheck,valsens,f4b:C1nat,commit1b:C1nat,... ; exited 1 (OOM late)
./run_chain5.sh <PID>     # dose:C1forced,dose:C2a
./run_chain6.sh <PID>     # circuitlite:C1natB, f4b:C1natB, validate:C1nat (one process per stage)
./run_chain7.sh           # validate:C1nat in a fresh process
./run_final.sh            # src/deviations_final.py, src/novelty_k3.py, analysis.py, audit/rederive.py, analysis.py, make_readme.py, schema check + mini/preview
```

`<PID>` is the process the chain waits for. Pass any finished PID, or none, to start the chain at once. Every stage
resumes from its own files, so after an OOM a rerun skips the work already done.

A clean equivalent of the same stages (the "How to run" section of `README.md`):

```bash
.venv/bin/python method.py --stages f4b:C1forced,f4b:C2a,commit1:C1forced+C2a,validate:C1forced,validate:C2a,commit2:C1forced+C2a,gen:C1forced,gen:C2a,enginecheck
.venv/bin/python method.py --stages valsens:C1forced,valsens:C2a,f4b:C1nat,commit1b:C1nat,validate:C1nat,circuitlite:C1natB,f4b:C1natB,dose:C1forced,dose:C2a
```

`cache/` (AtP, exact and class-mean arrays) is regenerable by the circuit stages.

## 5. Expected outputs and numbers

* `results/summary.json` is the master summary. `method_out.json`, `full_method_out.json`, `mini_method_out.json` and
  `preview_method_out.json` hold the exp_gen_sol_out output, one example per generation slot.
* The `metadata.summary.contrasts` block of `full_method_out.json`:
  * `C1nat_sd_m_v = 0.3379592507008036`.
  * `C1nat_A`: `TE_mean = 0.8931844075520833`, `TE_sd = 0.37727308731246684`, `n_TE_gt_min = 15`. The first pair is
    `W1|guy` vs `W1|mother` with TE 0.6239. Because the mean TE is below 1 nat, the run used the pre-registered
    C1-forced fallback.
* Mean total effects (README table): C1forced 9.91, C2a 19.33, C1nat 0.89, C1mix 4.00 and C1natB 0.46 nats.
* Validation (`data/validation_rows_*.jsonl`, `figures/validation_*.png`): 9/10 (C1-forced) and 8/10 (C2a) of the
  top-10 nodes beat 50 matched random components in both ABLATE and STEER.
* Generation (`data/gen_raw_*`, `data/gen_labels_*`, `figures/generation.png`), PREFILL, correct target programs out
  of 30:

  | unit | TWIN | TOP5 | RAND5 |
  |---|---|---|---|
  | B3 | 8 | 29 | 23 |
  | T10 | 1 | 29 | 30 |

  For B3, TOP5 vs RAND5 McNemar gives p = 0.0703 two-sided and 0.0352 one-sided. Verdict: K3 **PARTIAL** for both
  units.
* Dose sensitivity (`data/gen_dose_*`): at dose 0.5, T10 gives 30/30 vs 6/30 (p = 1.2e-07) and B3 gives 25 vs 20
  (p = 0.12).
* Motif test (`figures/motif_panel.png`): Qwen C1mix DEC 0.63, COND 0.01, depth 0.86, vs Gemma 0.53 / 0.36 / 0.69.
* Stability (`figures/stability.png`): top-10 Jaccard 0.25.
* Figures in `figures/`: `circuit_*`, `atp_vs_exact`, `faithfulness`, `dose_response`.
* No paper was in the workspace, so the mapping from these numbers to paper sections was not recorded. The
  corresponding README sections are "K3 verdicts", "Contrasts and circuits", "Validation", "Generation", "Motif test"
  and "Stability".

Because bf16 GPU kernels are not deterministic, a rerun on different hardware may differ slightly in the last digits.
