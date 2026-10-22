# Reproducibility

These are the steps that were actually run to produce this folder, on 2026-10-22 (UTC), and how to repeat them on
Ubuntu. Every path below is relative to this folder, the one that contains `eval.py`.

## 1. Get the artifact

This workspace is published as one folder of a public GitHub repository. Clone the repository and `cd` into this
artifact's folder:

```bash
git clone <repository-url>
cd <repository>/<this-artifact-folder>    # the folder holding eval.py, README.md and this file
```

## 2. System packages, Python and the environment

The run used Debian 12 in a container, but any recent Ubuntu works.

- System packages: `git`, `curl` and `ca-certificates`. Install them with
  `sudo apt-get update && sudo apt-get install -y git curl ca-certificates`.
- uv, the only package manager used here: `curl -LsSf https://astral.sh/uv/install.sh | sh`.
- Python 3.12. The run used CPython 3.12.14. If no 3.12 is installed, `uv python install 3.12` provides one.

Create the environment with the exact pinned versions:

```bash
bash restore.sh          # = uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
```

The versions installed in the run and pinned in `pyproject.toml` (from `uv pip freeze`; the venv has no pip):

```
aiohappyeyeballs==2.7.1  aiohttp==3.14.5  aiosignal==1.4.0  attrs==26.1.0  frozenlist==1.8.0  idna==3.20
jsonschema==4.26.0  jsonschema-specifications==2025.9.1  loguru==0.7.3  multidict==7.1.0  numpy==2.5.4
propcache==0.5.4  pypdf==6.21.2  pyyaml==6.0.3  referencing==0.37.0  rpds-py==2026.9.1  scipy==1.18.1
six==1.17.0  typing-extensions==4.16.0  yarl==1.25.1  zss==1.2.0
```

`audit/rederive.py` and `audit/headline_check.py` use only the Python standard library.

## 3. Data, models, environment variables

**Downloads.** No model, checkpoint or dataset is downloaded. No model is run: this artifact only recomputes numbers
from rows that earlier artifacts already wrote.

**Inputs.** Every input is vendored under `inputs/<artifact_id>/<path>`, with its sha256 and size in
`input_hashes.json`. The four declared dependencies are art_lpQalcAXMGr1 (engine control), art_rMlbrjVB1c__
(exchange and site experiment), art_zNyBP6zieI5u (Gemma) and art_dbUtqBjT0tPf (NLA). Two more artifacts were read
by path: art_aRTQM6CQ0Dre (iteration-6 Step 0) and art_OUuQUYQn5voE (iteration-6 positioning audit). The run report
being corrected is vendored as `inputs/report/current_report.md`.

**Finding the source artifacts.** The code reaches them through one anchor, `DEPS_ROOT` in `src/common.py`. It
defaults to three levels above this folder (the run's invention-loop folder) and is overridden by the environment
variable `AII_DEPS_ROOT`. In the published repository each artifact is a sibling folder. `src/common.py` looks first
under `DEPS_ROOT`, then at a sibling folder named like the artifact's workspace folder (for example
`gen_art_experiment_29`), then at one named by the artifact id. If none is reachable, the vendored copies are used
once their sha256 matches `input_hashes.json`.

This was tested: with `AII_DEPS_ROOT` pointing at an empty path, the offline run reproduces every correction, the
apply test, both audits and `eval_out.json`. The only difference is that the cross-check against the dependencies'
`full_method_out.json` files (`results/predict_crosscheck.json`) is skipped, because those 36 MB files are not
vendored.

**Environment variables (names only).**

| Variable | When it is needed |
|-|-|
| `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL` | Only for `--stages all`, which re-calls the judges (about USD 0.08). |
| `AII_DEPS_ROOT` | Optional; see above. |
| `AII_SKILLS` | Optional. It is the location of the AI Inventor `aii-web-tools` skill, which is internal tooling and not published. Only the live web pass of `--stages all` needs it. |

**User uploads.** None were used: the run's user-upload folder was empty. Nothing private is needed.

## 4. What was run, in order

Hardware: a CPU-only container with 11 CPUs (AMD EPYC 7402P) and a 57 GB memory limit. The NVIDIA RTX A4500 (20 GB)
of the compute profile was not used. Times are UTC on 2026-10-22.

1. **13:03 to 13:12, setup.** `uv venv .venv --python=3.12`, then
   `uv pip install --python=.venv/bin/python numpy scipy pyyaml pypdf zss loguru aiohttp jsonschema`. The resolved
   versions are the pins above. `src/stage_inputs.py` then vendored and hashed the 69 inputs.
2. **13:28, the live web pass.** `positioning.collect()` made 32 calls: arXiv abstract pages, quote greps over the
   abstract and HTML versions, 6 scholarly and 7 general searches. One extra general search, for the Forking Paths
   venue, ran at 13:41. Every page and result is cached under `audit/web/`.
3. **13:34, `uv run eval.py --stages all` (run 1).** Superseded. The judges completed (USD 0.045), but one
   adversarial stress case had node ids of n or more, and the final write failed on a signature change.
4. **13:36, `uv run eval.py --stages all` (run 2), the judges of record.** The stress case was fixed. The protocol
   was frozen at 13:39:49 in `audit/judge_protocol.json`. Then came 3 calls per item at temperature 0, items shuffled
   with seed 20261022, for openai/gpt-4.1-mini and deepseek/deepseek-chat-v3.1. GPT-4.1-mini failed the 9-of-10
   gate, so the declared replacement google/gemini-2.5-flash-lite was run, as recorded in
   `audit/judge_protocol_amendments.json`. Spend over both passes was USD 0.077; responses are in
   `audit/judge_cache.jsonl`.
5. **13:41 to 13:50, `uv run eval.py --stages offline`, repeated after small fixes.** The fixes were verified
   venues, the concordance band rule, de-duplicated value counts, the `predict_*` cross-check and the headline check.
   Offline mode reuses `results/novelty.json` and `audit/web/` and spends nothing. The final run took about 20 s of
   wall time.
6. **13:50, the aii-json formatter.** It ran on `eval_out.json`, producing `full_eval_out.json`,
   `mini_eval_out.json` and `preview_eval_out.json`. All four files then passed validation as `exp_eval_sol_out`.

To repeat:

```bash
uv run eval.py --stages offline     # no network, no spend; rebuilds every output from inputs/ and the caches
python3 -I audit/rederive.py        # the independent audit (also run by eval.py)
python3 -I audit/headline_check.py  # the headline re-derivation with placebos (also run by eval.py)
# optional, re-calls the judges and the live web pass (needs the variables of section 3):
uv run eval.py --stages all
```

Seeds:

| Seed | Used for |
|-|-|
| `numpy.random.default_rng(20261022)` | the NLA cluster bootstrap (the NLA artifact's own procedure; it reproduces [-0.347, 0.022] exactly) and the 2,000 draws of one random unit per sample |
| `random.Random(20261022)` | the blind order of the judged items |
| `random.Random(7)` | the stress-test inputs |
| `random.Random(3)` | audit placebo P3 |
| `random.Random(0)` and `random.Random(1)` | the placebos of the headline check |

## 5. What a reader should get

The offline run is deterministic, so these numbers should come out exactly:

- `corrections.json` holds 54 corrections. The apply test passes 54 of 54 with no overlaps. `report_corrected.md`
  carries 54 `(iteration-7 correction)` markers, and `report.diff` is its diff against the vendored report.
- The values are ledgered as 603 MATCH, 117 NEW, 1 CARRIED and 3 CORRECTED (`results/values_ledger.json`). The 3
  CORRECTED are the plan's venue expectations that the live records contradict; they are listed in
  `eval_out.json` under `metadata.discrepancies`.
- The lint finds 16 flags before and 0 after (`tables/lint.csv`).
- `audit/rederive_report.json` has 520 checks with 0 mismatches, and 7 of 7 placebos fail.
  `audit/headline_check.json` has 35 checks with 0 failed, and 7 of 7 placebos fail.
  `results/predict_crosscheck.json` has 137 checks with 0 mismatches (only when the dependency folders are reachable).
- In `eval_out.json`, `metrics_agg` holds M1 to M12 and `metadata.sections` covers 0a to 0l. Its seven datasets are
  corrections, stage_a_cells, table238_rows, nla_one_unit, novelty_judgements, figure_markers and positioning_rows.

Key numbers, with where they enter the paper (through the corrected run report the paper step quotes):

- **Section 6.4.1, Tables 244 to 250:**
  - Stage A on commit0's definition, with a correct-Y column: shortest path at blocks 0-35 has 24 of 30 attempts and
    21 of 30 correct programs, and the grid at blocks 0-35 has 14 and 3.
  - Post-hoc correct-Y McNemar against the matched-norm random exchange: 21:0, 15:2 and 11:0.
- **Section 6.4.2 and the NEW Table 254b:** the site is open, because the condition-span beta is -1.70
  [-3.96, 0.42] and -0.56 [-4.93, 2.91] and so fails post hoc.
- **Section 6.5, Tables 261 to 263:**
  - DAS rank 1 moves the fork log-odds by 8.8 nats within its controls, but 0 of 50 programs pass.
  - The standardised SAE ridge reaches 0.15, against 0.086 for its control.
- **Section 6.6, Table 270:** the NLA test at one unit per sample is 0:25, p 6.0e-8, over 104 samples. The
  task-cluster interval is [-0.35, 0.02]. With 5 clusters the cluster-level floor is p 0.0625.
- **Section 6.3, Table 238:** the correct-only counts on shortest path are 14/37 under W8A8 and 9/31 under bf16 at
  alpha 2. The screen-level verdict is MIXED.
- **Section 6.9, Table 278:** the engine control's 3 correct programs labelled other are all catalogue variants;
  0 are novel.
- **Section 6.9, the NEW Table 279:** the per-model synthesis.
- **Section 6.7, Table 277 row 66:** the positioning of the one-token fork. All 6 of 6 quotes are verified.
- **Sections 6.4.4, 6.5 and 6.6:** seven `[FIGURE:...]` markers (`figure_markers.json`).
- **Section 4.9:** the novelty claim is limited to the audited pools.

## Sandbox

Programs run in a subprocess (`src/sandbox_child.py`, started with `python -I`) under RLIMIT_AS 2 GB and RLIMIT_CPU
10 s, with a wall-clock timer per case, a minimal environment, and the socket module disabled before the program is
executed. Unprivileged network namespaces are refused on the run host (`unshare -n`), so the network block is best
effort, not enforced by the kernel.
