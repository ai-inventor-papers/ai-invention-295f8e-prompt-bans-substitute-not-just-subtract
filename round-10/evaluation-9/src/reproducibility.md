<!-- hand-maintained -->
# Reproducibility

This is what was actually run to produce the published files. It is CPU only: no GPU, no model calls and no API keys. Every path below is relative to this folder.

## 1. Get the artifact

```bash
git clone <URL of this run's public GitHub repository>
cd <this artifact's folder>      # the folder holding eval.py
```

The repository publishes the three declared dependencies as sibling folders named by their artifact ids:

- `art_8nXdw3_lDAll` (rename rows)
- `art_VVA3P0ocZNA2` (geometry rows)
- `art_cDba8_DycUJd` (base rows)

The code (`src/io_util.py`, anchored on `Path(__file__)`) looks for each dependency in this order:

1. `$AII_DEPS_ROOT/<artifact_id>`, when `AII_DEPS_ROOT` is set;
2. the sibling folder `../<artifact_id>`;
3. a `DEP_<artifact_id>=<path>` line in an optional, untracked `.env`.

## 2. System, Python and libraries

- Ubuntu with `uv` installed. Python 3.12 (3.12.14 was used).
- Create the venv and install the exact versions that were used. They are pinned in `pyproject.toml` and locked in `uv.lock`: contourpy 1.4.0, cycler 0.12.1, fonttools 4.67.0, kiwisolver 1.5.1, loguru 0.7.3, matplotlib 3.11.2, numpy 2.5.4, packaging 26.3, pillow 13.0.0, pyparsing 3.3.3, python-dateutil 3.0.0, scipy 1.18.1, six 1.17.0 and tzdata 2026.5.

```bash
uv venv .venv --python=3.12
uv sync            # or: uv pip install --python .venv/bin/python -r pyproject.toml
```

- `audit/rederive.py` uses the Python standard library only.

## 3. Data, environment variables and keys

Nothing is downloaded, and no API key is needed (OpenRouter spend: USD 0).

**What is already in this folder:**

- `inputs/report/current_report.md` is a byte-identical copy of the iteration-9 report being corrected.
- `inputs/<artifact_id>/` holds the small result JSONs, all listed with their sha256 in `inputs/SHA256SUMS`.
- `vendor/` holds the dependency source files used, unmodified, with sha256s in `vendor/SHA256SUMS`.

**What must come from the sibling dependency folders**, because these large row files are read in place:

- From `art_8nXdw3_lDAll`: `data/samples_v9.jsonl`, `data/labelled_v9_*.jsonl` and `results/retrace.jsonl`.
- From `art_cDba8_DycUJd`:
  - `results/b2_tf_B3.jsonl` and `results/b2_tf_T10.jsonl`;
  - the `results/b1_*.json` fork files;
  - `vendor/art_18XvfcJJZi1O/data/validation_rows_C1forced.jsonl`, the pair-row rule for item 0f.

**Environment variables (all optional; names only):**

| Variable | What it does |
|---|---|
| `AII_DEPS_ROOT` | Directory that contains the dependency folders. |
| `DEP_<artifact_id>` | Path of one dependency (in `.env`). |
| `REPORT` | The report to correct. Default: `inputs/report/current_report.md`. |
| `LOST_BINPACK` | The lost iteration-9 bin-packing workspace (not a declared dependency). |
| `FIG_SKILL` | The aii-data-fig-gen scripts that set the house figure style. |

- Without `LOST_BINPACK`, item 0j takes its gate values from the hypothesis text and is marked CARRIED. The published run read the files and marked 0j MATCH. The numbers are the same either way.
- Without `FIG_SKILL`, the figures render in plain matplotlib style.

No user-uploaded input is used.

## 4. Commands, seeds, hardware and runtime

```bash
uv run eval.py all            # stages: setup, controls, 0a ... 0j, edits, figures, ledger, audit, spotcheck, readme, out
# a single stage can be rerun by name, e.g.: uv run eval.py 0e
```

Each stage writes `results/<stage>.json`, updates `STATUS.md` and rewrites `eval_out_partial.json`. The audit stage runs `python -I audit/rederive.py`; the spotcheck stage runs `python -I audit/spotcheck.py`, a second standard-library check that reads `data/samples_v9.jsonl` instead of the labelled cell files that `src/` and the audit read.

**Seeds and settings:**

- Jonckheere-Terpstra uses 100,000 permutations with the record's seeds (seed 1 for the fine classes).
- The configuration cluster bootstrap uses B = 10,000 and seed 0.
- RSA relabeling p is exact: 10!, 9! or 6! relabelings, in chunks of 200,000.
- The audit's 10-class partial-RSA p uses 200,000 random relabelings with seed 20261024.
- The placebos use seed 7.
- The spot-check's McNemar placebo (200 within-program swaps) uses seed 20261025.

**Hardware and time:** 6 CPUs and 28 GB RAM in a container. The GPU (RTX 2000 Ada) was present but not used. Clean end-to-end runs took 209 to 235 s, each with exit code 0. The last run, on 2026-10-25 with the spotcheck stage, took 209 s.

**Packaging, run afterwards:**

- `aii_json_format_mini_preview.py --input eval_out.json` writes the full, mini and preview variants.
- `aii_json_validate_schema.py --format exp_eval_sol_out` validated all four files (PASSED).

## 5. What a reader should get

**Correction files:**

- `report_corrected.md`: 27 verbatim corrections tagged "(iteration-10 correction)", in Sections 9.2 to 9.9 and the closing. They add or change Tables 427, 431, 431b, 433, 437, 437b, 438, 440, 441, 441b, 441c, 443 and 444, and add the figure markers `[FIGURE:fig_s0_kcurves]` and `[FIGURE:fig_s0_placement]`.
- `report.diff` and `corrections.json`: every edit's old and new text, with a per-value ledger.
- `tables/*.csv`, `figures/` and `figure_markers.json`.
- `ledger.json`: the request ledger, item 0k.
- `eval_out.json` (metrics_agg).

**Checks:**

- The apply test passes, and every lint rule fires on the original report and never on the corrected copy.
- `audit/rederive.json` reports 861 checks, 0 mismatches and 6 of 6 placebos failing as required.
- `audit/spotcheck.json` recomputes 45 headline values of 0a, 0b, 0c, 0f, 0g, 0h and 0i from the raw rows (`data/samples_v9.jsonl`, `results/retrace.jsonl`, the manual reads, `b3_heldout_rows.jsonl` and `b2_tf_T10.jsonl`), with 0 mismatches. It also runs two placebos, and both fail on null input as required:
  - The exact McNemar test gives p 0.00012 on the observed Qwen3-32B k = 5 hand-read cell, but p < 0.05 in only 0.01 of 200 within-program swap draws (median p 0.79).
  - The pooled unit-weight-Dijkstra-compliant gap is 0.662 observed, but averages -0.006 over 200 swap draws, none of which reaches 0.662 (largest |gap| 0.12).
- Not independently re-derived by either check: the Jonckheere-Terpstra p-values (0b; each sits at its permutation floor), the 0i values read directly from stored fields (chance 0.167, base P 0.25 and unmapped mass 0.663), the 0j harness-gate values (read from the bin-packing files), and the ledger (0k), which is a synthesis that a lint checks against `report_corrected.md`.

**Headline numbers**, with where each appears in `report_corrected.md`:

- **Hand reads substituted (0a)** (Section 9.3 exhaustion paragraph, Tables 431, 431b, 443 and 444, Section 9.8, the closing; figure `fig_s0_kcurves` after Table 431b):
  - Qwen3-32B at k = 5: 27/46 = 0.59, gap 0.30.
  - Qwen3-32B on held-out templates: gap 0.396, below the committed 0.4.
  - Qwen3-14B at k = 5: 0.12, gap 0.73.
- **Fine tracer** (Table 431b, Section 9.3): Qwen3-14B on held-out templates: gap 0.38, which misses the 0.4 bar.
- **Runtime fine classes for Qwen3-32B (0b)** (Section 9.3, Table 431):
  - 22/46 = 0.48 at k = 4 and 10/46 = 0.22 at k = 5.
  - 11 of the 35 coarse violations at k = 4 are greedy best-first.
  - The registered sensitivity was a no-op in n3.json (12 of 12 cells equal).
- **Described ban against named (0c), mechanistic compliance by reading** (Section 9.3, Table 433, Section 9.8, the closing):
  - +0.58 by the runtime label;
  - -0.07 by the tracer;
  - +0.05 by the fine tracer;
  - +0.21 (0.02 to 0.38) under the per-cell reading.
- **Placement (0d)** (Table 438, Sections 9.7 to 9.9, the closing; figure `fig_s0_placement`):
  - Bellman-Ford/SPFA survivors: 15 of 15 opposite on both gate-passing Qwen3-32B frames (primary and programs-only; not on the second readout, whose gate fails).
  - Unit-weight Dijkstra survivors: at the edge, 15 of 15 on the primary frames and 10 of 15 on the Qwen3-32B programs-only frame.
- **RSA on named Qwen3-32B (0e)** (Section 9.4, Tables 437 and 437b, Table 443, the closing):
  - R_DS 0.65, against R_lex 0.46.
  - Correlation between R_lex and R_DS: r 0.13 (VIF 1.02).
  - Partial correlations: 0.502 for R_lex given R_DS and 0.675 for R_DS given R_lex.
- **Held-out circuit per side (0f)** (Sections 9.5 and 9.7, Table 444, the closing):
  - Forced side: 7.90 (ablate) and 7.65 (steer).
  - Padded side: about 0.
  - Overall means: 3.86 and 3.85.
  - The five-contrast exact test has a floor of 0.031 one-sided and 0.0625 two-sided.
- **Unit-weight Dijkstra, IDA\* and JPS counted as compliant (0h)** (Table 427, Table 431b, Section 9.3, the closing): pooled rename gap 0.662, against 0.697; 294 of the 371 covert programs carry the runtime label BFS or DFS.

Rerunning `uv run eval.py all` reproduces every table, `report_corrected.md`, `report.diff`, `corrections.json`, `ledger.json` and `audit/rederive.json` byte for byte. Two reruns checked this; their hash lists and logs are in `logs/rerun_check/`. The stage JSONs and `eval_out.json` differ only in timestamps and stage timings. The figure PDFs are written without a creation date, so they are byte-identical across reruns too. This file is kept on reruns; the generated notes go to `logs/reproducibility_generated.md`.
