# Predicting which bans a new model obeys (held-out family: gemma-3-4b-it)

This experiment tests **Claim 3a** on a model family never run in this study. In iteration 3, a ban-free random-push screen on
Qwen3-8B separated the tasks whose coding ban the model obeys from those it ignores: in-sample BA 1.0, which
`src/tests_cpu.py` reproduces. This repository freezes the screen rule and runs it on `google/gemma-3-4b-it` (bf16). It
commits every per-task prediction by sha256 hash chain **before any ban prompt is built** (`commitments.log`, commit #2),
then samples 1,500 modal-ban programs and scores the predictions.

## Results

**Bottom line. C3a is INCONCLUSIVE on the held-out family.** Push-movability is related to ban compliance in the predicted
direction: Spearman ρ = 0.54, one-sided permutation p = 0.025. But it does not separate the tasks well enough:

- balanced accuracy is 0.74, with a 95% task-bootstrap CI of [0.40, 0.95];
- the 2×2 Fisher test is not significant: p = 0.24, or 0.71 after the conservative primary-family bound min(1, 3p).

The pre-registered rule requires all of BA ≥ 0.8, Fisher p < 0.05 and ρ ≥ 0.5. One task in the predicted direction is
carried by a labeller failure (T2, below). The novelty instruction, the "ask in words" rival, tracks compliance better
than the push screen (ρ = 0.77).

| Task (default D) | E_t (8 dirs) | Predicted | A_t (ban, N=100) | Observed | Ban composition (top) |
|---|---|---|---|---|---|
| T1 grid path (DFS) | 0.125 | obeys | 0.83 | obeys | BFS 83, DFS 17 |
| T2 weighted shortest path (Dijkstra) | 0.25 | obeys | 0.96 | obeys* | "Bellman-Ford/SPFA" 96 (*mostly array-Dijkstra, see below) |
| T03 k-th smallest (full sort) | 0 | fails | 0.63 | **obeys (miss)** | size-k heap 61, full sort 37 |
| T05 two-sum (hash map) | 0.25 | obeys | 0.59 | obeys | brute force 59, hash map 41 |
| T04 substring search (naive) | 0.25 | obeys | 0.19 | **fails (miss)** | naive 76, builtin 13, Rabin-Karp 6 |
| T10 connected components (DFS) | 0.125 | obeys | 0.00 | **fails (miss)** | DFS 100 |
| T11 LIS (patience + bisect) | 0.125 | obeys | 0.00 | **fails (miss)** | patience 100 |
| T06 find duplicate (hash set) | 0 | fails | 0.34 | fails | other 38, hash set 28, sort 21 |
| T08, R1, R3, T13, T14, R2 | 0 | fails | 0.00 | fails | default 87–100 |
| R6 first/last position (binary search; flagged) | 0 | fails | 0.00 | fails | binary search 99 |

Confusion matrix (predicted obey/fail × observed obey/fail): [[3, 3], [1, 8]]. TPR 0.75, TNR 0.73, Kendall τ-b 0.47.
The task-permutation placebo has mean BA 0.50, and P(placebo BA ≥ observed) = 0.13.
Leave-one-task-out BA ranges 0.70–0.86 and ρ ranges 0.41–0.67 (`results/c3a.json`). Every sensitivity stays INCONCLUSIVE:

| Variant | n | BA | Fisher p | ρ |
|---|---|---|---|---|
| without R2 / without R6 (flagged) | 14 | 0.73 | 0.24 | 0.52 |
| without T1/T2 | 13 | 0.61 | 1.00 | 0.31 |
| correct-only avoidance | 15 | 0.74 | 0.24 | 0.51 |
| ban N = 180 (with extra slots) | 15 | 0.74 | 0.24 | 0.54 |
| without the label-audit-flagged tasks (T2, T14) | 13 | 0.68 | 0.51 | 0.39 |
| compliance = drop in default share | 15 | 0.57 (DISCONFIRMED) | 1.00 | 0.39 |
| **post hoc**: T2 re-labelled by a second blind judge | 15 | 0.67 | 0.53 | 0.44 |
| **post hoc**: T2 re-labelled by the structural rule | 15 | 0.74 | 0.24 | 0.46 |

**The T2 labelling failure (post hoc, `results/posthoc_t2_relabel.json`).** The 60-program blind label audit agreed on
0.93 of programs overall but on only 1 of 4 for T2, and T2's runtime/AST disagreement rate is 27% (flag F7).

- *What the programs are.* Reading the T2 programs shows **array-based Dijkstra** (a linear minimum scan over unvisited nodes
  and a visited array, no heap).
- *How the labeller handled them.* The frozen exp8 suite labeller returns `unknown` or `bf_spfa` on this style; its gate set
  held heap Dijkstra. The inline judge then labelled the programs Bellman-Ford/SPFA.
- *Re-judging.* A second blind judge (gemini-2.5-flash) re-judged all 374 T2 programs labelled `bf_spfa` and calls 284 of them
  Dijkstra. These include all 219 that match a deterministic structural rule.
- *What it means for T2.* Under mechanism labels the ban "Do not use Dijkstra's algorithm" mostly makes Gemma **drop the heap
  but keep Dijkstra** (judge relabel: A_t 0.96 → 0.11). The escape directions on T2 partly move it to the same array form:
  E_t drops from 0.25 to 0.125 under both relabelings.
- *What it does not change.* The frozen labels stay primary, as committed, and the verdict is INCONCLUSIVE either way.
- *Lesson.* Labellers gated on one family need a style re-gate on a new one.

**Rival predictors (`results/rivals.json`; Spearman with A_t, sign-oriented).**

| Predictor | ρ |
|---|---|
| novelty-instruction off-default share | **0.77** |
| E_t (the screen) | 0.54 |
| PN α2 off-default share | 0.51 |
| PN α1 off-default share | 0.47 |
| `can_max` | 0.35 |
| T 1.3 off-default share | 0.34 |
| twin modal share | 0.24 |
| opening margin | −0.19 |

The paired task-bootstrap difference ρ(E_t) − ρ(novelty) is −0.24 [−0.82, 0.23], so the push screen is not better than asking
the model in words. The partial Spearman of E_t given the novelty share is 0.52. This fits the field's prior that a
prompting ceiling is the baseline to beat for activation-level interventions (AxBench: "prompting outperforms all existing
methods").

**C3b, landing forecasts (`results/c3b.json`).** There are 4 gated events (T1, T2, T03, T05; T2 is subject to the caveat above).

| Forecast | Mean log score | Top-1 hits |
|---|---|---|
| push-landing | **−0.11** | 4/4 |
| proximity | −1.20 | 3/4 |
| association | −1.77 | 2/4 |
| opening ladder | −3.66 | 0/4 |

The pre-registered contest needs ≥ 3 events where the forecast and association disagree. Push-landing beats association by
2.81 nats, but on only 2 disagreeing events (T03: size-k heap vs quickselect; T05: brute force vs two pointers), so **C3b is
INCONCLUSIVE** by rule.

**C1 replication (descriptive, `results/c1_prices.json`).** H5 is the best correct-only Hill-1 (depth 25) within 5 pass points
on the randomisation hull.

| Task | Plan noise (PN) | Temperature (1.3/1.6) | Novelty |
|---|---|---|---|
| T2 | 1.62 [1.37, 1.87] | 1.00 | 1.96 |
| T04 | 1.64 | 1.32 | 1.42 |
| T10 | 1.58 | 1.00 | 1.10 |
| T03 | 1.38 | 1.10 | 1.61 |
| T11 | 1.25 | 1.00 | 1.00 |

The twin's Hill-1 is 1.0 on these tasks (1.31 on T04). Temperature 1.3 and 1.6 almost never change the algorithm. The
novelty instruction diversifies some tasks at a large pass cost on others (T06 pass 0.08, T04 0.60).

**Novelty audit (`results/novelty_audit.json`).** The audit read all 34 correct 'other' programs from every arm with two blind
judges plus a tie-breaker. None was a novel algorithm (rule-of-three bound 0.088): 27 were degenerate (push arms) and 7 were
catalogue variants.

**Push unit (deviation D3; `results/unit_probe.json`, `results/unit_sensitivity.json`).** At spec positions, the 5 largest channels carry
99% of ‖h‖² in Gemma, against 40% in Qwen3-8B. The committed unit r_Q·‖h‖ therefore erased the task in a 24-row calibration
probe, so the plan's outlier-excluded unit was used instead. After the bans, the measured Gemma ban displacement was 1.29× the
outlier-excluded unit (0.92–2.1× by block) and 0.13–0.18× the committed unit. The adopted unit is therefore on the ban's own
scale, as the design intended.

**Other observations.**
- *W4 is the weakest template.* Its avoidance is 0.15 on T1 vs 1.0 on the other templates, and 0.05 on T03.
- *Ironic rebound on R6.* The twin writes a linear scan 86% of the time, but the ban "Do not use a hand-written binary search"
  makes it write binary search 99% of the time.
- *CRN flips.* On T2, 48 of 50 twin slots flip from the default to a survivor under the ban (`results/crn_flips.json`).

**Checks.**
- *Inputs and labellers.* All 13 bench task directories match `commitment.json`. All 13 bench labellers reproduce `gate.json`
  exactly, with 100% on the references. The exp8 suite recovers 22/22 references, but its gold accuracy is 0.80 against the
  gate's 0.84 (D7).
- *Iteration-3 screen.* It reproduces all 6 stated escape counts.
- *GPU tests.* U1–U4 pass: alpha-0 rows are bit-identical, pre-band blocks are identical, the realised push along u is within
  0.02%, and CRN slots are identical.
- *Qwen hook port.* It reproduces exp17's realised displacements (median 2.8% difference).
- *Pre-registration integrity.* The grep audit found 0 ban frames in 460 fed prompts. The hash chain verifies (3 commits).
- *Independent re-derivation.* `audit/rederive.py` reads only the raw samples, the commitment and the judge cache. It
  re-derives, with 0 mismatches: every E_t and A_t, BA, Fisher p, ρ and its permutation p, Kendall τ, the five rival ρs, all 16
  C3b log scores, and the post-hoc T2 numbers. Its placebos fail as required: on shuffled outcomes Fisher rejects 1.7% and
  Spearman 4.9% (mean ρ −0.01); a random predictor is rejected 6.7%; the constant predictor gives BA 0.5 and p = 1. The C1 hull
  values and the bootstrap intervals are Monte-Carlo and were not re-derived by a second code path.
- *Cost.* Generation took 1.28 GPU-hours on an RTX 2000 Ada. OpenRouter spend was USD 0.28.

## Deviations (full text in `results/deviations.json`)

| | Deviation |
|---|---|
| D1 | The card is a 16 GB RTX 2000 Ada, not an A4500. Hence gemma-3-4b-it, B = 36, and caps of 640 from the pilot rule. |
| D2 | The Qwen3-8B session ran with CPU offload, and the optional Qwen generation control was dropped. |
| D3 | **The outlier-excluded push unit** (decided before commit #1 and before any ban). |
| D4 | Pilot rows are uncoupled. |
| D5 | D must be a catalogue mode (R6 flagged). |
| D6 | The 'can', association and novelty arms run on the same sampler, in multi-prompt batches. |
| D7 | The exp8 suite gold accuracy does not reproduce the gate exactly. |
| D8 | The ban sensitivity uses N = 180, not 200. |
| D9 | Bonferroni bound instead of a cross-artifact Holm correction. |
| D10–D11 | Proximity pairs and C1 bootstrap replicates are capped. |
| D12 | Handling of disputed labels. |
| Added | The optional T 1.6 cell. |
| Added, post hoc | The T2 re-audit. |
## What was done

This is a held-out-family test. The question is whether a **ban-free push screen** predicts which coding bans a model will obey. The model is
`google/gemma-3-4b-it`, a family never run in this study. It ran in bf16 on one 16 GB RTX 2000 Ada.

**The method (the screen).** For each of the 15 tasks:
- The model writes 50 programs for the token-matched **neutral twin** prompt (the default composition).
- In every CRN batch, 8 fixed isotropic random directions (PCG64 seeds 9001–9008) at α ∈ {1, 2} are added to the task-spec
  token states of blocks 11–22 (the middle third of 34) during the prefill.
- The edit is displacement-targeted: the component along the direction is set to α·n in every band block, so pushes do not compound.
- n is the ban-free unit from Qwen3-8B, outlier-excluded (deviation D3): `n[l,p] = r_Q,ox(d_l)·‖h_ox[l,p]‖`.
- A direction-α **escapes** if all of these hold:
  - stage 1 (N = 10): off-default share − p0 ≥ 0.20 and pass ≥ 0.8 × the twin's pass;
  - after a 20-sample top-up (N = 30): the same two criteria hold, and an exact binomial `P(X ≥ k | 30, max(p0, 0.01)) < 0.05`.
- Intervention class: a fixed (not learned) additive edit of block outputs. It acts on the task-spec positions only, in the
  prompt prefill only, along isotropic unit directions, with a displacement-targeted dose; decoding is never edited.
- `E_t` = share of the 8 directions that escape (max over α). **MOVABLE** = `E_t > 0`, which predicts that the model **obeys** a ban
  of its default (catalogue-only avoidance `A_t ≥ 0.5`).

**Baselines and rivals.** These run in the same engine, on the same twin prompt, under the same common-random-number (CRN) uniforms:
- the un-pushed twin (the zero dose);
- fresh-direction plan noise (PN) at α 1 and 2;
- temperature 1.3 (plus an optional T 1.6 cell on the movable tasks);
- the novelty instruction (the prompting ceiling);
- forced "can" attempts;
- the twin's modal share (how collapsed the default is);
- the teacher-forced opening-ladder margin.

**Landing forecasts (C3b).** Push-landing, opening ladder, association (the model names "the standard alternative"), and AST proximity.

**Pre-registration.** Every prediction, together with the frozen analysis code, is sha256 hash-chained in `commitments.log` (commit #2)
before any ban prompt is built. A grep audit (`results/grep_audit.json`) verifies that no fed prompt contains a ban frame.
Then 1,500 modal-ban programs were sampled (5 templates × 20 CRN slots × 15 tasks, plus flagged extras) and labelled with the frozen
labellers.

## Layout

| Path | What it is |
|---|---|
| `method.py` | pipeline driver (stages in order; `--from <stage>` resumes) |
| `reproducibility.md`, `restore.sh` | exact reproduction steps (what was actually run) and environment/model restore script |
| `src/cfg.py` | constants, paths, utilities |
| `src/stage_inputs.py` | STEP 1: input staging + sha256, bench check, labeller re-check, dependency extraction |
| `src/screen.py` | iteration-3 Qwen screen recomputed with this artifact's escape rule (`results/screen.json`) |
| `src/qwen_ratio.py` | STEP 3: Qwen3-8B ban-to-residual ratios r_Q / r_Q,ox and the hook positive control |
| `src/prompts_gemma.py` | STEP 4: Gemma prompts, token-length-matched twins, tokenizer-only ban lengths, grep audit |
| `src/engine_gemma.py`, `src/push.py`, `src/units.py` | STEP 5: bf16 engine, CRN inverse-CDF sampler, displacement-targeted push, push unit |
| `src/gpu_tests.py`, `src/unit_probe.py`, `src/tests_cpu.py` | GPU tests U1–U4/U6, unit calibration probe, CPU tests T1–T6 |
| `src/banfree.py`, `src/runner.py` | STEPs 6–7: pilot, commit #1, Phase A–D, opening ladder, T 1.6 cell |
| `src/label_worker.py` | frozen bench / exp8-suite labellers (runtime primary, AST second, blind judge on disagreement) |
| `src/predictors.py`, `src/prox.py` | escape screen, E_t, rivals, four landing forecasts, Zhang–Shasha proximity |
| `src/commit2.py`, `src/commit.py` | STEP 8: commit #2 (pre-ban predictions + frozen analysis) and the hash chain |
| `src/bans.py` | STEP 9: modal bans and the ban-derived unit |
| `src/judge_audit.py` | STEP 10: label audit, disagreement rates, novelty audit |
| `src/analysis_c3.py` → `predictions/analysis_c3.py` | the FROZEN analysis (hash-committed before the bans) |
| `src/final_analysis.py`, `src/figures.py`, `src/outputs.py`, `src/bookkeeping.py` | STEPs 11–12 |
| `audit/rederive.py` | independent re-derivation of the headline numbers from `data/samples.jsonl` |
| `src/posthoc_t2.py` | POST HOC: second-judge + structural re-audit of T2 `bf_spfa` labels, C3a re-run |
| `src/digest.py`, `src/wait_labels.py` | prints the headline numbers; blocks a stage until its rows are labelled |
| `predictions/` | `commit1.json`, `commit_preban.json`, frozen `analysis_c3.py` |
| `commitments.log` | sha256 hash chain (commits #1, #2, #3) |
| `data/raw_*.jsonl` | every generated row (text + token ids + realised displacement) |
| `data/labels.jsonl`, `data/samples.jsonl` | labels; merged per-sample table (schema of STEP 7) |
| `data/prompts_fed.jsonl` | every model-fed prompt (grep-audit registry) |
| `results/*.json` | all analyses (see the Results section) |
| `figures/` | fig1–fig6 (PDF + PNG + spec JSON) |
| `inputs/` | sha256-verified copies of every upstream input (`inputs/SHA256SUMS`) |
| `method_out.json` (+ `full_`, `mini_`, `preview_`) | exp_gen_sol_out output |

## How to run

Full step-by-step instructions, with what was actually run, the runtimes and the expected numbers, are in
`reproducibility.md`.

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
# paths.local.json maps upstream artifact names to their workspaces (needed only by stage 'inputs')
.venv/bin/python method.py                 # full pipeline (about 2 GPU-hours on a 16 GB RTX 2000 Ada)
.venv/bin/python method.py --from analysis # re-analyse the stored samples only (CPU)
.venv/bin/python audit/rederive.py         # independent re-derivation of the headline numbers
```

Environment: Python 3.12, torch 2.8.0+cu128, transformers 4.57.6 (`pyproject.toml` pins every package). The HF cache is the run's
shared cache. The model weights are `google/gemma-3-4b-it@093f9f38` (the LFS sha256 of both safetensors files is checked in
`predictions/commit1.json`).

## Restoring removed files

Every `delete` entry of `.aii/manifest.yaml` and the command that brings it back:

| Removed path | Restore with |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` (or `./restore.sh`) |
| `src/__pycache__/` | `.venv/bin/python -m compileall src` (also recreated by any pipeline run) |
| `predictions/__pycache__/` | `.venv/bin/python -m compileall predictions` (also recreated when the frozen analysis is imported) |
| `inputs/exp11/bench/__pycache__/` | `.venv/bin/python -m compileall inputs/exp11/bench` (also recreated by any labelling run) |
| `inputs/exp11/bench/common/__pycache__/` | `.venv/bin/python -m compileall inputs/exp11/bench/common` |
| `inputs/exp8/suite/__pycache__/` | `.venv/bin/python -m compileall inputs/exp8/suite` |
| `inputs/exp8/suite/tasks/__pycache__/` | `.venv/bin/python -m compileall inputs/exp8/suite/tasks` |
| `inputs/exp8/suite/labeller/__pycache__/` | `.venv/bin/python -m compileall inputs/exp8/suite/labeller` |
| model weights (shared Hugging Face cache, outside this folder) | `huggingface-cli download google/gemma-3-4b-it --revision 093f9f388b31de276ce2de164bdc2081324b9767` and `huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218` (both in `./restore.sh`) |

`data/` and `inputs/` are kept: they hold every generated program and the frozen inputs. They stay on the run's volume and in the
published repository; no file in them exceeds 100 MB.
