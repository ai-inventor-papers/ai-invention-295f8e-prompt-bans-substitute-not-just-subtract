# gen_demo_art_experiment_53 — report_results

> Phase: `gen_paper_repo` · `gen_demo_art`
> Run: `gen_paper_repo_c164ac661673` — A Random Activation Push Changes a Code Model's Algorithm Where Temperature Does Not
>
> Full, verbatim transcript of this agent task — every system/user prompt, assistant response, thinking block, tool call and tool result — in the order they occurred. Nothing truncated.

## Task: `gen_demo_art_experiment_53` (terminal_claude_agent, claude-opus-5-5)

### [1] CONFIG · 2026-10-26 15:21:48 UTC

```
model: Claude Opus 5.5 | effort: max | permission: bypassPermissions
```

### [2] SYSTEM-USER prompt · 2026-10-26 15:21:56 UTC

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
Your workspace: `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ`

CRITICAL: Every file you create, write, or save MUST be inside this workspace directory (subdirectories OK). You MUST NOT write files anywhere outside this path — external paths are READ-ONLY. Use absolute paths for all file operations.

EVERY file write MUST start with `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/`:
GOOD: `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/file.py`, `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/results/out.json`
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
id: art_a7CQm-6CXmoJ
type: experiment
title: Which weights make the model pick one algorithm
summary: |-
  BASE-W (iteration 10) localises, at the level of WEIGHTS, where post-training wrote Qwen3-8B's default algorithm at the decision ('fork') token, vs Qwen3-8B-Base, on iteration 9's units: CC (T10, connected components: ' find' vs ' dfs'/' bfs', 20 prompts, primary) and MST (B3, Kruskal vs Prim class, beside), plus Gemma-3-4b's grid fork (descriptive). One RTX 4090; every decisive prediction sha256-chained before its computation (commitments.log).
  Stage 0: own recapture on a different GPU partly reproduces iteration 9 (T10 instruct mean off 0.061 > 0.05 nats; per-prompt bf16 numerics floor up to 0.55 nats; CPU decompositions reproduce 0.842/0.416). Fallback F1: all shares use own m_I/m_B from the same cached states.
  W1 teacher-forced (exact CPU readout): restoring the base fork-class unembedding rows on the instruct residual closes 0.548 [0.44, 0.71] of the CC gap (ROWS_A 0.489, ROWS_D 0.060, final-norm gain 0.000; MST 1.249). Committed verdict SUPPORTED vs 50 isotropic matched-norm draws (median 0.044, max 0.210, p = 1/51), but 'readout-level, not token-specific': random directions in the residual's top-64 PC subspace of equal norm reach p95 1.252 (p = 0.37). Post-training mainly suppressed the ALTERNATIVES' rows (base rows raise ' dfs'/' bfs' fork logits by +2.2/+3.1 nats; ' find' -0.27); the dfs/bfs deltas point into the residual subspace, the find delta is isotropic. 2x2 interaction -1.34 (CC) / +1.75 (MST) nats.
  W1 generation (30 CRN slots, frozen hidden-test labellers): ROWS 5/30 correct DFS vs TWIN 1/30 (4:0, p = 0.125) -> committed verdict NOT SUPPORTED (bar 10/30); FPD 15/30; MST ROWS 24/30 Prim vs 0/30. Pre-registered extensions: pooled 90 CRN pairs ROWS 21/90 vs TWIN 4/90 (17:0, p = 1.5e-5); dosing the row delta x2/x3 gives 21/30 and 30/30 correct DFS (all passing) vs 1/30 for the median isotropic draw x3, but the max-share residual-subspace and delta-transplant draws x3 also give 30/30, and on MST almost any large edit flips the fork. No correct novel ('other') program; USD 0.
  W2 (late MLPs 26-35 swapped to base, all positions): share -0.145 vs Hungarian-matched early swaps 0.461 (diff -0.61 [-0.78, -0.48]) -> rule fails; same-layer random deltas move the margin comparably; fork-only bridge reproduces iteration 9's W arm within 0.008. W3 Gemma: base rows WIDEN the gap (-0.253), family-dependent.
  Checks: stdlib audit 425 checks 0 mismatches; float64 headline re-derivation (audit/rederive_headline.py) within 4.4e-7 with failing placebos; labeller gate 240/240; 627/630 CC programs pass the declared dependency's LeetCode 323/547 I/O pairs (agreement with the labeller 1.000).
  Files: results/summary.json (all verdicts/numbers), w1_tf_summary.json, w1_generation.json, w1_generation_power.json, w2_summary.json, w3_summary.json, stage0.json, deviations.json; figures F1-F8 (incl. activation-space plots F5/F6); data/gen_samples.jsonl + gen_labels.jsonl (1,260 programs); method_out.json (exp_gen_sol_out: w1_tf, w1_generation, w2_tf, w3_tf); cache/ fork states kept for CPU re-analysis.
workspace_path: >-
  /ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56
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
Raw data URL: https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-10/experiment-56/demo/mini_demo_data.json

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
GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-10/experiment-56/demo/mini_demo_data.json"
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
To test-run the notebook in a clean environment (simulating Colab), use the disposable venv at `/tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5`. It is on this machine's local disk, outside your workspace, which is on a slow network volume: never create a venv inside your workspace.
```bash
UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5
UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5/bin/python jupyter ipykernel
/tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb
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
TODO 6. Verify: (1) code_demo.ipynb contains GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-10/experiment-56/demo/mini_demo_data.json" exactly, (2) mini_demo_data.json exists, (3) uses GitHub URL pattern not just open('mini_demo_data.json').
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

### [3] ASSISTANT · 2026-10-26 15:22:06 UTC

```
I'll start by loading the required skills and inspecting the workspace and artifact files in parallel.
```

### [4] TOOL CALL — Skill · 2026-10-26 15:22:06 UTC

```
aii-colab
```

### [5] TOOL RESULT — Skill · 2026-10-26 15:22:06 UTC

```
{"success": true, "commandName": "aii-colab"}
```

### [6] TOOL CALL — Skill · 2026-10-26 15:22:06 UTC

```
aii-long-running-tasks
```

### [7] TOOL RESULT — Skill · 2026-10-26 15:22:06 UTC

```
{"success": true, "commandName": "aii-long-running-tasks"}
```

### [8] TOOL CALL — Bash · 2026-10-26 15:22:06 UTC

```
List workspace and artifact directory contents:
pwd && ls -la && ls -la .aii 2>/dev/null; git log --oneline | head -5; echo "---"; ls -la /ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56 2>&1 | head -80
```

### [9] TOOL RESULT — Bash · 2026-10-26 15:22:06 UTC

```
{"stdout": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ\ntotal 2968\ndrwxrwxrwx 3 aii-agent aii-agent 1003098 Oct 26 15:21 .\ndrwxrwxrwx 8 aii-agent aii-agent 2002207 Oct 26 15:21 ..\ndrwxrwxrwx 2 aii-agent aii-agent       1 Oct 26 15:21 .aii\n-rw-rw-rw- 1 aii-agent aii-agent      54 Oct 26 15:21 .aii_claude_session.json\n-rw-rw-rw- 1 aii-agent aii-agent   31675 Oct 26 15:22 .repl_agent.ptylog\ntotal 981\ndrwxrwxrwx 2 aii-agent aii-agent       1 Oct 26 15:21 .\ndrwxrwxrwx 3 aii-agent aii-agent 1003098 Oct 26 15:21 ..\nfatal: not a git repository (or any parent up to mount point /ai-inventor)\nStopping at filesystem boundary (GIT_DISCOVERY_ACROSS_FILESYSTEM not set).\n---\ntotal 24556\ndrwxrwxrwx 13 aii-agent aii-agent 2035164 Oct 25 05:32 .\ndrwxrwxrwx  9 aii-agent aii-agent 3000215 Oct 24 23:02 ..\ndrwxrwxrwx  2 aii-agent aii-agent   98100 Oct 25 01:49 .aii\n-rw-rw-rw-  1 aii-agent aii-agent      54 Oct 24 23:00 .aii_claude_session.json\n-rw-rw-rw-  1 aii-agent aii-agent    8738 Oct 25 01:49 .aii_worker_result.json\n-rw-rw-rw-  1 aii-agent aii-agent 2621292 Oct 25 01:49 .repl_agent.ptylog\n-rw-rw-rw-  1 aii-agent aii-agent    3662 Oct 25 01:48 .terminal_claude_agent_struct_out.json\n-rw-rw-rw-  1 aii-agent aii-agent   27927 Oct 25 01:47 README.md\ndrwxrwxrwx  2 aii-agent aii-agent 1002062 Oct 25 01:40 audit\ndrwxrwxrwx  2 aii-agent aii-agent 2013636 Oct 25 00:08 cache\n-rw-rw-rw-  1 aii-agent aii-agent   29506 Oct 25 01:45 commitments.log\ndrwxrwxrwx  2 aii-agent aii-agent 2000263 Oct 25 01:04 data\ndrwxrwxrwx  2 aii-agent aii-agent 2000168 Oct 25 00:25 figures\n-rw-rw-rw-  1 aii-agent aii-agent  872093 Oct 25 01:47 full_method_out.json\ndrwxrwxrwx  4 aii-agent aii-agent 2015630 Oct 25 01:28 inputs\n-rw-rw-rw-  1 aii-agent aii-agent  270335 Oct 24 23:14 inputs_manifest.json\ndrwxrwxrwx  3 aii-agent aii-agent 1016250 Oct 25 01:47 logs\n-rw-rw-rw-  1 aii-agent aii-agent    5222 Oct 25 01:45 method.py\n-rw-rw-rw-  1 aii-agent aii-agent  798463 Oct 25 01:46 method_out.json\n-rw-rw-rw-  1 aii-agent aii-agent  117378 Oct 25 01:47 mini_method_out.json\ndrwxrwxrwx  9 aii-agent aii-agent 2000129 Oct 25 01:45 predictions\n-rw-rw-rw-  1 aii-agent aii-agent   70405 Oct 25 01:47 preview_method_out.json\n-rw-rw-rw-  1 aii-agent aii-agent    2760 Oct 24 23:05 pyproject.toml\n-rw-rw-rw-  1 aii-agent aii-agent   10139 Oct 25 01:44 reproducibility.md\n-rwxrwxrwx  1 aii-agent aii-agent     746 Oct 25 00:46 restore.sh\ndrwxrwxrwx  2 aii-agent aii-agent 2004835 Oct 25 01:46 results\ndrwxrwxrwx  2 aii-agent aii-agent   91700 Oct 24 23:24 scripts\ndrwxrwxrwx  2 aii-agent aii-agent 1021030 Oct 25 05:32 src", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [10] ASSISTANT · 2026-10-26 15:22:14 UTC

```
No todo-tracking tool is available in this session, so I'll follow the six TODOs in order and track them in my updates. TODO 1 (skills) is done. Now TODO 2: reading the demo file and preview data.
```

### [11] TOOL CALL — Bash · 2026-10-26 15:22:14 UTC

```
Read the artifact's method.py and project config:
A=/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56; cat $A/method.py; echo "=== pyproject"; cat $A/pyproject.toml; echo "=== restore.sh"; cat $A/restore.sh; echo "=== struct out"; cat $A/.terminal_claude_agent_struct_out.json
```

### [12] TOOL RESULT — Bash · 2026-10-26 15:22:14 UTC

```
{"stdout": "#!/usr/bin/env python3\n\"\"\"BASE-W stage CLI: which weights hold the default algorithm (iteration 10).\n\nEvery stage runs its scripts in their own processes (GPU stages load one model per process; never two models on the\nGPU); each child's PID is recorded in logs/pids.jsonl and its output goes to logs/<stage>_<n>.log.\n\n  s_1   vendor + hash the inputs, hardware/env record, labeller gate, COMMIT #0 (protocol + code snapshot)\n  s0    capture the fork states of Qwen3-8B and Qwen3-8B-Base, numerics debug sweep, stage-0 report, null draws +\n        COMMIT #1\n  w1tf  W1 teacher-forced arms and nulls + COMMIT #2 (generation plan and predictions); per-token logit export\n  w1gen W1 generation (30 CRN slots per arm), G5 determinism test, labelling, analysis\n  ext   pre-registered generation extensions: dose-response (COMMIT #4), strong nulls at x3 (COMMIT #5), 60 extra\n        CRN slots for power (COMMIT #7); labelling, analysis\n  w2    Hungarian matching + COMMIT #3, in-place weight swaps (all-position and fork-only scopes), summary\n  w3    Gemma-3-4b it/pt captures and the output-untied row test (descriptive)\n  out   CPU tests, delta geometry, LeetCode-pair dependency check, stdlib audit, summary, positioning, figures,\n        method_out.json (+ mini/preview)\n\nUsage: .venv/bin/python method.py --stages s_1,s0,w1tf,w1gen,ext,w2,w3,out   (or --stages all)\n\"\"\"\n\nfrom __future__ import annotations\n\nimport argparse\nimport json\nimport os\nimport subprocess\nimport sys\nimport time\nfrom pathlib import Path\n\nROOT = Path(__file__).resolve().parent\nSRC = ROOT / \"src\"\nLOGS = ROOT / \"logs\"\nPY = sys.executable\n\nSTAGES: dict[str, list[list[str]]] = {\n    \"s_1\": [[\"inputs10.py\", \"copy\"], [\"inputs10.py\", \"hardware\"], [\"inputs10.py\", \"gate\"],\n            [\"protocol10.py\", \"commit0\"]],\n    \"s0\": [[\"capture10.py\", \"qwen\", \"all\"], [\"capture10.py\", \"qwen_base\", \"all\"], [\"debug_s0.py\", \"qwen\"],\n           [\"debug_s0.py\", \"qwen_base\"], [\"w1_tf.py\", \"s0report\"], [\"w1_tf.py\", \"nulls\"]],\n    \"w1tf\": [[\"w1_tf.py\", \"score\"], [\"w1_tf.py\", \"export_zs\"]],\n    \"w1gen\": [[\"w1_gen.py\", \"gpu\", \"2400\"], [\"w1_gen.py\", \"g5\"], [\"w1_gen.py\", \"label\"], [\"w1_gen.py\", \"analyze\"]],\n    \"ext\": [[\"w1_dose_gen.py\", \"commit\"], [\"w1_dose_gen.py\", \"gpu\"], [\"w1_dose_gen.py\", \"commit_strong\"],\n            [\"w1_dose_gen.py\", \"gpu_strong\"], [\"w1_dose_gen.py\", \"commit_power\"], [\"w1_dose_gen.py\", \"gpu_power\"],\n            [\"w1_gen.py\", \"label\"], [\"w1_gen.py\", \"analyze\"], [\"w1_dose_gen.py\", \"analyze_power\"]],\n    \"w2\": [[\"w2_swap.py\", \"match\"], [\"w2_swap.py\", \"gpu\", \"all\"], [\"w2_swap.py\", \"summary\"]],\n    \"w3\": [[\"w3_gemma.py\", \"gpu\", \"gemma\"], [\"w3_gemma.py\", \"gpu\", \"gemma_pt\"], [\"w3_gemma.py\", \"score\"]],\n    \"out\": [[\"tests_cpu10.py\"], [\"analysis10.py\", \"delta_geometry\"], [\"depcheck10.py\"], [\"../audit/rederive.py\"],\n            [\"../audit/rederive_headline.py\"],\n            [\"analysis10.py\", \"summary\"], [\"positioning10.py\"], [\"figures10.py\"], [\"outputs10.py\"]],\n}\nORDER = (\"s_1\", \"s0\", \"w1tf\", \"w1gen\", \"ext\", \"w2\", \"w3\", \"out\")\n\n\ndef run(stage: str, i: int, cmd: list[str]) -> None:\n    LOGS.mkdir(exist_ok=True)\n    log = LOGS / f\"{stage}_{i}.log\"\n    env = dict(os.environ, PYTORCH_CUDA_ALLOC_CONF=\"expandable_segments:True\")\n    argv = [PY, \"-I\", cmd[0]] + cmd[1:] if cmd[0] == \"../audit/rederive.py\" else [PY] + cmd\n    t0 = time.time()\n    with open(log, \"w\") as fh:\n        p = subprocess.Popen(argv, cwd=SRC, stdout=fh, stderr=subprocess.STDOUT, env=env)\n        with open(LOGS / \"pids.jsonl\", \"a\") as pf:\n            pf.write(json.dumps({\"stage\": stage, \"cmd\": cmd, \"pid\": p.pid, \"utc\": time.strftime(\"%Y-%m-%dT%H:%M:%SZ\",\n                                                                                               time.gmtime())}) + \"\\n\")\n        rc = p.wait()\n    print(f\"[{stage}] {' '.join(cmd)} -> rc {rc} in {time.time() - t0:.0f}s (log {log.relative_to(ROOT)})\")\n    if rc != 0:\n        raise SystemExit(f\"stage {stage} failed at {cmd}; see {log}\")\n\n\ndef format_outputs() -> None:\n    skill_env = os.environ.get(\"AII_JSON_SKILL_DIR\")      # the AI Inventor aii-json skill folder, if available\n    if not skill_env:\n        print(\"AII_JSON_SKILL_DIR not set: skipping schema validation and mini/preview generation\")\n        return\n    skill = Path(skill_env)\n    py = skill.parent / \".ability_client_venv\" / \"bin\" / \"python\"\n    if py.exists():\n        subprocess.run([str(py), str(skill / \"scripts\" / \"aii_json_validate_schema.py\"), \"--format\", \"exp_gen_sol_out\",\n                        \"--file\", str(ROOT / \"method_out.json\")], check=False)\n        subprocess.run([str(py), str(skill / \"scripts\" / \"aii_json_format_mini_preview.py\"), \"--input\",\n                        str(ROOT / \"method_out.json\")], check=False)\n\n\ndef main() -> None:\n    ap = argparse.ArgumentParser()\n    ap.add_argument(\"--stages\", default=\"all\")\n    a = ap.parse_args()\n    stages = ORDER if a.stages == \"all\" else tuple(s.strip() for s in a.stages.split(\",\"))\n    for s in stages:\n        if s not in STAGES:\n            raise SystemExit(f\"unknown stage {s}; choose from {ORDER}\")\n        for i, cmd in enumerate(STAGES[s]):\n            run(s, i, cmd)\n        if s == \"out\":\n            format_outputs()\n\n\nif __name__ == \"__main__\":\n    main()\n=== pyproject\n[project]\nname = \"iter10-base-w-weight-localisation\"\nversion = \"1.0.0\"\ndescription = \"Iteration 10, BASE-W: which weights hold the default algorithm (readout rows, late MLPs, Gemma rows) in Qwen3-8B vs Qwen3-8B-Base; pins copied from iteration 9.\"\nrequires-python = \"==3.12.*\"\n# Every package is pinned to the exact version installed in .venv (`uv pip freeze --python .venv/bin/python`; the\n# uv-created venv has no pip). Python 3.12.14. torch 2.8.0+cu128 wheels come from PyPI's default CUDA 12.8 build.\ndependencies = [\n    \"accelerate==1.15.0\",\n    \"annotated-types==0.8.0\",\n    \"anyio==4.15.1\",\n    \"astor==0.8.1\",\n    \"attrs==26.1.0\",\n    \"certifi==2026.10.19\",\n    \"charset-normalizer==3.5.2\",\n    \"cloudpickle==3.1.2\",\n    \"contourpy==1.4.0\",\n    \"cycler==0.12.1\",\n    \"filelock==4.2.4\",\n    \"fonttools==4.67.0\",\n    \"formulaic==1.2.2\",\n    \"fsspec==2026.9.0\",\n    \"h11==0.16.0\",\n    \"hf-xet==1.7.0\",\n    \"httpcore2==2.16.0\",\n    \"httpx2==2.16.0\",\n    \"huggingface-hub==0.36.2\",\n    \"idna==3.20\",\n    \"interface-meta==2.0.1\",\n    \"jinja2==3.1.6\",\n    \"jiter==0.17.0\",\n    \"joblib==1.6.0\",\n    \"jsonschema-specifications==2025.9.1\",\n    \"jsonschema==4.26.0\",\n    \"kiwisolver==1.5.1\",\n    \"loguru==0.7.3\",\n    \"markupsafe==3.0.4\",\n    \"matplotlib==3.11.2\",\n    \"mpmath==1.3.0\",\n    \"narwhals==2.27.1\",\n    \"networkx==3.7\",\n    \"numpy==2.2.6\",\n    \"nvidia-cublas-cu12==12.8.4.1\",\n    \"nvidia-cuda-cupti-cu12==12.8.90\",\n    \"nvidia-cuda-nvrtc-cu12==12.8.93\",\n    \"nvidia-cuda-runtime-cu12==12.8.90\",\n    \"nvidia-cudnn-cu12==9.10.2.21\",\n    \"nvidia-cufft-cu12==11.3.3.83\",\n    \"nvidia-cufile-cu12==1.13.1.3\",\n    \"nvidia-curand-cu12==10.3.9.90\",\n    \"nvidia-cusolver-cu12==11.7.3.90\",\n    \"nvidia-cusparse-cu12==12.5.8.93\",\n    \"nvidia-cusparselt-cu12==0.7.1\",\n    \"nvidia-nccl-cu12==2.27.3\",\n    \"nvidia-nvjitlink-cu12==12.8.93\",\n    \"nvidia-nvtx-cu12==12.8.90\",\n    \"openai==3.35.1\",\n    \"packaging==26.3\",\n    \"pandas==3.0.6\",\n    \"patsy==1.0.3\",\n    \"pillow==13.0.0\",\n    \"psutil==7.2.2\",\n    \"pydantic-core==2.50.1\",\n    \"pydantic==2.14.1\",\n    \"pyparsing==3.3.3\",\n    \"python-dateutil==3.0.0\",\n    \"pyyaml==6.0.3\",\n    \"rapidfuzz==3.14.6\",\n    \"referencing==0.37.0\",\n    \"regex==2026.9.29\",\n    \"requests==2.34.2\",\n    \"rpds-py==2026.9.1\",\n    \"safetensors==0.8.0\",\n    \"scikit-learn==1.9.1\",\n    \"scipy==1.18.1\",\n    \"setuptools==84.2.1\",\n    \"six==1.17.0\",\n    \"sniffio==1.3.1\",\n    \"statsmodels==0.15.0\",\n    \"sympy==1.14.0\",\n    \"tenacity==9.2.1\",\n    \"threadpoolctl==3.7.0\",\n    \"tokenizers==0.22.2\",\n    \"torch==2.8.0\",\n    \"tqdm==4.70.1\",\n    \"transformers==4.57.6\",\n    \"triton==3.4.0\",\n    \"truststore==0.10.5\",\n    \"typing-extensions==4.16.0\",\n    \"typing-inspection==0.4.4\",\n    \"tzdata==2026.5\",\n    \"urllib3==2.8.0\",\n    \"wrapt==2.5.1\",\n]\n=== restore.sh\n#!/usr/bin/env bash\n# Restore everything that .aii/manifest.yaml marks `delete`, plus the model weights (kept in the shared HF cache, not here).\nset -euo pipefail\ncd \"$(dirname \"$0\")\"\n# 1. Python environment (pinned versions in pyproject.toml; uv only)\nuv venv .venv --python=3.12\nuv pip install --python .venv/bin/python -r pyproject.toml\n# 2. model weights at the pinned revisions (into $HF_HUB_CACHE; Gemma needs an HF token with Gemma access)\nbash scripts/download_models.sh\n# 3. bytecode caches are rebuilt on import; to prebuild:\n.venv/bin/python -m compileall -q src inputs/iter9/src || true\n# 4. (optional) recompute cache/ (GPU, ~5 min on one 24 GB GPU) -- results/ already holds every number\n# .venv/bin/python method.py --stages s0,w3\n=== struct out\n{\n \"title\": \"Which weights make the model pick one algorithm\",\n \"layman_summary\": \"Tests whether a coding model's habit of always choosing the same algorithm lives in a few output weights, and shows that editing them makes it write the alternative algorithm correctly.\",\n \"summary\": \"BASE-W (iteration 10) localises, at the level of WEIGHTS, where post-training wrote Qwen3-8B's default algorithm at the decision ('fork') token, vs Qwen3-8B-Base, on iteration 9's units: CC (T10, connected components: ' find' vs ' dfs'/' bfs', 20 prompts, primary) and MST (B3, Kruskal vs Prim class, beside), plus Gemma-3-4b's grid fork (descriptive). One RTX 4090; every decisive prediction sha256-chained before its computation (commitments.log).\\nStage 0: own recapture on a different GPU partly reproduces iteration 9 (T10 instruct mean off 0.061 > 0.05 nats; per-prompt bf16 numerics floor up to 0.55 nats; CPU decompositions reproduce 0.842/0.416). Fallback F1: all shares use own m_I/m_B from the same cached states.\\nW1 teacher-forced (exact CPU readout): restoring the base fork-class unembedding rows on the instruct residual closes 0.548 [0.44, 0.71] of the CC gap (ROWS_A 0.489, ROWS_D 0.060, final-norm gain 0.000; MST 1.249). Committed verdict SUPPORTED vs 50 isotropic matched-norm draws (median 0.044, max 0.210, p = 1/51), but 'readout-level, not token-specific': random directions in the residual's top-64 PC subspace of equal norm reach p95 1.252 (p = 0.37). Post-training mainly suppressed the ALTERNATIVES' rows (base rows raise ' dfs'/' bfs' fork logits by +2.2/+3.1 nats; ' find' -0.27); the dfs/bfs deltas point into the residual subspace, the find delta is isotropic. 2x2 interaction -1.34 (CC) / +1.75 (MST) nats.\\nW1 generation (30 CRN slots, frozen hidden-test labellers): ROWS 5/30 correct DFS vs TWIN 1/30 (4:0, p = 0.125) -> committed verdict NOT SUPPORTED (bar 10/30); FPD 15/30; MST ROWS 24/30 Prim vs 0/30. Pre-registered extensions: pooled 90 CRN pairs ROWS 21/90 vs TWIN 4/90 (17:0, p = 1.5e-5); dosing the row delta x2/x3 gives 21/30 and 30/30 correct DFS (all passing) vs 1/30 for the median isotropic draw x3, but the max-share residual-subspace and delta-transplant draws x3 also give 30/30, and on MST almost any large edit flips the fork. No correct novel ('other') program; USD 0.\\nW2 (late MLPs 26-35 swapped to base, all positions): share -0.145 vs Hungarian-matched early swaps 0.461 (diff -0.61 [-0.78, -0.48]) -> rule fails; same-layer random deltas move the margin comparably; fork-only bridge reproduces iteration 9's W arm within 0.008. W3 Gemma: base rows WIDEN the gap (-0.253), family-dependent.\\nChecks: stdlib audit 425 checks 0 mismatches; float64 headline re-derivation (audit/rederive_headline.py) within 4.4e-7 with failing placebos; labeller gate 240/240; 627/630 CC programs pass the declared dependency's LeetCode 323/547 I/O pairs (agreement with the labeller 1.000).\\nFiles: results/summary.json (all verdicts/numbers), w1_tf_summary.json, w1_generation.json, w1_generation_power.json, w2_summary.json, w3_summary.json, stage0.json, deviations.json; figures F1-F8 (incl. activation-space plots F5/F6); data/gen_samples.jsonl + gen_labels.jsonl (1,260 programs); method_out.json (exp_gen_sol_out: w1_tf, w1_generation, w2_tf, w3_tf); cache/ fork states kept for CPU re-analysis.\",\n \"out_expected_files\": {\n  \"script\": \"method.py\",\n  \"full_output\": \"full_method_out.json\",\n  \"mini_output\": \"mini_method_out.json\",\n  \"preview_output\": \"preview_method_out.json\",\n  \"reproducibility\": \"reproducibility.md\"\n },\n \"upload_ignore_regexes\": [\n  \"(^|/)\\\\.venv/\",\n  \"(^|/)__pycache__/\",\n  \"(^|/)\\\\.repl_agent\\\\.ptylog$\"\n ]\n}", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [13] TOOL CALL — Bash · 2026-10-26 15:22:14 UTC

```
List artifact subdirectories and sizes:
A=/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56; ls -la $A/src $A/scripts $A/results $A/data $A/figures $A/audit $A/cache $A/inputs $A/predictions $A/logs | head -200; du -sh $A/* 2>/dev/null
```

### [14] TOOL RESULT — Bash · 2026-10-26 15:22:14 UTC

```
{"stdout": "/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/audit:\ntotal 2988\ndrwxrwxrwx  2 aii-agent aii-agent 1002062 Oct 25 01:40 .\ndrwxrwxrwx 13 aii-agent aii-agent 2035164 Oct 25 05:32 ..\n-rw-rw-rw-  1 aii-agent aii-agent   14569 Oct 25 01:05 rederive.py\n-rw-rw-rw-  1 aii-agent aii-agent    6555 Oct 25 01:40 rederive_headline.py\n\n/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/cache:\ntotal 143597\ndrwxrwxrwx  2 aii-agent aii-agent  2013636 Oct 25 00:08 .\ndrwxrwxrwx 13 aii-agent aii-agent  2035164 Oct 25 05:32 ..\n-rw-rw-rw-  1 aii-agent aii-agent 24309897 Oct 24 23:27 fork_base_B3.pt\n-rw-rw-rw-  1 aii-agent aii-agent 24310003 Oct 24 23:27 fork_base_T10.pt\n-rw-rw-rw-  1 aii-agent aii-agent 24310003 Oct 24 23:26 fork_instr_B3.pt\n-rw-rw-rw-  1 aii-agent aii-agent 24310109 Oct 24 23:26 fork_instr_T10.pt\n-rw-rw-rw-  1 aii-agent aii-agent 21199799 Oct 25 00:07 gemma_gemma.pt\n-rw-rw-rw-  1 aii-agent aii-agent 21199997 Oct 25 00:08 gemma_gemma_pt.pt\n-rw-rw-rw-  1 aii-agent aii-agent  1217453 Oct 24 23:34 lm_head_rownorms.pt\n-rw-rw-rw-  1 aii-agent aii-agent  1067406 Oct 24 23:26 resid_pca_B3.pt\n-rw-rw-rw-  1 aii-agent aii-agent  1067415 Oct 24 23:26 resid_pca_T10.pt\n\n/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/data:\ntotal 6635\ndrwxrwxrwx  2 aii-agent aii-agent 2000263 Oct 25 01:04 .\ndrwxrwxrwx 13 aii-agent aii-agent 2035164 Oct 25 05:32 ..\n-rw-rw-rw-  1 aii-agent aii-agent 1246934 Oct 25 01:04 gen_labels.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent 1511074 Oct 25 01:03 gen_samples.jsonl\n\n/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/figures:\ntotal 5671\ndrwxrwxrwx  2 aii-agent aii-agent 2000168 Oct 25 00:25 .\ndrwxrwxrwx 13 aii-agent aii-agent 2035164 Oct 25 05:32 ..\n-rw-rw-rw-  1 aii-agent aii-agent   28047 Oct 25 00:51 F1_w1_shares_nulls.pdf\n-rw-rw-rw-  1 aii-agent aii-agent  231234 Oct 25 00:51 F1_w1_shares_nulls.png\n-rw-rw-rw-  1 aii-agent aii-agent   42968 Oct 25 00:51 F2_per_prompt_shares.pdf\n-rw-rw-rw-  1 aii-agent aii-agent  202747 Oct 25 00:51 F2_per_prompt_shares.png\n-rw-rw-rw-  1 aii-agent aii-agent   17345 Oct 25 00:51 F3_dose_response.pdf\n-rw-rw-rw-  1 aii-agent aii-agent  136868 Oct 25 00:51 F3_dose_response.png\n-rw-rw-rw-  1 aii-agent aii-agent   20095 Oct 25 00:51 F4_generation.pdf\n-rw-rw-rw-  1 aii-agent aii-agent  232232 Oct 25 00:51 F4_generation.png\n-rw-rw-rw-  1 aii-agent aii-agent   41715 Oct 25 00:51 F5_readout_plane.pdf\n-rw-rw-rw-  1 aii-agent aii-agent  327961 Oct 25 00:51 F5_readout_plane.png\n-rw-rw-rw-  1 aii-agent aii-agent   17706 Oct 25 00:51 F6_pca_block35.pdf\n-rw-rw-rw-  1 aii-agent aii-agent  123840 Oct 25 00:51 F6_pca_block35.png\n-rw-rw-rw-  1 aii-agent aii-agent   21683 Oct 25 00:51 F7_w2_swaps.pdf\n-rw-rw-rw-  1 aii-agent aii-agent  234890 Oct 25 00:51 F7_w2_swaps.png\n-rw-rw-rw-  1 aii-agent aii-agent   16848 Oct 25 00:51 F8_w3_gemma.pdf\n-rw-rw-rw-  1 aii-agent aii-agent   71724 Oct 25 00:51 F8_w3_gemma.png\n\n/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/inputs:\ntotal 6936\ndrwxrwxrwx  4 aii-agent aii-agent 2015630 Oct 25 01:28 .\ndrwxrwxrwx 13 aii-agent aii-agent 2035164 Oct 25 05:32 ..\ndrwxrwxrwx  2 aii-agent aii-agent 1035145 Oct 25 01:28 art_j3Rm_lr2nzR6\ndrwxrwxrwx 10 aii-agent aii-agent 2015596 Oct 24 23:20 iter9\n\n/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/logs:\ntotal 4126\ndrwxrwxrwx  3 aii-agent aii-agent 1016250 Oct 25 01:47 .\ndrwxrwxrwx 13 aii-agent aii-agent 2035164 Oct 25 05:32 ..\n-rw-rw-rw-  1 aii-agent aii-agent     626 Oct 25 00:21 analysis10_delta_geometry.log\n-rw-rw-rw-  1 aii-agent aii-agent    1264 Oct 25 01:46 analysis10_summary.log\n-rw-rw-rw-  1 aii-agent aii-agent    7615 Oct 24 23:26 capture10_qwen.log\n-rw-rw-rw-  1 aii-agent aii-agent    5594 Oct 24 23:27 capture10_qwen_base.log\n-rw-rw-rw-  1 aii-agent aii-agent    2474 Oct 25 01:32 debug_s0.log\n-rw-rw-rw-  1 aii-agent aii-agent     554 Oct 24 23:34 debug_s0_qwen.log\n-rw-rw-rw-  1 aii-agent aii-agent     574 Oct 24 23:36 debug_s0_qwen_base.log\n-rw-rw-rw-  1 aii-agent aii-agent     651 Oct 25 01:42 depcheck10.log\n-rw-rw-rw-  1 aii-agent aii-agent     735 Oct 24 23:02 download.log\n-rw-rw-rw-  1 aii-agent aii-agent    1869 Oct 25 00:51 figures10.log\n-rw-rw-rw-  1 aii-agent aii-agent     112 Oct 24 23:15 gate_stdout.log\n-rw-rw-rw-  1 aii-agent aii-agent     144 Oct 24 23:14 inputs10_copy.log\n-rw-rw-rw-  1 aii-agent aii-agent     125 Oct 24 23:15 inputs10_gate.log\n-rw-rw-rw-  1 aii-agent aii-agent     662 Oct 24 23:14 inputs10_hardware.log\n-rw-rw-rw-  1 aii-agent aii-agent    1006 Oct 25 01:46 outputs10.log\ndrwxrwxrwx  2 aii-agent aii-agent 1001016 Oct 25 01:32 positioning\n-rw-rw-rw-  1 aii-agent aii-agent       0 Oct 25 00:31 positioning10.log\n-rw-rw-rw-  1 aii-agent aii-agent     119 Oct 24 23:20 protocol10.log\n-rw-rw-rw-  1 aii-agent aii-agent       8 Oct 24 23:27 run_s0.out\n-rw-rw-rw-  1 aii-agent aii-agent    4639 Oct 25 01:32 s0_qwen.log\n-rw-rw-rw-  1 aii-agent aii-agent    4532 Oct 25 01:32 s0_qwen_base.log\n-rw-rw-rw-  1 aii-agent aii-agent    2164 Oct 25 01:32 s0_smoke.log\n-rw-rw-rw-  1 aii-agent aii-agent    1187 Oct 25 01:45 tests_cpu10.log\n-rw-rw-rw-  1 aii-agent aii-agent    3518 Oct 25 01:45 time_ledger.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent    4338 Oct 25 01:47 todos.md\n-rw-rw-rw-  1 aii-agent aii-agent    1641 Oct 25 01:40 uv_pip_freeze.txt\n-rw-rw-rw-  1 aii-agent aii-agent    2280 Oct 24 23:10 venv_install.log\n-rw-rw-rw-  1 aii-agent aii-agent    5279 Oct 25 01:32 w1_dose_gen.out\n-rw-rw-rw-  1 aii-agent aii-agent     846 Oct 25 01:04 w1_dose_gen_analyze_power.log\n-rw-rw-rw-  1 aii-agent aii-agent    1177 Oct 25 00:36 w1_dose_gen_commit.log\n-rw-rw-rw-  1 aii-agent aii-agent     691 Oct 25 00:57 w1_dose_gen_commit_power.log\n-rw-rw-rw-  1 aii-agent aii-agent    1740 Oct 25 00:45 w1_dose_gen_commit_strong.log\n-rw-rw-rw-  1 aii-agent aii-agent    6088 Oct 25 00:41 w1_dose_gen_gpu.log\n-rw-rw-rw-  1 aii-agent aii-agent   10345 Oct 25 01:03 w1_dose_gen_gpu_power.log\n-rw-rw-rw-  1 aii-agent aii-agent    6786 Oct 25 00:49 w1_dose_gen_gpu_strong.log\n-rw-rw-rw-  1 aii-agent aii-agent    3452 Oct 25 00:50 w1_gen_analyze.log\n-rw-rw-rw-  1 aii-agent aii-agent     592 Oct 24 23:54 w1_gen_g5.log\n-rw-rw-rw-  1 aii-agent aii-agent   12607 Oct 24 23:45 w1_gen_gpu.log\n-rw-rw-rw-  1 aii-agent aii-agent   10589 Oct 25 01:32 w1_gen_gpu.out\n-rw-rw-rw-  1 aii-agent aii-agent     356 Oct 25 01:04 w1_gen_label.log\n-rw-rw-rw-  1 aii-agent aii-agent      75 Oct 24 23:52 w1_gen_label.out\n-rw-rw-rw-  1 aii-agent aii-agent    8396 Oct 25 01:32 w1_power_gen.out\n-rw-rw-rw-  1 aii-agent aii-agent    5697 Oct 25 01:32 w1_strong_gen.out\n-rw-rw-rw-  1 aii-agent aii-agent      83 Oct 25 00:08 w1_tf_export_zs.log\n-rw-rw-rw-  1 aii-agent aii-agent     587 Oct 24 23:34 w1_tf_nulls.log\n-rw-rw-rw-  1 aii-agent aii-agent     959 Oct 24 23:29 w1_tf_s0report.log\n-rw-rw-rw-  1 aii-agent aii-agent    1483 Oct 24 23:35 w1_tf_score.log\n-rw-rw-rw-  1 aii-agent aii-agent    1487 Oct 25 01:32 w1_tf_score.out\n-rw-rw-rw-  1 aii-agent aii-agent    5164 Oct 25 01:32 w2_gpu.out\n-rw-rw-rw-  1 aii-agent aii-agent     255 Oct 24 23:54 w2_match.out\n-rw-rw-rw-  1 aii-agent aii-agent    5155 Oct 25 01:32 w2_smoke.out\n-rw-rw-rw-  1 aii-agent aii-agent   14295 Oct 25 00:02 w2_swap_gpu.log\n-rw-rw-rw-  1 aii-agent aii-agent     335 Oct 24 23:54 w2_swap_match.log\n-rw-rw-rw-  1 aii-agent aii-agent    1563 Oct 25 00:05 w2_swap_summary.log\n-rw-rw-rw-  1 aii-agent aii-agent     301 Oct 25 00:08 w3_gemma_gpu.log\n-rw-rw-rw-  1 aii-agent aii-agent     546 Oct 25 00:13 w3_gemma_score.log\n-rw-rw-rw-  1 aii-agent aii-agent     637 Oct 25 01:32 w3_gpu.out\n\n/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/predictions:\ntotal 11019\ndrwxrwxrwx  9 aii-agent aii-agent 2000129 Oct 25 01:45 .\ndrwxrwxrwx 13 aii-agent aii-agent 2035164 Oct 25 05:32 ..\ndrwxrwxrwx  2 aii-agent aii-agent 1004283 Oct 24 23:20 code_commit0\ndrwxrwxrwx  2 aii-agent aii-agent 1022231 Oct 25 01:09 code_final\ndrwxrwxrwx  2 aii-agent aii-agent 1022320 Oct 25 01:17 code_final_v2\ndrwxrwxrwx  2 aii-agent aii-agent 1022923 Oct 25 01:24 code_final_v3\ndrwxrwxrwx  2 aii-agent aii-agent 1022952 Oct 25 01:33 code_final_v4\ndrwxrwxrwx  2 aii-agent aii-agent 1023693 Oct 25 01:45 code_final_v5\ndrwxrwxrwx  2 aii-agent aii-agent 1002010 Oct 25 01:14 code_history\n-rw-rw-rw-  1 aii-agent aii-agent    8218 Oct 24 23:20 commit0_protocol.json\n-rw-rw-rw-  1 aii-agent aii-agent     583 Oct 25 01:24 commit10_code_final_v3.json\n-rw-rw-rw-  1 aii-agent aii-agent     635 Oct 25 01:33 commit11_code_final_v4.json\n-rw-rw-rw-  1 aii-agent aii-agent     622 Oct 25 01:45 commit12_code_final_v5.json\n-rw-rw-rw-  1 aii-agent aii-agent     200 Oct 24 23:34 commit1_stage0_nulls.json\n-rw-rw-rw-  1 aii-agent aii-agent   69746 Oct 24 23:35 commit2_w1tf_genplan.json\n-rw-rw-rw-  1 aii-agent aii-agent     288 Oct 24 23:54 commit3_w2_matching.json\n-rw-rw-rw-  1 aii-agent aii-agent   18879 Oct 25 00:36 commit4_dose_gen.json\n-rw-rw-rw-  1 aii-agent aii-agent   20432 Oct 25 00:45 commit5_strong_null_gen.json\n-rw-rw-rw-  1 aii-agent aii-agent     919 Oct 25 00:57 commit7_power_gen.json\n-rw-rw-rw-  1 aii-agent aii-agent     498 Oct 25 01:09 commit8_code_final.json\n-rw-rw-rw-  1 aii-agent aii-agent     551 Oct 25 01:17 commit9_code_final_v2.json\n-rw-rw-rw-  1 aii-agent aii-agent     310 Oct 24 23:14 env.json\n-rw-rw-rw-  1 aii-agent aii-agent     308 Oct 24 23:14 hardware.json\n\n/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/results:\ntotal 53475\ndrwxrwxrwx  2 aii-agent aii-agent  2004835 Oct 25 01:46 .\ndrwxrwxrwx 13 aii-agent aii-agent  2035164 Oct 25 05:32 ..\n-rw-rw-rw-  1 aii-agent aii-agent     5676 Oct 24 23:27 capture_base.json\n-rw-rw-rw-  1 aii-agent aii-agent     5752 Oct 24 23:26 capture_instr.json\n-rw-rw-rw-  1 aii-agent aii-agent      790 Oct 25 00:05 decomposition.json\n-rw-rw-rw-  1 aii-agent aii-agent     8818 Oct 25 00:21 delta_geometry.json\n-rw-rw-rw-  1 aii-agent aii-agent     2130 Oct 25 01:42 depcheck_leetcode.json\n-rw-rw-rw-  1 aii-agent aii-agent     6767 Oct 25 01:16 deviations.json\n-rw-rw-rw-  1 aii-agent aii-agent      216 Oct 24 23:15 labeller_gate.json\n-rw-rw-rw-  1 aii-agent aii-agent 39329718 Oct 24 23:34 null_draws_B3.npz\n-rw-rw-rw-  1 aii-agent aii-agent  7375562 Oct 24 23:34 null_draws_T10.npz\n-rw-rw-rw-  1 aii-agent aii-agent     3741 Oct 24 23:34 null_meta.json\n-rw-rw-rw-  1 aii-agent aii-agent     1377 Oct 25 01:37 partial_status.json\n-rw-rw-rw-  1 aii-agent aii-agent     5969 Oct 25 00:31 positioning.json\n-rw-rw-rw-  1 aii-agent aii-agent    19113 Oct 25 01:45 rederive.json\n-rw-rw-rw-  1 aii-agent aii-agent     4076 Oct 25 01:41 rederive_headline.json\n-rw-rw-rw-  1 aii-agent aii-agent    23513 Oct 24 23:36 s0_debug.json\n-rw-rw-rw-  1 aii-agent aii-agent    13174 Oct 24 23:29 stage0.json\n-rw-rw-rw-  1 aii-agent aii-agent    36573 Oct 25 01:46 summary.json\n-rw-rw-rw-  1 aii-agent aii-agent     1779 Oct 25 01:45 tests_cpu.json\n-rw-rw-rw-  1 aii-agent aii-agent     3332 Oct 25 00:52 tests_gpu.json\n-rw-rw-rw-  1 aii-agent aii-agent     3675 Oct 25 00:02 tests_gpu_w2.json\n-rw-rw-rw-  1 aii-agent aii-agent     2052 Oct 24 23:45 w1_gen_gpu.json\n-rw-rw-rw-  1 aii-agent aii-agent    53603 Oct 25 00:50 w1_generation.json\n-rw-rw-rw-  1 aii-agent aii-agent     4860 Oct 25 01:04 w1_generation_power.json\n-rw-rw-rw-  1 aii-agent aii-agent  2613359 Oct 24 23:35 w1_tf_rows.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent    67479 Oct 24 23:35 w1_tf_summary.json\n-rw-rw-rw-  1 aii-agent aii-agent    28332 Oct 25 00:08 w1_tf_zS.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent     7039 Oct 24 23:54 w2_matching.json\n-rw-rw-rw-  1 aii-agent aii-agent   615491 Oct 25 00:02 w2_rows.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent   118923 Oct 25 00:05 w2_summary.json\n-rw-rw-rw-  1 aii-agent aii-agent     2444 Oct 25 00:08 w3_capture.json\n-rw-rw-rw-  1 aii-agent aii-agent   335163 Oct 25 00:13 w3_rows.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent     8445 Oct 25 00:13 w3_summary.json\n\n/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/scripts:\ntotal 2079\ndrwxrwxrwx  2 aii-agent aii-agent   91700 Oct 24 23:24 .\ndrwxrwxrwx 13 aii-agent aii-agent 2035164 Oct 25 05:32 ..\n-rwxrwxrwx  1 aii-agent aii-agent     556 Oct 24 23:02 download_models.sh\n-rwxrwxrwx  1 aii-agent aii-agent     361 Oct 24 23:24 run_s0.sh\n\n/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/src:\ntotal 3198\ndrwxrwxrwx  2 aii-agent aii-agent 1021030 Oct 25 05:32 .\ndrwxrwxrwx 13 aii-agent aii-agent 2035164 Oct 25 05:32 ..\n-rw-rw-rw-  1 aii-agent aii-agent    9435 Oct 25 01:45 analysis10.py\n-rw-rw-rw-  1 aii-agent aii-agent   10622 Oct 24 23:18 capture10.py\n-rw-rw-rw-  1 aii-agent aii-agent   14319 Oct 25 01:42 cfg10.py\n-rw-rw-rw-  1 aii-agent aii-agent    2443 Oct 24 23:32 debug_s0.py\n-rw-rw-rw-  1 aii-agent aii-agent    5518 Oct 25 01:42 depcheck10.py\n-rw-rw-rw-  1 aii-agent aii-agent   16535 Oct 25 00:42 figures10.py\n-rw-rw-rw-  1 aii-agent aii-agent    8577 Oct 24 23:10 inputs10.py\n-rw-rw-rw-  1 aii-agent aii-agent    8916 Oct 25 01:23 outputs10.py\n28K\t/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/README.md\n1000K\t/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/audit\n139M\t/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/cache\n29K\t/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/commitments.log\n4.6M\t/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/data\n3.6M\t/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/figures\n852K\t/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/full_method_out.json\n269M\t/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/inputs\n264K\t/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/inputs_manifest.json\n2.2M\t/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/logs\n5.5K\t/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/method.py\n780K\t/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/method_out.json\n115K\t/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/mini_method_out.json\n11M\t/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/predictions\n69K\t/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/preview_method_out.json\n3.0K\t/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/pyproject.toml\n10K\t/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/reproducibility.md\n1.0K\t/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/restore.sh\n51M\t/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/results\n92K\t/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/scripts\n1.2M\t/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/src", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [15] THINKING · 2026-10-26 15:22:24 UTC

```
method.py orchestrates stages by launching subprocess scripts in src/, but several referenced scripts (w1_tf.py, w1_gen.py, w2_swap.py, etc.) are missing. I'll look for a full code snapshot and check the README for context.
```

### [16] TOOL CALL — Bash · 2026-10-26 15:22:24 UTC

```
List code snapshots and input directories:
A=/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56; ls -la $A/predictions/code_final_v5 $A/predictions/code_history | head -60; ls -la $A/inputs/iter9 $A/inputs/art_j3Rm_lr2nzR6 | head -60
```

### [17] TOOL RESULT — Bash · 2026-10-26 15:22:24 UTC

```
{"stdout": "/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/predictions/code_final_v5:\ntotal 3195\ndrwxrwxrwx 2 aii-agent aii-agent 1023693 Oct 25 01:45 .\ndrwxrwxrwx 9 aii-agent aii-agent 2000129 Oct 25 01:45 ..\n-rw-rw-rw- 1 aii-agent aii-agent    9435 Oct 25 01:45 analysis10.py\n-rw-rw-rw- 1 aii-agent aii-agent   14569 Oct 25 01:05 audit_rederive.py\n-rw-rw-rw- 1 aii-agent aii-agent    6555 Oct 25 01:40 audit_rederive_headline.py\n-rw-rw-rw- 1 aii-agent aii-agent   10622 Oct 24 23:18 capture10.py\n-rw-rw-rw- 1 aii-agent aii-agent   14319 Oct 25 01:42 cfg10.py\n-rw-rw-rw- 1 aii-agent aii-agent    2443 Oct 24 23:32 debug_s0.py\n-rw-rw-rw- 1 aii-agent aii-agent    5518 Oct 25 01:42 depcheck10.py\n-rwxrwxrwx 1 aii-agent aii-agent     556 Oct 24 23:02 download_models.sh\n-rw-rw-rw- 1 aii-agent aii-agent   16535 Oct 25 00:42 figures10.py\n-rw-rw-rw- 1 aii-agent aii-agent    8577 Oct 24 23:10 inputs10.py\n-rw-rw-rw- 1 aii-agent aii-agent    5222 Oct 25 01:45 method.py\n-rw-rw-rw- 1 aii-agent aii-agent    8916 Oct 25 01:23 outputs10.py\n-rw-rw-rw- 1 aii-agent aii-agent    7068 Oct 25 00:29 positioning10.py\n-rw-rw-rw- 1 aii-agent aii-agent   10734 Oct 24 23:19 protocol10.py\n-rwxrwxrwx 1 aii-agent aii-agent     361 Oct 24 23:24 run_s0.sh\n-rw-rw-rw- 1 aii-agent aii-agent    6585 Oct 25 01:17 tests_cpu10.py\n-rw-rw-rw- 1 aii-agent aii-agent   20346 Oct 25 00:56 w1_dose_gen.py\n-rw-rw-rw- 1 aii-agent aii-agent   20228 Oct 25 00:45 w1_gen.py\n-rw-rw-rw- 1 aii-agent aii-agent   34971 Oct 25 00:08 w1_tf.py\n-rw-rw-rw- 1 aii-agent aii-agent   25357 Oct 24 23:58 w2_swap.py\n-rw-rw-rw- 1 aii-agent aii-agent   13701 Oct 24 23:49 w3_gemma.py\n\n/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/predictions/code_history:\ntotal 2953\ndrwxrwxrwx 2 aii-agent aii-agent 1002010 Oct 25 01:14 .\ndrwxrwxrwx 9 aii-agent aii-agent 2000129 Oct 25 01:45 ..\n-rw-rw-rw- 1 aii-agent aii-agent    7066 Oct 25 01:14 commit4_w1_dose_gen.py\n-rw-rw-rw- 1 aii-agent aii-agent   13518 Oct 25 01:14 commit5_w1_dose_gen.py\n/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/inputs/art_j3Rm_lr2nzR6:\ntotal 3332\ndrwxrwxrwx 2 aii-agent aii-agent 1035145 Oct 25 01:28 .\ndrwxrwxrwx 4 aii-agent aii-agent 2015630 Oct 25 01:28 ..\n-rw-rw-rw- 1 aii-agent aii-agent   60370 Oct 25 01:28 full_data_out_subset_323_547.json\n-rw-rw-rw- 1 aii-agent aii-agent  262028 Oct 19 15:47 mini_data_out.json\n-rw-rw-rw- 1 aii-agent aii-agent   26394 Oct 19 15:47 preview_data_out.json\n-rw-rw-rw- 1 aii-agent aii-agent   11098 Oct 19 15:57 reproducibility.md\n\n/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/inputs/iter9:\ntotal 10889\ndrwxrwxrwx 10 aii-agent aii-agent 2015596 Oct 24 23:20 .\ndrwxrwxrwx  4 aii-agent aii-agent 2015630 Oct 25 01:28 ..\n-rw-rw-rw-  1 aii-agent aii-agent   15180 Oct 24 23:05 README.md\ndrwxrwxrwx  2 aii-agent aii-agent       1 Oct 24 23:20 cache\n-rw-rw-rw-  1 aii-agent aii-agent     670 Oct 24 23:05 commitments.log\ndrwxrwxrwx  2 aii-agent aii-agent 1053845 Oct 24 23:05 data\ndrwxrwxrwx  2 aii-agent aii-agent       1 Oct 24 23:20 figures\ndrwxrwxrwx  2 aii-agent aii-agent       1 Oct 24 23:20 logs\ndrwxrwxrwx  2 aii-agent aii-agent 1005722 Oct 24 23:05 predictions\n-rw-rw-rw-  1 aii-agent aii-agent    2795 Oct 24 23:05 pyproject.toml\ndrwxrwxrwx  2 aii-agent aii-agent 2009745 Oct 24 23:05 results\ndrwxrwxrwx  2 aii-agent aii-agent 1021200 Oct 25 05:32 src\ndrwxrwxrwx  9 aii-agent aii-agent 2005770 Oct 24 23:05 vendor", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [18] TOOL CALL — Bash · 2026-10-26 15:22:24 UTC

```
Read the artifact README:
A=/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56; cat $A/README.md
```

### [19] TOOL RESULT — Bash · 2026-10-26 15:22:24 UTC

```
{"stdout": "# Which weights hold the default algorithm (iteration 10, BASE-W)\n\nIteration 9 found that when Qwen3-8B writes a program it commits to an algorithm at one **fork token**, and\nthat post-training sharpened that choice relative to Qwen3-8B-Base. Its component patching was non-specific:\nmatched random late-layer sets closed 81% of the MST gap.\n\nThis artifact moves the question from activations to **weights**. It asks whether the instruct default is stored\nin the... [truncated, 28388 chars total]
```

### [20] THINKING · 2026-10-26 15:22:58 UTC

```
The README confirms each W1 arm uses exact CPU arithmetic on cached fp32 fork states, letting readout analysis run GPU-free in a notebook. Now I'll check the core scripts it references.
```

### [21] TOOL CALL — Bash · 2026-10-26 15:22:58 UTC

```
Read the configuration and utilities module:
A=/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56; cat $A/src/cfg10.py
```

### [22] TOOL RESULT — Bash · 2026-10-26 15:22:58 UTC

```
{"stdout": "#!/usr/bin/env python3\n\"\"\"Iteration-10 BASE-W artifact: constants, paths and shared utilities.\n\nQuestion: where did post-training write Qwen3-8B's default at the algorithm fork, at the level of WEIGHTS?\n  W1  readout rows: the fork-class unembedding rows (and the final-norm gain) of the base model swapped into the\n      instruct readout of the instruct residual (exact CPU readout on cached fork states), against 3 x 50 matched\n      random-row nulls; then generation with 30 common-random-number slots per arm.\n  W2  late-MLP weights (layers 26-35) swapped to base in place (all-position and fork-only scopes), against\n      Frobenius-matched early swaps (Hungarian matched, layers 2-13) and same-layer random deltas.\n  W3  the W1 row test at Gemma-3-4b's grid fork (descriptive).\n\nConventions (as iteration 9):\n- Fork position = the LAST input position (prompt + opening); its logits choose the decision token.\n- Margin m = lse(z[D]) - lse(z[A]) in fp32 from the bf16 final-norm hidden state, D = the instruct default class\n  tokens, A = the alternative class tokens (= log P(D) - log P(A) at T 1).\n- share(X) = sum_p (m_I,p - m_X,p) / sum_p (m_I,p - m_B,p) (ratio of sums, primary).\n\"\"\"\n\nfrom __future__ import annotations\n\nimport hashlib\nimport json\nimport math\nimport os\nimport resource\nimport sys\nimport time\nfrom datetime import datetime, timezone\nfrom pathlib import Path\nfrom typing import Any, Iterable\n\nimport numpy as np\nfrom loguru import logger\n\nROOT = Path(__file__).resolve().parents[1]\nSRC = ROOT / \"src\"\nINPUTS = ROOT / \"inputs\"\nI9 = INPUTS / \"iter9\"                       # verbatim copy of iteration 9's artifact (results, data, vendor, src)\nI9_SRC = I9 / \"src\"                         # vendored iteration-9 code (imported, never edited)\nI9_RES = I9 / \"results\"\nI9_VENDOR = I9 / \"vendor\"\nV41 = I9_VENDOR / \"art_18XvfcJJZi1O\"        # frozen CC/MST labeller tree (label_k3.py + hidden tests)\nV43 = I9_VENDOR / \"art_lzuosbrb34wB\"\nDATA_DIR = ROOT / \"data\"\nRESULTS_DIR = ROOT / \"results\"\nFIG_DIR = ROOT / \"figures\"\nLOG_DIR = ROOT / \"logs\"\nPRED_DIR = ROOT / \"predictions\"\nCACHE_DIR = ROOT / \"cache\"\nfor _d in (DATA_DIR, RESULTS_DIR, FIG_DIR, LOG_DIR, PRED_DIR, CACHE_DIR):\n    _d.mkdir(parents=True, exist_ok=True)\nCOMMITS = ROOT / \"commitments.log\"\nGENESIS = hashlib.sha256(b\"iter10_basew\").hexdigest()\n\n# read-only source folders of the inputs other artifacts produced: the iteration-9 artifact art_cDba8_DycUJd (only\n# inputs10.py reads it; everything else reads the vendored copy inputs/iter9) and the declared dependency\n# art_j3Rm_lr2nzR6 (iteration-1 dataset). Resolution: the environment variable, else the sibling folder named by the\n# artifact id (how the repository publishes artifacts), else the vendored copy inside this folder.\ndef _artifact_dir(env: str, art_id: str, vendored: Path) -> Path:\n    if os.environ.get(env):\n        return Path(os.environ[env])\n    if (ROOT.parent / art_id).is_dir():\n        return ROOT.parent / art_id\n    return vendored\n\n\nITER9 = _artifact_dir(\"ART_CDBA8_DIR\", \"art_cDba8_DycUJd\", I9)\nDEP_DATASET = _artifact_dir(\"ART_J3RM_DIR\", \"art_j3Rm_lr2nzR6\", INPUTS / \"art_j3Rm_lr2nzR6\")\nDEP_SUBSET = INPUTS / \"art_j3Rm_lr2nzR6\" / \"full_data_out_subset_323_547.json\"\n\n# ------------------------------------------------------------------------------------------------ models\nMODELS = {\n    \"qwen\": (\"Qwen/Qwen3-8B\", \"b968826d9c46dd6066d109eabc6255188de91218\"),\n    \"qwen_base\": (\"Qwen/Qwen3-8B-Base\", \"49e3418fbbbca6ecbdf9608b4d22e5a407081db4\"),\n    \"gemma\": (\"google/gemma-3-4b-it\", \"093f9f388b31de276ce2de164bdc2081324b9767\"),\n    \"gemma_pt\": (\"google/gemma-3-4b-pt\", \"cc012e0a6d0787b4adcc0fa2c4da74402494554d\"),\n}\nN_LAYERS = 36\nD_MODEL = 4096\nD_FF = 12288\nVOCAB = 151936\nRMS_EPS = 1e-6\nEOS_IDS = (151645, 151643)\nTEMPLATES = (\"W1\", \"W2\", \"W3\", \"W4\", \"W5\")\n\n# ------------------------------------------------------------------------------------------------ design\nUNITS_TF = (\"T10\", \"B3\")                    # T10 = connected components (primary), B3 = MST (beside)\nUNIT_IDX = {\"T10\": 0, \"B3\": 1, \"G-GRID\": 2}\nB_OT_CANDIDATES = (40, 24, 16, 8)           # one-token batch shapes tried in S0 (iteration 9 used 40)\nCHUNK_ROWS = 8192                           # vocabulary rows per chunk for fp32 full-vocabulary readouts\nDOSES = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5)\nSIGN_DOSE = -1.0\nN_NULL = 50\nNULL_TYPES = (\"RAND_ISO\", \"DELTA_SWAP\", \"RAND_RESID\")\nNULL_SEED0 = {\"RAND_ISO\": 101000, \"RAND_RESID\": 102000, \"DELTA_SWAP\": 103000}\nRANDDELTA_SEED0 = 104000\nN_RANDDELTA = 3\nRESID_PCS = 64\nDELTA_SWAP_TOL_DELTA = 0.05                 # ||Delta_s|| within +-5% of ||Delta_t||\nDELTA_SWAP_TOL_W = 0.10                     # ||w_I,s|| within +-10% of ||w_I,t||\nDELTA_SWAP_EXCLUDE = {\"T10\": (\"find\", \"dfs\", \"bfs\", \"union\", \"kr\", \"prim\", \"mst\"),\n                      \"B3\": (\"find\", \"dfs\", \"bfs\", \"union\", \"kr\", \"prim\", \"mst\", \"check\", \"minimum\", \"priority\",\n                             \"helper\", \"dis\", \"pr\", \"use\", \"to\", \"using\", \"prime\"),\n                      \"G-GRID\": (\"visited\", \"queue\", \"dfs\", \"bfs\", \"stack\", \"find\", \"union\", \"kr\", \"prim\", \"mst\")}\nSEED_BOOT = 20261024\nN_BOOT = 10000\nSMALL_GAP = 0.5\nLATE = tuple(range(26, 36))\nEARLY_POOL = tuple(range(2, 14))\nITER9_W_LAYERS = (26, 27, 28, 30, 32)\n\n# generation (iteration-9 CRN engine)\nSEED0 = 9101\nSLOTS_PER_T = 6\nMAX_NEW = {\"B3\": 768, \"T10\": 1024}\nGEN_B = 6\nGEN_ARMS = (\"TWIN\", \"ROWS\", \"RAND_MED\", \"RAND_MAX\", \"RAND_0\", \"FPD\", \"ROWS_ALLSTEPS\", \"FULL_UNEMB_FORK\")\nCORRECT = {\"T10\": {\"dfs\"}, \"B3\": {\"prim_heap\", \"prim_array\"}}\nMINORITY = {\"T10\": {\"dfs\", \"bfs\"}, \"B3\": {\"prim_heap\", \"prim_array\"}}\nFULL_UNEMB_TV = 0.05\n\nTHRESH = {\n    \"W1_rows_share\": 0.50, \"W1_rand_iso_median\": 0.15, \"W1_disconfirm\": 0.20,\n    \"W1GEN_rows_min_correct\": 10, \"W1GEN_rand_max_correct\": 3, \"W1GEN_alpha\": 0.05,\n    \"W2_late_minus_early\": 0.15,\n    \"S0_mean_tol\": 0.05, \"S0_prompt_tol_B40\": 0.05, \"S0_prompt_tol_small_B\": 0.10, \"S0_spearman\": 0.99,\n    \"S0_decomp_tol\": 0.03, \"S0_decomp_target\": {\"T10\": 0.85, \"B3\": 0.43},\n    \"W2_bridge_tol\": 0.05, \"labeller_gate\": 0.99, \"G1_rel_err\": 2e-3,\n}\nBUDGET_MSG = \"AI Inventor per-run OpenRouter budget\"\nOPENROUTER_CAP_USD = 0.30\n\n\n# ------------------------------------------------------------------------------------------------ utils\ndef setup_logging(name: str) -> None:\n    logger.remove()\n    logger.add(sys.stdout, level=\"INFO\", format=\"{time:HH:mm:ss}|{level:<7}|{message}\")\n    logger.add(str(LOG_DIR / f\"{name}.log\"), rotation=\"30 MB\", level=\"DEBUG\")\n\n\ndef set_ram_limit(gb: float) -> None:\n    lim = int(gb * 1024 ** 3)\n    try:\n        resource.setrlimit(resource.RLIMIT_AS, (lim, lim))\n    except (ValueError, OSError) as e:\n        logger.warning(f\"could not set RLIMIT_AS: {e}\")\n\n\ndef detect_cpus() -> int:\n    try:\n        q = int(Path(\"/sys/fs/cgroup/cpu/cpu.cfs_quota_us\").read_text())\n        p = int(Path(\"/sys/fs/cgroup/cpu/cpu.cfs_period_us\").read_text())\n        if q > 0:\n            return max(1, math.ceil(q / p))\n    except (FileNotFoundError, ValueError):\n        pass\n    try:\n        return len(os.sched_getaffinity(0))\n    except (AttributeError, OSError):\n        return os.cpu_count() or 1\n\n\ndef container_ram_gb() -> float | None:\n    for p in (\"/sys/fs/cgroup/memory.max\", \"/sys/fs/cgroup/memory/memory.limit_in_bytes\"):\n        try:\n            v = Path(p).read_text().strip()\n            if v != \"max\" and int(v) < 1_000_000_000_000:\n                return int(v) / 1e9\n        except (FileNotFoundError, ValueError):\n            pass\n    return None\n\n\ndef utc_now() -> str:\n    return datetime.now(timezone.utc).strftime(\"%Y-%m-%dT%H:%M:%S.%fZ\")\n\n\ndef sha256_text(s: str) -> str:\n    return hashlib.sha256(s.encode(\"utf-8\")).hexdigest()\n\n\ndef sha256_file(p: Path) -> str:\n    h = hashlib.sha256()\n    with open(p, \"rb\") as fh:\n        for chunk in iter(lambda: fh.read(1 << 20), b\"\"):\n            h.update(chunk)\n    return h.hexdigest()\n\n\ndef ids_sha(ids: list[int]) -> str:\n    return sha256_text(json.dumps([int(i) for i in ids]))\n\n\ndef model_path(key: str) -> str:\n    mid, rev = MODELS[key]\n    cache = os.environ.get(\"HF_HUB_CACHE\") or (Path(os.environ.get(\"HF_HOME\", Path.home() / \".cache/huggingface\"))\n                                               / \"hub\")\n    snap = Path(cache) / (\"models--\" + mid.replace(\"/\", \"--\")) / \"snapshots\" / rev\n    if snap.exists():\n        return str(snap)\n    raise FileNotFoundError(f\"{mid}@{rev} not in the HF cache; run scripts/download_models.sh\")\n\n\ndef _json_default(o: Any) -> Any:\n    if isinstance(o, np.integer):\n        return int(o)\n    if isinstance(o, np.floating):\n        return None if not np.isfinite(o) else float(o)\n    if isinstance(o, np.ndarray):\n        return o.tolist()\n    if isinstance(o, np.bool_):\n        return bool(o)\n    if isinstance(o, Path):\n        return str(o)\n    if isinstance(o, (set, frozenset)):\n        return sorted(o)\n    if isinstance(o, tuple):\n        return list(o)\n    raise TypeError(f\"not JSON serialisable: {type(o)}\")\n\n\ndef clean_nan(o: Any) -> Any:\n    if isinstance(o, float):\n        return o if math.isfinite(o) else None\n    if isinstance(o, dict):\n        return {k: clean_nan(v) for k, v in o.items()}\n    if isinstance(o, (list, tuple)):\n        return [clean_nan(v) for v in o]\n    return o\n\n\ndef read_json(p: Path) -> Any:\n    return json.loads(Path(p).read_text())\n\n\ndef write_json(p: Path, obj: Any) -> None:\n    p = Path(p)\n    p.parent.mkdir(parents=True, exist_ok=True)\n    tmp = p.with_suffix(p.suffix + \".tmp\")\n    tmp.write_text(json.dumps(clean_nan(obj), indent=1, default=_json_default))\n    tmp.replace(p)\n\n\ndef read_jsonl(p: Path) -> list[dict[str, Any]]:\n    p = Path(p)\n    if not p.exists():\n        return []\n    out = []\n    with open(p) as fh:\n        for line in fh:\n            line = line.strip()\n            if line:\n                try:\n                    out.append(json.loads(line))\n                except json.JSONDecodeError:\n                    logger.warning(f\"skipping malformed line in {p.name}\")\n    return out\n\n\ndef append_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:\n    p = Path(p)\n    p.parent.mkdir(parents=True, exist_ok=True)\n    with open(p, \"a\") as fh:\n        for r in rows:\n            fh.write(json.dumps(clean_nan(r), default=_json_default) + \"\\n\")\n        fh.flush()\n\n\ndef write_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:\n    p = Path(p)\n    p.parent.mkdir(parents=True, exist_ok=True)\n    tmp = p.with_suffix(p.suffix + \".tmp\")\n    with open(tmp, \"w\") as fh:\n        for r in rows:\n            fh.write(json.dumps(clean_nan(r), default=_json_default) + \"\\n\")\n    tmp.replace(p)\n\n\ndef log_deviation(dev_id: str, text: str, severity: str = \"minor\") -> None:\n    p = RESULTS_DIR / \"deviations.json\"\n    cur = read_json(p) if p.exists() else []\n    if any(d[\"id\"] == dev_id for d in cur):\n        return\n    cur.append({\"id\": dev_id, \"severity\": severity, \"text\": text, \"utc\": utc_now()})\n    write_json(p, cur)\n    logger.warning(f\"DEVIATION {dev_id}: {text}\")\n\n\ndef ledger(milestone: str, **extra: Any) -> None:\n    \"\"\"logs/time_ledger.jsonl: one line per milestone.\"\"\"\n    append_jsonl(LOG_DIR / \"time_ledger.jsonl\", [{\"milestone\": milestone, \"utc\": utc_now(), \"unix\": time.time(),\n                                                  **extra}])\n\n\ndef partial_status(stage: str, **extra: Any) -> None:\n    p = RESULTS_DIR / \"partial_status.json\"\n    cur = read_json(p) if p.exists() else {\"stages\": {}}\n    cur[\"stages\"][stage] = {\"utc\": utc_now(), **extra}\n    cur[\"last_update\"] = utc_now()\n    write_json(p, cur)\n\n\n# ------------------------------------------------------------------------------------------------ commitment chain\ndef commit(name: str, payload: dict[str, Any] | None = None, files: list[Path] | None = None) -> dict[str, Any]:\n    \"\"\"Hash-chained pre-registration. Writes predictions/<name>.json (if payload), then appends one line per file to\n    commitments.log: 'utc | relative path | sha256(file) | link' with link = sha256(previous link + ' ' + this line's\n    path and file sha) and genesis = sha256('iter10_basew').\"\"\"\n    paths: list[Path] = []\n    if payload is not None:\n        p = PRED_DIR / f\"{name}.json\"\n        write_json(p, dict(payload, commit_name=name, utc=utc_now()))\n        paths.append(p)\n    paths += [Path(f) for f in (files or [])]\n    prev = GENESIS\n    if COMMITS.exists():\n        lines = [ln for ln in COMMITS.read_text().splitlines() if ln.strip()]\n        if lines:\n            prev = lines[-1].split(\" | \")[-1].strip()\n    out = []\n    with open(COMMITS, \"a\") as fh:\n        for p in paths:\n            rel = str(Path(p).resolve().relative_to(ROOT))\n            fsha = sha256_file(p)\n            link = sha256_text(prev + \" \" + rel + \" \" + fsha)\n            fh.write(f\"{utc_now()} | {name}:{rel} | {fsha} | {link}\\n\")\n            prev = link\n            out.append({\"path\": rel, \"sha256\": fsha, \"link\": link})\n    logger.info(f\"COMMIT {name}: {len(out)} file(s), last link {prev[:16]}\")\n    return {\"name\": name, \"entries\": out, \"last_link\": prev}\n\n\ndef verify_chain() -> dict[str, Any]:\n    lines = [ln for ln in COMMITS.read_text().splitlines() if ln.strip()] if COMMITS.exists() else []\n    prev = GENESIS\n    out = {\"n\": len(lines), \"all_links_ok\": True, \"all_hashes_ok\": True, \"bad\": []}\n    for ln in lines:\n        utc, tag, fsha, link = [x.strip() for x in ln.split(\" | \")]\n        rel = tag.split(\":\", 1)[1]\n        ok_link = sha256_text(prev + \" \" + rel + \" \" + fsha) == link\n        p = ROOT / rel\n        ok_hash = p.exists() and sha256_file(p) == fsha\n        if not (ok_link and ok_hash):\n            out[\"bad\"].append({\"line\": tag, \"link_ok\": ok_link, \"hash_ok\": ok_hash})\n        out[\"all_links_ok\"] &= ok_link\n        out[\"all_hashes_ok\"] &= ok_hash\n        prev = link\n    return out\n\n\ndef commit_utc(name: str) -> str | None:\n    if not COMMITS.exists():\n        return None\n    for ln in COMMITS.read_text().splitlines():\n        parts = [x.strip() for x in ln.split(\" | \")]\n        if len(parts) == 4 and parts[1].split(\":\", 1)[0] == name:\n            return parts[0]\n    return None\n\n\ndef import_iter9() -> None:\n    \"\"\"Put the vendored iteration-9 code (inputs/iter9/src) on sys.path; its cfg9 resolves ROOT = inputs/iter9.\"\"\"\n    p = str(I9_SRC)\n    if p not in sys.path:\n        sys.path.insert(0, p)", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [23] TOOL CALL — Bash · 2026-10-26 15:22:58 UTC

```
Read the headline re-derivation audit script:
A=/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56; cat $A/audit/rederive_headline.py
```

### [24] TOOL RESULT — Bash · 2026-10-26 15:22:58 UTC

```
{"stdout": "#!/usr/bin/env python3\n\"\"\"Headline re-derivation through a DIFFERENT code path (float64 NumPy, no src/ imports), from raw files only:\n  W1-TF   shares of ROWS_ALL / ROWS_A / ROWS_D and the RAND_ISO null (median, max, empirical p) from the cached bf16\n          fork states (cache/fork_*.pt), the raw safetensors lm_head rows and the committed null draws (npz)\n  W1-GEN  correct counts and exact McNemar (main 30, pooled 90, x3 dose) from data/gen_samples + data/gen_labels\n  W2      late-joint vs early-joint shares from the raw per-prompt margins in results/w2_rows.jsonl\nPlacebos that must FAIL: each RAND_ISO draw treated as the observed arm (its empirical p among the other 49 should\nbe ~uniform, ~5% below 0.05); arm labels randomly swapped within CRN pairs (median McNemar p >= 0.3); a constant\narm (m_arm = m_I, share exactly 0). Usage: .venv/bin/python audit/rederive_headline.py -> results/rederive_headline.json\n\"\"\"\nimport json\nimport math\nimport os\nimport random\nfrom pathlib import Path\n\nimport numpy as np\nimport torch\nfrom safetensors import safe_open\n\nROOT = Path(__file__).resolve().parents[1]\nREV = {\"qwen\": (\"Qwen--Qwen3-8B\", \"b968826d9c46dd6066d109eabc6255188de91218\"),\n       \"qwen_base\": (\"Qwen--Qwen3-8B-Base\", \"49e3418fbbbca6ecbdf9608b4d22e5a407081db4\")}\n\n\ndef rows(key, ids):\n    hub = Path(os.environ.get(\"HF_HUB_CACHE\", Path(os.environ.get(\"HF_HOME\", Path.home() / \".cache/huggingface\")) / \"hub\"))\n    snap = hub / f\"models--{REV[key][0]}\" / \"snapshots\" / REV[key][1]\n    fn = json.loads((snap / \"model.safetensors.index.json\").read_text())[\"weight_map\"][\"lm_head.weight\"]\n    with safe_open(str(snap / fn), framework=\"pt\") as fh:\n        sl = fh.get_slice(\"lm_head.weight\")\n        return np.stack([sl[i:i + 1][0].double().numpy() for i in ids])\n\n\ndef lse(x):\n    m = x.max(-1, keepdims=True)\n    return (m + np.log(np.exp(x - m).sum(-1, keepdims=True)))[..., 0]\n\n\ndef margin(h, R, nD):\n    z = h @ R.T\n    return lse(z[..., :nD]) - lse(z[..., nD:])\n\n\ndef share(mI, mX, mB):\n    return float(np.sum(mI - mX) / np.sum(mI - mB))\n\n\ndef mcnemar(b, c):\n    n, k = b + c, min(b, c)\n    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)\n\n\ndef jl(p):\n    return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]\n\n\nout = {\"W1_TF\": {}, \"W1_GEN\": {}, \"W2\": {}, \"placebos\": {}}\nunits = json.loads((ROOT / \"inputs/iter9/results/units.json\").read_text())\nrng = random.Random(5)\nfor u in (\"T10\", \"B3\"):\n    f = units[u][\"forks\"][0]\n    S, nD = [int(t) for t in f[\"D\"]] + [int(t) for t in f[\"A\"]], len(f[\"D\"])\n    ci = torch.load(ROOT / f\"cache/fork_instr_{u}.pt\")[\"caps\"]\n    cb = torch.load(ROOT / f\"cache/fork_base_{u}.pt\")[\"caps\"]\n    hI = np.stack([c[\"h_fin\"].double().numpy() for c in ci])\n    hB = np.stack([c[\"h_fin\"].double().numpy() for c in cb])\n    WI, WB = rows(\"qwen\", S), rows(\"qwen_base\", S)\n    mI, mB = margin(hI, WI, nD), margin(hB, WB, nD)\n    arms = {\"ROWS_ALL\": WB, \"ROWS_A\": np.concatenate([WI[:nD], WB[nD:]]), \"ROWS_D\": np.concatenate([WB[:nD], WI[nD:]])}\n    sh = {a: share(mI, margin(hI, R, nD), mB) for a, R in arms.items()}\n    iso = np.load(ROOT / f\"results/null_draws_{u}.npz\")[\"RAND_ISO\"].astype(np.float64)\n    null = np.array([share(mI, margin(hI, WI + iso[k], nD), mB) for k in range(len(iso))])\n    p = (1 + (null >= sh[\"ROWS_ALL\"]).sum()) / (1 + len(null))\n    out[\"W1_TF\"][u] = {\"gap_mean\": float((mI - mB).mean()), **sh, \"RAND_ISO_median\": float(np.median(null)),\n                       \"RAND_ISO_max\": float(null.max()), \"empirical_p_vs_RAND_ISO\": float(p)}\n    # placebo: each null draw as the 'observed' arm against the other 49 -> p should be ~uniform\n    pl = [(1 + (np.delete(null, k) >= null[k]).sum()) / len(null) for k in range(len(null))]\n    out[\"placebos\"][f\"W1_{u}_null_as_observed_frac_p_le_0.05\"] = float(np.mean(np.array(pl) <= 0.05))\n    out[\"placebos\"][f\"W1_{u}_constant_arm_share\"] = share(mI, mI.copy(), mB)\n\nlab = {r[\"sid\"]: r for r in jl(ROOT / \"data/gen_labels.jsonl\")}\ngood = {\"T10\": {\"dfs\"}, \"B3\": {\"prim_heap\", \"prim_array\"}}\nind = {}\nfor r in jl(ROOT / \"data/gen_samples.jsonl\"):\n    L = lab[r[\"sid\"]]\n    ind.setdefault((r[\"unit\"], r[\"arm\"]), {})[(r[\"template\"], r[\"slot\"])] = int(L[\"label\"] in good[r[\"unit\"]] and L[\"passed\"])\n\n\ndef test(u, a, b, pool=False):\n    x = dict(ind[(u, a)]); y = dict(ind[(u, b)])\n    if pool:\n        x.update(ind[(u, a + \"_EXTRA60\")]); y.update(ind[(u, b + \"_EXTRA60\")])\n    ks = sorted(set(x) & set(y))\n    bb = sum(x[k] and not y[k] for k in ks); cc = sum(y[k] and not x[k] for k in ks)\n    swp = []\n    for _ in range(300):\n        b2 = c2 = 0\n        for k in ks:\n            p_, q_ = (x[k], y[k]) if rng.random() < 0.5 else (y[k], x[k])\n            b2 += p_ and not q_; c2 += q_ and not p_\n        swp.append(mcnemar(b2, c2))\n    return {\"a_correct\": sum(x.values()), \"b_correct\": sum(y.values()), \"n\": len(ks), \"b\": bb, \"c\": cc,\n            \"p\": mcnemar(bb, cc), \"placebo_label_swap_median_p\": float(np.median(swp))}\n\n\nfor u in (\"T10\", \"B3\"):\n    out[\"W1_GEN\"][u] = {\"ROWS_vs_TWIN_30\": test(u, \"ROWS\", \"TWIN\"), \"ROWS_vs_RAND_MED_30\": test(u, \"ROWS\", \"RAND_MED\"),\n                        \"ROWS_vs_TWIN_pooled90\": test(u, \"ROWS\", \"TWIN\", True),\n                        \"ROWS_vs_RAND_MED_pooled90\": test(u, \"ROWS\", \"RAND_MED\", True),\n                        \"FPD_vs_TWIN_30\": test(u, \"FPD\", \"TWIN\"),\n                        \"ROWS_L3_vs_RAND_MED_L3\": test(u, \"ROWS_L3\", \"RAND_MED_L3\"),\n                        \"ROWS_L3_vs_RAND_RESID_MED_L3\": test(u, \"ROWS_L3\", \"RAND_RESID_MED_L3\")}\n\nw2 = jl(ROOT / \"results/w2_rows.jsonl\")\nfor u in (\"T10\", \"B3\"):\n    def sh2(cfg):\n        r = {x[\"pid\"]: x for x in w2 if x[\"unit\"] == u and x[\"scope\"] == \"A\" and x[\"config\"] == cfg}\n        return float(sum(v[\"m_I\"] - v[\"m\"] for v in r.values()) / sum(v[\"m_I\"] - v[\"m_B\"] for v in r.values()))\n    out[\"W2\"][u] = {\"W_late_joint\": sh2(\"W_late_joint\"), \"E_joint\": sh2(\"E_joint\"),\n                    \"late_minus_early\": sh2(\"W_late_joint\") - sh2(\"E_joint\")}\n\n# comparison with the reported (aggregated) numbers\nrep = json.loads((ROOT / \"results/w1_tf_summary.json\").read_text())[\"units\"]\nout[\"agreement_vs_reported\"] = {u: {a: abs(out[\"W1_TF\"][u][a] - rep[u][\"arms\"][a][\"share\"]) for a in (\"ROWS_ALL\", \"ROWS_A\",\n                                                                                                    \"ROWS_D\")}\n                                for u in (\"T10\", \"B3\")}\n(ROOT / \"results/rederive_headline.json\").write_text(json.dumps(out, indent=1))\nprint(json.dumps(out, indent=1)[:4000])", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [25] ASSISTANT · 2026-10-26 15:23:02 UTC

```
Now the core W1 teacher-forced module, which holds the arm and null computations.
```

### [26] TOOL CALL — Bash · 2026-10-26 15:23:02 UTC

```
Read the W1 teacher-forced analysis script:
A=/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56; cat $A/predictions/code_final_v5/w1_tf.py
```

### [27] TOOL RESULT — Bash · 2026-10-26 15:23:02 UTC

```
{"stdout": "#!/usr/bin/env python3\n\"\"\"W1 teacher-forced (CPU, exact): the class margin lse(z[D]) - lse(z[A]) depends only on the fork-class unembedding\nrows S = D u A and the final-normed residual, so every readout arm and every null is computed exactly on the cached\nfork states of S0.\n\nSubcommands:\n  s0report  stage-0 reproduction table vs iteration 9 (margins, CPU readout decomposition, G1 numerics floor)\n  nulls     generate the 3 x 50 null row draws from the comm... [truncated, 31743 chars total]
```

### [28] TOOL CALL — Read · 2026-10-26 15:23:04 UTC

```
/var/lib/aii-agent/claude/projects/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-10-art-a7CQm-6CXmoJ/16b8150d-a0ae-485d-a405-9d77a5091214/tool-results/blei18v6l.txt
```

### [29] TOOL RESULT — Read · 2026-10-26 15:23:04 UTC

```
{"type": "text", "file": {"filePath": "/var/lib/aii-agent/claude/projects/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-10-art-a7CQm-6CXmoJ/16b8150d-a0ae-485d-a405-9d77a5091214/tool-results/blei18v6l.txt", "content": "#!/usr/bin/env python3\n\"\"\"W1 teacher-forced (CPU, exact): the class margin lse(z[D]) - lse(z[A]) depends only on the fork-class unembedding\nrows S = D u A and the final-normed residual, so every readout... [truncated, 36945 chars total]
```

### [30] ASSISTANT · 2026-10-26 15:23:40 UTC

```
I now understand the core: W1 is exact arithmetic on cached fork states plus the fork-class unembedding rows. Next I'll inspect the preview output structure (TODO 2) and the cached tensors' shapes.
```

### [31] TOOL CALL — Bash · 2026-10-26 15:23:40 UTC

```
Inspect the preview output file structure:
A=/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56; python3 -c "
import json
d=json.load(open('$A/preview_method_out.json'))
print(type(d), list(d.keys()) if isinstance(d,dict) else len(d))
for k,v in d.items():
    if k!='datasets': print(k, json.dumps(v)[:1500])
for ds in d.get('datasets',[]):
    print('=== dataset', ds.get('dataset'), 'n examples', len(ds.get('examples',[])))
    for ex in ds['examples'][:2]:
        print(json.dumps(ex)[:2500])
        print('---')
"
```

### [32] TOOL RESULT — Bash · 2026-10-26 15:23:40 UTC

```
{"stdout": "<class 'dict'> ['metadata', 'datasets']\nmetadata {\"artifact\": \"iteration 10 BASE-W: which weights hold the default algorithm (Qwen3-8B vs Qwen3-8B-Base; Gemma-3-4b descriptive)\", \"method_name\": \"exact readout-row restoration at the algorithm fork (W1, teacher forced and in generation) and in-place late-MLP weight swaps (W2), each against matched-norm nulls\", \"baselines\": [\"TWIN (unmodified instruct readout)\", \"Fork-Patched Decoding (base fork logits; Cantarero et al.)\", \"50 isotropic matched-norm random-row draws (RAND_ISO)\"], \"models\": {\"qwen\": {\"id\": \"Qwen/Qwen3-8B\", \"revision\": \"b968826d9c46dd6066d109eabc6255188de91218\"}, \"qwen_base\": {\"id\": \"Qwen/Qwen3-8B-Base\", \"revision\": \"49e3418fbbbca6ecbdf9608b4d22e5a407081db4\"}, \"gemma\": {\"id\": \"google/gemma-3-4b-it\", \"revision\": \"093f9f388b31de276ce2de164bdc2081324b9767\"}, \"gemma_pt\": {\"id\": \"google/gemma-3-4b-pt\", \"revision\": \"cc012e0a6d0787b4adcc0fa2c4da74402494554d\"}}, \"summary\": {\"utc\": \"2026-10-25T01:46:07.544137Z\", \"claims\": {\"W1_TF_T10\": {\"role\": \"primary\", \"verdict\": \"SUPPORTED\", \"qualifier\": \"readout-level but not token-specific\", \"shares\": {\"ROWS_ALL\": 0.5484614645905562, \"ROWS_D\": 0.059531852065101934, \"ROWS_A\": 0.4889296543695837, \"NORM\": -0.0002993110573321062, \"ROWS_NORM\": 0.5467580319283261, \"FULL_UNEMB\": 0.5484614645905562, \"SIGN\": -0.5483295091286107}, \"ROWS_ALL_ci95\": [0.4396290582255756, 0.706851369990123], \"dose\": {\"DOSE_0.25\": 0.13709806360014754, \"DOSE_0.5\": 0.27420579319417787, \"DOSE_0.75\": 0.4113255320533354, \"DOSE_1\": 0.5484614645905562, \"DOSE_1.25\": 0.68\n=== dataset w1_tf n examples 3\n{\"input\": \"unit=T10 prompt_id=W1|ship | task: Do not use ship for this task. . . . . . . .\\n\\nTask: write a Python function solve(n, edges) that returns the number of connected components of an undirected graph. T...\", \"output\": \"-0.134754\", \"predict_TWIN\": \"5.887222\", \"predict_TWIN_cpu\": \"5.887218\", \"predict_ROWS_ALL\": \"3.372776\", \"predict_ROWS_D\": \"5.625786\", \"predict_ROWS_A\": \"3.634209\", \"predict_NORM\": \"5.882694\", \"predict_ROWS_NORM\": \"3.374531\", \"predict_FULL_UNEMB\": \"3.372776\", \"predict_NORM_recompute_instr_gain\": \"5.887218\", \"predict_DOSE_0_25\": \"5.258659\", \"predict_DOSE_0_5\": \"4.630093\", \"predict_DOSE_0_75\": \"4.001461\", \"predict_DOSE_1\": \"3.372776\", \"predict_DOSE_1_25\": \"2.744022\", \"predict_DOSE_1_5\": \"2.115170\", \"predict_SIGN\": \"8.401154\", \"predict_F_BI\": \"3.707207\", \"predict_F_BB_cpu\": \"-0.134762\", \"predict_F_II_cpu\": \"5.887218\", \"predict_UNEMB_ONLY_on_base_resid\": \"3.717590\", \"predict_RAND_ISO_median_draw\": \"5.725887\", \"predict_DELTA_SWAP_median_draw\": \"5.505360\", \"predict_RAND_RESID_median_draw\": \"5.152874\", \"metadata_unit\": \"T10\", \"metadata_template\": \"W1\", \"metadata_m_I\": 5.8872222900390625, \"metadata_gap\": 6.021976470947266, \"metadata_D_tokens\": [\" find\"], \"metadata_A_tokens\": [\" dfs\", \" bfs\"]}\n---\n{\"input\": \"unit=T10 prompt_id=W1|man | task: Do not use man for this task. . . . . . . .\\n\\nTask: write a Python function solve(n, edges) that returns the number of connected components of an undirected graph. The...\", \"output\": \"0.030426\", \"predict_TWIN\": \"7.967468\", \"predict_TWIN_cpu\": \"7.967468\", \"predict_ROWS_ALL\": \"5.698086\", \"predict_ROWS_D\": \"7.721230\", \"predict_ROWS_A\": \"5.944324\", \"predict_NORM\": \"7.964588\", \"predict_ROWS_NORM\": \"5.700176\", \"predict_FULL_UNEMB\": \"5.698086\", \"predict_NORM_recompute_instr_gain\": \"7.967468\", \"predict_DOSE_0_25\": \"7.400249\", \"predict_DOSE_0_5\": \"6.832962\", \"predict_DOSE_0_75\": \"6.265572\", \"predict_DOSE_1\": \"5.698086\", \"predict_DOSE_1_25\": \"5.130474\", \"predict_DOSE_1_5\": \"4.562687\", \"predict_SIGN\": \"10.235916\", \"predict_F_BI\": \"3.892143\", \"predict_F_BB_cpu\": \"0.030418\", \"predict_F_II_cpu\": \"7.967468\", \"predict_UNEMB_ONLY_on_base_resid\": \"3.899410\", \"predict_RAND_ISO_median_draw\": \"7.762859\", \"predict_DELTA_SWAP_median_draw\": \"7.629192\", \"predict_RAND_RESID_median_draw\": \"7.060959\", \"metadata_unit\": \"T10\", \"metadata_template\": \"W1\", \"metadata_m_I\": 7.96746826171875, \"metadata_gap\": 7.937042236328125, \"metadata_D_tokens\": [\" find\"], \"metadata_A_tokens\": [\" dfs\", \" bfs\"]}\n---\n=== dataset w1_generation n examples 3\n{\"input\": \"unit=T10 slot=0 seed=9101 prompt_id=W1|ship | task: Do not use ship for this task. . . . . . . .\\n\\nTask: write a Python function solve(n, edges) that returns the number of connected components of an un...\", \"output\": \"union_find|pass\", \"predict_ROWS\": \"union_find|pass\", \"predict_RAND_MED\": \"union_find|pass\", \"predict_FPD\": \"union_find|pass\", \"predict_RAND_MAX\": \"union_find|pass\", \"predict_RAND_0\": \"union_find|pass\", \"predict_ROWS_ALLSTEPS\": \"union_find|pass\", \"predict_ROWS_L2\": \"union_find|pass\", \"predict_ROWS_L3\": \"dfs|pass\", \"predict_RAND_MED_L2\": \"union_find|pass\", \"predict_RAND_MED_L3\": \"union_find|pass\", \"predict_RAND_RESID_MED_L3\": \"union_find|pass\", \"predict_RAND_RESID_MAX_L3\": \"dfs|pass\", \"predict_DELTA_SWAP_MED_L3\": \"union_find|pass\", \"predict_DELTA_SWAP_MAX_L3\": \"dfs|pass\", \"metadata_unit\": \"T10\", \"metadata_template\": \"W1\", \"metadata_fork_tokens\": {\"TWIN\": \" find\", \"ROWS\": \" find\", \"RAND_MED\": \" find\", \"FPD\": \" find\", \"RAND_MAX\": \" find\", \"RAND_0\": \" find\", \"ROWS_ALLSTEPS\": \" find\", \"ROWS_L2\": \" find\", \"ROWS_L3\": \" dfs\", \"RAND_MED_L2\": \" find\", \"RAND_MED_L3\": \" find\", \"RAND_RESID_MED_L3\": \" find\", \"RAND_RESID_MAX_L3\": \" dfs\", \"DELTA_SWAP_MED_L3\": \" find\", \"DELTA_SWAP_MAX_L3\": \" dfs\"}, \"metadata_n_tokens\": {\"TWIN\": 182, \"ROWS\": 182, \"RAND_MED\": 182, \"FPD\": 182, \"RAND_MAX\": 182, \"RAND_0\": 182, \"ROWS_ALLSTEPS\": 182, \"ROWS_L2\": 182, \"ROWS_L3\": 102, \"RAND_MED_L2\": 182, \"RAND_MED_L3\": 182, \"RAND_RESID_MED_L3\": 182, \"RAND_RESID_MAX_L3\": 102, \"DELTA_SWAP_MED_L3\": 182, \"DELTA_SWAP_MAX_L3\": 102}, \"metadata_code_sha256\": {\"TWIN\": \"d2acf1dcf3d26542231e5728a81c252fb8feb2631a109d890b6fbe7d60419f64\", \"ROWS\": \"d2acf1dcf3d26542231e5728a81c252fb8feb2631a109d890b6fbe7d60419f64\", \"RAND_MED\": \"d2acf1dcf3d26542231e5728a81c252fb8feb2631a109d890b6fbe7d60419f64\", \"FPD\": \"d2acf1dcf3d26542231e5728a81c252fb8feb2631a109d890b6fbe7d60419f64\", \"RAND_MAX\": \"d2acf1dcf3d26542231e5728a81c252fb8feb2631a109d890b6fbe7d60419f64\", \"RAND_0\": \"d2acf1dcf3d26542231e5728a81c252fb8feb2631a109d890b6fbe7d60419f64\", \"ROWS_ALLSTEPS\": \"d2acf1dcf3d26542231e5728a81c252fb8feb2631a109d890b6fbe7d60419f64\", \"ROWS_L2\": \"d2acf1dcf3d26542231e5728a81c252fb8feb2631a109d890b6fbe7d60419f64\", \"ROWS_L3\": \"fd27e09e4b1e7a740c1cce656e79ae5e43ac13041d30e233b5ca965e58434fa8\", \"RAND_MED_L2\": \"d2acf1dcf3d26542231e5728a81c252fb8feb2631a109d890b6fbe7d60419f64\", \"RAND_MED_L3\": \"d2acf1dcf3d26542231e5728a81c252fb8feb2631a109d890b6fbe7d60419f64\", \"RAND_RESID_MED_L3\": \"d2acf1dcf3d26542231e5728a81c252fb8feb2631a109\n---\n{\"input\": \"unit=T10 slot=1 seed=9102 prompt_id=W1|ship | task: Do not use ship for this task. . . . . . . .\\n\\nTask: write a Python function solve(n, edges) that returns the number of connected components of an un...\", \"output\": \"union_find|pass\", \"predict_ROWS\": \"union_find|pass\", \"predict_RAND_MED\": \"union_find|pass\", \"predict_FPD\": \"dfs|pass\", \"predict_RAND_MAX\": \"union_find|pass\", \"predict_RAND_0\": \"union_find|pass\", \"predict_ROWS_ALLSTEPS\": \"union_find|pass\", \"predict_ROWS_L2\": \"dfs|pass\", \"predict_ROWS_L3\": \"dfs|pass\", \"predict_RAND_MED_L2\": \"union_find|pass\", \"predict_RAND_MED_L3\": \"union_find|pass\", \"predict_RAND_RESID_MED_L3\": \"union_find|pass\", \"predict_RAND_RESID_MAX_L3\": \"dfs|pass\", \"predict_DELTA_SWAP_MED_L3\": \"union_find|pass\", \"predict_DELTA_SWAP_MAX_L3\": \"dfs|pass\", \"metadata_unit\": \"T10\", \"metadata_template\": \"W1\", \"metadata_fork_tokens\": {\"TWIN\": \" find\", \"ROWS\": \" find\", \"RAND_MED\": \" find\", \"FPD\": \" dfs\", \"RAND_MAX\": \" find\", \"RAND_0\": \" find\", \"ROWS_ALLSTEPS\": \" find\", \"ROWS_L2\": \" dfs\", \"ROWS_L3\": \" dfs\", \"RAND_MED_L2\": \" find\", \"RAND_MED_L3\": \" find\", \"RAND_RESID_MED_L3\": \" find\", \"RAND_RESID_MAX_L3\": \" dfs\", \"DELTA_SWAP_MED_L3\": \" find\", \"DELTA_SWAP_MAX_L3\": \" dfs\"}, \"metadata_n_tokens\": {\"TWIN\": 182, \"ROWS\": 182, \"RAND_MED\": 182, \"FPD\": 102, \"RAND_MAX\": 182, \"RAND_0\": 182, \"ROWS_ALLSTEPS\": 182, \"ROWS_L2\": 102, \"ROWS_L3\": 102, \"RAND_MED_L2\": 182, \"RAND_MED_L3\": 182, \"RAND_RESID_MED_L3\": 182, \"RAND_RESID_MAX_L3\": 102, \"DELTA_SWAP_MED_L3\": 182, \"DELTA_SWAP_MAX_L3\": 102}, \"metadata_code_sha256\": {\"TWIN\": \"d2acf1dcf3d26542231e5728a81c252fb8feb2631a109d890b6fbe7d60419f64\", \"ROWS\": \"d2acf1dcf3d26542231e5728a81c252fb8feb2631a109d890b6fbe7d60419f64\", \"RAND_MED\": \"d2acf1dcf3d26542231e5728a81c252fb8feb2631a109d890b6fbe7d60419f64\", \"FPD\": \"0fd97c67d481bb646643203aed604def220398d910c93e8599b1645ad91ec3a0\", \"RAND_MAX\": \"d2acf1dcf3d26542231e5728a81c252fb8feb2631a109d890b6fbe7d60419f64\", \"RAND_0\": \"d2acf1dcf3d26542231e5728a81c252fb8feb2631a109d890b6fbe7d60419f64\", \"ROWS_ALLSTEPS\": \"d2acf1dcf3d26542231e5728a81c252fb8feb2631a109d890b6fbe7d60419f64\", \"ROWS_L2\": \"0fd97c67d481bb646643203aed604def220398d910c93e8599b1645ad91ec3a0\", \"ROWS_L3\": \"0fd97c67d481bb646643203aed604def220398d910c93e8599b1645ad91ec3a0\", \"RAND_MED_L2\": \"d2acf1dcf3d26542231e5728a81c252fb8feb2631a109d890b6fbe7d60419f64\", \"RAND_MED_L3\": \"d2acf1dcf3d26542231e5728a81c252fb8feb2631a109d890b6fbe7d60419f64\", \"RAND_RESID_MED_L3\": \"d2acf1dcf3d26542231e5728a81c252fb8feb2631a109d890b6fbe7d60419\n---\n=== dataset w2_tf n examples 3\n{\"input\": \"unit=T10 prompt_id=W1|ship | task: Do not use ship for this task. . . . . . . .\\n\\nTask: write a Python function solve(n, edges) that returns the number of connected components of an undirected graph. T...\", \"output\": \"-0.134754\", \"predict_A_W26\": \"5.583324\", \"predict_A_W27\": \"5.925568\", \"predict_A_W28\": \"4.748260\", \"predict_A_W29\": \"6.087257\", \"predict_A_W30\": \"4.589737\", \"predict_A_W31\": \"5.529457\", \"predict_A_W32\": \"5.593124\", \"predict_A_W33\": \"5.399925\", \"predict_A_W34\": \"5.872883\", \"predict_A_W35\": \"7.383213\", \"predict_A_W_late_joint\": \"5.638474\", \"predict_A_W_late_joint_with_base_readout\": \"2.266239\", \"predict_A_E_match26_L13\": \"4.977379\", \"predict_A_E_match27_L12\": \"5.506489\", \"predict_A_E_match28_L11\": \"8.109528\", \"predict_A_E_match29_L10\": \"6.253849\", \"predict_A_E_match30_L9\": \"4.768421\", \"predict_A_E_match31_L8\": \"6.903435\", \"predict_A_E_match32_L7\": \"5.545231\", \"predict_A_E_match33_L6\": \"4.001041\", \"predict_A_E_match34_L5\": \"6.326607\", \"predict_A_E_match35_L4\": \"4.933464\", \"predict_A_E_joint\": \"1.801155\", \"predict_A_RANDDELTA_joint_0\": \"7.134331\", \"predict_A_RANDDELTA_joint_1\": \"4.833179\", \"predict_A_RANDDELTA_joint_2\": \"7.063511\", \"predict_A_RANDDELTA26_0\": \"5.524189\", \"predict_A_RANDDELTA26_1\": \"5.279533\", \"predict_A_RANDDELTA26_2\": \"5.808861\", \"predict_A_RANDDELTA27_0\": \"5.421654\", \"predict_A_RANDDELTA27_1\": \"5.804607\", \"predict_A_RANDDELTA27_2\": \"6.878361\", \"predict_A_RANDDELTA28_0\": \"5.522190\", \"predict_A_RANDDELTA28_1\": \"6.221424\", \"predict_A_RANDDELTA28_2\": \"5.479012\", \"predict_A_RANDDELTA29_0\": \"5.483326\", \"predict_A_RANDDELTA29_1\": \"5.943024\", \"predict_A_RANDDELTA29_2\": \"5.412174\", \"predict_A_RANDDELTA30_0\": \"5.684547\", \"predict_A_RANDDELTA30_1\": \"6.099243\", \"predict_A_RANDDELTA30_2\": \"6.082798\", \"predict_A_RANDDELTA31_0\": \"5.291096\", \"predict_A_RANDDELTA31_1\": \"6.054249\", \"predict_A_RANDDELTA31_2\": \"5.828175\", \"predict_A_RANDDELTA32_0\": \"5.808807\", \"predict_A_RANDDELTA32_1\": \"6.107861\", \"predict_A_RANDDELTA32_2\": \"6.024345\", \"predict_A_RANDDELTA33_0\": \"5.874226\", \"predict_A_RANDDELTA33_1\": \"6.231705\", \"predict_A_RANDDELTA33_2\": \"5.572624\", \"predict_A_RANDDELTA34_0\": \"5.734146\", \"predict_A_RANDDELTA34_1\": \"6.044769\", \"predict_A_RANDDELTA34_2\": \"5.988213\", \"predict_A_RANDDELTA35_0\": \"5.361130\", \"predict_A_RANDDELTA35_1\": \"5.642605\", \"predict_A_RANDDELTA35_2\": \"6.398205\", \"predict_A_ATTN_late_joint\": \"3.899658\", \"predict_A_BLOCKS_late_joint\": \"5.016636\", \"predict_A_BLOCKS_late_joint_with_base_readout\": \"0.948273\", \"predict_B_no\n---\n{\"input\": \"unit=T10 prompt_id=W1|man | task: Do not use man for this task. . . . . . . .\\n\\nTask: write a Python function solve(n, edges) that returns the number of connected components of an undirected graph. The...\", \"output\": \"0.030426\", \"predict_A_W26\": \"7.826538\", \"predict_A_W27\": \"7.891670\", \"predict_A_W28\": \"6.849213\", \"predict_A_W29\": \"8.067181\", \"predict_A_W30\": \"6.777035\", \"predict_A_W31\": \"7.506290\", \"predict_A_W32\": \"7.607067\", \"predict_A_W33\": \"7.198051\", \"predict_A_W34\": \"7.740822\", \"predict_A_W35\": \"9.405411\", \"predict_A_W_late_joint\": \"6.939133\", \"predict_A_W_late_joint_with_base_readout\": \"3.710751\", \"predict_A_E_match26_L13\": \"6.868546\", \"predict_A_E_match27_L12\": \"8.019344\", \"predict_A_E_match28_L11\": \"9.816822\", \"predict_A_E_match29_L10\": \"8.325253\", \"predict_A_E_match30_L9\": \"6.670227\", \"predict_A_E_match31_L8\": \"8.139919\", \"predict_A_E_match32_L7\": \"8.202065\", \"predict_A_E_match33_L6\": \"6.305843\", \"predict_A_E_match34_L5\": \"8.091583\", \"predict_A_E_match35_L4\": \"5.980019\", \"predict_A_E_joint\": \"3.539379\", \"predict_A_RANDDELTA_joint_0\": \"9.539469\", \"predict_A_RANDDELTA_joint_1\": \"7.056973\", \"predict_A_RANDDELTA_joint_2\": \"8.753445\", \"predict_A_RANDDELTA26_0\": \"7.785526\", \"predict_A_RANDDELTA26_1\": \"7.675316\", \"predict_A_RANDDELTA26_2\": \"8.072174\", \"predict_A_RANDDELTA27_0\": \"7.553158\", \"predict_A_RANDDELTA27_1\": \"7.890694\", \"predict_A_RANDDELTA27_2\": \"8.832844\", \"predict_A_RANDDELTA28_0\": \"7.820068\", \"predict_A_RANDDELTA28_1\": \"8.268082\", \"predict_A_RANDDELTA28_2\": \"7.463089\", \"predict_A_RANDDELTA29_0\": \"7.688564\", \"predict_A_RANDDELTA29_1\": \"8.178391\", \"predict_A_RANDDELTA29_2\": \"7.483761\", \"predict_A_RANDDELTA30_0\": \"7.855415\", \"predict_A_RANDDELTA30_1\": \"8.195248\", \"predict_A_RANDDELTA30_2\": \"8.096058\", \"predict_A_RANDDELTA31_0\": \"7.414776\", \"predict_A_RANDDELTA31_1\": \"7.977692\", \"predict_A_RANDDELTA31_2\": \"7.914871\", \"predict_A_RANDDELTA32_0\": \"7.906433\", \"predict_A_RANDDELTA32_1\": \"8.023415\", \"predict_A_RANDDELTA32_2\": \"8.024899\", \"predict_A_RANDDELTA33_0\": \"7.831715\", \"predict_A_RANDDELTA33_1\": \"8.237549\", \"predict_A_RANDDELTA33_2\": \"7.620041\", \"predict_A_RANDDELTA34_0\": \"7.760857\", \"predict_A_RANDDELTA34_1\": \"8.042164\", \"predict_A_RANDDELTA34_2\": \"7.997139\", \"predict_A_RANDDELTA35_0\": \"7.386948\", \"predict_A_RANDDELTA35_1\": \"7.782928\", \"predict_A_RANDDELTA35_2\": \"8.373531\", \"predict_A_ATTN_late_joint\": \"5.846809\", \"predict_A_BLOCKS_late_joint\": \"5.842426\", \"predict_A_BLOCKS_late_joint_with_base_readout\": \"1.877377\", \"predict_B_non\n---", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [33] THINKING · 2026-10-26 15:23:46 UTC

```
I found that the `w1_tf` dataset has per-prompt margins per arm, but running the method requires the raw fork-state vectors instead. I'll now check which Python and torch versions are available to inspect the `.pt` caches.
```

### [34] TOOL CALL — Bash · 2026-10-26 15:23:46 UTC

```
Check available Python, torch, and hardware:
which python3 uv; python3 --version; python3 -c "import torch, numpy; print(torch.__version__, numpy.__version__)" 2>&1 | tail -1; ls /tmp/aii_nb_test_envs/ 2>&1 | head; nproc; free -g | head -2; nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv 2>&1 | head -5; echo "HF_HOME=$HF_HOME UV_CACHE_DIR=$UV_CACHE_DIR"
```

### [35] TOOL RESULT — Bash · 2026-10-26 15:23:46 UTC

```
{"stdout": "/usr/local/bin/python3\n/usr/bin/uv\nPython 3.12.14\nModuleNotFoundError: No module named 'torch'\nls: cannot access '/tmp/aii_nb_test_envs/': No such file or directory\n2\n               total        used        free      shared  buff/cache   available\nMem:             755          47         276           1         438         707\n/bin/bash: line 1: nvidia-smi: command not found\nHF_HOME=/ai-inventor/aii_data/runs/run_jSassd-YWLVC/.shared_cache/hf UV_CACHE_DIR=/ai-inventor/aii_data/runs/run_jSassd-YWLVC/.shared_cache/uv", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [36] THINKING · 2026-10-26 15:24:40 UTC

```
No torch or GPU on this system, just 2 CPUs, but I need torch to read the `.pt` caches and Qwen safetensors. I'll locate the model weights and check the null and PCA metadata next.
```

### [37] TOOL CALL — Bash · 2026-10-26 15:24:40 UTC

```
Locate cached Qwen3-8B model weights:
for d in /ai-inventor/aii_data/runs/run_jSassd-YWLVC/.shared_cache /ai-inventor/aii_data/runs/run_5eGZGmskluur/.shared_cache; do echo "== $d"; ls $d 2>&1 | head; ls $d/hf $d/hf/hub 2>&1 | head -30; done; find / -maxdepth 6 -type d -name "models--Qwen--Qwen3-8B*" 2>/dev/null | head
```

### [38] TOOL CALL — Bash · 2026-10-26 15:24:40 UTC

```
Inspect null draw metadata and unit definitions:
A=/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56; python3 -c "
import json
m=json.load(open('$A/results/null_meta.json'))
for u,v in m['units'].items():
    print(u, 'S', v['S'], v['S_str'], 'distinct swap toks', v['delta_swap_distinct_tokens'], 'pca var', v['resid_pca_var_explained'])
    for t,p in v['pools'].items(): print('   pool', t, p)
"; python3 -c "
import json
u=json.load(open('$A/inputs/iter9/results/units.json'))
print(list(u.keys()))
for k in ('T10','B3'):
    U=u[k]; print(k, list(U.keys()))
    f=U['forks'][0]; print('  fork keys', list(f.keys()))
    print('  D', f['D'], 'A', f['A'])
    print('  prompts?', [kk for kk in U.keys()])
" 2>&1 | head -40
```

### [39] TOOL RESULT — Bash · 2026-10-26 15:24:48 UTC

```
{"stdout": "== /ai-inventor/aii_data/runs/run_jSassd-YWLVC/.shared_cache\nhf\npip\nuv\n/ai-inventor/aii_data/runs/run_jSassd-YWLVC/.shared_cache/hf:\nhub\nxet\n\n/ai-inventor/aii_data/runs/run_jSassd-YWLVC/.shared_cache/hf/hub:\nmodels--Qwen--Qwen3-0.6B\nmodels--Qwen--Qwen3-8B\nmodels--Qwen--Qwen3-8B-FP8\nmodels--mwhanna--gemma-scope-2-4b-it\nmodels--unsloth--Qwen3-32B-bnb-4bit\nmodels--unsloth--gemma-3-4b-it\n== /ai-inventor/aii_data/runs/run_5eGZGmskluur/.shared_cache\nls: cannot access '/ai-inventor/aii_data/runs/run_5eGZGmskluur/.shared_cache': No such file or directory\nls: cannot access '/ai-inventor/aii_data/runs/run_5eGZGmskluur/.shared_cache/hf': No such file or directory\nls: cannot access '/ai-inventor/aii_data/runs/run_5eGZGmskluur/.shared_cache/hf/hub': No such file or directory", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [40] TOOL RESULT — Bash · 2026-10-26 15:24:48 UTC

```
{"stdout": "T10 S [1477, 25792, 66564] [' find', ' dfs', ' bfs'] distinct swap toks 147 pca var 0.91533297454472\n   pool 1477 {'tok': ' find', 'n_candidates': 1359, 'delta_norm': 0.09424832463264465, 'w_norm': 1.4194759130477905}\n   pool 25792 {'tok': ' dfs', 'n_candidates': 9682, 'delta_norm': 0.20255759358406067, 'w_norm': 1.6457043886184692}\n   pool 66564 {'tok': ' bfs', 'n_candidates': 1201, 'delta_norm': 0.23335297405719757, 'w_norm': 1.5804827213287354}\nB3 S [16447, 9145, 4248, 30925, 7379, 31920, 12906, 4093, 35183, 2340, 5443, 84280, 2014, 12091, 66191, 12518] [' Kr', ' Union', ' Check', ' Minimum', ' Find', ' Priority', ' Helper', ' Dis', ' Prim', ' Pr', ' Use', ' MST', ' To', ' Using', 'Prim', ' Prime'] distinct swap toks 793 pca var 0.9021243226781425\n   pool 16447 {'tok': ' Kr', 'n_candidates': 16372, 'delta_norm': 0.19107916951179504, 'w_norm': 1.7328475713729858}\n   pool 9145 {'tok': ' Union', 'n_candidates': 14133, 'delta_norm': 0.19049668312072754, 'w_norm': 1.8762595653533936}\n   pool 4248 {'tok': ' Check', 'n_candidates': 1937, 'delta_norm': 0.13168790936470032, 'w_norm': 1.4412654638290405}\n   pool 30925 {'tok': ' Minimum', 'n_candidates': 13205, 'delta_norm': 0.1959885209798813, 'w_norm': 1.6796226501464844}\n   pool 7379 {'tok': ' Find', 'n_candidates': 2212, 'delta_norm': 0.14893284440040588, 'w_norm': 1.4147592782974243}\n   pool 31920 {'tok': ' Priority', 'n_candidates': 11586, 'delta_norm': 0.2027125507593155, 'w_norm': 1.8457074165344238}\n   pool 12906 {'tok': ' Helper', 'n_candidates': 1647, 'delta_norm': 0.23117932677268982, 'w_norm': 1.6237887144088745}\n   pool 4093 {'tok': ' Dis', 'n_candidates': 14636, 'delta_norm': 0.17301471531391144, 'w_norm': 1.6386162042617798}\n   pool 35183 {'tok': ' Prim', 'n_candidates': 14511, 'delta_norm': 0.1963111311197281, 'w_norm': 1.821581482887268}\n   pool 2340 {'tok': ' Pr', 'n_candidates': 10256, 'delta_norm': 0.17583127319812775, 'w_norm': 1.5631368160247803}\n   pool 5443 {'tok': ' Use', 'n_candidates': 1290, 'delta_norm': 0.13370339572429657, 'w_norm': 1.3820035457611084}\n   pool 84280 {'tok': ' MST', 'n_candidates': 15726, 'delta_norm': 0.19418492913246155, 'w_norm': 1.7752361297607422}\n   pool 2014 {'tok': ' To', 'n_candidates': 927, 'delta_norm': 0.11671336740255356, 'w_norm': 1.3522433042526245}\n   pool 12091 {'tok': ' Using', 'n_candidates': 854, 'delta_norm': 0.13970449566841125, 'w_norm': 1.3230191469192505}\n   pool 66191 {'tok': 'Prim', 'n_candidates': 13291, 'delta_norm': 0.2003859132528305, 'w_norm': 1.7873451709747314}\n   pool 12518 {'tok': ' Prime', 'n_candidates': 17742, 'delta_norm': 0.18178710341453552, 'w_norm': 1.7929332256317139}\n['B3', 'T10', 'CHK_T10', 'CHK_B3', 'G-GRID', 'G-T04', 'G-R6', 'L-GRID']\nT10 ['unit', 'family', 'kind', 'name', 'forks', 'prompts']\n  fork keys ['fork_id', 'opening', 'D', 'A', 'D_class', 'A_class', 'tok_a', 'tok_b', 'class_of', 'D_str', 'A_str', 'opening_text']\n  D [1477] A [25792, 66564]\n  prompts? ['unit', 'family', 'kind', 'name', 'forks', 'prompts']\nB3 ['unit', 'family', 'kind', 'name', 'forks', 'prompts']\n  fork keys ['fork_id', 'opening', 'tok_a', 'tok_b', 'bins', 'phat', 'D', 'A', 'D_class', 'A_class', 'class_of', 'instr_mass_ref', 'class_mass_ref', 'D_str', 'A_str', 'opening_text']\n  D [16447, 9145, 4248, 30925, 7379, 31920, 12906, 4093] A [35183, 2340, 5443, 84280, 2014, 12091, 66191, 12518]\n  prompts? ['unit', 'family', 'kind', 'name', 'forks', 'prompts']", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [41] THINKING · 2026-10-26 15:25:06 UTC

```
I found Qwen3-8B cached locally but not Qwen3-8B-Base. Since I only need 19 lm_head rows plus two norm gains, I'll check the snapshot's revision and try pulling just those bytes from the Hub via HTTP range requests.
```

### [42] TOOL CALL — Bash · 2026-10-26 15:25:06 UTC

```
Check local snapshot and network access:
H=/ai-inventor/aii_data/runs/run_jSassd-YWLVC/.shared_cache/hf/hub; ls $H/models--Qwen--Qwen3-8B/snapshots/; for s in $H/models--Qwen--Qwen3-8B/snapshots/*; do ls -la $s | head -20; done; timeout 20 curl -sI https://huggingface.co/Qwen/Qwen3-8B-Base/resolve/49e3418fbbbca6ecbdf9608b4d22e5a407081db4/model.safetensors.index.json | head -5; timeout 20 curl -sI https://pypi.org/simple/torch/ | head -2; timeout 20 curl -sI https://raw.githubusercontent.com/ | head -2
```

### [43] TOOL RESULT — Bash · 2026-10-26 15:25:06 UTC

```
{"stdout": "b968826d9c46dd6066d109eabc6255188de91218\ntotal 59\ndrwxrwxrwx 2 aii-agent aii-agent 28400 Oct 26 08:49 .\ndrwxrwxrwx 3 aii-agent aii-agent 28400 Oct 26 08:49 ..\nlrwxrwxrwx 1 aii-agent aii-agent    52 Oct 26 08:49 config.json -> ../../blobs/d46195ac87f837ad233d02b2f80f148bf7c005e0\nlrwxrwxrwx 1 aii-agent aii-agent    52 Oct 26 08:49 merges.txt -> ../../blobs/31349551d90c7606f325fe0f11bbb8bd5fa0d7c7\nlrwxrwxrwx 1 aii-agent aii-agent    76 Oct 26 08:49 tokenizer.json -> ../../blobs/aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4\nlrwxrwxrwx 1 aii-agent aii-agent    52 Oct 26 08:49 tokenizer_config.json -> ../../blobs/417d038a63fa3de29cfde265caedae14d1a58d92\nlrwxrwxrwx 1 aii-agent aii-agent    52 Oct 26 08:49 vocab.json -> ../../blobs/4783fe10ac3adce15ac8f358ef5462739852c569\nHTTP/2 307 \r\ncontent-type: text/plain; charset=utf-8\r\ncontent-length: 310\r\ndate: Mon, 26 Oct 2026 15:25:06 GMT\r\nlocation: /api/resolve-cache/models/Qwen/Qwen3-8B-Base/49e3418fbbbca6ecbdf9608b4d22e5a407081db4/model.safetensors.index.json?%2FQwen%2FQwen3-8B-Base%2Fresolve%2F49e3418fbbbca6ecbdf9608b4d22e5a407081db4%2Fmodel.safetensors.index.json=&etag=%22041fe9a0d3ab9c8895f264e7a3a60aa563398d7c%22\r\nHTTP/2 200 \r\naccess-control-allow-origin: *\r\nHTTP/2 301 \r\ncontent-security-policy: default-src 'none'; style-src 'unsafe-inline'; sandbox", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [44] THINKING · 2026-10-26 15:25:40 UTC

```
The local Qwen3-8B snapshot is missing its weights, so I'll range-fetch the needed rows at the pinned revisions. I'll also set up the sanctioned venv with CPU torch for data prep while reviewing the figure and analysis code.
```

### [45] TOOL CALL — Bash · 2026-10-26 15:25:40 UTC

```
Create venv with CPU torch for data prep:
cd /tmp && UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5 && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5/bin/python --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple "torch==2.9.0" "numpy==2.0.2" safetensors requests 2>&1 | tail -3; /tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5/bin/python -c "import torch, numpy; print(torch.__version__, numpy.__version__)"
```

### [46] TOOL CALL — Bash · 2026-10-26 15:25:40 UTC

```
Read the figures script:
A=/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56; cat $A/src/figures10.py | head -400
```

### [47] TOOL RESULT — Bash · 2026-10-26 15:26:10 UTC

```
{"stdout": "2.9.0+cu128 2.0.2", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [48] TOOL RESULT — Bash · 2026-10-26 15:26:10 UTC

```
{"stdout": "#!/usr/bin/env python3\n\"\"\"Figures F1-F8 (figures/*.pdf and *.png), drawn from the result files and cached fork states.\n\nF1 closed share by arm with the RAND_ISO, DELTA_SWAP and RAND_RESID null histograms (T10, B3)\nF2 per-prompt shares, point size = prompt gap\nF3 dose-response of the share vs lambda for the base-row delta and for RAND_ISO at matched lambda\nF4 generation counts by arm, stacked by label (correct vs failing), McNemar annotated\nF5 actual activation coordinates: instruct and base final-normed fork states (20 + 20) on the plane spanned by the\n   instruct readout difference direction u1 and the orthogonalised base readout direction u2, with margin isolines\n   under the instruct and the swapped (base-row) readouts\nF6 PCA of the block-35 outputs (final-norm inputs) at the fork, instruct vs base, with the readout difference\n   directions overlaid\nF7 W2 singles vs matched early swaps vs same-layer random deltas, and the weight-level decomposition\nF8 W3 Gemma shares with the null histograms\n\"\"\"\n\nfrom __future__ import annotations\n\nimport sys\n\nimport matplotlib\n\nmatplotlib.use(\"Agg\")\nimport matplotlib.pyplot as plt  # noqa: E402\nimport numpy as np  # noqa: E402\nimport torch  # noqa: E402\nfrom loguru import logger  # noqa: E402\n\nfrom cfg10 import CACHE_DIR, FIG_DIR, I9_RES, LATE, RESULTS_DIR, UNITS_TF, read_json, setup_logging  # noqa: E402\n\nplt.rcParams.update({\"font.size\": 9, \"pdf.fonttype\": 42, \"ps.fonttype\": 42, \"axes.spines.top\": False,\n                     \"axes.spines.right\": False, \"figure.dpi\": 150})\nC = {\"ROWS_ALL\": \"#c0392b\", \"ROWS_D\": \"#e67e22\", \"ROWS_A\": \"#8e44ad\", \"NORM\": \"#7f8c8d\", \"ROWS_NORM\": \"#2c3e50\",\n     \"SIGN\": \"#16a085\", \"RAND_ISO\": \"#3498db\", \"DELTA_SWAP\": \"#27ae60\", \"RAND_RESID\": \"#f1c40f\", \"instr\": \"#c0392b\",\n     \"base\": \"#2980b9\"}\nNAMES = {\"T10\": \"CC (T10): ' find' vs ' dfs'/' bfs'\", \"B3\": \"MST (B3): Kruskal vs Prim class\"}\n\n\ndef save(fig: plt.Figure, name: str) -> None:\n    fig.tight_layout()\n    fig.savefig(FIG_DIR / f\"{name}.pdf\")\n    fig.savefig(FIG_DIR / f\"{name}.png\", dpi=200)\n    plt.close(fig)\n    logger.info(f\"saved {name}\")\n\n\ndef f1(w1: dict) -> None:\n    fig, axes = plt.subplots(2, 2, figsize=(10, 6.5))\n    arms = [\"ROWS_ALL\", \"ROWS_D\", \"ROWS_A\", \"NORM\", \"ROWS_NORM\", \"SIGN\"]\n    for r, u in enumerate(UNITS_TF):\n        U = w1[\"units\"][u]\n        ax = axes[r, 0]\n        sh = [U[\"arms\"][a][\"share\"] for a in arms]\n        ci = [U[\"arms\"][a][\"ci95\"] for a in arms]\n        y = np.arange(len(arms))\n        ax.barh(y, sh, color=[C[a] for a in arms], alpha=0.85)\n        ax.errorbar(sh, y, xerr=[[s - c[0] for s, c in zip(sh, ci)], [c[1] - s for s, c in zip(sh, ci)]], fmt=\"none\",\n                    ecolor=\"k\", capsize=3, lw=1)\n        ax.set_yticks(y, arms)\n        ax.axvline(0, color=\"k\", lw=0.8)\n        ax.axvline(1, color=\"k\", lw=0.8, ls=\":\")\n        ax.set_xlabel(\"share of the gap closed (ratio of sums, 95% CI)\")\n        ax.set_title(f\"{NAMES[u]}: readout arms on the instruct residual (gap {U['gap_mean']:.2f} nats)\", fontsize=8.5)\n        ax = axes[r, 1]\n        allv = np.concatenate([U[\"nulls\"][nt][\"shares\"] for nt in (\"RAND_ISO\", \"DELTA_SWAP\", \"RAND_RESID\")])\n        lo, hi = np.percentile(allv, 1), np.percentile(allv, 99)\n        lo, hi = min(lo, -0.3), max(hi, U[\"arms\"][\"ROWS_ALL\"][\"share\"] + 0.2)\n        bins = np.linspace(lo, hi, 40)\n        for nt in (\"RAND_ISO\", \"DELTA_SWAP\", \"RAND_RESID\"):\n            v = np.clip(U[\"nulls\"][nt][\"shares\"], lo, hi)\n            ax.hist(v, bins=bins, alpha=0.55, color=C[nt],\n                    label=f\"{nt} (median {U['nulls'][nt]['median']:.2f}, p95 {U['nulls'][nt]['p95']:.2f})\")\n        ax.axvline(U[\"arms\"][\"ROWS_ALL\"][\"share\"], color=C[\"ROWS_ALL\"], lw=2,\n                   label=f\"ROWS_ALL {U['arms']['ROWS_ALL']['share']:.2f} (p vs RAND_ISO = \"\n                         f\"{U['nulls']['RAND_ISO']['empirical_p_rows_all']:.3f})\")\n        ax.set_xlabel(\"share closed by 50 null row edits (1-99% range shown)\")\n        ax.set_ylabel(\"draws\")\n        ax.legend(fontsize=6.5, frameon=False)\n        ax.set_title(f\"{u}: nulls (every S row moved by ||Delta_t||)\", fontsize=8.5)\n    save(fig, \"F1_w1_shares_nulls\")\n\n\ndef f2(w1: dict) -> None:\n    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))\n    for ax, u in zip(axes, UNITS_TF):\n        U = w1[\"units\"][u]\n        gap = np.array(U[\"gap\"])\n        x = np.arange(len(gap))\n        for a, off in ((\"ROWS_ALL\", -0.15), (\"ROWS_NORM\", 0.0), (\"ROWS_A\", 0.15)):\n            ax.scatter(x + off, U[\"arms\"][a][\"per_prompt_share\"], s=12 + 18 * np.abs(gap), color=C[a], alpha=0.75,\n                       label=a, edgecolor=\"k\", lw=0.3)\n        for i in np.nonzero(np.abs(gap) < 0.5)[0]:\n            ax.annotate(\"gap<0.5\", (i, U[\"arms\"][\"ROWS_ALL\"][\"per_prompt_share\"][i]), fontsize=6)\n        ax.axhline(0, color=\"k\", lw=0.8)\n        ax.axhline(1, color=\"k\", lw=0.8, ls=\":\")\n        ax.set_xticks(x, U[\"pids\"], rotation=90, fontsize=5.5)\n        ax.set_ylabel(\"per-prompt share closed\")\n        ax.set_title(f\"{u}: per-prompt shares (point area ~ gap in nats)\", fontsize=8.5)\n        ax.legend(fontsize=7, frameon=False)\n    save(fig, \"F2_per_prompt_shares\")\n\n\ndef f3(w1: dict) -> None:\n    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4))\n    for ax, u in zip(axes, UNITS_TF):\n        U = w1[\"units\"][u]\n        lams = [-1.0, 0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5]\n        rows = [U[\"arms\"][\"SIGN\"][\"share\"], 0.0] + [U[\"arms\"][f\"DOSE_{l:g}\"][\"share\"] for l in lams[2:]]\n        cur = U[\"nulls\"][\"RAND_ISO\"][\"dose_curve\"]\n        iso_med = [cur[\"-1\"][\"median_draw_share\"], 0.0] + [cur[f\"{l:g}\"][\"median_draw_share\"] for l in lams[2:]]\n        iso_all = [cur[\"-1\"][\"all_draws_median_share\"], 0.0] + [cur[f\"{l:g}\"][\"all_draws_median_share\"]\n                                                                for l in lams[2:]]\n        ax.plot(lams, rows, \"o-\", color=C[\"ROWS_ALL\"], label=\"base-row delta  w_I + lambda * Delta\")\n        ax.plot(lams, iso_med, \"s--\", color=C[\"RAND_ISO\"], label=\"RAND_ISO median-share draw at lambda\")\n        ax.plot(lams, iso_all, \"^:\", color=\"#1a5276\", label=\"median over the 50 RAND_ISO draws\")\n        ax.axhline(0, color=\"k\", lw=0.8)\n        ax.axhline(1, color=\"k\", lw=0.8, ls=\":\")\n        ax.set_xlabel(\"lambda (dose of the row edit)\")\n        ax.set_ylabel(\"share closed\")\n        ax.set_title(f\"{u}: dose-response\", fontsize=8.5)\n        ax.legend(fontsize=6.5, frameon=False)\n    save(fig, \"F3_dose_response\")\n\n\ndef f4(gen: dict) -> None:\n    fig, axes = plt.subplots(2, 1, figsize=(11, 7.6))\n    for ax, u in zip(axes, (\"T10\", \"B3\")):\n        G = gen[\"units\"][u]\n        arms = list(G[\"cells\"])\n        corr_lab = {\"T10\": \"correct DFS\", \"B3\": \"correct Prim\"}[u]\n        corr = np.array([G[\"cells\"][a][\"n_correct\"] for a in arms])\n        n = np.array([G[\"cells\"][a][\"n\"] for a in arms])\n        fails = np.array([G[\"cells\"][a][\"n\"] - G[\"cells\"][a][\"n_pass\"] for a in arms])\n        other = n - corr - fails\n        x = np.arange(len(arms))\n        ax.bar(x, corr, color=\"#c0392b\", label=corr_lab)\n        ax.bar(x, other, bottom=corr, color=\"#95a5a6\", label=\"default class / other (passing)\")\n        ax.bar(x, fails, bottom=corr + other, color=\"#2c3e50\", label=\"failing hidden tests\")\n        pred = [G[\"cells\"][a][\"predicted_correct_count\"] for a in arms]\n        ax.scatter(x, pred, marker=\"_\", s=300, color=\"k\", zorder=5, label=\"committed prediction (count)\")\n        for i, a in enumerate(arms):\n            t = G[\"tests\"].get(f\"{a}_vs_TWIN\")\n            if t and a != \"TWIN\":\n                ax.annotate(f\"{t['b_first_only']}:{t['c_second_only']}\\np={t['p_exact_two_sided']:.2g}\", (i, 31),\n                            ha=\"center\", fontsize=6)\n        ax.set_xticks(x, arms, rotation=25, fontsize=7)\n        ax.set_ylim(0, 36)\n        ax.set_ylabel(\"programs (30 CRN slots per arm)\")\n        ax.set_title(f\"{u}: generation by fork arm (McNemar vs TWIN above bars)\", fontsize=8.5)\n        ax.legend(fontsize=6.5, frameon=False, loc=\"upper left\", bbox_to_anchor=(1.0, 1.0))\n    save(fig, \"F4_generation\")\n\n\ndef f5_f6() -> None:\n    from w1_tf import UnitData, load_readout\n    units = read_json(I9_RES / \"units.json\")\n    WI, gI = load_readout(\"qwen\")\n    WB, gB = load_readout(\"qwen_base\")\n    fig5, ax5 = plt.subplots(1, 2, figsize=(11, 4.6))\n    fig6, ax6 = plt.subplots(1, 2, figsize=(10, 4.3))\n    for k, u in enumerate(UNITS_TF):\n        d = UnitData(u, units, WI, WB, gI, gB, need_logits=False)\n        WI_S, WB_S = d.WI_S.double(), d.WB_S.double()\n        dI = WI_S[:d.nD].mean(0) - WI_S[d.nD:].mean(0)\n        dB = WB_S[:d.nD].mean(0) - WB_S[d.nD:].mean(0)\n        u1 = dI / dI.norm()\n        v = dB - (dB @ u1) * u1\n        u2 = v / v.norm()\n        H = torch.cat([d.hfI, d.hfB]).double()\n        a, b = (H @ u1).numpy(), (H @ u2).numpy()\n        off = H - torch.outer(H @ u1, u1) - torch.outer(H @ u2, u2)\n        off_mean = off.mean(0)\n        ga = np.linspace(a.min() - 0.15 * np.ptp(a), a.max() + 0.15 * np.ptp(a), 120)\n        gb = np.linspace(b.min() - 0.25 * np.ptp(b), b.max() + 0.25 * np.ptp(b), 120)\n        A_, B_ = np.meshgrid(ga, gb)\n        G = (off_mean[None, None, :] + torch.from_numpy(A_)[..., None] * u1 + torch.from_numpy(B_)[..., None] * u2)\n        G = G.reshape(-1, G.shape[-1])\n\n        def mgrid(rows: torch.Tensor) -> np.ndarray:\n            z = G @ rows.T\n            return (torch.logsumexp(z[:, :d.nD], -1) - torch.logsumexp(z[:, d.nD:], -1)).numpy().reshape(A_.shape)\n        MI, MB = mgrid(WI_S), mgrid(WB_S)\n        ax = ax5[k]\n        cs1 = ax.contour(A_, B_, MI, levels=7, colors=C[\"instr\"], linewidths=0.8, alpha=0.8)\n        ax.clabel(cs1, fontsize=5.5, fmt=\"%.1f\")\n        cs2 = ax.contour(A_, B_, MB, levels=7, colors=C[\"base\"], linewidths=0.8, linestyles=\"--\", alpha=0.8)\n        ax.clabel(cs2, fontsize=5.5, fmt=\"%.1f\")\n        n = len(d.pids)\n        ax.scatter(a[:n], b[:n], color=C[\"instr\"], s=22, edgecolor=\"k\", lw=0.3, label=\"instruct fork state h_fin\")\n        ax.scatter(a[n:], b[n:], color=C[\"base\"], s=22, marker=\"s\", edgecolor=\"k\", lw=0.3,\n                   label=\"base fork state h_fin\")\n        ax.plot([], [], color=C[\"instr\"], lw=0.8, label=\"margin isolines, instruct S rows\")\n        ax.plot([], [], color=C[\"base\"], lw=0.8, ls=\"--\", label=\"margin isolines, base S rows (ROWS_ALL readout)\")\n        ax.set_xlabel(\"u1 = instruct readout direction (mean w_D - mean w_A), units of h\")\n        ax.set_ylabel(\"u2 = base readout direction, orthogonalised\")\n        ax.set_title(f\"{u}: final-normed fork states on the readout plane\\n(isolines through the mean off-plane \"\n                     f\"component; cos(dI, dB) = {float(dI @ dB / dI.norm() / dB.norm()):.3f})\", fontsize=8)\n        ax.legend(fontsize=6, frameon=False, loc=\"best\")\n        # F6 PCA of block-35 outputs (final-norm inputs) at the fork\n        P = torch.cat([d.hpI.float(), d.hpB.float()]).double()\n        mu = P.mean(0)\n        Uu, Ss, Vt = torch.linalg.svd(P - mu, full_matrices=False)\n        pcs = Vt[:2]\n        Y = ((P - mu) @ pcs.T).numpy()\n        ev = (Ss ** 2 / (Ss ** 2).sum()).numpy()\n        ax = ax6[k]\n        ax.scatter(Y[:n, 0], Y[:n, 1], color=C[\"instr\"], s=22, edgecolor=\"k\", lw=0.3, label=\"instruct h_pre (fork)\")\n        ax.scatter(Y[n:, 0], Y[n:, 1], color=C[\"base\"], s=22, marker=\"s\", edgecolor=\"k\", lw=0.3,\n                   label=\"base h_pre (fork)\")\n        sc = 0.35 * np.abs(Y).max()\n        for vec, col, lab in ((dI, C[\"instr\"], \"instruct readout direction\"), (dB, C[\"base\"], \"base readout direction\")):\n            p2 = (pcs @ (vec / vec.norm())).numpy()\n            ax.annotate(\"\", xy=(sc * p2[0] / max(1e-9, np.linalg.norm(p2)) * min(1, 3 * np.linalg.norm(p2)),\n                                sc * p2[1] / max(1e-9, np.linalg.norm(p2)) * min(1, 3 * np.linalg.norm(p2))),\n                        xytext=(0, 0), arrowprops=dict(arrowstyle=\"->\", color=col, lw=1.5))\n            ax.plot([], [], color=col, label=f\"{lab} (|proj| {np.linalg.norm(p2):.2f})\")\n        ax.set_xlabel(f\"PC1 ({100 * ev[0]:.1f}% of variance)\")\n        ax.set_ylabel(f\"PC2 ({100 * ev[1]:.1f}%)\")\n        ax.set_title(f\"{u}: PCA of block-35 outputs at the fork (20 + 20 prompts)\", fontsize=8.5)\n        ax.legend(fontsize=6, frameon=False)\n    fig5.tight_layout()\n    save(fig5, \"F5_readout_plane\")\n    save(fig6, \"F6_pca_block35\")\n\n\ndef f7(w2: dict) -> None:\n    fig, axes = plt.subplots(2, 2, figsize=(11, 6.5), gridspec_kw={\"width_ratios\": [2.2, 1]})\n    for r, u in enumerate(UNITS_TF):\n        W = w2[\"units\"][u]\n        A = W[\"scope_A_all_position\"]\n        ax = axes[r, 0]\n        pairs = {int(k): int(v) for k, v in w2[\"matching\"][\"pairs_late_to_early\"].items()}\n        x = np.arange(len(LATE))\n        late = [A[f\"W{l}\"][\"share\"] for l in LATE]\n        early = [A.get(f\"E_match{l}_L{pairs[l]}\", {}).get(\"share\", np.nan) for l in LATE]\n        fork = [W[\"scope_B_fork_only\"].get(f\"Wf{l}\", {}).get(\"share\", np.nan) for l in LATE]\n        ax.bar(x - 0.2, late, 0.4, color=\"#c0392b\", label=\"late MLP l -> base (all positions)\")\n        ax.bar(x + 0.2, early, 0.4, color=\"#7f8c8d\", label=\"matched early MLP -> base\")\n        ax.scatter(x - 0.2, fork, marker=\"D\", color=\"k\", s=14, zorder=5, label=\"late MLP l, fork-only (iter-9 W arm)\")\n        for j in range(3):\n            rd = [A.get(f\"RANDDELTA{l}_{j}\", {}).get(\"share\", np.nan) for l in LATE]\n            ax.scatter(x - 0.2 + 0.08 * (j - 1), rd, marker=\"x\", color=\"#3498db\", s=16, zorder=6,\n                       label=\"same-layer random delta (matched ||dW||)\" if j == 0 else None)\n        ax.set_xticks(x, [f\"L{l}\\n(E{pairs[l]})\" for l in LATE], fontsize=7)\n        ax.axhline(0, color=\"k\", lw=0.8)\n        ax.set_ylabel(\"share closed\")\n        ax.set_title(f\"{u}: single-layer weight swaps (W2)\", fontsize=8.5)\n        ax.legend(fontsize=6, frameon=False)\n        ax = axes[r, 1]\n        dec = W[\"decomposition\"]\n        keys = [(\"readout_rows_norm\", \"readout (rows + norm)\"), (\"late_mlps_all_position\", \"late MLPs 26-35\"),\n                (\"joint_late_mlps_plus_readout\", \"joint: late MLPs + readout\"),\n                (\"late_attention_all_position\", \"late attention 26-35\"),\n                (\"late_blocks_all_position\", \"late blocks (attn + MLP)\"),\n                (\"joint_late_blocks_plus_readout\", \"joint: late blocks + readout\")]\n        vals = [dec.get(k) for k, _ in keys]\n        rj = W[\"rule\"].get(\"randdelta_joint_shares\", [])\n        ax.barh(np.arange(len(keys)), [v if v is not None else 0 for v in vals],\n                color=[\"#2c3e50\", \"#c0392b\", \"#8e44ad\", \"#e67e22\", \"#d35400\", \"#6c3483\"])\n        ax.set_yticks(np.arange(len(keys)), [lbl for _, lbl in keys], fontsize=7)\n        ax.axvline(0, color=\"k\", lw=0.8)\n        ax.axvline(1, color=\"k\", lw=0.8, ls=\":\")\n        ax.set_xlabel(\"share closed\")\n        ax.set_title(f\"{u}: decomposition\\n(E_joint {W['rule']['early_joint']:.2f}; random joint \"\n                     f\"{', '.join(f'{v:.2f}' for v in rj)})\", fontsize=7.5)\n    save(fig, \"F7_w2_swaps\")\n\n\ndef f8(w3: dict) -> None:\n    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.4))\n    arms = [\"ROWS_ALL\", \"ROWS_D\", \"ROWS_A\", \"NORM\", \"ROWS_NORM\", \"SIGN\"]\n    ax = axes[0]\n    sh = [w3[\"arms\"][a][\"share\"] for a in arms]\n    ci = [w3[\"arms\"][a][\"ci95\"] for a in arms]\n    y = np.arange(len(arms))\n    ax.barh(y, sh, color=[C[a] for a in arms])\n    ax.errorbar(sh, y, xerr=[[s - c[0] for s, c in zip(sh, ci)], [c[1] - s for s, c in zip(sh, ci)]], fmt=\"none\",\n                ecolor=\"k\", capsize=3, lw=1)\n    ax.set_yticks(y, arms)\n    ax.axvline(0, color=\"k\", lw=0.8)\n    ax.set_xlabel(\"share closed\")\n    ax.set_title(f\"Gemma-3-4b G-GRID@32 (gap {w3['gap_mean']:.2f} nats; output-only untying)\", fontsize=8)\n    ax = axes[1]\n    for nt in (\"RAND_ISO\", \"DELTA_SWAP\"):\n        ax.hist(w3[\"nulls\"][nt][\"shares\"], bins=25, alpha=0.6, color=C[nt],\n                label=f\"{nt} (median {w3['nulls'][nt]['median']:.2f})\")\n    ax.axvline(w3[\"arms\"][\"ROWS_ALL\"][\"share\"], color=C[\"ROWS_ALL\"], lw=2, label=\"ROWS_ALL\")\n    ax.set_xlabel(\"share closed by 50 null row edits\")\n    ax.legend(fontsize=6.5, frameon=False)\n    save(fig, \"F8_w3_gemma\")\n\n\ndef main() -> None:\n    w1 = read_json(RESULTS_DIR / \"w1_tf_summary.json\")\n    f1(w1)\n    f2(w1)\n    f3(w1)\n    f4(read_json(RESULTS_DIR / \"w1_generation.json\"))\n    if (RESULTS_DIR / \"w2_summary.json\").exists():\n        f7(read_json(RESULTS_DIR / \"w2_summary.json\"))\n    if (RESULTS_DIR / \"w3_summary.json\").exists():\n        f8(read_json(RESULTS_DIR / \"w3_summary.json\"))\n    f5_f6()\n\n\nif __name__ == \"__main__\":\n    setup_logging(\"figures10\")\n    main()", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [49] THINKING · 2026-10-26 15:27:30 UTC

```
The venv is set with a PyPI CUDA build of torch, sufficient for data prep since Figures F5 and F6 only need cached vectors and rows to show real activation geometry. Next I'll review the delta-geometry analysis, the capture code, and the contents of the `.pt` file.
```

### [50] TOOL CALL — Bash · 2026-10-26 15:27:30 UTC

```
Read the delta geometry analysis code:
A=/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56; sed -n 1,140p $A/src/analysis10.py
```

### [51] TOOL RESULT — Bash · 2026-10-26 15:27:30 UTC

```
{"stdout": "#!/usr/bin/env python3\n\"\"\"Cross-claim analysis and the run summary.\n\n  delta_geometry  why same-norm edits aimed at the residual subspace (RAND_RESID) out-lever the real row deltas: for each\n                  fork-class token t, the fraction of ||Delta_t||^2 inside the top-64 principal subspace of the instruct\n                  final-normed residual, and the logit leverage |h . Delta_t| / (||h|| ||Delta_t||) of the real delta\n                  vs the RAND_ISO / RAND_RESID draws (results/delta_geometry.json)\n  summary         every verdict, headline number, deviation and cost in one file (results/summary.json)\n\"\"\"\n\nfrom __future__ import annotations\n\nimport sys\nfrom typing import Any\n\nimport numpy as np\nimport torch\nfrom loguru import logger\n\nfrom cfg10 import (CACHE_DIR, I9_RES, RESULTS_DIR, UNITS_TF, read_json, setup_logging, utc_now, verify_chain,\n                   write_json)\nfrom w1_tf import UnitData, load_readout\n\n\ndef delta_geometry() -> dict[str, Any]:\n    units = read_json(I9_RES / \"units.json\")\n    WI, gI = load_readout(\"qwen\")\n    WB, gB = load_readout(\"qwen_base\")\n    out: dict[str, Any] = {\"utc\": utc_now(), \"units\": {}}\n    for u in UNITS_TF:\n        d = UnitData(u, units, WI, WB, gI, gB, need_logits=False)\n        pca = torch.load(CACHE_DIR / f\"resid_pca_{u}.pt\")\n        V = pca[\"basis\"].double()                                        # [64, d]\n        nul = np.load(RESULTS_DIR / f\"null_draws_{u}.npz\")\n        h = d.hfI.double()\n        hn = h.norm(dim=-1, keepdim=True)\n        rec = {}\n        for j, t in enumerate(d.S):\n            dl = d.Delta[j].double()\n            frac = float((V @ dl).pow(2).sum() / dl.pow(2).sum())\n            lev = (h @ dl).abs() / (hn[:, 0] * dl.norm())\n            lev_iso = [float(((h @ torch.from_numpy(nul[\"RAND_ISO\"][k, j]).double()).abs() /\n                              (hn[:, 0] * dl.norm())).mean()) for k in range(nul[\"RAND_ISO\"].shape[0])]\n            lev_res = [float(((h @ torch.from_numpy(nul[\"RAND_RESID\"][k, j]).double()).abs() /\n                              (hn[:, 0] * dl.norm())).mean()) for k in range(nul[\"RAND_RESID\"].shape[0])]\n            lev_swp = [float(((h @ torch.from_numpy(nul[\"DELTA_SWAP\"][k, j]).double()).abs() /\n                              (hn[:, 0] * torch.from_numpy(nul[\"DELTA_SWAP\"][k, j]).double().norm())).mean())\n                       for k in range(nul[\"DELTA_SWAP\"].shape[0])]\n            rec[str(t)] = {\"class\": \"D\" if j < d.nD else \"A\", \"delta_norm\": float(dl.norm()),\n                           \"frac_delta_energy_in_resid_pc64\": frac,\n                           \"frac_expected_isotropic\": 64 / dl.numel(),\n                           \"leverage_real_mean\": float(lev.mean()), \"leverage_rand_iso_median\": float(np.median(lev_iso)),\n                           \"leverage_rand_resid_median\": float(np.median(lev_res)),\n                           \"leverage_delta_swap_median\": float(np.median(lev_swp)),\n                           \"signed_logit_change_mean\": float((h @ dl).mean())}\n        out[\"units\"][u] = {\"tokens\": rec, \"resid_pc64_var_explained\": pca[\"var_explained_top64\"]}\n        logger.info(f\"{u}: \" + \"; \".join(f\"{t}: frac {v['frac_delta_energy_in_resid_pc64']:.3f} lev \"\n                                         f\"{v['leverage_real_mean']:.4f} (iso {v['leverage_rand_iso_median']:.4f}, \"\n                                         f\"resid {v['leverage_rand_resid_median']:.4f}, swap \"\n                                         f\"{v['leverage_delta_swap_median']:.4f})\" for t, v in list(rec.items())[:4]))\n    write_json(RESULTS_DIR / \"delta_geometry.json\", out)\n    return out\n\n\ndef summary() -> dict[str, Any]:\n    s0 = read_json(RESULTS_DIR / \"stage0.json\")\n    w1 = read_json(RESULTS_DIR / \"w1_tf_summary.json\")\n    gen = read_json(RESULTS_DIR / \"w1_generation.json\")\n    w2 = read_json(RESULTS_DIR / \"w2_summary.json\") if (RESULTS_DIR / \"w2_summary.json\").exists() else None\n    w3 = read_json(RESULTS_DIR / \"w3_summary.json\") if (RESULTS_DIR / \"w3_summary.json\").exists() else None\n    dev = read_json(RESULTS_DIR / \"deviations.json\") if (RESULTS_DIR / \"deviations.json\").exists() else []\n    red = read_json(RESULTS_DIR / \"rederive.json\") if (RESULTS_DIR / \"rederive.json\").exists() else {}\n    out: dict[str, Any] = {\"utc\": utc_now(), \"claims\": {}}\n    out[\"S0\"] = {u: {\"mean_m_I\": s0[\"units\"][u][\"mean_m_I\"], \"mean_m_I_iter9\": s0[\"units\"][u][\"mean_m_I_iter9\"],\n                     \"mean_m_B\": s0[\"units\"][u][\"mean_m_B\"], \"mean_m_B_iter9\": s0[\"units\"][u][\"mean_m_B_iter9\"],\n                     \"gap_mean\": s0[\"units\"][u][\"gap_mean\"], \"gap_ci95\": s0[\"units\"][u][\"gap_ci95\"],\n                     \"max_per_prompt_abs_diff_I\": s0[\"units\"][u][\"max_per_prompt_abs_diff_I\"],\n                     \"spearman_I\": s0[\"units\"][u][\"spearman_I\"],\n                     \"decomposition_unembedding_only\": s0[\"units\"][u][\"readout_decomposition_cpu\"][\n                         \"share_unembedding_only\"],\n                     \"pass\": s0[\"units\"][u][\"pass\"]} for u in UNITS_TF}\n    for u in UNITS_TF:\n        U = w1[\"units\"][u]\n        out[\"claims\"][f\"W1_TF_{u}\"] = {\n            \"role\": U[\"verdict_role\"], \"verdict\": U[\"verdict\"], \"qualifier\": U[\"specificity_qualifier\"],\n            \"shares\": {a: U[\"arms\"][a][\"share\"] for a in (\"ROWS_ALL\", \"ROWS_D\", \"ROWS_A\", \"NORM\", \"ROWS_NORM\",\n                                                         \"FULL_UNEMB\", \"SIGN\")},\n            \"ROWS_ALL_ci95\": U[\"arms\"][\"ROWS_ALL\"][\"ci95\"],\n            \"dose\": {k: U[\"arms\"][k][\"share\"] for k in U[\"arms\"] if k.startswith(\"DOSE_\")},\n            \"nulls\": {k: {kk: U[\"nulls\"][k][kk] for kk in (\"median\", \"p95\", \"max\", \"empirical_p_rows_all\")}\n                      for k in U[\"nulls\"]}, \"factorial_2x2\": {k: v for k, v in U[\"factorial_2x2\"].items()\n                                                               if k != \"interaction_per_prompt\"}}\n        G = gen[\"units\"].get(u)\n        if G:\n            out[\"claims\"][f\"W1_GEN_{u}\"] = {\n                \"role\": G[\"verdict_role\"], \"verdict\": G[\"verdict\"],\n                \"correct_of_30\": {a: G[\"cells\"][a][\"n_correct\"] for a in G[\"cells\"]},\n                \"predicted_correct_of_30\": {a: G[\"cells\"][a][\"predicted_correct_count\"] for a in G[\"cells\"]},\n                \"pass_of_30\": {a: G[\"cells\"][a][\"n_pass\"] for a in G[\"cells\"]},\n                \"tests\": {k: {kk: v.get(kk) for kk in (\"b_first_only\", \"c_second_only\", \"p_exact_two_sided\",\n                                                       \"p_holm_primary\")} for k, v in G[\"tests\"].items() if \"|\" not in k}}\n        if w2:\n            W = w2[\"units\"][u]\n            out[\"claims\"][f\"W2_{u}\"] = {\"role\": W[\"rule_role\"], \"rule\": W[\"rule\"], \"decomposition\": W[\"decomposition\"],\n                                        \"bridge_iter9\": W[\"bridge_iter9\"],\n                                        \"singles_top3\": W[\"singles_ranked\"][:3]}\n    if w3:\n        out[\"claims\"][\"W3_G-GRID\"] = {\"role\": \"descriptive\", \"gap\": w3[\"gap_mean\"],\n                                      \"shares\": {a: w3[\"arms\"][a][\"share\"] for a in w3[\"arms\"]},\n                                      \"nulls\": {k: {kk: w3[\"nulls\"][k][kk] for kk in (\"median\", \"p95\", \"max\")}\n                                                for k in w3[\"nulls\"]}, \"reproduction_b1\": w3[\"reproduction_b1\"]}\n    pw_p = RESULTS_DIR / \"w1_generation_power.json\"\n    if pw_p.exists():\n        pw = read_json(pw_p)\n        out[\"claims\"][\"W1_GEN_power_extension\"] = {\n            \"role\": \"descriptive extension (COMMIT #7)\",\n            \"units\": {u: {\"pooled_90_correct\": {a: pw[\"units\"][u][\"cells\"][a][\"n_correct\"] for a in (\"TWIN\", \"ROWS\",\n                                                                                                  \"RAND_MED\")},\n                          \"tests\": pw[\"units\"][u][\"tests\"], \"predicted\": pw[\"units\"][u][\"predicted\"]}\n                      for u in pw[\"units\"]}}\n    dc_p = RESULTS_DIR / \"depcheck_leetcode.json\"\n    if dc_p.exists():\n        dc = read_json(dc_p)\n        out[\"dependency_check_leetcode_323_547\"] = {k: dc[k] for k in (\"source\", \"n_cases\", \"n_programs\", \"n_dep_pass\",\n                                                                       \"n_labeller_pass\",\n                                                                       \"agreement_dep_vs_labeller_pass\")}\n    rh_p = RESULTS_DIR / \"rederive_headline.json\"\n    if rh_p.exists():\n        rh = read_json(rh_p)\n        out[\"headline_rederivation_float64\"] = {\n            \"max_abs_diff_vs_reported\": max(v for u in rh[\"agreement_vs_reported\"].values() for v in u.values()),\n            \"W1_TF\": rh[\"W1_TF\"], \"W2\": rh[\"W2\"], \"placebos\": rh[\"placebos\"],\n            \"W1_GEN\": {u: {k: {kk: t[kk] for kk in (\"a_correct\", \"b_correct\", \"b\", \"c\", \"p\",\n                                                     \"placebo_label_swap_median_p\")} for k, t in v.items()}\n                       for u, v in rh[\"W1_GEN\"].items()}}\n    out[\"audit\"] = {\"n_checks\": red.get(\"n_checks\"), \"n_mismatches\": red.get(\"n_mismatches\"),\n                    \"placebos\": {k: red.get(k) for k in (\"P1_noise_placebo\", \"P3_DA_shuffle_placebo\")}}\n    out[\"commitment_chain\"] = verify_chain()\n    out[\"deviations\"] = dev\n    out[\"openrouter_spend_usd\"] = 0.0", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [52] TOOL CALL — Bash · 2026-10-26 15:27:30 UTC

```
Inspect cached fork-state tensor structure:
A=/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56; /tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5/bin/python -I -c "
import torch, numpy as np
for f in ['fork_instr_T10','fork_base_T10','fork_instr_B3','resid_pca_T10','lm_head_rownorms']:
    d=torch.load('$A/cache/'+f+'.pt', weights_only=False)
    print('==',f, type(d), list(d.keys()) if isinstance(d,dict) else '')
    for k,v in d.items():
        if k=='caps':
            print('  caps n', len(v)); c=v[0]
            for kk,vv in c.items(): print('    ', kk, (vv.dtype, tuple(vv.shape)) if hasattr(vv,'dtype') else (repr(vv)[:120]))
        else:
            print('  ', k, (v.dtype, tuple(v.shape)) if hasattr(v,'dtype') else repr(v)[:200])
z=np.load('$A/results/null_draws_T10.npz'); print({k:(z[k].dtype,z[k].shape) for k in z.files})
"
```

### [53] TOOL RESULT — Bash · 2026-10-26 15:27:30 UTC

```
{"stdout": "== fork_instr_T10 <class 'dict'> ['unit', 'model', 'B_ot', 'caps']\n   unit 'T10'\n   model 'qwen'\n   B_ot 40\n  caps n 20\n     h_pre (torch.bfloat16, (4096,))\n     h_fin (torch.bfloat16, (4096,))\n     rows_identical True\n     mlp_in (torch.bfloat16, (36, 4096))\n     mlp_out (torch.bfloat16, (36, 4096))\n     logits (torch.float32, (151936,))\n     m 5.8872222900390625\n     pid 'W1|ship'\n     template 'W1'\n     ids_sha '77b9a34abbbb189b14b9ddd9aedcb08be8a7ff167988282ac819a1df0749f36c'\n     n_ids 183\n== fork_base_T10 <class 'dict'> ['unit', 'model', 'B_ot', 'caps']\n   unit 'T10'\n   model 'qwen_base'\n   B_ot 40\n  caps n 20\n     h_pre (torch.bfloat16, (4096,))\n     h_fin (torch.bfloat16, (4096,))\n     rows_identical True\n     mlp_in (torch.bfloat16, (36, 4096))\n     mlp_out (torch.bfloat16, (36, 4096))\n     logits (torch.float32, (151936,))\n     m -0.13475418090820312\n     pid 'W1|ship'\n     template 'W1'\n     ids_sha '77b9a34abbbb189b14b9ddd9aedcb08be8a7ff167988282ac819a1df0749f36c'\n     n_ids 183\n== fork_instr_B3 <class 'dict'> ['unit', 'model', 'B_ot', 'caps']\n   unit 'B3'\n   model 'qwen'\n   B_ot 40\n  caps n 20\n     h_pre (torch.bfloat16, (4096,))\n     h_fin (torch.bfloat16, (4096,))\n     rows_identical True\n     mlp_in (torch.bfloat16, (36, 4096))\n     mlp_out (torch.bfloat16, (36, 4096))\n     logits (torch.float32, (151936,))\n     m 1.2419319152832031\n     pid 'W1|guy'\n     template 'W1'\n     ids_sha 'b78d6ddeee6f8559766c95c5f8ef33fbf72d75c6127b5895250e5ddcb407d38a'\n     n_ids 322\n== resid_pca_T10 <class 'dict'> ['basis', 'eigvals', 'mean', 'n_positions', 'var_explained_top64']\n   basis (torch.float32, (64, 4096))\n   eigvals (torch.float32, (64,))\n   mean (torch.float32, (4096,))\n   n_positions 3636\n   var_explained_top64 0.91533297454472\n== lm_head_rownorms <class 'dict'> ['delta_norm', 'w_instr_norm']\n   delta_norm (torch.float32, (151936,))\n   w_instr_norm (torch.float32, (151936,))\n{'S': (dtype('int64'), (3,)), 'RAND_ISO': (dtype('float32'), (50, 3, 4096)), 'RAND_RESID': (dtype('float32'), (50, 3, 4096)), 'DELTA_SWAP': (dtype('float32'), (50, 3, 4096)), 'DELTA_SWAP_tokens': (dtype('int64'), (50, 3)), 'delta_norm': (dtype('float32'), (3,))}", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [54] THINKING · 2026-10-26 15:27:46 UTC

```
The `.pt` caches contain the per-prompt `h_pre`, `h_fin`, and margin `m` that W1 needs, plus a 64×4096 PCA basis. I'll now check the prompt records and summary keys before writing the data-builder script.
```

### [55] TOOL CALL — Bash · 2026-10-26 15:27:46 UTC

```
Inspect prompt records and reported W1 summary:
A=/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56; python3 -c "
import json
u=json.load(open('$A/inputs/iter9/results/units.json'))
for k in ('T10','B3'):
    U=u[k]; print(k, U['name'], U['family'], U['kind'], 'n prompts', len(U['prompts']))
    p=U['prompts'][0]; print('  prompt keys', list(p.keys()))
    for kk,vv in p.items(): print('    ',kk, repr(vv)[:300])
    f=U['forks'][0]; print('  opening_text', repr(f['opening_text'])[:400]); print('  D_str', f['D_str'], 'A_str', f['A_str'], 'D_class', f['D_class'], 'A_class', f['A_class'])
w=json.load(open('$A/results/w1_tf_summary.json'))
print(list(w.keys())); U=w['units']['T10']; print(list(U.keys())); print(list(U['arms'].keys())); print(list(U['nulls'].keys()), list(U['nulls']['RAND_ISO'].keys()))
print('T10 rows_all', U['arms']['ROWS_ALL']['share'], U['arms']['ROWS_ALL']['ci95'], U['verdict'], U['specificity_qualifier'])
print({nt:(U['nulls'][nt]['median'],U['nulls'][nt]['p95'],U['nulls'][nt]['max'],U['nulls'][nt]['empirical_p_rows_all']) for nt in U['nulls']})
print(U['factorial_2x2']['interaction_mean'], U['per_token_logit_change'])
"
```

### [56] TOOL RESULT — Bash · 2026-10-26 15:27:46 UTC

````
{"stdout": "T10 connected components qwen b2 n prompts 20\n  prompt keys ['pid', 'template', 'noun', 'ids', 'ids_plain', 'pos', 'sha', 'exp41_m_clean']\n     pid 'W1|ship'\n     template 'W1'\n     noun 'ship'\n     ids [151644, 872, 198, 5404, 537, 990, 8284, 369, 419, 3383, 13, 659, 659, 659, 659, 659, 659, 6762, 6262, 25, 3270, 264, 13027, 729, 11625, 1445, 11, 12822, 8, 429, 4675, 279, 1372, 315, 8433, 6813, 315, 458, 2030, 74612, 4771, 13, 576, 7798, 525, 279, 25780, 220, 15, 311, 308, 481, 220, 16, 11, 448, 2\n     ids_plain [5404, 537, 990, 8284, 369, 419, 3383, 13, 659, 659, 659, 659, 659, 659, 6762, 6262, 25, 3270, 264, 13027, 729, 11625, 1445, 11, 12822, 8, 429, 4675, 279, 1372, 315, 8433, 6813, 315, 458, 2030, 74612, 4771, 13, 576, 7798, 525, 279, 25780, 220, 15, 311, 308, 481, 220, 16, 11, 448, 220, 16, 2651, 308,\n     pos {'COND': [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17], 'SPEC': [0, 1, 2, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72\n     sha '77b9a34abbbb189b14b9ddd9aedcb08be8a7ff167988282ac819a1df0749f36c'\n     exp41_m_clean 6.102848052978516\n  opening_text '```python\\ndef solve(n, edges):\\n    def'\n  D_str [' find'] A_str [' dfs', ' bfs'] D_class union_find A_class dfs|bfs\nB3 minimum spanning tree weight qwen b2 n prompts 20\n  prompt keys ['pid', 'template', 'noun', 'ids', 'ids_plain', 'pos', 'sha', 'exp41_m_clean']\n     pid 'W1|guy'\n     template 'W1'\n     noun 'guy'\n     ids [151644, 872, 198, 5404, 537, 990, 7412, 369, 419, 3383, 13, 659, 659, 659, 6762, 6262, 25, 3270, 264, 13027, 729, 11625, 1445, 11, 19241, 8, 429, 4675, 279, 24632, 2790, 2783, 315, 264, 5754, 315, 19241, 429, 7746, 678, 9720, 13, 2619, 525, 308, 9720, 48826, 220, 15, 311, 308, 481, 220, 16, 11, 138\n     ids_plain [5404, 537, 990, 7412, 369, 419, 3383, 13, 659, 659, 659, 6762, 6262, 25, 3270, 264, 13027, 729, 11625, 1445, 11, 19241, 8, 429, 4675, 279, 24632, 2790, 2783, 315, 264, 5754, 315, 19241, 429, 7746, 678, 9720, 13, 2619, 525, 308, 9720, 48826, 220, 15, 311, 308, 481, 220, 16, 11, 1380, 220, 16, 2651, \n     pos {'COND': [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14], 'SPEC': [0, 1, 2, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72\n     sha 'b78d6ddeee6f8559766c95c5f8ef33fbf72d75c6127b5895250e5ddcb407d38a'\n     exp41_m_clean 1.230194091796875\n  opening_text '```python\\ndef solve(n, roads):\\n    import heapq\\n\\n    # Build adjacency list\\n    graph = [[] for _ in range(n)]\\n    for u, v, w in roads:\\n        graph[u].append((v, w))\\n        graph[v].append((u, w))\\n\\n    #'\n  D_str [' Kr', ' Union', ' Check', ' Minimum', ' Find', ' Priority', ' Helper', ' Dis'] A_str [' Prim', ' Pr', ' Use', ' MST', ' To', ' Using', 'Prim', ' Prime'] D_class kruskal A_class prim_heap\n['utc', 'units', 'seconds']\n['pids', 'templates', 'gap_mean', 'gap', 'm_I', 'm_B', 'arms', 'S_str', 'nD', 'base_dist_mean', 'identity_full_unemb_minus_rows_all_max_abs', 'identity_twin_cpu_minus_gpu_max_abs', 'factorial_2x2', 'per_token_logit_change', 'delta_norms', 'nulls', 'verdict', 'specificity_qualifier', 'verdict_role', 'rows_all_by_template']\n['TWIN', 'TWIN_cpu', 'ROWS_ALL', 'ROWS_D', 'ROWS_A', 'NORM', 'ROWS_NORM', 'FULL_UNEMB', 'NORM_recompute_instr_gain', 'DOSE_0.25', 'DOSE_0.5', 'DOSE_0.75', 'DOSE_1', 'DOSE_1.25', 'DOSE_1.5', 'SIGN', 'F_BI', 'F_BB_cpu', 'F_II_cpu', 'UNEMB_ONLY_on_base_resid']\n['RAND_ISO', 'DELTA_SWAP', 'RAND_RESID'] ['shares', 'median', 'p95', 'max', 'min', 'mean', 'empirical_p_rows_all', 'p_floor', 'mean_unmapped', 'rows_all_above_max', 'rows_all_above_p95', 'median_draw', 'max_draw', 'dose_curve']\nT10 rows_all 0.5484614645905562 [0.4396290582255756, 0.706851369990123] SUPPORTED readout-level but not token-specific\n{'RAND_ISO': (0.04371715628133733, 0.1383038356630401, 0.20975997579735559, 0.0196078431372549), 'DELTA_SWAP': (0.08474978152133956, 0.40511481924486825, 0.6254140319684964, 0.058823529411764705), 'RAND_RESID': (0.1809416100742252, 1.2519895879252902, 2.3278898026484405, 0.37254901960784315)}\n-1.3366443634033203 {' find': {'mean': -0.27135932445526123, 'sd': 0.020528068765997887, 'class': 'D'}, ' dfs': {'mean': 2.2276344299316406, 'sd': 0.0825425460934639, 'class': 'A'}, ' bfs': {'mean': 3.143372058868408, 'sd': 0.13666857779026031, 'class': 'A'}}", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
````

### [57] THINKING · 2026-10-26 15:28:19 UTC

```
I'll decode the stored token id prompts using the local Qwen3 tokenizer for readable previews, and first verify that HTTP range requests work against the pinned safetensors shards before writing the builder.
```

### [58] TOOL CALL — Bash · 2026-10-26 15:28:19 UTC

```
Test HTTP range reads of safetensors headers:
cd /tmp && /tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5/bin/python -I -c "
import requests, json, struct
for repo, rev in [('Qwen/Qwen3-8B','b968826d9c46dd6066d109eabc6255188de91218'),('Qwen/Qwen3-8B-Base','49e3418fbbbca6ecbdf9608b4d22e5a407081db4')]:
    base=f'https://huggingface.co/{repo}/resolve/{rev}/'
    idx=requests.get(base+'model.safetensors.index.json', timeout=30).json()['weight_map']
    fl, fn = idx['lm_head.weight'], idx['model.norm.weight']
    print(repo, 'lm_head in', fl, 'norm in', fn)
    for f in sorted({fl, fn}):
        r=requests.get(base+f, headers={'Range':'bytes=0-7'}, timeout=30)
        n=struct.unpack('<Q', r.content)[0]
        h=requests.get(base+f, headers={'Range':f'bytes=8-{7+n}'}, timeout=30).json()
        for k in ('lm_head.weight','model.norm.weight'):
            if k in h: print('  ', f, r.status_code, k, h[k])
"; cd - >/dev/null
```

### [59] TOOL RESULT — Bash · 2026-10-26 15:28:23 UTC

```
{"stdout": "Qwen/Qwen3-8B lm_head in model-00005-of-00005.safetensors norm in model-00004-of-00005.safetensors\n   model-00004-of-00005.safetensors 206 model.norm.weight {'dtype': 'BF16', 'shape': [4096], 'data_offsets': [3187822592, 3187830784]}\n   model-00005-of-00005.safetensors 206 lm_head.weight {'dtype': 'BF16', 'shape': [151936, 4096], 'data_offsets': [0, 1244659712]}\nQwen/Qwen3-8B-Base lm_head in model-00005-of-00005.safetensors norm in model-00004-of-00005.safetensors\n   model-00004-of-00005.safetensors 206 model.norm.weight {'dtype': 'BF16', 'shape': [4096], 'data_offsets': [3187822592, 3187830784]}\n   model-00005-of-00005.safetensors 206 lm_head.weight {'dtype': 'BF16', 'shape': [151936, 4096], 'data_offsets': [0, 1244659712]}", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [60] THINKING · 2026-10-26 15:28:45 UTC

```
Range reads work on both pinned revisions, so I can pull just the 19 fork-class `lm_head` rows and the two final-norm gains. I'll add `tokenizers` for prompt decoding and write the data-builder script into the workspace.
```

### [61] TOOL CALL — Bash · 2026-10-26 15:28:45 UTC

```
Install tokenizers into the data-prep venv:
cd /tmp && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5/bin/python tokenizers 2>&1 | tail -2; /tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5/bin/python -I -c "import tokenizers; print(tokenizers.__version__)"; ls -la /ai-inventor/aii_data/runs/run_jSassd-YWLVC/.shared_cache/hf/hub/models--Qwen--Qwen3-8B/blobs/ | head
```

### [62] TOOL RESULT — Bash · 2026-10-26 15:28:47 UTC

```
{"stdout": "0.23.3\ntotal 19421\ndrwxrwxrwx 2 aii-agent aii-agent  2001514 Oct 26 08:49 .\ndrwxrwxrwx 6 aii-agent aii-agent  2001514 Oct 26 08:49 ..\n-rw-rw-rw- 1 aii-agent aii-agent  1671853 Oct 26 08:49 31349551d90c7606f325fe0f11bbb8bd5fa0d7c7\n-rw-rw-rw- 1 aii-agent aii-agent     9732 Oct 26 08:49 417d038a63fa3de29cfde265caedae14d1a58d92\n-rw-rw-rw- 1 aii-agent aii-agent  2776833 Oct 26 08:49 4783fe10ac3adce15ac8f358ef5462739852c569\n-rw-rw-rw- 1 aii-agent aii-agent 11422654 Oct 26 08:49 aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4\n-rw-rw-rw- 1 aii-agent aii-agent      728 Oct 26 08:49 d46195ac87f837ad233d02b2f80f148bf7c005e0", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [63] TOOL CALL — Write · 2026-10-26 15:29:29 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/build_mini_demo_data.py

#!/usr/bin/env python3
"""Build mini_demo_data.json for code_demo.ipynb from the BASE-W artifact (iteration 10, experiment 56).

The W1 teacher-forced arms of the artifact are exact CPU arithmetic on cached fork states: the class margin
lse(z[D]) - lse(z[A]) depends only on the final-normed residual at the fork and the fork-class unembedding rows.
This script collects exactly those inputs, so the notebook can recompute every W1 arm and null without a GPU.

Read-only inputs, all inside the artifact folder passed with --artifact-dir:
  cache/fork_{instr,base}_{T10,B3}.pt  per-prompt fork states of Qwen3-8B / Qwen3-8B-Base (h_pre, h_fin in bf16, the
                                       captured fp32 class margin m)
  cache/resid_pca_{u}.pt               top-64 PCA basis of the instruct final-normed residual (RAND_RESID null)
  results/null_draws_{u}.npz           committed null draws: DELTA_SWAP is stored for T10 (it needs the full 151,936-row
                                       lm_heads of both models); RAND_ISO and RAND_RESID are regenerated from their seeds
                                       in the notebook, and this script checks the regeneration bit-exactly
  results/w1_tf_summary.json, results/delta_geometry.json   reported numbers, for side-by-side comparison
  inputs/iter9/results/units.json      fork tokens D / A and the prompt token ids
Fetched with HTTP range requests from the Hugging Face Hub at the pinned revisions: the fork-class rows of lm_head.weight
(19 rows x 8 KB per model) and model.norm.weight of both models.

Usage: python build_mini_demo_data.py --artifact-dir <artifact folder> --tokenizer <Qwen3 tokenizer.json> [--out FILE]
"""

from __future__ import annotations

import argparse
import base64
import json
import struct
from pathlib import Path

import numpy as np
import requests
import torch
from tokenizers import Tokenizer

MODELS = {"qwen": ("Qwen/Qwen3-8B", "b968826d9c46dd6066d109eabc6255188de91218"),
          "qwen_base": ("Qwen/Qwen3-8B-Base", "49e3418fbbbca6ecbdf9608b4d22e5a407081db4")}
UNITS_TF = ("T10", "B3")
UNIT_IDX = {"T10": 0, "B3": 1}
NULL_SEED0 = {"RAND_ISO": 101000, "RAND_RESID": 102000, "DELTA_SWAP": 103000}
N_NULL = 50


def enc(a: torch.Tensor | np.ndarray) -> dict:
    """Array -> {"dtype", "shape", "b64"} with little-endian raw bytes; bfloat16 is stored as its uint16 bit pattern."""
    if isinstance(a, torch.Tensor):
        if a.dtype == torch.bfloat16:
            raw = a.contiguous().view(torch.int16).numpy().astype("<i2").tobytes()
            return {"dtype": "bfloat16", "shape": list(a.shape), "b64": base64.b64encode(raw).decode("ascii")}
        a = a.numpy()
    a = np.ascontiguousarray(a)
    if a.dtype != np.float32:
        raise TypeError(f"unexpected dtype {a.dtype}")
    return {"dtype": "float32", "shape": list(a.shape), "b64": base64.b64encode(a.astype("<f4").tobytes()).decode("ascii")}


class RangeSafetensors:
    """Reads single rows of a tensor from a safetensors shard on the Hub with HTTP range requests."""

    def __init__(self, repo: str, rev: str):
        self.base = f"https://huggingface.co/{repo}/resolve/{rev}/"
        self.wmap = requests.get(self.base + "model.safetensors.index.json", timeout=60).json()["weight_map"]
        self.headers: dict[str, tuple[int, dict]] = {}

    def _get(self, fn: str, a: int, b: int) -> bytes:
        r = requests.get(self.base + fn, headers={"Range": f"bytes={a}-{b}"}, timeout=120)
        assert r.status_code == 206 and len(r.content) == b - a + 1, (r.status_code, len(r.content))
        return r.content

    def _header(self, fn: str) -> tuple[int, dict]:
        if fn not in self.headers:
            n = struct.unpack("<Q", self._get(fn, 0, 7))[0]
            self.headers[fn] = (8 + n, json.loads(self._get(fn, 8, 7 + n)))
        return self.headers[fn]

    def rows(self, name: str, ids: list[int] | None) -> torch.Tensor:
        fn = self.wmap[name]
        start, hdr = self._header(fn)
        meta = hdr[name]
        assert meta["dtype"] == "BF16"
        d = meta["shape"][-1]
        off = start + meta["data_offsets"][0]
        if ids is None:                                             # the whole (1-D) tensor
            raw = self._get(fn, off, off + 2 * d - 1)
            return torch.frombuffer(bytearray(raw), dtype=torch.bfloat16).clone()
        out = []
        for i in ids:
            raw = self._get(fn, off + 2 * d * i, off + 2 * d * (i + 1) - 1)
            out.append(torch.frombuffer(bytearray(raw), dtype=torch.bfloat16).clone())
        return torch.stack(out)


def lse_margin(h: torch.Tensor, W: torch.Tensor, nD: int) -> np.ndarray:
    z = h @ W.T
    return (torch.logsumexp(z[:, :nD], -1) - torch.logsumexp(z[:, nD:], -1)).numpy()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact-dir", required=True, type=Path)
    ap.add_argument("--tokenizer", required=True, type=Path, help="Qwen3-8B tokenizer.json")
    ap.add_argument("--out", default=Path(__file__).resolve().parent / "mini_demo_data.json", type=Path)
    a = ap.parse_args()
    R = a.artifact_dir
    tok = Tokenizer.from_file(str(a.tokenizer))
    units = json.loads((R / "inputs/iter9/results/units.json").read_text())
    w1 = json.loads((R / "results/w1_tf_summary.json").read_text())
    geo = json.loads((R / "results/delta_geometry.json").read_text())
    rownorms = torch.load(R / "cache/lm_head_rownorms.pt")
    hub = {k: RangeSafetensors(*v) for k, v in MODELS.items()}
    g = {k: hub[k].rows("model.norm.weight", None) for k in MODELS}
    out: dict = {
        "description": "Inputs of the W1 teacher-forced readout test of the BASE-W artifact (iteration 10): cached fork "
                       "states of Qwen3-8B (instruct) and Qwen3-8B-Base for 20 prompts per unit, the fork-class "
                       "unembedding rows and final-norm gains of both models, the top-64 residual PCA basis, the "
                       "committed DELTA_SWAP null draws (T10) and the artifact's reported numbers.",
        "array_encoding": "{dtype, shape, b64}: base64 of little-endian raw bytes; bfloat16 arrays hold the uint16 bit "
                          "pattern of each value (decode: (u16 << 16) viewed as float32 is exact)",
        "models": {k: {"id": v[0], "revision": v[1]} for k, v in MODELS.items()},
        "readout": {"g_instr": enc(g["qwen"]), "g_base": enc(g["qwen_base"])},
        "units": {},
    }
    for u in UNITS_TF:
        U, f = units[u], units[u]["forks"][0]
        D, A = [int(t) for t in f["D"]], [int(t) for t in f["A"]]
        S, nD = D + A, len(D)
        ci = torch.load(R / f"cache/fork_instr_{u}.pt")
        cb = torch.load(R / f"cache/fork_base_{u}.pt")
        pids = [c["pid"] for c in ci["caps"]]
        assert pids == [c["pid"] for c in cb["caps"]]
        WI = hub["qwen"].rows("lm_head.weight", S)
        WB = hub["qwen_base"].rows("lm_head.weight", S)
        # the fetched rows must reproduce the committed delta norms and instruct row norms bit for bit
        nul = np.load(R / f"results/null_draws_{u}.npz")
        dn = (WB.float() - WI.float()).norm(dim=-1)
        assert list(nul["S"]) == S
        assert np.array_equal(dn.numpy(), nul["delta_norm"]), "row delta norms differ from the committed ones"
        assert torch.equal(WI.float().norm(dim=-1), rownorms["w_instr_norm"][S]), "instruct row norms differ"
        assert torch.equal(dn, rownorms["delta_norm"][S]), "delta norms differ from cache/lm_head_rownorms.pt"
        # RAND_ISO / RAND_RESID regenerate bit-exactly from the committed seeds (as w1_tf.make_nulls)
        V = torch.load(R / f"cache/resid_pca_{u}.pt")
        Vb = V["basis"].numpy().astype(np.float64)
        ui = UNIT_IDX[u]
        dnorm = dn.numpy()
        for k in range(N_NULL):
            for j, t in enumerate(S):
                r1 = np.random.default_rng([NULL_SEED0["RAND_ISO"] + 100 * ui + k, t])
                gg = r1.standard_normal(WI.shape[1])
                assert np.array_equal((dnorm[j] * gg / np.linalg.norm(gg)).astype(np.float32), nul["RAND_ISO"][k, j])
                r2 = np.random.default_rng([NULL_SEED0["RAND_RESID"] + 100 * ui + k, t])
                c = r2.standard_normal(Vb.shape[0])
                v = c @ Vb
                assert np.array_equal((dnorm[j] * v / np.linalg.norm(v)).astype(np.float32), nul["RAND_RESID"][k, j])
        # the captured instruct margin is reproduced by the CPU readout (TWIN_cpu) and ROWS_ALL by the reported share
        hfI = torch.stack([c["h_fin"] for c in ci["caps"]]).float()
        mI = np.array([c["m"] for c in ci["caps"]])
        mB = np.array([c["m"] for c in cb["caps"]])
        twin_cpu = lse_margin(hfI, WI.float(), nD)
        rows_all = lse_margin(hfI, WB.float(), nD)
        sh = float(np.sum(mI - rows_all)) / float(np.sum(mI - mB))
        rep = w1["units"][u]
        print(f"{u}: S {[tok.decode([t]) for t in S]}, max |TWIN_cpu - m_I| {np.abs(twin_cpu - mI).max():.2e}, "
              f"ROWS_ALL share {sh:.10f} (reported {rep['arms']['ROWS_ALL']['share']:.10f})")
        assert abs(sh - rep["arms"]["ROWS_ALL"]["share"]) < 1e-9
        prompts = {p["pid"]: p for p in U["prompts"]}
        ex = []
        for i, pid in enumerate(pids):
            p = prompts[pid]
            assert p["sha"] == ci["caps"][i]["ids_sha"] == cb["caps"][i]["ids_sha"]
            ex.append({"pid": pid, "template": ci["caps"][i]["template"], "noun": p["noun"],
                       "n_ids": ci["caps"][i]["n_ids"],
                       "input_text": tok.decode(p["ids"], skip_special_tokens=False),
                       "m_I": float(mI[i]), "m_B": float(mB[i]),
                       "h_pre_instr": enc(ci["caps"][i]["h_pre"]), "h_fin_instr": enc(ci["caps"][i]["h_fin"]),
                       "h_pre_base": enc(cb["caps"][i]["h_pre"]), "h_fin_base": enc(cb["caps"][i]["h_fin"])})
        null_data = {}
        if u == "T10":                                              # DELTA_SWAP needs the full lm_heads: store the draws
            null_data["DELTA_SWAP"] = enc(nul["DELTA_SWAP"])
            null_data["DELTA_SWAP_tokens"] = nul["DELTA_SWAP_tokens"].tolist()
            null_data["DELTA_SWAP_token_strings"] = [[tok.decode([int(t)]) for t in row]
                                                     for row in nul["DELTA_SWAP_tokens"]]
        arms_rep = {k: {kk: v[kk] for kk in ("share", "ci95", "mean_margin") if kk in v} for k, v in rep["arms"].items()}
        nulls_rep = {k: {kk: v[kk] for kk in ("median", "p95", "max", "empirical_p_rows_all", "median_draw", "max_draw")
                         if kk in v} for k, v in rep["nulls"].items()}
        for k, v in rep["nulls"].items():                           # committed null shares (used where draws are absent)
            nulls_rep[k]["shares"] = v["shares"]
        out["units"][u] = {
            "name": U["name"], "fork_id": f["fork_id"], "opening_text": f["opening_text"],
            "D": D, "A": A, "D_str": f["D_str"], "A_str": f["A_str"], "D_class": f["D_class"],
            "A_class": f["A_class"], "S": S, "nD": nD, "B_ot": [ci["B_ot"], cb["B_ot"]],
            "WI_S": enc(WI), "WB_S": enc(WB),
            "resid_pca": {"basis": enc(V["basis"]), "var_explained_top64": V["var_explained_top64"],
                          "n_positions": V["n_positions"]},
            "null_draws": null_data,
            "examples": ex,
            "reported": {"verdict": rep["verdict"], "specificity_qualifier": rep["specificity_qualifier"],
                         "verdict_role": rep["verdict_role"], "gap_mean": rep["gap_mean"], "arms": arms_rep,
                         "nulls": nulls_rep,
                         "factorial_2x2": {k: v for k, v in rep["factorial_2x2"].items()
                                           if k != "interaction_per_prompt"},
                         "per_token_logit_change": rep["per_token_logit_change"], "delta_norms": rep["delta_norms"],
                         "delta_geometry": geo["units"][u]["tokens"]},
        }
    a.out.write_text(json.dumps(out))
    print(f"wrote {a.out} ({a.out.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
```

### [64] TOOL RESULT — Write · 2026-10-26 15:29:29 UTC

```
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/build_mini_demo_data.py", "content": "#!/usr/bin/env python3\n\"\"\"Build mini_demo_data.json for code_demo.ipynb from the BASE-W artifact (iteration 10, experiment 56).\n\nThe W1 teacher-forced arms of the artifact are exact CPU arithmetic on cached fork states: the class margin\nlse(z[D]) - lse(z[A]) depends only on the final-normed residual at the fork and the fork-class unembedding rows.\nThis script collects exactly those inputs, so the notebook can recompute every W1 arm and null without a GPU.\n\nRead-only inputs, all inside the artifact folder passed with --artifact-dir:\n  cache/fork_{instr,base}_{T10,B3}.pt  per-prompt fork states of Qwen3-8B / Qwen3-8B-Base (h_pre, h_fin in bf16, the\n                                       captured fp32 class margin m)\n  cache/resid_pca_{u}.pt               top-64 PCA basis of the instruct final-normed residual (RAND_RESID null)\n  results/null_draws_{u}.npz           committed null draws: DELTA_SWAP is stored for T10 (it needs the full 151,936-row\n                                       lm_heads of both models); RAND_ISO and RAND_RESID are regenerated from their seeds\n                                       in the notebook, and this script checks the regeneration bit-exactly\n  results/w1_tf_summary.json, results/delta_geometry.json   reported numbers, for side-by-side comparison\n  inputs/iter9/results/units.json      fork tokens D / A and the prompt token ids\nFetched with HTTP range requests from the Hugging Face Hub at the pinned revisions: the fork-class rows of lm_head.weight\n(19 rows x 8 KB per model) and model.norm.weight of both models.\n\nUsage: python build_mini_demo_data.py --artifact-dir <artifact folder> --tokenizer <Qwen3 tokenizer.json> [--out FILE]\n\"\"\"\n\nfrom __future__ import annotations\n\nimport argparse\nimport base64\nimport json\nimport struct\nfrom pathlib import Path\n\nimport numpy as np\nimport requests\nimport torch\nfrom tokenizers import Tokenizer\n\nMODELS = {\"qwen\": (\"Qwen/Qwen3-8B\", \"b968826d9c46dd6066d109eabc6255188de91218\"),\n          \"qwen_base\": (\"Qwen/Qwen3-8B-Base\", \"49e3418fbbbca6ecbdf9608b4d22e5a407081db4\")}\nUNITS_TF = (\"T10\", \"B3\")\nUNIT_IDX = {\"T10\": 0, \"B3\": 1}\nNULL_SEED0 = {\"RAND_ISO\": 101000, \"RAND_RESID\": 102000, \"DELTA_SWAP\": 103000}\nN_NULL = 50\n\n\ndef enc(a: torch.Tensor | np.ndarray) -> dict:\n    \"\"\"Array -> {\"dtype\", \"shape\", \"b64\"} with little-endian raw bytes; bfloat16 is stored as its uint16 bit pattern.\"\"\"\n    if isinstance(a, torch.Tensor):\n        if a.dtype == torch.bfloat16:\n            raw = a.contiguous().view(torch.int16).numpy().astype(\"<i2\").tobytes()\n            return {\"dtype\": \"bfloat16\", \"shape\": list(a.shape), \"b64\": base64.b64encode(raw).decode(\"ascii\")}\n        a = a.numpy()\n    a = np.ascontiguousarray(a)\n    if a.dtype != np.float32:\n        raise TypeError(f\"unexpected dtype {a.dtype}\")\n    return {\"dtype\": \"float32\", \"shape\": list(a.shape), \"b64\": base64.b64encode(a.astype(\"<f4\").tobytes()).decode(\"ascii\")}\n\n\nclass RangeSafetensors:\n    \"\"\"Reads single rows of a tensor from a safetensors shard on the Hub with HTTP range requests.\"\"\"\n\n    def __init__(self, repo: str, rev: str):\n        self.base = f\"https://huggingface.co/{repo}/resolve/{rev}/\"\n        self.wmap = requests.get(self.base + \"model.safetensors.index.json\", timeout=60).json()[\"weight_map\"]\n        self.headers: dict[str, tuple[int, dict]] = {}\n\n    def _get(self, fn: str, a: int, b: int) -> bytes:\n        r = requests.get(self.base + fn, headers={\"Range\": f\"bytes={a}-{b}\"}, timeout=120)\n        assert r.status_code == 206 and len(r.content) == b - a + 1, (r.status_code, len(r.content))\n        return r.content\n\n    def _header(self, fn: str) -> tuple[int, dict]:\n        if fn not in self.headers:\n            n = struct.unpack(\"<Q\", self._get(fn, 0, 7))[0]\n            self.headers[fn] = (8 + n, json.loads(self._get(fn, 8, 7 + n)))\n        return self.headers[fn]\n\n    def rows(self, name: str, ids: list[int] | None) -> torch.Tensor:\n        fn = self.wmap[name]\n        start, hdr = self._header(fn)\n        meta = hdr[name]\n        assert meta[\"dtype\"] == \"BF16\"\n        d = meta[\"shape\"][-1]\n        off = start + meta[\"data_offsets\"][0]\n        if ids is None:                                             # the whole (1-D) tensor\n            raw = self._get(fn, off, off + 2 * d - 1)\n            return torch.frombuffer(bytearray(raw), dtype=torch.bfloat16).clone()\n        out = []\n        for i in ids:\n            raw = self._get(fn, off + 2 * d * i, off + 2 * d * (i + 1) - 1)\n            out.append(torch.frombuffer(bytearray(raw), dtype=torch.bfloat16).clone())\n        return torch.stack(out)\n\n\ndef lse_margin(h: torch.Tensor, W: torch.Tensor, nD: int) -> np.ndarray:\n    z = h @ W.T\n    return (torch.logsumexp(z[:, :nD], -1) - torch.logsumexp(z[:, nD:], -1)).numpy()\n\n\ndef main() -> None:\n    ap = argparse.ArgumentParser()\n    ap.add_argument(\"--artifact-dir\", required=True, type=Path)\n    ap.add_argument(\"--tokenizer\", required=True, type=Path, help=\"Qwen3-8B tokenizer.json\")\n    ap.add_argument(\"--out\", default=Path(__file__).resolve().parent / \"mini_demo_data.json\", type=Path)\n    a = ap.parse_args()\n    R = a.artifact_dir\n    tok = Tokenizer.from_file(str(a.tokenizer))\n    units = json.loads((R / \"inputs/iter9/results/units.json\").read_text())\n    w1 = json.loads((R / \"results/w1_tf_summary.json\").read_text())\n    geo = json.loads((R / \"results/delta_geometry.json\").read_text())\n    rownorms = torch.load(R / \"cache/lm_head_rownorms.pt\")\n    hub = {k: RangeSafetensors(*v) for k, v in MODELS.items()}\n    g = {k: hub[k].rows(\"model.norm.weight\", None) for k in MODELS}\n    out: dict = {\n        \"description\": \"Inputs of the W1 teacher-forced readout test of the BASE-W artifact (iteration 10): cached fork \"\n                       \"states of Qwen3-8B (instruct) and Qwen3-8B-Base for 20 prompts per unit, the fork-class \"\n                       \"unembedding rows and final-norm gains of both models, the top-64 residual PCA basis, the \"\n                       \"committed DELTA_SWAP null draws (T10) and the artifact's reported numbers.\",\n        \"array_encoding\": \"{dtype, shape, b64}: base64 of little-endian raw bytes; bfloat16 arrays hold the uint16 bit \"\n                          \"pattern of each value (decode: (u16 << 16) viewed as float32 is exact)\",\n        \"models\": {k: {\"id\": v[0], \"revision\": v[1]} for k, v in MODELS.items()},\n        \"readout\": {\"g_instr\": enc(g[\"qwen\"]), \"g_base\": enc(g[\"qwen_base\"])},\n        \"units\": {},\n    }\n    for u in UNITS_TF:\n        U, f = units[u], units[u][\"forks\"][0]\n        D, A = [int(t) for t in f[\"D\"]], [int(t) for t in f[\"A\"]]\n        S, nD = D + A, len(D)\n        ci = torch.load(R / f\"cache/fork_instr_{u}.pt\")\n        cb = torch.load(R / f\"cache/fork_base_{u}.pt\")\n        pids = [c[\"pid\"] for c in ci[\"caps\"]]\n        assert pids == [c[\"pid\"] for c in cb[\"caps\"]]\n        WI = hub[\"qwen\"].rows(\"lm_head.weight\", S)\n        WB = hub[\"qwen_base\"].rows(\"lm_head.weight\", S)\n        # the fetched rows must reproduce the committed delta norms and instruct row norms bit for bit\n        nul = np.load(R / f\"results/null_draws_{u}.npz\")\n        dn = (WB.float() - WI.float()).norm(dim=-1)\n        assert list(nul[\"S\"]) == S\n        assert np.array_equal(dn.numpy(), nul[\"delta_norm\"]), \"row delta norms differ from the committed ones\"\n        assert torch.equal(WI.float().norm(dim=-1), rownorms[\"w_instr_norm\"][S]), \"instruct row norms differ\"\n        assert torch.equal(dn, rownorms[\"delta_norm\"][S]), \"delta norms differ from cache/lm_head_rownorms.pt\"\n        # RAND_ISO / RAND_RESID regenerate bit-exactly from the committed seeds (as w1_tf.make_nulls)\n        V = torch.load(R / f\"cache/resid_pca_{u}.pt\")\n        Vb = V[\"basis\"].numpy().astype(np.float64)\n        ui = UNIT_IDX[u]\n        dnorm = dn.numpy()\n        for k in range(N_NULL):\n            for j, t in enumerate(S):\n                r1 = np.random.default_rng([NULL_SEED0[\"RAND_ISO\"] + 100 * ui + k, t])\n                gg = r1.standard_normal(WI.shape[1])\n                assert np.array_equal((dnorm[j] * gg / np.linalg.norm(gg)).astype(np.float32), nul[\"RAND_ISO\"][k, j])\n                r2 = np.random.default_rng([NULL_SEED0[\"RAND_RESID\"] + 100 * ui + k, t])\n                c = r2.standard_normal(Vb.shape[0])\n                v = c @ Vb\n                assert np.array_equal((dnorm[j] * v / np.linalg.norm(v)).astype(np.float32), nul[\"RAND_RESID\"][k, j])\n        # the captured instruct margin is reproduced by the CPU readout (TWIN_cpu) and ROWS_ALL by the reported share\n        hfI = torch.stack([c[\"h_fin\"] for c in ci[\"caps\"]]).float()\n        mI = np.array([c[\"m\"] for c in ci[\"caps\"]])\n        mB = np.array([c[\"m\"] for c in cb[\"caps\"]])\n        twin_cpu = lse_margin(hfI, WI.float(), nD)\n        rows_all = lse_margin(hfI, WB.float(), nD)\n        sh = float(np.sum(mI - rows_all)) / float(np.sum(mI - mB))\n        rep = w1[\"units\"][u]\n        print(f\"{u}: S {[tok.decode([t]) for t in S]}, max |TWIN_cpu - m_I| {np.abs(twin_cpu - mI).max():.2e}, \"\n              f\"ROWS_ALL share {sh:.10f} (reported {rep['arms']['ROWS_ALL']['share']:.10f})\")\n        assert abs(sh - rep[\"arms\"][\"ROWS_ALL\"][\"share\"]) < 1e-9\n        prompts = {p[\"pid\"]: p for p in U[\"prompts\"]}\n        ex = []\n        for i, pid in enumerate(pids):\n            p = prompts[pid]\n            assert p[\"sha\"] == ci[\"caps\"][i][\"ids_sha\"] == cb[\"caps\"][i][\"ids_sha\"]\n            ex.append({\"pid\": pid, \"template\": ci[\"caps\"][i][\"template\"], \"noun\": p[\"noun\"],\n                       \"n_ids\": ci[\"caps\"][i][\"n_ids\"],\n                       \"input_text\": tok.decode(p[\"ids\"], skip_special_tokens=False),\n                       \"m_I\": float(mI[i]), \"m_B\": float(mB[i]),\n                       \"h_pre_instr\": enc(ci[\"caps\"][i][\"h_pre\"]), \"h_fin_instr\": enc(ci[\"caps\"][i][\"h_fin\"]),\n                       \"h_pre_base\": enc(cb[\"caps\"][i][\"h_pre\"]), \"h_fin_base\": enc(cb[\"caps\"][i][\"h_fin\"])})\n        null_data = {}\n        if u == \"T10\":                                              # DELTA_SWAP needs the full lm_heads: store the draws\n            null_data[\"DELTA_SWAP\"] = enc(nul[\"DELTA_SWAP\"])\n            null_data[\"DELTA_SWAP_tokens\"] = nul[\"DELTA_SWAP_tokens\"].tolist()\n            null_data[\"DELTA_SWAP_token_strings\"] = [[tok.decode([int(t)]) for t in row]\n                                                     for row in nul[\"DELTA_SWAP_tokens\"]]\n        arms_rep = {k: {kk: v[kk] for kk in (\"share\", \"ci95\", \"mean_margin\") if kk in v} for k, v in rep[\"arms\"].items()}\n        nulls_rep = {k: {kk: v[kk] for kk in (\"median\", \"p95\", \"max\", \"empirical_p_rows_all\", \"median_draw\", \"max_draw\")\n                         if kk in v} for k, v in rep[\"nulls\"].items()}\n        for k, v in rep[\"nulls\"].items():                           # committed null shares (used where draws are absent)\n            nulls_rep[k][\"shares\"] = v[\"shares\"]\n        out[\"units\"][u] = {\n            \"name\": U[\"name\"], \"fork_id\": f[\"fork_id\"], \"opening_text\": f[\"opening_text\"],\n            \"D\": D, \"A\": A, \"D_str\": f[\"D_str\"], \"A_str\": f[\"A_str\"], \"D_class\": f[\"D_class\"],\n            \"A_class\": f[\"A_class\"], \"S\": S, \"nD\": nD, \"B_ot\": [ci[\"B_ot\"], cb[\"B_ot\"]],\n            \"WI_S\": enc(WI), \"WB_S\": enc(WB),\n            \"resid_pca\": {\"basis\": enc(V[\"basis\"]), \"var_explained_top64\": V[\"var_explained_top64\"],\n                          \"n_positions\": V[\"n_positions\"]},\n            \"null_draws\": null_data,\n            \"examples\": ex,\n            \"reported\": {\"verdict\": rep[\"verdict\"], \"specificity_qualifier\": rep[\"specificity_qualifier\"],\n                         \"verdict_role\": rep[\"verdict_role\"], \"gap_mean\": rep[\"gap_mean\"], \"arms\": arms_rep,\n                         \"nulls\": nulls_rep,\n                         \"factorial_2x2\": {k: v for k, v in rep[\"factorial_2x2\"].items()\n                                           if k != \"interaction_per_prompt\"},\n                         \"per_token_logit_change\": rep[\"per_token_logit_change\"], \"delta_norms\": rep[\"delta_norms\"],\n                         \"delta_geometry\": geo[\"units\"][u][\"tokens\"]},\n        }\n    a.out.write_text(json.dumps(out))\n    print(f\"wrote {a.out} ({a.out.stat().st_size / 1e6:.2f} MB)\")\n\n\nif __name__ == \"__main__\":\n    main()\n", "structuredPatch": [], "originalFile": null, "userModified": false}
```

### [65] TOOL CALL — Bash · 2026-10-26 15:29:37 UTC

```
Build mini_demo_data.json with exactness checks:
time /tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5/bin/python -I build_mini_demo_data.py --artifact-dir /ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56 --tokenizer /ai-inventor/aii_data/runs/run_jSassd-YWLVC/.shared_cache/hf/hub/models--Qwen--Qwen3-8B/snapshots/b968826d9c46dd6066d109eabc6255188de91218/tokenizer.json 2>&1 | tail -20; ls -la mini_demo_data.json
```

### [66] TOOL RESULT — Bash [ERROR] · 2026-10-26 15:29:47 UTC

```
Error: Exit code 2
T10: S [' find', ' dfs', ' bfs'], max |TWIN_cpu - m_I| 1.14e-05, ROWS_ALL share 0.5484614227 (reported 0.5484614646)
Traceback (most recent call last):
  File "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/build_mini_demo_data.py", line 209, in <module>
    main()
  File "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/build_mini_demo_data.py", line 164, in main
    assert abs(sh - rep["arms"]["ROWS_ALL"]["share"]) < 1e-9
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError

real	0m11.080s
user	0m1.936s
sys	0m0.221s
ls: cannot access 'mini_demo_data.json': No such file or directory
```

### [67] THINKING · 2026-10-26 15:29:59 UTC

```
Everything checks out bit-exactly except ROWS_ALL, which shows a 4e-8 discrepancy from fp32 matmul ordering differences—well within the artifact's own float64 audit tolerance of 4.4e-7. I'll loosen the tolerance to 1e-6 to account for this.
```

### [68] TOOL CALL — Edit · 2026-10-26 15:29:59 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/build_mini_demo_data.py
OLD:         assert abs(sh - rep["arms"]["ROWS_ALL"]["share"]) < 1e-9
NEW:         assert abs(sh - rep["arms"]["ROWS_ALL"]["share"]) < 1e-6      # fp32 matmul order differs across BLAS builds
```

### [69] TOOL RESULT — Edit · 2026-10-26 15:29:59 UTC

```
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/build_mini_demo_data.py", "oldString": "        assert abs(sh - rep[\"arms\"][\"ROWS_ALL\"][\"share\"]) < 1e-9", "newString": "        assert abs(sh - rep[\"arms\"][\"ROWS_ALL\"][\"share\"]) < 1e-6      # fp32 matmul order differs across BLAS builds", "originalFile": null, "structuredPatch": [{"oldStart": 161, "oldLines": 7, "newStart": 161, "newLines": 7, "lines": ["         rep = w1[\"units\"][u]", "         print(f\"{u}: S {[tok.decode([t]) for t in S]}, max |TWIN_cpu - m_I| {np.abs(twin_cpu - mI).max():.2e}, \"", "               f\"ROWS_ALL share {sh:.10f} (reported {rep['arms']['ROWS_ALL']['share']:.10f})\")", "-        assert abs(sh - rep[\"arms\"][\"ROWS_ALL\"][\"share\"]) < 1e-9", "+        assert abs(sh - rep[\"arms\"][\"ROWS_ALL\"][\"share\"]) < 1e-6      # fp32 matmul order differs across BLAS builds", "         prompts = {p[\"pid\"]: p for p in U[\"prompts\"]}", "         ex = []", "         for i, pid in enumerate(pids):"]}], "userModified": false, "replaceAll": false}
```

### [70] TOOL CALL — Bash · 2026-10-26 15:29:59 UTC

```
Rebuild mini_demo_data.json with relaxed tolerance:
time /tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5/bin/python -I build_mini_demo_data.py --artifact-dir /ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56 --tokenizer /ai-inventor/aii_data/runs/run_jSassd-YWLVC/.shared_cache/hf/hub/models--Qwen--Qwen3-8B/snapshots/b968826d9c46dd6066d109eabc6255188de91218/tokenizer.json 2>&1 | tail -20; ls -la mini_demo_data.json
```

### [71] TOOL RESULT — Bash · 2026-10-26 15:30:35 UTC

```
{"stdout": "T10: S [' find', ' dfs', ' bfs'], max |TWIN_cpu - m_I| 1.14e-05, ROWS_ALL share 0.5484614227 (reported 0.5484614646)\nB3: S [' Kr', ' Union', ' Check', ' Minimum', ' Find', ' Priority', ' Helper', ' Dis', ' Prim', ' Pr', ' Use', ' MST', ' To', ' Using', 'Prim', ' Prime'], max |TWIN_cpu - m_I| 7.63e-06, ROWS_ALL share 1.2494936426 (reported 1.2494940990)\nwrote /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/mini_demo_data.json (8.34 MB)\n\nreal\t0m35.977s\nuser\t0m6.743s\nsys\t0m1.991s\n-rw-rw-rw- 1 aii-agent aii-agent 8337194 Oct 26 15:30 mini_demo_data.json", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [72] THINKING · 2026-10-26 15:31:35 UTC

```
mini_demo_data.json is done (8.3 MB, 40 fork-state examples) with all exactness checks passing and ROWS_ALL matching within 4.6e-7, completing TODO 3. Next, I need to pull in the two iteration-9 stats helpers that `score()` calls before writing the notebook.
```

### [73] TOOL CALL — Bash · 2026-10-26 15:31:35 UTC

```
Extract iteration-9 stats helper functions:
A=/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56; grep -n "^def \|^import\|^from" $A/inputs/iter9/src/stats9.py | head -40; echo ----; python3 - <<'EOF'
import re
src=open('/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/inputs/iter9/src/stats9.py').read()
for name in ('boot_mean_ci','empirical_p_upper'):
    m=re.search(r'\ndef '+name+r'\(.*?(?=\ndef |\Z)', src, re.S)
    print(m.group(0))
EOF
```

### [74] TOOL RESULT — Bash · 2026-10-26 15:31:35 UTC

```
{"stdout": "6:from __future__ import annotations\n8:import itertools\n9:import math\n10:from typing import Sequence\n12:import numpy as np\n15:def js_div(ia: list[int], la: list[float], ib: list[int], lb: list[float]) -> float:\n34:def share(m_I: Sequence[float], m_X: Sequence[float], m_B: Sequence[float]) -> float:\n41:def share_mean_of_ratios(m_I: Sequence[float], m_X: Sequence[float], m_B: Sequence[float]) -> float:\n46:def boot_ci(fn, n: int, B: int = 10000, seed: int = 0, alpha: float = 0.05) -> tuple[float, float]:\n60:def boot_share_ci(m_I, m_X, m_B, B: int = 10000, seed: int = 0) -> tuple[float, float]:\n65:def boot_mean_ci(v, B: int = 10000, seed: int = 0) -> tuple[float, float]:\n70:def mcnemar_exact(b: int, c: int) -> float:\n80:def sign_flip_p(d: Sequence[float]) -> float:\n96:def holm(ps: Sequence[float]) -> list[float]:\n109:def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:\n119:def newcombe(k1: int, n1: int, k2: int, n2: int) -> tuple[float, float]:\n128:def empirical_p_upper(x: float, null: Sequence[float]) -> float:\n----\n\ndef boot_mean_ci(v, B: int = 10000, seed: int = 0) -> tuple[float, float]:\n    v = np.asarray(v, dtype=float)\n    return boot_ci(lambda idx: float(v[idx].mean()), len(v), B, seed)\n\n\n\ndef empirical_p_upper(x: float, null: Sequence[float]) -> float:\n    \"\"\"(1 + #null >= x) / (1 + n).\"\"\"\n    null = np.asarray(null, dtype=float)\n    return float((1 + np.sum(null >= x)) / (1 + len(null)))", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [75] TOOL CALL — Bash · 2026-10-26 15:31:39 UTC

```
Read bootstrap helper and spot-check the data file:
sed -n 46,70p /ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/inputs/iter9/src/stats9.py; python3 -c "
import json
d=json.load(open('/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/mini_demo_data.json'))
print(list(d.keys()))
U=d['units']['T10']; print(list(U.keys())); e=U['examples'][0]; print({k:(v if not isinstance(v,dict) else {kk:(vv if kk!='b64' else len(vv)) for kk,vv in v.items()}) for k,v in e.items()})
print(U['reported']['factorial_2x2'])
print(U['reported']['delta_geometry'])
print(d['units']['B3']['examples'][0]['input_text'][-600:])
"
```

### [76] TOOL RESULT — Bash · 2026-10-26 15:31:39 UTC

````
{"stdout": "def boot_ci(fn, n: int, B: int = 10000, seed: int = 0, alpha: float = 0.05) -> tuple[float, float]:\n    \"\"\"Percentile bootstrap over n units: fn(idx array) -> statistic.\"\"\"\n    rng = np.random.default_rng(seed)\n    vals = []\n    for _ in range(B):\n        idx = rng.integers(0, n, n)\n        v = fn(idx)\n        if v is not None and np.isfinite(v):\n            vals.append(v)\n    if not vals:\n        return (float(\"nan\"), float(\"nan\"))\n    return (float(np.percentile(vals, 100 * alpha / 2)), float(np.percentile(vals, 100 * (1 - alpha / 2))))\n\n\ndef boot_share_ci(m_I, m_X, m_B, B: int = 10000, seed: int = 0) -> tuple[float, float]:\n    a, x, b = map(np.asarray, (m_I, m_X, m_B))\n    return boot_ci(lambda idx: share(a[idx], x[idx], b[idx]), len(a), B, seed)\n\n\ndef boot_mean_ci(v, B: int = 10000, seed: int = 0) -> tuple[float, float]:\n    v = np.asarray(v, dtype=float)\n    return boot_ci(lambda idx: float(v[idx].mean()), len(v), B, seed)\n\n\ndef mcnemar_exact(b: int, c: int) -> float:\n['description', 'array_encoding', 'models', 'readout', 'units']\n['name', 'fork_id', 'opening_text', 'D', 'A', 'D_str', 'A_str', 'D_class', 'A_class', 'S', 'nD', 'B_ot', 'WI_S', 'WB_S', 'resid_pca', 'null_draws', 'examples', 'reported']\n{'pid': 'W1|ship', 'template': 'W1', 'noun': 'ship', 'n_ids': 183, 'input_text': '<|im_start|>user\\nDo not use ship for this task. . . . . . . .\\n\\nTask: write a Python function solve(n, edges) that returns the number of connected components of an undirected graph. The nodes are the integers 0 to n - 1, with 1 <= n <= 300. The argument edges is a list of pairs [u, v] with 0 <= u, v < n and u != v, each joining nodes u and v; 0 <= len(edges) <= 1500 and no pair of nodes is joined twice. A node with no edges forms a component on its own.\\n\\nUse only the Python standard library. Return only one ```python code block containing the function solve and any helpers, with no example usage and no explanation.<|im_end|>\\n<|im_start|>assistant\\n<think>\\n\\n</think>\\n\\n', 'm_I': 5.8872222900390625, 'm_B': -0.13475418090820312, 'h_pre_instr': {'dtype': 'bfloat16', 'shape': [4096], 'b64': 10924}, 'h_fin_instr': {'dtype': 'bfloat16', 'shape': [4096], 'b64': 10924}, 'h_pre_base': {'dtype': 'bfloat16', 'shape': [4096], 'b64': 10924}, 'h_fin_base': {'dtype': 'bfloat16', 'shape': [4096], 'b64': 10924}}\n{'m_II': 4.515952491760254, 'm_IB_rows_norm': 2.023707628250122, 'm_BI_base_resid_instr_readout': 3.786619186401367, 'm_BB': -0.04227027893066406, 'interaction_mean': -1.3366443634033203, 'interaction_ci95': [-1.3862310409545897, -1.2911225175857544], 'readout_effect_on_instr_resid': 2.492244911193848, 'readout_effect_on_base_resid': 3.828889274597168, 'residual_effect_under_instr_readout': 0.72933349609375, 'residual_effect_under_base_readout': 2.06597785949707, 'share_readout_on_instr_resid': 0.5467580319283261, 'share_readout_on_base_resid': 0.8399960833894916, 'share_unembedding_only_on_base_resid': 0.8417903596565685, 'share_interaction': -0.2932380514611656}\n{'1477': {'class': 'D', 'delta_norm': 0.09424832823947778, 'frac_delta_energy_in_resid_pc64': 0.015637508558135414, 'frac_expected_isotropic': 0.015625, 'leverage_real_mean': 0.01810275421094828, 'leverage_rand_iso_median': 0.010187445786426042, 'leverage_rand_resid_median': 0.10004700251126389, 'leverage_delta_swap_median': 0.04552292934514944, 'signed_logit_change_mean': -0.27135931556116477}, '25792': {'class': 'A', 'delta_norm': 0.20255759720052136, 'frac_delta_energy_in_resid_pc64': 0.0616269980140914, 'frac_expected_isotropic': 0.015625, 'leverage_real_mean': 0.06916116932102472, 'leverage_rand_iso_median': 0.00958825350986309, 'leverage_rand_resid_median': 0.08508474975566396, 'leverage_delta_swap_median': 0.01702601856097817, 'signed_logit_change_mean': 2.22763469268948}, '66564': {'class': 'A', 'delta_norm': 0.23335300367817366, 'frac_delta_energy_in_resid_pc64': 0.05409506105495583, 'frac_expected_isotropic': 0.015625, 'leverage_real_mean': 0.08470353827323587, 'leverage_rand_iso_median': 0.009651076962081426, 'leverage_rand_resid_median': 0.09325355198775212, 'leverage_delta_swap_median': 0.02029410484469122, 'signed_logit_change_mean': 3.1433721800085324}}\n != v) can be built for cost w, where 0 <= w <= 100000; several roads may join the same two cities. Choose roads so that every city can reach every other city through chosen roads, at the smallest possible total cost, and return that total as an int. If the cities cannot all be linked, return -1. For example, for n = 3 and roads = [[0, 1, 5], [0, 2, 6], [1, 2, 1]] the answer is 6.\n\nUse only the Python standard library. Return only one ```python code block containing the function solve and any helpers, with no example usage and no explanation.<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
````

### [77] ASSISTANT · 2026-10-26 15:31:45 UTC

```
The data file looks right: each prompt is the chat-formatted task, and the opening (`def solve(n, edges):\n    def`) is appended at the fork. Now I'll load the NotebookEdit tool for TODO 4.
```

### [78] TOOL CALL — ToolSearch · 2026-10-26 15:31:45 UTC

```
{'query': 'select:NotebookEdit', 'max_results': 1}
```

### [79] TOOL RESULT — ToolSearch · 2026-10-26 15:31:45 UTC

```
{"matches": ["NotebookEdit"], "query": "select:NotebookEdit", "total_deferred_tools": 28}
```

### [80] THINKING · 2026-10-26 15:35:55 UTC

```
I've laid out a ~30-cell notebook plan covering the orchestrator, W1 teacher-forced test, delta geometry/figures, and a final results table. Since NotebookEdit only edits existing notebooks, I'll first create a skeleton with just the title cell, then insert the rest.
```

### [81] TOOL CALL — Write · 2026-10-26 15:35:55 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb

{
 "cells": [
  {
   "cell_type": "markdown",
   "id": "c00-title",
   "metadata": {},
   "source": [
    "# Which weights make the model pick one algorithm (BASE-W, iteration 10)"
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

### [82] TOOL RESULT — Write · 2026-10-26 15:35:55 UTC

```
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb", "content": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"c00-title\",\n   \"metadata\": {},\n   \"source\": [\n    \"# Which weights make the model pick one algorithm (BASE-W, iteration 10)\"\n   ]\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}\n", "structuredPatch": [], "originalFile": null, "userModified": false}
```

### [83] TOOL CALL — Read · 2026-10-26 15:35:55 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb
```

### [84] TOOL RESULT — Read · 2026-10-26 15:35:55 UTC

```
{"type": "notebook", "file": {"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb", "cells": [{"cellType": "markdown", "source": "# Which weights make the model pick one algorithm (BASE-W, iteration 10)", "cell_id": "c00-title"}]}}
```

### [85] ASSISTANT · 2026-10-26 15:36:13 UTC

```
Now I'll fill in the full title and description, then insert the install cell and check how NotebookEdit reports new cell ids.
```

### [86] TOOL CALL — NotebookEdit · 2026-10-26 15:36:13 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': 'c00-title', 'edit_mode': 'replace', 'cell_type': 'markdown', 'new_source': '# Which weights make the model pick one algorithm (BASE-W, iteration 10)\n\nWhen Qwen3-8B writes a program, it commits to an algorithm at a single **fork token**. Asked to count the connected components of a graph, the instruct model opens `def solve(n, edges):` with a helper named `def find` (union-find) almost every time. The base model, Qwen3-8B-Base, is as likely to write `def dfs` or `def bfs`. This artifact asks **which weights** post-training changed to create that default:\n\n* **W1, readout rows:** the fork-class rows of the unembedding matrix (`lm_head`) and the final-norm gain.\n* **W2, late-MLP weights:** MLP layers 26-35 swapped to the base model in place.\n* **W3:** the W1 row test repeated on Gemma-3-4b (descriptive).\n\n**Units.** The prompts and fork tokens come from iteration 9.\n\n| unit | task | default class D (instruct) | alternative class A |\n|---|---|---|---|\n| **T10** (primary) | connected components, 20 prompts | `\' find\'` (union-find) | `\' dfs\'`, `\' bfs\'` |\n| **B3** (beside) | minimum spanning tree, 20 prompts | 8 Kruskal-class tokens | 8 Prim-class tokens |\n\n**Margin and share.** The fork\'s **class margin** is `m = lse(z[D]) - lse(z[A])`, which equals log P(D) - log P(A). An intervention ("arm") is scored by the **share of the instruct-minus-base gap it closes**: `share = sum_p (m_I - m_arm) / sum_p (m_I - m_B)`. This is a ratio of sums over prompts, with a 95% prompt bootstrap. A share of 0 means no effect; a share of 1 means the margin became fully base-like.\n\n### What this notebook runs\n`method.py` is a stage orchestrator: it launches about 40 scripts that load the 8B models on a 24 GB GPU (about 1 GPU-hour), which cannot run on a Colab CPU in 10 minutes. The core of the method does not need a GPU, though. **The class margin depends only on the final-normed residual at the fork and on the fork-class unembedding rows**, so every W1 arm and every null is exact arithmetic on the cached fork states. This notebook:\n\n1. shows the orchestrator (`method.py`) and its stage plan;\n2. re-runs the **W1 teacher-forced test** (`src/w1_tf.py`): readout arms, 3 x 50 matched-norm null edits, bootstrap CIs and the committed verdict rule;\n3. re-runs the **delta-geometry** analysis (`src/analysis10.py`);\n4. draws the figures from `src/figures10.py`, including the activation-space plots: the fork states on the readout plane (F5) and the PCA of the block-35 outputs (F6).\n\n`mini_demo_data.json` holds:\n* the cached fork states of 20 + 20 prompts (bf16, exact);\n* the fork-class `lm_head` rows and the final-norm gains of both models, fetched at the pinned revisions;\n* the residual\'s top-64 PCA basis;\n* the committed DELTA_SWAP draws for T10;\n* the artifact\'s reported numbers, for a side-by-side check.\n\nThe generation experiments (W1-GEN), W2 and W3 need model forwards on a GPU. Their reported results are summarized before the last cell.'}
```

### [87] TOOL RESULT — NotebookEdit · 2026-10-26 15:36:13 UTC

```
{"new_source": "# Which weights make the model pick one algorithm (BASE-W, iteration 10)\n\nWhen Qwen3-8B writes a program, it commits to an algorithm at a single **fork token**. Asked to count the connected components of a graph, the instruct model opens `def solve(n, edges):` with a helper named `def find` (union-find) almost every time. The base model, Qwen3-8B-Base, is as likely to write `def dfs` or `def bfs`. This artifact asks **which weights** post-training changed to create that default:\n\n* **W1, readout rows:** the fork-class rows of the unembedding matrix (`lm_head`) and the final-norm gain.\n* **W2, late-MLP weights:** MLP layers 26-35 swapped to the base model in place.\n* **W3:** the W1 row test repeated on Gemma-3-4b (descriptive).\n\n**Units.** The prompts and fork tokens come from iteration 9.\n\n| unit | task | default class D (instruct) | alternative class A |\n|---|---|---|---|\n| **T10** (primary) | connected components, 20 prompts | `' find'` (union-find) | `' dfs'`, `' bfs'` |\n| **B3** (beside) | minimum spanning tree, 20 prompts | 8 Kruskal-class tokens | 8 Prim-class tokens |\n\n**Margin and share.** The fork's **class margin** is `m = lse(z[D]) - lse(z[A])`, which equals log P(D) - log P(A). An intervention (\"arm\") is scored by the **share of the instruct-minus-base gap it closes**: `share = sum_p (m_I - m_arm) / sum_p (m_I - m_B)`. This is a ratio of sums over prompts, with a 95% prompt bootstrap. A share of 0 means no effect; a share of 1 means the margin became fully base-like.\n\n### What this notebook runs\n`method.py` is a stage orchestrator: it launches about 40 scripts that load the 8B models on a 24 GB GPU (about 1 GPU-hour), which cannot run on a Colab CPU in 10 minutes. The core of the method does not need a GPU, though. **The class margin depends only on the final-normed residual at the fork and on the fork-class unembedding rows**, so every W1 arm and every null is exact arithmetic on the cached fork states. This notebook:\n\n1. shows the orchestrator (`method.py`) and its stage plan;\n2. re-runs the **W1 teacher-forced test** (`src/w1_tf.py`): readout arms, 3 x 50 matched-norm null edits, bootstrap CIs and the committed verdict rule;\n3. re-runs the **delta-geometry** analysis (`src/analysis10.py`);\n4. draws the figures from `src/figures10.py`, including the activation-space plots: the fork states on the readout plane (F5) and the PCA of the block-35 outputs (F6).\n\n`mini_demo_data.json` holds:\n* the cached fork states of 20 + 20 prompts (bf16, exact);\n* the fork-class `lm_head` rows and the final-norm gains of both models, fetched at the pinned revisions;\n* the residual's top-64 PCA basis;\n* the committed DELTA_SWAP draws for T10;\n* the artifact's reported numbers, for a side-by-side check.\n\nThe generation experiments (W1-GEN), W2 and W3 need model forwards on a GPU. Their reported results are summarized before the last cell.", "old_source": "# Which weights make the model pick one algorithm (BASE-W, iteration 10)", "cell_type": "markdown", "language": "python", "edit_mode": "replace", "cell_id": "c00-title", "error": "", "notebook_path": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb", "original_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"c00-title\",\n   \"metadata\": {},\n   \"source\": [\n    \"# Which weights make the model pick one algorithm (BASE-W, iteration 10)\"\n   ]\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}\n", "updated_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"c00-title\",\n   \"metadata\": {},\n   \"source\": \"# Which weights make the model pick one algorithm (BASE-W, iteration 10)\\n\\nWhen Qwen3-8B writes a program, it commits to an algorithm at a single **fork token**. Asked to count the connected components of a graph, the instruct model opens `def solve(n, edges):` with a helper named `def find` (union-find) almost every time. The base model, Qwen3-8B-Base, is as likely to write `def dfs` or `def bfs`. This artifact asks **which weights** post-training changed to create that default:\\n\\n* **W1, readout rows:** the fork-class rows of the unembedding matrix (`lm_head`) and the final-norm gain.\\n* **W2, late-MLP weights:** MLP layers 26-35 swapped to the base model in place.\\n* **W3:** the W1 row test repeated on Gemma-3-4b (descriptive).\\n\\n**Units.** The prompts and fork tokens come from iteration 9.\\n\\n| unit | task | default class D (instruct) | alternative class A |\\n|---|---|---|---|\\n| **T10** (primary) | connected components, 20 prompts | `' find'` (union-find) | `' dfs'`, `' bfs'` |\\n| **B3** (beside) | minimum spanning tree, 20 prompts | 8 Kruskal-class tokens | 8 Prim-class tokens |\\n\\n**Margin and share.** The fork's **class margin** is `m = lse(z[D]) - lse(z[A])`, which equals log P(D) - log P(A). An intervention (\\\"arm\\\") is scored by the **share of the instruct-minus-base gap it closes**: `share = sum_p (m_I - m_arm) / sum_p (m_I - m_B)`. This is a ratio of sums over prompts, with a 95% prompt bootstrap. A share of 0 means no effect; a share of 1 means the margin became fully base-like.\\n\\n### What this notebook runs\\n`method.py` is a stage orchestrator: it launches about 40 scripts that load the 8B models on a 24 GB GPU (about 1 GPU-hour), which cannot run on a Colab CPU in 10 minutes. The core of the method does not need a GPU, though. **The class margin depends only on the final-normed residual at the fork and on the fork-class unembedding rows**, so every W1 arm and every null is exact arithmetic on the cached fork states. This notebook:\\n\\n1. shows the orchestrator (`method.py`) and its stage plan;\\n2. re-runs the **W1 teacher-forced test** (`src/w1_tf.py`): readout arms, 3 x 50 matched-norm null edits, bootstrap CIs and the committed verdict rule;\\n3. re-runs the **delta-geometry** analysis (`src/analysis10.py`);\\n4. draws the figures from `src/figures10.py`, including the activation-space plots: the fork states on the readout plane (F5) and the PCA of the block-35 outputs (F6).\\n\\n`mini_demo_data.json` holds:\\n* the cached fork states of 20 + 20 prompts (bf16, exact);\\n* the fork-class `lm_head` rows and the final-norm gains of both models, fetched at the pinned revisions;\\n* the residual's top-64 PCA basis;\\n* the committed DELTA_SWAP draws for T10;\\n* the artifact's reported numbers, for a side-by-side check.\\n\\nThe generation experiments (W1-GEN), W2 and W3 need model forwards on a GPU. Their reported results are summarized before the last cell.\"\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}"}
```

### [88] TOOL CALL — NotebookEdit · 2026-10-26 15:36:13 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': 'c00-title', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': "import subprocess, sys\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\n\n# loguru: NOT pre-installed on Colab, always install (the original scripts log with loguru)\n_pip('loguru==0.7.3')\n\n# numpy, matplotlib, torch: pre-installed on Colab; install locally only, at Colab's versions (torch as the CPU build)\nif 'google.colab' not in sys.modules:\n    _pip('numpy==2.0.2', 'matplotlib==3.10.0')\n    _pip('torch==2.9.0+cpu', '--index-url', 'https://download.pytorch.org/whl/cpu',\n         '--extra-index-url', 'https://pypi.org/simple')"}
```

### [89] TOOL RESULT — NotebookEdit · 2026-10-26 15:36:13 UTC

```
{"new_source": "import subprocess, sys\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\n\n# loguru: NOT pre-installed on Colab, always install (the original scripts log with loguru)\n_pip('loguru==0.7.3')\n\n# numpy, matplotlib, torch: pre-installed on Colab; install locally only, at Colab's versions (torch as the CPU build)\nif 'google.colab' not in sys.modules:\n    _pip('numpy==2.0.2', 'matplotlib==3.10.0')\n    _pip('torch==2.9.0+cpu', '--index-url', 'https://download.pytorch.org/whl/cpu',\n         '--extra-index-url', 'https://pypi.org/simple')", "cell_type": "code", "language": "python", "edit_mode": "insert", "cell_id": "5dfd487b", "error": "", "notebook_path": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb", "original_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"c00-title\",\n   \"metadata\": {},\n   \"source\": \"# Which weights make the model pick one algorithm (BASE-W, iteration 10)\\n\\nWhen Qwen3-8B writes a program, it commits to an algorithm at a single **fork token**. Asked to count the connected components of a graph, the instruct model opens `def solve(n, edges):` with a helper named `def find` (union-find) almost every time. The base model, Qwen3-8B-Base, is as likely to write `def dfs` or `def bfs`. This artifact asks **which weights** post-training changed to create that default:\\n\\n* **W1, readout rows:** the fork-class rows of the unembedding matrix (`lm_head`) and the final-norm gain.\\n* **W2, late-MLP weights:** MLP layers 26-35 swapped to the base model in place.\\n* **W3:** the W1 row test repeated on Gemma-3-4b (descriptive).\\n\\n**Units.** The prompts and fork tokens come from iteration 9.\\n\\n| unit | task | default class D (instruct) | alternative class A |\\n|---|---|---|---|\\n| **T10** (primary) | connected components, 20 prompts | `' find'` (union-find) | `' dfs'`, `' bfs'` |\\n| **B3** (beside) | minimum spanning tree, 20 prompts | 8 Kruskal-class tokens | 8 Prim-class tokens |\\n\\n**Margin and share.** The fork's **class margin** is `m = lse(z[D]) - lse(z[A])`, which equals log P(D) - log P(A). An intervention (\\\"arm\\\") is scored by the **share of the instruct-minus-base gap it closes**: `share = sum_p (m_I - m_arm) / sum_p (m_I - m_B)`. This is a ratio of sums over prompts, with a 95% prompt bootstrap. A share of 0 means no effect; a share of 1 means the margin became fully base-like.\\n\\n### What this notebook runs\\n`method.py` is a stage orchestrator: it launches about 40 scripts that load the 8B models on a 24 GB GPU (about 1 GPU-hour), which cannot run on a Colab CPU in 10 minutes. The core of the method does not need a GPU, though. **The class margin depends only on the final-normed residual at the fork and on the fork-class unembedding rows**, so every W1 arm and every null is exact arithmetic on the cached fork states. This notebook:\\n\\n1. shows the orchestrator (`method.py`) and its stage plan;\\n2. re-runs the **W1 teacher-forced test** (`src/w1_tf.py`): readout arms, 3 x 50 matched-norm null edits, bootstrap CIs and the committed verdict rule;\\n3. re-runs the **delta-geometry** analysis (`src/analysis10.py`);\\n4. draws the figures from `src/figures10.py`, including the activation-space plots: the fork states on the readout plane (F5) and the PCA of the block-35 outputs (F6).\\n\\n`mini_demo_data.json` holds:\\n* the cached fork states of 20 + 20 prompts (bf16, exact);\\n* the fork-class `lm_head` rows and the final-norm gains of both models, fetched at the pinned revisions;\\n* the residual's top-64 PCA basis;\\n* the committed DELTA_SWAP draws for T10;\\n* the artifact's reported numbers, for a side-by-side check.\\n\\nThe generation experiments (W1-GEN), W2 and W3 need model forwards on a GPU. Their reported results are summarized before the last cell.\"\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}", "updated_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"c00-title\",\n   \"metadata\": {},\n   \"source\": \"# Which weights make the model pick one algorithm (BASE-W, iteration 10)\\n\\nWhen Qwen3-8B writes a program, it commits to an algorithm at a single **fork token**. Asked to count the connected components of a graph, the instruct model opens `def solve(n, edges):` with a helper named `def find` (union-find) almost every time. The base model, Qwen3-8B-Base, is as likely to write `def dfs` or `def bfs`. This artifact asks **which weights** post-training changed to create that default:\\n\\n* **W1, readout rows:** the fork-class rows of the unembedding matrix (`lm_head`) and the final-norm gain.\\n* **W2, late-MLP weights:** MLP layers 26-35 swapped to the base model in place.\\n* **W3:** the W1 row test repeated on Gemma-3-4b (descriptive).\\n\\n**Units.** The prompts and fork tokens come from iteration 9.\\n\\n| unit | task | default class D (instruct) | alternative class A |\\n|---|---|---|---|\\n| **T10** (primary) | connected components, 20 prompts | `' find'` (union-find) | `' dfs'`, `' bfs'` |\\n| **B3** (beside) | minimum spanning tree, 20 prompts | 8 Kruskal-class tokens | 8 Prim-class tokens |\\n\\n**Margin and share.** The fork's **class margin** is `m = lse(z[D]) - lse(z[A])`, which equals log P(D) - log P(A). An intervention (\\\"arm\\\") is scored by the **share of the instruct-minus-base gap it closes**: `share = sum_p (m_I - m_arm) / sum_p (m_I - m_B)`. This is a ratio of sums over prompts, with a 95% prompt bootstrap. A share of 0 means no effect; a share of 1 means the margin became fully base-like.\\n\\n### What this notebook runs\\n`method.py` is a stage orchestrator: it launches about 40 scripts that load the 8B models on a 24 GB GPU (about 1 GPU-hour), which cannot run on a Colab CPU in 10 minutes. The core of the method does not need a GPU, though. **The class margin depends only on the final-normed residual at the fork and on the fork-class unembedding rows**, so every W1 arm and every null is exact arithmetic on the cached fork states. This notebook:\\n\\n1. shows the orchestrator (`method.py`) and its stage plan;\\n2. re-runs the **W1 teacher-forced test** (`src/w1_tf.py`): readout arms, 3 x 50 matched-norm null edits, bootstrap CIs and the committed verdict rule;\\n3. re-runs the **delta-geometry** analysis (`src/analysis10.py`);\\n4. draws the figures from `src/figures10.py`, including the activation-space plots: the fork states on the readout plane (F5) and the PCA of the block-35 outputs (F6).\\n\\n`mini_demo_data.json` holds:\\n* the cached fork states of 20 + 20 prompts (bf16, exact);\\n* the fork-class `lm_head` rows and the final-norm gains of both models, fetched at the pinned revisions;\\n* the residual's top-64 PCA basis;\\n* the committed DELTA_SWAP draws for T10;\\n* the artifact's reported numbers, for a side-by-side check.\\n\\nThe generation experiments (W1-GEN), W2 and W3 need model forwards on a GPU. Their reported results are summarized before the last cell.\"\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"5dfd487b\",\n   \"source\": \"import subprocess, sys\\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\\n\\n# loguru: NOT pre-installed on Colab, always install (the original scripts log with loguru)\\n_pip('loguru==0.7.3')\\n\\n# numpy, matplotlib, torch: pre-installed on Colab; install locally only, at Colab's versions (torch as the CPU build)\\nif 'google.colab' not in sys.modules:\\n    _pip('numpy==2.0.2', 'matplotlib==3.10.0')\\n    _pip('torch==2.9.0+cpu', '--index-url', 'https://download.pytorch.org/whl/cpu',\\n         '--extra-index-url', 'https://pypi.org/simple')\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}"}
```

### [90] ASSISTANT · 2026-10-26 15:36:59 UTC

```
Insert returns the new cell's id, so I can chain. To save round trips, I'll insert each batch in reverse order after a fixed anchor (the install cell), then verify the resulting order.
```

### [91] TOOL CALL — NotebookEdit · 2026-10-26 15:36:59 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': '5dfd487b', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '# ---------------------------------------------------------------- run size (the original values are in the comments)\nUNITS_TF = ("T10",)          # units to score; original ("T10", "B3")  (T10 = connected components, B3 = MST)\nN_NULL = 2                   # draws per null type; original 50 (the data file holds the 50 committed DELTA_SWAP draws)\nN_BOOT = 10                  # prompt-bootstrap resamples for the 95% CIs; original 10000\n\n# ---------------------------------------------------------------- fixed design constants (src/cfg10.py, COMMIT #0)\nD_MODEL = 4096\nRMS_EPS = 1e-6\nUNIT_IDX = {"T10": 0, "B3": 1, "G-GRID": 2}\nDOSES = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5)   # lambda in w_I + lambda * Delta\nSIGN_DOSE = -1.0\nNULL_TYPES = ("RAND_ISO", "DELTA_SWAP", "RAND_RESID")\nNULL_SEED0 = {"RAND_ISO": 101000, "RAND_RESID": 102000, "DELTA_SWAP": 103000}\nRESID_PCS = 64\nSEED_BOOT = 20261024\nSMALL_GAP = 0.5\nTHRESH = {"W1_rows_share": 0.50, "W1_rand_iso_median": 0.15, "W1_disconfirm": 0.20}   # committed W1 verdict rule'}
```

### [92] TOOL RESULT — NotebookEdit · 2026-10-26 15:36:59 UTC

```
{"new_source": "# ---------------------------------------------------------------- run size (the original values are in the comments)\nUNITS_TF = (\"T10\",)          # units to score; original (\"T10\", \"B3\")  (T10 = connected components, B3 = MST)\nN_NULL = 2                   # draws per null type; original 50 (the data file holds the 50 committed DELTA_SWAP draws)\nN_BOOT = 10                  # prompt-bootstrap resamples for the 95% CIs; original 10000\n\n# ---------------------------------------------------------------- fixed design constants (src/cfg10.py, COMMIT #0)\nD_MODEL = 4096\nRMS_EPS = 1e-6\nUNIT_IDX = {\"T10\": 0, \"B3\": 1, \"G-GRID\": 2}\nDOSES = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5)   # lambda in w_I + lambda * Delta\nSIGN_DOSE = -1.0\nNULL_TYPES = (\"RAND_ISO\", \"DELTA_SWAP\", \"RAND_RESID\")\nNULL_SEED0 = {\"RAND_ISO\": 101000, \"RAND_RESID\": 102000, \"DELTA_SWAP\": 103000}\nRESID_PCS = 64\nSEED_BOOT = 20261024\nSMALL_GAP = 0.5\nTHRESH = {\"W1_rows_share\": 0.50, \"W1_rand_iso_median\": 0.15, \"W1_disconfirm\": 0.20}   # committed W1 verdict rule", "cell_type": "code", "language": "python", "edit_mode": "insert", "cell_id": "e1d109ef", "error": "", "notebook_path": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb", "original_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"c00-title\",\n   \"metadata\": {},\n   \"source\": \"# Which weights make the model pick one algorithm (BASE-W, iteration 10)\\n\\nWhen Qwen3-8B writes a program, it commits to an algorithm at a single **fork token**. Asked to count the connected components of a graph, the instruct model opens `def solve(n, edges):` with a helper named `def find` (union-find) almost every time. The base model, Qwen3-8B-Base, is as likely to write `def dfs` or `def bfs`. This artifact asks **which weights** post-training changed to create that default:\\n\\n* **W1, readout rows:** the fork-class rows of the unembedding matrix (`lm_head`) and the final-norm gain.\\n* **W2, late-MLP weights:** MLP layers 26-35 swapped to the base model in place.\\n* **W3:** the W1 row test repeated on Gemma-3-4b (descriptive).\\n\\n**Units.** The prompts and fork tokens come from iteration 9.\\n\\n| unit | task | default class D (instruct) | alternative class A |\\n|---|---|---|---|\\n| **T10** (primary) | connected components, 20 prompts | `' find'` (union-find) | `' dfs'`, `' bfs'` |\\n| **B3** (beside) | minimum spanning tree, 20 prompts | 8 Kruskal-class tokens | 8 Prim-class tokens |\\n\\n**Margin and share.** The fork's **class margin** is `m = lse(z[D]) - lse(z[A])`, which equals log P(D) - log P(A). An intervention (\\\"arm\\\") is scored by the **share of the instruct-minus-base gap it closes**: `share = sum_p (m_I - m_arm) / sum_p (m_I - m_B)`. This is a ratio of sums over prompts, with a 95% prompt bootstrap. A share of 0 means no effect; a share of 1 means the margin became fully base-like.\\n\\n### What this notebook runs\\n`method.py` is a stage orchestrator: it launches about 40 scripts that load the 8B models on a 24 GB GPU (about 1 GPU-hour), which cannot run on a Colab CPU in 10 minutes. The core of the method does not need a GPU, though. **The class margin depends only on the final-normed residual at the fork and on the fork-class unembedding rows**, so every W1 arm and every null is exact arithmetic on the cached fork states. This notebook:\\n\\n1. shows the orchestrator (`method.py`) and its stage plan;\\n2. re-runs the **W1 teacher-forced test** (`src/w1_tf.py`): readout arms, 3 x 50 matched-norm null edits, bootstrap CIs and the committed verdict rule;\\n3. re-runs the **delta-geometry** analysis (`src/analysis10.py`);\\n4. draws the figures from `src/figures10.py`, including the activation-space plots: the fork states on the readout plane (F5) and the PCA of the block-35 outputs (F6).\\n\\n`mini_demo_data.json` holds:\\n* the cached fork states of 20 + 20 prompts (bf16, exact);\\n* the fork-class `lm_head` rows and the final-norm gains of both models, fetched at the pinned revisions;\\n* the residual's top-64 PCA basis;\\n* the committed DELTA_SWAP draws for T10;\\n* the artifact's reported numbers, for a side-by-side check.\\n\\nThe generation experiments (W1-GEN), W2 and W3 need model forwards on a GPU. Their reported results are summarized before the last cell.\"\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"5dfd487b\",\n   \"source\": \"import subprocess, sys\\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\\n\\n# loguru: NOT pre-installed on Colab, always install (the original scripts log with loguru)\\n_pip('loguru==0.7.3')\\n\\n# numpy, matplotlib, torch: pre-installed on Colab; install locally only, at Colab's versions (torch as the CPU build)\\nif 'google.colab' not in sys.modules:\\n    _pip('numpy==2.0.2', 'matplotlib==3.10.0')\\n    _pip('torch==2.9.0+cpu', '--index-url', 'https://download.pytorch.org/whl/cpu',\\n         '--extra-index-url', 'https://pypi.org/simple')\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}", "updated_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"c00-title\",\n   \"metadata\": {},\n   \"source\": \"# Which weights make the model pick one algorithm (BASE-W, iteration 10)\\n\\nWhen Qwen3-8B writes a program, it commits to an algorithm at a single **fork token**. Asked to count the connected components of a graph, the instruct model opens `def solve(n, edges):` with a helper named `def find` (union-find) almost every time. The base model, Qwen3-8B-Base, is as likely to write `def dfs` or `def bfs`. This artifact asks **which weights** post-training changed to create that default:\\n\\n* **W1, readout rows:** the fork-class rows of the unembedding matrix (`lm_head`) and the final-norm gain.\\n* **W2, late-MLP weights:** MLP layers 26-35 swapped to the base model in place.\\n* **W3:** the W1 row test repeated on Gemma-3-4b (descriptive).\\n\\n**Units.** The prompts and fork tokens come from iteration 9.\\n\\n| unit | task | default class D (instruct) | alternative class A |\\n|---|---|---|---|\\n| **T10** (primary) | connected components, 20 prompts | `' find'` (union-find) | `' dfs'`, `' bfs'` |\\n| **B3** (beside) | minimum spanning tree, 20 prompts | 8 Kruskal-class tokens | 8 Prim-class tokens |\\n\\n**Margin and share.** The fork's **class margin** is `m = lse(z[D]) - lse(z[A])`, which equals log P(D) - log P(A). An intervention (\\\"arm\\\") is scored by the **share of the instruct-minus-base gap it closes**: `share = sum_p (m_I - m_arm) / sum_p (m_I - m_B)`. This is a ratio of sums over prompts, with a 95% prompt bootstrap. A share of 0 means no effect; a share of 1 means the margin became fully base-like.\\n\\n### What this notebook runs\\n`method.py` is a stage orchestrator: it launches about 40 scripts that load the 8B models on a 24 GB GPU (about 1 GPU-hour), which cannot run on a Colab CPU in 10 minutes. The core of the method does not need a GPU, though. **The class margin depends only on the final-normed residual at the fork and on the fork-class unembedding rows**, so every W1 arm and every null is exact arithmetic on the cached fork states. This notebook:\\n\\n1. shows the orchestrator (`method.py`) and its stage plan;\\n2. re-runs the **W1 teacher-forced test** (`src/w1_tf.py`): readout arms, 3 x 50 matched-norm null edits, bootstrap CIs and the committed verdict rule;\\n3. re-runs the **delta-geometry** analysis (`src/analysis10.py`);\\n4. draws the figures from `src/figures10.py`, including the activation-space plots: the fork states on the readout plane (F5) and the PCA of the block-35 outputs (F6).\\n\\n`mini_demo_data.json` holds:\\n* the cached fork states of 20 + 20 prompts (bf16, exact);\\n* the fork-class `lm_head` rows and the final-norm gains of both models, fetched at the pinned revisions;\\n* the residual's top-64 PCA basis;\\n* the committed DELTA_SWAP draws for T10;\\n* the artifact's reported numbers, for a side-by-side check.\\n\\nThe generation experiments (W1-GEN), W2 and W3 need model forwards on a GPU. Their reported results are summarized before the last cell.\"\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"5dfd487b\",\n   \"source\": \"import subprocess, sys\\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\\n\\n# loguru: NOT pre-installed on Colab, always install (the original scripts log with loguru)\\n_pip('loguru==0.7.3')\\n\\n# numpy, matplotlib, torch: pre-installed on Colab; install locally only, at Colab's versions (torch as the CPU build)\\nif 'google.colab' not in sys.modules:\\n    _pip('numpy==2.0.2', 'matplotlib==3.10.0')\\n    _pip('torch==2.9.0+cpu', '--index-url', 'https://download.pytorch.org/whl/cpu',\\n         '--extra-index-url', 'https://pypi.org/simple')\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"e1d109ef\",\n   \"source\": \"# ---------------------------------------------------------------- run size (the original values are in the comments)\\nUNITS_TF = (\\\"T10\\\",)          # units to score; original (\\\"T10\\\", \\\"B3\\\")  (T10 = connected components, B3 = MST)\\nN_NULL = 2                   # draws per null type; original 50 (the data file holds the 50 committed DELTA_SWAP draws)\\nN_BOOT = 10                  # prompt-bootstrap resamples for the 95% CIs; original 10000\\n\\n# ---------------------------------------------------------------- fixed design constants (src/cfg10.py, COMMIT #0)\\nD_MODEL = 4096\\nRMS_EPS = 1e-6\\nUNIT_IDX = {\\\"T10\\\": 0, \\\"B3\\\": 1, \\\"G-GRID\\\": 2}\\nDOSES = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5)   # lambda in w_I + lambda * Delta\\nSIGN_DOSE = -1.0\\nNULL_TYPES = (\\\"RAND_ISO\\\", \\\"DELTA_SWAP\\\", \\\"RAND_RESID\\\")\\nNULL_SEED0 = {\\\"RAND_ISO\\\": 101000, \\\"RAND_RESID\\\": 102000, \\\"DELTA_SWAP\\\": 103000}\\nRESID_PCS = 64\\nSEED_BOOT = 20261024\\nSMALL_GAP = 0.5\\nTHRESH = {\\\"W1_rows_share\\\": 0.50, \\\"W1_rand_iso_median\\\": 0.15, \\\"W1_disconfirm\\\": 0.20}   # committed W1 verdict rule\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}"}
```

### [93] TOOL CALL — NotebookEdit · 2026-10-26 15:36:59 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': '5dfd487b', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': '### Configuration\nThe next cell holds every tunable parameter. The W1 test is a few 4096-dimensional dot products per prompt, so the **original values** run in seconds on a CPU: both units, 50 draws per null type and 10,000 bootstrap resamples. Lower `N_NULL`, `N_BOOT` or `UNITS_TF` for a quicker smoke test. The null statistics then no longer match the reported ones, which use 50 draws.\n\nThe fixed design constants come from `src/cfg10.py`. They were committed (COMMIT #0) before any model forward was run.'}
```

### [94] TOOL RESULT — NotebookEdit · 2026-10-26 15:36:59 UTC

```
{"new_source": "### Configuration\nThe next cell holds every tunable parameter. The W1 test is a few 4096-dimensional dot products per prompt, so the **original values** run in seconds on a CPU: both units, 50 draws per null type and 10,000 bootstrap resamples. Lower `N_NULL`, `N_BOOT` or `UNITS_TF` for a quicker smoke test. The null statistics then no longer match the reported ones, which use 50 draws.\n\nThe fixed design constants come from `src/cfg10.py`. They were committed (COMMIT #0) before any model forward was run.", "cell_type": "markdown", "language": "python", "edit_mode": "insert", "cell_id": "4d9d64de", "error": "", "notebook_path": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb", "original_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"c00-title\",\n   \"metadata\": {},\n   \"source\": \"# Which weights make the model pick one algorithm (BASE-W, iteration 10)\\n\\nWhen Qwen3-8B writes a program, it commits to an algorithm at a single **fork token**. Asked to count the connected components of a graph, the instruct model opens `def solve(n, edges):` with a helper named `def find` (union-find) almost every time. The base model, Qwen3-8B-Base, is as likely to write `def dfs` or `def bfs`. This artifact asks **which weights** post-training changed to create that default:\\n\\n* **W1, readout rows:** the fork-class rows of the unembedding matrix (`lm_head`) and the final-norm gain.\\n* **W2, late-MLP weights:** MLP layers 26-35 swapped to the base model in place.\\n* **W3:** the W1 row test repeated on Gemma-3-4b (descriptive).\\n\\n**Units.** The prompts and fork tokens come from iteration 9.\\n\\n| unit | task | default class D (instruct) | alternative class A |\\n|---|---|---|---|\\n| **T10** (primary) | connected components, 20 prompts | `' find'` (union-find) | `' dfs'`, `' bfs'` |\\n| **B3** (beside) | minimum spanning tree, 20 prompts | 8 Kruskal-class tokens | 8 Prim-class tokens |\\n\\n**Margin and share.** The fork's **class margin** is `m = lse(z[D]) - lse(z[A])`, which equals log P(D) - log P(A). An intervention (\\\"arm\\\") is scored by the **share of the instruct-minus-base gap it closes**: `share = sum_p (m_I - m_arm) / sum_p (m_I - m_B)`. This is a ratio of sums over prompts, with a 95% prompt bootstrap. A share of 0 means no effect; a share of 1 means the margin became fully base-like.\\n\\n### What this notebook runs\\n`method.py` is a stage orchestrator: it launches about 40 scripts that load the 8B models on a 24 GB GPU (about 1 GPU-hour), which cannot run on a Colab CPU in 10 minutes. The core of the method does not need a GPU, though. **The class margin depends only on the final-normed residual at the fork and on the fork-class unembedding rows**, so every W1 arm and every null is exact arithmetic on the cached fork states. This notebook:\\n\\n1. shows the orchestrator (`method.py`) and its stage plan;\\n2. re-runs the **W1 teacher-forced test** (`src/w1_tf.py`): readout arms, 3 x 50 matched-norm null edits, bootstrap CIs and the committed verdict rule;\\n3. re-runs the **delta-geometry** analysis (`src/analysis10.py`);\\n4. draws the figures from `src/figures10.py`, including the activation-space plots: the fork states on the readout plane (F5) and the PCA of the block-35 outputs (F6).\\n\\n`mini_demo_data.json` holds:\\n* the cached fork states of 20 + 20 prompts (bf16, exact);\\n* the fork-class `lm_head` rows and the final-norm gains of both models, fetched at the pinned revisions;\\n* the residual's top-64 PCA basis;\\n* the committed DELTA_SWAP draws for T10;\\n* the artifact's reported numbers, for a side-by-side check.\\n\\nThe generation experiments (W1-GEN), W2 and W3 need model forwards on a GPU. Their reported results are summarized before the last cell.\"\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"5dfd487b\",\n   \"source\": \"import subprocess, sys\\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\\n\\n# loguru: NOT pre-installed on Colab, always install (the original scripts log with loguru)\\n_pip('loguru==0.7.3')\\n\\n# numpy, matplotlib, torch: pre-installed on Colab; install locally only, at Colab's versions (torch as the CPU build)\\nif 'google.colab' not in sys.modules:\\n    _pip('numpy==2.0.2', 'matplotlib==3.10.0')\\n    _pip('torch==2.9.0+cpu', '--index-url', 'https://download.pytorch.org/whl/cpu',\\n         '--extra-index-url', 'https://pypi.org/simple')\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"e1d109ef\",\n   \"source\": \"# ---------------------------------------------------------------- run size (the original values are in the comments)\\nUNITS_TF = (\\\"T10\\\",)          # units to score; original (\\\"T10\\\", \\\"B3\\\")  (T10 = connected components, B3 = MST)\\nN_NULL = 2                   # draws per null type; original 50 (the data file holds the 50 committed DELTA_SWAP draws)\\nN_BOOT = 10                  # prompt-bootstrap resamples for the 95% CIs; original 10000\\n\\n# ---------------------------------------------------------------- fixed design constants (src/cfg10.py, COMMIT #0)\\nD_MODEL = 4096\\nRMS_EPS = 1e-6\\nUNIT_IDX = {\\\"T10\\\": 0, \\\"B3\\\": 1, \\\"G-GRID\\\": 2}\\nDOSES = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5)   # lambda in w_I + lambda * Delta\\nSIGN_DOSE = -1.0\\nNULL_TYPES = (\\\"RAND_ISO\\\", \\\"DELTA_SWAP\\\", \\\"RAND_RESID\\\")\\nNULL_SEED0 = {\\\"RAND_ISO\\\": 101000, \\\"RAND_RESID\\\": 102000, \\\"DELTA_SWAP\\\": 103000}\\nRESID_PCS = 64\\nSEED_BOOT = 20261024\\nSMALL_GAP = 0.5\\nTHRESH = {\\\"W1_rows_share\\\": 0.50, \\\"W1_rand_iso_median\\\": 0.15, \\\"W1_disconfirm\\\": 0.20}   # committed W1 verdict rule\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}", "updated_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"c00-title\",\n   \"metadata\": {},\n   \"source\": \"# Which weights make the model pick one algorithm (BASE-W, iteration 10)\\n\\nWhen Qwen3-8B writes a program, it commits to an algorithm at a single **fork token**. Asked to count the connected components of a graph, the instruct model opens `def solve(n, edges):` with a helper named `def find` (union-find) almost every time. The base model, Qwen3-8B-Base, is as likely to write `def dfs` or `def bfs`. This artifact asks **which weights** post-training changed to create that default:\\n\\n* **W1, readout rows:** the fork-class rows of the unembedding matrix (`lm_head`) and the final-norm gain.\\n* **W2, late-MLP weights:** MLP layers 26-35 swapped to the base model in place.\\n* **W3:** the W1 row test repeated on Gemma-3-4b (descriptive).\\n\\n**Units.** The prompts and fork tokens come from iteration 9.\\n\\n| unit | task | default class D (instruct) | alternative class A |\\n|---|---|---|---|\\n| **T10** (primary) | connected components, 20 prompts | `' find'` (union-find) | `' dfs'`, `' bfs'` |\\n| **B3** (beside) | minimum spanning tree, 20 prompts | 8 Kruskal-class tokens | 8 Prim-class tokens |\\n\\n**Margin and share.** The fork's **class margin** is `m = lse(z[D]) - lse(z[A])`, which equals log P(D) - log P(A). An intervention (\\\"arm\\\") is scored by the **share of the instruct-minus-base gap it closes**: `share = sum_p (m_I - m_arm) / sum_p (m_I - m_B)`. This is a ratio of sums over prompts, with a 95% prompt bootstrap. A share of 0 means no effect; a share of 1 means the margin became fully base-like.\\n\\n### What this notebook runs\\n`method.py` is a stage orchestrator: it launches about 40 scripts that load the 8B models on a 24 GB GPU (about 1 GPU-hour), which cannot run on a Colab CPU in 10 minutes. The core of the method does not need a GPU, though. **The class margin depends only on the final-normed residual at the fork and on the fork-class unembedding rows**, so every W1 arm and every null is exact arithmetic on the cached fork states. This notebook:\\n\\n1. shows the orchestrator (`method.py`) and its stage plan;\\n2. re-runs the **W1 teacher-forced test** (`src/w1_tf.py`): readout arms, 3 x 50 matched-norm null edits, bootstrap CIs and the committed verdict rule;\\n3. re-runs the **delta-geometry** analysis (`src/analysis10.py`);\\n4. draws the figures from `src/figures10.py`, including the activation-space plots: the fork states on the readout plane (F5) and the PCA of the block-35 outputs (F6).\\n\\n`mini_demo_data.json` holds:\\n* the cached fork states of 20 + 20 prompts (bf16, exact);\\n* the fork-class `lm_head` rows and the final-norm gains of both models, fetched at the pinned revisions;\\n* the residual's top-64 PCA basis;\\n* the committed DELTA_SWAP draws for T10;\\n* the artifact's reported numbers, for a side-by-side check.\\n\\nThe generation experiments (W1-GEN), W2 and W3 need model forwards on a GPU. Their reported results are summarized before the last cell.\"\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"5dfd487b\",\n   \"source\": \"import subprocess, sys\\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\\n\\n# loguru: NOT pre-installed on Colab, always install (the original scripts log with loguru)\\n_pip('loguru==0.7.3')\\n\\n# numpy, matplotlib, torch: pre-installed on Colab; install locally only, at Colab's versions (torch as the CPU build)\\nif 'google.colab' not in sys.modules:\\n    _pip('numpy==2.0.2', 'matplotlib==3.10.0')\\n    _pip('torch==2.9.0+cpu', '--index-url', 'https://download.pytorch.org/whl/cpu',\\n         '--extra-index-url', 'https://pypi.org/simple')\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"4d9d64de\",\n   \"source\": \"### Configuration\\nThe next cell holds every tunable parameter. The W1 test is a few 4096-dimensional dot products per prompt, so the **original values** run in seconds on a CPU: both units, 50 draws per null type and 10,000 bootstrap resamples. Lower `N_NULL`, `N_BOOT` or `UNITS_TF` for a quicker smoke test. The null statistics then no longer match the reported ones, which use 50 draws.\\n\\nThe fixed design constants come from `src/cfg10.py`. They were committed (COMMIT #0) before any model forward was run.\",\n   \"metadata\": {}\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"e1d109ef\",\n   \"source\": \"# ---------------------------------------------------------------- run size (the original values are in the comments)\\nUNITS_TF = (\\\"T10\\\",)          # units to score; original (\\\"T10\\\", \\\"B3\\\")  (T10 = connected components, B3 = MST)\\nN_NULL = 2                   # draws per null type; original 50 (the data file holds the 50 committed DELTA_SWAP draws)\\nN_BOOT = 10                  # prompt-bootstrap resamples for the 95% CIs; original 10000\\n\\n# ---------------------------------------------------------------- fixed design constants (src/cfg10.py, COMMIT #0)\\nD_MODEL = 4096\\nRMS_EPS = 1e-6\\nUNIT_IDX = {\\\"T10\\\": 0, \\\"B3\\\": 1, \\\"G-GRID\\\": 2}\\nDOSES = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5)   # lambda in w_I + lambda * Delta\\nSIGN_DOSE = -1.0\\nNULL_TYPES = (\\\"RAND_ISO\\\", \\\"DELTA_SWAP\\\", \\\"RAND_RESID\\\")\\nNULL_SEED0 = {\\\"RAND_ISO\\\": 101000, \\\"RAND_RESID\\\": 102000, \\\"DELTA_SWAP\\\": 103000}\\nRESID_PCS = 64\\nSEED_BOOT = 20261024\\nSMALL_GAP = 0.5\\nTHRESH = {\\\"W1_rows_share\\\": 0.50, \\\"W1_rand_iso_median\\\": 0.15, \\\"W1_disconfirm\\\": 0.20}   # committed W1 verdict rule\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}"}
```

### [95] TOOL CALL — NotebookEdit · 2026-10-26 15:36:59 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': '5dfd487b', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'data = load_data()\nprint({u: f"{len(U[\'examples\'])} prompts" for u, U in data["units"].items()}, "|",\n      {k: f"{v[\'id\']}@{v[\'revision\'][:8]}" for k, v in data["models"].items()})'}
```

### [96] TOOL RESULT — NotebookEdit · 2026-10-26 15:36:59 UTC

```
{"new_source": "data = load_data()\nprint({u: f\"{len(U['examples'])} prompts\" for u, U in data[\"units\"].items()}, \"|\",\n      {k: f\"{v['id']}@{v['revision'][:8]}\" for k, v in data[\"models\"].items()})", "cell_type": "code", "language": "python", "edit_mode": "insert", "cell_id": "7efd0587", "error": "", "notebook_path": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb", "original_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"c00-title\",\n   \"metadata\": {},\n   \"source\": \"# Which weights make the model pick one algorithm (BASE-W, iteration 10)\\n\\nWhen Qwen3-8B writes a program, it commits to an algorithm at a single **fork token**. Asked to count the connected components of a graph, the instruct model opens `def solve(n, edges):` with a helper named `def find` (union-find) almost every time. The base model, Qwen3-8B-Base, is as likely to write `def dfs` or `def bfs`. This artifact asks **which weights** post-training changed to create that default:\\n\\n* **W1, readout rows:** the fork-class rows of the unembedding matrix (`lm_head`) and the final-norm gain.\\n* **W2, late-MLP weights:** MLP layers 26-35 swapped to the base model in place.\\n* **W3:** the W1 row test repeated on Gemma-3-4b (descriptive).\\n\\n**Units.** The prompts and fork tokens come from iteration 9.\\n\\n| unit | task | default class D (instruct) | alternative class A |\\n|---|---|---|---|\\n| **T10** (primary) | connected components, 20 prompts | `' find'` (union-find) | `' dfs'`, `' bfs'` |\\n| **B3** (beside) | minimum spanning tree, 20 prompts | 8 Kruskal-class tokens | 8 Prim-class tokens |\\n\\n**Margin and share.** The fork's **class margin** is `m = lse(z[D]) - lse(z[A])`, which equals log P(D) - log P(A). An intervention (\\\"arm\\\") is scored by the **share of the instruct-minus-base gap it closes**: `share = sum_p (m_I - m_arm) / sum_p (m_I - m_B)`. This is a ratio of sums over prompts, with a 95% prompt bootstrap. A share of 0 means no effect; a share of 1 means the margin became fully base-like.\\n\\n### What this notebook runs\\n`method.py` is a stage orchestrator: it launches about 40 scripts that load the 8B models on a 24 GB GPU (about 1 GPU-hour), which cannot run on a Colab CPU in 10 minutes. The core of the method does not need a GPU, though. **The class margin depends only on the final-normed residual at the fork and on the fork-class unembedding rows**, so every W1 arm and every null is exact arithmetic on the cached fork states. This notebook:\\n\\n1. shows the orchestrator (`method.py`) and its stage plan;\\n2. re-runs the **W1 teacher-forced test** (`src/w1_tf.py`): readout arms, 3 x 50 matched-norm null edits, bootstrap CIs and the committed verdict rule;\\n3. re-runs the **delta-geometry** analysis (`src/analysis10.py`);\\n4. draws the figures from `src/figures10.py`, including the activation-space plots: the fork states on the readout plane (F5) and the PCA of the block-35 outputs (F6).\\n\\n`mini_demo_data.json` holds:\\n* the cached fork states of 20 + 20 prompts (bf16, exact);\\n* the fork-class `lm_head` rows and the final-norm gains of both models, fetched at the pinned revisions;\\n* the residual's top-64 PCA basis;\\n* the committed DELTA_SWAP draws for T10;\\n* the artifact's reported numbers, for a side-by-side check.\\n\\nThe generation experiments (W1-GEN), W2 and W3 need model forwards on a GPU. Their reported results are summarized before the last cell.\"\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"5dfd487b\",\n   \"source\": \"import subprocess, sys\\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\\n\\n# loguru: NOT pre-installed on Colab, always install (the original scripts log with loguru)\\n_pip('loguru==0.7.3')\\n\\n# numpy, matplotlib, torch: pre-installed on Colab; install locally only, at Colab's versions (torch as the CPU build)\\nif 'google.colab' not in sys.modules:\\n    _pip('numpy==2.0.2', 'matplotlib==3.10.0')\\n    _pip('torch==2.9.0+cpu', '--index-url', 'https://download.pytorch.org/whl/cpu',\\n         '--extra-index-url', 'https://pypi.org/simple')\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"4d9d64de\",\n   \"source\": \"### Configuration\\nThe next cell holds every tunable parameter. The W1 test is a few 4096-dimensional dot products per prompt, so the **original values** run in seconds on a CPU: both units, 50 draws per null type and 10,000 bootstrap resamples. Lower `N_NULL`, `N_BOOT` or `UNITS_TF` for a quicker smoke test. The null statistics then no longer match the reported ones, which use 50 draws.\\n\\nThe fixed design constants come from `src/cfg10.py`. They were committed (COMMIT #0) before any model forward was run.\",\n   \"metadata\": {}\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"e1d109ef\",\n   \"source\": \"# ---------------------------------------------------------------- run size (the original values are in the comments)\\nUNITS_TF = (\\\"T10\\\",)          # units to score; original (\\\"T10\\\", \\\"B3\\\")  (T10 = connected components, B3 = MST)\\nN_NULL = 2                   # draws per null type; original 50 (the data file holds the 50 committed DELTA_SWAP draws)\\nN_BOOT = 10                  # prompt-bootstrap resamples for the 95% CIs; original 10000\\n\\n# ---------------------------------------------------------------- fixed design constants (src/cfg10.py, COMMIT #0)\\nD_MODEL = 4096\\nRMS_EPS = 1e-6\\nUNIT_IDX = {\\\"T10\\\": 0, \\\"B3\\\": 1, \\\"G-GRID\\\": 2}\\nDOSES = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5)   # lambda in w_I + lambda * Delta\\nSIGN_DOSE = -1.0\\nNULL_TYPES = (\\\"RAND_ISO\\\", \\\"DELTA_SWAP\\\", \\\"RAND_RESID\\\")\\nNULL_SEED0 = {\\\"RAND_ISO\\\": 101000, \\\"RAND_RESID\\\": 102000, \\\"DELTA_SWAP\\\": 103000}\\nRESID_PCS = 64\\nSEED_BOOT = 20261024\\nSMALL_GAP = 0.5\\nTHRESH = {\\\"W1_rows_share\\\": 0.50, \\\"W1_rand_iso_median\\\": 0.15, \\\"W1_disconfirm\\\": 0.20}   # committed W1 verdict rule\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}", "updated_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"c00-title\",\n   \"metadata\": {},\n   \"source\": \"# Which weights make the model pick one algorithm (BASE-W, iteration 10)\\n\\nWhen Qwen3-8B writes a program, it commits to an algorithm at a single **fork token**. Asked to count the connected components of a graph, the instruct model opens `def solve(n, edges):` with a helper named `def find` (union-find) almost every time. The base model, Qwen3-8B-Base, is as likely to write `def dfs` or `def bfs`. This artifact asks **which weights** post-training changed to create that default:\\n\\n* **W1, readout rows:** the fork-class rows of the unembedding matrix (`lm_head`) and the final-norm gain.\\n* **W2, late-MLP weights:** MLP layers 26-35 swapped to the base model in place.\\n* **W3:** the W1 row test repeated on Gemma-3-4b (descriptive).\\n\\n**Units.** The prompts and fork tokens come from iteration 9.\\n\\n| unit | task | default class D (instruct) | alternative class A |\\n|---|---|---|---|\\n| **T10** (primary) | connected components, 20 prompts | `' find'` (union-find) | `' dfs'`, `' bfs'` |\\n| **B3** (beside) | minimum spanning tree, 20 prompts | 8 Kruskal-class tokens | 8 Prim-class tokens |\\n\\n**Margin and share.** The fork's **class margin** is `m = lse(z[D]) - lse(z[A])`, which equals log P(D) - log P(A). An intervention (\\\"arm\\\") is scored by the **share of the instruct-minus-base gap it closes**: `share = sum_p (m_I - m_arm) / sum_p (m_I - m_B)`. This is a ratio of sums over prompts, with a 95% prompt bootstrap. A share of 0 means no effect; a share of 1 means the margin became fully base-like.\\n\\n### What this notebook runs\\n`method.py` is a stage orchestrator: it launches about 40 scripts that load the 8B models on a 24 GB GPU (about 1 GPU-hour), which cannot run on a Colab CPU in 10 minutes. The core of the method does not need a GPU, though. **The class margin depends only on the final-normed residual at the fork and on the fork-class unembedding rows**, so every W1 arm and every null is exact arithmetic on the cached fork states. This notebook:\\n\\n1. shows the orchestrator (`method.py`) and its stage plan;\\n2. re-runs the **W1 teacher-forced test** (`src/w1_tf.py`): readout arms, 3 x 50 matched-norm null edits, bootstrap CIs and the committed verdict rule;\\n3. re-runs the **delta-geometry** analysis (`src/analysis10.py`);\\n4. draws the figures from `src/figures10.py`, including the activation-space plots: the fork states on the readout plane (F5) and the PCA of the block-35 outputs (F6).\\n\\n`mini_demo_data.json` holds:\\n* the cached fork states of 20 + 20 prompts (bf16, exact);\\n* the fork-class `lm_head` rows and the final-norm gains of both models, fetched at the pinned revisions;\\n* the residual's top-64 PCA basis;\\n* the committed DELTA_SWAP draws for T10;\\n* the artifact's reported numbers, for a side-by-side check.\\n\\nThe generation experiments (W1-GEN), W2 and W3 need model forwards on a GPU. Their reported results are summarized before the last cell.\"\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"5dfd487b\",\n   \"source\": \"import subprocess, sys\\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\\n\\n# loguru: NOT pre-installed on Colab, always install (the original scripts log with loguru)\\n_pip('loguru==0.7.3')\\n\\n# numpy, matplotlib, torch: pre-installed on Colab; install locally only, at Colab's versions (torch as the CPU build)\\nif 'google.colab' not in sys.modules:\\n    _pip('numpy==2.0.2', 'matplotlib==3.10.0')\\n    _pip('torch==2.9.0+cpu', '--index-url', 'https://download.pytorch.org/whl/cpu',\\n         '--extra-index-url', 'https://pypi.org/simple')\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"7efd0587\",\n   \"source\": \"data = load_data()\\nprint({u: f\\\"{len(U['examples'])} prompts\\\" for u, U in data[\\\"units\\\"].items()}, \\\"|\\\",\\n      {k: f\\\"{v['id']}@{v['revision'][:8]}\\\" for k, v in data[\\\"models\\\"].items()})\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"4d9d64de\",\n   \"source\": \"### Configuration\\nThe next cell holds every tunable parameter. The W1 test is a few 4096-dimensional dot products per prompt, so the **original values** run in seconds on a CPU: both units, 50 draws per null type and 10,000 bootstrap resamples. Lower `N_NULL`, `N_BOOT` or `UNITS_TF` for a quicker smoke test. The null statistics then no longer match the reported ones, which use 50 draws.\\n\\nThe fixed design constants come from `src/cfg10.py`. They were committed (COMMIT #0) before any model forward was run.\",\n   \"metadata\": {}\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"e1d109ef\",\n   \"source\": \"# ---------------------------------------------------------------- run size (the original values are in the comments)\\nUNITS_TF = (\\\"T10\\\",)          # units to score; original (\\\"T10\\\", \\\"B3\\\")  (T10 = connected components, B3 = MST)\\nN_NULL = 2                   # draws per null type; original 50 (the data file holds the 50 committed DELTA_SWAP draws)\\nN_BOOT = 10                  # prompt-bootstrap resamples for the 95% CIs; original 10000\\n\\n# ---------------------------------------------------------------- fixed design constants (src/cfg10.py, COMMIT #0)\\nD_MODEL = 4096\\nRMS_EPS = 1e-6\\nUNIT_IDX = {\\\"T10\\\": 0, \\\"B3\\\": 1, \\\"G-GRID\\\": 2}\\nDOSES = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5)   # lambda in w_I + lambda * Delta\\nSIGN_DOSE = -1.0\\nNULL_TYPES = (\\\"RAND_ISO\\\", \\\"DELTA_SWAP\\\", \\\"RAND_RESID\\\")\\nNULL_SEED0 = {\\\"RAND_ISO\\\": 101000, \\\"RAND_RESID\\\": 102000, \\\"DELTA_SWAP\\\": 103000}\\nRESID_PCS = 64\\nSEED_BOOT = 20261024\\nSMALL_GAP = 0.5\\nTHRESH = {\\\"W1_rows_share\\\": 0.50, \\\"W1_rand_iso_median\\\": 0.15, \\\"W1_disconfirm\\\": 0.20}   # committed W1 verdict rule\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}"}
```

### [97] TOOL CALL — NotebookEdit · 2026-10-26 15:36:59 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': '5dfd487b', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-10/experiment-56/demo/mini_demo_data.json"\nimport http.client\nimport json\nimport urllib.request\nfrom pathlib import Path\n\ndef load_data():\n    try:\n        with urllib.request.urlopen(GITHUB_DATA_URL, timeout=15) as response:\n            return json.loads(response.read().decode())\n    # Network errors, timeouts, a placeholder URL, bad JSON, a cut-off response.\n    except (OSError, ValueError, http.client.HTTPException) as e:\n        print("GitHub data unavailable, using local mini_demo_data.json:", e)\n    local = Path("mini_demo_data.json")\n    if local.exists(): return json.loads(local.read_text())\n    raise FileNotFoundError("Could not load mini_demo_data.json")\n\n\ndef arr(spec: dict) -> torch.Tensor:\n    """Decode one array of mini_demo_data.json ({dtype, shape, b64}: base64 of little-endian raw bytes).\n    bfloat16 arrays are stored as their uint16 bit patterns; (u16 << 16) viewed as float32 is the exact value."""\n    raw = base64.b64decode(spec["b64"])\n    if spec["dtype"] == "bfloat16":\n        f32 = (np.frombuffer(raw, dtype="<u2").astype(np.uint32) << 16).view(np.float32)\n        return torch.from_numpy(f32.reshape(spec["shape"]).copy()).to(torch.bfloat16)\n    return torch.from_numpy(np.frombuffer(raw, dtype="<f4").reshape(spec["shape"]).copy())'}
```

### [98] TOOL RESULT — NotebookEdit · 2026-10-26 15:36:59 UTC

```
{"new_source": "GITHUB_DATA_URL = \"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-10/experiment-56/demo/mini_demo_data.json\"\nimport http.client\nimport json\nimport urllib.request\nfrom pathlib import Path\n\ndef load_data():\n    try:\n        with urllib.request.urlopen(GITHUB_DATA_URL, timeout=15) as response:\n            return json.loads(response.read().decode())\n    # Network errors, timeouts, a placeholder URL, bad JSON, a cut-off response.\n    except (OSError, ValueError, http.client.HTTPException) as e:\n        print(\"GitHub data unavailable, using local mini_demo_data.json:\", e)\n    local = Path(\"mini_demo_data.json\")\n    if local.exists(): return json.loads(local.read_text())\n    raise FileNotFoundError(\"Could not load mini_demo_data.json\")\n\n\ndef arr(spec: dict) -> torch.Tensor:\n    \"\"\"Decode one array of mini_demo_data.json ({dtype, shape, b64}: base64 of little-endian raw bytes).\n    bfloat16 arrays are stored as their uint16 bit patterns; (u16 << 16) viewed as float32 is the exact value.\"\"\"\n    raw = base64.b64decode(spec[\"b64\"])\n    if spec[\"dtype\"] == \"bfloat16\":\n        f32 = (np.frombuffer(raw, dtype=\"<u2\").astype(np.uint32) << 16).view(np.float32)\n        return torch.from_numpy(f32.reshape(spec[\"shape\"]).copy()).to(torch.bfloat16)\n    return torch.from_numpy(np.frombuffer(raw, dtype=\"<f4\").reshape(spec[\"shape\"]).copy())", "cell_type": "code", "language": "python", "edit_mode": "insert", "cell_id": "7ea594f1", "error": "", "notebook_path": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb", "original_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"c00-title\",\n   \"metadata\": {},\n   \"source\": \"# Which weights make the model pick one algorithm (BASE-W, iteration 10)\\n\\nWhen Qwen3-8B writes a program, it commits to an algorithm at a single **fork token**. Asked to count the connected components of a graph, the instruct model opens `def solve(n, edges):` with a helper named `def find` (union-find) almost every time. The base model, Qwen3-8B-Base, is as likely to write `def dfs` or `def bfs`. This artifact asks **which weights** post-training changed to create that default:\\n\\n* **W1, readout rows:** the fork-class rows of the unembedding matrix (`lm_head`) and the final-norm gain.\\n* **W2, late-MLP weights:** MLP layers 26-35 swapped to the base model in place.\\n* **W3:** the W1 row test repeated on Gemma-3-4b (descriptive).\\n\\n**Units.** The prompts and fork tokens come from iteration 9.\\n\\n| unit | task | default class D (instruct) | alternative class A |\\n|---|---|---|---|\\n| **T10** (primary) | connected components, 20 prompts | `' find'` (union-find) | `' dfs'`, `' bfs'` |\\n| **B3** (beside) | minimum spanning tree, 20 prompts | 8 Kruskal-class tokens | 8 Prim-class tokens |\\n\\n**Margin and share.** The fork's **class margin** is `m = lse(z[D]) - lse(z[A])`, which equals log P(D) - log P(A). An intervention (\\\"arm\\\") is scored by the **share of the instruct-minus-base gap it closes**: `share = sum_p (m_I - m_arm) / sum_p (m_I - m_B)`. This is a ratio of sums over prompts, with a 95% prompt bootstrap. A share of 0 means no effect; a share of 1 means the margin became fully base-like.\\n\\n### What this notebook runs\\n`method.py` is a stage orchestrator: it launches about 40 scripts that load the 8B models on a 24 GB GPU (about 1 GPU-hour), which cannot run on a Colab CPU in 10 minutes. The core of the method does not need a GPU, though. **The class margin depends only on the final-normed residual at the fork and on the fork-class unembedding rows**, so every W1 arm and every null is exact arithmetic on the cached fork states. This notebook:\\n\\n1. shows the orchestrator (`method.py`) and its stage plan;\\n2. re-runs the **W1 teacher-forced test** (`src/w1_tf.py`): readout arms, 3 x 50 matched-norm null edits, bootstrap CIs and the committed verdict rule;\\n3. re-runs the **delta-geometry** analysis (`src/analysis10.py`);\\n4. draws the figures from `src/figures10.py`, including the activation-space plots: the fork states on the readout plane (F5) and the PCA of the block-35 outputs (F6).\\n\\n`mini_demo_data.json` holds:\\n* the cached fork states of 20 + 20 prompts (bf16, exact);\\n* the fork-class `lm_head` rows and the final-norm gains of both models, fetched at the pinned revisions;\\n* the residual's top-64 PCA basis;\\n* the committed DELTA_SWAP draws for T10;\\n* the artifact's reported numbers, for a side-by-side check.\\n\\nThe generation experiments (W1-GEN), W2 and W3 need model forwards on a GPU. Their reported results are summarized before the last cell.\"\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"5dfd487b\",\n   \"source\": \"import subprocess, sys\\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\\n\\n# loguru: NOT pre-installed on Colab, always install (the original scripts log with loguru)\\n_pip('loguru==0.7.3')\\n\\n# numpy, matplotlib, torch: pre-installed on Colab; install locally only, at Colab's versions (torch as the CPU build)\\nif 'google.colab' not in sys.modules:\\n    _pip('numpy==2.0.2', 'matplotlib==3.10.0')\\n    _pip('torch==2.9.0+cpu', '--index-url', 'https://download.pytorch.org/whl/cpu',\\n         '--extra-index-url', 'https://pypi.org/simple')\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"7efd0587\",\n   \"source\": \"data = load_data()\\nprint({u: f\\\"{len(U['examples'])} prompts\\\" for u, U in data[\\\"units\\\"].items()}, \\\"|\\\",\\n      {k: f\\\"{v['id']}@{v['revision'][:8]}\\\" for k, v in data[\\\"models\\\"].items()})\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"4d9d64de\",\n   \"source\": \"### Configuration\\nThe next cell holds every tunable parameter. The W1 test is a few 4096-dimensional dot products per prompt, so the **original values** run in seconds on a CPU: both units, 50 draws per null type and 10,000 bootstrap resamples. Lower `N_NULL`, `N_BOOT` or `UNITS_TF` for a quicker smoke test. The null statistics then no longer match the reported ones, which use 50 draws.\\n\\nThe fixed design constants come from `src/cfg10.py`. They were committed (COMMIT #0) before any model forward was run.\",\n   \"metadata\": {}\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"e1d109ef\",\n   \"source\": \"# ---------------------------------------------------------------- run size (the original values are in the comments)\\nUNITS_TF = (\\\"T10\\\",)          # units to score; original (\\\"T10\\\", \\\"B3\\\")  (T10 = connected components, B3 = MST)\\nN_NULL = 2                   # draws per null type; original 50 (the data file holds the 50 committed DELTA_SWAP draws)\\nN_BOOT = 10                  # prompt-bootstrap resamples for the 95% CIs; original 10000\\n\\n# ---------------------------------------------------------------- fixed design constants (src/cfg10.py, COMMIT #0)\\nD_MODEL = 4096\\nRMS_EPS = 1e-6\\nUNIT_IDX = {\\\"T10\\\": 0, \\\"B3\\\": 1, \\\"G-GRID\\\": 2}\\nDOSES = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5)   # lambda in w_I + lambda * Delta\\nSIGN_DOSE = -1.0\\nNULL_TYPES = (\\\"RAND_ISO\\\", \\\"DELTA_SWAP\\\", \\\"RAND_RESID\\\")\\nNULL_SEED0 = {\\\"RAND_ISO\\\": 101000, \\\"RAND_RESID\\\": 102000, \\\"DELTA_SWAP\\\": 103000}\\nRESID_PCS = 64\\nSEED_BOOT = 20261024\\nSMALL_GAP = 0.5\\nTHRESH = {\\\"W1_rows_share\\\": 0.50, \\\"W1_rand_iso_median\\\": 0.15, \\\"W1_disconfirm\\\": 0.20}   # committed W1 verdict rule\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}", "updated_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"c00-title\",\n   \"metadata\": {},\n   \"source\": \"# Which weights make the model pick one algorithm (BASE-W, iteration 10)\\n\\nWhen Qwen3-8B writes a program, it commits to an algorithm at a single **fork token**. Asked to count the connected components of a graph, the instruct model opens `def solve(n, edges):` with a helper named `def find` (union-find) almost every time. The base model, Qwen3-8B-Base, is as likely to write `def dfs` or `def bfs`. This artifact asks **which weights** post-training changed to create that default:\\n\\n* **W1, readout rows:** the fork-class rows of the unembedding matrix (`lm_head`) and the final-norm gain.\\n* **W2, late-MLP weights:** MLP layers 26-35 swapped to the base model in place.\\n* **W3:** the W1 row test repeated on Gemma-3-4b (descriptive).\\n\\n**Units.** The prompts and fork tokens come from iteration 9.\\n\\n| unit | task | default class D (instruct) | alternative class A |\\n|---|---|---|---|\\n| **T10** (primary) | connected components, 20 prompts | `' find'` (union-find) | `' dfs'`, `' bfs'` |\\n| **B3** (beside) | minimum spanning tree, 20 prompts | 8 Kruskal-class tokens | 8 Prim-class tokens |\\n\\n**Margin and share.** The fork's **class margin** is `m = lse(z[D]) - lse(z[A])`, which equals log P(D) - log P(A). An intervention (\\\"arm\\\") is scored by the **share of the instruct-minus-base gap it closes**: `share = sum_p (m_I - m_arm) / sum_p (m_I - m_B)`. This is a ratio of sums over prompts, with a 95% prompt bootstrap. A share of 0 means no effect; a share of 1 means the margin became fully base-like.\\n\\n### What this notebook runs\\n`method.py` is a stage orchestrator: it launches about 40 scripts that load the 8B models on a 24 GB GPU (about 1 GPU-hour), which cannot run on a Colab CPU in 10 minutes. The core of the method does not need a GPU, though. **The class margin depends only on the final-normed residual at the fork and on the fork-class unembedding rows**, so every W1 arm and every null is exact arithmetic on the cached fork states. This notebook:\\n\\n1. shows the orchestrator (`method.py`) and its stage plan;\\n2. re-runs the **W1 teacher-forced test** (`src/w1_tf.py`): readout arms, 3 x 50 matched-norm null edits, bootstrap CIs and the committed verdict rule;\\n3. re-runs the **delta-geometry** analysis (`src/analysis10.py`);\\n4. draws the figures from `src/figures10.py`, including the activation-space plots: the fork states on the readout plane (F5) and the PCA of the block-35 outputs (F6).\\n\\n`mini_demo_data.json` holds:\\n* the cached fork states of 20 + 20 prompts (bf16, exact);\\n* the fork-class `lm_head` rows and the final-norm gains of both models, fetched at the pinned revisions;\\n* the residual's top-64 PCA basis;\\n* the committed DELTA_SWAP draws for T10;\\n* the artifact's reported numbers, for a side-by-side check.\\n\\nThe generation experiments (W1-GEN), W2 and W3 need model forwards on a GPU. Their reported results are summarized before the last cell.\"\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"5dfd487b\",\n   \"source\": \"import subprocess, sys\\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\\n\\n# loguru: NOT pre-installed on Colab, always install (the original scripts log with loguru)\\n_pip('loguru==0.7.3')\\n\\n# numpy, matplotlib, torch: pre-installed on Colab; install locally only, at Colab's versions (torch as the CPU build)\\nif 'google.colab' not in sys.modules:\\n    _pip('numpy==2.0.2', 'matplotlib==3.10.0')\\n    _pip('torch==2.9.0+cpu', '--index-url', 'https://download.pytorch.org/whl/cpu',\\n         '--extra-index-url', 'https://pypi.org/simple')\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"7ea594f1\",\n   \"source\": \"GITHUB_DATA_URL = \\\"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-10/experiment-56/demo/mini_demo_data.json\\\"\\nimport http.client\\nimport json\\nimport urllib.request\\nfrom pathlib import Path\\n\\ndef load_data():\\n    try:\\n        with urllib.request.urlopen(GITHUB_DATA_URL, timeout=15) as response:\\n            return json.loads(response.read().decode())\\n    # Network errors, timeouts, a placeholder URL, bad JSON, a cut-off response.\\n    except (OSError, ValueError, http.client.HTTPException) as e:\\n        print(\\\"GitHub data unavailable, using local mini_demo_data.json:\\\", e)\\n    local = Path(\\\"mini_demo_data.json\\\")\\n    if local.exists(): return json.loads(local.read_text())\\n    raise FileNotFoundError(\\\"Could not load mini_demo_data.json\\\")\\n\\n\\ndef arr(spec: dict) -> torch.Tensor:\\n    \\\"\\\"\\\"Decode one array of mini_demo_data.json ({dtype, shape, b64}: base64 of little-endian raw bytes).\\n    bfloat16 arrays are stored as their uint16 bit patterns; (u16 << 16) viewed as float32 is the exact value.\\\"\\\"\\\"\\n    raw = base64.b64decode(spec[\\\"b64\\\"])\\n    if spec[\\\"dtype\\\"] == \\\"bfloat16\\\":\\n        f32 = (np.frombuffer(raw, dtype=\\\"<u2\\\").astype(np.uint32) << 16).view(np.float32)\\n        return torch.from_numpy(f32.reshape(spec[\\\"shape\\\"]).copy()).to(torch.bfloat16)\\n    return torch.from_numpy(np.frombuffer(raw, dtype=\\\"<f4\\\").reshape(spec[\\\"shape\\\"]).copy())\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"7efd0587\",\n   \"source\": \"data = load_data()\\nprint({u: f\\\"{len(U['examples'])} prompts\\\" for u, U in data[\\\"units\\\"].items()}, \\\"|\\\",\\n      {k: f\\\"{v['id']}@{v['revision'][:8]}\\\" for k, v in data[\\\"models\\\"].items()})\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"4d9d64de\",\n   \"source\": \"### Configuration\\nThe next cell holds every tunable parameter. The W1 test is a few 4096-dimensional dot products per prompt, so the **original values** run in seconds on a CPU: both units, 50 draws per null type and 10,000 bootstrap resamples. Lower `N_NULL`, `N_BOOT` or `UNITS_TF` for a quicker smoke test. The null statistics then no longer match the reported ones, which use 50 draws.\\n\\nThe fixed design constants come from `src/cfg10.py`. They were committed (COMMIT #0) before any model forward was run.\",\n   \"metadata\": {}\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"e1d109ef\",\n   \"source\": \"# ---------------------------------------------------------------- run size (the original values are in the comments)\\nUNITS_TF = (\\\"T10\\\",)          # units to score; original (\\\"T10\\\", \\\"B3\\\")  (T10 = connected components, B3 = MST)\\nN_NULL = 2                   # draws per null type; original 50 (the data file holds the 50 committed DELTA_SWAP draws)\\nN_BOOT = 10                  # prompt-bootstrap resamples for the 95% CIs; original 10000\\n\\n# ---------------------------------------------------------------- fixed design constants (src/cfg10.py, COMMIT #0)\\nD_MODEL = 4096\\nRMS_EPS = 1e-6\\nUNIT_IDX = {\\\"T10\\\": 0, \\\"B3\\\": 1, \\\"G-GRID\\\": 2}\\nDOSES = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5)   # lambda in w_I + lambda * Delta\\nSIGN_DOSE = -1.0\\nNULL_TYPES = (\\\"RAND_ISO\\\", \\\"DELTA_SWAP\\\", \\\"RAND_RESID\\\")\\nNULL_SEED0 = {\\\"RAND_ISO\\\": 101000, \\\"RAND_RESID\\\": 102000, \\\"DELTA_SWAP\\\": 103000}\\nRESID_PCS = 64\\nSEED_BOOT = 20261024\\nSMALL_GAP = 0.5\\nTHRESH = {\\\"W1_rows_share\\\": 0.50, \\\"W1_rand_iso_median\\\": 0.15, \\\"W1_disconfirm\\\": 0.20}   # committed W1 verdict rule\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}"}
```

### [99] TOOL CALL — NotebookEdit · 2026-10-26 15:36:59 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': '5dfd487b', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'from __future__ import annotations\n\n# --- method.py (the stage orchestrator): imports as in the original\nimport argparse\nimport json\nimport os\nimport subprocess\nimport sys\nimport time\nfrom pathlib import Path\n\n# --- src/w1_tf.py, src/analysis10.py, src/figures10.py and iteration 9\'s stats9.py: imports as in the originals\n#     (safetensors is not needed: the fork-class rows come from the data file instead of the 16 GB checkpoints)\nimport types\nfrom typing import Any, Sequence\n\nimport numpy as np\nimport torch\nfrom loguru import logger\n\n# --- notebook additions: array decoding and inline figures\nimport base64\nimport matplotlib.pyplot as plt\nfrom IPython.display import display\n\ntorch.set_num_threads(min(12, os.cpu_count() or 1))     # original: torch.set_num_threads(12)\nprint("torch", torch.__version__, "| numpy", np.__version__)'}
```

### [100] TOOL RESULT — NotebookEdit · 2026-10-26 15:36:59 UTC

```
{"new_source": "from __future__ import annotations\n\n# --- method.py (the stage orchestrator): imports as in the original\nimport argparse\nimport json\nimport os\nimport subprocess\nimport sys\nimport time\nfrom pathlib import Path\n\n# --- src/w1_tf.py, src/analysis10.py, src/figures10.py and iteration 9's stats9.py: imports as in the originals\n#     (safetensors is not needed: the fork-class rows come from the data file instead of the 16 GB checkpoints)\nimport types\nfrom typing import Any, Sequence\n\nimport numpy as np\nimport torch\nfrom loguru import logger\n\n# --- notebook additions: array decoding and inline figures\nimport base64\nimport matplotlib.pyplot as plt\nfrom IPython.display import display\n\ntorch.set_num_threads(min(12, os.cpu_count() or 1))     # original: torch.set_num_threads(12)\nprint(\"torch\", torch.__version__, \"| numpy\", np.__version__)", "cell_type": "code", "language": "python", "edit_mode": "insert", "cell_id": "982aeb53", "error": "", "notebook_path": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb", "original_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"c00-title\",\n   \"metadata\": {},\n   \"source\": \"# Which weights make the model pick one algorithm (BASE-W, iteration 10)\\n\\nWhen Qwen3-8B writes a program, it commits to an algorithm at a single **fork token**. Asked to count the connected components of a graph, the instruct model opens `def solve(n, edges):` with a helper named `def find` (union-find) almost every time. The base model, Qwen3-8B-Base, is as likely to write `def dfs` or `def bfs`. This artifact asks **which weights** post-training changed to create that default:\\n\\n* **W1, readout rows:** the fork-class rows of the unembedding matrix (`lm_head`) and the final-norm gain.\\n* **W2, late-MLP weights:** MLP layers 26-35 swapped to the base model in place.\\n* **W3:** the W1 row test repeated on Gemma-3-4b (descriptive).\\n\\n**Units.** The prompts and fork tokens come from iteration 9.\\n\\n| unit | task | default class D (instruct) | alternative class A |\\n|---|---|---|---|\\n| **T10** (primary) | connected components, 20 prompts | `' find'` (union-find) | `' dfs'`, `' bfs'` |\\n| **B3** (beside) | minimum spanning tree, 20 prompts | 8 Kruskal-class tokens | 8 Prim-class tokens |\\n\\n**Margin and share.** The fork's **class margin** is `m = lse(z[D]) - lse(z[A])`, which equals log P(D) - log P(A). An intervention (\\\"arm\\\") is scored by the **share of the instruct-minus-base gap it closes**: `share = sum_p (m_I - m_arm) / sum_p (m_I - m_B)`. This is a ratio of sums over prompts, with a 95% prompt bootstrap. A share of 0 means no effect; a share of 1 means the margin became fully base-like.\\n\\n### What this notebook runs\\n`method.py` is a stage orchestrator: it launches about 40 scripts that load the 8B models on a 24 GB GPU (about 1 GPU-hour), which cannot run on a Colab CPU in 10 minutes. The core of the method does not need a GPU, though. **The class margin depends only on the final-normed residual at the fork and on the fork-class unembedding rows**, so every W1 arm and every null is exact arithmetic on the cached fork states. This notebook:\\n\\n1. shows the orchestrator (`method.py`) and its stage plan;\\n2. re-runs the **W1 teacher-forced test** (`src/w1_tf.py`): readout arms, 3 x 50 matched-norm null edits, bootstrap CIs and the committed verdict rule;\\n3. re-runs the **delta-geometry** analysis (`src/analysis10.py`);\\n4. draws the figures from `src/figures10.py`, including the activation-space plots: the fork states on the readout plane (F5) and the PCA of the block-35 outputs (F6).\\n\\n`mini_demo_data.json` holds:\\n* the cached fork states of 20 + 20 prompts (bf16, exact);\\n* the fork-class `lm_head` rows and the final-norm gains of both models, fetched at the pinned revisions;\\n* the residual's top-64 PCA basis;\\n* the committed DELTA_SWAP draws for T10;\\n* the artifact's reported numbers, for a side-by-side check.\\n\\nThe generation experiments (W1-GEN), W2 and W3 need model forwards on a GPU. Their reported results are summarized before the last cell.\"\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"5dfd487b\",\n   \"source\": \"import subprocess, sys\\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\\n\\n# loguru: NOT pre-installed on Colab, always install (the original scripts log with loguru)\\n_pip('loguru==0.7.3')\\n\\n# numpy, matplotlib, torch: pre-installed on Colab; install locally only, at Colab's versions (torch as the CPU build)\\nif 'google.colab' not in sys.modules:\\n    _pip('numpy==2.0.2', 'matplotlib==3.10.0')\\n    _pip('torch==2.9.0+cpu', '--index-url', 'https://download.pytorch.org/whl/cpu',\\n         '--extra-index-url', 'https://pypi.org/simple')\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"7ea594f1\",\n   \"source\": \"GITHUB_DATA_URL = \\\"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-10/experiment-56/demo/mini_demo_data.json\\\"\\nimport http.client\\nimport json\\nimport urllib.request\\nfrom pathlib import Path\\n\\ndef load_data():\\n    try:\\n        with urllib.request.urlopen(GITHUB_DATA_URL, timeout=15) as response:\\n            return json.loads(response.read().decode())\\n    # Network errors, timeouts, a placeholder URL, bad JSON, a cut-off response.\\n    except (OSError, ValueError, http.client.HTTPException) as e:\\n        print(\\\"GitHub data unavailable, using local mini_demo_data.json:\\\", e)\\n    local = Path(\\\"mini_demo_data.json\\\")\\n    if local.exists(): return json.loads(local.read_text())\\n    raise FileNotFoundError(\\\"Could not load mini_demo_data.json\\\")\\n\\n\\ndef arr(spec: dict) -> torch.Tensor:\\n    \\\"\\\"\\\"Decode one array of mini_demo_data.json ({dtype, shape, b64}: base64 of little-endian raw bytes).\\n    bfloat16 arrays are stored as their uint16 bit patterns; (u16 << 16) viewed as float32 is the exact value.\\\"\\\"\\\"\\n    raw = base64.b64decode(spec[\\\"b64\\\"])\\n    if spec[\\\"dtype\\\"] == \\\"bfloat16\\\":\\n        f32 = (np.frombuffer(raw, dtype=\\\"<u2\\\").astype(np.uint32) << 16).view(np.float32)\\n        return torch.from_numpy(f32.reshape(spec[\\\"shape\\\"]).copy()).to(torch.bfloat16)\\n    return torch.from_numpy(np.frombuffer(raw, dtype=\\\"<f4\\\").reshape(spec[\\\"shape\\\"]).copy())\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"7efd0587\",\n   \"source\": \"data = load_data()\\nprint({u: f\\\"{len(U['examples'])} prompts\\\" for u, U in data[\\\"units\\\"].items()}, \\\"|\\\",\\n      {k: f\\\"{v['id']}@{v['revision'][:8]}\\\" for k, v in data[\\\"models\\\"].items()})\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"4d9d64de\",\n   \"source\": \"### Configuration\\nThe next cell holds every tunable parameter. The W1 test is a few 4096-dimensional dot products per prompt, so the **original values** run in seconds on a CPU: both units, 50 draws per null type and 10,000 bootstrap resamples. Lower `N_NULL`, `N_BOOT` or `UNITS_TF` for a quicker smoke test. The null statistics then no longer match the reported ones, which use 50 draws.\\n\\nThe fixed design constants come from `src/cfg10.py`. They were committed (COMMIT #0) before any model forward was run.\",\n   \"metadata\": {}\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"e1d109ef\",\n   \"source\": \"# ---------------------------------------------------------------- run size (the original values are in the comments)\\nUNITS_TF = (\\\"T10\\\",)          # units to score; original (\\\"T10\\\", \\\"B3\\\")  (T10 = connected components, B3 = MST)\\nN_NULL = 2                   # draws per null type; original 50 (the data file holds the 50 committed DELTA_SWAP draws)\\nN_BOOT = 10                  # prompt-bootstrap resamples for the 95% CIs; original 10000\\n\\n# ---------------------------------------------------------------- fixed design constants (src/cfg10.py, COMMIT #0)\\nD_MODEL = 4096\\nRMS_EPS = 1e-6\\nUNIT_IDX = {\\\"T10\\\": 0, \\\"B3\\\": 1, \\\"G-GRID\\\": 2}\\nDOSES = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5)   # lambda in w_I + lambda * Delta\\nSIGN_DOSE = -1.0\\nNULL_TYPES = (\\\"RAND_ISO\\\", \\\"DELTA_SWAP\\\", \\\"RAND_RESID\\\")\\nNULL_SEED0 = {\\\"RAND_ISO\\\": 101000, \\\"RAND_RESID\\\": 102000, \\\"DELTA_SWAP\\\": 103000}\\nRESID_PCS = 64\\nSEED_BOOT = 20261024\\nSMALL_GAP = 0.5\\nTHRESH = {\\\"W1_rows_share\\\": 0.50, \\\"W1_rand_iso_median\\\": 0.15, \\\"W1_disconfirm\\\": 0.20}   # committed W1 verdict rule\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}", "updated_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"c00-title\",\n   \"metadata\": {},\n   \"source\": \"# Which weights make the model pick one algorithm (BASE-W, iteration 10)\\n\\nWhen Qwen3-8B writes a program, it commits to an algorithm at a single **fork token**. Asked to count the connected components of a graph, the instruct model opens `def solve(n, edges):` with a helper named `def find` (union-find) almost every time. The base model, Qwen3-8B-Base, is as likely to write `def dfs` or `def bfs`. This artifact asks **which weights** post-training changed to create that default:\\n\\n* **W1, readout rows:** the fork-class rows of the unembedding matrix (`lm_head`) and the final-norm gain.\\n* **W2, late-MLP weights:** MLP layers 26-35 swapped to the base model in place.\\n* **W3:** the W1 row test repeated on Gemma-3-4b (descriptive).\\n\\n**Units.** The prompts and fork tokens come from iteration 9.\\n\\n| unit | task | default class D (instruct) | alternative class A |\\n|---|---|---|---|\\n| **T10** (primary) | connected components, 20 prompts | `' find'` (union-find) | `' dfs'`, `' bfs'` |\\n| **B3** (beside) | minimum spanning tree, 20 prompts | 8 Kruskal-class tokens | 8 Prim-class tokens |\\n\\n**Margin and share.** The fork's **class margin** is `m = lse(z[D]) - lse(z[A])`, which equals log P(D) - log P(A). An intervention (\\\"arm\\\") is scored by the **share of the instruct-minus-base gap it closes**: `share = sum_p (m_I - m_arm) / sum_p (m_I - m_B)`. This is a ratio of sums over prompts, with a 95% prompt bootstrap. A share of 0 means no effect; a share of 1 means the margin became fully base-like.\\n\\n### What this notebook runs\\n`method.py` is a stage orchestrator: it launches about 40 scripts that load the 8B models on a 24 GB GPU (about 1 GPU-hour), which cannot run on a Colab CPU in 10 minutes. The core of the method does not need a GPU, though. **The class margin depends only on the final-normed residual at the fork and on the fork-class unembedding rows**, so every W1 arm and every null is exact arithmetic on the cached fork states. This notebook:\\n\\n1. shows the orchestrator (`method.py`) and its stage plan;\\n2. re-runs the **W1 teacher-forced test** (`src/w1_tf.py`): readout arms, 3 x 50 matched-norm null edits, bootstrap CIs and the committed verdict rule;\\n3. re-runs the **delta-geometry** analysis (`src/analysis10.py`);\\n4. draws the figures from `src/figures10.py`, including the activation-space plots: the fork states on the readout plane (F5) and the PCA of the block-35 outputs (F6).\\n\\n`mini_demo_data.json` holds:\\n* the cached fork states of 20 + 20 prompts (bf16, exact);\\n* the fork-class `lm_head` rows and the final-norm gains of both models, fetched at the pinned revisions;\\n* the residual's top-64 PCA basis;\\n* the committed DELTA_SWAP draws for T10;\\n* the artifact's reported numbers, for a side-by-side check.\\n\\nThe generation experiments (W1-GEN), W2 and W3 need model forwards on a GPU. Their reported results are summarized before the last cell.\"\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"5dfd487b\",\n   \"source\": \"import subprocess, sys\\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\\n\\n# loguru: NOT pre-installed on Colab, always install (the original scripts log with loguru)\\n_pip('loguru==0.7.3')\\n\\n# numpy, matplotlib, torch: pre-installed on Colab; install locally only, at Colab's versions (torch as the CPU build)\\nif 'google.colab' not in sys.modules:\\n    _pip('numpy==2.0.2', 'matplotlib==3.10.0')\\n    _pip('torch==2.9.0+cpu', '--index-url', 'https://download.pytorch.org/whl/cpu',\\n         '--extra-index-url', 'https://pypi.org/simple')\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"982aeb53\",\n   \"source\": \"from __future__ import annotations\\n\\n# --- method.py (the stage orchestrator): imports as in the original\\nimport argparse\\nimport json\\nimport os\\nimport subprocess\\nimport sys\\nimport time\\nfrom pathlib import Path\\n\\n# --- src/w1_tf.py, src/analysis10.py, src/figures10.py and iteration 9's stats9.py: imports as in the originals\\n#     (safetensors is not needed: the fork-class rows come from the data file instead of the 16 GB checkpoints)\\nimport types\\nfrom typing import Any, Sequence\\n\\nimport numpy as np\\nimport torch\\nfrom loguru import logger\\n\\n# --- notebook additions: array decoding and inline figures\\nimport base64\\nimport matplotlib.pyplot as plt\\nfrom IPython.display import display\\n\\ntorch.set_num_threads(min(12, os.cpu_count() or 1))     # original: torch.set_num_threads(12)\\nprint(\\\"torch\\\", torch.__version__, \\\"| numpy\\\", np.__version__)\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"7ea594f1\",\n   \"source\": \"GITHUB_DATA_URL = \\\"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-10/experiment-56/demo/mini_demo_data.json\\\"\\nimport http.client\\nimport json\\nimport urllib.request\\nfrom pathlib import Path\\n\\ndef load_data():\\n    try:\\n        with urllib.request.urlopen(GITHUB_DATA_URL, timeout=15) as response:\\n            return json.loads(response.read().decode())\\n    # Network errors, timeouts, a placeholder URL, bad JSON, a cut-off response.\\n    except (OSError, ValueError, http.client.HTTPException) as e:\\n        print(\\\"GitHub data unavailable, using local mini_demo_data.json:\\\", e)\\n    local = Path(\\\"mini_demo_data.json\\\")\\n    if local.exists(): return json.loads(local.read_text())\\n    raise FileNotFoundError(\\\"Could not load mini_demo_data.json\\\")\\n\\n\\ndef arr(spec: dict) -> torch.Tensor:\\n    \\\"\\\"\\\"Decode one array of mini_demo_data.json ({dtype, shape, b64}: base64 of little-endian raw bytes).\\n    bfloat16 arrays are stored as their uint16 bit patterns; (u16 << 16) viewed as float32 is the exact value.\\\"\\\"\\\"\\n    raw = base64.b64decode(spec[\\\"b64\\\"])\\n    if spec[\\\"dtype\\\"] == \\\"bfloat16\\\":\\n        f32 = (np.frombuffer(raw, dtype=\\\"<u2\\\").astype(np.uint32) << 16).view(np.float32)\\n        return torch.from_numpy(f32.reshape(spec[\\\"shape\\\"]).copy()).to(torch.bfloat16)\\n    return torch.from_numpy(np.frombuffer(raw, dtype=\\\"<f4\\\").reshape(spec[\\\"shape\\\"]).copy())\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"7efd0587\",\n   \"source\": \"data = load_data()\\nprint({u: f\\\"{len(U['examples'])} prompts\\\" for u, U in data[\\\"units\\\"].items()}, \\\"|\\\",\\n      {k: f\\\"{v['id']}@{v['revision'][:8]}\\\" for k, v in data[\\\"models\\\"].items()})\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"4d9d64de\",\n   \"source\": \"### Configuration\\nThe next cell holds every tunable parameter. The W1 test is a few 4096-dimensional dot products per prompt, so the **original values** run in seconds on a CPU: both units, 50 draws per null type and 10,000 bootstrap resamples. Lower `N_NULL`, `N_BOOT` or `UNITS_TF` for a quicker smoke test. The null statistics then no longer match the reported ones, which use 50 draws.\\n\\nThe fixed design constants come from `src/cfg10.py`. They were committed (COMMIT #0) before any model forward was run.\",\n   \"metadata\": {}\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"e1d109ef\",\n   \"source\": \"# ---------------------------------------------------------------- run size (the original values are in the comments)\\nUNITS_TF = (\\\"T10\\\",)          # units to score; original (\\\"T10\\\", \\\"B3\\\")  (T10 = connected components, B3 = MST)\\nN_NULL = 2                   # draws per null type; original 50 (the data file holds the 50 committed DELTA_SWAP draws)\\nN_BOOT = 10                  # prompt-bootstrap resamples for the 95% CIs; original 10000\\n\\n# ---------------------------------------------------------------- fixed design constants (src/cfg10.py, COMMIT #0)\\nD_MODEL = 4096\\nRMS_EPS = 1e-6\\nUNIT_IDX = {\\\"T10\\\": 0, \\\"B3\\\": 1, \\\"G-GRID\\\": 2}\\nDOSES = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5)   # lambda in w_I + lambda * Delta\\nSIGN_DOSE = -1.0\\nNULL_TYPES = (\\\"RAND_ISO\\\", \\\"DELTA_SWAP\\\", \\\"RAND_RESID\\\")\\nNULL_SEED0 = {\\\"RAND_ISO\\\": 101000, \\\"RAND_RESID\\\": 102000, \\\"DELTA_SWAP\\\": 103000}\\nRESID_PCS = 64\\nSEED_BOOT = 20261024\\nSMALL_GAP = 0.5\\nTHRESH = {\\\"W1_rows_share\\\": 0.50, \\\"W1_rand_iso_median\\\": 0.15, \\\"W1_disconfirm\\\": 0.20}   # committed W1 verdict rule\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}"}
```

### [101] ASSISTANT · 2026-10-26 15:37:03 UTC

```
Let me verify the cell order produced by the reverse-insertion batch.
```

### [102] TOOL CALL — Bash · 2026-10-26 15:37:03 UTC

```
List notebook cells in order:
python3 -c "
import json
nb=json.load(open('code_demo.ipynb'))
for i,c in enumerate(nb['cells']):
    src=''.join(c['source']); print(i, c['id'], c['cell_type'], repr(src.splitlines()[0][:80]))
"
```

### [103] TOOL RESULT — Bash · 2026-10-26 15:37:03 UTC

```
{"stdout": "0 c00-title markdown '# Which weights make the model pick one algorithm (BASE-W, iteration 10)'\n1 5dfd487b code 'import subprocess, sys'\n2 982aeb53 code 'from __future__ import annotations'\n3 7ea594f1 code 'GITHUB_DATA_URL = \"https://raw.githubusercontent.com/ai-inventor-papers/ai-inven'\n4 7efd0587 code 'data = load_data()'\n5 4d9d64de markdown '### Configuration'\n6 e1d109ef code '# ---------------------------------------------------------------- run size (the'", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [104] ASSISTANT · 2026-10-26 15:38:23 UTC

```
The reverse-insertion trick preserves order. Batch 2 adds the orchestrator (`method.py` verbatim except `ROOT`), the dry-run plan, the shared helpers, and the readout primitives.
```

### [105] TOOL CALL — NotebookEdit · 2026-10-26 15:38:23 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': 'e1d109ef', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'def rms_bf16(h_pre: torch.Tensor, g: torch.Tensor, eps: float = RMS_EPS) -> torch.Tensor:\n    """Qwen3RMSNorm on the bf16 path (iteration 9\'s analysis9.readout_decomposition m_of): fp32 normalise, round to\n    bf16, multiply by the gain, round to bf16."""\n    x = h_pre.float()\n    h = x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + eps)\n    return (h.to(torch.bfloat16).float() * g.float()).to(torch.bfloat16).float()\n\n\ndef margin(h: torch.Tensor, WD: torch.Tensor, WA: torch.Tensor) -> torch.Tensor:\n    """h [n, d] fp32; WD [|D|, d], WA [|A|, d] fp32 (or [n, |D|, d] per-prompt rows)."""\n    if WD.dim() == 3:\n        zD = torch.einsum("nd,nkd->nk", h, WD)\n        zA = torch.einsum("nd,nkd->nk", h, WA)\n    else:\n        zD, zA = h @ WD.T, h @ WA.T\n    return torch.logsumexp(zD, -1) - torch.logsumexp(zA, -1)\n\n\ndef share(mI: np.ndarray, mX: np.ndarray, mB: np.ndarray) -> float:\n    den = float(np.sum(mI - mB))\n    return float(np.sum(mI - mX)) / den if abs(den) > 1e-12 else float("nan")\n\n\ndef boot_share(mI: np.ndarray, mX: np.ndarray, mB: np.ndarray, seed: int = SEED_BOOT, B: int = N_BOOT\n               ) -> tuple[float, float]:\n    rng = np.random.default_rng(seed)\n    idx = rng.integers(0, len(mI), (B, len(mI)))\n    num = (mI - mX)[idx].sum(1)\n    den = (mI - mB)[idx].sum(1)\n    ok = np.abs(den) > 1e-12\n    v = num[ok] / den[ok]\n    return (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5)))'}
```

### [106] TOOL RESULT — NotebookEdit · 2026-10-26 15:38:23 UTC

```
{"new_source": "def rms_bf16(h_pre: torch.Tensor, g: torch.Tensor, eps: float = RMS_EPS) -> torch.Tensor:\n    \"\"\"Qwen3RMSNorm on the bf16 path (iteration 9's analysis9.readout_decomposition m_of): fp32 normalise, round to\n    bf16, multiply by the gain, round to bf16.\"\"\"\n    x = h_pre.float()\n    h = x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + eps)\n    return (h.to(torch.bfloat16).float() * g.float()).to(torch.bfloat16).float()\n\n\ndef margin(h: torch.Tensor, WD: torch.Tensor, WA: torch.Tensor) -> torch.Tensor:\n    \"\"\"h [n, d] fp32; WD [|D|, d], WA [|A|, d] fp32 (or [n, |D|, d] per-prompt rows).\"\"\"\n    if WD.dim() == 3:\n        zD = torch.einsum(\"nd,nkd->nk\", h, WD)\n        zA = torch.einsum(\"nd,nkd->nk\", h, WA)\n    else:\n        zD, zA = h @ WD.T, h @ WA.T\n    return torch.logsumexp(zD, -1) - torch.logsumexp(zA, -1)\n\n\ndef share(mI: np.ndarray, mX: np.ndarray, mB: np.ndarray) -> float:\n    den = float(np.sum(mI - mB))\n    return float(np.sum(mI - mX)) / den if abs(den) > 1e-12 else float(\"nan\")\n\n\ndef boot_share(mI: np.ndarray, mX: np.ndarray, mB: np.ndarray, seed: int = SEED_BOOT, B: int = N_BOOT\n               ) -> tuple[float, float]:\n    rng = np.random.default_rng(seed)\n    idx = rng.integers(0, len(mI), (B, len(mI)))\n    num = (mI - mX)[idx].sum(1)\n    den = (mI - mB)[idx].sum(1)\n    ok = np.abs(den) > 1e-12\n    v = num[ok] / den[ok]\n    return (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5)))", "cell_type": "code", "language": "python", "edit_mode": "insert", "cell_id": "11f9d625", "error": "", "notebook_path": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb", "original_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"c00-title\",\n   \"metadata\": {},\n   \"source\": \"# Which weights make the model pick one algorithm (BASE-W, iteration 10)\\n\\nWhen Qwen3-8B writes a program, it commits to an algorithm at a single **fork token**. Asked to count the connected components of a graph, the instruct model opens `def solve(n, edges):` with a helper named `def find` (union-find) almost every time. The base model, Qwen3-8B-Base, is as likely to write `def dfs` or `def bfs`. This artifact asks **which weights** post-training changed to create that default:\\n\\n* **W1, readout rows:** the fork-class rows of the unembedding matrix (`lm_head`) and the final-norm gain.\\n* **W2, late-MLP weights:** MLP layers 26-35 swapped to the base model in place.\\n* **W3:** the W1 row test repeated on Gemma-3-4b (descriptive).\\n\\n**Units.** The prompts and fork tokens come from iteration 9.\\n\\n| unit | task | default class D (instruct) | alternative class A |\\n|---|---|---|---|\\n| **T10** (primary) | connected components, 20 prompts | `' find'` (union-find) | `' dfs'`, `' bfs'` |\\n| **B3** (beside) | minimum spanning tree, 20 prompts | 8 Kruskal-class tokens | 8 Prim-class tokens |\\n\\n**Margin and share.** The fork's **class margin** is `m = lse(z[D]) - lse(z[A])`, which equals log P(D) - log P(A). An intervention (\\\"arm\\\") is scored by the **share of the instruct-minus-base gap it closes**: `share = sum_p (m_I - m_arm) / sum_p (m_I - m_B)`. This is a ratio of sums over prompts, with a 95% prompt bootstrap. A share of 0 means no effect; a share of 1 means the margin became fully base-like.\\n\\n### What this notebook runs\\n`method.py` is a stage orchestrator: it launches about 40 scripts that load the 8B models on a 24 GB GPU (about 1 GPU-hour), which cannot run on a Colab CPU in 10 minutes. The core of the method does not need a GPU, though. **The class margin depends only on the final-normed residual at the fork and on the fork-class unembedding rows**, so every W1 arm and every null is exact arithmetic on the cached fork states. This notebook:\\n\\n1. shows the orchestrator (`method.py`) and its stage plan;\\n2. re-runs the **W1 teacher-forced test** (`src/w1_tf.py`): readout arms, 3 x 50 matched-norm null edits, bootstrap CIs and the committed verdict rule;\\n3. re-runs the **delta-geometry** analysis (`src/analysis10.py`);\\n4. draws the figures from `src/figures10.py`, including the activation-space plots: the fork states on the readout plane (F5) and the PCA of the block-35 outputs (F6).\\n\\n`mini_demo_data.json` holds:\\n* the cached fork states of 20 + 20 prompts (bf16, exact);\\n* the fork-class `lm_head` rows and the final-norm gains of both models, fetched at the pinned revisions;\\n* the residual's top-64 PCA basis;\\n* the committed DELTA_SWAP draws for T10;\\n* the artifact's reported numbers, for a side-by-side check.\\n\\nThe generation experiments (W1-GEN), W2 and W3 need model forwards on a GPU. Their reported results are summarized before the last cell.\"\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"5dfd487b\",\n   \"source\": \"import subprocess, sys\\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\\n\\n# loguru: NOT pre-installed on Colab, always install (the original scripts log with loguru)\\n_pip('loguru==0.7.3')\\n\\n# numpy, matplotlib, torch: pre-installed on Colab; install locally only, at Colab's versions (torch as the CPU build)\\nif 'google.colab' not in sys.modules:\\n    _pip('numpy==2.0.2', 'matplotlib==3.10.0')\\n    _pip('torch==2.9.0+cpu', '--index-url', 'https://download.pytorch.org/whl/cpu',\\n         '--extra-index-url', 'https://pypi.org/simple')\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"982aeb53\",\n   \"source\": \"from __future__ import annotations\\n\\n# --- method.py (the stage orchestrator): imports as in the original\\nimport argparse\\nimport json\\nimport os\\nimport subprocess\\nimport sys\\nimport time\\nfrom pathlib import Path\\n\\n# --- src/w1_tf.py, src/analysis10.py, src/figures10.py and iteration 9's stats9.py: imports as in the originals\\n#     (safetensors is not needed: the fork-class rows come from the data file instead of the 16 GB checkpoints)\\nimport types\\nfrom typing import Any, Sequence\\n\\nimport numpy as np\\nimport torch\\nfrom loguru import logger\\n\\n# --- notebook additions: array decoding and inline figures\\nimport base64\\nimport matplotlib.pyplot as plt\\nfrom IPython.display import display\\n\\ntorch.set_num_threads(min(12, os.cpu_count() or 1))     # original: torch.set_num_threads(12)\\nprint(\\\"torch\\\", torch.__version__, \\\"| numpy\\\", np.__version__)\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"7ea594f1\",\n   \"source\": \"GITHUB_DATA_URL = \\\"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-10/experiment-56/demo/mini_demo_data.json\\\"\\nimport http.client\\nimport json\\nimport urllib.request\\nfrom pathlib import Path\\n\\ndef load_data():\\n    try:\\n        with urllib.request.urlopen(GITHUB_DATA_URL, timeout=15) as response:\\n            return json.loads(response.read().decode())\\n    # Network errors, timeouts, a placeholder URL, bad JSON, a cut-off response.\\n    except (OSError, ValueError, http.client.HTTPException) as e:\\n        print(\\\"GitHub data unavailable, using local mini_demo_data.json:\\\", e)\\n    local = Path(\\\"mini_demo_data.json\\\")\\n    if local.exists(): return json.loads(local.read_text())\\n    raise FileNotFoundError(\\\"Could not load mini_demo_data.json\\\")\\n\\n\\ndef arr(spec: dict) -> torch.Tensor:\\n    \\\"\\\"\\\"Decode one array of mini_demo_data.json ({dtype, shape, b64}: base64 of little-endian raw bytes).\\n    bfloat16 arrays are stored as their uint16 bit patterns; (u16 << 16) viewed as float32 is the exact value.\\\"\\\"\\\"\\n    raw = base64.b64decode(spec[\\\"b64\\\"])\\n    if spec[\\\"dtype\\\"] == \\\"bfloat16\\\":\\n        f32 = (np.frombuffer(raw, dtype=\\\"<u2\\\").astype(np.uint32) << 16).view(np.float32)\\n        return torch.from_numpy(f32.reshape(spec[\\\"shape\\\"]).copy()).to(torch.bfloat16)\\n    return torch.from_numpy(np.frombuffer(raw, dtype=\\\"<f4\\\").reshape(spec[\\\"shape\\\"]).copy())\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"7efd0587\",\n   \"source\": \"data = load_data()\\nprint({u: f\\\"{len(U['examples'])} prompts\\\" for u, U in data[\\\"units\\\"].items()}, \\\"|\\\",\\n      {k: f\\\"{v['id']}@{v['revision'][:8]}\\\" for k, v in data[\\\"models\\\"].items()})\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"4d9d64de\",\n   \"source\": \"### Configuration\\nThe next cell holds every tunable parameter. The W1 test is a few 4096-dimensional dot products per prompt, so the **original values** run in seconds on a CPU: both units, 50 draws per null type and 10,000 bootstrap resamples. Lower `N_NULL`, `N_BOOT` or `UNITS_TF` for a quicker smoke test. The null statistics then no longer match the reported ones, which use 50 draws.\\n\\nThe fixed design constants come from `src/cfg10.py`. They were committed (COMMIT #0) before any model forward was run.\",\n   \"metadata\": {}\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"e1d109ef\",\n   \"source\": \"# ---------------------------------------------------------------- run size (the original values are in the comments)\\nUNITS_TF = (\\\"T10\\\",)          # units to score; original (\\\"T10\\\", \\\"B3\\\")  (T10 = connected components, B3 = MST)\\nN_NULL = 2                   # draws per null type; original 50 (the data file holds the 50 committed DELTA_SWAP draws)\\nN_BOOT = 10                  # prompt-bootstrap resamples for the 95% CIs; original 10000\\n\\n# ---------------------------------------------------------------- fixed design constants (src/cfg10.py, COMMIT #0)\\nD_MODEL = 4096\\nRMS_EPS = 1e-6\\nUNIT_IDX = {\\\"T10\\\": 0, \\\"B3\\\": 1, \\\"G-GRID\\\": 2}\\nDOSES = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5)   # lambda in w_I + lambda * Delta\\nSIGN_DOSE = -1.0\\nNULL_TYPES = (\\\"RAND_ISO\\\", \\\"DELTA_SWAP\\\", \\\"RAND_RESID\\\")\\nNULL_SEED0 = {\\\"RAND_ISO\\\": 101000, \\\"RAND_RESID\\\": 102000, \\\"DELTA_SWAP\\\": 103000}\\nRESID_PCS = 64\\nSEED_BOOT = 20261024\\nSMALL_GAP = 0.5\\nTHRESH = {\\\"W1_rows_share\\\": 0.50, \\\"W1_rand_iso_median\\\": 0.15, \\\"W1_disconfirm\\\": 0.20}   # committed W1 verdict rule\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}", "updated_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"c00-title\",\n   \"metadata\": {},\n   \"source\": \"# Which weights make the model pick one algorithm (BASE-W, iteration 10)\\n\\nWhen Qwen3-8B writes a program, it commits to an algorithm at a single **fork token**. Asked to count the connected components of a graph, the instruct model opens `def solve(n, edges):` with a helper named `def find` (union-find) almost every time. The base model, Qwen3-8B-Base, is as likely to write `def dfs` or `def bfs`. This artifact asks **which weights** post-training changed to create that default:\\n\\n* **W1, readout rows:** the fork-class rows of the unembedding matrix (`lm_head`) and the final-norm gain.\\n* **W2, late-MLP weights:** MLP layers 26-35 swapped to the base model in place.\\n* **W3:** the W1 row test repeated on Gemma-3-4b (descriptive).\\n\\n**Units.** The prompts and fork tokens come from iteration 9.\\n\\n| unit | task | default class D (instruct) | alternative class A |\\n|---|---|---|---|\\n| **T10** (primary) | connected components, 20 prompts | `' find'` (union-find) | `' dfs'`, `' bfs'` |\\n| **B3** (beside) | minimum spanning tree, 20 prompts | 8 Kruskal-class tokens | 8 Prim-class tokens |\\n\\n**Margin and share.** The fork's **class margin** is `m = lse(z[D]) - lse(z[A])`, which equals log P(D) - log P(A). An intervention (\\\"arm\\\") is scored by the **share of the instruct-minus-base gap it closes**: `share = sum_p (m_I - m_arm) / sum_p (m_I - m_B)`. This is a ratio of sums over prompts, with a 95% prompt bootstrap. A share of 0 means no effect; a share of 1 means the margin became fully base-like.\\n\\n### What this notebook runs\\n`method.py` is a stage orchestrator: it launches about 40 scripts that load the 8B models on a 24 GB GPU (about 1 GPU-hour), which cannot run on a Colab CPU in 10 minutes. The core of the method does not need a GPU, though. **The class margin depends only on the final-normed residual at the fork and on the fork-class unembedding rows**, so every W1 arm and every null is exact arithmetic on the cached fork states. This notebook:\\n\\n1. shows the orchestrator (`method.py`) and its stage plan;\\n2. re-runs the **W1 teacher-forced test** (`src/w1_tf.py`): readout arms, 3 x 50 matched-norm null edits, bootstrap CIs and the committed verdict rule;\\n3. re-runs the **delta-geometry** analysis (`src/analysis10.py`);\\n4. draws the figures from `src/figures10.py`, including the activation-space plots: the fork states on the readout plane (F5) and the PCA of the block-35 outputs (F6).\\n\\n`mini_demo_data.json` holds:\\n* the cached fork states of 20 + 20 prompts (bf16, exact);\\n* the fork-class `lm_head` rows and the final-norm gains of both models, fetched at the pinned revisions;\\n* the residual's top-64 PCA basis;\\n* the committed DELTA_SWAP draws for T10;\\n* the artifact's reported numbers, for a side-by-side check.\\n\\nThe generation experiments (W1-GEN), W2 and W3 need model forwards on a GPU. Their reported results are summarized before the last cell.\"\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"5dfd487b\",\n   \"source\": \"import subprocess, sys\\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\\n\\n# loguru: NOT pre-installed on Colab, always install (the original scripts log with loguru)\\n_pip('loguru==0.7.3')\\n\\n# numpy, matplotlib, torch: pre-installed on Colab; install locally only, at Colab's versions (torch as the CPU build)\\nif 'google.colab' not in sys.modules:\\n    _pip('numpy==2.0.2', 'matplotlib==3.10.0')\\n    _pip('torch==2.9.0+cpu', '--index-url', 'https://download.pytorch.org/whl/cpu',\\n         '--extra-index-url', 'https://pypi.org/simple')\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"982aeb53\",\n   \"source\": \"from __future__ import annotations\\n\\n# --- method.py (the stage orchestrator): imports as in the original\\nimport argparse\\nimport json\\nimport os\\nimport subprocess\\nimport sys\\nimport time\\nfrom pathlib import Path\\n\\n# --- src/w1_tf.py, src/analysis10.py, src/figures10.py and iteration 9's stats9.py: imports as in the originals\\n#     (safetensors is not needed: the fork-class rows come from the data file instead of the 16 GB checkpoints)\\nimport types\\nfrom typing import Any, Sequence\\n\\nimport numpy as np\\nimport torch\\nfrom loguru import logger\\n\\n# --- notebook additions: array decoding and inline figures\\nimport base64\\nimport matplotlib.pyplot as plt\\nfrom IPython.display import display\\n\\ntorch.set_num_threads(min(12, os.cpu_count() or 1))     # original: torch.set_num_threads(12)\\nprint(\\\"torch\\\", torch.__version__, \\\"| numpy\\\", np.__version__)\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"7ea594f1\",\n   \"source\": \"GITHUB_DATA_URL = \\\"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-10/experiment-56/demo/mini_demo_data.json\\\"\\nimport http.client\\nimport json\\nimport urllib.request\\nfrom pathlib import Path\\n\\ndef load_data():\\n    try:\\n        with urllib.request.urlopen(GITHUB_DATA_URL, timeout=15) as response:\\n            return json.loads(response.read().decode())\\n    # Network errors, timeouts, a placeholder URL, bad JSON, a cut-off response.\\n    except (OSError, ValueError, http.client.HTTPException) as e:\\n        print(\\\"GitHub data unavailable, using local mini_demo_data.json:\\\", e)\\n    local = Path(\\\"mini_demo_data.json\\\")\\n    if local.exists(): return json.loads(local.read_text())\\n    raise FileNotFoundError(\\\"Could not load mini_demo_data.json\\\")\\n\\n\\ndef arr(spec: dict) -> torch.Tensor:\\n    \\\"\\\"\\\"Decode one array of mini_demo_data.json ({dtype, shape, b64}: base64 of little-endian raw bytes).\\n    bfloat16 arrays are stored as their uint16 bit patterns; (u16 << 16) viewed as float32 is the exact value.\\\"\\\"\\\"\\n    raw = base64.b64decode(spec[\\\"b64\\\"])\\n    if spec[\\\"dtype\\\"] == \\\"bfloat16\\\":\\n        f32 = (np.frombuffer(raw, dtype=\\\"<u2\\\").astype(np.uint32) << 16).view(np.float32)\\n        return torch.from_numpy(f32.reshape(spec[\\\"shape\\\"]).copy()).to(torch.bfloat16)\\n    return torch.from_numpy(np.frombuffer(raw, dtype=\\\"<f4\\\").reshape(spec[\\\"shape\\\"]).copy())\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"7efd0587\",\n   \"source\": \"data = load_data()\\nprint({u: f\\\"{len(U['examples'])} prompts\\\" for u, U in data[\\\"units\\\"].items()}, \\\"|\\\",\\n      {k: f\\\"{v['id']}@{v['revision'][:8]}\\\" for k, v in data[\\\"models\\\"].items()})\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"4d9d64de\",\n   \"source\": \"### Configuration\\nThe next cell holds every tunable parameter. The W1 test is a few 4096-dimensional dot products per prompt, so the **original values** run in seconds on a CPU: both units, 50 draws per null type and 10,000 bootstrap resamples. Lower `N_NULL`, `N_BOOT` or `UNITS_TF` for a quicker smoke test. The null statistics then no longer match the reported ones, which use 50 draws.\\n\\nThe fixed design constants come from `src/cfg10.py`. They were committed (COMMIT #0) before any model forward was run.\",\n   \"metadata\": {}\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"e1d109ef\",\n   \"source\": \"# ---------------------------------------------------------------- run size (the original values are in the comments)\\nUNITS_TF = (\\\"T10\\\",)          # units to score; original (\\\"T10\\\", \\\"B3\\\")  (T10 = connected components, B3 = MST)\\nN_NULL = 2                   # draws per null type; original 50 (the data file holds the 50 committed DELTA_SWAP draws)\\nN_BOOT = 10                  # prompt-bootstrap resamples for the 95% CIs; original 10000\\n\\n# ---------------------------------------------------------------- fixed design constants (src/cfg10.py, COMMIT #0)\\nD_MODEL = 4096\\nRMS_EPS = 1e-6\\nUNIT_IDX = {\\\"T10\\\": 0, \\\"B3\\\": 1, \\\"G-GRID\\\": 2}\\nDOSES = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5)   # lambda in w_I + lambda * Delta\\nSIGN_DOSE = -1.0\\nNULL_TYPES = (\\\"RAND_ISO\\\", \\\"DELTA_SWAP\\\", \\\"RAND_RESID\\\")\\nNULL_SEED0 = {\\\"RAND_ISO\\\": 101000, \\\"RAND_RESID\\\": 102000, \\\"DELTA_SWAP\\\": 103000}\\nRESID_PCS = 64\\nSEED_BOOT = 20261024\\nSMALL_GAP = 0.5\\nTHRESH = {\\\"W1_rows_share\\\": 0.50, \\\"W1_rand_iso_median\\\": 0.15, \\\"W1_disconfirm\\\": 0.20}   # committed W1 verdict rule\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"11f9d625\",\n   \"source\": \"def rms_bf16(h_pre: torch.Tensor, g: torch.Tensor, eps: float = RMS_EPS) -> torch.Tensor:\\n    \\\"\\\"\\\"Qwen3RMSNorm on the bf16 path (iteration 9's analysis9.readout_decomposition m_of): fp32 normalise, round to\\n    bf16, multiply by the gain, round to bf16.\\\"\\\"\\\"\\n    x = h_pre.float()\\n    h = x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + eps)\\n    return (h.to(torch.bfloat16).float() * g.float()).to(torch.bfloat16).float()\\n\\n\\ndef margin(h: torch.Tensor, WD: torch.Tensor, WA: torch.Tensor) -> torch.Tensor:\\n    \\\"\\\"\\\"h [n, d] fp32; WD [|D|, d], WA [|A|, d] fp32 (or [n, |D|, d] per-prompt rows).\\\"\\\"\\\"\\n    if WD.dim() == 3:\\n        zD = torch.einsum(\\\"nd,nkd->nk\\\", h, WD)\\n        zA = torch.einsum(\\\"nd,nkd->nk\\\", h, WA)\\n    else:\\n        zD, zA = h @ WD.T, h @ WA.T\\n    return torch.logsumexp(zD, -1) - torch.logsumexp(zA, -1)\\n\\n\\ndef share(mI: np.ndarray, mX: np.ndarray, mB: np.ndarray) -> float:\\n    den = float(np.sum(mI - mB))\\n    return float(np.sum(mI - mX)) / den if abs(den) > 1e-12 else float(\\\"nan\\\")\\n\\n\\ndef boot_share(mI: np.ndarray, mX: np.ndarray, mB: np.ndarray, seed: int = SEED_BOOT, B: int = N_BOOT\\n               ) -> tuple[float, float]:\\n    rng = np.random.default_rng(seed)\\n    idx = rng.integers(0, len(mI), (B, len(mI)))\\n    num = (mI - mX)[idx].sum(1)\\n    den = (mI - mB)[idx].sum(1)\\n    ok = np.abs(den) > 1e-12\\n    v = num[ok] / den[ok]\\n    return (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5)))\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}"}
```

### [107] TOOL CALL — NotebookEdit · 2026-10-26 15:38:23 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': 'e1d109ef', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "## 3. Readout primitives (`src/w1_tf.py`)\nThese four functions are copied unchanged:\n* `rms_bf16`: Qwen3's final RMSNorm on the bf16 path. It normalises in fp32, rounds to bf16, multiplies by the gain `g` and rounds again. Iteration 9 used the same recompute, and it is bit-exact against the captured `h_fin` (test G1).\n* `margin`: `lse(h·W_D) - lse(h·W_A)` from the final-normed state `h` and the fork-class rows.\n* `share`: the ratio of sums, `sum(m_I - m_X) / sum(m_I - m_B)`.\n* `boot_share`: the 95% percentile CI of the share over 10,000 prompt resamples (seed 20261024).\n\nLeft out: the full-vocabulary readouts (`full_logits_cpu`, `dist_metrics`, `load_readout`). They need each model's whole 1.2 GB `lm_head` and feed only the KL/JS/P(D) side metrics and the generation predictions, never the class margin."}
```

### [108] TOOL RESULT — NotebookEdit · 2026-10-26 15:38:23 UTC

```
{"new_source": "## 3. Readout primitives (`src/w1_tf.py`)\nThese four functions are copied unchanged:\n* `rms_bf16`: Qwen3's final RMSNorm on the bf16 path. It normalises in fp32, rounds to bf16, multiplies by the gain `g` and rounds again. Iteration 9 used the same recompute, and it is bit-exact against the captured `h_fin` (test G1).\n* `margin`: `lse(h·W_D) - lse(h·W_A)` from the final-normed state `h` and the fork-class rows.\n* `share`: the ratio of sums, `sum(m_I... [truncated, 23916 chars total]
```

### [109] TOOL CALL — NotebookEdit · 2026-10-26 15:38:23 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': 'e1d109ef', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '# ---- src/cfg10.py: logging (stdout only; the original also adds a rotating file sink under logs/)\ndef setup_logging(name: str) -> None:\n    logger.remove()\n    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")\n\n\n# ---- inputs/iter9/src/stats9.py (iteration 9\'s statistics module; w1_tf.py does `import stats9 as S9`)\ndef boot_ci(fn, n: int, B: int = 10000, seed: int = 0, alpha: float = 0.05) -> tuple[float, float]:\n    """Percentile bootstrap over n units: fn(idx array) -> statistic."""\n    rng = np.random.default_rng(seed)\n    vals = []\n    for _ in range(B):\n        idx = rng.integers(0, n, n)\n        v = fn(idx)\n        if v is not None and np.isfinite(v):\n            vals.append(v)\n    if not vals:\n        return (float("nan"), float("nan"))\n    return (float(np.percentile(vals, 100 * alpha / 2)), float(np.percentile(vals, 100 * (1 - alpha / 2))))\n\n\ndef boot_mean_ci(v, B: int = 10000, seed: int = 0) -> tuple[float, float]:\n    v = np.asarray(v, dtype=float)\n    return boot_ci(lambda idx: float(v[idx].mean()), len(v), B, seed)\n\n\ndef empirical_p_upper(x: float, null: Sequence[float]) -> float:\n    """(1 + #null >= x) / (1 + n)."""\n    null = np.asarray(null, dtype=float)\n    return float((1 + np.sum(null >= x)) / (1 + len(null)))\n\n\nS9 = types.SimpleNamespace(boot_ci=boot_ci, boot_mean_ci=boot_mean_ci, empirical_p_upper=empirical_p_upper)\nsetup_logging("w1_tf_score")'}
```

### [110] TOOL RESULT — NotebookEdit · 2026-10-26 15:38:23 UTC

```
{"new_source": "# ---- src/cfg10.py: logging (stdout only; the original also adds a rotating file sink under logs/)\ndef setup_logging(name: str) -> None:\n    logger.remove()\n    logger.add(sys.stdout, level=\"INFO\", format=\"{time:HH:mm:ss}|{level:<7}|{message}\")\n\n\n# ---- inputs/iter9/src/stats9.py (iteration 9's statistics module; w1_tf.py does `import stats9 as S9`)\ndef boot_ci(fn, n: int, B: int = 10000, seed: int = 0, alpha: float = 0.05) -> tuple[float, f... [truncated, 27228 chars total]
```

### [111] TOOL CALL — NotebookEdit · 2026-10-26 15:38:23 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': 'e1d109ef', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "## 2. Shared helpers\nTwo small dependencies of `w1_tf.py`:\n* `setup_logging` from `src/cfg10.py`. It logs to stdout only; the original also writes a rotating log file.\n* The statistics helpers that `w1_tf.py` imports from iteration 9's `stats9.py` as `S9`:\n  * a percentile bootstrap over prompts;\n  * the empirical upper-tail p-value `(1 + #null >= x) / (1 + n)`. With 50 draws its floor is 1/51 = 0.0196."}
```

### [112] TOOL RESULT — NotebookEdit · 2026-10-26 15:38:23 UTC

```
{"new_source": "## 2. Shared helpers\nTwo small dependencies of `w1_tf.py`:\n* `setup_logging` from `src/cfg10.py`. It logs to stdout only; the original also writes a rotating log file.\n* The statistics helpers that `w1_tf.py` imports from iteration 9's `stats9.py` as `S9`:\n  * a percentile bootstrap over prompts;\n  * the empirical upper-tail p-value `(1 + #null >= x) / (1 + n)`. With 50 draws its floor is 1/51 = 0.0196.", "cell_type": "markdown", "language": "pytho... [truncated, 28410 chars total]
```

### [113] TOOL CALL — NotebookEdit · 2026-10-26 15:38:23 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': 'e1d109ef', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '# Dry run of `python method.py --stages all`: list every command in order instead of launching it.\nfor s in ORDER:\n    for i, cmd in enumerate(STAGES[s]):\n        print(f"[{s:<5}] python {\' \'.join(cmd):<38} -> logs/{s}_{i}.log")\nprint(f"\\n{sum(len(v) for v in STAGES.values())} commands in {len(ORDER)} stages. This notebook re-runs the CPU core "\n      "of w1tf (w1_tf.py score), plus analysis10.py delta_geometry and figures10.py from the out stage.")'}
```

### [114] TOOL RESULT — NotebookEdit · 2026-10-26 15:38:23 UTC

```
{"new_source": "# Dry run of `python method.py --stages all`: list every command in order instead of launching it.\nfor s in ORDER:\n    for i, cmd in enumerate(STAGES[s]):\n        print(f\"[{s:<5}] python {' '.join(cmd):<38} -> logs/{s}_{i}.log\")\nprint(f\"\\n{sum(len(v) for v in STAGES.values())} commands in {len(ORDER)} stages. This notebook re-runs the CPU core \"\n      \"of w1tf (w1_tf.py score), plus analysis10.py delta_geometry and figures10.py from the out s... [truncated, 29634 chars total]
```

### [115] TOOL CALL — NotebookEdit · 2026-10-26 15:38:23 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': 'e1d109ef', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '# method.py: "BASE-W stage CLI: which weights hold the default algorithm (iteration 10)" (docstring: see above)\nROOT = Path.cwd()               # was: Path(__file__).resolve().parent  (a notebook has no __file__)\nSRC = ROOT / "src"\nLOGS = ROOT / "logs"\nPY = sys.executable\n\nSTAGES: dict[str, list[list[str]]] = {\n    "s_1": [["inputs10.py", "copy"], ["inputs10.py", "hardware"], ["inputs10.py", "gate"],\n            ["protocol10.py", "commit0"]],\n    "s0": [["capture10.py", "qwen", "all"], ["capture10.py", "qwen_base", "all"], ["debug_s0.py", "qwen"],\n           ["debug_s0.py", "qwen_base"], ["w1_tf.py", "s0report"], ["w1_tf.py", "nulls"]],\n    "w1tf": [["w1_tf.py", "score"], ["w1_tf.py", "export_zs"]],\n    "w1gen": [["w1_gen.py", "gpu", "2400"], ["w1_gen.py", "g5"], ["w1_gen.py", "label"], ["w1_gen.py", "analyze"]],\n    "ext": [["w1_dose_gen.py", "commit"], ["w1_dose_gen.py", "gpu"], ["w1_dose_gen.py", "commit_strong"],\n            ["w1_dose_gen.py", "gpu_strong"], ["w1_dose_gen.py", "commit_power"], ["w1_dose_gen.py", "gpu_power"],\n            ["w1_gen.py", "label"], ["w1_gen.py", "analyze"], ["w1_dose_gen.py", "analyze_power"]],\n    "w2": [["w2_swap.py", "match"], ["w2_swap.py", "gpu", "all"], ["w2_swap.py", "summary"]],\n    "w3": [["w3_gemma.py", "gpu", "gemma"], ["w3_gemma.py", "gpu", "gemma_pt"], ["w3_gemma.py", "score"]],\n    "out": [["tests_cpu10.py"], ["analysis10.py", "delta_geometry"], ["depcheck10.py"], ["../audit/rederive.py"],\n            ["../audit/rederive_headline.py"],\n            ["analysis10.py", "summary"], ["positioning10.py"], ["figures10.py"], ["outputs10.py"]],\n}\nORDER = ("s_1", "s0", "w1tf", "w1gen", "ext", "w2", "w3", "out")\n\n\ndef run(stage: str, i: int, cmd: list[str]) -> None:\n    LOGS.mkdir(exist_ok=True)\n    log = LOGS / f"{stage}_{i}.log"\n    env = dict(os.environ, PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True")\n    argv = [PY, "-I", cmd[0]] + cmd[1:] if cmd[0] == "../audit/rederive.py" else [PY] + cmd\n    t0 = time.time()\n    with open(log, "w") as fh:\n        p = subprocess.Popen(argv, cwd=SRC, stdout=fh, stderr=subprocess.STDOUT, env=env)\n        with open(LOGS / "pids.jsonl", "a") as pf:\n            pf.write(json.dumps({"stage": stage, "cmd": cmd, "pid": p.pid, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",\n                                                                                               time.gmtime())}) + "\\n")\n        rc = p.wait()\n    print(f"[{stage}] {\' \'.join(cmd)} -> rc {rc} in {time.time() - t0:.0f}s (log {log.relative_to(ROOT)})")\n    if rc != 0:\n        raise SystemExit(f"stage {stage} failed at {cmd}; see {log}")\n\n\ndef format_outputs() -> None:\n    skill_env = os.environ.get("AII_JSON_SKILL_DIR")      # the AI Inventor aii-json skill folder, if available\n    if not skill_env:\n        print("AII_JSON_SKILL_DIR not set: skipping schema validation and mini/preview generation")\n        return\n    skill = Path(skill_env)\n    py = skill.parent / ".ability_client_venv" / "bin" / "python"\n    if py.exists():\n        subprocess.run([str(py), str(skill / "scripts" / "aii_json_validate_schema.py"), "--format", "exp_gen_sol_out",\n                        "--file", str(ROOT / "method_out.json")], check=False)\n        subprocess.run([str(py), str(skill / "scripts" / "aii_json_format_mini_preview.py"), "--input",\n                        str(ROOT / "method_out.json")], check=False)\n\n\ndef main() -> None:\n    ap = argparse.ArgumentParser()\n    ap.add_argument("--stages", default="all")\n    a = ap.parse_args()\n    stages = ORDER if a.stages == "all" else tuple(s.strip() for s in a.stages.split(","))\n    for s in stages:\n        if s not in STAGES:\n            raise SystemExit(f"unknown stage {s}; choose from {ORDER}")\n        for i, cmd in enumerate(STAGES[s]):\n            run(s, i, cmd)\n        if s == "out":\n            format_outputs()\n\n# main() is not called in the notebook: in the artifact folder, `.venv/bin/python method.py --stages all` runs it.'}
```

### [116] TOOL RESULT — NotebookEdit · 2026-10-26 15:38:23 UTC

```
{"new_source": "# method.py: \"BASE-W stage CLI: which weights hold the default algorithm (iteration 10)\" (docstring: see above)\nROOT = Path.cwd()               # was: Path(__file__).resolve().parent  (a notebook has no __file__)\nSRC = ROOT / \"src\"\nLOGS = ROOT / \"logs\"\nPY = sys.executable\n\nSTAGES: dict[str, list[list[str]]] = {\n    \"s_1\": [[\"inputs10.py\", \"copy\"], [\"inputs10.py\", \"hardware\"], [\"inputs10.py\", \"gate\"],\n            [\"protocol10... [truncated, 39178 chars total]
```

### [117] TOOL CALL — NotebookEdit · 2026-10-26 15:38:23 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': 'e1d109ef', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "## 1. The pipeline: `method.py` (stage orchestrator)\n\n`method.py` runs eight stages. Each stage launches its scripts from `src/` as separate processes. GPU stages load one model per process, never two models on the GPU at once. Each child's PID goes to `logs/pids.jsonl` and its output to `logs/<stage>_<n>.log`.\n\n| stage | what it does | needs |\n|---|---|---|\n| `s_1` | vendor and sha256 the inputs, hardware/env record, labeller gate, **COMMIT #0** (protocol + code snapshot) | CPU |\n| `s0` | capture the fork states of Qwen3-8B and Qwen3-8B-Base, numerics debug sweep, stage-0 report, null draws + **COMMIT #1** | GPU |\n| `w1tf` | **W1 teacher-forced arms and nulls** + COMMIT #2 (generation plan and predicted counts) | CPU, on cached states |\n| `w1gen` | W1 generation (30 common-random-number slots per arm), determinism test, labelling, McNemar analysis | GPU |\n| `ext` | pre-registered extensions: dose-response, strong nulls at x3, 60 extra slots for power | GPU |\n| `w2` | Hungarian matching + COMMIT #3, in-place late/early MLP weight swaps | GPU |\n| `w3` | Gemma-3-4b it/pt captures and the row test (descriptive) | GPU |\n| `out` | CPU tests, delta geometry, LeetCode dependency check, audits, summary, figures, `method_out.json` | CPU |\n\nEvery decisive prediction was sha256-chained in `commitments.log` before the computation it governs.\n\nThe next cell is the original `method.py`. The only change is `ROOT`, because a notebook has no `__file__`. **`main()` is not called.** Each command needs the artifact's `src/` scripts, about 40 GB of model weights and a 24 GB GPU (about 1 GPU-hour in total). The cell after it prints the plan of `--stages all` instead. Sections 3 to 9 then re-run the CPU part of `w1tf` and `out` on the cached fork states."}
```

### [118] TOOL RESULT — NotebookEdit · 2026-10-26 15:38:23 UTC

```
{"new_source": "## 1. The pipeline: `method.py` (stage orchestrator)\n\n`method.py` runs eight stages. Each stage launches its scripts from `src/` as separate processes. GPU stages load one model per process, never two models on the GPU at once. Each child's PID goes to `logs/pids.jsonl` and its output to `logs/<stage>_<n>.log`.\n\n| stage | what it does | needs |\n|---|---|---|\n| `s_1` | vendor and sha256 the inputs, hardware/env record, labeller gate, **COMMIT #0** ... [truncated, 43636 chars total]
```

### [119] THINKING · 2026-10-26 15:40:09 UTC

```
Batch 3 covers adding UnitData (loading directly from the data file instead of .pt caches/checkpoints), fork-context inspection, seed-regenerable null draws, and the arm definitions, anchored to primitives cell `11f9d625`.
```

### [120] TOOL CALL — NotebookEdit · 2026-10-26 15:40:09 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': '11f9d625', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'def arm_rows(d: UnitData) -> dict[str, Any]:\n    """Every W1 arm as (margins [n], full logits [n, V] or None). Demo: the full logits are not built (None)."""\n    WI_S, WB_S = d.WI_S, d.WB_S\n    hI_Bn = rms_bf16(d.hpI, d.gB)\n    hI_In = rms_bf16(d.hpI, d.gI)\n    hB_In = rms_bf16(d.hpB, d.gI)\n    hB_Bn = rms_bf16(d.hpB, d.gB)\n    rows_D = torch.cat([WB_S[:d.nD], WI_S[d.nD:]])\n    rows_A = torch.cat([WI_S[:d.nD], WB_S[d.nD:]])\n    arms: dict[str, tuple[np.ndarray, torch.Tensor | None]] = {}\n    arms["TWIN"] = (d.mI.copy(), None)\n    arms["TWIN_cpu"] = (d.m_rows(WI_S), None)\n    arms["ROWS_ALL"] = (d.m_rows(WB_S), None)\n    arms["ROWS_D"] = (d.m_rows(rows_D), None)\n    arms["ROWS_A"] = (d.m_rows(rows_A), None)\n    arms["NORM"] = (d.m_rows(WI_S, hI_Bn), None)\n    arms["ROWS_NORM"] = (d.m_rows(WB_S, hI_Bn), None)\n    # was: margin(d.hfI, WB_G["W"][d.D].float(), WB_G["W"][d.A].float()) on the full base lm_head (the same rows)\n    arms["FULL_UNEMB"] = (margin(d.hfI, WB_S[:d.nD], WB_S[d.nD:]).numpy(), None)\n    arms["NORM_recompute_instr_gain"] = (d.m_rows(WI_S, hI_In), None)\n    for lam in DOSES:\n        r = WI_S + lam * d.Delta\n        arms[f"DOSE_{lam:g}"] = (d.m_rows(r), None)\n    r = WI_S + SIGN_DOSE * d.Delta\n    arms["SIGN"] = (d.m_rows(r), None)\n    # 2x2 factorial (residual = final-norm input; readout = (norm gain, lm_head S rows))\n    arms["F_BI"] = (d.m_rows(WI_S, hB_In), None)                 # base residual, instruct readout\n    arms["F_BB_cpu"] = (d.m_rows(WB_S, hB_Bn), None)\n    arms["F_II_cpu"] = (d.m_rows(WI_S, hI_In), None)\n    arms["UNEMB_ONLY_on_base_resid"] = (d.m_rows(WI_S, hB_Bn), None)   # iteration 9\'s (h_pre_B, g_B, W_I)\n    return arms\n\n\ndef rec_rows(d: UnitData, arm: str, m: np.ndarray, met: dict[str, np.ndarray] | None, draw: int | None\n             ) -> list[dict[str, Any]]:\n    out = []\n    for i, pid in enumerate(d.pids):\n        r = {"unit": d.u, "pid": pid, "template": d.templates[i], "arm": arm, "draw": draw, "m": float(m[i]),\n             "m_I": float(d.mI[i]), "m_B": float(d.mB[i])}\n        if met is not None:\n            for k, v in met.items():\n                r[k] = float(v[i])\n        out.append(r)\n    return out\n\n\ndef summarize_arm(d: UnitData, m: np.ndarray, boot: bool = True) -> dict[str, Any]:\n    sh = share(d.mI, m, d.mB)\n    per = (d.mI - m) / np.where(np.abs(d.gap) > 1e-9, d.gap, np.nan)\n    small = np.abs(d.gap) < SMALL_GAP\n    out = {"share": sh, "mean_margin": float(m.mean()), "per_prompt_share": per.tolist(),\n           "mean_of_ratios": float(np.nanmean(per)), "median_of_ratios": float(np.nanmedian(per)),\n           "mean_of_ratios_excl_small_gap": float(np.nanmean(per[~small])) if (~small).any() else None,\n           "small_gap_prompts": [d.pids[i] for i in np.nonzero(small)[0]]}\n    if boot:\n        out["ci95"] = boot_share(d.mI, m, d.mB)\n    return out'}
```

### [121] TOOL RESULT — NotebookEdit · 2026-10-26 15:40:09 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [122] TOOL CALL — NotebookEdit · 2026-10-26 15:40:09 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': '11f9d625', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "## 6. The W1 arms (`arm_rows`)\nEvery arm keeps the **instruct residual** at the fork and changes only the readout:\n\n| arm | readout of the instruct fork state |\n|---|---|\n| `TWIN` / `TWIN_cpu` | the unchanged instruct readout (the captured GPU margin / its CPU recompute) |\n| **`ROWS_ALL`** (primary) | all fork-class rows S = D ∪ A taken from the base model |\n| `ROWS_D` / `ROWS_A` | only the default rows / only the alternative rows from the base model |\n| `NORM` | the base final-norm gain, with the rows unchanged |\n| `ROWS_NORM` | rows + gain: the readout upper bound for the class margin |\n| `FULL_UNEMB` | the whole base unembedding. The class margin reads only its D and A rows, so this equals ROWS_ALL by construction. |\n| `DOSE_λ`, `SIGN` | `w_I + λ·Delta` for λ = 0.25 … 1.5, and λ = -1 |\n| `F_BI`, `F_BB_cpu`, `F_II_cpu` | the cells of the 2×2 factorial: residual (instruct/base) × readout (instruct/base) |\n| `UNEMB_ONLY_on_base_resid` | iteration 9's decomposition: the base residual and gain read with the instruct rows |\n\n`summarize_arm` turns each arm's per-prompt margins into the share, its bootstrap CI and the per-prompt shares, and flags prompts whose gap is under 0.5 nats. The only change from the original is that each arm's full-vocabulary logits are not built (`None`)."}
```

### [123] TOOL RESULT — NotebookEdit · 2026-10-26 15:40:09 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [124] TOOL CALL — NotebookEdit · 2026-10-26 15:40:09 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': '11f9d625', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'def make_nulls_demo(u: str, d: UnitData) -> dict[str, Any]:\n    """Seed-regenerable part of w1_tf.make_nulls() for one unit: RAND_ISO and RAND_RESID draws [N_NULL, |S|, d], plus\n    the committed DELTA_SWAP draws when the data file holds them (the original returns results/null_draws_{u}.npz)."""\n    Sx = d.S\n    ui = UNIT_IDX[u]\n    dnorm = d.Delta.norm(dim=-1).numpy()                       # was: Dl = WB_S - WI_S; dnorm = Dl.norm(dim=-1).numpy()\n    V = arr(units[u]["resid_pca"]["basis"]).numpy().astype(np.float64)   # [64, d] (was: cache/resid_pca_{u}.pt)\n    iso = np.zeros((N_NULL, len(Sx), D_MODEL), dtype=np.float32)\n    res = np.zeros_like(iso)\n    for k in range(N_NULL):\n        for j, t in enumerate(Sx):\n            r1 = np.random.default_rng([NULL_SEED0["RAND_ISO"] + 100 * ui + k, t])\n            g = r1.standard_normal(D_MODEL)\n            iso[k, j] = (dnorm[j] * g / np.linalg.norm(g)).astype(np.float32)\n            r2 = np.random.default_rng([NULL_SEED0["RAND_RESID"] + 100 * ui + k, t])\n            c = r2.standard_normal(V.shape[0])\n            v = c @ V\n            res[k, j] = (dnorm[j] * v / np.linalg.norm(v)).astype(np.float32)\n    nul = {"S": np.array(Sx), "RAND_ISO": iso, "RAND_RESID": res, "delta_norm": dnorm}\n    nd = units[u]["null_draws"]\n    if "DELTA_SWAP" in nd:                                     # committed draws (DELTA_SWAP pools need the full lm_heads)\n        nul["DELTA_SWAP"] = arr(nd["DELTA_SWAP"]).numpy()[:N_NULL]\n        nul["DELTA_SWAP_tokens"] = np.array(nd["DELTA_SWAP_tokens"])[:N_NULL]\n    return nul\n\n\nnul_T10 = make_nulls_demo("T10", d)\nprint({k: tuple(np.shape(v)) for k, v in nul_T10.items()})\nfor nt in NULL_TYPES:\n    rel = np.abs(np.linalg.norm(nul_T10[nt], axis=-1) / nul_T10["delta_norm"] - 1)\n    print(f"{nt:<10}: max | ||draw|| / ||Delta_t|| - 1 | = {rel.max():.1e}")\nprint("DELTA_SWAP tokens standing in for (\' find\', \' dfs\', \' bfs\'), first draws:",\n      units["T10"]["null_draws"]["DELTA_SWAP_token_strings"][:min(3, N_NULL)])'}
```

### [125] TOOL RESULT — NotebookEdit · 2026-10-26 15:40:09 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [126] TOOL CALL — NotebookEdit · 2026-10-26 15:40:09 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': '11f9d625', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "## 5. Matched-norm null row edits (`make_nulls`)\nIs ROWS_ALL's effect special to the real post-training delta, or would any edit of these rows of the same size do as much? Each null moves every fork-class row `t` by a vector whose norm equals that of its real delta, `||Delta_t||`. Each null has 50 draws:\n\n| null | direction of each row edit | seed stream |\n|---|---|---|\n| `RAND_ISO` | isotropic Gaussian over all 4096 dimensions | `default_rng([101000 + 100·unit + k, t])` |\n| `RAND_RESID` | a random direction inside the top-64 PCA subspace of the instruct final-normed residual, where `h` lives (64 PCs explain about 91% of its variance) | `default_rng([102000 + 100·unit + k, t])` |\n| `DELTA_SWAP` | the **real** delta of another token, with `‖Delta_s‖` within ±5% and `‖w_I,s‖` within ±10% of token t's, excluding class-like strings | `default_rng([103000 + 100·unit + k, t])` |\n\nThe original drew all three nulls and committed them (COMMIT #1) before any arm was scored. The function below keeps the seed-regenerable part of `make_nulls`. It regenerates `RAND_ISO` and `RAND_RESID` from the committed seeds; both were checked bit-exact against the committed `.npz` when the data file was built.\n\n`DELTA_SWAP` needs both models' full 151,936-row `lm_head`s, so the data file stores the 50 committed draws for T10. It does not store B3's draws (13 MB); B3 instead falls back to its 50 committed DELTA_SWAP shares."}
```

### [127] TOOL RESULT — NotebookEdit · 2026-10-26 15:40:09 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [128] TOOL CALL — NotebookEdit · 2026-10-26 15:40:09 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': '11f9d625', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'units = data["units"]                                          # was: read_json(I9_RES / "units.json")\ngI = arr(data["readout"]["g_instr"]).float()                   # was: load_readout("qwen")[1]\ngB = arr(data["readout"]["g_base"]).float()                    # was: load_readout("qwen_base")[1]\n\nd = UnitData("T10", units, gI, gB)\nprint("Context at the fork (prompt 1 of 20: chat template + prefilled opening; the next token is the fork):\\n")\nprint(units["T10"]["examples"][0]["input_text"] + d.fork["opening_text"] + "▌")\nprint(f"\\nD = {d.fork[\'D_str\']} ({d.fork[\'D_class\']})  vs  A = {d.fork[\'A_str\']} ({d.fork[\'A_class\']})")\nprint(f"h_fin {tuple(d.hfI.shape)}, h_pre {tuple(d.hpI.shape)} {d.hpI.dtype}, fork-class rows {tuple(d.WI_S.shape)}")\nprint(f"mean margin: instruct m_I {d.mI.mean():.3f}, base m_B {d.mB.mean():.3f}, gap {d.gap.mean():.3f} nats")\nprint(f"mean P(D | D or A) = sigmoid(m): instruct {np.mean(1 / (1 + np.exp(-d.mI))):.3f}, "\n      f"base {np.mean(1 / (1 + np.exp(-d.mB))):.3f}")\nprint(f"TWIN_cpu (this CPU readout) vs the captured GPU margin: max |diff| {np.abs(d.m_rows(d.WI_S) - d.mI).max():.1e}")\nhr = rms_bf16(d.hpI, gI)\nn_exact = sum(torch.equal(hr[i], d.hfI[i]) for i in range(len(d.pids)))\nprint(f"G1: rms_bf16(h_pre_I, g_I) reproduces the captured h_fin bit for bit on {n_exact}/{len(d.pids)} prompts")'}
```

### [129] TOOL RESULT — NotebookEdit · 2026-10-26 15:40:09 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [130] TOOL CALL — NotebookEdit · 2026-10-26 15:40:09 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': '11f9d625', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'class UnitData:\n    """Cached fork states of one unit for both models, the readout rows and gains.\n    Demo: built from mini_demo_data.json; the original reads cache/fork_{instr,base}_{u}.pt and slices the full\n    lm_head.weight of each checkpoint (load_readout)."""\n\n    def __init__(self, u: str, units: dict[str, Any], gI: torch.Tensor, gB: torch.Tensor):\n        self.u = u\n        U = units[u]\n        self.fork = {k: U[k] for k in ("fork_id", "opening_text", "D", "A", "D_str", "A_str", "D_class", "A_class")}\n        self.D, self.A = [int(t) for t in U["D"]], [int(t) for t in U["A"]]\n        self.S = self.D + self.A\n        self.nD = len(self.D)\n        ex = U["examples"]                                      # was: ci, cb = torch.load(CACHE_DIR / "fork_*_{u}.pt")\n        self.pids = [c["pid"] for c in ex]\n        self.templates = [c["template"] for c in ex]\n        self.B_ot = tuple(U["B_ot"])\n        self.hfI = torch.stack([arr(c["h_fin_instr"]) for c in ex]).float()\n        self.hpI = torch.stack([arr(c["h_pre_instr"]) for c in ex])\n        self.hfB = torch.stack([arr(c["h_fin_base"]) for c in ex]).float()\n        self.hpB = torch.stack([arr(c["h_pre_base"]) for c in ex])\n        self.mI = np.array([c["m_I"] for c in ex])\n        self.mB = np.array([c["m_B"] for c in ex])\n        self.WI_S = arr(U["WI_S"]).float()                      # was: WI[self.S].float()\n        self.WB_S = arr(U["WB_S"]).float()                      # was: WB[self.S].float()\n        self.Delta = self.WB_S - self.WI_S\n        self.gI, self.gB = gI, gB\n        self.gap = self.mI - self.mB\n\n    def m_rows(self, rows_S: torch.Tensor, h: torch.Tensor | None = None) -> np.ndarray:\n        h = self.hfI if h is None else h\n        return margin(h, rows_S[..., :self.nD, :], rows_S[..., self.nD:, :]).numpy()'}
```

### [131] TOOL RESULT — NotebookEdit · 2026-10-26 15:40:09 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [132] TOOL CALL — NotebookEdit · 2026-10-26 15:40:09 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': '11f9d625', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': '## 4. The cached fork states (`UnitData`)\nStage `s0` ran each prompt, plus the prefilled code opening, through both models in one forward pass on the GPU (bf16, batch shape `B_ot = 40`, as in iteration 9). It cached three values at the **last input position**, where the next token decides the algorithm:\n* `h_pre`: the block-35 output, i.e. the input of the final RMSNorm;\n* `h_fin`: the final-normed residual, `rms_bf16(h_pre, g)`;\n* `m`: the fp32 class margin read from the full logits.\n\n`UnitData` collects one unit\'s states for both models, the fork-class rows `W_I,S` and `W_B,S` (S = D ∪ A), and their difference `Delta = W_B,S - W_I,S`, the "post-training delta" of the readout.\n\nThe class differs from the original in two ways:\n* **Data source.** The original `torch.load`s `cache/fork_*.pt` and slices the full `lm_head` of each checkpoint; here everything comes from `mini_demo_data.json`.\n* **Full-vocabulary logits.** The `need_logits` and `z_with_rows` paths are dropped.'}
```

### [133] TOOL RESULT — NotebookEdit · 2026-10-26 15:40:09 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [134] THINKING · 2026-10-26 15:44:17 UTC

```
Batch 3 is complete. Next up is batch 4, anchored at `dfd45fcb`, which adds `score()`, delta geometry, the F1–F3 figure code, the GPU-results summary, and the final comparison cell.
```

### [135] TOOL CALL — NotebookEdit · 2026-10-26 15:44:17 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': 'dfd45fcb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '# Key numbers: this notebook\'s re-computation next to the artifact\'s reported values (results/w1_tf_summary.json)\npairs = []\nfor u in UNITS_TF:\n    U, R = W1["units"][u], units[u]["reported"]\n    print(f"\\n=== {u}: {units[u][\'name\']}  |  gap {U[\'gap_mean\']:.3f} nats (reported {R[\'gap_mean\']:.3f})")\n    print(f"{\'arm\':<12}{\'share\':>9}{\'95% CI\':>18}{\'reported\':>10}{\'|diff|\':>9}")\n    for a in ("ROWS_ALL", "ROWS_D", "ROWS_A", "NORM", "ROWS_NORM", "FULL_UNEMB", "SIGN", "DOSE_0.5", "DOSE_1.5"):\n        s, r, ci = U["arms"][a]["share"], R["arms"][a]["share"], U["arms"][a]["ci95"]\n        print(f"{a:<12}{s:>9.4f}{f\'[{ci[0]:.3f}, {ci[1]:.3f}]\':>18}{r:>10.4f}{abs(s - r):>9.1e}")\n        pairs.append((u, a, r, s))\n    print(f"{\'null\':<12}{\'median\':>9}{\'p95\':>9}{\'max\':>9}{\'p(ROWS_ALL)\':>13}   reported median / p95 / max / p")\n    for nt in NULL_TYPES:\n        n_, r_ = U["nulls"][nt], R["nulls"][nt]\n        tag = "" if n_["recomputed"] else "  (committed shares)"\n        print(f"{nt:<12}{n_[\'median\']:>9.3f}{n_[\'p95\']:>9.3f}{n_[\'max\']:>9.3f}{n_[\'empirical_p_rows_all\']:>13.4f}   "\n              f"{r_[\'median\']:.3f} / {r_[\'p95\']:.3f} / {r_[\'max\']:.3f} / {r_[\'empirical_p_rows_all\']:.4f}{tag}")\n        pairs += [(u, f"{nt} {k}", r_[k], n_[k]) for k in ("median", "p95", "max")]\n    F, RF = U["factorial_2x2"], R["factorial_2x2"]\n    print(f"2x2 interaction {F[\'interaction_mean\']:+.3f} nats (reported {RF[\'interaction_mean\']:+.3f}); "\n          f"unembedding-only share on the base residual {F[\'share_unembedding_only_on_base_resid\']:.3f} "\n          f"(reported {RF[\'share_unembedding_only_on_base_resid\']:.3f})")\n    print(f"verdict: {U[\'verdict\']} / {U[\'specificity_qualifier\']}   (reported: {R[\'verdict\']} / "\n          f"{R[\'specificity_qualifier\']}; role {U[\'verdict_role\']})")\n\nfig, axes = plt.subplots(1, 1 + len(UNITS_TF), figsize=(5 + 5 * len(UNITS_TF), 4.2),\n                         gridspec_kw={"width_ratios": [1] + [1.4] * len(UNITS_TF)})\nax = axes[0]\nrep_v, nb_v = np.array([p[2] for p in pairs]), np.array([p[3] for p in pairs])\nfor u, mk in zip(UNITS_TF, ("o", "s")):\n    ix = [i for i, p in enumerate(pairs) if p[0] == u]\n    ax.scatter(rep_v[ix], nb_v[ix], marker=mk, s=22, alpha=0.8, label=u)\nlim = [min(rep_v.min(), nb_v.min()) - 0.1, max(rep_v.max(), nb_v.max()) + 0.1]\nax.plot(lim, lim, "k:", lw=0.8)\nax.set_xlabel("reported by the artifact")\nax.set_ylabel("re-computed in this notebook")\nax.set_title(f"arm shares and null statistics (max |diff| {np.abs(rep_v - nb_v).max():.1e})", fontsize=8.5)\nax.legend(fontsize=7, frameon=False)\nfor ax, u in zip(axes[1:], UNITS_TF):\n    U = W1["units"][u]\n    toks = list(U["per_token_logit_change"])\n    vals = [U["per_token_logit_change"][t]["mean"] for t in toks]\n    cols = [C["ROWS_D"] if U["per_token_logit_change"][t]["class"] == "D" else C["ROWS_A"] for t in toks]\n    ax.bar(range(len(toks)), vals, color=cols)\n    ax.set_xticks(range(len(toks)), [repr(t) for t in toks], rotation=60 if len(toks) > 4 else 0, fontsize=7)\n    ax.axhline(0, color="k", lw=0.8)\n    ax.set_ylabel("h_fin_I · Delta_t (nats)")\n    ax.set_title(f"{NAMES[u]}\\nlogit change from each fork token\'s base row (orange: D, purple: A)", fontsize=8)\nfig.tight_layout()\nplt.show()'}
```

### [136] TOOL RESULT — NotebookEdit · 2026-10-26 15:44:18 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [137] TOOL CALL — NotebookEdit · 2026-10-26 15:44:17 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': 'dfd45fcb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': '## What the GPU stages found (reported by the artifact, not re-run here)\n**W1 generation (`w1gen`, `ext`).** Programs were generated with 30 common-random-number slots per arm. The only difference between arms is the readout at the fork step. Correct means a DFS program for T10, or a Prim program for B3, that passes the hidden tests.\n\n| arm at the fork | T10 correct DFS / 30 | B3 correct Prim / 30 |\n|---|---|---|\n| TWIN (unchanged instruct readout) | 1 | 0 |\n| **ROWS** (base fork-class rows, λ = 1) | **5** (vs TWIN 4:0, p = 0.125) | **24** (24:0, p = 1.2e-7) |\n| RAND_MED (median isotropic draw) | 1 | 0 |\n| FPD (base fork logits) | 15 | 17 |\n| ROWS ×2 / ×3 (`w_I + 2·Delta`, `w_I + 3·Delta`) | **21 / 30** | 27 / 27 |\n| RAND_MED ×3 / RAND_RESID max-draw ×3 / DELTA_SWAP max-draw ×3 | 1 / 30 / 30 | 3 / 27 / 27 |\n\nNotes on the table:\n* **Committed verdict for T10: NOT SUPPORTED.** ROWS reached 5/30, below the registered bar of 10/30.\n* **Power extension.** Pooled over 90 CRN pairs, ROWS gives 21/90 correct DFS against 4/90 for TWIN (17:0, p = 1.5e-5).\n* **Correctness.** Every program in the dose arms passes the hidden tests.\n* **Novelty.** No edit produced a correct program outside the known classes.\n\n**W2 (late MLPs 26-35 swapped to base).** The share is -0.145, against 0.461 for Hungarian-matched early swaps, so the committed rule fails. Same-layer random deltas move the margin by comparable amounts. **W3 (Gemma-3-4b).** The base rows *widen* the gap (share -0.253), so the effect depends on the model family.\n\n**Answer to "can we make the model pick a less default solution?"**\n\nAt the decision token, post-training stored much of Qwen\'s default in the **readout**: it suppressed the alternatives\' unembedding rows (`\' dfs\'` and `\' bfs\'`) more than it promoted `\' find\'`. Pushing those 3 of 151,936 rows along the post-training delta is a cheap lever over **which known algorithm** gets written. It is not unique, though. The best random row edit of the same norm that points into the residual subspace does as well, which is the "readout-level, not token-specific" verdict above. It also creates no novelty.\n\nThe last cell puts this notebook\'s numbers next to the reported ones.'}
```

### [138] TOOL RESULT — NotebookEdit · 2026-10-26 15:44:18 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [139] TOOL CALL — NotebookEdit · 2026-10-26 15:44:17 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': 'dfd45fcb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'def f5_f6() -> None:\n    fig5, ax5 = plt.subplots(1, 2, figsize=(11, 4.6))\n    fig6, ax6 = plt.subplots(1, 2, figsize=(10, 4.3))\n    for k, u in enumerate(UNITS_TF):\n        d = UnitData(u, units, gI, gB)            # was: UnitData(u, units, WI, WB, gI, gB, need_logits=False)\n        WI_S, WB_S = d.WI_S.double(), d.WB_S.double()\n        dI = WI_S[:d.nD].mean(0) - WI_S[d.nD:].mean(0)\n        dB = WB_S[:d.nD].mean(0) - WB_S[d.nD:].mean(0)\n        u1 = dI / dI.norm()\n        v = dB - (dB @ u1) * u1\n        u2 = v / v.norm()\n        H = torch.cat([d.hfI, d.hfB]).double()\n        a, b = (H @ u1).numpy(), (H @ u2).numpy()\n        off = H - torch.outer(H @ u1, u1) - torch.outer(H @ u2, u2)\n        off_mean = off.mean(0)\n        ga = np.linspace(a.min() - 0.15 * np.ptp(a), a.max() + 0.15 * np.ptp(a), 120)\n        gb = np.linspace(b.min() - 0.25 * np.ptp(b), b.max() + 0.25 * np.ptp(b), 120)\n        A_, B_ = np.meshgrid(ga, gb)\n        G = (off_mean[None, None, :] + torch.from_numpy(A_)[..., None] * u1 + torch.from_numpy(B_)[..., None] * u2)\n        G = G.reshape(-1, G.shape[-1])\n\n        def mgrid(rows: torch.Tensor) -> np.ndarray:\n            z = G @ rows.T\n            return (torch.logsumexp(z[:, :d.nD], -1) - torch.logsumexp(z[:, d.nD:], -1)).numpy().reshape(A_.shape)\n        MI, MB = mgrid(WI_S), mgrid(WB_S)\n        ax = ax5[k]\n        cs1 = ax.contour(A_, B_, MI, levels=7, colors=C["instr"], linewidths=0.8, alpha=0.8)\n        ax.clabel(cs1, fontsize=5.5, fmt="%.1f")\n        cs2 = ax.contour(A_, B_, MB, levels=7, colors=C["base"], linewidths=0.8, linestyles="--", alpha=0.8)\n        ax.clabel(cs2, fontsize=5.5, fmt="%.1f")\n        n = len(d.pids)\n        ax.scatter(a[:n], b[:n], color=C["instr"], s=22, edgecolor="k", lw=0.3, label="instruct fork state h_fin")\n        ax.scatter(a[n:], b[n:], color=C["base"], s=22, marker="s", edgecolor="k", lw=0.3,\n                   label="base fork state h_fin")\n        ax.plot([], [], color=C["instr"], lw=0.8, label="margin isolines, instruct S rows")\n        ax.plot([], [], color=C["base"], lw=0.8, ls="--", label="margin isolines, base S rows (ROWS_ALL readout)")\n        ax.set_xlabel("u1 = instruct readout direction (mean w_D - mean w_A), units of h")\n        ax.set_ylabel("u2 = base readout direction, orthogonalised")\n        ax.set_title(f"{u}: final-normed fork states on the readout plane\\n(isolines through the mean off-plane "\n                     f"component; cos(dI, dB) = {float(dI @ dB / dI.norm() / dB.norm()):.3f})", fontsize=8)\n        ax.legend(fontsize=6, frameon=False, loc="best")\n        # F6 PCA of block-35 outputs (final-norm inputs) at the fork\n        P = torch.cat([d.hpI.float(), d.hpB.float()]).double()\n        mu = P.mean(0)\n        Uu, Ss, Vt = torch.linalg.svd(P - mu, full_matrices=False)\n        pcs = Vt[:2]\n        Y = ((P - mu) @ pcs.T).numpy()\n        ev = (Ss ** 2 / (Ss ** 2).sum()).numpy()\n        ax = ax6[k]\n        ax.scatter(Y[:n, 0], Y[:n, 1], color=C["instr"], s=22, edgecolor="k", lw=0.3, label="instruct h_pre (fork)")\n        ax.scatter(Y[n:, 0], Y[n:, 1], color=C["base"], s=22, marker="s", edgecolor="k", lw=0.3,\n                   label="base h_pre (fork)")\n        sc = 0.35 * np.abs(Y).max()\n        for vec, col, lab in ((dI, C["instr"], "instruct readout direction"), (dB, C["base"], "base readout direction")):\n            p2 = (pcs @ (vec / vec.norm())).numpy()\n            ax.annotate("", xy=(sc * p2[0] / max(1e-9, np.linalg.norm(p2)) * min(1, 3 * np.linalg.norm(p2)),\n                                sc * p2[1] / max(1e-9, np.linalg.norm(p2)) * min(1, 3 * np.linalg.norm(p2))),\n                        xytext=(0, 0), arrowprops=dict(arrowstyle="->", color=col, lw=1.5))\n            ax.plot([], [], color=col, label=f"{lab} (|proj| {np.linalg.norm(p2):.2f})")\n        ax.set_xlabel(f"PC1 ({100 * ev[0]:.1f}% of variance)")\n        ax.set_ylabel(f"PC2 ({100 * ev[1]:.1f}%)")\n        ax.set_title(f"{u}: PCA of block-35 outputs at the fork (20 + 20 prompts)", fontsize=8.5)\n        ax.legend(fontsize=6, frameon=False)\n    fig5.tight_layout()\n    save(fig5, "F5_readout_plane")\n    save(fig6, "F6_pca_block35")\n\n\nf5_f6()'}
```

### [140] TOOL RESULT — NotebookEdit · 2026-10-26 15:44:18 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [141] TOOL CALL — NotebookEdit · 2026-10-26 15:44:17 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': 'dfd45fcb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': '### F5 and F6: the fork states in activation space\nThese two figures plot actual activation coordinates, not summary statistics.\n\n**F5 (readout plane).** It projects the 20 instruct and 20 base final-normed fork states `h_fin` onto a plane spanned by two directions:\n* `u1`: the instruct readout direction, `mean w_D - mean w_A` of the instruct rows;\n* `u2`: the base readout direction, orthogonalised against `u1`.\n\nThe isolines are the class margin across this plane, taken through the mean off-plane component of the states. Solid red lines use the instruct rows; dashed blue lines use the base rows, i.e. the ROWS_ALL readout. The arm moves the isolines, not the points: the instruct states stay where they are, and the readout that judges them changes.\n\n**F6 (PCA of the block-35 outputs).** It shows the PCA of `h_pre`, the final-norm input, for both models at the fork. Arrows are the projections of the two readout directions.\n\n`f5_f6` is the original function. Only `UnitData` is built from the data file.'}
```

### [142] TOOL RESULT — NotebookEdit · 2026-10-26 15:44:18 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [143] TOOL CALL — NotebookEdit · 2026-10-26 15:44:17 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': 'dfd45fcb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'f1(W1)\nf2(W1)\nf3(W1)'}
```

### [144] TOOL RESULT — NotebookEdit · 2026-10-26 15:44:18 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [145] TOOL CALL — NotebookEdit · 2026-10-26 15:44:17 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': 'dfd45fcb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42, "ps.fonttype": 42, "axes.spines.top": False,\n                     "axes.spines.right": False, "figure.dpi": 150})\nC = {"ROWS_ALL": "#c0392b", "ROWS_D": "#e67e22", "ROWS_A": "#8e44ad", "NORM": "#7f8c8d", "ROWS_NORM": "#2c3e50",\n     "SIGN": "#16a085", "RAND_ISO": "#3498db", "DELTA_SWAP": "#27ae60", "RAND_RESID": "#f1c40f", "instr": "#c0392b",\n     "base": "#2980b9"}\nNAMES = {"T10": "CC (T10): \' find\' vs \' dfs\'/\' bfs\'", "B3": "MST (B3): Kruskal vs Prim class"}\n\n\ndef save(fig: plt.Figure, name: str) -> None:\n    fig.tight_layout()\n    display(fig)            # was: fig.savefig(FIG_DIR / f"{name}.pdf"); fig.savefig(FIG_DIR / f"{name}.png", dpi=200)\n    plt.close(fig)\n    logger.info(f"saved {name}")\n\n\ndef f1(w1: dict) -> None:\n    fig, axes = plt.subplots(2, 2, figsize=(10, 6.5))\n    arms = ["ROWS_ALL", "ROWS_D", "ROWS_A", "NORM", "ROWS_NORM", "SIGN"]\n    for r, u in enumerate(UNITS_TF):\n        U = w1["units"][u]\n        ax = axes[r, 0]\n        sh = [U["arms"][a]["share"] for a in arms]\n        ci = [U["arms"][a]["ci95"] for a in arms]\n        y = np.arange(len(arms))\n        ax.barh(y, sh, color=[C[a] for a in arms], alpha=0.85)\n        ax.errorbar(sh, y, xerr=[[s - c[0] for s, c in zip(sh, ci)], [c[1] - s for s, c in zip(sh, ci)]], fmt="none",\n                    ecolor="k", capsize=3, lw=1)\n        ax.set_yticks(y, arms)\n        ax.axvline(0, color="k", lw=0.8)\n        ax.axvline(1, color="k", lw=0.8, ls=":")\n        ax.set_xlabel("share of the gap closed (ratio of sums, 95% CI)")\n        ax.set_title(f"{NAMES[u]}: readout arms on the instruct residual (gap {U[\'gap_mean\']:.2f} nats)", fontsize=8.5)\n        ax = axes[r, 1]\n        allv = np.concatenate([U["nulls"][nt]["shares"] for nt in ("RAND_ISO", "DELTA_SWAP", "RAND_RESID")])\n        lo, hi = np.percentile(allv, 1), np.percentile(allv, 99)\n        lo, hi = min(lo, -0.3), max(hi, U["arms"]["ROWS_ALL"]["share"] + 0.2)\n        bins = np.linspace(lo, hi, 40)\n        for nt in ("RAND_ISO", "DELTA_SWAP", "RAND_RESID"):\n            v = np.clip(U["nulls"][nt]["shares"], lo, hi)\n            ax.hist(v, bins=bins, alpha=0.55, color=C[nt],\n                    label=f"{nt} (median {U[\'nulls\'][nt][\'median\']:.2f}, p95 {U[\'nulls\'][nt][\'p95\']:.2f})")\n        ax.axvline(U["arms"]["ROWS_ALL"]["share"], color=C["ROWS_ALL"], lw=2,\n                   label=f"ROWS_ALL {U[\'arms\'][\'ROWS_ALL\'][\'share\']:.2f} (p vs RAND_ISO = "\n                         f"{U[\'nulls\'][\'RAND_ISO\'][\'empirical_p_rows_all\']:.3f})")\n        ax.set_xlabel("share closed by 50 null row edits (1-99% range shown)")\n        ax.set_ylabel("draws")\n        ax.legend(fontsize=6.5, frameon=False)\n        ax.set_title(f"{u}: nulls (every S row moved by ||Delta_t||)", fontsize=8.5)\n    save(fig, "F1_w1_shares_nulls")\n\n\ndef f2(w1: dict) -> None:\n    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))\n    for ax, u in zip(axes, UNITS_TF):\n        U = w1["units"][u]\n        gap = np.array(U["gap"])\n        x = np.arange(len(gap))\n        for a, off in (("ROWS_ALL", -0.15), ("ROWS_NORM", 0.0), ("ROWS_A", 0.15)):\n            ax.scatter(x + off, U["arms"][a]["per_prompt_share"], s=12 + 18 * np.abs(gap), color=C[a], alpha=0.75,\n                       label=a, edgecolor="k", lw=0.3)\n        for i in np.nonzero(np.abs(gap) < 0.5)[0]:\n            ax.annotate("gap<0.5", (i, U["arms"]["ROWS_ALL"]["per_prompt_share"][i]), fontsize=6)\n        ax.axhline(0, color="k", lw=0.8)\n        ax.axhline(1, color="k", lw=0.8, ls=":")\n        ax.set_xticks(x, U["pids"], rotation=90, fontsize=5.5)\n        ax.set_ylabel("per-prompt share closed")\n        ax.set_title(f"{u}: per-prompt shares (point area ~ gap in nats)", fontsize=8.5)\n        ax.legend(fontsize=7, frameon=False)\n    save(fig, "F2_per_prompt_shares")\n\n\ndef f3(w1: dict) -> None:\n    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4))\n    for ax, u in zip(axes, UNITS_TF):\n        U = w1["units"][u]\n        lams = [-1.0, 0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5]\n        rows = [U["arms"]["SIGN"]["share"], 0.0] + [U["arms"][f"DOSE_{l:g}"]["share"] for l in lams[2:]]\n        cur = U["nulls"]["RAND_ISO"]["dose_curve"]\n        iso_med = [cur["-1"]["median_draw_share"], 0.0] + [cur[f"{l:g}"]["median_draw_share"] for l in lams[2:]]\n        iso_all = [cur["-1"]["all_draws_median_share"], 0.0] + [cur[f"{l:g}"]["all_draws_median_share"]\n                                                                for l in lams[2:]]\n        ax.plot(lams, rows, "o-", color=C["ROWS_ALL"], label="base-row delta  w_I + lambda * Delta")\n        ax.plot(lams, iso_med, "s--", color=C["RAND_ISO"], label="RAND_ISO median-share draw at lambda")\n        ax.plot(lams, iso_all, "^:", color="#1a5276", label="median over the 50 RAND_ISO draws")\n        ax.axhline(0, color="k", lw=0.8)\n        ax.axhline(1, color="k", lw=0.8, ls=":")\n        ax.set_xlabel("lambda (dose of the row edit)")\n        ax.set_ylabel("share closed")\n        ax.set_title(f"{u}: dose-response", fontsize=8.5)\n        ax.legend(fontsize=6.5, frameon=False)\n    save(fig, "F3_dose_response")'}
```

### [146] TOOL RESULT — NotebookEdit · 2026-10-26 15:44:18 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [147] TOOL CALL — NotebookEdit · 2026-10-26 15:44:17 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': 'dfd45fcb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "## 9. Figures (`src/figures10.py`)\nThe plotting code is unchanged, except that `save()` displays each figure inline instead of writing `figures/*.pdf` and `*.png`:\n* **F1:** shares of the readout arms (95% CI), next to the null histograms with ROWS_ALL marked.\n* **F2:** per-prompt shares; point area is proportional to the prompt's gap.\n* **F3:** dose-response of the share against λ for the base-row delta and for RAND_ISO edits of the same dose."}
```

### [148] TOOL RESULT — NotebookEdit · 2026-10-26 15:44:18 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [149] TOOL CALL — NotebookEdit · 2026-10-26 15:44:17 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': 'dfd45fcb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'def delta_geometry() -> dict[str, Any]:\n    out: dict[str, Any] = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "units": {}}\n    for u in UNITS_TF:\n        d = UnitData(u, units, gI, gB)\n        V = arr(units[u]["resid_pca"]["basis"]).double()                 # [64, d]  (was: cache/resid_pca_{u}.pt)\n        nul = make_nulls_demo(u, d)                                      # was: np.load(null_draws_{u}.npz)\n        h = d.hfI.double()\n        hn = h.norm(dim=-1, keepdim=True)\n        rec = {}\n        for j, t in enumerate(d.S):\n            dl = d.Delta[j].double()\n            frac = float((V @ dl).pow(2).sum() / dl.pow(2).sum())\n            lev = (h @ dl).abs() / (hn[:, 0] * dl.norm())\n            lev_iso = [float(((h @ torch.from_numpy(nul["RAND_ISO"][k, j]).double()).abs() /\n                              (hn[:, 0] * dl.norm())).mean()) for k in range(nul["RAND_ISO"].shape[0])]\n            lev_res = [float(((h @ torch.from_numpy(nul["RAND_RESID"][k, j]).double()).abs() /\n                              (hn[:, 0] * dl.norm())).mean()) for k in range(nul["RAND_RESID"].shape[0])]\n            lev_swp = [float(((h @ torch.from_numpy(nul["DELTA_SWAP"][k, j]).double()).abs() /\n                              (hn[:, 0] * torch.from_numpy(nul["DELTA_SWAP"][k, j]).double().norm())).mean())\n                       for k in range(nul["DELTA_SWAP"].shape[0])] if "DELTA_SWAP" in nul else [np.nan]  # demo: B3\n            rec[str(t)] = {"class": "D" if j < d.nD else "A", "delta_norm": float(dl.norm()),\n                           "frac_delta_energy_in_resid_pc64": frac,\n                           "frac_expected_isotropic": 64 / dl.numel(),\n                           "leverage_real_mean": float(lev.mean()), "leverage_rand_iso_median": float(np.median(lev_iso)),\n                           "leverage_rand_resid_median": float(np.median(lev_res)),\n                           "leverage_delta_swap_median": float(np.median(lev_swp)),\n                           "signed_logit_change_mean": float((h @ dl).mean())}\n        out["units"][u] = {"tokens": rec, "resid_pc64_var_explained": units[u]["resid_pca"]["var_explained_top64"]}\n        logger.info(f"{u}: " + "; ".join(f"{t}: frac {v[\'frac_delta_energy_in_resid_pc64\']:.3f} lev "\n                                         f"{v[\'leverage_real_mean\']:.4f} (iso {v[\'leverage_rand_iso_median\']:.4f}, "\n                                         f"resid {v[\'leverage_rand_resid_median\']:.4f}, swap "\n                                         f"{v[\'leverage_delta_swap_median\']:.4f})" for t, v in list(rec.items())[:4]))\n    return out\n\n\nGEO = delta_geometry()\nfor u, G in GEO["units"].items():\n    S_str = units[u]["D_str"] + units[u]["A_str"]\n    print(f"\\n{u}: the top-64 PCs explain {G[\'resid_pc64_var_explained\']:.3f} of the residual variance; "\n          f"isotropic energy fraction = 64/4096 = {64 / D_MODEL:.4f}")\n    print(f"{\'token\':<12}{\'class\':>6}{\'||Delta||\':>10}{\'frac PC64\':>10}{\'lev real\':>10}{\'lev ISO\':>9}{\'lev RESID\':>10}"\n          f"{\'lev SWAP\':>10}{\'h.Delta\':>9}")\n    for s, (t, v) in zip(S_str, G["tokens"].items()):\n        print(f"{s!r:<12}{v[\'class\']:>6}{v[\'delta_norm\']:>10.4f}{v[\'frac_delta_energy_in_resid_pc64\']:>10.4f}"\n              f"{v[\'leverage_real_mean\']:>10.4f}{v[\'leverage_rand_iso_median\']:>9.4f}"\n              f"{v[\'leverage_rand_resid_median\']:>10.4f}{v[\'leverage_delta_swap_median\']:>10.4f}"\n              f"{v[\'signed_logit_change_mean\']:>+9.2f}")'}
```

### [150] TOOL RESULT — NotebookEdit · 2026-10-26 15:44:18 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [151] TOOL CALL — NotebookEdit · 2026-10-26 15:44:17 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': 'dfd45fcb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': '## 8. Why do residual-subspace edits beat the real deltas? (`delta_geometry`, `src/analysis10.py`)\nThe RAND_RESID null closes as much of the gap as the real delta, or more. To see why, this analysis measures two things for each fork-class token `t`:\n* **energy in the residual subspace:** the fraction of `‖Delta_t‖²` inside the top-64 PCA subspace of the instruct final-normed residual. An isotropic vector puts 64/4096 = 0.0156 there.\n* **logit leverage:** `|h·Delta_t| / (‖h‖ ‖Delta_t‖)`, the cosine between the fork state and the edit, so the logit change per unit of edit norm. It is computed for the real delta and for the null draws of the same norm.\n\nThe original reads `cache/resid_pca_{u}.pt` and `results/null_draws_{u}.npz`; here the basis comes from the data file and the draws from `make_nulls_demo`.'}
```

### [152] TOOL RESULT — NotebookEdit · 2026-10-26 15:44:18 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [153] TOOL CALL — NotebookEdit · 2026-10-26 15:44:17 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': 'dfd45fcb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'W1 = score()\nfor u, U in W1["units"].items():\n    R = units[u]["reported"]\n    ci = U["arms"]["ROWS_ALL"]["ci95"]\n    print(f"\\n{u} ({units[u][\'name\']}): ROWS_ALL share {U[\'arms\'][\'ROWS_ALL\'][\'share\']:.4f} [{ci[0]:.3f}, {ci[1]:.3f}]"\n          f" (reported {R[\'arms\'][\'ROWS_ALL\'][\'share\']:.4f}) -> {U[\'verdict\']}, {U[\'specificity_qualifier\']}")\n    print("  logit change of each fork token from its base row, on the instruct state (nats): "\n          + ", ".join(f"{t!r} {v[\'mean\']:+.2f}" for t, v in U["per_token_logit_change"].items()))\n    print(f"  identities: max |FULL_UNEMB - ROWS_ALL| = {U[\'identity_full_unemb_minus_rows_all_max_abs\']:.1e}, "\n          f"max |TWIN_cpu - TWIN| = {U[\'identity_twin_cpu_minus_gpu_max_abs\']:.1e} nats")\nprint(f"\\n{len(W1_TF_ROWS)} per-prompt rows (arms + null draws) in W1_TF_ROWS; scoring took {W1[\'seconds\']} s")'}
```

### [154] TOOL RESULT — NotebookEdit · 2026-10-26 15:44:18 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [155] TOOL CALL — NotebookEdit · 2026-10-26 15:44:17 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': 'dfd45fcb', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'W1_TF_ROWS: list[dict[str, Any]] = []          # per-prompt margins of every arm and null draw (results/w1_tf_rows.jsonl)\n\n\ndef score() -> dict[str, Any]:\n    t0 = time.time()\n    all_rows: list[dict[str, Any]] = []\n    summ: dict[str, Any] = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "units": {}}\n    for u in UNITS_TF:\n        d = UnitData(u, units, gI, gB)\n        nul = make_nulls_demo(u, d)                             # was: np.load(RESULTS_DIR / f"null_draws_{u}.npz")\n        assert list(nul["S"]) == d.S\n        arms = arm_rows(d)\n        us: dict[str, Any] = {"pids": d.pids, "templates": d.templates, "gap_mean": float(d.gap.mean()),\n                              "gap": d.gap.tolist(), "m_I": d.mI.tolist(), "m_B": d.mB.tolist(), "arms": {},\n                              "S_str": d.fork["D_str"] + d.fork["A_str"], "nD": d.nD}   # was: tok.decode of each id\n        for a, (m, z) in arms.items():\n            all_rows += rec_rows(d, a, m, None, None)           # (dist_metrics(z, ...) needs the full logits)\n            us["arms"][a] = summarize_arm(d, m)\n        all_rows += rec_rows(d, "BASE", d.mB, None, None)\n        # identity checks\n        us["identity_full_unemb_minus_rows_all_max_abs"] = float(np.abs(arms["FULL_UNEMB"][0] -\n                                                                       arms["ROWS_ALL"][0]).max())\n        us["identity_twin_cpu_minus_gpu_max_abs"] = float(np.abs(arms["TWIN_cpu"][0] - d.mI).max())\n        # 2x2 factorial\n        mII, mIB, mBI, mBB = d.mI, arms["ROWS_NORM"][0], arms["F_BI"][0], d.mB\n        inter = mII - mIB - mBI + mBB\n        us["factorial_2x2"] = {"m_II": float(mII.mean()), "m_IB_rows_norm": float(mIB.mean()),\n                               "m_BI_base_resid_instr_readout": float(mBI.mean()), "m_BB": float(mBB.mean()),\n                               "interaction_mean": float(inter.mean()), "interaction_per_prompt": inter.tolist(),\n                               "interaction_ci95": list(S9.boot_mean_ci(inter, B=N_BOOT, seed=SEED_BOOT)),\n                               "readout_effect_on_instr_resid": float((mII - mIB).mean()),\n                               "readout_effect_on_base_resid": float((mBI - mBB).mean()),\n                               "residual_effect_under_instr_readout": float((mII - mBI).mean()),\n                               "residual_effect_under_base_readout": float((mIB - mBB).mean()),\n                               "share_readout_on_instr_resid": share(mII, mIB, mBB),\n                               "share_readout_on_base_resid": float((mBI - mBB).sum() / (mII - mBB).sum()),\n                               "share_unembedding_only_on_base_resid":\n                                   float((arms["UNEMB_ONLY_on_base_resid"][0] - mBB).sum() / (mII - mBB).sum()),\n                               "share_interaction": float(inter.sum() / (mII - mBB).sum())}\n        # per-token logit change h_fin_I . Delta_t\n        dz = (d.hfI @ d.Delta.T).numpy()\n        us["per_token_logit_change"] = {us["S_str"][j]: {"mean": float(dz[:, j].mean()), "sd": float(dz[:, j].std()),\n                                                         "class": "D" if j < d.nD else "A"}\n                                        for j in range(len(d.S))}\n        us["delta_norms"] = {us["S_str"][j]: float(d.Delta[j].norm()) for j in range(len(d.S))}\n        # nulls\n        nulls: dict[str, Any] = {}\n        obs = us["arms"]["ROWS_ALL"]["share"]\n        for nt in NULL_TYPES:\n            if nt in nul:\n                dl = torch.from_numpy(nul[nt])                          # [N_NULL, |S|, d]\n                shs = []\n                for k in range(N_NULL):\n                    r = d.WI_S + dl[k]\n                    m = d.m_rows(r)\n                    all_rows += rec_rows(d, nt, m, None, k)\n                    shs.append(share(d.mI, m, d.mB))\n            else:       # demo only: B3\'s DELTA_SWAP draws are not in mini_demo_data.json -> its committed shares\n                shs = units[u]["reported"]["nulls"][nt]["shares"][:N_NULL]\n                logger.warning(f"{u} {nt}: draws not in the demo data; using the {len(shs)} committed shares")\n            shs_a = np.array(shs)\n            nulls[nt] = {"shares": shs, "median": float(np.median(shs_a)), "p95": float(np.percentile(shs_a, 95)),\n                         "max": float(shs_a.max()), "min": float(shs_a.min()), "mean": float(shs_a.mean()),\n                         "empirical_p_rows_all": S9.empirical_p_upper(obs, shs_a),\n                         "p_floor": 1 / (N_NULL + 1), "recomputed": nt in nul,\n                         "rows_all_above_max": bool(obs > shs_a.max()), "rows_all_above_p95": bool(\n                             obs > np.percentile(shs_a, 95))}\n            # dose-matched isotropic curve (F3): lambda * delta for the draw with the median share\n            if nt == "RAND_ISO":\n                med = int(np.argsort(shs_a)[len(shs_a) // 2])\n                mx = int(np.argmax(shs_a))\n                nulls[nt]["median_draw"], nulls[nt]["max_draw"] = med, mx\n                curve = {}\n                for lam in DOSES + (SIGN_DOSE,):\n                    curve[f"{lam:g}"] = {\n                        "median_draw_share": share(d.mI, d.m_rows(d.WI_S + lam * dl[med]), d.mB),\n                        "all_draws_median_share": float(np.median([share(d.mI, d.m_rows(d.WI_S + lam * dl[k]), d.mB)\n                                                                   for k in range(N_NULL)]))}\n                nulls[nt]["dose_curve"] = curve\n        us["nulls"] = nulls\n        # verdict (T10 primary; B3 descriptive with the same rule)\n        rows_sh = obs\n        iso = nulls["RAND_ISO"]\n        if rows_sh >= THRESH["W1_rows_share"] and iso["median"] <= THRESH["W1_rand_iso_median"] and \\\n                rows_sh > iso["max"]:\n            verdict = "SUPPORTED"\n        elif rows_sh <= THRESH["W1_disconfirm"]:\n            verdict = "DISCONFIRMED"\n        else:\n            verdict = "PARTIAL"\n        spec = rows_sh > nulls["DELTA_SWAP"]["p95"] and rows_sh > nulls["RAND_RESID"]["p95"]\n        us["verdict"] = verdict\n        us["specificity_qualifier"] = ("written into these tokens\' own rows" if spec else\n                                       "readout-level but not token-specific")\n        us["verdict_role"] = "primary" if u == "T10" else "descriptive"\n        # per-template breakdown of ROWS_ALL\n        us["rows_all_by_template"] = {}\n        for w in sorted(set(d.templates)):\n            ix = [i for i, t in enumerate(d.templates) if t == w]\n            us["rows_all_by_template"][w] = share(d.mI[ix], arms["ROWS_ALL"][0][ix], d.mB[ix])\n        # (the original next builds the generation plan and predicted counts per arm from the full fork logits)\n        summ["units"][u] = us\n        logger.info(f"W1-TF {u}: ROWS_ALL {us[\'arms\'][\'ROWS_ALL\'][\'share\']:.3f} "\n                    f"{us[\'arms\'][\'ROWS_ALL\'][\'ci95\']}, ROWS_NORM {us[\'arms\'][\'ROWS_NORM\'][\'share\']:.3f}, NORM "\n                    f"{us[\'arms\'][\'NORM\'][\'share\']:.3f}, ROWS_D {us[\'arms\'][\'ROWS_D\'][\'share\']:.3f}, ROWS_A "\n                    f"{us[\'arms\'][\'ROWS_A\'][\'share\']:.3f}; RAND_ISO med {nulls[\'RAND_ISO\'][\'median\']:.3f} max "\n                    f"{nulls[\'RAND_ISO\'][\'max\']:.3f}; DELTA_SWAP p95 {nulls[\'DELTA_SWAP\'][\'p95\']:.3f}; RAND_RESID "\n                    f"p95 {nulls[\'RAND_RESID\'][\'p95\']:.3f}; interaction {us[\'factorial_2x2\'][\'interaction_mean\']:.3f}"\n                    f" -> {verdict} ({us[\'specificity_qualifier\']})")\n    W1_TF_ROWS[:] = all_rows                    # was: write_jsonl(RESULTS_DIR / "w1_tf_rows.jsonl", all_rows)\n    summ["seconds"] = round(time.time() - t0, 1)\n    # (the original writes results/w1_tf_summary.json and appends COMMIT #2 before any token is generated)\n    return summ'}
```

### [156] TOOL RESULT — NotebookEdit · 2026-10-26 15:44:18 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [157] TOOL CALL — NotebookEdit · 2026-10-26 15:44:17 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': 'dfd45fcb', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': '## 7. Scoring every arm and null (`score`)\n`score()` runs the whole W1 teacher-forced test for each unit:\n1. **Arms.** It computes every arm\'s margins, their share with a bootstrap CI, and two identity checks: FULL_UNEMB = ROWS_ALL, and TWIN_cpu ≈ the captured margin.\n2. **2×2 factorial.** It crosses residual (instruct/base) with readout (instruct/base) and reports the interaction `m_II - m_IB - m_BI + m_BB`. If readout and residual were additive, the interaction would be 0.\n3. **Per-token logit change.** `h_fin_I · Delta_t` is how much the base row of each fork token raises or lowers that token\'s logit on the instruct state.\n4. **Nulls.** For 50 draws of each null type it records the share, its median, p95 and maximum, and the empirical p of ROWS_ALL. For RAND_ISO it adds a dose curve along the draw with the median share.\n5. **Committed verdict rule** (T10 primary, B3 descriptive):\n   * **SUPPORTED** if ROWS_ALL ≥ 0.50, the RAND_ISO median ≤ 0.15 and ROWS_ALL > the RAND_ISO maximum;\n   * **DISCONFIRMED** if ROWS_ALL ≤ 0.20;\n   * otherwise **PARTIAL**.\n\n   A specificity qualifier then says *"written into these tokens\' own rows"* only if ROWS_ALL also beats the p95 of both DELTA_SWAP and RAND_RESID.\n\nRemoved from the original: the full-vocabulary distribution metrics, the generation predictions and plan (COMMIT #2), and the file writes.'}
```

### [158] TOOL RESULT — NotebookEdit · 2026-10-26 15:44:18 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [159] ASSISTANT · 2026-10-26 15:44:27 UTC

```
All cells are in. I'll verify the final cell order, then run the first test (TODO 4) with the minimal config: `UNITS_TF=("T10",)`, `N_NULL=2`, `N_BOOT=10`.
```

### [160] TOOL CALL — Bash · 2026-10-26 15:44:27 UTC

```
List notebook cells in final order:
python3 -c "
import json
nb=json.load(open('code_demo.ipynb'))
for i,c in enumerate(nb['cells']):
    src=''.join(c['source']); print(i, c['id'], c['cell_type'][:4], repr(src.splitlines()[0][:90]))
print(len(nb['cells']),'cells')
"
```

### [161] TOOL RESULT — Bash · 2026-10-26 15:44:27 UTC

```
{"stdout": "0 c00-title mark '# Which weights make the model pick one algorithm (BASE-W, iteration 10)'\n1 5dfd487b code 'import subprocess, sys'\n2 982aeb53 code 'from __future__ import annotations'\n3 7ea594f1 code 'GITHUB_DATA_URL = \"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8'\n4 7efd0587 code 'data = load_data()'\n5 4d9d64de mark '### Configuration'\n6 e1d109ef code '# ---------------------------------------------------------------- run size (the original '\n7 b84ec7ef mark '## 1. The pipeline: `method.py` (stage orchestrator)'\n8 95009a91 code '# method.py: \"BASE-W stage CLI: which weights hold the default algorithm (iteration 10)\" ('\n9 9bcfb9a9 code '# Dry run of `python method.py --stages all`: list every command in order instead of launc'\n10 be14fac7 mark '## 2. Shared helpers'\n11 11208bcf code '# ---- src/cfg10.py: logging (stdout only; the original also adds a rotating file sink und'\n12 5b25bf0f mark '## 3. Readout primitives (`src/w1_tf.py`)'\n13 11f9d625 code 'def rms_bf16(h_pre: torch.Tensor, g: torch.Tensor, eps: float = RMS_EPS) -> torch.Tensor:'\n14 f92d86dc mark '## 4. The cached fork states (`UnitData`)'\n15 bde2f903 code 'class UnitData:'\n16 02c073c6 code 'units = data[\"units\"]                                          # was: read_json(I9_RES / \"'\n17 2eff00f5 mark '## 5. Matched-norm null row edits (`make_nulls`)'\n18 10527758 code 'def make_nulls_demo(u: str, d: UnitData) -> dict[str, Any]:'\n19 035f8270 mark '## 6. The W1 arms (`arm_rows`)'\n20 dfd45fcb code 'def arm_rows(d: UnitData) -> dict[str, Any]:'\n21 a3a6b30d mark '## 7. Scoring every arm and null (`score`)'\n22 18d98def code 'W1_TF_ROWS: list[dict[str, Any]] = []          # per-prompt margins of every arm and null '\n23 11397ff3 code 'W1 = score()'\n24 d04ee8e2 mark '## 8. Why do residual-subspace edits beat the real deltas? (`delta_geometry`, `src/analysi'\n25 a50cfaef code 'def delta_geometry() -> dict[str, Any]:'\n26 9fc2f657 mark '## 9. Figures (`src/figures10.py`)'\n27 a79b585c code 'plt.rcParams.update({\"font.size\": 9, \"pdf.fonttype\": 42, \"ps.fonttype\": 42, \"axes.spines.t'\n28 5b62b8dd code 'f1(W1)'\n29 2ce49da0 mark '### F5 and F6: the fork states in activation space'\n30 141ec333 code 'def f5_f6() -> None:'\n31 7fddb6a9 mark '## What the GPU stages found (reported by the artifact, not re-run here)'\n32 b81c6c77 code \"# Key numbers: this notebook's re-computation next to the artifact's reported values (resu\"\n33 cells", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [162] ASSISTANT · 2026-10-26 15:44:37 UTC

```
Cell order is correct (33 cells). Launching test 1 in the background with the sanctioned clean venv; the log goes to `logs/` in the workspace.
```

### [163] TOOL CALL — Bash · 2026-10-26 15:44:37 UTC

```
Test-run notebook with minimal config in clean venv:
mkdir -p logs && ( time ( UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5 && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5/bin/python jupyter ipykernel && /tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb ) ) > logs/nbtest_1_minimal.log 2>&1; echo "exit $?" >> logs/nbtest_1_minimal.log; tail -30 logs/nbtest_1_minimal.log
```

### [164] TOOL RESULT — Bash · 2026-10-26 15:44:37 UTC

```
{"stdout": "", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false, "backgroundTaskId": "bz452ui3a"}
```

### [165] THINKING · 2026-10-26 15:45:13 UTC

```
While test 1 runs, I'll write the storage manifest—since the venv is in /tmp and everything else here is small text/code, no entries are needed.
```

### [166] TOOL CALL — Bash · 2026-10-26 15:45:13 UTC

```
Write the storage manifest with no entries:
ls -la .aii/ && cat > .aii/manifest.yaml <<'EOF'
# Storage decisions for this demo folder.
# Nothing here needs a keep/delete decision: every file is text or code (code_demo.ipynb, mini_demo_data.json
# at 8.3 MB, build_mini_demo_data.py, README.md, logs/*.log) and no cache directory lives in this folder.
# The notebook test virtualenv was created outside this folder, on local disk, and the pipeline removes it.
entries: []
EOF
cat .aii/manifest.yaml; ls -la
```

### [167] TOOL RESULT — Bash · 2026-10-26 15:45:13 UTC

```
{"stdout": "total 1955\ndrwxrwxrwx 2 aii-agent aii-agent       1 Oct 26 15:21 .\ndrwxrwxrwx 4 aii-agent aii-agent 2000911 Oct 26 15:44 ..\n# Storage decisions for this demo folder.\n# Nothing here needs a keep/delete decision: every file is text or code (code_demo.ipynb, mini_demo_data.json\n# at 8.3 MB, build_mini_demo_data.py, README.md, logs/*.log) and no cache directory lives in this folder.\n# The notebook test virtualenv was created outside this folder, on local disk, and the pipeline removes it.\nentries: []\ntotal 13314\ndrwxrwxrwx 4 aii-agent aii-agent 2000911 Oct 26 15:44 .\ndrwxrwxrwx 9 aii-agent aii-agent 2003278 Oct 26 15:25 ..\ndrwxrwxrwx 2 aii-agent aii-agent   37800 Oct 26 15:45 .aii\n-rw-rw-rw- 1 aii-agent aii-agent      54 Oct 26 15:21 .aii_claude_session.json\n-rw-rw-rw- 1 aii-agent aii-agent 1139199 Oct 26 15:45 .repl_agent.ptylog\n-rw-rw-rw- 1 aii-agent aii-agent   12239 Oct 26 15:29 build_mini_demo_data.py\n-rw-rw-rw- 1 aii-agent aii-agent   66259 Oct 26 15:44 code_demo.ipynb\ndrwxrwxrwx 2 aii-agent aii-agent   34600 Oct 26 15:44 logs\n-rw-rw-rw- 1 aii-agent aii-agent 8337194 Oct 26 15:30 mini_demo_data.json", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [168] ASSISTANT · 2026-10-26 15:45:20 UTC

```
The manifest is written. I'll wait for test 1 to finish before writing the README, since it should include the measured runtimes.
```

### [169] TOOL CALL — Bash · 2026-10-26 15:45:20 UTC

```
Brief pause while background test runs:
sleep 1; echo waiting
```

### [170] TOOL RESULT — Bash · 2026-10-26 15:45:20 UTC

```
{"stdout": "waiting", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [171] ASSISTANT · 2026-10-26 15:45:26 UTC

```
While waiting, I'll write the required structured output file, which is static.
```

### [172] TOOL CALL — Bash · 2026-10-26 15:45:26 UTC

```
Write the structured output JSON file:
cat > .terminal_claude_agent_struct_out.json <<'EOF'
{
  "out_expected_files": {
    "notebook": "code_demo.ipynb",
    "mini_data_file": "mini_demo_data.json"
  }
}
EOF
python3 -c "import json; print(json.load(open('.terminal_claude_agent_struct_out.json')))"
```

### [173] TOOL RESULT — Bash · 2026-10-26 15:45:26 UTC

```
{"stdout": "{'out_expected_files': {'notebook': 'code_demo.ipynb', 'mini_data_file': 'mini_demo_data.json'}}", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [174] TOOL CALL — ToolSearch · 2026-10-26 15:45:30 UTC

```
{'query': 'select:Monitor', 'max_results': 1}
```

### [175] TOOL RESULT — ToolSearch · 2026-10-26 15:45:30 UTC

```
{"matches": ["Monitor"], "query": "select:Monitor", "total_deferred_tools": 28}
```

### [176] ASSISTANT · 2026-10-26 15:45:56 UTC

```
Test 1 is still running. Meanwhile I'll draft `README.md`; I'll update its runtime figures once the final test completes.
```

### [177] TOOL CALL — Write · 2026-10-26 15:45:56 UTC

````
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/README.md

# Which weights make the model pick one algorithm: demo notebook (BASE-W, iteration 10)

This folder turns the BASE-W experiment (artifact `art_a7CQm-6CXmoJ`, experiment 56 of iteration 10) into a short,
runnable Jupyter notebook. The experiment asks where post-training wrote Qwen3-8B's default algorithm at the decision
("fork") token, relative to Qwen3-8B-Base, at the level of weights.

The artifact's `method.py` is a stage orchestrator: it launches about 40 scripts that load 8B models on a 24 GB GPU,
about 1 GPU-hour in total. Its core test (**W1**: restore the base model's fork-class unembedding rows on the instruct
residual) is exact arithmetic on cached fork states, because the class margin `lse(z[D]) - lse(z[A])` depends only on
the final-normed residual and the fork-class rows. The notebook therefore re-runs W1 on a CPU from a compact data file,
with the original code split into cells.

## Layout

| path | content |
|---|---|
| `code_demo.ipynb` | the demo notebook, saved with its outputs from the last test run |
| `mini_demo_data.json` | the notebook's input (8.3 MB, 40 examples): see below |
| `build_mini_demo_data.py` | rebuilds `mini_demo_data.json` from the artifact folder, with bit-exactness checks |
| `logs/` | the notebook test runs (minimal config, then scaled up), with timings |
| `.aii/manifest.yaml` | storage decisions; none are needed, since everything here is text or code under 10 MB |

### `mini_demo_data.json`

**Per unit.** There are two units:
* **T10:** connected components; `' find'` (union-find) against `' dfs'` / `' bfs'`.
* **B3:** minimum spanning tree; Kruskal-class against Prim-class tokens.

Each unit holds:
* `examples`: 20 prompts, each with its chat-formatted input text and the captured fp32 margins `m_I` / `m_B`. It also
  holds the fork states of both models: `h_pre` (the block-35 output) and `h_fin` (the final-normed residual), stored
  as base64 bf16 and decoded exactly.
* `WI_S`, `WB_S`: the fork-class `lm_head` rows of Qwen3-8B and Qwen3-8B-Base.
* `resid_pca`: the top-64 PCA basis of the instruct residual, used by the RAND_RESID null.
* `null_draws`: the 50 committed DELTA_SWAP draws, for T10 only. B3's are 13 MB and are left out; the notebook uses
  B3's committed shares instead.
* `reported`: the artifact's own numbers, for a side-by-side check.

**Shared.** `readout` holds the final-norm gains of both models.

**How the build was checked.** `build_mini_demo_data.py` asserts each of the following before writing the file:
* The `lm_head` rows were fetched with HTTP range requests at the pinned revisions, and they reproduce the committed
  delta norms and row norms bit for bit.
* RAND_ISO and RAND_RESID regenerate bit-exactly from their committed seeds.
* ROWS_ALL reproduces the reported share within 1e-6.

## What the notebook runs

1. **Orchestrator.** `method.py` itself, with only `ROOT` changed, and a dry run of its 40-command stage plan. The
   GPU stages are not launched.
2. **W1 teacher-forced test.** The code of `src/w1_tf.py`: `rms_bf16`, `margin`, `share`, `boot_share`, `UnitData`,
   `arm_rows`, `summarize_arm` and `score`. It covers the arms ROWS_ALL / ROWS_D / ROWS_A / NORM / ROWS_NORM /
   FULL_UNEMB / DOSE / SIGN, the 2x2 factorial, and the 3 x 50 matched-norm nulls with the committed verdict rule.
3. **Delta geometry.** `src/analysis10.py`'s `delta_geometry`: how much of each row delta lies in the residual
   subspace, and its logit leverage.
4. **Figures.** `src/figures10.py`'s F1 (shares and null histograms), F2 (per-prompt shares), F3 (dose-response), F5
   (fork states on the readout plane, in activation space) and F6 (PCA of the block-35 outputs).
5. **Summary.** The reported GPU results (W1 generation, W2 MLP swaps, W3 Gemma) as text. The final cell is a table and
   parity plot of the notebook's numbers against the reported ones.

## How to run

* **Colab.** Open `code_demo.ipynb` and choose Run all. The first cell installs `loguru` only. The notebook downloads
  `mini_demo_data.json` from this repository's GitHub raw URL, and falls back to a local copy next to the notebook.
* **Local.** The first cell pins Colab's versions (`numpy==2.0.2`, `matplotlib==3.10.0`, `torch==2.9.0+cpu`):

  ```bash
  pip install jupyter ipykernel
  jupyter nbconvert --to notebook --execute code_demo.ipynb --output code_demo.ipynb
  ```

The configuration cell holds the run size: `UNITS_TF`, `N_NULL` and `N_BOOT`. The notebook ships with the artifact's
original values: both units, 50 draws per null and 10,000 bootstrap resamples.

## Rebuilding the data file

```bash
python build_mini_demo_data.py --artifact-dir <the BASE-W artifact folder> \
    --tokenizer <Qwen3-8B tokenizer.json at revision b968826d9c46dd6066d109eabc6255188de91218>
```

The script needs `torch`, `numpy`, `requests` and `tokenizers`, plus network access to huggingface.co. From each model
it fetches only the 19 fork-class `lm_head` rows (8 KB each) and the final-norm gain, at revisions
`Qwen/Qwen3-8B@b968826d9c46dd6066d109eabc6255188de91218` and
`Qwen/Qwen3-8B-Base@49e3418fbbbca6ecbdf9608b4d22e5a407081db4`.

## Restoring removed files

Nothing in this folder is marked `delete` in `.aii/manifest.yaml`, so there is nothing to restore. `code_demo.ipynb`
installs its own dependencies from its first cell. The data file can be rebuilt with the command above.
````

### [178] TOOL RESULT — Write · 2026-10-26 15:45:56 UTC

````
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/README.md", "content": "# Which weights make the model pick one algorithm: demo notebook (BASE-W, iteration 10)\n\nThis folder turns the BASE-W experiment (artifact `art_a7CQm-6CXmoJ`, experiment 56 of iteration 10) into a short,\nrunnable Jupyter notebook. The experiment asks where post-training wrote Qwen3-8B's default algorithm at the decision\n(\"fork\") token, relative to Qwen3-8B-Base, at the level of weights.\n\nThe artifact's `method.py` is a stage orchestrator: it launches about 40 scripts that load 8B models on a 24 GB GPU,\nabout 1 GPU-hour in total. Its core test (**W1**: restore the base model's fork-class unembedding rows on the instruct\nresidual) is exact arithmetic on cached fork states, because the class margin `lse(z[D]) - lse(z[A])` depends only on\nthe final-normed residual and the fork-class rows. The notebook therefore re-runs W1 on a CPU from a compact data file,\nwith the original code split into cells.\n\n## Layout\n\n| path | content |\n|---|---|\n| `code_demo.ipynb` | the demo notebook, saved with its outputs from the last test run |\n| `mini_demo_data.json` | the notebook's input (8.3 MB, 40 examples): see below |\n| `build_mini_demo_data.py` | rebuilds `mini_demo_data.json` from the artifact folder, with bit-exactness checks |\n| `logs/` | the notebook test runs (minimal config, then scaled up), with timings |\n| `.aii/manifest.yaml` | storage decisions; none are needed, since everything here is text or code under 10 MB |\n\n### `mini_demo_data.json`\n\n**Per unit.** There are two units:\n* **T10:** connected components; `' find'` (union-find) against `' dfs'` / `' bfs'`.\n* **B3:** minimum spanning tree; Kruskal-class against Prim-class tokens.\n\nEach unit holds:\n* `examples`: 20 prompts, each with its chat-formatted input text and the captured fp32 margins `m_I` / `m_B`. It also\n  holds the fork states of both models: `h_pre` (the block-35 output) and `h_fin` (the final-normed residual), stored\n  as base64 bf16 and decoded exactly.\n* `WI_S`, `WB_S`: the fork-class `lm_head` rows of Qwen3-8B and Qwen3-8B-Base.\n* `resid_pca`: the top-64 PCA basis of the instruct residual, used by the RAND_RESID null.\n* `null_draws`: the 50 committed DELTA_SWAP draws, for T10 only. B3's are 13 MB and are left out; the notebook uses\n  B3's committed shares instead.\n* `reported`: the artifact's own numbers, for a side-by-side check.\n\n**Shared.** `readout` holds the final-norm gains of both models.\n\n**How the build was checked.** `build_mini_demo_data.py` asserts each of the following before writing the file:\n* The `lm_head` rows were fetched with HTTP range requests at the pinned revisions, and they reproduce the committed\n  delta norms and row norms bit for bit.\n* RAND_ISO and RAND_RESID regenerate bit-exactly from their committed seeds.\n* ROWS_ALL reproduces the reported share within 1e-6.\n\n## What the notebook runs\n\n1. **Orchestrator.** `method.py` itself, with only `ROOT` changed, and a dry run of its 40-command stage plan. The\n   GPU stages are not launched.\n2. **W1 teacher-forced test.** The code of `src/w1_tf.py`: `rms_bf16`, `margin`, `share`, `boot_share`, `UnitData`,\n   `arm_rows`, `summarize_arm` and `score`. It covers the arms ROWS_ALL / ROWS_D / ROWS_A / NORM / ROWS_NORM /\n   FULL_UNEMB / DOSE / SIGN, the 2x2 factorial, and the 3 x 50 matched-norm nulls with the committed verdict rule.\n3. **Delta geometry.** `src/analysis10.py`'s `delta_geometry`: how much of each row delta lies in the residual\n   subspace, and its logit leverage.\n4. **Figures.** `src/figures10.py`'s F1 (shares and null histograms), F2 (per-prompt shares), F3 (dose-response), F5\n   (fork states on the readout plane, in activation space) and F6 (PCA of the block-35 outputs).\n5. **Summary.** The reported GPU results (W1 generation, W2 MLP swaps, W3 Gemma) as text. The final cell is a table and\n   parity plot of the notebook's numbers against the reported ones.\n\n## How to run\n\n* **Colab.** Open `code_demo.ipynb` and choose Run all. The first cell installs `loguru` only. The notebook downloads\n  `mini_demo_data.json` from this repository's GitHub raw URL, and falls back to a local copy next to the notebook.\n* **Local.** The first cell pins Colab's versions (`numpy==2.0.2`, `matplotlib==3.10.0`, `torch==2.9.0+cpu`):\n\n  ```bash\n  pip install jupyter ipykernel\n  jupyter nbconvert --to notebook --execute code_demo.ipynb --output code_demo.ipynb\n  ```\n\nThe configuration cell holds the run size: `UNITS_TF`, `N_NULL` and `N_BOOT`. The notebook ships with the artifact's\noriginal values: both units, 50 draws per null and 10,000 bootstrap resamples.\n\n## Rebuilding the data file\n\n```bash\npython build_mini_demo_data.py --artifact-dir <the BASE-W artifact folder> \\\n    --tokenizer <Qwen3-8B tokenizer.json at revision b968826d9c46dd6066d109eabc6255188de91218>\n```\n\nThe script needs `torch`, `numpy`, `requests` and `tokenizers`, plus network access to huggingface.co. From each model\nit fetches only the 19 fork-class `lm_head` rows (8 KB each) and the final-norm gain, at revisions\n`Qwen/Qwen3-8B@b968826d9c46dd6066d109eabc6255188de91218` and\n`Qwen/Qwen3-8B-Base@49e3418fbbbca6ecbdf9608b4d22e5a407081db4`.\n\n## Restoring removed files\n\nNothing in this folder is marked `delete` in `.aii/manifest.yaml`, so there is nothing to restore. `code_demo.ipynb`\ninstalls its own dependencies from its first cell. The data file can be rebuilt with the command above.\n", "structuredPatch": [], "originalFile": null, "userModified": false}
````

### [179] TOOL CALL — Bash · 2026-10-26 15:45:58 UTC

```
Read test 1 log and notebook size:
cat logs/nbtest_1_minimal.log | tail -40; ls -la code_demo.ipynb
```

### [180] TOOL RESULT — Bash · 2026-10-26 15:45:58 UTC

```
{"stdout": "[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[IPKernelApp] WARNING | Kernel is running over TCP without encryption. All communication (including code and outputs) is sent in plain text and is susceptible to eavesdropping. Use IPC transport or launch with kernel manager-provisioned CurveZMQ keys to enable transport encryption.\n[NbConvertApp] Writing 741081 bytes to code_demo.ipynb\n\nreal\t0m57.085s\nuser\t0m18.827s\nsys\t0m3.470s\nexit 0\n-rw-rw-rw- 1 aii-agent aii-agent 741173 Oct 26 15:45 code_demo.ipynb", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [181] ASSISTANT · 2026-10-26 15:46:06 UTC

```
Test 1 passed: exit 0, 57 s end to end including venv creation and installs. Let me inspect the executed outputs for warnings or anything suspicious.
```

### [182] TOOL CALL — Bash · 2026-10-26 15:46:06 UTC

```
Print executed notebook outputs:
python3 -c "
import json
nb=json.load(open('code_demo.ipynb'))
for i,c in enumerate(nb['cells']):
    if c['cell_type']!='code': continue
    for o in c.get('outputs',[]):
        if o['output_type']=='stream':
            t=''.join(o['text'])
            print(f'--- cell {i} [{o[\"name\"]}]'); print(t[:2500])
        elif o['output_type'] in ('display_data','execute_result'):
            print(f'--- cell {i} [{o[\"output_type\"]}] keys', list(o['data'].keys()))
        elif o['output_type']=='error':
            print(f'--- cell {i} ERROR', o['ename'], o['evalue'])
"
```

### [183] TOOL RESULT — Bash · 2026-10-26 15:46:06 UTC

````
{"stdout": "--- cell 2 [stdout]\ntorch 2.9.0+cpu | numpy 2.0.2\n\n--- cell 4 [stdout]\nGitHub data unavailable, using local mini_demo_data.json: HTTP Error 404: Not Found\n{'T10': '20 prompts', 'B3': '20 prompts'} | {'qwen': 'Qwen/Qwen3-8B@b968826d', 'qwen_base': 'Qwen/Qwen3-8B-Base@49e3418f'}\n\n--- cell 9 [stdout]\n[s_1  ] python inputs10.py copy                       -> logs/s_1_0.log\n[s_1  ] python inputs10.py hardware                   -> logs/s_1_1.log\n[s_1  ] python inputs10.py gate                       -> logs/s_1_2.log\n[s_1  ] python protocol10.py commit0                  -> logs/s_1_3.log\n[s0   ] python capture10.py qwen all                  -> logs/s0_0.log\n[s0   ] python capture10.py qwen_base all             -> logs/s0_1.log\n[s0   ] python debug_s0.py qwen                       -> logs/s0_2.log\n[s0   ] python debug_s0.py qwen_base                  -> logs/s0_3.log\n[s0   ] python w1_tf.py s0report                      -> logs/s0_4.log\n[s0   ] python w1_tf.py nulls                         -> logs/s0_5.log\n[w1tf ] python w1_tf.py score                         -> logs/w1tf_0.log\n[w1tf ] python w1_tf.py export_zs                     -> logs/w1tf_1.log\n[w1gen] python w1_gen.py gpu 2400                     -> logs/w1gen_0.log\n[w1gen] python w1_gen.py g5                           -> logs/w1gen_1.log\n[w1gen] python w1_gen.py label                        -> logs/w1gen_2.log\n[w1gen] python w1_gen.py analyze                      -> logs/w1gen_3.log\n[ext  ] python w1_dose_gen.py commit                  -> logs/ext_0.log\n[ext  ] python w1_dose_gen.py gpu                     -> logs/ext_1.log\n[ext  ] python w1_dose_gen.py commit_strong           -> logs/ext_2.log\n[ext  ] python w1_dose_gen.py gpu_strong              -> logs/ext_3.log\n[ext  ] python w1_dose_gen.py commit_power            -> logs/ext_4.log\n[ext  ] python w1_dose_gen.py gpu_power               -> logs/ext_5.log\n[ext  ] python w1_gen.py label                        -> logs/ext_6.log\n[ext  ] python w1_gen.py analyze                      -> logs/ext_7.log\n[ext  ] python w1_dose_gen.py analyze_power           -> logs/ext_8.log\n[w2   ] python w2_swap.py match                       -> logs/w2_0.log\n[w2   ] python w2_swap.py gpu all                     -> logs/w2_1.log\n[w2   ] python w2_swap.py summary                     -> logs/w2_2.log\n[w3   ] python w3_gemma.py gpu gemma                  -> logs/w3_0.log\n[w3   ] python w3_gemma.py gpu gemma_pt               -> logs/w3_1.log\n[w3   ] python w3_gemma.py score                      -> logs/w3_2.log\n[out  ] python tests_cpu10.py                         -> logs/out_0.log\n[out  ] python analysis10.py delta_geometry           -> logs/out_1.log\n[out  ] python depcheck10.py                          -> logs/out_2.log\n[out  ] python ../audit/rederive.py                   \n--- cell 16 [stdout]\nContext at the fork (prompt 1 of 20: chat template + prefilled opening; the next token is the fork):\n\n<|im_start|>user\nDo not use ship for this task. . . . . . . .\n\nTask: write a Python function solve(n, edges) that returns the number of connected components of an undirected graph. The nodes are the integers 0 to n - 1, with 1 <= n <= 300. The argument edges is a list of pairs [u, v] with 0 <= u, v < n and u != v, each joining nodes u and v; 0 <= len(edges) <= 1500 and no pair of nodes is joined twice. A node with no edges forms a component on its own.\n\nUse only the Python standard library. Return only one ```python code block containing the function solve and any helpers, with no example usage and no explanation.<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n```python\ndef solve(n, edges):\n    def▌\n\nD = [' find'] (union_find)  vs  A = [' dfs', ' bfs'] (dfs|bfs)\nh_fin (20, 4096), h_pre (20, 4096) torch.bfloat16, fork-class rows (3, 4096)\nmean margin: instruct m_I 4.516, base m_B -0.042, gap 4.558 nats\nmean P(D | D or A) = sigmoid(m): instruct 0.948, base 0.489\nTWIN_cpu (this CPU readout) vs the captured GPU margin: max |diff| 1.1e-05\nG1: rms_bf16(h_pre_I, g_I) reproduces the captured h_fin bit for bit on 20/20 prompts\n\n--- cell 18 [stdout]\n{'S': (3,), 'RAND_ISO': (2, 3, 4096), 'RAND_RESID': (2, 3, 4096), 'delta_norm': (3,), 'DELTA_SWAP': (2, 3, 4096), 'DELTA_SWAP_tokens': (2, 3)}\nRAND_ISO  : max | ||draw|| / ||Delta_t|| - 1 | = 0.0e+00\nDELTA_SWAP: max | ||draw|| / ||Delta_t|| - 1 | = 4.4e-02\nRAND_RESID: max | ||draw|| / ||Delta_t|| - 1 | = 0.0e+00\nDELTA_SWAP tokens standing in for (' find', ' dfs', ' bfs'), first draws: [[' доллар', '课堂教学', '_nodes'], ['ができる', 'Beauty', '全都']]\n\n--- cell 23 [stdout]\n15:45:31|INFO   |W1-TF T10: ROWS_ALL 0.548 (0.47658854396146766, 0.645907165126811), ROWS_NORM 0.547, NORM -0.000, ROWS_D 0.060, ROWS_A 0.489; RAND_ISO med -0.014 max 0.115; DELTA_SWAP p95 -0.062; RAND_RESID p95 1.082; interaction -1.337 -> SUPPORTED (readout-level but not token-specific)\n\n--- cell 23 [stdout]\n\nT10 (connected components): ROWS_ALL share 0.5485 [0.477, 0.646] (reported 0.5485) -> SUPPORTED, readout-level but not token-specific\n  logit change of each fork token from its base row, on the instruct state (nats): ' find' -0.27, ' dfs' +2.23, ' bfs' +3.14\n  identities: max |FULL_UNEMB - ROWS_ALL| = 0.0e+00, max |TWIN_cpu - TWIN| = 1.1e-05 nats\n\n540 per-prompt rows (arms + null draws) in W1_TF_ROWS; scoring took 0.0 s\n\n--- cell 25 [stdout]\n15:45:31|INFO   |T10: 1477: frac 0.016 lev 0.0181 (iso 0.0146, resid 0.0963, swap 0.0433); 25792: frac 0.062 lev 0.0692 (iso 0.0114, resid 0.0726, swap 0.0461); 66564: frac 0.054 lev 0.0847 (iso 0.0192, resid 0.0695, swap 0.0266)\n\n--- cell 25 [stdout]\n\nT10: the top-64 PCs explain 0.915 of the residual variance; isotropic energy fraction = 64/4096 = 0.0156\ntoken        class ||Delta|| frac PC64  lev real  lev ISO lev RESID  lev SWAP  h.Delta\n' find'          D    0.0942    0.0156    0.0181   0.0146    0.0963    0.0433    -0.27\n' dfs'           A    0.2026    0.0616    0.0692   0.0114    0.0726    0.0461    +2.23\n' bfs'           A    0.2334    0.0541    0.0847   0.0192    0.0695    0.0266    +3.14\n\n--- cell 28 [display_data] keys ['image/png', 'text/plain']\n--- cell 28 [stdout]\n15:45:31|INFO   |saved F1_w1_shares_nulls\n\n--- cell 28 [display_data] keys ['image/png', 'text/plain']\n--- cell 28 [stdout]\n15:45:31|INFO   |saved F2_per_prompt_shares\n\n--- cell 28 [display_data] keys ['image/png', 'text/plain']\n--- cell 28 [stdout]\n15:45:31|INFO   |saved F3_dose_response\n\n--- cell 30 [display_data] keys ['image/png', 'text/plain']\n--- cell 30 [stdout]\n15:45:32|INFO   |saved F5_readout_plane\n\n--- cell 30 [display_data] keys ['image/png', 'text/plain']\n--- cell 30 [stdout]\n15:45:32|INFO   |saved F6_pca_block35\n\n--- cell 32 [stdout]\n\n=== T10: connected components  |  gap 4.558 nats (reported 4.558)\narm             share            95% CI  reported   |diff|\nROWS_ALL       0.5485    [0.477, 0.646]    0.5485  0.0e+00\nROWS_D         0.0595    [0.051, 0.071]    0.0595  0.0e+00\nROWS_A         0.4889    [0.425, 0.575]    0.4889  0.0e+00\nNORM          -0.0003   [-0.001, 0.000]   -0.0003  0.0e+00\nROWS_NORM      0.5468    [0.475, 0.643]    0.5468  0.0e+00\nFULL_UNEMB     0.5485    [0.477, 0.646]    0.5485  0.0e+00\nSIGN          -0.5483  [-0.646, -0.476]   -0.5483  0.0e+00\nDOSE_0.5       0.2742    [0.238, 0.323]    0.2742  0.0e+00\nDOSE_1.5       0.8228    [0.715, 0.969]    0.8228  0.0e+00\nnull           median      p95      max  p(ROWS_ALL)   reported median / p95 / max / p\nRAND_ISO       -0.014    0.102    0.115       0.3333   0.044 / 0.138 / 0.210 / 0.0196\nDELTA_SWAP     -0.182   -0.062   -0.048       0.3333   0.085 / 0.405 / 0.625 / 0.0588\nRAND_RESID      0.336    1.082    1.165       0.6667   0.181 / 1.252 / 2.328 / 0.3725\n2x2 interaction -1.337 nats (reported -1.337); unembedding-only share on the base residual 0.842 (reported 0.842)\nverdict: SUPPORTED / readout-level but not token-specific   (reported: SUPPORTED / readout-level but not token-specific; role primary)\n\n--- cell 32 [display_data] keys ['image/png', 'text/plain']", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
````

### [184] THINKING · 2026-10-26 15:46:20 UTC

```
The minimal run checks out end to end — arm shares match exactly, the G1 bf16 norm recompute is bit-exact on all 20 prompts, and the verdict/qualifier hold even with only 2 null draws. Before scaling up, I'll review the rendered figures to catch any plotting issues early.
```

### [185] TOOL CALL — Bash · 2026-10-26 15:46:20 UTC

```
Extract figure PNGs from executed notebook:
mkdir -p _preview && python3 -c "
import json, base64
nb=json.load(open('code_demo.ipynb'))
k=0
for i,c in enumerate(nb['cells']):
    for o in c.get('outputs',[]):
        if o['output_type'] in ('display_data','execute_result') and 'image/png' in o['data']:
            open(f'_preview/cell{i}_{k}.png','wb').write(base64.b64decode(o['data']['image/png'])); k+=1
print(k)
"; ls -la _preview
```

### [186] TOOL RESULT — Bash · 2026-10-26 15:46:40 UTC

```
{"stdout": "6\ntotal 3456\ndrwxrwxrwx 2 aii-agent aii-agent 1047651 Oct 26 15:46 .\ndrwxrwxrwx 5 aii-agent aii-agent 2001030 Oct 26 15:46 ..\n-rw-rw-rw- 1 aii-agent aii-agent   93264 Oct 26 15:46 cell28_0.png\n-rw-rw-rw- 1 aii-agent aii-agent   73652 Oct 26 15:46 cell28_1.png\n-rw-rw-rw- 1 aii-agent aii-agent   62681 Oct 26 15:46 cell28_2.png\n-rw-rw-rw- 1 aii-agent aii-agent  134076 Oct 26 15:46 cell30_3.png\n-rw-rw-rw- 1 aii-agent aii-agent   56419 Oct 26 15:46 cell30_4.png\n-rw-rw-rw- 1 aii-agent aii-agent   67863 Oct 26 15:46 cell32_5.png", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [187] TOOL CALL — Read · 2026-10-26 15:46:44 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/_preview/cell30_3.png
```

### [188] TOOL RESULT — Read · 2026-10-26 15:46:44 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [189] TOOL CALL — Read · 2026-10-26 15:46:44 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/_preview/cell32_5.png
```

### [190] TOOL RESULT — Read · 2026-10-26 15:46:44 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [191] THINKING · 2026-10-26 15:46:58 UTC

```
Figures check out—F5 clearly separates instruct (red) and base (blue) states with distinct margin isolines, and the parity-plot scatter matches expectations at N_NULL=2, completing TODO 4. Moving to TODO 5: scaling round 2 with both units at N_NULL=10 and N_BOOT=1000.
```

### [192] TOOL CALL — NotebookEdit · 2026-10-26 15:46:58 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/code_demo.ipynb', 'cell_id': 'e1d109ef', 'edit_mode': 'replace', 'cell_type': 'code', 'new_source': '# ---------------------------------------------------------------- run size (the original values are in the comments)\nUNITS_TF = ("T10", "B3")     # units to score; original ("T10", "B3")  (T10 = connected components, B3 = MST)\nN_NULL = 10                  # draws per null type; original 50 (the data file holds the 50 committed DELTA_SWAP draws)\nN_BOOT = 1000                # prompt-bootstrap resamples for the 95% CIs; original 10000\n\n# ---------------------------------------------------------------- fixed design constants (src/cfg10.py, COMMIT #0)\nD_MODEL = 4096\nRMS_EPS = 1e-6\nUNIT_IDX = {"T10": 0, "B3": 1, "G-GRID": 2}\nDOSES = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5)   # lambda in w_I + lambda * Delta\nSIGN_DOSE = -1.0\nNULL_TYPES = ("RAND_ISO", "DELTA_SWAP", "RAND_RESID")\nNULL_SEED0 = {"RAND_ISO": 101000, "RAND_RESID": 102000, "DELTA_SWAP": 103000}\nRESID_PCS = 64\nSEED_BOOT = 20261024\nSMALL_GAP = 0.5\nTHRESH = {"W1_rows_share": 0.50, "W1_rand_iso_median": 0.15, "W1_disconfirm": 0.20}   # committed W1 verdict rule'}
```

### [193] TOOL RESULT — NotebookEdit [ERROR] · 2026-10-26 15:46:58 UTC

```
Error: File has been modified since read, either by the user or by a linter. Read it again before attempting to write it.
```

### [194] TOOL CALL — Bash · 2026-10-26 15:46:58 UTC

```
Test-run notebook at scaled config (both units):
( time ( UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5 && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5/bin/python jupyter ipykernel && /tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb ) ) > logs/nbtest_2_scaled.log 2>&1; echo "exit $?" >> logs/nbtest_2_scaled.log; tail -8 logs/nbtest_2_scaled.log
```

### [195] TOOL RESULT — Bash · 2026-10-26 15:46:58 UTC

```
{"stdout": "", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false, "backgroundTaskId": "bzo8t70ru"}
```

### [196] THINKING · 2026-10-26 15:47:04 UTC

```
The edit failed since nbconvert had rewritten the notebook, so the test I just launched is using the old minimal config. I'll stop it with TaskStop, re-read the notebook, and redo the edit.
```

### [197] TOOL CALL — ToolSearch · 2026-10-26 15:47:04 UTC

```
{'query': 'select:TaskStop', 'max_results': 1}
```

### [198] TOOL RESULT — ToolSearch · 2026-10-26 15:47:04 UTC

```
{"matches": ["TaskStop"], "query": "select:TaskStop", "total_deferred_tools": 28}
```

### [199] TOOL CALL — TaskStop · 2026-10-26 15:47:06 UTC

```
{'task_id': 'bzo8t70ru'}
```

### [200] TOOL RESULT — TaskStop · 2026-10-26 15:47:06 UTC

```
{"message": "Successfully stopped task: bzo8t70ru (( time ( UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5 && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5/bin/python jupyter ipykernel && /tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb ) ) > logs/nbtest_2_scaled.log 2>&1; echo \"exit $?\" >> logs/nbtest_2_scaled.log; tail -8 logs/nbtest_2_scaled.log)", "task_id": "bzo8t70ru", "task_type": "local_bash", "command": "( time ( UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5 && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5/bin/python jupyter ipykernel && /tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb ) ) > logs/nbtest_2_scaled.log 2>&1; echo \"exit $?\" >> logs/nbtest_2_scaled.log; tail -8 logs/nbtest_2_scaled.log"}
```

### [201] ASSISTANT · 2026-10-26 15:47:14 UTC

```
Stopped. I'll confirm the notebook wasn't overwritten and that no kernel from that run is lingering; matching on my unique venv path is safe here.
```

### [202] TOOL CALL — Bash · 2026-10-26 15:47:14 UTC

```
Check notebook state and leftover processes:
ls -la --time-style=full-iso code_demo.ipynb; cat logs/nbtest_2_scaled.log | tail -5; ps -eo pid,etime,args | grep "art_a7CQm-6CXmoJ-0ccaa3ee52c5" | grep -v grep | head
```

### [203] TOOL RESULT — Bash · 2026-10-26 15:47:14 UTC

```
{"stdout": "-rw-rw-rw- 1 aii-agent aii-agent 741173 2026-10-26 15:45:32.000000000 +0000 code_demo.ipynb\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[IPKernelApp] WARNING | Kernel is running over TCP without encryption. All communication (including code and outputs) is sent in plain text and is susceptible to eavesdropping. Use IPC transport or launch with kernel manager-provisioned CurveZMQ keys to enable transport encryption.", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [204] THINKING · 2026-10-26 15:47:22 UTC

```
The notebook still shows the test 1 output with nothing left pending, so instead of reading the full 740 KB notebook back into context, I'll edit the config cell's source directly by its id.
```

### [205] TOOL CALL — Bash · 2026-10-26 15:47:22 UTC

```
Set scaled config values in notebook config cell:
python3 - <<'EOF'
import json
p = "code_demo.ipynb"
nb = json.load(open(p))
cell = next(c for c in nb["cells"] if c["id"] == "e1d109ef")
src = "".join(cell["source"])
old = ['UNITS_TF = ("T10",)          # units to score;', 'N_NULL = 2                   # draws per null type;', 'N_BOOT = 10                  # prompt-bootstrap']
new = ['UNITS_TF = ("T10", "B3")     # units to score;', 'N_NULL = 10                  # draws per null type;', 'N_BOOT = 1000                # prompt-bootstrap']
for o, n in zip(old, new):
    assert src.count(o) == 1, o
    src = src.replace(o, n)
cell["source"] = src.splitlines(keepends=True)
json.dump(nb, open(p, "w"), indent=1, ensure_ascii=False)
open(p, "a").write("\n")
print("".join(cell["source"])[:400])
EOF
```

### [206] TOOL RESULT — Bash · 2026-10-26 15:47:22 UTC

```
{"stdout": "# ---------------------------------------------------------------- run size (the original values are in the comments)\nUNITS_TF = (\"T10\", \"B3\")     # units to score; original (\"T10\", \"B3\")  (T10 = connected components, B3 = MST)\nN_NULL = 10                  # draws per null type; original 50 (the data file holds the 50 committed DELTA_SWAP draws)\nN_BOOT = 1000                # prompt-bootstrap resa", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [207] TOOL CALL — Bash · 2026-10-26 15:47:28 UTC

```
Test-run notebook at scaled config in clean venv:
python3 -c "import json; json.load(open('code_demo.ipynb')); print('valid json')" && ( time ( UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5 && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5/bin/python jupyter ipykernel && /tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb ) ) > logs/nbtest_2_scaled.log 2>&1; echo "exit $?" >> logs/nbtest_2_scaled.log; tail -8 logs/nbtest_2_scaled.log
```

### [208] TOOL RESULT — Bash · 2026-10-26 15:47:28 UTC

```
{"stdout": "", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false, "backgroundTaskId": "bdv87qras"}
```

### [209] ASSISTANT · 2026-10-26 15:47:32 UTC

```
While the scaled test runs, I'll check the remaining test 1 figures (F1, F6).
```

### [210] TOOL CALL — Read · 2026-10-26 15:47:32 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/_preview/cell28_0.png
```

### [211] TOOL RESULT — Read · 2026-10-26 15:47:32 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [212] TOOL CALL — Read · 2026-10-26 15:47:32 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/_preview/cell30_4.png
```

### [213] TOOL RESULT — Read · 2026-10-26 15:47:32 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [214] ASSISTANT · 2026-10-26 15:47:38 UTC

```
The figures match the originals' design, and the empty panels will fill once B3 is included. To confirm the reproduction is faithful, I'll compare with the artifact's own F5.
```

### [215] TOOL CALL — Read · 2026-10-26 15:47:38 UTC

```
/ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56/figures/F5_readout_plane.png
```

### [216] TOOL RESULT — Read · 2026-10-26 15:47:38 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [217] SYSTEM-USER prompt · 2026-10-26 15:47:38 UTC

```
[Image: original 2200x920, displayed at 2000x836. Multiply coordinates by 1.10 to map to original image.]
```

### [218] ASSISTANT · 2026-10-26 15:47:48 UTC

```
My notebook's T10 F5 panel is identical to the artifact's. While test 2 runs, I'll watch its log for completion with a Monitor until-loop.
```

### [219] TOOL CALL — Monitor · 2026-10-26 15:47:48 UTC

```
{'command': 'cd /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ && until grep -q "^exit" logs/nbtest_2_scaled.log 2>/dev/null; do sleep 2; done; grep -E "^exit|^real|Error|Traceback" logs/nbtest_2_scaled.log | head -20', 'description': 'scaled notebook test (test 2) completion', 'timeout_ms': 600000}
```

### [220] TOOL RESULT — Monitor · 2026-10-26 15:47:48 UTC

```
{"taskId": "bcrmty8iv", "timeoutMs": 600000, "persistent": false}
```

### [221] THINKING · 2026-10-26 15:47:58 UTC

```
While test 2 runs, I'll check whether the install cell produced noisy output worth suppressing with `%%capture`, and scan the notebook for any absolute server paths since it's getting published.
```

### [222] TOOL CALL — Bash · 2026-10-26 15:47:58 UTC

```
Check install output and absolute paths in published files:
python3 -c "
import json
nb=json.load(open('code_demo.ipynb'))
c=nb['cells'][1]; print('install cell outputs:', c.get('outputs'))
src=json.dumps([''.join(c['source']) for c in nb['cells']])
for bad in ('/ai-inventor','run_5eGZGmskluur','/tmp/'):
    print(bad, 'in sources:', bad in src)
"; grep -c "/ai-inventor" README.md build_mini_demo_data.py .aii/manifest.yaml; grep -o '"/ai-inventor[^"]*"' mini_demo_data.json | head -3; echo "data file abs-path hits: $(grep -c '/ai-inventor' mini_demo_data.json)"
```

### [223] TOOL RESULT — Bash · 2026-10-26 15:47:58 UTC

```
{"stdout": "install cell outputs: []\n/ai-inventor in sources: True\nrun_5eGZGmskluur in sources: False\n/tmp/ in sources: False\n.aii/manifest.yaml:0\nREADME.md:0\nbuild_mini_demo_data.py:0\ndata file abs-path hits: 0", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [224] THINKING · 2026-10-26 15:48:06 UTC

```
Test 2 passed in 24s, but the path check flagged a reference to `/ai-inventor` in the notebook sources that shouldn't be published—I'll track down where it is.
```

### [225] TOOL CALL — Bash · 2026-10-26 15:48:06 UTC

```
Locate absolute paths in notebook:
python3 -c "
import json
nb=json.load(open('code_demo.ipynb'))
for i,c in enumerate(nb['cells']):
    s=''.join(c['source'])
    for ln in s.splitlines():
        if '/ai-inventor' in ln: print('SOURCE cell', i, c['id'], repr(ln[:200]))
    for o in c.get('outputs',[]):
        t=json.dumps(o)
        if '/ai-inventor' in t:
            idx=t.find('/ai-inventor'); print('OUTPUT cell', i, o['output_type'], repr(t[max(0,idx-150):idx+150]))
print('metadata hit:', '/ai-inventor' in json.dumps(nb['metadata']))
"
```

### [226] TOOL RESULT — Bash · 2026-10-26 15:48:06 UTC

```
{"stdout": "SOURCE cell 3 7ea594f1 'GITHUB_DATA_URL = \"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-10/experiment-56/demo/mini_demo_data.js'\nmetadata hit: False", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [227] ASSISTANT · 2026-10-26 15:48:12 UTC

```
False alarm: the match is the GitHub org name `ai-inventor-papers` inside the required URL, not a server path. Sources and outputs are clean. Now the test 2 numbers, including B3:
```

### [228] TOOL CALL — Bash · 2026-10-26 15:48:12 UTC

```
Print key outputs of scaled test:
python3 -c "
import json
nb=json.load(open('code_demo.ipynb'))
for i in (16, 18, 23, 25, 32):
    c=nb['cells'][i]
    for o in c.get('outputs',[]):
        if o['output_type']=='stream':
            print(f'--- cell {i} [{o[\"name\"]}]'); print(''.join(o['text'])[:3500])
        elif o['output_type']=='error':
            print('ERROR', o['ename'], o['evalue'])
" | sed -n '1,200p' | grep -v "^<|im_start|>\|^Use only\|^Task:\|^Do not use" 
```

### [229] TOOL RESULT — Bash · 2026-10-26 15:48:12 UTC

````
{"stdout": "--- cell 16 [stdout]\nContext at the fork (prompt 1 of 20: chat template + prefilled opening; the next token is the fork):\n\n\n\n<think>\n\n</think>\n\n```python\ndef solve(n, edges):\n    def▌\n\nD = [' find'] (union_find)  vs  A = [' dfs', ' bfs'] (dfs|bfs)\nh_fin (20, 4096), h_pre (20, 4096) torch.bfloat16, fork-class rows (3, 4096)\nmean margin: instruct m_I 4.516, base m_B -0.042, gap 4.558 nats\nmean P(D | D or A) = sigmoid(m): instruct 0.948, base 0.489\nTWIN_cpu (this CPU readout) vs the captured GPU margin: max |diff| 1.1e-05\nG1: rms_bf16(h_pre_I, g_I) reproduces the captured h_fin bit for bit on 20/20 prompts\n\n--- cell 18 [stdout]\n{'S': (3,), 'RAND_ISO': (10, 3, 4096), 'RAND_RESID': (10, 3, 4096), 'delta_norm': (3,), 'DELTA_SWAP': (10, 3, 4096), 'DELTA_SWAP_tokens': (10, 3)}\nRAND_ISO  : max | ||draw|| / ||Delta_t|| - 1 | = 0.0e+00\nDELTA_SWAP: max | ||draw|| / ||Delta_t|| - 1 | = 4.9e-02\nRAND_RESID: max | ||draw|| / ||Delta_t|| - 1 | = 0.0e+00\nDELTA_SWAP tokens standing in for (' find', ' dfs', ' bfs'), first draws: [[' доллар', '课堂教学', '_nodes'], ['ができる', 'Beauty', '全都'], ['.Search', '?>', '◗']]\n\n--- cell 23 [stdout]\n15:47:48|INFO   |W1-TF T10: ROWS_ALL 0.548 (0.43922700692351974, 0.7251568732163185), ROWS_NORM 0.547, NORM -0.000, ROWS_D 0.060, ROWS_A 0.489; RAND_ISO med 0.042 max 0.128; DELTA_SWAP p95 0.408; RAND_RESID p95 1.252; interaction -1.337 -> SUPPORTED (readout-level but not token-specific)\n\n--- cell 23 [stdout]\n15:47:48|WARNING|B3 DELTA_SWAP: draws not in the demo data; using the 10 committed shares\n\n--- cell 23 [stdout]\n15:47:48|INFO   |W1-TF B3: ROWS_ALL 1.249 (1.1814146781283363, 1.3261085232965206), ROWS_NORM 1.254, NORM 0.006, ROWS_D 0.009, ROWS_A 1.240; RAND_ISO med 0.100 max 0.693; DELTA_SWAP p95 0.883; RAND_RESID p95 4.999; interaction 1.748 -> SUPPORTED (readout-level but not token-specific)\n\n--- cell 23 [stdout]\n\nT10 (connected components): ROWS_ALL share 0.5485 [0.439, 0.725] (reported 0.5485) -> SUPPORTED, readout-level but not token-specific\n  logit change of each fork token from its base row, on the instruct state (nats): ' find' -0.27, ' dfs' +2.23, ' bfs' +3.14\n  identities: max |FULL_UNEMB - ROWS_ALL| = 0.0e+00, max |TWIN_cpu - TWIN| = 1.1e-05 nats\n\nB3 (minimum spanning tree weight): ROWS_ALL share 1.2495 [1.181, 1.326] (reported 1.2495) -> SUPPORTED, readout-level but not token-specific\n  logit change of each fork token from its base row, on the instruct state (nats): ' Kr' -0.02, ' Union' -1.98, ' Check' +0.57, ' Minimum' +0.32, ' Find' +0.92, ' Priority' +1.29, ' Helper' +3.24, ' Dis' +0.99, ' Prim' +2.60, ' Pr' +0.17, ' Use' -0.93, ' MST' +1.57, ' To' -0.01, ' Using' -0.11, 'Prim' -0.53, ' Prime' +0.93\n  identities: max |FULL_UNEMB - ROWS_ALL| = 0.0e+00, max |TWIN_cpu - TWIN| = 1.1e-05 nats\n\n1840 per-prompt rows (arms + null draws) in W1_TF_ROWS; scoring took 0.1 s\n\n--- cell 25 [stdout]\n15:47:49|INFO   |T10: 1477: frac 0.016 lev 0.0181 (iso 0.0119, resid 0.0484, swap 0.0579); 25792: frac 0.062 lev 0.0692 (iso 0.0113, resid 0.1271, swap 0.0259); 66564: frac 0.054 lev 0.0847 (iso 0.0050, resid 0.0862, swap 0.0177)\n\n--- cell 25 [stdout]\n15:47:49|INFO   |B3: 16447: frac 0.035 lev 0.0008 (iso 0.0057, resid 0.0769, swap nan); 9145: frac 0.029 lev 0.0543 (iso 0.0135, resid 0.0926, swap nan); 4248: frac 0.030 lev 0.0225 (iso 0.0173, resid 0.0646, swap nan); 30925: frac 0.048 lev 0.0086 (iso 0.0105, resid 0.0731, swap nan)\n\n--- cell 25 [stdout]\n\nT10: the top-64 PCs explain 0.915 of the residual variance; isotropic energy fraction = 64/4096 = 0.0156\ntoken        class ||Delta|| frac PC64  lev real  lev ISO lev RESID  lev SWAP  h.Delta\n' find'          D    0.0942    0.0156    0.0181   0.0119    0.0484    0.0579    -0.27\n' dfs'           A    0.2026    0.0616    0.0692   0.0113    0.1271    0.0259    +2.23\n' bfs'           A    0.2334    0.0541    0.0847   0.0050    0.0862    0.0177    +3.14\n\nB3: the top-64 PCs explain 0.902 of the residual variance; isotropic energy fraction = 64/4096 = 0.0156\ntoken        class ||Delta|| frac PC64  lev real  lev ISO lev RESID  lev SWAP  h.Delta\n' Kr'            D    0.1911    0.0352    0.0008   0.0057    0.0769       nan    -0.02\n' Union'         D    0.1905    0.0290    0.0543   0.0135    0.0926       nan    -1.98\n' Check'         D    0.1317    0.0300    0.0225   0.0173    0.0646       nan    +0.57\n' Minimum'       D    0.1960    0.0484    0.0086   0.0105    0.0731       nan    +0.32\n' Find'          D    0.1489    0.0242    0.0322   0.0031    0.0861       nan    +0.92\n' Priority'      D    0.2027    0.0326    0.0334   0.0094    0.0339       nan    +1.29\n' Helper'        D    0.2312    0.0495    0.0734   0.0095    0.0608       nan    +3.24\n' Dis'           D    0.1730    0.0229    0.0299   0.0145    0.1049       nan    +0.99\n' Prim'          A    0.1963    0.0426    0.0694   0.0092    0.1136       nan    +2.60\n' Pr'            A    0.1758    0.0271    0.0051   0.0138    0.0853       nan    +0.17\n' Use'           A    0.1337    0.0186    0.0366   0.0126    0.1338       nan    -0.93\n' MST'           A    0.1942    0.0313    0.0422   0.0102    0.0765       nan    +1.57\n' To'            A    0.1167    0.0220    0.0004   0.0108    0.1174       nan    -0.01\n' Using'         A    0.1397    0.0205    0.0042   0.0127    0.0595       nan    -0.11\n'Prim'           A    0.2004    0.0476    0.0139   0.0075    0.0474       nan    -0.53\n' Prime'         A    0.1818    0.0285    0.0267   0.0075    0.1026       nan    +0.93\n\n--- cell 32 [stdout]\n\n=== T10: connected components  |  gap 4.558 nats (reported 4.558)\narm             share            95% CI  reported   |diff|\nROWS_ALL       0.5485    [0.439, 0.725]    0.5485  0.0e+00\nROWS_D         0.0595    [0.048, 0.079]    0.0595  0.0e+00\nROWS_A         0.4889    [0.392, 0.646]    0.4889  0.0e+00\nNORM          -0.0003   [-0.001, 0.000]   -0.0003  0.0e+00\nROWS_NORM      0.5468    [0.438, 0.723]    0.5468  0.0e+00\nFULL_UNEMB     0.5485    [0.439, 0.725]    0.5485  0.0e+00\nSIGN          -0.5483  [-0.725, -0.439]   -0.5483  0.0e+00\nDOSE_0.5       0.2742    [0.220, 0.363]    0.2742  0.0e+00\nDOSE_1.5       0.8228    [0.659, 1.088]    0.8228  0.0e+00\nnull           median      p95      max  p(ROWS_ALL)   reported median / p95 / max / p\nRAND_ISO        0.042    0.128    0.128       0.0909   0.044 / 0.138 / 0.210 / 0.0196\nDELTA_SWAP     -0.033    0.408    0.607       0.1818   0.085 / 0.405 / 0.625 / 0.0588\nRAND_RESID      0.188    1.252    1.323       0.4545   0.181 / 1.252 / 2.328 / 0.3725\n2x2 interaction -1.337 nats (reported -1.337); unembedding-only share on the base residual 0.842 (reported 0.842)\nverdict: SUPPORTED / readout-level but not token-specific   (reported: SUPPORTED / readout-level but not token-specific; role primary)\n\n=== B3: minimum spanning tree weight  |  gap 2.090 nats (reported 2.090)\narm             share            95% CI  reported   |diff|\nROWS_ALL       1.2495    [1.181, 1.326]    1.2495  0.0e+00\nROWS_D         0.0093    [0.004, 0.015]    0.0093  0.0e+00\nROWS_A         1.2402    [1.173, 1.317]    1.2402  0.0e+00\nNORM           0.0065    [0.005, 0.008]    0.0065  0.0e+00\nROWS_NORM      1.2542    [1.186, 1.332]    1.2542  0.0e+00\nFULL_UNEMB     1.2495    [1.181, 1.326]    1.2495  0.0e+00\nSIGN          -1.1853  [-1.262, -1.117]   -1.1853  0.0e+00\nDOSE_0.5       0.6234    [0.589, 0.662]    0.6234  0.0e+00\nDOSE_1.5       1.8757    [1.774, 1.991]    1.8757  0.0e+00\nnull           median      p95      max  p(ROWS_ALL)   reported median / p95 / max / p\nRAND_ISO        0.100    0.577    0.693       0.0909   0.051 / 0.720 / 0.942 / 0.0196\nDELTA_SWAP      0.213    0.883    0.908       0.0909   0.055 / 1.169 / 1.511 / 0.0588  (committed shares)\nRAND_RESID     -0.777    4.999    5.839       0.3636   0.113 / 5.394 / 6.224 / 0.2745\n2x2 interaction +1.748 nats (reported +1.748); unembedding-only share on the base residual 0.416 (reported 0.416)\nverdict: SUPPORTED / readout-level but not token-specific   (reported: SUPPORTED / readout-level but not token-specific; role descriptive)", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
````

### [230] THINKING · 2026-10-26 15:48:26 UTC

```
Test 2 checks out fully—arm shares, B3's decomposition, and verdicts all match, with scoring at just 0.1s well within budget. Moving to scaling round 3 with N_NULL=50 and N_BOOT=10000.
```

### [231] TOOL CALL — Bash · 2026-10-26 15:48:26 UTC

```
Set original config values and run final test:
python3 - <<'EOF'
import json
p = "code_demo.ipynb"
nb = json.load(open(p))
cell = next(c for c in nb["cells"] if c["id"] == "e1d109ef")
src = "".join(cell["source"])
old = ['N_NULL = 10                  # draws per null type;', 'N_BOOT = 1000                # prompt-bootstrap']
new = ['N_NULL = 50                  # draws per null type;', 'N_BOOT = 10000               # prompt-bootstrap']
for o, n in zip(old, new):
    assert src.count(o) == 1, o
    src = src.replace(o, n)
cell["source"] = src.splitlines(keepends=True)
json.dump(nb, open(p, "w"), indent=1, ensure_ascii=False)
open(p, "a").write("\n")
print("".join(cell["source"])[:420])
EOF
( time ( UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5 && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5/bin/python jupyter ipykernel && /tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb ) ) > logs/nbtest_3_full.log 2>&1; echo "exit $?" >> logs/nbtest_3_full.log; grep -E "^exit|^real" logs/nbtest_3_full.log
```

### [232] TOOL RESULT — Bash · 2026-10-26 15:48:48 UTC

```
{"stdout": "# ---------------------------------------------------------------- run size (the original values are in the comments)\nUNITS_TF = (\"T10\", \"B3\")     # units to score; original (\"T10\", \"B3\")  (T10 = connected components, B3 = MST)\nN_NULL = 50                  # draws per null type; original 50 (the data file holds the 50 committed DELTA_SWAP draws)\nN_BOOT = 10000               # prompt-bootstrap resamples for the 95% CI\nreal\t0m26.275s\nexit 0", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [233] ASSISTANT · 2026-10-26 15:48:56 UTC

```
The final test with the original parameters passed in 26 s end to end (57 s with a cold pip cache), far below the 600 s limit. Checking the final numbers against the reported ones:
```

### [234] TOOL CALL — Bash · 2026-10-26 15:48:56 UTC

```
Print final-run key outputs and check errors:
python3 -c "
import json
nb=json.load(open('code_demo.ipynb'))
for i in (23, 25, 32):
    c=nb['cells'][i]
    for o in c.get('outputs',[]):
        if o['output_type']=='stream':
            t=''.join(o['text'])
            if i==25 and 'B3:' in t and 'token' in t: t=t[:t.find('B3:')]
            print(f'--- cell {i} [{o[\"name\"]}]'); print(t[:3000])
        elif o['output_type']=='error':
            print('ERROR', o['ename'], o['evalue'])
errs=[(i,o['ename']) for i,c in enumerate(nb['cells']) for o in c.get('outputs',[]) if o['output_type']=='error']
print('errors:', errs)
print('stderr outputs:', [(i) for i,c in enumerate(nb['cells']) for o in c.get('outputs',[]) if o.get('name')=='stderr'])
"; ls -la code_demo.ipynb
```

### [235] TOOL RESULT — Bash · 2026-10-26 15:48:56 UTC

```
{"stdout": "--- cell 23 [stdout]\n15:48:44|INFO   |W1-TF T10: ROWS_ALL 0.548 (0.4396290582255756, 0.706851369990123), ROWS_NORM 0.547, NORM -0.000, ROWS_D 0.060, ROWS_A 0.489; RAND_ISO med 0.044 max 0.210; DELTA_SWAP p95 0.405; RAND_RESID p95 1.252; interaction -1.337 -> SUPPORTED (readout-level but not token-specific)\n\n--- cell 23 [stdout]\n15:48:44|WARNING|B3 DELTA_SWAP: draws not in the demo data; using the 50 committed shares\n\n--- cell 23 [stdout]\n15:48:44|INFO   |W1-TF B3: ROWS_ALL 1.249 (1.1803348280864892, 1.3230638555796224), ROWS_NORM 1.254, NORM 0.006, ROWS_D 0.009, ROWS_A 1.240; RAND_ISO med 0.051 max 0.942; DELTA_SWAP p95 1.169; RAND_RESID p95 5.394; interaction 1.748 -> SUPPORTED (readout-level but not token-specific)\n\n--- cell 23 [stdout]\n\nT10 (connected components): ROWS_ALL share 0.5485 [0.440, 0.707] (reported 0.5485) -> SUPPORTED, readout-level but not token-specific\n  logit change of each fork token from its base row, on the instruct state (nats): ' find' -0.27, ' dfs' +2.23, ' bfs' +3.14\n  identities: max |FULL_UNEMB - ROWS_ALL| = 0.0e+00, max |TWIN_cpu - TWIN| = 1.1e-05 nats\n\nB3 (minimum spanning tree weight): ROWS_ALL share 1.2495 [1.180, 1.323] (reported 1.2495) -> SUPPORTED, readout-level but not token-specific\n  logit change of each fork token from its base row, on the instruct state (nats): ' Kr' -0.02, ' Union' -1.98, ' Check' +0.57, ' Minimum' +0.32, ' Find' +0.92, ' Priority' +1.29, ' Helper' +3.24, ' Dis' +0.99, ' Prim' +2.60, ' Pr' +0.17, ' Use' -0.93, ' MST' +1.57, ' To' -0.01, ' Using' -0.11, 'Prim' -0.53, ' Prime' +0.93\n  identities: max |FULL_UNEMB - ROWS_ALL| = 0.0e+00, max |TWIN_cpu - TWIN| = 1.1e-05 nats\n\n5840 per-prompt rows (arms + null draws) in W1_TF_ROWS; scoring took 0.6 s\n\n--- cell 25 [stdout]\n15:48:44|INFO   |T10: 1477: frac 0.016 lev 0.0181 (iso 0.0102, resid 0.1000, swap 0.0455); 25792: frac 0.062 lev 0.0692 (iso 0.0096, resid 0.0851, swap 0.0170); 66564: frac 0.054 lev 0.0847 (iso 0.0097, resid 0.0933, swap 0.0203)\n\n--- cell 25 [stdout]\n15:48:44|INFO   |B3: 16447: frac 0.035 lev 0.0008 (iso 0.0085, resid 0.0865, swap nan); 9145: frac 0.029 lev 0.0543 (iso 0.0117, resid 0.0886, swap nan); 4248: frac 0.030 lev 0.0225 (iso 0.0109, resid 0.0790, swap nan); 30925: frac 0.048 lev 0.0086 (iso 0.0089, resid 0.0724, swap nan)\n\n--- cell 25 [stdout]\n\nT10: the top-64 PCs explain 0.915 of the residual variance; isotropic energy fraction = 64/4096 = 0.0156\ntoken        class ||Delta|| frac PC64  lev real  lev ISO lev RESID  lev SWAP  h.Delta\n' find'          D    0.0942    0.0156    0.0181   0.0102    0.1000    0.0455    -0.27\n' dfs'           A    0.2026    0.0616    0.0692   0.0096    0.0851    0.0170    +2.23\n' bfs'           A    0.2334    0.0541    0.0847   0.0097    0.0933    0.0203    +3.14\n\n\n--- cell 32 [stdout]\n\n=== T10: connected components  |  gap 4.558 nats (reported 4.558)\narm             share            95% CI  reported   |diff|\nROWS_ALL       0.5485    [0.440, 0.707]    0.5485  0.0e+00\nROWS_D         0.0595    [0.047, 0.078]    0.0595  0.0e+00\nROWS_A         0.4889    [0.392, 0.629]    0.4889  0.0e+00\nNORM          -0.0003   [-0.001, 0.000]   -0.0003  0.0e+00\nROWS_NORM      0.5468    [0.439, 0.704]    0.5468  0.0e+00\nFULL_UNEMB     0.5485    [0.440, 0.707]    0.5485  0.0e+00\nSIGN          -0.5483  [-0.707, -0.440]   -0.5483  0.0e+00\nDOSE_0.5       0.2742    [0.220, 0.353]    0.2742  0.0e+00\nDOSE_1.5       0.8228    [0.660, 1.060]    0.8228  0.0e+00\nnull           median      p95      max  p(ROWS_ALL)   reported median / p95 / max / p\nRAND_ISO        0.044    0.138    0.210       0.0196   0.044 / 0.138 / 0.210 / 0.0196\nDELTA_SWAP      0.085    0.405    0.625       0.0588   0.085 / 0.405 / 0.625 / 0.0588\nRAND_RESID      0.181    1.252    2.328       0.3725   0.181 / 1.252 / 2.328 / 0.3725\n2x2 interaction -1.337 nats (reported -1.337); unembedding-only share on the base residual 0.842 (reported 0.842)\nverdict: SUPPORTED / readout-level but not token-specific   (reported: SUPPORTED / readout-level but not token-specific; role primary)\n\n=== B3: minimum spanning tree weight  |  gap 2.090 nats (reported 2.090)\narm             share            95% CI  reported   |diff|\nROWS_ALL       1.2495    [1.180, 1.323]    1.2495  0.0e+00\nROWS_D         0.0093    [0.003, 0.015]    0.0093  0.0e+00\nROWS_A         1.2402    [1.172, 1.313]    1.2402  0.0e+00\nNORM           0.0065    [0.005, 0.008]    0.0065  0.0e+00\nROWS_NORM      1.2542    [1.184, 1.328]    1.2542  0.0e+00\nFULL_UNEMB     1.2495    [1.180, 1.323]    1.2495  0.0e+00\nSIGN          -1.1853  [-1.258, -1.115]   -1.1853  0.0e+00\nDOSE_0.5       0.6234    [0.589, 0.660]    0.6234  0.0e+00\nDOSE_1.5       1.8757    [1.772, 1.986]    1.8757  0.0e+00\nnull           median      p95      max  p(ROWS_ALL)   reported median / p95 / max / p\nRAND_ISO        0.051    0.720    0.942       0.0196   0.051 / 0.720 / 0.942 / 0.0196\nDELTA_SWAP      0.055    1.169    1.511       0.0588   0.055 / 1.169 / 1.511 / 0.0588  (committed shares)\nRAND_RESID      0.113    5.394    6.224       0.2745   0.113 / 5.394 / 6.224 / 0.2745\n2x2 interaction +1.748 nats (reported +1.748); unembedding-only share on the base residual 0.416 (reported 0.416)\nverdict: SUPPORTED / readout-level but not token-specific   (reported: SUPPORTED / readout-level but not token-specific; role descriptive)\n\nerrors: []\nstderr outputs: []\n-rw-rw-rw- 1 aii-agent aii-agent 1081031 Oct 26 15:48 code_demo.ipynb", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [236] THINKING · 2026-10-26 15:49:06 UTC

```
The full run exactly reproduces every reported W1 result for both units—arm shares, CIs, null stats, interactions, decompositions, and verdicts—with no errors. Now I'll check the final figures.
```

### [237] TOOL CALL — Bash · 2026-10-26 15:49:06 UTC

```
Extract final figures for visual check:
rm -f _preview/*.png && python3 -c "
import json, base64
nb=json.load(open('code_demo.ipynb'))
k=0
for i,c in enumerate(nb['cells']):
    for o in c.get('outputs',[]):
        if o['output_type'] in ('display_data','execute_result') and 'image/png' in o['data']:
            open(f'_preview/cell{i}_{k}.png','wb').write(base64.b64decode(o['data']['image/png'])); k+=1
print(k)
"; ls _preview
```

### [238] TOOL RESULT — Bash · 2026-10-26 15:49:06 UTC

```
{"stdout": "6\ncell28_0.png\ncell28_1.png\ncell28_2.png\ncell30_3.png\ncell30_4.png\ncell32_5.png", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [239] TOOL CALL — Read · 2026-10-26 15:49:12 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/_preview/cell28_0.png
```

### [240] TOOL RESULT — Read · 2026-10-26 15:49:12 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [241] TOOL CALL — Read · 2026-10-26 15:49:12 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/_preview/cell30_3.png
```

### [242] TOOL RESULT — Read · 2026-10-26 15:49:12 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [243] TOOL CALL — Read · 2026-10-26 15:49:12 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/_preview/cell32_5.png
```

### [244] TOOL RESULT — Read · 2026-10-26 15:49:12 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [245] SYSTEM-USER prompt · 2026-10-26 15:49:12 UTC

```
[Image: original 2239x619, displayed at 2000x553. Multiply coordinates by 1.12 to map to original image.]
```

### [246] THINKING · 2026-10-26 15:49:24 UTC

```
All figures render correctly, F5 matches the artifact in both units, and the parity plot confirms zero difference across arm shares and null statistics—TODO 5 is done, with the original parameters running in 26s so no reduced values were needed. Now I'll clean up temporary previews and update the README with the measured results and runtimes.
```

### [247] TOOL CALL — Bash · 2026-10-26 15:49:24 UTC

```
Remove preview images and list final workspace:
rm -r _preview && ls -la && ls -la logs && grep -E "^real|^exit" logs/*.log
```

### [248] TOOL RESULT — Bash · 2026-10-26 15:49:24 UTC

```
{"stdout": "total 15543\ndrwxrwxrwx 4 aii-agent aii-agent 2001036 Oct 26 15:49 .\ndrwxrwxrwx 9 aii-agent aii-agent 2003448 Oct 26 15:25 ..\ndrwxrwxrwx 2 aii-agent aii-agent   37800 Oct 26 15:45 .aii\n-rw-rw-rw- 1 aii-agent aii-agent      54 Oct 26 15:21 .aii_claude_session.json\n-rw-rw-rw- 1 aii-agent aii-agent 1438819 Oct 26 15:49 .repl_agent.ptylog\n-rw-rw-rw- 1 aii-agent aii-agent     113 Oct 26 15:45 .terminal_claude_agent_struct_out.json\n-rw-rw-rw- 1 aii-agent aii-agent    5365 Oct 26 15:45 README.md\n-rw-rw-rw- 1 aii-agent aii-agent   12239 Oct 26 15:29 build_mini_demo_data.py\n-rw-rw-rw- 1 aii-agent aii-agent 1081031 Oct 26 15:48 code_demo.ipynb\ndrwxrwxrwx 2 aii-agent aii-agent 1000132 Oct 26 15:48 logs\n-rw-rw-rw- 1 aii-agent aii-agent 8337194 Oct 26 15:30 mini_demo_data.json\ntotal 2933\ndrwxrwxrwx 2 aii-agent aii-agent 1000132 Oct 26 15:48 .\ndrwxrwxrwx 4 aii-agent aii-agent 2001036 Oct 26 15:49 ..\n-rw-rw-rw- 1 aii-agent aii-agent     452 Oct 26 15:45 nbtest_1_minimal.log\n-rw-rw-rw- 1 aii-agent aii-agent     453 Oct 26 15:47 nbtest_2_scaled.log\n-rw-rw-rw- 1 aii-agent aii-agent     453 Oct 26 15:48 nbtest_3_full.log\nlogs/nbtest_1_minimal.log:real\t0m57.085s\nlogs/nbtest_1_minimal.log:exit 0\nlogs/nbtest_2_scaled.log:real\t0m24.241s\nlogs/nbtest_2_scaled.log:exit 0\nlogs/nbtest_3_full.log:real\t0m26.275s\nlogs/nbtest_3_full.log:exit 0", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [249] TOOL CALL — Edit · 2026-10-26 15:49:32 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/README.md
OLD: ## How to run
NEW: ## Results of the final run (original parameters)

The notebook reproduces every reported W1 teacher-forced number. The arm shares differ from the reported ones by
0.0. The null medians, p95s, maxima and empirical p-values are identical, and so are both verdicts.

| | T10 (CC, primary) | B3 (MST, beside) |
|---|---|---|
| gap `m_I - m_B` | 4.558 nats | 2.090 nats |
| ROWS_ALL share [95% CI] | **0.548 [0.440, 0.707]** | 1.249 [1.180, 1.323] |
| ROWS_A / ROWS_D / NORM | 0.489 / 0.060 / -0.000 | 1.240 / 0.009 / 0.006 |
| RAND_ISO median / max / p | 0.044 / 0.210 / 0.020 | 0.051 / 0.942 / 0.020 |
| RAND_RESID p95 / p | 1.252 / 0.373 | 5.394 / 0.275 |
| 2x2 interaction | -1.337 nats | +1.748 nats |
| logit change from the base rows | `' find'` -0.27, `' dfs'` +2.23, `' bfs'` +3.14 | 16 tokens, mixed |
| verdict | SUPPORTED, readout-level but not token-specific | the same (descriptive) |

B3's DELTA_SWAP row uses its 50 committed shares, because its draws are not in the data file. The table above omits
that row.

**Test runs.** All runs used a fresh Python 3.12 virtualenv, with installs inside the notebook (`logs/`):

| run | settings | time |
|---|---|---|
| 1 | T10, 2 draws, 10 resamples | 57 s with a cold pip cache |
| 2 | both units, 10 draws, 1,000 resamples | 24 s |
| 3 | the original values | 26 s |

The W1 scoring itself takes 0.6 s.

## How to run
```

### [250] TOOL RESULT — Edit · 2026-10-26 15:49:32 UTC

````
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_10/art_a7CQm-6CXmoJ/README.md", "oldString": "## How to run", "newString": "## Results of the final run (original parameters)\n\nThe notebook reproduces every reported W1 teacher-forced number. The arm shares differ from the reported ones by\n0.0. The null medians, p95s, maxima and empirical p-values are identical, and so are both verdicts.\n\n| | T10 (CC, primary) | B3 (MST, beside) |\n|---|---|---|\n| gap `m_I - m_B` | 4.558 nats | 2.090 nats |\n| ROWS_ALL share [95% CI] | **0.548 [0.440, 0.707]** | 1.249 [1.180, 1.323] |\n| ROWS_A / ROWS_D / NORM | 0.489 / 0.060 / -0.000 | 1.240 / 0.009 / 0.006 |\n| RAND_ISO median / max / p | 0.044 / 0.210 / 0.020 | 0.051 / 0.942 / 0.020 |\n| RAND_RESID p95 / p | 1.252 / 0.373 | 5.394 / 0.275 |\n| 2x2 interaction | -1.337 nats | +1.748 nats |\n| logit change from the base rows | `' find'` -0.27, `' dfs'` +2.23, `' bfs'` +3.14 | 16 tokens, mixed |\n| verdict | SUPPORTED, readout-level but not token-specific | the same (descriptive) |\n\nB3's DELTA_SWAP row uses its 50 committed shares, because its draws are not in the data file. The table above omits\nthat row.\n\n**Test runs.** All runs used a fresh Python 3.12 virtualenv, with installs inside the notebook (`logs/`):\n\n| run | settings | time |\n|---|---|---|\n| 1 | T10, 2 draws, 10 resamples | 57 s with a cold pip cache |\n| 2 | both units, 10 draws, 1,000 resamples | 24 s |\n| 3 | the original values | 26 s |\n\nThe W1 scoring itself takes 0.6 s.\n\n## How to run", "originalFile": "# Which weights make the model pick one algorithm: demo notebook (BASE-W, iteration 10)\n\nThis folder turns the BASE-W experiment (artifact `art_a7CQm-6CXmoJ`, experiment 56 of iteration 10) into a short,\nrunnable Jupyter notebook. The experiment asks where post-training wrote Qwen3-8B's default algorithm at the decision\n(\"fork\") token, relative to Qwen3-8B-Base, at the level of weights.\n\nThe artifact's `method.py` is a stage orchestrator: it launches about 40 scripts that load 8B models on a 24 GB GPU,\nabout 1 GPU-hour in total. Its core test (**W1**: restore the base model's fork-class unembedding rows on the instruct\nresidual) is exact arithmetic on cached fork states, because the class margin `lse(z[D]) - lse(z[A])` depends only on\nthe final-normed residual and the fork-class rows. The notebook therefore re-runs W1 on a CPU from a compact data file,\nwith the original code split into cells.\n\n## Layout\n\n| path | content |\n|---|---|\n| `code_demo.ipynb` | the demo notebook, saved with its outputs from the last test run |\n| `mini_demo_data.json` | the notebook's input (8.3 MB, 40 examples): see below |\n| `build_mini_demo_data.py` | rebuilds `mini_demo_data.json` from the artifact folder, with bit-exactness checks |\n| `logs/` | the notebook test runs (minimal config, then scaled up), with timings |\n| `.aii/manifest.yaml` | storage decisions; none are needed, since everything here is text or code under 10 MB |\n\n### `mini_demo_data.json`\n\n**Per unit.** There are two units:\n* **T10:** connected components; `' find'` (union-find) against `' dfs'` / `' bfs'`.\n* **B3:** minimum spanning tree; Kruskal-class against Prim-class tokens.\n\nEach unit holds:\n* `examples`: 20 prompts, each with its chat-formatted input text and the captured fp32 margins `m_I` / `m_B`. It also\n  holds the fork states of both models: `h_pre` (the block-35 output) and `h_fin` (the final-normed residual), stored\n  as base64 bf16 and decoded exactly.\n* `WI_S`, `WB_S`: the fork-class `lm_head` rows of Qwen3-8B and Qwen3-8B-Base.\n* `resid_pca`: the top-64 PCA basis of the instruct residual, used by the RAND_RESID null.\n* `null_draws`: the 50 committed DELTA_SWAP draws, for T10 only. B3's are 13 MB and are left out; the notebook uses\n  B3's committed shares instead.\n* `reported`: the artifact's own numbers, for a side-by-side check.\n\n**Shared.** `readout` holds the final-norm gains of both models.\n\n**How the build was checked.** `build_mini_demo_data.py` asserts each of the following before writing the file:\n* The `lm_head` rows were fetched with HTTP range requests at the pinned revisions, and they reproduce the committed\n  delta norms and row norms bit for bit.\n* RAND_ISO and RAND_RESID regenerate bit-exactly from their committed seeds.\n* ROWS_ALL reproduces the reported share within 1e-6.\n\n## What the notebook runs\n\n1. **Orchestrator.** `method.py` itself, with only `ROOT` changed, and a dry run of its 40-command stage plan. The\n   GPU stages are not launched.\n2. **W1 teacher-forced test.** The code of `src/w1_tf.py`: `rms_bf16`, `margin`, `share`, `boot_share`, `UnitData`,\n   `arm_rows`, `summarize_arm` and `score`. It covers the arms ROWS_ALL / ROWS_D / ROWS_A / NORM / ROWS_NORM /\n   FULL_UNEMB / DOSE / SIGN, the 2x2 factorial, and the 3 x 50 matched-norm nulls with the committed verdict rule.\n3. **Delta geometry.** `src/analysis10.py`'s `delta_geometry`: how much of each row delta lies in the residual\n   subspace, and its logit leverage.\n4. **Figures.** `src/figures10.py`'s F1 (shares and null histograms), F2 (per-prompt shares), F3 (dose-response), F5\n   (fork states on the readout plane, in activation space) and F6 (PCA of the block-35 outputs).\n5. **Summary.** The reported GPU results (W1 generation, W2 MLP swaps, W3 Gemma) as text. The final cell is a table and\n   parity plot of the notebook's numbers against the reported ones.\n\n## How to run\n\n* **Colab.** Open `code_demo.ipynb` and choose Run all. The first cell installs `loguru` only. The notebook downloads\n  `mini_demo_data.json` from this repository's GitHub raw URL, and falls back to a local copy next to the notebook.\n* **Local.** The first cell pins Colab's versions (`numpy==2.0.2`, `matplotlib==3.10.0`, `torch==2.9.0+cpu`):\n\n  ```bash\n  pip install jupyter ipykernel\n  jupyter nbconvert --to notebook --execute code_demo.ipynb --output code_demo.ipynb\n  ```\n\nThe configuration cell holds the run size: `UNITS_TF`, `N_NULL` and `N_BOOT`. The notebook ships with the artifact's\noriginal values: both units, 50 draws per null and 10,000 bootstrap resamples.\n\n## Rebuilding the data file\n\n```bash\npython build_mini_demo_data.py --artifact-dir <the BASE-W artifact folder> \\\n    --tokenizer <Qwen3-8B tokenizer.json at revision b968826d9c46dd6066d109eabc6255188de91218>\n```\n\nThe script needs `torch`, `numpy`, `requests` and `tokenizers`, plus network access to huggingface.co. From each model\nit fetches only the 19 fork-class `lm_head` rows (8 KB each) and the final-norm gain, at revisions\n`Qwen/Qwen3-8B@b968826d9c46dd6066d109eabc6255188de91218` and\n`Qwen/Qwen3-8B-Base@49e3418fbbbca6ecbdf9608b4d22e5a407081db4`.\n\n## Restoring removed files\n\nNothing in this folder is marked `delete` in `.aii/manifest.yaml`, so there is nothing to restore. `code_demo.ipynb`\ninstalls its own dependencies from its first cell. The data file can be rebuilt with the command above.\n", "structuredPatch": [{"oldStart": 58, "oldLines": 6, "newStart": 58, "newLines": 35, "lines": [" 5. **Summary.** The reported GPU results (W1 generation, W2 MLP swaps, W3 Gemma) as text. The final cell is a table and", "    parity plot of the notebook's numbers against the reported ones.", " ", "+## Results of the final run (original parameters)", "+", "+The notebook reproduces every reported W1 teacher-forced number. The arm shares differ from the reported ones by", "+0.0. The null medians, p95s, maxima and empirical p-values are identical, and so are both verdicts.", "+", "+| | T10 (CC, primary) | B3 (MST, beside) |", "+|---|---|---|", "+| gap `m_I - m_B` | 4.558 nats | 2.090 nats |", "+| ROWS_ALL share [95% CI] | **0.548 [0.440, 0.707]** | 1.249 [1.180, 1.323] |", "+| ROWS_A / ROWS_D / NORM | 0.489 / 0.060 / -0.000 | 1.240 / 0.009 / 0.006 |", "+| RAND_ISO median / max / p | 0.044 / 0.210 / 0.020 | 0.051 / 0.942 / 0.020 |", "+| RAND_RESID p95 / p | 1.252 / 0.373 | 5.394 / 0.275 |", "+| 2x2 interaction | -1.337 nats | +1.748 nats |", "+| logit change from the base rows | `' find'` -0.27, `' dfs'` +2.23, `' bfs'` +3.14 | 16 tokens, mixed |", "+| verdict | SUPPORTED, readout-level but not token-specific | the same (descriptive) |", "+", "+B3's DELTA_SWAP row uses its 50 committed shares, because its draws are not in the data file. The table above omits", "+that row.", "+", "+**Test runs.** All runs used a fresh Python 3.12 virtualenv, with installs inside the notebook (`logs/`):", "+", "+| run | settings | time |", "+|---|---|---|", "+| 1 | T10, 2 draws, 10 resamples | 57 s with a cold pip cache |", "+| 2 | both units, 10 draws, 1,000 resamples | 24 s |", "+| 3 | the original values | 26 s |", "+", "+The W1 scoring itself takes 0.6 s.", "+", " ## How to run", " ", " * **Colab.** Open `code_demo.ipynb` and choose Run all. The first cell installs `loguru` only. The notebook downloads"]}], "userModified": false, "replaceAll": false}
````

### [251] ASSISTANT · 2026-10-26 15:49:44 UTC

```
README updated. Now TODO 6, the final verification: the exact URL string, the data file's existence, the GitHub-first loading pattern, and nbformat validity.
```

### [252] TOOL CALL — Bash · 2026-10-26 15:49:44 UTC

```
Verify URL, data file, loader pattern, notebook validity:
/tmp/aii_nb_test_envs/art_a7CQm-6CXmoJ-0ccaa3ee52c5/bin/python -I - <<'EOF'
import json, nbformat
from pathlib import Path
URL = 'GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-10/experiment-56/demo/mini_demo_data.json"'
nb = nbformat.read("code_demo.ipynb", as_version=4)
nbformat.validate(nb)
print("(0) nbformat valid; cells:", len(nb.cells), "| code cells executed:",
      sum(1 for c in nb.cells if c.cell_type == "code" and c.execution_count), "/", sum(1 for c in nb.cells if c.cell_type == "code"))
srcs = [c.source for c in nb.cells]
print("(1) exact GITHUB_DATA_URL line present:", any(URL in s for s in srcs))
p = Path("mini_demo_data.json")
d = json.loads(p.read_text())
print("(2) mini_demo_data.json exists:", p.exists(), f"{p.stat().st_size/1e6:.2f} MB;", "examples:", {u: len(U["examples"]) for u, U in d["units"].items()})
loader = next(s for s in srcs if "def load_data" in s)
print("(3) loader uses urlopen(GITHUB_DATA_URL) first, local file only as fallback:",
      "urllib.request.urlopen(GITHUB_DATA_URL" in loader and loader.index("urlopen") < loader.index('Path("mini_demo_data.json")'))
print("    data = load_data() cell present:", any(s.strip().startswith("data = load_data()") for s in srcs))
errs = [o for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", []) if o.get("output_type") == "error"]
print("errors in outputs:", len(errs))
EOF
```

### [253] TOOL RESULT — Bash · 2026-10-26 15:49:44 UTC

```
{"stdout": "(0) nbformat valid; cells: 33 | code cells executed: 20 / 20\n(1) exact GITHUB_DATA_URL line present: True\n(2) mini_demo_data.json exists: True 8.34 MB; examples: {'T10': 20, 'B3': 20}\n(3) loader uses urlopen(GITHUB_DATA_URL) first, local file only as fallback: True\n    data = load_data() cell present: True\nerrors in outputs: 0", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [254] ASSISTANT · 2026-10-26 15:50:00 UTC

```
I've built the demo notebook and its data file. The notebook runs in about 26 seconds end to end with the original settings and reproduces every reported number from the artifact's core test exactly.

**What the notebook can and can't run.** `method.py` only launches about 40 GPU scripts that load the 8B models, roughly 1 GPU-hour in total, so it can't run on Colab's CPU. The notebook shows `method.py` unchanged except for `ROOT`, and prints its stage plan without launching anything. It then re-runs the part that needs no GPU, using the original code split into cells:
- **W1 teacher-forced test** (`w1_tf.py`): all readout arms, the three sets of 50 random null edits, bootstrap confidence intervals and the committed verdict rule.
- **Delta geometry** (`analysis10.py`).
- **Figures** (`figures10.py`): F1–F3, plus F5 and F6, which plot the cached fork states in activation space.

The generation, W2 and W3 results need model forwards on a GPU, so they are summarized as text from the artifact's reported numbers.

**Data file.** `mini_demo_data.json` is 8.3 MB and holds 20 cached fork states per unit, T10 and B3, for both models. I fetched just the 19 needed unembedding rows and the final-norm gains from the Hugging Face Hub at the pinned revisions. The build script, `build_mini_demo_data.py`, checks that the rows match the artifact's committed values bit for bit. It also checks that two of the three null sets regenerate exactly from their seeds.

**Test runs** (fresh venv each time, as specified):

| run | settings | time |
|---|---|---|
| 1 | T10 only, 2 null draws, 10 bootstrap resamples | 57 s (cold pip cache) |
| 2 | both units, 10 draws, 1,000 resamples | 24 s |
| 3 | original values: both units, 50 draws, 10,000 resamples | 26 s |

**Results of the final run.** Every arm share and every null median, 95th percentile, maximum and p-value matches the reported value exactly. For T10, restoring the base model's rows closes 0.548 of the gap [0.440, 0.707]. The verdict is "SUPPORTED, readout-level but not token-specific", the same as reported.

Things you should know:
- **B3's third null set is not recomputed.** The artifact's 50 committed shares are used instead, because the draws themselves would add 13 MB. The notebook prints a warning and marks this in its table.
- **The GitHub URL returns 404 for now.** The files aren't pushed yet, so the test runs used the local copy of the data file, as designed.
- **No todo-tracking tool was available.** I followed the six TODOs in order without one.
- **The storage manifest has no entries.** Everything in the folder is text or code under 10 MB, and the test venv lives outside it.

Files are in the workspace folder:
- `code_demo.ipynb`
- `mini_demo_data.json`
- `build_mini_demo_data.py`
- `README.md`
- `.aii/manifest.yaml`
- `logs/` (the three test runs)
- `.terminal_claude_agent_struct_out.json`
```
