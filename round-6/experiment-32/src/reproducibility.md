# Reproducibility: panel II landing test (iteration 6)

This file describes what was **actually run** on 2026-10-21/22 (UTC), in order, and what a reader should get.
Every path is relative to this folder. No secret values appear here; environment variables are named only.

## 1. Get the artifact

The workspace is published as one folder of a public GitHub repository:

```bash
git clone <repository-url>
cd <repository>/<this-artifact-folder>        # the folder that holds this file, method.py and pyproject.toml
```

The declared dependency **art_j3Rm_lr2nzR6** ("Source data for an algorithm-choice coding bench") is published as a
sibling folder of the same repository. It is read through ONE environment variable, `AII_DEP_ART_J3RM`. Its default is
the sibling folder `../art_j3Rm_lr2nzR6`, which must hold `full_data_out.json`. Only `src/extract_sources.py` reads it.
Its output, `inputs/sources.json`, is already in this folder, so the CPU re-analysis does not need the dependency.

The read-only iteration-2..5 inputs this run used are vendored under `vendor/`, so the reader needs no other run
folder:

- iteration-5 B-unit rows: `vendor/exp26/samples_B_nocode.jsonl`, with its source hash beside it;
- pooled iteration-5 inputs: `vendor/exp25/` and `vendor/exp26/`;
- r_Q: `vendor/exp23/qwen_ratio.json`;
- twin templates: `vendor/exp7/frozen/`;
- hull code: `vendor/exp27/src/`;
- exp19 and exp20 hooks.

There were **no user-uploaded inputs** (the run's upload folder was empty).

## 2. System, Python and libraries

- **OS:** Ubuntu/Debian-like Linux x86_64 (the run used Debian 12, kernel 6.8, a container capped at 6 vCPUs and 66 GB
  RAM).
- **GPU:** one NVIDIA L4 (23 GB VRAM, compute capability 8.9), driver 595.91, CUDA 13.2 runtime on the host; the
  wheels use CUDA 12.8 (torch 2.8.0+cu128).
- **Python:** 3.12.14.
- **Package manager:** `uv` (no pip in the venvs).

**Main environment** (HF transformers, analysis, labellers): every package is pinned in `pyproject.toml`, which equals
`uv pip freeze` of `.venv` with 89 packages, and in `uv.lock`. Key pins:

- torch 2.8.0
- transformers 4.57.6
- tokenizers 0.22.2
- accelerate 1.15.0
- numpy 2.2.6
- scipy 1.18.1
- pandas 3.0.6
- matplotlib 3.11.2
- openai 3.35.1
- loguru 0.7.3
- jsonschema 4.25.1
- pytest 8.4.2

```bash
uv sync                    # creates .venv from pyproject.toml / uv.lock (took ~4.5 min on the run's network FS)
```

**vLLM environment** (unhooked sampling only, a separate process so it cannot perturb the HF pins): pinned in
`requirements-vllm.lock.txt` (157 packages), which equals `uv pip freeze` of `.venv_vllm`. vllm 0.11.0 installed
transformers 5.20.2, which fails to load the Qwen tokenizer (`all_special_tokens_extended`), so transformers was pinned
back to 4.57.6:

```bash
uv venv .venv_vllm --python 3.12
uv pip install --python .venv_vllm/bin/python vllm==0.11.0
uv pip install --python .venv_vllm/bin/python transformers==4.57.6 tokenizers==0.22.2
# exact closure: uv pip install --python .venv_vllm/bin/python -r requirements-vllm.lock.txt
```

`restore.sh` runs the environment steps above plus the model downloads below.

## 3. Models, data and keys

**Models** (in the Hugging Face cache named by `HF_HUB_CACHE`; never stored in this folder):

- `Qwen/Qwen3-8B` at revision `b968826d9c46dd6066d109eabc6255188de91218` (instruct);
- `Qwen/Qwen3-8B-Base` at revision `49e3418fbbbca6ecbdf9608b4d22e5a407081db4` (base).

```bash
.venv/bin/python -c "from huggingface_hub import snapshot_download as s; s('Qwen/Qwen3-8B', revision='b968826d9c46dd6066d109eabc6255188de91218'); s('Qwen/Qwen3-8B-Base', revision='49e3418fbbbca6ecbdf9608b4d22e5a407081db4')"
```

The run-time scripts locate the snapshots as `$HF_HUB_CACHE/models--Qwen--Qwen3-8B[-Base]/snapshots/<revision>`
(`src/cfg5.py:model_path`; the vLLM driver takes the snapshot folder as `--model`).

**Environment variables** (names only):

| variable | used by | needed for |
|---|---|---|
| `HF_HUB_CACHE` | `src/cfg5.py`, the vLLM commands | model snapshots |
| `HF_TOKEN` | huggingface_hub | optional (public models) |
| `OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY` | `src/judge5.py`, `src/novelty6.py` | the blind judges (`google/gemini-2.5-flash`, `openai/gpt-4.1-mini`, `deepseek/deepseek-chat`); cached in `data/judge_cache.jsonl` and `data/novelty_cache.jsonl`, so re-running the analysis costs nothing |
| `AII_DEP_ART_J3RM` | `src/extract_sources.py` | the dependency folder (default `../art_j3Rm_lr2nzR6`) |

## 4. What was run, in order

Wall clock: about 4 h 40 min, from 19:37 to 00:16 UTC. GPU time: HF hooked/CRN sampling 1.44 h (450 batches of 20
rows), vLLM sampling 0.61 h, plus model loads. OpenRouter: USD 0.33 over 1,468 judge calls.

Every seed is derived by sha256 from fixed strings (`predictions/protocol_v6_panelII.json` -> `dose.seeds`):

- ESC directions: `int(sha256('iter6|panelII|<u>|dir|<k>')[:8], 16)`;
- PN and GTN directions: `'iter6|panelII|<u>|PN|<alpha>|<w>|<s>'` and the same string with `GTN`;
- CRN uniforms of new units: `'iter6|crn|<u>|<w>|<s>'`; iteration-5 units reuse the exp26 stream;
- vLLM request seeds: `'iter6|vllm|...'`;
- bootstraps: `numpy.random.default_rng(20261021)`.

| # | command | what it does | time |
|---|---|---|---|
| 1 | `.venv/bin/python src/extract_sources.py` | 12 LeetCode rows + keyword rows + noun bank + validation subsets -> `inputs/sources.json` | 10 s |
| 2 | `.venv/bin/python src/protocol6.py` | **commit #0** (`predictions/protocol_v6_panelII.json`, 20:12:53Z, before any sample) | 1 s |
| 3 | vLLM job `screenB_instruct` (see 4a) | B1-B7 twin top-up (T 1.0 k 10-39, T 1.3 k 0-19) + forced programs | 5 min |
| 4 | `.venv/bin/python src/unitbuild.py II1` (... II6) | gate stage (i): tests, two oracles, references, mutants, labellers | 1 min/unit |
| 5 | `.venv/bin/python src/label5.py` (background daemon) | sandboxed tests + runtime tracer + AST labels -> `data/labels.jsonl` | all day |
| 6 | prompts + vLLM `new1_instruct`, `base1`, `instruct2` (4a) | II1-II6 twin/T 1.3/forced/association; base 200 chat + 100 plain + 30 intents; forced top-up + BINT code | 28 min |
| 7 | `.venv/bin/python src/judge5.py controls`; `.venv/bin/python src/gate2.py II1,II3,II4,II5,II6` | judge control gate (6/6 each); gate stage (ii) | 2 min |
| 8 | `.venv/bin/python src/gpu6.py --plan data/gpu_plan.json` (background) | HF: twin CRN k 0-9, q_lik scoring, then nudges once committed | daemon |
| 9 | `.venv/bin/python src/m_screen.py`; analysis commit (`commit5.commit`, tag `analysis_commit`) | M signs from iteration-5 data; analysis code + schema + tests committed at 22:11:51Z | 1 min |
| 10 | `.venv/bin/python src/quantities6.py II1,II3,II4,II5,II6,II2` | per-unit forecasts + **unit commits** (22:12Z), first nudge 22:18Z | 20 s |
| 11 | `src/unitbuild.py II7,II8`; vLLM `new2_instruct`, `new2_base`, `new2_bint`; `src/gate2.py II7,II8` (+ II7 `--revision`); `src/quantities6.py II8` / `II7` | second wave (`logs/switch_vllm.sh`, `logs/watch_ii78.sh`, `logs/watch_ii7.sh`) | 50 min |
| 12 | `.venv/bin/python src/quantities6.py B1,...,B7`; `src/gpu6.py --plan data/gpu_plan_v3.json` | SCREEN commits; II7/II8 nudges; B-unit alpha-4 ESC, PN alpha 4, GTN alpha 2; HF re-draw of iteration-5 twin slots | 60 min |
| 13 | `.venv/bin/python src/gpu_tests6.py` | G1-G6 GPU tests -> `results/tests_gpu.json` | 2 min |
| 14 | adjudication of remaining disagreements; `src/base_audit6.py II1,...,II8`; `src/novelty6.py` | judges | 5 min |
| 15 | `.venv/bin/python method.py` | final CPU stage (below) | 8 min |

4a. Every vLLM job was built with the `src/requests6.py` builders. The builders write `data/vllm_req/<job>.jsonl`;
those files are kept, so a job can be re-run without rebuilding. Each job was run as:

```bash
.venv_vllm/bin/python src/vllm_gen.py --model "$HF_HUB_CACHE/models--Qwen--Qwen3-8B/snapshots/b968826d9c46dd6066d109eabc6255188de91218" \
    --requests data/vllm_req/<job>.jsonl --out data/vllm_out/<job>.jsonl --max-num-seqs 128
.venv/bin/python src/requests6.py ingest <job> [--model-tag base]     # -> data/samples_raw.jsonl
```

For base jobs, use the base snapshot. Throughput was 18-40k programs/h for instruct and 7-10k/h for base.

**Re-running only the analysis (CPU, no GPU, no API spend: every judge answer is cached):**

```bash
uv run method.py                          # outputs6 (events, frozen analysis, figures, method_out.json),
                                          # audit/commit_order.py, audit/rederive.py, src/cpu_checks6.py, README
python3 -I audit/rederive_headlines.py    # second independent re-derivation of the headline numbers
.venv/bin/python -m pytest -q -c pytest.ini tests/test_pool_l1.py     # 9 synthetic checks of the frozen analysis
```

`src/cpu_checks6.py` also checks seed disjointness. It reads the iteration-4/5 sibling run folders, which exist only on
the original run volume; in the published repository that check finds no old seeds and says so.

## 5. What a reader should get

| output | expected content |
|---|---|
| `results/l1.json` (`verdict`) | **DESCRIPTIVE** |
| L1a (tail-empty events) | r_u hits 3/4 (II4/ESC, II5/ESC, II5/PN, II7/GTN), exact Poisson-binomial p = 0.1042 (6 events required) |
| L1b (discordant events) | b = 6, c = 3, ties 0, one-sided sign-test p = 0.2539 (FAIL); unit level b = 2, c = 1 over 3 units |
| hit counts on the 13 CONFIRMATION events | r_u 9, qlik_top1 6, t_u 9/9 where defined |
| log scores (`results/l1.json`, `log_scores.E`) | mean D_lik = 0.311 (one-sided LB 0.07), mean D_tail = 0.005 (LB -0.25) |
| `results/l2.json` | 6 of 940 correct off-default content-free nudged programs fall outside the base repertoire (II1 bisect_positions) |
| `results/m.json` | beta: rho = 0.946 over 7 units, one-sided exact p = 0.0016, Holm p = 0.010 (SUPPORTED); the other 5 candidates are not supported |
| `results/rederive.json`, `results/rederive_headlines.json` | 0 mismatches; placebos fail (random r_u at chance, shuffled E_u rejects about 3%, permuted q_base loses the D_lik advantage, swapped forecasts flip L1b) |
| `results/commit_order.json` | 0 chain breaks, commit #0 before the first sample, analysis code before the first nudge, 0 nudge rows before their unit commit |
| `results/tests_gpu.json` | CRN determinism; alpha-0 identity 20/20 (ESC) and 10/10 (GTN); max realised-dose error 0.0016; 5,700/5,700 identical vLLM prompt ids |
| `landing_events.json`, `units.json` | the pooling files (schema `schema/iter6_landing_v1.json`) for the next round's panel I + II test |
| `method_out.json` (+ full/mini/preview) | exp_gen_sol_out; all analyses in `metadata` |
| `figures/F1`-`F6` | landings per event, log-score forest, escape heatmap, base vs tail composition, M candidates, knob prices |

There is no paper yet. These numbers feed the panel-II paragraph of the iteration-6 write-up. F1 is the landing figure,
F2 the forecast comparison and F5 the M result. The README tables repeat every number above.

Sources of run-to-run variation if re-sampled:

- HF sampling is CRN-deterministic on the same GPU, kernels and batch shape (G1).
- vLLM rows use fixed per-request seeds but are not bit-reproducible across vLLM builds.
- bf16 numerics differ across GPU types: the iteration-5 twin slots re-drawn on the L4 agreed per slot 0.96-1.0 with
  the RTX 4090 originals.
- Judge answers are cached; fresh judge calls may differ slightly.
