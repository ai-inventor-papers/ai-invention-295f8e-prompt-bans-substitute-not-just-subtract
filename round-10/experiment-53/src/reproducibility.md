# Reproducing NOV-T (decision-token branching vs temperature on a constructive-TSP heuristic search)

This file describes what was actually run on 2026-10-24 (UTC 17:45 to about 23:35), in order. Every path is relative
to this folder.

## 1. Get the artifact

The workspace is published as one folder of a public GitHub repository:

```bash
git clone <repository-url>
cd <repository>/<this-folder>      # the folder that contains method.py and this file
```

The declared input dataset is the sibling artifact **art_j3Rm_lr2nzR6** (`full_data_out.json`, 96 MB). Point the
code at it with ONE environment variable (default: sibling folder `../art_j3Rm_lr2nzR6`):

```bash
export ART_J3RM_DIR=../art_j3Rm_lr2nzR6
```

Files copied read-only from the lost iteration-9 workspace (TSPLIB `.tsp` files, iteration-9 source) are in
`inputs/tsp9/` with sha256 hashes in `inputs_manifest.json`. No user-uploaded file was used (the uploads folder was
empty).

## 2. System, Python and libraries

- Ubuntu (Linux 6.8 kernel), **NVIDIA L4 (23 GB, compute capability 8.9)**, driver 595.91, CUDA 13.2 driver; a
  container quota of **5.1 CPUs** and 62 GB RAM. No system C compiler: `tools/cc` (and `tools/gcc`) wrap
  `python -m ziglang cc` so that Triton / torch.compile can build their launchers.
- Python **3.12.14**, `uv` 0.6.14.
- Exact library versions: `requirements.txt` (175 pins, from `uv pip freeze`) and `pyproject.toml` (same pins).
  Key pins: vllm 0.11.0, torch 2.8.0 (cu128), transformers 4.57.1, numpy 2.2.6, scipy 1.18.1, elkai 2.0.1,
  ortools 9.15.6755, openai 3.37.0, loguru, matplotlib, pytest.

```bash
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r requirements.txt
```

Note: an unpinned `uv pip install vllm==0.11.0 ...` pulls transformers 5.x, which crashes vLLM 0.11.0 at start
(`Qwen2Tokenizer has no attribute all_special_tokens_extended`); the pinned file avoids it.

## 3. Model, data and keys

- Model: `Qwen/Qwen3-8B-FP8` at revision `220b46e3b2180893580a4454f21f22d3ebb187d3` (8.9 GB):
  `hf download Qwen/Qwen3-8B-FP8 --revision 220b46e3b2180893580a4454f21f22d3ebb187d3` (uses `HF_HOME`).
- TSPLIB files: shipped in `data/tsplib_raw/` (13 files; re-downloaded from the mastqe mirror if missing).
- Random instances are generated from fixed seeds (`src/tsp_task.py`), LKH-3 references by elkai.
- Environment variables (names only): `HF_HOME` (model cache), `ART_J3RM_DIR` (dependency folder),
  `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY` (only for the advisory V3 judges, `src/judges.py`).
  The local vLLM client always uses `base_url=http://127.0.0.1:8000/v1`, `api_key=EMPTY`.

## 4. Commands, in the order they were run

```bash
python method.py stage0          # hardware record, instances, probe states (2,000), TSPLIB, elkai references
                                 # (192 random + 13 TSPLIB, ~60 s on 5 workers), TSPLIB gate, NN gate, baselines
python method.py p1              # tuned parametric P1: 2,000 random-search evaluations, rng 777 (~3 min, 2 workers)
bash start_vllm.sh compile &     # vLLM server (first start ~5 min incl. torch.compile); log in logs/vllm_server.log
python method.py gpu             # G1-G5 mechanics + throughput probe -> results/gpu_mechanics.json
python method.py tests           # 29 CPU unit tests (T1-T9), ~100 s
python method.py commit1         # predictions/protocol.json, hash-chained in commitments.log (COMMIT #1)
python method.py pilot           # seed 99, 10 calls per arm (data/pilot/, excluded from analysis)
# 100-call stage: data/targets.json = 160 calls for T1.0, T1.6, DTB, RPB, IDEA x seeds 0, 1; then
python src/search.py --out data --n-eval 4 --wait &          # main search (runs until data/STOP exists)
python src/cstar.py 22:25        # COMMIT #2: C* from rounds 2-4 -> row A, C* = 2000 (+ NOSEL 500), new targets
python src/corpus.py             # published-heuristic corpus, COMMIT #3
ART_J3RM_DIR=... python src/dep_extract.py   # all 10 dependency datasets scanned; harness check
python tests/test_rederive_forcing.py data   # 50/50 logged DTB/RPB forcings re-derived
touch data/STOP                  # hard stop touched 22:04 UTC (search exited 22:06:50 after round 32)
python method.py analyze         # clusters, rarefaction, bootstrap, held-out bests, verdicts, V3 pool
python method.py judges          # gated OpenRouter judges for V3 candidates (cap USD 0.50)
python method.py figures         # figures/F1..F6
python method.py rederive        # audit/rederive.py: stdlib re-derivation + placebos
python method.py outputs         # method_out.json + full/mini/preview
```

Seeds: search seeds 0 and 1 (pilot 99); request seeds `default_rng([seed, arm, call, 2])`; forced-token and position
draws `[seed, arm, call, 3|4]`; island streams `[seed, arm, 1|5|6]`; P1 rng 777; probe states rng 930100+i / 930200+i.

Runtime on the L4: the search ran ~2 h 08 min (19:58 to 22:06 UTC; 33 rounds, 1,056 calls per arm-seed, 10,812
calls) at ~580 generated tokens/s; round time grew from 60 s to ~310 s as programs lengthened. The final analysis
(held-out evaluation of 10 bests, 50 V3-pool programs, NOSEL) took ~8 min on 5 CPU workers; judges ~2 min (USD 0.037). vLLM sampling is not bit-reproducible across batch compositions
(G5 recorded byte identity only at batch 1), so a re-run reproduces the protocol and the statistics, not the exact
rows; the analysis, figures and re-derivation reproduce exactly from the kept `data/`.

## 5. What you should get

- `results/verdict_v1.json`, `results/verdict_v2.json`: the V1-T and V2-T verdicts (see README "Results").
- `results/clusters.json`: per arm-seed behaviour-cluster counts, rates per 1,000 calls, bootstrap intervals.
- `results/heldout.json`: held-out n=200 / extended / TSPLIB gaps of every arm-seed best, NN, P1 and the corpus.
- `results/rederive.json`: the stdlib re-derivation (must match `clusters.json`; all placebos must fail).
- `method_out.json` (+ `full_`, `mini_`, `preview_` variants): exp_gen_sol_out rows (one per call, per best
  program, per arm-seed cluster summary) with verdicts in `metadata`.
- `figures/F1..F6` (PDF + PNG).
