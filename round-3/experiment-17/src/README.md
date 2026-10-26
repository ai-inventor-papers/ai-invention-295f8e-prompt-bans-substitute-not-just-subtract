# Where in Qwen3-8B a coding ban lives (iteration 3, internal-locus experiment)

Qwen3-8B (pinned revision `b968826d…`, thinking off, T = 1.0) is told **not** to use the algorithm it would
normally write ("Do not use Dijkstra's algorithm…"). This repository asks where that prohibition lives inside
the model, using four tests, each run beside its baseline under common random numbers (CRN):

| Claim | What ran | Baseline / control beside it |
|---|---|---|
| **C2d**: an X-free prohibition direction | `v` = leave-one-task-out mean (13 other tasks × W1–W5) of the ban-minus-neutral-twin displacement at the task-spec positions, blocks 12–23. **ADD** writes `v` into the neutral twin's prefill (displacement-targeted, α ∈ {1, 2} [+0.5]); **SUBTRACT** projects `v` out of the ban prompt's prefill | 3 norm-matched random directions at α 1 and 2 (same blocks, positions, norms); the neutral twin and the named ban (prompting ceiling), N = 100; SUB_affine (twin-anchored) and a SUB_rand (random edit of SUB_plain's norm) on T1/T2 |
| **C2e**: a within-ban locus | L2 decoders of default-vs-other on residual states at generated tokens 1–8 and 16, at R and the task-spec mean, at blocks 8–28 | R (template-only), three written-text controls of matched or greater capacity (Ta token one-hots, Tb layer-0 embeddings PCA-64, Tc exact prefix match), within-template permutation null with a layer-max statistic |
| **C2f**: three ban-attending heads | mean-ablation of L21H17, L26H21, L26H25 at generated positions under the full ban | 3 layer-matched random head sets; the unablated ban on the same CRN slots |
| **0g**: Qwen-Scope SAE transfer | fraction of CE recovered vs zero-ablation (FR_zero) per model on its own outputs, 2×2 (model × text) | FR_mean, KL, dCE, FVU, L0, preservation of the ban-minus-twin displacement; 5a benchmarks latents against DiM |

Tasks: the two path tasks **T1** (grid path, default BFS) and **T2** (weighted shortest path, default Dijkstra),
and the bench tasks **T03** (k-th smallest, full sort), **T04** (substring search, naive window), **T06** (find
duplicate, hash set), **T05** (two-sum, hash map). The direction is built from all 14 tasks (12 bench + T1/T2).

## Results (headline)

**Bottom line.** The ban is not carried by a task-general linear prohibition direction at the task-spec positions.
Writing the shared ban displacement into a neutral prompt fails the frozen test on every gated task. Where it moves
behaviour at all (T2, T03), some random pushes of the same norm do as well (T2), or it lands on a different algorithm
from the ban (T03). Removing the displacement from a ban prompt does not restore the default (C2d disconfirmed). Within a ban, which algorithm the
model writes is not readable from the residual stream ahead of the written text (no C2e locus). It is set by the
prompt template, which a template-only decoder already captures, or by tokens sampled after the first 16. The three
ban-attending heads are not special: random heads in the same layers have nearly the same effect (C2f not
supported). The Qwen-Scope SAEs pass the frozen (lenient) transfer rule but keep only about a third of the ban
displacement's direction (0g).

All decisions use the rules hash-committed before sampling (`predictions/commit1.json`, `commitments.log`).
Shares are over attempted programs (invalid/disputed excluded); CIs are Wilson (shares) or slot bootstraps (paired
differences). 5,500 CRN samples were generated for the frozen design (plus 1,800 exploratory), all labelled; blind-judge spend USD 0.22 (cap raised to 0.40, deviation 5).

**Engine checks.** All GPU unit tests pass (`results/unit_tests_gpu.json`): CRN determinism, ADD with α = 0
reproduces the neutral twin token for token, the realised displacement along `v` equals α·n within 0.35%,
SUB_plain leaves |h·v̂| < 0.1% of ‖h‖, head-ablation identity, and the position convention (U3). U1b: decode with
20 rows is row-position independent (identical uniforms in different rows give identical tokens), so the CRN coupling
of every arm is exact; batch-1 teacher forcing is bit-exact (`results/unit_tests_u1b.json`). U7 reproduces exp8 on
T2 under FP8 (ban 2/20 Dijkstra, twin 20/20). T3 (leave-one-task-out maths) and T4 (planted-signal decoder test:
planted signal BA 1.0 vs null 0.59; a template-only signal does not beat the within-template null; IRLS = sklearn to
1e-5) pass (`results/test_direction_maths.json`, `results/test_c2e_synthetic.json`). Bench inputs match `bench/commitment.json` (0 mismatches);
bench labellers recover 100% of references and reproduce `gate.json` gold agreement exactly; the exp8 suite
recovers 22/22 references.

**The direction exists and is task-general on average, but small per position.** The leave-one-task-out `v` is
reliable (split-half cos 0.95–0.99 across blocks 12–23) and aligned with every held-out task's mean ban
displacement (cos 0.29–0.86 at block 18; random |cos| q95 = 0.03), yet it carries only 2–6% of each position's own
ban displacement (random: 0.02%) (`results/direction.json`).

**C2d: DISCONFIRMED** (`results/c2d.json`, figs 1–3). ADD passes on 0 of 5 gated tasks; its avoidance is not above
the maximum of the three norm-matched random directions on 5 of 6 tasks (T2, T1, T04, T06, T05).

| Task (default) | Named ban avoidance | ADD α1 / α2 (k 0–9) | Random α1 (3 seeds) | SUB_plain Δ banned share [95% CI] |
|---|---|---|---|---|
| T2 (Dijkstra) | 0.88 → Bellman-Ford/SPFA | 0.44 / 0.12 | 0.06, 0.50, 0.34 | +0.07 [−0.02, 0.17] |
| T1 (BFS) | 0.87 → DFS (all 13 BFS in W4) | 0.06 / 0.04 | 0.04, 0.00, 0.02 | −0.05 [−0.11, 0.00] |
| T03 (full sort) | 1.00 → quickselect 79, size-k heap 21 | 0.80 / 0.70 | 0.24, 0.70, 0.36 | 0.00 (no default to restore) |
| T04 (naive window) | 0.49 → KMP (fails the event gate) | 0.00 / 0.00 | 0.00, 0.00, 0.00 | −0.12 [−0.22, −0.02] |
| T06 (hash set) | 0.74 → index marking | 0.00 / 0.00 | 0.00, 0.00, 0.00 | −0.06 [−0.11, −0.02] |
| T05 (hash map) | 0.80 → brute force | 0.00 / 0.00 | 0.00, 0.10, 0.00 | −0.09 [−0.15, −0.04] |

- Pooled SUBTRACT over the gated tasks: Δ = −0.026, task-bootstrap 95% CI [−0.07, 0.03] (rule: ≥ 0.3 with CI > 0).
  Projecting `v` out of the ban never restores the default; on T04, T06 and T05 it makes the ban slightly *stronger*.
  On T1/T2 neither SUB_plain nor SUB_affine exceeds SUB_rand by the required 0.15, so necessity is not credited to
  `v`; SUB_rand (a random edit with SUB_plain's norm) is destructive (pass rate 0.00).
- Where ADD moves behaviour it does not reproduce the ban: on T03 ADD lands on a size-k heap while the ban lands on
  quickselect (JS = 0.52 vs permutation q95 0.03; the committed forecast missed). On T2 ADD and the ban both land on
  Bellman-Ford/SPFA (forecast hit), but so do the random directions that move T2.
- Dose-response is non-monotone (T2: α 0.5/1/2 → 0.02/0.35/0.12 over all slots). ADD and random edits are matched at
  the hooked blocks (realised displacement within 0.4% of α·n) and random edits grow *more* downstream
  (block 35: ≈283 vs 219 on T2), so a weak control is not the explanation.
- Reading: a positive C2d would have supported a "task-general named-default-ban component" (the twin keeps the
  prohibition frame, plan item (j)); the data instead say that adding the shared component of the ban displacement is
  no more effective than a random push of the same norm, and removing it is not necessary for the ban.

**C2f: NOT SUPPORTED** (`results/c2f.json`, fig 5). Mean-ablating L21H17, L26H21, L26H25 at generated positions
raises T1's BFS share from 0.12 (ban, same slots) to 0.24, but every layer-matched random head set raises it to 0.18:
Δ_T1 = +0.06 (90% CI [0.02, 0.12]; exact paired p = 0.125 vs each random set). T2 is unchanged (Δ_T2 = −0.03,
90% CI [−0.07, 0.03]). Almost all the T1 movement is in template W4, which carries every BFS under the ban: W4 BFS
goes from 6/10 (ban) to 10/10 (target heads) and 9/10 (each random set); the target set adds 2 more BFS in W1/W2.
The W4 ban is fragile to *any* small perturbation of layers 21/26.

**C2e: no within-ban locus (frozen rule, all testable tasks)** (`results/c2e.json`, fig 4). Decoders of
default-vs-other on batch-1 teacher-forced states (blocks 8–28; S-mean, R, generated tokens 1–8 and 16), 500
within-template permutations (T1/T2; 200 for bench tasks) with a layer-max null:

| Task | n (default / other) | max state BA, k = 1 → 8 | best of R / Ta / Tb / Tc at k = 8 | locus |
|---|---|---|---|---|
| T2 | 100 (12 / 88) | 0.53 → 0.63 (never above the null q95 ≈ 0.60–0.70) | 0.55 | none |
| T1 (+ W4 top-up) | 160 (61 / 99) | 0.904 at every k | 0.904 (template only) | none |
| T04 | 100 (51 / 49) | 0.832 at every k | 0.832 (template only) | none |
| T06 | 100 (26 / 74) | 0.88 at every k | 0.88 (template only) | none |
| T05 | 100 (20 / 80) | 1.00 at every k | 1.00 (template only) | none |
| T03 | 100 (0 / 100) | not testable (no default under the ban) | | |

- On T1, T04, T06 and T05 the class is decided by the *template*: under W4 ("X is not allowed here.") the model keeps
  the default in 20/20 bench samples and writes all 61 T1 BFS programs, so every decoder (state, R, text) reaches the
  template-only accuracy and none exceeds it. This is the confound the plan named, and the within-template null
  absorbs it.
- On T2 the default is spread over templates (2/0/4/3/3 of 20) and the choice is made inside the program: the
  first class-divergent token comes at a median of ~29 generated tokens, after the frozen window. Neither state nor
  text decodes the choice within tokens 1–16 (P3's "fork at the import line, tokens 3–5" is wrong for this sample).
- Determinism check (the information bound): at batch 1, identical prefixes give bit-identical states (max |Δ| = 0
  over 89–95 pairs per position on every task). A state at position k is a function of the written prefix.
- Secondary, archive-pooled (exp8 arm a + exp12 fresh pool, 200 rows per task; same rule): no locus. T2 state BA
  reaches 0.78–0.79 at k = 4–8 against 0.75 for the template-only decoder, a margin of 0.03–0.05 (< 0.10).
- Sensitivity: the first run on 20-row-batch states (row-position noise, deviation 10) gave the same verdict on
  every task (`results/c2e_batch20_sensitivity.json`).
- **Exploratory extension** (`results/c2e_extension.json`, fig 8; positions 24–96, PCA-64 text controls incl. a
  bag-of-tokens Td): on T1 and T04 the text (exact-prefix match up to 0.93–0.96) matches or beats the state at every
  k. On T2 the state curve is noisy and non-monotone (0.57, 0.66, 0.45, 0.50, 0.75 at k = 24, 32, 48, 64, 96); only
  k = 96 clears both the null (0.66) and the text controls (≤ 0.60), with 12 minority samples and no correction across
  the 5 positions. This is a single unreplicated point, not evidence of a locus.

**0g: Qwen-Scope SAE transfer** (`results/sae_transfer.json`, fig 6). 2×2 design: each model (FP8) scored with
the base-model SAEs spliced into the residual stream (block L output, positions ≥ 1, chat special tokens excluded),
100 sequences per text source. Cells give FR_zero / FR_mean / dCE (nats) / KL(clean‖SAE) / FVU:

| Model / text | CE clean | L15 | L20 | L27 |
|---|---|---|---|---|
| instruct / own text | 0.032 | 0.9890 / 0.984 / 0.168 / 0.171 / 0.365 | 0.9903 / 0.985 / 0.169 / 0.175 / 0.096 | 0.9939 / 0.991 / 0.095 / 0.097 / 0.156 |
| base / own text | 0.926 | 0.9928 / 0.988 / 0.100 / 0.102 / 0.294 | 0.9906 / 0.986 / 0.130 / 0.134 / 0.113 | 0.9907 / 0.985 / 0.125 / 0.127 / 0.228 |
| instruct / base text | 1.861 | 1.0072 / 1.010 / -0.099 / 0.181 / 0.358 | 1.0066 / 1.010 / -0.104 / 0.220 / 0.098 | 1.0170 / 1.026 / -0.245 / 0.169 / 0.156 |
| base / instruct text | 0.251 | 0.9966 / 0.994 / 0.051 / 0.049 / 0.287 | 0.9949 / 0.992 / 0.075 / 0.075 / 0.281 | 0.9961 / 0.994 / 0.054 / 0.057 / 0.334 |

- **Frozen rule** (FR_zero(instruct, own) ≥ 0.9 × FR_zero(base, own)): PASS at L15/L20/L27 = True/True/True
  (all layers pass). As the plan computed in advance, the ~12–15
  nat zero-ablation denominator makes this rule lenient: it licenses little by itself.
- Stricter companions: FR_mean passes the same 0.9× rule at L15/L20/L27 = True/True/True; the
  dCE ratio on own text (instruct/base) is 1.68 / 1.30 / 0.76
  (exp12, bf16, one shared corpus: 3.29 / 1.95 / 1.59); KL(clean‖SAE) instruct vs base on own text:
  0.171 vs 0.102 (L15), 0.175 vs 0.134 (L20),
  0.097 vs 0.127 (L27).
- Displacement preservation (the task-relevant test: does the SAE keep the ban-minus-twin displacement at S?):
  L15: cos 0.27, norm ratio 0.67–0.73; L20: cos 0.30, norm ratio 0.65–0.79; L27: cos 0.32, norm ratio 0.66–0.75.
  So although the SAEs recover ≥ 98.4% of the CE by both denominators, their reconstructions keep only about a third
  of the *direction* of the ban displacement (cos ≈ 0.3): what the ban changes in the residual stream is largely lost
  in reconstruction error. Latent-level claims about the ban should therefore not rest on these SAEs.
- The instruct-on-base-text row has *negative* dCE (the base-trained SAE lowers the instruct model's CE on base text,
  most at L27: 1.86 → 1.62 nats), consistent with the SAE pulling instruct activations toward base-model ones.
- Sanity: identity splice equals clean CE (instruct True, base True);
  zero splice at L15 gives 13.1 / 12.3 nats (exp12: 12.36). U5 FVU vs exp12 (instruct):
  L15 0.365 vs 0.366, L20 0.096 vs 0.094, L27 0.156 vs 0.153.

**5a (descriptive): SAE latents vs DiM** (`results/sae_readout.json`). Over 63 readout cells (6 tasks ×
L15/20/27 × {prohibition-present at S-mean; default-plan at k = 1, 2, 3 where testable}), a latent readout (top-1
or top-20) beats DiM beyond DiM's CI in 1 cell: T03 L27 prohibition-present, where the S-mean state is constant
within (template, condition) and every readout is at ceiling (top-1 latent 1.00 vs DiM 0.90). Within the ban
(default-plan), latents and DiM both stay at the template-only accuracy or at chance (T2: 0.32–0.50). DiM remains the
benchmark latents do not beat, as in exp12 and AxBench.

**Exploratory (outside the frozen rules; `results/c2d.json` → `exploratory_random_distribution`, fig 9).** With 12
more random directions (15 in all, α = 1, slots k 0–9): on **T03** ADD's avoidance (0.80) exceeds all 15 random
directions (max 0.70, mean 0.24), yet it lands on a size-k heap rather than the ban's quickselect, so it is a
direction-specific push, not a reproduction of the ban; on **T2** ADD sits at the 80th percentile (3 of 15 random
directions move T2 more; random mean 0.20); on **T1** ADD is indistinguishable from random (0.06 vs mean 0.07).

**5c (descriptive): geometry of early-generation states** (`results/manifold.json`, fig 7). At the mean of generated
tokens 1–3 and at k = 16 (blocks 20 and 23; no C2e locus, so L* = 20), the k-NN graphs (k = 10) over all arms are
fragmented (100–440 connected components for 800–1,100 points). Early states are prefix-determined (batch-1
extraction) and the first tokens are shared boilerplate (the code fence and the `solve` signature), so many points
coincide and most centroid geodesics are 0. No cloud has a persistent H1 feature beyond its coordinate-permutation
null. exp9's BFS/bidirectional-BFS neighbourhood cannot be re-examined: these arms produce no bidirectional-BFS, A*
or GBFS programs. The geometry adds nothing beyond C2e.

**Committed predictions vs outcomes** (`predictions/commit1.json`):

| Prediction | Outcome |
|---|---|
| P1: ADD (α 1 or 2) beats every random control on ≥ 2/3 of gated tasks and lands on the ban's modal survivor | **No**: 0 of 5 gated tasks |
| P2: SUB raises the banned share by ≥ 0.3 | **No**: pooled Δ = −0.026 [−0.07, 0.03] |
| P3: no locus; state and text rise together at the first divergent token; T2 fork at the import line (tokens 3–5) | **No locus: yes.** Fork position: **no** (median ≈ 29 tokens, outside the frozen window) |
| P4: C2f raises T1's banned share ≥ 0.15 over random heads; T2 unchanged | T1 **no** (+0.06); T2 unchanged **yes** (−0.03) |
| P5: 0g PASS by the frozen rule, FR_zero ≈ 0.98–0.995 for both models | PASS by the frozen rule; FR_zero instruct 0.989–0.994, base 0.991–0.993 |

**Audit** (`results/rederive.json`): an independent recomputation reproduces every arm share (0 mismatches); the
placebo (arm labels shuffled within CRN slots) erases the ADD-vs-random and head contrasts; the hash chain has 0
breaks; commit #1 (19:29:04Z) precedes the first sample (19:29:31Z) and commit #2 (19:54:34Z) precedes the first
ban-condition sample (19:58:05Z).

`audit/rederive_headlines.py` (`results/rederive_headlines.json`) re-derives the headline numbers from the raw sample
and label files. It uses code paths that share nothing with `src/analysis`: plain counting, exact McNemar via
`math.comb`, `statistics.fmean` on the raw per-sequence CE lists, and an sklearn decoder. All of these match:

- the pooled SUBTRACT Δ (−0.026);
- the ADD pass count (0);
- Δ_T1 (+0.06) and Δ_T2 (−0.027);
- FR_zero;
- U7 (2/20, 20/20);
- the exploratory counts.

The independent T2 decoder (k = 8, block 17) gives BA 0.638, below the frozen null (0.695); the determinism check
holds (89/89 identical pairs). The placebos behave:

- The one-sided McNemar test on arm labels shuffled within CRN slots is significant in 4.25% of runs (≈ α).
- The sklearn decoder on within-template-permuted labels averages BA 0.48.
- Swapping the SAE and zero-ablation CE per sequence drives FR_zero to about 0, yet the frozen 0.9× 0g rule still
  "passes" at L20 on that placebo. The frozen 0g rule is therefore not a discriminating test (as the plan warned);
  the FR values themselves (≈ 0.99 vs ≈ 0 on placebo) are what carry information.


## Conventions

- **Block l** = decoder block l (0-based); its output is HF `hidden_states[l+1]`. exp8 `c5.json` and exp12 use
  `layer l = hidden_states[l]`; every comparison maps indices explicitly. exp12's SAE hook (`model.model.layers[L]`
  output) is block L here.
- **S** = `[p1, spec_end)`: from the first token of `Task:` to the last user token (chat tail excluded). **R** = P − 1.
- **Generated position k** (1-based) = absolute position P + k − 1, where generated token k is the input; the state
  there predicts token k + 1 (unit test U3 confirms the convention).
- **CRN slot** = (task, template, k): uniforms `u_stream(task, template, k)` (PCG64 of a sha256 seed), one uniform per
  (row, step), inverse-CDF in vocabulary order (exp8 sampler), identical in every arm. Every batch has exactly 20
  rows of one (task, template), `prune=False`, so batch shapes match across arms and coupling is exact.
- Labels are mechanism-level (runtime trace first, AST second, blind LLM judge only on disagreement): a renamed or
  disguised default is still the default. `invalid` and `disputed` (judge unavailable) rows are excluded from shares.

## Deviations from the plan (all logged in `results/deviations.json`)

1. **FP8 instead of bf16 / bitsandbytes.** The machine has a 16 GB RTX 2000 Ada, not the 20 GB A4500 the plan
   assumed; bf16 weights need 16.4 GB. Every decoder Linear is quantised at load time from the pinned bf16 snapshot
   to float8_e4m3 with per-output-channel weight scales and per-token activation scales (`torch._scaled_mm`); the
   embeddings, RMSNorms and lm_head stay bf16. The plan's F2 named bitsandbytes 8-bit only because it assumed a GPU
   without FP8, and no C compiler is available for Triton kernels. **Validation (U7):** with exp8's frozen prompts
   and uniform keys, T2 ban → 2/20 Dijkstra (≤ 6/20 required) and twin → 20/20 (≥ 17/20 required).
2. Batches of 20 rows (two 10-slot blocks or one 20-slot block) instead of 10; arms without a batch partner get the
   slots k 10–19 as extra rows (e.g. SUB_plain N = 100).
3. Analysis code was hash-committed at commit #2 (still before any ban sample); the decision rules were committed
   verbatim at commit #1. Reporting code written later is chained as `commit2b`.
4. U3: FP8 decode and prefill use different GEMM shapes, so the same state differs by a few percent (aligned mean
   5.2% vs 82% off by one); the criterion confirms the position convention.
5. Judge cap raised from USD 0.20 to 0.40 (T2 ban programs often leave both mechanical labellers unresolved).
6. 0g: 100 sequences per corpus (25 per exp12 group), base outputs capped at 512 new tokens.
7. 5c: 100 coordinate permutations for the H1 null; figures rendered with matplotlib directly.
8. C2e null: 500 within-template permutations for T1/T2, 200 for bench tasks and the archive-pooled secondary.
9. Secondary C1 rows (drop item 1): forecasts are committed (`predictions/c1_forecasts.json`), event rows not scored.
10. **Batch-1 teacher forcing (found mid-run).** States were first extracted in 20-row batches; under FP8 a row's
    state then depends on its position in the batch (GEMM tiling): identical prefixes differed by 4–8% (relative L2).
    The C2e and 5a states were re-extracted at batch 1 as the plan specifies; the batch-20 C2e run is kept as a
    sensitivity analysis. Decode at 20 rows is row-position independent (U1b), so the behavioural CRN coupling is
    unaffected. The 5c states stay from 20-row batches (descriptive only).
11. Exploratory additions, labelled as such and outside the frozen rules: 12 extra random directions at α = 1 on
    T2/T1/T03, and a C2e extension to generated positions 24–96 with a bag-of-tokens text control.
12. 0g's first attempt stopped at an assertion (corpus key lacked `paraphrase_id`) before producing numbers; fixed
    and re-run.

## Layout

| Path | What it holds |
|---|---|
| `method.py` | orchestrator: `prompts`, `gpu1`, `label`, `commit2`, `gpu2`, `c2e`, `zerog`, `analyze` stages |
| `src/cfg.py` | constants, paths, conventions, utilities |
| `src/engine.py` | FP8 W8A8 loader, hooked prefill, CRN inverse-CDF sampler with a preallocated KV cache, teacher forcing |
| `src/prompts.py` | S1: ban prompts and token-aligned neutral twins (14 tasks × W1–W5) |
| `src/direction.py` | S2: displacements, leave-one-task-out `v`, diagnostics, random directions |
| `src/hooks.py` | ADD / RAND (displacement-targeted), SUB_plain / SUB_affine / SUB_rand, head-ablation masks |
| `src/sampling.py` | arm definitions, 20-row batch plan, per-batch prefill + sampling, realised-norm logging |
| `src/gpu_tests.py` | GPU unit tests U1–U3 (results in `results/unit_tests_gpu.json`) |
| `src/prereg.py`, `src/commit.py` | commits #1/#2 and the sha256 hash chain (`commitments.log`) |
| `src/label_worker.py` | labelling: exp8 suite (T1/T2), exp11 bench `label_one` (bench), blind judge on disagreement |
| `src/states.py` | S8 teacher-forced state extraction (C2e, 5a, 5c, archive power boost) |
| `src/states_io.py` | state-array I/O: one `.npy`, or row-wise `.partNNN.npy` parts under 90 MB each; every reader uses it |
| `src/zerog.py` | 0g: base generation, 2×2 CE design, SAE/zero/mean splices, displacement preservation, 5a codes |
| `src/analysis/` | `c2d.py`, `c2e.py` (batched GPU IRLS decoders), `c2f.py`, `sae_report.py`, `sae_readout.py` (5a), `manifold.py` (5c), `commit2.py`, `run_all.py` |
| `src/s0_checks.py`, `src/dataset_provenance.py` | input hashes, labeller re-check, dependency-dataset provenance (all 12 twin nouns are flagged noun-bank candidates of `art_j3Rm_lr2nzR6` concreteness_norms, 1 Qwen3 token each) |
| `src/c2e_ext.py` | exploratory C2e extension (generated positions 24–96, bag-of-tokens text control) |
| `src/patch.py` | conditional causal patch (runs only if C2e finds a locus; it found none, so it never ran) |
| `src/export_token_ids.py` | writes `data/token_ids/all.npz` (all generated token ids + offsets + keys) |
| `audit/rederive.py` | independent recomputation of arm shares, placebo (arm labels shuffled within slots), hash-chain and timing checks |
| `audit/rederive_headlines.py` | independent re-derivation of every headline number from raw files, with placebo tests |
| `reproducibility.md` | exact commands, hardware, versions, seeds and expected numbers |
| `tests/` | T3 direction maths, T4 synthetic decoder test, FP8 probe, speed/memory probe (U6), download script, README fillers, `make_mini_preview.py` (fallback for the mini/preview files) |
| `inputs/` | read-only copies of the iteration-2 inputs (exp7, exp8, exp9, exp11 bench, exp12, audit) |
| `prompts/prompts.jsonl` | 140 prompts (ids, p0, p1, spec_end, P, sha256) |
| `directions/` | `v_<task>.npy` (12 × 4096 unit vectors, blocks 12–23), `norms_<task>.npy`, `rand_<seed>.npy`, diagnostics arrays |
| `predictions/` | commit #1 (`commit1.json`: rules, predictions, seeds, head sets) and commit #2 (landing and C1 forecasts) |
| `data/samples_raw.jsonl` | every generated sample (arm, slot, block id, token ids, text) |
| `data/labels.jsonl` | one label row per sample (runtime, AST, judge, combined label, pass) |
| `data/realised_norms.jsonl` | realised edit and displacement norms of every edited prefill |
| `states/` | fp16 teacher-forced states (kept on the run volume; not published). Arrays over 90 MB are stored as row-wise parts `<name>.part001.npy`, `.part002.npy`, … (GitHub's 100 MB limit); `src/states_io.py` loads either form |
| `results/` | every analysis JSON (`c2d`, `c2e`, `c2e_batch20_sensitivity`, `c2e_extension`, `c2f`, `sae_transfer`, `sae_readout`, `manifold`, `direction`, `unit_tests_*`, `labeller_recheck`, `input_hashes`, `timing`, `deviations`, `rederive`, …) |
| `figures/` | fig1 avoidance by arm, fig2 landings, fig3 SUBTRACT, fig4 C2e curves, fig5 head ablation, fig6 0g 2×2, fig7 manifold, fig8 C2e extension, fig9 random-direction distribution (PNG + PDF) |
| `data/token_ids/all.npz` | every generated token id (also stored per row in `data/samples_raw.jsonl`) |
| `method_out.json` | exp_gen_sol_out: datasets `c2d_arms`, `c2f_heads`, `c2e_locus`, `sae_transfer` (+ mini/preview variants) |

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python method.py prompts                 # S1 (CPU)
.venv/bin/python method.py gpu1 --minutes 80 --optional-minutes 95   # S2, unit tests, commit #1, U7, S5
.venv/bin/python method.py label --minutes 270 &   # label worker (follows data/samples_raw.jsonl)
.venv/bin/python method.py commit2                 # S6 after every S5 row is labelled
.venv/bin/python method.py gpu2 --minutes 45 --optional-minutes 40  # S7 + S8
.venv/bin/python method.py c2e --minutes 40        # C2e decoders (GPU)
.venv/bin/python method.py zerog --minutes 60      # 0g (loads the base model, then the instruct model)
.venv/bin/python method.py analyze                 # S9 analyses, figures, method_out.json
.venv/bin/python audit/rederive.py                 # audit
```

The OpenRouter judge needs `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY`. Models and SAEs are read from the Hugging
Face cache named by `HF_HUB_CACHE`.

## Restoring removed files

| Removed path | Restore with |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` |
| `__pycache__/` | regenerated automatically by Python |
| Qwen3-8B (shared cache, not in this folder) | `huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218` |
| Qwen3-8B-Base (shared cache) | `huggingface-cli download Qwen/Qwen3-8B-Base` |
| Qwen-Scope SAEs (shared cache) | `huggingface-cli download Qwen/SAE-Res-Qwen3-8B-Base-W64K-L0_50 layer15.sae.pt layer20.sae.pt layer27.sae.pt` |

`states/` (teacher-forced fp16 states, several GB) and `directions/` stay on the run's storage volume and are not
part of the published repository; `states/` can be regenerated with `method.py gpu2` (S8 only re-runs missing
files) from `data/samples_raw.jsonl`.
