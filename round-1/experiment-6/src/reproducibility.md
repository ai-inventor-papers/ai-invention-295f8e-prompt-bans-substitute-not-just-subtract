# Reproducibility: Temperature and seeds, new ideas or rewording?

This file describes what was actually run to produce the results in this folder. Commands are given in order, with
seeds, hardware and approximate runtimes. Every path is relative to this folder.

## 1. Get the artifact

This folder is published as one folder of a public GitHub repository:

```bash
git clone <repository-url>
cd <repository>/<this-artifact-folder>        # the folder containing method.py
```

No input from another artifact is needed: the tasks, hidden tests, references and labeller are all built here.
The user uploaded no data for this run.

## 2. System, Python and libraries

- **OS and hardware used:** Linux 6.8 (Debian 12 container), 1 × NVIDIA GeForce RTX 5090 (32 GB VRAM), driver
  595.91.07 (CUDA 13.2). The cgroup allowed 14 CPU cores and 55 GB RAM.
- **NVIDIA driver:** any Ubuntu machine with a driver that supports CUDA 12.8 works. The torch wheel ships its own
  CUDA 12.8 runtime.
- **System packages:** none beyond the NVIDIA driver and `curl`. No C compiler was available, so vLLM ran with
  `enforce_eager=True`; this affects speed only.
- **Python and uv:** Python 3.12.14 and uv 0.6.14 (`curl -LsSf https://astral.sh/uv/install.sh | sh`).
- **Virtual environment:** every package is pinned in `pyproject.toml`, which is the full `uv pip freeze` of the venv
  that was used. Key versions: vllm 0.11.0, torch 2.8.0 (+cu128), transformers 4.57.6, numpy 2.2.6, scipy 1.18.1,
  scikit-learn 1.9.1, openai, loguru, matplotlib.

  ```bash
  uv venv .venv --python 3.12
  uv pip install --python .venv/bin/python -r pyproject.toml
  ```

## 3. Model, data and keys

- **Model:** `Qwen/Qwen3-8B`, revision `b968826d9c46dd6066d109eabc6255188de91218`:

  ```bash
  huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218
  ```

  The scripts set `HF_HUB_OFFLINE=1` by default. Download first, or export `HF_HUB_OFFLINE=0`. The run read the
  weights from a shared Hugging Face cache pointed to by `HF_HOME`; the default `~/.cache/huggingface` works too.
- **Data:** none to download. Hidden tests are generated with fixed RNG seeds (T1 seed 1019, T2 seed 2019) by
  `tasks/t1_grid.py` and `tasks/t2_sssp.py`. They are also committed under `tests/`, with sha256 values in
  `method_out.json` → `metadata.setup.hidden_tests_sha256`.
- **Environment variables** (names only):
  - `OPENROUTER_API_KEY` and `OPENROUTER_BASE_URL`, for the blind judge, gold-set judges and lexicon audit through
    OpenRouter. This run spent about $0.10.
  - Optionally `HF_TOKEN`, `HF_HOME` and `HF_HUB_OFFLINE`.
- **Judge models (OpenRouter ids):**
  - `google/gemini-2.5-flash-lite`: primary judge and lexicon audit.
  - `openai/gpt-4.1-mini` and `deepseek/deepseek-v4.1-flash-1017`: gold-set judges.
  - `google/gemini-2.5-flash`: adjudicator.

## 4. Commands, in the order they were run

| # | Command | What it does | Runtime |
|---|---|---|---|
| 1 | `.venv/bin/python prompts/build.py` | Builds the 552 prompts and checks the scaffold: the last 132 (T1) / 119 (T2) tokens are identical across conditions, and no algorithm name appears in the seeds or descriptions | ~1 min |
| 2 | Write `forecast/predictions_screen.json`; `sha256sum` → `logs/forecast_sha256.txt` | Hash-commits predictions P1–P8 **before any sampling** (`4d2d3fc7…333f6f`) | – |
| 3 | `.venv/bin/python gen/arms.py --smoke` | GPU smoke test: 32 A0 samples, 3 thinking traces, 1 trace forced to truncate at 64 tokens | ~6 min (engine load dominates) |
| 4 | `.venv/bin/python gen/arms.py --deadline 20:40 --n-think 10` | Capacity probe (64 samples, 2,844 tok/s), then arms A0, A1, A2, A6a, A3, A5, A4s1, A4s2, A6b, A6c, A6d (5,220 generations in `results/raw/`) | 38 min |
| 5 | `.venv/bin/python tasks/t1_grid.py`, `tasks/t2_sssp.py`, `harness/run_tests.py` | Hidden tests (41 + 39 cases); per-case limit = max(1 s, 10 × median BFS/Dijkstra time over 3 harness runs); all 16 references pass within limit/3; negative controls fail | ~1 min |
| 6 | `.venv/bin/python labeller/tracer.py`, `labeller/ast_rules.py` | Runtime and AST labels are 100% correct on all references and variants | <1 min |
| 7 | `.venv/bin/python labeller/label.py --workers 12 --judge-cap 1.0` | Tests, tracer and AST for 3,194 unique programs; judge on the disagreements | ~5 min |
| 8 | `.venv/bin/python hooks/states.py` | HF block: hook checks, R states at 36 layers, probes and l* (T1 27, T2 22), trajectory states | 18 min |
| 9 | Rule revisions 1 and 2 (listed in `results/labeller_gate.json` → `revisions`), then `.venv/bin/python labeller/label.py --workers 12 --judge-cap 1.0 --relabel` after each | Re-runs tracer and AST with the revised signatures; test results are reused | ~2 min each |
| 10 | `.venv/bin/python labeller/gold.py` | Gold set (references + 30 programs per task), two judges + adjudicator, gate | ~1 min |
| 11 | `.venv/bin/python analysis/test_metrics.py`; `.venv/bin/python labeller/test_rewrite.py` | DA@K vs hand computation and Monte Carlo; EA; Jaccard; isotropic null; checker; rewrite invariance | <1 min |
| 12 | `.venv/bin/python method.py analyze` | `analysis/run_all.py`: sections 8a–8i, figures, verdicts, forecast check | 3.5 min |
| 13 | `.venv/bin/python method.py output` | `method_out.json` (5,220 examples + all results); validated against `exp_gen_sol_out` | <1 min |
| 14 | `.venv/bin/python verify_headlines.py` | Independent re-derivation + placebo tests → `results/verify_headlines.json` | <1 min |
| 15 | `aii_json_format_mini_preview.py --input method_out.json` | `full_` / `mini_` / `preview_method_out.json` | <1 min |

`.venv/bin/python method.py all` runs the same pipeline in one go: setup, then generate, label, gate, hooks, analyze,
output. The labeller code already contains revisions 1 and 2, so a fresh `label` stage gives the final labels without
`--relabel`.

**Seeds and decoding settings:**

- Every vLLM request has its own seed, `stable_seed(task, condition, paraphrase, sample, arm, T, sampler,
  thinking)`. This is the first 31 bits of a sha256; see `common.py`.
- The engine seed is 0, with `generation_config='vllm'`, `min_p=0`, all penalties neutral, and `top_k=-1` meaning
  off.
- Gen-then-select picks the listed item with `numpy.default_rng(20261019 + sample_id)`, plus 100000 for T2.
- Analysis seeds are fixed inside `analysis/*.py`.
- vLLM batching is not bit-deterministic. A re-run gives statistically equivalent samples, not identical bytes. That
  is why the raw generations are kept in `results/raw/`.

## 5. What you should get

- **`results/analysis.json` → `bfs_dijkstra_table`:**
  - T1 BFS share of classified programs: 797/800 thinking off, with every cell ≥ 0.99; 800/800 thinking on.
  - T2 Dijkstra share: 797/800 thinking off, 800/800 thinking on.
  - Pass rates are 0.95–1.00. Plotted in `figures/fig1_bfs_dijkstra_share.png`.
- **`seeds_instructions`:**
  - Entropy and word seeds shift the modal share by ≤ 1 pp, and their 90% CIs lie within ±15 pp.
  - The semantic seed on T2 shifts Dijkstra by −67.4 pp toward Bellman-Ford (one-sided cluster-permutation
    p ≈ 0.0004).
  - "Fully novel" lowers Dijkstra by 14.6 pp on T2. Plotted in `figures/fig6_condition_label_mix.png`.
- **`ideas_by_phrasings`:**
  - On T1, thinking off, phrasing clusters (θ=0.8) grow from 3–4 at T=0.3 to 24–36 at T=1.3, while there are 1–2
    ideas.
  - The log-PPI slope is about +1.2 per unit T. Plotted in `figures/fig2_ideas_vs_phrasings.png`.
- **`subspace_test`:** read-position displacement ratios.
  - Entropy seed 0.73 / 1.16; word seed 1.56 / 1.01; semantic seed 3.42 / 3.70 (T1 / T2).
  - Plotted in `figures/fig3_displacement_ratios.png`.
- **`variance_split`:** complement variance rises with T; the raw mode-share slope is flat on T1 and +0.014 on T2.
  Plotted in `figures/fig4_variance_split.png`.
- **`gen_then_select`:** DA_idea@25 of 3.98 (T1) / 3.00 (T2) against 1.26 / 1.00 for A0.
- **`verdicts.overall`:** "MIXED: failing sub-claims -> S-T6 variance-share slope; random-seed equivalence at R (1.5x
  bound)".
- **`forecast_check`:** 6 of 8 predictions hit.
- **`results/labeller_gate.json`:** the gate fails by the strict criteria on both tasks (flag `labeller_gate_failed`),
  so all results are descriptive. References agree 100%; population kappa is 0.88 / 0.85.
- **`results/verify_headlines.json`:** the same headline numbers through an independent code path; placebo p-values
  of 0.49–1.0.

These outputs feed the paper-writing step. The figures in `figures/` are the paper figures (fig1 to fig6), and every
number quoted above lives in `method_out.json → metadata.results`.
