# Iteration-6 Step 0: repair the record, freeze the inputs

CPU-only record audit for iteration 6 of the algorithm-choice study (Qwen3-8B, Qwen3-8B-Base and gemma-3-4b). No model
is run. Every number is recomputed from the files of iteration 4 and iteration 5 on disk and cited as
`<artifact_id>:<relative path>#<key>`. The audit covers the four must-fix items of the blocking iteration-5 review and
its minor items. Each change to the report is written as an exact `old_text -> new_text` correction, and
iteration 6's screen inputs were hash-frozen before any analysis output existed. A stdlib-only re-derivation with
placebos then audits every headline.

* `corrections.json` holds **45 corrections**. Every `old_text` occurs exactly once in the iteration-6
  `current_report.md`, which is never edited, and no two corrections overlap.
  * The corrections carry 150 value checks: 93 MATCH, 14 CORRECTED, 43 NEW and 0 NOT_REPRODUCIBLE.
  * By correction: 17 qualify or mark text whose numbers MATCH, 9 change a number (CORRECTED) and 19 add new material
    (NEW).
* `eval_out.json` follows the `exp_eval_sol_out` schema and is validated, with full, mini and preview variants. It has
  368 aggregate metrics and 4 datasets: corrections, landing_events, m_candidates and adjudication.
* `audit/rederive.py` is stdlib-only and imports nothing from the eval code. It re-derives **163 checks with 0
  mismatches**:
  * both dose definitions and the weighting identity (15 tasks);
  * the engine-contrast shares and the alpha-2 Fisher p;
  * six dose-matched binomial p-values;
  * the landing tallies, their Poisson-binomial p, the unconfounded subsets and the t_u discordance;
  * ρ(β, E) with its Bonett-Wright and Fieller intervals, and one power cell by simulation;
  * runtime merit for all 30 units, and R6's ρ;
  * the phrasing values, the pooled PN-vs-DMD counts, the Gemma fill means and Wilcoxon p, and Table 126c;
  * the novelty-audit counts, and the absence of any NOVEL judge answer.
* **Not independently re-derived.** These come from the source files through the eval code only:
  * the bootstrap intervals, the permutation p of ρ, the copula power cells and the required n;
  * the other rivals and their paired deltas;
  * P15/P20, the panel B knob rows and repertoire violation;
  * the unit-clustered tally, the mixed-twin shares and the ban-unit column;
  * the L3 and F4 screens, and the judge gate and agreement indices.
  * Four of the five placebos fail as required. P2 cannot be met at n = 13 by construction; see below.
  * The commit chain verifies, and every frozen file predates every S3 output.
* OpenRouter spend was **USD 0.15** for 198 paid judge calls, against a cap of USD 0.45 (`results/costs.json`).
  Later reruns are served from `results/judge_cache.jsonl`.

## Results by review item

### 0a Engine (must-fix 1)
* **The two dose definitions are both right, and they reconcile exactly.**
  * The mean of per-position ratios (exp27 `unit_ratio`) reproduces 0.990, 0.889, 0.995, 0.874 and 1.394 on
    connected components (T10), shortest path (T2), two sum (T05), grid (T1) and kth smallest (T03).
  * The ratio of mean norms over blocks 12-23 (exp27 bf16 ban-free unit over the exp19 8-bit ban unit) reproduces
    Table 174: 0.745, 0.837, 0.778, 0.751 and 0.975.
  * The ban unit itself matches all 14 values of Table 174; T03 is 11.58. Substring search is the one CORRECTED value:
    0.279 against 0.30.
  * The ratio of mean norms equals the ban-norm-weighted mean of the per-block ratios, with a residual below 1e-6.
  * The gap between the two definitions lies **within blocks** (0.09 to 0.39 on the decisive tasks), not in the
    weighting across blocks (−0.04 to +0.03). It mixes per-position Jensen effects with the bf16 engine's own ban unit;
    see `figures/fig_dose_reconciliation`.
* **The record compared two different shares.** Iteration 4's per-sample plan noise shares in Table 222 are exp19
  `off_default_share`, which counts attempts off the default including failing programs. The bf16 shares count correct
  programs.
  * Correct-only on both engines, the 8-bit shares at alpha 1 / 2 are: shortest path 0.18/0.30 (recorded 0.26/0.54),
    grid 0.02/0.08 (recorded 0.06/0.24) and kth smallest 0.28/0.46 (recorded 0.28/0.50).
  * The alpha-2 drops from 8-bit to bf16 are 20-fold on components (30/50 against 1/50, Fisher p 7e-11), 6-fold on
    shortest path (p 9e-4), 3-fold on grid (p 0.36) and 1.6-fold on kth smallest (p 0.10).
  * The hypothesis quoted a 12- to 30-fold drop and p 1e-8 on shortest path. Those figures only arise with the
    mixed definitions.
* **Dose-matched test.** The 8-bit dose-response curve was interpolated at the bf16 dose expressed in 8-bit ban units,
  under both definitions.
  * bf16 is significantly below 8-bit on components at alpha 2 (p 3e-18), on shortest path at alpha 1 and 2 (lower
    Clopper-Pearson variant 0.010 to 0.041) and on kth smallest at alpha 1.
  * It is not significantly below on grid or two sum.
  * The dose shortfall is at most 13% (mean of ratios) or 25% (ratio of means), so the dose does not explain the drop.
  * The cause is **not** established, because engine, GPU, kernel and sampler streams all differ (Claim E).
* `figures/fig_beta_escape_bf16` keeps the engines in separate facets: bf16 in A and 8-bit in B, never pooled. Facet B
  marks eval3's frozen-screen verdicts.
* **Sentences on the movable set.** `results/movable_sentence_scan.json` lists the 28 sentences of Sections 4.x and
  5.x that mention the screen's movable set, each with a decision.
  * Corrections are added for:
    * Items 2-4 of 4.10.
    * The 4.2.6 and 4.9 statements of the set.
    * The 4.10 summaries and the 4.6 summary sentence.
    * The cross-engine screen check of 5.3.
  * Section 4 reports the 8-bit engine throughout, as stated in the 4.10 preamble, so its other sentences stay
    unchanged.

### 0b Landing (must-fix 2)
* **Tallies.** The 21 events reproduce 17/21.
  * New units: 6/7, Poisson-binomial p 0.0027.
  * Gemma: 5/7, p 0.025.
  * 8-bit screen: 5/5. bf16 remeasure: 1/2.
  * Unit-clustered: 15 of 19 clusters.
* **Twin-minority rival t_u.** It is defined on 7 events and hits 6 of them. The base runner-up also hits those 6, so
  there are **0 discordant pairs**. 6 of the 17 hits are landings the tuned twin had already written.
* **Unconfounded subset** (the twin wrote no correct non-default program):
  * Qwen: 3/4, p 0.052.
  * Gemma: 2/4, p 0.42.
  * Pooled: 5/8, p 0.053. All three MATCH.
* **Corrections.** The landing half moves from Established to a new "Descriptive leads" list, and the universal
  sentences in 5.10, 5.12 and the closing are deleted or qualified.
* **Mixed twins.** On trapped rain water (0.64), minimum spanning tree weight (0.66) and valid anagram (0.76) the twin
  itself writes a second correct algorithm.
* **Thin Gemma support.** The grid runner-up rests on 4 valid attempts and 0 correct programs, and kth smallest and
  connected components on 6 valid attempts each.

### 0c Movability (must-fix 3)
* **Correlation.** ρ(β, E) is 0.146 over the 13 primary units (MATCH).
  * Bonett-Wright 95% interval −0.44 to 0.65; Fieller −0.46 to 0.66; BCa −0.52 to 0.71.
  * One-sided permutation p 0.32 (200,000 permutations).
  * ρ is 0.006 with the two extension units.
* **Power** (10,000 simulations per cell) at n = 13 and ρ = 0.6 is 0.60 with a Gaussian copula on the observed
  marginals (ties included) and 0.70 bivariate normal.
  * About **30 units** are needed for power 0.8 at ρ = 0.5.
  * Panel A's "≈0.46 at 0.6" is not reproduced at n 6 or n 13.
* **Harmonised rivals**, one definition across both panels:
  * R6 runtime merit is re-timed with one harness for all 30 units. It reaches ρ 0.59 (p 0.018) on the 13 units.
  * Twin modal share reaches 0.41 and harmonised opening margin 0.37, both oriented.
  * R4 (novelty-instruction excess) had two definitions: panel A subtracted the twin and panel B did not. Recomputed
    from the labelled rows with one definition, it runs opposite to the predicted sign (ρ −0.55): valid anagram has a
    novelty excess of 0.76 and never moves, and trapped rain water −0.36 and moves (`tables/r4_novelty_excess.csv`).
  * The paired-bootstrap differences from β all include 0, with R4 only just doing so (−1.34 to 0.02).
  * R1 *is* harmonisable. Both panels logged log-probabilities of the first ≤16 body tokens under W1-W5, and panel B
    stored the negated margin, so the margin is recomputed from the raw log-probabilities with one formula.
* **Re-timing changes one record claim.** Longest common prefix also has a correct alternative about 2.1× faster than
  the default and never escapes, so "an alternative at least twice as fast" holds in rank, not as a rule.

### 0d Missing outputs (must-fix 4)
* **Table 206 phrasing.** All values MATCH: 2/4/8, 3/3/10, 2/3/9 and 5/7/12; the repeat cell gives 3/6/10. The noise
  floor |T0.7 − repeat| is 0/3/0, so the rise at θ 0.8 is within noise.
* **P15 and P20 for Tables 207-208** come from `prices.json`, with bootstrap reach rates.
* **Panel B knob rows** are the new Table 203b. MST matches the review: Prim 18/49 at T 1.3 and 20/50 under plan
  noise.
* **Panel B repertoire check.** It has **1 violation**, where the plan expected 0: count inversions has 3 correct
  nudged Fenwick-tree programs, and the base wrote that algorithm only as 2 valid attempts with 0 correct.
* **Table 126c** (rows K0522-K0524) MATCHES: Hill-1 2.87, 2.96 and 2.92 at pass costs of −12, −27 and −15.

### 0e Minor items
* **Table 211 per task.**
  * At alpha 2: 19:3 pooled (p 0.0009), of which kth smallest is 13:0 and the other four tasks 6:3 (p 0.51).
  * At alpha 1: 4:3.
  * Item 4 of 5.11 is restricted to kth smallest at alpha 2.
* **Gemma fill rule.**
  * Over all 7 events, with the undefined association scored as uniform: 1.50 nats, exact Wilcoxon p 0.023 (MATCH).
  * Over the 6 events where association is defined: 1.57 nats, p 0.047 (NEW).

### S4 Third-family blind adjudication
* **Design.** 14 programs that two judges called novel, plus 8 frozen controls: 3 name-scrubbed catalogue references,
  3 audit items judged DEGENERATE and 2 items manually KNOWN.
* **Outcome under the frozen rule: not completed.** No third-family judge passed the gate of 6 of 8 controls. The
  record therefore stays "judges 14 of 48, manual 0".
  * claude-haiku-4.5: 2 of 8.
  * mistral-medium-3.1: 3 of 8.
  * llama-4-maverick: 3 of 8.
* **Descriptively, all three judges call 0 of 14 novel.** Binary agreement with the manual classes is 1.0, as are
  AC1 and PABAK; kappa is undefined because no item is novel.
* **Second pass.** It shows the nearest known solutions in reverse order. It was run descriptively for all three
  judges, because none passed the gate.
  * All three again call 0 of 14 novel.
  * Pass-to-pass stability is 0.93 for haiku, 1.00 for mistral and 0.86 for maverick.
* **The gate failure comes from the controls.** All three judges call the R6 "degenerate" controls brute-force linear
  scans (known techniques) and the T06 "known" controls the catalogue's hash-set mode, which contests exp24's manual
  labels.

### 0f Frozen screen inputs (S2)
The freeze wrote five files to `frozen/`. Each is committed in `commitments.log` as
`utc | file | sha256 | prev_chain | chain`, with genesis = sha256('iter6_step0').

* **`m_candidates.json`**: the v6 M candidates on all 30 units, the screen ranking and the replacement pattern.
  * Screen ranking on 30 units: twin modal share ρ −0.37 (p 0.026), β_v6 0.24 (p 0.097), runtime merit 0.24
    (p 0.10). On the 15 new units, runtime merit reaches 0.46 (p 0.046).
  * Replacement pattern: 3 of 6 base-diverse immovable units against **0 of 7** movable units (Fisher p 0.070), with
    the v6 definition that pools chat and plain base programs.
  * The hypothesis's 1 of 7 reproduces only with chat-only compositions. There, single number's base modal algorithm
    is XOR fold; pooled, it is the hash-count default.
* **`e_inputs.json`**: the 300 exp19 plan-noise rows on T10, T2 and T03. It also holds the 40 exp22 directions,
  confirmed as rand_9101..9140, with their sha256 and their alpha-2 slots on T10 and T2, and reproduction targets
  with Clopper-Pearson intervals.
* **`l3_screen.json`** (descriptive only) covers 21 events.
  * Pooled held-out log score: q_base^γ −0.35, q_base −0.54, q_tail −1.01, uniform −1.30, association −1.59.
  * γ sits at its grid ceiling of 5 on 13 of 21 events, where the landing is a single algorithm and the fit
    degenerates to the base top-1.
  * Kendall τ is defined on only 2 events.
* **`f2_screen.json`**: the stored margins and the harmonised ones. The same-seed null tasks have no overlap with the
  new units.
* **`adjudication_design.json`**: the S4 design, frozen before any judge call.

## Deviations (`results/deviations.json`)
* **D1.** The first adjudication design selected 0 DEGENERATE controls, because exp24's judge_c is blank when judges a
  and b agree. The selection was fixed and the whole freeze re-run before any judge call; the superseded chain is
  kept.
* **D2.** The freeze was re-run to remove absolute server paths from published files.
  * Every frozen file except `e_inputs.json` is byte-identical to the chain in force when the judge ran.
  * `e_inputs.json` differs only in the keys of `source_sha256`.
* **D3.** The adjudication's second pass is descriptive only, because no judge passed the gate.
* **D4.** R4 is recomputed from the labelled rows with one definition for both panels.
* **D5.** The movable-set markers follow the curated rule described under 0a, not a blanket rule.
* **D6.** Per-position dose quantiles are not reported, because only per-block means were logged. The residual-norm
  ratios are carried from Table 174.
* **D7.** Paths are now portable: dependencies are sibling folders named by artifact id, and the undeclared inputs are
  vendored. The whole chain was re-run, and every frozen file is byte-identical.
* **Figures.** They are hand-written matplotlib (PDF+PNG, Type 42 fonts) rather than a JSON spec through
  aii-data-fig-gen, for time.
* **P2 placebo.** "Median |ρ| below 0.1" cannot hold at n 13: the permutation-null median |ρ| is about 0.2. It is
  reported as uninformative, with the signed median beside, and not re-thresholded.
* **Timing.** The re-timing ran single-threaded fresh `python -I` subprocesses for 145 references and finished in
  51 s. 30 references were flagged unstable (coefficient of variation above 0.2) and got 9 repeats; their units are
  marked `unstable` in `frozen/m_candidates.json`. Only log ratios are used.

## Layout
| Path | What |
|-|-|
| `eval.py` | orchestrator (`--stage freeze|analyse|judge|outputs|all`) |
| `src/common.py` | provenance-tracked readers, exact small-sample statistics |
| `src/load.py` | the 30 iteration-5 units (default, twin, base, E_u) |
| `src/time_child.py`, `src/s1_retime.py` | S1 one-harness re-timing → `retime/raw_times.json` |
| `src/s2_freeze.py` | S2 freeze (F1-F4, adjudication design, hash chain) |
| `src/s3_analyses.py` | 0a-0e analyses → `results/s3_analyses.json`, `tables/*.csv` |
| `src/s4_judge.py` | S4 third-family blind judge → `results/adjudication*.json` |
| `src/s5_outputs.py` | corrections, figures, `eval_out.json` |
| `audit/rederive.py` | stdlib-only re-derivation and placebos → `audit/rederive_result.json`, `audit/placebos.json` |
| `corrections.json` | the 45 `old_text -> new_text` corrections with provenance and statuses |
| `frozen/`, `commitments.log` | frozen screen inputs and their hash chain (`commitments_superseded_*.log`: earlier chains) |
| `tables/` | 24 CSV tables (dose, engine, landing, movability, power, rivals, prices, knob rows, adjudication ...) |
| `figures/` | `fig_beta_escape_bf16`, `fig_dose_reconciliation`, `fig_power` (PDF + PNG) |
| `results/` | `s3_analyses.json`, `input_hashes.json` (sha256 of every file read), `report_index.json`, `adjudication.json`, `adjudication_calls.json`, `judge_cache.jsonl`, `costs.json`, `deviations.json`, `movable_sentence_scan.json`, `iter6_genart_listing.json` (names only) |
| `eval_out.json` (+ `full_`, `mini_`, `preview_`) | schema `exp_eval_sol_out` |
| `inputs/` | vendored undeclared inputs: the iteration-6 report, the redacted protocol strings, eval3 `screen.json` and `tables/knob_table.csv`, exp18 `known_solutions_summary.json` (origins and sha256 in `inputs/SOURCES.json`) |
| `reproducibility.md` | exact step-by-step reproduction (what was run, seeds, hardware, expected numbers) |
| `pyproject.toml`, `requirements.lock.txt`, `install.sh` | every package pinned (Python 3.12.14) |
| `paths.local.example.json` | template for the unpublished `paths.local.json` (dependency folders on your machine) |

All outputs are small text files. Nothing is 100 MB or larger, so everything is published; no kept artifact lives only
on the run volume.

## How to run
See `reproducibility.md` for the full procedure.
* **Inputs.** Dependencies are read from sibling folders named by artifact id (`<AII_DEPS_ROOT>/<artifact_id>`;
  override per artifact with `AII_DEP_<id>`, or in `paths.local.json`). The undeclared inputs are vendored in
  `inputs/`.
* **Commands:**
```bash
bash install.sh                                # .venv from requirements.lock.txt (uv, Python 3.12)
.venv/bin/python src/s1_retime.py              # S1 (about 1 min)
.venv/bin/python eval.py --stage freeze        # S0 + S2
.venv/bin/python eval.py --stage analyse       # S3 (refuses to run unless the chain verifies)
.venv/bin/python eval.py --stage judge         # S4 (paid; served from results/judge_cache.jsonl when present)
.venv/bin/python eval.py --stage outputs       # S5
python3 -I audit/rederive.py                   # independent audit
.venv/bin/python eval.py --stage outputs       # fold the audit result into eval_out.json
```
* **Re-freezing** starts a new chain, keeps the old one as `commitments_superseded_<utc>.log`, and requires re-running
  S3.

## Restoring removed files
* **`.venv/`** (`delete: regenerable`): run `bash install.sh`. It installs `requirements.lock.txt`, which matches
  `pyproject.toml`, under Python 3.12.
* **`src/__pycache__/`** (`delete: regenerable`): Python rebuilds it on the next import, for example with
  `.venv/bin/python eval.py --stage analyse`.
* **Not published:**
  * `paths.local.json` holds machine-local dependency folders; recreate it from `paths.local.example.json`.
  * `inputs/protocol/scripts/build_strategy.py` names server paths; the code uses
    `inputs/protocol/protocol_strings_redacted.json` instead.
