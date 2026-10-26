# Finding the model's hidden algorithm switch (iteration 7, bf16 Qwen3-8B)

Qwen3-8B (revision `b968826d…`, bf16, thinking off) almost always writes one default algorithm per coding task:
Dijkstra for weighted shortest paths (T2), union-find for connected components (T10) and a full sort for the k-th
smallest element (T03). A prompt that bans the default ("Write a correct solution that does not use Dijkstra's
algorithm.") or forces an alternative ("Implement Floyd-Warshall for this task.") makes it write another algorithm.
This artifact asks whether that choice is carried by a **low-rank linear subspace** of the task-specification
states. The method is distributed alignment search (DAS): one orthonormal map `R` (4096 x 16, nested ranks
k = 1, 2, 4, 8, 16) is fitted on teacher-forced pairs. It is then tested where it counts, in held-out **generation**
scored by hidden tests, against the full-state exchange at the same site (the ceiling) and a battery of controls.

## Results

**Bottom line.** A rank-1 or rank-2 linear edit of mid-layer task-specification states moves the algorithm the
model writes about as much as exchanging the full states, and random subspaces of the same rank do nothing. But the
committed tests that would make this subspace *the* algorithm variable fail: permuted-label maps steer just as
well, a randomly initialised network admits an equally good teacher-forced fit, and the reverse interchange does
not restore the default. **P1 is NOT SUPPORTED on any task.** What was found is a strong, low-rank steering handle,
not a clean causal variable.

- **Where the choice is carried (layer profile + generation confirmation, `figures/F1_layer_profile`).**
  - *Teacher-forced profile.* The single-block full-state exchange peaks at block 18 (T2) and block 16 (T10, T03).
  - *Ban sources need the band.* In generation, exchanging the W5 ban's spec states at that single block moves
    **0/30** slots on T2 and T10. Exchanging them at every block of 12-23 moves 11/30 (T2, base 1/30) and 17/30
    (T10, base 0/30). So the committed band fallback fired on both core tasks.
  - *Forced instructions are carried by one block.* The same single-block exchange of a forced 'Implement Y'
    prompt transfers fully: T2 Bellman-Ford/SPFA 30/30 at block 18, T10 BFS 28/30 at block 16.
  - *T03 is single-block.* Its ban is carried by block 16 alone (27/30 vs band 28/30; base 5/30).
- **The committed DAS objective breaks the model (amendment 1).**
  - *Divergence.* The contrastive objective `C = LME_Y - LME_D` grew without bound on validation: T2 1,873 nats,
    T10 3,868 nats, against full-state ceilings of 14-35 nats. Its permuted-label twin diverged too (T2 880 nats).
    It rises by destroying the default's likelihood, as the plan warned.
  - *Generation pilot.* In a 10-slot pilot the committed map wrote broken programs: T2 ban arms 0/50 correct
    Bellman-Ford, pass 0.02; 77 of 110 T2 rows truncated.
  - *Amendment.* Before any held-out generation, a second map per task was fitted with the bounded standard DAS
    objective, the likelihood of the source's own programs (`LME_Y`). It used the same class, pairs, seeds and
    budget, with permuted-label and read-position twins. Every decisive cell below uses this map (`MAIN_LY`).
- **DAS recovers the full-state transfer at rank 1-2; random subspaces do not (`figures/F2_recovery_vs_rank`).**
  - *T2 ban source.* DAS rank 2 gives 12/30 correct Bellman-Ford/SPFA, against full-state 11/30 and base 1/30.
    Random rank-16 subspaces give 1, 0 and 1 of 30. McNemar DAS vs random 11:0 (Holm p 9.8e-4).
  - *T10 ban source.* DAS rank 16 gives 29/30 BFS, against full-state 17/30. Random gives 0/30. McNemar 61:0
    (Holm p 2.6e-18).
  - *T03 ban source.* DAS rank 1 gives 26/30 landing programs, against full-state 27/30 and base 5/30. Random gives
    6/30. McNemar 20:0 (Holm p 1.9e-6).
  - *Pass rates* stay at 0.8 or more of the base's on every DAS arm at the evaluated rank.
  - *Controls that hold.* Read-position DAS transfers 0.03 / 0.07 (T2 / T10). DIM-1 and PCA-16 transfer at most
    0.00. The null source ('Implement Dijkstra') transfers at most 0.03 off-default.
- **…but the committed specificity controls fail, so P1 = FAIL on T2, T10 and T03.**
  - *Permuted labels.* DAS fitted with permuted labels moves the true landing algorithm too: T2 15/30 at rank 2
    (transfer 0.47), T10 21/30 at rank 16 (0.70), T03 23/30 at rank 1 (0.60). The committed limit is 0.1.
  - *The permuted map can also write its own label.* At rank 16 it turns the T2 ban source into Floyd-Warshall
    programs (15/30); one training ban (W2) had been relabelled 'floyd'.
  - *Few labels to shuffle.* With only two kept algorithms per task, the permutation changed 44% of the training
    labels (56% on T03). The 'leave the default' signal survives any such shuffle.
  - *Random-initialisation control (Sutter, matched to the amended objective).* On a randomly initialised Qwen3-8B
    the fitted rank-16 map reaches a held-out teacher-forced gain of 13.3 nats, against 14.5 nats on the trained
    network (ratio 0.92; the committed limit is < 0.5). The full-state exchange on that random network does
    nothing (-0.9 nats). So the teacher-forced fit alone certifies nothing here.
- **Routing (C) is CATEGORICAL by the committed rule, but not because the map transfers a natural variable
  (`figures/F3_routing_confusion`).**
  - *Beyond the full-state exchange.* On T2 the map routes forced Floyd-Warshall 28/28 at rank 1, and on T03 forced
    counting sort 30/30. The full-state exchange at the same site does not carry either: Floyd-Warshall 8/20 (the
    rest become Bellman-Ford), counting sort 0/30.
  - *T10 is not categorical.* Both forced sources land on DFS: forced BFS routes to BFS on only 1/30 at rank 1 and
    9/30 at rank 16.
  - *Reading.* The map writes the forced algorithm more strongly than the source's own states transfer it.
- **Dormant-pathway checks (c6, `figures/F7_dormant_checks`).**
  - *Natural directions.* The fitted directions carry 0.7-18% of the natural cross-condition variance, against
    0.03-0.4% for random subspaces of the same rank (100th percentile).
  - *T2 reverse fails.* Writing the twin's value into the W5 ban at k* = 2 restores Dijkstra on 0/30 slots. The
    full-state reverse restores it on 21/30. Reverse recovery is 0, so the **DORMANT FLAG is raised (T2)**.
  - *T03 projection fails.* Projected onto the top-64 natural principal directions, the map keeps only 20-26% of
    its teacher-forced gain, so the **DORMANT FLAG is raised (T03)**.
  - *T10 is not testable.* The full-state reverse moves nothing, so reverse recovery is not estimable.
- **Where prompts sit on the plan subspace, and what they make the model write (M, T2, `figures/F4_causal_manifold`,
  `F5_topk_prohibition_placement`).**
  - *Bans move along the runner-up axis.* In R_16 coordinates all five ban paraphrases leave the paraphrase cloud
    (100th percentile of the 66-prompt null). They move along the Dijkstra -> Bellman-Ford axis by +1.1 to +1.8
    (null SD 0.37), toward the runner-up, which is also the base model's second choice (18 vs 25 correct programs).
  - *Seeds and instructions stay inside the null.* `seed=d32qxk4nt43`, `seed=(horse chair roof love)`,
    'Make a new algorithm.' and the 2,000-word novelty instruction sit at the 76th-94th percentiles.
  - *Behaviour matches (extension, N = 30 each).* Both random seeds, the semantic seed and 'Make a new algorithm.'
    keep Dijkstra on 28-30 of 30. Only the long-form novelty instruction moves anything: 6/30 Bellman-Ford, the
    runner-up. That shift happens while the model writes its rationale, not in the prompt states.
  - *Prediction miss.* The semantic seed sits at the 94th percentile, inside the null; it was predicted outside.
  - *Leave-one-survivor bans.* They are not placed near their survivor (mean survivor rank 3.1 of 5, random
    relabelling p 0.63). All of them sit nearest Bellman-Ford's forced points.
- **Discreteness (R, `figures/F6_discreteness`).**
  - *Graded, then flat.* Scaling the rank-2 edit by lambda raises correct Bellman-Ford from 1/20 (lambda 0-0.2)
    through 4/20 (lambda 0.4-0.5) to a plateau of 6-9/20 from lambda 0.6 to 1.5.
  - *Not discrete.* The committed logistic width is 3.25 (DISCRETE needs <= 0.3). The one hybrid candidate was
    judged a single algorithm.
  - *Reading.* The edit sets a probability over algorithms rather than flipping a switch.
- **Novelty.** 38 correct programs were labelled 'other': 36 are catalogue variants and 2 are labeller misses.
  None is novel.
- **Engine, audits, cost.**
  - *Engine check.* Per-slot twin labels agree with exp30's: T2 20/20, T03 19/20, T10 20/20.
  - *Unit tests.* U1, U2, U5 and U6 are exact. U3/U4 show 0.1-0.3-nat bf16 kernel-shape noise, so every compared
    condition of a pair is scored in one batch.
  - *Commit chain.* 18 commits, 0 breaks, no committed file changed.
  - *Re-derivation.* `audit/rederive.py` and `audit/rederive_tf.py`: 180 + 52 checks, 0 mismatches. Their placebos
    fail as they should (within-slot swaps p 0.31-1.0, random vs random p 1.0, random-as-DAS recovery <= 0.05).
  - *Cost.* 4,500 generated programs, about 1.6 GPU-hours on one RTX 4090, OpenRouter USD 0.13 (judges only).

| committed test / prediction | result |
|---|---|
| L* in blocks 14-20 (or band on T10) | L* 18 / 16 / 16; band fallback on T2 **and** T10 |
| full-state transfer at the site, T2 ban >= 0.5 | 0.33 (missed) |
| k* in {2, 4, 8} on T2 and T10 | T2 2; T10 1 (missed); T03 1 |
| **P1** (recovery >= 0.8, margin over random >= 0.4, McNemar Holm p < 0.01, permuted <= 0.1, pass >= 0.8x, T2 random-init < 0.5) | **FAIL on T2, T10, T03** (permuted clause everywhere; random-init on T2): **NOT SUPPORTED** |
| random rank-16 <= 0.15 / read position <= 0.05 / null <= 0.1 | 0.00-0.03 / 0.03 (T2), 0.07 (T10) / <= 0.03 |
| C: categorical on T10; Floyd-Warshall / Dial not routable on T2 | C = CATEGORICAL (T2, T03) by rule; T10 **not** categorical; Floyd-Warshall not routable by full-state, routed by DAS; Dial not kept (2/20 adherence) |
| dormant flag | raised on T2 (reverse) and T03 (projection) |
| M: random seeds inside the null; semantic seed outside | inside (88th, 77th pct); semantic seed **inside** (94th) |
| R: transition width <= 0.3 | 3.25: graded, not discrete |
| novelty: claim 'no novel algorithm' only at 0 | 0 novel of 38 |

Figures (PDF + PNG in `figures/`): F1 layer profile and confirmation, F2 recovery vs rank (generation and
teacher-forced), F3 routing confusion matrices, F4 causal manifold (DAS-1 x DAS-2 plane, MDS, Isomap, centroids
sized by implemented count under the twin, under Qwen3-8B-Base and under the knobs, all in actual activation
coordinates), F5 leave-one-survivor placement, F6 discreteness, F7 dormant checks, F8 fit curves (the committed
objective diverges; the amended one is bounded). Every table is in `results/summary.md`, generated from the JSON
results.

## What was run

Every arm runs in one HF bf16 engine: exp30's float64 inverse-CDF sampler with exact common random numbers. Every
arm of a slot shares the slot's uniform stream, generation uses a fence stop, and the batch size is fixed per task.
Programs are labelled by the frozen gated labellers (runtime tracer + AST; a blind judge only on disagreement; the
exp28 re-gate for T2). Edits act on block outputs at the task-specification positions during the prefill only,
in fp32, cast to bf16.

| block | what | design |
|---|---|---|
| Stage 0 | forced 'Implement Y' (5 template families x every catalogue algorithm, N = 20 per Y), padding twins, bans W1-W3 (N = 10 each), the W5 ban (N = 30), twins | kept Y (adherence >= 0.7): T2 Bellman-Ford/SPFA, Floyd-Warshall; T10 BFS, DFS; T03 heapify-pop, quickselect, counting sort. Ban landing: T2 Bellman-Ford/SPFA, T10 BFS, T03 quickselect + size-k heap |
| targets | 5 correct programs per algorithm (first 48 response tokens, exact ids) | ban samples first, then TRAIN-family forced samples; defaults from the twins + TRAIN-family padding twins (amendment v2) |
| layer profile | teacher-forced full-state exchange at blocks 10-26 (step 2), bands 12-23 / 0-35, the read position, on 24 aligned training pairs | L* = argmax mean gain; confirmed in generation (N = 30) on the held-out W5 ban and family-3 forced source |
| DAS fits | one orthonormal map (nested ranks 1-16), rank-cycled training on all (source x base) training pairs aligned by offset from 'Task:'; 150 steps (+75 if still improving), early stopping on validation bases | committed objective C (diverged; T2 also its permuted and read-position twins); **amended objective LME_Y**: MAIN_LY + PERM_LY (+ RPOS_LY on T2, T10) |
| controls | random rank-k subspaces (seeds 9001-9003), permuted-label DAS, read-position DAS + full-state at the read position, null source 'Implement <default>', DIM-1, PCA-16, projected map (top-64 natural PCs), reverse interchange, Sutter random-init network (T2) | all on the same CRN slots |
| held-out generation | W5 ban -> W5 twins (12 nouns, slot mod 12); forced families 3/4 -> their padding twins; N = 30 per cell | 1,400 programs on T2, 1,250 on T10, 660 on T03 (incl. confirmation cells, the committed-map pilot and the second seed) |
| M, R, extensions | R_16 coordinates of 151 T2 prompts; lambda sweep (N = 20 x 10); behaviour of seeds/instructions (N = 30 x 6); a second init seed (T2) | no generation in M itself |

## Deviations from the plan

- **Objective (amendment 1).** The committed contrastive objective diverged (see Results). A bounded LME_Y map was
  fitted before any held-out generation and carries every decisive cell. The committed map is reported from a
  10-slot pilot. On T10 only its MAIN fit was run; T03 uses only the amended objective.
- **Site.** The declared band fallback fired on T2 and T10, so those maps act on blocks 12-23. T03 acts at block 16.
- **GPU and caps.**
  - *GPU.* An RTX 4090 (24 GB) instead of the planned A4500, with the whole model on the GPU and batch 16 per task.
  - *Caps.* Generation caps are exp30's 384 / 512 tokens, kept for engine-check comparability and time;
    truncations are counted per cell.
  - *Cache.* `HF_HOME` was not redirected to `./hf_cache`, as the run instructions require.
- **Unit tests U3/U4.** Both miss the strict tolerances because of bf16 kernel-shape noise. Every compared
  condition of a pair is therefore scored in one batch.
- **Analysis code** was frozen in amendment 2, before generation (not in commit 0). The P1 random-init clause uses
  the LME_Y-matched random-network fit; the committed comparison was against a diverged fit (ratio 0.013, not
  meaningful).
- **Targets.** Distinct 48-token openings are few, so the default pool was extended to padding twins (amendment
  `commit1_<task>_v2`). Validation target sets are partly filled from training programs. T10 DFS has 3 distinct
  programs, T03 heapify-pop 1 and full sort 2.
- **Baselines.**
  - *PCA-16* uses per-position-centred states, because the 15 forced prompts give rank 14.
  - *Middle block.* DIM-1, the natural-state checks and M use block 18, the band's middle block.
  - *Held-out targets.* The held-out teacher-forced pairs use the training target sets.
- **Drops.** Plan resampling and the T1 extension (T1 DAS and the literal top-five placement on T1) were not run.
  Each DAS fit has one init seed; a second seed was added on T2 as an extension.
- **Extensions beyond the plan.** Behaviour of the prompts M places (N = 30 each) and a second init seed on T2: the
  two subspaces differ (principal angles 38-90 degrees) yet behave alike (no significant McNemar difference).

All items are in `results/deviations.json`. Amendments are in `commitments.log` / `predictions/`.

## Layout

| path | content |
|---|---|
| `method.py` | entry point: every stage in the order it was run (`.venv/bin/python method.py [stage …]`) |
| `src/prompts7.py` | all prompt records (bans, 12-noun twins, forced x 5 families, padding twins, M prompts) + CPU tests |
| `src/gpu7.py`, `src/run_gpu7.py` | GPU engine (prefill edits, CRN generation via exp30's decoder) and the stage driver |
| `src/das7.py` | packed teacher-forced scoring, site caches, the DAS map class, fitting and validation |
| `src/stages_a7.py`, `src/stages_b7.py`, `src/stages_c7.py` | unit tests and Stage 0; targets, profile, fits, TF evaluation; generation cells, R, M, random-init, extensions |
| `src/analysis7.py`, `src/m7.py` | committed analyses (P1, controls, C, dormant, R, pilot) and the manifold analysis |
| `src/report7.py`, `src/summary7.py`, `src/figures7.py`, `src/outputs7.py`, `src/bookkeeping7.py` | results JSON + figures, `results/summary.md`, `method_out.json`, deviations / costs / timing |
| `src/prereg7.py`, `src/commit7.py` | commit 0 and the sha256 hash chain (genesis sha256('iter7_dir2')) |
| `src/label7.py`, `src/novelty6.py`, `src/hybrid7.py` | label worker (frozen labellers), novelty audit, R hybrid judge |
| `src/cfg.py`, `cfg6.py`, `engine*.py`, `gpu6.py`, `label_worker_v4.py`, `regate_rules.py`, `prompts_v4.py`, `prompts6.py`, `stats6.py`, … | byte copies of exp30's code, reused unchanged |
| `audit/rederive.py`, `audit/rederive_tf.py` | independent re-derivation of the headline numbers from the raw rows (180 + 52 checks, 0 mismatches) + placebo tests that fail as they should |
| `reproducibility.md`, `restore.sh` | exact reproduction steps as run; venv + model restore |
| `prompts/prompts7.jsonl`, `prompts/prompt_report7.json` | every prompt with positions and split |
| `data/samples_raw.jsonl`, `data/labels.jsonl` | one row per generated program (4,500) and its label |
| `data/tf_profile.jsonl`, `data/tf_heldout*.jsonl` | teacher-forced profile and held-out evaluation rows |
| `das_maps/` | every fitted and control map (`<task>_<fit>.pt`, 16 x 4096 fp32) + natural PCs |
| `cache/` | spec-mean natural states and M coordinates (npz) |
| `results/` | every analysis (`p1`, `p1_controls_*`, `c_routing`, `dormant`, `m_manifold`, `m_behaviour`, `r_*`, `seed2_*`, `randinit*`, `site_*`, `targets_*`, `das_fits*`, `tf_eval*`, `novelty_audit`, `engine_check`, `unit_tests_gpu`, …) and `summary.md` |
| `figures/` | F1-F8 (PDF + PNG) |
| `predictions/`, `commitments.log` | commits and amendments (18, verified) and hardware |
| `inputs/`, `inputs_extra/` | read-only copies of the prior artifacts read here (exp30 code, prompts and labels; bench; exp8 suite; extracts of exp24, exp29, exp9) |
| `method_out.json` (+ `full_`, `mini_`, `preview_`) | exp_gen_sol_out output: one example per (task, source group, CRN slot), `predict_<arm>` = `label|pass` |

## How to run

```bash
bash restore.sh                                  # venv from pyproject.toml + Qwen/Qwen3-8B@b968826d (HF cache)
.venv/bin/python method.py                       # or stage by stage: prompts commit0 utest s0 targets profile fit fitly gen after report novelty outputs audit
```

The GPU stages need one CUDA GPU with at least 24 GB. The label worker, the novelty audit and the hybrid judge
need `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY`; judges are called only on labeller disagreement.

## Kept artifacts

The fitted maps (`das_maps/`), the raw and labelled samples (`data/`), the natural-state caches (`cache/`) and every
result stay on this run's volume at these relative paths. All are small; no file in this folder reaches 100 MB.
The model weights are not in this folder.

## Restoring removed files

| removed path | restore with |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` |
| `**/__pycache__/` | regenerated on import (or `.venv/bin/python -m compileall -q src inputs`) |
| model weights (shared HF cache, not in this folder) | `.venv/bin/python src/download_model7.py` (or `huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218`) |
