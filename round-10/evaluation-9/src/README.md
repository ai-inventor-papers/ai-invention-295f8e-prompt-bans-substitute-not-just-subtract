# Fixing the iteration-9 record, item by item (iteration-10 S0 record repair)

CPU-only evaluation artifact of the AI Inventor run. It re-derives, from the three declared iteration-9 artifacts, every number the blocking iteration-9 review questioned (items 0a to 0j), writes each repair as a verbatim `old_text -> new_text` edit tagged `(iteration-10 correction)` into a corrected copy of the report, and proves the edits (apply test, residual-claim lint with positive controls, GRIM-style attainability checks, an independent standard-library re-derivation whose placebos must fail). Item 0k is a source-cited request ledger. No GPU and no model calls were used (OpenRouter spend USD 0.00).

Dependencies (read in place or copied to `inputs/` with `inputs/SHA256SUMS`): `art_8nXdw3_lDAll` (rename rows), `art_VVA3P0ocZNA2` (geometry rows), `art_cDba8_DycUJd` (base rows), and the report being corrected (`inputs/report/current_report.md`, sha256 `27545375f03c3e96e79c921a280b25f756ee5b3b5ce484a17ce600a7557ff4e0`).

## Results

**Positive controls (S-1):** 7 of 7 match exactly: `results/n3.json` and `results/n3_tracer.json` (all 24 cells, a/b/c/d and Newcombe intervals), the pooled gaps 0.697 and 0.608, all 63 RSA rhos (1e-9) and their exact p-values, the b2 null medians, the b3 held-out means and the placement edge counts.

| Item | What the files say | Edits |
|-|-|-|
| 0a hand reads | Qwen3-32B k = 5: 27/46 = 0.59 (gap 0.30); held out 0.54 (gap 0.396, just below the 0.4 bar); Qwen3-14B 0.12 (gap 0.73). The fine tracer (stored) gives Qwen3-14B held-out 20/50 = 0.40, gap 0.38 < 0.4, so 'supported for Qwen3-14B under all three readings' would have been wrong. | Table 431, new 431b, 9.3, 9.8, 443, 444, closing |
| 0b runtime fine classes | The registered sensitivity was a no-op (12 of 12 cells of n3.json repeat the coarse value). Applied: Qwen3-32B k = 4 22/46 = 0.48; 11 of 35 coarse violations at k = 4 are greedy best-first. | 9.3 |
| 0c described ban | runtime +0.58 (0.39 to 0.71); tracer -0.07 (-0.25 to 0.12); tracer fine +0.05; per-cell reading +0.21 (0.02 to 0.38). | 9.3, Table 433, 9.8, closing |
| 0d placement families | Family map frozen first (15/15/3/5). Bellman-Ford/SPFA opposite 15/15 on both gate-passing Qwen3-32B frames (median g 28.1 against frame median 24.8); unit-weight Dijkstra edge 15/15 primary, 10/15 programs-only. | Table 438, 9.7, 9.8, 9.9, closing |
| 0e RSA | Named Qwen3-32B: R_DS 0.65 (p 0.0010) against R_lex 0.46; lex-DS r 0.13 (VIF 1.02); partials lexical given data structure 0.502, data structure given lexical 0.675 (both schemes p <= 0.0026). | 9.4, Table 437, new 437b, closing |
| 0f held-out circuit | forced side 7.90 (ablate) / 7.65 (steer); padded -0.19 / 0.05; five contrasts p 0.031 one-sided (floor). 8.14 / 7.41 = means over both sides of the 20 pair prompts (recovered: MATCH). | 9.5, 9.7, Table 444, closing |
| 0g random sets | Sets repeating an MLP: MST R 1/50, MST Rpure 47/50, CC R 36/50, CC Rpure 50/50; CC fork stack per-prompt mean 0.13 against ratio of means 0.45. | 9.5, new 441b/441c, closing |
| 0h UD/IDA*/JPS compliant | pooled gap 0.662 against 0.697; covert BFS/DFS 294 of 371; C6 range 0.63 / 0.31 / 0.30-0.70. | Table 427, 9.3, closing |
| 0i slips | program probe 0.167 = chance for six classes; 7 of 350 samples lost; Gemma grid base P(BFS) 0.25, unmapped 0.663. | 9.2, 9.3, 9.4, 9.5, Table 440, 9.8 |
| 0j harness gate | MATCH: G-HARNESS PASS; best fit 5.37% / 3.98%; FunSearch 3.11% / 0.68%. | 9.6, 9.9 |
| 0k ledger | 21 request parts; every one of 170 numbers appears in `report_corrected.md`. | `ledger.json`, `tables/ledger.csv` |

**Proofs:** 27 edits; apply test PASS (every old_text once, no overlaps, applied back to front, every new_text once, byte-identical outside the spans, unified diff); lint PASS (15 rules, 20 hits on the original, 0 on the corrected copy; R14 and R15 have no instance in the original and are shown firing on planted sentences); GRIM 76 checks, 0 failures; audit 861 checks, 0 mismatches, placebos failing as required 6 of 6. Value statuses: CORRECTED 10, MATCH 44, NEW 90.

**Second spot-check:** `audit/spotcheck.py` (standard library only, with its own class maps; it reads `data/samples_v9.jsonl` instead of the labelled cell files that `src/` and `audit/rederive.py` read, plus `results/retrace.jsonl`, the manual reads and the b3/b2 row files) recomputes 45 headline values of 0a, 0b, 0c, 0f, 0g, 0h and 0i: 0 mismatches against the stage results. Placebos: random within-program swaps of the lexical and mechanistic indicators give exact McNemar p < 0.05 in 0.010 of 200 draws (median p 0.79; observed p 0.00012) and move the pooled unit-weight-Dijkstra-compliant gap to -0.006 on average (largest |gap| 0.12, against 0.662 observed), so both tests fail on null input as required.

**Departures from the plan, stated:** the hand reads are one reader's, not double-coded (a third reading, not gold); no sampling or redraw (random sets are not redrawn without reuse: BASE-W); partial-RSA p-values are descriptive; the per-family placement was not preregistered and 'opposite' is relative to a two-class reference median; the 8.14 / 7.41 averaging rule was recovered from the iteration-8 rows vendored inside `art_cDba8_DycUJd` (status MATCH, not CARRIED); the harness-gate values were read from the lost iteration-9 bin-packing workspace's own files (status MATCH); the Bellman-Ford/SPFA placement and the tracer-fine column of the described ban are computed from rows (not stored by the record).

## Layout

- `eval.py`: stage CLI (`uv run eval.py all` or one stage: setup, controls, 0a-0j, edits, figures, ledger, audit, spotcheck, readme, out)
- `src/`: stage code: io_util, vend (wrappers of the vendored code), rows, s_setup, s_controls, s_rename (0a 0b 0c 0h), s_geometry (0d 0e), s_base (0f 0g), s_slips (0i 0j), edits_build + apply_lint (S-8), s_figures, s_ledger, s_audit, s_spotcheck, s_out, s_readme
- `vendor/`: unmodified copies of analysis_v9.py, stats_v9.py, common.py, stage_analysis.py, b3_9.py, cmap9.py, stats9.py with vendor/SHA256SUMS
- `inputs/`: byte-identical copies of the report and the small result JSONs; inputs/SHA256SUMS lists every file read (row files read in place)
- `results/`: one JSON per stage (s0_setup ... s10_ledger), criteria.json (committed bars quoted verbatim), apply_test.json
- `tables/`: every new table as CSV (Table 431b, 433b, 437b, 438b, 440b, 441b, 441c, 427 sensitivity, lint rules, ledger, exact cell counts)
- `figures/`: fig_s0_kcurves and fig_s0_placement (PDF and PNG); figure_markers.json holds their six-field captions
- `corrections.json`: the 27 edits: id, items, location, old_text, new_text, reason, values (recorded, recomputed, status, tolerance, source, script, output)
- `report_corrected.md / report.diff`: the corrected report and its unified diff against inputs/report/current_report.md
- `ledger.json`: 0k request ledger
- `audit/`: rederive.py (stdlib only), rederive.json, planted/ (P6 copy); spotcheck.py and spotcheck.json (second stdlib check of 0a-0c and 0f-0i from the raw rows)
- `eval_out.json`: exp_eval_sol_out output (plus full_/mini_/preview_ variants); eval_out_partial.json is rewritten after every stage
- `STATUS.md, logs/run.log`: progress checkpoints

## How to run

```bash
uv sync                       # creates .venv with the versions pinned in pyproject.toml and uv.lock
export AII_DEPS_ROOT=/path/to/folder/with/one/subfolder/per/artifact_id   # or DEP_<id>=... lines in .env
uv run eval.py all            # about 4 minutes on 6 CPUs (209 to 235 s measured)
python3 -I audit/rederive.py  # independent stdlib audit (also run by the audit stage)
python3 -I audit/spotcheck.py # second stdlib spot-check (also run by the spotcheck stage)
```

## Restoring removed files

- `.venv/` (deleted after the round, regenerable): `uv sync` (Python 3.12; the versions pinned in `pyproject.toml` and locked in `uv.lock`)
- `__pycache__/` directories (regenerable): created again by any `uv run eval.py ...`

Nothing else is deleted. All kept outputs are small and stay in the published repository; no file of 100 MB or more exists in this workspace.
