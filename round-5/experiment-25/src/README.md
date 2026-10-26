# Can the base model forecast nudgeable tasks? (iteration 5, Step 2, panel A)

Qwen3-8B (instruct, thinking off) writes almost every Python solution to a coding task with one default algorithm.
Earlier iterations found that a small isotropic push on the task-specification states (blocks 12–23, prompt prefill
only) moves some tasks off that default and leaves others pinned. This repository tests a forecast of **which tasks
move, and where they land**, made from **Qwen3-8B-Base** before any push:

* **Claim A1 (whether a task moves).** The base model's correct-only off-default share β_u, sampled on the same
  chat-templated token ids as the instruct twin, predicts the escape fraction E_u of a fixed population of push
  directions.
* **Claim A2 (where a pushed task lands).** The base model's most frequent correct non-default algorithm r_u predicts
  the landing L_u of the confirmed escapes, and beats an association prompt and an AST-proximity forecast on log
  score.

For every unit, the forecast (default, β_u with its Wilson CI, r_u, the rivals) was sha256-committed into a hash chain
**before** the first push row was sampled; a programmatic guard in the GPU worker refused push jobs until then
(`results/guard_check.json`: true for all 23 units/tasks).

## Bottom line

**A1 is not supported in this panel; A2 is.** All numbers below are generated from the result files
(`results/summary.md`, written by `src/report5.py`). Two independent stdlib-only scripts re-derive them from the
raw samples with **0 mismatches**, and their placebos fail as they must: `audit/rederive.py` (β, r_u, E, landings,
ρ/p, A2, Extra arm A) and `audit/rederive2.py` (rivals, corrected association and proximity log scores, 'half +
screen', engine check, gate κ, novelty and repertoire counts).

* **Primary set (the pre-registered units that passed their labeller gate: A1–A5, A7; n = 6).**
  Spearman ρ(β, E) = −0.03 (exact one-sided permutation p = 0.56). The one base-collapsed unit (A2, β = 0) is
  immovable, as A1 predicts. But 2 of the 5 base-diverse units (β ≥ 0.2) are also immovable, including the most
  diverse one: A4 (count primes, β = 0.81) never escapes. Under the measurement-error bootstrap the median ρ is
  −0.09 (90% interval [−0.37, 0.21]). The panel is **not consistent** with the pooled thresholds (ρ ≥ 0.6, ≥ 80%
  collapsed immovable, β ahead of every rival). The pooled decision across panels is made next round from
  `pooled_inputs.json`.
* **β loses to the trivial rivals.** Within the primary panel, E tracks two rivals far better than β does.
  * The minimum runtime-merit ratio of the alternatives: ρ = −0.88. The three units that move have an alternative about
    twice as fast as the default or faster (ratios 0.10–0.51); the three that do not move have ratios 0.86–4.35. The
    extension unit A9 breaks this (its fastest alternative has ratio 0.11, yet it never escapes): ρ = −0.66 with the
    extension.
  * The twin's own modal share: ρ = −0.70, Δ = ρ(β,E) − sign·ρ(rival,E) = −0.73, 95% task-bootstrap CI
    [−1.90, −0.09].
* **A2: the base runner-up is exactly where pushes land.** On all 3 events (A1, A3, A7: default, β ≥ 0.05, observed
  movable) r_u = L_u (Poisson-binomial P(H ≥ 3) = 0.019 under chance 1/(K−1)). The base composition's log score beats
  proximity on every event (mean margin 0.99 nats).
  * **Association bug.** The committed association forecast was uniform: every answer restates the default named in
    the question, and the committed mapping took the earliest mention (deviation D-assoc-mapping). With the mapping
    corrected post hoc on the same pre-commitment answers, association is a strong rival. It names the landing on 2 of
    the 3 events (A1, A3; it says Manacher where A7 lands on brute force).
  * **Base still wins.** The base composition has the higher log score on all 3 events (mean margin 0.85 nats;
    1.10 against the committed uniform version).
  * The exact Wilcoxon p = 0.25 is the smallest attainable with 3 events.
* **Pushes never leave the base repertoire.** No correct off-default plan-noise or escape program lands on an
  algorithm with zero correct and zero valid base programs (`results/outside_base_repertoire.json` is empty).
* **With the two reserve units (A8 jump game, A9 median of two sorted lists; a logged extension, n = 8)** the picture
  sharpens rather than reverses: ρ = −0.33 (p = 0.80). Both are base-diverse (β = 0.47, 0.71) and both are
  immovable; A9's two screen passers failed confirmation.
* **Descriptive 'half + screen' view (21 units: the 6 new units plus the 15 existing tasks, using Step 1's committed β
  and this run's Extra-arm-A E).** Here ρ = 0.54 (p = 0.0065) and, for the existing tasks alone, ρ = 0.59
  (p = 0.0096). That correlation comes from 13 of the 15 existing tasks being immovable, with low β concentrated
  among them, while the two movable tasks (T03, T10) are base-diverse. Base-diverse tasks are still often immovable
  (T1, T2, T14), and the landing check splits (T10 hit, T03 miss). This view is descriptive, not a test of A1.
* **Extra arm A (the 15 existing tasks under the ban-free unit, 8 fixed directions × α {1, 2}).** Only T03
  (E = 0.25) and T10 (E = 0.125) escape. T05, T06, T1 and T2, which the frozen screen called movable under the
  iteration-4 ban unit, are immovable here. The positive control holds: T03 and T10 escape at α = 2.

Scope: one model family, memorised LeetCode problems, n = 6 primary units. The design can only detect a strong
relation (power ≈ 0.46 at a true ρ = 0.6 even when pooled with panel B), so the A1 null in this panel is weak
evidence on its own. The rival results and the A4/A8/A9 counter-examples are the more informative part.

## What was run

| Stage | What | Where |
|---|---|---|
| 0 | Precision rule (RTX 4090, 23.5 GiB → bf16 for **both** models), input copies with sha256 manifest, dependency extraction (all 10 datasets of `art_j3Rm_lr2nzR6`), seed disjointness check, CPU tests | `src/stage0.py`, `predictions/precision_rule.json`, `inputs/MANIFEST.sha256`, `results/dependency_usage.json`, `tests/` |
| 1 | GPU tests U1–U7 (CRN determinism, α-0 identity, dose accuracy 1.4·10⁻⁴, memory, fence invariance, base sanity), engine check against the screen's FP8 rows | `results/gpu_tests.jsonl`, `results/engine_check.json` |
| 2 | 9 unit specs frozen up front in new wording (grep audit: 0 algorithm words, 0 catalogue names), twins with a neutral noun padded to the longest display name; per unit: hidden tests (LeetCode I/O + seeded edge/random/stress), one reference per mode, mutants, quadratic baselines, runtime + AST labellers, gold set judged blind by two LLM families + a third, gate (κ ≥ 0.8, runtime vs adjudicated ≥ 0.9, references 100%), one revision round on a holdout | `src/specs5.py`, `newbench/<unit>/`, `newbench/common/` |
| 3 | Per gated unit: twin N = 50, base N = 100 on identical ids + plain completion N = 50, rivals (opening margin, merit gap, twin modal share, novelty N = 30, association N = 20, AST proximity), base audit → **commitment** → escape population (8 directions × α {1, 2} × 10 rows, top-up to 30 for screen passers, binomial confirmation), plan noise α 1 and 2 (N = 50 each), T 1.3 (N = 50) | `src/unit_commit.py`, `predictions/unit_<u>.json`, `commitments.log` |
| 4 | Extra arm A: fresh twin + the same 8 directions on the 15 existing tasks, same ban-free unit and engine (after commits #0 and #E) | `results/extra_arm_a.json` |
| 5 | Labelling (tests + runtime + AST, judges on disagreement), labeller re-check of the 15 existing labellers, validity fix | `src/label_worker5.py`, `src/recheck.py`, `src/fix_validity.py` |
| 6 | Frozen analysis (committed at #0) on the primary and extension sets, 'half + screen', sensitivities, novelty audit | `src/analysis_a1a2.py`, `src/final_run.py`, `src/novelty_audit.py` |
| 7 | Outputs, figures, independent re-derivation, placebos | `src/outputs5.py`, `src/figures5.py`, `audit/rederive.py` |

Scale: 8,620 sampled rows in 0.98 GPU-hours of batch time (5 model loads), 8,390 labelled programs, USD 0.35 of
OpenRouter judge calls (cap 2.00).

### Units

| Unit | LeetCode | Catalogue (mode ids) | Gate | Default (twin share) | β [95% CI] | r_u | E | L_u |
|---|---|---|---|---|---|---|---|---|
| A1 majority element | 169 | boyer_moore_vote, hash_count, sort_middle, divide_conquer, randomized_verify, bit_count, library_mode | κ 0.92, rt 0.95 | hash_count (1.00) | 0.41 [0.26, 0.59] | boyer_moore_vote | 0.125 | boyer_moore_vote |
| A2 maximum block sum | 53 | kadane, prefix_min, divide_conquer, segment_tree | κ 1.00, rt 1.00 | kadane (1.00) | 0.00 [0.00, 0.08] | – | 0 | – |
| A3 trapped rain water | 42 | two_pointers, prefix_suffix_max, monotonic_stack, peak_split | κ 0.82, rt 0.90 | prefix_suffix_max (0.64) | 0.23 [0.10, 0.43] | two_pointers | 0.438 | two_pointers |
| A4 count primes | 204 | eratosthenes, trial_division, linear_sieve, segmented_sieve, sundaram, atkin | κ 1.00, rt 0.95 | eratosthenes (1.00) | 0.81 [0.64, 0.91] | trial_division | 0 | – |
| A5 longest common prefix | 14 | horizontal_scan, vertical_scan, sort_ends, binary_search_length, divide_conquer, trie, library_commonprefix | κ 0.84, rt 0.90 | horizontal_scan (1.00) | 0.30 [0.15, 0.52] | vertical_scan | 0 | – |
| A6 number of islands | 200 | dfs_flood, bfs_flood, union_find | **GATE_FAIL** (holdout κ 0.74, rt 0.89) | excluded | | | | |
| A7 longest mirrored substring | 5 | expand_center, dp_table, manacher, brute_force | κ 1.00, rt 1.00 | expand_center (1.00) | 0.46 [0.30, 0.64] | brute_force | 0.188 | brute_force |
| A8 jump game (ext.) | 55 | greedy, dp, bfs_indices | κ 1.00, rt 1.00 | greedy (1.00) | 0.47 [0.32, 0.63]† | dp | 0 | – |
| A9 median of two lists (ext.) | 4 | merge_two_pointers, partition_binary_search, heap_merge, concat_sort | κ 1.00, rt 1.00 (revision round) | merge_two_pointers (1.00) | 0.71 [0.51, 0.85] | concat_sort | 0 | – |

† A8 has 19 correct base programs (< 20), so by the pre-registered rule its β is computed on valid attempts
(flagged). The full tables (per-unit pass rates, PN excess, knob rows, rivals, Extra arm A, engine check, gates) are
in `results/summary.md`.

### Checks that hold

* Engine: the twins reproduce the screen's FP8 rows (T03 per-slot label agreement 1.00, T2 0.98). The two pushed
  cells differ under bf16 (agreement 0.74 and 0.86; T2's JSD is just outside the template-resampling null), so this
  is reported as **precision sensitivity**. All contrasts in this repository are within the bf16 engine.
* Labellers: every gated unit's labellers agree on 100% of references and on 35/35 hand-written variants. The existing
  labellers match their frozen gates within 0.02 (`results/labeller_recheck.json`).
* External cross-check (`results/external_reference_check.json`, descriptive). Independent TheAlgorithms
  implementations from the dependency (MIT) were wrapped as `solve`. 8 of 9 pass the frozen hidden tests (the ninth
  fails to import matplotlib). The runtime labeller gives the intended mode on 7 of 9; the misses are that unloadable
  file and a Misra-Gries 'majority vote' that counts candidates in a Counter, labelled hash_count. The AST labeller
  matches 6 of 9.
* Novelty audit: 2 correct programs labelled 'other' among 6,854 correct programs (1 catalogue variant, 1
  degenerate); **no correct novel algorithm** (rule-of-three 95% bound 0.00044 per correct program).
* Placebos fail as they must. Shuffling β across units gives a mean ρ of 0.00 over all permutations. Shuffling labels
  between twin and escape rows drives E to ≤ 0.007 on average (observed E up to 0.44).
* Hash chain: 144 lines, 0 breaks (`python src/verify_chain.py`). The only committed files that changed after their
  last commitment are A1's `tests.jsonl` and `build_report.json` (deviation D-A1-rebuild: informational timing fields
  only).

### Deviations (all logged in `results/deviations.jsonl`, summarised in `results/summary.md`)

D-A1-rebuild (A1 builder re-run after freezing; identical cases), D-tracer-shared (tracer extended after A1–A3
froze; no A1–A3 feature affected), D-validity-has-solve (commented-out programs re-marked invalid uniformly),
D-reserve-extension (A8/A9 built as a labelled extension although the mid-artifact rule did not trigger),
D-early-draws (full twin/base drawn in the first model loads), D-states-compact, D-ec-T2-twin (engine-check cell
re-run), D-recheck-late (labeller re-check after Extra-arm-A stage 1; no label changed), D-half-screen-code,
D-iter1-purged (not needed: Step 1 β available), D-assoc-mapping (association rival mapped every answer to the
default; corrected post hoc beside the committed values).

## Repository layout

```
README.md                 this file
reproducibility.md        exact environment, downloads, env-var names, commands in run order, expected numbers
method.py                 entry point (setup / workers / unit / final); describes the method and the rival baselines
pyproject.toml            direct dependencies; requirements.lock.txt = exact environment (uv pip freeze)
method_out.json           exp_gen_sol_out: datasets panelA_units / panelA_cells / existing_remeasure + all analyses
full_/mini_/preview_method_out.json   size variants of method_out.json
pooled_inputs.json        schema iter5_panel_v1: raw per-unit ingredients for next round's pooling (both panels)
commitments.log           sha256 hash chain (COMMIT0, COMMITE, LABELLER_<u>, UNIT_<u>, NODEFAULT_<u>)
predictions/              protocol_commit0.json, commitE.json, precision_rule.json, models.json, unit_<u>.json
src/                      pipeline code
  cfg5.py                 constants, paths, thresholds (committed at #0)
  stage0.py               inputs manifest, dataset extraction, seeds, precision rule
  specs5.py               frozen unit specs, twin nouns, prompt rendering and audit
  engine5.py hooks5.py    exp19 engine/hooks (diff: results/engine_diff.txt) -- bf16, per-model stop set
  sampler5.py             CRN sampling of every arm, ban-free dose unit, realised-displacement log
  gpu_worker.py jobs.py   priority job queue with the commit guard; job builders
  controller.py           keeps the queue fed (Extra arm A, push arms after commits, escape top-ups)
  label_worker5.py        labelling of every sampled row (existing bench/path labellers + new units)
  unit_commit.py          default, rivals, base audit, prediction file, commitment
  freeze_unit.py          gate.json + labeller.frozen + LABELLER_<u> commitment
  metrics.py escape_rule.py analysis_a1a2.py   FROZEN analysis (sha256 in predictions/protocol_commit0.json)
  final_run.py            frozen analysis on the primary and extension sets + 'half + screen'
  engine_check.py recheck.py novelty_audit.py fix_validity.py outputs5.py figures5.py report5.py verify_chain.py
  assoc_fix.py            POST HOC corrected association rival (D-assoc-mapping)
  external_refs.py        TheAlgorithms implementations through the frozen tests and labellers
  manual_steps.py         the one-off steps first run as inline snippets (initial jobs, commits #0/#E, A8/A9, EC re-run)
newbench/
  common/                 runner5 (sandbox), tracer5 (runtime features), harness5, astlib, label5, judge5, build5, gate5
  A<k>_<name>/            spec.json, unit_def.py (references, mutants, generator, probes), tests.jsonl, checker.py,
                          runtime_rules.py, ast_rules.py, probes.json, references/, mutants/, build_report.json,
                          gate_round0.json, gate_holdout.json, gate.json, labeller.frozen
data/
  prompts_new.jsonl prompts_assoc.jsonl   rendered prompts (ids, spans, sha256)
  raw/<task>.jsonl        every sampled row (text, token ids, finish reason, realised displacement)
  labels/<task>.jsonl     one label row per sample (tests, runtime / AST / judge labels, code)
  samples.jsonl           one row per program with the plan's OUTPUT schema (8,390 rows)
results/                  a1*.json a2*.json half_screen.json extra_arm_a.json unit_summaries*.json unit_<u>_summary.json
                          knob_rows*.json repertoire_check*.json sensitivities.json engine_check.json gpu_tests.jsonl
                          labeller_recheck.json prompt_audit.json units_gate.json novelty_audit.json margins/ base_audit_<u>.json
                          timing*.json costs.json deviations.jsonl guard_check.json summary.md ...
figures/                  fig1-fig5 (.pdf + .png); specs/ = the JSON specs and plotted numbers
audit/                    rederive.py, rederive2.py (stdlib-only re-derivations + placebos) and their *_report.json
tests/                    CPU tests of the analysis and the hash chain (pytest)
inputs/                   read-only copies of earlier iterations' code and data (sha256 manifest)
states/                   per-task clean-twin states and ban-free dose units (npz)
queue/                    the GPU job files that were run (done/) -- the exact work list
```

Figures: `fig1` β against E with Wilson and bootstrap bars (existing tasks in grey); `fig2` the per-direction escape
heat map; `fig3` twin/base/PN/escape compositions; `fig4` Extra arm A against iteration 4; `fig5` every
pre-registered predictor against E.

## How to run

See `reproducibility.md` for the exact environment, downloads, environment-variable names and the commands in the
order they were run.

`method.py` is the entry point: `python method.py setup | workers | unit <A1..A9> | final` runs the stages below. In
this workspace only `final` should be rerun, since `setup` would overwrite files already in `commitments.log`. The
explicit sequence is:

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r requirements.lock.txt
huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218
huggingface-cli download Qwen/Qwen3-8B-Base --revision 49e3418fbbbca6ecbdf9608b4d22e5a407081db4
.venv/bin/python src/stage0.py                 # precision rule, inputs manifest, dataset extraction, seeds
.venv/bin/python src/specs5.py                 # freeze A1-A7 specs and render prompts (A8/A9: see D-reserve-extension)
.venv/bin/python -m pytest -c pytest.ini tests # CPU tests
# commit #0 / #E (see predictions/protocol_commit0.json); then start the three long-running processes:
.venv/bin/python src/gpu_worker.py & .venv/bin/python src/label_worker5.py & .venv/bin/python src/controller.py &
# per unit: build, gate, freeze, commit (the controller enqueues its pushes once UNIT_<u> is in commitments.log)
.venv/bin/python -m newbench.common.build5 A1 && .venv/bin/python -m newbench.common.gate5 A1
.venv/bin/python src/freeze_unit.py A1 round0 && .venv/bin/python src/unit_commit.py A1
# after all rows are labelled
.venv/bin/python src/fix_validity.py && .venv/bin/python src/novelty_audit.py && .venv/bin/python src/final_run.py
.venv/bin/python src/engine_check.py && .venv/bin/python src/recheck.py
.venv/bin/python src/outputs5.py && .venv/bin/python src/figures5.py && .venv/bin/python src/report5.py
python3 -I audit/rederive.py && .venv/bin/python src/verify_chain.py
```

The OpenRouter judges need `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY`. Every judge call is cached
(`data/judge_cache*.jsonl`), so a rerun of the labelling reuses the recorded verdicts and makes no new calls.

## Kept artifacts

Everything this module produced stays where it was written, on the run's storage volume: `data/`, `states/`,
`results/`, `predictions/`, `newbench/`, `inputs/` and `figures/`. These are text, code or small files, which are
always kept. The published repository omits only files of 100 MB or more, and none exist here (the largest is
`data/samples.jsonl`, about 10 MB).

## Restoring removed files

`.aii/manifest.yaml` marks only regenerable caches for deletion after the round. Each comes back with one command:

| Removed path (manifest entry) | Command that restores it |
|---|---|
| `.venv/` (≈ 9 GB) | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r requirements.lock.txt` |
| `**/__pycache__/` | recreated automatically by Python on the next run of any script (e.g. `.venv/bin/python method.py final`) |
| `.pytest_cache/` | `.venv/bin/python -m pytest -c pytest.ini tests` |

The model weights live in the shared Hugging Face cache, not in this folder:
`huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218` and
`huggingface-cli download Qwen/Qwen3-8B-Base --revision 49e3418fbbbca6ecbdf9608b4d22e5a407081db4`.

## Dependency use and licences

All 10 datasets of the dependency `art_j3Rm_lr2nzR6` were read (`results/dependency_usage.json`):

* LeetCodeDataset: problem sources and the I/O pairs behind every unit's hidden tests.
* concreteness_norms: the twin nouns.
* thealgorithms_python (MIT): the external cross-check above.
* Mercury, llm-creativity, KodCode, XLCoST, CLRS-text, HumanEval+ and EnAMEL: inventoried (counts per task or unit,
  recorded with their intended roles) and not otherwise used.

Program text is stored only for the MIT TheAlgorithms extract. The CC-BY-NC (Mercury, KodCode) and CC-BY-SA (XLCoST)
extracts keep counts and paths only. Reference implementations, mutants and labellers were written for this
repository. Iteration-2/3/4 code and data are copied from this run's own artifacts.
