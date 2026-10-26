# Fixing the iteration-7 record before iteration 8

This is Step 0 of iteration 8: an erratum and re-derivation pass over the iteration-7 record. It runs on CPU only and
answers all eleven items (0a-0k) of the blocking iteration-7 review. It uses data already on disk plus USD 0.095 of
judge calls. Every corrected number is traced to a raw file, with the value as recorded in the report, the recomputed
value and a status (`corrections.json`). Every edit to the report is machine-checkable: each `old_text` occurs exactly
once, no two edits overlap, and a lint shows the contradicted phrasing is gone. An independent stdlib audit re-derives
every NEW and CORRECTED value, and its placebos must fail.

## Results

| Check | Result |
|-|-|
| Report edits | 84, each marked `(iteration-8 correction)` (directly, or through its table's caption) |
| Residual-claim lint | 35 hits before (28 phrases plus 4 undefined `Step K` tags), 0 after |
| Apply test | passes; a one-character mutation of one `old_text` fails it, as it must |
| Value ledger | 141 values: 68 MATCH, 7 CORRECTED, 63 NEW, 3 CARRIED |
| Stdlib audit (`audit/rederive.py`) | 97 checks, 0 mismatches, 6/6 placebos fail as required, 0 NEW/CORRECTED values unchecked |
| Headline check (`audit/headline_check.py`) | 11/11 headline numbers re-derived through different code paths, 5/5 placebos fail as required |

**0a. Counting sort.** The frozen kth-smallest runtime rule sent "count, then sort the distinct values" to `other`, and
the AST rule returned `unknown` for it. That is counting sort in dictionary form.
- **Extension.** `labeller_v2/` adds one recogniser mapped to the existing `counting_sort` label. One revision round was
  used: the first version also required a plain dict in the tracer's `dict_sizes`, which the tracer does not record for
  `collections.Counter`.
- **Validation before any relabel.** All 6 bench references agree. The gold set is unchanged (kappa runtime-vs-AST
  0.951, runtime-vs-adjudicated 0.964, identical to `gate.json`). 5/5 constructed controls pass: two positives and three
  negatives (dict memo then `sorted(nums)`, a value-bucket select, a heap over Counter items).
- **Relabel.** All 960 kth-smallest rows were relabelled. There are 35 transitions, all `other -> counting_sort`; the old
  rules reproduce every stored label (1.000).
- **Adjudication.** It covers the 162 programs in the 19 exp33 cells with more than 20% `other`. Judge A
  (deepseek-chat-v3.1) scored 10/10 on the gate controls and judge B (mistral-medium-3.1) 9/10, so both count.
  Agreement: kappa(A, B) 0.96; rule against A 0.64 and against B 0.64. I read 48 distinct programs manually (38
  disagreements plus the 10-program agreement sample).
- **Full-state exchange of the forced counting-sort source.** It now gives **29/30** counting sort (dictionary form).
  The 30th program is a binary search on the value range, which the rule had labelled quickselect.
- **Kth-smallest pooled recovery.** It falls from 1.59 / 1.57 / 1.55 to **1.01 [0.95, 1.08] / 1.00 [0.93, 1.08] /
  0.99 [0.92, 1.06]** at ranks 1 / 4 / 16, using exp33's own slot bootstrap. As a placebo, the port first reproduces
  every exp33 pooled recovery and interval exactly on all three tasks.
- **Unchanged quantities.** The random-subspace recovery (0.05) and the permuted-label transfers (0.60 / 0.47) do not
  change. The transfers are absolute, (count - base)/30; relative to the full-state effect they are 1.40, 1.24 and 0.82.
- **Novelty audit.** 29 of the 36 catalogue variants in 7.3.9 come from this one cell, and 6 more from the forced
  counting-sort prompts.
- **Routing.** DAS routes more cleanly than the full state on **one** task (shortest path). On kth smallest the edit
  changes the implementation form, not the algorithm: under DAS 28 of 30 programs are an array of counts at
  rank 16, while the full state's are a dictionary with sorted keys.
- **Contrastive pilot on shortest path (Table 301).** 56 of the 67 programs labelled `other` are degenerate text and
  11 are Dijkstra attempts that crash. 19 of the 30 programs labelled Dijkstra are degenerate text that the frozen path
  labeller calls Dijkstra. No relabelled program passes, so the correct-program counts stand.

**0b.** Recovery is now reported by source and rank in a new Table 297b (`tables/recovery_by_source.csv`). It recovers
0.17-0.43 of forced Bellman-Ford/SPFA and 0.06-0.53 of forced BFS. Rank 2 was never generated for forced sources. The
three untrained-network ratios, defined from their keys (shortest path only):
- 0.013: the committed comparison, against the diverged contrastive fit; not meaningful.
- 0.92: the fit-value ratio, 13.31 against 14.45 nats.
- **5.08**: the gain in the fitted LME_Y objective, 43.6 against 8.6 nats.

**0c.** The Gemma DAS, difference-in-means and twin cells run with the 32-token opening prefilled (`src/g2.py:877`;
`prefix_len` 32 in the raw rows). The forced-BFS "ceiling" is sampled from index 0 with no prefix
(`src/g2.py:878-885`) on the same CRN slots. So "42 against 35" is not a comparison. The prefill condition is now
stated at every mention.

**0d.** The fork margin is restated as a readout. The Spearman correlations recompute to 0.804 [0.62, 0.91] for the
margin and 0.869 for the 48-token LLR. No property of the push direction predicted which pushes move the fork: the axis
projection gives 0.17 and 0.01, and the iteration-4 plan subspace gives 0.03.

**0e. Gemma natural variance.** It lies below the random 95th percentile at ranks 1, 2 and 4, and above it at rank 8.
At block 22, rank 1 lies above it (0.00294 against 0.00078).
- The committed `dormant_flag` was false only because |rho| = 0.497 (`g2.py:618`).
- Recovery of 1.98-2.81 times the full-state swap is the off-manifold signature that Makelov et al. warn about.
- The dormancy checks were not run.
- The two families' controls are declared not comparable (new Table 364d, `tables/control_protocols.csv`).

**0f.** A new Table 371b and `positioning.json`. All 12 neighbour rows and both ICML 2026 workshop posters for
"A Tale of Two Temperatures" (AdaptFM, 75333; 4th Structured Probabilistic Inference & Generative Modeling, 74361)
were verified live on 2026-10-23 with `fetch_grep`; the raw outputs are in `audit/web/`. The venue row now says COLM,
from the arXiv v2 comment, which gives no year, and that the paper is about diffusion LMs.

**0g.** A new subsection 7.3.10 quotes D-drop, D-tfsets, D-targets and D-cap verbatim. Plan resampling and the
DAS-coordinate top-five placement are carried forward as open items.

**0h.** Table 346 gains fresh-slot rows: top quartile 24/50 against rest 9/50 (McNemar 15:0); full unit 21/50 against
shuffled positions 4/50 (17:0); RD_seed -0.10 [-0.22, 0.02]. These are recomputed from the slot-level rows. The 81%
and 82% are different quantities: the top-quartile share of energy on connected components, and one
massive-activation cell on shortest path.

**0i.** Search is reported as rates and clusters (`tables/search_by_arm.csv`):

| Arm | Programs / calls | Clusters |
|-|-|-|
| Search | 78/2,500 | 12 |
| Larger mutator | 23/500 | 7 |
| Instruction only | 2/500 | 1 |
| Enumerate and pick | 0/1,250 | - |
| No evolution | 0/500 | - |

The rate ratio against the instruction alone is 7.8, with a lower bound of 2.41, short of the committed 10x. Table
371's 816 / 707 / 103 / 6 matches the file.

**0j.** Scope is now stated per unit.
- **Minimum spanning tree weight** passes. But its T 1.0 prediction (0.237) lies outside the Wilson interval
  [0.28, 0.54], and the stream-lean explanation (Fisher p 0.011) is post hoc.
- **0.19 against 0.20.** Both numbers stand. Table 330's 0.19 counts Prim only; `posthoc.json`'s 20/100 also counts
  the disputed program.
- **Manifold claim.** W1-W3 are marked as training templates of the map, so the claim rests on W4 (D 1.73) and W5
  (D 2.62).
- **Semantic seed.** It is on the boundary of the null: 93.9th percentile, D 1.127 against 1.130.

**0k.** The four stale `pending the 2x2 of Step K` tags are replaced with the sentences from `retag.json`. Ten lost
file names are restored (11 edits), found by a difflib comparison against the record audit's `report_corrected.md`.

## Layout

| Path | What it is |
|-|-|
| `eval.py` | entry point; `--stages s0,a,b,c,d,e,f,g,h,i,j,k,apply,audit,out` (or `all`) |
| `sections/common.py` | shared helpers: Clopper-Pearson, Wilson, exact McNemar, Newcombe, Fisher, average-rank Spearman, bootstraps, correction records, lint |
| `sections/a_labeller.py` | A1-A3: labeller v2 validation (references, gold set, controls) and the T03 relabel |
| `sections/judges.py`, `sections/a_adjudicate.py`, `sections/manual_reads.py` | A4: gated two-family judges (cached), adjudicated column, manual reads |
| `sections/a_recompute.py` | A5: line-for-line port of exp33's P1 / pooled recovery / slot bootstrap / routing, with the placebo |
| `sections/item_a.py` ... `sections/item_ghijk.py` | one function per review item: traced values plus report edits |
| `sections/s0_apply.py`, `sections/outputs.py` | S0 (vendoring, hashes, section index, lint before), APPLY (apply test, diff, lint after, placebo), OUT |
| `labeller_v2/` | copies of the frozen T03 AST/runtime rules with the one added recogniser; `controls.py` holds the five constructed controls |
| `audit/rederive.py` | independent stdlib re-derivation of every NEW/CORRECTED value, with placebos; writes `audit/rederive_report.json` |
| `audit/headline_check.py` | short separate re-derivation of the headline numbers through different code paths (regex relabel of the raw code, counting ranks, bisection bound), with placebos; writes `audit/headline_check.json` |
| `reproducibility.md` | step-by-step reproduction: environment, inputs by artifact id, commands, seeds, hardware, expected numbers |
| `audit/judge_cache.jsonl`, `audit/judge_gate.json` | every judge response (a rerun is free) and the gate scores |
| `audit/web/` | raw `fetch_grep` outputs for every positioning row (`run_fetches.sh` refreshes them) |
| `corrections.json` | 84 edits (old_text, new_text, item, section, line) and the 141-value ledger |
| `report_corrected.md`, `report.diff` | the corrected report and a unified diff against `inputs/report/current_report.md` |
| `positioning.json` | the iteration-8 positioning rows with dated evidence and status |
| `tables/*.csv` | counting_sort_adjudication, relabel_confusion, labeller_v2_validation, recovery_by_source, gemma_natural_variance, control_protocols, search_by_arm, lint |
| `eval_out.json` (= `full_eval_out.json`), `mini_eval_out.json`, `preview_eval_out.json` | `exp_eval_sol_out` output, schema-validated |
| `results/` | intermediate JSON for every stage (a2 validation, a3 relabel, a4 adjudication, a5 recompute, items, apply, audit) |
| `inputs/` | the vendored report, the record audit's files, the T03 bench copy (from exp33's vendored bench), `input_hashes.json`, `resolved_paths.json` |

## How to run

```bash
uv sync                          # creates .venv from pyproject.toml / uv.lock
uv run eval.py --stages all      # about 1 minute; judge calls come from audit/judge_cache.jsonl, so a rerun costs nothing
python3 -I audit/rederive.py     # the stdlib audit on its own
```

The iteration-7 dependency workspaces are read in place, read-only, through one constant, `DEP_ROOT`. On the run's
storage it is `../../../round-7`; in the published repository it is this folder's parent, where they are
sibling folders. Set `AII_DEP_ROOT` to override (see `reproducibility.md`). The report and the record audit's files
are vendored into `inputs/` with sha256 hashes in `inputs/input_hashes.json`.

## Departures and limits

- **Constructed controls.** Two of the ten judge-gate controls, and both positive labeller controls, are dictionary-form
  counting sorts that I wrote. The bench has no independent exemplar of that form. The other eight gate controls are
  bench references and gold items, and a dictionary-using full sort serves as a negative control.
- **The T2 rule.** The T2 (shortest path) rule label was not changed. The adjudication shows the frozen path labeller
  names degenerate text "dijkstra" in 19 pilot programs; none passes.
- **Placebo (ii).** The pooled point recovery is a ratio of sums and does not depend on slot order (checked). The
  slot-shuffle placebo therefore acts on the paired bootstrap interval, which changes only slightly because the DAS
  cells are near-saturated. A label-shuffle placebo is added; it changes the point value.
- **Not run.** The Gemma dormancy checks (reverse interchange, projected-map retention), the Qwen untrained network on
  connected components and kth smallest, and a prefill-matched instruction cell are stated as not run. They are left to
  later artifacts. No new saturation search was run, so the positioning wording stays "to our knowledge (mini search
  dated 2026-10-22, re-verified 2026-10-23)".

## Restoring removed files

Only regenerable bulk is marked for deletion in `.aii/manifest.yaml`:

| Path (delete entry in `.aii/manifest.yaml`) | Restore with |
|-|-|
| `.venv/` | `uv sync` (or `bash restore.sh`) |
| `sections/__pycache__/` | `uv run eval.py --stages all` (Python rewrites the bytecode cache) |
| `labeller_v2/__pycache__/` | `uv run eval.py --stages all` |
| `inputs/bench_T03/bench/__pycache__/` | `uv run eval.py --stages all` |
| `inputs/bench_T03/bench/common/__pycache__/` | `uv run eval.py --stages all` |

`bash restore.sh` runs both commands. Nothing else needs restoring. Every result, table and log is kept, along with
the judge cache (`audit/judge_cache.jsonl`, a small text file kept automatically), and no file in this folder is 100 MB
or larger.
