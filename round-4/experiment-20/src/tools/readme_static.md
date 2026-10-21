## Design (what was run)

**Model and decoding.** Qwen3-8B, revision `b968826d9c46dd6066d109eabc6255188de91218`, thinking off, T = 1.0,
top-p 1, no top-k, at most 1,024 new tokens. A row stops at end of turn or at the closing fence of its first code
block. Precision follows the rule frozen in commit #0: on this 16 GB RTX 2000 Ada (compute 8.9) the decoder
linears run in FP8 W8A8 (exp17's engine). Embeddings, norms and lm_head stay bf16. Every arm uses the same precision.

**Prompts.** These are the neutral twins of the exp17 ban prompts. Each twin has a condition sentence, then the fixed
task specification, then the chat tail. In the condition sentence the banned name is replaced by a neutral noun,
padded with ` .` to the ban's token length. There are 5 templates (W1-W5) per task. Tasks and their defaults: T03
k-th smallest (full sort), T05 two sum (hash map), T06 find duplicate (hash set), T10 connected components
(union-find), T1 grid path (BFS), T2 weighted shortest path (Dijkstra). No ban prompt is ever sampled. Ban prompts
enter only as forward passes, to measure the units.

**Sites.** Every edit is displacement-targeted: `h <- h + (target - (h - h_twin).u) u` in fp32, cast to bf16. The
displacement from the clean twin along `u` therefore equals the target exactly at every hooked block and position.

| Site | Blocks | Positions | Per-position target (alpha x unit) |
|---|---|---|---|
| S0 | 12-23 | task spec S | alpha * n_S[l,k] |
| S1 | 12-23 | read position R = P-1 | alpha * n_R[l] |
| S2 | 12-23 | condition span COND | alpha * n_C,w[l,p] (zero on frame tokens before the noun) |
| S3 | 12-23 | generated input positions 1-32 (vs a teacher-forced shadow row) | alpha * n_G[l] |
| S4 | 0-11 | S | alpha * n_S[l,k] |
| S5 | 24-35 | S | alpha * n_S[l,k] (the block-35 edit is a no-op by construction, U7) |
| S1E / S2E | 12-23 | R / COND | S1 / S2 target x the energy-matching scalar c |
| TOP5 (T1) | 12-23 | S | per-block u_top5[l] (mean survivor centroid - mean TOP5 centroid) |

**Units** (`units/units_<task>.npz`). n = ||h_ban - h_twin|| per block and position, averaged over W1-W5 for S and
R and per template for COND. n_G[l] = mean over k of n_S[l,k]. Relative units are n / ||h_twin||.
`results/units_summary.json` reports them per site.

**Directions and common random numbers.** Slot (t, w, k) uses one random direction:
u = normalise(PCG64(stable_seed('PN4', t, w, k)).standard_normal(4096)). It is shared by every site, every dose and
the boundary arm. Slot (t, w, k) also uses the exp17 token uniforms u_stream(t, w, k). Every site contrast is
therefore an exact paired flip. Batches are fixed at 20 rows of one (task, template), and finished rows are fed
`<|im_end|>`. Under that shape a row's tokens do not depend on its batch-mates (GPU test U1).

**Cells.** Twin: N = 50 (k 0-9). S0-S5 at alpha 1, 2 and 4: N = 30 each (k 0-5). S1E and S2E at alpha 1: N = 30.
S0 at alpha 8: N = 50. TOP5 at alpha 1, 2 and 4 on T1: N = 50, with S0 topped up to N = 50 on T1 as the random
control. Engine check: T03 rand_9002 and T2 rand_9004 at alpha 1, N = 50 each. In total, 4,510 programs plus 540
shadow rows plus 150 filler twin rows (`TWIN_X`, descriptive only).

**Order of operations.** CPU tests, then GPU prep (positions, units, C3d geometry), then GPU tests U1-U7, then the
screen file, then commit #0, then the engine check, then smoke (slots k >= 100), then commit #1 (predictions, rules,
hull + decision code), then decisive sampling (priority P1-P9). The label worker runs alongside sampling. Then the
K=7 labels, commit #2 (analysis code), the analysis and the novelty audit. Last come the executor's manual pass, the
re-derivation and the outputs.

## Layout

| Path | What it is |
|---|---|
| `method.py` | Orchestrator, one sub-command per stage (`uv run method.py <stage>`; see its docstring). |
| `src/cfg.py` | Frozen constants (tasks, defaults, sites, blocks, alphas, slots), paths, JSON and hash helpers. |
| `src/engine.py` | FP8 W8A8 Qwen3-8B engine (exp17) with the CRN inverse-CDF sampler, the fence stop and the S3 decode-time site with shadow rows. |
| `src/hooks.py` | The displacement-targeted prefill edit used by every prefill site. |
| `src/prompts.py` | Prompt loading and re-render check, COND/S/R spans, forced T1 prompts and TOP5 ban segments (C3d). |
| `src/gpu_main.py` | GPU driver: hardware and precision rule, units, C3d geometry, GPU tests, engine check, staged sampling. |
| `src/schedule.py` | Cells, priorities and fixed-shape batch packing (atomic S3 hooked/shadow pairs). |
| `src/screen.py` | STEP 6 screen file (canonical JSON + sha256). |
| `src/prereg.py`, `src/predictions_spec.py`, `src/commit.py` | Commits #0/#1 and the sha256 hash chain (`commitments.log`). |
| `src/label_pipeline.py` | Frozen labellers (exp11 bench, exp8 suite) with judge on disagreement; follows the raw rows. |
| `src/label_k7.py` | exp9 extended / K=7 labeller for every T1 row (C3d). |
| `src/hull.py` | Rarefied Hill, randomisation hull (H5, P15, P20) and the C1-site decision rule (committed in #1). |
| `src/analysis.py` | STEP 11: cells, hull bootstrap, C1-site, failure modes, paired flips, transmission, pooled model, boundary, engine check, C3d scoring, units summary. |
| `src/audit.py` | STEP 12: known-solution index (+T05), stress tests, judge controls, blind judges + tie-break, summary; dependency usage. |
| `src/recheck.py` | STEP 0.1: inputs SHA256SUMS, bench vs commitment, labeller re-check on references and gold sets. |
| `src/figures.py`, `src/outputs.py`, `src/finalize.py` | Figures, `method_out.json`, deviations/timing/commit-order audit. |
| `audit/rederive.py` | Independent re-derivation of the headlines and three placebos (separate code path). |
| `audit/rederive_headlines.py` | Second re-derivation from raw files with different methods (Mantel-Haenszel, hand McNemar) and placebos. |
| `reproducibility.md` | What was actually run, in order, with hardware, seeds, runtimes and the numbers a rerun should give. |
| `audit/manual_pass.jsonl` | The executor's manual verdict on every stress-passing audit program. |
| `audit/novelty_audit_pool.json` | Audit pool with stress results, judge and tie-break verdicts and nearest known solutions. |
| `tests/test_cpu.py`, `tests/u4_diagnostic.py` | CPU unit tests T1-T5; the U4 follow-up diagnostic (GPU). |
| `tools/` | `overlap_check.py` (STEP 11.10, runnable later), `tables.py` (README tables), `manual_view.py`. |
| `inputs/` | Read-only copies of every earlier-artifact file this run reads (`inputs/SHA256SUMS`). |
| `units/`, `directions/` | Per-site units; u_top5 and the plan-site geometry (PCA-50 points, centroids). |
| `predictions/` | Commit #0 protocol, commit #1 predictions, frozen forced-prompt list. |
| `data/samples_raw.jsonl` | Every generated row (text, token ids, finish reason, realised displacement, first-token KL). |
| `data/labels.jsonl`, `data/labels_k7.jsonl` | Labels (label, passed, runtime/AST/judge labels, code); K=7/extended labels for T1. |
| `data/row_logs.jsonl` | Per-row displacement logs (R at blocks 12-35, along-u and total at the site, S3 step-wise KL/displacement). |
| `data/known_solutions.jsonl` | Known-solution index rebuilt from the dataset dependency (472 + 42 T05 rows). |
| `results/` | All analysis JSON (see the results section), timing, tests, costs, deviations. |
| `figures/` | fig1-fig7 (PDF + PNG). |
| `method_out.json`, `full_/mini_/preview_method_out.json` | Final output (exp_gen_sol_out schema, validated). |
| `pyproject.toml`, `uv.lock` | Pinned environment (Python 3.12; torch 2.8.0, transformers 4.57.6, the exp17 pins plus ijson). |
| `commitments.log` | sha256 hash chain of every pre-registered and final file (commits #0-#4). |
| `restore.sh`, `.aii/manifest.yaml` | Restore commands; the manifest marks the regenerable caches (`.venv/`, `__pycache__/`) for deletion (everything else is text or small and always kept). |

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
export HF_HUB_CACHE=...            # holds Qwen/Qwen3-8B at the pinned revision
export ART_J3RM_DIR=...            # folder with the dataset dependency's full_data_out.json (audit index only)
export OPENROUTER_BASE_URL=... OPENROUTER_API_KEY=...   # labelling judge on disagreement, novelty audit
uv run method.py tests-cpu && uv run method.py screen
uv run method.py gpu &             # waits for commit #0, then for commit #1 before decisive sampling
uv run method.py commit0           # after GPU prep wrote units/ and results/hardware.json
uv run method.py commit1           # predictions + decision code
uv run method.py label &           # label worker
uv run method.py k7 && uv run method.py analysis --boot 2000 --workers 5
uv run method.py audit && uv run python tools/manual_view.py --neigh   # then write audit/manual_pass.jsonl
uv run method.py audit-summary && uv run method.py deps && uv run method.py rederive
uv run method.py u4 && uv run method.py figures && uv run method.py outputs
```

A GPU with FP8 support (compute capability >= 8.9, >= 16 GB) is required for the engine as written.
