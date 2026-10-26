# gen_demo_art_evaluation_3 — report_results

> Phase: `gen_paper_repo` · `gen_demo_art`
> Run: `gen_paper_repo_c164ac661673` — A Random Activation Push Changes a Code Model's Algorithm Where Temperature Does Not
>
> Full, verbatim transcript of this agent task — every system/user prompt, assistant response, thinking block, tool call and tool result — in the order they occurred. Nothing truncated.

## Task: `gen_demo_art_evaluation_3` (terminal_claude_agent, claude-opus-5-5)

### [1] CONFIG · 2026-10-26 10:50:57 UTC

```
model: Claude Opus 5.5 | effort: max | permission: bypassPermissions
```

### [2] SYSTEM-USER prompt · 2026-10-26 10:51:07 UTC

````
<conversion_philosophy>
**MINIMAL CHANGES — PRESERVE THE ORIGINAL CODE**

The goal is to make the artifact's code READABLE, UNDERSTANDABLE, and RUNNABLE in a short time
to someone reviewing the research, with the option to easily scale parameters back to original
values for a full run (which can take much longer). Think of this as annotating and reformatting,
not refactoring.

**DO:**
- Split the original script into logical notebook cells (imports, setup, processing, results)
- Add markdown cells BETWEEN code cells explaining what each section does and why
- Add inline comments where the logic is non-obvious
- Add a visualization/summary cell at the end showing key outputs
- Fix hardcoded file paths to use the GitHub data loading pattern

**DO NOT:**
- Rewrite functions or change algorithms
- Rename variables or restructure logic
- Add error handling, type hints, or "improvements" that weren't in the original
- Simplify or "clean up" the original code
- Remove any original comments or logic
- Change the computational approach

The reader should recognize the original script when looking at the notebook — it's the
same code, just split into cells with explanatory markdown between sections.
</conversion_philosophy>

<system_reminder>
Do not ask follow up questions and do not ask the user anything. Execute all steps independently.
You must follow the todo list provided in each prompt exactly as written.
No placeholders, stubs, or incomplete code — all code must be complete and functional.
</system_reminder>

<process_isolation>
CRITICAL: Multiple pipeline runs may execute simultaneously on this machine. `ps aux | grep method.py` matches ALL runs, not just yours.
- NEVER kill processes by name (`killall`, `pkill -f`, `ps aux | grep ... | xargs kill`). This kills OTHER runs' processes.
- NEVER monitor processes by name (`ps aux | grep method.py`). You will see other runs' processes and get confused.
- ALWAYS use PID-based process management:
  Run: `uv run method.py & PID=$!` or `timeout <seconds> uv run method.py & PID=$!`
  Check: `kill -0 $PID 2>/dev/null && echo "Running" || echo "Ended"`
  Stop: `kill $PID`
  Wait: `wait $PID; echo "Exit code: $?"`
  Monitor: `tail -f logs/run.log & TAIL_PID=$!` then `kill $TAIL_PID` when done
</process_isolation>

<workspace>
Your workspace: `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ`

CRITICAL: Every file you create, write, or save MUST be inside this workspace directory (subdirectories OK). You MUST NOT write files anywhere outside this path — external paths are READ-ONLY. Use absolute paths for all file operations.

EVERY file write MUST start with `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/`:
GOOD: `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/file.py`, `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/results/out.json`
BAD: `/tmp/file.py`, `~/output.json`, `./file.py`, any path outside the workspace
</workspace>
<disposable_outputs>
A SHARED CACHE ALREADY EXISTS FOR THIS RUN: `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/.shared_cache`
`HF_HOME`, `HF_HUB_CACHE`, `TRANSFORMERS_CACHE`, `HF_DATASETS_CACHE`,
`TORCH_HOME`, `PIP_CACHE_DIR` and `UV_CACHE_DIR` are ALREADY set to point
there. Every step and every iteration of this run shares it, so a model or
dataset an earlier experiment downloaded is already on disk for you.

DO NOT override those variables. In particular do NOT write the common
pattern `os.environ["HF_HOME"] = <workspace>/hf_cache` — `HF_HOME` and
`TRANSFORMERS_CACHE` are read differently by `huggingface_hub` (one has
`/hub` appended, the other does not), so pointing both at one directory
stores every weight TWICE. That mistake cost one run 25 GB of identical
blobs. If you must set them, use the values above verbatim.

YOUR WORKING DIRECTORY IS A DELIVERABLE. When this module ends it must read
like a GitHub repository someone else can fork, resume and run — and the bulk
it holds must be either worth keeping or restorable. This run shares a storage
volume with the database; a run that fills it stops every other run on the box.

So before you finish, produce TWO files:

1. `.aii/manifest.yaml` — one entry per heavy path, each with EXACTLY ONE decision.
   The `.aii/` directory ALREADY EXISTS in your cwd: write the file into
   it. Do not create, replace or `touch` `.aii` itself — a plain file by
   that name makes the manifest unwritable for the rest of the module.

```yaml
entries:
  - path: results/
    keep: six GPU-hours of sweep output, not reproducible inside this run
  - path: hf_cache/
    delete: redownloadable
    source: "huggingface-cli download meta-llama/Llama-3-8B"
  - path: checkpoints/
    delete: regenerable
    source: "uv run train.py --epochs 3 --seed 0"
```

   - `keep:` takes a ONE-LINE reason. Use it for the expensive and the
     irreproducible: trained weights, long-running results, datasets you
     collected yourself.
   - `delete:` takes `redownloadable` (and a `source:` naming the repo id, URL
     or command) or `regenerable` (and a `source:` that is the command which
     rebuilds it). These are deleted AFTER the round ends, never mid-step.
   - Every path is RELATIVE TO YOUR CWD and must resolve INSIDE it. Absolute
     paths, `..`, and anything resolving outside are rejected.
   - Globs and whole directories are fine. A whole `hf_cache/` is ONE entry —
     do not list files individually.

2. `README.md` — written as if your cwd were a GitHub repository: what you
   did, the layout with a line per important file/directory, how to run it,
   and a **"Restoring removed files"** section giving the install/download
   command for EVERY `delete` entry. An `install.sh` or `restore.sh` beside it
   is welcome.

A CHECKER RUNS WHEN YOU SUBMIT. If anything heavy has no decision it fails
your submission and hands you the uncovered list, grouped by directory with
sizes, and you fix the manifest and submit again.

WHAT NEEDS NO DECISION — do not write entries for these:
- text and code files, at ANY size (source, JSON, CSV, YAML, logs, markdown);
- anything under the auto-keep floor (10 MB), whatever it holds.
Only large binaries and cache directories (`hf_cache/`, `.venv/`,
`node_modules/`, `checkpoints/`, `wandb/`, `__pycache__/`, …) need one.

NEVER mark your results, figures, papers, code, logs or anything a later step
reads as `delete`. If a later step needs it, it is a `keep`.

WHAT A `keep` BUYS YOU. Anything you do not mark `delete` stays exactly where
you wrote it, on this run's storage volume, at the path it already has — it is
not moved, renamed or copied. A later round reads it there, by that absolute
workspace path, so a checkpoint you keep is a checkpoint the next round can
load instead of retraining. It is also the ONLY copy: the publish step pushes
your cwd to GitHub but skips every file of 100 MB or
more, so trained weights and large binary artifacts never leave the volume.
Name each kept artifact in your results and your `README.md` by its path
RELATIVE to your cwd, and say it stays on the run's volume rather than in the
published repository. Never write an absolute server path into a file that is
published: a reader's machine has none of them.
</disposable_outputs>

<tool_use>
Maximize parallel tool calls. Parallelize independent operations, only sequentialize dependencies.
- Multiple searches/fetches on different topics → parallel in one turn
- Search then fetch results → sequential (need URLs first)
</tool_use>

<task>
Convert this artifact's Python script into a demo notebook with MINIMAL changes to the original code.
Split into cells, add markdown explanations between sections, add a visualization cell at the end.
Output: mini_demo_data.json + code_demo.ipynb (notebook that loads data from GitHub URL)
</task>

<artifact_info>
id: art_sV0cQ3ef1ZRQ
type: evaluation
title: Record repair and a frozen push screen
summary: >-
  CPU-only Step 0 of iteration 4 (record repair + frozen push screen). Every number is recomputed from labelled rows of the
  11 declared dependencies (exp4, exp6, exp7, exp9, exp11, exp13-exp18) with '<artifact_id>:<relative path>' provenance; no
  model text generated; judge spend USD 0.22. PROVIDES: (1) screen.json, the frozen push-movability screen in canonical JSON,
  sha256 d6a2ca9711f461973c39482314a523d448d0590cb40e32432826dec1da4846e8, with the stdlib-only screen_rule.py (reproduces
  it byte for byte from screen_input.json) and screen_extras.json (per-direction rows, per-engine counts, power notes 1-0.1^(1/K),
  descriptive Fisher p, discrepancies). Movable tasks = T03, T05, T06, T1, T10, T2 (= frozen C1 set); movable vs catalogue-only
  modal-ban avoidance >= 0.5 is 6/0/0/8 (one-sided Fisher p = 1/3003, screen not confirmation); T10 escapes only on the bf16
  HF engine (exp13 rand3), the rest on exp17 FP8 directions; the immovable side is weakly tested (mostly K=3, UB90 0.54).
  (2) tables/knob_table.csv: 1,120 artifact x task x arm x dial cells, each priced against its own twin (pass cost with Newcombe
  CI), correct-only rarefied Hill-1 at depth 25 with template/iid 90% CIs, Good's coverage, catalogue-only avoidance, escape/qualify
  flags; arm_dictionary, random_direction_counts (T03 8/18 at alpha 1, T2 3/15, T05 2/3 and T06 1/3 at alpha 2), table110_alpha2,
  per_task_verdict (best rows at <=5/<=20 pts, coverage-standardised sensitivity). 25 of 27 quoted review numbers reproduce;
  corrected: 'nothing reaches Hill 1.5 under 20 pts on R1/R3/R6/T11/T13/T14' (T14 modal ban 1.78 at 17 pts; exp14 exposure
  arms) and two-sum alpha-2 avoidance 0.469 not 0.48 (denominator). On T03/T05 the cheapest qualifying row is a norm-matched
  random direction and the structured ADD edit sits inside the random range. (3) Route landing (exp16): 7/7 readings, JS 17/17
  to 1e-6, F_prompt 0.611 [0.06,1.17] / F_direct 0.744 [0.38,1.11]; without residue-gated T13 0.648 [-0.08,1.38] / 0.865 [0.68,1.05];
  T13 not gated under catalogue-only avoidance (0.15) so no route class. (4) Llama hits with 'other' excluded: LADDER 6/13
  (Poisson-binomial p 0.100), ASSOCIATE 7/13 (p 0.032); snap-back 0.72/0.73/0.93. (5) 'Other' audit: 21 events, 226 programs
  (6 passing): 68 catalogue variant, 156 degenerate, 2 labeller miss, 0 novel (the one passing NOVEL-flagged program re-runs
  60/60 hidden + 3/3 stress tests but is a textbook value binary search over a sort); judge kappa 0.77 (gpt-4.1-mini below
  the 5/6 control gate, gemini-2.5-flash weighted, deepseek tie-break), manual pass 73 programs incl. all 44 T13 merge-interval
  programs (29 coverage-array, 12 unsorted sweep, 3 other, all failing); residue-gated events exp13 T13, exp16 T13:a, Llama
  T06. (6) Rigor: defined-only hit rates, exposure SUBTRACT defined 4/33 (hits 4/4 both arms), Table 82 per distinct row gain
  0/11, residual 0/11, implied 8/11 (6 sham). (7) Section 3.10 replacement sentences and all corrections in corrections.json
  (0f -> this iteration's research artifact). (8) Rival predictors (14 tasks): movability rho 0.86 vs can 0.16, clarity -0.07,
  FRLP 0.19, nonce -0.19, novelty 0.35. (9) Figures: captioned markers M1-M5 with the position caveat and a 2x2 composite
  in activation coordinates; at the label-independent g16 position BFS's nearest neighbour is IDA*, not BiBFS. AUDIT: audit/rederive.py
  (stdlib, 29 checks) and audit/rederive_extra.py (12 checks) with 0 mismatches; 7/7 placebos fail as required. Outputs: full/mini/preview_eval_out.json
  (exp_eval_sol_out; metadata.sections + 12 datasets), README.md, reproducibility.md; run with `uv sync --frozen && uv run
  eval.py --stages all` (~1.5 min, cached judges).
workspace_path: >-
  /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3
out_expected_files:
- eval.py
- full_eval_out.json
- mini_eval_out.json
- preview_eval_out.json
- reproducibility.md
out_demo_files:
- path: eval.py
  description: Evaluation script with metrics computation
</artifact_info>

<github_repo>
Repo URL: https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract
Raw data URL: https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-4/evaluation-3/demo/mini_demo_data.json

URLs won't work yet — files pushed to GitHub AFTER notebook creation.
Use local fallback pattern so notebook works locally (now) and in Colab (after deployment).
</github_repo>

<data_file_sizes>
Data files come in three sizes:
- preview_*_out.json — READ THIS to inspect the data structure
- mini_*_out.json (~3 examples) — use for prototyping/testing
- full_*_out.json (complete) — use for the final production run. NEVER open it directly (too large to read into context). Instead, extract values programmatically with shell commands (e.g. grep) or a Python script (use aii-long-running-tasks skill for scripts).
</data_file_sizes>

<install_dependencies_pattern>
Follow the aii-colab skill exactly. It has the install cell pattern, pre-installed package list, numpy 2.0 compat shims, and all Colab-specific rules.
</install_dependencies_pattern>

<data_loading_pattern>
`mini_demo_data.json` = curated subset for the demo.
Use this pattern for Colab compatibility (GitHub URL with local fallback):
```python
GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-4/evaluation-3/demo/mini_demo_data.json"
import http.client
import json
import urllib.request
from pathlib import Path

def load_data():
    try:
        with urllib.request.urlopen(GITHUB_DATA_URL, timeout=15) as response:
            return json.loads(response.read().decode())
    # Network errors, timeouts, a placeholder URL, bad JSON, a cut-off response.
    except (OSError, ValueError, http.client.HTTPException) as e:
        print("GitHub data unavailable, using local mini_demo_data.json:", e)
    local = Path("mini_demo_data.json")
    if local.exists(): return json.loads(local.read_text())
    raise FileNotFoundError("Could not load mini_demo_data.json")
```
</data_loading_pattern>

<notebook_structure>
--- Setup ---
Cell 1 (markdown): Title, description, what this artifact does.
Cell 2 (code): Install dependencies — follow the aii-colab skill's install cell pattern exactly. Fill in all packages imported by the artifact's code.
Cell 3 (code): Imports — copy original import block as-is, plus any additional imports needed for the notebook (e.g. matplotlib for visualization).
Cell 4 (code): Data loading helper — use the <data_loading_pattern> above.
Cell 5 (code): `data = load_data()`

--- Config ---
Config cell (code): Define ALL tunable parameters (iterations, epochs, n_samples, hidden_size, etc.) as variables at the top of this cell. Start with the ABSOLUTE MINIMUM values — the smallest that produce any output at all (e.g. 1 iteration, 2 samples, smallest array size). These get gradually increased during testing — see TODOs.

--- Processing ---
Remaining cells: One code cell per logical section of the original script. Add a markdown cell BEFORE each code cell. Copy code as closely as possible, with these changes:
  1. Replace file paths to use the loaded `data` variable.
  2. Use the config variables from the config cell (NOT hardcoded values).
  3. Minimal fixes are allowed if something doesn't work in notebook context (e.g. adjusting paths, removing CLI args, fixing imports), but keep changes to the absolute minimum.

--- Results ---
Visualization cell (code): Print key results in a readable table, plot numeric data with matplotlib if appropriate.
</notebook_structure>

<priority>
WORKING > OPTIMIZED. A small-scale demo that runs correctly is the goal. Once the notebook passes with minimum config values, scale up only if time permits — do NOT spend multiple retries chasing larger parameters. If a working version exists, finish and move on.
</priority>

<max_notebook_total_runtime>600s (10 min)</max_notebook_total_runtime>

<test_environment>
To test-run the notebook in a clean environment (simulating Colab), use the disposable venv at `/tmp/aii_nb_test_envs/art_sV0cQ3ef1ZRQ-ad6af5bda702`. It is on this machine's local disk, outside your workspace, which is on a slow network volume: never create a venv inside your workspace.
```bash
UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_sV0cQ3ef1ZRQ-ad6af5bda702
UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_sV0cQ3ef1ZRQ-ad6af5bda702/bin/python jupyter ipykernel
/tmp/aii_nb_test_envs/art_sV0cQ3ef1ZRQ-ad6af5bda702/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb
```
The timeout is set to <max_notebook_total_runtime>. The entire notebook must finish within this time.
`UV_VENV_CLEAR=1` recreates the venv empty at the start of every test, so each test starts clean. Do NOT delete it yourself: the pipeline removes it after you finish. If you run a test in the background, wait for its result before starting the next test.

What happens: the venv starts with only pip, jupyter and ipykernel. When the notebook's install cell runs, `google.colab` is NOT in sys.modules, so ALL packages get installed — non-Colab packages unconditionally, and Colab packages (numpy, pandas, etc.) at Colab's exact versions via the guard block. The result mirrors Colab's environment as closely as possible. If a cell fails, fix the notebook and re-run.
</test_environment>

FIRST, add ALL of these to your todo list using your task/todo-tracking tool:

CRITICAL: Todo content must be copied exactly as is written here, with NO CHANGES. These todos are intentionally detailed so that another LLM could read each one without any external context and understand exactly what it has to do.


<todos>
TODO 1. Read and STRICTLY follow these skills: aii-colab, aii-long-running-tasks.
TODO 2. Read demo file and relevant preview_* files (preview only). Understand script structure: imports, setup, processing, output. Identify ALL tunable parameters (iterations, epochs, n_samples, hidden_size, batch_size, etc.) — these go in the config cell.
TODO 3. Create `mini_demo_data.json`: curated subset from at most ONE dataset (no more than 100 diverse examples). CRITICAL: do NOT read/grep full output file — may crash. Use `head -c 5000` or stream first entries with Python to pick examples.
TODO 4. Create `code_demo.ipynb` via NotebookEdit following <notebook_structure>. Set ALL config parameters to ABSOLUTE MINIMUM values — the smallest that produce any output (e.g. 1 iteration, 2 samples, smallest array sizes). Test-run using <test_environment>. Fix all errors until it passes.
TODO 5. GRADUALLY SCALE (but don't overdo it): increase config params step by step (e.g. ~2x each round). After each increase: test-run, record runtime, fix errors. STOP SCALING as soon as results look meaningful — a working small-scale demo beats a failed large-scale one. If full original params fit within <max_notebook_total_runtime> (10% margin), use them. Otherwise keep whatever works and comment out the true original values. Do NOT spend more than 2-3 scaling rounds.
TODO 6. Verify: (1) code_demo.ipynb contains GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-4/evaluation-3/demo/mini_demo_data.json" exactly, (2) mini_demo_data.json exists, (3) uses GitHub URL pattern not just open('mini_demo_data.json').
</todos>

---

Output the result as JSON to: `./.terminal_claude_agent_struct_out.json`

JSON Schema:
```json
{
  "$defs": {
    "DemoExpectedFiles": {
      "description": "Expected output files from code demo notebook generation.",
      "properties": {
        "notebook": {
          "default": "",
          "description": "Path to the generated demo notebook. Example: 'code_demo.ipynb'",
          "title": "Notebook",
          "type": "string"
        },
        "mini_data_file": {
          "default": "",
          "description": "Path to the mini demo data JSON (curated subset). Example: 'mini_demo_data.json'",
          "title": "Mini Data File",
          "type": "string"
        }
      },
      "title": "DemoExpectedFiles",
      "type": "object"
    }
  },
  "description": "Dataset/experiment/evaluation \u2192 Jupyter notebook demo.\n\nTitle and summary come from the parent artifact (gen_art step),\nnot from the demo agent. The agent only outputs expected files.",
  "properties": {
    "out_expected_files": {
      "$ref": "#/$defs/DemoExpectedFiles",
      "description": "All output files you created. Must include the demo notebook."
    }
  },
  "required": [],
  "title": "CodeDemo",
  "type": "object"
}
```

IMPORTANT: this task is NOT complete until `./.terminal_claude_agent_struct_out.json` exists and contains JSON matching the schema above.

take this repo as inspiration: https://github.com/DrejcPesjak/llm-creativity
use one or more open-weight models (minimum 1B params), probably instruction tuned it
and first run behavioral analysis (similar to repo mentioned above), then move to interpretability (can be manifolds, or also other techniques like sae, circuits, nla, j-lens, logit lens...)
the question is: how does "creativity" manifest inside the model, and can we influence it?
(in layman terms, can we make llms give truly creative and novel solutions?)

(you do not need to implement everything bellow, see whats reasonable, interesting and might lead to new insights)
is "temp" really the "llm creativity knob"?  (Astra found "coincidentally" similar direction for navier-stokes solution, as Buckmaster & Levent)
(always same seed)
1 a) does a tight temp , with topk=10 produce 10 reasoning trajectories of 1 idea/solution but same 10 phrasings
b) or does tight temp, with topk=10 produce 10 reasoning trajectories of 10 ideas/solutions with 1 phrasing each
c) and does loosing up temp, make a) more to 2/3/4 ideas each with 10 phrasings ; or make b) keep original 10 ideas, now each with 10 phrasings
(temp is rather a minor part in this idea, put more focus on the following things)
test: "implement path saerch algorithm" -> does llm always design BFS?
2 can context seeding help? prepand "seed=d32qxk4nt43" or "seed=(horse chair roof love)"
hyp: is llm a probablistic model, and thus gives you the average/mean answer? and only context pushes you into a different subspace
 - ie of possible range of answer [0,100] , on direct question llm gives you 50. then with context you move to [80,100] subspace and llm gives you 90
3 so how much does prompt instructions matter? ("Make a new algorithm", "Make a fully novel algorithm never seen before ... 2000 words ..."
-> analyze the internals , all the runs that produced BFS , vs all runs that produced DFS , vs dijkstra ...
  -> analyze with thought anchors, NLA, SAE ...
  -> what is the average answer? plot a "path search algorithm" manifold, color each algorithm centroid by implemented-count (lets say we have 10 algorithms in total of 100 gens)
     -> then prohibit the top 5 in prompt, and see if the implemented count moves to the edge of those 5, or to the opposite side (if its a circle manifold)
  - (manifold lit: https://arxiv.org/pdf/2605.05115 , https://www.goodfire.com/research/manifold-steering ) - geodesic and mds
    - (the reports need to contain actual geometry plots, actual activation space, not some summary bar charts)
````

### [3] ASSISTANT · 2026-10-26 10:51:21 UTC

```
I'll start by reading the required skills and exploring the artifact workspace in parallel.
```

### [4] TOOL CALL — Skill · 2026-10-26 10:51:21 UTC

```
aii-colab
```

### [5] TOOL RESULT — Skill · 2026-10-26 10:51:21 UTC

```
{"success": true, "commandName": "aii-colab"}
```

### [6] TOOL CALL — Skill · 2026-10-26 10:51:21 UTC

```
aii-long-running-tasks
```

### [7] TOOL RESULT — Skill · 2026-10-26 10:51:21 UTC

```
{"success": true, "commandName": "aii-long-running-tasks"}
```

### [8] TOOL CALL — Bash · 2026-10-26 10:51:21 UTC

```
List artifact and workspace directories:
ls -la /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/ 2>&1 | head -100; echo "---"; ls -la /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/ 2>&1
```

### [9] TOOL RESULT — Bash · 2026-10-26 10:51:21 UTC

```
{"stdout": "total 22928\ndrwxrwxrwx 12 aii-agent aii-agent 2001226 Oct 25 14:39 .\ndrwxrwxrwx  9 aii-agent aii-agent 3000361 Oct 21 06:54 ..\ndrwxrwxrwx  2 aii-agent aii-agent   65400 Oct 21 04:26 .aii\n-rw-rw-rw-  1 aii-agent aii-agent      54 Oct 21 03:23 .aii_claude_session.json\n-rw-rw-rw-  1 aii-agent aii-agent    8987 Oct 21 04:27 .aii_worker_result.json\n-rw-rw-rw-  1 aii-agent aii-agent 2448571 Oct 21 04:27 .repl_agent.ptylog\n-rw-rw-rw-  1 aii-agent aii-agent    4315 Oct 21 04:26 .terminal_claude_agent_struct_out.json\n-rw-rw-rw-  1 aii-agent aii-agent    8278 Oct 21 04:25 README.md\ndrwxrwxrwx  2 aii-agent aii-agent 1000767 Oct 25 14:39 __pycache__\ndrwxrwxrwx  3 aii-agent aii-agent 2000136 Oct 21 04:22 audit\n-rw-rw-rw-  1 aii-agent aii-agent   37891 Oct 21 04:24 corrections.json\ndrwxrwxrwx  2 aii-agent aii-agent 2000221 Oct 21 03:38 data\n-rw-rw-rw-  1 aii-agent aii-agent    1872 Oct 21 04:06 eval.py\n-rw-rw-rw-  1 aii-agent aii-agent 1556592 Oct 21 04:24 eval_out.json\ndrwxrwxrwx  2 aii-agent aii-agent 2000136 Oct 21 03:54 figures\n-rw-rw-rw-  1 aii-agent aii-agent 1740632 Oct 21 04:24 full_eval_out.json\n-rw-rw-rw-  1 aii-agent aii-agent   48820 Oct 21 04:15 inputs.json\ndrwxrwxrwx  2 aii-agent aii-agent 1024889 Oct 21 04:08 logs\n-rw-rw-rw-  1 aii-agent aii-agent  148546 Oct 21 04:24 mini_eval_out.json\n-rw-rw-rw-  1 aii-agent aii-agent     282 Oct 21 04:14 paths.local.json\n-rw-rw-rw-  1 aii-agent aii-agent   60883 Oct 21 04:24 preview_eval_out.json\n-rw-rw-rw-  1 aii-agent aii-agent    1467 Oct 21 04:20 pyproject.toml\n-rw-rw-rw-  1 aii-agent aii-agent      40 Oct 21 04:07 pytest.ini\n-rw-rw-rw-  1 aii-agent aii-agent   11406 Oct 21 04:25 reproducibility.md\ndrwxrwxrwx  2 aii-agent aii-agent 1008408 Oct 21 03:56 results\n-rw-rw-rw-  1 aii-agent aii-agent    4092 Oct 21 04:16 screen.json\n-rw-rw-rw-  1 aii-agent aii-agent      78 Oct 21 04:16 screen.sha256\n-rw-rw-rw-  1 aii-agent aii-agent   61643 Oct 21 04:16 screen_extras.json\n-rw-rw-rw-  1 aii-agent aii-agent   34332 Oct 21 04:16 screen_input.json\n-rw-rw-rw-  1 aii-agent aii-agent    4763 Oct 21 03:38 screen_rule.py\ndrwxrwxrwx  3 aii-agent aii-agent 1030007 Oct 25 14:38 src\ndrwxrwxrwx  2 aii-agent aii-agent 1072682 Oct 21 04:01 tables\ndrwxrwxrwx  2 aii-agent aii-agent 1000347 Oct 21 10:50 tests\n-rw-rw-rw-  1 aii-agent aii-agent   80228 Oct 21 04:20 uv.lock\n---\ntotal 1996\ndrwxrwxrwx 3 aii-agent aii-agent 1003423 Oct 26 10:50 .\ndrwxrwxrwx 4 aii-agent aii-agent 1003425 Oct 26 10:51 ..\ndrwxrwxrwx 2 aii-agent aii-agent       1 Oct 26 10:50 .aii\n-rw-rw-rw- 1 aii-agent aii-agent      54 Oct 26 10:50 .aii_claude_session.json\n-rw-rw-rw- 1 aii-agent aii-agent   39115 Oct 26 10:51 .repl_agent.ptylog", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [10] ASSISTANT · 2026-10-26 10:51:29 UTC

```
The `eval.py` is tiny (1.8 KB) — it's likely a thin driver over `src/`. Let me read it along with the README, layout and preview structure.
```

### [11] TOOL CALL — Bash · 2026-10-26 10:51:29 UTC

```
Read eval.py, pyproject and list source tree:
A=/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3; cat $A/eval.py; echo "=== PYPROJECT"; cat $A/pyproject.toml; echo "=== PATHS"; cat $A/paths.local.json; echo "=== pytest.ini"; cat $A/pytest.ini; echo "=== SRC"; find $A/src $A/audit $A/tests $A/data $A/tables $A/results $A/figures -maxdepth 3 -type f -not -path '*/__pycache__/*' | xargs ls -la 2>/dev/null | awk '{print $5, $9}'
```

### [12] TOOL RESULT — Bash · 2026-10-26 10:51:29 UTC

```
{"stdout": "#!/usr/bin/env python3\n\"\"\"Iteration-4 Step 0: record repair and frozen push screen. Single entry point with stage flags.\n\n    uv run eval.py --stages all            # every stage in order\n    uv run eval.py --stages knob,screen    # selected stages (each reads the previous stages' outputs)\n\nStages: inventory rows judges knob screen route llama other figures rigor wording rivals audit outputs.\nCPU only; no model text is generated; the only LLM calls are the (0d) judges (src/run_judges.py).\n\"\"\"\n\nfrom __future__ import annotations\n\nimport argparse\nimport json\nimport resource\nimport sys\nimport time\nfrom pathlib import Path\n\nfrom loguru import logger\n\nWS = Path(__file__).resolve().parent\nsys.path.insert(0, str(WS))\n\nlogger.remove()\nlogger.add(sys.stdout, level=\"INFO\", format=\"{time:HH:mm:ss}|{level:<7}|{message}\")\nlogger.add(WS / \"logs\" / \"eval.log\", rotation=\"30 MB\", level=\"DEBUG\")\n\nSTAGES = [\"inventory\", \"rows\", \"judges\", \"knob\", \"screen\", \"route\", \"llama\", \"other\", \"figures\", \"rigor\", \"wording\", \"rivals\",\n          \"audit\", \"outputs\"]\n\n\ndef _limit_memory(gb: float = 18.0) -> None:\n    try:\n        resource.setrlimit(resource.RLIMIT_AS, (int(gb * 1024 ** 3), int(gb * 1024 ** 3)))\n    except (ValueError, OSError) as e:\n        logger.warning(f\"could not set RLIMIT_AS: {e}\")\n\n\n@logger.catch(reraise=True)\ndef main() -> None:\n    ap = argparse.ArgumentParser()\n    ap.add_argument(\"--stages\", default=\"all\")\n    args = ap.parse_args()\n    stages = STAGES if args.stages == \"all\" else [s.strip() for s in args.stages.split(\",\")]\n    _limit_memory()\n    import pandas as pd\n\n    from src import stages as S\n    for st in stages:\n        t0 = time.time()\n        logger.info(f\"=== stage {st} ===\")\n        getattr(S, f\"stage_{st}\")()\n        logger.info(f\"=== stage {st} done in {time.time() - t0:.1f}s ===\")\n    del pd\n\n\nif __name__ == \"__main__\":\n    main()\n=== PYPROJECT\n[project]\nname = \"record-repair-push-screen\"\nversion = \"0.1.0\"\ndescription = \"Iteration-4 Step 0: record repair and frozen push screen (CPU-only re-analysis of declared dependencies)\"\nrequires-python = \">=3.12,<3.13\"\n# Every package installed in .venv, pinned to the exact version used for the published results\n# (from `uv pip freeze --python .venv/bin/python`; the uv-created venv has no pip executable).\ndependencies = [\n    \"annotated-types==0.8.0\",\n    \"anyio==4.15.1\",\n    \"certifi==2026.10.19\",\n    \"charset-normalizer==3.5.2\",\n    \"cloudpickle==3.1.2\",\n    \"contourpy==1.4.0\",\n    \"cycler==0.12.1\",\n    \"fonttools==4.67.0\",\n    \"h11==0.16.0\",\n    \"httpcore2==2.15.1\",\n    \"httpx2==2.15.1\",\n    \"idna==3.20\",\n    \"iniconfig==2.3.1\",\n    \"jiter==0.17.0\",\n    \"joblib==1.6.0\",\n    \"kiwisolver==1.5.1\",\n    \"loguru==0.7.3\",\n    \"matplotlib==3.11.2\",\n    \"narwhals==2.27.1\",\n    \"numpy==2.5.4\",\n    \"openai==3.35.1\",\n    \"packaging==26.3\",\n    \"pandas==3.0.6\",\n    \"pillow==13.0.0\",\n    \"pluggy==1.7.0\",\n    \"pyarrow==26.0.0\",\n    \"pydantic==2.14.1\",\n    \"pydantic-core==2.50.1\",\n    \"pygments==2.21.0\",\n    \"pyparsing==3.3.3\",\n    \"pytest==9.1.1\",\n    \"python-dateutil==2.9.0.post0\",\n    \"requests==2.34.2\",\n    \"scikit-learn==1.9.1\",\n    \"scipy==1.18.1\",\n    \"six==1.17.0\",\n    \"sniffio==1.3.1\",\n    \"tenacity==9.2.1\",\n    \"threadpoolctl==3.7.0\",\n    \"truststore==0.10.5\",\n    \"typing-extensions==4.16.0\",\n    \"typing-inspection==0.4.4\",\n    \"urllib3==2.8.0\",\n]\n=== PATHS\n{\n \"AII_ITER1\": \"/ai-inventor/aii_data/runs/run_4VFKidE1bxPG/3_invention_loop/iter_1/gen_art\",\n \"AII_ITER2\": \"/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art\",\n \"AII_ITER3\": \"/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art\"\n}\n=== pytest.ini\n[pytest]\ntestpaths = tests\naddopts = -q\n=== SRC\n478106 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/audit/judge_cache.jsonl\n214194 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/audit/judge_results.json\n18862 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/audit/manual_pass.json\n2730 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/audit/manual_sample_ids.json\n2653 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/audit/placebos.json\n9350 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/audit/placebos.py\n93973 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/audit/pool.parquet\n5643 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/audit/pool_events.json\n5038 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/audit/rederive.json\n21628 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/audit/rederive.py\n3401 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/audit/rederive_extra.json\n10666 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/audit/rederive_extra.py\n857 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/audit/rerun/cand.py\n564966 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/audit/rerun/cases.json\n414 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/audit/rerun/checker.py\n1222 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/audit/rerun/harness.py\n51 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/audit/rerun/ref.py\n121797 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/data/knob.parquet\n2198246 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/data/rows.parquet\n7131 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/figures/captions.json\n80051 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/figures/composite_2x2_activation.pdf\n187860 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/figures/composite_2x2_activation.png\n54937 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/figures/marker_M1_fig_manifold_t1_baseline.pdf\n55403 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/figures/marker_M1_fig_manifold_t1_baseline.png\n60116 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/figures/marker_M2_fig_manifold_t1_single_bfs.pdf\n61207 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/figures/marker_M2_fig_manifold_t1_single_bfs.png\n59918 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/figures/marker_M3_fig_manifold_t1_multi_TOP5.pdf\n61192 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/figures/marker_M3_fig_manifold_t1_multi_TOP5.png\n49735 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/figures/marker_M4_fig_manifold_t2_los_bf_spfa.pdf\n49791 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/figures/marker_M4_fig_manifold_t2_los_bf_spfa.png\n336282 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/figures/marker_M5_fig7_manifold.pdf\n371473 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/figures/marker_M5_fig7_manifold.png\n7131 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/results/figures.json\n7527 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/results/llama.json\n32913 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/results/other_audit.json\n5515 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/results/rigor.json\n4098 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/results/rivals.json\n16884 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/results/route.json\n923 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/results/screen_summary.json\n11108 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/results/wording.json\n0 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/src/__init__.py\n11227 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/src/figures.py\n16499 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/src/knob.py\n3561 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/src/labels.py\n7862 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/src/llama.py\n18169 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/src/other_assemble.py\n17665 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/src/other_audit.py\n28872 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/src/outputs.py\n2844 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/src/paths.py\n10216 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/src/rigor.py\n6975 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/src/rivals.py\n15059 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/src/route.py\n9081 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/src/rows.py\n2458 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/src/run_judges.py\n27946 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/src/screen.py\n8266 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/src/stages.py\n11151 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/src/stats.py\n7687 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/src/wording.py\n42426 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/tables/arm_dictionary.csv\n13759 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/tables/catalogue_only_avoidance.csv\n896 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/tables/defined_only_hits.csv\n1584 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/tables/knob_rows_not_recomputed.csv\n500652 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/tables/knob_table.csv\n9838 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/tables/llama_hits.csv\n4452 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/tables/merge_intervals_correction.csv\n2104 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/tables/other_audit_events.csv\n136813 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/tables/other_audit_programs.csv\n7396 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/tables/per_task_verdict.csv\n1424 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/tables/random_direction_counts.csv\n1104 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/tables/rival_predictor_values.csv\n1720 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/tables/rival_predictors.csv\n6424 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/tables/route_landing.csv\n4170 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/tables/table110_alpha2.csv\n3183 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/tables/table82_distinct_rows.csv\n6319 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/tables/verification_targets.csv\n3555 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/tests/test_stats.py", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [13] TOOL CALL — Bash · 2026-10-26 10:51:29 UTC

```
Read artifact README and reproducibility notes:
A=/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3; cat $A/README.md; echo "=== REPRO"; cat $A/reproducibility.md
```

### [14] TOOL RESULT — Bash · 2026-10-26 10:51:29 UTC

````
{"stdout": "# Fixing the record, freezing the push screen\n\nThis is Step 0 of iteration 4 of an algorithm-choice study on Qwen3-8B, with Llama-3.1-8B as the replication model. It runs on CPU only. No model text is generated, and the only LLM calls are the blind judges of the 'other' audit (0d), which cost **USD 0.22**. Every number is recomputed from labelled rows already on disk in the 11 declared dependencies. Each number cites its source as `<artifact_id>:<relative path>`.\n\n## Headline results\n\n| Item | Result |\n|---|---|\n| 0a knob table | 1,120 cells (artifact × task × arm × dial), each priced against its own twin. 25 of 27 quoted review numbers reproduce. Two are corrected. First, \"nothing reaches Hill 1.5 under 20 points on R1/R3/R6/T11/T13/T14\" is false once the T14 modal ban (1.78 at 17 pts) and the exp14 exposure arms are counted. Second, the two-sum α=2 avoidance is 0.469 on the attempted denominator, against the review's 0.48 (= 1 − 26/50). |\n| 0i screen | `screen.json`, sha256 `d6a2ca9711f461973c39482314a523d448d0590cb40e32432826dec1da4846e8`. Movable tasks: T03, T05, T06, T1, T10, T2, which is exactly the frozen C1 set. Movable against catalogue-only ban avoidance ≥ 0.5 gives a 6/0/0/8 table (one-sided Fisher p = 1/3003). This is descriptive: screen, not confirmation. |\n| 0b route landing | All 7 recorded readings reproduce. JS divergence matches exp16 to 1e-6 on 17 of 17 arms. exp16's pooled F_prompt 0.611 [0.06, 1.17] and F_direct 0.744 [0.38, 1.11] reproduce exactly. Without T13 they are 0.648 [−0.08, 1.38] and 0.865 [0.68, 1.05]. T13 is not gated under catalogue-only avoidance (0.15). |\n| 0c Llama hits | With 'other' removed as nominee and as landing: LADDER 6/13 (Poisson-binomial p = 0.100) and ASSOCIATE 7/13 (p = 0.032). Table 102 checks 3/3. Snap-back: the default takes 0.72, 0.73 and 0.93 of non-banned attempts. |\n| 0d 'other' audit | 21 events and 226 unique programs, of which 6 pass. Final classes: 68 catalogue variant, 156 degenerate, 2 labeller miss, **0 novel**. Judge κ(A,B) = 0.77. Judge A falls below the 5/6 control gate and gets no weight. The manual read covers 73 programs. Residue-gated events are exp13 T13, exp16 T13:a and Llama T06. Merge intervals: 29 coverage-array, 12 unsorted-sweep and 3 other programs, all failing. |\n| 0e figures | Five captioned markers (M1–M5) and a 2×2 composite in activation coordinates (MDS stress-1 0.025/0.006). At the fixed g16 position, BFS's nearest neighbour is IDA* rather than BiBFS. |\n| 0g rigor | Defined-only hit rates. The exposure SUBTRACT forecast is defined for 4 of 33 shown algorithms and hits 4/4 in both arms. Table 82 per distinct row: gain 0/11, residual 0/11, implied mass 8/11 (6 of them sham rows). |\n| 0h wording | Replacement sentences for Section 3.10 are in `corrections.json` and `results/wording.json`. |\n| 0j rivals | Spearman ρ against catalogue-only avoidance: movable 0.86, max E_t 0.85, can 0.16, clarity −0.07, FRLP runner-up mass 0.19, nonce −0.19, novelty 0.35. These are screen values, not confirmation. |\n| audit | `audit/rederive.py` is a stdlib-only reimplementation: 29 checks, 0 mismatches, and the screen sha256 matches byte for byte. `audit/rederive_extra.py` adds 12 checks (sklearn/scipy), with 0 mismatches. All 7 placebos fail to show an effect, as required. |\n\n## Layout\n\n| Path | What it is |\n|---|---|\n| `eval.py` | Single entry point with stage flags (`--stages all` or a comma list). |\n| `src/paths.py` | Maps artifact ids to dependency roots (`AII_ITER1/2/3`) and builds citations. |\n| `src/labels.py` | G1: catalogues (exp11 `spec.json`; T1/T2 lists), aliases, defaults. |\n| `src/rows.py` | G2: unified row table, written to `data/rows.parquet`. |\n| `src/stats.py` | Rarefied Hill-1, Good's coverage, Newcombe, Poisson-binomial, permutation Spearman, jackknife, kappa. |\n| `src/knob.py`, `src/screen.py` | 0a knob table, direction counts, Table 110, verification targets, per-task verdicts; 0i screen. |\n| `src/route.py`, `src/llama.py` | 0b route landing and route fractions; 0c Llama hit rules. |\n| `src/other_audit.py`, `src/run_judges.py`, `src/other_assemble.py` | 0d pool and features, blind judges, assembly. |\n| `src/figures.py`, `src/rigor.py`, `src/wording.py`, `src/rivals.py`, `src/outputs.py` | 0e, 0g, 0h and 0j, plus the output contract. |\n| `screen_rule.py` | Stdlib-only screen rule. `python screen_rule.py screen_input.json out.json` reproduces `screen.json` byte for byte. |\n| `screen.json`, `screen.sha256`, `screen_extras.json`, `screen_input.json` | Frozen screen core, its hash, the unhashed extras (per-direction rows, power notes, Fisher p, discrepancies) and the rule input. |\n| `full_eval_out.json` (= `eval_out.json`), `mini_eval_out.json`, `preview_eval_out.json` | `exp_eval_sol_out` output. Section summaries are under `metadata.sections`, with one dataset per section. |\n| `corrections.json` | Each review item (0a–0j) with replacement sentences, recomputed numbers, sources and a status. 0f is delivered by this iteration's research artifact (Table 92b). |\n| `tables/` | `knob_table.csv`, `arm_dictionary.csv`, `random_direction_counts.csv`, `table110_alpha2.csv`, `verification_targets.csv`, `per_task_verdict.csv`, `route_landing.csv`, `llama_hits.csv`, `other_audit_programs.csv`, `other_audit_events.csv`, `catalogue_only_avoidance.csv`, `merge_intervals_correction.csv`, `defined_only_hits.csv`, `table82_distinct_rows.csv`, `rival_predictors.csv`, `rival_predictor_values.csv`, `knob_rows_not_recomputed.csv`. |\n| `figures/` | Captioned markers `marker_M1..M5_*.{png,pdf}`, `composite_2x2_activation.{png,pdf}` and `captions.json`. |\n| `audit/` | `rederive.py`/`rederive.json`, `rederive_extra.py`/`rederive_extra.json`, `placebos.py`/`placebos.json`, judge cache (`judge_cache.jsonl`), judge results, the 0d pool (`pool.parquet`, `pool_events.json`), the manual pass (`manual_pass.json`, `manual_sample_ids.json`), and the hidden-test re-run harness (`rerun/`). |\n| `results/` | One JSON per section: screen summary, route, llama, other audit, figures, rigor, wording, rivals. |\n| `inputs.json` | G0 inventory of every declared input file: sha256, bytes, rows, fields. |\n| `tests/test_stats.py` | Unit tests on hand-computed toy cells. Run with `uv run pytest`. |\n| `reproducibility.md` | Seeds, versions, deviations and departures from the plan. |\n\n## How to run\n\n```bash\nuv sync --frozen                     # .venv with the exact versions pinned in pyproject.toml / uv.lock (Python 3.12)\n# dependency artifacts are read from sibling folders named by artifact id (or original folder name) under\n# AII_DEPS_DIR (default: this folder's parent); on the run server AII_ITER1/2/3 or paths.local.json are used\nuv run eval.py --stages all          # about 1.5 minutes; the judge stage reuses audit/judge_cache.jsonl, so it costs nothing\nuv run pytest                         # unit tests\npython3 -I audit/rederive.py         # independent re-derivation (stdlib only)\nuv run python audit/rederive_extra.py   # second independent re-derivation with shuffled-input placebos\n```\n\nSee `reproducibility.md` for the full step-by-step record (versions, seeds, hardware, runtimes, expected numbers).\n\nThe judge stage (`src/run_judges.py`) needs `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY` only for prompts that are not already in `audit/judge_cache.jsonl`. It checks `GET <base>/key` first, stops if less than USD 3 remains in the shared pot, stops at USD 1.8 of its own spend, and cancels everything on the first budget 403.\n\n## Publishing notes\n\n`paths.local.json` holds the machine-specific dependency roots and is excluded from the published repository, along with `.venv/`, `__pycache__/` and `.pytest_cache/` (upload-ignore regexes: `(^|/)\\.venv/`, `(^|/)__pycache__/`, `(^|/)\\.pytest_cache/`, `(^|/)paths\\.local\\.json$`).\n\n## Kept artifacts\n\nEverything except the virtual environment and caches is kept on the run's volume at the paths above. All kept files are under 10 MB and are published.\n\n## Restoring removed files\n\n| Removed path | How to restore |\n|---|---|\n| `.venv/` | `uv sync --frozen` (exact pins from `pyproject.toml` / `uv.lock`) |\n| `**/__pycache__/`, `.pytest_cache/` | Regenerated automatically by running `uv run eval.py --stages all` or `uv run pytest`. |\n=== REPRO\n# Reproducing \"Fixing the record, freezing the push screen\"\n\nThis artifact is a CPU-only re-analysis. It generates no model text. Its only network calls are the cached LLM-judge calls of the 'other' audit (0d). Every path below is relative to this artifact's folder.\n\n## 1. Get the artifact\n\nThe workspace is published as one folder of a public GitHub repository. The 11 dependency artifacts it reads are published in the same repository as sibling folders.\n\n```bash\ngit clone <repository URL>\ncd <repository>/<this artifact's folder>      # the folder that contains eval.py, screen.json, screen_rule.py\n```\n\n## 2. System, Python and libraries (what was actually used)\n\n- OS: Debian 12 container (any recent Ubuntu works). No system packages are needed beyond `curl` and `git`.\n- uv 0.6.14 and Python 3.12.14 (uv-managed).\n- Hardware: 6 vCPUs (AMD EPYC 7443, cgroup quota 5.6 CPUs) and a 28 GB RAM limit. The pod had an NVIDIA RTX 2000 Ada (16 GB), which was **not used**.\n\n```bash\ncurl -LsSf https://astral.sh/uv/install.sh | sh        # installs uv (0.6.14 was used)\nuv python install 3.12\nuv sync --frozen                                       # creates .venv with the exact pins in pyproject.toml / uv.lock\n```\n\nWhat was actually run on the server, before the versions were frozen, was:\n\n```bash\nuv venv .venv --python=3.12\nuv pip install --python=.venv/bin/python numpy pandas scipy scikit-learn matplotlib loguru openai pyarrow tenacity requests pytest\n```\n\nThat resolved to the versions now pinned in `pyproject.toml`. The key ones are numpy 2.5.4, pandas 3.0.6, scipy 1.18.1, scikit-learn 1.9.1, matplotlib 3.11.2, pyarrow 26.0.0, loguru 0.7.3, openai 3.35.1, requests 2.34.2, tenacity 9.2.1 and pytest 9.1.1. A uv venv has no `pip` executable, so the pins come from `uv pip freeze --python .venv/bin/python`.\n\n## 3. Inputs, environment variables and keys\n\n**Dependency artifacts.** They are read only, and each is resolved by artifact id:\n\n| Artifact id | Role | Files read |\n|---|---|---|\n| art_pVlCZ272hDV7 | exp17 | `data/labels.jsonl`, `results/c2d.json`, `figures/fig7_manifold.png` |\n| art_1AYTO1Epb_7t | exp13 | `data/samples.jsonl`, `results/c1_events.jsonl`, `predictions/proximity.json` |\n| art__5akZ9W9iZM4 | exp16 | `data/samples.jsonl`, `results/{landing_by_route,route,screen_paths,prefill,replication}.json` |\n| art_Q-qh-9HhPoWo | exp15 | `data/samples.jsonl`, `results/c1_events.jsonl`, `predictions/forecasts.json`, `results/push_hook_stats.json` |\n| art_WiY4wqHLb9Gy | exp14 | `data/samples.jsonl`, `results/{c1_events.jsonl,c1_summary.json,other_reports.json,advance_rule_null_calibration.json}` |\n| art_ccAbfJVcv0LO | exp18 | `data/samples_*.jsonl`, `results/{c3,novelty_audit,manual_audit}.json` |\n| art_IVZc3TWCeE9f | exp9 | `data/samples.jsonl`, `results/{landing,los,manifold}.json`, `figures/fig_manifold_*.png`, `states/t*/…/part_*.npz` |\n| art_6zBfl3kDjeiP | exp7 | `results/{frlp_cells.jsonl,gate_events.json,association.json}`, `data/forced_labelled.jsonl`, `frozen/ladder_profile.json` |\n| art_0ndRfWKBWclR | exp11 | `bench/*/{spec.json,tests.jsonl,checker.py,references/*.py}`, `data/{association,samples_forced,frlp_cells,samples_pilot,samples_llama_pilot}.jsonl` |\n| art_U5UKkFrOgSsE | iteration-1 exp4 | `data/samples.jsonl` |\n| art_UoCVh2Qe5RZ0 | iteration-1 exp6 | `results/samples.jsonl` |\n\n**How folders are resolved.** `src/paths.py` and the audit scripts look under `AII_DEPS_DIR`, which defaults to `..` (this folder's parent, where the repository's sibling folders sit). Each artifact is found by a folder named after its artifact id, or after its original workspace folder (for example `gen_art_experiment_13`). On the run server, `AII_ITER1`, `AII_ITER2` and `AII_ITER3` (or the unpublished `paths.local.json`) point at the original roots instead.\n\n**Not published.** exp9's `states/` activations (0.95 GB) were kept on the run volume and are not published. Without them, the figures stage records the 2×2 activation composite and the g16 check as `failed` in `results/figures.json`. Every other stage is unaffected.\n\n**User-uploaded inputs.** None are used. The run's upload folder was empty.\n\n**Environment variables (names only).**\n- `AII_DEPS_DIR`: optional.\n- `AII_ITER1`, `AII_ITER2`, `AII_ITER3`: run server only.\n- `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY`: needed only for judge prompts that are not already in the published `audit/judge_cache.jsonl`. With the published cache, no key is needed and no money is spent.\n\n## 4. Commands, in the order they produce the published results\n\n```bash\nuv run eval.py --stages all\n```\n\nThis runs the following stages, about 1.5 minutes in total on the hardware above:\n\n| Stage | What it does |\n|---|---|\n| `inventory` | `inputs.json` |\n| `rows` | `data/rows.parquet`, 65,433 labelled rows |\n| `judges` | 0d pool, features and blind judges; cache hits only |\n| `knob` | 1,120 cells |\n| `screen` | `screen.json`, `screen.sha256`, `screen_extras.json`, verification targets |\n| `route` | |\n| `llama` | |\n| `other` | 0d assembly, with the manual pass read from `audit/manual_pass.json` |\n| `figures` | |\n| `rigor` | |\n| `wording` | |\n| `rivals` | |\n| `audit` | `audit/rederive.py`, `audit/placebos.py`, `audit/rederive_extra.py` |\n| `outputs` | `eval_out.json` (= `full_eval_out.json`), `mini_eval_out.json`, `preview_eval_out.json`, `corrections.json` |\n\nThe extra checks and tools, run separately:\n\n```bash\nuv run pytest                              # 9 unit tests (tests/test_stats.py), ~6 s\npython3 -I audit/rederive.py               # stdlib-only re-derivation: 29 checks, 0 mismatches, ~3 s\nuv run python audit/placebos.py            # 4 placebos, all fail to show an effect, ~9 s\nuv run python audit/rederive_extra.py      # 12 more checks, 3 placebos, ~17 s\npython3 screen_rule.py screen_input.json screen_check.json   # stdlib rule; byte-identical to screen.json\n```\n\n**History notes.**\n- The judge calls were made once by the `judges` stage, through `src/run_judges.py`. That was 472 judge calls plus 20 tie-breaks at temperature 0, about 1.5 minutes, USD 0.223. The models were openai/gpt-4.1-mini, google/gemini-2.5-flash and deepseek/deepseek-chat-v3.1. Re-running reuses `audit/judge_cache.jsonl`, which is keyed by model + sha256 of the prompt.\n- The manual pass (Step C) was done by the executor reading the programs. Its verdicts are stored in `audit/manual_pass.json`, and the code reads them rather than producing them.\n- During development, stages were also run one at a time with `--stages <list>`. The published files come from the final full run, followed by `--stages audit,outputs` once `rederive_extra.py` was added.\n- The pipeline's aii-json formatter then rewrote `full_/mini_/preview_eval_out.json` from `eval_out.json`. `eval.py` writes equivalent variants itself (first 3 examples per dataset; preview strings truncated to 200 characters), so a reader's mini/preview may differ only in whitespace.\n\n**Seeds and settings.**\n- Master seed 20261021. Each cell's seed is `int(sha256('20261021|' + cell_id)[:8], 16)`.\n- Rarefaction: 1,000 subsamples at depth 25. CIs: 1,000 bootstrap replicates × 200 draws (90% percentile).\n- Spearman permutation: 1e6 draws. Placebos: 1,000 / 1e5 / 1e4 / 500 draws.\n- 0d pool: capped at 25 programs per event (seeded). Manual 20% sample: seed 20261021.\n- Judges run at temperature 0.\n\n## 5. What you should get, and where it appears in the paper\n\n| Output | Numbers | Paper location |\n|---|---|---|\n| `screen.json` / `screen.sha256` | sha256 `d6a2ca9711f461973c39482314a523d448d0590cb40e32432826dec1da4846e8`. Movable: T03, T05, T06, T1, T10, T2. Movable × catalogue-only ban avoidance ≥ 0.5 table 6/0/0/8 (Fisher one-sided p = 1/3003, descriptive). | Claim 3a screen and the frozen C1 event set |\n| `tables/knob_table.csv`, `tables/verification_targets.csv` | 1,120 cells. 25 of 27 quoted numbers reproduce. Two are corrected: \"nothing reaches Hill 1.5 under 20 pts on R1/R3/R6/T11/T13/T14\" is false once the T14 modal ban (1.78 at 17 pts) and the exp14 exposure arms are counted; two-sum α=2 avoidance is 0.469 on the attempted denominator, not 0.48. T03 α=1: 7/15 escape (Hill 2.92/2.42/2.32/2.13/2.11). T2: 3/15. | Section 3.2.5 one-statistic knob table; Table 110 (`tables/table110_alpha2.csv`) |\n| `tables/random_direction_counts.csv` | E_t: T03 8/18 (α1, pooled engines), T05 2/3 (α2), T06 1/3 (α2), T10 1/3 (α1, bf16 only), T1 1/15, T2 3/15. | Push-movability screen |\n| `tables/route_landing.csv`, `results/route.json` | All 7 readings reproduce. JS matches exp16 to 1e-6 (17/17). F_prompt 0.611 [0.06, 1.17] and F_direct 0.744 [0.38, 1.11]. Without T13: 0.648 [−0.08, 1.38] and 0.865 [0.68, 1.05]. T13 is not gated under catalogue-only avoidance (0.15). | Section 3.11 route-landing lead; Section 3.10 'carry more' |\n| `tables/llama_hits.csv`, `results/llama.json` | 'Other' excluded: LADDER 6/13 (p 0.100), ASSOCIATE 7/13 (p 0.032). Table 102 checks 3/3. Snap-back 0.72/0.73/0.93. | Section 3.5 scoring note; Table 102; Section 3.10 |\n| `tables/other_audit_*.csv`, `tables/catalogue_only_avoidance.csv`, `tables/merge_intervals_correction.csv` | 226 programs (6 passing): 68 catalogue variant, 156 degenerate, 2 labeller miss, 0 novel. κ(A,B) = 0.77. Residue-gated events: exp13 T13, exp16 T13:a, Llama T06. Merge intervals: 29/12/3, all failing. | Tables 95, 102 and 106 catalogue-only columns; novelty statement |\n| `tables/table82_distinct_rows.csv`, `tables/defined_only_hits.csv` | Table 82: gain 0/11, residual 0/11, implied mass 8/11 (6 sham). Exposure SUBTRACT defined 4/33, hits 4/4 in both arms. | Table 82; Section 3.10 exposure sentence |\n| `tables/rival_predictors.csv` | Spearman ρ: movable 0.86, can 0.16, clarity −0.07, FRLP 0.19, nonce −0.19, novelty 0.35. These are screen values, not confirmation. | Claim 3a rival contrast |\n| `corrections.json` | Replacement sentences for review items 0a–0j. 0f (Table 92b) is delivered by this iteration's research artifact. | Sections 3.5, 3.10, 3.11 |\n| `figures/` | Markers M1–M5 with the position caveat. The 2×2 composite has MDS stress-1 0.025/0.006. | Geometry figures |\n\n## 6. Independently re-derived numbers\n\n- **`audit/rederive.py`** (stdlib only, no `src/` imports) re-derives: the verification targets for T03, T2, T05, T06, T04, the exp13 rows, exp4 and exp6; the screen sha256 (byte for byte) and the movable set; the Llama strict hits and p-values; the route fractions (all five tasks, without T13, catalogue-only); catalogue-only avoidance; the Table 82 hits; and all six rival ρ values.\n- **`audit/rederive_extra.py`** (sklearn / scipy / math) re-derives: judge κ; the control gate; the final class counts and 0 novel; the snap-back and Table 102 counts; the exposure sentence; the exp13 contest with and without T13; the screen Fisher p; the movability ρ; the T10 route readings; and the 60/60 hidden-test re-run.\n- **Placebos.** All 7 fail to show an effect, as required: P1–P4, plus κ, Fisher and Spearman on shuffled input.\n- **Not independently re-derived:**\n  - bootstrap CIs and Good's coverage of the knob table;\n  - the coverage-standardised sensitivity;\n  - per-task best rows;\n  - the defined-only hit-rate table;\n  - the Section 3.10 template-arm (13/19, 15/19) and prefill-depth numbers;\n  - the figure statistics (MDS stress, g16 neighbour order);\n  - the manual merge-interval classes, which are a manual read.", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
````

### [15] ASSISTANT · 2026-10-26 10:51:49 UTC

```
`eval.py` is a thin stage dispatcher over `src/`. Let me look at the stage implementations and the output data structure to decide what can run self-contained in a notebook.
```

### [16] TOOL CALL — Bash · 2026-10-26 10:51:49 UTC

```
Read stages dispatcher and paths module:
A=/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3; cat $A/src/stages.py; echo "=== PATHS.PY"; cat $A/src/paths.py
```

### [17] TOOL RESULT — Bash · 2026-10-26 10:51:49 UTC

```
{"stdout": "\"\"\"Stage implementations called by eval.py. Each stage reads earlier stages' outputs from data/ and results/.\"\"\"\n\nfrom __future__ import annotations\n\nimport hashlib\nimport json\nfrom pathlib import Path\n\nimport pandas as pd\nfrom loguru import logger\n\nfrom src.paths import ARTIFACTS, WS, cite, p\n\nDATA = WS / \"data\"\nRES = WS / \"results\"\nTAB = WS / \"tables\"\nfor _d in (DATA, RES, TAB, WS / \"figures\", WS / \"audit\"):\n    _d.mkdir(exist_ok=True)\n\n# files named in builds_on, per artifact (relative to each workspace)\nDECLARED = {\n    \"exp17\": [\"data/labels.jsonl\", \"results/c2d.json\", \"data/realised_norms.jsonl\", \"results/manifold.json\",\n              \"figures/fig7_manifold.png\", \"figures/fig7_manifold.pdf\"],\n    \"exp13\": [\"data/samples.jsonl\", \"results/c1_events.jsonl\", \"results/analysis.json\", \"predictions/proximity.json\",\n              \"predictions/associate.json\", \"predictions/forecasts.json\", \"src/analyze.py\"],\n    \"exp16\": [\"results/landing_by_route.json\", \"results/shares.json\", \"results/route.json\", \"results/gate.json\",\n              \"results/prefill.json\", \"results/replication.json\", \"results/c1_events.jsonl\", \"data/samples.jsonl\",\n              \"results/screen_paths.json\"],\n    \"exp15\": [\"src/scoring.py\", \"results/c1_events.jsonl\", \"data/samples.jsonl\", \"data/labels.jsonl\",\n              \"results/other_reaudit.json\", \"results/push_hook_stats.json\", \"results/ban_norms.json\",\n              \"predictions/forecasts.json\"],\n    \"exp14\": [\"results/other_reports.json\", \"results/c1_events.jsonl\", \"results/c1_summary.json\",\n              \"results/advance_rule_null_calibration.json\", \"results/correct_other_programs.jsonl\",\n              \"data/samples.jsonl\"],\n    \"exp18\": [\"data/samples_walk.jsonl\", \"data/samples_los.jsonl\", \"data/samples_two_step.jsonl\",\n              \"data/samples_longform.jsonl\", \"data/samples_sham.jsonl\", \"data/samples_fixed_top5.jsonl\",\n              \"results/reach.json\", \"results/c3.json\", \"results/can.json\", \"results/novelty_audit.json\",\n              \"results/manual_audit.json\", \"data/llm_cache.jsonl\", \"results/known_solutions_summary.json\"],\n    \"exp9\": [\"results/manifold.json\", \"results/landing.json\", \"results/los.json\", \"results/persistence.json\",\n             \"data/samples.jsonl\", \"figures/fig_manifold_t1_baseline.png\", \"figures/fig_manifold_t1_single_bfs.png\",\n             \"figures/fig_manifold_t1_multi_TOP5.png\", \"figures/fig_manifold_t2_los_bf_spfa.png\"],\n    \"exp7\": [\"results/frlp_cells.jsonl\", \"results/gate_events.json\", \"results/c1.json\", \"results/association.json\",\n             \"data/forced_labelled.jsonl\", \"data/forced_selected.jsonl\", \"frozen/ladder_profile.json\", \"method.py\"],\n    \"exp11\": [\"data/association.jsonl\", \"data/samples_forced.jsonl\", \"data/frlp_cells.jsonl\",\n              \"data/samples_pilot.jsonl\", \"data/samples_llama_pilot.jsonl\", \"bench/commitment.json\"],\n    \"exp4\": [\"data/samples.jsonl\", \"results/buy_table.json\", \"results/dose_response.json\"],\n    \"exp6\": [\"results/samples.jsonl\", \"results/analysis.json\"],\n}\n\n\ndef sha256_file(path: Path) -> str:\n    h = hashlib.sha256()\n    with path.open(\"rb\") as f:\n        for chunk in iter(lambda: f.read(1 << 20), b\"\"):\n            h.update(chunk)\n    return h.hexdigest()\n\n\ndef _describe(path: Path) -> dict:\n    d: dict = {\"bytes\": path.stat().st_size, \"sha256\": sha256_file(path)}\n    if path.suffix == \".jsonl\":\n        n = 0\n        first = None\n        with path.open() as f:\n            for line in f:\n                if line.strip():\n                    n += 1\n                    if first is None:\n                        first = json.loads(line)\n        d[\"rows\"] = n\n        d[\"fields\"] = sorted(first.keys()) if isinstance(first, dict) else None\n    elif path.suffix == \".json\":\n        try:\n            obj = json.loads(path.read_text())\n            d[\"top_level_keys\"] = sorted(obj.keys())[:60] if isinstance(obj, dict) else f\"list[{len(obj)}]\"\n        except (json.JSONDecodeError, UnicodeDecodeError):\n            d[\"top_level_keys\"] = \"unparseable\"\n    return d\n\n\ndef stage_inventory() -> None:\n    out = []\n    for exp, rels in DECLARED.items():\n        for rel in rels:\n            path = p(exp, rel)\n            rec = {\"artifact_id\": cite(exp, rel).split(\":\")[0], \"relpath\": rel, \"cite\": cite(exp, rel)}\n            if path.exists():\n                rec.update(_describe(path))\n                rec[\"status\"] = \"present\"\n            else:\n                rec[\"status\"] = \"not_computable_from_declared_inputs\"\n            out.append(rec)\n    # bench folders of exp11 (13 tasks)\n    from src.labels import BENCH_DIRS\n    for t, d in BENCH_DIRS.items():\n        for rel in (f\"bench/{d}/spec.json\", f\"bench/{d}/tests.jsonl\"):\n            path = p(\"exp11\", rel)\n            rec = {\"artifact_id\": cite(\"exp11\", rel).split(\":\")[0], \"relpath\": rel, \"cite\": cite(\"exp11\", rel)}\n            rec.update(_describe(path) if path.exists() else {})\n            rec[\"status\"] = \"present\" if path.exists() else \"not_computable_from_declared_inputs\"\n            out.append(rec)\n    (WS / \"inputs.json\").write_text(json.dumps(out, indent=1))\n    miss = [r[\"cite\"] for r in out if r[\"status\"] != \"present\"]\n    logger.info(f\"inventory: {len(out)} files, {len(miss)} missing: {miss}\")\n\n\ndef stage_rows() -> None:\n    from src.rows import build_rows\n    build_rows(DATA / \"rows.parquet\")\n\n\ndef stage_judges() -> None:\n    \"\"\"(0d) Steps A-B: pool, features, blind judges. Re-runs hit audit/judge_cache.jsonl, so no call is paid twice.\"\"\"\n    import subprocess\n    import sys\n    r = subprocess.run([sys.executable, str(WS / \"src\" / \"run_judges.py\")], capture_output=True, text=True, timeout=3600)\n    logger.info(f\"run_judges: {r.stdout.strip()[-400:]}\")\n    if r.returncode:\n        logger.error(r.stderr[-2000:])\n        raise RuntimeError(\"run_judges failed\")\n\n\ndef stage_knob() -> None:\n    from src.knob import KNOB_COLUMNS, arm_dictionary, build_knob_table\n    rows = pd.read_parquet(DATA / \"rows.parquet\")\n    knob = build_knob_table(rows)\n    hook = json.loads(p(\"exp15\", \"results/push_hook_stats.json\").read_text())\n    knob[\"realised_l21_displacement_ratio\"] = [\n        hook.get(a.split(\"_\", 1)[1], {}).get(\"added_over_target_l21\") if (e == \"exp15\" and a.startswith(\"rand_\")) else None\n        for e, a in zip(knob.exp, knob.arm)]\n    knob.to_parquet(DATA / \"knob.parquet\", index=False)\n    knob[KNOB_COLUMNS].to_csv(TAB / \"knob_table.csv\", index=False)\n    arm_dictionary(knob).to_csv(TAB / \"arm_dictionary.csv\", index=False)\n    logger.info(f\"knob table: {len(knob)} rows -> tables/knob_table.csv\")\n\n\ndef stage_screen() -> None:\n    from src.screen import run_screen_stage\n    run_screen_stage()\n\n\ndef stage_route() -> None:\n    from src.route import run_route_stage\n    run_route_stage()\n\n\ndef stage_llama() -> None:\n    from src.llama import run_llama_stage\n    run_llama_stage()\n\n\ndef stage_other() -> None:\n    from src.other_assemble import run_other_stage\n    run_other_stage()\n\n\ndef stage_figures() -> None:\n    from src.figures import run_figures_stage\n    run_figures_stage()\n\n\ndef stage_rigor() -> None:\n    from src.rigor import run_rigor_stage\n    run_rigor_stage()\n\n\ndef stage_wording() -> None:\n    from src.wording import run_wording_stage\n    run_wording_stage()\n\n\ndef stage_rivals() -> None:\n    from src.rivals import run_rivals_stage\n    run_rivals_stage()\n\n\ndef stage_audit() -> None:\n    import subprocess\n    import sys\n    r1 = subprocess.run([sys.executable, \"-I\", str(WS / \"audit\" / \"rederive.py\")], capture_output=True, text=True, timeout=1800)\n    logger.info(f\"audit/rederive.py: {r1.stdout.strip()[-300:]} {r1.stderr.strip()[-300:]}\")\n    r2 = subprocess.run([sys.executable, \"-I\", str(WS / \"audit\" / \"placebos.py\")], capture_output=True, text=True, timeout=1800)\n    logger.info(f\"audit/placebos.py: {r2.stdout.strip()[-300:]} {r2.stderr.strip()[-300:]}\")\n    r3 = subprocess.run([sys.executable, str(WS / \"audit\" / \"rederive_extra.py\")], capture_output=True, text=True, timeout=1800)\n    logger.info(f\"audit/rederive_extra.py: {r3.stdout.strip()[-300:]} {r3.stderr.strip()[-300:]}\")\n    if r1.returncode or r2.returncode or r3.returncode:\n        raise RuntimeError(\"audit scripts failed\")\n\n\ndef stage_outputs() -> None:\n    from src.outputs import run_outputs_stage\n    run_outputs_stage()\n=== PATHS.PY\n\"\"\"Artifact-id -> workspace-root mapping for the 11 declared dependencies (read-only inputs).\n\nRoots come from AII_ITER1/2/3 or the unpublished paths.local.json on the run server, else from published sibling\nfolders under AII_DEPS_DIR (default: this workspace's parent). Every output cites\n'<artifact_id>:<relative path>' and never an absolute path.\n\"\"\"\n\nfrom __future__ import annotations\n\nimport json\nimport os\nfrom pathlib import Path\n\nWS = Path(__file__).resolve().parent.parent\n\n\ndef _local_roots() -> dict[str, str]:\n    \"\"\"Machine-specific roots live in paths.local.json (not published); environment variables take precedence.\"\"\"\n    f = WS / \"paths.local.json\"\n    return json.loads(f.read_text()) if f.exists() else {}\n\n\n_DEFAULT_ROOTS = _local_roots()\n\n# artifact id -> (root env var, workspace folder, short experiment name)\nARTIFACTS: dict[str, tuple[str, str, str]] = {\n    \"art_U5UKkFrOgSsE\": (\"AII_ITER1\", \"gen_art_experiment_4\", \"exp4\"),\n    \"art_UoCVh2Qe5RZ0\": (\"AII_ITER1\", \"gen_art_experiment_6\", \"exp6\"),\n    \"art_6zBfl3kDjeiP\": (\"AII_ITER2\", \"gen_art_experiment_7\", \"exp7\"),\n    \"art_IVZc3TWCeE9f\": (\"AII_ITER2\", \"gen_art_experiment_9\", \"exp9\"),\n    \"art_0ndRfWKBWclR\": (\"AII_ITER2\", \"gen_art_experiment_11\", \"exp11\"),\n    \"art_1AYTO1Epb_7t\": (\"AII_ITER3\", \"gen_art_experiment_13\", \"exp13\"),\n    \"art_WiY4wqHLb9Gy\": (\"AII_ITER3\", \"gen_art_experiment_14\", \"exp14\"),\n    \"art_Q-qh-9HhPoWo\": (\"AII_ITER3\", \"gen_art_experiment_15\", \"exp15\"),\n    \"art__5akZ9W9iZM4\": (\"AII_ITER3\", \"gen_art_experiment_16\", \"exp16\"),\n    \"art_pVlCZ272hDV7\": (\"AII_ITER3\", \"gen_art_experiment_17\", \"exp17\"),\n    \"art_ccAbfJVcv0LO\": (\"AII_ITER3\", \"gen_art_experiment_18\", \"exp18\"),\n}\nBY_EXP = {v[2]: k for k, v in ARTIFACTS.items()}\n\n\ndef root(aid: str) -> Path:\n    \"\"\"Dependency workspace: AII_ITERn (or the unpublished paths.local.json) on the run server; otherwise the\n    published sibling folder under AII_DEPS_DIR (default: this workspace's parent), named by artifact id or by the\n    original workspace folder name.\"\"\"\n    env, folder, _ = ARTIFACTS[aid]\n    base = os.environ.get(env) or _DEFAULT_ROOTS.get(env)\n    if base:\n        return Path(base) / folder\n    deps = Path(os.environ.get(\"AII_DEPS_DIR\") or WS.parent)\n    for cand in (deps / aid, deps / folder, *sorted(deps.glob(f\"*{aid}*\"))):\n        if cand.is_dir():\n            return cand\n    raise FileNotFoundError(f\"dependency {aid} ({folder}) not found under {deps}; set AII_DEPS_DIR or {env}\")\n\n\ndef p(exp_or_aid: str, rel: str) -> Path:\n    \"\"\"Absolute path of a dependency file, addressed by 'exp13' or by artifact id.\"\"\"\n    aid = BY_EXP.get(exp_or_aid, exp_or_aid)\n    return root(aid) / rel\n\n\ndef cite(exp_or_aid: str, rel: str) -> str:\n    aid = BY_EXP.get(exp_or_aid, exp_or_aid)\n    return f\"{aid}:{rel}\"\n\n\ndef exp_name(aid: str) -> str:\n    return ARTIFACTS[aid][2]", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [18] TOOL CALL — Bash · 2026-10-26 10:51:49 UTC

```
Inspect preview eval output structure:
A=/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3; python3 - <<'EOF'
import json
p="/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/preview_eval_out.json"
d=json.load(open(p))
print(type(d), list(d.keys()) if isinstance(d,dict) else len(d))
md=d.get("metadata",{})
print("metadata keys:", list(md.keys()))
for k,v in md.items():
    s=json.dumps(v)
    print("  META", k, len(s), s[:300])
print("metrics_agg" in d, d.get("metrics_agg"))
for ds in d.get("datasets",[]):
    ex=ds.get("examples",[])
    print("DATASET", ds.get("dataset"), "n_examples(preview)=", len(ex))
    if ex:
        e=ex[0]
        for kk,vv in e.items():
            print("    ", kk, "=", str(vv)[:250].replace("\n","\\n"))
EOF
```

### [19] TOOL RESULT — Bash · 2026-10-26 10:51:49 UTC

```
{"stdout": "<class 'dict'> ['metadata', 'metrics_agg', 'datasets']\nmetadata keys: ['evaluation_name', 'artifact_plan_id', 'description', 'screen_sha256', 'corrections', 'sections', 'conventions']\n  META evaluation_name 43 \"iter4_step0_record_repair_and_push_screen\"\n  META artifact_plan_id 28 \"gen_plan_evaluation_1_idx1\"\n  META description 205 \"CPU-only record repair of iteration-3 numbers and the frozen push-movability screen; every number recomputed from labelled rows of the 11 declared dependencies with '<artifact_id>:<relative path>' pro...\"\n  META screen_sha256 66 \"d6a2ca9711f461973c39482314a523d448d0590cb40e32432826dec1da4846e8\"\n  META corrections 18 \"corrections.json\"\n  META sections 31205 {\"knob_table\": {\"n_rows\": 1120, \"file\": \"tables/knob_table.csv\", \"arm_dictionary\": \"tables/arm_dictionary.csv\", \"random_direction_counts\": \"tables/random_direction_counts.csv\", \"table110\": \"tables/table110_alpha2.csv\", \"verification\": {\"n\": 27, \"matched\": 25}, \"per_task_verdict\": [{\"task\": \"T03\", \"b\n  META conventions 373 {\"H1r25\": \"correct-only, mechanism-labelled Hill-1 rarefied to depth 25 (1,000 subsamples); 90% percentile bootstrap (1,000 x 200), template clusters when 5 templates have >= 5 correct programs, iid interval bes...\", \"pass_cost\": \"100 x (pass_twin - pass_arm), Newcombe hybrid-score 95% interval\", \"e\nTrue {'n_knob_rows': 1120.0, 'n_targets': 27.0, 'n_targets_matched': 25.0, 'n_movable_tasks': 6.0, 'E_T03_a1': 0.4444444444444444, 'E_T2_a1': 0.2, 'E_T05_a2': 0.6666666666666666, 'E_T06_a2': 0.3333333333333333, 'E_T1_a1': 0.06666666666666667, 'E_T10_a1': 0.3333333333333333, 'screen_fisher_p_descriptive': 0.000333000333000333, 'screen_balanced_accuracy': 1.0, 'llama_assoc_hits_excl_other': 7.0, 'llama_ladder_hits_excl_other': 6.0, 'llama_assoc_p_excl_other': 0.03171599451303157, 'llama_ladder_p_excl_other': 0.1000374430727024, 'route_F_prompt_all5': 0.6111111111111112, 'route_F_direct_all5': 0.7439613526570049, 'route_F_prompt_wo_T13': 0.647887323943662, 'route_F_direct_wo_T13': 0.8647887323943663, 'route_F_prompt_cat_all5': 0.6341463414634146, 'route_F_direct_cat_all5': 0.8238482384823849, 'route_readings_matched': 7.0, 'other_n_programs': 226.0, 'other_n_passed': 6.0, 'other_n_novel_confirmed': 0.0, 'judge_kappa': 0.7746996169788551, 'judge_agreement': 0.915929203539823, 'rival_rho_movability': 0.8612327526892111, 'rival_rho_max_E_t': 0.8500202673964815, 'rival_rho_can': 0.1621954873394075, 'rival_rho_clarity': -0.06505490571714548, 'rival_rho_frlp': 0.18502247526320056, 'rival_rho_nonce': -0.19116713782225253, 'rival_rho_novelty': 0.3532688377417424, 'table82_hits_implied': 8.0, 'table82_hits_gain': 0.0, 'rederive_n_checks': 29.0, 'rederive_n_mismatches': 0.0, 'placebos_failed_as_required': 4.0, 'rederive_extra_n_checks': 12.0, 'rederive_extra_n_mismatches': 0.0, 'rederive_extra_placebos_failed_as_required': 3.0, 'openrouter_usd': 0.0, 'n_qualify_dirs_R1': 0.0, 'n_qualify_dirs_R3': 0.0, 'n_qualify_dirs_R6': 0.0, 'n_qualify_dirs_T03': 7.0, 'n_qualify_dirs_T04': 0.0, 'n_qualify_dirs_T05': 1.0, 'n_qualify_dirs_T06': 1.0, 'n_qualify_dirs_T08': 0.0, 'n_qualify_dirs_T1': 0.0, 'n_qualify_dirs_T10': 0.0, 'n_qualify_dirs_T11': 0.0, 'n_qualify_dirs_T13': 0.0, 'n_qualify_dirs_T14': 0.0, 'n_qualify_dirs_T2': 0.0}\nDATASET knob_table n_examples(preview)= 3\n     input = art_0ndRfWKBWclR | task R1 | arm llama_pilot_fp8 | dial {} | vllm/fp8 | n=50\n     output = H1r25=nan CI90=[NaN, NaN]; pass=0.040; cost=nan pts vs none; offdef=0.439; cat_only=0.098\n     metadata_row_id = K0000\n     metadata_class = control\n     metadata_family = pilot\n     metadata_model = meta-llama/Llama-3.1-8B-Instruct\n     metadata_ref_arm = \n     metadata_correct_composition = {\"dp_bisect\": 1, \"greedy_end\": 1}\n     metadata_attempted_composition = {\"greedy_end\": 23, \"other\": 14, \"dp_bisect\": 3, \"dag_longest_path\": 1}\n     metadata_flags = below_depth\n     metadata_sources = art_0ndRfWKBWclR:data/samples_llama_pilot.jsonl\n     predict_escape = null\n     predict_qualify = null\n     eval_pass_rate = 0.04\n     eval_offdef_share = 0.4390243902439024\n     eval_cat_only_avoidance = 0.0975609756097561\n     eval_coverage = 0.0\n     eval_S_obs = 2.0\n     eval_n = 50.0\nDATASET verification_targets n_examples(preview)= 3\n     input = T03 alpha 1: escaping directions of 15 (exp17)\n     output = \"7/15\"\n     metadata_target_id = T03_a1_escape\n     metadata_expected = \"7/15\"\n     metadata_tolerance = exact\n     metadata_source = art_pVlCZ272hDV7:data/labels.jsonl\n     metadata_explanation = \n     predict_recomputed = \"7/15\"\n     eval_match = 1.0\nDATASET push_screen n_examples(preview)= 3\n     input = task T03: push-movability screen (frozen, sha256 d6a2ca9711f4)\n     output = movable=1; E_t(a1)=0.4444; E_t(a2)=1.0; push_top1=quickselect; cat-only ban avoidance=0.97\n     metadata_push_landing = {\"heapify_pop\": 0.0032, \"quickselect\": 0.6457, \"size_k_heap\": 0.3511}\n     metadata_power_note = {\"K_direction_alpha_cells\": 21, \"n_escape\": 11, \"ub90_per_direction_escape_if_zero\": null}\n     metadata_in_c1_event_set = True\n     predict_movable = 1\n     predict_push_top1 = quickselect\n     eval_E_t_a1 = 0.4444\n     eval_E_t_a2 = 1.0\n     eval_movable = 1.0\n     eval_cat_only_ban_avoidance = 0.97\n     eval_ban_avoidance_ge_0_5 = 1.0", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [20] ASSISTANT · 2026-10-26 10:51:57 UTC

```
Let me see all 12 datasets with sizes (summarised programmatically), plus the core metric code (`screen_rule.py`, `src/stats.py`).
```

### [21] TOOL CALL — Bash · 2026-10-26 10:51:57 UTC

```
Summarise all datasets in full eval output:
python3 - <<'EOF'
import json
p="/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/full_eval_out.json"
d=json.load(open(p))
for ds in d["datasets"]:
    ex=ds["examples"]
    keys=sorted({k for e in ex for k in e})
    print(f"DATASET {ds['dataset']:<28} n={len(ex):>5}  bytes={len(json.dumps(ex)):>8}  keys={keys}")
EOF
```

### [22] TOOL RESULT — Bash · 2026-10-26 10:51:57 UTC

```
{"stdout": "DATASET knob_table                   n= 1120  bytes= 1007370  keys=['eval_H1r10', 'eval_H1r25', 'eval_H1r25_cat', 'eval_S_obs', 'eval_cat_only_avoidance', 'eval_coverage', 'eval_n', 'eval_offdef_share', 'eval_pass_cost_pts', 'eval_pass_rate', 'input', 'metadata_attempted_composition', 'metadata_ci_unit', 'metadata_class', 'metadata_correct_composition', 'metadata_family', 'metadata_flags', 'metadata_model', 'metadata_ref_arm', 'metadata_row_id', 'metadata_sources', 'output', 'predict_escape', 'predict_qualify']\nDATASET verification_targets         n=   27  bytes=   12847  keys=['eval_match', 'input', 'metadata_expected', 'metadata_explanation', 'metadata_source', 'metadata_target_id', 'metadata_tolerance', 'output', 'predict_recomputed']\nDATASET push_screen                  n=   14  bytes=    7716  keys=['eval_E_t_a1', 'eval_E_t_a2', 'eval_ban_avoidance_ge_0_5', 'eval_cat_only_ban_avoidance', 'eval_movable', 'input', 'metadata_in_c1_event_set', 'metadata_power_note', 'metadata_push_landing', 'output', 'predict_movable', 'predict_push_top1']\nDATASET random_directions            n=  108  bytes=   36769  keys=['eval_H1r25', 'eval_n', 'eval_pass_cost_pts', 'input', 'metadata_knob_row_id', 'metadata_offdef_cat_counts', 'metadata_source', 'output', 'predict_qualify']\nDATASET route_landing                n=   25  bytes=   13561  keys=['eval_JS_vs_a', 'eval_hit_association', 'eval_hit_frlp', 'eval_hit_proximity', 'eval_hit_push', 'eval_null_q95', 'input', 'metadata_correct_composition', 'metadata_default', 'output', 'predict_association_modal', 'predict_frlp_runner_up', 'predict_modal_nondefault', 'predict_proximity_top1', 'predict_push_top1']\nDATASET llama_hits                   n=   18  bytes=   11511  keys=['eval_ASSOCIATE_hit_excl_other', 'eval_LADDER_hit_excl_other', 'eval_PROXIMITY_hit_excl_other', 'eval_SUBTRACT_hit_excl_other', 'eval_chance', 'eval_n_nonbanned', 'input', 'metadata_event_type', 'metadata_gate_pass', 'metadata_rule_recorded', 'output', 'predict_ASSOCIATE', 'predict_LADDER', 'predict_PROXIMITY', 'predict_SUBTRACT']\nDATASET other_audit                  n=  226  bytes=  170241  keys=['eval_nearest_known_jaccard', 'eval_passed', 'input', 'metadata_features', 'metadata_manual_reason', 'metadata_nearest_known', 'output', 'predict_consensus', 'predict_judge_A', 'predict_judge_B', 'predict_judge_C_tiebreak']\nDATASET figures                      n=    7  bytes=    5847  keys=['input', 'metadata_file_png', 'metadata_note', 'metadata_panels', 'metadata_source', 'output']\nDATASET rigor                        n=   24  bytes=    5494  keys=['eval_fractional_rate', 'eval_hit_gain', 'eval_hit_implied', 'eval_hit_rate_defined_only', 'eval_hit_residual', 'eval_n_defined', 'input', 'output', 'predict_argmax_gain', 'predict_argmax_implied_mass', 'predict_argmax_residual_gain']\nDATASET wording_section_3_10         n=    4  bytes=    2533  keys=['input', 'metadata_sources', 'output']\nDATASET rival_predictors             n=    7  bytes=    3837  keys=['eval_balanced_accuracy', 'eval_fisher_p', 'eval_kendall_tau_b', 'eval_p_holm', 'eval_p_perm', 'eval_spearman_rho', 'input', 'metadata_confusion_table', 'metadata_label', 'metadata_median_cut', 'output', 'predict_beats_movability', 'predict_direction']\nDATASET audit                        n=   48  bytes=    9789  keys=['eval_failed_as_required', 'eval_match', 'input', 'metadata_expected', 'output', 'predict_status']", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [23] TOOL CALL — Bash · 2026-10-26 10:51:57 UTC

```
Read screen rule and stats module:
A=/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3; cat $A/screen_rule.py; echo "=== STATS"; cat $A/src/stats.py
```

### [24] TOOL RESULT — Bash · 2026-10-26 10:51:57 UTC

```
{"stdout": "#!/usr/bin/env python3\n\"\"\"Push-movability screen rule (stdlib only), so parallel artifacts can recompute screen.json byte for byte.\n\nInput JSON (path as argv[1], or stdin):\n  {\"direction_rows\": [{\"task\", \"alpha\", \"direction_id\", \"engine\", \"n\", \"n_attempted\", \"n_default\", \"n_passed\",\n                       \"twin_n\", \"twin_n_attempted\", \"twin_n_default\", \"twin_n_passed\",\n                       \"offdef_cat_counts\": {label: count}}, ...],\n   \"ban_avoidance\": {task: catalogue-only modal-ban avoidance},\n   \"tasks\": [...], \"c1_event_set\": [...], \"source_sha256\": {cite: sha256}}\nOutput: canonical screen-core JSON on stdout (or argv[2]); its sha256 on stderr.\n\nRule (Claim 3a screen): ESCAPE(d, t, a) iff offdef(d) - offdef(twin) >= 0.20 and pass(d) >= 0.8 x pass(twin),\nwith offdef = 1 - n_default / n_attempted and pass = n_passed / n. E_t(a) = escaping / run at alpha a;\nMOVABLE(t) = 1 iff E_t(a) > 0 for some a <= 2. Push landing over escaping directions:\nw_X = sum_d e_d * share_d(X | off-default catalogue attempts) / sum_d e_d, e_d = offdef(d) - offdef(twin);\n'other' is excluded. Screen prediction: movable implies catalogue-only ban avoidance >= 0.5.\n\"\"\"\n\nfrom __future__ import annotations\n\nimport hashlib\nimport json\nimport sys\n\nESCAPE_MARGIN = 0.20\nPASS_RATIO = 0.8\nALPHAS = (1.0, 2.0)\nRULE_TEXT = \"movable(t) implies catalogue-only modal-ban avoidance(t) >= 0.5\"\nESCAPE_TEXT = (\"escape(d,t,a): offdef(d)-offdef(twin) >= 0.20 and pass(d) >= 0.8*pass(twin); \"\n               \"offdef = 1 - n_default/n_attempted; pass = n_passed/n (no-code rows fail)\")\n\n\ndef _r(x):\n    if isinstance(x, float):\n        return round(x, 4)\n    if isinstance(x, dict):\n        return {k: _r(v) for k, v in x.items()}\n    if isinstance(x, list):\n        return [_r(v) for v in x]\n    return x\n\n\ndef canonical_bytes(obj) -> bytes:\n    return (json.dumps(_r(obj), sort_keys=True, ensure_ascii=True, separators=(\",\", \":\")) + \"\\n\").encode(\"ascii\")\n\n\ndef offdef(n_default: int, n_attempted: int):\n    return 1.0 - n_default / n_attempted if n_attempted else None\n\n\ndef escape_of(row: dict):\n    od = offdef(row[\"n_default\"], row[\"n_attempted\"])\n    tw = offdef(row[\"twin_n_default\"], row[\"twin_n_attempted\"])\n    if od is None or tw is None or not row[\"n\"] or not row[\"twin_n\"]:\n        return False, 0.0\n    p, pt = row[\"n_passed\"] / row[\"n\"], row[\"twin_n_passed\"] / row[\"twin_n\"]\n    excess = od - tw\n    # 1e-9 guards float noise at the exact 0.20 boundary (e.g. 0.30 - 0.10)\n    return bool(excess >= ESCAPE_MARGIN - 1e-9 and p >= PASS_RATIO * pt - 1e-12), excess\n\n\ndef build_core(inp: dict) -> dict:\n    tasks = sorted(inp[\"tasks\"])\n    per = {}\n    for t in tasks:\n        rows = [r for r in inp[\"direction_rows\"] if r[\"task\"] == t]\n        rec = {}\n        movable = 0\n        num: dict = {}\n        den = 0.0\n        for a in ALPHAS:\n            ra = [r for r in rows if float(r[\"alpha\"]) == a]\n            n_esc = 0\n            for r in ra:\n                esc, e = escape_of(r)\n                if esc:\n                    n_esc += 1\n                    cnt = {k: v for k, v in r[\"offdef_cat_counts\"].items() if k != \"other\" and v > 0}\n                    tot = sum(cnt.values())\n                    if tot > 0:\n                        den += e\n                        for k, v in cnt.items():\n                            num[k] = num.get(k, 0.0) + e * v / tot\n            key = f\"alpha_{int(a)}\"\n            rec[key] = {\"n_directions_run\": len(ra), \"n_escape\": n_esc,\n                        \"E_t\": (n_esc / len(ra)) if ra else None}\n            if ra and n_esc > 0:\n                movable = 1\n        land = {k: v / den for k, v in sorted(num.items())} if den > 0 else {}\n        top1 = sorted(land.items(), key=lambda kv: (-round(kv[1], 12), kv[0]))[0][0] if land else None\n        av = inp[\"ban_avoidance\"].get(t)\n        rec.update({\"movable\": movable, \"push_landing\": land, \"push_top1\": top1, \"cat_only_ban_avoidance\": av,\n                    \"ban_avoidance_ge_0_5\": (None if av is None else bool(av >= 0.5))})\n        per[t] = rec\n    return {\"screen_version\": \"iter4-step0\", \"tasks\": per, \"c1_event_set\": sorted(inp[\"c1_event_set\"]),\n            \"screen_rule\": RULE_TEXT, \"escape_rule\": ESCAPE_TEXT,\n            \"movable_tasks\": sorted(t for t in tasks if per[t][\"movable\"]),\n            \"source_sha256\": dict(sorted(inp[\"source_sha256\"].items()))}\n\n\ndef main() -> None:\n    raw = open(sys.argv[1]).read() if len(sys.argv) > 1 and sys.argv[1] != \"-\" else sys.stdin.read()\n    core = build_core(json.loads(raw))\n    b = canonical_bytes(core)\n    if len(sys.argv) > 2:\n        open(sys.argv[2], \"wb\").write(b)\n    else:\n        sys.stdout.write(b.decode(\"ascii\"))\n    sys.stderr.write(hashlib.sha256(b).hexdigest() + \"\\n\")\n\n\nif __name__ == \"__main__\":\n    main()\n=== STATS\n\"\"\"Shared statistics (Section 1 of the plan). Unit-tested in tests/test_stats.py on hand-computed toy cells.\"\"\"\n\nfrom __future__ import annotations\n\nimport hashlib\nimport itertools\nimport math\nfrom collections import Counter\nfrom typing import Iterable, Sequence\n\nimport numpy as np\nfrom scipy import stats as sps\n\nMASTER_SEED = 20261021\nDEPTH = 25\nDEPTH_LOW = 10\nN_RAREFY = 1000\nN_BOOT = 1000\nN_BOOT_RAREFY = 200\n\n\ndef cell_seed(cell_id: str) -> int:\n    return int(hashlib.sha256(f\"{MASTER_SEED}|{cell_id}\".encode()).hexdigest()[:8], 16)\n\n\ndef hill1_counts(x: np.ndarray) -> float:\n    x = np.asarray(x, float)\n    x = x[x > 0]\n    if x.sum() <= 0:\n        return float(\"nan\")\n    q = x / x.sum()\n    return float(math.exp(-(q * np.log(q)).sum()))\n\n\ndef _hill1_rows(draws: np.ndarray, depth: int) -> np.ndarray:\n    q = draws / depth\n    with np.errstate(divide=\"ignore\", invalid=\"ignore\"):\n        h = np.where(q > 0, q * np.log(np.where(q > 0, q, 1.0)), 0.0).sum(axis=1)\n    return np.exp(-h)\n\n\ndef rarefied_hill1(counts: Sequence[int], depth: int, n_draws: int, rng: np.random.Generator) -> float:\n    c = np.asarray([int(v) for v in counts if int(v) > 0], np.int64)\n    if c.sum() < depth or len(c) == 0:\n        return float(\"nan\")\n    if len(c) == 1:\n        return 1.0\n    if c.sum() == depth:\n        return hill1_counts(c)\n    d = rng.multivariate_hypergeometric(c, depth, size=n_draws, method=\"marginals\")\n    return float(_hill1_rows(d, depth).mean())\n\n\ndef goods_coverage(counts: Sequence[int]) -> float:\n    c = np.asarray([v for v in counts if v > 0])\n    n = c.sum()\n    if n == 0:\n        return float(\"nan\")\n    f1 = int((c == 1).sum())\n    return float(1 - f1 / n)\n\n\ndef expected_coverage_at(counts: Sequence[int], m: int) -> float:\n    \"\"\"Expected sample coverage of a size-m subsample (interpolation, Chao & Jost 2012 eq. 4a).\"\"\"\n    c = np.asarray([v for v in counts if v > 0], float)\n    n = int(c.sum())\n    if m >= n:\n        return goods_coverage(c)\n    tot = 0.0\n    for xi in c:\n        if n - xi >= m:\n            # C(n - xi, m) / C(n - 1, m)\n            tot += (xi / n) * math.exp(math.lgamma(n - xi + 1) - math.lgamma(n - xi - m + 1)\n                                       - math.lgamma(n) + math.lgamma(n - m))\n    return float(1 - tot)\n\n\ndef coverage_standardised_hill1(counts: Sequence[int], target_cov: float, rng: np.random.Generator,\n                                n_draws: int = 400) -> tuple[float, int]:\n    \"\"\"Hill-1 rarefied to the size m whose expected coverage first reaches target_cov (interpolation only).\"\"\"\n    c = [int(v) for v in counts if v > 0]\n    n = sum(c)\n    if n == 0 or not np.isfinite(target_cov):\n        return float(\"nan\"), 0\n    m_star = n\n    for m in range(1, n + 1):\n        if expected_coverage_at(c, m) >= target_cov - 1e-12:\n            m_star = m\n            break\n    return rarefied_hill1(c, m_star, n_draws, rng), m_star\n\n\ndef h1r_cell(correct_labels: Sequence[str], templates: Sequence[str] | None, cell_id: str, depth: int = DEPTH,\n             drop: Iterable[str] = (), n_boot: int = N_BOOT, n_boot_rarefy: int = N_BOOT_RAREFY,\n             with_ci: bool = True) -> dict:\n    \"\"\"Correct-only rarefied Hill-1 for one cell; percentile CIs (template-cluster when eligible, and iid).\"\"\"\n    drop = set(drop)\n    keep = [i for i, l in enumerate(correct_labels) if l not in drop]\n    labs = [correct_labels[i] for i in keep]\n    tpls = [templates[i] for i in keep] if templates is not None else None\n    cats = sorted(set(labs))\n    idx = {c: i for i, c in enumerate(cats)}\n    counts = np.zeros(len(cats), np.int64)\n    for l in labs:\n        counts[idx[l]] += 1\n    n_c = int(counts.sum())\n    rng = np.random.default_rng(cell_seed(f\"{cell_id}|d{depth}|{'-'.join(sorted(drop))}\"))\n    out = {\"n_c\": n_c, \"S_obs\": int((counts > 0).sum()), \"coverage\": goods_coverage(counts),\n           \"value\": rarefied_hill1(counts, depth, N_RAREFY, rng), \"ci90\": [float(\"nan\")] * 2,\n           \"ci90_iid\": [float(\"nan\")] * 2, \"ci_unit\": None}\n    if not with_ci or n_c < depth or len(cats) <= 1:\n        if n_c >= depth and len(cats) == 1:\n            out[\"ci90\"] = [1.0, 1.0]\n            out[\"ci90_iid\"] = [1.0, 1.0]\n            out[\"ci_unit\"] = \"degenerate\"\n        return out\n    # iid program bootstrap\n    probs = counts / n_c\n    vals = np.full(n_boot, np.nan)\n    for b in range(n_boot):\n        cb = rng.multinomial(n_c, probs)\n        vals[b] = rarefied_hill1(cb, depth, n_boot_rarefy, rng)\n    out[\"ci90_iid\"] = [float(np.nanquantile(vals, 0.05)), float(np.nanquantile(vals, 0.95))]\n    out[\"ci90\"] = list(out[\"ci90_iid\"])\n    out[\"ci_unit\"] = \"program\"\n    if tpls is not None:\n        by_t: dict[str, np.ndarray] = {}\n        for l, t in zip(labs, tpls):\n            by_t.setdefault(str(t), np.zeros(len(cats), np.int64))[idx[l]] += 1\n        tkeys = sorted(by_t)\n        if len(tkeys) == 5 and all(by_t[t].sum() >= 5 for t in tkeys):\n            mat = np.stack([by_t[t] for t in tkeys])\n            tv = np.full(n_boot, np.nan)\n            for b in range(n_boot):\n                pick = rng.integers(0, len(tkeys), len(tkeys))\n                tv[b] = rarefied_hill1(mat[pick].sum(0), depth, n_boot_rarefy, rng)\n            if np.isfinite(tv).sum() > 0.5 * n_boot:\n                out[\"ci90\"] = [float(np.nanquantile(tv, 0.05)), float(np.nanquantile(tv, 0.95))]\n                out[\"ci_unit\"] = \"template(5 clusters; few-cluster)\"\n    return out\n\n\ndef wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:\n    if n <= 0:\n        return float(\"nan\"), float(\"nan\")\n    ph = k / n\n    den = 1 + z * z / n\n    c = (ph + z * z / (2 * n)) / den\n    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den\n    return max(0.0, c - h), min(1.0, c + h)\n\n\ndef newcombe_diff(k1: int, n1: int, k2: int, n2: int) -> tuple[float, float, float]:\n    \"\"\"p1 - p2 with the Newcombe (1998, method 10) hybrid-score 95% interval.\"\"\"\n    if n1 <= 0 or n2 <= 0:\n        return float(\"nan\"), float(\"nan\"), float(\"nan\")\n    p1, p2 = k1 / n1, k2 / n2\n    l1, u1 = wilson(k1, n1)\n    l2, u2 = wilson(k2, n2)\n    d = p1 - p2\n    return d, d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)\n\n\ndef poisson_binomial_sf(k: int, probs: Sequence[float]) -> float:\n    \"\"\"P(X >= k) for X = sum of independent Bernoulli(p_i), by dynamic programming.\"\"\"\n    dist = np.zeros(len(probs) + 1)\n    dist[0] = 1.0\n    for pi in probs:\n        dist[1:] = dist[1:] * (1 - pi) + dist[:-1] * pi\n        dist[0] *= (1 - pi)\n    return float(dist[k:].sum())\n\n\ndef binom_sf(k: int, n: int, p0: float) -> float:\n    return float(sps.binom.sf(k - 1, n, p0))\n\n\ndef _rank(a: np.ndarray) -> np.ndarray:\n    return sps.rankdata(a)\n\n\ndef spearman_perm(x: Sequence[float], y: Sequence[float], n_perm: int = 1_000_000, seed: int = MASTER_SEED) -> dict:\n    x = np.asarray(x, float)\n    y = np.asarray(y, float)\n    ok = np.isfinite(x) & np.isfinite(y)\n    x, y = x[ok], y[ok]\n    n = len(x)\n    if n < 3 or np.all(x == x[0]) or np.all(y == y[0]):\n        return {\"rho\": float(\"nan\"), \"p_perm\": float(\"nan\"), \"n\": n, \"method\": \"undefined\"}\n    rx, ry = _rank(x), _rank(y)\n    rx = (rx - rx.mean()) / np.sqrt(((rx - rx.mean()) ** 2).sum())\n    ry = (ry - ry.mean()) / np.sqrt(((ry - ry.mean()) ** 2).sum())\n    rho = float((rx * ry).sum())\n    if n <= 9:\n        perms = np.array(list(itertools.permutations(range(n))))\n        null = (rx[None, :] * ry[perms]).sum(1)\n        method = f\"exact enumeration ({len(perms)} permutations)\"\n    else:\n        rng = np.random.default_rng(seed)\n        null = np.empty(n_perm)\n        chunk = 100_000\n        for s in range(0, n_perm, chunk):\n            m = min(chunk, n_perm - s)\n            idx = np.argsort(rng.random((m, n)), axis=1)\n            null[s:s + m] = (rx[None, :] * ry[idx]).sum(1)\n        method = f\"Monte Carlo permutation ({n_perm} draws)\"\n    p = float((np.abs(null) >= abs(rho) - 1e-12).mean())\n    tau = sps.kendalltau(x, y)\n    return {\"rho\": rho, \"p_perm\": p, \"n\": n, \"method\": method, \"kendall_tau_b\": float(tau.statistic),\n            \"kendall_p\": float(tau.pvalue)}\n\n\ndef holm(pvals: Sequence[float]) -> list[float]:\n    p = np.asarray(pvals, float)\n    out = np.full(len(p), np.nan)\n    ok = np.where(np.isfinite(p))[0]\n    order = ok[np.argsort(p[ok])]\n    m = len(order)\n    run = 0.0\n    for i, j in enumerate(order):\n        run = max(run, min(1.0, (m - i) * p[j]))\n        out[j] = run\n    return out.tolist()\n\n\ndef jackknife_ci(theta: float, jack_vals: Sequence[float], level: float = 0.95) -> list[float]:\n    j = np.asarray(jack_vals, float)\n    n = len(j)\n    if n < 3:\n        return [float(\"nan\"), float(\"nan\")]\n    se = math.sqrt((n - 1) / n * ((j - j.mean()) ** 2).sum())\n    tq = sps.t.ppf(0.5 + level / 2, n - 1)\n    return [theta - tq * se, theta + tq * se]\n\n\ndef cohen_kappa(a: Sequence[str], b: Sequence[str]) -> float:\n    a, b = list(a), list(b)\n    n = len(a)\n    if n == 0:\n        return float(\"nan\")\n    po = sum(x == y for x, y in zip(a, b)) / n\n    ca, cb = Counter(a), Counter(b)\n    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)\n    return float((po - pe) / (1 - pe)) if pe < 1 else float(\"nan\")\n\n\ndef kappa_boot_ci(a: Sequence[str], b: Sequence[str], n_boot: int = 2000, seed: int = MASTER_SEED) -> list[float]:\n    a, b = list(a), list(b)\n    n = len(a)\n    if n < 3:\n        return [float(\"nan\"), float(\"nan\")]\n    rng = np.random.default_rng(seed)\n    vals = []\n    for _ in range(n_boot):\n        ix = rng.integers(0, n, n)\n        vals.append(cohen_kappa([a[i] for i in ix], [b[i] for i in ix]))\n    v = np.asarray(vals, float)\n    v = v[np.isfinite(v)]\n    return [float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))] if len(v) else [float(\"nan\")] * 2\n\n\ndef balanced_accuracy(pred: Sequence[int], truth: Sequence[int]) -> float:\n    pred, truth = np.asarray(pred), np.asarray(truth)\n    pos, neg = truth == 1, truth == 0\n    if pos.sum() == 0 or neg.sum() == 0:\n        return float(\"nan\")\n    return float(0.5 * ((pred[pos] == 1).mean() + (pred[neg] == 0).mean()))\n\n\ndef fisher_2x2(pred: Sequence[int], truth: Sequence[int], alternative: str = \"two-sided\") -> dict:\n    pred, truth = np.asarray(pred), np.asarray(truth)\n    tab = [[int(((pred == 1) & (truth == 1)).sum()), int(((pred == 1) & (truth == 0)).sum())],\n           [int(((pred == 0) & (truth == 1)).sum()), int(((pred == 0) & (truth == 0)).sum())]]\n    res = sps.fisher_exact(tab, alternative=alternative)\n    return {\"table\": tab, \"p\": float(res.pvalue), \"alternative\": alternative}\n\n\ndef js_div2(p: np.ndarray, q: np.ndarray) -> float:\n    \"\"\"Base-2 Jensen-Shannon divergence (exp16 convention).\"\"\"\n    p = np.asarray(p, float) / np.sum(p)\n    q = np.asarray(q, float) / np.sum(q)\n    m = 0.5 * (p + q)\n\n    def kl(a, b):\n        mask = a > 0\n        return float((a[mask] * np.log2(a[mask] / b[mask])).sum())\n\n    return 0.5 * kl(p, m) + 0.5 * kl(q, m)\n\n\ndef upper_bound_zero_of_k(k: int, level: float = 0.90) -> float:\n    \"\"\"One-sided upper bound on a per-direction escape probability when 0 of k escape.\"\"\"\n    return float(1 - (1 - level) ** (1 / k)) if k > 0 else float(\"nan\")", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [25] THINKING · 2026-10-26 10:52:31 UTC

```
I'll look at `src/knob.py` and `src/screen.py` to understand how the knob table's 1,120 cells are computed and seeded, and whether the screen can be driven from knob rows.
```

### [26] TOOL CALL — Bash · 2026-10-26 10:52:31 UTC

```
Read knob table module:
A=/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3; cat -n $A/src/knob.py
```

### [27] TOOL RESULT — Bash · 2026-10-26 10:52:31 UTC

```
{"stdout": "     1\t\"\"\"(0a) One-statistic knob table: one row per artifact x task x arm x dial cell, priced against its own twin.\"\"\"\n     2\t\n     3\tfrom __future__ import annotations\n     4\t\n     5\timport json\n     6\timport multiprocessing as mp\n     7\timport re\n     8\tfrom collections import Counter\n     9\tfrom concurrent.futures import ProcessPoolExecutor\n    10\tfrom typing import Any\n    11\t\n    12\timport numpy as np\n    13\timport pandas as pd\n    14\tfrom loguru import logger\n    15\t\n    16\tfrom src.paths import ARTIFACTS, exp_name\n    17\tfrom src.stats import DEPTH, DEPTH_LOW, h1r_cell, newcombe_diff\n    18\t\n    19\tNONCAT_DROP_MARK = \"__noncat__\"\n    20\t\n    21\t\n    22\t# ------------------------------------------------------------------------------------------------ arm dictionary\n    23\tdef classify(exp: str, arm: str, dial: dict) -> tuple[str, str, str]:\n    24\t    \"\"\"-> (class, family, one-line description).\"\"\"\n    25\t    a = arm\n    26\t    if exp == \"exp13\":\n    27\t        m = {\"twin\": (\"control\", \"twin\", \"neutral twin (vLLM)\"), \"hf_twin\": (\"control\", \"twin\", \"neutral twin (HF engine)\"),\n    28\t             \"sham\": (\"control\", \"sham_veto\", \"sham token veto\"), \"ban\": (\"knob\", \"prompt:ban\", \"modal 'do not use X' ban\"),\n    29\t             \"nonce\": (\"knob\", \"prompt:nonce\", \"nonce ban\"), \"novelty\": (\"knob\", \"prompt:novelty\", \"novelty instruction\"),\n    30\t             \"oneshot\": (\"knob\", \"veto\", \"one-shot token veto\"), \"persistent\": (\"knob\", \"veto\", \"persistent token veto\"),\n    31\t             \"iter1\": (\"knob\", \"veto\", \"iterated veto round 1\"), \"iter2\": (\"knob\", \"veto\", \"iterated veto round 2\"),\n    32\t             \"iter3\": (\"knob\", \"veto\", \"iterated veto round 3\"),\n    33\t             \"bandpatch\": (\"knob\", \"activation-ban-derived\", \"ban task-spec states patched into the twin (ban-derived)\")}\n    34\t        if a in m:\n    35\t            return m[a]\n    36\t        if a.startswith(\"rand\"):\n    37\t            return (\"knob\", \"activation-random\", \"matched-norm isotropic random direction at task-spec states, layers 12-23\")\n    38\t    if exp == \"exp17\":\n    39\t        if a == \"NEUTRAL\":\n    40\t            return (\"control\", \"twin\", \"neutral twin (HF, FP8 linears)\")\n    41\t        if a.startswith(\"BAN\"):\n    42\t            return (\"knob\", \"prompt:ban\", \"modal ban\" + (\" (top-up samples)\" if \"TOPUP\" in a else \"\"))\n    43\t        if a.startswith(\"ADD\"):\n    44\t            return (\"knob\", \"activation-structured\", \"leave-one-task-out prohibition direction added to the twin\")\n    45\t        if a.startswith(\"RAND\"):\n    46\t            return (\"knob\", \"activation-random\", \"norm-matched random direction added to the twin\")\n    47\t        if a.startswith(\"SUB\") or a.startswith(\"HEADS\"):\n    48\t            return (\"ablation\", \"ablation-on-ban\", \"intervention on the ban (projection / head ablation); not a knob\")\n    49\t        if a.startswith(\"U7\"):\n    50\t            return (\"control\", \"engine_check\", \"U7 engine reproduction check\")\n    51\t    if exp == \"exp15\":\n    52\t        if a in (\"neutral_baseline\", \"vetofree\"):\n    53\t            return (\"control\", \"twin\", \"Llama neutral twin\" + (\" (veto chain pass-1)\" if a == \"vetofree\" else \"\"))\n    54\t        if a == \"pilot_fp8\":\n    55\t            return (\"control\", \"pilot\", \"Llama FP8 pilot (no ban)\")\n    56\t        if a in (\"nonce\", \"novelty\"):\n    57\t            return (\"knob\", f\"prompt:{a}\", f\"{a} prompt (Llama)\")\n    58\t        if a.startswith(\"rand_\"):\n    59\t            return (\"knob\", \"activation-random\", \"matched-norm random direction at spec positions, layers 11-21 (Llama)\")\n    60\t        if a.startswith(\"ban_\"):\n    61\t            return (\"knob\", \"prompt:ban\", f\"{a.split(':')[0][4:]} ban of {a.split(':')[1]} (Llama)\")\n    62\t        if a.startswith(\"veto_\"):\n    63\t            return (\"knob\", \"veto\", f\"{a[5:]} signature-n-gram veto (Llama)\")\n    64\t    if exp == \"exp16\":\n    65\t        return (\"control\", \"route_diagnostic\", {\"a\": \"full ban\", \"b\": \"token-matched neutral twin\",\n    66\t                                                \"c\": \"prompt route (twin condition + ban spec states)\",\n    67\t                                                \"d\": \"direct route (ban condition + twin spec states)\",\n    68\t                                                \"K0\": \"condition span invisible to generated tokens\",\n    69\t                                                \"V1\": \"one-shot veto of the default's n-gram\"}.get(a, \"route/prefill diagnostic arm\"))\n    70\t    if exp == \"exp14\":\n    71\t        kind = a.split(\":\")[0]\n    72\t        if kind == \"copy\":\n    73\t            return (\"control\", \"copy\", \"COPY: shown programs of Y, no ban\")\n    74\t        if kind == \"baseline\":\n    75\t            return (\"control\", \"twin\", \"no-exposure baseline\")\n    76\t        if kind in (\"named\", \"unnamed\"):\n    77\t            return (\"knob\", \"prompt:exposure_ban\", f\"{kind.upper()} exposure ban of the shown algorithm\")\n    78\t        if kind == \"veto\":\n    79\t            return (\"knob\", \"veto\", \"in-context signature veto of the shown algorithm\")\n    80\t        if kind.startswith(\"W\"):\n    81\t            return (\"knob\", \"prompt:exposure_ban\", f\"exposure ban, template arm {kind}\")\n    82\t    if exp == \"exp18\":\n    83\t        if a == \"walk_twin\":\n    84\t            return (\"control\", \"twin\", \"neutral twin (walk step 0)\")\n    85\t        if a.startswith(\"walk_step\"):\n    86\t            return (\"knob\", \"veto\", \"persistent token-walk veto\")\n    87\t        if a == \"sham\":\n    88\t            return (\"control\", \"sham_veto\", \"matched sham veto\")\n    89\t        if a == \"fixed_top5\":\n    90\t            return (\"knob\", \"veto\", \"fixed TOP5 veto\")\n    91\t        if a.startswith(\"los:\"):\n    92\t            return (\"knob\", \"prompt:list\", \"leave-one-survivor list ban\")\n    93\t        if a.startswith(\"two_step:\"):\n    94\t            return (\"knob\", \"prompt:ban\", \"two-step ban\")\n    95\t        if a.startswith(\"longform:\"):\n    96\t            return (\"knob\", \"prompt:instruction\", \"2,000-word 'make a (fully) novel algorithm' instruction\")\n    97\t    if exp == \"exp9\":\n    98\t        if a == \"baseline\":\n    99\t            return (\"control\", \"twin\", \"no-ban baseline\")\n   100\t        if a.startswith(\"single:\"):\n   101\t            return (\"knob\", \"prompt:ban\", \"single-name ban\")\n   102\t        if a.startswith(\"los:\"):\n   103\t            return (\"knob\", \"prompt:list\", \"leave-one-survivor list\")\n   104\t        if a.startswith(\"multi:\"):\n   105\t            return (\"knob\", \"prompt:list\", \"multi-name ban list\")\n   106\t    if exp == \"exp4\":\n   107\t        if a == \"baseline\":\n   108\t            return (\"control\", \"twin\", \"vLLM baseline\")\n   109\t        if a == \"steer:dc\":\n   110\t            if dial.get(\"c\", 0) == 0:\n   111\t                return (\"control\", \"twin\", \"HF c=0 hook\")\n   112\t            return (\"knob\", \"activation-structured\", \"decommitment direction d_dc\")\n   113\t        if a in (\"steer:rand1\", \"steer:rand2\"):\n   114\t            return (\"knob\", \"activation-random\", \"random direction (iteration 1)\")\n   115\t        if a == \"steer:placebo\":\n   116\t            return (\"knob\", \"activation-structured\", \"variable-name placebo direction\")\n   117\t        if a == \"steer:breadth\":\n   118\t            return (\"knob\", \"activation-structured\", \"breadth direction\")\n   119\t        if a == \"steer:dcxfer\":\n   120\t            return (\"knob\", \"activation-structured\", \"cross-task transferred d_dc\")\n   121\t        if a.startswith(\"enumerate\"):\n   122\t            return (\"knob\", \"prompt:instruction\", \"enumeration prompt\")\n   123\t        if a.startswith(\"ban:\"):\n   124\t            return (\"knob\", \"prompt:ban\", \"modal ban\")\n   125\t        if a.startswith(\"mention:\"):\n   126\t            return (\"control\", \"mention_twin\", \"mention twin\")\n   127\t        if a.startswith(\"succession\"):\n   128\t            return (\"knob\", \"prompt:ban\", \"succession ban\")\n   129\t    if exp == \"exp6\":\n   130\t        kind, cond = a.split(\":\", 1)\n   131\t        if kind == \"A0\":\n   132\t            return (\"control\", \"twin\", \"no-cue baseline T=1.0, pure sampling, thinking off\")\n   133\t        if kind in (\"A1\", \"A6a\", \"A6b\", \"A6c\", \"A6d\"):\n   134\t            return (\"knob\", \"decoding\", \"temperature x sampler grid\" + (\" (thinking on)\" if dial.get(\"thinking\") else \"\"))\n   135\t        if kind == \"A2\":\n   136\t            return (\"knob\", \"prompt:seed\", f\"{cond.replace('seed_', '')} seed\")\n   137\t        if kind == \"A3\":\n   138\t            return (\"knob\", \"prompt:instruction\", f\"creativity instruction {cond}\")\n   139\t        if kind.startswith(\"A4\"):\n   140\t            return (\"ceiling\", \"generate_then_select\", \"generate-then-select (ceiling, never ranked)\")\n   141\t    if exp == \"exp11\":\n   142\t        return (\"control\", \"pilot\", \"FP8 pilot (no ban)\")\n   143\t    return (\"unclassified\", \"unclassified\", a)\n   144\t\n   145\t\n   146\tdef ref_of(exp: str, arm: str, dial: dict, task: str, precision: str, cells: set) -> tuple[tuple | None, list[str]]:\n   147\t    \"\"\"Own-twin reference cell key (exp, task, arm, dial_json, precision) and flags.\"\"\"\n   148\t    flags: list[str] = []\n   149\t    dj = json.dumps({}, sort_keys=True)\n   150\t    cand = None\n   151\t    if exp == \"exp13\":\n   152\t        hf = arm.startswith(\"rand\") or arm in (\"bandpatch\", \"hf_twin\")\n   153\t        cand = (task, \"hf_twin\" if hf else \"twin\", dj)\n   154\t    elif exp == \"exp17\":\n   155\t        cand = (task, \"NEUTRAL\", dj)\n   156\t    elif exp == \"exp15\":\n   157\t        cand = (task, \"vetofree\" if arm.startswith(\"veto_\") else \"neutral_baseline\", dj)\n   158\t    elif exp == \"exp16\":\n   159\t        cand = (task, \"b\", dj)\n   160\t    elif exp == \"exp14\":\n   161\t        kind = arm.split(\":\")[0]\n   162\t        y = arm.split(\":\", 1)[1] if \":\" in arm else None\n   163\t        cand = (task, \"baseline\", dj) if kind == \"copy\" else (task, f\"copy:{y}\", dj)\n   164\t    elif exp == \"exp18\":\n   165\t        cand = (task, \"walk_twin\", dj)\n   166\t    elif exp == \"exp9\":\n   167\t        cand = (task, \"baseline\", dj)\n   168\t    elif exp == \"exp4\":\n   169\t        if arm in (\"baseline\",) or arm.startswith((\"ban:\", \"mention:\", \"enumerate\", \"succession\")):\n   170\t            cand = (task, \"baseline\", dj)\n   171\t        else:\n   172\t            cand = (task, \"steer:dc\", json.dumps({\"c\": 0.0, \"layer\": 18}, sort_keys=True))\n   173\t    elif exp == \"exp6\":\n   174\t        cand = (task, \"A0:baseline\", json.dumps({\"T\": 1.0, \"sampler\": \"pure\", \"thinking\": False}, sort_keys=True))\n   175\t        if dial.get(\"thinking\"):\n   176\t            flags.append(\"ref_thinking_off\")\n   177\t    if cand is None:\n   178\t        return None, flags\n   179\t    key = (exp,) + cand + (precision,)\n   180\t    if key in cells:\n   181\t        return key, flags\n   182\t    others = [c for c in cells if c[:4] == key[:4]]\n   183\t    if others:\n   184\t        flags.append(\"cross_precision_ref\")\n   185\t        return others[0], flags\n   186\t    return None, flags + [\"no_own_twin\"]\n   187\t\n   188\t\n   189\t# ------------------------------------------------------------------------------------------------ cells\n   190\tdef _cell_job(args: tuple) -> dict:\n   191\t    cid, labels, templates, noncat = args\n   192\t    prim = h1r_cell(labels, templates, cid, DEPTH)\n   193\t    cat = h1r_cell(labels, templates, cid + \"|cat\", DEPTH, drop=noncat, with_ci=False)\n   194\t    low = h1r_cell(labels, templates, cid, DEPTH_LOW, with_ci=False) if prim[\"n_c\"] < DEPTH else None\n   195\t    return {\"cid\": cid, \"prim\": prim, \"cat\": cat, \"low\": low}\n   196\t\n   197\t\n   198\tdef build_knob_table(rows: pd.DataFrame, n_workers: int = 5) -> pd.DataFrame:\n   199\t    rows = rows.copy()\n   200\t    rows[\"exp\"] = rows.artifact_id.map(exp_name)\n   201\t    keys = [\"exp\", \"artifact_id\", \"task\", \"arm\", \"dial\", \"precision\"]\n   202\t    groups = list(rows.groupby(keys, sort=True))\n   203\t    cellset = {(k[0], k[2], k[3], k[4], k[5]) for k, _ in groups}\n   204\t    base = []\n   205\t    jobs = []\n   206\t    for (exp, aid, task, arm, dial, prec), g in groups:\n   207\t        cid = f\"{aid}|{task}|{arm}|{dial}|{prec}\"\n   208\t        att = g[g.attempted]\n   209\t        cor = g[g.passed]\n   210\t        noncat = sorted(set(cor.label_norm[~cor.is_catalogue]))\n   211\t        jobs.append((cid, cor.label_norm.tolist(), cor.template.tolist(), noncat))\n   212\t        base.append({\"cid\": cid, \"exp\": exp, \"artifact_id\": aid, \"src_file\": g.src_file.iloc[0], \"model\": g.model.iloc[0],\n   213\t                     \"engine\": \",\".join(sorted(set(g.engine))), \"precision\": prec, \"task\": task, \"arm\": arm,\n   214\t                     \"dial\": dial, \"n\": int(len(g)), \"n_attempted\": int(len(att)), \"n_correct\": int(len(cor)),\n   215\t                     \"n_default_att\": int(att.is_default.sum()),\n   216\t                     \"n_cat_nondefault_att\": int((att.is_catalogue & ~att.is_default).sum()),\n   217\t                     \"correct_composition\": json.dumps(dict(Counter(cor.label_norm).most_common())),\n   218\t                     \"attempted_composition\": json.dumps(dict(Counter(att.label_norm).most_common())),\n   219\t                     \"offdef_attempted_cat_composition\": json.dumps(dict(Counter(\n   220\t                         att.label_norm[att.is_catalogue & ~att.is_default]).most_common())),\n   221\t                     \"other_share\": float((att.label_norm == \"other\").mean()) if len(att) else float(\"nan\")})\n   222\t    logger.info(f\"knob table: {len(base)} cells; computing rarefied Hill-1 with {n_workers} workers\")\n   223\t    with ProcessPoolExecutor(max_workers=n_workers, mp_context=mp.get_context(\"spawn\")) as ex:\n   224\t        res = {r[\"cid\"]: r for r in ex.map(_cell_job, jobs, chunksize=8)}\n   225\t    out = []\n   226\t    for b in base:\n   227\t        r = res[b[\"cid\"]]\n   228\t        prim, cat, low = r[\"prim\"], r[\"cat\"], r[\"low\"]\n   229\t        dial = json.loads(b[\"dial\"])\n   230\t        cls, fam, desc = classify(b[\"exp\"], b[\"arm\"], dial)\n   231\t        b.update({\"class\": cls, \"family\": fam, \"description\": desc,\n   232\t                  \"pass_rate\": b[\"n_correct\"] / b[\"n\"] if b[\"n\"] else float(\"nan\"),\n   233\t                  \"offdef_share\": 1 - b[\"n_default_att\"] / b[\"n_attempted\"] if b[\"n_attempted\"] else float(\"nan\"),\n   234\t                  \"cat_only_avoidance\": b[\"n_cat_nondefault_att\"] / b[\"n_attempted\"] if b[\"n_attempted\"] else float(\"nan\"),\n   235\t                  \"H1r25\": prim[\"value\"], \"H1r25_ci90\": json.dumps([round(x, 4) for x in prim[\"ci90\"]]),\n   236\t                  \"H1r25_ci90_iid\": json.dumps([round(x, 4) for x in prim[\"ci90_iid\"]]), \"ci_unit\": prim[\"ci_unit\"],\n   237\t                  \"H1r25_cat\": cat[\"value\"], \"H1r10\": (low or {}).get(\"value\", float(\"nan\")),\n   238\t                  \"S_obs\": prim[\"S_obs\"], \"coverage\": prim[\"coverage\"]})\n   239\t        ref, flags = ref_of(b[\"exp\"], b[\"arm\"], dial, b[\"task\"], b[\"precision\"], cellset)\n   240\t        b[\"ref_key\"] = json.dumps(ref) if ref else \"\"\n   241\t        b[\"flags_list\"] = flags + ([\"below_depth\"] if prim[\"n_c\"] < DEPTH else [])\n   242\t        out.append(b)\n   243\t    df = pd.DataFrame(out)\n   244\t    idx = {(r.exp, r.task, r.arm, r.dial, r.precision): i for i, r in df.iterrows()}\n   245\t    ref_pass, ref_arm, cost, cost_ci, ref_off, esc, qual = [], [], [], [], [], [], []\n   246\t    for _, r in df.iterrows():\n   247\t        if not r.ref_key:\n   248\t            ref_pass.append(np.nan); ref_arm.append(\"\"); cost.append(np.nan); cost_ci.append(\"[]\"); ref_off.append(np.nan)\n   249\t            esc.append(None); qual.append(None)\n   250\t            continue\n   251\t        rk = tuple(json.loads(r.ref_key))\n   252\t        rr = df.loc[idx[rk]]\n   253\t        ref_arm.append(f\"{rr.arm}{'' if rr.dial == '{}' else ' ' + rr.dial}\")\n   254\t        ref_pass.append(rr.pass_rate)\n   255\t        d, lo, hi = newcombe_diff(int(rr.n_correct), int(rr.n), int(r.n_correct), int(r.n))\n   256\t        cost.append(100 * d)\n   257\t        cost_ci.append(json.dumps([round(100 * lo, 2), round(100 * hi, 2)]))\n   258\t        ref_off.append(rr.offdef_share)\n   259\t        if r[\"class\"] == \"control\":\n   260\t            esc.append(None); qual.append(None)\n   261\t        else:\n   262\t            esc.append(bool((r.offdef_share - rr.offdef_share) >= 0.20 and r.pass_rate >= 0.8 * rr.pass_rate))\n   263\t            qual.append(bool(np.isfinite(r.H1r25) and r.H1r25 >= 2 and 100 * d <= 20))\n   264\t    df[\"ref_arm\"], df[\"ref_pass\"], df[\"pass_cost_pts\"], df[\"pass_cost_ci95\"] = ref_arm, ref_pass, cost, cost_ci\n   265\t    df[\"ref_offdef_share\"], df[\"escape\"], df[\"qualify\"] = ref_off, esc, qual\n   266\t    df[\"flags\"] = df.flags_list.map(lambda x: \";\".join(x))\n   267\t    df[\"sources\"] = df.artifact_id + \":\" + df.src_file\n   268\t    df[\"row_id\"] = [f\"K{i:04d}\" for i in range(len(df))]\n   269\t    return df\n   270\t\n   271\t\n   272\tKNOB_COLUMNS = [\"row_id\", \"artifact_id\", \"src_file\", \"model\", \"engine\", \"precision\", \"task\", \"arm\", \"class\", \"family\",\n   273\t                \"dial\", \"n\", \"n_attempted\", \"n_correct\", \"pass_rate\", \"ref_arm\", \"ref_pass\", \"pass_cost_pts\",\n   274\t                \"pass_cost_ci95\", \"offdef_share\", \"ref_offdef_share\", \"cat_only_avoidance\", \"other_share\", \"H1r25\",\n   275\t                \"H1r25_ci90\", \"H1r25_ci90_iid\", \"ci_unit\", \"H1r25_cat\", \"H1r10\", \"S_obs\", \"coverage\",\n   276\t                \"correct_composition\", \"attempted_composition\", \"offdef_attempted_cat_composition\", \"escape\",\n   277\t                \"qualify\", \"flags\", \"sources\", \"description\", \"realised_l21_displacement_ratio\"]\n   278\t\n   279\t\n   280\tdef arm_dictionary(knob: pd.DataFrame) -> pd.DataFrame:\n   281\t    d = knob.groupby([\"artifact_id\", \"arm\"]).agg(cls=(\"class\", \"first\"), family=(\"family\", \"first\"),\n   282\t                                                  description=(\"description\", \"first\"), ref_arm=(\"ref_arm\", \"first\"),\n   283\t                                                  engine=(\"engine\", \"first\"), precision=(\"precision\", \"first\"),\n   284\t                                                  n_cells=(\"row_id\", \"count\")).reset_index()\n   285\t    return d.rename(columns={\"cls\": \"class\"})\n   286\t\n   287\t\n   288\tdef direction_id(exp: str, arm: str) -> str:\n   289\t    return f\"{exp}:{arm}\"\n   290\t\n   291\t\n   292\tdef is_random_direction(r: pd.Series) -> bool:\n   293\t    return r[\"family\"] == \"activation-random\" and r[\"model\"].startswith(\"Qwen\") and r[\"exp\"] in (\"exp13\", \"exp17\")\n   294\t\n   295\t\n   296\tdef alpha_of(r: pd.Series) -> float:\n   297\t    if r[\"exp\"] == \"exp17\":\n   298\t        m = re.search(r\"_a(\\d+(?:\\.\\d+)?)$\", r[\"arm\"])\n   299\t        return float(m.group(1)) if m else float(\"nan\")\n   300\t    return 1.0  # exp13 matched-norm random directions (norm of the ban displacement) are the alpha-1 analogue", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [28] TOOL CALL — Bash · 2026-10-26 10:52:31 UTC

```
Read screen module:
A=/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3; cat -n $A/src/screen.py | head -400
```

### [29] TOOL RESULT — Bash · 2026-10-26 10:52:31 UTC

```
{"stdout": "     1\t\"\"\"(0a) direction counts, Table 110, verification targets, per-task verdicts; (0i) frozen screen file.\"\"\"\n     2\t\n     3\tfrom __future__ import annotations\n     4\t\n     5\timport hashlib\n     6\timport importlib.util\n     7\timport json\n     8\timport math\n     9\tfrom collections import Counter\n    10\t\n    11\timport numpy as np\n    12\timport pandas as pd\n    13\tfrom loguru import logger\n    14\tfrom scipy import stats as sps\n    ... [truncated, 29533 chars total]
```

### [30] THINKING · 2026-10-26 10:53:37 UTC

```
I'll check the raw row schema, label catalogue module, and stage timings to determine what the mini dataset needs to carry through the pipeline (rows → knob table → screen rule).
```

### [31] TOOL CALL — Bash · 2026-10-26 10:53:37 UTC

```
Read labels module and stage timings:
A=/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3; cat -n $A/src/labels.py; echo "=== LOG timings"; grep -E "=== stage .* done|knob table:|screen.json sha256|verification targets" $A/logs/eval.log | tail -40
```

### [32] TOOL RESULT — Bash · 2026-10-26 10:53:37 UTC

```
{"stdout": "     1\t\"\"\"STEP G1: label normalisation. Frozen labels are used as recorded; only spellings are aliased.\n     2\t\n     3\tCatalogues: bench tasks from exp11 bench/<task>/spec.json; T1 = exp9's 7-mode analysis catalogue (plus\n     4\titeration-1's dijkstra_unit, kept verbatim and flagged); T2 = dijkstra, bf_spfa, bidijkstra, floyd, dial.\n     5\t\"\"\"\n     6\t\n     7\tfrom __future__ import annotations\n     8\t\n     9\timport json\n    10\tfrom functools import lru_cache\n    11\t\n    12\tfrom src.paths import p\n    13\t\n    14\tBENCH_DIRS = {\n    15\t    \"T03\": \"T03_kth_smallest\", \"T04\": \"T04_substring_search\", \"T05\": \"T05_two_sum\", \"T06\": \"T06_find_duplicate\",\n    16\t    \"T08\": \"T08_fibonacci\", \"T10\": \"T10_connected_components\", \"T11\": \"T11_longest_increasing_subsequence\",\n    17\t    \"T13\": \"T13_merge_intervals\", \"T14\": \"T14_top_k_frequent\", \"R1\": \"R1_non_overlapping_intervals\",\n    18\t    \"R2\": \"R2_cycle_detection\", \"R3\": \"R3_topological_order\", \"R6\": \"R6_first_last_position\",\n    19\t}\n    20\tBENCH12 = [\"T03\", \"T04\", \"T05\", \"T06\", \"T08\", \"T10\", \"T11\", \"T13\", \"T14\", \"R1\", \"R3\", \"R6\"]\n    21\tPATH_TASKS = [\"T1\", \"T2\"]\n    22\tQWEN14 = BENCH12 + PATH_TASKS\n    23\t\n    24\tT1_CATALOGUE = [\"bfs\", \"dfs\", \"bibfs\", \"iddfs\", \"astar\", \"gbfs\", \"idastar\", \"dijkstra_unit\"]\n    25\tT2_CATALOGUE = [\"dijkstra\", \"bf_spfa\", \"bidijkstra\", \"floyd\", \"dial\"]\n    26\t\n    27\t# iteration-1/2 spellings -> canonical\n    28\tALIASES = {\n    29\t    \"bellman_ford_spfa\": \"bf_spfa\", \"bidirectional_bfs\": \"bibfs\", \"floyd_warshall\": \"floyd\",\n    30\t    \"bidirectional_dijkstra\": \"bidijkstra\", \"astar_greedy\": \"astar\", \"astar_gbfs\": \"astar\",\n    31\t}\n    32\t# labels that are not an attempted program (no code / unparseable / unresolved)\n    33\tNOT_ATTEMPTED = {\"invalid\", \"no_code\", \"unparseable\", \"disputed\", \"unresolved\", \"extraction_failed\", \"\", \"none\", \"None\"}\n    34\tNON_CATALOGUE_KEEP = {\"other\", \"builtin\", \"unknown\", \"invalid\", \"no_code\", \"unparseable\", \"disputed\", \"unresolved\"}\n    35\t\n    36\tQWEN_DEFAULT = {\n    37\t    \"T03\": \"full_sort\", \"T04\": \"naive\", \"T05\": \"hash_map\", \"T06\": \"hash_set\", \"T08\": \"iteration\", \"T10\": \"union_find\",\n    38\t    \"T11\": \"quadratic_dp\", \"T13\": \"sort_sweep\", \"T14\": \"sort_by_count\", \"R1\": \"greedy_end\", \"R3\": \"kahn\",\n    39\t    \"R6\": \"binary_search\", \"T1\": \"bfs\", \"T2\": \"dijkstra\",\n    40\t}\n    41\t\n    42\t\n    43\t@lru_cache(maxsize=None)\n    44\tdef spec(task: str) -> dict:\n    45\t    return json.loads(p(\"exp11\", f\"bench/{BENCH_DIRS[task]}/spec.json\").read_text())\n    46\t\n    47\t\n    48\t@lru_cache(maxsize=None)\n    49\tdef catalogue(task: str) -> tuple[str, ...]:\n    50\t    if task == \"T1\":\n    51\t        return tuple(T1_CATALOGUE)\n    52\t    if task == \"T2\":\n    53\t        return tuple(T2_CATALOGUE)\n    54\t    return tuple(c[\"mode\"] for c in spec(task)[\"catalogue\"])\n    55\t\n    56\t\n    57\tdef catalogue_descriptions(task: str) -> dict[str, str]:\n    58\t    if task in PATH_TASKS:\n    59\t        return {m: m for m in catalogue(task)}\n    60\t    return {c[\"mode\"]: f\"{c['display_name']}: {c['mechanism']}\" for c in spec(task)[\"catalogue\"]}\n    61\t\n    62\t\n    63\tdef norm_task(t: str) -> str:\n    64\t    t = str(t)\n    65\t    return {\"t1\": \"T1\", \"t2\": \"T2\"}.get(t, t)\n    66\t\n    67\t\n    68\tdef norm_label(lab: object) -> str:\n    69\t    s = \"no_code\" if lab is None else str(lab).strip()\n    70\t    return ALIASES.get(s, s)\n    71\t\n    72\t\n    73\tdef is_catalogue(task: str, lab: str) -> bool:\n    74\t    try:\n    75\t        return lab in catalogue(task)\n    76\t    except KeyError:\n    77\t        return False\n    78\t\n    79\t\n    80\tdef attempted(lab: str) -> bool:\n    81\t    return lab not in NOT_ATTEMPTED\n    82\t\n    83\t\n    84\t@lru_cache(maxsize=None)\n    85\tdef llama_defaults() -> dict[str, str]:\n    86\t    out = {}\n    87\t    for line in p(\"exp15\", \"results/c1_events.jsonl\").read_text().splitlines():\n    88\t        if line.strip():\n    89\t            ev = json.loads(line)\n    90\t            if ev[\"event_type\"] == \"modal\":\n    91\t                out[ev[\"task\"]] = ev[\"banned\"]\n    92\t    return out\n    93\t\n    94\t\n    95\tdef default_of(task: str, model: str = \"qwen\") -> str | None:\n    96\t    if \"llama\" in model.lower():\n    97\t        return llama_defaults().get(task)\n    98\t    return QWEN_DEFAULT.get(task)\n=== LOG timings\n2026-10-21 04:11:08.016 | INFO     | __main__:main:54 - === stage knob done in 22.0s ===\n2026-10-21 04:11:08.396 | INFO     | src.screen:run_screen_stage:366 - verification targets: 25/27 matched\n2026-10-21 04:11:08.731 | INFO     | src.screen:run_screen_stage:389 - screen.json sha256 d6a2ca9711f461973c39482314a523d448d0590cb40e32432826dec1da4846e8; movable ['T03', 'T05', 'T06', 'T1', 'T10', 'T2']\n2026-10-21 04:11:08.757 | INFO     | __main__:main:54 - === stage screen done in 0.7s ===\n2026-10-21 04:11:13.372 | INFO     | __main__:main:54 - === stage route done in 4.6s ===\n2026-10-21 04:11:13.445 | INFO     | __main__:main:54 - === stage llama done in 0.1s ===\n2026-10-21 04:11:14.558 | INFO     | __main__:main:54 - === stage other done in 1.1s ===\n2026-10-21 04:11:38.291 | INFO     | __main__:main:54 - === stage figures done in 23.7s ===\n2026-10-21 04:11:38.643 | INFO     | __main__:main:54 - === stage rigor done in 0.3s ===\n2026-10-21 04:11:38.715 | INFO     | __main__:main:54 - === stage wording done in 0.1s ===\n2026-10-21 04:11:40.740 | INFO     | __main__:main:54 - === stage rivals done in 2.0s ===\n2026-10-21 04:11:50.827 | INFO     | __main__:main:54 - === stage audit done in 10.1s ===\n2026-10-21 04:11:51.490 | INFO     | __main__:main:54 - === stage outputs done in 0.7s ===\n2026-10-21 04:12:11.763 | INFO     | __main__:main:54 - === stage outputs done in 0.8s ===\n2026-10-21 04:15:00.651 | INFO     | __main__:main:54 - === stage inventory done in 2.1s ===\n2026-10-21 04:15:02.424 | INFO     | __main__:main:54 - === stage rows done in 1.8s ===\n2026-10-21 04:15:18.756 | INFO     | __main__:main:54 - === stage judges done in 16.3s ===\n2026-10-21 04:15:25.976 | INFO     | src.knob:build_knob_table:222 - knob table: 1120 cells; computing rarefied Hill-1 with 5 workers\n2026-10-21 04:15:41.576 | INFO     | src.stages:stage_knob:134 - knob table: 1120 rows -> tables/knob_table.csv\n2026-10-21 04:15:41.579 | INFO     | __main__:main:54 - === stage knob done in 22.8s ===\n2026-10-21 04:15:41.852 | INFO     | src.screen:run_screen_stage:366 - verification targets: 25/27 matched\n2026-10-21 04:15:42.228 | INFO     | src.screen:run_screen_stage:389 - screen.json sha256 d6a2ca9711f461973c39482314a523d448d0590cb40e32432826dec1da4846e8; movable ['T03', 'T05', 'T06', 'T1', 'T10', 'T2']\n2026-10-21 04:15:42.262 | INFO     | __main__:main:54 - === stage screen done in 0.7s ===\n2026-10-21 04:15:46.977 | INFO     | __main__:main:54 - === stage route done in 4.7s ===\n2026-10-21 04:15:47.049 | INFO     | __main__:main:54 - === stage llama done in 0.1s ===\n2026-10-21 04:15:48.253 | INFO     | __main__:main:54 - === stage other done in 1.2s ===\n2026-10-21 04:16:14.220 | INFO     | __main__:main:54 - === stage figures done in 26.0s ===\n2026-10-21 04:16:14.542 | INFO     | __main__:main:54 - === stage rigor done in 0.3s ===\n2026-10-21 04:16:14.614 | INFO     | __main__:main:54 - === stage wording done in 0.1s ===\n2026-10-21 04:16:16.619 | INFO     | __main__:main:54 - === stage rivals done in 2.0s ===\n2026-10-21 04:16:28.115 | INFO     | __main__:main:54 - === stage audit done in 11.5s ===\n2026-10-21 04:16:28.755 | INFO     | __main__:main:54 - === stage outputs done in 0.6s ===\n2026-10-21 04:16:57.255 | INFO     | src.screen:run_screen_stage:369 - verification targets: 25/27 matched\n2026-10-21 04:16:57.649 | INFO     | src.screen:run_screen_stage:392 - screen.json sha256 d6a2ca9711f461973c39482314a523d448d0590cb40e32432826dec1da4846e8; movable ['T03', 'T05', 'T06', 'T1', 'T10', 'T2']\n2026-10-21 04:16:57.674 | INFO     | __main__:main:54 - === stage screen done in 4.7s ===\n2026-10-21 04:16:58.753 | INFO     | __main__:main:54 - === stage other done in 1.1s ===\n2026-10-21 04:17:09.122 | INFO     | __main__:main:54 - === stage audit done in 10.4s ===\n2026-10-21 04:17:09.843 | INFO     | __main__:main:54 - === stage outputs done in 0.7s ===\n2026-10-21 04:24:04.237 | INFO     | __main__:main:54 - === stage audit done in 25.6s ===\n2026-10-21 04:24:05.255 | INFO     | __main__:main:54 - === stage outputs done in 1.0s ===", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [33] TOOL CALL — Bash · 2026-10-26 10:53:37 UTC

```
Check available Python libraries for data inspection:
cd /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3 && ls .venv 2>/dev/null | head -3; which python3; python3 -c "import pandas, numpy, scipy, pyarrow; print(pandas.__version__, numpy.__version__, scipy.__version__, pyarrow.__version__)" 2>&1
```

### [34] TOOL RESULT — Bash · 2026-10-26 10:53:37 UTC

```
{"stdout": "/usr/local/bin/python3\n2.3.3 2.2.6 1.16.3 25.0.0", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [35] ASSISTANT · 2026-10-26 10:53:47 UTC

```
System Python has pandas/pyarrow, so I can inspect the parquet files read-only. Let me look at the row schema and the knob table's family/task distribution.
```

### [36] TOOL CALL — Bash · 2026-10-26 10:53:47 UTC

```
Inspect rows and knob parquet schemas:
cd /tmp && python3 -I - <<'EOF'
import pandas as pd, json
A="/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3"
rows=pd.read_parquet(f"{A}/data/rows.parquet")
print("ROWS", rows.shape); print(rows.dtypes.to_string())
print(rows.head(3).T.to_string()[:3000])
knob=pd.read_parquet(f"{A}/data/knob.parquet")
print("KNOB", knob.shape); print(list(knob.columns))
print(knob.groupby(["exp","family"]).size().to_string())
EOF
```

### [37] TOOL RESULT — Bash · 2026-10-26 10:53:47 UTC

```
{"stdout": "ROWS (65433, 18)\nartifact_id     object\nsrc_file        object\nmodel           object\nengine          object\nprecision       object\ntask            object\narm             object\ndial            object\ntemplate        object\nsample_id       object\nlabel           object\nlabel_norm      object\nis_catalogue      bool\nis_default        bool\nattempted         bool\npassed            bool\ncode_sha256     object\nextra           object\n                                                                             0                                                                 1                                                                 2\nartifact_id                                                   art_pVlCZ272hDV7                                                  art_pVlCZ272hDV7                                                  art_pVlCZ272hDV7\nsrc_file                                                     data/labels.jsonl                                                 data/labels.jsonl                                                 data/labels.jsonl\nmodel                                                            Qwen/Qwen3-8B                                                     Qwen/Qwen3-8B                                                     Qwen/Qwen3-8B\nengine                                                                      hf                                                                hf                                                                hf\nprecision                                                                  fp8                                                               fp8                                                               fp8\ntask                                                                        T2                                                                T2                                                                T2\narm                                                                     U7_BAN                                                            U7_BAN                                                            U7_BAN\ndial                                                                        {}                                                                {}                                                                {}\ntemplate                                                                    W1                                                                W1                                                                W1\nsample_id                                                       T2|W1|U7_BAN|0                                                                 1                                                                 2\nlabel                                                                  bf_spfa                                                          dijkstra                                                           bf_spfa\nlabel_norm                                                             bf_spfa                                                          dijkstra                                                           bf_spfa\nis_catalogue                                                              True                                                              True                                                              True\nis_default                                    \nKNOB (1120, 46)\n['cid', 'exp', 'artifact_id', 'src_file', 'model', 'engine', 'precision', 'task', 'arm', 'dial', 'n', 'n_attempted', 'n_correct', 'n_default_att', 'n_cat_nondefault_att', 'correct_composition', 'attempted_composition', 'offdef_attempted_cat_composition', 'other_share', 'class', 'family', 'description', 'pass_rate', 'offdef_share', 'cat_only_avoidance', 'H1r25', 'H1r25_ci90', 'H1r25_ci90_iid', 'ci_unit', 'H1r25_cat', 'H1r10', 'S_obs', 'coverage', 'ref_key', 'flags_list', 'ref_arm', 'ref_pass', 'pass_cost_pts', 'pass_cost_ci95', 'ref_offdef_share', 'escape', 'qualify', 'flags', 'sources', 'row_id', 'realised_l21_displacement_ratio']\nexp    family                \nexp11  pilot                      26\nexp13  activation-ban-derived     12\n       activation-random          36\n       prompt:ban                 12\n       prompt:nonce               12\n       prompt:novelty             12\n       sham_veto                  12\n       twin                       24\n       veto                       55\nexp14  copy                       33\n       prompt:exposure_ban       142\n       twin                       12\n       veto                       93\nexp15  activation-random          36\n       pilot                      13\n       prompt:ban                 18\n       prompt:nonce               12\n       prompt:novelty             12\n       twin                       24\n       veto                       47\nexp16  route_diagnostic          176\nexp17  ablation-on-ban            18\n       activation-random          72\n       activation-structured      18\n       engine_check                2\n       prompt:ban                  7\n       twin                        6\nexp18  prompt:ban                  6\n       prompt:instruction         21\n       prompt:list                17\n       sham_veto                   4\n       twin                        6\n       veto                       23\nexp4   activation-random           4\n       activation-structured      20\n       mention_twin                2\n       prompt:ban                  4\n       prompt:instruction          4\n       twin                        4\nexp6   decoding                   32\n       generate_then_select        2\n       prompt:instruction          8\n       prompt:seed                 6\n       twin                        2\nexp9   prompt:ban                  2\n       prompt:list                 9\n       twin                        2", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [38] THINKING · 2026-10-26 10:54:43 UTC

```
exp17's 72 random-direction cells plus exp13's 36 push the full screen to ~140 cells, exceeding the 100-example cap. I'll size each piece so I can curate a subset that still reproduces the per-task screen records exactly while covering diverse knob families.
```

### [39] TOOL CALL — Bash · 2026-10-26 10:54:43 UTC

```
Count screen cells and list candidate knob cells:
cd /tmp && python3 -I - <<'EOF'
import pandas as pd, json
A="/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3"
knob=pd.read_parquet(f"{A}/data/knob.parquet")
pd.set_option("display.width",250); pd.set_option("display.max_colwidth",60)
sel = knob[(knob.family=="activation-random") & knob.exp.isin(["exp13","exp17"])]
print("direction rows per task/exp:"); print(sel.groupby(["task","exp"]).size().unstack(fill_value=0).to_string())
print("exp17 twins:", knob[(knob.exp=="exp17")&(knob.arm=="NEUTRAL")][["task","n","precision"]].values.tolist())
print("exp13 hf_twin tasks:", sorted(knob[(knob.exp=="exp13")&(knob.arm=="hf_twin")].task))
print("exp13 ban tasks:", sorted(knob[(knob.exp=="exp13")&(knob.arm=="ban")].task))
print("n stats:", knob.n.describe().to_string())
for e in ["exp6","exp18","exp9","exp4"]:
    q=knob[knob.exp==e][["row_id","task","arm","dial","precision","n","family","H1r25","pass_cost_pts","ci_unit"]]
    print("=====",e, len(q)); print(q.to_string(index=False))
EOF
```

### [40] TOOL RESULT — Bash · 2026-10-26 10:54:43 UTC

```
{"stdout": "direction rows per task/exp:\nexp   exp13  exp17\ntask              \nR1        3      0\nR3        3      0\nR6        3      0\nT03       3     18\nT04       3      6\nT05       3      6\nT06       3      6\nT08       3      0\nT1        0     18\nT10       3      0\nT11       3      0\nT13       3      0\nT14       3      0\nT2        0     18\nexp17 twins: [['T03', 100, 'fp8'], ['T04', 100, 'fp8'], ['T05', 100, 'fp8'], ['T06', 100, 'fp8'], ['T1', 100, 'fp8'], [... [truncated, 29339 chars total]
```

### [41] THINKING · 2026-10-26 10:55:59 UTC

```
This data aligns with the research question on temperature, seeds, creativity instructions, bans, and steering directions versus Hill-1 diversity and pass cost. Now I'll review the rest of the screen stage, the frozen `screen.json`, and the exp11 task specs needed for `catalogue()`.
```

### [42] TOOL CALL — Bash · 2026-10-26 10:55:59 UTC

```
Read screen stage tail and frozen screen output:
A=/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3; sed -n 400,520p $A/src/screen.py; echo "=== SCREEN.JSON"; python3 -c "
import json; d=json.load(open('$A/screen.json'))
print(list(d.keys()))
for t,v in d['tasks'].items(): print(t, json.dumps(v))
print(d['movable_tasks'], d['c1_event_set']); print(d['source_sha256'])"; cat $A/screen.sha256; ls /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_11/bench/ 2>&1 | head
```

### [43] TOOL RESULT — Bash · 2026-10-26 10:55:59 UTC

```
{"stdout": "    n_comp = sum(comp.values())\n    power = {}\n    for t in QWEN14:\n        k = sum(1 for r in drows if r[\"task\"] == t)\n        n_esc = sum(rule.escape_of(r)[0] for r in drows if r[\"task\"] == t)\n        power[t] = {\"K_direction_alpha_cells\": k, \"n_escape\": n_esc,\n                    \"ub90_per_direction_escape_if_zero\": round(upper_bound_zero_of_k(k), 4) if n_esc == 0 else None}\n    per_engine = {}\n    for t in QWEN14:\n        for eng in (\"hf-fp8\", \"hf-bf16\"):\n            rr = [r for r in drows if r[\"task\"] == t and r[\"engine\"] == eng]\n            if rr:\n                per_engine.setdefault(t, {})[eng] = {\n                    \"n_run\": len(rr), \"n_escape\": sum(rule.escape_of(r)[0] for r in rr),\n                    \"escaping\": [r[\"direction_id\"] + f\"@a{r['alpha']}\" for r in rr if rule.escape_of(r)[0]],\n                    \"H1r25\": {r[\"direction_id\"] + f\"@a{r['alpha']}\": r[\"H1r25\"] for r in rr}}\n    disc = []\n    for t in C1_SET:\n        if not movable[t]:\n            disc.append({\"task\": t, \"note\": f\"{t} is in the frozen C1 event set by the hypothesis's decree but does not \"\n                                             \"escape mechanically under the pass >= 0.8 x twin rule; the set is not edited.\"})\n    for t in QWEN14:\n        if movable[t] and not comp[t]:\n            disc.append({\"task\": t, \"note\": \"movable but catalogue-only ban avoidance < 0.5 (screen rule violated)\"})\n        if not movable[t] and comp[t]:\n            disc.append({\"task\": t, \"note\": \"not movable but ban avoidance >= 0.5 (screen rule violated)\"})\n    extras = {\"per_direction_rows\": drows, \"per_engine\": per_engine, \"power_note\": power,\n              \"power_note_text\": \"With K direction-alpha cells and 0 escapes, the one-sided 90% upper bound on a task's \"\n                                 \"per-direction escape probability is 1 - 0.1^(1/K) (0.54 at K=3, 0.32 at K=6, 0.14 at K=15): \"\n                                 \"the immovable side is weakly tested; more directions belong to the plan-subspace artifact.\",\n              \"fisher_movable_vs_avoidance\": {**fis, \"label\": \"descriptive only: screen, not confirmation (rule read off the same data)\"},\n              \"hypergeometric_one_sided_if_perfect\": 1 / math.comb(len(QWEN14), max(k_mov, 1)) if k_mov == n_comp else None,\n              \"balanced_accuracy\": ba, \"n_movable\": k_mov, \"n_ban_avoidance_ge_0_5\": n_comp,\n              \"ban_avoidance_sources\": av_src, \"discrepancies\": disc,\n              \"escaping_engine_per_task\": {t: sorted({r[\"engine\"] for r in drows if r[\"task\"] == t and rule.escape_of(r)[0]})\n                                           for t in QWEN14},\n              \"screen_sha256\": sha}\n    (WS / \"screen_extras.json\").write_text(json.dumps(extras, indent=1, default=str))\n    summary = {\"sha256\": sha, \"movable_tasks\": core[\"movable_tasks\"], \"n_movable\": k_mov,\n               \"fisher_p_descriptive\": fis[\"p\"], \"table\": fis[\"table\"], \"balanced_accuracy\": ba,\n               \"verification\": {\"n_targets\": int(len(vt)), \"n_matched\": int(vt.match.sum())},\n               \"E\": {f\"{t}_a{int(a)}\": core[\"tasks\"][t][f\"alpha_{int(a)}\"][\"E_t\"] for t in QWEN14 for a in (1.0, 2.0)}}\n    (RES / \"screen_summary.json\").write_text(json.dumps(summary, indent=1, default=str))\n=== SCREEN.JSON\n['c1_event_set', 'escape_rule', 'movable_tasks', 'screen_rule', 'screen_version', 'source_sha256', 'tasks']\nR1 {\"alpha_1\": {\"E_t\": 0.0, \"n_directions_run\": 3, \"n_escape\": 0}, \"alpha_2\": {\"E_t\": null, \"n_directions_run\": 0, \"n_escape\": 0}, \"ban_avoidance_ge_0_5\": false, \"cat_only_ban_avoidance\": 0.0, \"movable\": 0, \"push_landing\": {}, \"push_top1\": null}\nR3 {\"alpha_1\": {\"E_t\": 0.0, \"n_directions_run\": 3, \"n_escape\": 0}, \"alpha_2\": {\"E_t\": null, \"n_directions_run\": 0, \"n_escape\": 0}, \"ban_avoidance_ge_0_5\": false, \"cat_only_ban_avoidance\": 0.08, \"movable\": 0, \"push_landing\": {}, \"push_top1\": null}\nR6 {\"alpha_1\": {\"E_t\": 0.0, \"n_directions_run\": 3, \"n_escape\": 0}, \"alpha_2\": {\"E_t\": null, \"n_directions_run\": 0, \"n_escape\": 0}, \"ban_avoidance_ge_0_5\": false, \"cat_only_ban_avoidance\": 0.01, \"movable\": 0, \"push_landing\": {}, \"push_top1\": null}\nT03 {\"alpha_1\": {\"E_t\": 0.4444, \"n_directions_run\": 18, \"n_escape\": 8}, \"alpha_2\": {\"E_t\": 1.0, \"n_directions_run\": 3, \"n_escape\": 3}, \"ban_avoidance_ge_0_5\": true, \"cat_only_ban_avoidance\": 0.97, \"movable\": 1, \"push_landing\": {\"heapify_pop\": 0.0032, \"quickselect\": 0.6457, \"size_k_heap\": 0.3511}, \"push_top1\": \"quickselect\"}\nT04 {\"alpha_1\": {\"E_t\": 0.0, \"n_directions_run\": 6, \"n_escape\": 0}, \"alpha_2\": {\"E_t\": 0.0, \"n_directions_run\": 3, \"n_escape\": 0}, \"ban_avoidance_ge_0_5\": false, \"cat_only_ban_avoidance\": 0.4, \"movable\": 0, \"push_landing\": {}, \"push_top1\": null}\nT05 {\"alpha_1\": {\"E_t\": 0.0, \"n_directions_run\": 6, \"n_escape\": 0}, \"alpha_2\": {\"E_t\": 0.6667, \"n_directions_run\": 3, \"n_escape\": 2}, \"ban_avoidance_ge_0_5\": true, \"cat_only_ban_avoidance\": 0.86, \"movable\": 1, \"push_landing\": {\"brute_force\": 1.0}, \"push_top1\": \"brute_force\"}\nT06 {\"alpha_1\": {\"E_t\": 0.0, \"n_directions_run\": 6, \"n_escape\": 0}, \"alpha_2\": {\"E_t\": 0.3333, \"n_directions_run\": 3, \"n_escape\": 1}, \"ban_avoidance_ge_0_5\": true, \"cat_only_ban_avoidance\": 0.79, \"movable\": 1, \"push_landing\": {\"index_marking\": 0.2105, \"sort_adjacent\": 0.7895}, \"push_top1\": \"sort_adjacent\"}\nT08 {\"alpha_1\": {\"E_t\": 0.0, \"n_directions_run\": 3, \"n_escape\": 0}, \"alpha_2\": {\"E_t\": null, \"n_directions_run\": 0, \"n_escape\": 0}, \"ban_avoidance_ge_0_5\": false, \"cat_only_ban_avoidance\": 0.01, \"movable\": 0, \"push_landing\": {}, \"push_top1\": null}\nT1 {\"alpha_1\": {\"E_t\": 0.0667, \"n_directions_run\": 15, \"n_escape\": 1}, \"alpha_2\": {\"E_t\": 0.0, \"n_directions_run\": 3, \"n_escape\": 0}, \"ban_avoidance_ge_0_5\": true, \"cat_only_ban_avoidance\": 0.86, \"movable\": 1, \"push_landing\": {\"dfs\": 1.0}, \"push_top1\": \"dfs\"}\nT10 {\"alpha_1\": {\"E_t\": 0.3333, \"n_directions_run\": 3, \"n_escape\": 1}, \"alpha_2\": {\"E_t\": null, \"n_directions_run\": 0, \"n_escape\": 0}, \"ban_avoidance_ge_0_5\": true, \"cat_only_ban_avoidance\": 1.0, \"movable\": 1, \"push_landing\": {\"dfs\": 1.0}, \"push_top1\": \"dfs\"}\nT11 {\"alpha_1\": {\"E_t\": 0.0, \"n_directions_run\": 3, \"n_escape\": 0}, \"alpha_2\": {\"E_t\": null, \"n_directions_run\": 0, \"n_escape\": 0}, \"ban_avoidance_ge_0_5\": false, \"cat_only_ban_avoidance\": 0.02, \"movable\": 0, \"push_landing\": {}, \"push_top1\": null}\nT13 {\"alpha_1\": {\"E_t\": 0.0, \"n_directions_run\": 3, \"n_escape\": 0}, \"alpha_2\": {\"E_t\": null, \"n_directions_run\": 0, \"n_escape\": 0}, \"ban_avoidance_ge_0_5\": false, \"cat_only_ban_avoidance\": 0.14, \"movable\": 0, \"push_landing\": {}, \"push_top1\": null}\nT14 {\"alpha_1\": {\"E_t\": 0.0, \"n_directions_run\": 3, \"n_escape\": 0}, \"alpha_2\": {\"E_t\": null, \"n_directions_run\": 0, \"n_escape\": 0}, \"ban_avoidance_ge_0_5\": false, \"cat_only_ban_avoidance\": 0.47, \"movable\": 0, \"push_landing\": {}, \"push_top1\": null}\nT2 {\"alpha_1\": {\"E_t\": 0.2, \"n_directions_run\": 15, \"n_escape\": 3}, \"alpha_2\": {\"E_t\": 0.0, \"n_directions_run\": 3, \"n_escape\": 0}, \"ban_avoidance_ge_0_5\": true, \"cat_only_ban_avoidance\": 0.83, \"movable\": 1, \"push_landing\": {\"bf_spfa\": 1.0}, \"push_top1\": \"bf_spfa\"}\n['T03', 'T05', 'T06', 'T1', 'T10', 'T2'] ['T03', 'T05', 'T06', 'T1', 'T10', 'T2']\n{'art_1AYTO1Epb_7t:data/samples.jsonl': '4b5d786d1ae4cfc38ce0618d1086fa7b188c66e549039106f0947342d4a665b7', 'art_IVZc3TWCeE9f:data/samples.jsonl': '4f6d1bcf9a5df5356b30a57f33edf05a086e6100b677692ad425d8808c1b76f8', 'art_pVlCZ272hDV7:data/labels.jsonl': '62349de7e02379d90b995499e62768883ec33d8e873ed47c336c223cc6e4b327'}\nd6a2ca9711f461973c39482314a523d448d0590cb40e32432826dec1da4846e8  screen.json\nR1_non_overlapping_intervals\nR2_cycle_detection\nR3_topological_order\nR6_first_last_position\nT03_kth_smallest\nT04_substring_search\nT05_two_sum\nT06_find_duplicate\nT08_fibonacci\nT10_connected_components", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [44] THINKING · 2026-10-26 10:57:59 UTC

```
I can reproduce the per-task records exactly from the counts shown. Before curating, I'll verify row field constancy per cell, check NaN encoding in the eval output, and inspect candidate cell sizes.
```

### [45] TOOL CALL — Bash · 2026-10-26 10:57:59 UTC

```
Check per-cell field constancy and NaN encoding:
cd /tmp && python3 -I - <<'EOF'
import pandas as pd, json
A="/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3"
rows=pd.read_parquet(f"{A}/data/rows.parquet")
keys=["artifact_id","task","arm","dial","precision"]
g=rows.groupby(keys)
for c in ["src_file","model","engine","template"]:
    nun=g[c].nunique(dropna=False)
    print(c, "cells with >1 distinct:", int((nun>1).sum()), "of", len(nun), "| null count:", int(rows[c].isna().sum()))
print("template values:", rows.template.value_counts(dropna=False).head(12).to_dict())
print("engine values:", rows.engine.value_counts(dropna=False).to_dict())
print("extra sample:", rows.extra.dropna().head(3).tolist())
raw=open(f"{A}/full_eval_out.json").read()
print("NaN tokens in full_eval_out:", raw.count("NaN"), " null tokens:", raw.count("null"))
# check example with NaN
d=json.loads(raw)
kt=[ds for ds in d["datasets"] if ds["dataset"]=="knob_table"][0]["examples"]
ex=[e for e in kt if e["metadata_row_id"]=="K1071"][0]
print(json.dumps(ex, indent=0)[:2500])
EOF
```

### [46] TOOL RESULT — Bash · 2026-10-26 10:57:59 UTC

```
{"stdout": "src_file cells with >1 distinct: 0 of 1120 | null count: 0\nmodel cells with >1 distinct: 0 of 1120 | null count: 0\nengine cells with >1 distinct: 0 of 1120 | null count: 0\ntemplate cells with >1 distinct: 663 of 1120 | null count: 0\ntemplate values: {'None': 17630, 'W5': 8290, 'W1': 6910, 'W4': 6890, 'W2': 6870, 'W3': 6830, '3': 1818, '4': 1800, '5': 1798, '1': 1786, '2': 1786, 'UNNAMED': 1650}\nengine values: {'vllm': 39963, 'hf': 25470}\nextra sample: ['{}', '{}', '{}']\nNaN tokens in full_eval_out: 690  null tokens: 801\n{\n\"input\": \"art_UoCVh2Qe5RZ0 | task T1 | arm A3:instr_fully_novel | dial {\\\"T\\\": 1.0, \\\"sampler\\\": \\\"pure\\\", \\\"thinking\\\": false} | vllm/bf16 | n=100\",\n\"output\": \"H1r25=1.229 CI90=[1.053, 1.4097]; pass=0.850; cost=12.0 pts vs A0:baseline {\\\"T\\\": 1.0, \\\"sampler\\\": \\\"pure\\\", \\\"thinking\\\": false}; offdef=0.130; cat_only=0.130\",\n\"metadata_row_id\": \"K1071\",\n\"metadata_class\": \"knob\",\n\"metadata_family\": \"prompt:instruction\",\n\"metadata_model\": \"Qwen/Qwen3-8B\",\n\"metadata_ref_arm\": \"A0:baseline {\\\"T\\\": 1.0, \\\"sampler\\\": \\\"pure\\\", \\\"thinking\\\": false}\",\n\"metadata_correct_composition\": \"{\\\"bfs\\\": 81, \\\"dijkstra_unit\\\": 2, \\\"dfs\\\": 1, \\\"astar\\\": 1}\",\n\"metadata_attempted_composition\": \"{\\\"bfs\\\": 87, \\\"dfs\\\": 10, \\\"dijkstra_unit\\\": 2, \\\"astar\\\": 1}\",\n\"metadata_flags\": \"\",\n\"metadata_sources\": \"art_UoCVh2Qe5RZ0:results/samples.jsonl\",\n\"metadata_ci_unit\": \"program\",\n\"predict_escape\": \"False\",\n\"predict_qualify\": \"False\",\n\"eval_H1r25\": 1.229391397648806,\n\"eval_H1r25_cat\": 1.2237848253706074,\n\"eval_pass_rate\": 0.85,\n\"eval_pass_cost_pts\": 12.0,\n\"eval_offdef_share\": 0.13,\n\"eval_cat_only_avoidance\": 0.13,\n\"eval_coverage\": 0.9764705882352941,\n\"eval_S_obs\": 4.0,\n\"eval_n\": 100.0\n}", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [47] THINKING · 2026-10-26 10:58:31 UTC

```
Since src_file, model, and engine stay constant per cell and only template varies per program, I'll check the exp11 task spec structure for catalogue() and verify the candidate cell selection resolves to ~99 cells.
```

### [48] TOOL CALL — Bash · 2026-10-26 10:58:31 UTC

```
Inspect exp11 task spec catalogues:
B=/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_11/bench; python3 -c "
import json
for d in ['T03_kth_smallest','T10_connected_components','T13_merge_intervals','T14_top_k_frequent']:
    s=json.load(open('$B/'+d+'/spec.json'))
    print(d, list(s.keys()))
    print('  ', [(c['mode'], c.get('display_name')) for c in s['catalogue']])
"
```

### [49] TOOL RESULT — Bash · 2026-10-26 10:58:31 UTC

```
{"stdout": "T03_kth_smallest ['task', 'task_id', 'leetcode_ids', 'signature', 'description', 'format_line', 'spec_text', 'bounds', 'catalogue', 'aliases', 'forced_templates', 'descriptive_forced_template', 'association_template', 'spec_version']\n   [('full_sort', 'a full sort'), ('size_k_heap', 'a size-k heap'), ('heapify_pop', 'heapify-and-pop'), ('quickselect', 'quickselect'), ('median_of_medians', 'median of medians'), ('counting_sort', 'counting sort')]\nT10_connected_components ['task', 'task_id', 'leetcode_ids', 'signature', 'description', 'format_line', 'spec_text', 'bounds', 'catalogue', 'aliases', 'forced_templates', 'descriptive_forced_template', 'association_template', 'spec_version']\n   [('bfs', 'breadth-first search (BFS)'), ('dfs', 'depth-first search (DFS)'), ('union_find', 'union-find (disjoint set union)'), ('label_propagation', 'label propagation')]\nT13_merge_intervals ['task', 'task_id', 'leetcode_ids', 'signature', 'description', 'format_line', 'spec_text', 'bounds', 'catalogue', 'aliases', 'forced_templates', 'descriptive_forced_template', 'association_template', 'spec_version']\n   [('sort_sweep', 'sorting and a single sweep'), ('interval_tree', 'an interval tree'), ('union_find', 'union-find over overlapping intervals')]\nT14_top_k_frequent ['task', 'task_id', 'leetcode_ids', 'signature', 'description', 'format_line', 'spec_text', 'bounds', 'catalogue', 'aliases', 'forced_templates', 'descriptive_forced_template', 'association_template', 'spec_version']\n   [('sort_by_count', 'sorting by frequency'), ('heap', 'a heap'), ('bucket_sort', 'bucket sort by frequency'), ('quickselect_counts', 'quickselect on the counts')]", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [50] THINKING · 2026-10-26 10:59:19 UTC

```
I've worked out a 99-cell selection plan from the `knob_table` dataset covering the key screen groups and path-search knobs on T1, ordered so any prefix stays self-consistent. Now I'll write a curation script in the workspace so this subset can be regenerated.
```

### [51] TOOL CALL — Write · 2026-10-26 10:59:19 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/make_mini_demo_data.py

#!/usr/bin/env python3
"""Build mini_demo_data.json: 99 knob-table cells (one dataset) with the labelled program rows behind each cell.

Reads (read-only) the evaluation artifact art_sV0cQ3ef1ZRQ: data/rows.parquet (labelled program rows),
data/knob.parquet (cell keys and recorded CIs), full_eval_out.json (the recorded knob_table examples), screen.json and
screen.sha256 (the frozen push screen), plus the exp11 bench spec.json catalogues of the screened bench tasks.

    python3 make_mini_demo_data.py --artifact <artifact folder> --bench <exp11 bench folder> --out mini_demo_data.json

Cells are ordered in groups so that any prefix of the list is self-consistent (each twin precedes the cells priced
against it, and each screen group holds every cell the screen rule reads for that task).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pandas as pd

# (group, exp, task, arm, dial or None) - dial None means "every dial of that arm"
T1_DIAL = '{"T": 1.0, "sampler": "pure", "thinking": false}'
SELECTION: list[tuple[str, str, str, str, str | None]] = []


def _add(group: str, exp: str, task: str, arms: list[str], dial: str | None = None) -> None:
    SELECTION.extend((group, exp, task, a, dial) for a in arms)


# --- screen groups: every cell the push screen reads for these tasks (directions, their twins, the ban row)
for t in ("T10", "T13", "T14"):
    _add(f"screen:{t}", "exp13", t, ["hf_twin", "rand1", "rand2", "rand3", "twin", "ban"])
_add("screen:T03", "exp13", "T03", ["hf_twin", "rand1", "rand2", "rand3", "twin", "ban"])
_add("screen:T03", "exp17", "T03", ["NEUTRAL"])
SELECTION.append(("screen:T03", "exp17", "T03", "__random__", None))
_add("screen:T1", "exp17", "T1", ["NEUTRAL"])
SELECTION.append(("screen:T1", "exp17", "T1", "__random__", None))
_add("screen:T1", "exp9", "T1", ["baseline", "single:bfs"])
# --- path-search task T1: every kind of knob the study tried, each with its own twin
_add("knobs:T1", "exp9", "T1", ["multi:ARC", "multi:SCATTER", "multi:TOP", "multi:TOP5"])
_add("knobs:T1", "exp6", "T1", ["A0:baseline"], T1_DIAL)
for T in (0.3, 0.7, 1.0, 1.3):
    for s in ("topk10", "topp095"):
        _add("knobs:T1", "exp6", "T1", ["A1:baseline"], json.dumps({"T": T, "sampler": s, "thinking": False}, sort_keys=True))
_add("knobs:T1", "exp6", "T1", ["A2:seed_entropy", "A2:seed_semantic", "A2:seed_word"], T1_DIAL)
_add("knobs:T1", "exp6", "T1", ["A3:instr_creative", "A3:instr_enumerate", "A3:instr_fully_novel", "A3:instr_new_algo"],
     T1_DIAL)
_add("knobs:T1", "exp6", "T1", ["A4s2:gen_then_select"], T1_DIAL)
_add("knobs:T1", "exp4", "T1", ["baseline", "ban:bfs", "succession:2"])
_add("knobs:T1", "exp4", "T1", ["steer:dc"], '{"c": 0.0, "layer": 18}')
_add("knobs:T1", "exp4", "T1", ["steer:dc"], '{"c": 0.25, "layer": 18}')
_add("knobs:T1", "exp4", "T1", ["steer:rand1"], '{"c": 0.1, "layer": 18}')
_add("knobs:T1", "exp18", "T1", ["walk_twin", "two_step:TWO(bfs,dfs)", "sham", "fixed_top5"])
_add("knobs:T1", "exp18", "T1", ["longform:LF1"], '{"thinking": false}')
# --- prompt knobs and vetoes on T03 (priced against the exp13 vLLM twin already in screen:T03)
_add("knobs:T03", "exp13", "T03", ["novelty", "nonce", "oneshot"])

GROUP_NOTES = {
    "screen:T10": "connected components: exp13 bf16 random directions rand1-3, their HF twin, the modal ban and its vLLM twin",
    "screen:T13": "merge intervals (immovable): exp13 random directions, HF twin, modal ban and vLLM twin",
    "screen:T14": "top-k frequent (immovable; modal ban Hill 1.78 at 17 pts): exp13 random directions, twins, modal ban",
    "screen:T03": "k-th smallest: exp13 rand1-3 + exp17 RAND90xx directions at alpha 1 and 2, both twins, the modal ban",
    "screen:T1": "path search: exp17 RAND90xx directions at alpha 1 and 2 and their twin; exp9 single BFS ban and its baseline",
    "knobs:T1": ("path search: temperature x sampler grid, context seeds, creativity instructions, generate-then-select, "
                 "top-k / list bans, decommitment and random steering, token vetoes, 2,000-word novelty instruction"),
    "knobs:T03": "k-th smallest: novelty instruction, nonce ban and one-shot token veto (exp13)",
}


def _clean(x):
    """NaN -> None so the file is strict JSON."""
    if isinstance(x, float) and not math.isfinite(x):
        return None
    if isinstance(x, dict):
        return {k: _clean(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_clean(v) for v in x]
    return x


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", required=True, type=Path)
    ap.add_argument("--bench", required=True, type=Path)
    ap.add_argument("--out", default="mini_demo_data.json", type=Path)
    a = ap.parse_args()

    knob = pd.read_parquet(a.artifact / "data" / "knob.parquet")
    rows = pd.read_parquet(a.artifact / "data" / "rows.parquet")
    full = json.loads((a.artifact / "full_eval_out.json").read_text())
    recorded = {e["metadata_row_id"]: e for ds in full["datasets"] if ds["dataset"] == "knob_table" for e in ds["examples"]}
    frozen = json.loads((a.artifact / "screen.json").read_text())
    sha = (a.artifact / "screen.sha256").read_text().split()[0]

    picked: list[tuple[str, pd.Series]] = []
    for group, exp, task, arm, dial in SELECTION:
        q = knob[(knob.exp == exp) & (knob.task == task)]
        if arm == "__random__":
            q = q[q.family == "activation-random"].sort_values("arm")
        else:
            q = q[q.arm == arm]
            if dial is not None:
                q = q[q.dial == dial]
        if len(q) == 0:
            raise SystemExit(f"no knob cell for {group} {exp} {task} {arm} {dial}")
        if arm != "__random__" and len(q) != 1:
            raise SystemExit(f"ambiguous knob cell for {group} {exp} {task} {arm} {dial}: {len(q)}")
        picked.extend((group, r) for _, r in q.iterrows())
    ids = [r.row_id for _, r in picked]
    assert len(ids) == len(set(ids)), "duplicate cell"

    keys = ["artifact_id", "task", "arm", "dial", "precision"]
    by_cell = {k: g for k, g in rows.groupby(keys, sort=False)}
    examples = []
    for group, r in picked:
        g = by_cell[tuple(r[k] for k in keys)]
        assert len(g) == r.n, (r.row_id, len(g), r.n)
        ex = dict(recorded[r.row_id])
        ex["metadata_demo_group"] = group
        ex["metadata_cell_key"] = {k: r[k] for k in keys}
        ex["metadata_recorded_ci"] = {"H1r25_ci90": json.loads(r.H1r25_ci90), "H1r25_ci90_iid": json.loads(r.H1r25_ci90_iid),
                                      "pass_cost_ci95": json.loads(r.pass_cost_ci95)}
        ex["metadata_programs"] = {
            "src_file": g.src_file.iloc[0], "model": g.model.iloc[0], "engine": g.engine.iloc[0],
            "template": g.template.astype(str).tolist(), "label_norm": g.label_norm.tolist(),
            "is_catalogue": g.is_catalogue.astype(bool).tolist(), "is_default": g.is_default.astype(bool).tolist(),
            "attempted": g.attempted.astype(bool).tolist(), "passed": g.passed.astype(bool).tolist()}
        examples.append(_clean(ex))

    specs = {}
    bench_dirs = {"T03": "T03_kth_smallest", "T10": "T10_connected_components", "T13": "T13_merge_intervals",
                  "T14": "T14_top_k_frequent"}
    for t, d in bench_dirs.items():
        s = json.loads((a.bench / d / "spec.json").read_text())
        specs[t] = {"task": s["task"], "catalogue": [{"mode": c["mode"], "display_name": c["display_name"]}
                                                     for c in s["catalogue"]]}

    groups = {}
    for group, _ in picked:
        groups[group] = groups.get(group, 0) + 1
    out = {
        "metadata": {
            "description": ("Demo subset of the iteration-4 Step-0 knob table (art_sV0cQ3ef1ZRQ): 99 artifact x task x arm "
                            "x dial cells, each carrying its recorded knob-table values and the labelled program rows "
                            "(label, template, attempted, passed, catalogue/default flags) they were computed from."),
            "dataset_source": "art_sV0cQ3ef1ZRQ:full_eval_out.json (dataset knob_table) + data/rows.parquet",
            "groups": [{"group": k, "n_cells": v, "note": GROUP_NOTES[k]} for k, v in groups.items()],
            "original_parameters": {"MASTER_SEED": 20261021, "DEPTH": 25, "DEPTH_LOW": 10, "N_RAREFY": 1000,
                                    "N_BOOT": 1000, "N_BOOT_RAREFY": 200},
            "conventions": full["metadata"]["conventions"],
            "task_specs": specs,
            "frozen_screen": frozen,
            "screen_sha256": sha,
        },
        "datasets": [{"dataset": "knob_table", "examples": examples}],
    }
    a.out.write_text(json.dumps(out, indent=1, allow_nan=False) + "\n")
    n_prog = sum(len(e["metadata_programs"]["label_norm"]) for e in examples)
    print(f"wrote {a.out}: {len(examples)} cells, {n_prog} program rows, {a.out.stat().st_size / 1e6:.2f} MB; groups {groups}")


if __name__ == "__main__":
    main()
```

### [52] TOOL RESULT — Write · 2026-10-26 10:59:19 UTC

```
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/make_mini_demo_data.py", "content": "#!/usr/bin/env python3\n\"\"\"Build mini_demo_data.json: 99 knob-table cells (one dataset) with the labelled program rows behind each cell.\n\nReads (read-only) the evaluation artifact art_sV0cQ3ef1ZRQ: data/rows.parquet (labelled program rows),\ndata/knob.parquet (cell keys and recorded CIs), full_eval_out.json (the recorded knob_table examples), screen.json and\nscreen.sha256 (the frozen push screen), plus the exp11 bench spec.json catalogues of the screened bench tasks.\n\n    python3 make_mini_demo_data.py --artifact <artifact folder> --bench <exp11 bench folder> --out mini_demo_data.json\n\nCells are ordered in groups so that any prefix of the list is self-consistent (each twin precedes the cells priced\nagainst it, and each screen group holds every cell the screen rule reads for that task).\n\"\"\"\n\nfrom __future__ import annotations\n\nimport argparse\nimport json\nimport math\nfrom pathlib import Path\n\nimport pandas as pd\n\n# (group, exp, task, arm, dial or None) - dial None means \"every dial of that arm\"\nT1_DIAL = '{\"T\": 1.0, \"sampler\": \"pure\", \"thinking\": false}'\nSELECTION: list[tuple[str, str, str, str, str | None]] = []\n\n\ndef _add(group: str, exp: str, task: str, arms: list[str], dial: str | None = None) -> None:\n    SELECTION.extend((group, exp, task, a, dial) for a in arms)\n\n\n# --- screen groups: every cell the push screen reads for these tasks (directions, their twins, the ban row)\nfor t in (\"T10\", \"T13\", \"T14\"):\n    _add(f\"screen:{t}\", \"exp13\", t, [\"hf_twin\", \"rand1\", \"rand2\", \"rand3\", \"twin\", \"ban\"])\n_add(\"screen:T03\", \"exp13\", \"T03\", [\"hf_twin\", \"rand1\", \"rand2\", \"rand3\", \"twin\", \"ban\"])\n_add(\"screen:T03\", \"exp17\", \"T03\", [\"NEUTRAL\"])\nSELECTION.append((\"screen:T03\", \"exp17\", \"T03\", \"__random__\", None))\n_add(\"screen:T1\", \"exp17\", \"T1\", [\"NEUTRAL\"])\nSELECTION.append((\"screen:T1\", \"exp17\", \"T1\", \"__random__\", None))\n_add(\"screen:T1\", \"exp9\", \"T1\", [\"baseline\", \"single:bfs\"])\n# --- path-search task T1: every kind of knob the study tried, each with its own twin\n_add(\"knobs:T1\", \"exp9\", \"T1\", [\"multi:ARC\", \"multi:SCATTER\", \"multi:TOP\", \"multi:TOP5\"])\n_add(\"knobs:T1\", \"exp6\", \"T1\", [\"A0:baseline\"], T1_DIAL)\nfor T in (0.3, 0.7, 1.0, 1.3):\n    for s in (\"topk10\", \"topp095\"):\n        _add(\"knobs:T1\", \"exp6\", \"T1\", [\"A1:baseline\"], json.dumps({\"T\": T, \"sampler\": s, \"thinking\": False}, sort_keys=True))\n_add(\"knobs:T1\", \"exp6\", \"T1\", [\"A2:seed_entropy\", \"A2:seed_semantic\", \"A2:seed_word\"], T1_DIAL)\n_add(\"knobs:T1\", \"exp6\", \"T1\", [\"A3:instr_creative\", \"A3:instr_enumerate\", \"A3:instr_fully_novel\", \"A3:instr_new_algo\"],\n     T1_DIAL)\n_add(\"knobs:T1\", \"exp6\", \"T1\", [\"A4s2:gen_then_select\"], T1_DIAL)\n_add(\"knobs:T1\", \"exp4\", \"T1\", [\"baseline\", \"ban:bfs\", \"succession:2\"])\n_add(\"knobs:T1\", \"exp4\", \"T1\", [\"steer:dc\"], '{\"c\": 0.0, \"layer\": 18}')\n_add(\"knobs:T1\", \"exp4\", \"T1\", [\"steer:dc\"], '{\"c\": 0.25, \"layer\": 18}')\n_add(\"knobs:T1\", \"exp4\", \"T1\", [\"steer:rand1\"], '{\"c\": 0.1, \"layer\": 18}')\n_add(\"knobs:T1\", \"exp18\", \"T1\", [\"walk_twin\", \"two_step:TWO(bfs,dfs)\", \"sham\", \"fixed_top5\"])\n_add(\"knobs:T1\", \"exp18\", \"T1\", [\"longform:LF1\"], '{\"thinking\": false}')\n# --- prompt knobs and vetoes on T03 (priced against the exp13 vLLM twin already in screen:T03)\n_add(\"knobs:T03\", \"exp13\", \"T03\", [\"novelty\", \"nonce\", \"oneshot\"])\n\nGROUP_NOTES = {\n    \"screen:T10\": \"connected components: exp13 bf16 random directions rand1-3, their HF twin, the modal ban and its vLLM twin\",\n    \"screen:T13\": \"merge intervals (immovable): exp13 random directions, HF twin, modal ban and vLLM twin\",\n    \"screen:T14\": \"top-k frequent (immovable; modal ban Hill 1.78 at 17 pts): exp13 random directions, twins, modal ban\",\n    \"screen:T03\": \"k-th smallest: exp13 rand1-3 + exp17 RAND90xx directions at alpha 1 and 2, both twins, the modal ban\",\n    \"screen:T1\": \"path search: exp17 RAND90xx directions at alpha 1 and 2 and their twin; exp9 single BFS ban and its baseline\",\n    \"knobs:T1\": (\"path search: temperature x sampler grid, context seeds, creativity instructions, generate-then-select, \"\n                 \"top-k / list bans, decommitment and random steering, token vetoes, 2,000-word novelty instruction\"),\n    \"knobs:T03\": \"k-th smallest: novelty instruction, nonce ban and one-shot token veto (exp13)\",\n}\n\n\ndef _clean(x):\n    \"\"\"NaN -> None so the file is strict JSON.\"\"\"\n    if isinstance(x, float) and not math.isfinite(x):\n        return None\n    if isinstance(x, dict):\n        return {k: _clean(v) for k, v in x.items()}\n    if isinstance(x, list):\n        return [_clean(v) for v in x]\n    return x\n\n\ndef main() -> None:\n    ap = argparse.ArgumentParser()\n    ap.add_argument(\"--artifact\", required=True, type=Path)\n    ap.add_argument(\"--bench\", required=True, type=Path)\n    ap.add_argument(\"--out\", default=\"mini_demo_data.json\", type=Path)\n    a = ap.parse_args()\n\n    knob = pd.read_parquet(a.artifact / \"data\" / \"knob.parquet\")\n    rows = pd.read_parquet(a.artifact / \"data\" / \"rows.parquet\")\n    full = json.loads((a.artifact / \"full_eval_out.json\").read_text())\n    recorded = {e[\"metadata_row_id\"]: e for ds in full[\"datasets\"] if ds[\"dataset\"] == \"knob_table\" for e in ds[\"examples\"]}\n    frozen = json.loads((a.artifact / \"screen.json\").read_text())\n    sha = (a.artifact / \"screen.sha256\").read_text().split()[0]\n\n    picked: list[tuple[str, pd.Series]] = []\n    for group, exp, task, arm, dial in SELECTION:\n        q = knob[(knob.exp == exp) & (knob.task == task)]\n        if arm == \"__random__\":\n            q = q[q.family == \"activation-random\"].sort_values(\"arm\")\n        else:\n            q = q[q.arm == arm]\n            if dial is not None:\n                q = q[q.dial == dial]\n        if len(q) == 0:\n            raise SystemExit(f\"no knob cell for {group} {exp} {task} {arm} {dial}\")\n        if arm != \"__random__\" and len(q) != 1:\n            raise SystemExit(f\"ambiguous knob cell for {group} {exp} {task} {arm} {dial}: {len(q)}\")\n        picked.extend((group, r) for _, r in q.iterrows())\n    ids = [r.row_id for _, r in picked]\n    assert len(ids) == len(set(ids)), \"duplicate cell\"\n\n    keys = [\"artifact_id\", \"task\", \"arm\", \"dial\", \"precision\"]\n    by_cell = {k: g for k, g in rows.groupby(keys, sort=False)}\n    examples = []\n    for group, r in picked:\n        g = by_cell[tuple(r[k] for k in keys)]\n        assert len(g) == r.n, (r.row_id, len(g), r.n)\n        ex = dict(recorded[r.row_id])\n        ex[\"metadata_demo_group\"] = group\n        ex[\"metadata_cell_key\"] = {k: r[k] for k in keys}\n        ex[\"metadata_recorded_ci\"] = {\"H1r25_ci90\": json.loads(r.H1r25_ci90), \"H1r25_ci90_iid\": json.loads(r.H1r25_ci90_iid),\n                                      \"pass_cost_ci95\": json.loads(r.pass_cost_ci95)}\n        ex[\"metadata_programs\"] = {\n            \"src_file\": g.src_file.iloc[0], \"model\": g.model.iloc[0], \"engine\": g.engine.iloc[0],\n            \"template\": g.template.astype(str).tolist(), \"label_norm\": g.label_norm.tolist(),\n            \"is_catalogue\": g.is_catalogue.astype(bool).tolist(), \"is_default\": g.is_default.astype(bool).tolist(),\n            \"attempted\": g.attempted.astype(bool).tolist(), \"passed\": g.passed.astype(bool).tolist()}\n        examples.append(_clean(ex))\n\n    specs = {}\n    bench_dirs = {\"T03\": \"T03_kth_smallest\", \"T10\": \"T10_connected_components\", \"T13\": \"T13_merge_intervals\",\n                  \"T14\": \"T14_top_k_frequent\"}\n    for t, d in bench_dirs.items():\n        s = json.loads((a.bench / d / \"spec.json\").read_text())\n        specs[t] = {\"task\": s[\"task\"], \"catalogue\": [{\"mode\": c[\"mode\"], \"display_name\": c[\"display_name\"]}\n                                                     for c in s[\"catalogue\"]]}\n\n    groups = {}\n    for group, _ in picked:\n        groups[group] = groups.get(group, 0) + 1\n    out = {\n        \"metadata\": {\n            \"description\": (\"Demo subset of the iteration-4 Step-0 knob table (art_sV0cQ3ef1ZRQ): 99 artifact x task x arm \"\n                            \"x dial cells, each carrying its recorded knob-table values and the labelled program rows \"\n                            \"(label, template, attempted, passed, catalogue/default flags) they were computed from.\"),\n            \"dataset_source\": \"art_sV0cQ3ef1ZRQ:full_eval_out.json (dataset knob_table) + data/rows.parquet\",\n            \"groups\": [{\"group\": k, \"n_cells\": v, \"note\": GROUP_NOTES[k]} for k, v in groups.items()],\n            \"original_parameters\": {\"MASTER_SEED\": 20261021, \"DEPTH\": 25, \"DEPTH_LOW\": 10, \"N_RAREFY\": 1000,\n                                    \"N_BOOT\": 1000, \"N_BOOT_RAREFY\": 200},\n            \"conventions\": full[\"metadata\"][\"conventions\"],\n            \"task_specs\": specs,\n            \"frozen_screen\": frozen,\n            \"screen_sha256\": sha,\n        },\n        \"datasets\": [{\"dataset\": \"knob_table\", \"examples\": examples}],\n    }\n    a.out.write_text(json.dumps(out, indent=1, allow_nan=False) + \"\\n\")\n    n_prog = sum(len(e[\"metadata_programs\"][\"label_norm\"]) for e in examples)\n    print(f\"wrote {a.out}: {len(examples)} cells, {n_prog} program rows, {a.out.stat().st_size / 1e6:.2f} MB; groups {groups}\")\n\n\nif __name__ == \"__main__\":\n    main()\n", "structuredPatch": [], "originalFile": null, "userModified": false}
```

### [53] TOOL CALL — Bash · 2026-10-26 10:59:25 UTC

```
Build mini demo data and preview its head:
python3 make_mini_demo_data.py --artifact /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3 --bench /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_11/bench --out mini_demo_data.json && ls -la mini_demo_data.json && head -c 1500 mini_demo_data.json
```

### [54] TOOL RESULT — Bash · 2026-10-26 10:59:27 UTC

```
{"stdout": "wrote mini_demo_data.json: 99 cells, 6925 program rows, 0.76 MB; groups {'screen:T10': 6, 'screen:T13': 6, 'screen:T14': 6, 'screen:T03': 25, 'screen:T1': 21, 'knobs:T1': 32, 'knobs:T03': 3}\n-rw-rw-rw- 1 aii-agent aii-agent 762309 Oct 26 10:59 mini_demo_data.json\n{\n \"metadata\": {\n  \"description\": \"Demo subset of the iteration-4 Step-0 knob table (art_sV0cQ3ef1ZRQ): 99 artifact x task x arm x dial cells, each carrying its recorded knob-table values and the labelled program rows (label, template, attempted, passed, catalogue/default flags) they were computed from.\",\n  \"dataset_source\": \"art_sV0cQ3ef1ZRQ:full_eval_out.json (dataset knob_table) + data/rows.parquet\",\n  \"groups\": [\n   {\n    \"group\": \"screen:T10\",\n    \"n_cells\": 6,\n    \"note\": \"connected components: exp13 bf16 random directions rand1-3, their HF twin, the modal ban and its vLLM twin\"\n   },\n   {\n    \"group\": \"screen:T13\",\n    \"n_cells\": 6,\n    \"note\": \"merge intervals (immovable): exp13 random directions, HF twin, modal ban and vLLM twin\"\n   },\n   {\n    \"group\": \"screen:T14\",\n    \"n_cells\": 6,\n    \"note\": \"top-k frequent (immovable; modal ban Hill 1.78 at 17 pts): exp13 random directions, twins, modal ban\"\n   },\n   {\n    \"group\": \"screen:T03\",\n    \"n_cells\": 25,\n    \"note\": \"k-th smallest: exp13 rand1-3 + exp17 RAND90xx directions at alpha 1 and 2, both twins, the modal ban\"\n   },\n   {\n    \"group\": \"screen:T1\",\n    \"n_cells\": 21,\n    \"note\": \"path search: exp17 RAND90xx directions at alpha 1 and 2 and their twin; exp9 single BFS ban and its baseline\"\n   },\n   {\n    \"group\": \"knobs:T1\",\n    \"n_cells\": 32,\n    \"note\": \"path search: temperature x sampler grid, context seeds, creativity instructions, generate-then-select, top-k / list bans, decommitment and random steering, token", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [55] ASSISTANT · 2026-10-26 10:59:57 UTC

```
Mini data built: 99 cells, 6,925 labelled program rows, 0.76 MB, one dataset (`knob_table`). Now let me load the NotebookEdit tool schema (the TODO asks to build the notebook with it).
```

### [56] TOOL CALL — ToolSearch · 2026-10-26 10:59:57 UTC

```
{'query': 'select:NotebookEdit', 'max_results': 1}
```

### [57] TOOL RESULT — ToolSearch · 2026-10-26 10:59:57 UTC

```
{"matches": ["NotebookEdit"], "query": "select:NotebookEdit", "total_deferred_tools": 24}
```

### [58] THINKING · 2026-10-26 11:05:18 UTC

```
I'll build the notebook by inserting cells in reverse order starting from a skeleton, but first I need to check how `src/outputs.py` records knob values to ensure the comparison matches correctly.
```

### [59] TOOL CALL — Bash · 2026-10-26 11:05:18 UTC

```
Check how recorded knob values are written:
A=/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3; grep -n "knob_table\|eval_H1r\|eval_pass\|predict_escape\|predict_qualify\|eval_coverage\|eval_S_obs\|def _num\|def _f\b\|round(" $A/src/outputs.py | head -40
```

### [60] TOOL RESULT — Bash · 2026-10-26 11:05:18 UTC

```
{"stdout": "32:def _num(x) -> float | None:\n97:        \"0a_knob_table\": {\n107:            \"numbers\": {\"n_targets\": n_t, \"n_matched\": n_m}, \"sources\": [\"tables/knob_table.csv\", \"tables/verification_targets.csv\",\n199:    ds.append({\"dataset\": \"knob_table\", \"examples\": exs})\n326:        \"knob_table\": {\"n_rows\": len(knob), \"file\": \"tables/knob_table.csv\", \"arm_dictionary\": \"tables/arm_dictionary.csv\",", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [61] TOOL CALL — Bash · 2026-10-26 11:05:34 UTC

```
Read knob example writer in outputs module:
A=/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3; sed -n 25,45p $A/src/outputs.py; echo ...; sed -n 170,200p $A/src/outputs.py
```

### [62] TOOL RESULT — Bash · 2026-10-26 11:05:34 UTC

```
{"stdout": "    (\"art_-QPYRaFERCBX\", \"exp10\", 2, \"Llama path-task landings\"),\n    (\"art_3iv5G76C3yoX\", \"exp12\", 2, \"fresh C1 pool on T1/T2 (exp16 screen_paths cites 'exp12_c1_fresh_pool')\"),\n    (\"art_3tH2xtoZ7Gj2\", \"evaluation_2\", 3, \"iteration-3 audit: 306-row knob table, judge cache, g16 recomputation\"),\n    (\"art_j3Rm_lr2nzR6\", \"dataset_1\", 3, \"472 known human / textbook solutions (nearest-solution pool)\"),\n]\n\n\ndef _num(x) -> float | None:\n    try:\n        v = float(x)\n    except (TypeError, ValueError):\n        return None\n    return v if math.isfinite(v) else None\n\n\ndef ex(inp: str, out: str, meta: dict | None = None, pred: dict | None = None, ev: dict | None = None) -> dict:\n    d = {\"input\": str(inp), \"output\": str(out)}\n    for k, v in (meta or {}).items():\n        if v is None or (isinstance(v, float) and not math.isfinite(v)):\n            continue\n        d[f\"metadata_{k}\"] = v\n...\n    vt = pd.read_csv(TAB / \"verification_targets.csv\")\n    ptv = pd.read_csv(TAB / \"per_task_verdict.csv\")\n    dcounts = pd.read_csv(TAB / \"random_direction_counts.csv\")\n    scr = _r(RES / \"screen_summary.json\")\n    screen = _r(WS / \"screen.json\")\n    extras = _r(WS / \"screen_extras.json\")\n    route, llama, other = _r(RES / \"route.json\"), _r(RES / \"llama.json\"), _r(RES / \"other_audit.json\")\n    figs, rigor, wording, rivals = _r(RES / \"figures.json\"), _r(RES / \"rigor.json\"), _r(RES / \"wording.json\"), _r(RES / \"rivals.json\")\n    red, plc, rex = _r(AUD / \"rederive.json\"), _r(AUD / \"placebos.json\"), _r(AUD / \"rederive_extra.json\")\n    pd.DataFrame([{\"artifact_id\": a, \"experiment\": e, \"iteration\": i, \"rows_held\": d,\n                   \"status\": \"listed, not recomputed (not a declared dependency; workspace not opened)\"}\n                  for a, e, i, d in NOT_DECLARED]).to_csv(TAB / \"knob_rows_not_recomputed.csv\", index=False)\n    corr = corrections(scr, route, llama, other, rigor, wording, vt, ptv, rivals, figs, knob)\n    (WS / \"corrections.json\").write_text(json.dumps(corr, indent=1))\n\n    # ---------------- datasets\n    ds = []\n    exs = []\n    for _, r in knob.iterrows():\n        exs.append(ex(f\"{r.artifact_id} | task {r.task} | arm {r.arm} | dial {r.dial} | {r.engine}/{r.precision} | n={r.n}\",\n                      f\"H1r25={r.H1r25:.3f} CI90={r.H1r25_ci90}; pass={r.pass_rate:.3f}; cost={r.pass_cost_pts:.1f} pts vs \"\n                      f\"{r.ref_arm or 'none'}; offdef={r.offdef_share:.3f}; cat_only={r.cat_only_avoidance:.3f}\",\n                      {\"row_id\": r.row_id, \"class\": r[\"class\"], \"family\": r.family, \"model\": r.model, \"ref_arm\": r.ref_arm,\n                       \"correct_composition\": r.correct_composition, \"attempted_composition\": r.attempted_composition,\n                       \"flags\": r[\"flags\"], \"sources\": r[\"sources\"], \"ci_unit\": r.ci_unit},\n                      {\"escape\": r.escape, \"qualify\": r.qualify},\n                      {\"H1r25\": r.H1r25, \"H1r25_cat\": r.H1r25_cat, \"H1r10\": r.H1r10, \"pass_rate\": r.pass_rate,\n                       \"pass_cost_pts\": r.pass_cost_pts, \"offdef_share\": r.offdef_share,\n                       \"cat_only_avoidance\": r.cat_only_avoidance, \"coverage\": r.coverage, \"S_obs\": r.S_obs, \"n\": r.n}))\n    ds.append({\"dataset\": \"knob_table\", \"examples\": exs})\n    ds.append({\"dataset\": \"verification_targets\", \"examples\": [", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [63] TOOL CALL — Bash · 2026-10-26 11:05:46 UTC

```
Check predict field encoding in examples:
A=/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3; sed -n 39,60p $A/src/outputs.py; cd /tmp && python3 -I -c "
import json, collections
d=json.load(open('/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/mini_demo_data.json'))
ex=d['datasets'][0]['examples']
print(collections.Counter(repr(e.get('predict_escape','<absent>')) for e in ex))
print(collections.Counter(repr(e.get('predict_qualify','<absent>')) for e in ex))
print(collections.Counter(tuple(sorted(k for k in e if k.startswith('eval_'))) for e in ex).most_common(4))
"
```

### [64] TOOL RESULT — Bash · 2026-10-26 11:05:46 UTC

```
{"stdout": "def ex(inp: str, out: str, meta: dict | None = None, pred: dict | None = None, ev: dict | None = None) -> dict:\n    d = {\"input\": str(inp), \"output\": str(out)}\n    for k, v in (meta or {}).items():\n        if v is None or (isinstance(v, float) and not math.isfinite(v)):\n            continue\n        d[f\"metadata_{k}\"] = v\n    for k, v in (pred or {}).items():\n        d[f\"predict_{k}\"] = \"null\" if v is None else str(v)\n    for k, v in (ev or {}).items():\n        n = _num(v)\n        if n is not None:\n            d[f\"eval_{k}\"] = n\n    return d\n\n\ndef clean(o):\n    if isinstance(o, float):\n        return o if math.isfinite(o) else None\n    if isinstance(o, dict):\n        return {str(k): clean(v) for k, v in o.items()}\n    if isinstance(o, (list, tuple)):\nCounter({\"'False'\": 64, \"'True'\": 19, \"'null'\": 16})\nCounter({\"'False'\": 73, \"'null'\": 16, \"'True'\": 10})\n[(('eval_H1r25', 'eval_H1r25_cat', 'eval_S_obs', 'eval_cat_only_avoidance', 'eval_coverage', 'eval_n', 'eval_offdef_share', 'eval_pass_cost_pts', 'eval_pass_rate'), 90), (('eval_H1r10', 'eval_S_obs', 'eval_cat_only_avoidance', 'eval_coverage', 'eval_n', 'eval_offdef_share', 'eval_pass_cost_pts', 'eval_pass_rate'), 8), (('eval_S_obs', 'eval_cat_only_avoidance', 'eval_coverage', 'eval_n', 'eval_offdef_share', 'eval_pass_cost_pts', 'eval_pass_rate'), 1)]", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [65] THINKING · 2026-10-26 11:05:58 UTC

```
Flags are stored as strings ("True"/"False"/"null") with NaNs omitted, so I'll map them accordingly. I'll now build the notebook, starting with a one-cell skeleton for the closing summary, then adding cells via NotebookEdit.
```

### [66] TOOL CALL — Write · 2026-10-26 11:05:58 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb

{
 "cells": [
  {
   "cell_type": "markdown",
   "id": "summary",
   "metadata": {},
   "source": [
    "## Summary and scaling\n",
    "\n",
    "The config cell controls the run size. To reproduce the artifact's numbers exactly, set `N_RAREFY = 1000`, `N_BOOT = 1000`, `N_BOOT_RAREFY = 200` and `N_CELLS = 99` and run all cells."
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "name": "python",
   "version": "3.12"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
```

### [67] TOOL RESULT — Write · 2026-10-26 11:05:58 UTC

```
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb", "content": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"summary\",\n   \"metadata\": {},\n   \"source\": [\n    \"## Summary and scaling\\n\",\n    \"\\n\",\n    \"The config cell controls the run size. To reproduce the artifact's numbers exactly, set `N_RAREFY = 1000`, `N_BOOT = 1000`, `N_BOOT_RAREFY = 200` and `N_CELLS = 99` and run all cells.\"\n   ]\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}\n", "structuredPatch": [], "originalFile": null, "userModified": false}
```

### [68] TOOL CALL — Read · 2026-10-26 11:05:58 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb
```

### [69] TOOL RESULT — Read · 2026-10-26 11:05:58 UTC

```
{"type": "notebook", "file": {"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb", "cells": [{"cellType": "markdown", "source": "## Summary and scaling\n\nThe config cell controls the run size. To reproduce the artifact's numbers exactly, set `N_RAREFY = 1000`, `N_BOOT = 1000`, `N_BOOT_RAREFY = 200` and `N_CELLS = 99` and run all cells.", "cell_id": "summary"}]}}
```

### [70] ASSISTANT · 2026-10-26 11:08:22 UTC

```
Skeleton is in place. Now inserting the cells — each insert without `cell_id` goes to the top, so I insert from the last cell backwards. Starting with the visualization cell.
```

### [71] TOOL CALL — NotebookEdit · 2026-10-26 11:08:22 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '# (a) knob map of the path-search task T1, (b) escape geometry of the random directions, (c) the screen rule,\n# (d) recomputed vs recorded Hill-1\nFAM_COLORS = {"twin": "#7f7f7f", "mention_twin": "#bdbdbd", "sham_veto": "#c5b0d5", "decoding": "#1f77b4",\n              "prompt:seed": "#17becf", "prompt:instruction": "#2ca02c", "prompt:novelty": "#98df8a",\n              "prompt:nonce": "#ff9896", "prompt:ban": "#d62728", "prompt:list": "#ff7f0e", "veto": "#9467bd",\n              "activation-random": "#e377c2", "activation-structured": "#8c564b", "activation-ban-derived": "#c49c94",\n              "generate_then_select": "#bcbd22"}\nSHORT = {"A2:seed_semantic": "semantic seed", "A2:seed_entropy": "entropy seed", "A3:instr_fully_novel": "\'fully novel\' instr.",\n         "A3:instr_new_algo": "\'new algorithm\' instr.", "A4s2:gen_then_select": "generate-then-select (ceiling)",\n         "single:bfs": "ban BFS", "multi:TOP5": "ban top-5", "multi:SCATTER": "ban SCATTER list",\n         "succession:2": "succession ban", "two_step:TWO(bfs,dfs)": "ban BFS + DFS"}\nfig, axes = plt.subplots(2, 2, figsize=(15, 12.5))\n\n# (a) every T1 cell with a depth-25 value: pass cost against the cell\'s own twin vs correct-only Hill-1\nax = axes[0, 0]\nk1 = knob[(knob.task == "T1") & knob.H1r25.notna() & knob.pass_cost_pts.notna()]\nif len(k1):\n    for fam, g in k1.groupby("family"):\n        ax.scatter(g.pass_cost_pts, g.H1r25, s=55, color=FAM_COLORS.get(fam, "k"), edgecolor="k", linewidth=0.4,\n                   alpha=0.85, zorder=3, label=f"{fam} ({len(g)})")\n    for _, r in k1[k1.arm.isin(list(SHORT))].iterrows():\n        ax.annotate(SHORT[r.arm], (r.pass_cost_pts, r.H1r25), xytext=(5, 4), textcoords="offset points", fontsize=8)\n    dec = k1[k1.family == "decoding"]\n    if len(dec):\n        ax.annotate(f"{len(dec)} temperature x sampler cells\\n(T 0.3-1.3, top-k 10 / top-p 0.95)",\n                    (dec.pass_cost_pts.mean(), dec.H1r25.mean()), xytext=(30, -45), textcoords="offset points",\n                    fontsize=8, arrowprops={"arrowstyle": "->", "lw": 0.8})\n    x0, x1 = ax.get_xlim()\n    y0, y1 = ax.get_ylim()\n    ax.fill_between([x0, 20], 2, max(y1, 2.3), color="gold", alpha=0.2, zorder=1, label="qualify: H1r25 >= 2 at <= 20 pts")\n    ax.set_xlim(x0, x1)\n    ax.set_ylim(min(y0, 0.9), max(y1, 2.3))\n    ax.legend(fontsize=7, loc="upper right")\nelse:\n    ax.text(0.5, 0.5, f"no T1 cell among the first N_CELLS = {N_CELLS}", ha="center", transform=ax.transAxes)\nn_below = int(((knob.task == "T1") & knob.H1r25.isna()).sum())\nax.set(xlabel="pass cost (points vs own twin)", ylabel="H1r25 (effective number of algorithms among 25 correct)",\n       title=f"(a) T1 path search: every knob vs its own twin\\n({len(k1)} cells; {n_below} below depth 25 not shown)")\n\n# (b) each random direction x alpha: excess off-default share over its twin vs pass rate relative to the twin\nax = axes[0, 1]\ndr = pd.DataFrame(extras["per_direction_rows"])\nif len(dr):\n    dr["excess"] = (1 - dr.n_default / dr.n_attempted) - (1 - dr.twin_n_default / dr.twin_n_attempted)\n    dr["pass_ratio"] = (dr.n_passed / dr.n) / (dr.twin_n_passed / dr.twin_n)\n    dr["escape"] = [escape_of(r)[0] for r in extras["per_direction_rows"]]\n    tcol = dict(zip(sorted(dr.task.unique()), plt.cm.tab10.colors))\n    mk = {("hf-fp8", 1.0): "o", ("hf-fp8", 2.0): "^", ("hf-bf16", 1.0): "s"}\n    for (t, eng, a), g in dr.groupby(["task", "engine", "alpha"]):\n        ax.scatter(g.excess, g.pass_ratio, s=65, marker=mk.get((eng, a), "D"), color=tcol[t],\n                   edgecolors=["k" if e else "none" for e in g.escape], linewidths=1.3, alpha=0.85, zorder=3,\n                   label=f"{t} {eng} alpha {a:g}: {int(g.escape.sum())}/{len(g)} escape")\n    x0, x1 = ax.get_xlim()\n    y0, y1 = ax.get_ylim()\n    ax.fill_between([0.20, max(x1, 0.3)], 0.8, max(y1, 1.05), color="gold", alpha=0.2, zorder=1, label="escape region")\n    ax.axvline(0.20, color="k", ls="--", lw=0.8)\n    ax.axhline(0.8, color="k", ls=":", lw=0.8)\n    ax.set_xlim(x0, max(x1, 0.3))\n    ax.set_ylim(y0, max(y1, 1.05))\n    ax.legend(fontsize=7, loc="lower right")\nax.set(xlabel="off-default share: direction minus twin", ylabel="pass rate: direction / twin",\n       title="(b) random activation directions: escape = excess >= 0.20 at pass >= 0.8 x twin\\n(black edge = escaping)")\n\n# (c) the screen rule: best escape fraction over alpha vs catalogue-only modal-ban avoidance, for all 14 tasks\nax = axes[1, 0]\n\n\ndef _emax(rec: dict) -> float:\n    return max([v for v in (rec["alpha_1"]["E_t"], rec["alpha_2"]["E_t"]) if v is not None], default=0.0)\n\n\nfor i, (t, rec) in enumerate(sorted(frozen["tasks"].items())):\n    mine = t in screen["tasks"]\n    rr = screen["tasks"][t] if mine else rec\n    col = "#d62728" if rr["movable"] else "#1f77b4"\n    ax.scatter(_emax(rr), rr["cat_only_ban_avoidance"], s=130 if mine else 70, color=col if mine else "none",\n               edgecolor=col if mine else "#7f7f7f", linewidth=1.5, zorder=3)\n    ax.annotate(t, (_emax(rr), rr["cat_only_ban_avoidance"]), xytext=(8, 8 * (i % 3 - 1) - 3), textcoords="offset points",\n                fontsize=9 if mine else 8, color="k" if mine else "#7f7f7f")\nax.axhline(0.5, color="k", ls="--", lw=0.8)\nax.fill_between([0.02, 1.05], 0.5, 1.05, color="gold", alpha=0.2, zorder=1)\nax.text(0.55, 0.53, "movable (E_t > 0) and avoidance >= 0.5", fontsize=8)\nax.set_xlim(-0.05, 1.05)\nax.set_ylim(-0.05, 1.05)\nax.legend(handles=[Line2D([], [], marker="o", ls="", color="#d62728", label="movable (recomputed here)"),\n                   Line2D([], [], marker="o", ls="", color="#1f77b4", label="immovable (recomputed here)"),\n                   Line2D([], [], marker="o", ls="", mfc="none", mec="#7f7f7f", label="frozen record (not in demo subset)")],\n          fontsize=8, loc="center right")\nax.set(xlabel="max over alpha of E_t (escaping / run)", ylabel="catalogue-only modal-ban avoidance",\n       title="(c) push screen: movable => modal-ban avoidance >= 0.5")\n\n# (d) reproduction check of the Monte-Carlo statistic\nax = axes[1, 1]\nok = np.isfinite(new.H1r25.values) & np.isfinite(old.H1r25.values)\nif ok.any():\n    ax.scatter(old.H1r25[ok], new.H1r25[ok], s=40, color="#2ca02c", edgecolor="k", linewidth=0.4, zorder=3)\n    lo = float(min(old.H1r25[ok].min(), new.H1r25[ok].min())) - 0.05\n    hi = float(max(old.H1r25[ok].max(), new.H1r25[ok].max())) + 0.05\n    ax.plot([lo, hi], [lo, hi], "k--", lw=0.8)\n    d = np.abs(new.H1r25[ok] - old.H1r25[ok])\n    ax.set_title(f"(d) recomputed vs recorded H1r25 ({int(ok.sum())} cells), max |diff| = {d.max():.2e}\\n"\n                 f"(N_RAREFY = {N_RAREFY}, N_BOOT = {N_BOOT}, N_BOOT_RAREFY = {N_BOOT_RAREFY})")\nax.set(xlabel="recorded H1r25 (artifact knob table)", ylabel="recomputed H1r25 (this notebook)")\nplt.tight_layout()\nfig.savefig(WS / "figures" / "demo_summary.png", dpi=120, bbox_inches="tight")\nplt.show()'}
```

### [72] TOOL RESULT — NotebookEdit · 2026-10-26 11:08:22 UTC

```
{"new_source": "# (a) knob map of the path-search task T1, (b) escape geometry of the random directions, (c) the screen rule,\n# (d) recomputed vs recorded Hill-1\nFAM_COLORS = {\"twin\": \"#7f7f7f\", \"mention_twin\": \"#bdbdbd\", \"sham_veto\": \"#c5b0d5\", \"decoding\": \"#1f77b4\",\n              \"prompt:seed\": \"#17becf\", \"prompt:instruction\": \"#2ca02c\", \"prompt:novelty\": \"#98df8a\",\n              \"prompt:nonce\": \"#ff9896\", \"prompt:ban\": \"#d62728\", \"prompt:list\": \"#ff7f0e\", \"veto\": \"#9467bd\",\n              \"activation-random\": \"#e377c2\", \"activation-structured\": \"#8c564b\", \"activation-ban-derived\": \"#c49c94\",\n              \"generate_then_select\": \"#bcbd22\"}\nSHORT = {\"A2:seed_semantic\": \"semantic seed\", \"A2:seed_entropy\": \"entropy seed\", \"A3:instr_fully_novel\": \"'fully novel' instr.\",\n         \"A3:instr_new_algo\": \"'new algorithm' instr.\", \"A4s2:gen_then_select\": \"generate-then-select (ceiling)\",\n         \"single:bfs\": \"ban BFS\", \"multi:TOP5\": \"ban top-5\", \"multi:SCATTER\": \"ban SCATTER list\",\n         \"succession:2\": \"succession ban\", \"two_step:TWO(bfs,dfs)\": \"ban BFS + DFS\"}\nfig, axes = plt.subplots(2, 2, figsize=(15, 12.5))\n\n# (a) every T1 cell with a depth-25 value: pass cost against the cell's own twin vs correct-only Hill-1\nax = axes[0, 0]\nk1 = knob[(knob.task == \"T1\") & knob.H1r25.notna() & knob.pass_cost_pts.notna()]\nif len(k1):\n    for fam, g in k1.groupby(\"family\"):\n        ax.scatter(g.pass_cost_pts, g.H1r25, s=55, color=FAM_COLORS.get(fam, \"k\"), edgecolor=\"k\", linewidth=0.4,\n                   alpha=0.85, zorder=3, label=f\"{fam} ({len(g)})\")\n    for _, r in k1[k1.arm.isin(list(SHORT))].iterrows():\n        ax.annotate(SHORT[r.arm], (r.pass_cost_pts, r.H1r25), xytext=(5, 4), textcoords=\"offset points\", fontsize=8)\n    dec = k1[k1.family == \"decoding\"]\n    if len(dec):\n        ax.annotate(f\"{len(dec)} temperature x sampler cells\\n(T 0.3-1.3, top-k 10 / top-p 0.95)\",\n                    (dec.pass_cost_pts.mean(), dec.H1r25.mean()), xytext=(30, -45), textcoords=\"offset points\",\n                    fontsize=8, arrowprops={\"arrowstyle\": \"->\", \"lw\": 0.8})\n    x0, x1 = ax.get_xlim()\n    y0, y1 = ax.get_ylim()\n    ax.fill_between([x0, 20], 2, max(y1, 2.3), color=\"gold\", alpha=0.2, zorder=1, label=\"qualify: H1r25 >= 2 at <= 20 pts\")\n    ax.set_xlim(x0, x1)\n    ax.set_ylim(min(y0, 0.9), max(y1, 2.3))\n    ax.legend(fontsize=7, loc=\"upper right\")\nelse:\n    ax.text(0.5, 0.5, f\"no T1 cell among the first N_CELLS = {N_CELLS}\", ha=\"center\", transform=ax.transAxes)\nn_below = int(((knob.task == \"T1\") & knob.H1r25.isna()).sum())\nax.set(xlabel=\"pass cost (points vs own twin)\", ylabel=\"H1r25 (effective number of algorithms among 25 correct)\",\n       title=f\"(a) T1 path search: every knob vs its own twin\\n({len(k1)} cells; {n_below} below depth 25 not shown)\")\n\n# (b) each random direction x alpha: excess off-default share over its twin vs pass rate relative to the twin\nax = axes[0, 1]\ndr = pd.DataFrame(extras[\"per_direction_rows\"])\nif len(dr):\n    dr[\"excess\"] = (1 - dr.n_default / dr.n_attempted) - (1 - dr.twin_n_default / dr.twin_n_attempted)\n    dr[\"pass_ratio\"] = (dr.n_passed / dr.n) / (dr.twin_n_passed / dr.twin_n)\n    dr[\"escape\"] = [escape_of(r)[0] for r in extras[\"per_direction_rows\"]]\n    tcol = dict(zip(sorted(dr.task.unique()), plt.cm.tab10.colors))\n    mk = {(\"hf-fp8\", 1.0): \"o\", (\"hf-fp8\", 2.0): \"^\", (\"hf-bf16\", 1.0): \"s\"}\n    for (t, eng, a), g in dr.groupby([\"task\", \"engine\", \"alpha\"]):\n        ax.scatter(g.excess, g.pass_ratio, s=65, marker=mk.get((eng, a), \"D\"), color=tcol[t],\n                   edgecolors=[\"k\" if e else \"none\" for e in g.escape], linewidths=1.3, alpha=0.85, zorder=3,\n                   label=f\"{t} {eng} alpha {a:g}: {int(g.escape.sum())}/{len(g)} escape\")\n    x0, x1 = ax.get_xlim()\n    y0, y1 = ax.get_ylim()\n    ax.fill_between([0.20, max(x1, 0.3)], 0.8, max(y1, 1.05), color=\"gold\", alpha=0.2, zorder=1, label=\"escape region\")\n    ax.axvline(0.20, color=\"k\", ls=\"--\", lw=0.8)\n    ax.axhline(0.8, color=\"k\", ls=\":\", lw=0.8)\n    ax.set_xlim(x0, max(x1, 0.3))\n    ax.set_ylim(y0, max(y1, 1.05))\n    ax.legend(fontsize=7, loc=\"lower right\")\nax.set(xlabel=\"off-default share: direction minus twin\", ylabel=\"pass rate: direction / twin\",\n       title=\"(b) random activation directions: escape = excess >= 0.20 at pass >= 0.8 x twin\\n(black edge = escaping)\")\n\n# (c) the screen rule: best escape fraction over alpha vs catalogue-only modal-ban avoidance, for all 14 tasks\nax = axes[1, 0]\n\n\ndef _emax(rec: dict) -> float:\n    return max([v for v in (rec[\"alpha_1\"][\"E_t\"], rec[\"alpha_2\"][\"E_t\"]) if v is not None], default=0.0)\n\n\nfor i, (t, rec) in enumerate(sorted(frozen[\"tasks\"].items())):\n    mine = t in screen[\"tasks\"]\n    rr = screen[\"tasks\"][t] if mine else rec\n    col = \"#d62728\" if rr[\"movable\"] else \"#1f77b4\"\n    ax.scatter(_emax(rr), rr[\"cat_only_ban_avoidance\"], s=130 if mine else 70, color=col if mine else \"none\",\n               edgecolor=col if mine else \"#7f7f7f\", linewidth=1.5, zorder=3)\n    ax.annotate(t, (_emax(rr), rr[\"cat_only_ban_avoidance\"]), xytext=(8, 8 * (i % 3 - 1) - 3), textcoords=\"offset points\",\n                fontsize=9 if mine else 8, color=\"k\" if mine else \"#7f7f7f\")\nax.axhline(0.5, color=\"k\", ls=\"--\", lw=0.8)\nax.fill_between([0.02, 1.05], 0.5, 1.05, color=\"gold\", alpha=0.2, zorder=1)\nax.text(0.55, 0.53, \"movable (E_t > 0) and avoidance >= 0.5\", fontsize=8)\nax.set_xlim(-0.05, 1.05)\nax.set_ylim(-0.05, 1.05)\nax.legend(handles=[Line2D([], [], marker=\"o\", ls=\"\", color=\"#d62728\", label=\"movable (recomputed here)\"),\n                   Line2D([], [], marker=\"o\", ls=\"\", color=\"#1f77b4\", label=\"immovable (recomputed here)\"),\n                   Line2D([], [], marker=\"o\", ls=\"\", mfc=\"none\", mec=\"#7f7f7f\", label=\"frozen record (not in demo subset)\")],\n          fontsize=8, loc=\"center right\")\nax.set(xlabel=\"max over alpha of E_t (escaping / run)\", ylabel=\"catalogue-only modal-ban avoidance\",\n       title=\"(c) push screen: movable => modal-ban avoidance >= 0.5\")\n\n# (d) reproduction check of the Monte-Carlo statistic\nax = axes[1, 1]\nok = np.isfinite(new.H1r25.values) & np.isfinite(old.H1r25.values)\nif ok.any():\n    ax.scatter(old.H1r25[ok], new.H1r25[ok], s=40, color=\"#2ca02c\", edgecolor=\"k\", linewidth=0.4, zorder=3)\n    lo = float(min(old.H1r25[ok].min(), new.H1r25[ok].min())) - 0.05\n    hi = float(max(old.H1r25[ok].max(), new.H1r25[ok].max())) + 0.05\n    ax.plot([lo, hi], [lo, hi], \"k--\", lw=0.8)\n    d = np.abs(new.H1r25[ok] - old.H1r25[ok])\n    ax.set_title(f\"(d) recomputed vs recorded H1r25 ({int(ok.sum())} cells), max |diff| = {d.max():.2e}\\n\"\n                 f\"(N_RAREFY = {N_RAREFY}, N_BOOT = {N_BOOT}, N_BOOT_RAREFY = {N_BOOT_RAREFY})\")\nax.set(xlabel=\"recorded H1r25 (artifact knob table)\", ylabel=\"recomputed H1r25 (this notebook)\")\nplt.tight_layout()\nfig.savefig(WS / \"figures\" / \"demo_summary.png\", dpi=120, bbox_inches=\"tight\")\nplt.show()", "cell_type": "code", "language": "python", "edit_mode": "insert", "cell_id": "1c8d802c", "error": "", "notebook_path": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb", "original_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"summary\",\n   \"metadata\": {},\n   \"source\": [\n    \"## Summary and scaling\\n\",\n    \"\\n\",\n    \"The config cell controls the run size. To reproduce the artifact's numbers exactly, set `N_RAREFY = 1000`, `N_BOOT = 1000`, `N_BOOT_RAREFY = 200` and `N_CELLS = 99` and run all cells.\"\n   ]\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}\n", "updated_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"1c8d802c\",\n   \"source\": \"# (a) knob map of the path-search task T1, (b) escape geometry of the random directions, (c) the screen rule,\\n# (d) recomputed vs recorded Hill-1\\nFAM_COLORS = {\\\"twin\\\": \\\"#7f7f7f\\\", \\\"mention_twin\\\": \\\"#bdbdbd\\\", \\\"sham_veto\\\": \\\"#c5b0d5\\\", \\\"decoding\\\": \\\"#1f77b4\\\",\\n              \\\"prompt:seed\\\": \\\"#17becf\\\", \\\"prompt:instruction\\\": \\\"#2ca02c\\\", \\\"prompt:novelty\\\": \\\"#98df8a\\\",\\n              \\\"prompt:nonce\\\": \\\"#ff9896\\\", \\\"prompt:ban\\\": \\\"#d62728\\\", \\\"prompt:list\\\": \\\"#ff7f0e\\\", \\\"veto\\\": \\\"#9467bd\\\",\\n              \\\"activation-random\\\": \\\"#e377c2\\\", \\\"activation-structured\\\": \\\"#8c564b\\\", \\\"activation-ban-derived\\\": \\\"#c49c94\\\",\\n              \\\"generate_then_select\\\": \\\"#bcbd22\\\"}\\nSHORT = {\\\"A2:seed_semantic\\\": \\\"semantic seed\\\", \\\"A2:seed_entropy\\\": \\\"entropy seed\\\", \\\"A3:instr_fully_novel\\\": \\\"'fully novel' instr.\\\",\\n         \\\"A3:instr_new_algo\\\": \\\"'new algorithm' instr.\\\", \\\"A4s2:gen_then_select\\\": \\\"generate-then-select (ceiling)\\\",\\n         \\\"single:bfs\\\": \\\"ban BFS\\\", \\\"multi:TOP5\\\": \\\"ban top-5\\\", \\\"multi:SCATTER\\\": \\\"ban SCATTER list\\\",\\n         \\\"succession:2\\\": \\\"succession ban\\\", \\\"two_step:TWO(bfs,dfs)\\\": \\\"ban BFS + DFS\\\"}\\nfig, axes = plt.subplots(2, 2, figsize=(15, 12.5))\\n\\n# (a) every T1 cell with a depth-25 value: pass cost against the cell's own twin vs correct-only Hill-1\\nax = axes[0, 0]\\nk1 = knob[(knob.task == \\\"T1\\\") & knob.H1r25.notna() & knob.pass_cost_pts.notna()]\\nif len(k1):\\n    for fam, g in k1.groupby(\\\"family\\\"):\\n        ax.scatter(g.pass_cost_pts, g.H1r25, s=55, color=FAM_COLORS.get(fam, \\\"k\\\"), edgecolor=\\\"k\\\", linewidth=0.4,\\n                   alpha=0.85, zorder=3, label=f\\\"{fam} ({len(g)})\\\")\\n    for _, r in k1[k1.arm.isin(list(SHORT))].iterrows():\\n        ax.annotate(SHORT[r.arm], (r.pass_cost_pts, r.H1r25), xytext=(5, 4), textcoords=\\\"offset points\\\", fontsize=8)\\n    dec = k1[k1.family == \\\"decoding\\\"]\\n    if len(dec):\\n        ax.annotate(f\\\"{len(dec)} temperature x sampler cells\\\\n(T 0.3-1.3, top-k 10 / top-p 0.95)\\\",\\n                    (dec.pass_cost_pts.mean(), dec.H1r25.mean()), xytext=(30, -45), textcoords=\\\"offset points\\\",\\n                    fontsize=8, arrowprops={\\\"arrowstyle\\\": \\\"->\\\", \\\"lw\\\": 0.8})\\n    x0, x1 = ax.get_xlim()\\n    y0, y1 = ax.get_ylim()\\n    ax.fill_between([x0, 20], 2, max(y1, 2.3), color=\\\"gold\\\", alpha=0.2, zorder=1, label=\\\"qualify: H1r25 >= 2 at <= 20 pts\\\")\\n    ax.set_xlim(x0, x1)\\n    ax.set_ylim(min(y0, 0.9), max(y1, 2.3))\\n    ax.legend(fontsize=7, loc=\\\"upper right\\\")\\nelse:\\n    ax.text(0.5, 0.5, f\\\"no T1 cell among the first N_CELLS = {N_CELLS}\\\", ha=\\\"center\\\", transform=ax.transAxes)\\nn_below = int(((knob.task == \\\"T1\\\") & knob.H1r25.isna()).sum())\\nax.set(xlabel=\\\"pass cost (points vs own twin)\\\", ylabel=\\\"H1r25 (effective number of algorithms among 25 correct)\\\",\\n       title=f\\\"(a) T1 path search: every knob vs its own twin\\\\n({len(k1)} cells; {n_below} below depth 25 not shown)\\\")\\n\\n# (b) each random direction x alpha: excess off-default share over its twin vs pass rate relative to the twin\\nax = axes[0, 1]\\ndr = pd.DataFrame(extras[\\\"per_direction_rows\\\"])\\nif len(dr):\\n    dr[\\\"excess\\\"] = (1 - dr.n_default / dr.n_attempted) - (1 - dr.twin_n_default / dr.twin_n_attempted)\\n    dr[\\\"pass_ratio\\\"] = (dr.n_passed / dr.n) / (dr.twin_n_passed / dr.twin_n)\\n    dr[\\\"escape\\\"] = [escape_of(r)[0] for r in extras[\\\"per_direction_rows\\\"]]\\n    tcol = dict(zip(sorted(dr.task.unique()), plt.cm.tab10.colors))\\n    mk = {(\\\"hf-fp8\\\", 1.0): \\\"o\\\", (\\\"hf-fp8\\\", 2.0): \\\"^\\\", (\\\"hf-bf16\\\", 1.0): \\\"s\\\"}\\n    for (t, eng, a), g in dr.groupby([\\\"task\\\", \\\"engine\\\", \\\"alpha\\\"]):\\n        ax.scatter(g.excess, g.pass_ratio, s=65, marker=mk.get((eng, a), \\\"D\\\"), color=tcol[t],\\n                   edgecolors=[\\\"k\\\" if e else \\\"none\\\" for e in g.escape], linewidths=1.3, alpha=0.85, zorder=3,\\n                   label=f\\\"{t} {eng} alpha {a:g}: {int(g.escape.sum())}/{len(g)} escape\\\")\\n    x0, x1 = ax.get_xlim()\\n    y0, y1 = ax.get_ylim()\\n    ax.fill_between([0.20, max(x1, 0.3)], 0.8, max(y1, 1.05), color=\\\"gold\\\", alpha=0.2, zorder=1, label=\\\"escape region\\\")\\n    ax.axvline(0.20, color=\\\"k\\\", ls=\\\"--\\\", lw=0.8)\\n    ax.axhline(0.8, color=\\\"k\\\", ls=\\\":\\\", lw=0.8)\\n    ax.set_xlim(x0, max(x1, 0.3))\\n    ax.set_ylim(y0, max(y1, 1.05))\\n    ax.legend(fontsize=7, loc=\\\"lower right\\\")\\nax.set(xlabel=\\\"off-default share: direction minus twin\\\", ylabel=\\\"pass rate: direction / twin\\\",\\n       title=\\\"(b) random activation directions: escape = excess >= 0.20 at pass >= 0.8 x twin\\\\n(black edge = escaping)\\\")\\n\\n# (c) the screen rule: best escape fraction over alpha vs catalogue-only modal-ban avoidance, for all 14 tasks\\nax = axes[1, 0]\\n\\n\\ndef _emax(rec: dict) -> float:\\n    return max([v for v in (rec[\\\"alpha_1\\\"][\\\"E_t\\\"], rec[\\\"alpha_2\\\"][\\\"E_t\\\"]) if v is not None], default=0.0)\\n\\n\\nfor i, (t, rec) in enumerate(sorted(frozen[\\\"tasks\\\"].items())):\\n    mine = t in screen[\\\"tasks\\\"]\\n    rr = screen[\\\"tasks\\\"][t] if mine else rec\\n    col = \\\"#d62728\\\" if rr[\\\"movable\\\"] else \\\"#1f77b4\\\"\\n    ax.scatter(_emax(rr), rr[\\\"cat_only_ban_avoidance\\\"], s=130 if mine else 70, color=col if mine else \\\"none\\\",\\n               edgecolor=col if mine else \\\"#7f7f7f\\\", linewidth=1.5, zorder=3)\\n    ax.annotate(t, (_emax(rr), rr[\\\"cat_only_ban_avoidance\\\"]), xytext=(8, 8 * (i % 3 - 1) - 3), textcoords=\\\"offset points\\\",\\n                fontsize=9 if mine else 8, color=\\\"k\\\" if mine else \\\"#7f7f7f\\\")\\nax.axhline(0.5, color=\\\"k\\\", ls=\\\"--\\\", lw=0.8)\\nax.fill_between([0.02, 1.05], 0.5, 1.05, color=\\\"gold\\\", alpha=0.2, zorder=1)\\nax.text(0.55, 0.53, \\\"movable (E_t > 0) and avoidance >= 0.5\\\", fontsize=8)\\nax.set_xlim(-0.05, 1.05)\\nax.set_ylim(-0.05, 1.05)\\nax.legend(handles=[Line2D([], [], marker=\\\"o\\\", ls=\\\"\\\", color=\\\"#d62728\\\", label=\\\"movable (recomputed here)\\\"),\\n                   Line2D([], [], marker=\\\"o\\\", ls=\\\"\\\", color=\\\"#1f77b4\\\", label=\\\"immovable (recomputed here)\\\"),\\n                   Line2D([], [], marker=\\\"o\\\", ls=\\\"\\\", mfc=\\\"none\\\", mec=\\\"#7f7f7f\\\", label=\\\"frozen record (not in demo subset)\\\")],\\n          fontsize=8, loc=\\\"center right\\\")\\nax.set(xlabel=\\\"max over alpha of E_t (escaping / run)\\\", ylabel=\\\"catalogue-only modal-ban avoidance\\\",\\n       title=\\\"(c) push screen: movable => modal-ban avoidance >= 0.5\\\")\\n\\n# (d) reproduction check of the Monte-Carlo statistic\\nax = axes[1, 1]\\nok = np.isfinite(new.H1r25.values) & np.isfinite(old.H1r25.values)\\nif ok.any():\\n    ax.scatter(old.H1r25[ok], new.H1r25[ok], s=40, color=\\\"#2ca02c\\\", edgecolor=\\\"k\\\", linewidth=0.4, zorder=3)\\n    lo = float(min(old.H1r25[ok].min(), new.H1r25[ok].min())) - 0.05\\n    hi = float(max(old.H1r25[ok].max(), new.H1r25[ok].max())) + 0.05\\n    ax.plot([lo, hi], [lo, hi], \\\"k--\\\", lw=0.8)\\n    d = np.abs(new.H1r25[ok] - old.H1r25[ok])\\n    ax.set_title(f\\\"(d) recomputed vs recorded H1r25 ({int(ok.sum())} cells), max |diff| = {d.max():.2e}\\\\n\\\"\\n                 f\\\"(N_RAREFY = {N_RAREFY}, N_BOOT = {N_BOOT}, N_BOOT_RAREFY = {N_BOOT_RAREFY})\\\")\\nax.set(xlabel=\\\"recorded H1r25 (artifact knob table)\\\", ylabel=\\\"recomputed H1r25 (this notebook)\\\")\\nplt.tight_layout()\\nfig.savefig(WS / \\\"figures\\\" / \\\"demo_summary.png\\\", dpi=120, bbox_inches=\\\"tight\\\")\\nplt.show()\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"summary\",\n   \"metadata\": {},\n   \"source\": [\n    \"## Summary and scaling\\n\",\n    \"\\n\",\n    \"The config cell controls the run size. To reproduce the artifact's numbers exactly, set `N_RAREFY = 1000`, `N_BOOT = 1000`, `N_BOOT_RAREFY = 200` and `N_CELLS = 99` and run all cells.\"\n   ]\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}"}
```

### [73] TOOL CALL — NotebookEdit · 2026-10-26 11:08:40 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "## Visualization\n\n- **(a)** The knob map of the path-search task T1: each cell's pass cost against its own twin (x) against its correct-only Hill-1 (y). The gold box is the *qualify* region (Hill-1 ≥ 2 at a cost of at most 20 points): two equally common correct algorithms without losing more than 20 points of pass rate.\n- **(b)** The escape rule in its own coordinates: each random direction × α is one point. The x-axis is how much it raises the off-default share over its twin, and the y-axis is its pass rate relative to the twin. Escaping directions (gold region) have a black edge.\n- **(c)** The screen rule over all 14 tasks. Filled markers were recomputed here, and hollow markers are the frozen records of tasks outside the demo subset.\n- **(d)** Recomputed against recorded `H1r25` for every demo cell."}
```

### [74] TOOL RESULT — NotebookEdit · 2026-10-26 11:08:40 UTC

```
{"new_source": "## Visualization\n\n- **(a)** The knob map of the path-search task T1: each cell's pass cost against its own twin (x) against its correct-only Hill-1 (y). The gold box is the *qualify* region (Hill-1 ≥ 2 at a cost of at most 20 points): two equally common correct algorithms without losing more than 20 points of pass rate.\n- **(b)** The escape rule in its own coordinates: each random direction × α is one point. The x-axis is how much it raises the off-default share over its twin, and the y-axis is its pass rate relative to the twin. Escaping directions (gold region) have a black edge.\n- **(c)** The screen rule over all 14 tasks. Filled markers were recomputed here, and hollow markers are the frozen records of tasks outside the demo subset.\n- **(d)** Recomputed against recorded `H1r25` for every demo cell.", "cell_type": "markdown", "language": "python", "edit_mode": "insert", "cell_id": "9b595dbb", "error": "", "notebook_path": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb", "original_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"1c8d802c\",\n   \"source\": \"# (a) knob map of the path-search task T1, (b) escape geometry of the random directions, (c) the screen rule,\\n# (d) recomputed vs recorded Hill-1\\nFAM_COLORS = {\\\"twin\\\": \\\"#7f7f7f\\\", \\\"mention_twin\\\": \\\"#bdbdbd\\\", \\\"sham_veto\\\": \\\"#c5b0d5\\\", \\\"decoding\\\": \\\"#1f77b4\\\",\\n              \\\"prompt:seed\\\": \\\"#17becf\\\", \\\"prompt:instruction\\\": \\\"#2ca02c\\\", \\\"prompt:novelty\\\": \\\"#98df8a\\\",\\n              \\\"prompt:nonce\\\": \\\"#ff9896\\\", \\\"prompt:ban\\\": \\\"#d62728\\\", \\\"prompt:list\\\": \\\"#ff7f0e\\\", \\\"veto\\\": \\\"#9467bd\\\",\\n              \\\"activation-random\\\": \\\"#e377c2\\\", \\\"activation-structured\\\": \\\"#8c564b\\\", \\\"activation-ban-derived\\\": \\\"#c49c94\\\",\\n              \\\"generate_then_select\\\": \\\"#bcbd22\\\"}\\nSHORT = {\\\"A2:seed_semantic\\\": \\\"semantic seed\\\", \\\"A2:seed_entropy\\\": \\\"entropy seed\\\", \\\"A3:instr_fully_novel\\\": \\\"'fully novel' instr.\\\",\\n         \\\"A3:instr_new_algo\\\": \\\"'new algorithm' instr.\\\", \\\"A4s2:gen_then_select\\\": \\\"generate-then-select (ceiling)\\\",\\n         \\\"single:bfs\\\": \\\"ban BFS\\\", \\\"multi:TOP5\\\": \\\"ban top-5\\\", \\\"multi:SCATTER\\\": \\\"ban SCATTER list\\\",\\n         \\\"succession:2\\\": \\\"succession ban\\\", \\\"two_step:TWO(bfs,dfs)\\\": \\\"ban BFS + DFS\\\"}\\nfig, axes = plt.subplots(2, 2, figsize=(15, 12.5))\\n\\n# (a) every T1 cell with a depth-25 value: pass cost against the cell's own twin vs correct-only Hill-1\\nax = axes[0, 0]\\nk1 = knob[(knob.task == \\\"T1\\\") & knob.H1r25.notna() & knob.pass_cost_pts.notna()]\\nif len(k1):\\n    for fam, g in k1.groupby(\\\"family\\\"):\\n        ax.scatter(g.pass_cost_pts, g.H1r25, s=55, color=FAM_COLORS.get(fam, \\\"k\\\"), edgecolor=\\\"k\\\", linewidth=0.4,\\n                   alpha=0.85, zorder=3, label=f\\\"{fam} ({len(g)})\\\")\\n    for _, r in k1[k1.arm.isin(list(SHORT))].iterrows():\\n        ax.annotate(SHORT[r.arm], (r.pass_cost_pts, r.H1r25), xytext=(5, 4), textcoords=\\\"offset points\\\", fontsize=8)\\n    dec = k1[k1.family == \\\"decoding\\\"]\\n    if len(dec):\\n        ax.annotate(f\\\"{len(dec)} temperature x sampler cells\\\\n(T 0.3-1.3, top-k 10 / top-p 0.95)\\\",\\n                    (dec.pass_cost_pts.mean(), dec.H1r25.mean()), xytext=(30, -45), textcoords=\\\"offset points\\\",\\n                    fontsize=8, arrowprops={\\\"arrowstyle\\\": \\\"->\\\", \\\"lw\\\": 0.8})\\n    x0, x1 = ax.get_xlim()\\n    y0, y1 = ax.get_ylim()\\n    ax.fill_between([x0, 20], 2, max(y1, 2.3), color=\\\"gold\\\", alpha=0.2, zorder=1, label=\\\"qualify: H1r25 >= 2 at <= 20 pts\\\")\\n    ax.set_xlim(x0, x1)\\n    ax.set_ylim(min(y0, 0.9), max(y1, 2.3))\\n    ax.legend(fontsize=7, loc=\\\"upper right\\\")\\nelse:\\n    ax.text(0.5, 0.5, f\\\"no T1 cell among the first N_CELLS = {N_CELLS}\\\", ha=\\\"center\\\", transform=ax.transAxes)\\nn_below = int(((knob.task == \\\"T1\\\") & knob.H1r25.isna()).sum())\\nax.set(xlabel=\\\"pass cost (points vs own twin)\\\", ylabel=\\\"H1r25 (effective number of algorithms among 25 correct)\\\",\\n       title=f\\\"(a) T1 path search: every knob vs its own twin\\\\n({len(k1)} cells; {n_below} below depth 25 not shown)\\\")\\n\\n# (b) each random direction x alpha: excess off-default share over its twin vs pass rate relative to the twin\\nax = axes[0, 1]\\ndr = pd.DataFrame(extras[\\\"per_direction_rows\\\"])\\nif len(dr):\\n    dr[\\\"excess\\\"] = (1 - dr.n_default / dr.n_attempted) - (1 - dr.twin_n_default / dr.twin_n_attempted)\\n    dr[\\\"pass_ratio\\\"] = (dr.n_passed / dr.n) / (dr.twin_n_passed / dr.twin_n)\\n    dr[\\\"escape\\\"] = [escape_of(r)[0] for r in extras[\\\"per_direction_rows\\\"]]\\n    tcol = dict(zip(sorted(dr.task.unique()), plt.cm.tab10.colors))\\n    mk = {(\\\"hf-fp8\\\", 1.0): \\\"o\\\", (\\\"hf-fp8\\\", 2.0): \\\"^\\\", (\\\"hf-bf16\\\", 1.0): \\\"s\\\"}\\n    for (t, eng, a), g in dr.groupby([\\\"task\\\", \\\"engine\\\", \\\"alpha\\\"]):\\n        ax.scatter(g.excess, g.pass_ratio, s=65, marker=mk.get((eng, a), \\\"D\\\"), color=tcol[t],\\n                   edgecolors=[\\\"k\\\" if e else \\\"none\\\" for e in g.escape], linewidths=1.3, alpha=0.85, zorder=3,\\n                   label=f\\\"{t} {eng} alpha {a:g}: {int(g.escape.sum())}/{len(g)} escape\\\")\\n    x0, x1 = ax.get_xlim()\\n    y0, y1 = ax.get_ylim()\\n    ax.fill_between([0.20, max(x1, 0.3)], 0.8, max(y1, 1.05), color=\\\"gold\\\", alpha=0.2, zorder=1, label=\\\"escape region\\\")\\n    ax.axvline(0.20, color=\\\"k\\\", ls=\\\"--\\\", lw=0.8)\\n    ax.axhline(0.8, color=\\\"k\\\", ls=\\\":\\\", lw=0.8)\\n    ax.set_xlim(x0, max(x1, 0.3))\\n    ax.set_ylim(y0, max(y1, 1.05))\\n    ax.legend(fontsize=7, loc=\\\"lower right\\\")\\nax.set(xlabel=\\\"off-default share: direction minus twin\\\", ylabel=\\\"pass rate: direction / twin\\\",\\n       title=\\\"(b) random activation directions: escape = excess >= 0.20 at pass >= 0.8 x twin\\\\n(black edge = escaping)\\\")\\n\\n# (c) the screen rule: best escape fraction over alpha vs catalogue-only modal-ban avoidance, for all 14 tasks\\nax = axes[1, 0]\\n\\n\\ndef _emax(rec: dict) -> float:\\n    return max([v for v in (rec[\\\"alpha_1\\\"][\\\"E_t\\\"], rec[\\\"alpha_2\\\"][\\\"E_t\\\"]) if v is not None], default=0.0)\\n\\n\\nfor i, (t, rec) in enumerate(sorted(frozen[\\\"tasks\\\"].items())):\\n    mine = t in screen[\\\"tasks\\\"]\\n    rr = screen[\\\"tasks\\\"][t] if mine else rec\\n    col = \\\"#d62728\\\" if rr[\\\"movable\\\"] else \\\"#1f77b4\\\"\\n    ax.scatter(_emax(rr), rr[\\\"cat_only_ban_avoidance\\\"], s=130 if mine else 70, color=col if mine else \\\"none\\\",\\n               edgecolor=col if mine else \\\"#7f7f7f\\\", linewidth=1.5, zorder=3)\\n    ax.annotate(t, (_emax(rr), rr[\\\"cat_only_ban_avoidance\\\"]), xytext=(8, 8 * (i % 3 - 1) - 3), textcoords=\\\"offset points\\\",\\n                fontsize=9 if mine else 8, color=\\\"k\\\" if mine else \\\"#7f7f7f\\\")\\nax.axhline(0.5, color=\\\"k\\\", ls=\\\"--\\\", lw=0.8)\\nax.fill_between([0.02, 1.05], 0.5, 1.05, color=\\\"gold\\\", alpha=0.2, zorder=1)\\nax.text(0.55, 0.53, \\\"movable (E_t > 0) and avoidance >= 0.5\\\", fontsize=8)\\nax.set_xlim(-0.05, 1.05)\\nax.set_ylim(-0.05, 1.05)\\nax.legend(handles=[Line2D([], [], marker=\\\"o\\\", ls=\\\"\\\", color=\\\"#d62728\\\", label=\\\"movable (recomputed here)\\\"),\\n                   Line2D([], [], marker=\\\"o\\\", ls=\\\"\\\", color=\\\"#1f77b4\\\", label=\\\"immovable (recomputed here)\\\"),\\n                   Line2D([], [], marker=\\\"o\\\", ls=\\\"\\\", mfc=\\\"none\\\", mec=\\\"#7f7f7f\\\", label=\\\"frozen record (not in demo subset)\\\")],\\n          fontsize=8, loc=\\\"center right\\\")\\nax.set(xlabel=\\\"max over alpha of E_t (escaping / run)\\\", ylabel=\\\"catalogue-only modal-ban avoidance\\\",\\n       title=\\\"(c) push screen: movable => modal-ban avoidance >= 0.5\\\")\\n\\n# (d) reproduction check of the Monte-Carlo statistic\\nax = axes[1, 1]\\nok = np.isfinite(new.H1r25.values) & np.isfinite(old.H1r25.values)\\nif ok.any():\\n    ax.scatter(old.H1r25[ok], new.H1r25[ok], s=40, color=\\\"#2ca02c\\\", edgecolor=\\\"k\\\", linewidth=0.4, zorder=3)\\n    lo = float(min(old.H1r25[ok].min(), new.H1r25[ok].min())) - 0.05\\n    hi = float(max(old.H1r25[ok].max(), new.H1r25[ok].max())) + 0.05\\n    ax.plot([lo, hi], [lo, hi], \\\"k--\\\", lw=0.8)\\n    d = np.abs(new.H1r25[ok] - old.H1r25[ok])\\n    ax.set_title(f\\\"(d) recomputed vs recorded H1r25 ({int(ok.sum())} cells), max |diff| = {d.max():.2e}\\\\n\\\"\\n                 f\\\"(N_RAREFY = {N_RAREFY}, N_BOOT = {N_BOOT}, N_BOOT_RAREFY = {N_BOOT_RAREFY})\\\")\\nax.set(xlabel=\\\"recorded H1r25 (artifact knob table)\\\", ylabel=\\\"recomputed H1r25 (this notebook)\\\")\\nplt.tight_layout()\\nfig.savefig(WS / \\\"figures\\\" / \\\"demo_summary.png\\\", dpi=120, bbox_inches=\\\"tight\\\")\\nplt.show()\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"summary\",\n   \"metadata\": {},\n   \"source\": [\n    \"## Summary and scaling\\n\",\n    \"\\n\",\n    \"The config cell controls the run size. To reproduce the artifact's numbers exactly, set `N_RAREFY = 1000`, `N_BOOT = 1000`, `N_BOOT_RAREFY = 200` and `N_CELLS = 99` and run all cells.\"\n   ]\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}", "updated_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"9b595dbb\",\n   \"source\": \"## Visualization\\n\\n- **(a)** The knob map of the path-search task T1: each cell's pass cost against its own twin (x) against its correct-only Hill-1 (y). The gold box is the *qualify* region (Hill-1 ≥ 2 at a cost of at most 20 points): two equally common correct algorithms without losing more than 20 points of pass rate.\\n- **(b)** The escape rule in its own coordinates: each random direction × α is one point. The x-axis is how much it raises the off-default share over its twin, and the y-axis is its pass rate relative to the twin. Escaping directions (gold region) have a black edge.\\n- **(c)** The screen rule over all 14 tasks. Filled markers were recomputed here, and hollow markers are the frozen records of tasks outside the demo subset.\\n- **(d)** Recomputed against recorded `H1r25` for every demo cell.\",\n   \"metadata\": {}\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"1c8d802c\",\n   \"source\": \"# (a) knob map of the path-search task T1, (b) escape geometry of the random directions, (c) the screen rule,\\n# (d) recomputed vs recorded Hill-1\\nFAM_COLORS = {\\\"twin\\\": \\\"#7f7f7f\\\", \\\"mention_twin\\\": \\\"#bdbdbd\\\", \\\"sham_veto\\\": \\\"#c5b0d5\\\", \\\"decoding\\\": \\\"#1f77b4\\\",\\n              \\\"prompt:seed\\\": \\\"#17becf\\\", \\\"prompt:instruction\\\": \\\"#2ca02c\\\", \\\"prompt:novelty\\\": \\\"#98df8a\\\",\\n              \\\"prompt:nonce\\\": \\\"#ff9896\\\", \\\"prompt:ban\\\": \\\"#d62728\\\", \\\"prompt:list\\\": \\\"#ff7f0e\\\", \\\"veto\\\": \\\"#9467bd\\\",\\n              \\\"activation-random\\\": \\\"#e377c2\\\", \\\"activation-structured\\\": \\\"#8c564b\\\", \\\"activation-ban-derived\\\": \\\"#c49c94\\\",\\n              \\\"generate_then_select\\\": \\\"#bcbd22\\\"}\\nSHORT = {\\\"A2:seed_semantic\\\": \\\"semantic seed\\\", \\\"A2:seed_entropy\\\": \\\"entropy seed\\\", \\\"A3:instr_fully_novel\\\": \\\"'fully novel' instr.\\\",\\n         \\\"A3:instr_new_algo\\\": \\\"'new algorithm' instr.\\\", \\\"A4s2:gen_then_select\\\": \\\"generate-then-select (ceiling)\\\",\\n         \\\"single:bfs\\\": \\\"ban BFS\\\", \\\"multi:TOP5\\\": \\\"ban top-5\\\", \\\"multi:SCATTER\\\": \\\"ban SCATTER list\\\",\\n         \\\"succession:2\\\": \\\"succession ban\\\", \\\"two_step:TWO(bfs,dfs)\\\": \\\"ban BFS + DFS\\\"}\\nfig, axes = plt.subplots(2, 2, figsize=(15, 12.5))\\n\\n# (a) every T1 cell with a depth-25 value: pass cost against the cell's own twin vs correct-only Hill-1\\nax = axes[0, 0]\\nk1 = knob[(knob.task == \\\"T1\\\") & knob.H1r25.notna() & knob.pass_cost_pts.notna()]\\nif len(k1):\\n    for fam, g in k1.groupby(\\\"family\\\"):\\n        ax.scatter(g.pass_cost_pts, g.H1r25, s=55, color=FAM_COLORS.get(fam, \\\"k\\\"), edgecolor=\\\"k\\\", linewidth=0.4,\\n                   alpha=0.85, zorder=3, label=f\\\"{fam} ({len(g)})\\\")\\n    for _, r in k1[k1.arm.isin(list(SHORT))].iterrows():\\n        ax.annotate(SHORT[r.arm], (r.pass_cost_pts, r.H1r25), xytext=(5, 4), textcoords=\\\"offset points\\\", fontsize=8)\\n    dec = k1[k1.family == \\\"decoding\\\"]\\n    if len(dec):\\n        ax.annotate(f\\\"{len(dec)} temperature x sampler cells\\\\n(T 0.3-1.3, top-k 10 / top-p 0.95)\\\",\\n                    (dec.pass_cost_pts.mean(), dec.H1r25.mean()), xytext=(30, -45), textcoords=\\\"offset points\\\",\\n                    fontsize=8, arrowprops={\\\"arrowstyle\\\": \\\"->\\\", \\\"lw\\\": 0.8})\\n    x0, x1 = ax.get_xlim()\\n    y0, y1 = ax.get_ylim()\\n    ax.fill_between([x0, 20], 2, max(y1, 2.3), color=\\\"gold\\\", alpha=0.2, zorder=1, label=\\\"qualify: H1r25 >= 2 at <= 20 pts\\\")\\n    ax.set_xlim(x0, x1)\\n    ax.set_ylim(min(y0, 0.9), max(y1, 2.3))\\n    ax.legend(fontsize=7, loc=\\\"upper right\\\")\\nelse:\\n    ax.text(0.5, 0.5, f\\\"no T1 cell among the first N_CELLS = {N_CELLS}\\\", ha=\\\"center\\\", transform=ax.transAxes)\\nn_below = int(((knob.task == \\\"T1\\\") & knob.H1r25.isna()).sum())\\nax.set(xlabel=\\\"pass cost (points vs own twin)\\\", ylabel=\\\"H1r25 (effective number of algorithms among 25 correct)\\\",\\n       title=f\\\"(a) T1 path search: every knob vs its own twin\\\\n({len(k1)} cells; {n_below} below depth 25 not shown)\\\")\\n\\n# (b) each random direction x alpha: excess off-default share over its twin vs pass rate relative to the twin\\nax = axes[0, 1]\\ndr = pd.DataFrame(extras[\\\"per_direction_rows\\\"])\\nif len(dr):\\n    dr[\\\"excess\\\"] = (1 - dr.n_default / dr.n_attempted) - (1 - dr.twin_n_default / dr.twin_n_attempted)\\n    dr[\\\"pass_ratio\\\"] = (dr.n_passed / dr.n) / (dr.twin_n_passed / dr.twin_n)\\n    dr[\\\"escape\\\"] = [escape_of(r)[0] for r in extras[\\\"per_direction_rows\\\"]]\\n    tcol = dict(zip(sorted(dr.task.unique()), plt.cm.tab10.colors))\\n    mk = {(\\\"hf-fp8\\\", 1.0): \\\"o\\\", (\\\"hf-fp8\\\", 2.0): \\\"^\\\", (\\\"hf-bf16\\\", 1.0): \\\"s\\\"}\\n    for (t, eng, a), g in dr.groupby([\\\"task\\\", \\\"engine\\\", \\\"alpha\\\"]):\\n        ax.scatter(g.excess, g.pass_ratio, s=65, marker=mk.get((eng, a), \\\"D\\\"), color=tcol[t],\\n                   edgecolors=[\\\"k\\\" if e else \\\"none\\\" for e in g.escape], linewidths=1.3, alpha=0.85, zorder=3,\\n                   label=f\\\"{t} {eng} alpha {a:g}: {int(g.escape.sum())}/{len(g)} escape\\\")\\n    x0, x1 = ax.get_xlim()\\n    y0, y1 = ax.get_ylim()\\n    ax.fill_between([0.20, max(x1, 0.3)], 0.8, max(y1, 1.05), color=\\\"gold\\\", alpha=0.2, zorder=1, label=\\\"escape region\\\")\\n    ax.axvline(0.20, color=\\\"k\\\", ls=\\\"--\\\", lw=0.8)\\n    ax.axhline(0.8, color=\\\"k\\\", ls=\\\":\\\", lw=0.8)\\n    ax.set_xlim(x0, max(x1, 0.3))\\n    ax.set_ylim(y0, max(y1, 1.05))\\n    ax.legend(fontsize=7, loc=\\\"lower right\\\")\\nax.set(xlabel=\\\"off-default share: direction minus twin\\\", ylabel=\\\"pass rate: direction / twin\\\",\\n       title=\\\"(b) random activation directions: escape = excess >= 0.20 at pass >= 0.8 x twin\\\\n(black edge = escaping)\\\")\\n\\n# (c) the screen rule: best escape fraction over alpha vs catalogue-only modal-ban avoidance, for all 14 tasks\\nax = axes[1, 0]\\n\\n\\ndef _emax(rec: dict) -> float:\\n    return max([v for v in (rec[\\\"alpha_1\\\"][\\\"E_t\\\"], rec[\\\"alpha_2\\\"][\\\"E_t\\\"]) if v is not None], default=0.0)\\n\\n\\nfor i, (t, rec) in enumerate(sorted(frozen[\\\"tasks\\\"].items())):\\n    mine = t in screen[\\\"tasks\\\"]\\n    rr = screen[\\\"tasks\\\"][t] if mine else rec\\n    col = \\\"#d62728\\\" if rr[\\\"movable\\\"] else \\\"#1f77b4\\\"\\n    ax.scatter(_emax(rr), rr[\\\"cat_only_ban_avoidance\\\"], s=130 if mine else 70, color=col if mine else \\\"none\\\",\\n               edgecolor=col if mine else \\\"#7f7f7f\\\", linewidth=1.5, zorder=3)\\n    ax.annotate(t, (_emax(rr), rr[\\\"cat_only_ban_avoidance\\\"]), xytext=(8, 8 * (i % 3 - 1) - 3), textcoords=\\\"offset points\\\",\\n                fontsize=9 if mine else 8, color=\\\"k\\\" if mine else \\\"#7f7f7f\\\")\\nax.axhline(0.5, color=\\\"k\\\", ls=\\\"--\\\", lw=0.8)\\nax.fill_between([0.02, 1.05], 0.5, 1.05, color=\\\"gold\\\", alpha=0.2, zorder=1)\\nax.text(0.55, 0.53, \\\"movable (E_t > 0) and avoidance >= 0.5\\\", fontsize=8)\\nax.set_xlim(-0.05, 1.05)\\nax.set_ylim(-0.05, 1.05)\\nax.legend(handles=[Line2D([], [], marker=\\\"o\\\", ls=\\\"\\\", color=\\\"#d62728\\\", label=\\\"movable (recomputed here)\\\"),\\n                   Line2D([], [], marker=\\\"o\\\", ls=\\\"\\\", color=\\\"#1f77b4\\\", label=\\\"immovable (recomputed here)\\\"),\\n                   Line2D([], [], marker=\\\"o\\\", ls=\\\"\\\", mfc=\\\"none\\\", mec=\\\"#7f7f7f\\\", label=\\\"frozen record (not in demo subset)\\\")],\\n          fontsize=8, loc=\\\"center right\\\")\\nax.set(xlabel=\\\"max over alpha of E_t (escaping / run)\\\", ylabel=\\\"catalogue-only modal-ban avoidance\\\",\\n       title=\\\"(c) push screen: movable => modal-ban avoidance >= 0.5\\\")\\n\\n# (d) reproduction check of the Monte-Carlo statistic\\nax = axes[1, 1]\\nok = np.isfinite(new.H1r25.values) & np.isfinite(old.H1r25.values)\\nif ok.any():\\n    ax.scatter(old.H1r25[ok], new.H1r25[ok], s=40, color=\\\"#2ca02c\\\", edgecolor=\\\"k\\\", linewidth=0.4, zorder=3)\\n    lo = float(min(old.H1r25[ok].min(), new.H1r25[ok].min())) - 0.05\\n    hi = float(max(old.H1r25[ok].max(), new.H1r25[ok].max())) + 0.05\\n    ax.plot([lo, hi], [lo, hi], \\\"k--\\\", lw=0.8)\\n    d = np.abs(new.H1r25[ok] - old.H1r25[ok])\\n    ax.set_title(f\\\"(d) recomputed vs recorded H1r25 ({int(ok.sum())} cells), max |diff| = {d.max():.2e}\\\\n\\\"\\n                 f\\\"(N_RAREFY = {N_RAREFY}, N_BOOT = {N_BOOT}, N_BOOT_RAREFY = {N_BOOT_RAREFY})\\\")\\nax.set(xlabel=\\\"recorded H1r25 (artifact knob table)\\\", ylabel=\\\"recomputed H1r25 (this notebook)\\\")\\nplt.tight_layout()\\nfig.savefig(WS / \\\"figures\\\" / \\\"demo_summary.png\\\", dpi=120, bbox_inches=\\\"tight\\\")\\nplt.show()\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"summary\",\n   \"metadata\": {},\n   \"source\": [\n    \"## Summary and scaling\\n\",\n    \"\\n\",\n    \"The config cell controls the run size. To reproduce the artifact's numbers exactly, set `N_RAREFY = 1000`, `N_BOOT = 1000`, `N_BOOT_RAREFY = 200` and `N_CELLS = 99` and run all cells.\"\n   ]\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}"}
```

### [75] TOOL CALL — NotebookEdit · 2026-10-26 11:08:40 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'screen = json.loads((WS / "screen.json").read_text())\nextras = json.loads((WS / "screen_extras.json").read_text())\nfrozen = data["metadata"]["frozen_screen"]\ntab = []\nfor t, rec in screen["tasks"].items():\n    a1, a2 = rec["alpha_1"], rec["alpha_2"]\n    tab.append({"task": t, "alpha 1 escape/run": f"{a1[\'n_escape\']}/{a1[\'n_directions_run\']}",\n                "alpha 2 escape/run": f"{a2[\'n_escape\']}/{a2[\'n_directions_run\']}", "movable": rec["movable"],\n                "push_top1": rec["push_top1"], "push_landing": rec["push_landing"],\n                "cat-only ban avoidance": rec["cat_only_ban_avoidance"], "avoidance >= 0.5": rec["ban_avoidance_ge_0_5"],\n                "escaping engines": ",".join(extras["escaping_engine_per_task"][t]) or "-",\n                "identical to frozen record": rec == frozen["tasks"][t]})\ndisplay(pd.DataFrame(tab))\nfis = extras["fisher_movable_vs_avoidance"]\nprint(f"movable x (avoidance >= 0.5) on the {len(tab)} screened tasks: table {fis[\'table\']}, one-sided Fisher p = "\n      f"{fis[\'p\']:.4g}, balanced accuracy {extras[\'balanced_accuracy\']} ({fis[\'label\']})")\nprint(f"frozen screen (all 14 tasks): movable {frozen[\'movable_tasks\']}; C1 event set {frozen[\'c1_event_set\']}")\n\n# byte-level check: substitute the recomputed task records into the frozen screen and hash the canonical bytes\nspliced = {**frozen, "tasks": {**frozen["tasks"], **screen["tasks"]}}\nspliced["movable_tasks"] = sorted(t for t, v in spliced["tasks"].items() if v["movable"])\nsha_spliced = hashlib.sha256(canonical_bytes(spliced)).hexdigest()\nprint(f"published screen.json sha256           {data[\'metadata\'][\'screen_sha256\']}")\nprint(f"with the {len(tab)} recomputed task records  {sha_spliced}  -> "\n      f"{\'byte-identical\' if sha_spliced == data[\'metadata\'][\'screen_sha256\'] else \'DIFFERENT\'}")'}
```

### [76] TOOL RESULT — NotebookEdit · 2026-10-26 11:08:40 UTC

```
{"new_source": "screen = json.loads((WS / \"screen.json\").read_text())\nextras = json.loads((WS / \"screen_extras.json\").read_text())\nfrozen = data[\"metadata\"][\"frozen_screen\"]\ntab = []\nfor t, rec in screen[\"tasks\"].items():\n    a1, a2 = rec[\"alpha_1\"], rec[\"alpha_2\"]\n    tab.append({\"task\": t, \"alpha 1 escape/run\": f\"{a1['n_escape']}/{a1['n_directions_run']}\",\n                \"alpha 2 escape/run\": f\"{a2['n_escape']}/{a2['n_directions_run']}\... [truncated, 23946 chars total]
```

### [77] TOOL CALL — NotebookEdit · 2026-10-26 11:08:40 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "## Results 2: the push screen against the frozen `screen.json`\n\nEach screened task's record is compared with the frozen record of the artifact. The records depend only on counts, so they must be identical at any Monte-Carlo setting.\n\nAs a byte-level check, the recomputed records are substituted into the frozen screen (the other tasks keep their frozen records) and the canonical bytes are hashed. The sha256 equals the published `d6a2ca97…` only if every recomputed record is identical down to the 4-decimal rounding."}
```

### [78] TOOL RESULT — NotebookEdit · 2026-10-26 11:08:40 UTC

```
{"new_source": "## Results 2: the push screen against the frozen `screen.json`\n\nEach screened task's record is compared with the frozen record of the artifact. The records depend only on counts, so they must be identical at any Monte-Carlo setting.\n\nAs a byte-level check, the recomputed records are substituted into the frozen screen (the other tasks keep their frozen records) and the canonical bytes are hashed. The sha256 equals the published `d6a2ca97…` only if ev... [truncated, 25462 chars total]
```

### [79] ASSISTANT · 2026-10-26 11:08:52 UTC

```
I sent three inserts in one message — let me verify they all landed, in the right order, before continuing.
```

### [80] TOOL CALL — Bash · 2026-10-26 11:08:52 UTC

```
List notebook cells to verify order:
python3 -c "
import json; nb=json.load(open('code_demo.ipynb'))
for c in nb['cells']: print(c['id'], c['cell_type'], ''.join(c['source']).splitlines()[0][:90])"
```

### [81] TOOL RESULT — Bash · 2026-10-26 11:08:52 UTC

```
{"stdout": "33645481 markdown ## Results 2: the push screen against the frozen `screen.json`\nda154212 code screen = json.loads((WS / \"screen.json\").read_text())\n9b595dbb markdown ## Visualization\n1c8d802c code # (a) knob map of the path-search task T1, (b) escape geometry of the random directions, (\nsummary markdown ## Summary and scaling", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [82] ASSISTANT · 2026-10-26 11:09:22 UTC

```
All landed in order — batched inserts run sequentially, so I'll continue in batches (still last-to-first). Next: the knob-comparison results and the `main()` runner.
```

### [83] TOOL CALL — NotebookEdit · 2026-10-26 11:09:22 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'knob = pd.read_parquet(DATA / "knob.parquet")\nKEY = ["artifact_id", "task", "arm", "dial", "precision"]\nrecorded = {tuple(ex["metadata_cell_key"][k] for k in KEY): ex for ex in data["datasets"][0]["examples"][:N_CELLS]}\nNUM = ["pass_rate", "pass_cost_pts", "offdef_share", "cat_only_avoidance", "coverage", "S_obs", "H1r25", "H1r25_cat", "H1r10"]\nCIS = ["H1r25_ci90", "H1r25_ci90_iid", "pass_cost_ci95"]\nMONTE_CARLO = {"H1r25", "H1r25_cat", "H1r10", "H1r25_ci90", "H1r25_ci90_iid", "qualify"}\n\n\ndef _num(x) -> float:\n    return float("nan") if x is None else float(x)\n\n\ndef _ci(x) -> list[float]:\n    return [_num(v) for v in x] if x else [float("nan"), float("nan")]\n\n\ndef _flag(x) -> str:\n    """Recorded flags are the strings \'True\' / \'False\' / \'null\'."""\n    return "null" if x is None or (isinstance(x, float) and math.isnan(x)) else str(bool(x))\n\n\ndef _pairs(a, b) -> list:\n    return list(zip(a, b)) if isinstance(a, list) else [(a, b)]\n\n\nmeta, new_rows, old_rows = [], [], []\nfor _, r in knob.iterrows():\n    ex = recorded[tuple(r[k] for k in KEY)]\n    meta.append({"group": ex["metadata_demo_group"], "exp": r.exp, "task": r.task,\n                 "arm": r.arm + ("" if r.dial == "{}" else " " + r.dial), "family": r.family, "n": int(r.n)})\n    new_rows.append({**{c: float(r[c]) for c in NUM}, **{c: _ci(json.loads(r[c])) for c in CIS},\n                     "escape": _flag(r.escape), "qualify": _flag(r.qualify)})\n    old_rows.append({**{c: _num(ex.get(f"eval_{c}")) for c in NUM}, **{c: _ci(ex["metadata_recorded_ci"][c]) for c in CIS},\n                     "escape": ex["predict_escape"], "qualify": ex["predict_qualify"]})\nnew, old = pd.DataFrame(new_rows), pd.DataFrame(old_rows)\n\nagree = []\nfor c in new.columns:\n    if isinstance(new[c].iloc[0], str):\n        same, diffs = [a == b for a, b in zip(new[c], old[c])], []\n    else:\n        pairs = [_pairs(a, b) for a, b in zip(new[c], old[c])]\n        same = [all((math.isnan(x) and math.isnan(y)) or abs(x - y) <= 1e-9 for x, y in p) for p in pairs]\n        diffs = [abs(x - y) for p in pairs for x, y in p if math.isfinite(x) and math.isfinite(y)]\n    agree.append({"column": c, "kind": "Monte Carlo" if c in MONTE_CARLO else "counts (exact)", "cells": len(same),\n                  "identical": int(sum(same)), "max |recomputed - recorded|": max(diffs) if diffs else 0.0})\nprint(f"{len(new)} cells recomputed with N_RAREFY = {N_RAREFY}, N_BOOT = {N_BOOT}, N_BOOT_RAREFY = {N_BOOT_RAREFY}")\ndisplay(pd.DataFrame(agree))\n\nview = pd.DataFrame(meta)\nview["pass"] = new.pass_rate.round(3)\nview["cost_pts"] = new.pass_cost_pts.round(1)\nview["H1r25"] = new.H1r25.round(3)\nview["H1r25_recorded"] = old.H1r25.round(3)\nview["CI90"] = [f"[{a:.2f}, {b:.2f}]" if math.isfinite(a) else "" for a, b in new.H1r25_ci90]\nview["coverage"] = new.coverage.round(3)\nview["offdef"] = new.offdef_share.round(2)\nview["cat_only"] = new.cat_only_avoidance.round(2)\nview["escape"], view["qualify"] = new.escape, new.qualify\npd.concat([pd.DataFrame(meta), new.add_suffix("_recomputed"), old.add_suffix("_recorded")], axis=1).to_csv(\n    TAB / "demo_recomputed_vs_recorded.csv", index=False)\nt1 = view[(view.task == "T1") & ~view.arm.str.startswith("RAND")].sort_values(["family", "cost_pts"])\nprint(f"\\nPath-search task T1: {len(t1)} knob and twin cells (exp17 random directions are in the screen below)")\ndisplay(t1.drop(columns=["task"]).reset_index(drop=True))'}
```

### [84] TOOL RESULT — NotebookEdit · 2026-10-26 11:09:22 UTC

```
{"new_source": "knob = pd.read_parquet(DATA / \"knob.parquet\")\nKEY = [\"artifact_id\", \"task\", \"arm\", \"dial\", \"precision\"]\nrecorded = {tuple(ex[\"metadata_cell_key\"][k] for k in KEY): ex for ex in data[\"datasets\"][0][\"examples\"][:N_CELLS]}\nNUM = [\"pass_rate\", \"pass_cost_pts\", \"offdef_share\", \"cat_only_avoidance\", \"coverage\", \"S_obs\", \"H1r25\", \"H1r25_cat\", \"H1r10\"]\nCIS = [\"H1r25_ci90\", \"H1r25_ci90_iid\", \"pass_cost_ci95\"]\nMONTE_... [truncated, 33379 chars total]
```

### [85] TOOL CALL — NotebookEdit · 2026-10-26 11:09:22 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': '## Results 1: the recomputed knob table against the recorded artifact\n\nEvery recomputed cell is matched with its recorded row by artifact, task, arm, dial and precision.\n\n- **Counts columns** must agree exactly at any setting: pass rate, pass cost and its CI, off-default share, catalogue-only avoidance, coverage, observed richness and `escape`.\n- **Monte-Carlo columns** agree exactly only with the original `N_RAREFY` / `N_BOOT` / `N_BOOT_RAREFY`, because each cell then replays the same random stream from its own seed: `H1r25`, `H1r25_cat`, `H1r10`, the 90% CIs, and `qualify`, which thresholds `H1r25`.\n\nThe table after the agreement summary lists every T1 (path-search) cell, which together cover each knob family the study tried on one task.'}
```

### [86] TOOL RESULT — NotebookEdit · 2026-10-26 11:09:22 UTC

```
{"new_source": "## Results 1: the recomputed knob table against the recorded artifact\n\nEvery recomputed cell is matched with its recorded row by artifact, task, arm, dial and precision.\n\n- **Counts columns** must agree exactly at any setting: pass rate, pass cost and its CI, off-default share, catalogue-only avoidance, coverage, observed richness and `escape`.\n- **Monte-Carlo columns** agree exactly only with the original `N_RAREFY` / `N_BOOT` / `N_BOOT_RAREFY`, b... [truncated, 35565 chars total]
```

### [87] TOOL CALL — NotebookEdit · 2026-10-26 11:09:22 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '@logger.catch(reraise=True)\ndef main() -> None:\n    # NOTEBOOK: the original parsed `--stages` with argparse (default "all"); here the list comes from the config cell\n    stages = RUN_STAGES\n    _limit_memory()\n    import pandas as pd\n\n    for st in stages:\n        t0 = time.time()\n        logger.info(f"=== stage {st} ===")\n        globals()[f"stage_{st}"]()  # NOTEBOOK: was getattr(S, f"stage_{st}")() with `from src import stages as S`\n        logger.info(f"=== stage {st} done in {time.time() - t0:.1f}s ===")\n    del pd\n\n\nt_run = time.time()\nmain()\nprint(f"stages {RUN_STAGES} finished in {time.time() - t_run:.1f}s; outputs in {WS}/")'}
```

### [88] TOOL RESULT — NotebookEdit · 2026-10-26 11:09:22 UTC

```
{"new_source": "@logger.catch(reraise=True)\ndef main() -> None:\n    # NOTEBOOK: the original parsed `--stages` with argparse (default \"all\"); here the list comes from the config cell\n    stages = RUN_STAGES\n    _limit_memory()\n    import pandas as pd\n\n    for st in stages:\n        t0 = time.time()\n        logger.info(f\"=== stage {st} ===\")\n        globals()[f\"stage_{st}\"]()  # NOTEBOOK: was getattr(S, f\"stage_{st}\")() with `from src import stages as S... [truncated, 37225 chars total]
```

### [89] TOOL CALL — NotebookEdit · 2026-10-26 11:09:22 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': '## Run the stages (`eval.py` `main`)\n\nThe original `main()` parses `--stages`, caps the address space at 18 GB and calls `src.stages.stage_<name>()` for each stage in order. Here the stage list comes from the config cell. The `knob` stage writes `data/knob.parquet`, `tables/knob_table.csv` and `tables/arm_dictionary.csv`. The `screen` stage writes `screen_input.json`, `screen.json`, `screen.sha256`, `screen_extras.json`, `results/screen_summary.json` and two tables. Everything goes into `demo_run/`.'}
```

### [90] TOOL RESULT — NotebookEdit · 2026-10-26 11:09:22 UTC

```
{"new_source": "## Run the stages (`eval.py` `main`)\n\nThe original `main()` parses `--stages`, caps the address space at 18 GB and calls `src.stages.stage_<name>()` for each stage in order. Here the stage list comes from the config cell. The `knob` stage writes `data/knob.parquet`, `tables/knob_table.csv` and `tables/arm_dictionary.csv`. The `screen` stage writes `screen_input.json`, `screen.json`, `screen.sha256`, `screen_extras.json`, `results/screen_summary.json` ... [truncated, 38558 chars total]
```

### [91] ASSISTANT · 2026-10-26 11:10:12 UTC

```
Next batch: the `screen` stage (`run_screen_stage`) and the `src/screen.py` helpers that build its input from the knob table.
```

### [92] TOOL CALL — NotebookEdit · 2026-10-26 11:10:12 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'def run_screen_stage() -> None:\n    rule = _load_rule()\n    knob = pd.read_parquet(DATA / "knob.parquet")\n    drows = random_direction_rows(knob)\n    av, av_src = ban_avoidance(knob)\n    dcounts = direction_counts_table(drows)\n    dcounts.to_csv(TAB / "random_direction_counts.csv", index=False)\n    table110(knob).to_csv(TAB / "table110_alpha2.csv", index=False)\n    # NOTEBOOK: verification_targets(knob, drows) (the 27 quoted review numbers -> tables/verification_targets.csv) and\n    # per_task_verdict(knob, dcounts) (-> tables/per_task_verdict.csv) read cells of all 14 tasks, most of them outside\n    # the demo subset, so both are skipped here.\n    # NOTEBOOK: the original screened all of QWEN14; here the screen runs on the tasks whose complete screen input (every\n    # random direction, its twin and the modal-ban row) is among the demo cells.\n    SCREEN_TASKS = [t for t in QWEN14 if t in av and any(r["task"] == t for r in drows)]\n    # screen core via the stdlib rule\n    # NOTEBOOK: the original hashed the three source files here (sha256_file(p(aid, rel)) for exp17 data/labels.jsonl,\n    # exp13 and exp9 data/samples.jsonl); they are not shipped, so their recorded sha256 values are reused.\n    src_sha = dict(data["metadata"]["frozen_screen"]["source_sha256"])\n    inp = {"direction_rows": [{k: v for k, v in r.items() if k in (\n        "task", "alpha", "direction_id", "engine", "n", "n_attempted", "n_default", "n_passed", "twin_n",\n        "twin_n_attempted", "twin_n_default", "twin_n_passed", "offdef_cat_counts")} for r in drows],\n        "ban_avoidance": {t: round(v, 6) for t, v in av.items()}, "tasks": SCREEN_TASKS, "c1_event_set": C1_SET,\n        "source_sha256": src_sha}\n    (WS / "screen_input.json").write_text(json.dumps(inp, indent=1, sort_keys=True))\n    core = rule.build_core(inp)\n    b = rule.canonical_bytes(core)\n    (WS / "screen.json").write_bytes(b)\n    sha = hashlib.sha256(b).hexdigest()\n    (WS / "screen.sha256").write_text(f"{sha}  screen.json\\n")\n    logger.info(f"screen.json sha256 {sha}; movable {core[\'movable_tasks\']}")\n    # extras (not hashed)\n    movable = {t: core["tasks"][t]["movable"] for t in SCREEN_TASKS}\n    comp = {t: int(av[t] >= 0.5) for t in SCREEN_TASKS}\n    fis = fisher_2x2([movable[t] for t in SCREEN_TASKS], [comp[t] for t in SCREEN_TASKS], alternative="greater")\n    ba = balanced_accuracy([movable[t] for t in SCREEN_TASKS], [comp[t] for t in SCREEN_TASKS])\n    k_mov = sum(movable.values())\n    n_comp = sum(comp.values())\n    power = {}\n    for t in SCREEN_TASKS:\n        k = sum(1 for r in drows if r["task"] == t)\n        n_esc = sum(rule.escape_of(r)[0] for r in drows if r["task"] == t)\n        power[t] = {"K_direction_alpha_cells": k, "n_escape": n_esc,\n                    "ub90_per_direction_escape_if_zero": round(upper_bound_zero_of_k(k), 4) if n_esc == 0 else None}\n    per_engine = {}\n    for t in SCREEN_TASKS:\n        for eng in ("hf-fp8", "hf-bf16"):\n            rr = [r for r in drows if r["task"] == t and r["engine"] == eng]\n            if rr:\n                per_engine.setdefault(t, {})[eng] = {\n                    "n_run": len(rr), "n_escape": sum(rule.escape_of(r)[0] for r in rr),\n                    "escaping": [r["direction_id"] + f"@a{r[\'alpha\']}" for r in rr if rule.escape_of(r)[0]],\n                    "H1r25": {r["direction_id"] + f"@a{r[\'alpha\']}": r["H1r25"] for r in rr}}\n    disc = []\n    for t in C1_SET:\n        if t in movable and not movable[t]:  # NOTEBOOK: `t in movable`, since only SCREEN_TASKS are screened\n            disc.append({"task": t, "note": f"{t} is in the frozen C1 event set by the hypothesis\'s decree but does not "\n                                             "escape mechanically under the pass >= 0.8 x twin rule; the set is not edited."})\n    for t in SCREEN_TASKS:\n        if movable[t] and not comp[t]:\n            disc.append({"task": t, "note": "movable but catalogue-only ban avoidance < 0.5 (screen rule violated)"})\n        if not movable[t] and comp[t]:\n            disc.append({"task": t, "note": "not movable but ban avoidance >= 0.5 (screen rule violated)"})\n    extras = {"per_direction_rows": drows, "per_engine": per_engine, "power_note": power,\n              "power_note_text": "With K direction-alpha cells and 0 escapes, the one-sided 90% upper bound on a task\'s "\n                                 "per-direction escape probability is 1 - 0.1^(1/K) (0.54 at K=3, 0.32 at K=6, 0.14 at K=15): "\n                                 "the immovable side is weakly tested; more directions belong to the plan-subspace artifact.",\n              "fisher_movable_vs_avoidance": {**fis, "label": "descriptive only: screen, not confirmation (rule read off the same data)"},\n              "hypergeometric_one_sided_if_perfect": 1 / math.comb(len(SCREEN_TASKS), max(k_mov, 1)) if k_mov == n_comp else None,\n              "balanced_accuracy": ba, "n_movable": k_mov, "n_ban_avoidance_ge_0_5": n_comp,\n              "ban_avoidance_sources": av_src, "discrepancies": disc,\n              "escaping_engine_per_task": {t: sorted({r["engine"] for r in drows if r["task"] == t and rule.escape_of(r)[0]})\n                                           for t in SCREEN_TASKS},\n              "screen_sha256": sha}\n    (WS / "screen_extras.json").write_text(json.dumps(extras, indent=1, default=str))\n    summary = {"sha256": sha, "movable_tasks": core["movable_tasks"], "n_movable": k_mov,\n               "fisher_p_descriptive": fis["p"], "table": fis["table"], "balanced_accuracy": ba,\n               # NOTEBOOK: the "verification" entry (n_targets / n_matched of verification_targets) is skipped in the demo\n               "E": {f"{t}_a{int(a)}": core["tasks"][t][f"alpha_{int(a)}"]["E_t"] for t in SCREEN_TASKS for a in (1.0, 2.0)}}\n    (RES / "screen_summary.json").write_text(json.dumps(summary, indent=1, default=str))\n\n\n# ---- src/stages.py ----\ndef stage_screen() -> None:\n    # NOTEBOOK: was `from src.screen import run_screen_stage`; the function is defined above\n    run_screen_stage()'}
```

### [93] TOOL RESULT — NotebookEdit · 2026-10-26 11:10:12 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [94] TOOL CALL — NotebookEdit · 2026-10-26 11:10:12 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': '## Stage `screen` (`src/screen.py`, part 2)\n\nThis stage writes the screen input, then `screen.json` (the canonical core) with its sha256. It also writes the unhashed extras: per-engine counts, power notes, a descriptive one-sided Fisher test and balanced accuracy of *movable* against *avoidance ≥ 0.5*, and the discrepancies.\n\nThree adaptations to the demo subset are marked `NOTEBOOK:` in the code:\n1. The screen covers the tasks whose complete input is in the subset, instead of all 14.\n2. The `source_sha256` of the three source files is taken from the frozen screen, because the files are not shipped.\n3. The 27 verification targets and the per-task verdicts, which read cells of all 14 tasks, are skipped.'}
```

### [95] TOOL RESULT — NotebookEdit · 2026-10-26 11:10:12 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [96] TOOL CALL — NotebookEdit · 2026-10-26 11:10:12 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'C1_SET = ["T03", "T05", "T06", "T10", "T1", "T2"]\n\n\ndef _load_rule():\n    # NOTEBOOK: the original imported screen_rule.py from the artifact folder with importlib.util; its functions are\n    # defined in the cell above, so the same three names are handed back as a namespace\n    return types.SimpleNamespace(escape_of=escape_of, build_core=build_core, canonical_bytes=canonical_bytes)\n\n\ndef _comp(s: str) -> dict:\n    return json.loads(s) if isinstance(s, str) and s else {}\n\n\ndef random_direction_rows(knob: pd.DataFrame) -> list[dict]:\n    """Per-direction rows for the screen: exp17 RAND90xx (HF, FP8 linears) and exp13 rand1-3 (HF, bf16)."""\n    k = knob.set_index(["exp", "task", "arm", "dial", "precision"], drop=False)\n    out = []\n    sel = knob[(knob.family == "activation-random") & knob.exp.isin(["exp13", "exp17"]) & knob.task.isin(QWEN14)]\n    for _, r in sel.iterrows():\n        ref = k.loc[tuple(json.loads(r.ref_key))]\n        if r.exp == "exp17":\n            did, alpha = "exp17:" + r.arm.split("_a")[0], float(r.arm.split("_a")[1])\n            engine = "hf-fp8"\n        else:\n            did, alpha, engine = "exp13:" + r.arm, 1.0, "hf-bf16"\n        att = _comp(r.attempted_composition)\n        d = default_of(r.task)\n        cat = set(catalogue(r.task))\n        offcat = {l: c for l, c in att.items() if l in cat and l != d}\n        out.append({"task": r.task, "alpha": alpha, "direction_id": did, "engine": engine, "n": int(r.n),\n                    "n_attempted": int(r.n_attempted), "n_default": int(att.get(d, 0)), "n_passed": int(r.n_correct),\n                    "twin_n": int(ref.n), "twin_n_attempted": int(ref.n_attempted),\n                    "twin_n_default": int(_comp(ref.attempted_composition).get(d, 0)),\n                    "twin_n_passed": int(ref.n_correct), "offdef_cat_counts": dict(sorted(offcat.items())),\n                    "n_other": int(att.get("other", 0)), "H1r25": None if not np.isfinite(r.H1r25) else round(float(r.H1r25), 4),\n                    "pass_cost_pts": round(float(r.pass_cost_pts), 2), "qualify": bool(r.qualify),\n                    "knob_row_id": r.row_id, "source": r.sources})\n    return out\n\n\ndef ban_avoidance(knob: pd.DataFrame) -> tuple[dict, dict]:\n    """Catalogue-only modal-ban avoidance: exp13 arm ban (bench); exp9 single-ban rows (T1/T2)."""\n    av, src = {}, {}\n    for t in BENCH12:\n        q = knob[(knob.exp == "exp13") & (knob.task == t) & (knob.arm == "ban")]\n        if not len(q):  # NOTEBOOK: the demo subset holds the ban rows of the screened tasks only\n            continue\n        r = q.iloc[0]\n        av[t] = float(r.cat_only_avoidance)\n        src[t] = {"source": r.sources, "plain_avoidance": float(r.offdef_share), "n_attempted": int(r.n_attempted)}\n    for t, arm in (("T1", "single:bfs"), ("T2", "single:dijkstra")):\n        q = knob[(knob.exp == "exp9") & (knob.task == t) & (knob.arm == arm)]\n        if not len(q):  # NOTEBOOK: as above\n            continue\n        r = q.iloc[0]\n        av[t] = float(r.cat_only_avoidance)\n        src[t] = {"source": r.sources, "plain_avoidance": float(r.offdef_share), "n_attempted": int(r.n_attempted)}\n    # NOTEBOOK: the original also attached, as a source note only, the pooled iteration-2 T1 / T2 ban landings of exp16\n    # (results/screen_paths.json -> src[t]["exp16_screen_paths_pooled_cat_only_avoidance"]); that file is not shipped.\n    return av, src\n\n\ndef direction_counts_table(drows: list[dict]) -> pd.DataFrame:\n    rule = _load_rule()\n    recs = []\n    for t in QWEN14:\n        for a in (1.0, 2.0):\n            ra = [r for r in drows if r["task"] == t and r["alpha"] == a]\n            if not ra:\n                continue\n            esc = [r for r in ra if rule.escape_of(r)[0]]\n            qual = [r for r in esc if r["qualify"]]\n            qual_all = [r for r in ra if r["qualify"]]\n            rec = {"task": t, "alpha": a, "engine": "pooled", "n_run": len(ra), "n_escape": len(esc),\n                   "n_qualify": len(qual_all), "n_escape_and_qualify": len(qual),\n                   "escaping_ids": ";".join(r["direction_id"] for r in esc),\n                   "qualifying_ids": ";".join(r["direction_id"] for r in qual_all),\n                   "denominator": f"{len(esc)}/{len(ra)}"}\n            for eng in ("hf-fp8", "hf-bf16"):\n                re_ = [r for r in ra if r["engine"] == eng]\n                rec[f"n_run_{eng}"] = len(re_)\n                rec[f"n_escape_{eng}"] = sum(rule.escape_of(r)[0] for r in re_)\n                rec[f"n_qualify_{eng}"] = sum(r["qualify"] for r in re_)\n            recs.append(rec)\n    return pd.DataFrame(recs)\n\n\ndef table110(knob: pd.DataFrame) -> pd.DataFrame:\n    sel = knob[(knob.exp == "exp17") & knob.arm.isin(["RAND9001_a2.0", "RAND9002_a2.0", "RAND9003_a2.0", "ADD_a2.0"])]\n    return sel[["task", "arm", "n", "n_attempted", "offdef_share", "cat_only_avoidance", "pass_rate", "pass_cost_pts",\n                "H1r25", "attempted_composition", "correct_composition", "sources"]].rename(\n        columns={"offdef_share": "avoidance"}).sort_values(["task", "arm"])'}
```

### [97] TOOL RESULT — NotebookEdit · 2026-10-26 11:10:12 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [98] TOOL CALL — NotebookEdit · 2026-10-26 11:10:12 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': '## Screen inputs from the knob table (`src/screen.py`, part 1)\n\n`random_direction_rows` turns each Qwen random-direction cell into one screen row and pairs its counts with those of its twin. The cells are exp17 `RAND90xx_a1.0` / `_a2.0`, norm-matched directions on the HF engine with FP8 linears, and exp13 `rand1-3`, matched-norm directions on the bf16 HF engine.\n\n`ban_avoidance` reads each task\'s catalogue-only avoidance under the modal "do not use X" ban: exp13 `ban` for bench tasks, and exp9 `single:bfs` / `single:dijkstra` for T1 / T2.\n\n`direction_counts_table` gives the per-task, per-α direction counts (`tables/random_direction_counts.csv`), and `table110` lists exp17\'s α = 2 rows.'}
```

### [99] TOOL RESULT — NotebookEdit · 2026-10-26 11:10:12 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [100] ASSISTANT · 2026-10-26 11:11:08 UTC

```
Next batch: `screen_rule.py`, the `knob` stage function, and `build_knob_table`.
```

### [101] TOOL CALL — NotebookEdit · 2026-10-26 11:11:08 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '# screen_rule.py: "Push-movability screen rule (stdlib only), so parallel artifacts can recompute screen.json byte for byte."\n# Rule (Claim 3a screen): ESCAPE(d, t, a) iff offdef(d) - offdef(twin) >= 0.20 and pass(d) >= 0.8 x pass(twin),\n# with offdef = 1 - n_default / n_attempted and pass = n_passed / n. E_t(a) = escaping / run at alpha a;\n# MOVABLE(t) = 1 iff E_t(a) > 0 for some a <= 2. Push landing over escaping directions:\n# w_X = sum_d e_d * share_d(X | off-default catalogue attempts) / sum_d e_d, e_d = offdef(d) - offdef(twin);\n# \'other\' is excluded. Screen prediction: movable implies catalogue-only ban avoidance >= 0.5.\n# (Its command-line main(), `python screen_rule.py screen_input.json out.json`, is not needed in the notebook.)\n\nESCAPE_MARGIN = 0.20\nPASS_RATIO = 0.8\nALPHAS = (1.0, 2.0)\nRULE_TEXT = "movable(t) implies catalogue-only modal-ban avoidance(t) >= 0.5"\nESCAPE_TEXT = ("escape(d,t,a): offdef(d)-offdef(twin) >= 0.20 and pass(d) >= 0.8*pass(twin); "\n               "offdef = 1 - n_default/n_attempted; pass = n_passed/n (no-code rows fail)")\n\n\ndef _r(x):\n    if isinstance(x, float):\n        return round(x, 4)\n    if isinstance(x, dict):\n        return {k: _r(v) for k, v in x.items()}\n    if isinstance(x, list):\n        return [_r(v) for v in x]\n    return x\n\n\ndef canonical_bytes(obj) -> bytes:\n    return (json.dumps(_r(obj), sort_keys=True, ensure_ascii=True, separators=(",", ":")) + "\\n").encode("ascii")\n\n\ndef offdef(n_default: int, n_attempted: int):\n    return 1.0 - n_default / n_attempted if n_attempted else None\n\n\ndef escape_of(row: dict):\n    od = offdef(row["n_default"], row["n_attempted"])\n    tw = offdef(row["twin_n_default"], row["twin_n_attempted"])\n    if od is None or tw is None or not row["n"] or not row["twin_n"]:\n        return False, 0.0\n    p, pt = row["n_passed"] / row["n"], row["twin_n_passed"] / row["twin_n"]\n    excess = od - tw\n    # 1e-9 guards float noise at the exact 0.20 boundary (e.g. 0.30 - 0.10)\n    return bool(excess >= ESCAPE_MARGIN - 1e-9 and p >= PASS_RATIO * pt - 1e-12), excess\n\n\ndef build_core(inp: dict) -> dict:\n    tasks = sorted(inp["tasks"])\n    per = {}\n    for t in tasks:\n        rows = [r for r in inp["direction_rows"] if r["task"] == t]\n        rec = {}\n        movable = 0\n        num: dict = {}\n        den = 0.0\n        for a in ALPHAS:\n            ra = [r for r in rows if float(r["alpha"]) == a]\n            n_esc = 0\n            for r in ra:\n                esc, e = escape_of(r)\n                if esc:\n                    n_esc += 1\n                    cnt = {k: v for k, v in r["offdef_cat_counts"].items() if k != "other" and v > 0}\n                    tot = sum(cnt.values())\n                    if tot > 0:\n                        den += e\n                        for k, v in cnt.items():\n                            num[k] = num.get(k, 0.0) + e * v / tot\n            key = f"alpha_{int(a)}"\n            rec[key] = {"n_directions_run": len(ra), "n_escape": n_esc,\n                        "E_t": (n_esc / len(ra)) if ra else None}\n            if ra and n_esc > 0:\n                movable = 1\n        land = {k: v / den for k, v in sorted(num.items())} if den > 0 else {}\n        top1 = sorted(land.items(), key=lambda kv: (-round(kv[1], 12), kv[0]))[0][0] if land else None\n        av = inp["ban_avoidance"].get(t)\n        rec.update({"movable": movable, "push_landing": land, "push_top1": top1, "cat_only_ban_avoidance": av,\n                    "ban_avoidance_ge_0_5": (None if av is None else bool(av >= 0.5))})\n        per[t] = rec\n    return {"screen_version": "iter4-step0", "tasks": per, "c1_event_set": sorted(inp["c1_event_set"]),\n            "screen_rule": RULE_TEXT, "escape_rule": ESCAPE_TEXT,\n            "movable_tasks": sorted(t for t in tasks if per[t]["movable"]),\n            "source_sha256": dict(sorted(inp["source_sha256"].items()))}'}
```

### [102] TOOL RESULT — NotebookEdit · 2026-10-26 11:11:08 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [103] TOOL CALL — NotebookEdit · 2026-10-26 11:11:08 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "## The frozen screen rule (`screen_rule.py`, standard library only)\n\n`screen_rule.py` uses only the standard library, so that parallel artifacts can recompute `screen.json` byte for byte. Its input is one row per random direction × α, holding the counts for the direction and for its twin, plus each task's catalogue-only modal-ban avoidance.\n\nFor every task the rule:\n- counts the escaping directions at α = 1 and α = 2, giving `E_t(α)` = escaping / run;\n- marks the task *movable* if any direction escapes;\n- computes the **push landing**: the catalogue algorithms the escaping directions land on, weighted by each direction's excess off-default share ('other' is excluded).\n\nThe output is canonical JSON (sorted keys, floats rounded to 4 places), so its sha256 identifies the frozen screen."}
```

### [104] TOOL RESULT — NotebookEdit · 2026-10-26 11:11:08 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [105] TOOL CALL — NotebookEdit · 2026-10-26 11:11:08 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'def stage_knob() -> None:\n    # NOTEBOOK: KNOB_COLUMNS, arm_dictionary and build_knob_table are defined above (was `from src.knob import ...`)\n    rows = rows_from_data(data, N_CELLS)  # NOTEBOOK: was pd.read_parquet(DATA / "rows.parquet") (written by stage rows)\n    knob = build_knob_table(rows)\n    # NOTEBOOK: was json.loads(p("exp15", "results/push_hook_stats.json").read_text()); that file only annotates exp15\'s\n    # Llama random-direction arms, none of which is in the demo subset, so the column below is all None here\n    hook = {}\n    knob["realised_l21_displacement_ratio"] = [\n        hook.get(a.split("_", 1)[1], {}).get("added_over_target_l21") if (e == "exp15" and a.startswith("rand_")) else None\n        for e, a in zip(knob.exp, knob.arm)]\n    knob.to_parquet(DATA / "knob.parquet", index=False)\n    knob[KNOB_COLUMNS].to_csv(TAB / "knob_table.csv", index=False)\n    arm_dictionary(knob).to_csv(TAB / "arm_dictionary.csv", index=False)\n    logger.info(f"knob table: {len(knob)} rows -> tables/knob_table.csv")'}
```

### [106] TOOL RESULT — NotebookEdit · 2026-10-26 11:11:08 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [107] TOOL CALL — NotebookEdit · 2026-10-26 11:11:08 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': '## Stage `knob` (`src/stages.py`)\n\nThis stage builds the knob table from the program rows. It writes `data/knob.parquet`, which the screen stage reads, plus `tables/knob_table.csv` and `tables/arm_dictionary.csv`.'}
```

### [108] TOOL RESULT — NotebookEdit · 2026-10-26 11:11:08 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [109] TOOL CALL — NotebookEdit · 2026-10-26 11:11:08 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '# ------------------------------------------------------------------------------------------------ cells\ndef _cell_job(args: tuple) -> dict:\n    cid, labels, templates, noncat = args\n    prim = h1r_cell(labels, templates, cid, DEPTH)\n    cat = h1r_cell(labels, templates, cid + "|cat", DEPTH, drop=noncat, with_ci=False)\n    low = h1r_cell(labels, templates, cid, DEPTH_LOW, with_ci=False) if prim["n_c"] < DEPTH else None\n    return {"cid": cid, "prim": prim, "cat": cat, "low": low}\n\n\ndef build_knob_table(rows: pd.DataFrame, n_workers: int = 1) -> pd.DataFrame:\n    rows = rows.copy()\n    rows["exp"] = rows.artifact_id.map(exp_name)\n    keys = ["exp", "artifact_id", "task", "arm", "dial", "precision"]\n    groups = list(rows.groupby(keys, sort=True))\n    cellset = {(k[0], k[2], k[3], k[4], k[5]) for k, _ in groups}\n    base = []\n    jobs = []\n    for (exp, aid, task, arm, dial, prec), g in groups:\n        cid = f"{aid}|{task}|{arm}|{dial}|{prec}"\n        att = g[g.attempted]\n        cor = g[g.passed]\n        noncat = sorted(set(cor.label_norm[~cor.is_catalogue]))\n        jobs.append((cid, cor.label_norm.tolist(), cor.template.tolist(), noncat))\n        base.append({"cid": cid, "exp": exp, "artifact_id": aid, "src_file": g.src_file.iloc[0], "model": g.model.iloc[0],\n                     "engine": ",".join(sorted(set(g.engine))), "precision": prec, "task": task, "arm": arm,\n                     "dial": dial, "n": int(len(g)), "n_attempted": int(len(att)), "n_correct": int(len(cor)),\n                     "n_default_att": int(att.is_default.sum()),\n                     "n_cat_nondefault_att": int((att.is_catalogue & ~att.is_default).sum()),\n                     "correct_composition": json.dumps(dict(Counter(cor.label_norm).most_common())),\n                     "attempted_composition": json.dumps(dict(Counter(att.label_norm).most_common())),\n                     "offdef_attempted_cat_composition": json.dumps(dict(Counter(\n                         att.label_norm[att.is_catalogue & ~att.is_default]).most_common())),\n                     "other_share": float((att.label_norm == "other").mean()) if len(att) else float("nan")})\n    logger.info(f"knob table: {len(base)} cells; computing rarefied Hill-1 with {n_workers} workers")\n    # NOTEBOOK: the original ran the jobs with ProcessPoolExecutor(max_workers=n_workers (default 5),\n    # mp_context=mp.get_context("spawn")) and ex.map(_cell_job, jobs, chunksize=8). Spawned workers cannot import a\n    # function defined in a notebook, so the same jobs run in this process; every cell has its own seed, so the\n    # results are identical.\n    res = {r["cid"]: r for r in map(_cell_job, jobs)}\n    out = []\n    for b in base:\n        r = res[b["cid"]]\n        prim, cat, low = r["prim"], r["cat"], r["low"]\n        dial = json.loads(b["dial"])\n        cls, fam, desc = classify(b["exp"], b["arm"], dial)\n        b.update({"class": cls, "family": fam, "description": desc,\n                  "pass_rate": b["n_correct"] / b["n"] if b["n"] else float("nan"),\n                  "offdef_share": 1 - b["n_default_att"] / b["n_attempted"] if b["n_attempted"] else float("nan"),\n                  "cat_only_avoidance": b["n_cat_nondefault_att"] / b["n_attempted"] if b["n_attempted"] else float("nan"),\n                  "H1r25": prim["value"], "H1r25_ci90": json.dumps([round(x, 4) for x in prim["ci90"]]),\n                  "H1r25_ci90_iid": json.dumps([round(x, 4) for x in prim["ci90_iid"]]), "ci_unit": prim["ci_unit"],\n                  "H1r25_cat": cat["value"], "H1r10": (low or {}).get("value", float("nan")),\n                  "S_obs": prim["S_obs"], "coverage": prim["coverage"]})\n        ref, flags = ref_of(b["exp"], b["arm"], dial, b["task"], b["precision"], cellset)\n        b["ref_key"] = json.dumps(ref) if ref else ""\n        b["flags_list"] = flags + (["below_depth"] if prim["n_c"] < DEPTH else [])\n        out.append(b)\n    df = pd.DataFrame(out)\n    idx = {(r.exp, r.task, r.arm, r.dial, r.precision): i for i, r in df.iterrows()}\n    ref_pass, ref_arm, cost, cost_ci, ref_off, esc, qual = [], [], [], [], [], [], []\n    for _, r in df.iterrows():\n        if not r.ref_key:\n            ref_pass.append(np.nan); ref_arm.append(""); cost.append(np.nan); cost_ci.append("[]"); ref_off.append(np.nan)\n            esc.append(None); qual.append(None)\n            continue\n        rk = tuple(json.loads(r.ref_key))\n        rr = df.loc[idx[rk]]\n        ref_arm.append(f"{rr.arm}{\'\' if rr.dial == \'{}\' else \' \' + rr.dial}")\n        ref_pass.append(rr.pass_rate)\n        d, lo, hi = newcombe_diff(int(rr.n_correct), int(rr.n), int(r.n_correct), int(r.n))\n        cost.append(100 * d)\n        cost_ci.append(json.dumps([round(100 * lo, 2), round(100 * hi, 2)]))\n        ref_off.append(rr.offdef_share)\n        if r["class"] == "control":\n            esc.append(None); qual.append(None)\n        else:\n            esc.append(bool((r.offdef_share - rr.offdef_share) >= 0.20 and r.pass_rate >= 0.8 * rr.pass_rate))\n            qual.append(bool(np.isfinite(r.H1r25) and r.H1r25 >= 2 and 100 * d <= 20))\n    df["ref_arm"], df["ref_pass"], df["pass_cost_pts"], df["pass_cost_ci95"] = ref_arm, ref_pass, cost, cost_ci\n    df["ref_offdef_share"], df["escape"], df["qualify"] = ref_off, esc, qual\n    df["flags"] = df.flags_list.map(lambda x: ";".join(x))\n    df["sources"] = df.artifact_id + ":" + df.src_file\n    df["row_id"] = [f"K{i:04d}" for i in range(len(df))]\n    return df\n\n\nKNOB_COLUMNS = ["row_id", "artifact_id", "src_file", "model", "engine", "precision", "task", "arm", "class", "family",\n                "dial", "n", "n_attempted", "n_correct", "pass_rate", "ref_arm", "ref_pass", "pass_cost_pts",\n                "pass_cost_ci95", "offdef_share", "ref_offdef_share", "cat_only_avoidance", "other_share", "H1r25",\n                "H1r25_ci90", "H1r25_ci90_iid", "ci_unit", "H1r25_cat", "H1r10", "S_obs", "coverage",\n                "correct_composition", "attempted_composition", "offdef_attempted_cat_composition", "escape",\n                "qualify", "flags", "sources", "description", "realised_l21_displacement_ratio"]\n\n\ndef arm_dictionary(knob: pd.DataFrame) -> pd.DataFrame:\n    d = knob.groupby(["artifact_id", "arm"]).agg(cls=("class", "first"), family=("family", "first"),\n                                                  description=("description", "first"), ref_arm=("ref_arm", "first"),\n                                                  engine=("engine", "first"), precision=("precision", "first"),\n                                                  n_cells=("row_id", "count")).reset_index()\n    return d.rename(columns={"cls": "class"})'}
```

### [110] TOOL RESULT — NotebookEdit · 2026-10-26 11:11:08 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [111] TOOL CALL — NotebookEdit · 2026-10-26 11:11:08 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "## One row per cell (`src/knob.py`, part 2)\n\n`build_knob_table` groups the program rows into cells. For each cell it computes:\n- the depth-25 Hill-1 with its CIs;\n- the same value with non-catalogue labels dropped (`H1r25_cat`);\n- the depth-10 value `H1r10` for cells below depth;\n- Good's coverage and the pass rate;\n- the **off-default share**, 1 − default / attempted;\n- the **catalogue-only avoidance**, catalogue non-default / attempted. This counts only avoidance of the default by writing another *known* algorithm, not by writing 'other' or broken code.\n\nEach cell is then priced against its own twin. Its pass cost gets a Newcombe CI, and two flags are set:\n- **escape**: off-default share ≥ twin + 0.20 at pass ≥ 0.8 × twin;\n- **qualify**: Hill-1 ≥ 2 at a cost of at most 20 points."}
```

### [112] TOOL RESULT — NotebookEdit · 2026-10-26 11:11:08 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [113] ASSISTANT · 2026-10-26 11:12:04 UTC

```
Next batch: the arm dictionary (`classify`, `ref_of`), the rows adapter, and the pass-cost statistics.
```

### [114] TOOL CALL — NotebookEdit · 2026-10-26 11:12:04 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'NONCAT_DROP_MARK = "__noncat__"\n\n\n# ------------------------------------------------------------------------------------------------ arm dictionary\ndef classify(exp: str, arm: str, dial: dict) -> tuple[str, str, str]:\n    """-> (class, family, one-line description)."""\n    a = arm\n    if exp == "exp13":\n        m = {"twin": ("control", "twin", "neutral twin (vLLM)"), "hf_twin": ("control", "twin", "neutral twin (HF engine)"),\n             "sham": ("control", "sham_veto", "sham token veto"), "ban": ("knob", "prompt:ban", "modal \'do not use X\' ban"),\n             "nonce": ("knob", "prompt:nonce", "nonce ban"), "novelty": ("knob", "prompt:novelty", "novelty instruction"),\n             "oneshot": ("knob", "veto", "one-shot token veto"), "persistent": ("knob", "veto", "persistent token veto"),\n             "iter1": ("knob", "veto", "iterated veto round 1"), "iter2": ("knob", "veto", "iterated veto round 2"),\n             "iter3": ("knob", "veto", "iterated veto round 3"),\n             "bandpatch": ("knob", "activation-ban-derived", "ban task-spec states patched into the twin (ban-derived)")}\n        if a in m:\n            return m[a]\n        if a.startswith("rand"):\n            return ("knob", "activation-random", "matched-norm isotropic random direction at task-spec states, layers 12-23")\n    if exp == "exp17":\n        if a == "NEUTRAL":\n            return ("control", "twin", "neutral twin (HF, FP8 linears)")\n        if a.startswith("BAN"):\n            return ("knob", "prompt:ban", "modal ban" + (" (top-up samples)" if "TOPUP" in a else ""))\n        if a.startswith("ADD"):\n            return ("knob", "activation-structured", "leave-one-task-out prohibition direction added to the twin")\n        if a.startswith("RAND"):\n            return ("knob", "activation-random", "norm-matched random direction added to the twin")\n        if a.startswith("SUB") or a.startswith("HEADS"):\n            return ("ablation", "ablation-on-ban", "intervention on the ban (projection / head ablation); not a knob")\n        if a.startswith("U7"):\n            return ("control", "engine_check", "U7 engine reproduction check")\n    if exp == "exp15":\n        if a in ("neutral_baseline", "vetofree"):\n            return ("control", "twin", "Llama neutral twin" + (" (veto chain pass-1)" if a == "vetofree" else ""))\n        if a == "pilot_fp8":\n            return ("control", "pilot", "Llama FP8 pilot (no ban)")\n        if a in ("nonce", "novelty"):\n            return ("knob", f"prompt:{a}", f"{a} prompt (Llama)")\n        if a.startswith("rand_"):\n            return ("knob", "activation-random", "matched-norm random direction at spec positions, layers 11-21 (Llama)")\n        if a.startswith("ban_"):\n            return ("knob", "prompt:ban", f"{a.split(\':\')[0][4:]} ban of {a.split(\':\')[1]} (Llama)")\n        if a.startswith("veto_"):\n            return ("knob", "veto", f"{a[5:]} signature-n-gram veto (Llama)")\n    if exp == "exp16":\n        return ("control", "route_diagnostic", {"a": "full ban", "b": "token-matched neutral twin",\n                                                "c": "prompt route (twin condition + ban spec states)",\n                                                "d": "direct route (ban condition + twin spec states)",\n                                                "K0": "condition span invisible to generated tokens",\n                                                "V1": "one-shot veto of the default\'s n-gram"}.get(a, "route/prefill diagnostic arm"))\n    if exp == "exp14":\n        kind = a.split(":")[0]\n        if kind == "copy":\n            return ("control", "copy", "COPY: shown programs of Y, no ban")\n        if kind == "baseline":\n            return ("control", "twin", "no-exposure baseline")\n        if kind in ("named", "unnamed"):\n            return ("knob", "prompt:exposure_ban", f"{kind.upper()} exposure ban of the shown algorithm")\n        if kind == "veto":\n            return ("knob", "veto", "in-context signature veto of the shown algorithm")\n        if kind.startswith("W"):\n            return ("knob", "prompt:exposure_ban", f"exposure ban, template arm {kind}")\n    if exp == "exp18":\n        if a == "walk_twin":\n            return ("control", "twin", "neutral twin (walk step 0)")\n        if a.startswith("walk_step"):\n            return ("knob", "veto", "persistent token-walk veto")\n        if a == "sham":\n            return ("control", "sham_veto", "matched sham veto")\n        if a == "fixed_top5":\n            return ("knob", "veto", "fixed TOP5 veto")\n        if a.startswith("los:"):\n            return ("knob", "prompt:list", "leave-one-survivor list ban")\n        if a.startswith("two_step:"):\n            return ("knob", "prompt:ban", "two-step ban")\n        if a.startswith("longform:"):\n            return ("knob", "prompt:instruction", "2,000-word \'make a (fully) novel algorithm\' instruction")\n    if exp == "exp9":\n        if a == "baseline":\n            return ("control", "twin", "no-ban baseline")\n        if a.startswith("single:"):\n            return ("knob", "prompt:ban", "single-name ban")\n        if a.startswith("los:"):\n            return ("knob", "prompt:list", "leave-one-survivor list")\n        if a.startswith("multi:"):\n            return ("knob", "prompt:list", "multi-name ban list")\n    if exp == "exp4":\n        if a == "baseline":\n            return ("control", "twin", "vLLM baseline")\n        if a == "steer:dc":\n            if dial.get("c", 0) == 0:\n                return ("control", "twin", "HF c=0 hook")\n            return ("knob", "activation-structured", "decommitment direction d_dc")\n        if a in ("steer:rand1", "steer:rand2"):\n            return ("knob", "activation-random", "random direction (iteration 1)")\n        if a == "steer:placebo":\n            return ("knob", "activation-structured", "variable-name placebo direction")\n        if a == "steer:breadth":\n            return ("knob", "activation-structured", "breadth direction")\n        if a == "steer:dcxfer":\n            return ("knob", "activation-structured", "cross-task transferred d_dc")\n        if a.startswith("enumerate"):\n            return ("knob", "prompt:instruction", "enumeration prompt")\n        if a.startswith("ban:"):\n            return ("knob", "prompt:ban", "modal ban")\n        if a.startswith("mention:"):\n            return ("control", "mention_twin", "mention twin")\n        if a.startswith("succession"):\n            return ("knob", "prompt:ban", "succession ban")\n    if exp == "exp6":\n        kind, cond = a.split(":", 1)\n        if kind == "A0":\n            return ("control", "twin", "no-cue baseline T=1.0, pure sampling, thinking off")\n        if kind in ("A1", "A6a", "A6b", "A6c", "A6d"):\n            return ("knob", "decoding", "temperature x sampler grid" + (" (thinking on)" if dial.get("thinking") else ""))\n        if kind == "A2":\n            return ("knob", "prompt:seed", f"{cond.replace(\'seed_\', \'\')} seed")\n        if kind == "A3":\n            return ("knob", "prompt:instruction", f"creativity instruction {cond}")\n        if kind.startswith("A4"):\n            return ("ceiling", "generate_then_select", "generate-then-select (ceiling, never ranked)")\n    if exp == "exp11":\n        return ("control", "pilot", "FP8 pilot (no ban)")\n    return ("unclassified", "unclassified", a)\n\n\ndef ref_of(exp: str, arm: str, dial: dict, task: str, precision: str, cells: set) -> tuple[tuple | None, list[str]]:\n    """Own-twin reference cell key (exp, task, arm, dial_json, precision) and flags."""\n    flags: list[str] = []\n    dj = json.dumps({}, sort_keys=True)\n    cand = None\n    if exp == "exp13":\n        hf = arm.startswith("rand") or arm in ("bandpatch", "hf_twin")\n        cand = (task, "hf_twin" if hf else "twin", dj)\n    elif exp == "exp17":\n        cand = (task, "NEUTRAL", dj)\n    elif exp == "exp15":\n        cand = (task, "vetofree" if arm.startswith("veto_") else "neutral_baseline", dj)\n    elif exp == "exp16":\n        cand = (task, "b", dj)\n    elif exp == "exp14":\n        kind = arm.split(":")[0]\n        y = arm.split(":", 1)[1] if ":" in arm else None\n        cand = (task, "baseline", dj) if kind == "copy" else (task, f"copy:{y}", dj)\n    elif exp == "exp18":\n        cand = (task, "walk_twin", dj)\n    elif exp == "exp9":\n        cand = (task, "baseline", dj)\n    elif exp == "exp4":\n        if arm in ("baseline",) or arm.startswith(("ban:", "mention:", "enumerate", "succession")):\n            cand = (task, "baseline", dj)\n        else:\n            cand = (task, "steer:dc", json.dumps({"c": 0.0, "layer": 18}, sort_keys=True))\n    elif exp == "exp6":\n        cand = (task, "A0:baseline", json.dumps({"T": 1.0, "sampler": "pure", "thinking": False}, sort_keys=True))\n        if dial.get("thinking"):\n            flags.append("ref_thinking_off")\n    if cand is None:\n        return None, flags\n    key = (exp,) + cand + (precision,)\n    if key in cells:\n        return key, flags\n    others = [c for c in cells if c[:4] == key[:4]]\n    if others:\n        flags.append("cross_precision_ref")\n        return others[0], flags\n    return None, flags + ["no_own_twin"]'}
```

### [115] TOOL RESULT — NotebookEdit · 2026-10-26 11:12:04 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [116] TOOL CALL — NotebookEdit · 2026-10-26 11:12:04 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "## Arm dictionary and own-twin pricing (`src/knob.py`, part 1)\n\n`classify` puts every arm into a class (`knob`, `control`, `ablation` or `ceiling`) and a family. The families include `decoding` (temperature × sampler), `prompt:seed`, `prompt:instruction`, `prompt:ban`, `prompt:list`, `veto`, `activation-random` and `activation-structured`.\n\n`ref_of` names the cell's **own twin**: the neutral cell of the same experiment, task and engine that the arm is priced against. Examples are exp6's T = 1.0 pure-sampling baseline, exp17's NEUTRAL arm and exp13's HF twin for activation interventions."}
```

### [117] TOOL RESULT — NotebookEdit · 2026-10-26 11:12:04 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [118] TOOL CALL — NotebookEdit · 2026-10-26 11:12:04 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'def rows_from_data(data: dict, n_cells: int) -> pd.DataFrame:\n    """One row per labelled program of the first n_cells demo cells, with the data/rows.parquet columns the knob stage reads."""\n    recs = []\n    for ex in data["datasets"][0]["examples"][:n_cells]:\n        key, prog = ex["metadata_cell_key"], ex["metadata_programs"]\n        for tpl, lab, cat, dft, att, ok in zip(prog["template"], prog["label_norm"], prog["is_catalogue"], prog["is_default"],\n                                               prog["attempted"], prog["passed"]):\n            recs.append({**key, "src_file": prog["src_file"], "model": prog["model"], "engine": prog["engine"],\n                         "template": tpl, "label_norm": lab, "is_catalogue": cat, "is_default": dft, "attempted": att,\n                         "passed": ok})\n    return pd.DataFrame(recs)\n\n\n_rows = rows_from_data(data, N_CELLS)\nprint(f"{len(_rows)} labelled program rows in {_rows.groupby([\'artifact_id\', \'task\', \'arm\', \'dial\', \'precision\']).ngroups} cells")\ndisplay(_rows.head())'}
```

### [119] TOOL RESULT — NotebookEdit · 2026-10-26 11:12:04 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [120] TOOL CALL — NotebookEdit · 2026-10-26 11:12:04 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "## Labelled program rows (replaces the `rows` stage and `data/rows.parquet`)\n\nIn the original pipeline, the `rows` stage (step G2) merges the labelled samples of the 11 dependencies into `data/rows.parquet`, 65,433 rows in all, one per generated program. Each row gives:\n- the program's cell: artifact, task, arm, dial and precision;\n- its prompt template and normalised algorithm label;\n- the flags `attempted` (the output contains a program), `passed` (it passed the hidden tests), `is_catalogue` and `is_default`.\n\nHere the same columns are rebuilt from the demo cells."}
```

### [121] TOOL RESULT — NotebookEdit · 2026-10-26 11:12:04 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [122] TOOL CALL — NotebookEdit · 2026-10-26 11:12:04 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:\n    if n <= 0:\n        return float("nan"), float("nan")\n    ph = k / n\n    den = 1 + z * z / n\n    c = (ph + z * z / (2 * n)) / den\n    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den\n    return max(0.0, c - h), min(1.0, c + h)\n\n\ndef newcombe_diff(k1: int, n1: int, k2: int, n2: int) -> tuple[float, float, float]:\n    """p1 - p2 with the Newcombe (1998, method 10) hybrid-score 95% interval."""\n    if n1 <= 0 or n2 <= 0:\n        return float("nan"), float("nan"), float("nan")\n    p1, p2 = k1 / n1, k2 / n2\n    l1, u1 = wilson(k1, n1)\n    l2, u2 = wilson(k2, n2)\n    d = p1 - p2\n    return d, d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)\n\n\ndef balanced_accuracy(pred: Sequence[int], truth: Sequence[int]) -> float:\n    pred, truth = np.asarray(pred), np.asarray(truth)\n    pos, neg = truth == 1, truth == 0\n    if pos.sum() == 0 or neg.sum() == 0:\n        return float("nan")\n    return float(0.5 * ((pred[pos] == 1).mean() + (pred[neg] == 0).mean()))\n\n\ndef fisher_2x2(pred: Sequence[int], truth: Sequence[int], alternative: str = "two-sided") -> dict:\n    pred, truth = np.asarray(pred), np.asarray(truth)\n    tab = [[int(((pred == 1) & (truth == 1)).sum()), int(((pred == 1) & (truth == 0)).sum())],\n           [int(((pred == 0) & (truth == 1)).sum()), int(((pred == 0) & (truth == 0)).sum())]]\n    res = sps.fisher_exact(tab, alternative=alternative)\n    return {"table": tab, "p": float(res.pvalue), "alternative": alternative}\n\n\ndef upper_bound_zero_of_k(k: int, level: float = 0.90) -> float:\n    """One-sided upper bound on a per-direction escape probability when 0 of k escape."""\n    return float(1 - (1 - level) ** (1 / k)) if k > 0 else float("nan")'}
```

### [123] TOOL RESULT — NotebookEdit · 2026-10-26 11:12:04 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [124] TOOL CALL — NotebookEdit · 2026-10-26 11:12:04 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "## Pass cost and screen statistics (`src/stats.py`, part 2)\n\nA knob only matters if the programs still work.\n- **Pass cost** = 100 × (twin pass rate − arm pass rate), in percentage points. Its 95% interval is the Newcombe (1998, method 10) hybrid-score interval built from two Wilson intervals.\n- The screen summary uses a one-sided Fisher exact test and the balanced accuracy of *movable* against *avoidance ≥ 0.5*.\n- The power note `1 − 0.1^(1/K)` is the one-sided 90% upper bound on a task's per-direction escape probability when 0 of K directions escape.\n\nThe other functions in `src/stats.py`, such as the permutation Spearman, Poisson-binomial, kappa and jackknife, serve stages outside this demo."}
```

### [125] TOOL RESULT — NotebookEdit · 2026-10-26 11:12:04 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [126] ASSISTANT · 2026-10-26 11:13:02 UTC

```
Next batch: the Hill‑1 statistics (`src/stats.py` part 1), paths/labels, and the `eval.py` entry-point setup.
```

### [127] TOOL CALL — NotebookEdit · 2026-10-26 11:13:02 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'MASTER_SEED = 20261021\nDEPTH = 25\nDEPTH_LOW = 10\n# NOTEBOOK: N_RAREFY, N_BOOT and N_BOOT_RAREFY (originally 1000, 1000 and 200) are set in the config cell\n\n\ndef cell_seed(cell_id: str) -> int:\n    return int(hashlib.sha256(f"{MASTER_SEED}|{cell_id}".encode()).hexdigest()[:8], 16)\n\n\ndef hill1_counts(x: np.ndarray) -> float:\n    x = np.asarray(x, float)\n    x = x[x > 0]\n    if x.sum() <= 0:\n        return float("nan")\n    q = x / x.sum()\n    return float(math.exp(-(q * np.log(q)).sum()))\n\n\ndef _hill1_rows(draws: np.ndarray, depth: int) -> np.ndarray:\n    q = draws / depth\n    with np.errstate(divide="ignore", invalid="ignore"):\n        h = np.where(q > 0, q * np.log(np.where(q > 0, q, 1.0)), 0.0).sum(axis=1)\n    return np.exp(-h)\n\n\ndef rarefied_hill1(counts: Sequence[int], depth: int, n_draws: int, rng: np.random.Generator) -> float:\n    c = np.asarray([int(v) for v in counts if int(v) > 0], np.int64)\n    if c.sum() < depth or len(c) == 0:\n        return float("nan")\n    if len(c) == 1:\n        return 1.0\n    if c.sum() == depth:\n        return hill1_counts(c)\n    d = rng.multivariate_hypergeometric(c, depth, size=n_draws, method="marginals")\n    return float(_hill1_rows(d, depth).mean())\n\n\ndef goods_coverage(counts: Sequence[int]) -> float:\n    c = np.asarray([v for v in counts if v > 0])\n    n = c.sum()\n    if n == 0:\n        return float("nan")\n    f1 = int((c == 1).sum())\n    return float(1 - f1 / n)\n\n\ndef h1r_cell(correct_labels: Sequence[str], templates: Sequence[str] | None, cell_id: str, depth: int = DEPTH,\n             drop: Iterable[str] = (), n_boot: int = N_BOOT, n_boot_rarefy: int = N_BOOT_RAREFY,\n             with_ci: bool = True) -> dict:\n    """Correct-only rarefied Hill-1 for one cell; percentile CIs (template-cluster when eligible, and iid)."""\n    drop = set(drop)\n    keep = [i for i, l in enumerate(correct_labels) if l not in drop]\n    labs = [correct_labels[i] for i in keep]\n    tpls = [templates[i] for i in keep] if templates is not None else None\n    cats = sorted(set(labs))\n    idx = {c: i for i, c in enumerate(cats)}\n    counts = np.zeros(len(cats), np.int64)\n    for l in labs:\n        counts[idx[l]] += 1\n    n_c = int(counts.sum())\n    rng = np.random.default_rng(cell_seed(f"{cell_id}|d{depth}|{\'-\'.join(sorted(drop))}"))\n    out = {"n_c": n_c, "S_obs": int((counts > 0).sum()), "coverage": goods_coverage(counts),\n           "value": rarefied_hill1(counts, depth, N_RAREFY, rng), "ci90": [float("nan")] * 2,\n           "ci90_iid": [float("nan")] * 2, "ci_unit": None}\n    if not with_ci or n_c < depth or len(cats) <= 1:\n        if n_c >= depth and len(cats) == 1:\n            out["ci90"] = [1.0, 1.0]\n            out["ci90_iid"] = [1.0, 1.0]\n            out["ci_unit"] = "degenerate"\n        return out\n    # iid program bootstrap\n    probs = counts / n_c\n    vals = np.full(n_boot, np.nan)\n    for b in range(n_boot):\n        cb = rng.multinomial(n_c, probs)\n        vals[b] = rarefied_hill1(cb, depth, n_boot_rarefy, rng)\n    out["ci90_iid"] = [float(np.nanquantile(vals, 0.05)), float(np.nanquantile(vals, 0.95))]\n    out["ci90"] = list(out["ci90_iid"])\n    out["ci_unit"] = "program"\n    if tpls is not None:\n        by_t: dict[str, np.ndarray] = {}\n        for l, t in zip(labs, tpls):\n            by_t.setdefault(str(t), np.zeros(len(cats), np.int64))[idx[l]] += 1\n        tkeys = sorted(by_t)\n        if len(tkeys) == 5 and all(by_t[t].sum() >= 5 for t in tkeys):\n            mat = np.stack([by_t[t] for t in tkeys])\n            tv = np.full(n_boot, np.nan)\n            for b in range(n_boot):\n                pick = rng.integers(0, len(tkeys), len(tkeys))\n                tv[b] = rarefied_hill1(mat[pick].sum(0), depth, n_boot_rarefy, rng)\n            if np.isfinite(tv).sum() > 0.5 * n_boot:\n                out["ci90"] = [float(np.nanquantile(tv, 0.05)), float(np.nanquantile(tv, 0.95))]\n                out["ci_unit"] = "template(5 clusters; few-cluster)"\n    return out'}
```

### [128] TOOL RESULT — NotebookEdit · 2026-10-26 11:13:03 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [129] TOOL CALL — NotebookEdit · 2026-10-26 11:13:02 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "## Diversity statistic (`src/stats.py`, part 1)\n\nThe knob table's one statistic is **correct-only, rarefied Hill-1 at depth 25**. Take the algorithm labels of the programs that passed, draw 25 of them without replacement (`N_RAREFY` times), and average `exp(Shannon entropy)` of the label shares. The result is the effective number of distinct algorithms among 25 correct programs: 1.0 means every correct program uses the same algorithm, 2.0 means two equally common algorithms. Rarefying to a fixed depth makes cells with different numbers of correct programs comparable. Cells with fewer than 25 correct programs get no depth-25 value (`below_depth`) and report a depth-10 value instead.\n\n`h1r_cell` also returns:\n- Good's coverage, 1 − singletons / n;\n- a 90% percentile CI from an iid program bootstrap (`N_BOOT` replicates × `N_BOOT_RAREFY` rarefactions). When the cell has 5 prompt templates with ≥ 5 correct programs each, a template-cluster bootstrap replaces it.\n\nEvery cell draws from its own seed, `sha256('20261021|' + cell id)`, so results do not depend on the order in which cells are processed."}
```

### [130] TOOL RESULT — NotebookEdit · 2026-10-26 11:13:03 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [131] TOOL CALL — NotebookEdit · 2026-10-26 11:13:02 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '# ---- src/paths.py: artifact id -> short experiment name; \'<artifact_id>:<relative path>\' citations ----\n# artifact id -> (root env var, workspace folder, short experiment name)\nARTIFACTS: dict[str, tuple[str, str, str]] = {\n    "art_U5UKkFrOgSsE": ("AII_ITER1", "gen_art_experiment_4", "exp4"),\n    "art_UoCVh2Qe5RZ0": ("AII_ITER1", "gen_art_experiment_6", "exp6"),\n    "art_6zBfl3kDjeiP": ("AII_ITER2", "gen_art_experiment_7", "exp7"),\n    "art_IVZc3TWCeE9f": ("AII_ITER2", "gen_art_experiment_9", "exp9"),\n    "art_0ndRfWKBWclR": ("AII_ITER2", "gen_art_experiment_11", "exp11"),\n    "art_1AYTO1Epb_7t": ("AII_ITER3", "gen_art_experiment_13", "exp13"),\n    "art_WiY4wqHLb9Gy": ("AII_ITER3", "gen_art_experiment_14", "exp14"),\n    "art_Q-qh-9HhPoWo": ("AII_ITER3", "gen_art_experiment_15", "exp15"),\n    "art__5akZ9W9iZM4": ("AII_ITER3", "gen_art_experiment_16", "exp16"),\n    "art_pVlCZ272hDV7": ("AII_ITER3", "gen_art_experiment_17", "exp17"),\n    "art_ccAbfJVcv0LO": ("AII_ITER3", "gen_art_experiment_18", "exp18"),\n}\nBY_EXP = {v[2]: k for k, v in ARTIFACTS.items()}\n\n\ndef cite(exp_or_aid: str, rel: str) -> str:\n    aid = BY_EXP.get(exp_or_aid, exp_or_aid)\n    return f"{aid}:{rel}"\n\n\ndef exp_name(aid: str) -> str:\n    return ARTIFACTS[aid][2]\n\n\n# ---- src/labels.py (STEP G1): task lists, catalogues, defaults ----\nBENCH_DIRS = {\n    "T03": "T03_kth_smallest", "T04": "T04_substring_search", "T05": "T05_two_sum", "T06": "T06_find_duplicate",\n    "T08": "T08_fibonacci", "T10": "T10_connected_components", "T11": "T11_longest_increasing_subsequence",\n    "T13": "T13_merge_intervals", "T14": "T14_top_k_frequent", "R1": "R1_non_overlapping_intervals",\n    "R2": "R2_cycle_detection", "R3": "R3_topological_order", "R6": "R6_first_last_position",\n}\nBENCH12 = ["T03", "T04", "T05", "T06", "T08", "T10", "T11", "T13", "T14", "R1", "R3", "R6"]\nPATH_TASKS = ["T1", "T2"]\nQWEN14 = BENCH12 + PATH_TASKS\n\nT1_CATALOGUE = ["bfs", "dfs", "bibfs", "iddfs", "astar", "gbfs", "idastar", "dijkstra_unit"]\nT2_CATALOGUE = ["dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"]\n\nQWEN_DEFAULT = {\n    "T03": "full_sort", "T04": "naive", "T05": "hash_map", "T06": "hash_set", "T08": "iteration", "T10": "union_find",\n    "T11": "quadratic_dp", "T13": "sort_sweep", "T14": "sort_by_count", "R1": "greedy_end", "R3": "kahn",\n    "R6": "binary_search", "T1": "bfs", "T2": "dijkstra",\n}\n\n\n@lru_cache(maxsize=None)\ndef spec(task: str) -> dict:\n    # NOTEBOOK: was json.loads(p("exp11", f"bench/{BENCH_DIRS[task]}/spec.json").read_text()); the demo data carries the\n    # catalogues of the screened bench tasks\n    return data["metadata"]["task_specs"][task]\n\n\n@lru_cache(maxsize=None)\ndef catalogue(task: str) -> tuple[str, ...]:\n    if task == "T1":\n        return tuple(T1_CATALOGUE)\n    if task == "T2":\n        return tuple(T2_CATALOGUE)\n    return tuple(c["mode"] for c in spec(task)["catalogue"])\n\n\ndef default_of(task: str, model: str = "qwen") -> str | None:\n    # NOTEBOOK: the Llama branch reads exp15 results/c1_events.jsonl (llama_defaults, not shipped); every demo cell is Qwen\n    if "llama" in model.lower():\n        return llama_defaults().get(task)\n    return QWEN_DEFAULT.get(task)\n\n\nfor _t in ("T1", "T03", "T10", "T13", "T14"):\n    print(f"{_t}: default {default_of(_t)!r}; catalogue {list(catalogue(_t))}")'}
```

### [132] TOOL RESULT — NotebookEdit · 2026-10-26 11:13:03 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [133] TOOL CALL — NotebookEdit · 2026-10-26 11:13:02 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "## Artifact ids and label catalogues (`src/paths.py`, `src/labels.py`)\n\nEvery output cites its source as `<artifact_id>:<relative path>`. `ARTIFACTS` maps the 11 dependency artifacts to their short experiment names, exp4 to exp18.\n\n`src/labels.py` (step G1) holds the task lists, each task's **catalogue** of known algorithms, and the model's **default** algorithm. For T1, path search, the default is BFS.\n- The bench catalogues come from exp11's `bench/<task>/spec.json`. The demo data carries those of the screened bench tasks, so `spec()` reads them from `data` instead of the file system.\n- Two kinds of code are left out because the demo rows are already normalised: the functions that locate dependency folders on disk (`root`, `p`), and the label-normalisation helpers that only the `rows` stage uses."}
```

### [134] TOOL RESULT — NotebookEdit · 2026-10-26 11:13:03 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [135] TOOL CALL — NotebookEdit · 2026-10-26 11:13:02 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '# eval.py: "Iteration-4 Step 0: record repair and frozen push screen. Single entry point with stage flags."\n# NOTEBOOK: WS was Path(__file__).resolve().parent (the artifact folder); here it is the config cell\'s output folder\nWS.mkdir(exist_ok=True)\n\nlogger.remove()\nlogger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")\nlogger.add(WS / "logs" / "eval.log", rotation="30 MB", level="DEBUG")\n\nSTAGES = ["inventory", "rows", "judges", "knob", "screen", "route", "llama", "other", "figures", "rigor", "wording", "rivals",\n          "audit", "outputs"]\n\n\ndef _limit_memory(gb: float = 18.0) -> None:\n    try:\n        resource.setrlimit(resource.RLIMIT_AS, (int(gb * 1024 ** 3), int(gb * 1024 ** 3)))\n    except (ValueError, OSError) as e:\n        logger.warning(f"could not set RLIMIT_AS: {e}")\n\n\n# src/stages.py: "Stage implementations called by eval.py. Each stage reads earlier stages\' outputs from data/ and results/."\nDATA = WS / "data"\nRES = WS / "results"\nTAB = WS / "tables"\nfor _d in (DATA, RES, TAB, WS / "figures", WS / "audit"):\n    _d.mkdir(exist_ok=True)'}
```

### [136] TOOL RESULT — NotebookEdit · 2026-10-26 11:13:03 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [137] TOOL CALL — NotebookEdit · 2026-10-26 11:13:03 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "## `eval.py` entry point: logging, stage list, memory cap\n\n`eval.py` is a single entry point with stage flags (`uv run eval.py --stages all`). Each stage reads earlier stages' outputs from `data/` and `results/`. The cell below holds its logger setup, the stage list and the address-space cap, plus the output folders that `src/stages.py` creates.\n\nOf the 14 stages, only `knob` and `screen` are defined in this notebook. The other twelve read files of the 11 dependency artifacts or the LLM-judge cache, which the demo data does not ship: `inventory`, `rows`, `judges`, `route`, `llama`, `other`, `figures`, `rigor`, `wording`, `rivals`, `audit` and `outputs`."}
```

### [138] TOOL RESULT — NotebookEdit · 2026-10-26 11:13:03 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [139] ASSISTANT · 2026-10-26 11:13:45 UTC

```
Final batch: config, data loading, imports, install cell and the title.
```

### [140] TOOL CALL — NotebookEdit · 2026-10-26 11:13:45 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '# ---- tunable parameters (the original values are in the comments) ----\n# Monte-Carlo sizes of src/stats.py (original: N_RAREFY = 1000, N_BOOT = 1000, N_BOOT_RAREFY = 200)\nN_RAREFY = 10        # rarefaction subsamples per Hill-1 value\nN_BOOT = 10          # bootstrap replicates per 90% CI\nN_BOOT_RAREFY = 10   # rarefaction subsamples inside each bootstrap replicate\n# data size (original: all 1,120 cells of data/rows.parquet; mini_demo_data.json holds 99 of them)\nN_CELLS = 6          # first N demo cells, at least 6 (the first 6 are the complete T10 screen group); 99 = all\n# eval.py --stages (original default: all 14 stages; only these two run from the demo data)\nRUN_STAGES = ["knob", "screen"]\n# output folder (the original wrote into the artifact folder: data/, tables/, results/, screen.json, logs/)\nWS = Path("demo_run")'}
```

### [141] TOOL RESULT — NotebookEdit · 2026-10-26 11:13:45 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [142] TOOL CALL — NotebookEdit · 2026-10-26 11:13:45 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': '## Configuration\n\nAll tunable parameters are set here; re-run the notebook from this cell after changing them.\n- `N_RAREFY`, `N_BOOT` and `N_BOOT_RAREFY` are the Monte-Carlo sizes of `src/stats.py`. With the original values (1000 / 1000 / 200) and the original per-cell seeds, every Hill-1 value and CI is recomputed exactly. Smaller values run faster and give Hill-1 values within Monte-Carlo error of the recorded ones.\n- Pass rates, pass costs, coverage, avoidance shares and the screen itself are exact at any setting, because they are counts.\n- `N_CELLS` takes the first cells of the demo data. The cells are ordered in groups, with each twin before the cells priced against it, so any prefix of at least 6 cells is self-consistent.'}
```

### [143] TOOL RESULT — NotebookEdit · 2026-10-26 11:13:45 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [144] TOOL CALL — NotebookEdit · 2026-10-26 11:13:45 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'data = load_data()\nexamples = data["datasets"][0]["examples"]\nprint(f"dataset {data[\'datasets\'][0][\'dataset\']!r}: {len(examples)} cells, "\n      f"{sum(len(e[\'metadata_programs\'][\'label_norm\']) for e in examples)} labelled program rows")\nfor g in data["metadata"]["groups"]:\n    print(f"  {g[\'group\']:<11} {g[\'n_cells\']:>3} cells  {g[\'note\']}")'}
```

### [145] TOOL RESULT — NotebookEdit · 2026-10-26 11:13:45 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [146] TOOL CALL — NotebookEdit · 2026-10-26 11:13:45 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-4/evaluation-3/demo/mini_demo_data.json"\nimport http.client\nimport json\nimport urllib.request\nfrom pathlib import Path\n\ndef load_data():\n    try:\n        with urllib.request.urlopen(GITHUB_DATA_URL, timeout=15) as response:\n            return json.loads(response.read().decode())\n    # Network errors, timeouts, a placeholder URL, bad JSON, a cut-off response.\n    except (OSError, ValueError, http.client.HTTPException) as e:\n        print("GitHub data unavailable, using local mini_demo_data.json:", e)\n    local = Path("mini_demo_data.json")\n    if local.exists(): return json.loads(local.read_text())\n    raise FileNotFoundError("Could not load mini_demo_data.json")'}
```

### [147] TOOL RESULT — NotebookEdit · 2026-10-26 11:13:45 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [148] TOOL CALL — NotebookEdit · 2026-10-26 11:13:45 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'from __future__ import annotations\n\n# --- original imports (eval.py, src/stages.py, src/stats.py, src/labels.py, src/knob.py, src/screen.py, screen_rule.py) ---\nimport argparse\nimport hashlib\nimport importlib.util\nimport itertools\nimport json\nimport math\nimport multiprocessing as mp\nimport re\nimport resource\nimport sys\nimport time\nfrom collections import Counter\nfrom concurrent.futures import ProcessPoolExecutor\nfrom functools import lru_cache\nfrom pathlib import Path\nfrom typing import Any, Iterable, Sequence\n\nimport numpy as np\nimport pandas as pd\nfrom loguru import logger\nfrom scipy import stats as sps\n\n# --- notebook additions: a namespace standing in for the screen_rule.py module, tables and figures ---\nimport types\n\nimport matplotlib.pyplot as plt\nfrom IPython.display import display\nfrom matplotlib.lines import Line2D'}
```

### [149] TOOL RESULT — NotebookEdit · 2026-10-26 11:13:45 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [150] TOOL CALL — NotebookEdit · 2026-10-26 11:13:45 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': "import subprocess, sys\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\n\n# loguru — NOT pre-installed on Colab, always install\n_pip('loguru==0.7.3')\n\n# numpy, pandas, scipy, matplotlib, pyarrow — pre-installed on Colab, install locally only (Colab's exact versions)\nif 'google.colab' not in sys.modules:\n    _pip('numpy==2.0.2', 'pandas==2.2.2', 'scipy==1.16.3', 'matplotlib==3.10.0', 'pyarrow==18.1.0')"}
```

### [151] TOOL RESULT — NotebookEdit · 2026-10-26 11:13:45 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [152] TOOL CALL — NotebookEdit · 2026-10-26 11:13:45 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': '# Record repair and a frozen push screen: knob table and push-movability screen (demo)\n\n**Artifact `art_sV0cQ3ef1ZRQ`** (evaluation) is the CPU-only Step 0 of iteration 4 of a study on *algorithm choice* in Qwen3-8B, with Llama-3.1-8B as the replication model. The study asks how "creativity" shows up, meaning a program written with a different algorithm than the model\'s default, and which knob actually moves it. The candidates are temperature, context seeds, instructions ("make a fully novel algorithm…"), prompt bans, token vetoes and directions added in activation space.\n\nThis step generates no model text. It recomputes every number from **labelled program rows** of 11 earlier experiments. Each program is labelled with:\n- the algorithm it implements;\n- whether it passed the hidden tests;\n- whether that algorithm is in the task\'s catalogue of known algorithms;\n- whether it is the model\'s default.\n\nThe original entry point `eval.py` runs 14 stages from `src/`. This notebook runs the two central ones on a curated subset, with the original code split into cells. Every change is marked `NOTEBOOK:`.\n\n| Stage | What it computes |\n|---|---|\n| `knob` | The **one-statistic knob table**. For every artifact × task × arm × dial cell: the correct-only **rarefied Hill-1 at depth 25** (`H1r25`, the effective number of distinct algorithms among 25 correct programs) with 90% bootstrap CIs, Good\'s coverage, the **pass cost** against the cell\'s own twin (Newcombe 95% CI), the off-default share, the catalogue-only avoidance, and the escape and qualify flags. |\n| `screen` | The **frozen push-movability screen**. A random activation direction *escapes* if it raises the off-default share by at least 0.20 over its twin while keeping pass ≥ 0.8 × twin. A task is *movable* if any direction escapes at α ≤ 2. The screen rule says *movable ⇒ catalogue-only modal-ban avoidance ≥ 0.5*. |\n\n**Demo data** (`mini_demo_data.json`) holds 99 of the 1,120 knob-table cells and the 6,925 labelled program rows behind them, in two parts:\n- the complete screen input of tasks T10, T13, T14, T03 and T1;\n- every kind of knob the study tried on the path-search task **T1**, "implement a path search algorithm", which asks whether the model always writes BFS.\n\nEach cell carries its recorded values, so every recomputed number is checked against the artifact.'}
```

### [153] TOOL RESULT — NotebookEdit · 2026-10-26 11:13:45 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [154] ASSISTANT · 2026-10-26 11:13:53 UTC

```
All cells inserted. Let me verify the final cell order, and check which libraries the system Python has for a quick pre-flight run of the code cells.
```

### [155] TOOL CALL — Bash · 2026-10-26 11:13:53 UTC

```
Verify notebook cell order and system libraries:
python3 -c "
import json; nb=json.load(open('code_demo.ipynb'))
for i,c in enumerate(nb['cells']): print(i, c['id'], c['cell_type'][:4], ''.join(c['source']).splitlines()[0][:100])"; python3 -c "import loguru, IPython, matplotlib, scipy; print('loguru', loguru.__version__, 'IPython', IPython.__version__, 'mpl', matplotlib.__version__, 'scipy', scipy.__version__)" 2>&1
```

### [156] TOOL RESULT — Bash [ERROR] · 2026-10-26 11:13:53 UTC

```
Error: Exit code 1
0 07a9bc8c mark # Record repair and a frozen push screen: knob table and push-movability screen (demo)
1 83c176e2 code import subprocess, sys
2 af9b6202 code from __future__ import annotations
3 a8cd780b code GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-b
4 1f982e57 code data = load_data()
5 15250ae9 mark ## Configuration
6 10ec93e8 code # ---- tunable parameters (the original values are in the comments) ----
7 f1f869d0 mark ## `eval.py` entry point: logging, stage list, memory cap
8 1bfc9c45 code # eval.py: "Iteration-4 Step 0: record repair and frozen push screen. Single entry point with stage 
9 707527e0 mark ## Artifact ids and label catalogues (`src/paths.py`, `src/labels.py`)
10 cb09d0d1 code # ---- src/paths.py: artifact id -> short experiment name; '<artifact_id>:<relative path>' citations
11 83206e8a mark ## Diversity statistic (`src/stats.py`, part 1)
12 51252419 code MASTER_SEED = 20261021
13 6457f7ec mark ## Pass cost and screen statistics (`src/stats.py`, part 2)
14 177ddc6b code def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
15 12e887fe mark ## Labelled program rows (replaces the `rows` stage and `data/rows.parquet`)
16 fc0844f5 code def rows_from_data(data: dict, n_cells: int) -> pd.DataFrame:
17 4b713e47 mark ## Arm dictionary and own-twin pricing (`src/knob.py`, part 1)
18 a8280e10 code NONCAT_DROP_MARK = "__noncat__"
19 33e6d80f mark ## One row per cell (`src/knob.py`, part 2)
20 02b9c4bb code # ------------------------------------------------------------------------------------------------ c
21 e15a0241 mark ## Stage `knob` (`src/stages.py`)
22 9eb4d4f7 code def stage_knob() -> None:
23 ef253816 mark ## The frozen screen rule (`screen_rule.py`, standard library only)
24 acd978bf code # screen_rule.py: "Push-movability screen rule (stdlib only), so parallel artifacts can recompute sc
25 937488c4 mark ## Screen inputs from the knob table (`src/screen.py`, part 1)
26 d7e61955 code C1_SET = ["T03", "T05", "T06", "T10", "T1", "T2"]
27 67147c2e mark ## Stage `screen` (`src/screen.py`, part 2)
28 f449899e code def run_screen_stage() -> None:
29 609b176a mark ## Run the stages (`eval.py` `main`)
30 a857bd5f code @logger.catch(reraise=True)
31 754b1dbf mark ## Results 1: the recomputed knob table against the recorded artifact
32 e3db4c35 code knob = pd.read_parquet(DATA / "knob.parquet")
33 33645481 mark ## Results 2: the push screen against the frozen `screen.json`
34 da154212 code screen = json.loads((WS / "screen.json").read_text())
35 9b595dbb mark ## Visualization
36 1c8d802c code # (a) knob map of the path-search task T1, (b) escape geometry of the random directions, (c) the scr
37 summary mark ## Summary and scaling
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'IPython'
```

### [157] ASSISTANT · 2026-10-26 11:14:07 UTC

```
Cell order is correct (38 cells). System Python lacks IPython, so I'll go straight to the official clean-venv test with the minimum config (6 cells, N=10/10/10), timing the run.
```

### [158] TOOL CALL — Bash · 2026-10-26 11:14:07 UTC

```
Run notebook test in clean venv with minimum config:
T0=$(date +%s) && UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_sV0cQ3ef1ZRQ-ad6af5bda702 && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_sV0cQ3ef1ZRQ-ad6af5bda702/bin/python jupyter ipykernel && T1=$(date +%s) && /tmp/aii_nb_test_envs/art_sV0cQ3ef1ZRQ-ad6af5bda702/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | tail -30; echo "venv setup: $((T1-T0))s, notebook run: $(( $(date +%s)-T1 ))s"
```

### [159] TOOL RESULT — Bash · 2026-10-26 11:14:25 UTC

```
{"stdout": "[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[IPKernelApp] WARNING | Kernel is running over TCP without encryption. All communication (including code and outputs) is sent in plain text and is susceptible to eavesdropping. Use IPC transport or launch with kernel manager-provisioned CurveZMQ keys to enable transport encryption.\n[NbConvertApp] Writing 329612 bytes to code_demo.ipynb\nvenv setup: 2s, notebook run: 17s", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [160] ASSISTANT · 2026-10-26 11:14:33 UTC

```
Minimum config passed in 17 s. Let me inspect the cell outputs (text only) to check correctness, not just completion.
```

### [161] TOOL CALL — Bash · 2026-10-26 11:14:33 UTC

```
Print text outputs of executed notebook cells:
python3 - <<'EOF'
import json
nb=json.load(open('code_demo.ipynb'))
for i,c in enumerate(nb['cells']):
    if c['cell_type']!='code': continue
    for o in c.get('outputs',[]):
        t=o.get('output_type')
        if t=='stream': txt=''.join(o['text'])
        elif t in('execute_result','display_data'):
            d=o['data']; txt=''.join(d.get('text/plain','')) if 'image/png' not in d else '<image/png>'
        elif t=='error': txt='ERROR '+o['ename']+': '+o['evalue']
        else: txt=t
        print(f'--- cell {i} [{t}]'); print(txt[:3000])
EOF
```

### [162] TOOL RESULT — Bash · 2026-10-26 11:14:33 UTC

```
{"stdout": "--- cell 4 [stream]\nGitHub data unavailable, using local mini_demo_data.json: HTTP Error 404: Not Found\ndataset 'knob_table': 99 cells, 6925 labelled program rows\n  screen:T10    6 cells  connected components: exp13 bf16 random directions rand1-3, their HF twin, the modal ban and its vLLM twin\n  screen:T13    6 cells  merge intervals (immovable): exp13 random directions, HF twin, modal ban and vLLM twin\n  screen:T14    6 cells  top-k frequent (immovable; modal ban Hill 1.78 at 17 pts): exp13 random directions, twins, modal ban\n  screen:T03   25 cells  k-th smallest: exp13 rand1-3 + exp17 RAND90xx directions at alpha 1 and 2, both twins, the modal ban\n  screen:T1    21 cells  path search: exp17 RAND90xx directions at alpha 1 and 2 and their twin; exp9 single BFS ban and its baseline\n  knobs:T1     32 cells  path search: temperature x sampler grid, context seeds, creativity instructions, generate-then-select, top-k / list bans, decommitment and random steering, token vetoes, 2,000-word novelty instruction\n  knobs:T03     3 cells  k-th smallest: novelty instruction, nonce ban and one-shot token veto (exp13)\n\n--- cell 10 [stream]\nT1: default 'bfs'; catalogue ['bfs', 'dfs', 'bibfs', 'iddfs', 'astar', 'gbfs', 'idastar', 'dijkstra_unit']\nT03: default 'full_sort'; catalogue ['full_sort', 'size_k_heap', 'heapify_pop', 'quickselect', 'median_of_medians', 'counting_sort']\nT10: default 'union_find'; catalogue ['bfs', 'dfs', 'union_find', 'label_propagation']\nT13: default 'sort_sweep'; catalogue ['sort_sweep', 'interval_tree', 'union_find']\nT14: default 'sort_by_count'; catalogue ['sort_by_count', 'heap', 'bucket_sort', 'quickselect_counts']\n\n--- cell 16 [stream]\n350 labelled program rows in 6 cells\n\n--- cell 16 [display_data]\n        artifact_id task      arm dial precision            src_file  \\\n0  art_1AYTO1Epb_7t  T10  hf_twin   {}      bf16  data/samples.jsonl   \n1  art_1AYTO1Epb_7t  T10  hf_twin   {}      bf16  data/samples.jsonl   \n2  art_1AYTO1Epb_7t  T10  hf_twin   {}      bf16  data/samples.jsonl   \n3  art_1AYTO1Epb_7t  T10  hf_twin   {}      bf16  data/samples.jsonl   \n4  art_1AYTO1Epb_7t  T10  hf_twin   {}      bf16  data/samples.jsonl   \n\n           model engine template  label_norm  is_catalogue  is_default  \\\n0  Qwen/Qwen3-8B     hf       W1  union_find          True        True   \n1  Qwen/Qwen3-8B     hf       W1  union_find          True        True   \n2  Qwen/Qwen3-8B     hf       W1  union_find          True        True   \n3  Qwen/Qwen3-8B     hf       W1  union_find          True        True   \n4  Qwen/Qwen3-8B     hf       W1  union_find          True        True   \n\n   attempted  passed  \n0       True    True  \n1       True    True  \n2       True    True  \n3       True    True  \n4       True    True  \n--- cell 30 [stream]\n11:14:23|INFO   |=== stage knob ===\n\n--- cell 30 [stream]\n11:14:23|INFO   |knob table: 6 cells; computing rarefied Hill-1 with 1 workers\n\n--- cell 30 [stream]\n11:14:23|INFO   |knob table: 6 rows -> tables/knob_table.csv\n\n--- cell 30 [stream]\n11:14:23|INFO   |=== stage knob done in 0.1s ===\n\n--- cell 30 [stream]\n11:14:23|INFO   |=== stage screen ===\n\n--- cell 30 [stream]\n11:14:23|INFO   |screen.json sha256 aade7ffb4521288e7735dbd5d46337e4b0ecf0ec82bff4d82e2827c94dfe9596; movable ['T10']\n\n--- cell 30 [stream]\n11:14:23|INFO   |=== stage screen done in 0.1s ===\n\n--- cell 30 [stream]\nstages ['knob', 'screen'] finished in 0.2s; outputs in demo_run/\n\n--- cell 32 [stream]\n6 cells recomputed with N_RAREFY = 10, N_BOOT = 10, N_BOOT_RAREFY = 10\n\n--- cell 32 [display_data]\n                column            kind  cells  identical  \\\n0            pass_rate  counts (exact)      6          6   \n1        pass_cost_pts  counts (exact)      6          6   \n2         offdef_share  counts (exact)      6          6   \n3   cat_only_avoidance  counts (exact)      6          6   \n4             coverage  counts (exact)      6          6   \n5                S_obs  counts (exact)      6          6   \n6                H1r25     Monte Carlo      6          4   \n7            H1r25_cat     Monte Carlo      6          4   \n8                H1r10     Monte Carlo      6          6   \n9           H1r25_ci90     Monte Carlo      6          4   \n10      H1r25_ci90_iid     Monte Carlo      6          4   \n11      pass_cost_ci95  counts (exact)      6          6   \n12              escape  counts (exact)      6          6   \n13             qualify     Monte Carlo      6          6   \n\n    max |recomputed - recorded|  \n0                      0.000000  \n1                      0.000000  \n2                      0.000000  \n3                      0.000000  \n4                      0.000000  \n5                      0.000000  \n6                      0.098892  \n7                      0.047078  \n8                      0.000000  \n9                      0.063200  \n10                     0.037300  \n11                     0.000000  \n12                     0.000000  \n13                     0.000000  \n--- cell 32 [stream]\n\nPath-search task T1: 0 knob and twin cells (exp17 random directions are in the screen below)\n\n--- cell 32 [display_data]\nEmpty DataFrame\nColumns: [group, exp, arm, family, n, pass, cost_pts, H1r25, H1r25_recorded, CI90, coverage, offdef, cat_only, escape, qualify]\nIndex: []\n--- cell 34 [display_data]\n  task alpha 1 escape/run alpha 2 escape/run  movable push_top1  push_landing  \\\n0  T10                1/3                0/0        1       dfs  {'dfs': 1.0}   \n\n   cat-only ban avoidance  avoidance >= 0.5 escaping engines  \\\n0                     1.0              True          hf-bf16   \n\n   identical to frozen record  \n0                        True  \n--- cell 34 [stream]\nmovable x (avoidance >= 0.5) on the 1 screened tasks: table [[1, 0], [0, 0]], one-sided Fisher p = 1, balanced accuracy nan (descriptive only: screen, not confirmation (rule read off the same data))\nfrozen screen (all 14 tasks): movable ['T03', 'T05', 'T06', 'T1', 'T10', 'T2']; C1 event set ['T03', 'T05', 'T06', 'T1', 'T10', 'T2']\npublished screen.json sha256           d6a2ca9711f461973c39482314a523d448d0590cb40e32432826dec1da4846e8\nwith the 1 recomputed task records  d6a2ca9711f461973c39482314a523d448d0590cb40e32432826dec1da4846e8  -> byte-identical\n\n--- cell 36 [display_data]\n<image/png>", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [163] THINKING · 2026-10-26 11:14:51 UTC

```
The minimum config checks out fully — count-based columns match exactly, Monte-Carlo values are within expected noise, and the T10 screen hash matches byte-for-byte. Next, I'll patch the config cell's source directly to run scaling round 1 across all 99 cells with Monte-Carlo sizes ×10.
```

### [164] TOOL CALL — Bash · 2026-10-26 11:14:51 UTC

```
Scale config to 99 cells and N 100/100/50, re-run:
python3 - <<'EOF'
import json, re
p='code_demo.ipynb'; nb=json.load(open(p))
c=[c for c in nb['cells'] if c['id']=='10ec93e8'][0]
s=''.join(c['source'])
s=re.sub(r'^N_RAREFY = \d+ ', 'N_RAREFY = 100', s, flags=re.M)
s=re.sub(r'^N_BOOT = \d+ ', 'N_BOOT = 100', s, flags=re.M)
s=re.sub(r'^N_BOOT_RAREFY = \d+ ', 'N_BOOT_RAREFY = 50', s, flags=re.M)
s=re.sub(r'^N_CELLS = \d+ ', 'N_CELLS = 99', s, flags=re.M)
c['source']=s.splitlines(keepends=True)
json.dump(nb, open(p,'w'), indent=1, ensure_ascii=False); open(p,'a').write('\n')
print(s)
EOF
T1=$(date +%s); /tmp/aii_nb_test_envs/art_sV0cQ3ef1ZRQ-ad6af5bda702/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | grep -v WARNING | tail -5; echo "notebook run: $(( $(date +%s)-T1 ))s"
```

### [165] TOOL RESULT — Bash · 2026-10-26 11:14:55 UTC

```
{"stdout": "# ---- tunable parameters (the original values are in the comments) ----\n# Monte-Carlo sizes of src/stats.py (original: N_RAREFY = 1000, N_BOOT = 1000, N_BOOT_RAREFY = 200)\nN_RAREFY = 100       # rarefaction subsamples per Hill-1 value\nN_BOOT = 100         # bootstrap replicates per 90% CI\nN_BOOT_RAREFY = 50  # rarefaction subsamples inside each bootstrap replicate\n# data size (original: all 1,120 cells of data/rows.parquet; mini_demo_data.json holds 99 of them)\nN_CELLS = 99         # first N demo cells, at least 6 (the first 6 are the complete T10 screen group); 99 = all\n# eval.py --stages (original default: all 14 stages; only these two run from the demo data)\nRUN_STAGES = [\"knob\", \"screen\"]\n# output folder (the original wrote into the artifact folder: data/, tables/, results/, screen.json, logs/)\nWS = Path(\"demo_run\")\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[NbConvertApp] Writing 460020 bytes to code_demo.ipynb\nnotebook run: 6s", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [166] ASSISTANT · 2026-10-26 11:15:03 UTC

```
Round 1 ran in 6 s (venv reused, so installs were no-ops — the final test will use a fresh venv). Let me check the results at this scale.
```

### [167] TOOL CALL — Bash · 2026-10-26 11:15:03 UTC

```
Print stage, comparison and screen outputs:
python3 - <<'EOF'
import json
nb=json.load(open('code_demo.ipynb'))
for i,c in enumerate(nb['cells']):
    if c['cell_type']!='code' or i not in (30,32,34): continue
    for o in c.get('outputs',[]):
        t=o.get('output_type')
        if t=='stream': txt=''.join(o['text'])
        elif t in('execute_result','display_data'):
            d=o['data']; txt=''.join(d.get('text/plain','')) if 'image/png' not in d else '<image/png>'
        elif t=='error': txt='ERROR '+o['ename']+': '+o['evalue']
        else: txt=t
        print(f'--- cell {i} [{t}]'); print(txt[:6000])
EOF
```

### [168] TOOL RESULT — Bash · 2026-10-26 11:15:03 UTC

```
{"stdout": "--- cell 30 [stream]\n11:14:51|INFO   |=== stage knob ===\n\n--- cell 30 [stream]\n11:14:51|INFO   |knob table: 99 cells; computing rarefied Hill-1 with 1 workers\n\n--- cell 30 [stream]\n11:14:51|INFO   |knob table: 99 rows -> tables/knob_table.csv\n\n--- cell 30 [stream]\n11:14:51|INFO   |=== stage knob done in 0.3s ===\n\n--- cell 30 [stream]\n11:14:51|INFO   |=== stage screen ===\n\n--- cell 30 [stream]\n11:14:51|INFO   |screen.json sha256 7c0777dc107d36726918e7c6ab3d03e4e7411ce5f19c439cdabe2de5cedb6191; movable ['T03', 'T1', 'T10']\n\n--- cell 30 [stream]\n11:14:51|INFO   |=== stage screen done in 0.1s ===\n\n--- cell 30 [stream]\nstages ['knob', 'screen'] finished in 0.5s; outputs in demo_run/\n\n--- cell 32 [stream]\n99 cells recomputed with N_RAREFY = 100, N_BOOT = 100, N_BOOT_RAREFY = 50\n\n--- cell 32 [display_data]\n                column            kind  cells  identical  \\\n0            pass_rate  counts (exact)     99         99   \n1        pass_cost_pts  counts (exact)     99         99   \n2         offdef_share  counts (exact)     99         99   \n3   cat_only_avoidance  counts (exact)     99         99   \n4             coverage  counts (exact)     99         99   \n5                S_obs  counts (exact)     99         99   \n6                H1r25     Monte Carlo     99         56   \n7            H1r25_cat     Monte Carlo     99         57   \n8                H1r10     Monte Carlo     99         95   \n9           H1r25_ci90     Monte Carlo     99         56   \n10      H1r25_ci90_iid     Monte Carlo     99         56   \n11      pass_cost_ci95  counts (exact)     99         99   \n12              escape  counts (exact)     99         99   \n13             qualify     Monte Carlo     99         99   \n\n    max |recomputed - recorded|  \n0                      0.000000  \n1                      0.000000  \n2                      0.000000  \n3                      0.000000  \n4                      0.000000  \n5                      0.000000  \n6                      0.044941  \n7                      0.048202  \n8                      0.022216  \n9                      0.094100  \n10                     0.097100  \n11                     0.000000  \n12                     0.000000  \n13                     0.000000  \n--- cell 32 [stream]\n\nPath-search task T1: 35 knob and twin cells (exp17 random directions are in the screen below)\n\n--- cell 32 [display_data]\n        group    exp                                                arm  \\\n0    knobs:T1   exp4                steer:rand1 {\"c\": 0.1, \"layer\": 18}   \n1    knobs:T1   exp4                  steer:dc {\"c\": 0.25, \"layer\": 18}   \n2    knobs:T1   exp6  A1:baseline {\"T\": 0.3, \"sampler\": \"topk10\", \"t...   \n3    knobs:T1   exp6  A1:baseline {\"T\": 0.3, \"sampler\": \"topp095\", \"...   \n4    knobs:T1   exp6  A1:baseline {\"T\": 0.7, \"sampler\": \"topp095\", \"...   \n5    knobs:T1   exp6  A1:baseline {\"T\": 1.0, \"sampler\": \"topp095\", \"...   \n6    knobs:T1   exp6  A1:baseline {\"T\": 0.7, \"sampler\": \"topk10\", \"t...   \n7    knobs:T1   exp6  A1:baseline {\"T\": 1.0, \"sampler\": \"topk10\", \"t...   \n8    knobs:T1   exp6  A1:baseline {\"T\": 1.3, \"sampler\": \"topp095\", \"...   \n9    knobs:T1   exp6  A1:baseline {\"T\": 1.3, \"sampler\": \"topk10\", \"t...   \n10   knobs:T1   exp6  A4s2:gen_then_select {\"T\": 1.0, \"sampler\": \"pu...   \n11   knobs:T1   exp4                                       succession:2   \n12   knobs:T1   exp4                                            ban:bfs   \n13   knobs:T1  exp18                              two_step:TWO(bfs,dfs)   \n14  screen:T1   exp9                                         single:bfs   \n15   knobs:T1   exp6  A3:instr_creative {\"T\": 1.0, \"sampler\": \"pure\"...   \n16   knobs:T1   exp6  A3:instr_enumerate {\"T\": 1.0, \"sampler\": \"pure...   \n17   knobs:T1   exp6  A3:instr_new_algo {\"T\": 1.0, \"sampler\": \"pure\"...   \n18   knobs:T1   exp6  A3:instr_fully_novel {\"T\": 1.0, \"sampler\": \"pu...   \n19   knobs:T1  exp18                   longform:LF1 {\"thinking\": false}   \n20   knobs:T1   exp9                                      multi:SCATTER   \n21   knobs:T1   exp9                                         multi:TOP5   \n22   knobs:T1   exp9                                          multi:ARC   \n23   knobs:T1   exp9                                          multi:TOP   \n24   knobs:T1   exp6  A2:seed_entropy {\"T\": 1.0, \"sampler\": \"pure\", ...   \n25   knobs:T1   exp6  A2:seed_word {\"T\": 1.0, \"sampler\": \"pure\", \"th...   \n26   knobs:T1   exp6  A2:seed_semantic {\"T\": 1.0, \"sampler\": \"pure\",...   \n27   knobs:T1  exp18                                               sham   \n28  screen:T1  exp17                                            NEUTRAL   \n29   knobs:T1  exp18                                          walk_twin   \n30   knobs:T1   exp4                                           baseline   \n31   knobs:T1   exp4                   steer:dc {\"c\": 0.0, \"layer\": 18}   \n32   knobs:T1   exp6  A0:baseline {\"T\": 1.0, \"sampler\": \"pure\", \"thi...   \n33  screen:T1   exp9                                           baseline   \n34   knobs:T1  exp18                                         fixed_top5   \n\n                   family    n   pass  cost_pts  H1r25  H1r25_recorded  \\\n0       activation-random  100  0.980       2.0  1.000           1.000   \n1   activation-structured  100  0.570      43.0  1.000           1.000   \n2                decoding  100  1.000      -3.0  1.000           1.000   \n3                decoding  100  1.000      -3.0  1.000           1.000   \n4                decoding  100  1.000      -3.0  1.000           1.000   \n5                decoding  100  1.000      -3.0  1.000           1.000   \n6                decoding  100  0.980      -1.0  1.000           1.000   \n7                decoding  100  0.980      -1.0  1.000           1.000   \n8                decoding  100  0.970       0.0  1.000           1.000   \n9                decoding  100  0.950       2.0  1.057           1.044   \n10   generate_then_select  100  0.550      42.0  3.340           3.358   \n11             prompt:ban  100  0.880      12.0  2.181           2.187   \n12             prompt:ban  100  0.640      36.0  1.930           1.949   \n13             prompt:ban  100  0.540      38.0  1.908           1.895   \n14             prompt:ban  100  0.410      48.0  1.785           1.776   \n15     prompt:instruction  100  1.000      -3.0  1.000           1.000   \n16     prompt:instruction  100  0.990      -2.0  1.000           1.000   \n17     prompt:instruction  100  0.940       3.0  1.100           1.100   \n18     prompt:instruction  100  0.850      12.0  1.223           1.229   \n19     prompt:instruction   25  0.280      64.0    NaN             NaN   \n20            prompt:list  100  0.750      14.0  2.146           2.101   \n21            prompt:list  100  0.680      21.0  1.680           1.679   \n22            prompt:list  100  0.600      29.0  1.860           1.866   \n23            prompt:list  100  0.400      49.0  1.251           1.242   \n24            prompt:seed  100  1.000      -3.0  1.000           1.000   \n25            prompt:seed  100  1.000      -3.0  1.000           1.000   \n26            prompt:seed  100  0.930       4.0  1.080           1.095   \n27              sham_veto   50  0.960      -4.0  1.000           1.000   \n28                   twin  100  0.810       0.0  1.000           1.000   \n29                   twin   50  0.920       0.0  1.000           1.000   \n30                   twin  200  1.000       0.0  1.000           1.000   \n31                   twin  100  1.000       0.0  1.000           1.000   \n32                   twin  100  0.970       0.0  1.044           1.047   \n33                   twin  100  0.890       0.0  1.000           1.000   \n34                   veto  150  0.153      76.7    NaN             NaN   \n\n            CI90  coverage  offdef  cat_only escape qualify  \n0   [1.00, 1.00]     1.000    0.00      0.00  False   False  \n1   [1.00, 1.00]     1.000    0.03      0.00  False   False  \n2   [1.00, 1.00]     1.000    0.00      0.00  False   False  \n3   [1.00, 1.00]     1.000    0.00      0.00  False   False  \n4   [1.00, 1.00]     1.000    0.00      0.00  False   False  \n5   [1.00, 1.00]     1.000    0.00      0.00  False   False  \n6   [1.00, 1.00]     1.000    0.01      0.01  False   False  \n7   [1.00, 1.00]     1.000    0.00      0.00  False   False  \n8   [1.00, 1.00]     1.000    0.01      0.01  False   False  \n9   [1.00, 1.1\n--- cell 34 [display_data]\n  task alpha 1 escape/run alpha 2 escape/run  movable    push_top1  \\\n0  T03               8/18                3/3        1  quickselect   \n1   T1               1/15                0/3        1          dfs   \n2  T10                1/3                0/0        1          dfs   \n3  T13                0/3                0/0        0         None   \n4  T14                0/3                0/0        0         None   \n\n                                        push_landing  cat-only ban avoidance  \\\n0  {'heapify_pop': 0.0032, 'quickselect': 0.6457,...                    0.97   \n1                                       {'dfs': 1.0}                    0.86   \n2                                       {'dfs': 1.0}                    1.00   \n3                                                 {}                    0.14   \n4                                                 {}                    0.47   \n\n   avoidance >= 0.5 escaping engines  identical to frozen record  \n0              True   hf-bf16,hf-fp8                        True  \n1              True           hf-fp8                        True  \n2              True          hf-bf16                        True  \n3             False                -                        True  \n4             False                -                        True  \n--- cell 34 [stream]\nmovable x (avoidance >= 0.5) on the 5 screened tasks: table [[3, 0], [0, 2]], one-sided Fisher p = 0.1, balanced accuracy 1.0 (descriptive only: screen, not confirmation (rule read off the same data))\nfrozen screen (all 14 tasks): movable ['T03', 'T05', 'T06', 'T1', 'T10', 'T2']; C1 event set ['T03', 'T05', 'T06', 'T1', 'T10', 'T2']\npublished screen.json sha256           d6a2ca9711f461973c39482314a523d448d0590cb40e32432826dec1da4846e8\nwith the 5 recomputed task records  d6a2ca9711f461973c39482314a523d448d0590cb40e32432826dec1da4846e8  -> byte-identical", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [169] THINKING · 2026-10-26 11:15:17 UTC

```
Round 1 checks out fully: counts, screened records, and spliced checksums all match, with the knob stage finishing in 0.3s. Now scaling to round 2 using the original parameters (1000/1000/200, all 99 cells).
```

### [170] TOOL CALL — Bash · 2026-10-26 11:15:17 UTC

```
Run with original parameters and check agreement:
python3 - <<'EOF'
import json, re
p='code_demo.ipynb'; nb=json.load(open(p))
c=[c for c in nb['cells'] if c['id']=='10ec93e8'][0]
s=''.join(c['source'])
s=re.sub(r'^N_RAREFY = \d+ +', 'N_RAREFY = 1000      ', s, flags=re.M)
s=re.sub(r'^N_BOOT = \d+ +', 'N_BOOT = 1000        ', s, flags=re.M)
s=re.sub(r'^N_BOOT_RAREFY = \d+ +', 'N_BOOT_RAREFY = 200  ', s, flags=re.M)
c['source']=s.splitlines(keepends=True)
json.dump(nb, open(p,'w'), indent=1, ensure_ascii=False); open(p,'a').write('\n')
print(s)
EOF
T1=$(date +%s); /tmp/aii_nb_test_envs/art_sV0cQ3ef1ZRQ-ad6af5bda702/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | grep -v WARNING | tail -5; echo "notebook run: $(( $(date +%s)-T1 ))s"
python3 - <<'EOF'
import json
nb=json.load(open('/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/code_demo.ipynb'))
for i in (30, 32, 34):
    c=nb['cells'][i]
    for o in c.get('outputs',[]):
        t=o.get('output_type')
        if t=='stream': txt=''.join(o['text'])
        elif t in('execute_result','display_data'): txt=''.join(o['data'].get('text/plain',''))
        elif t=='error': txt='ERROR '+o['ename']+': '+o['evalue']
        else: txt=t
        if i==32 and 'group' in txt: continue
        print(f'--- cell {i} [{t}]'); print(txt[:2500])
EOF
```

### [171] TOOL RESULT — Bash · 2026-10-26 11:15:25 UTC

```
{"stdout": "# ---- tunable parameters (the original values are in the comments) ----\n# Monte-Carlo sizes of src/stats.py (original: N_RAREFY = 1000, N_BOOT = 1000, N_BOOT_RAREFY = 200)\nN_RAREFY = 1000      # rarefaction subsamples per Hill-1 value\nN_BOOT = 1000        # bootstrap replicates per 90% CI\nN_BOOT_RAREFY = 200  # rarefaction subsamples inside each bootstrap replicate\n# data size (original: all 1,120 cells of data/rows.parquet; mini_demo_data.json holds 99 of them)\nN_CELLS = 99         # first N demo cells, at least 6 (the first 6 are the complete T10 screen group); 99 = all\n# eval.py --stages (original default: all 14 stages; only these two run from the demo data)\nRUN_STAGES = [\"knob\", \"screen\"]\n# output folder (the original wrote into the artifact folder: data/, tables/, results/, screen.json, logs/)\nWS = Path(\"demo_run\")\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[NbConvertApp] Writing 459544 bytes to code_demo.ipynb\nnotebook run: 9s\n--- cell 30 [stream]\n11:15:19|INFO   |=== stage knob ===\n\n--- cell 30 [stream]\n11:15:19|INFO   |knob table: 99 cells; computing rarefied Hill-1 with 1 workers\n\n--- cell 30 [stream]\n11:15:22|INFO   |knob table: 99 rows -> tables/knob_table.csv\n\n--- cell 30 [stream]\n11:15:22|INFO   |=== stage knob done in 3.1s ===\n\n--- cell 30 [stream]\n11:15:22|INFO   |=== stage screen ===\n\n--- cell 30 [stream]\n11:15:23|INFO   |screen.json sha256 7c0777dc107d36726918e7c6ab3d03e4e7411ce5f19c439cdabe2de5cedb6191; movable ['T03', 'T1', 'T10']\n\n--- cell 30 [stream]\n11:15:23|INFO   |=== stage screen done in 0.1s ===\n\n--- cell 30 [stream]\nstages ['knob', 'screen'] finished in 3.2s; outputs in demo_run/\n\n--- cell 32 [stream]\n99 cells recomputed with N_RAREFY = 1000, N_BOOT = 1000, N_BOOT_RAREFY = 200\n\n--- cell 32 [display_data]\n                column            kind  cells  identical  \\\n0            pass_rate  counts (exact)     99         99   \n1        pass_cost_pts  counts (exact)     99         99   \n2         offdef_share  counts (exact)     99         99   \n3   cat_only_avoidance  counts (exact)     99         99   \n4             coverage  counts (exact)     99         99   \n5                S_obs  counts (exact)     99         99   \n6                H1r25     Monte Carlo     99         99   \n7            H1r25_cat     Monte Carlo     99         99   \n8                H1r10     Monte Carlo     99         99   \n9           H1r25_ci90     Monte Carlo     99         99   \n10      H1r25_ci90_iid     Monte Carlo     99         99   \n11      pass_cost_ci95  counts (exact)     99         99   \n12              escape  counts (exact)     99         99   \n13             qualify     Monte Carlo     99         99   \n\n    max |recomputed - recorded|  \n0                  0.000000e+00  \n1                  0.000000e+00  \n2                  0.000000e+00  \n3                  0.000000e+00  \n4                  0.000000e+00  \n5                  0.000000e+00  \n6                  2.220446e-16  \n7                  0.000000e+00  \n8                  0.000000e+00  \n9                  0.000000e+00  \n10                 0.000000e+00  \n11                 0.000000e+00  \n12                 0.000000e+00  \n13                 0.000000e+00  \n--- cell 32 [stream]\n\nPath-search task T1: 35 knob and twin cells (exp17 random directions are in the screen below)\n\n--- cell 34 [display_data]\n  task alpha 1 escape/run alpha 2 escape/run  movable    push_top1  \\\n0  T03               8/18                3/3        1  quickselect   \n1   T1               1/15                0/3        1          dfs   \n2  T10                1/3                0/0        1          dfs   \n3  T13                0/3                0/0        0         None   \n4  T14                0/3                0/0        0         None   \n\n                                        push_landing  cat-only ban avoidance  \\\n0  {'heapify_pop': 0.0032, 'quickselect': 0.6457,...                    0.97   \n1                                       {'dfs': 1.0}                    0.86   \n2                                       {'dfs': 1.0}                    1.00   \n3                                                 {}                    0.14   \n4                                                 {}                    0.47   \n\n   avoidance >= 0.5 escaping engines  identical to frozen record  \n0              True   hf-bf16,hf-fp8                        True  \n1              True           hf-fp8                        True  \n2              True          hf-bf16                        True  \n3             False                -                        True  \n4             False                -                        True  \n--- cell 34 [stream]\nmovable x (avoidance >= 0.5) on the 5 screened tasks: table [[3, 0], [0, 2]], one-sided Fisher p = 0.1, balanced accuracy 1.0 (descriptive only: screen, not confirmation (rule read off the same data))\nfrozen screen (all 14 tasks): movable ['T03', 'T05', 'T06', 'T1', 'T10', 'T2']; C1 event set ['T03', 'T05', 'T06', 'T1', 'T10', 'T2']\npublished screen.json sha256           d6a2ca9711f461973c39482314a523d448d0590cb40e32432826dec1da4846e8\nwith the 5 recomputed task records  d6a2ca9711f461973c39482314a523d448d0590cb40e32432826dec1da4846e8  -> byte-identical", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [172] THINKING · 2026-10-26 11:15:35 UTC

```
All 99 cells match the original parameters exactly (max difference just float rounding), confirming reproduction even across numpy versions, so I'm keeping these as the final config. Now I'll check the figure visually.
```

### [173] TOOL CALL — Bash · 2026-10-26 11:15:35 UTC

```
List demo outputs and extract figure for review:
ls -la demo_run demo_run/figures demo_run/tables && python3 -c "
import json,base64
nb=json.load(open('code_demo.ipynb'))
for o in nb['cells'][36]['outputs']:
    if 'data' in o and 'image/png' in o['data']:
        open('demo_run/figures/_nb_fig_check.png','wb').write(base64.b64decode(o['data']['image/png'])); print('saved')
"
```

### [174] TOOL RESULT — Bash · 2026-10-26 11:15:35 UTC

```
{"stdout": "demo_run:\ntotal 7018\ndrwxrwxrwx 8 aii-agent aii-agent 1045526 Oct 26 11:14 .\ndrwxrwxrwx 4 aii-agent aii-agent 2000269 Oct 26 11:14 ..\ndrwxrwxrwx 2 aii-agent aii-agent       1 Oct 26 11:14 audit\ndrwxrwxrwx 2 aii-agent aii-agent 1003809 Oct 26 11:14 data\ndrwxrwxrwx 2 aii-agent aii-agent 1028538 Oct 26 11:14 figures\ndrwxrwxrwx 2 aii-agent aii-agent 1000218 Oct 26 11:14 logs\ndrwxrwxrwx 2 aii-agent aii-agent   50300 Oct 26 11:14 results\n-rw-rw-rw- 1 aii-agent aii-agent    1938 Oct 26 11:15 screen.json\n-rw-rw-rw- 1 aii-agent aii-agent      78 Oct 26 11:15 screen.sha256\n-rw-rw-rw- 1 aii-agent aii-agent   27699 Oct 26 11:15 screen_extras.json\n-rw-rw-rw- 1 aii-agent aii-agent   15782 Oct 26 11:15 screen_input.json\ndrwxrwxrwx 2 aii-agent aii-agent 1008467 Oct 26 11:14 tables\n\ndemo_run/figures:\ntotal 2312\ndrwxrwxrwx 2 aii-agent aii-agent 1028538 Oct 26 11:14 .\ndrwxrwxrwx 8 aii-agent aii-agent 1045526 Oct 26 11:14 ..\n-rw-rw-rw- 1 aii-agent aii-agent  292233 Oct 26 11:15 demo_summary.png\n\ndemo_run/tables:\ntotal 2093\ndrwxrwxrwx 2 aii-agent aii-agent 1008467 Oct 26 11:14 .\ndrwxrwxrwx 8 aii-agent aii-agent 1045526 Oct 26 11:14 ..\n-rw-rw-rw- 1 aii-agent aii-agent    6074 Oct 26 11:15 arm_dictionary.csv\n-rw-rw-rw- 1 aii-agent aii-agent   31262 Oct 26 11:15 demo_recomputed_vs_recorded.csv\n-rw-rw-rw- 1 aii-agent aii-agent   47238 Oct 26 11:15 knob_table.csv\n-rw-rw-rw- 1 aii-agent aii-agent     778 Oct 26 11:15 random_direction_counts.csv\n-rw-rw-rw- 1 aii-agent aii-agent    1360 Oct 26 11:15 table110_alpha2.csv\nsaved", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [175] TOOL CALL — Read · 2026-10-26 11:15:39 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/demo_run/figures/demo_summary.png
```

### [176] TOOL RESULT — Read · 2026-10-26 11:15:39 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [177] THINKING · 2026-10-26 11:17:03 UTC

```
The figure renders correctly but has overlapping labels—in panel (a) annotations collide with the x-axis label and legend, and in panel (c) the legend overlaps rule text while four frozen tasks stack at (0,0). I'll fix these label placement issues in the visualization cell.
```

### [178] TOOL CALL — Bash · 2026-10-26 11:17:03 UTC

```
Patch figure label placement and re-run notebook:
python3 - <<'EOF'
import json
p='code_demo.ipynb'; nb=json.load(open(p))
c=[c for c in nb['cells'] if c['id']=='1c8d802c'][0]
s=''.join(c['source'])
reps = [
('''SHORT = {"A2:seed_semantic": "semantic seed", "A2:seed_entropy": "entropy seed", "A3:instr_fully_novel": "'fully novel' instr.",
         "A3:instr_new_algo": "'new algorithm' instr.", "A4s2:gen_then_select": "generate-then-select (ceiling)",
         "single:bfs": "ban BFS", "multi:TOP5": "ban top-5", "multi:SCATTER": "ban SCATTER list",
         "succession:2": "succession ban", "two_step:TWO(bfs,dfs)": "ban BFS + DFS"}''',
'''# annotated T1 arms: label and text offset (points)
SHORT = {"A2:seed_semantic": ("semantic seed", (8, -14)), "A3:instr_fully_novel": ("'fully novel' instr.", (5, 4)),
         "A4s2:gen_then_select": ("generate-then-select", (-50, -14)), "single:bfs": ("ban BFS", (5, 4)),
         "multi:TOP5": ("ban top-5", (5, 4)), "multi:SCATTER": ("ban SCATTER list", (5, 4)),
         "succession:2": ("succession ban", (5, 4)), "two_step:TWO(bfs,dfs)": ("ban BFS + DFS", (5, 4))}'''),
('''        ax.annotate(SHORT[r.arm], (r.pass_cost_pts, r.H1r25), xytext=(5, 4), textcoords="offset points", fontsize=8)''',
 '''        ax.annotate(SHORT[r.arm][0], (r.pass_cost_pts, r.H1r25), xytext=SHORT[r.arm][1], textcoords="offset points",
                    fontsize=8)'''),
('''(dec.pass_cost_pts.mean(), dec.H1r25.mean()), xytext=(30, -45), textcoords="offset points",''',
 '''(dec.pass_cost_pts.mean(), dec.H1r25.mean()), xytext=(-95, 30), textcoords="offset points",'''),
('''    ax.legend(fontsize=7, loc="upper right")
else:''', '''    ax.legend(fontsize=7, loc="upper center")
else:'''),
('''for i, (t, rec) in enumerate(sorted(frozen["tasks"].items())):
    mine = t in screen["tasks"]
    rr = screen["tasks"][t] if mine else rec
    col = "#d62728" if rr["movable"] else "#1f77b4"
    ax.scatter(_emax(rr), rr["cat_only_ban_avoidance"], s=130 if mine else 70, color=col if mine else "none",
               edgecolor=col if mine else "#7f7f7f", linewidth=1.5, zorder=3)
    ax.annotate(t, (_emax(rr), rr["cat_only_ban_avoidance"]), xytext=(8, 8 * (i % 3 - 1) - 3), textcoords="offset points",
                fontsize=9 if mine else 8, color="k" if mine else "#7f7f7f")''',
'''labels = {}
for t, rec in sorted(frozen["tasks"].items()):
    mine = t in screen["tasks"]
    rr = screen["tasks"][t] if mine else rec
    x, y = _emax(rr), rr["cat_only_ban_avoidance"]
    col = "#d62728" if rr["movable"] else "#1f77b4"
    ax.scatter(x, y, s=130 if mine else 70, color=col if mine else "none", edgecolor=col if mine else "#7f7f7f",
               linewidth=1.5, zorder=3)
    labels.setdefault((round(x / 0.04), round(y / 0.04)), []).append((t, mine, x, y))
for grp in labels.values():  # tasks at (nearly) the same point share one label
    mine = any(m for _, m, _, _ in grp)
    ax.annotate(", ".join(t for t, _, _, _ in grp), grp[0][2:], xytext=(8, -3), textcoords="offset points",
                fontsize=9 if mine else 8, color="k" if mine else "#7f7f7f")'''),
('''ax.text(0.55, 0.53, "movable (E_t > 0) and avoidance >= 0.5", fontsize=8)
ax.set_xlim(-0.05, 1.05)''', '''ax.text(0.45, 0.53, "movable (E_t > 0) and avoidance >= 0.5", fontsize=8)
ax.set_xlim(-0.05, 1.12)'''),
('''          fontsize=8, loc="center right")''', '''          fontsize=8, loc="lower right")'''),
]
for a, b in reps:
    assert s.count(a) == 1, a[:60]
    s = s.replace(a, b)
c['source']=s.splitlines(keepends=True)
json.dump(nb, open(p,'w'), indent=1, ensure_ascii=False); open(p,'a').write('\n')
print("patched")
EOF
T1=$(date +%s); /tmp/aii_nb_test_envs/art_sV0cQ3ef1ZRQ-ad6af5bda702/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | grep -v WARNING | tail -3; echo "notebook run: $(( $(date +%s)-T1 ))s"
```

### [179] TOOL RESULT — Bash · 2026-10-26 11:17:09 UTC

```
{"stdout": "patched\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[NbConvertApp] Writing 457816 bytes to code_demo.ipynb\nnotebook run: 8s", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [180] TOOL CALL — Read · 2026-10-26 11:17:13 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/demo_run/figures/demo_summary.png
```

### [181] TOOL RESULT — Read · 2026-10-26 11:17:13 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [182] THINKING · 2026-10-26 11:18:03 UTC

```
Labels are now clean, with the temperature-cluster callout, legend, and stacked frozen tasks all properly displayed. Next I'll pull the exact final numbers from the executed outputs to cite in the closing summary.
```

### [183] TOOL CALL — Bash · 2026-10-26 11:18:03 UTC

```
Extract final T1 and qualifying-cell numbers for summary:
rm -f demo_run/figures/_nb_fig_check.png && python3 - <<'EOF'
import pandas as pd
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 48); pd.set_option("display.max_rows", 200)
d = pd.read_csv("demo_run/tables/demo_recomputed_vs_recorded.csv")
k = pd.read_csv("demo_run/tables/knob_table.csv")
t1 = d[(d.task == "T1") & ~d.arm.str.startswith("RAND")]
print(t1[["exp","arm","family","n","pass_rate_recomputed","pass_cost_pts_recomputed","H1r25_recomputed","H1r25_ci90_recomputed","offdef_share_recomputed","cat_only_avoidance_recomputed","escape_recomputed","qualify_recomputed"]].round(3).to_string(index=False))
print("\nqualifying cells (H1r25>=2 at <=20 pts):")
print(k[k.qualify == True][["task","arm","family","H1r25","pass_cost_pts","pass_rate"]].round(3).to_string(index=False))
r = d[(d.task == "T1") & d.arm.str.startswith("RAND")]
print("\nT1 exp17 RAND directions: H1r25 range", r.H1r25_recomputed.min(), r.H1r25_recomputed.max(), "| escape:", (r.escape_recomputed=="True").sum(), "/", len(r))
print(k[(k.task=="T1") & (k.escape==True)][["arm","H1r25","pass_rate","pass_cost_pts","offdef_share","attempted_composition"]].to_string(index=False))
print(k[(k.task=="T1") & (k.arm=="NEUTRAL")][["arm","pass_rate","offdef_share","attempted_composition","correct_composition"]].to_string(index=False))
print(k[(k.task=="T1") & (k.arm=="A0:baseline")][["arm","pass_rate","offdef_share","attempted_composition","correct_composition"]].to_string(index=False))
EOF
```

### [184] TOOL RESULT — Bash · 2026-10-26 11:18:05 UTC

```
{"stdout": "  exp                                                                   arm                family   n  pass_rate_recomputed  pass_cost_pts_recomputed  H1r25_recomputed H1r25_ci90_recomputed  offdef_share_recomputed  cat_only_avoidance_recomputed escape_recomputed qualify_recomputed\nexp17                                                               NEUTRAL                  twin 100                 0.810                     0.000             1.000            [1.0, 1.0]                    0.010                          0.010               NaN                NaN\nexp18                                                            fixed_top5                  veto 150                 0.153                    76.667               NaN            [nan, nan]                    0.054                          0.054             False              False\nexp18                                      longform:LF1 {\"thinking\": false}    prompt:instruction  25                 0.280                    64.000               NaN            [nan, nan]                    0.812                          0.750             False              False\nexp18                                                                  sham             sham_veto  50                 0.960                    -4.000             1.000            [1.0, 1.0]                    0.000                          0.000               NaN                NaN\nexp18                                                 two_step:TWO(bfs,dfs)            prompt:ban 100                 0.540                    38.000             1.895       [1.1834, 2.123]                    0.840                          0.820             False              False\nexp18                                                             walk_twin                  twin  50                 0.920                     0.000             1.000            [1.0, 1.0]                    0.000                          0.000               NaN                NaN\n exp4                                                               ban:bfs            prompt:ban 100                 0.640                    36.000             1.949      [1.6857, 2.2092]                    0.510                          0.500             False              False\n exp4                                                              baseline                  twin 200                 1.000                     0.000             1.000            [1.0, 1.0]                    0.000                          0.000               NaN                NaN\n exp4                                      steer:dc {\"c\": 0.0, \"layer\": 18}                  twin 100                 1.000                     0.000             1.000            [1.0, 1.0]                    0.000                          0.000               NaN                NaN\n exp4                                     steer:dc {\"c\": 0.25, \"layer\": 18} activation-structured 100                 0.570                    43.000             1.000            [1.0, 1.0]                    0.030                          0.000             False              False\n exp4                                   steer:rand1 {\"c\": 0.1, \"layer\": 18}     activation-random 100                 0.980                     2.000             1.000            [1.0, 1.0]                    0.000                          0.000             False              False\n exp4                                                          succession:2            prompt:ban 100                 0.880                    12.000             2.187      [1.8397, 2.5428]                    0.300                          0.290              True               True\n exp6          A0:baseline {\"T\": 1.0, \"sampler\": \"pure\", \"thinking\": false}                  twin 100                 0.970                     0.000             1.047         [1.0, 1.1305]                    0.010                          0.010               NaN                NaN\n exp6        A1:baseline {\"T\": 0.3, \"sampler\": \"topk10\", \"thinking\": false}              decoding 100                 1.000                    -3.000             1.000            [1.0, 1.0]                    0.000                          0.000             False              False\n exp6       A1:baseline {\"T\": 0.3, \"sampler\": \"topp095\", \"thinking\": false}              decoding 100                 1.000                    -3.000             1.000            [1.0, 1.0]                    0.000                          0.000             False              False\n exp6        A1:baseline {\"T\": 0.7, \"sampler\": \"topk10\", \"thinking\": false}              decoding 100                 0.980                    -1.000             1.000            [1.0, 1.0]                    0.010                          0.010             False              False\n exp6       A1:baseline {\"T\": 0.7, \"sampler\": \"topp095\", \"thinking\": false}              decoding 100                 1.000                    -3.000             1.000            [1.0, 1.0]                    0.000                          0.000             False              False\n exp6        A1:baseline {\"T\": 1.0, \"sampler\": \"topk10\", \"thinking\": false}              decoding 100                 0.980                    -1.000             1.000            [1.0, 1.0]                    0.000                          0.000             False              False\n exp6       A1:baseline {\"T\": 1.0, \"sampler\": \"topp095\", \"thinking\": false}              decoding 100                 1.000                    -3.000             1.000            [1.0, 1.0]                    0.000                          0.000             False              False\n exp6        A1:baseline {\"T\": 1.3, \"sampler\": \"topk10\", \"thinking\": false}              decoding 100                 0.950                     2.000             1.044         [1.0, 1.1352]                    0.010                          0.010             False              False\n exp6       A1:baseline {\"T\": 1.3, \"sampler\": \"topp095\", \"thinking\": false}              decoding 100                 0.970                     0.000             1.000            [1.0, 1.0]                    0.010                          0.010             False              False\n exp6      A2:seed_entropy {\"T\": 1.0, \"sampler\": \"pure\", \"thinking\": false}           prompt:seed 100                 1.000                    -3.000             1.000            [1.0, 1.0]                    0.000                          0.000             False              False\n exp6     A2:seed_semantic {\"T\": 1.0, \"sampler\": \"pure\", \"thinking\": false}           prompt:seed 100                 0.930                     4.000             1.095          [1.0, 1.194]                    0.050                          0.050             False              False\n exp6         A2:seed_word {\"T\": 1.0, \"sampler\": \"pure\", \"thinking\": false}           prompt:seed 100                 1.000                    -3.000             1.000            [1.0, 1.0]                    0.000                          0.000             False              False\n exp6    A3:instr_creative {\"T\": 1.0, \"sampler\": \"pure\", \"thinking\": false}    prompt:instruction 100                 1.000                    -3.000             1.000            [1.0, 1.0]                    0.000                          0.000             False              False\n exp6   A3:instr_enumerate {\"T\": 1.0, \"sampler\": \"pure\", \"thinking\": false}    prompt:instruction 100                 0.990                    -2.000             1.000            [1.0, 1.0]                    0.000                          0.000             False              False\n exp6 A3:instr_fully_novel {\"T\": 1.0, \"sampler\": \"pure\", \"thinking\": false}    prompt:instruction 100                 0.850                    12.000             1.229       [1.053, 1.4097]                    0.130                          0.130             False              False\n exp6    A3:instr_new_algo {\"T\": 1.0, \"sampler\": \"pure\", \"thinking\": false}    prompt:instruction 100                 0.940                     3.000             1.100         [1.0, 1.1991]                    0.030                          0.030             False              False\n exp6 A4s2:gen_then_select {\"T\": 1.0, \"sampler\": \"pure\", \"thinking\": false}  generate_then_select 100                 0.550                    42.000             3.358      [2.8369, 3.6258]                    0.700                          0.630             False              False\n exp9                                                              baseline                  twin 100                 0.890                     0.000             1.000            [1.0, 1.0]                    0.000                          0.000               NaN                NaN\n exp9                                                             multi:ARC           prompt:list 100                 0.600                    29.000             1.866      [1.3179, 1.9763]                    0.370                          0.370             False              False\n exp9                                                         multi:SCATTER           prompt:list 100                 0.750                    14.000             2.101      [1.6102, 2.3736]                    0.310                          0.310              True               True\n exp9                                                             multi:TOP           prompt:list 100                 0.400                    49.000             1.242          [1.0, 1.483]                    0.410                          0.290             False              False\n exp9                                                            multi:TOP5           prompt:list 100                 0.680                    21.000             1.679      [1.3059, 1.9456]                    0.370                          0.370             False              False\n exp9                                                            single:bfs            prompt:ban 100                 0.410                    48.000             1.776      [1.5292, 1.9373]                    0.860                          0.860             False              False\n\nqualifying cells (H1r25>=2 at <=20 pts):\ntask           arm            family  H1r25  pass_cost_pts  pass_rate\n T03           ban        prompt:ban  2.167            8.0       0.92\n T03 RAND9002_a1.0 activation-random  2.923            0.0       1.00\n T03 RAND9002_a2.0 activation-random  2.134            2.0       0.98\n T03 RAND9003_a1.0 activation-random  2.320            4.0       0.96\n T03 RAND9003_a2.0 activation-random  2.293            2.0       0.98\n T03 RAND9006_a1.0 activation-random  2.134            4.0       0.96\n T03 RAND9010_a1.0 activation-random  2.109            0.0       1.00\n T03 RAND9014_a1.0 activation-random  2.420            0.0       1.00\n  T1  succession:2        prompt:ban  2.187           12.0       0.88\n  T1 multi:SCATTER       prompt:list  2.101           14.0       0.75\n\nT1 exp17 RAND directions: H1r25 range 1.0 1.9919589974203875 | escape: 0 / 18\n          arm    H1r25  pass_rate  pass_cost_pts  offdef_share                                               attempted_composition\nRAND9014_a1.0 1.751332       0.72            9.0          0.24                                              {\"bfs\": 38, \"dfs\": 12}\n succession:2 2.186585       0.88           12.0          0.30 {\"bfs\": 70, \"dijkstra_unit\": 15, \"dfs\": 11, \"astar\": 3, \"other\": 1}\nmulti:SCATTER 2.101352       0.75           14.0          0.31              {\"bfs\": 69, \"dfs\": 27, \"dijkstra_unit\": 2, \"astar\": 2}\n    arm  pass_rate  offdef_share attempted_composition correct_composition\nNEUTRAL       0.81          0.01 {\"bfs\": 99, \"dfs\": 1}         {\"bfs\": 81}\n        arm  pass_rate  offdef_share           attempted_composition             correct_composition\nA0:baseline       0.97          0.01 {\"bfs\": 99, \"dijkstra_unit\": 1} {\"bfs\": 96, \"dijkstra_unit\": 1}", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [185] THINKING · 2026-10-26 11:18:53 UTC

```
That earlier "0/18 escapes" result was just a CSV parsing artifact, not a real discrepancy—the knob table correctly shows RAND9014_a1.0 escaping, matching the screen's 1/15. Now I'll check how much of the full T1 table the demo subset actually covers before concluding only two T1 cells qualify.
```

### [186] TOOL CALL — Bash · 2026-10-26 11:18:53 UTC

```
Check T1 coverage of the demo subset vs full table:
cd /tmp && python3 -I - <<'EOF'
import pandas as pd
A="/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3"
k=pd.read_parquet(f"{A}/data/knob.parquet")
t1=k[k.task=="T1"]
print("full T1 cells:", len(t1), "| by exp:", t1.groupby("exp").size().to_dict())
q=t1[(t1.qualify==True)]
print("full-table T1 qualifying:", q[["exp","arm","dial","H1r25","pass_cost_pts"]].round(3).values.tolist())
print("full-table T1 qwen knob H1r25>=2:", t1[(t1["class"]=="knob")&(t1.H1r25>=2)][["exp","arm","H1r25","pass_cost_pts"]].round(2).values.tolist())
EOF
```

### [187] TOOL RESULT — Bash · 2026-10-26 11:18:53 UTC

```
{"stdout": "full T1 cells: 98 | by exp: {'exp16': 5, 'exp17': 31, 'exp18': 12, 'exp4': 19, 'exp6': 25, 'exp9': 6}\nfull-table T1 qualifying: [['exp4', 'succession:2', '{}', 2.187, 12.0], ['exp9', 'multi:SCATTER', '{}', 2.101, 14.0]]\nfull-table T1 qwen knob H1r25>=2: [['exp4', 'succession:2', 2.19, 12.0], ['exp9', 'multi:SCATTER', 2.1, 14.0]]", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [188] THINKING · 2026-10-26 11:19:13 UTC

```
Confirmed both qualifying T1 cells fall within the demo subset, so the claim holds. I'll now update the closing summary cell with this interpretation and run the final test from a freshly recreated venv.
```

### [189] TOOL CALL — Bash · 2026-10-26 11:19:13 UTC

```
Replace summary cell and run final test in fresh venv:
python3 - <<'PYEOF'
import json
p = 'code_demo.ipynb'
nb = json.load(open(p))
c = [c for c in nb['cells'] if c['id'] == 'summary'][0]
s = r"""## Summary

**What was reproduced.** With the original Monte-Carlo sizes, every one of the 99 demo cells matches the artifact's knob table on all 14 compared columns (largest difference 2.2e-16). The columns are Hill-1 and its CIs, coverage, pass cost with its Newcombe CI, off-default share, catalogue-only avoidance, and the escape and qualify flags. The five screened tasks reproduce their frozen `screen.json` records exactly: T03, T1 and T10 are movable, T13 and T14 are not. Substituting these records into the frozen file gives back the published sha256 `d6a2ca97…` byte for byte.

**What the path-search task T1 shows.** The model writes BFS. In the twins, 96 of 97 correct programs in exp6's T = 1.0 baseline are BFS, 81 of 81 in exp17's twin, and all 200 programs of exp4's baseline.
- *Temperature is not the creativity knob here.* Across T = 0.3–1.3 with top-k 10 or top-p 0.95, 7 of the 8 cells have Hill-1 = 1.00, the eighth reaches 1.04, and the off-default share stays at 0.01 or below. Sampling changes the wording, not the algorithm.
- *Context seeds and creativity instructions barely move it.* The entropy and word seeds give 1.00 and the semantic seed 1.09. The "creative" and "enumerate" instructions give 1.00, "new algorithm" 1.10, and "fully novel" 1.23 at a cost of 12 points. The 2,000-word "fully novel algorithm" instruction does move off BFS (off-default share 0.81), but only 28% of its programs pass, so it has no depth-25 value.
- *Bans move the algorithm, at a price.* Banning BFS by name sends 86% of programs off the default but costs 48 points (Hill-1 1.78). Banning the top-5 list gives 1.68 at 21 points. Only two T1 cells qualify, here and in the full 98-cell T1 table: the succession ban (2.19 at 12 points) and the SCATTER list ban (2.10 at 14 points). Generate-then-select reaches 3.36 at 42 points; it is a ceiling and is never ranked.
- *Activation directions depend on the task.* On T1, one of 15 random exp17 directions escapes at α = 1, towards DFS, and the decommitment steering direction at c = 0.25 costs 43 points with Hill-1 still 1.00. On T03, by contrast, 7 random direction-α cells qualify at a cost of 0–4 points (Hill-1 up to 2.92), above the modal ban (2.17 at 8 points).

**The screen.** On the five screened tasks, *movable* and *modal-ban avoidance ≥ 0.5* agree perfectly (a 3/0/0/2 table); on all 14 frozen tasks the table is 6/0/0/8 (one-sided Fisher p = 1/3003). This is a screen read off the same data, not a confirmation. The immovable side is also weakly tested: most tasks have K = 3 directions, which bounds the per-direction escape probability only below 0.54 (90% upper bound).

**Scaling.** The config cell already uses the original Monte-Carlo sizes. The knob stage takes about 3 s for the 99 cells, and the whole notebook runs in well under a minute once the packages are installed. The full 1,120-cell table and the other 12 stages need the 11 dependency artifacts. In the artifact's repository folder they run with `uv run eval.py --stages all` in about 1.5 minutes."""
c['source'] = s.splitlines(keepends=True)
json.dump(nb, open(p, 'w'), indent=1, ensure_ascii=False); open(p, 'a').write('\n')
print("summary replaced")
PYEOF
T0=$(date +%s) && UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_sV0cQ3ef1ZRQ-ad6af5bda702 && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_sV0cQ3ef1ZRQ-ad6af5bda702/bin/python jupyter ipykernel && T1=$(date +%s) && /tmp/aii_nb_test_envs/art_sV0cQ3ef1ZRQ-ad6af5bda702/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | grep -v WARNING | tail -3; echo "venv setup: $((T1-T0))s, notebook run (incl. install cell): $(( $(date +%s)-T1 ))s"
```

### [190] TOOL RESULT — Bash · 2026-10-26 11:19:33 UTC

```
{"stdout": "summary replaced\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[NbConvertApp] Writing 460752 bytes to code_demo.ipynb\nvenv setup: 1s, notebook run (incl. install cell): 20s", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [191] THINKING · 2026-10-26 11:19:47 UTC

```
The clean-venv run passed in 20 seconds including the install cell. Next I'll verify TODO 6 and scan the executed notebook for errors, warnings, or leaked absolute server paths.
```

### [192] TOOL CALL — Bash · 2026-10-26 11:19:47 UTC

```
Verify URL, data file, errors and absolute paths:
python3 - <<'EOF'
import json
nb = json.load(open('code_demo.ipynb'))
URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-4/evaluation-3/demo/mini_demo_data.json"
src = "\n".join("".join(c["source"]) for c in nb["cells"])
print("(1) exact GITHUB_DATA_URL line present:", f'GITHUB_DATA_URL = "{URL}"' in src)
print("(3) urlopen(GITHUB_DATA_URL) used:", "urllib.request.urlopen(GITHUB_DATA_URL" in src, "| load_data() called:", "data = load_data()" in src)
n_code = sum(c["cell_type"] == "code" for c in nb["cells"])
errs, warns, executed = [], [], 0
for i, c in enumerate(nb["cells"]):
    if c["cell_type"] != "code": continue
    executed += c.get("execution_count") is not None
    for o in c.get("outputs", []):
        if o["output_type"] == "error": errs.append((i, o["ename"]))
        if o["output_type"] == "stream" and o.get("name") == "stderr": warns.append((i, "".join(o["text"])[:300]))
print(f"code cells: {n_code}, executed: {executed}, errors: {errs}")
print("stderr outputs:", warns if warns else "none")
blob = json.dumps(nb)
for pat in ("/ai-inventor", "/tmp/", "aii_nb_test_envs", "/home/"):
    print(f"occurrences of {pat!r} in notebook:", blob.count(pat))
for o in nb["cells"][30]["outputs"]:
    if o["output_type"] == "stream": print("".join(o["text"]).rstrip())
EOF
ls -la mini_demo_data.json code_demo.ipynb; python3 -c "import json; json.load(open('mini_demo_data.json')); print('(2) mini_demo_data.json parses as strict JSON')"
```

### [193] TOOL RESULT — Bash · 2026-10-26 11:19:47 UTC

```
{"stdout": "(1) exact GITHUB_DATA_URL line present: True\n(3) urlopen(GITHUB_DATA_URL) used: True | load_data() called: True\ncode cells: 20, executed: 20, errors: []\nstderr outputs: none\noccurrences of '/ai-inventor' in notebook: 1\noccurrences of '/tmp/' in notebook: 0\noccurrences of 'aii_nb_test_envs' in notebook: 0\noccurrences of '/home/' in notebook: 0\n11:19:28|INFO   |=== stage knob ===\n11:19:28|INFO   |knob table: 99 cells; computing rarefied Hill-1 with 1 workers\n11:19:31|INFO   |knob table: 99 rows -> tables/knob_table.csv\n11:19:31|INFO   |=== stage knob done in 3.1s ===\n11:19:31|INFO   |=== stage screen ===\n11:19:31|INFO   |screen.json sha256 7c0777dc107d36726918e7c6ab3d03e4e7411ce5f19c439cdabe2de5cedb6191; movable ['T03', 'T1', 'T10']\n11:19:31|INFO   |=== stage screen done in 0.1s ===\nstages ['knob', 'screen'] finished in 3.2s; outputs in demo_run/\n-rw-rw-rw- 1 aii-agent aii-agent 460818 Oct 26 11:19 code_demo.ipynb\n-rw-rw-rw- 1 aii-agent aii-agent 762309 Oct 26 10:59 mini_demo_data.json\n(2) mini_demo_data.json parses as strict JSON", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [194] THINKING · 2026-10-26 11:19:51 UTC

```
All TODO 6 checks pass—20/20 code cells executed with no errors. I'll track down the one remaining `/ai-inventor` reference, since absolute server paths shouldn't be published.
```

### [195] TOOL CALL — Bash · 2026-10-26 11:19:51 UTC

```
Locate absolute path string in notebook:
python3 - <<'EOF'
import json
nb = json.load(open('code_demo.ipynb'))
for i, c in enumerate(nb["cells"]):
    s = json.dumps(c)
    j = s.find("/ai-inventor")
    if j >= 0: print(i, c["cell_type"], repr(s[max(0, j-300):j+200]))
print("nb metadata:", json.dumps(nb["metadata"])[:400])
EOF
grep -c "/ai-inventor" mini_demo_data.json make_mini_demo_data.py
```

### [196] TOOL RESULT — Bash · 2026-10-26 11:19:51 UTC

```
{"stdout": "3 code 'on\": {\"iopub.execute_input\": \"2026-10-26T11:19:27.800925Z\", \"iopub.status.busy\": \"2026-10-26T11:19:27.800717Z\", \"iopub.status.idle\": \"2026-10-26T11:19:27.805475Z\", \"shell.execute_reply\": \"2026-10-26T11:19:27.804912Z\"}}, \"outputs\": [], \"source\": [\"GITHUB_DATA_URL = \\\\\"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-4/evaluation-3/demo/mini_demo_data.json\\\\\"\\\\n\", \"import http.client\\\\n\", \"import json\\\\n\", \"imp'\nnb metadata: {\"kernelspec\": {\"display_name\": \"Python 3\", \"language\": \"python\", \"name\": \"python3\"}, \"language_info\": {\"codemirror_mode\": {\"name\": \"ipython\", \"version\": 3}, \"file_extension\": \".py\", \"mimetype\": \"text/x-python\", \"name\": \"python\", \"nbconvert_exporter\": \"python\", \"pygments_lexer\": \"ipython3\", \"version\": \"3.12.14\"}}\nmini_demo_data.json:0\nmake_mini_demo_data.py:0", "stderr": "", "interrupted": false, "isImage": false, "returnCodeInterpretation": "No matches found", "noOutputExpected": false}
```

### [197] THINKING · 2026-10-26 11:20:39 UTC

```
That match was a false positive—just part of a GitHub org name, not a real server path—so everything checks out. I'll delete the `demo_run/` test output now and move on to writing the README, manifest, and structured output.
```

### [198] TOOL CALL — Bash · 2026-10-26 11:20:39 UTC

```
Remove regenerable test outputs and list workspace:
ls -la demo_run && rm -rf demo_run && ls -la . .aii && du -sh . 2>/dev/null
```

### [199] TOOL RESULT — Bash · 2026-10-26 11:20:39 UTC

```
{"stdout": "total 7018\ndrwxrwxrwx 8 aii-agent aii-agent 1045517 Oct 26 11:14 .\ndrwxrwxrwx 4 aii-agent aii-agent 2000290 Oct 26 11:14 ..\ndrwxrwxrwx 2 aii-agent aii-agent       1 Oct 26 11:14 audit\ndrwxrwxrwx 2 aii-agent aii-agent 1003809 Oct 26 11:14 data\ndrwxrwxrwx 2 aii-agent aii-agent 1028383 Oct 26 11:18 figures\ndrwxrwxrwx 2 aii-agent aii-agent 1000364 Oct 26 11:14 logs\ndrwxrwxrwx 2 aii-agent aii-agent   50300 Oct 26 11:14 results\n-rw-rw-rw- 1 aii-agent aii-agent    1938 Oct 26 11:19 screen.json\n-rw-rw-rw- 1 aii-agent aii-agent      78 Oct 26 11:19 screen.sha256\n-rw-rw-rw- 1 aii-agent aii-agent   27699 Oct 26 11:19 screen_extras.json\n-rw-rw-rw- 1 aii-agent aii-agent   15782 Oct 26 11:19 screen_input.json\ndrwxrwxrwx 2 aii-agent aii-agent 1008467 Oct 26 11:14 tables\n.:\ntotal 6427\ndrwxrwxrwx 3 aii-agent aii-agent 2000245 Oct 26 11:20 .\ndrwxrwxrwx 7 aii-agent aii-agent 2001576 Oct 26 11:16 ..\ndrwxrwxrwx 2 aii-agent aii-agent       1 Oct 26 10:50 .aii\n-rw-rw-rw- 1 aii-agent aii-agent      54 Oct 26 10:50 .aii_claude_session.json\n-rw-rw-rw- 1 aii-agent aii-agent 1344173 Oct 26 11:20 .repl_agent.ptylog\n-rw-rw-rw- 1 aii-agent aii-agent  460818 Oct 26 11:19 code_demo.ipynb\n-rw-rw-rw- 1 aii-agent aii-agent    9051 Oct 26 10:59 make_mini_demo_data.py\n-rw-rw-rw- 1 aii-agent aii-agent  762309 Oct 26 10:59 mini_demo_data.json\n\n.aii:\ntotal 1954\ndrwxrwxrwx 2 aii-agent aii-agent       1 Oct 26 10:50 .\ndrwxrwxrwx 3 aii-agent aii-agent 2000245 Oct 26 11:20 ..\n4.4M\t.", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [200] ASSISTANT · 2026-10-26 11:21:13 UTC

```
Workspace is 4.4 MB with nothing over the 10 MB floor. Writing the README, the manifest (no heavy paths to decide on), and the structured output.
```

### [201] TOOL CALL — Write · 2026-10-26 11:21:13 UTC

````
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/README.md

# Demo: record repair and a frozen push screen

This folder holds a Colab-ready notebook for the evaluation artifact `art_sV0cQ3ef1ZRQ`, "Record repair and a frozen push screen". That artifact is the CPU-only Step 0 of iteration 4 of a study on algorithm choice in Qwen3-8B, with Llama-3.1-8B as the replication model. The study asks whether temperature, context seeds, instructions, prompt bans, token vetoes or activation directions make the model write a different algorithm than its default.

The notebook runs the artifact's two central stages, `knob` and `screen`, on a 99-cell subset of its knob table. It uses the artifact's own code (`eval.py`, `src/stats.py`, `src/labels.py`, `src/knob.py`, `src/screen.py`, `screen_rule.py`), split into cells with explanations in between. Each change is marked `NOTEBOOK:` in the code. Every recomputed number is checked against the values recorded in the artifact.

## What the notebook shows

These are the results with the original Monte-Carlo sizes (1000 rarefactions, 1000 × 200 bootstrap):

- **Exact reproduction.** All 99 cells match the artifact's knob table on 14 columns (largest difference 2.2e-16). The columns are rarefied Hill-1 at depth 25 with its template and iid 90% CIs, `H1r25_cat`, `H1r10`, Good's coverage, pass rate, pass cost with its Newcombe CI, off-default share, catalogue-only avoidance, and the escape and qualify flags. This holds although Colab's numpy 2.0.2 replaces the original 2.5.4.
- **Screen.** The five screened tasks (T03, T1, T10, T13, T14) reproduce their records in the frozen `screen.json` exactly. Substituting them into the frozen file gives back the published sha256 `d6a2ca9711f461973c39482314a523d448d0590cb40e32432826dec1da4846e8` byte for byte.
- **Path-search task T1.** The model writes BFS, and temperature does not change that. Across T = 0.3–1.3 with top-k 10 or top-p 0.95, 7 of 8 cells have Hill-1 = 1.00 and the eighth 1.04. Seeds and creativity instructions move it little: at most 1.09 for seeds and 1.23 for instructions. Bans move the algorithm but cost pass rate: banning BFS gives Hill-1 1.78 at 48 points. Only the succession ban (2.19 at 12 points) and the SCATTER list ban (2.10 at 14 points) qualify. Random activation directions escape on 1 of 15 (α = 1). On T03, 7 random direction-α cells qualify at 0–4 points.

## Layout

| Path | What it is |
|---|---|
| `code_demo.ipynb` | The demo notebook, executed, with all outputs and the 2×2 summary figure. |
| `mini_demo_data.json` | The demo data: one dataset, `knob_table`, with 99 cells, each carrying its recorded knob-table values and the labelled program rows behind it (6,925 rows in total). `metadata` holds the frozen screen, its sha256, the catalogues of the screened bench tasks and the original parameters. |
| `make_mini_demo_data.py` | The script that built `mini_demo_data.json` from the artifact's files. |
| `.aii/manifest.yaml` | Storage decisions. Nothing in this folder is heavy. |

The 99 cells come in seven groups, ordered so that any prefix of the list is self-consistent:

| Group | Cells | Contents |
|---|---|---|
| `screen:T10`, `screen:T13`, `screen:T14` | 6 each | exp13 random directions `rand1-3`, the HF twin, the modal ban and its vLLM twin |
| `screen:T03` | 25 | the same exp13 cells, plus the exp17 `RAND90xx` directions at α 1 and 2 and their twin |
| `screen:T1` | 21 | the exp17 directions and twin, plus exp9's single BFS ban and its baseline |
| `knobs:T1` | 32 | path search: the temperature × sampler grid, context seeds, creativity instructions, generate-then-select, top-k and list bans, decommitment and random steering, token vetoes, and the 2,000-word novelty instruction |
| `knobs:T03` | 3 | exp13 novelty instruction, nonce ban and one-shot veto |

## How to run

**Colab.** Open `code_demo.ipynb` and choose *Runtime → Run all*. The first code cell installs `loguru`. The notebook reads `mini_demo_data.json` from the repository's raw GitHub URL, or from a local copy next to the notebook if the URL is unavailable.

**Locally** (Python 3.12). Outside Colab, the install cell also pins Colab's versions of numpy, pandas, scipy, matplotlib and pyarrow.

```bash
uv venv --seed --python 3.12 /tmp/demo-venv
uv pip install --python /tmp/demo-venv/bin/python jupyter ipykernel
/tmp/demo-venv/bin/jupyter nbconvert --to notebook --execute code_demo.ipynb --output code_demo.ipynb
```

A clean run takes about 20 s including the package installs; the `knob` stage itself takes about 3 s. The stages write their outputs to `demo_run/`: `data/knob.parquet`, `tables/*.csv` (including `demo_recomputed_vs_recorded.csv`), `screen_input.json`, `screen.json`, `screen.sha256`, `screen_extras.json`, `results/screen_summary.json`, `figures/demo_summary.png` and `logs/eval.log`.

**Parameters.** These are set in the config cell:
- `N_RAREFY`, `N_BOOT` and `N_BOOT_RAREFY` (original 1000 / 1000 / 200). Smaller values run faster and give Hill-1 values within Monte-Carlo error of the recorded ones. Counts-based columns and the screen are exact at any setting.
- `N_CELLS`, the number of demo cells used, at least 6, 99 = all.
- `RUN_STAGES`.

## Changes from the original code

All marked `NOTEBOOK:` in the notebook:

- The program rows come from `mini_demo_data.json` instead of `data/rows.parquet`, which the `rows` stage builds from the 11 dependency artifacts.
- `spec()` reads the bench catalogues from the demo data instead of exp11's `bench/<task>/spec.json`.
- The knob-cell jobs run in-process (`map`) instead of in a spawn `ProcessPoolExecutor`, because spawned workers cannot import functions defined in a notebook. Each cell has its own seed, so the results are identical.
- The screen runs on the tasks whose full input is in the subset, rather than all 14. The source-file sha256 values are taken from the frozen screen. `verification_targets` and `per_task_verdict` are skipped, because they need cells of all 14 tasks.
- `screen_rule.py`'s functions are defined in a cell; `_load_rule()` returns them as a namespace instead of importing the file.
- The other 12 stages (`inventory`, `rows`, `judges`, `route`, `llama`, `other`, `figures`, `rigor`, `wording`, `rivals`, `audit`, `outputs`) need the dependency artifacts or the judge cache. They run in the artifact's own folder with `uv run eval.py --stages all`, in about 1.5 minutes.

## Rebuilding `mini_demo_data.json`

```bash
python3 make_mini_demo_data.py --artifact <evaluation artifact folder> --bench <exp11 artifact folder>/bench --out mini_demo_data.json
```

The script needs pandas and pyarrow. From the evaluation artifact `art_sV0cQ3ef1ZRQ` it reads `data/rows.parquet`, `data/knob.parquet`, `full_eval_out.json`, `screen.json` and `screen.sha256`. From exp11 (`art_0ndRfWKBWclR`) it reads `bench/<task>/spec.json`. The cell selection is the `SELECTION` list at the top of the script.

## Kept artifacts

Every file here is small text or JSON, all of it under 1 MB, and is published with the repository. Nothing stays only on the run's volume.

## Restoring removed files

No path is marked `delete` in `.aii/manifest.yaml`, so nothing needs restoring. `demo_run/` is not part of the repository: running the notebook recreates it in seconds (see *How to run*).
````

### [202] TOOL RESULT — Write · 2026-10-26 11:21:13 UTC

````
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/README.md", "content": "# Demo: record repair and a frozen push screen\n\nThis folder holds a Colab-ready notebook for the evaluation artifact `art_sV0cQ3ef1ZRQ`, \"Record repair and a frozen push screen\". That artifact is the CPU-only Step 0 of iteration 4 of a study on algorithm choice in Qwen3-8B, with Llama-3.1-8B as the replication model. The study asks whether temperature, context seeds, instructions, prompt bans, token vetoes or activation directions make the model write a different algorithm than its default.\n\nThe notebook runs the artifact's two central stages, `knob` and `screen`, on a 99-cell subset of its knob table. It uses the artifact's own code (`eval.py`, `src/stats.py`, `src/labels.py`, `src/knob.py`, `src/screen.py`, `screen_rule.py`), split into cells with explanations in between. Each change is marked `NOTEBOOK:` in the code. Every recomputed number is checked against the values recorded in the artifact.\n\n## What the notebook shows\n\nThese are the results with the original Monte-Carlo sizes (1000 rarefactions, 1000 × 200 bootstrap):\n\n- **Exact reproduction.** All 99 cells match the artifact's knob table on 14 columns (largest difference 2.2e-16). The columns are rarefied Hill-1 at depth 25 with its template and iid 90% CIs, `H1r25_cat`, `H1r10`, Good's coverage, pass rate, pass cost with its Newcombe CI, off-default share, catalogue-only avoidance, and the escape and qualify flags. This holds although Colab's numpy 2.0.2 replaces the original 2.5.4.\n- **Screen.** The five screened tasks (T03, T1, T10, T13, T14) reproduce their records in the frozen `screen.json` exactly. Substituting them into the frozen file gives back the published sha256 `d6a2ca9711f461973c39482314a523d448d0590cb40e32432826dec1da4846e8` byte for byte.\n- **Path-search task T1.** The model writes BFS, and temperature does not change that. Across T = 0.3–1.3 with top-k 10 or top-p 0.95, 7 of 8 cells have Hill-1 = 1.00 and the eighth 1.04. Seeds and creativity instructions move it little: at most 1.09 for seeds and 1.23 for instructions. Bans move the algorithm but cost pass rate: banning BFS gives Hill-1 1.78 at 48 points. Only the succession ban (2.19 at 12 points) and the SCATTER list ban (2.10 at 14 points) qualify. Random activation directions escape on 1 of 15 (α = 1). On T03, 7 random direction-α cells qualify at 0–4 points.\n\n## Layout\n\n| Path | What it is |\n|---|---|\n| `code_demo.ipynb` | The demo notebook, executed, with all outputs and the 2×2 summary figure. |\n| `mini_demo_data.json` | The demo data: one dataset, `knob_table`, with 99 cells, each carrying its recorded knob-table values and the labelled program rows behind it (6,925 rows in total). `metadata` holds the frozen screen, its sha256, the catalogues of the screened bench tasks and the original parameters. |\n| `make_mini_demo_data.py` | The script that built `mini_demo_data.json` from the artifact's files. |\n| `.aii/manifest.yaml` | Storage decisions. Nothing in this folder is heavy. |\n\nThe 99 cells come in seven groups, ordered so that any prefix of the list is self-consistent:\n\n| Group | Cells | Contents |\n|---|---|---|\n| `screen:T10`, `screen:T13`, `screen:T14` | 6 each | exp13 random directions `rand1-3`, the HF twin, the modal ban and its vLLM twin |\n| `screen:T03` | 25 | the same exp13 cells, plus the exp17 `RAND90xx` directions at α 1 and 2 and their twin |\n| `screen:T1` | 21 | the exp17 directions and twin, plus exp9's single BFS ban and its baseline |\n| `knobs:T1` | 32 | path search: the temperature × sampler grid, context seeds, creativity instructions, generate-then-select, top-k and list bans, decommitment and random steering, token vetoes, and the 2,000-word novelty instruction |\n| `knobs:T03` | 3 | exp13 novelty instruction, nonce ban and one-shot veto |\n\n## How to run\n\n**Colab.** Open `code_demo.ipynb` and choose *Runtime → Run all*. The first code cell installs `loguru`. The notebook reads `mini_demo_data.json` from the repository's raw GitHub URL, or from a local copy next to the notebook if the URL is unavailable.\n\n**Locally** (Python 3.12). Outside Colab, the install cell also pins Colab's versions of numpy, pandas, scipy, matplotlib and pyarrow.\n\n```bash\nuv venv --seed --python 3.12 /tmp/demo-venv\nuv pip install --python /tmp/demo-venv/bin/python jupyter ipykernel\n/tmp/demo-venv/bin/jupyter nbconvert --to notebook --execute code_demo.ipynb --output code_demo.ipynb\n```\n\nA clean run takes about 20 s including the package installs; the `knob` stage itself takes about 3 s. The stages write their outputs to `demo_run/`: `data/knob.parquet`, `tables/*.csv` (including `demo_recomputed_vs_recorded.csv`), `screen_input.json`, `screen.json`, `screen.sha256`, `screen_extras.json`, `results/screen_summary.json`, `figures/demo_summary.png` and `logs/eval.log`.\n\n**Parameters.** These are set in the config cell:\n- `N_RAREFY`, `N_BOOT` and `N_BOOT_RAREFY` (original 1000 / 1000 / 200). Smaller values run faster and give Hill-1 values within Monte-Carlo error of the recorded ones. Counts-based columns and the screen are exact at any setting.\n- `N_CELLS`, the number of demo cells used, at least 6, 99 = all.\n- `RUN_STAGES`.\n\n## Changes from the original code\n\nAll marked `NOTEBOOK:` in the notebook:\n\n- The program rows come from `mini_demo_data.json` instead of `data/rows.parquet`, which the `rows` stage builds from the 11 dependency artifacts.\n- `spec()` reads the bench catalogues from the demo data instead of exp11's `bench/<task>/spec.json`.\n- The knob-cell jobs run in-process (`map`) instead of in a spawn `ProcessPoolExecutor`, because spawned workers cannot import functions defined in a notebook. Each cell has its own seed, so the results are identical.\n- The screen runs on the tasks whose full input is in the subset, rather than all 14. The source-file sha256 values are taken from the frozen screen. `verification_targets` and `per_task_verdict` are skipped, because they need cells of all 14 tasks.\n- `screen_rule.py`'s functions are defined in a cell; `_load_rule()` returns them as a namespace instead of importing the file.\n- The other 12 stages (`inventory`, `rows`, `judges`, `route`, `llama`, `other`, `figures`, `rigor`, `wording`, `rivals`, `audit`, `outputs`) need the dependency artifacts or the judge cache. They run in the artifact's own folder with `uv run eval.py --stages all`, in about 1.5 minutes.\n\n## Rebuilding `mini_demo_data.json`\n\n```bash\npython3 make_mini_demo_data.py --artifact <evaluation artifact folder> --bench <exp11 artifact folder>/bench --out mini_demo_data.json\n```\n\nThe script needs pandas and pyarrow. From the evaluation artifact `art_sV0cQ3ef1ZRQ` it reads `data/rows.parquet`, `data/knob.parquet`, `full_eval_out.json`, `screen.json` and `screen.sha256`. From exp11 (`art_0ndRfWKBWclR`) it reads `bench/<task>/spec.json`. The cell selection is the `SELECTION` list at the top of the script.\n\n## Kept artifacts\n\nEvery file here is small text or JSON, all of it under 1 MB, and is published with the repository. Nothing stays only on the run's volume.\n\n## Restoring removed files\n\nNo path is marked `delete` in `.aii/manifest.yaml`, so nothing needs restoring. `demo_run/` is not part of the repository: running the notebook recreates it in seconds (see *How to run*).\n", "structuredPatch": [], "originalFile": null, "userModified": false}
````

### [203] TOOL CALL — Write · 2026-10-26 11:21:13 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/.aii/manifest.yaml

# Storage decisions for this demo folder.
# Nothing heavy lives here: code_demo.ipynb (~0.5 MB), mini_demo_data.json (~0.8 MB), make_mini_demo_data.py and
# README.md are text files under the 10 MB auto-keep floor, and no cache or virtual environment was created in this
# folder (the notebook test venv lives outside it). demo_run/, written when the notebook runs, was removed after testing.
entries: []
```

### [204] TOOL RESULT — Write · 2026-10-26 11:21:13 UTC

```
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/.aii/manifest.yaml", "content": "# Storage decisions for this demo folder.\n# Nothing heavy lives here: code_demo.ipynb (~0.5 MB), mini_demo_data.json (~0.8 MB), make_mini_demo_data.py and\n# README.md are text files under the 10 MB auto-keep floor, and no cache or virtual environment was created in this\n# folder (the notebook test venv lives outside it). demo_run/, written when the notebook runs, was removed after testing.\nentries: []\n", "structuredPatch": [], "originalFile": null, "userModified": false}
```

### [205] TOOL CALL — Write · 2026-10-26 11:21:13 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/.terminal_claude_agent_struct_out.json

{
  "out_expected_files": {
    "notebook": "code_demo.ipynb",
    "mini_data_file": "mini_demo_data.json"
  }
}
```

### [206] TOOL RESULT — Write · 2026-10-26 11:21:13 UTC

```
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_sV0cQ3ef1ZRQ/.terminal_claude_agent_struct_out.json", "content": "{\n  \"out_expected_files\": {\n    \"notebook\": \"code_demo.ipynb\",\n    \"mini_data_file\": \"mini_demo_data.json\"\n  }\n}\n", "structuredPatch": [], "originalFile": null, "userModified": false}
```

### [207] ASSISTANT · 2026-10-26 11:21:23 UTC

```
Final validation of the deliverables: manifest YAML, structured output JSON, and the notebook's final config values.
```

### [208] TOOL CALL — Bash · 2026-10-26 11:21:23 UTC

```
Validate manifest, struct output and final config:
python3 -c "
import json, yaml
print('manifest:', yaml.safe_load(open('.aii/manifest.yaml')))
print('struct out:', json.load(open('.terminal_claude_agent_struct_out.json')))
nb = json.load(open('code_demo.ipynb'))
cfg = [c for c in nb['cells'] if c['id'] == '10ec93e8'][0]
print(''.join(l for l in cfg['source'] if l.startswith(('N_', 'RUN_'))))
" && grep -n "/ai-inventor/aii_data\|run_aRfWvcSWjssb" README.md make_mini_demo_data.py code_demo.ipynb mini_demo_data.json | head; echo "absolute-path scan done"; ls -la
```

### [209] TOOL RESULT — Bash · 2026-10-26 11:21:23 UTC

```
{"stdout": "manifest: {'entries': []}\nstruct out: {'out_expected_files': {'notebook': 'code_demo.ipynb', 'mini_data_file': 'mini_demo_data.json'}}\nN_RAREFY = 1000      # rarefaction subsamples per Hill-1 value\nN_BOOT = 1000        # bootstrap replicates per 90% CI\nN_BOOT_RAREFY = 200  # rarefaction subsamples inside each bootstrap replicate\nN_CELLS = 99         # first N demo cells, at least 6 (the first 6 are the complete T10 screen group); 99 = all\nRUN_STAGES = [\"knob\", \"screen\"]\n\nabsolute-path scan done\ntotal 6520\ndrwxrwxrwx 3 aii-agent aii-agent 2000250 Oct 26 11:21 .\ndrwxrwxrwx 8 aii-agent aii-agent 2001546 Oct 26 11:20 ..\ndrwxrwxrwx 2 aii-agent aii-agent   40500 Oct 26 11:21 .aii\n-rw-rw-rw- 1 aii-agent aii-agent      54 Oct 26 10:50 .aii_claude_session.json\n-rw-rw-rw- 1 aii-agent aii-agent 1391512 Oct 26 11:21 .repl_agent.ptylog\n-rw-rw-rw- 1 aii-agent aii-agent     113 Oct 26 11:21 .terminal_claude_agent_struct_out.json\n-rw-rw-rw- 1 aii-agent aii-agent    7262 Oct 26 11:21 README.md\n-rw-rw-rw- 1 aii-agent aii-agent  460818 Oct 26 11:19 code_demo.ipynb\n-rw-rw-rw- 1 aii-agent aii-agent    9051 Oct 26 10:59 make_mini_demo_data.py\n-rw-rw-rw- 1 aii-agent aii-agent  762309 Oct 26 10:59 mini_demo_data.json", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [210] ASSISTANT · 2026-10-26 11:21:42 UTC

```
I've built the demo notebook and its data, and the notebook passes a clean-venv test in 20 s, using the artifact's original parameters.

`eval.py` is only a stage dispatcher; the computation lives in `src/`. So the notebook runs the artifact's two central stages, `knob` and `screen`, using the original code split into cells. Every change from the original is marked `NOTEBOOK:` in the code. The other 12 stages need files from the 11 upstream artifacts, which the demo data doesn't include; the notebook says so where it lists the stages.

**Demo data.** `mini_demo_data.json` takes 99 cells from one dataset (`knob_table`), plus the 6,925 labelled program rows behind them. The cells are:
- every input the screen reads for five tasks: T10, T13, T14, T03 and T1;
- every knob the study tried on the path-search task T1, each with its baseline ("twin"): the temperature × sampler grid, context seeds, creativity instructions, bans (including a top-5 ban), steering directions, vetoes and the 2,000-word "fully novel" instruction.

**Reproduction.** With the original parameters, all 99 cells match the artifact's recorded values on all 14 compared columns (largest difference 2.2e-16). That holds even though Colab's numpy (2.0.2) is older than the version the artifact used. All five screened tasks reproduce their frozen `screen.json` records exactly. Putting those records back into the frozen file gives the published hash `d6a2ca97…` byte for byte.

**Scaling:**

| Run | Cells | Monte-Carlo sizes | Time | Result |
|---|---|---|---|---|
| Minimum | 6 | 10 / 10 / 10 | 17 s | count columns identical; T10 screen record identical |
| Round 1 | 99 | 100 / 100 / 50 | 6 s | 99/99 count columns identical; all 5 screen records identical |
| Final | 99 | 1000 / 1000 / 200 (original) | 20 s, fresh venv, installs included | every column identical |

**What it shows on T1.** The model writes BFS, and temperature doesn't change that: 7 of the 8 temperature/sampler cells (T 0.3–1.3) have a diversity score (Hill‑1) of exactly 1.00. Seeds and creativity instructions reach at most 1.23. Bans do move the algorithm but cost pass rate: banning BFS by name gives 1.78 at a 48-point drop. Only two T1 cells reach a score of 2 at a cost of 20 points or less: the succession ban and the SCATTER list ban.

Things that differ from what was asked or from the original:
- **Todo list:** this environment has no todo-tracking tool, so I followed the six TODOs in order without one.
- **NotebookEdit:** all 38 cells were created with it. After test runs rewrote the file with outputs, I changed the config values and fixed figure label positions by patching the notebook JSON directly.
- **Skipped in the screen stage:** the 27 verification targets and the per-task verdicts. Both read cells from all 14 tasks, most of which aren't in the 99-cell subset.
- **Data URL:** the GitHub URL currently returns 404 because nothing is pushed yet, so the notebook falls back to the local file.
- **Test outputs:** I deleted `demo_run/`, which the notebook writes when it runs; the executed notebook already contains all its tables and the figure.

I also wrote a README, an empty manifest (nothing over 10 MB) and `.terminal_claude_agent_struct_out.json`.

Files are in `art_sV0cQ3ef1ZRQ/`:
- code_demo.ipynb
- mini_demo_data.json
- make_mini_demo_data.py
- README.md
- .aii/manifest.yaml
- .terminal_claude_agent_struct_out.json
```
