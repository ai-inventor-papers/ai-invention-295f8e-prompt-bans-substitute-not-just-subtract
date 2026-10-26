# Reproducing "Fixing the record, freezing the push screen"

This artifact is a CPU-only re-analysis. It generates no model text. Its only network calls are the cached LLM-judge calls of the 'other' audit (0d). Every path below is relative to this artifact's folder.

## 1. Get the artifact

The workspace is published as one folder of a public GitHub repository. The 11 dependency artifacts it reads are published in the same repository as sibling folders.

```bash
git clone <repository URL>
cd <repository>/<this artifact's folder>      # the folder that contains eval.py, screen.json, screen_rule.py
```

## 2. System, Python and libraries (what was actually used)

- OS: Debian 12 container (any recent Ubuntu works). No system packages are needed beyond `curl` and `git`.
- uv 0.6.14 and Python 3.12.14 (uv-managed).
- Hardware: 6 vCPUs (AMD EPYC 7443, cgroup quota 5.6 CPUs) and a 28 GB RAM limit. The pod had an NVIDIA RTX 2000 Ada (16 GB), which was **not used**.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh        # installs uv (0.6.14 was used)
uv python install 3.12
uv sync --frozen                                       # creates .venv with the exact pins in pyproject.toml / uv.lock
```

What was actually run on the server, before the versions were frozen, was:

```bash
uv venv .venv --python=3.12
uv pip install --python=.venv/bin/python numpy pandas scipy scikit-learn matplotlib loguru openai pyarrow tenacity requests pytest
```

That resolved to the versions now pinned in `pyproject.toml`. The key ones are numpy 2.5.4, pandas 3.0.6, scipy 1.18.1, scikit-learn 1.9.1, matplotlib 3.11.2, pyarrow 26.0.0, loguru 0.7.3, openai 3.35.1, requests 2.34.2, tenacity 9.2.1 and pytest 9.1.1. A uv venv has no `pip` executable, so the pins come from `uv pip freeze --python .venv/bin/python`.

## 3. Inputs, environment variables and keys

**Dependency artifacts.** They are read only, and each is resolved by artifact id:

| Artifact id | Role | Files read |
|---|---|---|
| art_pVlCZ272hDV7 | exp17 | `data/labels.jsonl`, `results/c2d.json`, `figures/fig7_manifold.png` |
| art_1AYTO1Epb_7t | exp13 | `data/samples.jsonl`, `results/c1_events.jsonl`, `predictions/proximity.json` |
| art__5akZ9W9iZM4 | exp16 | `data/samples.jsonl`, `results/{landing_by_route,route,screen_paths,prefill,replication}.json` |
| art_Q-qh-9HhPoWo | exp15 | `data/samples.jsonl`, `results/c1_events.jsonl`, `predictions/forecasts.json`, `results/push_hook_stats.json` |
| art_WiY4wqHLb9Gy | exp14 | `data/samples.jsonl`, `results/{c1_events.jsonl,c1_summary.json,other_reports.json,advance_rule_null_calibration.json}` |
| art_ccAbfJVcv0LO | exp18 | `data/samples_*.jsonl`, `results/{c3,novelty_audit,manual_audit}.json` |
| art_IVZc3TWCeE9f | exp9 | `data/samples.jsonl`, `results/{landing,los,manifold}.json`, `figures/fig_manifold_*.png`, `states/t*/…/part_*.npz` |
| art_6zBfl3kDjeiP | exp7 | `results/{frlp_cells.jsonl,gate_events.json,association.json}`, `data/forced_labelled.jsonl`, `frozen/ladder_profile.json` |
| art_0ndRfWKBWclR | exp11 | `bench/*/{spec.json,tests.jsonl,checker.py,references/*.py}`, `data/{association,samples_forced,frlp_cells,samples_pilot,samples_llama_pilot}.jsonl` |
| art_U5UKkFrOgSsE | iteration-1 exp4 | `data/samples.jsonl` |
| art_UoCVh2Qe5RZ0 | iteration-1 exp6 | `results/samples.jsonl` |

**How folders are resolved.** `src/paths.py` and the audit scripts look under `AII_DEPS_DIR`, which defaults to `..` (this folder's parent, where the repository's sibling folders sit). Each artifact is found by a folder named after its artifact id, or after its original workspace folder (for example `gen_art_experiment_13`). On the run server, `AII_ITER1`, `AII_ITER2` and `AII_ITER3` (or the unpublished `paths.local.json`) point at the original roots instead.

**Not published.** exp9's `states/` activations (0.95 GB) were kept on the run volume and are not published. Without them, the figures stage records the 2×2 activation composite and the g16 check as `failed` in `results/figures.json`. Every other stage is unaffected.

**User-uploaded inputs.** None are used. The run's upload folder was empty.

**Environment variables (names only).**
- `AII_DEPS_DIR`: optional.
- `AII_ITER1`, `AII_ITER2`, `AII_ITER3`: run server only.
- `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY`: needed only for judge prompts that are not already in the published `audit/judge_cache.jsonl`. With the published cache, no key is needed and no money is spent.

## 4. Commands, in the order they produce the published results

```bash
uv run eval.py --stages all
```

This runs the following stages, about 1.5 minutes in total on the hardware above:

| Stage | What it does |
|---|---|
| `inventory` | `inputs.json` |
| `rows` | `data/rows.parquet`, 65,433 labelled rows |
| `judges` | 0d pool, features and blind judges; cache hits only |
| `knob` | 1,120 cells |
| `screen` | `screen.json`, `screen.sha256`, `screen_extras.json`, verification targets |
| `route` | |
| `llama` | |
| `other` | 0d assembly, with the manual pass read from `audit/manual_pass.json` |
| `figures` | |
| `rigor` | |
| `wording` | |
| `rivals` | |
| `audit` | `audit/rederive.py`, `audit/placebos.py`, `audit/rederive_extra.py` |
| `outputs` | `eval_out.json` (= `full_eval_out.json`), `mini_eval_out.json`, `preview_eval_out.json`, `corrections.json` |

The extra checks and tools, run separately:

```bash
uv run pytest                              # 9 unit tests (tests/test_stats.py), ~6 s
python3 -I audit/rederive.py               # stdlib-only re-derivation: 29 checks, 0 mismatches, ~3 s
uv run python audit/placebos.py            # 4 placebos, all fail to show an effect, ~9 s
uv run python audit/rederive_extra.py      # 12 more checks, 3 placebos, ~17 s
python3 screen_rule.py screen_input.json screen_check.json   # stdlib rule; byte-identical to screen.json
```

**History notes.**
- The judge calls were made once by the `judges` stage, through `src/run_judges.py`. That was 472 judge calls plus 20 tie-breaks at temperature 0, about 1.5 minutes, USD 0.223. The models were openai/gpt-4.1-mini, google/gemini-2.5-flash and deepseek/deepseek-chat-v3.1. Re-running reuses `audit/judge_cache.jsonl`, which is keyed by model + sha256 of the prompt.
- The manual pass (Step C) was done by the executor reading the programs. Its verdicts are stored in `audit/manual_pass.json`, and the code reads them rather than producing them.
- During development, stages were also run one at a time with `--stages <list>`. The published files come from the final full run, followed by `--stages audit,outputs` once `rederive_extra.py` was added.
- The pipeline's aii-json formatter then rewrote `full_/mini_/preview_eval_out.json` from `eval_out.json`. `eval.py` writes equivalent variants itself (first 3 examples per dataset; preview strings truncated to 200 characters), so a reader's mini/preview may differ only in whitespace.

**Seeds and settings.**
- Master seed 20261021. Each cell's seed is `int(sha256('20261021|' + cell_id)[:8], 16)`.
- Rarefaction: 1,000 subsamples at depth 25. CIs: 1,000 bootstrap replicates × 200 draws (90% percentile).
- Spearman permutation: 1e6 draws. Placebos: 1,000 / 1e5 / 1e4 / 500 draws.
- 0d pool: capped at 25 programs per event (seeded). Manual 20% sample: seed 20261021.
- Judges run at temperature 0.

## 5. What you should get, and where it appears in the paper

| Output | Numbers | Paper location |
|---|---|---|
| `screen.json` / `screen.sha256` | sha256 `d6a2ca9711f461973c39482314a523d448d0590cb40e32432826dec1da4846e8`. Movable: T03, T05, T06, T1, T10, T2. Movable × catalogue-only ban avoidance ≥ 0.5 table 6/0/0/8 (Fisher one-sided p = 1/3003, descriptive). | Claim 3a screen and the frozen C1 event set |
| `tables/knob_table.csv`, `tables/verification_targets.csv` | 1,120 cells. 25 of 27 quoted numbers reproduce. Two are corrected: "nothing reaches Hill 1.5 under 20 pts on R1/R3/R6/T11/T13/T14" is false once the T14 modal ban (1.78 at 17 pts) and the exp14 exposure arms are counted; two-sum α=2 avoidance is 0.469 on the attempted denominator, not 0.48. T03 α=1: 7/15 escape (Hill 2.92/2.42/2.32/2.13/2.11). T2: 3/15. | Section 3.2.5 one-statistic knob table; Table 110 (`tables/table110_alpha2.csv`) |
| `tables/random_direction_counts.csv` | E_t: T03 8/18 (α1, pooled engines), T05 2/3 (α2), T06 1/3 (α2), T10 1/3 (α1, bf16 only), T1 1/15, T2 3/15. | Push-movability screen |
| `tables/route_landing.csv`, `results/route.json` | All 7 readings reproduce. JS matches exp16 to 1e-6 (17/17). F_prompt 0.611 [0.06, 1.17] and F_direct 0.744 [0.38, 1.11]. Without T13: 0.648 [−0.08, 1.38] and 0.865 [0.68, 1.05]. T13 is not gated under catalogue-only avoidance (0.15). | Section 3.11 route-landing lead; Section 3.10 'carry more' |
| `tables/llama_hits.csv`, `results/llama.json` | 'Other' excluded: LADDER 6/13 (p 0.100), ASSOCIATE 7/13 (p 0.032). Table 102 checks 3/3. Snap-back 0.72/0.73/0.93. | Section 3.5 scoring note; Table 102; Section 3.10 |
| `tables/other_audit_*.csv`, `tables/catalogue_only_avoidance.csv`, `tables/merge_intervals_correction.csv` | 226 programs (6 passing): 68 catalogue variant, 156 degenerate, 2 labeller miss, 0 novel. κ(A,B) = 0.77. Residue-gated events: exp13 T13, exp16 T13:a, Llama T06. Merge intervals: 29/12/3, all failing. | Tables 95, 102 and 106 catalogue-only columns; novelty statement |
| `tables/table82_distinct_rows.csv`, `tables/defined_only_hits.csv` | Table 82: gain 0/11, residual 0/11, implied mass 8/11 (6 sham). Exposure SUBTRACT defined 4/33, hits 4/4 in both arms. | Table 82; Section 3.10 exposure sentence |
| `tables/rival_predictors.csv` | Spearman ρ: movable 0.86, can 0.16, clarity −0.07, FRLP 0.19, nonce −0.19, novelty 0.35. These are screen values, not confirmation. | Claim 3a rival contrast |
| `corrections.json` | Replacement sentences for review items 0a–0j. 0f (Table 92b) is delivered by this iteration's research artifact. | Sections 3.5, 3.10, 3.11 |
| `figures/` | Markers M1–M5 with the position caveat. The 2×2 composite has MDS stress-1 0.025/0.006. | Geometry figures |

## 6. Independently re-derived numbers

- **`audit/rederive.py`** (stdlib only, no `src/` imports) re-derives: the verification targets for T03, T2, T05, T06, T04, the exp13 rows, exp4 and exp6; the screen sha256 (byte for byte) and the movable set; the Llama strict hits and p-values; the route fractions (all five tasks, without T13, catalogue-only); catalogue-only avoidance; the Table 82 hits; and all six rival ρ values.
- **`audit/rederive_extra.py`** (sklearn / scipy / math) re-derives: judge κ; the control gate; the final class counts and 0 novel; the snap-back and Table 102 counts; the exposure sentence; the exp13 contest with and without T13; the screen Fisher p; the movability ρ; the T10 route readings; and the 60/60 hidden-test re-run.
- **Placebos.** All 7 fail to show an effect, as required: P1–P4, plus κ, Fisher and Spearman on shuffled input.
- **Not independently re-derived:**
  - bootstrap CIs and Good's coverage of the knob table;
  - the coverage-standardised sensitivity;
  - per-task best rows;
  - the defined-only hit-rate table;
  - the Section 3.10 template-arm (13/19, 15/19) and prefill-depth numbers;
  - the figure statistics (MDS stress, g16 neighbour order);
  - the manual merge-interval classes, which are a manual read.
