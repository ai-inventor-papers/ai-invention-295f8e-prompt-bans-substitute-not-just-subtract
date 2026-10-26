
### G1: a circuit for the fork margin (G1-P path patching, validated in the real model)

- **Pairs.** 15 clean/corrupt pairs: 10 natural pairs (DFS-leaning vs BFS-leaning twin variant of the same template,
  total effect 0.8-3.4 nats) and 5 forced pairs (forced-DFS vs forced-BFS, F1-F5, 15-19 nats). The mean total effect
  is 7.2 nats.
- **Screen.**
  - AtP covered 1,224 nodes (272 heads + 34 MLPs x FORK / CSTAR / SPEC / COND).
  - Exact patching covered 60 nodes. AtP agrees with exact noising at Pearson 0.65 and Spearman 0.73, with mean
    absolute error 0.31 nats against a mean exact effect of 0.55.
  - Where the effect enters: FORK 53%, COND 36%, SPEC 6%, CSTAR 5% (share of total exact noising effect).
  - The natural-pair and forced-pair top-20 sets overlap with Jaccard 0.38.
- **Top 10 nodes by exact noising effect** (clean DFS-leaning run, node <- BFS-leaning value; mean over 15 pairs):

  | Node | Noising effect (nats) |
  |---|---|
  | MLP L0 @ COND | +4.43 |
  | MLP L6 @ COND | +2.01 |
  | MLP L25 @ FORK | +1.96 |
  | MLP L21 @ FORK | +1.54 |
  | MLP L2 @ COND | +1.00 |
  | head L22.H5 @ FORK | +1.00 |
  | MLP L26 @ FORK | +0.97 |
  | MLP L14 @ COND | +0.93 |
  | MLP L22 @ FORK | +0.86 |
  | MLP L17 @ FORK | +0.84 |

  Every node's denoising effect has the opposite sign (-0.65 to -5.5).
- **Edges (path patching, kept if |dm| >= 5% of the total effect = 0.36 nats).**
  - Fork-position MLP chain: MLP L17 -> MLP L19 (+0.56), MLP L21 -> MLP L22 (+0.51), MLP L25 -> MLP L26 (+0.53).
  - Head L22.H5 -> MLP L25 (+0.50).
  - Direct paths to the margin: head L33.H2 (+0.88), MLP L25 (+0.62), MLP L22 (+0.57), MLP L26 (+0.42).
  - The condition-sentence MLPs (L0-L14 at COND) act through the residual stream and later attention, not through a
    single kept edge. They encode the noun or condition; the fork-position chain turns it into the token-32 choice.
- **Cross-check with iteration 6.** Iteration 6's strongest first-order SAE nodes sat at the FORK position at layers
  22 and 29. G1-P's top FORK nodes sit at layers 15-33, peaking at 21-26. The site agrees.
- **Validation in the real model (24 prompts: 10 BFS-leaning + 10 DFS-leaning variants + forced F1/F5 x BFS/DFS).**
  - Each top node was ABLATED (set to the opposite-class mean at aligned positions) or STEERED (own + 2 x (opposite
    mean - own mean)), against 50 random components of the same position class matched on write norm.
  - MLP nodes rarely had 50 MLP candidates within +/-50% of their norm, so their nulls are the 50 nearest-norm
    components of any type at that class (D09).
  - d_i = oriented dm(node) - mean dm(random nulls); exact one-sided sign-flip test over the 20 variants; Holm over
    10 nodes.

  | Node | ABLATE median d (Holm p) | STEER median d (Holm p) | Claim (ablate / steer) |
  |---|---|---|---|
  | MLP L0 @ COND | +0.28 (< 1e-4) | +0.49 (4e-4) | yes / yes |
  | MLP L6 @ COND | +0.16 (0.09) | +0.25 (0.25) | no / no |
  | MLP L25 @ FORK | +0.28 (3e-4) | +0.62 (< 1e-4) | yes / yes |
  | MLP L21 @ FORK | +0.23 (5e-4) | +0.48 (< 1e-4) | yes / yes |
  | MLP L2 @ COND | +0.07 (0.15) | +0.10 (0.13) | no / no |
  | head L22.H5 @ FORK | +0.19 (0.002) | +0.39 (< 1e-4) | yes / yes |
  | MLP L26 @ FORK | +0.15 (5e-4) | +0.61 (< 1e-4) | yes / yes |
  | MLP L14 @ COND | +0.17 (5e-4) | +0.39 (0.001) | yes / yes |
  | MLP L22 @ FORK | +0.34 (1e-4) | +0.68 (< 1e-4) | yes / yes |
  | MLP L17 @ FORK | +0.05 (0.10) | +0.17 (< 1e-4) | no / yes |

  - **NODE CLAIM holds for 7 nodes (ABLATE) and 8 nodes (STEER).** The joint top-5 set beats all 50 matched random
    sets (median oriented dm 0.98 nats ablate, 2.0 steer), and so does the top-10 set (1.47 and 3.96).
  - On the natural variants the effects are modest: the natural pairs differ by only about 2 nats in total. On the
    forced prompts they are large: ablating MLP L0 at the condition sentence to the opposite forced class moves m by
    13-17 nats, and the fork-position MLPs move it by 1.7-5.7 nats.
  - Reading: the condition-sentence MLPs (L0, L14) carry the prompt's lexical cue; the fork-position stack (MLP
    L21/L22, head L22.H5, MLP L25/L26) turns it into the token-32 decision. This is one circuit hypothesis for one
    fork, with per-prompt distributions in `results/g1_validation.json`.
- **Generation arms (N = 30; twin W1-W5 x 6 CRN slots; prompt + c* prefilled; edits in the prefill).**

  | Arm | Attempted target | Correct target | Pass | Test |
  |---|---|---|---|---|
  | twin | 9 BFS | 8 | 0.97 | - |
  | top-5 STEER toward BFS | 20 BFS | **16** | 0.83 | vs twin: correct 10 vs 2, p = 0.019; attempted 12 vs 1, p = 0.002. vs random-5 STEER: p = 0.006 (correct), 0.002 (attempted) |
  | random-5 STEER (matched) | 9 BFS | 7 | 0.93 | null |
  | top-5 ABLATE to the BFS mean | 12 BFS | 7 | 0.83 | attempted 3 vs 0, p = 0.125 |
  | random-5 ABLATE | 9 BFS | 6 | 0.90 | null |
  | top-10 ABLATE to the BFS mean | 12 BFS | 10 | 0.93 | p = 0.125 (attempted) |
  | top-5 ABLATE to the DFS mean | 22 DFS | 22 | 0.90 | vs twin 21 DFS: n.s. |

  Steering the validated nodes moves what the model writes and keeps the programs valid. Setting them to the natural
  class mean does not: the natural classes differ by only about 2 nats at the fork, so a class-mean ablation is a
  small push.

### G1-T: circuit-tracer attribution graph (timed attempt)

G1T_SECTION

## Audit (independent re-derivation)

- **Hash chain.** `audit/verify_chain.py` (standard library only) re-derives every chain value. The ordering checks
  pass:
  - commit #0 precedes every sample;
  - #1 precedes the first temperature sample;
  - #2b precedes the first G1 generation row;
  - #3 precedes the first dose-sweep row.

  See `results/verify_chain.json`.
- **Re-derivation.** `audit/rederive.py` (standard library only) re-derives 52 headline quantities from the raw rows
  with **0 mismatches**: engine counts, U6 counts and McNemar, every G3 cell and the MAE, the G1 arm counts and their
  McNemar p, and every G2 dose count with its Holm-adjusted p. See `results/rederive.json`.
- **Placebos.**
  - A temperature-shuffled G3 sweep gives MAE 0.123 against the real 0.026, and fails the 0.10 law.
  - Randomly sign-flipped G1 node effects give 0 significant nodes.
  - Slot-shuffled (unpaired) dose cells are reported beside the paired tests.
- **Labeller.** On the frozen exp8 T1 labeller, 12/12 references are labelled correctly and 5/5 hand-made mutants
  fail the hidden tests. Runtime and AST agree on 2,830 of 3,010 programs; the blind judge (openai/gpt-4.1-mini)
  resolved the other 180.
- **Spend.** OpenRouter USD 0.044 in total (labeller judge 0.036 over 88 calls; novelty audit and re-gate
  0.007), against the USD 0.5 cap.

## method_out.json

exp_gen_sol_out format, validated. Datasets:

| Dataset | Rows | Output | Predictions |
|---|---|---|---|
| `engine_check` | 50 | this run's label\|pass | `predict_iter6` |
| `u6_calibration` | 200 | (b) single-prompt label | (a) multi-prompt full and partial labels |
| `g3_calibration_fork_token` | 500 | forced fork token -> label\|pass | iteration 6 token-table prediction |
| `g1_nodes` | 20 | node effect (oriented dm) | `predict_random_null` |
| `g1_generation` | 30 slots | twin | one `predict_<arm>` per arm |
| `g2_teacher_forced` | 768 held-out pairs | dy_full | DAS k1-k8, RAND, SHUF, DiM |
| `g2_dose_sweep` | 50 slots | twin | one `predict_<cell>` per cell |
| `g3_temperature` | 50 slots x 2 samplers | T1.0 label | `predict_T0p3`, `predict_T0p7`, `predict_T1p3` |

`metadata.results` holds every `results/*.json`. The `full_`, `mini_` and `preview_` variants are beside it.
