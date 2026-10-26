# Reading and steering Gemma's BFS-or-DFS choice with Gemma Scope 2 SAEs (claim S)

**Question.** Asked for one and the same grid-path task (T1), `google/gemma-3-4b-it` writes depth-first search (DFS)
about 70% of the time and breadth-first search (BFS) about 30%. Where in the generation does that choice fork, can
the choice be read from the model's internals beyond what the visible text already says, and do the model's own
sparse autoencoders (Gemma Scope 2, trained on gemma-3-4b-it) read and steer it better than plain baselines
(difference in means (DiM), raw residual, raw dimensions, random features, isotropic directions, prompting)?

**Short answer (one model, one decisive task: a screen for the next iteration, not a general claim).**

1. **The plan is a single-token fork, about 138 tokens before any algorithm-identifying code.** All programs open
   with the same 32 tokens (```` ```python ````, `def solve(grid, start, goal):`, `rows = len(grid)`,
   `cols = len(grid[0])`, indent). The next token decides: ` visited` leads to DFS (P(BFS) = 0.011, n = 1,409), while
   a blank line, `if`, `queue` or `q` lead to BFS (P(BFS) 0.95-1.00). Prefix resampling (3,712 continuations) finds a
   significant change point with a rise of at least 0.4 on 12/12 BFS base paths, at prefix lengths 16-36.
2. **It is readable beyond the text, at the fork position, but not specifically through SAEs and not before
   generation starts.** A Lasso on layer-29 SAE codes at the fork position predicts the fork log-odds y_v of 120
   neutral prompt variants (held-out noun R² 0.66) far better than a text-only control (0.18): ΔR² = 0.49
   [0.26, 0.65], p = 0.003. That meets the pre-registered bar, and the SAE model beats DiM (0.34) and raw PCA-16 (0.56).
   But a tuned ridge on the *raw* layer-29 residual (not pre-registered) reaches 0.72, and ridge on the same SAE codes
   reaches only ≤ 0.09. So the information is in the residual, and the SAE advantage depends on the estimator. At the
   task-specification positions (before any response token), SAE codes (0.18) do no better than text (0.18).
3. **The SAE features steer the fork, but DiM is 2.3-3.1x stronger per unit norm, and every fork-site edit breaks
   correctness.** At the fork position (layer 22, 120 variants), matched-norm edits move y by: SAE clamp (top-20 input
   features) +1.78 nats, DiM +4.04, random features +0.51, isotropic +0.12. In generation (N = 50, CRN-paired):
   - Baseline twin: 13/50 programs are BFS. The SAE clamp gives 30/50 (k = 20) and 36/50 (k = 50). DiM at the same
     norm gives 46/50 and 49/50; random features give 21/50.
   - Pass rates collapse: 0.84 for the twin vs 0.58 (SAE k20) and 0.32 (DiM k20).
   - So the pre-registered metric (target class *and* passing hidden tests) shows no significant effect anywhere
     (exact McNemar, Holm), and there is **no feature claim** (AxBench-style: SAE features did not beat DiM).
   - **Caveat on that rule.** The pre-registered feature rule (FEAT target-correct ≥ DiM, with pass ≥ 0.8 x twin
     pass) is *also met by random features* at k = 50 (RANDF 9 ≥ DiM 7, pass 0.76). Because DiM breaks the programs,
     the rule cannot discriminate here (placebo in `results/rederive.json`).
   - The informative comparison is the plan shift itself (attempted BFS, secondary and descriptive, exact McNemar on
     CRN pairs):
     - SAE clamp vs twin: 30 vs 13 (p = 1.5e-5) at k = 20; 36 vs 13 (p = 2.4e-7) at k = 50.
     - SAE vs random features: 36 vs 21 (p = 6.1e-5).
     - DiM vs SAE at matched norm: 46 vs 30 (p = 3.1e-5).
   - At matched *logit* effect (the matched-pass rule's extra DiM cells, λ = 0.45 and 0.32), DiM and the SAE clamp
     shift the plan equally (32 vs 30, p = 0.50; 34 vs 36, p = 0.63). DiM keeps slightly more programs correct
     (13 vs 9, 14 vs 10).
   - Edits at the task-specification positions do nothing (12-19 BFS vs 13).
   - Toward DFS, both work cleanly (SAE 47/50 DFS, DiM 50/50, vs 37 for the twin; pass 0.98-1.00).
4. **A low-rank DAS subspace at the fork carries the choice, but forcing it breaks the program.** Swapping in the
   forced-BFS source state moves held-out y by +8.8 nats at rank 1 and +9.8 at rank 4 (random subspaces: -0.08 to
   +0.05). In generation, the rank-4 interchange makes 50/50 programs BFS, but 0/50 pass. This is consistent with the
   DiM result: the plan is essentially one direction at one position, and pushing it hard costs correctness.
5. **Banning the five most common algorithms does not make the model creative; it makes it write the banned
   algorithm.** Under the TOP5 ban (BFS, DFS, IDDFS, A*, greedy best-first), 50/50 programs still use banned modes
   (avoidance 0.00, like Qwen in iteration 2). BFS rises from 10/50 to 41/50 (McNemar 32 vs 1, p = 7.9e-9), and the
   pass rate drops from 0.86 to 0.38. In activation space the TOP5 prompt states sit next to the banned A*/greedy
   cluster (landing rank 1 of 15 possible banned/survivor splits in three of four spaces).

Every number above is re-derived in `results/rederive.json` and `results/rederive_headlines.json` (see the audit
section), and detailed in `method_out.json` (metadata) and `results/*.json`.

## What was run (plan stages S0-S13)

| Stage | What | Status / key output |
|---|---|---|
| S0 | stage inputs, sha256 checks (384/384 copies, bench 25/25), hardware, instrument ids, **commit #0** | `results/s0_inputs.json`, `predictions/` |
| S1 | U1 CRN determinism, U2 identity hooks (zero edit, error-preserving SAE splice, clamp-to-own-value: bit-identical) | `results/tests_gpu_s1.json` (all pass) |
| S3 | natural splits N = 200 for T1, T04, R6 (+ engine check vs iteration 5) | `results/natural_split.json`, `results/engine_check.json` |
| S2 | instrument gate (FVE, L0, dead share, spliced-in ΔCE, loss recovered) vs wikitext + LeetCode reference | `results/gate.json`: layers 22, 29 pass; 9, 17 fail (descriptive) |
| S4 | fork: partial labeller (U8 200/200), 24 base paths x 16 prefixes x 8 + refinement, change points | `results/fork.json`, `figures/fork_trajectories.*` |
| S5 | 120 neutral variants (y_v + states), 115 contrast prompts, sampling validation (60 x 10) | `cache/states/`, `results/sampling_validation.json` |
| S6 | (a) within-prompt decodability vs visible-prefix text; (b) cross-prompt readout; (c) contrast separability | `results/decodability_within.json`, `readout.json`, `contrast_separability.json` |
| S7 | input-score and output-score feature sets, DiM/RANDF/ISO, layer rule, **commit #1** | `results/selection.json`, `predictions/commit1.json` |
| S8 | logit dose-response sweep (11,280 rows) + 15 generation cells + twin + 2 matched-pass DiM cells | `results/clamps.json`, `logit_sweep_summary.json`, `figures/clamp_cells.*`, `dose_response.*` |
| S9 | DAS rank 1/2/4 at the fork + generation N = 50 for the best k | `results/das.json` |
| S10 | attribution graph **dropped first** (drop order); fallback = first-order attribution patching on resid_post SAEs, top-5 nodes validated by real-model ablation/steering + joint cells (N = 30) | `results/attribution.json` |
| S11 | TOP5 prohibition + geometry (PCA, Isomap k = 10, classical MDS) in raw and SAE coordinates | `results/top5.json`, `results/geometry.json`, `figures/geometry_*`, `generated_panel_L22.*` |
| S12 | T04 / R6 descriptive (splits, decodability at generated position 32) | in `natural_split.json`, `decodability_within.json` |
| S13 | novelty audit of every correct 'other' program + style re-gate (OpenRouter) | `results/novelty_audit.json`, `results/regate.json` |

Pre-registration: `commitments.log` is a sha256 hash chain over `predictions/commit0.json` (before any sample) and
`predictions/commit1.json` (before any clamp generation); `audit/verify_chain.py` checks it and the ordering.

## Results in more detail

- **Natural splits (N = 200 each).**
  - T1: DFS 139 (69.5%, Wilson 62.8-75.5%) / BFS 61. Correct: DFS 134, BFS 38. Pass rate 0.86. Default DFS (0.78 of
    correct programs).
  - T04: naive 173 / builtin 27. R6: linear scan 170 / binary search 29 / other 1. Both pass 1.00.
  - Engine check vs iteration 5: T1 label agreement 0.94 (54% byte-identical programs), T04 1.00. The 6% difference
    is kernel and batch-shape sensitivity (different GPU and batch).
- **Gate.** ΔCE on the task corpus is small in absolute terms (0.017-0.097 nats/token) because the model's own
  programs have very low loss. Layer 9 fails the ΔCE ratio, and layer 17 fails the FVU ratio by 0.0001. Generic-text
  L0 is 57-64 (the medium band is quoted as 30-60) and FVE 0.71-0.97.
- **Within-prompt decodability (S6a).**
  - At the read position before the first algorithm-identifying token, every method, the text control included, is
    at balanced accuracy 1.00. The text already shows the algorithm, so there is no SAE advantage.
  - At the fork, 185/200 samples share their prefix with an other-class sample, so the test is undefined by
    construction, as pre-registered.
  - The identical-prefix share up to the fork is 0.73-0.85 per template.
- **Cross-prompt readout (S6b).** y_v has mean -0.92 nats and SD 0.67, with a within-template SD of 0.58, so nouns
  matter. The sampled BFS share tracks y_v: Spearman 0.65 over 60 variants x 10 samples.
- **Feature selection.** Input-score (forced contrast) and output-score (attribution) sets share 2 of 20 latents at
  the fork. Output-score clamps (k = 20) move y +1.35 and BFS to 25/50, with pass rate 0.78.
- **Attribution fallback (S10, first-order, not a graph).**
  - Ablating the two strongest nodes moves y by 4.0 and 6.3 nats, against 0.8 and 0.4 for random active latents at
    matched contribution norm. Two of the remaining three beat random; layer-22 latent 142 does not.
  - Jointly ablating the top-5 nodes turns 29/30 programs into BFS, but none pass. Joint steering gives 19/30 BFS
    (12 correct).
- **DAS (S9).** Held-out Δy is +8.8, +9.5 and +9.8 for k = 1, 2, 4, against about 0 for random subspaces.
  - The "shuffled-source" control is **not informative** as built: every source is a forced-BFS prompt, so shuffling
    templates still imports a BFS state.
  - Generation with the k = 4 subspace: 50/50 BFS, 0/50 pass.
- **Prompting ceiling.** Forced BFS gives 50/50 BFS (38 correct), forced DFS 50/50 DFS (45 correct). A single-name
  ban leaves the banned algorithm in 11/50 (ban BFS) and 8/50 (ban DFS) programs.
- **Contrast separability (S6c).** Leave-one-out nearest-class-mean accuracy:
  - forced-BFS vs forced-DFS prompts: 1.00 at every layer, SAE and raw alike;
  - ban-DFS vs ban-BFS: 0.7-1.0.
  - Top latents are listed with their ids for Neuronpedia lookup; the labels are descriptive only.
- **Novelty audit (S13).**
  - 1 of 1,450 correct programs was labelled 'other' (an R6 program). Two of three judges call it a catalogue
    variant, so **0 novel algorithms** (rule-of-three upper bound 3/1450 = 0.0021).
  - The style re-gate agrees 30/30: both blind judges match the labeller on 30 T1 programs.
  - Total OpenRouter spend: USD 0.034.

## Audit (independent re-derivation)

- `audit/verify_chain.py`: the hash chain is intact. The first S3 row comes after commit #0, and the first clamp row
  after commit #1.
- `audit/rederive.py` (standard library only) re-derives 32 headline quantities from the raw rows with 0 mismatches:
  the S3/contrast compositions, the fork token table, every primary McNemar test and 5 secondary attempted-class
  tests. Its placebos:
  - Shuffled-class decodability: 0.43, at chance, as required.
  - RANDF-as-FEAT: *meets* the feature rule at both sites. The rule is therefore non-discriminating (see above).
- `audit/rederive_headlines.py`, through different code paths:
  - Sampling-validation Spearman 0.654 (hand-written ranks; shuffled-y placebo 95th percentile 0.22).
  - Dose-response means from raw sweep rows (DiM/FEAT = 2.27 at k = 20; isotropic placebo ≈ 0).
  - TOP5 McNemar 32 vs 1 (placebo p = 1.0).
  - The readout with a different estimator. Standardized numpy ridge on the same SAE codes gives R² 0.15 vs 0.09 for
    a template + noun-norm control (permuted-y placebo far below), and unstandardized ridge on SAE codes gives ≤ 0.09.
    Ridge on the raw layer-29 fork residual gives 0.70-0.72. So the *existence* of a fork-position readout beyond text
    is robust, but the *SAE-specific* advantage of the pre-registered Lasso is not.

## Layout

| Path | What |
|---|---|
| `method.py` | entry point; one function per stage (`--stage s0, gen1, label, fork, tfgate, variants, select, clamps, das, attrib, analysis, outputs`) |
| `src/cfg.py` | constants, paths, CRN seeds, design parameters |
| `src/engine.py`, `src/push.py`, `src/prompts.py`, `src/label_worker.py`, `src/regate_rules.py`, `src/units.py` | iteration-5 engine, hooks, prompt builders and labellers (reused; `engine.decode` extended with pad rows and a partial-labeller stop) |
| `src/gen.py` | CRN generation runner (fixed batch shape, live per-row edits) |
| `src/sae.py` | Gemma Scope 2 JumpReLU SAE loader (direct from `params.safetensors`) |
| `src/fork.py` | partial-code labeller, binomial change points, prefix bookkeeping |
| `src/clamp.py` | feature selection and the FEAT / DiM / RANDF / ISO edits at matched outlier-excluded norm |
| `src/analysis_S.py`, `src/figures_S.py`, `src/novelty.py`, `src/outputs.py` | analyses, figures, S13 audits, `method_out.json` builder |
| `src/extract_dep.py` | extracts the used parts of the dependency `art_j3Rm_lr2nzR6` into `inputs/dep_extract/` |
| `src/commit.py`, `audit/verify_chain.py`, `audit/rederive.py`, `audit/rederive_headlines.py` | hash-chained commitments and the independent audits |
| `src/chain_gpu*.sh` | the shell chains that ran the GPU stages back to back |
| `inputs/` | verified copies of every upstream input (`MANIFEST.sha256`) |
| `data/` | raw generations (`raw_*.jsonl`), labels, fork continuations, sampling validation |
| `results/` | every analysis result (JSON); `deviations.json` lists all deviations |
| `figures/` | PNG + PDF figures (geometry in actual activation coordinates) |
| `predictions/`, `commitments.log` | commit #0, commit #1, hardware and instrument ids |
| `cache/states/` | residual states and SAE selections (about 1.6 GB; **kept on the run's volume, not in the published repository**) |
| `method_out.json`, `full_/mini_/preview_method_out.json` | exp_gen_sol_out output: datasets `natural_split` (600), `engine_check` (100), `fork_resampling` (384), `prompt_variants` (120), `clamp_cells` (50 CRN slots x every cell as `predict_*`), `contrast_arms` (50 slots: forced, ban, TOP5, TOP5 twin); metadata = every results file |
| `logs/` | stage logs, timing, OpenRouter spend |

## How to run

See `reproducibility.md` for the exact commands, order, hardware and timings. In short:

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
for st in s0 gen1 fork tfgate variants select clamps das attrib; do .venv/bin/python method.py --stage $st; done
.venv/bin/python method.py --stage label   # labels every raw row (run alongside or after the generation stages)
.venv/bin/python method.py --stage analysis && .venv/bin/python method.py --stage outputs
python3 audit/verify_chain.py && python3 audit/rederive.py && .venv/bin/python audit/rederive_headlines.py
```

## Deviations (full list in `results/deviations.json`)

- **D1 GPU.** RTX 2000 Ada, 16 GB, not an A4500. The batch shape is B = 20. A host slowdown made decoding 10x slower
  for about 55 minutes of the clamp stage. Results are unaffected.
- **D2 Fork index rule.** The first-coded median rule landed on a deterministic indentation token. Before commit #1,
  it was replaced by the refined index with maximal token-class mutual information (index 32, also the modal one).
- **D3 Forced paraphrases.** The 10 forced paraphrases come from exp9's frozen forced templates.
- **D4 S10.** circuit-tracer was not installed (drop order). The first-order fallback is labelled as such.
- **D5 Batching.** Contrast arms and sampling validation used multi-prompt batches (CRN-keyed, not bit-coupled).
- **D6 Partial labeller.** Fork continuations and sampling validation use the partial-code labeller (U8 = 1.00).
- **Other.**
  - S6a permutation nulls use 200 permutations (100 for T04/R6), and S6b uses 300 (not 1,000), with C fixed inside
    the permutations.
  - The S8 per-sample displacement is logged at the prefill (spec mean and fork position, blocks 11-33), not at
    generated tokens 1-32.
  - The S11 generated-position panel shows natural samples only; there is no clamp overlay.
  - U4 (clamp readback) and U5 (matched-norm realisation) were not run as separate unit tests. The matched norm is
    imposed by construction in `src/clamp.py`.
  - The T04 fork and the T04/R6 cross-prompt readout were not run (drop order).
  - SAE-site layer 29 at SPEC gave non-finite y in the layer-rule probe. Layer 22 was chosen for both sites, and
    non-finite sweep rows are counted (`n_nonfinite`).

## Restoring removed files

`.aii/manifest.yaml` marks these for deletion after the round; all are regenerable:

- `.venv/`: `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml`
- `__pycache__/` folders (`__pycache__/`, `src/__pycache__/`, `inputs/exp8/suite/**/__pycache__/`,
  `inputs/exp11/bench/**/__pycache__/`): created automatically by any Python run.
- Model weights and SAEs are not stored here (a shared HF cache outside this folder was used). Download them with
  `huggingface-cli download google/gemma-3-4b-it --revision 093f9f388b31de276ce2de164bdc2081324b9767` and
  `huggingface-cli download google/gemma-scope-2-4b-it --revision 3e94b68be95290aada5b7525cf431d3040f81bb1 --include "resid_post/layer_*_width_16k_l0_medium/*"`;
  the code downloads them on first use.

`cache/states/` is **kept** on the run's volume (it is not published because its files exceed the repository size
limit). To rebuild it, run `method.py --stage tfgate`, then `--stage variants`, then `--stage select` (about 30
GPU-minutes). `das` re-creates the DAS subspaces.
