# Reproducing "Do a few early tokens decide the algorithm?"

These are the steps that were actually run, in order. All paths are relative to this folder.

## 1. Get the artifact

The workspace is published as one folder of a public GitHub repository:

```bash
git clone <repository-url>
cd <repository>/<this-folder>      # the folder that contains method.py
```

## 2. System, Python and libraries

- OS: Debian 12 / Ubuntu 22.04+ (Linux x86_64). Hardware used: 1x NVIDIA RTX A4500 (20 GB VRAM, driver 570, CUDA 12.8), 12 CPU cores, 57 GB RAM.
- Python 3.12 and [uv](https://github.com/astral-sh/uv) 0.6+ (`pip` is never used).

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r requirements.txt   # what was run (resolves to the pins below)
# exact pins of the environment that produced the results are in pyproject.toml:
#   vllm==0.11.0, torch==2.8.0 (+cu128 wheel), transformers==4.57.6, scikit-learn, numpy, ruptures, ...
```

`pyproject.toml` lists every installed package pinned to the exact version (`uv pip freeze`).

## 3. Model, data and keys

- Model: `Qwen/Qwen3-8B` from the Hugging Face Hub (about 16 GB, bf16). It downloads automatically on first use;
  to pre-fetch: `huggingface-cli download Qwen/Qwen3-8B`. Set `HF_HOME` if you want a specific cache location.
- No external dataset: the two tasks, their 40 hidden test cases each and the reference solutions are generated
  by seeded code in `tasks/` (`python -m tasks.build_tasks`).
- The OpenRouter judge (used only in the analysis phase) needs the environment variables `OPENROUTER_BASE_URL`
  and `OPENROUTER_API_KEY` (names only; supply your own). The judge spent well under 1 USD. Set `SKIP_JUDGE=1` to
  run the analysis without it (labels then come from the runtime tracer / AST rules only).
- No user-uploaded input is used.

## 4. Commands, in the order they were run

```bash
# S1: hidden tests, reference timing (3x under a 5-process load), per-case limits, gate  (~1 min)
.venv/bin/python -m tasks.build_tasks
# T2/T3: labeller + harness unit tests (references, bad programs, timeouts, no_code, cache)  (~20 s)
.venv/bin/python tests/test_labeller.py
# gen1 (GPU, vLLM): engine tests T4/T5, then S6 pools (staged: paraphrase 0, then all 10)  (~10 min)
.venv/bin/python method.py --phase gen1
# gen2 (GPU, vLLM): S7 screen, S8 change points, S9 localise + confirm + controls,
#                   S10 prompt swap, S11 fork-window knob (+ predictions.json hashed before S10/S11)  (~50 min)
.venv/bin/python method.py --phase gen2
# S12 (GPU, HF transformers, after vLLM exited): residual states at 8 positions x layers 8..28  (~5 min)
.venv/bin/python method.py --phase states
# S13/S14 (CPU + OpenRouter judge): adjudication, readouts, probes, verdict, figures, method_out.json (~10 min)
.venv/bin/python method.py --phase analysis        # also the default: `uv run method.py`
```

Seeds: every vLLM request uses `seed = sha256(task, condition, paraphrase, arm/base path, prefix_len, ...) mod 2^31`
(`common.stable_seed`); the vLLM engine seed is 0; vLLM gives the i-th of n parallel samples `seed + i`. CPU
statistics use fixed numpy seeds. vLLM ran with `dtype=bfloat16, max_model_len=2048, max_num_batched_tokens=2048,
enable_prefix_caching=True, max_num_seqs=48, enforce_eager=True` (the two CUDA-graph settings failed to initialise
on the 20 GB card, the plan's retry ladder). Decoding: `top_p=1.0, top_k=-1`, stop string `"\n```\n"`.

Bit-exact regeneration is not guaranteed across GPUs/drivers (bf16 kernels and batch composition change logits
slightly); the labelled per-sample rows in `generations/*.jsonl` are the record the analysis reads.

## 5. What you should get

- `method_out.json` (= `full_method_out.json`; `mini_`/`preview_` are truncated views): `metadata` holds the verdict
  with its rule trace, every readout (pools, screen R0 / fixed-by / F1 / F2 / F3, forks, swap, knob table and
  contrasts K1-K4, probe summary, T6 sensitivity curve, test results, deviations, prereg/predictions hashes);
  `datasets` holds per-example rows (knob arms per task, ban-condition pools, screen base paths, swap paths).
- `generations/*.jsonl`: every generation with its label (`pools`, `screen`, `localise`, `confirm`, `swap`, `knob`).
- `forks.json`, `swap.json`, `knob_table.json`, `probes.json`, `summaries/*.json`, `figures/*.png`.
- Headline numbers are listed in `README.md` (section "Results").
