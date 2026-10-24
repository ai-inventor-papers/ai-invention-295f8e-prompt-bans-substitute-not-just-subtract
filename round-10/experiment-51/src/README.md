# NOV-B1: evolving online bin-packing rules with an 8B model

FunSearch-style island search on online 1-D bin packing with **Qwen3-8B-FP8** (vLLM 0.11, thinking off) as the
mutator and the iteration-9 FunSearch harness as the evaluator (copied, sha256-verified and re-gated: G-HARNESS PASS,
best fit 5.37% on OR3 and 3.98% on Weibull 5k, c12 3.11%, c14 0.68%, gate block identical to BP9).

Five arms ran in lockstep at matched calls (2,000 per arm and seed, seeds 0 and 1, rounds of 25, lag-1 pipeline,
5 islands per arm-seed):

- **T1.0**: temperature 1.0;
- **T1.6**: temperature 1.6 with top-p 0.95;
- **DTB** (decision-token branching, the proposed operator): force a rank 2-8 token at the highest-entropy code token
  of the first 48 body tokens;
- **RPB**: its random-position placebo;
- **IDEA**: a one-sentence "write a different idea" instruction.

A no-selection arm (**NS**, fixed FF/BF parents, 1,000 calls per seed) ran afterwards. The known-heuristic corpus has
86 priority-form entries: textbook rules, Sum-of-Squares, FunSearch c12/c14, 60 EoH programs, ReEvo, HSEvo,
MCTS-AHD, LLM4AD, the ab family and a tuned ab member. The full 3,843-point ab grid is used as a strict sensitivity.
Every rule, threshold and code hash was committed before the samples it governs (`commitments.log`, 6 hash-chained
commits).

## Results (verdict rules in `predictions/commit1.json`)

| claim | verdict | key numbers |
|---|---|---|
| V1: every core arm's best beats 0.8x best fit on H-FSW5k and H-OR3 | **SUPPORTED** | best per arm, excess %: T1.0 1.53/3.55, T1.6 1.40/3.55, DTB 2.43/4.18, RPB 1.73/3.48 (bars 3.19/4.29). Also: IDEA 1.85/3.38, NS = best fit 3.98/5.37, tuned ab 2.14/3.06 |
| V2: DTB finds >=1.5x the behaviour clusters of T1.0 and T1.6 | **PARTIAL** | clusters over 4,000 calls: T1.0 148, T1.6 373, DTB 446, RPB 212, IDEA 770. R1 3.01 [2.66, 3.43]; R2 1.20 [1.13, 1.33] (fails); R3 2.10. Per-token R2 1.08, rarefied R2 1.15. DTB's best is the weakest on held-out |
| V3: at least one NOVEL rule beating 0.8x best fit | **SUPPORTED, flagged** | 211 candidates, 70 NB, 53 joint clusters, 30 audited. Judge gate unmet (mistral 9/10, deepseek 5/10, kimi 6/10), so the arm-blind manual read decides: 22 reduce to the ab principle; 8 NOVEL, all one idea family (prefer a leftover that is a whole multiple of the item size; from T1.0 2, DTB 4, IDEA 2). Mistral agrees 8/8; advisory majority 5/8 |
| V5 (descriptive): birth tokens | none | reversion 0.40 at birth positions vs 0.36 at controls, sign test p = 0.49 |
| V6: IDEA mostly renames its parents | **PARTIAL** | rename rate IDEA 0.44 vs T1.0 0.86 (difference CI -0.45 to -0.40) |
| evaluator effect | none | NS never beats best fit (5-6 clusters); T1.0 does by call 1,000 |

Caveats:

- There are 2 seeds only, so V2 is a screen without between-run inference.
- The 0.9 probe-agreement filter did no work: permuting the corpus leaves NB at 70 → 70.
- One novel program is stochastic (`np.random.rand`).
- No ablation of the multiple-of-item term was run.
- Every deviation is listed in `results/deviations.json`.

`audit/rederive.py` independently re-derives V1, V2, V3 counts, V6, placebos and the commitment chain
(`results/rederive.json`).

## Layout

- `method.py`: entry point that runs the stages in order (`uv run method.py s0 s1 vllm smoke search ns post judges v5 final`).
- `src/bp.py`, `src/sandbox.py`, `src/gate.py`, `src/fetch_ext.py`: the BP9 harness (exact FunSearch semantics, sandbox, gate, source fetcher).
- `src/s0_verify.py`: hash verification and the v10 gate comparison.
- `src/probes.py`: the 2,000 P1 probe states and their self-checks.
- `src/corpus.py`, `src/dep_scan.py`: the known-heuristic corpus, tuned ab and calibration; the dependency scan.
- `src/prompts.py`, `src/engine.py`, `src/islands.py`, `src/search.py`: prompting, the vLLM client with the DTB/RPB fork logic, FunSearch island semantics, and the lockstep scheduler.
- `src/commit.py`, `src/commit2.py`: the hash-chained commitments and the C* ladder.
- `src/cluster.py`, `src/analysis.py`, `src/postsearch.py`: behaviour clusters, the committed verdict rules, and the post-search stages.
- `src/judges.py`, `src/v3_final.py`, `src/v5.py`, `src/figures.py`, `src/costs.py`, `src/outputs.py`: V3 judges and classes, V5, figures F1-F8, costs and positioning, `method_out.json`.
- `tests/`: the 30 unit tests, the smoke diagnostics and a live engine check.
- `audit/`: arm-blind manual-read aids (`profile_*.py`), `manual_read.json`, `blind_read_sheet.json`, the sealed arm map and `rederive.py`.
- `data/instances/`, `data/probes/`, `data/corpus/`: the 14 instance sets, the probe file, the corpus and the ab grid.
- `data/main/`, `data/ns/`, `data/smoke/`: search rows (`programs.jsonl`), completion token ids and decision vectors (`decisions/*.u16`, uint16, 2,000 per call).
- `results/`: all analyses (`v1.json` … `v6.json`, `v3_final.json`, `clusters.json`, `judge_*.json`, `placebos.json`, `rederive.json`, …).
- `predictions/`: `commit1.json` … `commit6.json`, `thresholds.json`, `hardware.json`.
- `figures/`: F1-F8 (PDF + PNG).
- `ext/`: pinned external sources (FunSearch notebook, EoH runs, ReEvo, HSEvo, MCTS-AHD, LLM4AD, OR-Library, arXiv 2510.27353).
- `method_out.json`, `full_method_out.json`, `mini_method_out.json`, `preview_method_out.json`: exp_gen_sol_out output.
- `reproducibility.md`: the exact commands, versions, hardware and expected numbers.

## How to run

See `reproducibility.md`. In short:

1. `uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r pyproject.toml`.
2. Download Qwen/Qwen3-8B-FP8 at revision `220b46e3`.
3. Set `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY` for the judges.
4. Run `uv run method.py <stages>`.

Every analysis after the search is deterministic given `data/main/` and `data/ns/`. To re-check the headline numbers,
run `.venv/bin/python audit/rederive.py`.

All kept artifacts stay where they are in this folder, at the relative paths above. None is 100 MB or larger, so all
of them are published.

## Restoring removed files

- `.venv/` (deleted, regenerable):
  `uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r pyproject.toml`
- `vllm_cache/` (deleted, regenerable): `bash start_vllm.sh`. vLLM and Triton rebuild their caches on the first start;
  the model itself is restored with
  `huggingface-cli download Qwen/Qwen3-8B-FP8 --revision 220b46e3b2180893580a4454f21f22d3ebb187d3`.
- `src/__pycache__/` (deleted, regenerable): `.venv/bin/python -m compileall src`. It is also rebuilt by any run.
