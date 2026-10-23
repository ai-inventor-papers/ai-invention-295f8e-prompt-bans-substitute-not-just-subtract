# Reproducing the iteration-8 record repair

These steps reproduce the corrected report, the value ledger, the tables and both audits exactly as produced on
2026-10-23. Everything runs on CPU. A rerun makes no paid API calls, because every judge response is cached in
`audit/judge_cache.jsonl`. Every path below is relative to this artifact's folder.

## 1. Get the artifact

This folder is one folder of the run's public GitHub repository. Clone the repository and change into this folder:

```bash
git clone <repository URL>
cd <repository>/<this artifact's folder>     # the folder that holds eval.py and this file
```

The inputs produced by other artifacts are their own folders in the same repository (siblings of this one). They are
named by artifact id in section 3.

## 2. System packages, Python and the environment

- **OS.** Ubuntu or any Linux with `bash`, `sed` and `git`. Nothing beyond the base system was installed.
- **Python.** 3.12 (3.12.14 was used).
- **uv.** 0.6.14 was used. Install it with `curl -LsSf https://astral.sh/uv/install.sh | sh` if it is missing.
- **Environment.** `uv sync` creates `.venv/` from `pyproject.toml` and `uv.lock`, with every package pinned to the
  version actually installed:

```bash
uv sync
# equivalently, what was actually run when the folder was created:
#   uv venv .venv --python=3.12
#   uv pip install --python=.venv/bin/python aiohappyeyeballs==2.7.1 aiohttp==3.14.5 aiosignal==1.4.0 attrs==26.1.0 \
#     frozenlist==1.8.0 idna==3.20 loguru==0.7.3 multidict==7.1.0 numpy==2.5.4 propcache==0.5.4 pyyaml==6.0.3 \
#     tenacity==9.2.1 typing-extensions==4.16.0 yarl==1.25.1
```

The sandboxed program tracer of the vendored kth-smallest bench (`inputs/bench_T03/bench/common/`) runs each
generated program in a fresh `python3.12 -I -S` subprocess. It uses `python3.12` from `PATH`, or the interpreter named
in `BENCH_SANDBOX_PYTHON`. The two audit scripts use only the standard library and run with any `python3` (3.10 or
newer).

## 3. Inputs, environment variables and keys

**Inputs from other artifacts.** They are read through one constant, `DEP_ROOT` (in `sections/common.py`, mirrored in
the two audit scripts). It is the folder that holds the iteration-7 artifact folders.
- On the run's own storage, `DEP_ROOT` is `../../../round-7`, relative to this folder.
- In the published repository, the default falls back to this folder's parent, where the artifacts are sibling folders.
- Each artifact is found by its folder name, or else by its artifact id.
- If your layout differs, set `AII_DEP_ROOT`.

| Artifact id | Folder name | Files read |
|-|-|-|
| art_veI9l_Rb9wDY | gen_art_experiment_33 | `results/{p1,novelty_audit,randinit_T2,randinit_ly_T2,deviations,m_manifold,c_routing,kstar_*,targets_*,site_*}.json`, `data/labels.jsonl`, `src/cfg7.py`, `src/analysis7.py`, `inputs/exp11/bench/T03_kth_smallest/{gate.json,gold_set.jsonl}` |
| art_pHL7LWNhpcCS | gen_art_experiment_34 | `results/f_analysis.json`, `results/p2_analysis.json`, `README.md` |
| art_MZAfDPVhM6Ui | gen_art_experiment_35 | `results/posthoc.json`, `results/test2.json` |
| art_8O5eaNc5gxJs | gen_art_experiment_36 | `results/e3_replicate.json`, `results/retag.json`, `data/samples.jsonl` |
| art_VhaHGe7SxV95 | gen_art_experiment_37 | `results/{program_classes,arm_rates,ratio_tests,L_vs_S}.json` |
| art_HY7uYZz-OjRW | gen_art_experiment_38 | `src/g2.py`, `src/cfg.py`, `results/g2_decisions.json`, `data/raw_g2dose.jsonl`, `README.md` |
| art_LzP2qPwUrANz | gen_art_evaluation_6 | vendored in `inputs/eval6/` (`positioning.json`, `report_corrected.md`, `corrections.json`) |

**Vendored inputs.** These live in this folder and are not fetched again:
- The report to correct: `inputs/report/current_report.md`. On the run's storage it came from
  `../../gen_strat/current_report.md`.
- The kth-smallest bench copy: `inputs/bench_T03/`, taken from exp33's own vendored bench.
- The record audit's files: `inputs/eval6/`.

Their sha256 hashes, and those of every dependency file read, are in `inputs/input_hashes.json`.

**Environment variables (names only):**
- `OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY`: needed only if `audit/judge_cache.jsonl` is deleted. The judges are
  `deepseek/deepseek-chat-v3.1` and `mistralai/mistral-medium-3.1`, temperature 0, `max_tokens` 200. A fresh run of
  the 10 gate controls plus 129 distinct programs per judge cost USD 0.095.
- `AII_DEP_ROOT` (optional): where the dependency folders are.
- `AII_REPORT_SRC` (optional): used only if the vendored report is missing.
- `AII_JSON_SKILL_DIR` (optional): the aii-json skill, used to write the mini and preview files and to validate the
  schema. Without it, `sections/outputs.py` writes the same three files itself and skips validation.
- `AII_WEB_TOOLS_DIR` (optional): the aii-web-tools skill, used only by `audit/web/run_fetches.sh`.

**Not needed.** No model, checkpoint or dataset downloads, and no GPU.

**User uploads.** No user-uploaded input was used. The run's `user_uploads` folder is private and unpublished, and
nothing in this artifact reads it.

## 4. The commands that were run, in order

Hardware: one container on an AMD Ryzen 9 7950X with a 14-CPU quota and 56 GB RAM. An RTX 4090 (24 GB) was present
and unused.

1. **Live positioning evidence.** `bash audit/web/run_fetches.sh`, about 2 minutes on 2026-10-23. It writes one
   `fetch_grep` output per neighbour into `audit/web/*.txt`. These are live web pages, so a later run can differ; the
   committed raw outputs are what `positioning.json` and Table 371b cite.
2. **Pipeline.** `uv run eval.py --stages all` (stages `s0,a,b,c,d,e,f,g,h,i,j,k,apply,audit,out`). Runtime: about
   25 s with the judge cache present. The first run's judge batch took about 1.5 minutes.

   During development I ran stage subsets; the final outputs come from `uv run eval.py --stages all`. One labeller
   revision round (A2) is part of the code, because the first rule version failed the Counter positive control (4/5).
3. **Audits.** The audit stage runs both scripts; they can also be run on their own:

   ```bash
   python3 -I audit/rederive.py        # 97 checks, 0 mismatches, 6/6 placebos fail as required
   python3 -I audit/headline_check.py  # 11/11 headline numbers re-derived, 5/5 placebos fail as required
   ```

**Seeds.** They are fixed in code:

| Seed | Used for |
|-|-|
| 20261022 | exp33's slot bootstrap, ported exactly (numpy `default_rng`, 2,000 resamples, percentile 2.5/97.5) |
| 20261023 | blind judge order; the stdlib bootstrap; the Spearman bootstrap |
| 7 | the 10-program agreement sample |
| 11, 5, 9, 3, 1, 2 | placebo shuffles |

## 5. What you should get

The headline values below come from `eval_out.json` `metrics_agg`. Every value is also in `corrections.json`, with the
value as recorded in the report, the recomputed value, a status and its source.

**Report edits, lint and audits**

| Quantity | Value | Where it appears |
|-|-|-|
| Report edits | 84 (`report_corrected.md`, `report.diff`) | every edited passage ends with "(iteration-8 correction)", directly or through its table's caption |
| Residual-claim lint | 35 hits before, 0 after (`tables/lint.csv`) | - |
| Apply test | passes; a mutated `old_text` fails it | - |
| Value ledger | 141 values: 68 MATCH, 7 CORRECTED, 63 NEW, 3 CARRIED | `corrections.json` |
| Labeller v2 validation | references 6/6; gold kappa 0.951 and runtime-vs-adjudicated 0.964 (unchanged); controls 5/5 | `tables/labeller_v2_validation.csv` |
| Judge gate | A 10/10, B 9/10; kappa(A, B) 0.963; rule against A 0.636, against B 0.640 | `audit/judge_gate.json` |
| Manual reads | 48 distinct programs | `tables/counting_sort_adjudication.csv` |

**Kth-smallest relabel and recovery**

| Quantity | Value | Where it appears |
|-|-|-|
| Full-state exchange of the forced counting-sort source | 29/30 counting sort (was 0/30) | 7.3.4; Tables 296, 300, 314 |
| Pooled kth recovery, ranks 1 / 4 / 16 | 1.0125 [0.952, 1.079] / 1.000 [0.926, 1.075] / 0.9875 [0.918, 1.065] (was 1.59 / 1.57 / 1.55) | Table 297 |
| Recovery by source and rank | `tables/recovery_by_source.csv` | new Table 297b |

**Controls, readouts and rates**

| Quantity | Value | Where it appears |
|-|-|-|
| Untrained-network ratios (shortest path only) | 0.013, 0.92, 5.08 | 7.3.5; Table 372 |
| Fork-margin Spearman | 0.804; opening LLR 0.869 | 7.4.3, 7.9, 7.10, closing |
| Gemma natural variance | below the random 95th percentile at ranks 1, 2 and 4 (`tables/gemma_natural_variance.csv`) | 7.8.3; Tables 364b, 364d |
| Search rate ratio against the instruction alone | 7.8, lower bound 2.41 (`tables/search_by_arm.csv`) | Table 372, 7.10, 7.11, closing |
| Positioning | 12 rows plus 2 workshop posters, all VERIFIED on 2026-10-23 (`positioning.json`) | new Table 371b |

All four output JSON files (`eval_out.json`, `full_eval_out.json`, `mini_eval_out.json`, `preview_eval_out.json`)
validate against `exp_eval_sol_out`. No paper exists yet: the paper step reads `report_corrected.md`, and the section
and table numbers above refer to it.
