## Design (what was run)

**Model and decoding.** Qwen3-8B, revision `b968826d9c46dd6066d109eabc6255188de91218`, thinking off, T = 1.0, top-p 1,
no top-k. A row stops at end of turn or at the closing fence of its first code block (exp20's fence stop); at most
1,024 new tokens on T03/T10 and 1,536 on T2/T1. **Precision W16A16**: bf16 weights and bf16 activations in HF
transformers 4.57.6 (attention `sdpa`) on one NVIDIA L4 (22 GiB usable). Every edit is computed in fp32 and cast to
bf16. This label is on every row (`precision: "W16A16"`). Nothing here crosses precisions inferentially; the
iteration-4 FP8 cells are set beside these ones only descriptively (`results/fp8_vs_bf16_sites.json`).

**Prompts.** These are the neutral twins of exp17's ban prompts, as exp20 used them (5 templates W1-W5 per task). The
condition sentence names a neutral noun, padded with ` .`. It is followed by the fixed task specification and the
chat tail. Every prompt is re-rendered through the chat template and must reproduce exp20's ids and sha256.
Ban prompts enter only as forward passes, to measure r_Q. U7 checks that none is ever sampled.

**Sites.** Every edit is displacement-targeted: `h <- h + (target - (h - h_twin).u) u`. The displacement from the
clean twin along `u` therefore equals the target exactly at every hooked block and position. The dose is the
**ban-free unit** `n[l,p] = ||h_twin[l,p]|| x r_Q(l)`. Here r_Q(l) is the median ban displacement ratio: exp23's
frozen value at blocks 12-23, and a bf16 recomputation by exp23's recipe at blocks 0-11 and 24-35. The calibration
ratio at blocks 12-23 is 0.952, inside [0.9, 1.1], so no rescaling was applied. Sites:

| Site | Blocks | Positions | Per-position target |
|---|---|---|---|
| S0 | 12-23 | task spec S | alpha x n[l,p] |
| S4 | 0-11 | S | alpha x n[l,p] |
| S5 | 24-35 | S | alpha x n[l,p] (the block-35 edit is a no-op, U5) |
| S1 | 12-23 | read position R = P-1 | alpha x n[l,R] |
| S1E | 12-23 | R | alpha x c x n[l,R], c = sqrt(sum_{l,S} n^2 / sum_l n[l,R]^2): energy-matched to S0 |
| S2 | 12-23 | condition sentence COND (every token) | alpha x n[l,p] |
| S3 | 12-23 | generated input positions 1-32, against a teacher-forced shadow row | alpha x n_G[l] |
| TOP5 | 12-23 | S | per-block push u_push[l] = unit(mean survivor centroid - mean banned centroid) |
| TOP3 | 12-23 | S | the same push for the T03 top-3 variant |

**Directions and common random numbers.** Slot (t, w, k) has one random direction,
`u = normalise(PCG64(stable_seed('ITER6_S2', t, w, k)).standard_normal(4096))`. This namespace is new: its maximum
|cos| with every earlier direction file is 0.069 (`directions/seeds.json`). It is shared by every site and dose.
Slot (t, w, k) also has exp17's token uniforms u_stream(t, w, k). Every site contrast is therefore an exact paired
flip on the same slot. Batches have a fixed shape (16 rows on T03/T10, 12 on T2/T1) and hold one (task, template).
Finished rows are fed `<|im_end|>`. Under that shape a row's tokens do not depend on its batch-mates (U1).

**Cells.** Twins N = 50 (k 0-9). On T03 and T10 the sites S0, S4, S5, S1, S2 and S3 run at alpha 1, 2 and 4, N = 30
each (k 0-5), plus S1E. On T2 the same sites (and S1E) run at alpha 2 and 4. The S-d pushes run at alpha 1, 2 and
4, N = 50: T03 top-5, T03 top-3, T10 all-but-one and T1's iteration-4 u_top5. T1 also gets its twin and an S0
random control at the same per-position unit. The outcome-blind extensions are S4 at alpha 8 and a top-up of the
P2 cells to N = 50 (k 6-9). The positive control U8 replays exp25's ECBAN cells (rand_9002 on T03 and rand_9004
on T2, alpha 1, exp17's FP8 ban unit, 50 slots each).

**Order of operations.**
1. CPU: input copies and hashes, then the CPU tests.
2. GPU prep: positions, r_Q, units, forced states, banned sets, push directions, push progress, memory probe.
3. GPU tests U1-U6, then the positive control U8, then smoke slots (k >= 100).
4. Commit #1 (rules, cells, sets, units, directions, predictions).
5. Decisive sampling in priority order. The label worker runs alongside it.
6. F2 scoring passes.
7. Commit #2 (final analysis code), then the analysis, the novelty audit, the figures, the outputs and the
   independent re-derivation.

## Layout

| Path | What it is |
|---|---|
| `method.py` | Orchestrator, one sub-command per stage (`uv run method.py <stage>`; see its docstring). |
| `src/cfg.py` | Frozen constants (tasks, defaults, sites, blocks, alphas, slots, batch shape), paths, JSON/hash helpers. |
| `src/engine_w16.py` | W16A16 HF engine: batch-1 prefill with edit hooks, CRN inverse-CDF sampler, fence stop, S3 shadow site, teacher-forced scoring, thinking sampler. |
| `src/hooks.py` | The displacement-targeted edit (exp20's maths) and its batched form. |
| `src/sites.py` | Per-(task, template) context, ban-free units, site targets, directions, row prefill with displacement logging, fixed-shape batches. |
| `src/prompts.py` | Prompt loading and re-render check, COND/S/R spans, forced named and masked prompts for the S-d manifold. |
| `src/schedule.py` | Cells, execution priorities (drop order), fixed-shape batch packing with TWIN_X fillers. |
| `src/gpu_main.py` | GPU driver: prep, tests (U1-U8), decisive sampling with timing extrapolation. |
| `src/geometry.py` | Implemented counts, banned sets, push directions, push progress, k-NN geodesics, MDS, edge test. |
| `src/decide.py`, `src/stats.py` | Committed decision rules (S-a, S-b, S-c, F1, F2) and their statistics. |
| `src/label_worker.py`, `src/label_k7.py` | Frozen gated labellers (exp20's), and exp9's K=7/extended T1 labeller. |
| `src/scoring.py` | F2 teacher-forced q_lik / margin passes on 15 tasks, and the thinking-on T2 margin. |
| `src/analysis.py` | Every analysis: cells, S-a, S-b, S-c, landings, dose axis, F1, F2, S-d, engine checks, FP8 comparison. |
| `src/audit.py`, `src/audit_rows.py` | Novelty audit (exp20's module): stress tests, known-solution index, blind judges, controls. |
| `src/figures.py`, `src/outputs.py` | Figures and `method_out.json`. |
| `src/prereg.py`, `src/commit.py` | Input hashes, direction seeds, commits #1/#2 (hash chain in `commitments.log`). |
| `tests/test_cpu.py` | CPU unit tests (all 9 pass; `results/unit_tests_cpu.json`). |
| `audit/rederive.py` | Independent re-derivation of the headlines with placebos (`results/rederive.json`). |
| `inputs/` | Read-only copies of every earlier-artifact file used, with `inputs/SHA256SUMS` (572 files). |
| `data/samples_raw.jsonl`, `data/labels.jsonl`, `data/labels_k7.jsonl`, `data/samples.jsonl` | Raw rows, labels, T1 K=7 labels, merged rows (the row schema of the plan). |
| `data/row_logs/` | Per-cell fp32 arrays: per-position displacement at the last hooked block, post-edit S-means (blocks 18, 23). |
| `units/` | r_Q for all 36 blocks, ban-free units per task. |
| `directions/` | Push directions, the T1 bf16 rebuild, the seed registry. |
| `cache/` | bf16 twin states (all blocks; S, R, COND), forced-prompt states, push states, code-opening states. Kept on the run volume (files >= 100 MB are not published). |
| `predictions/` | Commit #1 content (`s_commit.json`, `banned_sets.json`). |
| `results/` | Every analysis JSON; `figures/` the figures. |
| `method_out.json` (+ mini/preview) | exp_gen_sol_out output. |

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python method.py inputs && .venv/bin/python method.py cputests
.venv/bin/python method.py prep && .venv/bin/python method.py seeds && .venv/bin/python method.py gputests
.venv/bin/python method.py commit1
.venv/bin/python method.py sample --deadline-unix <unix time> &      # decisive sampling (GPU)
(cd src && ../.venv/bin/python label_worker.py follow) &              # labels alongside
.venv/bin/python method.py score && .venv/bin/python method.py label   # F2 passes; K=7 labels for T1
.venv/bin/python method.py commit2 && .venv/bin/python method.py analyse
.venv/bin/python method.py audit && .venv/bin/python method.py audit_summary
.venv/bin/python method.py figures && .venv/bin/python method.py outputs
```

The Qwen3-8B weights come from the Hugging Face cache (`huggingface-cli download Qwen/Qwen3-8B --revision
b968826d9c46dd6066d109eabc6255188de91218`). The declared dataset dependency (art_j3Rm_lr2nzR6,
`full_data_out.json`) is read in place to rebuild the known-solution index. Set `ART_J3RM_DIR` to its folder.

## Restoring removed files

| Removed path | How to restore |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` |
| `src/__pycache__/`, `tests/__pycache__/` | regenerated automatically on the next run |

Everything else is kept. `cache/` and `data/row_logs/` stay on the run volume, at the paths they already have. Files of
100 MB or more (the four `cache/twin_states_*.pt`) are not in the published repository. Rebuild them with
`.venv/bin/python method.py prep` (about 1 GPU-minute).
