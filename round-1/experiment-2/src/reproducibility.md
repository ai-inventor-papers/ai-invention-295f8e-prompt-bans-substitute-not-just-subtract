# Reproducing this artifact

This file describes what was actually run for artifact `gen_plan_experiment_2_idx3` ("Mapping how bans move
path-search choices"), including the failed attempts, so that a reader can rebuild the same environment and
reproduce the same numbers. All paths are relative to this artifact's folder.

## 1. Get the artifact

The workspace is published as one folder of a public GitHub repository:

```bash
git clone <URL of the published repository>
cd <repository>/<folder of artifact gen_plan_experiment_2_idx3>   # the folder that contains method.py and this file
```

This artifact uses no other artifact's outputs and no user-uploaded inputs (the run's upload folder was empty).
It builds its own tasks, hidden tests, prompts and labels.

What is **not** in the repository: `cache/suffix_means_*.npy` and `cache/hR_layer{8..20}.npy`, about 370 MB of
float16 activations that only Phase B reads. They are excluded from upload and stay on the run's storage volume.
`python method.py --only phase_b` regenerates them (section 4). Everything that `analysis/analyze.py` reads is
published: `cache/hR_layer{21..28}.npy`, `cache/hR_index.jsonl`, `cache/basis_*.npz`, `cache/hR_ablated_*.npz`,
`cache/directions_*.npz` and `cache/anchors_*.npz`.

## 2. System, Python, environment

What the run used:

* **OS**: Debian GNU/Linux 12 (bookworm) container, kernel 6.8, x86-64. Ubuntu 22.04/24.04 works the same way.
* **GPU**: 1 × NVIDIA L4, 23 GB VRAM (driver 595.91.07, CUDA 13.2 driver API). CPU: 6 cores (cgroup quota).
  RAM: 57 GB (cgroup limit).
* **System packages**: none beyond `git` and `curl`. No C compiler was available. That is why vLLM could not
  start (section 4, "what failed") and is not needed.
* **Python** 3.12.14 (CPython). **uv** 0.6.14.

```bash
# from the artifact folder
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r pyproject.toml   # 211 exactly pinned packages (= logs/pip_freeze.txt)
```

Key versions (all are pinned in `pyproject.toml`): torch 2.13.0 (CUDA 13.0 wheel), transformers 5.19.0,
accelerate 1.15.0, safetensors 0.8.0, huggingface-hub 2.2.0, numpy 2.3.5, scipy 1.18.1, scikit-learn 1.9.1,
networkx 3.7, matplotlib 3.11.2, loguru 0.7.3, openai 3.35.1, joblib 1.6.0, threadpoolctl 3.7.0, pyyaml 6.0.3.
vllm 0.32.0 is pinned because it was installed, but it is never used.

## 3. Downloads, environment variables, keys (names only)

* **Model**: `Qwen/Qwen3-8B` from the Hugging Face Hub, revision `b968826d9c46dd6066d109eabc6255188de91218`
  (about 16.4 GB, bf16 safetensors). Download it once with
  `.venv/bin/hf download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218`. It goes to the
  Hugging Face cache, never into this folder.
* **Environment variables**:
  * `HF_HOME`: optional, the Hugging Face cache location.
  * `HF_TOKEN`: optional, the model is public.
  * `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY`: required for the labelling stages, which call the blind LLM
    judge and the gold-set judges through OpenRouter.
* The judge models are:
  * `anthropic/claude-haiku-5.5`: primary judge, temperature 0, reasoning effort "low".
  * `openai/gpt-4.1-mini`: second gold-set judge.
  * `deepseek/deepseek-v4.1-flash-1017`: gold-set resolver.
  * Total spend in the run: about $0.09 (`logs/openrouter_spend.jsonl`).
* The scripts set the compiler caches (`VLLM_CACHE_ROOT`, `TRITON_CACHE_DIR`, `TORCHINDUCTOR_CACHE_DIR`,
  `XDG_CACHE_HOME`) to folders inside the artifact folder (`common.py`).

## 4. Commands, in the order they were run

Every GPU phase is its own process, and `method.py` runs a stage with `--only <stage>`. Wall-clock times are from
the run on the L4 (`logs/timing.jsonl`, `logs/method.log`). The seeds are fixed in code; see the end of this
section.

```bash
.venv/bin/python tasks/tasklib.py            # hidden tests (41 T1 / 42 T2), references 3/3, wrong programs fail   ~2 min CPU
.venv/bin/python labeller/test_labeller.py   # labeller unit tests: runtime and AST 19/19                          ~1 min CPU
.venv/bin/python prompts/build_prompts.py    # 1140 prompts + token ids; asserts identical suffix ids per task     ~2.5 min CPU
.venv/bin/python gen/phase_a.py --batch 32   # Phase A on HF generate (see "what failed")                          46 min GPU
.venv/bin/python method.py --only label_a    # label 1060 programs, labeller gate, Phase-A summary (judge calls)    ~7 min
.venv/bin/python method.py --only succession # rebuild prompts with the ordered succession ban sets (1550 prompts)  ~2 min
.venv/bin/python method.py --only phase_b    # h_R cache, R gate, manifold, directions, COMMIT forecasts            35 min GPU+CPU
.venv/bin/python method.py --only phase_c    # prompt bans (ban:bfs, ban:dijkstra; N=100 each)                      10 min GPU
.venv/bin/python method.py --only phase_d    # hooked removal arms (R-plus-prompt variant, alpha 0/0.5/1/2)         19 min GPU
.venv/bin/python method.py --only phase_c_ext  # mention:modal (N=50) + exploratory step-2 bans (N=50)              9 min GPU
.venv/bin/python method.py --only phase_d_ext  # exploratory full-variant removal arms (alpha 2, 4)                  13 min GPU
.venv/bin/python method.py --only analysis   # all results/, figures/, method_out.json                              ~3 min CPU
.venv/bin/python analysis/audit_rederive.py  # independent re-derivation of the headline numbers (99 checks)        ~2 min CPU
# mini/preview variants of method_out.json (the AI Inventor aii-json skill script):
#   aii_json_format_mini_preview.py --input method_out.json  -> full_/mini_/preview_method_out.json
```

`python method.py` with no arguments runs the same stages in the same order (tasks → … → analysis; then run the
two extension stages and the audit as above). Total GPU time is about 2.2 h on one L4.

**What failed during the run, and how it was handled:**

1. **vLLM did not start.** `gen/vllm_engine.py` tried the plan's FIT ladder. Every engine start failed with
   `InductorError: Failed to find C compiler`, because Triton needs a C compiler and the container has none. A
   zig-cc shim could not be installed in time (`logs/zig_install.log`). All sampling therefore uses batched HF
   `generate` (`gen/hf_engine.py`) on the same token ids (the plan's fallback). `gen/vllm_engine.py` is kept only for
   its pure-Python helpers (code extraction, stop string).
2. **The first HF Phase-A run was too slow.** It used batch 24 and waited on the longest row. It was stopped after
   its 24-sample mini stage, which is kept in `data/raw_phaseA.jsonl`. It was then resumed with batch 32 and chunked
   continuation (rows still running after 448 new tokens are continued in a later batch, up to 1024 tokens).
   `gen/phase_a.py` skips rows that already exist, so rerunning it continues rather than duplicates.
3. **The first launch of `phase_d_ext` failed with a NameError**, because the function was defined after the
   `__main__` guard. It was fixed and re-run. No samples were lost.
4. **`cache/suffix_means_t{1,2}.npz` (122 MB) exceeded the 100 MB file limit.** It was split into per-mode `.npy`
   files after Phase B, and Phase B's reader and writer were updated to match.

**Seeds and decoding.**

* Sampling: T=1.0, top_p=1.0, top-k off, thinking off (`enable_thinking=False`).
  * Phases A and C: max 1024 new tokens, per-row stop at the closing code fence.
  * Phase D: max 768 new tokens.
* Batch seeds are `torch.manual_seed(seed_base + b)` for batch b:
  * Phase A: `seed_base = stable_seed("phaseA", stage) % 100000`.
  * Elicitation: `stable_seed("elicit", attempt)`.
  * Phase C: `stable_seed("phaseC", tag)`.
  * Phase D: `1000 + b`, with identical batch composition across arms (common random numbers).
* `stable_seed` is the first 8 hex digits of a SHA-256 hash (`common.py`).
* Other fixed seeds:
  * hidden-test generators: 1 (T1) and 2 (T2); probe inputs: 7;
  * random-control directions: 101 and 202;
  * Phase B bootstraps: 7; analysis bootstraps: 2026; audit placebos: 99; gold-set sampling: 11.

Batched bf16 sampling is reproducible on the same GPU/driver with the same batch composition. On other hardware
the token-level outputs can differ, but the label distributions should agree within sampling noise.

**Re-running Phase B overwrites the commit.** Phase B rewrites `predictions/predictions_v1.json` and appends to
`predictions/commit_log.jsonl`. Back up `predictions/` first if you only want to regenerate the excluded cache
files.

## 5. What you should get

| Number | Value in this run | File |
|---|---|---|
| Baseline T1 / T2 | 200/200 BFS (pass 0.99) / 200/200 Dijkstra (pass 1.00) | `results/summaries.json`, `results/phaseA_summary.json` |
| Forced manipulation check | 0.94 (T1) / 0.74 (T2) | `results/phaseA_summary.json` |
| Labeller gate | κ(runtime, AST) 0.90 / 0.94; runtime vs adjudicated 0.96 / 0.92; pass | `results/labeller_gate.json` |
| R gate | T1 l*=27 (transfer 0.67 vs null 0.22; decoder fails), T2 l*=24 (transfer 0.54 vs 0.31; pass) | `results/gate.json`, `figures/gate_per_layer.png` |
| Manifold | TwoNN ID 4.2 / 5.2 (shuffled nulls ≈ 11.9 / 11.6); MDS stress-1 0.22; geodesic BFS→DFS 41, →unit-Dijkstra 58, →A* 71, →IDDFS 82, →bidir 95 | `results/manifold.json`, `results/geometry_b.json`, `figures/manifold_t{1,2}.png` |
| Commit | sha256 `186f7182ebb7c16a8cf808d18bfe63e6de25d3e71b619cd72affe8ce3d669e9a`, 45 events | `predictions/commit_log.jsonl` |
| Ban events | ban:bfs 62 BFS / 29 DFS / 9 unit-Dijkstra, compliance 0.18; ban:dijkstra 72 Dijkstra / 27 BF-SPFA / 1 other, compliance 0.22 | `results/contest.json`, `figures/ban_shift_on_manifold_t{1,2}.png` |
| Contest (primary) | mean log score geodesic −1.43, decoder −1.44, uniform −1.56, association −2.59; 0 top-1 hits | `results/contest.json` |
| C3 | all X inconclusive; shifts 61–99% residual | `results/c3_decomposition.json`, `figures/c3_shares_t{1,2}.png` |
| C2 removal (pre-declared) | 0/50 moved at α 0.5/1/2 on both tasks; 78–90% of outputs byte-identical to α=0 (random controls 80–96%); verdict "untestable" | `results/c2_removal.json`, `figures/removal_outcomes.png` |
| C2 exploratory full variant | α=2: no movement; α=4: 25/25 degenerate (no code) | `results/c2_removal.json` |
| Audit | 99 re-derived numbers, 0 mismatches; placebos fail | `results/audit_rederive.json` |

The paper is not written yet. These numbers are the "Results at a glance" section of `README.md`, and the figures
are the ones a report would use: the manifold (`figures/manifold_t*.png`), where the bans send the model
(`figures/ban_shift_on_manifold_t*.png`), the R gate, the C3 shares and the removal outcomes. `method_out.json`
(validated against the `exp_gen_sol_out` schema) holds one example per generated program (2310) and the 7 scored
contest events with their committed forecast distributions.
