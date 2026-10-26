# Reproducing NOV-B1 (evolving bin-packing rules with an 8B model)

This describes what was **actually run** on 2026-10-24 (UTC), in order. Every path below is relative to this folder.

## 1. Get the artifact

```bash
git clone <the published repository>
cd <repository>/gen_art_experiment_51      # this folder
```

The folder contains the code (`method.py`, `src/`, `tests/`, `audit/`), the committed predictions (`predictions/`,
`commitments.log`), the instance sets (`data/instances/`), the probe file (`data/probes/P1.json`), the known-heuristic
corpus (`data/corpus/`), the external sources (`ext/`), the raw search rows (`data/main/`, `data/ns/`, `data/smoke/`),
the results (`results/`), the figures (`figures/`) and `method_out.json` with its `full_`/`mini_`/`preview_` variants.

## 2. System, Python and libraries

- Ubuntu/Debian x86-64, NVIDIA driver with CUDA 12.x (the run used driver 595.91, CUDA 13.2 runtime reported).
- Python 3.12.14, `uv` 0.6.14. No system C compiler is needed: `tools/cc` is a zig-cc shim for Triton.
- Exact versions: `pyproject.toml` pins all 171 packages installed in `.venv` (key ones: `vllm==0.11.0`,
  `torch==2.8.0`, `transformers==4.57.1`, `numpy==2.2.6`, `scipy==1.18.1`, `scikit-learn==1.9.1`,
  `matplotlib==3.11.2`, `aiohttp==3.14.5`, `loguru==0.7.3`, `jsonschema==4.26.0`, `ziglang==0.17.0`).

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r pyproject.toml
```

## 3. Downloads, environment variables, keys (names only)

- Model (sampling only): `Qwen/Qwen3-8B-FP8` at revision `220b46e3b2180893580a4454f21f22d3ebb187d3`
  (`huggingface-cli download Qwen/Qwen3-8B-FP8 --revision 220b46e3b2180893580a4454f21f22d3ebb187d3`). The run used the
  standard Hugging Face cache (`HF_HOME`); set it wherever you like.
- `OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY`: only for the V3 judges (`src/judges.py`); the run spent USD 0.14.
- External primary sources are already in `ext/` with sha256s in `results/ext_sources.json`; `src/fetch_ext.py`
  re-downloads them from the pinned commits/URLs if needed.
- The declared dependency **art_j3Rm_lr2nzR6** (`full_data_out.json`, an algorithm-choice coding bench) is read once by
  `src/dep_scan.py` through the environment variable `ART_J3RM_LR2NZR6_DIR` (default: the sibling folder
  `../art_j3Rm_lr2nzR6`). Its scan output is already committed in `data/corpus/dep_scan/dep_scan_hits.json`, so the scan
  is optional. No user-uploaded data is used.

## 4. Commands, in the order they were run (hardware: 1x RTX 4090 24 GB, 13.6-vCPU cgroup quota, 56 GB RAM)

All commands use `OMP_NUM_THREADS=1`; `method.py <stage>` runs the same scripts in the same order.

| # | command | what it does | wall time |
|---|---------|--------------|-----------|
| 1 | `python -I src/s0_verify.py verify` | instance-set and `ext/` hashes vs the embedded/BP9 values, notebook copies identical | <1 min |
| 2 | `uv run --no-sync python -I src/gate.py` then `... src/s0_verify.py gate` | rebuild instance sets, reproduce FunSearch's printed numbers (G-HARNESS PASS), write `results/harness_gate_v10.json` and `predictions/thresholds.json` | 10 s |
| 3 | `python -I src/dep_scan.py` | scan of art_j3Rm_lr2nzR6 (36 regex hits, 6 priority-expressible textbook rules) | 1 min |
| 4 | `uv run --no-sync python -I src/probes.py` | `data/probes/P1.json` (2,000 states, seed 20261024; file sha256 `c13ed7bc...`) + self-checks | 15 s |
| 5 | `uv run --no-sync python -I src/corpus.py 10` | 86-entry corpus, 3,843-point ab grid (F for the first 2,000 of permutation seed 20261025), calibration | 13 min |
| 6 | `bash start_vllm.sh` | vLLM server on 127.0.0.1:8051 (FP8 Marlin, `-O0`, prefix caching, max-logprobs 20) | ~4 min |
| 7 | `uv run --no-sync python tests/unit_tests.py` | 30 unit tests (sandbox, prompt/trim, DTB/RPB fork logic, islands, clusters) | 2 min |
| 8 | `predictions/commit1.json` via `src/commit.py` | hash-chained commit #1 (before any search call) | - |
| 9 | `uv run --no-sync python -I src/search.py --run smoke --seeds 99 --rounds 1 --calls-per-round 10` | smoke round (discarded; `tests/smoke_check.py smoke`) | 3 min |
| 10 | `uv run --no-sync python -I src/search.py --run main --seeds 0,1 --rounds 80 --calls-per-round 25 --arms T1.0,T1.6,DTB,RPB,IDEA --pause-after 3 --workers 10 --deadline <epoch>` | main search; pauses after round 4 | 1 h 11 min |
| 11 | `uv run --no-sync python -I src/commit2.py <hard-stop epoch>` | commit #2: C* = 2,000 (ladder level L1); the paused search resumes | - |
| 12 | `uv run --no-sync python -I src/search.py --run ns --seeds 0,1 --rounds 40 --calls-per-round 25 --arms NS` | no-selection arm | 2 min |
| 13 | `src/judges.py gate` (after commit #3) | judge gate on 10 controls | 1 min |
| 14 | `uv run --no-sync python -I src/postsearch.py clusters,best,v12,v3` | clusters, best programs (held-out once), V1, V2, V3 candidates | 6 min |
| 15 | `src/v5.py` (after commits #4, #5; vLLM restarted with `VLLM_GPU_UTIL=0.80 bash start_vllm.sh`) | V5 founder reversion | 6 min |
| 16 | `python audit/profile_candidates.py`, `python audit/profile_echo.py`; arm-blind read written to `audit/manual_read.json`; commit #6 | manual read aids and the read itself | 30 min |
| 17 | `src/judges.py candidates`, `src/v3_final.py` | advisory judges, V3 classes | 2 min |
| 18 | `src/postsearch.py v6,evaluator,placebo`, `src/costs.py`, `src/figures.py`, `src/outputs.py`, `python3 audit/rederive.py` | V6, evaluator effect, placebos, costs, figures, `method_out.json`, independent re-derivation | 3 min |

Seeds: search seeds 0 and 1 (smoke 99); vLLM per-call seed = 32-bit sha256 hash of (seed, arm index, call id);
parent sampling `default_rng([seed, arm_idx, 1])`, island resets `[seed, arm_idx, 2]`, RPB/DTB forced-token draws
`[seed, arm_idx, call_id, 7]`. GPU sampling is not bit-reproducible across hardware or batch composition, so a rerun
reproduces the protocol and the statistics, not the identical programs. Every analysis after step 12 is deterministic
given `data/main/` and `data/ns/`.

## 5. What you should get

- `results/harness_gate_v10.json`: G-HARNESS PASS; BF 212.0 bins / 5.36779% on OR3, 2067.0 / 3.98430% on Weibull 5k;
  c12 207.45 / 3.10636%; c14 2001.4 / 0.68417%.
- `results/v1.json`: V1 **SUPPORTED**. Best program per core arm, held-out excess on H-FSW5k / H-OR3 (bars 3.187% / 4.294%):
  T1.0 1.53 / 3.55, T1.6 1.40 / 3.55, DTB 2.43 / 4.18, RPB 1.73 / 3.48 (IDEA 1.85 / 3.38; NS = best fit 3.98 / 5.37).
- `results/v2.json`: V2 **PARTIAL**. Behaviour clusters over 2 x 2,000 calls: T1.0 148, T1.6 373, DTB 446, RPB 212,
  IDEA 770. R1 = 3.01 [2.66, 3.43], R2 = 1.20 [1.13, 1.33], R3 = 2.10 [1.89, 2.32].
- `results/v3_final.json`: 211 candidates, 70 NB, 53 joint clusters, 30 audited; judge gate unmet; 8 NOVEL by the
  arm-blind manual read (all one idea family: prefer leftovers that are whole multiples of the item size).
- `results/v5.json` (reversion 0.40 at birth tokens vs 0.36 at controls, sign test p = 0.49), `results/v6.json`
  (V6 PARTIAL: rename rate IDEA 0.44 vs T1.0 0.86), `results/evaluator_effect.json` (NS never beats best fit),
  `results/placebos.json` (label shuffles never reach R1 >= 1.5), `results/rederive.json` (independent re-derivation).
- Figures F1-F8 in `figures/` (PDF + PNG).
