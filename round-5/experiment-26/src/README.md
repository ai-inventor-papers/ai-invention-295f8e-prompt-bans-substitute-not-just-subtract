# Panel B: does base-model variety predict which coding tasks random pushes can move?

Iteration-5 confirmation of Claims **A1** and **A2** on **Qwen3-8B** (instruct, revision `b968826d`) and
**Qwen3-8B-Base** (revision `49e3418f`, pinned here), panel B of two. Panel A runs the same design on other units; the
next round pools both halves mechanically through `pooled_inputs.json`.

- **A1.** Across coding units, does the base model's off-default share `beta_u` rank the escape fraction `E_u`
  (the share of 8 fresh isotropic random pushes that move the instruct model's algorithm, at alpha 1 and 2)?
- **A2.** For units that move, does the base model's runner-up mechanism `r_u`, and its whole correct-only
  composition, forecast where the pushes land better than association answers (ASSOC) and AST proximity (PROX)?

`beta_u`, `r_u`, the base composition and every rival predictor are computed ban-free from frozen samples and
sha256-committed **before** the unit's first push sample. Within this panel, A1 and A2 are **descriptive**: about 7
units cannot reach the pooled bar (rho >= 0.6 with p < 0.01 needs rho >= 0.893 at n = 7).

## Results (panel B)

**A1 (descriptive, n = 7):** Spearman rho(beta_u, E_u) = **0.21**, exact one-sided permutation p = 0.333 (exact enumeration (5040 permutations)), unit-bootstrap 95% CI [-0.75, 0.95]. Secondary target: rho(beta_u, PN_excess_u) = 0.82 (p = 0.017). Partial Spearman given K_u = 0.38. The pooled bar (rho >= 0.6, p < 0.01) cannot be reached by one panel; this number goes to the pooled test through `pooled_inputs.json`.

All 7 new units were base-diverse (beta >= 0.05, predicted MOVABLE); 4 moved (E > 0) and 3 did not. Movable x beta class: {'beta<0.05': 0, '0.05<=beta<0.2': 1, 'beta>=0.2': 3}; immovable: {'beta<0.05': 0, '0.05<=beta<0.2': 1, 'beta>=0.2': 2}. No unit was base-collapsed, so the 'collapsed -> immovable' half of the claim is untested in this panel.

| unit | default | K | beta_u | beta (attempts) | beta (plain) | r_u | E (a=1) | E (a=2) | E_u | push landing | PN excess | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B1 missing number | arithmetic_sum | 5 | 0.06 | 0.19 | 0.12 | xor_fold | 0.000 | 0.000 | 0.000 | - | 0.00 | - |
| B2 single number | hash_count | 4 | 0.56 | 0.60 | 0.43 | xor_fold | 0.375 | 0.500 | 0.438 | xor_fold | 0.30 | - |
| B3 mst weight | kruskal | 4 | 0.11 | 0.42 | 0.33 | prim_heap | 0.125 | 0.125 | 0.125 | prim_heap | 0.06 | - |
| B4 integer sqrt | binary_search | 6 | 0.37 | 0.44 | 0.50 | float_sqrt | 0.125 | 0.125 | 0.125 | linear_scan | 0.10 | - |
| B5 all subsets | backtracking | 4 | 0.37 | 0.38 | 0.58 | iterative_doubling | 0.000 | 0.000 | 0.000 | - | 0.08 | - |
| B6 valid anagram | sort_compare | 3 | 0.81 | 0.80 | 0.55 | hash_count | 0.000 | 0.000 | 0.000 | - | 0.12 | - |
| B7 count inversions | merge_sort_count | 4 | 0.75 | 0.75 | 0.00 | sorted_insertion_bisect | 0.250 | 0.375 | 0.312 | sorted_insertion_bisect | 0.18 | default_from_few_correct(n_correct=3); twin_pass_below_0.7(0.06); base_fewer_than_20_correct(n=15): attempt composition used |

**Rival predictors** (Spearman with E_u; paired unit-bootstrap CI of rho(beta, E) - rho(rival, E)):

| predictor | rho with E | one-sided p | rho(beta) - rho(rival), 95% CI |
|---|---|---|---|
| beta_u (ours) | 0.21 | 0.333 | - |
| R_margin | 0.21 | 0.333 | [-1.32, 1.38] |
| R_merit_runtime | 0.54 | 0.114 | [-1.32, 0.67] |
| R_merit_length | 0.58 | 0.090 | [-1.40, 0.81] |
| R_modal | 0.11 | 0.429 | [-0.93, 0.88] |
| R_novel | -0.03 | 0.543 | [-0.68, 0.87] |
| R_novel_correct | -0.03 | 0.543 | [-0.69, 0.88] |
| K_u | 0.07 | 0.448 | [-1.49, 1.59] |

**Sensitivities** (rho, p): beta_attempt 0.39 (0.183); beta_plain -0.45 (0.857); beta_correct 0.04 (0.471); exclude_uncertain_class -0.03 (0.539); b2_split_label 0.43 (0.169); exclude_flagged_twins 0.06 (0.467). **Placebo** (beta shuffled, 1,000x): mean rho 0.008, rejection rate at p < 0.05 = 0.048.

**A2 (4 events: movable units with beta >= 0.05 and a defined landing):** top-1 hits 3.0 / 4 (chance 1.20), exact Poisson-binomial p = 0.081. Per-event log scores:

| unit | r_u | push landing | hit | log score BASE | ASSOC | PROX |
|---|---|---|---|---|---|---|
| B2 | xor_fold | xor_fold | 1.0 | -0.17 | -0.10 | -0.95 |
| B3 | prim_heap | prim_heap | 1.0 | -0.30 | -0.10 | -0.94 |
| B4 | float_sqrt | linear_scan | 0.0 | -1.10 | -3.29 | -1.57 |
| B7 | sorted_insertion_bisect | sorted_insertion_bisect | 1.0 | -2.39 | -3.18 | -1.02 |

Paired log-score differences: BASE_minus_ASSOC: mean 0.68 nats over 4 events (0.10-nat margin met: yes); BASE_minus_PROX: mean 0.13 nats over 4 events (0.10-nat margin met: yes). With fewer than 5 events no Wilcoxon test is run; events are listed.

**Extended A1 views (descriptive, committed addendum):** new units + re-measured parents: rho 0.43 (p = 0.055, n = 15); new units + parents + variants with cluster-preserving permutation: rho 0.54 (p = 0.015, n = 22, 7 parent-variant clusters).

**Within-parent (disguised variants, 8 pairs):** default shifted in ['T10', 'T14']; among pairs without a shift, sign agreement of delta-beta and delta-E 0/1; Spearman(delta-beta, delta-E) = 0.13 (p = 0.500).

| parent | default P / V | beta P | beta V | E P | E V | McNemar (confirmed) P-only / V-only |
|---|---|---|---|---|---|---|
| T03 | full_sort / full_sort | 0.41 | 0.35 | 0.500 | 0.750 | 1 / 5 |
| T10 | union_find / bfs | 0.37 | 0.96 | 0.188 | 0.312 | 2 / 4 |
| T05 | hash_map / hash_map | 0.14 | 0.05 | 0.000 | 0.000 | 0 / 0 |
| T06 | hash_set / hash_set | 0.20 | 0.32 | 0.000 | 0.000 | 0 / 0 |
| T04 | naive / naive | 0.18 | 0.15 | 0.000 | 0.000 | 0 / 0 |
| T08 | iteration / iteration | 0.40 | 0.07 | 0.000 | 0.000 | 0 / 0 |
| T14 | sort_by_count / NO_DEFAULT | 0.26 | - | 0.000 | 0.000 | 0 / 0 |
| R1 | greedy_end / greedy_end | 0.23 | 0.08 | 0.000 | 0.000 | 0 / 0 |

**Screen view (descriptive, cross-engine):** beta from the iteration-5 Step-1 base repertoire vs iteration-4 E (ban unit, FP8) on the 15 screen tasks: rho 0.79 (p = 0.0003). These tasks generated the hypothesis, so this is not a test.

**Reading.** Within panel B the primary A1 statistic is weak and not significant: beta_u does not rank the escape fraction (rho 0.21, p = 0.33). The units that moved (B2, B3, B4, B7) and those that did not (B1, B5, B6) overlap in beta; two clearly base-diverse units stayed immovable at alpha <= 2, which is the disconfirming pattern for the 'diverse -> movable' half of the claim. The graded plan-noise target agrees better (rho 0.82, p = 0.017), and the pooled descriptive views that add the re-measured parents and the variants are positive, but none of these is the pre-registered primary test and n is small. A2 is suggestive: r_u named the push landing in 3 of 4 events (p = 0.08), and the base composition out-scored the association forecast in log score; with fewer than five events this stays descriptive. These panel-B numbers are inputs to the pooled panel A + B test, not a verdict on their own.

**Validity checks.**
- Engine check (bf16 here vs FP8 in iteration 3/4, same slots): T03 rand_9002 per-slot label agreement 0.74, JS 0.021 vs null q95 0.051 (within template-resampling null); T2 rand_9004 0.64, JS 0.051 (outside null (precision sensitivity, reported)). Twins: T03 1.00, T2 0.98. No gross failure.
- Labeller gates (stage ii): B1 gated (kappa 1.00); B2 gated (kappa 0.93); B3 gated after revision (kappa 0.93, holdout 1.00); B4 gated after revision (kappa 1.00, holdout 1.00); B5 gated after revision (kappa 0.89, holdout 0.83); B6 gated (kappa 1.00); B7 gated after revision (kappa 0.87, holdout 1.00). 15-program blind base audits: B1 1.00, B2 1.00, B3 1.00, B4 0.93, B5 0.93, B6 1.00, B7 1.00.
- Novelty audit: 12 distinct correct 'other' programs among 10366 correct programs; verdicts {'CATALOGUE_VARIANT': 7, 'DEGENERATE': 5}; no correct novel algorithm (rule-of-three upper bound 3/N = 0.0003 per correct program).
- Independent re-derivation: 0 mismatches; twin-as-push placebo E = 0 for all units: yes; shuffled-beta mean rho 0.011.
- Commit order: chain breaks 0; push rows before their unit's commit 0; analysis code committed before the first push: yes; commit #0 before the first sample: yes.
- OpenRouter spend: USD 0.192 over 1000 judge calls (cap 2.00).
- GPU: 740 batches of 20 rows, 1.74 GPU-hours of sampling on one RTX 4090 (bf16).


## What was done

1. **Seven new units** (candidate list B, all built and all enrolled), each with new wording that contains no
   algorithm or data-structure word (`units_spec.BANNED_BASE` + catalogue names and aliases), generated hidden tests
   checked by two independent oracles, a catalogue of 3 to 6 test-passing references (`units/<u>/references/`),
   mutants that must fail, brute-force methods that must exceed the limit, and gated runtime + AST labellers:
   B1 missing number, B2 single number, B3 MST weight, B4 integer square root, B5 all subsets, B6 valid anagram,
   B7 count inversions. The reserves B8/B9 were not needed (7 >= 5 units passed by T+3:00).
2. **Per unit, in this order:** the instruct twin (N = 50, CRN) fixes the default; the base repertoire is sampled
   under the identical chat-templated token ids (N = 200, plus a plain-completion sensitivity, N = 50);
   `beta_u`, `r_u`, the base composition and the rivals are hash-committed; only then do the escape population
   (8 isotropic directions x alpha 1, 2 x N = 10, confirmed at N = 30), plan noise (alpha 1, 2, N = 50, a fresh
   direction per sample) and temperature 1.3 (N = 50) run.
3. **Extra arm:** narrative-disguised variants of eight bench tasks (T03, T10, T05, T06, T04, T08, T14, R1; the path
   tasks T2/T1 skipped), each with a paired parent re-measure on the same engine, the same ban-free unit and the same
   8 direction seeds; within-parent delta-beta vs delta-E addresses the task-affordance confound.
4. **Audits:** engine check against the iteration-3/4 rows, two-stage labeller gates, 15-program blind-judge base
   audits, structural audit, novelty audit of every correct `other` program, independent re-derivation with
   placebos, commit-order proof.

## Design constants (frozen in commit #0, `predictions/protocol_v5_panelB.json`)

| item | value |
|---|---|
| decoding | T = 1.0, top-p 1.0, no top-k, thinking off, max 1024 new tokens, fence stop, exp8 inverse-CDF CRN sampler |
| engine | bf16 HF on an RTX 4090 (precision rule: FP8 only if cc >= 8.9 and VRAM < 19.5 GiB); batches of 20 rows |
| twins | W1-W5 neutral twins (`Do not use <noun> for this task.` + ' .' padding to the display-name length) |
| push | `h_S <- h_S + (alpha n[l,p] - (h_S - h_twin).u) u` at blocks 12-23, task-spec positions, prefill only |
| ban-free unit | `n[l,p] = r_Q(l) * ||h_twin_clean[l,p]||`, r_Q from exp23 `qwen_ratio.json` (plain variant) |
| directions | `seed(unit, k) = int(sha256('iter5|panelB|{unit}|dir|{k}')[:8], 16)`, k = 0..7 (variants: parent's seeds) |
| escape rule | stage 1 (N = 10): share >= twin + 0.20 and pass >= 0.8 x twin; confirmed at N = 30 with one-sided exact binomial p < 0.05 vs p0 = (k_twin + 0.5)/(n_twin + 1) |
| default | modal correct-only twin label with share >= 0.6 (N = 50), else NO_DEFAULT |
| share | catalogue off-default labels / valid attempts (invalid and disputed excluded) |

## Layout

| path | what it holds |
|---|---|
| `method.py` | entry point; `uv run method.py` re-runs the CPU-only final stage (analysis, audits, figures, outputs); `--stage all` re-runs everything (GPU) |
| `method_out.json` (+ `full_`/`mini_`/`preview_`) | exp_gen_sol_out: `panelB_units` (one example per unit: spec -> twin default, base-model predictions, every analysis quantity) and `panelB_cells` (one example per unit x arm x cell) |
| `pooled_inputs.json` | one record per unit (schema `iter5_panel_v1`, `predictions/pooled_inputs_schema.json`) for pooling with panel A |
| `commitments.log` | sha256 hash chain of every committed file (protocol, analysis code, gates, per-unit predictions) |
| `predictions/` | `protocol_v5_panelB.json`, `precision.json`, `units/<u>.json` (committed per-unit predictions), schema |
| `src/cfg5.py`, `src/engine5.py`, `src/sampling5.py`, `src/ctx5.py` | constants, bf16 engine + CRN sampler with fence stop, arm registry and B = 20 batches, push edits + realised-displacement logging |
| `src/units_spec.py` | frozen spec cards (wording, catalogue, aliases) of B1-B7 |
| `src/units/b1.py ... b7.py` | per-unit tests generator, two oracles, references, mutants, excluded methods, probes, runtime and AST rules |
| `src/unitlib.py`, `src/sandbox_tests.py`, `src/sandbox_trace.py` | sandboxed test runner and the runtime tracer (instrumented ints/strings, C-call profile, call depth, line growth) |
| `src/unitbuild.py`, `src/gate2.py` | gate stage (i) (references, mutants, limits, oracles) and stage (ii) (gold set, two blind judges, kappa) |
| `src/label5.py`, `src/judge5.py`, `src/labels_view.py` | label worker, OpenRouter judges with cache and budget stop, final labels and the escape rule |
| `src/quantities.py`, `src/quantities_extra.py`, `src/commit5.py` | per-unit predictions, rivals, forecasts, grep audit, and the hash-chained commit |
| `src/units_extra.py` | disguised variants + paired parents (bench labeller adapter) |
| `src/margins.py` | teacher-forced opening log-probs (R_margin) |
| `src/engine_check.py`, `src/novelty_audit.py`, `src/vendor_check.py`, `src/outputs.py`, `src/figures.py` | engine check, novelty audit, vendored-input integrity, final outputs, figures |
| `analysis/a1a2.py`, `analysis/variants.py` | frozen A1/A2 and within-parent analysis (committed before the first push) |
| `analysis/a1_extended.py` | committed addendum: panel + parents view and cluster-preserving A1 |
| `analysis/screen_view.py` | descriptive screen view: Step-1 beta vs iteration-4 E on the 15 screen tasks (cross-engine) |
| `audit/rederive.py`, `audit/commit_order.py` | independent re-derivation with placebos; commit-order proof |
| `audit/rederive_headlines.py` | short separate re-derivation of every headline number (A1, PN, A2, extended and screen views, per-unit values) with shuffled-beta, shuffled-r_u and constant-beta placebos -> `results/rederive_headlines.json` |
| `src/build_prompts.py`, `src/commit_steps.py` | prompt rendering before commit #0; the two inline hash-chain commits as a script |
| `reproducibility.md` | the exact commands, in order, with hardware, seeds, environment variables and expected numbers |
| `tests/test_analysis.py` | the analysis code on synthetic units (planted rho), permutation/Poisson-binomial checks |
| `tests/test_cpu.py` | build checks, tracer sanity, banned-word grep, planted-ban grep positive control, chain verification |
| `tests/test_datasets.py` | roles of the other five dependency datasets (HumanEval+ harness, EnAMEL references, CLRS name mapping, Mercury AST labels, llm-creativity prior) |
| `src/adjudicate_all.py`, `src/vendor_check.py`, `src/prefill_cache.py`, `src/readme_fill.py` | final adjudication pass, vendored-input integrity, cache regeneration, README rendering from results |
| `README.template.md` | README source; `src/readme_fill.py` fills the results and deviations sections from the result files |
| `units/<u>/` | tests.jsonl, references/, mutants/, build_report, gate_stage_i, gate (+ revision/holdout), catalogue_frozen, default, neutral nouns, positions |
| `data/samples_raw.jsonl` | every sampled program with its raw text and token ids (both models) |
| `data/samples.jsonl` | one row per program: model, unit, arm, site, alpha, seed, template, slot, temperature, label, labeller source, passed, finish reason, tokens, realised displacement, code |
| `data/labels.jsonl`, `data/judge_labels.jsonl`, `data/judge_cache.jsonl` | labeller output, judge adjudications, judge cache |
| `data/prompts.jsonl`, `data/prompts_extra.jsonl` | every rendered prompt (token ids, task-spec span) |
| `results/` | `a1_panel.json`, `a2_panel.json`, `a1_extended.json`, `variants.json`, `rivals.json`, `repertoire_check.json`, `unit_outcomes*.json`, `units_table.csv`, `engine_check.json`, `novelty_audit.json`, `label_audit.json`, `structural_audit.json`, `rederive.json`, `commit_order.json`, `vendor_check.json`, `timing*.json*`, `costs.json`, `deviations.json` |
| `figures/` | F1 beta vs E, F2 per-direction escape heatmap, F3 base composition vs push landing, F4 rivals vs E, F5 within-parent delta-beta vs delta-E, F6 base vs plan-noise Hill-1 (PDF + PNG, specs in `figures/specs/`) |
| `vendor/` | read-only copies of the iteration-2/3/4 inputs used (bench labellers, exp8 suite, exp17 prompts/directions, exp23 r_Q, exp22 engine); `vendor/SHA256SUMS` |
| `inputs/sources.json` | the rows extracted from the dependency dataset (LeetCode rows, inversion rows, neutral-noun bank, validation subsets) |
| `directions/`, `cache/` | push directions (`rand_<seed>.npy`) and fp16 push-norm caches |

Kept artifacts stay on the run's storage volume at these relative paths; files of 100 MB or more are not part of the
published repository (none of this artifact's data files is that large).

## How to run

```bash
uv sync                                   # Python 3.12, every package pinned in pyproject.toml / uv.lock
uv run method.py                          # final stage: analysis, audits, figures, outputs (CPU, ~10 min)
uv run method.py --stage all              # the whole pipeline (needs one 24 GB GPU and OPENROUTER_* variables)
uv run audit/rederive_headlines.py        # independent re-derivation of the headline numbers
```

`reproducibility.md` lists the exact order in which the stages were actually run.

Environment variables (no absolute paths are stored in this repository):

| variable | used by | meaning |
|---|---|---|
| `AII_DEP_ART_J3RM` | `src/extract_sources.py`, `tests/test_datasets.py` | folder of the dependency dataset `art_j3Rm_lr2nzR6` (holds `full_data_out.json`); default: a sibling folder named `art_j3Rm_lr2nzR6` |
| `AII_DATA_FIG_GEN_SCRIPTS` | `src/figures.py` | the aii-data-fig-gen `scripts/` folder (house style + generator) |
| `AII_STEP1_BASE_REPERTOIRE` | `analysis/screen_view.py` | optional; default: the snapshot `inputs/exp24_base_repertoire_snapshot.json` |
| `HF_HUB_CACHE` | `src/engine5.py` | Hugging Face cache holding the two pinned model snapshots |
| `OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY` | `src/judge5.py` | blind judges (OpenRouter only; judge responses are cached in `data/judge_cache.jsonl`) |

## Restoring removed files

Only regenerable bulk is removed after the round (see `.aii/manifest.yaml`); every result, prediction, unit build,
figure and data file stays.

| removed path | restore with |
|---|---|
| `.venv/` | `uv sync` |
| `src/__pycache__/`, `src/units/__pycache__/`, `analysis/__pycache__/` | regenerated on import, or `python -m compileall src analysis` |
| `vendor/exp11/bench/__pycache__/`, `vendor/exp11/bench/common/__pycache__/` | regenerated when the bench labeller is imported (`python -m compileall vendor/exp11/bench`) |
| `vendor/exp8/suite/tasks/__pycache__/`, `vendor/exp8/suite/labeller/__pycache__/` | regenerated when the exp8 suite labeller is imported (`python -m compileall vendor/exp8/suite`) |
| `vendor/exp23/__pycache__/` | regenerated when `vendor/exp23/prox.py` is imported (`python -m compileall vendor/exp23`) |
| model weights (shared Hugging Face cache, never in this folder) | `huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218` and `huggingface-cli download Qwen/Qwen3-8B-Base --revision 49e3418fbbbca6ecbdf9608b4d22e5a407081db4` |
| `cache/` (kept; if absent) | `uv run src/prefill_cache.py --all` (instruct model on a GPU) |

## Deviations from the plan

- **base_n_200**: Base chat repertoire raised from N=100 (W1-W5 x k 0-19) to N=200 (W1-W5 x k 0-39) for every unit, decided before any unit commit or push sample: under the chat template Qwen3-8B-Base is 46-61% invalid (off-task text, no solve function), which left fewer than 20 correct base programs on B3 and B7 at N=100. The pilot (k 0-5) and gate-draw definitions are unchanged.
- **analysis_code_freeze_commit**: Commit #0 froze the protocol and every analysis rule verbatim in prose; the analysis code (analysis/a1a2.py, analysis/variants.py) is hash-committed later but before the first push sample of any unit (outcomes = push arms only), not before the first twin/base sample.
- **gpu_rtx4090**: The pod has an RTX 4090 (24 GiB, cc 8.9) instead of the planned A4500; the frozen precision rule selects bf16_hf (VRAM >= 19.5 GiB); batches of B = 20 rows.
- **models_shared_cache**: Model weights live in the run's shared HF cache (HF_HUB_CACHE), not in WORK/hf_cache, per the run's storage rules; nothing to delete in the workspace.
- **sampling_order**: All seven unit specs were frozen first and every unit's twin/novelty/association (instruct) and base sessions were sampled before the labellers were built (GPU throughput was ~10x the plan's estimate); build stratification is therefore moot: all seven candidates were built and every gated unit is enrolled.
- **b6_adversarial_stress**: B6: the quadratic remove-one-by-one method passed the original random stress cases (list.remove finds a uniformly distributed letter within ~26 positions); two adversarial maximum-size stress cases (opposite letter blocks) were added before the gate, after which it fails the 1 s limit and stays excluded_by_limit.
- **gate_abstention**: Gate stage (ii) metrics: the runtime labeller abstains (None) on programs it cannot trace (crash, timeout, import of an unavailable package); kappa(runtime, AST) and runtime-vs-adjudicated are computed over traceable items, the all-items versions are reported, and combined-vs-adjudicated >= 0.9 over ALL items is required in addition. B1/B2/B6 passed under the stricter all-items metric; B3/B4/B5/B7 passed after the single revision round (rule fixes: combinations-based brute force -> other, prim_array needs a visited/dist array, generic halving midpoint, user-defined isqrt/sqrt are not library calls, merge-sort label needs a non-unit counter increment inside the recursion, SortedList -> sorted insertion, quadratic line growth -> other); holdouts of 6 new adjudicated base programs: 6/6, 6/6, 5/6, 6/6.
- **b7_twin_flag**: B7: 47/50 twin programs are the O(n^2) pair scan, which exceeds the 1 s limit at n = 20000 (by the size bound), so the twin pass rate is 0.06 (< 0.7 abort signal). Not an engine bug; the unit is kept, the default comes from 3 correct twin programs and is flagged ('default_from_few_correct', 'twin_pass_below_0.7'); A1 is reported with and without flagged units.
- **extra_arm_pairs**: Extra arm: pairs T03, T10, T05, T06, T04, T08, T14, R1 (plan order with the path tasks T2 and T1 skipped: their variants need the exp8 suite and the heap-vs-array Dijkstra structural re-gate). Variants keep the parent's function name and argument names, so the parent's bench labellers and hidden tests apply unchanged (no wrapping). The twin and base sessions of the extra arm were sampled while the new-unit labellers were being built (pushes only after each P_/V_ commit).
- **engine_check_t2**: Engine check: T03 reproduces the exp17 composition within the template-resampling null (per-slot label agreement 0.74, code identity 0.64 under bf16 vs FP8); T2 (path task) is outside the null (dijkstra 31 / bf_spfa 7 / disputed 12 vs exp17 26/24), reported as precision sensitivity; no gross failure.
- **analysis_addendum_a1_extended**: analysis/a1_extended.py (panel+parents A1 view and the cluster-preserving clustered A1 of plan section 11, missing from the frozen a1a2.py) was hash-committed as an addendum after the B-unit pushes but BEFORE any push sample of a P_/V_ unit; its B-only content adds no new test on B outcomes.
- **screen_view_uncommitted_input**: analysis/screen_view.py reads beta for the 15 screen tasks from the iteration-5 Step-1 artifact's results/base_repertoire.json, which was not yet in that artifact's commit chain when read (snapshot + sha256 in inputs/), against iteration-4 E (ban unit, FP8): descriptive only.
- **dataset_checks**: tests/test_datasets.py runs the HumanEval+ and EnAMEL harness checks with `python -I` (site enabled, because the HumanEval+ test code imports numpy); the hidden-test sandbox itself runs `-I -S`.
- **raw_rows_location**: Raw text and token ids of every program are kept in data/samples_raw.jsonl (one file) rather than a data/raw/ folder; data/samples.jsonl is the labelled per-program table.
- **v_t14_no_default**: V_T14 (disguised top-k frequent) has NO_DEFAULT (twin modal correct share < 0.6): reported, excluded from A1, and its pair counts as a default shift in the within-parent analysis. Its escape cells were sampled before the default was known and are not analysed.
- **disputed_labels**: 10 of 14000 program rows remain 'disputed' (runtime/AST disagreement without a two-of-three judge majority); they are excluded from shares and counted. Gemini 2.5 Flash returned HTTP 429 on some calls; each call was retried up to three times.
- **variant_spot_check_threshold**: Variant gate: the plan asks for a judge spot-check of 10 variant gate-draw programs without a threshold; agreement >= 0.8 was required (all eight variants passed: 0.8-1.0).
- **no_staged_scaling**: Arms were not run in 10 -> 100 -> full stages: the first instruct session measured throughput (1-28 s per 20-row batch, results/timing.jsonl) and every later arm fit in minutes; abort signals were checked on the twin and base labels instead (B7 twin pass flagged; base invalid rates 46-61% handled by raising base N).
- **rival_sensitivities_not_computed**: Not computed: the R_merit variant using r_u's reference, per-cell correct-only Hill-1 for every cell (only arm-pooled base/PN/escape Hill-1 is reported), and a numerical comparison of the realised displacement with the iteration-4 S0 band (realised displacements are summarised in results/realised_displacement.json; relative error of the targeted component < 1e-3 in the GPU tests).
- **pooled_schema_panelA_absent**: predictions/pooled_inputs_schema.json: panel A's schema file was not on disk when the outputs were written (checked in the sibling panel-A workspace), so this panel's schema was written and pooled_inputs.json validated against it; panel A must assert equality or the next round must reconcile.
- **reserves_not_built**: B8/B9 were not built; all 7 candidates passed gate stage (ii) before T+3:00.
- **no_drops**: no arm was dropped; plain completion, T1.3, PN alpha 1 and 2 ran for every new unit.

