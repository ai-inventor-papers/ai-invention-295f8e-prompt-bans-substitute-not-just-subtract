# Where tuning sharpened the algorithm choice (iteration 9, claims B1-B3)

This artifact tests the run's question "does an LLM give the mean answer?" at the **single decision token where a
code model picks its algorithm** (the *fork*). It compares base and instruction-tuned models on identical token ids
and asks three things:

* **B1** (behavioural, teacher-forced): how much sharper is the instruct model at the fork than its base, in two new
  families (Gemma-3-4b pt/it, Llama-3.1-8B base/instruct), and is the divergence special to forks once base entropy is
  controlled (Cantarero-style controls)?
* **B2** (mechanistic, Qwen3-8B vs Qwen3-8B-Base): which components carry the sharpening? Cross-model activation
  patching (CMAP) of base outputs into the instruct run at the fork, against an exhaustive single-component sweep, 50
  write-norm-matched random sets, the task-specification nodes, residual-stream swaps, a reverse patch, a weight swap,
  a CPU readout decomposition, and a generation test (N = 30 common-random-number slots per arm).
* **B3**: rerun of iteration 8's held-out validation of the layer-0 condition MLP, whose held-out arm never applied an
  edit because of a `MeanCache` bug, plus the motif statistic on contrasts matched in kind.

Everything was pre-registered in a sha256 commitment chain (`commitments.log`, `predictions/`) before the decisive
passes; every headline number was re-derived by an independent standard-library script with placebos
(`results/rederive.json`: 0 mismatches).

## Results (all numbers from `results/*.json`)

### B1: base vs instruct at counterfactually located forks (verdict **PARTIAL**)

Margin = log P(default class) − log P(alternative class) at the fork, chat template (primary for Gemma; the committed
rule switched Llama to template-free because the Llama-3.1-8B base embedding rows of `<|start_header_id|>`,
`<|end_header_id|>` and `<|eot_id|>` have ~3e-21 × the median row norm, i.e. they are untrained).

| fork | N | instruct P(D) | base P(D) | gain (nats) [95% CI] | template-free gain | JS fork / entropy-matched | argmax differs |
|---|---|---|---|---|---|---|---|
| G-GRID@32 (BFS vs DFS) | 20 | 0.671 | 0.089 | 1.78 [1.59, 2.00] | 0.95 | 1.09 | 20/20 |
| G-T04@31 (substring) | 5 | 0.832 | 0.765 | 1.75 [−1.31, 4.82] | 4.54 | 0.75 | 2/5 |
| G-R6@12 (first/last) | 5 | 0.946 | 0.370 | 3.07 [2.06, 4.10] | 2.03 | 1.18 | 0/5 |
| G-R6@24 (first/last) | 5 | 0.882 | 0.481 | 1.68 [0.37, 2.99] | 3.05 | 0.90 | 0/5 |
| L-GRID@52 (descriptive) | 5 | 0.654 | 0.366 | 0.96 (template-free) | — | 0.60 | 5/5 |
| L-GRID@121 (descriptive) | 5 | 0.606 | 0.757 | −0.71 (template-free) | — | 0.71 | 0/5 |

* P1 (gain ≥ 2 nats on every near-collapsed fork) **fails**: G-R6@12 passes (3.07), G-R6@24 does not (1.68).
* P2 (|phrasing entropy change| < 0.5 nats) **holds** on every Gemma unit (0.44-0.50 nats; the base is slightly more
  uncertain at ordinary positions; URIAL: the instruct token is the base's top-1 at 91-97% of phrasing positions).
* P3 **fails**: JS at the fork is 4.7-6.6× the mean phrasing JS, but only 0.75-1.18× the JS at base-entropy-decile
  matched positions, i.e. at these forks "fork" ≈ "high base entropy". Cantarero's fork set (base entropy ≥ q0.90)
  reproduces their pattern: JS 11-15× higher inside than outside, rate-matched random ≈ 1.0, and every Gemma
  counterfactual fork falls inside the set.
* P4 **fails** (the instruct argmax differs from the base argmax on a majority of prompts only on G-GRID).
* Llama L-GRID fails the committed on-policy rule (instruct log P(opening) ≈ −13.6 < −5 for all prompts), so it is
  reported descriptively and excluded from the verdict.
* Qwen3-8B iteration-8 gains (carried, tagged): T1 3.27, T10 13.41, T2 2.11, B3 1.84, A3 1.53 nats.

### B2: which components carry the sharpening in Qwen3-8B (verdict **PARTIAL**)

share(X) = Σ_p (m_I − m_X) / Σ_p (m_I − m_B): the fraction of the instruct-minus-base margin gap closed by patching
the base outputs of X into the instruct run at the fork (20 prompts per unit; fixed batch shapes; one-token-path
caches).

| | MST (B3: Kruskal vs Prim) | CC (T10: `find` vs `dfs`/`bfs`) |
|---|---|---|
| gap m_I − m_B (nats) | 2.06 [1.96, 2.16] | 4.52 [3.50, 5.57] |
| FSTACK (10 validated fork-stack nodes) | **1.00** [0.96, 1.04] | **0.45** [0.28, 0.57] |
| F_MLP (5 MLPs) / F_HEAD (5 heads) | 1.08 / 0.17 | 0.41 / 0.30 |
| 50 matched random sets: median / p95 / empirical p | 0.81 / 1.41 / **p = 0.45** | −0.22 / 0.06 / **p = 0.020** |
| R-pure (exp41 top-15 excluded): median / p | 0.66 / p = 0.039 | −0.46 / p = 0.020 |
| SPEC set (task-specification nodes) | −0.02 | −0.17 |
| RS-fork(23) / RS-fork(36) (residual swap at the fork) | 0.78 / 0.57 | −0.05 / 0.15 |
| RS-prefix(23) / RS-all(23) | 0.44 / 1.13 | 0.37 / 0.61 |
| readout decomposition: unembedding-only share (CPU) | 0.43 | **0.85** |
| best single components | MLP L35 0.98, L28 0.62, L29 0.56, L26 0.52 | MLP L30 0.53, L35 0.38, L34 0.26, head L23H10 0.21 |
| W arm (base MLP weights, instruct inputs, 5 MLPs) | 0.23 | 0.38 |
| REV (instruct FSTACK into the base): share opened | −0.30 | 0.22 (p = 0.02) |

* Q1 (FSTACK ≥ 0.5 on both) fails on CC (0.45); Q2 (FSTACK above the random p95) fails on MST — matched random
  late-layer sets close a median 81% of the MST gap; Q3 (SPEC ≤ 0.15) holds. Localisation rule: *distributed* on both.
* The sharpening is **not** written upstream (SPEC ≈ 0) and is carried at the fork by **late MLPs (layers 26-35)**,
  redundantly: several single late MLPs each close about half of the MST gap and FSTACK's joint share is about half
  the sum of its singles.
* A large part of the gap is not in the residual stream at all: the fine-tuned **unembedding** alone accounts for 43%
  (MST) and 85% (CC) of the gap when it reads the base model's own final residual. This is why RS-fork(36) does not
  reach 1 (the plan's confirmation signal failed for this reason; the identity check passes exactly).
* Weight-change profile (S7a, CPU): every module moved by 5-11% (relative Frobenius) in tuning, the unembedding by 9%; but the CC alternative-class rows moved more than almost all rows (' dfs' 12.0%, 91st percentile; ' bfs' 14.4%, 96th) while ' find' moved little (6.6%, 27th) — consistent with the readout carrying most of the CC gap. Per-layer MLP weight change does not track the per-layer CMAP shares (r ≤ 0.2).
* Activation geometry (F8): along PC1 of the block-30 output at the fork (98.5% / 94.6% of the variance of instruct +
  base states), FSTACK-patched states move most of the way from instruct to base; median-random and RS-fork(23) states
  move less.

### B3: held-out condition-node rerun

* Bug confirmed: the original `MeanCache.get` returns `None` for every COND node on every held-out C1forced prompt,
  so iteration 8's held-out arm applied no edit (`mean_d_heldout = 0.0`).
* Fixed by `src/meancache_aligned.py` (interpolates each class prompt's condition-span values to the target span
  length). Layer-0 condition MLP on the 10 held-out prompts: ablate mean d = 3.86 nats (sign-flip p = 0.0625), steer
  (dose 2) mean d = 3.85 (p = 0.023); Holm within the 6-test B3 family 0.22 / 0.12. Iteration 8's pair-prompt values
  were 8.14 / 7.41. MLP L5 reverses sign (ablate −1.50, p = 0.008). Dose 0.5 shows nothing (post hoc).
* Reproduction of iteration 8's pair-prompt value: 8.387 vs 8.291 (|diff| 0.096 > 0.05). Debug: exp41's
  `k3circuit.py` / `k3engine.py` were modified after its validation rows were written; exp41's clean margins
  reproduce exactly (0.0), so ids and positions are right.
* Motif, matched in kind: natural contrasts — Qwen COND 0.08 / DEC 0.34 vs Gemma COND 0.37 / DEC 0.51; forced
  contrasts — Qwen COND 0.01 / DEC 0.62 vs Gemma COND 0.34 / DEC 0.54. The COND share still differs.

### B2 generation: does a one-token intervention change the algorithm the model writes?

N = 30 common-random-number slots per arm (W1-W5 × 6, seeds 9101-9130; T 1; the instruct model's own opening
prefilled; arms differ only at the fork token; every later token is sampled from the unpatched instruct model).
Programs are labelled by the frozen iteration-5/6 labellers (hidden tests + runtime tracer + AST). Predictions were
committed before any token was generated (`predictions/commit1_gen.json`).

| arm (fork token from …) | MST: Kruskal / **Prim** (correct) | CC: union-find / **DFS** (correct) | predicted minority share (MST / CC) |
|---|---|---|---|
| TWIN (instruct) | 29 / **0** (1 disputed) | 29 / **1** | 0.19 / 0.03 |
| FSTACK (base outputs of the 10 fork-stack nodes) | 8 / **19** (3 disputed) | 29 / **1** | 0.66 / 0.06 |
| RAND (median matched random set) | 10 / **19** | 29 / **0** (1 invalid) | 0.59 / 0.00 |
| FPD (base logits at the fork) | 9 / **18** (17 correct) | 12 / **18** | 0.63 / 0.46 |

* MST: FSTACK vs TWIN 19:0 discordant (exact McNemar p = 3.8e-6, Holm 1.1e-5); **FSTACK vs RAND 2:2 (p = 1)**;
  FSTACK vs FPD 6:4 (p = 0.75). One token flips two thirds of the programs to correct Prim, but a matched random
  late-layer set does exactly as well — the same non-specificity as teacher forcing.
* CC: FSTACK changes nothing (0:0), as committed (its 0.45 share of a 4.5-nat gap leaves P(dfs) ≈ 0.06); FPD vs TWIN
  18:1 (p = 7.6e-5). Here the sharpening sits mostly in the unembedding, and only replacing the whole fork
  distribution brings back the base model's alternative.
* TWIN shows 0/30 Prim against a predicted 0.19: the 30 shared fork uniforms include only 2 above 0.81 (expected 5.7), and the instruct CDF puts ' Kr' (lower token id) before ' Prim'; because the uniforms are shared across arms, every contrast is paired on the same draws.
* Predicted vs observed algorithm shares agree (MAE 0.005-0.069 per arm); pass rates 29-30/30 in every arm; no correct
  program is labelled 'other' (none novel; rule-of-three bound 3/237 = 0.013), so no judge was called (USD 0).
* Placebos (re-derivation): swapping the two arms' labels within CRN pairs at random gives median p 0.63-1.0.


## Layout

| path | content |
|---|---|
| `method.py` | stage CLI (`--stages all` or a comma list); every GPU stage runs in its own process |
| `run_qwen.sh`, `run_queue2.sh`, `run_qwen_v2.sh`, `restore.sh` | the shell chains actually used to sequence the GPU stages (one model at a time), and the restore script |
| `src/cfg9.py` | constants, models and revisions, thresholds, utilities, commitment chain |
| `src/s0_preflight.py` | hardware record and sha256-checked vendoring of the read-only inputs |
| `src/units9.py` | `results/units.json`: prompts, template-free ids, openings, fork class tokens |
| `src/stats9.py` | JS (top-256 + tail), share, bootstrap, exact McNemar, sign-flip, Holm, Wilson, Newcombe |
| `src/tests_cpu9.py` | CPU unit tests (`results/tests_cpu.json`) |
| `src/commit9.py` | COMMIT #0 and #0b payloads |
| `src/cmap9.py` | B2 engine: captures, one-token patched forwards, residual swaps, random sets, REV arm |
| `src/b2gen9.py` | B2 generation (TWIN / FSTACK / RAND / FPD), labelling, McNemar |
| `src/b1_9.py` | B1 teacher-forced forks and analysis (Gemma, Llama) |
| `src/b3_9.py`, `src/meancache_aligned.py` | B3 rerun and the interpolating MeanCache |
| `src/analysis9.py` | committed B2 rules, nulls, ranks, readout decomposition, summaries |
| `src/figures9.py` | figures F1-F8 (`figures/*.pdf|png`) |
| `src/rederive9.py` | independent stdlib re-derivation + placebos (`results/rederive.json`) |
| `src/outputs9.py` | `method_out.json` (exp_gen_sol_out) |
| `src/positioning9.py` | dated literature verdicts (`results/positioning.json`) |
| `src/weightdiff9.py` | optional S7a: per-module relative weight change instruct vs base (`results/weight_change.json`) |
| `results/` | per-prompt rows (`b1_tf_*.json`, `b2_tf_*.jsonl`, `b2_rev_*.jsonl`, `b3_heldout_rows.jsonl`), summaries (`b1_summary.json`, `b2_summary.json`, `b2_generation.json`, `b3_summary.json`, `summary.json`), `positioning.json`, `rederive.json`, `deviations.json`, `v1_variable_batch/` (superseded first B2 pass) |
| `predictions/` | committed predictions (`commit0`, `commitB3`, `commit0b`, `commit1_gen`), hardware, model revisions |
| `data/` | generated programs (`samples.jsonl`) and labels (`labels_gen.jsonl`) |
| `vendor/` | sha256-checked copies of iteration 5-8 inputs (`vendor/inputs.json` lists every file) |
| `cache/` | activation caches (~12 GB; regenerable, not published) |
| `method_out.json`, `full_/mini_/preview_method_out.json` | per-example outputs |

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python src/download_models.py          # needs HF_TOKEN with access to Gemma 3 and Llama 3.1
.venv/bin/python method.py --stages all          # ~1 GPU-hour on one 24 GB L4
```

The read-only inputs are vendored under `vendor/` (paths in `vendor/inputs.json`); `src/cfg9.py` only reads the
original run folders when `src/s0_preflight.py` is re-run on the original volume.

## Restoring removed files

`.aii/manifest.yaml` marks three paths `delete`; `restore.sh` rebuilds them:

* `.venv/` (uv environment, ~10 GB) — `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml`
* `cache/` (activation caches, ~12 GB of `.pt` files) — `cd src && ../.venv/bin/python cmap9.py s1 all && ../.venv/bin/python cmap9.py s2 all && ../.venv/bin/python cmap9.py s3 all`
  (needs the model weights below)
* `src/__pycache__/` (Python bytecode) — `python -m compileall src`, or simply rebuilt on import

The model weights are not inside this folder (they live in the shared Hugging Face cache); re-download them with
`.venv/bin/python src/download_models.py` (Qwen/Qwen3-8B b968826d, Qwen/Qwen3-8B-Base 49e3418f,
google/gemma-3-4b-it 093f9f38, google/gemma-3-4b-pt cc012e0a, meta-llama/Llama-3.1-8B-Instruct 0e9e39f2,
meta-llama/Llama-3.1-8B d04e592b).

Everything else (`results/`, `predictions/`, `data/`, `figures/`, `vendor/`, `logs/`) is text, code or small figures
and stays at these relative paths; no file in them exceeds 100 MB, so all of it is in the published repository.

## Deviations and not run

See `results/deviations.json` (each with severity). The main ones: the base_subarm engine check misses 0.05 on some
templates (different GPU in iteration 8; exp41 reproduces exactly on the same L4); the B2 confirmation signal
"RS-fork(36) ≈ 1" failed because the unembedding carries part of the gap (debugged, readout decomposition added); the
first B2 pass used variable batch shapes and was superseded by a fixed-shape rerun (v1 kept as a sensitivity); the
B3 reproduction is 0.096 off because the vendored exp41 engine changed after its rows were written; the self-patch
placebo is ≤ 0.15 nats (head writes cached in bf16), above the 0.02 target. Not run: Llama shortest-path (L-SP), the
optional B2 grid / shortest-path units, S7b (Gemma CMAP; S7a weight-change profile was run), token maps for unmapped base fork tokens; the novelty-audit judges were not
needed (no correct generated program is labelled 'other'). OpenRouter spend: USD 0.
