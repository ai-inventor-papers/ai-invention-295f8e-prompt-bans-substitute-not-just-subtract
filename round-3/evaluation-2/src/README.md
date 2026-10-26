# Fixing the record and auditing novel code (iteration 3, Step 0)

CPU-only evaluation for an AI Inventor study of how prompt-level algorithm bans move a code model's algorithm choice
(Qwen3-8B, with Llama-3.1-8B-Instruct as the second family). It generates nothing and does no GPU scoring. It repairs
the iteration-2 record from data already on disk, and it answers the novelty question from data. The only paid calls
are blind LLM judges (USD 0.42).

Every number cites its source as `<artifact_id>:<relative path>`, for example `art_6zBfl3kDjeiP:results/c1.json`.
Dependencies are read in place and read-only. `common/paths.py: dep_root()` looks for each one first in
`$AII_DEPS_ROOT/<artifact_id>`, then in the sibling folder `../<artifact_id>` (the published repository), and finally
in the AI Inventor run-volume layout, relative to this folder. Nothing heavy is copied in. The exp9 activation states
(0.95 GB) stay on the run volume. Exact reproduction steps are in `reproducibility.md`.

## What the evaluation found

**(0a) C1 cannot be decided with the current likelihood instrument.**

- *Argmax test.* Over 17 sampled single-ban events in Qwen, the argmax of the likelihood gain, full or residual, picks
  the substitute the model actually writes in **0/17** events (chance about 0.22). The argmax of the implied ban-cell
  mass picks it in **14/17** (8/8 for modal bans).
- *Estimable-mass restriction.* No ban row keeps three survivors that have at least 1% mass and an ESS of at least 5
  (**0 of 11** rows), which is the result predicted before computing.
- *Bootstrap against replicate noise.* On Qwen the two-stage bootstrap variance of Gbar is **2.7×** the replicate
  noise term that the frozen correction used (median; range 1.2–4.3; one-stage 1.6). For Llama, exp10 reports 4.8–11.3×.
- *AIM bias.* The mention-reference AIM is biased negative by construction: the null mean is −0.27 to −0.33.
  - Llama's −0.28 sits at the null's 66th percentile, so the bias explains it fully.
  - Qwen's −0.595 still lies below the null's 1st percentile.
- *ESS-weighted share.* The 1.24 "share" is impossible as a proportion, because the noise-corrected V_u is −35.4.
- *Cost of a mass-level C1.* The plug-in lower bound is M5 ≈ 50 programs per algorithm. The lognormal extrapolation is
  about 10³¹ programs, and 22% of the pooled PSIS k-hat fits are above 0.7. Separating SHARE from 0.5 by 0.10 would need
  about 129 Qwen events or 43 Llama events. The decision therefore moves to sampled landings on a bench.

**(0b) Manifold.**

- *Figures.* exp9 shipped 13 Isomap figures, not the 14 claimed. They are copied to `figures/exp9/`.
- *Re-derivation.* The recomputed geometry reproduces exp9: the centroid matrix matches to within 1e-7, and the
  nearest-neighbour maps agree in 24 of 24 settings.
- *BFS–bidirectional BFS adjacency.* At the label-independent g16 position it **does not survive**. The pair is
  nearest, but permuted labels reproduce that with p = 0.19. The two clouds are not separable: the centroid distance is
  0.96 of the within-class spread, and the exchangeability test gives p = 0.48.
- *Persistent H1.* There is no loop at either position.
  - At 'pre' the planted-loop power is 1.00. That position partly encodes the label.
  - At g16 the power is only 0.04, so "no circle" is powered only at the label-confounded position.

**(0c) Novelty audit.**

- *The answer.* There are 78 unique correct out-of-catalogue programs across the 11 declared artifacts and the exp3
  pools copy. **None is a novel algorithm.** That is the call of two blind judges from different families with a
  tie-break, confirmed by a manual read of every program. The rule-of-three bound is 3/78 = 0.038.
- *Judges.* Agreement between the two judges is only fair: Cohen's kappa 0.38 [0.31, 0.45]. gpt-4.1-mini over-calls
  NOVEL on broken, failing code.
- *Controls.*
  - Positive controls fail the strict gate: 7/10 came back LABELLER_MISS with the right name. All 10 were named
    correctly by both judges.
  - Negative controls pass 5/5.
  - No control was called NOVEL.
- *TOP ban.* TOP's 0.13 not-banned share consists of 12 degenerate failing programs and 1 correct unit-weight Dijkstra.
  It is not avoidance into a non-banned catalogue algorithm.

**(0d) Llama, correct programs only.**

- Every quoted composition reproduces exactly.
- On T1, Llama's correct programs are all BFS (20/20; Hill_cc 1.00, against Hill_all 1.87). Its apparent diversity on
  T1 is failing code.
- On the bench, Llama is more diverse than Qwen on 9 of 13 tasks at equal depth (10 programs).

**(0e) Knob table.**

- 306 rows were rebuilt (276 without exp5), against the audit's 249.
- Under the declared class rule, no KNOB row costing fewer than 20 pass points reaches a rarefied Hill-1 of 2 at
  depth 25.
- The best is exp6's semantic seed on T2: **1.940** [90% 1.770, 2.094] at 7 pass points. Its interval includes 2.

**(0f) Positioning.** 12 of 12 rows are verified on 2026-10-20 against verbatim quotes.

**(0h) Corrections.** `corrections.json` holds 12 record items, each with its old wording, the recomputed numbers and
their sources, and a replacement sentence. It also holds a table of 19 reproduction targets quoted in the record:
16 reproduce. The 3 that differ each carry their cause: the knob-table row count, the 14 claimed
figures, and DFS as the mode in 5 of 5 draws rather than 4 of 5. Among those that reproduce, the iteration-1
five-draw counts come out at Bellman-Ford/SPFA 272/272 and DFS 116/128.

**Audit.** `audit/rederive.py` re-derives the headlines independently: **72/72** checks pass, and all **7/7** placebo
tests fail as required. It recomputes from the raw files, with its own code:
- event landings and argmax hits, including the implied mass from exp7's `frlp_cells.jsonl`;
- the rows kept under the mass restriction;
- the noise terms and the variance-ratio arithmetic;
- a re-simulated AIM null;
- cell-by-cell plug-in M5;
- g16 separability, nearest neighbour and the H1 lifetime;
- the out-of-catalogue count, the novel count, kappa and TOP avoidance;
- every Llama Hill_cc;
- the top-5 knob Hills and pass points;
- the positioning quotes.

Not re-derived independently:
- the 2,000 bootstrap draws behind the variance ratios, which are checked only against exp7's noise terms;
- the split-half AIM null;
- the lognormal M5 and the PSIS k-hat;
- the manifold N2 permutation p and the planted-loop power;
- the knob bootstrap intervals.

## Layout

| Path | What it is |
|---|---|
| `eval.py` | Entry point; runs every section, or one with `--section` (judge calls are cached). |
| `common/paths.py` | Dependency map (artifact id → relative path), JSON I/O, code-hash key. |
| `common/rows.py` | Normalises every per-program record of the origin files to one schema; label map. |
| `common/stats.py` | Wilson/Newcombe intervals, Hill (plug-in, Miller–Madow, rarefied), kappa, Kish ESS, PSIS k-hat. |
| `sections/s0_inventory.py` | S0: `inputs/inventory.json` (bytes, sha256, rows, keys per file), `tables/label_map.csv`. |
| `sections/s0a_c1.py` | (0a) C1 diagnostics: event table, implied-mass C1, bootstrap/replicate, AIM null, M arithmetic. |
| `sections/s0b_manifold.py` | (0b) exp9 figures, implemented counts, g16 geometry, N1/N2/N3 nulls, persistent H1, power. |
| `sections/s0c_novelty.py` | (0c) selection, controls, blind judge prompts and async calls (budget-capped). |
| `sections/s0c_final.py` | (0c) final classes, kappa, controls, novelty answer, multi-ban avoidance with 'other' kept separate. |
| `sections/s0d_llama.py` | (0d) Llama correct-only compositions and Hill numbers. |
| `sections/s0e_knob.py` | (0e) knob table, class rule, references, reproduction table. |
| `sections/s0f_positioning.py` | (0f) dated positioning rows, re-verified against the saved pages in `results/web/`. |
| `sections/s0h_corrections.py` | (0h) `corrections.json`. |
| `sections/assemble.py` | `full_eval_out.json`, `mini_eval_out.json`, `preview_eval_out.json` (exp_eval_sol_out). |
| `vendor/exp7/` | exp7's `config.py`, `frlp.py`, `c1.py`, vendored so C1 cells are rebuilt exactly; only `config.py` is path-patched. |
| `audit/rederive.py` | Independent re-derivation (no project imports) and the placebos → `audit/rederive_report.json`. |
| `audit/selection.jsonl`, `audit/selection_commit.txt` | Novelty selection, hash-committed before any judge call. |
| `audit/judge_cache.jsonl` | Every judge response with its cost (kept; re-running costs money). |
| `audit/manual_pass.jsonl` | Executor's manual pass: all 78 Set A programs, plus 112 Set B disagreement, NOVEL and TOP programs. |
| `results/*.json` | Per-section outputs (`c1_diagnostics`, `manifold`, `novelty_audit`, `llama_correct_only`, `knob_table`, `positioning`, ...). |
| `tables/*.csv` | Argmax vs landing, M arithmetic, manifold counts and grid, novelty audit and class counts, corrected multi-ban avoidance, knob table with class and reference maps, Llama, positioning, label map. |
| `figures/argmax_vs_landing.{pdf,png}` | Hit rate of each likelihood argmax on the realised landing (Wilson 95%); `figures/make_figures.py`. |
| `figures/knob_ranking.{pdf,png}` | The ten best KNOB rows under 20 pass points; rendered from `figures/knob_ranking_spec.json` (aii-data-fig-gen) written by `figures/make_knob_spec.py`. |
| `figures/exp9/` | The 13 exp9 manifold figures and 2 k-stability figures, as found. |
| `corrections.json`, `deviations.json` | 12 record corrections; 12 deviations from the plan. |
| `reproducibility.md`, `pyproject.toml`, `uv.lock`, `requirements.lock.txt`, `install.sh` | Step-by-step reproduction and the exact pinned environment (51 packages). |
| `eval_out.json` (= `full_eval_out.json`; also `mini_`/`preview_`) | Main output: 72 metrics, 7 datasets (c1_events, novelty_audit, knob_table, llama_correct_only, manifold_grid, positioning, corrections). |

## How to run

```bash
./install.sh                                   # uv venv + pinned packages (CPU only)
uv run eval.py --section no_judges             # every section except the paid judge calls (~3 min)
uv run eval.py --section judges                # judge calls; reuses audit/judge_cache.jsonl, so only missing calls are made
uv run audit/rederive.py                       # independent re-derivation + placebos
uv run eval.py --section assemble              # re-assemble with the re-derivation report included
```

The judge run needs `OPENROUTER_API_KEY` and `OPENROUTER_BASE_URL`. It stops at a spend of USD 1.30, and stops at the
first "AI Inventor per-run OpenRouter budget" refusal. The manual pass is in `audit/write_manual_pass_A.py` and
`audit/write_manual_pass_B.py`; the code was read with `audit/dump_for_manual_pass.py` and `audit/dump_setB.py`.

## Restoring removed files

| Removed path | Restore with |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r requirements.lock.txt` (or `./install.sh`) |
| `**/__pycache__/` | Recreated automatically on the next `uv run eval.py ...` |

Nothing else is deleted. The dependencies are not copied in. A fork reads them from sibling folders named by artifact
id (`../<artifact_id>`), from `$AII_DEPS_ROOT/<artifact_id>`, or from the AI Inventor run volume; see
`reproducibility.md`.
