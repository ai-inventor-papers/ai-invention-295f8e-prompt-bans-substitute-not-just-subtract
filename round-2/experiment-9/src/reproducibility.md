# Reproducing "Banning five path algorithms at once"

This file describes what was actually run, in order, on one machine on 2026-10-20 (UTC). There are two paths.
Path A re-runs every analysis from the published raw generations and teacher-forced scores, on CPU only. Path B
regenerates everything, which needs a GPU and the OpenRouter judge.

## 1. Get the artifact

The workspace is published as one folder of a public GitHub repository:

```bash
git clone <repository-url>
cd <repository>/<this-artifact-folder>      # the folder that contains method.py and this file
```

Every path below is relative to this folder.

## 2. System, Python and libraries

- OS: Linux x86_64 (Debian 12 container; Ubuntu 22.04 or 24.04 works the same). No C compiler is needed: vLLM runs in
  eager mode.
- Python 3.12.14 (`/usr/local/bin/python3.12`). Candidate programs run in a stdlib-only interpreter (`python3.12 -I -S`).
  Set `SANDBOX_PYTHON` if `python3.12` is neither at `/usr/local/bin` nor `/usr/bin`.
- `uv` 0.6.14.
- GPU (Path B only): one NVIDIA GeForce RTX 4090, 24 GB, driver 580.126.20 (CUDA 13.0 driver; the torch wheels bundle
  CUDA 12.8). 14 CPU cores and a 56 GB RAM limit (cgroup).
- Libraries: `pyproject.toml` pins all 176 installed packages exactly (from `uv pip freeze`). Examples: `vllm==0.11.0`,
  `torch==2.8.0`, `transformers==4.57.6`, `numpy==2.2.6`, `scipy==1.18.1`, `scikit-learn==1.7.2`, `ripser==0.6.12`,
  `matplotlib==3.11.2`, `loguru==0.7.3`, `openai==3.35.1`.

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python -c "import torch, vllm, transformers, sklearn, ripser; print(torch.cuda.is_available())"
```

## 3. Inputs, downloads and environment variables

- Model: `Qwen/Qwen3-8B`, revision `b968826d9c46dd6066d109eabc6255188de91218`, bf16, from the Hugging Face cache:
  `huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218`.
  The usual `HF_HOME` / `HF_HUB_CACHE` variables are honoured.
- Declared dependency `art_j3Rm_lr2nzR6` (gen_art_dataset_1, "Source data for an algorithm-choice coding bench").
  Only its `full_data_out.json` is read: the `concreteness_norms` neutral-noun bank, plus the nine other datasets in
  `mb/aux_datasets.py`. It is read through ONE constant, `common.DS_FILE`. The default is the sibling folder
  `../gen_art_dataset_1/full_data_out.json`; override it with `MB_DEP_DATASET=<path to full_data_out.json>`.
- The iteration-1 canonical suite (exp1 = art__skdlFp_o3e9) is already copied into `canon/` and `tasks/`, with sha256
  values in `results/provenance.json`. Nothing else from iteration 1 is read.
- No user-uploaded inputs are used.
- Environment variables, by name only:
  - `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY`: the blind judge and the gold-set judges (Path B, labelling only).
  - Optional: `HF_TOKEN`, `MB_VLLM_PORT` (default 8019), `MB_MAX_NUM_SEQS` (default 24) and `SANDBOX_PYTHON`.
  - Optional: `AII_JSON_SKILL_DIR`, used only to schema-validate the outputs.

## 4. Commands, in the order they were run

Every stage logs to `logs/<stage>.log`. The scaling stages (10 -> 100 -> full) record time per unit in
`logs/timing.json`.

### Path B: full regeneration (about 4.5 h wall clock here, about 1 GPU-hour)

```bash
uv run method.py freeze          # S1: prompts/frozen_prompts.json, neutral nouns, padding; commitments.log line 0
uv run method.py recheck         # S0: canonical exp1 labeller on its gold set (135/144) and 22 references (22/22)
uv run method.py refs            # S3: 25 references + 4 unit probes through the extended labeller (25/25, 4/4)
uv run method.py serve --session s1      # PID-managed `vllm serve` (eager, max_num_seqs 24, prefix caching, seed 0)
uv run method.py smoke           # forced smoke: 1 per paraphrase (150 programs), staged 10 -> 100 -> full
uv run method.py s1main          # baseline 2x10x10, single bans 2x5x20, T2 leave-one-survivor 5x5x20 (900 programs)
uv run method.py label --src data/raw_smoke.jsonl
uv run method.py smoke_decide    # descriptive variant where < 7/10 smoke programs are labelled as requested
uv run method.py forced_rest     # 3 more per paraphrase (plain) or 4 per paraphrase (descriptive): 500 programs
uv run method.py stop
uv run method.py label --src data/raw_smoke.jsonl
uv run method.py label --src data/raw_forced_rest.jsonl
uv run method.py label --src data/raw_session1.jsonl
uv run method.py keep            # keep rule (>= 70% of 40 forced programs labelled as requested)
uv run method.py validate        # 40-program gold set: gpt-4.1-mini + gemini-2.5-flash, deepseek-chat-v3.1 adjudicates
uv run method.py psets           # program sets (M <= 30, sample-major), halves, scrub + verification
uv run method.py score1a         # HF: self-checks, baseline (round-robin), denominators (10 F_j), base/forced/own states
uv run method.py select          # TOP / ARC / SCATTER (+ TOP5) from FRLP and the consensus geodesic matrix
uv run method.py score1b         # HF: FRLP cells (ban/mention/neutral twins, nonce, LOS, tier 3), 11,372 passes
uv run method.py aux             # corpus ladder (CORPUS forecast) and the other dependency datasets
uv run method.py commit          # forecasts + planned prompts + analysis/landing.py sha256 hash-chained
uv run method.py serve --session s2
uv run method.py session2        # TOP, ARC, SCATTER, TOP5: 4 x 5 templates x 20 = 400 programs
uv run method.py stop
uv run method.py label --src data/raw_session2.jsonl
uv run method.py score2          # HF: own/base states of session-2 programs + noun-B placebo
uv run method.py analyse         # landing.json, los.json, manifold.json, persistence.json, checks.json, figures
uv run method.py outputs         # data/samples.jsonl, method_out.json (+ full/mini/preview)
.venv/bin/python -I audit/rederive.py    # independent re-derivation + placebos
```

What actually happened, beyond the list above:

- The judge wording was revised once, after the gold gate missed in round 0, and the three `label` commands, `keep`
  and `validate` were run again (deviation D-gold-revision).
- The first vLLM server crashed on a logprobs request before writing any sample. It was restarted without logprobs.
- A 14-program trial of `score1a` was run and its outputs deleted before the full run.
- `select` was run twice: the second time added TOP5, before anything was committed.

### Seeds

- Each request is sampled with `seed = int(sha256('task|condition|template|paraphrase[|stage]')[:8], 16)`, stored in
  every row. vLLM bf16 sampling is reproducible at the distribution level, not token for token.
- Gold-set sampling uses `random.Random(0)`.
- Selection bootstrap: `numpy` seed 0. Landing bootstrap: seed 20261020. Manifold, probes and persistence: seed 0.
- Small-tier tests: seeds 20261020 (T1) and 20261021 (T2).

### Path A: CPU-only re-analysis

`uv run method.py` with no stage argument runs `outputs`, which rebuilds `method_out.json` and `data/samples.jsonl`
from the saved results. `uv.lock` (written by `uv run`) pins the resolution.

Path A starts from the published raw generations, labels, scores and denominators. `states/` is not published, so the
manifold and probe stages need Path B's `score1a` and `score2` first.

```bash
uv run method.py landing         # results/landing.json, results/los.json
uv run method.py extra           # results/checks.json (shingles, FRLP sanity, commit-order audit)
uv run method.py outputs
.venv/bin/python -I audit/rederive.py
```

Re-labelling with `uv run method.py label --src data/raw_session2.jsonl` reuses `data/program_eval_cache.jsonl` and
`labeller_ext/judge_cache.jsonl`, so it makes no new API calls.

## 5. What you should get

- `results/catalogue_keep.json`: 5 of 10 grid algorithms kept (BFS 40/40, DFS 40/40, IDDFS 37/40, greedy 35/40, IDA*
  36/40). The analysis catalogue has K = 7.
- `results/labeller_recheck.json`: 0.9375 and 22/22.
- `results/labeller_ext_validation.json`: gold 32/40 (round 0: 33/40), kappa 0.53, with unit-weight Dijkstra, JPS and
  bidirectional A* excluded.
- `results/landing.json`, multi-ban avoidance: TOP 0.13, ARC 0.37, SCATTER 0.04, TOP5 0.00 (all gates fail). Single
  bans: 0.86 (T1, BFS -> DFS 86) and 0.84 (T2, Dijkstra -> BF/SPFA 83). Disguise rates 0.41-0.92. ARC log score +1.06
  nats/program over uniform for every ladder-type forecast. All exact permutation p >= 0.33 per set and >= 0.11 pooled.
- `results/los.json`, "will": Dijkstra 0.95, BF/SPFA 0.51, bidirectional Dijkstra, Floyd and Dial 0.00.
- `predictions/forecasts_*.json` and `results/commit_summary.json`: FRLP-implied avoidance TOP 3e-14, ARC 0.9995,
  SCATTER 9e-9, TOP5 2e-18. `commitments.log` verifies, and its last line precedes the first session-2 request.
- `results/frlp_cells.jsonl`, L(base) T1: BFS 0.63, DFS -0.49, greedy -18.5, A* -30.8, IDDFS -30.9, BiBFS -47.0,
  IDA* -129.0. T2: Dijkstra -1.80.
- `results/manifold.json`: stress-1 0.025 (T1) and 0.006 (T2). `results/persistence.json`: no evidence of a loop.
- `results/independent_rederivation.json`: every number above recomputed through separate code, matching exactly.
  Placebo: on random survivor shares the permutation test rejects at its nominal discrete level (0.18 at p <= 1/6,
  floor 1/6), so it is not vacuous.
  Shuffling condition labels among the four multi-bans leaves the avoidance range where it is (real 0.37; shuffled
  mean 0.33, 95th percentile 0.41). The four lists produce the same BFS/DFS mix (`results/posthoc_mix_homogeneity.json`:
  chi-square p = 0.48), so the avoidance differences reflect which of BFS and DFS is on each list.
- Figures: `figures/fig_landing.*`, `figures/fig_los.*`, `figures/fig_manifold_*` and `figures/fig_kstab_*`.

These numbers are the artifact's results section (C4 multi-ban test) in the run's report. Absolute timings vary with the
GPU, and vLLM sampling is not token-identical across runs.
