# Reproducing "Where in Qwen3-8B a coding ban lives"

This file describes what was actually run on 2026-10-20, in the order it was run, including the restarts. Every path
is relative to this folder.

## 1. Get the artifact

This folder is one folder of a public GitHub repository. Clone the repository and `cd` into the folder that contains
this file (it holds `method.py`, `README.md` and `pyproject.toml`):

```bash
git clone <repository-url>
cd <repository>/<this-artifact-folder>
```

The folder already contains everything the code reads from other artifacts. `inputs/` holds read-only copies of the
iteration-2 artifacts:

- `inputs/exp8`: `art_8_ULPE8jJQc_` (engine, frozen T1/T2 prompts, canonical labeller suite, archived ban rows).
- `inputs/exp11`: `art_0ndRfWKBWclR` (frozen bench, labellers, `commitment.json`).
- `inputs/exp7`: frozen padding rule and nouns.
- `inputs/exp9`: manifold reference and samples.
- `inputs/exp12`: `art_3iv5G76C3yoX` (SAE code, transfer corpus inputs, fresh-pool ban rows).
- `inputs/audit`: probe code.

The only declared dependency, the dataset `art_j3Rm_lr2nzR6`, is read by one script only (`src/dataset_provenance.py`,
a provenance check). It looks for the dataset in this order: the first command-line argument, then the environment
variable `ART_J3RM_DIR`, then the sibling folder `../art_j3Rm_lr2nzR6`. No user-uploaded (private) file was used.

## 2. System, Python and libraries

Hardware actually used:

- 1 × NVIDIA RTX 2000 Ada Generation, 16 GB VRAM, compute capability 8.9 (driver 595.91, CUDA 13.2 runtime).
- 6 CPU cores (cgroup quota 5.1).
- 28 GB RAM container limit.
- Debian 12 container. Ubuntu 22.04/24.04 works the same way.

No C compiler is needed: nothing is compiled. The FP8 kernels are `torch._scaled_mm` from the torch wheel. A GPU with
FP8 support (compute capability ≥ 8.9, ≥ 16 GB) is required for the engine as written.

Python 3.12.14 and uv 0.6.14. All 82 packages are pinned in `pyproject.toml` to the versions installed in `.venv`
(`uv pip freeze`). Key pins: torch 2.8.0 (cu128 wheel), transformers 4.57.6, numpy 2.2.6, scikit-learn 1.9.1,
ripser 0.6.15, openai 3.35.1.

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
```

## 3. Models, data and environment variables

Models are read from the Hugging Face cache named by `HF_HUB_CACHE` (or `HF_HOME`). Download them first:

```bash
huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218
huggingface-cli download Qwen/Qwen3-8B-Base          # snapshot used: 49e3418fbbbca6ecbdf9608b4d22e5a407081db4
huggingface-cli download Qwen/SAE-Res-Qwen3-8B-Base-W64K-L0_50 layer15.sae.pt layer20.sae.pt layer27.sae.pt
# SAE snapshot used: 9b7d647127c303dd371e5dbd992236bd9799b171
```

(`tests/download_0g.py` does the base model and SAE downloads.)

Environment variables, names only:

- `HF_HUB_CACHE` / `HF_HOME`: model cache.
- `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY`: the blind LLM judge, called only when the runtime and AST labellers
  disagree. Judges: `openai/gpt-4.1-mini` for T1/T2, `google/gemini-2.5-flash-lite` for bench tasks. Total spend was
  USD 0.22. Judge answers are cached in `data/judge_cache*.jsonl`, so a re-run with these caches makes no new calls for
  identical programs.
- `ART_J3RM_DIR` (optional): see above.
- `AII_JSON_SKILL_DIR` (optional): only used by `finalize.sh`. Without it, `tests/make_mini_preview.py` writes the
  mini/preview files.

## 4. Commands, in the order they were run

The model is Qwen3-8B with its decoder linears quantised to FP8 at load time (W8A8 dynamic, see README deviation 1).
Thinking is off, T = 1.0, top-p 1, no top-k, at most 1024 new tokens. Every stage is resumable and skips completed
work.

| # | Command | What it does | Approx. time on the RTX 2000 Ada |
|---|---|---|---|
| 1 | `.venv/bin/python method.py prompts` | S1: 140 prompts, token-aligned twins (`prompts/prompts.jsonl`) | 1 min (CPU) |
| 2 | `.venv/bin/python method.py gpu1 --minutes 78 --optional-minutes 92` | S2 direction (54 s), GPU unit tests, commit #1, U7, S5 ban-free arms (150 batches of 20) | 30 min |
| 3 | `.venv/bin/python method.py label --minutes 270 &` | label worker, run in parallel with every sampling stage | follows sampling |
| 4 | `.venv/bin/python src/s0_checks.py` | input hashes, labeller re-check | 2 min (CPU) |
| 5 | `.venv/bin/python method.py commit2` | S6 summaries, landing forecasts, commit #2 | < 1 min |
| 6 | `.venv/bin/python method.py gpu2 --minutes 45 --optional-minutes 40` | S7 ban arms, SUB, head ablation, W4 top-up, ADD α 0.5, S8 states | 55 min |
| 7 | `.venv/bin/python method.py c2e --minutes 40` | C2e decoders on 20-row-batch states (later kept as `results/c2e_batch20_sensitivity.json`) | 20 min |
| 8 | `.venv/bin/python method.py zerog --minutes 60` | first 0g attempt, stopped at a corpus assertion (bug fixed, README deviation 12) | 2 min |
| 9 | `.venv/bin/python method.py gpu3 --minutes 35` | C2e extension states (batch 1), 12 exploratory random directions, extension decoders | 30 min |
| 10 | `.venv/bin/python method.py gpu3 --minutes 20` | second run: U1b test, batch-1 re-extraction of the C2e/5a states | 10 min |
| 11 | `mv results/c2e.json results/c2e_batch20_sensitivity.json && .venv/bin/python method.py c2e --minutes 40` | C2e on batch-1 states (primary) | 22 min |
| 12 | `.venv/bin/python method.py zerog --minutes 60` | 0g: base generation, 2×2 CE design, SAE encoding for 5a | 45 min |
| 13 | `.venv/bin/python method.py s8c` | batch-1 re-extraction of the 5c states | 15 min |
| 14 | `./finalize.sh` | analyses + figures + `method_out.json`, token-id export, README fill, mini/preview, final hash commit, audit | 6 min |
| 15 | `.venv/bin/python audit/rederive_headlines.py` | independent re-derivation of the headline numbers + placebo tests | 2 min |

Other checks that were run:

- `.venv/bin/python tests/test_c2e_synthetic.py` (T4).
- `.venv/bin/python tests/test_direction_maths.py` (T3).
- `.venv/bin/python src/dataset_provenance.py`.

Restarts during the run:

- The first `gpu1` attempt stopped at unit test U3. The criterion was revised before any sampling (README deviation 4).
- The label worker was restarted twice to rebalance and then raise the judge cap (USD 0.20 → 0.40).

GPU time was about 3.5 h in total; wall time was about 4 h.

Seeds and keys:

- CRN uniforms: `u_stream(task, template, k)` = PCG64(sha256 of `task|template|k`). U7 used exp8's keys
  (`beh`, `t2`, template, k).
- Random directions: PCG64 seeds 9001–9003 (frozen) and 9004–9015 (exploratory).
- Random head sets: numpy seeds 7101–7103.
- Folds: StratifiedKFold with `random_state=0`.
- Permutations: seed 100 (C2e).
- Bootstraps: fixed seeds in `src/analysis/*.py`.

Determinism: with the same GPU model and software stack, sampling and batch-1 teacher forcing are bit-exact
(`results/unit_tests_u1b.json`). On a different GPU, FP8 GEMM kernels may differ, so individual token sequences can
change; the arm-level shares and verdicts are the reproducible quantities. Judge labels are cached; re-querying the
judges (temperature 0) may still vary slightly.

## 5. What you should get

The headline numbers are in `README.md` → "Results (headline)". They were independently re-derived by
`audit/rederive.py` and `audit/rederive_headlines.py` (`results/rederive*.json`).

C2d (`results/c2d.json`): **DISCONFIRMED**.

- ADD passes on 0 of 5 gated tasks.
- ADD sits within the random range on 5 of 6 tasks.
- Pooled SUBTRACT Δ banned share = −0.026, 95% CI [−0.07, 0.03].
- T2: ADD avoidance 0.44 vs random 0.06 / 0.50 / 0.34.
- T03: ADD 0.80, landing on a size-k heap; the ban lands on quickselect.

C2e (`results/c2e.json`): no locus on any testable task.

- T2 state BA ≤ 0.63 against a layer-max null q95 of about 0.70.
- T1, T04, T06 and T05 equal their template-only accuracy (0.904 / 0.832 / 0.88 / 1.00).
- T03 is not testable.

C2f (`results/c2f.json`): **NOT SUPPORTED**. Δ_T1 = +0.06 (90% CI [0.02, 0.12]); Δ_T2 = −0.03.

0g (`results/sae_transfer.json`): frozen rule **PASS** at L15/20/27.

- FR_zero instruct / base on own text: 0.989 / 0.993, 0.990 / 0.991, 0.994 / 0.991.
- Displacement preservation is only cos ≈ 0.27–0.32.
- On placebo input (SAE/zero CE swapped per sequence) the FR values collapse to about 0, but the 0.9× rule can still
  pass, so the rule is lenient, as the plan stated.

Engine checks:

- U7 (`data/samples_raw.jsonl`, arms `U7_*`): T2 ban 2/20 Dijkstra, twin 20/20.
- Unit tests: `results/unit_tests_gpu.json`, `results/unit_tests_u1b.json`, `results/test_*.json`.

Outputs and where they appear:

- Figures fig1–fig9 in `figures/` (PNG + PDF), referenced from `README.md`.
- `method_out.json` (+ `full_`, `mini_`, `preview_` variants) in exp_gen_sol_out format.

State arrays (`states/`) larger than 90 MB are stored as row-wise parts (`T2_BAN.part001.npy`, …), each under
GitHub's 100 MB limit. `src/states_io.py` writes and reads them; the split was verified to be lossless
(`np.array_equal` against the original before deletion), and every reader was re-run on the split files with
identical results.

There is no paper in this folder yet. A paper built from this artifact should quote the numbers above from the
listed JSON files.
