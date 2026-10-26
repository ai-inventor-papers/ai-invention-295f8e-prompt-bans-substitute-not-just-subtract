# Reproducibility: evolving programs to find new algorithms (iteration 7, claim N)

This file records what was **actually run** to produce the published results, in order, on Ubuntu. Every path below
is relative to this artifact's folder.

## 1. Get the artifact

This artifact is one folder of a public GitHub repository.

```bash
git clone <repository-url>
cd <repository>/<this-artifact-folder>      # the folder that holds method.py and this file
```

**Declared input artifact, `art_j3Rm_lr2nzR6`.** This is the "source data for an algorithm-choice coding bench"
dataset. The repository publishes it as a sibling folder, `../art_j3Rm_lr2nzR6`, and this code needs its
`full_data_out.json`. The code resolves that folder through one constant, `DEP_DIR` in `src/common.py`, in this
order:

1. the environment variable `ART_J3RM_DIR`;
2. the sibling folder `../art_j3Rm_lr2nzR6`;
3. the original run layout.

If the dependency sits somewhere else, set `ART_J3RM_DIR=<path to its folder>`.

**Non-declared inputs.** These are frozen benches, labellers and prompts from earlier iterations. They are vendored
byte-for-byte into `inputs/vendor/`, with their original locations (relative to the runs root) and sha256s in
`inputs/vendor_manifest.json`. They are published with this folder, so a reader needs no other artifact.

**User uploads.** No user-uploaded file was used; the run's `user_uploads` folder was empty.

## 2. System, Python and libraries

**Hardware used:**

* 1 × NVIDIA RTX A4500, 20 GB VRAM, driver 595.91 (it reports CUDA 13.2);
* a container with 11 vCPUs (cgroup quota) and 57 GB RAM.

The GPU stages need about 19 GB of VRAM. Every other stage runs on the CPU.

**OS and system packages:**

* Debian 12 container. Ubuntu 22.04 or 24.04 works the same.
* CPython **3.12.14**. The sandbox runs candidate programs under a stdlib-only `python3.12 -I -S` interpreter, by
  default `/usr/local/bin/python3.12`, else `python3.12` on `PATH`; override it with `SANDBOX_PYTHON`.
* `uv` 0.6.14.
* No C compiler is needed. Without one, vLLM's `torch.compile` fails and the code falls back to
  `enforce_eager=True` automatically; that is what happened in this run.

**Environment.** These are the commands that were run; `pyproject.toml` pins all 172 installed packages exactly:

```bash
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r pyproject.toml   # or: ./restore.sh
```

The first resolve picked transformers 5.20.2, so it was then pinned to 4.57.6. The direct versions are:

| Package | Version |
|---|---|
| vllm | 0.11.0 |
| torch | 2.8.0 (+cu128 wheels from PyPI) |
| transformers | 4.57.6 |
| xformers | 0.0.32.post1 |
| triton | 3.4.0 |
| numpy | 2.2.6 |
| scipy | 1.18.1 |
| rapidfuzz | 3.14.6 |
| zss | 1.2.0 |
| loguru | 0.7.3 |
| openai | 3.36.1 |
| matplotlib | 3.11.2 |
| pytest | 9.1.1 |

`audit/rederive.py` and `audit/rederive_raw.py` need only the Python standard library.

## 3. Models, data and environment variables (names only)

**Models.** These are public Hugging Face models at pinned revisions. `src/engine.py` reads them from the Hugging Face
cache; if they are missing, it downloads them with `huggingface_hub.snapshot_download` at the same revision.

* `Qwen/Qwen3-8B` @ `b968826d9c46dd6066d109eabc6255188de91218` — the mutator and instruct model, bf16.
* `Qwen/Qwen3-8B-Base` @ `49e3418fbbbca6ecbdf9608b4d22e5a407081db4` — the BINT intents.

**Environment variables:**

* `HF_HOME` and `HF_HUB_CACHE` — cache location (optional).
* `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY` — the OpenRouter-compatible endpoint. They are used by:
  * labeller disputes;
  * the 10-control judge gate;
  * the advisory adjudication votes;
  * the optional large-mutator arm L.
* `ART_J3RM_DIR` (optional) — location of the dependency.
* `SANDBOX_PYTHON` (optional).
* `AII_DATA_FIG_GEN_SCRIPTS` (optional) — the folder of the house-style figure helpers. Without it, figures use plain
  matplotlib.

**API models used:**

| Purpose | Model |
|---|---|
| Label disputes | `google/gemini-2.5-flash-lite` (fallback `google/gemini-2.5-flash`) |
| Judges | `mistralai/mistral-medium-3.1`, `moonshotai/kimi-k2-0905`, `google/gemini-2.5-flash`, `deepseek/deepseek-chat-v3.1`, `openai/gpt-4.1-mini` |
| Arm L | `qwen/qwen3-235b-a22b-2507` (per-call fallback `qwen/qwen3-coder`) |

Total spend was USD 0.89 (`results/costs.json`, `results/openrouter_ledger.jsonl`).

## 4. Commands, in the order they were run

The seeds were:

* vLLM engine seed 7101;
* per-request seed `int(sha256("task|arm|index")) mod 2^31` (`src/common.py`, `stable_seed`);
* stress-input seeds T2 770002, T03 770003, A3 770043;
* search-database RNG `stable_seed(task, "S", "db")`.

Decoding is T 1.0, top-p 1, no top-k, max_tokens 1024 (1536 on T2), stop `"\n```\n"`, thinking off,
`max_model_len` 4096, `gpu_memory_utilization` 0.92, prefix caching on, `max_num_seqs` 48.

| # | Command | What it does | Wall time |
|---|---|---|---|
| 1 | `.venv/bin/python method.py --stage inputs` | Vendors the inputs (skipped when `inputs/vendor/` exists), then builds and verifies `inputs/tasks/{T2,T03,A3}.json`: every reference passes; stress outputs come from the fastest reference. | ~15 s |
| 2 | `.venv/bin/python method.py --stage corpus` | Known-solution corpus: **n_corpus 18,237** + 20 catalogue references → `data/corpus/`. | ~30 s |
| 3 | `.venv/bin/python -m pytest -q tests` | Unit tests U1–U5 (13 tests). | ~30 s |
| 4 | `.venv/bin/python method.py --stage commit0` | Commit #0: hypothesis, prompts, ladder, analysis code hash (`commitments.log`). | <1 s |
| 5 | `.venv/bin/python method.py --stage calib` | GPU: engine check (20 per task), calibration (30 per catalogue mode per task), throughput pilot. | ~10 min |
| 6 | `.venv/bin/python method.py --stage commit1 --gpu-hours 2.0` | s\*, engine-check verdicts, final N (Level 0+1). | ~5 s |
| 7 | `.venv/bin/python src/amend_intents.py` | amendment1: BINT-intent headroom. In the original session this was an inline snippet with identical content. | <1 s |
| 8 | `.venv/bin/python method.py --stage base` | GPU: Qwen3-8B-Base intents (T2/T03 2,000, A3 500). | ~7 min |
| 9 | `.venv/bin/python method.py --stage run --deadline-min 120` | GPU: arms S, NE, I0, EAP, BINT, B0 on T03 → T2 → A3. | ~56 min |
| — | (amendment2) | The critic's self-match exclusion was restricted to scoring the seed references themselves (a bug fix made before any decisive sample). It is already in the published `src/critic.py`; its record is `predictions/amendment2.json`. | — |
| 10 | `.venv/bin/python src/amend_level2.py` | amendment3: Level 2 on T03 (S 2,500; EAP and BINT 1,250). | <1 s |
| 11 | `.venv/bin/python method.py --stage run --plan predictions/amendment3.json --deadline-min 40` | GPU: resumes T03 from its saved search state. | ~14 min |
| 12 | `.venv/bin/python method.py --stage L --n-l 500` | Arm L via OpenRouter. It ran concurrently with step 9 and needs no GPU. | ~18 min |
| 13 | `.venv/bin/python method.py --stage label` | Final labels, with disputes sent to the judge, and the OOC screen. Run after each task finished; the last run came after step 11. | ~1 min |
| 14 | `.venv/bin/python method.py --stage adjudicate --tasks T03,T2,A3` | Dedup, clusters, commit #2, complexity probes, 10-control gate. **No judge passed**, so the pre-registered fallback F5 applies. | ~2 min |
| 15 | `.venv/bin/python src/advisory.py` | Ungated advisory votes of the pre-registered judge pair on all 244 candidates. | ~5 min |
| 16 | manual reads → `results/manual_reads.jsonl` | The executor's reads of all 244 candidates: 121 full and 123 structured. `src/manual_queue.py` prints the queue. These are published judgments; re-running cannot regenerate them. | ~45 min |
| 17 | `.venv/bin/python method.py --stage classes` | Final classes (manual read, propagated to cluster members), propagation and judge-vs-manual checks. | ~2 s |
| 18 | `.venv/bin/python method.py --stage analyse` | All statistics → `results/*.json`, `data/samples.jsonl`. | ~12 s |
| 19 | `.venv/bin/python src/rulecheck.py` | Arm-blind rule replication of level b → `results/levelb_rule_check.json`. | ~5 s |
| 20 | `.venv/bin/python method.py --stage outputs` | Figures F1–F6, `method_out.json`, then `audit/rederive.py`. | ~1 min |
| 21 | `.venv/bin/python <aii-json skill>/aii_json_format_mini_preview.py --input method_out.json` | Variants (see below). | <1 min |
| 22 | `python3 audit/rederive.py` and `python3 audit/rederive_raw.py` | Independent re-derivations. Both print `"ok": true`. | ~10 s |

**Step 21 without the pipeline tool.** `full_method_out.json` is the same content as `method_out.json`.
`mini_method_out.json` holds the first 3 examples of each dataset. `preview_method_out.json` is the mini version with
strings truncated to 200 characters.

**Exact reproducibility.**

* **CPU steps** are deterministic: corpus, evaluator, statistics, figures, audits.
* **GPU generation** uses per-request seeds, but vLLM batching is not guaranteed to be batch-invariant. A re-run on
  the same stack reproduces the distributions, but not necessarily every program byte-for-byte.
* **API outputs** (judges, arm L at T 1.0) can vary.
* **To re-check the published numbers**, run steps 17–22 on the published data. Those steps reproduce them exactly.

## 5. Expected outputs and numbers

**Where the results are:**

| Result | File |
|---|---|
| Verdict | `results/verdict.json` |
| Primary and secondary tests | `results/ratio_tests.json` |
| Per task × arm counts | `results/arm_rates.json` |
| Every generated program | `data/samples.jsonl` |
| Figures | `figures/F1_discovery_curves`, `F2_archive_heatmaps`, `F3_novelty`, `F4_adjudication`, `F5_lineage`, `F6_program_space_mds` (each as `.pdf` and `.png`) |

In the paper, these give the results table (arm rates and verdicts), the discovery-curve figure (F1), the
search-dynamics figure (F2, F5), the novelty figure (F3, F6) and the adjudication figure (F4).

**Corpus and screen thresholds:**

* n_corpus = 18,237.
* s\* = T2 0.359, T03 0.303, A3 0.608 (`predictions/commit1.json`).

**Engine check:** pass rate 1.0 on all three tasks. The default label appears in 20/20 programs on T2 and on T03; A3
shows both modes (15 prefix-suffix + 5 two-pointers).

**Primary test.** S vs K, where K = EAP by the max rule:

| Task | Level | X_S / N_S | X_K / N_K | R̂ | LB95 | Verdict |
|---|---|---|---|---|---|---|
| T2 | a | 46/1500 | 6/750 | 3.83 | 1.83 | NOT MET |
| T03 | a | 412/2500 | 31/1250 | 6.65 | 4.86 | NOT MET |
| A3 | a | 31/1000 | 17/500 | 0.91 | 0.54 | NOT MET |
| T03 | b | 78 | 0 | ∞ | 12.77 | STRONG |
| T2, A3 | b | 0 | 0 | — | — | NOT ESTIMABLE |

The overall verdict is NOT MET at both levels.

**Secondary contrasts:**

* T03 level b: S vs NE is 78 vs 0 (LB95 5.11); S vs I0 is 78 vs 2 (LB95 2.41).
* T2 level a: S vs NE is 46 vs 1 (LB95 3.10).
* Arm L vs S's first 500 calls, level b: 23 vs 9 (R̂ 2.56, LB95 1.28).

**Novelty:**

* 0 NOVEL ALGORITHM programs.
* Rule-of-three: ≤ 7.5% over 40 merged adjudicated clusters; ≤ 2.0% over 152 pre-merge clusters.
* The judge gate failed (best score Kimi K2 8/10), so the final classes are manual reads.
* Advisory judge κ is 0.42.
* The arm-blind rule replication agrees with the manual classes on 94.4% of distinct OOC programs.

**Audits:**

* `audit/rederive.py`: 109 checks, 0 mismatches.
* `audit/rederive_raw.py` re-derives all primary and secondary counts, R̂ and LB95 from the raw rows with exact
  binomial sums, again with 0 mismatches.
* The placebos fail as required:

  | Placebo | Result |
  |---|---|
  | Permuted arm labels | 4% significant |
  | Random flags | 3% significant |
  | Constant baseline | R = 1.0, LB95 0.87 |

* 0 rows predate their governing commit.
* The hash chain in `commitments.log` verifies.
