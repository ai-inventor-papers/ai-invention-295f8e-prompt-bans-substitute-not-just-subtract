# Fixing the run's record, number by number (iteration 7, Step 0)

This repository repairs the iteration-6 record of the run report before the paper step quotes it. Every number it
touches is re-derived from the raw rows of the four declared iteration-6 experiments, then corrected in place in the
report as a verbatim `old_text -> new_text` pair marked `(iteration-7 correction)`. Each pair is proven to apply to a
copy of the report. A standard-library audit with placebos that must fail and a lint for leftover wrong claims check
the result. Nothing new is generated: no model is run. The only paid calls are three blind judge families (USD 0.077
in all). A dated web pass verifies the quotes.

Inputs (declared dependencies): art_lpQalcAXMGr1 (engine control), art_rMlbrjVB1c__ (exchange and site experiment),
art_zNyBP6zieI5u (Gemma), art_dbUtqBjT0tPf (NLA). Read by path: art_aRTQM6CQ0Dre (the iteration-6 Step 0),
art_OUuQUYQn5voE (the iteration-6 positioning audit) and the report itself, as read on 2026-10-22.

## Headline

| Check | Result |
|-|-|
| Corrections | 54, all applying exactly once (apply test 54/54), with no overlaps |
| Values ledgered | 603 MATCH, 117 NEW, 1 CARRIED, 3 CORRECTED (the 3 are venue expectations of the plan that the live records contradict) |
| Residual-claim lint | 16 flags in the uncorrected report, 0 in `report_corrected.md` |
| Independent audit (`audit/rederive.py`, stdlib only) | 520 checks, 0 mismatches; 7 of 7 placebos fail as they must |
| Headline re-derivation (`audit/headline_check.py`, stdlib, its own code path) | 35 checks, 0 failed; 7 of 7 placebos fail |
| Cross-check against the dependencies' own `predict_*` fields | 137 checks, 0 mismatches |
| Inputs | 69 files vendored and sha256-hashed, 0 missing |
| Spend and time | OpenRouter USD 0.077; a full offline pass takes about 20 s of wall time, and the judge stage about 2 minutes |

## What each item found

**0a, the Stage A metric.** The report described the outcome as "the share of correct programs implementing Y". Its
tables actually print commit0's preregistered outcome: `share(label == Y | cell) - share(label == Y | TWIN), all
samples (invalid rows count as not-Y)`, with the validity gate `pass_X / pass_TWIN >= 0.8`. The definition is
restored as primary. A *correct Y / N* column with Clopper-Pearson intervals is added to Tables 244 to 250, and the
prose of 6.4.1 now quotes both counts.

Key cells:

| Cell | Attempts labelled Y | Correct programs | Note |
|-|-|-|-|
| shortest path, blocks 0-35 | 24/30 | 21/30 | |
| shortest path, blocks 12-23 | 18/30 | 11/30 | pass ratio 0.73, below the gate |
| kth smallest, blocks 0-35 | 17/30 | 16/30 | |
| grid, blocks 0-35 | 14/30 | 3/30 | pass ratio 0.59, below the gate |
| grid, condition span | 10/30 | 7/30 | |
| forced Bellman-Ford/SPFA exchange | 30/30 | 30/30 | twin 1/30, so commit0's transfer is 0.967 |
| forced BFS exchange | 28/30 | 24/30 | pass 0.87 |

Five cells fail commit0's gate. A post-hoc McNemar on correct Y (NEW, not preregistered) compares the exchange with
the matched-norm random exchange:

| Task | Correct Y | Exact p | Preregistered attempted contrast |
|-|-|-|-|
| shortest path | 21:0 | 9.5e-7 | 23:0 |
| kth smallest | 15:2 | 0.0023 | 16:2 |
| connected components | 11:0 | 9.8e-4 | 11:0 |

`tables/occurrence_ledger.csv` classifies every report hit of 0.80, 0.57, 0.47 and 0.33 (and of 0.567, 0.467 and
0.333).

**0b, the site.** The rule label is quoted verbatim: 'WITHDRAWN as FP8-specific: the site of the choice is open'.

- The condition-span clause fails post hoc. Its beta is -1.70 [-3.96, 0.42] on kth smallest and -0.56 [-4.93, 2.91]
  on connected components (cluster bootstrap), so the site is open. The 'FP8-specific' half of the label is refuted
  by Section 6.3.
- A NEW concordance table (Table 254b) sets the noise sites against Stage A. They agree on kth smallest (both at
  blocks 12-23). On connected components they disagree: noise acts most at blocks 0-11 (S4 coefficient +2.51
  [1.39, 3.80], flips 4:18, p 0.004), while the exchange transfers at blocks 12-23.
- Removing the default is depth-redundant: the share of attempts off union find is 0.87 at blocks 0-11 and 0.63 at
  blocks 24-35.

**0c, Gemma.** DAS is restated within the controls it had:

- Rank 1 moves the held-out fork log-odds by 8.8 nats, against -0.08 to +0.05 for random subspaces.
- The shuffled-source control is uninformative by construction (10.1 nats).
- No random-initialisation or target-shuffled control was run.
- The rank-4 interchange gives BFS in 50 of 50 attempts with 0 of 50 programs passing.

The readout gains the following context:

- The standardised SAE ridge reaches 0.15, against 0.086 for a template-plus-noun-norm control (delta 0.064, below
  the 0.10 bar).
- The estimator sensitivity is reported: unstandardised SAE ridge from -0.76 to 0.06, raw ridge 0.70 to 0.72.
- A caveat is added: a readout at the fork position is close to a next-token readout.

"Every edit breaks programs" becomes "edits toward BFS lowered the pass rate from 0.84 to 0.16-0.58, except the SAE
top-5 clamp (18 BFS, pass 0.84)".

**0d, the synthesis.** "Where the choice is held, in three models" is replaced by statements per model and per
quantity, with a NEW Table 279. Gemma drops out of the read-position sentences, because its SPEC site is a mean over
the task-spec positions (`src/cfg.py` line 7). "What remains open" now names five items: the plan-and-fork account,
DAS with the Sutter controls, the fork-margin test of temperature, the circuit at Gemma's fork, and evaluator-guided
search.

**0e, the figures.** Seven `[FIGURE:...]` markers are added, each with a caption note. The captions are built from
the generating code and the PDF text, and are tied to their files by sha256 (`figure_markers.json`).

- Every plotted position precedes the fork.
- In Gemma's plots and in F8, the centroid marker sizes come from realised labels. Centroid positions never do.
- MDS stress is 0.371, 0.369, 0.542 and 0.569 in the four Gemma plots. It is not recorded for F5 or F8.

**0f, the top-five dose.** The forced-prompt centroids span -0.098 to +0.144 on PC1. The alpha-1 points move from
+0.09 to -0.44. Pass falls 0.67, 0.30, 0.03, 0.00. The claim now reads "at doses of 1 to 8 ban units, which
overshoot the forced-prompt manifold"; an in-manifold dose was not tried.

**0g, Table 238.** Two correct-only columns are added. On shortest path the correct off-default counts are:

| Alpha | W8A8 | bf16 |
|-|-|-|
| 2 | 14/37 | 9/31 |
| 1 | 9/43 | 5/43 |

The screen-level verdict for shortest path is MIXED. W8A8 passes the screen on 15 of 40 directions, against 8 to 9
for the other engines. Under both W8A8 and bf16, 17 of 40 directions reach the +0.20 excess but fail the pass clause.

**0h, the NLA test.** The published test is reproduced exactly: 364 units, 20:88, p 2.3e-11, task-cluster bootstrap
[-0.35, 0.02], with 5 clusters (the tasks T05, T06, T1, T10 and T2). With one unit per sample (104 samples):

| Test | Result |
|-|-|
| First unit per sample | 0:25, p 6.0e-8 |
| 2,000 random draws of one unit per sample | median 4:29, p 1.9e-5; every draw below 0.05 |
| Sign test on per-sample differences | 12:38, p 3.1e-4 |
| Durkalski-adjusted McNemar | p 6.5e-5 |
| Task level | 1:3, p 0.625 |

With 5 clusters no cluster-level test can go below p 0.0625. The outside reader is better per sample, and the
evidence is inconclusive at the task level.

**0i, executed but not reported.** U6 failed mildly: the BFS share from the empty prefix is 0.38 (73 of 192),
against a natural 0.305 [0.245, 0.372], exact binomial p 0.028. D12 is quoted verbatim in 6.5 and 6.8.

The engine control had **3** correct programs labelled other. Only 2 are in `data/labels.jsonl`; the third is an
iteration-4 engine-a row listed in `data/samples.jsonl`, with its code in `inputs/exp22/labels.jsonl`. Two are
array-scan O(n^2) Dijkstra, and one is n rounds of Bellman-Ford relaxation commented as Floyd-Warshall. All pass the
hidden tests (45/45) and three sandboxed stress tests (12/12 maximum-size, 8/8 adversarial, 300/300 random small).
Their nearest known solutions have tree distance 0.00 to 0.11.

The judges:

| Judge | Gate (classes merged) | Exact classes | Status |
|-|-|-|-|
| DeepSeek-chat-v3.1 | 10/10 | 7/10 | passed |
| GPT-4.1-mini | 8/10 | | failed |
| Gemini-2.5-flash-lite | 8/10 | | failed; the declared replacement, rate-limited on 12 of its 39 calls |

Both failing judges misread the same two "known outside" controls, D'Esopo-Pape and Johnson, as catalogue variants.
Only one judge is therefore gated, and kappa is reported for the primary pair: 0.38 on exact classes, 0.61 on
merged ones. Every judge and the manual read class all three programs as catalogue algorithms. Final count: 0 novel.
Table 278's row is updated, and no rate is quoted.

**0j, Section 4.9.** The diff against the report iteration 6 received locates the iteration-6 insertion, which is
wrapped as "(Correction, iteration 6: ...)". The claim "every correct program outside the catalogue ... has been
read" is limited to the pools actually audited. Two pools are named as never audited: about 9,000
forking-token programs, as recorded in Section 3.2.3 (CARRIED), and the engine control's nearest-known pass. No
other line repeats the claim.

**0k, positioning.** All 6 neighbour quotes verified: 4 re-matched live in the full text, 2 taken from the live
abstract. Versions and venues:

| Neighbour | Venue and version found | Against the plan |
|-|-|-|
| Forking Paths | ICLR 2025 (OpenReview and the proceedings; not on the arXiv record) | matches |
| Forking Fast | v1 2026-08-20; no venue; no NeurIPS 2026 paper page found | CORRECTED |
| Hanna and Ameisen | ICLR 2026 | matches |
| Ma and Rui | Mechanistic Interpretability Workshop at ICML 2026, not the main conference | CORRECTED |
| A Tale of Two Temperatures (seed) | COLM, not ICML 2026 | CORRECTED |

The mini saturation search ran 14 logged queries (6 scholarly), with 137 hits, 136 of them unique. Its verdicts: 0
occupies, 14 adjacent, 1 irrelevant. The new Table 277 row 66 (ADJACENT-ONLY, "to our knowledge, mini search dated
2026-10-22") passes the consistency check: it does not say "readable across prompts" and it carries the next-token
qualifier.

**0l, tags.** The six plan-sampler and movability verdicts in 5.7, 5.11, 6.2.4 and the closing now carry "(ban-free
unit and iteration-5 seeds; pending the 2x2 of Step K)".

## Departures (from the plan's practice alignment)

- No new model compute. The Gemma DAS controls (random initialisation, shuffled targets, forced-DFS sources) and a
  logit-lens control are named, not run.
- The one-unit-per-sample NLA test treats samples as independent, but they share 5 task clusters.
- The 18,237-solution corpus is not in a declared tree. The nearest-known comparison uses three sources instead: the
  bench references, the run's correct catalogue-labelled programs, and a 406-solution subset of that corpus that sits
  inside art_lpQalcAXMGr1 (34 of them shortest-path).
- Three programs support no rate. The site intervals come from `site_grid.json` and are not refitted. Figure captions
  come from code and PDF text, not regenerated figures.
- Adversarial stress case. A first judge pass used an adversarial case with node ids of n or more, which crashed
  three catalogue references. The case was fixed and every judge re-run. The superseded responses stay in
  `audit/judge_cache.jsonl` and count toward spend.
- Network isolation. The sandbox's network block is best effort, because unprivileged network namespaces are refused
  on this host.

## Layout

- `eval.py`: the orchestrator. It runs the stages, the apply test, the lint and the audit, and writes every output.
- `src/stage_inputs.py`: resolves, vendors and hashes the inputs, writing `input_hashes.json`.
- `src/items_qwen.py`: items 0a, 0b, 0f and 0g (Qwen3-8B Stage A, site grid, top-five dose, Table 238).
- `src/items_other.py`: items 0c, 0d, 0h, 0i (U6 and D12), 0j and 0l.
- `src/figmarkers.py`: 0e, the figure captions and markers.
- `src/novelty.py` and `src/sandbox_child.py`: 0i, the tests, nearest-known search, controls, blind judges and gate.
- `src/positioning.py` and `src/positioning_assemble.py`: 0k, the quotes, versions, venues, saturation search and
  verdicts.
- `src/corrections.py` and `src/editor.py`: the correction registry, value statuses, apply test and lint.
- `src/crosscheck_predict.py`: recomputation from the dependencies' published `predict_*` fields.
- `src/stats.py`: Clopper-Pearson, exact binomial and McNemar, the sign test, the Durkalski adjustment and kappa.
- `src/outputs.py`: writes `eval_out.json` and its full, mini and preview variants.
- `audit/rederive.py`: the independent stdlib audit with placebos P1 to P7. It writes `audit/rederive_report.json`.
- `audit/headline_check.py`: a short re-derivation of every headline number through different code paths, with a
  placebo per statistical test. It writes `audit/headline_check.json`.
- `audit/judge_protocol.json` and `audit/judge_protocol_amendments.json`: the frozen judge protocol and the
  replacement amendment. `audit/judge_cache.jsonl` holds every response; `audit/judge_runs_summary.json` summarises
  them.
- `audit/web/`: the cached arXiv pages, quote greps and search results, plus `collect_log.json`.
- `corrections.json`: all 54 corrections, with their values and the apply-test record.
- `report_corrected.md` and `report.diff`: the corrected report, and its diff against `inputs/report/current_report.md`.
- `figure_markers.json` and `positioning.json`: the 0e and 0k deliverables.
- `eval_out.json`, `full_eval_out.json`, `mini_eval_out.json` and `preview_eval_out.json`: the exp_eval_sol_out output
  (metrics M1 to M12, seven datasets, and metadata.sections 0a to 0l).
- `results/`: `items.json` (every recomputed quantity), `values_ledger.json`, `novelty.json` and
  `predict_crosscheck.json`.
- `tables/`: `stage_a_cells.csv`, `table238_correct_only.csv`, `nla_one_unit_per_sample.csv`,
  `occurrence_ledger.csv`, `corrections_index.csv` and `lint.csv`.
- `inputs/`: the vendored, hashed copies of every input. They are kept in place on the run's volume, and every file
  is under 100 MB, so they are also published.
- `reproducibility.md`: the exact steps, versions, seeds, hardware and expected outputs. `logs/` holds the run logs.
- `pyproject.toml` pins every installed package; `restore.sh` recreates `.venv` from it.

## How to run

```bash
bash restore.sh                     # .venv with the exact pinned versions of pyproject.toml
uv run eval.py --stages offline     # reuses results/novelty.json and audit/web/; no network, no spend
python3 -I audit/rederive.py        # the audit on its own (standard library only)
python3 -I audit/headline_check.py  # the headline re-derivation with placebos
uv run eval.py --stages all         # optional: paid judges and the live web pass (about USD 0.08)
```

Inputs produced by other artifacts are reached through one anchor, `DEPS_ROOT` in `src/common.py`, which is relative
to this folder and can be overridden with `AII_DEPS_ROOT`. The repository publishes those artifacts as sibling folders.
Without them the run falls back to the sha256-verified copies in `inputs/`, so this folder runs on its own.

## Restoring removed files

`.aii/manifest.yaml` marks two paths for deletion after the round. Both can be rebuilt:

- `.venv/` (regenerable): `bash restore.sh`, which runs `uv venv .venv --python=3.12` and then
  `uv pip install --python .venv/bin/python -r pyproject.toml`.
- `src/__pycache__/` (regenerable): any run, for example `uv run eval.py --stages offline`.

Upload exclusions for the published repository: `(^|/)\.venv/` and `(^|/)__pycache__/`.
