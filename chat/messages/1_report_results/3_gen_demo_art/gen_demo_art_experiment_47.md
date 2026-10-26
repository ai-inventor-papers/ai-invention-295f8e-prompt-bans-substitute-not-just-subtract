# gen_demo_art_experiment_47 — report_results

> Phase: `gen_paper_repo` · `gen_demo_art`
> Run: `gen_paper_repo_c164ac661673` — A Random Activation Push Changes a Code Model's Algorithm Where Temperature Does Not
>
> Full, verbatim transcript of this agent task — every system/user prompt, assistant response, thinking block, tool call and tool result — in the order they occurred. Nothing truncated.

## Task: `gen_demo_art_experiment_47` (terminal_claude_agent, claude-opus-5-5)

### [1] CONFIG · 2026-10-26 14:26:52 UTC

```
model: Claude Opus 5.5 | effort: max | permission: bypassPermissions
```

### [2] SYSTEM-USER prompt · 2026-10-26 14:27:10 UTC

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
Your workspace: `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd`

CRITICAL: Every file you create, write, or save MUST be inside this workspace directory (subdirectories OK). You MUST NOT write files anywhere outside this path — external paths are READ-ONLY. Use absolute paths for all file operations.

EVERY file write MUST start with `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd/`:
GOOD: `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd/file.py`, `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd/results/out.json`
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
id: art_cDba8_DycUJd
type: experiment
title: How tuning sharpens a code model's algorithm choice
summary: >-
  Iteration-9 BASE artifact (claims B1-B3), all pre-registered in a sha256 commitment chain and re-derived by an independent
  stdlib script (0 mismatches; placebos fail). B1 (Gemma-3-4b pt vs it on 3 forks; Llama-3.1-8B base vs instruct descriptive):
  instruct models are sharper at the algorithm fork (gains G-GRID 1.78 [1.59, 2.00], G-T04 1.75, G-R6 3.07 and 1.68 nats)
  while ordinary positions barely change (|dH| < 0.5; the instruct token is the base top-1 at 91-97% of phrasing positions);
  but JS at forks is only 0.75-1.18x JS at base-entropy-matched positions (fork ~ high base entropy; Cantarero in/out 11-15x
  reproduced), P1/P3/P4 fail -> verdict PARTIAL. Llama-3.1-8B base chat-token embeddings are untrained (norm ~3e-21 of median),
  so template-free is primary for Llama; L-GRID fails the on-policy rule (descriptive only). B2 (Qwen3-8B vs Qwen3-8B-Base,
  cross-model activation patching at the fork, 20 prompts/unit, fixed batch shapes): on MST the 10 validated fork-stack nodes
  close 1.00 [0.96, 1.04] of the 2.06-nat gap but 50 write-norm-matched random late sets close a median 0.81 (p = 0.45; R-pure
  p = 0.039); on CC the stack closes 0.45 [0.28, 0.57] of a 4.52-nat gap vs random median -0.22 (p = 0.020). Task-spec (SPEC)
  nodes close ~0; late MLPs (L26-35) carry the residual part redundantly; the fine-tuned unembedding alone accounts for 43%
  (MST) / 85% (CC) of the gap (CPU readout decomposition), which is why RS-fork(36) < 1. Committed verdict PARTIAL (Q1 fails
  on CC, Q2 on MST, Q3 holds), localisation 'distributed'. Generation (N=30 CRN slots/arm, frozen labellers + hidden tests):
  on MST one-token FSTACK patch gives 19/30 correct Prim vs 0/30 twin (McNemar 19:0, p=3.8e-6) but a matched random set also
  gives 19/30 (2:2) and FPD (base logits at the fork) 18/30; on CC only FPD moves the choice (18/30 DFS vs 1/30). B3: iteration-8
  MeanCache bug confirmed (None on all held-out COND nodes); with interpolated means the layer-0 condition MLP's held-out
  effect is 3.86 nats ablate (p=0.0625) / 3.85 steer (p=0.023), about half the pair-prompt values; the exp41 value reproduces
  to 0.096 (its engine changed after its rows). Kind-matched motif still differs on COND share. Outputs: method_out.json (370
  examples: b1_forks, b2_tf, b3_heldout, b2_generation), results/*.json per-prompt rows and summaries, figures F1-F8 (incl.
  PCA of actual block-30 residuals), predictions/ commits, README with deviations. Activation caches (cache/, ~12 GB) are
  regenerable and excluded from upload.
workspace_path: >-
  /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50
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
Raw data URL: https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-9/experiment-50/demo/mini_demo_data.json

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
GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-9/experiment-50/demo/mini_demo_data.json"
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
To test-run the notebook in a clean environment (simulating Colab), use the disposable venv at `/tmp/aii_nb_test_envs/art_cDba8_DycUJd-e339753424ba`. It is on this machine's local disk, outside your workspace, which is on a slow network volume: never create a venv inside your workspace.
```bash
UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_cDba8_DycUJd-e339753424ba
UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_cDba8_DycUJd-e339753424ba/bin/python jupyter ipykernel
/tmp/aii_nb_test_envs/art_cDba8_DycUJd-e339753424ba/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb
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
TODO 6. Verify: (1) code_demo.ipynb contains GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-9/experiment-50/demo/mini_demo_data.json" exactly, (2) mini_demo_data.json exists, (3) uses GitHub URL pattern not just open('mini_demo_data.json').
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

### [3] ASSISTANT · 2026-10-26 14:27:36 UTC

```
I'll start by loading the required skills and looking at the workspace and the artifact's files.
```

### [4] TOOL CALL — Skill · 2026-10-26 14:27:36 UTC

```
aii-colab
```

### [5] TOOL CALL — Skill · 2026-10-26 14:27:36 UTC

```
aii-long-running-tasks
```

### [6] TOOL RESULT — Skill · 2026-10-26 14:27:36 UTC

```
{"success": true, "commandName": "aii-colab"}
```

### [7] TOOL RESULT — Skill · 2026-10-26 14:27:36 UTC

```
{"success": true, "commandName": "aii-long-running-tasks"}
```

### [8] TOOL CALL — ToolSearch · 2026-10-26 14:27:36 UTC

```
{'query': 'todo task list tracking', 'max_results': 5}
```

### [9] TOOL RESULT — ToolSearch · 2026-10-26 14:27:36 UTC

```
{"matches": ["CronList", "TaskStop", "EndConversation", "EnterWorktree", "SendMessage"], "query": "todo task list tracking", "total_deferred_tools": 28}
```

### [10] TOOL CALL — Bash · 2026-10-26 14:27:36 UTC

```
List workspace and artifact source directory:
ls -la && ls -la .aii 2>/dev/null; git log --oneline | head -5; echo ---; ls -la /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50 2>&1 | head -80
```

### [11] TOOL RESULT — Bash · 2026-10-26 14:27:36 UTC

```
{"stdout": "total 2983\ndrwxrwxrwx 3 aii-agent aii-agent 1004578 Oct 26 14:27 .\ndrwxrwxrwx 6 aii-agent aii-agent 2000616 Oct 26 14:26 ..\ndrwxrwxrwx 2 aii-agent aii-agent       1 Oct 26 14:26 .aii\n-rw-rw-rw- 1 aii-agent aii-agent      54 Oct 26 14:26 .aii_claude_session.json\n-rw-rw-rw- 1 aii-agent aii-agent   46940 Oct 26 14:27 .repl_agent.ptylog\ntotal 982\ndrwxrwxrwx 2 aii-agent aii-agent       1 Oct 26 14:26 .\ndrwxrwxrwx 3 aii-agent aii-agent 1004578 Oct 26 14:27 ..\nfatal: not a git repository (or any parent up to mount point /ai-inventor)\nStopping at filesystem boundary (GIT_DISCOVERY_ACROSS_FILESYSTEM not set).\n---\ntotal 20640\ndrwxrwxrwx 12 aii-agent aii-agent 2023169 Oct 23 18:04 .\ndrwxrwxrwx  9 aii-agent aii-agent 3000187 Oct 23 11:57 ..\ndrwxrwxrwx  2 aii-agent aii-agent   59900 Oct 23 16:27 .aii\n-rw-rw-rw-  1 aii-agent aii-agent      54 Oct 23 11:58 .aii_claude_session.json\n-rw-rw-rw-  1 aii-agent aii-agent    5943 Oct 23 16:27 .aii_worker_result.json\n-rw-rw-rw-  1 aii-agent aii-agent 1865013 Oct 23 16:27 .repl_agent.ptylog\n-rw-rw-rw-  1 aii-agent aii-agent    3264 Oct 23 15:55 .terminal_claude_agent_struct_out.json\n-rw-rw-rw-  1 aii-agent aii-agent   15180 Oct 23 16:24 README.md\ndrwxrwxrwx  2 aii-agent aii-agent 2001747 Oct 23 18:04 cache\n-rw-rw-rw-  1 aii-agent aii-agent     670 Oct 23 15:30 commitments.log\ndrwxrwxrwx  2 aii-agent aii-agent 1053845 Oct 23 15:36 data\ndrwxrwxrwx  2 aii-agent aii-agent 2000137 Oct 23 15:40 figures\n-rw-rw-rw-  1 aii-agent aii-agent  872997 Oct 23 16:07 full_method_out.json\ndrwxrwxrwx  2 aii-agent aii-agent 1008546 Oct 23 16:14 logs\n-rw-rw-rw-  1 aii-agent aii-agent    4078 Oct 23 15:48 method.py\n-rw-rw-rw-  1 aii-agent aii-agent  771523 Oct 23 16:06 method_out.json\n-rw-rw-rw-  1 aii-agent aii-agent  234693 Oct 23 16:07 mini_method_out.json\ndrwxrwxrwx  2 aii-agent aii-agent 1005722 Oct 23 15:30 predictions\n-rw-rw-rw-  1 aii-agent aii-agent  147833 Oct 23 16:07 preview_method_out.json\n-rw-rw-rw-  1 aii-agent aii-agent    2795 Oct 23 12:01 pyproject.toml\n-rw-rw-rw-  1 aii-agent aii-agent    6484 Oct 23 16:01 reproducibility.md\n-rwxrwxrwx  1 aii-agent aii-agent     824 Oct 23 14:51 restore.sh\ndrwxrwxrwx  3 aii-agent aii-agent 2015052 Oct 23 16:05 results\n-rwxrwxrwx  1 aii-agent aii-agent     423 Oct 23 14:00 run_queue2.sh\n-rwxrwxrwx  1 aii-agent aii-agent     326 Oct 23 13:46 run_qwen.sh\n-rwxrwxrwx  1 aii-agent aii-agent     751 Oct 23 14:03 run_qwen_v2.sh\ndrwxrwxrwx  2 aii-agent aii-agent 1021200 Oct 23 18:04 src\ndrwxrwxrwx  2 aii-agent aii-agent       1 Oct 23 12:01 tests\ndrwxrwxrwx  9 aii-agent aii-agent 2005770 Oct 23 16:15 vendor", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [12] ASSISTANT · 2026-10-26 14:27:45 UTC

```
No todo-tracking tool exists in this session, so I'll keep the 6 TODOs, copied word for word, in a scratchpad file and track progress there. Next I'll read the artifact's code and docs.
```

### [13] TOOL CALL — ToolSearch · 2026-10-26 14:27:45 UTC

```
{'query': 'select:TodoWrite,TaskCreate,NotebookEdit', 'max_results': 5}
```

### [14] TOOL RESULT — ToolSearch · 2026-10-26 14:27:45 UTC

```
{"matches": ["NotebookEdit"], "query": "select:TodoWrite,TaskCreate,NotebookEdit", "total_deferred_tools": 28}
```

### [15] TOOL CALL — Bash · 2026-10-26 14:27:45 UTC

```
Read method.py and list artifact directories:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50; cat $A/method.py; echo ======; ls -la $A/src $A/results $A/data $A/predictions $A/figures $A/tests $A/logs | head -150; echo =====; du -sh $A/* 2>/dev/null
```

### [16] TOOL RESULT — Bash · 2026-10-26 14:27:45 UTC

```
{"stdout": "#!/usr/bin/env python3\n\"\"\"Stage CLI for the iteration-9 BASE artifact (claims B1-B3): where instruction tuning sharpened the algorithm choice.\n\nEvery GPU stage runs in its own process (one model on the GPU at a time). Stages, in the order they were run:\n\n  preflight   hardware record + sha256-checked copies of the read-only inputs (vendor/)      src/s0_preflight.py\n  units       units.json: prompts, openings, fork class tokens (CPU, tokenizers)              src/units9.py\n  tests       CPU unit tests (must pass before COMMIT #0)                                    src/tests_cpu9.py\n  commit0     COMMIT #0: units, node lists, samplers, thresholds, verdict rules              src/commit9.py\n  cache_qwen  B2 s1 (Qwen3-8B capture) + s2 (Qwen3-8B-Base capture, random sets, REV arm)    src/cmap9.py\n  patch_qwen  B2 s3: one-token CMAP sweep, sets, random nulls, RS swaps, SPEC, W arm          src/cmap9.py\n  b3          B3: exp41 reproduction, MeanCache bug, COMMIT B3, interpolated held-out rerun   src/b3_9.py\n  generate    B2 generation (COMMIT #1, TWIN/FSTACK/RAND/FPD x 30 CRN slots), labels, tests   src/b2gen9.py\n  b1          B1: Gemma-3-4b it/pt and Llama-3.1-8B instruct/base teacher-forced forks       src/b1_9.py\n  commit0b    sha256 of analysis9.py before any verdict                                      src/commit9.py\n  analyze     committed B1/B2 rules, B3 statistics, summaries                                src/{b1_9,b3_9,analysis9}.py\n  figures     F1-F8 (PDF + PNG)                                                              src/figures9.py\n  positioning dated literature verdicts                                                      src/positioning9.py\n  rederive    stdlib re-derivation of every headline number + placebos                       src/rederive9.py\n  outputs     method_out.json (exp_gen_sol_out)                                              src/outputs9.py\n\nUsage: uv run method.py --stages all | --stages b1,analyze,figures\n\"\"\"\n\nfrom __future__ import annotations\n\nimport argparse\nimport subprocess\nimport sys\nimport time\nfrom pathlib import Path\n\nfrom loguru import logger\n\nROOT = Path(__file__).resolve().parent\nSRC = ROOT / \"src\"\nPY = sys.executable\n\nSTAGES: dict[str, list[list[str]]] = {\n    \"preflight\": [[\"s0_preflight.py\"]],\n    \"units\": [[\"units9.py\"]],\n    \"tests\": [[\"tests_cpu9.py\"]],\n    \"commit0\": [[\"commit9.py\", \"commit0\"]],\n    \"cache_qwen\": [[\"cmap9.py\", \"s1\", \"all\"], [\"cmap9.py\", \"s2\", \"all\"]],\n    \"patch_qwen\": [[\"cmap9.py\", \"s3\", \"all\"]],\n    \"b3\": [[\"b3_9.py\", \"gpu\"]],\n    \"b1\": [[\"b1_9.py\", \"gpu\", m] for m in (\"gemma\", \"gemma_pt\", \"llama\", \"llama_base\")],\n    \"commit0b\": [[\"commit9.py\", \"commit0b\"]],\n    \"analyze\": [[\"b1_9.py\", \"analyze\"], [\"b3_9.py\", \"analyze\"], [\"analysis9.py\"]],\n    \"generate\": [[\"b2gen9.py\", \"gpu\"], [\"b2gen9.py\", \"label\"], [\"b2gen9.py\", \"analyze\"]],\n    \"figures\": [[\"figures9.py\"]],\n    \"positioning\": [[\"positioning9.py\"]],\n    \"rederive\": [[\"rederive9.py\"]],\n    \"outputs\": [[\"outputs9.py\"]],\n}\nORDER = list(STAGES)\n\n\n@logger.catch(reraise=True)\ndef main() -> None:\n    logger.remove()\n    logger.add(sys.stdout, level=\"INFO\", format=\"{time:HH:mm:ss}|{level:<7}|{message}\")\n    (ROOT / \"logs\").mkdir(exist_ok=True)\n    logger.add(str(ROOT / \"logs\" / \"method.log\"), rotation=\"30 MB\", level=\"DEBUG\")\n    ap = argparse.ArgumentParser()\n    ap.add_argument(\"--stages\", default=\"all\", help=\"comma-separated stage names or 'all'\")\n    args = ap.parse_args()\n    todo = ORDER if args.stages == \"all\" else [s.strip() for s in args.stages.split(\",\")]\n    for s in todo:\n        if s not in STAGES:\n            raise ValueError(f\"unknown stage {s}; known: {ORDER}\")\n    for s in todo:\n        for cmd in STAGES[s]:\n            t0 = time.time()\n            logger.info(f\"stage {s}: {' '.join(cmd)}\")\n            r = subprocess.run([PY, *cmd], cwd=SRC)\n            if r.returncode != 0:\n                raise RuntimeError(f\"stage {s} failed: {' '.join(cmd)} (exit {r.returncode})\")\n            logger.info(f\"stage {s}: done in {time.time() - t0:.0f}s\")\n\n\nif __name__ == \"__main__\":\n    main()\n======\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50/data:\ntotal 3545\ndrwxrwxrwx  2 aii-agent aii-agent 1053845 Oct 23 15:36 .\ndrwxrwxrwx 12 aii-agent aii-agent 2023169 Oct 23 18:04 ..\n-rw-rw-rw-  1 aii-agent aii-agent  244526 Oct 23 15:36 labels_gen.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent  306855 Oct 23 15:33 samples.jsonl\n\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50/figures:\ntotal 5339\ndrwxrwxrwx  2 aii-agent aii-agent 2000137 Oct 23 15:40 .\ndrwxrwxrwx 12 aii-agent aii-agent 2023169 Oct 23 18:04 ..\n-rw-rw-rw-  1 aii-agent aii-agent   27042 Oct 23 15:40 F1_b1_margins.pdf\n-rw-rw-rw-  1 aii-agent aii-agent  157548 Oct 23 15:40 F1_b1_margins.png\n-rw-rw-rw-  1 aii-agent aii-agent   15744 Oct 23 15:40 F2_b1_js_controls.pdf\n-rw-rw-rw-  1 aii-agent aii-agent   83886 Oct 23 15:40 F2_b1_js_controls.png\n-rw-rw-rw-  1 aii-agent aii-agent   58774 Oct 23 15:40 F3_b2_singles_by_layer.pdf\n-rw-rw-rw-  1 aii-agent aii-agent  257864 Oct 23 15:40 F3_b2_singles_by_layer.png\n-rw-rw-rw-  1 aii-agent aii-agent   23287 Oct 23 15:40 F4_b2_residual_swaps.pdf\n-rw-rw-rw-  1 aii-agent aii-agent  222175 Oct 23 15:40 F4_b2_residual_swaps.png\n-rw-rw-rw-  1 aii-agent aii-agent   17681 Oct 23 15:40 F5_b2_random_null.pdf\n-rw-rw-rw-  1 aii-agent aii-agent   97439 Oct 23 15:40 F5_b2_random_null.png\n-rw-rw-rw-  1 aii-agent aii-agent   18364 Oct 23 15:40 F6_b2_generation.pdf\n-rw-rw-rw-  1 aii-agent aii-agent  115415 Oct 23 15:40 F6_b2_generation.png\n-rw-rw-rw-  1 aii-agent aii-agent   21053 Oct 23 15:40 F7_b3_heldout.pdf\n-rw-rw-rw-  1 aii-agent aii-agent   99745 Oct 23 15:40 F7_b3_heldout.png\n-rw-rw-rw-  1 aii-agent aii-agent   34834 Oct 23 15:40 F8_b2_geometry_pca.pdf\n-rw-rw-rw-  1 aii-agent aii-agent  189248 Oct 23 15:40 F8_b2_geometry_pca.png\n\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50/logs:\ntotal 3055\ndrwxrwxrwx  2 aii-agent aii-agent 1008546 Oct 23 16:14 .\ndrwxrwxrwx 12 aii-agent aii-agent 2023169 Oct 23 18:04 ..\n-rw-rw-rw-  1 aii-agent aii-agent     252 Oct 23 15:51 analysis9.log\n-rw-rw-rw-  1 aii-agent aii-agent       0 Oct 23 15:51 analysis9_summary.log\n-rw-rw-rw-  1 aii-agent aii-agent     689 Oct 23 15:51 b1_9_analyze.log\n-rw-rw-rw-  1 aii-agent aii-agent     547 Oct 23 15:51 b1_9_gpu_gemma.log\n-rw-rw-rw-  1 aii-agent aii-agent     568 Oct 23 15:51 b1_9_gpu_gemma_pt.log\n-rw-rw-rw-  1 aii-agent aii-agent     303 Oct 23 15:51 b1_9_gpu_llama.log\n-rw-rw-rw-  1 aii-agent aii-agent     758 Oct 23 15:51 b1_9_gpu_llama_base.log\n-rw-rw-rw-  1 aii-agent aii-agent     589 Oct 23 15:51 b2gen9_analyze.log\n-rw-rw-rw-  1 aii-agent aii-agent    3971 Oct 23 15:51 b2gen9_gpu.log\n-rw-rw-rw-  1 aii-agent aii-agent       0 Oct 23 15:51 b2gen9_label.log\n-rw-rw-rw-  1 aii-agent aii-agent       0 Oct 23 15:51 b3_9_analyze.log\n-rw-rw-rw-  1 aii-agent aii-agent    2157 Oct 23 15:51 b3_9_gpu.log\n-rw-rw-rw-  1 aii-agent aii-agent    2122 Oct 23 15:51 cmap9_s1.log\n-rw-rw-rw-  1 aii-agent aii-agent    2589 Oct 23 15:51 cmap9_s2.log\n-rw-rw-rw-  1 aii-agent aii-agent   16953 Oct 23 15:51 cmap9_s3.log\n-rw-rw-rw-  1 aii-agent aii-agent     377 Oct 23 15:51 commit9.log\n-rw-rw-rw-  1 aii-agent aii-agent    4671 Oct 23 15:51 download.log\n-rw-rw-rw-  1 aii-agent aii-agent    1784 Oct 23 15:51 figures9.log\n-rw-rw-rw-  1 aii-agent aii-agent    1692 Oct 23 15:51 method.log\n-rw-rw-rw-  1 aii-agent aii-agent    1143 Oct 23 16:06 outputs9.log\n-rw-rw-rw-  1 aii-agent aii-agent    4297 Oct 23 15:51 run_gen.out\n-rw-rw-rw-  1 aii-agent aii-agent    5875 Oct 23 15:51 run_queue2.out\n-rw-rw-rw-  1 aii-agent aii-agent    8495 Oct 23 15:51 run_qwen.out\n-rw-rw-rw-  1 aii-agent aii-agent    4608 Oct 23 15:51 run_qwen_v2.out\n-rw-rw-rw-  1 aii-agent aii-agent    7191 Oct 23 15:51 run_s3_v2.out\n-rw-rw-rw-  1 aii-agent aii-agent    6490 Oct 23 16:02 run_weightdiff.out\n-rw-rw-rw-  1 aii-agent aii-agent     370 Oct 23 15:51 s0_preflight.log\n-rw-rw-rw-  1 aii-agent aii-agent      93 Oct 23 16:15 s0_vendor_update.log\n-rw-rw-rw-  1 aii-agent aii-agent      80 Oct 23 15:51 tests_cpu9.log\n-rw-rw-rw-  1 aii-agent aii-agent     922 Oct 23 15:51 units9.log\n-rw-rw-rw-  1 aii-agent aii-agent    7933 Oct 23 16:02 weightdiff9.log\n\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50/predictions:\ntotal 3017\ndrwxrwxrwx  2 aii-agent aii-agent 1005722 Oct 23 15:30 .\ndrwxrwxrwx 12 aii-agent aii-agent 2023169 Oct 23 18:04 ..\n-rw-rw-rw-  1 aii-agent aii-agent   19016 Oct 23 13:36 commit0.json\n-rw-rw-rw-  1 aii-agent aii-agent    4366 Oct 23 14:18 commit0b.json\n-rw-rw-rw-  1 aii-agent aii-agent   32723 Oct 23 15:30 commit1_gen.json\n-rw-rw-rw-  1 aii-agent aii-agent    1281 Oct 23 14:04 commitB3.json\n-rw-rw-rw-  1 aii-agent aii-agent     229 Oct 23 13:06 hardware.json\n-rw-rw-rw-  1 aii-agent aii-agent     984 Oct 23 12:21 model_revisions.json\n\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50/results:\ntotal 132145\ndrwxrwxrwx  3 aii-agent aii-agent  2015052 Oct 23 16:05 .\ndrwxrwxrwx 12 aii-agent aii-agent  2023169 Oct 23 18:04 ..\n-rw-rw-rw-  1 aii-agent aii-agent     8406 Oct 23 14:32 b1_gemma_G-GRID.json\n-rw-rw-rw-  1 aii-agent aii-agent     9867 Oct 23 14:32 b1_gemma_G-R6.json\n-rw-rw-rw-  1 aii-agent aii-agent     5211 Oct 23 14:32 b1_gemma_G-T04.json\n-rw-rw-rw-  1 aii-agent aii-agent    10376 Oct 23 14:32 b1_llama_L-GRID.json\n-rw-rw-rw-  1 aii-agent aii-agent    39031 Oct 23 14:32 b1_summary.json\n-rw-rw-rw-  1 aii-agent aii-agent 31328541 Oct 23 14:21 b1_tf_gemma.json\n-rw-rw-rw-  1 aii-agent aii-agent 41519658 Oct 23 14:23 b1_tf_gemma_pt.json\n-rw-rw-rw-  1 aii-agent aii-agent 12606788 Oct 23 14:26 b1_tf_llama.json\n-rw-rw-rw-  1 aii-agent aii-agent 13656233 Oct 23 14:29 b1_tf_llama_base.json\n-rw-rw-rw-  1 aii-agent aii-agent     9503 Oct 23 15:36 b2_generation.json\n-rw-rw-rw-  1 aii-agent aii-agent   123097 Oct 23 14:34 b2_rev_B3.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent   122377 Oct 23 14:35 b2_rev_T10.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent   159578 Oct 23 14:56 b2_summary.json\n-rw-rw-rw-  1 aii-agent aii-agent 13734313 Oct 23 14:50 b2_tf_B3.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent 13642323 Oct 23 14:53 b2_tf_T10.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent     2138 Oct 23 14:18 b3_gpu.json\n-rw-rw-rw-  1 aii-agent aii-agent   451707 Oct 23 14:18 b3_heldout_rows.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent    18196 Oct 23 14:24 b3_summary.json\n-rw-rw-rw-  1 aii-agent aii-agent   271167 Oct 23 14:34 capture_base.json\n-rw-rw-rw-  1 aii-agent aii-agent   280687 Oct 23 14:31 capture_instr.json\n-rw-rw-rw-  1 aii-agent aii-agent     5793 Oct 23 15:42 deviations.json\n-rw-rw-rw-  1 aii-agent aii-agent      965 Oct 23 14:51 gpu_tests_b2.json\n-rw-rw-rw-  1 aii-agent aii-agent     4685 Oct 23 14:49 positioning.json\n-rw-rw-rw-  1 aii-agent aii-agent   140208 Oct 23 14:35 random_sets.json\n-rw-rw-rw-  1 aii-agent aii-agent     7008 Oct 23 15:57 rederive.json\n-rw-rw-rw-  1 aii-agent aii-agent    27962 Oct 23 13:54 spec_random_sets_B3.json\n-rw-rw-rw-  1 aii-agent aii-agent    28292 Oct 23 13:57 spec_random_sets_T10.json\n-rw-rw-rw-  1 aii-agent aii-agent     1106 Oct 23 15:33 stage_timing.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent   230435 Oct 23 16:05 summary.json\n-rw-rw-rw-  1 aii-agent aii-agent     1106 Oct 23 13:36 tests_cpu.json\n-rw-rw-rw-  1 aii-agent aii-agent   807624 Oct 23 13:15 units.json\ndrwxrwxrwx  2 aii-agent aii-agent  2002724 Oct 23 14:29 v1_variable_batch\n-rw-rw-rw-  1 aii-agent aii-agent     9928 Oct 23 16:02 weight_change.json\n\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50/src:\ntotal 3191\ndrwxrwxrwx  2 aii-agent aii-agent 1021200 Oct 23 18:04 .\ndrwxrwxrwx 12 aii-agent aii-agent 2023169 Oct 23 18:04 ..\n-rw-rw-rw-  1 aii-agent aii-agent   14698 Oct 23 14:07 analysis9.py\n-rw-rw-rw-  1 aii-agent aii-agent   22565 Oct 23 14:31 b1_9.py\n-rw-rw-rw-  1 aii-agent aii-agent   15686 Oct 23 15:26 b2gen9.py\n-rw-rw-rw-  1 aii-agent aii-agent   16628 Oct 23 13:53 b3_9.py\n-rw-rw-rw-  1 aii-agent aii-agent   12456 Oct 23 15:51 cfg9.py\n-rw-rw-rw-  1 aii-agent aii-agent   47631 Oct 23 14:44 cmap9.py\n-rw-rw-rw-  1 aii-agent aii-agent    5578 Oct 23 13:33 commit9.py\n-rw-rw-rw-  1 aii-agent aii-agent    1903 Oct 23 12:13 download_models.py\n-rw-rw-rw-  1 aii-agent aii-agent   14050 Oct 23 15:39 figures9.py\n-rw-rw-rw-  1 aii-agent aii-agent    3339 Oct 23 13:31 meancache_aligned.py\n-rw-rw-rw-  1 aii-agent aii-agent   12510 Oct 23 16:01 outputs9.py\n-rw-rw-rw-  1 aii-agent aii-agent    5673 Oct 23 14:48 positioning9.py\n-rw-rw-rw-  1 aii-agent aii-agent   12326 Oct 23 15:57 rederive9.py\n-rw-rw-rw-  1 aii-agent aii-agent    4791 Oct 23 16:14 s0_preflight.py\n-rw-rw-rw-  1 aii-agent aii-agent    4641 Oct 23 13:27 stats9.py\n-rw-rw-rw-  1 aii-agent aii-agent    4982 Oct 23 13:29 tests_cpu9.py\n-rw-rw-rw-  1 aii-agent aii-agent   13989 Oct 23 13:11 units9.py\n-rw-rw-rw-  1 aii-agent aii-agent    3650 Oct 23 16:00 weightdiff9.py\n\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50/tests:\ntotal 1977\ndrwxrwxrwx  2 aii-agent aii-agent       1 Oct 23 12:01 .\ndrwxrwxrwx 12 aii-agent aii-agent 2023169 Oct 23 18:04 ..\n=====\n15K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50/README.md\n20M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50/cache\n1.0K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50/commitments.log\n1.6M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50/data\n3.3M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50/figures\n853K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50/full_method_out.json\n1.1M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50/logs\n4.0K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50/method.py\n754K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50/method_out.json\n230K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50/mini_method_out.json\n1.1M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50/predictions\n145K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50/preview_method_out.json\n3.0K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50/pyproject.toml\n6.5K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50/reproducibility.md\n1.0K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50/restore.sh\n155M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50/results\n512\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50/run_queue2.sh\n512\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50/run_qwen.sh\n1.0K\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50/run_qwen_v2.sh\n1.2M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50/src\n512\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50/tests\n161M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50/vendor", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [17] ASSISTANT · 2026-10-26 14:28:01 UTC

```
NotebookEdit is available, but there is no todo tool, so I'll record the TODOs in a scratchpad file. Next I'll read the artifact README, the reproducibility notes and the shape of the output files.
```

### [18] TOOL CALL — Bash · 2026-10-26 14:28:01 UTC

```
Save todo list; read artifact README and docs:
mkdir -p "/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad" && cat > "/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/todos.md" <<'EOF'
# TODO list (copied verbatim; no todo tool available in this session)
- [ ] TODO 1. Read and STRICTLY follow these skills: aii-colab, aii-long-running-tasks.
- [ ] TODO 2. Read demo file and relevant preview_* files (preview only). Understand script structure: imports, setup, processing, output. Identify ALL tunable parameters (iterations, epochs, n_samples, hidden_size, batch_size, etc.) — these go in the config cell.
- [ ] TODO 3. Create `mini_demo_data.json`: curated subset from at most ONE dataset (no more than 100 diverse examples). CRITICAL: do NOT read/grep full output file — may crash. Use `head -c 5000` or stream first entries with Python to pick examples.
- [ ] TODO 4. Create `code_demo.ipynb` via NotebookEdit following <notebook_structure>. Set ALL config parameters to ABSOLUTE MINIMUM values — the smallest that produce any output (e.g. 1 iteration, 2 samples, smallest array sizes). Test-run using <test_environment>. Fix all errors until it passes.
- [ ] TODO 5. GRADUALLY SCALE (but don't overdo it): increase config params step by step (e.g. ~2x each round). After each increase: test-run, record runtime, fix errors. STOP SCALING as soon as results look meaningful — a working small-scale demo beats a failed large-scale one. If full original params fit within <max_notebook_total_runtime> (10% margin), use them. Otherwise keep whatever works and comment out the true original values. Do NOT spend more than 2-3 scaling rounds.
- [ ] TODO 6. Verify: (1) code_demo.ipynb contains GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-9/experiment-50/demo/mini_demo_data.json" exactly, (2) mini_demo_data.json exists, (3) uses GitHub URL pattern not just open('mini_demo_data.json').
EOF
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50; cat $A/README.md; echo =====; cat $A/reproducibility.md; echo ====; cat $A/pyproject.toml; echo ===; cat $A/restore.sh; cat $A/.terminal_claude_agent_struct_out.json | head -c 3500
```

### [19] TOOL RESULT — Bash · 2026-10-26 14:28:01 UTC

```
{"stdout": "# Where tuning sharpened the algorithm choice (iteration 9, claims B1-B3)\n\nThis artifact tests the run's question \"does an LLM give the mean answer?\" at the **single decision token where a\ncode model picks its algorithm** (the *fork*). It compares base and instruction-tuned models on identical token ids\nand asks three things:\n\n* **B1** (behavioural, teacher-forced): how much sharper is the instruct model at the fork than its base, in two new\n  families (Ge... [truncated, 29255 chars total]
```

### [20] THINKING · 2026-10-26 14:28:27 UTC

```
The core logic is in `src/*.py`, with `method.py` just dispatching stages. Next I'll inspect the preview file for the output data structure and list what each src module defines.
```

### [21] TOOL CALL — Bash · 2026-10-26 14:28:27 UTC

```
Inspect preview output structure per dataset:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50; cd /tmp && python3 -I - "$A/preview_method_out.json" <<'EOF'
import json,sys
d=json.load(open(sys.argv[1]))
print(type(d), list(d.keys()) if isinstance(d,dict) else len(d))
for k,v in d.items():
    if k!='datasets': print(k, '->', (json.dumps(v)[:1500]))
for ds in d.get('datasets',[]):
    print('=== dataset', ds.get('dataset'), 'n=',len(ds.get('examples',[])), 'keys', [k for k in ds if k!='examples'])
    ex=ds['examples'][0]
    for kk,vv in ex.items():
        s=json.dumps(vv) if not isinstance(vv,str) else vv
        print('   ',kk,':',s[:700])
EOF
```

### [22] TOOL RESULT — Bash · 2026-10-26 14:28:27 UTC

```
{"stdout": "<class 'dict'> ['metadata', 'datasets']\nmetadata -> {\"artifact\": \"iteration-9 BASE artifact (claims B1-B3): where instruction tuning sharpened the algorithm choice\", \"method_name\": \"teacher-forced base-vs-instruct fork margins (B1); cross-model activation patching at the fork with matched random nulls and residual swaps (B2); interpolated-mean held-out rerun (B3)\", \"baselines\": [\"both unpatched anchors (instruct, base) on identical ids\", \"50 write-norm-matched random component sets (R, R-pure, R-scaled)\", \"exhaustive single-component sweep (36 MLPs + 1152 heads)\"], \"models\": {\"qwen\": {\"id\": \"Qwen/Qwen3-8B\", \"revision\": \"b968826d9c46dd6066d109eabc6255188de91218\"}, \"qwen_base\": {\"id\": \"Qwen/Qwen3-8B-Base\", \"revision\": \"49e3418fbbbca6ecbdf9608b4d22e5a407081db4\"}, \"gemma\": {\"id\": \"google/gemma-3-4b-it\", \"revision\": \"093f9f388b31de276ce2de164bdc2081324b9767\"}, \"gemma_pt\": {\"id\": \"google/gemma-3-4b-pt\", \"revision\": \"cc012e0a6d0787b4adcc0fa2c4da74402494554d\"}, \"llama\": {\"id\": \"meta-llama/Llama-3.1-8B-Instruct\", \"revision\": \"0e9e39f249a16976918f6564b8830bc894c89659\"}, \"llama_base\": {\"id\": \"meta-llama/Llama-3.1-8B\", \"revision\": \"d04e592bb4f6aa9cfee91e2e20afa771667e1d4b\"}}, \"b1\": {\"units\": {\"G-GRID\": {\"family\": \"gemma\", \"unit\": \"G-GRID\", \"forks\": {\"G-GRID@32\": {\"chat\": {\"margin_instr\": [1.3819992138915804, 1.1137155279291369, 1.4728604347613907], \"margin_base\": [-0.9711638093511936, -0.9711638093511936, -1.0052271204284213], \"gain\": [2.3531630232427743, 2.0848793372803307, 2.478087555189812], \"gain_mean\": 1.7840351517264985, \"gain_ci95\"\n=== dataset b1_forks n= 3 keys ['dataset']\n    input : <bos><start_of_turn>user\nDo not use house for this task. . . . . . .\n\nTask: write a Python function solve(grid, start, goal) that finds a path between two cells of a grid. grid is a list of equal-leng...\n    output : visited\n    predict_instruct_argmax : visited\n    predict_base_argmax : queue\n    metadata_family : gemma\n    metadata_unit : G-GRID\n    metadata_fork_id : G-GRID@32\n    metadata_prompt_id : W1|house\n    metadata_template_mode : chat\n    metadata_on_policy_kept : true\n    metadata_descriptive_only : false\n    metadata_D_tokens : [\"visited\"]\n    metadata_A_tokens : [\"\\n\", \"if\", \"queue\"]\n    metadata_margin_instr : 1.3819992138915804\n    metadata_margin_base : -0.9711638093511936\n    metadata_gain : 2.3531630232427743\n    metadata_pD_instr : 0.7992953925806641\n    metadata_pD_base : 0.09218436537429323\n    metadata_pA_instr : 0.2006839668385785\n    metadata_pA_base : 0.2434604125691861\n    metadata_entropy_instr : 0.7119141630192787\n    metadata_entropy_base : 3.3890677863699543\n    metadata_logp_opening_instr : -0.16316389735598935\n    metadata_models : [\"google/gemma-3-4b-it\", \"google/gemma-3-4b-pt\"]\n=== dataset b2_tf n= 3 keys ['dataset']\n    input : <|im_start|>user\nDo not use guy for this task. . . . .\n\nTask: write a Python function solve(n, roads) that returns the smallest total cost of a choice of roads that links all cities. There are n citie...\n    output :  Kr\n    predict_instruct_unpatched :  Kr\n    predict_FSTACK_patched :  Prim\n    predict_median_random_set_patched :  Prim\n    predict_RSfork36_patched :  D\n    predict_base_model :  Prim\n    metadata_unit : B3\n    metadata_prompt_id : W1|guy\n    metadata_template : W1\n    metadata_D_tokens : [\" Kr\", \" Union\", \" Check\"]\n    metadata_A_tokens : [\" Prim\", \" Pr\", \" Use\"]\n    metadata_m_I : 1.2982978820800781\n    metadata_m_B : -0.8064613342285156\n    metadata_gap : 2.1047592163085938\n    metadata_m_FSTACK : -0.8488121032714844\n    metadata_share_FSTACK : 1.020121431807884\n    metadata_share_F_MLP : 1.1169986406887178\n    metadata_share_F_HEAD : 0.19558676937018576\n    metadata_share_F_MST : 0.7731889442682375\n    metadata_share_F_CC : 1.1332270049841413\n    metadata_share_SPEC : -0.11289352061622111\n    metadata_share_RSfork23 : 0.7235487086542818\n    metadata_share_RSfork36 : 0.5778830992297236\n    metadata_share_RSprefix23 : 0.5532306298142274\n    metadata_share_RSall23 : 1.2343525147258723\n    metadata_share_W_all : 0.2725709107385591\n    metadata_share_median_random_set : 0.8516139555958314\n    metadata_share_random_sets : [1.2382782057091073, 0.2275269596737653, 1.4565709107385592]\n    metadata_self_patch_dm : -0.057575225830078125\n    metadata_identity_heads_minus_RS36 : -0.007236480712890625\n=== dataset b3_heldout n= 3 keys ['dataset']\n    input : C1forced held-out prompt F11|forced|pad (art_18XvfcJJZi1O k3prompts.b3_forced) + the 61-token MST opening; edit ablate of mlp|L0|H-1|COND (aligned means)\n    output : clean\n    predict_node_oriented_dm : -0.155174\n    predict_random_mean_oriented_dm : -0.043762\n    metadata_node : mlp|L0|H-1|COND\n    metadata_mode : ablate\n    metadata_variant : aligned\n    metadata_prompt : F11|forced|pad\n    metadata_d : -0.11141250610351563\n    metadata_frac_random_beaten : 0.0\n    metadata_label : committed", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [23] ASSISTANT · 2026-10-26 14:28:35 UTC

```
Next I'll read the source modules, starting with the config, statistics, analysis and re-derivation code that the CPU stages use.
```

### [24] TOOL CALL — Bash · 2026-10-26 14:28:35 UTC

```
Read cfg9.py:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50; cat -n $A/src/cfg9.py
```

### [25] TOOL RESULT — Bash · 2026-10-26 14:28:35 UTC

```
{"stdout": "     1\t#!/usr/bin/env python3\n     2\t\"\"\"Iteration-9 BASE artifact (claims B1-B3) constants and utilities.\n     3\t\n     4\tB1  base vs instruct teacher-forced at counterfactually located forks (Gemma-3-4b pt/it, Llama-3.1-8B base/instruct).\n     5\tB2  cross-model activation patching (CMAP) in Qwen3-8B: base-model component outputs patched into the instruct model at\n     6\t    the fork position; validated fork-stack (FSTACK) vs an exhaustive single-component sweep, 50 write-norm-matched\n     7\t    random sets, the task-specification nodes and residual-stream swaps (upper bounds / localisation).\n     8\tB3  rerun of iteration 8's held-out condition-node validation with an interpolating MeanCache.\n     9\t\n    10\tConventions:\n    11\t- Fork position = the LAST input position (prompt + opening); its logits choose the decision token.\n    12\t- Margin m = logsumexp(logits[D]) - logsumexp(logits[A]) in fp32 from the bf16 final-norm hidden state (D = the\n    13\t  instruct model's default class tokens, A = the alternative class), i.e. log P(D) - log P(A) at T 1.\n    14\t- share(X) = sum_p (m_I,p - m_X,p) / sum_p (m_I,p - m_B,p): the share of the instruct-minus-base margin gap that patching\n    15\t  the base outputs of X into the instruct run closes (ratio of sums; the mean of per-prompt ratios is reported beside it).\n    16\t\"\"\"\n    17\t\n    18\tfrom __future__ import annotations\n    19\t\n    20\timport hashlib\n    21\timport json\n    22\timport math\n    23\timport os\n    24\timport resource\n    25\timport sys\n    26\tfrom datetime import datetime, timezone\n    27\tfrom pathlib import Path\n    28\tfrom typing import Any, Iterable\n    29\t\n    30\timport numpy as np\n    31\tfrom loguru import logger\n    32\t\n    33\tROOT = Path(__file__).resolve().parents[1]\n    34\tSRC = ROOT / \"src\"\n    35\tVENDOR = ROOT / \"vendor\"\n    36\tDATA_DIR = ROOT / \"data\"\n    37\tRESULTS_DIR = ROOT / \"results\"\n    38\tFIG_DIR = ROOT / \"figures\"\n    39\tLOG_DIR = ROOT / \"logs\"\n    40\tPRED_DIR = ROOT / \"predictions\"\n    41\tCACHE_DIR = ROOT / \"cache\"\n    42\tfor _d in (DATA_DIR, RESULTS_DIR, FIG_DIR, LOG_DIR, PRED_DIR, CACHE_DIR):\n    43\t    _d.mkdir(parents=True, exist_ok=True)\n    44\tCOMMITS = ROOT / \"commitments.log\"\n    45\tGENESIS = hashlib.sha256(b\"iter9_base\").hexdigest()\n    46\t\n    47\t# read-only prior artifacts on the run volume (copied into vendor/<artifact id>/ with sha256 by s0_preflight.py)\n    48\tRUN = ROOT.parents[3]\n    49\tITER = RUN / \"3_invention_loop\"\n    50\tSRCS = {\n    51\t    \"art_18XvfcJJZi1O\": ITER / \"iter_8\" / \"gen_art\" / \"gen_art_experiment_41\",\n    52\t    \"art_lzuosbrb34wB\": ITER / \"iter_8\" / \"gen_art\" / \"gen_art_experiment_43\",\n    53\t    \"art_MZAfDPVhM6Ui\": ITER / \"iter_7\" / \"gen_art\" / \"gen_art_experiment_35\",\n    54\t    \"art_pHL7LWNhpcCS\": ITER / \"iter_7\" / \"gen_art\" / \"gen_art_experiment_34\",\n    55\t    \"art_vnyi0Fm5SyNH\": ITER / \"iter_8\" / \"gen_art\" / \"gen_art_experiment_39\",\n    56\t    \"art_rMlbrjVB1c__\": ITER / \"iter_6\" / \"gen_art\" / \"gen_art_experiment_30\",\n    57\t    \"art_zNyBP6zieI5u\": ITER / \"iter_6\" / \"gen_art\" / \"gen_art_experiment_31\",\n    58\t    \"art_FJMIE9T9_PMv\": ITER / \"iter_8\" / \"gen_art\" / \"gen_art_experiment_42\",\n    59\t    \"exp38\": ITER / \"iter_7\" / \"gen_art\" / \"gen_art_experiment_38\",\n    60\t    \"art_j3Rm_lr2nzR6\": RUN.parent / \"run_4VFKidE1bxPG\" / \"3_invention_loop\" / \"iter_1\" / \"gen_art\" / \"gen_art_dataset_1\",\n    61\t}\n    62\t# portable resolution of every source artifact: ART_<ID>_DIR env var, else the published sibling folder ../<id>,\n    63\t# else the original run layout above (only s0_preflight.py reads these; everything else reads vendor/)\n    64\tfor _k in list(SRCS):\n    65\t    _env = os.environ.get(f\"ART_{_k.upper()}_DIR\")\n    66\t    if _env:\n    67\t        SRCS[_k] = Path(_env)\n    68\t    elif (ROOT.parent / _k).exists():\n    69\t        SRCS[_k] = ROOT.parent / _k\n    70\tV41 = VENDOR / \"art_18XvfcJJZi1O\"\n    71\tV43 = VENDOR / \"art_lzuosbrb34wB\"\n    72\tV35 = VENDOR / \"art_MZAfDPVhM6Ui\"\n    73\tV31 = VENDOR / \"art_zNyBP6zieI5u\"\n    74\tV42 = VENDOR / \"art_FJMIE9T9_PMv\"\n    75\tV38 = VENDOR / \"exp38\"\n    76\t\n    77\t# ------------------------------------------------------------------------------------------------ models\n    78\tMODELS = {\n    79\t    \"qwen\": (\"Qwen/Qwen3-8B\", \"b968826d9c46dd6066d109eabc6255188de91218\"),\n    80\t    \"qwen_base\": (\"Qwen/Qwen3-8B-Base\", \"49e3418fbbbca6ecbdf9608b4d22e5a407081db4\"),\n    81\t    \"gemma\": (\"google/gemma-3-4b-it\", \"093f9f388b31de276ce2de164bdc2081324b9767\"),\n    82\t    \"gemma_pt\": (\"google/gemma-3-4b-pt\", \"cc012e0a6d0787b4adcc0fa2c4da74402494554d\"),\n    83\t    \"llama\": (\"meta-llama/Llama-3.1-8B-Instruct\", \"0e9e39f249a16976918f6564b8830bc894c89659\"),\n    84\t    \"llama_base\": (\"meta-llama/Llama-3.1-8B\", \"d04e592bb4f6aa9cfee91e2e20afa771667e1d4b\"),\n    85\t}\n    86\tN_LAYERS = 36\n    87\tN_HEADS = 32\n    88\tHEAD_DIM = 128\n    89\tD_MODEL = 4096\n    90\tTEMPLATES = (\"W1\", \"W2\", \"W3\", \"W4\", \"W5\")\n    91\t\n    92\t# ------------------------------------------------------------------------------------------------ design (commit #0)\n    93\tFSTACK = [\"mlp|L26\", \"mlp|L27\", \"mlp|L28\", \"mlp|L30\", \"mlp|L32\",\n    94\t          \"head|L23|H10\", \"head|L27|H31\", \"head|L29|H6\", \"head|L33|H14\", \"head|L34|H28\"]\n    95\tSPEC_EMBEDDED = {\"B3\": [\"mlp|L20\", \"mlp|L12\", \"mlp|L8\", \"mlp|L19\", \"mlp|L16\"],\n    96\t                 \"T10\": [\"mlp|L13\", \"head|L11|H13\", \"mlp|L9\", \"head|L11|H14\", \"head|L14|H5\"]}\n    97\tRS_LAYERS = (4, 8, 12, 16, 20, 23, 26, 30)\n    98\tRAND_BAND = (20, 35)\n    99\tSPEC_RAND_BAND = (4, 24)\n   100\tRAND_TOL = (0.70, 1.43)\n   101\tRAND_TOL_WIDE = (0.5, 2.0)\n   102\tN_RAND = 50\n   103\tN_RAND_SPEC = 20\n   104\tSEED_RAND = 90901\n   105\tSEED_BOOT = 20261023\n   106\tN_BOOT = 10000\n   107\tQ_FORK = 0.90\n   108\tNEAR_COLLAPSE = 0.85\n   109\tLLAMA_CHAT_NORM_FRAC = 0.1\n   110\tGEMMA_MASS_MIN = 0.01\n   111\tONPOLICY_MIN_LOGP = -5.0\n   112\tNPOS = 64\n   113\tTOPK = 256\n   114\tENGINE_TOL = 0.05\n   115\tSELF_PATCH_TOL = 0.02\n   116\tIDENTITY_TOL = 0.05\n   117\tB3_TARGET_D = 8.29053352355957\n   118\tB3_TOL_EXACT = 1e-3\n   119\tB3_TOL_GPU = 0.05\n   120\tSTEER_DOSE = 2.0\n   121\tSTEER_DOSE_SENS = 0.5\n   122\tBUDGET_MSG = \"AI Inventor per-run OpenRouter budget\"\n   123\tOPENROUTER_CAP_USD = 0.20\n   124\t\n   125\tTHRESH = {\n   126\t    \"B1_P1_gain\": 2.0, \"B1_P2_dH\": 0.5, \"B1_P3_fork_vs_matched\": 1.3, \"B1_P3_random_vs_phrasing\": 1.3,\n   127\t    \"B1_disconfirm_gain\": 1.0,\n   128\t    \"B2_Q1_share\": 0.5, \"B2_Q2_median_random\": 0.15, \"B2_Q2_pctile\": 95, \"B2_Q3_spec\": 0.15,\n   129\t    \"B2_disconfirm_share\": 0.2, \"B2_upstream_rs_prefix23\": 0.5, \"B2_late_rs_gap\": 0.5,\n   130\t}\n   131\t\n   132\t\n   133\t# ------------------------------------------------------------------------------------------------ utils\n   134\tdef setup_logging(name: str) -> None:\n   135\t    logger.remove()\n   136\t    logger.add(sys.stdout, level=\"INFO\", format=\"{time:HH:mm:ss}|{level:<7}|{message}\")\n   137\t    logger.add(str(LOG_DIR / f\"{name}.log\"), rotation=\"30 MB\", level=\"DEBUG\")\n   138\t\n   139\t\n   140\tdef set_ram_limit(gb: float) -> None:\n   141\t    lim = int(gb * 1024 ** 3)\n   142\t    try:\n   143\t        resource.setrlimit(resource.RLIMIT_AS, (lim, lim))\n   144\t    except (ValueError, OSError) as e:\n   145\t        logger.warning(f\"could not set RLIMIT_AS: {e}\")\n   146\t\n   147\t\n   148\tdef detect_cpus() -> int:\n   149\t    try:\n   150\t        q = int(Path(\"/sys/fs/cgroup/cpu/cpu.cfs_quota_us\").read_text())\n   151\t        p = int(Path(\"/sys/fs/cgroup/cpu/cpu.cfs_period_us\").read_text())\n   152\t        if q > 0:\n   153\t            return max(1, math.ceil(q / p))\n   154\t    except (FileNotFoundError, ValueError):\n   155\t        pass\n   156\t    try:\n   157\t        return len(os.sched_getaffinity(0))\n   158\t    except (AttributeError, OSError):\n   159\t        return os.cpu_count() or 1\n   160\t\n   161\t\n   162\tdef container_ram_gb() -> float | None:\n   163\t    for p in (\"/sys/fs/cgroup/memory.max\", \"/sys/fs/cgroup/memory/memory.limit_in_bytes\"):\n   164\t        try:\n   165\t            v = Path(p).read_text().strip()\n   166\t            if v != \"max\" and int(v) < 1_000_000_000_000:\n   167\t                return int(v) / 1e9\n   168\t        except (FileNotFoundError, ValueError):\n   169\t            pass\n   170\t    return None\n   171\t\n   172\t\n   173\tdef utc_now() -> str:\n   174\t    return datetime.now(timezone.utc).strftime(\"%Y-%m-%dT%H:%M:%S.%fZ\")\n   175\t\n   176\t\n   177\tdef sha256_text(s: str) -> str:\n   178\t    return hashlib.sha256(s.encode(\"utf-8\")).hexdigest()\n   179\t\n   180\t\n   181\tdef sha256_file(p: Path) -> str:\n   182\t    h = hashlib.sha256()\n   183\t    with open(p, \"rb\") as fh:\n   184\t        for chunk in iter(lambda: fh.read(1 << 20), b\"\"):\n   185\t            h.update(chunk)\n   186\t    return h.hexdigest()\n   187\t\n   188\t\n   189\tdef ids_sha(ids: list[int]) -> str:\n   190\t    return sha256_text(json.dumps([int(i) for i in ids]))\n   191\t\n   192\t\n   193\tdef model_path(key: str) -> str:\n   194\t    mid, rev = MODELS[key]\n   195\t    cache = os.environ.get(\"HF_HUB_CACHE\")\n   196\t    if cache:\n   197\t        snap = Path(cache) / (\"models--\" + mid.replace(\"/\", \"--\")) / \"snapshots\" / rev\n   198\t        if snap.exists():\n   199\t            return str(snap)\n   200\t    return mid\n   201\t\n   202\t\n   203\tdef _json_default(o: Any) -> Any:\n   204\t    if isinstance(o, np.integer):\n   205\t        return int(o)\n   206\t    if isinstance(o, np.floating):\n   207\t        return None if not np.isfinite(o) else float(o)\n   208\t    if isinstance(o, np.ndarray):\n   209\t        return o.tolist()\n   210\t    if isinstance(o, np.bool_):\n   211\t        return bool(o)\n   212\t    if isinstance(o, Path):\n   213\t        return str(o)\n   214\t    if isinstance(o, (set, frozenset)):\n   215\t        return sorted(o)\n   216\t    if isinstance(o, tuple):\n   217\t        return list(o)\n   218\t    raise TypeError(f\"not JSON serialisable: {type(o)}\")\n   219\t\n   220\t\n   221\tdef clean_nan(o: Any) -> Any:\n   222\t    if isinstance(o, float):\n   223\t        return o if math.isfinite(o) else None\n   224\t    if isinstance(o, dict):\n   225\t        return {k: clean_nan(v) for k, v in o.items()}\n   226\t    if isinstance(o, (list, tuple)):\n   227\t        return [clean_nan(v) for v in o]\n   228\t    return o\n   229\t\n   230\t\n   231\tdef read_json(p: Path) -> Any:\n   232\t    return json.loads(Path(p).read_text())\n   233\t\n   234\t\n   235\tdef write_json(p: Path, obj: Any) -> None:\n   236\t    p = Path(p)\n   237\t    p.parent.mkdir(parents=True, exist_ok=True)\n   238\t    tmp = p.with_suffix(p.suffix + \".tmp\")\n   239\t    tmp.write_text(json.dumps(clean_nan(obj), indent=1, default=_json_default))\n   240\t    tmp.replace(p)\n   241\t\n   242\t\n   243\tdef read_jsonl(p: Path) -> list[dict[str, Any]]:\n   244\t    p = Path(p)\n   245\t    if not p.exists():\n   246\t        return []\n   247\t    out = []\n   248\t    with open(p) as fh:\n   249\t        for line in fh:\n   250\t            line = line.strip()\n   251\t            if line:\n   252\t                try:\n   253\t                    out.append(json.loads(line))\n   254\t                except json.JSONDecodeError:\n   255\t                    logger.warning(f\"skipping malformed line in {p.name}\")\n   256\t    return out\n   257\t\n   258\t\n   259\tdef append_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:\n   260\t    p = Path(p)\n   261\t    p.parent.mkdir(parents=True, exist_ok=True)\n   262\t    with open(p, \"a\") as fh:\n   263\t        for r in rows:\n   264\t            fh.write(json.dumps(clean_nan(r), default=_json_default) + \"\\n\")\n   265\t        fh.flush()\n   266\t\n   267\t\n   268\tdef write_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:\n   269\t    p = Path(p)\n   270\t    p.parent.mkdir(parents=True, exist_ok=True)\n   271\t    tmp = p.with_suffix(p.suffix + \".tmp\")\n   272\t    with open(tmp, \"w\") as fh:\n   273\t        for r in rows:\n   274\t            fh.write(json.dumps(clean_nan(r), default=_json_default) + \"\\n\")\n   275\t    tmp.replace(p)\n   276\t\n   277\t\n   278\tdef log_deviation(dev_id: str, text: str, severity: str = \"minor\") -> None:\n   279\t    p = RESULTS_DIR / \"deviations.json\"\n   280\t    cur = read_json(p) if p.exists() else []\n   281\t    if any(d[\"id\"] == dev_id for d in cur):\n   282\t        return\n   283\t    cur.append({\"id\": dev_id, \"severity\": severity, \"text\": text, \"utc\": utc_now()})\n   284\t    write_json(p, cur)\n   285\t    logger.warning(f\"DEVIATION {dev_id}: {text}\")\n   286\t\n   287\t\n   288\tdef stage_time(stage: str, seconds: float, **extra: Any) -> None:\n   289\t    append_jsonl(RESULTS_DIR / \"stage_timing.jsonl\", [{\"stage\": stage, \"seconds\": round(seconds, 1), \"utc\": utc_now(),\n   290\t                                                       **extra}])\n   291\t\n   292\t\n   293\t# ------------------------------------------------------------------------------------------------ commitment chain\n   294\tdef commit(name: str, payload: dict[str, Any]) -> dict[str, Any]:\n   295\t    \"\"\"Write predictions/<name>.json, then append 'utc name file_sha256 link' to commitments.log where\n   296\t    link = sha256(previous link + file_sha256) (genesis = sha256('iter9_base')).\"\"\"\n   297\t    p = PRED_DIR / f\"{name}.json\"\n   298\t    payload = dict(payload, commit_name=name, utc=utc_now())\n   299\t    write_json(p, payload)\n   300\t    fsha = sha256_file(p)\n   301\t    prev = GENESIS\n   302\t    if COMMITS.exists():\n   303\t        lines = [ln for ln in COMMITS.read_text().splitlines() if ln.strip()]\n   304\t        if lines:\n   305\t            prev = lines[-1].split()[-1]\n   306\t    link = sha256_text(prev + fsha)\n   307\t    with open(COMMITS, \"a\") as fh:\n   308\t        fh.write(f\"{utc_now()} {name} {fsha} {link}\\n\")\n   309\t    logger.info(f\"COMMIT {name}: file sha256 {fsha[:16]}, link {link[:16]}\")\n   310\t    return {\"name\": name, \"file_sha256\": fsha, \"link\": link}\n   311\t\n   312\t\n   313\tdef verify_chain() -> dict[str, Any]:\n   314\t    lines = [ln for ln in COMMITS.read_text().splitlines() if ln.strip()] if COMMITS.exists() else []\n   315\t    prev = GENESIS\n   316\t    out = {\"n\": len(lines), \"commits\": [], \"all_links_ok\": True, \"all_hashes_ok\": True}\n   317\t    for ln in lines:\n   318\t        utc, name, fsha, link = ln.split()\n   319\t        ok_link = sha256_text(prev + fsha) == link\n   320\t        p = PRED_DIR / f\"{name}.json\"\n   321\t        ok_hash = p.exists() and sha256_file(p) == fsha\n   322\t        out[\"commits\"].append({\"utc\": utc, \"name\": name, \"link_ok\": ok_link, \"hash_ok\": ok_hash})\n   323\t        out[\"all_links_ok\"] &= ok_link\n   324\t        out[\"all_hashes_ok\"] &= ok_hash\n   325\t        prev = link\n   326\t    return out\n   327\t\n   328\t\n   329\tdef commit_utc(name: str) -> str | None:\n   330\t    if not COMMITS.exists():\n   331\t        return None\n   332\t    for ln in COMMITS.read_text().splitlines():\n   333\t        parts = ln.split()\n   334\t        if len(parts) == 4 and parts[1] == name:\n   335\t            return parts[0]\n   336\t    return None", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [26] TOOL CALL — Bash · 2026-10-26 14:28:35 UTC

```
Read stats9.py and analysis9.py:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50; cat -n $A/src/stats9.py; echo; echo =========; cat -n $A/src/analysis9.py
```

### [27] TOOL RESULT — Bash · 2026-10-26 14:28:35 UTC

```
{"stdout": "     1\t#!/usr/bin/env python3\n     2\t\"\"\"Statistics used by every claim: JS over top-K supports + tail bucket (iteration-8 base_arm.js_div, verbatim), share of\n     3\tthe anchor gap (ratio of sums and mean of ratios), percentile bootstrap, exact two-sided McNemar, exact sign-flip test,\n     4\tHolm, Wilson and Newcombe intervals.\"\"\"\n     5\t\n     6\tfrom __future__ import annotations\n     7\t\n     8\timport itertools\n     9\timport math\n    10\tfro... [truncated, 23748 chars total]
```

### [28] THINKING · 2026-10-26 14:29:45 UTC

```
I'll use the B2 analysis (analysis9.py) as the CPU core for the demo since it runs entirely on per-prompt CMAP margin rows. Next, I'll check the figures, re-derivation and generation-analysis code, plus what's left in `cache/`.
```

### [29] TOOL CALL — Bash · 2026-10-26 14:29:45 UTC

```
List cache dir and read figures9.py:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50; ls -la $A/cache | head; echo; cat -n $A/src/figures9.py
```

### [30] TOOL RESULT — Bash · 2026-10-26 14:29:45 UTC

```
{"stdout": "total 21831\ndrwxrwxrwx  2 aii-agent aii-agent 2001747 Oct 23 18:04 .\ndrwxrwxrwx 12 aii-agent aii-agent 2023169 Oct 23 18:04 ..\n-rw-rw-rw-  1 aii-agent aii-agent  457973 Oct 23 14:47 geom_B3_00.pt\n-rw-rw-rw-  1 aii-agent aii-agent  457973 Oct 23 14:47 geom_B3_01.pt\n-rw-rw-rw-  1 aii-agent aii-agent  457973 Oct 23 14:47 geom_B3_02.pt\n-rw-rw-rw-  1 aii-agent aii-agent  457973 Oct 23 14:47 geom_B3_03.pt\n-rw-rw-rw-  1 aii-agent aii-agent  457973 Oct 23 14:48 geom_B3_04.pt\n-rw-rw-rw-  1 aii-agent aii-agent  457973 Oct 23 14:48 geom_B3_05.pt\n-rw-rw-rw-  1 aii-agent aii-agent  457973 Oct 23 14:48 geom_B3_06.pt\n\n     1\t#!/usr/bin/env python3\n     2\t\"\"\"S8 figures (PDF + PNG in figures/): F1 B1 margins, F2 JS controls, F3 single-component sweep by layer, F4 residual\n     3\tswaps vs depth, F5 FSTACK vs matched random sets, F7 B3 held-out effects vs null, F8 activation geometry (PCA of the\n     4\tactual block-30 output at the fork). F6 generation algorithm mix per arm (predicted vs observed).\"\"\"\n     5\t\n     6\tfrom __future__ import annotations\n     7\t\n     8\timport numpy as np\n     9\timport torch\n    10\tfrom loguru import logger\n    11\t\n    12\timport matplotlib\n    13\tmatplotlib.use(\"Agg\")\n    14\timport matplotlib.pyplot as plt  # noqa: E402\n    15\t\n    16\tfrom cfg9 import CACHE_DIR, FIG_DIR, FSTACK, N_HEADS, N_LAYERS, RESULTS_DIR, RS_LAYERS, read_json, read_jsonl, \\\n    17\t    setup_logging  # noqa: E402\n    18\t\n    19\tplt.rcParams.update({\"font.size\": 9, \"axes.spines.top\": False, \"axes.spines.right\": False, \"pdf.fonttype\": 42,\n    20\t                     \"ps.fonttype\": 42, \"savefig.dpi\": 200})\n    21\tC_I, C_B, C_F, C_R, C_S = \"#1f77b4\", \"#d62728\", \"#2ca02c\", \"#7f7f7f\", \"#9467bd\"\n    22\t\n    23\t\n    24\tdef save(fig, name: str) -> None:\n    25\t    fig.tight_layout()\n    26\t    fig.savefig(FIG_DIR / f\"{name}.pdf\")\n    27\t    fig.savefig(FIG_DIR / f\"{name}.png\")\n    28\t    plt.close(fig)\n    29\t    logger.info(f\"figure {name}\")\n    30\t\n    31\t\n    32\tdef f1_b1_margins(b1: dict) -> None:\n    33\t    rows = []\n    34\t    for u, r in b1[\"units\"].items():\n    35\t        for fid, fr in r[\"forks\"].items():\n    36\t            rows.append((fid + (\" (descriptive)\" if r.get(\"descriptive_only\") else \"\"), fr))\n    37\t    q8 = b1.get(\"qwen_iter8_carried\", {})\n    38\t    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharey=False)\n    39\t    for ax, mode in zip(axes, (\"chat\", \"plain\")):\n    40\t        x = np.arange(len(rows))\n    41\t        for i, (fid, fr) in enumerate(rows):\n    42\t            mi, mb = np.array(fr[mode][\"margin_instr\"]), np.array(fr[mode][\"margin_base\"])\n    43\t            ax.scatter(np.full(len(mi), i - 0.12), mi, s=10, color=C_I, alpha=0.7, label=\"instruct\" if i == 0 else None)\n    44\t            ax.scatter(np.full(len(mb), i + 0.12), mb, s=10, color=C_B, alpha=0.7, label=\"base\" if i == 0 else None)\n    45\t            ax.plot([i - 0.25, i + 0.0], [mi.mean()] * 2, color=C_I, lw=2)\n    46\t            ax.plot([i + 0.0, i + 0.25], [mb.mean()] * 2, color=C_B, lw=2)\n    47\t        ax.set_xticks(x)\n    48\t        ax.set_xticklabels([f for f, _ in rows], rotation=30, ha=\"right\")\n    49\t        ax.axhline(0, color=\"k\", lw=0.5)\n    50\t        ax.set_ylabel(\"fork margin log P(D) - log P(A) (nats)\")\n    51\t        ax.set_title(f\"B1 fork margins, {'chat template' if mode == 'chat' else 'template-free'}\")\n    52\t        if mode == \"chat\" and q8:\n    53\t            txt = \"Qwen3-8B iter-8 gains (carried): \" + \", \".join(f\"{t} {v['margin_gain_mean']:.2f}\"\n    54\t                                                                 for t, v in q8.items())\n    55\t            ax.text(0.01, 0.98, txt, transform=ax.transAxes, fontsize=6.5, va=\"top\")\n    56\t        ax.legend(loc=\"lower right\", fontsize=7)\n    57\t    save(fig, \"F1_b1_margins\")\n    58\t\n    59\t\n    60\tdef f2_js(b1: dict) -> None:\n    61\t    rows = [(fid, fr) for r in b1[\"units\"].values() for fid, fr in r[\"forks\"].items()]\n    62\t    fig, ax = plt.subplots(figsize=(7.5, 3.4))\n    63\t    w = 0.2\n    64\t    labels = (\"js_fork_mean\", \"js_entropy_matched_mean\", \"js_random_mean\", \"js_phrasing_mean\")\n    65\t    names = (\"fork\", \"base-entropy-decile matched\", \"rate-matched random\", \"all phrasing positions\")\n    66\t    cols = (C_F, C_S, C_R, \"#bcbd22\")\n    67\t    for j, (lab, nm, c) in enumerate(zip(labels, names, cols)):\n    68\t        ax.bar(np.arange(len(rows)) + (j - 1.5) * w, [fr[\"phrasing\"][lab] or 0 for _, fr in rows], w, color=c,\n    69\t               label=nm)\n    70\t    ax.set_xticks(np.arange(len(rows)))\n    71\t    ax.set_xticklabels([f for f, _ in rows], rotation=20, ha=\"right\")\n    72\t    ax.set_ylabel(\"JS(instruct || base), nats\\n(top-256 + tail bucket)\")\n    73\t    ax.set_title(\"B1: divergence at the fork vs Cantarero-style controls (chat template)\")\n    74\t    ax.legend(fontsize=7)\n    75\t    save(fig, \"F2_b1_js_controls\")\n    76\t\n    77\t\n    78\tdef f3_singles(b2: dict) -> None:\n    79\t    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))\n    80\t    for ax, (u, r) in zip(axes, b2[\"units\"].items()):\n    81\t        s = r[\"singles\"]\n    82\t        L = np.arange(N_LAYERS)\n    83\t        mlp = [s.get(f\"mlp|L{l}\", np.nan) for l in L]\n    84\t        ax.plot(L, mlp, \"-o\", ms=3, color=C_B, label=\"MLP (single)\")\n    85\t        hx, hy = [], []\n    86\t        for l in L:\n    87\t            for h in range(N_HEADS):\n    88\t                k = f\"head|L{l}|H{h}\"\n    89\t                if k in s:\n    90\t                    hx.append(l + np.random.default_rng(l * 97 + h).uniform(-0.25, 0.25))\n    91\t                    hy.append(s[k])\n    92\t        ax.scatter(hx, hy, s=4, color=C_R, alpha=0.5, label=\"attention head (single)\")\n    93\t        lo, hi = np.percentile(hy, [2.5, 97.5])\n    94\t        ax.axhspan(lo, hi, color=C_R, alpha=0.15, label=\"central 95% of single heads\")\n    95\t        for k in FSTACK:\n    96\t            kind, l = k.split(\"|\")[0], int(k.split(\"|\")[1][1:])\n    97\t            if k in s:\n    98\t                ax.scatter([l], [s[k]], s=40, facecolor=\"none\", edgecolor=C_F, lw=1.5,\n    99\t                           label=\"FSTACK node\" if k == FSTACK[0] else None)\n   100\t        ax.axhline(0, color=\"k\", lw=0.5)\n   101\t        ax.set_xlabel(\"layer\")\n   102\t        ax.set_ylabel(\"share of the instruct-base gap closed\")\n   103\t        ax.set_title(f\"{u}: single-component CMAP at the fork (N={r['n_prompts']} prompts)\\nFSTACK set \"\n   104\t                     f\"{r['arms']['FSTACK']['share']:.2f}; sum of its singles {r['sum_singles_FSTACK']:.2f}\")\n   105\t        ax.legend(fontsize=6.5, loc=\"upper left\")\n   106\t    save(fig, \"F3_b2_singles_by_layer\")\n   107\t\n   108\t\n   109\tdef f4_rs(b2: dict) -> None:\n   110\t    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))\n   111\t    for ax, (u, r) in zip(axes, b2[\"units\"].items()):\n   112\t        rf = r[\"RS_fork\"]\n   113\t        ls = sorted(int(k) for k in rf)\n   114\t        ax.plot(ls, [rf[str(l)] if str(l) in rf else rf[l] for l in ls], \"-\", color=C_I, label=\"RS-fork(l): fork only\")\n   115\t        for key, lab, mk in ((\"RS_prefix\", \"RS-prefix(l): positions before the fork\", \"s\"),\n   116\t                             (\"RS_all\", \"RS-all(l): all positions\", \"^\")):\n   117\t            d = r[key]\n   118\t            xs = sorted(int(k) for k in d)\n   119\t            ax.plot(xs, [d[str(l)] if str(l) in d else d[l] for l in xs], mk + \"--\", ms=4, label=lab)\n   120\t        ax.axhline(r[\"arms\"][\"FSTACK\"][\"share\"], color=C_F, lw=1.5, label=\"FSTACK (10 nodes)\")\n   121\t        if \"SPEC\" in r[\"arms\"]:\n   122\t            ax.axhline(r[\"arms\"][\"SPEC\"][\"share\"], color=C_S, lw=1.2, ls=\":\", label=\"SPEC set\")\n   123\t        ax.axhline(r[\"null_R\"][\"median\"], color=C_R, lw=1, ls=\"-.\", label=\"median matched random set\")\n   124\t        ax.axhline(1, color=\"k\", lw=0.5)\n   125\t        ax.axhline(0, color=\"k\", lw=0.5)\n   126\t        ax.set_xlabel(\"layer l (residual input of block l; 36 = final-norm input)\")\n   127\t        ax.set_ylabel(\"share of gap closed\")\n   128\t        ax.set_title(f\"{u}: residual swaps (base -> instruct) vs depth\")\n   129\t        ax.legend(fontsize=6.5)\n   130\t    save(fig, \"F4_b2_residual_swaps\")\n   131\t\n   132\t\n   133\tdef f5_null(b2: dict) -> None:\n   134\t    fig, axes = plt.subplots(1, 2, figsize=(10, 3.4))\n   135\t    for ax, (u, r) in zip(axes, b2[\"units\"].items()):\n   136\t        ax.hist(r[\"null_R\"][\"shares\"], bins=20, color=C_R, alpha=0.7, label=\"50 matched random sets (R)\")\n   137\t        if \"null_Rpure\" in r:\n   138\t            ax.hist(r[\"null_Rpure\"][\"shares\"], bins=20, color=C_S, alpha=0.4, label=\"R-pure (exp41 top-15 excluded)\")\n   139\t        ax.axvline(r[\"arms\"][\"FSTACK\"][\"share\"], color=C_F, lw=2, label=f\"FSTACK {r['arms']['FSTACK']['share']:.2f}\")\n   140\t        ax.axvline(r[\"null_R\"][\"p95\"], color=\"k\", ls=\"--\", lw=1, label=\"R 95th percentile\")\n   141\t        ax.set_xlabel(\"share of gap closed\")\n   142\t        ax.set_ylabel(\"count\")\n   143\t        ax.set_title(f\"{u}: FSTACK vs write-norm-matched random sets (p = {r['null_R']['empirical_p_upper']:.3f})\")\n   144\t        ax.legend(fontsize=6.5)\n   145\t    save(fig, \"F5_b2_random_null\")\n   146\t\n   147\t\n   148\tdef f7_b3(b3: dict) -> None:\n   149\t    pn = {k: v for k, v in b3[\"per_node\"].items() if k.startswith(\"aligned|\") and v[\"mode\"] in (\"ablate\", \"steer\")}\n   150\t    if not pn:\n   151\t        return\n   152\t    rows = read_jsonl(RESULTS_DIR / \"b3_heldout_rows.jsonl\")\n   153\t    fig, ax = plt.subplots(figsize=(9, 3.6))\n   154\t    keys = list(pn)\n   155\t    for i, k in enumerate(keys):\n   156\t        v = pn[k]\n   157\t        d = np.array(v[\"d_per_prompt\"])\n   158\t        ax.scatter(np.full(len(d), i), d, s=12, color=C_F if v[\"mode\"] == \"ablate\" else C_S, alpha=0.8)\n   159\t        # random null spread: per prompt, random component values minus their mean\n   160\t        tag = f\"aligned|{v['mode']}|{v['node']}\"\n   161\t        spread = []\n   162\t        for r in rows:\n   163\t            rv = [r[\"res\"][f\"{tag}|r{j}\"] for j in range(50) if f\"{tag}|r{j}\" in r[\"res\"]]\n   164\t            if rv:\n   165\t                spread += list(np.asarray(rv) - np.mean(rv))\n   166\t        if spread:\n   167\t            lo, hi = np.percentile(spread, [2.5, 97.5])\n   168\t            ax.plot([i, i], [lo, hi], color=C_R, lw=4, alpha=0.4)\n   169\t        ax.text(i, ax.get_ylim()[1] if i == 0 else d.max(), f\"p={v['p_sign_flip_heldout']:.3f}\", fontsize=6,\n   170\t                ha=\"center\", va=\"bottom\")\n   171\t    ax.set_xticks(range(len(keys)))\n   172\t    ax.set_xticklabels([f\"{pn[k]['mode']}\\n{pn[k]['node'].replace('|H-1', '')}\" for k in keys], fontsize=6.5,\n   173\t                       rotation=30, ha=\"right\")\n   174\t    ax.axhline(0, color=\"k\", lw=0.5)\n   175\t    ax.set_ylabel(\"d = node effect - mean random effect (nats)\")\n   176\t    ax.set_title(\"B3: held-out C1forced prompts with interpolated condition means (grey: central 95% of random \"\n   177\t                 \"components)\")\n   178\t    save(fig, \"F7_b3_heldout\")\n   179\t\n   180\t\n   181\tdef f8_geometry(b2: dict) -> None:\n   182\t    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))\n   183\t    for ax, (u, r) in zip(axes, b2[\"units\"].items()):\n   184\t        tf = read_jsonl(RESULTS_DIR / f\"b2_tf_{u}.jsonl\")\n   185\t        pids = []\n   186\t        m = {}\n   187\t        for row in tf:\n   188\t            if row[\"pid\"] not in pids:\n   189\t                pids.append(row[\"pid\"])\n   190\t            m[(row[\"pid\"], row[\"arm\"])] = row[\"m\"]\n   191\t        rsh = r[\"null_R\"][\"shares\"]\n   192\t        med = int(np.argsort(rsh)[len(rsh) // 2])\n   193\t        cb = torch.load(CACHE_DIR / f\"base_{u}.pt\")\n   194\t        pts, cols, kinds = [], [], []\n   195\t        for pi, p in enumerate(pids):\n   196\t            gp = CACHE_DIR / f\"geom_{u}_{pi:02d}.pt\"\n   197\t            if not gp.exists():\n   198\t                continue\n   199\t            g = torch.load(gp)\n   200\t            base_state = (cb[\"caps\"][pi].get(\"ot\") or cb[\"caps\"][pi])[\"resid\"][31]\n   201\t            for kind, vec, mm in ((\"instruct\", g[\"none\"], m[(p, \"none\")]), (\"base\", base_state, r[\"m_B\"][pi]),\n   202\t                                  (\"FSTACK-patched\", g[\"FSTACK\"], m[(p, \"FSTACK\")]),\n   203\t                                  (\"median random-patched\", g[f\"R{med}\"], m[(p, f\"R{med}\")]),\n   204\t                                  (\"RS-fork(23)-patched\", g[\"RSfork23\"], m[(p, \"RSfork23\")])):\n   205\t                pts.append(vec.float().numpy())\n   206\t                cols.append(mm)\n   207\t                kinds.append(kind)\n   208\t        X = np.stack(pts)\n   209\t        fit = X[[i for i, k in enumerate(kinds) if k in (\"instruct\", \"base\")]]\n   210\t        mu = fit.mean(0)\n   211\t        U_, Sv, Vt = np.linalg.svd(fit - mu, full_matrices=False)\n   212\t        ev = Sv ** 2 / (Sv ** 2).sum()\n   213\t        Y = (X - mu) @ Vt[:2].T\n   214\t        marks = {\"instruct\": \"o\", \"base\": \"s\", \"FSTACK-patched\": \"^\", \"median random-patched\": \"x\",\n   215\t                 \"RS-fork(23)-patched\": \"D\"}\n   216\t        sc = None\n   217\t        for kind, mk in marks.items():\n   218\t            ii = [i for i, k in enumerate(kinds) if k == kind]\n   219\t            sc = ax.scatter(Y[ii, 0], Y[ii, 1], c=[cols[i] for i in ii], cmap=\"coolwarm\", marker=mk, s=28,\n   220\t                            vmin=min(cols), vmax=max(cols), label=kind, edgecolors=\"k\", linewidths=0.3)\n   221\t        fig.colorbar(sc, ax=ax, label=\"fork margin m (nats)\")\n   222\t        ax.set_xlabel(f\"PC1 ({ev[0] * 100:.1f}% var)\")\n   223\t        ax.set_ylabel(f\"PC2 ({ev[1] * 100:.1f}% var)\")\n   224\t        ax.set_title(f\"{u}: block-30 output (residual into block 31) at the fork\\nPCA fit on instruct + base states, \"\n   225\t                     f\"N={len(pids)} prompts; other states projected\", fontsize=8)\n   226\t        ax.legend(fontsize=6, loc=\"best\")\n   227\t        del cb\n   228\t    save(fig, \"F8_b2_geometry_pca\")\n   229\t\n   230\t\n   231\tdef f6_generation() -> None:\n   232\t    p = RESULTS_DIR / \"b2_generation.json\"\n   233\t    if not p.exists():\n   234\t        return\n   235\t    g = read_json(p)\n   236\t    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))\n   237\t    arms = (\"TWIN\", \"FSTACK\", \"RAND\", \"FPD\")\n   238\t    for ax, u, minority in zip(axes, (\"B3\", \"T10\"), (\"prim_heap\", \"dfs\")):\n   239\t        cells = g[u][\"cells\"]\n   240\t        x = np.arange(len(arms))\n   241\t        obs = [cells[a][\"observed_shares\"].get(minority) or 0 for a in arms]\n   242\t        pre = [cells[a][\"predicted_shares\"].get(minority, 0) for a in arms]\n   243\t        ci = [cells[a][\"correct_minority_ci95\"] for a in arms]\n   244\t        rate = [cells[a][\"correct_minority_rate\"] for a in arms]\n   245\t        ax.bar(x - 0.18, obs, 0.36, color=C_F, label=f\"observed share labelled {minority}\")\n   246\t        ax.bar(x + 0.18, pre, 0.36, color=C_R, alpha=0.6, label=\"predicted (COMMIT #1, TF fork distribution x token map)\")\n   247\t        ax.errorbar(x - 0.18, rate, yerr=[[r - c[0] for r, c in zip(rate, ci)], [c[1] - r for r, c in zip(rate, ci)]],\n   248\t                    fmt=\"none\", ecolor=\"k\", capsize=3, label=\"correct-minority rate, Wilson 95%\")\n   249\t        ax.set_xticks(x)\n   250\t        ax.set_xticklabels(arms)\n   251\t        ax.set_ylim(0, 1)\n   252\t        t = g[u][\"tests\"]\n   253\t        ax.set_title(f\"{u}: minority algorithm in N=30 CRN programs per arm\\nFSTACK vs TWIN \"\n   254\t                     f\"{t['FSTACK_vs_TWIN']['b_first_only']}:{t['FSTACK_vs_TWIN']['c_second_only']} \"\n   255\t                     f\"(p={t['FSTACK_vs_TWIN']['p_exact_two_sided']:.1e}); FSTACK vs RAND \"\n   256\t                     f\"{t['FSTACK_vs_RAND']['b_first_only']}:{t['FSTACK_vs_RAND']['c_second_only']}; FSTACK vs FPD \"\n   257\t                     f\"{t['FSTACK_vs_FPD']['b_first_only']}:{t['FSTACK_vs_FPD']['c_second_only']}\", fontsize=8)\n   258\t        ax.set_ylabel(\"share of programs\")\n   259\t        ax.legend(fontsize=6.5, loc=\"upper left\")\n   260\t    save(fig, \"F6_b2_generation\")\n   261\t\n   262\t\n   263\tdef main() -> None:\n   264\t    b1p, b2p, b3p = (RESULTS_DIR / f\"{n}.json\" for n in (\"b1_summary\", \"b2_summary\", \"b3_summary\"))\n   265\t    if b1p.exists():\n   266\t        b1 = read_json(b1p)\n   267\t        f1_b1_margins(b1)\n   268\t        f2_js(b1)\n   269\t    if b2p.exists():\n   270\t        b2 = read_json(b2p)\n   271\t        f3_singles(b2)\n   272\t        f4_rs(b2)\n   273\t        f5_null(b2)\n   274\t        try:\n   275\t            f8_geometry(b2)\n   276\t        except (FileNotFoundError, KeyError, RuntimeError) as e:\n   277\t            logger.error(f\"F8 failed: {e}\")\n   278\t    if b3p.exists():\n   279\t        f7_b3(read_json(b3p))\n   280\t    f6_generation()\n   281\t\n   282\t\n   283\tif __name__ == \"__main__\":\n   284\t    setup_logging(\"figures9\")\n   285\t    main()", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [31] TOOL CALL — Bash · 2026-10-26 14:29:45 UTC

```
Read rederive9.py:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50; cat -n $A/src/rederive9.py
```

### [32] TOOL RESULT — Bash · 2026-10-26 14:29:45 UTC

```
{"stdout": "     1\t#!/usr/bin/env python3\n     2\t\"\"\"Independent re-derivation (Python standard library only; no numpy, no project imports) of every headline number from\n     3\tthe raw per-prompt rows, compared with the aggregated summaries; plus placebos that must FAIL.\n     4\t\n     5\tRaw inputs: results/b2_tf_<unit>.jsonl (per prompt x arm margins), results/b1_tf_<model>.json (per prompt fork\n     6\tmargins and opening log-likelihoods), results/b3_heldout_rows.jsonl (per held-out prompt job values).\n     7\tWrites results/rederive.json.\"\"\"\n     8\t\n     9\tfrom __future__ import annotations\n    10\t\n    11\timport itertools\n    12\timport json\n    13\timport random\n    14\timport statistics\n    15\tfrom pathlib import Path\n    16\t\n    17\tROOT = Path(__file__).resolve().parents[1]\n    18\tRES = ROOT / \"results\"\n    19\tTOL = 1e-6\n    20\t\n    21\t\n    22\tdef jl(p: Path) -> list[dict]:\n    23\t    with open(p) as fh:\n    24\t        return [json.loads(x) for x in fh if x.strip()]\n    25\t\n    26\t\n    27\tdef pct(xs: list[float], q: float) -> float:\n    28\t    \"\"\"numpy-default (linear) percentile.\"\"\"\n    29\t    s = sorted(xs)\n    30\t    k = (len(s) - 1) * q / 100\n    31\t    f = int(k)\n    32\t    c = min(f + 1, len(s) - 1)\n    33\t    return s[f] + (s[c] - s[f]) * (k - f)\n    34\t\n    35\t\n    36\tdef b2(mism: list, out: dict) -> None:\n    37\t    summ = json.loads((RES / \"b2_summary.json\").read_text())\n    38\t    for u in (\"B3\", \"T10\"):\n    39\t        rows = jl(RES / f\"b2_tf_{u}.jsonl\")\n    40\t        mI, mB, arm = {}, {}, {}\n    41\t        for r in rows:\n    42\t            mI[r[\"pid\"]] = r[\"m_I\"]\n    43\t            mB[r[\"pid\"]] = r[\"m_B\"]\n    44\t            arm.setdefault(r[\"arm\"], {})[r[\"pid\"]] = r[\"m\"]\n    45\t        pids = sorted(mI)\n    46\t        den = sum(mI[p] - mB[p] for p in pids)\n    47\t\n    48\t        def sh(a: str) -> float:\n    49\t            return sum(mI[p] - arm[a][p] for p in pids) / den\n    50\t        rec = {\"FSTACK\": sh(\"FSTACK\"), \"RSfork36\": sh(\"RSfork36\"), \"RSfork23\": sh(\"RSfork23\"),\n    51\t               \"SPEC\": sh(\"SPEC\") if \"SPEC\" in arm else None, \"gap_mean\": statistics.mean(mI[p] - mB[p] for p in pids)}\n    52\t        R = [sh(f\"R{s}\") for s in range(50)]\n    53\t        rec[\"R_median\"] = statistics.median(R)\n    54\t        rec[\"R_p95\"] = pct(R, 95)\n    55\t        rec[\"R_empirical_p\"] = (1 + sum(x >= rec[\"FSTACK\"] for x in R)) / 51\n    56\t        S = summ[\"units\"][u]\n    57\t        cmp_ = {\"FSTACK\": S[\"arms\"][\"FSTACK\"][\"share\"], \"RSfork36\": S[\"RS_fork\"][\"36\"],\n    58\t                \"RSfork23\": S[\"RS_fork\"][\"23\"], \"SPEC\": S[\"arms\"].get(\"SPEC\", {}).get(\"share\"),\n    59\t                \"gap_mean\": S[\"gap_mean\"], \"R_median\": S[\"null_R\"][\"median\"], \"R_p95\": S[\"null_R\"][\"p95\"],\n    60\t                \"R_empirical_p\": S[\"null_R\"][\"empirical_p_upper\"]}\n    61\t        for k, v in rec.items():\n    62\t            if v is None or cmp_.get(k) is None:\n    63\t                continue\n    64\t            if abs(v - cmp_[k]) > TOL:\n    65\t                mism.append(f\"B2 {u} {k}: rederived {v} vs summary {cmp_[k]}\")\n    66\t        # placebo: node-label permutation -> treat a random R set as 'the circuit' against the other 49 sets\n    67\t        rng = random.Random(7)\n    68\t        ps = []\n    69\t        for _ in range(200):\n    70\t            j = rng.randrange(50)\n    71\t            others = [x for i, x in enumerate(R) if i != j]\n    72\t            ps.append((1 + sum(x >= R[j] for x in others)) / 50)\n    73\t        rec[\"placebo_permuted_node_labels_frac_p_le_0.05\"] = sum(p <= 0.05 for p in ps) / len(ps)\n    74\t        rec[\"placebo_permuted_node_labels_fails\"] = rec[\"placebo_permuted_node_labels_frac_p_le_0.05\"] <= 0.10\n    75\t        # placebo: swap the instruct and base anchors -> FSTACK 'share' sign flips relative to the gap\n    76\t        rec[\"placebo_anchor_swap_share\"] = sum(mB[p] - arm[\"FSTACK\"][p] for p in pids) / sum(mB[p] - mI[p]\n    77\t                                                                                             for p in pids)\n    78\t        out[f\"B2_{u}\"] = rec\n    79\t\n    80\t\n    81\tdef b1(mism: list, out: dict) -> None:\n    82\t    summ = json.loads((RES / \"b1_summary.json\").read_text())\n    83\t    pairs = {\"gemma\": (\"gemma\", \"gemma_pt\"), \"llama\": (\"llama\", \"llama_base\")}\n    84\t    for fam, (ki, kb) in pairs.items():\n    85\t        pi, pb = RES / f\"b1_tf_{ki}.json\", RES / f\"b1_tf_{kb}.json\"\n    86\t        if not (pi.exists() and pb.exists()):\n    87\t            continue\n    88\t        I, B = json.loads(pi.read_text()), json.loads(pb.read_text())\n    89\t        units = json.loads((RES / \"units.json\").read_text())\n    90\t        for u, ru in I[\"units\"].items():\n    91\t            U = units[u]\n    92\t            byI = {r[\"pid\"]: r for r in ru[\"prompts\"]}\n    93\t            byB = {r[\"pid\"]: r for r in B[\"units\"][u][\"prompts\"]}\n    94\t            keep = [p[\"pid\"] for p in U[\"prompts\"]\n    95\t                    if min(byI[p[\"pid\"]][\"forks\"][f[\"fork_id\"]][\"chat\"][\"logp_opening\"] for f in U[\"forks\"]) >= -5.0]\n    96\t            keep = keep[:U.get(\"max_prompts\", 20)]\n    97\t            if not keep:                       # committed rule drops every prompt -> descriptive on all prompts\n    98\t                keep = [p[\"pid\"] for p in U[\"prompts\"]][:U.get(\"max_prompts\", 20)]\n    99\t                out[f\"B1_{u}_descriptive_only\"] = True\n   100\t            for f in U[\"forks\"]:\n   101\t                fid = f[\"fork_id\"]\n   102\t                for mode in (\"chat\", \"plain\"):\n   103\t                    g = [byI[k][\"forks\"][fid][mode][\"margin\"] - byB[k][\"forks\"][fid][mode][\"margin\"] for k in keep]\n   104\t                    gm = statistics.mean(g)\n   105\t                    ref = summ[\"units\"][u][\"forks\"][fid][mode][\"gain_mean\"]\n   106\t                    if abs(gm - ref) > TOL:\n   107\t                        mism.append(f\"B1 {fid} {mode} gain: rederived {gm} vs summary {ref}\")\n   108\t                    out[f\"B1_{fid}_{mode}_gain\"] = gm\n   109\t                    # placebo: swapped labels -> the >= 2 nat gain criterion must fail\n   110\t                    out[f\"B1_{fid}_{mode}_placebo_swapped_gain\"] = -gm\n   111\t                    out[f\"B1_{fid}_{mode}_placebo_fails\"] = (-gm) < 2.0\n   112\t\n   113\t\n   114\tdef b3(mism: list, out: dict) -> None:\n   115\t    p = RES / \"b3_heldout_rows.jsonl\"\n   116\t    if not p.exists():\n   117\t        return\n   118\t    rows = jl(p)\n   119\t    summ = json.loads((RES / \"b3_summary.json\").read_text())\n   120\t    for key, v in summ[\"per_node\"].items():\n   121\t        if not key.startswith(\"aligned|\") or v[\"mode\"] not in (\"ablate\", \"steer\"):\n   122\t            continue\n   123\t        d = []\n   124\t        for r in rows:\n   125\t            node = r[\"res\"].get(f\"{key}|node\")\n   126\t            rv = [r[\"res\"][f\"{key}|r{j}\"] for j in range(50) if f\"{key}|r{j}\" in r[\"res\"]]\n   127\t            if node is None or not rv:\n   128\t                continue\n   129\t            d.append(node - sum(rv) / len(rv))\n   130\t        md = statistics.mean(d)\n   131\t        if abs(md - v[\"mean_d_heldout\"]) > TOL:\n   132\t            mism.append(f\"B3 {key} mean_d: rederived {md} vs summary {v['mean_d_heldout']}\")\n   133\t        obs = abs(md)\n   134\t        cnt = sum(1 for s in itertools.product((1, -1), repeat=len(d))\n   135\t                  if abs(sum(a * b for a, b in zip(d, s)) / len(d)) >= obs - 1e-12)\n   136\t        pv = cnt / 2 ** len(d)\n   137\t        if abs(pv - v[\"p_sign_flip_heldout\"]) > TOL:\n   138\t            mism.append(f\"B3 {key} p: rederived {pv} vs summary {v['p_sign_flip_heldout']}\")\n   139\t        # placebo: random sign assignment of the per-prompt d (shuffled pairing) -> p should usually be large\n   140\t        rng = random.Random(11)\n   141\t        pl = []\n   142\t        for _ in range(100):\n   143\t            dd = [x * rng.choice((1, -1)) for x in d]\n   144\t            o2 = abs(statistics.mean(dd))\n   145\t            c2 = sum(1 for s in itertools.product((1, -1), repeat=len(dd))\n   146\t                     if abs(sum(a * b for a, b in zip(dd, s)) / len(dd)) >= o2 - 1e-12)\n   147\t            pl.append(c2 / 2 ** len(dd))\n   148\t        out[f\"B3_{key}\"] = {\"mean_d\": md, \"p\": pv, \"placebo_sign_shuffle_frac_p_le_0.05\":\n   149\t                            sum(x <= 0.05 for x in pl) / len(pl)}\n   150\t\n   151\t\n   152\tdef gen(mism: list, out: dict) -> None:\n   153\t    raw = jl(RES.parent / \"data\" / \"samples.jsonl\")\n   154\t    lab = {r[\"sid\"]: r for r in jl(RES.parent / \"data\" / \"labels_gen.jsonl\")}\n   155\t    summ = json.loads((RES / \"b2_generation.json\").read_text())\n   156\t    minority = {\"B3\": {\"prim_heap\", \"prim_array\"}, \"T10\": {\"dfs\", \"bfs\"}}\n   157\t    for u in (\"B3\", \"T10\"):\n   158\t        ind = {}\n   159\t        for r in raw:\n   160\t            if r[\"task\"] != u:\n   161\t                continue\n   162\t            L = lab[r[\"sid\"]]\n   163\t            ind.setdefault(r[\"arm\"], {})[(r[\"template\"], r[\"slot\"])] = int(L[\"label\"] in minority[u] and L[\"passed\"])\n   164\t        for a, b in ((\"FSTACK\", \"TWIN\"), (\"FSTACK\", \"RAND\"), (\"FSTACK\", \"FPD\"), (\"FPD\", \"TWIN\")):\n   165\t            ks = sorted(set(ind[a]) & set(ind[b]))\n   166\t            n10 = sum(1 for k in ks if ind[a][k] == 1 and ind[b][k] == 0)\n   167\t            n01 = sum(1 for k in ks if ind[a][k] == 0 and ind[b][k] == 1)\n   168\t            ref = summ[u][\"tests\"][f\"{a}_vs_{b}\"]\n   169\t            if (n10, n01) != (ref[\"b_first_only\"], ref[\"c_second_only\"]):\n   170\t                mism.append(f\"gen {u} {a}_vs_{b}: rederived {n10}:{n01} vs {ref['b_first_only']}:{ref['c_second_only']}\")\n   171\t            n = n10 + n01\n   172\t            p = min(1.0, 2 * sum(__import__(\"math\").comb(n, i) for i in range(0, min(n10, n01) + 1)) / 2 ** n) if n else 1.0\n   173\t            out[f\"gen_{u}_{a}_vs_{b}\"] = {\"b\": n10, \"c\": n01, \"p\": p}\n   174\t            # placebo: shuffle the CRN slot pairing of the second arm -> the paired McNemar should lose significance\n   175\t            rng = random.Random(5)\n   176\t            pl = []\n   177\t            for _ in range(200):\n   178\t                kk = ks[:]\n   179\t                rng.shuffle(kk)\n   180\t                m10 = sum(1 for k, k2 in zip(ks, kk) if ind[a][k] == 1 and ind[b][k2] == 0)\n   181\t                m01 = sum(1 for k, k2 in zip(ks, kk) if ind[a][k] == 0 and ind[b][k2] == 1)\n   182\t                nn = m10 + m01\n   183\t                pl.append(min(1.0, 2 * sum(__import__(\"math\").comb(nn, i) for i in range(0, min(m10, m01) + 1))\n   184\t                              / 2 ** nn) if nn else 1.0)\n   185\t            out[f\"gen_{u}_{a}_vs_{b}\"][\"placebo_slot_shuffle_median_p\"] = statistics.median(pl)\n   186\t            out[f\"gen_{u}_{a}_vs_{b}\"][\"note_slot_shuffle\"] = (\"uninformative when one arm has no minority programs \"\n   187\t                                                              \"(the contrast is then marginal, pairing-free)\")\n   188\t            # placebo 2: swap the two arms' labels within each CRN pair at random (the null McNemar permutes)\n   189\t            pl2 = []\n   190\t            for _ in range(200):\n   191\t                m10 = m01 = 0\n   192\t                for k in ks:\n   193\t                    x, y = (ind[a][k], ind[b][k]) if rng.random() < 0.5 else (ind[b][k], ind[a][k])\n   194\t                    m10 += int(x == 1 and y == 0)\n   195\t                    m01 += int(x == 0 and y == 1)\n   196\t                nn = m10 + m01\n   197\t                pl2.append(min(1.0, 2 * sum(__import__(\"math\").comb(nn, i) for i in range(0, min(m10, m01) + 1))\n   198\t                               / 2 ** nn) if nn else 1.0)\n   199\t            out[f\"gen_{u}_{a}_vs_{b}\"][\"placebo_within_pair_arm_swap_median_p\"] = statistics.median(pl2)\n   200\t            out[f\"gen_{u}_{a}_vs_{b}\"][\"placebo_within_pair_arm_swap_frac_p_le_0.05\"] = sum(x <= 0.05 for x in pl2) / 200\n   201\t\n   202\t\n   203\tdef chain(mism: list, out: dict) -> None:\n   204\t    \"\"\"Commit chain links (sha256(prev + file sha)) and 'decisive rows after their commit' (stdlib).\"\"\"\n   205\t    import hashlib\n   206\t    lines = [l.split() for l in (ROOT / \"commitments.log\").read_text().splitlines() if l.strip()]\n   207\t    prev = hashlib.sha256(b\"iter9_base\").hexdigest()\n   208\t    ok = True\n   209\t    when = {}\n   210\t    for utc, name, fsha, link in lines:\n   211\t        fs = hashlib.sha256((ROOT / \"predictions\" / f\"{name}.json\").read_bytes()).hexdigest()\n   212\t        ok &= fs == fsha and hashlib.sha256((prev + fsha).encode()).hexdigest() == link\n   213\t        prev = link\n   214\t        when[name] = utc\n   215\t    first = {}\n   216\t    for nm, path in ((\"b2_tf\", RES / \"b2_tf_B3.jsonl\"), (\"b3_heldout\", RES / \"b3_heldout_rows.jsonl\"),\n   217\t                     (\"generation\", RES.parent / \"data\" / \"samples.jsonl\")):\n   218\t        rows = jl(path)\n   219\t        first[nm] = min(r[\"utc\"] for r in rows) if rows else None\n   220\t    order = {\"b2_tf_after_commit0\": first[\"b2_tf\"] > when.get(\"commit0\", \"~\"),\n   221\t             \"b3_heldout_after_commitB3\": first[\"b3_heldout\"] > when.get(\"commitB3\", \"~\"),\n   222\t             \"generation_after_commit1_gen\": first[\"generation\"] > when.get(\"commit1_gen\", \"~\")}\n   223\t    out[\"commit_chain\"] = {\"n\": len(lines), \"all_ok\": ok, \"commits\": when, \"first_rows\": first, \"order\": order}\n   224\t    if not ok:\n   225\t        mism.append(\"commit chain does not verify\")\n   226\t    for k, v in order.items():\n   227\t        if not v:\n   228\t            mism.append(f\"timestamp order fails: {k}\")\n   229\t\n   230\t\n   231\tdef main() -> None:\n   232\t    mism: list[str] = []\n   233\t    out: dict = {}\n   234\t    for fn in (b2, b1, b3, gen, chain):\n   235\t        try:\n   236\t            fn(mism, out)\n   237\t        except FileNotFoundError as e:\n   238\t            out[f\"{fn.__name__}_missing\"] = str(e)\n   239\t    out[\"mismatches\"] = mism\n   240\t    out[\"n_mismatches\"] = len(mism)\n   241\t    (RES / \"rederive.json\").write_text(json.dumps(out, indent=1))\n   242\t    print(f\"rederive: {len(mism)} mismatches\")\n   243\t    for m in mism[:20]:\n   244\t        print(\"  \", m)\n   245\t\n   246\t\n   247\tif __name__ == \"__main__\":\n   248\t    main()", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [33] ASSISTANT · 2026-10-26 14:30:17 UTC

```
`cache/` still holds the small `geom_*.pt` fork-state files that F8 (the activation-geometry PCA) needs. Next I'll check what else survives there and look at the raw B2 per-prompt rows.
```

### [34] TOOL CALL — Bash · 2026-10-26 14:30:17 UTC

```
Count cache files and inspect B2 per-prompt rows:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50; ls $A/cache | sed 's/_[0-9]*\.pt$//' | sort | uniq -c; ls -la $A/cache | grep -v geom_; echo; head -c 1500 $A/results/b2_tf_B3.jsonl; echo; echo; python3 -I - $A/results/b2_tf_B3.jsonl <<'EOF'
import json,sys,collections
rows=[json.loads(l) for l in open(sys.argv[1]) if l.strip()]
print('rows',len(rows))
print('keys', sorted(rows[0].keys()))
arms=collections.Counter(r['arm'] for r in rows)
print('n arms',len(arms))
pids=collections.Counter(r['pid'] for r in rows)
print('n pids',len(pids), list(pids.items())[:3])
import re
fam=collections.Counter(re.sub(r'\d+$','#',a) if not a.startswith(('mlp|','head|')) else a.split('|')[0] for a in arms)
print(fam)
print([a for a in arms if not a.startswith(('mlp|','head|','R','SPECR'))])
# sizes of fields
for k in rows[0]:
    print(k, len(json.dumps(rows[0][k])))
EOF
```

### [35] TOOL RESULT — Bash · 2026-10-26 14:30:17 UTC

```
{"stdout": "     20 geom_B3\n     20 geom_T10\ntotal 21831\ndrwxrwxrwx  2 aii-agent aii-agent 2001747 Oct 23 18:04 .\ndrwxrwxrwx 12 aii-agent aii-agent 2023169 Oct 23 18:04 ..\n\n{\"unit\": \"B3\", \"pid\": \"W1|guy\", \"template\": \"W1\", \"arm\": \"none\", \"m\": 1.2982978820800781, \"m_raw\": 1.2982978820800781, \"dm_tok\": 0.0, \"dm\": 0.0, \"ref0_drift\": 0.0, \"dist\": {\"entropy\": 0.5352820754051208, \"top_ids\": [16447, 35183, 2340, 9008, 9145, 4248, 5443, 30925, 7379, 1416, 31920, 84280, 2014, 12906, 5712, 3386, 12091, 4093, 12518, 66191, 10657, 19785, 1752, 29053, 10349, 31166, 5624, 730, 4230, 15967, 1759, 2910, 18614, 7656, 8575, 20552, 4389, 8860, 12199, 20513, 22966, 13655, 20578, 25169, 39267, 647, 15690, 8406, 2691, 6452, 9129, 22752, 45799, 65169, 25001, 5714, 8704, 5145, 14822, 19813, 23282, 1096, 13015, 49370, 362, 7169, 29279, 65984, 94312, 20517, 21837, 22826, 3234, 5309, 12090, 75112, 422, 576, 22918, 595, 19725, 1205, 7405, 4968, 9735, 19643, 28025, 37108, 12256, 13760, 25429, 2885, 17893, 18626, 31075, 87419, 98566, 2573, 31399, 89601, 758, 4127, 22603, 31639, 2363, 3411, 4504, 23768, 86377, 22749, 64740, 9855, 11766, 39947, 42797, 21419, 55378, 1230, 1779, 10466, 11994, 27785, 20848, 27196, 44263, 46070, 90351, 13532, 1477, 5542, 11194, 29901, 77143, 84784, 42, 421, 7487, 12407, 71931, 2126, 5027, 8886, 86721, 5512, 13383, 26599, 4457, 8278, 76140, 8603, 58556, 3533, 6771, 7899, 24622, 29734, 88497, 28596, 3973, 7107, 9258, 40325, 58431, 17251, 3085, 19008, 22201, 9468, 43517, 220, 13023, 16701, 21281, 24287, 38302, 50968, 1333, 46093, 30811, 53486, 64101, 90820, 3197, 16516, 16605, 20165, 50857, 17022, 35379, 68530, 5976, 8427, 18608, 3199, 8993, 27657, 4\n\nrows 28580\nkeys ['arm', 'dist', 'dm', 'dm_tok', 'm', 'm_B', 'm_I', 'm_raw', 'pid', 'ref0_drift', 'template', 'unit', 'utc']\nn arms 1429\nn pids 20 [('W1|guy', 1429), ('W1|phone', 1429), ('W1|office', 1429)]\nCounter({'head': 1152, 'R#': 50, 'Rpure#': 50, 'Rscaled#': 50, 'RSfork#': 37, 'mlp': 36, 'SPECR#': 20, 'RSprefix#': 8, 'RSall#': 8, 'W#': 5, 'none': 1, 'FSTACK': 1, 'F_MLP': 1, 'F_HEAD': 1, 'F_MST': 1, 'F_CC': 1, 'self_FSTACK': 1, 'xprompt_FSTACK': 1, 'ALL_attn': 1, 'ALL_heads': 1, 'W_all': 1, 'full_none': 1, 'SPEC': 1})\n['none', 'FSTACK', 'F_MLP', 'F_HEAD', 'F_MST', 'F_CC', 'self_FSTACK', 'xprompt_FSTACK', 'ALL_attn', 'ALL_heads', 'W_all', 'W26', 'W27', 'W28', 'W30', 'W32', 'full_none', 'SPEC']\nunit 4\npid 8\ntemplate 4\narm 6\nm 18\nm_raw 18\ndm_tok 3\ndm 3\nref0_drift 3\ndist 4640\nm_I 18\nm_B 19\nutc 29", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [36] THINKING · 2026-10-26 14:30:35 UTC

```
Each unit contains 20 prompts × 1429 patching arms, and since only `pid`, `arm`, `m`, `m_I`, and `m_B` matter for the analysis, I'll drop the large `dist` field. Next I'll locate a Python environment with torch to inspect the `geom_*.pt` fork-state files.
```

### [37] TOOL CALL — Bash · 2026-10-26 14:30:35 UTC

```
Check available Python, torch, numpy and machine resources:
which python3 uv; python3 --version; python3 -c "import torch; print(torch.__version__)" 2>&1 | tail -1; python3 -c "import numpy; print(numpy.__version__)" 2>&1 | tail -1; echo $UV_CACHE_DIR; ls /ai-inventor/aii_data/runs/run_jSassd-YWLVC/.shared_cache 2>/dev/null | head; nproc; free -g | head -2; df -h /tmp | tail -1
```

### [38] TOOL RESULT — Bash · 2026-10-26 14:30:35 UTC

```
{"stdout": "/usr/local/bin/python3\n/usr/bin/uv\nPython 3.12.14\nModuleNotFoundError: No module named 'torch'\n2.2.6\n/ai-inventor/aii_data/runs/run_jSassd-YWLVC/.shared_cache/uv\nhf\npip\nuv\n2\n               total        used        free      shared  buff/cache   available\nMem:             755          66         277           2         419         688\noverlay          20G   64M   20G   1% /", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [39] ASSISTANT · 2026-10-26 14:30:47 UTC

```
No torch is installed system-wide, so I'll build a scratch venv on local disk in the background for inspecting the `.pt` files and keep reading code meanwhile.
```

### [40] TOOL CALL — Bash · 2026-10-26 14:30:47 UTC

```
Create scratch venv with CPU torch for inspection:
SP="/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad"; cd "$SP" && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --python /usr/local/bin/python3.12 "$SP/venv" && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python "$SP/venv/bin/python" --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple torch==2.9.0 numpy==2.0.2 2>&1 | tail -3; "$SP/venv/bin/python" -c "import torch, numpy; print(torch.__version__, numpy.__version__)"
```

### [41] TOOL RESULT — Bash · 2026-10-26 14:30:47 UTC

```
{"stdout": "", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false, "backgroundTaskId": "bs8j69nb5", "backgroundCwdHint": "Session cwd remains /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd; directory changes made by the backgrounded command do not apply to subsequent commands."}
```

### [42] TOOL CALL — Bash · 2026-10-26 14:30:47 UTC

```
Read first part of cmap9.py:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50; sed -n 1,200p $A/src/cmap9.py
```

### [43] TOOL RESULT — Bash · 2026-10-26 14:30:47 UTC

```
{"stdout": "#!/usr/bin/env python3\n\"\"\"B2: cross-model activation patching (CMAP) in Qwen3-8B (bf16, sdpa, one GPU, never both models on it).\n\nStages (one model load each):\n  s1  instruct capture: fork-position caches (MLP outputs, o_proj inputs z and per-head writes, attention outputs,\n      residual at every layer input and at the final-norm input), all-position residuals at RS_LAYERS, all-position\n      MLP outputs / z in the SPEC band (layers 4-24); engine checks against base_subarm and exp41.\n  s2  base capture (same + full-vocab fork logits), base W_O (layers 4-24) and FSTACK-MLP weights for the W arm,\n      matched random sets (needs both caches), basis alignment, REV arm (instruct outputs into the base model).\n  s3  instruct patching: one-token forwards of the fork token over the cached prefix KV (row 0 unpatched) for the\n      single-component sweep (36 MLPs + 1152 heads), the sets, 50 random sets (R / R-pure / R-scaled), placebos,\n      the identity checks, RS-fork(0..36) and the W arm; full forwards for RS-prefix / RS-all and the SPEC arm.\n\nPatch semantics (base values into the instruct run, fork position only unless stated):\n  MLP l       output of layers[l].mlp set to the base output.\n  head (l,h)  o_proj output += base_write_h - z_h @ W_O[:, h].T  (the head's write becomes the base write).\n  attn l      o_proj output set to the base o_proj output.\n  RS(l)       input of layers[l] (l = 36: the final-norm input) set to the base residual.\n  W l         MLP l recomputed from its current input with the BASE MLP weights (fp32, CPU).\n\"\"\"\n\nfrom __future__ import annotations\n\nimport gc\nimport sys\nimport time\nfrom typing import Any\n\nimport numpy as np\nimport torch\nfrom loguru import logger\n\nfrom cfg9 import (CACHE_DIR, D_MODEL, ENGINE_TOL, FSTACK, HEAD_DIM, IDENTITY_TOL, N_HEADS, N_LAYERS, N_RAND,\n                  N_RAND_SPEC, RAND_BAND, RAND_TOL, RAND_TOL_WIDE, RESULTS_DIR, RS_LAYERS, SEED_RAND,\n                  SELF_PATCH_TOL, SPEC_EMBEDDED, SPEC_RAND_BAND, TEMPLATES, TOPK, V41, V43, append_jsonl,\n                  log_deviation, model_path, read_json, read_jsonl, setup_logging, stage_time, utc_now, write_json)\nfrom units9 import load_units\n\nB2_UNITS = (\"B3\", \"T10\")\nSPEC_LAYERS = tuple(range(SPEC_RAND_BAND[0], SPEC_RAND_BAND[1] + 1))\nGEOM_LAYER = 31          # input of layer 31 = output of block 30 (F8)\nMLP_W_LAYERS = (26, 27, 28, 30, 32)\nROWS = 40                # one-token rows per chunk\nFROWS = 8                # full-forward rows per chunk\n\n\n# ================================================================================================ keys\ndef parse(k: str) -> tuple[str, int, int]:\n    p = k.split(\"|\")\n    return (p[0], int(p[1][1:]), int(p[2][1:]) if len(p) > 2 else -1)\n\n\ndef key(kind: str, l: int, h: int = -1) -> str:\n    return f\"mlp|L{l}\" if kind == \"mlp\" else f\"head|L{l}|H{h}\"\n\n\ndef exp41_to_key(k: str) -> tuple[str, str]:\n    \"\"\"'mlp|L27|H-1|DEC' -> ('mlp|L27', 'DEC').\"\"\"\n    kind, l, h, c = k.split(\"|\")\n    return (f\"mlp|{l}\" if kind == \"mlp\" else f\"head|{l}|{h}\"), c\n\n\ndef node_sets() -> dict[str, list[str]]:\n    s = read_json(V41 / \"results\" / \"summary.json\")\n    out = {\"FSTACK\": list(FSTACK), \"F_MLP\": [k for k in FSTACK if k.startswith(\"mlp\")],\n           \"F_HEAD\": [k for k in FSTACK if k.startswith(\"head\")]}\n    for name, c in ((\"F_MST\", \"C1forced\"), (\"F_CC\", \"C2a\")):\n        ks = []\n        for r in s[\"validation\"][c][\"node_pass\"]:\n            k, cl = exp41_to_key(r[\"node\"])\n            if r[\"both\"] and cl == \"DEC\":\n                ks.append(k)\n        out[name] = ks\n    return out\n\n\ndef spec_sets() -> dict[str, list[str]]:\n    out = {}\n    for unit, cname in ((\"B3\", \"C1nat\"), (\"T10\", \"C2a\")):\n        top15 = read_json(V41 / \"results\" / \"summary.json\")[\"circuits\"][cname][\"top15\"]\n        top15 = [t if isinstance(t, str) else t.get(\"node\") for t in top15]\n        ks = [exp41_to_key(k)[0] for k in top15 if exp41_to_key(k)[1] == \"SPEC\"][:5]\n        if ks != SPEC_EMBEDDED[unit]:\n            log_deviation(f\"spec_set_{unit}\", f\"SPEC set from circuit_{cname}.json top15 {ks} differs from the \"\n                                              f\"embedded list {SPEC_EMBEDDED[unit]}; the file's list is used\")\n        out[unit] = ks or SPEC_EMBEDDED[unit]\n    return out\n\n\ndef exp41_top15_dec() -> set[str]:\n    s = read_json(V41 / \"results\" / \"summary.json\")\n    out = set()\n    for c, v in s[\"circuits\"].items():\n        for k in v.get(\"top15\") or []:\n            kk, cl = exp41_to_key(k if isinstance(k, str) else k[\"node\"])\n            if cl == \"DEC\":\n                out.add(kk)\n    return out\n\n\n# ================================================================================================ model\nSTATE: dict[str, Any] = {}\n\n\ndef load(which: str) -> tuple[Any, Any]:\n    from transformers import AutoModelForCausalLM, AutoTokenizer\n    t0 = time.time()\n    path = model_path(which)\n    tok = AutoTokenizer.from_pretrained(path)\n    free0, _ = torch.cuda.mem_get_info(0)\n    model = AutoModelForCausalLM.from_pretrained(path, dtype=torch.bfloat16, attn_implementation=\"sdpa\",\n                                                 device_map={\"\": 0}, low_cpu_mem_usage=True)\n    model.eval()\n    model.requires_grad_(False)\n    gc.collect()\n    torch.cuda.empty_cache()\n    torch.cuda.set_per_process_memory_fraction(0.97, 0)\n    free, total = torch.cuda.mem_get_info(0)\n    info = {\"model\": which, \"path_snapshot\": path.split(\"/\")[-1], \"load_s\": round(time.time() - t0, 1),\n            \"free_vram_before_GB\": round(free0 / 1e9, 2), \"free_vram_after_GB\": round(free / 1e9, 2),\n            \"gpu\": torch.cuda.get_device_name(0)}\n    logger.info(f\"loaded {which}: {info}\")\n    STATE.update(model=model, tok=tok, which=which, info=info)\n    return model, tok\n\n\ndef unload() -> None:\n    for k in (\"model\",):\n        STATE.pop(k, None)\n    gc.collect()\n    torch.cuda.empty_cache()\n\n\nclass Readout:\n    \"\"\"fp32 readout from the final-norm hidden state: m = lse(z[D]) - lse(z[A]); m_tok = z[a] - z[b].\"\"\"\n\n    def __init__(self, model: Any, fork: dict[str, Any], tok: Any):\n        W = model.lm_head.weight\n        self.D, self.A = list(fork[\"D\"]), list(fork[\"A\"])\n        self.WD = W[self.D].float()\n        self.WA = W[self.A].float()\n        if fork.get(\"tok_a\"):\n            a = tok(fork[\"tok_a\"], add_special_tokens=False)[\"input_ids\"][0]\n            b = tok(fork[\"tok_b\"], add_special_tokens=False)[\"input_ids\"][0]\n            self.Wab = W[[a, b]].float()\n        else:\n            self.Wab = None\n\n    def __call__(self, h: torch.Tensor) -> dict[str, torch.Tensor]:\n        hf = h.float()\n        m = torch.logsumexp(hf @ self.WD.T, -1) - torch.logsumexp(hf @ self.WA.T, -1)\n        out = {\"m\": m}\n        if self.Wab is not None:\n            z = hf @ self.Wab.T\n            out[\"m_tok\"] = z[..., 0] - z[..., 1]\n        return out\n\n\ndef bf16_logits(model: Any, h: torch.Tensor) -> torch.Tensor:\n    return model.lm_head(h).float()\n\n\ndef dist_summary(lg: torch.Tensor, D: list[int], A: list[int], k: int = TOPK) -> dict[str, Any]:\n    lp = torch.log_softmax(lg.float(), -1)\n    ent = float(-(lp.exp() * lp).sum())\n    top = torch.topk(lp, k)\n    return {\"entropy\": ent, \"top_ids\": top.indices.tolist(), \"top_lp\": [round(float(x), 5) for x in top.values],\n            \"pD\": float(lp[D].exp().sum()), \"pA\": float(lp[A].exp().sum()),\n            \"m_bf16\": float(torch.logsumexp(lp[D], 0) - torch.logsumexp(lp[A], 0)), \"argmax\": int(lp.argmax())}\n\n\n# ================================================================================================ capture\n@torch.no_grad()\ndef capture(model: Any, ids: list[int], spec_band: bool = True) -> dict[str, torch.Tensor]:\n    \"\"\"One forward over ids; returns CPU bf16 tensors (fork = last position).\"\"\"\n    L = N_LAYERS\n    rin: dict[int, torch.Tensor] = {}\n    rall: dict[int, torch.Tensor] = {}\n    mlp: dict[int, torch.Tensor] = {}\n    mall: dict[int, torch.Tensor] = {}\n    z: dict[int, torch.Tensor] = {}\n    zall: dict[int, torch.Tensor] = {}\n    att: dict[int, torch.Tensor] = {}\n    hs = []\n    layers = model.model.layers\n\n    def pre_layer(l):\n        def f(m, args, kwargs):\n            x = args[0] if args else kwargs[\"hidden_states\"]\n            rin[l] = x[0, -1].detach().to(torch.bfloat16).cpu()\n            if l in RS_LAYERS:\n                rall[l] = x[0].detach().to(torch.bfloat16).cpu()\n        return f\n\n    def pre_norm(m, args, kwargs):\n        x = args[0] if args else kwargs[\"hidden_states\"]\n        rin[L] = x[0, -1].detach().to(torch.bfloat16).cpu()\n\n    def mlp_hook(l):\n        def f(m, inp, out):", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [44] TOOL CALL — Bash · 2026-10-26 14:30:51 UTC

```
Find geometry capture code in cmap9.py:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50; grep -n "geom\|GEOM" $A/src/cmap9.py | head -40; echo; sed -n 200,420p $A/src/cmap9.py
```

### [45] TOOL RESULT — Bash · 2026-10-26 14:30:51 UTC

```
{"stdout": "41:GEOM_LAYER = 31          # input of layer 31 = output of block 30 (F8)\n556:                store[\"geom\"] = x[:, -1].detach().to(torch.bfloat16).cpu()\n584:               want_dist: set[int], want_geom: set[int], D: list[int], A: list[int],\n600:        hs = ot.hooks(chunk, capture_l=GEOM_LAYER, store=store)\n629:            if gi in want_geom:\n630:                rec[\"geom\"] = store[\"geom\"][j].clone()\n859:            want_geom = {nm2i[k] for k in (\"none\", \"FSTACK\", \"RSfork23\", \"RSfork36\")} | {nm2i[f\"R{s}\"]\n861:            res = run_onetok(model, ot, kv, ids[-1], len(ids) - 1, rows, Rd, want_dist, want_geom, f[\"D\"], f[\"A\"])\n863:            out_rows, geom = [], {}\n870:                if \"geom\" in rr:\n871:                    geom[nm] = rr[\"geom\"]\n913:            torch.save(geom, CACHE_DIR / f\"geom_{u}_{pi:02d}.pt\")\n\n        def f(m, inp, out):\n            mlp[l] = out[0, -1].detach().to(torch.bfloat16).cpu()\n            if spec_band and l in SPEC_LAYERS:\n                mall[l] = out[0].detach().to(torch.bfloat16).cpu()\n        return f\n\n    def o_hook(l):\n        def f(m, inp, out):\n            zz = inp[0]\n            z[l] = zz[0, -1].detach().to(torch.bfloat16).cpu()\n            att[l] = out[0, -1].detach().to(torch.bfloat16).cpu()\n            if spec_band and l in SPEC_LAYERS:\n                zall[l] = zz[0].detach().to(torch.bfloat16).cpu()\n        return f\n\n    for l in range(L):\n        hs.append(layers[l].register_forward_pre_hook(pre_layer(l), with_kwargs=True))\n        hs.append(layers[l].mlp.register_forward_hook(mlp_hook(l)))\n        hs.append(layers[l].self_attn.o_proj.register_forward_hook(o_hook(l)))\n    hs.append(model.model.norm.register_forward_pre_hook(pre_norm, with_kwargs=True))\n    try:\n        out = model.model(input_ids=torch.tensor([ids], device=\"cuda\"), use_cache=False)\n    finally:\n        for h in hs:\n            h.remove()\n    hfin = out.last_hidden_state[0, -1].detach()\n    # per-head writes at the fork with this model's own W_O\n    writes = torch.zeros(L, N_HEADS, D_MODEL, dtype=torch.bfloat16)\n    for l in range(L):\n        Wo = layers[l].self_attn.o_proj.weight.float().view(D_MODEL, N_HEADS, HEAD_DIM)\n        zz = z[l].cuda().float().view(N_HEADS, HEAD_DIM)\n        writes[l] = torch.einsum(\"hd,ohd->ho\", zz, Wo).to(torch.bfloat16).cpu()\n    res = {\"resid\": torch.stack([rin[l] for l in range(L + 1)]), \"mlp\": torch.stack([mlp[l] for l in range(L)]),\n           \"z\": torch.stack([z[l] for l in range(L)]), \"attn\": torch.stack([att[l] for l in range(L)]),\n           \"writes\": writes, \"resid_all\": torch.stack([rall[l] for l in RS_LAYERS]),\n           \"hfin\": hfin.to(torch.bfloat16).cpu()}\n    if spec_band:\n        res[\"mlp_all\"] = torch.stack([mall[l] for l in SPEC_LAYERS])\n        res[\"z_all\"] = torch.stack([zall[l] for l in SPEC_LAYERS])\n    del out\n    return res\n\n\n@torch.no_grad()\ndef onetok_capture(model: Any, ids: list[int], B: int = ROWS) -> dict[str, torch.Tensor]:\n    \"\"\"Fork-position values on the SAME computation path as the patched runs: a one-token forward of the fork token\n    over the prefix KV with the fixed batch shape B (all rows unpatched; row 0 is read). Patch values and anchors taken\n    from this path make the self-patch exact and remove full-forward vs one-token kernel offsets.\"\"\"\n    kv = prefix_kv(model, ids)\n    L = N_LAYERS\n    rin: dict[int, torch.Tensor] = {}\n    mlp: dict[int, torch.Tensor] = {}\n    z: dict[int, torch.Tensor] = {}\n    att: dict[int, torch.Tensor] = {}\n    hs = []\n    layers = model.model.layers\n\n    def pre_layer(l):\n        def f(m, args, kwargs):\n            x = args[0] if args else kwargs[\"hidden_states\"]\n            rin[l] = x[0, -1].detach().to(torch.bfloat16).cpu()\n        return f\n\n    def pre_norm(m, args, kwargs):\n        x = args[0] if args else kwargs[\"hidden_states\"]\n        rin[L] = x[0, -1].detach().to(torch.bfloat16).cpu()\n\n    def mlp_hook(l):\n        def f(m, inp, out):\n            mlp[l] = out[0, -1].detach().to(torch.bfloat16).cpu()\n        return f\n\n    def o_hook(l):\n        def f(m, inp, out):\n            z[l] = inp[0][0, -1].detach().to(torch.bfloat16).cpu()\n            att[l] = out[0, -1].detach().to(torch.bfloat16).cpu()\n        return f\n\n    for l in range(L):\n        hs.append(layers[l].register_forward_pre_hook(pre_layer(l), with_kwargs=True))\n        hs.append(layers[l].mlp.register_forward_hook(mlp_hook(l)))\n        hs.append(layers[l].self_attn.o_proj.register_forward_hook(o_hook(l)))\n    hs.append(model.model.norm.register_forward_pre_hook(pre_norm, with_kwargs=True))\n    pos = len(ids) - 1\n    try:\n        cache = build_cache(kv, B)\n        o = model.model(input_ids=torch.full((B, 1), ids[-1], device=\"cuda\", dtype=torch.long), past_key_values=cache,\n                        position_ids=torch.full((B, 1), pos, device=\"cuda\"),\n                        cache_position=torch.tensor([pos], device=\"cuda\"), use_cache=True)\n    finally:\n        for h in hs:\n            h.remove()\n    hfin = o.last_hidden_state[0, -1].detach()\n    writes = torch.zeros(L, N_HEADS, D_MODEL, dtype=torch.bfloat16)\n    for l in range(L):\n        Wo = layers[l].self_attn.o_proj.weight.float().view(D_MODEL, N_HEADS, HEAD_DIM)\n        writes[l] = torch.einsum(\"hd,ohd->ho\", z[l].cuda().float().view(N_HEADS, HEAD_DIM), Wo).to(\n            torch.bfloat16).cpu()\n    del o, cache, kv\n    return {\"resid\": torch.stack([rin[l] for l in range(L + 1)]), \"mlp\": torch.stack([mlp[l] for l in range(L)]),\n            \"z\": torch.stack([z[l] for l in range(L)]), \"attn\": torch.stack([att[l] for l in range(L)]),\n            \"writes\": writes, \"hfin\": hfin.to(torch.bfloat16).cpu()}\n\n\n@torch.no_grad()\ndef check_margins(model: Any, tok: Any, units: dict[str, Any], which: str) -> dict[str, Any]:\n    \"\"\"base_arm-style margins (bf16 lm_head logits -> fp32 log_softmax) on the iteration-8 twins (chat and plain).\"\"\"\n    out = {}\n    ref = read_json(V43 / \"results\" / \"base_subarm.json\")[\"tasks\"]\n    for u, t in ((\"CHK_B3\", \"B3\"), (\"CHK_T10\", \"T10\")):\n        U = units[u]\n        f = U[\"forks\"][0]\n        rec = {}\n        for mode in (\"chat\", \"plain\"):\n            ms = []\n            for p in U[\"prompts\"]:\n                ids = (p[\"ids\"] if mode == \"chat\" else p[\"ids_plain\"]) + f[\"opening\"]\n                # exactly iteration 8's engine8.teacher_force call shape (logits_to_keep = len(opening) + 1): the bf16\n                # lm_head output is quantised (0.125-0.25 at |logit| 16-64) and its rounding depends on the GEMM shape\n                o = model(input_ids=torch.tensor([ids], device=\"cuda\"), use_cache=False,\n                          logits_to_keep=len(f[\"opening\"]) + 1)\n                lp = torch.log_softmax(o.logits[0, -1].float().double(), -1)\n                ms.append(float(torch.logsumexp(lp[f[\"D\"]], 0) - torch.logsumexp(lp[f[\"A\"]], 0)))\n            rec[mode] = ms\n        key_ = \"margin_instr\" if which == \"qwen\" else \"margin_base\"\n        key_p = \"margin_instr_template_free\" if which == \"qwen\" else \"margin_base_template_free\"\n        diffs = [abs(a - b) for a, b in zip(rec[\"chat\"], ref[t][key_])]\n        diffs_p = [abs(a - b) for a, b in zip(rec[\"plain\"], ref[t][key_p])]\n        out[t] = {\"chat\": rec[\"chat\"], \"plain\": rec[\"plain\"], \"ref_chat\": ref[t][key_], \"ref_plain\": ref[t][key_p],\n                  \"max_abs_diff_chat\": max(diffs), \"max_abs_diff_plain\": max(diffs_p),\n                  \"pass\": max(diffs) <= ENGINE_TOL}\n        logger.info(f\"engine check {which} {t}: chat {np.round(rec['chat'], 3).tolist()} vs ref \"\n                    f\"{np.round(ref[t][key_], 3).tolist()} (max diff {max(diffs):.4f})\")\n    return out\n\n\ndef stage_capture(which: str, max_prompts: int | None = None) -> None:\n    \"\"\"s1 (which='qwen') / s2 capture part (which='qwen_base').\"\"\"\n    t0 = time.time()\n    model, tok = load(which)\n    units = load_units()\n    tag = \"instr\" if which == \"qwen\" else \"base\"\n    gt: dict[str, Any] = {\"model\": which, \"load\": STATE[\"info\"], \"utc\": utc_now()}\n    gt[\"engine_check\"] = check_margins(model, tok, units, which)\n    for u in B2_UNITS:\n        U = units[u]\n        f = U[\"forks\"][0]\n        R = Readout(model, f, tok)\n        caps, recs = [], []\n        prompts = U[\"prompts\"][:max_prompts] if max_prompts else U[\"prompts\"]\n        for p in prompts:\n            ids = p[\"ids\"] + f[\"opening\"]\n            c = capture(model, ids)\n            c[\"ot\"] = onetok_capture(model, ids)\n            r_ot = R(c[\"ot\"][\"hfin\"].cuda())\n            h = c[\"hfin\"].cuda()\n            r = R(h)\n            lg = bf16_logits(model, h)\n            ds = dist_summary(lg, f[\"D\"], f[\"A\"])\n            rec = {\"pid\": p[\"pid\"], \"m\": float(r[\"m\"]), \"m_tok\": float(r[\"m_tok\"]), **ds, \"n_ids\": len(ids),\n                   \"m_ot\": float(r_ot[\"m\"]), \"m_tok_ot\": float(r_ot[\"m_tok\"])}\n            if which == \"qwen_base\":\n                c[\"logits_full\"] = lg.to(torch.float16).cpu()\n            # opening log-likelihood (on-policy check is instruct-only)\n            if which == \"qwen\":\n                o = model(input_ids=torch.tensor([ids], device=\"cuda\"), use_cache=False)\n                lp = torch.log_softmax(o.logits[0].float(), -1)\n                P = len(p[\"ids\"])\n                op = f[\"opening\"]\n                rec[\"logp_opening\"] = float(sum(lp[P - 1 + j, op[j]] for j in range(len(op))))\n                del o, lp\n            caps.append(c)\n            recs.append(rec)\n        torch.save({\"pids\": [p[\"pid\"] for p in prompts], \"caps\": caps}, CACHE_DIR / f\"{tag}_{u}.pt\")\n        gt[u] = recs\n        if which == \"qwen\":\n            d = [abs(r[\"m_tok\"] - p[\"exp41_m_clean\"]) for r, p in zip(recs, prompts) if p.get(\"exp41_m_clean\")]\n            gt[f\"{u}_exp41_check\"] = {\"max_abs_diff\": max(d) if d else None, \"n\": len(d),\n                                      \"pass\": bool(d) and max(d) <= ENGINE_TOL,\n                                      \"per_prompt\": [(p[\"pid\"], p.get(\"exp41_m_clean\"), r[\"m_tok\"])\n                                                     for r, p in zip(recs, prompts)]}\n            logger.info(f\"exp41 clean-margin check {u}: max |diff| {gt[f'{u}_exp41_check']['max_abs_diff']}\")\n        logger.info(f\"{tag} {u}: m mean {np.mean([r['m'] for r in recs]):.3f} over {len(recs)} prompts\")\n    if which == \"qwen_base\":\n        sd = {}\n        for l in MLP_W_LAYERS:\n            mm = model.model.layers[l].mlp\n            sd[l] = {n: getattr(mm, n).weight.detach().to(torch.bfloat16).cpu() for n in (\"gate_proj\", \"up_proj\",\n                                                                                           \"down_proj\")}\n        torch.save(sd, CACHE_DIR / \"base_mlp_w.pt\")\n        torch.save({l: model.model.layers[l].self_attn.o_proj.weight.detach().to(torch.bfloat16).cpu()\n                    for l in SPEC_LAYERS}, CACHE_DIR / \"base_wo.pt\")\n    write_json(RESULTS_DIR / f\"capture_{tag}.json\", gt)\n    stage_time(f\"capture_{tag}\", time.time() - t0)\n\n\n# ================================================================================================ random sets\ndef delta_norms(ci: dict, cb: dict) -> dict[str, float]:\n    \"\"\"Mean over prompts of ||base - instr|| at the fork for every MLP and head write.\"\"\"\n    acc: dict[str, list[float]] = {}\n    for a, b in zip(ci[\"caps\"], cb[\"caps\"]):\n        a, b = a[\"ot\"], b[\"ot\"]\n        dm = (b[\"mlp\"].float() - a[\"mlp\"].float()).norm(dim=-1)\n        dw = (b[\"writes\"].float() - a[\"writes\"].float()).norm(dim=-1)\n        for l in range(N_LAYERS):\n            acc.setdefault(key(\"mlp\", l), []).append(float(dm[l]))\n            for h in range(N_HEADS):\n                acc.setdefault(key(\"head\", l, h), []).append(float(dw[l, h]))\n    return {k: float(np.mean(v)) for k, v in acc.items()}\n\n\ndef draw_random_sets(norms: dict[str, float], targets: list[str], seed: int, n: int, band: tuple[int, int],\n                     exclude: set[str]) -> dict[str, Any]:\n    \"\"\"For each target node: same type, layer in band, not in exclude; candidates with mean delta norm within\n    x[0.70, 1.43] of the target's (widened to x[0.5, 2] if < 3 candidates). n sets; within a set no repeats.\"\"\"\n    rng = np.random.default_rng(seed)\n    pools, meta = {}, {}\n    for t in targets:\n        kind, _, _ = parse(t)\n        pool = [k for k in norms if parse(k)[0] == kind and band[0] <= parse(k)[1] <= band[1] and k not in exclude]\n        w0 = norms[t]", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [46] TOOL CALL — Bash · 2026-10-26 14:32:29 UTC

```
Inspect REV rows, random sets and gpu tests files:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50; cd /tmp && python3 -I - $A <<'EOF'
import json,sys,collections
A=sys.argv[1]
rev=[json.loads(l) for l in open(A+'/results/b2_rev_B3.jsonl') if l.strip()]
print('REV rows',len(rev),'keys',sorted(rev[0]), 'arms', len(set(r['arm'] for r in rev)), sorted(set(r['arm'] for r in rev))[:8])
print({k:(v if k!='dist' else '...') for k,v in rev[0].items()})
rs=json.load(open(A+'/results/random_sets.json'))
print('random_sets keys', list(rs.keys()))
for u in rs:
    print(u, {k:(type(v).__name__, len(json.dumps(v))) for k,v in rs[u].items()} if isinstance(rs[u],dict) else type(rs[u]))
    if isinstance(rs[u],dict):
        for fam in ('R','Rpure','Rscaled'):
            if fam in rs[u]:
                print('  ',fam, {k:(type(v).__name__, len(json.dumps(v))) for k,v in rs[u][fam].items()})
        print('  meta R:', json.dumps(rs[u]['R'].get('meta'))[:600])
        print('  basis_alignment:', json.dumps(rs[u].get('basis_alignment'))[:600])
for u in ('B3','T10'):
    s=json.load(open(A+f'/results/spec_random_sets_{u}.json'))
    print('spec', u, {k:(type(v).__name__, len(json.dumps(v))) for k,v in s.items()}, json.dumps(s['meta'])[:300], s['n_distinct_sets'])
g=json.load(open(A+'/results/gpu_tests_b2.json'))
print('gpu_tests', json.dumps(g)[:1000])
EOF
```

### [47] TOOL RESULT — Bash · 2026-10-26 14:32:29 UTC

```
{"stdout": "REV rows 1100 keys ['arm', 'm', 'pid', 'unit', 'utc'] arms 55 ['FSTACK', 'F_HEAD', 'F_MLP', 'R0', 'R1', 'R10', 'R11', 'R12']\n{'unit': 'B3', 'pid': 'W1|guy', 'arm': 'none', 'm': -0.8064651489257812, 'utc': '2026-10-23T14:34:46.929241Z'}\nrandom_sets keys ['B3', 'T10']\nB3 {'R': ('dict', 7962), 'Rpure': ('dict', 7947), 'norms_fork': ('dict', 41757), 'basis_alignment': ('dict', 1518)}\n   R {'sets': ('list', 6792), 'meta': ('dict', 1112), 'n_distinct_sets': ('int', 2), 'seed': ('int', 5)}\n   Rpure {'sets': ('list', 6777), 'meta': ('dict', 1112), 'n_distinct_sets': ('int', 2), 'seed': ('int', 5)}\n  meta R: {\"mlp|L26\": {\"tolerance\": [0.5, 2.0], \"n_candidates\": 5, \"norm\": 48.47560424804688, \"n_distinct_drawn\": 5}, \"mlp|L27\": {\"tolerance\": [0.5, 2.0], \"n_candidates\": 5, \"norm\": 63.181694412231444, \"n_distinct_drawn\": 5}, \"mlp|L28\": {\"tolerance\": [0.5, 2.0], \"n_candidates\": 5, \"norm\": 75.10192184448242, \"n_distinct_drawn\": 5}, \"mlp|L30\": {\"tolerance\": [0.7, 1.43], \"n_candidates\": 3, \"norm\": 100.9360580444336, \"n_distinct_drawn\": 3}, \"mlp|L32\": {\"tolerance\": [0.7, 1.43], \"n_candidates\": 4, \"norm\": 125.8778564453125, \"n_distinct_drawn\": 4}, \"head|L23|H10\": {\"tolerance\": [0.7, 1.43], \"n_candidates\": 83\n  basis_alignment: {\"cos_mean_by_layer\": [0.9975947141647339, 0.9959944486618042, 0.9939987063407898, 0.9897481203079224, 0.9820534586906433, 0.9835023880004883, 0.9834517240524292, 0.9850033521652222, 0.9837669134140015, 0.9823377728462219, 0.9771323204040527, 0.975361168384552, 0.9777975082397461, 0.9741487503051758, 0.973845362663269, 0.9750839471817017, 0.9704177975654602, 0.9703636169433594, 0.9637039303779602, 0.962027907371521, 0.9590876698493958, 0.9585423469543457, 0.9542574882507324, 0.9510746002197266, 0.9537575840950012, 0.9546863436698914, 0.9526011347770691, 0.9485535621643066, 0.9482051730155945, \nT10 {'R': ('dict', 7935), 'Rpure': ('dict', 7928), 'norms_fork': ('dict', 41750), 'basis_alignment': ('dict', 1521)}\n   R {'sets': ('list', 6763), 'meta': ('dict', 1114), 'n_distinct_sets': ('int', 2), 'seed': ('int', 5)}\n   Rpure {'sets': ('list', 6755), 'meta': ('dict', 1115), 'n_distinct_sets': ('int', 2), 'seed': ('int', 5)}\n  meta R: {\"mlp|L26\": {\"tolerance\": [0.5, 2.0], \"n_candidates\": 4, \"norm\": 52.227579498291014, \"n_distinct_drawn\": 4}, \"mlp|L27\": {\"tolerance\": [0.5, 2.0], \"n_candidates\": 4, \"norm\": 73.33942184448242, \"n_distinct_drawn\": 4}, \"mlp|L28\": {\"tolerance\": [0.5, 2.0], \"n_candidates\": 3, \"norm\": 91.1974323272705, \"n_distinct_drawn\": 3}, \"mlp|L30\": {\"tolerance\": [0.7, 1.43], \"n_candidates\": 3, \"norm\": 129.5505813598633, \"n_distinct_drawn\": 3}, \"mlp|L32\": {\"tolerance\": [0.7, 1.43], \"n_candidates\": 3, \"norm\": 145.4388740539551, \"n_distinct_drawn\": 3}, \"head|L23|H10\": {\"tolerance\": [0.7, 1.43], \"n_candidates\": 80,\n  basis_alignment: {\"cos_mean_by_layer\": [0.9984180331230164, 0.9957664608955383, 0.9923524856567383, 0.9884111285209656, 0.9876126050949097, 0.9849799275398254, 0.984455943107605, 0.9842661023139954, 0.9808392524719238, 0.9737613797187805, 0.9706354141235352, 0.9711458086967468, 0.96898353099823, 0.9666039347648621, 0.9635331034660339, 0.9633879661560059, 0.9606901407241821, 0.9593429565429688, 0.9531351923942566, 0.9521486163139343, 0.9459081888198853, 0.9438323974609375, 0.9405390620231628, 0.9412720799446106, 0.9388605952262878, 0.9388874769210815, 0.9364051818847656, 0.9340348243713379, 0.9321198463439941, \nspec B3 {'sets': ('list', 1120), 'meta': ('dict', 539), 'n_distinct_sets': ('int', 2), 'seed': ('int', 5), 'norms_spec': ('dict', 24252)} {\"mlp|L20\": {\"tolerance\": [0.7, 1.43], \"n_candidates\": 4, \"norm\": 31.647204780578612, \"n_distinct_drawn\": 3}, \"mlp|L12\": {\"tolerance\": [0.7, 1.43], \"n_candidates\": 7, \"norm\": 16.73056650161743, \"n_distinct_drawn\": 7}, \"mlp|L8\": {\"tolerance\": [0.5, 2.0], \"n_candidates\": 8, \"norm\": 10.270636224746704, 20\nspec T10 {'sets': ('list', 1414), 'meta': ('dict', 565), 'n_distinct_sets': ('int', 2), 'seed': ('int', 5), 'norms_spec': ('dict', 24262)} {\"mlp|L13\": {\"tolerance\": [0.7, 1.43], \"n_candidates\": 8, \"norm\": 16.982659912109376, \"n_distinct_drawn\": 8}, \"head|L11|H13\": {\"tolerance\": [0.7, 1.43], \"n_candidates\": 209, \"norm\": 1.639030510187149, \"n_distinct_drawn\": 18}, \"mlp|L9\": {\"tolerance\": [0.7, 1.43], \"n_candidates\": 4, \"norm\": 12.6184092 20\ngpu_tests {\"B3\": {\"G2_self_patch_dm\": -0.057575225830078125, \"G2_pass\": false, \"G3_identity_attn_minus_RS36\": 0.0, \"G3_identity_heads_minus_RS36\": -0.007236480712890625, \"G3_pass\": true, \"RSfork36_vs_mB\": 0.8884544372558594, \"B1_shape_vs_B40_unpatched\": 0.006244659423828125, \"G4_batched_vs_single_max_abs_dm_diff\": 0.0, \"G4_pass\": true, \"onetok_vs_full_unpatched\": -0.048095703125, \"RSfork36_vs_mB_ot\": 0.8884544372558594, \"utc\": \"2026-10-23T14:47:26.300113Z\"}, \"T10\": {\"G2_self_patch_dm\": -0.0225372314453125, \"G2_pass\": false, \"G3_identity_attn_minus_RS36\": 0.0, \"G3_identity_heads_minus_RS36\": 0.005496978759765625, \"G3_pass\": true, \"RSfork36_vs_mB\": 3.8394508361816406, \"B1_shape_vs_B40_unpatched\": -0.05083465576171875, \"G4_batched_vs_single_max_abs_dm_diff\": 0.0, \"G4_pass\": true, \"onetok_vs_full_unpatched\": -0.07392501831054688, \"RSfork36_vs_mB_ot\": 3.8394508361816406, \"utc\": \"2026-10-23T14:51:04.142373Z\"}}", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [48] TOOL CALL — Bash · 2026-10-26 14:32:37 UTC

```
Inspect geometry cache file contents:
SP="/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad"; cat "$SP/../tasks/bs8j69nb5.output"; A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50; cd /tmp && "$SP/venv/bin/python" -I - $A <<'EOF'
import torch, sys
A=sys.argv[1]
g=torch.load(A+'/cache/geom_B3_00.pt')
print(type(g), len(g))
ks=list(g.keys())
print(ks[:10], ks[-10:])
v=g['none']; print(v.dtype, v.shape, float(v.float().abs().max()), float(v.float().norm()))
import numpy as np
mx=max(float(t.float().abs().max()) for t in g.values())
print('max abs over all', mx)
for k in ('none','FSTACK','RSfork23','RSfork36'):
    print(k, k in g, float((g[k].float()-g['none'].float()).norm()) if k in g else None)
EOF
```

### [49] TOOL RESULT — Bash · 2026-10-26 14:32:37 UTC

```
{"stdout": "2.9.0+cu128 2.0.2\n\n[exited with code 0]\n<class 'dict'> 54\n['none', 'FSTACK', 'R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7'] ['R42', 'R43', 'R44', 'R45', 'R46', 'R47', 'R48', 'R49', 'RSfork23', 'RSfork36']\ntorch.bfloat16 torch.Size([4096]) 258.0 644.1149291992188\nmax abs over all 296.0\nnone True 0.0\nFSTACK True 176.42892456054688\nRSfork23 True 120.8680191040039\nRSfork36 True 0.0", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [50] THINKING · 2026-10-26 14:33:01 UTC

```
Found that the geometry files contain the instruct state and 53 patched fork states as 4096-d bf16 vectors, while the base-model states were in the now-deleted `cache/base_*.pt`. Now I'll read through the rest of the CMAP engine and output builder to accurately describe each patching arm in the notebook text.
```

### [51] TOOL CALL — Bash · 2026-10-26 14:33:01 UTC

```
Read middle part of cmap9.py:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50; sed -n 420,700p $A/src/cmap9.py
```

### [52] TOOL RESULT — Bash · 2026-10-26 14:33:01 UTC

```
{"stdout": "        w0 = norms[t]\n        cand = [k for k in pool if RAND_TOL[0] * w0 <= norms[k] <= RAND_TOL[1] * w0]\n        tol = list(RAND_TOL)\n        if len(cand) < 3:\n            cand = [k for k in pool if RAND_TOL_WIDE[0] * w0 <= norms[k] <= RAND_TOL_WIDE[1] * w0]\n            tol = list(RAND_TOL_WIDE)\n            if len(cand) < 3:\n                cand = sorted(pool, key=lambda k: abs(norms[k] - w0))[:3]\n                tol = \"nearest-3\"\n        pools[t] = sorted(cand)\n        meta[t] = {\"tolerance\": tol, \"n_candidates\": len(cand), \"norm\": w0}\n    sets = []\n    for _ in range(n):\n        s = []\n        for t in targets:\n            c = [k for k in pools[t] if k not in s] or pools[t]\n            s.append(c[int(rng.integers(len(c)))])\n        sets.append(s)\n    for t in targets:\n        j = targets.index(t)\n        meta[t][\"n_distinct_drawn\"] = len({s[j] for s in sets})\n    return {\"sets\": sets, \"meta\": meta, \"n_distinct_sets\": len({tuple(sorted(s)) for s in sets}), \"seed\": seed}\n\n\ndef spec_delta_norms(ci: dict, cb: dict, pos_lists: list[list[int]], Wo_i: dict, Wo_b: dict) -> dict[str, float]:\n    acc: dict[str, list[float]] = {}\n    for a, b, ps in zip(ci[\"caps\"], cb[\"caps\"], pos_lists):\n        pt = torch.tensor(ps)\n        for j, l in enumerate(SPEC_LAYERS):\n            dm = (b[\"mlp_all\"][j][pt].float() - a[\"mlp_all\"][j][pt].float()).norm(dim=-1).mean()\n            acc.setdefault(key(\"mlp\", l), []).append(float(dm))\n            za = a[\"z_all\"][j][pt].cuda().float().view(len(ps), N_HEADS, HEAD_DIM)\n            zb = b[\"z_all\"][j][pt].cuda().float().view(len(ps), N_HEADS, HEAD_DIM)\n            wa = torch.einsum(\"phd,ohd->pho\", za, Wo_i[l].cuda().float().view(D_MODEL, N_HEADS, HEAD_DIM))\n            wb = torch.einsum(\"phd,ohd->pho\", zb, Wo_b[l].cuda().float().view(D_MODEL, N_HEADS, HEAD_DIM))\n            dn = (wb - wa).norm(dim=-1).mean(0).cpu()\n            for h in range(N_HEADS):\n                acc.setdefault(key(\"head\", l, h), []).append(float(dn[h]))\n            del za, zb, wa, wb\n    return {k: float(np.mean(v)) for k, v in acc.items()}\n\n\n# ================================================================================================ patched forwards\nclass OneTok:\n    \"\"\"Row specs for a one-token forward at the fork: list of ops per row.\n    ops: ('mlp', l, vec) | ('head', l, h, vec) | ('attn', l, vec) | ('resid', l, vec) | ('mlpw', l).\"\"\"\n\n    def __init__(self, model: Any, base_w: dict | None = None):\n        self.model = model\n        self.Wo = [model.model.layers[l].self_attn.o_proj.weight.view(D_MODEL, N_HEADS, HEAD_DIM)\n                   for l in range(N_LAYERS)]\n        self.base_w = base_w\n\n    def hooks(self, rows: list[list[tuple]], capture_l: int | None = None, store: dict | None = None) -> list:\n        m = self.model\n        B = len(rows)\n        per_mlp: dict[int, list] = {}\n        per_head: dict[int, list] = {}\n        per_attn: dict[int, list] = {}\n        per_res: dict[int, list] = {}\n        per_w: dict[int, list] = {}\n        for r, ops in enumerate(rows):\n            for op in ops:\n                if op[0] == \"mlp\":\n                    per_mlp.setdefault(op[1], []).append((r, op[2]))\n                elif op[0] == \"head\":\n                    per_head.setdefault(op[1], []).append((r, op[2], op[3]))\n                elif op[0] == \"attn\":\n                    per_attn.setdefault(op[1], []).append((r, op[2]))\n                elif op[0] == \"resid\":\n                    per_res.setdefault(op[1], []).append((r, op[2]))\n                elif op[0] == \"mlpw\":\n                    per_w.setdefault(op[1], []).append(r)\n        hs = []\n        dev = \"cuda\"\n\n        def T(v):\n            return torch.stack([(x if torch.is_tensor(x) else torch.as_tensor(x)).float() for x in v]).to(dev)\n\n        for l in set(per_mlp) | set(per_w):\n            it = per_mlp.get(l, [])\n            rr = torch.tensor([a for a, _ in it], device=dev, dtype=torch.long)\n            vv = T([b for _, b in it]) if it else None\n            wr = per_w.get(l, [])\n\n            def f(mod, inp, out, rr=rr, vv=vv, wr=wr, l=l):\n                out = out.clone()\n                if vv is not None:\n                    out[rr, -1] = vv.to(out.dtype)\n                if wr:\n                    x = inp[0][wr, -1].float().cpu()\n                    W = self.base_w[l]\n                    y = (torch.nn.functional.silu(x @ W[\"gate_proj\"].T) * (x @ W[\"up_proj\"].T)) @ W[\"down_proj\"].T\n                    out[torch.tensor(wr, device=dev), -1] = y.to(dev).to(out.dtype)\n                return out\n            hs.append(m.model.layers[l].mlp.register_forward_hook(f))\n        for l in set(per_head) | set(per_attn):\n            ih = per_head.get(l, [])\n            ia = per_attn.get(l, [])\n            hr = torch.tensor([a for a, _, _ in ih], device=dev, dtype=torch.long)\n            hh = torch.tensor([b for _, b, _ in ih], device=dev, dtype=torch.long)\n            hv = T([c for _, _, c in ih]).float() if ih else None\n            ar = torch.tensor([a for a, _ in ia], device=dev, dtype=torch.long)\n            av = T([b for _, b in ia]) if ia else None\n\n            def g(mod, inp, out, hr=hr, hh=hh, hv=hv, ar=ar, av=av, l=l):\n                out = out.clone()\n                if av is not None:\n                    out[ar, -1] = av.to(out.dtype)\n                if hv is not None:\n                    z = inp[0][hr, -1].float().view(-1, N_HEADS, HEAD_DIM)\n                    zh = z[torch.arange(len(hr), device=dev), hh]                       # [k, 128]\n                    Wb = self.Wo[l][:, hh, :].float().permute(1, 0, 2)                   # [k, 4096, 128]\n                    cur = torch.einsum(\"kd,kod->ko\", zh, Wb)\n                    acc = out[:, -1].float()\n                    acc.index_add_(0, hr, hv - cur)\n                    out[:, -1] = acc.to(out.dtype)\n                return out\n            hs.append(m.model.layers[l].self_attn.o_proj.register_forward_hook(g))\n        for l, it in per_res.items():\n            rr = torch.tensor([a for a, _ in it], device=dev, dtype=torch.long)\n            vv = T([b for _, b in it])\n            mod = m.model.norm if l == N_LAYERS else m.model.layers[l]\n\n            def pre(mod_, args, kwargs, rr=rr, vv=vv):\n                x = args[0] if args else kwargs[\"hidden_states\"]\n                x = x.clone()\n                x[rr, -1] = vv.to(x.dtype)\n                if args:\n                    return (x,) + tuple(args[1:]), kwargs\n                kwargs = dict(kwargs, hidden_states=x)\n                return args, kwargs\n            hs.append(mod.register_forward_pre_hook(pre, with_kwargs=True))\n        if capture_l is not None and store is not None:\n            def capg(mod_, args, kwargs):\n                x = args[0] if args else kwargs[\"hidden_states\"]\n                store[\"geom\"] = x[:, -1].detach().to(torch.bfloat16).cpu()\n            hs.append(m.model.layers[capture_l].register_forward_pre_hook(capg, with_kwargs=True))\n        return hs\n\n\ndef build_cache(kv: list[tuple[torch.Tensor, torch.Tensor]], B: int):\n    from transformers.cache_utils import DynamicCache\n    cache = DynamicCache()\n    for l, (K, V) in enumerate(kv):\n        cache.update(K.expand(B, -1, -1, -1).contiguous(), V.expand(B, -1, -1, -1).contiguous(), l)\n    return cache\n\n\n@torch.no_grad()\ndef prefix_kv(model: Any, ids: list[int]) -> list[tuple[torch.Tensor, torch.Tensor]]:\n    from transformers.cache_utils import DynamicCache\n    cache = DynamicCache()\n    model.model(input_ids=torch.tensor([ids[:-1]], device=\"cuda\"), past_key_values=cache, use_cache=True)\n    if hasattr(cache, \"layers\"):\n        kv = [(L.keys.clone(), L.values.clone()) for L in cache.layers]\n    else:\n        kv = [(K.clone(), V.clone()) for K, V in zip(cache.key_cache, cache.value_cache)]\n    del cache\n    return kv\n\n\n@torch.no_grad()\ndef run_onetok(model: Any, ot: OneTok, kv: list, last_id: int, pos: int, rows: list[list[tuple]], R: Readout,\n               want_dist: set[int], want_geom: set[int], D: list[int], A: list[int],\n               max_rows: int = ROWS) -> list[dict[str, Any]]:\n    \"\"\"rows[0] must be [] (unpatched). Each chunk re-adds an unpatched row 0; dm is relative to that row.\"\"\"\n    out: list[dict[str, Any]] = []\n    body = rows[1:]\n    idx_body = list(range(1, len(rows)))\n    first = None\n    step = max(1, max_rows - 1)\n    for b0 in range(0, max(1, len(body)), step):\n        chunk = [[]] + body[b0:b0 + step]\n        cidx = [0] + idx_body[b0:b0 + step]\n        n_real = len(chunk)\n        chunk = chunk + [[] for _ in range(max_rows - n_real)]      # fixed batch shape (padding rows unpatched)\n        cidx = cidx + [-1] * (max_rows - n_real)\n        B = len(chunk)\n        store: dict[str, Any] = {}\n        hs = ot.hooks(chunk, capture_l=GEOM_LAYER, store=store)\n        try:\n            cache = build_cache(kv, B)\n            o = model.model(input_ids=torch.full((B, 1), last_id, device=\"cuda\", dtype=torch.long),\n                            past_key_values=cache, position_ids=torch.full((B, 1), pos, device=\"cuda\"),\n                            cache_position=torch.tensor([pos], device=\"cuda\"), use_cache=True)\n        finally:\n            for h in hs:\n                h.remove()\n        h = o.last_hidden_state[:, -1]\n        r = R(h)\n        m = r[\"m\"].tolist()\n        mt = r[\"m_tok\"].tolist() if \"m_tok\" in r else [None] * B\n        if first is None:\n            first = m[0]\n        lg = None\n        for j, gi in enumerate(cidx):\n            if gi < 0:\n                continue\n            if j == 0 and gi != 0:\n                continue\n            if gi == 0 and out:\n                continue\n            rec = {\"i\": gi, \"m\": first + (m[j] - m[0]), \"m_raw\": m[j], \"ref0_drift\": m[0] - first,\n                   \"m_tok\": (mt[j] - mt[0]) if mt[j] is not None else None}\n            if gi in want_dist:\n                if lg is None:\n                    lg = bf16_logits(model, h)\n                rec[\"dist\"] = dist_summary(lg[j], D, A)\n            if gi in want_geom:\n                rec[\"geom\"] = store[\"geom\"][j].clone()\n            out.append(rec)\n        del o, cache, lg\n    out.sort(key=lambda d: d[\"i\"])\n    return out\n\n\n@torch.no_grad()\ndef run_full(model: Any, ids: list[int], rows: list[list[tuple]], R: Readout, Wo_b: dict,\n             max_rows: int = FROWS) -> list[dict[str, Any]]:\n    \"\"\"Full forwards; ops: ('rpos', l, pos LongTensor, vals [k, 4096]) | ('mpos', l, pos, vals) |\n    ('hpos', l, h, pos, z_base [k, 128]) (base write = z_base @ W_O_base[:, h].T).\"\"\"\n    m_ = model\n    out = []\n    dev = \"cuda\"\n    for b0 in range(0, len(rows), max_rows - 1):\n        chunk = [[]] + rows[b0:b0 + max_rows - 1]\n        n_real = len(chunk)\n        chunk = chunk + [[] for _ in range(max_rows - n_real)]      # fixed batch shape\n        B = len(chunk)\n        hs = []\n        per_r: dict[int, list] = {}\n        per_m: dict[int, list] = {}\n        per_h: dict[int, list] = {}\n        for r, ops in enumerate(chunk):\n            for op in ops:\n                {\"rpos\": per_r, \"mpos\": per_m, \"hpos\": per_h}[op[0]].setdefault(op[1], []).append((r,) + op[2:])\n        for l, it in per_r.items():\n            def pre(mod_, args, kwargs, it=it):\n                x = args[0] if args else kwargs[\"hidden_states\"]\n                x = x.clone()\n                for r, ps, v in it:\n                    x[r, ps.to(dev)] = v.to(dev).to(x.dtype)\n                if args:\n                    return (x,) + tuple(args[1:]), kwargs\n                return args, dict(kwargs, hidden_states=x)\n            mod = m_.model.norm if l == N_LAYERS else m_.model.layers[l]\n            hs.append(mod.register_forward_pre_hook(pre, with_kwargs=True))\n        for l, it in per_m.items():\n            def f(mod_, inp, o, it=it):\n                o = o.clone()\n                for r, ps, v in it:\n                    o[r, ps.to(dev)] = v.to(dev).to(o.dtype)\n                return o\n            hs.append(m_.model.layers[l].mlp.register_forward_hook(f))\n        for l, it in per_h.items():\n            Wi = m_.model.layers[l].self_attn.o_proj.weight.view(D_MODEL, N_HEADS, HEAD_DIM)\n            Wb = Wo_b[l].to(dev).view(D_MODEL, N_HEADS, HEAD_DIM)\n\n            def g(mod_, inp, o, it=it, Wi=Wi, Wb=Wb):\n                o = o.clone()\n                for r, h, ps, zb in it:\n                    ps = ps.to(dev)\n                    zc = inp[0][r, ps, h * HEAD_DIM:(h + 1) * HEAD_DIM].float()\n                    cur = zc @ Wi[:, h, :].float().T\n                    base = zb.to(dev).float() @ Wb[:, h, :].float().T\n                    o[r, ps] = (o[r, ps].float() + base - cur).to(o.dtype)\n                return o\n            hs.append(m_.model.layers[l].self_attn.o_proj.register_forward_hook(g))\n        try:\n            inp = torch.tensor([ids], device=dev).expand(B, -1).contiguous()\n            o = m_.model(input_ids=inp, use_cache=False)\n        finally:\n            for h in hs:\n                h.remove()\n        r = R(o.last_hidden_state[:, -1])\n        mm = r[\"m\"].tolist()\n        for j in range(1, n_real):\n            out.append({\"m\": mm[j], \"m_ref_row\": mm[0]})\n        if b0 == 0:\n            out.insert(0, {\"m\": mm[0], \"m_ref_row\": mm[0], \"unpatched\": True})", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [53] TOOL CALL — Bash · 2026-10-26 14:33:01 UTC

```
Read last part of cmap9.py:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50; sed -n 700,1000p $A/src/cmap9.py
```

### [54] TOOL RESULT — Bash · 2026-10-26 14:33:01 UTC

```
{"stdout": "            out.insert(0, {\"m\": mm[0], \"m_ref_row\": mm[0], \"unpatched\": True})\n        del o\n    return out\n\n\n# ================================================================================================ stage s2 extras\ndef base_stage_extras(max_prompts: int | None = None) -> None:\n    \"\"\"In the base load (after capture): random sets, basis alignment, REV arm.\"\"\"\n    model, tok = STATE[\"model\"], STATE[\"tok\"]\n    units = load_units()\n    sets = node_sets()\n    rs_all = {}\n    top15 = exp41_top15_dec()\n    for ui, u in enumerate(B2_UNITS):\n        ci = torch.load(CACHE_DIR / f\"instr_{u}.pt\")\n        cb = torch.load(CACHE_DIR / f\"base_{u}.pt\")\n        norms = delta_norms(ci, cb)\n        R = draw_random_sets(norms, FSTACK, SEED_RAND + ui, N_RAND, RAND_BAND, set(FSTACK))\n        Rp = draw_random_sets(norms, FSTACK, SEED_RAND + ui, N_RAND, RAND_BAND, set(FSTACK) | top15)\n        rs_all[u] = {\"R\": R, \"Rpure\": Rp, \"norms_fork\": norms}\n        # basis alignment\n        cos, ratio = [], []\n        for a, b in zip(ci[\"caps\"], cb[\"caps\"]):\n            ra, rb = a[\"ot\"][\"resid\"].float(), b[\"ot\"][\"resid\"].float()\n            cos.append(torch.nn.functional.cosine_similarity(ra, rb, dim=-1).numpy())\n            ratio.append((rb.norm(dim=-1) / ra.norm(dim=-1).clamp_min(1e-6)).numpy())\n        rs_all[u][\"basis_alignment\"] = {\"cos_mean_by_layer\": np.mean(cos, 0).tolist(),\n                                        \"norm_ratio_mean_by_layer\": np.mean(ratio, 0).tolist()}\n        # REV arm: instruct outputs into the base model at the fork\n        f = units[u][\"forks\"][0]\n        Rd = Readout(model, f, tok)\n        ot = OneTok(model)\n        recs = []\n        prompts = units[u][\"prompts\"][:max_prompts] if max_prompts else units[u][\"prompts\"]\n        for pi, p in enumerate(prompts):\n            ids = p[\"ids\"] + f[\"opening\"]\n            kv = prefix_kv(model, ids)\n            a = ci[\"caps\"][pi][\"ot\"]\n\n            def ops_for(keys: list[str]) -> list[tuple]:\n                ops = []\n                for k in keys:\n                    kind, l, h = parse(k)\n                    ops.append((\"mlp\", l, a[\"mlp\"][l]) if kind == \"mlp\" else (\"head\", l, h, a[\"writes\"][l, h]))\n                return ops\n            rows = [[], ops_for(FSTACK), ops_for(sets[\"F_MLP\"]), ops_for(sets[\"F_HEAD\"])]\n            rows += [ops_for(s) for s in R[\"sets\"]]\n            rows += [[(\"resid\", N_LAYERS, a[\"resid\"][N_LAYERS])]]\n            res = run_onetok(model, ot, kv, ids[-1], len(ids) - 1, rows, Rd, set(), set(), f[\"D\"], f[\"A\"])\n            names = [\"none\", \"FSTACK\", \"F_MLP\", \"F_HEAD\"] + [f\"R{s}\" for s in range(N_RAND)] + [\"RS36_instr\"]\n            for nm, rr in zip(names, res):\n                recs.append({\"unit\": u, \"pid\": p[\"pid\"], \"arm\": nm, \"m\": rr[\"m\"], \"utc\": utc_now()})\n            del kv\n        append_jsonl(RESULTS_DIR / f\"b2_rev_{u}.jsonl\", recs)\n        del ci, cb\n        gc.collect()\n    write_json(RESULTS_DIR / \"random_sets.json\", {u: {k: v for k, v in d.items()} for u, d in rs_all.items()})\n\n\n# ================================================================================================ stage s3\ndef stage_patch(max_prompts: int | None = None, units_sel: tuple[str, ...] = B2_UNITS) -> None:\n    t0 = time.time()\n    model, tok = load(\"qwen\")\n    units = load_units()\n    sets = node_sets()\n    specs = spec_sets()\n    rsets = read_json(RESULTS_DIR / \"random_sets.json\")\n    base_w = {l: {k: v.float() for k, v in d.items()} for l, d in torch.load(CACHE_DIR / \"base_mlp_w.pt\").items()}\n    Wo_b = torch.load(CACHE_DIR / \"base_wo.pt\")\n    Wo_i = {l: model.model.layers[l].self_attn.o_proj.weight.detach().cpu() for l in SPEC_LAYERS}\n    ot = OneTok(model, base_w)\n    gpu_tests: dict[str, Any] = {}\n    for ui, u in enumerate(units_sel):\n        U = units[u]\n        f = U[\"forks\"][0]\n        Rd = Readout(model, f, tok)\n        ci = torch.load(CACHE_DIR / f\"instr_{u}.pt\")\n        cb = torch.load(CACHE_DIR / f\"base_{u}.pt\")\n        prompts = U[\"prompts\"][:max_prompts] if max_prompts else U[\"prompts\"]\n        n = len(prompts)\n        R = rsets[u][\"R\"][\"sets\"]\n        Rp = rsets[u][\"Rpure\"][\"sets\"]\n        norms = rsets[u][\"norms_fork\"]\n        # SPEC random sets (needs SPEC-position delta norms; drawn once per unit, committed seed)\n        pos_lists = [p[\"pos\"][\"SPEC\"] for p in prompts]\n        sp_path = RESULTS_DIR / f\"spec_random_sets_{u}.json\"\n        if sp_path.exists():\n            SR = read_json(sp_path)\n        else:\n            snorms = spec_delta_norms({\"caps\": ci[\"caps\"][:n]}, {\"caps\": cb[\"caps\"][:n]}, pos_lists, Wo_i, Wo_b)\n            SR = draw_random_sets(snorms, specs[u], SEED_RAND + 100 + ui, N_RAND_SPEC, SPEC_RAND_BAND,\n                                  set(specs[u]))\n            SR[\"norms_spec\"] = snorms\n            write_json(sp_path, SR)\n        done = {r[\"pid\"] for r in read_jsonl(RESULTS_DIR / f\"b2_tf_{u}.jsonl\")}\n        mB_of = {r[\"pid\"]: r[\"m_ot\"] for r in read_json(RESULTS_DIR / \"capture_base.json\")[u]}\n        for pi, p in enumerate(prompts):\n            if p[\"pid\"] in done:\n                continue\n            tp = time.time()\n            ids = p[\"ids\"] + f[\"opening\"]\n            af, bf = ci[\"caps\"][pi], cb[\"caps\"][pi]          # full-forward caches (RS-prefix / RS-all / SPEC arms)\n            a, b = af[\"ot\"], bf[\"ot\"]                          # one-token-path fork values (one-token arms)\n            bx = cb[\"caps\"][(pi + 1) % len(cb[\"caps\"])][\"ot\"]\n            kv = prefix_kv(model, ids)\n\n            def ops(keys: list[str], src: dict, scale_to: list[str] | None = None) -> list[tuple]:\n                o = []\n                for j, k in enumerate(keys):\n                    kind, l, h = parse(k)\n                    if kind == \"mlp\":\n                        v = src[\"mlp\"][l]\n                        if scale_to is not None:\n                            s = norms[scale_to[j]] / max(norms[k], 1e-6)\n                            v = (a[\"mlp\"][l].float() + s * (src[\"mlp\"][l].float() - a[\"mlp\"][l].float()))\n                        o.append((\"mlp\", l, v))\n                    else:\n                        v = src[\"writes\"][l, h]\n                        if scale_to is not None:\n                            s = norms[scale_to[j]] / max(norms[k], 1e-6)\n                            v = (a[\"writes\"][l, h].float() + s * (src[\"writes\"][l, h].float() -\n                                                                  a[\"writes\"][l, h].float()))\n                        o.append((\"head\", l, h, v))\n                return o\n            names: list[str] = [\"none\"]\n            rows: list[list[tuple]] = [[]]\n            for l in range(N_LAYERS):\n                names.append(key(\"mlp\", l))\n                rows.append(ops([key(\"mlp\", l)], b))\n            for l in range(N_LAYERS):\n                for h in range(N_HEADS):\n                    names.append(key(\"head\", l, h))\n                    rows.append(ops([key(\"head\", l, h)], b))\n            for sname in (\"FSTACK\", \"F_MLP\", \"F_HEAD\", \"F_MST\", \"F_CC\"):\n                names.append(sname)\n                rows.append(ops(sets[sname], b))\n            for s in range(len(R)):\n                names.append(f\"R{s}\")\n                rows.append(ops(R[s], b))\n            for s in range(len(Rp)):\n                names.append(f\"Rpure{s}\")\n                rows.append(ops(Rp[s], b))\n            for s in range(len(R)):\n                names.append(f\"Rscaled{s}\")\n                rows.append(ops(R[s], b, scale_to=FSTACK))\n            names += [\"self_FSTACK\", \"xprompt_FSTACK\"]\n            rows += [ops(FSTACK, a), ops(FSTACK, bx)]\n            allc = [(\"resid\", 0, b[\"resid\"][0])] + [(\"mlp\", l, b[\"mlp\"][l]) for l in range(N_LAYERS)]\n            names += [\"ALL_attn\", \"ALL_heads\"]\n            rows += [allc + [(\"attn\", l, b[\"attn\"][l]) for l in range(N_LAYERS)],\n                     allc + [(\"head\", l, h, b[\"writes\"][l, h]) for l in range(N_LAYERS) for h in range(N_HEADS)]]\n            for l in range(N_LAYERS + 1):\n                names.append(f\"RSfork{l}\")\n                rows.append([(\"resid\", l, b[\"resid\"][l])])\n            names += [\"W_all\"] + [f\"W{l}\" for l in MLP_W_LAYERS]\n            rows += [[(\"mlpw\", l) for l in MLP_W_LAYERS]] + [[(\"mlpw\", l)] for l in MLP_W_LAYERS]\n            nm2i = {nm: i for i, nm in enumerate(names)}\n            want_dist = {nm2i[k] for k in (\"none\", \"FSTACK\", \"F_MST\", \"F_CC\", \"RSfork23\", \"RSfork36\", \"ALL_attn\")}\n            want_dist |= {nm2i[f\"R{s}\"] for s in range(len(R))}\n            want_geom = {nm2i[k] for k in (\"none\", \"FSTACK\", \"RSfork23\", \"RSfork36\")} | {nm2i[f\"R{s}\"]\n                                                                                         for s in range(len(R))}\n            res = run_onetok(model, ot, kv, ids[-1], len(ids) - 1, rows, Rd, want_dist, want_geom, f[\"D\"], f[\"A\"])\n            m_none = res[0][\"m\"]\n            out_rows, geom = [], {}\n            for nm, rr in zip(names, res):\n                rec = {\"unit\": u, \"pid\": p[\"pid\"], \"template\": p[\"template\"], \"arm\": nm, \"m\": rr[\"m\"],\n                       \"m_raw\": rr[\"m_raw\"], \"dm_tok\": rr[\"m_tok\"], \"dm\": rr[\"m\"] - m_none,\n                       \"ref0_drift\": rr[\"ref0_drift\"]}\n                if \"dist\" in rr:\n                    rec[\"dist\"] = rr[\"dist\"]\n                if \"geom\" in rr:\n                    geom[nm] = rr[\"geom\"]\n                out_rows.append(rec)\n            # full-forward arms: RS-prefix / RS-all and the SPEC arm\n            P = len(ids)\n            fpos = torch.arange(P - 1)\n            apos = torch.arange(P)\n            frows, fnames = [], []\n            for j, l in enumerate(RS_LAYERS):\n                fnames.append(f\"RSprefix{l}\")\n                frows.append([(\"rpos\", l, fpos, bf[\"resid_all\"][j][:P - 1])])\n                fnames.append(f\"RSall{l}\")\n                frows.append([(\"rpos\", l, apos, bf[\"resid_all\"][j])])\n            sp = torch.tensor(p[\"pos\"][\"SPEC\"])\n\n            def spec_ops(keys: list[str]) -> list[tuple]:\n                o = []\n                for k in keys:\n                    kind, l, h = parse(k)\n                    j = SPEC_LAYERS.index(l)\n                    if kind == \"mlp\":\n                        o.append((\"mpos\", l, sp, bf[\"mlp_all\"][j][sp]))\n                    else:\n                        o.append((\"hpos\", l, h, sp, bf[\"z_all\"][j][sp][:, h * HEAD_DIM:(h + 1) * HEAD_DIM]))\n                return o\n            fnames.append(\"SPEC\")\n            frows.append(spec_ops(specs[u]))\n            for s, ss in enumerate(SR[\"sets\"]):\n                fnames.append(f\"SPECR{s}\")\n                frows.append(spec_ops(ss))\n            fres = run_full(model, ids, frows, Rd, Wo_b)\n            m_full0 = fres[0][\"m\"]\n            for nm, rr in zip([\"full_none\"] + fnames, fres):\n                dmf = rr[\"m\"] - rr[\"m_ref_row\"]\n                out_rows.append({\"unit\": u, \"pid\": p[\"pid\"], \"template\": p[\"template\"], \"arm\": nm,\n                                 \"m\": (m_full0 if nm == \"full_none\" else m_none + dmf), \"m_raw\": rr[\"m\"],\n                                 \"m_tok\": None, \"dm\": dmf, \"ref0_drift\": rr[\"m_ref_row\"] - m_full0})\n            mB = mB_of[p[\"pid\"]]\n            for rr in out_rows:\n                rr[\"m_I\"] = m_none\n                rr[\"m_B\"] = mB\n                rr[\"utc\"] = utc_now()\n            append_jsonl(RESULTS_DIR / f\"b2_tf_{u}.jsonl\", out_rows)\n            torch.save(geom, CACHE_DIR / f\"geom_{u}_{pi:02d}.pt\")\n            # GPU tests on the first prompt of each unit\n            if pi == 0:\n                gpu_tests[u] = gpu_checks(model, ot, kv, ids, Rd, f, a, b, out_rows)\n                write_json(RESULTS_DIR / \"gpu_tests_b2.json\", gpu_tests)\n            del kv\n            dt = time.time() - tp\n            byarm = {r[\"arm\"]: r for r in out_rows}\n            gap = m_none - mB\n            logger.info(f\"[{u}] {p['pid']} {dt:.1f}s | m_I {m_none:.3f} m_B {mB:.3f} | share FSTACK \"\n                        f\"{(m_none - byarm['FSTACK']['m']) / gap:.3f} RS36 {(m_none - byarm['RSfork36']['m']) / gap:.3f} \"\n                        f\"RS23 {(m_none - byarm['RSfork23']['m']) / gap:.3f} self {byarm['self_FSTACK']['dm']:.4f} \"\n                        f\"ALL-RS36 {byarm['ALL_attn']['m'] - byarm['RSfork36']['m']:.4f}\")\n        del ci, cb\n        gc.collect()\n        torch.cuda.empty_cache()\n    stage_time(\"b2_patch\", time.time() - t0, max_prompts=max_prompts)\n\n\n@torch.no_grad()\ndef gpu_checks(model: Any, ot: OneTok, kv: list, ids: list[int], Rd: Readout, f: dict, a: dict, b: dict,\n               rows: list[dict]) -> dict[str, Any]:\n    by = {r[\"arm\"]: r for r in rows}\n    out: dict[str, Any] = {}\n    out[\"G2_self_patch_dm\"] = by[\"self_FSTACK\"][\"dm\"]\n    out[\"G2_pass\"] = abs(by[\"self_FSTACK\"][\"dm\"]) <= SELF_PATCH_TOL\n    out[\"G3_identity_attn_minus_RS36\"] = by[\"ALL_attn\"][\"m\"] - by[\"RSfork36\"][\"m\"]\n    out[\"G3_identity_heads_minus_RS36\"] = by[\"ALL_heads\"][\"m\"] - by[\"RSfork36\"][\"m\"]\n    out[\"G3_pass\"] = abs(out[\"G3_identity_heads_minus_RS36\"]) <= IDENTITY_TOL\n    out[\"RSfork36_vs_mB\"] = by[\"RSfork36\"][\"m\"] - by[\"RSfork36\"][\"m_B\"]\n    # G4 batching: 8 single-MLP rows batched vs one at a time (each with its own unpatched row 0)\n    keys = [key(\"mlp\", l) for l in (5, 12, 20, 26, 27, 30, 33, 35)]\n    rows_b = [[]] + [[(\"mlp\", parse(k)[1], b[\"mlp\"][parse(k)[1]])] for k in keys]\n    rb = run_onetok(model, ot, kv, ids[-1], len(ids) - 1, rows_b, Rd, set(), set(), f[\"D\"], f[\"A\"])\n    diffs = []\n    for j, k in enumerate(keys):\n        r1 = run_onetok(model, ot, kv, ids[-1], len(ids) - 1, [[], rows_b[j + 1]], Rd, set(), set(), f[\"D\"], f[\"A\"])\n        diffs.append(abs((rb[j + 1][\"m\"] - rb[0][\"m\"]) - (r1[1][\"m\"] - r1[0][\"m\"])))\n    # unbatched (B = 1 shape) unpatched one-token margin vs the fixed-shape row 0, for the record\n    r_b1 = run_onetok(model, ot, kv, ids[-1], len(ids) - 1, [[]], Rd, set(), set(), f[\"D\"], f[\"A\"], max_rows=1)\n    out[\"B1_shape_vs_B40_unpatched\"] = r_b1[0][\"m\"] - rb[0][\"m\"]\n    out[\"G4_batched_vs_single_max_abs_dm_diff\"] = max(diffs)\n    out[\"G4_pass\"] = max(diffs) <= SELF_PATCH_TOL\n    # one-token unpatched vs full forward\n    out[\"onetok_vs_full_unpatched\"] = by[\"none\"][\"m\"] - by[\"full_none\"][\"m\"]\n    out[\"RSfork36_vs_mB_ot\"] = by[\"RSfork36\"][\"m\"] - by[\"RSfork36\"][\"m_B\"]\n    out[\"utc\"] = utc_now()\n    logger.info(f\"GPU checks: {out}\")\n    return out\n\n\nif __name__ == \"__main__\":\n    setup_logging(f\"cmap9_{sys.argv[1]}\")\n    mp = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] != \"all\" else None\n    if sys.argv[1] == \"s1\":\n        stage_capture(\"qwen\", mp)\n    elif sys.argv[1] == \"s2\":\n        stage_capture(\"qwen_base\", mp)\n        base_stage_extras(mp)\n    elif sys.argv[1] == \"s3\":\n        stage_patch(mp)", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [55] THINKING · 2026-10-26 14:33:19 UTC

```
Since `draw_random_sets` is pure numpy on stored delta norms, I can rebuild the 50 null sets in the notebook and verify them against the run's output. Next I'll check the output builder and unit definitions, then pull reference values from the run's summary.
```

### [56] TOOL CALL — Bash · 2026-10-26 14:33:19 UTC

```
Read outputs9.py:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50; cat -n $A/src/outputs9.py | sed -n 1,400p
```

### [57] TOOL RESULT — Bash · 2026-10-26 14:33:19 UTC

```
{"stdout": "     1\t#!/usr/bin/env python3\n     2\t\"\"\"S8 outputs: method_out.json in the exp_gen_sol_out schema.\n     3\t\n     4\tDatasets: b1_forks (unit x fork x prompt x template mode; Gemma it/pt and Llama instruct/base), b2_tf (Qwen unit x\n     5\tprompt with every arm's margin and share), b3_heldout (node x mode x held-out prompt). b2_generation is not produced\n     6\t(S4 dropped; see metadata.not_run). Metadata holds every analysis summary, the commit chain, deviations and costs.\"\"\"\n     7\t\n     8\tfrom __future__ import annotations\n     9\t\n    10\timport json\n    11\tfrom typing import Any\n    12\t\n    13\timport numpy as np\n    14\tfrom loguru import logger\n    15\t\n    16\tfrom cfg9 import (MODELS, ROOT, RESULTS_DIR, model_path, read_json, read_jsonl, setup_logging, utc_now, verify_chain,\n    17\t                  write_json)\n    18\t\n    19\t\n    20\tdef toks() -> dict[str, Any]:\n    21\t    from transformers import AutoTokenizer\n    22\t    return {\"qwen\": AutoTokenizer.from_pretrained(model_path(\"qwen\")),\n    23\t            \"gemma\": AutoTokenizer.from_pretrained(model_path(\"gemma\")),\n    24\t            \"llama\": AutoTokenizer.from_pretrained(model_path(\"llama\"))}\n    25\t\n    26\t\n    27\tdef b1_examples(T: dict, U: dict) -> list[dict[str, Any]]:\n    28\t    ex = []\n    29\t    pairs = {\"gemma\": (\"gemma\", \"gemma_pt\"), \"llama\": (\"llama\", \"llama_base\")}\n    30\t    summ = read_json(RESULTS_DIR / \"b1_summary.json\")\n    31\t    for fam, (ki, kb) in pairs.items():\n    32\t        pi, pb = RESULTS_DIR / f\"b1_tf_{ki}.json\", RESULTS_DIR / f\"b1_tf_{kb}.json\"\n    33\t        if not (pi.exists() and pb.exists()):\n    34\t            continue\n    35\t        I, B = read_json(pi), read_json(pb)\n    36\t        tk = T[fam]\n    37\t        for u, ru in I[\"units\"].items():\n    38\t            Uu = U[u]\n    39\t            su = summ[\"units\"].get(u, {})\n    40\t            kept = set(su.get(\"on_policy\", {}).get(\"kept\", []))\n    41\t            byB = {r[\"pid\"]: r for r in B[\"units\"][u][\"prompts\"]}\n    42\t            byP = {p[\"pid\"]: p for p in Uu[\"prompts\"]}\n    43\t            for r in ru[\"prompts\"]:\n    44\t                p = byP[r[\"pid\"]]\n    45\t                for f in Uu[\"forks\"]:\n    46\t                    fid = f[\"fork_id\"]\n    47\t                    for mode in (\"chat\", \"plain\"):\n    48\t                        a, b = r[\"forks\"][fid][mode], byB[r[\"pid\"]][\"forks\"][fid][mode]\n    49\t                        ids = (p[\"ids\"] if mode == \"chat\" else p[\"ids_plain\"]) + f[\"opening\"]\n    50\t                        ex.append({\n    51\t                            \"input\": tk.decode(ids),\n    52\t                            \"output\": tk.decode([a[\"argmax\"]]),\n    53\t                            \"predict_instruct_argmax\": tk.decode([a[\"argmax\"]]),\n    54\t                            \"predict_base_argmax\": tk.decode([b[\"argmax\"]]),\n    55\t                            \"metadata_family\": fam, \"metadata_unit\": u, \"metadata_fork_id\": fid,\n    56\t                            \"metadata_prompt_id\": r[\"pid\"], \"metadata_template_mode\": mode,\n    57\t                            \"metadata_on_policy_kept\": r[\"pid\"] in kept,\n    58\t                            \"metadata_descriptive_only\": bool(su.get(\"descriptive_only\")),\n    59\t                            \"metadata_D_tokens\": f[\"D_str\"], \"metadata_A_tokens\": f[\"A_str\"],\n    60\t                            \"metadata_margin_instr\": a[\"margin\"], \"metadata_margin_base\": b[\"margin\"],\n    61\t                            \"metadata_gain\": a[\"margin\"] - b[\"margin\"], \"metadata_pD_instr\": a[\"pD\"],\n    62\t                            \"metadata_pD_base\": b[\"pD\"], \"metadata_pA_instr\": a[\"pA\"], \"metadata_pA_base\": b[\"pA\"],\n    63\t                            \"metadata_entropy_instr\": a[\"entropy\"], \"metadata_entropy_base\": b[\"entropy\"],\n    64\t                            \"metadata_logp_opening_instr\": a[\"logp_opening\"],\n    65\t                            \"metadata_models\": [MODELS[ki][0], MODELS[kb][0]]})\n    66\t    return ex\n    67\t\n    68\t\n    69\tdef b2_examples(T: dict, U: dict) -> list[dict[str, Any]]:\n    70\t    ex = []\n    71\t    tk = T[\"qwen\"]\n    72\t    for u in (\"B3\", \"T10\"):\n    73\t        rows = read_jsonl(RESULTS_DIR / f\"b2_tf_{u}.jsonl\")\n    74\t        if not rows:\n    75\t            continue\n    76\t        b2s = read_json(RESULTS_DIR / \"b2_summary.json\")[\"units\"][u]\n    77\t        rsh = b2s[\"null_R\"][\"shares\"]\n    78\t        med = int(np.argsort(rsh)[len(rsh) // 2])\n    79\t        by: dict[str, dict[str, dict]] = {}\n    80\t        for r in rows:\n    81\t            by.setdefault(r[\"pid\"], {})[r[\"arm\"]] = r\n    82\t        f = U[u][\"forks\"][0]\n    83\t        P = {p[\"pid\"]: p for p in U[u][\"prompts\"]}\n    84\t        base_cap = {r[\"pid\"]: r for r in read_json(RESULTS_DIR / \"capture_base.json\")[u]}\n    85\t        for pid, arms in by.items():\n    86\t            mI, mB = arms[\"none\"][\"m_I\"], arms[\"none\"][\"m_B\"]\n    87\t            gap = mI - mB\n    88\t\n    89\t            def sh(a: str) -> float | None:\n    90\t                return (mI - arms[a][\"m\"]) / gap if a in arms and abs(gap) > 1e-9 else None\n    91\t            am = lambda a: tk.decode([arms[a][\"dist\"][\"argmax\"]]) if a in arms and \"dist\" in arms[a] else \"\"  # noqa\n    92\t            ex.append({\n    93\t                \"input\": tk.decode(P[pid][\"ids\"] + f[\"opening\"]),\n    94\t                \"output\": am(\"none\"),\n    95\t                \"predict_instruct_unpatched\": am(\"none\"),\n    96\t                \"predict_FSTACK_patched\": am(\"FSTACK\"),\n    97\t                \"predict_median_random_set_patched\": am(f\"R{med}\"),\n    98\t                \"predict_RSfork36_patched\": am(\"RSfork36\"),\n    99\t                \"predict_base_model\": tk.decode([base_cap[pid][\"argmax\"]]),\n   100\t                \"metadata_unit\": u, \"metadata_prompt_id\": pid, \"metadata_template\": P[pid][\"template\"],\n   101\t                \"metadata_D_tokens\": f[\"D_str\"], \"metadata_A_tokens\": f[\"A_str\"],\n   102\t                \"metadata_m_I\": mI, \"metadata_m_B\": mB, \"metadata_gap\": gap,\n   103\t                \"metadata_m_FSTACK\": arms[\"FSTACK\"][\"m\"], \"metadata_share_FSTACK\": sh(\"FSTACK\"),\n   104\t                \"metadata_share_F_MLP\": sh(\"F_MLP\"), \"metadata_share_F_HEAD\": sh(\"F_HEAD\"),\n   105\t                \"metadata_share_F_MST\": sh(\"F_MST\"), \"metadata_share_F_CC\": sh(\"F_CC\"),\n   106\t                \"metadata_share_SPEC\": sh(\"SPEC\"), \"metadata_share_RSfork23\": sh(\"RSfork23\"),\n   107\t                \"metadata_share_RSfork36\": sh(\"RSfork36\"), \"metadata_share_RSprefix23\": sh(\"RSprefix23\"),\n   108\t                \"metadata_share_RSall23\": sh(\"RSall23\"), \"metadata_share_W_all\": sh(\"W_all\"),\n   109\t                \"metadata_share_median_random_set\": sh(f\"R{med}\"),\n   110\t                \"metadata_share_random_sets\": [sh(f\"R{s}\") for s in range(50)],\n   111\t                \"metadata_self_patch_dm\": arms[\"self_FSTACK\"][\"dm\"],\n   112\t                \"metadata_identity_heads_minus_RS36\": arms[\"ALL_heads\"][\"m\"] - arms[\"RSfork36\"][\"m\"]})\n   113\t    return ex\n   114\t\n   115\t\n   116\tdef b3_examples() -> list[dict[str, Any]]:\n   117\t    rows = read_jsonl(RESULTS_DIR / \"b3_heldout_rows.jsonl\")\n   118\t    s = read_json(RESULTS_DIR / \"b3_summary.json\")\n   119\t    ex = []\n   120\t    for key, v in s[\"per_node\"].items():\n   121\t        tag = f\"{v['variant']}|{v['mode']}|{v['node']}\"\n   122\t        for r in rows:\n   123\t            node = r[\"res\"].get(f\"{tag}|node\")\n   124\t            rv = [r[\"res\"][f\"{tag}|r{j}\"] for j in range(50) if f\"{tag}|r{j}\" in r[\"res\"]]\n   125\t            if node is None or not rv:\n   126\t                continue\n   127\t            ex.append({\"input\": f\"C1forced held-out prompt {r['vid']} (art_18XvfcJJZi1O k3prompts.b3_forced) + the \"\n   128\t                                f\"61-token MST opening; edit {v['mode']} of {v['node']} ({v['variant']} means)\",\n   129\t                       \"output\": r[\"side\"],\n   130\t                       \"predict_node_oriented_dm\": f\"{node:.6f}\",\n   131\t                       \"predict_random_mean_oriented_dm\": f\"{float(np.mean(rv)):.6f}\",\n   132\t                       \"metadata_node\": v[\"node\"], \"metadata_mode\": v[\"mode\"], \"metadata_variant\": v[\"variant\"],\n   133\t                       \"metadata_prompt\": r[\"vid\"], \"metadata_d\": node - float(np.mean(rv)),\n   134\t                       \"metadata_frac_random_beaten\": float(np.mean(np.asarray(rv) < node)),\n   135\t                       \"metadata_label\": v[\"label\"]})\n   136\t    return ex\n   137\t\n   138\t\n   139\tdef gen_examples() -> list[dict[str, Any]]:\n   140\t    raw = read_jsonl(ROOT / \"data\" / \"samples.jsonl\")\n   141\t    lab = {r[\"sid\"]: r for r in read_jsonl(ROOT / \"data\" / \"labels_gen.jsonl\")}\n   142\t    by: dict[tuple, dict[str, dict]] = {}\n   143\t    for r in raw:\n   144\t        by.setdefault((r[\"task\"], r[\"template\"], r[\"slot\"]), {})[r[\"arm\"]] = r\n   145\t    ex = []\n   146\t    for (u, w, slot), arms in sorted(by.items()):\n   147\t        if \"TWIN\" not in arms:\n   148\t            continue\n   149\t        def lp(a):\n   150\t            if a not in arms or arms[a][\"sid\"] not in lab:\n   151\t                return \"\"\n   152\t            L = lab[arms[a][\"sid\"]]\n   153\t            return f\"{L['label']}|{'pass' if L['passed'] else 'fail'}\"\n   154\t        tw = arms[\"TWIN\"]\n   155\t        ex.append({\"input\": f\"{u} prompt {tw['prompt_id']} (template {w}), CRN slot {slot} (seed {tw['seed']}); the \"\n   156\t                            f\"instruct model's on-policy opening is prefilled; arms differ only at the fork token\",\n   157\t                   \"output\": lp(\"TWIN\"), \"predict_FSTACK\": lp(\"FSTACK\"), \"predict_RAND\": lp(\"RAND\"),\n   158\t                   \"predict_FPD\": lp(\"FPD\"),\n   159\t                   \"metadata_unit\": u, \"metadata_template\": w, \"metadata_slot\": slot, \"metadata_seed\": tw[\"seed\"],\n   160\t                   \"metadata_fork_tokens\": {a: arms[a][\"fork_token\"] for a in arms},\n   161\t                   \"metadata_n_tokens\": {a: arms[a][\"n_tokens\"] for a in arms},\n   162\t                   \"metadata_code_TWIN\": tw[\"text\"]})\n   163\t    return ex\n   164\t\n   165\t\n   166\tdef main() -> None:\n   167\t    U = read_json(RESULTS_DIR / \"units.json\")\n   168\t    T = toks()\n   169\t    datasets = []\n   170\t    for name, fn in ((\"b1_forks\", lambda: b1_examples(T, U)), (\"b2_tf\", lambda: b2_examples(T, U)),\n   171\t                     (\"b3_heldout\", b3_examples), (\"b2_generation\", gen_examples)):\n   172\t        try:\n   173\t            ex = fn()\n   174\t        except FileNotFoundError as e:\n   175\t            logger.error(f\"{name}: {e}\")\n   176\t            ex = []\n   177\t        if ex:\n   178\t            datasets.append({\"dataset\": name, \"examples\": ex})\n   179\t        logger.info(f\"{name}: {len(ex)} examples\")\n   180\t    summ = read_json(RESULTS_DIR / \"summary.json\") if (RESULTS_DIR / \"summary.json\").exists() else {}\n   181\t    timing = read_jsonl(RESULTS_DIR / \"stage_timing.jsonl\")\n   182\t    meta = {\n   183\t        \"artifact\": \"iteration-9 BASE artifact (claims B1-B3): where instruction tuning sharpened the algorithm choice\",\n   184\t        \"method_name\": \"teacher-forced base-vs-instruct fork margins (B1); cross-model activation patching at the \"\n   185\t                       \"fork with matched random nulls and residual swaps (B2); interpolated-mean held-out rerun (B3)\",\n   186\t        \"baselines\": [\"both unpatched anchors (instruct, base) on identical ids\", \"50 write-norm-matched random \"\n   187\t                      \"component sets (R, R-pure, R-scaled)\", \"exhaustive single-component sweep (36 MLPs + 1152 \"\n   188\t                      \"heads)\", \"SPEC (task-specification) set + 20 matched random SPEC sets\",\n   189\t                      \"residual-stream swaps RS-fork / RS-prefix / RS-all (upper bounds)\", \"base-entropy-matched and \"\n   190\t                      \"rate-matched random positions (Cantarero)\", \"template-free arm\"],\n   191\t        \"models\": {k: {\"id\": v[0], \"revision\": v[1]} for k, v in MODELS.items()},\n   192\t        \"b1\": summ.get(\"b1_summary\"), \"b2_verdict\": (summ.get(\"b2_summary\") or {}).get(\"verdict\"),\n   193\t        \"b2\": {u: {k: v for k, v in r.items() if k not in (\"singles\", \"per_prompt_share\")}\n   194\t               for u, r in ((summ.get(\"b2_summary\") or {}).get(\"units\") or {}).items()},\n   195\t        \"b2_v1_sensitivity\": (summ.get(\"b2_summary\") or {}).get(\"v1_variable_batch_sensitivity\"),\n   196\t        \"b3\": summ.get(\"b3_summary\"), \"commit_chain\": verify_chain(), \"deviations\": summ.get(\"deviations\"),\n   197\t        \"gpu_seconds_by_stage\": timing, \"gpu_hours_total\": round(sum(t[\"seconds\"] for t in timing) / 3600, 3),\n   198\t        \"openrouter_usd\": 0.0,\n   199\t        \"b2_generation\": read_json(RESULTS_DIR / \"b2_generation.json\")\n   200\t        if (RESULTS_DIR / \"b2_generation.json\").exists() else None,\n   201\t        \"weight_change_S7a\": read_json(RESULTS_DIR / \"weight_change.json\")\n   202\t        if (RESULTS_DIR / \"weight_change.json\").exists() else None,\n   203\t        \"rederive\": read_json(RESULTS_DIR / \"rederive.json\") if (RESULTS_DIR / \"rederive.json\").exists() else None,\n   204\t        \"positioning\": read_json(RESULTS_DIR / \"positioning.json\")\n   205\t        if (RESULTS_DIR / \"positioning.json\").exists() else None,\n   206\t        \"not_run\": [\"L-SP Llama shortest-path unit (second in the drop order)\", \"B2 T1 / T2 units (optional)\",\n   207\t                    \"S7b optional Gemma CMAP unit (S7a weight-change profile was run)\",\n   208\t                    \"token maps for unmapped base fork tokens (forced continuations); unmapped mass is reported\",\n   209\t                    \"novelty audit judges: no correct generated program is labelled 'other' (none novel; rule-of-\"\n   210\t                    \"three bound 3/237 = 0.013 on the novel-class rate among correct programs); USD 0 spent\"],\n   211\t        \"utc\": utc_now(),\n   212\t    }\n   213\t    out = {\"metadata\": meta, \"datasets\": datasets}\n   214\t    write_json(ROOT / \"method_out.json\", out)\n   215\t    logger.info(f\"method_out.json: {sum(len(d['examples']) for d in datasets)} examples\")\n   216\t\n   217\t\n   218\tif __name__ == \"__main__\":\n   219\t    setup_logging(\"outputs9\")\n   220\t    main()", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [58] TOOL CALL — Bash · 2026-10-26 14:33:19 UTC

```
Extract reference values from b2_summary.json:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50; cd /tmp && python3 -I - $A <<'EOF'
import json,sys
A=sys.argv[1]
s=json.load(open(A+'/results/b2_summary.json'))
print(list(s.keys()))
print({k:s[k] for k in ('Q1_both','Q2_both','Q3_both','verdict')})
for u,r in s['units'].items():
    print('==',u, list(r.keys()))
    print(' n_prompts', r['n_prompts'], 'gap', r['gap_mean'], r['gap_ci95'])
    print(' FSTACK', r['arms']['FSTACK']['share'], r['arms']['FSTACK']['share_ci95'])
    print(' null_R', {k:v for k,v in r['null_R'].items() if k!='shares'})
    print(' RS36', r['RS_fork'].get('36'), 'RS23', r['RS_fork'].get('23'), 'prefix23', r['RS_prefix'].get('23'))
    print(' Q', r['Q1'], r['Q2'], r['Q3'], r['localisation'])
    print(' readout', json.dumps(r['readout_decomposition_cpu'])[:800])
    print(' REV', r.get('REV'))
    print(' random_set_meta keys', list(r['random_set_meta'].keys()))
    print(' v1', s['v1_variable_batch_sensitivity'].get(u))
    print(' singles_top10', r['singles_top10'][:4])
EOF
```

### [59] TOOL RESULT — Bash · 2026-10-26 14:33:19 UTC

```
{"stdout": "['units', 'Q1_both', 'Q2_both', 'Q3_both', 'verdict', 'utc', 'v1_variable_batch_sensitivity']\n{'Q1_both': False, 'Q2_both': False, 'Q3_both': True, 'verdict': 'PARTIAL'}\n== B3 ['unit', 'n_prompts', 'm_I', 'm_B', 'gap_mean', 'gap_ci95', 'arms', 'null_R', 'null_Rpure', 'null_Rscaled', 'null_SPECR', 'RS_fork', 'RS_prefix', 'RS_all', 'singles', 'singles_top10', 'jaccard_top10_vs_FSTACK', 'fstack_single_ranks', 'sum_singles_FSTACK', 'interaction_FSTACK_minus_sum_singles', 'singles_mlp_total', 'singles_head_total', 'self_patch_max_abs_dm', 'identity_heads_minus_RS36_max_abs', 'identity_attn_minus_RS36_max_abs', 'onetok_minus_full_unpatched_mean', 'REV', 'Q1', 'Q2', 'Q3', 'localisation', 'supp_FSTACK_over_RS36', 'readout_decomposition_cpu', 'random_set_meta', 'spec_random_set_meta', 'gpu_tests']\n n_prompts 20 gap 2.059030532836914 [1.9603620386123657, 2.1635967445373536]\n FSTACK 0.997695560547463 [0.9578442708709167, 1.0404700935538165]\n null_R {'median': 0.8072684282439035, 'p95': 1.4134067761283897, 'max': 1.4644640003705334, 'empirical_p_upper': 0.45098039215686275, 'frac_below_ref': 0.56}\n RS36 0.5726278224218985 RS23 0.7793199786943331 prefix23 0.44275491535629097\n Q True False True distributed\n readout {\"base_resid|instr_norm|instr_U\": 0.13234310150146483, \"base_resid|base_norm|instr_U\": 0.12892503738403321, \"base_resid|instr_norm|base_U\": -0.7516695022583008, \"base_resid|base_norm|base_U\": -0.7476247787475586, \"instr_resid|instr_norm|instr_U\": 1.3113985061645508, \"instr_resid|base_norm|base_U\": -1.309712791442871, \"share_residual_swap_under_instr_readout\": 0.5726284949290482, \"share_readout_swap_on_base_resid\": 0.42737150507095184, \"share_unembedding_only\": 0.42571146356366135, \"share_norm_only\": -0.001964389397818218, \"note\": \"fp32 CPU recomputation from cached final-norm inputs; 'share_residual_swap_under_instr_readout' is the CPU analogue of RS-fork(36); the two parts sum to 1 by construction\"}\n REV {'share_opened_FSTACK': -0.30398508603320906, 'share_opened_F_MLP': -0.26991426784928557, 'share_opened_F_HEAD': -0.01854713878789282, 'share_opened_RS36_instr_resid_in_base': -0.2729879345082328, 'null_R_median': 0.029054977883791487, 'null_R_p95': 0.31264629582455244, 'empirical_p_upper': 0.9607843137254902, 'base_anchor_drift_max': 1.1444091796875e-05}\n random_set_meta keys ['R', 'R_n_distinct_sets', 'Rpure_n_distinct_sets', 'basis_alignment']\n v1 {'FSTACK': 1.0022815947286592, 'RSfork36': 0.5659584382172207, 'RSfork23': 0.764872195898423, 'SPEC': -0.019297771525875473, 'R_median': 0.8198217128155771, 'self_patch_max_abs_dm': 0.15336990356445312, 'note': 'v1 = variable batch shapes and full-forward caches (superseded; sensitivity only)'}\n singles_top10 [['mlp|L35', 0.9760469651003914], ['mlp|L28', 0.6235820383965169], ['mlp|L29', 0.5644437136703643], ['mlp|L26', 0.51683240314027]]\n== T10 ['unit', 'n_prompts', 'm_I', 'm_B', 'gap_mean', 'gap_ci95', 'arms', 'null_R', 'null_Rpure', 'null_Rscaled', 'null_SPECR', 'RS_fork', 'RS_prefix', 'RS_all', 'singles', 'singles_top10', 'jaccard_top10_vs_FSTACK', 'fstack_single_ranks', 'sum_singles_FSTACK', 'interaction_FSTACK_minus_sum_singles', 'singles_mlp_total', 'singles_head_total', 'self_patch_max_abs_dm', 'identity_heads_minus_RS36_max_abs', 'identity_attn_minus_RS36_max_abs', 'onetok_minus_full_unpatched_mean', 'REV', 'Q1', 'Q2', 'Q3', 'localisation', 'supp_FSTACK_over_RS36', 'readout_decomposition_cpu', 'random_set_meta', 'spec_random_set_meta', 'gpu_tests']\n n_prompts 20 gap 4.518890762329102 [3.5011833715438843, 5.574109530448913]\n FSTACK 0.4517074158612683 [0.2771083253274017, 0.565489619190677]\n null_R {'median': -0.2232473009245905, 'p95': 0.05572332595616017, 'max': 0.10670516573483321, 'empirical_p_upper': 0.0196078431372549, 'frac_below_ref': 1.0}\n RS36 0.15162315113767086 RS23 -0.04749113223947896 prefix23 0.37230087183008004\n Q False True True distributed\n readout {\"base_resid|instr_norm|instr_U\": 3.7698137283325197, \"base_resid|base_norm|instr_U\": 3.777958106994629, \"base_resid|instr_norm|base_U\": -0.07678737640380859, \"base_resid|base_norm|base_U\": -0.06391429901123047, \"instr_resid|instr_norm|instr_U\": 4.454979705810547, \"instr_resid|base_norm|base_U\": 1.9617906570434571, \"share_residual_swap_under_instr_readout\": 0.15162249363382665, \"share_readout_swap_on_base_resid\": 0.8483775063661734, \"share_unembedding_only\": 0.8501798010545238, \"share_norm_only\": -0.002848723023563336, \"note\": \"fp32 CPU recomputation from cached final-norm inputs; 'share_residual_swap_under_instr_readout' is the CPU analogue of RS-fork(36); the two parts sum to 1 by construction\"}\n REV {'share_opened_FSTACK': 0.22336060920474343, 'share_opened_F_MLP': 0.1953335138161815, 'share_opened_F_HEAD': 0.09465692261886521, 'share_opened_RS36_instr_resid_in_base': 0.4482743585788993, 'null_R_median': -0.056546403296775, 'null_R_p95': 0.08690064689341154, 'empirical_p_upper': 0.0196078431372549, 'base_anchor_drift_max': 7.62939453125e-06}\n random_set_meta keys ['R', 'R_n_distinct_sets', 'Rpure_n_distinct_sets', 'basis_alignment']\n v1 {'FSTACK': 0.4498690417406425, 'RSfork36': 0.15928068603630952, 'RSfork23': -0.04006765467149656, 'SPEC': -0.16634755066702425, 'R_median': -0.215831073414272, 'self_patch_max_abs_dm': 0.5180282592773438, 'note': 'v1 = variable batch shapes and full-forward caches (superseded; sensitivity only)'}\n singles_top10 [['mlp|L30', 0.5344874612115937], ['mlp|L35', 0.3805599459260556], ['mlp|L34', 0.2631189208915312], ['head|L23|H10', 0.20865201682829504]]", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [60] THINKING · 2026-10-26 14:33:55 UTC

```
Found the B2 reference values to replicate: MST FSTACK 0.998 (null p=0.45), CC 0.452 (p=0.020), verdict PARTIAL. Next I'll check B3/T10's unit definitions (prompts, opening, D/A token classes) so examples have readable text.
```

### [61] TOOL CALL — Bash · 2026-10-26 14:33:55 UTC

```
Inspect unit definitions for B3 and T10:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50; sed -n 1,60p $A/src/units9.py; grep -n "B3\|T10" $A/src/units9.py | head -30; cd /tmp && python3 -I - $A <<'EOF'
import json,sys
A=sys.argv[1]
U=json.load(open(A+'/results/units.json'))
print(list(U.keys()))
for u in ('B3','T10'):
    x=U[u]; print('==',u, [k for k in x.keys()])
    f=x['forks'][0]; print(' fork keys', list(f.keys()))
    print(' D_str',f.get('D_str'),'A_str',f.get('A_str'), 'opening len', len(f['opening']), 'tok_a', f.get('tok_a'), f.get('tok_b'))
    print(' n prompts', len(x['prompts']), 'prompt keys', list(x['prompts'][0].keys()))
    print(' desc', {k:v for k,v in x.items() if k not in ('prompts','forks')})
    print(' opening_text', repr(f.get('opening_text', ''))[:400])
EOF
```

### [62] TOOL RESULT — Bash · 2026-10-26 14:33:55 UTC

````
{"stdout": "#!/usr/bin/env python3\n\"\"\"S0.4: build units.json (CPU; tokenizers only).\n\nQwen B2 units (CMAP): B3 (MST; 20 = exp41 C1nat set-A clean prompts + the k=4 set-B clean prompt per template; 61-token\nopening; D = Kruskal-class tokens, A = Prim-class tokens of locate_B3 o0) and T10 (CC; 20 = exp41 C2a clean prompts\nW1-W5 x ship/man/guy + 'baby'; prefix up to ' def'; D = {' find'}, A = {' dfs', ' bfs'}).\nQwen engine-check units: the iteration-8 base_subarm twins (prompts8) at the base_subarm decision specs (B3, T10).\nGemma B1 units: G-GRID (exp31 grid fork, index 32), G-T04 (token 31), G-R6 (tokens 12 and 24).\nLlama B1 unit: L-GRID (locate_L-T1 openings o1 d=52 and o2 d=121).\nD / A at the B1 forks: the two non-UNDECIDED classes with the largest instruct mass at the fork (locate mass_T1).\nTemplate-free ids: [BOS if the family has one] + user text + blank line (+ the same opening), as base_arm 'plain'.\n\"\"\"\n\nfrom __future__ import annotations\n\nimport json\nimport sys\nfrom collections import Counter\nfrom typing import Any\n\nfrom loguru import logger\n\nfrom cfg9 import (TEMPLATES, V31, V35, V41, V43, ids_sha, model_path, read_json, read_jsonl, setup_logging,\n                  write_json, ROOT)\n\nUNITS_JSON = ROOT / \"results\" / \"units.json\"\nGEMMA_HEAD = \"<bos><start_of_turn>user\\n\"\nGEMMA_TAIL = \"<end_of_turn>\\n<start_of_turn>model\\n\"\nNOUN_SKIP = {\"house\"}\n\n\ndef _k3():\n    p = str(V41 / \"src\")\n    if p not in sys.path:\n        sys.path.insert(0, p)\n    import k3prompts as KP  # noqa: E402\n    return KP\n\n\ndef _classes_from_locate(o: dict[str, Any], key_tokens: str = \"tokens\", key_mass: str = \"mass_T1\",\n                         class_of: dict[str, str] | None = None) -> dict[str, Any]:\n    toks = [int(t) for t in o[key_tokens]]\n    mass = [float(m) for m in o[key_mass]]\n    co = class_of if class_of is not None else {str(k): v for k, v in o[\"classes\"][\"class_of\"].items()}\n    agg: Counter = Counter()\n    for t, m in zip(toks, mass):\n        c = co.get(str(t), \"UNDECIDED\")\n        if c not in (\"UNDECIDED\", \"other\", \"invalid\"):\n            agg[c] += m\n    (dcls, _), (acls, _) = agg.most_common(2)\n    D = [t for t in toks if co.get(str(t)) == dcls]\n    A = [t for t in toks if co.get(str(t)) == acls]\n    return {\"D\": D, \"A\": A, \"D_class\": dcls, \"A_class\": acls, \"class_of\": {str(t): co.get(str(t), \"UNDECIDED\")\n                                                                          for t in toks},\n            \"instr_mass_ref\": {str(t): m for t, m in zip(toks, mass)}, \"class_mass_ref\": dict(agg)}\n\n\ndef _phat_class(phat: dict[str, list[float]], bins: list[str], thr: float = 0.7) -> dict[str, str]:\n    out = {}\n    for t, v in phat.items():\n4:Qwen B2 units (CMAP): B3 (MST; 20 = exp41 C1nat set-A clean prompts + the k=4 set-B clean prompt per template; 61-token\n5:opening; D = Kruskal-class tokens, A = Prim-class tokens of locate_B3 o0) and T10 (CC; 20 = exp41 C2a clean prompts\n7:Qwen engine-check units: the iteration-8 base_subarm twins (prompts8) at the base_subarm decision specs (B3, T10).\n83:    # ---------------- B3 (MST)\n92:    loc = read_json(V43 / \"results\" / \"locate_B3.json\")\n94:    assert [int(x) for x in o0[\"O\"]] == list(O), \"locate_B3 o0 opening differs from the exp41 opening\"\n103:    out[\"B3\"] = {\"unit\": \"B3\", \"family\": \"qwen\", \"kind\": \"b2\", \"name\": \"minimum spanning tree weight\",\n104:                 \"forks\": [dict(fork_id=\"B3\", opening=list(O), tok_a=\" Kr\", tok_b=\" Prim\",\n107:    # ---------------- T10 (CC)\n119:    out[\"T10\"] = {\"unit\": \"T10\", \"family\": \"qwen\", \"kind\": \"b2\", \"name\": \"connected components\",\n120:                  \"forks\": [{\"fork_id\": \"T10\", \"opening\": list(pre), \"D\": D, \"A\": A, \"D_class\": \"union_find\",\n126:    cr = read_json(V35 / \"predictions\" / \"collapsed_raw.json\")[\"T10\"]\n129:    progs = [s[\"token_ids\"] for s in sam if s[\"unit\"] == \"T10\" and s.get(\"arm\") == \"TWIN6\"]\n132:    out[\"CHK_T10\"] = {\"unit\": \"CHK_T10\", \"family\": \"qwen\", \"kind\": \"check\",\n133:                      \"forks\": [{\"fork_id\": \"CHK_T10\", \"opening\": prefix, \"D\": Dt,\n135:                      \"prompts\": [{\"pid\": f\"T10|{w}|twin\", \"template\": w, \"ids\": P8[(\"T10\", w)][\"ids\"],\n136:                                   \"ids_plain\": _plain(tok, _user_text_qwen(tok, P8[(\"T10\", w)][\"ids\"]), False),\n137:                                   \"sha\": ids_sha(P8[(\"T10\", w)][\"ids\"])} for w in TEMPLATES]}\n138:    out[\"CHK_B3\"] = {\"unit\": \"CHK_B3\", \"family\": \"qwen\", \"kind\": \"check\",\n139:                     \"forks\": [{\"fork_id\": \"CHK_B3\", \"opening\": list(O), \"D\": cl[\"D\"], \"A\": cl[\"A\"]}],\n140:                     \"prompts\": [{\"pid\": f\"B3|{w}|twin\", \"template\": w, \"ids\": P8[(\"B3\", w)][\"ids\"],\n141:                                  \"ids_plain\": _plain(tok, _user_text_qwen(tok, P8[(\"B3\", w)][\"ids\"]), False),\n142:                                  \"sha\": ids_sha(P8[(\"B3\", w)][\"ids\"])} for w in TEMPLATES]}\n['B3', 'T10', 'CHK_T10', 'CHK_B3', 'G-GRID', 'G-T04', 'G-R6', 'L-GRID']\n== B3 ['unit', 'family', 'kind', 'name', 'forks', 'prompts']\n fork keys ['fork_id', 'opening', 'tok_a', 'tok_b', 'bins', 'phat', 'D', 'A', 'D_class', 'A_class', 'class_of', 'instr_mass_ref', 'class_mass_ref', 'D_str', 'A_str', 'opening_text']\n D_str [' Kr', ' Union', ' Check', ' Minimum', ' Find', ' Priority', ' Helper', ' Dis'] A_str [' Prim', ' Pr', ' Use', ' MST', ' To', ' Using', 'Prim', ' Prime'] opening len 61 tok_a  Kr  Prim\n n prompts 20 prompt keys ['pid', 'template', 'noun', 'ids', 'ids_plain', 'pos', 'sha', 'exp41_m_clean']\n desc {'unit': 'B3', 'family': 'qwen', 'kind': 'b2', 'name': 'minimum spanning tree weight'}\n opening_text '```python\\ndef solve(n, roads):\\n    import heapq\\n\\n    # Build adjacency list\\n    graph = [[] for _ in range(n)]\\n    for u, v, w in roads:\\n        graph[u].append((v, w))\\n        graph[v].append((u, w))\\n\\n    #'\n== T10 ['unit', 'family', 'kind', 'name', 'forks', 'prompts']\n fork keys ['fork_id', 'opening', 'D', 'A', 'D_class', 'A_class', 'tok_a', 'tok_b', 'class_of', 'D_str', 'A_str', 'opening_text']\n D_str [' find'] A_str [' dfs', ' bfs'] opening len 11 tok_a  find  dfs\n n prompts 20 prompt keys ['pid', 'template', 'noun', 'ids', 'ids_plain', 'pos', 'sha', 'exp41_m_clean']\n desc {'unit': 'T10', 'family': 'qwen', 'kind': 'b2', 'name': 'connected components'}\n opening_text '```python\\ndef solve(n, edges):\\n    def'", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd", "interrupted": false, "isImage": false, "noOutputExpected": false}
````

### [63] THINKING · 2026-10-26 14:35:29 UTC

```
Unit definitions confirmed: B3 forks on Kruskal vs Prim for MST, T10 forks on union-find vs DFS/BFS for connected components. Next I'll check the exp41 circuit lists excluded by the R-pure null, then write the data builder.
```

### [64] TOOL CALL — Bash · 2026-10-26 14:35:29 UTC

```
Inspect vendored exp41 circuits top15 lists:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50; ls $A/vendor; ls $A/vendor/art_18XvfcJJZi1O/results | head -30; cd /tmp && python3 -I - $A <<'EOF'
import json,sys
A=sys.argv[1]
s=json.load(open(A+'/vendor/art_18XvfcJJZi1O/results/summary.json'))
print(list(s.keys()))
print(list(s['circuits'].keys()))
for c,v in s['circuits'].items():
    print(c, type(v.get('top15')), json.dumps(v.get('top15'))[:300])
EOF
```

### [65] TOOL RESULT — Bash · 2026-10-26 14:35:29 UTC

```
{"stdout": "art_18XvfcJJZi1O\nart_FJMIE9T9_PMv\nart_MZAfDPVhM6Ui\nart_j3Rm_lr2nzR6\nart_lzuosbrb34wB\nart_zNyBP6zieI5u\nexp38\ninputs.json\ncircuit_C1forced.json\ncircuit_C1mix.json\ncircuit_C1nat.json\ncircuit_C1natB.json\ncircuit_C2a.json\ncontrasts.json\nnouns.json\nselection_C1forced.json\nselection_C1nat.json\nselection_C2a.json\nsummary.json\n['utc', 'contrasts', 'circuits', 'validation', 'validation_sensitivity', 'generation', 'U7_crn_determinism', 'dose_sensitivity', 'motif', 'cross_contrast_overlap', 'stability', 'gemma_recount', 'K3', 'engine_check', 'gpu_tests', 'tests_cpu', 'deviations', 'memory_probe', 'labeller_check', 'novelty_audit', 'positioning', 'transcoder_precheck', 'rederive', 'commit_chain', 'stage_timing', 'gpu_seconds_total', 'openrouter_usd', 'F9_other_flags', 'n_rows_jsonl', 'figures']\n['C1nat', 'C1forced', 'C1mix', 'C1natB', 'C2a']\nC1nat <class 'list'> [\"mlp|L0|H-1|COND\", \"mlp|L27|H-1|DEC\", \"mlp|L20|H-1|SPEC\", \"mlp|L12|H-1|SPEC\", \"mlp|L30|H-1|DEC\", \"mlp|L8|H-1|SPEC\", \"mlp|L19|H-1|SPEC\", \"mlp|L5|H-1|COND\", \"head|L34|H28|DEC\", \"mlp|L16|H-1|SPEC\", \"mlp|L9|H-1|SPEC\", \"mlp|L28|H-1|DEC\", \"mlp|L35|H-1|DEC\", \"mlp|L1|H-1|COND\", \"mlp|L34|H-1|DEC\"]\nC1forced <class 'list'> [\"mlp|L0|H-1|COND\", \"head|L33|H14|DEC\", \"mlp|L35|H-1|DEC\", \"head|L34|H28|DEC\", \"mlp|L27|H-1|DEC\", \"head|L29|H6|DEC\", \"mlp|L30|H-1|DEC\", \"head|L23|H10|OPEN\", \"mlp|L28|H-1|DEC\", \"mlp|L11|H-1|SPEC\", \"head|L27|H31|DEC\", \"mlp|L10|H-1|SPEC\", \"head|L23|H10|SPEC\", \"mlp|L34|H-1|DEC\", \"mlp|L26|H-1|DEC\"]\nC1mix <class 'list'> [\"mlp|L35|H-1|DEC\", \"head|L34|H28|DEC\", \"mlp|L27|H-1|DEC\", \"head|L33|H14|DEC\", \"mlp|L30|H-1|DEC\", \"mlp|L28|H-1|DEC\", \"head|L29|H6|DEC\", \"mlp|L10|H-1|SPEC\", \"mlp|L16|H-1|SPEC\", \"head|L23|H10|OPEN\", \"head|L27|H31|DEC\", \"mlp|L33|H-1|DEC\", \"head|L23|H10|SPEC\", \"mlp|L19|H-1|SPEC\", \"mlp|L26|H-1|DEC\"]\nC1natB <class 'list'> [\"mlp|L0|H-1|COND\", \"mlp|L4|H-1|COND\", \"mlp|L12|H-1|SPEC\", \"mlp|L14|H-1|SPEC\", \"mlp|L19|H-1|SPEC\", \"mlp|L33|H-1|DEC\", \"mlp|L17|H-1|SPEC\", \"mlp|L34|H-1|DEC\", \"mlp|L13|H-1|OPEN\", \"head|L34|H28|DEC\", \"mlp|L16|H-1|SPEC\", \"mlp|L9|H-1|COND\", \"mlp|L10|H-1|SPEC\", \"mlp|L5|H-1|COND\", \"mlp|L1|H-1|COND\"]\nC2a <class 'list'> [\"mlp|L27|H-1|DEC\", \"mlp|L26|H-1|DEC\", \"mlp|L32|H-1|DEC\", \"mlp|L30|H-1|DEC\", \"head|L23|H10|DEC\", \"head|L27|H31|DEC\", \"mlp|L28|H-1|DEC\", \"mlp|L31|H-1|DEC\", \"mlp|L13|H-1|SPEC\", \"head|L11|H13|SPEC\", \"mlp|L9|H-1|SPEC\", \"head|L23|H11|DEC\", \"head|L11|H14|SPEC\", \"head|L14|H5|SPEC\", \"head|L26|H20|DEC\"]", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [66] THINKING · 2026-10-26 14:36:21 UTC

```
I have everything needed to build the demo data. I'll write a reproducible builder script that takes the artifact folder as an argument (avoiding hardcoded server paths), then run it using the scratch venv for torch support.
```

### [67] TOOL CALL — Write · 2026-10-26 14:36:21 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd/build_mini_demo_data.py

#!/usr/bin/env python3
"""Build mini_demo_data.json for code_demo.ipynb from the iteration-9 artifact folder (experiment 50).

The demo uses ONE dataset of the artifact, b2_tf: the 40 teacher-forced Qwen3-8B prompts (units B3 = MST and
T10 = connected components, 20 prompts each) on which cross-model activation patching (CMAP) was run. Each example
keeps every patching arm's fork margin (1429 arms), the reverse-patch (REV) margins (55 arms), the instruct / base
anchors, and the block-30 output at the fork for the four states F8 plots (bf16 bits, base64). The per-row top-256
distributions (`dist`) are dropped. Small run-level inputs that the analysis reads (random-set draws and their delta
norms, SPEC random sets, GPU tests, exp41 top-15 lists) and the original summary values (for comparison) go into
`metadata`.

Usage (needs numpy and torch; torch only to read cache/geom_*.pt):
    python build_mini_demo_data.py --artifact-dir <path to the experiment-50 artifact folder> --out mini_demo_data.json
"""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

import numpy as np
import torch

UNITS = ("B3", "T10")
GEOM_STATES = ("none", "FSTACK", "RSfork23")      # + the median random set R{med}, as in figures9.f8_geometry


def jl(p: Path) -> list[dict]:
    with open(p) as fh:
        return [json.loads(x) for x in fh if x.strip()]


def bf16_b64(t: torch.Tensor) -> str:
    """Exact bf16 bits of a 4096-d vector, little-endian uint16, base64."""
    assert t.dtype == torch.bfloat16
    return base64.b64encode(t.contiguous().view(torch.int16).numpy().astype("<i2").tobytes()).decode("ascii")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact-dir", required=True, type=Path)
    ap.add_argument("--out", default=Path(__file__).resolve().parent / "mini_demo_data.json", type=Path)
    args = ap.parse_args()
    A = args.artifact_dir
    R = A / "results"

    units = json.loads((R / "units.json").read_text())
    b2s = json.loads((R / "b2_summary.json").read_text())
    rsets = json.loads((R / "random_sets.json").read_text())
    gpu_tests = json.loads((R / "gpu_tests_b2.json").read_text())
    exp41 = json.loads((A / "vendor" / "art_18XvfcJJZi1O" / "results" / "summary.json").read_text())
    full = json.loads((A / "full_method_out.json").read_text())
    ex_txt = {}
    for ds in full["datasets"]:
        if ds["dataset"] == "b2_tf":
            for e in ds["examples"]:
                ex_txt[(e["metadata_unit"], e["metadata_prompt_id"])] = e

    meta_units, examples, med_idx, reference = {}, [], {}, {}
    spec_sets, carried = {}, {}
    for u in UNITS:
        U = units[u]
        f = U["forks"][0]
        meta_units[u] = {"name": U["name"], "D_class": f["D_class"], "A_class": f["A_class"], "D_tokens": f["D_str"],
                         "A_tokens": f["A_str"], "D_ids": f["D"], "A_ids": f["A"], "tok_a": f["tok_a"],
                         "tok_b": f["tok_b"], "opening_text": f["opening_text"], "n_opening_tokens": len(f["opening"])}
        S = b2s["units"][u]
        rsh = S["null_R"]["shares"]
        med = int(np.argsort(rsh)[len(rsh) // 2])
        med_idx[u] = med
        # per-prompt margins of every arm, in the original row order (bootstrap resampling depends on the pid order)
        rows = jl(R / f"b2_tf_{u}.jsonl")
        by: dict[str, dict] = {}
        for r in rows:
            e = by.setdefault(r["pid"], {"template": r["template"], "m_I": r["m_I"], "m_B": r["m_B"], "arms": {}})
            e["arms"][r["arm"]] = r["m"]
        rev: dict[str, dict] = {}
        for r in jl(R / f"b2_rev_{u}.jsonl"):
            rev.setdefault(r["pid"], {})[r["arm"]] = r["m"]
        # fork states (block-30 output = input of layer 31) saved by cmap9.stage_patch, file index = prompt index
        geom = {}
        for pi, p in enumerate(U["prompts"]):
            gp = A / "cache" / f"geom_{u}_{pi:02d}.pt"
            if gp.exists():
                g = torch.load(gp)
                geom[p["pid"]] = {k: bf16_b64(g[k]) for k in GEOM_STATES + (f"R{med}",)}
        for pid, e in by.items():
            t = ex_txt[(u, pid)]
            examples.append({
                "unit": u, "pid": pid, "template": e["template"],
                "input": t["input"], "output": t["output"],
                "predict_base_model": t["predict_base_model"], "predict_FSTACK_patched": t["predict_FSTACK_patched"],
                "predict_median_random_set_patched": t["predict_median_random_set_patched"],
                "predict_RSfork36_patched": t["predict_RSfork36_patched"],
                "m_I": e["m_I"], "m_B": e["m_B"], "arms": e["arms"], "rev_arms": rev[pid],
                "geom_bf16_b64": geom.get(pid)})
        sp = json.loads((R / f"spec_random_sets_{u}.json").read_text())
        spec_sets[u] = {k: sp[k] for k in ("sets", "meta", "n_distinct_sets", "seed", "norms_spec")}
        carried[u] = {"readout_decomposition_cpu": S["readout_decomposition_cpu"]}
        reference[u] = {
            "n_prompts": S["n_prompts"], "gap_mean": S["gap_mean"], "gap_ci95": S["gap_ci95"],
            "FSTACK_share": S["arms"]["FSTACK"]["share"], "FSTACK_share_ci95": S["arms"]["FSTACK"]["share_ci95"],
            "F_MLP_share": S["arms"]["F_MLP"]["share"], "F_HEAD_share": S["arms"]["F_HEAD"]["share"],
            "SPEC_share": S["arms"]["SPEC"]["share"],
            "null_R": {k: v for k, v in S["null_R"].items() if k != "shares"},
            "null_Rpure": {k: v for k, v in S["null_Rpure"].items() if k != "shares"},
            "RS_fork_23": S["RS_fork"]["23"], "RS_fork_36": S["RS_fork"]["36"], "RS_prefix_23": S["RS_prefix"]["23"],
            "RS_all_23": S["RS_all"]["23"], "sum_singles_FSTACK": S["sum_singles_FSTACK"],
            "singles_top10": S["singles_top10"], "REV": S["REV"], "Q1": S["Q1"], "Q2": S["Q2"], "Q3": S["Q3"],
            "localisation": S["localisation"]}
    reference["verdict"] = b2s["verdict"]
    reference.update({k: b2s[k] for k in ("Q1_both", "Q2_both", "Q3_both")})

    out = {
        "metadata": {
            "title": "How tuning sharpens a code model's algorithm choice: B2 cross-model activation patching rows",
            "source": "iteration-9 artifact art_cDba8_DycUJd (experiment 50), dataset b2_tf",
            "source_files": ["results/b2_tf_B3.jsonl", "results/b2_tf_T10.jsonl", "results/b2_rev_B3.jsonl",
                             "results/b2_rev_T10.jsonl", "results/random_sets.json", "results/spec_random_sets_*.json",
                             "results/gpu_tests_b2.json", "results/units.json", "results/b2_summary.json",
                             "cache/geom_*.pt", "vendor/art_18XvfcJJZi1O/results/summary.json (circuits top15)"],
            "models": {"qwen": ["Qwen/Qwen3-8B", "b968826d9c46dd6066d109eabc6255188de91218"],
                       "qwen_base": ["Qwen/Qwen3-8B-Base", "49e3418fbbbca6ecbdf9608b4d22e5a407081db4"]},
            "n_examples": len(examples),
            "units": meta_units,
            "random_sets": {u: {k: rsets[u][k] for k in ("R", "Rpure", "norms_fork", "basis_alignment")}
                            for u in UNITS},
            "spec_random_sets": spec_sets,
            "gpu_tests_b2": gpu_tests,
            "exp41_circuits_top15": {c: {"top15": v["top15"]} for c, v in exp41["circuits"].items()},
            "carried": carried,
            "geometry": {"layer_input": 31, "dim": 4096, "states": list(GEOM_STATES) + ["R{median}"],
                         "median_R_index": med_idx,
                         "encoding": "bf16 bit patterns as little-endian int16, base64; decode with "
                                     "(np.frombuffer(b64decode(s), '<i2').astype(np.int32) << 16).view(np.float32)",
                         "note": "base-model fork states (cache/base_*.pt) were not kept by the original run"},
            "reference_original_run": reference,
        },
        "examples": examples,
    }
    args.out.write_text(json.dumps(out, indent=1))
    print(f"wrote {args.out.name}: {len(examples)} examples, {args.out.stat().st_size / 1e6:.2f} MB; "
          f"median R index {med_idx}")


if __name__ == "__main__":
    main()
```

### [68] TOOL RESULT — Write · 2026-10-26 14:36:21 UTC

```
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd/build_mini_demo_data.py", "content": "#!/usr/bin/env python3\n\"\"\"Build mini_demo_data.json for code_demo.ipynb from the iteration-9 artifact folder (experiment 50).\n\nThe demo uses ONE dataset of the artifact, b2_tf: the 40 teacher-forced Qwen3-8B prompts (units B3 = MST and\nT10 = connected components, 20 prompts each) on which cross-model activation patching (CMAP) was run. Each example\nkeeps every patching arm's fork margin (1429 arms), the reverse-patch (REV) margins (55 arms), the instruct / base\nanchors, and the block-30 output at the fork for the four states F8 plots (bf16 bits, base64). The per-row top-256\ndistributions (`dist`) are dropped. Small run-level inputs that the analysis reads (random-set draws and their delta\nnorms, SPEC random sets, GPU tests, exp41 top-15 lists) and the original summary values (for comparison) go into\n`metadata`.\n\nUsage (needs numpy and torch; torch only to read cache/geom_*.pt):\n    python build_mini_demo_data.py --artifact-dir <path to the experiment-50 artifact folder> --out mini_demo_data.json\n\"\"\"\n\nfrom __future__ import annotations\n\nimport argparse\nimport base64\nimport json\nfrom pathlib import Path\n\nimport numpy as np\nimport torch\n\nUNITS = (\"B3\", \"T10\")\nGEOM_STATES = (\"none\", \"FSTACK\", \"RSfork23\")      # + the median random set R{med}, as in figures9.f8_geometry\n\n\ndef jl(p: Path) -> list[dict]:\n    with open(p) as fh:\n        return [json.loads(x) for x in fh if x.strip()]\n\n\ndef bf16_b64(t: torch.Tensor) -> str:\n    \"\"\"Exact bf16 bits of a 4096-d vector, little-endian uint16, base64.\"\"\"\n    assert t.dtype == torch.bfloat16\n    return base64.b64encode(t.contiguous().view(torch.int16).numpy().astype(\"<i2\").tobytes()).decode(\"ascii\")\n\n\ndef main() -> None:\n    ap = argparse.ArgumentParser()\n    ap.add_argument(\"--artifact-dir\", required=True, type=Path)\n    ap.add_argument(\"--out\", default=Path(__file__).resolve().parent / \"mini_demo_data.json\", type=Path)\n    args = ap.parse_args()\n    A = args.artifact_dir\n    R = A / \"results\"\n\n    units = json.loads((R / \"units.json\").read_text())\n    b2s = json.loads((R / \"b2_summary.json\").read_text())\n    rsets = json.loads((R / \"random_sets.json\").read_text())\n    gpu_tests = json.loads((R / \"gpu_tests_b2.json\").read_text())\n    exp41 = json.loads((A / \"vendor\" / \"art_18XvfcJJZi1O\" / \"results\" / \"summary.json\").read_text())\n    full = json.loads((A / \"full_method_out.json\").read_text())\n    ex_txt = {}\n    for ds in full[\"datasets\"]:\n        if ds[\"dataset\"] == \"b2_tf\":\n            for e in ds[\"examples\"]:\n                ex_txt[(e[\"metadata_unit\"], e[\"metadata_prompt_id\"])] = e\n\n    meta_units, examples, med_idx, reference = {}, [], {}, {}\n    spec_sets, carried = {}, {}\n    for u in UNITS:\n        U = units[u]\n        f = U[\"forks\"][0]\n        meta_units[u] = {\"name\": U[\"name\"], \"D_class\": f[\"D_class\"], \"A_class\": f[\"A_class\"], \"D_tokens\": f[\"D_str\"],\n                         \"A_tokens\": f[\"A_str\"], \"D_ids\": f[\"D\"], \"A_ids\": f[\"A\"], \"tok_a\": f[\"tok_a\"],\n                         \"tok_b\": f[\"tok_b\"], \"opening_text\": f[\"opening_text\"], \"n_opening_tokens\": len(f[\"opening\"])}\n        S = b2s[\"units\"][u]\n        rsh = S[\"null_R\"][\"shares\"]\n        med = int(np.argsort(rsh)[len(rsh) // 2])\n        med_idx[u] = med\n        # per-prompt margins of every arm, in the original row order (bootstrap resampling depends on the pid order)\n        rows = jl(R / f\"b2_tf_{u}.jsonl\")\n        by: dict[str, dict] = {}\n        for r in rows:\n            e = by.setdefault(r[\"pid\"], {\"template\": r[\"template\"], \"m_I\": r[\"m_I\"], \"m_B\": r[\"m_B\"], \"arms\": {}})\n            e[\"arms\"][r[\"arm\"]] = r[\"m\"]\n        rev: dict[str, dict] = {}\n        for r in jl(R / f\"b2_rev_{u}.jsonl\"):\n            rev.setdefault(r[\"pid\"], {})[r[\"arm\"]] = r[\"m\"]\n        # fork states (block-30 output = input of layer 31) saved by cmap9.stage_patch, file index = prompt index\n        geom = {}\n        for pi, p in enumerate(U[\"prompts\"]):\n            gp = A / \"cache\" / f\"geom_{u}_{pi:02d}.pt\"\n            if gp.exists():\n                g = torch.load(gp)\n                geom[p[\"pid\"]] = {k: bf16_b64(g[k]) for k in GEOM_STATES + (f\"R{med}\",)}\n        for pid, e in by.items():\n            t = ex_txt[(u, pid)]\n            examples.append({\n                \"unit\": u, \"pid\": pid, \"template\": e[\"template\"],\n                \"input\": t[\"input\"], \"output\": t[\"output\"],\n                \"predict_base_model\": t[\"predict_base_model\"], \"predict_FSTACK_patched\": t[\"predict_FSTACK_patched\"],\n                \"predict_median_random_set_patched\": t[\"predict_median_random_set_patched\"],\n                \"predict_RSfork36_patched\": t[\"predict_RSfork36_patched\"],\n                \"m_I\": e[\"m_I\"], \"m_B\": e[\"m_B\"], \"arms\": e[\"arms\"], \"rev_arms\": rev[pid],\n                \"geom_bf16_b64\": geom.get(pid)})\n        sp = json.loads((R / f\"spec_random_sets_{u}.json\").read_text())\n        spec_sets[u] = {k: sp[k] for k in (\"sets\", \"meta\", \"n_distinct_sets\", \"seed\", \"norms_spec\")}\n        carried[u] = {\"readout_decomposition_cpu\": S[\"readout_decomposition_cpu\"]}\n        reference[u] = {\n            \"n_prompts\": S[\"n_prompts\"], \"gap_mean\": S[\"gap_mean\"], \"gap_ci95\": S[\"gap_ci95\"],\n            \"FSTACK_share\": S[\"arms\"][\"FSTACK\"][\"share\"], \"FSTACK_share_ci95\": S[\"arms\"][\"FSTACK\"][\"share_ci95\"],\n            \"F_MLP_share\": S[\"arms\"][\"F_MLP\"][\"share\"], \"F_HEAD_share\": S[\"arms\"][\"F_HEAD\"][\"share\"],\n            \"SPEC_share\": S[\"arms\"][\"SPEC\"][\"share\"],\n            \"null_R\": {k: v for k, v in S[\"null_R\"].items() if k != \"shares\"},\n            \"null_Rpure\": {k: v for k, v in S[\"null_Rpure\"].items() if k != \"shares\"},\n            \"RS_fork_23\": S[\"RS_fork\"][\"23\"], \"RS_fork_36\": S[\"RS_fork\"][\"36\"], \"RS_prefix_23\": S[\"RS_prefix\"][\"23\"],\n            \"RS_all_23\": S[\"RS_all\"][\"23\"], \"sum_singles_FSTACK\": S[\"sum_singles_FSTACK\"],\n            \"singles_top10\": S[\"singles_top10\"], \"REV\": S[\"REV\"], \"Q1\": S[\"Q1\"], \"Q2\": S[\"Q2\"], \"Q3\": S[\"Q3\"],\n            \"localisation\": S[\"localisation\"]}\n    reference[\"verdict\"] = b2s[\"verdict\"]\n    reference.update({k: b2s[k] for k in (\"Q1_both\", \"Q2_both\", \"Q3_both\")})\n\n    out = {\n        \"metadata\": {\n            \"title\": \"How tuning sharpens a code model's algorithm choice: B2 cross-model activation patching rows\",\n            \"source\": \"iteration-9 artifact art_cDba8_DycUJd (experiment 50), dataset b2_tf\",\n            \"source_files\": [\"results/b2_tf_B3.jsonl\", \"results/b2_tf_T10.jsonl\", \"results/b2_rev_B3.jsonl\",\n                             \"results/b2_rev_T10.jsonl\", \"results/random_sets.json\", \"results/spec_random_sets_*.json\",\n                             \"results/gpu_tests_b2.json\", \"results/units.json\", \"results/b2_summary.json\",\n                             \"cache/geom_*.pt\", \"vendor/art_18XvfcJJZi1O/results/summary.json (circuits top15)\"],\n            \"models\": {\"qwen\": [\"Qwen/Qwen3-8B\", \"b968826d9c46dd6066d109eabc6255188de91218\"],\n                       \"qwen_base\": [\"Qwen/Qwen3-8B-Base\", \"49e3418fbbbca6ecbdf9608b4d22e5a407081db4\"]},\n            \"n_examples\": len(examples),\n            \"units\": meta_units,\n            \"random_sets\": {u: {k: rsets[u][k] for k in (\"R\", \"Rpure\", \"norms_fork\", \"basis_alignment\")}\n                            for u in UNITS},\n            \"spec_random_sets\": spec_sets,\n            \"gpu_tests_b2\": gpu_tests,\n            \"exp41_circuits_top15\": {c: {\"top15\": v[\"top15\"]} for c, v in exp41[\"circuits\"].items()},\n            \"carried\": carried,\n            \"geometry\": {\"layer_input\": 31, \"dim\": 4096, \"states\": list(GEOM_STATES) + [\"R{median}\"],\n                         \"median_R_index\": med_idx,\n                         \"encoding\": \"bf16 bit patterns as little-endian int16, base64; decode with \"\n                                     \"(np.frombuffer(b64decode(s), '<i2').astype(np.int32) << 16).view(np.float32)\",\n                         \"note\": \"base-model fork states (cache/base_*.pt) were not kept by the original run\"},\n            \"reference_original_run\": reference,\n        },\n        \"examples\": examples,\n    }\n    args.out.write_text(json.dumps(out, indent=1))\n    print(f\"wrote {args.out.name}: {len(examples)} examples, {args.out.stat().st_size / 1e6:.2f} MB; \"\n          f\"median R index {med_idx}\")\n\n\nif __name__ == \"__main__\":\n    main()\n", "structuredPatch": [], "originalFile": null, "userModified": false}
```

### [69] TOOL CALL — Bash · 2026-10-26 14:36:21 UTC

```
Build mini_demo_data.json from the artifact:
SP="/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad"; W=/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd; cd /tmp && time "$SP/venv/bin/python" -I "$W/build_mini_demo_data.py" --artifact-dir /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50 --out "$W/mini_demo_data.json" && ls -la "$W/mini_demo_data.json" && head -c 1500 "$W/mini_demo_data.json"
```

### [70] TOOL RESULT — Bash · 2026-10-26 14:36:23 UTC

```
{"stdout": "wrote mini_demo_data.json: 40 examples, 4.27 MB; median R index {'B3': 20, 'T10': 13}\n\nreal\t0m2.102s\nuser\t0m1.413s\nsys\t0m0.202s\n-rw-rw-rw- 1 aii-agent aii-agent 4273245 Oct 26 14:36 /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd/mini_demo_data.json\n{\n \"metadata\": {\n  \"title\": \"How tuning sharpens a code model's algorithm choice: B2 cross-model activation patching rows\",\n  \"source\": \"iteration-9 artifact art_cDba8_DycUJd (experiment 50), dataset b2_tf\",\n  \"source_files\": [\n   \"results/b2_tf_B3.jsonl\",\n   \"results/b2_tf_T10.jsonl\",\n   \"results/b2_rev_B3.jsonl\",\n   \"results/b2_rev_T10.jsonl\",\n   \"results/random_sets.json\",\n   \"results/spec_random_sets_*.json\",\n   \"results/gpu_tests_b2.json\",\n   \"results/units.json\",\n   \"results/b2_summary.json\",\n   \"cache/geom_*.pt\",\n   \"vendor/art_18XvfcJJZi1O/results/summary.json (circuits top15)\"\n  ],\n  \"models\": {\n   \"qwen\": [\n    \"Qwen/Qwen3-8B\",\n    \"b968826d9c46dd6066d109eabc6255188de91218\"\n   ],\n   \"qwen_base\": [\n    \"Qwen/Qwen3-8B-Base\",\n    \"49e3418fbbbca6ecbdf9608b4d22e5a407081db4\"\n   ]\n  },\n  \"n_examples\": 40,\n  \"units\": {\n   \"B3\": {\n    \"name\": \"minimum spanning tree weight\",\n    \"D_class\": \"kruskal\",\n    \"A_class\": \"prim_heap\",\n    \"D_tokens\": [\n     \" Kr\",\n     \" Union\",\n     \" Check\",\n     \" Minimum\",\n     \" Find\",\n     \" Priority\",\n     \" Helper\",\n     \" Dis\"\n    ],\n    \"A_tokens\": [\n     \" Prim\",\n     \" Pr\",\n     \" Use\",\n     \" MST\",\n     \" To\",\n     \" Using\",\n     \"Prim\",\n     \" Prime\"\n    ],\n    \"D_ids\": [\n     16447,\n     9145,\n     4248,\n     30925,\n     7379,\n     31920,\n     12906,\n     4093\n    ],\n    \"A_ids\": [\n     35183,\n     2340,\n     5443,\n     84280,\n     2014,\n     12091,\n     66191,\n     12518\n    ],\n    \"tok_a\": \" Kr\",\n    \"tok_b\": \" Prim\",\n    \"opening_t", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [71] THINKING · 2026-10-26 14:36:49 UTC

```
The data file is 4.27 MB with 40 examples (20 prompts × 2 units), with median random sets R20 (B3) and R13 (T10). Next I'll verify the original shares reproduce and the fork-state vectors decode, then add matplotlib and loguru to the scratch venv for prototyping.
```

### [72] TOOL CALL — Bash · 2026-10-26 14:36:49 UTC

```
Sanity-check demo data and install plotting deps:
SP="/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad"; W=/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd; (UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python "$SP/venv/bin/python" matplotlib==3.10.0 loguru==0.7.3 2>&1 | tail -2) ; cd /tmp && "$SP/venv/bin/python" -I - "$W/mini_demo_data.json" <<'EOF'
import json,sys,base64
import numpy as np
d=json.load(open(sys.argv[1]))
ex=d['examples']
print(len(ex), sum(e['geom_bf16_b64'] is not None for e in ex), 'with geom')
for u in ('B3','T10'):
    E=[e for e in ex if e['unit']==u]
    num=sum(e['m_I']-e['arms']['FSTACK'] for e in E); den=sum(e['m_I']-e['m_B'] for e in E)
    print(u, len(E), 'FSTACK share', num/den, 'ref', d['metadata']['reference_original_run'][u]['FSTACK_share'], 'n arms', len(E[0]['arms']), 'rev', len(E[0]['rev_arms']))
g=ex[0]['geom_bf16_b64']
v=(np.frombuffer(base64.b64decode(g['none']),'<i2').astype(np.int32) << 16).view(np.float32)
import torch
t=torch.load('/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50/cache/geom_B3_00.pt')['none'].float().numpy()
print('decode exact:', np.array_equal(v,t), v[:5], t[:5], np.linalg.norm(v))
print(ex[0]['pid'], ex[0]['output'], ex[0]['predict_base_model'], ex[0]['predict_FSTACK_patched'])
print(repr(ex[0]['input'][:600]))
print(repr(ex[0]['input'][-400:]))
EOF
```

### [73] TOOL RESULT — Bash · 2026-10-26 14:36:51 UTC

````
{"stdout": "40 40 with geom\nB3 20 FSTACK share 0.997695560547463 ref 0.997695560547463 n arms 1429 rev 55\nT10 20 FSTACK share 0.4517074158612683 ref 0.4517074158612683 n arms 1429 rev 55\ndecode exact: True [ 15.125     -8.1875   -16.875     11.6875     1.609375] [ 15.125     -8.1875   -16.875     11.6875     1.609375] 644.11523\nW1|guy  Kr  Prim  Prim\n'<|im_start|>user\\nDo not use guy for this task. . . . .\\n\\nTask: write a Python function solve(n, roads) that returns the smallest total cost of a choice of roads that links all cities. There are n cities numbered 0 to n - 1, where 1 <= n <= 500. The argument roads is a list of at most 10000 triples [u, v, w], each meaning that a two-way road between cities u and v (u != v) can be built for cost w, where 0 <= w <= 100000; several roads may join the same two cities. Choose roads so that every city can reach every other city through chosen roads, at the smallest possible total cost, and return that'\n'andard library. Return only one ```python code block containing the function solve and any helpers, with no example usage and no explanation.<|im_end|>\\n<|im_start|>assistant\\n<think>\\n\\n</think>\\n\\n```python\\ndef solve(n, roads):\\n    import heapq\\n\\n    # Build adjacency list\\n    graph = [[] for _ in range(n)]\\n    for u, v, w in roads:\\n        graph[u].append((v, w))\\n        graph[v].append((u, w))\\n\\n    #'", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd", "interrupted": false, "isImage": false, "noOutputExpected": false}
````

### [74] THINKING · 2026-10-26 14:39:19 UTC

```
Demo data checks out: FSTACK shares match the original, all 40 examples have fork states, and bf16 decode is bit-exact, completing TODOs 1-3. Now I'll write a generator script in the scratchpad to build the notebook cells so I can test the code as a plain script before running nbconvert.
```

### [75] TOOL CALL — Bash · 2026-10-26 14:39:19 UTC

```
Mark TODOs 1-3 done; list recorded deviations:
SP="/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad"; sed -i 's/^- \[ \] TODO 1\./- [x] TODO 1./; s/^- \[ \] TODO 2\./- [x] TODO 2./; s/^- \[ \] TODO 3\./- [x] TODO 3./' "$SP/todos.md"; grep -c "\[x\]" "$SP/todos.md"; A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50; cat $A/results/deviations.json | python3 -c "import json,sys; [print(d['id'], d['severity'], d['text'][:200]) for d in json.load(sys.stdin)]"
```

### [76] TOOL RESULT — Bash · 2026-10-26 14:39:19 UTC

```
{"stdout": "3\nb3_repro_tolerance minor 6.1 reproduction |diff| 0.09614 > 1e-3 (> 0.05)\nb3_repro_code_changed major 6.1 debug: the vendored exp41 src/k3circuit.py and src/k3engine.py were last modified at 03:42:39Z, after data/validation_rows_C1forced.jsonl was written (02:38:29Z), so the 'unchanged vendored path' \nengine_check_base_subarm_gpu minor G1 engine check vs iteration-8 base_subarm margins misses 0.05 on some templates (instruct: exact 0.25/0.5-nat bf16 logit steps on 2-4 of 5 templates; base: up to 0.17 nats). base_subarm was computed \nb2_confirmation_rs36 major Confirmation signal 'RS-fork(36) closes about 1.0 of the gap' failed on the first prompts (B3 0.44-0.58, T10 -0.42 to 0.50). The identity check passes (all components patched = RS-fork(36) within 0.06\nb2_v2_fixed_shapes major First B2 pass (v1, archived in results/v1_variable_batch/) used variable last-chunk batch shapes and full-forward caches: self-patch |dm| up to 0.22 and batched-vs-single dm differences up to 0.21 nat\nb3_separate_load minor S6 (B3) runs in its own instruct load (b3_9.py gpu) rather than inside S3's load.\nanalysis_sha_commit0b minor analysis9.py was written after COMMIT #0; its sha256 is committed in commit0b before any verdict is computed. Verdict rules and thresholds are in COMMIT #0.\nfpd_fork_only minor FPD is applied at the counterfactual fork token only (base logits at that one position), not at every entropy-gated position as in Cantarero et al. (plan departure f).\ngen_fork_kv minor In generation, FSTACK / RAND patches act on the fork position's forward pass, so the K/V cached at that position carry the patch; every later position is computed by the unpatched instruct model. FPD \ngen_prompts_slots minor Generation uses, per template, the first B2 prompt of that template (cached base values exist only for the B2 prompts) x 6 CRN slots (seeds 9101-9130), 30 programs per arm and unit.\nrandom_set_repeat minor When a type's candidate pool is exhausted (MLP pools hold 3-5 components), the no-repeat rule falls back to the full pool, so a few random sets contain a repeated MLP (e.g. T10 set 13 has MLP L31 twic\nself_patch_g2 minor G2 (self-patch |dm| <= 0.02) still fails in v2 (max 0.11 MST, 0.15 CC; mean share 0.003 / 0.001): head writes are cached in bf16, so setting a head's write to its own cached value re-rounds it; MLP an\ngemma_t04_r6_prompts minor G-T04 and G-R6 have 5 prompts each (prompts8 holds only the W1-W5 twins, no noun variants), so their CIs are crude (plan departure b).\nllama_onpolicy major L-GRID: every prompt fails the committed on-policy rule (instruct log P(opening) about -13.6 < -5 over the 52-token opening), so Llama is reported descriptively and excluded from the B1 verdict; L-SP \ntoken_maps_unmapped minor Token maps for unmapped base fork tokens (forced instruct continuations) were not built; the unmapped base mass is reported (G-GRID 0.66, G-T04 0.16, G-R6 0.31/0.34).", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [77] ASSISTANT · 2026-10-26 14:43:15 UTC

```
Now I'll write the notebook generator with every cell's source.
```

### [78] TOOL CALL — Write · 2026-10-26 14:43:15 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [79] TOOL RESULT — Write · 2026-10-26 14:43:15 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [80] ASSISTANT · 2026-10-26 14:43:45 UTC

```
I'll swap the awkward staticmethod class for a `SimpleNamespace`, which stands in for `import stats9 as S` more cleanly. Then I'll generate and run the prototype script.
```

### [81] TOOL CALL — Edit · 2026-10-26 14:43:45 UTC

```
File: /tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/make_nb.py
OLD: class _Stats:                     # notebook only: analysis9.py calls these functions as `S.<name>` (import stats9 as S)
    share, share_mean_of_ratios, boot_share_ci, boot_mean_ci = (staticmethod(share), staticmethod(share_mean_of_ratios),
                                                                 staticmethod(boot_share_ci), staticmethod(boot_mean_ci))
    empirical_p_upper = staticmethod(empirical_p_upper)


S = _Stats
NEW: # notebook only: analysis9.py does `import stats9 as S` and calls S.share(...), S.boot_share_ci(...), ...
S = SimpleNamespace(js_div=js_div, share=share, share_mean_of_ratios=share_mean_of_ratios, boot_ci=boot_ci,
                    boot_share_ci=boot_share_ci, boot_mean_ci=boot_mean_ci, mcnemar_exact=mcnemar_exact,
                    sign_flip_p=sign_flip_p, holm=holm, wilson=wilson, newcombe=newcombe,
                    empirical_p_upper=empirical_p_upper)
```

### [82] TOOL RESULT — Edit · 2026-10-26 14:43:45 UTC

```
{"filePath": "/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/make_nb.py", "oldString": "class _Stats:                     # notebook only: analysis9.py calls these functions as `S.<name>` (import stats9 as S)\n    share, share_mean_of_ratios, boot_share_ci, boot_mean_ci = (staticmethod(share), staticmethod(share_mean_of_ratios),\n                                                                 staticmethod(boot_share_ci), staticmethod(boot_mean_ci))\n    empirical_p_upper = staticmethod(empirical_p_upper)\n\n\nS = _Stats", "newString": "# notebook only: analysis9.py does `import stats9 as S` and calls S.share(...), S.boot_share_ci(...), ...\nS = SimpleNamespace(js_div=js_div, share=share, share_mean_of_ratios=share_mean_of_ratios, boot_ci=boot_ci,\n                    boot_share_ci=boot_share_ci, boot_mean_ci=boot_mean_ci, mcnemar_exact=mcnemar_exact,\n                    sign_flip_p=sign_flip_p, holm=holm, wilson=wilson, newcombe=newcombe,\n                    empirical_p_upper=empirical_p_upper)", "originalFile": null, "structuredPatch": [{"oldStart": 488, "oldLines": 13, "newStart": 488, "newLines": 11, "lines": ["     return float((1 + np.sum(null >= x)) / (1 + len(null)))", " ", " ", "-class _Stats:                     # notebook only: analysis9.py calls these functions as `S.<name>` (import stats9 as S)", "-    share, share_mean_of_ratios, boot_share_ci, boot_mean_ci = (staticmethod(share), staticmethod(share_mean_of_ratios),", "-                                                                 staticmethod(boot_share_ci), staticmethod(boot_mean_ci))", "-    empirical_p_upper = staticmethod(empirical_p_upper)", "-", "-", "-S = _Stats", "+# notebook only: analysis9.py does `import stats9 as S` and calls S.share(...), S.boot_share_ci(...), ...", "+S = SimpleNamespace(js_div=js_div, share=share, share_mean_of_ratios=share_mean_of_ratios, boot_ci=boot_ci,", "+                    boot_share_ci=boot_share_ci, boot_mean_ci=boot_mean_ci, mcnemar_exact=mcnemar_exact,", "+                    sign_flip_p=sign_flip_p, holm=holm, wilson=wilson, newcombe=newcombe,", "+                    empirical_p_upper=empirical_p_upper)", " ''')", " ", " # ---------------------------------------------------------------------------------------------------------- materialise"]}], "userModified": false, "replaceAll": false}
```

### [83] TOOL CALL — Edit · 2026-10-26 14:43:45 UTC

```
File: /tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/make_nb.py
OLD: from datetime import datetime, timezone
from typing import Any, Iterable, Sequence

import numpy as np
NEW: from datetime import datetime, timezone
from types import SimpleNamespace   # notebook only: stands in for `import stats9 as S`
from typing import Any, Iterable, Sequence

import numpy as np
```

### [84] TOOL RESULT — Edit · 2026-10-26 14:43:45 UTC

```
{"filePath": "/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/make_nb.py", "oldString": "from datetime import datetime, timezone\nfrom typing import Any, Iterable, Sequence\n\nimport numpy as np", "newString": "from datetime import datetime, timezone\nfrom types import SimpleNamespace   # notebook only: stands in for `import stats9 as S`\nfrom typing import Any, Iterable, Sequence\n\nimport numpy as np", "originalFile": null, "structuredPatch": [{"oldStart": 99, "oldLines": 6, "newStart": 99, "newLines": 7, "lines": [" import random", " import statistics", " from datetime import datetime, timezone", "+from types import SimpleNamespace   # notebook only: stands in for `import stats9 as S`", " from typing import Any, Iterable, Sequence", " ", " import numpy as np"]}], "userModified": false, "replaceAll": false}
```

### [85] TOOL CALL — Bash · 2026-10-26 14:43:45 UTC

```
Generate notebook and run prototype at minimum config:
SP="/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad"; W=/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd; mkdir -p "$SP/proto" && cp "$W/mini_demo_data.json" "$SP/proto/" && cd "$SP" && python3 make_nb.py "$SP/proto/code_demo.ipynb" "$SP/proto/proto.py" && cd "$SP/proto" && MPLBACKEND=Agg timeout 300 "$SP/venv/bin/python" proto.py 2>&1 | tail -120
```

### [86] TOOL RESULT — Bash · 2026-10-26 14:43:49 UTC

```
{"stdout": "wrote /tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/proto/code_demo.ipynb with 35 cells (21 code)\nwrote /tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/proto/proto.py\nanalyze      b1_9.py analyze ; b3_9.py analyze ; analysis9.py\n             -> replayed here: analysis9.py: the committed B2 rules (shares, nulls, Q1-Q3, verdict, localisation)\ngenerate     b2gen9.py gpu ; b2gen9.py label ; b2gen9.py analyze\nfigures      figures9.py\n             -> replayed here: figures9.py: F3, F4, F5 and an F8-style activation-geometry plot\npositioning  positioning9.py\nrederive     rederive9.py\n             -> replayed here: rederive9.py: stdlib re-derivation of the B2 numbers + placebos\noutputs      outputs9.py\nB3: wrote 2 prompts x 1429 arms -> results/b2_tf_B3.jsonl; 55 REV arms -> results/b2_rev_B3.jsonl\nT10: wrote 2 prompts x 1429 arms -> results/b2_tf_T10.jsonl; 55 REV arms -> results/b2_rev_T10.jsonl\n\nB3 W1|guy: m_I 1.298, m_B -0.806; patched margins: FSTACK -0.849, mlp|L35 -0.731, head|L23|H10 1.335, R0 -1.308, SPEC 1.536, RSfork23 -0.225, RSfork36 0.082\nB3: re-drawn sets identical to the patched ones: R 2/2, R-pure 2/2, SPEC-R 2/2\n   FSTACK node    |delta| at fork    tolerance #candidates   R0 replacement\n   mlp|L26                  48.48   [0.5, 2.0]           5   mlp|L23 (|delta| 31.99)\n   mlp|L27                  63.18   [0.5, 2.0]           5   mlp|L31 (|delta| 114.76)\n   mlp|L28                  75.10   [0.5, 2.0]           5   mlp|L33 (|delta| 140.80)\n   mlp|L30                 100.94  [0.7, 1.43]           3   mlp|L29 (|delta| 93.70)\n   mlp|L32                 125.88  [0.7, 1.43]           4   mlp|L34 (|delta| 167.38)\n   head|L23|H10              7.19  [0.7, 1.43]          83   head|L34|H31 (|delta| 9.64)\n   head|L27|H31             14.20  [0.7, 1.43]          36   head|L27|H28 (|delta| 9.99)\n   head|L29|H6               9.75  [0.7, 1.43]          58   head|L34|H2 (|delta| 12.41)\n   head|L33|H14             12.16  [0.7, 1.43]          40   head|L35|H0 (|delta| 13.19)\n   head|L34|H28             40.37  [0.7, 1.43]           4   head|L34|H21 (|delta| 32.14)\nT10: re-drawn sets identical to the patched ones: R 2/2, R-pure 2/2, SPEC-R 2/2\n   FSTACK node    |delta| at fork    tolerance #candidates   R0 replacement\n   mlp|L26                  52.23   [0.5, 2.0]           4   mlp|L29 (|delta| 102.39)\n   mlp|L27                  73.34   [0.5, 2.0]           4   mlp|L31 (|delta| 133.77)\n   mlp|L28                  91.20   [0.5, 2.0]           3   mlp|L33 (|delta| 171.61)\n   mlp|L30                 129.55  [0.7, 1.43]           3   mlp|L33 (|delta| 171.61)\n   mlp|L32                 145.44  [0.7, 1.43]           3   mlp|L31 (|delta| 133.77)\n   head|L23|H10              7.60  [0.7, 1.43]          80   head|L27|H23 (|delta| 5.54)\n   head|L27|H31             11.50  [0.7, 1.43]          36   head|L28|H7 (|delta| 12.62)\n   head|L29|H6               6.03  [0.7, 1.43]         109   head|L35|H3 (|delta| 4.97)\n   head|L33|H14              7.13  [0.7, 1.43]          83   head|L27|H29 (|delta| 5.40)\n   head|L34|H28             24.13  [0.7, 1.43]          21   head|L32|H21 (|delta| 28.24)\n14:43:46|INFO   |B2 verdict PARTIAL: B3: FSTACK 1.081 (R median 0.746, p95 1.210), SPEC -0.089, RS36 0.582, loc written upstream; T10: FSTACK 0.634 (R median 0.181, p95 0.200), SPEC -0.045, RS36 0.445, loc distributed\n\nanalysis done in 0.0s on 2 prompts/unit, N_BOOT = 10\n\n[B3] minimum spanning tree weight: gap m_I - m_B = 2.09 nats [2.07 2.1 ]\n   share FSTACK       +1.081  95% CI [1.034 1.144]\n   share F_MLP        +1.156  95% CI [1.126 1.195]\n   share F_HEAD       +0.234  95% CI [0.204 0.274]\n   share SPEC         -0.089  95% CI [-0.108 -0.066]\n   share W_all        +0.275  95% CI [0.273 0.278]\n   share self_FSTACK  +0.024  95% CI [0.02  0.027]\n   random sets R (n=2): median +0.746, p95 +1.210, empirical p(FSTACK) = 0.667\n   RS-fork(23) +0.745, RS-fork(36) +0.582, RS-prefix(23) +0.641; unembedding-only share (carried) 0.43\n   top singles: mlp|L35 0.95, mlp|L28 0.66, mlp|L29 0.60, mlp|L27 0.54, mlp|L26 0.53\n   Q1 True  Q2 False  Q3 True  localisation: written upstream\n\n[T10] connected components: gap m_I - m_B = 6.93 nats [6.2  7.87]\n   share FSTACK       +0.634  95% CI [0.613 0.655]\n   share F_MLP        +0.599  95% CI [0.579 0.62 ]\n   share F_HEAD       +0.319  95% CI [0.259 0.379]\n   share SPEC         -0.045  95% CI [-0.051 -0.04 ]\n   share W_all        +0.346  95% CI [0.314 0.379]\n   share self_FSTACK  +0.005  95% CI [0.004 0.007]\n   random sets R (n=2): median +0.181, p95 +0.200, empirical p(FSTACK) = 0.333\n   RS-fork(23) +0.171, RS-fork(36) +0.445, RS-prefix(23) +0.442; unembedding-only share (carried) 0.85\n   top singles: mlp|L30 0.41, mlp|L35 0.35, mlp|L27 0.33, head|L23|H10 0.21, mlp|L34 0.20\n   Q1 True  Q2 False  Q3 True  localisation: distributed\n\nB2 verdict: PARTIAL (Q1 both True, Q2 both False, Q3 both True)\n14:43:46|INFO   |figure F3_b2_singles_by_layer\n14:43:47|INFO   |figure F4_b2_residual_swaps\n14:43:47|INFO   |figure F5_b2_random_null\n/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/proto/proto.py:860: UserWarning: You passed a edgecolor/edgecolors ('k') for an unfilled marker ('x').  Matplotlib is ignoring the edgecolor in favor of the facecolor.  This behavior may change in the future.\n  sc = ax.scatter(Y[ii, 0], Y[ii, 1], c=[cols[i] for i in ii], cmap=\"coolwarm\", marker=mk, s=28,\n14:43:47|INFO   |figure F8_b2_geometry_pca_demo\nB3: mean |instruct state| = 645\n   FSTACK-patched           moves the state by  176.1 (L2), cosine with the FSTACK shift +1.00\n   median random-patched    moves the state by  103.4 (L2), cosine with the FSTACK shift +0.49\n   RS-fork(23)-patched      moves the state by  120.4 (L2), cosine with the FSTACK shift +0.44\nT10: mean |instruct state| = 579\n   FSTACK-patched           moves the state by  236.7 (L2), cosine with the FSTACK shift +1.00\n   median random-patched    moves the state by  134.1 (L2), cosine with the FSTACK shift +0.50\n   RS-fork(23)-patched      moves the state by  165.1 (L2), cosine with the FSTACK shift +0.64\nrederive: 0 mismatches\nB3: stdlib FSTACK share 1.081350, R median 0.745938, empirical p 0.6667 | placebo (permuted node labels) frac p<=0.05 = 0.000 -> fails as required: True; anchor-swap share -0.081\nT10: stdlib FSTACK share 0.633974, R median 0.180869, empirical p 0.3333 | placebo (permuted node labels) frac p<=0.05 = 0.000 -> fails as required: True; anchor-swap share +0.366\nunit  quantity                                    this notebook           original run\n--------------------------------------------------------------------------------------\nB3    prompts                                                 2                     20\nB3    gap m_I - m_B (nats)                                2.086                  2.059\nB3    FSTACK share                                        1.081                  0.998\nB3    FSTACK share 95% CI                          [1.03, 1.14]           [0.96, 1.04]\nB3    F_MLP share                                         1.156                  1.079\nB3    F_HEAD share                                        0.234                  0.174\nB3    random sets R: median share                         0.746                  0.807\nB3    random sets R: 95th pct                             1.210                  1.413\nB3    empirical p (FSTACK vs R)                           0.667                  0.451\nB3    R-pure: median / p                           [0.92, 0.33]           [0.66, 0.04]\nB3    SPEC share                                         -0.089                 -0.019\nB3    RS-fork(23) / RS-fork(36)                    [0.74, 0.58]           [0.78, 0.57]\nB3    RS-prefix(23)                                       0.641                  0.443\nB3    unembedding-only share (carried)                    0.426                  0.426\nB3    REV: share opened by FSTACK                        -0.269                 -0.304\nB3    Q1 / Q2 / Q3                          True / False / True    True / False / True\nB3    localisation                             written upstream            distributed\nT10   prompts                                                 2                     20\nT10   gap m_I - m_B (nats)                                6.925                  4.519\nT10   FSTACK share                                        0.634                  0.452\nT10   FSTACK share 95% CI                          [0.61, 0.65]           [0.28, 0.57]\nT10   F_MLP share                                         0.599                  0.406\nT10   F_HEAD share                                        0.319                  0.302\nT10   random sets R: median share                         0.181                 -0.223\nT10   random sets R: 95th pct                             0.200                  0.056\nT10   empirical p (FSTACK vs R)                           0.333                  0.020\nT10   R-pure: median / p                          [-0.16, 0.33]          [-0.46, 0.02]\nT10   SPEC share                                         -0.045                 -0.167\nT10   RS-fork(23) / RS-fork(36)                    [0.17, 0.44]          [-0.05, 0.15]\nT10   RS-prefix(23)                                       0.442                  0.372\nT10   unembedding-only share (carried)                    0.850                  0.850\nT10   REV: share opened by FSTACK                         0.279                  0.223\nT10   Q1 / Q2 / Q3                          True / False / True    False / True / True\nT10   localisation                                  distributed            distributed\nboth  B2 verdict                                        PARTIAL                PARTIAL", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [87] THINKING · 2026-10-26 14:43:59 UTC

```
Prototype passed the minimal-config test cleanly, with zero mismatches and identical re-drawn random sets. Now I'll rerun it at full scale (20 prompts, 10,000 resamples, 50+20 random sets, 200 placebo draws) to confirm exact agreement and check runtime.
```

### [88] TOOL CALL — Bash · 2026-10-26 14:43:59 UTC

```
Run prototype at original full configuration:
SP="/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad"; cd "$SP/proto" && sed -e 's/^N_PROMPTS_PER_UNIT = 2 /N_PROMPTS_PER_UNIT = 20 /; s/^N_BOOT = 10 /N_BOOT = 10000 /; s/^N_RAND = 2 /N_RAND = 50 /; s/^N_RAND_SPEC = 2 /N_RAND_SPEC = 20 /; s/^N_PLACEBO_DRAWS = 2 /N_PLACEBO_DRAWS = 200 /' proto.py > proto_full.py && grep -n "^N_" proto_full.py && /usr/bin/time -v env MPLBACKEND=Agg "$SP/venv/bin/python" proto_full.py > full.log 2> time.log; tail -50 full.log; grep -E "Elapsed|Maximum resident" time.log; grep -n "analysis done\|rederive:\|re-drawn" full.log
```

### [89] TOOL RESULT — Bash · 2026-10-26 14:43:59 UTC

```
{"stdout": "65:N_PROMPTS_PER_UNIT = 20      # prompts per unit taken from the data (original: 20 = all; minimum 2)\n66:N_BOOT = 10000                 # bootstrap resamples per CI, cfg9.N_BOOT (original: 10000; minimum 10)\n67:N_RAND = 50                  # matched random component sets per null R / R-pure / R-scaled, cfg9.N_RAND (original: 50; minimum 2)\n68:N_RAND_SPEC = 20             # matched random SPEC sets, cfg9.N_RAND_SPEC (original: 20; minimum 2)\n69:N_PLACEBO_DRAWS = 200         # placebo draws in the stdlib re-derivation, rederive9.b2 (original: 200; minimum 2)\n121:N_LAYERS = 36\n122:N_HEADS = 32", "stderr": "", "interrupted": false, "isImage": false, "returnCodeInterpretation": "No matches found", "noOutputExpected": false}
```

### [90] TOOL CALL — Bash · 2026-10-26 14:44:09 UTC

```
Rerun full-config prototype with timing:
SP="/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad"; cd "$SP/proto" && cat time.log | head; ls -la; start=$(date +%s); MPLBACKEND=Agg "$SP/venv/bin/python" proto_full.py > full.log 2>&1; echo "exit $? elapsed $(( $(date +%s) - start ))s"; grep -n "analysis done\|rederive:\|re-drawn\|Error\|Traceback" full.log; sed -n '/^unit  quantity/,$p' full.log
```

### [91] TOOL RESULT — Bash · 2026-10-26 14:44:11 UTC

```
{"stdout": "/bin/bash: line 1: /usr/bin/time: No such file or directory\ntotal 4376\ndrwxrwxrwx 5 aii-agent aii-agent     167 Oct 26 14:43 .\ndrwx------ 4 aii-agent aii-agent      85 Oct 26 14:43 ..\n-rw-rw-rw- 1 aii-agent aii-agent   85584 Oct 26 14:43 code_demo.ipynb\ndrwxrwxrwx 2 aii-agent aii-agent    4096 Oct 26 14:43 figures\n-rw-rw-rw- 1 aii-agent aii-agent       0 Oct 26 14:43 full.log\ndrwxrwxrwx 2 aii-agent aii-agent      47 Oct 26 14:43 logs\n-rw-rw-rw- 1 aii-agent aii-agent 4273245 Oct 26 14:43 mini_demo_data.json\n-rw-rw-rw- 1 aii-agent aii-agent   52096 Oct 26 14:43 proto.py\n-rw-rw-rw- 1 aii-agent aii-agent   52104 Oct 26 14:43 proto_full.py\ndrwxrwxrwx 2 aii-agent aii-agent    4096 Oct 26 14:43 results\n-rw-rw-rw- 1 aii-agent aii-agent      60 Oct 26 14:43 time.log\nexit 0 elapsed 6s\n1:GitHub data unavailable, using local mini_demo_data.json: HTTP Error 404: Not Found\n49:B3: re-drawn sets identical to the patched ones: R 50/50, R-pure 50/50, SPEC-R 20/20\n61:T10: re-drawn sets identical to the patched ones: R 50/50, R-pure 50/50, SPEC-R 20/20\n75:analysis done in 2.7s on 20 prompts/unit, N_BOOT = 10000\n116:rederive: 0 mismatches\nunit  quantity                                    this notebook           original run\n--------------------------------------------------------------------------------------\nB3    prompts                                                20                     20\nB3    gap m_I - m_B (nats)                                2.059                  2.059\nB3    FSTACK share                                        0.998                  0.998\nB3    FSTACK share 95% CI                          [0.96, 1.04]           [0.96, 1.04]\nB3    F_MLP share                                         1.079                  1.079\nB3    F_HEAD share                                        0.174                  0.174\nB3    random sets R: median share                         0.807                  0.807\nB3    random sets R: 95th pct                             1.413                  1.413\nB3    empirical p (FSTACK vs R)                           0.451                  0.451\nB3    R-pure: median / p                           [0.66, 0.04]           [0.66, 0.04]\nB3    SPEC share                                         -0.019                 -0.019\nB3    RS-fork(23) / RS-fork(36)                    [0.78, 0.57]           [0.78, 0.57]\nB3    RS-prefix(23)                                       0.443                  0.443\nB3    unembedding-only share (carried)                    0.426                  0.426\nB3    REV: share opened by FSTACK                        -0.304                 -0.304\nB3    Q1 / Q2 / Q3                          True / False / True    True / False / True\nB3    localisation                                  distributed            distributed\nT10   prompts                                                20                     20\nT10   gap m_I - m_B (nats)                                4.519                  4.519\nT10   FSTACK share                                        0.452                  0.452\nT10   FSTACK share 95% CI                          [0.28, 0.57]           [0.28, 0.57]\nT10   F_MLP share                                         0.406                  0.406\nT10   F_HEAD share                                        0.302                  0.302\nT10   random sets R: median share                        -0.223                 -0.223\nT10   random sets R: 95th pct                             0.056                  0.056\nT10   empirical p (FSTACK vs R)                           0.020                  0.020\nT10   R-pure: median / p                          [-0.46, 0.02]          [-0.46, 0.02]\nT10   SPEC share                                         -0.167                 -0.167\nT10   RS-fork(23) / RS-fork(36)                   [-0.05, 0.15]          [-0.05, 0.15]\nT10   RS-prefix(23)                                       0.372                  0.372\nT10   unembedding-only share (carried)                    0.850                  0.850\nT10   REV: share opened by FSTACK                         0.223                  0.223\nT10   Q1 / Q2 / Q3                          False / True / True    False / True / True\nT10   localisation                                  distributed            distributed\nboth  B2 verdict                                        PARTIAL                PARTIAL", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [92] THINKING · 2026-10-26 14:44:29 UTC

```
All recomputed numbers at the original configuration match the original run (verdict included), with the script running in 6s. Next I'll compare the recomputed summary against the original b2_summary.json at full precision and examine the figures.
```

### [93] TOOL CALL — Bash · 2026-10-26 14:44:29 UTC

```
Compare recomputed summary with original at full precision:
SP="/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad"; A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50; cd /tmp && python3 -I - "$SP/proto/results/b2_summary.json" "$A/results/b2_summary.json" "$SP/proto/results/rederive.json" "$A/results/rederive.json" <<'EOF'
import json,sys,math
a=json.load(open(sys.argv[1])); b=json.load(open(sys.argv[2]))
n=0; bad=[]
def walk(x,y,path):
    global n
    if path.endswith('utc') or 'gpu_tests' in path or 'v1_variable' in path: return
    if isinstance(x,dict) and isinstance(y,dict):
        for k in set(x)|set(y):
            if k not in x or k not in y: bad.append((path+'/'+str(k),'missing', k in x, k in y)); continue
            walk(x[k],y[k],path+'/'+str(k))
    elif isinstance(x,list) and isinstance(y,list):
        if len(x)!=len(y): bad.append((path,'len',len(x),len(y))); return
        for i,(p,q) in enumerate(zip(x,y)): walk(p,q,path+f'[{i}]')
    elif isinstance(x,(int,float)) and isinstance(y,(int,float)) and not isinstance(x,bool):
        n+=1
        if not (x==y or (abs(x-y)<=1e-12)): bad.append((path,x,y))
    else:
        n+=1
        if x!=y: bad.append((path,x,y))
walk(a,b,'')
print('compared',n,'leaves; mismatches',len(bad)); print(bad[:10])
ra=json.load(open(sys.argv[3])); rb=json.load(open(sys.argv[4]))
for u in ('B2_B3','B2_T10'):
    print(u, {k:(ra[u][k], rb[u][k]) for k in ra[u] if ra[u][k]!=rb[u][k]})
EOF
```

### [94] TOOL RESULT — Bash · 2026-10-26 14:44:29 UTC

```
{"stdout": "compared 4246 leaves; mismatches 0\n[]\nB2_B3 {}\nB2_T10 {}", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [95] TOOL CALL — Read · 2026-10-26 14:44:29 UTC

```
/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/proto/figures/F8_b2_geometry_pca_demo.png
```

### [96] TOOL RESULT — Read · 2026-10-26 14:44:29 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [97] SYSTEM-USER prompt · 2026-10-26 14:44:29 UTC

```
[Image: original 2200x880, displayed at 2000x800. Multiply coordinates by 1.10 to map to original image.]
```

### [98] TOOL CALL — Read · 2026-10-26 14:44:29 UTC

```
/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/proto/figures/summary_b2.png
```

### [99] TOOL RESULT — Read · 2026-10-26 14:44:29 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [100] THINKING · 2026-10-26 14:45:23 UTC

```
The recomputation matches the original to within 1e-12, but the plots revealed my draft interpretation misdescribed the geometry (random patches move only ~60% as far as FSTACK and only partly in the same direction) and that the summary figure's legends hide some points. I'll fix the text, address the legend issue, add markdown cells between code cells, and first pull the exact numbers to cite.
```

### [101] TOOL CALL — Bash · 2026-10-26 14:45:23 UTC

```
Extract numbers for the interpretation text:
SP="/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad"; cd /tmp && python3 -I - "$SP/proto/results/b2_summary.json" <<'EOF'
import json,sys
s=json.load(open(sys.argv[1]))
for u,r in s['units'].items():
    print(u, 'sum_singles_FSTACK', round(r['sum_singles_FSTACK'],3), 'interaction', round(r['interaction_FSTACK_minus_sum_singles'],3), 'FSTACK', round(r['arms']['FSTACK']['share'],3))
    print('  top10', [(k, round(v,2)) for k,v in r['singles_top10']])
    print('  jaccard', r['jaccard_top10_vs_FSTACK'], 'ranks', {k:(v['rank'],round(v['share'],2)) for k,v in r['fstack_single_ranks'].items()})
    print('  m_I range', round(min(r['m_I']),2), round(max(r['m_I']),2), 'm_B range', round(min(r['m_B']),2), round(max(r['m_B']),2))
    print('  RS_fork', {k: round(v,2) for k,v in r['RS_fork'].items()})
    print('  W', {k: round(r['arms'][k]['share'],2) for k in ('W_all','W26','W27','W28','W30','W32')})
    print('  self', r['self_patch_max_abs_dm'], 'xprompt', round(r['arms']['xprompt_FSTACK']['share'],3), 'ALL_attn', round(r['arms']['ALL_attn']['share'],3), 'ALL_heads', round(r['arms']['ALL_heads']['share'],3))
    print('  null_Rscaled', {k:round(v,3) for k,v in r['null_Rscaled'].items() if k!='shares'}, 'SPECR', {k:round(v,3) for k,v in r['null_SPECR'].items() if k!='shares'})
EOF
```

### [102] TOOL RESULT — Bash · 2026-10-26 14:45:23 UTC

```
{"stdout": "B3 sum_singles_FSTACK 1.958 interaction -0.96 FSTACK 0.998\n  top10 [('mlp|L35', 0.98), ('mlp|L28', 0.62), ('mlp|L29', 0.56), ('mlp|L26', 0.52), ('mlp|L27', 0.49), ('mlp|L33', 0.39), ('mlp|L21', 0.34), ('mlp|L34', 0.31), ('head|L27|H31', 0.28), ('mlp|L30', 0.27)]\n  jaccard 0.3333333333333333 ranks {'mlp|L26': (4, 0.52), 'mlp|L27': (5, 0.49), 'mlp|L28': (2, 0.62), 'mlp|L30': (9, 0.27), 'mlp|L32': (34, -0.12), 'head|L23|H10': (1113, -0.04), 'head|L27|H31': (1, 0.28), 'head|L29|H6': (1081, -0.03), 'head|L33|H14': (1126, -0.06), 'head|L34|H28': (162, 0.01)}\n  m_I range 0.98 1.85 m_B range -0.85 -0.59\n  RS_fork {'0': 0.0, '1': -0.02, '2': 0.0, '3': 0.01, '4': 0.0, '5': -0.01, '6': 0.01, '7': 0.02, '8': -0.01, '9': -0.03, '10': -0.06, '11': -0.08, '12': -0.11, '13': -0.08, '14': -0.04, '15': -0.01, '16': 0.1, '17': 0.08, '18': -0.06, '19': -0.06, '20': 0.08, '21': 0.25, '22': 0.63, '23': 0.78, '24': 1.19, '25': 1.25, '26': 1.3, '27': 1.46, '28': 1.49, '29': 1.31, '30': 1.04, '31': 0.9, '32': 0.69, '33': 0.79, '34': 0.72, '35': 0.87, '36': 0.57}\n  W {'W_all': 0.23, 'W26': 0.07, 'W27': -0.16, 'W28': -0.0, 'W30': -0.03, 'W32': 0.43}\n  self 0.10977554321289062 xprompt 1.001 ALL_attn 0.573 ALL_heads 0.571\n  null_Rscaled {'median': 0.642, 'p95': 1.013, 'max': 1.113, 'empirical_p_upper': 0.098, 'frac_below_ref': 0.92} SPECR {'median': 0.383, 'p95': 1.182, 'max': 1.243, 'empirical_p_upper': 0.952, 'frac_below_ref': 0.05}\nT10 sum_singles_FSTACK 1.102 interaction -0.651 FSTACK 0.452\n  top10 [('mlp|L30', 0.53), ('mlp|L35', 0.38), ('mlp|L34', 0.26), ('head|L23|H10', 0.21), ('head|L27|H31', 0.18), ('mlp|L14', 0.17), ('mlp|L21', 0.17), ('mlp|L18', 0.17), ('mlp|L24', 0.12), ('head|L35|H8', 0.12)]\n  jaccard 0.17647058823529413 ranks {'mlp|L26': (11, 0.08), 'mlp|L27': (9, 0.09), 'mlp|L28': (8, 0.1), 'mlp|L30': (1, 0.53), 'mlp|L32': (31, -0.1), 'head|L23|H10': (1, 0.21), 'head|L27|H31': (2, 0.18), 'head|L29|H6': (389, 0.0), 'head|L33|H14': (398, 0.0), 'head|L34|H28': (500, -0.0)}\n  m_I range 0.21 8.95 m_B range -0.33 0.2\n  RS_fork {'0': -0.01, '1': -0.03, '2': -0.05, '3': -0.01, '4': -0.02, '5': -0.03, '6': -0.03, '7': -0.06, '8': -0.08, '9': -0.11, '10': -0.15, '11': -0.21, '12': -0.09, '13': -0.0, '14': 0.03, '15': 0.12, '16': 0.17, '17': 0.5, '18': 0.44, '19': 0.2, '20': 0.07, '21': -0.05, '22': -0.01, '23': -0.05, '24': -0.18, '25': 0.09, '26': -0.17, '27': 0.17, '28': 0.28, '29': 0.43, '30': 0.4, '31': 0.55, '32': 0.52, '33': 0.51, '34': 0.5, '35': 0.45, '36': 0.15}\n  W {'W_all': 0.38, 'W26': -0.03, 'W27': -0.07, 'W28': 0.21, 'W30': 0.23, 'W32': 0.03}\n  self 0.14809036254882812 xprompt 0.454 ALL_attn 0.152 ALL_heads 0.151\n  null_Rscaled {'median': -0.25, 'p95': 0.023, 'max': 0.089, 'empirical_p_upper': 0.02, 'frac_below_ref': 1.0} SPECR {'median': 0.562, 'p95': 1.136, 'max': 1.284, 'empirical_p_upper': 1.0, 'frac_below_ref': 0.0}", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [103] TOOL CALL — Bash · 2026-10-26 14:45:45 UTC

```
Show full-config geometry and placebo lines:
SP="/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad"; grep -A3 "mean |instruct state|" "$SP/proto/full.log"; grep -B2 -A6 "placebo" "$SP/proto/full.log" | head -20
```

### [104] TOOL RESULT — Bash · 2026-10-26 14:45:45 UTC

```
{"stdout": "B3: mean |instruct state| = 643\n   FSTACK-patched           moves the state by  173.0 (L2), cosine with the FSTACK shift +1.00\n   median random-patched    moves the state by  102.2 (L2), cosine with the FSTACK shift +0.48\n   RS-fork(23)-patched      moves the state by  120.7 (L2), cosine with the FSTACK shift +0.43\nT10: mean |instruct state| = 574\n   FSTACK-patched           moves the state by  230.1 (L2), cosine with the FSTACK shift +1.00\n   median random-patched    moves the state by  129.5 (L2), cosine with the FSTACK shift +0.48\n   RS-fork(23)-patched      moves the state by  163.8 (L2), cosine with the FSTACK shift +0.62\npositioning  positioning9.py\nrederive     rederive9.py\n             -> replayed here: rederive9.py: stdlib re-derivation of the B2 numbers + placebos\noutputs      outputs9.py\nB3: wrote 20 prompts x 1429 arms -> results/b2_tf_B3.jsonl; 55 REV arms -> results/b2_rev_B3.jsonl\nT10: wrote 20 prompts x 1429 arms -> results/b2_tf_T10.jsonl; 55 REV arms -> results/b2_rev_T10.jsonl\n\nB3 W1|guy: m_I 1.298, m_B -0.806; patched margins: FSTACK -0.849, mlp|L35 -0.731, head|L23|H10 1.335, R0 -1.308, SPEC 1.536, RSfork23 -0.225, RSfork36 0.082\nB3: re-drawn sets identical to the patched ones: R 50/50, R-pure 50/50, SPEC-R 20/20\n--\n   RS-fork(23)-patched      moves the state by  163.8 (L2), cosine with the FSTACK shift +0.62\nrederive: 0 mismatches\nB3: stdlib FSTACK share 0.997696, R median 0.807268, empirical p 0.4510 | placebo (permuted node labels) frac p<=0.05 = 0.030 -> fails as required: True; anchor-swap share +0.002\nT10: stdlib FSTACK share 0.451707, R median -0.223247, empirical p 0.0196 | placebo (permuted node labels) frac p<=0.05 = 0.055 -> fails as required: True; anchor-swap share +0.548\nunit  quantity                                    this notebook           original run\n--------------------------------------------------------------------------------------\nB3    prompts                                                20                     20\nB3    gap m_I - m_B (nats)                                2.059                  2.059\nB3    FSTACK share                                        0.998                  0.998\nB3    FSTACK share 95% CI                          [0.96, 1.04]           [0.96, 1.04]", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [105] THINKING · 2026-10-26 14:46:45 UTC

```
I've confirmed the full-config geometry numbers (FSTACK 173/230 L2, median random similarity ~59%/56%, cosine 0.48, state norms ≈600). Now I'll update the interpretation with these values, fix the legend placement, and insert the missing markdown cells between code cells.
```

### [106] TOOL CALL — Edit · 2026-10-26 14:46:45 UTC

```
File: /tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/make_nb.py
OLD:     return {"sets": sets, "meta": meta, "n_distinct_sets": len({tuple(sorted(s)) for s in sets}), "seed": seed}
''')

code(r'''
# rerun the draws exactly as cmap9.base_stage_extras (R, R-pure) and cmap9.stage_patch (SPEC) did, from the stored norms
NEW:     return {"sets": sets, "meta": meta, "n_distinct_sets": len({tuple(sorted(s)) for s in sets}), "seed": seed}
''')

md(r'''
The next cell reruns the three draws with the committed seeds (`SEED_RAND + unit index` for R and R-pure,
`SEED_RAND + 100 + unit index` for SPEC). It then counts how many of the first `N_RAND` / `N_RAND_SPEC` sets match the
ones actually patched on the GPU, and lists the matching details for the FSTACK nodes together with the first random
set's replacement for each node.
''')

code(r'''
# rerun the draws exactly as cmap9.base_stage_extras (R, R-pure) and cmap9.stage_patch (SPEC) did, from the stored norms
```

### [107] TOOL RESULT — Edit · 2026-10-26 14:46:45 UTC

```
{"filePath": "/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/make_nb.py", "oldString": "    return {\"sets\": sets, \"meta\": meta, \"n_distinct_sets\": len({tuple(sorted(s)) for s in sets}), \"seed\": seed}\n''')\n\ncode(r'''\n# rerun the draws exactly as cmap9.base_stage_extras (R, R-pure) and cmap9.stage_patch (SPEC) did, from the stored norms", "newString": "    return {\"sets\": sets, \"meta\": meta, \"n_distinct_sets\": len({tuple(sorted(s)) for s in sets}), \"seed\": seed}\n''')\n\nmd(r'''\nThe next cell reruns the three draws with the committed seeds (`SEED_RAND + unit index` for R and R-pure,\n`SEED_RAND + 100 + unit index` for SPEC). It then counts how many of the first `N_RAND` / `N_RAND_SPEC` sets match the\nones actually patched on the GPU, and lists the matching details for the FSTACK nodes together with the first random\nset's replacement for each node.\n''')\n\ncode(r'''\n# rerun the draws exactly as cmap9.base_stage_extras (R, R-pure) and cmap9.stage_patch (SPEC) did, from the stored norms", "originalFile": null, "structuredPatch": [{"oldStart": 613, "oldLines": 6, "newStart": 613, "newLines": 13, "lines": ["     return {\"sets\": sets, \"meta\": meta, \"n_distinct_sets\": len({tuple(sorted(s)) for s in sets}), \"seed\": seed}", " ''')", " ", "+md(r'''", "+The next cell reruns the three draws with the committed seeds (`SEED_RAND + unit index` for R and R-pure,", "+`SEED_RAND + 100 + unit index` for SPEC). It then counts how many of the first `N_RAND` / `N_RAND_SPEC` sets match the", "+ones actually patched on the GPU, and lists the matching details for the FSTACK nodes together with the first random", "+set's replacement for each node.", "+''')", "+", " code(r'''", " # rerun the draws exactly as cmap9.base_stage_extras (R, R-pure) and cmap9.stage_patch (SPEC) did, from the stored norms", " rsets_all = read_json(RESULTS_DIR / \"random_sets.json\")"]}], "userModified": false, "replaceAll": false}
```

### [108] TOOL CALL — Edit · 2026-10-26 14:46:45 UTC

```
File: /tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/make_nb.py
OLD:                    "is the CPU analogue of RS-fork(36); the two parts sum to 1 by construction")
    return res
''')

code(r'''
def b2_unit(u: str, ui: int) -> dict[str, Any]:
NEW:                    "is the CPU analogue of RS-fork(36); the two parts sum to 1 by construction")
    return res
''')

md(r'''
`b2_unit` computes every B2 statistic of one unit from its rows and applies Q1-Q3 and the localisation rule. `b2`
combines the two units into the verdict and writes `results/b2_summary.json`, exactly as the original stage did.
''')

code(r'''
def b2_unit(u: str, ui: int) -> dict[str, Any]:
```

### [109] TOOL CALL — Edit · 2026-10-26 14:46:45 UTC

```
File: /tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/make_nb.py
OLD:     save(fig, "F5_b2_random_null")
''')

code(r'''
setup_logging("figures9")
NEW:     save(fig, "F5_b2_random_null")
''')

md(r'''
As in `figures9.main()`, the figures are drawn from the summary file the analysis just wrote. In F3, a single late MLP
that closes a large share on its own, while FSTACK as a whole is no larger than the sum of its parts, indicates
redundancy. In F5, the green line has to clear the grey random distribution for Q2.
''')

code(r'''
setup_logging("figures9")
```

### [110] TOOL CALL — Edit · 2026-10-26 14:46:45 UTC

```
File: /tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/make_nb.py
OLD:         out[f"B2_{u}"] = rec
''')

code(r'''
mism: list[str] = []
NEW:         out[f"B2_{u}"] = rec
''')

md(r'''
Run the re-derivation against `results/b2_summary.json` and write `results/rederive.json`. The original run reported
0 mismatches; the placebo rows must report `fails as required: True`.
''')

code(r'''
mism: list[str] = []
```

### [111] TOOL CALL — Edit · 2026-10-26 14:46:45 UTC

```
File: /tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/make_nb.py
OLD:     print(f"{u:<5} {k:<34} {_f(a):>22} {_f(b):>22}")
''')

code(r'''
fig, axes = plt.subplots(2, 2, figsize=(12, 7.6), gridspec_kw={"width_ratios": [1.25, 1]})
NEW:     print(f"{u:<5} {k:<34} {_f(a):>22} {_f(b):>22}")
''')

md(r'''
**Summary figure.**

* **Left**: the raw per-prompt fork margins, which are the data every share is computed from: the two anchors (instruct
  `m_I`, base `m_B`) and three patched instruct runs. Above 0 the default algorithm class is more likely, below 0 the
  alternative.
* **Right**: the shares that enter the committed rules, with their 95 % bootstrap CIs. The grey band is the central
  90 % of the matched random sets.
''')

code(r'''
fig, axes = plt.subplots(2, 2, figsize=(12, 8.4), gridspec_kw={"width_ratios": [1.25, 1]})
```

### [112] TOOL CALL — Edit · 2026-10-26 14:46:45 UTC

```
File: /tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/make_nb.py
OLD:     ax.axhline(0, color="k", lw=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(pids, rotation=70, fontsize=6)
    ax.set_ylabel("fork margin m = log P(D) - log P(A)")
    U = UNITS_DATA[u]
    ax.set_title(f"{u} ({U['name']}): D = {U['D_class']} {U['D_tokens'][:2]}, A = {U['A_class']} {U['A_tokens'][:2]}",
                 fontsize=8.5)
    ax.legend(fontsize=6.5, ncol=2, loc="best")
NEW:     ax.axhline(0, color="k", lw=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(pids, rotation=70, fontsize=6)
    ax.set_ylabel("fork margin m = log P(D) - log P(A)")
    U = UNITS_DATA[u]
    ax.set_title(f"{u} ({U['name']}): D = {U['D_class']} {U['D_tokens'][:2]}, A = {U['A_class']} {U['A_tokens'][:2]}",
                 fontsize=8.5)
    y0, y1 = ax.get_ylim()
    ax.set_ylim(y0, y1 + 0.42 * (y1 - y0))          # head room for the legend
    ax.legend(fontsize=6.5, ncol=3, loc="upper center")
```

### [113] TOOL RESULT — Edit · 2026-10-26 14:46:45 UTC

```
{"filePath": "/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/make_nb.py", "oldString": "                   \"is the CPU analogue of RS-fork(36); the two parts sum to 1 by construction\")\n    return res\n''')\n\ncode(r'''\ndef b2_unit(u: str, ui: int) -> dict[str, Any]:", "newString": "                   \"is the CPU analogue of RS-fork(36); the two parts sum to 1 by construction\")\n    return res\n''')\n\nmd(r'''\n`b2_unit` computes every B2 statistic of one unit from its rows and applies Q1-Q3 and the localisation rule. `b2`\ncombines the two units into the verdict and writes `results/b2_summary.json`, exactly as the original stage did.\n''')\n\ncode(r'''\ndef b2_unit(u: str, ui: int) -> dict[str, Any]:", "originalFile": null, "structuredPatch": [{"oldStart": 771, "oldLines": 6, "newStart": 771, "newLines": 11, "lines": ["     return res", " ''')", " ", "+md(r'''", "+`b2_unit` computes every B2 statistic of one unit from its rows and applies Q1-Q3 and the localisation rule. `b2`", "+combines the two units into the verdict and writes `results/b2_summary.json`, exactly as the original stage did.", "+''')", "+", " code(r'''", " def b2_unit(u: str, ui: int) -> dict[str, Any]:", "     pids, by, mI, mB = rows_by_arm(u)"]}], "userModified": false, "replaceAll": false}
```

### [114] TOOL RESULT — Edit · 2026-10-26 14:46:45 UTC

```
{"filePath": "/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/make_nb.py", "oldString": "    save(fig, \"F5_b2_random_null\")\n''')\n\ncode(r'''\nsetup_logging(\"figures9\")", "newString": "    save(fig, \"F5_b2_random_null\")\n''')\n\nmd(r'''\nAs in `figures9.main()`, the figures are drawn from the summary file the analysis just wrote. In F3, a single late MLP\nthat closes a large share on its own, while FSTACK as a whole is no larger than the sum of its parts, indicates\nredundancy. In F5, the green line has to clear the grey random distribution for Q2.\n''')\n\ncode(r'''\nsetup_logging(\"figures9\")", "originalFile": null, "structuredPatch": [{"oldStart": 1043, "oldLines": 6, "newStart": 1043, "newLines": 12, "lines": ["     save(fig, \"F5_b2_random_null\")", " ''')", " ", "+md(r'''", "+As in `figures9.main()`, the figures are drawn from the summary file the analysis just wrote. In F3, a single late MLP", "+that closes a large share on its own, while FSTACK as a whole is no larger than the sum of its parts, indicates", "+redundancy. In F5, the green line has to clear the grey random distribution for Q2.", "+''')", "+", " code(r'''", " setup_logging(\"figures9\")", " b2 = read_json(RESULTS_DIR / \"b2_summary.json\")   # as figures9.main(): the summary file written by the analysis"]}], "userModified": false, "replaceAll": false}
```

### [115] TOOL RESULT — Edit · 2026-10-26 14:46:45 UTC

```
{"filePath": "/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/make_nb.py", "oldString": "        out[f\"B2_{u}\"] = rec\n''')\n\ncode(r'''\nmism: list[str] = []", "newString": "        out[f\"B2_{u}\"] = rec\n''')\n\nmd(r'''\nRun the re-derivation against `results/b2_summary.json` and write `results/rederive.json`. The original run reported\n0 mismatches; the placebo rows must report `fails as required: True`.\n''')\n\ncode(r'''\nmism: list[str] = []", "originalFile": null, "structuredPatch": [{"oldStart": 1230, "oldLines": 6, "newStart": 1230, "newLines": 11, "lines": ["         out[f\"B2_{u}\"] = rec", " ''')", " ", "+md(r'''", "+Run the re-derivation against `results/b2_summary.json` and write `results/rederive.json`. The original run reported", "+0 mismatches; the placebo rows must report `fails as required: True`.", "+''')", "+", " code(r'''", " mism: list[str] = []", " out_rd: dict = {}"]}], "userModified": false, "replaceAll": false}
```

### [116] TOOL RESULT — Edit · 2026-10-26 14:46:45 UTC

```
{"filePath": "/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/make_nb.py", "oldString": "    print(f\"{u:<5} {k:<34} {_f(a):>22} {_f(b):>22}\")\n''')\n\ncode(r'''\nfig, axes = plt.subplots(2, 2, figsize=(12, 7.6), gridspec_kw={\"width_ratios\": [1.25, 1]})", "newString": "    print(f\"{u:<5} {k:<34} {_f(a):>22} {_f(b):>22}\")\n''')\n\nmd(r'''\n**Summary figure.**\n\n* **Left**: the raw per-prompt fork margins, which are the data every share is computed from: the two anchors (instruct\n  `m_I`, base `m_B`) and three patched instruct runs. Above 0 the default algorithm class is more likely, below 0 the\n  alternative.\n* **Right**: the shares that enter the committed rules, with their 95 % bootstrap CIs. The grey band is the central\n  90 % of the matched random sets.\n''')\n\ncode(r'''\nfig, axes = plt.subplots(2, 2, figsize=(12, 8.4), gridspec_kw={\"width_ratios\": [1.25, 1]})", "originalFile": null, "structuredPatch": [{"oldStart": 1308, "oldLines": 8, "newStart": 1308, "newLines": 18, "lines": ["     print(f\"{u:<5} {k:<34} {_f(a):>22} {_f(b):>22}\")", " ''')", " ", "+md(r'''", "+**Summary figure.**", "+", "+* **Left**: the raw per-prompt fork margins, which are the data every share is computed from: the two anchors (instruct", "+  `m_I`, base `m_B`) and three patched instruct runs. Above 0 the default algorithm class is more likely, below 0 the", "+  alternative.", "+* **Right**: the shares that enter the committed rules, with their 95 % bootstrap CIs. The grey band is the central", "+  90 % of the matched random sets.", "+''')", "+", " code(r'''", "-fig, axes = plt.subplots(2, 2, figsize=(12, 7.6), gridspec_kw={\"width_ratios\": [1.25, 1]})", "+fig, axes = plt.subplots(2, 2, figsize=(12, 8.4), gridspec_kw={\"width_ratios\": [1.25, 1]})", " for row, u in enumerate(UNITS):", "     r = b2s[\"units\"][u]", "     pids, by, mI, mB = rows_by_arm(u)"]}], "userModified": false, "replaceAll": false}
```

### [117] TOOL RESULT — Edit · 2026-10-26 14:46:45 UTC

```
{"filePath": "/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/make_nb.py", "oldString": "    ax.axhline(0, color=\"k\", lw=0.6)\n    ax.set_xticks(x)\n    ax.set_xticklabels(pids, rotation=70, fontsize=6)\n    ax.set_ylabel(\"fork margin m = log P(D) - log P(A)\")\n    U = UNITS_DATA[u]\n    ax.set_title(f\"{u} ({U['name']}): D = {U['D_class']} {U['D_tokens'][:2]}, A = {U['A_class']} {U['A_tokens'][:2]}\",\n                 fontsize=8.5)\n    ax.legend(fontsize=6.5, ncol=2, loc=\"best\")", "newString": "    ax.axhline(0, color=\"k\", lw=0.6)\n    ax.set_xticks(x)\n    ax.set_xticklabels(pids, rotation=70, fontsize=6)\n    ax.set_ylabel(\"fork margin m = log P(D) - log P(A)\")\n    U = UNITS_DATA[u]\n    ax.set_title(f\"{u} ({U['name']}): D = {U['D_class']} {U['D_tokens'][:2]}, A = {U['A_class']} {U['A_tokens'][:2]}\",\n                 fontsize=8.5)\n    y0, y1 = ax.get_ylim()\n    ax.set_ylim(y0, y1 + 0.42 * (y1 - y0))          # head room for the legend\n    ax.legend(fontsize=6.5, ncol=3, loc=\"upper center\")", "originalFile": null, "structuredPatch": [{"oldStart": 1340, "oldLines": 7, "newStart": 1340, "newLines": 9, "lines": ["     U = UNITS_DATA[u]", "     ax.set_title(f\"{u} ({U['name']}): D = {U['D_class']} {U['D_tokens'][:2]}, A = {U['A_class']} {U['A_tokens'][:2]}\",", "                  fontsize=8.5)", "-    ax.legend(fontsize=6.5, ncol=2, loc=\"best\")", "+    y0, y1 = ax.get_ylim()", "+    ax.set_ylim(y0, y1 + 0.42 * (y1 - y0))          # head room for the legend", "+    ax.legend(fontsize=6.5, ncol=3, loc=\"upper center\")", "     # (right) the shares that decide the verdict, with bootstrap CIs, against the random null", "     ax = axes[row, 1]", "     names = [\"FSTACK\", \"F_MLP\", \"F_HEAD\", \"SPEC\", \"W_all\"]"]}], "userModified": false, "replaceAll": false}
```

### [118] TOOL CALL — Edit · 2026-10-26 14:46:45 UTC

```
File: /tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/make_nb.py
OLD:     ax.set_title(f"{u}: FSTACK {r['arms']['FSTACK']['share']:.2f} vs random p = {nr['empirical_p_upper']:.3f}; "
                 f"Q1 {r['Q1']}, Q2 {r['Q2']}, Q3 {r['Q3']}", fontsize=8.5)
    ax.legend(fontsize=6.3, loc="lower right")
NEW:     ax.set_title(f"{u}: FSTACK {r['arms']['FSTACK']['share']:.2f} vs random p = {nr['empirical_p_upper']:.3f}; "
                 f"Q1 {r['Q1']}, Q2 {r['Q2']}, Q3 {r['Q3']}", fontsize=8.5)
    ax.legend(fontsize=6.3, loc="upper center", bbox_to_anchor=(0.45, -0.17), ncol=2)
```

### [119] TOOL RESULT — Edit · 2026-10-26 14:46:45 UTC

```
{"filePath": "/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/make_nb.py", "oldString": "    ax.set_title(f\"{u}: FSTACK {r['arms']['FSTACK']['share']:.2f} vs random p = {nr['empirical_p_upper']:.3f}; \"\n                 f\"Q1 {r['Q1']}, Q2 {r['Q2']}, Q3 {r['Q3']}\", fontsize=8.5)\n    ax.legend(fontsize=6.3, loc=\"lower right\")", "newString": "    ax.set_title(f\"{u}: FSTACK {r['arms']['FSTACK']['share']:.2f} vs random p = {nr['empirical_p_upper']:.3f}; \"\n                 f\"Q1 {r['Q1']}, Q2 {r['Q2']}, Q3 {r['Q3']}\", fontsize=8.5)\n    ax.legend(fontsize=6.3, loc=\"upper center\", bbox_to_anchor=(0.45, -0.17), ncol=2)", "originalFile": null, "structuredPatch": [{"oldStart": 1365, "oldLines": 7, "newStart": 1365, "newLines": 7, "lines": ["     ax.set_xlabel(\"share of the instruct-base gap closed\")", "     ax.set_title(f\"{u}: FSTACK {r['arms']['FSTACK']['share']:.2f} vs random p = {nr['empirical_p_upper']:.3f}; \"", "                  f\"Q1 {r['Q1']}, Q2 {r['Q2']}, Q3 {r['Q3']}\", fontsize=8.5)", "-    ax.legend(fontsize=6.3, loc=\"lower right\")", "+    ax.legend(fontsize=6.3, loc=\"upper center\", bbox_to_anchor=(0.45, -0.17), ncol=2)", " fig.suptitle(f\"B2 verdict {b2s['verdict']} (localisation: {b2s['units']['B3']['localisation']} / \"", "              f\"{b2s['units']['T10']['localisation']}); * = carried from the original CPU readout analysis\", fontsize=9)", " fig.tight_layout()"]}], "userModified": false, "replaceAll": false}
```

### [120] TOOL CALL — Edit · 2026-10-26 14:46:45 UTC

```
File: /tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/make_nb.py
OLD: ### What the numbers say

* **The instruct model is sharper at the fork, and the sharpening is not upstream.** The base model often prefers the
  alternative (Prim / DFS), while the tuned model is confidently on Kruskal / union-find. Patching the
  task-specification nodes (SPEC ≈ 0) or swapping the residual stream at earlier positions (RS-prefix(23) < 0.5) does
  not close the gap. The decision is made late, at the fork itself.
* **MST (B3): the 10 fork-stack nodes close all of the gap, but so does almost any matched late set.** The median
  write-norm-matched random late set closes about 0.8 of the gap (p = 0.45), several single late MLPs (L35, L28, L29,
  L26) each close about half, and FSTACK's joint share is about half the sum of its singles. The late MLPs (layers
  26-35) therefore carry the sharpening **redundantly**, which is not a specific circuit (Q2 fails).
* **Connected components (T10): FSTACK is specific but only partial** (0.45 vs a random median of −0.22, p = 0.020).
  Most of the CC gap is not in the residual stream at all: reading the base model's own final residual with the
  **tuned unembedding** already reproduces 85 % of it. This is also why RS-fork(36), which swaps the entire final
  residual, closes only 0.15.
* The geometry plot shows the same picture in activation space. The FSTACK and median-random patches move the
  block-30 state by similar amounts and largely in the same direction, and the margin falls as the state moves away
  from the instruct cluster.
* Committed verdict: **PARTIAL**. Q1 fails on CC, Q2 fails on MST, Q3 holds; localisation is "distributed".

For the run's question about the *mean answer*: tuning does not install a dedicated "pick Kruskal" circuit upstream. It
sharpens the readout of an already-present preference, partly in many redundant late MLPs and partly in the
unembedding itself. The original run also showed that a one-token patch at the fork can flip the written program, so
the minority algorithm is still there, but a matched random late patch flips it just as often (19/30 Prim for both
on MST).
NEW: ### What the numbers say (original configuration: 20 prompts per unit)

* **The tuned model is decided where its base is not.** At the MST fork the base model leans to Prim
  (`m_B` from −0.85 to −0.6) and the instruct model to Kruskal (`m_I` from 1.0 to 1.85). At the connected-components
  fork the base model is indifferent (`m_B` ≈ 0) and the instruct model prefers `find` by 0.2 to 9 nats.
* **Not written upstream.** The task-specification nodes close nothing (SPEC ≈ 0). Swapping the whole residual stream at
  all earlier positions (RS-prefix(23) = 0.44 / 0.37) stays below the committed 0.5 "written upstream" threshold. The
  sharpening is mostly computed at the fork itself: the fork-only swap RS-fork(l) is ≈ 0 up to layer 20 and peaks in
  layers 24-31 (F4).
* **MST (B3): many late MLPs carry it redundantly.**
  * FSTACK closes the whole gap (1.00 [0.96, 1.04]), but the median write-norm-matched random late set closes 0.81
    (p = 0.45).
  * Single late MLPs close a lot on their own (L35 0.98, L28 0.62, L29 0.56, L26 0.52), and FSTACK's joint share is
    half the sum of its singles (1.00 vs 1.96).
  * Base values taken from a *different* prompt work as well as the matched ones (`xprompt_FSTACK` 1.00).
  * So what FSTACK transplants is a generic, prompt-independent base-vs-tuned offset of the late MLPs rather than a
    specific circuit. Q2 fails.
* **Connected components (T10): specific but partial.** FSTACK closes 0.45 [0.28, 0.57] against a random median of
  −0.22 (p = 0.020). Most of the CC gap is not in the residual stream at all: reading the base model's own final
  residual with the **tuned unembedding** reproduces 85 % of it. This is why RS-fork(36), which swaps the entire final
  residual, closes only 0.15.
* **Activation space (Section 8).**
  * FSTACK moves the block-30 state the furthest (≈ 175 / 230 L2 against a state norm of ≈ 600).
  * The median random set moves it about 60 % as far and only partly in the same direction (cosine ≈ 0.5), and
    RS-fork(23) moves it elsewhere again.
  * On MST all three still push the margin to the Prim side (blue points): quite different late perturbations reach
    the same decision, which is the geometric face of the non-specificity found by the null test. On CC the
    random-patched states keep a high margin (red ×).
* **Committed verdict: PARTIAL.** Q1 fails on CC, Q2 fails on MST, Q3 holds; localisation is "distributed".

For the run's question about the *mean answer*: tuning does not add a dedicated "choose Kruskal" step upstream, at the
task statement. It sharpens the readout of a preference the base model only weakly has, or does not have. That
sharpening sits partly in a redundant late-MLP offset and partly in the unembedding itself. The minority algorithm is
still there to be found. In the original run's generation test, a one-token patch at the fork flipped 19/30 MST
programs to Prim, but a matched random late patch did the same (19/30). On CC only replacing the whole fork
distribution with the base model's brought DFS back (18/30).
```

### [121] TOOL RESULT — Edit · 2026-10-26 14:46:45 UTC

```
{"filePath": "/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/make_nb.py", "oldString": "### What the numbers say\n\n* **The instruct model is sharper at the fork, and the sharpening is not upstream.** The base model often prefers the\n  alternative (Prim / DFS), while the tuned model is confidently on Kruskal / union-find. Patching the\n  task-specification nodes (SPEC ≈ 0) or swapping the residual stream at earlier positions (RS-prefix(23) < 0.5) does\n  not close the gap. The decision is made late, at the fork itself.\n* **MST (B3): the 10 fork-stack nodes close all of the gap, but so does almost any matched late set.** The median\n  write-norm-matched random late set closes about 0.8 of the gap (p = 0.45), several single late MLPs (L35, L28, L29,\n  L26) each close about half, and FSTACK's joint share is about half the sum of its singles. The late MLPs (layers\n  26-35) therefore carry the sharpening **redundantly**, which is not a specific circuit (Q2 fails).\n* **Connected components (T10): FSTACK is specific but only partial** (0.45 vs a random median of −0.22, p = 0.020).\n  Most of the CC gap is not in the residual stream at all: reading the base model's own final residual with the\n  **tuned unembedding** already reproduces 85 % of it. This is also why RS-fork(36), which swaps the entire final\n  residual, closes only 0.15.\n* The geometry plot shows the same picture in activation space. The FSTACK and median-random patches move the\n  block-30 state by similar amounts and largely in the same direction, and the margin falls as the state moves away\n  from the instruct cluster.\n* Committed verdict: **PARTIAL**. Q1 fails on CC, Q2 fails on MST, Q3 holds; localisation is \"distributed\".\n\nFor the run's question about the *mean answer*: tuning does not install a dedicated \"pick Kruskal\" circuit upstream. It\nsharpens the readout of an already-present preference, partly in many redundant late MLPs and partly in the\nunembedding itself. The original run also showed that a one-token patch at the fork can flip the written program, so\nthe minority algorithm is still there, but a matched random late patch flips it just as often (19/30 Prim for both\non MST).", "newString": "### What the numbers say (original configuration: 20 prompts per unit)\n\n* **The tuned model is decided where its base is not.** At the MST fork the base model leans to Prim\n  (`m_B` from −0.85 to −0.6) and the instruct model to Kruskal (`m_I` from 1.0 to 1.85). At the connected-components\n  fork the base model is indifferent (`m_B` ≈ 0) and the instruct model prefers `find` by 0.2 to 9 nats.\n* **Not written upstream.** The task-specification nodes close nothing (SPEC ≈ 0). Swapping the whole residual stream at\n  all earlier positions (RS-prefix(23) = 0.44 / 0.37) stays below the committed 0.5 \"written upstream\" threshold. The\n  sharpening is mostly computed at the fork itself: the fork-only swap RS-fork(l) is ≈ 0 up to layer 20 and peaks in\n  layers 24-31 (F4).\n* **MST (B3): many late MLPs carry it redundantly.**\n  * FSTACK closes the whole gap (1.00 [0.96, 1.04]), but the median write-norm-matched random late set closes 0.81\n    (p = 0.45).\n  * Single late MLPs close a lot on their own (L35 0.98, L28 0.62, L29 0.56, L26 0.52), and FSTACK's joint share is\n    half the sum of its singles (1.00 vs 1.96).\n  * Base values taken from a *different* prompt work as well as the matched ones (`xprompt_FSTACK` 1.00).\n  * So what FSTACK transplants is a generic, prompt-independent base-vs-tuned offset of the late MLPs rather than a\n    specific circuit. Q2 fails.\n* **Connected components (T10): specific but partial.** FSTACK closes 0.45 [0.28, 0.57] against a random median of\n  −0.22 (p = 0.020). Most of the CC gap is not in the residual stream at all: reading the base model's own final\n  residual with the **tuned unembedding** reproduces 85 % of it. This is why RS-fork(36), which swaps the entire final\n  residual, closes only 0.15.\n* **Activation space (Section 8).**\n  * FSTACK moves the block-30 state the furthest (≈ 175 / 230 L2 against a state norm of ≈ 600).\n  * The median random set moves it about 60 % as far and only partly in the same direction (cosine ≈ 0.5), and\n    RS-fork(23) moves it elsewhere again.\n  * On MST all three still push the margin to the Prim side (blue points): quite different late perturbations reach\n    the same decision, which is the geometric face of the non-specificity found by the null test. On CC the\n    random-patched states keep a high margin (red ×).\n* **Committed verdict: PARTIAL.** Q1 fails on CC, Q2 fails on MST, Q3 holds; localisation is \"distributed\".\n\nFor the run's question about the *mean answer*: tuning does not add a dedicated \"choose Kruskal\" step upstream, at the\ntask statement. It sharpens the readout of a preference the base model only weakly has, or does not have. That\nsharpening sits partly in a redundant late-MLP offset and partly in the unembedding itself. The minority algorithm is\nstill there to be found. In the original run's generation test, a one-token patch at the fork flipped 19/30 MST\nprograms to Prim, but a matched random late patch did the same (19/30). On CC only replacing the whole fork\ndistribution with the base model's brought DFS back (18/30).", "originalFile": null, "structuredPatch": [{"oldStart": 1374, "oldLines": 30, "newStart": 1374, "newLines": 42, "lines": [" ''')", " ", " md(r'''", "-### What the numbers say", "+### What the numbers say (original configuration: 20 prompts per unit)", " ", "-* **The instruct model is sharper at the fork, and the sharpening is not upstream.** The base model often prefers the", "-  alternative (Prim / DFS), while the tuned model is confidently on Kruskal / union-find. Patching the", "-  task-specification nodes (SPEC ≈ 0) or swapping the residual stream at earlier positions (RS-prefix(23) < 0.5) does", "-  not close the gap. The decision is made late, at the fork itself.", "-* **MST (B3): the 10 fork-stack nodes close all of the gap, but so does almost any matched late set.** The median", "-  write-norm-matched random late set closes about 0.8 of the gap (p = 0.45), several single late MLPs (L35, L28, L29,", "-  L26) each close about half, and FSTACK's joint share is about half the sum of its singles. The late MLPs (layers", "-  26-35) therefore carry the sharpening **redundantly**, which is not a specific circuit (Q2 fails).", "-* **Connected components (T10): FSTACK is specific but only partial** (0.45 vs a random median of −0.22, p = 0.020).", "-  Most of the CC gap is not in the residual stream at all: reading the base model's own final residual with the", "-  **tuned unembedding** already reproduces 85 % of it. This is also why RS-fork(36), which swaps the entire final", "+* **The tuned model is decided where its base is not.** At the MST fork the base model leans to Prim", "+  (`m_B` from −0.85 to −0.6) and the instruct model to Kruskal (`m_I` from 1.0 to 1.85). At the connected-components", "+  fork the base model is indifferent (`m_B` ≈ 0) and the instruct model prefers `find` by 0.2 to 9 nats.", "+* **Not written upstream.** The task-specification nodes close nothing (SPEC ≈ 0). Swapping the whole residual stream at", "+  all earlier positions (RS-prefix(23) = 0.44 / 0.37) stays below the committed 0.5 \"written upstream\" threshold. The", "+  sharpening is mostly computed at the fork itself: the fork-only swap RS-fork(l) is ≈ 0 up to layer 20 and peaks in", "+  layers 24-31 (F4).", "+* **MST (B3): many late MLPs carry it redundantly.**", "+  * FSTACK closes the whole gap (1.00 [0.96, 1.04]), but the median write-norm-matched random late set closes 0.81", "+    (p = 0.45).", "+  * Single late MLPs close a lot on their own (L35 0.98, L28 0.62, L29 0.56, L26 0.52), and FSTACK's joint share is", "+    half the sum of its singles (1.00 vs 1.96).", "+  * Base values taken from a *different* prompt work as well as the matched ones (`xprompt_FSTACK` 1.00).", "+  * So what FSTACK transplants is a generic, prompt-independent base-vs-tuned offset of the late MLPs rather than a", "+    specific circuit. Q2 fails.", "+* **Connected components (T10): specific but partial.** FSTACK closes 0.45 [0.28, 0.57] against a random median of", "+  −0.22 (p = 0.020). Most of the CC gap is not in the residual stream at all: reading the base model's own final", "+  residual with the **tuned unembedding** reproduces 85 % of it. This is why RS-fork(36), which swaps the entire final", "   residual, closes only 0.15.", "-* The geometry plot shows the same picture in activation space. The FSTACK and median-random patches move the", "-  block-30 state by similar amounts and largely in the same direction, and the margin falls as the state moves away", "-  from the instruct cluster.", "-* Committed verdict: **PARTIAL**. Q1 fails on CC, Q2 fails on MST, Q3 holds; localisation is \"distributed\".", "+* **Activation space (Section 8).**", "+  * FSTACK moves the block-30 state the furthest (≈ 175 / 230 L2 against a state norm of ≈ 600).", "+  * The median random set moves it about 60 % as far and only partly in the same direction (cosine ≈ 0.5), and", "+    RS-fork(23) moves it elsewhere again.", "+  * On MST all three still push the margin to the Prim side (blue points): quite different late perturbations reach", "+    the same decision, which is the geometric face of the non-specificity found by the null test. On CC the", "+    random-patched states keep a high margin (red ×).", "+* **Committed verdict: PARTIAL.** Q1 fails on CC, Q2 fails on MST, Q3 holds; localisation is \"distributed\".", " ", "-For the run's question about the *mean answer*: tuning does not install a dedicated \"pick Kruskal\" circuit upstream. It", "-sharpens the readout of an already-present preference, partly in many redundant late MLPs and partly in the", "-unembedding itself. The original run also showed that a one-token patch at the fork can flip the written program, so", "-the minority algorithm is still there, but a matched random late patch flips it just as often (19/30 Prim for both", "-on MST).", "+For the run's question about the *mean answer*: tuning does not add a dedicated \"choose Kruskal\" step upstream, at the", "+task statement. It sharpens the readout of a preference the base model only weakly has, or does not have. That", "+sharpening sits partly in a redundant late-MLP offset and partly in the unembedding itself. The minority algorithm is", "+still there to be found. In the original run's generation test, a one-token patch at the fork flipped 19/30 MST", "+programs to Prim, but a matched random late patch did the same (19/30). On CC only replacing the whole fork", "+distribution with the base model's brought DFS back (18/30).", " ", " **Running the full pipeline** (needs a 24 GB GPU, `HF_TOKEN` with access to Gemma 3 and Llama 3.1, about 65 GB of", " weights and about 1 GPU-hour), from the artifact folder of the repository:"]}], "userModified": false, "replaceAll": false}
```

### [122] ASSISTANT · 2026-10-26 14:47:03 UTC

```
I'll correct one more claim: on T10 the RS-fork curve is not ≈ 0 up to layer 20 (there is a 0.5 bump at layers 17-18). Then I'll generate the notebook in the workspace at minimum config.
```

### [123] TOOL CALL — Edit · 2026-10-26 14:47:03 UTC

```
File: /tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/make_nb.py
OLD:   sharpening is mostly computed at the fork itself: the fork-only swap RS-fork(l) is ≈ 0 up to layer 20 and peaks in
  layers 24-31 (F4).
NEW:   sharpening is mostly computed at the fork itself. The fork-only swap RS-fork(l) is near 0 through layer 15 and largest
  in the late layers (F4): on MST it peaks at 1.49 at layer 28; on CC it reaches 0.5-0.55 at layers 17-18 and 31-34.
```

### [124] TOOL RESULT — Edit · 2026-10-26 14:47:03 UTC

```
{"filePath": "/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/make_nb.py", "oldString": "  sharpening is mostly computed at the fork itself: the fork-only swap RS-fork(l) is ≈ 0 up to layer 20 and peaks in\n  layers 24-31 (F4).", "newString": "  sharpening is mostly computed at the fork itself. The fork-only swap RS-fork(l) is near 0 through layer 15 and largest\n  in the late layers (F4): on MST it peaks at 1.49 at layer 28; on CC it reaches 0.5-0.55 at layers 17-18 and 31-34.", "originalFile": null, "structuredPatch": [{"oldStart": 1381, "oldLines": 8, "newStart": 1381, "newLines": 8, "lines": ["   fork the base model is indifferent (`m_B` ≈ 0) and the instruct model prefers `find` by 0.2 to 9 nats.", " * **Not written upstream.** The task-specification nodes close nothing (SPEC ≈ 0). Swapping the whole residual stream at", "   all earlier positions (RS-prefix(23) = 0.44 / 0.37) stays below the committed 0.5 \"written upstream\" threshold. The", "-  sharpening is mostly computed at the fork itself: the fork-only swap RS-fork(l) is ≈ 0 up to layer 20 and peaks in", "-  layers 24-31 (F4).", "+  sharpening is mostly computed at the fork itself. The fork-only swap RS-fork(l) is near 0 through layer 15 and largest", "+  in the late layers (F4): on MST it peaks at 1.49 at layer 28; on CC it reaches 0.5-0.55 at layers 17-18 and 31-34.", " * **MST (B3): many late MLPs carry it redundantly.**", "   * FSTACK closes the whole gap (1.00 [0.96, 1.04]), but the median write-norm-matched random late set closes 0.81", "     (p = 0.45)."]}], "userModified": false, "replaceAll": false}
```

### [125] TOOL CALL — Bash · 2026-10-26 14:47:03 UTC

```
Generate workspace notebook and check cell structure:
SP="/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad"; W=/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd; cd "$SP" && python3 make_nb.py "$W/code_demo.ipynb" "$SP/proto/proto.py" && python3 -c "
import json; nb=json.load(open('$W/code_demo.ipynb'))
types=[c['cell_type'] for c in nb['cells']]
print(len(types), 'cells'); 
# check: every code cell (after the first 5 setup cells) is preceded by a markdown cell
bad=[i for i,t in enumerate(types) if t=='code' and i>5 and types[i-1]!='markdown']
print('code cells not preceded by markdown (after setup):', bad)
print(''.join(types[i][0] for i in range(len(types))))
"
```

### [126] TOOL RESULT — Bash · 2026-10-26 14:47:03 UTC

```
{"stdout": "wrote /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd/code_demo.ipynb with 40 cells (21 code)\nwrote /tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/proto/proto.py\n40 cells\ncode cells not preceded by markdown (after setup): []\nmccccmcmcmcmcmcmcmcmcmcmcmcmcmcmcmcmcmcm", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [127] ASSISTANT · 2026-10-26 14:47:17 UTC

```
The structure is right: the five setup cells, then a markdown cell before every code cell. Next is TODO 4's test, run with the exact commands given in the clean venv at minimum config.
```

### [128] TOOL CALL — Bash · 2026-10-26 14:47:17 UTC

```
Test-run notebook in clean venv at minimum config:
start=$(date +%s) && UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_cDba8_DycUJd-e339753424ba && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_cDba8_DycUJd-e339753424ba/bin/python jupyter ipykernel && echo "env ready in $(( $(date +%s) - start ))s" && t1=$(date +%s) && /tmp/aii_nb_test_envs/art_cDba8_DycUJd-e339753424ba/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | tail -15; echo "nbconvert exit ${PIPESTATUS[0]} in $(( $(date +%s) - t1 ))s"
```

### [129] TOOL RESULT — Bash · 2026-10-26 14:47:37 UTC

```
{"stdout": "env ready in 5s\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[IPKernelApp] WARNING | Kernel is running over TCP without encryption. All communication (including code and outputs) is sent in plain text and is susceptible to eavesdropping. Use IPC transport or launch with kernel manager-provisioned CurveZMQ keys to enable transport encryption.\n[NbConvertApp] Writing 632649 bytes to code_demo.ipynb\nnbconvert exit 0 in 18s", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [130] ASSISTANT · 2026-10-26 14:47:43 UTC

```
The minimum-config notebook executed cleanly in the fresh venv in 18 s, installs included. Next I'll check every cell's outputs for errors, stderr noise and rendered figures.
```

### [131] TOOL CALL — Bash · 2026-10-26 14:47:43 UTC

```
Inspect executed notebook outputs for errors:
python3 - <<'EOF'
import json
nb=json.load(open('code_demo.ipynb'))
for i,c in enumerate(nb['cells']):
    if c['cell_type']!='code': continue
    kinds=[]
    for o in c.get('outputs',[]):
        if o['output_type']=='stream':
            kinds.append(f"{o['name']}:{len(''.join(o['text']))}ch")
            if o['name']=='stderr': print(f'--- cell {i} STDERR:', ''.join(o['text'])[:600])
        elif o['output_type']=='error':
            print(f'--- cell {i} ERROR', o['ename'], o['evalue'])
        else:
            kinds.append(o['output_type']+':'+','.join(k for k in o.get('data',{})))
    print(i, c['execution_count'], kinds, '|', c['source'][0][:70].rstrip())
EOF
```

### [132] TOOL RESULT — Bash · 2026-10-26 14:47:43 UTC

```
{"stdout": "1 1 [] | import subprocess, sys\n2 2 [] | from __future__ import annotations\n3 3 [] | GITHUB_DATA_URL = \"https://raw.githubusercontent.com/ai-inventor-paper\n4 4 ['stdout:985ch'] | data = load_data()\n6 5 [] | N_PROMPTS_PER_UNIT = 2      # prompts per unit taken from the data (or\n8 6 ['stdout:994ch'] | STAGES: dict[str, list[list[str]]] = {\n10 7 [] | ROOT = Path.cwd()                     # notebook: the working director\n12 8 [] | def js_div(ia: list[int], la: list[float], ib: list[int], lb: list[flo\n14 9 ['stdout:357ch'] | UNITS_DATA = M[\"units\"]\n16 10 [] | def parse(k: str) -> tuple[str, int, int]:\n18 11 ['stdout:2060ch'] | # rerun the draws exactly as cmap9.base_stage_extras (R, R-pure) and c\n20 12 [] | UNITS = (\"B3\", \"T10\")\n22 13 [] | def b2_unit(u: str, ui: int) -> dict[str, Any]:\n24 14 ['stdout:218ch', 'stdout:1534ch'] | setup_logging(\"analysis9\")\n26 15 [] | plt.rcParams.update({\"font.size\": 9, \"axes.spines.top\": False, \"axes.s\n28 16 ['display_data:image/png,text/plain', 'stdout:47ch', 'display_data:image/png,text/plain', 'stdout:45ch', 'display_data:image/png,text/plain', 'stdout:42ch'] | setup_logging(\"figures9\")\n--- cell 30 STDERR: /tmp/ipykernel_563/2451970436.py:43: UserWarning: You passed a edgecolor/edgecolors ('k') for an unfilled marker ('x').  Matplotlib is ignoring the edgecolor in favor of the facecolor.  This behavior may change in the future.\n  sc = ax.scatter(Y[ii, 0], Y[ii, 1], c=[cols[i] for i in ii], cmap=\"coolwarm\", marker=mk, s=28,\n\n30 17 ['stderr:323ch', 'display_data:image/png,text/plain', 'stdout:48ch', 'stdout:635ch'] | def bf16_from_b64(s: str) -> np.ndarray:\n32 18 [] | RES = RESULTS_DIR\n34 19 ['stdout:382ch'] | mism: list[str] = []\n36 20 ['stdout:3219ch'] | b2s = read_json(RESULTS_DIR / \"b2_summary.json\")\n38 21 ['display_data:image/png,text/plain'] | fig, axes = plt.subplots(2, 2, figsize=(12, 8.4), gridspec_kw={\"width_", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [133] THINKING · 2026-10-26 14:48:05 UTC

```
All cells ran successfully, with only a benign matplotlib warning from the original F8 scatter code—TODO 4 is done. Next, for TODO 5 I'll scale the config in two NotebookEdit passes (small test values, then original values), clearing outputs first to keep images out of the context.
```

### [134] TOOL CALL — Bash · 2026-10-26 14:48:05 UTC

```
Record round 0 and clear notebook outputs:
SP="/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad"; sed -i 's/^- \[ \] TODO 4\./- [x] TODO 4./' "$SP/todos.md"; echo "round0 (min: 2 prompts, N_BOOT 10, N_RAND 2, N_RAND_SPEC 2, N_PLACEBO 2): nbconvert 18s incl. installs, pass" >> "$SP/scaling_log.txt"; cd /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd && /tmp/aii_nb_test_envs/art_cDba8_DycUJd-e339753424ba/bin/jupyter nbconvert --clear-output --inplace code_demo.ipynb 2>&1 | tail -1; ls -la code_demo.ipynb
```

### [135] TOOL RESULT — Bash · 2026-10-26 14:48:07 UTC

```
{"stdout": "[NbConvertApp] Writing 94699 bytes to code_demo.ipynb\n-rw-rw-rw- 1 aii-agent aii-agent 94761 Oct 26 14:48 code_demo.ipynb", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [136] TOOL CALL — Read · 2026-10-26 14:48:09 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd/code_demo.ipynb
```

### [137] TOOL RESULT — Read [ERROR] · 2026-10-26 14:48:11 UTC

```
Error: File content (38273 tokens) exceeds maximum allowed tokens (25000). Use offset and limit parameters to read specific portions of the file, or search for specific content instead of reading the whole file.
```

### [138] TOOL CALL — Read · 2026-10-26 14:48:15 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd/code_demo.ipynb
```

### [139] TOOL RESULT — Read [ERROR] · 2026-10-26 14:48:15 UTC

```
Error: File content (38273 tokens) exceeds maximum allowed tokens (25000). Use offset and limit parameters to read specific portions of the file, or search for specific content instead of reading the whole file.
```

### [140] TOOL CALL — Read · 2026-10-26 14:48:19 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd/code_demo.ipynb
```

### [141] TOOL RESULT — Read [ERROR] · 2026-10-26 14:48:19 UTC

```
Error: File content (38273 tokens) exceeds maximum allowed tokens (25000). Use offset and limit parameters to read specific portions of the file, or search for specific content instead of reading the whole file.
```

### [142] THINKING · 2026-10-26 14:48:41 UTC

```
The notebook is too large for the Read tool, and NotebookEdit requires a prior Read—so I'll write a small script to edit the config cell's source directly at the JSON level.
```

### [143] TOOL CALL — Write · 2026-10-26 14:48:41 UTC

```
File: /tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/set_config.py

#!/usr/bin/env python3
"""Set the values in code_demo.ipynb's configuration cell (the cell whose source starts with N_PROMPTS_PER_UNIT).
Usage: set_config.py <notebook> N_PROMPTS_PER_UNIT N_BOOT N_RAND N_RAND_SPEC N_PLACEBO_DRAWS"""

import json
import re
import sys

nb_path = sys.argv[1]
names = ("N_PROMPTS_PER_UNIT", "N_BOOT", "N_RAND", "N_RAND_SPEC", "N_PLACEBO_DRAWS")
vals = dict(zip(names, sys.argv[2:7]))
nb = json.load(open(nb_path))
cells = [c for c in nb["cells"] if c["cell_type"] == "code" and "".join(c["source"]).startswith("N_PROMPTS_PER_UNIT")]
assert len(cells) == 1, f"expected one config cell, found {len(cells)}"
src = "".join(cells[0]["source"])
for k, v in vals.items():
    src, n = re.subn(rf"^{k} = \S+( +)", lambda m: f"{k} = {v}".ljust(len(m.group(0))) if len(f"{k} = {v}") < len(m.group(0)) else f"{k} = {v} ", src, count=1, flags=re.M)
    assert n == 1, k
lines = src.split("\n")
cells[0]["source"] = [ln + "\n" for ln in lines[:-1]] + [lines[-1]]
with open(nb_path, "w") as fh:
    fh.write(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")
print(src)
```

### [144] TOOL RESULT — Write · 2026-10-26 14:48:41 UTC

```
{"type": "create", "filePath": "/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/set_config.py", "content": "#!/usr/bin/env python3\n\"\"\"Set the values in code_demo.ipynb's configuration cell (the cell whose source starts with N_PROMPTS_PER_UNIT).\nUsage: set_config.py <notebook> N_PROMPTS_PER_UNIT N_BOOT N_RAND N_RAND_SPEC N_PLACEBO_DRAWS\"\"\"\n\nimport json\nimport re\nimport sys\n\nnb_path = sys.argv[1]\nnames = (\"N_PROMPTS_PER_UNIT\", \"N_BOOT\", \"N_RAND\", \"N_RAND_SPEC\", \"N_PLACEBO_DRAWS\")\nvals = dict(zip(names, sys.argv[2:7]))\nnb = json.load(open(nb_path))\ncells = [c for c in nb[\"cells\"] if c[\"cell_type\"] == \"code\" and \"\".join(c[\"source\"]).startswith(\"N_PROMPTS_PER_UNIT\")]\nassert len(cells) == 1, f\"expected one config cell, found {len(cells)}\"\nsrc = \"\".join(cells[0][\"source\"])\nfor k, v in vals.items():\n    src, n = re.subn(rf\"^{k} = \\S+( +)\", lambda m: f\"{k} = {v}\".ljust(len(m.group(0))) if len(f\"{k} = {v}\") < len(m.group(0)) else f\"{k} = {v} \", src, count=1, flags=re.M)\n    assert n == 1, k\nlines = src.split(\"\\n\")\ncells[0][\"source\"] = [ln + \"\\n\" for ln in lines[:-1]] + [lines[-1]]\nwith open(nb_path, \"w\") as fh:\n    fh.write(json.dumps(nb, indent=1, ensure_ascii=False) + \"\\n\")\nprint(src)\n", "structuredPatch": [], "originalFile": null, "userModified": false}
```

### [145] TOOL CALL — Bash · 2026-10-26 14:48:41 UTC

```
Scaling round 1: set config and test-run notebook:
SP="/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad"; cd /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd && python3 "$SP/set_config.py" code_demo.ipynb 10 1000 25 10 100 && start=$(date +%s) && UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_cDba8_DycUJd-e339753424ba && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_cDba8_DycUJd-e339753424ba/bin/python jupyter ipykernel && t1=$(date +%s) && /tmp/aii_nb_test_envs/art_cDba8_DycUJd-e339753424ba/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | grep -v "TCP without encryption" | tail -5; echo "nbconvert exit ${PIPESTATUS[0]} in $(( $(date +%s) - t1 ))s"; python3 - <<'EOF'
import json
nb=json.load(open('code_demo.ipynb'))
err=[(i,o['ename'],o['evalue']) for i,c in enumerate(nb['cells']) if c['cell_type']=='code' for o in c.get('outputs',[]) if o['output_type']=='error']
print('errors:', err)
for i,c in enumerate(nb['cells']):
    s=''.join(c['source'])
    if c['cell_type']=='code' and (s.startswith('setup_logging("analysis9")') or s.startswith('mism:')):
        print(''.join(''.join(o.get('text','')) for o in c['outputs'] if o['output_type']=='stream')[-1500:])
EOF
```

### [146] TOOL RESULT — Bash · 2026-10-26 14:48:53 UTC

```
{"stdout": "N_PROMPTS_PER_UNIT = 10     # prompts per unit taken from the data (original: 20 = all; minimum 2)\nN_BOOT = 1000               # bootstrap resamples per CI, cfg9.N_BOOT (original: 10000; minimum 10)\nN_RAND = 25                 # matched random component sets per null R / R-pure / R-scaled, cfg9.N_RAND (original: 50; minimum 2)\nN_RAND_SPEC = 10            # matched random SPEC sets, cfg9.N_RAND_SPEC (original: 20; minimum 2)\nN_PLACEBO_DRAWS = 100       # placebo draws in the stdlib re-derivation, rederive9.b2 (original: 200; minimum 2)\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[NbConvertApp] Writing 650899 bytes to code_demo.ipynb\nnbconvert exit 0 in 12s\nerrors: []\nit, N_BOOT = 1000\n\n[B3] minimum spanning tree weight: gap m_I - m_B = 2.07 nats [1.96 2.21]\n   share FSTACK       +1.033  95% CI [0.974 1.091]\n   share F_MLP        +1.105  95% CI [1.045 1.162]\n   share F_HEAD       +0.202  95% CI [0.156 0.249]\n   share SPEC         -0.080  95% CI [-0.129 -0.037]\n   share W_all        +0.226  95% CI [0.202 0.25 ]\n   share self_FSTACK  -0.002  95% CI [-0.019  0.012]\n   random sets R (n=25): median +0.801, p95 +1.404, empirical p(FSTACK) = 0.500\n   RS-fork(23) +0.781, RS-fork(36) +0.586, RS-prefix(23) +0.474; unembedding-only share (carried) 0.43\n   top singles: mlp|L35 0.95, mlp|L28 0.63, mlp|L29 0.55, mlp|L26 0.50, mlp|L27 0.49\n   Q1 True  Q2 False  Q3 True  localisation: distributed\n\n[T10] connected components: gap m_I - m_B = 4.38 nats [3.15 5.53]\n   share FSTACK       +0.455  95% CI [0.274 0.556]\n   share F_MLP        +0.413  95% CI [0.22  0.516]\n   share F_HEAD       +0.327  95% CI [0.27  0.419]\n   share SPEC         -0.224  95% CI [-0.541 -0.013]\n   share W_all        +0.393  95% CI [0.35  0.468]\n   share self_FSTACK  +0.004  95% CI [-0.003  0.013]\n   random sets R (n=25): median -0.235, p95 +0.042, empirical p(FSTACK) = 0.038\n   RS-fork(23) -0.069, RS-fork(36) +0.124, RS-prefix(23) +0.348; unembedding-only share (carried) 0.85\n   top singles: mlp|L30 0.57, mlp|L35 0.38, mlp|L34 0.27, head|L23|H10 0.25, mlp|L14 0.19\n   Q1 False  Q2 True  Q3 True  localisation: distributed\n\nB2 verdict: PARTIAL (Q1 both False, Q2 both False, Q3 both True)\n\nrederive: 0 mismatches\nB3: stdlib FSTACK share 1.032737, R median 0.800767, empirical p 0.5000 | placebo (permuted node labels) frac p<=0.05 = 0.030 -> fails as required: True; anchor-swap share -0.033\nT10: stdlib FSTACK share 0.455190, R median -0.234978, empirical p 0.0385 | placebo (permuted node labels) frac p<=0.05 = 0.040 -> fails as required: True; anchor-swap share +0.545", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [147] THINKING · 2026-10-26 14:49:09 UTC

```
Round 1 passed in 12s with no errors and the qualitative pattern matches expectations. Moving on to Round 2 with the full original values, which should run quickly given the 6s prototype timing.
```

### [148] TOOL CALL — Bash · 2026-10-26 14:49:09 UTC

```
Scaling round 2: original config test-run:
SP="/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad"; echo "round1 (10 prompts, N_BOOT 1000, N_RAND 25, N_RAND_SPEC 10, N_PLACEBO 100): nbconvert 12s, pass" >> "$SP/scaling_log.txt"; cd /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd && python3 "$SP/set_config.py" code_demo.ipynb 20 10000 50 20 200 && UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_cDba8_DycUJd-e339753424ba && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_cDba8_DycUJd-e339753424ba/bin/python jupyter ipykernel && t1=$(date +%s) && /tmp/aii_nb_test_envs/art_cDba8_DycUJd-e339753424ba/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | grep -v "TCP without encryption" | tail -5; echo "nbconvert exit ${PIPESTATUS[0]} in $(( $(date +%s) - t1 ))s"; python3 - <<'EOF'
import json
nb=json.load(open('code_demo.ipynb'))
err=[(i,o['ename'],o['evalue']) for i,c in enumerate(nb['cells']) if c['cell_type']=='code' for o in c.get('outputs',[]) if o['output_type']=='error']
print('errors:', err)
for i,c in enumerate(nb['cells']):
    s=''.join(c['source'])
    if c['cell_type']=='code' and (s.startswith('b2s = read_json') or s.startswith('mism:') or s.startswith('# rerun the draws') or s.startswith('def bf16_from_b64')):
        print(''.join(''.join(o.get('text','')) for o in c['outputs'] if o['output_type']=='stream')[:3500])
        print('=====')
EOF
```

### [149] TOOL RESULT — Bash · 2026-10-26 14:49:21 UTC

```
{"stdout": "N_PROMPTS_PER_UNIT = 20     # prompts per unit taken from the data (original: 20 = all; minimum 2)\nN_BOOT = 10000              # bootstrap resamples per CI, cfg9.N_BOOT (original: 10000; minimum 10)\nN_RAND = 50                 # matched random component sets per null R / R-pure / R-scaled, cfg9.N_RAND (original: 50; minimum 2)\nN_RAND_SPEC = 20            # matched random SPEC sets, cfg9.N_RAND_SPEC (original: 20; minimum 2)\nN_PLACEBO_DRAWS = 200       # placebo draws in the stdlib re-derivation, rederive9.b2 (original: 200; minimum 2)\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[NbConvertApp] Writing 676466 bytes to code_demo.ipynb\nnbconvert exit 0 in 14s\nerrors: []\nB3: re-drawn sets identical to the patched ones: R 50/50, R-pure 50/50, SPEC-R 20/20\n   FSTACK node    |delta| at fork    tolerance #candidates   R0 replacement\n   mlp|L26                  48.48   [0.5, 2.0]           5   mlp|L23 (|delta| 31.99)\n   mlp|L27                  63.18   [0.5, 2.0]           5   mlp|L31 (|delta| 114.76)\n   mlp|L28                  75.10   [0.5, 2.0]           5   mlp|L33 (|delta| 140.80)\n   mlp|L30                 100.94  [0.7, 1.43]           3   mlp|L29 (|delta| 93.70)\n   mlp|L32                 125.88  [0.7, 1.43]           4   mlp|L34 (|delta| 167.38)\n   head|L23|H10              7.19  [0.7, 1.43]          83   head|L34|H31 (|delta| 9.64)\n   head|L27|H31             14.20  [0.7, 1.43]          36   head|L27|H28 (|delta| 9.99)\n   head|L29|H6               9.75  [0.7, 1.43]          58   head|L34|H2 (|delta| 12.41)\n   head|L33|H14             12.16  [0.7, 1.43]          40   head|L35|H0 (|delta| 13.19)\n   head|L34|H28             40.37  [0.7, 1.43]           4   head|L34|H21 (|delta| 32.14)\nT10: re-drawn sets identical to the patched ones: R 50/50, R-pure 50/50, SPEC-R 20/20\n   FSTACK node    |delta| at fork    tolerance #candidates   R0 replacement\n   mlp|L26                  52.23   [0.5, 2.0]           4   mlp|L29 (|delta| 102.39)\n   mlp|L27                  73.34   [0.5, 2.0]           4   mlp|L31 (|delta| 133.77)\n   mlp|L28                  91.20   [0.5, 2.0]           3   mlp|L33 (|delta| 171.61)\n   mlp|L30                 129.55  [0.7, 1.43]           3   mlp|L33 (|delta| 171.61)\n   mlp|L32                 145.44  [0.7, 1.43]           3   mlp|L31 (|delta| 133.77)\n   head|L23|H10              7.60  [0.7, 1.43]          80   head|L27|H23 (|delta| 5.54)\n   head|L27|H31             11.50  [0.7, 1.43]          36   head|L28|H7 (|delta| 12.62)\n   head|L29|H6               6.03  [0.7, 1.43]         109   head|L35|H3 (|delta| 4.97)\n   head|L33|H14              7.13  [0.7, 1.43]          83   head|L27|H29 (|delta| 5.40)\n   head|L34|H28             24.13  [0.7, 1.43]          21   head|L32|H21 (|delta| 28.24)\n\n=====\n/tmp/ipykernel_746/2451970436.py:43: UserWarning: You passed a edgecolor/edgecolors ('k') for an unfilled marker ('x').  Matplotlib is ignoring the edgecolor in favor of the facecolor.  This behavior may change in the future.\n  sc = ax.scatter(Y[ii, 0], Y[ii, 1], c=[cols[i] for i in ii], cmap=\"coolwarm\", marker=mk, s=28,\n14:49:18|INFO   |figure F8_b2_geometry_pca_demo\nB3: mean |instruct state| = 643\n   FSTACK-patched           moves the state by  173.0 (L2), cosine with the FSTACK shift +1.00\n   median random-patched    moves the state by  102.2 (L2), cosine with the FSTACK shift +0.48\n   RS-fork(23)-patched      moves the state by  120.7 (L2), cosine with the FSTACK shift +0.43\nT10: mean |instruct state| = 574\n   FSTACK-patched           moves the state by  230.1 (L2), cosine with the FSTACK shift +1.00\n   median random-patched    moves the state by  129.5 (L2), cosine with the FSTACK shift +0.48\n   RS-fork(23)-patched      moves the state by  163.8 (L2), cosine with the FSTACK shift +0.62\n\n=====\nrederive: 0 mismatches\nB3: stdlib FSTACK share 0.997696, R median 0.807268, empirical p 0.4510 | placebo (permuted node labels) frac p<=0.05 = 0.030 -> fails as required: True; anchor-swap share +0.002\nT10: stdlib FSTACK share 0.451707, R median -0.223247, empirical p 0.0196 | placebo (permuted node labels) frac p<=0.05 = 0.055 -> fails as required: True; anchor-swap share +0.548\n\n=====\nunit  quantity                                    this notebook           original run\n--------------------------------------------------------------------------------------\nB3    prompts                                                20                     20\nB3    gap m_I - m_B (nats)                                2.059                  2.059\nB3    FSTACK share                                        0.998                  0.998\nB3    FSTACK share 95% CI                          [0.96, 1.04]           [0.96, 1.04]\nB3    F_MLP share                                         1.079                  1.079\nB3    F_HEAD share                                        0.174                  0.174\nB3    random sets R: median share                         0.807                  0.807\nB3    random sets R: 95th pct                             1.413                  1.413\nB3    empirical p (FSTACK vs R)                           0.451                  0.451\nB3    R-pure: median / p                           [0.66, 0.04]           [0.66, 0.04]\nB3    SPEC share                                         -0.019                 -0.019\nB3    RS-fork(23) / RS-fork(36)                    [0.78, 0.57]           [0.78, 0.57]\nB3    RS-prefix(23)                                       0.443                  0.443\nB3    unembedding-only share (carried)                    0.426                  0.426\nB3    REV: share opened by FSTACK                        -0.304                 -0.304\nB3    Q1 / Q2 / Q3                          True / False / True    True / False / True\nB3    localisation                                  distributed            distributed\nT10   prompts                                                20                     20\nT10   gap m_I - m_B (nats)                                4.519                  4.519\nT10   FSTACK share                                        0.452                  0.452\nT10   FSTACK share 95% CI                          [0.28, 0.57]           [0.28, 0.57]\nT10   F_MLP share                                         0.406                  0.406\nT10   F_HEAD share                                        0.302                  0.302\nT10   random sets R: median share                        -0.223                 -0.223\nT10   random sets R: 95th pct                             0.056                  0.056\nT10   empirical p (FSTACK vs R)                           0.020                  0.020\nT10   R-pure: median / p                          [-0.46, 0.02]          [-0.46, 0.02]\nT10   SPEC share                                         -0.167                 -0.167\nT10   RS-fork(23) / RS-fork(36)                   [-0.05, 0.15]          [-0.05, 0.15]\nT10   RS-prefix(23)                                       0.372                  0.372\nT10   unembedding-only share (carried)                    0.850                  0.850\nT10   REV: share opened by FSTACK                         0.223                  0.223\nT10   Q1 / Q2 / Q3                          False / True / True    False / True / True\nT10   localisation                                  distributed            distributed\nboth  B2 verdict                                        PARTIAL                PARTIAL\n\n=====", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [150] THINKING · 2026-10-26 14:49:31 UTC

```
Round 2 with the original configuration passed in 14s, well under budget, with no errors and matching results—so I'll keep the original values. Next, I'll check the rendered figures.
```

### [151] TOOL CALL — Read · 2026-10-26 14:49:31 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd/figures/summary_b2.png
```

### [152] TOOL RESULT — Read · 2026-10-26 14:49:32 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [153] TOOL CALL — Read · 2026-10-26 14:49:31 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd/figures/F3_b2_singles_by_layer.png
```

### [154] TOOL RESULT — Read · 2026-10-26 14:49:32 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [155] SYSTEM-USER prompt · 2026-10-26 14:49:31 UTC

```
[Image: original 2200x760, displayed at 2000x691. Multiply coordinates by 1.10 to map to original image.]
```

### [156] TOOL CALL — Read · 2026-10-26 14:49:31 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd/figures/F4_b2_residual_swaps.png
```

### [157] TOOL RESULT — Read · 2026-10-26 14:49:32 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [158] SYSTEM-USER prompt · 2026-10-26 14:49:32 UTC

```
[Image: original 2200x760, displayed at 2000x691. Multiply coordinates by 1.10 to map to original image.]
```

### [159] TOOL CALL — Read · 2026-10-26 14:49:32 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd/figures/F5_b2_random_null.png
```

### [160] TOOL RESULT — Read · 2026-10-26 14:49:32 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [161] THINKING · 2026-10-26 14:51:00 UTC

```
All four figures render cleanly now, and F4 reveals that early-layer prefix swaps (8-16) close up to 1.2 of the MST gap while only layer 23 triggers the committed rule—I'll update the text to reflect this and make the anchor-swap placebo description concrete. Then I'll reset the generator's config defaults, regenerate, and run the final test so the delivered notebook includes outputs.
```

### [162] TOOL CALL — Edit · 2026-10-26 14:51:00 UTC

```
File: /tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/make_nb.py
OLD: * **Not written upstream.** The task-specification nodes close nothing (SPEC ≈ 0). Swapping the whole residual stream at
  all earlier positions (RS-prefix(23) = 0.44 / 0.37) stays below the committed 0.5 "written upstream" threshold. The
  sharpening is mostly computed at the fork itself. The fork-only swap RS-fork(l) is near 0 through layer 15 and largest
  in the late layers (F4): on MST it peaks at 1.49 at layer 28; on CC it reaches 0.5-0.55 at layers 17-18 and 31-34.
NEW: * **Not written upstream at the task statement.** The task-specification nodes close nothing (SPEC ≈ 0). By layer 23
  the earlier positions carry less than half of the gap: swapping the residual stream at all positions before the
  fork closes 0.44 / 0.37, below the committed 0.5 "written upstream" threshold. Swaps at earlier layers close more
  (up to 1.2 on MST at layer 8), because they hand the instruct model a base-model reading of the whole prompt. At the
  fork position itself, RS-fork(l) is near 0 through layer 15 and largest in the late layers (F4): on MST it peaks at
  1.49 at layer 28; on CC it reaches 0.5-0.55 at layers 17-18 and 31-34.
```

### [163] TOOL CALL — Edit · 2026-10-26 14:51:00 UTC

```
File: /tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/make_nb.py
OLD: * **anchor swap**: swapping the instruct and base anchors flips the meaning of the FSTACK share.
NEW: * **anchor swap**: recompute the FSTACK share with the instruct and base anchors swapped. It must not reproduce the
  real share; it comes out as 1 − share.
```

### [164] TOOL RESULT — Edit · 2026-10-26 14:51:00 UTC

```
{"filePath": "/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/make_nb.py", "oldString": "* **Not written upstream.** The task-specification nodes close nothing (SPEC ≈ 0). Swapping the whole residual stream at\n  all earlier positions (RS-prefix(23) = 0.44 / 0.37) stays below the committed 0.5 \"written upstream\" threshold. The\n  sharpening is mostly computed at the fork itself. The fork-only swap RS-fork(l) is near 0 through layer 15 and largest\n  in the late layers (F4): on MST it peaks at 1.49 at layer 28; on CC it reaches 0.5-0.55 at layers 17-18 and 31-34.", "newString": "* **Not written upstream at the task statement.** The task-specification nodes close nothing (SPEC ≈ 0). By layer 23\n  the earlier positions carry less than half of the gap: swapping the residual stream at all positions before the\n  fork closes 0.44 / 0.37, below the committed 0.5 \"written upstream\" threshold. Swaps at earlier layers close more\n  (up to 1.2 on MST at layer 8), because they hand the instruct model a base-model reading of the whole prompt. At the\n  fork position itself, RS-fork(l) is near 0 through layer 15 and largest in the late layers (F4): on MST it peaks at\n  1.49 at layer 28; on CC it reaches 0.5-0.55 at layers 17-18 and 31-34.", "originalFile": null, "structuredPatch": [{"oldStart": 1379, "oldLines": 10, "newStart": 1379, "newLines": 12, "lines": [" * **The tuned model is decided where its base is not.** At the MST fork the base model leans to Prim", "   (`m_B` from −0.85 to −0.6) and the instruct model to Kruskal (`m_I` from 1.0 to 1.85). At the connected-components", "   fork the base model is indifferent (`m_B` ≈ 0) and the instruct model prefers `find` by 0.2 to 9 nats.", "-* **Not written upstream.** The task-specification nodes close nothing (SPEC ≈ 0). Swapping the whole residual stream at", "-  all earlier positions (RS-prefix(23) = 0.44 / 0.37) stays below the committed 0.5 \"written upstream\" threshold. The", "-  sharpening is mostly computed at the fork itself. The fork-only swap RS-fork(l) is near 0 through layer 15 and largest", "-  in the late layers (F4): on MST it peaks at 1.49 at layer 28; on CC it reaches 0.5-0.55 at layers 17-18 and 31-34.", "+* **Not written upstream at the task statement.** The task-specification nodes close nothing (SPEC ≈ 0). By layer 23", "+  the earlier positions carry less than half of the gap: swapping the residual stream at all positions before the", "+  fork closes 0.44 / 0.37, below the committed 0.5 \"written upstream\" threshold. Swaps at earlier layers close more", "+  (up to 1.2 on MST at layer 8), because they hand the instruct model a base-model reading of the whole prompt. At the", "+  fork position itself, RS-fork(l) is near 0 through layer 15 and largest in the late layers (F4): on MST it peaks at", "+  1.49 at layer 28; on CC it reaches 0.5-0.55 at layers 17-18 and 31-34.", " * **MST (B3): many late MLPs carry it redundantly.**", "   * FSTACK closes the whole gap (1.00 [0.96, 1.04]), but the median write-norm-matched random late set closes 0.81", "     (p = 0.45)."]}], "userModified": false, "replaceAll": false}
```

### [165] TOOL RESULT — Edit · 2026-10-26 14:51:00 UTC

```
{"filePath": "/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/make_nb.py", "oldString": "* **anchor swap**: swapping the instruct and base anchors flips the meaning of the FSTACK share.", "newString": "* **anchor swap**: recompute the FSTACK share with the instruct and base anchors swapped. It must not reproduce the\n  real share; it comes out as 1 − share.", "originalFile": null, "structuredPatch": [{"oldStart": 1160, "oldLines": 7, "newStart": 1160, "newLines": 8, "lines": [" ", " * **node-label permutation**: treat a random R set as \"the circuit\" and test it against the other random sets. It", "   should be significant (p ≤ 0.05) in at most about 10 % of draws.", "-* **anchor swap**: swapping the instruct and base anchors flips the meaning of the FSTACK share.", "+* **anchor swap**: recompute the FSTACK share with the instruct and base anchors swapped. It must not reproduce the", "+  real share; it comes out as 1 − share.", " ", " The function is renamed `rederive_b2` because the notebook already has analysis9's `b2`. As above, the hard-coded 50", " random sets and 200 placebo draws read `N_RAND` / `N_PLACEBO_DRAWS`."]}], "userModified": false, "replaceAll": false}
```

### [166] TOOL CALL — Edit · 2026-10-26 14:51:00 UTC

```
File: /tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/make_nb.py
OLD: N_PROMPTS_PER_UNIT = 2      # prompts per unit taken from the data (original: 20 = all; minimum 2)
N_BOOT = 10                 # bootstrap resamples per CI, cfg9.N_BOOT (original: 10000; minimum 10)
N_RAND = 2                  # matched random component sets per null R / R-pure / R-scaled, cfg9.N_RAND (original: 50; minimum 2)
N_RAND_SPEC = 2             # matched random SPEC sets, cfg9.N_RAND_SPEC (original: 20; minimum 2)
N_PLACEBO_DRAWS = 2         # placebo draws in the stdlib re-derivation, rederive9.b2 (original: 200; minimum 2)
NEW: N_PROMPTS_PER_UNIT = 20     # prompts per unit taken from the data (original: 20 = all; minimum 2)
N_BOOT = 10000              # bootstrap resamples per CI, cfg9.N_BOOT (original: 10000; minimum 10)
N_RAND = 50                 # matched random component sets per null R / R-pure / R-scaled, cfg9.N_RAND (original: 50; minimum 2)
N_RAND_SPEC = 20            # matched random SPEC sets, cfg9.N_RAND_SPEC (original: 20; minimum 2)
N_PLACEBO_DRAWS = 200       # placebo draws in the stdlib re-derivation, rederive9.b2 (original: 200; minimum 2)
```

### [167] TOOL CALL — Bash · 2026-10-26 14:51:00 UTC

```
Regenerate final notebook and run final test:
SP="/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad"; echo "round2 (original: 20 prompts, N_BOOT 10000, N_RAND 50, N_RAND_SPEC 20, N_PLACEBO 200): nbconvert 14s, pass, all numbers == original run" >> "$SP/scaling_log.txt"; W=/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd; cd "$SP" && python3 make_nb.py "$W/code_demo.ipynb" && cd "$W" && rm -rf results figures logs && UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_cDba8_DycUJd-e339753424ba && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_cDba8_DycUJd-e339753424ba/bin/python jupyter ipykernel && t1=$(date +%s) && /tmp/aii_nb_test_envs/art_cDba8_DycUJd-e339753424ba/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | grep -v "TCP without encryption" | tail -3; echo "nbconvert exit ${PIPESTATUS[0]} in $(( $(date +%s) - t1 ))s"; python3 - <<'EOF'
import json
nb=json.load(open('code_demo.ipynb'))
err=[(i,o['ename'],o['evalue']) for i,c in enumerate(nb['cells']) if c['cell_type']=='code' for o in c.get('outputs',[]) if o['output_type']=='error']
print('errors:', err, '| executed code cells:', sum(1 for c in nb['cells'] if c['cell_type']=='code' and c['execution_count']), '/', sum(1 for c in nb['cells'] if c['cell_type']=='code'))
print('images:', sum(1 for c in nb['cells'] if c['cell_type']=='code' for o in c.get('outputs',[]) if 'image/png' in o.get('data',{})))
cfg=[''.join(c['source']) for c in nb['cells'] if c['cell_type']=='code' and ''.join(c['source']).startswith('N_PROMPTS')][0]; print(cfg)
print('GITHUB_DATA_URL exact:', any('GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-9/experiment-50/demo/mini_demo_data.json"' in ''.join(c['source']) for c in nb['cells']))
last=[c for c in nb['cells'] if c['cell_type']=='code' and ''.join(c['source']).startswith('b2s = read_json')][0]
print(''.join(''.join(o.get('text','')) for o in last['outputs'])[-400:])
EOF
du -sh results figures logs code_demo.ipynb mini_demo_data.json; ls figures
```

### [168] TOOL RESULT — Edit · 2026-10-26 14:51:00 UTC

```
{"filePath": "/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/make_nb.py", "oldString": "N_PROMPTS_PER_UNIT = 2      # prompts per unit taken from the data (original: 20 = all; minimum 2)\nN_BOOT = 10                 # bootstrap resamples per CI, cfg9.N_BOOT (original: 10000; minimum 10)\nN_RAND = 2                  # matched random component sets per null R / R-pure / R-scaled, cfg9.N_RAND (original: 50; minimum 2)\nN_RAND_SPEC = 2             # matched random SPEC sets, cfg9.N_RAND_SPEC (original: 20; minimum 2)\nN_PLACEBO_DRAWS = 2         # placebo draws in the stdlib re-derivation, rederive9.b2 (original: 200; minimum 2)", "newString": "N_PROMPTS_PER_UNIT = 20     # prompts per unit taken from the data (original: 20 = all; minimum 2)\nN_BOOT = 10000              # bootstrap resamples per CI, cfg9.N_BOOT (original: 10000; minimum 10)\nN_RAND = 50                 # matched random component sets per null R / R-pure / R-scaled, cfg9.N_RAND (original: 50; minimum 2)\nN_RAND_SPEC = 20            # matched random SPEC sets, cfg9.N_RAND_SPEC (original: 20; minimum 2)\nN_PLACEBO_DRAWS = 200       # placebo draws in the stdlib re-derivation, rederive9.b2 (original: 200; minimum 2)", "originalFile": null, "structuredPatch": [{"oldStart": 155, "oldLines": 11, "newStart": 155, "newLines": 11, "lines": [" ''')", " ", " code(r'''", "-N_PROMPTS_PER_UNIT = 2      # prompts per unit taken from the data (original: 20 = all; minimum 2)", "-N_BOOT = 10                 # bootstrap resamples per CI, cfg9.N_BOOT (original: 10000; minimum 10)", "-N_RAND = 2                  # matched random component sets per null R / R-pure / R-scaled, cfg9.N_RAND (original: 50; minimum 2)", "-N_RAND_SPEC = 2             # matched random SPEC sets, cfg9.N_RAND_SPEC (original: 20; minimum 2)", "-N_PLACEBO_DRAWS = 2         # placebo draws in the stdlib re-derivation, rederive9.b2 (original: 200; minimum 2)", "+N_PROMPTS_PER_UNIT = 20     # prompts per unit taken from the data (original: 20 = all; minimum 2)", "+N_BOOT = 10000              # bootstrap resamples per CI, cfg9.N_BOOT (original: 10000; minimum 10)", "+N_RAND = 50                 # matched random component sets per null R / R-pure / R-scaled, cfg9.N_RAND (original: 50; minimum 2)", "+N_RAND_SPEC = 20            # matched random SPEC sets, cfg9.N_RAND_SPEC (original: 20; minimum 2)", "+N_PLACEBO_DRAWS = 200       # placebo draws in the stdlib re-derivation, rederive9.b2 (original: 200; minimum 2)", " ''')", " ", " # ---------------------------------------------------------------------------------------------------------- method.py"]}], "userModified": false, "replaceAll": false}
```

### [169] TOOL RESULT — Bash · 2026-10-26 14:51:46 UTC

```
{"stdout": "wrote /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd/code_demo.ipynb with 40 cells (21 code)\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[NbConvertApp] Writing 676733 bytes to code_demo.ipynb\nnbconvert exit 0 in 45s\nerrors: [] | executed code cells: 21 / 21\nimages: 5\nN_PROMPTS_PER_UNIT = 20     # prompts per unit taken from the data (original: 20 = all; minimum 2)\nN_BOOT = 10000              # bootstrap resamples per CI, cfg9.N_BOOT (original: 10000; minimum 10)\nN_RAND = 50                 # matched random component sets per null R / R-pure / R-scaled, cfg9.N_RAND (original: 50; minimum 2)\nN_RAND_SPEC = 20            # matched random SPEC sets, cfg9.N_RAND_SPEC (original: 20; minimum 2)\nN_PLACEBO_DRAWS = 200       # placebo draws in the stdlib re-derivation, rederive9.b2 (original: 200; minimum 2)\nGITHUB_DATA_URL exact: True\ned)                    0.850                  0.850\nT10   REV: share opened by FSTACK                         0.223                  0.223\nT10   Q1 / Q2 / Q3                          False / True / True    False / True / True\nT10   localisation                                  distributed            distributed\nboth  B2 verdict                                        PARTIAL                PARTIAL\n\n11M\tresults\n2.1M\tfigures\n59K\tlogs\n661K\tcode_demo.ipynb\n4.1M\tmini_demo_data.json\nF3_b2_singles_by_layer.pdf\nF3_b2_singles_by_layer.png\nF4_b2_residual_swaps.pdf\nF4_b2_residual_swaps.png\nF5_b2_random_null.pdf\nF5_b2_random_null.png\nF8_b2_geometry_pca_demo.pdf\nF8_b2_geometry_pca_demo.png\nsummary_b2.png", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [170] THINKING · 2026-10-26 14:52:28 UTC

```
The notebook passed all checks: 21/21 cells executed, 5 figures, no errors, ran in 45s under the 600s budget, and the GitHub URL is confirmed present. Now I'll proofread the rendered markdown and clean up the test-run byproducts (`results/`, `logs/`) since the notebook regenerates them each run.
```

### [171] TOOL CALL — Bash · 2026-10-26 14:52:28 UTC

```
Mark TODOs done and review notebook markdown:
SP="/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad"; sed -i 's/^- \[ \] TODO 5\./- [x] TODO 5./; s/^- \[ \] TODO 6\./- [x] TODO 6./' "$SP/todos.md"; cat "$SP/todos.md" | cut -c1-60; cat "$SP/scaling_log.txt"; cd /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd && python3 - <<'EOF'
import json
nb=json.load(open('code_demo.ipynb'))
for i,c in enumerate(nb['cells']):
    if c['cell_type']=='markdown' and i in (6,12,26,28,34,38):
        print(f'--- md cell {i}'); print(''.join(c['source'])[:1500])
EOF
```

### [172] TOOL RESULT — Bash · 2026-10-26 14:52:28 UTC

```
{"stdout": "# TODO list (copied verbatim; no todo tool available in this\n- [x] TODO 1. Read and STRICTLY follow these skills: aii-col\n- [x] TODO 2. Read demo file and relevant preview_* files (p\n- [x] TODO 3. Create `mini_demo_data.json`: curated subset f\n- [x] TODO 4. Create `code_demo.ipynb` via NotebookEdit foll\n- [x] TODO 5. GRADUALLY SCALE (but don't overdo it): increas\n- [x] TODO 6. Verify: (1) code_demo.ipynb contains GITHUB_DA\nround0 (min: 2 prompts, N_BOOT 10, N_RAND 2, N_RAND_SPEC 2, N_PLACEBO 2): nbconvert 18s incl. installs, pass\nround1 (10 prompts, N_BOOT 1000, N_RAND 25, N_RAND_SPEC 10, N_PLACEBO 100): nbconvert 12s, pass\nround2 (original: 20 prompts, N_BOOT 10000, N_RAND 50, N_RAND_SPEC 20, N_PLACEBO 200): nbconvert 14s, pass, all numbers == original run", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [173] TOOL CALL — Bash · 2026-10-26 14:52:34 UTC

```
List markdown cells and print final ones:
python3 - <<'EOF'
import json
nb=json.load(open('code_demo.ipynb'))
for i,c in enumerate(nb['cells']):
    if c['cell_type']=='markdown':
        s=''.join(c['source'])
        print(f'[{i}] {s.splitlines()[0][:110]}  ({len(s)} ch)')
print()
print(''.join(nb['cells'][37]['source']))
print('----')
print(''.join(nb['cells'][39]['source'])[:4000])
EOF
```

### [174] TOOL RESULT — Bash · 2026-10-26 14:52:34 UTC

````
{"stdout": "[0] # How tuning sharpens a code model's algorithm choice  (3818 ch)\n[5] ## Configuration  (406 ch)\n[7] ## 1. The pipeline (`method.py`)  (560 ch)\n[9] ## 2. Constants and utilities (`src/cfg9.py`)  (575 ch)\n[11] ## 3. Statistics (`src/stats9.py`)  (356 ch)\n[13] ## 4. Put the demo rows where the original scripts read them  (1362 ch)\n[15] ## 5. Matched random null sets (`src/cmap9.py`, CPU part)  (969 ch)\n[17] The next cell reruns the three draws with the committed seeds (`SEED_RAND + unit index` for R and R-pure,  (374 ch)\n[19] ## 6. The committed B2 rules (`src/analysis9.py`)  (1793 ch)\n[21] `b2_unit` computes every B2 statistic of one unit from its rows and applies Q1-Q3 and the localisation rule. `  (226 ch)\n[23] Run the analysis stage (`analysis9.py`'s `__main__`: `setup_logging(\"analysis9\"); b2()`). The cross-claim `sum  (247 ch)\n[25] ## 7. Figures F3-F5 (`src/figures9.py`)  (678 ch)\n[27] As in `figures9.main()`, the figures are drawn from the summary file the analysis just wrote. In F3, a single   (314 ch)\n[29] ## 8. Activation geometry at the fork (F8-style)  (1137 ch)\n[31] ## 9. Independent re-derivation (`src/rederive9.py`, B2 part)  (859 ch)\n[33] Run the re-derivation against `results/b2_summary.json` and write `results/rederive.json`. The original run re  (186 ch)\n[35] ## 10. Results  (437 ch)\n[37] **Summary figure.**  (424 ch)\n[39] ### What the numbers say (original configuration: 20 prompts per unit)  (3705 ch)\n\n**Summary figure.**\n\n* **Left**: the raw per-prompt fork margins, which are the data every share is computed from: the two anchors (instruct\n  `m_I`, base `m_B`) and three patched instruct runs. Above 0 the default algorithm class is more likely, below 0 the\n  alternative.\n* **Right**: the shares that enter the committed rules, with their 95 % bootstrap CIs. The grey band is the central\n  90 % of the matched random sets.\n----\n### What the numbers say (original configuration: 20 prompts per unit)\n\n* **The tuned model is decided where its base is not.** At the MST fork the base model leans to Prim\n  (`m_B` from −0.85 to −0.6) and the instruct model to Kruskal (`m_I` from 1.0 to 1.85). At the connected-components\n  fork the base model is indifferent (`m_B` ≈ 0) and the instruct model prefers `find` by 0.2 to 9 nats.\n* **Not written upstream at the task statement.** The task-specification nodes close nothing (SPEC ≈ 0). By layer 23\n  the earlier positions carry less than half of the gap: swapping the residual stream at all positions before the\n  fork closes 0.44 / 0.37, below the committed 0.5 \"written upstream\" threshold. Swaps at earlier layers close more\n  (up to 1.2 on MST at layer 8), because they hand the instruct model a base-model reading of the whole prompt. At the\n  fork position itself, RS-fork(l) is near 0 through layer 15 and largest in the late layers (F4): on MST it peaks at\n  1.49 at layer 28; on CC it reaches 0.5-0.55 at layers 17-18 and 31-34.\n* **MST (B3): many late MLPs carry it redundantly.**\n  * FSTACK closes the whole gap (1.00 [0.96, 1.04]), but the median write-norm-matched random late set closes 0.81\n    (p = 0.45).\n  * Single late MLPs close a lot on their own (L35 0.98, L28 0.62, L29 0.56, L26 0.52), and FSTACK's joint share is\n    half the sum of its singles (1.00 vs 1.96).\n  * Base values taken from a *different* prompt work as well as the matched ones (`xprompt_FSTACK` 1.00).\n  * So what FSTACK transplants is a generic, prompt-independent base-vs-tuned offset of the late MLPs rather than a\n    specific circuit. Q2 fails.\n* **Connected components (T10): specific but partial.** FSTACK closes 0.45 [0.28, 0.57] against a random median of\n  −0.22 (p = 0.020). Most of the CC gap is not in the residual stream at all: reading the base model's own final\n  residual with the **tuned unembedding** reproduces 85 % of it. This is why RS-fork(36), which swaps the entire final\n  residual, closes only 0.15.\n* **Activation space (Section 8).**\n  * FSTACK moves the block-30 state the furthest (≈ 175 / 230 L2 against a state norm of ≈ 600).\n  * The median random set moves it about 60 % as far and only partly in the same direction (cosine ≈ 0.5), and\n    RS-fork(23) moves it elsewhere again.\n  * On MST all three still push the margin to the Prim side (blue points): quite different late perturbations reach\n    the same decision, which is the geometric face of the non-specificity found by the null test. On CC the\n    random-patched states keep a high margin (red ×).\n* **Committed verdict: PARTIAL.** Q1 fails on CC, Q2 fails on MST, Q3 holds; localisation is \"distributed\".\n\nFor the run's question about the *mean answer*: tuning does not add a dedicated \"choose Kruskal\" step upstream, at the\ntask statement. It sharpens the readout of a preference the base model only weakly has, or does not have. That\nsharpening sits partly in a redundant late-MLP offset and partly in the unembedding itself. The minority algorithm is\nstill there to be found. In the original run's generation test, a one-token patch at the fork flipped 19/30 MST\nprograms to Prim, but a matched random late patch did the same (19/30). On CC only replacing the whole fork\ndistribution with the base model's brought DFS back (18/30).\n\n**Running the full pipeline** (needs a 24 GB GPU, `HF_TOKEN` with access to Gemma 3 and Llama 3.1, about 65 GB of\nweights and about 1 GPU-hour), from the artifact folder of the repository:\n\n```bash\nuv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml\n.venv/bin/python src/download_models.py\n.venv/bin/python method.py --stages all\n```", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
````

### [175] THINKING · 2026-10-26 14:52:52 UTC

```
I noticed a factual error in the closing interpretation: on MST, the base model actually leans toward Prim rather than weakly favoring the stated preference. I'll correct that markdown cell in place and apply the same fix in the generator.
```

### [176] TOOL CALL — Bash · 2026-10-26 14:52:52 UTC

```
Fix interpretation sentence; remove regenerable run outputs:
SP="/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad"; cd /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd && python3 - "$SP/make_nb.py" <<'EOF'
import json, sys
old = ("For the run's question about the *mean answer*: tuning does not add a dedicated \"choose Kruskal\" step upstream, at the\n"
       "task statement. It sharpens the readout of a preference the base model only weakly has, or does not have. That\n"
       "sharpening sits partly in a redundant late-MLP offset and partly in the unembedding itself. The minority algorithm is\n"
       "still there to be found.")
new = ("For the run's question about the *mean answer*: tuning does not add a dedicated \"choose Kruskal\" step upstream, at the\n"
       "task statement. At a fork where the base model leans the other way (MST: Prim) or is undecided (CC), tuning installs\n"
       "a confident default late in the network, partly as a redundant late-MLP offset and partly in the unembedding itself.\n"
       "The minority algorithm is still there to be found.")
# notebook (keeps executed outputs)
nb = json.load(open('code_demo.ipynb'))
hit = 0
for c in nb['cells']:
    s = ''.join(c['source'])
    if c['cell_type'] == 'markdown' and old in s:
        s = s.replace(old, new); lines = s.split('\n')
        c['source'] = [l + '\n' for l in lines[:-1]] + [lines[-1]]; hit += 1
assert hit == 1, hit
open('code_demo.ipynb', 'w').write(json.dumps(nb, indent=1, ensure_ascii=False) + '\n')
# generator
g = open(sys.argv[1]).read(); assert g.count(old) == 1; open(sys.argv[1], 'w').write(g.replace(old, new))
print('updated notebook + generator')
EOF
rm -rf results logs && ls -la && du -sh figures
```

### [177] TOOL RESULT — Bash · 2026-10-26 14:52:52 UTC

```
{"stdout": "updated notebook + generator\ntotal 11003\ndrwxrwxrwx 4 aii-agent aii-agent 2000683 Oct 26 14:52 .\ndrwxrwxrwx 6 aii-agent aii-agent 2002296 Oct 26 14:26 ..\ndrwxrwxrwx 2 aii-agent aii-agent       1 Oct 26 14:26 .aii\n-rw-rw-rw- 1 aii-agent aii-agent      54 Oct 26 14:26 .aii_claude_session.json\n-rw-rw-rw- 1 aii-agent aii-agent 1207469 Oct 26 14:52 .repl_agent.ptylog\n-rw-rw-rw- 1 aii-agent aii-agent    8200 Oct 26 14:36 build_mini_demo_data.py\n-rw-rw-rw- 1 aii-agent aii-agent  676828 Oct 26 14:52 code_demo.ipynb\ndrwxrwxrwx 2 aii-agent aii-agent 1098364 Oct 26 14:51 figures\n-rw-rw-rw- 1 aii-agent aii-agent 4273245 Oct 26 14:36 mini_demo_data.json\n2.1M\tfigures", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [178] ASSISTANT · 2026-10-26 14:53:42 UTC

```
The workspace now holds only the deliverables. Next are the README and the manifest.
```

### [179] TOOL CALL — Write · 2026-10-26 14:53:42 UTC

````
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd/README.md

# Demo: how tuning sharpens a code model's algorithm choice (claim B2)

A runnable, CPU-only demo notebook for the iteration-9 experiment artifact `art_cDba8_DycUJd` (experiment 50, claims
B1-B3). The artifact compares instruction-tuned and base models at the **fork**: the single token where a code model
commits to an algorithm, e.g. `' Kr'`(uskal) vs `' Prim'` for a minimum spanning tree (unit **B3**), or `' find'`
(union-find) vs `' dfs'` / `' bfs'` for connected components (unit **T10**).

The notebook replays the artifact's **B2** analysis, cross-model activation patching (CMAP) in Qwen3-8B vs
Qwen3-8B-Base, on the real per-prompt rows of the GPU run. It uses the original CPU code:

* the matched-random-set draw (`src/cmap9.py`);
* the committed decision rules (`src/analysis9.py`);
* figures F3-F5 and an F8-style activation-geometry plot (`src/figures9.py`);
* the standard-library re-derivation with placebos (`src/rederive9.py`).

The script was split into cells with explanations between them. Nothing is simulated.

## Result of the demo

With the original configuration (20 prompts per unit, 10 000 bootstrap resamples, 50 + 20 random sets, 200 placebo
draws) the notebook recomputes the B2 summary **identically** to the original run. All 4 246 numeric fields of
`b2_summary.json` match to within 1e-12, bootstrap CIs included. The stdlib re-derivation reports 0 mismatches, and
the re-drawn random sets equal the ones patched on the GPU (R 50/50, R-pure 50/50, SPEC-R 20/20 per unit).

| | MST (B3: Kruskal vs Prim) | CC (T10: `find` vs `dfs`/`bfs`) |
|---|---|---|
| gap m_I − m_B (nats) | 2.06 | 4.52 |
| FSTACK share [95 % CI] | 1.00 [0.96, 1.04] | 0.45 [0.28, 0.57] |
| 50 matched random sets: median / empirical p | 0.81 / 0.45 | −0.22 / 0.020 |
| SPEC share | −0.02 | −0.17 |
| RS-fork(23) / RS-fork(36) | 0.78 / 0.57 | −0.05 / 0.15 |
| unembedding-only share (carried, see below) | 0.43 | 0.85 |
| Q1 / Q2 / Q3 | True / False / True | False / True / True |
| verdict / localisation | PARTIAL / distributed | PARTIAL / distributed |

## Layout

| path | content |
|---|---|
| `code_demo.ipynb` | the demo notebook, executed, with outputs (40 cells; markdown before every code cell) |
| `mini_demo_data.json` | demo data: the `b2_tf` dataset of the artifact (40 examples = 2 units × 20 prompts), 4.3 MB |
| `build_mini_demo_data.py` | rebuilds `mini_demo_data.json` from the artifact folder |
| `figures/` | figures written by the executed notebook: `F3_b2_singles_by_layer`, `F4_b2_residual_swaps`, `F5_b2_random_null`, `F8_b2_geometry_pca_demo` (PDF + PNG), `summary_b2.png` |
| `.aii/manifest.yaml` | keep / delete decisions for the pipeline's storage checker |

Running the notebook also writes `results/` and `logs/` in its working directory. These hold the per-prompt rows it
writes back into the original layout, `b2_summary.json`, `rederive.json` and loguru logs. They are not shipped,
because every run of the notebook rebuilds them.

## How to run

**Colab:** open `code_demo.ipynb` and run all cells. The data is fetched from
`https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-9/experiment-50/demo/mini_demo_data.json`,
with a fallback to a local `mini_demo_data.json`. The install cell only adds `loguru`. On Colab numpy and matplotlib
are preinstalled; locally the cell installs them at Colab's versions (numpy 2.0.2, matplotlib 3.10.0).

**Locally** (Python 3.12):

```bash
python -m venv .venv && .venv/bin/pip install jupyter ipykernel
.venv/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb
```

The run takes 15-45 s on a CPU. No GPU, model weights or Hugging Face token are needed.

**Configuration** (first code cell after the data loading):

| parameter | value used | original | minimum |
|---|---|---|---|
| `N_PROMPTS_PER_UNIT` | 20 | 20 (all prompts in the data) | 2 |
| `N_BOOT` | 10000 | 10000 | 10 |
| `N_RAND` | 50 | 50 | 2 |
| `N_RAND_SPEC` | 20 | 20 | 2 |
| `N_PLACEBO_DRAWS` | 200 | 200 | 2 |

The notebook was tested at the minimum values (18 s), at 10 / 1000 / 25 / 10 / 100 (12 s), and at the original values
(14-45 s), each in a fresh Python 3.12 venv.

## The demo data (`mini_demo_data.json`)

`metadata` holds:

* the unit definitions: the D / A token classes and the code opening;
* the random-set draws with their fork delta norms (`random_sets`, `spec_random_sets`);
* the GPU self-checks (`gpu_tests_b2`) and iteration 8's top-15 lists (`exp41_circuits_top15`), which the R-pure
  null uses;
* the readout-decomposition values (`carried`);
* the geometry encoding (`geometry`);
* the original run's summary values (`reference_original_run`), for the comparison table.

Each of the 40 `examples` holds:

* `unit`, `pid`, `template`;
* `input` (the decoded prompt + opening) and `output` (the instruct model's fork token), plus the base / patched argmax
  tokens;
* the anchors `m_I`, `m_B`;
* `arms`: the fork margin of every one of the 1429 patching arms;
* `rev_arms`: the 55 reverse-patch arms;
* `geom_bf16_b64`: the block-30 output at the fork (4096-d, exact bf16 bits, base64) for the unpatched, FSTACK,
  median-random-set and RS-fork(23) states.

It was built with

```bash
python build_mini_demo_data.py --artifact-dir <experiment-50 artifact folder> --out mini_demo_data.json
```

The script needs numpy and torch, the latter only to read `cache/geom_*.pt`. It reads these files of the artifact
folder:

* `results/b2_tf_{B3,T10}.jsonl` (per prompt × arm rows; the top-256 `dist` fields are dropped);
* `results/b2_rev_*.jsonl`, `results/random_sets.json`, `results/spec_random_sets_*.json`;
* `results/gpu_tests_b2.json`, `results/units.json`, `results/b2_summary.json`;
* `full_method_out.json` (for the decoded prompt text);
* `vendor/art_18XvfcJJZi1O/results/summary.json`;
* `cache/geom_*.pt`.

The original upload excluded `cache/`. Its `geom_*.pt` files exist only on the run's volume and in this JSON, and
are regenerated on a GPU by `cmap9.py s3 all`.

## Changes relative to the original code (all minimal; each is commented in the notebook)

1. A cell writes the demo rows from `mini_demo_data.json` back into the `results/` files the original scripts read.
   `analysis9.py`, `figures9.py` and `rederive9.py` then run on them unchanged.
2. The hard-coded counts become configuration variables: 50 random sets (`N_RAND`), 20 SPEC random sets
   (`N_RAND_SPEC`), 10 000 bootstrap resamples (`N_BOOT`) and 200 placebo draws (`N_PLACEBO_DRAWS`).
3. **Readout decomposition.** `analysis9.readout_decomposition` needs both models' final-norm inputs (the ~12 GB
   activation cache) and the 16 GB safetensors. The function is shown, and `b2_unit` takes its values from the
   original run (`metadata.carried`).
4. **F8 geometry.** The base model's own block-30 states lived only in `cache/base_*.pt`, which the original run did
   not keep. The PCA is therefore fit on the instruct + patched states instead of the instruct + base states, and the
   base markers are omitted. The plot is saved as `F8_b2_geometry_pca_demo` to keep it apart from the paper's F8. The
   notebook adds a printout of each patch's displacement norm and its cosine with the FSTACK shift.
5. Notebook-context fixes:
   * `import stats9 as S` becomes a `SimpleNamespace`;
   * `rederive9.b2` is renamed `rederive_b2`, because `analysis9.b2` already exists;
   * `figures9.save` shows the figure inline instead of closing it, and `matplotlib.use("Agg")` is dropped;
   * torch is not imported.
6. Two blocks are not run, because they need files outside this dataset: `analysis9.summary()` (it merges the B1 / B3
   summaries and verifies the commitment chain) and the superseded v1 sensitivity block (its rows are not in the
   data, so the code skips it).

## Not reproduced here

* The GPU stages of `method.py`: Qwen3-8B / -Base captures and patched forward passes, the Gemma / Llama B1 runs, the
  B3 rerun and the generation test. They need a 24 GB GPU, about 65 GB of weights and about 1 GPU-hour, and run with
  `method.py --stages all` in the artifact folder.
* The B1, B3 and generation results are quoted in the notebook's introduction, not recomputed.

## Restoring removed files

No path in this folder is marked `delete` in `.aii/manifest.yaml`, so nothing needs restoring.

* The run outputs `results/` and `logs/` are regenerated by executing the notebook (command above).
* `mini_demo_data.json` is regenerated from the artifact folder with `build_mini_demo_data.py` (command above).
````

### [180] TOOL RESULT — Write · 2026-10-26 14:53:42 UTC

````
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd/README.md", "content": "# Demo: how tuning sharpens a code model's algorithm choice (claim B2)\n\nA runnable, CPU-only demo notebook for the iteration-9 experiment artifact `art_cDba8_DycUJd` (experiment 50, claims\nB1-B3). The artifact compares instruction-tuned and base models at the **fork**: the single token where a code model\ncommits to an algorithm, e.g. `' Kr'`(uskal) vs `' Prim'` for a minimum spanning tree (unit **B3**), or `' find'`\n(union-find) vs `' dfs'` / `' bfs'` for connected components (unit **T10**).\n\nThe notebook replays the artifact's **B2** analysis, cross-model activation patching (CMAP) in Qwen3-8B vs\nQwen3-8B-Base, on the real per-prompt rows of the GPU run. It uses the original CPU code:\n\n* the matched-random-set draw (`src/cmap9.py`);\n* the committed decision rules (`src/analysis9.py`);\n* figures F3-F5 and an F8-style activation-geometry plot (`src/figures9.py`);\n* the standard-library re-derivation with placebos (`src/rederive9.py`).\n\nThe script was split into cells with explanations between them. Nothing is simulated.\n\n## Result of the demo\n\nWith the original configuration (20 prompts per unit, 10 000 bootstrap resamples, 50 + 20 random sets, 200 placebo\ndraws) the notebook recomputes the B2 summary **identically** to the original run. All 4 246 numeric fields of\n`b2_summary.json` match to within 1e-12, bootstrap CIs included. The stdlib re-derivation reports 0 mismatches, and\nthe re-drawn random sets equal the ones patched on the GPU (R 50/50, R-pure 50/50, SPEC-R 20/20 per unit).\n\n| | MST (B3: Kruskal vs Prim) | CC (T10: `find` vs `dfs`/`bfs`) |\n|---|---|---|\n| gap m_I − m_B (nats) | 2.06 | 4.52 |\n| FSTACK share [95 % CI] | 1.00 [0.96, 1.04] | 0.45 [0.28, 0.57] |\n| 50 matched random sets: median / empirical p | 0.81 / 0.45 | −0.22 / 0.020 |\n| SPEC share | −0.02 | −0.17 |\n| RS-fork(23) / RS-fork(36) | 0.78 / 0.57 | −0.05 / 0.15 |\n| unembedding-only share (carried, see below) | 0.43 | 0.85 |\n| Q1 / Q2 / Q3 | True / False / True | False / True / True |\n| verdict / localisation | PARTIAL / distributed | PARTIAL / distributed |\n\n## Layout\n\n| path | content |\n|---|---|\n| `code_demo.ipynb` | the demo notebook, executed, with outputs (40 cells; markdown before every code cell) |\n| `mini_demo_data.json` | demo data: the `b2_tf` dataset of the artifact (40 examples = 2 units × 20 prompts), 4.3 MB |\n| `build_mini_demo_data.py` | rebuilds `mini_demo_data.json` from the artifact folder |\n| `figures/` | figures written by the executed notebook: `F3_b2_singles_by_layer`, `F4_b2_residual_swaps`, `F5_b2_random_null`, `F8_b2_geometry_pca_demo` (PDF + PNG), `summary_b2.png` |\n| `.aii/manifest.yaml` | keep / delete decisions for the pipeline's storage checker |\n\nRunning the notebook also writes `results/` and `logs/` in its working directory. These hold the per-prompt rows it\nwrites back into the original layout, `b2_summary.json`, `rederive.json` and loguru logs. They are not shipped,\nbecause every run of the notebook rebuilds them.\n\n## How to run\n\n**Colab:** open `code_demo.ipynb` and run all cells. The data is fetched from\n`https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-9/experiment-50/demo/mini_demo_data.json`,\nwith a fallback to a local `mini_demo_data.json`. The install cell only adds `loguru`. On Colab numpy and matplotlib\nare preinstalled; locally the cell installs them at Colab's versions (numpy 2.0.2, matplotlib 3.10.0).\n\n**Locally** (Python 3.12):\n\n```bash\npython -m venv .venv && .venv/bin/pip install jupyter ipykernel\n.venv/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb\n```\n\nThe run takes 15-45 s on a CPU. No GPU, model weights or Hugging Face token are needed.\n\n**Configuration** (first code cell after the data loading):\n\n| parameter | value used | original | minimum |\n|---|---|---|---|\n| `N_PROMPTS_PER_UNIT` | 20 | 20 (all prompts in the data) | 2 |\n| `N_BOOT` | 10000 | 10000 | 10 |\n| `N_RAND` | 50 | 50 | 2 |\n| `N_RAND_SPEC` | 20 | 20 | 2 |\n| `N_PLACEBO_DRAWS` | 200 | 200 | 2 |\n\nThe notebook was tested at the minimum values (18 s), at 10 / 1000 / 25 / 10 / 100 (12 s), and at the original values\n(14-45 s), each in a fresh Python 3.12 venv.\n\n## The demo data (`mini_demo_data.json`)\n\n`metadata` holds:\n\n* the unit definitions: the D / A token classes and the code opening;\n* the random-set draws with their fork delta norms (`random_sets`, `spec_random_sets`);\n* the GPU self-checks (`gpu_tests_b2`) and iteration 8's top-15 lists (`exp41_circuits_top15`), which the R-pure\n  null uses;\n* the readout-decomposition values (`carried`);\n* the geometry encoding (`geometry`);\n* the original run's summary values (`reference_original_run`), for the comparison table.\n\nEach of the 40 `examples` holds:\n\n* `unit`, `pid`, `template`;\n* `input` (the decoded prompt + opening) and `output` (the instruct model's fork token), plus the base / patched argmax\n  tokens;\n* the anchors `m_I`, `m_B`;\n* `arms`: the fork margin of every one of the 1429 patching arms;\n* `rev_arms`: the 55 reverse-patch arms;\n* `geom_bf16_b64`: the block-30 output at the fork (4096-d, exact bf16 bits, base64) for the unpatched, FSTACK,\n  median-random-set and RS-fork(23) states.\n\nIt was built with\n\n```bash\npython build_mini_demo_data.py --artifact-dir <experiment-50 artifact folder> --out mini_demo_data.json\n```\n\nThe script needs numpy and torch, the latter only to read `cache/geom_*.pt`. It reads these files of the artifact\nfolder:\n\n* `results/b2_tf_{B3,T10}.jsonl` (per prompt × arm rows; the top-256 `dist` fields are dropped);\n* `results/b2_rev_*.jsonl`, `results/random_sets.json`, `results/spec_random_sets_*.json`;\n* `results/gpu_tests_b2.json`, `results/units.json`, `results/b2_summary.json`;\n* `full_method_out.json` (for the decoded prompt text);\n* `vendor/art_18XvfcJJZi1O/results/summary.json`;\n* `cache/geom_*.pt`.\n\nThe original upload excluded `cache/`. Its `geom_*.pt` files exist only on the run's volume and in this JSON, and\nare regenerated on a GPU by `cmap9.py s3 all`.\n\n## Changes relative to the original code (all minimal; each is commented in the notebook)\n\n1. A cell writes the demo rows from `mini_demo_data.json` back into the `results/` files the original scripts read.\n   `analysis9.py`, `figures9.py` and `rederive9.py` then run on them unchanged.\n2. The hard-coded counts become configuration variables: 50 random sets (`N_RAND`), 20 SPEC random sets\n   (`N_RAND_SPEC`), 10 000 bootstrap resamples (`N_BOOT`) and 200 placebo draws (`N_PLACEBO_DRAWS`).\n3. **Readout decomposition.** `analysis9.readout_decomposition` needs both models' final-norm inputs (the ~12 GB\n   activation cache) and the 16 GB safetensors. The function is shown, and `b2_unit` takes its values from the\n   original run (`metadata.carried`).\n4. **F8 geometry.** The base model's own block-30 states lived only in `cache/base_*.pt`, which the original run did\n   not keep. The PCA is therefore fit on the instruct + patched states instead of the instruct + base states, and the\n   base markers are omitted. The plot is saved as `F8_b2_geometry_pca_demo` to keep it apart from the paper's F8. The\n   notebook adds a printout of each patch's displacement norm and its cosine with the FSTACK shift.\n5. Notebook-context fixes:\n   * `import stats9 as S` becomes a `SimpleNamespace`;\n   * `rederive9.b2` is renamed `rederive_b2`, because `analysis9.b2` already exists;\n   * `figures9.save` shows the figure inline instead of closing it, and `matplotlib.use(\"Agg\")` is dropped;\n   * torch is not imported.\n6. Two blocks are not run, because they need files outside this dataset: `analysis9.summary()` (it merges the B1 / B3\n   summaries and verifies the commitment chain) and the superseded v1 sensitivity block (its rows are not in the\n   data, so the code skips it).\n\n## Not reproduced here\n\n* The GPU stages of `method.py`: Qwen3-8B / -Base captures and patched forward passes, the Gemma / Llama B1 runs, the\n  B3 rerun and the generation test. They need a 24 GB GPU, about 65 GB of weights and about 1 GPU-hour, and run with\n  `method.py --stages all` in the artifact folder.\n* The B1, B3 and generation results are quoted in the notebook's introduction, not recomputed.\n\n## Restoring removed files\n\nNo path in this folder is marked `delete` in `.aii/manifest.yaml`, so nothing needs restoring.\n\n* The run outputs `results/` and `logs/` are regenerated by executing the notebook (command above).\n* `mini_demo_data.json` is regenerated from the artifact folder with `build_mini_demo_data.py` (command above).\n", "structuredPatch": [], "originalFile": null, "userModified": false}
````

### [181] TOOL CALL — Write · 2026-10-26 14:53:42 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd/.aii/manifest.yaml

entries:
  - path: mini_demo_data.json
    keep: demo dataset read by code_demo.ipynb (40 B2 prompts x 1429 CMAP arms + bf16 fork states); its fork states come from cache/geom_*.pt, which the original upload excluded
  - path: code_demo.ipynb
    keep: the executed demo notebook (deliverable)
  - path: figures/
    keep: figures written by the executed notebook (F3-F5, F8-style geometry, summary); small PNG/PDF
```

### [182] TOOL RESULT — Write · 2026-10-26 14:53:42 UTC

```
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd/.aii/manifest.yaml", "content": "entries:\n  - path: mini_demo_data.json\n    keep: demo dataset read by code_demo.ipynb (40 B2 prompts x 1429 CMAP arms + bf16 fork states); its fork states come from cache/geom_*.pt, which the original upload excluded\n  - path: code_demo.ipynb\n    keep: the executed demo notebook (deliverable)\n  - path: figures/\n    keep: figures written by the executed notebook (F3-F5, F8-style geometry, summary); small PNG/PDF\n", "structuredPatch": [], "originalFile": null, "userModified": false}
```

### [183] TOOL CALL — Write · 2026-10-26 14:53:42 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd/.terminal_claude_agent_struct_out.json

{
  "out_expected_files": {
    "notebook": "code_demo.ipynb",
    "mini_data_file": "mini_demo_data.json"
  }
}
```

### [184] TOOL RESULT — Write · 2026-10-26 14:53:42 UTC

```
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd/.terminal_claude_agent_struct_out.json", "content": "{\n  \"out_expected_files\": {\n    \"notebook\": \"code_demo.ipynb\",\n    \"mini_data_file\": \"mini_demo_data.json\"\n  }\n}\n", "structuredPatch": [], "originalFile": null, "userModified": false}
```

### [185] ASSISTANT · 2026-10-26 14:53:54 UTC

```
Final checks: the manifest parses, the notebook validates as nbformat after the in-place edit, the struct output is valid JSON, and no absolute server path leaked into a publishable file.
```

### [186] TOOL CALL — Bash · 2026-10-26 14:53:54 UTC

```
Validate notebook, manifest, struct output and paths:
/tmp/aii_nb_test_envs/art_cDba8_DycUJd-e339753424ba/bin/python - <<'EOF'
import json, nbformat, yaml, pathlib
nb = nbformat.read('code_demo.ipynb', as_version=4); nbformat.validate(nb); print('nbformat valid:', len(nb.cells), 'cells')
m = yaml.safe_load(open('.aii/manifest.yaml')); print('manifest entries:', [(e['path'], [k for k in e if k != 'path']) for e in m['entries']])
for e in m['entries']: assert pathlib.Path(e['path']).exists(), e
print('struct out:', json.load(open('.terminal_claude_agent_struct_out.json')))
EOF
grep -l "/ai-inventor\|run_0oWBKrKEGsmU" README.md code_demo.ipynb mini_demo_data.json build_mini_demo_data.py .aii/manifest.yaml 2>/dev/null || echo "no absolute server paths in published files"; grep -o '/tmp/[^ "]*' code_demo.ipynb | sort -u | head; find . -size +10M -not -path './.repl_agent.ptylog'; ls -la . figures
```

### [187] TOOL RESULT — Bash · 2026-10-26 14:53:54 UTC

```
{"stdout": "nbformat valid: 40 cells\nmanifest entries: [('mini_demo_data.json', ['keep']), ('code_demo.ipynb', ['keep']), ('figures/', ['keep'])]\nstruct out: {'out_expected_files': {'notebook': 'code_demo.ipynb', 'mini_data_file': 'mini_demo_data.json'}}\ncode_demo.ipynb\nREADME.md\n/tmp/ipykernel_841/2451970436.py:43:\n.:\ntotal 11117\ndrwxrwxrwx 4 aii-agent aii-agent 2000690 Oct 26 14:53 .\ndrwxrwxrwx 6 aii-agent aii-agent 2002313 Oct 26 14:26 ..\ndrwxrwxrwx 2 aii-agent aii-agent   41500 Oct 26 14:53 .aii\n-rw-rw-rw- 1 aii-agent aii-agent      54 Oct 26 14:26 .aii_claude_session.json\n-rw-rw-rw- 1 aii-agent aii-agent 1270611 Oct 26 14:53 .repl_agent.ptylog\n-rw-rw-rw- 1 aii-agent aii-agent     113 Oct 26 14:53 .terminal_claude_agent_struct_out.json\n-rw-rw-rw- 1 aii-agent aii-agent    8633 Oct 26 14:53 README.md\n-rw-rw-rw- 1 aii-agent aii-agent    8200 Oct 26 14:36 build_mini_demo_data.py\n-rw-rw-rw- 1 aii-agent aii-agent  676828 Oct 26 14:52 code_demo.ipynb\ndrwxrwxrwx 2 aii-agent aii-agent 1098364 Oct 26 14:51 figures\n-rw-rw-rw- 1 aii-agent aii-agent 4273245 Oct 26 14:36 mini_demo_data.json\n\nfigures:\ntotal 4013\ndrwxrwxrwx 2 aii-agent aii-agent 1098364 Oct 26 14:51 .\ndrwxrwxrwx 4 aii-agent aii-agent 2000690 Oct 26 14:53 ..\n-rw-rw-rw- 1 aii-agent aii-agent   57345 Oct 26 14:51 F3_b2_singles_by_layer.pdf\n-rw-rw-rw- 1 aii-agent aii-agent  225420 Oct 26 14:51 F3_b2_singles_by_layer.png\n-rw-rw-rw- 1 aii-agent aii-agent   18692 Oct 26 14:51 F4_b2_residual_swaps.pdf\n-rw-rw-rw- 1 aii-agent aii-agent  191977 Oct 26 14:51 F4_b2_residual_swaps.png\n-rw-rw-rw- 1 aii-agent aii-agent   16871 Oct 26 14:51 F5_b2_random_null.pdf\n-rw-rw-rw- 1 aii-agent aii-agent   76514 Oct 26 14:51 F5_b2_random_null.png\n-rw-rw-rw- 1 aii-agent aii-agent   28317 Oct 26 14:51 F8_b2_geometry_pca_demo.pdf\n-rw-rw-rw- 1 aii-agent aii-agent  138492 Oct 26 14:51 F8_b2_geometry_pca_demo.png\n-rw-rw-rw- 1 aii-agent aii-agent  253627 Oct 26 14:51 summary_b2.png", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [188] ASSISTANT · 2026-10-26 14:54:00 UTC

```
The grep found server-path-like strings in `code_demo.ipynb` and `README.md`. I'll find out exactly what matched.
```

### [189] TOOL CALL — Bash · 2026-10-26 14:54:00 UTC

```
Show the matched path strings in context:
grep -n -o ".\{60\}\(/ai-inventor\|run_0oWBKrKEGsmU\).\{60\}" README.md code_demo.ipynb | head
```

### [190] TOOL RESULT — Bash · 2026-10-26 14:54:00 UTC

```
{"stdout": "", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [191] TOOL CALL — Bash · 2026-10-26 14:54:06 UTC

```
Locate ai-inventor strings in README and notebook:
grep -n "ai-inventor" README.md | cut -c1-220; grep -c "ai-inventor" code_demo.ipynb; grep -o ".\{0,40\}ai-inventor.\{0,60\}" code_demo.ipynb | sort | uniq -c | head
```

### [192] TOOL RESULT — Bash · 2026-10-26 14:54:06 UTC

```
{"stdout": "53:`https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-9/experiment-50/demo/mini_demo_data.json`,\n1\n      1 L = \\\"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [193] ASSISTANT · 2026-10-26 14:54:37 UTC

```
The demo is finished. `code_demo.ipynb` is executed with outputs and, at the original configuration, reproduces the B2 analysis exactly from the stored per-prompt rows. All 4,246 numeric fields of `b2_summary.json` match the original run to within 1e-12, bootstrap CIs included. The verdict is PARTIAL with localisation "distributed", as in the original.

**What the notebook runs.** Only one of the artifact's datasets is used: `b2_tf`, the 40 Qwen3-8B patching prompts (20 MST, 20 connected components). On those rows it runs the original CPU code:
- **Random null sets:** the draw is rerun from the stored norms and seeds, and every set (50 R, 50 R-pure, 20 SPEC-R per unit) is identical to the ones patched on the GPU.
- **Decision rules:** the committed Q1–Q3, verdict and localisation rules from `analysis9.py`, with no code changes.
- **Figures:** F3–F5 unchanged, plus an F8-style plot of the actual block-30 activations at the fork.
- **Re-derivation:** the standard-library check reports 0 mismatches, and its placebos fail as required.

The GPU stages (model forward passes) and the B1, B3 and generation results are not recomputed; their numbers are only quoted in the introduction.

**Departures from the original code you should know about:**
- **F8 without base-model states.** The base model's own fork activations lived in a cache the original run deleted. So the PCA is fit on the instruct and patched states instead, and the plot is saved under a separate name from the paper's F8.
- **Unembedding finding is not recomputed.** The share of the gap carried by the tuned unembedding (43 % MST, 85 % CC) needs the 16 GB weights and the deleted cache. The notebook shows the function and uses the original run's values.
- **Hard-coded counts became settings.** The random-set counts (50 and 20) and the placebo count (200) are now config variables.
- **Name fixes for the notebook.** `rederive9.b2` is renamed `rederive_b2` because `analysis9.b2` already exists, and `import stats9 as S` is replaced by an equivalent namespace.
- **Original `summary()` is not run.** It needs the B1/B3 summaries and the commitment-chain files, which are outside this dataset.

**Scaling (TODO 5).** I tested in the fresh venv three times:

| round | prompts / bootstrap / random sets / SPEC sets / placebo draws | runtime |
|---|---|---|
| 1 | minimum: 2 / 10 / 2 / 2 / 2 | 18 s |
| 2 | 10 / 1000 / 25 / 10 / 100 | 12 s |
| 3 | original: 20 / 10000 / 50 / 20 / 200 | 14–45 s |

The notebook keeps the original values, well inside the 600 s limit.

**Things that differ from the instructions:**
- **No NotebookEdit.** The notebook is about 38K tokens, over the Read tool's 25K limit, and NotebookEdit refuses files it hasn't read. I generated the notebook from cell sources I had tested as a plain script, and changed the config cell with a small script that edits only that cell's JSON. The generator is `/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-9-art-cDba8-DycUJd/06cc5ef4-2121-42ef-9e7a-40d8955df1b5/scratchpad/make_nb.py`.
- **No todo tool.** This session has none, so I kept the six TODOs verbatim in a scratchpad file and checked them all off.
- **One warning in the notebook output.** The F8 cell shows a matplotlib `UserWarning` that comes from the original plotting code; I left it.
- **Research paragraph treated as background.** I read the closing paragraph about LLM creativity as context for the overall research run, not as a task for this step.

TODO 6 checks pass: the exact `GITHUB_DATA_URL` is in the notebook, `mini_demo_data.json` exists, and loading uses the GitHub URL with a local fallback (it currently falls back, since the URL returns 404 until the push). I removed the `results/` and `logs/` folders my test runs created; running the notebook rebuilds them.

Files are in the workspace:
- `code_demo.ipynb`
- `mini_demo_data.json` (4.3 MB)
- `build_mini_demo_data.py` — rebuilds the data file; it needs the artifact folder, which includes the run-volume-only `cache/geom_*.pt` files
- `figures/`
- `README.md`
- `.aii/manifest.yaml` — `keep` entries only, nothing marked delete
- `.terminal_claude_agent_struct_out.json`
```

### [194] SYSTEM-USER prompt · 2026-10-26 14:54:40 UTC

```
<CRITICAL_ERROR>
The module-end file check FAILED (attempt 1/3).

PROBLEMS:
  - .aii/manifest.yaml: 'mini_demo_data.json' matches nothing that needs a decision — remove it (text, code and files under the auto-keep floor are always kept)
  - .aii/manifest.yaml: 'code_demo.ipynb' matches nothing that needs a decision — remove it (text, code and files under the auto-keep floor are always kept)
  - .aii/manifest.yaml: 'figures/' matches nothing that needs a decision — remove it (text, code and files under the auto-keep floor are always kept)

FIX IT:
1. Add one entry per uncovered path to `.aii/manifest.yaml` (create it if missing).
   Every path is RELATIVE TO YOUR CWD and must resolve inside it. Globs and
   whole directories are fine — a whole `hf_cache/` is ONE entry.

   entries:
     - path: results/
       keep: six GPU-hours of sweep output, not reproducible in this run
     - path: hf_cache/
       delete: redownloadable
       source: "huggingface-cli download meta-llama/Llama-3-8B"
     - path: checkpoints/
       delete: regenerable
       source: "uv run train.py --epochs 3"

   `keep:` takes a one-line reason. `delete:` takes `redownloadable` or
   `regenerable` and a `source:` that brings the files back.
2. Make sure `README.md` reads like a GitHub repository README: what you did,
   the layout (a line per important file/dir), how to run it, and a
   "Restoring removed files" section with the command for EVERY delete entry.
3. Text and code files never need a decision, and neither does anything under
   the auto-keep floor. Only large binaries and cache directories do.
</CRITICAL_ERROR>
```

### [195] ASSISTANT · 2026-10-26 14:54:52 UTC

```
The checker wants no entries for files that don't need a decision, and nothing in this folder is large or a cache. So the manifest becomes an empty list, and I'll update the README's manifest line to say so.
```

### [196] TOOL CALL — Write · 2026-10-26 14:54:52 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd/.aii/manifest.yaml

entries: []
```

### [197] TOOL RESULT — Write · 2026-10-26 14:54:52 UTC

```
{"type": "update", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd/.aii/manifest.yaml", "content": "entries: []\n", "structuredPatch": [{"oldStart": 1, "oldLines": 7, "newStart": 1, "newLines": 1, "lines": ["-entries:", "-  - path: mini_demo_data.json", "-    keep: demo dataset read by code_demo.ipynb (40 B2 prompts x 1429 CMAP arms + bf16 fork states); its fork states come from cache/geom_*.pt, which the original upload excluded", "-  - path: code_demo.ipynb", "-    keep: the executed demo notebook (deliverable)", "-  - path: figures/", "-    keep: figures written by the executed notebook (F3-F5, F8-style geometry, summary); small PNG/PDF", "+entries: []"]}], "originalFile": "entries:\n  - path: mini_demo_data.json\n    keep: demo dataset read by code_demo.ipynb (40 B2 prompts x 1429 CMAP arms + bf16 fork states); its fork states come from cache/geom_*.pt, which the original upload excluded\n  - path: code_demo.ipynb\n    keep: the executed demo notebook (deliverable)\n  - path: figures/\n    keep: figures written by the executed notebook (F3-F5, F8-style geometry, summary); small PNG/PDF\n", "userModified": false}
```

### [198] TOOL CALL — Edit · 2026-10-26 14:54:52 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd/README.md
OLD: | `.aii/manifest.yaml` | keep / delete decisions for the pipeline's storage checker |
NEW: | `.aii/manifest.yaml` | storage decisions for the pipeline's checker: empty, since every file here is text, code or below the 10 MB floor |
```

### [199] TOOL RESULT — Edit · 2026-10-26 14:54:52 UTC

````
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_9/art_cDba8_DycUJd/README.md", "oldString": "| `.aii/manifest.yaml` | keep / delete decisions for the pipeline's storage checker |", "newString": "| `.aii/manifest.yaml` | storage decisions for the pipeline's checker: empty, since every file here is text, code or below the 10 MB floor |", "originalFile": "# Demo: how tuning sharpens a code model's algorithm choice (claim B2)\n\nA runnable, CPU-only demo notebook for the iteration-9 experiment artifact `art_cDba8_DycUJd` (experiment 50, claims\nB1-B3). The artifact compares instruction-tuned and base models at the **fork**: the single token where a code model\ncommits to an algorithm, e.g. `' Kr'`(uskal) vs `' Prim'` for a minimum spanning tree (unit **B3**), or `' find'`\n(union-find) vs `' dfs'` / `' bfs'` for connected components (unit **T10**).\n\nThe notebook replays the artifact's **B2** analysis, cross-model activation patching (CMAP) in Qwen3-8B vs\nQwen3-8B-Base, on the real per-prompt rows of the GPU run. It uses the original CPU code:\n\n* the matched-random-set draw (`src/cmap9.py`);\n* the committed decision rules (`src/analysis9.py`);\n* figures F3-F5 and an F8-style activation-geometry plot (`src/figures9.py`);\n* the standard-library re-derivation with placebos (`src/rederive9.py`).\n\nThe script was split into cells with explanations between them. Nothing is simulated.\n\n## Result of the demo\n\nWith the original configuration (20 prompts per unit, 10 000 bootstrap resamples, 50 + 20 random sets, 200 placebo\ndraws) the notebook recomputes the B2 summary **identically** to the original run. All 4 246 numeric fields of\n`b2_summary.json` match to within 1e-12, bootstrap CIs included. The stdlib re-derivation reports 0 mismatches, and\nthe re-drawn random sets equal the ones patched on the GPU (R 50/50, R-pure 50/50, SPEC-R 20/20 per unit).\n\n| | MST (B3: Kruskal vs Prim) | CC (T10: `find` vs `dfs`/`bfs`) |\n|---|---|---|\n| gap m_I − m_B (nats) | 2.06 | 4.52 |\n| FSTACK share [95 % CI] | 1.00 [0.96, 1.04] | 0.45 [0.28, 0.57] |\n| 50 matched random sets: median / empirical p | 0.81 / 0.45 | −0.22 / 0.020 |\n| SPEC share | −0.02 | −0.17 |\n| RS-fork(23) / RS-fork(36) | 0.78 / 0.57 | −0.05 / 0.15 |\n| unembedding-only share (carried, see below) | 0.43 | 0.85 |\n| Q1 / Q2 / Q3 | True / False / True | False / True / True |\n| verdict / localisation | PARTIAL / distributed | PARTIAL / distributed |\n\n## Layout\n\n| path | content |\n|---|---|\n| `code_demo.ipynb` | the demo notebook, executed, with outputs (40 cells; markdown before every code cell) |\n| `mini_demo_data.json` | demo data: the `b2_tf` dataset of the artifact (40 examples = 2 units × 20 prompts), 4.3 MB |\n| `build_mini_demo_data.py` | rebuilds `mini_demo_data.json` from the artifact folder |\n| `figures/` | figures written by the executed notebook: `F3_b2_singles_by_layer`, `F4_b2_residual_swaps`, `F5_b2_random_null`, `F8_b2_geometry_pca_demo` (PDF + PNG), `summary_b2.png` |\n| `.aii/manifest.yaml` | keep / delete decisions for the pipeline's storage checker |\n\nRunning the notebook also writes `results/` and `logs/` in its working directory. These hold the per-prompt rows it\nwrites back into the original layout, `b2_summary.json`, `rederive.json` and loguru logs. They are not shipped,\nbecause every run of the notebook rebuilds them.\n\n## How to run\n\n**Colab:** open `code_demo.ipynb` and run all cells. The data is fetched from\n`https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-9/experiment-50/demo/mini_demo_data.json`,\nwith a fallback to a local `mini_demo_data.json`. The install cell only adds `loguru`. On Colab numpy and matplotlib\nare preinstalled; locally the cell installs them at Colab's versions (numpy 2.0.2, matplotlib 3.10.0).\n\n**Locally** (Python 3.12):\n\n```bash\npython -m venv .venv && .venv/bin/pip install jupyter ipykernel\n.venv/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb\n```\n\nThe run takes 15-45 s on a CPU. No GPU, model weights or Hugging Face token are needed.\n\n**Configuration** (first code cell after the data loading):\n\n| parameter | value used | original | minimum |\n|---|---|---|---|\n| `N_PROMPTS_PER_UNIT` | 20 | 20 (all prompts in the data) | 2 |\n| `N_BOOT` | 10000 | 10000 | 10 |\n| `N_RAND` | 50 | 50 | 2 |\n| `N_RAND_SPEC` | 20 | 20 | 2 |\n| `N_PLACEBO_DRAWS` | 200 | 200 | 2 |\n\nThe notebook was tested at the minimum values (18 s), at 10 / 1000 / 25 / 10 / 100 (12 s), and at the original values\n(14-45 s), each in a fresh Python 3.12 venv.\n\n## The demo data (`mini_demo_data.json`)\n\n`metadata` holds:\n\n* the unit definitions: the D / A token classes and the code opening;\n* the random-set draws with their fork delta norms (`random_sets`, `spec_random_sets`);\n* the GPU self-checks (`gpu_tests_b2`) and iteration 8's top-15 lists (`exp41_circuits_top15`), which the R-pure\n  null uses;\n* the readout-decomposition values (`carried`);\n* the geometry encoding (`geometry`);\n* the original run's summary values (`reference_original_run`), for the comparison table.\n\nEach of the 40 `examples` holds:\n\n* `unit`, `pid`, `template`;\n* `input` (the decoded prompt + opening) and `output` (the instruct model's fork token), plus the base / patched argmax\n  tokens;\n* the anchors `m_I`, `m_B`;\n* `arms`: the fork margin of every one of the 1429 patching arms;\n* `rev_arms`: the 55 reverse-patch arms;\n* `geom_bf16_b64`: the block-30 output at the fork (4096-d, exact bf16 bits, base64) for the unpatched, FSTACK,\n  median-random-set and RS-fork(23) states.\n\nIt was built with\n\n```bash\npython build_mini_demo_data.py --artifact-dir <experiment-50 artifact folder> --out mini_demo_data.json\n```\n\nThe script needs numpy and torch, the latter only to read `cache/geom_*.pt`. It reads these files of the artifact\nfolder:\n\n* `results/b2_tf_{B3,T10}.jsonl` (per prompt × arm rows; the top-256 `dist` fields are dropped);\n* `results/b2_rev_*.jsonl`, `results/random_sets.json`, `results/spec_random_sets_*.json`;\n* `results/gpu_tests_b2.json`, `results/units.json`, `results/b2_summary.json`;\n* `full_method_out.json` (for the decoded prompt text);\n* `vendor/art_18XvfcJJZi1O/results/summary.json`;\n* `cache/geom_*.pt`.\n\nThe original upload excluded `cache/`. Its `geom_*.pt` files exist only on the run's volume and in this JSON, and\nare regenerated on a GPU by `cmap9.py s3 all`.\n\n## Changes relative to the original code (all minimal; each is commented in the notebook)\n\n1. A cell writes the demo rows from `mini_demo_data.json` back into the `results/` files the original scripts read.\n   `analysis9.py`, `figures9.py` and `rederive9.py` then run on them unchanged.\n2. The hard-coded counts become configuration variables: 50 random sets (`N_RAND`), 20 SPEC random sets\n   (`N_RAND_SPEC`), 10 000 bootstrap resamples (`N_BOOT`) and 200 placebo draws (`N_PLACEBO_DRAWS`).\n3. **Readout decomposition.** `analysis9.readout_decomposition` needs both models' final-norm inputs (the ~12 GB\n   activation cache) and the 16 GB safetensors. The function is shown, and `b2_unit` takes its values from the\n   original run (`metadata.carried`).\n4. **F8 geometry.** The base model's own block-30 states lived only in `cache/base_*.pt`, which the original run did\n   not keep. The PCA is therefore fit on the instruct + patched states instead of the instruct + base states, and the\n   base markers are omitted. The plot is saved as `F8_b2_geometry_pca_demo` to keep it apart from the paper's F8. The\n   notebook adds a printout of each patch's displacement norm and its cosine with the FSTACK shift.\n5. Notebook-context fixes:\n   * `import stats9 as S` becomes a `SimpleNamespace`;\n   * `rederive9.b2` is renamed `rederive_b2`, because `analysis9.b2` already exists;\n   * `figures9.save` shows the figure inline instead of closing it, and `matplotlib.use(\"Agg\")` is dropped;\n   * torch is not imported.\n6. Two blocks are not run, because they need files outside this dataset: `analysis9.summary()` (it merges the B1 / B3\n   summaries and verifies the commitment chain) and the superseded v1 sensitivity block (its rows are not in the\n   data, so the code skips it).\n\n## Not reproduced here\n\n* The GPU stages of `method.py`: Qwen3-8B / -Base captures and patched forward passes, the Gemma / Llama B1 runs, the\n  B3 rerun and the generation test. They need a 24 GB GPU, about 65 GB of weights and about 1 GPU-hour, and run with\n  `method.py --stages all` in the artifact folder.\n* The B1, B3 and generation results are quoted in the notebook's introduction, not recomputed.\n\n## Restoring removed files\n\nNo path in this folder is marked `delete` in `.aii/manifest.yaml`, so nothing needs restoring.\n\n* The run outputs `results/` and `logs/` are regenerated by executing the notebook (command above).\n* `mini_demo_data.json` is regenerated from the artifact folder with `build_mini_demo_data.py` (command above).\n", "structuredPatch": [{"oldStart": 41, "oldLines": 7, "newStart": 41, "newLines": 7, "lines": [" | `mini_demo_data.json` | demo data: the `b2_tf` dataset of the artifact (40 examples = 2 units × 20 prompts), 4.3 MB |", " | `build_mini_demo_data.py` | rebuilds `mini_demo_data.json` from the artifact folder |", " | `figures/` | figures written by the executed notebook: `F3_b2_singles_by_layer`, `F4_b2_residual_swaps`, `F5_b2_random_null`, `F8_b2_geometry_pca_demo` (PDF + PNG), `summary_b2.png` |", "-| `.aii/manifest.yaml` | keep / delete decisions for the pipeline's storage checker |", "+| `.aii/manifest.yaml` | storage decisions for the pipeline's checker: empty, since every file here is text, code or below the 10 MB floor |", " ", " Running the notebook also writes `results/` and `logs/` in its working directory. These hold the per-prompt rows it", " writes back into the original layout, `b2_summary.json`, `rederive.json` and loguru logs. They are not shipped,"]}], "userModified": false, "replaceAll": false}
````

### [200] TOOL CALL — Bash · 2026-10-26 14:54:52 UTC

```
Verify manifest and check for heavy paths:
/tmp/aii_nb_test_envs/art_cDba8_DycUJd-e339753424ba/bin/python -c "import yaml; print(yaml.safe_load(open('.aii/manifest.yaml')))"; find . -size +10M -not -name '.repl_agent.ptylog' -print; find . -type d \( -name '__pycache__' -o -name '.venv' -o -name '*cache*' -o -name 'node_modules' -o -name 'checkpoints' -o -name 'wandb' \) -print; grep -n "manifest\|Restoring" README.md
```

### [201] TOOL RESULT — Bash · 2026-10-26 14:54:52 UTC

```
{"stdout": "{'entries': []}\n44:| `.aii/manifest.yaml` | storage decisions for the pipeline's checker: empty, since every file here is text, code or below the 10 MB floor |\n150:## Restoring removed files\n152:No path in this folder is marked `delete` in `.aii/manifest.yaml`, so nothing needs restoring.", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [202] ASSISTANT · 2026-10-26 14:54:55 UTC

```
I fixed the manifest error by emptying `.aii/manifest.yaml` to `entries: []`. The three entries I had written (`mini_demo_data.json`, `code_demo.ipynb`, `figures/`) were for files that never need a decision.

Nothing in the folder needs a decision. Apart from the pipeline's own log file, no file is over 10 MB and there are no cache directories. The largest file is `mini_demo_data.json` at 4.3 MB, and it is plain text.

In `README.md` I updated the line describing the manifest to say it is empty and why. The "Restoring removed files" section still says nothing is marked delete, which stays true.

The notebook, demo data and struct output file are unchanged.
```
