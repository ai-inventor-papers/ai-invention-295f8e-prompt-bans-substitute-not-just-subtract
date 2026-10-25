# NOV-R: do banned packing rules come back renamed?

When a model is told *"Do not use Best Fit"*, does it stop **using** best fit, or does it only stop **naming** it? This
artifact asks Qwen3 models for one-shot online bin-packing heuristics in the exact FunSearch `priority(item, bins)`
interface. Each program is scored two ways:

* **Lexical compliance (baseline instrument, L1):** no banned rule name or abbreviation anywhere in the extracted
  program (code, comments, docstrings).
* **Mechanistic compliance (proposed instrument):** agreement below 0.95 with every banned rule, where agreement is the
  share of identical bin choices over 2,000 committed probe states (exact behaviour, so it cannot be fooled by names).
  A stochastic matcher handles random fit.

Models: **Qwen3-8B** (no thinking, local vLLM FP8), and **Qwen3-14B** and **Qwen3-32B** (thinking on, OpenRouter with
DeepInfra fp8 pinned). Cells per model: `BASE` (no ban), which fixes each model's own frequency order over six textbook
rules (BF, FF, WF, AWF, LF, RF); `NAME_1..NAME_5`, cumulative name bans of the model's top-k rules on templates W1-W3;
`DESC_5`, a name-free described ban; `HOLD_5`, held-out templates W4/W5 at k = 5; and two novelty instructions
(`INSTR_NEW` "Make a new algorithm.", `INSTR_LONG` "Make a fully novel algorithm never seen before ... 2,000 words").
All thresholds, prompts, verdict rules and the analysis code were hash-committed before any sample
(`predictions/commitments.log`).

## Headline results (1,143 samples; spend USD 1.42)

| | Qwen3-8B (no thinking) | Qwen3-14B (thinking) | Qwen3-32B (thinking) |
|---|---|---|---|
| BASE class mix (VALID) | BF 9, FF 2, other 25 (36/50 valid) | **BF 50/50** | **BF 48/49** |
| NAME_1 (ban BF): L1 / mechanistic | 0.85 / **0.59** (n 41) | 0.93 / 1.00 (n 30) | 0.87 / 1.00 (n 30) |
| NAME_5 (ban top 5): L1 / mechanistic | 0.91 / **0.51** (n 43) | 0.96 / 0.93 (n 27) | 0.88 / 1.00 (n 24) |
| k = 5 gap L1 - mech, paired Newcombe 95% | **+0.40 [0.21, 0.55]** | +0.04 [-0.12, 0.20] | -0.13 [-0.31, 0.04] |
| HOLD_5 gap (held-out templates) | +0.08 [-0.08, 0.24] | -0.13 [-0.31, 0.04] | -0.04 [-0.19, 0.09] |
| Rename rate at k = 1 (lexically clean but still a banned rule) | **14/35 = 0.40** [0.26, 0.56] | 0/28 | 0/26 |
| JT trend of mech. compliance over k (perm. p) | 0.54 | 0.038 (Holm 0.11) | 0.38 |
| INSTR_NEW "Make a new algorithm": classed best fit | 18/42 | **28/29** | **28/28** |

* **P1 (renaming gap): PARTIAL.** The gap is large and significant only for the model without thinking (Qwen3-8B: about
  40-49% of its lexically compliant programs still implement a banned rule, mostly best fit under a new name such
  as "tightest fit" or "minimum remaining space"). The thinking models really do change behaviour under a name ban: their programs leave
  the banned rules (mostly to `other` rules; under a BF ban Qwen3-32B moves to first fit in 14 of 30). Their reasoning
  traces name the banned rule in 100% of cases and self-identify near it in 90-100%. The verdict is the same at class
  thresholds 0.90 and 0.98 and on informative states only (`results/sensitivities.json`).
* **P2 (described vs named ban): DISCONFIRMED** (difference 0.00, 0.00 and +0.03). Only first fit's description passed
  the naming check (each model named the other descriptions "First Fit Decreasing" or the like), so `DESC_5` bans only
  FF, a rule these models rarely use. Compliance is about 1.0 either way, which makes this a weak test.
* **P3 (novel and better is rare): SUPPORTED.** 0 of 1,143 programs beat best fit on both held-out sets (FunSearch
  OR3 and Weibull 5k, 0.8 x BF excess). 186 VALID programs are behaviourally novel against the 426-member published
  corpus (max agreement < 0.9), but none is better. Clopper-Pearson upper bounds are 0.07 per cell at N 50 and 0.12 at
  N 30, so the 2% bound holds as a point estimate only.
* **Novelty instructions do not move the answer:** "Make a new algorithm" returns best fit in 28/29 (14B) and 28/28 (32B)
  programs. Under `INSTR_NEW`, every program that claims novelty is a catalogue rule (>= 0.95) or a corpus heuristic
  (>= 0.9) for the thinking models (4/4 and 11/11), and 6/7 are for Qwen3-8B.
* **Independent re-derivation:** `audit/rederive.py` (stdlib only, separate code path) recomputes every agreement, class,
  lexical flag, cell count, JT statistic and p-value, both Newcombe intervals and all three verdicts, with **0 mismatches**.
  All four placebos fail as required: 600 shuffled-k JT tests give p < 0.05 in 3.8% of cases, randomly swapped flags
  give a mean gap of 0.001, 50 random decision vectors are all classed `other`, and a renamed best fit with a
  "tightest" comment is still classed BF with no lexical hit (`results/rederive.json`).

## Integrity notes (read before using the numbers)

* **Container crash and restart.** The worker container crashed at about 4.2 h (an agent API error). Sampling resumed
  at 5.9 h with one orchestrator and one evaluator behind exclusive lock files (deviation `CRASH_RESTART`). The OpenRouter
  decisive cells use the plan's reduction ladder: **N 30** for Qwen3-14B and Qwen3-32B (31 in Qwen3-32B NAME_1-3) and
  N 50 for Qwen3-8B. All INSTR cells were completed (30 / 50).
* **Duplicate orchestrator (21:21-22:00 UTC).** A kill reached a shell wrapper and left its Python child alive, so two
  samplers ran together (deviation `DUPLICATE_ORCHESTRATOR`). Effects and repairs:
  - 5 duplicate Qwen3-32B BASE rows moved to `data/samples_raw_q32_duplicates_crash_era.jsonl`, keeping the first row
    per slot, which is the one that was evaluated.
  - The first naming-check files mixed empty 96-token replies with genuine ones. A clean rerun (`data/naming_raw_<m>_clean.jsonl`,
    `results/naming_checks_<m>_clean.json`) was committed as `commit3_q14` and `commit3_q32` **before** any Qwen3-32B
    DESC_5 row. Both models give S_desc = [FF], the value used.
  - The payload files of `commit2_q14` and `commit2_q32` were **overwritten after their hashes were logged**, so lines
    2-3 of `predictions/commitments.log` no longer match the files on disk. The chain itself (each line hashing the
    previous one) still verifies, and `commit1`, `commit2_q8` and both `commit3` match. B_1..B_5 (BF, FF, WF, AWF, LF)
    are identical in every version, so the NAME and HOLD cells are unaffected.
* `inputs/inputs_manifest.json` (the committed original, whose sha256 is in commit #1) records run-volume source paths and is not published; `inputs/inputs_manifest_public.json` is the same file with that prefix replaced.
* Other deviations (D1-D9, D9b, naming `/no_think` fallback, 8 evaluation workers, moved stop times) are listed with
  their times and reasons in `results/deviations.json` and `method_out.json` -> `metadata.deviations`.
* One model family only (Qwen3), quantised inference, and samples that are not byte-reproducible. The analysis is
  behavioural only.

## Layout

| Path | What it holds |
|---|---|
| `method.py` | Stage CLI `--stage s0..s12` (setup, harness gate, probes, corpus and instrument gate, commit #1, engines, sampler, evaluator, analysis, P3 audit, outputs) |
| `src/bp.py`, `src/sandbox.py` | FunSearch bin-packing harness and the restricted, rlimited evaluation sandbox (from the iteration-9 workspace) |
| `src/refs.py`, `src/probes.py`, `src/instr.py`, `src/gate_instr.py` | Catalogue references, the P10 probe builder, the behavioural instrument with its RF matcher, and the instrument gate |
| `src/corpus.py` | Published-heuristic corpus (FunSearch c12/c14, EoH, ReEvo, HSEvo, MCTS-AHD, LLM4AD, ab family) and its decision vectors |
| `src/prompts.py`, `src/lexical.py`, `src/extract.py` | Prompts and templates, alias and synonym matching, code extraction |
| `src/sample_local.py`, `src/sample_or.py`, `src/orchestrate.py` | vLLM and OpenRouter samplers, plus the priority-queue orchestrator with budget-403 stop |
| `src/evalq.py` | Evaluation consumer (probes, SEL-OR/SEL-W, held-out H-OR3/H-FSW5k, corpus agreement) |
| `src/analysis.py`, `src/stats.py`, `src/figures.py` | P1/P2/P3, rename and reasoning tables, sensitivities, statistics, and figures F1-F6 |
| `src/judges.py`, `src/positioning_search.py`, `src/outputs.py` | P3 audit (0 candidates, so no judge call), the dated positioning queries, and the output files |
| `audit/rederive.py` | Independent stdlib re-derivation and placebos |
| `predictions/` | `commitments.log` hash chain, commit payloads 1-3, `frozen_code/`, `hardware.json` |
| `data/samples_raw_<model>.jsonl` | Every response with its reasoning trace, tokens, cost and provider |
| `data/eval_rows.jsonl`, `data/decisions.jsonl`, `data/samples.jsonl` | Evaluator rows, decision vectors (integer lists), and one analysis row per sample in the shared schema |
| `data/probes/P10.json`, `data/instances/` | The committed 2,000 probe states and the 14 instance sets |
| `results/` | `cells`, `p1`, `p2`, `p3`, `p3_audit`, `rename_table`, `reasoning`, `sensitivities`, `harness_gate_v10`, `instrument_gate`, `corpus*`, `naming_checks*`, `positioning`, `costs`, `deviations`, `rederive` |
| `figures/F1..F6` | Compliance vs k; class composition; MDS behaviour map in decision space; instrument heatmap; held-out excess; max agreement with banned rules |
| `method_out.json`, `full_/mini_/preview_method_out.json` | exp_gen_sol_out output (datasets `novr_samples`, `novr_cells`, `novr_instrument`, plus all analyses in `metadata`) |
| `inputs/`, `ext/` | Read-only copies of the reused inputs (sha256 in `inputs/inputs_manifest_public.json`) and the pinned corpus files |
| `logs/` | Stage logs, `time_ledger.jsonl`, `throughput.jsonl`, `pip_freeze.txt` |

No kept file reaches 100 MB, so everything listed above is in the published repository. The only deleted bulk is the
virtual environment and `src/__pycache__/` (see below). `vllm_cache/` (125 KB) stays on the run volume and is
recreated by `bash start_vllm.sh`.

## How to run

See `reproducibility.md` for the full sequence. In short:

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r pyproject.toml
export OPENROUTER_BASE_URL=... OPENROUTER_API_KEY=...        # names only; values are yours
.venv/bin/python method.py --stage s1      # harness gate (needs no API)
.venv/bin/python method.py --stage s10     # analysis + figures from the shipped data/
python3 audit/rederive.py                  # independent re-derivation, stdlib only
.venv/bin/python method.py --stage s12     # method_out.json and data/samples.jsonl
```

Re-sampling (`--stage s8` with `--stage s9` beside it) needs the local vLLM server (`bash start_vllm.sh`) and OpenRouter
credit. Committed labels already exist, so a fresh run must start from an empty `predictions/commitments.log`.

## Restoring removed files

| Removed path | Restore with |
|---|---|
| `.venv/` | `uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r pyproject.toml` |
| `src/__pycache__/` | recreated on import, or `.venv/bin/python -m compileall src` |
| Qwen3-8B weights (shared HF cache, not in this folder) | `huggingface-cli download Qwen/Qwen3-8B-FP8 --revision 220b46e3b2180893580a4454f21f22d3ebb187d3` |

`restore.sh` runs the first and last rows.
