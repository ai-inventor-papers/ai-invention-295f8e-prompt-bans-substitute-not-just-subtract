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

<<RESULTS>>

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

<<DEVIATIONS>>
