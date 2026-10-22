# Panel I: does the base model forecast where content-free nudges move Qwen3-8B's algorithm?

Iteration 6, Step 3 (Claim **L** primary, **M** and **K** secondary), panel I of two, on **Qwen3-8B** (instruct,
revision `b968826d`) and **Qwen3-8B-Base** (revision `49e3418f`). Every row is W16A16 (bf16), thinking off, and both
models read the identical chat-templated token ids.

**Claim L.** When a content-free push (an isotropic random direction added to the task-specification states at
blocks 12-23, or noise on the first 32 generated tokens) moves the instruct model off its default algorithm, the
algorithm it lands on is the one the **base model** ranks next (its runner-up `r_u` / composition `q_base`), better
than rivals built from the tuned model itself: its own sampled minority modes (`q_tail`, `t_u`) and its likelihood
ranking of the alternatives (`q_lik`, teacher-forced openings of verified forced programs). Chance is uniform over the
surviving algorithms. All forecasts of a unit were sha256-committed (`commitments.log`) before that unit's first nudge
row. With one panel of about ten units, L1a, L1b and M are **descriptive here**; the frozen `pool_l1.py` pools panels I
and II next round.

## Results (panel I)

**What happened.** All ten list-I units were built, gated and enrolled (nine passed gate (ii) at the first attempt,
I10 after its single revision round); no unit, arm or N was dropped by the clock. The instruct model is strongly
collapsed: 7 of the 10 units have an **empty tail** (zero correct non-default programs among 300 twin samples). Pushes
rarely moved it: only **7 of the 30** (unit, nudge type) pairs produced a landing event (>= 5 correct off-default
catalogue programs in pass-rate-gated cells), on four units (I2, I5, I6, I7); the escape fraction E_u is 0 for six
units.

- **Where nudges did land, the base runner-up named the landing in 5 of 7 events** (I2 ESC, I6 ESC, I7 ESC/PN/GTN).
  The two misses (I5 ESC and PN) landed on `min_heap_ends`, which is the tuned model's own minority mode (t_u) and its
  q_lik top-1, while the base runner-up was `sweep_events`. t_u named the landing in 5 of the 6 events where it is
  defined.
- **L1a (tail-empty events):** only 1 event (I6 ESC, a hit; Poisson-binomial p = 0.33). DESCRIPTIVE.
- **L1b (base vs q_lik where they disagree):** 6 discordant events; the base forecast alone hit 4 (I6 ESC, I7 ESC, PN,
  GTN), q_lik alone hit 2 (I5 ESC, PN); exact sign test p = 0.34. Under the frozen rule (n >= 6) this is a **FAIL**
  (not significant). The 6 events come from only 3 units; the unit-clustered version is 2 vs 1 (DESCRIPTIVE).
- **Log scores on the 7 matched events:** the base composition beats q_lik by +0.95 nats per program (one-sided 95%
  event-bootstrap lower bound +0.32; unit-cluster bound 0.00) and q_lik_raw by +16 nats (the raw-score softmax is
  near-degenerate). Against q_tail the mean is +0.25 nats, lower bound -0.05 per event (non-inferior at the -0.10
  margin) but -0.16 under the unit-cluster bootstrap (**not** non-inferior per unit).
- **L2:** 0 of 477 correct nudged off-default programs fell in a mode the base model never produced (rule-of-three upper
  bound 0.006). **Novelty:** 1 distinct correct 'other' program among 8,936 correct programs, judged a catalogue
  variant: no correct novel algorithm (bound 3/N = 0.00034 per correct program).
- **M (descriptive):** E_u is ranked by the frozen candidates twin modal share (Spearman -0.89, Holm p = 0.016, meets
  the frozen criterion) and base off-default share beta (+0.71, one-sided p = 0.014, Holm 0.07); E_u has six ties at
  0, so these rest on four moving units.
- **K:** plan noise at alpha 2 is nearly free (pass cost <= 4 points) but adds diversity mainly on the movable units
  (rarefied Hill-1 1.95 on I5 and 1.67 on I7, 1.10 on I1, 1.00 elsewhere); alpha 4 and the base-intent knob (BINT) raise rarefied Hill-1 on more units at larger pass costs (e.g. I1
  BINT 1.94 at 33 points, I8 BINT 2.06 at 10 points).

**Reading.** Panel I cannot decide Claim L. Its decisive ingredient, landing events on tail-empty units, almost never
occurred: content-free pushes of up to 0.41 x ||h|| left the default intact on six of the seven tail-empty units.
Where landings occurred, the base runner-up was right more often than q_lik (4 vs 2 discordant wins, 5/7 overall),
but the tuned model's own minority mode was right just as often (5/6), and the per-unit comparison with q_tail does
not clear the non-inferiority margin. The counts go to the pooled panel I + II test through `landing_events.json` and
`units.json` (schema `iter6_landing_v1`).

<!-- SUMMARY -->

## Validity checks

- **Gates (stage ii):** references 100% under both labellers on every unit; Cohen's kappa(runtime, AST) 0.86-1.00 and
  runtime vs adjudicated 0.92-1.00 on the gold sets (I10 after the revision round, holdout kappa 1.00).
  Style re-gate (10 nudged programs per unit, two judge families): 0% disagreement on every unit.
- **Base audits (15 programs per unit):** raw agreement of the final labels with each judge 0.53-1.00; most
  disagreements are 'other' (ours) vs 'invalid' (judges) on broken plain completions; with those merged, agreement is
  0.60-1.00. Relabelling the audited rows with the judges' joint label changes no unit's r_u
  (`results/label_qa.json`). Units below 0.8 are flagged in `units/<u>/base_audit.json`.
- **Engine check:** HF-50 vs vLLM-50 label composition inside the template-resampling null (2,000 resamples) on all ten
  units, so D_u, q_tail and p0 use the pooled twin rows as planned.
- **GPU tests** (`results/gpu_tests.json`): G1 CRN determinism, G2 batch-companion invariance, G3 alpha = 0 push equals
  the twin, G4 push rel_err < 1e-3 at every edited block, G5 GTN alpha = 0 equals the twin and the shadow tokens equal
  the GTN tokens inside the window: all pass. **G6 failed:** right-padded B-row teacher forcing differs from batch-1 by
  up to 1.26 nats per 48-token program (bf16 batch-shape noise), so q_lik and the fork margin use batch-1 teacher
  forcing (exact per sequence).
- **Realised displacement:** ESC/PN prefill pushes hit their target along u with relative error <= 8.4e-4; the target
  is 0.10 / 0.21 / 0.41 x ||h_twin|| at alpha 1 / 2 / 4; GTN rows <= 5.5e-4.
- **Integrity** (`results/commit_order.json`): 0 chain breaks; commit #0 precedes the first sample; the analysis-code
  addendum (pool_l1.py) and the enrolment hash precede the first nudge row; every unit's commit precedes its first
  nudge row; no nudge row predates the enrolment.
- **Re-derivation** (`audit/rederive.py`, no shared code): 0 mismatches for E_u, every landing event, L1a and L1b.
  Placebos: a random non-default forecast hits 0.338 of the L1a events against a chance of 0.333; the twin scored as a
  push gives E_u = 0 on every unit.
- **Sandbox harness check (dependency rows):** the docstring examples of 24 HumanEval+/EnAMEL canonical solutions run
  through the same sandbox: 30/38 cases pass; the 8 others return exactly the documented values but are rejected by the
  integer-only list rule of the `exact` checker (built for I7) or because JSON turns tuples into lists, which no list-I
  unit relies on (`results/harness_check.json`). All ten dependency datasets are accounted for in
  `results/dependency_usage.json`.
- **Headline re-derivation** (`audit/rederive_headlines.py`, reads the raw row files, labels and adjudications directly): the event count, r_u / t_u hits, L1a, L1b, both log-score differences, L2 and the two M correlations all match; placebos fail (random r_u: L1b p < 0.05 in 0% of 2,000 draws; E_u permuted across units: the M test reaches p < 0.05 in 3.5% of 200 permutations; a random Dirichlet forecast averages -0.19 nats against q_lik and never reaches the observed +0.95).
- **Spend and compute:** OpenRouter USD 0.34 over 1,411 judge calls (cap 2.00). One NVIDIA L4: vLLM 31.5 min (instruct
  4.8, base 25.2, BINT 1.5), HF CRN engine 71 min (twin 6.0, ESC stage 1 29.6, confirmations 7.2, PN 16.2, GTN 11.8).

## What was done

1. **Units (S1).** Ten new LeetCode-derived units in new wording with no algorithm or data-structure word
   (`src/units_spec6.py`; the grep audit and its planted-ban control are in `results/grep_audit.json`): I1 longest
   consecutive run, I2 group anagrams, I3 happy number, I4 h-index, I5 meeting rooms, I6 three values in place, I7 one
   counts 0..n, I8 first missing positive, I9 common values with repeats, I10 best single trade (reserves I11, I12:
   cards only, not needed).
2. **Unhooked sampling on vLLM bf16 (S2-S3).** Instruct: forced programs (5 wordings x 5 seeds per mode), 250 twin
   rows (150 at T 1.0, 100 at T 1.3), association answers. Base: 200 chat twin rows, 100 plain completions, 30 base
   intents. Per-request seeds from the frozen rule.
3. **Build and gate (S4).** Hidden tests checked by two independent oracles, one reference per mode at <= 0.25 x the
   limit, >= 3 mutants, excluded brute force that exceeds the limit; a runtime tracer built on `sys.monitoring`
   (opcode profile with BINARY_OP by operator, calls with argument sizes, input-list access counters, user-call depth)
   as the primary labeller and AST rules second; blind judges only on disagreement.
4. **HF CRN engine (S5).** Memory probe (B = 12), GPU tests, HF twin (50 per unit), q_lik passes; per-unit forecasts
   committed; enrolment order hashed.
5. **Nudges (S7)**, in enrolment order: ESC 8 fixed directions x alpha 1/2/4 x N 10 with confirmation to N 30, plan
   noise (a fresh direction per sample) at alpha 2 and 4 (N 50 each), generated-token noise at alpha 2 (N 50, shadow
   rows), and the BINT knob (N 30, vLLM).
6. **Analysis (S10)**: `pool_l1.py` (frozen), L2, L3, M, K, novelty audit, label QA, figures, independent
   re-derivation and the commit-order proof.

## Design constants (frozen in commit #0, `predictions/protocol_v6_panelI.json`)

| item | value |
|---|---|
| decoding | T 1.0 (twin T 1.3 rows on vLLM), top-p 1, no top-k, thinking off, max 1,024 new tokens, fence stop |
| HF engine | bf16 sdpa, CRN inverse-CDF sampler (float64 softmax(logits / T)), B = 12 rows of one (unit, template) prompt, prune = False |
| push | `h <- h + (alpha n[l,p] - (h - h_twin).u) u`, blocks 12-23, task-spec positions, prefill only; `n = r_Q(l) ||h_twin||` |
| GTN | generated tokens 1..32, blocks 12-23, teacher-forced shadow row as reference, alpha 2 |
| seeds | directions `sha256('iter6|panelI|'+unit+'|dir|'+k)[:8]`; PN / GTN per (unit, alpha, template, slot); CRN `sha256('iter6|panelI|'+unit+'|'+w+'|'+k)[:16]` |
| escape rule | stage 1 (N 10): share >= twin + 0.20 and pass >= 0.8 x twin; confirmed at N 30 with one-sided exact binomial p < 0.05 vs p0 = (k_twin + 0.5)/(n_twin + 1) |
| landing event | pass-gated cells of one nudge type pooled; >= 5 correct off-default catalogue programs; clear iff the modal mode leads by 15 points |
| default | modal correct twin label with share >= 0.6 over the 300 twin rows |

## Deviations from the plan

<!-- DEVIATIONS -->

## Layout

| path | what it holds |
|---|---|
| `reproducibility.md` | the exact commands run, in order, with hardware, timings, env-var names and expected numbers |
| `method.py` | entry point: `uv run method.py` re-runs the CPU-only analysis stage; `--stage all` runs every stage in order |
| `pool_l1.py` | the frozen, stdlib-only pooled test of Claim L (committed before the first nudge) |
| `landing_events.json`, `units.json` | panel-I inputs to `pool_l1.py` (schema `iter6_landing_v1`) |
| `method_out.json` (+ `full_`/`mini_`/`preview_`) | exp_gen_sol_out: `panelI_units`, `panelI_events`, `panelI_cells`, each with predict_base / predict_qlik / predict_tail |
| `commitments.log` | sha256 hash chain (genesis sha256('iter6|panelI')): commit #0, analysis addenda, unit commits, enrolment |
| `predictions/` | `protocol_v6_panelI.json` (frozen protocol), `units/<u>.json` (committed forecasts), `enrolment.json` |
| `src/cfg6.py`, `src/units_spec6.py`, `src/prompts6.py`, `src/build_prompts6.py`, `src/extract_sources6.py` | constants and seed rules, unit cards, prompt rendering and grep audit, dependency extraction |
| `src/vllm6.py`, `src/bint6.py` | unhooked vLLM sampling (instruct, base, BINT) |
| `src/engine6.py`, `src/ctx6.py`, `src/hf6.py` | HF bf16 CRN engine with push and GTN hooks, memory probe, GPU tests, q_lik passes, nudge scheduler |
| `src/units/i1.py ... i10.py`, `src/unitlib6.py`, `src/sandbox_tests6.py`, `src/sandbox_trace6.py`, `src/unitbuild6.py` | per-unit tests, oracles, references, mutants, probes and rules; sandboxed test runner and runtime tracer; stage (i) |
| `src/label6.py`, `src/judge6.py`, `src/labels_view6.py`, `src/gate6.py`, `src/forced6.py` | labelling, blind judges, final labels, gate (ii) and base audits, forced-program verification |
| `src/instruments6.py`, `src/commit6.py` | L instruments, engine check, per-unit commit, enrolment; hash chain |
| `analysis/` | event builder, secondary analyses (L2, L3, M, K), novelty audit, label QA, sandbox harness check, figures, outputs, summary |
| `audit/rederive.py`, `audit/rederive_headlines.py`, `audit/commit_order.py` | independent re-derivations with placebos (from samples.jsonl, and from the raw row files); integrity proof |
| `tests/test_cpu.py`, `tests/test_pool_l1.py` | CPU tests (builds, grep audit, tokenizer identity, chain tamper) and pool_l1 synthetic tests |
| `units/<u>/` | tests.jsonl, references/, mutants/, build report, gates, base audit, forced_verified.json, neutral noun, positions |
| `data/` | `raw_vllm.jsonl`, `raw_hf.jsonl` (every generation with token ids), `labels.jsonl`, `adjudications.jsonl`, `judge_cache.jsonl`, `samples.jsonl` (one row per program), `prompts.jsonl`, `realised_disp.jsonl` |
| `results/` | pool_l1_panelI, l2, l3, m, k, novelty, label_qa, cells, gpu_tests, hf_batch, grep_audit, commit_order, rederive, cpu_tests, qlik/, nudge_runs/, timing, costs, deviations, summary.md |
| `figures/` | F1 base forecast vs landings, F2 event table, F3 escape heatmap, F4 log-score differences, F5 M vs E_u, F6 knobs (PDF + PNG) |
| `vendor/` | read-only copies of the iteration-5 files the code was ported from, with `vendor/SHA256SUMS` |
| `directions/` | the push directions `rand_<seed>.npy` (kept on the run's volume) |
| `inputs/` | rows extracted from the dependency dataset (`sources.json`) |

Every kept artifact stays on the run's storage volume at these relative paths; no file here reaches 100 MB.

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r requirements.lock.txt
uv run method.py                    # analysis, audits, figures, outputs (CPU, ~10 min, a few judge calls)
uv run method.py --stage all        # the whole pipeline (one >= 20 GB GPU, OPENROUTER_* variables)
python pool_l1.py --events landing_events.json <panel II events> --units units.json <panel II units> --out pooled.json
```

Environment variables: `HF_HUB_CACHE` (the two pinned model snapshots), `OPENROUTER_BASE_URL` and
`OPENROUTER_API_KEY` (blind judges, cached in `data/judge_cache.jsonl`), `AII_DEP_ART_J3RM` (folder of the dependency
dataset `art_j3Rm_lr2nzR6`, holding `full_data_out.json`).

## Restoring removed files

Only regenerable bulk is removed after the round (`.aii/manifest.yaml`); every result, prediction, unit build, figure
and data file stays.

| removed path | restore with |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r requirements.lock.txt` |
| `__pycache__/`, `src/__pycache__/`, `src/units/__pycache__/` | regenerated on import, or `python -m compileall . src src/units` |
| model weights (shared Hugging Face cache, never in this folder) | `huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218` and `huggingface-cli download Qwen/Qwen3-8B-Base --revision 49e3418fbbbca6ecbdf9608b4d22e5a407081db4` |
