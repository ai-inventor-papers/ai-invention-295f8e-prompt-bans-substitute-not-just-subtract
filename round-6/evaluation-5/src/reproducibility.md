# Reproducibility: iteration-6 record repair and second novelty check

This file describes what was actually run to produce the outputs in this folder. Every path below is relative to this
folder.

## 1. Get the artifact

The workspace is published as one folder of a public GitHub repository:

```bash
git clone <repository URL>
cd <repository>/<this artifact's folder>
```

### Dependency artifacts

The inputs produced by other artifacts are read from their own folders. The published repository holds them as
sibling folders of this one, and the code looks each one up by its artifact id. All of these are declared
dependencies:

| Artifact id | What is read |
|-|-|
| `art_jR6Pyy3W9xum` (bf16 knob experiment) | `results/{unit_ratio,cells,prices,bootstrap,literal_cell,pn_vs_dmd,claim_c,knob_table,vllm_engine}.json`, `data/labels.jsonl`, `src/gen5.py`, `src/analysis_c.py` |
| `art_mWn-MQEnNelg` (8-bit plan-noise experiment) | `results/{alpha_sweep,c1,prices}.json`, `data/labels.jsonl`, `src/engine_v4.py`, `src/cfg.py` |
| `art_SHaWv77P1XCI` (site experiment) | `results/{escape,c3b,units}.json` |
| `art_CcZLW-9NX00l` (transplant) | `results/{novelty_audit,base_repertoire,screen_check}.json`, `inputs/exp11/bench/` (specs, tests, checkers, references, forced programs), `inputs/eval2/common/stats.py` |
| `art_8WbrpoEFslk9` (panel A) | `pooled_inputs.json`, `results/{a2,a2_assoc_corrected,extra_arm_a,knob_rows,repertoire_check}.json`, `newbench/*/tests.jsonl` |
| `art_9a8LrIv2lHbV` (panel B) | `pooled_inputs.json`, `results/{a2_panel,rivals,repertoire_check,unit_outcomes}.json`, `units/*/tests.jsonl` |
| `art_hG0QPiaIPNhP` (Gemma) | `results/{e_a2,e_a1,predictors}.json` |
| `art_ccAbfJVcv0LO` (bans and vetoes) | `inputs/known_solutions.jsonl` |

### Location setting

One environment variable, `AII_DEPS_ROOT`, sets where these folders are found. Its default is the parent of this
folder, which is where the repository puts the sibling folders. Inside that root, a dependency is looked up in this
order:

1. by its artifact id;
2. by its id without the `art_` prefix;
3. by its original workspace name (for example `gen_art_experiment_27`);
4. by the run's layout `iter_<k>/gen_art/<name>`.

The run was made on the original server with `AII_DEPS_ROOT` pointing at the run's `3_invention_loop` folder, which
uses that last layout.

### Vendored inputs

These inputs are not declared dependencies, so copies ship in this folder:

- **Two earlier evaluations.** `inputs/art_mgek9PfVBNbh/` holds `corrections.json`, `rivals.json` and
  `tables/dose_units.csv`. `inputs/art_sV0cQ3ef1ZRQ/` holds `screen.json` and `tables/knob_table.csv`. The plan reads
  these by path, and the code falls back to the copies when no sibling folder exists.
- **The report.** The iteration-6 report that the corrections are keyed to is `inputs/report/current_report.md`
  (override with `AII_REPORT`). It is the run's own strategy-step file, not a user upload.

### User uploads

No user-uploaded input is used. The run's upload folder was empty when this artifact ran.

## 2. System, Python and libraries

- **System.** Ubuntu or Debian with Python 3.12 and `uv`. The run used a Debian 12 container with Python 3.12.14. No
  other system package is needed: the sandboxed programs use only the Python standard library, and no C compiler is
  required.
- **Environment.**

  ```bash
  uv venv .venv --python=3.12
  uv pip install --python .venv/bin/python -r requirements.lock.txt
  ```

  `uv run eval.py ...` also works. It syncs from `pyproject.toml`, which pins the same versions.
- **Exact versions installed and used.** These are the same as `pyproject.toml` and `requirements.lock.txt`. The uv
  venv has no `pip` binary, so the list comes from `uv pip freeze`:

  ```
  aiohappyeyeballs==2.7.1  aiohttp==3.14.5  aiosignal==1.4.0  attrs==26.1.0  contourpy==1.4.0  cycler==0.12.1
  fonttools==4.67.0  frozenlist==1.8.0  idna==3.20  kiwisolver==1.5.1  loguru==0.7.3  matplotlib==3.11.2
  multidict==7.1.0  numpy==2.3.5  packaging==26.3  pillow==13.0.0  propcache==0.5.4  pyparsing==3.3.3
  python-dateutil==3.0.0  pyyaml==6.0.3  scipy==1.16.3  six==1.17.0  tenacity==9.2.1  typing-extensions==4.16.0
  tzdata==2026.5  yarl==1.25.1  zss==1.2.0
  ```

  numpy is held below 2.4. A numpy 2.5 wheel installed half-built in this container, and `zss` could not import with it.

## 3. Downloads, environment variables, keys

No model, checkpoint or dataset is downloaded. No GPU is used. The environment variables, by name:

| Name | Required? | What it does |
|-|-|-|
| `AII_DEPS_ROOT` | Optional | Location of the dependency folders. Default: the parent folder. |
| `AII_REPORT` | Optional | The report the corrections are keyed to. Default: `inputs/report/current_report.md`. |
| `AII_JSON_SKILL_DIR` | Optional | The AI Inventor `aii-json` skill folder. When it is set, the out stage validates `eval_out.json` against `exp_eval_sol_out` and writes `full_`/`mini_`/`preview_eval_out.json`. Without it, validation is skipped. |
| `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL` | Only for new judge calls | Needed only when a judge response is missing from `audit/judge_cache.jsonl`, for example after the cache is deleted or a prompt changes. With the shipped cache, every call is served from disk and costs nothing. |

## 4. Commands that were run, in order

Hardware: a container with 6 CPU cores (AMD EPYC 7352) and 28 GB of RAM. An NVIDIA RTX 2000 Ada (16 GB) was present
and unused. All stages are CPU-only.

```bash
export AII_DEPS_ROOT=<folder holding the dependency artifacts>      # see section 1
export AII_JSON_SKILL_DIR=<aii-json skill folder>                   # optional
uv run eval.py --stages all          # s0,0a,0b,0c,0d,0e,0f,audit,out; defaults --n-boot 10000 --n-power 10000 --max-usd 0.90
uv run python audit/summarise_judge_runs.py   # writes audit/judge_runs_summary.json
uv run python audit/headline_check.py         # short independent check of the headline numbers, with placebos
uv run python src/finalize.py                 # strips NUL bytes and absolute paths from the text outputs
```

Approximate runtime of one `--stages all` run is 6.5 minutes:

| Stage | Time |
|-|-|
| s0 | 1 s |
| 0a | 8 s |
| 0b | 3 s |
| 0c | 30 s (10,000 bootstrap and 10,000 power replicates) |
| 0d | 1 s |
| 0e | 1 s |
| 0f | 5 min: sandbox stress tests 45 s; Zhang-Shasha tree edit distances on 5 processes 190 s; judges from the cache |
| audit | 10 s |
| out | 15 s |

The two audit scripts take 10 s and 1 s.

### Judge passes

Stage 0f queried OpenRouter in four passes. All four are in `audit/judge_runs_summary.json` and all their responses
are in `audit/judge_cache.jsonl`:

1. Passes 1 and 2 put measured run times into the prompts, so their prompt hashes differed from run to run.
2. Pass 3 used deterministic prompts.
3. Pass 4 re-queried two Kimi outputs that had come back empty at a 1,500-token cap, this time with a 4,000-token cap.

Total spend was USD 0.29 over 431 paid calls. Later runs, including the final `--stages all`, are fully cached and
identical.

### Seeds

All seeds are fixed in the code:

| What | Seed(s) |
|-|-|
| Permutation tests | 1 (rho, 10^6 Monte Carlo permutations); 8 (correct-only sensitivity); 10 (rivals); 11 (figure) |
| Unit bootstrap | 2, and 9 for the rival deltas |
| Copula power | 4, 5 and 6 |
| Within-set landing permutation | 5 |
| Event-cluster bootstrap | 17 |
| Stress-test generators | 1 to 5 |
| Blinding shuffle | 20261022 |
| Rarefied Hill-1 | 0, via the run's own `vendor/eval2_stats.py` |

The judges ran at temperature 0, with three calls per item for Mistral Medium 3.1 and one for Kimi K2.

## 5. What a reader should get, and where it appears in the paper

### `eval_out.json`

Format `exp_eval_sol_out`, with `full_`, `mini_` and `preview_` variants. It holds 10 datasets and about 370
metrics. The headline values:

- **Engine.**
  - Connected components: bf16 1 of 50 against 8-bit 30 of 50 correct programs off the default at alpha 2 (Fisher p
    7.2e-11); bracket p 0.056.
  - Shortest path: 2 of 47 against 15 of 37 (p 5.3e-5); bracket p 0.017.
  - Both are tagged 'did NOT replicate in bf16 at the population level'.
- **Landings.**
  - 17 of 21 events (Poisson-binomial p 5.8e-7).
  - Unconfounded held-out subset: 5 of 8 (p 0.053). Item 2 of section 5.11 therefore moves to the descriptive results.
- **Movability.**
  - Spearman 0.146 over the 13 new units, Bonett-Wright 95% interval [-0.44, 0.65].
  - The value is 0.035 if count inversions' beta comes from correct programs (the committed beta uses attempts).
  - Power at a true 0.6 is 0.63 one-sided and 0.50 two-sided. These are Monte Carlo values, accurate to about ±0.01.
- **Second adjudication.**
  - Mistral called 1 of the 14 programs novel (P13, a linear search, overturned on a full read). Kimi called 0.
  - Control gates: 9/10 for each judge.
  - Final novel count: 0.
- **Audit.** `audit/rederive.py` passes all of its checks and 5 of 5 placebos fail. `audit/headline_check.py`
  reproduces 7 of 7 headline numbers, and its placebos fail.

### `corrections.json`

It holds 36 corrections, each with a verbatim `old_text` from the report and its `new_text`. They apply to these
sections of the paper:

- §4.2.1: Table 126c.
- §4.2.3: Table 129 rows.
- §4.9: novelty.
- §4.10: what iteration 4 established, with engine tags.
- §5.2: dose units.
- §5.4 and §5.5: the panels, plus the new Table 203b.
- §5.7: Tables 206-208, plus the new Table 207b.
- §5.8: Tables 214 and 217.
- §5.10: Table 222, `fig_beta_escape`, and the landing tally.
- §5.11: items 2-4, the movability bullet and the dead end.
- §5.12.
- The closing 'What we have learned so far': internal account, influence, landings, representation and novelty.

### Other outputs

- `figures/fig_beta_escape_l4l.{pdf,png}` replaces the cross-engine `fig_beta_escape` in §5.10.
- `tables/*.csv` hold the full tables behind each correction.
- `engine_labels.json` holds the engine tag of every internal result.

## 6. Departures from the plan

1. **Packaging.** Dependencies are pinned in `pyproject.toml` rather than in inline script metadata, because the
   repository's Python standard forbids inline headers.
2. **Permutation p.** At n = 13, exact enumeration would take 6.2e9 permutations. The rho p therefore uses 10^6
   Monte Carlo permutations, with mid-ranks for ties.
3. **R6 runtime merit.** It is computed under one definition from the `ref_times` that both panels stored in
   `tests.jsonl`, the panels' own harness timings. Nothing was re-timed, because the raw per-mode times exist.
4. **Tree edit distance.** The exact Zhang-Shasha distance is computed on a shortlist: the 20 pool members closest by
   difflib on identifier-scrubbed source, plus every reference. `bench/common/canon.py` builds token streams, not
   ASTs.
5. **Second judge.** It is `moonshotai/kimi-k2-0905`. Neither Mistral nor Moonshot appears in any dependency's cost or
   audit file.
6. **Extension items.** 17 more programs, those the audit manually classed KNOWN OUTSIDE THE CATALOGUE, are judged
   descriptively and not gated.
7. **The 25% sentence.** The 'shortfall of at most about 25%' sentence does not exist in the report. The dose
   correction is keyed instead to its range sentence, 'the ban-free unit is 0.30 to 0.97 of the ban unit across
   tasks'.
8. **The repeated maximum-selection control.** The plan calls it a textbook technique outside the catalogue. The
   iteration-5 manual pass classed the same technique (program P10) as a catalogue variant, and both judges agree
   with that pass. The gate is therefore reported under both conventions, and it passes under either.
9. **Power.** Power at a true 0.6 is 0.63 for the registered one-sided test. The direction's quoted 0.46 matches the
   two-sided power (0.50).
