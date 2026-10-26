# gen_demo_art_experiment_46 — report_results

> Phase: `gen_paper_repo` · `gen_demo_art`
> Run: `gen_paper_repo_c164ac661673` — A Random Activation Push Changes a Code Model's Algorithm Where Temperature Does Not
>
> Full, verbatim transcript of this agent task — every system/user prompt, assistant response, thinking block, tool call and tool result — in the order they occurred. Nothing truncated.

## Task: `gen_demo_art_experiment_46` (terminal_claude_agent, claude-opus-5-5)

### [1] CONFIG · 2026-10-26 14:21:30 UTC

```
model: Claude Opus 5.5 | effort: max | permission: bypassPermissions
```

### [2] SYSTEM-USER prompt · 2026-10-26 14:21:40 UTC

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
Your workspace: `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2`

CRITICAL: Every file you create, write, or save MUST be inside this workspace directory (subdirectories OK). You MUST NOT write files anywhere outside this path — external paths are READ-ONLY. Use absolute paths for all file operations.

EVERY file write MUST start with `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/`:
GOOD: `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/file.py`, `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/results/out.json`
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
id: art_VVA3P0ocZNA2
type: experiment
title: Mapping grid algorithms with and without their names
summary: >-
  TP-G iteration 9 (claim N4). Qwen3-32B nf4 (truncated decoder, iteration 8's code unchanged) and Qwen3-8B bf16 ten-algorithm
  grid manifolds rebuilt four ways with fixed readout/block rule/k/landing code: M-name (300 alias prompts), M-desc (name-free
  descriptions passing a Qwen3-32B naming gate; JPS has none: [['bibfs|2', 0.15], ['jps|0', 0.7], ['jps|1', 0.6], ['jps|2',
  0.45]]), M-lex (alias minus token-matched neutral twin) and M-code (name-scrubbed verified programs; PRIMARY counts {'bfs':
  20, 'dfs': 20, 'bibfs': 8, 'iddfs': 2, 'astar': 20, 'gbfs': 20, 'dijkstra_unit': 20, 'idastar': 17, 'jps': 0, 'biastar':
  2}; classes over non-banned algorithms with >= 10 programs). NAMED OUTCOME: MIXED. Unit-Dijkstra (the iteration-8 survivor)
  class at k15: M-name OPPOSITE (rank 5/5, g/median 1.63); M-lex OPPOSITE (rank 4/5, g/median 1.20); M-desc OPPOSITE (rank
  3/4, g/median 1.08); M-code R1 EDGE (rank 1/2, g/median 0.67); M-code Qwen3-32B-only frame EDGE (rank 1/2, g/median 0.79);
  8B M-name OPPOSITE (rank 4/5, g/median 1.17), 8B M-desc OPPOSITE (rank 3/4, g/median 1.01), 8B M-code EDGE (rank 1/2, g/median
  0.63). Reproduction: per-prompt cosine >= 0.9999, g within 0.030, classes identical, but committed gate Spearman 0.894 <
  0.95 (k10: 0.997; kNN tie flips), fallback F1. Lexical: Spearman(g_alias, L1) on M-name -0.74 (k10) / -0.65 (k15), P4 True.
  RSA (exact 10! Mantel): M-name vs R_lex 0.46 (p 0.003), vs R_beh 0.24 (p 0.091); M-desc vs R_beh 0.12 (p 0.252); M-code
  vs R_beh 0.64 (p 0.018), vs R_surface 0.67 (p 0.010). Placement on M-code: LOO accuracy 0.85; uDij survivors EDGE 15/15.
  Predictions pass: {'P1': False, 'P2': False, 'P3': True, 'P4': True, 'P5': None, 'P6': True, 'P7': None, 'P8': True}. Audits:
  rederive.py 0 mismatches, audit_states mismatches []. Geometry is correlational. OpenRouter USD 0.094. Files: results/n4_verdict.json,
  results/geometry_*.json, rsa.json, lexical_regression.json, placement.json, figures/ (PCA/MDS/Isomap in activation coordinates),
  method_out.json; cache/states/ (states + frozen geodesic graphs geo_*_k10/k15.npz for iteration 10) stays on the run volume,
  not in the repository.
workspace_path: >-
  /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46
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
Raw data URL: https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-9/experiment-46/demo/mini_demo_data.json

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
GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-9/experiment-46/demo/mini_demo_data.json"
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
To test-run the notebook in a clean environment (simulating Colab), use the disposable venv at `/tmp/aii_nb_test_envs/art_VVA3P0ocZNA2-b603e68c357e`. It is on this machine's local disk, outside your workspace, which is on a slow network volume: never create a venv inside your workspace.
```bash
UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_VVA3P0ocZNA2-b603e68c357e
UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_VVA3P0ocZNA2-b603e68c357e/bin/python jupyter ipykernel
/tmp/aii_nb_test_envs/art_VVA3P0ocZNA2-b603e68c357e/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb
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
TODO 6. Verify: (1) code_demo.ipynb contains GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-9/experiment-46/demo/mini_demo_data.json" exactly, (2) mini_demo_data.json exists, (3) uses GitHub URL pattern not just open('mini_demo_data.json').
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

### [3] ASSISTANT · 2026-10-26 14:21:52 UTC

```
I'll start by loading the required skills and looking at the workspace and the source artifact.
```

### [4] TOOL CALL — Skill · 2026-10-26 14:21:52 UTC

```
aii-colab
```

### [5] TOOL CALL — Skill · 2026-10-26 14:21:52 UTC

```
aii-long-running-tasks
```

### [6] TOOL RESULT — Skill · 2026-10-26 14:21:52 UTC

```
{"success": true, "commandName": "aii-colab"}
```

### [7] TOOL RESULT — Skill · 2026-10-26 14:21:52 UTC

```
{"success": true, "commandName": "aii-long-running-tasks"}
```

### [8] TOOL CALL — Bash · 2026-10-26 14:21:52 UTC

```
List workspace and source artifact directory:
pwd && ls -la && ls -la .aii 2>/dev/null; echo "---"; ls -la /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46 2>&1 | head -50
```

### [9] TOOL RESULT — Bash · 2026-10-26 14:21:52 UTC

```
{"stdout": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2\ntotal 2078\ndrwxrwxrwx 3 aii-agent aii-agent 1003140 Oct 26 14:21 .\ndrwxrwxrwx 5 aii-agent aii-agent 1091031 Oct 26 14:20 ..\ndrwxrwxrwx 2 aii-agent aii-agent       1 Oct 26 14:20 .aii\n-rw-rw-rw- 1 aii-agent aii-agent      54 Oct 26 14:21 .aii_claude_session.json\n-rw-rw-rw- 1 aii-agent aii-agent   32104 Oct 26 14:21 .repl_agent.ptylog\ntotal 981\ndrwxrwxrwx 2 aii-agent aii-agent       1 Oct 26 14:20 .\ndrwxrwxrwx 3 aii-agent aii-agent 1003140 Oct 26 14:21 ..\n---\ntotal 26577\ndrwxrwxrwx 14 aii-agent aii-agent 3000131 Oct 23 18:02 .\ndrwxrwxrwx  9 aii-agent aii-agent 3000187 Oct 23 11:57 ..\ndrwxrwxrwx  2 aii-agent aii-agent   85700 Oct 23 15:27 .aii\n-rw-rw-rw-  1 aii-agent aii-agent      54 Oct 23 13:30 .aii_claude_session.json\n-rw-rw-rw-  1 aii-agent aii-agent    1311 Oct 23 13:25 .aii_cost_ledger.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent    7622 Oct 23 15:27 .aii_worker_result.json\n-rw-rw-rw-  1 aii-agent aii-agent  557637 Oct 23 15:27 .repl_agent.ptylog\n-rw-rw-rw-  1 aii-agent aii-agent    2815 Oct 23 15:21 .terminal_claude_agent_struct_out.json\n-rw-rw-rw-  1 aii-agent aii-agent   17152 Oct 23 15:21 README.md\n-rw-rw-rw-  1 aii-agent aii-agent    5227 Oct 23 13:51 README_static.md\ndrwxrwxrwx  2 aii-agent aii-agent 1001230 Oct 23 12:47 audit\ndrwxrwxrwx  3 aii-agent aii-agent 3000120 Oct 23 09:40 cache\n-rw-rw-rw-  1 aii-agent aii-agent    1741 Oct 23 15:01 commitments.log\ndrwxrwxrwx 15 aii-agent aii-agent 2008428 Oct 23 15:20 data\ndrwxrwxrwx  3 aii-agent aii-agent 2000827 Oct 23 15:18 figures\n-rw-rw-rw-  1 aii-agent aii-agent 1700254 Oct 23 15:21 full_method_out.json\ndrwxrwxrwx  7 aii-agent aii-agent 2001486 Oct 23 10:24 inputs\ndrwxrwxrwx  2 aii-agent aii-agent 1033897 Oct 23 15:20 logs\n-rw-rw-rw-  1 aii-agent aii-agent    3855 Oct 23 10:20 method.py\n-rw-rw-rw-  1 aii-agent aii-agent 1583418 Oct 23 15:20 method_out.json\n-rw-rw-rw-  1 aii-agent aii-agent   35853 Oct 23 15:21 mini_method_out.json\ndrwxrwxrwx  2 aii-agent aii-agent 1002207 Oct 23 15:01 predictions\n-rw-rw-rw-  1 aii-agent aii-agent   25131 Oct 23 15:21 preview_method_out.json\n-rw-rw-rw-  1 aii-agent aii-agent    2550 Oct 23 13:24 pyproject.toml\n-rw-rw-rw-  1 aii-agent aii-agent    7274 Oct 23 14:23 reproducibility.md\n-rw-rw-rw-  1 aii-agent aii-agent    1363 Oct 23 13:24 requirements.lock.txt\ndrwxrwxrwx  3 aii-agent aii-agent 2000147 Oct 23 15:21 results\n-rwxrwxrwx  1 aii-agent aii-agent    1070 Oct 23 14:54 run_chain.sh\ndrwxrwxrwx  2 aii-agent aii-agent 1002815 Oct 23 15:15 scripts\ndrwxrwxrwx  3 aii-agent aii-agent 1054043 Oct 23 18:02 src\ndrwxrwxrwx  4 aii-agent aii-agent 1061190 Oct 23 10:24 vendor", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [10] ASSISTANT · 2026-10-26 14:21:58 UTC

```
Skills loaded. There is no todo-tracking tool in this session, so I'll track the six TODOs in order. Next is TODO 2: read the demo file and the preview data.
```

### [11] TOOL CALL — Bash · 2026-10-26 14:21:58 UTC

```
Show method.py, pyproject and run script:
SRC=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46; cat $SRC/method.py; echo "=== pyproject"; cat $SRC/pyproject.toml; echo "=== run_chain"; cat $SRC/run_chain.sh; echo "=== req lock"; cat $SRC/requirements.lock.txt
```

### [12] TOOL RESULT — Bash · 2026-10-26 14:21:58 UTC

```
{"stdout": "#!/usr/bin/env python3\n\"\"\"TP-G (iteration 9): Qwen3-32B's ten-algorithm grid manifold with and without the algorithms' names.\n\nOrchestrator: one sub-command per stage (`.venv/bin/python method.py <stage> [args]`). Stages, in run order:\n  inputs        Stage -1  copy prior-artifact inputs into inputs/ (+ SHA256SUMS), hardware record\n  commit0       Stage 0   predictions, gates and definitions, hash-committed before any state\n  mname [tag]   Stage 1   M-name states (iteration 8's 300 forced prompts) + reproduction gate (GPU)\n  cpu           Stage 2   probe grids, expansion tracer, behavioural RDM, lexical measures, descriptions,\n                          M-lex prompts and twins, M-code contexts; then COMMIT #1a\n  naming        Stage 3a  OpenRouter naming gate (Qwen3-32B names each description 20 times)\n  topups        Stage 3b  OpenRouter forced top-ups (Qwen3-32B programs)\n  pools         Stage 4   ACCEPT, scrub (G-scrub), program sets, placement sets; then COMMIT #1b\n  states [tag]  Stage 5   M-desc, M-lex, ban and M-code states (GPU)\n  blocks        Stage 6   label-only block selection; then COMMIT #2\n  analyse       Stages 7-10  geometry, verdicts, landing, bootstrap, robustness, lexical regression, RSA, placement\n  figures       Stage 11\n  outputs       Stage 12  points/placements rows, n4_verdict.json, method_out.json\n\"\"\"\n\nfrom __future__ import annotations\n\nimport os\nimport resource\nimport sys\nfrom pathlib import Path\n\nROOT = Path(__file__).resolve().parent\nsys.path.insert(0, str(ROOT / \"src\"))\nsys.path.insert(1, str(ROOT / \"vendor\" / \"exp9\"))\n\nfrom loguru import logger  # noqa: E402\n\nfrom common import setup_logging  # noqa: E402\n\nGPU_STAGES = {\"mname\", \"states\", \"smoke_gpu\"}\n\n\ndef _limits(stage: str) -> None:\n    if stage in GPU_STAGES:\n        import torch\n\n        if torch.cuda.is_available():\n            torch.cuda.set_per_process_memory_fraction(0.90, 0)\n        return\n    ram = int(float(os.environ.get(\"TPG_RAM_GB\", \"40\")) * 1024 ** 3)\n    resource.setrlimit(resource.RLIMIT_AS, (ram, ram))\n\n\n@logger.catch(reraise=True)\ndef main() -> None:\n    if len(sys.argv) < 2:\n        print(__doc__)\n        sys.exit(1)\n    stage, args = sys.argv[1], sys.argv[2:]\n    setup_logging(f\"stage_{stage}\")\n    _limits(stage)\n    logger.info(f\"=== stage {stage} {args} ===\")\n    if stage == \"inputs\":\n        import stage_setup\n        stage_setup.stage_inputs()\n    elif stage == \"hardware\":\n        import stage_setup\n        stage_setup.stage_hardware()\n    elif stage == \"commit0\":\n        import stage_setup\n        stage_setup.stage_commit0()\n    elif stage == \"mname\":\n        import stage_states\n        stage_states.stage_mname(args[0] if args else \"32b\", int(args[1]) if len(args) > 1 else 0)\n    elif stage == \"repro\":\n        import stage_states\n        stage_states.repro_check(args[0] if args else \"32b\")\n    elif stage == \"cpu\":\n        import stage_cpu\n        stage_cpu.stage_cpu(*args)\n    elif stage == \"naming\":\n        import stage_or\n        stage_or.stage_naming(*args)\n    elif stage == \"topups\":\n        import stage_or\n        stage_or.stage_topups(*args)\n    elif stage == \"pools\":\n        import stage_pools\n        stage_pools.stage_pools(*args)\n    elif stage == \"states\":\n        import stage_states\n        stage_states.stage_states(*args)\n    elif stage == \"blocks\":\n        import stage_analysis\n        stage_analysis.stage_blocks(*args)\n    elif stage == \"analyse\":\n        import stage_analysis\n        stage_analysis.stage_analyse(*args)\n    elif stage == \"figures\":\n        import stage_figures\n        stage_figures.stage_figures(*args)\n    elif stage == \"outputs\":\n        import stage_outputs\n        stage_outputs.stage_outputs(*args)\n    else:\n        raise SystemExit(f\"unknown stage {stage}\")\n    logger.info(f\"=== stage {stage} done ===\")\n\n\nif __name__ == \"__main__\":\n    main()\n=== pyproject\n[project]\nname = \"tpg-names-vs-mechanism-geometry\"\nversion = \"1.0.0\"\ndescription = \"Iteration 9 TP-G: Qwen3-32B (nf4) and Qwen3-8B (bf16) ten-algorithm grid manifolds rebuilt with names (M-name), name-free descriptions (M-desc), name-only lexical deltas (M-lex) and name-scrubbed programs (M-code); landing of the iteration-8 survivors, lexical regression, RSA against lexical/behavioural/surface RDMs, per-program placement.\"\nrequires-python = \"==3.12.*\"\n# Every package pinned to the exact version installed in .venv (`uv pip freeze --python .venv/bin/python`; the venv\n# has no pip of its own). Same list as requirements.lock.txt. Shared packages match the iteration-8 pins.\ndependencies = [\n    \"accelerate==1.15.0\",\n    \"aiohappyeyeballs==2.7.1\",\n    \"aiohttp==3.14.5\",\n    \"aiosignal==1.4.0\",\n    \"attrs==26.1.0\",\n    \"bitsandbytes==0.50.2\",\n    \"certifi==2026.10.19\",\n    \"charset-normalizer==3.5.2\",\n    \"cloudpickle==3.1.2\",\n    \"contourpy==1.4.0\",\n    \"cycler==0.12.1\",\n    \"filelock==4.2.4\",\n    \"fonttools==4.67.0\",\n    \"frozenlist==1.8.0\",\n    \"fsspec==2026.9.0\",\n    \"hf-xet==1.7.0\",\n    \"huggingface-hub==0.36.2\",\n    \"idna==3.20\",\n    \"jinja2==3.1.6\",\n    \"joblib==1.6.0\",\n    \"kiwisolver==1.5.1\",\n    \"loguru==0.7.3\",\n    \"markupsafe==3.0.4\",\n    \"matplotlib==3.11.2\",\n    \"mpmath==1.3.0\",\n    \"multidict==7.1.0\",\n    \"narwhals==2.27.1\",\n    \"networkx==3.7\",\n    \"numpy==2.2.6\",\n    \"nvidia-cublas-cu12==12.8.4.1\",\n    \"nvidia-cuda-cupti-cu12==12.8.90\",\n    \"nvidia-cuda-nvrtc-cu12==12.8.93\",\n    \"nvidia-cuda-runtime-cu12==12.8.90\",\n    \"nvidia-cudnn-cu12==9.10.2.21\",\n    \"nvidia-cufft-cu12==11.3.3.83\",\n    \"nvidia-cufile-cu12==1.13.1.3\",\n    \"nvidia-curand-cu12==10.3.9.90\",\n    \"nvidia-cusolver-cu12==11.7.3.90\",\n    \"nvidia-cusparse-cu12==12.5.8.93\",\n    \"nvidia-cusparselt-cu12==0.7.1\",\n    \"nvidia-nccl-cu12==2.27.3\",\n    \"nvidia-nvjitlink-cu12==12.8.93\",\n    \"nvidia-nvtx-cu12==12.8.90\",\n    \"packaging==26.3\",\n    \"pillow==13.0.0\",\n    \"propcache==0.5.4\",\n    \"psutil==7.2.2\",\n    \"pyparsing==3.3.3\",\n    \"python-dateutil==3.0.0\",\n    \"pyyaml==6.0.3\",\n    \"regex==2026.9.29\",\n    \"requests==2.34.2\",\n    \"safetensors==0.8.0\",\n    \"scikit-learn==1.9.1\",\n    \"scipy==1.18.1\",\n    \"setuptools==84.2.1\",\n    \"six==1.17.0\",\n    \"sympy==1.14.0\",\n    \"tenacity==9.2.1\",\n    \"threadpoolctl==3.7.0\",\n    \"tokenizers==0.22.2\",\n    \"torch==2.8.0\",\n    \"tqdm==4.70.1\",\n    \"transformers==4.57.6\",\n    \"triton==3.4.0\",\n    \"typing-extensions==4.16.0\",\n    \"tzdata==2026.5\",\n    \"urllib3==2.8.0\",\n    \"yarl==1.25.1\",\n    \"zss==1.2.0\",\n]\n=== run_chain\n#!/usr/bin/env bash\n# Runs the post-pool stages in order (each stage must succeed before the next starts).\n# Usage: ./run_chain.sh [first_stage_index]   (0 = 32B states, 1 = 8B states, 2 = blocks, 3 = analyse, 4 = figures,\n#                                              5 = outputs, 6 = audits)\nset -euo pipefail\ncd \"$(dirname \"$0\")\"\nPY=.venv/bin/python\nexport OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1\nstart=${1:-0}\nsteps=(\"$PY method.py states 32b mcode\"\n       \"$PY method.py states 8b mcode\"\n       \"$PY method.py blocks\"\n       \"$PY method.py analyse\"\n       \"$PY method.py figures\"\n       \"$PY method.py outputs\"\n       \"$PY audit/rederive.py\")\nfor i in \"${!steps[@]}\"; do\n  if [ \"$i\" -lt \"$start\" ]; then continue; fi\n  echo \"=== $(date -u +%H:%M:%S) step $i: ${steps[$i]}\"\n  if [ \"$i\" -ge 4 ]; then ${steps[$i]} > \"logs/chain_step_$i.out\" 2>&1 || echo \"step $i FAILED (continuing)\"; else ${steps[$i]} > \"logs/chain_step_$i.out\" 2>&1 || { echo \"step $i FAILED\"; exit 1; }; fi\ndone\necho \"=== $(date -u +%H:%M:%S) chain done\"\n=== req lock\naccelerate==1.15.0\naiohappyeyeballs==2.7.1\naiohttp==3.14.5\naiosignal==1.4.0\nattrs==26.1.0\nbitsandbytes==0.50.2\ncertifi==2026.10.19\ncharset-normalizer==3.5.2\ncloudpickle==3.1.2\ncontourpy==1.4.0\ncycler==0.12.1\nfilelock==4.2.4\nfonttools==4.67.0\nfrozenlist==1.8.0\nfsspec==2026.9.0\nhf-xet==1.7.0\nhuggingface-hub==0.36.2\nidna==3.20\njinja2==3.1.6\njoblib==1.6.0\nkiwisolver==1.5.1\nloguru==0.7.3\nmarkupsafe==3.0.4\nmatplotlib==3.11.2\nmpmath==1.3.0\nmultidict==7.1.0\nnarwhals==2.27.1\nnetworkx==3.7\nnumpy==2.2.6\nnvidia-cublas-cu12==12.8.4.1\nnvidia-cuda-cupti-cu12==12.8.90\nnvidia-cuda-nvrtc-cu12==12.8.93\nnvidia-cuda-runtime-cu12==12.8.90\nnvidia-cudnn-cu12==9.10.2.21\nnvidia-cufft-cu12==11.3.3.83\nnvidia-cufile-cu12==1.13.1.3\nnvidia-curand-cu12==10.3.9.90\nnvidia-cusolver-cu12==11.7.3.90\nnvidia-cusparse-cu12==12.5.8.93\nnvidia-cusparselt-cu12==0.7.1\nnvidia-nccl-cu12==2.27.3\nnvidia-nvjitlink-cu12==12.8.93\nnvidia-nvtx-cu12==12.8.90\npackaging==26.3\npillow==13.0.0\npropcache==0.5.4\npsutil==7.2.2\npyparsing==3.3.3\npython-dateutil==3.0.0\npyyaml==6.0.3\nregex==2026.9.29\nrequests==2.34.2\nsafetensors==0.8.0\nscikit-learn==1.9.1\nscipy==1.18.1\nsetuptools==84.2.1\nsix==1.17.0\nsympy==1.14.0\ntenacity==9.2.1\nthreadpoolctl==3.7.0\ntokenizers==0.22.2\ntorch==2.8.0\ntqdm==4.70.1\ntransformers==4.57.6\ntriton==3.4.0\ntyping-extensions==4.16.0\ntzdata==2026.5\nurllib3==2.8.0\nyarl==1.25.1\nzss==1.2.0", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [13] TOOL CALL — Bash · 2026-10-26 14:21:58 UTC

```
List source tree, results and figures:
SRC=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46; find $SRC/src $SRC/scripts $SRC/results $SRC/figures $SRC/predictions $SRC/audit -maxdepth 3 | head -150; echo; du -sh $SRC/src $SRC/scripts $SRC/results $SRC/figures $SRC/data $SRC/cache $SRC/inputs $SRC/vendor 2>/dev/null
```

### [14] TOOL RESULT — Bash · 2026-10-26 14:21:58 UTC

```
{"stdout": "/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/scripts\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/predictions\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/audit\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/audit/audit_states.py\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/audit/rederive.py\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/lexical_alias_level_32b.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/lexical_alias_level_32b.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/behavioural_mds.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/behavioural_mds.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/rdms.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/rdms.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/isomap_8b_mcode_PRIMARY_R1.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/isomap_8b_mcode_PRIMARY_R1.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/mds_8b_mcode_PRIMARY_R1.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/mds_8b_mcode_PRIMARY_R1.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/pca_8b_mcode_PRIMARY_R1.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/pca_8b_mcode_PRIMARY_R1.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/isomap_8b_mdesc.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/isomap_8b_mdesc.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/mds_8b_mdesc.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/mds_8b_mdesc.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/pca_8b_mdesc.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/pca_8b_mdesc.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/isomap_8b_mname.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/isomap_8b_mname.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/mds_8b_mname.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/mds_8b_mname.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/pca_8b_mname.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/pca_8b_mname.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/isomap_32b_mcode_M32_R1.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/isomap_32b_mcode_M32_R1.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/mds_32b_mcode_M32_R1.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/mds_32b_mcode_M32_R1.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/pca_32b_mcode_M32_R1.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/pca_32b_mcode_M32_R1.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/isomap_32b_mcode_PRIMARY_R2.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/isomap_32b_mcode_PRIMARY_R2.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/mds_32b_mcode_PRIMARY_R2.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/mds_32b_mcode_PRIMARY_R2.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/pca_32b_mcode_PRIMARY_R2.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/pca_32b_mcode_PRIMARY_R2.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/isomap_32b_mcode_PRIMARY_R1.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/isomap_32b_mcode_PRIMARY_R1.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/mds_32b_mcode_PRIMARY_R1.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/mds_32b_mcode_PRIMARY_R1.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/pca_32b_mcode_PRIMARY_R1.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/pca_32b_mcode_PRIMARY_R1.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/isomap_32b_mlex.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/isomap_32b_mlex.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/mds_32b_mlex.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/mds_32b_mlex.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/pca_32b_mlex.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/pca_32b_mlex.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/isomap_32b_mdesc.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/isomap_32b_mdesc.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/mds_32b_mdesc.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/mds_32b_mdesc.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/pca_32b_mdesc.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/pca_32b_mdesc.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/class_table.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/class_table.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/isomap_32b_mname.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/isomap_32b_mname.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/mds_32b_mname.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/mds_32b_mname.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/pca_32b_mname.png\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/pca_32b_mname.pdf\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures/coords\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/audit_states.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/tests.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/rederive.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/n4_verdict.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/placement.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/rsa.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/surface_rdm.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/geometry_all.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/geometry_8b_mcode_PRIMARY_R1.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/lexical_regression.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/geometry_8b_mdesc.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/geometry_8b_mname.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/geometry_32b_mcode_M32_R1.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/geometry_32b_mcode_PRIMARY_R2.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/geometry_32b_mcode_PRIMARY_R1.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/geometry_32b_mlex.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/geometry_32b_mdesc.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/geometry_32b_mname.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/deviations.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/states_mcode_8b.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/load_8b_mcode.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/states_mcode_32b.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/load_32b_mcode.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/acceptance.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/g_scrub.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/states_mdesc_8b.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/load_8b_mdesc.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/states_mdesc_32b.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/load_32b_mdesc_mcode.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/positioning.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/positioning_raw\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/repro_mname_8b.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/states_mlex_8b.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/load_8b_mname_mlex_ban.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/topups.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/costs.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/naming_gate.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/states_mlex_32b.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/.cost.lock\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/openrouter_key_checks.jsonl\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/naming_scorer_test.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/load_32b_mlex_ban.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/lexical.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/behavioural_distance.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/g_tracer.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/repro_mname_32b.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/.dev.lock\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/states_mname_32b.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/timing.jsonl\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results/inputs_status.json\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/scripts/post2.sh\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/scripts/post_analysis.sh\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/scripts/make_tests.py\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/scripts/finalize.sh\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/scripts/make_struct.py\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/scripts/make_readme.py\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/scripts/test_figures.py\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/scripts/wait_then_chain.sh\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/scripts/test_analysis.py\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/scripts/warm_cache.py\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/scripts/download_models.py\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/stage_analysis.py\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/stage_outputs.py\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/stage_figures.py\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/stage_mcode.py\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/stage_pools.py\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/stage_or.py\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/stage_states.py\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/programs.py\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/stage_cpu.py\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/expansion.py\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/expansion_child.py\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/judge_tp.py\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/sample_or.py\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/label_tp.py\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/landing.py\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/geometry.py\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/states.py\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/prompts_tp.py\n\n2.6M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src\n1011K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/scripts\n4.4M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/results\n13M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/figures\n107M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/data\n1.3G\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache\n40M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/inputs\n7.5M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/vendor", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [15] ASSISTANT · 2026-10-26 14:22:08 UTC

```
`method.py` is only a stage dispatcher; the real logic is in `src/`. I'll read the README, the reproducibility notes and the preview output to see the data shapes.
```

### [16] TOOL CALL — Bash · 2026-10-26 14:22:08 UTC

```
Read the artifact README:
SRC=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46; cat $SRC/README.md
```

### [17] TOOL RESULT — Bash · 2026-10-26 14:22:08 UTC

````
{"stdout": "# Mapping the ten grid algorithms with and without their names (TP-G, iteration 9)\n\nDoes Qwen3-32B's internal map of ten path-search algorithms reflect what the algorithms *do*, or only their *names*? Iteration 8 found that the algorithm Qwen3-32B writes when its top five are banned (unit-weight Dijkstra) sits OPPOSITE the banned five on a manifold built from prompts that *name* each algorithm. This artifact rebuilds that manifold four ways, holding the model, readout, block rule, k and landing code fixed: **M-name** (iteration 8's 300 alias prompts, reproduced), **M-desc** (name-free mechanism descriptions that Qwen3-32B can name), **M-lex** (name-only sentences minus token-length-matched neutral-noun twins) and **M-code** (name-scrubbed, verified programs, teacher-forced). All geometry is correlational: The geometry is correlational: it describes where representations and survivors sit, not whether the model uses this geometry to choose an algorithm (iteration 7's in-manifold pushes moved 0/300).\n\n**Named outcome (pre-registered rule): MIXED.** M-code class of unit Dijkstra at k 15: EDGE; M-desc: OPPOSITE; M-code source robustness: ROBUST; k-sensitive: False.\n\n## Headline results\n\n### 1. M-name reproduces iteration 8's classes, but not its committed rank gate\n\n- Per-prompt cosine with iteration 8's cached states: >= 0.99998 at every block (17-47).\n- g of the five non-banned algorithms: max |difference| 0.030; classes identical ({'bibfs': 'EDGE', 'biastar': 'EDGE', 'idastar': 'MIDDLE', 'jps': 'OPPOSITE', 'dijkstra_unit': 'OPPOSITE'}).\n- Committed gate (Spearman of the 45 class-geodesic entries, k 15, block 31) = 0.894 < 0.95: **G-repro fails**; at k 10 the same statistic is 0.997. Near-tied kNN edges among the banned clusters flip at k 15 (float16 storage was ruled out: 0.9999). Fallback F1 applies: the new states are used throughout and iteration 8's verdict (OPPOSITE) is reported beside.\n- Qwen3-8B bf16 M-name against iteration 8's cached states: Spearman 0.994 (k 15), unit Dijkstra OPPOSITE at every k.\n\n### 2. Verdict table (where the 15 unit-Dijkstra survivors land)\n\n| Manifold (model) | L* | N | non-banned used | class(uDij) k10 | class(uDij) k15 | rank (1 = nearest) | g/median | nearest banned | landing verdict k15 | bootstrap P(EDGE) | split-half (S-B) |\n|---|---|---|---|---|---|---|---|---|---|---|---|\n| 32b|mname | 31 | 300 | bibfs, biastar, idastar, jps, dijkstra_unit | OPPOSITE | OPPOSITE | 5 | 1.63 | astar | OPPOSITE | 0.00 | 0.99 |\n| 32b|mdesc | 31 | 260 | bibfs, biastar, idastar, dijkstra_unit | OPPOSITE | OPPOSITE | 3 | 1.08 | astar | OPPOSITE | 0.01 | 0.99 |\n| 32b|mlex | 31 | 300 | bibfs, biastar, idastar, jps, dijkstra_unit | OPPOSITE | OPPOSITE | 4 | 1.20 | astar | OPPOSITE | 0.00 | 0.99 |\n| 32b|mcode_PRIMARY_R1 | 33 | 117 | idastar, dijkstra_unit | EDGE | EDGE | 1 | 0.67 | gbfs | EDGE | 1.00 | 0.99 |\n| 32b|mcode_PRIMARY_R2 | 21 | 117 | idastar, dijkstra_unit | EDGE | EDGE | 1 | 0.32 | astar | EDGE | 1.00 | 0.91 |\n| 32b|mcode_M32_R1 | 31 | 113 | idastar, dijkstra_unit | EDGE | EDGE | 1 | 0.79 | gbfs | EDGE | 1.00 | 0.99 |\n| 8b|mname | 17 | 300 | bibfs, biastar, idastar, jps, dijkstra_unit | OPPOSITE | OPPOSITE | 4 | 1.17 | astar | OPPOSITE | 0.01 | 0.98 |\n| 8b|mdesc | 17 | 260 | bibfs, biastar, idastar, dijkstra_unit | OPPOSITE | OPPOSITE | 3 | 1.01 | astar | OPPOSITE | 0.49 | 0.98 |\n| 8b|mcode_PRIMARY_R1 | 17 | 117 | idastar, dijkstra_unit | EDGE | EDGE | 1 | 0.63 | gbfs | EDGE | 1.00 | 0.98 |\n\nClasses use iteration 8's relative rule (EDGE below the median of the non-banned g values, OPPOSITE above). A class over fewer than five non-banned algorithms is reported but weaker (see M-desc and M-code exclusions below).\n\n### 3. Names drive the alias-level geometry (P4)\n\n- 32b|mname: Spearman(g_alias, L1) = -0.74 (k 10, permutation p 0.0010) and -0.65 (k 15, p 0.0052); partial given alias length -0.67; within-algorithm exact p (L2, 7,776 permutations) 0.157. P4 (<= -0.6 at both k): True.\n- 8b|mname: Spearman(g_alias, L1) = -0.70 (k 10, permutation p 0.0026) and -0.78 (k 15, p 0.0005); partial given alias length -0.78; within-algorithm exact p (L2, 7,776 permutations) 0.551. P4 (<= -0.6 at both k): True.\n- 32b|mlex: Spearman(g_alias, L1) = -0.59 (k 10, permutation p 0.0111) and -0.65 (k 15, p 0.0054); partial given alias length -0.75; within-algorithm exact p (L2, 7,776 permutations) 0.326. P4 (<= -0.6 at both k): False.\n\n### 4. RSA against model RDMs (exact label-permutation Mantel p)\n\n| Neural RDM | R_lex | R_beh | R_surface | R_len | noise ceiling (upper) |\n|---|---|---|---|---|---|\n| 32b|mname (10 classes) | 0.46 (p 0.003) | 0.24 (p 0.091) | 0.20 (p 0.128) | 0.07 (p 0.297) | 1.00 |\n| 32b|mdesc (9 classes) | 0.57 (p 0.000) | 0.12 (p 0.252) | 0.02 (p 0.463) | 0.01 (p 0.426) | 1.00 |\n| 32b|mlex (10 classes) | 0.47 (p 0.001) | 0.29 (p 0.034) | -0.13 (p 0.785) | 0.33 (p 0.027) | 0.99 |\n| 32b|mcode_PRIMARY_R1 (6 classes) | 0.29 (p 0.164) | 0.64 (p 0.018) | 0.67 (p 0.010) | 0.78 (p 0.007) | 1.00 |\n| 32b|mcode_PRIMARY_R2 (6 classes) | -0.01 (p 0.451) | 0.59 (p 0.050) | 0.66 (p 0.039) | 0.49 (p 0.081) | 0.96 |\n| 32b|mcode_M32_R1 (6 classes) | 0.10 (p 0.372) | 0.73 (p 0.008) | 0.70 (p 0.010) | 0.77 (p 0.007) | 1.00 |\n| 8b|mname (10 classes) | 0.48 (p 0.002) | 0.27 (p 0.071) | -0.12 (p 0.715) | 0.28 (p 0.058) | 0.99 |\n| 8b|mdesc (9 classes) | 0.25 (p 0.079) | 0.25 (p 0.087) | 0.33 (p 0.040) | 0.46 (p 0.008) | 0.99 |\n| 8b|mcode_PRIMARY_R1 (6 classes) | 0.10 (p 0.360) | 0.88 (p 0.001) | 0.87 (p 0.001) | 0.88 (p 0.001) | 0.99 |\n\nName evocation: a probe trained on M-name (block 31) classifies M-desc at balanced accuracy 0.69 (chance 0.11) and M-code R1 at 0.17.\n\n### 5. Behavioural anchor (P6) and stimulus gates\n\n- Behavioural RDM from expansion-order traces of the 15 T1 references on 40 probe grids: d_beh to BFS {'bibfs': 0.72, 'biastar': 0.86, 'idastar': 1.12, 'jps': 1.06, 'dijkstra_unit': 0.31}; unit Dijkstra nearest BFS: True (true by construction for the order term). Behavioural classes: {'bibfs': 'OPPOSITE', 'biastar': 'EDGE', 'idastar': 'OPPOSITE', 'jps': 'MIDDLE', 'dijkstra_unit': 'EDGE'}. G-tracer 13/15 (biA* shows no second frontier because its forward side always wins ties on these grids; IDA* rarely restarts because the Manhattan bound is tight).\n- Naming gate (Qwen3-32B, 20 namings per description, >= 16/20): passing descriptions per algorithm {'bfs': 3, 'dfs': 3, 'bibfs': 2, 'iddfs': 3, 'astar': 3, 'gbfs': 3, 'dijkstra_unit': 3, 'idastar': 3, 'jps': 0, 'biastar': 3}; excluded [['bibfs|2', 0.15], ['jps|0', 0.7], ['jps|1', 0.6], ['jps|2', 0.45]]. **JPS has no nameable name-free description**, so M-desc classes run over the other four non-banned algorithms.\n- M-code program sets (PRIMARY / Qwen3-32B-only M32 / Qwen3-8B-only M8): {'PRIMARY': {'bfs': 20, 'dfs': 20, 'bibfs': 8, 'iddfs': 2, 'astar': 20, 'gbfs': 20, 'dijkstra_unit': 20, 'idastar': 17, 'jps': 0, 'biastar': 2}, 'M32': {'bfs': 20, 'dfs': 20, 'bibfs': 2, 'iddfs': 0, 'astar': 20, 'gbfs': 20, 'dijkstra_unit': 20, 'idastar': 13, 'jps': 0, 'biastar': 1}, 'M8': {'bfs': 20, 'dfs': 17, 'bibfs': 4, 'iddfs': 0, 'astar': 11, 'gbfs': 20, 'dijkstra_unit': 9, 'idastar': 3, 'jps': 0, 'biastar': 0}}; algorithms below the 10-program floor are excluded: {'PRIMARY': ['bibfs', 'iddfs', 'jps', 'biastar'], 'M32': ['bibfs', 'iddfs', 'jps', 'biastar'], 'M8': ['bibfs', 'iddfs', 'dijkstra_unit', 'idastar', 'jps', 'biastar']}.\n- G-scrub (name scrubbing preserves AST modulo names, expansion sequences, labels and suite outcomes): 449/470; planted 'def bfs' test clean=True.\n\n### 6. Per-program placement on M-code\n\n- 32b|mcode_PRIMARY_R1 (block 33, k 15): leave-one-out placement accuracy 0.85 (gate 0.70: True); unit-Dijkstra survivors EDGE 15/15, nearest-algorithm counts {gbfs: 2, dijkstra_unit: 13}; BASE programs placed on their own label: 1.00.\n- 32b|mcode_PRIMARY_R2 (block 21, k 15): leave-one-out placement accuracy 0.67 (gate 0.70: False); unit-Dijkstra survivors EDGE 15/15, nearest-algorithm counts {gbfs: 1, dijkstra_unit: 14}; BASE programs placed on their own label: 0.98.\n- 32b|mcode_M32_R1 (block 31, k 15): leave-one-out placement accuracy 0.89 (gate 0.70: True); unit-Dijkstra survivors EDGE 10/15, nearest-algorithm counts {astar: 1, dijkstra_unit: 14}; BASE programs placed on their own label: 1.00.\n- 8b|mcode_PRIMARY_R1 (block 17, k 15): leave-one-out placement accuracy 0.83 (gate 0.70: True); unit-Dijkstra survivors EDGE 15/15, nearest-algorithm counts {gbfs: 3, dijkstra_unit: 12}; BASE programs placed on their own label: 0.92.\n\n### 7. Pre-registered predictions\n\n- P1: pass = False\n- P2: pass = False\n- P3: pass = True\n- P4: pass = True\n- P5: pass = descriptive\n- P6: pass = True\n- P7: pass = descriptive\n- P8: pass = True\n\n### 8. Independent re-derivation\n\n- `audit/rederive.py` (standard library only, from the JSON class matrices and alias rows): 0 mismatches; placebos {'random_survivor_labels_share_NEITHER': 0.9333333333333333, 'shuffled_labels_share_udij_OPPOSITE': 0.366, 'permuted_L1_mean_rho': -0.009264500449452597, 'permuted_L1_share_as_extreme_as_observed': 0.006}.\n- `audit/audit_states.py` (sklearn kNN + networkx Dijkstra on the raw state files, no project geometry code): mismatches []; 32b|mname: classes equal True, max |dg| 3.73e-13, placebo share 0.40; 32b|mdesc: classes equal True, max |dg| 1.53e-13, placebo share 0.65; 32b|mlex: classes equal True, max |dg| 1.78e-15, placebo share 0.20; 32b|mcode_PRIMARY_R1: classes equal True, max |dg| 1.39e-13, placebo share 0.45\n\n## Cost\n\nOpenRouter: USD 0.094 for 1440 calls ({'naming_gate': 0.008386, 'topups': 0.085323}); cap 0.40.\n\n## Deviations (results/deviations.json)\n\n- **F1-repro**: M-name reproduction rho=0.894 (0.85-0.95: proceed with new states)\n- **D-desc-checks**: descriptions outside the checks: [('bibfs', 'D3', 19, None)]\n- **D-accept-B**: M-code sets use tier-B acceptance (mechanism labels + committed AST rules + trace check + valid paths on >= 38/40 probe grids) instead of the two hidden suites, for every source and algorithm alike: under tier A (committed ACCEPT) 4 of 5 non-banned classes have < 10 programs, mostly IDDFS/IDA*-style timeouts on the 30x30 hidden cases; tier-A counts are reported in results/acceptance.json\n- **F9-S1-bibfs**: 19/40 labeller disagreements for S1 bibfs (excluded; no manual adjudication within the time box)\n- **F9-S1-dijkstra_unit**: 13/40 labeller disagreements for S1 dijkstra_unit (excluded; no manual adjudication within the time box)\n- **F9-S1-idastar**: 33/50 labeller disagreements for S1 idastar (excluded; no manual adjudication within the time box)\n- **F9-S1-jps**: 25/50 labeller disagreements for S1 jps (excluded; no manual adjudication within the time box)\n- **F9-S1-biastar**: 36/50 labeller disagreements for S1 biastar (excluded; no manual adjudication within the time box)\n- **F9-S2-bibfs**: 36/60 labeller disagreements for S2 bibfs (excluded; no manual adjudication within the time box)\n- **F9-S2-idastar**: 32/60 labeller disagreements for S2 idastar (excluded; no manual adjudication within the time box)\n- **F9-S2-jps**: 36/60 labeller disagreements for S2 jps (excluded; no manual adjudication within the time box)\n- **F9-S2-biastar**: 44/60 labeller disagreements for S2 biastar (excluded; no manual adjudication within the time box)\n- **D-gscrub-fix**: G-scrub re-run before any M-code state: the first run required tier-B programs to pass the hidden suites after scrubbing (they were never required to pass them); the check is now 'suites outcome unchanged' (placement SURV/BASE still must pass); the code-span check counts boundary-straddling tokens; commit COMMIT1b-r1\n- **F10-time**: analysis restricted to the 32B manifolds M-name, M-desc, M-lex, M-code PRIMARY R1/R2 and the Qwen3-32B-only M-code frame, and to M-name, M-desc, M-code R1 on Qwen3-8B; dropped for time: M8 frame, R1g and R3 readouts, Qwen3-8B M-lex (their states are kept in cache/states)\n\n## How it was run\n\nEvery stage is `.venv/bin/python method.py <stage> [args]`; logs go to `logs/`, timings to `results/timing.jsonl`,\nOpenRouter spend to `results/costs.json`. Stages in run order:\n\n| Stage | Command | What it does |\n|---|---|---|\n| -1 | `inputs` | Copies the prior-artifact inputs into `inputs/` (+ `inputs/SHA256SUMS`), vendors the harness and labeller, writes `predictions/hardware.json` |\n| 0 | `commit0` | Predictions P1-P8, gates, definitions, named outcomes; hash-committed before any state (`commitments.log`) |\n| 1 | `mname 32b` | Qwen3-32B nf4 S-mean states of iteration 8's 300 forced prompts + the reproduction gate |\n| 2 | `cpu` | 40 probe grids, expansion tracer on the 15 T1 references (G-tracer), behavioural RDM, lexical measures, descriptions v0, M-lex prompts with token-matched neutral twins, M-code contexts; COMMIT #1a |\n| 3a | `naming` | Qwen3-32B (OpenRouter, DeepInfra fp8, thinking off) names each description 20 times; <= 2 rewrites |\n| 3b | `topups` | 600 forced Qwen3-32B programs (60 per algorithm) |\n| 4 | `pools` | ACCEPT (tier A committed, tier B used), scrub + G-scrub, M-code sets PRIMARY / M32 / M8, placement sets SURV / BASE / DISOBEY, M-desc prompts; COMMIT #1b |\n| 5 | `states 32b mlex ban`, `states 8b mname mlex ban`, `states 32b mdesc mcode`, `states 8b mdesc mcode` | S-mean and code-token states |\n| 6 | `blocks` | Label-only block selection (iteration 8's layer rule) for every model x manifold; COMMIT #2 |\n| 7-10 | `analyse` | Geometry, verdicts, landing, bootstrap, robustness grid, crossnobis / z-scored sensitivities, frozen geodesics, lexical regression, exact-permutation RSA, name evocation, out-of-sample placement |\n| 11 | `figures` | PCA / MDS / Isomap figures in activation coordinates, class table, RDM heatmaps, behavioural MDS |\n| 12 | `outputs` | `data/points.jsonl`, `data/placements.jsonl`, `results/n4_verdict.json`, `method_out.json` |\n| audit | `audit/rederive.py`, `audit/audit_states.py` | Independent re-derivations (stdlib-only from JSON; independent kNN/Dijkstra from raw states) with placebos |\n\n`run_chain.sh` runs stages 5 (mdesc/mcode) to the audit unattended.\n\n## Layout\n\n| Path | What it is |\n|---|---|\n| `method.py` | Orchestrator, one sub-command per stage |\n| `src/common.py`, `src/prompts_tp.py`, `src/states.py`, `src/geometry.py`, `src/landing.py`, `src/label_tp.py`, `src/sample_or.py`, `src/judge_tp.py` | Iteration 8's modules (art_R-HSmXq2t97f), byte-identical copies, imported unchanged |\n| `src/e44/` | Unedited archive of iteration 8's whole `src/` |\n| `src/tpg.py` | This artifact's frozen constants (banned split, model pins, blocks, k, budgets, gates) |\n| `src/stage_setup.py` | Stage -1 and commit #0 |\n| `src/stage_states.py`, `src/stage_mcode.py` | State extraction (S-mean families; M-code readouts R1 / R1g / R2 / R3) |\n| `src/stage_cpu.py`, `src/expansion.py`, `src/expansion_child.py` | Probe grids, expansion tracer (child runs sandboxed, stdlib only), behavioural RDM, lexical measures, descriptions, M-lex twins, M-code contexts |\n| `src/stage_or.py` | OpenRouter naming gate and top-ups (pinned provider, cost ledger, 403 stop) |\n| `src/programs.py`, `src/stage_pools.py` | ACCEPT, scrubber, G-scrub, program and placement sets |\n| `src/stage_analysis.py` | Block selection, geometry, landing, bootstrap, robustness, lexical regression, RSA, placement |\n| `src/stage_figures.py`, `src/stage_outputs.py` | Figures and outputs |\n| `audit/` | Independent re-derivations |\n| `predictions/commit{0,1a,1b,2}.json`, `commitments.log` | Pre-registrations and their sha256 hash chain |\n| `inputs/` | Prior-artifact inputs copied at Stage -1 (+ `SHA256SUMS`) |\n| `vendor/exp9/`, `vendor/exp2/` | Iteration-2 harness, hidden suites, references and labeller (via iteration 8) |\n| `data/` | Probe grids, descriptions, naming calls, top-ups, program sets, M-lex prompts, points and placements rows, sandbox cache |\n| `results/` | Every analysis JSON |\n| `figures/` | PDF + PNG figures; `figures/coords/` holds the 2-D coordinates they were drawn from |\n| `cache/states/` | Activation states and frozen geodesic graphs. **Kept on the run's storage volume, not in the published repository** (files of 100 MB or more are not published; the whole directory is excluded from upload) |\n\n## Restoring removed files\n\nThe manifest (`.aii/manifest.yaml`) marks three things for deletion after the round; each is restorable:\n\n```bash\n# .venv/ (regenerable)\nuv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r requirements.lock.txt\n# inputs/e44/states/ (regenerable: copies of the iteration-8 states; needs the art_R-HSmXq2t97f artifact folder,\n# located by the TPG_E44 environment variable)\n.venv/bin/python method.py inputs\n# __pycache__/ (regenerable): created on import\n```\n\nModel weights are not stored in this folder. They are downloaded into the Hugging Face cache by\n`.venv/bin/python scripts/download_models.py` (`unsloth/Qwen3-32B-bnb-4bit@7f721e74a6a8cc9ee352f7e49303a2c1705f9083`,\n`Qwen/Qwen3-8B@b968826d9c46dd6066d109eabc6255188de91218`).\n`cache/states/` is kept on the run volume; to rebuild it from scratch run the `mname`, `states` and `analyse` stages\n(about 30 GPU-minutes on one RTX 5090).", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
````

### [18] TOOL CALL — Bash · 2026-10-26 14:22:08 UTC

```
Read reproducibility notes and static README:
SRC=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46; cat $SRC/reproducibility.md; echo "=== README_static"; cat $SRC/README_static.md
```

### [19] TOOL RESULT — Bash · 2026-10-26 14:22:08 UTC

````
{"stdout": "# Reproducibility: mapping the ten grid algorithms with and without their names (TP-G, iteration 9)\n\nThis file describes what was **actually run**, in order, on the machine that produced the results. Every path is\nrelative to this artifact's folder.\n\n## 1. Getting the artifact\n\nThis workspace is published as one folder of the run's public GitHub repository:\n\n```bash\ngit clone <repository-url>\ncd <repository>/<this-artifact-folder>          # the folder that contains method.py and this file\n```\n\nThe folder contains everything the analysis reads except the activation-state files (`cache/states/`, about 0.5 GB),\nwhich stay on the run's storage volume and are excluded from the repository; they are rebuilt by the `mname`,\n`states` and `analyse` stages (section 4). The run's `user_uploads` folder was empty; no user-uploaded input is used.\n\nPrior artifacts are read **only** by Stage -1 (`method.py inputs`), which copies them into `inputs/` and `vendor/`\nwith `inputs/SHA256SUMS`. Their locations are environment variables with sibling-folder defaults in `src/tpg.py`:\n`TPG_E44` (art_R-HSmXq2t97f, iteration 8), `TPG_EXP9` (art_IVZc3TWCeE9f, iteration 2: forced programs, harness,\nreferences), `TPG_EXP2` (art_D6Z0Snf09sFL: 41-case suite), `TPG_EXP8` (art_8_ULPE8jJQc_: twin frames) and\n`TPG_DSET` (art_j3Rm_lr2nzR6, the declared dependency: 718 neutral nouns). Every later stage reads `inputs/` and\n`vendor/` only, so a clone can rerun every stage after Stage -1 without the prior artifacts.\n\n## 2. System, Python and libraries\n\n| Item | What was used |\n|---|---|\n| OS | Debian GNU/Linux 12 container on Linux 6.8 (Ubuntu 22.04/24.04 works the same way) |\n| GPU | 1x NVIDIA GeForce RTX 5090, 32 GB VRAM (driver 595.91.07, CUDA 12.8 wheels) |\n| CPU / RAM | 14 vCPU (cgroup quota, AMD Ryzen 9 9950X), 85 GB RAM (cgroup limit) |\n| Python | CPython 3.12.14; the sandboxes run candidates with `/usr/local/bin/python3.12 -I -S` (override: `SANDBOX_PYTHON`) |\n| Package manager | uv (the venv has no pip) |\n| Libraries | 70 packages pinned in `pyproject.toml` and `requirements.lock.txt` (identical lists): torch 2.8.0, transformers 4.57.6, bitsandbytes 0.50.2, accelerate 1.15.0, scikit-learn 1.9.1, scipy 1.18.1, numpy 2.2.6, networkx 3.7, matplotlib 3.11.2, aiohttp 3.14.5, loguru 0.7.3 - the same versions as iteration 8 for every shared package (`predictions/hardware.json -> matches_e44_pins`) |\n\n```bash\ncurl -LsSf https://astral.sh/uv/install.sh | sh\nuv venv .venv --python=3.12\nuv pip install --python .venv/bin/python -r requirements.lock.txt\n```\n\n## 3. Downloads, environment variables and keys (names only)\n\nModel weights (Hugging Face Hub, pinned revisions; `scripts/download_models.py` downloads both into the HF cache):\n\n| Repo | Revision | Used for |\n|---|---|---|\n| `unsloth/Qwen3-32B-bnb-4bit` | `7f721e74a6a8cc9ee352f7e49303a2c1705f9083` | all Qwen3-32B states (nf4, decoder truncated to 48 of 64 blocks; exact for blocks 0-47) |\n| `Qwen/Qwen3-8B` | `b968826d9c46dd6066d109eabc6255188de91218` | Qwen3-8B states (bf16, truncated to 29 of 36 blocks) |\n\nOpenRouter (only `qwen/qwen3-32b`, provider pinned to DeepInfra fp8 with `allow_fallbacks: false`, thinking off via\n`reasoning.enabled=false` plus the ` /no_think` soft switch, T 1.0, top_p 1.0):\n\n| Variable | Needed for |\n|---|---|\n| `OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY` | naming gate and top-ups (stages `naming`, `topups`) |\n| `HF_HOME` / `HF_HUB_CACHE` | optional: where the weights are cached |\n| `TPG_E44`, `TPG_EXP9`, `TPG_EXP2`, `TPG_EXP8`, `TPG_DSET` | only for Stage -1 (re-copying `inputs/`) |\n| `TPG_OR_CAP` | optional: artifact OpenRouter cap in USD (default 0.40) |\n| `TPG_WORKERS` | optional: process-pool size for the analysis (default 12) |\n\n## 4. Commands in the order they were run\n\nEach stage is `.venv/bin/python method.py <stage> [args]`. Seeds: probe grids and set selection 9009; bootstrap\nseeds 0..999 per k; landing nulls seed 0 (iteration 8's code). Approximate wall times on the hardware above.\n\n| # | Command | Time | Notes |\n|---|---|---|---|\n| 0 | `.venv/bin/python scripts/download_models.py` | 1 min | weights into the shared HF cache |\n| 1 | `method.py inputs` | 2 min | inputs + `inputs/SHA256SUMS` + `predictions/hardware.json` |\n| 2 | `method.py commit0` | <1 min | COMMIT0 |\n| 3 | `method.py mname 32b` | 11 min | 300 forced prompts, hook check, sdpa-vs-eager check, reproduction (`results/repro_mname_32b.json`) |\n| 4 | `method.py cpu` | 4 min | probe grids, tracer, behavioural RDM, lexical, descriptions, M-lex twins, contexts; COMMIT1a |\n| 5 | `method.py states 32b mlex ban` | 5 min | first attempt failed on a duplicated npz key (fixed, re-run) |\n| 6 | `method.py naming` | 9 min | 840 calls, USD 0.008 |\n| 7 | `method.py topups` | 34 min | 600 calls (2 waves of 30 per algorithm), USD 0.085 |\n| 8 | `method.py pools` | 29 min | first run: COMMIT1b |\n| 9 | `method.py states 8b mname mlex ban` | 4 min | + Qwen3-8B reproduction (`results/repro_mname_8b.json`) |\n| 10 | `method.py states 32b mdesc mcode` | 2 min | M-desc extracted; M-code stopped on a too-strict code-span check (no M-code state written) |\n| 11 | `method.py pools COMMIT1b-r1` | 21 min | G-scrub fix before any M-code state (deviation D-gscrub-fix); COMMIT1b-r1 |\n| 12 | `method.py states 8b mdesc` | 5 min | |\n| 13 | `./run_chain.sh 0` | see `logs/chain.out` | `states 32b mcode`, `states 8b mcode`, `blocks` (COMMIT2), `analyse`, `figures`, `outputs`, `audit/rederive.py` |\n| 14 | `.venv/bin/python audit/audit_states.py` | 3 min | state-level audit |\n| 15 | aii-json format script on `method_out.json`; `scripts/make_readme.py` | <1 min | full/mini/preview variants, README |\n\nThe hash chain is in `commitments.log` (COMMIT0, COMMIT1a, COMMIT1b, COMMIT1b-r1, COMMIT2); `common.verify_chain()`\nchecks it and `method_out.json -> metadata.commitments` records the result.\n\n## 5. What a reader should get\n\n| Output | Where |\n|---|---|\n| Named outcome, P1-P8 pass/fail, secondary statistics | `results/n4_verdict.json` |\n| Per-manifold geometry (PCA EVR, MDS stress-1, Isomap components, g, classes, landing nulls, bootstrap, robustness grid, crossnobis, z-scored) | `results/geometry_<model>_<manifold>.json`, `results/geometry_all.json` |\n| Reproduction of iteration 8 | `results/repro_mname_32b.json`, `results/repro_mname_8b.json` |\n| Lexical regression (alias level) | `results/lexical_regression.json` |\n| RSA with exact Mantel p, noise ceilings, name evocation | `results/rsa.json` |\n| Per-program placement | `results/placement.json`, `data/placements.jsonl` |\n| Behavioural RDM, G-tracer | `results/behavioural_distance.json`, `results/g_tracer.json` |\n| Naming gate, acceptance, scrub gate | `results/naming_gate.json`, `results/acceptance.json`, `results/g_scrub.json` |\n| Figures (activation coordinates) | `figures/pca_*`, `figures/mds_*`, `figures/isomap_*`, `figures/class_table.*`, `figures/rdms.*`, `figures/behavioural_mds.*`, `figures/lexical_alias_level_32b.*` |\n| Independent re-derivations | `results/rederive.json`, `results/audit_states.json` |\n| Pipeline output | `method_out.json` (+ `full_`/`mini_`/`preview_` variants) |\n\nThe README's headline section is generated from these files by `scripts/make_readme.py`; every number in it can be\ntraced to one of them.\n=== README_static\n## How it was run\n\nEvery stage is `.venv/bin/python method.py <stage> [args]`; logs go to `logs/`, timings to `results/timing.jsonl`,\nOpenRouter spend to `results/costs.json`. Stages in run order:\n\n| Stage | Command | What it does |\n|---|---|---|\n| -1 | `inputs` | Copies the prior-artifact inputs into `inputs/` (+ `inputs/SHA256SUMS`), vendors the harness and labeller, writes `predictions/hardware.json` |\n| 0 | `commit0` | Predictions P1-P8, gates, definitions, named outcomes; hash-committed before any state (`commitments.log`) |\n| 1 | `mname 32b` | Qwen3-32B nf4 S-mean states of iteration 8's 300 forced prompts + the reproduction gate |\n| 2 | `cpu` | 40 probe grids, expansion tracer on the 15 T1 references (G-tracer), behavioural RDM, lexical measures, descriptions v0, M-lex prompts with token-matched neutral twins, M-code contexts; COMMIT #1a |\n| 3a | `naming` | Qwen3-32B (OpenRouter, DeepInfra fp8, thinking off) names each description 20 times; <= 2 rewrites |\n| 3b | `topups` | 600 forced Qwen3-32B programs (60 per algorithm) |\n| 4 | `pools` | ACCEPT (tier A committed, tier B used), scrub + G-scrub, M-code sets PRIMARY / M32 / M8, placement sets SURV / BASE / DISOBEY, M-desc prompts; COMMIT #1b |\n| 5 | `states 32b mlex ban`, `states 8b mname mlex ban`, `states 32b mdesc mcode`, `states 8b mdesc mcode` | S-mean and code-token states |\n| 6 | `blocks` | Label-only block selection (iteration 8's layer rule) for every model x manifold; COMMIT #2 |\n| 7-10 | `analyse` | Geometry, verdicts, landing, bootstrap, robustness grid, crossnobis / z-scored sensitivities, frozen geodesics, lexical regression, exact-permutation RSA, name evocation, out-of-sample placement |\n| 11 | `figures` | PCA / MDS / Isomap figures in activation coordinates, class table, RDM heatmaps, behavioural MDS |\n| 12 | `outputs` | `data/points.jsonl`, `data/placements.jsonl`, `results/n4_verdict.json`, `method_out.json` |\n| audit | `audit/rederive.py`, `audit/audit_states.py` | Independent re-derivations (stdlib-only from JSON; independent kNN/Dijkstra from raw states) with placebos |\n\n`run_chain.sh` runs stages 5 (mdesc/mcode) to the audit unattended.\n\n## Layout\n\n| Path | What it is |\n|---|---|\n| `method.py` | Orchestrator, one sub-command per stage |\n| `src/common.py`, `src/prompts_tp.py`, `src/states.py`, `src/geometry.py`, `src/landing.py`, `src/label_tp.py`, `src/sample_or.py`, `src/judge_tp.py` | Iteration 8's modules (art_R-HSmXq2t97f), byte-identical copies, imported unchanged |\n| `src/e44/` | Unedited archive of iteration 8's whole `src/` |\n| `src/tpg.py` | This artifact's frozen constants (banned split, model pins, blocks, k, budgets, gates) |\n| `src/stage_setup.py` | Stage -1 and commit #0 |\n| `src/stage_states.py`, `src/stage_mcode.py` | State extraction (S-mean families; M-code readouts R1 / R1g / R2 / R3) |\n| `src/stage_cpu.py`, `src/expansion.py`, `src/expansion_child.py` | Probe grids, expansion tracer (child runs sandboxed, stdlib only), behavioural RDM, lexical measures, descriptions, M-lex twins, M-code contexts |\n| `src/stage_or.py` | OpenRouter naming gate and top-ups (pinned provider, cost ledger, 403 stop) |\n| `src/programs.py`, `src/stage_pools.py` | ACCEPT, scrubber, G-scrub, program and placement sets |\n| `src/stage_analysis.py` | Block selection, geometry, landing, bootstrap, robustness, lexical regression, RSA, placement |\n| `src/stage_figures.py`, `src/stage_outputs.py` | Figures and outputs |\n| `audit/` | Independent re-derivations |\n| `predictions/commit{0,1a,1b,2}.json`, `commitments.log` | Pre-registrations and their sha256 hash chain |\n| `inputs/` | Prior-artifact inputs copied at Stage -1 (+ `SHA256SUMS`) |\n| `vendor/exp9/`, `vendor/exp2/` | Iteration-2 harness, hidden suites, references and labeller (via iteration 8) |\n| `data/` | Probe grids, descriptions, naming calls, top-ups, program sets, M-lex prompts, points and placements rows, sandbox cache |\n| `results/` | Every analysis JSON |\n| `figures/` | PDF + PNG figures; `figures/coords/` holds the 2-D coordinates they were drawn from |\n| `cache/states/` | Activation states and frozen geodesic graphs. **Kept on the run's storage volume, not in the published repository** (files of 100 MB or more are not published; the whole directory is excluded from upload) |\n\n## Restoring removed files\n\nThe manifest (`.aii/manifest.yaml`) marks three things for deletion after the round; each is restorable:\n\n```bash\n# .venv/ (regenerable)\nuv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r requirements.lock.txt\n# inputs/e44/states/ (regenerable: copies of the iteration-8 states; needs the art_R-HSmXq2t97f artifact folder,\n# located by the TPG_E44 environment variable)\n.venv/bin/python method.py inputs\n# __pycache__/ (regenerable): created on import\n```\n\nModel weights are not stored in this folder. They are downloaded into the Hugging Face cache by\n`.venv/bin/python scripts/download_models.py` (`unsloth/Qwen3-32B-bnb-4bit@7f721e74a6a8cc9ee352f7e49303a2c1705f9083`,\n`Qwen/Qwen3-8B@b968826d9c46dd6066d109eabc6255188de91218`).\n`cache/states/` is kept on the run volume; to rebuild it from scratch run the `mname`, `states` and `analyse` stages\n(about 30 GPU-minutes on one RTX 5090).", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
````

### [20] THINKING · 2026-10-26 14:22:16 UTC

```
Since the full pipeline needs GPU access for Qwen3-32B plus OpenRouter calls, I'll build the Colab demo around CPU analysis on cached states instead—checking the preview output and analysis modules now to see which parts are feasible.
```

### [21] TOOL CALL — Bash · 2026-10-26 14:22:16 UTC

```
Count lines in the source modules:
SRC=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46; wc -l $SRC/src/*.py $SRC/audit/*.py; ls -la $SRC/src/ $SRC/src/e44 2>/dev/null | head -60; ls $SRC/vendor/exp9 | head
```

### [22] TOOL RESULT — Bash · 2026-10-26 14:22:16 UTC

```
{"stdout": "   473 /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/common.py\n   245 /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/expansion.py\n   364 /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/expansion_child.py\n   260 /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/geometry.py\n   266 /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/judge_tp.py\n   197 /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/label_tp.py\n    90 /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/landing.py\n   284 /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/programs.py\n   134 /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/prompts_tp.py\n   177 /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/sample_or.py\n   812 /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/stage_analysis.py\n   574 /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/stage_cpu.py\n   283 /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/stage_figures.py\n   167 /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/stage_mcode.py\n   315 /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/stage_or.py\n   259 /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/stage_outputs.py\n   260 /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/stage_pools.py\n   290 /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/stage_setup.py\n   290 /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/stage_states.py\n   300 /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/states.py\n    86 /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/tpg.py\n   108 /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/audit/audit_states.py\n   196 /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/audit/rederive.py\n  6430 total\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/:\ntotal 5269\ndrwxrwxrwx  3 aii-agent aii-agent 1054043 Oct 23 18:02 .\ndrwxrwxrwx 14 aii-agent aii-agent 3000131 Oct 23 18:02 ..\n-rw-rw-rw-  1 aii-agent aii-agent   24443 Oct 23 10:16 common.py\ndrwxrwxrwx  2 aii-agent aii-agent 1023691 Oct 23 10:16 e44\n-rw-rw-rw-  1 aii-agent aii-agent   11813 Oct 23 14:00 expansion.py\n-rw-rw-rw-  1 aii-agent aii-agent   12344 Oct 23 13:19 expansion_child.py\n-rw-rw-rw-  1 aii-agent aii-agent   12247 Oct 23 10:16 geometry.py\n-rw-rw-rw-  1 aii-agent aii-agent   12330 Oct 23 10:16 judge_tp.py\n-rw-rw-rw-  1 aii-agent aii-agent    9225 Oct 23 10:16 label_tp.py\n-rw-rw-rw-  1 aii-agent aii-agent    3927 Oct 23 10:16 landing.py\n-rw-rw-rw-  1 aii-agent aii-agent   12148 Oct 23 12:55 programs.py\n-rw-rw-rw-  1 aii-agent aii-agent    5697 Oct 23 10:16 prompts_tp.py\n-rw-rw-rw-  1 aii-agent aii-agent    9528 Oct 23 10:16 sample_or.py\n-rw-rw-rw-  1 aii-agent aii-agent   42442 Oct 23 15:10 stage_analysis.py\n-rw-rw-rw-  1 aii-agent aii-agent   33930 Oct 23 11:43 stage_cpu.py\n-rw-rw-rw-  1 aii-agent aii-agent   14120 Oct 23 12:40 stage_figures.py\n-rw-rw-rw-  1 aii-agent aii-agent    8052 Oct 23 14:00 stage_mcode.py\n-rw-rw-rw-  1 aii-agent aii-agent   16065 Oct 23 12:10 stage_or.py\n-rw-rw-rw-  1 aii-agent aii-agent   15983 Oct 23 12:44 stage_outputs.py\n-rw-rw-rw-  1 aii-agent aii-agent   15771 Oct 23 14:00 stage_pools.py\n-rw-rw-rw-  1 aii-agent aii-agent   16892 Oct 23 15:02 stage_setup.py\n-rw-rw-rw-  1 aii-agent aii-agent   15362 Oct 23 15:02 stage_states.py\n-rw-rw-rw-  1 aii-agent aii-agent   13799 Oct 23 10:16 states.py\n-rw-rw-rw-  1 aii-agent aii-agent    4690 Oct 23 10:11 tpg.py\n\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/e44:\ntotal 2271\ndrwxrwxrwx 2 aii-agent aii-agent 1023691 Oct 23 10:16 .\ndrwxrwxrwx 3 aii-agent aii-agent 1054043 Oct 23 18:02 ..\n-rw-rw-rw- 1 aii-agent aii-agent    7347 Oct 23 10:16 adjudicate.py\n-rw-rw-rw- 1 aii-agent aii-agent   24443 Oct 23 10:16 common.py\n-rw-rw-rw- 1 aii-agent aii-agent   13838 Oct 23 10:16 figures.py\n-rw-rw-rw- 1 aii-agent aii-agent   12247 Oct 23 10:16 geometry.py\n-rw-rw-rw- 1 aii-agent aii-agent   12330 Oct 23 10:16 judge_tp.py\n-rw-rw-rw- 1 aii-agent aii-agent    9225 Oct 23 10:16 label_tp.py\n-rw-rw-rw- 1 aii-agent aii-agent    3927 Oct 23 10:16 landing.py\n-rw-rw-rw- 1 aii-agent aii-agent    9025 Oct 23 10:16 novelty.py\n-rw-rw-rw- 1 aii-agent aii-agent    7531 Oct 23 10:16 outputs.py\n-rw-rw-rw- 1 aii-agent aii-agent    5697 Oct 23 10:16 prompts_tp.py\n-rw-rw-rw- 1 aii-agent aii-agent   10639 Oct 23 10:16 rederive.py\n-rw-rw-rw- 1 aii-agent aii-agent    9528 Oct 23 10:16 sample_or.py\n-rw-rw-rw- 1 aii-agent aii-agent    6276 Oct 23 10:16 sample_vllm.py\n-rw-rw-rw- 1 aii-agent aii-agent   12792 Oct 23 10:16 screen.py\n-rw-rw-rw- 1 aii-agent aii-agent   17842 Oct 23 10:16 setup_tp.py\n-rw-rw-rw- 1 aii-agent aii-agent   66112 Oct 23 10:16 stages.py\n-rw-rw-rw- 1 aii-agent aii-agent   13799 Oct 23 10:16 states.py\n__init__.py\nlabeller_ext\ntasks", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [23] TOOL CALL — Bash · 2026-10-26 14:22:16 UTC

```
Inspect the preview output structure:
SRC=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46; head -c 6000 $SRC/preview_method_out.json; echo; echo ...; python3 -c "
import json
d=json.load(open('$SRC/preview_method_out.json'))
def walk(x, p='', depth=0):
    if depth>4: return
    if isinstance(x, dict):
        for k,v in list(x.items())[:40]:
            t=type(v).__name__
            extra = f' len={len(v)}' if isinstance(v,(list,dict,str)) else ''
            print('  '*depth + f'{p}.{k}: {t}{extra}')
            walk(v, k, depth+1)
    elif isinstance(x, list) and x:
        print('  '*depth + f'{p}[0]: {type(x[0]).__name__}')
        walk(x[0], p+'[0]', depth+1)
walk(d)
"
```

### [24] TOOL RESULT — Bash · 2026-10-26 14:22:16 UTC

```
{"stdout": "{\n  \"metadata\": {\n    \"method_name\": \"TP-G: ten-algorithm grid manifold with and without names (iteration 9)\",\n    \"description\": \"Qwen3-32B nf4 (truncated decoder) and Qwen3-8B bf16 activation manifolds of 10 path-search algorithms from alias prompts (M-name), name-free descriptions (M-desc), alias-minus-twin deltas (M-lex) and ...\",\n    \"n4_verdict\": {\n      \"named_outcome\": \"MIXED\",\n      \"mcode_class_k15\": \"EDGE\",\n      \"mdesc_class_k15\": \"OPPOSITE\",\n      \"mcode_source_robustness\": \"ROBUST\",\n      \"k_sensitive\": false,\n      \"statement\": \"The geometry is correlational: it describes where representations and survivors sit, not whether the model uses this geometry to choose an algorithm (iteration 7's in-manifold pushes moved 0/300).\"\n    },\n    \"predictions_pass\": {\n      \"P1\": false,\n      \"P2\": false,\n      \"P3\": true,\n      \"P4\": true,\n      \"P5\": null,\n      \"P6\": true,\n      \"P7\": null,\n      \"P8\": true\n    },\n    \"secondary_statistics\": {\n      \"32b|mname\": {\n        \"L_star\": 31,\n        \"k5\": {\n          \"udij_class\": \"MIDDLE\",\n          \"udij_rank\": 3,\n          \"udij_ratio\": 1.0,\n          \"nearest_banned\": \"iddfs\",\n          \"classes\": {\n            \"bibfs\": \"EDGE\",\n            \"biastar\": \"OPPOSITE\",\n            \"idastar\": \"EDGE\",\n            \"jps\": \"OPPOSITE\",\n            \"dijkstra_unit\": \"MIDDLE\"\n          }\n        },\n        \"k10\": {\n          \"udij_class\": \"OPPOSITE\",\n          \"udij_rank\": 5,\n          \"udij_ratio\": 1.7828001234446156,\n          \"nearest_banned\": \"iddfs\",\n          \"classes\": {\n            \"bibfs\": \"EDGE\",\n            \"biastar\": \"EDGE\",\n            \"idastar\": \"MIDDLE\",\n            \"jps\": \"OPPOSITE\",\n            \"dijkstra_unit\": \"OPPOSITE\"\n          }\n        },\n        \"k15\": {\n          \"udij_class\": \"OPPOSITE\",\n          \"udij_rank\": 5,\n          \"udij_ratio\": 1.6310051031502248,\n          \"nearest_banned\": \"astar\",\n          \"classes\": {\n            \"bibfs\": \"EDGE\",\n            \"biastar\": \"EDGE\",\n            \"idastar\": \"MIDDLE\",\n            \"jps\": \"OPPOSITE\",\n            \"dijkstra_unit\": \"OPPOSITE\"\n          }\n        },\n        \"bootstrap_k15\": {\n          \"udij_edge_probability\": 0.0,\n          \"udij_class_stability\": 1.0,\n          \"udij_ratio_ci95\": [\n            1.270564590188291,\n            2.0066874413248654\n          ],\n          \"n_boot\": 1000\n        },\n        \"robustness_udij_class_counts\": {\n          \"MIDDLE\": 4,\n          \"OPPOSITE\": 10,\n          \"EDGE\": 1\n        },\n        \"crossnobis_udij_class\": \"OPPOSITE\",\n        \"zscored_udij_class\": \"OPPOSITE\",\n        \"euclid_centroid_udij_class\": \"OPPOSITE\",\n        \"split_half_spearman_brown_k15\": 0.9919649379108838,\n        \"nonbanned_used\": [\n          \"bibfs\",\n          \"biastar\",\n          \"idastar\"\n        ]\n      },\n      \"32b|mlex\": {\n        \"L_star\": 31,\n        \"k5\": {\n          \"udij_class\": \"OPPOSITE\",\n          \"udij_rank\": 5,\n          \"udij_ratio\": 1.5523128637874914,\n          \"nearest_banned\": \"astar\",\n          \"classes\": {\n            \"bibfs\": \"EDGE\",\n            \"biastar\": \"MIDDLE\",\n            \"idastar\": \"EDGE\",\n            \"jps\": \"OPPOSITE\",\n            \"dijkstra_unit\": \"OPPOSITE\"\n          }\n        },\n        \"k10\": {\n          \"udij_class\": \"OPPOSITE\",\n          \"udij_rank\": 4,\n          \"udij_ratio\": 1.2637408521222768,\n          \"nearest_banned\": \"astar\",\n          \"classes\": {\n            \"bibfs\": \"EDGE\",\n            \"biastar\": \"EDGE\",\n            \"idastar\": \"MIDDLE\",\n            \"jps\": \"OPPOSITE\",\n            \"dijkstra_unit\": \"OPPOSITE\"\n          }\n        },\n        \"k15\": {\n          \"udij_class\": \"OPPOSITE\",\n          \"udij_rank\": 4,\n          \"udij_ratio\": 1.200160346140986,\n          \"nearest_banned\": \"astar\",\n          \"classes\": {\n            \"bibfs\": \"EDGE\",\n            \"biastar\": \"EDGE\",\n            \"idastar\": \"MIDDLE\",\n            \"jps\": \"OPPOSITE\",\n            \"dijkstra_unit\": \"OPPOSITE\"\n          }\n        },\n        \"bootstrap_k15\": {\n          \"udij_edge_probability\": 0.0,\n          \"udij_class_stability\": 0.999,\n          \"udij_ratio_ci95\": [\n            1.0966313671447376,\n            1.31036043665128\n          ],\n          \"n_boot\": 1000\n        },\n        \"robustness_udij_class_counts\": {\n          \"OPPOSITE\": 15\n        },\n        \"crossnobis_udij_class\": \"OPPOSITE\",\n        \"zscored_udij_class\": \"OPPOSITE\",\n        \"euclid_centroid_udij_class\": \"OPPOSITE\",\n        \"split_half_spearman_brown_k15\": 0.9883372209263578,\n        \"nonbanned_used\": [\n          \"bibfs\",\n          \"biastar\",\n          \"idastar\"\n        ]\n      },\n      \"32b|mdesc\": {\n        \"L_star\": 31,\n        \"k5\": {\n          \"udij_class\": \"OPPOSITE\",\n          \"udij_rank\": 4,\n          \"udij_ratio\": 1.0212571538849213,\n          \"nearest_banned\": \"astar\",\n          \"classes\": {\n            \"bibfs\": \"OPPOSITE\",\n            \"biastar\": \"EDGE\",\n            \"idastar\": \"EDGE\",\n            \"dijkstra_unit\": \"OPPOSITE\"\n          }\n        },\n        \"k10\": {\n          \"udij_class\": \"OPPOSITE\",\n          \"udij_rank\": 3,\n          \"udij_ratio\": 1.0579689713910803,\n          \"nearest_banned\": \"astar\",\n          \"classes\": {\n            \"bibfs\": \"OPPOSITE\",\n            \"biastar\": \"EDGE\",\n            \"idastar\": \"EDGE\",\n            \"dijkstra_unit\": \"OPPOSITE\"\n          }\n        },\n        \"k15\": {\n          \"udij_class\": \"OPPOSITE\",\n          \"udij_rank\": 3,\n          \"udij_ratio\": 1.0811913889736746,\n          \"nearest_banned\": \"astar\",\n          \"classes\": {\n            \"bibfs\": \"OPPOSITE\",\n            \"biastar\": \"EDGE\",\n            \"idastar\": \"EDGE\",\n            \"dijkstra_unit\": \"OPPOSITE\"\n          }\n        },\n        \"bootstrap_k15\": {\n          \"udij_edge_probability\": 0.009,\n          \"udij_class_stability\": 0.991,\n          \"udij_ratio_ci95\": [\n            1.0116651536937242,\n            1.3689510274487982\n          ],\n          \"n_boot\": 1000\n        },\n        \"robustness_udij_class_counts\": {\n          \"OPPOSITE\": 15\n        },\n        \"crossnobis_udij_class\": \"OPPOSITE\",\n    \n...\n.metadata: dict len=11\n  metadata.method_name: str len=70\n  metadata.description: str len=203\n  metadata.n4_verdict: dict len=6\n    n4_verdict.named_outcome: str len=5\n    n4_verdict.mcode_class_k15: str len=4\n    n4_verdict.mdesc_class_k15: str len=8\n    n4_verdict.mcode_source_robustness: str len=6\n    n4_verdict.k_sensitive: bool\n    n4_verdict.statement: str len=196\n  metadata.predictions_pass: dict len=8\n    predictions_pass.P1: bool\n    predictions_pass.P2: bool\n    predictions_pass.P3: bool\n    predictions_pass.P4: bool\n    predictions_pass.P5: NoneType\n    predictions_pass.P6: bool\n    predictions_pass.P7: NoneType\n    predictions_pass.P8: bool\n  metadata.secondary_statistics: dict len=8\n    secondary_statistics.32b|mname: dict len=11\n      32b|mname.L_star: int\n      32b|mname.k5: dict len=5\n        k5.udij_class: str len=6\n        k5.udij_rank: int\n        k5.udij_ratio: float\n        k5.nearest_banned: str len=5\n        k5.classes: dict len=5\n      32b|mname.k10: dict len=5\n        k10.udij_class: str len=8\n        k10.udij_rank: int\n        k10.udij_ratio: float\n        k10.nearest_banned: str len=5\n        k10.classes: dict len=5\n      32b|mname.k15: dict len=5\n        k15.udij_class: str len=8\n        k15.udij_rank: int\n        k15.udij_ratio: float\n        k15.nearest_banned: str len=5\n        k15.classes: dict len=5\n      32b|mname.bootstrap_k15: dict len=4\n        bootstrap_k15.udij_edge_probability: float\n        bootstrap_k15.udij_class_stability: float\n        bootstrap_k15.udij_ratio_ci95: list len=2\n        bootstrap_k15.n_boot: int\n      32b|mname.robustness_udij_class_counts: dict len=3\n        robustness_udij_class_counts.MIDDLE: int\n        robustness_udij_class_counts.OPPOSITE: int\n        robustness_udij_class_counts.EDGE: int\n      32b|mname.crossnobis_udij_class: str len=8\n      32b|mname.zscored_udij_class: str len=8\n      32b|mname.euclid_centroid_udij_class: str len=8\n      32b|mname.split_half_spearman_brown_k15: float\n      32b|mname.nonbanned_used: list len=3\n        nonbanned_used[0]: str\n    secondary_statistics.32b|mlex: dict len=11\n      32b|mlex.L_star: int\n      32b|mlex.k5: dict len=5\n        k5.udij_class: str len=8\n        k5.udij_rank: int\n        k5.udij_ratio: float\n        k5.nearest_banned: str len=5\n        k5.classes: dict len=5\n      32b|mlex.k10: dict len=5\n        k10.udij_class: str len=8\n        k10.udij_rank: int\n        k10.udij_ratio: float\n        k10.nearest_banned: str len=5\n        k10.classes: dict len=5\n      32b|mlex.k15: dict len=5\n        k15.udij_class: str len=8\n        k15.udij_rank: int\n        k15.udij_ratio: float\n        k15.nearest_banned: str len=5\n        k15.classes: dict len=5\n      32b|mlex.bootstrap_k15: dict len=4\n        bootstrap_k15.udij_edge_probability: float\n        bootstrap_k15.udij_class_stability: float\n        bootstrap_k15.udij_ratio_ci95: list len=2\n        bootstrap_k15.n_boot: int\n      32b|mlex.robustness_udij_class_counts: dict len=1\n        robustness_udij_class_counts.OPPOSITE: int\n      32b|mlex.crossnobis_udij_class: str len=8\n      32b|mlex.zscored_udij_class: str len=8\n      32b|mlex.euclid_centroid_udij_class: str len=8\n      32b|mlex.split_half_spearman_brown_k15: float\n      32b|mlex.nonbanned_used: list len=3\n        nonbanned_used[0]: str\n    secondary_statistics.32b|mdesc: dict len=11\n      32b|mdesc.L_star: int\n      32b|mdesc.k5: dict len=5\n        k5.udij_class: str len=8\n        k5.udij_rank: int\n        k5.udij_ratio: float\n        k5.nearest_banned: str len=5\n        k5.classes: dict len=4\n      32b|mdesc.k10: dict len=5\n        k10.udij_class: str len=8\n        k10.udij_rank: int\n        k10.udij_ratio: float\n        k10.nearest_banned: str len=5\n        k10.classes: dict len=4\n      32b|mdesc.k15: dict len=5\n        k15.udij_class: str len=8\n        k15.udij_rank: int\n        k15.udij_ratio: float\n        k15.nearest_banned: str len=5\n        k15.classes: dict len=4\n      32b|mdesc.bootstrap_k15: dict len=4\n        bootstrap_k15.udij_edge_probability: float\n        bootstrap_k15.udij_class_stability: float\n        bootstrap_k15.udij_ratio_ci95: list len=2\n        bootstrap_k15.n_boot: int\n      32b|mdesc.robustness_udij_class_counts: dict len=1\n        robustness_udij_class_counts.OPPOSITE: int\n      32b|mdesc.crossnobis_udij_class: str len=8\n      32b|mdesc.zscored_udij_class: str len=8\n      32b|mdesc.euclid_centroid_udij_class: str len=8\n      32b|mdesc.split_half_spearman_brown_k15: float\n      32b|mdesc.nonbanned_used: list len=3\n        nonbanned_used[0]: str\n    secondary_statistics.32b|mcode_PRIMARY_R1: dict len=11\n      32b|mcode_PRIMARY_R1.L_star: int\n      32b|mcode_PRIMARY_R1.k5: dict len=5\n        k5.udij_class: str len=4\n        k5.udij_rank: int\n        k5.udij_ratio: float\n        k5.nearest_banned: str len=4\n        k5.classes: dict len=2\n      32b|mcode_PRIMARY_R1.k10: dict len=5\n        k10.udij_class: str len=4\n        k10.udij_rank: int\n        k10.udij_ratio: float\n        k10.nearest_banned: str len=4\n        k10.classes: dict len=2\n      32b|mcode_PRIMARY_R1.k15: dict len=5\n        k15.udij_class: str len=4\n        k15.udij_rank: int\n        k15.udij_ratio: float\n        k15.nearest_banned: str len=4\n        k15.classes: dict len=2\n      32b|mcode_PRIMARY_R1.bootstrap_k15: dict len=4\n        bootstrap_k15.udij_edge_probability: float\n        bootstrap_k15.udij_class_stability: float\n        bootstrap_k15.udij_ratio_ci95: list len=2\n        bootstrap_k15.n_boot: int\n      32b|mcode_PRIMARY_R1.robustness_udij_class_counts: dict len=1\n        robustness_udij_class_counts.EDGE: int\n      32b|mcode_PRIMARY_R1.crossnobis_udij_class: str len=4\n      32b|mcode_PRIMARY_R1.zscored_udij_class: str len=4\n      32b|mcode_PRIMARY_R1.euclid_centroid_udij_class: str len=4\n      32b|mcode_PRIMARY_R1.split_half_spearman_brown_k15: float\n      32b|mcode_PRIMARY_R1.nonbanned_used: list len=2\n        nonbanned_used[0]: str\n    secondary_statistics.32b|mcode_M32_R1: dict len=11\n      32b|mcode_M32_R1.L_star: int\n      32b|mcode_M32_R1.k5: dict len=5\n        k5.udij_class: str len=4\n        k5.udij_rank: int\n        k5.udij_ratio: float\n        k5.nearest_banned: str len=4\n        k5.classes: dict len=2\n      32b|mcode_M32_R1.k10: dict len=5\n        k10.udij_class: str len=4\n        k10.udij_rank: int\n        k10.udij_ratio: float\n        k10.nearest_banned: str len=4\n        k10.classes: dict len=2\n      32b|mcode_M32_R1.k15: dict len=5\n        k15.udij_class: str len=4\n        k15.udij_rank: int\n        k15.udij_ratio: float\n        k15.nearest_banned: str len=4\n        k15.classes: dict len=2\n      32b|mcode_M32_R1.bootstrap_k15: dict len=4\n        bootstrap_k15.udij_edge_probability: float\n        bootstrap_k15.udij_class_stability: float\n        bootstrap_k15.udij_ratio_ci95: list len=2\n        bootstrap_k15.n_boot: int\n      32b|mcode_M32_R1.robustness_udij_class_counts: dict len=1\n        robustness_udij_class_counts.EDGE: int\n      32b|mcode_M32_R1.crossnobis_udij_class: str len=4\n      32b|mcode_M32_R1.zscored_udij_class: str len=4\n      32b|mcode_M32_R1.euclid_centroid_udij_class: str len=4\n      32b|mcode_M32_R1.split_half_spearman_brown_k15: float\n      32b|mcode_M32_R1.nonbanned_used: list len=2\n        nonbanned_used[0]: str\n    secondary_statistics.8b|mname: dict len=11\n      8b|mname.L_star: int\n      8b|mname.k5: dict len=5\n        k5.udij_class: str len=8\n        k5.udij_rank: int\n        k5.udij_ratio: float\n        k5.nearest_banned: str len=5\n        k5.classes: dict len=5\n      8b|mname.k10: dict len=5\n        k10.udij_class: str len=8\n        k10.udij_rank: int\n        k10.udij_ratio: float\n        k10.nearest_banned: str len=5\n        k10.classes: dict len=5\n      8b|mname.k15: dict len=5\n        k15.udij_class: str len=8\n        k15.udij_rank: int\n        k15.udij_ratio: float\n        k15.nearest_banned: str len=5\n        k15.classes: dict len=5\n      8b|mname.bootstrap_k15: dict len=4\n        bootstrap_k15.udij_edge_probability: float\n        bootstrap_k15.udij_class_stability: float\n        bootstrap_k15.udij_ratio_ci95: list len=2\n        bootstrap_k15.n_boot: int\n      8b|mname.robustness_udij_class_counts: dict len=3\n        robustness_udij_class_counts.OPPOSITE: int\n        robustness_udij_class_counts.MIDDLE: int\n        robustness_udij_class_counts.EDGE: int\n      8b|mname.crossnobis_udij_class: str len=6\n      8b|mname.zscored_udij_class: str len=8\n      8b|mname.euclid_centroid_udij_class: str len=6\n      8b|mname.split_half_spearman_brown_k15: float\n      8b|mname.nonbanned_used: list len=3\n        nonbanned_used[0]: str\n    secondary_statistics.8b|mdesc: dict len=11\n      8b|mdesc.L_star: int\n      8b|mdesc.k5: dict len=5\n        k5.udij_class: str len=4\n        k5.udij_rank: int\n        k5.udij_ratio: float\n        k5.nearest_banned: str len=4\n        k5.classes: dict len=4\n      8b|mdesc.k10: dict len=5\n        k10.udij_class: str len=8\n        k10.udij_rank: int\n        k10.udij_ratio: float\n        k10.nearest_banned: str len=5\n        k10.classes: dict len=4\n      8b|mdesc.k15: dict len=5\n        k15.udij_class: str len=8\n        k15.udij_rank: int\n        k15.udij_ratio: float\n        k15.nearest_banned: str len=5\n        k15.classes: dict len=4\n      8b|mdesc.bootstrap_k15: dict len=4\n        bootstrap_k15.udij_edge_probability: float\n        bootstrap_k15.udij_class_stability: float\n        bootstrap_k15.udij_ratio_ci95: list len=2\n        bootstrap_k15.n_boot: int\n      8b|mdesc.robustness_udij_class_counts: dict len=2\n        robustness_udij_class_counts.EDGE: int\n        robustness_udij_class_counts.OPPOSITE: int\n      8b|mdesc.crossnobis_udij_class: str len=4\n      8b|mdesc.zscored_udij_class: str len=8\n      8b|mdesc.euclid_centroid_udij_class: str len=4\n      8b|mdesc.split_half_spearman_brown_k15: float\n      8b|mdesc.nonbanned_used: list len=3\n        nonbanned_used[0]: str\n    secondary_statistics.8b|mcode_PRIMARY_R1: dict len=11\n      8b|mcode_PRIMARY_R1.L_star: int\n      8b|mcode_PRIMARY_R1.k5: dict len=5\n        k5.udij_class: str len=4\n        k5.udij_rank: int\n        k5.udij_ratio: float\n        k5.nearest_banned: str len=4\n        k5.classes: dict len=2\n      8b|mcode_PRIMARY_R1.k10: dict len=5\n        k10.udij_class: str len=4\n        k10.udij_rank: int\n        k10.udij_ratio: float\n        k10.nearest_banned: str len=4\n        k10.classes: dict len=2\n      8b|mcode_PRIMARY_R1.k15: dict len=5\n        k15.udij_class: str len=4\n        k15.udij_rank: int\n        k15.udij_ratio: float\n        k15.nearest_banned: str len=4\n        k15.classes: dict len=2\n      8b|mcode_PRIMARY_R1.bootstrap_k15: dict len=4\n        bootstrap_k15.udij_edge_probability: float\n        bootstrap_k15.udij_class_stability: float\n        bootstrap_k15.udij_ratio_ci95: list len=2\n        bootstrap_k15.n_boot: int\n      8b|mcode_PRIMARY_R1.robustness_udij_class_counts: dict len=1\n        robustness_udij_class_counts.EDGE: int\n      8b|mcode_PRIMARY_R1.crossnobis_udij_class: str len=4\n      8b|mcode_PRIMARY_R1.zscored_udij_class: str len=4\n      8b|mcode_PRIMARY_R1.euclid_centroid_udij_class: str len=4\n      8b|mcode_PRIMARY_R1.split_half_spearman_brown_k15: float\n      8b|mcode_PRIMARY_R1.nonbanned_used: list len=2\n        nonbanned_used[0]: str\n  metadata.commitments: dict len=3\n    commitments.chain_ok: bool\n    commitments.problems: list len=0\n    commitments.entries: list len=3\n      entries[0]: dict\n        entries[0].label: str len=7\n        entries[0].utc: str len=27\n        entries[0].payload: str len=24\n  metadata.deviations: list len=3\n    deviations[0]: dict\n      deviations[0].code: str len=8\n      deviations[0].text: str len=66\n      deviations[0].utc: str len=27\n  metadata.costs: dict len=5\n    costs.total_usd: float\n    costs.by_purpose: dict len=2\n      by_purpose.naming_gate: float\n      by_purpose.topups: float\n    costs.n_calls: int\n    costs.budget_refusals: int\n    costs.updated_utc: str len=27\n  metadata.timing: list len=3\n    timing[0]: dict\n      timing[0].key: str len=15\n      timing[0].seconds: float\n      timing[0].units: int\n      timing[0].sec_per_unit: float\n      timing[0].note: str len=0\n      timing[0].utc: str len=27\n  metadata.baselines: dict len=6\n    baselines.lexical_model_rdm: str len=5\n    baselines.surface_code_rdm: str len=9\n    baselines.length_rdm: str len=5\n    baselines.behavioural_rdm: str len=5\n    baselines.name_condition: str len=31\n    baselines.nulls: str len=47\n  metadata.files: dict len=42\n    files.acceptance.json: str len=64\n    files.behavioural_distance.json: str len=64\n    files.costs.json: str len=64\n    files.deviations.json: str len=64\n    files.g_scrub.json: str len=64\n    files.g_tracer.json: str len=64\n    files.geometry_32b_mcode_M32_R1.json: str len=64\n    files.geometry_32b_mcode_PRIMARY_R1.json: str len=64\n    files.geometry_32b_mcode_PRIMARY_R2.json: str len=64\n    files.geometry_32b_mdesc.json: str len=64\n    files.geometry_32b_mlex.json: str len=64\n    files.geometry_32b_mname.json: str len=64\n    files.geometry_8b_mcode_PRIMARY_R1.json: str len=64\n    files.geometry_8b_mdesc.json: str len=64\n    files.geometry_8b_mname.json: str len=64\n    files.geometry_all.json: str len=64\n    files.inputs_status.json: str len=64\n    files.lexical.json: str len=64\n    files.lexical_regression.json: str len=64\n    files.load_32b_mcode.json: str len=64\n    files.load_32b_mdesc_mcode.json: str len=64\n    files.load_32b_mlex_ban.json: str len=64\n    files.load_8b_mcode.json: str len=64\n    files.load_8b_mdesc.json: str len=64\n    files.load_8b_mname_mlex_ban.json: str len=64\n    files.n4_verdict.json: str len=64\n    files.naming_gate.json: str len=64\n    files.naming_scorer_test.json: str len=64\n    files.placement.json: str len=64\n    files.positioning.json: str len=64\n    files.repro_mname_32b.json: str len=64\n    files.repro_mname_8b.json: str len=64\n    files.rsa.json: str len=64\n    files.states_mcode_32b.json: str len=64\n    files.states_mcode_8b.json: str len=64\n    files.states_mdesc_32b.json: str len=64\n    files.states_mdesc_8b.json: str len=64\n    files.states_mlex_32b.json: str len=64\n    files.states_mlex_8b.json: str len=64\n    files.states_mname_32b.json: str len=64\n.datasets: list len=3\n  datasets[0]: dict\n    datasets[0].dataset: str len=10\n    datasets[0].examples: list len=3\n      examples[0]: dict\n        examples[0].input: str len=203\n        examples[0].output: str len=3\n        examples[0].predict_nearest_mname: str len=3\n        examples[0].metadata_model: str len=26\n        examples[0].metadata_manifold: str len=5\n        examples[0].metadata_point_id: str len=15\n        examples[0].metadata_k: int", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [25] ASSISTANT · 2026-10-26 14:22:22 UTC

```
Next I'll read the core geometry and landing modules (the iteration-8 code reused unchanged here) and the frozen constants.
```

### [26] TOOL CALL — Bash · 2026-10-26 14:22:22 UTC

```
Read geometry, landing and constants modules:
SRC=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46; cat $SRC/src/geometry.py; echo "=== landing.py"; cat $SRC/src/landing.py; echo "=== tpg.py"; cat $SRC/src/tpg.py
```

### [27] TOOL RESULT — Bash · 2026-10-26 14:22:22 UTC

```
{"stdout": "#!/usr/bin/env python3\n\"\"\"Stage 7 G2/G3 geometry in actual activation coordinates (no summary bars).\n\nG2 L*: per block, standardise -> PCA(64) fit in fold -> multinomial logistic regression (C=1); grouped 10-fold CV with\ngroups = (template t, alias j) pairs (a held-out paraphrase is held out for all 10 algorithms); score = balanced\naccuracy; L* = argmax, ties within 0.01 -> block nearest depth 0.5 (all at ceiling -> nearest depth 0.5 among ceiling).\nG3 M1 at L*: PCA 2D (EVR), classical MDS on the 300 points and the 10 centroids (Kruskal stress-1), Isomap k in\n{5,10,15} on the symmetrised kNN distance graph (shortest inter-component edges added if disconnected, component count\nrecorded), geodesics via scipy shortest_path. g_k(a) = min over b in B of mean geodesic distance over pairs (points of\na, points of b) (iteration-7 top5geo.py definition). Classes: EDGE g < median, MIDDLE g == median, OPPOSITE g > median\nover the 5 non-banned algorithms. Reliability: split-half Spearman of 10x10 mean-geodesic matrices; 1,000 bootstrap\nresamples of paraphrase groups -> class and nearest-banned stability.\n\"\"\"\n\nfrom __future__ import annotations\n\nfrom typing import Any\n\nimport numpy as np\nfrom loguru import logger\nfrom scipy.sparse import csr_matrix\nfrom scipy.sparse.csgraph import connected_components, shortest_path\nfrom scipy.spatial.distance import cdist, pdist, squareform\nfrom scipy.stats import spearmanr\n\nfrom common import CANON_ORDER\n\n\n# ---------------------------------------------------------------------------------------------- layer selection\ndef layer_curve(X_blocks: np.ndarray, labels: np.ndarray, groups: np.ndarray, blocks: list[int],\n                sel_blocks: list[int], n_layers: int) -> dict[str, Any]:\n    from sklearn.decomposition import PCA\n    from sklearn.linear_model import LogisticRegression\n    from sklearn.metrics import balanced_accuracy_score\n    from sklearn.model_selection import GroupKFold\n    from sklearn.pipeline import make_pipeline\n    from sklearn.preprocessing import StandardScaler\n\n    curve = {}\n    preds = {}\n    gkf = GroupKFold(n_splits=10)\n    for b in sel_blocks:\n        X = X_blocks[:, blocks.index(b)].astype(np.float64)\n        pred = np.empty(len(labels), dtype=object)\n        for tr, te in gkf.split(X, labels, groups):\n            clf = make_pipeline(StandardScaler(), PCA(n_components=min(64, len(tr) - 1), random_state=0),\n                                LogisticRegression(C=1.0, max_iter=3000))\n            clf.fit(X[tr], labels[tr])\n            pred[te] = clf.predict(X[te])\n        curve[b] = float(balanced_accuracy_score(labels, pred.astype(str)))\n        preds[b] = [str(x) for x in pred]\n    best = max(curve.values())\n    near = [b for b in sel_blocks if best - curve[b] <= 0.01]\n    L = min(near, key=lambda b: (abs((b + 1) / n_layers - 0.5), b))\n    ceiling = [b for b in sel_blocks if curve[b] >= 0.9999]\n    rule = \"argmax (ties within 0.01 -> nearest depth 0.5)\"\n    if len(ceiling) == len(sel_blocks):\n        L = min(ceiling, key=lambda b: (abs((b + 1) / n_layers - 0.5), b))\n        rule = \"all blocks at ceiling -> nearest depth 0.5\"\n    return {\"curve\": curve, \"L_star\": int(L), \"best\": best, \"tied_blocks\": near, \"rule\": rule,\n            \"depth_of_L_star\": (L + 1) / n_layers, \"cv_pred_at_L\": preds[L]}\n\n\n# ---------------------------------------------------------------------------------------------- graphs\ndef knn_graph(X: np.ndarray, k: int) -> tuple[csr_matrix, int, int]:\n    \"\"\"Symmetrised kNN distance graph; disconnected components joined by their shortest inter-component edges\n    (as sklearn Isomap does). Returns (graph, components before joining, edges added).\"\"\"\n    D = squareform(pdist(X))\n    n = len(X)\n    D[D == 0] = 1e-12                       # duplicates (bootstrap) stay connected\n    np.fill_diagonal(D, 0.0)\n    W = np.zeros((n, n))\n    order = np.argsort(D, axis=1)\n    for i in range(n):\n        nb = [j for j in order[i] if j != i][:k]\n        W[i, nb] = D[i, nb]\n    W = np.maximum(W, W.T)\n    G = csr_matrix(W)\n    ncomp, lab = connected_components(G, directed=False)\n    added = 0\n    if ncomp > 1:\n        for a in range(ncomp):\n            for b in range(a + 1, ncomp):\n                ia, ib = np.where(lab == a)[0], np.where(lab == b)[0]\n                sub = D[np.ix_(ia, ib)]\n                i, j = np.unravel_index(np.argmin(sub), sub.shape)\n                W[ia[i], ib[j]] = W[ib[j], ia[i]] = max(sub[i, j], 1e-12)\n                added += 1\n        G = csr_matrix(W)\n    return G, int(ncomp), added\n\n\ndef geodesics(X: np.ndarray, k: int) -> tuple[np.ndarray, dict[str, Any]]:\n    Xu = X.copy()\n    # exact duplicates (bootstrap resamples) -> jitter-free handling: dedupe by index mapping\n    G, ncomp, added = knn_graph(Xu, k)\n    geo = shortest_path(G, method=\"D\", directed=False)\n    return geo, {\"k\": k, \"components_before_join\": ncomp, \"edges_added\": added, \"connected\": ncomp == 1,\n                 \"finite\": bool(np.isfinite(geo).all())}\n\n\ndef class_matrix(geo: np.ndarray, labels: np.ndarray, classes: list[str]) -> np.ndarray:\n    M = np.zeros((len(classes), len(classes)))\n    for i, a in enumerate(classes):\n        for j, b in enumerate(classes):\n            sub = geo[np.ix_(labels == a, labels == b)]\n            if i == j:\n                sub = sub[~np.eye(len(sub), dtype=bool)] if sub.shape[0] == sub.shape[1] else sub\n            M[i, j] = float(np.mean(sub)) if sub.size else np.nan\n    return M\n\n\ndef g_values(geo: np.ndarray, labels: np.ndarray, banned: list[str], nonbanned: list[str]) -> tuple[dict, dict]:\n    g, near = {}, {}\n    for a in nonbanned:\n        dm = [float(np.mean(geo[np.ix_(labels == a, labels == b)])) for b in banned]\n        g[a] = min(dm)\n        near[a] = banned[int(np.argmin(dm))]\n    return g, near\n\n\ndef g_centroid(X: np.ndarray, labels: np.ndarray, banned: list[str], nonbanned: list[str]) -> tuple[dict, dict]:\n    cent = {c: X[labels == c].mean(0) for c in set(labels)}\n    g, near = {}, {}\n    for a in nonbanned:\n        dm = [float(np.linalg.norm(cent[a] - cent[b])) for b in banned]\n        g[a] = min(dm)\n        near[a] = banned[int(np.argmin(dm))]\n    return g, near\n\n\ndef classify(g: dict[str, float]) -> tuple[dict[str, str], float]:\n    med = float(np.median(list(g.values())))\n    cls = {a: (\"EDGE\" if v < med - 1e-12 else \"OPPOSITE\" if v > med + 1e-12 else \"MIDDLE\") for a, v in g.items()}\n    return cls, med\n\n\n# ---------------------------------------------------------------------------------------------- embeddings\ndef stress1(D: np.ndarray, Y: np.ndarray) -> float:\n    d = squareform(pdist(Y))\n    iu = np.triu_indices(len(D), 1)\n    return float(np.sqrt(((D[iu] - d[iu]) ** 2).sum() / (D[iu] ** 2).sum()))\n\n\ndef classical_mds(D: np.ndarray, k: int = 2) -> np.ndarray:\n    n = len(D)\n    J = np.eye(n) - 1.0 / n\n    B = -0.5 * J @ (D ** 2) @ J\n    w, V = np.linalg.eigh(B)\n    i = np.argsort(w)[::-1][:k]\n    return V[:, i] * np.sqrt(np.maximum(w[i], 0))\n\n\ndef manifold(X: np.ndarray, labels: np.ndarray, banned: list[str], ks: tuple[int, ...] = (5, 10, 15),\n             fit_isomap: bool = True) -> dict[str, Any]:\n    \"\"\"Full M1 description at one block (raw coordinates).\"\"\"\n    from sklearn.decomposition import PCA\n    from sklearn.manifold import Isomap\n\n    nonbanned = [a for a in CANON_ORDER if a not in banned]\n    out: dict[str, Any] = {\"n_points\": int(len(X)), \"banned\": banned, \"nonbanned\": nonbanned}\n    pca = PCA(n_components=10, random_state=0).fit(X)\n    out[\"pca_evr\"] = pca.explained_variance_ratio_[:10].tolist()\n    D = squareform(pdist(X))\n    Ym = classical_mds(D)\n    out[\"mds_points_stress1\"] = stress1(D, Ym)\n    cent = np.stack([X[labels == c].mean(0) for c in CANON_ORDER])\n    Dc = squareform(pdist(cent))\n    Ymc = classical_mds(Dc)\n    out[\"mds_centroids_stress1\"] = stress1(Dc, Ymc)\n    out[\"centroid_distance_matrix\"] = Dc.tolist()\n    emb: dict[str, Any] = {\"pca\": pca, \"mds_points\": Ym, \"mds_centroids\": Ymc, \"isomap\": {}, \"geo\": {}}\n    for k in ks:\n        geo, info = geodesics(X, k)\n        g, near = g_values(geo, labels, banned, nonbanned)\n        cls, med = classify(g)\n        M = class_matrix(geo, labels, CANON_ORDER)\n        out[f\"k{k}\"] = {**info, \"g\": g, \"nearest_banned\": near, \"classes\": cls, \"median\": med,\n                        \"class_geodesic_matrix\": M.tolist()}\n        emb[\"geo\"][k] = geo\n        if fit_isomap:\n            iso = Isomap(n_neighbors=k, n_components=2)\n            Y = iso.fit_transform(X)\n            out[f\"k{k}\"][\"isomap_stress1_vs_geodesic\"] = stress1(np.where(np.isfinite(geo), geo, np.nanmax(\n                geo[np.isfinite(geo)])), Y)\n            emb[\"isomap\"][k] = (iso, Y)\n    gc_, nc_ = g_centroid(X, labels, banned, nonbanned)\n    clc, medc = classify(gc_)\n    out[\"euclid_centroid\"] = {\"g\": gc_, \"nearest_banned\": nc_, \"classes\": clc, \"median\": medc}\n    out[\"k_primary\"] = 10 if out[\"k10\"][\"connected\"] else next((k for k in ks if out[f\"k{k}\"][\"connected\"]), 10)\n    return out | {\"_emb\": emb}\n\n\ndef split_half(X: np.ndarray, labels: np.ndarray, groups: np.ndarray, k: int) -> dict[str, Any]:\n    h1 = groups < 15\n    res = {}\n    mats = []\n    for m in (h1, ~h1):\n        geo, info = geodesics(X[m], k)\n        mats.append(class_matrix(geo, labels[m], CANON_ORDER))\n    iu = np.triu_indices(10, 1)\n    rho = spearmanr(mats[0][iu], mats[1][iu]).statistic\n    res[\"spearman_offdiag\"] = float(rho)\n    res[\"k\"] = k\n    return res\n\n\ndef bootstrap(X: np.ndarray, labels: np.ndarray, groups: np.ndarray, banned: list[str], k: int, n_boot: int = 1000,\n              seed: int = 0) -> dict[str, Any]:\n    \"\"\"Resample the 30 paraphrase groups with replacement; duplicates are kept as distinct points (a zero-length edge\n    is replaced by 1e-12 so duplicates stay connected).\"\"\"\n    rng = np.random.default_rng(seed)\n    nonbanned = [a for a in CANON_ORDER if a not in banned]\n    ug = np.unique(groups)\n    full_g, full_near = g_values(geodesics(X, k)[0], labels, banned, nonbanned)\n    full_cls, _ = classify(full_g)\n    same_cls = {a: 0 for a in nonbanned}\n    same_near = {a: 0 for a in nonbanned}\n    edge_count = {a: 0 for a in nonbanned}\n    for _ in range(n_boot):\n        gs = rng.choice(ug, size=len(ug), replace=True)\n        idx = np.concatenate([np.where(groups == g)[0] for g in gs])\n        Xb = X[idx] + rng.normal(0, 1e-9, size=X[idx].shape)\n        geo, _info = geodesics(Xb, k)\n        g, near = g_values(geo, labels[idx], banned, nonbanned)\n        cls, _ = classify(g)\n        for a in nonbanned:\n            same_cls[a] += cls[a] == full_cls[a]\n            same_near[a] += near[a] == full_near[a]\n            edge_count[a] += cls[a] == \"EDGE\"\n    return {\"n_boot\": n_boot, \"k\": k, \"class_stability\": {a: same_cls[a] / n_boot for a in nonbanned},\n            \"nearest_banned_stability\": {a: same_near[a] / n_boot for a in nonbanned},\n            \"edge_probability\": {a: edge_count[a] / n_boot for a in nonbanned}, \"full_classes\": full_cls,\n            \"full_nearest\": full_near}\n\n\ndef strip_private(d: dict[str, Any]) -> dict[str, Any]:\n    return {k: v for k, v in d.items() if not k.startswith(\"_\")}\n\n\ndef synthetic_ring(n_per: int = 30, dim: int = 50, radius: float = 10.0, noise: float = 1.0,\n                   seed: int = 0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:\n    \"\"\"T8: 10 Gaussian clusters on a ring (algorithms in canonical order around the ring).\"\"\"\n    rng = np.random.default_rng(seed)\n    X, lab, grp = [], [], []\n    basis = np.linalg.qr(rng.normal(size=(dim, 2)))[0]\n    for i, a in enumerate(CANON_ORDER):\n        th = 2 * np.pi * i / 10\n        c = radius * (np.cos(th) * basis[:, 0] + np.sin(th) * basis[:, 1])\n        X.append(c + noise * rng.normal(size=(n_per, dim)) / np.sqrt(dim) * 3)\n        lab += [a] * n_per\n        grp += list(range(n_per))\n    return np.concatenate(X), np.array(lab), np.array(grp)\n\n\ndef log_summary(tag: str, m: dict[str, Any]) -> None:\n    kp = m[\"k_primary\"]\n    logger.info(f\"[{tag}] PCA EVR {np.round(m['pca_evr'][:2], 3).tolist()}, MDS stress1 points \"\n                f\"{m['mds_points_stress1']:.3f} centroids {m['mds_centroids_stress1']:.3f}; k={kp} classes \"\n                f\"{m[f'k{kp}']['classes']} comps {[m[f'k{k}']['components_before_join'] for k in (5, 10, 15)]}\")\n=== landing.py\n#!/usr/bin/env python3\n\"\"\"Stage 7 G5 landing test. S = mean over correct survivors of g_k(label). Nulls (seed 0):\n  U: labels iid uniform over the 5 non-banned algorithms, 10,000 draws (committed)\n  F: iid by m*'s baseline frequency among non-banned algorithms, +0.5 smoothing, 10,000 draws (committed)\n  P: exact 120 permutations of algorithm identities among the 5, count profile fixed -> algorithm-level p (added)\n  C: iid by correct-when-forced rates, +0.5 smoothed (added; correctness-filter confound)\np_edge = P(S_null <= S); p_opp = P(S_null >= S).\nVERDICT: EDGE iff p_edge(U) < 0.05 and p_edge(F) < 0.05 and > 50% of survivors in EDGE algorithms; OPPOSITE mirrored;\nelse NEITHER. p(P) and p(C) always printed beside it.\n\"\"\"\n\nfrom __future__ import annotations\n\nimport collections\nimport itertools\nfrom typing import Any\n\nimport numpy as np\n\n\ndef stat(g: dict[str, float], labels: list[str]) -> float:\n    return float(np.mean([g[a] for a in labels])) if labels else float(\"nan\")\n\n\ndef iid_null(g: dict[str, float], probs: dict[str, float], n: int, draws: int = 10000, seed: int = 0) -> np.ndarray:\n    algs = list(g)\n    p = np.array([probs[a] for a in algs], dtype=float)\n    p = p / p.sum()\n    vals = np.array([g[a] for a in algs])\n    rng = np.random.default_rng(seed)\n    idx = rng.choice(len(algs), size=(draws, n), p=p)\n    return vals[idx].mean(1)\n\n\ndef perm_null(g: dict[str, float], labels: list[str]) -> np.ndarray:\n    algs = list(g)\n    cnt = collections.Counter(labels)\n    counts = np.array([cnt[a] for a in algs], dtype=float)\n    vals = np.array([g[a] for a in algs])\n    out = []\n    for perm in itertools.permutations(range(len(algs))):\n        out.append(float((counts * vals[list(perm)]).sum() / counts.sum()))\n    return np.array(out)\n\n\ndef pvals(null: np.ndarray, S: float) -> dict[str, float]:\n    eps = 1e-12\n    return {\"p_edge\": float(np.mean(null <= S + eps)), \"p_opp\": float(np.mean(null >= S - eps)),\n            \"null_mean\": float(null.mean()), \"null_q\": np.quantile(null, [0.025, 0.05, 0.5, 0.95, 0.975]).tolist(),\n            \"n\": int(len(null))}\n\n\ndef landing(g: dict[str, float], classes: dict[str, str], surv: list[str], base_counts: dict[str, int],\n            forced_rates: dict[str, float], draws: int = 10000, seed: int = 0) -> dict[str, Any]:\n    nonbanned = list(g)\n    n = len(surv)\n    out: dict[str, Any] = {\"n_surv\": n, \"survivor_counts\": dict(collections.Counter(surv)), \"g\": g, \"classes\": classes}\n    if n == 0:\n        out.update({\"S\": None, \"verdict\": \"NO SURVIVORS\", \"descriptive_only\": True})\n        return out\n    S = stat(g, surv)\n    out[\"S\"] = S\n    U = iid_null(g, {a: 1.0 for a in nonbanned}, n, draws, seed)\n    fprobs = {a: base_counts.get(a, 0) + 0.5 for a in nonbanned}\n    F = iid_null(g, fprobs, n, draws, seed + 1)\n    P = perm_null(g, surv)\n    cprobs = {a: forced_rates.get(a, 0.0) + 0.5 / 40 for a in nonbanned}\n    C = iid_null(g, cprobs, n, draws, seed + 2)\n    out[\"nulls\"] = {\"U\": pvals(U, S), \"F\": pvals(F, S), \"P\": pvals(P, S), \"C\": pvals(C, S)}\n    out[\"null_F_probs\"] = fprobs\n    out[\"null_F_near_uniform\"] = all(base_counts.get(a, 0) == 0 for a in nonbanned)\n    out[\"null_C_probs\"] = cprobs\n    share = collections.Counter(classes[a] for a in surv)\n    out[\"class_shares\"] = {k: v / n for k, v in share.items()}\n    pU, pF = out[\"nulls\"][\"U\"], out[\"nulls\"][\"F\"]\n    if pU[\"p_edge\"] < 0.05 and pF[\"p_edge\"] < 0.05 and share[\"EDGE\"] / n > 0.5:\n        v = \"EDGE\"\n    elif pU[\"p_opp\"] < 0.05 and pF[\"p_opp\"] < 0.05 and share[\"OPPOSITE\"] / n > 0.5:\n        v = \"OPPOSITE\"\n    else:\n        v = \"NEITHER\"\n    out[\"verdict\"] = v\n    out[\"descriptive_only\"] = n < 5\n    out[\"perm_floor\"] = float(1.0 / len(P) * sum(1 for x in P if abs(x - P.min()) < 1e-12))\n    out[\"_nulls_raw\"] = {\"U\": U, \"F\": F, \"P\": P, \"C\": C}\n    return out\n\n\ndef strip(d: dict[str, Any]) -> dict[str, Any]:\n    return {k: v for k, v in d.items() if not k.startswith(\"_\")}\n=== tpg.py\n#!/usr/bin/env python3\n\"\"\"TP-G shared constants and helpers (iteration 9, gen_plan_experiment_2_idx3).\n\nEverything that is frozen for this artifact lives here: the banned / non-banned split, the model pins, the block\nranges, the verdict settings, the budget, and the absolute locations of the prior artifacts that Stage -1 copies into\ninputs/ (read once, never written). The iteration-8 modules (common, prompts_tp, states, geometry, landing, label_tp,\nsample_or) are byte-identical copies of art_R-HSmXq2t97f src/ and are imported unchanged; their ROOT resolves to this\nartifact's folder because they sit one level below it.\n\"\"\"\n\nfrom __future__ import annotations\n\nimport os\nfrom pathlib import Path\n\nfrom common import (CANON_ORDER, CONFIGS, DATA, FIGS, LOGS, PRED, RESULTS, ROOT, STATES, read_json,  # noqa: F401\n                    utc_now, write_json)\n\n# ---------------------------------------------------------------------------------------------- catalogue split\nB5 = [\"bfs\", \"dfs\", \"iddfs\", \"astar\", \"gbfs\"]                       # banned (iteration-8 C6 top five)\nNB5 = [\"bibfs\", \"biastar\", \"idastar\", \"jps\", \"dijkstra_unit\"]       # non-banned\nUDIJ = \"dijkstra_unit\"\nassert set(B5) | set(NB5) == set(CANON_ORDER)\n\n# ---------------------------------------------------------------------------------------------- prior artifacts\nRUN0 = Path(\"/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop\")\nE44 = Path(os.environ.get(\"TPG_E44\", str(RUN0 / \"iter_8/gen_art/gen_art_experiment_44\")))           # art_R-HSmXq2t97f\nEXP9 = Path(os.environ.get(\"TPG_EXP9\", \"/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/\"\n                                       \"gen_art/gen_art_experiment_9\"))                              # art_IVZc3TWCeE9f\nEXP2 = Path(os.environ.get(\"TPG_EXP2\", \"/ai-inventor/aii_data/runs/run_4VFKidE1bxPG/3_invention_loop/iter_1/\"\n                                       \"gen_art/gen_art_experiment_2\"))                              # art_D6Z0Snf09sFL\nEXP8 = Path(os.environ.get(\"TPG_EXP8\", \"/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/\"\n                                       \"gen_art/gen_art_experiment_8\"))                              # art_8_ULPE8jJQc_\nDSET = Path(os.environ.get(\"TPG_DSET\", \"/ai-inventor/aii_data/runs/run_4VFKidE1bxPG/3_invention_loop/iter_1/\"\n                                       \"gen_art/gen_art_dataset_1\"))                                 # art_j3Rm_lr2nzR6\nARTIFACT_IDS = {\"E44\": \"art_R-HSmXq2t97f\", \"EXP9\": \"art_IVZc3TWCeE9f\", \"EXP2\": \"art_D6Z0Snf09sFL\",\n                \"EXP8\": \"art_8_ULPE8jJQc_\", \"DSET\": \"art_j3Rm_lr2nzR6\"}\n\nINPUTS = ROOT / \"inputs\"\nIN_E44 = INPUTS / \"e44\"\nSTATES_DIR = STATES                      # cache/states (kept on the run volume)\n\n# ---------------------------------------------------------------------------------------------- models\nM32 = {\"repo\": \"unsloth/Qwen3-32B-bnb-4bit\", \"revision\": \"7f721e74a6a8cc9ee352f7e49303a2c1705f9083\",\n       \"precision\": \"nf4\", \"n_layers\": 64, \"n_keep\": 48, \"ext_blocks\": list(range(17, 48)),\n       \"sel_blocks\": list(range(19, 46)), \"tag\": \"32b\", \"engine\": \"hf-nf4-truncated\", \"ref_block\": 31}\nM8 = {\"repo\": \"Qwen/Qwen3-8B\", \"revision\": \"b968826d9c46dd6066d109eabc6255188de91218\", \"precision\": \"bf16\",\n      \"n_layers\": 36, \"n_keep\": 29, \"ext_blocks\": list(range(8, 29)), \"sel_blocks\": list(range(10, 27)),\n      \"tag\": \"8b\", \"engine\": \"hf-bf16-truncated\", \"ref_block\": 17}\nMODELS = {\"32b\": M32, \"8b\": M8}\n\n# ---------------------------------------------------------------------------------------------- frozen settings\nKS = (5, 10, 15)\nK_VERDICT = 15                       # iteration 8's primary k (k 10 is the committed second verdict setting)\nK_SECOND = 10\nN_BOOT_32B = 1000\nN_BOOT_OTHER = 200\nOR_CAP_USD = float(os.environ.get(\"TPG_OR_CAP\", \"0.40\"))\nTOPUP_STOP_USD = 0.32\nOR_MODEL = \"qwen/qwen3-32b\"\nOR_PIN = {\"order\": [\"DeepInfra\"], \"allow_fallbacks\": False, \"quantizations\": [\"fp8\"]}\nNAMING_N = 20\nNAMING_PASS = 16\nTOPUP_TARGET = 24\nTOPUP_MAX_ATTEMPTS = 60\nMCODE_PER_ALG = 20\nMCODE_MIN = 10\nLOO_GATE = 0.70\nREPRO_GATE = 0.95\nRELIABILITY_FLAG = 0.70\nSEED = 9009\n\n# Survivors of iteration 8 (C6, Qwen3-32B thinking on): label-level landing input (landing.json / confirmation.json).\nSURV_SCREEN = [UDIJ] * 6\nSURV_CONFIRM = [UDIJ] * 9\n\n\ndef forced_rates_e44() -> dict[str, float]:\n    \"\"\"Correct-when-forced rates recovered from iteration 8's null_C_probs (p - 0.5/40).\"\"\"\n    land = read_json(IN_E44 / \"results\" / \"landing.json\")\n    probs = land[\"primary\"][\"null_C_probs\"]\n    return {a: max(0.0, float(p) - 0.0125) for a, p in probs.items()}\n\n\ndef rel(p: Path) -> str:\n    return str(Path(p).resolve().relative_to(ROOT))", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [28] TOOL CALL — Bash · 2026-10-26 14:22:22 UTC

```
Show the preview dataset examples:
SRC=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46; python3 -c "
import json
d=json.load(open('$SRC/preview_method_out.json'))
for ds in d['datasets']:
    print('DATASET', ds['dataset'], len(ds['examples']))
    for ex in ds['examples'][:3]:
        print(json.dumps(ex, indent=1)[:1500])
        print('--')
"
```

### [29] TOOL RESULT — Bash · 2026-10-26 14:22:22 UTC

```
{"stdout": "DATASET tpg_points 3\n{\n \"input\": \"Implement breadth-first search (BFS) for this task.\\n\\nTask: write a Python function solve(grid, start, goal) that finds a path between two cells of a grid. grid is a list of equal-length strings with b...\",\n \"output\": \"bfs\",\n \"predict_nearest_mname\": \"bfs\",\n \"metadata_model\": \"unsloth/Qwen3-32B-bnb-4bit\",\n \"metadata_manifold\": \"mname\",\n \"metadata_point_id\": \"mname|bfs|t0|j0\",\n \"metadata_k\": 15\n}\n--\n{\n \"input\": \"Implement BFS for this task.\\n\\nTask: write a Python function solve(grid, start, goal) that finds a path between two cells of a grid. grid is a list of equal-length strings with between 1 and 30 rows an...\",\n \"output\": \"bfs\",\n \"predict_nearest_mname\": \"bfs\",\n \"metadata_model\": \"unsloth/Qwen3-32B-bnb-4bit\",\n \"metadata_manifold\": \"mname\",\n \"metadata_point_id\": \"mname|bfs|t0|j1\",\n \"metadata_k\": 15\n}\n--\n{\n \"input\": \"Implement a breadth-first search for this task.\\n\\nTask: write a Python function solve(grid, start, goal) that finds a path between two cells of a grid. grid is a list of equal-length strings with betwe...\",\n \"output\": \"bfs\",\n \"predict_nearest_mname\": \"bfs\",\n \"metadata_model\": \"unsloth/Qwen3-32B-bnb-4bit\",\n \"metadata_manifold\": \"mname\",\n \"metadata_point_id\": \"mname|bfs|t0|j2\",\n \"metadata_k\": 15\n}\n--\nDATASET tpg_placements 3\n{\n \"input\": \"import random\\n\\ndef solve(grid, start, goal):\\n    rows = len(grid)\\n    if rows == 0:\\n        return []\\n    cols = len(grid[0])\\n    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':\\n ...\",\n \"output\": \"other: random walk with restart\",\n \"predict_nearest_mcode\": \"bfs\",\n \"predict_class\": \"EDGE\",\n \"metadata_set\": \"SURV\",\n \"metadata_uid\": \"C6|ban|0\",\n \"metadata_g_x\": 24.68766120716996,\n \"metadata_nearest_banned\": \"bfs\"\n}\n--\n{\n \"input\": \"import heapq\\nimport math\\n\\ndef solve(grid, start, goal):\\n    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':\\n        return []\\n    if start == goal:\\n        return [start]\\n    rows...\",\n \"output\": \"dijkstra_unit\",\n \"predict_nearest_mcode\": \"dijkstra_unit\",\n \"predict_class\": \"EDGE\",\n \"metadata_set\": \"SURV\",\n \"metadata_uid\": \"C6|ban|7\",\n \"metadata_g_x\": 21.97903238341068,\n \"metadata_nearest_banned\": \"gbfs\"\n}\n--\n{\n \"input\": \"import heapq\\n\\ndef solve(grid, start, goal):\\n    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':\\n        return []\\n    if start == goal:\\n        return [start]\\n    rows, cols = (le...\",\n \"output\": \"dijkstra_unit\",\n \"predict_nearest_mcode\": \"dijkstra_unit\",\n \"predict_class\": \"EDGE\",\n \"metadata_set\": \"SURV\",\n \"metadata_uid\": \"C6|ban|18\",\n \"metadata_g_x\": 17.141750481699457,\n \"metadata_nearest_banned\": \"gbfs\"\n}\n--\nDATASET tpg_naming 3\n{\n \"input\": \"a search that keeps the cells waiting to be visited in a first-in-first-out queue and always takes the oldest one next\",\n \"output\": \"bfs\",\n \"predict_qwen32b_modal\": \"bfs\",\n \"metadata_rate\": 1.0,\n \"metadata_passed\": true,\n \"metadata_slot\": \"bfs|0\",\n \"metadata_version\": 0\n}\n--\n{\n \"input\": \"a search that visits every cell one step from the start, then every cell two steps away, and so on, ring by ring\",\n \"output\": \"bfs\",\n \"predict_qwen32b_modal\": \"bfs\",\n \"metadata_rate\": 1.0,\n \"metadata_passed\": true,\n \"metadata_slot\": \"bfs|1\",\n \"metadata_version\": 0\n}\n--\n{\n \"input\": \"a search that spreads out from the start like a ripple on a pond, finishing each wave before starting the next\",\n \"output\": \"bfs\",\n \"predict_qwen32b_modal\": \"bfs\",\n \"metadata_rate\": 1.0,\n \"metadata_passed\": true,\n \"metadata_slot\": \"bfs|2\",\n \"metadata_version\": 0\n}\n--", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [30] ASSISTANT · 2026-10-26 14:22:28 UTC

```
The analysis stage is where the demo's computation lives. I'll read `stage_analysis.py` in full, plus the state-level audit and the cache layout.
```

### [31] TOOL CALL — Read · 2026-10-26 14:22:28 UTC

```
/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/stage_analysis.py
```

### [32] TOOL RESULT — Read · 2026-10-26 14:22:28 UTC

```
{"type": "text", "file": {"filePath": "/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src/stage_analysis.py", "content": "#!/usr/bin/env python3\n\"\"\"Stages 6-10: label-only block selection + COMMIT #2; geometry, verdicts, landing, bootstrap, robustness,\ncrossnobis and z-scored sensitivities, frozen geodesics for iteration 10; lexical regressions; RSA with exact\nlabel-permutation Mantel nulls; name evocation; per-program o... [truncated, 44907 chars total]
```

### [33] TOOL CALL — Bash · 2026-10-26 14:22:28 UTC

```
Read state audit script and list cached states:
SRC=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46; cat $SRC/audit/audit_states.py; echo "=== cache"; find $SRC/cache -maxdepth 3 | head -80; du -sh $SRC/cache/states/* 2>/dev/null | sort -h | tail -40
```

### [34] TOOL RESULT — Bash · 2026-10-26 14:22:28 UTC

```
{"stdout": "#!/usr/bin/env python3\n\"\"\"State-level audit by a different code path: recomputes the headline class geometry from the raw state files\n(cache/states/*.npz) with sklearn's NearestNeighbors kNN graph, networkx connected components and joins, and\nnetworkx Dijkstra (iteration 8's geometry.py is NOT imported), at the committed block (predictions/commit2.json)\nand k 15; compares g, classes and the unit-Dijkstra rank with results/geometry_all.json. Placebo: the same pipeline\non algorithm labels shuffled across points must not reproduce the classes more often than chance.\nWrites results/audit_states.json.\"\"\"\n\nimport json\nimport sys\nfrom pathlib import Path\n\nimport networkx as nx\nimport numpy as np\nfrom sklearn.neighbors import NearestNeighbors\n\nROOT = Path(__file__).resolve().parent.parent\nCANON = [\"bfs\", \"dfs\", \"bibfs\", \"iddfs\", \"astar\", \"gbfs\", \"dijkstra_unit\", \"idastar\", \"jps\", \"biastar\"]\nB5 = [\"bfs\", \"dfs\", \"iddfs\", \"astar\", \"gbfs\"]\nNB5 = [\"bibfs\", \"biastar\", \"idastar\", \"jps\", \"dijkstra_unit\"]\n\n\ndef knn_geodesics(X, k):\n    nn = NearestNeighbors(n_neighbors=k + 1).fit(X)\n    dist, idx = nn.kneighbors(X)\n    G = nx.Graph()\n    G.add_nodes_from(range(len(X)))\n    for i in range(len(X)):\n        for d, j in zip(dist[i], idx[i]):\n            if j != i:\n                w = max(float(d), 1e-12)\n                if not G.has_edge(i, j) or G[i][j][\"weight\"] > w:\n                    G.add_edge(i, int(j), weight=w)\n    comps = [sorted(c) for c in nx.connected_components(G)]\n    if len(comps) > 1:\n        for a in range(len(comps)):\n            for b in range(a + 1, len(comps)):\n                A, Bc = np.array(comps[a]), np.array(comps[b])\n                D = np.linalg.norm(X[A][:, None, :] - X[Bc][None, :, :], axis=2)\n                i, j = np.unravel_index(np.argmin(D), D.shape)\n                G.add_edge(int(A[i]), int(Bc[j]), weight=max(float(D[i, j]), 1e-12))\n    n = len(X)\n    geo = np.zeros((n, n))\n    for s, dd in nx.all_pairs_dijkstra_path_length(G, weight=\"weight\"):\n        for t, v in dd.items():\n            geo[s, t] = v\n    return geo, len(comps)\n\n\ndef g_classes(geo, labels):\n    nb = [a for a in NB5 if a in set(labels)]\n    g = {a: min(float(geo[np.ix_(labels == a, labels == b)].mean()) for b in B5 if (labels == b).any()) for a in nb}\n    m = float(np.median(list(g.values())))\n    cls = {a: \"EDGE\" if v < m - 1e-12 else \"OPPOSITE\" if v > m + 1e-12 else \"MIDDLE\" for a, v in g.items()}\n    return g, cls\n\n\ndef load(model, name):\n    S = ROOT / \"cache\" / \"states\"\n    if name in (\"mname\", \"mdesc\"):\n        z = np.load(S / f\"{name}_{model}.npz\")\n        return z[\"smean\"], z[\"algorithm\"], [int(b) for b in z[\"blocks\"]]\n    if name == \"mlex\":\n        z = np.load(S / f\"mlex_{model}.npz\")\n        return z[\"delta\"], z[\"algorithm\"], [int(b) for b in z[\"blocks\"]]\n    z = np.load(S / f\"mcode_{model}.npz\")\n    sets = json.loads((ROOT / \"data\" / \"mcode_sets.json\").read_text())[\"sets\"][\"PRIMARY\"]\n    keys = list(z[\"keys\"])\n    rows = [(keys.index(p[\"scrubbed_sha256\"]), a) for a in CANON if len(sets[a]) >= 10 for p in sets[a]]\n    ri = list(z[\"readouts\"]).index(\"R1\")\n    return z[\"R\"][[r[0] for r in rows], ri], np.array([r[1] for r in rows]), [int(b) for b in z[\"blocks\"]]\n\n\ndef main():\n    blocks = json.loads((ROOT / \"predictions\" / \"commit2.json\").read_text())[\"manifolds\"]\n    geo_all = json.loads((ROOT / \"results\" / \"geometry_all.json\").read_text())\n    out = {\"checks\": {}, \"mismatches\": []}\n    rng = np.random.default_rng(0)\n    for key in (\"32b|mname\", \"32b|mdesc\", \"32b|mlex\", \"32b|mcode_PRIMARY_R1\"):\n        if key not in geo_all or key not in blocks:\n            continue\n        model, name = key.split(\"|\")\n        name0 = \"mcode\" if name.startswith(\"mcode\") else name\n        X, labels, bl = load(model, name0)\n        L = blocks[key][\"L_star\"]\n        Xb = X[:, bl.index(L)].astype(np.float64)\n        geo, ncomp = knn_geodesics(Xb, 15)\n        g, cls = g_classes(geo, labels)\n        ref = geo_all[key][\"L_star\"][\"describe\"][\"k15\"]\n        maxdiff = max(abs(g[a] - ref[\"g\"][a]) for a in g)\n        same = cls == ref[\"classes\"]\n        plac = []\n        for _ in range(20):\n            lp = rng.permutation(labels)\n            _, cp = g_classes(geo, lp)\n            plac.append(cp.get(\"dijkstra_unit\") == cls.get(\"dijkstra_unit\"))\n        out[\"checks\"][key] = {\"block\": L, \"components\": ncomp, \"g\": g, \"classes\": cls, \"max_abs_g_diff\": maxdiff,\n                              \"classes_equal\": same, \"placebo_shuffled_labels_share_same_udij_class\":\n                                  float(np.mean(plac))}\n        if not same or maxdiff > 1e-6 * max(1.0, max(abs(v) for v in g.values())):\n            out[\"mismatches\"].append(key)\n        print(key, \"classes equal\", same, \"max |dg|\", maxdiff, \"placebo\", float(np.mean(plac)), flush=True)\n    (ROOT / \"results\" / \"audit_states.json\").write_text(json.dumps(out, indent=1))\n    return 0 if not out[\"mismatches\"] else 1\n\n\nif __name__ == \"__main__\":\n    sys.exit(main())\n=== cache\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_8b_mcode_PRIMARY_R1_k15.npz\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_8b_mcode_PRIMARY_R1_k10.npz\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/boot_8b_mcode_PRIMARY_R1_k10.npy\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/boot_8b_mcode_PRIMARY_R1_k15.npy\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_8b_mdesc_k15.npz\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_8b_mdesc_k10.npz\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/boot_8b_mdesc_k10.npy\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/boot_8b_mdesc_k15.npy\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_8b_mname_k15.npz\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_8b_mname_k10.npz\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/boot_8b_mname_k10.npy\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/boot_8b_mname_k15.npy\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_32b_mcode_M32_R1_k15.npz\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_32b_mcode_M32_R1_k10.npz\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/boot_32b_mcode_M32_R1_k10.npy\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/boot_32b_mcode_M32_R1_k15.npy\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_32b_mcode_PRIMARY_R2_k15.npz\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_32b_mcode_PRIMARY_R2_k10.npz\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/boot_32b_mcode_PRIMARY_R2_k10.npy\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/boot_32b_mcode_PRIMARY_R2_k15.npy\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_32b_mcode_PRIMARY_R1_k15.npz\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_32b_mcode_PRIMARY_R1_k10.npz\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/boot_32b_mcode_PRIMARY_R1_k10.npy\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/boot_32b_mcode_PRIMARY_R1_k15.npy\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_32b_mlex_k15.npz\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_32b_mlex_k10.npz\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/boot_32b_mlex_k10.npy\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/boot_32b_mlex_k15.npy\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_32b_mdesc_k15.npz\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_32b_mdesc_k10.npz\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/boot_32b_mdesc_k10.npy\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/boot_32b_mdesc_k15.npy\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/mcode_8b.npz\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/mcode_32b.npz\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/mdesc_8b.npz\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_32b_mname_k15.npz\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_32b_mname_k10.npz\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/boot_32b_mname_k10.npy\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/boot_32b_mname_k15.npy\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/mdesc_32b.npz\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/ban_8b.npz\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/mlex_8b.npz\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/mname_8b.npz\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/ban_32b.npz\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/mlex_32b.npz\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/mname_32b.npz\n79K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/boot_8b_mdesc_k10.npy\n79K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/boot_8b_mdesc_k15.npy\n79K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/boot_8b_mname_k10.npy\n79K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/boot_8b_mname_k15.npy\n391K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/boot_32b_mcode_PRIMARY_R1_k10.npy\n391K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/boot_32b_mcode_PRIMARY_R1_k15.npy\n391K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/boot_32b_mdesc_k10.npy\n391K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/boot_32b_mdesc_k15.npy\n391K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/boot_32b_mlex_k10.npy\n391K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/boot_32b_mlex_k15.npy\n391K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/boot_32b_mname_k10.npy\n391K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/boot_32b_mname_k15.npy\n1.1M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/ban_8b.npz\n1.2M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_32b_mcode_PRIMARY_R2_k10.npz\n1.2M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_32b_mcode_PRIMARY_R2_k15.npz\n1.2M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_8b_mcode_PRIMARY_R1_k10.npz\n1.2M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_8b_mcode_PRIMARY_R1_k15.npz\n1.4M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_32b_mcode_M32_R1_k10.npz\n1.4M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_32b_mcode_M32_R1_k15.npz\n1.5M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_32b_mcode_PRIMARY_R1_k10.npz\n1.5M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_32b_mcode_PRIMARY_R1_k15.npz\n2.0M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/ban_32b.npz\n3.0M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_8b_mdesc_k10.npz\n3.0M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_8b_mdesc_k15.npz\n3.5M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_32b_mdesc_k10.npz\n3.5M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_8b_mname_k10.npz\n3.5M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_8b_mname_k15.npz\n3.6M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_32b_mdesc_k15.npz\n4.2M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_32b_mlex_k10.npz\n4.2M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_32b_mlex_k15.npz\n4.2M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_32b_mname_k10.npz\n4.2M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/geo_32b_mname_k15.npz\n40M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/mdesc_8b.npz\n46M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/mname_8b.npz\n74M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/mdesc_32b.npz\n85M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/mname_32b.npz\n138M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/mlex_8b.npz\n191M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/mcode_8b.npz\n254M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/mlex_32b.npz\n352M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/cache/states/mcode_32b.npz", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [35] THINKING · 2026-10-26 14:23:52 UTC

```
I'll reuse iteration 8's `geometry.py`/`landing.py` and `stage_analysis.py` wrappers for the CPU-side code, then check the frozen per-manifold states at L* and the small model RDMs that the analysis reads.
```

### [36] TOOL CALL — Bash · 2026-10-26 14:23:52 UTC

```
Inspect frozen geodesic state files and selected blocks:
SRC=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46; cd /tmp && python3 - <<'EOF'
import numpy as np, json
SRC="/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46"
for f in ["geo_32b_mname_k15","geo_32b_mcode_PRIMARY_R1_k15","geo_32b_mdesc_k15","geo_32b_mlex_k15","geo_8b_mname_k15"]:
    z=np.load(f"{SRC}/cache/states/{f}.npz", allow_pickle=False)
    print(f, {k:(z[k].shape, z[k].dtype) for k in z.files})
    print("  block", z["block"], "readout", z["readout"], "labels uniq", np.unique(z["labels"], return_counts=True))
    print("  ids[:3]", z["point_ids"][:3])
c2=json.load(open(f"{SRC}/predictions/commit2.json"))
for k,v in c2["manifolds"].items(): print(k, v["L_star"], v["n_points"], round(v["best"],3))
EOF
```

### [37] TOOL RESULT — Bash · 2026-10-26 14:23:52 UTC

```
{"stdout": "geo_32b_mname_k15 {'geo': ((300, 300), dtype('float64')), 'adjacency': ((300, 300), dtype('float32')), 'X': ((300, 5120), dtype('float32')), 'labels': ((300,), dtype('<U13')), 'point_ids': ((300,), dtype('<U25')), 'block': ((), dtype('int64')), 'readout': ((), dtype('<U6')), 'standardised': ((), dtype('bool')), 'k': ((), dtype('int64'))}\n  block 31 readout S-mean labels uniq (array(['astar', 'bfs', 'biastar', 'bibfs', 'dfs', 'dijkstra_unit', 'gbfs',\n       'idastar', 'iddfs', 'jps'], dtype='<U13'), array([30, 30, 30, 30, 30, 30, 30, 30, 30, 30]))\n  ids[:3] ['mname|bfs|t0|j0' 'mname|bfs|t0|j1' 'mname|bfs|t0|j2']\ngeo_32b_mcode_PRIMARY_R1_k15 {'geo': ((117, 117), dtype('float64')), 'adjacency': ((117, 117), dtype('float32')), 'X': ((117, 5120), dtype('float32')), 'labels': ((117,), dtype('<U13')), 'point_ids': ((117,), dtype('<U27')), 'block': ((), dtype('int64')), 'readout': ((), dtype('<U2')), 'standardised': ((), dtype('bool')), 'k': ((), dtype('int64'))}\n  block 33 readout R1 labels uniq (array(['astar', 'bfs', 'dfs', 'dijkstra_unit', 'gbfs', 'idastar'],\n      dtype='<U13'), array([20, 20, 20, 20, 20, 17]))\n  ids[:3] ['S1|forced:bfs|0|7' 'S1|forced:bfs|2|7' 'S1|forced:bfs|0|0']\ngeo_32b_mdesc_k15 {'geo': ((260, 260), dtype('float64')), 'adjacency': ((260, 260), dtype('float32')), 'X': ((260, 5120), dtype('float32')), 'labels': ((260,), dtype('<U13')), 'point_ids': ((260,), dtype('<U28')), 'block': ((), dtype('int64')), 'readout': ((), dtype('<U6')), 'standardised': ((), dtype('bool')), 'k': ((), dtype('int64'))}\n  block 31 readout S-mean labels uniq (array(['astar', 'bfs', 'biastar', 'bibfs', 'dfs', 'dijkstra_unit', 'gbfs',\n       'idastar', 'iddfs'], dtype='<U13'), array([30, 30, 30, 20, 30, 30, 30, 30, 30]))\n  ids[:3] ['mdesc|bfs|D1|v0|t0' 'mdesc|bfs|D1|v0|t1' 'mdesc|bfs|D1|v0|t2']\ngeo_32b_mlex_k15 {'geo': ((300, 300), dtype('float64')), 'adjacency': ((300, 300), dtype('float32')), 'X': ((300, 5120), dtype('float32')), 'labels': ((300,), dtype('<U13')), 'point_ids': ((300,), dtype('<U24')), 'block': ((), dtype('int64')), 'readout': ((), dtype('<U6')), 'standardised': ((), dtype('bool')), 'k': ((), dtype('int64'))}\n  block 31 readout S-mean labels uniq (array(['astar', 'bfs', 'biastar', 'bibfs', 'dfs', 'dijkstra_unit', 'gbfs',\n       'idastar', 'iddfs', 'jps'], dtype='<U13'), array([30, 30, 30, 30, 30, 30, 30, 30, 30, 30]))\n  ids[:3] ['mlex|bfs|t0|j0' 'mlex|bfs|t0|j1' 'mlex|bfs|t0|j2']\ngeo_8b_mname_k15 {'geo': ((300, 300), dtype('float64')), 'adjacency': ((300, 300), dtype('float32')), 'X': ((300, 4096), dtype('float32')), 'labels': ((300,), dtype('<U13')), 'point_ids': ((300,), dtype('<U25')), 'block': ((), dtype('int64')), 'readout': ((), dtype('<U6')), 'standardised': ((), dtype('bool')), 'k': ((), dtype('int64'))}\n  block 17 readout S-mean labels uniq (array(['astar', 'bfs', 'biastar', 'bibfs', 'dfs', 'dijkstra_unit', 'gbfs',\n       'idastar', 'iddfs', 'jps'], dtype='<U13'), array([30, 30, 30, 30, 30, 30, 30, 30, 30, 30]))\n  ids[:3] ['mname|bfs|t0|j0' 'mname|bfs|t0|j1' 'mname|bfs|t0|j2']\n32b|mname 31 300 1.0\n32b|mdesc 31 260 1.0\n32b|mlex 31 300 1.0\n32b|mcode_PRIMARY_R1 33 117 0.942\n32b|mcode_PRIMARY_R2 21 117 0.897\n32b|mcode_M32_R1 31 113 0.983\n8b|mname 17 300 1.0\n8b|mdesc 17 260 1.0\n8b|mcode_PRIMARY_R1 17 117 0.925", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [38] TOOL CALL — Bash · 2026-10-26 14:23:52 UTC

```
Inspect lexical, behavioural, surface RDM and landing inputs:
SRC=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46; cd /tmp && python3 - <<'EOF'
import json
SRC="/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46"
lex=json.load(open(f"{SRC}/results/lexical.json")); print("lexical keys", list(lex.keys())); print(" aliases[0]", lex["aliases"][0]); print(" n aliases", len(lex["aliases"]))
beh=json.load(open(f"{SRC}/results/behavioural_distance.json")); print("beh keys", list(beh.keys()))
sur=json.load(open(f"{SRC}/results/surface_rdm.json")); print("surface keys", list(sur.keys()), list(sur["R_len"].keys()))
ms=json.load(open(f"{SRC}/data/mcode_sets.json")); print("mcode_sets keys", list(ms.keys())); print(" sets", list(ms["sets"].keys())); 
print(" placement n", len(ms["placement"]), "first keys", list(ms["placement"][0].keys()))
import collections
print(" placement sets", collections.Counter((p["set"], p["algorithm"]) for p in ms["placement"]))
p0=ms["sets"]["PRIMARY"]["bfs"][0]; print(" PRIMARY bfs[0] keys", list(p0.keys()))
import os
print(os.listdir(f"{SRC}/inputs/e44"))
print(os.listdir(f"{SRC}/inputs/e44/results")[:50])
land=json.load(open(f"{SRC}/inputs/e44/results/landing.json")); print("landing keys", list(land.keys())); print(" primary keys", list(land["primary"].keys()))
print(" null_C_probs", land["primary"]["null_C_probs"])
EOF
ls -la $SRC/inputs/e44/data | head -30
```

### [39] TOOL RESULT — Bash · 2026-10-26 14:23:52 UTC

```
{"stdout": "lexical keys ['aliases', 'R_lex', 'algorithms', 'L1_nonbanned', 'expected_L1', 'L1_matches_expected']\n aliases[0] {'algorithm': 'bfs', 'alias_index': 0, 'alias': 'breadth-first search (BFS)', 'L1': 1, 'L2': 0.5333333333333333, 'L3': 0.4444444444444444, 'n_tokens': 7, 'banned': True}\n n aliases 30\nbeh keys ['algorithms', 'references', 'd_order', 'd_DS', 'd_beh_lambda0.0', 'd_beh_lambda0.5', 'd_beh_lambda1.0', 'behavioural_g', 'behavioural_nearest_banned', 'behavioural_classes', 'P6_d_beh_to_bfs', 'P6_udij_nearest_to_bfs', 'behavioural_coordinates_mds', 'behavioural_mds_stress1', 'program_level_d_order', 'program_level_d_DS', 'reference_flags', 'g_tracer_pass']\nsurface keys ['R_surface', 'R_len', 'lengths'] ['mname', 'mlex', 'mdesc', 'mcode']\nmcode_sets keys ['sets', 'counts', 'excluded_lt_min', 'placement', 'utc', 'source_mix_primary']\n sets ['PRIMARY', 'M32', 'M8']\n placement n 113 first keys ['source', 'author', 'algorithm', 'uid', 'condition', 'scrubbed', 'scrubbed_sha256', 'rename_map', 'ds_flags', 'lexical_flag', 'runtime_label', 'ast_label', 'g_scrub_pass', 'set', 'other_name', 'arm', 'template', 'provider', 'seed', 'code_sha256', 'context_variant']\n placement sets Counter({('BASE', 'bfs'): 50, ('SURV', 'other'): 23, ('SURV', 'dijkstra_unit'): 15, ('DISOBEY', 'dfs'): 15, ('DISOBEY', 'gbfs'): 6, ('DISOBEY', 'bfs'): 4})\n PRIMARY bfs[0] keys ['source', 'author', 'algorithm', 'uid', 'condition', 'scrubbed', 'scrubbed_sha256', 'rename_map', 'ds_flags', 'lexical_flag', 'runtime_label', 'ast_label', 'g_scrub_pass', 'set', 'other_name', 'arm', 'template', 'provider', 'seed', 'code_sha256', 'context_variant']\n['commitments.log', 'reproducibility.md', 'pyproject.toml', 'states', 'data', 'results']\n['deviations.json', 'selection.json', 'screen.json', 'confirmation.json', 'states_C1_bf16.json', 'states_C6_nf4.json', 'renderer_checks.json', 't8_synthetic.json', 'quant_check.json', 'landing_robustness.json', 'landing.json', 'geometry_M1.json']\nlanding keys ['config', 'mode', 'L_star', 'k', 'survivors', 'n_surv', 'primary', 'attempted', 'euclid_centroid', 'standardised', 'forced_rates_source', 'descriptive_only', 'note']\n primary keys ['n_surv', 'survivor_counts', 'g', 'classes', 'S', 'nulls', 'null_F_probs', 'null_F_near_uniform', 'null_C_probs', 'class_shares', 'verdict', 'descriptive_only', 'perm_floor']\n null_C_probs {'bibfs': 0.1375, 'dijkstra_unit': 0.28750000000000003, 'idastar': 0.0125, 'jps': 0.0125, 'biastar': 0.0125}\ntotal 10865\ndrwxrwxrwx 2 aii-agent aii-agent 2000679 Oct 23 10:24 .\ndrwxrwxrwx 5 aii-agent aii-agent 2000879 Oct 23 10:24 ..\n-rw-rw-rw- 1 aii-agent aii-agent 2020632 Oct 23 04:18 labelled_C6_ban.jsonl\n-rw-rw-rw- 1 aii-agent aii-agent 3203647 Oct 23 03:46 labelled_C6_baseline.jsonl\n-rw-rw-rw- 1 aii-agent aii-agent 1894353 Oct 23 05:20 labelled_C6_confirm.jsonl\n-rw-rw-rw- 1 aii-agent aii-agent    3978 Oct 23 04:18 manual_reads.jsonl", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [40] THINKING · 2026-10-26 14:24:44 UTC

```
I'll set up a local exploration venv on scratch disk to test subsampling designs against the full-data CPU analysis results on the precomputed Qwen3-32B states.
```

### [41] TOOL CALL — Bash · 2026-10-26 14:24:44 UTC

```
Create exploration venv with Colab-pinned packages:
SP=/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-VVA3P0ocZNA2/39a5c6e0-c154-4645-bb18-199862447326/scratchpad; mkdir -p $SP && cd $SP && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --python /usr/local/bin/python3.12 $SP/venv && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python $SP/venv/bin/python numpy==2.0.2 scipy==1.16.3 scikit-learn==1.6.1 matplotlib==3.10.0 networkx==3.6.1 loguru==0.7.3 && $SP/venv/bin/python -c "import numpy, scipy, sklearn, matplotlib, networkx, loguru; print('ok', numpy.__version__, scipy.__version__, sklearn.__version__)"; nproc; free -g | head -2
```

### [42] TOOL RESULT — Bash · 2026-10-26 14:24:48 UTC

```
{"stdout": "ok 2.0.2 1.16.3 1.6.1\n2\n               total        used        free      shared  buff/cache   available\nMem:             755          87          81           0         592         667", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [43] ASSISTANT · 2026-10-26 14:25:02 UTC

```
Only 2 CPUs here, so runtimes must be measured with that in mind. Next I'll check `common.py`, which `geometry.py` imports `CANON_ORDER` from, and the group encoding in the state files.
```

### [44] TOOL CALL — Bash · 2026-10-26 14:25:02 UTC

```
Read top of common.py and wilson_ci helper:
SRC=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46; sed -n 1,80p $SRC/src/common.py; grep -n "def wilson_ci" -A 12 $SRC/src/common.py
```

### [45] TOOL RESULT — Bash · 2026-10-26 14:25:02 UTC

````
{"stdout": "#!/usr/bin/env python3\n\"\"\"Frozen protocol, paths and shared helpers for the iteration-8 top-five ban screen (gen_plan_experiment_6_idx7).\n\nOne definition of: the T1 task spec, the 10-algorithm catalogue (display names, canonical order, judge definitions),\nthe alias table for forced prompts, the W1-W5 + P6/P7 ban templates, the screen configurations C1-C10, the selection\nrule, hash-chained commitments, Wilson / Newcombe intervals, the deviation log and the OpenRouter cost ledger.\nPrior-iteration files are read only from inputs/ (copied with sha256 at Stage 0) and vendor/exp9/ (harness +\nlabeller, copied read-only from ITER2 exp9).\n\"\"\"\n\nfrom __future__ import annotations\n\nimport fcntl\nimport hashlib\nimport json\nimport math\nimport os\nimport re\nimport sys\nfrom datetime import datetime, timezone\nfrom pathlib import Path\nfrom typing import Any, Iterable\n\nfrom loguru import logger\n\nROOT = Path(__file__).resolve().parent.parent\nSRC = ROOT / \"src\"\nINPUTS = ROOT / \"inputs\"\nVENDOR = ROOT / \"vendor\" / \"exp9\"\nDATA = ROOT / \"data\"\nRESULTS = ROOT / \"results\"\nFIGS = ROOT / \"figures\"\nPRED = ROOT / \"predictions\"\nLOGS = ROOT / \"logs\"\nCACHE = ROOT / \"cache\"\nSTATES = CACHE / \"states\"\nCOMMIT_LOG = ROOT / \"commitments.log\"\nfor _d in (INPUTS, DATA, RESULTS, FIGS, PRED, LOGS, STATES):\n    _d.mkdir(parents=True, exist_ok=True)\n\n# ---------------------------------------------------------------------------------------------- prior-artifact inputs\n# Read ONLY at Stage 0, then copied into inputs/ (with inputs/SHA256SUMS); every later stage reads inputs/ and vendor/.\n# Each input artifact is located through ONE environment variable TP_DEP_<KEY>; by default it is the sibling folder\n# named by its artifact id under TP_DEPS_DIR (default: the folder that contains this artifact, which is how the\n# published repository lays out sibling artifacts). Stage 0 skips the copy when inputs/SHA256SUMS already verifies.\nDEPS_DIR = Path(os.environ.get(\"TP_DEPS_DIR\", str(ROOT.parent)))\nDEP_ARTIFACT_IDS = {\n    \"exp9\": \"art_IVZc3TWCeE9f\",      # ITER2 gen_art_experiment_9: T1 task, harness, 10-class labeller, frozen prompts\n    \"exp2\": \"art_D6Z0Snf09sFL\",      # ITER1 gen_art_experiment_2: secondary hidden suite (hidden_tests_t1.json)\n    \"exp34\": \"art_pHL7LWNhpcCS\",     # ITER7 gen_art_experiment_34: top5geo.py, top5_geometry.json, known corpus\n    \"exp29\": \"art_lpQalcAXMGr1\",     # ITER6 gen_art_experiment_29: known_solutions.json\n    \"exp31\": \"art_zNyBP6zieI5u\",     # ITER6 gen_art_experiment_31: gemma-3-4b-it TOP5 row (carried C10)\n    \"exp18\": \"gen_art_experiment_18\",  # ITER3 gen_art_experiment_18: known_solutions_summary.json (id not recorded)\n    \"dataset\": \"art_j3Rm_lr2nzR6\",   # declared dependency: algorithm-choice source data (full_data_out.json)\n}\nSRC_PATHS = {k: Path(os.environ.get(f\"TP_DEP_{k.upper()}\", str(DEPS_DIR / v))) for k, v in DEP_ARTIFACT_IDS.items()}\nDS_FILE = INPUTS / \"dataset\" / \"full_data_out.json\"\n\n# ---------------------------------------------------------------------------------------------- frozen task protocol\nT1_DESCRIPTION = (\n    \"Task: write a Python function solve(grid, start, goal) that finds a path between two cells of a grid. \"\n    \"grid is a list of equal-length strings with between 1 and 30 rows and between 1 and 30 columns; \"\n    \"the character . is a free cell and the character # is a wall. start and goal are (row, col) tuples of \"\n    \"0-based indices. A move goes to one of the 4 orthogonal neighbours (up, down, left, right) and may not \"\n    \"leave the grid or enter a wall. Return a list of (row, col) tuples that begins with start, ends with goal, \"\n    \"and in which consecutive cells are neighbours and every cell is free. Any valid path is accepted; it does \"\n    \"not have to be the shortest. If start equals goal and the cell is free, return [start]. If no path exists, \"\n    \"or start or goal is a wall, return [].\"\n)\nFORMAT_TEXT = (\n    \"Use only the Python standard library. Return only one ```python code block containing the function solve \"\n    \"and any helpers, with no example usage and no explanation.\"\n)\n\nCANON_ORDER = [\"bfs\", \"dfs\", \"bibfs\", \"iddfs\", \"astar\", \"gbfs\", \"dijkstra_unit\", \"idastar\", \"jps\", \"biastar\"]\nDISPLAY = {\n    \"bfs\": \"breadth-first search (BFS)\", \"dfs\": \"depth-first search (DFS)\", \"bibfs\": \"bidirectional BFS\",\n    \"iddfs\": \"iterative deepening DFS (IDDFS)\", \"astar\": \"A* search\", \"gbfs\": \"greedy best-first search\",\n    \"dijkstra_unit\": \"unit-weight Dijkstra\", \"idastar\": \"IDA* search\", \"jps\": \"jump point search\",\n    \"biastar\": \"bidirectional A* search\",\n328:def wilson_ci(k: int, n: int, z: float = Z95) -> tuple[float, float]:\n329-    if n <= 0:\n330-        return (float(\"nan\"), float(\"nan\"))\n331-    p = k / n\n332-    den = 1 + z * z / n\n333-    centre = (p + z * z / (2 * n)) / den\n334-    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den\n335-    return (max(0.0, centre - half), min(1.0, centre + half))\n336-\n337-\n338-def wilson_upper_one_sided(k: int, n: int) -> float:\n339-    \"\"\"One-sided 95% upper bound (Wilson with z = 1.645).\"\"\"\n340-    return wilson_ci(k, n, z=1.6448536269514722)[1]", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
````

### [46] TOOL CALL — Bash · 2026-10-26 14:25:02 UTC

```
Inspect M-name and M-code state file arrays:
SP=/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-VVA3P0ocZNA2/39a5c6e0-c154-4645-bb18-199862447326/scratchpad; cd $SP && $SP/venv/bin/python -B - <<'EOF'
import numpy as np, json
SRC="/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46"
z=np.load(f"{SRC}/cache/states/mname_32b.npz")
print(z.files)
for k in z.files:
    if k!="smean": print(k, z[k].shape, z[k].dtype, z[k][:12])
print("smean", z["smean"].shape, z["smean"].dtype)
zc=np.load(f"{SRC}/cache/states/mcode_32b.npz")
print(zc.files)
for k in zc.files:
    if k!="R": print(k, zc[k].shape, zc[k].dtype, zc[k][:6])
print("R", zc["R"].shape, zc["R"].dtype)
EOF
```

### [47] TOOL RESULT — Bash · 2026-10-26 14:25:04 UTC

```
{"stdout": "['smean', 'blocks', 'algorithm', 'group', 'template', 'alias', 'prompt_sha256']\nblocks (31,) int64 [17 18 19 20 21 22 23 24 25 26 27 28]\nalgorithm (300,) <U13 ['bfs' 'bfs' 'bfs' 'bfs' 'bfs' 'bfs' 'bfs' 'bfs' 'bfs' 'bfs' 'bfs' 'bfs']\ngroup (300,) int64 [ 0  1  2  3  4  5  6  7  8  9 10 11]\ntemplate (300,) int64 [0 0 0 1 1 1 2 2 2 3 3 3]\nalias (300,) int64 [0 1 2 0 1 2 0 1 2 0 1 2]\nprompt_sha256 (300,) <U64 ['8c6642e4ac24ea81d8bd3369de636ddcec887b1928f4a8b2eeb00c62939e7740'\n 'da598793d8a7c0d20797eca4e29072b55e460a49c6fa129a1d0232860d5e0bc8'\n '025257d07aa12ac8ce7a0be97228bf04d1fc9c4bcaa57ed3e3e6cdfac74de901'\n 'e307fed118d66fa14f1369907efe296e74896128a439894fd8d51f31b06faafe'\n '18bed859c063fc7267b5ef8f4b4ffbf54225553fd3d8995e3a107f5dff8bb8ae'\n '2cd91ac6c3d49104bf62243468928d24315748f137ba3d5882c80fe61c0e7a3f'\n '5ff3b872d76e5192599c25642585de451d74187230efe5ad4c2c5d489daf7852'\n '9c41860c93b1f2a1f6ebf059cb7525a60d8fc995a431fb9c246a8b1a9e53cc02'\n '14f39625680f237ddc9ecb73ed9296e89a974cb4c669f7f084a0c64c8e210da1'\n '86c5fdb83e1f66e76bb3bbb46329ca916a9b19b2b0c797025416b44d378958c5'\n '6de407903a109463dfcc79c882a903511f520bbd0dcbfbe592439bc2172cd3a6'\n 'b071a7292b66195053251e791b8941a00b35930316b184044f1b1c40fd36a9e0']\nsmean (300, 31, 5120) float16\n['R', 'blocks', 'keys', 'algorithm', 'readouts']\nblocks (31,) int64 [17 18 19 20 21 22]\nkeys (341,) <U64 ['9094a4b79e0b42fa6eabf9bc3ccc413dd4421232dc5ef129b6a3e88122e4cfc4'\n '803666b048146bc28cecd48a98f81edc5c53e71d7e3410c545ef017d5666623b'\n '47af29fd4ebb09c0c0926d1d1c94f0b7ea5584a958f426b498fec24ec96fce30'\n '1988860ca1430f15aef76e0fa73e957101edb123ac5582028f75adc60eac0f33'\n 'c62500ad8d96bc382a73f430130b2622e3232b3ba76ec5b961ca4192e5224a23'\n 'd5be06f581e9eb4a31df77f80562da7e80956fededfed1f8fda5f1c1f784f465']\nalgorithm (341,) <U13 ['bfs' 'bfs' 'bfs' 'bfs' 'bfs' 'bfs']\nreadouts (4,) <U3 ['R1' 'R1g' 'R2' 'R3']\nR (341, 4, 31, 5120) float16", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [48] THINKING · 2026-10-26 14:25:42 UTC

```
The float16 base64 encoding preserves state data exactly at ~1.4 MB per 100 points. Next, I'll test which 100-point subsample of M-name, M-code, and survivors reproduces the full-data unit-Dijkstra classes using the unchanged geometry code.
```

### [49] TOOL CALL — Bash · 2026-10-26 14:25:42 UTC

```
Test M-name subsample designs against the full result:
SP=/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-VVA3P0ocZNA2/39a5c6e0-c154-4645-bb18-199862447326/scratchpad; mkdir -p $SP/fake && cat > $SP/fake/common.py <<'EOF'
CANON_ORDER = ["bfs", "dfs", "bibfs", "iddfs", "astar", "gbfs", "dijkstra_unit", "idastar", "jps", "biastar"]
EOF
cat > $SP/explore1.py <<'EOF'
import sys, json, time
sys.path.insert(0, sys.argv[1] + "/fake")
sys.path.insert(1, "/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src")
import numpy as np
import geometry
SRC = "/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46"
B5 = ["bfs", "dfs", "iddfs", "astar", "gbfs"]; NB5 = ["bibfs", "biastar", "idastar", "jps", "dijkstra_unit"]; UDIJ = "dijkstra_unit"
CANON = geometry.CANON_ORDER
def summary(X, labels, ks=(5, 10, 15)):
    present = set(labels.tolist()); nb = [a for a in NB5 if a in present]; bp = [b for b in B5 if b in present]
    out = {}
    for k in ks:
        geo, info = geometry.geodesics(X, k)
        g, near = geometry.g_values(geo, labels, bp, nb)
        cls, med = geometry.classify(g)
        rank = sorted(nb, key=lambda a: g[a]).index(UDIJ) + 1
        out[k] = (cls[UDIJ], rank, round(g[UDIJ] / med, 2), near[UDIJ], info["components_before_join"])
    return out
zn = np.load(f"{SRC}/cache/states/mname_32b.npz")
blocks = [int(b) for b in zn["blocks"]]
Xn_all = zn["smean"][:, blocks.index(31)].astype(np.float64)
ln, gn, tn, an = zn["algorithm"], zn["group"].astype(int), zn["template"], zn["alias"]
t0 = time.time()
print("FULL mname", summary(Xn_all, ln), round(time.time() - t0, 2), "s")
for temps in [(0,), (0, 1), (0, 1, 2), (3, 4), (5, 6), (8, 9), (0, 5)]:
    m = np.isin(tn, temps)
    print("mname templates", temps, int(m.sum()), summary(Xn_all[m], ln[m]))
# 5 per alg: templates (0,1) aliases (0,1,2) minus one alias
for sel in [((0, 1), (0, 1)), ((0, 1, 2), (0,)), ((0, 1, 2, 3, 4), (0,)), ((0,1,2,3,4),(1,)), ((0,1,2,3,4),(2,))]:
    m = np.isin(tn, sel[0]) & np.isin(an, sel[1])
    print("mname t", sel[0], "a", sel[1], int(m.sum()), summary(Xn_all[m], ln[m]))
EOF
cd $SP && $SP/venv/bin/python -B explore1.py $SP 2>&1 | grep -v "^\s*$"
```

### [50] TOOL RESULT — Bash · 2026-10-26 14:25:42 UTC

```
{"stdout": "FULL mname {5: ('MIDDLE', 3, 1.0, 'iddfs', 8), 10: ('OPPOSITE', 5, 1.78, 'iddfs', 3), 15: ('OPPOSITE', 5, 1.63, 'astar', 1)} 0.19 s\nmname templates (0,) 30 {5: ('OPPOSITE', 4, 1.0, 'astar', 1), 10: ('OPPOSITE', 4, 1.12, 'astar', 1), 15: ('OPPOSITE', 4, 1.15, 'astar', 1)}\nmname templates (0, 1) 60 {5: ('OPPOSITE', 4, 1.18, 'astar', 1), 10: ('OPPOSITE', 4, 1.01, 'astar', 1), 15: ('OPPOSITE', 4, 1.09, 'astar', 1)}\nmname templates (0, 1, 2) 90 {5: ('OPPOSITE', 5, 1.78, 'astar', 3), 10: ('OPPOSITE', 4, 1.1, 'astar', 1), 15: ('OPPOSITE', 4, 1.07, 'astar', 1)}\nmname templates (3, 4) 60 {5: ('OPPOSITE', 4, 1.26, 'astar', 2), 10: ('OPPOSITE', 4, 1.02, 'astar', 1), 15: ('OPPOSITE', 4, 1.08, 'astar', 1)}\nmname templates (5, 6) 60 {5: ('OPPOSITE', 4, 1.09, 'astar', 1), 10: ('OPPOSITE', 4, 1.04, 'astar', 1), 15: ('OPPOSITE', 4, 1.08, 'astar', 1)}\nmname templates (8, 9) 60 {5: ('OPPOSITE', 5, 1.46, 'astar', 1), 10: ('OPPOSITE', 4, 1.15, 'astar', 1), 15: ('OPPOSITE', 4, 1.09, 'astar', 1)}\nmname templates (0, 5) 60 {5: ('OPPOSITE', 4, 1.29, 'astar', 2), 10: ('OPPOSITE', 4, 1.03, 'astar', 1), 15: ('OPPOSITE', 4, 1.09, 'astar', 1)}\nmname t (0, 1) a (0, 1) 40 {5: ('OPPOSITE', 4, 1.07, 'astar', 1), 10: ('OPPOSITE', 4, 1.14, 'astar', 1), 15: ('OPPOSITE', 5, 1.14, 'astar', 1)}\nmname t (0, 1, 2) a (0,) 30 {5: ('OPPOSITE', 5, 1.29, 'astar', 2), 10: ('OPPOSITE', 4, 1.23, 'astar', 1), 15: ('OPPOSITE', 5, 1.19, 'astar', 1)}\nmname t (0, 1, 2, 3, 4) a (0,) 50 {5: ('OPPOSITE', 5, 1.29, 'astar', 2), 10: ('OPPOSITE', 4, 1.11, 'astar', 1), 15: ('OPPOSITE', 4, 1.13, 'astar', 1)}\nmname t (0, 1, 2, 3, 4) a (1,) 50 {5: ('OPPOSITE', 4, 1.1, 'astar', 2), 10: ('OPPOSITE', 4, 1.13, 'astar', 1), 15: ('OPPOSITE', 4, 1.17, 'astar', 1)}\nmname t (0, 1, 2, 3, 4) a (2,) 50 {5: ('MIDDLE', 3, 1.0, 'astar', 1), 10: ('MIDDLE', 3, 1.0, 'astar', 1), 15: ('MIDDLE', 3, 1.0, 'astar', 1)}", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [51] THINKING · 2026-10-26 14:26:08 UTC

```
M-name holds up: every 60-point template subset (2 templates × 3 aliases × 10 algorithms) still puts unit Dijkstra OPPOSITE at k = 5, 10, and 15, matching the full 300-point result. Next I'll test M-code frame subsets and the 15 survivor placements.
```

### [52] TOOL CALL — Bash · 2026-10-26 14:26:08 UTC

```
Test M-code frame subsamples and survivor placement:
SP=/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-VVA3P0ocZNA2/39a5c6e0-c154-4645-bb18-199862447326/scratchpad; cat > $SP/explore2.py <<'EOF'
import sys, json, time
sys.path.insert(0, sys.argv[1] + "/fake")
sys.path.insert(1, "/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src")
import numpy as np
import geometry
SRC = "/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46"
B5 = ["bfs", "dfs", "iddfs", "astar", "gbfs"]; NB5 = ["bibfs", "biastar", "idastar", "jps", "dijkstra_unit"]; UDIJ = "dijkstra_unit"
CANON = geometry.CANON_ORDER
def summary(X, labels, ks=(5, 10, 15)):
    present = set(labels.tolist()); nb = [a for a in NB5 if a in present]; bp = [b for b in B5 if b in present]
    out = {}
    for k in ks:
        geo, info = geometry.geodesics(X, k)
        g, near = geometry.g_values(geo, labels, bp, nb)
        cls, med = geometry.classify(g)
        rank = sorted(nb, key=lambda a: g[a]).index(UDIJ) + 1
        out[k] = (cls[UDIJ], rank, round(g[UDIJ] / med, 2), near[UDIJ], info["components_before_join"])
    return out
def oos(x, F, geo, k):
    d = np.linalg.norm(F - x, axis=1); nn = np.argsort(d)[:k]
    return np.min(d[nn][:, None] + geo[nn], axis=0)
z = np.load(f"{SRC}/cache/states/mcode_32b.npz")
keys = list(z["keys"]); ri = list(z["readouts"]).index("R1"); bi = [int(b) for b in z["blocks"]].index(33)
R = z["R"][:, ri, bi].astype(np.float64)
ms = json.load(open(f"{SRC}/data/mcode_sets.json"))
rows = []
for a in CANON:
    prog = ms["sets"]["PRIMARY"][a]
    if len(prog) < 10: continue
    for rank, p in enumerate(prog):
        rows.append((keys.index(p["scrubbed_sha256"]), a, rank % 10, p["uid"], rank))
idx = np.array([r[0] for r in rows]); lab = np.array([r[1] for r in rows]); grp = np.array([r[2] for r in rows]); rk = np.array([r[4] for r in rows])
F_all = R[idx]
print("FULL mcode", len(F_all), summary(F_all, lab))
surv = [p for p in ms["placement"] if p["set"] == "SURV" and p["algorithm"] == UDIJ]
print("n surv", len(surv), [p["uid"] for p in surv])
def place(F, lab, k):
    geo, _ = geometry.geodesics(F, k)
    nb = [a for a in NB5 if a in set(lab.tolist())]
    g, _ = geometry.g_values(geo, lab, [b for b in B5 if b in set(lab.tolist())], nb)
    cls, med = geometry.classify(g)
    res = []
    for p in surv:
        x = R[keys.index(p["scrubbed_sha256"])]
        dv = oos(x, F, geo, k)
        means = {a: float(dv[lab == a].mean()) for a in sorted(set(lab.tolist()))}
        gb = {b: means[b] for b in B5 if b in means}; gx = min(gb.values())
        res.append(("E" if gx < med else "O", min(means, key=means.get)[:4]))
    return res
print("FULL placement k15", place(F_all, lab, 15))
for nmax in (4, 5, 6, 7, 8):
    m = rk < nmax
    print("mcode ranks <", nmax, int(m.sum()), summary(F_all[m], lab[m]))
    for k in (10, 15):
        pl = place(F_all[m], lab[m], k)
        print("   placement k", k, sum(c == "E" for c, _ in pl), "/", len(pl), pl)
EOF
cd $SP && $SP/venv/bin/python -B explore2.py $SP 2>&1 | grep -v "^\s*$"
```

### [53] TOOL RESULT — Bash · 2026-10-26 14:26:10 UTC

```
{"stdout": "FULL mcode 117 {5: ('EDGE', 1, 0.73, 'gbfs', 5), 10: ('EDGE', 1, 0.64, 'gbfs', 3), 15: ('EDGE', 1, 0.67, 'gbfs', 1)}\nn surv 15 ['C6|ban|7', 'C6|ban|18', 'C6|ban|31', 'C6|ban|41', 'C6|ban|44', 'C6|ban|49', 'C6|confirm|14', 'C6|confirm|16', 'C6|confirm|19', 'C6|confirm|31', 'C6|confirm|32', 'C6|confirm|34', 'C6|confirm|39', 'C6|confirm|42', 'C6|confirm|48']\nFULL placement k15 [('E', 'dijk'), ('E', 'dijk'), ('E', 'dijk'), ('E', 'dijk'), ('E', 'dijk'), ('E', 'dijk'), ('E', 'gbfs'), ('E', 'dijk'), ('E', 'dijk'), ('E', 'dijk'), ('E', 'dijk'), ('E', 'dijk'), ('E', 'dijk'), ('E', 'dijk'), ('E', 'gbfs')]\nmcode ranks < 4 24 {5: ('EDGE', 1, 0.64, 'gbfs', 1), 10: ('EDGE', 1, 0.7, 'gbfs', 1), 15: ('EDGE', 1, 0.71, 'gbfs', 1)}\n   placement k 10 14 / 15 [('O', 'asta'), ('E', 'gbfs'), ('E', 'gbfs'), ('E', 'gbfs'), ('E', 'gbfs'), ('E', 'gbfs'), ('E', 'gbfs'), ('E', 'asta'), ('E', 'asta'), ('E', 'asta'), ('E', 'asta'), ('E', 'dijk'), ('E', 'asta'), ('E', 'asta'), ('E', 'gbfs')]\n   placement k 15 10 / 15 [('O', 'asta'), ('E', 'dijk'), ('E', 'gbfs'), ('E', 'dijk'), ('E', 'dijk'), ('E', 'dijk'), ('E', 'gbfs'), ('E', 'asta'), ('O', 'asta'), ('E', 'asta'), ('O', 'asta'), ('E', 'dijk'), ('O', 'asta'), ('O', 'asta'), ('E', 'gbfs')]\nmcode ranks < 5 30 {5: ('EDGE', 1, 0.67, 'gbfs', 1), 10: ('EDGE', 1, 0.74, 'gbfs', 1), 15: ('EDGE', 1, 0.7, 'gbfs', 1)}\n   placement k 10 12 / 15 [('E', 'asta'), ('E', 'dijk'), ('E', 'gbfs'), ('E', 'dijk'), ('E', 'gbfs'), ('E', 'dijk'), ('E', 'asta'), ('E', 'asta'), ('E', 'asta'), ('E', 'asta'), ('O', 'gbfs'), ('E', 'gbfs'), ('O', 'gbfs'), ('O', 'asta'), ('E', 'gbfs')]\n   placement k 15 11 / 15 [('O', 'asta'), ('E', 'dijk'), ('E', 'gbfs'), ('E', 'dijk'), ('E', 'dijk'), ('E', 'dijk'), ('E', 'dijk'), ('E', 'asta'), ('O', 'asta'), ('E', 'asta'), ('O', 'asta'), ('E', 'dijk'), ('E', 'gbfs'), ('O', 'asta'), ('E', 'gbfs')]\nmcode ranks < 6 36 {5: ('EDGE', 1, 0.59, 'gbfs', 2), 10: ('EDGE', 1, 0.7, 'gbfs', 1), 15: ('EDGE', 1, 0.72, 'gbfs', 1)}\n   placement k 10 15 / 15 [('E', 'asta'), ('E', 'dijk'), ('E', 'asta'), ('E', 'dijk'), ('E', 'asta'), ('E', 'dijk'), ('E', 'asta'), ('E', 'asta'), ('E', 'asta'), ('E', 'asta'), ('E', 'asta'), ('E', 'dijk'), ('E', 'gbfs'), ('E', 'asta'), ('E', 'gbfs')]\n   placement k 15 11 / 15 [('O', 'asta'), ('E', 'gbfs'), ('O', 'gbfs'), ('E', 'dijk'), ('E', 'dijk'), ('E', 'dijk'), ('E', 'gbfs'), ('E', 'asta'), ('E', 'asta'), ('E', 'asta'), ('O', 'gbfs'), ('E', 'dijk'), ('E', 'gbfs'), ('O', 'asta'), ('E', 'gbfs')]\nmcode ranks < 7 42 {5: ('EDGE', 1, 0.58, 'gbfs', 3), 10: ('EDGE', 1, 0.67, 'gbfs', 1), 15: ('EDGE', 1, 0.72, 'gbfs', 1)}\n   placement k 10 14 / 15 [('E', 'asta'), ('E', 'dijk'), ('E', 'asta'), ('E', 'asta'), ('E', 'gbfs'), ('E', 'dijk'), ('E', 'asta'), ('E', 'asta'), ('E', 'asta'), ('E', 'asta'), ('E', 'asta'), ('E', 'dijk'), ('O', 'asta'), ('E', 'asta'), ('E', 'gbfs')]\n   placement k 15 9 / 15 [('O', 'asta'), ('E', 'gbfs'), ('O', 'asta'), ('E', 'dijk'), ('O', 'gbfs'), ('E', 'gbfs'), ('E', 'asta'), ('E', 'asta'), ('E', 'asta'), ('E', 'asta'), ('O', 'asta'), ('E', 'dijk'), ('O', 'gbfs'), ('O', 'asta'), ('E', 'gbfs')]\nmcode ranks < 8 48 {5: ('EDGE', 1, 0.59, 'gbfs', 3), 10: ('EDGE', 1, 0.7, 'gbfs', 1), 15: ('EDGE', 1, 0.71, 'gbfs', 1)}\n   placement k 10 14 / 15 [('E', 'asta'), ('E', 'dijk'), ('E', 'asta'), ('E', 'dijk'), ('E', 'gbfs'), ('E', 'dijk'), ('E', 'asta'), ('E', 'asta'), ('E', 'asta'), ('E', 'gbfs'), ('E', 'asta'), ('E', 'dijk'), ('O', 'dijk'), ('E', 'asta'), ('E', 'gbfs')]\n   placement k 15 11 / 15 [('E', 'asta'), ('E', 'gbfs'), ('E', 'asta'), ('E', 'dijk'), ('O', 'dijk'), ('E', 'dijk'), ('E', 'asta'), ('E', 'asta'), ('E', 'asta'), ('E', 'asta'), ('O', 'asta'), ('E', 'dijk'), ('O', 'gbfs'), ('O', 'asta'), ('E', 'gbfs')]", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [54] THINKING · 2026-10-26 14:26:56 UTC

```
The M-code frame holds EDGE rank 1 across subsample sizes, though survivor placement weakens as the frame shrinks (9–15 of 15 EDGE). I'll now compare two 99-point designs across all headline statistics—classes, RSA ρ, lexical P4, placement, and LOO—before choosing.
```

### [55] TOOL CALL — Bash · 2026-10-26 14:26:56 UTC

```
Compare two 99-point demo designs on headline stats:
SP=/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-VVA3P0ocZNA2/39a5c6e0-c154-4645-bb18-199862447326/scratchpad; cat > $SP/explore3.py <<'EOF'
import sys, json, time
sys.path.insert(0, sys.argv[1] + "/fake")
sys.path.insert(1, "/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src")
import numpy as np
from scipy.stats import spearmanr
import geometry
SRC = "/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46"
B5 = ["bfs", "dfs", "iddfs", "astar", "gbfs"]; NB5 = ["bibfs", "biastar", "idastar", "jps", "dijkstra_unit"]; UDIJ = "dijkstra_unit"
CANON = geometry.CANON_ORDER
lex = json.load(open(f"{SRC}/results/lexical.json")); beh = json.load(open(f"{SRC}/results/behavioural_distance.json")); sur = json.load(open(f"{SRC}/results/surface_rdm.json"))
RD = {"R_lex": np.array(lex["R_lex"]), "R_beh": np.array(beh["d_beh_lambda0.5"]), "R_surface": np.array(sur["R_surface"])}
lx = {(r["algorithm"], r["alias_index"]): r for r in lex["aliases"]}
def rsa(geo, labels):
    M = geometry.class_matrix(geo, labels, CANON); M = (M + M.T) / 2
    present = [i for i, a in enumerate(CANON) if a in set(labels.tolist())]
    Mn = M[np.ix_(present, present)]; iu = np.triu_indices(len(present), 1)
    return {k: round(float(spearmanr(Mn[iu], R[np.ix_(present, present)][iu]).statistic), 2) for k, R in RD.items()}
def summ(X, labels, alias=None):
    present = set(labels.tolist()); nb = [a for a in NB5 if a in present]; bp = [b for b in B5 if b in present]
    out = {}
    for k in (10, 15):
        geo, info = geometry.geodesics(X, k)
        g, near = geometry.g_values(geo, labels, bp, nb)
        cls, med = geometry.classify(g)
        rank = sorted(nb, key=lambda a: g[a]).index(UDIJ) + 1
        o = [cls[UDIJ], rank, round(g[UDIJ] / med, 2), near[UDIJ], rsa(geo, labels)]
        if alias is not None:
            rows = []
            for a in NB5:
                for j in range(3):
                    sel = (labels == a) & (alias == j)
                    rows.append((min(float(np.mean(geo[np.ix_(sel, labels == b)])) for b in B5), lx[(a, j)]["L1"]))
            o.append(("P4 rho", round(float(spearmanr([r[0] for r in rows], [r[1] for r in rows]).statistic), 2)))
        out[k] = o
    return out
zn = np.load(f"{SRC}/cache/states/mname_32b.npz"); blocks = [int(b) for b in zn["blocks"]]
Xn = zn["smean"][:, blocks.index(31)].astype(np.float64); ln, tn, an = zn["algorithm"], zn["template"], zn["alias"]
z = np.load(f"{SRC}/cache/states/mcode_32b.npz"); keys = list(z["keys"]); ri = list(z["readouts"]).index("R1"); bi = [int(b) for b in z["blocks"]].index(33)
R = z["R"][:, ri, bi].astype(np.float64)
ms = json.load(open(f"{SRC}/data/mcode_sets.json"))
rows = [(keys.index(p["scrubbed_sha256"]), a, rank) for a in CANON if len(ms["sets"]["PRIMARY"][a]) >= 10 for rank, p in enumerate(ms["sets"]["PRIMARY"][a])]
F_all = R[[r[0] for r in rows]]; lab = np.array([r[1] for r in rows]); rk = np.array([r[2] for r in rows])
surv = [p for p in ms["placement"] if p["set"] == "SURV" and p["algorithm"] == UDIJ]
Xs = np.stack([R[keys.index(p["scrubbed_sha256"])] for p in surv])
def oos(x, F, geo, k):
    d = np.linalg.norm(F - x, axis=1); nn = np.argsort(d)[:k]
    return np.min(d[nn][:, None] + geo[nn], axis=0)
def place(F, lab, k):
    geo, _ = geometry.geodesics(F, k); nb = [a for a in NB5 if a in set(lab.tolist())]
    g, _ = geometry.g_values(geo, lab, [b for b in B5 if b in set(lab.tolist())], nb); cls, med = geometry.classify(g)
    ne = 0; near = []
    for x in Xs:
        dv = oos(x, F, geo, k); means = {a: float(dv[lab == a].mean()) for a in sorted(set(lab.tolist()))}
        gx = min(means[b] for b in B5 if b in means); ne += gx < med; near.append(min(means, key=means.get))
    # LOO accuracy
    acc = []
    for i in range(len(F)):
        keep = np.ones(len(F), bool); keep[i] = False
        g2, _ = geometry.geodesics(F[keep], k); dv = oos(F[i], F[keep], g2, k); l2 = lab[keep]
        means = {a: float(dv[l2 == a].mean()) for a in sorted(set(l2.tolist()))}; acc.append(min(means, key=means.get) == lab[i])
    import collections
    return ne, dict(collections.Counter(near)), round(float(np.mean(acc)), 2)
print("FULL mname", summ(Xn, ln, an))
print("FULL mcode", summ(F_all, lab), "placement k15", place(F_all, lab, 15))
for tmpl, nr in (((0, 1), 4), ((0,), 9), ((0, 1), 5), ((0,), 7)):
    m = np.isin(tn, tmpl); mc = rk < nr
    print(f"=== D: mname templates {tmpl} [{int(m.sum())}] + mcode ranks<{nr} [{int(mc.sum())}] + 15 surv = {int(m.sum()) + int(mc.sum()) + 15}")
    print("  mname", summ(Xn[m], ln[m], an[m]))
    print("  mcode", summ(F_all[mc], lab[mc]))
    for k in (10, 15): print("  placement k", k, place(F_all[mc], lab[mc], k))
EOF
cd $SP && $SP/venv/bin/python -B explore3.py $SP 2>&1 | grep -v "^\s*$"
```

### [56] TOOL RESULT — Bash · 2026-10-26 14:27:00 UTC

```
{"stdout": "FULL mname {10: ['OPPOSITE', 5, 1.78, 'iddfs', {'R_lex': 0.29, 'R_beh': 0.38, 'R_surface': 0.16}, ('P4 rho', -0.74)], 15: ['OPPOSITE', 5, 1.63, 'astar', {'R_lex': 0.46, 'R_beh': 0.24, 'R_surface': 0.2}, ('P4 rho', -0.65)]}\nFULL mcode {10: ['EDGE', 1, 0.64, 'gbfs', {'R_lex': 0.22, 'R_beh': 0.71, 'R_surface': 0.75}], 15: ['EDGE', 1, 0.67, 'gbfs', {'R_lex': 0.29, 'R_beh': 0.64, 'R_surface': 0.67}]} placement k15 (15, {'dijkstra_unit': 13, 'gbfs': 2}, 0.85)\n=== D: mname templates (0, 1) [60] + mcode ranks<4 [24] + 15 surv = 99\n  mname {10: ['OPPOSITE', 4, 1.01, 'astar', {'R_lex': 0.43, 'R_beh': 0.23, 'R_surface': -0.04}, ('P4 rho', -0.6)], 15: ['OPPOSITE', 4, 1.09, 'astar', {'R_lex': 0.39, 'R_beh': 0.31, 'R_surface': -0.08}, ('P4 rho', -0.65)]}\n  mcode {10: ['EDGE', 1, 0.7, 'gbfs', {'R_lex': 0.02, 'R_beh': 0.83, 'R_surface': 0.82}], 15: ['EDGE', 1, 0.71, 'gbfs', {'R_lex': 0.01, 'R_beh': 0.86, 'R_surface': 0.87}]}\n  placement k 10 (14, {'astar': 7, 'gbfs': 7, 'dijkstra_unit': 1}, 0.83)\n  placement k 15 (10, {'astar': 7, 'dijkstra_unit': 5, 'gbfs': 3}, 0.92)\n=== D: mname templates (0,) [30] + mcode ranks<9 [54] + 15 surv = 99\n  mname {10: ['OPPOSITE', 4, 1.12, 'astar', {'R_lex': 0.37, 'R_beh': 0.31, 'R_surface': -0.13}, ('P4 rho', -0.65)], 15: ['OPPOSITE', 4, 1.15, 'astar', {'R_lex': 0.52, 'R_beh': 0.35, 'R_surface': -0.11}, ('P4 rho', -0.65)]}\n  mcode {10: ['EDGE', 1, 0.68, 'gbfs', {'R_lex': 0.08, 'R_beh': 0.82, 'R_surface': 0.8}], 15: ['EDGE', 1, 0.69, 'gbfs', {'R_lex': 0.07, 'R_beh': 0.83, 'R_surface': 0.82}]}\n  placement k 10 (15, {'astar': 5, 'dijkstra_unit': 3, 'gbfs': 7}, 0.85)\n  placement k 15 (15, {'astar': 8, 'gbfs': 5, 'dijkstra_unit': 2}, 0.81)\n=== D: mname templates (0, 1) [60] + mcode ranks<5 [30] + 15 surv = 105\n  mname {10: ['OPPOSITE', 4, 1.01, 'astar', {'R_lex': 0.43, 'R_beh': 0.23, 'R_surface': -0.04}, ('P4 rho', -0.6)], 15: ['OPPOSITE', 4, 1.09, 'astar', {'R_lex': 0.39, 'R_beh': 0.31, 'R_surface': -0.08}, ('P4 rho', -0.65)]}\n  mcode {10: ['EDGE', 1, 0.74, 'gbfs', {'R_lex': 0.07, 'R_beh': 0.81, 'R_surface': 0.8}], 15: ['EDGE', 1, 0.7, 'gbfs', {'R_lex': 0.06, 'R_beh': 0.88, 'R_surface': 0.87}]}\n  placement k 10 (12, {'astar': 6, 'dijkstra_unit': 3, 'gbfs': 6}, 0.77)\n  placement k 15 (11, {'astar': 6, 'dijkstra_unit': 6, 'gbfs': 3}, 0.9)\n=== D: mname templates (0,) [30] + mcode ranks<7 [42] + 15 surv = 87\n  mname {10: ['OPPOSITE', 4, 1.12, 'astar', {'R_lex': 0.37, 'R_beh': 0.31, 'R_surface': -0.13}, ('P4 rho', -0.65)], 15: ['OPPOSITE', 4, 1.15, 'astar', {'R_lex': 0.52, 'R_beh': 0.35, 'R_surface': -0.11}, ('P4 rho', -0.65)]}\n  mcode {10: ['EDGE', 1, 0.67, 'gbfs', {'R_lex': 0.07, 'R_beh': 0.79, 'R_surface': 0.78}], 15: ['EDGE', 1, 0.72, 'gbfs', {'R_lex': 0.12, 'R_beh': 0.85, 'R_surface': 0.85}]}\n  placement k 10 (14, {'astar': 10, 'dijkstra_unit': 3, 'gbfs': 2}, 0.88)\n  placement k 15 (9, {'astar': 8, 'gbfs': 5, 'dijkstra_unit': 2}, 0.76)", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [57] THINKING · 2026-10-26 14:28:22 UTC

```
The 99-point design matches the full-data results qualitatively across all key metrics (M-name: OPPOSITE, M-code: EDGE, 15/15 survivors at EDGE), and the full-data runs reproduce the README numbers exactly. Next I'll check the figure and output stages to ensure the plotting and verdict cells replicate the original code.
```

### [58] TOOL CALL — Bash · 2026-10-26 14:28:22 UTC

```
Read the figures stage source:
SRC=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46; cat $SRC/src/stage_figures.py
```

### [59] TOOL RESULT — Bash · 2026-10-26 14:28:22 UTC

```
{"stdout": "#!/usr/bin/env python3\n\"\"\"Stage 11 figures (PDF + PNG), all in actual activation coordinates unless labelled otherwise.\n\nPer model x manifold: (a) PCA of the points with centroids sized/coloured by implemented counts (C6 baseline; C6\nban screen + confirm), banned algorithms outlined, ban-prompt states as stars (S-mean manifolds) or survivor\nprograms as crosses (M-code); (b) classical MDS of points and centroids; (c) Isomap at the verdict k with the\ngeodesic path from unit-weight Dijkstra to its nearest banned algorithm. Plus the class table heatmap, RDM heatmaps\nand the behavioural MDS ('behavioural coordinates, not activations').\"\"\"\n\nfrom __future__ import annotations\n\nfrom collections import Counter\nfrom typing import Any\n\nimport matplotlib\n\nmatplotlib.use(\"Agg\")\nimport matplotlib.pyplot as plt  # noqa: E402\nimport numpy as np  # noqa: E402\nfrom loguru import logger  # noqa: E402\nfrom scipy.sparse.csgraph import shortest_path  # noqa: E402\n\nimport geometry  # noqa: E402\nfrom common import CANON_ORDER, SHORT, read_json, read_jsonl  # noqa: E402\nfrom tpg import B5, DATA, IN_E44, K_VERDICT, MODELS, NB5, RESULTS, ROOT, STATES_DIR, UDIJ  # noqa: E402\n\nFIG = ROOT / \"figures\"\nCOL = dict(zip(CANON_ORDER, plt.cm.tab10(np.linspace(0, 1, 10))))\nTITLES = {\"mname\": \"M-name (alias prompts, S-mean)\", \"mdesc\": \"M-desc (name-free descriptions, S-mean)\",\n          \"mlex\": \"M-lex (alias minus neutral twin, S-mean delta)\",\n          \"mcode_PRIMARY_R1\": \"M-code PRIMARY (mean over code tokens, R1)\",\n          \"mcode_PRIMARY_R2\": \"M-code PRIMARY (pop-position token, R2)\",\n          \"mcode_M32_R1\": \"M-code Qwen3-32B-only frame (R1)\", \"mcode_M8_R1\": \"M-code Qwen3-8B-only frame (R1)\",\n          \"mcode_PRIMARY_R1g\": \"M-code PRIMARY (R1 without massive tokens)\",\n          \"mcode_PRIMARY_R3\": \"M-code PRIMARY (16th code token, R3: negative control)\"}\n\n\ndef _save(fig: Any, name: str) -> None:\n    fig.savefig(FIG / f\"{name}.pdf\", bbox_inches=\"tight\")\n    fig.savefig(FIG / f\"{name}.png\", dpi=150, bbox_inches=\"tight\")\n    plt.close(fig)\n\n\ndef counts() -> tuple[Counter, Counter]:\n    base = Counter(r.get(\"adj_label\") for r in read_jsonl(IN_E44 / \"data\" / \"labelled_C6_baseline.jsonl\"))\n    ban = Counter(r.get(\"adj_label\") for f in (\"labelled_C6_ban.jsonl\", \"labelled_C6_confirm.jsonl\")\n                  for r in read_jsonl(IN_E44 / \"data\" / f))\n    return base, ban\n\n\ndef _overlay(model_tag: str, name: str, z: Any) -> tuple[np.ndarray | None, str]:\n    comps, mean, L = z[\"pca_components\"], z[\"pca_mean\"], int(z[\"block\"])\n    if name in (\"mname\", \"mdesc\"):\n        f = STATES_DIR / f\"ban_{model_tag}.npz\"\n        if f.exists():\n            b = np.load(f)\n            Q = b[\"smean\"][:, [int(x) for x in b[\"blocks\"]].index(L)].astype(np.float32)\n            return (Q - mean) @ comps.T, \"7 ban prompts (W1-W5, P6, P7)\"\n    if name.startswith(\"mcode\"):\n        f = STATES_DIR / f\"mcode_{model_tag}.npz\"\n        if f.exists():\n            m = np.load(f)\n            ro = name.split(\"_\")[2]\n            ri = list(m[\"readouts\"]).index(ro)\n            ms = read_json(DATA / \"mcode_sets.json\")\n            keys = list(m[\"keys\"])\n            sel = [keys.index(p[\"scrubbed_sha256\"]) for p in ms[\"placement\"] if p[\"set\"] == \"SURV\" and\n                   p[\"algorithm\"] == UDIJ and p[\"scrubbed_sha256\"] in keys]\n            if sel:\n                Q = m[\"R\"][sel, ri, [int(x) for x in m[\"blocks\"]].index(L)].astype(np.float32)\n                return (Q - mean) @ comps.T, f\"{len(sel)} unit-Dijkstra survivor programs (C6)\"\n    return None, \"\"\n\n\ndef manifold_figs(model_tag: str, name: str, geo_res: dict[str, Any]) -> None:\n    f = FIG / \"coords\" / f\"{model_tag}_{name}.npz\"\n    if not f.exists():\n        return\n    z = np.load(f, allow_pickle=False)\n    labels = z[\"labels\"]\n    L = int(z[\"block\"])\n    present = [a for a in CANON_ORDER if a in set(labels.tolist())]\n    base, ban = counts()\n    cfg = MODELS[model_tag]\n    prec = \"nf4\" if model_tag == \"32b\" else \"bf16\"\n    mdl = \"Qwen3-32B\" if model_tag == \"32b\" else \"Qwen3-8B\"\n    readout = \"SPEC-token mean (S-mean)\" if not name.startswith(\"mcode\") else TITLES[name].split(\"(\")[-1].rstrip(\")\")\n    cap = f\"{mdl} {prec}, block {L}, readout {readout}, N={len(labels)}\"\n    P = z[\"pca2\"]\n    evr = z[\"evr\"]\n    Q, qlab = _overlay(model_tag, name, z)\n    fig, axes = plt.subplots(1, 2, figsize=(14, 6))\n    for ax, (cnt, ttl) in zip(axes, ((base, \"C6 baseline implemented counts\"), (ban, \"C6 ban implemented counts \"\n                                                                                    \"(screen + confirm)\"))):\n        for a in present:\n            s = labels == a\n            ax.scatter(P[s, 0], P[s, 1], s=10, color=COL[a], alpha=0.35)\n        vmax = max(1, max(cnt.get(a, 0) for a in present))\n        for a in present:\n            c = P[labels == a].mean(0)\n            n = cnt.get(a, 0)\n            ax.scatter([c[0]], [c[1]], s=60 + 40 * np.sqrt(n + 1), c=[[n / vmax]], cmap=\"viridis\", vmin=0, vmax=1,\n                       edgecolors=\"red\" if a in B5 else \"black\", linewidths=2.5 if a in B5 else 1.0, zorder=5)\n            ax.annotate(f\"{SHORT[a]} ({n})\", c, fontsize=8, xytext=(4, 4), textcoords=\"offset points\")\n        if Q is not None:\n            mk = \"*\" if not name.startswith(\"mcode\") else \"x\"\n            ax.scatter(Q[:, 0], Q[:, 1], marker=mk, s=110 if mk == \"*\" else 45, color=\"black\", label=qlab, zorder=6)\n            ax.legend(loc=\"best\", fontsize=8)\n        elif not name.startswith(\"mcode\"):\n            c = P[labels == UDIJ].mean(0) if UDIJ in present else None\n            if c is not None:\n                th = np.linspace(0, 2 * np.pi, 15, endpoint=False)\n                r = 0.04 * (P.max() - P.min())\n                ax.scatter(c[0] + r * np.cos(th), c[1] + r * np.sin(th), s=12, marker=\"o\", facecolors=\"none\",\n                           edgecolors=\"black\", label=\"15 unit-Dijkstra survivors (label-level)\")\n                ax.legend(loc=\"best\", fontsize=8)\n        ax.set_xlabel(f\"PC1 ({100 * evr[0]:.1f}% var.)\")\n        ax.set_ylabel(f\"PC2 ({100 * evr[1]:.1f}% var.)\")\n        ax.set_title(ttl, fontsize=10)\n    fig.suptitle(f\"(a) PCA of residual states: {TITLES[name]}\\n{cap}; banned (red outline): \"\n                 f\"{', '.join(SHORT[b] for b in B5)}\", fontsize=10)\n    _save(fig, f\"pca_{model_tag}_{name}\")\n    # (b) MDS\n    d = geo_res[\"L_star\"][\"describe\"]\n    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))\n    Ym = z[\"mds\"]\n    for a in present:\n        s = labels == a\n        axes[0].scatter(Ym[s, 0], Ym[s, 1], s=10, color=COL[a], label=SHORT[a], alpha=0.6)\n    axes[0].legend(fontsize=7, ncol=2)\n    axes[0].set_title(f\"classical MDS of the {len(labels)} points (stress-1 {d['mds_points_stress1']:.2f})\", fontsize=10)\n    Yc = z[\"mds_c\"]\n    for i, a in enumerate(present):\n        axes[1].scatter([Yc[i, 0]], [Yc[i, 1]], s=120, color=COL[a], edgecolors=\"red\" if a in B5 else \"black\",\n                        linewidths=2.5 if a in B5 else 1)\n        axes[1].annotate(SHORT[a], Yc[i], fontsize=9, xytext=(5, 5), textcoords=\"offset points\")\n    axes[1].set_title(f\"classical MDS of the {len(present)} centroids (stress-1 {d['mds_centroids_stress1']:.2f})\",\n                      fontsize=10)\n    for ax in axes:\n        ax.set_xlabel(\"MDS 1\")\n        ax.set_ylabel(\"MDS 2\")\n    fig.suptitle(f\"(b) {TITLES[name]} - {cap}\", fontsize=10)\n    _save(fig, f\"mds_{model_tag}_{name}\")\n    # (c) Isomap with geodesic path uDij -> nearest banned\n    Y = z[\"iso\"]\n    if len(Y):\n        geo = z[\"geo\"]\n        fig, ax = plt.subplots(figsize=(8, 7))\n        for a in present:\n            s = labels == a\n            ax.scatter(Y[s, 0], Y[s, 1], s=12, color=COL[a], label=SHORT[a], alpha=0.7,\n                       edgecolors=\"red\" if a in B5 else \"none\", linewidths=0.6)\n        kd = d[f\"k{K_VERDICT}\"]\n        if UDIJ in present:\n            nb = kd[\"nearest_banned\"][UDIJ]\n            iu = np.where(labels == UDIJ)[0]\n            ib = np.where(labels == nb)[0]\n            sub = geo[np.ix_(iu, ib)]\n            i, j = np.unravel_index(np.argmin(sub), sub.shape)\n            X = np.load(STATES_DIR / f\"geo_{model_tag}_{name}_k{K_VERDICT}.npz\")\n            G = X[\"adjacency\"]\n            _, pred = shortest_path(G, method=\"D\", directed=False, indices=[iu[i]], return_predecessors=True)\n            path, cur = [], ib[j]\n            while cur >= 0 and cur != iu[i]:\n                path.append(cur)\n                cur = pred[0, cur]\n            path.append(iu[i])\n            ax.plot(Y[path, 0], Y[path, 1], \"k-\", lw=1.5, label=f\"geodesic {SHORT[UDIJ]} -> {SHORT[nb]}\")\n            ttl = (f\"class(uDij)={kd['classes'][UDIJ]}, g={kd['g'][UDIJ]:.2f}, median {kd['median']:.2f}, \"\n                   f\"rank {kd['udij_rank']}/{len(kd['g'])}\")\n        else:\n            ttl = \"unit Dijkstra not in this manifold\"\n        ax.legend(fontsize=7, ncol=2)\n        ax.set_xlabel(\"Isomap 1\")\n        ax.set_ylabel(\"Isomap 2\")\n        ax.set_title(f\"(c) Isomap k={K_VERDICT}: {TITLES[name]}\\n{cap}; {ttl}\", fontsize=9)\n        _save(fig, f\"isomap_{model_tag}_{name}\")\n    _ = cfg\n\n\ndef class_table(geo_all: dict[str, Any]) -> None:\n    rows, cells, txt = [], [], []\n    cmap = {\"EDGE\": 0, \"MIDDLE\": 1, \"OPPOSITE\": 2}\n    for key, r in geo_all.items():\n        if r is None:\n            continue\n        kd = r[\"L_star\"][\"describe\"][f\"k{K_VERDICT}\"]\n        rows.append(f\"{key} (L{r['L_star']['block']})\")\n        cells.append([cmap.get(kd[\"classes\"].get(a), np.nan) for a in NB5])\n        txt.append([(f\"{kd['classes'][a][:3]}\\n{kd['g'][a] / kd['median']:.2f}\" if a in kd[\"classes\"] else \"not run\")\n                    for a in NB5])\n    if not rows:\n        return\n    fig, ax = plt.subplots(figsize=(9, 0.55 * len(rows) + 1.5))\n    ax.imshow(np.array(cells, dtype=float), cmap=\"coolwarm\", vmin=0, vmax=2, aspect=\"auto\")\n    for i in range(len(rows)):\n        for j in range(5):\n            ax.text(j, i, txt[i][j], ha=\"center\", va=\"center\", fontsize=7,\n                    fontweight=\"bold\" if NB5[j] == UDIJ else \"normal\")\n    ax.set_xticks(range(5), [SHORT[a] for a in NB5])\n    ax.set_yticks(range(len(rows)), rows, fontsize=7)\n    ax.set_title(f\"EDGE / MIDDLE / OPPOSITE of the non-banned algorithms (k={K_VERDICT}, cell = class, g/median)\",\n                 fontsize=9)\n    _save(fig, \"class_table\")\n\n\ndef rdm_figs() -> None:\n    rs = read_json(RESULTS / \"rsa.json\") if (RESULTS / \"rsa.json\").exists() else {}\n    beh = read_json(RESULTS / \"behavioural_distance.json\")\n    lex = read_json(RESULTS / \"lexical.json\")\n    mats = {\"R_beh (behavioural)\": np.array(beh[\"d_beh_lambda0.5\"]), \"R_lex (alias 3-grams)\": np.array(lex[\"R_lex\"])}\n    sur = RESULTS / \"surface_rdm.json\"\n    if sur.exists():\n        mats[\"R_surface (AST 4-grams)\"] = np.array(read_json(sur)[\"R_surface\"])\n    geo_all = read_json(RESULTS / \"geometry_all.json\")\n    for key in (\"32b|mname\", \"32b|mdesc\", \"32b|mlex\", \"32b|mcode_PRIMARY_R1\"):\n        if key in geo_all:\n            M = np.array(geo_all[key][\"L_star\"][\"describe\"][f\"k{K_VERDICT}\"][\"class_geodesic_matrix\"])\n            M = (M + M.T) / 2\n            np.fill_diagonal(M, 0)\n            r = rs.get(key, {}).get(\"models\", {})\n            lab = f\"{key} neural; rho beh {r.get('R_beh', {}).get('rho', float('nan')):.2f}, lex \" \\\n                  f\"{r.get('R_lex', {}).get('rho', float('nan')):.2f}\"\n            mats[lab] = M\n    n = len(mats)\n    fig, axes = plt.subplots(2, (n + 1) // 2, figsize=(4.2 * ((n + 1) // 2), 8.5))\n    for ax, (t, M) in zip(axes.ravel(), mats.items()):\n        ax.imshow(np.nan_to_num(M), cmap=\"magma\")\n        ax.set_xticks(range(10), [SHORT[a] for a in CANON_ORDER], rotation=90, fontsize=7)\n        ax.set_yticks(range(10), [SHORT[a] for a in CANON_ORDER], fontsize=7)\n        ax.set_title(t, fontsize=7)\n    for ax in axes.ravel()[n:]:\n        ax.axis(\"off\")\n    _save(fig, \"rdms\")\n    Y = beh[\"behavioural_coordinates_mds\"]\n    fig, ax = plt.subplots(figsize=(6, 5))\n    for a in CANON_ORDER:\n        ax.scatter([Y[a][0]], [Y[a][1]], s=120, color=COL[a], edgecolors=\"red\" if a in B5 else \"black\",\n                   linewidths=2.5 if a in B5 else 1)\n        ax.annotate(SHORT[a], Y[a], xytext=(5, 5), textcoords=\"offset points\")\n    ax.set_title(f\"Behavioural coordinates, not activations: classical MDS of d_beh\\n(expansion-order traces of the \"\n                 f\"15 T1 references on 40 probe grids; stress-1 {beh['behavioural_mds_stress1']:.2f})\", fontsize=9)\n    ax.set_xlabel(\"behavioural MDS 1\")\n    ax.set_ylabel(\"behavioural MDS 2\")\n    _save(fig, \"behavioural_mds\")\n\n\ndef lexical_fig() -> None:\n    lr = read_json(RESULTS / \"lexical_regression.json\") if (RESULTS / \"lexical_regression.json\").exists() else {}\n    r = lr.get(\"32b|mname\")\n    if not r:\n        return\n    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))\n    for ax, k in zip(axes, (\"k10\", \"k15\")):\n        rows = r[k][\"rows\"]\n        for row in rows:\n            ax.scatter(row[\"L1\"] + np.random.default_rng(len(row[\"alias\"] if \"alias\" in row else \"\") + row[\n                \"alias_index\"]).uniform(-0.08, 0.08), row[\"g_alias\"], color=COL[row[\"algorithm\"]], s=50)\n        for a in NB5:\n            ax.scatter([], [], color=COL[a], label=SHORT[a])\n        ax.set_xlabel(\"L1 = banned algorithms whose alias regex matches the alias\")\n        ax.set_ylabel(\"g_alias (min mean geodesic to a banned algorithm)\")\n        ax.set_title(f\"M-name alias level, {k}: Spearman {r[k]['spearman_L1']:.2f} (perm p {r[k]['perm_p_L1']:.4f})\",\n                     fontsize=9)\n        ax.legend(fontsize=7)\n    _save(fig, \"lexical_alias_level_32b\")\n\n\ndef stage_figures(*args: str) -> None:\n    FIG.mkdir(exist_ok=True)\n    geo_all = read_json(RESULTS / \"geometry_all.json\")\n    for key, r in geo_all.items():\n        if r is None:\n            continue\n        m, name = key.split(\"|\")\n        try:\n            manifold_figs(m, name, r)\n        except (ValueError, KeyError, IndexError, FileNotFoundError) as e:\n            logger.error(f\"figure {key} failed: {type(e).__name__}: {e}\")\n    class_table(geo_all)\n    rdm_figs()\n    lexical_fig()\n    logger.info(f\"figures: {len(list(FIG.glob('*.png')))} PNG files\")", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [60] TOOL CALL — Bash · 2026-10-26 14:28:22 UTC

```
Read the outputs stage source (verdict rule):
SRC=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46; sed -n 1,140p $SRC/src/stage_outputs.py
```

### [61] TOOL RESULT — Bash · 2026-10-26 14:28:22 UTC

```
{"stdout": "#!/usr/bin/env python3\n\"\"\"Stage 12: data/points.jsonl, data/placements.jsonl, results/n4_verdict.json (P1-P8, named outcome) and\nmethod_out.json (exp_gen_sol_out: tpg_points, tpg_placements, tpg_naming + metadata).\"\"\"\n\nfrom __future__ import annotations\n\nfrom collections import Counter\nfrom typing import Any\n\nimport numpy as np\nfrom loguru import logger\n\nimport prompts_tp\nfrom common import (CANON_ORDER, read_json, read_jsonl, sha256_file, utc_now, verify_chain, write_json, write_jsonl)\nfrom tpg import B5, DATA, K_SECOND, K_VERDICT, MODELS, NB5, PRED, RESULTS, ROOT, STATES_DIR, UDIJ\n\nSTATEMENT = (\"The geometry is correlational: it describes where representations and survivors sit, not whether the \"\n             \"model uses this geometry to choose an algorithm (iteration 7's in-manifold pushes moved 0/300).\")\n\n\ndef _get(d: dict[str, Any], *ks: str, default: Any = None) -> Any:\n    for k in ks:\n        if not isinstance(d, dict) or k not in d:\n            return default\n        d = d[k]\n    return d\n\n\ndef _verdict(geo: dict[str, Any], key: str, k: int) -> str | None:\n    r = geo.get(key)\n    if not r:\n        return None\n    return _get(r, \"L_star\", \"landing\", f\"k{k}\", \"pooled\", \"verdict\")\n\n\ndef _cls(geo: dict[str, Any], key: str, k: int) -> str | None:\n    r = geo.get(key)\n    if not r:\n        return None\n    return _get(r, \"L_star\", \"describe\", f\"k{k}\", \"classes\", UDIJ)\n\n\ndef n4_verdict() -> dict[str, Any]:\n    geo = read_json(RESULTS / \"geometry_all.json\")\n    rep = read_json(RESULTS / \"repro_mname_32b.json\")\n    lex = read_json(RESULTS / \"lexical_regression.json\")\n    beh = read_json(RESULTS / \"behavioural_distance.json\")\n    rsa = read_json(RESULTS / \"rsa.json\")\n    pl = read_json(RESULTS / \"placement.json\") if (RESULTS / \"placement.json\").exists() else {}\n    P: dict[str, Any] = {}\n    gr = rep[\"G_repro\"]\n    P[\"P1\"] = {\"pass\": gr[\"pass\"], \"spearman\": gr[\"spearman_vs_geo_C6_nf4_k15_block31\"],\n               \"classes_equal\": gr[\"classes_new\"] == gr[\"classes_e44\"], \"max_abs_g_diff\": gr[\"max_abs_g_diff\"],\n               \"spearman_k10\": rep[\"by_k\"][\"10\"][\"spearman_class_geodesic\"] if \"10\" in rep[\"by_k\"] else None,\n               \"note\": \"fallback F1 (0.85 <= rho < 0.95): new states used for every manifold; cached-state verdict \"\n                       \"(iteration 8: OPPOSITE) reported beside\"}\n    code_key, desc_key = \"32b|mcode_PRIMARY_R1\", \"32b|mdesc\"\n    c2 = read_json(PRED / \"commit2.json\")\n    if _get(c2, \"F8\", \"32b\", \"verdict_readout\") == \"R2\":\n        code_key = \"32b|mcode_PRIMARY_R2\"\n    v = {key: {f\"k{k}\": {\"verdict\": _verdict(geo, key, k), \"udij_class\": _cls(geo, key, k)} for k in (K_SECOND, K_VERDICT)}\n         for key in (\"32b|mname\", \"32b|mlex\", desc_key, code_key, \"32b|mcode_M32_R1\", \"32b|mcode_M8_R1\",\n                     \"32b|mcode_PRIMARY_R2\", \"8b|mname\", \"8b|mlex\", \"8b|mdesc\", \"8b|mcode_PRIMARY_R1\")}\n    P[\"P2\"] = {\"pass\": all(v[key][f\"k{k}\"][\"udij_class\"] == \"EDGE\" for key in (code_key, desc_key)\n                           for k in (K_SECOND, K_VERDICT)) and\n               all(v[key][f\"k{K_VERDICT}\"][\"verdict\"] == \"EDGE\" for key in (code_key, desc_key)),\n               \"mcode\": v[code_key], \"mdesc\": v[desc_key]}\n    P[\"P3\"] = {\"pass\": all(v[key][f\"k{k}\"][\"udij_class\"] == \"OPPOSITE\" for key in (\"32b|mname\", \"32b|mlex\")\n                           for k in (K_SECOND, K_VERDICT)), \"mname\": v[\"32b|mname\"], \"mlex\": v[\"32b|mlex\"]}\n    lm = lex.get(\"32b|mname\") or {}\n    P[\"P4\"] = {\"pass\": bool(lm.get(\"P4_pass\")),\n               \"spearman_L1\": {f\"k{k}\": _get(lm, f\"k{k}\", \"spearman_L1\") for k in (K_SECOND, K_VERDICT)},\n               \"perm_p_L1\": {f\"k{k}\": _get(lm, f\"k{k}\", \"perm_p_L1\") for k in (K_SECOND, K_VERDICT)},\n               \"within_algorithm\": {f\"k{k}\": _get(lm, f\"k{k}\", \"within_algorithm\") for k in (K_SECOND, K_VERDICT)}}\n    P[\"P5\"] = {\"descriptive\": lex.get(\"descriptive_mdesc_mcode\")}\n    P[\"P6\"] = {\"pass\": beh[\"P6_udij_nearest_to_bfs\"], \"d_beh_to_bfs\": beh[\"P6_d_beh_to_bfs\"],\n               \"note\": \"anchor: unit-weight Dijkstra expands in BFS order on a unit grid by construction\"}\n\n    def rho(key: str, m: str) -> float | None:\n        return _get(rsa, key, \"models\", m, \"rho\")\n\n    P[\"P7\"] = {\"rho\": {key: {m: rho(key, m) for m in (\"R_lex\", \"R_beh\", \"R_surface\", \"R_len\")}\n                       for key in (\"32b|mname\", desc_key, code_key, \"32b|mlex\")},\n               \"pattern\": {\"name_lex_gt_beh\": (rho(\"32b|mname\", \"R_lex\") or -9) > (rho(\"32b|mname\", \"R_beh\") or -9),\n                           \"code_beh_gt_lex\": (rho(code_key, \"R_beh\") or -9) > (rho(code_key, \"R_lex\") or -9),\n                           \"desc_beh_gt_lex\": (rho(desc_key, \"R_beh\") or -9) > (rho(desc_key, \"R_lex\") or -9)},\n               \"p_exact\": {key: {m: _get(rsa, key, \"models\", m, \"p_exact\") for m in (\"R_lex\", \"R_beh\")}\n                           for key in (\"32b|mname\", desc_key, code_key)}, \"descriptive\": True}\n    plc = pl.get(\"32b|mcode_PRIMARY_R1\", {})\n    P[\"P8\"] = {\"pass\": plc.get(\"P8_pass\"), \"G_place\": plc.get(\"G_place\"), \"udij_survivors\": plc.get(\"udij_survivors\")}\n    # secondary statistics\n    sec = {}\n    for key in (\"32b|mname\", \"32b|mlex\", desc_key, code_key, \"32b|mcode_M32_R1\", \"8b|mname\", \"8b|mdesc\",\n                \"8b|mcode_PRIMARY_R1\"):\n        r = geo.get(key)\n        if not r:\n            continue\n        d = r[\"L_star\"][\"describe\"]\n        bs = _get(r, \"L_star\", \"bootstrap\", f\"k{K_VERDICT}\") or {}\n        sec[key] = {\"L_star\": r[\"L_star\"][\"block\"],\n                    **{f\"k{k}\": {\"udij_class\": d[f\"k{k}\"][\"classes\"].get(UDIJ), \"udij_rank\": d[f\"k{k}\"][\"udij_rank\"],\n                                 \"udij_ratio\": d[f\"k{k}\"][\"udij_ratio\"],\n                                 \"nearest_banned\": d[f\"k{k}\"][\"nearest_banned\"].get(UDIJ),\n                                 \"classes\": d[f\"k{k}\"][\"classes\"]} for k in (5, K_SECOND, K_VERDICT)},\n                    \"bootstrap_k15\": {\"udij_edge_probability\": _get(bs, \"edge_probability\", UDIJ),\n                                      \"udij_class_stability\": _get(bs, \"class_stability\", UDIJ),\n                                      \"udij_ratio_ci95\": bs.get(\"udij_ratio_ci95\"), \"n_boot\": bs.get(\"n_boot\")},\n                    \"robustness_udij_class_counts\": _get(r, \"L_star\", \"robustness\", \"udij_class_counts\"),\n                    \"crossnobis_udij_class\": _get(r, \"L_star\", \"crossnobis\", \"classes\", UDIJ),\n                    \"zscored_udij_class\": _get(r, \"L_star\", \"zscored\", \"classes\", UDIJ),\n                    \"euclid_centroid_udij_class\": _get(d, \"euclid_centroid\", \"classes\", UDIJ),\n                    \"split_half_spearman_brown_k15\": _get(r, \"L_star\", \"split_half\", f\"k{K_VERDICT}\",\n                                                          \"spearman_brown\"),\n                    \"nonbanned_used\": d[\"nonbanned_used\"]}\n    # named outcome\n    mc15, md15 = v[code_key][f\"k{K_VERDICT}\"][\"udij_class\"], v[desc_key][f\"k{K_VERDICT}\"][\"udij_class\"]\n    mc10, md10 = v[code_key][f\"k{K_SECOND}\"][\"udij_class\"], v[desc_key][f\"k{K_SECOND}\"][\"udij_class\"]\n    m32 = v[\"32b|mcode_M32_R1\"][f\"k{K_VERDICT}\"][\"udij_class\"]\n    source = \"ROBUST\" if m32 == mc15 else (\"SOURCE-SENSITIVE\" if m32 else \"M32 frame not available\")\n    k_sensitive = (mc15 != mc10) or (md15 != md10)\n    if mc15 is None or md15 is None:\n        outcome = \"UNTESTABLE\"\n    elif P[\"P2\"][\"pass\"] and P[\"P3\"][\"pass\"] and P[\"P4\"][\"pass\"] and P[\"P6\"][\"pass\"]:\n        outcome = \"CONFIRMED\"\n    elif mc15 == \"OPPOSITE\" and md15 == \"OPPOSITE\" and not k_sensitive and source != \"SOURCE-SENSITIVE\":\n        outcome = \"ROBUST-OPPOSITE\"\n    elif mc15 != md15 or k_sensitive or source == \"SOURCE-SENSITIVE\":\n        outcome = \"MIXED\"\n    elif P[\"P3\"][\"pass\"] and P[\"P4\"][\"pass\"] and mc15 in (\"MIDDLE\",) and md15 in (\"MIDDLE\",):\n        outcome = \"NAMES-ONLY\"\n    else:\n        outcome = \"NONE OF THE NAMED OUTCOMES\"\n    out = {\"utc\": utc_now(), \"predictions\": P, \"secondary_statistics\": sec, \"verdict_table\": v,\n           \"mcode_source_robustness\": source, \"k_sensitive\": k_sensitive,\n           \"mcode_class_k15\": mc15, \"mdesc_class_k15\": md15, \"named_outcome\": outcome,\n           \"mcode_verdict_key\": code_key, \"statement\": STATEMENT,\n           \"mdesc_excluded_algorithms\": [a for a in NB5 if a not in _get(geo.get(desc_key, {}), \"L_star\", \"describe\",\n                                                                          \"nonbanned_used\", default=[])]}\n    write_json(RESULTS / \"n4_verdict.json\", out)\n    logger.info(f\"N4 outcome {outcome}: M-code {mc15}/{mc10}, M-desc {md15}/{md10}, M32 {m32}; \"", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [62] THINKING · 2026-10-26 14:28:42 UTC

```
I'll have the notebook mirror stages 7–11 by writing out geometry.py/landing.py, adapting stage_analysis.py's functions to run sequentially, and reusing stage_figures.py's plotting code. Next, I'll locate the prompt/program texts and implemented-count inputs for the mini data.
```

### [63] TOOL CALL — Bash · 2026-10-26 14:28:42 UTC

```
List artifact data files and peek at points rows:
SRC=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46; ls -la $SRC/data | head -50; head -c 1500 $SRC/data/points.jsonl; echo; echo ---; head -c 800 $SRC/data/placements.jsonl; echo; grep -n "SHORT" $SRC/src/common.py | head -5
```

### [64] TOOL RESULT — Bash · 2026-10-26 14:28:42 UTC

```
{"stdout": "total 46887\ndrwxrwxrwx 15 aii-agent aii-agent  2008428 Oct 23 15:20 .\ndrwxrwxrwx 14 aii-agent aii-agent  3000131 Oct 23 18:02 ..\n-rw-rw-rw-  1 aii-agent aii-agent    22493 Oct 23 11:46 descriptions_v0.json\n-rw-rw-rw-  1 aii-agent aii-agent     6162 Oct 23 11:46 mcode_contexts.json\n-rw-rw-rw-  1 aii-agent aii-agent   919038 Oct 23 14:21 mcode_sets.json\n-rw-rw-rw-  1 aii-agent aii-agent   368597 Oct 23 14:21 mdesc_prompts.json\n-rw-rw-rw-  1 aii-agent aii-agent   681431 Oct 23 11:46 mlex_prompts.json\n-rw-rw-rw-  1 aii-agent aii-agent   782507 Oct 23 12:25 naming_calls.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent   895975 Oct 23 15:20 placements.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent   937113 Oct 23 15:20 points.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent    20573 Oct 23 11:43 probe_grids.json\n-rw-rw-rw-  1 aii-agent aii-agent 14082696 Oct 23 14:17 program_eval_cache.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent  1415385 Oct 23 11:43 reference_traces.json\ndrwxrwxrwx  2 aii-agent aii-agent  2000326 Oct 23 15:03 tmp5l6f163o\ndrwxrwxrwx  2 aii-agent aii-agent  2000271 Oct 23 15:09 tmp5t6ifwnp\ndrwxrwxrwx  2 aii-agent aii-agent  2000373 Oct 23 14:33 tmp_cpqx5ic\ndrwxrwxrwx  2 aii-agent aii-agent  1001646 Oct 23 13:18 tmph7szprpw\ndrwxrwxrwx  2 aii-agent aii-agent  2000236 Oct 23 15:02 tmpof57q6ij\ndrwxrwxrwx  2 aii-agent aii-agent  1001682 Oct 23 13:19 tmpokq7l65p\ndrwxrwxrwx  2 aii-agent aii-agent  1001640 Oct 23 13:18 tmppfvhhndm\ndrwxrwxrwx  2 aii-agent aii-agent  2000278 Oct 23 15:12 tmpsyg1n93r\ndrwxrwxrwx  2 aii-agent aii-agent  1001632 Oct 23 13:19 tmpu3e1lvyf\ndrwxrwxrwx  2 aii-agent aii-agent  1001646 Oct 23 13:18 tmpvi46nla9\ndrwxrwxrwx  2 aii-agent aii-agent  2000271 Oct 23 15:01 tmpvmez14uu\ndrwxrwxrwx  2 aii-agent aii-agent  2000333 Oct 23 14:15 tmpw280v7s4\n-rw-rw-rw-  1 aii-agent aii-agent  1851659 Oct 23 12:59 topups.jsonl\ndrwxrwxrwx  2 aii-agent aii-agent  2004232 Oct 23 14:21 trace_cache\n{\"model\": \"unsloth/Qwen3-32B-bnb-4bit\", \"engine\": \"hf-nf4-truncated\", \"provider\": null, \"task\": \"T1\", \"arm\": \"mname\", \"condition\": \"mname\", \"k\": 15, \"label\": \"bfs\", \"point_id\": \"mname|bfs|t0|j0\", \"predict_nearest\": \"bfs\", \"template\": 0, \"alias\": 0}\n{\"model\": \"unsloth/Qwen3-32B-bnb-4bit\", \"engine\": \"hf-nf4-truncated\", \"provider\": null, \"task\": \"T1\", \"arm\": \"mname\", \"condition\": \"mname\", \"k\": 15, \"label\": \"bfs\", \"point_id\": \"mname|bfs|t0|j1\", \"predict_nearest\": \"bfs\", \"template\": 0, \"alias\": 1}\n{\"model\": \"unsloth/Qwen3-32B-bnb-4bit\", \"engine\": \"hf-nf4-truncated\", \"provider\": null, \"task\": \"T1\", \"arm\": \"mname\", \"condition\": \"mname\", \"k\": 15, \"label\": \"bfs\", \"point_id\": \"mname|bfs|t0|j2\", \"predict_nearest\": \"bfs\", \"template\": 0, \"alias\": 2}\n{\"model\": \"unsloth/Qwen3-32B-bnb-4bit\", \"engine\": \"hf-nf4-truncated\", \"provider\": null, \"task\": \"T1\", \"arm\": \"mname\", \"condition\": \"mname\", \"k\": 15, \"label\": \"bfs\", \"point_id\": \"mname|bfs|t1|j0\", \"predict_nearest\": \"bfs\", \"template\": 1, \"alias\": 0}\n{\"model\": \"unsloth/Qwen3-32B-bnb-4bit\", \"engine\": \"hf-nf4-truncated\", \"provider\": null, \"task\": \"T1\", \"arm\": \"mname\", \"condition\": \"mname\", \"k\": 15, \"label\": \"bfs\", \"point_id\": \"mname|bfs|t1|j1\", \"predict_nearest\": \"bfs\", \"template\": 1, \"alias\": 1}\n{\"model\": \"unsloth/Qwen3-32B-bnb-4bit\", \"engine\": \"hf-nf4-truncated\", \"provider\": null, \"task\": \"T1\", \"arm\": \"mname\", \"condition\": \"mname\", \"k\": 15, \"label\": \"bfs\", \"point_id\": \"mname|bfs|t1|j2\", \"predict_nearest\": \"bfs\", \"template\": 1, \"alias\": 2}\n{\"mode\n---\n{\"model\": \"32b\", \"frame\": \"mcode_PRIMARY_R1\", \"block\": 33, \"k\": 15, \"readout\": \"R1\", \"uid\": \"C6|ban|0\", \"set\": \"SURV\", \"label\": \"other\", \"other_name\": \"random walk with restart\", \"nearest_algorithm\": \"bfs\", \"g_x\": 24.68766120716996, \"nearest_banned\": \"bfs\", \"class\": \"EDGE\", \"mean_geodesic\": {\"astar\": 58.88899745393606, \"bfs\": 24.68766120716996, \"dfs\": 25.06021104391351, \"dijkstra_unit\": 54.902503394509985, \"gbfs\": 54.74085412921854, \"idastar\": 55.52495369287058}, \"g_scrub_pass\": false, \"code_sha256\": \"a9f6b61acf85d6279e809b982fa4e3d0e37ad24b6bf2eb347d3690d8e1cdce0e\", \"code\": \"import random\\n\\ndef solve(grid, start, goal):\\n    rows = len(grid)\\n    if rows == 0:\\n        return []\\n    cols = len(grid[0])\\n    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':\\n        re\n82:SHORT = {\"bfs\": \"BFS\", \"dfs\": \"DFS\", \"bibfs\": \"BiBFS\", \"iddfs\": \"IDDFS\", \"astar\": \"A*\", \"gbfs\": \"GBFS\",\n133:SHORT_FORMS: dict[str, list[str]] = {\n468:        pats += SHORT_FORMS[k]", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [65] ASSISTANT · 2026-10-26 14:29:08 UTC

```
`points.jsonl` has no prompt text, so I'll take it from `full_method_out.json`, loaded programmatically and never printed. Next I'll check the `SHORT` display names and that dataset's fields.
```

### [66] TOOL CALL — Bash · 2026-10-26 14:29:08 UTC

```
Inspect full output datasets and geometry results:
SRC=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46; sed -n 82,84p $SRC/src/common.py; SP=/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-VVA3P0ocZNA2/39a5c6e0-c154-4645-bb18-199862447326/scratchpad; $SP/venv/bin/python -B - <<'EOF'
import json, collections
SRC="/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46"
d = json.load(open(f"{SRC}/full_method_out.json"))
for ds in d["datasets"]:
    ex = ds["examples"]
    print(ds["dataset"], len(ex), sorted(ex[0].keys()))
    if ds["dataset"] == "tpg_points":
        print(" manifolds", collections.Counter((e["metadata_model"], e["metadata_manifold"]) for e in ex))
        e0 = [e for e in ex if e["metadata_point_id"] == "mname|bfs|t0|j0"][0]
        print(" input len", len(e0["input"]), repr(e0["input"][-300:]))
        e1 = [e for e in ex if e["metadata_manifold"].startswith("mcode")][0]
        print(" mcode example keys", {k: (v if len(str(v)) < 80 else str(v)[:80]) for k, v in e1.items()})
geo = json.load(open(f"{SRC}/results/geometry_all.json"))
r = geo["32b|mname"]
print("geometry_all 32b|mname keys", list(r.keys()), "L_star keys", list(r["L_star"].keys()))
print("summary", json.dumps(r["summary"])[:600])
print("landing k15 pooled", {k: v for k, v in r["L_star"]["landing"]["k15"]["pooled"].items() if k in ("S", "verdict", "class_shares")})
EOF
```

### [67] TOOL RESULT — Bash · 2026-10-26 14:29:08 UTC

````
{"stdout": "SHORT = {\"bfs\": \"BFS\", \"dfs\": \"DFS\", \"bibfs\": \"BiBFS\", \"iddfs\": \"IDDFS\", \"astar\": \"A*\", \"gbfs\": \"GBFS\",\n         \"dijkstra_unit\": \"Dijkstra(u)\", \"idastar\": \"IDA*\", \"jps\": \"JPS\", \"biastar\": \"BiA*\", \"other\": \"other\",\n         \"no_code\": \"no code\", \"invalid\": \"invalid\"}\ntpg_points 1080 ['input', 'metadata_k', 'metadata_manifold', 'metadata_model', 'metadata_point_id', 'output', 'predict_nearest_mname']\n manifolds Counter({('unsloth/Qwen3-32B-bnb-4bit', 'mname'): 300, ('unsloth/Qwen3-32B-bnb-4bit', 'mlex'): 300, ('unsloth/Qwen3-32B-bnb-4bit', 'mdesc'): 260, ('unsloth/Qwen3-32B-bnb-4bit', 'mcode_M32_R1'): 113, ('unsloth/Qwen3-32B-bnb-4bit', 'mcode_PRIMARY_R1'): 107})\n input len 979 'o be the shortest. If start equals goal and the cell is free, return [start]. If no path exists, or start or goal is a wall, return [].\\n\\nUse only the Python standard library. Return only one ```python code block containing the function solve and any helpers, with no example usage and no explanation.'\n mcode example keys {'input': 'from collections import deque\\n\\ndef solve(grid, start, goal):\\n    if not grid or ', 'output': 'bfs', 'predict_nearest_mcode_PRIMARY_R1': 'bfs', 'metadata_model': 'unsloth/Qwen3-32B-bnb-4bit', 'metadata_manifold': 'mcode_PRIMARY_R1', 'metadata_point_id': 'S1|forced:bfs|0|7', 'metadata_k': 15}\ntpg_placements 113 ['input', 'metadata_g_x', 'metadata_nearest_banned', 'metadata_set', 'metadata_uid', 'output', 'predict_class', 'predict_nearest_mcode']\ntpg_naming 42 ['input', 'metadata_passed', 'metadata_rate', 'metadata_slot', 'metadata_version', 'output', 'predict_qwen32b_modal']\ngeometry_all 32b|mname keys ['model', 'manifold', 'L_star', 'ref_block', 'n_points', 'layer_curve', 'ref_block_same_as_L_star', 'summary'] L_star keys ['block', 'describe', 'landing', 'split_half', 'bootstrap', 'robustness', 'crossnobis', 'zscored']\nsummary {\"k5\": {\"udij_class\": \"MIDDLE\", \"udij_rank\": 3, \"udij_ratio\": 1.0, \"udij_nearest_banned\": \"iddfs\", \"classes\": {\"bibfs\": \"EDGE\", \"biastar\": \"OPPOSITE\", \"idastar\": \"EDGE\", \"jps\": \"OPPOSITE\", \"dijkstra_unit\": \"MIDDLE\"}, \"verdict_pooled\": null}, \"k10\": {\"udij_class\": \"OPPOSITE\", \"udij_rank\": 5, \"udij_ratio\": 1.7828001234446156, \"udij_nearest_banned\": \"iddfs\", \"classes\": {\"bibfs\": \"EDGE\", \"biastar\": \"EDGE\", \"idastar\": \"MIDDLE\", \"jps\": \"OPPOSITE\", \"dijkstra_unit\": \"OPPOSITE\"}, \"verdict_pooled\": \"OPPOSITE\"}, \"k15\": {\"udij_class\": \"OPPOSITE\", \"udij_rank\": 5, \"udij_ratio\": 1.6310051031502248, \"udij_nea\nlanding k15 pooled {'S': 21.595219929194194, 'class_shares': {'OPPOSITE': 1.0}, 'verdict': 'OPPOSITE'}", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
````

### [68] THINKING · 2026-10-26 14:31:04 UTC

```
I'll write the builder script into scripts/, taking the source folder as an argument to avoid hardcoding paths, but first I need to check the RSA, placement, and verdict JSON layouts it copies from.
```

### [69] TOOL CALL — Bash · 2026-10-26 14:31:04 UTC

```
Inspect RSA, placement, lexical and verdict JSON layouts:
SRC=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46; grep -n "^Z95" $SRC/src/common.py; SP=/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-VVA3P0ocZNA2/39a5c6e0-c154-4645-bb18-199862447326/scratchpad; $SP/venv/bin/python -B - <<'EOF'
import json
SRC="/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46"
rsa = json.load(open(f"{SRC}/results/rsa.json")); print("rsa keys", list(rsa.keys())); print(" 32b|mname", {k: (v if not isinstance(v, dict) else list(v.keys())) for k, v in rsa["32b|mname"].items()})
print(" models R_lex", rsa["32b|mname"]["models"]["R_lex"])
pl = json.load(open(f"{SRC}/results/placement.json")); print("placement keys", list(pl.keys())); v = pl["32b|mcode_PRIMARY_R1"]; print({k: v[k] for k in v if k != "rows"})
lr = json.load(open(f"{SRC}/results/lexical_regression.json")); print("lexreg keys", list(lr.keys())); print({k: (lr["32b|mname"]["k15"][k] if k != "rows" else "...") for k in lr["32b|mname"]["k15"]})
n4 = json.load(open(f"{SRC}/results/n4_verdict.json")); print("n4 keys", list(n4.keys())); print(" verdict_table", json.dumps(n4["verdict_table"])[:900])
beh = json.load(open(f"{SRC}/results/behavioural_distance.json")); print("beh mds", beh["behavioural_coordinates_mds"], beh["behavioural_mds_stress1"])
import math
dl = json.load(open(f"{SRC}/data/descriptions_v0.json")); print("R_desc_lex has nan", any(isinstance(x, float) and math.isnan(x) for row in dl["R_desc_lex"] for x in row))
sur = json.load(open(f"{SRC}/results/surface_rdm.json")); print("R_len mname has nan", any(isinstance(x, float) and math.isnan(x) for row in sur["R_len"]["mcode"] for x in row))
EOF
```

### [70] TOOL RESULT — Bash · 2026-10-26 14:31:04 UTC

```
{"stdout": "325:Z95 = 1.959963984540054\nrsa keys ['32b|mname', '32b|mdesc', '32b|mlex', '32b|mcode_PRIMARY_R1', '32b|mcode_PRIMARY_R2', '32b|mcode_M32_R1', '8b|mname', '8b|mdesc', '8b|mcode_PRIMARY_R1', 'name_evocation']\n 32b|mname {'present': ['bfs', 'dfs', 'bibfs', 'iddfs', 'astar', 'gbfs', 'dijkstra_unit', 'idastar', 'jps', 'biastar'], 'noise_ceiling_upper': 0.9959743660912583, 'split_half_spearman_brown': 0.9919649379108838, 'models': ['R_lex', 'R_beh', 'R_beh_order', 'R_DS', 'R_surface', 'R_len', 'R_desc_lex'], 'rho_differences_bootstrap': ['R_lex-R_beh', 'R_beh-R_lex', 'R_surface-R_beh']}\n models R_lex {'rho': 0.463768115942029, 'p_exact': 0.0025035824514991183, 'n_perms': 3628800, 'n_pairs': 45}\nplacement keys ['32b|mcode_PRIMARY_R1', '32b|mcode_PRIMARY_R2', '32b|mcode_M32_R1', '8b|mcode_PRIMARY_R1']\n{'frame': 'mcode_PRIMARY_R1', 'model': '32b', 'block': 33, 'k': 15, 'readout': 'R1', 'G_place': {'loo_accuracy': 0.8547008547008547, 'gate': 0.7, 'pass': True}, 'frame_g': {'idastar': 32.8627058350452, 'dijkstra_unit': 16.648370975564}, 'frame_classes': {'idastar': 'OPPOSITE', 'dijkstra_unit': 'EDGE'}, 'frame_median': 24.7555384053046, 'base_accuracy_own_label': 1.0, 'udij_survivors': {'n': 15, 'n_edge': 15, 'share_edge': 1.0, 'wilson95': [0.7961166989641515, 1.0], 'share_nearest_banned': 0.13333333333333333, 'nearest_algorithm_counts': {'bfs': 0, 'dfs': 0, 'bibfs': 0, 'iddfs': 0, 'astar': 0, 'gbfs': 2, 'dijkstra_unit': 13, 'idastar': 0, 'jps': 0, 'biastar': 0}, 'mannwhitney_p_vs_frame_udij_loo': 8.978175298633825e-05, 'frame_udij_loo_g_median': 16.50621523534173, 'survivor_g_median': 20.236814302673473}, 'P8_pass': True}\nlexreg keys ['32b|mname', '32b|mlex', '8b|mname', 'descriptive_mdesc_mcode']\n{'rows': '...', 'spearman_L1': -0.6499638673269305, 'perm_p_L1': 0.00517, 'partial_L1_given_length': -0.6680008813359436, 'spearman_L2': -0.3896337570144074, 'perm_p_L2': 0.07371, 'partial_L2_given_length': -0.4187532975227804, 'spearman_L3': -0.7680054866576358, 'perm_p_L3': 0.00062, 'partial_L3_given_length': -0.774587212522645, 'within_algorithm': {'pearson_demeaned_g_L2': -0.2790165536294543, 'exact_p_lower': 0.15650720164609053, 'n_perms': 7776}}\nn4 keys ['utc', 'predictions', 'secondary_statistics', 'verdict_table', 'mcode_source_robustness', 'k_sensitive', 'mcode_class_k15', 'mdesc_class_k15', 'named_outcome', 'mcode_verdict_key', 'statement', 'mdesc_excluded_algorithms']\n verdict_table {\"32b|mname\": {\"k10\": {\"verdict\": \"OPPOSITE\", \"udij_class\": \"OPPOSITE\"}, \"k15\": {\"verdict\": \"OPPOSITE\", \"udij_class\": \"OPPOSITE\"}}, \"32b|mlex\": {\"k10\": {\"verdict\": \"OPPOSITE\", \"udij_class\": \"OPPOSITE\"}, \"k15\": {\"verdict\": \"OPPOSITE\", \"udij_class\": \"OPPOSITE\"}}, \"32b|mdesc\": {\"k10\": {\"verdict\": \"NEITHER\", \"udij_class\": \"OPPOSITE\"}, \"k15\": {\"verdict\": \"OPPOSITE\", \"udij_class\": \"OPPOSITE\"}}, \"32b|mcode_PRIMARY_R1\": {\"k10\": {\"verdict\": \"EDGE\", \"udij_class\": \"EDGE\"}, \"k15\": {\"verdict\": \"EDGE\", \"udij_class\": \"EDGE\"}}, \"32b|mcode_M32_R1\": {\"k10\": {\"verdict\": \"EDGE\", \"udij_class\": \"EDGE\"}, \"k15\": {\"verdict\": \"EDGE\", \"udij_class\": \"EDGE\"}}, \"32b|mcode_M8_R1\": {\"k10\": {\"verdict\": null, \"udij_class\": null}, \"k15\": {\"verdict\": null, \"udij_class\": null}}, \"32b|mcode_PRIMARY_R2\": {\"k10\": {\"verdict\": \"EDGE\", \"udij_class\": \"EDGE\"}, \"k15\": {\"verdict\": \"EDGE\", \"udij_class\": \"EDGE\"}}, \"8b|mname\": {\"k10\": {\nbeh mds {'bfs': [-0.34673440399856736, 0.19112072400095614], 'dfs': [-0.30561226838217936, -0.18992006166279363], 'bibfs': [-0.23416381224596522, 0.15697815268410648], 'iddfs': [-0.548185278558491, 0.08858969556225368], 'astar': [0.2784629478861139, 0.16790474043437723], 'gbfs': [0.3626037538435796, 0.10028527639028076], 'dijkstra_unit': [-0.15678491404439146, 0.21841689104990122], 'idastar': [-0.005970517275867448, -0.8533047952471118], 'jps': [0.5968013870772945, -0.014945909136261622], 'biastar': [0.35958310569847424, 0.13487528592429207]} 0.32074450965089374\nR_desc_lex has nan False\nR_len mname has nan True", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [71] ASSISTANT · 2026-10-26 14:31:46 UTC

```
I have the layouts. Writing the builder script (source folder passed as an argument):
```

### [72] TOOL CALL — Write · 2026-10-26 14:31:46 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/scripts/build_mini_demo_data.py

#!/usr/bin/env python3
"""Build mini_demo_data.json for code_demo.ipynb from the TP-G iteration-9 artifact folder (art_VVA3P0ocZNA2).

The demo reruns the CPU analysis stages (geometry, landing, bootstrap, lexical regression, RSA, placement, figures)
on a 99-point subset of the cached Qwen3-32B (nf4) activation states, at the block L* committed for each manifold:

  * M-name           template 0 x 3 aliases x 10 algorithms = 30 of the 300 alias prompts (S-mean readout)
  * M-code PRIMARY   the first 9 programs (set rank 0-8) of each algorithm with >= 10 programs = 54 of 117 (R1 readout)
  * placement SURV   the 15 unit-weight-Dijkstra survivor programs, in the same M-code coordinates

Every vector is the cached float16 state itself, stored losslessly as base64 (little-endian float16, 5120 values).
The small inputs the analysis reads (model RDMs, lexical alias measures, landing-null inputs, implemented counts)
and the full-run reference results are copied into "metadata".

Usage:  python scripts/build_mini_demo_data.py --src <artifact folder> [--out mini_demo_data.json]
"""

from __future__ import annotations

import argparse
import base64
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

CANON_ORDER = ["bfs", "dfs", "bibfs", "iddfs", "astar", "gbfs", "dijkstra_unit", "idastar", "jps", "biastar"]
B5 = ["bfs", "dfs", "iddfs", "astar", "gbfs"]
NB5 = ["bibfs", "biastar", "idastar", "jps", "dijkstra_unit"]
UDIJ = "dijkstra_unit"
MCODE_MIN = 10


def b64_f16(v: np.ndarray) -> str:
    return base64.b64encode(np.ascontiguousarray(v, dtype="<f2").tobytes()).decode("ascii")


def read_json(p: Path) -> Any:
    return json.loads(p.read_text())


def read_jsonl(p: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


def no_nan(x: Any) -> Any:
    """JSON has no NaN: matrices keep None where the source had NaN (np.array(..., dtype=float) restores it)."""
    if isinstance(x, list):
        return [no_nan(v) for v in x]
    if isinstance(x, dict):
        return {k: no_nan(v) for k, v in x.items()}
    if isinstance(x, float) and math.isnan(x):
        return None
    return x


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--src", required=True, help="artifact folder that contains method.py, results/ and cache/states/")
    ap.add_argument("--out", default="mini_demo_data.json")
    ap.add_argument("--mname-templates", default="0", help="comma-separated M-name template indices to keep")
    ap.add_argument("--mcode-per-alg", type=int, default=9, help="programs kept per M-code algorithm (set ranks 0..n-1)")
    a = ap.parse_args()
    S = Path(a.src)

    c2 = read_json(S / "predictions" / "commit2.json")
    L_name = int(c2["manifolds"]["32b|mname"]["L_star"])
    L_code = int(c2["manifolds"]["32b|mcode_PRIMARY_R1"]["L_star"])
    full = read_json(S / "full_method_out.json")
    prompts = {e["metadata_point_id"]: e["input"] for ds in full["datasets"] if ds["dataset"] == "tpg_points"
               for e in ds["examples"]}

    examples: list[dict[str, Any]] = []
    # ------------------------------------------------------------------ M-name (alias prompts, S-mean, block L*)
    z = np.load(S / "cache" / "states" / "mname_32b.npz")
    smean = z["smean"]                                          # [300, 31 blocks, 5120] float16, loaded once
    bi = [int(b) for b in z["blocks"]].index(L_name)
    templates = {int(t) for t in a.mname_templates.split(",")}
    for i in range(len(z["algorithm"])):
        t, j, alg = int(z["template"][i]), int(z["alias"][i]), str(z["algorithm"][i])
        if t not in templates:
            continue
        pid = f"mname|{alg}|t{t}|j{j}"
        examples.append({"point_id": pid, "manifold": "mname", "algorithm": alg, "banned": alg in B5,
                         "group": int(z["group"][i]), "template": t, "alias_index": j, "block": L_name,
                         "readout": "S-mean", "input": prompts[pid], "x_f16_b64": b64_f16(smean[i, bi])})
    # ------------------------------------------------------------------ M-code PRIMARY frame + SURV placements (R1)
    zc = np.load(S / "cache" / "states" / "mcode_32b.npz")
    R = zc["R"]                                                 # [341, 4 readouts, 31 blocks, 5120] float16
    keys = list(zc["keys"])
    ri = list(zc["readouts"]).index("R1")
    bc = [int(b) for b in zc["blocks"]].index(L_code)
    ms = read_json(S / "data" / "mcode_sets.json")
    for alg in CANON_ORDER:
        prog = ms["sets"]["PRIMARY"][alg]
        if len(prog) < MCODE_MIN:                               # same exclusion rule as load_manifold()
            continue
        for rank, p in enumerate(prog[:a.mcode_per_alg]):
            examples.append({"point_id": p["uid"], "manifold": "mcode_PRIMARY_R1", "algorithm": alg,
                             "banned": alg in B5, "group": rank % 10, "set_rank": rank, "source": p.get("source"),
                             "author": p.get("author"), "block": L_code, "readout": "R1",
                             "scrubbed_sha256": p["scrubbed_sha256"], "input": p["scrubbed"],
                             "x_f16_b64": b64_f16(R[keys.index(p["scrubbed_sha256"]), ri, bc])})
    for p in ms["placement"]:
        if p["set"] == "SURV" and p["algorithm"] == UDIJ and p["scrubbed_sha256"] in keys:
            examples.append({"point_id": p["uid"], "manifold": "placement_SURV", "algorithm": UDIJ, "banned": False,
                             "set": p["set"], "condition": p.get("condition"), "other_name": p.get("other_name"),
                             "g_scrub_pass": p.get("g_scrub_pass"), "block": L_code, "readout": "R1",
                             "scrubbed_sha256": p["scrubbed_sha256"], "input": p["scrubbed"],
                             "x_f16_b64": b64_f16(R[keys.index(p["scrubbed_sha256"]), ri, bc])})

    # ------------------------------------------------------------------ small analysis inputs
    e44 = S / "inputs" / "e44"
    base = read_jsonl(e44 / "data" / "labelled_C6_baseline.jsonl")
    ban = [r for f in ("labelled_C6_ban.jsonl", "labelled_C6_confirm.jsonl") for r in read_jsonl(e44 / "data" / f)]
    land = read_json(e44 / "results" / "landing.json")
    beh = read_json(S / "results" / "behavioural_distance.json")
    lex = read_json(S / "results" / "lexical.json")
    sur = read_json(S / "results" / "surface_rdm.json")
    dl = read_json(S / "data" / "descriptions_v0.json")

    # ------------------------------------------------------------------ full-run reference results (all 300/117 points)
    geo = read_json(S / "results" / "geometry_all.json")
    rsa = read_json(S / "results" / "rsa.json")
    lr = read_json(S / "results" / "lexical_regression.json")
    pl = read_json(S / "results" / "placement.json")
    n4 = read_json(S / "results" / "n4_verdict.json")
    ref_geo = {}
    for key, r in geo.items():
        Ls = r["L_star"]
        bs = Ls.get("bootstrap", {}).get("k15", {})
        ref_geo[key] = {"L_star": Ls["block"], "n_points": r["n_points"], "summary": r["summary"],
                        "landing_pooled_verdict": {k: Ls["landing"][k]["pooled"].get("verdict") for k in ("k10", "k15")},
                        "bootstrap_k15": {"n_boot": bs.get("n_boot"), "edge_probability": bs.get("edge_probability"),
                                          "class_stability": bs.get("class_stability"),
                                          "udij_ratio_ci95": bs.get("udij_ratio_ci95")},
                        "split_half_spearman_brown_k15": Ls["split_half"]["k15"]["spearman_brown"],
                        "crossnobis_classes": Ls.get("crossnobis", {}).get("classes"),
                        "zscored_classes": Ls.get("zscored", {}).get("classes"),
                        "euclid_centroid_classes": Ls["describe"]["euclid_centroid"]["classes"],
                        "robustness_udij_class_counts": Ls.get("robustness", {}).get("udij_class_counts")}
    ref_rsa = {key: {m: {"rho": v["rho"], "p_exact": v["p_exact"]} for m, v in r["models"].items()}
               for key, r in rsa.items() if key != "name_evocation"}
    ref_lex = {key: {k: {f: lr[key][k][f] for f in ("spearman_L1", "perm_p_L1", "spearman_L3", "perm_p_L3")}
                     for k in ("k10", "k15")} | {"P4_pass": lr[key]["P4_pass"]}
               for key in ("32b|mname", "32b|mlex", "8b|mname") if key in lr}
    ref_pl = {key: {"G_place": v["G_place"], "frame_classes": v["frame_classes"], "P8_pass": v["P8_pass"],
                    "udij_survivors": {f: v["udij_survivors"][f] for f in ("n", "n_edge", "share_edge",
                                                                           "nearest_algorithm_counts")}}
              for key, v in pl.items()}
    ref_n4 = {"named_outcome": n4["named_outcome"], "mcode_class_k15": n4["mcode_class_k15"],
              "mdesc_class_k15": n4["mdesc_class_k15"], "mcode_source_robustness": n4["mcode_source_robustness"],
              "k_sensitive": n4["k_sensitive"], "verdict_table": n4["verdict_table"], "statement": n4["statement"],
              "predictions_pass": {p: v.get("pass") for p, v in n4["predictions"].items()}}

    counts = Counter(e["manifold"] for e in examples)
    meta = {
        "title": "Mapping grid algorithms with and without their names (TP-G, iteration 9): demo subset",
        "source_artifact": "art_VVA3P0ocZNA2 (gen_art_experiment_46, invention-loop iteration 9)",
        "model": {"repo": "unsloth/Qwen3-32B-bnb-4bit", "revision": "7f721e74a6a8cc9ee352f7e49303a2c1705f9083",
                  "precision": "nf4", "n_layers": 64, "d_model": 5120, "ref_block": 31},
        "vector_encoding": "x_f16_b64 = base64 of the cached little-endian float16 state (5120 values): "
                           "np.frombuffer(base64.b64decode(s), dtype='<f2')",
        "selection": {"mname": f"templates {sorted(templates)} x aliases 0-2 x 10 algorithms "
                               f"({counts['mname']} of 300 points), S-mean readout, block {L_name}",
                      "mcode_PRIMARY_R1": f"set ranks 0-{a.mcode_per_alg - 1} of every algorithm with >= {MCODE_MIN} "
                                          f"PRIMARY programs ({counts['mcode_PRIMARY_R1']} of 117 points), "
                                          f"R1 readout (mean over code tokens), block {L_code}",
                      "placement_SURV": f"all {counts['placement_SURV']} unit-Dijkstra survivor programs (C6 ban "
                                        f"screen + confirm), same readout and block as the M-code frame"},
        "n_examples": len(examples), "examples_per_manifold": dict(counts),
        "L_star": {"32b|mname": L_name, "32b|mcode_PRIMARY_R1": L_code},
        "landing_inputs": {"C6_baseline_adj_label_counts": dict(Counter(r.get("adj_label") for r in base)),
                           "C6_ban_adj_label_counts": dict(Counter(r.get("adj_label") for r in ban)),
                           "forced_rates_e44": {k: max(0.0, float(v) - 0.0125)
                                                for k, v in land["primary"]["null_C_probs"].items()},
                           "survivors_screen": [UDIJ] * 6, "survivors_confirm": [UDIJ] * 9},
        "model_rdms": no_nan({"R_lex": lex["R_lex"], "R_beh": beh["d_beh_lambda0.5"], "R_beh_order": beh["d_order"],
                              "R_DS": beh["d_DS"], "R_surface": sur["R_surface"], "R_len": sur["R_len"],
                              "R_desc_lex": dl["R_desc_lex"]}),
        "lexical_aliases": lex["aliases"],
        "behavioural_mds": {"coordinates": beh["behavioural_coordinates_mds"],
                            "stress1": beh["behavioural_mds_stress1"]},
        "full_run_reference": no_nan({"geometry": ref_geo, "rsa": ref_rsa, "lexical_regression": ref_lex,
                                      "placement": ref_pl, "n4_verdict": ref_n4}),
    }
    out = Path(a.out)
    out.write_text(json.dumps({"metadata": meta, "examples": examples}, indent=1, allow_nan=False))
    print(f"wrote {out} ({out.stat().st_size / 1e6:.2f} MB): {len(examples)} examples {dict(counts)}")


if __name__ == "__main__":
    main()
```

### [73] TOOL RESULT — Write · 2026-10-26 14:31:46 UTC

```
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/scripts/build_mini_demo_data.py", "content": "#!/usr/bin/env python3\n\"\"\"Build mini_demo_data.json for code_demo.ipynb from the TP-G iteration-9 artifact folder (art_VVA3P0ocZNA2).\n\nThe demo reruns the CPU analysis stages (geometry, landing, bootstrap, lexical regression, RSA, placement, figures)\non a 99-point subset of the cached Qwen3-32B (nf4) activation states, at the block L* committed for each manifold:\n\n  * M-name           template 0 x 3 aliases x 10 algorithms = 30 of the 300 alias prompts (S-mean readout)\n  * M-code PRIMARY   the first 9 programs (set rank 0-8) of each algorithm with >= 10 programs = 54 of 117 (R1 readout)\n  * placement SURV   the 15 unit-weight-Dijkstra survivor programs, in the same M-code coordinates\n\nEvery vector is the cached float16 state itself, stored losslessly as base64 (little-endian float16, 5120 values).\nThe small inputs the analysis reads (model RDMs, lexical alias measures, landing-null inputs, implemented counts)\nand the full-run reference results are copied into \"metadata\".\n\nUsage:  python scripts/build_mini_demo_data.py --src <artifact folder> [--out mini_demo_data.json]\n\"\"\"\n\nfrom __future__ import annotations\n\nimport argparse\nimport base64\nimport json\nimport math\nfrom collections import Counter\nfrom pathlib import Path\nfrom typing import Any\n\nimport numpy as np\n\nCANON_ORDER = [\"bfs\", \"dfs\", \"bibfs\", \"iddfs\", \"astar\", \"gbfs\", \"dijkstra_unit\", \"idastar\", \"jps\", \"biastar\"]\nB5 = [\"bfs\", \"dfs\", \"iddfs\", \"astar\", \"gbfs\"]\nNB5 = [\"bibfs\", \"biastar\", \"idastar\", \"jps\", \"dijkstra_unit\"]\nUDIJ = \"dijkstra_unit\"\nMCODE_MIN = 10\n\n\ndef b64_f16(v: np.ndarray) -> str:\n    return base64.b64encode(np.ascontiguousarray(v, dtype=\"<f2\").tobytes()).decode(\"ascii\")\n\n\ndef read_json(p: Path) -> Any:\n    return json.loads(p.read_text())\n\n\ndef read_jsonl(p: Path) -> list[dict[str, Any]]:\n    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]\n\n\ndef no_nan(x: Any) -> Any:\n    \"\"\"JSON has no NaN: matrices keep None where the source had NaN (np.array(..., dtype=float) restores it).\"\"\"\n    if isinstance(x, list):\n        return [no_nan(v) for v in x]\n    if isinstance(x, dict):\n        return {k: no_nan(v) for k, v in x.items()}\n    if isinstance(x, float) and math.isnan(x):\n        return None\n    return x\n\n\ndef main() -> None:\n    ap = argparse.ArgumentParser(description=__doc__.split(\"\\n\")[0])\n    ap.add_argument(\"--src\", required=True, help=\"artifact folder that contains method.py, results/ and cache/states/\")\n    ap.add_argument(\"--out\", default=\"mini_demo_data.json\")\n    ap.add_argument(\"--mname-templates\", default=\"0\", help=\"comma-separated M-name template indices to keep\")\n    ap.add_argument(\"--mcode-per-alg\", type=int, default=9, help=\"programs kept per M-code algorithm (set ranks 0..n-1)\")\n    a = ap.parse_args()\n    S = Path(a.src)\n\n    c2 = read_json(S / \"predictions\" / \"commit2.json\")\n    L_name = int(c2[\"manifolds\"][\"32b|mname\"][\"L_star\"])\n    L_code = int(c2[\"manifolds\"][\"32b|mcode_PRIMARY_R1\"][\"L_star\"])\n    full = read_json(S / \"full_method_out.json\")\n    prompts = {e[\"metadata_point_id\"]: e[\"input\"] for ds in full[\"datasets\"] if ds[\"dataset\"] == \"tpg_points\"\n               for e in ds[\"examples\"]}\n\n    examples: list[dict[str, Any]] = []\n    # ------------------------------------------------------------------ M-name (alias prompts, S-mean, block L*)\n    z = np.load(S / \"cache\" / \"states\" / \"mname_32b.npz\")\n    smean = z[\"smean\"]                                          # [300, 31 blocks, 5120] float16, loaded once\n    bi = [int(b) for b in z[\"blocks\"]].index(L_name)\n    templates = {int(t) for t in a.mname_templates.split(\",\")}\n    for i in range(len(z[\"algorithm\"])):\n        t, j, alg = int(z[\"template\"][i]), int(z[\"alias\"][i]), str(z[\"algorithm\"][i])\n        if t not in templates:\n            continue\n        pid = f\"mname|{alg}|t{t}|j{j}\"\n        examples.append({\"point_id\": pid, \"manifold\": \"mname\", \"algorithm\": alg, \"banned\": alg in B5,\n                         \"group\": int(z[\"group\"][i]), \"template\": t, \"alias_index\": j, \"block\": L_name,\n                         \"readout\": \"S-mean\", \"input\": prompts[pid], \"x_f16_b64\": b64_f16(smean[i, bi])})\n    # ------------------------------------------------------------------ M-code PRIMARY frame + SURV placements (R1)\n    zc = np.load(S / \"cache\" / \"states\" / \"mcode_32b.npz\")\n    R = zc[\"R\"]                                                 # [341, 4 readouts, 31 blocks, 5120] float16\n    keys = list(zc[\"keys\"])\n    ri = list(zc[\"readouts\"]).index(\"R1\")\n    bc = [int(b) for b in zc[\"blocks\"]].index(L_code)\n    ms = read_json(S / \"data\" / \"mcode_sets.json\")\n    for alg in CANON_ORDER:\n        prog = ms[\"sets\"][\"PRIMARY\"][alg]\n        if len(prog) < MCODE_MIN:                               # same exclusion rule as load_manifold()\n            continue\n        for rank, p in enumerate(prog[:a.mcode_per_alg]):\n            examples.append({\"point_id\": p[\"uid\"], \"manifold\": \"mcode_PRIMARY_R1\", \"algorithm\": alg,\n                             \"banned\": alg in B5, \"group\": rank % 10, \"set_rank\": rank, \"source\": p.get(\"source\"),\n                             \"author\": p.get(\"author\"), \"block\": L_code, \"readout\": \"R1\",\n                             \"scrubbed_sha256\": p[\"scrubbed_sha256\"], \"input\": p[\"scrubbed\"],\n                             \"x_f16_b64\": b64_f16(R[keys.index(p[\"scrubbed_sha256\"]), ri, bc])})\n    for p in ms[\"placement\"]:\n        if p[\"set\"] == \"SURV\" and p[\"algorithm\"] == UDIJ and p[\"scrubbed_sha256\"] in keys:\n            examples.append({\"point_id\": p[\"uid\"], \"manifold\": \"placement_SURV\", \"algorithm\": UDIJ, \"banned\": False,\n                             \"set\": p[\"set\"], \"condition\": p.get(\"condition\"), \"other_name\": p.get(\"other_name\"),\n                             \"g_scrub_pass\": p.get(\"g_scrub_pass\"), \"block\": L_code, \"readout\": \"R1\",\n                             \"scrubbed_sha256\": p[\"scrubbed_sha256\"], \"input\": p[\"scrubbed\"],\n                             \"x_f16_b64\": b64_f16(R[keys.index(p[\"scrubbed_sha256\"]), ri, bc])})\n\n    # ------------------------------------------------------------------ small analysis inputs\n    e44 = S / \"inputs\" / \"e44\"\n    base = read_jsonl(e44 / \"data\" / \"labelled_C6_baseline.jsonl\")\n    ban = [r for f in (\"labelled_C6_ban.jsonl\", \"labelled_C6_confirm.jsonl\") for r in read_jsonl(e44 / \"data\" / f)]\n    land = read_json(e44 / \"results\" / \"landing.json\")\n    beh = read_json(S / \"results\" / \"behavioural_distance.json\")\n    lex = read_json(S / \"results\" / \"lexical.json\")\n    sur = read_json(S / \"results\" / \"surface_rdm.json\")\n    dl = read_json(S / \"data\" / \"descriptions_v0.json\")\n\n    # ------------------------------------------------------------------ full-run reference results (all 300/117 points)\n    geo = read_json(S / \"results\" / \"geometry_all.json\")\n    rsa = read_json(S / \"results\" / \"rsa.json\")\n    lr = read_json(S / \"results\" / \"lexical_regression.json\")\n    pl = read_json(S / \"results\" / \"placement.json\")\n    n4 = read_json(S / \"results\" / \"n4_verdict.json\")\n    ref_geo = {}\n    for key, r in geo.items():\n        Ls = r[\"L_star\"]\n        bs = Ls.get(\"bootstrap\", {}).get(\"k15\", {})\n        ref_geo[key] = {\"L_star\": Ls[\"block\"], \"n_points\": r[\"n_points\"], \"summary\": r[\"summary\"],\n                        \"landing_pooled_verdict\": {k: Ls[\"landing\"][k][\"pooled\"].get(\"verdict\") for k in (\"k10\", \"k15\")},\n                        \"bootstrap_k15\": {\"n_boot\": bs.get(\"n_boot\"), \"edge_probability\": bs.get(\"edge_probability\"),\n                                          \"class_stability\": bs.get(\"class_stability\"),\n                                          \"udij_ratio_ci95\": bs.get(\"udij_ratio_ci95\")},\n                        \"split_half_spearman_brown_k15\": Ls[\"split_half\"][\"k15\"][\"spearman_brown\"],\n                        \"crossnobis_classes\": Ls.get(\"crossnobis\", {}).get(\"classes\"),\n                        \"zscored_classes\": Ls.get(\"zscored\", {}).get(\"classes\"),\n                        \"euclid_centroid_classes\": Ls[\"describe\"][\"euclid_centroid\"][\"classes\"],\n                        \"robustness_udij_class_counts\": Ls.get(\"robustness\", {}).get(\"udij_class_counts\")}\n    ref_rsa = {key: {m: {\"rho\": v[\"rho\"], \"p_exact\": v[\"p_exact\"]} for m, v in r[\"models\"].items()}\n               for key, r in rsa.items() if key != \"name_evocation\"}\n    ref_lex = {key: {k: {f: lr[key][k][f] for f in (\"spearman_L1\", \"perm_p_L1\", \"spearman_L3\", \"perm_p_L3\")}\n                     for k in (\"k10\", \"k15\")} | {\"P4_pass\": lr[key][\"P4_pass\"]}\n               for key in (\"32b|mname\", \"32b|mlex\", \"8b|mname\") if key in lr}\n    ref_pl = {key: {\"G_place\": v[\"G_place\"], \"frame_classes\": v[\"frame_classes\"], \"P8_pass\": v[\"P8_pass\"],\n                    \"udij_survivors\": {f: v[\"udij_survivors\"][f] for f in (\"n\", \"n_edge\", \"share_edge\",\n                                                                           \"nearest_algorithm_counts\")}}\n              for key, v in pl.items()}\n    ref_n4 = {\"named_outcome\": n4[\"named_outcome\"], \"mcode_class_k15\": n4[\"mcode_class_k15\"],\n              \"mdesc_class_k15\": n4[\"mdesc_class_k15\"], \"mcode_source_robustness\": n4[\"mcode_source_robustness\"],\n              \"k_sensitive\": n4[\"k_sensitive\"], \"verdict_table\": n4[\"verdict_table\"], \"statement\": n4[\"statement\"],\n              \"predictions_pass\": {p: v.get(\"pass\") for p, v in n4[\"predictions\"].items()}}\n\n    counts = Counter(e[\"manifold\"] for e in examples)\n    meta = {\n        \"title\": \"Mapping grid algorithms with and without their names (TP-G, iteration 9): demo subset\",\n        \"source_artifact\": \"art_VVA3P0ocZNA2 (gen_art_experiment_46, invention-loop iteration 9)\",\n        \"model\": {\"repo\": \"unsloth/Qwen3-32B-bnb-4bit\", \"revision\": \"7f721e74a6a8cc9ee352f7e49303a2c1705f9083\",\n                  \"precision\": \"nf4\", \"n_layers\": 64, \"d_model\": 5120, \"ref_block\": 31},\n        \"vector_encoding\": \"x_f16_b64 = base64 of the cached little-endian float16 state (5120 values): \"\n                           \"np.frombuffer(base64.b64decode(s), dtype='<f2')\",\n        \"selection\": {\"mname\": f\"templates {sorted(templates)} x aliases 0-2 x 10 algorithms \"\n                               f\"({counts['mname']} of 300 points), S-mean readout, block {L_name}\",\n                      \"mcode_PRIMARY_R1\": f\"set ranks 0-{a.mcode_per_alg - 1} of every algorithm with >= {MCODE_MIN} \"\n                                          f\"PRIMARY programs ({counts['mcode_PRIMARY_R1']} of 117 points), \"\n                                          f\"R1 readout (mean over code tokens), block {L_code}\",\n                      \"placement_SURV\": f\"all {counts['placement_SURV']} unit-Dijkstra survivor programs (C6 ban \"\n                                        f\"screen + confirm), same readout and block as the M-code frame\"},\n        \"n_examples\": len(examples), \"examples_per_manifold\": dict(counts),\n        \"L_star\": {\"32b|mname\": L_name, \"32b|mcode_PRIMARY_R1\": L_code},\n        \"landing_inputs\": {\"C6_baseline_adj_label_counts\": dict(Counter(r.get(\"adj_label\") for r in base)),\n                           \"C6_ban_adj_label_counts\": dict(Counter(r.get(\"adj_label\") for r in ban)),\n                           \"forced_rates_e44\": {k: max(0.0, float(v) - 0.0125)\n                                                for k, v in land[\"primary\"][\"null_C_probs\"].items()},\n                           \"survivors_screen\": [UDIJ] * 6, \"survivors_confirm\": [UDIJ] * 9},\n        \"model_rdms\": no_nan({\"R_lex\": lex[\"R_lex\"], \"R_beh\": beh[\"d_beh_lambda0.5\"], \"R_beh_order\": beh[\"d_order\"],\n                              \"R_DS\": beh[\"d_DS\"], \"R_surface\": sur[\"R_surface\"], \"R_len\": sur[\"R_len\"],\n                              \"R_desc_lex\": dl[\"R_desc_lex\"]}),\n        \"lexical_aliases\": lex[\"aliases\"],\n        \"behavioural_mds\": {\"coordinates\": beh[\"behavioural_coordinates_mds\"],\n                            \"stress1\": beh[\"behavioural_mds_stress1\"]},\n        \"full_run_reference\": no_nan({\"geometry\": ref_geo, \"rsa\": ref_rsa, \"lexical_regression\": ref_lex,\n                                      \"placement\": ref_pl, \"n4_verdict\": ref_n4}),\n    }\n    out = Path(a.out)\n    out.write_text(json.dumps({\"metadata\": meta, \"examples\": examples}, indent=1, allow_nan=False))\n    print(f\"wrote {out} ({out.stat().st_size / 1e6:.2f} MB): {len(examples)} examples {dict(counts)}\")\n\n\nif __name__ == \"__main__\":\n    main()\n", "structuredPatch": [], "originalFile": null, "userModified": false}
```

### [74] TOOL CALL — Bash · 2026-10-26 14:31:52 UTC

```
Build mini_demo_data.json from the source artifact:
SP=/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-VVA3P0ocZNA2/39a5c6e0-c154-4645-bb18-199862447326/scratchpad; WS=/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2; cd $WS && time $SP/venv/bin/python -B scripts/build_mini_demo_data.py --src /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46 --out $WS/mini_demo_data.json && ls -la $WS/mini_demo_data.json && head -c 1500 $WS/mini_demo_data.json
```

### [75] TOOL RESULT — Bash · 2026-10-26 14:31:54 UTC

```
{"stdout": "wrote /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/mini_demo_data.json (1.56 MB): 99 examples {'mname': 30, 'mcode_PRIMARY_R1': 54, 'placement_SURV': 15}\n\nreal\t0m2.594s\nuser\t0m2.012s\nsys\t0m0.190s\n-rw-rw-rw- 1 aii-agent aii-agent 1562275 Oct 26 14:31 /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/mini_demo_data.json\n{\n \"metadata\": {\n  \"title\": \"Mapping grid algorithms with and without their names (TP-G, iteration 9): demo subset\",\n  \"source_artifact\": \"art_VVA3P0ocZNA2 (gen_art_experiment_46, invention-loop iteration 9)\",\n  \"model\": {\n   \"repo\": \"unsloth/Qwen3-32B-bnb-4bit\",\n   \"revision\": \"7f721e74a6a8cc9ee352f7e49303a2c1705f9083\",\n   \"precision\": \"nf4\",\n   \"n_layers\": 64,\n   \"d_model\": 5120,\n   \"ref_block\": 31\n  },\n  \"vector_encoding\": \"x_f16_b64 = base64 of the cached little-endian float16 state (5120 values): np.frombuffer(base64.b64decode(s), dtype='<f2')\",\n  \"selection\": {\n   \"mname\": \"templates [0] x aliases 0-2 x 10 algorithms (30 of 300 points), S-mean readout, block 31\",\n   \"mcode_PRIMARY_R1\": \"set ranks 0-8 of every algorithm with >= 10 PRIMARY programs (54 of 117 points), R1 readout (mean over code tokens), block 33\",\n   \"placement_SURV\": \"all 15 unit-Dijkstra survivor programs (C6 ban screen + confirm), same readout and block as the M-code frame\"\n  },\n  \"n_examples\": 99,\n  \"examples_per_manifold\": {\n   \"mname\": 30,\n   \"mcode_PRIMARY_R1\": 54,\n   \"placement_SURV\": 15\n  },\n  \"L_star\": {\n   \"32b|mname\": 31,\n   \"32b|mcode_PRIMARY_R1\": 33\n  },\n  \"landing_inputs\": {\n   \"C6_baseline_adj_label_counts\": {\n    \"invalid\": 9,\n    \"bfs\": 91\n   },\n   \"C6_ban_adj_label_counts\": {\n    \"other\": 28,\n    \"invalid\": 29,\n    \"dfs\": 16,\n    \"gbfs\": 6,\n    \"dijkstra_unit\": 15,\n    \"bfs\": 4,\n    \"astar\": 2\n   },\n   \"forced_rates_e44\": {\n    \"bibfs\": 0.125,\n    \"dijkstra_unit\": 0.275,\n    \"idastar\":", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [76] THINKING · 2026-10-26 14:32:08 UTC

```
TODO 3 is complete: mini_demo_data.json (1.56 MB, 99 examples — 30 M-name, 54 M-code, 15 survivors) with baseline stats showing Qwen3-32B wrote BFS 91/100 times unrestricted. Moving to TODO 4, I'll load the notebook to build it with NotebookEdit.
```

### [77] TOOL CALL — ToolSearch · 2026-10-26 14:32:08 UTC

```
{'query': 'select:NotebookEdit', 'max_results': 1}
```

### [78] TOOL RESULT — ToolSearch · 2026-10-26 14:32:08 UTC

```
{"matches": ["NotebookEdit"], "query": "select:NotebookEdit", "total_deferred_tools": 28}
```

### [79] ASSISTANT · 2026-10-26 14:34:53 UTC

```
I'll build the notebook with NotebookEdit. In parallel, I'll add Jupyter to my scratch venv so I can iterate quickly before the official clean-environment test.
```

### [80] TOOL CALL — Bash · 2026-10-26 14:34:53 UTC

```
Install Jupyter into the scratch venv:
SP=/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-VVA3P0ocZNA2/39a5c6e0-c154-4645-bb18-199862447326/scratchpad; UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python $SP/venv/bin/python jupyter ipykernel pip && $SP/venv/bin/jupyter nbconvert --version && $SP/venv/bin/python -m pip --version
```

### [81] TOOL RESULT — Bash · 2026-10-26 14:34:53 UTC

```
{"stdout": "", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false, "backgroundTaskId": "blvr4tcib"}
```

### [82] TOOL CALL — Write · 2026-10-26 14:34:53 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb

{
 "cells": [
  {
   "cell_type": "markdown",
   "id": "closing-notes",
   "metadata": {},
   "source": [
    "## Scaling back to the full run\n",
    "\n",
    "* **Parameters.** Set `N_BOOT_32B = 1000`, `N_BOOT_OTHER = 200`, `LANDING_DRAWS = 10000` and `PERM_P_N = 100000` in the config cell (the committed values); `KS`, `K_VERDICT` and `K_SECOND` are already the committed values.\n",
    "* **Data.** The full analysis uses all 300 M-name, 260 M-desc, 300 M-lex and 117 M-code states at every block 17-47 (`cache/states/`, about 0.5 GB of float16 arrays). They stay on the run's storage volume and are rebuilt with the artifact's GPU stages: `method.py mname 32b`, `method.py states 32b mlex ban`, `method.py states 32b mdesc mcode` (about 30 GPU-minutes on one RTX 5090), then `method.py blocks`, `method.py analyse`, `method.py figures`, `method.py outputs`.\n",
    "* **What changes with the data.** Layer selection (`blocks`), the reference-block section, the 5-block robustness grid, name evocation and the 8B / M-desc / M-lex manifolds need those states; every function in this notebook runs on them unchanged once `load_manifold` reads the `.npz` files again.\n",
    "\n",
    "The geometry is correlational: it describes where representations and survivors sit, not whether the model uses this geometry to choose an algorithm."
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

### [83] TOOL RESULT — Write · 2026-10-26 14:34:53 UTC

```
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb", "content": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"closing-notes\",\n   \"metadata\": {},\n   \"source\": [\n    \"## Scaling back to the full run\\n\",\n    \"\\n\",\n    \"* **Parameters.** Set `N_BOOT_32B = 1000`, `N_BOOT_OTHER = 200`, `LANDING_DRAWS = 10000` and `PERM_P_N = 100000` in the config cell (the committed values); `KS`, `K_VERDICT` and `K_SECOND` are already the committed values.\\n\",\n    \"* **Data.** The full analysis uses all 300 M-name, 260 M-desc, 300 M-lex and 117 M-code states at every block 17-47 (`cache/states/`, about 0.5 GB of float16 arrays). They stay on the run's storage volume and are rebuilt with the artifact's GPU stages: `method.py mname 32b`, `method.py states 32b mlex ban`, `method.py states 32b mdesc mcode` (about 30 GPU-minutes on one RTX 5090), then `method.py blocks`, `method.py analyse`, `method.py figures`, `method.py outputs`.\\n\",\n    \"* **What changes with the data.** Layer selection (`blocks`), the reference-block section, the 5-block robustness grid, name evocation and the 8B / M-desc / M-lex manifolds need those states; every function in this notebook runs on them unchanged once `load_manifold` reads the `.npz` files again.\\n\",\n    \"\\n\",\n    \"The geometry is correlational: it describes where representations and survivors sit, not whether the model uses this geometry to choose an algorithm.\"\n   ]\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}\n", "structuredPatch": [], "originalFile": null, "userModified": false}
```

### [84] ASSISTANT · 2026-10-26 14:34:57 UTC

```
The skeleton notebook (with the closing cell) exists. I'll read it once, as NotebookEdit requires, then insert cells in reverse order at the top so they land in sequence.
```

### [85] TOOL CALL — Read · 2026-10-26 14:34:57 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb
```

### [86] TOOL RESULT — Read · 2026-10-26 14:34:57 UTC

```
{"type": "notebook", "file": {"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb", "cells": [{"cellType": "markdown", "source": "## Scaling back to the full run\n\n* **Parameters.** Set `N_BOOT_32B = 1000`, `N_BOOT_OTHER = 200`, `LANDING_DRAWS = 10000` and `PERM_P_N = 100000` in the config cell (the committed values); `KS`, `K_VERDICT` and `K_SECOND` are already the committed values.\n* **Data.** The full analysis uses all 300 M-name, 260 M-desc, 300 M-lex and 117 M-code states at every block 17-47 (`cache/states/`, about 0.5 GB of float16 arrays). They stay on the run's storage volume and are rebuilt with the artifact's GPU stages: `method.py mname 32b`, `method.py states 32b mlex ban`, `method.py states 32b mdesc mcode` (about 30 GPU-minutes on one RTX 5090), then `method.py blocks`, `method.py analyse`, `method.py figures`, `method.py outputs`.\n* **What changes with the data.** Layer selection (`blocks`), the reference-block section, the 5-block robustness grid, name evocation and the 8B / M-desc / M-lex manifolds need those states; every function in this notebook runs on them unchanged once `load_manifold` reads the `.npz` files again.\n\nThe geometry is correlational: it describes where representations and survivors sit, not whether the model uses this geometry to choose an algorithm.", "cell_id": "closing-notes"}]}}
```

### [87] ASSISTANT · 2026-10-26 14:38:41 UTC

```
Now I'll insert the notebook cells, last first, each at the top of the notebook. I'm starting with the results cell: a demo-vs-full-run table and a two-map Isomap figure.
```

### [88] TOOL CALL — NotebookEdit · 2026-10-26 14:38:41 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '# ---------------------------------------------------------------------------------------------- demo vs full run\nref = meta["full_run_reference"]\nKEYS = ["32b|mname", "32b|mcode_PRIMARY_R1"]\nprint("Where does unit-weight Dijkstra sit relative to the banned five?")\nprint("demo = this notebook on the 99-point subset; full = the artifact\'s run on all points (300 M-name, 117 M-code)\\n")\nprint(f"{\'manifold\':21s}{\'k\':>3s} | {\'class: demo\':>11s} {\'full\':>9s} | {\'rank: demo\':>10s} {\'full\':>5s} | "\n      f"{\'g/median: demo\':>14s} {\'full\':>5s} | {\'nearest banned: demo\':>20s} {\'full\':>6s}")\nfor key in KEYS:\n    sd, sf = geo_results[key]["summary"], ref["geometry"][key]["summary"]\n    n_nb = len(geo_results[key]["L_star"]["describe"]["nonbanned_used"])\n    for k in KS:\n        a, b = sd[f"k{k}"], sf[f"k{k}"]\n        print(f"{key:21s}{k:3d} | {a[\'udij_class\']:>11s} {b[\'udij_class\']:>9s} | {a[\'udij_rank\']:>8d}/{n_nb} "\n              f"{b[\'udij_rank\']:>3d}/{n_nb} | {a[\'udij_ratio\']:14.2f} {b[\'udij_ratio\']:5.2f} | "\n              f"{SHORT[a[\'udij_nearest_banned\']]:>20s} {SHORT[b[\'udij_nearest_banned\']]:>6s}")\n\nprint(f"\\nLanding verdict (15 pooled survivors) and stability, k = {K_VERDICT}")\nfor key in KEYS:\n    r, f = geo_results[key]["L_star"], ref["geometry"][key]\n    bd, bf = r["bootstrap"][f"k{K_VERDICT}"], f["bootstrap_k15"]\n    print(f"  {key:21s} landing demo {r[\'landing\'][f\'k{K_VERDICT}\'][\'pooled\'][\'verdict\']:8s} full "\n          f"{f[\'landing_pooled_verdict\'][\'k15\']:8s} | bootstrap P(EDGE) demo {bd[\'edge_probability\'][UDIJ]:.2f} "\n          f"(n={bd[\'n_boot\']}) full {bf[\'edge_probability\'][UDIJ]:.2f} (n={bf[\'n_boot\']}) | split-half S-B demo "\n          f"{r[\'split_half\'][f\'k{K_VERDICT}\'][\'spearman_brown\']:.2f} full {f[\'split_half_spearman_brown_k15\']:.2f}")\n\nprint("\\nRSA: Spearman rho of the class-geodesic RDM with each model RDM (exact Mantel p)")\nfor key in KEYS:\n    parts = []\n    for mn in ("R_lex", "R_beh", "R_surface"):\n        d, f = rsa_results[key]["models"][mn], ref["rsa"][key][mn]\n        parts.append(f"{mn} demo {d[\'rho\']:+.2f} (p {d[\'p_exact\']:.3f}) full {f[\'rho\']:+.2f} (p {f[\'p_exact\']:.3f})")\n    print(f"  {key:21s} " + " | ".join(parts))\n\nlx_d, lx_f = lex_results["32b|mname"], ref["lexical_regression"]["32b|mname"]\nprint(f"\\nP4, M-name alias level, Spearman(g_alias, L1): demo k10 {lx_d[\'k10\'][\'spearman_L1\']:+.2f}, k15 "\n      f"{lx_d[\'k15\'][\'spearman_L1\']:+.2f} (pass {lx_d[\'P4_pass\']}) | full k10 {lx_f[\'k10\'][\'spearman_L1\']:+.2f}, k15 "\n      f"{lx_f[\'k15\'][\'spearman_L1\']:+.2f} (pass {lx_f[\'P4_pass\']})")\npl_d, pl_f = placement_results["32b|mcode_PRIMARY_R1"], ref["placement"]["32b|mcode_PRIMARY_R1"]\nprint(f"P8, survivor programs placed at the EDGE of M-code: demo {pl_d[\'udij_survivors\'][\'n_edge\']}/"\n      f"{pl_d[\'udij_survivors\'][\'n\']} (LOO accuracy {pl_d[\'G_place\'][\'loo_accuracy\']:.2f}) | full "\n      f"{pl_f[\'udij_survivors\'][\'n_edge\']}/{pl_f[\'udij_survivors\'][\'n\']} (LOO accuracy {pl_f[\'G_place\'][\'loo_accuracy\']:.2f})")\n\nn4 = ref["n4_verdict"]\nprint("\\nFull run, k = 15 class of unit Dijkstra on every manifold analysed: " + ", ".join(\n    f"{k} {v[\'k15\'][\'udij_class\']}" for k, v in n4["verdict_table"].items() if v["k15"]["udij_class"]))\nprint(f"Full-run named outcome: {n4[\'named_outcome\']} (M-code {n4[\'mcode_class_k15\']}, M-desc {n4[\'mdesc_class_k15\']}); "\n      f"predictions {n4[\'predictions_pass\']}")\nprint(f"\\nNotebook run time so far: {time.time() - T0:.0f} s")\n\n# ---------------------------------------------------------------------------------------------- one picture\nfig, axes = plt.subplots(1, 2, figsize=(16, 7))\nfor ax, key in zip(axes, KEYS):\n    m_tag, name = key.split("|")\n    z = COORDS[f"{m_tag}_{name}"]\n    Y, labels = z["iso"], z["labels"]\n    kd = geo_results[key]["L_star"]["describe"][f"k{K_VERDICT}"]\n    for a in [a for a in CANON_ORDER if a in set(labels.tolist())]:\n        s = labels == a\n        ax.scatter(Y[s, 0], Y[s, 1], s=80 if a == UDIJ else 35, color=COL[a], alpha=0.9, label=SHORT[a],\n                   edgecolors="red" if a in B5 else ("black" if a == UDIJ else "none"), linewidths=1.2)\n    # geodesic from unit Dijkstra to its nearest banned algorithm, traced on the kNN graph (as in figure (c))\n    nb = kd["nearest_banned"][UDIJ]\n    iu, ib = np.where(labels == UDIJ)[0], np.where(labels == nb)[0]\n    i, j = np.unravel_index(np.argmin(z["geo"][np.ix_(iu, ib)]), (len(iu), len(ib)))\n    _, pred = shortest_path(FROZEN[f"geo_{m_tag}_{name}_k{K_VERDICT}"]["adjacency"], method="D", directed=False,\n                            indices=[iu[i]], return_predecessors=True)\n    path, cur = [], ib[j]\n    while cur >= 0 and cur != iu[i]:\n        path.append(cur)\n        cur = pred[0, cur]\n    path.append(iu[i])\n    ax.plot(Y[path, 0], Y[path, 1], "k--", lw=1.2, label=f"geodesic {SHORT[UDIJ]} -> {SHORT[nb]}")\n    if name.startswith("mcode"):\n        # the 15 survivor programs, embedded out of sample by the fitted Isomap\n        sel = [e for e in data["examples"] if e["manifold"] == "placement_SURV"]\n        Q = np.stack([np.frombuffer(base64.b64decode(e["x_f16_b64"]), dtype="<f2") for e in sel]).astype(np.float64)\n        Yq = z["isomap_model"].transform(Q)\n        ax.scatter(Yq[:, 0], Yq[:, 1], marker="x", s=60, color="black", label=f"{len(sel)} survivor programs")\n    ax.set_title(f"{TITLES[name]}, block {z[\'block\']}\\nunit Dijkstra is {kd[\'classes\'][UDIJ]}: "\n                 f"g/median {kd[\'udij_ratio\']:.2f}, rank {kd[\'udij_rank\']}/{len(kd[\'g\'])} (Isomap k={K_VERDICT})",\n                 fontsize=10)\n    ax.set_xlabel("Isomap 1")\n    ax.set_ylabel("Isomap 2")\n    ax.legend(fontsize=7, ncol=2, loc="best")\nfig.suptitle("Qwen3-32B: the algorithm written when the top five are banned (unit Dijkstra, black outline) sits "\n             "OPPOSITE the banned five (red outline) on the map of names,\\nbut at their EDGE on the map of programs, "\n             "where the actual survivor programs (x) also land", fontsize=11)\nplt.tight_layout()\nplt.show()'}
```

### [89] TOOL RESULT — NotebookEdit · 2026-10-26 14:38:41 UTC

```
{"new_source": "# ---------------------------------------------------------------------------------------------- demo vs full run\nref = meta[\"full_run_reference\"]\nKEYS = [\"32b|mname\", \"32b|mcode_PRIMARY_R1\"]\nprint(\"Where does unit-weight Dijkstra sit relative to the banned five?\")\nprint(\"demo = this notebook on the 99-point subset; full = the artifact's run on all points (300 M-name, 117 M-code)\\n\")\nprint(f\"{'manifold':21s}{'k':>3s} | {'class: demo':>11s} {'full':>9s} | {'rank: demo':>10s} {'full':>5s} | \"\n      f\"{'g/median: demo':>14s} {'full':>5s} | {'nearest banned: demo':>20s} {'full':>6s}\")\nfor key in KEYS:\n    sd, sf = geo_results[key][\"summary\"], ref[\"geometry\"][key][\"summary\"]\n    n_nb = len(geo_results[key][\"L_star\"][\"describe\"][\"nonbanned_used\"])\n    for k in KS:\n        a, b = sd[f\"k{k}\"], sf[f\"k{k}\"]\n        print(f\"{key:21s}{k:3d} | {a['udij_class']:>11s} {b['udij_class']:>9s} | {a['udij_rank']:>8d}/{n_nb} \"\n              f\"{b['udij_rank']:>3d}/{n_nb} | {a['udij_ratio']:14.2f} {b['udij_ratio']:5.2f} | \"\n              f\"{SHORT[a['udij_nearest_banned']]:>20s} {SHORT[b['udij_nearest_banned']]:>6s}\")\n\nprint(f\"\\nLanding verdict (15 pooled survivors) and stability, k = {K_VERDICT}\")\nfor key in KEYS:\n    r, f = geo_results[key][\"L_star\"], ref[\"geometry\"][key]\n    bd, bf = r[\"bootstrap\"][f\"k{K_VERDICT}\"], f[\"bootstrap_k15\"]\n    print(f\"  {key:21s} landing demo {r['landing'][f'k{K_VERDICT}']['pooled']['verdict']:8s} full \"\n          f\"{f['landing_pooled_verdict']['k15']:8s} | bootstrap P(EDGE) demo {bd['edge_probability'][UDIJ]:.2f} \"\n          f\"(n={bd['n_boot']}) full {bf['edge_probability'][UDIJ]:.2f} (n={bf['n_boot']}) | split-half S-B demo \"\n          f\"{r['split_half'][f'k{K_VERDICT}']['spearman_brown']:.2f} full {f['split_half_spearman_brown_k15']:.2f}\")\n\nprint(\"\\nRSA: Spearman rho of the class-geodesic RDM with each model RDM (exact Mantel p)\")\nfor key in KEYS:\n    parts = []\n    for mn in (\"R_lex\", \"R_beh\", \"R_surface\"):\n        d, f = rsa_results[key][\"models\"][mn], ref[\"rsa\"][key][mn]\n        parts.append(f\"{mn} demo {d['rho']:+.2f} (p {d['p_exact']:.3f}) full {f['rho']:+.2f} (p {f['p_exact']:.3f})\")\n    print(f\"  {key:21s} \" + \" | \".join(parts))\n\nlx_d, lx_f = lex_results[\"32b|mname\"], ref[\"lexical_regression\"][\"32b|mname\"]\nprint(f\"\\nP4, M-name alias level, Spearman(g_alias, L1): demo k10 {lx_d['k10']['spearman_L1']:+.2f}, k15 \"\n      f\"{lx_d['k15']['spearman_L1']:+.2f} (pass {lx_d['P4_pass']}) | full k10 {lx_f['k10']['spearman_L1']:+.2f}, k15 \"\n      f\"{lx_f['k15']['spearman_L1']:+.2f} (pass {lx_f['P4_pass']})\")\npl_d, pl_f = placement_results[\"32b|mcode_PRIMARY_R1\"], ref[\"placement\"][\"32b|mcode_PRIMARY_R1\"]\nprint(f\"P8, survivor programs placed at the EDGE of M-code: demo {pl_d['udij_survivors']['n_edge']}/\"\n      f\"{pl_d['udij_survivors']['n']} (LOO accuracy {pl_d['G_place']['loo_accuracy']:.2f}) | full \"\n      f\"{pl_f['udij_survivors']['n_edge']}/{pl_f['udij_survivors']['n']} (LOO accuracy {pl_f['G_place']['loo_accuracy']:.2f})\")\n\nn4 = ref[\"n4_verdict\"]\nprint(\"\\nFull run, k = 15 class of unit Dijkstra on every manifold analysed: \" + \", \".join(\n    f\"{k} {v['k15']['udij_class']}\" for k, v in n4[\"verdict_table\"].items() if v[\"k15\"][\"udij_class\"]))\nprint(f\"Full-run named outcome: {n4['named_outcome']} (M-code {n4['mcode_class_k15']}, M-desc {n4['mdesc_class_k15']}); \"\n      f\"predictions {n4['predictions_pass']}\")\nprint(f\"\\nNotebook run time so far: {time.time() - T0:.0f} s\")\n\n# ---------------------------------------------------------------------------------------------- one picture\nfig, axes = plt.subplots(1, 2, figsize=(16, 7))\nfor ax, key in zip(axes, KEYS):\n    m_tag, name = key.split(\"|\")\n    z = COORDS[f\"{m_tag}_{name}\"]\n    Y, labels = z[\"iso\"], z[\"labels\"]\n    kd = geo_results[key][\"L_star\"][\"describe\"][f\"k{K_VERDICT}\"]\n    for a in [a for a in CANON_ORDER if a in set(labels.tolist())]:\n        s = labels == a\n        ax.scatter(Y[s, 0], Y[s, 1], s=80 if a == UDIJ else 35, color=COL[a], alpha=0.9, label=SHORT[a],\n                   edgecolors=\"red\" if a in B5 else (\"black\" if a == UDIJ else \"none\"), linewidths=1.2)\n    # geodesic from unit Dijkstra to its nearest banned algorithm, traced on the kNN graph (as in figure (c))\n    nb = kd[\"nearest_banned\"][UDIJ]\n    iu, ib = np.where(labels == UDIJ)[0], np.where(labels == nb)[0]\n    i, j = np.unravel_index(np.argmin(z[\"geo\"][np.ix_(iu, ib)]), (len(iu), len(ib)))\n    _, pred = shortest_path(FROZEN[f\"geo_{m_tag}_{name}_k{K_VERDICT}\"][\"adjacency\"], method=\"D\", directed=False,\n                            indices=[iu[i]], return_predecessors=True)\n    path, cur = [], ib[j]\n    while cur >= 0 and cur != iu[i]:\n        path.append(cur)\n        cur = pred[0, cur]\n    path.append(iu[i])\n    ax.plot(Y[path, 0], Y[path, 1], \"k--\", lw=1.2, label=f\"geodesic {SHORT[UDIJ]} -> {SHORT[nb]}\")\n    if name.startswith(\"mcode\"):\n        # the 15 survivor programs, embedded out of sample by the fitted Isomap\n        sel = [e for e in data[\"examples\"] if e[\"manifold\"] == \"placement_SURV\"]\n        Q = np.stack([np.frombuffer(base64.b64decode(e[\"x_f16_b64\"]), dtype=\"<f2\") for e in sel]).astype(np.float64)\n        Yq = z[\"isomap_model\"].transform(Q)\n        ax.scatter(Yq[:, 0], Yq[:, 1], marker=\"x\", s=60, color=\"black\", label=f\"{len(sel)} survivor programs\")\n    ax.set_title(f\"{TITLES[name]}, block {z['block']}\\nunit Dijkstra is {kd['classes'][UDIJ]}: \"\n                 f\"g/median {kd['udij_ratio']:.2f}, rank {kd['udij_rank']}/{len(kd['g'])} (Isomap k={K_VERDICT})\",\n                 fontsize=10)\n    ax.set_xlabel(\"Isomap 1\")\n    ax.set_ylabel(\"Isomap 2\")\n    ax.legend(fontsize=7, ncol=2, loc=\"best\")\nfig.suptitle(\"Qwen3-32B: the algorithm written when the top five are banned (unit Dijkstra, black outline) sits \"\n             \"OPPOSITE the banned five (red outline) on the map of names,\\nbut at their EDGE on the map of programs, \"\n             \"where the actual survivor programs (x) also land\", fontsize=11)\nplt.tight_layout()\nplt.show()", "cell_type": "code", "language": "python", "edit_mode": "insert", "cell_id": "737f7307", "error": "", "notebook_path": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb", "original_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"closing-notes\",\n   \"metadata\": {},\n   \"source\": [\n    \"## Scaling back to the full run\\n\",\n    \"\\n\",\n    \"* **Parameters.** Set `N_BOOT_32B = 1000`, `N_BOOT_OTHER = 200`, `LANDING_DRAWS = 10000` and `PERM_P_N = 100000` in the config cell (the committed values); `KS`, `K_VERDICT` and `K_SECOND` are already the committed values.\\n\",\n    \"* **Data.** The full analysis uses all 300 M-name, 260 M-desc, 300 M-lex and 117 M-code states at every block 17-47 (`cache/states/`, about 0.5 GB of float16 arrays). They stay on the run's storage volume and are rebuilt with the artifact's GPU stages: `method.py mname 32b`, `method.py states 32b mlex ban`, `method.py states 32b mdesc mcode` (about 30 GPU-minutes on one RTX 5090), then `method.py blocks`, `method.py analyse`, `method.py figures`, `method.py outputs`.\\n\",\n    \"* **What changes with the data.** Layer selection (`blocks`), the reference-block section, the 5-block robustness grid, name evocation and the 8B / M-desc / M-lex manifolds need those states; every function in this notebook runs on them unchanged once `load_manifold` reads the `.npz` files again.\\n\",\n    \"\\n\",\n    \"The geometry is correlational: it describes where representations and survivors sit, not whether the model uses this geometry to choose an algorithm.\"\n   ]\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}\n", "updated_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"737f7307\",\n   \"source\": \"# ---------------------------------------------------------------------------------------------- demo vs full run\\nref = meta[\\\"full_run_reference\\\"]\\nKEYS = [\\\"32b|mname\\\", \\\"32b|mcode_PRIMARY_R1\\\"]\\nprint(\\\"Where does unit-weight Dijkstra sit relative to the banned five?\\\")\\nprint(\\\"demo = this notebook on the 99-point subset; full = the artifact's run on all points (300 M-name, 117 M-code)\\\\n\\\")\\nprint(f\\\"{'manifold':21s}{'k':>3s} | {'class: demo':>11s} {'full':>9s} | {'rank: demo':>10s} {'full':>5s} | \\\"\\n      f\\\"{'g/median: demo':>14s} {'full':>5s} | {'nearest banned: demo':>20s} {'full':>6s}\\\")\\nfor key in KEYS:\\n    sd, sf = geo_results[key][\\\"summary\\\"], ref[\\\"geometry\\\"][key][\\\"summary\\\"]\\n    n_nb = len(geo_results[key][\\\"L_star\\\"][\\\"describe\\\"][\\\"nonbanned_used\\\"])\\n    for k in KS:\\n        a, b = sd[f\\\"k{k}\\\"], sf[f\\\"k{k}\\\"]\\n        print(f\\\"{key:21s}{k:3d} | {a['udij_class']:>11s} {b['udij_class']:>9s} | {a['udij_rank']:>8d}/{n_nb} \\\"\\n              f\\\"{b['udij_rank']:>3d}/{n_nb} | {a['udij_ratio']:14.2f} {b['udij_ratio']:5.2f} | \\\"\\n              f\\\"{SHORT[a['udij_nearest_banned']]:>20s} {SHORT[b['udij_nearest_banned']]:>6s}\\\")\\n\\nprint(f\\\"\\\\nLanding verdict (15 pooled survivors) and stability, k = {K_VERDICT}\\\")\\nfor key in KEYS:\\n    r, f = geo_results[key][\\\"L_star\\\"], ref[\\\"geometry\\\"][key]\\n    bd, bf = r[\\\"bootstrap\\\"][f\\\"k{K_VERDICT}\\\"], f[\\\"bootstrap_k15\\\"]\\n    print(f\\\"  {key:21s} landing demo {r['landing'][f'k{K_VERDICT}']['pooled']['verdict']:8s} full \\\"\\n          f\\\"{f['landing_pooled_verdict']['k15']:8s} | bootstrap P(EDGE) demo {bd['edge_probability'][UDIJ]:.2f} \\\"\\n          f\\\"(n={bd['n_boot']}) full {bf['edge_probability'][UDIJ]:.2f} (n={bf['n_boot']}) | split-half S-B demo \\\"\\n          f\\\"{r['split_half'][f'k{K_VERDICT}']['spearman_brown']:.2f} full {f['split_half_spearman_brown_k15']:.2f}\\\")\\n\\nprint(\\\"\\\\nRSA: Spearman rho of the class-geodesic RDM with each model RDM (exact Mantel p)\\\")\\nfor key in KEYS:\\n    parts = []\\n    for mn in (\\\"R_lex\\\", \\\"R_beh\\\", \\\"R_surface\\\"):\\n        d, f = rsa_results[key][\\\"models\\\"][mn], ref[\\\"rsa\\\"][key][mn]\\n        parts.append(f\\\"{mn} demo {d['rho']:+.2f} (p {d['p_exact']:.3f}) full {f['rho']:+.2f} (p {f['p_exact']:.3f})\\\")\\n    print(f\\\"  {key:21s} \\\" + \\\" | \\\".join(parts))\\n\\nlx_d, lx_f = lex_results[\\\"32b|mname\\\"], ref[\\\"lexical_regression\\\"][\\\"32b|mname\\\"]\\nprint(f\\\"\\\\nP4, M-name alias level, Spearman(g_alias, L1): demo k10 {lx_d['k10']['spearman_L1']:+.2f}, k15 \\\"\\n      f\\\"{lx_d['k15']['spearman_L1']:+.2f} (pass {lx_d['P4_pass']}) | full k10 {lx_f['k10']['spearman_L1']:+.2f}, k15 \\\"\\n      f\\\"{lx_f['k15']['spearman_L1']:+.2f} (pass {lx_f['P4_pass']})\\\")\\npl_d, pl_f = placement_results[\\\"32b|mcode_PRIMARY_R1\\\"], ref[\\\"placement\\\"][\\\"32b|mcode_PRIMARY_R1\\\"]\\nprint(f\\\"P8, survivor programs placed at the EDGE of M-code: demo {pl_d['udij_survivors']['n_edge']}/\\\"\\n      f\\\"{pl_d['udij_survivors']['n']} (LOO accuracy {pl_d['G_place']['loo_accuracy']:.2f}) | full \\\"\\n      f\\\"{pl_f['udij_survivors']['n_edge']}/{pl_f['udij_survivors']['n']} (LOO accuracy {pl_f['G_place']['loo_accuracy']:.2f})\\\")\\n\\nn4 = ref[\\\"n4_verdict\\\"]\\nprint(\\\"\\\\nFull run, k = 15 class of unit Dijkstra on every manifold analysed: \\\" + \\\", \\\".join(\\n    f\\\"{k} {v['k15']['udij_class']}\\\" for k, v in n4[\\\"verdict_table\\\"].items() if v[\\\"k15\\\"][\\\"udij_class\\\"]))\\nprint(f\\\"Full-run named outcome: {n4['named_outcome']} (M-code {n4['mcode_class_k15']}, M-desc {n4['mdesc_class_k15']}); \\\"\\n      f\\\"predictions {n4['predictions_pass']}\\\")\\nprint(f\\\"\\\\nNotebook run time so far: {time.time() - T0:.0f} s\\\")\\n\\n# ---------------------------------------------------------------------------------------------- one picture\\nfig, axes = plt.subplots(1, 2, figsize=(16, 7))\\nfor ax, key in zip(axes, KEYS):\\n    m_tag, name = key.split(\\\"|\\\")\\n    z = COORDS[f\\\"{m_tag}_{name}\\\"]\\n    Y, labels = z[\\\"iso\\\"], z[\\\"labels\\\"]\\n    kd = geo_results[key][\\\"L_star\\\"][\\\"describe\\\"][f\\\"k{K_VERDICT}\\\"]\\n    for a in [a for a in CANON_ORDER if a in set(labels.tolist())]:\\n        s = labels == a\\n        ax.scatter(Y[s, 0], Y[s, 1], s=80 if a == UDIJ else 35, color=COL[a], alpha=0.9, label=SHORT[a],\\n                   edgecolors=\\\"red\\\" if a in B5 else (\\\"black\\\" if a == UDIJ else \\\"none\\\"), linewidths=1.2)\\n    # geodesic from unit Dijkstra to its nearest banned algorithm, traced on the kNN graph (as in figure (c))\\n    nb = kd[\\\"nearest_banned\\\"][UDIJ]\\n    iu, ib = np.where(labels == UDIJ)[0], np.where(labels == nb)[0]\\n    i, j = np.unravel_index(np.argmin(z[\\\"geo\\\"][np.ix_(iu, ib)]), (len(iu), len(ib)))\\n    _, pred = shortest_path(FROZEN[f\\\"geo_{m_tag}_{name}_k{K_VERDICT}\\\"][\\\"adjacency\\\"], method=\\\"D\\\", directed=False,\\n                            indices=[iu[i]], return_predecessors=True)\\n    path, cur = [], ib[j]\\n    while cur >= 0 and cur != iu[i]:\\n        path.append(cur)\\n        cur = pred[0, cur]\\n    path.append(iu[i])\\n    ax.plot(Y[path, 0], Y[path, 1], \\\"k--\\\", lw=1.2, label=f\\\"geodesic {SHORT[UDIJ]} -> {SHORT[nb]}\\\")\\n    if name.startswith(\\\"mcode\\\"):\\n        # the 15 survivor programs, embedded out of sample by the fitted Isomap\\n        sel = [e for e in data[\\\"examples\\\"] if e[\\\"manifold\\\"] == \\\"placement_SURV\\\"]\\n        Q = np.stack([np.frombuffer(base64.b64decode(e[\\\"x_f16_b64\\\"]), dtype=\\\"<f2\\\") for e in sel]).astype(np.float64)\\n        Yq = z[\\\"isomap_model\\\"].transform(Q)\\n        ax.scatter(Yq[:, 0], Yq[:, 1], marker=\\\"x\\\", s=60, color=\\\"black\\\", label=f\\\"{len(sel)} survivor programs\\\")\\n    ax.set_title(f\\\"{TITLES[name]}, block {z['block']}\\\\nunit Dijkstra is {kd['classes'][UDIJ]}: \\\"\\n                 f\\\"g/median {kd['udij_ratio']:.2f}, rank {kd['udij_rank']}/{len(kd['g'])} (Isomap k={K_VERDICT})\\\",\\n                 fontsize=10)\\n    ax.set_xlabel(\\\"Isomap 1\\\")\\n    ax.set_ylabel(\\\"Isomap 2\\\")\\n    ax.legend(fontsize=7, ncol=2, loc=\\\"best\\\")\\nfig.suptitle(\\\"Qwen3-32B: the algorithm written when the top five are banned (unit Dijkstra, black outline) sits \\\"\\n             \\\"OPPOSITE the banned five (red outline) on the map of names,\\\\nbut at their EDGE on the map of programs, \\\"\\n             \\\"where the actual survivor programs (x) also land\\\", fontsize=11)\\nplt.tight_layout()\\nplt.show()\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"closing-notes\",\n   \"metadata\": {},\n   \"source\": [\n    \"## Scaling back to the full run\\n\",\n    \"\\n\",\n    \"* **Parameters.** Set `N_BOOT_32B = 1000`, `N_BOOT_OTHER = 200`, `LANDING_DRAWS = 10000` and `PERM_P_N = 100000` in the config cell (the committed values); `KS`, `K_VERDICT` and `K_SECOND` are already the committed values.\\n\",\n    \"* **Data.** The full analysis uses all 300 M-name, 260 M-desc, 300 M-lex and 117 M-code states at every block 17-47 (`cache/states/`, about 0.5 GB of float16 arrays). They stay on the run's storage volume and are rebuilt with the artifact's GPU stages: `method.py mname 32b`, `method.py states 32b mlex ban`, `method.py states 32b mdesc mcode` (about 30 GPU-minutes on one RTX 5090), then `method.py blocks`, `method.py analyse`, `method.py figures`, `method.py outputs`.\\n\",\n    \"* **What changes with the data.** Layer selection (`blocks`), the reference-block section, the 5-block robustness grid, name evocation and the 8B / M-desc / M-lex manifolds need those states; every function in this notebook runs on them unchanged once `load_manifold` reads the `.npz` files again.\\n\",\n    \"\\n\",\n    \"The geometry is correlational: it describes where representations and survivors sit, not whether the model uses this geometry to choose an algorithm.\"\n   ]\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}"}
```

### [90] TOOL CALL — NotebookEdit · 2026-10-26 14:38:41 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "## Results: the demo subset against the full run\n\nThe table puts every headline number computed above next to the artifact's full-run value (all 300 M-name prompts, all 117 M-code programs, 1,000 bootstrap resamples), read from `metadata.full_run_reference` of the demo data. The figure shows both manifolds side by side in Isomap coordinates: the same model, the same algorithm (unit Dijkstra, black outline) and the same banned five (red outline). On the map of **names** unit Dijkstra sits OPPOSITE the banned five; on the map of **programs** it sits at their EDGE, and the 15 programs Qwen3-32B actually wrote under the ban (crosses, embedded out of sample) land there too.\n\nOn the 99-point subset, the M-name class and the RSA ordering (R_lex above R_beh) depend on the k-graph and on the few points per algorithm. Read them with the bootstrap stability and the full-run column beside them."}
```

### [91] TOOL RESULT — NotebookEdit · 2026-10-26 14:38:41 UTC

```
{"new_source": "## Results: the demo subset against the full run\n\nThe table puts every headline number computed above next to the artifact's full-run value (all 300 M-name prompts, all 117 M-code programs, 1,000 bootstrap resamples), read from `metadata.full_run_reference` of the demo data. The figure shows both manifolds side by side in Isomap coordinates: the same model, the same algorithm (unit Dijkstra, black outline) and the same banned five (red outline). On the map of **names** unit Dijkstra sits OPPOSITE the banned five; on the map of **programs** it sits at their EDGE, and the 15 programs Qwen3-32B actually wrote under the ban (crosses, embedded out of sample) land there too.\n\nOn the 99-point subset, the M-name class and the RSA ordering (R_lex above R_beh) depend on the k-graph and on the few points per algorithm. Read them with the bootstrap stability and the full-run column beside them.", "cell_type": "markdown", "language": "python", "edit_mode": "insert", "cell_id": "9c6957aa", "error": "", "notebook_path": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb", "original_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"737f7307\",\n   \"source\": \"# ---------------------------------------------------------------------------------------------- demo vs full run\\nref = meta[\\\"full_run_reference\\\"]\\nKEYS = [\\\"32b|mname\\\", \\\"32b|mcode_PRIMARY_R1\\\"]\\nprint(\\\"Where does unit-weight Dijkstra sit relative to the banned five?\\\")\\nprint(\\\"demo = this notebook on the 99-point subset; full = the artifact's run on all points (300 M-name, 117 M-code)\\\\n\\\")\\nprint(f\\\"{'manifold':21s}{'k':>3s} | {'class: demo':>11s} {'full':>9s} | {'rank: demo':>10s} {'full':>5s} | \\\"\\n      f\\\"{'g/median: demo':>14s} {'full':>5s} | {'nearest banned: demo':>20s} {'full':>6s}\\\")\\nfor key in KEYS:\\n    sd, sf = geo_results[key][\\\"summary\\\"], ref[\\\"geometry\\\"][key][\\\"summary\\\"]\\n    n_nb = len(geo_results[key][\\\"L_star\\\"][\\\"describe\\\"][\\\"nonbanned_used\\\"])\\n    for k in KS:\\n        a, b = sd[f\\\"k{k}\\\"], sf[f\\\"k{k}\\\"]\\n        print(f\\\"{key:21s}{k:3d} | {a['udij_class']:>11s} {b['udij_class']:>9s} | {a['udij_rank']:>8d}/{n_nb} \\\"\\n              f\\\"{b['udij_rank']:>3d}/{n_nb} | {a['udij_ratio']:14.2f} {b['udij_ratio']:5.2f} | \\\"\\n              f\\\"{SHORT[a['udij_nearest_banned']]:>20s} {SHORT[b['udij_nearest_banned']]:>6s}\\\")\\n\\nprint(f\\\"\\\\nLanding verdict (15 pooled survivors) and stability, k = {K_VERDICT}\\\")\\nfor key in KEYS:\\n    r, f = geo_results[key][\\\"L_star\\\"], ref[\\\"geometry\\\"][key]\\n    bd, bf = r[\\\"bootstrap\\\"][f\\\"k{K_VERDICT}\\\"], f[\\\"bootstrap_k15\\\"]\\n    print(f\\\"  {key:21s} landing demo {r['landing'][f'k{K_VERDICT}']['pooled']['verdict']:8s} full \\\"\\n          f\\\"{f['landing_pooled_verdict']['k15']:8s} | bootstrap P(EDGE) demo {bd['edge_probability'][UDIJ]:.2f} \\\"\\n          f\\\"(n={bd['n_boot']}) full {bf['edge_probability'][UDIJ]:.2f} (n={bf['n_boot']}) | split-half S-B demo \\\"\\n          f\\\"{r['split_half'][f'k{K_VERDICT}']['spearman_brown']:.2f} full {f['split_half_spearman_brown_k15']:.2f}\\\")\\n\\nprint(\\\"\\\\nRSA: Spearman rho of the class-geodesic RDM with each model RDM (exact Mantel p)\\\")\\nfor key in KEYS:\\n    parts = []\\n    for mn in (\\\"R_lex\\\", \\\"R_beh\\\", \\\"R_surface\\\"):\\n        d, f = rsa_results[key][\\\"models\\\"][mn], ref[\\\"rsa\\\"][key][mn]\\n        parts.append(f\\\"{mn} demo {d['rho']:+.2f} (p {d['p_exact']:.3f}) full {f['rho']:+.2f} (p {f['p_exact']:.3f})\\\")\\n    print(f\\\"  {key:21s} \\\" + \\\" | \\\".join(parts))\\n\\nlx_d, lx_f = lex_results[\\\"32b|mname\\\"], ref[\\\"lexical_regression\\\"][\\\"32b|mname\\\"]\\nprint(f\\\"\\\\nP4, M-name alias level, Spearman(g_alias, L1): demo k10 {lx_d['k10']['spearman_L1']:+.2f}, k15 \\\"\\n      f\\\"{lx_d['k15']['spearman_L1']:+.2f} (pass {lx_d['P4_pass']}) | full k10 {lx_f['k10']['spearman_L1']:+.2f}, k15 \\\"\\n      f\\\"{lx_f['k15']['spearman_L1']:+.2f} (pass {lx_f['P4_pass']})\\\")\\npl_d, pl_f = placement_results[\\\"32b|mcode_PRIMARY_R1\\\"], ref[\\\"placement\\\"][\\\"32b|mcode_PRIMARY_R1\\\"]\\nprint(f\\\"P8, survivor programs placed at the EDGE of M-code: demo {pl_d['udij_survivors']['n_edge']}/\\\"\\n      f\\\"{pl_d['udij_survivors']['n']} (LOO accuracy {pl_d['G_place']['loo_accuracy']:.2f}) | full \\\"\\n      f\\\"{pl_f['udij_survivors']['n_edge']}/{pl_f['udij_survivors']['n']} (LOO accuracy {pl_f['G_place']['loo_accuracy']:.2f})\\\")\\n\\nn4 = ref[\\\"n4_verdict\\\"]\\nprint(\\\"\\\\nFull run, k = 15 class of unit Dijkstra on every manifold analysed: \\\" + \\\", \\\".join(\\n    f\\\"{k} {v['k15']['udij_class']}\\\" for k, v in n4[\\\"verdict_table\\\"].items() if v[\\\"k15\\\"][\\\"udij_class\\\"]))\\nprint(f\\\"Full-run named outcome: {n4['named_outcome']} (M-code {n4['mcode_class_k15']}, M-desc {n4['mdesc_class_k15']}); \\\"\\n      f\\\"predictions {n4['predictions_pass']}\\\")\\nprint(f\\\"\\\\nNotebook run time so far: {time.time() - T0:.0f} s\\\")\\n\\n# ---------------------------------------------------------------------------------------------- one picture\\nfig, axes = plt.subplots(1, 2, figsize=(16, 7))\\nfor ax, key in zip(axes, KEYS):\\n    m_tag, name = key.split(\\\"|\\\")\\n    z = COORDS[f\\\"{m_tag}_{name}\\\"]\\n    Y, labels = z[\\\"iso\\\"], z[\\\"labels\\\"]\\n    kd = geo_results[key][\\\"L_star\\\"][\\\"describe\\\"][f\\\"k{K_VERDICT}\\\"]\\n    for a in [a for a in CANON_ORDER if a in set(labels.tolist())]:\\n        s = labels == a\\n        ax.scatter(Y[s, 0], Y[s, 1], s=80 if a == UDIJ else 35, color=COL[a], alpha=0.9, label=SHORT[a],\\n                   edgecolors=\\\"red\\\" if a in B5 else (\\\"black\\\" if a == UDIJ else \\\"none\\\"), linewidths=1.2)\\n    # geodesic from unit Dijkstra to its nearest banned algorithm, traced on the kNN graph (as in figure (c))\\n    nb = kd[\\\"nearest_banned\\\"][UDIJ]\\n    iu, ib = np.where(labels == UDIJ)[0], np.where(labels == nb)[0]\\n    i, j = np.unravel_index(np.argmin(z[\\\"geo\\\"][np.ix_(iu, ib)]), (len(iu), len(ib)))\\n    _, pred = shortest_path(FROZEN[f\\\"geo_{m_tag}_{name}_k{K_VERDICT}\\\"][\\\"adjacency\\\"], method=\\\"D\\\", directed=False,\\n                            indices=[iu[i]], return_predecessors=True)\\n    path, cur = [], ib[j]\\n    while cur >= 0 and cur != iu[i]:\\n        path.append(cur)\\n        cur = pred[0, cur]\\n    path.append(iu[i])\\n    ax.plot(Y[path, 0], Y[path, 1], \\\"k--\\\", lw=1.2, label=f\\\"geodesic {SHORT[UDIJ]} -> {SHORT[nb]}\\\")\\n    if name.startswith(\\\"mcode\\\"):\\n        # the 15 survivor programs, embedded out of sample by the fitted Isomap\\n        sel = [e for e in data[\\\"examples\\\"] if e[\\\"manifold\\\"] == \\\"placement_SURV\\\"]\\n        Q = np.stack([np.frombuffer(base64.b64decode(e[\\\"x_f16_b64\\\"]), dtype=\\\"<f2\\\") for e in sel]).astype(np.float64)\\n        Yq = z[\\\"isomap_model\\\"].transform(Q)\\n        ax.scatter(Yq[:, 0], Yq[:, 1], marker=\\\"x\\\", s=60, color=\\\"black\\\", label=f\\\"{len(sel)} survivor programs\\\")\\n    ax.set_title(f\\\"{TITLES[name]}, block {z['block']}\\\\nunit Dijkstra is {kd['classes'][UDIJ]}: \\\"\\n                 f\\\"g/median {kd['udij_ratio']:.2f}, rank {kd['udij_rank']}/{len(kd['g'])} (Isomap k={K_VERDICT})\\\",\\n                 fontsize=10)\\n    ax.set_xlabel(\\\"Isomap 1\\\")\\n    ax.set_ylabel(\\\"Isomap 2\\\")\\n    ax.legend(fontsize=7, ncol=2, loc=\\\"best\\\")\\nfig.suptitle(\\\"Qwen3-32B: the algorithm written when the top five are banned (unit Dijkstra, black outline) sits \\\"\\n             \\\"OPPOSITE the banned five (red outline) on the map of names,\\\\nbut at their EDGE on the map of programs, \\\"\\n             \\\"where the actual survivor programs (x) also land\\\", fontsize=11)\\nplt.tight_layout()\\nplt.show()\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"closing-notes\",\n   \"metadata\": {},\n   \"source\": [\n    \"## Scaling back to the full run\\n\",\n    \"\\n\",\n    \"* **Parameters.** Set `N_BOOT_32B = 1000`, `N_BOOT_OTHER = 200`, `LANDING_DRAWS = 10000` and `PERM_P_N = 100000` in the config cell (the committed values); `KS`, `K_VERDICT` and `K_SECOND` are already the committed values.\\n\",\n    \"* **Data.** The full analysis uses all 300 M-name, 260 M-desc, 300 M-lex and 117 M-code states at every block 17-47 (`cache/states/`, about 0.5 GB of float16 arrays). They stay on the run's storage volume and are rebuilt with the artifact's GPU stages: `method.py mname 32b`, `method.py states 32b mlex ban`, `method.py states 32b mdesc mcode` (about 30 GPU-minutes on one RTX 5090), then `method.py blocks`, `method.py analyse`, `method.py figures`, `method.py outputs`.\\n\",\n    \"* **What changes with the data.** Layer selection (`blocks`), the reference-block section, the 5-block robustness grid, name evocation and the 8B / M-desc / M-lex manifolds need those states; every function in this notebook runs on them unchanged once `load_manifold` reads the `.npz` files again.\\n\",\n    \"\\n\",\n    \"The geometry is correlational: it describes where representations and survivors sit, not whether the model uses this geometry to choose an algorithm.\"\n   ]\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}", "updated_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"9c6957aa\",\n   \"source\": \"## Results: the demo subset against the full run\\n\\nThe table puts every headline number computed above next to the artifact's full-run value (all 300 M-name prompts, all 117 M-code programs, 1,000 bootstrap resamples), read from `metadata.full_run_reference` of the demo data. The figure shows both manifolds side by side in Isomap coordinates: the same model, the same algorithm (unit Dijkstra, black outline) and the same banned five (red outline). On the map of **names** unit Dijkstra sits OPPOSITE the banned five; on the map of **programs** it sits at their EDGE, and the 15 programs Qwen3-32B actually wrote under the ban (crosses, embedded out of sample) land there too.\\n\\nOn the 99-point subset, the M-name class and the RSA ordering (R_lex above R_beh) depend on the k-graph and on the few points per algorithm. Read them with the bootstrap stability and the full-run column beside them.\",\n   \"metadata\": {}\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"737f7307\",\n   \"source\": \"# ---------------------------------------------------------------------------------------------- demo vs full run\\nref = meta[\\\"full_run_reference\\\"]\\nKEYS = [\\\"32b|mname\\\", \\\"32b|mcode_PRIMARY_R1\\\"]\\nprint(\\\"Where does unit-weight Dijkstra sit relative to the banned five?\\\")\\nprint(\\\"demo = this notebook on the 99-point subset; full = the artifact's run on all points (300 M-name, 117 M-code)\\\\n\\\")\\nprint(f\\\"{'manifold':21s}{'k':>3s} | {'class: demo':>11s} {'full':>9s} | {'rank: demo':>10s} {'full':>5s} | \\\"\\n      f\\\"{'g/median: demo':>14s} {'full':>5s} | {'nearest banned: demo':>20s} {'full':>6s}\\\")\\nfor key in KEYS:\\n    sd, sf = geo_results[key][\\\"summary\\\"], ref[\\\"geometry\\\"][key][\\\"summary\\\"]\\n    n_nb = len(geo_results[key][\\\"L_star\\\"][\\\"describe\\\"][\\\"nonbanned_used\\\"])\\n    for k in KS:\\n        a, b = sd[f\\\"k{k}\\\"], sf[f\\\"k{k}\\\"]\\n        print(f\\\"{key:21s}{k:3d} | {a['udij_class']:>11s} {b['udij_class']:>9s} | {a['udij_rank']:>8d}/{n_nb} \\\"\\n              f\\\"{b['udij_rank']:>3d}/{n_nb} | {a['udij_ratio']:14.2f} {b['udij_ratio']:5.2f} | \\\"\\n              f\\\"{SHORT[a['udij_nearest_banned']]:>20s} {SHORT[b['udij_nearest_banned']]:>6s}\\\")\\n\\nprint(f\\\"\\\\nLanding verdict (15 pooled survivors) and stability, k = {K_VERDICT}\\\")\\nfor key in KEYS:\\n    r, f = geo_results[key][\\\"L_star\\\"], ref[\\\"geometry\\\"][key]\\n    bd, bf = r[\\\"bootstrap\\\"][f\\\"k{K_VERDICT}\\\"], f[\\\"bootstrap_k15\\\"]\\n    print(f\\\"  {key:21s} landing demo {r['landing'][f'k{K_VERDICT}']['pooled']['verdict']:8s} full \\\"\\n          f\\\"{f['landing_pooled_verdict']['k15']:8s} | bootstrap P(EDGE) demo {bd['edge_probability'][UDIJ]:.2f} \\\"\\n          f\\\"(n={bd['n_boot']}) full {bf['edge_probability'][UDIJ]:.2f} (n={bf['n_boot']}) | split-half S-B demo \\\"\\n          f\\\"{r['split_half'][f'k{K_VERDICT}']['spearman_brown']:.2f} full {f['split_half_spearman_brown_k15']:.2f}\\\")\\n\\nprint(\\\"\\\\nRSA: Spearman rho of the class-geodesic RDM with each model RDM (exact Mantel p)\\\")\\nfor key in KEYS:\\n    parts = []\\n    for mn in (\\\"R_lex\\\", \\\"R_beh\\\", \\\"R_surface\\\"):\\n        d, f = rsa_results[key][\\\"models\\\"][mn], ref[\\\"rsa\\\"][key][mn]\\n        parts.append(f\\\"{mn} demo {d['rho']:+.2f} (p {d['p_exact']:.3f}) full {f['rho']:+.2f} (p {f['p_exact']:.3f})\\\")\\n    print(f\\\"  {key:21s} \\\" + \\\" | \\\".join(parts))\\n\\nlx_d, lx_f = lex_results[\\\"32b|mname\\\"], ref[\\\"lexical_regression\\\"][\\\"32b|mname\\\"]\\nprint(f\\\"\\\\nP4, M-name alias level, Spearman(g_alias, L1): demo k10 {lx_d['k10']['spearman_L1']:+.2f}, k15 \\\"\\n      f\\\"{lx_d['k15']['spearman_L1']:+.2f} (pass {lx_d['P4_pass']}) | full k10 {lx_f['k10']['spearman_L1']:+.2f}, k15 \\\"\\n      f\\\"{lx_f['k15']['spearman_L1']:+.2f} (pass {lx_f['P4_pass']})\\\")\\npl_d, pl_f = placement_results[\\\"32b|mcode_PRIMARY_R1\\\"], ref[\\\"placement\\\"][\\\"32b|mcode_PRIMARY_R1\\\"]\\nprint(f\\\"P8, survivor programs placed at the EDGE of M-code: demo {pl_d['udij_survivors']['n_edge']}/\\\"\\n      f\\\"{pl_d['udij_survivors']['n']} (LOO accuracy {pl_d['G_place']['loo_accuracy']:.2f}) | full \\\"\\n      f\\\"{pl_f['udij_survivors']['n_edge']}/{pl_f['udij_survivors']['n']} (LOO accuracy {pl_f['G_place']['loo_accuracy']:.2f})\\\")\\n\\nn4 = ref[\\\"n4_verdict\\\"]\\nprint(\\\"\\\\nFull run, k = 15 class of unit Dijkstra on every manifold analysed: \\\" + \\\", \\\".join(\\n    f\\\"{k} {v['k15']['udij_class']}\\\" for k, v in n4[\\\"verdict_table\\\"].items() if v[\\\"k15\\\"][\\\"udij_class\\\"]))\\nprint(f\\\"Full-run named outcome: {n4['named_outcome']} (M-code {n4['mcode_class_k15']}, M-desc {n4['mdesc_class_k15']}); \\\"\\n      f\\\"predictions {n4['predictions_pass']}\\\")\\nprint(f\\\"\\\\nNotebook run time so far: {time.time() - T0:.0f} s\\\")\\n\\n# ---------------------------------------------------------------------------------------------- one picture\\nfig, axes = plt.subplots(1, 2, figsize=(16, 7))\\nfor ax, key in zip(axes, KEYS):\\n    m_tag, name = key.split(\\\"|\\\")\\n    z = COORDS[f\\\"{m_tag}_{name}\\\"]\\n    Y, labels = z[\\\"iso\\\"], z[\\\"labels\\\"]\\n    kd = geo_results[key][\\\"L_star\\\"][\\\"describe\\\"][f\\\"k{K_VERDICT}\\\"]\\n    for a in [a for a in CANON_ORDER if a in set(labels.tolist())]:\\n        s = labels == a\\n        ax.scatter(Y[s, 0], Y[s, 1], s=80 if a == UDIJ else 35, color=COL[a], alpha=0.9, label=SHORT[a],\\n                   edgecolors=\\\"red\\\" if a in B5 else (\\\"black\\\" if a == UDIJ else \\\"none\\\"), linewidths=1.2)\\n    # geodesic from unit Dijkstra to its nearest banned algorithm, traced on the kNN graph (as in figure (c))\\n    nb = kd[\\\"nearest_banned\\\"][UDIJ]\\n    iu, ib = np.where(labels == UDIJ)[0], np.where(labels == nb)[0]\\n    i, j = np.unravel_index(np.argmin(z[\\\"geo\\\"][np.ix_(iu, ib)]), (len(iu), len(ib)))\\n    _, pred = shortest_path(FROZEN[f\\\"geo_{m_tag}_{name}_k{K_VERDICT}\\\"][\\\"adjacency\\\"], method=\\\"D\\\", directed=False,\\n                            indices=[iu[i]], return_predecessors=True)\\n    path, cur = [], ib[j]\\n    while cur >= 0 and cur != iu[i]:\\n        path.append(cur)\\n        cur = pred[0, cur]\\n    path.append(iu[i])\\n    ax.plot(Y[path, 0], Y[path, 1], \\\"k--\\\", lw=1.2, label=f\\\"geodesic {SHORT[UDIJ]} -> {SHORT[nb]}\\\")\\n    if name.startswith(\\\"mcode\\\"):\\n        # the 15 survivor programs, embedded out of sample by the fitted Isomap\\n        sel = [e for e in data[\\\"examples\\\"] if e[\\\"manifold\\\"] == \\\"placement_SURV\\\"]\\n        Q = np.stack([np.frombuffer(base64.b64decode(e[\\\"x_f16_b64\\\"]), dtype=\\\"<f2\\\") for e in sel]).astype(np.float64)\\n        Yq = z[\\\"isomap_model\\\"].transform(Q)\\n        ax.scatter(Yq[:, 0], Yq[:, 1], marker=\\\"x\\\", s=60, color=\\\"black\\\", label=f\\\"{len(sel)} survivor programs\\\")\\n    ax.set_title(f\\\"{TITLES[name]}, block {z['block']}\\\\nunit Dijkstra is {kd['classes'][UDIJ]}: \\\"\\n                 f\\\"g/median {kd['udij_ratio']:.2f}, rank {kd['udij_rank']}/{len(kd['g'])} (Isomap k={K_VERDICT})\\\",\\n                 fontsize=10)\\n    ax.set_xlabel(\\\"Isomap 1\\\")\\n    ax.set_ylabel(\\\"Isomap 2\\\")\\n    ax.legend(fontsize=7, ncol=2, loc=\\\"best\\\")\\nfig.suptitle(\\\"Qwen3-32B: the algorithm written when the top five are banned (unit Dijkstra, black outline) sits \\\"\\n             \\\"OPPOSITE the banned five (red outline) on the map of names,\\\\nbut at their EDGE on the map of programs, \\\"\\n             \\\"where the actual survivor programs (x) also land\\\", fontsize=11)\\nplt.tight_layout()\\nplt.show()\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"closing-notes\",\n   \"metadata\": {},\n   \"source\": [\n    \"## Scaling back to the full run\\n\",\n    \"\\n\",\n    \"* **Parameters.** Set `N_BOOT_32B = 1000`, `N_BOOT_OTHER = 200`, `LANDING_DRAWS = 10000` and `PERM_P_N = 100000` in the config cell (the committed values); `KS`, `K_VERDICT` and `K_SECOND` are already the committed values.\\n\",\n    \"* **Data.** The full analysis uses all 300 M-name, 260 M-desc, 300 M-lex and 117 M-code states at every block 17-47 (`cache/states/`, about 0.5 GB of float16 arrays). They stay on the run's storage volume and are rebuilt with the artifact's GPU stages: `method.py mname 32b`, `method.py states 32b mlex ban`, `method.py states 32b mdesc mcode` (about 30 GPU-minutes on one RTX 5090), then `method.py blocks`, `method.py analyse`, `method.py figures`, `method.py outputs`.\\n\",\n    \"* **What changes with the data.** Layer selection (`blocks`), the reference-block section, the 5-block robustness grid, name evocation and the 8B / M-desc / M-lex manifolds need those states; every function in this notebook runs on them unchanged once `load_manifold` reads the `.npz` files again.\\n\",\n    \"\\n\",\n    \"The geometry is correlational: it describes where representations and survivors sit, not whether the model uses this geometry to choose an algorithm.\"\n   ]\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}"}
```

### [92] ASSISTANT · 2026-10-26 14:40:25 UTC

```
Both cells went in, in order. Next come the figure cells copied from `stage_figures.py` (inserted in reverse).
```

### [93] TOOL CALL — NotebookEdit · 2026-10-26 14:40:25 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'def class_table(geo_all: dict[str, Any]) -> None:\n    rows, cells, txt = [], [], []\n    cmap = {"EDGE": 0, "MIDDLE": 1, "OPPOSITE": 2}\n    for key, r in geo_all.items():\n        if r is None:\n            continue\n        kd = r["L_star"]["describe"][f"k{K_VERDICT}"]\n        rows.append(f"{key} (L{r[\'L_star\'][\'block\']})")\n        cells.append([cmap.get(kd["classes"].get(a), np.nan) for a in NB5])\n        txt.append([(f"{kd[\'classes\'][a][:3]}\\n{kd[\'g\'][a] / kd[\'median\']:.2f}" if a in kd["classes"] else "not run")\n                    for a in NB5])\n    if not rows:\n        return\n    fig, ax = plt.subplots(figsize=(9, 0.55 * len(rows) + 1.5))\n    ax.imshow(np.array(cells, dtype=float), cmap="coolwarm", vmin=0, vmax=2, aspect="auto")\n    for i in range(len(rows)):\n        for j in range(5):\n            ax.text(j, i, txt[i][j], ha="center", va="center", fontsize=7,\n                    fontweight="bold" if NB5[j] == UDIJ else "normal")\n    ax.set_xticks(range(5), [SHORT[a] for a in NB5])\n    ax.set_yticks(range(len(rows)), rows, fontsize=7)\n    ax.set_title(f"EDGE / MIDDLE / OPPOSITE of the non-banned algorithms (k={K_VERDICT}, cell = class, g/median)",\n                 fontsize=9)\n    _save(fig, "class_table")\n\n\ndef rdm_figs() -> None:\n    rs = rsa_results                       # notebook: in memory (original: results/rsa.json)\n    md = meta["model_rdms"]                # notebook: demo data (original: results/behavioural_distance.json, ...)\n    mats = {"R_beh (behavioural)": np.array(md["R_beh"], dtype=float),\n            "R_lex (alias 3-grams)": np.array(md["R_lex"], dtype=float)}\n    mats["R_surface (AST 4-grams)"] = np.array(md["R_surface"], dtype=float)\n    geo_all = geo_results                  # notebook: in memory (original: results/geometry_all.json)\n    for key in ("32b|mname", "32b|mdesc", "32b|mlex", "32b|mcode_PRIMARY_R1"):\n        if key in geo_all:\n            M = np.array(geo_all[key]["L_star"]["describe"][f"k{K_VERDICT}"]["class_geodesic_matrix"])\n            M = (M + M.T) / 2\n            np.fill_diagonal(M, 0)\n            r = rs.get(key, {}).get("models", {})\n            lab = f"{key} neural; rho beh {r.get(\'R_beh\', {}).get(\'rho\', float(\'nan\')):.2f}, lex " \\\n                  f"{r.get(\'R_lex\', {}).get(\'rho\', float(\'nan\')):.2f}"\n            mats[lab] = M\n    n = len(mats)\n    fig, axes = plt.subplots(2, (n + 1) // 2, figsize=(4.2 * ((n + 1) // 2), 8.5))\n    for ax, (t, M) in zip(axes.ravel(), mats.items()):\n        ax.imshow(np.nan_to_num(M), cmap="magma")\n        ax.set_xticks(range(10), [SHORT[a] for a in CANON_ORDER], rotation=90, fontsize=7)\n        ax.set_yticks(range(10), [SHORT[a] for a in CANON_ORDER], fontsize=7)\n        ax.set_title(t, fontsize=7)\n    for ax in axes.ravel()[n:]:\n        ax.axis("off")\n    _save(fig, "rdms")\n    Y = meta["behavioural_mds"]["coordinates"]\n    fig, ax = plt.subplots(figsize=(6, 5))\n    for a in CANON_ORDER:\n        ax.scatter([Y[a][0]], [Y[a][1]], s=120, color=COL[a], edgecolors="red" if a in B5 else "black",\n                   linewidths=2.5 if a in B5 else 1)\n        ax.annotate(SHORT[a], Y[a], xytext=(5, 5), textcoords="offset points")\n    ax.set_title(f"Behavioural coordinates, not activations: classical MDS of d_beh\\n(expansion-order traces of the "\n                 f"15 T1 references on 40 probe grids; stress-1 {meta[\'behavioural_mds\'][\'stress1\']:.2f})", fontsize=9)\n    ax.set_xlabel("behavioural MDS 1")\n    ax.set_ylabel("behavioural MDS 2")\n    _save(fig, "behavioural_mds")\n\n\ndef lexical_fig() -> None:\n    lr = lex_results                       # notebook: in memory (original: results/lexical_regression.json)\n    r = lr.get("32b|mname")\n    if not r:\n        return\n    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))\n    for ax, k in zip(axes, ("k10", "k15")):\n        rows = r[k]["rows"]\n        for row in rows:\n            ax.scatter(row["L1"] + np.random.default_rng(len(row["alias"] if "alias" in row else "") + row[\n                "alias_index"]).uniform(-0.08, 0.08), row["g_alias"], color=COL[row["algorithm"]], s=50)\n        for a in NB5:\n            ax.scatter([], [], color=COL[a], label=SHORT[a])\n        ax.set_xlabel("L1 = banned algorithms whose alias regex matches the alias")\n        ax.set_ylabel("g_alias (min mean geodesic to a banned algorithm)")\n        ax.set_title(f"M-name alias level, {k}: Spearman {r[k][\'spearman_L1\']:.2f} (perm p {r[k][\'perm_p_L1\']:.4f})",\n                     fontsize=9)\n        ax.legend(fontsize=7)\n    _save(fig, "lexical_alias_level_32b")\n\n\nclass_table(geo_results)\nrdm_figs()\nlexical_fig()'}
```

### [94] TOOL RESULT — NotebookEdit · 2026-10-26 14:40:25 UTC

```
{"new_source": "def class_table(geo_all: dict[str, Any]) -> None:\n    rows, cells, txt = [], [], []\n    cmap = {\"EDGE\": 0, \"MIDDLE\": 1, \"OPPOSITE\": 2}\n    for key, r in geo_all.items():\n        if r is None:\n            continue\n        kd = r[\"L_star\"][\"describe\"][f\"k{K_VERDICT}\"]\n        rows.append(f\"{key} (L{r['L_star']['block']})\")\n        cells.append([cmap.get(kd[\"classes\"].get(a), np.nan) for a in NB5])\n        txt.append([(f\"{kd['clas... [truncated, 29624 chars total]
```

### [95] TOOL CALL — NotebookEdit · 2026-10-26 14:40:25 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "### Class table, RDM heatmaps, behavioural map and the alias-level lexical plot\n\n`class_table`, `rdm_figs` and `lexical_fig` from `src/stage_figures.py`, reading the in-memory results:\n\n* **Class table**: for each manifold, every non-banned algorithm's class and g / median at k = 15 (bold: unit Dijkstra).\n* **RDMs**: the three model RDMs (behaviour, alias lexicon, program surface) next to the neural class-geodesic RDMs. M-code has only 6 classes, because the other algorithms have fewer than 10 verified programs; their rows are blank.\n* **Behavioural MDS**: drawn in behavioural coordinates, not activations. By construction, unit Dijkstra expands cells in BFS order on a unit grid.\n* **Lexical plot**: each alias of a non-banned algorithm, its L1 (how many banned names it contains) against its g_alias."}
```

### [96] TOOL RESULT — NotebookEdit · 2026-10-26 14:40:25 UTC

```
{"new_source": "### Class table, RDM heatmaps, behavioural map and the alias-level lexical plot\n\n`class_table`, `rdm_figs` and `lexical_fig` from `src/stage_figures.py`, reading the in-memory results:\n\n* **Class table**: for each manifold, every non-banned algorithm's class and g / median at k = 15 (bold: unit Dijkstra).\n* **RDMs**: the three model RDMs (behaviour, alias lexicon, program surface) next to the neural class-geodesic RDMs. M-code has only 6 classes, b... [truncated, 31895 chars total]
```

### [97] TOOL CALL — NotebookEdit · 2026-10-26 14:40:25 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'for key, r in geo_results.items():\n    m_tag, name = key.split("|")\n    manifold_figs(m_tag, name, r)'}
```

### [98] TOOL RESULT — NotebookEdit · 2026-10-26 14:40:25 UTC

```
{"new_source": "for key, r in geo_results.items():\n    m_tag, name = key.split(\"|\")\n    manifold_figs(m_tag, name, r)", "cell_type": "code", "language": "python", "edit_mode": "insert", "cell_id": "b4cb6f78", "error": "", "notebook_path": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb", "original_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"dee... [truncated, 32388 chars total]
```

### [99] TOOL CALL — NotebookEdit · 2026-10-26 14:40:25 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': '### Per-manifold figures: M-name, then M-code\n\nFor each manifold: (a) PCA, coloured by implemented counts without and with the ban; (b) classical MDS of the points and of the class centroids; (c) Isomap with the geodesic from unit Dijkstra to its nearest banned algorithm. With only 3 prompts per algorithm in the M-name subset, its points are sparse (the full run has 30 per algorithm).'}
```

### [100] TOOL RESULT — NotebookEdit · 2026-10-26 14:40:25 UTC

```
{"new_source": "### Per-manifold figures: M-name, then M-code\n\nFor each manifold: (a) PCA, coloured by implemented counts without and with the ban; (b) classical MDS of the points and of the class centroids; (c) Isomap with the geodesic from unit Dijkstra to its nearest banned algorithm. With only 3 prompts per algorithm in the M-name subset, its points are sparse (the full run has 30 per algorithm).", "cell_type": "markdown", "language": "python", "edit_mode": "inse... [truncated, 33452 chars total]
```

### [101] TOOL CALL — NotebookEdit · 2026-10-26 14:40:25 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'COL = dict(zip(CANON_ORDER, plt.cm.tab10(np.linspace(0, 1, 10))))\nTITLES = {"mname": "M-name (alias prompts, S-mean)", "mdesc": "M-desc (name-free descriptions, S-mean)",\n          "mlex": "M-lex (alias minus neutral twin, S-mean delta)",\n          "mcode_PRIMARY_R1": "M-code PRIMARY (mean over code tokens, R1)",\n          "mcode_PRIMARY_R2": "M-code PRIMARY (pop-position token, R2)",\n          "mcode_M32_R1": "M-code Qwen3-32B-only frame (R1)", "mcode_M8_R1": "M-code Qwen3-8B-only frame (R1)",\n          "mcode_PRIMARY_R1g": "M-code PRIMARY (R1 without massive tokens)",\n          "mcode_PRIMARY_R3": "M-code PRIMARY (16th code token, R3: negative control)"}\n\n\ndef _save(fig: Any, name: str) -> None:\n    # notebook: shown inline (the original wrote figures/<name>.pdf and figures/<name>.png)\n    plt.show()\n\n\ndef counts() -> tuple[Counter, Counter]:\n    # notebook: iteration 8\'s labelled C6 generations, counted per label in the demo data (original:\n    # inputs/e44/data/labelled_C6_baseline.jsonl, labelled_C6_ban.jsonl and labelled_C6_confirm.jsonl)\n    li = meta["landing_inputs"]\n    return Counter(li["C6_baseline_adj_label_counts"]), Counter(li["C6_ban_adj_label_counts"])\n\n\ndef _overlay(model_tag: str, name: str, z: Any) -> tuple[np.ndarray | None, str]:\n    comps, mean, L = z["pca_components"], z["pca_mean"], int(z["block"])\n    if name in ("mname", "mdesc"):\n        # notebook: the 7 ban-prompt states (cache/states/ban_32b.npz) are not in the demo data, so the figure\n        # falls back to the ring of 15 label-level survivors around the unit-Dijkstra centroid\n        return None, ""\n    if name.startswith("mcode"):\n        # notebook: survivor programs from the demo data (original: cache/states/mcode_<model>.npz + mcode_sets.json)\n        sel = [e for e in data["examples"] if e["manifold"] == "placement_SURV" and e["algorithm"] == UDIJ]\n        if sel:\n            Q = np.stack([np.frombuffer(base64.b64decode(e["x_f16_b64"]), dtype="<f2") for e in sel]).astype(np.float32)\n            return (Q - mean) @ comps.T, f"{len(sel)} unit-Dijkstra survivor programs (C6)"\n    return None, ""\n\n\ndef manifold_figs(model_tag: str, name: str, geo_res: dict[str, Any]) -> None:\n    z = COORDS.get(f"{model_tag}_{name}")       # notebook: in memory (original: figures/coords/<model>_<name>.npz)\n    if z is None:\n        return\n    labels = z["labels"]\n    L = int(z["block"])\n    present = [a for a in CANON_ORDER if a in set(labels.tolist())]\n    base, ban = counts()\n    cfg = MODELS[model_tag]\n    prec = "nf4" if model_tag == "32b" else "bf16"\n    mdl = "Qwen3-32B" if model_tag == "32b" else "Qwen3-8B"\n    readout = "SPEC-token mean (S-mean)" if not name.startswith("mcode") else TITLES[name].split("(")[-1].rstrip(")")\n    cap = f"{mdl} {prec}, block {L}, readout {readout}, N={len(labels)}"\n    P = z["pca2"]\n    evr = z["evr"]\n    Q, qlab = _overlay(model_tag, name, z)\n    fig, axes = plt.subplots(1, 2, figsize=(14, 6))\n    for ax, (cnt, ttl) in zip(axes, ((base, "C6 baseline implemented counts"), (ban, "C6 ban implemented counts "\n                                                                                    "(screen + confirm)"))):\n        for a in present:\n            s = labels == a\n            ax.scatter(P[s, 0], P[s, 1], s=10, color=COL[a], alpha=0.35)\n        vmax = max(1, max(cnt.get(a, 0) for a in present))\n        for a in present:\n            c = P[labels == a].mean(0)\n            n = cnt.get(a, 0)\n            ax.scatter([c[0]], [c[1]], s=60 + 40 * np.sqrt(n + 1), c=[[n / vmax]], cmap="viridis", vmin=0, vmax=1,\n                       edgecolors="red" if a in B5 else "black", linewidths=2.5 if a in B5 else 1.0, zorder=5)\n            ax.annotate(f"{SHORT[a]} ({n})", c, fontsize=8, xytext=(4, 4), textcoords="offset points")\n        if Q is not None:\n            mk = "*" if not name.startswith("mcode") else "x"\n            ax.scatter(Q[:, 0], Q[:, 1], marker=mk, s=110 if mk == "*" else 45, color="black", label=qlab, zorder=6)\n            ax.legend(loc="best", fontsize=8)\n        elif not name.startswith("mcode"):\n            c = P[labels == UDIJ].mean(0) if UDIJ in present else None\n            if c is not None:\n                th = np.linspace(0, 2 * np.pi, 15, endpoint=False)\n                r = 0.04 * (P.max() - P.min())\n                ax.scatter(c[0] + r * np.cos(th), c[1] + r * np.sin(th), s=12, marker="o", facecolors="none",\n                           edgecolors="black", label="15 unit-Dijkstra survivors (label-level)")\n                ax.legend(loc="best", fontsize=8)\n        ax.set_xlabel(f"PC1 ({100 * evr[0]:.1f}% var.)")\n        ax.set_ylabel(f"PC2 ({100 * evr[1]:.1f}% var.)")\n        ax.set_title(ttl, fontsize=10)\n    fig.suptitle(f"(a) PCA of residual states: {TITLES[name]}\\n{cap}; banned (red outline): "\n                 f"{\', \'.join(SHORT[b] for b in B5)}", fontsize=10)\n    _save(fig, f"pca_{model_tag}_{name}")\n    # (b) MDS\n    d = geo_res["L_star"]["describe"]\n    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))\n    Ym = z["mds"]\n    for a in present:\n        s = labels == a\n        axes[0].scatter(Ym[s, 0], Ym[s, 1], s=10, color=COL[a], label=SHORT[a], alpha=0.6)\n    axes[0].legend(fontsize=7, ncol=2)\n    axes[0].set_title(f"classical MDS of the {len(labels)} points (stress-1 {d[\'mds_points_stress1\']:.2f})", fontsize=10)\n    Yc = z["mds_c"]\n    for i, a in enumerate(present):\n        axes[1].scatter([Yc[i, 0]], [Yc[i, 1]], s=120, color=COL[a], edgecolors="red" if a in B5 else "black",\n                        linewidths=2.5 if a in B5 else 1)\n        axes[1].annotate(SHORT[a], Yc[i], fontsize=9, xytext=(5, 5), textcoords="offset points")\n    axes[1].set_title(f"classical MDS of the {len(present)} centroids (stress-1 {d[\'mds_centroids_stress1\']:.2f})",\n                      fontsize=10)\n    for ax in axes:\n        ax.set_xlabel("MDS 1")\n        ax.set_ylabel("MDS 2")\n    fig.suptitle(f"(b) {TITLES[name]} - {cap}", fontsize=10)\n    _save(fig, f"mds_{model_tag}_{name}")\n    # (c) Isomap with geodesic path uDij -> nearest banned\n    Y = z["iso"]\n    if len(Y):\n        geo = z["geo"]\n        fig, ax = plt.subplots(figsize=(8, 7))\n        for a in present:\n            s = labels == a\n            ax.scatter(Y[s, 0], Y[s, 1], s=12, color=COL[a], label=SHORT[a], alpha=0.7,\n                       edgecolors="red" if a in B5 else "none", linewidths=0.6)\n        kd = d[f"k{K_VERDICT}"]\n        if UDIJ in present:\n            nb = kd["nearest_banned"][UDIJ]\n            iu = np.where(labels == UDIJ)[0]\n            ib = np.where(labels == nb)[0]\n            sub = geo[np.ix_(iu, ib)]\n            i, j = np.unravel_index(np.argmin(sub), sub.shape)\n            G = FROZEN[f"geo_{model_tag}_{name}_k{K_VERDICT}"]["adjacency"]   # notebook: was cache/states/geo_*.npz\n            _, pred = shortest_path(G, method="D", directed=False, indices=[iu[i]], return_predecessors=True)\n            path, cur = [], ib[j]\n            while cur >= 0 and cur != iu[i]:\n                path.append(cur)\n                cur = pred[0, cur]\n            path.append(iu[i])\n            ax.plot(Y[path, 0], Y[path, 1], "k-", lw=1.5, label=f"geodesic {SHORT[UDIJ]} -> {SHORT[nb]}")\n            ttl = (f"class(uDij)={kd[\'classes\'][UDIJ]}, g={kd[\'g\'][UDIJ]:.2f}, median {kd[\'median\']:.2f}, "\n                   f"rank {kd[\'udij_rank\']}/{len(kd[\'g\'])}")\n        else:\n            ttl = "unit Dijkstra not in this manifold"\n        ax.legend(fontsize=7, ncol=2)\n        ax.set_xlabel("Isomap 1")\n        ax.set_ylabel("Isomap 2")\n        ax.set_title(f"(c) Isomap k={K_VERDICT}: {TITLES[name]}\\n{cap}; {ttl}", fontsize=9)\n        _save(fig, f"isomap_{model_tag}_{name}")\n    _ = cfg'}
```

### [102] TOOL RESULT — NotebookEdit · 2026-10-26 14:40:25 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [103] TOOL CALL — NotebookEdit · 2026-10-26 14:40:25 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': '## Stage 11: figures in activation coordinates\n\nThe plotting code of `src/stage_figures.py`. It draws from the in-memory coordinates instead of `figures/coords/*.npz` and shows figures inline instead of saving PDF / PNG. Per manifold:\n\n* **(a) PCA** of the states. Class centroids are sized and coloured by how often Qwen3-32B *implemented* each algorithm without the ban (left: BFS 91 of 100) and with it (right: unit Dijkstra 15 of 100). Banned algorithms are outlined in red. On M-code the 15 survivor programs are drawn as crosses; on M-name a ring of the 15 label-level survivors surrounds the unit-Dijkstra centroid, because the ban-prompt states are not in the demo data.\n* **(b) classical MDS** of the points and of the class centroids, with Kruskal stress-1.\n* **(c) Isomap** at k = 15, with the geodesic path (on the kNN graph) from unit Dijkstra to its nearest banned algorithm.'}
```

### [104] TOOL RESULT — NotebookEdit · 2026-10-26 14:40:25 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [105] ASSISTANT · 2026-10-26 14:42:21 UTC

```
The figure cells are in, in order. Next: the RSA, placement and audit cells (again in reverse).
```

### [106] TOOL CALL — NotebookEdit · 2026-10-26 14:42:21 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'def knn_geodesics(X, k):\n    nn = NearestNeighbors(n_neighbors=k + 1).fit(X)\n    dist, idx = nn.kneighbors(X)\n    G = nx.Graph()\n    G.add_nodes_from(range(len(X)))\n    for i in range(len(X)):\n        for d, j in zip(dist[i], idx[i]):\n            if j != i:\n                w = max(float(d), 1e-12)\n                if not G.has_edge(i, j) or G[i][j]["weight"] > w:\n                    G.add_edge(i, int(j), weight=w)\n    comps = [sorted(c) for c in nx.connected_components(G)]\n    if len(comps) > 1:\n        for a in range(len(comps)):\n            for b in range(a + 1, len(comps)):\n                A, Bc = np.array(comps[a]), np.array(comps[b])\n                D = np.linalg.norm(X[A][:, None, :] - X[Bc][None, :, :], axis=2)\n                i, j = np.unravel_index(np.argmin(D), D.shape)\n                G.add_edge(int(A[i]), int(Bc[j]), weight=max(float(D[i, j]), 1e-12))\n    n = len(X)\n    geo = np.zeros((n, n))\n    for s, dd in nx.all_pairs_dijkstra_path_length(G, weight="weight"):\n        for t, v in dd.items():\n            geo[s, t] = v\n    return geo, len(comps)\n\n\ndef g_classes(geo, labels):\n    nb = [a for a in NB5 if a in set(labels)]\n    g = {a: min(float(geo[np.ix_(labels == a, labels == b)].mean()) for b in B5 if (labels == b).any()) for a in nb}\n    m = float(np.median(list(g.values())))\n    cls = {a: "EDGE" if v < m - 1e-12 else "OPPOSITE" if v > m + 1e-12 else "MIDDLE" for a, v in g.items()}\n    return g, cls\n\n\n# main() of audit/audit_states.py, comparing with the in-memory geometry instead of results/geometry_all.json\naudit = {"checks": {}, "mismatches": []}\nrng = np.random.default_rng(0)\nfor key in ("32b|mname", "32b|mdesc", "32b|mlex", "32b|mcode_PRIMARY_R1"):\n    if key not in geo_results or key not in blocks_rec["manifolds"]:\n        continue\n    model, name = key.split("|")\n    m = load_manifold(model, name)        # notebook: the original load() read cache/states/<name>_<model>.npz directly\n    X, labels, bl = m["X"], m["labels"], m["blocks"]\n    L = blocks_rec["manifolds"][key]["L_star"]\n    Xb = X[:, bl.index(L)].astype(np.float64)\n    geo, ncomp = knn_geodesics(Xb, 15)\n    g, cls = g_classes(geo, labels)\n    ref = geo_results[key]["L_star"]["describe"]["k15"]\n    maxdiff = max(abs(g[a] - ref["g"][a]) for a in g)\n    same = cls == ref["classes"]\n    plac = []\n    for _ in range(20):\n        lp = rng.permutation(labels)\n        _, cp = g_classes(geo, lp)\n        plac.append(cp.get("dijkstra_unit") == cls.get("dijkstra_unit"))\n    audit["checks"][key] = {"block": L, "components": ncomp, "g": g, "classes": cls, "max_abs_g_diff": maxdiff,\n                            "classes_equal": same, "placebo_shuffled_labels_share_same_udij_class":\n                                float(np.mean(plac))}\n    if not same or maxdiff > 1e-6 * max(1.0, max(abs(v) for v in g.values())):\n        audit["mismatches"].append(key)\n    print(key, "classes equal", same, "max |dg|", maxdiff, "placebo", float(np.mean(plac)), flush=True)\nprint("mismatches:", audit["mismatches"])'}
```

### [107] TOOL RESULT — NotebookEdit · 2026-10-26 14:42:21 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [108] TOOL CALL — NotebookEdit · 2026-10-26 14:42:21 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "## Independent audit (`audit/audit_states.py`)\n\nA second code path that shares nothing with `geometry.py`. It recomputes g and the classes at k = 15 from the raw states, using sklearn's `NearestNeighbors` for the kNN graph and networkx for components, joins and Dijkstra. It must reproduce the classes exactly and g to floating-point precision (`mismatches` must be empty). A placebo shuffles the algorithm labels across points 20 times; it should not reproduce unit Dijkstra's class much more often than chance."}
```

### [109] TOOL RESULT — NotebookEdit · 2026-10-26 14:42:21 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [110] TOOL CALL — NotebookEdit · 2026-10-26 14:42:21 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '# ---------------------------------------------------------------------------------------------- placement\ndef oos(x: np.ndarray, F: np.ndarray, geo: np.ndarray, k: int) -> np.ndarray:\n    d = np.linalg.norm(F - x, axis=1)\n    nn = np.argsort(d)[:k]\n    return np.min(d[nn][:, None] + geo[nn], axis=0)\n\n\ndef _loo_one(args: tuple) -> tuple[int, str]:\n    i, F, labels, k = args\n    import geometry as gm\n\n    keep = np.ones(len(F), bool)\n    keep[i] = False\n    geo, _ = gm.geodesics(F[keep], k)\n    dv = oos(F[i], F[keep], geo, k)\n    lab = labels[keep]\n    algs = sorted(set(lab.tolist()))\n    means = {a: float(dv[lab == a].mean()) for a in algs}\n    return i, min(means, key=means.get)\n\n\ndef placement(model_tag: str, frame_name: str, L: int, k: int = K_VERDICT) -> dict[str, Any] | None:\n    m = load_manifold(model_tag, frame_name)\n    if m is None:\n        return None\n    ro = m["readout"]\n    F = m["X"][:, m["blocks"].index(L)].astype(np.float64)\n    labels = m["labels"]\n    geo, _ = geometry.geodesics(F, k)\n    nb = [a for a in NB5 if a in set(labels.tolist())]\n    g_frame, _ = geometry.g_values(geo, labels, [b for b in B5 if b in set(labels.tolist())], nb)\n    cls_frame, med = classes_of(g_frame)\n    # notebook: in-process map (the original mapped _loo_one over a spawn ProcessPoolExecutor)\n    loo = dict(map(_loo_one, [(i, F, labels, k) for i in range(len(F))]))\n    acc = float(np.mean([loo[i] == labels[i] for i in range(len(F))]))\n    # notebook: placement programs and their states come from the demo data (original: data/mcode_sets.json placement\n    # sets SURV / BASE / DISOBEY + cache/states/mcode_<model>.npz); the demo holds the 15 SURV unit-Dijkstra programs\n    rows = []\n    for p in [e for e in data["examples"] if e["manifold"] == "placement_SURV"]:\n        x = np.frombuffer(base64.b64decode(p["x_f16_b64"]), dtype="<f2").astype(np.float64)\n        dv = oos(x, F, geo, k)\n        means = {a: float(dv[labels == a].mean()) for a in sorted(set(labels.tolist()))}\n        gb = {b: means[b] for b in B5 if b in means}\n        gx = min(gb.values())\n        rows.append({"uid": p["point_id"], "set": p["set"], "label": p["algorithm"], "other_name": p.get("other_name"),\n                     "nearest_algorithm": min(means, key=means.get), "g_x": gx,\n                     "nearest_banned": min(gb, key=gb.get), "class": "EDGE" if gx < med - 1e-12 else\n                     ("OPPOSITE" if gx > med + 1e-12 else "MIDDLE"), "mean_geodesic": means,\n                     "g_scrub_pass": p.get("g_scrub_pass")})\n    ud = [r for r in rows if r["set"] == "SURV" and r["label"] == UDIJ]\n    n_edge = sum(r["class"] == "EDGE" for r in ud)\n    base = [r for r in rows if r["set"] == "BASE"]\n    # LOO g of frame uDij programs for the descriptive comparison\n    frame_ud_g = []\n    for i in np.where(labels == UDIJ)[0]:\n        keep = np.ones(len(F), bool)\n        keep[i] = False\n        g2, _ = geometry.geodesics(F[keep], k)\n        dv = oos(F[i], F[keep], g2, k)\n        frame_ud_g.append(min(float(dv[labels[keep] == b].mean()) for b in B5 if (labels[keep] == b).any()))\n    mw = None\n    if ud and frame_ud_g:\n        mw = mannwhitneyu([r["g_x"] for r in ud], frame_ud_g).pvalue\n    return {"frame": frame_name, "model": model_tag, "block": L, "k": k, "readout": ro,\n            "G_place": {"loo_accuracy": acc, "gate": LOO_GATE, "pass": acc >= LOO_GATE},\n            "frame_g": g_frame, "frame_classes": cls_frame, "frame_median": med,\n            "base_accuracy_own_label": float(np.mean([r["nearest_algorithm"] == r["label"] for r in base]))\n            if base else None,\n            "udij_survivors": {"n": len(ud), "n_edge": n_edge, "share_edge": n_edge / len(ud) if ud else None,\n                               "wilson95": wilson_ci(n_edge, len(ud)) if ud else None,\n                               "share_nearest_banned": float(np.mean([r["nearest_algorithm"] in B5 for r in ud]))\n                               if ud else None,\n                               "nearest_algorithm_counts": {a: sum(r["nearest_algorithm"] == a for r in ud)\n                                                            for a in CANON_ORDER},\n                               "mannwhitney_p_vs_frame_udij_loo": mw,\n                               "frame_udij_loo_g_median": float(np.median(frame_ud_g)) if frame_ud_g else None,\n                               "survivor_g_median": float(np.median([r["g_x"] for r in ud])) if ud else None},\n            "P8_pass": (n_edge / len(ud) > 0.5) if ud and acc >= LOO_GATE else None,\n            "rows": rows}\n\n\nt = time.time()\nplacement_results: dict[str, Any] = {}\nfor frame in ("mcode_PRIMARY_R1",):            # the full run also places on mcode_PRIMARY_R2 and mcode_M32_R1 (32b, 8b)\n    key = f"32b|{frame}"\n    if key in blocks_rec["manifolds"]:\n        r = placement("32b", frame, blocks_rec["manifolds"][key]["L_star"])\n        if r:\n            placement_results[key] = r\n            logger.info(f"placement {key}: LOO {r[\'G_place\'][\'loo_accuracy\']:.2f}; uDij survivors "\n                        f"EDGE {r[\'udij_survivors\'][\'n_edge\']}/{r[\'udij_survivors\'][\'n\']}")\nprint(f"placement: {time.time() - t:.1f} s")\npl = placement_results["32b|mcode_PRIMARY_R1"]\nus = pl["udij_survivors"]\nnear = ", ".join(f"{SHORT[a]} {c}" for a, c in us["nearest_algorithm_counts"].items() if c)\nprint(f"frame classes {pl[\'frame_classes\']} (median g {pl[\'frame_median\']:.2f}); leave-one-out placement accuracy "\n      f"{pl[\'G_place\'][\'loo_accuracy\']:.2f} (gate {LOO_GATE}: {pl[\'G_place\'][\'pass\']})")\nprint(f"unit-Dijkstra survivor programs at the EDGE: {us[\'n_edge\']}/{us[\'n\']} (Wilson 95% "\n      f"{np.round(us[\'wilson95\'], 2).tolist()}); nearest algorithm: {near}; P8 pass: {pl[\'P8_pass\']}")\nprint(f"survivor g median {us[\'survivor_g_median\']:.2f} vs frame unit-Dijkstra programs (leave-one-out) "\n      f"{us[\'frame_udij_loo_g_median\']:.2f}; Mann-Whitney p {us[\'mannwhitney_p_vs_frame_udij_loo\']:.3g}")\nfor row in pl["rows"]:\n    print(f"  {row[\'uid\']:14s} nearest {SHORT[row[\'nearest_algorithm\']]:11s} g_x {row[\'g_x\']:6.2f}  {row[\'class\']:8s} "\n          f"(nearest banned {SHORT[row[\'nearest_banned\']]})")'}
```

### [111] TOOL RESULT — NotebookEdit · 2026-10-26 14:42:21 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [112] TOOL CALL — NotebookEdit · 2026-10-26 14:42:21 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "## Stage 10c: where do the actual survivor programs land? (P8, out-of-sample placement)\n\nThe M-code manifold serves as a fixed *frame*, and new programs are placed in it without refitting:\n\n1. A new program x gets a geodesic distance to every frame point: the best path through one of its k nearest frame points (`oos`).\n2. Its class is EDGE if its smallest mean geodesic to a banned algorithm is below the frame's median g.\n3. **G-place gate**: the frame programs' leave-one-out placement accuracy must be at least 0.70.\n4. **P8**: more than half of the 15 unit-Dijkstra survivor programs land at the EDGE.\n\nThe full run also places the BASE and DISOBEY sets; those are not in the demo data."}
```

### [113] TOOL RESULT — NotebookEdit · 2026-10-26 14:42:21 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [114] TOOL CALL — NotebookEdit · 2026-10-26 14:42:21 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '# ---------------------------------------------------------------------------------------------- RSA\n_PERMS: dict[int, np.ndarray] = {}\n\n\ndef _perms(n: int) -> np.ndarray:\n    if n not in _PERMS:\n        _PERMS[n] = np.array(list(itertools.permutations(range(n))), dtype=np.int8)\n    return _PERMS[n]\n\n\ndef mantel_exact(neural: np.ndarray, model: np.ndarray) -> dict[str, Any]:\n    """Spearman over the upper triangle; exact p over all n! condition-label permutations (one-sided, >=)."""\n    n = len(neural)\n    iu = np.triu_indices(n, 1)\n    rv = rankdata(neural[iu])\n    rv = rv - rv.mean()\n    RM = np.zeros((n, n))\n    RM[iu] = rankdata(model[iu])\n    RM = RM + RM.T\n    rm = RM[iu] - RM[iu].mean()\n    rho = float((rv * rm).sum() / np.sqrt((rv ** 2).sum() * (rm ** 2).sum()))\n    P = _perms(n)\n    flat = RM.ravel()\n    mean_r = RM[iu].mean()\n    den = np.sqrt((rv ** 2).sum() * (rm ** 2).sum())\n    ge = 0\n    for s in range(0, len(P), 200000):\n        ch = P[s:s + 200000].astype(np.int64)\n        vals = flat[ch[:, iu[0]] * n + ch[:, iu[1]]] - mean_r\n        r = (vals @ rv) / den\n        ge += int(np.sum(r >= rho - 1e-12))\n    return {"rho": rho, "p_exact": ge / len(P), "n_perms": int(len(P)), "n_pairs": int(len(rv))}\n\n\ndef model_rdms(manifold: str) -> dict[str, np.ndarray]:\n    # notebook: the model RDMs come from the demo data (original: results/behavioural_distance.json, lexical.json,\n    # surface_rdm.json and data/descriptions_v0.json); a JSON null is a NaN of the original\n    md = meta["model_rdms"]\n    out = {"R_lex": np.array(md["R_lex"], dtype=float), "R_beh": np.array(md["R_beh"], dtype=float),\n           "R_beh_order": np.array(md["R_beh_order"], dtype=float), "R_DS": np.array(md["R_DS"], dtype=float)}\n    out["R_surface"] = np.array(md["R_surface"], dtype=float)\n    if manifold in md.get("R_len", {}):\n        out["R_len"] = np.array(md["R_len"][manifold], dtype=float)\n    out["R_desc_lex"] = np.array(md["R_desc_lex"], dtype=float)\n    return out\n\n\ndef rsa(geo_results: dict[str, Any]) -> dict[str, Any]:\n    out: dict[str, Any] = {}\n    for key, r in geo_results.items():\n        if r is None:\n            continue\n        model_tag, name = key.split("|")\n        d = r["L_star"]["describe"]\n        M = np.array(d[f"k{K_VERDICT}"]["class_geodesic_matrix"])\n        M = (M + M.T) / 2\n        present = [i for i, a in enumerate(CANON_ORDER) if a in d["present"]]\n        Mn = M[np.ix_(present, present)]\n        mr = model_rdms("mcode" if name.startswith("mcode") else name)\n        sh = r["L_star"]["split_half"][f"k{K_VERDICT}"]\n        res = {"present": [CANON_ORDER[i] for i in present], "noise_ceiling_upper": sh["noise_ceiling_upper"],\n               "split_half_spearman_brown": sh["spearman_brown"], "models": {}}\n        for mn, R in mr.items():\n            Rm = R[np.ix_(present, present)]\n            if not np.isfinite(Rm).all():\n                continue\n            res["models"][mn] = mantel_exact(Mn, Rm)\n        # bootstrap CIs of rho differences from the stored bootstrap matrices\n        bp = f"boot_{model_tag}_{name}_k{K_VERDICT}"    # notebook: in memory (original: cache/states/<bp>.npy)\n        if bp in BOOT_MATS:\n            mats = BOOT_MATS[bp]\n            iu = np.triu_indices(len(present), 1)\n            diffs = {}\n            for a_, b_ in (("R_lex", "R_beh"), ("R_beh", "R_lex"), ("R_surface", "R_beh")):\n                if a_ in mr and b_ in mr:\n                    Ra = mr[a_][np.ix_(present, present)][iu]\n                    Rb = mr[b_][np.ix_(present, present)][iu]\n                    vals = []\n                    for Mb in mats:\n                        v = np.asarray(Mb)[np.ix_(present, present)][iu]\n                        if not np.isfinite(v).all():\n                            continue\n                        vals.append(spearmanr(v, Ra).statistic - spearmanr(v, Rb).statistic)\n                    if vals:\n                        diffs[f"{a_}-{b_}"] = {"mean": float(np.mean(vals)),\n                                               "ci95": [float(np.quantile(vals, 0.025)),\n                                                        float(np.quantile(vals, 0.975))], "n": len(vals)}\n            res["rho_differences_bootstrap"] = diffs\n        if name.startswith("mcode") and "R_surface" in mr and "R_len" in mr:\n            iu = np.triu_indices(len(present), 1)\n            v = Mn[iu]\n            rb = mr["R_beh"][np.ix_(present, present)][iu]\n            z1 = mr["R_surface"][np.ix_(present, present)][iu]\n            res["partial_beh_given_surface"] = partial_spearman(v, rb, z1)\n        out[key] = res\n        logger.info(f"RSA {key}: " + ", ".join(f"{k} {v[\'rho\']:.2f} (p {v[\'p_exact\']:.4f})"\n                                               for k, v in res["models"].items()))\n    return out\n\n\nt = time.time()\nrsa_results = rsa(geo_results)\nprint(f"RSA: {time.time() - t:.1f} s")\nfor key, r in rsa_results.items():\n    print(f"\\n{key}: {len(r[\'present\'])} algorithms, noise ceiling (upper) {r[\'noise_ceiling_upper\']:.2f}")\n    for mn, v in r["models"].items():\n        print(f"  {mn:11s} rho {v[\'rho\']:+.2f}   exact p {v[\'p_exact\']:.4f}   ({v[\'n_perms\']:,} permutations)")\n    for dk, dv in r.get("rho_differences_bootstrap", {}).items():\n        print(f"  bootstrap rho({dk.replace(\'-\', \') - rho(\')}): mean {dv[\'mean\']:+.2f}, 95% CI "\n              f"{np.round(dv[\'ci95\'], 2).tolist()} (n {dv[\'n\']})")\n    if "partial_beh_given_surface" in r:\n        print(f"  partial rho(neural, R_beh | R_surface) {r[\'partial_beh_given_surface\']:+.2f}")'}
```

### [115] TOOL RESULT — NotebookEdit · 2026-10-26 14:42:21 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [116] TOOL CALL — NotebookEdit · 2026-10-26 14:42:21 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "## Stage 10b: representational similarity analysis\n\nThe neural RDM is the symmetrised class-geodesic matrix at k = 15 over the algorithms present. It is compared (Spearman over the upper triangle) with model RDMs that are computed without the model's activations:\n\n* **R_lex**: lexical distance between the algorithms' alias strings (character 3-grams);\n* **R_beh**: behavioural distance from expansion-order traces of reference implementations on 40 probe grids (`R_beh_order` and `R_DS` are its two components);\n* **R_surface**: 1 - Jaccard of identifier-normalised AST 4-gram shingles of the PRIMARY programs;\n* **R_len**: difference in mean stimulus token length; **R_desc_lex**: lexical distance between the descriptions.\n\n`mantel_exact` enumerates **all** n! relabellings of the algorithms: 10! = 3,628,800 for M-name and 6! = 720 for M-code. That gives an exact one-sided p. Bootstrap CIs of rho differences reuse the bootstrap class matrices. The full run also tests *name evocation* (a probe trained on M-name, applied to the other manifolds), which needs all 300 M-name states and is not part of the demo."}
```

### [117] TOOL RESULT — NotebookEdit · 2026-10-26 14:42:21 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [118] ASSISTANT · 2026-10-26 14:43:55 UTC

```
The RSA, placement and audit cells are in. Next: the lexical-regression cells, the geometry run cell, and `analyse_manifold`.
```

### [119] TOOL CALL — NotebookEdit · 2026-10-26 14:43:55 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '# ---------------------------------------------------------------------------------------------- lexical regression\ndef _perm_p(x: np.ndarray, y: np.ndarray, n: int = 100000, seed: int = 0) -> float:\n    rng = np.random.default_rng(seed)\n    r0 = spearmanr(x, y).statistic\n    rx, ry = rankdata(x), rankdata(y)\n    ry = ry - ry.mean()\n    P = np.argsort(rng.random((n, len(x))), axis=1)\n    rxp = rx[P] - rx.mean()\n    rr = (rxp * ry).sum(1) / np.sqrt((rxp ** 2).sum(1) * (ry ** 2).sum())\n    return float(np.mean(rr <= r0 + 1e-12)) if r0 < 0 else float(np.mean(rr >= r0 - 1e-12))\n\n\ndef partial_spearman(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> float:\n    rx, ry, rz = rankdata(x), rankdata(y), rankdata(z)\n    A = np.c_[np.ones(len(rz)), rz]\n    ex = rx - A @ np.linalg.lstsq(A, rx, rcond=None)[0]\n    ey = ry - A @ np.linalg.lstsq(A, ry, rcond=None)[0]\n    den = np.sqrt((ex ** 2).sum() * (ey ** 2).sum())\n    return float((ex * ey).sum() / den) if den > 0 else float("nan")\n\n\ndef alias_level(model_tag: str, name: str, L: int) -> dict[str, Any] | None:\n    m = load_manifold(model_tag, name)\n    if m is None:\n        return None\n    lex = {"aliases": meta["lexical_aliases"]}       # notebook: was read_json(RESULTS / "lexical.json")\n    lx = {(r["algorithm"], r["alias_index"]): r for r in lex["aliases"]}\n    X = m["X"][:, m["blocks"].index(L)].astype(np.float64)\n    out = {}\n    key_arr = m["alias"] if name in ("mname", "mlex") else None\n    for k in (K_SECOND, K_VERDICT):\n        geo, _ = geometry.geodesics(X, k)\n        rows = []\n        for a in NB5:\n            for j in range(3):\n                sel = (m["labels"] == a) & (key_arr == j)\n                gm = min(float(np.mean(geo[np.ix_(sel, m["labels"] == b)])) for b in B5)\n                rows.append({"algorithm": a, "alias_index": j, "g_alias": gm, **{f: lx[(a, j)][f] for f in\n                                                                                 ("L1", "L2", "L3", "n_tokens")}})\n        g = np.array([r["g_alias"] for r in rows])\n        res: dict[str, Any] = {"rows": rows}\n        for f in ("L1", "L2", "L3"):\n            v = np.array([r[f] for r in rows], dtype=float)\n            res[f"spearman_{f}"] = float(spearmanr(g, v).statistic)\n            res[f"perm_p_{f}"] = _perm_p(g, v, n=PERM_P_N)          # notebook: n from the config cell\n            res[f"partial_{f}_given_length"] = partial_spearman(g, v, np.array([r["n_tokens"] for r in rows]))\n        # within-algorithm test: demean by algorithm, exact 6^5 within-algorithm permutations of L2\n        algs = [r["algorithm"] for r in rows]\n        gd = g - np.array([np.mean([g[i] for i in range(15) if algs[i] == algs[t]]) for t in range(15)])\n        L2 = np.array([r["L2"] for r in rows])\n        L2d = L2 - np.array([np.mean([L2[i] for i in range(15) if algs[i] == algs[t]]) for t in range(15)])\n        r0 = float(np.corrcoef(gd, L2d)[0, 1]) if L2d.std() > 0 else float("nan")\n        perms = list(itertools.permutations(range(3)))\n        cnt, tot = 0, 0\n        for combo in itertools.product(perms, repeat=5):\n            L2p = np.concatenate([L2d[3 * i:3 * i + 3][list(p)] for i, p in enumerate(combo)])\n            r = float(np.corrcoef(gd, L2p)[0, 1]) if L2p.std() > 0 else 0.0\n            cnt += r <= r0 + 1e-12\n            tot += 1\n        res["within_algorithm"] = {"pearson_demeaned_g_L2": r0, "exact_p_lower": cnt / tot, "n_perms": tot}\n        out[f"k{k}"] = res\n    out["P4_pass"] = all(out[f"k{k}"]["spearman_L1"] <= -0.6 for k in (K_SECOND, K_VERDICT))\n    return out\n\n\nt = time.time()\nlex_results = {"32b|mname": alias_level("32b", "mname", blocks_rec["manifolds"]["32b|mname"]["L_star"])}\nprint(f"lexical regression: {time.time() - t:.1f} s")\nlr = lex_results["32b|mname"]\nalias_text = {(r["algorithm"], r["alias_index"]): r["alias"] for r in meta["lexical_aliases"]}\nfor row in lr[f"k{K_VERDICT}"]["rows"]:\n    print(f"  {alias_text[(row[\'algorithm\'], row[\'alias_index\'])]:34s} L1 {row[\'L1\']}   "\n          f"g_alias (k={K_VERDICT}) {row[\'g_alias\']:6.2f}")\nfor k in (K_SECOND, K_VERDICT):\n    x = lr[f"k{k}"]\n    print(f"k={k}: Spearman(g_alias, L1) {x[\'spearman_L1\']:+.2f} (perm p {x[\'perm_p_L1\']:.4f}), partial given length "\n          f"{x[\'partial_L1_given_length\']:+.2f}; L3 {x[\'spearman_L3\']:+.2f}; within-algorithm exact p (L2) "\n          f"{x[\'within_algorithm\'][\'exact_p_lower\']:.3f} ({x[\'within_algorithm\'][\'n_perms\']:,} permutations)")\nprint("P4 pass (<= -0.6 at both k):", lr["P4_pass"])'}
```

### [120] TOOL RESULT — NotebookEdit · 2026-10-26 14:43:55 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [121] TOOL CALL — NotebookEdit · 2026-10-26 14:43:55 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': '## Stage 10a: do the names drive the name-based geometry? (P4, alias level)\n\nEach non-banned algorithm has three aliases ("bidirectional BFS", "BiBFS", ...), 15 in all. For each one:\n\n* **g_alias** is the smallest mean geodesic distance from that alias\'s prompts to a banned algorithm.\n* **L1** counts the banned algorithms whose alias patterns match the alias string. For example, "bidirectional **BFS**" contains a banned name.\n\nPre-registered prediction **P4**: Spearman(g_alias, L1) <= -0.6 at k = 10 and at k = 15. That is, aliases containing a banned name sit closer to the banned region. Also reported: a permutation p, the partial correlation given alias token length, and an exact within-algorithm permutation test (6^5 = 7,776 permutations of L2 within each algorithm).'}
```

### [122] TOOL RESULT — NotebookEdit · 2026-10-26 14:43:55 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [123] TOOL CALL — NotebookEdit · 2026-10-26 14:43:55 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 't = time.time()\ngeo_results: dict[str, Any] = {}\nfor name in MANIFOLDS_DEMO:\n    r = analyse_manifold("32b", name, blocks_rec)\n    if r is not None:\n        geo_results[f"32b|{name}"] = r\nprint(f"geometry: {time.time() - t:.1f} s")\nfor key, r in geo_results.items():\n    d = r["L_star"]["describe"]\n    print(f"\\n{key}: block {r[\'L_star\'][\'block\']}, {d[\'n_points\']} points, PCA EVR(1-3) "\n          f"{np.round(d[\'pca_evr\'][:3], 3).tolist()}, MDS stress-1 points {d[\'mds_points_stress1\']:.2f} / "\n          f"centroids {d[\'mds_centroids_stress1\']:.2f}")\n    for k in KS:\n        s = r["summary"][f"k{k}"]\n        print(f"  k={k:2d}: {SHORT[UDIJ]} {s[\'udij_class\']:8s} rank {s[\'udij_rank\']}/{len(d[f\'k{k}\'][\'g\'])}  g/median "\n              f"{s[\'udij_ratio\']:.2f}  nearest banned {SHORT[s[\'udij_nearest_banned\']]:5s} landing {s[\'verdict_pooled\']}"\n              f"  | g: " + ", ".join(f"{SHORT[a]} {v:.1f}" for a, v in d[f"k{k}"]["g"].items()))\n    bs = r["L_star"]["bootstrap"][f"k{K_VERDICT}"]\n    print(f"  bootstrap k={K_VERDICT} (n={bs[\'n_boot\']}): P(EDGE) {bs[\'edge_probability\'][UDIJ]:.2f}, class stability "\n          f"{bs[\'class_stability\'][UDIJ]:.2f}, g/median 95% CI {np.round(bs[\'udij_ratio_ci95\'], 2).tolist()}")\n    lp = r["L_star"]["landing"][f"k{K_VERDICT}"]["pooled"]\n    print(f"  landing k={K_VERDICT} (15 pooled survivors): S {lp[\'S\']:.2f}, p_edge U {lp[\'nulls\'][\'U\'][\'p_edge\']:.3f} "\n          f"F {lp[\'nulls\'][\'F\'][\'p_edge\']:.3f} P {lp[\'nulls\'][\'P\'][\'p_edge\']:.3f} C {lp[\'nulls\'][\'C\'][\'p_edge\']:.3f}; "\n          f"p_opp U {lp[\'nulls\'][\'U\'][\'p_opp\']:.3f} F {lp[\'nulls\'][\'F\'][\'p_opp\']:.3f} -> {lp[\'verdict\']}")\n    print(f"  split-half Spearman-Brown k={K_VERDICT}: {r[\'L_star\'][\'split_half\'][f\'k{K_VERDICT}\'][\'spearman_brown\']:.2f}; "\n          f"crossnobis {r[\'L_star\'][\'crossnobis\'][\'classes\'].get(UDIJ)}, z-scored "\n          f"{r[\'L_star\'][\'zscored\'][\'classes\'].get(UDIJ)}, Euclidean centroid {d[\'euclid_centroid\'][\'classes\'].get(UDIJ)}; "\n          f"robustness cells {r[\'L_star\'][\'robustness\'][\'udij_class_counts\']}")'}
```

### [124] TOOL RESULT — NotebookEdit · 2026-10-26 14:43:55 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [125] TOOL CALL — NotebookEdit · 2026-10-26 14:43:55 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "### Run it on M-name (names) and M-code (programs)\n\nThese are the two manifolds that disagree in the full run. For each one the cell prints, at every k:\n\n* unit Dijkstra's class, rank and g / median;\n* its nearest banned algorithm and the pooled landing verdict;\n* the g value of every non-banned algorithm present.\n\nIt then prints the bootstrap stability, the landing-null p-values, the split-half reliability and the sensitivity classes (crossnobis, z-scored, Euclidean centroid). Unit Dijkstra's rank counts from 1, nearest to the banned five, among the non-banned algorithms present: 5 on M-name, but only 2 on M-code, where IDA* and unit Dijkstra are the only non-banned algorithms with at least 10 verified programs."}
```

### [126] TOOL RESULT — NotebookEdit · 2026-10-26 14:43:55 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [127] TOOL CALL — NotebookEdit · 2026-10-26 14:43:55 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'BOOT_MATS: dict[str, np.ndarray] = {}     # notebook: bootstrap class matrices (original: cache/states/boot_*.npy)\nFROZEN: dict[str, dict[str, Any]] = {}    # notebook: frozen kNN graphs for iteration 10 (original: cache/states/geo_*.npz)\nCOORDS: dict[str, dict[str, Any]] = {}    # notebook: figure inputs (original: figures/coords/<model>_<name>.npz)\n\n\ndef analyse_manifold(model_tag: str, name: str, blocks_rec: dict[str, Any]) -> dict[str, Any] | None:\n    m = load_manifold(model_tag, name)\n    if m is None:\n        return None\n    cfg = MODELS[model_tag]\n    key = f"{model_tag}|{name}"\n    L = blocks_rec["manifolds"][key]["L_star"]\n    res: dict[str, Any] = {"model": model_tag, "manifold": name, "L_star": L, "ref_block": cfg["ref_block"],\n                           "n_points": int(len(m["X"])), "layer_curve": blocks_rec["manifolds"][key]}\n    n_boot = N_BOOT_32B if model_tag == "32b" and name in VERDICT_MANIFOLDS[:4] else N_BOOT_OTHER\n    for tag_b, b in (("L_star", L), ("ref_block", cfg["ref_block"])):\n        if tag_b == "ref_block" and b == L:\n            res["ref_block_same_as_L_star"] = True\n            continue\n        if b not in m["blocks"]:                  # notebook: the demo data hold block L* only\n            res[f"{tag_b}_not_in_demo_data"] = b\n            continue\n        X = m["X"][:, m["blocks"].index(b)].astype(np.float64)\n        d = describe(X, m["labels"], embed=(tag_b == "L_star"))\n        emb = d.pop("_emb")\n        sec: dict[str, Any] = {"block": b, "describe": d}\n        sec["landing"] = {f"k{k}": landing_all(d[f"k{k}"]["g"], d[f"k{k}"]["classes"]) for k in (K_SECOND, K_VERDICT)}\n        sec["split_half"] = {f"k{k}": {kk: vv for kk, vv in split_half(X, m["labels"], m["groups"], k).items()\n                                       if kk != "half_matrices"} for k in KS}\n        if tag_b == "L_star":\n            sec["bootstrap"] = {}\n            for k in (K_VERDICT, K_SECOND):\n                bs = bootstrap(X, m["labels"], m["groups"], k, n_boot, d[f"k{k}"], seed=k)\n                mats = bs.pop("_matrices")\n                BOOT_MATS[f"boot_{model_tag}_{name}_k{k}"] = np.array(mats, dtype=np.float32)\n                sec["bootstrap"][f"k{k}"] = bs\n            sec["robustness"] = robustness(m["X"], m["labels"], m["blocks"], L)\n            sec["crossnobis"] = crossnobis(X, m["labels"], m["groups"])\n            mu, sd = X.mean(0), X.std(0) + 1e-8\n            dz = describe((X - mu) / sd, m["labels"], ks=(K_VERDICT,))\n            dz.pop("_emb")\n            sec["zscored"] = {"classes": dz[f"k{K_VERDICT}"]["classes"], "g": dz[f"k{K_VERDICT}"]["g"]}\n            # freeze for iteration 10 (out-of-sample placement without refitting)\n            for k in (K_SECOND, K_VERDICT):\n                G, ncomp, added = geometry.knn_graph(X, k)\n                FROZEN[f"geo_{model_tag}_{name}_k{k}"] = dict(\n                    geo=emb["geo"][k], adjacency=G.toarray().astype(np.float32), X=X.astype(np.float32),\n                    labels=m["labels"], point_ids=m["ids"], block=L, readout=m.get("readout", "S-mean"),\n                    standardised=False, k=k)\n            # figure inputs (2-D coordinates only)\n            pca2 = emb["pca"].transform(X)[:, :2]\n            iso = emb.get("isomap")\n            COORDS[f"{model_tag}_{name}"] = dict(\n                pca2=pca2, evr=np.array(d["pca_evr"][:2]), mds=emb["mds_points"], mds_c=emb["mds_centroids"],\n                iso=iso[1] if iso else np.zeros((0, 2)), labels=m["labels"], geo=emb["geo"][K_VERDICT], block=L,\n                pca_components=emb["pca"].components_[:2].astype(np.float32),\n                pca_mean=emb["pca"].mean_.astype(np.float32),\n                isomap_model=iso[0] if iso else None)   # notebook: kept to embed the survivors in the final figure\n        res[tag_b] = sec\n    v = res["L_star"]["describe"]\n    res["summary"] = {f"k{k}": {"udij_class": v[f"k{k}"]["classes"].get(UDIJ), "udij_rank": v[f"k{k}"]["udij_rank"],\n                                "udij_ratio": v[f"k{k}"]["udij_ratio"], "udij_nearest_banned":\n                                    v[f"k{k}"]["nearest_banned"].get(UDIJ), "classes": v[f"k{k}"]["classes"],\n                                "verdict_pooled": res["L_star"]["landing"].get(f"k{k}", {}).get("pooled", {}).get(\n                                    "verdict") if k in (K_SECOND, K_VERDICT) else None} for k in KS}\n    logger.info(f"[{model_tag} {name}] L*={L} k15 {res[\'summary\'][\'k15\'][\'classes\']} verdict "\n                f"{res[\'summary\'][\'k15\'][\'verdict_pooled\']} | k10 {res[\'summary\'][\'k10\'][\'udij_class\']} "\n                f"{res[\'summary\'][\'k10\'][\'verdict_pooled\']}")\n    return res'}
```

### [128] TOOL RESULT — NotebookEdit · 2026-10-26 14:43:55 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [129] TOOL CALL — NotebookEdit · 2026-10-26 14:43:55 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "## Stages 7-10 together: `analyse_manifold`\n\nThis is the artifact's per-manifold driver. It is unchanged except where it wrote files: the bootstrap class matrices, the frozen kNN graphs (kept for iteration 10) and the 2-D figure coordinates now stay in memory (`BOOT_MATS`, `FROZEN`, `COORDS`).\n\nThe reference-block section re-describes the manifold at block 31, so the two manifolds can be compared at one depth. For M-name, L\\* already is block 31. For M-code (L\\* = 33), block 31 is not in the demo data, so the section is skipped."}
```

### [130] TOOL RESULT — NotebookEdit · 2026-10-26 14:43:55 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [131] ASSISTANT · 2026-10-26 14:45:29 UTC

```
The driver and lexical cells are in. Next: `load_manifold`, `describe`, the reliability functions, and `landing_all`/`robustness`.
```

### [132] TOOL CALL — NotebookEdit · 2026-10-26 14:45:29 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'def landing_all(g: dict[str, float], cls: dict[str, str]) -> dict[str, Any]:\n    # notebook: iteration 8\'s labelled C6 baseline, counted per label in the demo data\n    # (original: base = read_jsonl(IN_E44 / "data" / "labelled_C6_baseline.jsonl"))\n    base = meta["landing_inputs"]["C6_baseline_adj_label_counts"]\n    base_counts = {a: base.get(a, 0) for a in g}\n    rates = forced_rates_e44()\n    out = {}\n    for nm, surv in (("screen", SURV_SCREEN), ("confirm", SURV_CONFIRM), ("pooled", SURV_SCREEN + SURV_CONFIRM)):\n        surv_ok = [s for s in surv if s in g]\n        if not surv_ok:\n            out[nm] = {"verdict": "UNTESTABLE (survivor algorithm not in the manifold)"}\n            continue\n        out[nm] = landing.strip(landing.landing(g, cls, surv_ok, base_counts, rates, draws=LANDING_DRAWS))\n    return out\n\n\ndef robustness(Xb: np.ndarray, labels: np.ndarray, blocks: list[int], L: int) -> dict[str, Any]:\n    cells = {}\n    for b in range(L - 2, L + 3):\n        if b not in blocks:\n            continue\n        X = Xb[:, blocks.index(b)].astype(np.float64)\n        nb = [a for a in NB5 if a in set(labels.tolist())]\n        bp = [b for b in B5 if b in set(labels.tolist())]\n        for k in KS:\n            geo, info = geometry.geodesics(X, k)\n            g, _ = geometry.g_values(geo, labels, bp, nb)\n            cls, _ = classes_of(g)\n            lk = landing_all(g, cls)["pooled"]\n            cells[f"L{b}_k{k}"] = {"udij_class": cls.get(UDIJ), "classes": cls, "verdict": lk.get("verdict"),\n                                   "components": info["components_before_join"]}\n    from collections import Counter\n\n    return {"cells": cells, "udij_class_counts": dict(Counter(c["udij_class"] for c in cells.values())),\n            "verdict_counts": dict(Counter(c["verdict"] for c in cells.values())), "n_cells": len(cells)}'}
```

### [133] TOOL RESULT — NotebookEdit · 2026-10-26 14:45:29 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [134] TOOL CALL — NotebookEdit · 2026-10-26 14:45:29 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "## Stage 9: landing test and robustness grid\n\n* `landing_all` runs iteration 8's landing test three times: on the 6 survivors from the ban screen, on the 9 from the confirmation run, and on all 15 pooled. All of them are unit-Dijkstra programs. The baseline counts and the forced rates feed the F and C nulls.\n* `robustness` repeats the classes and the pooled verdict for every block from L\\*-2 to L\\*+2 and every k. The demo data hold block L\\* only, so here the grid has the 3 cells at L\\* (the full run has 15)."}
```

### [135] TOOL RESULT — NotebookEdit · 2026-10-26 14:45:29 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [136] TOOL CALL — NotebookEdit · 2026-10-26 14:45:29 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'def split_half(X: np.ndarray, labels: np.ndarray, groups: np.ndarray, k: int) -> dict[str, Any]:\n    ug = np.unique(groups)\n    thr = ug[len(ug) // 2]\n    h1 = groups < thr\n    mats = []\n    for m in (h1, ~h1):\n        geo, _ = geometry.geodesics(X[m], k)\n        M = geometry.class_matrix(geo, labels[m], CANON_ORDER)\n        mats.append((M + M.T) / 2)\n    present = [i for i, a in enumerate(CANON_ORDER) if a in set(labels.tolist())]\n    iu = [(i, j) for i, j in itertools.combinations(present, 2)]\n    a = [mats[0][i, j] for i, j in iu]\n    b = [mats[1][i, j] for i, j in iu]\n    rho = float(spearmanr(a, b).statistic)\n    sb = 2 * rho / (1 + rho) if rho > -1 else float("nan")\n    return {"k": k, "split_threshold_group": int(thr), "spearman_halves": rho, "spearman_brown": sb,\n            "noise_ceiling_upper": float(np.sqrt(max(sb, 0.0))), "flag_unreliable": sb < RELIABILITY_FLAG,\n            "half_matrices": [m.tolist() for m in mats]}\n\n\ndef _boot_chunk(args: tuple) -> list[dict[str, Any]]:\n    X, labels, groups, k, seeds = args\n    import geometry as gm\n    b5, nb5 = B5, NB5                         # notebook: was `from tpg import B5 as b5, NB5 as nb5`\n\n    nb = [a for a in nb5 if a in set(labels.tolist())]\n    b5 = [b for b in b5 if b in set(labels.tolist())]\n    ug = np.unique(groups)\n    out = []\n    for s in seeds:\n        rng = np.random.default_rng(s)\n        gs = rng.choice(ug, size=len(ug), replace=True)\n        idx = np.concatenate([np.where(groups == g)[0] for g in gs])\n        Xb = X[idx] + rng.normal(0, 1e-9, size=X[idx].shape)\n        geo, _ = gm.geodesics(Xb, k)\n        g, near = gm.g_values(geo, labels[idx], b5, nb)\n        M = gm.class_matrix(geo, labels[idx], list(__import__("common").CANON_ORDER))\n        out.append({"g": g, "near": near, "M": ((M + M.T) / 2).tolist()})\n    return out\n\n\ndef bootstrap(X: np.ndarray, labels: np.ndarray, groups: np.ndarray, k: int, n_boot: int, full: dict[str, Any],\n              seed: int = 0) -> dict[str, Any]:\n    seeds = [seed * 100000 + i for i in range(n_boot)]\n    chunks = [seeds[i::N_WORKERS] for i in range(N_WORKERS)]\n    # notebook: the chunks run in-process (the original mapped them over a spawn ProcessPoolExecutor)\n    res = [r for part in map(_boot_chunk, [(X, labels, groups, k, c) for c in chunks if c]) for r in part]\n    nb = list(full["g"].keys())\n    full_cls = full["classes"]\n    cls_runs = [classes_of(r["g"])[0] for r in res]\n    ratios = [r["g"][UDIJ] / float(np.median(list(r["g"].values()))) for r in res] if UDIJ in nb else []\n    ranks = [sorted(nb, key=lambda a: r["g"][a]).index(UDIJ) + 1 for r in res] if UDIJ in nb else []\n    return {"n_boot": len(res), "k": k,\n            "class_stability": {a: float(np.mean([c[a] == full_cls[a] for c in cls_runs])) for a in nb},\n            "edge_probability": {a: float(np.mean([c[a] == "EDGE" for c in cls_runs])) for a in nb},\n            "opposite_probability": {a: float(np.mean([c[a] == "OPPOSITE" for c in cls_runs])) for a in nb},\n            "nearest_banned_stability": {a: float(np.mean([r["near"][a] == full["nearest_banned"][a] for r in res]))\n                                         for a in nb},\n            "udij_ratio_ci95": [float(np.quantile(ratios, 0.025)), float(np.quantile(ratios, 0.975))] if ratios\n            else None, "udij_rank_distribution": {int(v): ranks.count(v) for v in sorted(set(ranks))},\n            "_matrices": [r["M"] for r in res]}\n\n\ndef crossnobis(X: np.ndarray, labels: np.ndarray, groups: np.ndarray) -> dict[str, Any]:\n    """Split-half cross-validated squared centroid distances d2(a,b) = (mu_a^A - mu_b^A).(mu_a^B - mu_b^B)."""\n    ug = np.unique(groups)\n    thr = ug[len(ug) // 2]\n    h1 = groups < thr\n    present = [a for a in CANON_ORDER if a in set(labels.tolist())]\n    muA = {a: X[h1 & (labels == a)].mean(0) for a in present}\n    muB = {a: X[~h1 & (labels == a)].mean(0) for a in present}\n    D = np.zeros((10, 10))\n    for i, a in enumerate(CANON_ORDER):\n        for j, b in enumerate(CANON_ORDER):\n            if a in present and b in present and a != b:\n                D[i, j] = float((muA[a] - muA[b]) @ (muB[a] - muB[b]))\n    nb = [a for a in NB5 if a in present]\n    g = {a: min(D[CANON_ORDER.index(a), CANON_ORDER.index(b)] for b in B5 if b in present) for a in nb}\n    cls, med = classes_of(g)\n    return {"d2_cv": D.tolist(), "g": g, "classes": cls, "median": med}'}
```

### [137] TOOL RESULT — NotebookEdit · 2026-10-26 14:45:29 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [138] TOOL CALL — NotebookEdit · 2026-10-26 14:45:29 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "## Stage 8: reliability checks\n\n* `split_half` splits the paraphrase groups in two and recomputes the class-geodesic matrix on each half, then correlates the halves (Spearman, Spearman-Brown corrected). Its square root is the noise ceiling used by the RSA.\n* `bootstrap` resamples the paraphrase groups with replacement `n_boot` times; a 1e-9 jitter keeps duplicate points distinct. It recomputes g and the classes each time and reports how stable unit Dijkstra's class, rank and g / median are.\n* `crossnobis` computes split-half cross-validated squared centroid distances. This distance is unbiased and does not use the kNN graph.\n\nThe original mapped `_boot_chunk` over a spawn `ProcessPoolExecutor` with 12 workers. Here the chunks run in-process, which gives identical results because every resample has its own seed. In the demo M-name subset the paraphrase groups are its 3 aliases (template 0 only), so its bootstrap and split-half are coarse."}
```

### [139] TOOL RESULT — NotebookEdit · 2026-10-26 14:45:29 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [140] TOOL CALL — NotebookEdit · 2026-10-26 14:45:29 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '# ---------------------------------------------------------------------------------------------- geometry\ndef classes_of(g: dict[str, float]) -> tuple[dict[str, str], float]:\n    return geometry.classify(g)\n\n\ndef describe(X: np.ndarray, labels: np.ndarray, ks: tuple[int, ...] = KS, embed: bool = False) -> dict[str, Any]:\n    present = [a for a in CANON_ORDER if a in set(labels.tolist())]\n    nb = [a for a in NB5 if a in present]\n    bp = [b for b in B5 if b in present]\n    out: dict[str, Any] = {"n_points": int(len(X)), "present": present, "nonbanned_used": nb, "banned_used": bp}\n    from sklearn.decomposition import PCA\n\n    pca = PCA(n_components=min(10, len(X) - 1), random_state=0).fit(X)\n    out["pca_evr"] = pca.explained_variance_ratio_.tolist()\n    D = geometry.squareform(geometry.pdist(X))\n    Ym = geometry.classical_mds(D)\n    out["mds_points_stress1"] = geometry.stress1(D, Ym)\n    cent = np.stack([X[labels == c].mean(0) for c in present])\n    Dc = geometry.squareform(geometry.pdist(cent))\n    Ymc = geometry.classical_mds(Dc)\n    out["mds_centroids_stress1"] = geometry.stress1(Dc, Ymc)\n    out["centroid_distance_matrix"] = Dc.tolist()\n    emb = {"pca": pca, "mds_points": Ym, "mds_centroids": Ymc, "geo": {}, "D": D}\n    for k in ks:\n        geo, info = geometry.geodesics(X, k)\n        g, near = geometry.g_values(geo, labels, bp, nb)\n        cls, med = classes_of(g)\n        M = geometry.class_matrix(geo, labels, CANON_ORDER)\n        rank = sorted(nb, key=lambda a: g[a]).index(UDIJ) + 1 if UDIJ in nb else None\n        out[f"k{k}"] = {**info, "g": g, "nearest_banned": near, "classes": cls, "median": med,\n                        "class_geodesic_matrix": M.tolist(), "udij_rank": rank,\n                        "udij_ratio": (g[UDIJ] / med) if UDIJ in nb and med > 0 else None}\n        emb["geo"][k] = geo\n    gc_, nc_ = geometry.g_centroid(X, labels, bp, nb)\n    clc, medc = classes_of(gc_)\n    out["euclid_centroid"] = {"g": gc_, "nearest_banned": nc_, "classes": clc, "median": medc}\n    if embed:\n        from sklearn.manifold import Isomap\n\n        iso = Isomap(n_neighbors=K_VERDICT, n_components=2).fit(X)\n        emb["isomap"] = (iso, iso.embedding_)\n    out["_emb"] = emb\n    return out'}
```

### [141] TOOL RESULT — NotebookEdit · 2026-10-26 14:45:29 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [142] TOOL CALL — NotebookEdit · 2026-10-26 14:45:29 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "## Stage 7: the geometry of one manifold\n\n`describe` (from `src/stage_analysis.py`) describes one manifold at one block:\n\n* PCA explained-variance ratios, and classical MDS of the points and of the class centroids, each with its stress.\n* For every k in `KS`: the kNN geodesics; the g value and nearest banned algorithm of each non-banned algorithm; the EDGE / MIDDLE / OPPOSITE classes; the 10 x 10 class-geodesic matrix.\n* Unit Dijkstra's rank (1 = nearest to the banned five) and its g / median ratio (below 1 = EDGE side).\n* As a sensitivity check, g computed from Euclidean centroid distances instead of geodesics.\n\nWith classes defined relative to the median of the non-banned algorithms, EDGE versus OPPOSITE is a *relative* statement: closer to (or farther from) the banned region than the typical non-banned algorithm."}
```

### [143] TOOL RESULT — NotebookEdit · 2026-10-26 14:45:29 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [144] TOOL CALL — NotebookEdit · 2026-10-26 14:45:29 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '# ---------------------------------------------------------------------------------------------- loading\ndef load_manifold(model_tag: str, name: str) -> dict[str, Any] | None:\n    """X [n, n_blocks, d] float32, labels, groups, ids, blocks, stimulus info.\n    Notebook: built from mini_demo_data.json (block L* only) instead of cache/states/<name>_<model>.npz."""\n    rows = [e for e in data["examples"] if e["manifold"] == name]\n    if model_tag != "32b" or not rows:\n        return None\n    X = np.stack([np.frombuffer(base64.b64decode(e["x_f16_b64"]), dtype="<f2") for e in rows])   # cached float16\n    m = {"X": X[:, None, :].astype(np.float32), "labels": np.array([e["algorithm"] for e in rows]),\n         "groups": np.array([e["group"] for e in rows]).astype(int), "ids": np.array([e["point_id"] for e in rows]),\n         "blocks": [int(rows[0]["block"])]}\n    if name == "mname":\n        m["template"] = np.array([e["template"] for e in rows])\n        m["alias"] = np.array([e["alias_index"] for e in rows])\n    if name.startswith("mcode_"):\n        _, frame, ro = name.split("_")\n        m.update({"readout": ro, "frame": frame, "keys": np.array([e["scrubbed_sha256"] for e in rows])})\n    return m\n\n\n# Stage 6 record (predictions/commit2.json): the label-only layer choice, hash-committed before landing / placement\nblocks_rec = {"manifolds": {key: {"L_star": L} for key, L in meta["L_star"].items()}}\nfor name in MANIFOLDS_DEMO:\n    m = load_manifold("32b", name)\n    print(f"{name:17s} X {tuple(m[\'X\'].shape)} {m[\'X\'].dtype}, block {m[\'blocks\']}, paraphrase groups "\n          f"{sorted(set(m[\'groups\'].tolist()))}, points per algorithm {dict(Counter(m[\'labels\'].tolist()))}")\nex_name = next(e for e in data["examples"] if e["manifold"] == "mname")\nex_code = next(e for e in data["examples"] if e["manifold"] == "mcode_PRIMARY_R1" and e["algorithm"] == UDIJ)\nprint(f"\\nM-name point {ex_name[\'point_id\']}:\\n{ex_name[\'input\'][:420]} ...")\nprint(f"\\nM-code point {ex_code[\'point_id\']} (unit Dijkstra, name-scrubbed):\\n{ex_code[\'input\'][:700]}")'}
```

### [145] TOOL RESULT — NotebookEdit · 2026-10-26 14:45:29 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [146] TOOL CALL — NotebookEdit · 2026-10-26 14:45:29 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "## Stage 5 output: the activation states\n\nIn the artifact, `method.py mname 32b` and `method.py states 32b mdesc mcode` run every stimulus through Qwen3-32B (nf4, decoder truncated to 48 of its 64 blocks). For every block from 17 to 47 they store:\n\n* **S-mean** for prompts (M-name): the mean residual-stream state over the tokens of the task specification.\n* **R1** for programs (M-code): the mean state over the program's code tokens, with the program teacher-forced as the assistant's answer.\n\nStage 6 (`method.py blocks`) then picks one layer per manifold *from the labels only*: grouped 10-fold CV of a PCA-64 + logistic-regression probe, argmax, ties broken toward depth 0.5. The choice is hash-committed before any landing or placement is computed: **L\\* = 31 for M-name and 33 for M-code**.\n\n`load_manifold` below returns the same structure as the original: `X` of shape `[n, n_blocks, d]`, labels, paraphrase groups, ids and blocks. Here it is built from the demo data, which hold block L\\* only. The paraphrase groups are the units that split-half and bootstrap resample: (template, alias) for M-name, and set rank mod 10 for M-code."}
```

### [147] TOOL RESULT — NotebookEdit · 2026-10-26 14:45:29 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [148] THINKING · 2026-10-26 14:47:09 UTC

```
Now I'll add the module cells—copying `geometry.py` and `landing.py` verbatim, followed by the `common.py` excerpt and `tpg.py` constants—then diff the written files against the originals after the first run.
```

### [149] TOOL CALL — NotebookEdit · 2026-10-26 14:47:09 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'import geometry\nimport landing\nfrom common import CANON_ORDER, SHORT, wilson_ci\n\n# ---------------------------------------------------------------------------------------------- catalogue split\nB5 = ["bfs", "dfs", "iddfs", "astar", "gbfs"]                       # banned (iteration-8 C6 top five)\nNB5 = ["bibfs", "biastar", "idastar", "jps", "dijkstra_unit"]       # non-banned\nUDIJ = "dijkstra_unit"\nassert set(B5) | set(NB5) == set(CANON_ORDER)\n\n# ---------------------------------------------------------------------------------------------- models\nM32 = {"repo": "unsloth/Qwen3-32B-bnb-4bit", "revision": "7f721e74a6a8cc9ee352f7e49303a2c1705f9083",\n       "precision": "nf4", "n_layers": 64, "n_keep": 48, "ext_blocks": list(range(17, 48)),\n       "sel_blocks": list(range(19, 46)), "tag": "32b", "engine": "hf-nf4-truncated", "ref_block": 31}\nMODELS = {"32b": M32}            # the artifact also pins Qwen/Qwen3-8B (bf16) as "8b"; its states are not in the demo\n\n# ---------------------------------------------------------------------------------------------- frozen settings\nMCODE_MIN = 10\nLOO_GATE = 0.70\nRELIABILITY_FLAG = 0.70\n\n# Survivors of iteration 8 (C6, Qwen3-32B thinking on): label-level landing input (landing.json / confirmation.json).\nSURV_SCREEN = [UDIJ] * 6\nSURV_CONFIRM = [UDIJ] * 9\n\n# src/stage_analysis.py\nVERDICT_MANIFOLDS = ["mname", "mdesc", "mlex", "mcode_PRIMARY_R1", "mcode_PRIMARY_R2", "mcode_M32_R1", "mcode_M8_R1"]\n\n\ndef forced_rates_e44() -> dict[str, float]:\n    """Correct-when-forced rates recovered from iteration 8\'s null_C_probs (p - 0.5/40).\n    Notebook: computed from inputs/e44/results/landing.json when the demo data were built."""\n    return dict(meta["landing_inputs"]["forced_rates_e44"])\n\n\nprint("banned:", [SHORT[a] for a in B5], "| non-banned:", [SHORT[a] for a in NB5])\nprint("Qwen3-32B implemented, no ban (100 generations):", meta["landing_inputs"]["C6_baseline_adj_label_counts"])\nprint("Qwen3-32B implemented, top five banned (100 generations):", meta["landing_inputs"]["C6_ban_adj_label_counts"])\nprint("correct-when-forced rates (C null):", forced_rates_e44())'}
```

### [150] TOOL RESULT — NotebookEdit · 2026-10-26 14:47:10 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [151] TOOL CALL — NotebookEdit · 2026-10-26 14:47:10 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "### Frozen protocol constants (`src/tpg.py`)\n\nThe banned / non-banned split, the model pin and the gates were frozen and hash-committed before any state was computed. The values below are copied from `src/tpg.py`. The landing inputs that `tpg.forced_rates_e44()` and `landing_all()` read from iteration 8's files are included in `mini_demo_data.json`. The cell also prints the behavioural starting point: what Qwen3-32B implements without the ban and with it."}
```

### [152] TOOL RESULT — NotebookEdit · 2026-10-26 14:47:10 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [153] TOOL CALL — NotebookEdit · 2026-10-26 14:47:10 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '%%writefile tpg_modules/landing.py\n#!/usr/bin/env python3\n"""Stage 7 G5 landing test. S = mean over correct survivors of g_k(label). Nulls (seed 0):\n  U: labels iid uniform over the 5 non-banned algorithms, 10,000 draws (committed)\n  F: iid by m*\'s baseline frequency among non-banned algorithms, +0.5 smoothing, 10,000 draws (committed)\n  P: exact 120 permutations of algorithm identities among the 5, count profile fixed -> algorithm-level p (added)\n  C: iid by correct-when-forced rates, +0.5 smoothed (added; correctness-filter confound)\np_edge = P(S_null <= S); p_opp = P(S_null >= S).\nVERDICT: EDGE iff p_edge(U) < 0.05 and p_edge(F) < 0.05 and > 50% of survivors in EDGE algorithms; OPPOSITE mirrored;\nelse NEITHER. p(P) and p(C) always printed beside it.\n"""\n\nfrom __future__ import annotations\n\nimport collections\nimport itertools\nfrom typing import Any\n\nimport numpy as np\n\n\ndef stat(g: dict[str, float], labels: list[str]) -> float:\n    return float(np.mean([g[a] for a in labels])) if labels else float("nan")\n\n\ndef iid_null(g: dict[str, float], probs: dict[str, float], n: int, draws: int = 10000, seed: int = 0) -> np.ndarray:\n    algs = list(g)\n    p = np.array([probs[a] for a in algs], dtype=float)\n    p = p / p.sum()\n    vals = np.array([g[a] for a in algs])\n    rng = np.random.default_rng(seed)\n    idx = rng.choice(len(algs), size=(draws, n), p=p)\n    return vals[idx].mean(1)\n\n\ndef perm_null(g: dict[str, float], labels: list[str]) -> np.ndarray:\n    algs = list(g)\n    cnt = collections.Counter(labels)\n    counts = np.array([cnt[a] for a in algs], dtype=float)\n    vals = np.array([g[a] for a in algs])\n    out = []\n    for perm in itertools.permutations(range(len(algs))):\n        out.append(float((counts * vals[list(perm)]).sum() / counts.sum()))\n    return np.array(out)\n\n\ndef pvals(null: np.ndarray, S: float) -> dict[str, float]:\n    eps = 1e-12\n    return {"p_edge": float(np.mean(null <= S + eps)), "p_opp": float(np.mean(null >= S - eps)),\n            "null_mean": float(null.mean()), "null_q": np.quantile(null, [0.025, 0.05, 0.5, 0.95, 0.975]).tolist(),\n            "n": int(len(null))}\n\n\ndef landing(g: dict[str, float], classes: dict[str, str], surv: list[str], base_counts: dict[str, int],\n            forced_rates: dict[str, float], draws: int = 10000, seed: int = 0) -> dict[str, Any]:\n    nonbanned = list(g)\n    n = len(surv)\n    out: dict[str, Any] = {"n_surv": n, "survivor_counts": dict(collections.Counter(surv)), "g": g, "classes": classes}\n    if n == 0:\n        out.update({"S": None, "verdict": "NO SURVIVORS", "descriptive_only": True})\n        return out\n    S = stat(g, surv)\n    out["S"] = S\n    U = iid_null(g, {a: 1.0 for a in nonbanned}, n, draws, seed)\n    fprobs = {a: base_counts.get(a, 0) + 0.5 for a in nonbanned}\n    F = iid_null(g, fprobs, n, draws, seed + 1)\n    P = perm_null(g, surv)\n    cprobs = {a: forced_rates.get(a, 0.0) + 0.5 / 40 for a in nonbanned}\n    C = iid_null(g, cprobs, n, draws, seed + 2)\n    out["nulls"] = {"U": pvals(U, S), "F": pvals(F, S), "P": pvals(P, S), "C": pvals(C, S)}\n    out["null_F_probs"] = fprobs\n    out["null_F_near_uniform"] = all(base_counts.get(a, 0) == 0 for a in nonbanned)\n    out["null_C_probs"] = cprobs\n    share = collections.Counter(classes[a] for a in surv)\n    out["class_shares"] = {k: v / n for k, v in share.items()}\n    pU, pF = out["nulls"]["U"], out["nulls"]["F"]\n    if pU["p_edge"] < 0.05 and pF["p_edge"] < 0.05 and share["EDGE"] / n > 0.5:\n        v = "EDGE"\n    elif pU["p_opp"] < 0.05 and pF["p_opp"] < 0.05 and share["OPPOSITE"] / n > 0.5:\n        v = "OPPOSITE"\n    else:\n        v = "NEITHER"\n    out["verdict"] = v\n    out["descriptive_only"] = n < 5\n    out["perm_floor"] = float(1.0 / len(P) * sum(1 for x in P if abs(x - P.min()) < 1e-12))\n    out["_nulls_raw"] = {"U": U, "F": F, "P": P, "C": C}\n    return out\n\n\ndef strip(d: dict[str, Any]) -> dict[str, Any]:\n    return {k: v for k, v in d.items() if not k.startswith("_")}'}
```

### [154] TOOL RESULT — NotebookEdit · 2026-10-26 14:47:10 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [155] TOOL CALL — NotebookEdit · 2026-10-26 14:47:10 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "### `landing.py` (iteration 8, imported unchanged)\n\nThe **landing test** asks whether the 15 survivors land closer to the banned five than chance would put them. That is 6 from the ban screen and 9 from the confirmation run, all unit Dijkstra.\n\n* **Statistic**: S = mean g over the survivors' algorithms.\n* **Nulls**:\n  * U: labels drawn iid uniformly over the non-banned algorithms;\n  * F: iid by the unbanned baseline frequencies, with +0.5 smoothing;\n  * P: exact permutations of the algorithm identities;\n  * C: iid by the correct-when-forced rates.\n* **Verdict**: EDGE iff p_edge(U) < 0.05, p_edge(F) < 0.05 and most survivors sit in EDGE algorithms; OPPOSITE is the mirror image; otherwise NEITHER."}
```

### [156] TOOL RESULT — NotebookEdit · 2026-10-26 14:47:10 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [157] TOOL CALL — NotebookEdit · 2026-10-26 14:47:10 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '%%writefile tpg_modules/geometry.py\n#!/usr/bin/env python3\n"""Stage 7 G2/G3 geometry in actual activation coordinates (no summary bars).\n\nG2 L*: per block, standardise -> PCA(64) fit in fold -> multinomial logistic regression (C=1); grouped 10-fold CV with\ngroups = (template t, alias j) pairs (a held-out paraphrase is held out for all 10 algorithms); score = balanced\naccuracy; L* = argmax, ties within 0.01 -> block nearest depth 0.5 (all at ceiling -> nearest depth 0.5 among ceiling).\nG3 M1 at L*: PCA 2D (EVR), classical MDS on the 300 points and the 10 centroids (Kruskal stress-1), Isomap k in\n{5,10,15} on the symmetrised kNN distance graph (shortest inter-component edges added if disconnected, component count\nrecorded), geodesics via scipy shortest_path. g_k(a) = min over b in B of mean geodesic distance over pairs (points of\na, points of b) (iteration-7 top5geo.py definition). Classes: EDGE g < median, MIDDLE g == median, OPPOSITE g > median\nover the 5 non-banned algorithms. Reliability: split-half Spearman of 10x10 mean-geodesic matrices; 1,000 bootstrap\nresamples of paraphrase groups -> class and nearest-banned stability.\n"""\n\nfrom __future__ import annotations\n\nfrom typing import Any\n\nimport numpy as np\nfrom loguru import logger\nfrom scipy.sparse import csr_matrix\nfrom scipy.sparse.csgraph import connected_components, shortest_path\nfrom scipy.spatial.distance import cdist, pdist, squareform\nfrom scipy.stats import spearmanr\n\nfrom common import CANON_ORDER\n\n\n# ---------------------------------------------------------------------------------------------- layer selection\ndef layer_curve(X_blocks: np.ndarray, labels: np.ndarray, groups: np.ndarray, blocks: list[int],\n                sel_blocks: list[int], n_layers: int) -> dict[str, Any]:\n    from sklearn.decomposition import PCA\n    from sklearn.linear_model import LogisticRegression\n    from sklearn.metrics import balanced_accuracy_score\n    from sklearn.model_selection import GroupKFold\n    from sklearn.pipeline import make_pipeline\n    from sklearn.preprocessing import StandardScaler\n\n    curve = {}\n    preds = {}\n    gkf = GroupKFold(n_splits=10)\n    for b in sel_blocks:\n        X = X_blocks[:, blocks.index(b)].astype(np.float64)\n        pred = np.empty(len(labels), dtype=object)\n        for tr, te in gkf.split(X, labels, groups):\n            clf = make_pipeline(StandardScaler(), PCA(n_components=min(64, len(tr) - 1), random_state=0),\n                                LogisticRegression(C=1.0, max_iter=3000))\n            clf.fit(X[tr], labels[tr])\n            pred[te] = clf.predict(X[te])\n        curve[b] = float(balanced_accuracy_score(labels, pred.astype(str)))\n        preds[b] = [str(x) for x in pred]\n    best = max(curve.values())\n    near = [b for b in sel_blocks if best - curve[b] <= 0.01]\n    L = min(near, key=lambda b: (abs((b + 1) / n_layers - 0.5), b))\n    ceiling = [b for b in sel_blocks if curve[b] >= 0.9999]\n    rule = "argmax (ties within 0.01 -> nearest depth 0.5)"\n    if len(ceiling) == len(sel_blocks):\n        L = min(ceiling, key=lambda b: (abs((b + 1) / n_layers - 0.5), b))\n        rule = "all blocks at ceiling -> nearest depth 0.5"\n    return {"curve": curve, "L_star": int(L), "best": best, "tied_blocks": near, "rule": rule,\n            "depth_of_L_star": (L + 1) / n_layers, "cv_pred_at_L": preds[L]}\n\n\n# ---------------------------------------------------------------------------------------------- graphs\ndef knn_graph(X: np.ndarray, k: int) -> tuple[csr_matrix, int, int]:\n    """Symmetrised kNN distance graph; disconnected components joined by their shortest inter-component edges\n    (as sklearn Isomap does). Returns (graph, components before joining, edges added)."""\n    D = squareform(pdist(X))\n    n = len(X)\n    D[D == 0] = 1e-12                       # duplicates (bootstrap) stay connected\n    np.fill_diagonal(D, 0.0)\n    W = np.zeros((n, n))\n    order = np.argsort(D, axis=1)\n    for i in range(n):\n        nb = [j for j in order[i] if j != i][:k]\n        W[i, nb] = D[i, nb]\n    W = np.maximum(W, W.T)\n    G = csr_matrix(W)\n    ncomp, lab = connected_components(G, directed=False)\n    added = 0\n    if ncomp > 1:\n        for a in range(ncomp):\n            for b in range(a + 1, ncomp):\n                ia, ib = np.where(lab == a)[0], np.where(lab == b)[0]\n                sub = D[np.ix_(ia, ib)]\n                i, j = np.unravel_index(np.argmin(sub), sub.shape)\n                W[ia[i], ib[j]] = W[ib[j], ia[i]] = max(sub[i, j], 1e-12)\n                added += 1\n        G = csr_matrix(W)\n    return G, int(ncomp), added\n\n\ndef geodesics(X: np.ndarray, k: int) -> tuple[np.ndarray, dict[str, Any]]:\n    Xu = X.copy()\n    # exact duplicates (bootstrap resamples) -> jitter-free handling: dedupe by index mapping\n    G, ncomp, added = knn_graph(Xu, k)\n    geo = shortest_path(G, method="D", directed=False)\n    return geo, {"k": k, "components_before_join": ncomp, "edges_added": added, "connected": ncomp == 1,\n                 "finite": bool(np.isfinite(geo).all())}\n\n\ndef class_matrix(geo: np.ndarray, labels: np.ndarray, classes: list[str]) -> np.ndarray:\n    M = np.zeros((len(classes), len(classes)))\n    for i, a in enumerate(classes):\n        for j, b in enumerate(classes):\n            sub = geo[np.ix_(labels == a, labels == b)]\n            if i == j:\n                sub = sub[~np.eye(len(sub), dtype=bool)] if sub.shape[0] == sub.shape[1] else sub\n            M[i, j] = float(np.mean(sub)) if sub.size else np.nan\n    return M\n\n\ndef g_values(geo: np.ndarray, labels: np.ndarray, banned: list[str], nonbanned: list[str]) -> tuple[dict, dict]:\n    g, near = {}, {}\n    for a in nonbanned:\n        dm = [float(np.mean(geo[np.ix_(labels == a, labels == b)])) for b in banned]\n        g[a] = min(dm)\n        near[a] = banned[int(np.argmin(dm))]\n    return g, near\n\n\ndef g_centroid(X: np.ndarray, labels: np.ndarray, banned: list[str], nonbanned: list[str]) -> tuple[dict, dict]:\n    cent = {c: X[labels == c].mean(0) for c in set(labels)}\n    g, near = {}, {}\n    for a in nonbanned:\n        dm = [float(np.linalg.norm(cent[a] - cent[b])) for b in banned]\n        g[a] = min(dm)\n        near[a] = banned[int(np.argmin(dm))]\n    return g, near\n\n\ndef classify(g: dict[str, float]) -> tuple[dict[str, str], float]:\n    med = float(np.median(list(g.values())))\n    cls = {a: ("EDGE" if v < med - 1e-12 else "OPPOSITE" if v > med + 1e-12 else "MIDDLE") for a, v in g.items()}\n    return cls, med\n\n\n# ---------------------------------------------------------------------------------------------- embeddings\ndef stress1(D: np.ndarray, Y: np.ndarray) -> float:\n    d = squareform(pdist(Y))\n    iu = np.triu_indices(len(D), 1)\n    return float(np.sqrt(((D[iu] - d[iu]) ** 2).sum() / (D[iu] ** 2).sum()))\n\n\ndef classical_mds(D: np.ndarray, k: int = 2) -> np.ndarray:\n    n = len(D)\n    J = np.eye(n) - 1.0 / n\n    B = -0.5 * J @ (D ** 2) @ J\n    w, V = np.linalg.eigh(B)\n    i = np.argsort(w)[::-1][:k]\n    return V[:, i] * np.sqrt(np.maximum(w[i], 0))\n\n\ndef manifold(X: np.ndarray, labels: np.ndarray, banned: list[str], ks: tuple[int, ...] = (5, 10, 15),\n             fit_isomap: bool = True) -> dict[str, Any]:\n    """Full M1 description at one block (raw coordinates)."""\n    from sklearn.decomposition import PCA\n    from sklearn.manifold import Isomap\n\n    nonbanned = [a for a in CANON_ORDER if a not in banned]\n    out: dict[str, Any] = {"n_points": int(len(X)), "banned": banned, "nonbanned": nonbanned}\n    pca = PCA(n_components=10, random_state=0).fit(X)\n    out["pca_evr"] = pca.explained_variance_ratio_[:10].tolist()\n    D = squareform(pdist(X))\n    Ym = classical_mds(D)\n    out["mds_points_stress1"] = stress1(D, Ym)\n    cent = np.stack([X[labels == c].mean(0) for c in CANON_ORDER])\n    Dc = squareform(pdist(cent))\n    Ymc = classical_mds(Dc)\n    out["mds_centroids_stress1"] = stress1(Dc, Ymc)\n    out["centroid_distance_matrix"] = Dc.tolist()\n    emb: dict[str, Any] = {"pca": pca, "mds_points": Ym, "mds_centroids": Ymc, "isomap": {}, "geo": {}}\n    for k in ks:\n        geo, info = geodesics(X, k)\n        g, near = g_values(geo, labels, banned, nonbanned)\n        cls, med = classify(g)\n        M = class_matrix(geo, labels, CANON_ORDER)\n        out[f"k{k}"] = {**info, "g": g, "nearest_banned": near, "classes": cls, "median": med,\n                        "class_geodesic_matrix": M.tolist()}\n        emb["geo"][k] = geo\n        if fit_isomap:\n            iso = Isomap(n_neighbors=k, n_components=2)\n            Y = iso.fit_transform(X)\n            out[f"k{k}"]["isomap_stress1_vs_geodesic"] = stress1(np.where(np.isfinite(geo), geo, np.nanmax(\n                geo[np.isfinite(geo)])), Y)\n            emb["isomap"][k] = (iso, Y)\n    gc_, nc_ = g_centroid(X, labels, banned, nonbanned)\n    clc, medc = classify(gc_)\n    out["euclid_centroid"] = {"g": gc_, "nearest_banned": nc_, "classes": clc, "median": medc}\n    out["k_primary"] = 10 if out["k10"]["connected"] else next((k for k in ks if out[f"k{k}"]["connected"]), 10)\n    return out | {"_emb": emb}\n\n\ndef split_half(X: np.ndarray, labels: np.ndarray, groups: np.ndarray, k: int) -> dict[str, Any]:\n    h1 = groups < 15\n    res = {}\n    mats = []\n    for m in (h1, ~h1):\n        geo, info = geodesics(X[m], k)\n        mats.append(class_matrix(geo, labels[m], CANON_ORDER))\n    iu = np.triu_indices(10, 1)\n    rho = spearmanr(mats[0][iu], mats[1][iu]).statistic\n    res["spearman_offdiag"] = float(rho)\n    res["k"] = k\n    return res\n\n\ndef bootstrap(X: np.ndarray, labels: np.ndarray, groups: np.ndarray, banned: list[str], k: int, n_boot: int = 1000,\n              seed: int = 0) -> dict[str, Any]:\n    """Resample the 30 paraphrase groups with replacement; duplicates are kept as distinct points (a zero-length edge\n    is replaced by 1e-12 so duplicates stay connected)."""\n    rng = np.random.default_rng(seed)\n    nonbanned = [a for a in CANON_ORDER if a not in banned]\n    ug = np.unique(groups)\n    full_g, full_near = g_values(geodesics(X, k)[0], labels, banned, nonbanned)\n    full_cls, _ = classify(full_g)\n    same_cls = {a: 0 for a in nonbanned}\n    same_near = {a: 0 for a in nonbanned}\n    edge_count = {a: 0 for a in nonbanned}\n    for _ in range(n_boot):\n        gs = rng.choice(ug, size=len(ug), replace=True)\n        idx = np.concatenate([np.where(groups == g)[0] for g in gs])\n        Xb = X[idx] + rng.normal(0, 1e-9, size=X[idx].shape)\n        geo, _info = geodesics(Xb, k)\n        g, near = g_values(geo, labels[idx], banned, nonbanned)\n        cls, _ = classify(g)\n        for a in nonbanned:\n            same_cls[a] += cls[a] == full_cls[a]\n            same_near[a] += near[a] == full_near[a]\n            edge_count[a] += cls[a] == "EDGE"\n    return {"n_boot": n_boot, "k": k, "class_stability": {a: same_cls[a] / n_boot for a in nonbanned},\n            "nearest_banned_stability": {a: same_near[a] / n_boot for a in nonbanned},\n            "edge_probability": {a: edge_count[a] / n_boot for a in nonbanned}, "full_classes": full_cls,\n            "full_nearest": full_near}\n\n\ndef strip_private(d: dict[str, Any]) -> dict[str, Any]:\n    return {k: v for k, v in d.items() if not k.startswith("_")}\n\n\ndef synthetic_ring(n_per: int = 30, dim: int = 50, radius: float = 10.0, noise: float = 1.0,\n                   seed: int = 0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:\n    """T8: 10 Gaussian clusters on a ring (algorithms in canonical order around the ring)."""\n    rng = np.random.default_rng(seed)\n    X, lab, grp = [], [], []\n    basis = np.linalg.qr(rng.normal(size=(dim, 2)))[0]\n    for i, a in enumerate(CANON_ORDER):\n        th = 2 * np.pi * i / 10\n        c = radius * (np.cos(th) * basis[:, 0] + np.sin(th) * basis[:, 1])\n        X.append(c + noise * rng.normal(size=(n_per, dim)) / np.sqrt(dim) * 3)\n        lab += [a] * n_per\n        grp += list(range(n_per))\n    return np.concatenate(X), np.array(lab), np.array(grp)\n\n\ndef log_summary(tag: str, m: dict[str, Any]) -> None:\n    kp = m["k_primary"]\n    logger.info(f"[{tag}] PCA EVR {np.round(m[\'pca_evr\'][:2], 3).tolist()}, MDS stress1 points "\n                f"{m[\'mds_points_stress1\']:.3f} centroids {m[\'mds_centroids_stress1\']:.3f}; k={kp} classes "\n                f"{m[f\'k{kp}\'][\'classes\']} comps {[m[f\'k{k}\'][\'components_before_join\'] for k in (5, 10, 15)]}")'}
```

### [158] TOOL RESULT — NotebookEdit · 2026-10-26 14:47:10 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [159] TOOL CALL — NotebookEdit · 2026-10-26 14:47:10 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "### `geometry.py` (iteration 8, imported unchanged)\n\nThe core of the method. For one manifold (points `X`, algorithm `labels`) at one layer:\n\n* **kNN geodesics.** Connect every point to its k nearest neighbours (Euclidean distance, symmetrised graph). Disconnected components are joined by their shortest edge, as sklearn's Isomap does. Dijkstra on this graph then gives distances that follow the manifold instead of cutting straight through space.\n* **g(a)** for a non-banned algorithm a: the mean geodesic distance between the points of a and the points of a banned algorithm b, minimised over the five banned b. A small g means a is close to some banned algorithm.\n* **Class.** EDGE if g(a) is below the median g of the non-banned algorithms, OPPOSITE if above, MIDDLE if equal.\n* **Embeddings** for the figures: PCA, classical MDS (with Kruskal stress-1) and Isomap.\n\nThe module also keeps iteration 8's `layer_curve`, `manifold`, `split_half`, `bootstrap` and synthetic-ring test. Iteration 9 calls only the graph, g, class and embedding helpers; its own wrappers come from `stage_analysis.py` (below)."}
```

### [160] TOOL RESULT — NotebookEdit · 2026-10-26 14:47:10 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [161] TOOL CALL — NotebookEdit · 2026-10-26 14:47:10 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '%%writefile tpg_modules/common.py\n"""Excerpt of the artifact\'s src/common.py: only the definitions the analysis stages use, copied unchanged (the full\nmodule also holds the T1 task text, the alias table, prompt templates, paths, the hash-chained commitments and the\nOpenRouter cost ledger)."""\n\nfrom __future__ import annotations\n\nimport math\n\nCANON_ORDER = ["bfs", "dfs", "bibfs", "iddfs", "astar", "gbfs", "dijkstra_unit", "idastar", "jps", "biastar"]\nSHORT = {"bfs": "BFS", "dfs": "DFS", "bibfs": "BiBFS", "iddfs": "IDDFS", "astar": "A*", "gbfs": "GBFS",\n         "dijkstra_unit": "Dijkstra(u)", "idastar": "IDA*", "jps": "JPS", "biastar": "BiA*", "other": "other",\n         "no_code": "no code", "invalid": "invalid"}\nZ95 = 1.959963984540054\n\n\ndef wilson_ci(k: int, n: int, z: float = Z95) -> tuple[float, float]:\n    if n <= 0:\n        return (float("nan"), float("nan"))\n    p = k / n\n    den = 1 + z * z / n\n    centre = (p + z * z / (2 * n)) / den\n    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den\n    return (max(0.0, centre - half), min(1.0, centre + half))'}
```

### [162] TOOL RESULT — NotebookEdit · 2026-10-26 14:47:10 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [163] TOOL CALL — NotebookEdit · 2026-10-26 14:47:10 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "## The artifact's modules\n\nThe analysis imports three modules. Each is written to `tpg_modules/` by the cell below it and then imported, so the code you read is the code that runs.\n\n* `common.py`: the project-wide frozen protocol. The analysis needs only the canonical order of the ten algorithms, their short names and the Wilson interval, so only that excerpt (unchanged lines) is written.\n* `geometry.py` and `landing.py`: iteration 8's modules, which iteration 9 imports byte-for-byte unchanged. They are reproduced in full."}
```

### [164] TOOL RESULT — NotebookEdit · 2026-10-26 14:47:10 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [165] THINKING · 2026-10-26 14:48:04 UTC

```
Module cells are in place, and the final setup batch—title, install, imports, data loader, data load, config markdown, and config—has been inserted, with config starting at minimal resampling values.
```

### [166] TOOL CALL — NotebookEdit · 2026-10-26 14:48:04 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '# ---------------------------------------------------------------------------------------------- tunable parameters\n# Demo values; the committed values of the full run are in the comments.\nKS = (5, 10, 15)          # kNN sizes reported                                   (original: (5, 10, 15))\nK_VERDICT = 15            # k of the committed verdict                           (original: 15)\nK_SECOND = 10             # committed second verdict k                            (original: 10)\nN_BOOT_32B = 10           # paraphrase-group bootstrap resamples, 32B verdict manifolds    (original: 1000)\nN_BOOT_OTHER = 10         # bootstrap resamples of every other manifold (none in the demo) (original: 200)\nLANDING_DRAWS = 1000      # draws of each iid landing null (U, F, C)             (original: 10000)\nPERM_P_N = 1000           # permutations behind the alias-level Spearman p       (original: 100000)\nN_WORKERS = 1             # bootstrap seed chunks, run in-process here           (original: 12 worker processes)\nMANIFOLDS_DEMO = ["mname", "mcode_PRIMARY_R1"]   # in mini_demo_data.json (the full run: 6 on Qwen3-32B, 3 on Qwen3-8B)'}
```

### [167] TOOL RESULT — NotebookEdit · 2026-10-26 14:48:04 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [168] TOOL CALL — NotebookEdit · 2026-10-26 14:48:04 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': '## Configuration\n\nAll tunable parameters in one place. The kNN sizes `KS`, `K_VERDICT` and `K_SECOND` are the committed values. The resampling counts (bootstrap resamples, landing-null draws, permutations) can be set to their committed values, which are given in the comments.\n\n`N_WORKERS` only splits the bootstrap seeds into chunks. The notebook runs the chunks in-process, because a spawn-based process pool cannot import functions defined in a notebook.'}
```

### [169] TOOL RESULT — NotebookEdit · 2026-10-26 14:48:04 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [170] TOOL CALL — NotebookEdit · 2026-10-26 14:48:04 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'data = load_data()\nmeta = data["metadata"]\nprint(f"{len(data[\'examples\'])} examples from {meta[\'source_artifact\']}: {meta[\'examples_per_manifold\']}")\nfor name, rule in meta["selection"].items():\n    print(f"  {name:17s} {rule}")\nprint("vector encoding:", meta["vector_encoding"])'}
```

### [171] TOOL RESULT — NotebookEdit · 2026-10-26 14:48:04 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [172] TOOL CALL — NotebookEdit · 2026-10-26 14:48:04 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-9/experiment-46/demo/mini_demo_data.json"\nimport http.client\nimport json\nimport urllib.request\nfrom pathlib import Path\n\ndef load_data():\n    try:\n        with urllib.request.urlopen(GITHUB_DATA_URL, timeout=15) as response:\n            return json.loads(response.read().decode())\n    # Network errors, timeouts, a placeholder URL, bad JSON, a cut-off response.\n    except (OSError, ValueError, http.client.HTTPException) as e:\n        print("GitHub data unavailable, using local mini_demo_data.json:", e)\n    local = Path("mini_demo_data.json")\n    if local.exists(): return json.loads(local.read_text())\n    raise FileNotFoundError("Could not load mini_demo_data.json")'}
```

### [173] TOOL RESULT — NotebookEdit · 2026-10-26 14:48:04 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [174] TOOL CALL — NotebookEdit · 2026-10-26 14:48:04 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'from __future__ import annotations\n\n# --- import block of src/stage_analysis.py (unchanged) ---\nimport itertools\nimport multiprocessing as mp\nimport os\nimport sys\nfrom concurrent.futures import ProcessPoolExecutor\nfrom pathlib import Path\nfrom typing import Any\n\nimport numpy as np\nfrom loguru import logger\nfrom scipy.stats import mannwhitneyu, rankdata, spearmanr\n\n# --- further imports of src/stage_figures.py and audit/audit_states.py ---\nfrom collections import Counter\n\nimport matplotlib.pyplot as plt\nimport networkx as nx\nfrom scipy.sparse.csgraph import shortest_path\nfrom sklearn.neighbors import NearestNeighbors\n\n# --- added for the notebook ---\nimport base64\nimport json\nimport time\n\nlogger.remove()                                   # loguru: one plain line per message in the notebook output\nlogger.add(sys.stdout, format="{message}", level="INFO")\nMODULE_DIR = Path("tpg_modules")                  # the artifact\'s modules are written here below, then imported\nMODULE_DIR.mkdir(exist_ok=True)\nsys.path.insert(0, str(MODULE_DIR))\nT0 = time.time()'}
```

### [175] TOOL RESULT — NotebookEdit · 2026-10-26 14:48:04 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [176] TOOL CALL — NotebookEdit · 2026-10-26 14:48:04 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': "import subprocess, sys\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\n\n# loguru — NOT on Colab, always install (the artifact's modules log through it)\n_pip('loguru==0.7.3')\n\n# numpy, scipy, scikit-learn, matplotlib, networkx — pre-installed on Colab, install locally only\nif 'google.colab' not in sys.modules:\n    _pip('numpy==2.0.2', 'scipy==1.16.3', 'scikit-learn==1.6.1', 'matplotlib==3.10.0', 'networkx==3.6.1')"}
```

### [177] TOOL RESULT — NotebookEdit · 2026-10-26 14:48:04 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [178] TOOL CALL — NotebookEdit · 2026-10-26 14:48:04 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': '# Mapping grid algorithms with and without their names (TP-G, iteration 9)\n\n**Demo of artifact `art_VVA3P0ocZNA2`**: the activation geometry of ten grid path-search algorithms in Qwen3-32B (nf4). This notebook runs the artifact\'s analysis code (`method.py analyse` and `method.py figures`) on cached activations.\n\n**The question.** Asked to *"write a Python function solve(grid, start, goal) that finds a path"*, Qwen3-32B writes **BFS in 91 of 100** generations: the model\'s "average answer". When the prompt **bans its top five** (BFS, DFS, IDDFS, A\\*, greedy best-first search), the only other catalogued algorithm it writes is **unit-weight Dijkstra**, in 15 of 100 generations. The rest are other searches, invalid code, or ignore the ban. When a model is pushed off its default, does it move to a *neighbour* of what was banned, or far away? On a map of the model\'s internal representations, does unit Dijkstra sit at the **EDGE** of the banned region or on the **OPPOSITE** side?\n\nIteration 8 built that map from prompts that *name* each algorithm and found unit Dijkstra **OPPOSITE** the banned five. This artifact asks whether the map reflects what the algorithms *do* or only what they are *called*. It rebuilds the map four ways, holding the model, readout, layer rule, k and landing code fixed:\n\n| Manifold | Points | One point is ... |\n|---|---|---|\n| **M-name** | 300 | a prompt naming the algorithm ("Implement breadth-first search (BFS) for this task. ..."; 10 templates x 3 aliases) |\n| M-desc | 260 | a name-free description of the mechanism that Qwen3-32B can still name |\n| M-lex | 300 | an alias prompt minus a token-matched neutral twin (the name-only signal) |\n| **M-code** | 117 | a verified, name-scrubbed program, teacher-forced through the model |\n\n**Full-run result (pre-registered named outcome: MIXED).**\n\n* Unit Dijkstra sits OPPOSITE the banned five on every name-based manifold (M-name, M-lex, M-desc).\n* It sits at the EDGE of the program manifold M-code, and the 15 survivor programs also land at the EDGE (15/15).\n* Name-based geometry tracks how similar the names are (RSA with R_lex). Program geometry tracks behaviour (R_beh) and code surface (R_surface).\n* The geometry is correlational: it shows where representations sit, not whether the model uses them to choose.\n\n**What this notebook runs.** The GPU stages (Qwen3-32B nf4 forward passes) and the OpenRouter stages cannot run on a Colab CPU in minutes. Their output, the cached activation vectors, is loaded from `mini_demo_data.json`: **99 points from the two contrasting manifolds** (30 M-name prompts, 54 M-code programs) **plus the 15 survivor programs**. They are exactly as cached: float16, 5120-dimensional, at the committed layer L\\*. On these points the notebook reruns the original analysis code:\n\n* kNN-graph geodesics and the EDGE / OPPOSITE classes;\n* the landing test, bootstrap and split-half reliability, crossnobis and z-scored checks;\n* the alias-level lexical regression and RSA with exact Mantel tests;\n* out-of-sample placement of the survivors and the independent networkx audit;\n* PCA / MDS / Isomap figures in activation coordinates.\n\nThe last section prints the full-run numbers beside the demo numbers.'}
```

### [179] TOOL RESULT — NotebookEdit · 2026-10-26 14:48:04 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [180] ASSISTANT · 2026-10-26 14:48:16 UTC

```
All 43 cells are in. Next I'll check the cell order, then run a fast trial in a scratch copy with my pre-provisioned venv, so the workspace isn't cluttered while I iterate.
```

### [181] TOOL CALL — Bash · 2026-10-26 14:48:16 UTC

```
Check notebook cell order and stage a scratch copy:
SP=/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-VVA3P0ocZNA2/39a5c6e0-c154-4645-bb18-199862447326/scratchpad; WS=/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2; $SP/venv/bin/python - <<EOF
import json
nb = json.load(open("$WS/code_demo.ipynb"))
for i, c in enumerate(nb["cells"]):
    src = "".join(c["source"]) if isinstance(c["source"], list) else c["source"]
    first = src.strip().splitlines()[0][:100] if src.strip() else ""
    print(f"{i:2d} {c['cell_type'][:4]} {c.get('id','')[:10]:10s} {first}")
print(nb["nbformat"], nb["nbformat_minor"], nb["metadata"])
EOF
mkdir -p $SP/run1 && cp $WS/code_demo.ipynb $WS/mini_demo_data.json $SP/run1/
```

### [182] TOOL RESULT — Bash · 2026-10-26 14:48:16 UTC

```
{"stdout": " 0 mark 527b09c4   # Mapping grid algorithms with and without their names (TP-G, iteration 9)\n 1 code 8783fb09   import subprocess, sys\n 2 code 03029212   from __future__ import annotations\n 3 code d1d865b1   GITHUB_DATA_URL = \"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-b\n 4 code 1f6176e2   data = load_data()\n 5 mark 581ba56b   ## Configuration\n 6 code 6907aa27   # ---------------------------------------------------------------------------------------------- tun\n 7 mark afe43eb8   ## The artifact's modules\n 8 code 1706be8a   %%writefile tpg_modules/common.py\n 9 mark 86090bf5   ### `geometry.py` (iteration 8, imported unchanged)\n10 code bfeebbe0   %%writefile tpg_modules/geometry.py\n11 mark 281b2c24   ### `landing.py` (iteration 8, imported unchanged)\n12 code 4fc09f62   %%writefile tpg_modules/landing.py\n13 mark 6706aed2   ### Frozen protocol constants (`src/tpg.py`)\n14 code 89da0387   import geometry\n15 mark e197b92a   ## Stage 5 output: the activation states\n16 code dfdbe8e0   # ---------------------------------------------------------------------------------------------- loa\n17 mark 85cab652   ## Stage 7: the geometry of one manifold\n18 code 84f086cc   # ---------------------------------------------------------------------------------------------- geo\n19 mark 12346fad   ## Stage 8: reliability checks\n20 code 0c7fb2cd   def split_half(X: np.ndarray, labels: np.ndarray, groups: np.ndarray, k: int) -> dict[str, Any]:\n21 mark abf063f0   ## Stage 9: landing test and robustness grid\n22 code afc46c6e   def landing_all(g: dict[str, float], cls: dict[str, str]) -> dict[str, Any]:\n23 mark 4c6ba9b0   ## Stages 7-10 together: `analyse_manifold`\n24 code 0ba87e0c   BOOT_MATS: dict[str, np.ndarray] = {}     # notebook: bootstrap class matrices (original: cache/stat\n25 mark 0473dbff   ### Run it on M-name (names) and M-code (programs)\n26 code dc70f2fc   t = time.time()\n27 mark df5f63f4   ## Stage 10a: do the names drive the name-based geometry? (P4, alias level)\n28 code 8190d25b   # ---------------------------------------------------------------------------------------------- lex\n29 mark b17e0785   ## Stage 10b: representational similarity analysis\n30 code ecf1581b   # ---------------------------------------------------------------------------------------------- RSA\n31 mark 289a1a57   ## Stage 10c: where do the actual survivor programs land? (P8, out-of-sample placement)\n32 code d77f6cfc   # ---------------------------------------------------------------------------------------------- pla\n33 mark ff53f77a   ## Independent audit (`audit/audit_states.py`)\n34 code 607533b8   def knn_geodesics(X, k):\n35 mark 00713663   ## Stage 11: figures in activation coordinates\n36 code 04d72429   COL = dict(zip(CANON_ORDER, plt.cm.tab10(np.linspace(0, 1, 10))))\n37 mark c72df438   ### Per-manifold figures: M-name, then M-code\n38 code b4cb6f78   for key, r in geo_results.items():\n39 mark dee89e3e   ### Class table, RDM heatmaps, behavioural map and the alias-level lexical plot\n40 code bd651e0a   def class_table(geo_all: dict[str, Any]) -> None:\n41 mark 9c6957aa   ## Results: the demo subset against the full run\n42 code 737f7307   # ---------------------------------------------------------------------------------------------- dem\n43 mark closing-no ## Scaling back to the full run\n4 5 {'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}, 'language_info': {'name': 'python', 'version': '3.12'}}", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [183] ASSISTANT · 2026-10-26 14:48:22 UTC

```
The order is correct (44 cells). Next I'll execute the scratch copy with the minimal config and time it.
```

### [184] TOOL CALL — Bash · 2026-10-26 14:48:22 UTC

```
Execute notebook copy in scratch venv (minimal config):
SP=/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-VVA3P0ocZNA2/39a5c6e0-c154-4645-bb18-199862447326/scratchpad; cd $SP/run1 && start=$(date +%s) && $SP/venv/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb > nbconvert.log 2>&1; echo "exit $? after $(( $(date +%s) - start )) s"; tail -30 nbconvert.log
```

### [185] TOOL RESULT — Bash · 2026-10-26 14:48:40 UTC

```
{"stdout": "exit 0 after 18 s\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[IPKernelApp] WARNING | Kernel is running over TCP without encryption. All communication (including code and outputs) is sent in plain text and is susceptible to eavesdropping. Use IPC transport or launch with kernel manager-provisioned CurveZMQ keys to enable transport encryption.\n[NbConvertApp] Writing 916844 bytes to code_demo.ipynb", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [186] ASSISTANT · 2026-10-26 14:48:48 UTC

```
The first run passed in 18 s. Next I'll check every cell's text output and stderr, and diff the written modules against the artifact's originals.
```

### [187] TOOL CALL — Bash · 2026-10-26 14:48:48 UTC

```
Diff written modules and dump cell outputs:
SP=/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-VVA3P0ocZNA2/39a5c6e0-c154-4645-bb18-199862447326/scratchpad; SRC=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46; cd $SP/run1 && for f in geometry landing; do echo "== diff $f.py"; diff $SRC/src/$f.py tpg_modules/$f.py && echo IDENTICAL; done; $SP/venv/bin/python - <<'EOF'
import json
nb = json.load(open("code_demo.ipynb"))
for i, c in enumerate(nb["cells"]):
    if c["cell_type"] != "code":
        continue
    outs = c.get("outputs", [])
    texts = []
    for o in outs:
        if o["output_type"] == "stream":
            texts.append(f"[{o['name']}] " + "".join(o["text"]))
        elif o["output_type"] == "error":
            texts.append("ERROR " + o["ename"] + ": " + o["evalue"])
        elif o["output_type"] in ("display_data", "execute_result"):
            texts.append("<" + ",".join(o["data"].keys()) + ">")
    t = "\n".join(texts)
    print(f"----- cell {i} ({len(outs)} outputs)")
    print(t[:3500])
EOF
```

### [188] TOOL RESULT — Bash · 2026-10-26 14:48:48 UTC

```
{"stdout": "== diff geometry.py\nIDENTICAL\n== diff landing.py\nIDENTICAL\n----- cell 1 (0 outputs)\n\n----- cell 2 (0 outputs)\n\n----- cell 3 (0 outputs)\n\n----- cell 4 (1 outputs)\n[stdout] GitHub data unavailable, using local mini_demo_data.json: HTTP Error 404: Not Found\n99 examples from art_VVA3P0ocZNA2 (gen_art_experiment_46, invention-loop iteration 9): {'mname': 30, 'mcode_PRIMARY_R1': 54, 'placement_SURV': 15}\n  mname             templates [0] x aliases 0-2 x 10 algorithms (30 of 300 points), S-mean readout, block 31\n  mcode_PRIMARY_R1  set ranks 0-8 of every algorithm with >= 10 PRIMARY programs (54 of 117 points), R1 readout (mean over code tokens), block 33\n  placement_SURV    all 15 unit-Dijkstra survivor programs (C6 ban screen + confirm), same readout and block as the M-code frame\nvector encoding: x_f16_b64 = base64 of the cached little-endian float16 state (5120 values): np.frombuffer(base64.b64decode(s), dtype='<f2')\n\n----- cell 6 (0 outputs)\n\n----- cell 8 (1 outputs)\n[stdout] Writing tpg_modules/common.py\n\n----- cell 10 (1 outputs)\n[stdout] Writing tpg_modules/geometry.py\n\n----- cell 12 (1 outputs)\n[stdout] Writing tpg_modules/landing.py\n\n----- cell 14 (1 outputs)\n[stdout] banned: ['BFS', 'DFS', 'IDDFS', 'A*', 'GBFS'] | non-banned: ['BiBFS', 'BiA*', 'IDA*', 'JPS', 'Dijkstra(u)']\nQwen3-32B implemented, no ban (100 generations): {'invalid': 9, 'bfs': 91}\nQwen3-32B implemented, top five banned (100 generations): {'other': 28, 'invalid': 29, 'dfs': 16, 'gbfs': 6, 'dijkstra_unit': 15, 'bfs': 4, 'astar': 2}\ncorrect-when-forced rates (C null): {'bibfs': 0.125, 'dijkstra_unit': 0.275, 'idastar': 0.0, 'jps': 0.0, 'biastar': 0.0}\n\n----- cell 16 (1 outputs)\n[stdout] mname             X (30, 1, 5120) float32, block [31], paraphrase groups [0, 1, 2], points per algorithm {'bfs': 3, 'dfs': 3, 'bibfs': 3, 'iddfs': 3, 'astar': 3, 'gbfs': 3, 'dijkstra_unit': 3, 'idastar': 3, 'jps': 3, 'biastar': 3}\nmcode_PRIMARY_R1  X (54, 1, 5120) float32, block [33], paraphrase groups [0, 1, 2, 3, 4, 5, 6, 7, 8], points per algorithm {'bfs': 9, 'dfs': 9, 'astar': 9, 'gbfs': 9, 'dijkstra_unit': 9, 'idastar': 9}\n\nM-name point mname|bfs|t0|j0:\nImplement breadth-first search (BFS) for this task.\n\nTask: write a Python function solve(grid, start, goal) that finds a path between two cells of a grid. grid is a list of equal-length strings with between 1 and 30 rows and between 1 and 30 columns; the character . is a free cell and the character # is a wall. start and goal are (row, col) tuples of 0-based indices. A move goes to one of the 4 orthogonal neighbours  ...\n\nM-code point S1|forced:dijkstra_unit|2|9 (unit Dijkstra, name-scrubbed):\ndef solve(grid, start, goal):\n    rows = len(grid)\n    cols = len(grid[0]) if rows else 0\n    if start[0] < 0 or start[0] >= rows or start[1] < 0 or (start[1] >= cols) or (grid[start[0]][start[1]] == '#') or (goal[0] < 0) or (goal[0] >= rows) or (goal[1] < 0) or (goal[1] >= cols) or (grid[goal[0]][goal[1]] == '#'):\n        return []\n    if start == goal:\n        return [start]\n    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]\n    from heapq import heappush, heappop\n    pq = [(0, start, [start])]\n    visited = set()\n    while pq:\n        dist, (r, c), path = heappop(pq)\n        if (r, c) == goal:\n            return path\n        if (r, c) in visited:\n            continue\n        visited.add(\n\n----- cell 18 (0 outputs)\n\n----- cell 20 (0 outputs)\n\n----- cell 22 (0 outputs)\n\n----- cell 24 (0 outputs)\n\n----- cell 26 (3 outputs)\n[stdout] [32b mname] L*=31 k15 {'bibfs': 'EDGE', 'biastar': 'EDGE', 'idastar': 'MIDDLE', 'jps': 'OPPOSITE', 'dijkstra_unit': 'OPPOSITE'} verdict OPPOSITE | k10 OPPOSITE NEITHER\n\n[stdout] [32b mcode_PRIMARY_R1] L*=33 k15 {'idastar': 'OPPOSITE', 'dijkstra_unit': 'EDGE'} verdict EDGE | k10 EDGE EDGE\n\n[stdout] geometry: 0.7 s\n\n32b|mname: block 31, 30 points, PCA EVR(1-3) [0.403, 0.137, 0.091], MDS stress-1 points 0.36 / centroids 0.29\n  k= 5: Dijkstra(u) OPPOSITE rank 4/5  g/median 1.00  nearest banned A*    landing None  | g: BiBFS 6.5, BiA* 7.1, IDA* 9.5, JPS 12.0, Dijkstra(u) 9.5\n  k=10: Dijkstra(u) OPPOSITE rank 4/5  g/median 1.12  nearest banned A*    landing NEITHER  | g: BiBFS 6.5, BiA* 6.8, IDA* 7.7, JPS 11.4, Dijkstra(u) 8.6\n  k=15: Dijkstra(u) OPPOSITE rank 4/5  g/median 1.15  nearest banned A*    landing OPPOSITE  | g: BiBFS 6.5, BiA* 6.8, IDA* 7.4, JPS 9.3, Dijkstra(u) 8.6\n  bootstrap k=15 (n=10): P(EDGE) 0.00, class stability 1.00, g/median 95% CI [1.02, 1.19]\n  landing k=15 (15 pooled survivors): S 8.58, p_edge U 0.999 F 0.999 P 0.800 C 1.000; p_opp U 0.001 F 0.001 -> OPPOSITE\n  split-half Spearman-Brown k=15: 0.93; crossnobis OPPOSITE, z-scored OPPOSITE, Euclidean centroid OPPOSITE; robustness cells {'OPPOSITE': 3}\n\n32b|mcode_PRIMARY_R1: block 33, 54 points, PCA EVR(1-3) [0.331, 0.276, 0.063], MDS stress-1 points 0.31 / centroids 0.09\n  k= 5: Dijkstra(u) EDGE     rank 1/2  g/median 0.60  nearest banned GBFS  landing None  | g: IDA* 41.3, Dijkstra(u) 17.9\n  k=10: Dijkstra(u) EDGE     rank 1/2  g/median 0.68  nearest banned GBFS  landing EDGE  | g: IDA* 28.1, Dijkstra(u) 14.6\n  k=15: Dijkstra(u) EDGE     rank 1/2  g/median 0.69  nearest banned GBFS  landing EDGE  | g: IDA* 25.2, Dijkstra(u) 13.4\n  bootstrap k=15 (n=10): P(EDGE) 1.00, class stability 1.00, g/median 95% CI [0.62, 0.78]\n  landing k=15 (15 pooled survivors): S 13.36, p_edge U 0.000 F 0.000 P 0.500 C 0.522; p_opp U 1.000 F 1.000 -> EDGE\n  split-half Spearman-Brown k=15: 0.94; crossnobis EDGE, z-scored EDGE, Euclidean centroid EDGE; robustness cells {'EDGE': 3}\n\n----- cell 28 (1 outputs)\n[stdout] lexical regression: 0.5 s\n  bidirectional BFS                  L1 1   g_alias (k=15)   7.12\n  bidirectional breadth-first search L1 1   g_alias (k=15)   6.56\n  a breadth-first search run from both start and goal L1 1   g_alias (k=15)   5.96\n  bidirectional A* search            L1 1   g_alias (k=15)   6.25\n  bidirectional A*                   L1 1   g_alias (k=15)   6.68\n  A* run from both start and goal at once L1 1   g_alias (k=15)   7.60\n  IDA* search                        L1 1   g_alias (k=15)   6.68\n  iterative deepening A* (IDA*)      L1 2   g_alias (k=15)   8.36\n  IDA* with a Manhattan heuristic    L1 1   g_alias (k=15)   6.77\n  jump point search                  L1 0   g_alias (k=15)   8.65\n  JPS                                L1 0   g_alias (k=15)   8.54\n  jump point search (JPS) on a uniform-cost grid L1 0   g_alias (k=15)  10.67\n  unit-weight Dijkstra               L1 0   g_alias (k=15)   8.23\n  Dijkstra's algorithm with unit edge weights L1 0   g_alias (k=15)   9.31\n  a priority-queue Dijkstra search   L1 0   g_alias (k=15)   8.19\nk=10: Spearman(g_alias, L1) -0.65 (perm p 0.0040), partial given length -0.65; L3 -0.79; within-algorithm exact p (L2) 0.308 (7,776 permutations)\nk=15: Spearman(g_alias, L1) -0.65 (perm p 0.0050), partial given length -0.67; L3 -0.80; within-algorithm exact p (L2) 0.211 (7,776 permutations)\nP4 pass (<= -0.6 at both k): True\n\n----- cell 30 (3 outputs)\n[stdout] RSA 32b|mname: R_lex 0.52 (p 0.0001), R_beh 0.35 (p 0.0148), R_beh_order 0.17 (p 0.1467), R_DS 0.53 (p 0.0022), R_surface -0.11 (p 0.7287), R_len 0.25 (p 0.0546), R_desc_lex 0.56 (p 0.0001)\n\n[stdout] RSA 32b|mcode_PRIMARY_R1: R_lex 0.07 (p 0.4014), R_beh 0.83 (p 0.0028), R_beh_order 0.66 (p 0.0125), R_DS 0.67 (p 0.0111), R_surface 0.82 (p 0.0014), R_len 0.84 (p 0.0028), R_desc_lex 0.90 (p 0.0042)\n\n[stdout] RSA: 9.6 s\n\n32b|mname: 10 algorithms, noise ceiling (upper) 0.96\n  R_lex       rho +0.52   exact p 0.0001   (3,628,800 permutations)\n  R_beh       rho +0.35   exact p 0.0148   (3,628,800 permutations)\n  R_beh_order rho +0.17   exact p 0.1467   (3,628,800 permutations)\n  R_DS        rho +0.53   exact p 0.0022   (3,628,800 permutations)\n  R_surface   rho -0.11   exact p 0.7287   (3,628,800 permutations)\n  R_len       rho +0.25   exact p 0.0546   (3,628,800 permutations)\n  R_desc_lex  rho +0.56   exact p 0.0001   (3,628,800 permutations)\n  bootstrap rho(R_lex) - rho(R_beh): mean +0.16, 95% CI [0.14, 0.18] (n 10)\n  bootstrap rho(R_beh) - rho(R_lex): mean -0.16, 95% CI [-0.18, -0.14] (n 10)\n  bootstrap rho(R_surface) - rho(R_beh): mean -0.44, 95% CI [-0.57, -0.3] (n 10)\n\n32b|mcode_PRIMARY_R1: 6 algorithms, noise ceiling (upper) 0.97\n  R_lex       rho +0.07   exact p 0.4014   (720 permutations)\n  R_beh       rho +0.83   exact p 0.0028   (720 permutations)\n  R_beh_order rho +0.66   exact p 0.0125   (720 permutations)\n  R_DS        rho +0.67   exact p 0.0111   (720 permutations)\n  R_surface   rho +0.82   exact p 0.0014   (720 permutations)\n  R_len       rho +0.84   exact p 0.0028   (720 permutations)\n  R_desc_lex  rho +0.90   exact p 0.0042   (720 permutations)\n  bootstrap rho(R_lex) - rho(R_beh): mean -0.72, 95% CI [-0.8, -0.61] (n 10)\n  bootstrap rho(R_beh) - rho(R_lex): mean +0.72, 95% CI [0.61, 0.8] (n 10)\n  bootstrap rho(R_surface) - rho(R_beh): mean -0.02, 95% CI [-0.07, 0.02] (n 10)\n  partial rho(neural, R_beh | R_surface) +0.40\n\n----- cell 32 (2 outputs)\n[stdout] placement 32b|mcode_PRIMARY_R1: LOO 0.81; uDij survivors EDGE 15/15\n\n[stdout] placement: 0.2 s\nframe classes {'idastar': 'OPPOSITE', 'dijkstra_unit': 'EDGE'} (median g 19.27); leave-one-out placement accuracy 0.81 (gate 0.7: True)\nunit-Dijkstra survivor programs at the EDGE: 15/15 (Wilson 95% [0.8, 1.0]); nearest algorithm: A* 8, GBFS 5, Dijkstra(u) 2; P8 pass: True\nsurvivor g median 17.14 vs frame unit-Dijkstra programs (leave-one-out) 12.90; Mann-Whitney p 0.00104\n  C6|ban|7       nearest A*          g_x  18.43  EDGE     (nearest banned A*)\n  C6|ban|18      nearest GBFS        g_x  14.31  EDGE     (nearest banned GBFS)\n  C6|ban|31      nearest A*          g_x  17.14  EDGE     (nearest banned A*)\n  C6|ban|41      nearest A*          g_x  16.00  EDGE     (nearest banned A*)\n  C6|ban|44      nearest GBFS        g_x  17.11  EDGE     (nearest banned GBFS)\n  C6|ban|49      nearest Dijkstra(u) g_x  14.17  EDGE     (nearest banned GBFS)\n  C6|confirm|14  nearest A*          g_x  16.44  EDGE     (nearest banned A*)\n  C6|confirm|16  nearest GBFS        g_x  16.84  EDGE     (nearest banned GBFS)\n  C6|confirm|19  nearest A*          g_x  17.34  EDGE     (nearest banned A*)\n  C6|confirm|31  nearest A*          g_x  17.29  EDGE     (nearest banned A*)\n  C6|confirm|32  nearest A*          g_x  17.97  EDGE     (nearest banned A*)\n  C6|confirm|34  nearest Dijkstra(u) g_x  17.50  EDGE     (nearest banned A*)\n  C6|confirm|39  nearest A*          g_x  18.25  EDGE     (nearest banned A*)\n  C6|confirm|42  nearest GBFS        g_x  17.91  EDGE     (nearest banned GBFS)\n  C6|confirm|48  nearest GBFS        g_x  14.37  EDGE     (nearest banned GBFS)\n\n----- cell 34 (3 outputs)\n[stdout] 32b|mname classes equal True max |dg| 6.661338147750939e-14 placebo 0.3\n\n[stdout] 32b|mcode_PRIMARY_R1 classes equal True max |dg| 1.1901590823981678e-13 placebo 0.5\n\n[stdout] mismatches: []\n\n----- cell 36 (0 outputs)\n\n----- cell 38 (6 outputs)\n<image/png,text/plain>\n<image/png,text/plain>\n<image/png,text/plain>\n<image/png,text/plain>\n<image/png,text/plain>\n<image/png,text/plain>\n----- cell 40 (4 outputs)\n<image/png,text/plain>\n<image/png,text/plain>\n<image/png,text/plain>\n<image/png,text/plain>\n----- cell 42 (2 outputs)\n[stdout] Where does unit-weight Dijkstra sit relative to the banned five?\ndemo = this notebook on the 99-point subset; full = the artifact's run on all points (300 M-name, 117 M-code)\n\nmanifold               k | class: demo      full | rank: demo  full | g/median: demo  full | nearest banned: demo   full\n32b|mname              5 |    OPPOSITE    MIDDLE |        4/5   3/5 |           1.00  1.00 |                   A*  IDDFS\n32b|mname             10 |    OPPOSITE  OPPOSITE |        4/5   5/5 |           1.12  1.78 |                   A*  IDDFS\n32b|mname             15 |    OPPOSITE  OPPOSITE |        4/5   5/5 |           1.15  1.63 |                   A*     A*\n32b|mcode_PRIMARY_R1   5 |        EDGE      EDGE |        1/2   1/2 |           0.60  0.73 |                 GBFS   GBFS\n32b|mcode_PRIMARY_R1  10 |        EDGE      EDGE |        1/2   1/2 |           0.68  0.64 |                 GBFS   GBFS\n32b|mcode_PRIMARY_R1  15 |        EDGE      EDGE |        1/2   1/2 |           0.69  0.67 |                 GBFS   GBFS\n\nLanding verdict (15 pooled survivors) and stability, k = 15\n  32b|mname             landing demo OPPOSITE full OPPOSITE | bootstrap P(EDGE) demo 0.00 (n=10) full 0.00 (n=1000) | split-half S-B demo 0.93 full 0.99\n  32b|mcode_PRIMARY_R1  landing demo EDGE     full EDGE     | bootstrap P(EDGE) demo 1.00 (n=10) full 1.00 (n=1000) | split-half S-B demo 0.94 full 0.99\n\nRSA: Spearman rho of the class-geodesic RDM with each model RDM (exact Mantel p)\n  32b|mname             R_lex demo +0.52 (p 0.000) full +0.46 (p 0.003) | R_beh demo +0.35 (p 0.015) full +0.24 (p 0.091) | R_surface demo -0.11 (p 0.729) full +0.20 (p 0.128)\n  32b|mcode_PRIMARY_R1  R_lex demo +0.07 (p 0.401) full +0.29 (p 0.164) | R_beh demo +0.83 (p 0.003) full +0.64 (p 0.018) | R_surface demo +0.82 (p 0.001) full +0.67 (p 0.010)\n\nP4, M-name alias level, Spearman(g_alias, L1): demo k10 -0.65, k15 -0.65 (pass True) | full k10 -0.74, k15 -0.65 (pass True)\nP8, survivor programs placed at the EDGE of M-code: demo 15/15 (LOO accuracy 0.81) | full 15/15 (LOO accuracy 0.85)\n\nFull run, k = 15 class of unit Dijkstra on every manifold analysed: 32b|mname OPPOSITE, 32b|mlex OPPOSITE, 32b|mdesc OPPOSITE, 32b|mcode_PRIMARY_R1 EDGE, 32b|mcode_M32_R1 EDGE, 32b|mcode_PRIMARY_R2 EDGE, 8b|mname OPPOSITE, 8b|mdesc OPPOSITE, 8b|mcode_PRIMARY_R1 EDGE\nFull-run named outcome: MIXED (M-code EDGE, M-desc OPPOSITE); predictions {'P1': False, 'P2': False, 'P3': True, 'P4': True, 'P5': None, 'P6': True, 'P7': None, 'P8': True}\n\nNotebook run time so far: 13 s\n\n<image/png,text/plain>", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [189] THINKING · 2026-10-26 14:49:00 UTC

```
The run checks out — files match originals exactly and the audit shows no mismatches, with the demo reproducing the expected headline results (M-name OPPOSITE, M-code EDGE, RSA alignment pattern, P4 passing). Next I'll extract and review the figures.
```

### [190] TOOL CALL — Bash · 2026-10-26 14:49:00 UTC

```
Extract figure PNGs from executed notebook:
SP=/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-VVA3P0ocZNA2/39a5c6e0-c154-4645-bb18-199862447326/scratchpad; mkdir -p $SP/figs1 && cd $SP/run1 && $SP/venv/bin/python - <<EOF
import json, base64
nb = json.load(open("code_demo.ipynb"))
n = 0
for i, c in enumerate(nb["cells"]):
    for j, o in enumerate(c.get("outputs", [])):
        if o["output_type"] == "display_data" and "image/png" in o["data"]:
            p = f"$SP/figs1/cell{i:02d}_{j}.png"
            open(p, "wb").write(base64.b64decode(o["data"]["image/png"]))
            n += 1
print(n, "figures")
EOF
ls -la $SP/figs1
```

### [191] TOOL RESULT — Bash · 2026-10-26 14:49:00 UTC

```
{"stdout": "11 figures\ntotal 596\ndrwxrwxrwx 2 aii-agent aii-agent   4096 Oct 26 14:48 .\ndrwx------ 6 aii-agent aii-agent    144 Oct 26 14:48 ..\n-rw-rw-rw- 1 aii-agent aii-agent  72608 Oct 26 14:48 cell38_0.png\n-rw-rw-rw- 1 aii-agent aii-agent  53437 Oct 26 14:48 cell38_1.png\n-rw-rw-rw- 1 aii-agent aii-agent  43093 Oct 26 14:48 cell38_2.png\n-rw-rw-rw- 1 aii-agent aii-agent  66112 Oct 26 14:48 cell38_3.png\n-rw-rw-rw- 1 aii-agent aii-agent  49807 Oct 26 14:48 cell38_4.png\n-rw-rw-rw- 1 aii-agent aii-agent  39681 Oct 26 14:48 cell38_5.png\n-rw-rw-rw- 1 aii-agent aii-agent  21561 Oct 26 14:48 cell40_0.png\n-rw-rw-rw- 1 aii-agent aii-agent  43983 Oct 26 14:48 cell40_1.png\n-rw-rw-rw- 1 aii-agent aii-agent  36782 Oct 26 14:48 cell40_2.png\n-rw-rw-rw- 1 aii-agent aii-agent  41629 Oct 26 14:48 cell40_3.png\n-rw-rw-rw- 1 aii-agent aii-agent 111877 Oct 26 14:48 cell42_1.png", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [192] TOOL CALL — Read · 2026-10-26 14:49:08 UTC

```
/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-VVA3P0ocZNA2/39a5c6e0-c154-4645-bb18-199862447326/scratchpad/figs1/cell42_1.png
```

### [193] TOOL RESULT — Read · 2026-10-26 14:49:09 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [194] TOOL CALL — Read · 2026-10-26 14:49:08 UTC

```
/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-VVA3P0ocZNA2/39a5c6e0-c154-4645-bb18-199862447326/scratchpad/figs1/cell38_3.png
```

### [195] TOOL RESULT — Read · 2026-10-26 14:49:09 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [196] TOOL CALL — Read · 2026-10-26 14:49:08 UTC

```
/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-VVA3P0ocZNA2/39a5c6e0-c154-4645-bb18-199862447326/scratchpad/figs1/cell38_0.png
```

### [197] TOOL RESULT — Read · 2026-10-26 14:49:09 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [198] THINKING · 2026-10-26 14:49:20 UTC

```
The final figures and PCA panels render correctly, with the survivor cluster appearing near the A*/GBFS/unit-Dijkstra region on M-code. Next I'll check the class table, RDM heatmaps, and lexical plot.
```

### [199] TOOL CALL — Read · 2026-10-26 14:49:20 UTC

```
/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-VVA3P0ocZNA2/39a5c6e0-c154-4645-bb18-199862447326/scratchpad/figs1/cell40_1.png
```

### [200] TOOL RESULT — Read · 2026-10-26 14:49:21 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [201] TOOL CALL — Read · 2026-10-26 14:49:20 UTC

```
/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-VVA3P0ocZNA2/39a5c6e0-c154-4645-bb18-199862447326/scratchpad/figs1/cell40_0.png
```

### [202] TOOL RESULT — Read · 2026-10-26 14:49:20 UTC

```
{"type": "image", "file": {"base64": "iVBORw0KGgoAAAANSUhEUgAAA2wAAAEGCAYAAAAZnBZEAAAAOnRFWHRTb2Z0d2FyZQBNYXRwbG90bGliIHZlcnNpb24zLjEwLjAsIGh0dHBzOi8vbWF0cGxvdGxpYi5vcmcvlHJYcgAAAAlwSFlzAAAPYQAAD2EBqD+naQAAU6VJREFUeJzt3Xd8FMX/x/HXXXpIBQIBEhIwMZSEJr1X6YqKUkTAgiKiYAFBRUFRUb82BMUCIgoIKiigAtLBrhCkSBEIPaGlh9Tb3x/5ZeVIRyAHvJ+Pxz3gdmZnZzdze/fZmZ21GIZhICIiIiIiIg7HWtYVEBERERERkYIpYBMREREREXFQCthEREREREQclAI2ERERERERB6WATURERERExEEpYBMREREREXFQCthEREREREQclAI2ERERERERB6WATURERERExEEpYBM... [truncated, 28956 chars total]
```

### [203] TOOL CALL — Read · 2026-10-26 14:49:20 UTC

```
/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-VVA3P0ocZNA2/39a5c6e0-c154-4645-bb18-199862447326/scratchpad/figs1/cell40_3.png
```

### [204] TOOL RESULT — Read · 2026-10-26 14:49:21 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [205] THINKING · 2026-10-26 14:49:44 UTC

```
Figures match the original style and TODO 4 is complete, with the minimal config running cleanly in 18s. Now I'll tackle TODO 5 by timing two scaled resampling rounds on scratch copies—first at 10× parameters, then at full committed values.
```

### [206] TOOL CALL — Bash · 2026-10-26 14:49:44 UTC

```
Scaling round 1: run with 10x resampling:
SP=/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-VVA3P0ocZNA2/39a5c6e0-c154-4645-bb18-199862447326/scratchpad; WS=/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2
cat > $SP/set_config.py <<'EOF'
import json, re, sys
src, dst = sys.argv[1], sys.argv[2]
vals = dict(kv.split("=") for kv in sys.argv[3:])
nb = json.load(open(src))
for c in nb["cells"]:
    s = "".join(c["source"]) if isinstance(c["source"], list) else c["source"]
    if c["cell_type"] == "code" and "tunable parameters" in s:
        for k, v in vals.items():
            s, n = re.subn(rf"^{k} = \S+", f"{k} = {v}", s, flags=re.M)
            assert n == 1, k
        c["source"] = s
json.dump(nb, open(dst, "w"), indent=1)
EOF
for r in r10 rfull; do mkdir -p $SP/$r && cp $WS/mini_demo_data.json $SP/$r/; done
$SP/venv/bin/python $SP/set_config.py $WS/code_demo.ipynb $SP/r10/code_demo.ipynb N_BOOT_32B=100 N_BOOT_OTHER=20 LANDING_DRAWS=10000 PERM_P_N=10000
cd $SP/r10 && start=$(date +%s) && $SP/venv/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb > nbconvert.log 2>&1; echo "r10 exit $? after $(( $(date +%s) - start )) s"
$SP/venv/bin/python - <<'EOF'
import json
nb = json.load(open("code_demo.ipynb"))
for i in (26, 30, 42):
    for o in nb["cells"][i].get("outputs", []):
        if o["output_type"] == "stream":
            t = "".join(o["text"])
            for line in t.splitlines():
                if any(s in line for s in ("geometry:", "RSA:", "bootstrap", "run time", "placement:", "32b|mname  ", "32b|mcode_PRIMARY_R1  ")):
                    print(f"[cell {i}] {line}")
EOF
```

### [207] TOOL RESULT — Bash · 2026-10-26 14:50:00 UTC

```
{"stdout": "r10 exit 0 after 19 s\n[cell 26] geometry: 2.6 s\n[cell 26]   bootstrap k=15 (n=100): P(EDGE) 0.00, class stability 1.00, g/median 95% CI [1.06, 1.2]\n[cell 26]   bootstrap k=15 (n=100): P(EDGE) 1.00, class stability 1.00, g/median 95% CI [0.61, 0.76]\n[cell 30] RSA: 9.7 s\n[cell 30]   bootstrap rho(R_lex) - rho(R_beh): mean +0.15, 95% CI [0.11, 0.18] (n 100)\n[cell 30]   bootstrap rho(R_beh) - rho(R_lex): mean -0.15, 95% CI [-0.18, -0.11] (n 100)\n[cell 30]   bootstrap rho(R_surface) - rho(R_beh): mean -0.42, 95% CI [-0.53, -0.3] (n 100)\n[cell 30]   bootstrap rho(R_lex) - rho(R_beh): mean -0.75, 95% CI [-0.88, -0.62] (n 100)\n[cell 30]   bootstrap rho(R_beh) - rho(R_lex): mean +0.75, 95% CI [0.62, 0.88] (n 100)\n[cell 30]   bootstrap rho(R_surface) - rho(R_beh): mean -0.02, 95% CI [-0.08, 0.02] (n 100)\n[cell 42] 32b|mname              5 |    OPPOSITE    MIDDLE |        4/5   3/5 |           1.00  1.00 |                   A*  IDDFS\n[cell 42] 32b|mname             10 |    OPPOSITE  OPPOSITE |        4/5   5/5 |           1.12  1.78 |                   A*  IDDFS\n[cell 42] 32b|mname             15 |    OPPOSITE  OPPOSITE |        4/5   5/5 |           1.15  1.63 |                   A*     A*\n[cell 42] 32b|mcode_PRIMARY_R1   5 |        EDGE      EDGE |        1/2   1/2 |           0.60  0.73 |                 GBFS   GBFS\n[cell 42] 32b|mcode_PRIMARY_R1  10 |        EDGE      EDGE |        1/2   1/2 |           0.68  0.64 |                 GBFS   GBFS\n[cell 42] 32b|mcode_PRIMARY_R1  15 |        EDGE      EDGE |        1/2   1/2 |           0.69  0.67 |                 GBFS   GBFS\n[cell 42]   32b|mname             landing demo OPPOSITE full OPPOSITE | bootstrap P(EDGE) demo 0.00 (n=100) full 0.00 (n=1000) | split-half S-B demo 0.93 full 0.99\n[cell 42]   32b|mcode_PRIMARY_R1  landing demo EDGE     full EDGE     | bootstrap P(EDGE) demo 1.00 (n=100) full 1.00 (n=1000) | split-half S-B demo 0.94 full 0.99\n[cell 42] RSA: Spearman rho of the class-geodesic RDM with each model RDM (exact Mantel p)\n[cell 42]   32b|mname             R_lex demo +0.52 (p 0.000) full +0.46 (p 0.003) | R_beh demo +0.35 (p 0.015) full +0.24 (p 0.091) | R_surface demo -0.11 (p 0.729) full +0.20 (p 0.128)\n[cell 42]   32b|mcode_PRIMARY_R1  R_lex demo +0.07 (p 0.401) full +0.29 (p 0.164) | R_beh demo +0.83 (p 0.003) full +0.64 (p 0.018) | R_surface demo +0.82 (p 0.001) full +0.67 (p 0.010)\n[cell 42] Notebook run time so far: 15 s", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [208] THINKING · 2026-10-26 14:50:12 UTC

```
Round 1 (10×) ran in 19 s, with the geometry cell rising from 0.7 to 2.6 s — extrapolating linearly, the full 1000 resamples should take ~25 s, well inside the 600 s budget. I'll now run round 2 using all original values.
```

### [209] TOOL CALL — Bash · 2026-10-26 14:50:12 UTC

```
Scaling round 2: run with committed resampling values:
SP=/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-VVA3P0ocZNA2/39a5c6e0-c154-4645-bb18-199862447326/scratchpad; WS=/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2
$SP/venv/bin/python $SP/set_config.py $WS/code_demo.ipynb $SP/rfull/code_demo.ipynb N_BOOT_32B=1000 N_BOOT_OTHER=200 LANDING_DRAWS=10000 PERM_P_N=100000
cd $SP/rfull && start=$(date +%s) && $SP/venv/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb > nbconvert.log 2>&1; echo "rfull exit $? after $(( $(date +%s) - start )) s"
$SP/venv/bin/python - <<'EOF'
import json
nb = json.load(open("code_demo.ipynb"))
for i in (26, 28, 30, 32, 42):
    for o in nb["cells"][i].get("outputs", []):
        if o["output_type"] == "stream":
            t = "".join(o["text"])
            for line in t.splitlines():
                if any(s in line for s in ("geometry:", "RSA:", "bootstrap", "run time", "placement:", "lexical regression:", "landing k=15", "k=10: Spearman", "k=15: Spearman", "  32b|mname  ", "  32b|mcode_PRIMARY_R1  ", "P8,", "P4,")):
                    print(f"[cell {i}] {line}")
EOF
```

### [210] TOOL RESULT — Bash · 2026-10-26 14:50:48 UTC

```
{"stdout": "rfull exit 0 after 39 s\n[cell 26] geometry: 20.3 s\n[cell 26]   bootstrap k=15 (n=1000): P(EDGE) 0.00, class stability 1.00, g/median 95% CI [1.02, 1.2]\n[cell 26]   landing k=15 (15 pooled survivors): S 8.58, p_edge U 0.999 F 0.999 P 0.800 C 1.000; p_opp U 0.001 F 0.001 -> OPPOSITE\n[cell 26]   bootstrap k=15 (n=1000): P(EDGE) 1.00, class stability 1.00, g/median 95% CI [0.61, 0.75]\n[cell 26]   landing k=15 (15 pooled survivors): S 13.36, p_edge U 0.000 F 0.000 P 0.500 C 0.525; p_opp U 1.000 F 1.000 -> EDGE\n[cell 28] lexical regression: 0.6 s\n[cell 28] k=10: Spearman(g_alias, L1) -0.65 (perm p 0.0054), partial given length -0.65; L3 -0.79; within-algorithm exact p (L2) 0.308 (7,776 permutations)\n[cell 28] k=15: Spearman(g_alias, L1) -0.65 (perm p 0.0053), partial given length -0.67; L3 -0.80; within-algorithm exact p (L2) 0.211 (7,776 permutations)\n[cell 30] RSA: 11.4 s\n[cell 30]   bootstrap rho(R_lex) - rho(R_beh): mean +0.15, 95% CI [0.11, 0.18] (n 1000)\n[cell 30]   bootstrap rho(R_beh) - rho(R_lex): mean -0.15, 95% CI [-0.18, -0.11] (n 1000)\n[cell 30]   bootstrap rho(R_surface) - rho(R_beh): mean -0.43, 95% CI [-0.57, -0.3] (n 1000)\n[cell 30]   bootstrap rho(R_lex) - rho(R_beh): mean -0.76, 95% CI [-0.91, -0.61] (n 1000)\n[cell 30]   bootstrap rho(R_beh) - rho(R_lex): mean +0.76, 95% CI [0.61, 0.91] (n 1000)\n[cell 30]   bootstrap rho(R_surface) - rho(R_beh): mean -0.03, 95% CI [-0.09, 0.01] (n 1000)\n[cell 32] placement: 0.2 s\n[cell 42]   32b|mname             landing demo OPPOSITE full OPPOSITE | bootstrap P(EDGE) demo 0.00 (n=1000) full 0.00 (n=1000) | split-half S-B demo 0.93 full 0.99\n[cell 42]   32b|mcode_PRIMARY_R1  landing demo EDGE     full EDGE     | bootstrap P(EDGE) demo 1.00 (n=1000) full 1.00 (n=1000) | split-half S-B demo 0.94 full 0.99\n[cell 42] RSA: Spearman rho of the class-geodesic RDM with each model RDM (exact Mantel p)\n[cell 42]   32b|mname             R_lex demo +0.52 (p 0.000) full +0.46 (p 0.003) | R_beh demo +0.35 (p 0.015) full +0.24 (p 0.091) | R_surface demo -0.11 (p 0.729) full +0.20 (p 0.128)\n[cell 42]   32b|mcode_PRIMARY_R1  R_lex demo +0.07 (p 0.401) full +0.29 (p 0.164) | R_beh demo +0.83 (p 0.003) full +0.64 (p 0.018) | R_surface demo +0.82 (p 0.001) full +0.67 (p 0.010)\n[cell 42] P4, M-name alias level, Spearman(g_alias, L1): demo k10 -0.65, k15 -0.65 (pass True) | full k10 -0.74, k15 -0.65 (pass True)\n[cell 42] P8, survivor programs placed at the EDGE of M-code: demo 15/15 (LOO accuracy 0.81) | full 15/15 (LOO accuracy 0.85)\n[cell 42] Notebook run time so far: 35 s", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [211] THINKING · 2026-10-26 14:51:44 UTC

```
Runtime checks out at 39s with original parameters, well under the 540s limit, so I'll keep them as-is per TODO 5. I'll update the config cell and its markdown, and add survivors' nearest-algorithm counts (demo vs full) to the results to highlight the one visible difference.
```

### [212] TOOL CALL — NotebookEdit · 2026-10-26 14:51:44 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'cell_id': '6907aa27', 'edit_mode': 'replace', 'new_source': '# ---------------------------------------------------------------------------------------------- tunable parameters\n# All at the committed values of the full run; on the 99 demo points the analysis takes well under a minute.\n# Smallest values that still run (quick check): N_BOOT_32B = N_BOOT_OTHER = 10, LANDING_DRAWS = 1000, PERM_P_N = 1000.\nKS = (5, 10, 15)          # kNN sizes reported                                   (original: (5, 10, 15))\nK_VERDICT = 15            # k of the committed verdict                           (original: 15)\nK_SECOND = 10             # committed second verdict k                            (original: 10)\nN_BOOT_32B = 1000         # paraphrase-group bootstrap resamples, 32B verdict manifolds    (original: 1000)\nN_BOOT_OTHER = 200        # bootstrap resamples of every other manifold (none in the demo) (original: 200)\nLANDING_DRAWS = 10000     # draws of each iid landing null (U, F, C)             (original: 10000)\nPERM_P_N = 100000         # permutations behind the alias-level Spearman p       (original: 100000)\nN_WORKERS = 1             # bootstrap seed chunks, run in-process here           (original: 12 worker processes)\nMANIFOLDS_DEMO = ["mname", "mcode_PRIMARY_R1"]   # in mini_demo_data.json (the full run: 6 on Qwen3-32B, 3 on Qwen3-8B)'}
```

### [213] TOOL RESULT — NotebookEdit · 2026-10-26 14:51:45 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [214] TOOL CALL — NotebookEdit · 2026-10-26 14:51:45 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'cell_id': '581ba56b', 'edit_mode': 'replace', 'new_source': '## Configuration\n\nAll tunable parameters in one place, set to the **committed values of the full run**: k = 5, 10 and 15; 1,000 bootstrap resamples; 10,000 draws per landing null; 100,000 permutations for the lexical p-values. On the 99 demo points the whole analysis takes about 40 seconds on a 2-core CPU. What is reduced is the *data*: 99 of the 1,000+ cached states (see `mini_demo_data.json`).\n\n`N_WORKERS` only splits the bootstrap seeds into chunks. The notebook runs the chunks in-process, because a spawn-based process pool cannot import functions defined in a notebook.'}
```

### [215] TOOL RESULT — NotebookEdit · 2026-10-26 14:51:45 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [216] TOOL CALL — NotebookEdit · 2026-10-26 14:51:45 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'cell_id': '737f7307', 'edit_mode': 'replace', 'new_source': '# ---------------------------------------------------------------------------------------------- demo vs full run\nref = meta["full_run_reference"]\nKEYS = ["32b|mname", "32b|mcode_PRIMARY_R1"]\nprint("Where does unit-weight Dijkstra sit relative to the banned five?")\nprint("demo = this notebook on the 99-point subset; full = the artifact\'s run on all points (300 M-name, 117 M-code)\\n")\nprint(f"{\'manifold\':21s}{\'k\':>3s} | {\'class: demo\':>11s} {\'full\':>9s} | {\'rank: demo\':>10s} {\'full\':>5s} | "\n      f"{\'g/median: demo\':>14s} {\'full\':>5s} | {\'nearest banned: demo\':>20s} {\'full\':>6s}")\nfor key in KEYS:\n    sd, sf = geo_results[key]["summary"], ref["geometry"][key]["summary"]\n    n_nb = len(geo_results[key]["L_star"]["describe"]["nonbanned_used"])\n    for k in KS:\n        a, b = sd[f"k{k}"], sf[f"k{k}"]\n        print(f"{key:21s}{k:3d} | {a[\'udij_class\']:>11s} {b[\'udij_class\']:>9s} | {a[\'udij_rank\']:>8d}/{n_nb} "\n              f"{b[\'udij_rank\']:>3d}/{n_nb} | {a[\'udij_ratio\']:14.2f} {b[\'udij_ratio\']:5.2f} | "\n              f"{SHORT[a[\'udij_nearest_banned\']]:>20s} {SHORT[b[\'udij_nearest_banned\']]:>6s}")\n\nprint(f"\\nLanding verdict (15 pooled survivors) and stability, k = {K_VERDICT}")\nfor key in KEYS:\n    r, f = geo_results[key]["L_star"], ref["geometry"][key]\n    bd, bf = r["bootstrap"][f"k{K_VERDICT}"], f["bootstrap_k15"]\n    print(f"  {key:21s} landing demo {r[\'landing\'][f\'k{K_VERDICT}\'][\'pooled\'][\'verdict\']:8s} full "\n          f"{f[\'landing_pooled_verdict\'][\'k15\']:8s} | bootstrap P(EDGE) demo {bd[\'edge_probability\'][UDIJ]:.2f} "\n          f"(n={bd[\'n_boot\']}) full {bf[\'edge_probability\'][UDIJ]:.2f} (n={bf[\'n_boot\']}) | split-half S-B demo "\n          f"{r[\'split_half\'][f\'k{K_VERDICT}\'][\'spearman_brown\']:.2f} full {f[\'split_half_spearman_brown_k15\']:.2f}")\n\nprint("\\nRSA: Spearman rho of the class-geodesic RDM with each model RDM (exact Mantel p)")\nfor key in KEYS:\n    parts = []\n    for mn in ("R_lex", "R_beh", "R_surface"):\n        d, f = rsa_results[key]["models"][mn], ref["rsa"][key][mn]\n        parts.append(f"{mn} demo {d[\'rho\']:+.2f} (p {d[\'p_exact\']:.3f}) full {f[\'rho\']:+.2f} (p {f[\'p_exact\']:.3f})")\n    print(f"  {key:21s} " + " | ".join(parts))\n\nlx_d, lx_f = lex_results["32b|mname"], ref["lexical_regression"]["32b|mname"]\nprint(f"\\nP4, M-name alias level, Spearman(g_alias, L1): demo k10 {lx_d[\'k10\'][\'spearman_L1\']:+.2f}, k15 "\n      f"{lx_d[\'k15\'][\'spearman_L1\']:+.2f} (pass {lx_d[\'P4_pass\']}) | full k10 {lx_f[\'k10\'][\'spearman_L1\']:+.2f}, k15 "\n      f"{lx_f[\'k15\'][\'spearman_L1\']:+.2f} (pass {lx_f[\'P4_pass\']})")\npl_d, pl_f = placement_results["32b|mcode_PRIMARY_R1"], ref["placement"]["32b|mcode_PRIMARY_R1"]\nprint(f"P8, survivor programs placed at the EDGE of M-code: demo {pl_d[\'udij_survivors\'][\'n_edge\']}/"\n      f"{pl_d[\'udij_survivors\'][\'n\']} (LOO accuracy {pl_d[\'G_place\'][\'loo_accuracy\']:.2f}) | full "\n      f"{pl_f[\'udij_survivors\'][\'n_edge\']}/{pl_f[\'udij_survivors\'][\'n\']} (LOO accuracy {pl_f[\'G_place\'][\'loo_accuracy\']:.2f})")\nprint("    their nearest algorithm: demo " + ", ".join(\n    f"{SHORT[a]} {c}" for a, c in pl_d["udij_survivors"]["nearest_algorithm_counts"].items() if c) + " | full " + ", ".join(\n    f"{SHORT[a]} {c}" for a, c in pl_f["udij_survivors"]["nearest_algorithm_counts"].items() if c))\n\nn4 = ref["n4_verdict"]\nprint("\\nFull run, k = 15 class of unit Dijkstra on every manifold analysed: " + ", ".join(\n    f"{k} {v[\'k15\'][\'udij_class\']}" for k, v in n4["verdict_table"].items() if v["k15"]["udij_class"]))\nprint(f"Full-run named outcome: {n4[\'named_outcome\']} (M-code {n4[\'mcode_class_k15\']}, M-desc {n4[\'mdesc_class_k15\']}); "\n      f"predictions {n4[\'predictions_pass\']}")\nprint(f"\\nNotebook run time so far: {time.time() - T0:.0f} s")\n\n# ---------------------------------------------------------------------------------------------- one picture\nfig, axes = plt.subplots(1, 2, figsize=(16, 7))\nfor ax, key in zip(axes, KEYS):\n    m_tag, name = key.split("|")\n    z = COORDS[f"{m_tag}_{name}"]\n    Y, labels = z["iso"], z["labels"]\n    kd = geo_results[key]["L_star"]["describe"][f"k{K_VERDICT}"]\n    for a in [a for a in CANON_ORDER if a in set(labels.tolist())]:\n        s = labels == a\n        ax.scatter(Y[s, 0], Y[s, 1], s=80 if a == UDIJ else 35, color=COL[a], alpha=0.9, label=SHORT[a],\n                   edgecolors="red" if a in B5 else ("black" if a == UDIJ else "none"), linewidths=1.2)\n    # geodesic from unit Dijkstra to its nearest banned algorithm, traced on the kNN graph (as in figure (c))\n    nb = kd["nearest_banned"][UDIJ]\n    iu, ib = np.where(labels == UDIJ)[0], np.where(labels == nb)[0]\n    i, j = np.unravel_index(np.argmin(z["geo"][np.ix_(iu, ib)]), (len(iu), len(ib)))\n    _, pred = shortest_path(FROZEN[f"geo_{m_tag}_{name}_k{K_VERDICT}"]["adjacency"], method="D", directed=False,\n                            indices=[iu[i]], return_predecessors=True)\n    path, cur = [], ib[j]\n    while cur >= 0 and cur != iu[i]:\n        path.append(cur)\n        cur = pred[0, cur]\n    path.append(iu[i])\n    ax.plot(Y[path, 0], Y[path, 1], "k--", lw=1.2, label=f"geodesic {SHORT[UDIJ]} -> {SHORT[nb]}")\n    if name.startswith("mcode"):\n        # the 15 survivor programs, embedded out of sample by the fitted Isomap\n        sel = [e for e in data["examples"] if e["manifold"] == "placement_SURV"]\n        Q = np.stack([np.frombuffer(base64.b64decode(e["x_f16_b64"]), dtype="<f2") for e in sel]).astype(np.float64)\n        Yq = z["isomap_model"].transform(Q)\n        ax.scatter(Yq[:, 0], Yq[:, 1], marker="x", s=60, color="black", label=f"{len(sel)} survivor programs")\n    ax.set_title(f"{TITLES[name]}, block {z[\'block\']}\\nunit Dijkstra is {kd[\'classes\'][UDIJ]}: "\n                 f"g/median {kd[\'udij_ratio\']:.2f}, rank {kd[\'udij_rank\']}/{len(kd[\'g\'])} (Isomap k={K_VERDICT})",\n                 fontsize=10)\n    ax.set_xlabel("Isomap 1")\n    ax.set_ylabel("Isomap 2")\n    ax.legend(fontsize=7, ncol=2, loc="best")\nfig.suptitle("Qwen3-32B: the algorithm written when the top five are banned (unit Dijkstra, black outline) sits "\n             "OPPOSITE the banned five (red outline) on the map of names,\\nbut at their EDGE on the map of programs, "\n             "where the actual survivor programs (x) also land", fontsize=11)\nplt.tight_layout()\nplt.show()'}
```

### [217] TOOL RESULT — NotebookEdit · 2026-10-26 14:51:45 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [218] TOOL CALL — NotebookEdit · 2026-10-26 14:51:45 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'cell_id': '9c6957aa', 'edit_mode': 'replace', 'new_source': "## Results: the demo subset against the full run\n\nThe table below puts every headline number computed above next to the artifact's full-run value: all 300 M-name prompts, all 117 M-code programs, and the same resampling counts. Those values are read from `metadata.full_run_reference` in the demo data.\n\nThe figure shows both manifolds side by side in Isomap coordinates: the same model, the same algorithm (unit Dijkstra, black outline) and the same banned five (red outline).\n\n* On the map of **names**, unit Dijkstra sits OPPOSITE the banned five.\n* On the map of **programs**, it sits at their EDGE. The 15 programs Qwen3-32B actually wrote under the ban (crosses, embedded out of sample) land there too.\n\nHow far the demo subset can be trusted:\n\n* **What reproduces.** The classes, the pooled landing verdicts at k = 15, the RSA ordering (M-name: R_lex above R_beh; M-code: R_beh and R_surface far above R_lex), P4 and P8 all match the full run.\n* **What differs in size.** The M-name subset has only 3 prompts per algorithm, so its g / median ratios are smaller (1.1 vs 1.6) and its k = 10 landing verdict is NEITHER rather than OPPOSITE.\n* **Placement nearest neighbour.** The M-code frame here has 9 rather than 20 programs per algorithm. So each survivor's single nearest algorithm is mostly A\\* or GBFS instead of unit Dijkstra (13 of 15 in the full run), although all 15 still land on the EDGE side."}
```

### [219] TOOL RESULT — NotebookEdit · 2026-10-26 14:51:45 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [220] TOOL CALL — NotebookEdit · 2026-10-26 14:51:45 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/code_demo.ipynb', 'cell_id': 'closing-notes', 'edit_mode': 'replace', 'new_source': "## Scaling back to the full run\n\n* **Parameters.** The config cell already holds the committed values (k = 5 / 10 / 15, 1,000 bootstrap resamples, 10,000 landing-null draws, 100,000 permutations). For a quick check they can be lowered to `N_BOOT_32B = N_BOOT_OTHER = 10`, `LANDING_DRAWS = PERM_P_N = 1000`.\n* **Data.** The full analysis uses all 300 M-name, 260 M-desc, 300 M-lex and 117 M-code states at every block from 17 to 47 (`cache/states/`, about 0.5 GB of float16 arrays), plus the Qwen3-8B states. These files stay on the run's storage volume and are not in the published repository. The artifact's GPU stages rebuild them: `method.py mname 32b`, `method.py states 32b mlex ban` and `method.py states 32b mdesc mcode`, about 30 GPU-minutes on one RTX 5090. Then run `method.py blocks`, `method.py analyse`, `method.py figures` and `method.py outputs`.\n* **What changes with the data.** Several parts need those states: layer selection (`blocks`), the reference-block section, the 5-block robustness grid, name evocation, and the Qwen3-8B / M-desc / M-lex manifolds. Every function in this notebook runs on the states unchanged once `load_manifold` reads the `.npz` files again (the original `load_manifold` of `src/stage_analysis.py`).\n* **Rebuilding the demo data.** `scripts/build_mini_demo_data.py --src <artifact folder>` regenerates `mini_demo_data.json` from the artifact's cached states. `--mname-templates` and `--mcode-per-alg` choose a different subset.\n\nThe geometry is correlational: it describes where representations and survivors sit, not whether the model uses this geometry to choose an algorithm."}
```

### [221] TOOL RESULT — NotebookEdit · 2026-10-26 14:51:45 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [222] THINKING · 2026-10-26 14:51:55 UTC

```
The notebook now has the committed parameters, nearest-algorithm line, and updated markdown. Next I'll run the official clean-environment test in the background (fresh venv, Colab-pinned install, 600s timeout) as specified.
```

### [223] TOOL CALL — Bash · 2026-10-26 14:51:55 UTC

```
Run the official clean-venv notebook test:
start=$(date +%s) && UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_VVA3P0ocZNA2-b603e68c357e && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_VVA3P0ocZNA2-b603e68c357e/bin/python jupyter ipykernel && echo "env ready after $(( $(date +%s) - start )) s" && nb_start=$(date +%s) && /tmp/aii_nb_test_envs/art_VVA3P0ocZNA2-b603e68c357e/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb; echo "nbconvert exit $? after $(( $(date +%s) - nb_start )) s (total $(( $(date +%s) - start )) s)"
```

### [224] TOOL RESULT — Bash · 2026-10-26 14:51:55 UTC

```
{"stdout": "", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false, "backgroundTaskId": "blftqfzyd"}
```

### [225] THINKING · 2026-10-26 14:53:13 UTC

```
While the clean test runs, I'll draft the README, storage manifest, and structured output—the workspace itself is light, just a 1.6 MB JSON file plus code and text.
```

### [226] TOOL CALL — Write · 2026-10-26 14:53:13 UTC

````
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/README.md

# Demo: mapping grid algorithms with and without their names (TP-G, iteration 9)

A runnable, Colab-ready demo of artifact `art_VVA3P0ocZNA2` (experiment 46 of invention-loop iteration 9). The
artifact asks where Qwen3-32B represents the algorithm it writes when its five favourite grid path-search algorithms
are banned. This folder reruns the artifact's own CPU analysis code on a 99-point subset of the cached Qwen3-32B
activations: stages 7-11 of `method.py` (geometry, landing test, bootstrap, lexical regression, RSA, out-of-sample
placement, independent audit, figures).

## Background

Asked to write `solve(grid, start, goal)`, Qwen3-32B implements BFS in 91 of 100 generations. With BFS, DFS, IDDFS,
A\* and greedy best-first search banned in the prompt, the only other catalogued algorithm it writes is unit-weight
Dijkstra (15 of 100). The artifact maps the ten algorithms in the model's residual stream four ways:

* **M-name**: prompts that name the algorithm;
* **M-desc**: name-free descriptions;
* **M-lex**: name-only deltas;
* **M-code**: name-scrubbed programs.

For each map it asks whether unit Dijkstra sits at the **EDGE** of the banned region or **OPPOSITE** it. The full run's
pre-registered outcome is **MIXED**: OPPOSITE on every name-based map, EDGE on the program map. All 15 survivor
programs are also placed at the EDGE. The geometry is correlational.

## Layout

| Path | What it is |
|---|---|
| `code_demo.ipynb` | The demo notebook, executed with outputs. It loads `mini_demo_data.json` from the GitHub raw URL and falls back to the local copy. |
| `mini_demo_data.json` | 99 cached activation states with labels and stimulus text, plus the small inputs the analysis reads and the full-run reference results (1.6 MB). |
| `scripts/build_mini_demo_data.py` | Builds `mini_demo_data.json` from the artifact folder (subset rule, encoding and copied inputs). |
| `.aii/manifest.yaml` | Storage decisions. There is nothing heavy in this folder, so the list is empty. |
| `tpg_modules/` | Not in the repository. The notebook writes it at run time: the artifact's `geometry.py` and `landing.py` byte-for-byte, and a `common.py` excerpt. |

## How to run

* **Colab**: open `code_demo.ipynb` and choose *Runtime > Run all*. It takes about a minute. On Colab the install cell only adds `loguru`.
* **Locally** (Python 3.12):

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python jupyter ipykernel pip
.venv/bin/jupyter nbconvert --to notebook --execute code_demo.ipynb --output code_demo.ipynb
```

The first notebook cell installs the Colab-pinned `numpy==2.0.2`, `scipy==1.16.3`, `scikit-learn==1.6.1`,
`matplotlib==3.10.0`, `networkx==3.6.1` and `loguru==0.7.3`.

On 2 CPU cores the whole notebook took about 40 s of analysis plus the package install. It runs with the committed
resampling counts: 1,000 bootstrap resamples, 10,000 landing-null draws and 100,000 permutations; exact Mantel tests
use 10! = 3,628,800 relabellings.

## The demo data (`mini_demo_data.json`)

`examples` holds 99 points from the cached Qwen3-32B (nf4) states, each at the layer L\* that was committed for its
manifold:

| `manifold` | Points | Selection | Readout, block |
|---|---|---|---|
| `mname` | 30 of 300 | prompt template 0 x aliases 0-2 x all 10 algorithms | S-mean (mean over task-spec tokens), block 31 |
| `mcode_PRIMARY_R1` | 54 of 117 | the first 9 programs (set rank 0-8) of each algorithm with >= 10 verified programs | R1 (mean over code tokens), block 33 |
| `placement_SURV` | 15 of 15 | every unit-Dijkstra program written under the top-five ban | R1, block 33 |

Each example carries:

* `point_id`, `algorithm`, `banned` and `group` (the paraphrase unit used by split-half and bootstrap);
* `input`: the prompt or the name-scrubbed program;
* `x_f16_b64`: the cached float16 state, 5120 values, stored losslessly as base64. Decode it with `np.frombuffer(base64.b64decode(s), dtype='<f2')`.

`metadata` holds the committed blocks and the landing-null inputs (iteration 8's implemented counts and
correct-when-forced rates). It also holds the model RDMs (R_lex, R_beh, R_surface, R_len, ...), the alias lexical
measures, the behavioural MDS coordinates, and the full-run reference results (geometry, RSA, lexical regression,
placement and the N4 verdict) that the notebook prints beside its own numbers.

Why this subset: the selection rule is fixed (first template, first 9 programs), not tuned per point. Every single
M-name template keeps unit Dijkstra OPPOSITE. The M-code frame needs enough programs per algorithm for 15-nearest-
neighbour placement, so it gets more of the 99-point budget.

## Results (demo subset vs full run)

| Quantity | Demo (99 points) | Full run |
|---|---|---|
| M-name, class of unit Dijkstra at k = 10 / 15 | OPPOSITE / OPPOSITE (g/median 1.12 / 1.15) | OPPOSITE / OPPOSITE (1.78 / 1.63) |
| M-code, class of unit Dijkstra at k = 10 / 15 | EDGE / EDGE (0.68 / 0.69) | EDGE / EDGE (0.64 / 0.67) |
| Pooled landing verdict at k = 15, M-name / M-code | OPPOSITE / EDGE | OPPOSITE / EDGE |
| Bootstrap P(EDGE) at k = 15 (1,000 resamples), M-name / M-code | 0.00 / 1.00 | 0.00 / 1.00 |
| RSA, M-name: rho with R_lex / R_beh | 0.52 / 0.35 | 0.46 / 0.24 |
| RSA, M-code: rho with R_lex / R_beh / R_surface | 0.07 / 0.83 / 0.82 | 0.29 / 0.64 / 0.67 |
| P4, Spearman(g_alias, L1) at k = 10 / 15 | -0.65 / -0.65 (pass) | -0.74 / -0.65 (pass) |
| P8, survivor programs placed at the EDGE (LOO accuracy) | 15/15 (0.81) | 15/15 (0.85) |
| Independent networkx audit | classes equal, max abs g diff about 1e-13 | 0 mismatches |

What differs:

* The demo's M-name landing verdict at k = 10 is NEITHER (full run: OPPOSITE).
* In the demo's smaller M-code frame, the survivors' single nearest algorithm is mostly A\* or GBFS rather than unit Dijkstra. All 15 still land on the EDGE side.

## Changes relative to the artifact's code

The notebook keeps the artifact's functions and only replaces file I/O with the in-memory demo data:

* `load_manifold`, `landing_all`, `model_rdms`, `counts` and `_overlay` read `mini_demo_data.json` instead of `cache/states/*.npz` and the `results/` and `inputs/` JSON files.
* The bootstrap and leave-one-out maps run in-process instead of over a spawn `ProcessPoolExecutor`, which cannot import notebook functions. Each resample has its own seed, so the results are identical.
* Files that the analysis wrote are kept in dicts instead: bootstrap matrices, frozen kNN graphs, figure coordinates.
* Figures are shown inline instead of being saved as PDF/PNG.
* `LANDING_DRAWS` and `PERM_P_N` come from the config cell. Their defaults are the committed 10,000 and 100,000.
* Not run, because it needs states that are not in the demo data:
  * GPU state extraction and OpenRouter stages;
  * layer selection;
  * the reference-block section for M-code;
  * the 5-block robustness grid (only the L\* cells run);
  * name evocation;
  * the M-desc, M-lex and Qwen3-8B manifolds.

## Restoring removed files

Nothing in this folder is marked for deletion: `.aii/manifest.yaml` has no `delete` entries and nothing here is
heavy. Two things can be regenerated:

```bash
# tpg_modules/ (written by the notebook's %%writefile cells on every run)
jupyter nbconvert --to notebook --execute code_demo.ipynb --output code_demo.ipynb

# mini_demo_data.json, from the artifact folder of art_VVA3P0ocZNA2 (needs its cache/states/)
python scripts/build_mini_demo_data.py --src <artifact folder> --out mini_demo_data.json
```

The artifact's `cache/states/` (about 0.5 GB of float16 activation arrays) stays on the run's storage volume and is
not in the published repository. To rebuild it from scratch, run that artifact's GPU stages: `method.py mname 32b`,
`method.py states 32b mlex ban`, `method.py states 32b mdesc mcode`, about 30 GPU-minutes on one RTX 5090.
````

### [227] TOOL RESULT — Write · 2026-10-26 14:53:13 UTC

````
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/README.md", "content": "# Demo: mapping grid algorithms with and without their names (TP-G, iteration 9)\n\nA runnable, Colab-ready demo of artifact `art_VVA3P0ocZNA2` (experiment 46 of invention-loop iteration 9). The\nartifact asks where Qwen3-32B represents the algorithm it writes when its five favourite grid path-search algorithms\nare banned. This folder reruns the artifact's own CPU analysis code on a 99-point subset of the cached Qwen3-32B\nactivations: stages 7-11 of `method.py` (geometry, landing test, bootstrap, lexical regression, RSA, out-of-sample\nplacement, independent audit, figures).\n\n## Background\n\nAsked to write `solve(grid, start, goal)`, Qwen3-32B implements BFS in 91 of 100 generations. With BFS, DFS, IDDFS,\nA\\* and greedy best-first search banned in the prompt, the only other catalogued algorithm it writes is unit-weight\nDijkstra (15 of 100). The artifact maps the ten algorithms in the model's residual stream four ways:\n\n* **M-name**: prompts that name the algorithm;\n* **M-desc**: name-free descriptions;\n* **M-lex**: name-only deltas;\n* **M-code**: name-scrubbed programs.\n\nFor each map it asks whether unit Dijkstra sits at the **EDGE** of the banned region or **OPPOSITE** it. The full run's\npre-registered outcome is **MIXED**: OPPOSITE on every name-based map, EDGE on the program map. All 15 survivor\nprograms are also placed at the EDGE. The geometry is correlational.\n\n## Layout\n\n| Path | What it is |\n|---|---|\n| `code_demo.ipynb` | The demo notebook, executed with outputs. It loads `mini_demo_data.json` from the GitHub raw URL and falls back to the local copy. |\n| `mini_demo_data.json` | 99 cached activation states with labels and stimulus text, plus the small inputs the analysis reads and the full-run reference results (1.6 MB). |\n| `scripts/build_mini_demo_data.py` | Builds `mini_demo_data.json` from the artifact folder (subset rule, encoding and copied inputs). |\n| `.aii/manifest.yaml` | Storage decisions. There is nothing heavy in this folder, so the list is empty. |\n| `tpg_modules/` | Not in the repository. The notebook writes it at run time: the artifact's `geometry.py` and `landing.py` byte-for-byte, and a `common.py` excerpt. |\n\n## How to run\n\n* **Colab**: open `code_demo.ipynb` and choose *Runtime > Run all*. It takes about a minute. On Colab the install cell only adds `loguru`.\n* **Locally** (Python 3.12):\n\n```bash\nuv venv --python 3.12 .venv\nuv pip install --python .venv/bin/python jupyter ipykernel pip\n.venv/bin/jupyter nbconvert --to notebook --execute code_demo.ipynb --output code_demo.ipynb\n```\n\nThe first notebook cell installs the Colab-pinned `numpy==2.0.2`, `scipy==1.16.3`, `scikit-learn==1.6.1`,\n`matplotlib==3.10.0`, `networkx==3.6.1` and `loguru==0.7.3`.\n\nOn 2 CPU cores the whole notebook took about 40 s of analysis plus the package install. It runs with the committed\nresampling counts: 1,000 bootstrap resamples, 10,000 landing-null draws and 100,000 permutations; exact Mantel tests\nuse 10! = 3,628,800 relabellings.\n\n## The demo data (`mini_demo_data.json`)\n\n`examples` holds 99 points from the cached Qwen3-32B (nf4) states, each at the layer L\\* that was committed for its\nmanifold:\n\n| `manifold` | Points | Selection | Readout, block |\n|---|---|---|---|\n| `mname` | 30 of 300 | prompt template 0 x aliases 0-2 x all 10 algorithms | S-mean (mean over task-spec tokens), block 31 |\n| `mcode_PRIMARY_R1` | 54 of 117 | the first 9 programs (set rank 0-8) of each algorithm with >= 10 verified programs | R1 (mean over code tokens), block 33 |\n| `placement_SURV` | 15 of 15 | every unit-Dijkstra program written under the top-five ban | R1, block 33 |\n\nEach example carries:\n\n* `point_id`, `algorithm`, `banned` and `group` (the paraphrase unit used by split-half and bootstrap);\n* `input`: the prompt or the name-scrubbed program;\n* `x_f16_b64`: the cached float16 state, 5120 values, stored losslessly as base64. Decode it with `np.frombuffer(base64.b64decode(s), dtype='<f2')`.\n\n`metadata` holds the committed blocks and the landing-null inputs (iteration 8's implemented counts and\ncorrect-when-forced rates). It also holds the model RDMs (R_lex, R_beh, R_surface, R_len, ...), the alias lexical\nmeasures, the behavioural MDS coordinates, and the full-run reference results (geometry, RSA, lexical regression,\nplacement and the N4 verdict) that the notebook prints beside its own numbers.\n\nWhy this subset: the selection rule is fixed (first template, first 9 programs), not tuned per point. Every single\nM-name template keeps unit Dijkstra OPPOSITE. The M-code frame needs enough programs per algorithm for 15-nearest-\nneighbour placement, so it gets more of the 99-point budget.\n\n## Results (demo subset vs full run)\n\n| Quantity | Demo (99 points) | Full run |\n|---|---|---|\n| M-name, class of unit Dijkstra at k = 10 / 15 | OPPOSITE / OPPOSITE (g/median 1.12 / 1.15) | OPPOSITE / OPPOSITE (1.78 / 1.63) |\n| M-code, class of unit Dijkstra at k = 10 / 15 | EDGE / EDGE (0.68 / 0.69) | EDGE / EDGE (0.64 / 0.67) |\n| Pooled landing verdict at k = 15, M-name / M-code | OPPOSITE / EDGE | OPPOSITE / EDGE |\n| Bootstrap P(EDGE) at k = 15 (1,000 resamples), M-name / M-code | 0.00 / 1.00 | 0.00 / 1.00 |\n| RSA, M-name: rho with R_lex / R_beh | 0.52 / 0.35 | 0.46 / 0.24 |\n| RSA, M-code: rho with R_lex / R_beh / R_surface | 0.07 / 0.83 / 0.82 | 0.29 / 0.64 / 0.67 |\n| P4, Spearman(g_alias, L1) at k = 10 / 15 | -0.65 / -0.65 (pass) | -0.74 / -0.65 (pass) |\n| P8, survivor programs placed at the EDGE (LOO accuracy) | 15/15 (0.81) | 15/15 (0.85) |\n| Independent networkx audit | classes equal, max abs g diff about 1e-13 | 0 mismatches |\n\nWhat differs:\n\n* The demo's M-name landing verdict at k = 10 is NEITHER (full run: OPPOSITE).\n* In the demo's smaller M-code frame, the survivors' single nearest algorithm is mostly A\\* or GBFS rather than unit Dijkstra. All 15 still land on the EDGE side.\n\n## Changes relative to the artifact's code\n\nThe notebook keeps the artifact's functions and only replaces file I/O with the in-memory demo data:\n\n* `load_manifold`, `landing_all`, `model_rdms`, `counts` and `_overlay` read `mini_demo_data.json` instead of `cache/states/*.npz` and the `results/` and `inputs/` JSON files.\n* The bootstrap and leave-one-out maps run in-process instead of over a spawn `ProcessPoolExecutor`, which cannot import notebook functions. Each resample has its own seed, so the results are identical.\n* Files that the analysis wrote are kept in dicts instead: bootstrap matrices, frozen kNN graphs, figure coordinates.\n* Figures are shown inline instead of being saved as PDF/PNG.\n* `LANDING_DRAWS` and `PERM_P_N` come from the config cell. Their defaults are the committed 10,000 and 100,000.\n* Not run, because it needs states that are not in the demo data:\n  * GPU state extraction and OpenRouter stages;\n  * layer selection;\n  * the reference-block section for M-code;\n  * the 5-block robustness grid (only the L\\* cells run);\n  * name evocation;\n  * the M-desc, M-lex and Qwen3-8B manifolds.\n\n## Restoring removed files\n\nNothing in this folder is marked for deletion: `.aii/manifest.yaml` has no `delete` entries and nothing here is\nheavy. Two things can be regenerated:\n\n```bash\n# tpg_modules/ (written by the notebook's %%writefile cells on every run)\njupyter nbconvert --to notebook --execute code_demo.ipynb --output code_demo.ipynb\n\n# mini_demo_data.json, from the artifact folder of art_VVA3P0ocZNA2 (needs its cache/states/)\npython scripts/build_mini_demo_data.py --src <artifact folder> --out mini_demo_data.json\n```\n\nThe artifact's `cache/states/` (about 0.5 GB of float16 activation arrays) stays on the run's storage volume and is\nnot in the published repository. To rebuild it from scratch, run that artifact's GPU stages: `method.py mname 32b`,\n`method.py states 32b mlex ban`, `method.py states 32b mdesc mcode`, about 30 GPU-minutes on one RTX 5090.\n", "structuredPatch": [], "originalFile": null, "userModified": false}
````

### [228] TOOL CALL — Write · 2026-10-26 14:53:13 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/.aii/manifest.yaml

# Storage decisions for this demo folder. Nothing here is heavy: code_demo.ipynb, mini_demo_data.json (1.6 MB),
# scripts/ and README.md are text or code below the auto-keep floor, so they need no entry. The notebook writes
# tpg_modules/ (three small .py files, no __pycache__) at run time; see README.md "Restoring removed files".
entries: []
```

### [229] TOOL RESULT — Write · 2026-10-26 14:53:13 UTC

```
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/.aii/manifest.yaml", "content": "# Storage decisions for this demo folder. Nothing here is heavy: code_demo.ipynb, mini_demo_data.json (1.6 MB),\n# scripts/ and README.md are text or code below the auto-keep floor, so they need no entry. The notebook writes\n# tpg_modules/ (three small .py files, no __pycache__) at run time; see README.md \"Restoring removed files\".\nentries: []\n", "structuredPatch": [], "originalFile": null, "userModified": false}
```

### [230] TOOL CALL — Write · 2026-10-26 14:53:13 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/.terminal_claude_agent_struct_out.json

{
  "out_expected_files": {
    "notebook": "code_demo.ipynb",
    "mini_data_file": "mini_demo_data.json"
  }
}
```

### [231] TOOL RESULT — Write · 2026-10-26 14:53:13 UTC

```
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/.terminal_claude_agent_struct_out.json", "content": "{\n  \"out_expected_files\": {\n    \"notebook\": \"code_demo.ipynb\",\n    \"mini_data_file\": \"mini_demo_data.json\"\n  }\n}\n", "structuredPatch": [], "originalFile": null, "userModified": false}
```

### [232] TOOL CALL — Bash · 2026-10-26 14:53:17 UTC

```
Show official test result and workspace contents:
cat /tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-VVA3P0ocZNA2/39a5c6e0-c154-4645-bb18-199862447326/tasks/blftqfzyd.output | tail -15; WS=/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2; ls -la $WS $WS/tpg_modules; find $WS -name "__pycache__"
```

### [233] TOOL RESULT — Bash · 2026-10-26 14:53:17 UTC

```
{"stdout": "env ready after 1 s\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[IPKernelApp] WARNING | Kernel is running over TCP without encryption. All communication (including code and outputs) is sent in plain text and is susceptible to eavesdropping. Use IPC transport or launch with kernel manager-provisioned CurveZMQ keys to enable transport encryption.\n[NbConvertApp] Writing 918526 bytes to code_demo.ipynb\nnbconvert exit 0 after 50 s (total 51 s)\n\n[exited with code 0]\n/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2:\ntotal 9847\ndrwxrwxrwx 5 aii-agent aii-agent 2000390 Oct 26 14:53 .\ndrwxrwxrwx 6 aii-agent aii-agent 2002303 Oct 26 14:26 ..\ndrwxrwxrwx 2 aii-agent aii-agent   34500 Oct 26 14:53 .aii\n-rw-rw-rw- 1 aii-agent aii-agent      54 Oct 26 14:21 .aii_claude_session.json\n-rw-rw-rw- 1 aii-agent aii-agent 1547815 Oct 26 14:53 .repl_agent.ptylog\n-rw-rw-rw- 1 aii-agent aii-agent     113 Oct 26 14:53 .terminal_claude_agent_struct_out.json\n-rw-rw-rw- 1 aii-agent aii-agent    7855 Oct 26 14:53 README.md\n-rw-rw-rw- 1 aii-agent aii-agent  918530 Oct 26 14:52 code_demo.ipynb\n-rw-rw-rw- 1 aii-agent aii-agent 1562275 Oct 26 14:31 mini_demo_data.json\ndrwxrwxrwx 2 aii-agent aii-agent 1001199 Oct 26 14:31 scripts\ndrwxrwxrwx 3 aii-agent aii-agent 1004675 Oct 26 14:52 tpg_modules\n\n/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/tpg_modules:\ntotal 3933\ndrwxrwxrwx 3 aii-agent aii-agent 1004675 Oct 26 14:52 .\ndrwxrwxrwx 5 aii-agent aii-agent 2000390 Oct 26 14:53 ..\ndrwxrwxrwx 2 aii-agent aii-agent 1002992 Oct 26 14:52 __pycache__\n-rw-rw-rw- 1 aii-agent aii-agent    1054 Oct 26 14:52 common.py\n-rw-rw-rw- 1 aii-agent aii-agent   12247 Oct 26 14:52 geometry.py\n-rw-rw-rw- 1 aii-agent aii-agent    3927 Oct 26 14:52 landing.py\n/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/tpg_modules/__pycache__", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [234] THINKING · 2026-10-26 14:53:29 UTC

```
The clean-environment test passed in 50s, well under the 600s limit, but it left a stray `__pycache__` folder—I'll add `sys.dont_write_bytecode = True` and rerun, after first checking this run's output for stderr warnings or absolute paths.
```

### [235] TOOL CALL — Bash · 2026-10-26 14:53:29 UTC

```
Check outputs for errors, stderr and absolute paths:
WS=/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2; SP=/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-VVA3P0ocZNA2/39a5c6e0-c154-4645-bb18-199862447326/scratchpad; $SP/venv/bin/python - <<EOF
import json
nb = json.load(open("$WS/code_demo.ipynb"))
errs = 0
for i, c in enumerate(nb["cells"]):
    for o in c.get("outputs", []):
        if o["output_type"] == "error":
            errs += 1; print("ERROR in cell", i, o["ename"], o["evalue"])
        if o["output_type"] == "stream" and o["name"] == "stderr":
            print(f"STDERR cell {i}:", "".join(o["text"])[:800])
print("errors:", errs, "| exec counts:", [c.get("execution_count") for c in nb["cells"] if c["cell_type"] == "code"])
raw = open("$WS/code_demo.ipynb").read()
for s in ("/ai-inventor", "/tmp/", "run_0oWBKrKEGsmU", "aii-agent"):
    print(repr(s), "occurrences in notebook:", raw.count(s))
print("README abs paths:", open("$WS/README.md").read().count("/ai-inventor"), "| mini data abs paths:", open("$WS/mini_demo_data.json").read().count("/ai-inventor"), "| builder abs paths:", open("$WS/scripts/build_mini_demo_data.py").read().count("/ai-inventor"))
for o in nb["cells"][42]["outputs"]:
    if o["output_type"] == "stream": print("".join(o["text"]))
EOF
```

### [236] TOOL RESULT — Bash · 2026-10-26 14:53:29 UTC

```
{"stdout": "errors: 0 | exec counts: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]\n'/ai-inventor' occurrences in notebook: 1\n'/tmp/' occurrences in notebook: 0\n'run_0oWBKrKEGsmU' occurrences in notebook: 0\n'aii-agent' occurrences in notebook: 0\nREADME abs paths: 0 | mini data abs paths: 0 | builder abs paths: 0\nWhere does unit-weight Dijkstra sit relative to the banned five?\ndemo = this notebook on the 99-point subset; full = the artifact's run on all points (300 M-name, 117 M-code)\n\nmanifold               k | class: demo      full | rank: demo  full | g/median: demo  full | nearest banned: demo   full\n32b|mname              5 |    OPPOSITE    MIDDLE |        4/5   3/5 |           1.00  1.00 |                   A*  IDDFS\n32b|mname             10 |    OPPOSITE  OPPOSITE |        4/5   5/5 |           1.12  1.78 |                   A*  IDDFS\n32b|mname             15 |    OPPOSITE  OPPOSITE |        4/5   5/5 |           1.15  1.63 |                   A*     A*\n32b|mcode_PRIMARY_R1   5 |        EDGE      EDGE |        1/2   1/2 |           0.60  0.73 |                 GBFS   GBFS\n32b|mcode_PRIMARY_R1  10 |        EDGE      EDGE |        1/2   1/2 |           0.68  0.64 |                 GBFS   GBFS\n32b|mcode_PRIMARY_R1  15 |        EDGE      EDGE |        1/2   1/2 |           0.69  0.67 |                 GBFS   GBFS\n\nLanding verdict (15 pooled survivors) and stability, k = 15\n  32b|mname             landing demo OPPOSITE full OPPOSITE | bootstrap P(EDGE) demo 0.00 (n=1000) full 0.00 (n=1000) | split-half S-B demo 0.93 full 0.99\n  32b|mcode_PRIMARY_R1  landing demo EDGE     full EDGE     | bootstrap P(EDGE) demo 1.00 (n=1000) full 1.00 (n=1000) | split-half S-B demo 0.94 full 0.99\n\nRSA: Spearman rho of the class-geodesic RDM with each model RDM (exact Mantel p)\n  32b|mname             R_lex demo +0.52 (p 0.000) full +0.46 (p 0.003) | R_beh demo +0.35 (p 0.015) full +0.24 (p 0.091) | R_surface demo -0.11 (p 0.729) full +0.20 (p 0.128)\n  32b|mcode_PRIMARY_R1  R_lex demo +0.07 (p 0.401) full +0.29 (p 0.164) | R_beh demo +0.83 (p 0.003) full +0.64 (p 0.018) | R_surface demo +0.82 (p 0.001) full +0.67 (p 0.010)\n\nP4, M-name alias level, Spearman(g_alias, L1): demo k10 -0.65, k15 -0.65 (pass True) | full k10 -0.74, k15 -0.65 (pass True)\nP8, survivor programs placed at the EDGE of M-code: demo 15/15 (LOO accuracy 0.81) | full 15/15 (LOO accuracy 0.85)\n    their nearest algorithm: demo A* 8, GBFS 5, Dijkstra(u) 2 | full GBFS 2, Dijkstra(u) 13\n\nFull run, k = 15 class of unit Dijkstra on every manifold analysed: 32b|mname OPPOSITE, 32b|mlex OPPOSITE, 32b|mdesc OPPOSITE, 32b|mcode_PRIMARY_R1 EDGE, 32b|mcode_M32_R1 EDGE, 32b|mcode_PRIMARY_R2 EDGE, 8b|mname OPPOSITE, 8b|mdesc OPPOSITE, 8b|mcode_PRIMARY_R1 EDGE\nFull-run named outcome: MIXED (M-code EDGE, M-desc OPPOSITE); predictions {'P1': False, 'P2': False, 'P3': True, 'P4': True, 'P5': None, 'P6': True, 'P7': None, 'P8': True}\n\nNotebook run time so far: 35 s", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [237] ASSISTANT · 2026-10-26 14:53:35 UTC

```
There is one `/ai-inventor` string in the notebook. I'll locate it, since no absolute server path may be published.
```

### [238] TOOL CALL — Bash · 2026-10-26 14:53:35 UTC

```
Locate the absolute path string in the notebook:
WS=/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2; grep -o ".\{200\}/ai-inventor.\{200\}" $WS/code_demo.ipynb | head -3
```

### [239] TOOL RESULT — Bash · 2026-10-26 14:53:35 UTC

```
{"stdout": "", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [240] TOOL CALL — Bash · 2026-10-26 14:53:37 UTC

```
Locate the absolute path with shorter context:
WS=/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2; grep -n -o ".\{0,160\}/ai-inventor.\{0,160\}" $WS/code_demo.ipynb | head -3
```

### [241] TOOL RESULT — Bash · 2026-10-26 14:53:39 UTC

```
{"stdout": "ugrep: error: error at position 90\n\\x80-\\xbf][\\x80-\\xbf]*){0,160}\n exceeds complexity limits___/", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [242] TOOL CALL — Bash · 2026-10-26 14:53:43 UTC

```
Print context around the absolute path:
WS=/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2; SP=/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-VVA3P0ocZNA2/39a5c6e0-c154-4645-bb18-199862447326/scratchpad; $SP/venv/bin/python -c "
raw = open('$WS/code_demo.ipynb').read()
i = raw.find('/ai-inventor')
print(repr(raw[max(0, i - 300): i + 200]))
"
```

### [243] TOOL RESULT — Bash · 2026-10-26 14:53:43 UTC

```
{"stdout": "'10-26T14:52:08.071974Z\",\\n     \"iopub.status.busy\": \"2026-10-26T14:52:08.071753Z\",\\n     \"iopub.status.idle\": \"2026-10-26T14:52:08.076259Z\",\\n     \"shell.execute_reply\": \"2026-10-26T14:52:08.075870Z\"\\n    }\\n   },\\n   \"outputs\": [],\\n   \"source\": [\\n    \"GITHUB_DATA_URL = \\\\\"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-9/experiment-46/demo/mini_demo_data.json\\\\\"\\\\n\",\\n    \"import http.client\\\\n\",\\n    \"import json'", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [244] THINKING · 2026-10-26 14:54:17 UTC

```
That flagged match is a false positive—just the `ai-inventor-papers` org name in a URL, not an absolute path, so the README, data file, and builder are clean. I'll delete `tpg_modules/` and its `__pycache__` (since it's just regenerated build output) rather than editing the notebook, then move on to the TODO 6 checks, the manifest comment fix, and cleanup.
```

### [245] TOOL CALL — Bash · 2026-10-26 14:54:17 UTC

```
Verify URL, data and fallback; remove runtime module dir:
WS=/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2; SP=/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-VVA3P0ocZNA2/39a5c6e0-c154-4645-bb18-199862447326/scratchpad; cd $WS
echo "(1) exact URL line in notebook source:"; $SP/venv/bin/python - <<'EOF'
import json
nb = json.load(open("code_demo.ipynb"))
want = 'GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-9/experiment-46/demo/mini_demo_data.json"'
src = ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]
print("   exact match:", any(want in s.splitlines() for s in src))
loader = [s for s in src if "def load_data" in s][0]
print("(3) urlopen(GITHUB_DATA_URL) used:", "urllib.request.urlopen(GITHUB_DATA_URL, timeout=15)" in loader, "| local fallback:", 'Path("mini_demo_data.json")' in loader)
d = json.load(open("mini_demo_data.json"))
print("(2) mini_demo_data.json:", len(d["examples"]), "examples, keys", sorted(d))
print("struct out:", json.load(open(".terminal_claude_agent_struct_out.json")))
EOF
rm -rf $WS/tpg_modules && sed -i 's|# tpg_modules/ (three small .py files, no __pycache__) at run time; see README.md "Restoring removed files".|# tpg_modules/ (copies of the artifact modules, a few KB) at run time and it is not kept here; see README.md\n# "Restoring removed files".|' $WS/.aii/manifest.yaml && cat $WS/.aii/manifest.yaml && find $WS -name "__pycache__" -o -name "tpg_modules" | head; ls -la $WS $WS/scripts; du -sh $WS --exclude=.repl_agent.ptylog 2>/dev/null
```

### [246] TOOL RESULT — Bash · 2026-10-26 14:54:17 UTC

```
{"stdout": "(1) exact URL line in notebook source:\n   exact match: True\n(3) urlopen(GITHUB_DATA_URL) used: True | local fallback: True\n(2) mini_demo_data.json: 99 examples, keys ['examples', 'metadata']\nstruct out: {'out_expected_files': {'notebook': 'code_demo.ipynb', 'mini_data_file': 'mini_demo_data.json'}}\n# Storage decisions for this demo folder. Nothing here is heavy: code_demo.ipynb, mini_demo_data.json (1.6 MB),\n# scripts/ and README.md are text or code below the auto-keep floor, so they need no entry. The notebook writes\n# tpg_modules/ (copies of the artifact modules, a few KB) at run time and it is not kept here; see README.md\n# \"Restoring removed files\".\nentries: []\n/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2:\ntotal 8929\ndrwxrwxrwx 4 aii-agent aii-agent 2000391 Oct 26 14:54 .\ndrwxrwxrwx 6 aii-agent aii-agent 2002313 Oct 26 14:26 ..\ndrwxrwxrwx 2 aii-agent aii-agent   37400 Oct 26 14:54 .aii\n-rw-rw-rw- 1 aii-agent aii-agent      54 Oct 26 14:21 .aii_claude_session.json\n-rw-rw-rw- 1 aii-agent aii-agent 1608853 Oct 26 14:54 .repl_agent.ptylog\n-rw-rw-rw- 1 aii-agent aii-agent     113 Oct 26 14:53 .terminal_claude_agent_struct_out.json\n-rw-rw-rw- 1 aii-agent aii-agent    7855 Oct 26 14:53 README.md\n-rw-rw-rw- 1 aii-agent aii-agent  918530 Oct 26 14:52 code_demo.ipynb\n-rw-rw-rw- 1 aii-agent aii-agent 1562275 Oct 26 14:31 mini_demo_data.json\ndrwxrwxrwx 2 aii-agent aii-agent 1001199 Oct 26 14:31 scripts\n\n/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/scripts:\ntotal 2944\ndrwxrwxrwx 2 aii-agent aii-agent 1001199 Oct 26 14:31 .\ndrwxrwxrwx 4 aii-agent aii-agent 2000391 Oct 26 14:54 ..\n-rw-rw-rw- 1 aii-agent aii-agent   12278 Oct 26 14:31 build_mini_demo_data.py\n5.3M\t/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [247] THINKING · 2026-10-26 14:54:37 UTC

```
TODO 6 checks all pass and the workspace is clean. I noticed the README overclaims that every M-name template keeps unit Dijkstra opposite when I'd only tested a few, so I'll verify all ten single templates before leaving the statement in.
```

### [248] TOOL CALL — Bash · 2026-10-26 14:54:37 UTC

```
Check unit-Dijkstra class for each single M-name template:
SP=/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-VVA3P0ocZNA2/39a5c6e0-c154-4645-bb18-199862447326/scratchpad; cat > $SP/explore4.py <<'EOF'
import sys
sys.path.insert(0, sys.argv[1] + "/fake")
sys.path.insert(1, "/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46/src")
import numpy as np
import geometry
SRC = "/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46"
B5 = ["bfs", "dfs", "iddfs", "astar", "gbfs"]; NB5 = ["bibfs", "biastar", "idastar", "jps", "dijkstra_unit"]
zn = np.load(f"{SRC}/cache/states/mname_32b.npz"); bl = [int(b) for b in zn["blocks"]]
Xn = zn["smean"][:, bl.index(31)].astype(np.float64); ln, tn = zn["algorithm"], zn["template"]
for t in range(10):
    m = tn == t
    row = []
    for k in (10, 15):
        geo, _ = geometry.geodesics(Xn[m], k)
        g, _ = geometry.g_values(geo, ln[m], B5, NB5)
        cls, med = geometry.classify(g)
        row.append(f"k{k} {cls['dijkstra_unit']} ({g['dijkstra_unit'] / med:.2f})")
    print(f"template {t}: " + ", ".join(row))
EOF
cd $SP && $SP/venv/bin/python -B explore4.py $SP
```

### [249] TOOL RESULT — Bash · 2026-10-26 14:54:37 UTC

```
{"stdout": "template 0: k10 OPPOSITE (1.12), k15 OPPOSITE (1.15)\ntemplate 1: k10 OPPOSITE (1.13), k15 OPPOSITE (1.17)\ntemplate 2: k10 OPPOSITE (1.12), k15 OPPOSITE (1.19)\ntemplate 3: k10 MIDDLE (1.00), k15 OPPOSITE (1.10)\ntemplate 4: k10 OPPOSITE (1.05), k15 OPPOSITE (1.10)\ntemplate 5: k10 OPPOSITE (1.11), k15 OPPOSITE (1.17)\ntemplate 6: k10 OPPOSITE (1.04), k15 OPPOSITE (1.08)\ntemplate 7: k10 OPPOSITE (1.17), k15 OPPOSITE (1.19)\ntemplate 8: k10 OPPOSITE (1.18), k15 OPPOSITE (1.15)\ntemplate 9: k10 OPPOSITE (1.18), k15 OPPOSITE (1.19)", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [250] THINKING · 2026-10-26 14:54:45 UTC

```
I've confirmed that all 10 templates place unit Dijkstra OPPOSITE at k=15, while at k=10 nine do so and template 3 lands MIDDLE instead. I'll update the README to state this precisely and explain how the 99-point split was derived.
```

### [251] TOOL CALL — Edit · 2026-10-26 14:54:45 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/README.md
OLD: Why this subset: the selection rule is fixed (first template, first 9 programs), not tuned per point. Every single
M-name template keeps unit Dijkstra OPPOSITE. The M-code frame needs enough programs per algorithm for 15-nearest-
neighbour placement, so it gets more of the 99-point budget.
NEW: Why this subset: the rule is fixed (the first template; the first 9 programs per algorithm), not a per-point pick.
Two splits of the 99-point budget were compared: 30 M-name + 54 M-code + 15 survivors, and 60 + 24 + 15. The first
was kept because 15-nearest-neighbour placement needs a larger M-code frame.

The M-name result does not hinge on the template. Run alone, each of the 10 templates puts unit Dijkstra OPPOSITE
at k = 15. At k = 10, 9 of the 10 do; template 3 gives MIDDLE.
```

### [252] TOOL RESULT — Edit · 2026-10-26 14:54:45 UTC

````
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_VVA3P0ocZNA2/README.md", "oldString": "Why this subset: the selection rule is fixed (first template, first 9 programs), not tuned per point. Every single\nM-name template keeps unit Dijkstra OPPOSITE. The M-code frame needs enough programs per algorithm for 15-nearest-\nneighbour placement, so it gets more of the 99-point budget.", "newString": "Why this subset: the rule is fixed (the first template; the first 9 programs per algorithm), not a per-point pick.\nTwo splits of the 99-point budget were compared: 30 M-name + 54 M-code + 15 survivors, and 60 + 24 + 15. The first\nwas kept because 15-nearest-neighbour placement needs a larger M-code frame.\n\nThe M-name result does not hinge on the template. Run alone, each of the 10 templates puts unit Dijkstra OPPOSITE\nat k = 15. At k = 10, 9 of the 10 do; template 3 gives MIDDLE.", "originalFile": "# Demo: mapping grid algorithms with and without their names (TP-G, iteration 9)\n\nA runnable, Colab-ready demo of artifact `art_VVA3P0ocZNA2` (experiment 46 of invention-loop iteration 9). The\nartifact asks where Qwen3-32B represents the algorithm it writes when its five favourite grid path-search algorithms\nare banned. This folder reruns the artifact's own CPU analysis code on a 99-point subset of the cached Qwen3-32B\nactivations: stages 7-11 of `method.py` (geometry, landing test, bootstrap, lexical regression, RSA, out-of-sample\nplacement, independent audit, figures).\n\n## Background\n\nAsked to write `solve(grid, start, goal)`, Qwen3-32B implements BFS in 91 of 100 generations. With BFS, DFS, IDDFS,\nA\\* and greedy best-first search banned in the prompt, the only other catalogued algorithm it writes is unit-weight\nDijkstra (15 of 100). The artifact maps the ten algorithms in the model's residual stream four ways:\n\n* **M-name**: prompts that name the algorithm;\n* **M-desc**: name-free descriptions;\n* **M-lex**: name-only deltas;\n* **M-code**: name-scrubbed programs.\n\nFor each map it asks whether unit Dijkstra sits at the **EDGE** of the banned region or **OPPOSITE** it. The full run's\npre-registered outcome is **MIXED**: OPPOSITE on every name-based map, EDGE on the program map. All 15 survivor\nprograms are also placed at the EDGE. The geometry is correlational.\n\n## Layout\n\n| Path | What it is |\n|---|---|\n| `code_demo.ipynb` | The demo notebook, executed with outputs. It loads `mini_demo_data.json` from the GitHub raw URL and falls back to the local copy. |\n| `mini_demo_data.json` | 99 cached activation states with labels and stimulus text, plus the small inputs the analysis reads and the full-run reference results (1.6 MB). |\n| `scripts/build_mini_demo_data.py` | Builds `mini_demo_data.json` from the artifact folder (subset rule, encoding and copied inputs). |\n| `.aii/manifest.yaml` | Storage decisions. There is nothing heavy in this folder, so the list is empty. |\n| `tpg_modules/` | Not in the repository. The notebook writes it at run time: the artifact's `geometry.py` and `landing.py` byte-for-byte, and a `common.py` excerpt. |\n\n## How to run\n\n* **Colab**: open `code_demo.ipynb` and choose *Runtime > Run all*. It takes about a minute. On Colab the install cell only adds `loguru`.\n* **Locally** (Python 3.12):\n\n```bash\nuv venv --python 3.12 .venv\nuv pip install --python .venv/bin/python jupyter ipykernel pip\n.venv/bin/jupyter nbconvert --to notebook --execute code_demo.ipynb --output code_demo.ipynb\n```\n\nThe first notebook cell installs the Colab-pinned `numpy==2.0.2`, `scipy==1.16.3`, `scikit-learn==1.6.1`,\n`matplotlib==3.10.0`, `networkx==3.6.1` and `loguru==0.7.3`.\n\nOn 2 CPU cores the whole notebook took about 40 s of analysis plus the package install. It runs with the committed\nresampling counts: 1,000 bootstrap resamples, 10,000 landing-null draws and 100,000 permutations; exact Mantel tests\nuse 10! = 3,628,800 relabellings.\n\n## The demo data (`mini_demo_data.json`)\n\n`examples` holds 99 points from the cached Qwen3-32B (nf4) states, each at the layer L\\* that was committed for its\nmanifold:\n\n| `manifold` | Points | Selection | Readout, block |\n|---|---|---|---|\n| `mname` | 30 of 300 | prompt template 0 x aliases 0-2 x all 10 algorithms | S-mean (mean over task-spec tokens), block 31 |\n| `mcode_PRIMARY_R1` | 54 of 117 | the first 9 programs (set rank 0-8) of each algorithm with >= 10 verified programs | R1 (mean over code tokens), block 33 |\n| `placement_SURV` | 15 of 15 | every unit-Dijkstra program written under the top-five ban | R1, block 33 |\n\nEach example carries:\n\n* `point_id`, `algorithm`, `banned` and `group` (the paraphrase unit used by split-half and bootstrap);\n* `input`: the prompt or the name-scrubbed program;\n* `x_f16_b64`: the cached float16 state, 5120 values, stored losslessly as base64. Decode it with `np.frombuffer(base64.b64decode(s), dtype='<f2')`.\n\n`metadata` holds the committed blocks and the landing-null inputs (iteration 8's implemented counts and\ncorrect-when-forced rates). It also holds the model RDMs (R_lex, R_beh, R_surface, R_len, ...), the alias lexical\nmeasures, the behavioural MDS coordinates, and the full-run reference results (geometry, RSA, lexical regression,\nplacement and the N4 verdict) that the notebook prints beside its own numbers.\n\nWhy this subset: the selection rule is fixed (first template, first 9 programs), not tuned per point. Every single\nM-name template keeps unit Dijkstra OPPOSITE. The M-code frame needs enough programs per algorithm for 15-nearest-\nneighbour placement, so it gets more of the 99-point budget.\n\n## Results (demo subset vs full run)\n\n| Quantity | Demo (99 points) | Full run |\n|---|---|---|\n| M-name, class of unit Dijkstra at k = 10 / 15 | OPPOSITE / OPPOSITE (g/median 1.12 / 1.15) | OPPOSITE / OPPOSITE (1.78 / 1.63) |\n| M-code, class of unit Dijkstra at k = 10 / 15 | EDGE / EDGE (0.68 / 0.69) | EDGE / EDGE (0.64 / 0.67) |\n| Pooled landing verdict at k = 15, M-name / M-code | OPPOSITE / EDGE | OPPOSITE / EDGE |\n| Bootstrap P(EDGE) at k = 15 (1,000 resamples), M-name / M-code | 0.00 / 1.00 | 0.00 / 1.00 |\n| RSA, M-name: rho with R_lex / R_beh | 0.52 / 0.35 | 0.46 / 0.24 |\n| RSA, M-code: rho with R_lex / R_beh / R_surface | 0.07 / 0.83 / 0.82 | 0.29 / 0.64 / 0.67 |\n| P4, Spearman(g_alias, L1) at k = 10 / 15 | -0.65 / -0.65 (pass) | -0.74 / -0.65 (pass) |\n| P8, survivor programs placed at the EDGE (LOO accuracy) | 15/15 (0.81) | 15/15 (0.85) |\n| Independent networkx audit | classes equal, max abs g diff about 1e-13 | 0 mismatches |\n\nWhat differs:\n\n* The demo's M-name landing verdict at k = 10 is NEITHER (full run: OPPOSITE).\n* In the demo's smaller M-code frame, the survivors' single nearest algorithm is mostly A\\* or GBFS rather than unit Dijkstra. All 15 still land on the EDGE side.\n\n## Changes relative to the artifact's code\n\nThe notebook keeps the artifact's functions and only replaces file I/O with the in-memory demo data:\n\n* `load_manifold`, `landing_all`, `model_rdms`, `counts` and `_overlay` read `mini_demo_data.json` instead of `cache/states/*.npz` and the `results/` and `inputs/` JSON files.\n* The bootstrap and leave-one-out maps run in-process instead of over a spawn `ProcessPoolExecutor`, which cannot import notebook functions. Each resample has its own seed, so the results are identical.\n* Files that the analysis wrote are kept in dicts instead: bootstrap matrices, frozen kNN graphs, figure coordinates.\n* Figures are shown inline instead of being saved as PDF/PNG.\n* `LANDING_DRAWS` and `PERM_P_N` come from the config cell. Their defaults are the committed 10,000 and 100,000.\n* Not run, because it needs states that are not in the demo data:\n  * GPU state extraction and OpenRouter stages;\n  * layer selection;\n  * the reference-block section for M-code;\n  * the 5-block robustness grid (only the L\\* cells run);\n  * name evocation;\n  * the M-desc, M-lex and Qwen3-8B manifolds.\n\n## Restoring removed files\n\nNothing in this folder is marked for deletion: `.aii/manifest.yaml` has no `delete` entries and nothing here is\nheavy. Two things can be regenerated:\n\n```bash\n# tpg_modules/ (written by the notebook's %%writefile cells on every run)\njupyter nbconvert --to notebook --execute code_demo.ipynb --output code_demo.ipynb\n\n# mini_demo_data.json, from the artifact folder of art_VVA3P0ocZNA2 (needs its cache/states/)\npython scripts/build_mini_demo_data.py --src <artifact folder> --out mini_demo_data.json\n```\n\nThe artifact's `cache/states/` (about 0.5 GB of float16 activation arrays) stays on the run's storage volume and is\nnot in the published repository. To rebuild it from scratch, run that artifact's GPU stages: `method.py mname 32b`,\n`method.py states 32b mlex ban`, `method.py states 32b mdesc mcode`, about 30 GPU-minutes on one RTX 5090.\n", "structuredPatch": [{"oldStart": 71, "oldLines": 10, "newStart": 71, "newLines": 13, "lines": [" measures, the behavioural MDS coordinates, and the full-run reference results (geometry, RSA, lexical regression,", " placement and the N4 verdict) that the notebook prints beside its own numbers.", " ", "-Why this subset: the selection rule is fixed (first template, first 9 programs), not tuned per point. Every single", "-M-name template keeps unit Dijkstra OPPOSITE. The M-code frame needs enough programs per algorithm for 15-nearest-", "-neighbour placement, so it gets more of the 99-point budget.", "+Why this subset: the rule is fixed (the first template; the first 9 programs per algorithm), not a per-point pick.", "+Two splits of the 99-point budget were compared: 30 M-name + 54 M-code + 15 survivors, and 60 + 24 + 15. The first", "+was kept because 15-nearest-neighbour placement needs a larger M-code frame.", " ", "+The M-name result does not hinge on the template. Run alone, each of the 10 templates puts unit Dijkstra OPPOSITE", "+at k = 15. At k = 10, 9 of the 10 do; template 3 gives MIDDLE.", "+", " ## Results (demo subset vs full run)", " ", " | Quantity | Demo (99 points) | Full run |"]}], "userModified": false, "replaceAll": false}
````

### [253] ASSISTANT · 2026-10-26 14:55:01 UTC

```
I've built the demo notebook and its data file, and the notebook passes the clean-environment test: exit 0 in 50 s including package installs, against the 600 s limit.

The artifact's `method.py` is only a stage dispatcher, and its first stages need Qwen3-32B on a GPU plus OpenRouter calls. So the notebook skips those and reruns the CPU analysis code (stages 7–11) on activation vectors the artifact already cached.

**What the notebook runs.** It uses the original analysis functions (`describe`, bootstrap, landing test, lexical regression, RSA with exact Mantel tests, survivor placement, the networkx audit, PCA/MDS/Isomap figures). It writes the original `geometry.py` and `landing.py` to disk and imports them, and both are byte-identical to the artifact's files. The only code changes are:
- data is read from `mini_demo_data.json` instead of the artifact's files;
- the process pools run in-process, because a notebook can't feed them;
- outputs are kept in memory or shown inline instead of saved.

All resampling parameters are at the original values (1,000 bootstrap resamples, 10,000 null draws, 100,000 permutations). The scaling went 18 s at minimum values, 19 s at 10×, 39 s at the original values, so no reduction was needed.

**The data subset.** `mini_demo_data.json` (1.6 MB) holds 99 cached Qwen3-32B states, stored losslessly:
- 30 prompts that name an algorithm (M-name, one prompt template × 3 aliases × 10 algorithms);
- 54 name-scrubbed programs (M-code, the first 9 per algorithm);
- the 15 unit-Dijkstra programs Qwen3-32B wrote when its top five algorithms were banned.

On this subset the headline result matches the full run:

| | Demo (99 points) | Full run |
|---|---|---|
| Unit Dijkstra on M-name, k = 15 | OPPOSITE | OPPOSITE |
| Unit Dijkstra on M-code, k = 15 | EDGE | EDGE |
| M-name RSA, ρ with R_lex / R_beh | 0.52 / 0.35 | 0.46 / 0.24 |
| M-code RSA, ρ with R_beh / R_lex | 0.83 / 0.07 | 0.64 / 0.29 |
| P4 (names drive alias-level geometry) | passes | passes |
| Survivor programs placed at the EDGE | 15/15 | 15/15 |
| Independent audit | no mismatches | no mismatches |

The notebook prints the full-run numbers beside its own and states where the subset differs:
- the M-name verdict at k = 10 is NEITHER instead of OPPOSITE;
- the survivors' nearest algorithm is mostly A\* or GBFS rather than unit Dijkstra, though all 15 still land on the EDGE side.

**Not run in the demo**, because it needs states that aren't in the subset: layer selection, the multi-block robustness grid, name evocation, and the M-desc, M-lex and Qwen3-8B maps.

**Before you rely on it:**
- The GitHub data URL returns 404 until the files are pushed. The notebook falls back to the local copy, which is what the test used.
- Running the notebook writes a small `tpg_modules/` folder holding the module copies. I deleted it after testing; it's regenerated on every run.

Files are in the workspace:
- `code_demo.ipynb`
- `mini_demo_data.json`
- `scripts/build_mini_demo_data.py` (rebuilds the data from the artifact folder)
- `README.md`
- `.aii/manifest.yaml` (no entries; nothing here is heavy)
- `.terminal_claude_agent_struct_out.json`
```
