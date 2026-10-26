# Reproducing the iteration-9 Step-0 record repair

This file says exactly what was run on 2026-10-23 to produce the files in this folder, and how to run it again. Every
path below is relative to this folder.

## 1. Get the artifact

```bash
git clone <URL of the published run repository>
cd <repository>/<this artifact's folder>        # the folder that holds eval.py, README.md and this file
```

The repair reads six iteration-8 artifacts, each published as a sibling folder of this one in the same repository. They are named by id:

| Artifact id | Role | Original folder on the run volume |
|-|-|-|
| `art_vnyi0Fm5SyNH` | fork-dosing experiment | `gen_art_experiment_39` |
| `art_e-_q5mSJGrSb` | DAS experiment | `gen_art_experiment_40` |
| `art_18XvfcJJZi1O` | circuit experiment | `gen_art_experiment_41` |
| `art_FJMIE9T9_PMv` | Gemma dial experiment | `gen_art_experiment_42` |
| `art_lzuosbrb34wB` | temperature-law experiment | `gen_art_experiment_43` |
| `art_R-HSmXq2t97f` | top-five prohibition experiment | `gen_art_experiment_44` |

All code finds these through ONE setting: `S0_DEPS_DIR`, defined in `src/recompute.py`. The two audit scripts mirror it in their own code. Each artifact is looked up by its id or by its original folder name, first under `S0_DEPS_DIR` (default `../../../round-8`, the run-volume layout) and then as a sibling folder (`..`). If the six folders are somewhere else, set `S0_DEPS_DIR` to the folder that contains them.

## 2. System, Python and libraries

- **OS:** Ubuntu 22.04/24.04 or any Linux. We ran in a Debian 12 container. No system packages were needed beyond what `uv` provides.
- **Hardware actually used:** CPU only, 14 cores (AMD Ryzen 9 9950X) and a 55 GB RAM container limit. Peak memory stayed under 3 GB. An RTX 5090 was present but unused; there is no GPU code.
- **Python 3.12.14**, managed with **uv 0.6.14**.

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
```

`pyproject.toml` pins all 29 packages that were installed, at the exact versions used. The direct dependencies are
`numpy==2.5.4`, `scipy==1.18.1`, `matplotlib==3.11.2`, `pyyaml==6.0.3`, `loguru==0.7.3` and `tokenizers==0.23.3`; the
rest are their dependencies. The uv venv has no `pip` executable, so the list came from
`uv pip freeze --python .venv/bin/python`. The audits (`audit/rederive.py`, `audit/headline_rederive.py`) use only the
Python standard library.

## 3. Data, models, environment variables

- **The report under repair** is vendored: `inputs/report/current_report.md` (sha256
  `8b3804f3ecbfedd4c1d54586edd56fe02aaa5c81e4570f4a3aa171ad0cbd7438`). `eval.py` refuses to run on any other report.
  If the strategy's original copy is reachable (`S0_REPORT_SRC`, default `../../gen_strat/current_report.md`), it is
  checked for equality too.
- **The iteration-8 inputs** are the files of the six sibling artifacts. All 53 are listed with their sha256 in
  `inputs_manifest.json`, which is checked unchanged at the end of every run.
- **The 181 MB states file is not published.** The publish step skips files of 100 MB or more, and
  `art_R-HSmXq2t97f/cache/states/smean_C6_nf4.npz` is 181 MB. It holds the residual states and the prompt index of the
  300 forced prompts. Without it:
  - gates E1–E3 and every 0e statistic run from `inputs/forced_index_C6_nf4.json`, a vendored copy of the file's small
    prompt-index arrays, which records the file's sha256 `d1eab914…`;
  - only the E4 cross-check is skipped (`results/s0e.json` gets the flag "E4 not run");
  - on the run volume, where the file exists, E4 ran and reproduced the stored geodesics exactly (Spearman 1.000).

  `src/vendor_index.py` rebuilds the index from the states file.
- **The tokenizer** is needed only for the optional BPE-overlap sensitivity: the `tokenizer.json` of
  `unsloth/Qwen3-32B-bnb-4bit`, read offline from the Hugging Face cache named by `HF_HUB_CACHE` (or `HF_HOME/hub`).
  To fetch it: `huggingface-cli download unsloth/Qwen3-32B-bnb-4bit tokenizer.json`. Without it the sensitivity is
  skipped, as the commitment allows.
- **Environment variables** (names only):
  - `S0_DEPS_DIR`: location of the six artifacts;
  - `S0_REPORT_SRC`: optional;
  - `HF_HUB_CACHE` or `HF_HOME`, and `HF_HUB_OFFLINE=1`: the tokenizer;
  - `AII_WEB_TOOLS_DIR`: needed only to re-run the live web checks with the AI Inventor aii-web-tools skill.

  No API key is needed, and no paid API was called (OpenRouter spend USD 0).
- **User uploads:** none were used; the run's upload folder was empty.

## 4. What was run, in order (2026-10-23, UTC)

1. **Environment.** The commands in section 2.
2. **Live neighbour checks**, 09:42 UTC, about 11 s: `AII_WEB_TOOLS_DIR=<skill dir> bash audit/web_verify.sh`. This
   fetches and greps the 17 pages listed in `audit/web_jobs.tsv` and writes the raw outputs to `audit/web/*.txt`.
   Re-running it fetches today's pages, which may differ. The published raw outputs are the evidence behind Table 416b.
3. **Pre-commitment**, 09:53:57 UTC, before any alias-level number existed: `uv run src/commit_s0e.py`. It writes
   `predictions/commit_s0e.json` and appends its sha256 to `commitments.log`. It never overwrites an existing commit.
4. **Main pipeline**, about 40 s on CPU: `uv run eval.py --stages all`. Stages:
   - **setup**: hashes the inputs;
   - **0e**: gates E1–E4 and the alias statistics;
   - **BPE sensitivity**: `src/tertiary_bpe.py`;
   - **value ledger**: 0a/0b/0c/0f;
   - **edits**: 0d positioning, 0g markers, the 49 edits, the apply test, the whole-report lint, `report_corrected.md`
     and `report.diff`;
   - **audits**: `audit/rederive.py` (400 checks) and `audit/headline_rederive.py` (headlines from raw rows, with
     placebos);
   - **outputs**: `eval_out.json` and its variants, followed by the inputs-unchanged assert.
5. **Variants and validation.** We then ran the AI Inventor aii-json format script on `eval_out.json`, which rewrote
   `full_eval_out.json`, `mini_eval_out.json` (3 examples per dataset) and `preview_eval_out.json` (strings truncated to
   200 characters), and validated all four against the `exp_eval_sol_out` schema (all passed). Without that skill,
   `eval.py` writes equivalent variants itself.

Seeds and fixed settings:

- `SEED = 20261023` (`src/alias_geometry.py`): template bootstrap (2,000), placebos P1–P3 (1,000 each) and the Monte
  Carlo null for content-word overlap (200,000 draws);
- planted-control seeds 10000–10199;
- `SEED + 3` for the BPE Monte Carlo null;
- `random.Random(20261023)` and `random.Random(7)` in the two audits.

Every exact null (360,360 assignments for the 15-alias test, 120 for the 5-centroid test, 7,776 for the stratified test)
is deterministic.

The commitment chain in `commitments.log` records two amendments to `src/stage_0e.py` after the commit, each with a
reason line. Neither touches a statistic, null or rule:

- the legend of panel A was moved;
- a fallback to the vendored prompt index was added for copies without the states file.

`src/alias_geometry.py` is byte-identical to the committed version.

## 5. What you should get

| Quantity | Value | Where |
|-|-|-|
| Edits; apply test; lint | 49 edits; apply test passes; 28 unallowed residual-claim hits before, 0 after (8 allowlisted pre-iteration-8 hits) | `corrections.json`, `apply_test.json`, `lint_allowlist.json`; `metrics_agg` |
| Value ledger | 298 values: 147 MATCH, 151 NEW, 0 CORRECTED, 0 CARRIED | `corrections.json#values_by_status`, `tables/ledger.csv` |
| 0a circuit | L0 condition-MLP held-out effect 0.00, because the held-out edit was not applied (0 of 10 held-out prompts share a template with a pair prompt); pair means 8.14 and 7.41 nats; natural-contrast held-out 0.28 nats (p 0.031); motif different (condition share 0.01 against [0.21, 0.51]; depth 0.86 against [0.45, 0.80]) | report 8.5 (Tables 395/396 and the paragraph after Table 395), 8.9 Table 414, 8.10, closing; `tables/circuit_heldout.csv` |
| 0b DAS | Qwen3-8B fork NO HANDLE: toward BFS 29 of 30 written, 5 correct, pass 0.20 against 0.83, 5:0 against random (p 0.0625); Gemma SUFFICIENT HANDLE 22 of 30 | report 8.4 Verdict, 8.9, Tables 414 and 416, closing; `tables/occurrences_29of30.csv` |
| 0c entropy and law | above the twin's 90th percentile in 209 of 209 samples; highest-entropy position 44/44, 32/39, 21/39, 2/50, 0/37; law 5 of 6 units, flat law better on valid anagram (0.030 against 0.054), tempering on substring search (0.023 against 0.033), sign test p 0.34 | report 8.3, 8.9, 8.10, closing; `tables/entropy_scope.csv`, `tables/law_scope.csv` |
| 0d positioning | Table 416b: 11 neighbours checked live (8 VERIFIED, 3 VERIFIED-ABSTRACT); Cantarero et al. on two NeurIPS 2026 workshop posters | report 8.10b and references [142]–[146]; `tables/positioning_rows.csv`, `audit/web/` |
| 0e alias manifold | gates E1–E4 pass; 15-alias rho -0.61 (exact p 0.0093; CI -0.71 to -0.59) at k 15 and -0.77 at k 10; 5-centroid -0.63 (p 0.133, floor 0.033); within-algorithm -0.12 (p 0.46); BPE sensitivity -0.50 (p 0.057); verdict CONFOUNDED | report 8.8 ("Is 'opposite' a property of the names?"), 8.9, 8.10, 8.11, closing; `results/s0e.json`, `tables/alias_*.csv`, `figures/alias_overlap.png` |
| 0f Gemma arms | A2, A4 and A6 not run on Gemma; three families scored at the twin's Hill | report 8.3; `tables/gemma_arms.csv` |
| 0g markers | 7 iteration-8 figure markers plus `fig_alias_overlap`, each with six caption fields and sha256 | `figure_markers.json`; report 8.3, 8.4, 8.6, 8.8 |
| Audits | `audit/rederive.py`: 400 checks, 0 mismatches, 4/4 placebos fail. `audit/headline_rederive.py`: all headlines reproduce from raw rows, and its placebos fail | `audit/rederive_result.json`, `audit/headline_rederive.json` |

Small differences are possible only in quantities that depend on the live web pages (re-fetching them) and in the last
digit of Monte Carlo p-values on a different numpy build. Every exact statistic and every headline above is
deterministic.
