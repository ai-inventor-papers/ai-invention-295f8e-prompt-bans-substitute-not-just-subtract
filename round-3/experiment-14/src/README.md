# Show a solution, ban it, see what replaces it

This is the Step-1b **exposure-ban** experiment on **Qwen3-8B** (bf16, thinking off, vLLM 0.11.0, revision `b968826d`). It runs over the 12 frozen tasks of the exp11 algorithm-choice bench.

For every non-default algorithm Y that has at least one correct forced program (33 Y; 19 of them **priority**, meaning the frozen associate differs from the default), the prompt shows up to 5 name-scrubbed correct programs of Y and then asks one of three things:

- **COPY** (the matched twin): `Write a correct solution.`
- **NAMED** (= frozen template W5): `Write a correct solution that does not use {Y}.`
- **UNNAMED**: `Write a correct solution that uses a different algorithm from the one above.`

There are N = 50 samples per Y and arm. The seed of each (task, Y, shown program, index) is shared by every arm.

Four forecasts of the replacement were committed in a sha256 hash chain **before any ban sample was drawn**:

| family | what it predicts | committed in |
|---|---|---|
| LADDER | the model's context-free default | COMMIT #1 |
| ASSOCIATE | the modal frozen "standard alternative to Y" answer | COMMIT #1 |
| PROXIMITY | the survivor nearest each shown program (Zhang-Shasha tree edit distance on identifier-normalised ASTs) | COMMIT #1 |
| SUBTRACT-IN-CONTEXT | the non-Y landing under an iterated persistent veto of Y's distinctive token n-gram, under the copy-twin prompt (no ban text) | COMMIT #2 |

All numbers below come from `results/` and were re-derived independently by `audit/rederive.py`: 0 mismatches over all 66 events.

## Main results (Qwen exposure stratum)

**1. Showing a solution makes the model copy it.**
- Under COPY, a mean 0.93 of attempts use the shown algorithm Y. The median is 1.00, and no Y is below 0.2.
- Its default appears in only 0.05 of COPY attempts.

**2. The ban is obeyed, and the replacement snaps back to the default.**
- NAMED avoidance (1 − share labelled Y) averages 0.95; UNNAMED averages 0.996.
- The default's share of attempts:

  | COPY | final veto round | NAMED | UNNAMED |
  |--:|--:|--:|--:|
  | 0.05 | 0.10 | 0.72 | 0.82 |

- In 24 of the 31 gated NAMED events the modal replacement *is* the default. For priority Y it is 14 of 18.
- NAMED and UNNAMED pick the same modal replacement for 0.88 of Y, and their landings are JS-consistent for 0.79 of Y. Naming Y adds little beyond "something else".

**3. Frozen C1 forecast contest (primary: gated NAMED events).**
- **Gate:** 31 of 33 events pass (avoidance ≥ 0.5 and ≥ 20 non-Y attempts). T03 size_k_heap and T11 patience_bisect fail because Y is kept.
- **Disagreeing events:** 30 of the gated events disagree.
- **Advance rule:**

  | family | wins | advances (≥ 3 wins)? |
  |---|--:|---|
  | LADDER | 7 | yes |
  | SUBTRACT | 2 | no |
  | ASSOCIATE | 2 | no |
  | PROXIMITY | 0 | no |

- **Frozen branch: `SUBTRACTION/LADDER (LADDER)`.**
- **Paired Wilcoxon tests (n = 30, Holm over 4).** None reaches p_Holm < 0.05. Positive differences favour the ban-free family.

  | difference | mean (nats) | task-cluster 95% CI | p | p_Holm |
  |---|--:|---|--:|--:|
  | SUBTRACT − ASSOCIATE | +1.02 | [0.35, 1.56] | 0.020 | 0.081 |
  | LADDER − ASSOCIATE | +1.29 | [0.10, 2.38] | 0.027 | 0.081 |
  | LADDER − PROXIMITY | +0.50 | [−0.40, 1.16] | — | 0.159 |
  | SUBTRACT − PROXIMITY | +0.23 | — | — | 0.96 |

- **Top-1 hit rate on gated NAMED events:**

  | LADDER | PROXIMITY | ASSOCIATE | SUBTRACT |
  |--:|--:|--:|--:|
  | 0.77 | 0.61 | 0.45 | 0.36 |

- **UNNAMED events (descriptive)** give the same branch. There LADDER − ASSOCIATE is Holm-significant (+1.42 nats, p_Holm = 0.0056).
- **Pre-registered sensitivities.** Every one returns LADDER with 7–9 wins: SUBTRACT-top1, excluding co-vetoed survivors, priority Y only (18 events), token-distance PROXIMITY, correct-only landings, and excluding labeller-flagged tasks. The exception is "exclude undefined SUBTRACT", which has only 2 events and is therefore UNDETERMINED.

**How strong is the verdict? Read it with these caveats.**
- **The ≥ 3-wins counting rule is not a significance test.**
  - Unit test T1(f): under a no-information null it advances some family in 85% of 200 simulated draws, while Holm-Wilcoxon errs in 2%.
  - On the real events, a label-permutation placebo advances some family in 100% of draws (LADDER in 43%).
  - So the branch label alone is weak evidence. The paired tests and CIs are the informative part: they consistently rank LADDER (and SUBTRACT) above ASSOCIATE, but none survives Holm for NAMED.
- **The signature veto rarely removed Y.**
  - SUBTRACT-IN-CONTEXT is defined (≥ 20 non-Y attempts in some round) for only 4 of 33 Y. Those four:
    - T03 median_of_medians → quickselect
    - T05 brute_force → hash_map
    - T10 label_propagation → union_find
    - R6 exponential_search → binary_search
  - For 25 of 33 Y, Y still re-emerges in ≥ 20% of attempts after 3 rounds ("not carried by a small set of surface tokens").
  - The veto costs a mean 0.70 in pass rate, and 46% of final-round outputs are invalid.
  - Under the frozen rule an undefined SUBTRACT is scored as Uniform(S). Its tied top-1 is why almost every event counts as "disagreeing".
- **Exploratory, not pre-registered:** LADDER vs ASSOCIATE vs PROXIMITY on the 21 gated NAMED events where those three disagree. Wins are LADDER 8, ASSOCIATE 3, PROXIMITY 0. LADDER − ASSOCIATE gives p = 0.027, Holm (3 tests) 0.081.
- **C1-exposure** (the ban's modal survivor vs the veto's, where the associate differs) has only 2 qualifying events: T05 brute_force and T10 label_propagation. Both agree, giving CONFIRM 2/2. Both landings are the default, so this is snap-back, not a substitution test.
- **Template sensitivity** (W1–W4, 10 samples × 19 priority Y; descriptive, never in C1): mean avoidance is 0.93, 0.94, 0.96 and 0.81. W4 "{X} is not allowed here." is the weakest.

**Bottom line for the next round.** On Qwen3-8B, banning a just-shown algorithm sends the model back to its context-free default far more often than to its own stated "standard alternative". Nothing here supports a substitution account.

The ban-free signature veto cannot serve as the subtraction forecast for most Y: the algorithm survives the removal of its surface tokens.

Cross-model pooling with the Llama artifact is the pre-registered next step.

## What was run

1. **`setup`** (CPU)
   - Copies exp11's `bench/` to `bench_copy/` and verifies all 158 committed sha256 hashes plus exp11's chain.
   - Re-checks the labeller on 320 gold rows and references. It reproduces every `gate.json` value exactly, references 100%.
   - Recounts eligibility: 33 Y / 19 priority, as planned.
   - Writes COMMIT #0, the hashes of the inputs the bench commitment does not list.
2. **`forecasts`** (CPU)
   - Shown-program pools: scrub, then hidden tests, then relabel, then canonical-token dedup, then ≤ 600 tokens.
   - The distinctive n-gram g* by the frozen rule.
   - Allocation; PROXIMITY over 2,972 Zhang-Shasha pairs, with a token-distance sensitivity; LADDER; ASSOCIATE.
   - 775 rendered prompts, including the W1–W4 template prompts.
3. **`commit1`**: 11 unit tests pass; `analysis/` and `tests/` are tarred; COMMIT #1 is written. No generation happens before this.
4. **`stage1`** (GPU)
   - Engine: bf16, eager, prefix caching, KV cache 32,576 tokens.
   - T2 smoke tests:
     - vetoed n-gram in 0/20 veto samples vs 20/20 COPY samples;
     - planted `' heapq'` 1-gram veto: 0 vs 20;
     - an inert veto gives 20/20 identical outputs;
     - veto/COPY twins diverge exactly at the vetoed position in 20/20.
   - Batch A: COPY twin, veto round 1, and a bf16 baseline check that confirms every default (share 1.00; R6 0.95).
   - Veto rounds 2 and 3 for Y re-emerging ≥ 20%; SUBTRACT-IN-CONTEXT.
5. **`commit2`**: COMMIT #2 (SUBTRACT, veto rounds, copy twin, baseline check, template-arm declaration). Every ban sample is timestamped after it; this is checked.
6. **`stage2`** (GPU): NAMED and UNNAMED (3,300), then the W1–W4 arm (760). The arm ran because 28 of the 120 GPU-minutes had been used.
7. **`analyze`** / **`audit`**: the frozen C1 analysis and the reports below, then the independent re-derivation and placebos.

**Labelling.** The bench's gated labeller, unchanged: hidden tests, runtime-trace labeller, AST labeller, and the blind judge `google/gemini-2.5-flash-lite` on disagreements. Of 10,600 programs:

| source | programs |
|---|--:|
| runtime + AST agree | 7,478 |
| judge | 1,398 |
| runtime (AST unknown) | 147 |
| invalid (no code block) | 1,577, mostly from veto rounds |

Upstream 429 rate limits were retried until no judge fallback remained. OpenRouter spend was **USD 0.096** over 1,229 calls.

**Compute.** GPU time was about 1.0 GPU-hour on one NVIDIA L4:

| run | minutes |
|---|--:|
| stage 1 | 20 |
| stage 2 | 14.5 |
| aborted first stage-1 attempt | about 26 |

## Deviations

All are listed in `results/deviations.jsonl` and in `method_out.json` → `metadata.deviations`.

- **Hardware.** An NVIDIA L4 (23 GB), not an A4500. There is no C compiler, so vLLM runs eager without torch.compile. The plan's `./hf_cache` is replaced by the run's shared HF cache, and the vLLM caches live under `.cache/`.
- **Seeds.** Seeds use common random numbers across arms (`sha256("task:Y:p{i}:s{j}")`), as the plan's twin diagnostic requires. Plan step 0.12 hashed the arm into the seed.
- **T1(f).** The plan expected the counting rule to advance nothing in ≥ 95% of null draws. The measured rate is 85% false advances. The rule was kept as frozen; the unit test asserts the Holm-Wilcoxon level instead.
- **Stop-token bug.** Found and fixed in stage 1. The round-2 n-gram was first chosen on raw vLLM `token_ids`, which keep `<|im_end|>`, so that token was vetoed and outputs rambled to 1,024 tokens. The 750 affected samples are kept in `data/discarded_round2_stop_token_bug.jsonl`. Round 2 was redrawn with the plan's rule: canonical tokenisation of the fenced extracted code.
- **Single shown program.** Aggressive canonical-token deduplication leaves 11 of 33 Y with one shown program (flag `n_shown_lt5`).
- **Exploratory three-family analysis.** Added beside the frozen C1 and labelled as not pre-registered.

## Layout

| path | contents |
|---|---|
| `method.py` | CLI: `setup`, `forecasts`, `commit1`, `stage1`, `commit2`, `stage2`, `analyze`, `audit` |
| `exposure/core.py` | constants, paths, wordings, hashing, logging, timings |
| `exposure/forecasts.py` | bench copy + verification, labeller re-check, eligibility + ASSOCIATE, shown pools, n-grams, allocation, PROXIMITY, prompts |
| `exposure/ngram.py` | the frozen distinctive-n-gram rule |
| `exposure/astdist.py` | identifier-normalised ASTs and Zhang-Shasha distance |
| `exposure/veto.py` | `NgramVeto`, the persistent n-gram veto as a vLLM V1 `AdapterLogitsProcessor` |
| `exposure/sampling.py`, `exposure/stages.py` | engine, requests, smoke tests, staged sampling with concurrent labelling, veto iteration, stage 2 |
| `exposure/labels.py` | bench `label_one` + frozen combine rule + judge (cap USD 0.50) |
| `exposure/report.py`, `exposure/figures.py` | per-sample table, reports, exploratory analysis, figures, `method_out.json` |
| `analysis/c1.py`, `analysis/events.py` | **frozen** analysis code: scoring, advance rule, Holm-Wilcoxon, C1-exposure, placebos, event assembly (tarred in COMMIT #1) |
| `tests/test_unit.py` | T1 unit tests (a)–(g) plus the veto processor |
| `audit/rederive.py` | independent re-derivation of every event and headline number; sign-flip, constant-forecast and rotation placebos |
| `predictions/` | committed forecasts, shown programs, n-grams, co-veto lists, prompts, SUBTRACT, veto rounds, baseline check, `analysis_code.tar` |
| `commitments.log` | sha256 hash chain: COMMIT #0, #1 (10 files), #2 (5 files) |
| `data/generations.jsonl` | raw outputs (text, token ids, finish reason, veto mask) of all 10,600 samples |
| `data/samples.jsonl` | one row per program in the frozen schema (label, labeller source, passed, code, …) |
| `data/labels_raw.jsonl`, `data/labels_combined.jsonl` | labeller outputs before and after the judge |
| `data/judge_cache.jsonl` | judge answers (seeded from exp11) |
| `data/smoke_raw.jsonl`, `data/discarded_round2_stop_token_bug.jsonl` | smoke-test samples; the discarded round-2 samples |
| `results/c1_events.jsonl` | one row per (Y, NAMED / UNNAMED) event: forecasts, top-1s, log scores, gate, flags |
| `results/c1_summary.json` | frozen C1 (rule, tests, branch), sensitivities, C1-exposure, placebos, exploratory analysis, spend, GPU hours |
| `results/other_reports.json`, `results/arm_stats.json` | copy rates, snap-back, named-vs-unnamed, disguise, G-tests, veto diagnostics, template arm; per-(Y, arm) stats |
| `results/rederive.json` | audit output (0 mismatches) |
| `results/smoke_tests.json`, `results/labeller_recheck.json`, `results/bench_verification.json`, `results/deviations.jsonl`, `results/timings.json` | supporting records |
| `results/correct_other_programs.jsonl` | every correct program labelled 'other', for the next round's novelty audit |
| `figures/` | `landing_bars`, `forest_logscore_differences`, `copy_rate_vs_avoidance`, `default_share_by_arm` (PNG + PDF) |
| `method_out.json` (+ `full_` / `mini_` / `preview_`) | `exp_gen_sol_out`: `exposure_events` (66 events; `predict_subtract/ladder/associate/proximity` = the top-1s) and `exposure_samples` (10,600 programs) |
| `bench_copy/`, `inputs/` | verified copy of the exp11 bench; exp11 inputs used as cross-checks |
| `logs/` | per-step logs, including the aborted stage-1 attempt |

## How to run

See `reproducibility.md` for the full sequence. In short:

```bash
bash restore.sh
.venv/bin/python method.py setup && .venv/bin/python method.py forecasts && .venv/bin/python method.py commit1
.venv/bin/python method.py stage1 && .venv/bin/python method.py commit2 && .venv/bin/python method.py stage2
.venv/bin/python method.py analyze && .venv/bin/python method.py audit
```

`analyze` and `audit` run on the published data alone; they need neither a GPU nor exp11.

## Kept artifacts

Everything in this folder except the paths below is kept, on the run's volume and in the published repository. Every file is under 100 MB; the largest are `data/generations.jsonl` (about 20 MB) and `full_method_out.json` (14 MB).

The model weights are not stored here. They live in the Hugging Face cache.

## Restoring removed files

`.aii/manifest.yaml` marks these paths for deletion after the round:

| deleted path | restore command |
|---|---|
| `.venv/` (regenerable, about 14 GB) | `bash restore.sh`, or `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r requirements.txt` |
| `.cache/` (regenerable: vLLM / Triton / XDG caches) | recreated by the next GPU job: `.venv/bin/python method.py stage1` |
| `exposure/__pycache__/`, `analysis/__pycache__/`, `tests/__pycache__/`, `bench_copy/__pycache__/`, `bench_copy/common/__pycache__/` (regenerable bytecode) | recreated on import: `.venv/bin/python method.py --help` |

To fetch the model weights elsewhere:

```bash
hf download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218
```

## Upload exclusions

`.venv/`, `.cache/`, `__pycache__/` and the agent session files are not published.
