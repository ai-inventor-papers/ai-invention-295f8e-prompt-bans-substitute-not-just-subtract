# gen_demo_art_experiment_40 — report_results

> Phase: `gen_paper_repo` · `gen_demo_art`
> Run: `gen_paper_repo_c164ac661673` — A Random Activation Push Changes a Code Model's Algorithm Where Temperature Does Not
>
> Full, verbatim transcript of this agent task — every system/user prompt, assistant response, thinking block, tool call and tool result — in the order they occurred. Nothing truncated.

## Task: `gen_demo_art_experiment_40` (terminal_claude_agent, claude-opus-5-5)

### [1] CONFIG · 2026-10-26 13:37:53 UTC

```
model: Claude Opus 5.5 | effort: max | permission: bypassPermissions
```

### [2] SYSTEM-USER prompt · 2026-10-26 13:37:59 UTC

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
Your workspace: `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb`

CRITICAL: Every file you create, write, or save MUST be inside this workspace directory (subdirectories OK). You MUST NOT write files anywhere outside this path — external paths are READ-ONLY. Use absolute paths for all file operations.

EVERY file write MUST start with `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/`:
GOOD: `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/file.py`, `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/results/out.json`
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
id: art_e-_q5mSJGrSb
type: experiment
title: Searching for a hidden algorithm switch in code models
summary: >-
  Iteration-8 test of claim K2: is there a certified low-rank causal variable for the algorithm a code model picks? One DAS
  protocol was committed before any GPU use (commit #0, hash-chained, 8 commits verified): linear orthonormal map (ranks 1/2/4/8),
  bounded KL objective, class-margin readout at the decision token. It was applied at three sites: Qwen3-8B T10 connected
  components (BFS/DFS/union-find, token 11 after ' def'); gemma-3-4b-it T1 grid (BFS/DFS only; A* and IDDFS failed adherence);
  and the Qwen T10 task band (blocks 12-23, one shared map). There were seven committed controls (c1-c7). RESULT: K2 DISCONFIRMED
  (p_K2 = 0.037). T10 decision site (rule-chosen L* = 22, k* = 4): TF recovery 8.43, OFF-MANIFOLD (DAS Delta 17.4 vs full-state
  2.1 nats). c2 label controls keep 0.87/0.63/0.77 of the effect (limit 0.10); c3 random-init 0.69 (limit 0.25); c4 and c5
  fail; c1, c6 and c7 pass. In generation (CRN, N = 30, hidden tests), DAS writes 29/30 correct DFS (full-state 2, random
  0), but BFS edits yield 29/30 BFS attempts with only 5 passing tests, so the pooled verdict is NO HANDLE. GRID decision
  site (L* = 16, k* = 4): TF 3.07, OFF-MANIFOLD; c2 0.11-0.20 (2-class shuffles), c3 0.41, c5 and c6 fail; generation BFS
  22/30 vs full 10, random 5, base 6 (SUFFICIENT HANDLE). T10 band (k* = 2): TF 0.82, c3 passes (0.18), c4 passes, c2 fails
  (0.71-0.79), c5 fails on twins (passes c5b), c7 fails; generation BFS 28/30, but DFS sources are routed to BFS (24/30).
  Post hoc, block 24 (full state carries 16 nats): recovery 1.22, c4-c7 pass, yet c2 (0.50-0.61) and c3 (0.54) still fail,
  so the specificity failure is not an artifact of the rule-chosen block. Mediation of iteration 4's 40 random pushes: retrospective
  Spearman 0.39 (bar 0.5), prospective 0.09 on 24 new directions. Clamping the band subspace removes -0.01 of escapes (random
  clamp 0.02; decision-site clamp -0.05). Pushes act elsewhere. No novel algorithm: 0 'other' among 1,857 correct programs.
  Geometry figures plot actual R_8 activation coordinates (MDS/Isomap plus PCA). Placement prompts (seeds, novelty instruction,
  Gemma top-5 ban) stay inside the twin cluster. Provides: method_out.json (exp_gen_sol_out; 8 datasets, 2,042 examples: per-slot
  generation labels, per-pair TF Deltas, mediation slots); results/*.json; results/summary.md; das_maps/ (all fitted maps);
  data/ (samples, labels, TF rows); figures F1-F5; audit/rederive.py (stdlib; 38 checks all match, placebos fail; c3 recomputed
  only from stored means); reproducibility.md. Departures: NVIDIA L4 instead of A4500; B3 and the Gemma band dropped; band
  fits 109 steps and 2 seeds; S2 engine check not run; judge not called on labeller disagreements.
workspace_path: >-
  /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40
out_expected_files:
- method.py
- full_method_out.json
- mini_method_out.json
- preview_method_out.json
- reproducibility.md
out_demo_files:
- path: method.py
  description: Research methodology implementation
</artifact_info>

<github_repo>
Repo URL: https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract
Raw data URL: https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-8/experiment-40/demo/mini_demo_data.json

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
GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-8/experiment-40/demo/mini_demo_data.json"
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
To test-run the notebook in a clean environment (simulating Colab), use the disposable venv at `/tmp/aii_nb_test_envs/art_e-_q5mSJGrSb-df3879c8a834`. It is on this machine's local disk, outside your workspace, which is on a slow network volume: never create a venv inside your workspace.
```bash
UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_e-_q5mSJGrSb-df3879c8a834
UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_e-_q5mSJGrSb-df3879c8a834/bin/python jupyter ipykernel
/tmp/aii_nb_test_envs/art_e-_q5mSJGrSb-df3879c8a834/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb
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
TODO 6. Verify: (1) code_demo.ipynb contains GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-8/experiment-40/demo/mini_demo_data.json" exactly, (2) mini_demo_data.json exists, (3) uses GitHub URL pattern not just open('mini_demo_data.json').
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

### [3] ASSISTANT · 2026-10-26 13:38:19 UTC

```
I'll start by loading the two required skills and looking at the artifact and my workspace in parallel.
```

### [4] TOOL CALL — Skill · 2026-10-26 13:38:19 UTC

```
aii-colab
```

### [5] TOOL CALL — Skill · 2026-10-26 13:38:19 UTC

```
aii-long-running-tasks
```

### [6] TOOL RESULT — Skill · 2026-10-26 13:38:19 UTC

```
{"success": true, "commandName": "aii-colab"}
```

### [7] TOOL RESULT — Skill · 2026-10-26 13:38:19 UTC

```
{"success": true, "commandName": "aii-long-running-tasks"}
```

### [8] TOOL CALL — Bash · 2026-10-26 13:38:19 UTC

```
List workspace and artifact directories:
pwd && ls -la && ls -la .aii 2>/dev/null; git log --oneline -5 2>/dev/null; echo "---- ARTIFACT ----"; ls -la /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40
```

### [9] TOOL RESULT — Bash · 2026-10-26 13:38:19 UTC

```
{"stdout": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb\ntotal 2970\ndrwxrwxrwx 3 aii-agent aii-agent 1003476 Oct 26 13:37 .\ndrwxrwxrwx 6 aii-agent aii-agent 2000185 Oct 26 13:37 ..\ndrwxrwxrwx 2 aii-agent aii-agent       1 Oct 26 13:36 .aii\n-rw-rw-rw- 1 aii-agent aii-agent      54 Oct 26 13:37 .aii_claude_session.json\n-rw-rw-rw- 1 aii-agent aii-agent   35541 Oct 26 13:38 .repl_agent.ptylog\ntotal 981\ndrwxrwxrwx 2 aii-agent aii-agent       1 Oct 26 13:36 .\ndrwxrwxrwx 3 aii-agent aii-agent 1003476 Oct 26 13:37 ..\n---- ARTIFACT ----\ntotal 26704\ndrwxrwxrwx 16 aii-agent aii-agent 2016627 Oct 23 08:56 .\ndrwxrwxrwx  9 aii-agent aii-agent 3000129 Oct 23 02:17 ..\ndrwxrwxrwx  2 aii-agent aii-agent   78500 Oct 23 06:04 .aii\n-rw-rw-rw-  1 aii-agent aii-agent      54 Oct 23 05:51 .aii_claude_session.json\n-rw-rw-rw-  1 aii-agent aii-agent    7417 Oct 23 06:04 .aii_worker_result.json\n-rw-rw-rw-  1 aii-agent aii-agent   72394 Oct 23 06:04 .repl_agent.ptylog\n-rw-rw-rw-  1 aii-agent aii-agent    3294 Oct 23 05:53 .terminal_claude_agent_struct_out.json\n-rw-rw-rw-  1 aii-agent aii-agent   28338 Oct 23 05:59 README.md\ndrwxrwxrwx  2 aii-agent aii-agent 1001287 Oct 23 03:18 audit\ndrwxrwxrwx  2 aii-agent aii-agent 1014720 Oct 23 08:56 cache\n-rw-rw-rw-  1 aii-agent aii-agent    2794 Oct 23 04:53 commitments.log\ndrwxrwxrwx  2 aii-agent aii-agent 2000313 Oct 23 05:00 das_maps\ndrwxrwxrwx  2 aii-agent aii-agent 2000965 Oct 23 04:31 data\ndrwxrwxrwx  2 aii-agent aii-agent 2000118 Oct 23 05:06 figures\n-rw-rw-rw-  1 aii-agent aii-agent 1846281 Oct 23 05:48 full_method_out.json\ndrwxrwxrwx 10 aii-agent aii-agent 2014577 Oct 23 01:49 inputs\ndrwxrwxrwx  2 aii-agent aii-agent 1017243 Oct 23 05:14 logs\n-rw-rw-rw-  1 aii-agent aii-agent    2745 Oct 23 03:50 method.py\n-rw-rw-rw-  1 aii-agent aii-agent 1644951 Oct 23 05:47 method_out.json\n-rw-rw-rw-  1 aii-agent aii-agent  250939 Oct 23 05:48 mini_method_out.json\ndrwxrwxrwx  2 aii-agent aii-agent 1004419 Oct 23 04:53 predictions\n-rw-rw-rw-  1 aii-agent aii-agent  220146 Oct 23 05:48 preview_method_out.json\ndrwxrwxrwx  2 aii-agent aii-agent 2000132 Oct 23 01:34 prompts\n-rw-rw-rw-  1 aii-agent aii-agent    2834 Oct 23 05:37 pyproject.toml\n-rw-rw-rw-  1 aii-agent aii-agent   10915 Oct 23 05:42 reproducibility.md\ndrwxrwxrwx  2 aii-agent aii-agent 1069901 Oct 23 05:20 results\ndrwxrwxrwx  2 aii-agent aii-agent 1000451 Oct 23 04:36 scripts\ndrwxrwxrwx  2 aii-agent aii-agent 1023929 Oct 23 08:56 src\ndrwxrwxrwx  2 aii-agent aii-agent 1000693 Oct 23 02:38 tests", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [10] THINKING · 2026-10-26 13:38:29 UTC

```
Both skills are loaded. Since there's no todo tool available, I'll track the six TODOs in a scratchpad file and start by reading the artifact's script to see how it's laid out.
```

### [11] TOOL CALL — ToolSearch · 2026-10-26 13:38:29 UTC

```
{'query': 'todo task list tracking', 'max_results': 5}
```

### [12] TOOL RESULT — ToolSearch · 2026-10-26 13:38:29 UTC

```
{"matches": ["CronList", "TaskStop", "EndConversation", "EnterWorktree", "SendMessage"], "query": "todo task list tracking", "total_deferred_tools": 28}
```

### [13] TOOL CALL — Bash · 2026-10-26 13:38:29 UTC

```
Read method.py, pyproject, and artifact struct output:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40; cat -n $A/method.py; echo "==== pyproject ===="; cat $A/pyproject.toml; echo "==== struct out ===="; cat $A/.terminal_claude_agent_struct_out.json
```

### [14] TOOL RESULT — Bash · 2026-10-26 13:38:29 UTC

```
{"stdout": "     1\t#!/usr/bin/env python3\n     2\t\"\"\"Entry point: runs the whole iteration-8 DAS experiment in stage order (each stage is resumable and skips work\n     3\twhose result file already exists). GPU stages load one model at a time.\n     4\t\n     5\t  S0  src/s0_inputs.py      copy + hash inputs; dependency extraction (all ten datasets of art_j3Rm_lr2nzR6)\n     6\t  S1  src/prompts8.py       T10 and GRID prompt sets, splits\n     7\t  #0  src/commit0.py        protocol commitment (before any GPU use)\n     8\t  S3-S6  src/run_dec.py     decision site per unit: token maps, adherence, commit #1, caches, unit tests, scan, fits,\n     9\t                            controls c1/c2/c4/c5/c6/c7, baselines\n    10\t  S9  src/run_gen.py        generation cells (commit #2 first), labelled by src/label8.py\n    11\t  S8  src/run_rinit.py      random-initialisation control c3 (decision site; --band for the band)\n    12\t  S7  src/run_band.py       T10 task band\n    13\t  S10 src/run_med.py        mediation of iteration 4's random pushes (commit #3, #4)\n    14\t  post src/run_post.py      per-pair label-control test for p_K2 (T10)\n    15\t  S11-S12 src/analysis8.py, src/figures8.py, src/novelty8.py, src/digest8.py, src/outputs8.py, audit/rederive.py\n    16\t\n    17\tUsage: .venv/bin/python method.py [--cpu-only]\n    18\t\"\"\"\n    19\t\n    20\tfrom __future__ import annotations\n    21\t\n    22\timport argparse\n    23\timport subprocess\n    24\timport sys\n    25\tfrom pathlib import Path\n    26\t\n    27\tROOT = Path(__file__).resolve().parent\n    28\tPY = sys.executable\n    29\t\n    30\t\n    31\tdef run(*args: str) -> None:\n    32\t    print(\"+\", \" \".join(args), flush=True)\n    33\t    subprocess.run([PY, *args], cwd=ROOT, check=True)\n    34\t\n    35\t\n    36\tdef main() -> None:\n    37\t    ap = argparse.ArgumentParser()\n    38\t    ap.add_argument(\"--cpu-only\", action=\"store_true\", help=\"only the analysis / output stages\")\n    39\t    a = ap.parse_args()\n    40\t    if not a.cpu_only:\n    41\t        run(\"src/s0_inputs.py\")\n    42\t        run(\"src/prompts8.py\")\n    43\t        run(\"src/commit0.py\")\n    44\t        run(\"src/run_dec.py\", \"--unit\", \"T10\")\n    45\t        run(\"src/run_gen.py\", \"--unit\", \"T10\", \"--sites\", \"dec\")\n    46\t        run(\"src/run_rinit.py\", \"--unit\", \"T10\")\n    47\t        run(\"src/run_band.py\")\n    48\t        run(\"src/run_gen.py\", \"--unit\", \"T10\", \"--sites\", \"band\")\n    49\t        run(\"src/run_rinit.py\", \"--unit\", \"T10\", \"--band\")\n    50\t        run(\"src/run_dec.py\", \"--unit\", \"GRID\")\n    51\t        run(\"src/run_gen.py\", \"--unit\", \"GRID\", \"--sites\", \"dec\")\n    52\t        run(\"src/run_rinit.py\", \"--unit\", \"GRID\")\n    53\t        run(\"src/run_med.py\")\n    54\t        run(\"src/run_post.py\", \"--unit\", \"T10\")\n    55\t        run(\"src/run_dec.py\", \"--unit\", \"T10\", \"--force_L\", \"24\")\n    56\t        run(\"src/label8.py\", \"--unit\", \"T10\")\n    57\t        run(\"src/label8.py\", \"--unit\", \"GRID\")\n    58\t    run(\"src/analysis8.py\")\n    59\t    run(\"src/novelty8.py\")\n    60\t    run(\"src/figures8.py\")\n    61\t    run(\"src/digest8.py\")\n    62\t    run(\"src/outputs8.py\")\n    63\t    subprocess.run([sys.executable, \"audit/rederive.py\"], cwd=ROOT, check=True)\n    64\t\n    65\t\n    66\tif __name__ == \"__main__\":\n    67\t    main()\n==== pyproject ====\n[project]\nname = \"das8-hidden-algorithm-switch\"\nversion = \"1.0.0\"\ndescription = \"Iteration 8: one DAS protocol (linear orthonormal map, bounded KL objective, class-margin readout) at the decision token and task band of Qwen3-8B and gemma-3-4b-it, with seven committed controls, generation validation and mediation of random pushes.\"\nrequires-python = \"==3.12.*\"\n# Every package installed in .venv, pinned with == (identical to `uv pip freeze --python .venv/bin/python`;\n# the uv-created venv has no pip). Python 3.12.14, uv 0.6.14; torch 2.8.0 wheels are PyPI's CUDA 12.8 build.\ndependencies = [\n    \"accelerate==1.15.0\",\n    \"annotated-types==0.8.0\",\n    \"anyio==4.15.1\",\n    \"astor==0.8.1\",\n    \"attrs==26.1.0\",\n    \"certifi==2026.10.19\",\n    \"charset-normalizer==3.5.2\",\n    \"cloudpickle==3.1.2\",\n    \"contourpy==1.4.0\",\n    \"cycler==0.12.1\",\n    \"filelock==4.2.4\",\n    \"fonttools==4.67.0\",\n    \"formulaic==1.2.2\",\n    \"fsspec==2026.9.0\",\n    \"h11==0.16.0\",\n    \"hf-xet==1.7.0\",\n    \"httpcore2==2.16.0\",\n    \"httpx2==2.16.0\",\n    \"huggingface-hub==0.36.2\",\n    \"idna==3.20\",\n    \"interface-meta==2.0.1\",\n    \"jinja2==3.1.6\",\n    \"jiter==0.17.0\",\n    \"joblib==1.6.0\",\n    \"jsonschema-specifications==2025.9.1\",\n    \"jsonschema==4.26.0\",\n    \"kiwisolver==1.5.1\",\n    \"loguru==0.7.3\",\n    \"markupsafe==3.0.4\",\n    \"matplotlib==3.11.2\",\n    \"mpmath==1.3.0\",\n    \"narwhals==2.27.1\",\n    \"networkx==3.7\",\n    \"numpy==2.2.6\",\n    \"nvidia-cublas-cu12==12.8.4.1\",\n    \"nvidia-cuda-cupti-cu12==12.8.90\",\n    \"nvidia-cuda-nvrtc-cu12==12.8.93\",\n    \"nvidia-cuda-runtime-cu12==12.8.90\",\n    \"nvidia-cudnn-cu12==9.10.2.21\",\n    \"nvidia-cufft-cu12==11.3.3.83\",\n    \"nvidia-cufile-cu12==1.13.1.3\",\n    \"nvidia-curand-cu12==10.3.9.90\",\n    \"nvidia-cusolver-cu12==11.7.3.90\",\n    \"nvidia-cusparse-cu12==12.5.8.93\",\n    \"nvidia-cusparselt-cu12==0.7.1\",\n    \"nvidia-nccl-cu12==2.27.3\",\n    \"nvidia-nvjitlink-cu12==12.8.93\",\n    \"nvidia-nvtx-cu12==12.8.90\",\n    \"openai==3.35.1\",\n    \"packaging==26.3\",\n    \"pandas==3.0.6\",\n    \"patsy==1.0.3\",\n    \"pillow==13.0.0\",\n    \"psutil==7.2.2\",\n    \"pydantic-core==2.50.1\",\n    \"pydantic==2.14.1\",\n    \"pyparsing==3.3.3\",\n    \"python-dateutil==3.0.0\",\n    \"pyyaml==6.0.3\",\n    \"rapidfuzz==3.14.6\",\n    \"referencing==0.37.0\",\n    \"regex==2026.9.29\",\n    \"requests==2.34.2\",\n    \"rpds-py==2026.9.1\",\n    \"safetensors==0.8.0\",\n    \"scikit-learn==1.9.1\",\n    \"scipy==1.18.1\",\n    \"setuptools==84.2.1\",\n    \"six==1.17.0\",\n    \"sniffio==1.3.1\",\n    \"statsmodels==0.15.0\",\n    \"sympy==1.14.0\",\n    \"tenacity==9.2.1\",\n    \"threadpoolctl==3.7.0\",\n    \"tokenizers==0.22.2\",\n    \"torch==2.8.0\",\n    \"tqdm==4.70.1\",\n    \"transformers==4.57.6\",\n    \"triton==3.4.0\",\n    \"truststore==0.10.5\",\n    \"typing-extensions==4.16.0\",\n    \"typing-inspection==0.4.4\",\n    \"tzdata==2026.5\",\n    \"urllib3==2.8.0\",\n    \"wrapt==2.5.1\",\n]\n==== struct out ====\n{\n \"title\": \"Searching for a hidden algorithm switch in code models\",\n \"layman_summary\": \"Looks inside two AI coding models for a small internal 'switch' that decides which algorithm they write; finds edits that steer the choice but no switch that passes all the checks.\",\n \"summary\": \"Iteration-8 test of claim K2: is there a certified low-rank causal variable for the algorithm a code model picks? One DAS protocol was committed before any GPU use (commit #0, hash-chained, 8 commits verified): linear orthonormal map (ranks 1/2/4/8), bounded KL objective, class-margin readout at the decision token. It was applied at three sites: Qwen3-8B T10 connected components (BFS/DFS/union-find, token 11 after ' def'); gemma-3-4b-it T1 grid (BFS/DFS only; A* and IDDFS failed adherence); and the Qwen T10 task band (blocks 12-23, one shared map). There were seven committed controls (c1-c7). RESULT: K2 DISCONFIRMED (p_K2 = 0.037). T10 decision site (rule-chosen L* = 22, k* = 4): TF recovery 8.43, OFF-MANIFOLD (DAS Delta 17.4 vs full-state 2.1 nats). c2 label controls keep 0.87/0.63/0.77 of the effect (limit 0.10); c3 random-init 0.69 (limit 0.25); c4 and c5 fail; c1, c6 and c7 pass. In generation (CRN, N = 30, hidden tests), DAS writes 29/30 correct DFS (full-state 2, random 0), but BFS edits yield 29/30 BFS attempts with only 5 passing tests, so the pooled verdict is NO HANDLE. GRID decision site (L* = 16, k* = 4): TF 3.07, OFF-MANIFOLD; c2 0.11-0.20 (2-class shuffles), c3 0.41, c5 and c6 fail; generation BFS 22/30 vs full 10, random 5, base 6 (SUFFICIENT HANDLE). T10 band (k* = 2): TF 0.82, c3 passes (0.18), c4 passes, c2 fails (0.71-0.79), c5 fails on twins (passes c5b), c7 fails; generation BFS 28/30, but DFS sources are routed to BFS (24/30). Post hoc, block 24 (full state carries 16 nats): recovery 1.22, c4-c7 pass, yet c2 (0.50-0.61) and c3 (0.54) still fail, so the specificity failure is not an artifact of the rule-chosen block. Mediation of iteration 4's 40 random pushes: retrospective Spearman 0.39 (bar 0.5), prospective 0.09 on 24 new directions. Clamping the band subspace removes -0.01 of escapes (random clamp 0.02; decision-site clamp -0.05). Pushes act elsewhere. No novel algorithm: 0 'other' among 1,857 correct programs. Geometry figures plot actual R_8 activation coordinates (MDS/Isomap plus PCA). Placement prompts (seeds, novelty instruction, Gemma top-5 ban) stay inside the twin cluster. Provides: method_out.json (exp_gen_sol_out; 8 datasets, 2,042 examples: per-slot generation labels, per-pair TF Deltas, mediation slots); results/*.json; results/summary.md; das_maps/ (all fitted maps); data/ (samples, labels, TF rows); figures F1-F5; audit/rederive.py (stdlib; 38 checks all match, placebos fail; c3 recomputed only from stored means); reproducibility.md. Departures: NVIDIA L4 instead of A4500; B3 and the Gemma band dropped; band fits 109 steps and 2 seeds; S2 engine check not run; judge not called on labeller disagreements.\",\n \"out_expected_files\": {\n  \"script\": \"method.py\",\n  \"full_output\": \"full_method_out.json\",\n  \"mini_output\": \"mini_method_out.json\",\n  \"preview_output\": \"preview_method_out.json\",\n  \"reproducibility\": \"reproducibility.md\"\n },\n \"upload_ignore_regexes\": [\n  \"(^|/)cache/\",\n  \"(^|/)\\\\.venv/\",\n  \"(^|/)__pycache__/\"\n ]\n}", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [15] TOOL CALL — Bash · 2026-10-26 13:38:29 UTC

```
List artifact subdirectories and sizes:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40; for d in src scripts audit results data das_maps figures inputs logs predictions prompts tests cache .aii; do echo "==== $d ===="; ls -la $A/$d | head -60; done; du -sh $A/* 2>/dev/null | sort -h | tail -30
```

### [16] TOOL RESULT — Bash · 2026-10-26 13:38:29 UTC

```
{"stdout": "==== src ====\ntotal 3215\ndrwxrwxrwx  2 aii-agent aii-agent 1023929 Oct 23 08:56 .\ndrwxrwxrwx 16 aii-agent aii-agent 2016627 Oct 23 08:56 ..\n-rw-rw-rw-  1 aii-agent aii-agent   16793 Oct 23 04:37 analysis8.py\n-rw-rw-rw-  1 aii-agent aii-agent    9367 Oct 23 01:05 cfg8.py\n-rw-rw-rw-  1 aii-agent aii-agent    7495 Oct 23 01:45 commit0.py\n-rw-rw-rw-  1 aii-agent aii-agent    2122 Oct 23 01:39 commit8.py\n-rw-rw-rw-  1 aii-agent aii-agent   25942 Oct 23 02:44 das8.py\n-rw-rw-rw-  1 aii-agent aii-agent    5978 Oct 23 03:34 digest8.py\n-rw-rw-rw-  1 aii-agent aii-agent   19203 Oct 23 01:19 engine8.py\n-rw-rw-rw-  1 aii-agent aii-agent   13338 Oct 23 05:20 figures8.py\n-rw-rw-rw-  1 aii-agent aii-agent    6657 Oct 23 01:48 gen8.py\n-rw-rw-rw-  1 aii-agent aii-agent    4455 Oct 23 01:24 grid_prompts.py\n-rw-rw-rw-  1 aii-agent aii-agent    7559 Oct 23 02:11 label8.py\n-rw-rw-rw-  1 aii-agent aii-agent    6815 Oct 23 02:57 novelty8.py\n-rw-rw-rw-  1 aii-agent aii-agent    7548 Oct 23 05:26 outputs8.py\n-rw-rw-rw-  1 aii-agent aii-agent   11117 Oct 23 01:33 prompts8.py\n-rw-rw-rw-  1 aii-agent aii-agent   15168 Oct 23 01:53 run_band.py\n-rw-rw-rw-  1 aii-agent aii-agent   36244 Oct 23 03:41 run_dec.py\n-rw-rw-rw-  1 aii-agent aii-agent   11272 Oct 23 03:44 run_gen.py\n-rw-rw-rw-  1 aii-agent aii-agent   14900 Oct 23 04:16 run_med.py\n-rw-rw-rw-  1 aii-agent aii-agent    2680 Oct 23 02:27 run_post.py\n-rw-rw-rw-  1 aii-agent aii-agent    7303 Oct 23 04:36 run_rinit.py\n-rw-rw-rw-  1 aii-agent aii-agent    7044 Oct 23 05:38 s0_inputs.py\n-rw-rw-rw-  1 aii-agent aii-agent    6042 Oct 23 01:39 stats8.py\n==== scripts ====\ntotal 2953\ndrwxrwxrwx  2 aii-agent aii-agent 1000451 Oct 23 04:36 .\ndrwxrwxrwx 16 aii-agent aii-agent 2016627 Oct 23 08:56 ..\n-rwxrwxrwx  1 aii-agent aii-agent    1024 Oct 23 02:10 gpu_queue.sh\n-rwxrwxrwx  1 aii-agent aii-agent     581 Oct 23 02:27 gpu_queue2.sh\n-rwxrwxrwx  1 aii-agent aii-agent    1135 Oct 23 03:09 gpu_queue3.sh\n-rwxrwxrwx  1 aii-agent aii-agent    1031 Oct 23 03:42 gpu_queue4.sh\n-rwxrwxrwx  1 aii-agent aii-agent     456 Oct 23 04:19 gpu_queue5.sh\n-rwxrwxrwx  1 aii-agent aii-agent     394 Oct 23 04:36 gpu_queue6.sh\n==== audit ====\ntotal 2961\ndrwxrwxrwx  2 aii-agent aii-agent 1001287 Oct 23 03:18 .\ndrwxrwxrwx 16 aii-agent aii-agent 2016627 Oct 23 08:56 ..\n-rw-rw-rw-  1 aii-agent aii-agent   13186 Oct 23 05:39 rederive.py\n==== results ====\ntotal 3721\ndrwxrwxrwx  2 aii-agent aii-agent 1069901 Oct 23 05:20 .\ndrwxrwxrwx 16 aii-agent aii-agent 2016627 Oct 23 08:56 ..\n-rw-rw-rw-  1 aii-agent aii-agent   33004 Oct 23 05:05 analysis.json\n-rw-rw-rw-  1 aii-agent aii-agent   11711 Oct 23 03:29 band_T10.json\n-rw-rw-rw-  1 aii-agent aii-agent    8153 Oct 23 03:06 band_T10_partial.json\n-rw-rw-rw-  1 aii-agent aii-agent      79 Oct 23 01:46 commit0_done.json\n-rw-rw-rw-  1 aii-agent aii-agent      43 Oct 23 05:00 costs.json\n-rw-rw-rw-  1 aii-agent aii-agent   17866 Oct 23 03:52 dec_GRID.json\n-rw-rw-rw-  1 aii-agent aii-agent   22482 Oct 23 02:24 dec_T10.json\n-rw-rw-rw-  1 aii-agent aii-agent   22686 Oct 23 04:31 dec_T10_L24.json\n-rw-rw-rw-  1 aii-agent aii-agent    3967 Oct 23 05:45 deviations.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent       4 Oct 23 03:59 gen_done_GRID.flag\n-rw-rw-rw-  1 aii-agent aii-agent       4 Oct 23 04:56 gen_done_T10.flag\n-rw-rw-rw-  1 aii-agent aii-agent    4076 Oct 23 05:20 geometry.json\n-rw-rw-rw-  1 aii-agent aii-agent       5 Oct 23 04:57 gpu_queue5_done.flag\n-rw-rw-rw-  1 aii-agent aii-agent       5 Oct 23 05:00 gpu_queue6_done.flag\n-rw-rw-rw-  1 aii-agent aii-agent       5 Oct 23 04:31 gpu_queue_done.flag\n-rw-rw-rw-  1 aii-agent aii-agent   24498 Oct 23 04:56 mediation_T10.json\n-rw-rw-rw-  1 aii-agent aii-agent     436 Oct 23 05:00 novelty_audit.json\n-rw-rw-rw-  1 aii-agent aii-agent    3839 Oct 23 03:16 positioning.json\n-rw-rw-rw-  1 aii-agent aii-agent     733 Oct 23 04:10 post_T10.json\n-rw-rw-rw-  1 aii-agent aii-agent    6340 Oct 23 05:39 rederive.json\n-rw-rw-rw-  1 aii-agent aii-agent     995 Oct 23 04:02 rinit_GRID.json\n-rw-rw-rw-  1 aii-agent aii-agent     985 Oct 23 02:38 rinit_T10.json\n-rw-rw-rw-  1 aii-agent aii-agent     987 Oct 23 05:00 rinit_T10_L24.json\n-rw-rw-rw-  1 aii-agent aii-agent     574 Oct 23 04:06 rinit_T10_band.json\n-rw-rw-rw-  1 aii-agent aii-agent  223213 Oct 23 02:44 s3_GRID.json\n-rw-rw-rw-  1 aii-agent aii-agent  306404 Oct 23 01:49 s3_T10.json\n-rw-rw-rw-  1 aii-agent aii-agent    4233 Oct 23 02:50 scan_GRID.json\n-rw-rw-rw-  1 aii-agent aii-agent    4454 Oct 23 02:07 scan_T10.json\n-rw-rw-rw-  1 aii-agent aii-agent   12526 Oct 23 05:28 summary.md\n-rw-rw-rw-  1 aii-agent aii-agent     807 Oct 23 02:51 unit_tests_cpu.json\n-rw-rw-rw-  1 aii-agent aii-agent     342 Oct 23 02:46 unit_tests_gpu_GRID.json\n-rw-rw-rw-  1 aii-agent aii-agent     335 Oct 23 01:52 unit_tests_gpu_T10.json\n==== data ====\ntotal 13812\ndrwxrwxrwx  2 aii-agent aii-agent 2000965 Oct 23 04:31 .\ndrwxrwxrwx 16 aii-agent aii-agent 2016627 Oct 23 08:56 ..\n-rw-rw-rw-  1 aii-agent aii-agent  381187 Oct 23 03:59 labels_GRID.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent 2556804 Oct 23 04:57 labels_T10.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent   46427 Oct 23 03:46 pairs_GRID.json\n-rw-rw-rw-  1 aii-agent aii-agent  165032 Oct 23 04:13 pairs_T10.json\n-rw-rw-rw-  1 aii-agent aii-agent  337025 Oct 23 03:59 samples_GRID.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent 2097222 Oct 23 04:56 samples_T10.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent  319739 Oct 23 03:52 tf_GRID_dec.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent   42989 Oct 23 03:50 tf_GRID_dec_perm_L16.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent  179917 Oct 23 03:29 tf_T10_band.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent 1750256 Oct 23 02:24 tf_T10_dec.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent 1772528 Oct 23 04:31 tf_T10_dec_L24.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent  226537 Oct 23 04:10 tf_T10_dec_perm_L22.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent  225998 Oct 23 04:28 tf_T10_dec_perm_L24.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent   20097 Oct 23 04:56 timing_gen.jsonl\n==== das_maps ====\ntotal 7145\ndrwxrwxrwx  2 aii-agent aii-agent 2000313 Oct 23 05:00 .\ndrwxrwxrwx 16 aii-agent aii-agent 2016627 Oct 23 08:56 ..\n-rw-rw-rw-  1 aii-agent aii-agent   83694 Oct 23 03:49 GRID_dec_L16_perm_shuffle0.pt\n-rw-rw-rw-  1 aii-agent aii-agent   83694 Oct 23 03:50 GRID_dec_L16_perm_shuffle1.pt\n-rw-rw-rw-  1 aii-agent aii-agent   83694 Oct 23 03:50 GRID_dec_L16_perm_shuffle2.pt\n-rw-rw-rw-  1 aii-agent aii-agent   11986 Oct 23 02:55 GRID_dec_L16_rank1only.pt\n-rw-rw-rw-  1 aii-agent aii-agent   83680 Oct 23 04:02 GRID_dec_L16_rinit_seed0.pt\n-rw-rw-rw-  1 aii-agent aii-agent   83574 Oct 23 02:52 GRID_dec_L16_seed0.pt\n-rw-rw-rw-  1 aii-agent aii-agent   83574 Oct 23 02:53 GRID_dec_L16_seed1.pt\n-rw-rw-rw-  1 aii-agent aii-agent   83574 Oct 23 02:54 GRID_dec_L16_seed2.pt\n-rw-rw-rw-  1 aii-agent aii-agent  132719 Oct 23 03:09 T10_band_perm_pi1.pt\n-rw-rw-rw-  1 aii-agent aii-agent  132719 Oct 23 03:11 T10_band_perm_pi2.pt\n-rw-rw-rw-  1 aii-agent aii-agent  132740 Oct 23 03:13 T10_band_perm_prompt.pt\n-rw-rw-rw-  1 aii-agent aii-agent  132740 Oct 23 04:06 T10_band_rinit_seed0.pt\n-rw-rw-rw-  1 aii-agent aii-agent  132698 Oct 23 03:03 T10_band_seed0.pt\n-rw-rw-rw-  1 aii-agent aii-agent  132698 Oct 23 03:06 T10_band_seed1.pt\n-rw-rw-rw-  1 aii-agent aii-agent  132740 Oct 23 02:19 T10_dec_L22_perm_pi1.pt\n-rw-rw-rw-  1 aii-agent aii-agent  132740 Oct 23 02:20 T10_dec_L22_perm_pi2.pt\n-rw-rw-rw-  1 aii-agent aii-agent  132825 Oct 23 02:21 T10_dec_L22_perm_prompt.pt\n-rw-rw-rw-  1 aii-agent aii-agent   18059 Oct 23 02:11 T10_dec_L22_rank1only.pt\n-rw-rw-rw-  1 aii-agent aii-agent  132825 Oct 23 02:38 T10_dec_L22_rinit_seed0.pt\n-rw-rw-rw-  1 aii-agent aii-agent  132719 Oct 23 02:08 T10_dec_L22_seed0.pt\n-rw-rw-rw-  1 aii-agent aii-agent  132719 Oct 23 02:09 T10_dec_L22_seed1.pt\n-rw-rw-rw-  1 aii-agent aii-agent  132719 Oct 23 02:11 T10_dec_L22_seed2.pt\n-rw-rw-rw-  1 aii-agent aii-agent  132740 Oct 23 04:26 T10_dec_L24_perm_pi1.pt\n-rw-rw-rw-  1 aii-agent aii-agent  132740 Oct 23 04:27 T10_dec_L24_perm_pi2.pt\n-rw-rw-rw-  1 aii-agent aii-agent  132825 Oct 23 04:28 T10_dec_L24_perm_prompt.pt\n-rw-rw-rw-  1 aii-agent aii-agent   18059 Oct 23 04:18 T10_dec_L24_rank1only.pt\n-rw-rw-rw-  1 aii-agent aii-agent  132825 Oct 23 05:00 T10_dec_L24_rinit_seed0.pt\n-rw-rw-rw-  1 aii-agent aii-agent  132719 Oct 23 04:14 T10_dec_L24_seed0.pt\n-rw-rw-rw-  1 aii-agent aii-agent  132719 Oct 23 04:16 T10_dec_L24_seed1.pt\n-rw-rw-rw-  1 aii-agent aii-agent  132719 Oct 23 04:17 T10_dec_L24_seed2.pt\n==== figures ====\ntotal 5136\ndrwxrwxrwx  2 aii-agent aii-agent 2000118 Oct 23 05:06 .\ndrwxrwxrwx 16 aii-agent aii-agent 2016627 Oct 23 08:56 ..\n-rw-rw-rw-  1 aii-agent aii-agent   20245 Oct 23 05:20 F1_scan_profile.pdf\n-rw-rw-rw-  1 aii-agent aii-agent  163888 Oct 23 05:20 F1_scan_profile.png\n-rw-rw-rw-  1 aii-agent aii-agent   20394 Oct 23 05:20 F2_recovery_by_rank.pdf\n-rw-rw-rw-  1 aii-agent aii-agent  138947 Oct 23 05:20 F2_recovery_by_rank.png\n-rw-rw-rw-  1 aii-agent aii-agent   41216 Oct 23 05:20 F3_geometry_GRID.pdf\n-rw-rw-rw-  1 aii-agent aii-agent  238589 Oct 23 05:20 F3_geometry_GRID.png\n-rw-rw-rw-  1 aii-agent aii-agent   45670 Oct 23 05:20 F3_geometry_T10.pdf\n-rw-rw-rw-  1 aii-agent aii-agent  239302 Oct 23 05:20 F3_geometry_T10.png\n-rw-rw-rw-  1 aii-agent aii-agent   22188 Oct 23 05:20 F3b_handle_axis_GRID.pdf\n-rw-rw-rw-  1 aii-agent aii-agent   48262 Oct 23 05:20 F3b_handle_axis_GRID.png\n-rw-rw-rw-  1 aii-agent aii-agent   24012 Oct 23 05:20 F3b_handle_axis_T10.pdf\n-rw-rw-rw-  1 aii-agent aii-agent   49623 Oct 23 05:20 F3b_handle_axis_T10.png\n-rw-rw-rw-  1 aii-agent aii-agent   15012 Oct 23 05:20 F4_generation.pdf\n-rw-rw-rw-  1 aii-agent aii-agent   97011 Oct 23 05:20 F4_generation.png\n-rw-rw-rw-  1 aii-agent aii-agent   17636 Oct 23 05:20 F5_mediation.pdf\n-rw-rw-rw-  1 aii-agent aii-agent   55589 Oct 23 05:20 F5_mediation.png\n==== inputs ====\ntotal 18331\ndrwxrwxrwx 10 aii-agent aii-agent 2014577 Oct 23 01:49 .\ndrwxrwxrwx 16 aii-agent aii-agent 2016627 Oct 23 08:56 ..\n-rw-rw-rw-  1 aii-agent aii-agent  528503 Oct 23 01:25 dep_extract.json\ndrwxrwxrwx  3 aii-agent aii-agent 2001180 Oct 23 01:11 exp11\ndrwxrwxrwx  2 aii-agent aii-agent 1012629 Oct 23 01:49 exp13\ndrwxrwxrwx  3 aii-agent aii-agent 1098362 Oct 23 01:12 exp22\ndrwxrwxrwx  3 aii-agent aii-agent 2005590 Oct 23 01:12 exp29\ndrwxrwxrwx  4 aii-agent aii-agent 2000198 Oct 23 01:12 exp30\ndrwxrwxrwx  3 aii-agent aii-agent 2000154 Oct 23 01:12 exp33\ndrwxrwxrwx  3 aii-agent aii-agent 2003509 Oct 23 01:12 exp34\ndrwxrwxrwx 12 aii-agent aii-agent 2003776 Oct 23 01:34 exp38\n-rw-rw-rw-  1 aii-agent aii-agent   82041 Oct 23 01:25 input_hashes.json\n==== logs ====\ntotal 3144\ndrwxrwxrwx  2 aii-agent aii-agent 1017243 Oct 23 05:14 .\ndrwxrwxrwx 16 aii-agent aii-agent 2016627 Oct 23 08:56 ..\n-rw-rw-rw-  1 aii-agent aii-agent    2939 Oct 23 05:14 analysis8.log\n-rw-rw-rw-  1 aii-agent aii-agent       0 Oct 23 05:14 commit0.log\n-rw-rw-rw-  1 aii-agent aii-agent     322 Oct 23 05:14 dl_gemma.log\n-rw-rw-rw-  1 aii-agent aii-agent    5359 Oct 23 05:14 dl_qwen.log\n-rw-rw-rw-  1 aii-agent aii-agent    1228 Oct 23 05:20 figures8.log\n-rw-rw-rw-  1 aii-agent aii-agent       0 Oct 23 05:14 gpu_queue.out\n-rw-rw-rw-  1 aii-agent aii-agent       0 Oct 23 05:14 gpu_queue2.out\n-rw-rw-rw-  1 aii-agent aii-agent       0 Oct 23 05:14 gpu_queue3.out\n-rw-rw-rw-  1 aii-agent aii-agent       0 Oct 23 05:14 gpu_queue4.out\n-rw-rw-rw-  1 aii-agent aii-agent       0 Oct 23 05:14 gpu_queue5.out\n-rw-rw-rw-  1 aii-agent aii-agent       0 Oct 23 05:14 gpu_queue6.out\n-rw-rw-rw-  1 aii-agent aii-agent    1344 Oct 23 05:14 label8_GRID.log\n-rw-rw-rw-  1 aii-agent aii-agent     642 Oct 23 05:14 label8_GRID.out\n-rw-rw-rw-  1 aii-agent aii-agent    6599 Oct 23 05:14 label8_T10.log\n-rw-rw-rw-  1 aii-agent aii-agent    2302 Oct 23 05:14 label8_T10.out\n-rw-rw-rw-  1 aii-agent aii-agent     826 Oct 23 05:14 label8_T10_final.out\n-rw-rw-rw-  1 aii-agent aii-agent     233 Oct 23 05:14 novelty8.log\n-rw-rw-rw-  1 aii-agent aii-agent     499 Oct 23 05:47 outputs8.log\n-rw-rw-rw-  1 aii-agent aii-agent     189 Oct 23 05:14 prompts8.log\n-rw-rw-rw-  1 aii-agent aii-agent     311 Oct 23 05:14 prompts8.out\n-rw-rw-rw-  1 aii-agent aii-agent    5527 Oct 23 05:14 run_band_T10.log\n-rw-rw-rw-  1 aii-agent aii-agent    4982 Oct 23 05:14 run_band_T10.out\n-rw-rw-rw-  1 aii-agent aii-agent   16277 Oct 23 05:14 run_dec_GRID.log\n-rw-rw-rw-  1 aii-agent aii-agent    9892 Oct 23 05:14 run_dec_GRID.out\n-rw-rw-rw-  1 aii-agent aii-agent    1780 Oct 23 05:14 run_dec_GRID2.out\n-rw-rw-rw-  1 aii-agent aii-agent    3504 Oct 23 05:14 run_dec_GRID3.out\n-rw-rw-rw-  1 aii-agent aii-agent   26435 Oct 23 05:14 run_dec_T10.log\n-rw-rw-rw-  1 aii-agent aii-agent   10650 Oct 23 05:14 run_dec_T10.out\n-rw-rw-rw-  1 aii-agent aii-agent    7409 Oct 23 05:14 run_dec_T10_L24.out\n-rw-rw-rw-  1 aii-agent aii-agent    2546 Oct 23 05:14 run_gen_GRID.log\n-rw-rw-rw-  1 aii-agent aii-agent    2394 Oct 23 05:14 run_gen_GRID_dec.out\n-rw-rw-rw-  1 aii-agent aii-agent    8538 Oct 23 05:14 run_gen_T10.log\n-rw-rw-rw-  1 aii-agent aii-agent    4062 Oct 23 05:14 run_gen_T10_band.out\n-rw-rw-rw-  1 aii-agent aii-agent    4060 Oct 23 05:14 run_gen_T10_dec.out\n-rw-rw-rw-  1 aii-agent aii-agent    9013 Oct 23 05:14 run_med_T10.log\n-rw-rw-rw-  1 aii-agent aii-agent    2138 Oct 23 05:14 run_med_T10.out\n-rw-rw-rw-  1 aii-agent aii-agent    6721 Oct 23 05:14 run_med_T10_rerun.out\n-rw-rw-rw-  1 aii-agent aii-agent    1241 Oct 23 05:14 run_post_T10.log\n-rw-rw-rw-  1 aii-agent aii-agent    1833 Oct 23 05:14 run_post_T10.out\n-rw-rw-rw-  1 aii-agent aii-agent    1947 Oct 23 05:14 run_rinit_GRID.log\n-rw-rw-rw-  1 aii-agent aii-agent    1928 Oct 23 05:14 run_rinit_GRID.out\n-rw-rw-rw-  1 aii-agent aii-agent    5097 Oct 23 05:14 run_rinit_T10.log\n-rw-rw-rw-  1 aii-agent aii-agent    1903 Oct 23 05:14 run_rinit_T10.out\n-rw-rw-rw-  1 aii-agent aii-agent    1903 Oct 23 05:14 run_rinit_T10_L24.out\n-rw-rw-rw-  1 aii-agent aii-agent    1444 Oct 23 05:14 run_rinit_T10_band.out\n-rw-rw-rw-  1 aii-agent aii-agent    5302 Oct 23 05:14 s0_inputs.log\n-rw-rw-rw-  1 aii-agent aii-agent    1574 Oct 23 05:14 s0_inputs.out\n-rw-rw-rw-  1 aii-agent aii-agent    1576 Oct 23 05:14 s0_inputs2.out\n-rw-rw-rw-  1 aii-agent aii-agent    2102 Oct 23 05:14 venv.log\n==== predictions ====\ntotal 2997\ndrwxrwxrwx  2 aii-agent aii-agent 1004419 Oct 23 04:53 .\ndrwxrwxrwx 16 aii-agent aii-agent 2016627 Oct 23 08:56 ..\n-rw-rw-rw-  1 aii-agent aii-agent    7319 Oct 23 01:46 commit0.json\n-rw-rw-rw-  1 aii-agent aii-agent    1057 Oct 23 02:46 commit1_GRID.json\n-rw-rw-rw-  1 aii-agent aii-agent    1104 Oct 23 01:51 commit1_T10.json\n-rw-rw-rw-  1 aii-agent aii-agent    4008 Oct 23 03:53 commit2_GRID_dec.json\n-rw-rw-rw-  1 aii-agent aii-agent    7234 Oct 23 03:34 commit2_T10_band.json\n-rw-rw-rw-  1 aii-agent aii-agent    7099 Oct 23 02:25 commit2_T10_dec.json\n-rw-rw-rw-  1 aii-agent aii-agent   10714 Oct 23 04:08 commit3_mediation.json\n-rw-rw-rw-  1 aii-agent aii-agent    6440 Oct 23 04:53 commit4_prospective.json\n-rw-rw-rw-  1 aii-agent aii-agent     281 Oct 23 03:26 hardware.json\n==== prompts ====\ntotal 5284\ndrwxrwxrwx  2 aii-agent aii-agent 2000132 Oct 23 01:34 .\ndrwxrwxrwx 16 aii-agent aii-agent 2016627 Oct 23 08:56 ..\n-rw-rw-rw-  1 aii-agent aii-agent  740345 Oct 23 01:34 grid_prompts.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent  653010 Oct 23 01:33 t10_prompts.jsonl\n==== tests ====\ntotal 2954\ndrwxrwxrwx  2 aii-agent aii-agent 1000693 Oct 23 02:38 .\ndrwxrwxrwx 16 aii-agent aii-agent 2016627 Oct 23 08:56 ..\n-rw-rw-rw-  1 aii-agent aii-agent    7103 Oct 23 02:38 test_cpu_tiny.py\n==== cache ====\ntotal 3109\ndrwxrwxrwx  2 aii-agent aii-agent 1014720 Oct 23 08:56 .\ndrwxrwxrwx 16 aii-agent aii-agent 2016627 Oct 23 08:56 ..\n-rw-rw-rw-  1 aii-agent aii-agent   63048 Oct 23 03:52 q_GRID_dec_trained.pt\n-rw-rw-rw-  1 aii-agent aii-agent   87691 Oct 23 04:31 q_T10_dec_trained.pt\n==== .aii ====\ntotal 2048\ndrwxrwxrwx  2 aii-agent aii-agent   78500 Oct 23 06:04 .\ndrwxrwxrwx 16 aii-agent aii-agent 2016627 Oct 23 08:56 ..\n-rw-rw-rw-  1 aii-agent aii-agent     634 Oct 23 05:59 manifest.yaml\n-rw-rw-rw-  1 aii-agent aii-agent     151 Oct 23 06:04 module_end.json\n3.0K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40/commitments.log\n3.0K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40/method.py\n3.0K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40/pyproject.toml\n11K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40/reproducibility.md\n28K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40/README.md\n215K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40/preview_method_out.json\n246K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40/mini_method_out.json\n984K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40/scripts\n985K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40/tests\n991K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40/audit\n1.1M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40/predictions\n1.2M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40/cache\n1.2M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40/logs\n1.3M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40/src\n1.6M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40/method_out.json\n1.8M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40/full_method_out.json\n1.8M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40/results\n3.1M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40/figures\n3.3M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40/prompts\n5.1M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40/das_maps\n12M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40/data\n239M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40/inputs", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [17] THINKING · 2026-10-26 13:39:11 UTC

```
No todo tool is available, so I'll track the six TODOs manually. Since `method.py` just orchestrates ~20 subprocess stage scripts, I'll check the README, reproducibility notes, and preview output structure to figure out what can run in 10 minutes on CPU.
```

### [18] TOOL CALL — Bash · 2026-10-26 13:39:11 UTC

```
Read the artifact README:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40; cat $A/README.md
```

### [19] TOOL RESULT — Bash · 2026-10-26 13:39:11 UTC

```
{"stdout": "# Checking for a hidden algorithm switch (iteration 8): one DAS protocol, seven controls, two model families\n\n**Question (claim K2).** When a code model picks an algorithm (BFS vs DFS vs union-find for connected components;\nBFS vs DFS for a grid path), is there a **low-rank causal variable** for that choice inside the model, a linear\nsubspace that *is* the algorithm decision? Or is there only a **steering handle**, a direction that changes the output\nwithout b... [truncated, 28853 chars total]
```

### [20] TOOL CALL — Bash · 2026-10-26 13:39:11 UTC

```
Read reproducibility notes, manifest, and check hardware:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40; cat $A/reproducibility.md; echo ====; cat $A/.aii/manifest.yaml; echo; nvidia-smi 2>&1 | head -15; nproc; free -h
```

### [21] TOOL RESULT — Bash · 2026-10-26 13:39:11 UTC

````
{"stdout": "# Reproducing \"Checking for a hidden algorithm switch\" (iteration 8, DAS with seven controls)\n\nThese are the steps that were ACTUALLY run, in order, including the reruns after crashes. Every path is relative to\nthis folder.\n\n## 1. Get the artifact\n\nThis folder is published as one directory of a public GitHub repository.\n\n```bash\ngit clone <repository-url>\ncd <repository>/<this-artifact-folder>     # the folder that holds README.md, method.py, src/, inputs/\n```\n\nThe folder already ships its frozen inputs (`inputs/`, sha256 in `inputs/input_hashes.json`), every prompt with its\ntoken ids (`prompts/`), all per-sample rows (`data/`), the fitted maps (`das_maps/`) and every result file\n(`results/`). Two kinds of material are not shipped: the activation caches (`cache/`, regenerable) and the\nPython environment (`.venv/`).\n\nNo user-uploaded files were used: the run's upload folder was empty.\n\n## 2. System, Python and libraries\n\nWhat the run used:\n\n| item | value |\n|---|---|\n| OS | Debian GNU/Linux 12 (bookworm) container; Ubuntu 22.04 or later works the same |\n| GPU | 1x NVIDIA L4, 23 GB VRAM (driver 595.91, CUDA runtime from the torch wheel: 12.8) |\n| CPU and RAM | 6 CPUs (cgroup quota), 57 GB RAM limit |\n| Python and uv | Python 3.12.14, uv 0.6.14 |\n| libraries | 85 packages pinned with `==` in `pyproject.toml` (identical to `uv pip freeze`) |\n\nKey library versions: torch 2.8.0 (PyPI CUDA 12.8 build), transformers 4.57.6, numpy 2.2.6, scipy 1.18.1,\nscikit-learn 1.9.1, matplotlib 3.11.2, loguru 0.7.3, openai 3.35.1.\n\n```bash\nsudo apt-get install -y python3.12 git      # or let uv fetch Python 3.12\ncurl -LsSf https://astral.sh/uv/install.sh | sh\nuv venv .venv --python=3.12\nuv pip install --python .venv/bin/python -r pyproject.toml\n```\n\n## 3. Models, data and environment variables\n\n- **Models** (Hugging Face, pinned revisions), downloaded into the Hugging Face cache:\n\n  ```bash\n  hf download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218\n  hf download google/gemma-3-4b-it --revision 093f9f388b31de276ce2de164bdc2081324b9767\n  ```\n\n- **Environment variables** (names only):\n  - `HF_HOME` and `HF_HUB_CACHE`: where the models live. `src/cfg8.py:model_path` reads `HF_HUB_CACHE`.\n  - `HF_TOKEN`: the Gemma licence must be accepted on the Hub.\n  - `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY`: used only by the novelty audit (`src/novelty8.py`). No call was\n    made in this run (0 candidates, USD 0.00).\n  - `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`: set by the GPU queue scripts.\n  - Optional for S0 only: `AII_ARTIFACTS_DIR` (a folder holding the source artifacts as sibling folders named by id)\n    and `ART_J3RM_DIR` (the dataset dependency).\n- **Inputs from other artifacts.** `src/s0_inputs.py` copied them into `inputs/`, and they ship with this folder, so\n  S0 never has to be re-run. To rebuild `inputs/`, point `AII_ARTIFACTS_DIR` at the published repository root, or\n  keep the artifacts as sibling folders. The source artifacts, by id:\n  - art_veI9l_Rb9wDY (iteration-7 T10 DAS prompts and code);\n  - art_pHL7LWNhpcCS (T10 forks, remeasure);\n  - art_HY7uYZz-OjRW (Gemma code, iteration-6 Gemma inputs, iteration-7 subspaces);\n  - art_lpQalcAXMGr1 (push outcomes, known solutions, exp22 units and directions);\n  - art_rMlbrjVB1c__ (exp30 engine and prompts);\n  - art_j3Rm_lr2nzR6, the declared dataset dependency, read through `ART_J3RM_DIR` or `../art_j3Rm_lr2nzR6`.\n\n  One file was added by hand after S0: `inputs/exp13/norms_T10.npz` (the absolute unit n[l,p]), copied from\n  art_veI9l_Rb9wDY's `inputs/exp13/results/tensors/norms_T10.npz`.\n\n## 4. Commands in the order they were run (wall clock 00:44-05:30 UTC, 2026-10-23)\n\nAll GPU stages load one model at a time; each skips work whose result file exists.\n\n### CPU stages\n\n| step | command | runtime |\n|---|---|---|\n| S0 inputs | `.venv/bin/python src/s0_inputs.py` (first pass, then rerun with the corrected noun-flag field) | ~1 min |\n| S1 prompts | `.venv/bin/python src/prompts8.py` | ~3 min |\n| COMMIT #0 | `.venv/bin/python src/commit0.py` | seconds |\n\nS1 produces 290 T10 prompts and 207 GRID prompts. COMMIT #0 runs before any GPU use.\n\n### GPU stages\n\n1. `.venv/bin/python src/run_dec.py --unit T10` (~23 min).\n   - What it runs: S3 token maps and adherence; COMMIT #1; caches; U-tests; scan of blocks 0, 2, ..., 34; fits at\n     L* = 22; controls c1, c2, c4-c7.\n   - The first attempt was stopped at block 2 of the scan to fix a NaN-ordering bug in the L* argmax, then\n     restarted.\n2. `.venv/bin/python src/run_gen.py --unit T10 --sites dec --minutes 30 --B 16` (~8 min, 419 programs). COMMIT #2\n   runs first, and `src/label8.py` labels in the background.\n3. `.venv/bin/python src/run_rinit.py --unit T10` (~4 min): c3 on a random-init Qwen3-8B.\n4. `.venv/bin/python src/run_dec.py --unit GRID`: crashed in the 2-class label control (no pair survives a\n   2-class derangement).\n5. `.venv/bin/python src/run_band.py --minutes 35` (~30 min): T10 band, 109 steps per fit.\n6. `.venv/bin/python src/run_gen.py --unit T10 --sites band --minutes 18 --B 16` (~9 min).\n7. `.venv/bin/python src/run_dec.py --unit GRID`, rerun with the F3 balanced-shuffle control (~12 min). It reuses\n   `results/scan_GRID.json` and the seed maps fitted before the crash.\n8. `.venv/bin/python src/run_gen.py --unit GRID --sites dec --minutes 16 --B 16` (~4 min, 220 programs).\n9. `.venv/bin/python src/run_rinit.py --unit GRID` (~3 min).\n10. `.venv/bin/python src/run_rinit.py --unit T10 --band --band_minutes 8` (~4 min).\n11. `.venv/bin/python src/run_med.py --minutes 28`: computed the predictor, COMMIT #3 and the Spearman tests, then ran\n    out of GPU memory in the clamp rows. The rerun `.venv/bin/python src/run_med.py --minutes 24` (~24 min) ran\n    COMMIT #4, the clamp (270 slots) and the prospective set (208 programs).\n12. `.venv/bin/python src/run_post.py --unit T10` (~3 min): per-pair label-control test (p_c2) from the saved maps.\n13. `.venv/bin/python src/run_dec.py --unit T10 --force_L 24` (~20 min): post-hoc block-24 sensitivity.\n14. `.venv/bin/python src/run_rinit.py --unit T10 --force_L 24` (~3 min).\n15. `.venv/bin/python src/label8.py --unit T10`: labels the mediation rows.\n\n`scripts/gpu_queue*.sh` hold the exact queues used. Total GPU time was about 3.2 h on the L4.\n\n### Analysis and outputs (CPU)\n\n```bash\n.venv/bin/python src/analysis8.py      # verdicts, K2, mediation outcomes -> results/analysis.json\n.venv/bin/python src/novelty8.py       # novelty audit (0 candidates -> no API call)\n.venv/bin/python src/figures8.py       # figures/F1-F5 (PDF + PNG)\n.venv/bin/python src/digest8.py        # results/summary.md (tables straight from the JSONs)\n.venv/bin/python src/outputs8.py       # method_out.json\n# full_/mini_/preview_method_out.json come from the aii-json skill's format script:\n#   aii_json_format_mini_preview.py --input method_out.json --format exp_gen_sol_out\npython3 audit/rederive.py              # stdlib-only re-derivation + placebos -> results/rederive.json\n.venv/bin/python tests/test_cpu_tiny.py   # CPU equivalence tests (results/unit_tests_cpu.json)\n```\n\n`.venv/bin/python method.py` runs the same stage order end to end. `.venv/bin/python method.py --cpu-only` re-runs\nonly the analysis and output stages from the saved rows.\n\n### Seeds and configuration (all in `src/cfg8.py` and `predictions/commit0.json`)\n\n- **Fits:** fit seeds 0, 1, 2 (init `torch.Generator().manual_seed(1000 + seed)`); Adam, lr 2e-2, 240 steps\n  (scan 100; band 109).\n- **Early stopping:** inner-validation KL every 20 steps, patience 3.\n- **Controls:** random subspaces use Haar seeds 7000-7049; label controls use fit seeds 10-12.\n- **Random-init networks:** `torch.manual_seed(0)`, then HF `post_init`.\n- **Splits and sampling:** noun split seed 8001; pair sampling seed 8002; bootstrap 2,000 resamples (seed 0 per\n  call).\n- **Generation:** CRN stream `PCG64(sha256(unit|site|iter8|slot))`; temperature 1.0, top-p 1, no top-k;\n  max_new_tokens 512 (T10) and 1,024 (GRID); fence stop.\n- **Mediation:** iteration-4 directions `rand_9101`-`rand_9140`, alpha 2; prospective directions 98001-98024 from\n  `PCG64(seed)` normalised Gaussians.\n\n## 5. What a reader should get\n\n### Files\n\n| file | contents |\n|---|---|\n| `results/analysis.json` | verdicts per (unit, site), K2 status and p_K2, mediation outcomes |\n| `results/summary.md` | all tables (auto-generated) |\n| `results/dec_T10.json` | T10 decision site (L* = 22, k* = 4) |\n| `results/band_T10.json` | T10 task band (k* = 2) |\n| `results/dec_GRID.json` | GRID decision site (L* = 16, k* = 4) |\n| `results/rinit_*.json` | random-init control c3 |\n| `results/mediation_T10.json` | mediation |\n| `results/dec_T10_L24.json` | post-hoc block-24 sensitivity |\n\n### Headline numbers\n\nAll of these are re-derived by `audit/rederive.py` from the raw rows (`results/rederive.json`: 38 checks, all\nmatch), except c3, which is recomputed only from the stored per-site means.\n\n- **Teacher-forced held-out recovery at k*:** T10 decision 8.43 (OFF-MANIFOLD), T10 band 0.82, GRID decision 3.07,\n  T10 block 24 (post hoc) 1.22.\n- **c2 label-control ratios** (limit 0.10):\n  - T10: 0.87, 0.63, 0.77;\n  - GRID: 0.11, 0.11, 0.20;\n  - T10 block 24: 0.61, 0.57, 0.50.\n- **c3 random-init ratios** (limit 0.25): T10 0.69, GRID 0.41, band 0.18, T10 block 24 0.54.\n- **Generation**, correct target programs out of 30 (DAS / FULL / RAND / BASE):\n  - T10 decision, DFS: 29 / 2 / 0 / 0;\n  - T10 decision, BFS: 5 / 0 / 0 / 0, with 29 attempting BFS;\n  - T10 band, BFS: 28 / 23 / 0 / 0;\n  - T10 band, DFS: 3 / 20 / 0 / 0;\n  - GRID decision, BFS: 22 / 10 / 5 / 6.\n- **Verdicts:**\n  - T10 decision: NO HANDLE (pooled pass ratio 0.72);\n  - T10 band: SUFFICIENT HANDLE (fails c2, c5, c7);\n  - GRID decision: SUFFICIENT HANDLE (fails c2, c3, c5, c6).\n  - K2: DISCONFIRMED, p_K2 = 0.037.\n- **Mediation:**\n  - retrospective Spearman 0.39 (bar 0.5); prospective 0.09;\n  - clamp removal: band subspace -0.01, random 0.02, decision site -0.05 among reached slots.\n- **Novelty:** 0 'other' programs among 1,857 correct programs.\n\n### Paper mapping\n\n- The Results tables, verdict table and figures in `README.md` and `results/summary.md` are what the run's report\n  and paper cite.\n- Geometry figures: `figures/F3_geometry_T10` and `F3_geometry_GRID`.\n- Scan: `figures/F1_scan_profile`.\n- Recovery by rank: `F2_recovery_by_rank`.\n- Generation: `F4_generation`.\n- Mediation: `F5_mediation`.\n\n### Reproduction tolerance\n\nTeacher-forced numbers are deterministic up to bf16 kernel differences: the KV path differs from full recompute by\nat most 0.25 nats, and every Delta is measured within one path. Generation runs bf16 on a CRN stream, so a different\nGPU model or batch shape can change individual slots. Expect counts within a few slots per cell; verdicts can flip\nonly where a criterion sits near its threshold (for example GRID's pass ratio 0.81 against 0.80).\n====\nentries:\n  - path: .venv/\n    delete: regenerable\n    source: \"uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml\"\n  - path: cache/\n    delete: regenerable\n    source: \".venv/bin/python src/run_dec.py --unit T10 && .venv/bin/python src/run_dec.py --unit GRID && .venv/bin/python src/run_band.py\"\n  - path: inputs/\n    keep: frozen sha256-hashed copies of earlier iterations' prompts, bench, labellers, maps and push directions that the code reads; several upstream iterations are already purged\n  - path: src/__pycache__/\n    delete: regenerable\n    source: \".venv/bin/python -m compileall src\"\n\n/bin/bash: line 1: nvidia-smi: command not found\n4\n               total        used        free      shared  buff/cache   available\nMem:           755Gi        41Gi       178Gi        15Mi       540Gi       713Gi\nSwap:             0B          0B          0B", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
````

### [22] TOOL CALL — Bash · 2026-10-26 13:39:11 UTC

```
Summarize preview output JSON structure:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40; python3 - <<'EOF'
import json
A="/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40"
d=json.load(open(A+"/preview_method_out.json"))
print(type(d), list(d.keys()) if isinstance(d,dict) else len(d))
def show(x, ind=0, maxitems=4):
    p=" "*ind
    if isinstance(x, dict):
        for k,v in list(x.items())[:40]:
            if isinstance(v,(dict,list)):
                print(f"{p}{k}: {type(v).__name__}({len(v)})")
                show(v, ind+2)
            else:
                s=repr(v)
                print(f"{p}{k}: {s[:200]}")
    elif isinstance(x, list):
        for i,v in enumerate(x[:2]):
            print(f"{p}[{i}] {type(v).__name__}")
            show(v, ind+2)
show(d)
EOF
```

### [23] TOOL RESULT — Bash · 2026-10-26 13:39:11 UTC

```
{"stdout": "<class 'dict'> ['metadata', 'datasets']\nmetadata: dict(32)\n  method_name: 'DAS8: one DAS protocol (linear orthonormal map, bounded KL objective, class-margin readout) at the decision token and task band, with seven committed controls'\n  description: 'Checks whether a low-rank causal variable for the chosen algorithm exists in Qwen3-8B (T10 connected components) and gemma-3-4b-it (T1 grid path), against full-state, random-subspace, label-control, \n  verdicts: di... [truncated, 31333 chars total]
```

### [24] THINKING · 2026-10-26 13:39:19 UTC

```
No GPU is available on this machine, so the Qwen3-8B and Gemma stages can't run in a 10-minute CPU notebook. I'll move on to mapping the 8 datasets in the output file to see what each example contains.
```

### [25] TOOL CALL — Bash · 2026-10-26 13:39:19 UTC

```
Print metadata and per-dataset example fields from preview:
python3 - <<'EOF'
import json
A="/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40"
d=json.load(open(A+"/preview_method_out.json"))
md=d["metadata"]
print("METADATA KEYS:", list(md.keys()))
for k,v in md.items():
    s=json.dumps(v)
    print(f"--- {k}: ({len(s)} chars) {s[:600]}")
print()
for ds in d["datasets"]:
    print("=== DATASET", ds.get("dataset"), "n_examples(preview)=", len(ds.get("examples",[])), "keys:", list(ds.keys()))
    ex=ds["examples"][0]
    for k,v in ex.items():
        s=json.dumps(v)
        print(f"   {k}: {s[:400]}")
EOF
```

### [26] TOOL RESULT — Bash · 2026-10-26 13:39:19 UTC

```
{"stdout": "METADATA KEYS: ['method_name', 'description', 'verdicts', 'K2', 'mediation', 'commit_chain', 'deviations', 'dec_T10', 'band_T10', 'dec_GRID', 'dec_T10_L24', 'rinit_T10', 'rinit_GRID', 'rinit_T10_band', 'rinit_T10_L24', 's3_T10', 's3_GRID', 'geometry', 'novelty_audit', 'costs', 'post_T10', 'unit_tests_cpu', 'unit_tests_gpu_T10', 'unit_tests_gpu_GRID', 'mediation_T10', 'positioning', 'rederive', 'scan_T10', 'scan_GRID', 'gen_T10_dec', 'gen_T10_band', 'gen_GRID_dec']\n--- method_name: (160 chars) \"DAS8: one DAS protocol (linear orthonormal map, bounded KL objective, class-margin readout) at the decision token and task band, with seven committed controls\"\n--- description: (205 chars) \"Checks whether a low-rank causal variable for the chosen algorithm exists in Qwen3-8B (T10 connected components) and gemma-3-4b-it (T1 grid path), against full-state, random-subspace, label-control, r...\"\n--- verdicts: (4774 chars) {\"T10-dec\": {\"verdict\": \"NO HANDLE\", \"V0_by_class\": {\"bfs\": {\"gen_recovery\": null, \"pass_ratio\": 0.24, \"mcnemar_p_das_gt_rand\": 0.03125, \"V0_class\": false, \"full_minus_base_correct\": 0}, \"dfs\": {\"gen_recovery\": 14.5, \"pass_ratio\": 1.2, \"mcnemar_p_das_gt_rand\": 1.862645149230957e-09, \"V0_class\": true, \"full_minus_base_correct\": 2}}, \"note_generation_recovery\": \"generation recovery divides by FULL - BASE correct counts; when the full-state exchange moves <= 2 slots the ratio is not a fraction of a ceiling\", \"V0\": false, \"V0_parts\": {\"tf_recovery\": true, \"gen_recovery\": true, \"pass_ratio\": false,\n--- K2: (488 chars) {\"confirmed\": false, \"disconfirmed\": true, \"status\": \"DISCONFIRMED\", \"p_by_site\": {\"T10\": {\"p_c2_max\": 0.03698150924537731, \"p_c3\": 0.0004997501249375312, \"max\": 0.03698150924537731}, \"GRID\": {\"p_c2_max\": 0.0004997501249375312, \"p_c3\": 0.0004997501249375312, \"max\": 0.0004997501249375312}}, \"p_K2\": 0.03698150924537731, \"rule\": \"confirmed iff T10-dec and GRID-dec both CERTIFIED; disconfirmed iff a decision site fails c2 or c3 in either family; p_K2 = max over sites of max(p_c2, p_c3)\"}\n--- mediation: (1724 chars) {\"escapes_PUSH\": 221, \"n_PUSH\": 276, \"clamp_TASK\": {\"n_pairs\": 270, \"escapes_push\": 218, \"escapes_clamp\": 221, \"removal\": -0.013761467889908285, \"mcnemar_push_vs_clamp\": {\"a_only\": 8, \"b_only\": 11, \"p_two_sided\": 0.6476058959960938, \"p_one_sided_a_gt_b\": 0.8203582763671875}, \"pass_rate_clamp\": 0.8703703703703703}, \"clamp_RAND\": {\"n_pairs\": 270, \"escapes_push\": 218, \"escapes_clamp\": 213, \"removal\": 0.022935779816513735, \"mcnemar_push_vs_clamp\": {\"a_only\": 8, \"b_only\": 3, \"p_two_sided\": 0.2265625, \"p_one_sided_a_gt_b\": 0.11328125}, \"pass_rate_clamp\": 0.8222222222222222}, \"clamp_DEC\": {\"n_reached\n--- commit_chain: (122 chars) {\"n_commits\": 8, \"breaks\": [], \"changed_payloads\": [], \"ok\": true, \"names\": [\"commit0\", \"commit1_T10\", \"commit2_T10_dec\"]}\n--- deviations: (528 chars) [{\"key\": \"GRID_two_class\", \"text\": \"GRID has 2 adherent classes ['bfs', 'dfs']; c2 cyclic derangements replaced by the prompt-level balanced shuffle (F2/F3)\", \"utc\": \"2026-10-23T02:44:29.116539Z\"}, {\"key\": \"band_steps\", \"text\": \"band fits run 109 steps (timing 2.22 s/step; same budget for every band fit, controls included)\", \"utc\": \"2026-10-23T03:01:10.434259Z\"}, {\"key\": \"hardware_json_late\", \"text\": \"predictions/hardware.json was written after the T10 decision-site generation began\", \"utc\": \"2026-10-23T03:26:42.011886Z\"}]\n--- dec_T10: (18826 chars) {\"unit\": \"T10\", \"family\": \"qwen\", \"classes\": [\"bfs\", \"dfs\", \"union_find\"], \"L_star\": 22, \"readout_proximal\": false, \"k_star\": 4, \"scan\": {\"0\": {\"cv_recovery_by_fold\": [], \"cv_median_recovery\": null, \"full_state_mean_delta_held96\": -0.024740934371948242, \"full_state_flip_share_held96\": 0.3020833333333333, \"note\": \"full-state exchange moves < 10% of pairs by >= 1 nat: recovery undefined, not fitted\"}, \"2\": {\"cv_recovery_by_fold\": [], \"cv_median_recovery\": null, \"full_state_mean_delta_held96\": -0.011723001797993978, \"full_state_flip_share_held96\": 0.34375, \"note\": \"full-state exchange moves < 10%\n--- band_T10: (9583 chars) {\"unit\": \"T10\", \"band\": [12, 13, 14], \"n_train_pairs\": 2000, \"n_held_subsample\": 96, \"U4\": {\"zero_rank_vs_full_recompute_max_abs_logP_class\": 0.12498855590820312, \"full_state_flip_to_source_class_share_held96\": 0.5833333333333334, \"pass_flip_0.9\": false, \"mean_delta_full\": 18.18716738621394}, \"timing\": {\"sec_per_step\": 2.2164738972981772, \"sec_eval16\": 0.7966029644012451, \"steps\": 109}, \"k_star\": 2, \"recovery_by_rank\": {\"1\": {\"n\": 96, \"n_src\": 24, \"n_base\": 37, \"recovery\": 0.7627281447121865, \"ci95\": [0.43939670520970103, 1.0858484747106356], \"mean_delta_edit\": 13.871864438056946, \"mean_delta_\n--- dec_GRID: (15348 chars) {\"unit\": \"GRID\", \"family\": \"gemma\", \"classes\": [\"bfs\", \"dfs\"], \"L_star\": 16, \"readout_proximal\": false, \"k_star\": 4, \"scan\": {\"0\": {\"cv_recovery_by_fold\": [], \"cv_median_recovery\": null, \"full_state_mean_delta_held96\": 0.06301768620808919, \"full_state_flip_share_held96\": 0.6770833333333334, \"note\": \"full-state exchange moves < 10% of pairs by >= 1 nat: recovery undefined, not fitted\"}, \"2\": {\"cv_recovery_by_fold\": [], \"cv_median_recovery\": null, \"full_state_mean_delta_held96\": 0.01619398593902588, \"full_state_flip_share_held96\": 0.4791666666666667, \"note\": \"full-state exchange moves < 10% of p\n--- dec_T10_L24: (18968 chars) {\"unit\": \"T10\", \"family\": \"qwen\", \"classes\": [\"bfs\", \"dfs\", \"union_find\"], \"L_star\": 24, \"readout_proximal\": false, \"k_star\": 2, \"scan\": {\"0\": {\"cv_recovery_by_fold\": [], \"cv_median_recovery\": null, \"full_state_mean_delta_held96\": -0.024740934371948242, \"full_state_flip_share_held96\": 0.3020833333333333, \"note\": \"full-state exchange moves < 10% of pairs by >= 1 nat: recovery undefined, not fitted\"}, \"2\": {\"cv_recovery_by_fold\": [], \"cv_median_recovery\": null, \"full_state_mean_delta_held96\": -0.011723001797993978, \"full_state_flip_share_held96\": 0.34375, \"note\": \"full-state exchange moves < 10%\n--- rinit_T10: (890 chars) {\"unit\": \"T10\", \"U8_entropy_nats\": [11.120536804199219, 11.105794906616211], \"U8_pass_gt_8\": true, \"site\": \"dec\", \"L\": 22, \"k_star\": 4, \"by_rank\": {\"1\": {\"mean_delta_rinit\": 10.02843123515447, \"kl_mean\": 1.6003944479417986}, \"2\": {\"mean_delta_rinit\": 10.779726208051045, \"kl_mean\": 2.1933216758243117}, \"4\": {\"mean_delta_rinit\": 12.081434981822968, \"kl_mean\": 3.099046284602955}, \"8\": {\"mean_delta_rinit\": 12.986624685923259, \"kl_mean\": 3.673934429092333}}, \"mean_delta_trained\": 17.53134325027466, \"mean_delta_rinit\": 12.081434981822968, \"ratio\": 0.6891334457006705, \"pass\": false, \"test_trained_gt_\n--- rinit_GRID: (900 chars) {\"unit\": \"GRID\", \"U8_entropy_nats\": [11.95640754699707, 11.960336685180664], \"U8_pass_gt_8\": true, \"site\": \"dec\", \"L\": 16, \"k_star\": 4, \"by_rank\": {\"1\": {\"mean_delta_rinit\": 3.8907977683203563, \"kl_mean\": 0.016420044355183756}, \"2\": {\"mean_delta_rinit\": 4.041903712919781, \"kl_mean\": 0.020271284562050646}, \"4\": {\"mean_delta_rinit\": 3.6983136406966617, \"kl_mean\": 0.017833712601626774}, \"8\": {\"mean_delta_rinit\": 3.6864161576543535, \"kl_mean\": 0.018323092721339713}}, \"mean_delta_trained\": 9.104610885892596, \"mean_delta_rinit\": 3.6983136406966617, \"ratio\": 0.40620227344664683, \"pass\": false, \"test_\n--- rinit_T10_band: (532 chars) {\"unit\": \"T10\", \"U8_entropy_nats\": [11.120536804199219, 11.105794906616211], \"U8_pass_gt_8\": true, \"site\": \"band\", \"k_star\": 2, \"mean_delta_trained\": 14.894549230734507, \"mean_delta_rinit\": 2.70632396141688, \"ratio\": 0.18169895036718886, \"pass\": true, \"test_trained_gt_rinit\": {\"mean_diff\": 12.188225269317627, \"p_cluster_boot\": 0.0004997501249375312, \"p_wilcoxon_pairs\": 1.2357891798915206e-16}, \"fit\": {\"best_step\": 109, \"best_val_kl\": 7.565387111123782, \"steps_run\": 109, \"seconds\": 146.3}, \"steps_budget\": 109, \"seconds\": 174.8}\n--- rinit_T10_L24: (892 chars) {\"unit\": \"T10\", \"U8_entropy_nats\": [11.120536804199219, 11.105794906616211], \"U8_pass_gt_8\": true, \"site\": \"dec\", \"L\": 24, \"k_star\": 2, \"by_rank\": {\"1\": {\"mean_delta_rinit\": 10.133584160804748, \"kl_mean\": 1.6785189999469246}, \"2\": {\"mean_delta_rinit\": 10.656524064540863, \"kl_mean\": 2.030973614733666}, \"4\": {\"mean_delta_rinit\": 11.511067503293356, \"kl_mean\": 2.7626707158020385}, \"8\": {\"mean_delta_rinit\": 12.419171723524729, \"kl_mean\": 3.32468905961141}}, \"mean_delta_trained\": 19.816160151163736, \"mean_delta_rinit\": 10.656524064540863, \"ratio\": 0.5377693752598705, \"pass\": false, \"test_trained_gt\n--- s3_T10: (733 chars) {\"unit\": \"T10\", \"unmapped_candidates\": {\"1936\": {\"token\": \" build\", \"max_mass\": 0.02277, \"labels\": {\"dfs\": 10}, \"class\": \"dfs\"}}, \"token_map\": {\"66564\": \"bfs\", \"25792\": \"dfs\", \"1477\": \"union_find\", \"11300\": \"union_find\", \"1936\": \"dfs\"}, \"class_sets\": {\"bfs\": [66564], \"dfs\": [25792, 1936], \"union_find\": [1477, 11300]}, \"adherence\": {\"bfs\": {\"mean_own_class_mass_at_d\": 0.9940987557172776, \"n_forced\": 20, \"kept\": true}, \"dfs\": {\"mean_own_class_mass_at_d\": 0.9999776870012284, \"n_forced\": 20, \"kept\": true}, \"union_find\": {\"mean_own_class_mass_at_d\": 0.9999999433755875, \"n_forced\": 20, \"free_labels\"\n--- s3_GRID: (998 chars) {\"unit\": \"GRID\", \"unmapped_candidates\": {\"9607\": {\"token\": \"stack\", \"max_mass\": 0.55812, \"labels\": {\"dfs\": 9, \"disputed\": 1}, \"class\": \"dfs\"}, \"5265\": {\"token\": \"open\", \"max_mass\": 0.05927, \"labels\": {\"bfs\": 9, \"disputed\": 1}, \"class\": \"bfs\"}}, \"token_map\": {\"107\": \"bfs\", \"584\": \"bfs\", \"15204\": \"bfs\", \"236809\": \"bfs\", \"53227\": \"dfs\", \"9607\": \"dfs\", \"5265\": \"bfs\"}, \"class_sets\": {\"bfs\": [107, 584, 15204], \"dfs\": [53227, 9607]}, \"adherence\": {\"bfs\": {\"mean_own_class_mass_at_d\": 0.9995309084653854, \"n_forced\": 20, \"kept\": true}, \"dfs\": {\"mean_own_class_mass_at_d\": 0.9968029648065567, \"n_forced\": \n--- geometry: (3531 chars) {\"T10\": {\"unit\": \"T10\", \"L\": 22, \"mds_stress1\": 0.014684073126979015, \"isomap_mean_geodesic_between_groups\": {\"ban|bfs\": 17.371543884277344, \"ban|dfs\": 10.006659507751465, \"ban|instr\": 4.124963760375977, \"ban|p0\": 3.7493724822998047, \"ban|padtwin\": 3.4246509075164795, \"ban|seed\": 3.1308951377868652, \"ban|twin\": 3.7580552101135254, \"ban|union_find\": 5.419531345367432, \"bfs|dfs\": 9.39411735534668, \"bfs|instr\": 18.728302001953125, \"bfs|p0\": 18.272287368774414, \"bfs|padtwin\": 17.9774227142334, \"bfs|seed\": 16.09488296508789, \"bfs|twin\": 18.185338973999023, \"bfs|union_find\": 13.294388771057129, \"dfs\n--- novelty_audit: (384 chars) {\"judges\": [\"deepseek/deepseek-chat-v3.1\", \"mistralai/mistral-medium-3.1\"], \"cap_usd\": 0.3, \"units\": {\"T10\": {\"n_correct_programs\": 1708, \"n_candidates\": 0, \"rule_of_three_upper_bound_novel_rate\": 0.001756440281030445, \"judged\": []}, \"GRID\": {\"n_correct_programs\": 149, \"n_candidates\": 0, \"rule_of_three_upper_bound_novel_rate\": 0.020134228187919462, \"judged\": []}}, \"spent_usd\": 0.0}\n--- costs: (39 chars) {\"openrouter_usd\": 0.0, \"cap_usd\": 0.3}\n--- post_T10: (636 chars) {\"unit\": \"T10\", \"L\": 22, \"k_star\": 4, \"mean_delta_true\": 17.509216632843017, \"perm\": {\"pi1\": {\"mean_delta\": 15.108920202255248, \"test_true_gt_perm\": {\"mean_diff\": 2.4002964305877685, \"p_cluster_boot\": 0.03698150924537731, \"p_wilcoxon_pairs\": 1.600719096339626e-28}}, \"pi2\": {\"mean_delta\": 11.177985747655233, \"test_true_gt_perm\": {\"mean_diff\": 6.331230885187785, \"p_cluster_boot\": 0.0004997501249375312, \"p_wilcoxon_pairs\": 3.0924420849936363e-100}}, \"prompt\": {\"mean_delta\": 13.362031698226929, \"test_true_gt_perm\": {\"mean_diff\": 4.147184934616089, \"p_cluster_boot\": 0.0004997501249375312, \"p_wilcox\n--- unit_tests_cpu: (801 chars) {\"note\": \"tests/test_cpu_tiny.py on tiny random Qwen3 / Gemma3 models (bf16, CPU): max |log P(class)| difference between the DAS machinery and full recomputation with hooks\", \"qwen\": {\"dec_zero_edit\": 0.0019, \"dec_full_edit\": 0.00094, \"dec_proj_edit\": 0.0019, \"dec_mixed_lengths\": 0.0019, \"band_zero_edit\": 0.00093, \"band_full_exchange\": 0.001, \"band_proj_edit\": 0.0012, \"fit_orth_err\": 2.4e-07, \"band_fit_orth_err\": 3.6e-07}, \"gemma\": {\"dec_zero_edit\": 0.0019, \"dec_full_edit\": 0.0011, \"dec_proj_edit\": 0.0016, \"dec_mixed_lengths\": 0.0019, \"band_zero_edit\": 0.0021, \"band_full_exchange\": 0.0012, \"ba\n--- unit_tests_gpu_T10: (318 chars) {\"U1_max_abs_logit_diff\": 0.0, \"U2_max_abs_logP_class_diff_kv_vs_full\": 0.25, \"U3_max_abs_logP_class_diff_fullstate_edit\": 0.24909591674804688, \"U2_pass_0.3\": true, \"U9\": {\"kl_random_init_map\": 11.297689338525137, \"kl_after_20_steps\": 10.703729808330536, \"reduction\": 0.052573540694662024}, \"U7_memory_peak_GB\": 16.28}\n--- unit_tests_gpu_GRID: (325 chars) {\"U1_max_abs_logit_diff\": 0.0, \"U2_max_abs_logP_class_diff_kv_vs_full\": 0.0999298095703125, \"U3_max_abs_logP_class_diff_fullstate_edit\": 0.1226806640625, \"U2_pass_0.3\": true, \"U9\": {\"kl_random_init_map\": 1.1766524252792199, \"kl_after_20_steps\": 0.24771971286584935, \"reduction\": 0.789470783772816}, \"U7_memory_peak_GB\": 9.48}\n--- mediation_T10: (21003 chars) {\"unit\": \"T10\", \"alpha\": 2.0, \"k_star_band\": 2, \"L_star\": 22, \"k_star_dec\": 4, \"dbar_crosscheck_keys\": [\"POP_d9101_a2.0__W1\", \"POP_d9102_a2.0__W1\", \"POP_d9103_a2.0__W1\"], \"spearman_escape_pooled\": {\"rho\": 0.39147708195720493, \"p_one_sided\": 0.006099390060993901, \"n\": 40}, \"spearman_escape_d\": {\"rho\": 0.36136948694511073, \"p_one_sided\": 0.0110988901109889, \"n\": 40}, \"spearman_escape_c\": {\"rho\": 0.3868820567844952, \"p_one_sided\": 0.007099290070992901, \"n\": 40}, \"partial_spearman_ctrl_normD_band\": 0.41787320850946064, \"partial_spearman_ctrl_normD_block35\": 0.39288328968788966, \"spearman_pi_bfs\": \n--- positioning: (1810 chars) {\"date\": \"2026-10-23\", \"tool\": \"WebSearch (standard mode); quotes are verbatim fragments returned in the search-result summaries of the listed sources\", \"queries\": [{\"query\": \"distributed alignment search interchange intervention Geiger Finding alignments between interpretable causal variables and distributed neural representations\", \"source\": \"https://arxiv.org/abs/2303.02536 (Geiger, Wu, Potts, Icard, Goodman; CLeaR 2024, PMLR 236)\", \"quote\": \"DAS found perfect alignments for binary high-level variables tied to simple equality and lexical entailment\", \"verdict\": \"Map class and interchange ar\n--- rederive: (5036 chars) {\"tf\": {\"T10_dec\": {\"rederived\": 8.432892175097768, \"reported\": 8.432892175097768, \"n\": 552, \"match\": true}, \"T10_band\": {\"rederived\": 0.818959264762952, \"reported\": 0.818959264762952, \"n\": 96, \"match\": true}, \"GRID_dec\": {\"rederived\": 3.0687714031813402, \"reported\": 3.0687714031813402, \"n\": 108, \"match\": true}, \"T10_dec_L24\": {\"rederived\": 1.2202767836853499, \"reported\": 1.2202767836853499, \"n\": 600, \"match\": true}}, \"gen\": {\"T10\": {\"dec\": {\"bfs|BASE\": {\"rederived\": 0, \"n\": 30, \"reported\": 0, \"match\": true}, \"bfs|FULL\": {\"rederived\": 0, \"n\": 30, \"reported\": 0, \"match\": true}, \"bfs|DAS\": {\"red\n--- scan_T10: (4120 chars) {\"0\": {\"cv_recovery_by_fold\": [], \"cv_median_recovery\": null, \"full_state_mean_delta_held96\": -0.024740934371948242, \"full_state_flip_share_held96\": 0.3020833333333333, \"note\": \"full-state exchange moves < 10% of pairs by >= 1 nat: recovery undefined, not fitted\"}, \"2\": {\"cv_recovery_by_fold\": [], \"cv_median_recovery\": null, \"full_state_mean_delta_held96\": -0.011723001797993978, \"full_state_flip_share_held96\": 0.34375, \"note\": \"full-state exchange moves < 10% of pairs by >= 1 nat: recovery undefined, not fitted\"}, \"4\": {\"cv_recovery_by_fold\": [], \"cv_median_recovery\": null, \"full_state_mean_de\n--- scan_GRID: (3921 chars) {\"0\": {\"cv_recovery_by_fold\": [], \"cv_median_recovery\": null, \"full_state_mean_delta_held96\": 0.06301768620808919, \"full_state_flip_share_held96\": 0.6770833333333334, \"note\": \"full-state exchange moves < 10% of pairs by >= 1 nat: recovery undefined, not fitted\"}, \"2\": {\"cv_recovery_by_fold\": [], \"cv_median_recovery\": null, \"full_state_mean_delta_held96\": 0.01619398593902588, \"full_state_flip_share_held96\": 0.4791666666666667, \"note\": \"full-state exchange moves < 10% of pairs by >= 1 nat: recovery undefined, not fitted\"}, \"4\": {\"cv_recovery_by_fold\": [], \"cv_median_recovery\": null, \"full_state_\n--- gen_T10_dec: (6530 chars) {\"unit\": \"T10\", \"site\": \"dec\", \"classes\": {\"bfs\": {\"arms\": {\"BASE\": {\"n_planned\": 30, \"n\": 30, \"correct_target\": 0, \"share\": 0.0, \"wilson95\": [0.0, 0.113517091390478], \"attempted_target\": 0, \"pass_rate\": 0.8333333333333334, \"other_share\": 0.0, \"labels\": {\"union_find\": 28, \"dfs\": 2}, \"correct_default\": 23, \"invalid\": 0}, \"FULL\": {\"n_planned\": 30, \"n\": 30, \"correct_target\": 0, \"share\": 0.0, \"wilson95\": [0.0, 0.113517091390478], \"attempted_target\": 0, \"pass_rate\": 0.7666666666666667, \"other_share\": 0.0, \"labels\": {\"union_find\": 29, \"dfs\": 1}, \"correct_default\": 22, \"invalid\": 0}, \"DAS\": {\"n_plann\n--- gen_T10_band: (6705 chars) {\"unit\": \"T10\", \"site\": \"band\", \"classes\": {\"bfs\": {\"arms\": {\"BASE\": {\"n_planned\": 30, \"n\": 30, \"correct_target\": 0, \"share\": 0.0, \"wilson95\": [0.0, 0.113517091390478], \"attempted_target\": 0, \"pass_rate\": 1.0, \"other_share\": 0.0, \"labels\": {\"union_find\": 30}, \"correct_default\": 30, \"invalid\": 0}, \"FULL\": {\"n_planned\": 30, \"n\": 30, \"correct_target\": 23, \"share\": 0.7666666666666667, \"wilson95\": [0.5907132766967574, 0.8820776078949878], \"attempted_target\": 23, \"pass_rate\": 1.0, \"other_share\": 0.0, \"labels\": {\"bfs\": 23, \"dfs\": 7}, \"correct_default\": 0, \"invalid\": 0}, \"DAS\": {\"n_planned\": 30, \"n\": \n--- gen_GRID_dec: (4182 chars) {\"unit\": \"GRID\", \"site\": \"dec\", \"classes\": {\"bfs\": {\"arms\": {\"BASE\": {\"n_planned\": 30, \"n\": 30, \"correct_target\": 6, \"share\": 0.2, \"wilson95\": [0.09504978102401235, 0.37306047381027446], \"attempted_target\": 8, \"pass_rate\": 0.9, \"other_share\": 0.0, \"labels\": {\"dfs\": 21, \"bfs\": 8, \"disputed\": 1}, \"correct_default\": null, \"invalid\": 0}, \"FULL\": {\"n_planned\": 30, \"n\": 30, \"correct_target\": 10, \"share\": 0.3333333333333333, \"wilson95\": [0.19230295526846194, 0.5122027418616973], \"attempted_target\": 24, \"pass_rate\": 0.43333333333333335, \"other_share\": 0.0, \"labels\": {\"bfs\": 24, \"disputed\": 3, \"dfs\": 3\n\n=== DATASET T10_dec_generation n_examples(preview)= 3 keys: ['dataset', 'examples']\n   input: \"[T10 | dec site | target class bfs | slot 0] BASE PROMPT: user\\nBaby is not allowed here. . . . . . . .\\n\\nTask: write a Python function solve(n, edges) that returns the number of connected components of...\"\n   output: \"bfs\"\n   metadata_unit: \"T10\"\n   metadata_site: \"dec\"\n   metadata_target_class: \"bfs\"\n   metadata_slot: 0\n   metadata_base_key: \"T10|twin|W4|baby\"\n   metadata_source_key: \"T10|forced|k3|j0|bfs\"\n   predict_BASE: \"union_find|pass\"\n   predict_FULL: \"union_find|pass\"\n   predict_DAS: \"bfs|fail\"\n   predict_RAND: \"union_find|pass\"\n   predict_PERM: \"dfs|pass\"\n   predict_REV_DAS: \"bfs|pass\"\n   predict_REV_FULL: \"bfs|pass\"\n   predict_SRC: \"bfs|pass\"\n=== DATASET T10_band_generation n_examples(preview)= 3 keys: ['dataset', 'examples']\n   input: \"[T10 | band site | target class bfs | slot 0] BASE PROMPT: user\\nBaby is not allowed here. . . . . . . .\\n\\nTask: write a Python function solve(n, edges) that returns the number of connected components o...\"\n   output: \"bfs\"\n   metadata_unit: \"T10\"\n   metadata_site: \"band\"\n   metadata_target_class: \"bfs\"\n   metadata_slot: 0\n   metadata_base_key: \"T10|twin|W4|baby\"\n   metadata_source_key: \"T10|forced|k3|j0|bfs\"\n   predict_BASE: \"union_find|pass\"\n   predict_FULL: \"bfs|pass\"\n   predict_DAS: \"bfs|pass\"\n   predict_RAND: \"union_find|pass\"\n   predict_PERM: \"bfs|pass\"\n   predict_REV_DAS: \"bfs|pass\"\n   predict_REV_FULL: \"bfs|pass\"\n   predict_SRC: \"bfs|pass\"\n=== DATASET T10_dec_teacher_forced n_examples(preview)= 3 keys: ['dataset', 'examples']\n   input: \"[T10 | dec | teacher-forced held-out pair] source=T10|forced|k3|j0|bfs base=T10|twin|W5|school\"\n   output: \"bfs\"\n   metadata_class_src: \"bfs\"\n   metadata_class_base: \"dfs\"\n   metadata_delta_full: 1.3749771118164062\n   predict_seed0_k1: \"11.7070\"\n   predict_seed0_k2: \"12.9301\"\n   predict_seed0_k4: \"13.1611\"\n   predict_seed0_k8: \"13.1611\"\n   predict_seed1_k1: \"12.2014\"\n   predict_seed1_k2: \"12.6611\"\n   predict_seed1_k4: \"13.3872\"\n   predict_seed1_k8: \"13.7323\"\n   predict_seed2_k1: \"10.9570\"\n   predict_seed2_k2: \"11.6880\"\n   predict_seed2_k4: \"11.9380\"\n   predict_seed2_k8: \"12.3998\"", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [27] THINKING · 2026-10-26 13:39:47 UTC

```
I'll stream the full output through Python to list all 8 dataset names and counts (not their contents), while also reviewing the CPU-side source behind `method.py --cpu-only`.
```

### [28] TOOL CALL — Bash · 2026-10-26 13:39:47 UTC

```
List all datasets and example counts in full and mini outputs:
python3 - <<'EOF'
import json
A="/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40"
for fn in ["full_method_out.json","mini_method_out.json"]:
    d=json.load(open(A+"/"+fn))
    print("FILE", fn)
    for ds in d["datasets"]:
        exs=ds["examples"]
        keys=sorted({k for e in exs for k in e})
        print(f"  {ds['dataset']}: n={len(exs)}  keys={keys}")
EOF
```

### [29] TOOL RESULT — Bash · 2026-10-26 13:39:47 UTC

```
{"stdout": "FILE full_method_out.json\n  T10_dec_generation: n=60  keys=['input', 'metadata_base_key', 'metadata_site', 'metadata_slot', 'metadata_source_key', 'metadata_target_class', 'metadata_unit', 'output', 'predict_BASE', 'predict_DAS', 'predict_DAS_k1', 'predict_DAS_k2', 'predict_FULL', 'predict_PERM', 'predict_RAND', 'predict_REV_DAS', 'predict_REV_FULL', 'predict_SRC']\n  T10_band_generation: n=60  keys=['input', 'metadata_base_key', 'metadata_site', 'metadata_slot', 'metadata_source_key', 'metadata_target_class', 'metadata_unit', 'output', 'predict_BASE', 'predict_DAS', 'predict_DAS_k1', 'predict_DAS_k4', 'predict_FULL', 'predict_PERM', 'predict_RAND', 'predict_REV_DAS', 'predict_REV_FULL', 'predict_SRC']\n  T10_dec_teacher_forced: n=600  keys=['input', 'metadata_class_base', 'metadata_class_src', 'metadata_delta_full', 'output', 'predict_seed0_k1', 'predict_seed0_k2', 'predict_seed0_k4', 'predict_seed0_k8', 'predict_seed1_k1', 'predict_seed1_k2', 'predict_seed1_k4', 'predict_seed1_k8', 'predict_seed2_k1', 'predict_seed2_k2', 'predict_seed2_k4', 'predict_seed2_k8']\n  T10_band_teacher_forced: n=96  keys=['input', 'metadata_class_base', 'metadata_class_src', 'metadata_delta_full', 'output', 'predict_seed0_k1', 'predict_seed0_k2', 'predict_seed0_k4', 'predict_seed0_k8', 'predict_seed1_k1', 'predict_seed1_k2', 'predict_seed1_k4', 'predict_seed1_k8']\n  T10_dec_L24_teacher_forced: n=600  keys=['input', 'metadata_class_base', 'metadata_class_src', 'metadata_delta_full', 'output', 'predict_seed0_k1', 'predict_seed0_k2', 'predict_seed0_k4', 'predict_seed0_k8', 'predict_seed1_k1', 'predict_seed1_k2', 'predict_seed1_k4', 'predict_seed1_k8', 'predict_seed2_k1', 'predict_seed2_k2', 'predict_seed2_k4', 'predict_seed2_k8']\n  GRID_dec_generation: n=30  keys=['input', 'metadata_base_key', 'metadata_site', 'metadata_slot', 'metadata_source_key', 'metadata_target_class', 'metadata_unit', 'output', 'predict_BASE', 'predict_DAS', 'predict_DAS_k1', 'predict_DAS_k2', 'predict_FULL', 'predict_PERM', 'predict_RAND', 'predict_REV_DAS', 'predict_REV_FULL', 'predict_SRC']\n  GRID_dec_teacher_forced: n=112  keys=['input', 'metadata_class_base', 'metadata_class_src', 'metadata_delta_full', 'output', 'predict_seed0_k1', 'predict_seed0_k2', 'predict_seed0_k4', 'predict_seed0_k8', 'predict_seed1_k1', 'predict_seed1_k2', 'predict_seed1_k4', 'predict_seed1_k8', 'predict_seed2_k1', 'predict_seed2_k2', 'predict_seed2_k4', 'predict_seed2_k8']\n  T10_mediation_clamp_prospective: n=484  keys=['input', 'metadata_direction_seed', 'metadata_pi_committed', 'metadata_slot', 'output', 'predict_DEC', 'predict_PUSH', 'predict_RAND', 'predict_TASK']\nFILE mini_method_out.json\n  T10_dec_generation: n=3  keys=['input', 'metadata_base_key', 'metadata_site', 'metadata_slot', 'metadata_source_key', 'metadata_target_class', 'metadata_unit', 'output', 'predict_BASE', 'predict_DAS', 'predict_FULL', 'predict_PERM', 'predict_RAND', 'predict_REV_DAS', 'predict_REV_FULL', 'predict_SRC']\n  T10_band_generation: n=3  keys=['input', 'metadata_base_key', 'metadata_site', 'metadata_slot', 'metadata_source_key', 'metadata_target_class', 'metadata_unit', 'output', 'predict_BASE', 'predict_DAS', 'predict_FULL', 'predict_PERM', 'predict_RAND', 'predict_REV_DAS', 'predict_REV_FULL', 'predict_SRC']\n  T10_dec_teacher_forced: n=3  keys=['input', 'metadata_class_base', 'metadata_class_src', 'metadata_delta_full', 'output', 'predict_seed0_k1', 'predict_seed0_k2', 'predict_seed0_k4', 'predict_seed0_k8', 'predict_seed1_k1', 'predict_seed1_k2', 'predict_seed1_k4', 'predict_seed1_k8', 'predict_seed2_k1', 'predict_seed2_k2', 'predict_seed2_k4', 'predict_seed2_k8']\n  T10_band_teacher_forced: n=3  keys=['input', 'metadata_class_base', 'metadata_class_src', 'metadata_delta_full', 'output', 'predict_seed0_k1', 'predict_seed0_k2', 'predict_seed0_k4', 'predict_seed0_k8', 'predict_seed1_k1', 'predict_seed1_k2', 'predict_seed1_k4', 'predict_seed1_k8']\n  T10_dec_L24_teacher_forced: n=3  keys=['input', 'metadata_class_base', 'metadata_class_src', 'metadata_delta_full', 'output', 'predict_seed0_k1', 'predict_seed0_k2', 'predict_seed0_k4', 'predict_seed0_k8', 'predict_seed1_k1', 'predict_seed1_k2', 'predict_seed1_k4', 'predict_seed1_k8', 'predict_seed2_k1', 'predict_seed2_k2', 'predict_seed2_k4', 'predict_seed2_k8']\n  GRID_dec_generation: n=3  keys=['input', 'metadata_base_key', 'metadata_site', 'metadata_slot', 'metadata_source_key', 'metadata_target_class', 'metadata_unit', 'output', 'predict_BASE', 'predict_DAS', 'predict_DAS_k1', 'predict_DAS_k2', 'predict_FULL', 'predict_PERM', 'predict_RAND', 'predict_REV_DAS', 'predict_REV_FULL', 'predict_SRC']\n  GRID_dec_teacher_forced: n=3  keys=['input', 'metadata_class_base', 'metadata_class_src', 'metadata_delta_full', 'output', 'predict_seed0_k1', 'predict_seed0_k2', 'predict_seed0_k4', 'predict_seed0_k8', 'predict_seed1_k1', 'predict_seed1_k2', 'predict_seed1_k4', 'predict_seed1_k8', 'predict_seed2_k1', 'predict_seed2_k2', 'predict_seed2_k4', 'predict_seed2_k8']\n  T10_mediation_clamp_prospective: n=3  keys=['input', 'metadata_direction_seed', 'metadata_pi_committed', 'metadata_slot', 'output', 'predict_PUSH', 'predict_RAND', 'predict_TASK']", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [30] TOOL CALL — Bash · 2026-10-26 13:39:47 UTC

```
Read cfg8.py and stats8.py source:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40; cat -n $A/src/cfg8.py; echo "=========== stats8 ==========="; cat -n $A/src/stats8.py
```

### [31] TOOL RESULT — Bash · 2026-10-26 13:39:47 UTC

````
{"stdout": "     1\t#!/usr/bin/env python3\n     2\t\"\"\"Iteration-8 constants and utilities: one DAS protocol (linear orthonormal map, bounded KL objective, class-margin\n     3\treadout) at the decision token and the task band of Qwen3-8B (T10) and at the decision token of gemma-3-4b-it (T1 grid).\n     4\t\n     5\tConventions (inherited from iterations 6-7, restated in README.md):\n     6\t- BLOCK l = decoder block l (0-based); its OUTPUT is HF hidden_states[l + 1]. Every edit replaces a block output.\n     7\t- Decision position d: the position of the last prefilled opening token; its next-token logits choose the decision\n     8\t  token (T10: response token 11 after ' def'; grid: response index 32 after c*).\n     9\t- Class probability P(c) = sum of softmax mass over the class token set T_c; P(other) = 1 - sum_c P(c).\n    10\t- Margin = log P(c_src) - log P(c_base); Delta = margin_edit - margin_base on the SAME computation path.\n    11\t- CRN: slot s of a unit uses u_stream(unit, 'iter8', s) (PCG64 of a sha256 seed); every arm of a cell shares it.\n    12\t\"\"\"\n    13\t\n    14\tfrom __future__ import annotations\n    15\t\n    16\timport hashlib\n    17\timport json\n    18\timport math\n    19\timport os\n    20\timport resource\n    21\timport sys\n    22\tfrom datetime import datetime, timezone\n    23\tfrom pathlib import Path\n    24\tfrom typing import Any, Iterable\n    25\t\n    26\timport numpy as np\n    27\tfrom loguru import logger\n    28\t\n    29\tROOT = Path(__file__).resolve().parents[1]\n    30\tINPUTS = ROOT / \"inputs\"\n    31\tDATA = ROOT / \"data\"\n    32\tRESULTS = ROOT / \"results\"\n    33\tFIGS = ROOT / \"figures\"\n    34\tLOGS = ROOT / \"logs\"\n    35\tCACHE = ROOT / \"cache\"\n    36\tMAPS = ROOT / \"das_maps\"\n    37\tPRED = ROOT / \"predictions\"\n    38\tAUDIT = ROOT / \"audit\"\n    39\tPROMPTS_DIR = ROOT / \"prompts\"\n    40\tfor _d in (DATA, RESULTS, FIGS, LOGS, CACHE, MAPS, PRED, AUDIT, PROMPTS_DIR):\n    41\t    _d.mkdir(parents=True, exist_ok=True)\n    42\tCOMMIT_LOG = ROOT / \"commitments.log\"\n    43\tDEVIATIONS = RESULTS / \"deviations.jsonl\"\n    44\t\n    45\t# Source artifacts (read-only; only s0_inputs.py reads them). This folder sits at\n    46\t# <run>/3_invention_loop/iter_8/gen_art/<artifact>; earlier iterations are found relative to it (override: AII_LOOP_DIR).\n    47\tLOOP = Path(os.environ.get(\"AII_LOOP_DIR\", ROOT.parents[2]))\n    48\t\n    49\t# ------------------------------------------------------------------------------------------------ models\n    50\tQWEN_ID = \"Qwen/Qwen3-8B\"\n    51\tQWEN_REV = \"b968826d9c46dd6066d109eabc6255188de91218\"\n    52\tGEMMA_ID = \"google/gemma-3-4b-it\"\n    53\tGEMMA_REV = \"093f9f388b31de276ce2de164bdc2081324b9767\"\n    54\tFAMILY = {\n    55\t    \"qwen\": {\"id\": QWEN_ID, \"rev\": QWEN_REV, \"n_layers\": 36, \"d_model\": 4096, \"n_kv\": 8, \"head_dim\": 128,\n    56\t             \"band\": tuple(range(12, 24)), \"stop_ids\": (151645, 151643)},\n    57\t    \"gemma\": {\"id\": GEMMA_ID, \"rev\": GEMMA_REV, \"n_layers\": 34, \"d_model\": 2560, \"n_kv\": 4, \"head_dim\": 256,\n    58\t              \"band\": tuple(range(11, 23)), \"stop_ids\": (1, 106)},\n    59\t}\n    60\t\n    61\t# ------------------------------------------------------------------------------------------------ units\n    62\t# T10 (Qwen3-8B): canonical opening tokens 0..10 = '```python\\ndef solve(n, edges):\\n' + indent + ' def'\n    63\tOPEN_T10 = [73594, 12669, 198, 750, 11625, 1445, 11, 12822, 982, 262, 707]\n    64\tUNITS = {\n    65\t    \"T10\": {\"family\": \"qwen\", \"task\": \"T10\", \"default\": \"union_find\", \"classes\": [\"bfs\", \"dfs\", \"union_find\"],\n    66\t            \"primary\": \"dfs\", \"max_new\": 512, \"fence\": \"bench\"},\n    67\t    \"GRID\": {\"family\": \"gemma\", \"task\": \"T1\", \"default\": None, \"classes\": [\"bfs\", \"dfs\"], \"primary\": \"bfs\",\n    68\t             \"max_new\": 1024, \"fence\": \"path\"},\n    69\t}\n    70\t# display names of the forced sources (equal-structure paraphrases; template k x name j)\n    71\tT10_FORCED_TEMPLATES = (\"Implement {j} for this task.\", \"Use {j} to solve this task.\", \"Solve this task with {j}.\",\n    72\t                        \"Your solution should use {j}.\", \"Write an implementation based on {j}.\")\n    73\tT10_DISPLAY = {\n    74\t    \"bfs\": (\"breadth-first search (BFS)\", \"BFS\", \"breadth-first search\", \"a breadth-first search\"),\n    75\t    \"dfs\": (\"depth-first search (DFS)\", \"DFS\", \"depth-first search\", \"a depth-first search\"),\n    76\t    \"union_find\": (\"union-find (disjoint set union)\", \"union-find\", \"a disjoint-set union\", \"a union-find structure\"),\n    77\t}\n    78\tTRAIN_FAM = (0, 1, 2)\n    79\tHELD_FAM = (3, 4)\n    80\tTRAIN_W = (\"W1\", \"W2\", \"W3\")\n    81\tHELD_W = (\"W4\", \"W5\")\n    82\tNOUN_SPLIT_SEED = 8001\n    83\tN_T10_NOUNS = 32                      # 12 frozen (iteration 7) + 20 single-token nouns from art_j3Rm_lr2nzR6\n    84\t\n    85\t# ------------------------------------------------------------------------------------------------ DAS protocol\n    86\tRANKS = (1, 2, 4, 8)\n    87\tK_MAX = 8\n    88\tFIT_STEPS = 240\n    89\tSCAN_STEPS = 100\n    90\tLR = 2e-2\n    91\tBATCH_DEC = 48\n    92\tBATCH_BAND = 8\n    93\tVAL_EVERY = 20\n    94\tPATIENCE = 3\n    95\tN_RANDOM_SUBSPACES = 50\n    96\tRANDOM_SEED0 = 7000\n    97\tLABEL_CONTROL_SEEDS = (10, 11, 12)\n    98\tFIT_SEEDS = (0, 1, 2)\n    99\tN_BOOT = 2000\n   100\tBOOT_SEED = 20261023\n   101\tOFF_MANIFOLD = 1.5\n   102\tTRAIN_PAIR_CAP = 2000\n   103\tHELD_PAIR_CAP = 600\n   104\tTHRESH = {\"c1_median_max\": 0.05, \"c2_ratio_max\": 0.10, \"c3_ratio_max\": 0.25, \"c4_min\": 0.5, \"c5_min\": 0.5,\n   105\t          \"c6_pct\": 95.0, \"c7_cos_min\": 0.5, \"c7_pct\": 99.0, \"V0_tf\": 0.5, \"V0_tf_lo\": 0.25, \"V0_gen\": 0.5,\n   106\t          \"V0_pass_ratio\": 0.8, \"V0_mcnemar_p\": 0.05}\n   107\tPROSPECTIVE_SEEDS = tuple(range(98001, 98025))\n   108\tBUDGET_MSG = \"AI Inventor per-run OpenRouter budget\"\n   109\tOPENROUTER_CAP_USD = 0.30\n   110\t\n   111\t\n   112\t# ------------------------------------------------------------------------------------------------ utils\n   113\tdef setup_logging(name: str) -> None:\n   114\t    logger.remove()\n   115\t    logger.add(sys.stdout, level=\"INFO\", format=\"{time:HH:mm:ss}|{level:<7}|{message}\")\n   116\t    logger.add(str(LOGS / f\"{name}.log\"), rotation=\"30 MB\", level=\"DEBUG\")\n   117\t\n   118\t\n   119\tdef set_ram_limit(gb: float) -> None:\n   120\t    lim = int(gb * 1024 ** 3)\n   121\t    try:\n   122\t        resource.setrlimit(resource.RLIMIT_AS, (lim, lim))\n   123\t    except (ValueError, OSError) as e:\n   124\t        logger.warning(f\"could not set RLIMIT_AS: {e}\")\n   125\t\n   126\t\n   127\tdef detect_cpus() -> int:\n   128\t    try:\n   129\t        q = int(Path(\"/sys/fs/cgroup/cpu/cpu.cfs_quota_us\").read_text())\n   130\t        p = int(Path(\"/sys/fs/cgroup/cpu/cpu.cfs_period_us\").read_text())\n   131\t        if q > 0:\n   132\t            return max(1, math.ceil(q / p))\n   133\t    except (FileNotFoundError, ValueError):\n   134\t        pass\n   135\t    try:\n   136\t        return len(os.sched_getaffinity(0))\n   137\t    except (AttributeError, OSError):\n   138\t        return os.cpu_count() or 1\n   139\t\n   140\t\n   141\tdef utc_now() -> str:\n   142\t    return datetime.now(timezone.utc).strftime(\"%Y-%m-%dT%H:%M:%S.%fZ\")\n   143\t\n   144\t\n   145\tdef sha256_text(s: str) -> str:\n   146\t    return hashlib.sha256(s.encode(\"utf-8\")).hexdigest()\n   147\t\n   148\t\n   149\tdef sha256_file(p: Path) -> str:\n   150\t    h = hashlib.sha256()\n   151\t    with open(p, \"rb\") as fh:\n   152\t        for chunk in iter(lambda: fh.read(1 << 20), b\"\"):\n   153\t            h.update(chunk)\n   154\t    return h.hexdigest()\n   155\t\n   156\t\n   157\tdef stable_seed(*parts: Any) -> int:\n   158\t    \"\"\"Deterministic 63-bit seed from arbitrary parts (sha256 of their '|'-joined repr) -- exp8/exp17 convention.\"\"\"\n   159\t    return int(hashlib.sha256(\"|\".join(str(p) for p in parts).encode()).hexdigest(), 16) % (2 ** 63)\n   160\t\n   161\t\n   162\tdef u_stream(*key: Any, n: int = 1536) -> np.ndarray:\n   163\t    return np.random.Generator(np.random.PCG64(stable_seed(*key))).random(n)\n   164\t\n   165\t\n   166\tdef _json_default(o: Any) -> Any:\n   167\t    if isinstance(o, np.integer):\n   168\t        return int(o)\n   169\t    if isinstance(o, np.floating):\n   170\t        return None if not np.isfinite(o) else float(o)\n   171\t    if isinstance(o, np.ndarray):\n   172\t        return o.tolist()\n   173\t    if isinstance(o, np.bool_):\n   174\t        return bool(o)\n   175\t    if isinstance(o, Path):\n   176\t        return str(o)\n   177\t    if isinstance(o, (set, frozenset)):\n   178\t        return sorted(o)\n   179\t    if isinstance(o, float) and not math.isfinite(o):\n   180\t        return None\n   181\t    raise TypeError(f\"not JSON serialisable: {type(o)}\")\n   182\t\n   183\t\n   184\tdef _clean(o: Any) -> Any:\n   185\t    if isinstance(o, float):\n   186\t        return o if math.isfinite(o) else None\n   187\t    if isinstance(o, dict):\n   188\t        return {str(k): _clean(v) for k, v in o.items()}\n   189\t    if isinstance(o, (list, tuple)):\n   190\t        return [_clean(v) for v in o]\n   191\t    return o\n   192\t\n   193\t\n   194\tdef read_json(p: Path) -> Any:\n   195\t    return json.loads(Path(p).read_text())\n   196\t\n   197\t\n   198\tdef write_json(p: Path, obj: Any) -> None:\n   199\t    p = Path(p)\n   200\t    p.parent.mkdir(parents=True, exist_ok=True)\n   201\t    tmp = p.with_suffix(p.suffix + \".tmp\")\n   202\t    tmp.write_text(json.dumps(_clean(obj), indent=1, default=_json_default))\n   203\t    tmp.replace(p)\n   204\t\n   205\t\n   206\tdef read_jsonl(p: Path) -> list[dict[str, Any]]:\n   207\t    p = Path(p)\n   208\t    if not p.exists():\n   209\t        return []\n   210\t    out = []\n   211\t    with open(p) as fh:\n   212\t        for line in fh:\n   213\t            line = line.strip()\n   214\t            if line:\n   215\t                try:\n   216\t                    out.append(json.loads(line))\n   217\t                except json.JSONDecodeError:\n   218\t                    logger.warning(f\"skipping malformed line in {p.name}\")\n   219\t    return out\n   220\t\n   221\t\n   222\tdef append_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:\n   223\t    p = Path(p)\n   224\t    p.parent.mkdir(parents=True, exist_ok=True)\n   225\t    with open(p, \"a\") as fh:\n   226\t        for r in rows:\n   227\t            fh.write(json.dumps(_clean(r), default=_json_default) + \"\\n\")\n   228\t        fh.flush()\n   229\t\n   230\t\n   231\tdef write_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:\n   232\t    p = Path(p)\n   233\t    p.parent.mkdir(parents=True, exist_ok=True)\n   234\t    tmp = p.with_suffix(p.suffix + \".tmp\")\n   235\t    with open(tmp, \"w\") as fh:\n   236\t        for r in rows:\n   237\t            fh.write(json.dumps(_clean(r), default=_json_default) + \"\\n\")\n   238\t    tmp.replace(p)\n   239\t\n   240\t\n   241\tdef add_deviation(key: str, text: str, **kw: Any) -> None:\n   242\t    append_jsonl(DEVIATIONS, [{\"key\": key, \"text\": text, \"utc\": utc_now(), **kw}])\n   243\t    logger.warning(f\"DEVIATION {key}: {text}\")\n   244\t\n   245\t\n   246\tdef model_path(model_id: str, revision: str) -> str:\n   247\t    cache = os.environ.get(\"HF_HUB_CACHE\")\n   248\t    if cache:\n   249\t        snap = Path(cache) / (\"models--\" + model_id.replace(\"/\", \"--\")) / \"snapshots\" / revision\n   250\t        if snap.exists():\n   251\t            return str(snap)\n   252\t    return model_id\n=========== stats8 ===========\n     1\t#!/usr/bin/env python3\n     2\t\"\"\"Statistics: normalised recovery with a two-way cluster bootstrap (source prompts x base prompts), Wilson\n     3\tintervals, exact McNemar on CRN-paired outcomes, one-sided Wilcoxon, Spearman with permutation p.\"\"\"\n     4\t\n     5\tfrom __future__ import annotations\n     6\t\n     7\timport math\n     8\tfrom typing import Any\n     9\t\n    10\timport numpy as np\n    11\tfrom scipy import stats\n    12\t\n    13\t\n    14\tdef recovery(d_edit: np.ndarray, d_full: np.ndarray, src: list[str], base: list[str], n_boot: int = 2000,\n    15\t             seed: int = 0, min_full: float = 1.0) -> dict[str, Any]:\n    16\t    \"\"\"recovery = mean(Delta_edit) / mean(Delta_full) over pairs with |Delta_full| >= min_full; CI by resampling\n    17\t    source and base prompts independently (a pair enters with multiplicity count_src x count_base).\"\"\"\n    18\t    d_edit = np.asarray(d_edit, float)\n    19\t    d_full = np.asarray(d_full, float)\n    20\t    ok = np.abs(d_full) >= min_full\n    21\t    if ok.sum() == 0:\n    22\t        return {\"n\": 0, \"recovery\": None}\n    23\t    de, df = d_edit[ok], d_full[ok]\n    24\t    s = np.array(src)[ok]\n    25\t    b = np.array(base)[ok]\n    26\t    us, ub = np.unique(s), np.unique(b)\n    27\t    si = np.searchsorted(us, s)\n    28\t    bi = np.searchsorted(ub, b)\n    29\t    point = float(de.mean() / df.mean())\n    30\t    rng = np.random.default_rng(seed)\n    31\t    boots = []\n    32\t    for _ in range(n_boot):\n    33\t        cs = np.bincount(rng.integers(0, len(us), len(us)), minlength=len(us))\n    34\t        cb = np.bincount(rng.integers(0, len(ub), len(ub)), minlength=len(ub))\n    35\t        w = cs[si] * cb[bi]\n    36\t        if w.sum() == 0 or (w * df).sum() == 0:\n    37\t            continue\n    38\t        boots.append(float((w * de).sum() / (w * df).sum()))\n    39\t    lo, hi = (float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))) if boots else (None, None)\n    40\t    return {\"n\": int(ok.sum()), \"n_src\": int(len(us)), \"n_base\": int(len(ub)), \"recovery\": point, \"ci95\": [lo, hi],\n    41\t            \"mean_delta_edit\": float(de.mean()), \"mean_delta_full\": float(df.mean()),\n    42\t            \"iia_like_share_positive\": float(np.mean(de > 0))}\n    43\t\n    44\t\n    45\tdef ratio_ci(num: np.ndarray, den_mean: float, src: list[str], base: list[str], n_boot: int = 2000, seed: int = 0\n    46\t             ) -> dict[str, Any]:\n    47\t    \"\"\"mean(num) / den_mean with a two-way cluster bootstrap of the numerator (denominator held fixed).\"\"\"\n    48\t    num = np.asarray(num, float)\n    49\t    s, b = np.array(src), np.array(base)\n    50\t    us, ub = np.unique(s), np.unique(b)\n    51\t    si, bi = np.searchsorted(us, s), np.searchsorted(ub, b)\n    52\t    rng = np.random.default_rng(seed)\n    53\t    boots = []\n    54\t    for _ in range(n_boot):\n    55\t        cs = np.bincount(rng.integers(0, len(us), len(us)), minlength=len(us))\n    56\t        cb = np.bincount(rng.integers(0, len(ub), len(ub)), minlength=len(ub))\n    57\t        w = cs[si] * cb[bi]\n    58\t        if w.sum():\n    59\t            boots.append(float((w * num).sum() / w.sum() / den_mean))\n    60\t    return {\"ratio\": float(num.mean() / den_mean) if den_mean else None,\n    61\t            \"ci95\": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))] if boots else None}\n    62\t\n    63\t\n    64\tdef wilson(k: int, n: int, z: float = 1.96) -> list[float | None]:\n    65\t    if n == 0:\n    66\t        return [None, None]\n    67\t    p = k / n\n    68\t    den = 1 + z * z / n\n    69\t    c = (p + z * z / (2 * n)) / den\n    70\t    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den\n    71\t    return [max(0.0, c - h), min(1.0, c + h)]\n    72\t\n    73\t\n    74\tdef mcnemar(a: list[bool], b: list[bool]) -> dict[str, Any]:\n    75\t    \"\"\"Exact two-sided McNemar on paired booleans (a vs b): discordant counts and p.\"\"\"\n    76\t    n10 = sum(1 for x, y in zip(a, b) if x and not y)\n    77\t    n01 = sum(1 for x, y in zip(a, b) if y and not x)\n    78\t    n = n10 + n01\n    79\t    p = float(stats.binomtest(n10, n, 0.5).pvalue) if n else 1.0\n    80\t    p1 = float(stats.binomtest(n10, n, 0.5, alternative=\"greater\").pvalue) if n else 1.0\n    81\t    return {\"a_only\": n10, \"b_only\": n01, \"p_two_sided\": p, \"p_one_sided_a_gt_b\": p1}\n    82\t\n    83\t\n    84\tdef wilcoxon_greater(x: np.ndarray, y: np.ndarray) -> float:\n    85\t    d = np.asarray(x, float) - np.asarray(y, float)\n    86\t    d = d[d != 0]\n    87\t    if d.size < 3:\n    88\t        return 1.0\n    89\t    return float(stats.wilcoxon(d, alternative=\"greater\").pvalue)\n    90\t\n    91\t\n    92\tdef cluster_wilcoxon_p(x: np.ndarray, y: np.ndarray, src: list[str], base: list[str], n_boot: int = 2000,\n    93\t                       seed: int = 0) -> dict[str, Any]:\n    94\t    \"\"\"One-sided pair-level test of mean(x - y) > 0 with a two-way cluster bootstrap (p = share of resamples <= 0).\"\"\"\n    95\t    d = np.asarray(x, float) - np.asarray(y, float)\n    96\t    s, b = np.array(src), np.array(base)\n    97\t    us, ub = np.unique(s), np.unique(b)\n    98\t    si, bi = np.searchsorted(us, s), np.searchsorted(ub, b)\n    99\t    rng = np.random.default_rng(seed)\n   100\t    ms = []\n   101\t    for _ in range(n_boot):\n   102\t        cs = np.bincount(rng.integers(0, len(us), len(us)), minlength=len(us))\n   103\t        cb = np.bincount(rng.integers(0, len(ub), len(ub)), minlength=len(ub))\n   104\t        w = cs[si] * cb[bi]\n   105\t        if w.sum():\n   106\t            ms.append(float((w * d).sum() / w.sum()))\n   107\t    ms = np.array(ms)\n   108\t    return {\"mean_diff\": float(d.mean()), \"p_cluster_boot\": float((np.sum(ms <= 0) + 1) / (len(ms) + 1)),\n   109\t            \"p_wilcoxon_pairs\": wilcoxon_greater(x, y)}\n   110\t\n   111\t\n   112\tdef spearman_perm(x: np.ndarray, y: np.ndarray, n_perm: int = 10000, seed: int = 0) -> dict[str, Any]:\n   113\t    x, y = np.asarray(x, float), np.asarray(y, float)\n   114\t    if len(x) < 4:\n   115\t        return {\"rho\": None, \"p_one_sided\": None, \"n\": int(len(x))}\n   116\t    rho = float(stats.spearmanr(x, y).statistic)\n   117\t    rng = np.random.default_rng(seed)\n   118\t    cnt = 0\n   119\t    for _ in range(n_perm):\n   120\t        r = stats.spearmanr(x, rng.permutation(y)).statistic\n   121\t        if r >= rho:\n   122\t            cnt += 1\n   123\t    return {\"rho\": rho, \"p_one_sided\": (cnt + 1) / (n_perm + 1), \"n\": int(len(x))}\n   124\t\n   125\t\n   126\tdef partial_spearman(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> float | None:\n   127\t    \"\"\"Spearman partial correlation of x and y controlling z (rank-residual method).\"\"\"\n   128\t    if len(x) < 5:\n   129\t        return None\n   130\t    rx, ry, rz = (stats.rankdata(v) for v in (x, y, z))\n   131\t    A = np.vstack([rz, np.ones_like(rz)]).T\n   132\t    ex = rx - A @ np.linalg.lstsq(A, rx, rcond=None)[0]\n   133\t    ey = ry - A @ np.linalg.lstsq(A, ry, rcond=None)[0]\n   134\t    den = np.sqrt((ex ** 2).sum() * (ey ** 2).sum())\n   135\t    return float((ex * ey).sum() / den) if den else None", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
````

### [32] ASSISTANT · 2026-10-26 13:39:53 UTC

```
Now the CPU-only stages themselves: `analysis8.py`, `outputs8.py`, `digest8.py`, `novelty8.py`, `figures8.py`, and the stdlib audit `rederive.py`.
```

### [33] TOOL CALL — Bash · 2026-10-26 13:39:53 UTC

```
Read analysis8.py source:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40; cat -n $A/src/analysis8.py
```

### [34] TOOL RESULT — Bash · 2026-10-26 13:39:53 UTC

```
{"stdout": "     1\t#!/usr/bin/env python3\n     2\t\"\"\"Analysis: generation tables, verdicts per (unit, site), K2 and p_K2, mediation outcomes (clamp, prospective),\n     3\tgeometry figures (actual activation coordinates) and the method_out.json rows.\n     4\t\n     5\tUsage: python src/analysis8.py\n     6\t\"\"\"\n     7\t\n     8\tfrom __future__ import annotations\n     9\t\n    10\timport json\n    11\timport sys\n    12\tfrom pathlib import Path\n    13\tfrom typing import Any\n    14\t\n    15\tsys.path.insert(0, str(Path(__file__).resolve().parent))\n    16\t\n    17\timport numpy as np\n    18\tfrom loguru import logger\n    19\t\n    20\timport stats8 as ST\n    21\tfrom cfg8 import (DATA, FIGS, PRED, RESULTS, THRESH, UNITS, read_json, read_jsonl, setup_logging, write_json)\n    22\t\n    23\tOFF_T10 = (\"bfs\", \"dfs\", \"label_propagation\")\n    24\t\n    25\t\n    26\tdef load_gen(unit: str) -> dict[str, dict[str, Any]]:\n    27\t    samples = {r[\"sample_id\"]: r for r in read_jsonl(DATA / f\"samples_{unit}.jsonl\")}\n    28\t    labels = {}\n    29\t    for r in read_jsonl(DATA / f\"labels_{unit}.jsonl\"):\n    30\t        labels.setdefault(r[\"sample_id\"], r)\n    31\t    out = {}\n    32\t    for sid, s in samples.items():\n    33\t        l = labels.get(sid)\n    34\t        if l is None:\n    35\t            continue\n    36\t        row = dict(s)\n    37\t        row.update({\"label\": l[\"label\"], \"passed\": bool(l.get(\"passed\")), \"valid\": bool(l.get(\"valid\")),\n    38\t                    \"labeller_source\": l.get(\"labeller_source\"), \"code\": l.get(\"code\")})\n    39\t        out[sid] = row\n    40\t    return out\n    41\t\n    42\t\n    43\tdef ok_label(r: dict[str, Any] | None, c: str) -> bool:\n    44\t    return bool(r is not None and r[\"label\"] == c and r[\"passed\"])\n    45\t\n    46\t\n    47\tdef gen_tables(unit: str, site: str, G: dict[str, dict[str, Any]]) -> dict[str, Any] | None:\n    48\t    cm = PRED / f\"commit2_{unit}_{site}.json\"\n    49\t    if not cm.exists():\n    50\t        return None\n    51\t    c2 = read_json(cm)\n    52\t    slot_map = c2[\"slot_map\"]\n    53\t    cells = c2[\"cells\"]\n    54\t    out: dict[str, Any] = {\"unit\": unit, \"site\": site, \"classes\": {}}\n    55\t    pooled = {\"DAS\": [], \"RAND\": [], \"BASE\": [], \"FULL\": [], \"pass_DAS\": [], \"pass_BASE\": []}\n    56\t    for c, slots in slot_map.items():\n    57\t        n_by_arm = {arm: n for (s_, arm, cc, n) in cells if s_ == site and cc == c}\n    58\t        tab: dict[str, Any] = {}\n    59\t        rows_by_arm: dict[str, list] = {}\n    60\t        for arm, n in n_by_arm.items():\n    61\t            rr = []\n    62\t            for s in range(n):\n    63\t                sm = slots[s]\n    64\t                sid = (f\"{unit}|{site}|BASE|{sm['base']}|{s}\" if arm == \"BASE\" else f\"{unit}|{site}|{arm}|{c}|{s}\")\n    65\t                rr.append(G.get(sid))\n    66\t            rows_by_arm[arm] = rr\n    67\t            got = [r for r in rr if r is not None]\n    68\t            tgt = c\n    69\t            if arm in (\"REV-DAS\", \"REV-FULL\", \"SRC\"):\n    70\t                tgt = got[0][\"class_src\"] if got and arm != \"SRC\" else (got[0][\"class_base\"] if got else c)\n    71\t            k = sum(ok_label(r, c) for r in got)\n    72\t            kdef = sum(ok_label(r, UNITS[unit][\"default\"] or \"\") for r in got) if UNITS[unit][\"default\"] else None\n    73\t            labs = {}\n    74\t            for r in got:\n    75\t                labs[r[\"label\"]] = labs.get(r[\"label\"], 0) + 1\n    76\t            tab[arm] = {\"n_planned\": n, \"n\": len(got), \"correct_target\": k, \"share\": k / len(got) if got else None,\n    77\t                        \"wilson95\": ST.wilson(k, len(got)), \"attempted_target\": sum(r[\"label\"] == c for r in got),\n    78\t                        \"pass_rate\": float(np.mean([r[\"passed\"] for r in got])) if got else None,\n    79\t                        \"other_share\": float(np.mean([r[\"label\"] == \"other\" for r in got])) if got else None,\n    80\t                        \"labels\": labs, \"correct_default\": kdef,\n    81\t                        \"invalid\": sum(r[\"label\"] == \"invalid\" for r in got)}\n    82\t        def paired(a: str, b: str) -> dict[str, Any] | None:\n    83\t            if a not in rows_by_arm or b not in rows_by_arm:\n    84\t                return None\n    85\t            n = min(len(rows_by_arm[a]), len(rows_by_arm[b]))\n    86\t            xa = [ok_label(rows_by_arm[a][i], c) for i in range(n) if rows_by_arm[a][i] and rows_by_arm[b][i]]\n    87\t            xb = [ok_label(rows_by_arm[b][i], c) for i in range(n) if rows_by_arm[a][i] and rows_by_arm[b][i]]\n    88\t            return ST.mcnemar(xa, xb)\n    89\t        kb = tab.get(\"BASE\", {}).get(\"correct_target\", 0)\n    90\t        kf = tab.get(\"FULL\", {}).get(\"correct_target\", 0)\n    91\t        kd = tab.get(\"DAS\", {}).get(\"correct_target\", 0)\n    92\t        rec = (kd - kb) / (kf - kb) if (kf - kb) else None\n    93\t        pr = (tab[\"DAS\"][\"pass_rate\"] / tab[\"BASE\"][\"pass_rate\"]) if (tab.get(\"DAS\", {}).get(\"pass_rate\") and\n    94\t                                                                     tab.get(\"BASE\", {}).get(\"pass_rate\")) else None\n    95\t        dflt = UNITS[unit][\"default\"]\n    96\t        rev = None\n    97\t        if all(x in tab for x in (\"REV-DAS\", \"REV-FULL\", \"SRC\")):\n    98\t            # restored programs of the twin's class (T10: the default); GRID: the base class of the twin\n    99\t            def k_restore(arm: str) -> int:\n   100\t                got = [r for r in rows_by_arm[arm] if r]\n   101\t                tw_cls = got[0][\"class_src\"] if got and arm != \"SRC\" else None\n   102\t                if tw_cls is None:\n   103\t                    tw_cls = (rows_by_arm[\"REV-DAS\"][0] or {}).get(\"class_src\") if rows_by_arm.get(\"REV-DAS\") else None\n   104\t                return sum(ok_label(r, tw_cls or (dflt or \"\")) for r in got)\n   105\t            ks, krd, krf = k_restore(\"SRC\"), k_restore(\"REV-DAS\"), k_restore(\"REV-FULL\")\n   106\t            rev = {\"restored_SRC\": ks, \"restored_REV_DAS\": krd, \"restored_REV_FULL\": krf,\n   107\t                   \"gen_c4\": (krd - ks) / (krf - ks) if (krf - ks) else None}\n   108\t        out[\"classes\"][c] = {\"arms\": tab, \"gen_recovery\": rec, \"pass_ratio_DAS_vs_BASE\": pr,\n   109\t                             \"mcnemar_DAS_vs_RAND\": paired(\"DAS\", \"RAND\"), \"mcnemar_DAS_vs_BASE\": paired(\"DAS\", \"BASE\"),\n   110\t                             \"mcnemar_FULL_vs_BASE\": paired(\"FULL\", \"BASE\"), \"reverse\": rev,\n   111\t                             \"extra_ranks\": {arm: tab[arm] for arm in tab if arm.startswith(\"DAS_k\")}}\n   112\t        for arm in (\"DAS\", \"RAND\", \"BASE\", \"FULL\"):\n   113\t            if arm in rows_by_arm:\n   114\t                pooled[arm] += [ok_label(r, c) if r else None for r in rows_by_arm[arm]]\n   115\t        if \"DAS\" in rows_by_arm:\n   116\t            pooled[\"pass_DAS\"] += [r[\"passed\"] for r in rows_by_arm[\"DAS\"] if r]\n   117\t            pooled[\"pass_BASE\"] += [r[\"passed\"] for r in rows_by_arm.get(\"BASE\", []) if r]\n   118\t    # pooled over off-default classes (CRN-paired by slot within class)\n   119\t    def cnt(x: list) -> int:\n   120\t        return sum(1 for v in x if v)\n   121\t    kd, kb, kf = cnt(pooled[\"DAS\"]), cnt(pooled[\"BASE\"]), cnt(pooled[\"FULL\"])\n   122\t    pairs_dr = [(a, b) for a, b in zip(pooled[\"DAS\"], pooled[\"RAND\"]) if a is not None and b is not None]\n   123\t    out[\"pooled\"] = {\"DAS\": kd, \"BASE\": kb, \"FULL\": kf, \"RAND\": cnt(pooled[\"RAND\"]),\n   124\t                     \"n_DAS\": len([v for v in pooled[\"DAS\"] if v is not None]),\n   125\t                     \"gen_recovery\": (kd - kb) / (kf - kb) if (kf - kb) else None,\n   126\t                     \"pass_ratio\": (np.mean(pooled[\"pass_DAS\"]) / np.mean(pooled[\"pass_BASE\"]))\n   127\t                     if pooled[\"pass_DAS\"] and pooled[\"pass_BASE\"] and np.mean(pooled[\"pass_BASE\"]) else None,\n   128\t                     \"mcnemar_DAS_vs_RAND\": ST.mcnemar([a for a, _ in pairs_dr], [b for _, b in pairs_dr])}\n   129\t    return out\n   130\t\n   131\t\n   132\tdef verdict(tf: dict[str, Any] | None, gen: dict[str, Any] | None, rinit: dict[str, Any] | None) -> dict[str, Any]:\n   133\t    if tf is None:\n   134\t        return {\"verdict\": \"NOT RUN\"}\n   135\t    main = tf[\"main\"]\n   136\t    v_tf = bool(main[\"recovery\"] is not None and main[\"recovery\"] >= THRESH[\"V0_tf\"] and main[\"ci95\"][0] is not None\n   137\t                and main[\"ci95\"][0] > THRESH[\"V0_tf_lo\"])\n   138\t    g = (gen or {}).get(\"pooled\", {})\n   139\t    v_gen = bool(g.get(\"gen_recovery\") is not None and g[\"gen_recovery\"] >= THRESH[\"V0_gen\"])\n   140\t    v_pass = bool(g.get(\"pass_ratio\") is not None and g[\"pass_ratio\"] >= THRESH[\"V0_pass_ratio\"])\n   141\t    mc = g.get(\"mcnemar_DAS_vs_RAND\") or {}\n   142\t    v_mc = bool(mc.get(\"p_one_sided_a_gt_b\", 1) < THRESH[\"V0_mcnemar_p\"] and mc.get(\"a_only\", 0) > mc.get(\"b_only\", 0))\n   143\t    V0 = v_tf and v_gen and v_pass and v_mc\n   144\t    c = {\"c1\": all(v[\"pass\"] for v in tf[\"c1\"].values()) if isinstance(tf[\"c1\"], dict) else False,\n   145\t         \"c2\": bool(tf[\"c2\"].get(\"pass\")),\n   146\t         \"c3\": bool(rinit.get(\"pass\")) if rinit else None,\n   147\t         \"c4\": bool(tf[\"c4\"].get(\"pass\")),\n   148\t         \"c5\": bool(tf[\"c5\"].get(\"pass\")),\n   149\t         \"c6\": bool(tf[\"c6\"][\"twins\"][\"pass\"]) if \"twins\" in tf[\"c6\"] else False,\n   150\t         \"c7\": bool(tf[\"c7\"].get(\"pass\"))}\n   151\t    c1_k = tf[\"c1\"].get(str(tf[\"k_star\"])) or tf[\"c1\"].get(tf[\"k_star\"])\n   152\t    failed = [k for k, v in c.items() if v is False]\n   153\t    untested = [k for k, v in c.items() if v is None]\n   154\t    if not V0:\n   155\t        lab = \"NO HANDLE\"\n   156\t    elif not failed and not untested:\n   157\t        lab = \"CERTIFIED VARIABLE\"\n   158\t    elif c[\"c1\"]:\n   159\t        lab = \"SUFFICIENT HANDLE\"\n   160\t    else:\n   161\t        lab = \"NO HANDLE (c1 fails)\"\n   162\t    kinds = {\"c2\": \"map-class capacity\", \"c3\": \"map-class capacity\", \"c4\": \"dormant/off-manifold\",\n   163\t             \"c5\": \"dormant/off-manifold\", \"c6\": \"dormant/off-manifold\", \"c7\": \"unstable across seeds\",\n   164\t             \"c1\": \"random subspaces suffice\"}\n   165\t    by_class = {}\n   166\t    for cname, cv in ((gen or {}).get(\"classes\") or {}).items():\n   167\t        mcc = cv.get(\"mcnemar_DAS_vs_RAND\") or {}\n   168\t        by_class[cname] = {\"gen_recovery\": cv.get(\"gen_recovery\"), \"pass_ratio\": cv.get(\"pass_ratio_DAS_vs_BASE\"),\n   169\t                           \"mcnemar_p_das_gt_rand\": mcc.get(\"p_one_sided_a_gt_b\"),\n   170\t                           \"V0_class\": bool(v_tf and cv.get(\"gen_recovery\") is not None and cv[\"gen_recovery\"] >= 0.5\n   171\t                                            and (cv.get(\"pass_ratio_DAS_vs_BASE\") or 0) >= 0.8\n   172\t                                            and (mcc.get(\"p_one_sided_a_gt_b\") or 1) < 0.05),\n   173\t                           \"full_minus_base_correct\": ((cv[\"arms\"].get(\"FULL\") or {}).get(\"correct_target\", 0) -\n   174\t                                                       (cv[\"arms\"].get(\"BASE\") or {}).get(\"correct_target\", 0))}\n   175\t    return {\"verdict\": lab, \"V0_by_class\": by_class,\n   176\t            \"note_generation_recovery\": \"generation recovery divides by FULL - BASE correct counts; when the full-state \"\n   177\t                                        \"exchange moves <= 2 slots the ratio is not a fraction of a ceiling\",\n   178\t            \"V0\": V0, \"V0_parts\": {\"tf_recovery\": v_tf, \"gen_recovery\": v_gen, \"pass_ratio\": v_pass,\n   179\t                                                   \"mcnemar_das_gt_rand\": v_mc},\n   180\t            \"controls\": c, \"failed_controls\": {k: kinds[k] for k in failed}, \"untested_controls\": untested,\n   181\t            \"off_manifold_flag\": bool(tf.get(\"off_manifold_flag\")), \"tf_recovery\": main[\"recovery\"],\n   182\t            \"tf_ci95\": main[\"ci95\"], \"gen_recovery\": g.get(\"gen_recovery\"), \"pass_ratio\": g.get(\"pass_ratio\"),\n   183\t            \"mcnemar\": mc, \"c1_at_kstar\": c1_k}\n   184\t\n   185\t\n   186\tdef mediation_outcomes(G: dict[str, dict[str, Any]]) -> dict[str, Any] | None:\n   187\t    p = RESULTS / \"mediation_T10.json\"\n   188\t    if not p.exists():\n   189\t        return None\n   190\t    med = read_json(p)\n   191\t    top = med.get(\"top10_escaping\", [])\n   192\t    esc = lambda r: bool(r and r[\"passed\"] and r[\"label\"] in OFF_T10)  # noqa: E731\n   193\t    arms = {}\n   194\t    for arm in (\"PUSH\", \"TASK\", \"RAND\"):\n   195\t        arms[arm] = {(sd, s): G.get(f\"T10|med|{arm}|{sd}|{s}\") for sd in top for s in range(30)}\n   196\t    out: dict[str, Any] = {}\n   197\t    push = arms[\"PUSH\"]\n   198\t    e_push = sum(esc(r) for r in push.values())\n   199\t    out[\"escapes_PUSH\"] = e_push\n   200\t    out[\"n_PUSH\"] = sum(r is not None for r in push.values())\n   201\t    for arm in (\"TASK\", \"RAND\"):\n   202\t        keys = [k for k in push if push[k] and arms[arm].get(k)]\n   203\t        a = [esc(push[k]) for k in keys]\n   204\t        b = [esc(arms[arm][k]) for k in keys]\n   205\t        ea, eb = sum(a), sum(b)\n   206\t        out[f\"clamp_{arm}\"] = {\"n_pairs\": len(keys), \"escapes_push\": ea, \"escapes_clamp\": eb,\n   207\t                               \"removal\": 1 - eb / ea if ea else None, \"mcnemar_push_vs_clamp\": ST.mcnemar(a, b),\n   208\t                               \"pass_rate_clamp\": float(np.mean([arms[arm][k][\"passed\"] for k in keys])) if keys else None}\n   209\t    dec_keys = [(sd, s) for sd in top for s in range(10) if G.get(f\"T10|med|DEC|{sd}|{s}\")]\n   210\t    if dec_keys:\n   211\t        a = [esc(push.get(k)) for k in dec_keys]\n   212\t        b = [esc(G.get(f\"T10|med|DEC|{k[0]}|{k[1]}\")) for k in dec_keys]\n   213\t        out[\"clamp_DEC\"] = {\"n_reached\": len(dec_keys), \"reach_rate\": med.get(\"dec_clamp_reach_rate\"),\n   214\t                            \"escapes_push_reached\": sum(a), \"escapes_clamp\": sum(b),\n   215\t                            \"removal\": 1 - sum(b) / sum(a) if sum(a) else None, \"mcnemar\": ST.mcnemar(a, b)}\n   216\t    else:\n   217\t        out[\"clamp_DEC\"] = {\"n_reached\": 0, \"reach_rate\": med.get(\"dec_clamp_reach_rate\")}\n   218\t    t = out.get(\"clamp_TASK\", {})\n   219\t    r = out.get(\"clamp_RAND\", {})\n   220\t    out[\"not_estimable\"] = bool(e_push < 8)\n   221\t    out[\"clamp_pass\"] = bool(not out[\"not_estimable\"] and (t.get(\"removal\") or 0) >= 0.5 and\n   222\t                             (r.get(\"removal\") if r.get(\"removal\") is not None else 1) <= 0.10)\n   223\t    pro = med.get(\"prospective_pi\", {})\n   224\t    if pro:\n   225\t        xs, ys = [], []\n   226\t        for sd, v in pro.items():\n   227\t            rows = [G.get(f\"T10|pro|PUSH|{sd}|{s}\") for s in range(10)]\n   228\t            rows = [x for x in rows if x]\n   229\t            if rows:\n   230\t                xs.append(v[\"pi\"])\n   231\t                ys.append(float(np.mean([esc(x) for x in rows])))\n   232\t        out[\"prospective\"] = {\"n_directions\": len(xs), \"spearman\": ST.spearman_perm(np.array(xs), np.array(ys)),\n   233\t                              \"mean_escape\": float(np.mean(ys)) if ys else None}\n   234\t    out[\"retrospective\"] = {k: med.get(k) for k in med if k.startswith(\"spearman\") or k.startswith(\"partial\")\n   235\t                            or k.startswith(\"placebo\")}\n   236\t    return out\n   237\t\n   238\t\n   239\tdef main() -> None:\n   240\t    setup_logging(\"analysis8\")\n   241\t    res: dict[str, Any] = {}\n   242\t    gens = {}\n   243\t    for unit in (\"T10\", \"GRID\"):\n   244\t        G = load_gen(unit)\n   245\t        gens[unit] = G\n   246\t        for site in (\"dec\", \"band\"):\n   247\t            gt = gen_tables(unit, site, G)\n   248\t            if gt:\n   249\t                res[f\"gen_{unit}_{site}\"] = gt\n   250\t    tf = {(\"T10\", \"dec\"): RESULTS / \"dec_T10.json\", (\"T10\", \"band\"): RESULTS / \"band_T10.json\",\n   251\t          (\"GRID\", \"dec\"): RESULTS / \"dec_GRID.json\", (\"T10\", \"dec_L24_posthoc\"): RESULTS / \"dec_T10_L24.json\"}\n   252\t    ri = {(\"T10\", \"dec\"): RESULTS / \"rinit_T10.json\", (\"T10\", \"band\"): RESULTS / \"rinit_T10_band.json\",\n   253\t          (\"GRID\", \"dec\"): RESULTS / \"rinit_GRID.json\", (\"T10\", \"dec_L24_posthoc\"): RESULTS / \"rinit_T10_L24.json\"}\n   254\t    verdicts = {}\n   255\t    for (unit, site), p in tf.items():\n   256\t        t = read_json(p) if p.exists() else None\n   257\t        r = read_json(ri[(unit, site)]) if ri[(unit, site)].exists() else None\n   258\t        v = verdict(t, res.get(f\"gen_{unit}_{site}\"), r)\n   259\t        if site.endswith(\"posthoc\") and t is not None:\n   260\t            v[\"verdict\"] = \"POST HOC, TF-only (no generation): controls \" + (\n   261\t                \"all pass\" if not v[\"failed_controls\"] and not v[\"untested_controls\"] else\n   262\t                f\"failed {sorted(v['failed_controls'])}, untested {v['untested_controls']}\")\n   263\t        verdicts[f\"{unit}-{site}\"] = v\n   264\t    res[\"verdicts\"] = verdicts\n   265\t    # ---- K2 and p_K2 (intersection-union over the two decision sites)\n   266\t    pk = {}\n   267\t    for unit in (\"T10\", \"GRID\"):\n   268\t        d = RESULTS / f\"dec_{unit}.json\"\n   269\t        if not d.exists():\n   270\t            continue\n   271\t        dd = read_json(d)\n   272\t        p_c2 = []\n   273\t        post = RESULTS / f\"post_{unit}.json\"\n   274\t        if post.exists():\n   275\t            p_c2 = [v[\"test_true_gt_perm\"][\"p_cluster_boot\"] for v in read_json(post)[\"perm\"].values()]\n   276\t        else:\n   277\t            p_c2 = [v[\"test_true_gt_perm\"][\"p_cluster_boot\"] for v in dd[\"c2\"].values()\n   278\t                    if isinstance(v, dict) and \"test_true_gt_perm\" in v]\n   279\t        r = RESULTS / f\"rinit_{unit}.json\"\n   280\t        p_c3 = read_json(r)[\"test_trained_gt_rinit\"][\"p_cluster_boot\"] if r.exists() else None\n   281\t        pk[unit] = {\"p_c2_max\": max(p_c2) if p_c2 else None, \"p_c3\": p_c3,\n   282\t                    \"max\": max([x for x in [max(p_c2) if p_c2 else None, p_c3] if x is not None], default=None)}\n   283\t    vt, vg = verdicts.get(\"T10-dec\", {}), verdicts.get(\"GRID-dec\", {})\n   284\t    confirmed = vt.get(\"verdict\") == \"CERTIFIED VARIABLE\" and vg.get(\"verdict\") == \"CERTIFIED VARIABLE\"\n   285\t    disc = any(v.get(\"controls\", {}).get(c) is False for v in (vt, vg) for c in (\"c2\", \"c3\"))\n   286\t    res[\"K2\"] = {\"confirmed\": confirmed, \"disconfirmed\": disc,\n   287\t                 \"status\": \"CONFIRMED\" if confirmed else (\"DISCONFIRMED\" if disc else \"NOT CONFIRMED (inconclusive)\"),\n   288\t                 \"p_by_site\": pk,\n   289\t                 \"p_K2\": max([v[\"max\"] for v in pk.values() if v[\"max\"] is not None], default=None),\n   290\t                 \"rule\": \"confirmed iff T10-dec and GRID-dec both CERTIFIED; disconfirmed iff a decision site fails \"\n   291\t                         \"c2 or c3 in either family; p_K2 = max over sites of max(p_c2, p_c3)\"}\n   292\t    med = mediation_outcomes(gens[\"T10\"])\n   293\t    if med:\n   294\t        res[\"mediation\"] = med\n   295\t    write_json(RESULTS / \"analysis.json\", res)\n   296\t    logger.info(json.dumps({k: v.get(\"verdict\") for k, v in verdicts.items()}))\n   297\t    logger.info(f\"K2: {res['K2']['status']} p_K2 {res['K2']['p_K2']}\")\n   298\t\n   299\t\n   300\tif __name__ == \"__main__\":\n   301\t    main()", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [35] TOOL CALL — Bash · 2026-10-26 13:39:53 UTC

```
Read outputs8, digest8, novelty8 source:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40; cat -n $A/src/outputs8.py; echo "=========== digest8 ==========="; cat -n $A/src/digest8.py; echo "=========== novelty8 ==========="; cat -n $A/src/novelty8.py
```

### [36] TOOL RESULT — Bash · 2026-10-26 13:39:53 UTC

```
{"stdout": "     1\t#!/usr/bin/env python3\n     2\t\"\"\"method_out.json (exp_gen_sol_out schema): one example per (unit, site, target class, slot) of the generation\n     3\tcells (predict_<arm> = 'label|pass' or 'label|fail'), one per mediation clamp slot, and one per held-out teacher-forced\n     4\tpair (predict_<fit> = Delta in nats). Metadata: verdicts, K2, controls, recovery tables, scan profiles, mediation,\n     5\tdeviations, timing, costs, commit chain.\n     6\t\n... [truncated, 24981 chars total]
```

### [37] ASSISTANT · 2026-10-26 13:39:59 UTC

```
Next: `figures8.py`, which draws the activation-geometry plots, and `audit/rederive.py`.
```

### [38] TOOL CALL — Bash · 2026-10-26 13:39:59 UTC

```
Read figures8.py source:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40; cat -n $A/src/figures8.py
```

### [39] TOOL RESULT — Bash · 2026-10-26 13:39:59 UTC

```
{"stdout": "     1\t#!/usr/bin/env python3\n     2\t\"\"\"S11 geometry + figures (actual activation coordinates; PDF + PNG in figures/).\n     3\t\n     4\tF1 scan profile per unit: rank-1 CV recovery and full-state mean Delta by block (L* marked).\n     5\tF2 held-out TF recovery by rank (seed 0) against the random-subspace median / 95th percentile (c1).\n     6\tF3 decision-site geometry per unit: every prompt's coordinates in the fitted R_8 subspace at (L*, d) (centred on the\n     7\t   twin mean), embedded in 2-D by metric MDS (Kruskal stress-1 printed) and Isomap (k = 8); class centroids sized by\n     8\t   implemented counts (BASE + SRC generation rows); companion PCA of the raw block-L* states. Title says 'causal\n     9\t   manifold' only if the site is CERTIFIED, else 'handle coordinates (not certified)'.\n    10\tF4 generation: correct target programs by arm and class (Wilson 95% intervals).\n    11\tF5 mediation: committed predictor pi_u against the escape share (retrospective 40 + prospective 24).\n    12\t\n    13\tUsage: python src/figures8.py\n    14\t\"\"\"\n    15\t\n    16\tfrom __future__ import annotations\n    17\t\n    18\timport sys\n    19\tfrom pathlib import Path\n    20\tfrom typing import Any\n    21\t\n    22\tsys.path.insert(0, str(Path(__file__).resolve().parent))\n    23\t\n    24\timport matplotlib\n    25\t\n    26\tmatplotlib.use(\"Agg\")\n    27\timport matplotlib.pyplot as plt\n    28\timport numpy as np\n    29\timport torch\n    30\tfrom loguru import logger\n    31\tfrom sklearn.decomposition import PCA\n    32\tfrom sklearn.manifold import MDS, Isomap\n    33\t\n    34\tfrom cfg8 import CACHE, FIGS, MAPS, PROMPTS_DIR, RESULTS, read_json, read_jsonl, setup_logging, write_json\n    35\t\n    36\tplt.rcParams.update({\"pdf.fonttype\": 42, \"ps.fonttype\": 42, \"font.size\": 9, \"axes.spines.top\": False,\n    37\t                     \"axes.spines.right\": False})\n    38\tCOL = {\"bfs\": \"#1f77b4\", \"dfs\": \"#d62728\", \"union_find\": \"#2ca02c\", \"astar_gbfs\": \"#9467bd\", \"iddfs\": \"#8c564b\",\n    39\t       \"twin\": \"#7f7f7f\", \"padtwin\": \"#bcbd22\", \"ban\": \"#ff7f0e\", \"top5\": \"#e377c2\", \"seed\": \"#17becf\",\n    40\t       \"instr\": \"#000000\", \"p0\": \"#aaaaaa\"}\n    41\t\n    42\t\n    43\tdef save(fig: Any, name: str) -> None:\n    44\t    fig.savefig(FIGS / f\"{name}.pdf\", bbox_inches=\"tight\")\n    45\t    fig.savefig(FIGS / f\"{name}.png\", dpi=180, bbox_inches=\"tight\")\n    46\t    plt.close(fig)\n    47\t\n    48\t\n    49\tdef group_of(r: dict[str, Any]) -> str:\n    50\t    k = r[\"kind\"]\n    51\t    if k == \"forced\":\n    52\t        return r[\"Y\"]\n    53\t    if k in (\"seed_rand1\", \"seed_rand2\"):\n    54\t        return \"seed\"\n    55\t    if k in (\"instr_new\", \"instr_novel\"):\n    56\t        return \"instr\"\n    57\t    return k\n    58\t\n    59\t\n    60\tdef f1_scan() -> None:\n    61\t    fig, axes = plt.subplots(1, 2, figsize=(14, 4.0))\n    62\t    fig.subplots_adjust(wspace=0.45)\n    63\t    for ax, unit in zip(axes, (\"T10\", \"GRID\")):\n    64\t        p = RESULTS / f\"scan_{unit}.json\"\n    65\t        if not p.exists():\n    66\t            ax.set_title(f\"{unit}: scan not run\")\n    67\t            continue\n    68\t        sc = {int(k): v for k, v in read_json(p).items()}\n    69\t        L = sorted(sc)\n    70\t        rec = [float(sc[l][\"cv_median_recovery\"]) if sc[l][\"cv_median_recovery\"] is not None else np.nan for l in L]\n    71\t        full = [sc[l][\"full_state_mean_delta_held96\"] for l in L]\n    72\t        ax.plot(L, rec, \"o-\", color=\"#d62728\", label=\"rank-1 DAS CV recovery\")\n    73\t        ax.axhline(1.0, color=\"#d62728\", lw=0.6, ls=\":\")\n    74\t        ax.axhline(1.5, color=\"#d62728\", lw=0.6, ls=\"--\")\n    75\t        ax.set_xlabel(\"block L (edit of the block output at the decision position d)\")\n    76\t        ax.set_ylabel(\"rank-1 DAS recovery (DAS / full-state)\")\n    77\t        ax2 = ax.twinx()\n    78\t        ax2.plot(L, full, \"s--\", color=\"#555555\", label=\"full-state mean Delta (nats)\")\n    79\t        ax2.set_ylabel(\"full-state mean Delta (nats)\")\n    80\t        d = RESULTS / f\"dec_{unit}.json\"\n    81\t        if d.exists():\n    82\t            Ls = read_json(d)[\"L_star\"]\n    83\t            ax.axvline(Ls, color=\"k\", lw=0.8)\n    84\t            ax.text(Ls, ax.get_ylim()[1] * 0.95, f\" L*={Ls}\", fontsize=8)\n    85\t        ax.set_title(f\"{unit} ({'Qwen3-8B' if unit == 'T10' else 'gemma-3-4b-it'}): block scan; dotted = 1, \"\n    86\t                     f\"dashed = OFF-MANIFOLD 1.5\", fontsize=9)\n    87\t        h1, l1 = ax.get_legend_handles_labels()\n    88\t        h2, l2 = ax2.get_legend_handles_labels()\n    89\t        ax.legend(h1 + h2, l1 + l2, fontsize=7, loc=\"upper left\")\n    90\t    save(fig, \"F1_scan_profile\")\n    91\t\n    92\t\n    93\tdef f2_rank() -> None:\n    94\t    sites = [(\"T10\", \"dec\", RESULTS / \"dec_T10.json\"), (\"T10\", \"band\", RESULTS / \"band_T10.json\"),\n    95\t             (\"GRID\", \"dec\", RESULTS / \"dec_GRID.json\"), (\"T10\", \"dec L24 (post hoc)\", RESULTS / \"dec_T10_L24.json\")]\n    96\t    sites = [s for s in sites if s[2].exists()]\n    97\t    if not sites:\n    98\t        return\n    99\t    fig, axes = plt.subplots(1, len(sites), figsize=(3.6 * len(sites), 3.2), squeeze=False)\n   100\t    for ax, (unit, site, p) in zip(axes[0], sites):\n   101\t        d = read_json(p)\n   102\t        ks = [1, 2, 4, 8]\n   103\t        rr = [d[\"recovery_by_rank\"][str(k)][\"recovery\"] for k in ks]\n   104\t        lo = [d[\"recovery_by_rank\"][str(k)][\"ci95\"][0] for k in ks]\n   105\t        hi = [d[\"recovery_by_rank\"][str(k)][\"ci95\"][1] for k in ks]\n   106\t        ax.errorbar(ks, rr, yerr=[np.array(rr) - np.array(lo), np.array(hi) - np.array(rr)], fmt=\"o-\",\n   107\t                    color=\"#d62728\", capsize=3, label=\"DAS (seed 0), held-out\")\n   108\t        med = [d[\"c1\"][str(k)][\"median\"] for k in ks]\n   109\t        p95 = [d[\"c1\"][str(k)][\"p95\"] for k in ks]\n   110\t        ax.plot(ks, med, \"x--\", color=\"#555555\", label=\"random subspaces: median\")\n   111\t        ax.plot(ks, p95, \"+:\", color=\"#555555\", label=\"random: 95th pct\")\n   112\t        ax.axhline(1.0, color=\"k\", lw=0.5)\n   113\t        ax.set_xscale(\"log\", base=2)\n   114\t        ax.set_xticks(ks)\n   115\t        ax.set_xticklabels(ks)\n   116\t        ax.set_xlabel(\"rank k\")\n   117\t        ax.set_ylabel(\"normalised recovery\")\n   118\t        ax.set_title(f\"{unit} {site}: k*={d['k_star']}\", fontsize=9)\n   119\t        ax.legend(fontsize=6)\n   120\t    save(fig, \"F2_recovery_by_rank\")\n   121\t\n   122\t\n   123\tdef implemented_counts(unit: str) -> dict[str, int]:\n   124\t    labs = read_jsonl(Path(RESULTS.parent / \"data\" / f\"labels_{unit}.jsonl\"))\n   125\t    cnt: dict[str, int] = {}\n   126\t    for r in labs:\n   127\t        if r.get(\"arm\") in (\"BASE\", \"SRC\") and r.get(\"passed\"):\n   128\t            cnt[r[\"label\"]] = cnt.get(r[\"label\"], 0) + 1\n   129\t    return cnt\n   130\t\n   131\t\n   132\tdef f3_geometry(unit: str, verdict: str | None) -> dict[str, Any] | None:\n   133\t    d = RESULTS / f\"dec_{unit}.json\"\n   134\t    st = CACHE / f\"states_{unit}_dec_trained.pt\"\n   135\t    if not d.exists() or not st.exists():\n   136\t        return None\n   137\t    dd = read_json(d)\n   138\t    L = dd[\"L_star\"]\n   139\t    R = torch.load(MAPS / f\"{unit}_dec_L{L}_seed0.pt\").float()           # [D, 8]\n   140\t    H = torch.load(st)\n   141\t    P = {r[\"key\"]: r for r in read_jsonl(PROMPTS_DIR / (\"t10_prompts.jsonl\" if unit == \"T10\" else \"grid_prompts.jsonl\"))}\n   142\t    keys = [k for k in P if k in H]\n   143\t    X = torch.stack([H[k][L].float() for k in keys])                     # [n, D]\n   144\t    tw = [i for i, k in enumerate(keys) if P[k][\"kind\"] == \"twin\"]\n   145\t    mu = X[tw].mean(0)\n   146\t    Z = ((X - mu) @ R).numpy()                                           # [n, 8] handle coordinates\n   147\t    groups = [group_of(P[k]) for k in keys]\n   148\t    D = np.linalg.norm(Z[:, None] - Z[None], axis=-1)\n   149\t    mds = MDS(n_components=2, dissimilarity=\"precomputed\", random_state=0, n_init=4, normalized_stress=\"auto\")\n   150\t    E = mds.fit_transform(D)\n   151\t    dE = np.linalg.norm(E[:, None] - E[None], axis=-1)\n   152\t    stress1 = float(np.sqrt(((D - dE) ** 2).sum() / (D ** 2).sum()))\n   153\t    iso = Isomap(n_neighbors=8, n_components=2)\n   154\t    Ei = iso.fit_transform(Z)\n   155\t    geo = iso.dist_matrix_\n   156\t    cnt = implemented_counts(unit)\n   157\t    certified = verdict == \"CERTIFIED VARIABLE\"\n   158\t    title = \"causal manifold\" if certified else \"handle coordinates (not certified)\"\n   159\t    ug = sorted(set(groups))\n   160\t    cents = {g: E[[i for i, x in enumerate(groups) if x == g]].mean(0) for g in ug}\n   161\t    cls_names = [g for g in ug if g in (\"bfs\", \"dfs\", \"union_find\", \"astar_gbfs\", \"iddfs\")]\n   162\t    gd = {}\n   163\t    for a in ug:\n   164\t        for b in ug:\n   165\t            if a < b:\n   166\t                ia = [i for i, x in enumerate(groups) if x == a]\n   167\t                ib = [i for i, x in enumerate(groups) if x == b]\n   168\t                gd[f\"{a}|{b}\"] = float(np.mean(geo[np.ix_(ia, ib)]))\n   169\t    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))\n   170\t    for ax, emb, name in ((axes[0], E, f\"metric MDS of R_8 coordinates (stress-1 {stress1:.2f})\"),\n   171\t                          (axes[1], Ei, \"Isomap (k = 8) of R_8 coordinates\")):\n   172\t        for g in ug:\n   173\t            ix = [i for i, x in enumerate(groups) if x == g]\n   174\t            ax.scatter(emb[ix, 0], emb[ix, 1], s=10, alpha=0.6, color=COL.get(g, \"#333333\"), label=f\"{g} (n={len(ix)})\")\n   175\t        for g in cls_names:\n   176\t            ix = [i for i, x in enumerate(groups) if x == g]\n   177\t            c = emb[ix].mean(0)\n   178\t            ax.scatter([c[0]], [c[1]], s=40 + 6 * cnt.get(g, 0), marker=\"*\", color=COL.get(g), edgecolor=\"k\",\n   179\t                       zorder=5)\n   180\t            ax.annotate(f\"{g}: {cnt.get(g, 0)} impl.\", c, fontsize=7)\n   181\t        for g in (\"ban\", \"top5\", \"seed\", \"instr\"):\n   182\t            ix = [i for i, x in enumerate(groups) if x == g]\n   183\t            if ix:\n   184\t                c = emb[ix].mean(0)\n   185\t                ax.annotate(g, c, fontsize=7, color=COL.get(g))\n   186\t        ax.set_title(name, fontsize=9)\n   187\t        ax.set_xlabel(\"embedding axis 1 (a.u.)\")\n   188\t        ax.set_ylabel(\"embedding axis 2 (a.u.)\")\n   189\t    axes[0].legend(fontsize=6, loc=\"best\")\n   190\t    pca = PCA(n_components=2).fit(X.numpy())\n   191\t    Ep = pca.transform(X.numpy())\n   192\t    for g in ug:\n   193\t        ix = [i for i, x in enumerate(groups) if x == g]\n   194\t        axes[2].scatter(Ep[ix, 0], Ep[ix, 1], s=10, alpha=0.6, color=COL.get(g, \"#333333\"), label=g)\n   195\t    axes[2].set_title(f\"PCA of raw block-{L} states at d (var {pca.explained_variance_ratio_.sum():.2f})\", fontsize=9)\n   196\t    axes[2].set_xlabel(\"PC1 of raw residual states\")\n   197\t    axes[2].set_ylabel(\"PC2 of raw residual states\")\n   198\t    fig.suptitle(f\"{unit} decision site, block {L}: {title}. Stars = class centroids, size ~ implemented \"\n   199\t                 f\"(passing BASE + SRC programs)\", fontsize=10)\n   200\t    save(fig, f\"F3_geometry_{unit}\")\n   201\t    # handle coordinate 1 against class: a 1-D view of the actual coordinates\n   202\t    fig, ax = plt.subplots(figsize=(6, 3))\n   203\t    for j, g in enumerate(ug):\n   204\t        ix = [i for i, x in enumerate(groups) if x == g]\n   205\t        ax.scatter(Z[ix, 0], np.full(len(ix), j) + np.random.default_rng(j).uniform(-0.2, 0.2, len(ix)), s=8,\n   206\t                   color=COL.get(g, \"#333333\"))\n   207\t    ax.set_yticks(range(len(ug)))\n   208\t    ax.set_yticklabels(ug, fontsize=7)\n   209\t    ax.set_xlabel(f\"coordinate on R_1 at block {L} (projection of h - mean(twins); activation units)\")\n   210\t    ax.set_title(f\"{unit}: first handle coordinate per prompt group ({title})\", fontsize=9)\n   211\t    save(fig, f\"F3b_handle_axis_{unit}\")\n   212\t    return {\"unit\": unit, \"L\": L, \"mds_stress1\": stress1, \"isomap_mean_geodesic_between_groups\": gd,\n   213\t            \"implemented_counts\": cnt, \"title\": title, \"n_prompts\": len(keys),\n   214\t            \"group_centroids_mds\": {g: cents[g].tolist() for g in ug}}\n   215\t\n   216\t\n   217\tdef f4_generation(an: dict[str, Any]) -> None:\n   218\t    items = [(k, v) for k, v in an.items() if k.startswith(\"gen_\")]\n   219\t    if not items:\n   220\t        return\n   221\t    fig, axes = plt.subplots(1, len(items), figsize=(5 * len(items), 3.6), squeeze=False)\n   222\t    for ax, (k, g) in zip(axes[0], items):\n   223\t        arms = [\"BASE\", \"FULL\", \"DAS\", \"RAND\", \"PERM\"]\n   224\t        x = np.arange(len(arms))\n   225\t        w = 0.8 / max(1, len(g[\"classes\"]))\n   226\t        for j, (c, v) in enumerate(g[\"classes\"].items()):\n   227\t            sh = [(v[\"arms\"].get(a) or {}).get(\"share\") or 0 for a in arms]\n   228\t            ci = [(v[\"arms\"].get(a) or {}).get(\"wilson95\") or [0, 0] for a in arms]\n   229\t            lo = [s - (c_[0] or 0) for s, c_ in zip(sh, ci)]\n   230\t            hi = [(c_[1] or 0) - s for s, c_ in zip(sh, ci)]\n   231\t            ax.bar(x + j * w, sh, w, yerr=[lo, hi], capsize=2, color=COL.get(c, \"#888\"), label=f\"target {c}\")\n   232\t        ax.set_xticks(x + w * (len(g[\"classes\"]) - 1) / 2)\n   233\t        ax.set_xticklabels(arms)\n   234\t        ax.set_ylabel(\"share of correct target-class programs\")\n   235\t        ax.set_title(k.replace(\"gen_\", \"\"), fontsize=9)\n   236\t        ax.legend(fontsize=7)\n   237\t    save(fig, \"F4_generation\")\n   238\t\n   239\t\n   240\tdef f5_mediation() -> None:\n   241\t    p = RESULTS / \"mediation_T10.json\"\n   242\t    if not p.exists():\n   243\t        return\n   244\t    m = read_json(p)\n   245\t    an = read_json(RESULTS / \"analysis.json\") if (RESULTS / \"analysis.json\").exists() else {}\n   246\t    fig, ax = plt.subplots(figsize=(5, 3.6))\n   247\t    xs = [v[\"pi\"] for v in m[\"directions\"].values() if v.get(\"escape_pooled\") is not None]\n   248\t    ys = [v[\"escape_pooled\"] for v in m[\"directions\"].values() if v.get(\"escape_pooled\") is not None]\n   249\t    ax.scatter(xs, ys, s=16, color=\"#d62728\", label=\"40 iteration-4 directions (retrospective)\")\n   250\t    rho = (m.get(\"spearman_escape_pooled\") or {}).get(\"rho\")\n   251\t    ax.set_xlabel(\"committed predictor pi_u (projection of the realised push on the band subspace)\")\n   252\t    ax.set_ylabel(\"escape share (correct off-default programs)\")\n   253\t    ax.set_title(f\"Mediation: Spearman rho = {rho:.2f}\" if rho is not None else \"Mediation\", fontsize=9)\n   254\t    ax.legend(fontsize=7)\n   255\t    save(fig, \"F5_mediation\")\n   256\t\n   257\t\n   258\tdef main() -> None:\n   259\t    setup_logging(\"figures8\")\n   260\t    FIGS.mkdir(exist_ok=True)\n   261\t    an = read_json(RESULTS / \"analysis.json\") if (RESULTS / \"analysis.json\").exists() else {}\n   262\t    f1_scan()\n   263\t    f2_rank()\n   264\t    geo = {}\n   265\t    for unit in (\"T10\", \"GRID\"):\n   266\t        try:\n   267\t            v = an.get(\"verdicts\", {}).get(f\"{unit}-dec\", {}).get(\"verdict\")\n   268\t            g = f3_geometry(unit, v)\n   269\t            if g:\n   270\t                geo[unit] = g\n   271\t        except (RuntimeError, ValueError, KeyError, FileNotFoundError) as e:\n   272\t            logger.error(f\"geometry {unit} failed: {e}\")\n   273\t    write_json(RESULTS / \"geometry.json\", geo)\n   274\t    f4_generation(an)\n   275\t    f5_mediation()\n   276\t    logger.info(f\"figures written: {sorted(p.name for p in FIGS.glob('*.png'))}\")\n   277\t\n   278\t\n   279\tif __name__ == \"__main__\":\n   280\t    main()", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [40] TOOL CALL — Bash · 2026-10-26 13:39:59 UTC

```
Read audit/rederive.py source:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40; cat -n $A/audit/rederive.py
```

### [41] TOOL RESULT — Bash · 2026-10-26 13:39:59 UTC

```
{"stdout": "     1\t#!/usr/bin/env python3\n     2\t\"\"\"Independent re-derivation (Python standard library only; shares no code with src/): recomputes the headline numbers\n     3\tfrom the raw rows and compares them with the reported ones; runs the placebos, which must fail.\n     4\t\n     5\t  TF   recovery at k* (seed 0) = mean(Delta_DAS) / mean(Delta_FULL) over held-out pairs with |Delta_FULL| >= 1\n     6\t       (data/tf_<unit>_<site>.jsonl) vs results/dec_<unit>.json / band_T10.json\n     7\t  GEN  correct-target counts per (site, arm, class) from data/samples_<unit>.jsonl + data/labels_<unit>.jsonl vs\n     8\t       results/analysis.json; generation recovery and pass ratio recomputed\n     9\t  PLACEBO-GEN  DAS and RAND outcomes swapped by a fair coin per slot: the DAS-RAND discordance must vanish (|a-b| small)\n    10\t  PLACEBO-MED  a randomly permuted mediation predictor: |Spearman rho| must be < 0.3\n    11\tUsage: python3 audit/rederive.py   (writes results/rederive.json)\n    12\t\"\"\"\n    13\t\n    14\timport json\n    15\timport math\n    16\timport random\n    17\tfrom pathlib import Path\n    18\t\n    19\tROOT = Path(__file__).resolve().parents[1]\n    20\tRES = ROOT / \"results\"\n    21\tDATA = ROOT / \"data\"\n    22\t\n    23\t\n    24\tdef jl(p):\n    25\t    out = []\n    26\t    if not p.exists():\n    27\t        return out\n    28\t    for line in p.read_text().splitlines():\n    29\t        line = line.strip()\n    30\t        if line:\n    31\t            out.append(json.loads(line))\n    32\t    return out\n    33\t\n    34\t\n    35\tdef jr(p):\n    36\t    return json.loads(p.read_text()) if p.exists() else None\n    37\t\n    38\t\n    39\tdef ranks(x):\n    40\t    order = sorted(range(len(x)), key=lambda i: x[i])\n    41\t    r = [0.0] * len(x)\n    42\t    i = 0\n    43\t    while i < len(order):\n    44\t        j = i\n    45\t        while j + 1 < len(order) and x[order[j + 1]] == x[order[i]]:\n    46\t            j += 1\n    47\t        for k in range(i, j + 1):\n    48\t            r[order[k]] = (i + j) / 2 + 1\n    49\t        i = j + 1\n    50\t    return r\n    51\t\n    52\t\n    53\tdef spearman(x, y):\n    54\t    rx, ry = ranks(x), ranks(y)\n    55\t    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)\n    56\t    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))\n    57\t    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))\n    58\t    return num / den if den else 0.0\n    59\t\n    60\t\n    61\tdef tf_check(unit, site, rep_path, rtag=\"\"):\n    62\t    rows = jl(DATA / f\"tf_{unit}_{site}{rtag}.jsonl\")\n    63\t    rep = jr(rep_path)\n    64\t    if not rows or rep is None:\n    65\t        return None\n    66\t    k = rep[\"k_star\"]\n    67\t    sel = [r for r in rows if r[\"fit\"] == \"seed0\" and r[\"rank_k\"] == k and abs(r[\"delta_full\"]) >= 1.0]\n    68\t    if not sel:\n    69\t        return None\n    70\t    rec = (sum(r[\"delta\"] for r in sel) / len(sel)) / (sum(r[\"delta_full\"] for r in sel) / len(sel))\n    71\t    return {\"rederived\": rec, \"reported\": rep[\"main\"][\"recovery\"], \"n\": len(sel),\n    72\t            \"match\": abs(rec - rep[\"main\"][\"recovery\"]) < 1e-6}\n    73\t\n    74\t\n    75\tdef gen_check(unit):\n    76\t    samples = {r[\"sample_id\"]: r for r in jl(DATA / f\"samples_{unit}.jsonl\")}\n    77\t    labels = {}\n    78\t    for r in jl(DATA / f\"labels_{unit}.jsonl\"):\n    79\t        labels.setdefault(r[\"sample_id\"], r)\n    80\t    an = jr(RES / \"analysis.json\") or {}\n    81\t    out = {}\n    82\t    for site in (\"dec\", \"band\"):\n    83\t        cm = jr(ROOT / \"predictions\" / f\"commit2_{unit}_{site}.json\")\n    84\t        if cm is None:\n    85\t            continue\n    86\t        rep = an.get(f\"gen_{unit}_{site}\", {}).get(\"classes\", {})\n    87\t        site_out = {}\n    88\t        for c, slots in cm[\"slot_map\"].items():\n    89\t            for arm in (\"BASE\", \"FULL\", \"DAS\", \"RAND\"):\n    90\t                n = next((x[3] for x in cm[\"cells\"] if x[0] == site and x[1] == arm and x[2] == c), 0)\n    91\t                k = 0\n    92\t                m = 0\n    93\t                for s in range(n):\n    94\t                    sid = (f\"{unit}|{site}|BASE|{slots[s]['base']}|{s}\" if arm == \"BASE\" else\n    95\t                           f\"{unit}|{site}|{arm}|{c}|{s}\")\n    96\t                    l = labels.get(sid)\n    97\t                    if l is None or sid not in samples:\n    98\t                        continue\n    99\t                    m += 1\n   100\t                    k += int(l[\"label\"] == c and bool(l.get(\"passed\")))\n   101\t                r = (rep.get(c, {}).get(\"arms\", {}).get(arm) or {}).get(\"correct_target\")\n   102\t                site_out[f\"{c}|{arm}\"] = {\"rederived\": k, \"n\": m, \"reported\": r, \"match\": r == k}\n   103\t            # placebo: swap DAS / RAND outcomes by a fair coin per slot\n   104\t            rng = random.Random(7)\n   105\t            a = b = 0\n   106\t            for s in range(30):\n   107\t                d = labels.get(f\"{unit}|{site}|DAS|{c}|{s}\")\n   108\t                q = labels.get(f\"{unit}|{site}|RAND|{c}|{s}\")\n   109\t                if not d or not q:\n   110\t                    continue\n   111\t                x = int(d[\"label\"] == c and bool(d.get(\"passed\")))\n   112\t                y = int(q[\"label\"] == c and bool(q.get(\"passed\")))\n   113\t                if rng.random() < 0.5:\n   114\t                    x, y = y, x\n   115\t                a += int(x and not y)\n   116\t                b += int(y and not x)\n   117\t            site_out[f\"{c}|placebo_swap_DAS_RAND\"] = {\"a_only\": a, \"b_only\": b,\n   118\t                                                      \"fails_as_expected\": abs(a - b) <= max(3, 0.5 * (a + b))}\n   119\t        out[site] = site_out\n   120\t    return out\n   121\t\n   122\t\n   123\tdef med_placebo():\n   124\t    m = jr(RES / \"mediation_T10.json\")\n   125\t    if not m:\n   126\t        return None\n   127\t    d = [v for v in m[\"directions\"].values() if v.get(\"escape_pooled\") is not None]\n   128\t    x = [v[\"pi\"] for v in d]\n   129\t    y = [v[\"escape_pooled\"] for v in d]\n   130\t    rho = spearman(x, y)\n   131\t    rng = random.Random(11)\n   132\t    xp = x[:]\n   133\t    rng.shuffle(xp)\n   134\t    rp = spearman(xp, y)\n   135\t    return {\"rho_rederived\": rho, \"rho_reported\": (m.get(\"spearman_escape_pooled\") or {}).get(\"rho\"),\n   136\t            \"placebo_rho\": rp, \"placebo_fails_as_expected\": abs(rp) < 0.3}\n   137\t\n   138\t\n   139\tdef binom_one_sided(a, b):\n   140\t    \"\"\"P(X >= a) for X ~ Binomial(a + b, 0.5): exact one-sided McNemar on discordant counts.\"\"\"\n   141\t    n = a + b\n   142\t    if n == 0:\n   143\t        return 1.0\n   144\t    return sum(math.comb(n, k) for k in range(a, n + 1)) / 2 ** n\n   145\t\n   146\t\n   147\tdef c2_check(unit, rep_path, L, rtag=\"\"):\n   148\t    \"\"\"c2 ratio = recovery(perm map) / recovery(true map), both over held-out pairs with |Delta_FULL| >= 1, from the\n   149\t    per-pair rows (tf_<unit>_dec<rtag>.jsonl for the true map and Delta_FULL; tf_<unit>_dec_perm_L<L>.jsonl).\"\"\"\n   150\t    rep = jr(rep_path)\n   151\t    true = jl(DATA / f\"tf_{unit}_dec{rtag}.jsonl\")\n   152\t    perm = jl(DATA / f\"tf_{unit}_dec_perm_L{L}.jsonl\")\n   153\t    if rep is None or not true or not perm:\n   154\t        return None\n   155\t    k = rep[\"k_star\"]\n   156\t    full = {(r[\"src\"], r[\"base\"]): r[\"delta_full\"] for r in true if r[\"fit\"] == \"seed0\" and r[\"rank_k\"] == k}\n   157\t    dtrue = {(r[\"src\"], r[\"base\"]): r[\"delta\"] for r in true if r[\"fit\"] == \"seed0\" and r[\"rank_k\"] == k}\n   158\t    keys = [q for q in full if abs(full[q]) >= 1.0]\n   159\t    mf = sum(full[q] for q in keys) / len(keys)\n   160\t    rec_true = (sum(dtrue[q] for q in keys) / len(keys)) / mf\n   161\t    out = {}\n   162\t    fits = sorted({r[\"fit\"] for r in perm})\n   163\t    for f in fits:\n   164\t        d = {}\n   165\t        for r in perm:\n   166\t            if r[\"fit\"] == f:\n   167\t                d[(r[\"src\"], r[\"base\"])] = r[\"delta\"]       # last write wins (a refit row set replaces an earlier one)\n   168\t        if not all(q in d for q in keys):\n   169\t            continue\n   170\t        rec = (sum(d[q] for q in keys) / len(keys)) / mf\n   171\t        name = f.replace(\"perm_\", \"\")\n   172\t        reported = (rep[\"c2\"].get(name) or {}).get(\"ratio_to_true_fit\")\n   173\t        out[name] = {\"rederived_ratio\": rec / rec_true, \"reported_ratio\": reported,\n   174\t                     \"match_0.02\": reported is not None and abs(rec / rec_true - reported) < 0.02,\n   175\t                     \"fails_threshold_0.1\": rec / rec_true > 0.10}\n   176\t    return out\n   177\t\n   178\t\n   179\tdef mediation_check():\n   180\t    an = jr(RES / \"analysis.json\") or {}\n   181\t    med = jr(RES / \"mediation_T10.json\")\n   182\t    if not med:\n   183\t        return None\n   184\t    labels = {}\n   185\t    for r in jl(DATA / \"labels_T10.jsonl\"):\n   186\t        labels.setdefault(r[\"sample_id\"], r)\n   187\t    esc = lambda r: bool(r) and bool(r.get(\"passed\")) and r.get(\"label\") in (\"bfs\", \"dfs\", \"label_propagation\")\n   188\t    top = med[\"top10_escaping\"]\n   189\t    out = {}\n   190\t    for arm in (\"TASK\", \"RAND\"):\n   191\t        a = b = n = ep = ec = 0\n   192\t        for sd in top:\n   193\t            for s in range(30):\n   194\t                x, y = labels.get(f\"T10|med|PUSH|{sd}|{s}\"), labels.get(f\"T10|med|{arm}|{sd}|{s}\")\n   195\t                if not x or not y:\n   196\t                    continue\n   197\t                n += 1\n   198\t                ex, ey = esc(x), esc(y)\n   199\t                ep += ex\n   200\t                ec += ey\n   201\t                a += int(ex and not ey)\n   202\t                b += int(ey and not ex)\n   203\t        rem = 1 - ec / ep if ep else None\n   204\t        rep = (an.get(\"mediation\") or {}).get(f\"clamp_{arm}\", {})\n   205\t        out[arm] = {\"pairs\": n, \"escapes_push\": ep, \"escapes_clamp\": ec, \"removal_rederived\": rem,\n   206\t                    \"removal_reported\": rep.get(\"removal\"), \"match\": rep.get(\"removal\") is not None and rem is not None\n   207\t                    and abs(rep[\"removal\"] - rem) < 1e-9, \"mcnemar_push_gt_clamp_p\": binom_one_sided(a, b)}\n   208\t    # prospective Spearman from the committed predictor (#4) and the raw labels\n   209\t    c4 = jr(ROOT / \"predictions\" / \"commit4_prospective.json\")\n   210\t    xs, ys = [], []\n   211\t    for sd, v in (c4 or {}).get(\"pi\", {}).items():\n   212\t        rows = [labels.get(f\"T10|pro|PUSH|{sd}|{s}\") for s in range(10)]\n   213\t        rows = [r for r in rows if r]\n   214\t        if rows:\n   215\t            xs.append(v[\"pi\"])\n   216\t            ys.append(sum(esc(r) for r in rows) / len(rows))\n   217\t    rho = spearman(xs, ys) if len(xs) > 3 else None\n   218\t    rep = ((an.get(\"mediation\") or {}).get(\"prospective\") or {}).get(\"spearman\", {}).get(\"rho\")\n   219\t    out[\"prospective\"] = {\"n\": len(xs), \"rho_rederived\": rho, \"rho_reported\": rep,\n   220\t                          \"match\": rho is not None and rep is not None and abs(rho - rep) < 1e-9}\n   221\t    return out\n   222\t\n   223\t\n   224\tdef mcnemar_check():\n   225\t    \"\"\"Exact one-sided McNemar DAS > RAND per (unit, site, class) from raw labels; placebo = DAS vs DAS-shuffled.\"\"\"\n   226\t    out = {}\n   227\t    for unit in (\"T10\", \"GRID\"):\n   228\t        labels = {}\n   229\t        for r in jl(DATA / f\"labels_{unit}.jsonl\"):\n   230\t            labels.setdefault(r[\"sample_id\"], r)\n   231\t        for site in (\"dec\", \"band\"):\n   232\t            cm = jr(ROOT / \"predictions\" / f\"commit2_{unit}_{site}.json\")\n   233\t            if not cm:\n   234\t                continue\n   235\t            for c in cm[\"slot_map\"]:\n   236\t                a = b = 0\n   237\t                for s in range(30):\n   238\t                    d = labels.get(f\"{unit}|{site}|DAS|{c}|{s}\")\n   239\t                    q = labels.get(f\"{unit}|{site}|RAND|{c}|{s}\")\n   240\t                    if not d or not q:\n   241\t                        continue\n   242\t                    x = d[\"label\"] == c and bool(d.get(\"passed\"))\n   243\t                    y = q[\"label\"] == c and bool(q.get(\"passed\"))\n   244\t                    a += int(x and not y)\n   245\t                    b += int(y and not x)\n   246\t                out[f\"{unit}|{site}|{c}\"] = {\"das_only\": a, \"rand_only\": b, \"p_one_sided\": binom_one_sided(a, b)}\n   247\t    return out\n   248\t\n   249\t\n   250\tdef k2_check():\n   251\t    \"\"\"K2 from the per-site control flags in the raw result JSONs: disconfirmed iff a decision site fails c2 or c3.\"\"\"\n   252\t    res = {}\n   253\t    for unit in (\"T10\", \"GRID\"):\n   254\t        d = jr(RES / f\"dec_{unit}.json\")\n   255\t        r = jr(RES / f\"rinit_{unit}.json\")\n   256\t        if not d or not r:\n   257\t            continue\n   258\t        c2_fail = any(isinstance(v, dict) and \"ratio_to_true_fit\" in v and (v[\"ratio_to_true_fit\"] or 0) > 0.10\n   259\t                      for v in d[\"c2\"].values())\n   260\t        c3_fail = (r[\"mean_delta_rinit\"] / r[\"mean_delta_trained\"]) > 0.25\n   261\t        res[unit] = {\"c2_fail\": c2_fail, \"c3_fail\": c3_fail,\n   262\t                     \"c3_ratio_from_means\": r[\"mean_delta_rinit\"] / r[\"mean_delta_trained\"]}\n   263\t    disc = any(v[\"c2_fail\"] or v[\"c3_fail\"] for v in res.values())\n   264\t    rep = ((jr(RES / \"analysis.json\") or {}).get(\"K2\") or {}).get(\"status\")\n   265\t    return {\"by_unit\": res, \"status_rederived\": \"DISCONFIRMED\" if disc else \"NOT DISCONFIRMED\", \"status_reported\": rep}\n   266\t\n   267\t\n   268\tdef main():\n   269\t    out = {\"tf\": {\"T10_dec\": tf_check(\"T10\", \"dec\", RES / \"dec_T10.json\"),\n   270\t                  \"T10_band\": tf_check(\"T10\", \"band\", RES / \"band_T10.json\"),\n   271\t                  \"GRID_dec\": tf_check(\"GRID\", \"dec\", RES / \"dec_GRID.json\"),\n   272\t                  \"T10_dec_L24\": tf_check(\"T10\", \"dec\", RES / \"dec_T10_L24.json\", \"_L24\")},\n   273\t           \"gen\": {\"T10\": gen_check(\"T10\"), \"GRID\": gen_check(\"GRID\")},\n   274\t           \"mediation\": med_placebo(),\n   275\t           \"c2\": {\"T10_L22\": c2_check(\"T10\", RES / \"dec_T10.json\", 22),\n   276\t                  \"GRID_L16\": c2_check(\"GRID\", RES / \"dec_GRID.json\", 16),\n   277\t                  \"T10_L24\": c2_check(\"T10\", RES / \"dec_T10_L24.json\", 24, \"_L24\")},\n   278\t           \"mediation_clamp_prospective\": mediation_check(),\n   279\t           \"mcnemar_das_vs_rand\": mcnemar_check(),\n   280\t           \"K2\": k2_check()}\n   281\t    flat = []\n   282\t    for v in out[\"tf\"].values():\n   283\t        if v:\n   284\t            flat.append(v[\"match\"])\n   285\t    for u in out[\"gen\"].values():\n   286\t        for site in u.values():\n   287\t            for k, v in site.items():\n   288\t                if \"match\" in v:\n   289\t                    flat.append(v[\"match\"])\n   290\t    for grp in out[\"c2\"].values():\n   291\t        for v in (grp or {}).values():\n   292\t            flat.append(v[\"match_0.02\"])\n   293\t    mc = out[\"mediation_clamp_prospective\"] or {}\n   294\t    for k in (\"TASK\", \"RAND\", \"prospective\"):\n   295\t        if k in mc:\n   296\t            flat.append(mc[k][\"match\"])\n   297\t    if out[\"mediation\"]:\n   298\t        flat.append(abs(out[\"mediation\"][\"rho_rederived\"] - out[\"mediation\"][\"rho_reported\"]) < 1e-9)\n   299\t    flat.append(out[\"K2\"][\"status_rederived\"] == out[\"K2\"][\"status_reported\"])\n   300\t    out[\"all_match\"] = all(flat) if flat else None\n   301\t    out[\"n_checks\"] = len(flat)\n   302\t    (RES / \"rederive.json\").write_text(json.dumps(out, indent=1))\n   303\t    print(json.dumps({\"all_match\": out[\"all_match\"], \"n_checks\": out[\"n_checks\"]}))\n   304\t\n   305\t\n   306\tif __name__ == \"__main__\":\n   307\t    main()", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [42] THINKING · 2026-10-26 13:40:44 UTC

```
I've reviewed the CPU-side stages. Next I'll check the DAS core (das8.py), the hooked engine, and the CPU tiny-model test to see if any part of the method can run live on CPU.
```

### [43] TOOL CALL — Bash · 2026-10-26 13:40:44 UTC

```
Read das8.py DAS protocol source:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40; cat -n $A/src/das8.py
```

### [44] TOOL RESULT — Bash · 2026-10-26 13:40:44 UTC

```
{"stdout": "     1\t#!/usr/bin/env python3\n     2\t\"\"\"das8: ONE DAS protocol for both families and both sites (declared in commit #0 before any fit).\n     3\t\n     4\tMAP CLASS. W in R^{D x 8} (free), R = QR(W)[:, :k] (orthonormal columns, nested ranks k in {1, 2, 4, 8}); one rank is\n     5\tsampled per step (Matryoshka-style). Interchange: h <- h + R (R^T h_src - R^T h).\n     6\tOBJECTIVE. KL(q_src || q_edit) over the class bins {classes..., other} at the decision pos... [truncated, 31127 chars total]
```

### [45] TOOL CALL — Bash · 2026-10-26 13:40:44 UTC

```
Read CPU tiny-model test and its results:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40; cat -n $A/tests/test_cpu_tiny.py; echo; echo "===== results/unit_tests_cpu.json"; cat $A/results/unit_tests_cpu.json
```

### [46] TOOL RESULT — Bash · 2026-10-26 13:40:44 UTC

```
{"stdout": "     1\t#!/usr/bin/env python3\n     2\t\"\"\"CPU tests of the DAS machinery on tiny random Qwen3 / Gemma3 models (no downloads): the decision-site KV path and\n     3\tthe band recompute path must reproduce full recomputation (zero edit, full-state edit, projected edit), and the\n     4\tderangement / recovery / bootstrap helpers must behave as specified.\n     5\t\n     6\tUsage: .venv/bin/python tests/test_cpu_tiny.py\n     7\t\"\"\"\n     8\t\n     9\tfrom __future__ import annotations\n    10\t\n    11\timport sys\n    12\tfrom pathlib import Path\n    13\t\n    14\tsys.path.insert(0, str(Path(__file__).resolve().parents[1] / \"src\"))\n    15\t\n    16\timport numpy as np\n    17\timport torch\n    18\t\n    19\timport das8\n    20\timport stats8 as ST\n    21\tfrom engine8 import LM, block_hooks, prefill\n    22\t\n    23\t\n    24\tdef tiny(family: str) -> LM:\n    25\t    torch.manual_seed(0)\n    26\t    if family == \"qwen\":\n    27\t        from transformers import Qwen3Config, Qwen3ForCausalLM\n    28\t        cfg = Qwen3Config(vocab_size=500, hidden_size=64, intermediate_size=128, num_hidden_layers=6,\n    29\t                          num_attention_heads=4, num_key_value_heads=2, head_dim=16, max_position_embeddings=512,\n    30\t                          tie_word_embeddings=False)\n    31\t        cfg._attn_implementation = \"sdpa\"\n    32\t        m = Qwen3ForCausalLM(cfg).to(torch.bfloat16)\n    33\t    else:\n    34\t        from transformers import Gemma3ForCausalLM, Gemma3TextConfig\n    35\t        cfg = Gemma3TextConfig(vocab_size=500, hidden_size=64, intermediate_size=128, num_hidden_layers=6,\n    36\t                               num_attention_heads=4, num_key_value_heads=2, head_dim=16, max_position_embeddings=512,\n    37\t                               sliding_window=512, query_pre_attn_scalar=16)\n    38\t        cfg._attn_implementation = \"sdpa\"\n    39\t        m = Gemma3ForCausalLM(cfg).to(torch.bfloat16)\n    40\t    m.eval()\n    41\t    m.requires_grad_(False)\n    42\t\n    43\t    class Tok:\n    44\t        def decode(self, ids, **kw):\n    45\t            return \" \".join(str(i) for i in ids)\n    46\t\n    47\t        def __len__(self):\n    48\t            return 500\n    49\t    lm = LM(family, Tok(), m, {})\n    50\t    lm.D = 64\n    51\t    return lm\n    52\t\n    53\t\n    54\tdef prompts(n: int, rng: np.random.Generator) -> dict[str, dict]:\n    55\t    spec = list(rng.integers(5, 400, 20))\n    56\t    tail = [7, 8, 9]\n    57\t    opening = [11, 12, 13, 14]\n    58\t    P = {}\n    59\t    for i in range(n):\n    60\t        seg = list(rng.integers(5, 400, int(rng.integers(3, 7))))\n    61\t        ids = [1, 2] + seg + spec + tail\n    62\t        p1 = 2 + len(seg)\n    63\t        P[f\"p{i}\"] = {\"key\": f\"p{i}\", \"unit\": \"TEST\", \"ids\": ids, \"P\": len(ids), \"p1\": p1, \"spec_end\": p1 + len(spec),\n    64\t                      \"dec_ids\": ids + opening}\n    65\t    return P\n    66\t\n    67\t\n    68\tdef check(family: str) -> dict:\n    69\t    lm = tiny(family)\n    70\t    rng = np.random.default_rng(0)\n    71\t    P = prompts(8, rng)\n    72\t    cmap = das8.ClassMap([\"a\", \"b\", \"c\"], {\"a\": [11, 20], \"b\": [30, 31], \"c\": [40]})\n    73\t    keys = list(P)\n    74\t    site = das8.DecSite(lm, P, cmap, base_keys=keys, all_keys=keys, G=4, Q=3)\n    75\t    out = {}\n    76\t    L = 2\n    77\t    # zero edit on the KV path vs full recompute\n    78\t    errs, errs_full, errs_proj = [], [], []\n    79\t    R = das8.haar(1, 64, 2)\n    80\t    for b in keys[:4]:\n    81\t        lg_full = prefill(lm, P[b][\"dec_ids\"])[\"logits\"]\n    82\t        H = torch.stack([site.H[b][L]] * 3)[None].expand(4, 3, -1).contiguous()\n    83\t        lg_kv = site.forward(L, [b] * 4, H)[0, 0]\n    84\t        errs.append(float((cmap.lp(lg_full) - cmap.lp(lg_kv)).abs().max()))\n    85\t        s = keys[-1]\n    86\t        hs = site.H[s][L]\n    87\t        hb = site.H[b][L]\n    88\t\n    89\t        def ed(h, val):\n    90\t            h = h.clone()\n    91\t            h[:, -1] = val.to(h.dtype)\n    92\t            return h\n    93\t        lg_full_e = prefill(lm, P[b][\"dec_ids\"], edits={L: lambda h: ed(h, hs)})[\"logits\"]\n    94\t        lg_kv_e = site.forward(L, [b] * 4, hs[None, None].expand(4, 3, -1).contiguous())[0, 0]\n    95\t        errs_full.append(float((cmap.lp(lg_full_e) - cmap.lp(lg_kv_e)).abs().max()))\n    96\t        hn = hb + ((hs - hb) @ R) @ R.T\n    97\t        lg_full_p = prefill(lm, P[b][\"dec_ids\"], edits={L: lambda h: ed(h, hn)})[\"logits\"]\n    98\t        lg_kv_p = site.forward(L, [b] * 4, hn[None, None].expand(4, 3, -1).contiguous())[0, 0]\n    99\t        errs_proj.append(float((cmap.lp(lg_full_p) - cmap.lp(lg_kv_p)).abs().max()))\n   100\t    # mixed bases in one batch (different prefix lengths -> left padding)\n   101\t    mix = keys[:4]\n   102\t    Hm = torch.stack([torch.stack([site.H[b][L]] * 3) for b in mix])\n   103\t    lg_mix = site.forward(L, mix, Hm)[:, 0]\n   104\t    errs_mix = [float((cmap.lp(prefill(lm, P[b][\"dec_ids\"])[\"logits\"]) - cmap.lp(lg_mix[i])).abs().max())\n   105\t                for i, b in enumerate(mix)]\n   106\t    out[\"dec_zero_edit\"] = max(errs)\n   107\t    out[\"dec_full_edit\"] = max(errs_full)\n   108\t    out[\"dec_proj_edit\"] = max(errs_proj)\n   109\t    out[\"dec_mixed_lengths\"] = max(errs_mix)\n   110\t    # band: zero edit and full-state exchange vs full recompute with hooks\n   111\t    band = (1, 2, 3)\n   112\t    cls = {k: 0 for k in keys}\n   113\t    bs = das8.BandSite(lm, P, cmap, band, keys, keys, cls)\n   114\t    e0, e1, e2 = [], [], []\n   115\t    for b, s in zip(keys[:4], keys[4:8]):\n   116\t        lg_none = bs.forward([(s, b)], \"none\")[0]\n   117\t        lg_full = prefill(lm, P[b][\"dec_ids\"])[\"logits\"]\n   118\t        e0.append(float((cmap.lp(lg_none) - cmap.lp(lg_full)).abs().max()))\n   119\t        S = bs.n_spec\n   120\t        src = bs.src[s].float()\n   121\t        pb = P[b][\"p1\"]\n   122\t\n   123\t        def mk(j):\n   124\t            def f(h):\n   125\t                h = h.clone()\n   126\t                h[0, pb:pb + S] = src[j].to(h.dtype)\n   127\t                return h\n   128\t            return f\n   129\t        lg_hook = prefill(lm, P[b][\"dec_ids\"], edits={l: mk(j) for j, l in enumerate(band)})[\"logits\"]\n   130\t        lg_bs = bs.forward([(s, b)], None)[0]\n   131\t        e1.append(float((cmap.lp(lg_hook) - cmap.lp(lg_bs)).abs().max()))\n   132\t\n   133\t        def mkp(j):\n   134\t            def f(h):\n   135\t                h = h.clone()\n   136\t                hb_ = h[0, pb:pb + S].float()\n   137\t                h[0, pb:pb + S] = (hb_ + ((src[j] - hb_) @ R) @ R.T).to(h.dtype)\n   138\t                return h\n   139\t            return f\n   140\t        lg_hook_p = prefill(lm, P[b][\"dec_ids\"], edits={l: mkp(j) for j, l in enumerate(band)})[\"logits\"]\n   141\t        lg_bs_p = bs.forward([(s, b)], R)[0]\n   142\t        e2.append(float((cmap.lp(lg_hook_p) - cmap.lp(lg_bs_p)).abs().max()))\n   143\t    out[\"band_zero_edit\"] = max(e0)\n   144\t    out[\"band_full_exchange\"] = max(e1)\n   145\t    out[\"band_proj_edit\"] = max(e2)\n   146\t    # a few fit steps run without error and return an orthonormal R\n   147\t    pairs = [(keys[i], keys[j]) for i in range(4) for j in range(4, 8)]\n   148\t    f = site.fit(L, pairs, pairs[:4], seed=0, steps=4, val_every=2)\n   149\t    out[\"fit_orth_err\"] = float((f[\"R\"].T @ f[\"R\"] - torch.eye(8)).abs().max())\n   150\t    fb = bs.fit(pairs, pairs[:2], seed=0, q_tgt={k: site.q[k] for k in keys}, steps=2, bs=2, val_every=1)\n   151\t    out[\"band_fit_orth_err\"] = float((fb[\"R\"].T @ fb[\"R\"] - torch.eye(8)).abs().max())\n   152\t    return out\n   153\t\n   154\t\n   155\tdef main() -> None:\n   156\t    res = {}\n   157\t    for fam in (\"qwen\", \"gemma\"):\n   158\t        res[fam] = check(fam)\n   159\t        print(fam, res[fam])\n   160\t    # recovery / bootstrap on synthetic deltas with a known ratio\n   161\t    rng = np.random.default_rng(0)\n   162\t    df = rng.normal(5, 1, 600)\n   163\t    de = 0.6 * df + rng.normal(0, 0.1, 600)\n   164\t    src = [f\"s{i % 12}\" for i in range(600)]\n   165\t    base = [f\"b{i % 50}\" for i in range(600)]\n   166\t    r = ST.recovery(de, df, src, base, n_boot=200)\n   167\t    print(\"recovery\", r[\"recovery\"], r[\"ci95\"])\n   168\t    ok = all(v < 0.1 for fam in res.values() for k, v in fam.items() if not k.endswith(\"orth_err\")) and \\\n   169\t        abs(r[\"recovery\"] - 0.6) < 0.01\n   170\t    print(\"PASS\" if ok else \"FAIL\")\n   171\t\n   172\t\n   173\tif __name__ == \"__main__\":\n   174\t    main()\n\n===== results/unit_tests_cpu.json\n{\"note\": \"tests/test_cpu_tiny.py on tiny random Qwen3 / Gemma3 models (bf16, CPU): max |log P(class)| difference between the DAS machinery and full recomputation with hooks\",\n \"qwen\": {\"dec_zero_edit\": 0.0019, \"dec_full_edit\": 0.00094, \"dec_proj_edit\": 0.0019, \"dec_mixed_lengths\": 0.0019, \"band_zero_edit\": 0.00093, \"band_full_exchange\": 0.0010, \"band_proj_edit\": 0.0012, \"fit_orth_err\": 2.4e-07, \"band_fit_orth_err\": 3.6e-07},\n \"gemma\": {\"dec_zero_edit\": 0.0019, \"dec_full_edit\": 0.0011, \"dec_proj_edit\": 0.0016, \"dec_mixed_lengths\": 0.0019, \"band_zero_edit\": 0.0021, \"band_full_exchange\": 0.0012, \"band_proj_edit\": 0.0022, \"fit_orth_err\": 2.4e-07, \"band_fit_orth_err\": 2.4e-07},\n \"recovery_synthetic_true_0.6\": {\"estimate\": 0.5992, \"ci95\": [0.5968, 0.6017], \"pass_within_0.01\": true},\n \"result\": \"PASS\"}", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [47] THINKING · 2026-10-26 13:42:46 UTC

```
I now have a plan: since GPU-dependent components can't run, the notebook will use the artifact's CPU-only analysis path on the T10 decision-site teacher-forced pairs. Next I'll examine how pairs are distributed across classes/prompts and review the result metadata to select 100 diverse examples.
```

### [48] TOOL CALL — Bash · 2026-10-26 13:42:46 UTC

```
Profile T10 teacher-forced pairs distribution:
python3 - <<'EOF'
import json, collections, re
A="/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40"
d=json.load(open(A+"/full_method_out.json"))
ds={x["dataset"]:x["examples"] for x in d["datasets"]}
ex=ds["T10_dec_teacher_forced"]
print("n",len(ex))
pat=re.compile(r"source=(\S+) base=(\S+)")
srcs=collections.Counter(); bases=collections.Counter(); combo=collections.Counter()
nf=0
for e in ex:
    s,b=pat.search(e["input"]).groups()
    srcs[s]+=1; bases[b]+=1
    combo[(e["metadata_class_src"],e["metadata_class_base"])]+=1
    nf+= abs(e["metadata_delta_full"])>=1
print("pairs |dfull|>=1:",nf)
print("n unique src",len(srcs),"n unique base",len(bases))
print("combos",combo)
print("src sample",list(srcs.items())[:12])
print("base sample",list(bases.items())[:12])
import numpy as np
df=np.array([e["metadata_delta_full"] for e in ex]); dk=np.array([float(e["predict_seed0_k4"]) for e in ex])
ok=np.abs(df)>=1
print("mean dfull(ok)",df[ok].mean(),"mean das k4(ok)",dk[ok].mean(),"rec",dk[ok].mean()/df[ok].mean())
print("input example:",ex[0]["input"])
print("all predict keys present in all rows?", all(all(f"predict_seed{s}_k{k}" in e for s in range(3) for k in (1,2,4,8)) for e in ex))
EOF
```

### [49] TOOL RESULT — Bash · 2026-10-26 13:42:46 UTC

```
{"stdout": "n 600\npairs |dfull|>=1: 552\nn unique src 24 n unique base 44\ncombos Counter({('bfs', 'union_find'): 280, ('dfs', 'union_find'): 280, ('bfs', 'dfs'): 20, ('union_find', 'dfs'): 20})\nsrc sample [('T10|forced|k3|j0|bfs', 37), ('T10|forced|k3|j1|bfs', 37), ('T10|forced|k3|j2|bfs', 39), ('T10|forced|k3|j3|bfs', 37), ('T10|forced|k4|j0|bfs', 39), ('T10|forced|k4|j1|bfs', 39), ('T10|forced|k4|j2|bfs', 35), ('T10|forced|k4|j3|bfs', 37), ('T10|forced|k3|j0|dfs', 31), ('T10|forced|k3|j1|dfs', 36), ('T10|forced|k3|j2|dfs', 37), ('T10|forced|k3|j3|dfs', 38)]\nbase sample [('T10|twin|W5|school', 15), ('T10|twin|W5|head', 11), ('T10|twin|W5|bed', 14), ('T10|padtwin|k3|j0|bfs', 15), ('T10|padtwin|k3|j1|bfs', 14), ('T10|padtwin|k3|j3|bfs', 15), ('T10|padtwin|k3|j0|dfs', 14), ('T10|padtwin|k3|j1|dfs', 14), ('T10|padtwin|k3|j2|dfs', 11), ('T10|padtwin|k3|j3|dfs', 13), ('T10|padtwin|k3|j0|union_find', 13), ('T10|padtwin|k3|j1|union_find', 13)]\nmean dfull(ok) 2.0596929840419604 mean das k4(ok) 17.369176630434787 rec 8.4328959534296\ninput example: [T10 | dec | teacher-forced held-out pair] source=T10|forced|k3|j0|bfs base=T10|twin|W5|school\nall predict keys present in all rows? True", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [50] TOOL CALL — Bash · 2026-10-26 13:42:46 UTC

```
Inspect dec_T10 metadata structure and sizes:
python3 - <<'EOF'
import json
A="/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40"
d=json.load(open(A+"/full_method_out.json"))
md=d["metadata"]
def skel(x, ind=0, depth=3):
    p="  "*ind
    if isinstance(x, dict):
        for k,v in x.items():
            if isinstance(v,(dict,list)) and depth>0:
                print(f"{p}{k}: {type(v).__name__}[{len(v)}] {json.dumps(v)[:120] if len(json.dumps(v))<=120 else ''}")
                if len(json.dumps(v))>120: skel(v, ind+1, depth-1)
            else:
                print(f"{p}{k}: {json.dumps(v)[:120]}")
    elif isinstance(x, list):
        print(f"{p}list[{len(x)}] first: {json.dumps(x[0])[:150] if x else ''}")
for key in ["dec_T10"]:
    print("=====",key, len(json.dumps(md[key])))
    skel({k:v for k,v in md[key].items() if k!="scan"}, 0, 3)
    print("scan keys:", list(md[key]["scan"].keys()))
    print("scan[22]:", json.dumps(md[key]["scan"]["22"])[:800])
for key in md:
    print(key, len(json.dumps(md[key])))
EOF
```

### [51] TOOL RESULT — Bash · 2026-10-26 13:42:46 UTC

```
{"stdout": "===== dec_T10 18889\nunit: \"T10\"\nfamily: \"qwen\"\nclasses: list[3] [\"bfs\", \"dfs\", \"union_find\"]\nL_star: 22\nreadout_proximal: false\nk_star: 4\nunit_tests: dict[6] \n  U1_max_abs_logit_diff: 0.0\n  U2_max_abs_logP_class_diff_kv_vs_full: 0.25\n  U3_max_abs_logP_class_diff_fullstate_edit: 0.24909591674804688\n  U2_pass_0.3: true\n  U9: dict[3] {\"kl_random_init_map\": 11.297689338525137, \"kl_after_20_steps\": 10.703729808330536, \"reduction\": 0.052573540694662024}\n  U7_memory_peak_GB: 16.28\nn_train_pairs: 2000\nn_held_pairs: 600\nrecovery_by_rank: dict[6] \n  1: dict[9] \n    n: 552\n    n_src: 24\n    n_base: 43\n    recovery: 7.669751647939563\n    ci95: list[2] [5.110762500048022, 10.711533188181077]\n    mean_delta_edit: 15.797333658605382\n    mean_delta_full: 2.0596929840419604\n    iia_like_share_positive: 0.9637681159420289\n    by_class: dict[3] \n      bfs: {\"n\": 268, \"n_src\": 8, \"n_base\": 42, \"recovery\": 15.251578908510824, \"ci95\": [13.160840832975486, 18.375666214130668], \"\n      dfs: {\"n\": 264, \"n_src\": 8, \"n_base\": 40, \"recovery\": 4.199587321664158, \"ci95\": [3.7096472280056987, 4.826502591117777], \"me\n      union_find: {\"n\": 20, \"n_src\": 8, \"n_base\": 3, \"recovery\": -0.38510951782265795, \"ci95\": [-0.5088384120140922, -0.26427292141696335]\n  2: dict[9] \n    n: 552\n    n_src: 24\n    n_base: 43\n    recovery: 8.123025298693475\n    ci95: list[2] [5.604826630492428, 11.024681573169214]\n    mean_delta_edit: 16.7309382169143\n    mean_delta_full: 2.0596929840419604\n    iia_like_share_positive: 0.9655797101449275\n    by_class: dict[3] \n      bfs: {\"n\": 268, \"n_src\": 8, \"n_base\": 42, \"recovery\": 15.357407740534617, \"ci95\": [13.292148468442047, 18.476256051984816], \"\n      dfs: {\"n\": 264, \"n_src\": 8, \"n_base\": 40, \"recovery\": 4.9261680112513275, \"ci95\": [4.4166541847452905, 5.565255242958096], \"m\n      union_find: {\"n\": 20, \"n_src\": 8, \"n_base\": 3, \"recovery\": -0.1632257433597665, \"ci95\": [-0.2520558320003138, -0.07450424116877655],\n  4: dict[9] \n    n: 552\n    n_src: 24\n    n_base: 43\n    recovery: 8.432892175097768\n    ci95: list[2] [5.944438813564415, 11.296062773717395]\n    mean_delta_edit: 17.36916884823122\n    mean_delta_full: 2.0596929840419604\n    iia_like_share_positive: 0.9746376811594203\n    by_class: dict[3] \n      bfs: {\"n\": 268, \"n_src\": 8, \"n_base\": 42, \"recovery\": 15.376468241969315, \"ci95\": [13.32855957124446, 18.497263191572312], \"m\n      dfs: {\"n\": 264, \"n_src\": 8, \"n_base\": 40, \"recovery\": 5.469886538180017, \"ci95\": [4.9306864234619665, 6.14899198721382], \"mea\n      union_find: {\"n\": 20, \"n_src\": 8, \"n_base\": 3, \"recovery\": -0.07381441195198805, \"ci95\": [-0.1668347527501457, 0.008538033804510962]\n  8: dict[9] \n    n: 552\n    n_src: 24\n    n_base: 43\n    recovery: 9.263255251537572\n    ci95: list[2] [6.832667803808298, 12.03069017902412]\n    mean_delta_edit: 19.079461850981783\n    mean_delta_full: 2.0596929840419604\n    iia_like_share_positive: 0.9945652173913043\n    by_class: dict[3] \n      bfs: {\"n\": 268, \"n_src\": 8, \"n_base\": 42, \"recovery\": 15.69703115735749, \"ci95\": [13.582332293394673, 18.897318145667985], \"m\n      dfs: {\"n\": 264, \"n_src\": 8, \"n_base\": 40, \"recovery\": 6.765117512564584, \"ci95\": [6.116286286142477, 7.61321670498485], \"mean\n      union_find: {\"n\": 20, \"n_src\": 8, \"n_base\": 3, \"recovery\": 0.08153416970484614, \"ci95\": [-0.012255716542621814, 0.17431038030115376]\n  seed1: dict[4] \n    1: dict[8] \n      n: 552\n      n_src: 24\n      n_base: 43\n      recovery: 7.978394659508171\n      ci95: [5.425017104772042, 11.358715910203175]\n      mean_delta_edit: 16.433043504106827\n      mean_delta_full: 2.0596929840419604\n      iia_like_share_positive: 0.9637681159420289\n    2: dict[8] \n      n: 552\n      n_src: 24\n      n_base: 43\n      recovery: 8.059545217502045\n      ci95: [5.461554341625092, 11.506563462867074]\n      mean_delta_edit: 16.6001887390579\n      mean_delta_full: 2.0596929840419604\n      iia_like_share_positive: 0.9637681159420289\n    4: dict[8] \n      n: 552\n      n_src: 24\n      n_base: 43\n      recovery: 8.575711046138544\n      ci95: [6.058519950908245, 11.870031312367576]\n      mean_delta_edit: 17.6633318749027\n      mean_delta_full: 2.0596929840419604\n      iia_like_share_positive: 0.967391304347826\n    8: dict[8] \n      n: 552\n      n_src: 24\n      n_base: 43\n      recovery: 9.601373778896075\n      ci95: [7.295418717288468, 12.523352758231937]\n      mean_delta_edit: 19.77588220955669\n      mean_delta_full: 2.0596929840419604\n      iia_like_share_positive: 0.9981884057971014\n  seed2: dict[4] \n    1: dict[8] \n      n: 552\n      n_src: 24\n      n_base: 43\n      recovery: 7.606927563856273\n      ci95: [5.1721737908815735, 10.814795678155821]\n      mean_delta_edit: 15.667935333390167\n      mean_delta_full: 2.0596929840419604\n      iia_like_share_positive: 0.9746376811594203\n    2: dict[8] \n      n: 552\n      n_src: 24\n      n_base: 43\n      recovery: 7.787766432423661\n      ci95: [5.340741818593619, 11.01279890842098]\n      mean_delta_edit: 16.040407882220503\n      mean_delta_full: 2.0596929840419604\n      iia_like_share_positive: 0.9764492753623188\n    4: dict[8] \n      n: 552\n      n_src: 24\n      n_base: 43\n      recovery: 7.836088436300938\n      ci95: [5.390836959370066, 11.05939249845571]\n      mean_delta_edit: 16.139936374581378\n      mean_delta_full: 2.0596929840419604\n      iia_like_share_positive: 0.9764492753623188\n    8: dict[8] \n      n: 552\n      n_src: 24\n      n_base: 43\n      recovery: 8.754134259076167\n      ci95: [6.516218078594462, 11.66312092363191]\n      mean_delta_edit: 18.030828914780546\n      mean_delta_full: 2.0596929840419604\n      iia_like_share_positive: 1.0\nrank1_only: dict[8] \n  n: 552\n  n_src: 24\n  n_base: 43\n  recovery: 7.693053450069223\n  ci95: list[2] [5.025825083962496, 10.863170135670892]\n  mean_delta_edit: 15.845328216967376\n  mean_delta_full: 2.0596929840419604\n  iia_like_share_positive: 0.9637681159420289\nmain: dict[9] \n  n: 552\n  n_src: 24\n  n_base: 43\n  recovery: 8.432892175097768\n  ci95: list[2] [5.944438813564415, 11.296062773717395]\n  mean_delta_edit: 17.36916884823122\n  mean_delta_full: 2.0596929840419604\n  iia_like_share_positive: 0.9746376811594203\n  by_class: dict[3] \n    bfs: dict[8] \n      n: 268\n      n_src: 8\n      n_base: 42\n      recovery: 15.376468241969315\n      ci95: [13.32855957124446, 18.497263191572312]\n      mean_delta_edit: 23.265443097299606\n      mean_delta_full: 1.5130550612264604\n      iia_like_share_positive: 1.0\n    dfs: dict[8] \n      n: 264\n      n_src: 8\n      n_base: 40\n      recovery: 5.469886538180017\n      ci95: [4.9306864234619665, 6.14899198721382]\n      mean_delta_edit: 12.732101447654493\n      mean_delta_full: 2.3276719469012637\n      iia_like_share_positive: 1.0\n    union_find: dict[8] \n      n: 20\n      n_src: 8\n      n_base: 3\n      recovery: -0.07381441195198805\n      ci95: [-0.1668347527501457, 0.008538033804510962]\n      mean_delta_edit: -0.43161640167236326\n      mean_delta_full: 5.847318840026856\n      iia_like_share_positive: 0.3\noff_manifold_flag: true\nfull_state_held: dict[3] {\"mean_delta\": 1.9211839612325032, \"flip_share\": 0.97, \"share_abs_ge_1\": 0.92}\nfits: dict[3] \n  0: dict[5] \n    best_step: 240\n    best_val_kl: 0.1855863432113741\n    steps_run: 240\n    seconds: 80.7\n    hist_tail: list[3] \n      list[3] first: {\"step\": 238, \"k\": 8, \"loss\": 0.03378370404243469}\n  1: dict[5] \n    best_step: 240\n    best_val_kl: 0.09386272074819621\n    steps_run: 240\n    seconds: 78.9\n    hist_tail: list[3] \n      list[3] first: {\"step\": 238, \"k\": 8, \"loss\": 0.03876985237002373}\n  2: dict[5] \n    best_step: 240\n    best_val_kl: 0.31441303010979027\n    steps_run: 240\n    seconds: 78.7\n    hist_tail: list[3] \n      list[3] first: {\"step\": 238, \"k\": 1, \"loss\": 0.14208051562309265}\nc1: dict[4] \n  1: dict[5] {\"median\": -0.008520448433719983, \"p95\": 0.0070718851325280215, \"max\": 0.015280275403198753, \"n\": 50, \"pass\": true}\n  2: dict[5] {\"median\": -0.0056122191365223775, \"p95\": 0.005160303288540625, \"max\": 0.013733504369389029, \"n\": 50, \"pass\": true}\n  4: dict[5] {\"median\": -0.005335866348852657, \"p95\": 0.014967972142734435, \"max\": 0.019018203906749454, \"n\": 50, \"pass\": true}\n  8: dict[5] {\"median\": 0.0010398891127624227, \"p95\": 0.028834794071987017, \"max\": 0.043646665835180815, \"n\": 50, \"pass\": true}\nc2: dict[6] \n  note: \"targets = class-mean q of the permuted class; pairs whose permuted target equals class_base are dropped (100% of retain\n  pi1: dict[9] \n    fit: dict[4] {\"best_step\": 200, \"best_val_kl\": 0.0006250844394306081, \"steps_run\": 240, \"seconds\": 98.6}\n    n_train_pairs_retained: 1000\n    share_targets_changed: 1.0\n    heldout_recovery_toward_true_class: dict[8] \n      n: 552\n      n_src: 24\n      n_base: 43\n      recovery: 7.322660713185028\n      ci95: [5.557409071556048, 9.10141212529044]\n      mean_delta_edit: 15.082432895466901\n      mean_delta_full: 2.0596929840419604\n      iia_like_share_positive: 0.9510869565217391\n    ratio_to_true_fit: 0.8683451135316018\n    pass: false\n    secondary_mean_delta_toward_permuted_class: 17.38161880493164\n    secondary_n_pairs: 300\n    train_fit_kl_to_permuted_targets: 0.00017939724687815302\n  pi2: dict[9] \n    fit: dict[4] {\"best_step\": 140, \"best_val_kl\": 0.4013086110033984, \"steps_run\": 200, \"seconds\": 83.9}\n    n_train_pairs_retained: 1000\n    share_targets_changed: 1.0\n    heldout_recovery_toward_true_class: dict[8] \n      n: 552\n      n_src: 24\n      n_base: 43\n      recovery: 5.344927867025502\n      ci95: [3.749744421598219, 7.189032204097036]\n      mean_delta_edit: 11.008910427922787\n      mean_delta_full: 2.0596929840419604\n      iia_like_share_positive: 0.9637681159420289\n    ratio_to_true_fit: 0.6338190689558455\n    pass: false\n    secondary_mean_delta_toward_permuted_class: 18.00359447479248\n    secondary_n_pairs: 300\n    train_fit_kl_to_permuted_targets: 0.6879612706676372\n  prompt: dict[7] \n    fit: dict[4] {\"best_step\": 40, \"best_val_kl\": 0.40051302424471436, \"steps_run\": 100, \"seconds\": 41.4}\n    n_train_pairs_retained: 997\n    share_targets_changed: 1.0\n    heldout_recovery_toward_true_class: dict[8] \n      n: 552\n      n_src: 24\n      n_base: 43\n      recovery: 6.456976054391884\n      ci95: [4.813412999893811, 8.153278152289749]\n      mean_delta_edit: 13.299388277357902\n      mean_delta_full: 2.0596929840419604\n      iia_like_share_positive: 0.9637681159420289\n    ratio_to_true_fit: 0.7656893886843779\n    pass: false\n    train_fit_kl_to_permuted_targets: 0.42942275145569436\n  pass: false\n  primary_statistic: \"held-out recovery toward the TRUE source class under each label-control fit <= 0.1 x true-fit recovery\"\nc4: dict[10] \n  n: 16\n  n_src: 16\n  n_base: 16\n  recovery: -2.723979080428778\n  ci95: list[2] [-5.093644027707801, -1.8957539939936374]\n  mean_delta_edit: 4.2969948053359985\n  mean_delta_full: -1.577469825744629\n  iia_like_share_positive: 1.0\n  pass: false\n  n_pairs: 16\nc5: dict[4] \n  twins: dict[3] {\"recovery_proj\": 1.4994820090092573, \"retention\": 0.17781349243824202, \"n_states\": 160}\n  twins_forced_bans: dict[3] {\"recovery_proj\": 1.5962260051014685, \"retention\": 0.18928571265444438, \"n_states\": 290}\n  pass: false\n  pass_b: false\nc6: dict[2] \n  twins: dict[6] \n    share: 0.007648519389761101\n    random_p95: 0.0016031257661150015\n    random_median: 0.000911469406350243\n    percentile: 100.0\n    pass: true\n    n_states: 160\n  twins_forced_bans: dict[6] \n    share: 0.09445830992481899\n    random_p95: 0.001493969437846974\n    random_median: 0.0009164576202228083\n    percentile: 100.0\n    pass: true\n    n_states: 290\nc7: dict[4] \n  first_cosines: list[3] [0.8912194803858107, 0.8534730806048926, 0.8694175379191025]\n  median_first_cosine: 0.8694175379191025\n  random_p99: 0.07163477103780044\n  pass: true\nbaselines: dict[9] \n  DiM1_bfs: dict[9] \n    n: 268\n    n_src: 8\n    n_base: 42\n    recovery: 0.5856901884725874\n    ci95: list[2] [0.45542031711320397, 0.772767924122036]\n    mean_delta_edit: 0.8861815039791278\n    mean_delta_full: 1.5130550612264604\n    iia_like_share_positive: 0.9850746268656716\n    cos_with_R1: 0.5627881288528442\n  DiM1_dfs: dict[9] \n    n: 264\n    n_src: 8\n    n_base: 40\n    recovery: 0.43653439266722416\n    ci95: list[2] [0.38235660125496534, 0.501817130694301]\n    mean_delta_edit: 1.0161088596690784\n    mean_delta_full: 2.3276719469012637\n    iia_like_share_positive: 1.0\n    cos_with_R1: 0.393543541431427\n  DiM1_union_find: dict[9] \n    n: 20\n    n_src: 8\n    n_base: 3\n    recovery: 0.6092489262819452\n    ci95: list[2] [0.5272342449872579, 0.6940608429472683]\n    mean_delta_edit: 3.5624727249145507\n    mean_delta_full: 5.847318840026856\n    iia_like_share_positive: 1.0\n    cos_with_R1: 0.10747277736663818\n  PCA1: dict[8] \n    n: 552\n    n_src: 24\n    n_base: 43\n    recovery: -0.04166401731627161\n    ci95: list[2] [-0.1379056874168793, 0.06669660825876697]\n    mean_delta_edit: -0.08581508415332739\n    mean_delta_full: 2.0596929840419604\n    iia_like_share_positive: 0.3605072463768116\n  PCA2: dict[8] \n    n: 552\n    n_src: 24\n    n_base: 43\n    recovery: 0.45548232237158714\n    ci95: list[2] [0.34982789586714785, 0.5832900670509952]\n    mean_delta_edit: 0.9381537437438965\n    mean_delta_full: 2.0596929840419604\n    iia_like_share_positive: 0.9981884057971014\n  PCA4: dict[8] \n    n: 552\n    n_src: 24\n    n_base: 43\n    recovery: 0.8956693212645956\n    ci95: list[2] [0.8202879184076336, 0.9827053399713954]\n    mean_delta_edit: 1.8448038170303123\n    mean_delta_full: 2.0596929840419604\n    iia_like_share_positive: 0.9873188405797102\n  PCA8: dict[8] \n    n: 552\n    n_src: 24\n    n_base: 43\n    recovery: 0.9732852775981878\n    ci95: list[2] [0.8714353177663396, 1.0855787480277441]\n    mean_delta_edit: 2.0046688577403193\n    mean_delta_full: 2.0596929840419604\n    iia_like_share_positive: 0.9873188405797102\n  logit_lens_cos_R1: 0.06893440335988998\n  logit_lens_tokens: list[2] [\" bfs\", \" find\"]\niter7_side: null\nseconds: 1403.8\nscan keys: ['0', '2', '4', '6', '8', '10', '12', '14', '16', '18', '20', '22', '24', '26', '28', '30', '32', '34']\nscan[22]: {\"cv_recovery_by_fold\": [8.570195243578492, 7.241655764819687], \"cv_median_recovery\": 7.9059255041990895, \"full_state_mean_delta_held96\": 1.499998966852824, \"full_state_flip_share_held96\": 0.9791666666666666}\nmethod_name 160\ndescription 328\nverdicts 4774\nK2 488\nmediation 1724\ncommit_chain 222\ndeviations 3982\ndec_T10 18889\nband_T10 9619\ndec_GRID 15348\ndec_T10_L24 19033\nrinit_T10 890\nrinit_GRID 900\nrinit_T10_band 532\nrinit_T10_L24 892\ns3_T10 733\ns3_GRID 1012\ngeometry 3531\nnovelty_audit 384\ncosts 39\npost_T10 636\nunit_tests_cpu 801\nunit_tests_gpu_T10 318\nunit_tests_gpu_GRID 325\nmediation_T10 21199\npositioning 3759\nrederive 5036\nscan_T10 4120\nscan_GRID 3921\ngen_T10_dec 6530\ngen_T10_band 6705\ngen_GRID_dec 4182", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [52] THINKING · 2026-10-26 13:42:54 UTC

```
The metadata is small enough (~150 KB) to ship with the 100 curated pairs. Next I'll examine how `run_dec.py` builds the recovery-by-rank tables and OFF-MANIFOLD flag from per-pair Deltas so the notebook can reuse that exact code.
```

### [53] TOOL CALL — Bash · 2026-10-26 13:42:54 UTC

```
Locate recovery table code in run_dec.py:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40; grep -n "recovery_by_rank\|off_manifold\|OFF_MANIFOLD\|def \|by_class\|ST.recovery\|tf_rows\|append_jsonl\|k_star\|rank1_only\|\"main\"\|seed1\|n_boot\|min_full" $A/src/run_dec.py | head -120
```

### [54] TOOL RESULT — Bash · 2026-10-26 13:42:54 UTC

```
{"stdout": "34:                  N_RANDOM_SUBSPACES, OFF_MANIFOLD, PROMPTS_DIR, RANDOM_SEED0, RANKS, RESULTS, SCAN_STEPS, THRESH,\n35:                  TRAIN_PAIR_CAP, UNITS, add_deviation, append_jsonl, read_json, read_jsonl, set_ram_limit,\n46:def load_prompts(unit: str) -> dict[str, dict[str, Any]]:\n51:def fam_of(r: dict[str, Any]) -> int:\n57:def gen_continuations(lm: Any, ids: list[int], n: int, max_new: int, fence: str, key: tuple) -> list[list[int]]:\n65:def labeller(unit: str):\n72:def stage_s3(unit: str, lm: Any, P: dict[str, dict[str, Any]], quick: bool) -> dict[str, Any]:\n119:    def cmass(k: str, c: str) -> float:\n161:def build_pairs(unit: str, P: dict[str, dict[str, Any]], cls: dict[str, int], classes: list[str]\n183:    def cross(S: list[str], B: list[str], cap: int) -> list[tuple[str, str]]:\n203:def recov(site: DecSite, L: int, pairs: list[tuple[str, str]], R: Any, full: dict[str, np.ndarray],\n206:    r = ST.recovery(ev[\"delta\"], full[\"delta\"], [p[0] for p in pairs], [p[1] for p in pairs], seed=seed)\n211:def by_class(site: DecSite, pairs: list[tuple[str, str]], ev_delta: np.ndarray, full_delta: np.ndarray,\n218:        r = ST.recovery(ev_delta[ix], full_delta[ix], [pairs[i][0] for i in ix], [pairs[i][1] for i in ix],\n219:                        n_boot=500)\n224:def strip(d: dict[str, Any]) -> dict[str, Any]:\n229:def stage_dec(unit: str, quick: bool = False, force_L: int | None = None) -> None:\n260:        \"decision_position\": \"last prefilled opening token (T10: token 10 ' def' after 'def solve(n, edges):'; GRID: \"\n307:    def _score(L: int) -> float:\n341:    tf_rows = []\n347:                rec_rank[k] = {**strip(r), \"by_class\": by_class(site, held, r[\"delta\"], full_h[\"delta\"], classes)}\n351:                tf_rows.append({\"unit\": unit, \"site\": \"dec\", \"layer\": L, \"fit\": f\"seed{sd}\", \"rank_k\": k,\n373:    true_d = np.array([r[\"delta\"] for r in tf_rows if r[\"fit\"] == \"seed0\" and r[\"rank_k\"] == kstar])\n423:           \"k_star\": kstar, \"scan\": scan, \"unit_tests\": ut, \"n_train_pairs\": len(train), \"n_held_pairs\": len(held),\n424:           \"recovery_by_rank\": rec_rank, \"rank1_only\": r1only, \"main\": main,\n425:           \"off_manifold_flag\": bool(main[\"recovery\"] and main[\"recovery\"] > OFF_MANIFOLD),\n433:    write_jsonl(DATA / f\"tf_{unit}_dec{rtag}.jsonl\", tf_rows)\n442:def unit_tests(site: DecSite, lm: Any, P: dict, train: list, held: list, unit: str) -> dict[str, Any]:\n471:        def ed(h: torch.Tensor) -> torch.Tensor:\n495:def label_controls(site: DecSite, P: dict, L: int, train: list, held: list, full_h: dict, classes: list[str],\n533:        def pt(s: str) -> int:\n558:            append_jsonl(DATA / f\"tf_{P[train[0][0]]['unit']}_dec_perm_L{L}.jsonl\",\n580:def reverse_test(site: DecSite, P: dict, L: int, Rk: torch.Tensor, classes: list[str], cls: dict, unit: str,\n598:    r = ST.recovery(das[\"delta\"], full[\"delta\"], [a for a, _ in rows], [b for _, b in rows], min_full=0.0)\n604:def baselines(site: DecSite, P: dict, L: int, held: list, full_h: dict, classes: list[str], cls: dict,\n621:        r = ST.recovery(ev[\"delta\"], full_h[\"delta\"][ix], [p[0] for p in hp], [p[1] for p in hp], n_boot=500)\n644:def iter7_side(site: DecSite, L: int, held: list, full_h: dict, Xn: torch.Tensor, lm: Any) -> dict[str, Any]:\n670:def main() -> None:", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [55] TOOL CALL — Bash · 2026-10-26 13:42:58 UTC

```
Read run_dec.py header, pairs, recovery and stage_dec:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40; sed -n 1,60p $A/src/run_dec.py; echo "....."; sed -n 155,240p $A/src/run_dec.py; echo "....."; sed -n 286,440p $A/src/run_dec.py
```

### [56] TOOL RESULT — Bash · 2026-10-26 13:42:58 UTC

```
{"stdout": "#!/usr/bin/env python3\n\"\"\"Decision-site stages for one unit (T10 on Qwen3-8B, GRID on gemma-3-4b-it), trained network:\n\nS3  teacher-force every prompt with the opening prefilled -> class distribution at d, top-50 tokens; token map\n    (iteration-7 maps + forced-token continuations for unmapped tokens with >= 2% mass); adherence for classes\n    without an iteration-7 record; class list; pairs (commit #1).\nS4  state cache at d (all blocks) + base keys/values (DecSite).\nU   unit tests U1-U3 (KV path), U9 (mini-fit).\nS6  scan (every 2nd block, rank 1, 2-fold leave-family-out CV, 100 steps) -> L*; main fits (3 seeds) + rank-1-only\n    fit; k*; controls c1 (50 Haar subspaces / rank), c2 (3 label-control refits), c4 (reverse), c5/c5b (projection on\n    natural PCs), c6/c6b (variance share), c7 (principal angles); baselines DiM-1, PCA-k, logit lens.\n\nUsage: python src/run_dec.py --unit T10|GRID [--quick]\n\"\"\"\n\nfrom __future__ import annotations\n\nimport argparse\nimport gc\nimport json\nimport sys\nimport time\nfrom pathlib import Path\nfrom typing import Any\n\nsys.path.insert(0, str(Path(__file__).resolve().parent))\n\nimport numpy as np\nimport torch\nfrom loguru import logger\n\nimport stats8 as ST\nfrom cfg8 import (BATCH_DEC, DATA, FIT_SEEDS, FIT_STEPS, HELD_PAIR_CAP, INPUTS, LABEL_CONTROL_SEEDS, LR, MAPS,\n                  N_RANDOM_SUBSPACES, OFF_MANIFOLD, PROMPTS_DIR, RANDOM_SEED0, RANKS, RESULTS, SCAN_STEPS, THRESH,\n                  TRAIN_PAIR_CAP, UNITS, add_deviation, append_jsonl, read_json, read_jsonl, set_ram_limit,\n                  setup_logging, u_stream, write_json, write_jsonl)\nfrom commit8 import commit, committed\nfrom das8 import ClassMap, DecSite, haar, kl, orth, pca_basis, principal_cosines, project_map, variance_share\nfrom engine8 import decode, load_lm, prefill, states_at\n\nT10_MAP0 = {66564: \"bfs\", 25792: \"dfs\", 1477: \"union_find\", 11300: \"union_find\"}\nGRID_MAP0 = {107: \"bfs\", 584: \"bfs\", 15204: \"bfs\", 236809: \"bfs\", 53227: \"dfs\"}\nFAM_KEY = {\"T10\": \"fam\", \"GRID\": \"fam\"}\n\n\ndef load_prompts(unit: str) -> dict[str, dict[str, Any]]:\n    f = PROMPTS_DIR / (\"t10_prompts.jsonl\" if unit == \"T10\" else \"grid_prompts.jsonl\")\n    return {r[\"key\"]: r for r in read_jsonl(f)}\n\n\ndef fam_of(r: dict[str, Any]) -> int:\n    f = r.get(\"fam\")\n    return int(f[1:]) - 1 if isinstance(f, str) else int(f)\n\n\n# ================================================================================================ S3\ndef gen_continuations(lm: Any, ids: list[int], n: int, max_new: int, fence: str, key: tuple) -> list[list[int]]:\n    pre = prefill(lm, ids)\n    us = [u_stream(*key, s) for s in range(n)]\n    res = decode(lm, [pre] * n, us, max_new, fence)\n.....\n    write_json(out_p, res)\n    logger.info(f\"S3 {unit}: classes {classes}; adherence {json.dumps({c: round(a['mean_own_class_mass_at_d'], 3) for c, a in adh.items()})}\")\n    return res\n\n\n# ================================================================================================ pairs\ndef build_pairs(unit: str, P: dict[str, dict[str, Any]], cls: dict[str, int], classes: list[str]\n                ) -> dict[str, Any]:\n    rng = np.random.default_rng(8002)\n    src_ok, excluded = [], []\n    for k, r in P.items():\n        if r[\"kind\"] != \"forced\" or r[\"Y\"] not in classes:\n            continue\n        if classes[cls[k]] != r[\"Y\"]:\n            excluded.append({\"key\": k, \"Y\": r[\"Y\"], \"tf_class\": classes[cls[k]]})\n            continue\n        src_ok.append(k)\n    if unit == \"T10\":\n        bases_tr = [k for k, r in P.items() if (r[\"kind\"] == \"twin\" and r[\"split\"] == \"train\") or\n                    (r[\"kind\"] == \"padtwin\" and r[\"split\"] == \"train\")]\n        bases_he = [k for k, r in P.items() if (r[\"kind\"] == \"twin\" and r[\"split\"] == \"held\") or\n                    (r[\"kind\"] == \"padtwin\" and r[\"split\"] == \"held\")]\n    else:\n        bases_tr = [k for k, r in P.items() if r[\"kind\"] == \"twin\" and r[\"split\"] == \"train\"]\n        bases_he = [k for k, r in P.items() if r[\"kind\"] == \"twin\" and r[\"split\"] == \"held\"]\n    src_tr = [k for k in src_ok if P[k][\"split\"] == \"train\"]\n    src_he = [k for k in src_ok if P[k][\"split\"] == \"held\"]\n\n    def cross(S: list[str], B: list[str], cap: int) -> list[tuple[str, str]]:\n        allp = [(s, b) for s in S for b in B if cls[s] != cls[b]]\n        if len(allp) <= cap:\n            return allp\n        strata: dict[tuple[int, int], list[tuple[str, str]]] = {}\n        for p in allp:\n            strata.setdefault((cls[p[0]], cls[p[1]]), []).append(p)\n        out = []\n        for key, ps in sorted(strata.items()):\n            n = max(1, int(round(cap * len(ps) / len(allp))))\n            ix = rng.choice(len(ps), size=min(n, len(ps)), replace=False)\n            out += [ps[i] for i in sorted(ix)]\n        return out\n    train = cross(src_tr, bases_tr, TRAIN_PAIR_CAP)\n    held = cross(src_he, bases_he, HELD_PAIR_CAP)\n    return {\"train\": train, \"held\": held, \"sources_train\": src_tr, \"sources_held\": src_he, \"bases_train\": bases_tr,\n            \"bases_held\": bases_he, \"excluded_sources\": excluded}\n\n\n# ================================================================================================ helpers\ndef recov(site: DecSite, L: int, pairs: list[tuple[str, str]], R: Any, full: dict[str, np.ndarray],\n          tgt_cls: dict | None = None, seed: int = 0) -> dict[str, Any]:\n    ev = site.evaluate(L, pairs, R, tgt_cls=tgt_cls)\n    r = ST.recovery(ev[\"delta\"], full[\"delta\"], [p[0] for p in pairs], [p[1] for p in pairs], seed=seed)\n    r[\"delta\"] = ev[\"delta\"]\n    return r\n\n\ndef by_class(site: DecSite, pairs: list[tuple[str, str]], ev_delta: np.ndarray, full_delta: np.ndarray,\n             classes: list[str]) -> dict[str, Any]:\n    out = {}\n    for ci, c in enumerate(classes):\n        ix = [i for i, p in enumerate(pairs) if site.cls[p[0]] == ci]\n        if not ix:\n            continue\n        r = ST.recovery(ev_delta[ix], full_delta[ix], [pairs[i][0] for i in ix], [pairs[i][1] for i in ix],\n                        n_boot=500)\n        out[c] = {k: v for k, v in r.items() if k != \"delta\"}\n    return out\n\n\ndef strip(d: dict[str, Any]) -> dict[str, Any]:\n    return {k: v for k, v in d.items() if k != \"delta\"}\n\n\n# ================================================================================================ main stage\ndef stage_dec(unit: str, quick: bool = False, force_L: int | None = None) -> None:\n    rtag = f\"_L{force_L}\" if force_L is not None else \"\"\n    out_p = RESULTS / f\"dec_{unit}{rtag}.json\"\n    if out_p.exists():\n        logger.info(f\"{out_p.name} exists; skipping\")\n        return\n    U = UNITS[unit]\n    fam = U[\"family\"]\n    P = load_prompts(unit)\n    lm = load_lm(fam)\n    t_all = time.time()\n    s3 = stage_s3(unit, lm, P, quick)\n.....\n                       \"full_state_flip_share_held96\": float(np.mean(fh[\"delta\"] > 0)),\n                       \"note\": \"full-state exchange moves < 10% of pairs by >= 1 nat: recovery undefined, not fitted\"}\n            logger.info(f\"scan {unit} L{L}: no full-state effect ({scan[L]['full_state_mean_delta_held96']:.3f})\")\n            continue\n        for fo in folds:\n            tp = [p for p in train if fam_of(P[p[0]]) != fo]\n            vp = [p for p in train if fam_of(P[p[0]]) == fo]\n            vp = [vp[i] for i in np.random.default_rng(L).choice(len(vp), size=min(96, len(vp)), replace=False)]\n            fit = site.fit(L, tp, [], seed=0, steps=SCAN_STEPS if not quick else 20, ranks=(1,), log_name=f\"scan L{L}\")\n            full = site.evaluate(L, vp, None)\n            r = recov(site, L, vp, fit[\"R\"][:, :1], full)\n            rec.append(r[\"recovery\"] if r[\"recovery\"] is not None else float(\"nan\"))\n        scan[L] = {\"cv_recovery_by_fold\": rec, \"cv_median_recovery\": float(np.nanmedian(rec)),\n                   \"full_state_mean_delta_held96\": float(fh[\"delta\"].mean()),\n                   \"full_state_flip_share_held96\": float(np.mean(fh[\"delta\"] > 0))}\n        logger.info(f\"scan {unit} L{L}: {scan[L]} ({time.time() - t0:.0f}s)\")\n    if force_L is not None or reuse_scan:\n        scan = read_json(RESULTS / f\"scan_{unit}.json\")\n        scan = {int(k): v for k, v in scan.items()}\n    else:\n        write_json(RESULTS / f\"scan_{unit}.json\", scan)\n    def _score(L: int) -> float:\n        v = scan[L][\"cv_median_recovery\"]\n        return round(float(v), 6) if (v is not None and np.isfinite(float(v))) else -np.inf\n    Lstar = max(scan_blocks, key=lambda L: (_score(L), -L)) if force_L is None else force_L\n    readout_proximal = Lstar >= N - 4\n    logger.info(f\"{unit}: L* = {Lstar} (readout-proximal {readout_proximal})\")\n    # ---- main fits\n    L = Lstar\n    full_h = site.evaluate(L, held, None)\n    fits = {}\n    for sd in (FIT_SEEDS if not quick else (0,)):\n        vf = fams_tr[sd % len(fams_tr)]\n        tp = [p for p in train if fam_of(P[p[0]]) != vf]\n        vp = [p for p in train if fam_of(P[p[0]]) == vf]\n        vp = [vp[i] for i in np.random.default_rng(sd).choice(len(vp), size=min(96, len(vp)), replace=False)]\n        mp = MAPS / f\"{unit}_dec_L{L}_seed{sd}.pt\"\n        if mp.exists() and force_L is None:\n            fits[sd] = {\"R\": torch.load(mp), \"best_step\": None, \"note\": \"map reused from an earlier run of this \"\n                        \"stage (identical code, seed and pairs) that crashed after fitting\", \"hist\": []}\n            continue\n        fits[sd] = site.fit(L, tp, vp, seed=sd, steps=FIT_STEPS if not quick else 40, log_name=f\"{unit} L{L} s{sd}\")\n        torch.save(fits[sd][\"R\"], mp)\n    vf = fams_tr[0]\n    tp = [p for p in train if fam_of(P[p[0]]) != vf]\n    vp = [p for p in train if fam_of(P[p[0]]) == vf][:96]\n    r1p = MAPS / f\"{unit}_dec_L{L}_rank1only.pt\"\n    if r1p.exists() and force_L is None:\n        fit_r1 = {\"R\": torch.load(r1p)}\n    else:\n        fit_r1 = site.fit(L, tp, vp, seed=0, steps=FIT_STEPS if not quick else 40, ranks=(1,),\n                          log_name=f\"{unit} r1only\")\n        torch.save(fit_r1[\"R\"], r1p)\n    R0 = fits[0][\"R\"]\n    # ---- held-out recovery by rank / seed / class\n    tf_rows = []\n    rec_rank: dict[int, Any] = {}\n    for sd, f in fits.items():\n        for k in RANKS:\n            r = recov(site, L, held, f[\"R\"][:, :k], full_h, seed=sd)\n            if sd == 0:\n                rec_rank[k] = {**strip(r), \"by_class\": by_class(site, held, r[\"delta\"], full_h[\"delta\"], classes)}\n            else:\n                rec_rank.setdefault(f\"seed{sd}\", {})[k] = strip(r)\n            for i, p in enumerate(held):\n                tf_rows.append({\"unit\": unit, \"site\": \"dec\", \"layer\": L, \"fit\": f\"seed{sd}\", \"rank_k\": k,\n                                \"src\": p[0], \"base\": p[1], \"class_src\": classes[cls[p[0]]],\n                                \"class_base\": classes[cls[p[1]]], \"delta\": float(r[\"delta\"][i]),\n                                \"delta_full\": float(full_h[\"delta\"][i])})\n    best = max(RANKS, key=lambda k: rec_rank[k][\"recovery\"] or -9)\n    kstar = min(k for k in RANKS if (rec_rank[k][\"recovery\"] or -9) >= 0.9 * rec_rank[best][\"recovery\"])\n    r1only = strip(recov(site, L, held, fit_r1[\"R\"][:, :1], full_h))\n    Rk = R0[:, :kstar]\n    main = rec_rank[kstar]\n    logger.info(f\"{unit}: k* = {kstar}; recovery {main['recovery']:.3f} CI {main['ci95']}\")\n    # ---- c1 random subspaces\n    c1 = {}\n    for k in RANKS:\n        vals = []\n        for i in range(N_RANDOM_SUBSPACES if not quick else 5):\n            r = recov(site, L, held, haar(RANDOM_SEED0 + i, lm.D, k), full_h)\n            vals.append(r[\"recovery\"])\n        vals = np.array([v for v in vals if v is not None])\n        c1[k] = {\"median\": float(np.median(vals)), \"p95\": float(np.percentile(vals, 95)), \"max\": float(vals.max()),\n                 \"n\": int(len(vals)), \"pass\": bool(np.median(vals) <= THRESH[\"c1_median_max\"])}\n        logger.info(f\"c1 {unit} k{k}: {c1[k]}\")\n    # ---- c2 label controls\n    true_d = np.array([r[\"delta\"] for r in tf_rows if r[\"fit\"] == \"seed0\" and r[\"rank_k\"] == kstar])\n    c2 = label_controls(site, P, L, train, held, full_h, classes, cls, main, kstar, fams_tr, quick, true_d)\n    # ---- c4 reverse\n    c4 = reverse_test(site, P, L, Rk, classes, cls, unit, pairs)\n    # ---- c5 / c6 natural basis\n    twins = [k for k in keys_all if P[k][\"kind\"] == \"twin\"]\n    Xn = torch.stack([site.H[k][L] for k in twins])\n    allnat = [k for k in keys_all if P[k][\"kind\"] in (\"twin\", \"forced\", \"ban\", \"top5\", \"instr_novel\", \"seed_rand1\",\n                                                       \"seed_rand2\", \"instr_new\", \"padtwin\", \"p0\")]\n    Xb = torch.stack([site.H[k][L] for k in allnat])\n    c5, c6 = {}, {}\n    for tag, X in ((\"twins\", Xn), (\"twins_forced_bans\", Xb)):\n        U64, S = pca_basis(X, 64)\n        Rp = project_map(Rk, U64)\n        if Rp is None:\n            c5[tag] = {\"retention\": 0.0, \"note\": \"projection lost rank\", \"n_states\": int(X.shape[0])}\n        else:\n            rp = recov(site, L, held, Rp, full_h)\n            c5[tag] = {\"recovery_proj\": rp[\"recovery\"], \"retention\": (rp[\"recovery\"] or 0) / main[\"recovery\"]\n                       if main[\"recovery\"] else None, \"n_states\": int(X.shape[0])}\n        share = variance_share(Rk, S)\n        rs = np.array([variance_share(haar(50000 + i, lm.D, kstar), S) for i in range(1000)])\n        c6[tag] = {\"share\": share, \"random_p95\": float(np.percentile(rs, 95)), \"random_median\": float(np.median(rs)),\n                   \"percentile\": float((rs < share).mean() * 100), \"pass\": bool(share > np.percentile(rs, 95)),\n                   \"n_states\": int(X.shape[0])}\n    c5[\"pass\"] = bool((c5[\"twins\"].get(\"retention\") or 0) >= THRESH[\"c5_min\"])\n    c5[\"pass_b\"] = bool((c5[\"twins_forced_bans\"].get(\"retention\") or 0) >= THRESH[\"c5_min\"])\n    # ---- c7 principal angles\n    cos = []\n    sds = sorted(fits)\n    for a in range(len(sds)):\n        for b in range(a + 1, len(sds)):\n            cos.append(float(principal_cosines(fits[sds[a]][\"R\"][:, :kstar], fits[sds[b]][\"R\"][:, :kstar])[0]))\n    rnd = [float(principal_cosines(haar(60000 + i, lm.D, kstar), haar(61000 + i, lm.D, kstar))[0]) for i in range(1000)]\n    c7 = {\"first_cosines\": cos, \"median_first_cosine\": float(np.median(cos)) if cos else None,\n          \"random_p99\": float(np.percentile(rnd, 99)),\n          \"pass\": bool(cos and np.median(cos) >= THRESH[\"c7_cos_min\"] and np.median(cos) > np.percentile(rnd, 99))}\n    # ---- baselines: DiM-1 per class, PCA-k, logit lens\n    try:\n        base_tab = baselines(site, P, L, held, full_h, classes, cls, twins, lm, cmap, Rk, kstar)\n    except (RuntimeError, ValueError, KeyError, IndexError) as e:\n        logger.error(f\"baselines failed: {e}\")\n        base_tab = {\"error\": str(e)}\n    # ---- iteration-7 Gemma subspaces (side table)\n    try:\n        side = iter7_side(site, L, held, full_h, Xn, lm) if unit == \"GRID\" else None\n    except (RuntimeError, ValueError, KeyError, IndexError, TypeError, AttributeError) as e:\n        logger.error(f\"iter7 side table failed: {e}\")\n        side = {\"error\": str(e)}\n    res = {\"unit\": unit, \"family\": fam, \"classes\": classes, \"L_star\": Lstar, \"readout_proximal\": readout_proximal,\n           \"k_star\": kstar, \"scan\": scan, \"unit_tests\": ut, \"n_train_pairs\": len(train), \"n_held_pairs\": len(held),\n           \"recovery_by_rank\": rec_rank, \"rank1_only\": r1only, \"main\": main,\n           \"off_manifold_flag\": bool(main[\"recovery\"] and main[\"recovery\"] > OFF_MANIFOLD),\n           \"full_state_held\": {\"mean_delta\": float(full_h[\"delta\"].mean()),\n                               \"flip_share\": float(np.mean(full_h[\"delta\"] > 0)),\n                               \"share_abs_ge_1\": float(np.mean(np.abs(full_h[\"delta\"]) >= 1))},\n           \"fits\": {str(s): {k: v for k, v in f.items() if k not in (\"R\", \"hist\")} | {\"hist_tail\": f.get(\"hist\", [])[-3:]}\n                    for s, f in fits.items()},\n           \"c1\": c1, \"c2\": c2, \"c4\": c4, \"c5\": c5, \"c6\": c6, \"c7\": c7, \"baselines\": base_tab, \"iter7_side\": side,\n           \"seconds\": round(time.time() - t_all, 1)}\n    write_jsonl(DATA / f\"tf_{unit}_dec{rtag}.jsonl\", tf_rows)\n    torch.save({k: site.H[k].to(torch.bfloat16) for k in keys_all}, RESULTS.parent / \"cache\" / f\"states_{unit}_dec_trained.pt\")\n    torch.save({k: site.q[k] for k in keys_all}, RESULTS.parent / \"cache\" / f\"q_{unit}_dec_trained.pt\")\n    write_json(out_p, res)\n    logger.info(f\"dec {unit} done in {time.time() - t_all:.0f}s\")\n    site.free()\n    lm.free()", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [57] THINKING · 2026-10-26 13:43:56 UTC

```
Since stage_dec builds recovery tables purely from per-pair Deltas, which the teacher-forced dataset already stores, the notebook can replay this step using those stored Deltas instead of calling the GPU's site.evaluate. Now I'll check whether the prompt file includes readable source and base prompt text so the demo can display an actual pair.
```

### [58] TOOL CALL — Bash · 2026-10-26 13:43:56 UTC

```
Inspect T10 prompt records and generation input text:
python3 - <<'EOF'
import json, re
A="/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40"
rows=[json.loads(l) for l in open(A+"/prompts/t10_prompts.jsonl")]
print(len(rows), "keys:", sorted(rows[0].keys()))
for r in rows[:1]:
    print({k:(v if not isinstance(v,list) else f"list[{len(v)}]") for k,v in r.items()})
kinds={}
for r in rows: kinds[r["kind"]]=kinds.get(r["kind"],0)+1
print(kinds)
# check presence of text fields
for k in rows[0]:
    if isinstance(rows[0][k],str) and len(rows[0][k])>40: print("TEXT FIELD",k, repr(rows[0][k][:300]))
d=json.load(open(A+"/full_method_out.json"))
ex={x["dataset"]:x["examples"] for x in d["datasets"]}["T10_dec_generation"][0]
print("GEN INPUT len", len(ex["input"]))
print(ex["input"][:1500])
EOF
```

### [59] TOOL RESULT — Bash · 2026-10-26 13:43:56 UTC

````
{"stdout": "290 keys: ['P', 'Y', 'd', 'dec_ids', 'fam', 'family', 'ids', 'key', 'kind', 'name_idx', 'p0', 'p1', 'prompt_sha256', 'segment', 'spec_end', 'split', 'unit']\n{'unit': 'T10', 'family': 'qwen', 'kind': 'forced', 'ids': 'list[169]', 'P': 169, 'p0': 3, 'p1': 15, 'spec_end': 160, 'prompt_sha256': 'd3f9d01ff280dc34a8e68226c66f6eed36527edaf3842ebfb9dee91662e63e0f', 'key': 'T10|forced|k0|j0|bfs', 'fam': 0, 'name_idx': 0, 'Y': 'bfs', 'segment': 'Implement breadth-first search (BFS) for this task.', 'split': 'train', 'dec_ids': 'list[180]', 'd': 179}\n{'forced': 60, 'padtwin': 60, 'twin': 160, 'ban': 5, 'p0': 1, 'seed_rand1': 1, 'seed_rand2': 1, 'instr_new': 1, 'instr_novel': 1}\nTEXT FIELD prompt_sha256 'd3f9d01ff280dc34a8e68226c66f6eed36527edaf3842ebfb9dee91662e63e0f'\nTEXT FIELD segment 'Implement breadth-first search (BFS) for this task.'\nGEN INPUT len 1372\n[T10 | dec site | target class bfs | slot 0] BASE PROMPT: user\nBaby is not allowed here. . . . . . . .\n\nTask: write a Python function solve(n, edges) that returns the number of connected components of an undirected graph. The nodes are the integers 0 to n - 1, with 1 <= n <= 300. The argument edges is a list of pairs [u, v] with 0 <= u, v < n and u != v, each joining nodes u and v; 0 <= len(edges) <= 1500 and no pair of nodes is joined twice. A node with no edges forms a component on its own.\n\nUse only the Python standard library. Return only one ```python code block containing the function solve and any helpers, with no example usage and no explanation.\nassistant\n<think>\n\n</think>\n\n || SOURCE PROMPT (edit source): user\nYour solution should use breadth-first search (BFS).\n\nTask: write a Python function solve(n, edges) that returns the number of connected components of an undirected graph. The nodes are the integers 0 to n - 1, with 1 <= n <= 300. The argument edges is a list of pairs [u, v] with 0 <= u, v < n and u != v, each joining nodes u and v; 0 <= len(edges) <= 1500 and no pair of nodes is joined twice. A node with no edges forms a component on its own.\n\nUse only the Python standard library. Return only one ```python code block containing the function solve and any helpers, with no example usage and no explanation.\nassistant\n<think>\n\n</think>", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
````

### [60] THINKING · 2026-10-26 13:44:54 UTC

```
I'll add each prompt's readable `segment` to the mini data so the notebook can display actual source and base prompts, then check the geometry and token-map metadata feeding the centroid plot and decision-token explanation.
```

### [61] TOOL CALL — Bash · 2026-10-26 13:44:54 UTC

```
Inspect geometry, token map, verdict and mediation metadata:
python3 - <<'EOF'
import json
A="/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40"
d=json.load(open(A+"/full_method_out.json"))
md=d["metadata"]
print(json.dumps(md["geometry"])[:3600])
print()
print(json.dumps(md["s3_T10"]))
print()
print(json.dumps(md["verdicts"]["T10-dec"])[:1500])
print()
print("mediation_T10 keys:", list(md["mediation_T10"].keys()))
dirs=md["mediation_T10"]["directions"]; k0=list(dirs)[0]; print("direction example:", k0, json.dumps(dirs[k0])[:400], len(dirs))
print("gen_T10_dec keys:", list(md["gen_T10_dec"].keys()), "pooled:", json.dumps(md["gen_T10_dec"]["pooled"]))
print("gen classes dfs DAS:", json.dumps(md["gen_T10_dec"]["classes"]["dfs"]["arms"]["DAS"]))
print("gen dfs mcnemar:", json.dumps(md["gen_T10_dec"]["classes"]["dfs"]["mcnemar_DAS_vs_RAND"]))
print("band_T10 keys:", list(md["band_T10"].keys()))
print("dec_GRID c2 keys:", list(md["dec_GRID"]["c2"].keys()))
EOF
```

### [62] TOOL RESULT — Bash · 2026-10-26 13:44:54 UTC

```
{"stdout": "{\"T10\": {\"unit\": \"T10\", \"L\": 22, \"mds_stress1\": 0.014684073126979015, \"isomap_mean_geodesic_between_groups\": {\"ban|bfs\": 17.371543884277344, \"ban|dfs\": 10.006659507751465, \"ban|instr\": 4.124963760375977, \"ban|p0\": 3.7493724822998047, \"ban|padtwin\": 3.4246509075164795, \"ban|seed\": 3.1308951377868652, \"ban|twin\": 3.7580552101135254, \"ban|union_find\": 5.419531345367432, \"bfs|dfs\": 9.39411735534668, \"bfs|instr\": 18.728302001953125, \"bfs|p0\": 18.272287368774414, \"bfs|padtwin\": 17.9774227142334, \"bfs|seed\": 16.09488296508789, \"bfs|twin\": 18.185338973999023, \"bfs|union_find\": 13.294388771057129, \"dfs|instr\": 13.391087532043457, \"dfs|p0\": 13.184202194213867, \"dfs|padtwin\": 12.773946762084961, \"dfs|seed\": 11.977978706359863, \"dfs|twin\": 13.098454475402832, \"dfs|union_find\": 13.967948913574219, \"instr|p0\": 1.7473082542419434, \"instr|padtwin\": 1.7902084589004517, \"instr|seed\": 2.7918548583984375, \"instr|twin\": 2.0452682971954346, \"instr|union_find\": 5.788041114807129, \"p0|padtwin\": 0.5837591886520386, \"p0|seed\": 2.301680564880371, \"p0|twin\": 1.0948117971420288, \"p0|union_find\": 5.332024574279785, \"padtwin|seed\": 1.9613285064697266, \"padtwin|twin\": 1.185676097869873, \"padtwin|union_find\": 5.037161827087402, \"seed|twin\": 2.2351462841033936, \"seed|union_find\": 3.1546199321746826, \"twin|union_find\": 5.2450785636901855}, \"implemented_counts\": {\"bfs\": 34, \"dfs\": 35, \"union_find\": 87}, \"title\": \"handle coordinates (not certified)\", \"n_prompts\": 290, \"group_centroids_mds\": {\"ban\": [0.6389055831045842, 0.3079634418554975], \"bfs\": [7.488131981301348, 11.24505650506932], \"dfs\": [9.376249617038068, 2.945068069058481], \"instr\": [-1.8594198473666737, -1.4813636030728214], \"p0\": [-1.4880910977824495, -1.638383722343357], \"padtwin\": [-1.3826745515321648, -1.2977389335618386], \"seed\": [-1.2858953442911871, 0.10520815710221187], \"twin\": [-1.363672794562234, -1.5898728817784007], \"union_find\": [-1.57776590896629, 2.564619151035271]}}, \"GRID\": {\"unit\": \"GRID\", \"L\": 16, \"mds_stress1\": 0.02698726463026765, \"isomap_mean_geodesic_between_groups\": {\"astar_gbfs|ban\": 147.06614685058594, \"astar_gbfs|bfs\": 76.74359130859375, \"astar_gbfs|dfs\": 175.17144775390625, \"astar_gbfs|iddfs\": 80.10429382324219, \"astar_gbfs|instr\": 183.15927124023438, \"astar_gbfs|top5\": 179.9905242919922, \"astar_gbfs|twin\": 130.97483825683594, \"ban|bfs\": 208.6461944580078, \"ban|dfs\": 119.48873138427734, \"ban|iddfs\": 121.0588150024414, \"ban|instr\": 59.114646911621094, \"ban|top5\": 50.5816764831543, \"ban|twin\": 67.30671691894531, \"bfs|dfs\": 241.2654266357422, \"bfs|iddfs\": 145.44131469726562, \"bfs|instr\": 249.2532501220703, \"bfs|top5\": 246.08450317382812, \"bfs|twin\": 197.06878662109375, \"dfs|iddfs\": 133.65306091308594, \"dfs|instr\": 116.0424575805664, \"dfs|top5\": 112.87371826171875, \"dfs|twin\": 91.87931823730469, \"iddfs|instr\": 141.64088439941406, \"iddfs|top5\": 138.47213745117188, \"iddfs|twin\": 92.9748764038086, \"instr|top5\": 12.72221851348877, \"instr|twin\": 55.64067459106445, \"top5|twin\": 56.50011444091797}, \"implemented_counts\": {\"dfs\": 21, \"bfs\": 7}, \"title\": \"handle coordinates (not certified)\", \"n_prompts\": 207, \"group_centroids_mds\": {\"astar_gbfs\": [-56.553279078534274, 26.29968978815247], \"ban\": [-4.891307844525906, -23.40007061948787], \"bfs\": [-109.42247899278027, 31.41764243557845], \"dfs\": [92.75505659966902, -29.352589544323695], \"iddfs\": [1.7494285824251237, 28.803113378836407], \"instr\": [-11.81167466754762, -12.054034056155581], \"top5\": [-4.298605453376605, -18.13830834856963], \"twin\": [12.249935642733016, -8.3013702138559]}}}\n\n{\"unit\": \"T10\", \"unmapped_candidates\": {\"1936\": {\"token\": \" build\", \"max_mass\": 0.02277, \"labels\": {\"dfs\": 10}, \"class\": \"dfs\"}}, \"token_map\": {\"66564\": \"bfs\", \"25792\": \"dfs\", \"1477\": \"union_find\", \"11300\": \"union_find\", \"1936\": \"dfs\"}, \"class_sets\": {\"bfs\": [66564], \"dfs\": [25792, 1936], \"union_find\": [1477, 11300]}, \"adherence\": {\"bfs\": {\"mean_own_class_mass_at_d\": 0.9940987557172776, \"n_forced\": 20, \"kept\": true}, \"dfs\": {\"mean_own_class_mass_at_d\": 0.9999776870012284, \"n_forced\": 20, \"kept\": true}, \"union_find\": {\"mean_own_class_mass_at_d\": 0.9999999433755875, \"n_forced\": 20, \"free_labels\": {\"union_find\": 20}, \"own_label_share\": 1.0, \"n_free\": 20, \"kept\": true}}, \"classes\": [\"bfs\", \"dfs\", \"union_find\"], \"seconds\": 81.9}\n\n{\"verdict\": \"NO HANDLE\", \"V0_by_class\": {\"bfs\": {\"gen_recovery\": null, \"pass_ratio\": 0.24, \"mcnemar_p_das_gt_rand\": 0.03125, \"V0_class\": false, \"full_minus_base_correct\": 0}, \"dfs\": {\"gen_recovery\": 14.5, \"pass_ratio\": 1.2, \"mcnemar_p_das_gt_rand\": 1.862645149230957e-09, \"V0_class\": true, \"full_minus_base_correct\": 2}}, \"note_generation_recovery\": \"generation recovery divides by FULL - BASE correct counts; when the full-state exchange moves <= 2 slots the ratio is not a fraction of a ceiling\", \"V0\": false, \"V0_parts\": {\"tf_recovery\": true, \"gen_recovery\": true, \"pass_ratio\": false, \"mcnemar_das_gt_rand\": true}, \"controls\": {\"c1\": true, \"c2\": false, \"c3\": false, \"c4\": false, \"c5\": false, \"c6\": true, \"c7\": true}, \"failed_controls\": {\"c2\": \"map-class capacity\", \"c3\": \"map-class capacity\", \"c4\": \"dormant/off-manifold\", \"c5\": \"dormant/off-manifold\"}, \"untested_controls\": [], \"off_manifold_flag\": true, \"tf_recovery\": 8.432892175097768, \"tf_ci95\": [5.944438813564415, 11.296062773717395], \"gen_recovery\": 17.0, \"pass_ratio\": 0.72, \"mcnemar\": {\"a_only\": 34, \"b_only\": 0, \"p_two_sided\": 1.1641532182693481e-10, \"p_one_sided_a_gt_b\": 5.820766091346741e-11}, \"c1_at_kstar\": {\"median\": -0.005335866348852657, \"p95\": 0.014967972142734435, \"max\": 0.019018203906749454, \"n\": 50, \"pass\": true}}\n\nmediation_T10 keys: ['unit', 'alpha', 'k_star_band', 'L_star', 'k_star_dec', 'dbar_crosscheck_keys', 'spearman_escape_pooled', 'spearman_escape_d', 'spearman_escape_c', 'partial_spearman_ctrl_normD_band', 'partial_spearman_ctrl_normD_block35', 'spearman_pi_bfs', 'spearman_pi_dfs', 'placebo_random_predictor', 'directions', 'top10_escaping', 'dec_clamp_reach_rate', 'n_dec_clamp_rows', 'prospective_pi', 'clamp_reach']\ndirection example: 9101 {\"seed\": 9101, \"pi\": -0.7775299549102783, \"pi_by_class\": {\"bfs\": -0.7775299549102783, \"dfs\": -1.024617075920105}, \"norm_D_band\": 46.52405471801758, \"norm_D_block35\": 443.55730590820315, \"z_norm\": 0.5105188488960266, \"escape_d\": 0.0, \"escape_c\": 0.0, \"escape_pooled\": 0.0, \"n_d\": 10, \"n_c\": 10} 40\ngen_T10_dec keys: ['unit', 'site', 'classes', 'pooled'] pooled: {\"DAS\": 34, \"BASE\": 0, \"FULL\": 2, \"RAND\": 0, \"n_DAS\": 60, \"gen_recovery\": 17.0, \"pass_ratio\": 0.72, \"mcnemar_DAS_vs_RAND\": {\"a_only\": 34, \"b_only\": 0, \"p_two_sided\": 1.1641532182693481e-10, \"p_one_sided_a_gt_b\": 5.820766091346741e-11}}\ngen classes dfs DAS: {\"n_planned\": 30, \"n\": 30, \"correct_target\": 29, \"share\": 0.9666666666666667, \"wilson95\": [0.8332924860304112, 0.9940915620051425], \"attempted_target\": 29, \"pass_rate\": 1.0, \"other_share\": 0.0, \"labels\": {\"dfs\": 29, \"union_find\": 1}, \"correct_default\": 1, \"invalid\": 0}\ngen dfs mcnemar: {\"a_only\": 29, \"b_only\": 0, \"p_two_sided\": 3.725290298461914e-09, \"p_one_sided_a_gt_b\": 1.862645149230957e-09}\nband_T10 keys: ['unit', 'band', 'n_train_pairs', 'n_held_subsample', 'U4', 'timing', 'k_star', 'recovery_by_rank', 'main', 'off_manifold_flag', 'fits', 'c2', 'c1', 'c4', 'c5', 'c6', 'c7', 'iter7_handle_first_cosines']\ndec_GRID c2 keys: ['note', 'shuffle0', 'shuffle1', 'shuffle2', 'pass', 'primary_statistic']", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [63] THINKING · 2026-10-26 13:45:48 UTC

```
I'll write a small stdlib script to build mini_demo_data.json, subsetting 100 of the 600 held-out pairs (44/44/6/6 across the four strata) via round-robin selection with interleaved ordering to preserve coverage and overall recovery.
```

### [64] TOOL CALL — Write · 2026-10-26 13:45:48 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/build_mini_demo_data.py

#!/usr/bin/env python3
"""Build mini_demo_data.json for code_demo.ipynb from the artifact's full_method_out.json (standard library only).

The demo uses ONE dataset of the artifact's output: `T10_dec_teacher_forced` (600 held-out teacher-forced pairs of the
Qwen3-8B T10 decision site, block L* = 22; per pair the full-state Delta and the DAS Delta of every fit seed and rank).
100 pairs are kept, stratified by (source class, base class) and spread over as many source and base prompts as
possible; they are ordered so that every prefix is still mixed across strata (the notebook's N_PAIRS takes a prefix).

The metadata block keeps the artifact's own result JSONs that the CPU analysis stages read (per-site TF results,
controls, random-init control, generation tables, scan profiles, geometry, mediation, K2), plus the readable prompt
segment of every source / base prompt used by the kept pairs.

Usage: python3 build_mini_demo_data.py --artifact_dir <folder holding full_method_out.json and prompts/>
"""

import argparse
import json
import random
import re
from pathlib import Path

DATASET = "T10_dec_teacher_forced"
N_KEEP = 100
STRATA_TARGET = {("bfs", "union_find"): 44, ("dfs", "union_find"): 44, ("bfs", "dfs"): 6, ("union_find", "dfs"): 6}
SEED = 0
META_KEYS = ("method_name", "description", "verdicts", "K2", "mediation", "commit_chain", "deviations", "dec_T10",
             "band_T10", "dec_GRID", "dec_T10_L24", "rinit_T10", "rinit_GRID", "rinit_T10_band", "rinit_T10_L24",
             "s3_T10", "s3_GRID", "geometry", "novelty_audit", "costs", "post_T10", "unit_tests_cpu",
             "unit_tests_gpu_T10", "unit_tests_gpu_GRID", "mediation_T10", "rederive", "scan_T10", "scan_GRID",
             "gen_T10_dec", "gen_T10_band", "gen_GRID_dec")
PAIR_RE = re.compile(r"source=(\S+) base=(\S+)")


def pick_stratum(rows, n, base_use, rng):
    """Round-robin over source prompts; from each source take the pair whose base prompt is least used so far."""
    by_src = {}
    for r in rows:
        by_src.setdefault(PAIR_RE.search(r["input"]).group(1), []).append(r)
    srcs = sorted(by_src)
    rng.shuffle(srcs)
    out = []
    while len(out) < n and any(by_src.values()):
        for s in srcs:
            if len(out) >= n or not by_src[s]:
                continue
            cand = by_src[s]
            rng.shuffle(cand)
            cand.sort(key=lambda r: base_use.get(PAIR_RE.search(r["input"]).group(2), 0))
            r = cand.pop(0)
            base_use[PAIR_RE.search(r["input"]).group(2)] = base_use.get(PAIR_RE.search(r["input"]).group(2), 0) + 1
            out.append(r)
    return out


def interleave(chosen):
    """Order the kept pairs so that every prefix stays close to the target stratum shares."""
    total = sum(len(v) for v in chosen.values())
    taken = {k: 0 for k in chosen}
    order = []
    for i in range(total):
        k = min((k for k in chosen if taken[k] < len(chosen[k])),
                key=lambda k: (taken[k] + 1) / len(chosen[k]))
        order.append(chosen[k][taken[k]])
        taken[k] += 1
    return order


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact_dir", required=True, help="artifact folder (full_method_out.json, prompts/)")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "mini_demo_data.json"))
    a = ap.parse_args()
    art = Path(a.artifact_dir)
    full = json.loads((art / "full_method_out.json").read_text())
    ds = {d["dataset"]: d["examples"] for d in full["datasets"]}
    rows = ds[DATASET]
    strata = {}
    for r in rows:
        strata.setdefault((r["metadata_class_src"], r["metadata_class_base"]), []).append(r)
    rng = random.Random(SEED)
    base_use = {}
    chosen = {k: pick_stratum(list(strata[k]), n, base_use, rng) for k, n in STRATA_TARGET.items()}
    examples = interleave(chosen)
    assert len(examples) == N_KEEP, len(examples)
    # readable prompt segments (the one line that differs between prompts) for every source / base key kept
    prompts = {}
    for line in (art / "prompts" / "t10_prompts.jsonl").read_text().splitlines():
        if line.strip():
            p = json.loads(line)
            prompts[p["key"]] = p
    keys = sorted({k for r in examples for k in PAIR_RE.search(r["input"]).groups()})
    segs = {k: {"segment": prompts[k]["segment"], "kind": prompts[k]["kind"], "split": prompts[k]["split"]}
            for k in keys}
    # the shared task text, as decoded in the artifact's own generation rows (BASE PROMPT of slot 0)
    g0 = ds["T10_dec_generation"][0]["input"]
    task = g0[g0.index("Task:"):g0.index("explanation.") + len("explanation.")]
    meta = {k: full["metadata"][k] for k in META_KEYS if k in full["metadata"]}
    meta["demo_subset"] = {
        "source_dataset": DATASET, "n_source_examples": len(rows), "n_selected": len(examples),
        "strata_available": {f"{a_}->{b_}": len(v) for (a_, b_), v in sorted(strata.items())},
        "strata_selected": {f"{a_}->{b_}": len(v) for (a_, b_), v in sorted(chosen.items())},
        "n_unique_sources": len({PAIR_RE.search(r["input"]).group(1) for r in examples}),
        "n_unique_bases": len({PAIR_RE.search(r["input"]).group(2) for r in examples}),
        "selection": "stratified by (class_src, class_base); round-robin over source prompts, least-used base first; "
                     "strata interleaved so every prefix stays mixed", "seed": SEED}
    meta["prompt_segments"] = segs
    meta["t10_task_text"] = task
    out = {"metadata": meta, "datasets": [{"dataset": DATASET, "examples": examples}]}
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps(meta["demo_subset"], indent=1))
    print(f"wrote {a.out}: {Path(a.out).stat().st_size / 1e3:.0f} kB")


if __name__ == "__main__":
    main()
```

### [65] TOOL RESULT — Write · 2026-10-26 13:45:48 UTC

```
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/build_mini_demo_data.py", "content": "#!/usr/bin/env python3\n\"\"\"Build mini_demo_data.json for code_demo.ipynb from the artifact's full_method_out.json (standard library only).\n\nThe demo uses ONE dataset of the artifact's output: `T10_dec_teacher_forced` (600 held-out teacher-forced pairs of the\nQwen3-8B T10 decision site, block L* = 22; per pair the full-state Delta and the DAS Delta of every fit seed and rank).\n100 pairs are kept, stratified by (source class, base class) and spread over as many source and base prompts as\npossible; they are ordered so that every prefix is still mixed across strata (the notebook's N_PAIRS takes a prefix).\n\nThe metadata block keeps the artifact's own result JSONs that the CPU analysis stages read (per-site TF results,\ncontrols, random-init control, generation tables, scan profiles, geometry, mediation, K2), plus the readable prompt\nsegment of every source / base prompt used by the kept pairs.\n\nUsage: python3 build_mini_demo_data.py --artifact_dir <folder holding full_method_out.json and prompts/>\n\"\"\"\n\nimport argparse\nimport json\nimport random\nimport re\nfrom pathlib import Path\n\nDATASET = \"T10_dec_teacher_forced\"\nN_KEEP = 100\nSTRATA_TARGET = {(\"bfs\", \"union_find\"): 44, (\"dfs\", \"union_find\"): 44, (\"bfs\", \"dfs\"): 6, (\"union_find\", \"dfs\"): 6}\nSEED = 0\nMETA_KEYS = (\"method_name\", \"description\", \"verdicts\", \"K2\", \"mediation\", \"commit_chain\", \"deviations\", \"dec_T10\",\n             \"band_T10\", \"dec_GRID\", \"dec_T10_L24\", \"rinit_T10\", \"rinit_GRID\", \"rinit_T10_band\", \"rinit_T10_L24\",\n             \"s3_T10\", \"s3_GRID\", \"geometry\", \"novelty_audit\", \"costs\", \"post_T10\", \"unit_tests_cpu\",\n             \"unit_tests_gpu_T10\", \"unit_tests_gpu_GRID\", \"mediation_T10\", \"rederive\", \"scan_T10\", \"scan_GRID\",\n             \"gen_T10_dec\", \"gen_T10_band\", \"gen_GRID_dec\")\nPAIR_RE = re.compile(r\"source=(\\S+) base=(\\S+)\")\n\n\ndef pick_stratum(rows, n, base_use, rng):\n    \"\"\"Round-robin over source prompts; from each source take the pair whose base prompt is least used so far.\"\"\"\n    by_src = {}\n    for r in rows:\n        by_src.setdefault(PAIR_RE.search(r[\"input\"]).group(1), []).append(r)\n    srcs = sorted(by_src)\n    rng.shuffle(srcs)\n    out = []\n    while len(out) < n and any(by_src.values()):\n        for s in srcs:\n            if len(out) >= n or not by_src[s]:\n                continue\n            cand = by_src[s]\n            rng.shuffle(cand)\n            cand.sort(key=lambda r: base_use.get(PAIR_RE.search(r[\"input\"]).group(2), 0))\n            r = cand.pop(0)\n            base_use[PAIR_RE.search(r[\"input\"]).group(2)] = base_use.get(PAIR_RE.search(r[\"input\"]).group(2), 0) + 1\n            out.append(r)\n    return out\n\n\ndef interleave(chosen):\n    \"\"\"Order the kept pairs so that every prefix stays close to the target stratum shares.\"\"\"\n    total = sum(len(v) for v in chosen.values())\n    taken = {k: 0 for k in chosen}\n    order = []\n    for i in range(total):\n        k = min((k for k in chosen if taken[k] < len(chosen[k])),\n                key=lambda k: (taken[k] + 1) / len(chosen[k]))\n        order.append(chosen[k][taken[k]])\n        taken[k] += 1\n    return order\n\n\ndef main():\n    ap = argparse.ArgumentParser()\n    ap.add_argument(\"--artifact_dir\", required=True, help=\"artifact folder (full_method_out.json, prompts/)\")\n    ap.add_argument(\"--out\", default=str(Path(__file__).resolve().parent / \"mini_demo_data.json\"))\n    a = ap.parse_args()\n    art = Path(a.artifact_dir)\n    full = json.loads((art / \"full_method_out.json\").read_text())\n    ds = {d[\"dataset\"]: d[\"examples\"] for d in full[\"datasets\"]}\n    rows = ds[DATASET]\n    strata = {}\n    for r in rows:\n        strata.setdefault((r[\"metadata_class_src\"], r[\"metadata_class_base\"]), []).append(r)\n    rng = random.Random(SEED)\n    base_use = {}\n    chosen = {k: pick_stratum(list(strata[k]), n, base_use, rng) for k, n in STRATA_TARGET.items()}\n    examples = interleave(chosen)\n    assert len(examples) == N_KEEP, len(examples)\n    # readable prompt segments (the one line that differs between prompts) for every source / base key kept\n    prompts = {}\n    for line in (art / \"prompts\" / \"t10_prompts.jsonl\").read_text().splitlines():\n        if line.strip():\n            p = json.loads(line)\n            prompts[p[\"key\"]] = p\n    keys = sorted({k for r in examples for k in PAIR_RE.search(r[\"input\"]).groups()})\n    segs = {k: {\"segment\": prompts[k][\"segment\"], \"kind\": prompts[k][\"kind\"], \"split\": prompts[k][\"split\"]}\n            for k in keys}\n    # the shared task text, as decoded in the artifact's own generation rows (BASE PROMPT of slot 0)\n    g0 = ds[\"T10_dec_generation\"][0][\"input\"]\n    task = g0[g0.index(\"Task:\"):g0.index(\"explanation.\") + len(\"explanation.\")]\n    meta = {k: full[\"metadata\"][k] for k in META_KEYS if k in full[\"metadata\"]}\n    meta[\"demo_subset\"] = {\n        \"source_dataset\": DATASET, \"n_source_examples\": len(rows), \"n_selected\": len(examples),\n        \"strata_available\": {f\"{a_}->{b_}\": len(v) for (a_, b_), v in sorted(strata.items())},\n        \"strata_selected\": {f\"{a_}->{b_}\": len(v) for (a_, b_), v in sorted(chosen.items())},\n        \"n_unique_sources\": len({PAIR_RE.search(r[\"input\"]).group(1) for r in examples}),\n        \"n_unique_bases\": len({PAIR_RE.search(r[\"input\"]).group(2) for r in examples}),\n        \"selection\": \"stratified by (class_src, class_base); round-robin over source prompts, least-used base first; \"\n                     \"strata interleaved so every prefix stays mixed\", \"seed\": SEED}\n    meta[\"prompt_segments\"] = segs\n    meta[\"t10_task_text\"] = task\n    out = {\"metadata\": meta, \"datasets\": [{\"dataset\": DATASET, \"examples\": examples}]}\n    Path(a.out).write_text(json.dumps(out, indent=1))\n    print(json.dumps(meta[\"demo_subset\"], indent=1))\n    print(f\"wrote {a.out}: {Path(a.out).stat().st_size / 1e3:.0f} kB\")\n\n\nif __name__ == \"__main__\":\n    main()\n", "structuredPatch": [], "originalFile": null, "userModified": false}
```

### [66] TOOL CALL — Bash · 2026-10-26 13:45:56 UTC

```
Build mini demo data and check subset recovery by prefix:
python3 build_mini_demo_data.py --artifact_dir /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40 && ls -la mini_demo_data.json && python3 - <<'EOF'
import json, re
d=json.load(open("mini_demo_data.json"))
ex=d["datasets"][0]["examples"]
pat=re.compile(r"source=(\S+) base=(\S+)")
print([ (e["metadata_class_src"][:3], e["metadata_class_base"][:3]) for e in ex[:12]])
for n in (10,25,50,100):
    sub=ex[:n]
    ok=[e for e in sub if abs(e["metadata_delta_full"])>=1]
    de=sum(float(e["predict_seed0_k4"]) for e in ok)/len(ok); df=sum(e["metadata_delta_full"] for e in ok)/len(ok)
    print(n, "n_ok",len(ok),"rec k4 seed0", round(de/df,3), "mean das", round(de,2), "mean full", round(df,2))
print(json.dumps(d["metadata"]["prompt_segments"])[:600])
print(d["metadata"]["t10_task_text"])
EOF
```

### [67] TOOL RESULT — Bash [ERROR] · 2026-10-26 13:45:56 UTC

```
Error: Exit code 1
Traceback (most recent call last):
  File "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/build_mini_demo_data.py", line 115, in <module>
    main()
  File "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/build_mini_demo_data.py", line 92, in main
    segs = {k: {"segment": prompts[k]["segment"], "kind": prompts[k]["kind"], "split": prompts[k]["split"]}
                           ~~~~~~~~~~^^^^^^^^^^^
KeyError: 'segment'
```

### [68] ASSISTANT · 2026-10-26 13:46:02 UTC

```
Padded-twin prompts have no `segment` field. Let me see what those records carry instead.
```

### [69] TOOL CALL — Bash · 2026-10-26 13:46:02 UTC

```
Show fields of each T10 prompt kind:
python3 - <<'EOF'
import json
A="/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40"
rows=[json.loads(l) for l in open(A+"/prompts/t10_prompts.jsonl")]
seen=set()
for r in rows:
    if r["kind"] in seen: continue
    seen.add(r["kind"])
    print(r["kind"], {k:(v if not isinstance(v,list) else f"list[{len(v)}]") for k,v in r.items() if k not in ("prompt_sha256",)})
EOF
grep -n "padtwin" /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40/src/prompts8.py | head -20
```

### [70] TOOL RESULT — Bash · 2026-10-26 13:46:02 UTC

```
{"stdout": "forced {'unit': 'T10', 'family': 'qwen', 'kind': 'forced', 'ids': 'list[169]', 'P': 169, 'p0': 3, 'p1': 15, 'spec_end': 160, 'key': 'T10|forced|k0|j0|bfs', 'fam': 0, 'name_idx': 0, 'Y': 'bfs', 'segment': 'Implement breadth-first search (BFS) for this task.', 'split': 'train', 'dec_ids': 'list[180]', 'd': 179}\npadtwin {'unit': 'T10', 'family': 'qwen', 'kind': 'padtwin', 'ids': 'list[169]', 'P': 169, 'p0': 3, 'p1': 15, 'spec_end': 160, 'key': 'T10|padtwin|k0|j0|bfs', 'fam': 0, 'name_idx': 0, 'Y': None, 'padded_of': 'T10|forced|k0|j0|bfs', 'cond': 'list[2]', 'split': 'train', 'dec_ids': 'list[180]', 'd': 179}\ntwin {'unit': 'T10', 'family': 'qwen', 'kind': 'twin', 'ids': 'list[172]', 'P': 172, 'p0': 3, 'p1': 18, 'spec_end': 163, 'key': 'T10|twin|W1|ship', 'w': 'W1', 'noun': 'ship', 'noun_idx': 0, 'noun_source': 'iter7', 'split_w': 'train', 'split_noun': 'held', 'split': 'neither', 'dec_ids': 'list[183]', 'd': 182}\nban {'unit': 'T10', 'family': 'qwen', 'kind': 'ban', 'ids': 'list[172]', 'P': 172, 'p0': 3, 'p1': 18, 'spec_end': 163, 'key': 'T10|ban|W1', 'w': 'W1', 'segment': 'Do not use union-find (disjoint set union) for this task.', 'split': 'placement', 'dec_ids': 'list[183]', 'd': 182}\np0 {'unit': 'T10', 'family': 'qwen', 'kind': 'p0', 'ids': 'list[157]', 'P': 157, 'p0': 3, 'p1': 3, 'spec_end': 148, 'key': 'T10|p0|None', 'w': None, 'segment': '', 'split': 'placement', 'dec_ids': 'list[168]', 'd': 167}\nseed_rand1 {'unit': 'T10', 'family': 'qwen', 'kind': 'seed_rand1', 'ids': 'list[168]', 'P': 168, 'p0': 3, 'p1': 14, 'spec_end': 159, 'key': 'T10|seed_rand1', 'segment': 'seed=d32qxk4nt43', 'split': 'placement', 'dec_ids': 'list[179]', 'd': 178}\nseed_rand2 {'unit': 'T10', 'family': 'qwen', 'kind': 'seed_rand2', 'ids': 'list[164]', 'P': 164, 'p0': 3, 'p1': 10, 'spec_end': 155, 'key': 'T10|seed_rand2', 'segment': 'seed=(horse chair roof love)', 'split': 'placement', 'dec_ids': 'list[175]', 'd': 174}\ninstr_new {'unit': 'T10', 'family': 'qwen', 'kind': 'instr_new', 'ids': 'list[162]', 'P': 162, 'p0': 3, 'p1': 8, 'spec_end': 153, 'key': 'T10|instr_new', 'segment': 'Make a new algorithm.', 'split': 'placement', 'dec_ids': 'list[173]', 'd': 172}\ninstr_novel {'unit': 'T10', 'family': 'qwen', 'kind': 'instr_novel', 'ids': 'list[206]', 'P': 206, 'p0': 3, 'p1': 52, 'spec_end': 197, 'key': 'T10|instr_novel', 'segment': 'Make a fully novel algorithm never seen before for this task. Before writing any code, write a design rationale of about 2,000 words that explains the idea, why no one has used it before, and why it is correct.', 'split': 'placement', 'dec_ids': 'list[217]', 'd': 216}\n7:  padtwin          the forced prompt with its segment tokens replaced by ' .' (exp30 pad_record rule)\n142:                rows.append(rec(\"padtwin\", pids, old[\"p0\"], p1, se, key=f\"T10|padtwin|k{k}|j{j}|{Y}\", fam=k,\n195:        if r[\"kind\"] == \"padtwin\":", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [71] THINKING · 2026-10-26 13:46:16 UTC

```
Padded twins swap the forced prompt's segment tokens with `' .'`, defined by a template and a noun. I'll locate the twin templates in `prompts8.py` so each base prompt can be rendered as text.
```

### [72] TOOL CALL — Bash · 2026-10-26 13:46:16 UTC

```
Find twin prompt templates in prompts8.py:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40; sed -n 1,40p $A/src/prompts8.py; grep -n "W1\|W4\|W5\|template\|TEMPL\|not allowed" $A/src/prompts8.py | head -30
```

### [73] TOOL RESULT — Bash · 2026-10-26 13:46:16 UTC

```
{"stdout": "#!/usr/bin/env python3\n\"\"\"S1 (CPU): every prompt of iteration 8 with positions and splits -> prompts/prompts8.jsonl.\n\nT10 (Qwen3-8B; iteration-7 records in inputs/exp33/prompts7.jsonl reused verbatim where they exist):\n  forced[k][j][Y]  templates k = 0..4 x display names j = 0..3 x Y in {bfs, dfs, union_find}; (k, j = 0) reproduces\n                   iteration 7's forced[k][Y] ids exactly (asserted); Y = union_find is the null source\n  padtwin          the forced prompt with its segment tokens replaced by ' .' (exp30 pad_record rule)\n  twin[w][n]       W1-W5 x 32 single-token nouns: iteration 7's 12 (verbatim ids) + 20 from art_j3Rm_lr2nzR6's flagged\n                   neutral-noun candidates, rebuilt with the same rule (sentence + ' .' padding to the ban's length;\n                   the rebuild reproduces iteration 7's nouns 1-11 exactly, asserted)\n  ban[w], p0, seed_rand1/2, instr_new, instr_novel   placement-only (never fit, never generated)\nSplits: forced families train k = 0,1,2 / held k = 3,4; twin templates train W1-W3 / held W4-W5; nouns 70/30 by a\nseeded shuffle (seed 8001). A held-out pair needs a held-out family AND a held-out base.\nGRID (gemma-3-4b-it): built by src/grid_prompts.py with iteration 7's Gemma prompt code (inputs/exp38/src).\n\"\"\"\n\nfrom __future__ import annotations\n\nimport json\nimport subprocess\nimport sys\nfrom pathlib import Path\nfrom typing import Any\n\nsys.path.insert(0, str(Path(__file__).resolve().parent))\n\nimport numpy as np\nfrom loguru import logger\n\nfrom cfg8 import (FAMILY, HELD_FAM, HELD_W, INPUTS, N_T10_NOUNS, NOUN_SPLIT_SEED, OPEN_T10, PROMPTS_DIR, ROOT,\n                  T10_DISPLAY, T10_FORCED_TEMPLATES, TRAIN_FAM, TRAIN_W, model_path, read_json, read_jsonl,\n                  setup_logging, sha256_text, write_jsonl)\n\nW_TEMPLATES = {\"W1\": \"Do not use {N} for this task.\", \"W2\": \"Your solution must not rely on {N}.\",\n               \"W3\": \"Avoid {N} entirely.\", \"W4\": \"{N} is not allowed here.\",\n               \"W5\": \"Write a correct solution that does not use {N}.\"}\nEXCL = {\"sort\", \"set\", \"union\", \"label\", \"search\", \"depth\", \"breadth\", \"bucket\", \"dial\", \"flood\", \"order\", \"count\",\n        \"number\", \"graph\", \"node\", \"edge\", \"tree\", \"path\", \"list\", \"value\", \"component\", \"heap\", \"select\", \"pivot\",\n        \"median\", \"weight\", \"distance\", \"cycle\", \"loop\", \"group\", \"class\", \"function\", \"code\", \"task\", \"solution\",\n        \"algorithm\", \"program\", \"problem\", \"answer\", \"result\", \"test\", \"parent\", \"root\", \"find\", \"link\", \"network\",\n5:  forced[k][j][Y]  templates k = 0..4 x display names j = 0..3 x Y in {bfs, dfs, union_find}; (k, j = 0) reproduces\n8:  twin[w][n]       W1-W5 x 32 single-token nouns: iteration 7's 12 (verbatim ids) + 20 from art_j3Rm_lr2nzR6's flagged\n12:Splits: forced families train k = 0,1,2 / held k = 3,4; twin templates train W1-W3 / held W4-W5; nouns 70/30 by a\n31:                  T10_DISPLAY, T10_FORCED_TEMPLATES, TRAIN_FAM, TRAIN_W, model_path, read_json, read_jsonl,\n34:W_TEMPLATES = {\"W1\": \"Do not use {N} for this task.\", \"W2\": \"Your solution must not rely on {N}.\",\n35:               \"W3\": \"Avoid {N} entirely.\", \"W4\": \"{N} is not allowed here.\",\n36:               \"W5\": \"Write a correct solution that does not use {N}.\"}\n127:    for k, tmpl in enumerate(T10_FORCED_TEMPLATES):\n156:    for w in W_TEMPLATES:\n160:            sent = W_TEMPLATES[w].format(N=noun)", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [74] TOOL CALL — Bash · 2026-10-26 13:46:22 UTC

```
Read twin and padtwin construction rule:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40; sed -n 120,175p $A/src/prompts8.py
```

### [75] TOOL RESULT — Bash · 2026-10-26 13:46:22 UTC

```
{"stdout": "def build_t10(tok: Any) -> list[dict[str, Any]]:\n    p7 = [r for r in read_jsonl(INPUTS / \"exp33\" / \"prompts7.jsonl\") if r[\"task\"] == \"T10\"]\n    by = {r[\"key\"]: r for r in p7}\n    rows: list[dict[str, Any]] = []\n    # ---- forced sources and padding twins\n    for k, tmpl in enumerate(T10_FORCED_TEMPLATES):\n        old = by[f\"T10|forced|F{k}|bfs\"]\n        for Y, names in T10_DISPLAY.items():\n            for j, name in enumerate(names):\n                seg = tmpl.format(j=name)\n                ids = splice(tok, old, seg)\n                if j == 0:\n                    ref = by[f\"T10|forced|F{k}|{Y}\"]\n                    assert ids == ref[\"ids\"], f\"forced F{k}/{Y} does not reproduce iteration 7\"\n                p1 = old[\"p1\"] + (len(ids) - old[\"P\"])\n                se = old[\"spec_end\"] + (len(ids) - old[\"P\"])\n                fam_split = \"train\" if k in TRAIN_FAM else \"held\"\n                rows.append(rec(\"forced\", ids, old[\"p0\"], p1, se, key=f\"T10|forced|k{k}|j{j}|{Y}\", fam=k, name_idx=j,\n                                Y=Y, segment=seg, split=fam_split))\n                pids, cond = pad_twin_ids(tok, ids, old[\"p0\"], p1)\n                rows.append(rec(\"padtwin\", pids, old[\"p0\"], p1, se, key=f\"T10|padtwin|k{k}|j{j}|{Y}\", fam=k,\n                                name_idx=j, Y=None, padded_of=f\"T10|forced|k{k}|j{j}|{Y}\", cond=cond,\n                                split=fam_split))\n    # ---- twins: iteration-7 nouns verbatim + new nouns rebuilt with the same rule\n    tw7 = [r for r in p7 if r[\"kind\"] == \"twin\"]\n    nouns7 = [n for _, n in sorted({(r[\"noun_idx\"], r[\"noun\"]) for r in tw7})]\n    spec_text = tok.decode(tw7[0][\"ids\"][tw7[0][\"p1\"]:tw7[0][\"spec_end\"]])\n    extra = noun_pool(tok, spec_text, set(nouns7))[:N_T10_NOUNS - len(nouns7)]\n    nouns = nouns7 + extra\n    assert len(nouns) == N_T10_NOUNS, f\"only {len(nouns)} nouns\"\n    rng = np.random.default_rng(NOUN_SPLIT_SEED)\n    perm = list(rng.permutation(len(nouns)))\n    n_train = int(round(0.7 * len(nouns)))\n    noun_split = {nouns[i]: (\"train\" if r < n_train else \"held\") for r, i in enumerate(perm)}\n    for w in W_TEMPLATES:\n        base0 = next(r for r in tw7 if r[\"w\"] == w and r[\"noun_idx\"] == 0)\n        region_len = base0[\"p1\"] - base0[\"p0\"]\n        for ni, noun in enumerate(nouns):\n            sent = W_TEMPLATES[w].format(N=noun)\n            sent = cap_first(sent)\n            ids = splice(tok, base0, sent, pad_to=region_len)\n            if ni < len(nouns7):\n                ref = next(r for r in tw7 if r[\"w\"] == w and r[\"noun\"] == noun)\n                if ids != ref[\"ids\"]:\n                    ids = ref[\"ids\"]          # keep iteration 7's frozen ids verbatim (logged below)\n                    logger.warning(f\"twin {w}/{noun}: rebuild differs from iteration 7; frozen ids kept\")\n            if ids is None:\n                continue\n            rows.append(rec(\"twin\", ids, base0[\"p0\"], base0[\"p1\"], base0[\"spec_end\"], key=f\"T10|twin|{w}|{noun}\", w=w,\n                            noun=noun, noun_idx=ni, noun_source=\"iter7\" if ni < len(nouns7) else \"art_j3Rm\",\n                            split_w=\"train\" if w in TRAIN_W else \"held\", split_noun=noun_split[noun],\n                            split=(\"train\" if (w in TRAIN_W and noun_split[noun] == \"train\") else\n                                   \"held\" if (w in HELD_W and noun_split[noun] == \"held\") else \"neither\")))\n    # ---- placement-only prompts", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [76] THINKING · 2026-10-26 13:46:44 UTC

```
I'll update the build script to rebuild readable text for both twins and padded twins, reconstructing them from `cap_first(template.format(noun))` plus `' .'` padding using the same templates.
```

### [77] TOOL CALL — Edit · 2026-10-26 13:46:44 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/build_mini_demo_data.py
OLD: PAIR_RE = re.compile(r"source=(\S+) base=(\S+)")

NEW: PAIR_RE = re.compile(r"source=(\S+) base=(\S+)")
# twin templates, copied from the artifact's src/prompts8.py (twins = template + noun, padded with ' .' tokens)
W_TEMPLATES = {"W1": "Do not use {N} for this task.", "W2": "Your solution must not rely on {N}.",
               "W3": "Avoid {N} entirely.", "W4": "{N} is not allowed here.",
               "W5": "Write a correct solution that does not use {N}."}


def readable_segment(p):
    """The one line of a T10 prompt that differs between prompts (the rest is the shared task text)."""
    if p["kind"] == "twin":
        s = W_TEMPLATES[p["w"]].format(N=p["noun"])
        return s[0].upper() + s[1:] + " . . . (padded with ' .' tokens)"
    if p["kind"] == "padtwin":
        return " ".join(["."] * (p["p1"] - p["p0"])) + f"  (the segment of {p['padded_of']} replaced by ' .' tokens)"
    return p["segment"]
```

### [78] TOOL RESULT — Edit · 2026-10-26 13:46:44 UTC

```
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/build_mini_demo_data.py", "oldString": "PAIR_RE = re.compile(r\"source=(\\S+) base=(\\S+)\")\n", "newString": "PAIR_RE = re.compile(r\"source=(\\S+) base=(\\S+)\")\n# twin templates, copied from the artifact's src/prompts8.py (twins = template + noun, padded with ' .' tokens)\nW_TEMPLATES = {\"W1\": \"Do not use {N} for this task.\", \"W2\": \"Your solution must not rely on {N}.\",\n               \"W3\": \"Avoid {N} entirely.\", \"W4\": \"{N} is not allowed here.\",\n               \"W5\": \"Write a correct solution that does not use {N}.\"}\n\n\ndef readable_segment(p):\n    \"\"\"The one line of a T10 prompt that differs between prompts (the rest is the shared task text).\"\"\"\n    if p[\"kind\"] == \"twin\":\n        s = W_TEMPLATES[p[\"w\"]].format(N=p[\"noun\"])\n        return s[0].upper() + s[1:] + \" . . . (padded with ' .' tokens)\"\n    if p[\"kind\"] == \"padtwin\":\n        return \" \".join([\".\"] * (p[\"p1\"] - p[\"p0\"])) + f\"  (the segment of {p['padded_of']} replaced by ' .' tokens)\"\n    return p[\"segment\"]\n", "originalFile": "#!/usr/bin/env python3\n\"\"\"Build mini_demo_data.json for code_demo.ipynb from the artifact's full_method_out.json (standard library only).\n\nThe demo uses ONE dataset of the artifact's output: `T10_dec_teacher_forced` (600 held-out teacher-forced pairs of the\nQwen3-8B T10 decision site, block L* = 22; per pair the full-state Delta and the DAS Delta of every fit seed and rank).\n100 pairs are kept, stratified by (source class, base class) and spread over as many source and base prompts as\npossible; they are ordered so that every prefix is still mixed across strata (the notebook's N_PAIRS takes a prefix).\n\nThe metadata block keeps the artifact's own result JSONs that the CPU analysis stages read (per-site TF results,\ncontrols, random-init control, generation tables, scan profiles, geometry, mediation, K2), plus the readable prompt\nsegment of every source / base prompt used by the kept pairs.\n\nUsage: python3 build_mini_demo_data.py --artifact_dir <folder holding full_method_out.json and prompts/>\n\"\"\"\n\nimport argparse\nimport json\nimport random\nimport re\nfrom pathlib import Path\n\nDATASET = \"T10_dec_teacher_forced\"\nN_KEEP = 100\nSTRATA_TARGET = {(\"bfs\", \"union_find\"): 44, (\"dfs\", \"union_find\"): 44, (\"bfs\", \"dfs\"): 6, (\"union_find\", \"dfs\"): 6}\nSEED = 0\nMETA_KEYS = (\"method_name\", \"description\", \"verdicts\", \"K2\", \"mediation\", \"commit_chain\", \"deviations\", \"dec_T10\",\n             \"band_T10\", \"dec_GRID\", \"dec_T10_L24\", \"rinit_T10\", \"rinit_GRID\", \"rinit_T10_band\", \"rinit_T10_L24\",\n             \"s3_T10\", \"s3_GRID\", \"geometry\", \"novelty_audit\", \"costs\", \"post_T10\", \"unit_tests_cpu\",\n             \"unit_tests_gpu_T10\", \"unit_tests_gpu_GRID\", \"mediation_T10\", \"rederive\", \"scan_T10\", \"scan_GRID\",\n             \"gen_T10_dec\", \"gen_T10_band\", \"gen_GRID_dec\")\nPAIR_RE = re.compile(r\"source=(\\S+) base=(\\S+)\")\n\n\ndef pick_stratum(rows, n, base_use, rng):\n    \"\"\"Round-robin over source prompts; from each source take the pair whose base prompt is least used so far.\"\"\"\n    by_src = {}\n    for r in rows:\n        by_src.setdefault(PAIR_RE.search(r[\"input\"]).group(1), []).append(r)\n    srcs = sorted(by_src)\n    rng.shuffle(srcs)\n    out = []\n    while len(out) < n and any(by_src.values()):\n        for s in srcs:\n            if len(out) >= n or not by_src[s]:\n                continue\n            cand = by_src[s]\n            rng.shuffle(cand)\n            cand.sort(key=lambda r: base_use.get(PAIR_RE.search(r[\"input\"]).group(2), 0))\n            r = cand.pop(0)\n            base_use[PAIR_RE.search(r[\"input\"]).group(2)] = base_use.get(PAIR_RE.search(r[\"input\"]).group(2), 0) + 1\n            out.append(r)\n    return out\n\n\ndef interleave(chosen):\n    \"\"\"Order the kept pairs so that every prefix stays close to the target stratum shares.\"\"\"\n    total = sum(len(v) for v in chosen.values())\n    taken = {k: 0 for k in chosen}\n    order = []\n    for i in range(total):\n        k = min((k for k in chosen if taken[k] < len(chosen[k])),\n                key=lambda k: (taken[k] + 1) / len(chosen[k]))\n        order.append(chosen[k][taken[k]])\n        taken[k] += 1\n    return order\n\n\ndef main():\n    ap = argparse.ArgumentParser()\n    ap.add_argument(\"--artifact_dir\", required=True, help=\"artifact folder (full_method_out.json, prompts/)\")\n    ap.add_argument(\"--out\", default=str(Path(__file__).resolve().parent / \"mini_demo_data.json\"))\n    a = ap.parse_args()\n    art = Path(a.artifact_dir)\n    full = json.loads((art / \"full_method_out.json\").read_text())\n    ds = {d[\"dataset\"]: d[\"examples\"] for d in full[\"datasets\"]}\n    rows = ds[DATASET]\n    strata = {}\n    for r in rows:\n        strata.setdefault((r[\"metadata_class_src\"], r[\"metadata_class_base\"]), []).append(r)\n    rng = random.Random(SEED)\n    base_use = {}\n    chosen = {k: pick_stratum(list(strata[k]), n, base_use, rng) for k, n in STRATA_TARGET.items()}\n    examples = interleave(chosen)\n    assert len(examples) == N_KEEP, len(examples)\n    # readable prompt segments (the one line that differs between prompts) for every source / base key kept\n    prompts = {}\n    for line in (art / \"prompts\" / \"t10_prompts.jsonl\").read_text().splitlines():\n        if line.strip():\n            p = json.loads(line)\n            prompts[p[\"key\"]] = p\n    keys = sorted({k for r in examples for k in PAIR_RE.search(r[\"input\"]).groups()})\n    segs = {k: {\"segment\": prompts[k][\"segment\"], \"kind\": prompts[k][\"kind\"], \"split\": prompts[k][\"split\"]}\n            for k in keys}\n    # the shared task text, as decoded in the artifact's own generation rows (BASE PROMPT of slot 0)\n    g0 = ds[\"T10_dec_generation\"][0][\"input\"]\n    task = g0[g0.index(\"Task:\"):g0.index(\"explanation.\") + len(\"explanation.\")]\n    meta = {k: full[\"metadata\"][k] for k in META_KEYS if k in full[\"metadata\"]}\n    meta[\"demo_subset\"] = {\n        \"source_dataset\": DATASET, \"n_source_examples\": len(rows), \"n_selected\": len(examples),\n        \"strata_available\": {f\"{a_}->{b_}\": len(v) for (a_, b_), v in sorted(strata.items())},\n        \"strata_selected\": {f\"{a_}->{b_}\": len(v) for (a_, b_), v in sorted(chosen.items())},\n        \"n_unique_sources\": len({PAIR_RE.search(r[\"input\"]).group(1) for r in examples}),\n        \"n_unique_bases\": len({PAIR_RE.search(r[\"input\"]).group(2) for r in examples}),\n        \"selection\": \"stratified by (class_src, class_base); round-robin over source prompts, least-used base first; \"\n                     \"strata interleaved so every prefix stays mixed\", \"seed\": SEED}\n    meta[\"prompt_segments\"] = segs\n    meta[\"t10_task_text\"] = task\n    out = {\"metadata\": meta, \"datasets\": [{\"dataset\": DATASET, \"examples\": examples}]}\n    Path(a.out).write_text(json.dumps(out, indent=1))\n    print(json.dumps(meta[\"demo_subset\"], indent=1))\n    print(f\"wrote {a.out}: {Path(a.out).stat().st_size / 1e3:.0f} kB\")\n\n\nif __name__ == \"__main__\":\n    main()\n", "structuredPatch": [{"oldStart": 29, "oldLines": 8, "newStart": 29, "newLines": 22, "lines": ["              \"unit_tests_gpu_T10\", \"unit_tests_gpu_GRID\", \"mediation_T10\", \"rederive\", \"scan_T10\", \"scan_GRID\",", "              \"gen_T10_dec\", \"gen_T10_band\", \"gen_GRID_dec\")", " PAIR_RE = re.compile(r\"source=(\\S+) base=(\\S+)\")", "+# twin templates, copied from the artifact's src/prompts8.py (twins = template + noun, padded with ' .' tokens)", "+W_TEMPLATES = {\"W1\": \"Do not use {N} for this task.\", \"W2\": \"Your solution must not rely on {N}.\",", "+               \"W3\": \"Avoid {N} entirely.\", \"W4\": \"{N} is not allowed here.\",", "+               \"W5\": \"Write a correct solution that does not use {N}.\"}", " ", " ", "+def readable_segment(p):", "+    \"\"\"The one line of a T10 prompt that differs between prompts (the rest is the shared task text).\"\"\"", "+    if p[\"kind\"] == \"twin\":", "+        s = W_TEMPLATES[p[\"w\"]].format(N=p[\"noun\"])", "+        return s[0].upper() + s[1:] + \" . . . (padded with ' .' tokens)\"", "+    if p[\"kind\"] == \"padtwin\":", "+        return \" \".join([\".\"] * (p[\"p1\"] - p[\"p0\"])) + f\"  (the segment of {p['padded_of']} replaced by ' .' tokens)\"", "+    return p[\"segment\"]", "+", "+", " def pick_stratum(rows, n, base_use, rng):", "     \"\"\"Round-robin over source prompts; from each source take the pair whose base prompt is least used so far.\"\"\"", "     by_src = {}"]}], "userModified": false, "replaceAll": false}
```

### [79] TOOL CALL — Edit · 2026-10-26 13:46:44 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/build_mini_demo_data.py
OLD:     segs = {k: {"segment": prompts[k]["segment"], "kind": prompts[k]["kind"], "split": prompts[k]["split"]}
            for k in keys}
NEW:     segs = {k: {"segment": readable_segment(prompts[k]), "kind": prompts[k]["kind"], "split": prompts[k]["split"]}
            for k in keys}
```

### [80] TOOL RESULT — Edit · 2026-10-26 13:46:44 UTC

```
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/build_mini_demo_data.py", "oldString": "    segs = {k: {\"segment\": prompts[k][\"segment\"], \"kind\": prompts[k][\"kind\"], \"split\": prompts[k][\"split\"]}\n            for k in keys}", "newString": "    segs = {k: {\"segment\": readable_segment(prompts[k]), \"kind\": prompts[k][\"kind\"], \"split\": prompts[k][\"split\"]}\n            for k in keys}", "originalFile": "#!/usr/bin/env python3\n\"\"\"Build mini_demo_data.json for code_demo.ipynb from the artifact's full_method_out.json (standard library only).\n\nThe demo uses ONE dataset of the artifact's output: `T10_dec_teacher_forced` (600 held-out teacher-forced pairs of the\nQwen3-8B T10 decision site, block L* = 22; per pair the full-state Delta and the DAS Delta of every fit seed and rank).\n100 pairs are kept, stratified by (source class, base class) and spread over as many source and base prompts as\npossible; they are ordered so that every prefix is still mixed across strata (the notebook's N_PAIRS takes a prefix).\n\nThe metadata block keeps the artifact's own result JSONs that the CPU analysis stages read (per-site TF results,\ncontrols, random-init control, generation tables, scan profiles, geometry, mediation, K2), plus the readable prompt\nsegment of every source / base prompt used by the kept pairs.\n\nUsage: python3 build_mini_demo_data.py --artifact_dir <folder holding full_method_out.json and prompts/>\n\"\"\"\n\nimport argparse\nimport json\nimport random\nimport re\nfrom pathlib import Path\n\nDATASET = \"T10_dec_teacher_forced\"\nN_KEEP = 100\nSTRATA_TARGET = {(\"bfs\", \"union_find\"): 44, (\"dfs\", \"union_find\"): 44, (\"bfs\", \"dfs\"): 6, (\"union_find\", \"dfs\"): 6}\nSEED = 0\nMETA_KEYS = (\"method_name\", \"description\", \"verdicts\", \"K2\", \"mediation\", \"commit_chain\", \"deviations\", \"dec_T10\",\n             \"band_T10\", \"dec_GRID\", \"dec_T10_L24\", \"rinit_T10\", \"rinit_GRID\", \"rinit_T10_band\", \"rinit_T10_L24\",\n             \"s3_T10\", \"s3_GRID\", \"geometry\", \"novelty_audit\", \"costs\", \"post_T10\", \"unit_tests_cpu\",\n             \"unit_tests_gpu_T10\", \"unit_tests_gpu_GRID\", \"mediation_T10\", \"rederive\", \"scan_T10\", \"scan_GRID\",\n             \"gen_T10_dec\", \"gen_T10_band\", \"gen_GRID_dec\")\nPAIR_RE = re.compile(r\"source=(\\S+) base=(\\S+)\")\n# twin templates, copied from the artifact's src/prompts8.py (twins = template + noun, padded with ' .' tokens)\nW_TEMPLATES = {\"W1\": \"Do not use {N} for this task.\", \"W2\": \"Your solution must not rely on {N}.\",\n               \"W3\": \"Avoid {N} entirely.\", \"W4\": \"{N} is not allowed here.\",\n               \"W5\": \"Write a correct solution that does not use {N}.\"}\n\n\ndef readable_segment(p):\n    \"\"\"The one line of a T10 prompt that differs between prompts (the rest is the shared task text).\"\"\"\n    if p[\"kind\"] == \"twin\":\n        s = W_TEMPLATES[p[\"w\"]].format(N=p[\"noun\"])\n        return s[0].upper() + s[1:] + \" . . . (padded with ' .' tokens)\"\n    if p[\"kind\"] == \"padtwin\":\n        return \" \".join([\".\"] * (p[\"p1\"] - p[\"p0\"])) + f\"  (the segment of {p['padded_of']} replaced by ' .' tokens)\"\n    return p[\"segment\"]\n\n\ndef pick_stratum(rows, n, base_use, rng):\n    \"\"\"Round-robin over source prompts; from each source take the pair whose base prompt is least used so far.\"\"\"\n    by_src = {}\n    for r in rows:\n        by_src.setdefault(PAIR_RE.search(r[\"input\"]).group(1), []).append(r)\n    srcs = sorted(by_src)\n    rng.shuffle(srcs)\n    out = []\n    while len(out) < n and any(by_src.values()):\n        for s in srcs:\n            if len(out) >= n or not by_src[s]:\n                continue\n            cand = by_src[s]\n            rng.shuffle(cand)\n            cand.sort(key=lambda r: base_use.get(PAIR_RE.search(r[\"input\"]).group(2), 0))\n            r = cand.pop(0)\n            base_use[PAIR_RE.search(r[\"input\"]).group(2)] = base_use.get(PAIR_RE.search(r[\"input\"]).group(2), 0) + 1\n            out.append(r)\n    return out\n\n\ndef interleave(chosen):\n    \"\"\"Order the kept pairs so that every prefix stays close to the target stratum shares.\"\"\"\n    total = sum(len(v) for v in chosen.values())\n    taken = {k: 0 for k in chosen}\n    order = []\n    for i in range(total):\n        k = min((k for k in chosen if taken[k] < len(chosen[k])),\n                key=lambda k: (taken[k] + 1) / len(chosen[k]))\n        order.append(chosen[k][taken[k]])\n        taken[k] += 1\n    return order\n\n\ndef main():\n    ap = argparse.ArgumentParser()\n    ap.add_argument(\"--artifact_dir\", required=True, help=\"artifact folder (full_method_out.json, prompts/)\")\n    ap.add_argument(\"--out\", default=str(Path(__file__).resolve().parent / \"mini_demo_data.json\"))\n    a = ap.parse_args()\n    art = Path(a.artifact_dir)\n    full = json.loads((art / \"full_method_out.json\").read_text())\n    ds = {d[\"dataset\"]: d[\"examples\"] for d in full[\"datasets\"]}\n    rows = ds[DATASET]\n    strata = {}\n    for r in rows:\n        strata.setdefault((r[\"metadata_class_src\"], r[\"metadata_class_base\"]), []).append(r)\n    rng = random.Random(SEED)\n    base_use = {}\n    chosen = {k: pick_stratum(list(strata[k]), n, base_use, rng) for k, n in STRATA_TARGET.items()}\n    examples = interleave(chosen)\n    assert len(examples) == N_KEEP, len(examples)\n    # readable prompt segments (the one line that differs between prompts) for every source / base key kept\n    prompts = {}\n    for line in (art / \"prompts\" / \"t10_prompts.jsonl\").read_text().splitlines():\n        if line.strip():\n            p = json.loads(line)\n            prompts[p[\"key\"]] = p\n    keys = sorted({k for r in examples for k in PAIR_RE.search(r[\"input\"]).groups()})\n    segs = {k: {\"segment\": prompts[k][\"segment\"], \"kind\": prompts[k][\"kind\"], \"split\": prompts[k][\"split\"]}\n            for k in keys}\n    # the shared task text, as decoded in the artifact's own generation rows (BASE PROMPT of slot 0)\n    g0 = ds[\"T10_dec_generation\"][0][\"input\"]\n    task = g0[g0.index(\"Task:\"):g0.index(\"explanation.\") + len(\"explanation.\")]\n    meta = {k: full[\"metadata\"][k] for k in META_KEYS if k in full[\"metadata\"]}\n    meta[\"demo_subset\"] = {\n        \"source_dataset\": DATASET, \"n_source_examples\": len(rows), \"n_selected\": len(examples),\n        \"strata_available\": {f\"{a_}->{b_}\": len(v) for (a_, b_), v in sorted(strata.items())},\n        \"strata_selected\": {f\"{a_}->{b_}\": len(v) for (a_, b_), v in sorted(chosen.items())},\n        \"n_unique_sources\": len({PAIR_RE.search(r[\"input\"]).group(1) for r in examples}),\n        \"n_unique_bases\": len({PAIR_RE.search(r[\"input\"]).group(2) for r in examples}),\n        \"selection\": \"stratified by (class_src, class_base); round-robin over source prompts, least-used base first; \"\n                     \"strata interleaved so every prefix stays mixed\", \"seed\": SEED}\n    meta[\"prompt_segments\"] = segs\n    meta[\"t10_task_text\"] = task\n    out = {\"metadata\": meta, \"datasets\": [{\"dataset\": DATASET, \"examples\": examples}]}\n    Path(a.out).write_text(json.dumps(out, indent=1))\n    print(json.dumps(meta[\"demo_subset\"], indent=1))\n    print(f\"wrote {a.out}: {Path(a.out).stat().st_size / 1e3:.0f} kB\")\n\n\nif __name__ == \"__main__\":\n    main()\n", "structuredPatch": [{"oldStart": 103, "oldLines": 7, "newStart": 103, "newLines": 7, "lines": ["             p = json.loads(line)", "             prompts[p[\"key\"]] = p", "     keys = sorted({k for r in examples for k in PAIR_RE.search(r[\"input\"]).groups()})", "-    segs = {k: {\"segment\": prompts[k][\"segment\"], \"kind\": prompts[k][\"kind\"], \"split\": prompts[k][\"split\"]}", "+    segs = {k: {\"segment\": readable_segment(prompts[k]), \"kind\": prompts[k][\"kind\"], \"split\": prompts[k][\"split\"]}", "             for k in keys}", "     # the shared task text, as decoded in the artifact's own generation rows (BASE PROMPT of slot 0)", "     g0 = ds[\"T10_dec_generation\"][0][\"input\"]"]}], "userModified": false, "replaceAll": false}
```

### [81] TOOL CALL — Bash · 2026-10-26 13:46:44 UTC

```
Rebuild mini demo data and check prefixes:
python3 build_mini_demo_data.py --artifact_dir /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40 && ls -la mini_demo_data.json && python3 - <<'EOF'
import json, re
d=json.load(open("mini_demo_data.json"))
ex=d["datasets"][0]["examples"]
print([ (e["metadata_class_src"][:3], e["metadata_class_base"][:3]) for e in ex[:12]])
for n in (10,25,50,100):
    sub=ex[:n]
    ok=[e for e in sub if abs(e["metadata_delta_full"])>=1]
    de=sum(float(e["predict_seed0_k4"]) for e in ok)/len(ok); df=sum(e["metadata_delta_full"] for e in ok)/len(ok)
    print(n, "n_ok",len(ok),"rec k4 seed0", round(de/df,3), "mean das", round(de,2), "mean full", round(df,2))
segs=d["metadata"]["prompt_segments"]
for k in list(segs)[:3]+[k for k in segs if "padtwin" in k][:1]+[k for k in segs if "|twin|" in k][:2]:
    print(k, segs[k])
print(d["metadata"]["t10_task_text"])
EOF
```

### [82] TOOL RESULT — Bash · 2026-10-26 13:46:44 UTC

````
{"stdout": "{\n \"source_dataset\": \"T10_dec_teacher_forced\",\n \"n_source_examples\": 600,\n \"n_selected\": 100,\n \"strata_available\": {\n  \"bfs->dfs\": 20,\n  \"bfs->union_find\": 280,\n  \"dfs->union_find\": 280,\n  \"union_find->dfs\": 20\n },\n \"strata_selected\": {\n  \"bfs->dfs\": 6,\n  \"bfs->union_find\": 44,\n  \"dfs->union_find\": 44,\n  \"union_find->dfs\": 6\n },\n \"n_unique_sources\": 22,\n \"n_unique_bases\": 44,\n \"selection\": \"stratified by (class_src, class_base); round-robin over source prompts, least-used base first; strata interleaved so every prefix stays mixed\",\n \"seed\": 0\n}\nwrote /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/mini_demo_data.json: 260 kB\n-rw-rw-rw- 1 aii-agent aii-agent 259719 Oct 26 13:46 mini_demo_data.json\n[('bfs', 'uni'), ('dfs', 'uni'), ('bfs', 'uni'), ('dfs', 'uni'), ('bfs', 'uni'), ('dfs', 'uni'), ('bfs', 'uni'), ('dfs', 'uni'), ('bfs', 'uni'), ('dfs', 'uni'), ('bfs', 'uni'), ('dfs', 'uni')]\n10 n_ok 9 rec k4 seed0 8.998 mean das 19.0 mean full 2.11\n25 n_ok 22 rec k4 seed0 8.158 mean das 17.75 mean full 2.18\n50 n_ok 46 rec k4 seed0 7.58 mean das 16.75 mean full 2.21\n100 n_ok 92 rec k4 seed0 7.76 mean das 16.83 mean full 2.17\nT10|forced|k3|j0|bfs {'segment': 'Your solution should use breadth-first search (BFS).', 'kind': 'forced', 'split': 'held'}\nT10|forced|k3|j0|dfs {'segment': 'Your solution should use depth-first search (DFS).', 'kind': 'forced', 'split': 'held'}\nT10|forced|k3|j0|union_find {'segment': 'Your solution should use union-find (disjoint set union).', 'kind': 'forced', 'split': 'held'}\nT10|padtwin|k3|j0|bfs {'segment': \". . . . . . . . . . .  (the segment of T10|forced|k3|j0|bfs replaced by ' .' tokens)\", 'kind': 'padtwin', 'split': 'held'}\nT10|twin|W4|baby {'segment': \"Baby is not allowed here. . . . (padded with ' .' tokens)\", 'kind': 'twin', 'split': 'held'}\nT10|twin|W4|bed {'segment': \"Bed is not allowed here. . . . (padded with ' .' tokens)\", 'kind': 'twin', 'split': 'held'}\nTask: write a Python function solve(n, edges) that returns the number of connected components of an undirected graph. The nodes are the integers 0 to n - 1, with 1 <= n <= 300. The argument edges is a list of pairs [u, v] with 0 <= u, v < n and u != v, each joining nodes u and v; 0 <= len(edges) <= 1500 and no pair of nodes is joined twice. A node with no edges forms a component on its own.\n\nUse only the Python standard library. Return only one ```python code block containing the function solve and any helpers, with no example usage and no explanation.", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
````

### [83] THINKING · 2026-10-26 13:48:28 UTC

```
The subset yields a seed-0, k=4 recovery of 7.76 on 92 usable pairs (vs. published 8.43 on 552, CI 5.94–11.30), covering 22/24 held-out sources, all 44 bases, with every prefix mixed. Next, I'll verify a few metadata fields used by `verdict()` and the K2 block before writing the notebook, so the original functions run unmodified.
```

### [84] TOOL CALL — Bash · 2026-10-26 13:48:28 UTC

```
Verify metadata fields used by verdict and K2 code:
python3 - <<'EOF'
import json
md=json.load(open("mini_demo_data.json"))["metadata"]
print("GRID c2 shuffle0:", json.dumps(md["dec_GRID"]["c2"]["shuffle0"])[:600])
print("band c1 keys:", list(md["band_T10"]["c1"].keys()), "band c6 keys:", list(md["band_T10"]["c6"].keys()), "band c2 keys:", list(md["band_T10"]["c2"].keys()))
print("band recovery_by_rank keys:", list(md["band_T10"]["recovery_by_rank"].keys()))
print("L24 keys:", [k for k in md["dec_T10_L24"].keys()])
print("rinit_T10:", json.dumps(md["rinit_T10"])[:900])
print("post_T10:", json.dumps(md["post_T10"]))
print("published verdict labels:", {k:v["verdict"] for k,v in md["verdicts"].items()})
print("K2:", md["K2"]["status"], md["K2"]["p_K2"])
print("mediation summary keys:", list(md["mediation"].keys()))
print("gen_T10_band classes:", list(md["gen_T10_band"]["classes"].keys()), "gen_GRID:", list(md["gen_GRID_dec"]["classes"].keys()))
print("rederive keys:", list(md["rederive"].keys()))
EOF
```

### [85] TOOL RESULT — Bash · 2026-10-26 13:48:28 UTC

```
{"stdout": "GRID c2 shuffle0: {\"fit\": {\"best_step\": 80, \"best_val_kl\": 0.7596735975298927, \"steps_run\": 140, \"seconds\": 52.0}, \"n_train_pairs_retained\": 612, \"share_targets_changed\": 0.4166666666666667, \"heldout_recovery_toward_true_class\": {\"n\": 108, \"n_src\": 8, \"n_base\": 14, \"recovery\": 0.349421717122196, \"ci95\": [0.20406507313595457, 0.48674133654979124], \"mean_delta_edit\": 1.0535504729659468, \"mean_delta_full\": 3.0151259104410806, \"iia_like_share_positive\": 0.8888888888888888}, \"ratio_to_true_fit\": 0.1138637165218487, \"pass\": false, \"test_true_gt_perm\": {\"mean_diff\": 8.090013708387103, \"p_cluster_boot\": 0.0004997501249\nband c1 keys: ['1', '2', '4', '8'] band c6 keys: ['twins', 'twins_forced_bans'] band c2 keys: ['pi1', 'pi2', 'prompt', 'pass']\nband recovery_by_rank keys: ['1', '2', '4', '8', 'seed1']\nL24 keys: ['unit', 'family', 'classes', 'L_star', 'readout_proximal', 'k_star', 'scan', 'unit_tests', 'n_train_pairs', 'n_held_pairs', 'recovery_by_rank', 'rank1_only', 'main', 'off_manifold_flag', 'full_state_held', 'fits', 'c1', 'c2', 'c4', 'c5', 'c6', 'c7', 'baselines', 'iter7_side', 'seconds']\nrinit_T10: {\"unit\": \"T10\", \"U8_entropy_nats\": [11.120536804199219, 11.105794906616211], \"U8_pass_gt_8\": true, \"site\": \"dec\", \"L\": 22, \"k_star\": 4, \"by_rank\": {\"1\": {\"mean_delta_rinit\": 10.02843123515447, \"kl_mean\": 1.6003944479417986}, \"2\": {\"mean_delta_rinit\": 10.779726208051045, \"kl_mean\": 2.1933216758243117}, \"4\": {\"mean_delta_rinit\": 12.081434981822968, \"kl_mean\": 3.099046284602955}, \"8\": {\"mean_delta_rinit\": 12.986624685923259, \"kl_mean\": 3.673934429092333}}, \"mean_delta_trained\": 17.53134325027466, \"mean_delta_rinit\": 12.081434981822968, \"ratio\": 0.6891334457006705, \"pass\": false, \"test_trained_gt_rinit\": {\"mean_diff\": 5.449908268451691, \"p_cluster_boot\": 0.0004997501249375312, \"p_wilcoxon_pairs\": 1.1825072010272085e-55}, \"rinit_full_state_mean_delta\": 1.16163694302241, \"fit\": {\"best_step\": 240, \"best_val_kl\": 0.5660082205704384, \"steps_run\": 240, \"seconds\": 77.2}, \"seconds\": 141.4}\npost_T10: {\"unit\": \"T10\", \"L\": 22, \"k_star\": 4, \"mean_delta_true\": 17.509216632843017, \"perm\": {\"pi1\": {\"mean_delta\": 15.108920202255248, \"test_true_gt_perm\": {\"mean_diff\": 2.4002964305877685, \"p_cluster_boot\": 0.03698150924537731, \"p_wilcoxon_pairs\": 1.600719096339626e-28}}, \"pi2\": {\"mean_delta\": 11.177985747655233, \"test_true_gt_perm\": {\"mean_diff\": 6.331230885187785, \"p_cluster_boot\": 0.0004997501249375312, \"p_wilcoxon_pairs\": 3.0924420849936363e-100}}, \"prompt\": {\"mean_delta\": 13.362031698226929, \"test_true_gt_perm\": {\"mean_diff\": 4.147184934616089, \"p_cluster_boot\": 0.0004997501249375312, \"p_wilcoxon_pairs\": 5.770090425541267e-37}}}}\npublished verdict labels: {'T10-dec': 'NO HANDLE', 'T10-band': 'SUFFICIENT HANDLE', 'GRID-dec': 'SUFFICIENT HANDLE', 'T10-dec_L24_posthoc': \"POST HOC, TF-only (no generation): controls failed ['c2', 'c3'], untested []\"}\nK2: DISCONFIRMED 0.03698150924537731\nmediation summary keys: ['escapes_PUSH', 'n_PUSH', 'clamp_TASK', 'clamp_RAND', 'clamp_DEC', 'not_estimable', 'clamp_pass', 'prospective', 'retrospective']\ngen_T10_band classes: ['bfs', 'dfs'] gen_GRID: ['bfs']\nrederive keys: ['tf', 'gen', 'mediation', 'c2', 'mediation_clamp_prospective', 'mcnemar_das_vs_rand', 'K2', 'all_match', 'n_checks']", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [86] THINKING · 2026-10-26 13:50:58 UTC

```
All the required fields are present, so I'll now build the notebook using a builder script that copies cell sources from the original modules, then delete the builder once it passes. I'll also load the NotebookEdit tool for any targeted fixes afterward.
```

### [87] TOOL CALL — ToolSearch · 2026-10-26 13:50:58 UTC

```
{'query': 'select:NotebookEdit', 'max_results': 1}
```

### [88] TOOL RESULT — ToolSearch · 2026-10-26 13:50:58 UTC

```
{"matches": ["NotebookEdit"], "query": "select:NotebookEdit", "total_deferred_tools": 28}
```

### [89] THINKING · 2026-10-26 13:57:22 UTC

```
Building the builder script now, with each cell either copied from the original modules (stats8, run_dec, analysis8, digest8, figures8, rederive) or a minimal adapter reading from loaded `data` instead of `results/*.json` files.
```

### [90] TOOL CALL — Write · 2026-10-26 13:57:22 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [91] TOOL RESULT — Write · 2026-10-26 13:57:22 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [92] ASSISTANT · 2026-10-26 13:57:30 UTC

```
Before the slower clean-venv test, I'll build the notebook and do a quick dry run of its code cells (skipping the install cell) with whatever Python has the libraries, to catch errors early.
```

### [93] TOOL CALL — Bash · 2026-10-26 13:57:30 UTC

```
Build notebook and check available Python libraries:
python3 _build_notebook.py && python3 -c "import json;nb=json.load(open('code_demo.ipynb'));print(len(nb['cells']))"; for py in python3 /usr/local/bin/python3.12; do echo "== $py"; $py -c "import numpy, scipy, matplotlib; print('np', numpy.__version__, 'scipy', scipy.__version__, 'mpl', matplotlib.__version__)" 2>&1 | tail -1; $py -c "import loguru, IPython; print('loguru/IPython ok')" 2>&1 | tail -1; done; ls /tmp/aii_nb_test_envs/ 2>/dev/null | head
```

### [94] TOOL RESULT — Bash · 2026-10-26 13:57:32 UTC

```
{"stdout": "code_demo.ipynb: 27 cells\n27\n== python3\nnp 2.2.6 scipy 1.16.3 mpl 3.10.7\nModuleNotFoundError: No module named 'IPython'\n== /usr/local/bin/python3.12\nnp 2.2.6 scipy 1.16.3 mpl 3.10.7\nModuleNotFoundError: No module named 'IPython'", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [95] ASSISTANT · 2026-10-26 13:57:44 UTC

```
The system Python lacks IPython and loguru, so I'll go straight to the real test in the prescribed clean venv, timing each step.
```

### [96] TOOL CALL — Bash · 2026-10-26 13:57:44 UTC

```
Run notebook in clean test venv and time it:
ENV=/tmp/aii_nb_test_envs/art_e-_q5mSJGrSb-df3879c8a834 && t0=$(date +%s) && UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 $ENV && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python $ENV/bin/python jupyter ipykernel && t1=$(date +%s) && echo "venv+jupyter: $((t1-t0)) s" && $ENV/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | tail -40; t2=$(date +%s); echo "nbconvert execute: $((t2-t1)) s"
```

### [97] TOOL RESULT — Bash · 2026-10-26 13:58:02 UTC

```
{"stdout": "venv+jupyter: 3 s\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[IPKernelApp] WARNING | Kernel is running over TCP without encryption. All communication (including code and outputs) is sent in plain text and is susceptible to eavesdropping. Use IPC transport or launch with kernel manager-provisioned CurveZMQ keys to enable transport encryption.\n[NbConvertApp] Writing 544412 bytes to code_demo.ipynb\nnbconvert execute: 16 s", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [98] ASSISTANT · 2026-10-26 13:58:10 UTC

```
The notebook ran end to end in 16 s with no errors at the minimum config. Before scaling, I'll check each cell's output for warnings and wrong numbers.
```

### [99] TOOL CALL — Bash · 2026-10-26 13:58:10 UTC

```
Inspect executed notebook outputs per cell:
python3 - <<'EOF'
import json
nb=json.load(open("code_demo.ipynb"))
for i,c in enumerate(nb["cells"]):
    if c["cell_type"]!="code": continue
    print(f"=================== cell {i} (exec {c.get('execution_count')})")
    for o in c["outputs"]:
        t=o["output_type"]
        if t=="stream":
            txt="".join(o["text"]); print(f"[{o['name']}]", txt[:2500])
        elif t in ("display_data","execute_result"):
            d=o["data"]
            if "image/png" in d: print("[image/png]", len(d["image/png"]), "chars")
            elif "text/markdown" in d: print("[markdown]", "".join(d["text/markdown"])[:1800])
            else: print("[data]", list(d.keys()), "".join(d.get("text/plain",""))[:300])
        elif t=="error":
            print("[ERROR]", o["ename"], o["evalue"])
EOF
```

### [100] TOOL RESULT — Bash · 2026-10-26 13:58:10 UTC

```
{"stdout": "=================== cell 1 (exec 1)\n=================== cell 2 (exec 2)\n=================== cell 3 (exec 3)\n=================== cell 4 (exec 4)\n[stdout] GitHub data unavailable, using local mini_demo_data.json: HTTP Error 404: Not Found\ndatasets: [('T10_dec_teacher_forced', 100)]\nmetadata: 34 blocks -> K2, band_T10, commit_chain, costs, dec_GRID, dec_T10, dec_T10_L24, demo_subset, description, deviations, gen_GRID_dec, gen_T10_band, gen_T10_dec, geometry, mediation, mediation_T10, method_name, novelty_audit, post_T10, prompt_segments, rederive, rinit_GRID, rinit_T10, rinit_T10_L24, rinit_T10_band, s3_GRID, s3_T10, scan_GRID, scan_T10, t10_task_text, unit_tests_cpu, unit_tests_gpu_GRID, unit_tests_gpu_T10, verdicts\n{\n \"source_dataset\": \"T10_dec_teacher_forced\",\n \"n_source_examples\": 600,\n \"n_selected\": 100,\n \"strata_available\": {\n  \"bfs->dfs\": 20,\n  \"bfs->union_find\": 280,\n  \"dfs->union_find\": 280,\n  \"union_find->dfs\": 20\n },\n \"strata_selected\": {\n  \"bfs->dfs\": 6,\n  \"bfs->union_find\": 44,\n  \"dfs->union_find\": 44,\n  \"union_find->dfs\": 6\n },\n \"n_unique_sources\": 22,\n \"n_unique_bases\": 44,\n \"selection\": \"stratified by (class_src, class_base); round-robin over source prompts, least-used base first; strata interleaved so every prefix stays mixed\",\n \"seed\": 0\n}\n\n=================== cell 6 (exec 5)\n=================== cell 8 (exec 6)\n[stdout] recovery 0.5991696904586732 [0.5968344699411435, 0.6016892637816098]\n\n=================== cell 11 (exec 7)\n[stdout] T10_dec_teacher_forced: 10 held-out pairs -> 120 rows (pair x fit seed x rank)\n\nSOURCE T10|forced|k4|j0|bfs: Write an implementation based on breadth-first search (BFS).\nBASE   T10|twin|W5|baby: Write a correct solution that does not use baby. . . . (padded with ' .' tokens)\nshared task text: Task: write a Python function solve(n, edges) that returns the number of connected components of an undirected graph. The nodes are the integers 0 to  ...\nclass at the decision token: source -> bfs, base -> union_find\nDelta of the full-state exchange: 2.12 nats\nDelta of the DAS edit (seed 0): rank 1: 22.43, rank 2: 22.24, rank 4: 22.49, rank 8: 22.62\n\n=================== cell 13 (exec 8)\n[stdout] 13:57:59|INFO   |T10: k* = 4; recovery 8.998 CI [5.933887423337838, 13.37082513360939]\n\n[stdout] \nT10 decision site, block L* = 22: 10 held-out pairs replayed (9 with |Delta_full| >= 1 nat enter the recovery), N_BOOT = 20\nrank |  replay, seed 0 [95% CI] |  published, 552 pairs [95% CI] | random subspaces (c1) median\n   1 |   8.35 [4.92, 13.32] |         7.67 [5.11, 10.71] | -0.009\n   2 |   8.73 [5.50, 13.21] |         8.12 [5.60, 11.02] | -0.006\n   4 |   9.00 [5.93, 13.37] |         8.43 [5.94, 11.30] | -0.005\n   8 |   9.86 [7.10, 14.05] |         9.26 [6.83, 12.03] | 0.001\n\nby source class at k* = 4 (seed 0):\n  bfs        n =   5: recovery 12.20 (mean Delta DAS 23.8 vs full 1.95 nats); published 15.38 on 268 pairs\n  dfs        n =   4: recovery 5.63 (mean Delta DAS 13.0 vs full 2.31 nats); published 5.47 on 264 pairs\n\nk* = 4 (published 4); mean Delta: DAS 19.0 vs full-state 2.11 nats; OFF-MANIFOLD flag (recovery > 1.5): True (published True)\n\n=================== cell 15 (exec 9)\n[markdown] | unit-site | verdict (recomputed here) | V0 parts (TF / gen / pass ratio / McNemar) | failed controls | published verdict |\n|---|---|---|---|---|\n| T10-dec | NO HANDLE | yes / yes / no / yes | c2, c3, c4, c5 | NO HANDLE |\n| T10-band | SUFFICIENT HANDLE | yes / yes / yes / yes | c2, c5, c7 | SUFFICIENT HANDLE |\n| GRID-dec | SUFFICIENT HANDLE | yes / yes / yes / yes | c2, c3, c5, c6 | SUFFICIENT HANDLE |\n| T10-dec_L24_posthoc | POST HOC, TF-only (no generation): controls failed ['c2', 'c3'], untested [] | yes / no / no / no | c2, c3 | POST HOC, TF-only (no generation): controls failed ['c2', 'c3'], untested [] |\n| T10-dec, replayed TF (10 pairs) | NO HANDLE | yes / yes / no / yes | c2, c3, c4, c5 | (not published) |\n=================== cell 17 (exec 10)\n[stdout] 13:57:59|INFO   |{\"T10-dec\": \"NO HANDLE\", \"T10-band\": \"SUFFICIENT HANDLE\", \"GRID-dec\": \"SUFFICIENT HANDLE\", \"T10-dec_L24_posthoc\": \"POST HOC, TF-only (no generation): controls failed ['c2', 'c3'], untested []\"}\n\n[stdout] 13:57:59|INFO   |K2: DISCONFIRMED p_K2 0.03698150924537731\n\n[stdout] published: K2 DISCONFIRMED, p_K2 0.03698150924537731\n\n[markdown] | decision site | c2 label-control ratios (pass <= 0.10) | c3 random-init ratio (pass <= 0.25) | p_c2 max | p_c3 |\n|---|---|---|---|---|\n| T10 (L* = 22, k* = 4) | pi1 0.87, pi2 0.63, prompt 0.77 | 0.69 (12.1 vs 17.5 nats) | 0.0370 | 0.0005 |\n| GRID (L* = 16, k* = 4) | shuffle0 0.11, shuffle1 0.11, shuffle2 0.20 | 0.41 (3.7 vs 9.1 nats) | 0.0005 | 0.0005 |\n=================== cell 19 (exec 11)\n[markdown] # Auto-generated result tables (src/digest8.py)\n\n### T10 decision site (Qwen3-8B): teacher-forced (held-out pairs)\n\nL* = 22, k* = 4, held-out recovery at k* = 8.43 (95% two-way cluster CI 5.94 to 11.30); mean DAS Delta 17.37 nats vs full-state 2.06 nats; OFF-MANIFOLD flag: True\n\n| rank | recovery (seed 0) | by class: bfs | by class: dfs | by class: union_find |\n|---|---|---|---|---|\n| 1 | 7.67 | 15.25 | 4.20 | -0.39 |\n| 2 | 8.12 | 15.36 | 4.93 | -0.16 |\n| 4 | 8.43 | 15.38 | 5.47 | -0.07 |\n| 8 | 9.26 | 15.70 | 6.77 | 0.08 |\n\n| control | statistic | threshold | result |\n|---|---|---|---|\n| c1 random subspaces (k*) | median -0.005, p95 0.015 | median <= 0.05 | PASS |\n| c2 label control pi1 | ratio to true fit 0.87 | <= 0.10 | FAIL |\n| c2 label control pi2 | ratio to true fit 0.63 | <= 0.10 | FAIL |\n| c2 label control prompt | ratio to true fit 0.77 | <= 0.10 | FAIL |\n| c3 random-init network | ratio 0.69 (trained 17.53 vs random-init 12.08 nats) | <= 0.25 | FAIL |\n| c4 reverse interchange | -2.72 (16 pairs) | >= 0.5 | FAIL |\n| c5 projection on 64 twin PCs | retention 0.18 | >= 0.5 | FAIL |\n| c5b (twins + forced + bans basis) | retention 0.19 | >= 0.5 | FAIL |\n| c6 natural-variance share | 0.0076 vs random p95 0.0016 | > p95 | PASS |\n| c7 seed principal cosine | median first cosine 0.87 (random p99 0.07) | >= 0.5 and > p99 | PASS |\n\n### T10 task band (Qwen3-8B): teacher-forced (held-out pairs)\n\nL* = band, k* = 2, held-out recovery at k* = 0.82 (95% two-way cluster CI 0.48 to 1.16); mean DAS Delta 14.89 nats vs full-state 18.19 nats; OFF-MANIFOLD flag: False\n\n| rank | recovery (seed 0) | by class: bfs | by class: dfs | by class: union_find |\n|---|---|---|---|---|\n| 1 | 0.76 | 1.47 | 0.63 | -0.04 |\n| 2 | 0.82 | 1.57 | 0.68 | -0.04 |\n| 4 | 0.86 | 1.58 | 0.77 | -0.03 |\n| 8 | 0.\n=================== cell 21 (exec 12)\n[stdout] {\n \"tf\": {\n  \"T10_dec_replay\": {\n   \"rederived\": 8.99834980198658,\n   \"reported\": 8.99834980198658,\n   \"n\": 9,\n   \"match\": true\n  }\n },\n \"mediation\": {\n  \"rho_rederived\": 0.3914770819572048,\n  \"rho_reported\": 0.39147708195720493,\n  \"placebo_rho\": -0.03811924345883604,\n  \"placebo_fails_as_expected\": true\n },\n \"K2\": {\n  \"by_unit\": {\n   \"T10\": {\n    \"c2_fail\": true,\n    \"c3_fail\": true,\n    \"c3_ratio_from_means\": 0.6891334457006705\n   },\n   \"GRID\": {\n    \"c2_fail\": true,\n    \"c3_fail\": true,\n    \"c3_ratio_from_means\": 0.40620227344664683\n   }\n  },\n  \"status_rederived\": \"DISCONFIRMED\",\n  \"status_reported\": \"DISCONFIRMED\"\n },\n \"mcnemar_das_vs_rand\": {\n  \"T10_dec|bfs\": {\n   \"das_only\": 5,\n   \"rand_only\": 0,\n   \"p_one_sided\": 0.03125,\n   \"p_stored_scipy\": 0.03125\n  },\n  \"T10_dec|dfs\": {\n   \"das_only\": 29,\n   \"rand_only\": 0,\n   \"p_one_sided\": 1.862645149230957e-09,\n   \"p_stored_scipy\": 1.862645149230957e-09\n  },\n  \"T10_band|bfs\": {\n   \"das_only\": 28,\n   \"rand_only\": 0,\n   \"p_one_sided\": 3.725290298461914e-09,\n   \"p_stored_scipy\": 3.725290298461914e-09\n  },\n  \"T10_band|dfs\": {\n   \"das_only\": 3,\n   \"rand_only\": 0,\n   \"p_one_sided\": 0.125,\n   \"p_stored_scipy\": 0.125\n  },\n  \"GRID_dec|bfs\": {\n   \"das_only\": 17,\n   \"rand_only\": 0,\n   \"p_one_sided\": 7.62939453125e-06,\n   \"p_stored_scipy\": 7.62939453125e-06\n  }\n }\n}\npublished audit (all rows): all_match = True over 38 checks; T10_dec TF on all rows: {'rederived': 8.432892175097768, 'reported': 8.432892175097768, 'n': 552, 'match': True}\n\n=================== cell 23 (exec 13)\n[stdout] F1_scan_profile\n\n[image/png] 92848 chars\n[stdout] F2_recovery_by_rank\n\n[image/png] 68716 chars\n[stdout] F4_generation\n\n[image/png] 34552 chars\n[stdout] F5_mediation\n\n[image/png] 33004 chars\n=================== cell 25 (exec 14)\n[image/png] 205472 chars\n[markdown] | quantity | this notebook | published run |\n|---|---|---|\n| T10 decision-site TF recovery at k* [95% CI] | 9.00 [5.93, 13.37] on 9 pairs | 8.43 [5.94, 11.30] on 552 pairs |\n| k* | 4 | 4 |\n| mean Delta, DAS vs full state (nats) | 19.0 vs 2.11 | 17.4 vs 2.06 |\n| OFF-MANIFOLD flag | True | True |\n| verdict T10-dec | NO HANDLE (replayed TF), NO HANDLE (stored TF) | NO HANDLE |\n| verdicts T10-band / GRID-dec | SUFFICIENT HANDLE / SUFFICIENT HANDLE | SUFFICIENT HANDLE / SUFFICIENT HANDLE |\n| K2 (p_K2) | DISCONFIRMED (0.037) | DISCONFIRMED (0.037) |\n| T10 generation, target DFS: correct programs DAS / FULL / RAND / BASE (of 30) | stored | 29 / 2 / 0 / 0 |\n| T10 generation, target BFS: correct (attempted BFS) DAS / FULL / RAND / BASE | stored | 5 / 0 / 0 / 0 (29 DAS attempts) |\n| GRID generation, target BFS: DAS / FULL / RAND / BASE | stored | 22 / 10 / 5 / 6 |\n| novel ('other') algorithms among correct programs | stored | 0 of 1857 |", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [101] THINKING · 2026-10-26 13:58:20 UTC

```
Everything matches the published run—verdicts, K2, p_K2, stdlib audit, McNemar re-tests, and the 10-pair replay (k*=4, OFF-MANIFOLD flag) all agree. Next I'll extract the rendered figures into a temporary workspace folder to check their quality, then delete it afterward.
```

### [102] TOOL CALL — Bash · 2026-10-26 13:58:20 UTC

```
Extract notebook figure PNGs for review:
mkdir -p _tmp_png && python3 - <<'EOF'
import json, base64
nb=json.load(open("code_demo.ipynb"))
n=0
for i,c in enumerate(nb["cells"]):
    if c["cell_type"]!="code": continue
    for j,o in enumerate(c["outputs"]):
        if o["output_type"] in ("display_data","execute_result") and "image/png" in o["data"]:
            p=f"_tmp_png/cell{i:02d}_{j}.png"; open(p,"wb").write(base64.b64decode(o["data"]["image/png"])); n+=1; print(p)
EOF
```

### [103] TOOL RESULT — Bash · 2026-10-26 13:58:20 UTC

```
{"stdout": "_tmp_png/cell23_1.png\n_tmp_png/cell23_3.png\n_tmp_png/cell23_5.png\n_tmp_png/cell23_7.png\n_tmp_png/cell25_0.png", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [104] TOOL CALL — Read · 2026-10-26 13:58:28 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_tmp_png/cell25_0.png
```

### [105] TOOL RESULT — Read · 2026-10-26 13:58:28 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [106] TOOL CALL — Read · 2026-10-26 13:58:28 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_tmp_png/cell23_1.png
```

### [107] TOOL RESULT — Read · 2026-10-26 13:58:28 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [108] TOOL CALL — Read · 2026-10-26 13:58:28 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_tmp_png/cell23_3.png
```

### [109] TOOL RESULT — Read · 2026-10-26 13:58:28 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [110] THINKING · 2026-10-26 13:59:06 UTC

```
Found a real bug in panel (a): its x-label variable `L` was overwritten by the digest cell's Markdown lines, causing the table text to render across the figure—I'll fix it using `md["dec_T10"]["L_star"]`, make room for legends, and spread out overlapping centroid labels. First, I'll move on to the remaining two figures.
```

### [111] TOOL CALL — Read · 2026-10-26 13:59:06 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_tmp_png/cell23_5.png
```

### [112] TOOL RESULT — Read · 2026-10-26 13:59:06 UTC

```
{"type": "image", "file": {"base64": "iVBORw0KGgoAAAANSUhEUgAABM4AAAFSCAYAAAAKFZPKAAAAOnRFWHRTb2Z0d2FyZQBNYXRwbG90bGliIHZlcnNpb24zLjEwLjAsIGh0dHBzOi8vbWF0cGxvdGxpYi5vcmcvlHJYcgAAAAlwSFlzAAAPYQAAD2EBqD+naQAAZKRJREFUeJzt3Xd0FPX+//HXpof0EISFhKAUjV5kARWuQaULFlSuggKK+EWDEBAQ1IB0CNaLLQhX4NoAxYIgqFdRUeJVUCAq1UINJLSQBqSR/P7gl72sCbCT7KTt83HOnLMzO+U9Q5bXzmc/M2MpKSkpEQAAAAAAAAAHHtVdAAAAAAAAAFAT0XAGAAAAAAAAlIOGMwAAAAAAAKAcNJwBAAAAAAAA5aDhDAAAAAAAACgHDWcAAAAAAABAOWg4AwAAAAAAAMpBwxkAAAAAAAB... [truncated, 34762 chars total]
```

### [113] TOOL CALL — Read · 2026-10-26 13:59:06 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_tmp_png/cell23_7.png
```

### [114] TOOL RESULT — Read · 2026-10-26 13:59:06 UTC

```
{"type": "image", "file": {"base64": "iVBORw0KGgoAAAANSUhEUgAAAccAAAFkCAYAAABVdPDyAAAAOnRFWHRTb2Z0d2FyZQBNYXRwbG90bGliIHZlcnNpb24zLjEwLjAsIGh0dHBzOi8vbWF0cGxvdGxpYi5vcmcvlHJYcgAAAAlwSFlzAAAPYQAAD2EBqD+naQAAYB1JREFUeJzt3XdYU+fbB/BvQIYQQgggMiKCCOIAXFVL1YrWrdC6rdZReYsg2lptnWCtq9q6qlRrHW3FUWtR62hxYB11VnBRBzJkCzLCns/7hz9ODQTIkYQA3p/rygU5OeM+5yS585zzDAFjjIEQQgghHC1NB0AIIYQ0NJQcCSGEkEooORJCCCGVUHIkhBBCKqHkSAghhFRCyZEQQgiphJIjIYQQUgklR0IIIaQSSo6EEEJIJZQcSaPk5uaGPXv2AACCg4Px5ptvvvK6Ll6... [truncated, 33212 chars total]
```

### [115] THINKING · 2026-10-26 14:00:06 UTC

```
F4 and F5 match the original figure code, but F5's x-label gets clipped inline since the original saves PNGs with tight bounding boxes. I'll update `save()` to render to memory with that same setting and display the PNG, then apply the fixes in the builder.
```

### [116] TOOL CALL — Edit · 2026-10-26 14:00:06 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py
OLD: import json
import math
import random
import re
import sys
import types
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from loguru import logger
from scipy import stats

# notebook addition: render the digest tables (Markdown) inline
from IPython.display import Markdown, display
NEW: import io
import json
import math
import random
import re
import sys
import types
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from loguru import logger
from scipy import stats

# notebook addition: show the digest tables (Markdown) and the saved figures inline
from IPython.display import Image, Markdown, display
```

### [117] TOOL RESULT — Edit · 2026-10-26 14:00:06 UTC

```
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py", "oldString": "import json\nimport math\nimport random\nimport re\nimport sys\nimport types\nfrom pathlib import Path\nfrom typing import Any\n\nimport matplotlib.pyplot as plt\nimport numpy as np\nfrom loguru import logger\nfrom scipy import stats\n\n# notebook addition: render the digest tables (Markdown) inline\nfrom IPython.display import Markdown, display", "newString": "import io\nimport json\nimport math\nimport random\nimport re\nimport sys\nimport types\nfrom pathlib import Path\nfrom typing import Any\n\nimport matplotlib.pyplot as plt\nimport numpy as np\nfrom loguru import logger\nfrom scipy import stats\n\n# notebook addition: show the digest tables (Markdown) and the saved figures inline\nfrom IPython.display import Image, Markdown, display", "originalFile": null, "structuredPatch": [{"oldStart": 82, "oldLines": 6, "newStart": 82, "newLines": 7, "lines": [" ", " # Import blocks of the artifact's CPU stages: src/stats8.py, src/analysis8.py, src/digest8.py, src/figures8.py and", " # audit/rederive.py. (figures8.py also calls matplotlib.use(\"Agg\") to write files; here the figures are shown inline.)", "+import io", " import json", " import math", " import random"]}, {"oldStart": 96, "oldLines": 8, "newStart": 97, "newLines": 8, "lines": [" from loguru import logger", " from scipy import stats", " ", "-# notebook addition: render the digest tables (Markdown) inline", "-from IPython.display import Markdown, display", "+# notebook addition: show the digest tables (Markdown) and the saved figures inline", "+from IPython.display import Image, Markdown, display", " ", " # src/cfg8.py:setup_logging(), without its file sink (logs/<stage>.log)", " logger.remove()"]}], "userModified": false, "replaceAll": false}
```

### [118] TOOL CALL — Edit · 2026-10-26 14:00:06 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py
OLD: def save(fig: Any, name: str) -> None:
    # original: fig.savefig(FIGS / f"{name}.pdf"); fig.savefig(FIGS / f"{name}.png", dpi=180); plt.close(fig)
    print(name)
    plt.show()
NEW: def save(fig: Any, name: str) -> None:
    # original: fig.savefig(FIGS / f"{name}.pdf", bbox_inches="tight"); fig.savefig(FIGS / f"{name}.png", dpi=180,
    # bbox_inches="tight"); plt.close(fig) -- here the PNG goes to memory (lower dpi) and is displayed
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    print(name)
    display(Image(buf.getvalue()))
```

### [119] TOOL RESULT — Edit · 2026-10-26 14:00:06 UTC

```
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py", "oldString": "def save(fig: Any, name: str) -> None:\n    # original: fig.savefig(FIGS / f\"{name}.pdf\"); fig.savefig(FIGS / f\"{name}.png\", dpi=180); plt.close(fig)\n    print(name)\n    plt.show()", "newString": "def save(fig: Any, name: str) -> None:\n    # original: fig.savefig(FIGS / f\"{name}.pdf\", bbox_inches=\"tight\"); fig.savefig(FIGS / f\"{name}.png\", dpi=180,\n    # bbox_inches=\"tight\"); plt.close(fig) -- here the PNG goes to memory (lower dpi) and is displayed\n    buf = io.BytesIO()\n    fig.savefig(buf, format=\"png\", dpi=110, bbox_inches=\"tight\")\n    plt.close(fig)\n    print(name)\n    display(Image(buf.getvalue()))", "originalFile": null, "structuredPatch": [{"oldStart": 957, "oldLines": 9, "newStart": 957, "newLines": 13, "lines": [" ", " ", " def save(fig: Any, name: str) -> None:", "-    # original: fig.savefig(FIGS / f\"{name}.pdf\"); fig.savefig(FIGS / f\"{name}.png\", dpi=180); plt.close(fig)", "+    # original: fig.savefig(FIGS / f\"{name}.pdf\", bbox_inches=\"tight\"); fig.savefig(FIGS / f\"{name}.png\", dpi=180,", "+    # bbox_inches=\"tight\"); plt.close(fig) -- here the PNG goes to memory (lower dpi) and is displayed", "+    buf = io.BytesIO()", "+    fig.savefig(buf, format=\"png\", dpi=110, bbox_inches=\"tight\")", "+    plt.close(fig)", "     print(name)", "-    plt.show()", "+    display(Image(buf.getvalue()))", " ", " ", " def f1_scan() -> None:"]}], "userModified": false, "replaceAll": false}
```

### [120] TOOL CALL — Edit · 2026-10-26 14:00:06 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py
OLD: x0, x1 = min(min(d_full.values()), 0.0) - 0.3, max(d_full.values()) * 1.08
xx = np.array([0.0, x1])
ax.plot(xx, xx, "k--", lw=0.8, label="DAS = full-state exchange (recovery 1)")
ax.plot(xx, OFF_MANIFOLD * xx, "k:", lw=0.8, label=f"ratio {OFF_MANIFOLD} (OFF-MANIFOLD threshold on the means)")
ax.axvspan(x0, 1.0, color="#dddddd", alpha=0.5, label="|Delta_full| < 1 nat: left out of the recovery")
ax.axhline(0, color="#999999", lw=0.5)
ax.set_xlim(x0, x1)
ax.set_xlabel(f"full-state exchange Delta at block {L} (nats)")
ax.set_ylabel(f"rank-{kstar} DAS Delta, seed 0 (nats)")
ax.set_title(f"(a) T10 decision site, {len(held)} held-out pairs: recovery {main['recovery']:.2f} "
             f"(DAS {main['mean_delta_edit']:.1f} vs full {main['mean_delta_full']:.2f} nats)", fontsize=9)
ax.legend(fontsize=7, loc="upper left")
NEW: x0, x1 = min(min(d_full.values()), 0.0) - 0.3, max(d_full.values()) * 1.08
xx = np.array([0.0, x1])
ax.plot(xx, xx, "k--", lw=0.8, label="DAS = full-state exchange (recovery 1)")
ax.plot(xx, OFF_MANIFOLD * xx, "k:", lw=0.8, label=f"ratio {OFF_MANIFOLD} (OFF-MANIFOLD threshold on the means)")
ax.axvspan(x0, 1.0, color="#dddddd", alpha=0.5, label="|Delta_full| < 1 nat: left out of the recovery")
ax.axhline(0, color="#999999", lw=0.5)
ax.set_xlim(x0, x1)
ax.set_ylim(min(min(d_das.values()), 0.0) - 1.0, max(d_das.values()) * 1.45)     # headroom for the legend
ax.set_xlabel(f"full-state exchange Delta at block {md['dec_T10']['L_star']} (nats)")
ax.set_ylabel(f"rank-{kstar} DAS Delta, seed 0 (nats)")
ax.set_title(f"(a) T10 decision site, {len(held)} held-out pairs: recovery {main['recovery']:.2f} "
             f"(DAS {main['mean_delta_edit']:.1f} vs full {main['mean_delta_full']:.2f} nats)", fontsize=9)
ax.legend(fontsize=7, loc="upper left", framealpha=0.9)
```

### [121] TOOL RESULT — Edit · 2026-10-26 14:00:06 UTC

```
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py", "oldString": "x0, x1 = min(min(d_full.values()), 0.0) - 0.3, max(d_full.values()) * 1.08\nxx = np.array([0.0, x1])\nax.plot(xx, xx, \"k--\", lw=0.8, label=\"DAS = full-state exchange (recovery 1)\")\nax.plot(xx, OFF_MANIFOLD * xx, \"k:\", lw=0.8, label=f\"ratio {OFF_MANIFOLD} (OFF-MANIFOLD threshold on the means)\")\nax.axvspan(x0, 1.0, color=\"#dddddd\", alpha=0.5, label=\"|Delta_full| < 1 nat: left out of the recovery\")\nax.axhline(0, color=\"#999999\", lw=0.5)\nax.set_xlim(x0, x1)\nax.set_xlabel(f\"full-state exchange Delta at block {L} (nats)\")\nax.set_ylabel(f\"rank-{kstar} DAS Delta, seed 0 (nats)\")\nax.set_title(f\"(a) T10 decision site, {len(held)} held-out pairs: recovery {main['recovery']:.2f} \"\n             f\"(DAS {main['mean_delta_edit']:.1f} vs full {main['mean_delta_full']:.2f} nats)\", fontsize=9)\nax.legend(fontsize=7, loc=\"upper left\")", "newString": "x0, x1 = min(min(d_full.values()), 0.0) - 0.3, max(d_full.values()) * 1.08\nxx = np.array([0.0, x1])\nax.plot(xx, xx, \"k--\", lw=0.8, label=\"DAS = full-state exchange (recovery 1)\")\nax.plot(xx, OFF_MANIFOLD * xx, \"k:\", lw=0.8, label=f\"ratio {OFF_MANIFOLD} (OFF-MANIFOLD threshold on the means)\")\nax.axvspan(x0, 1.0, color=\"#dddddd\", alpha=0.5, label=\"|Delta_full| < 1 nat: left out of the recovery\")\nax.axhline(0, color=\"#999999\", lw=0.5)\nax.set_xlim(x0, x1)\nax.set_ylim(min(min(d_das.values()), 0.0) - 1.0, max(d_das.values()) * 1.45)     # headroom for the legend\nax.set_xlabel(f\"full-state exchange Delta at block {md['dec_T10']['L_star']} (nats)\")\nax.set_ylabel(f\"rank-{kstar} DAS Delta, seed 0 (nats)\")\nax.set_title(f\"(a) T10 decision site, {len(held)} held-out pairs: recovery {main['recovery']:.2f} \"\n             f\"(DAS {main['mean_delta_edit']:.1f} vs full {main['mean_delta_full']:.2f} nats)\", fontsize=9)\nax.legend(fontsize=7, loc=\"upper left\", framealpha=0.9)", "originalFile": null, "structuredPatch": [{"oldStart": 1113, "oldLines": 11, "newStart": 1113, "newLines": 12, "lines": [" ax.axvspan(x0, 1.0, color=\"#dddddd\", alpha=0.5, label=\"|Delta_full| < 1 nat: left out of the recovery\")", " ax.axhline(0, color=\"#999999\", lw=0.5)", " ax.set_xlim(x0, x1)", "-ax.set_xlabel(f\"full-state exchange Delta at block {L} (nats)\")", "+ax.set_ylim(min(min(d_das.values()), 0.0) - 1.0, max(d_das.values()) * 1.45)     # headroom for the legend", "+ax.set_xlabel(f\"full-state exchange Delta at block {md['dec_T10']['L_star']} (nats)\")", " ax.set_ylabel(f\"rank-{kstar} DAS Delta, seed 0 (nats)\")", " ax.set_title(f\"(a) T10 decision site, {len(held)} held-out pairs: recovery {main['recovery']:.2f} \"", "              f\"(DAS {main['mean_delta_edit']:.1f} vs full {main['mean_delta_full']:.2f} nats)\", fontsize=9)", "-ax.legend(fontsize=7, loc=\"upper left\")", "+ax.legend(fontsize=7, loc=\"upper left\", framealpha=0.9)", " ", " # (b) recovery by rank: this replay vs the published table", " ax = axes[0, 1]"]}], "userModified": false, "replaceAll": false}
```

### [122] TOOL CALL — Edit · 2026-10-26 14:00:06 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py
OLD: ax.set_title(f"(b) recovery by rank; k* = {kstar}; dotted line = OFF-MANIFOLD {OFF_MANIFOLD}", fontsize=9)
ax.legend(fontsize=7)

# (c, d) stored geometry: group centroids of the metric-MDS embedding of every prompt's R_8 coordinates
for ax, unit, tag in ((axes[1, 0], "T10", "(c)"), (axes[1, 1], "GRID", "(d)")):
    g = md["geometry"][unit]
    for grp, (x, y) in g["group_centroids_mds"].items():
        n_impl = g["implemented_counts"].get(grp, 0)
        is_cls = grp in ("bfs", "dfs", "union_find", "astar_gbfs", "iddfs")
        ax.scatter([x], [y], s=(80 + 8 * n_impl) if is_cls else 45, marker="*" if is_cls else "o",
                   color=COL.get(grp, "#333333"), edgecolor="k", linewidth=0.5, zorder=3)
        lab = f"{grp}: {n_impl} implemented" if grp in g["implemented_counts"] else grp
        ax.annotate(lab, (x, y), fontsize=8, xytext=(6, 4), textcoords="offset points")
NEW: ax.set_title(f"(b) recovery by rank; k* = {kstar}; dotted line = OFF-MANIFOLD {OFF_MANIFOLD}", fontsize=9)
ax.legend(fontsize=7, loc="lower left", bbox_to_anchor=(0.0, 0.1))

# (c, d) stored geometry: group centroids of the metric-MDS embedding of every prompt's R_8 coordinates
LABEL_OFFSET = {"twin": (6, -12), "padtwin": (6, 5), "p0": (-16, -14), "instr": (-30, 3), "seed": (6, 4)}
for ax, unit, tag in ((axes[1, 0], "T10", "(c)"), (axes[1, 1], "GRID", "(d)")):
    g = md["geometry"][unit]
    for grp, (x, y) in g["group_centroids_mds"].items():
        n_impl = g["implemented_counts"].get(grp, 0)
        is_cls = grp in ("bfs", "dfs", "union_find", "astar_gbfs", "iddfs")
        ax.scatter([x], [y], s=(80 + 8 * n_impl) if is_cls else 45, marker="*" if is_cls else "o",
                   color=COL.get(grp, "#333333"), edgecolor="k", linewidth=0.5, zorder=3)
        lab = f"{grp}: {n_impl} implemented" if grp in g["implemented_counts"] else grp
        ax.annotate(lab, (x, y), fontsize=8, xytext=LABEL_OFFSET.get(grp, (6, 4)), textcoords="offset points")
```

### [123] TOOL RESULT — Edit · 2026-10-26 14:00:06 UTC

```
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py", "oldString": "ax.set_title(f\"(b) recovery by rank; k* = {kstar}; dotted line = OFF-MANIFOLD {OFF_MANIFOLD}\", fontsize=9)\nax.legend(fontsize=7)\n\n# (c, d) stored geometry: group centroids of the metric-MDS embedding of every prompt's R_8 coordinates\nfor ax, unit, tag in ((axes[1, 0], \"T10\", \"(c)\"), (axes[1, 1], \"GRID\", \"(d)\")):\n    g = md[\"geometry\"][unit]\n    for grp, (x, y) in g[\"group_centroids_mds\"].items():\n        n_impl = g[\"implemented_counts\"].get(grp, 0)\n        is_cls = grp in (\"bfs\", \"dfs\", \"union_find\", \"astar_gbfs\", \"iddfs\")\n        ax.scatter([x], [y], s=(80 + 8 * n_impl) if is_cls else 45, marker=\"*\" if is_cls else \"o\",\n                   color=COL.get(grp, \"#333333\"), edgecolor=\"k\", linewidth=0.5, zorder=3)\n        lab = f\"{grp}: {n_impl} implemented\" if grp in g[\"implemented_counts\"] else grp\n        ax.annotate(lab, (x, y), fontsize=8, xytext=(6, 4), textcoords=\"offset points\")", "newString": "ax.set_title(f\"(b) recovery by rank; k* = {kstar}; dotted line = OFF-MANIFOLD {OFF_MANIFOLD}\", fontsize=9)\nax.legend(fontsize=7, loc=\"lower left\", bbox_to_anchor=(0.0, 0.1))\n\n# (c, d) stored geometry: group centroids of the metric-MDS embedding of every prompt's R_8 coordinates\nLABEL_OFFSET = {\"twin\": (6, -12), \"padtwin\": (6, 5), \"p0\": (-16, -14), \"instr\": (-30, 3), \"seed\": (6, 4)}\nfor ax, unit, tag in ((axes[1, 0], \"T10\", \"(c)\"), (axes[1, 1], \"GRID\", \"(d)\")):\n    g = md[\"geometry\"][unit]\n    for grp, (x, y) in g[\"group_centroids_mds\"].items():\n        n_impl = g[\"implemented_counts\"].get(grp, 0)\n        is_cls = grp in (\"bfs\", \"dfs\", \"union_find\", \"astar_gbfs\", \"iddfs\")\n        ax.scatter([x], [y], s=(80 + 8 * n_impl) if is_cls else 45, marker=\"*\" if is_cls else \"o\",\n                   color=COL.get(grp, \"#333333\"), edgecolor=\"k\", linewidth=0.5, zorder=3)\n        lab = f\"{grp}: {n_impl} implemented\" if grp in g[\"implemented_counts\"] else grp\n        ax.annotate(lab, (x, y), fontsize=8, xytext=LABEL_OFFSET.get(grp, (6, 4)), textcoords=\"offset points\")", "originalFile": null, "structuredPatch": [{"oldStart": 1147, "oldLines": 9, "newStart": 1147, "newLines": 10, "lines": [" ax.set_xlabel(\"rank k of the DAS map\")", " ax.set_ylabel(\"normalised recovery (DAS / full state)\")", " ax.set_title(f\"(b) recovery by rank; k* = {kstar}; dotted line = OFF-MANIFOLD {OFF_MANIFOLD}\", fontsize=9)", "-ax.legend(fontsize=7)", "+ax.legend(fontsize=7, loc=\"lower left\", bbox_to_anchor=(0.0, 0.1))", " ", " # (c, d) stored geometry: group centroids of the metric-MDS embedding of every prompt's R_8 coordinates", "+LABEL_OFFSET = {\"twin\": (6, -12), \"padtwin\": (6, 5), \"p0\": (-16, -14), \"instr\": (-30, 3), \"seed\": (6, 4)}", " for ax, unit, tag in ((axes[1, 0], \"T10\", \"(c)\"), (axes[1, 1], \"GRID\", \"(d)\")):", "     g = md[\"geometry\"][unit]", "     for grp, (x, y) in g[\"group_centroids_mds\"].items():"]}, {"oldStart": 1158, "oldLines": 7, "newStart": 1159, "newLines": 7, "lines": ["         ax.scatter([x], [y], s=(80 + 8 * n_impl) if is_cls else 45, marker=\"*\" if is_cls else \"o\",", "                    color=COL.get(grp, \"#333333\"), edgecolor=\"k\", linewidth=0.5, zorder=3)", "         lab = f\"{grp}: {n_impl} implemented\" if grp in g[\"implemented_counts\"] else grp", "-        ax.annotate(lab, (x, y), fontsize=8, xytext=(6, 4), textcoords=\"offset points\")", "+        ax.annotate(lab, (x, y), fontsize=8, xytext=LABEL_OFFSET.get(grp, (6, 4)), textcoords=\"offset points\")", "     ax.set_xlabel(\"MDS axis 1 (activation units)\")", "     ax.set_ylabel(\"MDS axis 2 (activation units)\")", "     ax.set_title(f\"{tag} {unit} ({'Qwen3-8B' if unit == 'T10' else 'gemma-3-4b-it'}), block {g['L']}: group centroids \""]}], "userModified": false, "replaceAll": false}
```

### [124] THINKING · 2026-10-26 14:00:24 UTC

```
Now I'll scale up: I'm adding optional arguments to the builder for the four demo knobs so each round regenerates the notebook with new values. Starting round 1 with N_PAIRS=25, N_BOOT=200, N_BOOT_CLASS=100, and seeds (0, 1), while also verifying the figure fixes.
```

### [125] TOOL CALL — Edit · 2026-10-26 14:00:24 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py
OLD: def build():
    nb = {"cells": [], "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                    "language_info": {"name": "python", "version": "3.12"}},
          "nbformat": 4, "nbformat_minor": 5}
    for i, (kind, src) in enumerate(CELLS):
NEW: def build():
    import argparse
    import re
    ap = argparse.ArgumentParser()
    ap.add_argument("--n_pairs", type=int)
    ap.add_argument("--n_boot", type=int)
    ap.add_argument("--n_boot_class", type=int)
    ap.add_argument("--seeds")
    a = ap.parse_args()
    knobs = {"N_PAIRS": a.n_pairs, "N_BOOT": a.n_boot, "N_BOOT_CLASS": a.n_boot_class, "DEMO_SEEDS": a.seeds}
    for i, (kind, src) in enumerate(CELLS):
        for name, val in knobs.items():
            if val is not None:
                src = re.sub(rf"^{name} = \S+( +#)", lambda m: f"{name} = {val}" + " " * max(1, len(m.group(0)) - len(f"{name} = {val}") - 1) + "#", src, flags=re.M)
        CELLS[i] = (kind, src)
    nb = {"cells": [], "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                    "language_info": {"name": "python", "version": "3.12"}},
          "nbformat": 4, "nbformat_minor": 5}
    for i, (kind, src) in enumerate(CELLS):
```

### [126] TOOL RESULT — Edit · 2026-10-26 14:00:24 UTC

```
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py", "oldString": "def build():\n    nb = {\"cells\": [], \"metadata\": {\"kernelspec\": {\"display_name\": \"Python 3\", \"language\": \"python\", \"name\": \"python3\"},\n                                    \"language_info\": {\"name\": \"python\", \"version\": \"3.12\"}},\n          \"nbformat\": 4, \"nbformat_minor\": 5}\n    for i, (kind, src) in enumerate(CELLS):", "newString": "def build():\n    import argparse\n    import re\n    ap = argparse.ArgumentParser()\n    ap.add_argument(\"--n_pairs\", type=int)\n    ap.add_argument(\"--n_boot\", type=int)\n    ap.add_argument(\"--n_boot_class\", type=int)\n    ap.add_argument(\"--seeds\")\n    a = ap.parse_args()\n    knobs = {\"N_PAIRS\": a.n_pairs, \"N_BOOT\": a.n_boot, \"N_BOOT_CLASS\": a.n_boot_class, \"DEMO_SEEDS\": a.seeds}\n    for i, (kind, src) in enumerate(CELLS):\n        for name, val in knobs.items():\n            if val is not None:\n                src = re.sub(rf\"^{name} = \\S+( +#)\", lambda m: f\"{name} = {val}\" + \" \" * max(1, len(m.group(0)) - len(f\"{name} = {val}\") - 1) + \"#\", src, flags=re.M)\n        CELLS[i] = (kind, src)\n    nb = {\"cells\": [], \"metadata\": {\"kernelspec\": {\"display_name\": \"Python 3\", \"language\": \"python\", \"name\": \"python3\"},\n                                    \"language_info\": {\"name\": \"python\", \"version\": \"3.12\"}},\n          \"nbformat\": 4, \"nbformat_minor\": 5}\n    for i, (kind, src) in enumerate(CELLS):", "originalFile": null, "structuredPatch": [{"oldStart": 1231, "oldLines": 6, "newStart": 1231, "newLines": 20, "lines": [" ", " ", " def build():", "+    import argparse", "+    import re", "+    ap = argparse.ArgumentParser()", "+    ap.add_argument(\"--n_pairs\", type=int)", "+    ap.add_argument(\"--n_boot\", type=int)", "+    ap.add_argument(\"--n_boot_class\", type=int)", "+    ap.add_argument(\"--seeds\")", "+    a = ap.parse_args()", "+    knobs = {\"N_PAIRS\": a.n_pairs, \"N_BOOT\": a.n_boot, \"N_BOOT_CLASS\": a.n_boot_class, \"DEMO_SEEDS\": a.seeds}", "+    for i, (kind, src) in enumerate(CELLS):", "+        for name, val in knobs.items():", "+            if val is not None:", "+                src = re.sub(rf\"^{name} = \\S+( +#)\", lambda m: f\"{name} = {val}\" + \" \" * max(1, len(m.group(0)) - len(f\"{name} = {val}\") - 1) + \"#\", src, flags=re.M)", "+        CELLS[i] = (kind, src)", "     nb = {\"cells\": [], \"metadata\": {\"kernelspec\": {\"display_name\": \"Python 3\", \"language\": \"python\", \"name\": \"python3\"},", "                                     \"language_info\": {\"name\": \"python\", \"version\": \"3.12\"}},", "           \"nbformat\": 4, \"nbformat_minor\": 5}"]}], "userModified": false, "replaceAll": false}
```

### [127] TOOL CALL — Bash · 2026-10-26 14:00:24 UTC

```
Scaling round 1: build with 25 pairs and run test:
python3 _build_notebook.py --n_pairs 25 --n_boot 200 --n_boot_class 100 --seeds "(0, 1)" && python3 -c "
import json;nb=json.load(open('code_demo.ipynb'))
src=''.join(nb['cells'][6]['source']); print(src[:700])" && ENV=/tmp/aii_nb_test_envs/art_e-_q5mSJGrSb-df3879c8a834 && t0=$(date +%s) && UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 $ENV && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python $ENV/bin/python jupyter ipykernel && t1=$(date +%s) && $ENV/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | grep -v "Kernel is running over TCP" | tail -20; t2=$(date +%s); echo "venv: $((t1-t0)) s; nbconvert execute: $((t2-t1)) s"
```

### [128] TOOL RESULT — Bash · 2026-10-26 14:01:12 UTC

```
{"stdout": "code_demo.ipynb: 27 cells\n# ---------------------------------------------------------------- demo knobs (originals in the comments)\nN_PAIRS = 25          # held-out teacher-forced pairs replayed (max 100 in mini_demo_data.json; the run: 600, full_method_out.json)\nN_BOOT = 200          # two-way cluster-bootstrap resamples per recovery CI (original: N_BOOT = 2000, src/cfg8.py)\nN_BOOT_CLASS = 100    # resamples for the per-class recovery (original: n_boot=500 in src/run_dec.py:by_class)\nDEMO_SEEDS = (0, 1)   # fit seeds whose stored Deltas are replayed; must contain 0 (original: FIT_SEEDS = (0, 1, 2))\n\n# ---------------------------------------------------------------- protocol constants (src/cfg8.py, commit #0)\nRANKS =\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[NbConvertApp] Writing 574013 bytes to code_demo.ipynb\nvenv: 1 s; nbconvert execute: 47 s", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [129] ASSISTANT · 2026-10-26 14:01:23 UTC

```
Round 1 passed, but it took 47 s against 16 s before. Let me read per-cell timings from the notebook metadata to see where the time goes.
```

### [130] TOOL CALL — Bash · 2026-10-26 14:01:23 UTC

```
Show per-cell execution times and errors:
python3 - <<'EOF'
import json
from datetime import datetime
nb=json.load(open("code_demo.ipynb"))
def t(s): return datetime.fromisoformat(s.replace("Z","+00:00"))
for i,c in enumerate(nb["cells"]):
    if c["cell_type"]!="code": continue
    ex=c["metadata"].get("execution",{})
    if "iopub.execute_input" in ex and "shell.execute_reply" in ex:
        print(i, round((t(ex["shell.execute_reply"])-t(ex["iopub.execute_input"])).total_seconds(),2), "s")
    for o in c["outputs"]:
        if o["output_type"]=="error": print("ERROR", o["ename"], o["evalue"])
        if o["output_type"]=="stream" and o["name"]=="stderr": print("STDERR", "".join(o["text"])[:500])
EOF
```

### [131] TOOL RESULT — Bash · 2026-10-26 14:01:23 UTC

```
{"stdout": "1 39.97 s\n2 0.68 s\n3 0.01 s\n4 0.29 s\n6 0.0 s\n8 0.04 s\n11 0.01 s\n13 0.06 s\n15 0.01 s\n17 0.01 s\n19 0.01 s\n21 0.01 s\n23 0.71 s\n25 0.4 s", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [132] ASSISTANT · 2026-10-26 14:01:29 UTC

```
The extra time is all in the install cell (40 s of pip into the fresh venv). Every processing cell takes under 1 s. Let me check that the figure fixes rendered correctly.
```

### [133] TOOL CALL — Bash · 2026-10-26 14:01:29 UTC

```
Extract updated figures for review:
rm -f _tmp_png/*.png && python3 - <<'EOF'
import json, base64
nb=json.load(open("code_demo.ipynb"))
for i,c in enumerate(nb["cells"]):
    if c["cell_type"]!="code": continue
    for j,o in enumerate(c["outputs"]):
        if o["output_type"] in ("display_data","execute_result") and "image/png" in o["data"]:
            p=f"_tmp_png/cell{i:02d}_{j}.png"; open(p,"wb").write(base64.b64decode(o["data"]["image/png"])); print(p, len(o["data"]["image/png"]))
EOF
```

### [134] TOOL RESULT — Bash · 2026-10-26 14:01:31 UTC

```
{"stdout": "_tmp_png/cell23_1.png 109436\n_tmp_png/cell23_3.png 74480\n_tmp_png/cell23_5.png 37852\n_tmp_png/cell23_7.png 39028\n_tmp_png/cell25_0.png 202472", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [135] TOOL CALL — Read · 2026-10-26 14:01:35 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_tmp_png/cell25_0.png
```

### [136] TOOL RESULT — Read · 2026-10-26 14:01:35 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [137] TOOL CALL — Read · 2026-10-26 14:01:35 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_tmp_png/cell23_7.png
```

### [138] TOOL RESULT — Read · 2026-10-26 14:01:35 UTC

```
{"type": "image", "file": {"base64": "iVBORw0KGgoAAAANSUhEUgAAAfQAAAGICAYAAAC3NhIwAAAAOnRFWHRTb2Z0d2FyZQBNYXRwbG90bGliIHZlcnNpb24zLjEwLjAsIGh0dHBzOi8vbWF0cGxvdGxpYi5vcmcvlHJYcgAAAAlwSFlzAAAQ6wAAEOsBUJTofAAAccNJREFUeJzt3XdUFNfbB/DvUpYOoiAgIKgYAaUoiqBGLIixEI1JfsZoRIwldgFNNBZskdiwYdRoRE00UaNGJUbF3hBRERtILyKgKBGQDvf9g5cJS12GXcryfM7hHPZOe2Zmd5+9M3fuFTDGGAghhBDSrMk1dgCEEEIIqT9K6IQQQogMoIROCCGEyABK6IQQQogMoIROCCGEyABK6IQQQogMoIROCCGEyABK6IQQQogMoIROCCGEyABK6IQQQogMoIROWiQ/Pz+Ymppyryd... [truncated, 39236 chars total]
```

### [139] THINKING · 2026-10-26 14:01:45 UTC

```
The figure renders correctly now, though F5's x-label is still clipped on the right. I'll check if the artifact's saved F5 has the same clipping to see if it originates from the original figure code.
```

### [140] TOOL CALL — Read · 2026-10-26 14:01:45 UTC

```
/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40/figures/F5_mediation.png
```

### [141] TOOL RESULT — Read · 2026-10-26 14:01:45 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [142] ASSISTANT · 2026-10-26 14:02:01 UTC

```
The artifact's own F5 shows the full label. Ours is clipped under matplotlib 3.10.0, Colab's version. I'll reproduce it directly in the test venv to find the cause.
```

### [143] TOOL CALL — Bash · 2026-10-26 14:02:01 UTC

```
Debug clipped F5 x-label with matplotlib 3.10:
/tmp/aii_nb_test_envs/art_e-_q5mSJGrSb-df3879c8a834/bin/python - <<'EOF'
import io, struct, matplotlib
print(matplotlib.__version__, matplotlib.get_backend())
import matplotlib.pyplot as plt
plt.rcParams.update({"font.size": 9})
def dims(b):
    w,h=struct.unpack(">II", b[16:24]); return w,h
for backend_note in ["default"]:
    fig, ax = plt.subplots(figsize=(5, 3.6))
    ax.scatter([0,1],[0,1])
    ax.set_xlabel("committed predictor pi_u (projection of the realised push on the band subspace)")
    buf=io.BytesIO(); fig.savefig(buf, format="png", dpi=110, bbox_inches="tight"); print("tight:", dims(buf.getvalue()))
    buf=io.BytesIO(); fig.savefig(buf, format="png", dpi=110); print("no tight:", dims(buf.getvalue()))
    print("label extent px@fig.dpi:", ax.xaxis.label.get_window_extent(fig.canvas.get_renderer()), "fig dpi", fig.dpi)
EOF
python3 - <<'EOF'
import struct
b=open("/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_tmp_png/cell23_7.png","rb").read()
print("notebook F5 png dims:", struct.unpack(">II", b[16:24]))
EOF
```

### [144] TOOL RESULT — Bash · 2026-10-26 14:02:01 UTC

```
{"stdout": "3.10.0 agg\ntight: (480, 371)\nno tight: (550, 396)\nlabel extent px@fig.dpi: Bbox(x0=3.625, y0=-0.2455555555555584, x1=508.875, y1=12.754444444444442) fig dpi 100.0\nnotebook F5 png dims: (500, 392)", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [145] THINKING · 2026-10-26 14:02:19 UTC

```
Matplotlib 3.10.0's tight bounding box cuts off an x-label wider than its axes, unlike 3.11.2 which keeps it. I'll check if passing the axis labels as `bbox_extra_artists` fixes this.
```

### [146] TOOL CALL — Bash · 2026-10-26 14:02:19 UTC

```
Test bbox_extra_artists fix for clipped label:
/tmp/aii_nb_test_envs/art_e-_q5mSJGrSb-df3879c8a834/bin/python - <<'EOF'
import io, struct
import matplotlib.pyplot as plt
plt.rcParams.update({"font.size": 9})
dims=lambda b: struct.unpack(">II", b[16:24])
fig, ax = plt.subplots(figsize=(5, 3.6))
ax.scatter([0,1],[0,1])
ax.set_xlabel("committed predictor pi_u (projection of the realised push on the band subspace)")
extra=[a.xaxis.label for a in fig.axes]+[a.yaxis.label for a in fig.axes]
buf=io.BytesIO(); fig.savefig(buf, format="png", dpi=110, bbox_inches="tight", bbox_extra_artists=extra); print("tight+extra:", dims(buf.getvalue()))
r=fig.canvas.get_renderer()
print("ax tightbbox", ax.get_tightbbox(r), "fig tightbbox", fig.get_tightbbox(r))
EOF
```

### [147] TOOL RESULT — Bash · 2026-10-26 14:02:19 UTC

```
{"stdout": "tight+extra: (577, 371)\nax tightbbox Bbox(x0=32.77777777777778, y0=-1.6777777777777825, x1=450.0, y1=316.80000000000007) fig tightbbox TransformedBbox(\n    Bbox(x0=32.77777777777778, y0=-1.6777777777777825, x1=450.0, y1=316.80000000000007),\n    Affine2D().scale(0.01))", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [148] ASSISTANT · 2026-10-26 14:02:37 UTC

```
Listing the axis labels as extra artists restores the full width (577 px). I'll put that into `save()` and run scaling round 2: N_PAIRS=50, N_BOOT=1000, N_BOOT_CLASS=250, all three seeds.
```

### [149] TOOL CALL — Edit · 2026-10-26 14:02:37 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py
OLD:     # original: fig.savefig(FIGS / f"{name}.pdf", bbox_inches="tight"); fig.savefig(FIGS / f"{name}.png", dpi=180,
    # bbox_inches="tight"); plt.close(fig) -- here the PNG goes to memory (lower dpi) and is displayed
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
NEW:     # original: fig.savefig(FIGS / f"{name}.pdf", bbox_inches="tight"); fig.savefig(FIGS / f"{name}.png", dpi=180,
    # bbox_inches="tight"); plt.close(fig) -- here the PNG goes to memory (lower dpi) and is displayed. The axis
    # labels are listed because matplotlib 3.10 (Colab) trims labels wider than their axes from the tight box.
    labels = [a.xaxis.label for a in fig.axes] + [a.yaxis.label for a in fig.axes]
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight", bbox_extra_artists=labels)
```

### [150] TOOL RESULT — Edit · 2026-10-26 14:02:37 UTC

```
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py", "oldString": "    # original: fig.savefig(FIGS / f\"{name}.pdf\", bbox_inches=\"tight\"); fig.savefig(FIGS / f\"{name}.png\", dpi=180,\n    # bbox_inches=\"tight\"); plt.close(fig) -- here the PNG goes to memory (lower dpi) and is displayed\n    buf = io.BytesIO()\n    fig.savefig(buf, format=\"png\", dpi=110, bbox_inches=\"tight\")", "newString": "    # original: fig.savefig(FIGS / f\"{name}.pdf\", bbox_inches=\"tight\"); fig.savefig(FIGS / f\"{name}.png\", dpi=180,\n    # bbox_inches=\"tight\"); plt.close(fig) -- here the PNG goes to memory (lower dpi) and is displayed. The axis\n    # labels are listed because matplotlib 3.10 (Colab) trims labels wider than their axes from the tight box.\n    labels = [a.xaxis.label for a in fig.axes] + [a.yaxis.label for a in fig.axes]\n    buf = io.BytesIO()\n    fig.savefig(buf, format=\"png\", dpi=110, bbox_inches=\"tight\", bbox_extra_artists=labels)", "originalFile": null, "structuredPatch": [{"oldStart": 958, "oldLines": 9, "newStart": 958, "newLines": 11, "lines": [" ", " def save(fig: Any, name: str) -> None:", "     # original: fig.savefig(FIGS / f\"{name}.pdf\", bbox_inches=\"tight\"); fig.savefig(FIGS / f\"{name}.png\", dpi=180,", "-    # bbox_inches=\"tight\"); plt.close(fig) -- here the PNG goes to memory (lower dpi) and is displayed", "+    # bbox_inches=\"tight\"); plt.close(fig) -- here the PNG goes to memory (lower dpi) and is displayed. The axis", "+    # labels are listed because matplotlib 3.10 (Colab) trims labels wider than their axes from the tight box.", "+    labels = [a.xaxis.label for a in fig.axes] + [a.yaxis.label for a in fig.axes]", "     buf = io.BytesIO()", "-    fig.savefig(buf, format=\"png\", dpi=110, bbox_inches=\"tight\")", "+    fig.savefig(buf, format=\"png\", dpi=110, bbox_inches=\"tight\", bbox_extra_artists=labels)", "     plt.close(fig)", "     print(name)", "     display(Image(buf.getvalue()))"]}], "userModified": false, "replaceAll": false}
```

### [151] TOOL CALL — Bash · 2026-10-26 14:02:37 UTC

```
Scaling round 2: 50 pairs, 1000 boots, 3 seeds:
python3 _build_notebook.py --n_pairs 50 --n_boot 1000 --n_boot_class 250 --seeds "(0, 1, 2)" && ENV=/tmp/aii_nb_test_envs/art_e-_q5mSJGrSb-df3879c8a834 && t0=$(date +%s) && UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 $ENV && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python $ENV/bin/python jupyter ipykernel && t1=$(date +%s) && $ENV/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | grep -v "Kernel is running over TCP" | tail -20; t2=$(date +%s); echo "venv: $((t1-t0)) s; nbconvert execute: $((t2-t1)) s" && python3 - <<'EOF'
import json
from datetime import datetime
nb=json.load(open("code_demo.ipynb"))
t=lambda s: datetime.fromisoformat(s.replace("Z","+00:00"))
tot=0
for i,c in enumerate(nb["cells"]):
    if c["cell_type"]!="code": continue
    ex=c["metadata"].get("execution",{}); dt=(t(ex["shell.execute_reply"])-t(ex["iopub.execute_input"])).total_seconds(); tot+=dt
    errs=[o for o in c["outputs"] if o["output_type"]=="error"]
    print(f"cell {i}: {dt:.2f} s" + (f"  ERROR {errs[0]['ename']}: {errs[0]['evalue']}" if errs else ""))
print("sum of cell times:", round(tot,1), "s")
src="".join(nb["cells"][13]["outputs"][1]["text"]) if len(nb["cells"][13]["outputs"])>1 else ""
for o in nb["cells"][13]["outputs"]:
    if o["output_type"]=="stream": print("".join(o["text"]))
EOF
```

### [152] TOOL RESULT — Bash · 2026-10-26 14:03:41 UTC

```
{"stdout": "code_demo.ipynb: 27 cells\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[NbConvertApp] Writing 582383 bytes to code_demo.ipynb\nvenv: 0 s; nbconvert execute: 64 s\ncell 1: 7.17 s\ncell 2: 0.74 s\ncell 3: 0.00 s\ncell 4: 0.31 s\ncell 6: 0.00 s\ncell 8: 0.04 s\ncell 11: 0.01 s\ncell 13: 0.21 s\ncell 15: 0.01 s\ncell 17: 0.01 s\ncell 19: 0.01 s\ncell 21: 0.01 s\ncell 23: 0.64 s\ncell 25: 0.31 s\nsum of cell times: 9.5 s\n14:03:39|INFO   |T10: k* = 4; recovery 7.580 CI [4.267259630055121, 11.643945657130713]\n\n\nT10 decision site, block L* = 22: 50 held-out pairs replayed (46 with |Delta_full| >= 1 nat enter the recovery), N_BOOT = 1000\nrank |  replay, seed 0 [95% CI] |  published, 552 pairs [95% CI] | random subspaces (c1) median\n   1 |   6.90 [3.62, 11.07] |         7.67 [5.11, 10.71] | -0.009\n   2 |   7.31 [4.00, 11.40] |         8.12 [5.60, 11.02] | -0.006\n   4 |   7.58 [4.27, 11.64] |         8.43 [5.94, 11.30] | -0.005\n   8 |   8.33 [4.96, 12.35] |         9.26 [6.83, 12.03] | 0.001\nseed 1: k1 7.17 (published 7.98), k2 7.22 (published 8.06), k4 7.71 (published 8.58), k8 8.63 (published 9.60)\nseed 2: k1 6.82 (published 7.61), k2 6.99 (published 7.79), k4 7.04 (published 7.84), k8 7.90 (published 8.75)\n\nby source class at k* = 4 (seed 0):\n  bfs        n =  23: recovery 14.13 (mean Delta DAS 22.5 vs full 1.59 nats); published 15.38 on 268 pairs\n  dfs        n =  20: recovery 5.34 (mean Delta DAS 12.7 vs full 2.39 nats); published 5.47 on 264 pairs\n  union_find n =   3: recovery -0.13 (mean Delta DAS -0.7 vs full 5.75 nats); published -0.07 on 20 pairs\n\nk* = 4 (published 4); mean Delta: DAS 16.7 vs full-state 2.21 nats; OFF-MANIFOLD flag (recovery > 1.5): True (published True)", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [153] THINKING · 2026-10-26 14:04:01 UTC

```
Round 2 confirms the result: k* = 4, recovery 7.58, OFF-MANIFOLD True, completing in 64s wall clock (9.5s cell time). Since runtime is fast, I'll run round 3 with full rigor—original bootstrap values (N_BOOT=2000, N_BOOT_CLASS=500), all three seeds, and all 100 pairs.
```

### [154] TOOL CALL — Bash · 2026-10-26 14:04:01 UTC

```
Scaling round 3: 100 pairs, original bootstrap values:
python3 _build_notebook.py --n_pairs 100 --n_boot 2000 --n_boot_class 500 --seeds "(0, 1, 2)" && ENV=/tmp/aii_nb_test_envs/art_e-_q5mSJGrSb-df3879c8a834 && t0=$(date +%s) && UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 $ENV && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python $ENV/bin/python jupyter ipykernel && t1=$(date +%s) && $ENV/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | grep -v "Kernel is running over TCP" | tail -20; t2=$(date +%s); echo "venv: $((t1-t0)) s; nbconvert execute: $((t2-t1)) s" && python3 - <<'EOF'
import json
from datetime import datetime
nb=json.load(open("code_demo.ipynb"))
t=lambda s: datetime.fromisoformat(s.replace("Z","+00:00"))
tot=0
for i,c in enumerate(nb["cells"]):
    if c["cell_type"]!="code": continue
    ex=c["metadata"].get("execution",{}); dt=(t(ex["shell.execute_reply"])-t(ex["iopub.execute_input"])).total_seconds(); tot+=dt
    errs=[o for o in c["outputs"] if o["output_type"]=="error"]
    print(f"cell {i}: {dt:.2f} s" + (f"  ERROR {errs[0]['ename']}: {errs[0]['evalue']}" if errs else ""))
print("sum of cell times:", round(tot,1), "s")
for k in (6, 11, 13, 15, 17, 25):
    print(f"------ cell {k} outputs")
    for o in nb["cells"][k]["outputs"]:
        if o["output_type"]=="stream": print("".join(o["text"])[:3000])
        elif "text/markdown" in o.get("data",{}): print("".join(o["data"]["text/markdown"])[:3000])
EOF
```

### [155] TOOL RESULT — Bash · 2026-10-26 14:04:47 UTC

```
{"stdout": "code_demo.ipynb: 27 cells\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[NbConvertApp] Writing 587422 bytes to code_demo.ipynb\nvenv: 1 s; nbconvert execute: 46 s\ncell 1: 7.14 s\ncell 2: 0.73 s\ncell 3: 0.01 s\ncell 4: 0.30 s\ncell 6: 0.00 s\ncell 8: 0.04 s\ncell 11: 0.01 s\ncell 13: 0.41 s\ncell 15: 0.01 s\ncell 17: 0.01 s\ncell 19: 0.01 s\ncell 21: 0.01 s\ncell 23: 0.69 s\ncell 25: 0.30 s\nsum of cell times: 9.7 s\n------ cell 6 outputs\n------ cell 11 outputs\nT10_dec_teacher_forced: 100 held-out pairs -> 1200 rows (pair x fit seed x rank)\n\nSOURCE T10|forced|k4|j0|bfs: Write an implementation based on breadth-first search (BFS).\nBASE   T10|twin|W5|baby: Write a correct solution that does not use baby. . . . (padded with ' .' tokens)\nshared task text: Task: write a Python function solve(n, edges) that returns the number of connected components of an undirected graph. The nodes are the integers 0 to  ...\nclass at the decision token: source -> bfs, base -> union_find\nDelta of the full-state exchange: 2.12 nats\nDelta of the DAS edit (seed 0): rank 1: 22.43, rank 2: 22.24, rank 4: 22.49, rank 8: 22.62\n\n------ cell 13 outputs\n14:04:44|INFO   |T10: k* = 4; recovery 7.760 CI [4.800405911220429, 11.220153534658209]\n\n\nT10 decision site, block L* = 22: 100 held-out pairs replayed (92 with |Delta_full| >= 1 nat enter the recovery), N_BOOT = 2000\nrank |  replay, seed 0 [95% CI] |  published, 552 pairs [95% CI] | random subspaces (c1) median\n   1 |   7.06 [4.14, 10.63] |         7.67 [5.11, 10.71] | -0.009\n   2 |   7.48 [4.56, 10.98] |         8.12 [5.60, 11.02] | -0.006\n   4 |   7.76 [4.80, 11.22] |         8.43 [5.94, 11.30] | -0.005\n   8 |   8.51 [5.47, 11.92] |         9.26 [6.83, 12.03] | 0.001\nseed 1: k1 7.34 (published 7.98), k2 7.41 (published 8.06), k4 7.90 (published 8.58), k8 8.81 (published 9.60)\nseed 2: k1 7.00 (published 7.61), k2 7.18 (published 7.79), k4 7.24 (published 7.84), k8 8.11 (published 8.75)\n\nby source class at k* = 4 (seed 0):\n  bfs        n =  45: recovery 14.89 (mean Delta DAS 22.8 vs full 1.53 nats); published 15.38 on 268 pairs\n  dfs        n =  41: recovery 5.49 (mean Delta DAS 12.8 vs full 2.33 nats); published 5.47 on 264 pairs\n  union_find n =   6: recovery -0.09 (mean Delta DAS -0.5 vs full 5.83 nats); published -0.07 on 20 pairs\n\nk* = 4 (published 4); mean Delta: DAS 16.8 vs full-state 2.17 nats; OFF-MANIFOLD flag (recovery > 1.5): True (published True)\n\n------ cell 15 outputs\n| unit-site | verdict (recomputed here) | V0 parts (TF / gen / pass ratio / McNemar) | failed controls | published verdict |\n|---|---|---|---|---|\n| T10-dec | NO HANDLE | yes / yes / no / yes | c2, c3, c4, c5 | NO HANDLE |\n| T10-band | SUFFICIENT HANDLE | yes / yes / yes / yes | c2, c5, c7 | SUFFICIENT HANDLE |\n| GRID-dec | SUFFICIENT HANDLE | yes / yes / yes / yes | c2, c3, c5, c6 | SUFFICIENT HANDLE |\n| T10-dec_L24_posthoc | POST HOC, TF-only (no generation): controls failed ['c2', 'c3'], untested [] | yes / no / no / no | c2, c3 | POST HOC, TF-only (no generation): controls failed ['c2', 'c3'], untested [] |\n| T10-dec, replayed TF (100 pairs) | NO HANDLE | yes / yes / no / yes | c2, c3, c4, c5 | (not published) |\n------ cell 17 outputs\n14:04:44|INFO   |{\"T10-dec\": \"NO HANDLE\", \"T10-band\": \"SUFFICIENT HANDLE\", \"GRID-dec\": \"SUFFICIENT HANDLE\", \"T10-dec_L24_posthoc\": \"POST HOC, TF-only (no generation): controls failed ['c2', 'c3'], untested []\"}\n\n14:04:44|INFO   |K2: DISCONFIRMED p_K2 0.03698150924537731\n\npublished: K2 DISCONFIRMED, p_K2 0.03698150924537731\n\n| decision site | c2 label-control ratios (pass <= 0.10) | c3 random-init ratio (pass <= 0.25) | p_c2 max | p_c3 |\n|---|---|---|---|---|\n| T10 (L* = 22, k* = 4) | pi1 0.87, pi2 0.63, prompt 0.77 | 0.69 (12.1 vs 17.5 nats) | 0.0370 | 0.0005 |\n| GRID (L* = 16, k* = 4) | shuffle0 0.11, shuffle1 0.11, shuffle2 0.20 | 0.41 (3.7 vs 9.1 nats) | 0.0005 | 0.0005 |\n------ cell 25 outputs\n| quantity | this notebook | published run |\n|---|---|---|\n| T10 decision-site TF recovery at k* [95% CI] | 7.76 [4.80, 11.22] on 92 pairs | 8.43 [5.94, 11.30] on 552 pairs |\n| k* | 4 | 4 |\n| mean Delta, DAS vs full state (nats) | 16.8 vs 2.17 | 17.4 vs 2.06 |\n| OFF-MANIFOLD flag | True | True |\n| verdict T10-dec | NO HANDLE (replayed TF), NO HANDLE (stored TF) | NO HANDLE |\n| verdicts T10-band / GRID-dec | SUFFICIENT HANDLE / SUFFICIENT HANDLE | SUFFICIENT HANDLE / SUFFICIENT HANDLE |\n| K2 (p_K2) | DISCONFIRMED (0.037) | DISCONFIRMED (0.037) |\n| T10 generation, target DFS: correct programs DAS / FULL / RAND / BASE (of 30) | stored | 29 / 2 / 0 / 0 |\n| T10 generation, target BFS: correct (attempted BFS) DAS / FULL / RAND / BASE | stored | 5 / 0 / 0 / 0 (29 DAS attempts) |\n| GRID generation, target BFS: DAS / FULL / RAND / BASE | stored | 22 / 10 / 5 / 6 |\n| novel ('other') algorithms among correct programs | stored | 0 of 1857 |", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [156] THINKING · 2026-10-26 14:05:05 UTC

```
Round 3 passed within time limits, and the 100-pair replay values are close to the published results. Now I'll verify the closing cell's claim that the replay exactly reproduces `dec_T10.json` on the full 600 pairs, since the stored Deltas are rounded to 4 decimals.
```

### [157] TOOL CALL — Bash · 2026-10-26 14:05:05 UTC

```
Check full-data replay against published recovery:
python3 - <<'EOF'
import json, re
import numpy as np
A="/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40"
d=json.load(open(A+"/full_method_out.json"))
ex={x["dataset"]:x["examples"] for x in d["datasets"]}["T10_dec_teacher_forced"]
pub=d["metadata"]["dec_T10"]
PAIR_RE=re.compile(r"source=(\S+) base=(\S+)")
def recovery(d_edit, d_full, src, base, n_boot=2000, seed=0, min_full=1.0):
    d_edit=np.asarray(d_edit,float); d_full=np.asarray(d_full,float); ok=np.abs(d_full)>=min_full
    de,df=d_edit[ok],d_full[ok]; s=np.array(src)[ok]; b=np.array(base)[ok]
    us,ub=np.unique(s),np.unique(b); si=np.searchsorted(us,s); bi=np.searchsorted(ub,b)
    point=float(de.mean()/df.mean()); rng=np.random.default_rng(seed); boots=[]
    for _ in range(n_boot):
        cs=np.bincount(rng.integers(0,len(us),len(us)),minlength=len(us)); cb=np.bincount(rng.integers(0,len(ub),len(ub)),minlength=len(ub))
        w=cs[si]*cb[bi]
        if w.sum()==0 or (w*df).sum()==0: continue
        boots.append(float((w*de).sum()/(w*df).sum()))
    return point, (float(np.percentile(boots,2.5)), float(np.percentile(boots,97.5)))
src=[PAIR_RE.search(e["input"]).group(1) for e in ex]; base=[PAIR_RE.search(e["input"]).group(2) for e in ex]
full=[e["metadata_delta_full"] for e in ex]
for k in (1,2,4,8):
    de=[float(e[f"predict_seed0_k{k}"]) for e in ex]
    p,ci=recovery(de,full,src,base)
    pb=pub["recovery_by_rank"][str(k)]
    print(k, round(p,4), [round(x,2) for x in ci], "| published", round(pb["recovery"],4), [round(x,2) for x in pb["ci95"]])
EOF
```

### [158] TOOL RESULT — Bash · 2026-10-26 14:05:05 UTC

```
{"stdout": "1 7.6698 [5.11, 10.71] | published 7.6698 [5.11, 10.71]\n2 8.123 [5.6, 11.02] | published 8.123 [5.6, 11.02]\n4 8.4329 [5.94, 11.3] | published 8.4329 [5.94, 11.3]\n8 9.2633 [6.83, 12.03] | published 9.2633 [6.83, 12.03]", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [159] THINKING · 2026-10-26 14:05:17 UTC

```
All 600 pairs replay match the published table to 4 decimals, same CIs — I'll soften the claim to "about four decimals" since the stored Deltas are rounded, then do a final check on the full-scale figures.
```

### [160] TOOL CALL — Edit · 2026-10-26 14:05:17 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py
OLD: `T10_dec_teacher_forced` dataset has the same format. The replay then reproduces `results/dec_T10.json` exactly:
recovery 7.67 / 8.12 / 8.43 / 9.26 at ranks 1 / 2 / 4 / 8.
NEW: `T10_dec_teacher_forced` dataset has the same format. The replay then reproduces `results/dec_T10.json`: recovery
7.67 / 8.12 / 8.43 / 9.26 at ranks 1 / 2 / 4 / 8, with the same CIs. The stored Deltas are rounded to 4 decimals, so
the agreement is to about four decimals.
```

### [161] TOOL RESULT — Edit · 2026-10-26 14:05:17 UTC

```
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py", "oldString": "`T10_dec_teacher_forced` dataset has the same format. The replay then reproduces `results/dec_T10.json` exactly:\nrecovery 7.67 / 8.12 / 8.43 / 9.26 at ranks 1 / 2 / 4 / 8.", "newString": "`T10_dec_teacher_forced` dataset has the same format. The replay then reproduces `results/dec_T10.json`: recovery\n7.67 / 8.12 / 8.43 / 9.26 at ranks 1 / 2 / 4 / 8, with the same CIs. The stored Deltas are rounded to 4 decimals, so\nthe agreement is to about four decimals.", "originalFile": null, "structuredPatch": [{"oldStart": 1207, "oldLines": 8, "newStart": 1207, "newLines": 9, "lines": [" ", " **Larger replay.** Set `N_PAIRS = 100`, `N_BOOT = 2000`, `N_BOOT_CLASS = 500` and `DEMO_SEEDS = (0, 1, 2)` (the", " original values). For the run's full 600 held-out pairs, point `data` at the artifact's `full_method_out.json`, whose", "-`T10_dec_teacher_forced` dataset has the same format. The replay then reproduces `results/dec_T10.json` exactly:", "-recovery 7.67 / 8.12 / 8.43 / 9.26 at ranks 1 / 2 / 4 / 8.", "+`T10_dec_teacher_forced` dataset has the same format. The replay then reproduces `results/dec_T10.json`: recovery", "+7.67 / 8.12 / 8.43 / 9.26 at ranks 1 / 2 / 4 / 8, with the same CIs. The stored Deltas are rounded to 4 decimals, so", "+the agreement is to about four decimals.", " ", " **The GPU stages.** Inside the artifact folder:", " "]}], "userModified": false, "replaceAll": false}
```

### [162] TOOL CALL — Bash · 2026-10-26 14:05:17 UTC

```
Extract full-scale figures for final review:
rm -f _tmp_png/*.png && python3 - <<'EOF'
import json, base64
nb=json.load(open("code_demo.ipynb"))
for i,c in enumerate(nb["cells"]):
    if c["cell_type"]!="code": continue
    for j,o in enumerate(c["outputs"]):
        if o["output_type"] in ("display_data","execute_result") and "image/png" in o["data"]:
            p=f"_tmp_png/cell{i:02d}_{j}.png"; open(p,"wb").write(base64.b64decode(o["data"]["image/png"])); print(p)
EOF
```

### [163] TOOL RESULT — Bash · 2026-10-26 14:05:17 UTC

```
{"stdout": "_tmp_png/cell23_1.png\n_tmp_png/cell23_3.png\n_tmp_png/cell23_5.png\n_tmp_png/cell23_7.png\n_tmp_png/cell25_0.png", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [164] TOOL CALL — Read · 2026-10-26 14:05:21 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_tmp_png/cell25_0.png
```

### [165] TOOL RESULT — Read · 2026-10-26 14:05:21 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [166] TOOL CALL — Read · 2026-10-26 14:05:21 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_tmp_png/cell23_7.png
```

### [167] TOOL RESULT — Read · 2026-10-26 14:05:21 UTC

```
{"type": "image", "file": {"base64": "iVBORw0KGgoAAAANSUhEUgAAAkEAAAGICAYAAABGCzRMAAAAOnRFWHRTb2Z0d2FyZQBNYXRwbG90bGliIHZlcnNpb24zLjEwLjAsIGh0dHBzOi8vbWF0cGxvdGxpYi5vcmcvlHJYcgAAAAlwSFlzAAAQ6wAAEOsBUJTofAAAd2NJREFUeJzt3Xtcjvf/B/DX3eHuHBFKpZBRqIgUhhHm0JhtX7OZMGMzx7KDObNpc4gN3zHmtM2GYcYMORtJzqfSSUoK0VRSqT6/P/p2/bo7l+7rVvfr+Xj0eNTnOnze13Xdh3ef63N9PgohhAARERGRltHRdABEREREmsAkiIiIiLQSkyAiIiLSSkyCiIiISCsxCSIiIiKtxCSIiIiItBKTICIiItJKTIKIiIhIKzEJIiIiIq3EJIiIiIi0EpMgogpYuXIlHBwcpL9Hjhy... [truncated, 41156 chars total]
```

### [168] THINKING · 2026-10-26 14:05:57 UTC

```
Both figures now look correct, with panel (a) clearly showing BFS sources at 21-27 nats, DFS at 11-14, and union-find near 0 (full-state Delta 5-7 nats). Next I'll expand the Section 10 text to cover the bans and Gemma's top-5 prohibition prompt, then rebuild with the final values from the definitive test run.
```

### [169] TOOL CALL — Edit · 2026-10-26 14:05:57 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py
OLD:   group centroids of that embedding. Stars are the forced-algorithm classes, sized by how many test-passing programs
  of that class the unedited and source prompts produced. The neutral twins, the seed strings ("seed=d32qxk4nt43",
  "seed=(horse chair roof love)") and the novelty instructions ("Make a new algorithm.", plus a 2,000-word novelty
  brief) all sit together, away from every forced cluster: in this subspace, prompt-level "creativity" pushes do not
  move toward another algorithm.
NEW:   group centroids of that embedding. Stars are the forced-algorithm classes, sized by how many test-passing programs
  of that class the unedited and source prompts produced.
  - In T10, three groups all sit together, away from every forced cluster: the neutral twins, the seed strings
    ("seed=d32qxk4nt43", "seed=(horse chair roof love)") and the novelty instructions ("Make a new algorithm.",
    plus a 2,000-word novelty brief). The five union-find bans ("ban") sit just outside them, toward the forced
    clusters.
  - In GRID, the prompt that prohibits the five most common algorithms ("top5") stays inside the twin cluster, on
    neither class's side.

  In this subspace, prompt-level "creativity" pushes do not move the model toward another algorithm.
```

### [170] TOOL RESULT — Edit · 2026-10-26 14:05:57 UTC

```
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py", "oldString": "  group centroids of that embedding. Stars are the forced-algorithm classes, sized by how many test-passing programs\n  of that class the unedited and source prompts produced. The neutral twins, the seed strings (\"seed=d32qxk4nt43\",\n  \"seed=(horse chair roof love)\") and the novelty instructions (\"Make a new algorithm.\", plus a 2,000-word novelty\n  brief) all sit together, away from every forced cluster: in this subspace, prompt-level \"creativity\" pushes do not\n  move toward another algorithm.", "newString": "  group centroids of that embedding. Stars are the forced-algorithm classes, sized by how many test-passing programs\n  of that class the unedited and source prompts produced.\n  - In T10, three groups all sit together, away from every forced cluster: the neutral twins, the seed strings\n    (\"seed=d32qxk4nt43\", \"seed=(horse chair roof love)\") and the novelty instructions (\"Make a new algorithm.\",\n    plus a 2,000-word novelty brief). The five union-find bans (\"ban\") sit just outside them, toward the forced\n    clusters.\n  - In GRID, the prompt that prohibits the five most common algorithms (\"top5\") stays inside the twin cluster, on\n    neither class's side.\n\n  In this subspace, prompt-level \"creativity\" pushes do not move the model toward another algorithm.", "originalFile": null, "structuredPatch": [{"oldStart": 1088, "oldLines": 10, "newStart": 1088, "newLines": 15, "lines": [" - **(c, d)** Where the prompt groups sit in the fitted handle subspace (stored `results/geometry.json`). Every", "   prompt's R_8 coordinates at (L\\*, d), centred on the neutral twins, were embedded by metric MDS. The points are the", "   group centroids of that embedding. Stars are the forced-algorithm classes, sized by how many test-passing programs", "-  of that class the unedited and source prompts produced. The neutral twins, the seed strings (\"seed=d32qxk4nt43\",", "-  \"seed=(horse chair roof love)\") and the novelty instructions (\"Make a new algorithm.\", plus a 2,000-word novelty", "-  brief) all sit together, away from every forced cluster: in this subspace, prompt-level \"creativity\" pushes do not", "-  move toward another algorithm.", "+  of that class the unedited and source prompts produced.", "+  - In T10, three groups all sit together, away from every forced cluster: the neutral twins, the seed strings", "+    (\"seed=d32qxk4nt43\", \"seed=(horse chair roof love)\") and the novelty instructions (\"Make a new algorithm.\",", "+    plus a 2,000-word novelty brief). The five union-find bans (\"ban\") sit just outside them, toward the forced", "+    clusters.", "+  - In GRID, the prompt that prohibits the five most common algorithms (\"top5\") stays inside the twin cluster, on", "+    neither class's side.", "+", "+  In this subspace, prompt-level \"creativity\" pushes do not move the model toward another algorithm.", " ''')", " ", " code(r'''"]}], "userModified": false, "replaceAll": false}
```

### [171] TOOL CALL — Bash · 2026-10-26 14:05:57 UTC

```
Final build with original values and full test run:
python3 _build_notebook.py --n_pairs 100 --n_boot 2000 --n_boot_class 500 --seeds "(0, 1, 2)" && ENV=/tmp/aii_nb_test_envs/art_e-_q5mSJGrSb-df3879c8a834 && t0=$(date +%s) && UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 $ENV && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python $ENV/bin/python jupyter ipykernel && t1=$(date +%s) && $ENV/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | grep -v "Kernel is running over TCP" | tail -20; t2=$(date +%s); echo "venv: $((t1-t0)) s; nbconvert execute: $((t2-t1)) s" && python3 - <<'EOF'
import json
nb=json.load(open("code_demo.ipynb"))
n_err=sum(1 for c in nb["cells"] if c["cell_type"]=="code" for o in c["outputs"] if o["output_type"]=="error")
stderr=[(i,"".join(o["text"])[:300]) for i,c in enumerate(nb["cells"]) if c["cell_type"]=="code" for o in c["outputs"] if o["output_type"]=="stream" and o["name"]=="stderr"]
unexec=[i for i,c in enumerate(nb["cells"]) if c["cell_type"]=="code" and c.get("execution_count") is None]
print("errors:", n_err, "| stderr outputs:", stderr, "| unexecuted code cells:", unexec)
print("install cell outputs:", nb["cells"][1]["outputs"])
print("config:", "".join(nb["cells"][6]["source"]).split("\n")[1:5])
EOF
```

### [172] TOOL RESULT — Bash · 2026-10-26 14:06:45 UTC

```
{"stdout": "code_demo.ipynb: 27 cells\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[NbConvertApp] Writing 587849 bytes to code_demo.ipynb\nvenv: 0 s; nbconvert execute: 47 s\nerrors: 0 | stderr outputs: [] | unexecuted code cells: []\ninstall cell outputs: []\nconfig: ['N_PAIRS = 100         # held-out teacher-forced pairs replayed (max 100 in mini_demo_data.json; the run: 600, full_method_out.json)', 'N_BOOT = 2000         # two-way cluster-bootstrap resamples per recovery CI (original: N_BOOT = 2000, src/cfg8.py)', 'N_BOOT_CLASS = 500    # resamples for the per-class recovery (original: n_boot=500 in src/run_dec.py:by_class)', 'DEMO_SEEDS = (0, 1, 2) # fit seeds whose stored Deltas are replayed; must contain 0 (original: FIT_SEEDS = (0, 1, 2))']", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [173] THINKING · 2026-10-26 14:06:57 UTC

```
The final run passed in 47s with no errors—everything executed cleanly including the install cell. I noticed the Section 1 text about knobs "starting small" is now outdated since the config reverted to original bootstrap values, so before the final rebuild I'll print all markdown cells to proofread them together.
```

### [174] TOOL CALL — Bash · 2026-10-26 14:06:57 UTC

```
Print all markdown cells for proofreading:
python3 - <<'EOF'
import json
nb=json.load(open("code_demo.ipynb"))
for i,c in enumerate(nb["cells"]):
    if c["cell_type"]=="markdown":
        print(f"=========== [{i}] markdown"); print("".join(c["source"]))
    else:
        src="".join(c["source"]); print(f"----------- [{i}] code: {len(src.splitlines())} lines; first: {src.splitlines()[0][:100]}")
EOF
```

### [175] TOOL RESULT — Bash · 2026-10-26 14:06:57 UTC

````
{"stdout": "=========== [0] markdown\n# Searching for a hidden algorithm switch in code models: a DAS demo (iteration 8)\n\n**Question (claim K2).** When a code model picks an algorithm (BFS, DFS or union-find to count the connected\ncomponents of a graph; BFS or DFS for a shortest grid path), is there a **low-rank causal variable** for that choice\ninside the model, i.e. a linear subspace that *is* the decision? Or is there only a **steering handle**, a direction that\nchanges what the model writes without being the model's own variable?\n\n**Method.** One distributed-alignment-search (DAS) protocol, hash-committed before any GPU use, applied at three sites:\n\n| site | model | where the edit is made | classes |\n|---|---|---|---|\n| T10 decision token | Qwen3-8B | block output at the last prefilled token ` def` (response token 11, after `def solve(n, edges):` + indent) | BFS / DFS / union-find |\n| T10 task band | Qwen3-8B | blocks 12-23 at every task-spec position, one shared map | same |\n| GRID decision token | gemma-3-4b-it | response index 32 of the grid-path answer | BFS / DFS |\n\n- **map:** a linear orthonormal `R` (d_model x 8, nested ranks 1/2/4/8); **interchange** `h <- h + R(R^T h_src - R^T h_base)`;\n- **objective:** KL from the source prompt's own class distribution to the edited base's (bounded, CDAS-style);\n- **readout:** the class margin `log P(class_src) - log P(class_base)` at the decision position;\n  **Delta** = margin after the edit - margin before;\n- **recovery** = mean Delta of the DAS edit / mean Delta of exchanging the *whole* state, over held-out pairs\n  (1 = the subspace does what the full state does; above 1.5 the run raises an **OFF-MANIFOLD** flag);\n- **seven committed controls** c1-c7 (random subspaces, label controls, a randomly initialised network, reverse\n  interchange, natural-variance retention, variance share, seed stability) and **generation** scored by hidden tests.\n\n**Result: K2 is DISCONFIRMED (p_K2 = 0.037).** DAS finds a strong rank-4 *steering handle*. For example, it makes\nQwen3-8B write a correct DFS program on 29 of 30 slots where it otherwise writes union-find. But no site passes the\nspecificity controls. Maps fitted to *wrong labels* (c2) or on a *randomly initialised* network (c3) still reach 41-87%\nof the effect. At the T10 decision site, the DAS edit moves the margin about 8 times more than exchanging the whole\nstate does, which marks the handle as off-manifold. In plain words: you can push the model into writing a different\nalgorithm, but the push does not reveal a hidden \"algorithm switch\".\n\n**What this notebook runs.** `method.py` chains about 20 stage scripts. The GPU stages (about 3.2 GPU-hours with the\n8B and 4B models) cannot run in a 10-minute CPU session, so the notebook replays the artifact's own\n`method.py --cpu-only` path on the saved rows:\n\n1. the **held-out recovery table** of the T10 decision site (the tail of stage S6 in `src/run_dec.py`), replayed\n   from the stored per-pair Deltas of 100 of the 600 held-out pairs;\n2. the committed **verdict rule** and **K2** (`src/analysis8.py`);\n3. the **result tables** (`src/digest8.py`), the stdlib **audit** (`audit/rederive.py`) and the **figures**\n   (`src/figures8.py`);\n4. a final visualisation of the actual per-pair Deltas and of where the prompts sit in the fitted handle subspace.\n\nThe data come from `mini_demo_data.json`: the `T10_dec_teacher_forced` dataset (100 curated pairs) plus the per-stage\nresult JSONs. It is loaded from GitHub, with a local fallback. After the install cell, the whole notebook runs in\nseconds.\n----------- [1] code: 9 lines; first: import subprocess, sys\n----------- [2] code: 29 lines; first: from __future__ import annotations\n----------- [3] code: 16 lines; first: GITHUB_DATA_URL = \"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-b\n----------- [4] code: 5 lines; first: data = load_data()\n=========== [5] markdown\n## 1. Configuration\n\nThe **demo knobs** at the top set how much of the stored data is replayed and how many bootstrap resamples are\ndrawn. They start small; the original values are given in the comments. The **protocol constants** below them are\ncopied from `src/cfg8.py`. They were committed (hash-chained, `commitments.log`) before any GPU use, so they are not\ntuning knobs.\n----------- [6] code: 20 lines; first: # ---------------------------------------------------------------- demo knobs (originals in the comm\n=========== [7] markdown\n## 2. Statistics (`src/stats8.py`, verbatim)\n\nEvery number in the verdicts comes from these helpers:\n\n- `recovery()`: mean(Delta_edit) / mean(Delta_full) over pairs whose full-state Delta is at least 1 nat. Its 95% CI\n  comes from a **two-way cluster bootstrap**: source prompts and base prompts are resampled independently, so a pair\n  enters with multiplicity count_src x count_base.\n- `wilson()` intervals for generation shares; exact `mcnemar()` on paired (common-random-number) generation slots;\n  `cluster_wilcoxon_p()` for the one-sided control tests; `spearman_perm()` and `partial_spearman()` for the\n  mediation analysis.\n\nThe cell ends with the estimator check from `tests/test_cpu_tiny.py`: on synthetic Deltas with a true ratio of 0.6 it\nmust return 0.6.\n----------- [8] code: 138 lines; first: # ================================================================ src/stats8.py (verbatim)\n=========== [9] markdown\n## 3. The GPU stages: what produced the stored rows\n\n`method.py` runs the stages below in order; each stage is resumable. Everything except the last row needs Qwen3-8B\n(bf16) or gemma-3-4b-it on a GPU, about 3.2 GPU-hours on one NVIDIA L4. So this notebook loads their **outputs**:\n\n| `method.py` stage | script | in this notebook |\n|---|---|---|\n| S0 inputs, S1 prompts, commit #0 | `src/s0_inputs.py`, `src/prompts8.py`, `src/commit0.py` | prompt texts in `prompt_segments` |\n| S3-S6 decision site (T10, GRID) | `src/run_dec.py --unit T10` / `--unit GRID` | **per-pair Deltas replayed (Section 4)**; controls c1, c2, c4-c7 read from `dec_*` |\n| S9 generation (CRN slots, hidden tests) | `src/run_gen.py`, `src/label8.py` | generation tables `gen_*` |\n| S8 random-initialised network (c3) | `src/run_rinit.py` | `rinit_*` |\n| S7 task band | `src/run_band.py` | `band_T10` |\n| S10 mediation of random pushes | `src/run_med.py` | `mediation_T10` |\n| per-pair label-control test (p_c2) | `src/run_post.py` | `post_T10` |\n| post hoc: same protocol at block 24 | `src/run_dec.py --unit T10 --force_L 24` | `dec_T10_L24`, `rinit_T10_L24` |\n| S11-S12 analysis, tables, figures, audit (CPU) | `src/analysis8.py`, `src/digest8.py`, `src/figures8.py`, `audit/rederive.py` | **run here (Sections 4-9)** |\n\nFor reference, here is the core of one fit (`src/das8.py`, `DecSite.fit`). This is the step that needs the model:\n\n```python\nR = torch.linalg.qr(W)[0][:, :k]                     # W: free D x 8 matrix -> orthonormal map, nested rank k\nHn = Hb[:, None] + ((Hs - Hb[:, None]) @ R) @ R.T    # interchange at block L, decision position d:\n                                                     #   h_base + R (R^T h_src - R^T h_base)\nlg = self.forward(L, bsel, Hn)                       # blocks L+1..N-1 for position d against the base's cached K/V\nloss = kl(T, self.cmap.probs(lg)).mean()             # bounded KL(q_src || q_edit) over {bfs, dfs, union_find, other}\n```\n\nThe readout (`ClassMap.margin`) is `log P(c_src) - log P(c_base)`. Here `P(c)` sums the softmax mass of the class's\ndecision tokens at the decision position: the model's next token after the prefilled ` def` names the helper it is\nabout to write, for example ` bfs` for BFS or ` find` for union-find (token sets in `md[\"s3_T10\"]`).\n`DecSite.evaluate()` then reports, for every held-out (source, base) pair, **Delta = margin after the edit - margin\nbefore**. It does this for the full-state exchange (`R = None`) and for every fitted map, seed and rank, and those\nrows are the dataset in `mini_demo_data.json`.\n\nA held-out pair needs a **held-out prompt family** (forced templates k = 3, 4) **and** a **held-out base** (twin\ntemplates W4-W5 with held-out nouns, or the padded twins of held-out forced prompts). The source is a \"forced\"\nprompt that names an algorithm; the base is a neutral twin of the same length.\n=========== [10] markdown\n## 4. Replay of the T10 decision-site recovery (stage S6 of `src/run_dec.py`)\n\n### 4a. Unpack the held-out pairs\n\n`src/outputs8.py:tf_examples()` pivoted `data/tf_T10_dec.jsonl` (one row per pair x fit seed x rank) into one example\nper pair. This cell undoes that pivot, so the replay below reads the same rows `run_dec.py` wrote. It then shows one\npair in words.\n----------- [11] code: 28 lines; first: # undo src/outputs8.py:tf_examples(): example (one per pair) -> rows of data/tf_T10_dec.jsonl (pair \n=========== [12] markdown\n### 4b. Held-out recovery by rank, seed and class; k* and the OFF-MANIFOLD flag\n\nThis is the tail of `stage_dec()` in `src/run_dec.py`, verbatim. The only change is that `site` is a `StoredSite`:\nits `evaluate()` returns the Deltas the GPU run measured (from the rows above) instead of running blocks\nL+1..N-1 of Qwen3-8B. A fitted map's first k columns, `f[\"R\"][:, :k]`, become the tag `(fit, k)`.\n\n- **k\\*** is the smallest rank whose recovery reaches 90% of the best rank's.\n- The **OFF-MANIFOLD flag** is raised when the recovery at k\\* exceeds 1.5, i.e. when the subspace edit moves the\n  margin more than half again as far as exchanging the whole state does.\n\nThe published run used all 552 usable held-out pairs (600 pairs, of which 552 have |Delta_full| >= 1 nat). This replay\nuses `N_PAIRS` of them.\n----------- [13] code: 97 lines; first: class StoredSite:\n=========== [14] markdown\n## 5. Controls and verdict per site (`src/analysis8.py:verdict`, verbatim)\n\nThe controls need the model, so their results are read from the stored per-site JSONs (`dec_*`, `band_T10`,\n`rinit_*`). The committed rule is then applied to them unchanged.\n\n**V0, the site is a steering handle**, requires all four of:\n\n- teacher-forced recovery >= 0.5 with CI lower bound > 0.25;\n- generation recovery >= 0.5, where generation recovery = (DAS - BASE correct programs) / (FULL - BASE);\n- pass ratio DAS / BASE >= 0.8;\n- McNemar DAS > RAND with p < 0.05.\n\n**Controls** (thresholds committed in #0):\n\n| control | what it tests | pass |\n|---|---|---|\n| c1 | 50 random subspaces per rank | median recovery <= 0.05 |\n| c2 | refits on permuted labels | <= 0.10 of the true fit |\n| c3 | randomly initialised network, same map class and budget | <= 0.25 of trained |\n| c4 | reverse interchange | >= 0.5 of the full-state reverse |\n| c5 | retention after projecting R onto the top-64 natural principal components | >= 0.5 |\n| c6 | natural-variance share | above the random 95th percentile |\n| c7 | seed stability | median first principal cosine >= 0.5 |\n\n**Labels:** `NO HANDLE` if V0 fails; `CERTIFIED VARIABLE` if V0 holds and every control passes; `SUFFICIENT HANDLE` if\nV0 holds and c1 passes but some other control fails.\n\nThe cell applies the rule twice for T10-dec: once to the stored teacher-forced table, and once with this notebook's\nreplayed recovery from Section 4 substituted.\n----------- [15] code: 88 lines; first: # ================================================================ src/analysis8.py:verdict (verbati\n=========== [16] markdown\n## 6. K2 and p_K2 (`src/analysis8.py:main`)\n\n- **K2 is confirmed** iff both decision sites are `CERTIFIED VARIABLE`.\n- **K2 is disconfirmed** iff a decision site fails c2 (label control) or c3 (random-init network) in either family.\n- **p_K2** = max over the two sites of max(p_c2, p_c3). These are one-sided pair-level tests that the true (trained)\n  fit beats its control, with a two-way cluster bootstrap. A small p_K2 says the true fits beat their controls; it\n  does not say they beat them by the committed margin.\n----------- [17] code: 43 lines; first: # ================================================================ src/analysis8.py:main, K2 part (r\n=========== [18] markdown\n## 7. Result tables (`src/digest8.py`, verbatim)\n\n`digest8.py` writes `results/summary.md` straight from the result JSONs; no number is typed by hand. It produces, per\nsite, the teacher-forced recovery by rank and class plus every control, then the generation cells (correct\ntarget-class programs per arm), the verdicts and K2. The cell renders the same Markdown inline instead of writing the\nfile.\n\n**Generation arms** (one common-random-number stream per slot; *correct* = target-class label **and** hidden tests pass):\n\n| arm | what is generated |\n|---|---|\n| BASE | the unedited twin prompt |\n| FULL | the full-state exchange |\n| DAS | the rank-k* edit |\n| RAND | a random rank-k* subspace |\n| PERM | the label-control map |\n| REV-DAS / REV-FULL | the reverse edits |\n| SRC | the source prompt itself |\n----------- [19] code: 87 lines; first: # ================================================================ src/digest8.py (verbatim)\n=========== [20] markdown\n## 8. Independent re-derivation (`audit/rederive.py`, standard library only)\n\nThe audit shares no code with `src/`: it recomputes headline numbers with plain Python and runs placebos that must\nfail. In the published run all 38 checks match. Here it checks four things:\n\n- **TF recovery:** the replayed recovery at k\\*, from the same rows, with plain sums instead of numpy.\n- **Mediation:** the retrospective Spearman correlation between each random push's committed predictor `pi` and its\n  escape share. A **placebo** with a shuffled predictor must give |rho| < 0.3.\n- **K2:** the status, recomputed from the raw control flags.\n- **McNemar:** exact one-sided McNemar tests (DAS > RAND) from the discordant slot counts of the generation tables.\n----------- [21] code: 94 lines; first: # ================================================================ audit/rederive.py (stdlib; rows /\n=========== [22] markdown\n## 9. Figures (`src/figures8.py`)\n\nThese are the same functions as the artifact's figure stage. They read the stored results and show the figures\ninline instead of saving PDF and PNG files.\n\n- **F1 scan profile.** For every second block: rank-1 DAS cross-validated recovery (red) and the full-state Delta\n  (grey). L\\* is the committed argmax. At L\\* = 22 (Qwen) and 16 (Gemma) the full state carries little of the class\n  yet, so a rank-1 subspace \"recovers\" many times more than the full state.\n- **F2 recovery by rank** for all four sites, against the median and 95th percentile of 50 random subspaces (c1).\n- **F4 generation.** Share of correct target-class programs per arm, with Wilson 95% intervals.\n- **F5 mediation.** For iteration 4's 40 random pushes: the committed predictor `pi_u` (how much of the push lies in\n  the band subspace) against the share of programs that escape the default algorithm.\n\n**F3 (geometry) is not redrawn here.** It needs `cache/states_<unit>_dec_trained.pt`, the block outputs of all 290\n(T10) or 207 (GRID) prompts, which is regenerable on the GPU but not shipped. Section 10 plots the stored group\ncentroids of its embedding instead.\n----------- [23] code: 124 lines; first: # ================================================================ src/figures8.py (results/*.json -\n=========== [24] markdown\n## 10. Results: the actual Deltas and the activation geometry\n\n- **(a)** The per-pair evidence behind the OFF-MANIFOLD flag. Each point is one held-out (source, base) pair: x is\n  the Delta of exchanging the whole block-22 state at the decision token, and y is the Delta of the rank-k\\* DAS edit.\n  BFS and DFS sources sit far above the identity line: a 4-dimensional edit moves the margin much more than the whole\n  4096-dimensional state does. The union-find sources (whose base twins already pick DFS) sit near zero.\n- **(b)** Recovery by rank, replayed here and as published, against random subspaces (c1).\n- **(c, d)** Where the prompt groups sit in the fitted handle subspace (stored `results/geometry.json`). Every\n  prompt's R_8 coordinates at (L\\*, d), centred on the neutral twins, were embedded by metric MDS. The points are the\n  group centroids of that embedding. Stars are the forced-algorithm classes, sized by how many test-passing programs\n  of that class the unedited and source prompts produced.\n  - In T10, three groups all sit together, away from every forced cluster: the neutral twins, the seed strings\n    (\"seed=d32qxk4nt43\", \"seed=(horse chair roof love)\") and the novelty instructions (\"Make a new algorithm.\",\n    plus a 2,000-word novelty brief). The five union-find bans (\"ban\") sit just outside them, toward the forced\n    clusters.\n  - In GRID, the prompt that prohibits the five most common algorithms (\"top5\") stays inside the twin cluster, on\n    neither class's side.\n\n  In this subspace, prompt-level \"creativity\" pushes do not move the model toward another algorithm.\n----------- [25] code: 105 lines; first: d_full = {(r[\"src\"], r[\"base\"]): r[\"delta_full\"] for r in tf_rows}\n=========== [26] markdown\n## Scaling back to the full run, and how to read the result\n\n**Larger replay.** Set `N_PAIRS = 100`, `N_BOOT = 2000`, `N_BOOT_CLASS = 500` and `DEMO_SEEDS = (0, 1, 2)` (the\noriginal values). For the run's full 600 held-out pairs, point `data` at the artifact's `full_method_out.json`, whose\n`T10_dec_teacher_forced` dataset has the same format. The replay then reproduces `results/dec_T10.json`: recovery\n7.67 / 8.12 / 8.43 / 9.26 at ranks 1 / 2 / 4 / 8, with the same CIs. The stored Deltas are rounded to 4 decimals, so\nthe agreement is to about four decimals.\n\n**The GPU stages.** Inside the artifact folder:\n\n```bash\nuv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml\nhf download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218\nhf download google/gemma-3-4b-it --revision 093f9f388b31de276ce2de164bdc2081324b9767\n.venv/bin/python method.py              # about 3.5 GPU-hours on one 23 GB L4\n.venv/bin/python method.py --cpu-only   # the analysis / tables / figures / audit replayed in this notebook\n```\n\n**Reading it.** The rank-4 edit at the decision token is a strong, reproducible handle, and it works in generation\n(29/30 correct DFS programs). It is not the model's own algorithm variable, for three reasons:\n\n1. **Specificity (c2, c3).** It works almost as well when fitted to the wrong labels or to an untrained network.\n2. **Location (OFF-MANIFOLD, c4, c5).** It acts where exchanging the whole state barely matters: Delta 17 vs 2 nats.\n3. **Coherence.** BFS edits in Qwen produce BFS openings but mostly broken programs (5 of 29 pass the hidden tests).\n\nRandom pushes from iteration 4 that also change the algorithm do not pass through these subspaces (clamp removal\n-0.01). No edit, push or clamp produced a novel algorithm: 0 'other' among 1,857 correct programs.", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
````

### [176] THINKING · 2026-10-26 14:07:41 UTC

```
Proofreading turned up a few issues: the intro conflates two controls' ranges (should be c2 at 11-87%, c3 at 41-69%), section 3 overstates GPU requirements, the decision-position wording doesn't match cfg8.py, and the scaling texts need updating for the original values. I'll fix these now.
```

### [177] TOOL CALL — Edit · 2026-10-26 14:07:41 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py
OLD: | T10 decision token | Qwen3-8B | block output at the last prefilled token ` def` (response token 11, after `def solve(n, edges):` + indent) | BFS / DFS / union-find |
| T10 task band | Qwen3-8B | blocks 12-23 at every task-spec position, one shared map | same |
| GRID decision token | gemma-3-4b-it | response index 32 of the grid-path answer | BFS / DFS |
NEW: | T10 decision token | Qwen3-8B | block output at the last prefilled opening token ` def` (after `def solve(n, edges):` + indent); its next token, response token 11, names the helper | BFS / DFS / union-find |
| T10 task band | Qwen3-8B | blocks 12-23 at every task-spec position, one shared map | same |
| GRID decision token | gemma-3-4b-it | the last token of a prefilled 32-token opening; its next token is response index 32 | BFS / DFS |
```

### [178] TOOL RESULT — Edit · 2026-10-26 14:07:41 UTC

```
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py", "oldString": "| T10 decision token | Qwen3-8B | block output at the last prefilled token ` def` (response token 11, after `def solve(n, edges):` + indent) | BFS / DFS / union-find |\n| T10 task band | Qwen3-8B | blocks 12-23 at every task-spec position, one shared map | same |\n| GRID decision token | gemma-3-4b-it | response index 32 of the grid-path answer | BFS / DFS |", "newString": "| T10 decision token | Qwen3-8B | block output at the last prefilled opening token ` def` (after `def solve(n, edges):` + indent); its next token, response token 11, names the helper | BFS / DFS / union-find |\n| T10 task band | Qwen3-8B | blocks 12-23 at every task-spec position, one shared map | same |\n| GRID decision token | gemma-3-4b-it | the last token of a prefilled 32-token opening; its next token is response index 32 | BFS / DFS |", "originalFile": null, "structuredPatch": [{"oldStart": 29, "oldLines": 9, "newStart": 29, "newLines": 9, "lines": [" ", " | site | model | where the edit is made | classes |", " |---|---|---|---|", "-| T10 decision token | Qwen3-8B | block output at the last prefilled token ` def` (response token 11, after `def solve(n, edges):` + indent) | BFS / DFS / union-find |", "+| T10 decision token | Qwen3-8B | block output at the last prefilled opening token ` def` (after `def solve(n, edges):` + indent); its next token, response token 11, names the helper | BFS / DFS / union-find |", " | T10 task band | Qwen3-8B | blocks 12-23 at every task-spec position, one shared map | same |", "-| GRID decision token | gemma-3-4b-it | response index 32 of the grid-path answer | BFS / DFS |", "+| GRID decision token | gemma-3-4b-it | the last token of a prefilled 32-token opening; its next token is response index 32 | BFS / DFS |", " ", " - **map:** a linear orthonormal `R` (d_model x 8, nested ranks 1/2/4/8); **interchange** `h <- h + R(R^T h_src - R^T h_base)`;", " - **objective:** KL from the source prompt's own class distribution to the edited base's (bounded, CDAS-style);"]}], "userModified": false, "replaceAll": false}
```

### [179] TOOL CALL — Edit · 2026-10-26 14:07:41 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py
OLD: Qwen3-8B write a correct DFS program on 29 of 30 slots where it otherwise writes union-find. But no site passes the
specificity controls. Maps fitted to *wrong labels* (c2) or on a *randomly initialised* network (c3) still reach 41-87%
of the effect. At the T10 decision site, the DAS edit moves the margin about 8 times more than exchanging the whole
NEW: Qwen3-8B write a correct DFS program on 29 of 30 slots where it otherwise writes union-find. But no site passes the
specificity controls. Maps fitted to *wrong labels* (c2) still reach 11-87% of the true map's effect (limit 10%), and
maps fitted on a *randomly initialised* network (c3) reach 41-69% (limit 25%). At the T10 decision site, the DAS edit
moves the margin about 8 times more than exchanging the whole
```

### [180] TOOL RESULT — Edit · 2026-10-26 14:07:41 UTC

```
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py", "oldString": "Qwen3-8B write a correct DFS program on 29 of 30 slots where it otherwise writes union-find. But no site passes the\nspecificity controls. Maps fitted to *wrong labels* (c2) or on a *randomly initialised* network (c3) still reach 41-87%\nof the effect. At the T10 decision site, the DAS edit moves the margin about 8 times more than exchanging the whole", "newString": "Qwen3-8B write a correct DFS program on 29 of 30 slots where it otherwise writes union-find. But no site passes the\nspecificity controls. Maps fitted to *wrong labels* (c2) still reach 11-87% of the true map's effect (limit 10%), and\nmaps fitted on a *randomly initialised* network (c3) reach 41-69% (limit 25%). At the T10 decision site, the DAS edit\nmoves the margin about 8 times more than exchanging the whole", "originalFile": null, "structuredPatch": [{"oldStart": 44, "oldLines": 8, "newStart": 44, "newLines": 9, "lines": [" ", " **Result: K2 is DISCONFIRMED (p_K2 = 0.037).** DAS finds a strong rank-4 *steering handle*. For example, it makes", " Qwen3-8B write a correct DFS program on 29 of 30 slots where it otherwise writes union-find. But no site passes the", "-specificity controls. Maps fitted to *wrong labels* (c2) or on a *randomly initialised* network (c3) still reach 41-87%", "-of the effect. At the T10 decision site, the DAS edit moves the margin about 8 times more than exchanging the whole", "+specificity controls. Maps fitted to *wrong labels* (c2) still reach 11-87% of the true map's effect (limit 10%), and", "+maps fitted on a *randomly initialised* network (c3) reach 41-69% (limit 25%). At the T10 decision site, the DAS edit", "+moves the margin about 8 times more than exchanging the whole", " state does, which marks the handle as off-manifold. In plain words: you can push the model into writing a different", " algorithm, but the push does not reveal a hidden \"algorithm switch\".", " "]}], "userModified": false, "replaceAll": false}
```

### [181] TOOL CALL — Edit · 2026-10-26 14:07:41 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py
OLD: The **demo knobs** at the top set how much of the stored data is replayed and how many bootstrap resamples are
drawn. They start small; the original values are given in the comments. The **protocol constants** below them are
copied from `src/cfg8.py`. They were committed (hash-chained, `commitments.log`) before any GPU use, so they are not
tuning knobs.
NEW: The **demo knobs** at the top set how much of the stored data is replayed and how many bootstrap resamples are
drawn. They are at the original values, except that `N_PAIRS` is capped by the 100 pairs shipped in the mini data
(the run had 600). The replay takes under a second. For the smallest run that still produces every output, use
`N_PAIRS = 10`, `N_BOOT = N_BOOT_CLASS = 20` and `DEMO_SEEDS = (0,)`.

The **protocol constants** below them are copied from `src/cfg8.py`. They were committed (hash-chained,
`commitments.log`) before any GPU use, so they are not tuning knobs.
```

### [182] TOOL RESULT — Edit · 2026-10-26 14:07:41 UTC

```
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py", "oldString": "The **demo knobs** at the top set how much of the stored data is replayed and how many bootstrap resamples are\ndrawn. They start small; the original values are given in the comments. The **protocol constants** below them are\ncopied from `src/cfg8.py`. They were committed (hash-chained, `commitments.log`) before any GPU use, so they are not\ntuning knobs.", "newString": "The **demo knobs** at the top set how much of the stored data is replayed and how many bootstrap resamples are\ndrawn. They are at the original values, except that `N_PAIRS` is capped by the 100 pairs shipped in the mini data\n(the run had 600). The replay takes under a second. For the smallest run that still produces every output, use\n`N_PAIRS = 10`, `N_BOOT = N_BOOT_CLASS = 20` and `DEMO_SEEDS = (0,)`.\n\nThe **protocol constants** below them are copied from `src/cfg8.py`. They were committed (hash-chained,\n`commitments.log`) before any GPU use, so they are not tuning knobs.", "originalFile": null, "structuredPatch": [{"oldStart": 142, "oldLines": 9, "newStart": 142, "newLines": 12, "lines": [" ## 1. Configuration", " ", " The **demo knobs** at the top set how much of the stored data is replayed and how many bootstrap resamples are", "-drawn. They start small; the original values are given in the comments. The **protocol constants** below them are", "-copied from `src/cfg8.py`. They were committed (hash-chained, `commitments.log`) before any GPU use, so they are not", "-tuning knobs.", "+drawn. They are at the original values, except that `N_PAIRS` is capped by the 100 pairs shipped in the mini data", "+(the run had 600). The replay takes under a second. For the smallest run that still produces every output, use", "+`N_PAIRS = 10`, `N_BOOT = N_BOOT_CLASS = 20` and `DEMO_SEEDS = (0,)`.", "+", "+The **protocol constants** below them are copied from `src/cfg8.py`. They were committed (hash-chained,", "+`commitments.log`) before any GPU use, so they are not tuning knobs.", " ''')", " ", " code(r'''"]}], "userModified": false, "replaceAll": false}
```

### [183] TOOL CALL — Edit · 2026-10-26 14:07:41 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py
OLD: `method.py` runs the stages below in order; each stage is resumable. Everything except the last row needs Qwen3-8B
(bf16) or gemma-3-4b-it on a GPU, about 3.2 GPU-hours on one NVIDIA L4. So this notebook loads their **outputs**:
NEW: `method.py` runs the stages below in order; each stage is resumable. The first and last rows run on the CPU
(`prompts8.py` needs only the tokenizers). Every row in between needs Qwen3-8B (bf16) or gemma-3-4b-it on a GPU, about
3.2 GPU-hours on one NVIDIA L4, so this notebook loads their **outputs**:
```

### [184] TOOL RESULT — Edit · 2026-10-26 14:07:41 UTC

```
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py", "oldString": "`method.py` runs the stages below in order; each stage is resumable. Everything except the last row needs Qwen3-8B\n(bf16) or gemma-3-4b-it on a GPU, about 3.2 GPU-hours on one NVIDIA L4. So this notebook loads their **outputs**:", "newString": "`method.py` runs the stages below in order; each stage is resumable. The first and last rows run on the CPU\n(`prompts8.py` needs only the tokenizers). Every row in between needs Qwen3-8B (bf16) or gemma-3-4b-it on a GPU, about\n3.2 GPU-hours on one NVIDIA L4, so this notebook loads their **outputs**:", "originalFile": null, "structuredPatch": [{"oldStart": 335, "oldLines": 8, "newStart": 335, "newLines": 9, "lines": [" md(r'''", " ## 3. The GPU stages: what produced the stored rows", " ", "-`method.py` runs the stages below in order; each stage is resumable. Everything except the last row needs Qwen3-8B", "-(bf16) or gemma-3-4b-it on a GPU, about 3.2 GPU-hours on one NVIDIA L4. So this notebook loads their **outputs**:", "+`method.py` runs the stages below in order; each stage is resumable. The first and last rows run on the CPU", "+(`prompts8.py` needs only the tokenizers). Every row in between needs Qwen3-8B (bf16) or gemma-3-4b-it on a GPU, about", "+3.2 GPU-hours on one NVIDIA L4, so this notebook loads their **outputs**:", " ", " | `method.py` stage | script | in this notebook |", " |---|---|---|"]}], "userModified": false, "replaceAll": false}
```

### [185] TOOL CALL — Edit · 2026-10-26 14:07:41 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py
OLD: **Larger replay.** Set `N_PAIRS = 100`, `N_BOOT = 2000`, `N_BOOT_CLASS = 500` and `DEMO_SEEDS = (0, 1, 2)` (the
original values). For the run's full 600 held-out pairs, point `data` at the artifact's `full_method_out.json`, whose
`T10_dec_teacher_forced` dataset has the same format. The replay then reproduces `results/dec_T10.json`: recovery
NEW: **Larger replay.** The notebook already uses the original bootstrap settings (`N_BOOT = 2000`, `N_BOOT_CLASS = 500`,
`DEMO_SEEDS = (0, 1, 2)`) on all 100 shipped pairs. For the run's full 600 held-out pairs, point `data` at the
artifact's `full_method_out.json` and set `N_PAIRS = 600`; its `T10_dec_teacher_forced` dataset has the same format.
The replay then reproduces `results/dec_T10.json`: recovery
```

### [186] TOOL RESULT — Edit · 2026-10-26 14:07:41 UTC

```
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py", "oldString": "**Larger replay.** Set `N_PAIRS = 100`, `N_BOOT = 2000`, `N_BOOT_CLASS = 500` and `DEMO_SEEDS = (0, 1, 2)` (the\noriginal values). For the run's full 600 held-out pairs, point `data` at the artifact's `full_method_out.json`, whose\n`T10_dec_teacher_forced` dataset has the same format. The replay then reproduces `results/dec_T10.json`: recovery", "newString": "**Larger replay.** The notebook already uses the original bootstrap settings (`N_BOOT = 2000`, `N_BOOT_CLASS = 500`,\n`DEMO_SEEDS = (0, 1, 2)`) on all 100 shipped pairs. For the run's full 600 held-out pairs, point `data` at the\nartifact's `full_method_out.json` and set `N_PAIRS = 600`; its `T10_dec_teacher_forced` dataset has the same format.\nThe replay then reproduces `results/dec_T10.json`: recovery", "originalFile": null, "structuredPatch": [{"oldStart": 1215, "oldLines": 9, "newStart": 1215, "newLines": 10, "lines": [" md(r'''", " ## Scaling back to the full run, and how to read the result", " ", "-**Larger replay.** Set `N_PAIRS = 100`, `N_BOOT = 2000`, `N_BOOT_CLASS = 500` and `DEMO_SEEDS = (0, 1, 2)` (the", "-original values). For the run's full 600 held-out pairs, point `data` at the artifact's `full_method_out.json`, whose", "-`T10_dec_teacher_forced` dataset has the same format. The replay then reproduces `results/dec_T10.json`: recovery", "+**Larger replay.** The notebook already uses the original bootstrap settings (`N_BOOT = 2000`, `N_BOOT_CLASS = 500`,", "+`DEMO_SEEDS = (0, 1, 2)`) on all 100 shipped pairs. For the run's full 600 held-out pairs, point `data` at the", "+artifact's `full_method_out.json` and set `N_PAIRS = 600`; its `T10_dec_teacher_forced` dataset has the same format.", "+The replay then reproduces `results/dec_T10.json`: recovery", " 7.67 / 8.12 / 8.43 / 9.26 at ranks 1 / 2 / 4 / 8, with the same CIs. The stored Deltas are rounded to 4 decimals, so", " the agreement is to about four decimals.", " "]}], "userModified": false, "replaceAll": false}
```

### [187] TOOL CALL — Edit · 2026-10-26 14:07:41 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py
OLD: .venv/bin/python method.py              # about 3.5 GPU-hours on one 23 GB L4
NEW: .venv/bin/python method.py              # everything: about 3.5 h on one 23 GB L4 (3.2 GPU-hours)
```

### [188] TOOL RESULT — Edit · 2026-10-26 14:07:41 UTC

````
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py", "oldString": ".venv/bin/python method.py              # about 3.5 GPU-hours on one 23 GB L4", "newString": ".venv/bin/python method.py              # everything: about 3.5 h on one 23 GB L4 (3.2 GPU-hours)", "originalFile": null, "structuredPatch": [{"oldStart": 1228, "oldLines": 7, "newStart": 1228, "newLines": 7, "lines": [" uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml", " hf download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218", " hf download google/gemma-3-4b-it --revision 093f9f388b31de276ce2de164bdc2081324b9767", "-.venv/bin/python method.py              # about 3.5 GPU-hours on one 23 GB L4", "+.venv/bin/python method.py              # everything: about 3.5 h on one 23 GB L4 (3.2 GPU-hours)", " .venv/bin/python method.py --cpu-only   # the analysis / tables / figures / audit replayed in this notebook", " ```", " "]}], "userModified": false, "replaceAll": false}
````

### [189] THINKING · 2026-10-26 14:08:13 UTC

```
I'll avoid fully swapping to `full_method_out.json` since that would drop demo-only metadata (`prompt_segments`, `demo_subset`) still used by two cells—instead I'll merge in just the full dataset, and make the example-pair lookup handle prompts missing from the mini data, then test it.
```

### [190] TOOL CALL — Edit · 2026-10-26 14:08:13 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py
OLD: `DEMO_SEEDS = (0, 1, 2)`) on all 100 shipped pairs. For the run's full 600 held-out pairs, point `data` at the
artifact's `full_method_out.json` and set `N_PAIRS = 600`; its `T10_dec_teacher_forced` dataset has the same format.
The replay then reproduces `results/dec_T10.json`: recovery
NEW: `DEMO_SEEDS = (0, 1, 2)`) on all 100 shipped pairs. For the run's full 600 held-out pairs, load the artifact's
`full_method_out.json`, put its `T10_dec_teacher_forced` dataset (same format) in place of `data["datasets"][0]`,
and set `N_PAIRS = 600`. The replay then reproduces `results/dec_T10.json`: recovery
```

### [191] TOOL RESULT — Edit · 2026-10-26 14:08:13 UTC

```
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py", "oldString": "`DEMO_SEEDS = (0, 1, 2)`) on all 100 shipped pairs. For the run's full 600 held-out pairs, point `data` at the\nartifact's `full_method_out.json` and set `N_PAIRS = 600`; its `T10_dec_teacher_forced` dataset has the same format.\nThe replay then reproduces `results/dec_T10.json`: recovery", "newString": "`DEMO_SEEDS = (0, 1, 2)`) on all 100 shipped pairs. For the run's full 600 held-out pairs, load the artifact's\n`full_method_out.json`, put its `T10_dec_teacher_forced` dataset (same format) in place of `data[\"datasets\"][0]`,\nand set `N_PAIRS = 600`. The replay then reproduces `results/dec_T10.json`: recovery", "originalFile": null, "structuredPatch": [{"oldStart": 1216, "oldLines": 9, "newStart": 1216, "newLines": 9, "lines": [" ## Scaling back to the full run, and how to read the result", " ", " **Larger replay.** The notebook already uses the original bootstrap settings (`N_BOOT = 2000`, `N_BOOT_CLASS = 500`,", "-`DEMO_SEEDS = (0, 1, 2)`) on all 100 shipped pairs. For the run's full 600 held-out pairs, point `data` at the", "-artifact's `full_method_out.json` and set `N_PAIRS = 600`; its `T10_dec_teacher_forced` dataset has the same format.", "-The replay then reproduces `results/dec_T10.json`: recovery", "+`DEMO_SEEDS = (0, 1, 2)`) on all 100 shipped pairs. For the run's full 600 held-out pairs, load the artifact's", "+`full_method_out.json`, put its `T10_dec_teacher_forced` dataset (same format) in place of `data[\"datasets\"][0]`,", "+and set `N_PAIRS = 600`. The replay then reproduces `results/dec_T10.json`: recovery", " 7.67 / 8.12 / 8.43 / 9.26 at ranks 1 / 2 / 4 / 8, with the same CIs. The stored Deltas are rounded to 4 decimals, so", " the agreement is to about four decimals.", " "]}], "userModified": false, "replaceAll": false}
```

### [192] TOOL CALL — Edit · 2026-10-26 14:08:13 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py
OLD: seg = md["prompt_segments"]
print(f"\nSOURCE {src}: {seg[src]['segment']}")
print(f"BASE   {base}: {seg[base]['segment']}")
NEW: seg = md["prompt_segments"]                      # readable texts of the prompts used by the 100 shipped pairs
print(f"\nSOURCE {src}: {seg.get(src, {'segment': 'n/a'})['segment']}")
print(f"BASE   {base}: {seg.get(base, {'segment': 'n/a'})['segment']}")
```

### [193] TOOL RESULT — Edit · 2026-10-26 14:08:13 UTC

```
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/_build_notebook.py", "oldString": "seg = md[\"prompt_segments\"]\nprint(f\"\\nSOURCE {src}: {seg[src]['segment']}\")\nprint(f\"BASE   {base}: {seg[base]['segment']}\")", "newString": "seg = md[\"prompt_segments\"]                      # readable texts of the prompts used by the 100 shipped pairs\nprint(f\"\\nSOURCE {src}: {seg.get(src, {'segment': 'n/a'})['segment']}\")\nprint(f\"BASE   {base}: {seg.get(base, {'segment': 'n/a'})['segment']}\")", "originalFile": null, "structuredPatch": [{"oldStart": 406, "oldLines": 9, "newStart": 406, "newLines": 9, "lines": [" # one pair in words: the source prompt names an algorithm; the base is a neutral twin; both share the task text", " e = examples[0]", " src, base = PAIR_RE.search(e[\"input\"]).groups()", "-seg = md[\"prompt_segments\"]", "-print(f\"\\nSOURCE {src}: {seg[src]['segment']}\")", "-print(f\"BASE   {base}: {seg[base]['segment']}\")", "+seg = md[\"prompt_segments\"]                      # readable texts of the prompts used by the 100 shipped pairs", "+print(f\"\\nSOURCE {src}: {seg.get(src, {'segment': 'n/a'})['segment']}\")", "+print(f\"BASE   {base}: {seg.get(base, {'segment': 'n/a'})['segment']}\")", " print(f\"shared task text: {md['t10_task_text'][:150]} ...\")", " print(f\"class at the decision token: source -> {e['metadata_class_src']}, base -> {e['metadata_class_base']}\")", " print(f\"Delta of the full-state exchange: {e['metadata_delta_full']:.2f} nats\")"]}], "userModified": false, "replaceAll": false}
```

### [194] TOOL CALL — Bash · 2026-10-26 14:08:13 UTC

```
Test documented full-600-pair path in a temp copy:
python3 _build_notebook.py --n_pairs 100 --n_boot 2000 --n_boot_class 500 --seeds "(0, 1, 2)" && mkdir -p _tmp_full && python3 - <<'EOF'
# variant of the notebook for the documented full-data path (temporary; deleted after the check)
import json
nb = json.load(open("code_demo.ipynb"))
A = "/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40/full_method_out.json"
for c in nb["cells"]:
    s = "".join(c["source"])
    if s.startswith("data = load_data()"):
        s = s.replace("data = load_data()", "data = load_data()\n_full = json.loads(Path(%r).read_text())\ndata['datasets'][0] = next(d for d in _full['datasets'] if d['dataset'] == 'T10_dec_teacher_forced')" % A)
        c["source"] = s
    if "N_PAIRS = 100" in s:
        c["source"] = s.replace("N_PAIRS = 100 ", "N_PAIRS = 600 ")
json.dump(nb, open("_tmp_full/code_demo_full.ipynb", "w"))
EOF
cp mini_demo_data.json _tmp_full/ && ENV=/tmp/aii_nb_test_envs/art_e-_q5mSJGrSb-df3879c8a834 && UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 $ENV && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python $ENV/bin/python jupyter ipykernel && cd _tmp_full && $ENV/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo_full.ipynb --output code_demo_full.ipynb 2>&1 | grep -v "Kernel is running" | tail -5 && python3 - <<'EOF'
import json
nb=json.load(open("code_demo_full.ipynb"))
errs=[(i,o["ename"],o["evalue"]) for i,c in enumerate(nb["cells"]) if c["cell_type"]=="code" for o in c["outputs"] if o["output_type"]=="error"]
print("errors:", errs)
for o in nb["cells"][13]["outputs"]:
    if o["output_type"]=="stream": print("".join(o["text"])[:1400])
EOF
```

### [195] TOOL RESULT — Bash · 2026-10-26 14:08:31 UTC

```
{"stdout": "code_demo.ipynb: 27 cells\n[NbConvertApp] Converting notebook code_demo_full.ipynb to notebook\n[NbConvertApp] Writing 610897 bytes to code_demo_full.ipynb\nerrors: []\n14:08:29|INFO   |T10: k* = 4; recovery 8.433 CI [5.944443684513753, 11.296072925698121]\n\n\nT10 decision site, block L* = 22: 600 held-out pairs replayed (552 with |Delta_full| >= 1 nat enter the recovery), N_BOOT = 2000\nrank |  replay, seed 0 [95% CI] |  published, 552 pairs [95% CI] | random subspaces (c1) median\n   1 |   7.67 [5.11, 10.71] |         7.67 [5.11, 10.71] | -0.009\n   2 |   8.12 [5.60, 11.02] |         8.12 [5.60, 11.02] | -0.006\n   4 |   8.43 [5.94, 11.30] |         8.43 [5.94, 11.30] | -0.005\n   8 |   9.26 [6.83, 12.03] |         9.26 [6.83, 12.03] | 0.001\nseed 1: k1 7.98 (published 7.98), k2 8.06 (published 8.06), k4 8.58 (published 8.58), k8 9.60 (published 9.60)\nseed 2: k1 7.61 (published 7.61), k2 7.79 (published 7.79), k4 7.84 (published 7.84), k8 8.75 (published 8.75)\n\nby source class at k* = 4 (seed 0):\n  bfs        n = 268: recovery 15.38 (mean Delta DAS 23.3 vs full 1.51 nats); published 15.38 on 268 pairs\n  dfs        n = 264: recovery 5.47 (mean Delta DAS 12.7 vs full 2.33 nats); published 5.47 on 264 pairs\n  union_find n =  20: recovery -0.07 (mean Delta DAS -0.4 vs full 5.85 nats); published -0.07 on 20 pairs\n\nk* = 4 (published 4); mean Delta: DAS 17.4 vs full-state 2.06 nats; OFF-MANIFOLD flag (recovery > 1.5): True (published True)", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [196] THINKING · 2026-10-26 14:08:45 UTC

```
Verified that running on all 600 pairs reproduces every published number (recovery by rank, CIs, per-seed and per-class values), confirming the replay matches `run_dec.py`. Now running the rebuilt notebook from the workspace root and cleaning up the temporary files.
```

### [197] TOOL CALL — Bash · 2026-10-26 14:08:45 UTC

```
Final notebook execution, checks, and temp cleanup:
cd /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb && ENV=/tmp/aii_nb_test_envs/art_e-_q5mSJGrSb-df3879c8a834 && t0=$(date +%s) && UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 $ENV && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python $ENV/bin/python jupyter ipykernel && t1=$(date +%s) && $ENV/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | grep -v "Kernel is running over TCP" | tail -5; t2=$(date +%s); echo "venv+jupyter: $((t1-t0)) s; nbconvert execute: $((t2-t1)) s" && python3 - <<'EOF'
import json
from datetime import datetime
nb=json.load(open("code_demo.ipynb"))
t=lambda s: datetime.fromisoformat(s.replace("Z","+00:00"))
errs=[(i,o["ename"],o["evalue"]) for i,c in enumerate(nb["cells"]) if c["cell_type"]=="code" for o in c["outputs"] if o["output_type"]=="error"]
stderr=[i for i,c in enumerate(nb["cells"]) if c["cell_type"]=="code" for o in c["outputs"] if o["output_type"]=="stream" and o["name"]=="stderr"]
unexec=[i for i,c in enumerate(nb["cells"]) if c["cell_type"]=="code" and c.get("execution_count") is None]
times={i: round((t(c["metadata"]["execution"]["shell.execute_reply"])-t(c["metadata"]["execution"]["iopub.execute_input"])).total_seconds(),2) for i,c in enumerate(nb["cells"]) if c["cell_type"]=="code"}
print("errors:", errs, "| stderr cells:", stderr, "| unexecuted:", unexec)
print("cell times (s):", times, "sum", round(sum(times.values()),1))
print("".join(nb["cells"][11]["outputs"][0]["text"])[:900])
EOF
rm -rf _tmp_full _tmp_png _build_notebook.py && ls -la
```

### [198] TOOL RESULT — Bash · 2026-10-26 14:08:57 UTC

```
{"stdout": "[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[NbConvertApp] Writing 588581 bytes to code_demo.ipynb\nvenv+jupyter: 1 s; nbconvert execute: 12 s\nerrors: [] | stderr cells: [] | unexecuted: []\ncell times (s): {1: 6.64, 2: 0.55, 3: 0.0, 4: 0.11, 6: 0.0, 8: 0.03, 11: 0.01, 13: 0.38, 15: 0.01, 17: 0.01, 19: 0.01, 21: 0.01, 23: 0.53, 25: 0.29} sum 8.6\nT10_dec_teacher_forced: 100 held-out pairs -> 1200 rows (pair x fit seed x rank)\n\nSOURCE T10|forced|k4|j0|bfs: Write an implementation based on breadth-first search (BFS).\nBASE   T10|twin|W5|baby: Write a correct solution that does not use baby. . . . (padded with ' .' tokens)\nshared task text: Task: write a Python function solve(n, edges) that returns the number of connected components of an undirected graph. The nodes are the integers 0 to  ...\nclass at the decision token: source -> bfs, base -> union_find\nDelta of the full-state exchange: 2.12 nats\nDelta of the DAS edit (seed 0): rank 1: 22.43, rank 2: 22.24, rank 4: 22.49, rank 8: 22.62\n\ntotal 6303\ndrwxrwxrwx 3 aii-agent aii-agent 2000233 Oct 26 14:08 .\ndrwxrwxrwx 9 aii-agent aii-agent 2001784 Oct 26 14:06 ..\ndrwxrwxrwx 2 aii-agent aii-agent       1 Oct 26 13:36 .aii\n-rw-rw-rw- 1 aii-agent aii-agent      54 Oct 26 13:37 .aii_claude_session.json\n-rw-rw-rw- 1 aii-agent aii-agent 1594989 Oct 26 14:08 .repl_agent.ptylog\n-rw-rw-rw- 1 aii-agent aii-agent    6627 Oct 26 13:46 build_mini_demo_data.py\n-rw-rw-rw- 1 aii-agent aii-agent  588585 Oct 26 14:08 code_demo.ipynb\n-rw-rw-rw- 1 aii-agent aii-agent  259719 Oct 26 13:46 mini_demo_data.json", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [199] THINKING · 2026-10-26 14:09:15 UTC

```
The clean run completed in 12s with no errors, and temp files are cleaned up. Next I'll handle TODO 6: setting the exact GitHub URL, data file, URL-first loading pattern, and running an nbformat schema check.
```

### [200] TOOL CALL — Bash · 2026-10-26 14:09:15 UTC

```
Verify URL, data file, loader pattern, notebook schema:
URL='GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-8/experiment-40/demo/mini_demo_data.json"' && python3 - "$URL" <<'EOF'
import json, sys
url_line = sys.argv[1]
nb = json.load(open("code_demo.ipynb"))
srcs = ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]
loader = next(s for s in srcs if "def load_data" in s)
print("(1) exact GITHUB_DATA_URL line present:", any(url_line in s for s in srcs))
print("(3) urlopen(GITHUB_DATA_URL) used before local fallback:", "urllib.request.urlopen(GITHUB_DATA_URL" in loader and loader.index("urlopen(GITHUB_DATA_URL") < loader.index('Path("mini_demo_data.json")'))
print("    data = load_data() called:", any(s.startswith("data = load_data()") for s in srcs))
print("    any bare open('mini_demo_data.json'):", any("open('mini_demo_data.json')" in s or 'open("mini_demo_data.json")' in s for s in srcs))
EOF
echo "(2) mini_demo_data.json:"; ls -la mini_demo_data.json && python3 -c "import json; d=json.load(open('mini_demo_data.json')); print('   valid JSON; datasets:', [(x['dataset'], len(x['examples'])) for x in d['datasets']])"
/tmp/aii_nb_test_envs/art_e-_q5mSJGrSb-df3879c8a834/bin/python -c "import nbformat; nb=nbformat.read('code_demo.ipynb', as_version=4); nbformat.validate(nb); print('nbformat validate: OK,', len(nb.cells), 'cells')"
grep -c "/ai-inventor" code_demo.ipynb mini_demo_data.json build_mini_demo_data.py || true
```

### [201] TOOL RESULT — Bash · 2026-10-26 14:09:17 UTC

```
{"stdout": "(1) exact GITHUB_DATA_URL line present: True\n(3) urlopen(GITHUB_DATA_URL) used before local fallback: True\n    data = load_data() called: True\n    any bare open('mini_demo_data.json'): False\n(2) mini_demo_data.json:\n-rw-rw-rw- 1 aii-agent aii-agent 259719 Oct 26 13:46 mini_demo_data.json\n   valid JSON; datasets: [('T10_dec_teacher_forced', 100)]\nnbformat validate: OK, 27 cells\ncode_demo.ipynb:1\nmini_demo_data.json:0\nbuild_mini_demo_data.py:0", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [202] ASSISTANT · 2026-10-26 14:09:23 UTC

```
All three TODO 6 checks pass and the notebook validates. But `code_demo.ipynb` contains one absolute server path (`/ai-inventor`), which must not ship in a published file. Let me find it.
```

### [203] TOOL CALL — Bash · 2026-10-26 14:09:23 UTC

```
Locate absolute path inside the notebook:
grep -o ".\{200\}/ai-inventor.\{200\}" code_demo.ipynb | head -3; python3 - <<'EOF'
import json
nb=json.load(open("code_demo.ipynb"))
for i,c in enumerate(nb["cells"]):
    s=json.dumps(c)
    if "/ai-inventor" in s:
        print("cell", i, c["cell_type"])
        for o in c.get("outputs",[]):
            t=json.dumps(o)
            if "/ai-inventor" in t: print("  in output type", o["output_type"], t[:100])
        if "/ai-inventor" in "".join(c["source"]): print("  in source")
print("nb metadata has it:", "/ai-inventor" in json.dumps(nb["metadata"]))
EOF
```

### [204] TOOL RESULT — Bash · 2026-10-26 14:09:23 UTC

```
{"stdout": "cell 3 code\n  in source\nnb metadata has it: False", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [205] TOOL CALL — Bash · 2026-10-26 14:09:29 UTC

```
Confirm match is the GitHub org name only:
grep -o "[^\"]\{0,40\}/ai-inventor[^\"]\{0,40\}" code_demo.ipynb; echo "strict server-path matches:"; grep -c "/ai-inventor/\|aii_data\|/tmp/\|/var/lib" code_demo.ipynb mini_demo_data.json build_mini_demo_data.py || true
```

### [206] TOOL RESULT — Bash · 2026-10-26 14:09:29 UTC

```
{"stdout": "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-\nstrict server-path matches:\ncode_demo.ipynb:0\nmini_demo_data.json:0\nbuild_mini_demo_data.py:0", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [207] THINKING · 2026-10-26 14:10:21 UTC

```
That match is just the GitHub org name in the required URL, not a server path—nothing relevant found there. Now checking the storage manifest and README files.
```

### [208] TOOL CALL — Write · 2026-10-26 14:10:21 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/.aii/manifest.yaml

# Storage decisions for this folder (the demo of art_e-_q5mSJGrSb).
# Nothing here needs a keep/delete decision: every file is a notebook, JSON, Python or Markdown file, and the
# largest (code_demo.ipynb, about 0.6 MB with its outputs) is far below the 10 MB auto-keep floor. No cache, venv or
# model weights were written here; the notebook was tested in a venv on local disk outside this folder.
entries: []
```

### [209] TOOL RESULT — Write · 2026-10-26 14:10:21 UTC

```
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/.aii/manifest.yaml", "content": "# Storage decisions for this folder (the demo of art_e-_q5mSJGrSb).\n# Nothing here needs a keep/delete decision: every file is a notebook, JSON, Python or Markdown file, and the\n# largest (code_demo.ipynb, about 0.6 MB with its outputs) is far below the 10 MB auto-keep floor. No cache, venv or\n# model weights were written here; the notebook was tested in a venv on local disk outside this folder.\nentries: []\n", "structuredPatch": [], "originalFile": null, "userModified": false}
```

### [210] TOOL CALL — Write · 2026-10-26 14:10:21 UTC

````
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/README.md

# Demo notebook: searching for a hidden algorithm switch in code models

This folder is the runnable demo of the iteration-8 experiment artifact `art_e-_q5mSJGrSb`.

**The question (claim K2).** When a code model picks an algorithm, is that choice carried by a **low-rank causal
variable**? Two settings were tested:

- Qwen3-8B choosing BFS, DFS or union-find to count the connected components of a graph (unit T10);
- gemma-3-4b-it choosing BFS or DFS for a shortest grid path (unit GRID).

**The method.** The artifact answers with one pre-committed distributed-alignment-search (DAS) protocol: a linear
orthonormal map, a bounded KL objective and a class-margin readout at the decision token. Seven controls were
committed with their thresholds before any fit.

**The answer.** K2 is **disconfirmed** (p_K2 = 0.037). A rank-4 edit is a strong *steering handle*: Qwen3-8B writes
correct DFS on 29 of 30 slots. It is not the model's own variable:

- Maps fitted to wrong labels (c2) or on a randomly initialised network (c3) keep 11-87% of the effect.
- At the T10 decision site the edit moves the margin 8 times more than exchanging the whole state (OFF-MANIFOLD).

## Layout

| path | what it is |
|---|---|
| `code_demo.ipynb` | the demo notebook (27 cells, executed; outputs included) |
| `mini_demo_data.json` | the data the notebook loads (260 kB): 100 of the 600 held-out teacher-forced pairs of the T10 decision site, plus the artifact's per-stage result JSONs |
| `build_mini_demo_data.py` | rebuilds `mini_demo_data.json` from the artifact's `full_method_out.json` and `prompts/t10_prompts.jsonl` (standard library only) |
| `README.md` | this file |
| `.aii/manifest.yaml` | storage manifest (nothing heavy, so no entries) |

## What the notebook runs

The artifact's `method.py` chains about 20 stage scripts. The GPU stages take about 3.2 GPU-hours with Qwen3-8B and
gemma-3-4b-it, so a 10-minute CPU notebook cannot run them. Instead, the notebook replays the artifact's own
`method.py --cpu-only` path on the saved rows.

The code is copied from the artifact's modules. The only changes are the ones a notebook needs: results are read
from the loaded `data` instead of `results/*.json`, and figures and tables are shown inline instead of written to
files.

| notebook section | original code | change |
|---|---|---|
| 2. Statistics | `src/stats8.py` | verbatim, plus the estimator check from `tests/test_cpu_tiny.py` |
| 4. Replay of the T10 decision-site recovery | tail of `stage_dec()` in `src/run_dec.py` | `site.evaluate()` returns the stored per-pair Deltas (`StoredSite`) instead of running Qwen3-8B |
| 5. Controls and verdict per site | `src/analysis8.py:verdict` and the verdict loop of `main()` | per-site result JSONs read from the metadata block |
| 6. K2 and p_K2 | `src/analysis8.py:main` | same |
| 7. Result tables | `src/digest8.py` | rendered inline instead of written to `results/summary.md` |
| 8. Independent re-derivation | `audit/rederive.py` | rows and results read from memory; McNemar re-tested from the stored discordant counts |
| 9. Figures F1, F2, F4, F5 | `src/figures8.py` | shown inline. F3 needs the activation cache (`cache/states_*`), which is not shipped |
| 10. Results | new | per-pair Deltas (DAS vs full state), recovery by rank (replay vs published), stored MDS centroids of the activation geometry, summary table |

### What the shipped run gives

The shipped run uses all 100 pairs with the original bootstrap settings.

- **Recovery.** Teacher-forced recovery at k* = 4 is **7.76** [4.80, 11.22] on 92 usable pairs. The published value
  is 8.43 [5.94, 11.30] on 552 pairs.
- **Per class.** BFS 14.89 (published 15.38); DFS 5.49 (5.47); union-find -0.09 (-0.07).
- **Flag.** The OFF-MANIFOLD flag is raised, as published.
- **Verdicts.** All four verdicts are recomputed identically: T10-dec NO HANDLE; T10-band and GRID-dec SUFFICIENT
  HANDLE; block 24 post hoc fails c2 and c3.
- **K2.** DISCONFIRMED, p_K2 = 0.037, recomputed identically.
- **Audit.** The stdlib re-derivation agrees: TF recovery, the mediation Spearman of 0.39 with its failing placebo,
  K2, and the exact McNemar p-values.
- **Full data.** With the artifact's full 600 pairs swapped in, the replay reproduces the published table:
  recovery 7.67 / 8.12 / 8.43 / 9.26 at ranks 1 / 2 / 4 / 8, with the same CIs, per class and per seed. This was
  checked during development.

## How to run

**Colab.** Open `code_demo.ipynb` and run all cells. The install cell adds only `loguru`, because numpy, scipy and
matplotlib are pre-installed. The data load from the repository's raw URL, with a fallback to a local
`mini_demo_data.json`.

**Locally** (Python 3.12):

```bash
python3.12 -m venv .venv && .venv/bin/pip install jupyter ipykernel
.venv/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb
```

Outside Colab, the install cell installs Colab's versions: numpy 2.0.2, scipy 1.16.3 and matplotlib 3.10.0, plus
loguru 0.7.3. The processing cells take about 2 s in total. The rest of the runtime is package installation.

**Testing.** The notebook was tested in a clean Python 3.12 venv that held only jupyter and ipykernel, with
`nbconvert --execute` and a 600 s timeout. Scaling rounds:

| round | `N_PAIRS` | `N_BOOT` | `N_BOOT_CLASS` | `DEMO_SEEDS` | wall clock | recovery at k* |
|---|---|---|---|---|---|---|
| minimum | 10 | 20 | 20 | (0,) | 16 s | 9.00 |
| 1 | 25 | 200 | 100 | (0, 1) | 47 s (40 s of it pip) | 8.16 |
| 2 | 50 | 1000 | 250 | (0, 1, 2) | 64 s | 7.58 |
| shipped (original bootstrap settings) | 100 | 2000 | 500 | (0, 1, 2) | 12-46 s | 7.76 |

The wall-clock spread comes from the package installation (pip cache), not from the analysis.

**Scaling to the full run.**

- *Full teacher-forced table:* put the `T10_dec_teacher_forced` dataset of the artifact's `full_method_out.json` in
  place of `data["datasets"][0]` and set `N_PAIRS = 600`.
- *GPU stages:* run inside the artifact folder. The models are `Qwen/Qwen3-8B` at revision
  `b968826d9c46dd6066d109eabc6255188de91218` and `google/gemma-3-4b-it` at revision
  `093f9f388b31de276ce2de164bdc2081324b9767`. `method.py` runs every stage; `method.py --cpu-only` runs the stages
  this notebook replays. The commands are in the notebook's last cell.

## Restoring removed files

Nothing in this folder is marked for deletion: `.aii/manifest.yaml` has no entries, and every file here is published
with the repository.

The two inputs the notebook needs can always be rebuilt:

- **Packages:** `pip install loguru==0.7.3 numpy==2.0.2 scipy==1.16.3 matplotlib==3.10.0`. The notebook's first
  cell does this itself.
- **`mini_demo_data.json`:** `python3 build_mini_demo_data.py --artifact_dir <artifact folder>`, where the artifact
  folder holds `full_method_out.json` and `prompts/t10_prompts.jsonl`. The selection is deterministic (seed 0).
````

### [211] TOOL RESULT — Write · 2026-10-26 14:10:21 UTC

````
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/README.md", "content": "# Demo notebook: searching for a hidden algorithm switch in code models\n\nThis folder is the runnable demo of the iteration-8 experiment artifact `art_e-_q5mSJGrSb`.\n\n**The question (claim K2).** When a code model picks an algorithm, is that choice carried by a **low-rank causal\nvariable**? Two settings were tested:\n\n- Qwen3-8B choosing BFS, DFS or union-find to count the connected components of a graph (unit T10);\n- gemma-3-4b-it choosing BFS or DFS for a shortest grid path (unit GRID).\n\n**The method.** The artifact answers with one pre-committed distributed-alignment-search (DAS) protocol: a linear\northonormal map, a bounded KL objective and a class-margin readout at the decision token. Seven controls were\ncommitted with their thresholds before any fit.\n\n**The answer.** K2 is **disconfirmed** (p_K2 = 0.037). A rank-4 edit is a strong *steering handle*: Qwen3-8B writes\ncorrect DFS on 29 of 30 slots. It is not the model's own variable:\n\n- Maps fitted to wrong labels (c2) or on a randomly initialised network (c3) keep 11-87% of the effect.\n- At the T10 decision site the edit moves the margin 8 times more than exchanging the whole state (OFF-MANIFOLD).\n\n## Layout\n\n| path | what it is |\n|---|---|\n| `code_demo.ipynb` | the demo notebook (27 cells, executed; outputs included) |\n| `mini_demo_data.json` | the data the notebook loads (260 kB): 100 of the 600 held-out teacher-forced pairs of the T10 decision site, plus the artifact's per-stage result JSONs |\n| `build_mini_demo_data.py` | rebuilds `mini_demo_data.json` from the artifact's `full_method_out.json` and `prompts/t10_prompts.jsonl` (standard library only) |\n| `README.md` | this file |\n| `.aii/manifest.yaml` | storage manifest (nothing heavy, so no entries) |\n\n## What the notebook runs\n\nThe artifact's `method.py` chains about 20 stage scripts. The GPU stages take about 3.2 GPU-hours with Qwen3-8B and\ngemma-3-4b-it, so a 10-minute CPU notebook cannot run them. Instead, the notebook replays the artifact's own\n`method.py --cpu-only` path on the saved rows.\n\nThe code is copied from the artifact's modules. The only changes are the ones a notebook needs: results are read\nfrom the loaded `data` instead of `results/*.json`, and figures and tables are shown inline instead of written to\nfiles.\n\n| notebook section | original code | change |\n|---|---|---|\n| 2. Statistics | `src/stats8.py` | verbatim, plus the estimator check from `tests/test_cpu_tiny.py` |\n| 4. Replay of the T10 decision-site recovery | tail of `stage_dec()` in `src/run_dec.py` | `site.evaluate()` returns the stored per-pair Deltas (`StoredSite`) instead of running Qwen3-8B |\n| 5. Controls and verdict per site | `src/analysis8.py:verdict` and the verdict loop of `main()` | per-site result JSONs read from the metadata block |\n| 6. K2 and p_K2 | `src/analysis8.py:main` | same |\n| 7. Result tables | `src/digest8.py` | rendered inline instead of written to `results/summary.md` |\n| 8. Independent re-derivation | `audit/rederive.py` | rows and results read from memory; McNemar re-tested from the stored discordant counts |\n| 9. Figures F1, F2, F4, F5 | `src/figures8.py` | shown inline. F3 needs the activation cache (`cache/states_*`), which is not shipped |\n| 10. Results | new | per-pair Deltas (DAS vs full state), recovery by rank (replay vs published), stored MDS centroids of the activation geometry, summary table |\n\n### What the shipped run gives\n\nThe shipped run uses all 100 pairs with the original bootstrap settings.\n\n- **Recovery.** Teacher-forced recovery at k* = 4 is **7.76** [4.80, 11.22] on 92 usable pairs. The published value\n  is 8.43 [5.94, 11.30] on 552 pairs.\n- **Per class.** BFS 14.89 (published 15.38); DFS 5.49 (5.47); union-find -0.09 (-0.07).\n- **Flag.** The OFF-MANIFOLD flag is raised, as published.\n- **Verdicts.** All four verdicts are recomputed identically: T10-dec NO HANDLE; T10-band and GRID-dec SUFFICIENT\n  HANDLE; block 24 post hoc fails c2 and c3.\n- **K2.** DISCONFIRMED, p_K2 = 0.037, recomputed identically.\n- **Audit.** The stdlib re-derivation agrees: TF recovery, the mediation Spearman of 0.39 with its failing placebo,\n  K2, and the exact McNemar p-values.\n- **Full data.** With the artifact's full 600 pairs swapped in, the replay reproduces the published table:\n  recovery 7.67 / 8.12 / 8.43 / 9.26 at ranks 1 / 2 / 4 / 8, with the same CIs, per class and per seed. This was\n  checked during development.\n\n## How to run\n\n**Colab.** Open `code_demo.ipynb` and run all cells. The install cell adds only `loguru`, because numpy, scipy and\nmatplotlib are pre-installed. The data load from the repository's raw URL, with a fallback to a local\n`mini_demo_data.json`.\n\n**Locally** (Python 3.12):\n\n```bash\npython3.12 -m venv .venv && .venv/bin/pip install jupyter ipykernel\n.venv/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb\n```\n\nOutside Colab, the install cell installs Colab's versions: numpy 2.0.2, scipy 1.16.3 and matplotlib 3.10.0, plus\nloguru 0.7.3. The processing cells take about 2 s in total. The rest of the runtime is package installation.\n\n**Testing.** The notebook was tested in a clean Python 3.12 venv that held only jupyter and ipykernel, with\n`nbconvert --execute` and a 600 s timeout. Scaling rounds:\n\n| round | `N_PAIRS` | `N_BOOT` | `N_BOOT_CLASS` | `DEMO_SEEDS` | wall clock | recovery at k* |\n|---|---|---|---|---|---|---|\n| minimum | 10 | 20 | 20 | (0,) | 16 s | 9.00 |\n| 1 | 25 | 200 | 100 | (0, 1) | 47 s (40 s of it pip) | 8.16 |\n| 2 | 50 | 1000 | 250 | (0, 1, 2) | 64 s | 7.58 |\n| shipped (original bootstrap settings) | 100 | 2000 | 500 | (0, 1, 2) | 12-46 s | 7.76 |\n\nThe wall-clock spread comes from the package installation (pip cache), not from the analysis.\n\n**Scaling to the full run.**\n\n- *Full teacher-forced table:* put the `T10_dec_teacher_forced` dataset of the artifact's `full_method_out.json` in\n  place of `data[\"datasets\"][0]` and set `N_PAIRS = 600`.\n- *GPU stages:* run inside the artifact folder. The models are `Qwen/Qwen3-8B` at revision\n  `b968826d9c46dd6066d109eabc6255188de91218` and `google/gemma-3-4b-it` at revision\n  `093f9f388b31de276ce2de164bdc2081324b9767`. `method.py` runs every stage; `method.py --cpu-only` runs the stages\n  this notebook replays. The commands are in the notebook's last cell.\n\n## Restoring removed files\n\nNothing in this folder is marked for deletion: `.aii/manifest.yaml` has no entries, and every file here is published\nwith the repository.\n\nThe two inputs the notebook needs can always be rebuilt:\n\n- **Packages:** `pip install loguru==0.7.3 numpy==2.0.2 scipy==1.16.3 matplotlib==3.10.0`. The notebook's first\n  cell does this itself.\n- **`mini_demo_data.json`:** `python3 build_mini_demo_data.py --artifact_dir <artifact folder>`, where the artifact\n  folder holds `full_method_out.json` and `prompts/t10_prompts.jsonl`. The selection is deterministic (seed 0).\n", "structuredPatch": [], "originalFile": null, "userModified": false}
````

### [212] ASSISTANT · 2026-10-26 14:10:33 UTC

```
Let me confirm that the build script deterministically reproduces the shipped `mini_demo_data.json`, and that the manifest parses as YAML.
```

### [213] TOOL CALL — Bash · 2026-10-26 14:10:33 UTC

```
Check deterministic rebuild and manifest YAML:
python3 build_mini_demo_data.py --artifact_dir /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40 --out _check_rebuild.json > /dev/null && cmp _check_rebuild.json mini_demo_data.json && echo "rebuild identical: yes"; rm -f _check_rebuild.json; /tmp/aii_nb_test_envs/art_e-_q5mSJGrSb-df3879c8a834/bin/python -c "import yaml; print('manifest:', yaml.safe_load(open('.aii/manifest.yaml')))"; find . -name "__pycache__" -o -name "*.pyc" | head; ls -la . .aii
```

### [214] TOOL RESULT — Bash · 2026-10-26 14:10:33 UTC

```
{"stdout": "rebuild identical: yes\nmanifest: {'entries': []}\n.:\ntotal 6454\ndrwxrwxrwx 3 aii-agent aii-agent 2000244 Oct 26 14:10 .\ndrwxrwxrwx 9 aii-agent aii-agent 2001858 Oct 26 14:06 ..\ndrwxrwxrwx 2 aii-agent aii-agent   41100 Oct 26 14:09 .aii\n-rw-rw-rw- 1 aii-agent aii-agent      54 Oct 26 13:37 .aii_claude_session.json\n-rw-rw-rw- 1 aii-agent aii-agent 1701697 Oct 26 14:10 .repl_agent.ptylog\n-rw-rw-rw- 1 aii-agent aii-agent    6923 Oct 26 14:10 README.md\n-rw-rw-rw- 1 aii-agent aii-agent    6627 Oct 26 13:46 build_mini_demo_data.py\n-rw-rw-rw- 1 aii-agent aii-agent  588585 Oct 26 14:08 code_demo.ipynb\n-rw-rw-rw- 1 aii-agent aii-agent  259719 Oct 26 13:46 mini_demo_data.json\n\n.aii:\ntotal 1995\ndrwxrwxrwx 2 aii-agent aii-agent   41100 Oct 26 14:09 .\ndrwxrwxrwx 3 aii-agent aii-agent 2000244 Oct 26 14:10 ..\n-rw-rw-rw- 1 aii-agent aii-agent     411 Oct 26 14:09 manifest.yaml", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [215] ASSISTANT · 2026-10-26 14:10:39 UTC

```
The rebuild is byte-identical, the manifest parses, and there are no stray caches. Last step: the structured output file.
```

### [216] TOOL CALL — Write · 2026-10-26 14:10:39 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/.terminal_claude_agent_struct_out.json

{
 "out_expected_files": {
  "notebook": "code_demo.ipynb",
  "mini_data_file": "mini_demo_data.json"
 }
}
```

### [217] TOOL RESULT — Write · 2026-10-26 14:10:39 UTC

```
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_8/art_e-_q5mSJGrSb/.terminal_claude_agent_struct_out.json", "content": "{\n \"out_expected_files\": {\n  \"notebook\": \"code_demo.ipynb\",\n  \"mini_data_file\": \"mini_demo_data.json\"\n }\n}\n", "structuredPatch": [], "originalFile": null, "userModified": false}
```

### [218] ASSISTANT · 2026-10-26 14:10:58 UTC

```
I've built the demo notebook and its data file. It runs cleanly from a fresh Python 3.12 environment in 12–64 seconds, well under the 10-minute limit; nearly all of that time is package installation.

The artifact's `method.py` runs about 20 stage scripts. Most need Qwen3-8B or gemma-3-4b-it on a GPU (about 3.2 GPU-hours), so they can't run in the notebook. Instead it runs the artifact's own CPU-only stages (`method.py --cpu-only`) on the saved results. The code is copied from the original modules; the only changes are reading results from the loaded data instead of result files, and showing tables and figures inline. Where the GPU run evaluated the model, the notebook substitutes the per-pair results the run stored.

**What it reproduces**
- **Main measurement:** on the 100 shipped pairs, the edit-strength ratio ("recovery") at rank 4 is 7.76 [4.80, 11.22], against the published 8.43 [5.94, 11.30] on 552 pairs. The off-manifold flag is raised, as published.
- **Full data:** when I swapped in all 600 pairs from the artifact, every published recovery value, confidence interval, per-seed and per-class number matched to about four decimals. That confirms the replay is faithful.
- **Verdicts:** all four site verdicts and the overall K2 result (disconfirmed, p = 0.037) come out identical to the published ones.
- **Audit:** the artifact's independent standard-library checks also agree.

**Scaling:** I tested at the minimum settings first, then in three rounds. The shipped notebook uses the original bootstrap settings (2000 and 500 resamples, three fit seeds); only the number of pairs is capped at the 100 in the mini data. The round-by-round table is in `README.md`.

**Limitations and deviations:**
- **Geometry figure:** the original per-prompt geometry plot (F3) can't be redrawn, because it needs an activation cache the artifact doesn't ship. The notebook plots the stored group centroids from that embedding instead.
- **Figure labels:** one figure label was cut off under matplotlib 3.10, Colab's version. A small change to the figure-saving function fixes it.
- **GitHub URL:** it returns 404 until the files are pushed, so for now the notebook uses its local fallback, as intended.
- **Instructions:** I generated the notebook with a temporary builder script (since deleted) rather than NotebookEdit. There was no todo-tracking tool, so I followed the six TODOs in order without one.

Files are in the workspace:
- `code_demo.ipynb` (executed, outputs included)
- `mini_demo_data.json`
- `build_mini_demo_data.py` (rebuilds the data file byte-identically)
- `README.md`
- `.aii/manifest.yaml` (no entries; nothing heavy)
- `.terminal_claude_agent_struct_out.json`
```
