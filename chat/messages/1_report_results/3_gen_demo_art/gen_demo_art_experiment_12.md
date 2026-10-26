# gen_demo_art_experiment_12 — report_results

> Phase: `gen_paper_repo` · `gen_demo_art`
> Run: `gen_paper_repo_c164ac661673` — A Random Activation Push Changes a Code Model's Algorithm Where Temperature Does Not
>
> Full, verbatim transcript of this agent task — every system/user prompt, assistant response, thinking block, tool call and tool result — in the order they occurred. Nothing truncated.

## Task: `gen_demo_art_experiment_12` (terminal_claude_agent, claude-opus-5-5)

### [1] CONFIG · 2026-10-26 09:49:19 UTC

```
model: Claude Opus 5.5 | effort: max | permission: bypassPermissions
```

### [2] SYSTEM-USER prompt · 2026-10-26 09:49:29 UTC

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
Your workspace: `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX`

CRITICAL: Every file you create, write, or save MUST be inside this workspace directory (subdirectories OK). You MUST NOT write files anywhere outside this path — external paths are READ-ONLY. Use absolute paths for all file operations.

EVERY file write MUST start with `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/`:
GOOD: `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/file.py`, `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/results/out.json`
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
id: art_3iv5G76C3yoX
type: experiment
title: Reading a coding ban inside Qwen3-8B
summary: >-
  Descriptive readout artifact on Qwen3-8B (bf16 states; FP8 twin for vLLM generation) for the iteration-1 path-search tasks
  under a ban on the modal algorithm (T1 grid: BFS banned; T2 weighted: Dijkstra banned). Provides method_out.json (exp_gen_sol_out,
  4 datasets, 1,122 examples: 200-run protocol-v2 fresh ban pool with per-run exp3-fitted readout predictions (SAE top-1/top-20
  latents vs DiM / raw logistic / top-20-neuron baselines), 480 same-seed CRN rows, 10 thinking traces, 432 thought-anchor
  continuations) and per-readout JSON in results/. KEY RESULTS: (1) Fresh pool banned share T1 0.15 (W4 template 15/20 BFS,
  others 0/20), T2 0.13; labeller re-check 0.965; commit locator 20/20. (2) Qwen-Scope SAE (W64K, k=50) base->instruct transfer
  test FAILS at L15/L20/L27 (dCE ratio 3.29/1.95/1.59 > 1.5) -> all latent results flagged out-of-distribution; DiM leads.
  (3) Discovery on exp3 states (nested LOPO + 200 within-paraphrase permutations + max-stat null): T2 decodable at k_pre/k16
  by every method (within-paraphrase AUC 0.67-0.86, p<=0.025); T1 not decodable within paraphrase; SAE latents never beat
  DiM/neurons beyond CIs. Positive control weak: exp3's commit token is the ' deque' import for most rows of both classes.
  (4) Replication on the fresh pool: exp3-fitted DiM transfers best (T1 within-template AUC 0.93-1.00, only W4 has both classes;
  T2 0.66-0.76); single top latent fails (0.27-0.80); shuffled-label placebo ~0.50. (5) Attention: same ban-specific heads
  on both tasks (L21H17, L26H21, L26H25; +0.21/+0.10 attention mass to the ban segment vs the token-matched neutral twin),
  focused on the banned name tokens; T1 compliant runs attend more (p=0.0025, within W4). (6) Prime-veto pattern absent in
  6/6 configs; at L27 NAME(X) and IMPL(X) latents are lower at k_pre under the ban than under both twins for the same text.
  (7) Thought anchors: T1 thinking runs 8.4-9.3k tokens (0/5 within the 8,192 cap) and DFS is fixed at the first resample
  point (D_0=1.0 in 4/4); T2 1 anchor in 32 sentences; early-label validity 13/16. (8) Same-seed CRN: ideas do not change
  with temperature (0/30 in 10/12 cells), so same- vs different-seed idea agreement is identical; phrasing changes less within
  a seed (e.g. 0.55 vs 0.76). (9) J-lens (community lens) fails its gate vs the logit lens (L27 top-1 0.104 vs 0.291); NLA
  not available for Qwen3-8B (dated 2026-10-20). Headlines re-derived independently (69 checks, 0 mismatches; float64 sensitivity
  noted). Kept on the run volume: results/tensors/ (E2 states, attention masses, SAE context codes). Deviations: results/deviations.json;
  not run: Gumbel-max sensitivity, E6, NLA.
workspace_path: >-
  /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_12
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
Raw data URL: https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-2/experiment-12/demo/mini_demo_data.json

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
GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-2/experiment-12/demo/mini_demo_data.json"
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
To test-run the notebook in a clean environment (simulating Colab), use the disposable venv at `/tmp/aii_nb_test_envs/art_3iv5G76C3yoX-2eaf8ea929eb`. It is on this machine's local disk, outside your workspace, which is on a slow network volume: never create a venv inside your workspace.
```bash
UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_3iv5G76C3yoX-2eaf8ea929eb
UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_3iv5G76C3yoX-2eaf8ea929eb/bin/python jupyter ipykernel
/tmp/aii_nb_test_envs/art_3iv5G76C3yoX-2eaf8ea929eb/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb
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
TODO 6. Verify: (1) code_demo.ipynb contains GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-2/experiment-12/demo/mini_demo_data.json" exactly, (2) mini_demo_data.json exists, (3) uses GitHub URL pattern not just open('mini_demo_data.json').
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

### [3] ASSISTANT · 2026-10-26 09:49:47 UTC

```
I'll start by loading the required skills and inspecting the workspace and artifact directory in parallel.
```

### [4] TOOL CALL — Skill · 2026-10-26 09:49:47 UTC

```
aii-colab
```

### [5] TOOL CALL — Skill · 2026-10-26 09:49:47 UTC

```
aii-long-running-tasks
```

### [6] TOOL RESULT — Skill · 2026-10-26 09:49:47 UTC

```
{"success": true, "commandName": "aii-colab"}
```

### [7] TOOL RESULT — Skill · 2026-10-26 09:49:47 UTC

```
{"success": true, "commandName": "aii-long-running-tasks"}
```

### [8] TOOL CALL — Bash · 2026-10-26 09:49:47 UTC

```
List workspace and artifact directory contents:
ls -la && ls -la .aii 2>/dev/null; echo "---"; git -C . log --oneline | head -5; echo "---ART---"; ls -la /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_12 2>&1 | head -50
```

### [9] TOOL RESULT — Bash · 2026-10-26 09:49:49 UTC

```
{"stdout": "total 2975\ndrwxrwxrwx 3 aii-agent aii-agent 1003885 Oct 26 09:49 .\ndrwxrwxrwx 9 aii-agent aii-agent 2000960 Oct 26 09:48 ..\ndrwxrwxrwx 2 aii-agent aii-agent       1 Oct 26 09:48 .aii\n-rw-rw-rw- 1 aii-agent aii-agent      54 Oct 26 09:49 .aii_claude_session.json\n-rw-rw-rw- 1 aii-agent aii-agent   40324 Oct 26 09:49 .repl_agent.ptylog\ntotal 981\ndrwxrwxrwx 2 aii-agent aii-agent       1 Oct 26 09:48 .\ndrwxrwxrwx 3 aii-agent aii-agent 1003885 Oct 26 09:49 ..\n---\nfatal: not a git repository (or any parent up to mount point /ai-inventor)\nStopping at filesystem boundary (GIT_DISCOVERY_ACROSS_FILESYSTEM not set).\n---ART---\ntotal 23569\ndrwxrwxrwx 10 aii-agent aii-agent 2022595 Oct 20 17:00 .\ndrwxrwxrwx  9 aii-agent aii-agent 3000146 Oct 20 04:59 ..\ndrwxrwxrwx  2 aii-agent aii-agent 1000169 Oct 20 15:12 .aii\n-rw-rw-rw-  1 aii-agent aii-agent      54 Oct 20 10:55 .aii_claude_session.json\n-rw-rw-rw-  1 aii-agent aii-agent    8291 Oct 20 15:12 .aii_worker_result.json\n-rw-rw-rw-  1 aii-agent aii-agent 1066458 Oct 20 15:12 .repl_agent.ptylog\n-rw-rw-rw-  1 aii-agent aii-agent    3257 Oct 20 14:47 .terminal_claude_agent_struct_out.json\n-rw-rw-rw-  1 aii-agent aii-agent   12551 Oct 20 15:06 README.md\n-rw-rw-rw-  1 aii-agent aii-agent    4422 Oct 20 14:47 TODO.md\ndrwxrwxrwx  2 aii-agent aii-agent 1080514 Oct 20 14:13 figures\n-rw-rw-rw-  1 aii-agent aii-agent 2996647 Oct 20 14:31 full_method_out.json\ndrwxrwxrwx  5 aii-agent aii-agent 2000744 Oct 20 03:54 inputs\ndrwxrwxrwx  2 aii-agent aii-agent 1022699 Oct 20 14:52 logs\n-rw-rw-rw-  1 aii-agent aii-agent    4157 Oct 20 14:07 method.py\n-rw-rw-rw-  1 aii-agent aii-agent 2625833 Oct 20 14:27 method_out.json\n-rw-rw-rw-  1 aii-agent aii-agent 1256780 Oct 20 14:31 mini_method_out.json\n-rw-rw-rw-  1 aii-agent aii-agent  933489 Oct 20 14:31 preview_method_out.json\ndrwxrwxrwx  2 aii-agent aii-agent 1034239 Oct 20 04:09 prompts\n-rw-rw-rw-  1 aii-agent aii-agent    4995 Oct 20 13:48 pyproject.toml\n-rw-rw-rw-  1 aii-agent aii-agent    8487 Oct 20 14:40 reproducibility.md\ndrwxrwxrwx  4 aii-agent aii-agent 2020844 Oct 20 14:27 results\ndrwxrwxrwx  2 aii-agent aii-agent 1021482 Oct 20 17:00 src\ndrwxrwxrwx  2 aii-agent aii-agent 1000133 Oct 20 11:44 tools", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [10] ASSISTANT · 2026-10-26 09:49:57 UTC

```
Skills loaded. Now let me read the artifact's demo file (`method.py`) and supporting docs.
```

### [11] TOOL CALL — Bash · 2026-10-26 09:49:57 UTC

```
Read method.py and list artifact subdirectories:
cd /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_12 && cat method.py; echo "=====SRC====="; ls -la src tools results figures logs inputs prompts | head -150
```

### [12] TOOL RESULT — Bash · 2026-10-26 09:49:57 UTC

```
{"stdout": "#!/usr/bin/env python3\n\"\"\"Reading a coding ban inside the model (Qwen3-8B, protocol v2): orchestrator.\n\nEvery stage runs as its own process (vLLM and HF never share the 16 GB GPU):\n  uv run method.py --stage A        # inputs check, labeller re-check (A1, A2), prompts (A3), 0e record (A4)\n  uv run method.py --stage B        # layer probe + SAE readout (i) discovery on exp3 states (CPU)\n  uv run method.py --stage vllm1    # C1 fresh ban pool + E5 same-seed CRN + Gumbel + determinism (GPU, vLLM)\n  uv run method.py --stage vllm2    # C2-C4 thought-anchor traces, resampling, validation completions (GPU, vLLM)\n  uv run method.py --stage label    # canonical labeller on every generation; commit locator (CPU)\n  uv run method.py --stage hf       # E1 transfer test, E2 fresh-pool states + attention, E4 J-lens (GPU, HF)\n  uv run method.py --stage analyse  # D1, D2, E3 readouts, figures (CPU)\n  uv run method.py --stage anchors  # D1 thought-anchor analysis only (CPU; also part of 'analyse')\n  uv run method.py --stage final    # A2 labeller check, fresh-pool + same-seed summaries, 0e record, method_out.json\n  uv run method.py --stage figures  # figures/*.png|pdf from results/*.json (CPU)\n  uv run method.py --stage verify   # independent re-derivation of headline numbers + placebo checks (CPU)\nBaselines are implemented side by side with each readout (DiM, raw logistic probe, top-20 raw dimensions,\ndifferent-seed CRN baseline, logit lens), on identical folds/rows.\n\"\"\"\n\nfrom __future__ import annotations\n\nimport os\n\n# The cgroup quota is ~5 CPUs while os.cpu_count() reports 48 host cores: cap every BLAS / OpenMP pool\n# BEFORE numpy/torch load, or the oversubscribed thread pools are throttled ~100x.\nfor _v in (\"OMP_NUM_THREADS\", \"OPENBLAS_NUM_THREADS\", \"MKL_NUM_THREADS\", \"NUMEXPR_NUM_THREADS\"):\n    os.environ.setdefault(_v, \"4\")\nos.environ.setdefault(\"CC\", os.path.join(os.path.dirname(os.path.abspath(__file__)), \"tools\", \"zigcc\"))\n\nimport argparse\nimport sys\nfrom pathlib import Path\n\nsys.path.insert(0, str(Path(__file__).resolve().parent / \"src\"))\n\nfrom loguru import logger  # noqa: E402\n\nfrom core import setup_logging  # noqa: E402\n\n\n@logger.catch(reraise=True)\ndef main() -> None:\n    ap = argparse.ArgumentParser()\n    ap.add_argument(\"--stage\", required=True)\n    ap.add_argument(\"--smoke\", action=\"store_true\")\n    ap.add_argument(\"--n\", type=int, default=None)\n    ap.add_argument(\"--part\", default=\"traces\", help=\"vllm2 sub-stage: traces | resample | complete\")\n    args = ap.parse_args()\n    setup_logging(f\"stage_{args.stage}\")\n    logger.info(f\"stage {args.stage} (smoke={args.smoke})\")\n    if args.stage == \"A\":\n        from stage_a import run_stage_a\n\n        run_stage_a()\n    elif args.stage == \"B\":\n        from readout_i import run_stage_b\n\n        run_stage_b()\n    elif args.stage == \"vllm1\":\n        from vllm_stage import session1\n\n        session1(n_per_template=args.n or int(os.environ.get('C1_PER_TEMPLATE', 20)),\n                 n_seeds=int(os.environ.get('CRN_SEEDS_N', 30)), gumbel_seeds=int(os.environ.get('GUMBEL_SEEDS_N', 0)),\n                 smoke=args.smoke)\n    elif args.stage == \"vllm2\":\n        from anchors_stage import session2\n\n        session2(part=args.part, n=args.n, smoke=args.smoke)\n    elif args.stage == \"label\":\n        from labelling import run_stage_label\n\n        run_stage_label()\n    elif args.stage == \"hf\":\n        from hf_stage import run_stage_hf\n\n        run_stage_hf(smoke=args.smoke)\n    elif args.stage == \"analyse\":\n        from analysis import run_stage_analyse\n\n        run_stage_analyse()\n    elif args.stage == \"anchors\":\n        from analysis import thought_anchors\n\n        thought_anchors()\n    elif args.stage == \"figures\":\n        from figures import run_figures\n\n        run_figures()\n    elif args.stage == \"verify\":\n        import runpy\n\n        runpy.run_path(str(Path(__file__).resolve().parent / \"src\" / \"verify_headlines.py\"), run_name=\"__main__\")\n    elif args.stage == \"final\":\n        from final import run_stage_final\n\n        run_stage_final()\n    else:\n        raise SystemExit(f\"unknown stage {args.stage}\")\n\n\nif __name__ == \"__main__\":\n    main()\n=====SRC=====\nfigures:\ntotal 3840\ndrwxrwxrwx  2 aii-agent aii-agent 1080514 Oct 20 14:13 .\ndrwxrwxrwx 10 aii-agent aii-agent 2022595 Oct 20 17:00 ..\n-rw-rw-rw-  1 aii-agent aii-agent   19160 Oct 20 14:44 fig_attention.pdf\n-rw-rw-rw-  1 aii-agent aii-agent   65261 Oct 20 14:44 fig_attention.png\n-rw-rw-rw-  1 aii-agent aii-agent   12760 Oct 20 14:44 fig_jlens.pdf\n-rw-rw-rw-  1 aii-agent aii-agent   43905 Oct 20 14:44 fig_jlens.png\n-rw-rw-rw-  1 aii-agent aii-agent   25316 Oct 20 14:44 fig_latent_vs_dim.pdf\n-rw-rw-rw-  1 aii-agent aii-agent  115412 Oct 20 14:44 fig_latent_vs_dim.png\n-rw-rw-rw-  1 aii-agent aii-agent   20616 Oct 20 14:44 fig_layer_probe.pdf\n-rw-rw-rw-  1 aii-agent aii-agent  157562 Oct 20 14:44 fig_layer_probe.png\n-rw-rw-rw-  1 aii-agent aii-agent   12770 Oct 20 14:44 fig_prime_veto.pdf\n-rw-rw-rw-  1 aii-agent aii-agent   51422 Oct 20 14:44 fig_prime_veto.png\n-rw-rw-rw-  1 aii-agent aii-agent   22953 Oct 20 14:44 fig_same_seed.pdf\n-rw-rw-rw-  1 aii-agent aii-agent  110413 Oct 20 14:44 fig_same_seed.png\n-rw-rw-rw-  1 aii-agent aii-agent   23208 Oct 20 14:44 fig_thought_anchors.pdf\n-rw-rw-rw-  1 aii-agent aii-agent   90627 Oct 20 14:44 fig_thought_anchors.png\n-rw-rw-rw-  1 aii-agent aii-agent   12354 Oct 20 14:44 fig_transfer.pdf\n-rw-rw-rw-  1 aii-agent aii-agent   40730 Oct 20 14:44 fig_transfer.png\n\ninputs:\ntotal 7869\ndrwxrwxrwx  5 aii-agent aii-agent 2000744 Oct 20 03:54 .\ndrwxrwxrwx 10 aii-agent aii-agent 2022595 Oct 20 17:00 ..\ndrwxrwxrwx 11 aii-agent aii-agent 2000712 Oct 20 17:00 exp1\ndrwxrwxrwx  5 aii-agent aii-agent 1029587 Oct 20 03:57 exp3\ndrwxrwxrwx 11 aii-agent aii-agent 1003446 Oct 20 17:00 exp6\n\nlogs:\ntotal 3213\ndrwxrwxrwx  2 aii-agent aii-agent 1022699 Oct 20 14:52 .\ndrwxrwxrwx 10 aii-agent aii-agent 2022595 Oct 20 17:00 ..\n-rw-rw-rw-  1 aii-agent aii-agent       5 Oct 20 14:52 chain2_done.txt\n-rw-rw-rw-  1 aii-agent aii-agent      13 Oct 20 14:52 chain_done.txt\n-rw-rw-rw-  1 aii-agent aii-agent     981 Oct 20 14:52 download_base_jlens.log\n-rw-rw-rw-  1 aii-agent aii-agent       6 Oct 20 14:52 heavy_pids.txt\n-rw-rw-rw-  1 aii-agent aii-agent     163 Oct 20 14:52 memwatch.log\n-rw-rw-rw-  1 aii-agent aii-agent       6 Oct 20 14:52 memwatch.pid\n-rw-rw-rw-  1 aii-agent aii-agent     903 Oct 20 14:52 prompts.log\n-rw-rw-rw-  1 aii-agent aii-agent   36342 Oct 20 14:52 smoke_vllm1.out\n-rw-rw-rw-  1 aii-agent aii-agent   12658 Oct 20 14:52 stage_B.log\n-rw-rw-rw-  1 aii-agent aii-agent    5679 Oct 20 14:52 stage_B.out\n-rw-rw-rw-  1 aii-agent aii-agent    4272 Oct 20 14:52 stage_B2.out\n-rw-rw-rw-  1 aii-agent aii-agent    9701 Oct 20 14:52 stage_analyse.log\n-rw-rw-rw-  1 aii-agent aii-agent    9133 Oct 20 14:52 stage_analyse.out\n-rw-rw-rw-  1 aii-agent aii-agent     168 Oct 20 14:52 stage_anchors.log\n-rw-rw-rw-  1 aii-agent aii-agent      45 Oct 20 14:52 stage_anchors.out\n-rw-rw-rw-  1 aii-agent aii-agent       0 Oct 20 14:52 stage_cpu_early.log\n-rw-rw-rw-  1 aii-agent aii-agent    2484 Oct 20 14:52 stage_figures.log\n-rw-rw-rw-  1 aii-agent aii-agent     421 Oct 20 14:52 stage_figures.out\n-rw-rw-rw-  1 aii-agent aii-agent     421 Oct 20 14:52 stage_figures2.out\n-rw-rw-rw-  1 aii-agent aii-agent    4168 Oct 20 14:52 stage_final.log\n-rw-rw-rw-  1 aii-agent aii-agent     613 Oct 20 14:52 stage_final.out\n-rw-rw-rw-  1 aii-agent aii-agent     613 Oct 20 14:52 stage_final2.out\n-rw-rw-rw-  1 aii-agent aii-agent     613 Oct 20 14:52 stage_final3.out\n-rw-rw-rw-  1 aii-agent aii-agent   24136 Oct 20 14:52 stage_hf.log\n-rw-rw-rw-  1 aii-agent aii-agent    5368 Oct 20 14:52 stage_hf.out\n-rw-rw-rw-  1 aii-agent aii-agent    9225 Oct 20 14:52 stage_hf_smoke.out\n-rw-rw-rw-  1 aii-agent aii-agent   31040 Oct 20 14:52 stage_label.log\n-rw-rw-rw-  1 aii-agent aii-agent    1848 Oct 20 14:52 stage_label.out\n-rw-rw-rw-  1 aii-agent aii-agent    1476 Oct 20 14:52 stage_label2.out\n-rw-rw-rw-  1 aii-agent aii-agent    1442 Oct 20 14:52 stage_label3.out\n-rw-rw-rw-  1 aii-agent aii-agent    1639 Oct 20 14:52 stage_label4.out\n-rw-rw-rw-  1 aii-agent aii-agent     166 Oct 20 14:52 stage_verify.log\n-rw-rw-rw-  1 aii-agent aii-agent     103 Oct 20 14:52 stage_verify.out\n-rw-rw-rw-  1 aii-agent aii-agent   23312 Oct 20 14:52 stage_vllm1.log\n-rw-rw-rw-  1 aii-agent aii-agent   10115 Oct 20 14:52 stage_vllm1.out\n-rw-rw-rw-  1 aii-agent aii-agent    4463 Oct 20 14:52 stage_vllm2.log\n-rw-rw-rw-  1 aii-agent aii-agent    6752 Oct 20 14:52 stage_vllm2_complete.out\n-rw-rw-rw-  1 aii-agent aii-agent    7327 Oct 20 14:52 stage_vllm2_resample.out\n-rw-rw-rw-  1 aii-agent aii-agent   10424 Oct 20 14:52 stage_vllm2_traces.out\n-rw-rw-rw-  1 aii-agent aii-agent    4194 Oct 20 14:52 venv_setup.log\n\nprompts:\ntotal 3328\ndrwxrwxrwx  2 aii-agent aii-agent 1034239 Oct 20 04:09 .\ndrwxrwxrwx 10 aii-agent aii-agent 2022595 Oct 20 17:00 ..\n-rw-rw-rw-  1 aii-agent aii-agent  109997 Oct 20 04:04 noun_bank_cache.json\n-rw-rw-rw-  1 aii-agent aii-agent  240611 Oct 20 04:09 prompts_v2.json\n\nresults:\ntotal 28946\ndrwxrwxrwx  4 aii-agent aii-agent 2020844 Oct 20 14:27 .\ndrwxrwxrwx 10 aii-agent aii-agent 2022595 Oct 20 17:00 ..\n-rw-rw-rw-  1 aii-agent aii-agent     295 Oct 20 13:56 analysis_status.json\n-rw-rw-rw-  1 aii-agent aii-agent    6132 Oct 20 14:05 deviations.json\n-rw-rw-rw-  1 aii-agent aii-agent   48301 Oct 20 13:31 e2_meta.json\n-rw-rw-rw-  1 aii-agent aii-agent 1076112 Oct 20 14:21 eval_cache.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent    4942 Oct 20 14:27 fresh_pool_summary.json\n-rw-rw-rw-  1 aii-agent aii-agent 3567814 Oct 20 13:36 jlens.json\n-rw-rw-rw-  1 aii-agent aii-agent  219014 Oct 20 13:56 jlens_summary.json\n-rw-rw-rw-  1 aii-agent aii-agent   66700 Oct 20 12:28 judge_cache.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent  824641 Oct 20 14:21 labelled_c1.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent  602095 Oct 20 14:21 labelled_c2.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent 3366316 Oct 20 14:21 labelled_c3.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent  422046 Oct 20 14:21 labelled_c4.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent 1923755 Oct 20 14:21 labelled_crn.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent   39318 Oct 20 14:21 labelled_det.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent    8804 Oct 20 14:21 labelled_rep10.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent     297 Oct 20 14:27 labeller_check.json\n-rw-rw-rw-  1 aii-agent aii-agent  237742 Oct 20 13:56 latent_contexts.json\n-rw-rw-rw-  1 aii-agent aii-agent  101197 Oct 20 09:06 layer_probe.json\n-rw-rw-rw-  1 aii-agent aii-agent    2025 Oct 20 14:21 locator_check.json\n-rw-rw-rw-  1 aii-agent aii-agent    4374 Oct 20 14:27 nla_jlens_search.json\n-rw-rw-rw-  1 aii-agent aii-agent     540 Oct 20 14:05 not_run.json\n-rw-rw-rw-  1 aii-agent aii-agent   16107 Oct 20 13:31 prompt_only_meta.json\ndrwxrwxrwx  2 aii-agent aii-agent 2000612 Oct 20 14:15 raw\n-rw-rw-rw-  1 aii-agent aii-agent 7156287 Oct 20 12:21 readout_i_discovery.json\n-rw-rw-rw-  1 aii-agent aii-agent  200345 Oct 20 13:54 readout_i_replication.json\n-rw-rw-rw-  1 aii-agent aii-agent   83267 Oct 20 13:55 readout_ii_attention.json\n-rw-rw-rw-  1 aii-agent aii-agent  173847 Oct 20 13:55 readout_iii_prime_veto.json\n-rw-rw-rw-  1 aii-agent aii-agent    1610 Oct 20 12:16 sae_alignment.json\n-rw-rw-rw-  1 aii-agent aii-agent    1014 Oct 20 09:07 sae_alignment_v0_fvu_only.json\n-rw-rw-rw-  1 aii-agent aii-agent   18078 Oct 20 14:27 same_seed.json\n-rw-rw-rw-  1 aii-agent aii-agent 1247854 Oct 20 14:21 samples.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent     192 Oct 20 12:28 spend.json\ndrwxrwxrwx  2 aii-agent aii-agent 2018174 Oct 20 13:35 tensors\n-rw-rw-rw-  1 aii-agent aii-agent    6546 Oct 20 13:50 thought_anchor_boundaries.json\n-rw-rw-rw-  1 aii-agent aii-agent   18963 Oct 20 14:27 thought_anchors.json\n-rw-rw-rw-  1 aii-agent aii-agent    8502 Oct 20 14:27 timing.json\n-rw-rw-rw-  1 aii-agent aii-agent    2689 Oct 20 13:50 transfer_summary.json\n-rw-rw-rw-  1 aii-agent aii-agent  100715 Oct 20 13:42 transfer_test.json\n-rw-rw-rw-  1 aii-agent aii-agent   10213 Oct 20 14:27 verify_headlines.json\n\nsrc:\ntotal 3192\ndrwxrwxrwx  2 aii-agent aii-agent 1021482 Oct 20 17:00 .\ndrwxrwxrwx 10 aii-agent aii-agent 2022595 Oct 20 17:00 ..\n-rw-rw-rw-  1 aii-agent aii-agent   34362 Oct 20 13:30 analysis.py\n-rw-rw-rw-  1 aii-agent aii-agent   11365 Oct 20 12:11 anchors_stage.py\n-rw-rw-rw-  1 aii-agent aii-agent   10726 Oct 20 04:03 core.py\n-rw-rw-rw-  1 aii-agent aii-agent    7781 Oct 20 13:58 early_label.py\n-rw-rw-rw-  1 aii-agent aii-agent    9556 Oct 20 14:44 figures.py\n-rw-rw-rw-  1 aii-agent aii-agent   26483 Oct 20 14:12 final.py\n-rw-rw-rw-  1 aii-agent aii-agent   35442 Oct 20 13:25 hf_stage.py\n-rw-rw-rw-  1 aii-agent aii-agent   15791 Oct 20 04:13 labelling.py\n-rw-rw-rw-  1 aii-agent aii-agent   10864 Oct 20 04:08 prompts.py\n-rw-rw-rw-  1 aii-agent aii-agent   32741 Oct 20 12:08 readout_i.py\n-rw-rw-rw-  1 aii-agent aii-agent   11505 Oct 20 14:27 verify_headlines.py\n-rw-rw-rw-  1 aii-agent aii-agent   13368 Oct 20 09:05 vllm_stage.py\n\ntools:\ntotal 2955\ndrwxrwxrwx  2 aii-agent aii-agent 1000133 Oct 20 11:44 .\ndrwxrwxrwx 10 aii-agent aii-agent 2022595 Oct 20 17:00 ..\n-rwxrwxrwx  1 aii-agent aii-agent    1139 Oct 20 12:54 memwatch.sh\n-rwxrwxrwx  1 aii-agent aii-agent     229 Oct 20 04:30 zigcc", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [13] TOOL CALL — Bash · 2026-10-26 09:49:57 UTC

```
Read artifact README, reproducibility notes and struct output:
cd /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_12 && cat README.md; echo "=====REPRO====="; cat reproducibility.md; echo "=====STRUCT====="; cat .terminal_claude_agent_struct_out.json
```

### [14] TOOL RESULT — Bash · 2026-10-26 09:49:57 UTC

```
{"stdout": "# Reading a coding ban inside the model (Qwen3-8B)\n\nA **descriptive** readout study of what happens inside Qwen3-8B when a coding prompt forbids the model's default\nalgorithm. Two tasks come from the canonical iteration-1 suite: T1 grid path, where BFS is banned, and T2 weighted\nshortest path, where Dijkstra is banned. Every readout sits next to a matched baseline on identical rows and folds.\nNothing here is a confirmatory test.\n\n| Arm | What ran | Baseline(... [truncated, 24869 chars total]
```

### [15] THINKING · 2026-10-26 09:50:11 UTC

```
I see that `method.py` orchestrates GPU stages (vLLM, HF Qwen3-8B) alongside CPU analysis stages in `src/`. I'll now inspect the data structure and CPU-side source files to figure out what fits within a 10-minute CPU notebook.
```

### [16] TOOL CALL — Bash · 2026-10-26 09:50:11 UTC

```
Inspect structure of preview output JSON:
cd /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_12 && python3 - <<'EOF'
import json
d = json.load(open("preview_method_out.json"))
print(type(d), list(d.keys()) if isinstance(d, dict) else len(d))
def show(o, depth=0, maxd=3, key=""):
    pad = "  "*depth
    if isinstance(o, dict):
        print(f"{pad}{key} dict({len(o)}) keys={list(o.keys())[:40]}")
        if depth < maxd:
            for k,v in list(o.items())[:40]:
                show(v, depth+1, maxd, k)
    elif isinstance(o, list):
        print(f"{pad}{key} list({len(o)})")
        if o and depth < maxd:
            show(o[0], depth+1, maxd, key+"[0]")
    else:
        s = repr(o)
        print(f"{pad}{key} = {s[:150]}")
show(d, maxd=2)
print("====")
for ds in d.get("datasets", []):
    print("DATASET", ds.get("dataset"), "n_examples", len(ds.get("examples", [])))
    if ds.get("examples"):
        ex = ds["examples"][0]
        for k, v in ex.items():
            print("   ", k, "=", repr(v)[:300])
EOF
```

### [17] TOOL RESULT — Bash · 2026-10-26 09:50:11 UTC

```
{"stdout": "<class 'dict'> ['metadata', 'datasets']\n dict(2) keys=['metadata', 'datasets']\n  metadata dict(23) keys=['method_name', 'artifact_id', 'date', 'description', 'models', 'deviations', 'fresh_pool_summary', 'same_seed', 'readout_i_discovery', 'record_0e', 'transfer_test', 'readout_i_replication', 'readout_ii_attention', 'readout_iii_prime_veto', 'jlens', 'thought_anchors', 'latent_contexts', 'labeller_check', 'locator_check', 'headline_verification', 'timing', 'spend', 'not_run']\n    method_name = 'Reading a coding ban inside the model (descriptive readouts, Qwen3-8B)'\n    artifact_id = 'gen_plan_experiment_6_idx7'\n    date = '2026-10-20'\n    description = 'SAE latent readouts vs DiM / raw logistic / top-20-neuron baselines (discovery on exp3 states, replication on a fresh protocol-v2 ban pool), base->in\n    models dict(3) keys=['generation', 'states', 'sae']\n    deviations list(3)\n    fresh_pool_summary dict(2) keys=['n_runs', 'per_task']\n    same_seed dict(6) keys=['coupling', 'n_rows', 'seeds', 'cells', 'determinism_rerun', 'step0_identical_history_check']\n    readout_i_discovery dict(5) keys=['layer_choice', 'confounds', 'sae_alignment', 'configs', 'controls']\n    record_0e dict(4) keys=['date', 'recorded_utc', 'NLA', 'J_LENS']\n    transfer_test dict(7) keys=['rule', 'ce_clean_inst', 'ce_clean_base', 'layers', 'splice_sanity', 'eager_check', 'n_pass']\n    readout_i_replication dict(2) keys=['configs', 'class_counts']\n    readout_ii_attention dict(2) keys=['note', 'tasks']\n    readout_iii_prime_veto dict(3) keys=['pattern', 'configs', 'attended_token_latents']\n    jlens dict(3) keys=['gate', 'fresh_by_class', 'R']\n    thought_anchors dict(5) keys=['traces', 'completion', 'validity', 'pooled_max_tvd_sentence_category', 'pooled_anchor_category']\n    latent_contexts dict(2) keys=['note', 'layers']\n    labeller_check dict(5) keys=['n_gold_resolved', 'combined_vs_adjudicated_agreement', 'pass_0.9', 'references_100pct_exp1_gate_report', 'note']\n    locator_check dict(4) keys=['n', 'n_match', 'pass', 'rows']\n    headline_verification dict(4) keys=['mismatches', 'checks', 'n_checks', 'n_mismatches']\n    timing dict(2) keys=['stages', 'gpu_hours_total']\n    spend dict(6) keys=['cap_usd', 'total_usd', 'by_purpose', 'n_calls', 'budget_refusals', 'updated_utc']\n    not_run list(3)\n  datasets list(3)\n    datasets[0] dict(2) keys=['dataset', 'examples']\n====\nDATASET fresh_ban_pool_protocol_v2 n_examples 3\n    input = 'Do not use breadth-first search (BFS) for this task.\\n\\nTask: write a Python function solve(grid, start, goal) that finds a path between two cells of a grid. grid is a list of equal-length strings with ...'\n    output = 'dfs'\n    metadata_task = 't1'\n    metadata_template = 'W1'\n    metadata_seed = 20261020\n    metadata_model = 'Qwen/Qwen3-8B-FP8'\n    metadata_decoding = 'T1.0_topp1.0_topk-off_max1024_thinkoff'\n    metadata_passed = False\n    metadata_labeller_source = 'agree'\n    metadata_commit_idx = 127\n    metadata_evidence_term = 'stack'\n    metadata_negated_first_mention = False\n    metadata_code_sha256 = '0a1bb728dd1717b50e57e29e291a9160f09ac32ae5b4a0d376c33c4e0ba63eb2'\n    metadata_n_gen_tokens = 258\n    metadata_readout_layer = 27\n    metadata_readout_scores_k_pre = {'sae_top1': 0.0, 'sae_top20_lr': -2.91774, 'raw_dim': -96.76024, 'raw_lr': -1.55828, 'neuron_top20_lr': -2.1112, 'neuron_top1': 3.32812, 'sae_code_dim': -64.36372}\n    predict_sae_top20_latents_exp3_fitted = 'dfs'\n    predict_sae_top1_latent_exp3_fitted = 'dfs'\n    predict_dim_baseline_exp3_fitted = 'dfs'\n    predict_raw_logistic_baseline_exp3_fitted = 'dfs'\n    predict_top20_neurons_baseline_exp3_fitted = 'dfs'\n    predict_banned_label = 'bfs'\nDATASET same_seed_crn n_examples 3\n    input = 'Please solve the following programming task.\\n\\nTask: write a Python function solve(grid, start, goal) that finds a path between two cells of a grid. grid is a list of equal-length strings with between ...'\n    output = 'bfs'\n    metadata_task = 't1'\n    metadata_condition = 'baseline'\n    metadata_seed = 0\n    metadata_T = 0.3\n    metadata_coupling = 'icdf_top10'\n    metadata_model = 'Qwen/Qwen3-8B-FP8'\n    metadata_passed = False\n    metadata_labeller_source = 'agree'\n    metadata_code_sha256 = '0cf9aa85cbbbe8acd3d6b8825d5218d6947f09727d77c34c666cf2aac43de14a'\n    metadata_n_gen_tokens = 245\n    predict_same_seed_T03 = 'bfs'\n    predict_different_seed_modal_T03 = 'bfs'\nDATASET thought_anchor_base_traces n_examples 3\n    input = 'Do not use breadth-first search (BFS) for this task.\\n\\nTask: write a Python function solve(grid, start, goal) that finds a path between two cells of a grid. grid is a list of equal-length strings with ...'\n    output = 'dfs'\n    metadata_task = 't1'\n    metadata_trace_id = 0\n    metadata_seed = 7000\n    metadata_complete_within_8192 = False\n    metadata_think_close_idx = 9264\n    metadata_n_gen_tokens = 9522\n    metadata_passed = False\n    metadata_decoding = 'T0.6_topp0.95_topk20_max9600_thinkon'\n    metadata_resampled = True\n    predict_early_label_of_thinking = 'dfs'", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [18] ASSISTANT · 2026-10-26 09:50:33 UTC

```
The data has 4 datasets with per-row labels and readout scores. Let me survey the CPU-side source (function overview first) to find which original code can run on the stored data.
```

### [19] TOOL CALL — Bash · 2026-10-26 09:50:33 UTC

```
List functions and imports in source modules:
cd /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_12/src && for f in core.py final.py analysis.py verify_headlines.py figures.py labelling.py early_label.py readout_i.py; do echo "=== $f ($(wc -l < $f) lines)"; grep -nE "^(def |class |[A-Z_]+ *=|from |import )" $f | head -60; done
```

### [20] TOOL RESULT — Bash · 2026-10-26 09:50:33 UTC

```
{"stdout": "=== core.py (286 lines)\n9:from __future__ import annotations\n11:import hashlib\n12:import importlib.util\n13:import json\n14:import math\n15:import os\n16:import sys\n17:import threading\n18:import time\n19:from datetime import datetime, timezone\n20:from pathlib import Path\n21:from types import ModuleType\n22:from typing import Any, Iterable\n24:from loguru import logger\n26:ROOT = Path(__file__).resolve().parent.parent\n27:SRC = ROOT / \"src\"\n28:RESULTS = ROOT / \"results\"\n29:FIGS = ROOT / \"figures\"\n30:LOGS = ROOT / \"logs\"\n31:INPUTS = ROOT / \"inputs\"\n32:PROMPTS_DIR = ROOT / \"prompts\"\n33:TENSORS = RESULTS / \"tensors\"\n41:RUNS_DIR = ROOT.parents[4]\n45:DATASET_SRC = ITER1 / \"gen_art_dataset_1\"\n48:MODEL_HF = \"Qwen/Qwen3-8B\"            # bf16 weights: every state / attention / CE readout\n49:MODEL_GEN = \"Qwen/Qwen3-8B-FP8\"       # official block-FP8 checkpoint: every vLLM generation (16 GB GPU)\n50:MODEL_BASE = \"Qwen/Qwen3-8B-Base\"     # SAE training model, for the transfer test\n51:SAE_REPO = \"Qwen/SAE-Res-Qwen3-8B-Base-W64K-L0_50\"\n52:SAE_K = 50\n53:JLENS_REPO = \"senku21x/cot-oracle-jlens\"\n54:JLENS_GIT = \"https://github.com/anthropics/jacobian-lens\"\n56:TASKS = (\"t1\", \"t2\")\n61:BANNED = {\"t1\": \"bfs\", \"t2\": \"dijkstra\"}           # X: the modal approach that the ban names\n62:SUBSTITUTE = {\"t1\": \"dfs\", \"t2\": \"bf_spfa\"}        # X': the main natural substitute under the ban\n63:X_NAME = {\"t1\": \"breadth-first search (BFS)\", \"t2\": \"Dijkstra\" + chr(39) + \"s algorithm\"}\n64:XSUB_NAME = {\"t1\": \"depth-first search (DFS)\", \"t2\": \"Bellman-Ford or SPFA\"}\n76:TEMPLATE_IDS = list(TEMPLATES)\n79:SEED_FRESH = 20261020        # fresh pool: 20261020 + i\n80:SEED_TRACE = 7000            # thinking base traces: 7000 + i\n81:SEED_CONT = 9000             # continuations: 9000 + trace*1000 + boundary*10 + j\n82:CRN_SEEDS = list(range(50))\n83:CRN_TEMPS = (0.3, 0.7, 1.0, 1.3)\n84:GUMBEL_SEED_OFFSET = 10 ** 6\n86:THINK_DECODING = dict(temperature=0.6, top_p=0.95, top_k=20)  # Qwen3 recommended thinking settings (D06)\n87:MAIN_DECODING = dict(temperature=1.0, top_p=1.0, top_k=-1)      # protocol thinking-off decoding\n89:OPENROUTER_CAP_USD = 0.30\n90:BUDGET_MSG = \"AI Inventor per-run OpenRouter budget\"\n91:JUDGE_MODEL = \"openai/gpt-4.1-mini\"  # exp1's canonical judge\n94:def setup_logging(name: str) -> None:\n101:def utc_now() -> str:\n105:def sha256_text(s: str) -> str:\n109:def sha256_file(p: Path, chunk: int = 1 << 24) -> str:\n120:def _json_default(o: Any) -> Any:\n138:def _clean_nan(o: Any) -> Any:\n148:def write_json(p: Path, obj: Any, indent: int | None = 1) -> None:\n157:def read_json(p: Path, default: Any = None) -> Any:\n164:def read_jsonl(p: Path) -> list[dict[str, Any]]:\n180:def write_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:\n189:def append_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:\n195:def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float | None, float | None]:\n=== final.py (442 lines)\n5:from __future__ import annotations\n7:import json\n8:from collections import Counter, defaultdict\n9:from typing import Any\n11:import numpy as np\n12:from loguru import logger\n14:from core import (BANNED, CRN_TEMPS, EXP6, MODEL_GEN, MODEL_HF, RESULTS, ROOT, SAE_REPO, TASKS, TEMPLATE_IDS, Timer,\n17:UNRES = {\"no_code\", \"unresolved\", None}\n18:THETAS = (0.7, 0.8, 0.9)\n21:def fresh_pool_summary() -> dict[str, Any]:\n47:def _metrics_mod():\n51:def _jacc(a: frozenset | None, b: frozenset | None) -> float | None:\n58:def same_seed_analysis() -> dict[str, Any]:\n187:def discovery_summary() -> dict[str, Any]:\n216:def nla_jlens_record() -> dict[str, Any]:\n258:def _readout_predictions() -> dict[tuple, dict[str, Any]]:\n273:def method_out(fresh: dict[str, Any], crn: dict[str, Any], disc: dict[str, Any], j0e: dict[str, Any]) -> None:\n376:def _strip_scores(R: Any) -> Any:\n385:def _strip_heatmaps(A: Any) -> Any:\n394:def labeller_check() -> dict[str, Any]:\n423:def run_stage_final() -> None:\n=== analysis.py (598 lines)\n17:from __future__ import annotations\n19:import gc\n20:from collections import Counter, defaultdict\n21:from typing import Any\n23:import numpy as np\n24:from loguru import logger\n25:from scipy.stats import binomtest\n27:from core import BANNED, RESULTS, SUBSTITUTE, TASKS, TEMPLATE_IDS, TENSORS, Timer, read_json, read_jsonl, write_json\n29:UNRES = {\"no_code\", \"unresolved\", None}\n30:CONDS = [\"ban\", \"mention\", \"neutral\"]\n31:N_BOOT = 2000\n34:def _labels() -> dict[tuple, dict[str, Any]]:\n38:def _boot_runs(y: np.ndarray, s: np.ndarray, g: np.ndarray, n_boot: int = N_BOOT, seed: int = 3) -> dict[str, Any]:\n56:def _codes(H: np.ndarray, S: dict[str, np.ndarray]) -> np.ndarray:\n64:def readout_i_replication() -> dict[str, Any]:\n145:def readout_ii_attention() -> dict[str, Any]:\n245:def readout_iii_prime_veto(attn: dict[str, Any] | None = None) -> dict[str, Any]:\n373:def latent_contexts(n_ctx: int = 10, width: int = 12) -> dict[str, Any]:\n424:def transfer_summary() -> dict[str, Any]:\n453:def jlens_summary() -> dict[str, Any]:\n479:def thought_anchors() -> dict[str, Any]:\n577:def run_stage_analyse() -> None:\n=== verify_headlines.py (217 lines)\n9:from __future__ import annotations\n11:import json\n12:import sys\n13:from pathlib import Path\n15:import numpy as np\n16:import pandas as pd\n17:from sklearn.metrics import roc_auc_score\n19:ROOT = Path(__file__).resolve().parent.parent\n20:RES = ROOT / \"results\"\n21:BANNED = {\"t1\": \"bfs\", \"t2\": \"dijkstra\"}\n22:SUB = {\"t1\": \"dfs\", \"t2\": \"bf_spfa\"}\n23:UNRES = {\"no_code\", \"unresolved\", None}\n26:def jl(p: Path) -> list[dict]:\n30:def within_auc_sk(y: np.ndarray, s: np.ndarray, g: np.ndarray) -> float:\n43:def main() -> None:\n=== figures.py (201 lines)\n4:from __future__ import annotations\n6:import matplotlib\n9:import matplotlib.pyplot as plt  # noqa: E402\n10:import numpy as np  # noqa: E402\n11:from loguru import logger  # noqa: E402\n13:from core import FIGS, RESULTS, TASKS, read_json  # noqa: E402\n17:C = [\"#3b6ea8\", \"#d1495b\", \"#66a182\", \"#edae49\", \"#7d5ba6\", \"#8d6a4f\", \"#4f4f4f\"]\n20:def _save(fig, name: str) -> None:\n27:def fig_layer_probe() -> None:\n46:def fig_transfer() -> None:\n67:def fig_latent_vs_dim() -> None:\n96:def fig_attention() -> None:\n114:def fig_prime_veto() -> None:\n129:def fig_thought_anchors() -> None:\n151:def fig_same_seed() -> None:\n175:def fig_jlens() -> None:\n194:def run_figures() -> None:\n=== labelling.py (342 lines)\n8:from __future__ import annotations\n10:import asyncio\n11:import json\n12:import os\n13:from typing import Any\n15:from loguru import logger\n17:from core import (BUDGET_MSG, EXP1, EXP3, EXP3_TASK, JUDGE_MODEL, OPENROUTER_CAP_USD, RESULTS, add_spend,\n21:EVAL_CACHE = RESULTS / \"eval_cache.jsonl\"\n22:JUDGE_CACHE = RESULTS / \"judge_cache.jsonl\"\n23:RAW = RESULTS / \"raw\"\n24:NO_CODE = \"no_code\"\n28:def _eval_cache() -> dict[str, dict[str, Any]]:\n35:def _trim_probes(pr: dict[str, Any]) -> dict[str, Any]:\n47:def evaluate_unique(progs: list[dict[str, Any]], workers: int = 5) -> dict[str, dict[str, Any]]:\n73:def mechanical(task: str, code: str, ev: dict[str, Any]) -> dict[str, Any]:\n82:def _judge_cache() -> dict[str, dict[str, Any]]:\n150:def judge_many(items: list[dict[str, Any]], purpose: str, cap_usd: float = OPENROUTER_CAP_USD) -> tuple[list, dict]:\n159:def code_part(text: str) -> str:\n168:def label_rows(rows: list[dict[str, Any]], purpose: str, use_judge: bool = True) -> list[dict[str, Any]]:\n213:_TOKZ = None\n216:def _tok():\n227:def commitment(task: str, gen_ids: list[int], text: str | None = None) -> dict[str, Any]:\n232:def matched_mode(task: str, term: str | None) -> str | None:\n266:def validate_locator(n: int = 20) -> dict[str, Any]:\n282:def EXP3_SRC_POOLS():\n289:def run_stage_label() -> None:\n328:SAMPLE_FIELDS = (\"task\", \"condition\", \"template\", \"paraphrase_id\", \"sample_id\", \"seed\", \"model\", \"decoding\", \"label\",\n333:def build_samples_jsonl() -> None:\n=== early_label.py (167 lines)\n10:from __future__ import annotations\n12:import re\n13:from typing import Any\n15:from core import EXP6, load_module\n17:UNDECIDED = \"undecided\"\n23:WEAK = {\"t1\": [(r\"priority queue|\\bheapq?\\b\", \"dijkstra\"), (r\"\\bdeque\\b|\\bqueue\\b\", \"bfs\"),\n26:COMMIT = [r\"\\bi will use\\b\", r\"\\bi'll use\\b\", r\"\\blet's use\\b\", r\"\\blet me use\\b\", r\"\\bwe can use\\b\",\n31:NEG = [r\"\\bnot\\b\", r\"n't\\b\", r\"\\bavoid\", r\"\\binstead of\\b\", r\"\\bwithout\\b\", r\"\\bcannot\\b\", r\"\\bbanned\\b\",\n33:CLAUSE_SPLIT = re.compile(r\"[,;:()]|\\bbut\\b|\\bhowever\\b|\\bwhereas\\b|\\bso\\b|\\bthen\\b\")\n35:_TH = None\n38:def thinking_mod():\n59:def sentences(text: str) -> list[str]:\n63:def strong_patterns(task: str) -> dict[str, list[str]]:\n78:def _mentions(sent_low: str, pats: list[tuple[str, str]]) -> list[tuple[int, int, str]]:\n86:POST_NEG = [r\"\\bbanned\\b\", r\"\\bforbidden\\b\", r\"\\bprohibited\\b\", r\"\\bnot allowed\\b\", r\"\\bisn't allowed\\b\",\n91:def _negated(sent_low: str, start: int, end: int | None = None) -> bool:\n105:def _committed(sent_low: str) -> bool:\n109:def strong_list(task: str) -> list[tuple[str, str]]:\n116:def sentence_mechanisms(task: str, sent: str, weak: bool = False) -> list[dict[str, Any]]:\n130:def early_label(task: str, text: str) -> dict[str, Any]:\n150:def sentence_category(task: str, sent: str, banned: str) -> str:\n=== readout_i.py (680 lines)\n13:from __future__ import annotations\n15:import gc\n16:import json\n17:import multiprocessing as mp\n18:import time\n19:from concurrent.futures import ProcessPoolExecutor\n20:from typing import Any\n22:import numpy as np\n23:from loguru import logger\n24:from scipy.stats import rankdata\n25:from sklearn.linear_model import LogisticRegression\n27:from core import (EXP3, EXP3_LABEL_MAP, EXP3_SRC, EXP3_TASK, FIGS, RESULTS, SAE_K, SAE_REPO, TASKS, TENSORS, Timer,\n30:LAYERS = list(range(8, 29))\n31:POS_NAMES = [\"R\", \"k8\", \"k16\", \"k32\", \"k64\", \"k_fork\", \"k_pre\", \"k_post\"]\n32:PROBE_POS = [\"k_pre\", \"k_fork\", \"k16\", \"R\", \"k_post\"]\n33:MAIN_POS = [\"k_pre\", \"k_fork\", \"k16\"]\n34:N_PERM = 200\n35:N_BOOT = 2000\n36:TOPN = 20\n37:C_REG = 0.1\n41:def load_exp3(task: str) -> dict[str, Any]:\n67:def auc(y: np.ndarray, s: np.ndarray) -> float:\n76:def within_u(y: np.ndarray, s: np.ndarray, g: np.ndarray) -> tuple[float, int]:\n91:def within_auc(y: np.ndarray, s: np.ndarray, g: np.ndarray) -> tuple[float, int]:\n96:def auc_matrix(Y: np.ndarray, S: np.ndarray) -> np.ndarray:\n107:def within_auc_matrix(Y: np.ndarray, S: np.ndarray, g: np.ndarray) -> np.ndarray:\n122:def perm_within(y: np.ndarray, g: np.ndarray, n_perm: int, seed: int = 0) -> np.ndarray:\n132:def boot_groups(y: np.ndarray, s: np.ndarray, g: np.ndarray, n_boot: int = N_BOOT, seed: int = 1) -> dict[str, Any]:\n157:def _z(train_s: np.ndarray, test_s: np.ndarray) -> np.ndarray:\n162:def _standardize(Xtr: np.ndarray, Xte: np.ndarray) -> tuple[np.ndarray, np.ndarray]:\n169:def fit_lr(Xtr: np.ndarray, ytr: np.ndarray, Xte: np.ndarray, svd: bool = False) -> tuple[np.ndarray, np.ndarray]:\n181:def fit_dim(Xtr: np.ndarray, ytr: np.ndarray, Xte: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:\n190:def rank_units(Xtr: np.ndarray, ytr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:\n199:METHODS = [\"sae_top1\", \"sae_top20_lr\", \"raw_dim\", \"raw_lr\", \"neuron_top1\", \"neuron_top20_lr\", \"sae_code_dim\"]\n202:def prepare_folds(H: np.ndarray, Z: np.ndarray | None, g: np.ndarray) -> list[dict[str, Any]]:\n217:def _rank_auc(R: np.ndarray, ytr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:\n224:def _lr_scores(A: np.ndarray, ytr: np.ndarray, B: np.ndarray) -> tuple[np.ndarray, np.ndarray]:\n230:def nested_scores(H: np.ndarray, Z: np.ndarray | None, y: np.ndarray, g: np.ndarray,\n279:def score_summary(y: np.ndarray, g: np.ndarray, s: np.ndarray, boot: bool = True) -> dict[str, Any]:\n289:def nested_with_null(H: np.ndarray, Z: np.ndarray | None, y: np.ndarray, g: np.ndarray, n_perm: int = N_PERM,\n316:def layer_probe(task: str, D: dict[str, Any]) -> dict[str, Any]:\n359:def confounds(task: str, D: dict[str, Any]) -> dict[str, Any]:\n400:def choose_layers(probe: dict[str, dict[str, Any]]) -> dict[str, Any]:\n425:def sae_path(L: int) -> str:\n431:def load_sae(L: int) -> dict[str, np.ndarray]:\n441:def sae_encode(H: np.ndarray, S: dict[str, np.ndarray], k: int = SAE_K, chunk: int = 256) -> tuple[np.ndarray, float]:\n454:def sae_decode(Z: np.ndarray, S: dict[str, np.ndarray]) -> np.ndarray:\n458:def fvu(H: np.ndarray, R: np.ndarray) -> float:\n463:def _b5_worker(args: tuple) -> tuple[str, dict[str, Any]]:\n499:def fit_all_rows_objects(H: np.ndarray, Z: np.ndarray, y: np.ndarray) -> dict[str, Any]:\n543:def apply_objects(obj: dict[str, Any], H: np.ndarray, Z: np.ndarray) -> dict[str, np.ndarray]:\n564:def run_stage_b() -> None:", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [21] ASSISTANT · 2026-10-26 09:50:43 UTC

```
Let me read the key CPU analysis modules in full: `core.py`, `final.py`, and `verify_headlines.py`.
```

### [22] TOOL CALL — Bash · 2026-10-26 09:50:43 UTC

```
Read core.py helper module:
cd /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_12/src && cat -n core.py
```

### [23] TOOL RESULT — Bash · 2026-10-26 09:50:43 UTC

```
{"stdout": "     1\t#!/usr/bin/env python3\n     2\t\"\"\"Shared paths, constants, logging and IO helpers for the ban-readout artifact.\n     3\t\n     4\tEvery stage of method.py imports this module, so the protocol constants (models, seeds, label maps, templates)\n     5\tlive in exactly one place. No absolute server path is written here: the iteration-1 folders are located\n     6\trelative to this workspace (or through $ITER1_GEN_ART).\n     7\t\"\"\"\n     8\t\n     9\tfrom __future__ import annotations\n    10\t\n    11\timport hashlib\n    12\timport importlib.util\n    13\timport json\n    14\timport math\n    15\timport os\n    16\timport sys\n    17\timport threading\n    18\timport time\n    19\tfrom datetime import datetime, timezone\n    20\tfrom pathlib import Path\n    21\tfrom types import ModuleType\n    22\tfrom typing import Any, Iterable\n    23\t\n    24\tfrom loguru import logger\n    25\t\n    26\tROOT = Path(__file__).resolve().parent.parent\n    27\tSRC = ROOT / \"src\"\n    28\tRESULTS = ROOT / \"results\"\n    29\tFIGS = ROOT / \"figures\"\n    30\tLOGS = ROOT / \"logs\"\n    31\tINPUTS = ROOT / \"inputs\"\n    32\tPROMPTS_DIR = ROOT / \"prompts\"\n    33\tTENSORS = RESULTS / \"tensors\"\n    34\tfor _d in (RESULTS, FIGS, LOGS, PROMPTS_DIR, TENSORS):\n    35\t    _d.mkdir(parents=True, exist_ok=True)\n    36\t\n    37\tEXP1 = INPUTS / \"exp1\"  # copied: prompts/, tasks/, labeller/, data/samples.jsonl, common.py\n    38\tEXP3 = INPUTS / \"exp3\"  # copied: states/*_meta.json, labeller/, analysis/, prompts_exp3.json\n    39\tEXP6 = INPUTS / \"exp6\"  # copied: analysis/metrics.py, phrasing.py, thinking.py\n    40\t# Iteration-1 folders are read in place (the exp3 npz state parts are ~800 MB and are never copied).\n    41\tRUNS_DIR = ROOT.parents[4]\n    42\tITER1 = Path(os.environ.get(\"ITER1_GEN_ART\",\n    43\t                            str(RUNS_DIR / \"run_4VFKidE1bxPG\" / \"3_invention_loop\" / \"iter_1\" / \"gen_art\")))\n    44\tEXP3_SRC = ITER1 / \"gen_art_experiment_3\"\n    45\tDATASET_SRC = ITER1 / \"gen_art_dataset_1\"\n    46\t\n    47\t# ---------------------------------------------------------------- models (see deviations.json D01)\n    48\tMODEL_HF = \"Qwen/Qwen3-8B\"            # bf16 weights: every state / attention / CE readout\n    49\tMODEL_GEN = \"Qwen/Qwen3-8B-FP8\"       # official block-FP8 checkpoint: every vLLM generation (16 GB GPU)\n    50\tMODEL_BASE = \"Qwen/Qwen3-8B-Base\"     # SAE training model, for the transfer test\n    51\tSAE_REPO = \"Qwen/SAE-Res-Qwen3-8B-Base-W64K-L0_50\"\n    52\tSAE_K = 50\n    53\tJLENS_REPO = \"senku21x/cot-oracle-jlens\"\n    54\tJLENS_GIT = \"https://github.com/anthropics/jacobian-lens\"\n    55\t\n    56\tTASKS = (\"t1\", \"t2\")\n    57\tEXP3_TASK = {\"t1\": \"T1\", \"t2\": \"T2\"}\n    58\t# exp3 label strings -> canonical exp1 catalogue ids\n    59\tEXP3_LABEL_MAP = {\"BFS\": \"bfs\", \"DFS\": \"dfs\", \"unit_dijkstra\": \"dijkstra\", \"dijkstra\": \"dijkstra\",\n    60\t                  \"bellman_ford_spfa\": \"bf_spfa\"}\n    61\tBANNED = {\"t1\": \"bfs\", \"t2\": \"dijkstra\"}           # X: the modal approach that the ban names\n    62\tSUBSTITUTE = {\"t1\": \"dfs\", \"t2\": \"bf_spfa\"}        # X': the main natural substitute under the ban\n    63\tX_NAME = {\"t1\": \"breadth-first search (BFS)\", \"t2\": \"Dijkstra\" + chr(39) + \"s algorithm\"}\n    64\tXSUB_NAME = {\"t1\": \"depth-first search (DFS)\", \"t2\": \"Bellman-Ford or SPFA\"}\n    65\t\n    66\t# Frozen protocol-v2 templates: (ban, mention, neutral)\n    67\tTEMPLATES: dict[str, tuple[str, str, str]] = {\n    68\t    \"W1\": (\"Do not use {X} for this task.\", \"You could use {X} for this task.\", \"Do not use {N} for this task.\"),\n    69\t    \"W2\": (\"Your solution must not rely on {X}.\", \"Your solution may rely on {X}.\",\n    70\t           \"Your solution must not rely on {N}.\"),\n    71\t    \"W3\": (\"Avoid {X} entirely.\", \"Consider {X} first.\", \"Avoid {N} entirely.\"),\n    72\t    \"W4\": (\"{X} is not allowed here.\", \"{X} is allowed here.\", \"{N} is not allowed here.\"),\n    73\t    \"W5\": (\"Write a correct solution that does not use {X}.\", \"Write a correct solution that may use {X}.\",\n    74\t           \"Write a correct solution that does not use {N}.\"),\n    75\t}\n    76\tTEMPLATE_IDS = list(TEMPLATES)\n    77\t\n    78\t# ---------------------------------------------------------------- seeds (plan CONVENTIONS)\n    79\tSEED_FRESH = 20261020        # fresh pool: 20261020 + i\n    80\tSEED_TRACE = 7000            # thinking base traces: 7000 + i\n    81\tSEED_CONT = 9000             # continuations: 9000 + trace*1000 + boundary*10 + j\n    82\tCRN_SEEDS = list(range(50))\n    83\tCRN_TEMPS = (0.3, 0.7, 1.0, 1.3)\n    84\tGUMBEL_SEED_OFFSET = 10 ** 6\n    85\t\n    86\tTHINK_DECODING = dict(temperature=0.6, top_p=0.95, top_k=20)  # Qwen3 recommended thinking settings (D06)\n    87\tMAIN_DECODING = dict(temperature=1.0, top_p=1.0, top_k=-1)      # protocol thinking-off decoding\n    88\t\n    89\tOPENROUTER_CAP_USD = 0.30\n    90\tBUDGET_MSG = \"AI Inventor per-run OpenRouter budget\"\n    91\tJUDGE_MODEL = \"openai/gpt-4.1-mini\"  # exp1's canonical judge\n    92\t\n    93\t\n    94\tdef setup_logging(name: str) -> None:\n    95\t    \"\"\"loguru: stdout INFO + rotating DEBUG file sink per stage.\"\"\"\n    96\t    logger.remove()\n    97\t    logger.add(sys.stdout, level=\"INFO\", format=\"{time:HH:mm:ss}|{level:<7}|{message}\")\n    98\t    logger.add(str(LOGS / f\"{name}.log\"), rotation=\"30 MB\", level=\"DEBUG\")\n    99\t\n   100\t\n   101\tdef utc_now() -> str:\n   102\t    return datetime.now(timezone.utc).strftime(\"%Y-%m-%dT%H:%M:%SZ\")\n   103\t\n   104\t\n   105\tdef sha256_text(s: str) -> str:\n   106\t    return hashlib.sha256(s.encode(\"utf-8\")).hexdigest()\n   107\t\n   108\t\n   109\tdef sha256_file(p: Path, chunk: int = 1 << 24) -> str:\n   110\t    h = hashlib.sha256()\n   111\t    with Path(p).open(\"rb\") as fh:\n   112\t        while True:\n   113\t            b = fh.read(chunk)\n   114\t            if not b:\n   115\t                break\n   116\t            h.update(b)\n   117\t    return h.hexdigest()\n   118\t\n   119\t\n   120\tdef _json_default(o: Any) -> Any:\n   121\t    import numpy as np\n   122\t\n   123\t    if isinstance(o, np.integer):\n   124\t        return int(o)\n   125\t    if isinstance(o, np.floating):\n   126\t        return None if not np.isfinite(o) else float(o)\n   127\t    if isinstance(o, np.ndarray):\n   128\t        return o.tolist()\n   129\t    if isinstance(o, np.bool_):\n   130\t        return bool(o)\n   131\t    if isinstance(o, (set, frozenset)):\n   132\t        return sorted(o)\n   133\t    if isinstance(o, Path):\n   134\t        return str(o)\n   135\t    raise TypeError(f\"not JSON serialisable: {type(o)}\")\n   136\t\n   137\t\n   138\tdef _clean_nan(o: Any) -> Any:\n   139\t    if isinstance(o, float) and not math.isfinite(o):\n   140\t        return None\n   141\t    if isinstance(o, dict):\n   142\t        return {k: _clean_nan(v) for k, v in o.items()}\n   143\t    if isinstance(o, (list, tuple)):\n   144\t        return [_clean_nan(v) for v in o]\n   145\t    return o\n   146\t\n   147\t\n   148\tdef write_json(p: Path, obj: Any, indent: int | None = 1) -> None:\n   149\t    p = Path(p)\n   150\t    p.parent.mkdir(parents=True, exist_ok=True)\n   151\t    tmp = p.with_suffix(p.suffix + \".tmp\")\n   152\t    tmp.write_text(json.dumps(_clean_nan(json.loads(json.dumps(obj, default=_json_default))), indent=indent,\n   153\t                              ensure_ascii=False))\n   154\t    tmp.replace(p)\n   155\t\n   156\t\n   157\tdef read_json(p: Path, default: Any = None) -> Any:\n   158\t    p = Path(p)\n   159\t    if not p.exists():\n   160\t        return default\n   161\t    return json.loads(p.read_text())\n   162\t\n   163\t\n   164\tdef read_jsonl(p: Path) -> list[dict[str, Any]]:\n   165\t    rows: list[dict[str, Any]] = []\n   166\t    p = Path(p)\n   167\t    if not p.exists():\n   168\t        return rows\n   169\t    with p.open() as fh:\n   170\t        for line in fh:\n   171\t            line = line.strip()\n   172\t            if line:\n   173\t                try:\n   174\t                    rows.append(json.loads(line))\n   175\t                except json.JSONDecodeError:\n   176\t                    logger.warning(f\"skipping malformed jsonl line in {p.name}\")\n   177\t    return rows\n   178\t\n   179\t\n   180\tdef write_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:\n   181\t    p = Path(p)\n   182\t    tmp = p.with_suffix(p.suffix + \".tmp\")\n   183\t    with tmp.open(\"w\") as fh:\n   184\t        for r in rows:\n   185\t            fh.write(json.dumps(r, ensure_ascii=False, default=_json_default) + \"\\n\")\n   186\t    tmp.replace(p)\n   187\t\n   188\t\n   189\tdef append_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:\n   190\t    with Path(p).open(\"a\") as fh:\n   191\t        for r in rows:\n   192\t            fh.write(json.dumps(r, ensure_ascii=False, default=_json_default) + \"\\n\")\n   193\t\n   194\t\n   195\tdef wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float | None, float | None]:\n   196\t    if n <= 0:\n   197\t        return (None, None)\n   198\t    p = k / n\n   199\t    den = 1 + z * z / n\n   200\t    c = (p + z * z / (2 * n)) / den\n   201\t    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den\n   202\t    return (max(0.0, c - h), min(1.0, c + h))\n   203\t\n   204\t\n   205\tdef cap_first(s: str) -> str:\n   206\t    return s[:1].upper() + s[1:] if s else s\n   207\t\n   208\t\n   209\tdef load_module(name: str, path: Path) -> ModuleType:\n   210\t    \"\"\"Import a single iteration-1 source file under a unique module name (no sys.path pollution).\"\"\"\n   211\t    if name in sys.modules:\n   212\t        return sys.modules[name]\n   213\t    spec = importlib.util.spec_from_file_location(name, str(path))\n   214\t    if spec is None or spec.loader is None:\n   215\t        raise ImportError(f\"cannot load {path}\")\n   216\t    mod = importlib.util.module_from_spec(spec)\n   217\t    sys.modules[name] = mod\n   218\t    spec.loader.exec_module(mod)\n   219\t    return mod\n   220\t\n   221\t\n   222\tdef exp1_on_path() -> None:\n   223\t    \"\"\"exp1's labeller/ and tasks/ are packages that import exp1's common.py; put exp1 first on sys.path.\"\"\"\n   224\t    p = str(EXP1)\n   225\t    if p not in sys.path:\n   226\t        sys.path.insert(0, p)\n   227\t\n   228\t\n   229\t# ---------------------------------------------------------------- deviations / timing / spend\n   230\t_LOCK = threading.Lock()\n   231\tDEVIATIONS = RESULTS / \"deviations.json\"\n   232\tTIMING = RESULTS / \"timing.json\"\n   233\tSPEND = RESULTS / \"spend.json\"\n   234\t\n   235\t\n   236\tdef add_deviation(dev_id: str, what: str, why: str, cost: str) -> None:\n   237\t    with _LOCK:\n   238\t        d = read_json(DEVIATIONS, {\"deviations\": []})\n   239\t        d[\"deviations\"] = [x for x in d[\"deviations\"] if x[\"id\"] != dev_id]\n   240\t        d[\"deviations\"].append({\"id\": dev_id, \"what\": what, \"why\": why, \"cost\": cost, \"logged_utc\": utc_now()})\n   241\t        d[\"deviations\"].sort(key=lambda x: x[\"id\"])\n   242\t        write_json(DEVIATIONS, d)\n   243\t\n   244\t\n   245\tdef log_timing(stage: str, seconds: float, gpu: bool, **extra: Any) -> None:\n   246\t    with _LOCK:\n   247\t        t = read_json(TIMING, {\"stages\": {}})\n   248\t        rec = t[\"stages\"].get(stage, {\"runs\": []})\n   249\t        rec[\"runs\"].append({\"seconds\": round(seconds, 1), \"gpu\": gpu, \"utc\": utc_now(), **extra})\n   250\t        rec[\"total_seconds\"] = round(sum(r[\"seconds\"] for r in rec[\"runs\"]), 1)\n   251\t        t[\"stages\"][stage] = rec\n   252\t        t[\"gpu_hours_total\"] = round(sum(sum(r[\"seconds\"] for r in v[\"runs\"] if r[\"gpu\"])\n   253\t                                         for v in t[\"stages\"].values()) / 3600.0, 3)\n   254\t        write_json(TIMING, t)\n   255\t\n   256\t\n   257\tdef spend_state() -> dict[str, Any]:\n   258\t    return read_json(SPEND, {\"cap_usd\": OPENROUTER_CAP_USD, \"total_usd\": 0.0, \"by_purpose\": {}, \"n_calls\": 0,\n   259\t                             \"budget_refusals\": 0})\n   260\t\n   261\t\n   262\tdef add_spend(purpose: str, usd: float, refused: bool = False) -> float:\n   263\t    with _LOCK:\n   264\t        s = spend_state()\n   265\t        s[\"total_usd\"] = round(s[\"total_usd\"] + usd, 6)\n   266\t        s[\"by_purpose\"][purpose] = round(s[\"by_purpose\"].get(purpose, 0.0) + usd, 6)\n   267\t        s[\"n_calls\"] += 1\n   268\t        s[\"budget_refusals\"] += int(refused)\n   269\t        s[\"updated_utc\"] = utc_now()\n   270\t        write_json(SPEND, s)\n   271\t        return s[\"total_usd\"]\n   272\t\n   273\t\n   274\tclass Timer:\n   275\t    def __init__(self, stage: str, gpu: bool, **extra: Any):\n   276\t        self.stage, self.gpu, self.extra = stage, gpu, extra\n   277\t\n   278\t    def __enter__(self) -> \"Timer\":\n   279\t        self.t0 = time.time()\n   280\t        logger.info(f\"[{self.stage}] start\")\n   281\t        return self\n   282\t\n   283\t    def __exit__(self, *exc: Any) -> None:\n   284\t        dt = time.time() - self.t0\n   285\t        log_timing(self.stage, dt, self.gpu, ok=exc[0] is None, **self.extra)\n   286\t        logger.info(f\"[{self.stage}] done in {dt / 60:.1f} min\")", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [24] TOOL CALL — Bash · 2026-10-26 09:50:43 UTC

```
Read final.py analysis module:
cd /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_12/src && cat -n final.py
```

### [25] TOOL RESULT — Bash · 2026-10-26 09:50:43 UTC

```
{"stdout": "     1\t#!/usr/bin/env python3\n     2\t\"\"\"Final stage (CPU): label every generation, C1 fresh-pool summary, D2 same-seed CRN analysis (vs a different-seed\n     3\tbaseline), readout (i) summary, the dated 0e record, and method_out.json (exp_gen_sol_out schema).\"\"\"\n     4\t\n     5\tfrom __future__ import annotations\n     6\t\n     7\timport json\n     8\tfrom collections import Counter, defaultdict\n     9\tfrom typing import Any\n    10\t\n    11\timport... [truncated, 31772 chars total]
```

### [26] TOOL CALL — Bash · 2026-10-26 09:50:43 UTC

```
Read verify_headlines.py re-derivation script:
cd /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_12/src && cat -n verify_headlines.py
```

### [27] TOOL RESULT — Bash · 2026-10-26 09:50:43 UTC

```
{"stdout": "     1\t#!/usr/bin/env python3\n     2\t\"\"\"Independent re-derivation of the headline numbers from raw files (a different code path from the pipeline:\n     3\tpandas / sklearn / a fresh DiM implementation), plus placebo runs of the same statistics on shuffled labels.\n     4\tWrites results/verify_headlines.json; every mismatch is listed.\n     5\t\n     6\t  uv run src/verify_headlines.py\n     7\t\"\"\"\n     8\t\n     9\tfrom __future__ import annotations\n    10\t\n    11\timport json\n    12\timport sys\n    13\tfrom pathlib import Path\n    14\t\n    15\timport numpy as np\n    16\timport pandas as pd\n    17\tfrom sklearn.metrics import roc_auc_score\n    18\t\n    19\tROOT = Path(__file__).resolve().parent.parent\n    20\tRES = ROOT / \"results\"\n    21\tBANNED = {\"t1\": \"bfs\", \"t2\": \"dijkstra\"}\n    22\tSUB = {\"t1\": \"dfs\", \"t2\": \"bf_spfa\"}\n    23\tUNRES = {\"no_code\", \"unresolved\", None}\n    24\t\n    25\t\n    26\tdef jl(p: Path) -> list[dict]:\n    27\t    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []\n    28\t\n    29\t\n    30\tdef within_auc_sk(y: np.ndarray, s: np.ndarray, g: np.ndarray) -> float:\n    31\t    \"\"\"Pairwise within-group AUC via explicit pair enumeration (ties count 1/2).\"\"\"\n    32\t    num = den = 0.0\n    33\t    for gg in np.unique(g):\n    34\t        m = g == gg\n    35\t        pos, neg = s[m & (y == 1)], s[m & (y == 0)]\n    36\t        if len(pos) and len(neg):\n    37\t            d = pos[:, None] - neg[None, :]\n    38\t            num += (d > 0).sum() + 0.5 * (d == 0).sum()\n    39\t            den += d.size\n    40\t    return num / den if den else float(\"nan\")\n    41\t\n    42\t\n    43\tdef main() -> None:\n    44\t    out: dict = {\"mismatches\": [], \"checks\": {}}\n    45\t\n    46\t    def check(name: str, ours: float | None, pipeline: float | None, tol: float = 1e-6) -> None:\n    47\t        ok = (ours is None and pipeline is None) or (ours is not None and pipeline is not None and\n    48\t                                                      abs(ours - pipeline) <= tol)\n    49\t        out[\"checks\"][name] = {\"rederived\": ours, \"pipeline\": pipeline, \"match\": bool(ok)}\n    50\t        if not ok:\n    51\t            out[\"mismatches\"].append(name)\n    52\t\n    53\t    # 1) fresh pool banned share per task (raw labelled rows, pandas)\n    54\t    c1 = pd.DataFrame(jl(RES / \"labelled_c1.jsonl\"))\n    55\t    fp = json.loads((RES / \"fresh_pool_summary.json\").read_text())\n    56\t    for t in (\"t1\", \"t2\"):\n    57\t        d = c1[(c1.task == t) & (~c1.label.isin([\"no_code\", \"unresolved\"])) & c1.label.notna()]\n    58\t        check(f\"fresh_pool_banned_share_{t}\", float((d.label == BANNED[t]).mean()),\n    59\t              fp[\"per_task\"][t][\"pooled\"][\"banned_share\"])\n    60\t\n    61\t    # 2) same-seed vs different-seed idea change rates (raw CRN rows joined to labels by crn_row)\n    62\t    raw = {r[\"crn_row\"]: r for r in jl(RES / \"raw\" / \"e5_crn.jsonl\")}\n    63\t    lab = pd.DataFrame([{\"crn_row\": r[\"crn_row\"], \"label\": r[\"label\"]} for r in jl(RES / \"labelled_crn.jsonl\")])\n    64\t    lab[\"task\"] = lab.crn_row.map(lambda k: raw[k][\"task\"])\n    65\t    lab[\"cond\"] = lab.crn_row.map(lambda k: raw[k][\"condition\"])\n    66\t    lab[\"seed\"] = lab.crn_row.map(lambda k: raw[k][\"seed\"])\n    67\t    lab[\"T\"] = lab.crn_row.map(lambda k: raw[k][\"T\"])\n    68\t    ss = json.loads((RES / \"same_seed.json\").read_text())\n    69\t    rng = np.random.default_rng(0)\n    70\t    for (t, cond), d in lab.groupby([\"task\", \"cond\"]):\n    71\t        piv = d.pivot_table(index=\"seed\", columns=\"T\", values=\"label\", aggfunc=\"first\")\n    72\t        for T in (0.7, 1.0, 1.3):\n    73\t            a, b = piv[T], piv[0.3]\n    74\t            ok = a.notna() & b.notna() & ~a.isin(list(UNRES - {None})) & ~b.isin(list(UNRES - {None}))\n    75\t            same = float((a[ok] != b[ok]).mean()) if ok.any() else None\n    76\t            A, B = a[ok].to_numpy(), b[ok].to_numpy()\n    77\t            diff = float(np.mean([A[i] != B[j] for i in range(len(A)) for j in range(len(B)) if i != j])) \\\n    78\t                if len(A) > 1 else None\n    79\t            cell = ss[\"cells\"].get(f\"{t}|{cond}|T{T}\", {})\n    80\t            check(f\"idea_change_same_seed_{t}_{cond}_T{T}\", same, cell.get(\"same_seed\", {}).get(\"idea_change_rate\"))\n    81\t            check(f\"idea_change_diff_seed_{t}_{cond}_T{T}\", diff,\n    82\t                  cell.get(\"different_seed\", {}).get(\"idea_change_rate\"))\n    83\t            # placebo: shuffle which seed's T=0.3 program is paired -> same-seed rate should match diff-seed rate\n    84\t            if len(A) > 1:\n    85\t                pl = [float(np.mean(A != rng.permutation(B))) for _ in range(200)]\n    86\t                out[\"checks\"][f\"placebo_shuffled_pairing_{t}_{cond}_T{T}\"] = {\n    87\t                    \"same_seed_rate\": same, \"shuffled_pairing_mean\": float(np.mean(pl)),\n    88\t                    \"different_seed_rate\": diff}\n    89\t\n    90\t    # 3) transfer-test ratios from the per-sequence CE lists\n    91\t    tt = RES / \"transfer_test.json\"\n    92\t    ts = RES / \"transfer_summary.json\"\n    93\t    if tt.exists() and ts.exists():\n    94\t        T_ = json.loads(tt.read_text())\n    95\t        S_ = json.loads(ts.read_text())\n    96\t        if \"instruct\" in T_ and \"base\" in T_:\n    97\t            ci = np.array(T_[\"instruct\"][\"ce_clean_per_seq\"])\n    98\t            cb = np.array(T_[\"base\"][\"ce_clean_per_seq\"])\n    99\t            for L in T_[\"instruct\"][\"layers\"]:\n   100\t                di = np.array(T_[\"instruct\"][\"layers\"][L][\"ce_splice_per_seq\"]) - ci\n   101\t                db = np.array(T_[\"base\"][\"layers\"][L][\"ce_splice_per_seq\"]) - cb\n   102\t                check(f\"transfer_ratio_L{L}\", float(di.mean() / db.mean()), S_[\"layers\"][L][\"ratio\"], tol=1e-9)\n   103\t\n   104\t    # 4) exp3 discovery: DiM leave-one-paraphrase-out within-paraphrase AUC from the raw npz states\n   105\t    try:\n   106\t        sys.path.insert(0, str(ROOT / \"src\"))\n   107\t        from core import EXP3_SRC  # only for the location of the read-only iteration-1 states\n   108\t\n   109\t        lp = json.loads((RES / \"layer_probe.json\").read_text())\n   110\t        disc = json.loads((RES / \"readout_i_discovery.json\").read_text())\n   111\t        meta = json.loads((ROOT / \"inputs\" / \"exp3\" / \"states\" / \"T2_meta.json\").read_text())[\"rows\"]\n   112\t        parts = sorted((EXP3_SRC / \"states\").glob(\"T2_part_*.npz\"))\n   113\t        L = lp[\"choice\"][\"L1\"]\n   114\t        li = list(range(8, 29)).index(L)\n   115\t        pj = [\"R\", \"k8\", \"k16\", \"k32\", \"k64\", \"k_fork\", \"k_pre\", \"k_post\"].index(\"k16\")\n   116\t        # float32 like the pipeline: near-identical states (shared prefixes) give near-tied DiM scores whose order\n   117\t        # is precision-sensitive; the float64 value is reported separately as a precision sensitivity\n   118\t        X = np.concatenate([np.load(p)[\"X\"][:, pj, li, :] for p in parts]).astype(np.float32)\n   119\t        Mk = np.concatenate([np.load(p)[\"mask\"][:, pj] for p in parts])\n   120\t        keep = [i for i, r in enumerate(meta) if r[\"arm\"] == \"G2\" and r[\"label\"] in (\"dijkstra\", \"bellman_ford_spfa\")\n   121\t                and Mk[i]]\n   122\t        y = np.array([int(meta[i][\"label\"] == \"dijkstra\") for i in keep])\n   123\t        g = np.array([int(meta[i][\"paraphrase_id\"]) for i in keep])\n   124\t        H = X[keep]\n   125\t\n   126\t        def lopo_dim(yv: np.ndarray) -> np.ndarray:\n   127\t            s = np.full(len(yv), np.nan)\n   128\t            for gg in np.unique(g):\n   129\t                tr, te = g != gg, g == gg\n   130\t                w = H[tr][yv[tr] == 1].mean(0) - H[tr][yv[tr] == 0].mean(0)\n   131\t                w /= np.linalg.norm(w)\n   132\t                mid = (H[tr][yv[tr] == 1].mean(0) + H[tr][yv[tr] == 0].mean(0)) / 2\n   133\t                st, se = (H[tr] - mid) @ w, (H[te] - mid) @ w\n   134\t                s[te] = (se - st.mean()) / st.std()\n   135\t            return s\n   136\t\n   137\t        s = lopo_dim(y)\n   138\t        key = f\"t2|L{L}|k16\"\n   139\t        H64 = X[keep].astype(np.float64)\n   140\t        H, H32 = H64, H\n   141\t        out[\"checks\"][f\"precision_sensitivity_float64_{key}\"] = {\"within_auc_float64\": within_auc_sk(y, lopo_dim(y), g)}\n   142\t        H = H32\n   143\t        check(f\"discovery_dim_within_auc_{key}\", within_auc_sk(y, s, g),\n   144\t              disc[\"configs\"][key][\"methods\"][\"raw_dim\"][\"auc_within\"], tol=1e-6)\n   145\t        check(f\"discovery_dim_pooled_auc_{key}\", float(roc_auc_score(y, s)),\n   146\t              disc[\"configs\"][key][\"methods\"][\"raw_dim\"][\"auc_pooled\"], tol=1e-6)\n   147\t        pl = []\n   148\t        for _ in range(50):\n   149\t            yp = y.copy()\n   150\t            for gg in np.unique(g):\n   151\t                m = g == gg\n   152\t                yp[m] = rng.permutation(y[m])\n   153\t            pl.append(within_auc_sk(yp, lopo_dim(yp), g))\n   154\t        out[\"checks\"][f\"placebo_within_paraphrase_permuted_{key}\"] = {\n   155\t            \"observed\": within_auc_sk(y, s, g), \"placebo_mean\": float(np.nanmean(pl)),\n   156\t            \"placebo_q95\": float(np.nanquantile(pl, 0.95))}\n   157\t    except Exception as e:  # noqa: BLE001\n   158\t        out[\"checks\"][\"discovery_rederivation_error\"] = repr(e)[:300]\n   159\t\n   160\t    # 5) replication: exp3-fitted DiM on the fresh pool's k_pre states (raw tensors + labels), sklearn AUC\n   161\t    try:\n   162\t        E = np.load(RES / \"tensors\" / \"e2_states.npz\")\n   163\t        st, layers = E[\"states\"], [int(x) for x in E[\"layers\"]]\n   164\t        runs = json.loads((RES / \"e2_meta.json\").read_text())[\"runs\"]\n   165\t        labs = {(r[\"task\"], r[\"template\"], r[\"sample_id\"]): r[\"label\"] for r in jl(RES / \"labelled_c1.jsonl\")}\n   166\t        rep = json.loads((RES / \"readout_i_replication.json\").read_text())\n   167\t        disc = json.loads((RES / \"readout_i_discovery.json\").read_text())\n   168\t        for t in (\"t1\", \"t2\"):\n   169\t            for L in layers:\n   170\t                key = f\"{t}|L{L}|k_pre\"\n   171\t                obj = disc[\"objects\"].get(key)\n   172\t                if obj is None or key not in rep[\"configs\"] or \"transfer_from_exp3\" not in rep[\"configs\"][key]:\n   173\t                    continue\n   174\t                w, mid = np.array(obj[\"raw_dim\"][\"w\"]), obj[\"raw_dim\"][\"mid\"]\n   175\t                rows = [m for m in runs if m[\"task\"] == t and labs.get((t, m[\"template\"], m[\"sample_id\"]))\n   176\t                        in (BANNED[t], SUB[t]) and np.isfinite(st[m[\"i\"], 0, 2, layers.index(L), 0])]\n   177\t                y = np.array([int(labs[(t, m[\"template\"], m[\"sample_id\"])] == BANNED[t]) for m in rows])\n   178\t                H = np.stack([st[m[\"i\"], 0, 2, layers.index(L)].astype(np.float64) for m in rows])\n   179\t                s = H @ w - mid\n   180\t                if 0 < y.sum() < len(y):\n   181\t                    check(f\"replication_dim_auc_{key}\", float(roc_auc_score(y, s)),\n   182\t                          rep[\"configs\"][key][\"transfer_from_exp3\"][\"raw_dim\"][\"auc_pooled\"], tol=2e-3)\n   183\t                    out[\"checks\"][f\"placebo_replication_shuffled_{key}\"] = {\n   184\t                        \"placebo_mean_auc\": float(np.mean([roc_auc_score(rng.permutation(y), s) for _ in range(200)]))}\n   185\t    except Exception as e:  # noqa: BLE001\n   186\t        out[\"checks\"][\"replication_rederivation_error\"] = repr(e)[:300]\n   187\t\n   188\t    # 6) thought anchors: TVD of the first trace from the raw continuation rows\n   189\t    try:\n   190\t        ta = json.loads((RES / \"thought_anchors.json\").read_text())\n   191\t        conts = jl(RES / \"labelled_c3.jsonl\")\n   192\t        for tid, tr in list(ta.get(\"traces\", {}).items())[:4]:\n   193\t            cs = [c for c in conts if str(c[\"trace_id\"]) == tid]\n   194\t\n   195\t            def oc(c: dict) -> str:\n   196\t                e = c.get(\"early_label\")\n   197\t                if e in (None, \"None\") and c.get(\"reached_code\"):\n   198\t                    return str(c.get(\"label\") or \"undecided\")\n   199\t                return str(e or \"undecided\")\n   200\t\n   201\t            df = pd.DataFrame({\"k\": [c[\"boundary_k\"] for c in cs], \"o\": [oc(c) for c in cs]})\n   202\t            tab = pd.crosstab(df.k, df.o, normalize=\"index\")\n   203\t            tv = [float(0.5 * (tab.loc[k] - tab.loc[k - 1]).abs().sum()) for k in range(1, int(df.k.max()) + 1)]\n   204\t            for k, (a, b) in enumerate(zip(tv, tr[\"tvd\"]), start=1):\n   205\t                check(f\"thought_anchor_tvd_trace{tid}_k{k}\", a, b, tol=1e-9)\n   206\t    except Exception as e:  # noqa: BLE001\n   207\t        out[\"checks\"][\"thought_anchor_rederivation_error\"] = repr(e)[:300]\n   208\t\n   209\t    out[\"n_checks\"] = sum(1 for v in out[\"checks\"].values() if isinstance(v, dict) and \"match\" in v)\n   210\t    out[\"n_mismatches\"] = len(out[\"mismatches\"])\n   211\t    (RES / \"verify_headlines.json\").write_text(json.dumps(out, indent=1, default=float))\n   212\t    print(json.dumps({\"n_checks\": out[\"n_checks\"], \"n_mismatches\": out[\"n_mismatches\"],\n   213\t                      \"mismatches\": out[\"mismatches\"]}, indent=1))\n   214\t\n   215\t\n   216\tif __name__ == \"__main__\":\n   217\t    main()", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [28] THINKING · 2026-10-26 09:51:23 UTC

```
I've confirmed `final.py` and `verify_headlines.py` can work off stored per-row data. Now I'll check the replication readout logic in `analysis.py`, the AUC helpers in `readout_i.py`, and `figures.py`.
```

### [29] TOOL CALL — Bash · 2026-10-26 09:51:23 UTC

```
Read analysis.py replication readout section:
cd /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_12/src && sed -n 1,145p analysis.py
```

### [30] TOOL RESULT — Bash · 2026-10-26 09:51:23 UTC

```
{"stdout": "#!/usr/bin/env python3\n\"\"\"Stage 'analyse' (CPU): E3 readouts from the E2 tensors, D1 thought anchors, transfer-test verdicts, J-lens summary.\n\n(i)   replication: exp3-fitted readout objects (top-1 latent, top-20-latent logistic, DiM, raw logistic, top-20 raw\n      dimensions, DiM on the SAE code) applied to the fresh pool's k_pre / k16 states (cross-prompt-set AUC, pooled\n      and within-template, bootstrap over runs), plus the full nested selection rerun inside the fresh pool\n      (leave-one-template-out, within-template permutation null) and the overlap of the top-20 latent lists.\n(ii)  attention from the k_pre query to the condition segment under ban vs neutral vs mention twins (same continuation),\n      per head, per layer third, per segment token; outcome split with a within-template permutation test.\n(iii) prime-veto: NAME(X), NAME(X'), IMPL(X), IMPL(X') latent sets and the DiM projection at R, k_pre and averaged over\n      generated tokens 0..c, under ban / mention / neutral, paired per run, split by outcome.\nD1    thought anchors: outcome distribution per resample point, TVD importance with a simulated multinomial floor,\n      drift toward the trace's own outcome, sentence categories, early-label validity.\nEvery readout is descriptive.\n\"\"\"\n\nfrom __future__ import annotations\n\nimport gc\nfrom collections import Counter, defaultdict\nfrom typing import Any\n\nimport numpy as np\nfrom loguru import logger\nfrom scipy.stats import binomtest\n\nfrom core import BANNED, RESULTS, SUBSTITUTE, TASKS, TEMPLATE_IDS, TENSORS, Timer, read_json, read_jsonl, write_json\n\nUNRES = {\"no_code\", \"unresolved\", None}\nCONDS = [\"ban\", \"mention\", \"neutral\"]\nN_BOOT = 2000\n\n\ndef _labels() -> dict[tuple, dict[str, Any]]:\n    return {(r[\"task\"], r[\"template\"], r[\"sample_id\"]): r for r in read_jsonl(RESULTS / \"labelled_c1.jsonl\")}\n\n\ndef _boot_runs(y: np.ndarray, s: np.ndarray, g: np.ndarray, n_boot: int = N_BOOT, seed: int = 3) -> dict[str, Any]:\n    from readout_i import auc, within_auc\n\n    rng = np.random.default_rng(seed)\n    pa, wa = [], []\n    n = len(y)\n    for _ in range(n_boot):\n        ii = rng.integers(0, n, n)\n        a = auc(y[ii], s[ii])\n        if np.isfinite(a):\n            pa.append(a)\n        w, npair = within_auc(y[ii], s[ii], g[ii])\n        if npair:\n            wa.append(w)\n    q = lambda v: [float(np.quantile(v, .025)), float(np.quantile(v, .975))] if len(v) > 20 else [None, None]  # noqa: E731\n    return {\"pooled_ci_runs\": q(pa), \"within_ci_runs\": q(wa)}\n\n\ndef _codes(H: np.ndarray, S: dict[str, np.ndarray]) -> np.ndarray:\n    from readout_i import sae_encode\n\n    Z, _ = sae_encode(H.astype(np.float32), S, chunk=128)\n    return Z\n\n\n# ---------------------------------------------------------------- (i) replication\ndef readout_i_replication() -> dict[str, Any]:\n    from readout_i import TOPN, apply_objects, auc, load_sae, nested_with_null, rank_units, within_auc\n\n    E = np.load(TENSORS / \"e2_states.npz\")\n    st, layers, pos_keys = E[\"states\"], [int(x) for x in E[\"layers\"]], [str(x) for x in E[\"pos_keys\"]]\n    meta = read_json(RESULTS / \"e2_meta.json\")[\"runs\"]\n    lab = _labels()\n    DISC = read_json(RESULTS / \"readout_i_discovery.json\")\n    out: dict[str, Any] = {\"configs\": {}, \"class_counts\": {}}\n    for li, L in enumerate(layers):\n        S = load_sae(L)\n        for t in TASKS:\n            idx = [m[\"i\"] for m in meta if m[\"task\"] == t]\n            labs = [lab.get((t, meta[i][\"template\"], meta[i][\"sample_id\"]), {}) for i in idx]\n            keep = [(i, r) for i, r in zip(idx, labs) if r.get(\"label\") in (BANNED[t], SUBSTITUTE[t])]\n            out[\"class_counts\"][t] = {\"n_banned\": sum(r[\"label\"] == BANNED[t] for _, r in keep),\n                                      \"n_substitute\": sum(r[\"label\"] == SUBSTITUTE[t] for _, r in keep),\n                                      \"per_template\": {w: [sum(r[\"label\"] == BANNED[t] for i, r in keep\n                                                               if meta[i][\"template\"] == w),\n                                                           sum(r[\"label\"] == SUBSTITUTE[t] for i, r in keep\n                                                               if meta[i][\"template\"] == w)] for w in TEMPLATE_IDS}}\n            for pos in (\"k_pre\", \"k16\"):\n                pj = pos_keys.index(pos)\n                rows = [(i, r) for i, r in keep if np.isfinite(st[i, 0, pj, li, 0])]\n                key = f\"{t}|L{L}|{pos}\"\n                if len(rows) < 10:\n                    out[\"configs\"][key] = {\"status\": \"too few runs\", \"n\": len(rows)}\n                    continue\n                ii = np.array([i for i, _ in rows])\n                y = np.array([int(r[\"label\"] == BANNED[t]) for _, r in rows])\n                g = np.array([TEMPLATE_IDS.index(meta[i][\"template\"]) for i in ii])\n                neg = np.array([bool(r.get(\"negated_first_mention\")) for _, r in rows])\n                H = st[ii, 0, pj, li].astype(np.float32)\n                Z = _codes(H, S)\n                rec: dict[str, Any] = {\"n\": int(len(y)), \"n_banned\": int(y.sum()), \"n_negated_first_mention\": int(neg.sum()),\n                                       \"transfer_from_exp3\": {}}\n                obj = DISC[\"objects\"].get(key)\n                rec[\"run_index\"] = ii.tolist()\n                if obj is not None and int(y.sum()) > 0 and int(len(y) - y.sum()) > 0:\n                    sc = apply_objects(obj, H, Z)\n                    rec[\"run_scores\"] = {m: np.asarray(v, dtype=float).round(5).tolist() for m, v in sc.items()}\n                    for m, s in sc.items():\n                        a = auc(y, s)\n                        w, npair = within_auc(y, s, g)\n                        r2 = {\"auc_pooled\": a, \"auc_within_template\": w, \"n_within_pairs\": npair,\n                              **_boot_runs(y, s, g)}\n                        if neg.any() and pos == \"k_pre\":\n                            k = ~neg\n                            if y[k].sum() > 0 and (1 - y[k]).sum() > 0:\n                                r2[\"auc_pooled_without_negated\"] = auc(y[k], s[k])\n                                r2[\"auc_within_without_negated\"] = within_auc(y[k], s[k], g[k])[0]\n                        rec[\"transfer_from_exp3\"][m] = r2\n                # nested selection inside the fresh pool (leave-one-template-out) + nulls\n                act = (Z != 0).sum(0) >= 5\n                if act.sum() >= TOPN and len(np.unique(g)) >= 3 and y.sum() >= 3 and (1 - y).sum() >= 3:\n                    Za = Z[:, act]\n                    act_ids = np.where(act)[0]\n                    res = nested_with_null(H, Za, y, g, n_perm=100, seed=L)\n                    rec[\"nested_in_fresh_pool\"] = res[\"methods\"]\n                    scr, sgn = rank_units(Za, y)\n                    top = [int(act_ids[j]) for j in np.argsort(-scr, kind=\"stable\")[:TOPN]]\n                    ex = DISC[\"configs\"].get(key, {}).get(\"final_top20\", [])\n                    ex_ids = [int(x[\"latent\"]) for x in ex]\n                    ov = len(set(top) & set(ex_ids))\n                    n_union_active = int(act.sum())\n                    rec[\"top20_fresh\"] = top\n                    rec[\"top20_overlap_with_exp3\"] = {\"overlap\": ov, \"jaccard\": ov / len(set(top) | set(ex_ids))\n                                                      if ex_ids else None,\n                                                      \"expected_overlap_by_chance\": TOPN * len(ex_ids) / max(1, n_union_active),\n                                                      \"n_active_fresh\": n_union_active}\n                out[\"configs\"][key] = rec\n                logger.info(f\"(i) {key}: n={len(y)} banned={int(y.sum())} \" + \" \".join(\n                    f\"{m}={v['auc_within_template']:.2f}\" for m, v in rec[\"transfer_from_exp3\"].items()\n                    if v.get(\"auc_within_template\") is not None and np.isfinite(v[\"auc_within_template\"])))\n        del S\n        gc.collect()\n    write_json(RESULTS / \"readout_i_replication.json\", out)\n    return out\n\n\n# ---------------------------------------------------------------- (ii) attention\ndef readout_ii_attention() -> dict[str, Any]:", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [31] TOOL CALL — Bash · 2026-10-26 09:51:23 UTC

```
Read AUC helpers and figure code:
cd /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_12/src && sed -n 60,160p readout_i.py; echo "======FIG====="; cat -n figures.py
```

### [32] TOOL RESULT — Bash · 2026-10-26 09:51:23 UTC

```
{"stdout": "    out = {\"X\": X[keep], \"mask\": M[keep], \"ks\": K[keep], \"y\": y, \"g\": g, \"labels\": lab,\n           \"rows\": [rows[i] for i in keep], \"all_X\": X, \"all_rows\": rows, \"n_dropped\": int(sum(\n               1 for r in rows if r[\"arm\"] == \"G2\") - len(keep))}\n    return out\n\n\n# ---------------------------------------------------------------- metrics\ndef auc(y: np.ndarray, s: np.ndarray) -> float:\n    y = np.asarray(y)\n    n1, n0 = int(y.sum()), int(len(y) - y.sum())\n    if n1 == 0 or n0 == 0:\n        return float(\"nan\")\n    r = rankdata(s)\n    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))\n\n\ndef within_u(y: np.ndarray, s: np.ndarray, g: np.ndarray) -> tuple[float, int]:\n    \"\"\"(sum of Mann-Whitney U over groups, number of within-group (pos, neg) pairs).\"\"\"\n    U, npairs = 0.0, 0\n    for gg in np.unique(g):\n        m = g == gg\n        yy = y[m]\n        n1, n0 = int(yy.sum()), int(len(yy) - yy.sum())\n        if n1 == 0 or n0 == 0:\n            continue\n        r = rankdata(s[m])\n        U += r[yy == 1].sum() - n1 * (n1 + 1) / 2\n        npairs += n1 * n0\n    return U, npairs\n\n\ndef within_auc(y: np.ndarray, s: np.ndarray, g: np.ndarray) -> tuple[float, int]:\n    U, n = within_u(y, s, g)\n    return (float(U / n) if n else float(\"nan\")), n\n\n\ndef auc_matrix(Y: np.ndarray, S: np.ndarray) -> np.ndarray:\n    \"\"\"Column-wise AUC for labels Y (n x P) and scores S (n x P) (or S (n,) broadcast).\"\"\"\n    if S.ndim == 1:\n        S = np.repeat(S[:, None], Y.shape[1], axis=1)\n    R = rankdata(S, axis=0)\n    n1 = Y.sum(0)\n    n0 = Y.shape[0] - n1\n    with np.errstate(invalid=\"ignore\", divide=\"ignore\"):\n        return ((R * Y).sum(0) - n1 * (n1 + 1) / 2) / (n1 * n0)\n\n\ndef within_auc_matrix(Y: np.ndarray, S: np.ndarray, g: np.ndarray) -> np.ndarray:\n    U = np.zeros(Y.shape[1])\n    NP = np.zeros(Y.shape[1])\n    for gg in np.unique(g):\n        m = g == gg\n        Yg, Sg = Y[m], S[m]\n        n1 = Yg.sum(0)\n        n0 = Yg.shape[0] - n1\n        R = rankdata(Sg, axis=0)\n        U += np.where((n1 > 0) & (n0 > 0), (R * Yg).sum(0) - n1 * (n1 + 1) / 2, 0.0)\n        NP += n1 * n0\n    with np.errstate(invalid=\"ignore\", divide=\"ignore\"):\n        return U / NP\n\n\ndef perm_within(y: np.ndarray, g: np.ndarray, n_perm: int, seed: int = 0) -> np.ndarray:\n    rng = np.random.default_rng(seed)\n    Y = np.repeat(y[:, None], n_perm, axis=1).copy()\n    for gg in np.unique(g):\n        idx = np.where(g == gg)[0]\n        for p in range(n_perm):\n            Y[idx, p] = y[idx][rng.permutation(len(idx))]\n    return Y\n\n\ndef boot_groups(y: np.ndarray, s: np.ndarray, g: np.ndarray, n_boot: int = N_BOOT, seed: int = 1) -> dict[str, Any]:\n    \"\"\"95% CIs of pooled and within-group AUC, resampling groups with replacement.\"\"\"\n    rng = np.random.default_rng(seed)\n    groups = np.unique(g)\n    idx_by = {gg: np.where(g == gg)[0] for gg in groups}\n    wu = {gg: within_u(y[idx_by[gg]], s[idx_by[gg]], np.zeros(len(idx_by[gg]))) for gg in groups}\n    pooled, within = [], []\n    for _ in range(n_boot):\n        pick = rng.choice(groups, len(groups), replace=True)\n        ii = np.concatenate([idx_by[gg] for gg in pick])\n        a = auc(y[ii], s[ii])\n        if np.isfinite(a):\n            pooled.append(a)\n        U = sum(wu[gg][0] for gg in pick)\n        n = sum(wu[gg][1] for gg in pick)\n        if n:\n            within.append(U / n)\n\n    def ci(v: list[float]) -> list[float | None]:\n        return [float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))] if len(v) > 20 else [None, None]\n\n    return {\"pooled_ci\": ci(pooled), \"within_ci\": ci(within)}\n\n\n# ---------------------------------------------------------------- per-fold fitters\ndef _z(train_s: np.ndarray, test_s: np.ndarray) -> np.ndarray:\n    m, sd = train_s.mean(), train_s.std()\n    return (test_s - m) / (sd if sd > 1e-12 else 1.0)\n\n======FIG=====\n     1\t#!/usr/bin/env python3\n     2\t\"\"\"Figures (matplotlib, Agg; PNG + PDF in figures/) drawn only from the results/*.json files.\"\"\"\n     3\t\n     4\tfrom __future__ import annotations\n     5\t\n     6\timport matplotlib\n     7\t\n     8\tmatplotlib.use(\"Agg\")\n     9\timport matplotlib.pyplot as plt  # noqa: E402\n    10\timport numpy as np  # noqa: E402\n    11\tfrom loguru import logger  # noqa: E402\n    12\t\n    13\tfrom core import FIGS, RESULTS, TASKS, read_json  # noqa: E402\n    14\t\n    15\tplt.rcParams.update({\"font.size\": 9, \"pdf.fonttype\": 42, \"ps.fonttype\": 42, \"axes.spines.top\": False,\n    16\t                     \"axes.spines.right\": False})\n    17\tC = [\"#3b6ea8\", \"#d1495b\", \"#66a182\", \"#edae49\", \"#7d5ba6\", \"#8d6a4f\", \"#4f4f4f\"]\n    18\t\n    19\t\n    20\tdef _save(fig, name: str) -> None:\n    21\t    fig.tight_layout()\n    22\t    fig.savefig(FIGS / f\"{name}.png\", dpi=170)\n    23\t    fig.savefig(FIGS / f\"{name}.pdf\")\n    24\t    plt.close(fig)\n    25\t\n    26\t\n    27\tdef fig_layer_probe() -> None:\n    28\t    LP = read_json(RESULTS / \"layer_probe.json\")\n    29\t    fig, axes = plt.subplots(1, 2, figsize=(8, 3), sharey=True)\n    30\t    for ax, t in zip(axes, TASKS):\n    31\t        for k, pos in enumerate([\"k_pre\", \"k16\", \"k_fork\", \"k_post\", \"R\"]):\n    32\t            v = [LP[\"tasks\"][t][f\"{pos}|L{L}\"][\"raw_dim\"][\"auc_within\"] for L in range(8, 29)]\n    33\t            if all(x is None for x in v):\n    34\t                continue\n    35\t            ax.plot(range(8, 29), [np.nan if x is None else x for x in v], marker=\"o\", ms=2.5, color=C[k], label=pos)\n    36\t        ax.axhline(0.5, color=\"grey\", lw=0.6, ls=\"--\")\n    37\t        for L in LP[\"choice\"][\"chosen\"]:\n    38\t            ax.axvline(L, color=\"grey\", lw=0.5, alpha=0.5)\n    39\t        ax.set_title(f\"{t}: within-paraphrase DiM AUC (exp3 ban rows)\")\n    40\t        ax.set_xlabel(\"layer\")\n    41\t    axes[0].set_ylabel(\"held-out AUC (LOPO)\")\n    42\t    axes[1].legend(fontsize=7, frameon=False)\n    43\t    _save(fig, \"fig_layer_probe\")\n    44\t\n    45\t\n    46\tdef fig_transfer() -> None:\n    47\t    T = read_json(RESULTS / \"transfer_summary.json\")\n    48\t    Ls = sorted(T[\"layers\"], key=int)\n    49\t    fig, axes = plt.subplots(1, 2, figsize=(7, 2.8))\n    50\t    x = np.arange(len(Ls))\n    51\t    axes[0].bar(x - 0.18, [T[\"layers\"][L][\"dce_inst\"] for L in Ls], 0.36, color=C[0], label=\"instruct\")\n    52\t    axes[0].bar(x + 0.18, [T[\"layers\"][L][\"dce_base\"] for L in Ls], 0.36, color=C[2], label=\"base\")\n    53\t    axes[0].set_xticks(x, [f\"L{L}\" for L in Ls])\n    54\t    axes[0].set_ylabel(\"spliced-in dCE (nats/token)\")\n    55\t    axes[0].legend(frameon=False, fontsize=7)\n    56\t    r = [T[\"layers\"][L][\"ratio\"] for L in Ls]\n    57\t    ci = [T[\"layers\"][L][\"ratio_ci95\"] or [np.nan, np.nan] for L in Ls]\n    58\t    axes[1].errorbar(x, r, yerr=[[a - c[0] for a, c in zip(r, ci)], [c[1] - a for a, c in zip(r, ci)]], fmt=\"o\",\n    59\t                     color=C[1], capsize=3)\n    60\t    axes[1].axhline(1.5, color=\"grey\", ls=\"--\", lw=0.8)\n    61\t    axes[1].set_xticks(x, [f\"L{L}\" for L in Ls])\n    62\t    axes[1].set_ylabel(\"dCE_inst / dCE_base\")\n    63\t    axes[1].set_title(\"pass if <= 1.5\", fontsize=8)\n    64\t    _save(fig, \"fig_transfer\")\n    65\t\n    66\t\n    67\tdef fig_latent_vs_dim() -> None:\n    68\t    D = read_json(RESULTS / \"readout_i_discovery.json\")\n    69\t    R = read_json(RESULTS / \"readout_i_replication.json\", {})\n    70\t    meths = [\"sae_top1\", \"sae_top20_lr\", \"sae_code_dim\", \"raw_dim\", \"raw_lr\", \"neuron_top1\", \"neuron_top20_lr\"]\n    71\t    keys = [k for k, v in D[\"configs\"].items() if \"methods\" in v and k.endswith(\"k_pre\")] + \\\n    72\t           [k for k, v in D[\"configs\"].items() if \"methods\" in v and k.endswith(\"k16\")]\n    73\t    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharey=True)\n    74\t    w = 0.11\n    75\t    for ax, title, src in ((axes[0], \"discovery (exp3, nested LOPO): within-paraphrase AUC\", \"disc\"),\n    76\t                           (axes[1], \"replication (exp3-fitted objects on the fresh pool): within-template AUC\",\n    77\t                            \"rep\")):\n    78\t        x = np.arange(len(keys))\n    79\t        for j, m in enumerate(meths):\n    80\t            if src == \"disc\":\n    81\t                v = [D[\"configs\"][k][\"methods\"][m][\"auc_within\"] for k in keys]\n    82\t                q = [D[\"configs\"][k][\"methods\"][m].get(\"null_within_q95\") for k in keys]\n    83\t                ax.scatter(x + (j - 3) * w, [np.nan if a is None else a for a in q], marker=\"_\", color=\"grey\", s=30)\n    84\t            else:\n    85\t                v = [R.get(\"configs\", {}).get(k, {}).get(\"transfer_from_exp3\", {}).get(m, {}).get(\n    86\t                    \"auc_within_template\") for k in keys]\n    87\t            ax.bar(x + (j - 3) * w, [np.nan if a is None else a for a in v], w, color=C[j % len(C)], label=m)\n    88\t        ax.axhline(0.5, color=\"grey\", lw=0.6, ls=\"--\")\n    89\t        ax.set_xticks(x, [k.replace(\"|\", \" \") for k in keys], rotation=30, fontsize=7)\n    90\t        ax.set_title(title, fontsize=9)\n    91\t        ax.set_ylim(0, 1)\n    92\t    axes[1].legend(ncol=7, fontsize=6, frameon=False, loc=\"upper center\", bbox_to_anchor=(0.5, -0.32))\n    93\t    _save(fig, \"fig_latent_vs_dim\")\n    94\t\n    95\t\n    96\tdef fig_attention() -> None:\n    97\t    A = read_json(RESULTS / \"readout_ii_attention.json\")\n    98\t    ts = [t for t in TASKS if \"heatmap_ban_minus_neutral_total\" in A[\"tasks\"].get(t, {})]\n    99\t    if not ts:\n   100\t        return\n   101\t    fig, axes = plt.subplots(1, len(ts), figsize=(4.2 * len(ts), 3.6))\n   102\t    axes = np.atleast_1d(axes)\n   103\t    for ax, t in zip(axes, ts):\n   104\t        M = np.array(A[\"tasks\"][t][\"heatmap_ban_minus_neutral_total\"])\n   105\t        v = np.nanmax(np.abs(M))\n   106\t        im = ax.imshow(M.T, aspect=\"auto\", cmap=\"RdBu_r\", vmin=-v, vmax=v, origin=\"lower\")\n   107\t        ax.set_xlabel(\"layer\")\n   108\t        ax.set_ylabel(\"head\")\n   109\t        ax.set_title(f\"{t}: attention mass k_pre -> segment, ban - neutral\", fontsize=8)\n   110\t        fig.colorbar(im, ax=ax, fraction=0.04)\n   111\t    _save(fig, \"fig_attention\")\n   112\t\n   113\t\n   114\tdef fig_prime_veto() -> None:\n   115\t    P = read_json(RESULTS / \"readout_iii_prime_veto.json\")\n   116\t    keys = sorted(P[\"configs\"])\n   117\t    fig, axes = plt.subplots(1, 2, figsize=(9, 3))\n   118\t    for ax, s in zip(axes, (\"NAME_X\", \"IMPL_X\")):\n   119\t        x = np.arange(len(keys))\n   120\t        for j, c in enumerate((\"ban\", \"mention\", \"neutral\")):\n   121\t            v = [P[\"configs\"][k][\"positions\"][\"k_pre\"][s][\"means\"][c] for k in keys]\n   122\t            ax.bar(x + (j - 1) * 0.27, v, 0.27, color=C[j], label=c)\n   123\t        ax.set_xticks(x, [k.replace(\"|\", \" \") for k in keys], rotation=30, fontsize=7)\n   124\t        ax.set_title(f\"{s}: summed latent activation at k_pre (same continuation)\", fontsize=8)\n   125\t    axes[0].legend(frameon=False, fontsize=7)\n   126\t    _save(fig, \"fig_prime_veto\")\n   127\t\n   128\t\n   129\tdef fig_thought_anchors() -> None:\n   130\t    TA = read_json(RESULTS / \"thought_anchors.json\")\n   131\t    tr = TA.get(\"traces\", {})\n   132\t    if not tr:\n   133\t        return\n   134\t    n = len(tr)\n   135\t    fig, axes = plt.subplots(n, 1, figsize=(7, 1.4 * n), sharex=True)\n   136\t    axes = np.atleast_1d(axes)\n   137\t    cat_col = {\"BAN_RESTATEMENT\": C[1], \"SUBSTITUTE_NAMING\": C[2], \"ALTERNATIVE_LISTING\": C[3],\n   138\t               \"PROBLEM_RESTATEMENT\": C[0], \"OTHER\": C[6], \"OTHER_MECHANISM\": C[4]}\n   139\t    for ax, (tid, r) in zip(axes, sorted(tr.items(), key=lambda kv: int(kv[0]))):\n   140\t        k = np.arange(1, len(r[\"tvd\"]) + 1)\n   141\t        ax.bar(k, r[\"tvd\"], color=[cat_col.get(c, C[6]) for c in r[\"sentence_categories\"][:len(k)]])\n   142\t        ax.plot(k, r[\"noise_floor_q95\"], \"k_\", ms=10)\n   143\t        ax.set_ylabel(f\"tr {tid}\\n{r['task']}\", fontsize=7)\n   144\t        ax.set_ylim(0, 1)\n   145\t    axes[-1].set_xlabel(\"sentence k (TVD between D_k and D_k-1; black: 95% multinomial floor)\")\n   146\t    handles = [plt.Rectangle((0, 0), 1, 1, color=v) for v in cat_col.values()]\n   147\t    axes[0].legend(handles, list(cat_col), ncol=3, fontsize=6, frameon=False)\n   148\t    _save(fig, \"fig_thought_anchors\")\n   149\t\n   150\t\n   151\tdef fig_same_seed() -> None:\n   152\t    S = read_json(RESULTS / \"same_seed.json\")\n   153\t    fig, axes = plt.subplots(2, 2, figsize=(8, 5.2), sharex=True)\n   154\t    Ts = [0.7, 1.0, 1.3]\n   155\t    for col, t in enumerate(TASKS):\n   156\t        for row, (metric, ylab) in enumerate(((\"idea_change_rate\", \"P(label_T != label_0.3)\"),\n   157\t                                              (\"phrasing_change_rate_theta0.8\", \"P(Jaccard < 0.8 | same label)\"))):\n   158\t            ax = axes[row, col]\n   159\t            for j, cond in enumerate((\"baseline\", \"ban\")):\n   160\t                for kind, ls in ((\"same_seed\", \"-\"), (\"different_seed\", \":\")):\n   161\t                    v = [S[\"cells\"].get(f\"{t}|{cond}|T{T}\", {}).get(kind, {}).get(metric) for T in Ts]\n   162\t                    ax.plot(Ts, [np.nan if a is None else a for a in v], ls, marker=\"o\", color=C[j],\n   163\t                            label=f\"{cond} {kind.replace('_', '-')}\")\n   164\t            ax.set_ylim(-0.03, 1.03)\n   165\t            if col == 0:\n   166\t                ax.set_ylabel(ylab, fontsize=8)\n   167\t            if row == 0:\n   168\t                ax.set_title(f\"{t}: change vs the same seed's T=0.3 program (CRN)\", fontsize=8)\n   169\t            else:\n   170\t                ax.set_xlabel(\"temperature T\")\n   171\t    axes[0, 1].legend(fontsize=6, frameon=False)\n   172\t    _save(fig, \"fig_same_seed\")\n   173\t\n   174\t\n   175\tdef fig_jlens() -> None:\n   176\t    J = read_json(RESULTS / \"jlens.json\", {})\n   177\t    if not J:\n   178\t        return\n   179\t    g = J[\"gate\"]\n   180\t    Ls = sorted(g[\"layers\"], key=int)\n   181\t    o = g[\"orientation\"]\n   182\t    fig, ax = plt.subplots(figsize=(4.5, 2.8))\n   183\t    ax.plot([int(L) for L in Ls], [g[\"layers\"][L][\"logit_lens\"][\"top1\"] for L in Ls], \"o-\", color=C[0],\n   184\t            label=\"logit lens\")\n   185\t    ax.plot([int(L) for L in Ls], [g[\"layers\"][L][f\"jlens_{o}\"][\"top1\"] for L in Ls], \"o-\", color=C[1],\n   186\t            label=f\"J-lens ({o})\")\n   187\t    ax.set_xlabel(\"source layer\")\n   188\t    ax.set_ylabel(\"top-1 agreement with model\")\n   189\t    ax.legend(frameon=False, fontsize=7)\n   190\t    ax.set_title(f\"J-lens gate: pass={g['gate_pass']}\", fontsize=8)\n   191\t    _save(fig, \"fig_jlens\")\n   192\t\n   193\t\n   194\tdef run_figures() -> None:\n   195\t    for fn in (fig_layer_probe, fig_transfer, fig_latent_vs_dim, fig_attention, fig_prime_veto, fig_thought_anchors,\n   196\t               fig_same_seed, fig_jlens):\n   197\t        try:\n   198\t            fn()\n   199\t            logger.info(f\"figure {fn.__name__} written\")\n   200\t        except Exception as e:  # noqa: BLE001 - a missing input skips that figure only\n   201\t            logger.warning(f\"figure {fn.__name__} skipped: {e!r}\")", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [33] ASSISTANT · 2026-10-26 09:51:47 UTC

```
Now let me inspect the full fresh-pool dataset programmatically (summaries only, no full dump): label counts per task/template, score coverage, and the pipeline's reference numbers.
```

### [34] TOOL CALL — Bash · 2026-10-26 09:51:47 UTC

```
Summarise fresh-pool labels, scores and reference numbers:
cd /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_12 && python3 - <<'EOF'
import json
from collections import Counter, defaultdict
d = json.load(open("full_method_out.json"))
for ds in d["datasets"]:
    print(ds["dataset"], len(ds["examples"]))
fp = [ds for ds in d["datasets"] if ds["dataset"]=="fresh_ban_pool_protocol_v2"][0]["examples"]
cnt = defaultdict(Counter)
sc = Counter()
for e in fp:
    cnt[(e["metadata_task"], e["metadata_template"])][e["output"]] += 1
    sc[(e["metadata_task"], bool(e["metadata_readout_scores_k_pre"]), e["metadata_readout_layer"])] += 1
for k in sorted(cnt): print(k, dict(cnt[k]))
print("score coverage", sc)
print("keys of scores", Counter(tuple(sorted(e["metadata_readout_scores_k_pre"].keys())) for e in fp))
print("input lens", min(len(e["input"]) for e in fp), max(len(e["input"]) for e in fp))
print("passed", Counter((e["metadata_task"], e["metadata_passed"]) for e in fp))
print("neg first", Counter((e["metadata_task"], e["metadata_negated_first_mention"]) for e in fp))
print("labeller src", Counter(e["metadata_labeller_source"] for e in fp))
print("evidence", Counter(e["metadata_evidence_term"] for e in fp).most_common(12))
print("commit None", sum(e["metadata_commit_idx"] is None for e in fp))
m = d["metadata"]
print(json.dumps(m["fresh_pool_summary"]["per_task"]["t1"]["W4"], indent=0)[:800])
rep = m["readout_i_replication"]
print("rep config keys", list(rep["configs"].keys()))
for k in ["t1|L27|k_pre", "t2|L27|k_pre"]:
    c = rep["configs"][k]
    print(k, "n", c.get("n"), "n_banned", c.get("n_banned"), "keys", list(c.keys()))
    for meth, r in c["transfer_from_exp3"].items():
        print("   ", meth, {kk: (round(vv,4) if isinstance(vv,float) else vv) for kk, vv in r.items()})
print("class_counts", json.dumps(rep["class_counts"]))
EOF
```

### [35] TOOL RESULT — Bash · 2026-10-26 09:51:47 UTC

```
{"stdout": "fresh_ban_pool_protocol_v2 200\nsame_seed_crn 480\nthought_anchor_base_traces 10\nthought_anchor_continuations 432\n('t1', 'W1') {'dfs': 20}\n('t1', 'W2') {'dfs': 20}\n('t1', 'W3') {'dfs': 20}\n('t1', 'W4') {'dfs': 5, 'bfs': 15}\n('t1', 'W5') {'dfs': 20}\n('t2', 'W1') {'bf_spfa': 19, 'dijkstra': 1}\n('t2', 'W2') {'bf_spfa': 20}\n('t2', 'W3') {'dijkstra': 5, 'bf_spfa': 14, 'other': 1}\n('t2', 'W4') {'bf_spfa': 14, 'dijkstra': 6}\n('t2', 'W5') {'bf_spfa': 19, 'dijkstra': 1}\nscore coverage Counter({('t2', True, 27): 99, ('t1', True, 27): 97, ('t1', False, 27): 3, ('t2', False, 27): 1})\nkeys of scores Counter({('neuron_top1', 'neuron_top20_lr', 'raw_dim', 'raw_lr', 'sae_code_dim', 'sae_top1', 'sae_top20_lr'): 196, (): 4})\ninput lens 717 998\npassed Counter({('t2', True): 96, ('t1', False): 66, ('t1', True): 34, ('t2', False): 4})\nneg first Counter({('t1', False): 100, ('t2', False): 92, ('t2', True): 8})\nlabeller src Counter({'agree': 119, 'judge': 81})\nevidence [('deque', 89), ('dfs', 39), ('stack', 18), ('Recurs', 14), ('Bellman', 14), ('queue', 6), ('heapq', 6), ('DFS', 5), (None, 3), ('depth-first', 3), ('Stack', 2), ('Depth-first', 1)]\ncommit None 3\n{\n\"n\": 20,\n\"n_coded\": 20,\n\"banned_share\": 0.75,\n\"banned_share_wilson\": [\n0.531299122381256,\n0.8881382985923343\n],\n\"avoidance\": 0.25,\n\"n_attempted_non_banned\": 5,\n\"event_gate_pass\": false,\n\"compliant_share\": 0.15,\n\"pass_rate\": 0.45,\n\"landing\": {\n\"dfs\": 5,\n\"bfs\": 15\n},\n\"commit_idx_found\": 20,\n\"negated_first_mention\": 0\n}\nrep config keys ['t1|L15|k_pre', 't1|L15|k16', 't2|L15|k_pre', 't2|L15|k16', 't1|L20|k_pre', 't1|L20|k16', 't2|L20|k_pre', 't2|L20|k16', 't1|L27|k_pre', 't1|L27|k16', 't2|L27|k_pre', 't2|L27|k16']\nt1|L27|k_pre n 97 n_banned 15 keys ['n', 'n_banned', 'n_negated_first_mention', 'transfer_from_exp3', 'run_index', 'nested_in_fresh_pool', 'top20_fresh', 'top20_overlap_with_exp3']\n    sae_top1 {'auc_pooled': 0.722, 'auc_within_template': 0.52, 'n_within_pairs': 75, 'pooled_ci_runs': [0.5547753348946571, 0.8739825189113613], 'within_ci_runs': [0.17291666567325592, 0.8157894611358643]}\n    sae_top20_lr {'auc_pooled': 0.9268, 'auc_within_template': 0.7067, 'n_within_pairs': 75, 'pooled_ci_runs': [0.859881621187801, 0.9759766814975148], 'within_ci_runs': [0.4255050505050505, 0.9294806985294117]}\n    raw_dim {'auc_pooled': 0.9854, 'auc_within_template': 1.0, 'n_within_pairs': 75, 'pooled_ci_runs': [0.9620557029177719, 0.999021223874165], 'within_ci_runs': [1.0, 1.0]}\n    raw_lr {'auc_pooled': 0.974, 'auc_within_template': 1.0, 'n_within_pairs': 75, 'pooled_ci_runs': [0.9395386590154032, 0.995697074010327], 'within_ci_runs': [1.0, 1.0]}\n    neuron_top20_lr {'auc_pooled': 0.9537, 'auc_within_template': 1.0, 'n_within_pairs': 75, 'pooled_ci_runs': [0.9031684981684982, 0.9882352941176471], 'within_ci_runs': [1.0, 1.0]}\n    neuron_top1 {'auc_pooled': 0.6996, 'auc_within_template': 0.7067, 'n_within_pairs': 75, 'pooled_ci_runs': [0.4905191645026207, 0.8819654047489165], 'within_ci_runs': [0.4533730149269104, 0.9230769276618958]}\n    sae_code_dim {'auc_pooled': 0.9797, 'auc_within_template': 1.0, 'n_within_pairs': 75, 'pooled_ci_runs': [0.948695652173913, 0.9968683282279773], 'within_ci_runs': [1.0, 1.0]}\nt2|L27|k_pre n 99 n_banned 13 keys ['n', 'n_banned', 'n_negated_first_mention', 'transfer_from_exp3', 'run_index', 'nested_in_fresh_pool', 'top20_fresh', 'top20_overlap_with_exp3']\n    sae_top1 {'auc_pooled': 0.5581, 'auc_within_template': 0.513, 'n_within_pairs': 192, 'pooled_ci_runs': [0.5274725556373596, 0.5926033630967139], 'within_ci_runs': [0.5, 0.5493843838572502], 'auc_pooled_without_negated': 0.5581, 'auc_within_without_negated': 0.5}\n    sae_top20_lr {'auc_pooled': 0.7652, 'auc_within_template': 0.7682, 'n_within_pairs': 192, 'pooled_ci_runs': [0.6225264429812272, 0.9042370880936642], 'within_ci_runs': [0.5877610245410384, 0.9294921875], 'auc_pooled_without_negated': 1.0, 'auc_within_without_negated': 1.0}\n    raw_dim {'auc_pooled': 0.8175, 'auc_within_template': 0.7604, 'n_within_pairs': 192, 'pooled_ci_runs': [0.6919697390450433, 0.9285731390257252], 'within_ci_runs': [0.5859699325590109, 0.9130600308982563], 'auc_pooled_without_negated': 1.0, 'auc_within_without_negated': 1.0}\n    raw_lr {'auc_pooled': 0.5613, 'auc_within_template': 0.6641, 'n_within_pairs': 192, 'pooled_ci_runs': [0.32459393814997267, 0.8137061247268927], 'within_ci_runs': [0.43702525252525254, 0.8775599193165637], 'auc_pooled_without_negated': 1.0, 'auc_within_without_negated': 1.0}\n    neuron_top20_lr {'auc_pooled': 0.5559, 'auc_within_template': 0.6589, 'n_within_pairs': 192, 'pooled_ci_runs': [0.3222087813620072, 0.8073195413061258], 'within_ci_runs': [0.42102927436935533, 0.8768828053609503], 'auc_pooled_without_negated': 1.0, 'auc_within_without_negated': 1.0}\n    neuron_top1 {'auc_pooled': 0.6369, 'auc_within_template': 0.6771, 'n_within_pairs': 192, 'pooled_ci_runs': [0.44156764894723893, 0.8420430690050125], 'within_ci_runs': [0.4642785586416721, 0.8843819916248319], 'auc_pooled_without_negated': 1.0, 'auc_within_without_negated': 1.0}\n    sae_code_dim {'auc_pooled': 0.8166, 'auc_within_template': 0.7656, 'n_within_pairs': 192, 'pooled_ci_runs': [0.6814774114774115, 0.9284468438538206], 'within_ci_runs': [0.5889721481391684, 0.9166743542435424], 'auc_pooled_without_negated': 1.0, 'auc_within_without_negated': 1.0}\nclass_counts {\"t1\": {\"n_banned\": 15, \"n_substitute\": 85, \"per_template\": {\"W1\": [0, 20], \"W2\": [0, 20], \"W3\": [0, 20], \"W4\": [15, 5], \"W5\": [0, 20]}}, \"t2\": {\"n_banned\": 13, \"n_substitute\": 86, \"per_template\": {\"W1\": [1, 19], \"W2\": [0, 20], \"W3\": [5, 14], \"W4\": [6, 14], \"W5\": [1, 19]}}}", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [36] THINKING · 2026-10-26 09:53:13 UTC

```
The fresh ban pool (200 runs) has per-run labels, prompts, and exp3-fitted readout scores at L27/k_pre for all 7 methods, making it the right dataset. Next I'll check how C1 rows are keyed (seed ↔ sample_id), the original row schema, and pinned versions.
```

### [37] TOOL CALL — Bash · 2026-10-26 09:53:13 UTC

```
Check seed/sample_id mapping, row keys and version pins:
cd /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_12 && grep -n "sample_id\|SEED_FRESH\|seed" src/vllm_stage.py | head -30; echo "----C1 ROW KEYS----"; head -n 1 results/labelled_c1.jsonl | python3 -c "import json,sys; r=json.loads(sys.stdin.read()); print({k:(repr(v)[:80]) for k,v in r.items()})"; echo "----PYPROJECT----"; grep -nE "loguru|numpy|pandas|scikit|scipy|matplotlib|^requires-python" pyproject.toml
```

### [38] TOOL RESULT — Bash · 2026-10-26 09:53:13 UTC

````
{"stdout": "2:\"\"\"vLLM block (GPU). Session 1: C1 fresh ban pool + E5 same-seed common-random-numbers (CRN) rows + Gumbel-max\n5:The CRN sampler is a vLLM V1 per-request logits processor: at step t of row (seed, T) it takes the top-10 logits\n7:reaches U[seed][t] with U[seed] = numpy default_rng(seed).random(1024), shared across T, tasks and conditions\n10:token = argmax(logit / T + G[seed][t][slot]) with G from default_rng(10**6 + seed) (Ravfogel et al. 2025's\n30:                  SEED_FRESH, TASKS, TEMPLATE_IDS, Timer, add_deviation, append_jsonl, read_json, read_jsonl,\n41:    \"\"\"Per-request CRN / Gumbel-max sampler; inactive for requests without extra_args['crn_seed'].\"\"\"\n48:        if \"crn_seed\" not in ea:\n50:        seed, T, mode, rid = int(ea[\"crn_seed\"]), float(ea[\"crn_T\"]), str(ea.get(\"crn_mode\", \"icdf\")), ea[\"crn_row\"]\n52:            U = np.random.default_rng(seed).random(CRN_MAX_STEPS)\n56:            G = np.random.default_rng(GUMBEL_SEED_OFFSET + seed).gumbel(size=(CRN_MAX_STEPS, 10))\n90:              enable_prefix_caching=True, seed=0, enforce_eager=enforce_eager,\n124:    done = {(r[\"task\"], r[\"template\"], r[\"sample_id\"]) for r in read_jsonl(out_path)}\n130:                seed = SEED_FRESH + i\n133:                    jobs.append({\"task\": t, \"template\": w, \"condition\": \"ban\", \"sample_id\": s, \"seed\": seed,\n144:                                     seed=j[\"seed\"], stop_token_ids=STOP_IDS) for j in part]\n159:                                 \"seed\": s, \"T\": T, \"coupling\": \"icdf_top10\", \"prompt_key\": key,\n169:                             extra_args={\"crn_seed\": j[\"seed\"], \"crn_T\": j[\"T\"], \"crn_mode\": mode,\n181:def stage_e5(llm, P: dict[str, Any], n_seeds: int) -> None:\n184:    all_rows = [r for r in crn_rows(P) if r[\"seed\"] < n_seeds]\n187:        # 10-row stage: 1 seed x 4 T x 2 conditions (+2 repeats of identical rows) -> s/token extrapolation\n188:        first = [r for r in todo if r[\"seed\"] == todo[0][\"seed\"] and r[\"task\"] == todo[0][\"task\"]][:8]\n201:    # determinism rerun: 2 seeds x 4 T of the W1 ban, task t1, in one batch of 8\n204:        jobs = [r for r in all_rows if r[\"task\"] == \"t1\" and r[\"condition\"] == \"ban\" and r[\"seed\"] in (0, 1)]\n210:def stage_gumbel(llm, P: dict[str, Any], n_seeds: int = 20) -> None:\n215:        for s in range(n_seeds):\n217:                jobs.append({\"task\": t, \"condition\": \"ban\", \"template\": \"W1\", \"seed\": s, \"T\": T,\n227:def session1(n_per_template: int = 40, n_seeds: int = 50, gumbel_seeds: int = 20, smoke: bool = False) -> None:\n240:                  \"the exact coupling (shared U[seed][t], inverse CDF over the (-logit, id)-sorted top-10).\",\n249:                       [SamplingParams(temperature=1.0, max_tokens=64, seed=1, stop_token_ids=STOP_IDS)] * 2,\n252:        jobs = [{\"task\": \"t1\", \"condition\": \"ban\", \"template\": \"W1\", \"seed\": 0, \"T\": T, \"coupling\": \"icdf_top10\",\n----C1 ROW KEYS----\n{'task': \"'t1'\", 'template': \"'W1'\", 'condition': \"'ban'\", 'sample_id': '0', 'seed': '20261020', 'prompt_key': \"'t1|ban|W1'\", 'arm': \"'C1_fresh_pool'\", 'model': \"'Qwen/Qwen3-8B-FP8'\", 'thinking': 'False', 'decoding': \"'T1.0_topp1.0_topk-off_max1024_thinkoff'\", 'prompt_len': '246', 'gen_token_ids': '[73594, 12669, 198, 750, 11625, 25319, 11, 1191, 11, 5795, 982, 262, 421, 537, 5', 'text': '\"```python\\\\ndef solve(grid, start, goal):\\\\n    if not grid or start == goal:\\\\n  ', 'finish_reason': \"'stop'\", 'n_gen_tokens': '258', 'extract_method': \"'python_block'\", 'code': '\"def solve(grid, start, goal):\\\\n    if not grid or start == goal:\\\\n        if gr', 'code_sha256': \"'0a1bb728dd1717b50e57e29e291a9160f09ac32ae5b4a0d376c33c4e0ba63eb2'\", 'passed': 'False', 'test_error': \"'wrong_answer'\", 'fail_case': \"'start_wall'\", 'runtime_label': \"'dfs'\", 'ast_label': \"'dfs'\", 'judge_label': 'None', 'label': \"'dfs'\", 'labeller_source': \"'agree'\", 'commit_idx': '127', 'evidence_term': \"'stack'\", 'commit_idx_strict': 'None', 'evidence_term_strict': 'None', 'matched_mode': \"'dfs'\", 'negated_first_mention': 'False'}\n----PYPROJECT----\n5:requires-python = \"==3.12.*\"\n8:# numpy, scipy, scikit-learn, pandas, networkx, loguru, openai, aiohttp, tenacity, matplotlib, psutil, pyyaml;\n72:  \"loguru==0.7.3\",\n75:  \"matplotlib==3.11.2\",\n86:  \"numpy==2.2.6\",\n114:  \"pandas==3.0.6\",\n147:  \"scikit-learn==1.9.1\",\n148:  \"scipy==1.18.1\",", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX", "interrupted": false, "isImage": false, "noOutputExpected": false}
````

### [39] TOOL CALL — Bash · 2026-10-26 09:53:21 UTC

```
Read C1 job construction and check seed mapping:
cd /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_12 && sed -n 118,150p src/vllm_stage.py; echo; python3 - <<'EOF'
import json
rows=[json.loads(l) for l in open("results/labelled_c1.jsonl")]
print(len(rows))
print(sorted({(r["seed"]-20261020, r["sample_id"]) for r in rows if r["task"]=="t1" and r["template"]=="W1"})[:25])
print("t2 W1:", sorted({(r["seed"]-20261020, r["sample_id"]) for r in rows if r["task"]=="t2" and r["template"]=="W1"})[:5])
print("seed unique per (task,template)?", len({(r["task"],r["template"],r["seed"]) for r in rows}))
EOF
```

### [40] TOOL RESULT — Bash · 2026-10-26 09:53:21 UTC

```
{"stdout": "def stage_c1(llm, P: dict[str, Any], n_per_template: int) -> None:\n    \"\"\"C1 fresh protocol-v2 ban pool: W1-W5 ban x n per task, T=1.0, top_p=1.0, max 1024, thinking off.\"\"\"\n    from vllm import SamplingParams\n\n    out_path = RAW / \"c1_fresh_pool.jsonl\"\n    done = {(r[\"task\"], r[\"template\"], r[\"sample_id\"]) for r in read_jsonl(out_path)}\n    jobs = []\n    i = 0\n    for t in TASKS:\n        for w in TEMPLATE_IDS:\n            for s in range(n_per_template):\n                seed = SEED_FRESH + i\n                i += 1\n                if (t, w, s) not in done:\n                    jobs.append({\"task\": t, \"template\": w, \"condition\": \"ban\", \"sample_id\": s, \"seed\": seed,\n                                 \"prompt_key\": f\"{t}|ban|{w}\"})\n    if not jobs:\n        logger.info(\"C1: all runs present\")\n        return\n    stages = [jobs[:10], jobs[10:100], jobs[100:]]\n    for k, part in enumerate(stages):\n        if not part:\n            continue\n        with Timer(f\"C1_part{k}\", gpu=True, n=len(part)):\n            params = [SamplingParams(temperature=MAIN_DECODING[\"temperature\"], top_p=1.0, max_tokens=1024,\n                                     seed=j[\"seed\"], stop_token_ids=STOP_IDS) for j in part]\n            res = generate(llm, [_prompt(P, j[\"prompt_key\"]) for j in part], params, f\"C1 part {k}\")\n            rows = [{**j, \"arm\": \"C1_fresh_pool\", \"model\": MODEL_GEN, \"thinking\": False,\n                     \"decoding\": \"T1.0_topp1.0_topk-off_max1024_thinkoff\",\n                     \"prompt_len\": len(_prompt(P, j[\"prompt_key\"])), **r} for j, r in zip(part, res)]\n            append_jsonl(out_path, rows)\n\n\n200\n[(0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7), (8, 8), (9, 9), (10, 10), (11, 11), (12, 12), (13, 13), (14, 14), (15, 15), (16, 16), (17, 17), (18, 18), (19, 19)]\nt2 W1: [(100, 0), (101, 1), (102, 2), (103, 3), (104, 4)]\nseed unique per (task,template)? 200", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [41] THINKING · 2026-10-26 09:55:19 UTC

```
I've worked out that sample_id derives from the seed via `(seed − 20261020) % 20`. Next I'll check where the unscored rows sit and verify against the full-run reference values.
```

### [42] TOOL CALL — Bash · 2026-10-26 09:55:19 UTC

```
Locate unscored rows and reference verification values:
cd /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_12 && python3 - <<'EOF'
import json
from collections import Counter
d = json.load(open("full_method_out.json"))
fp = d["datasets"][0]["examples"]
for e in fp:
    if not e["metadata_readout_scores_k_pre"]:
        print("UNSCORED", e["metadata_task"], e["metadata_template"], e["metadata_seed"], e["output"], e["metadata_commit_idx"], e["metadata_evidence_term"])
hv = d["metadata"]["headline_verification"]
print("n_checks", hv["n_checks"], "mism", hv["n_mismatches"])
for k, v in hv["checks"].items():
    if "fresh_pool" in k or "replication" in k:
        print(k, v)
# predicted-class agreement with label for scored rows
for t in ("t1", "t2"):
    rows = [e for e in fp if e["metadata_task"] == t and e["metadata_readout_scores_k_pre"]]
    for m in ["predict_dim_baseline_exp3_fitted", "predict_sae_top1_latent_exp3_fitted", "predict_sae_top20_latents_exp3_fitted"]:
        print(t, m, Counter((e["output"], e[m]) for e in rows))
print(d["metadata"]["fresh_pool_summary"]["per_task"]["t2"]["pooled"])
EOF
```

### [43] TOOL RESULT — Bash · 2026-10-26 09:55:19 UTC

```
{"stdout": "UNSCORED t1 W2 20261048 dfs None None\nUNSCORED t1 W3 20261064 dfs None None\nUNSCORED t1 W3 20261068 dfs None None\nUNSCORED t2 W3 20261173 other 6 deque\nn_checks 69 mism 0\nfresh_pool_banned_share_t1 {'rederived': 0.15, 'pipeline': 0.15, 'match': True}\nfresh_pool_banned_share_t2 {'rederived': 0.13, 'pipeline': 0.13, 'match': True}\nreplication_dim_auc_t1|L15|k_pre {'rederived': 0.7967479674796749, 'pipeline': 0.7967479674796748, 'match': True}\nplacebo_replication_shuffled_t1|L15|k_pre {'placebo_mean_auc': 0.4894308943089431}\nreplication_dim_auc_t1|L20|k_pre {'rederived': 0.9430894308943089, 'pipeline': 0.943089430894309, 'match': True}\nplacebo_replication_shuffled_t1|L20|k_pre {'placebo_mean_auc': 0.4989817073170732}\nreplication_dim_auc_t1|L27|k_pre {'rederived': 0.9853658536585366, 'pipeline': 0.9853658536585366, 'match': True}\nplacebo_replication_shuffled_t1|L27|k_pre {'placebo_mean_auc': 0.5022520325203252}\nreplication_dim_auc_t2|L15|k_pre {'rederived': 0.6359570661896244, 'pipeline': 0.6359570661896243, 'match': True}\nplacebo_replication_shuffled_t2|L15|k_pre {'placebo_mean_auc': 0.4946153846153847}\nreplication_dim_auc_t2|L20|k_pre {'rederived': 0.6207513416815743, 'pipeline': 0.6207513416815742, 'match': True}\nplacebo_replication_shuffled_t2|L20|k_pre {'placebo_mean_auc': 0.5003577817531306}\nreplication_dim_auc_t2|L27|k_pre {'rederived': 0.817531305903399, 'pipeline': 0.817531305903399, 'match': True}\nplacebo_replication_shuffled_t2|L27|k_pre {'placebo_mean_auc': 0.5113886404293381}\nt1 predict_dim_baseline_exp3_fitted Counter({('dfs', 'dfs'): 82, ('bfs', 'bfs'): 9, ('bfs', 'dfs'): 6})\nt1 predict_sae_top1_latent_exp3_fitted Counter({('dfs', 'dfs'): 56, ('dfs', 'bfs'): 26, ('bfs', 'bfs'): 9, ('bfs', 'dfs'): 6})\nt1 predict_sae_top20_latents_exp3_fitted Counter({('dfs', 'dfs'): 82, ('bfs', 'bfs'): 8, ('bfs', 'dfs'): 7})\nt2 predict_dim_baseline_exp3_fitted Counter({('bf_spfa', 'bf_spfa'): 72, ('bf_spfa', 'dijkstra'): 14, ('dijkstra', 'bf_spfa'): 7, ('dijkstra', 'dijkstra'): 6})\nt2 predict_sae_top1_latent_exp3_fitted Counter({('bf_spfa', 'bf_spfa'): 86, ('dijkstra', 'bf_spfa'): 13})\nt2 predict_sae_top20_latents_exp3_fitted Counter({('bf_spfa', 'bf_spfa'): 74, ('bf_spfa', 'dijkstra'): 12, ('dijkstra', 'bf_spfa'): 7, ('dijkstra', 'dijkstra'): 6})\n{'n': 100, 'n_coded': 100, 'banned_share': 0.13, 'banned_share_wilson': [0.07757167427240512, 0.20980351440076428], 'avoidance': 0.87, 'n_attempted_non_banned': 87, 'event_gate_pass': True, 'compliant_share': 0.83, 'pass_rate': 0.96, 'landing': {'bf_spfa': 86, 'dijkstra': 13, 'other': 1}, 'commit_idx_found': 100, 'negated_first_mention': 8}", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [44] THINKING · 2026-10-26 09:55:45 UTC

```
I've confirmed the data details (W4 is the only template with both BFS/DFS in T1, Dijkstra spans W1/W3/W4/W5 in T2, and 4 rows are missing k_pre states). Now I'll write a curation script to build a stratified 10-run sample per task×template cell with interleaved classes for balanced prefixes, joining in program text and full-pool reference numbers.
```

### [45] TOOL CALL — Bash · 2026-10-26 09:55:45 UTC

```
Create tools directory and check Python:
mkdir -p /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/tools && python3 --version && which python3 uv
```

### [46] TOOL RESULT — Bash · 2026-10-26 09:55:45 UTC

```
{"stdout": "Python 3.12.14\n/usr/local/bin/python3\n/usr/bin/uv", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [47] TOOL CALL — Write · 2026-10-26 09:56:13 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/tools/build_mini_demo_data.py

#!/usr/bin/env python3
"""Curate mini_demo_data.json from the artifact's full_method_out.json (dataset fresh_ban_pool_protocol_v2).

Selection (deterministic, no randomness):
  * 10 of the 20 runs in every task x template cell (2 tasks x 5 ban templates -> 100 runs);
  * per cell, labels are allocated proportionally (largest remainder), every label present keeps >= 1 run,
    ties go to the minority class (more banned-vs-substitute pairs for the within-template AUC);
  * inside a label, runs are taken evenly spaced over the seeds, runs with a k_pre readout score first;
    the one T1 W2 run without a k_pre state is kept on purpose (it shows the pipeline's 'no state' path);
  * each cell is ordered so that the two readout classes alternate (minority first) and runs that the readout
    cannot use (no score, or a third label) come last, so any per-cell prefix stays as balanced as possible;
  * the generated program text (results/labelled_c1.jsonl, matched on task/template/seed and code_sha256) is
    added as metadata_code, and the full 200-run pool's pipeline numbers are kept under metadata.reference_full_pool.

  python3 tools/build_mini_demo_data.py --full <artifact>/full_method_out.json \
      --c1 <artifact>/results/labelled_c1.jsonl --out mini_demo_data.json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

BANNED = {"t1": "bfs", "t2": "dijkstra"}
SUBSTITUTE = {"t1": "dfs", "t2": "bf_spfa"}
TEMPLATE_IDS = ["W1", "W2", "W3", "W4", "W5"]
PER_CELL = 10
FORCE_UNSCORED = {("t1", "W2")}  # keep one run without a k_pre state here


def allocate(counts: dict[str, int], k: int) -> dict[str, int]:
    n = sum(counts.values())
    quota = {lab: c * k / n for lab, c in counts.items()}
    alloc = {lab: max(1, int(q)) for lab, q in quota.items()}
    while sum(alloc.values()) < k:
        # largest remainder; ties -> the smaller class
        lab = max((lab for lab in counts if alloc[lab] < counts[lab]),
                  key=lambda x: (quota[x] - alloc[x], -counts[x]))
        alloc[lab] += 1
    while sum(alloc.values()) > k:
        lab = max((lab for lab in counts if alloc[lab] > 1), key=lambda x: (alloc[x] - quota[x], counts[x]))
        alloc[lab] -= 1
    return alloc


def spaced(rows: list[dict], k: int) -> list[dict]:
    if k >= len(rows):
        return list(rows)
    if k == 1:
        return [rows[len(rows) // 2]]
    idx = sorted({round(i * (len(rows) - 1) / (k - 1)) for i in range(k)})
    return [rows[i] for i in idx]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", required=True, type=Path)
    ap.add_argument("--c1", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()

    full = json.loads(a.full.read_text())
    pool = next(d for d in full["datasets"] if d["dataset"] == "fresh_ban_pool_protocol_v2")["examples"]
    code = {(r["task"], r["template"], r["seed"]): r for r in map(json.loads, a.c1.read_text().splitlines())}

    out_rows = []
    for t in ("t1", "t2"):
        for w in TEMPLATE_IDS:
            cell = sorted([e for e in pool if e["metadata_task"] == t and e["metadata_template"] == w],
                          key=lambda e: e["metadata_seed"])
            counts = Counter(e["output"] for e in cell)
            alloc = allocate(dict(counts), PER_CELL)
            picked = []
            for lab, k in alloc.items():
                rows = [e for e in cell if e["output"] == lab]
                scored = [e for e in rows if e["metadata_readout_scores_k_pre"]]
                unscored = [e for e in rows if not e["metadata_readout_scores_k_pre"]]
                if (t, w) in FORCE_UNSCORED and unscored:
                    picked += spaced(scored, k - 1) + unscored[:1]
                else:
                    picked += spaced(scored, k) + spaced(unscored, max(0, k - len(scored)))
            # order: readout classes alternate (minority first), unusable runs last
            usable = [e for e in picked if e["output"] in (BANNED[t], SUBSTITUTE[t]) and
                      e["metadata_readout_scores_k_pre"]]
            rest = [e for e in picked if e not in usable]
            by_lab = {lab: [e for e in usable if e["output"] == lab] for lab in (BANNED[t], SUBSTITUTE[t])}
            order = sorted(by_lab, key=lambda lab: len(by_lab[lab]))
            inter = []
            while any(by_lab.values()):
                for lab in order:
                    if by_lab[lab]:
                        inter.append(by_lab[lab].pop(0))
            for e in inter + rest:
                src = code[(t, w, e["metadata_seed"])]
                assert src["code_sha256"] == e["metadata_code_sha256"], (t, w, e["metadata_seed"])
                out_rows.append({**e, "metadata_code": src.get("code")})

    meta_full = full["metadata"]
    fps = meta_full["fresh_pool_summary"]["per_task"]
    rep = meta_full["readout_i_replication"]
    L1 = pool[0]["metadata_readout_layer"]
    keep_fp = ("n", "n_coded", "banned_share", "banned_share_wilson", "landing", "event_gate_pass", "pass_rate")
    hv = meta_full["headline_verification"]["checks"]
    tt = meta_full["transfer_test"]
    meta = {
        "source_artifact": "art_3iv5G76C3yoX - Reading a coding ban inside Qwen3-8B (exp_gen_sol_out)",
        "source_dataset": "fresh_ban_pool_protocol_v2 (200 runs: 2 tasks x 5 ban templates x 20 seeds, "
                          "Qwen/Qwen3-8B-FP8, T=1.0, top_p=1.0, max 1024 tokens, thinking off)",
        "selection": f"{PER_CELL} of 20 runs per task x template cell; proportional per label (largest remainder, "
                     ">= 1 per label present, ties to the minority class); evenly spaced seeds; one T1 W2 run "
                     "without a k_pre state kept; classes alternate inside a cell (minority first), runs the "
                     "readout cannot use last. metadata_code = the generated program (results/labelled_c1.jsonl).",
        "n_examples": len(out_rows),
        "readout_layer": L1,
        "readout_position": "k_pre (last token before the first algorithm-identifying lexicon match)",
        "reference_full_pool": {
            "fresh_pool_summary": {t: {w: {k: fps[t][w][k] for k in keep_fp} for w in TEMPLATE_IDS + ["pooled"]}
                                   for t in ("t1", "t2")},
            "readout_i_replication": {
                key: {"n": rep["configs"][key]["n"], "n_banned": rep["configs"][key]["n_banned"],
                      "transfer_from_exp3": rep["configs"][key]["transfer_from_exp3"]}
                for key in (f"t1|L{L1}|k_pre", f"t2|L{L1}|k_pre")},
            "class_counts": rep["class_counts"],
            "verify_headlines": {k: v for k, v in hv.items()
                                 if k.startswith("fresh_pool_banned_share") or f"L{L1}|k_pre" in k},
            "sae_transfer_test": {"rule": tt["rule"], "n_pass": tt["n_pass"],
                                  "ratio_by_layer": {L: tt["layers"][L]["ratio"] for L in tt["layers"]}},
        },
    }
    a.out.write_text(json.dumps({"metadata": meta,
                                 "datasets": [{"dataset": "fresh_ban_pool_protocol_v2", "examples": out_rows}]},
                                indent=1, ensure_ascii=False))
    cc = Counter((e["metadata_task"], e["metadata_template"], e["output"]) for e in out_rows)
    print(f"wrote {a.out} with {len(out_rows)} examples")
    for k in sorted(cc):
        print("  ", k, cc[k])


if __name__ == "__main__":
    main()
```

### [48] TOOL RESULT — Write · 2026-10-26 09:56:13 UTC

```
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/tools/build_mini_demo_data.py", "content": "#!/usr/bin/env python3\n\"\"\"Curate mini_demo_data.json from the artifact's full_method_out.json (dataset fresh_ban_pool_protocol_v2).\n\nSelection (deterministic, no randomness):\n  * 10 of the 20 runs in every task x template cell (2 tasks x 5 ban templates -> 100 runs);\n  * per cell, labels are allocated proportionally (largest remainder), every label present keeps >= 1 run,\n    ties go to the minority class (more banned-vs-substitute pairs for the within-template AUC);\n  * inside a label, runs are taken evenly spaced over the seeds, runs with a k_pre readout score first;\n    the one T1 W2 run without a k_pre state is kept on purpose (it shows the pipeline's 'no state' path);\n  * each cell is ordered so that the two readout classes alternate (minority first) and runs that the readout\n    cannot use (no score, or a third label) come last, so any per-cell prefix stays as balanced as possible;\n  * the generated program text (results/labelled_c1.jsonl, matched on task/template/seed and code_sha256) is\n    added as metadata_code, and the full 200-run pool's pipeline numbers are kept under metadata.reference_full_pool.\n\n  python3 tools/build_mini_demo_data.py --full <artifact>/full_method_out.json \\\n      --c1 <artifact>/results/labelled_c1.jsonl --out mini_demo_data.json\n\"\"\"\n\nfrom __future__ import annotations\n\nimport argparse\nimport json\nfrom collections import Counter\nfrom pathlib import Path\n\nBANNED = {\"t1\": \"bfs\", \"t2\": \"dijkstra\"}\nSUBSTITUTE = {\"t1\": \"dfs\", \"t2\": \"bf_spfa\"}\nTEMPLATE_IDS = [\"W1\", \"W2\", \"W3\", \"W4\", \"W5\"]\nPER_CELL = 10\nFORCE_UNSCORED = {(\"t1\", \"W2\")}  # keep one run without a k_pre state here\n\n\ndef allocate(counts: dict[str, int], k: int) -> dict[str, int]:\n    n = sum(counts.values())\n    quota = {lab: c * k / n for lab, c in counts.items()}\n    alloc = {lab: max(1, int(q)) for lab, q in quota.items()}\n    while sum(alloc.values()) < k:\n        # largest remainder; ties -> the smaller class\n        lab = max((lab for lab in counts if alloc[lab] < counts[lab]),\n                  key=lambda x: (quota[x] - alloc[x], -counts[x]))\n        alloc[lab] += 1\n    while sum(alloc.values()) > k:\n        lab = max((lab for lab in counts if alloc[lab] > 1), key=lambda x: (alloc[x] - quota[x], counts[x]))\n        alloc[lab] -= 1\n    return alloc\n\n\ndef spaced(rows: list[dict], k: int) -> list[dict]:\n    if k >= len(rows):\n        return list(rows)\n    if k == 1:\n        return [rows[len(rows) // 2]]\n    idx = sorted({round(i * (len(rows) - 1) / (k - 1)) for i in range(k)})\n    return [rows[i] for i in idx]\n\n\ndef main() -> None:\n    ap = argparse.ArgumentParser()\n    ap.add_argument(\"--full\", required=True, type=Path)\n    ap.add_argument(\"--c1\", required=True, type=Path)\n    ap.add_argument(\"--out\", required=True, type=Path)\n    a = ap.parse_args()\n\n    full = json.loads(a.full.read_text())\n    pool = next(d for d in full[\"datasets\"] if d[\"dataset\"] == \"fresh_ban_pool_protocol_v2\")[\"examples\"]\n    code = {(r[\"task\"], r[\"template\"], r[\"seed\"]): r for r in map(json.loads, a.c1.read_text().splitlines())}\n\n    out_rows = []\n    for t in (\"t1\", \"t2\"):\n        for w in TEMPLATE_IDS:\n            cell = sorted([e for e in pool if e[\"metadata_task\"] == t and e[\"metadata_template\"] == w],\n                          key=lambda e: e[\"metadata_seed\"])\n            counts = Counter(e[\"output\"] for e in cell)\n            alloc = allocate(dict(counts), PER_CELL)\n            picked = []\n            for lab, k in alloc.items():\n                rows = [e for e in cell if e[\"output\"] == lab]\n                scored = [e for e in rows if e[\"metadata_readout_scores_k_pre\"]]\n                unscored = [e for e in rows if not e[\"metadata_readout_scores_k_pre\"]]\n                if (t, w) in FORCE_UNSCORED and unscored:\n                    picked += spaced(scored, k - 1) + unscored[:1]\n                else:\n                    picked += spaced(scored, k) + spaced(unscored, max(0, k - len(scored)))\n            # order: readout classes alternate (minority first), unusable runs last\n            usable = [e for e in picked if e[\"output\"] in (BANNED[t], SUBSTITUTE[t]) and\n                      e[\"metadata_readout_scores_k_pre\"]]\n            rest = [e for e in picked if e not in usable]\n            by_lab = {lab: [e for e in usable if e[\"output\"] == lab] for lab in (BANNED[t], SUBSTITUTE[t])}\n            order = sorted(by_lab, key=lambda lab: len(by_lab[lab]))\n            inter = []\n            while any(by_lab.values()):\n                for lab in order:\n                    if by_lab[lab]:\n                        inter.append(by_lab[lab].pop(0))\n            for e in inter + rest:\n                src = code[(t, w, e[\"metadata_seed\"])]\n                assert src[\"code_sha256\"] == e[\"metadata_code_sha256\"], (t, w, e[\"metadata_seed\"])\n                out_rows.append({**e, \"metadata_code\": src.get(\"code\")})\n\n    meta_full = full[\"metadata\"]\n    fps = meta_full[\"fresh_pool_summary\"][\"per_task\"]\n    rep = meta_full[\"readout_i_replication\"]\n    L1 = pool[0][\"metadata_readout_layer\"]\n    keep_fp = (\"n\", \"n_coded\", \"banned_share\", \"banned_share_wilson\", \"landing\", \"event_gate_pass\", \"pass_rate\")\n    hv = meta_full[\"headline_verification\"][\"checks\"]\n    tt = meta_full[\"transfer_test\"]\n    meta = {\n        \"source_artifact\": \"art_3iv5G76C3yoX - Reading a coding ban inside Qwen3-8B (exp_gen_sol_out)\",\n        \"source_dataset\": \"fresh_ban_pool_protocol_v2 (200 runs: 2 tasks x 5 ban templates x 20 seeds, \"\n                          \"Qwen/Qwen3-8B-FP8, T=1.0, top_p=1.0, max 1024 tokens, thinking off)\",\n        \"selection\": f\"{PER_CELL} of 20 runs per task x template cell; proportional per label (largest remainder, \"\n                     \">= 1 per label present, ties to the minority class); evenly spaced seeds; one T1 W2 run \"\n                     \"without a k_pre state kept; classes alternate inside a cell (minority first), runs the \"\n                     \"readout cannot use last. metadata_code = the generated program (results/labelled_c1.jsonl).\",\n        \"n_examples\": len(out_rows),\n        \"readout_layer\": L1,\n        \"readout_position\": \"k_pre (last token before the first algorithm-identifying lexicon match)\",\n        \"reference_full_pool\": {\n            \"fresh_pool_summary\": {t: {w: {k: fps[t][w][k] for k in keep_fp} for w in TEMPLATE_IDS + [\"pooled\"]}\n                                   for t in (\"t1\", \"t2\")},\n            \"readout_i_replication\": {\n                key: {\"n\": rep[\"configs\"][key][\"n\"], \"n_banned\": rep[\"configs\"][key][\"n_banned\"],\n                      \"transfer_from_exp3\": rep[\"configs\"][key][\"transfer_from_exp3\"]}\n                for key in (f\"t1|L{L1}|k_pre\", f\"t2|L{L1}|k_pre\")},\n            \"class_counts\": rep[\"class_counts\"],\n            \"verify_headlines\": {k: v for k, v in hv.items()\n                                 if k.startswith(\"fresh_pool_banned_share\") or f\"L{L1}|k_pre\" in k},\n            \"sae_transfer_test\": {\"rule\": tt[\"rule\"], \"n_pass\": tt[\"n_pass\"],\n                                  \"ratio_by_layer\": {L: tt[\"layers\"][L][\"ratio\"] for L in tt[\"layers\"]}},\n        },\n    }\n    a.out.write_text(json.dumps({\"metadata\": meta,\n                                 \"datasets\": [{\"dataset\": \"fresh_ban_pool_protocol_v2\", \"examples\": out_rows}]},\n                                indent=1, ensure_ascii=False))\n    cc = Counter((e[\"metadata_task\"], e[\"metadata_template\"], e[\"output\"]) for e in out_rows)\n    print(f\"wrote {a.out} with {len(out_rows)} examples\")\n    for k in sorted(cc):\n        print(\"  \", k, cc[k])\n\n\nif __name__ == \"__main__\":\n    main()\n", "structuredPatch": [], "originalFile": null, "userModified": false}
```

### [49] TOOL CALL — Bash · 2026-10-26 09:56:21 UTC

```
Build mini demo data and verify its composition:
ART=/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_12 && python3 tools/build_mini_demo_data.py --full $ART/full_method_out.json --c1 $ART/results/labelled_c1.jsonl --out mini_demo_data.json && ls -la mini_demo_data.json && python3 - <<'EOF'
import json
d = json.load(open("mini_demo_data.json"))
ex = d["datasets"][0]["examples"]
print("n", len(ex), "keys", list(ex[0].keys()))
# cell order check
from itertools import groupby
for (t, w), g in groupby(ex, key=lambda e: (e["metadata_task"], e["metadata_template"])):
    g = list(g)
    print(t, w, [e["output"][:3] + ("" if e["metadata_readout_scores_k_pre"] else "*") for e in g])
print(json.dumps(d["metadata"]["reference_full_pool"]["sae_transfer_test"]))
print("max code len", max(len(e["metadata_code"] or "") for e in ex), "none code", sum(e["metadata_code"] is None for e in ex))
EOF
```

### [50] TOOL RESULT — Bash · 2026-10-26 09:56:21 UTC

```
{"stdout": "wrote mini_demo_data.json with 100 examples\n   ('t1', 'W1', 'dfs') 10\n   ('t1', 'W2', 'dfs') 10\n   ('t1', 'W3', 'dfs') 10\n   ('t1', 'W4', 'bfs') 7\n   ('t1', 'W4', 'dfs') 3\n   ('t1', 'W5', 'dfs') 10\n   ('t2', 'W1', 'bf_spfa') 9\n   ('t2', 'W1', 'dijkstra') 1\n   ('t2', 'W2', 'bf_spfa') 10\n   ('t2', 'W3', 'bf_spfa') 7\n   ('t2', 'W3', 'dijkstra') 2\n   ('t2', 'W3', 'other') 1\n   ('t2', 'W4', 'bf_spfa') 7\n   ('t2', 'W4', 'dijkstra') 3\n   ('t2', 'W5', 'bf_spfa') 9\n   ('t2', 'W5', 'dijkstra') 1\n-rw-rw-rw- 1 aii-agent aii-agent 312672 Oct 26 09:56 mini_demo_data.json\nn 100 keys ['input', 'output', 'metadata_task', 'metadata_template', 'metadata_seed', 'metadata_model', 'metadata_decoding', 'metadata_passed', 'metadata_labeller_source', 'metadata_commit_idx', 'metadata_evidence_term', 'metadata_negated_first_mention', 'metadata_code_sha256', 'metadata_n_gen_tokens', 'metadata_readout_layer', 'metadata_readout_scores_k_pre', 'predict_sae_top20_latents_exp3_fitted', 'predict_sae_top1_latent_exp3_fitted', 'predict_dim_baseline_exp3_fitted', 'predict_raw_logistic_baseline_exp3_fitted', 'predict_top20_neurons_baseline_exp3_fitted', 'predict_banned_label', 'metadata_code']\nt1 W1 ['dfs', 'dfs', 'dfs', 'dfs', 'dfs', 'dfs', 'dfs', 'dfs', 'dfs', 'dfs']\nt1 W2 ['dfs', 'dfs', 'dfs', 'dfs', 'dfs', 'dfs', 'dfs', 'dfs', 'dfs', 'dfs*']\nt1 W3 ['dfs', 'dfs', 'dfs', 'dfs', 'dfs', 'dfs', 'dfs', 'dfs', 'dfs', 'dfs']\nt1 W4 ['dfs', 'bfs', 'dfs', 'bfs', 'dfs', 'bfs', 'bfs', 'bfs', 'bfs', 'bfs']\nt1 W5 ['dfs', 'dfs', 'dfs', 'dfs', 'dfs', 'dfs', 'dfs', 'dfs', 'dfs', 'dfs']\nt2 W1 ['dij', 'bf_', 'bf_', 'bf_', 'bf_', 'bf_', 'bf_', 'bf_', 'bf_', 'bf_']\nt2 W2 ['bf_', 'bf_', 'bf_', 'bf_', 'bf_', 'bf_', 'bf_', 'bf_', 'bf_', 'bf_']\nt2 W3 ['dij', 'bf_', 'dij', 'bf_', 'bf_', 'bf_', 'bf_', 'bf_', 'bf_', 'oth*']\nt2 W4 ['dij', 'bf_', 'dij', 'bf_', 'dij', 'bf_', 'bf_', 'bf_', 'bf_', 'bf_']\nt2 W5 ['dij', 'bf_', 'bf_', 'bf_', 'bf_', 'bf_', 'bf_', 'bf_', 'bf_', 'bf_']\n{\"rule\": \"PASS(L) := dCE_inst(L) <= 1.5 x dCE_base(L) (spliced-in CE over response tokens)\", \"n_pass\": 0, \"ratio_by_layer\": {\"15\": 3.293978511257419, \"20\": 1.9457419882505633, \"27\": 1.5865409073202312}}\nmax code len 1726 none code 0", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [51] THINKING · 2026-10-26 09:58:21 UTC

```
mini_demo_data.json is ready (100 runs, 313 KB) with all labels, program text, and reference numbers preserved. Now checking how the original run_stage_analyse wires the readout call so the notebook mirrors it.
```

### [52] TOOL CALL — Bash · 2026-10-26 09:58:21 UTC

```
Read analyse stage runner and k_pre definition:
cd /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_12/src && sed -n 570,598p analysis.py; grep -n "k_pre\|commit" readout_i.py | head -20
```

### [53] TOOL RESULT — Bash · 2026-10-26 09:58:21 UTC

```
{"stdout": "    agree = [a == b for _, a, b in pairs if a not in (None, \"undecided\")]\n    out[\"validity\"] = {\"pairs\": pairs, \"n_decided\": len(agree), \"agreement\": float(np.mean(agree)) if agree else None,\n                       \"F7_stated_plan_wording\": bool(agree and np.mean(agree) < 0.8)}\n    write_json(RESULTS / \"thought_anchors.json\", out)\n    return out\n\n\ndef run_stage_analyse() -> None:\n    parts = {}\n    for name, fn in ((\"transfer_summary\", transfer_summary), (\"readout_i_replication\", readout_i_replication),\n                     (\"readout_ii_attention\", readout_ii_attention)):\n        with Timer(f\"analyse_{name}\", gpu=False):\n            try:\n                parts[name] = fn()\n            except Exception as e:  # noqa: BLE001 - each readout is reported independently\n                logger.exception(f\"{name} failed: {e!r}\")\n                parts[name] = {\"status\": f\"failed: {e!r}\"[:300]}\n    for name, fn in ((\"readout_iii_prime_veto\", lambda: readout_iii_prime_veto(parts.get(\"readout_ii_attention\"))),\n                     (\"latent_contexts\", latent_contexts), (\"jlens_summary\", jlens_summary),\n                     (\"thought_anchors\", thought_anchors)):\n        with Timer(f\"analyse_{name}\", gpu=False):\n            try:\n                parts[name] = fn()\n            except Exception as e:  # noqa: BLE001\n                logger.exception(f\"{name} failed: {e!r}\")\n                parts[name] = {\"status\": f\"failed: {e!r}\"[:300]}\n    write_json(RESULTS / \"analysis_status.json\", {k: (\"ok\" if not (isinstance(v, dict) and str(v.get(\"status\", \"\"))\n                                                                    .startswith(\"failed\")) else v[\"status\"])\n                                                  for k, v in parts.items()})\n31:POS_NAMES = [\"R\", \"k8\", \"k16\", \"k32\", \"k64\", \"k_fork\", \"k_pre\", \"k_post\"]\n32:PROBE_POS = [\"k_pre\", \"k_fork\", \"k16\", \"R\", \"k_post\"]\n33:MAIN_POS = [\"k_pre\", \"k_fork\", \"k16\"]\n360:    \"\"\"commit_idx per class, prefix identity with other-class rows of the same paraphrase, token at commit_idx.\"\"\"\n374:        c = p[\"commit_idx\"]\n376:        recs.append({\"pid\": r[\"paraphrase_id\"], \"label\": str(lab), \"commit_idx\": c,\n378:                     \"commit_token\": tok.decode([gids[c]]) if c is not None and c < len(gids) else None})\n381:        cs = [x[\"commit_idx\"] for x in recs if x[\"label\"] == lab and x[\"commit_idx\"] is not None]\n384:            if x[\"label\"] == lab and x[\"commit_token\"] is not None:\n385:                toks[x[\"commit_token\"]] = toks.get(x[\"commit_token\"], 0) + 1\n393:        out[lab] = {\"n\": n, \"commit_idx_median\": float(np.median(cs)) if cs else None,\n394:                    \"commit_idx_q10_q90\": [float(np.quantile(cs, 0.1)), float(np.quantile(cs, 0.9))] if cs else None,\n396:                    \"commit_token_counts\": dict(sorted(toks.items(), key=lambda kv: -kv[1])[:10])}\n406:            for pos, wgt in ((\"k_pre\", 2.0), (\"k_fork\", 1.0), (\"k16\", 1.0)):\n417:    return {\"score\": score, \"rule\": \"score(L)=weighted mean over tasks of within-paraphrase DiM AUC at k_pre (x2), \"", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [54] ASSISTANT · 2026-10-26 09:58:29 UTC

```
Let me load the `NotebookEdit` tool schema, since the TODO asks for the notebook to be built with it.
```

### [55] TOOL CALL — ToolSearch · 2026-10-26 09:58:29 UTC

```
{'query': 'select:NotebookEdit', 'max_results': 1}
```

### [56] TOOL RESULT — ToolSearch · 2026-10-26 09:58:29 UTC

```
{"matches": ["NotebookEdit"], "query": "select:NotebookEdit", "total_deferred_tools": 24}
```

### [57] THINKING · 2026-10-26 10:03:23 UTC

```
I'll build the notebook via a temporary JSON-safe builder script, then remove it and make all further edits—including scaling up the config from its minimal starting values—using NotebookEdit.
```

### [58] TOOL CALL — Write · 2026-10-26 10:03:23 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [59] TOOL RESULT — Write · 2026-10-26 10:03:23 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [60] ASSISTANT · 2026-10-26 10:03:35 UTC

```
Now generate the notebook, then delete the one-off builder so the notebook is the single source of truth.
```

### [61] TOOL CALL — Bash · 2026-10-26 10:03:35 UTC

```
Build notebook, remove builder, sanity-check structure:
python3 tools/_build_notebook.py && rm tools/_build_notebook.py && python3 -c "
import json; nb=json.load(open('code_demo.ipynb')); print(len(nb['cells']), 'cells'); print([c['cell_type'][0] for c in nb['cells']])
src=''.join(nb['cells'][4]['source']); print('URL ok:', 'GITHUB_DATA_URL = \"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-2/experiment-12/demo/mini_demo_data.json\"' in src)
" && ls tools/
```

### [62] TOOL RESULT — Bash · 2026-10-26 10:03:35 UTC

```
{"stdout": "wrote /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/code_demo.ipynb with 28 cells\n28 cells\n['m', 'c', 'c', 'c', 'c', 'm', 'c', 'm', 'c', 'm', 'c', 'm', 'c', 'm', 'c', 'm', 'c', 'm', 'c', 'm', 'c', 'm', 'c', 'm', 'c', 'm', 'c', 'm']\nURL ok: False\nbuild_mini_demo_data.py", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [63] ASSISTANT · 2026-10-26 10:03:43 UTC

```
The URL check looked at the wrong cell index (the loader is cell 3). Re-checking across all cells:
```

### [64] TOOL CALL — Bash · 2026-10-26 10:03:43 UTC

```
Verify URL presence and code cell syntax:
python3 -c "
import json; nb=json.load(open('code_demo.ipynb'))
want='GITHUB_DATA_URL = \"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-2/experiment-12/demo/mini_demo_data.json\"'
print([i for i,c in enumerate(nb['cells']) if want in ''.join(c['source'])])
import ast
for i,c in enumerate(nb['cells']):
    if c['cell_type']=='code':
        try: ast.parse(''.join(c['source']))
        except SyntaxError as e: print('SYNTAX', i, e)
print('parsed all code cells')
"
```

### [65] TOOL RESULT — Bash · 2026-10-26 10:03:43 UTC

```
{"stdout": "[3]\nparsed all code cells", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [66] ASSISTANT · 2026-10-26 10:03:57 UTC

```
Notebook is valid (28 cells, URL in the loader cell, all code parses). Launching test run 1 at the minimum config (`N_PER_CELL=2, N_BOOT=1, N_PLACEBO=1`) in the clean test venv, in the background:
```

### [67] TOOL CALL — Bash · 2026-10-26 10:03:57 UTC

```
Test-run notebook at minimum config in clean venv:
T0=$(date +%s) && UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_3iv5G76C3yoX-2eaf8ea929eb && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_3iv5G76C3yoX-2eaf8ea929eb/bin/python jupyter ipykernel && T1=$(date +%s) && echo "venv setup: $((T1-T0)) s" && /tmp/aii_nb_test_envs/art_3iv5G76C3yoX-2eaf8ea929eb/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb; RC=$?; T2=$(date +%s); echo "nbconvert exit=$RC, notebook runtime: $((T2-T1)) s"
```

### [68] TOOL RESULT — Bash · 2026-10-26 10:03:57 UTC

```
{"stdout": "", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false, "backgroundTaskId": "bdzeg2l3p"}
```

### [69] THINKING · 2026-10-26 10:04:11 UTC

```
While test run 1 runs, I'll write the manifest—since nothing here is a large binary or cache, it won't need any entries.
```

### [70] TOOL CALL — Write · 2026-10-26 10:04:11 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/.aii/manifest.yaml

# Heavy-path decisions for this workspace (demo notebook of art_3iv5G76C3yoX).
# Nothing here is a large binary or a cache directory: the notebook, mini_demo_data.json (~0.3 MB), the curation
# script, the notebook's small JSON results, its log and one PNG figure are all text/code or far below the 10 MB
# auto-keep floor. The notebook test venv lives on local disk outside this workspace and is removed by the pipeline,
# so there is nothing to keep or delete.
entries: []
```

### [71] TOOL RESULT — Write · 2026-10-26 10:04:11 UTC

```
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/.aii/manifest.yaml", "content": "# Heavy-path decisions for this workspace (demo notebook of art_3iv5G76C3yoX).\n# Nothing here is a large binary or a cache directory: the notebook, mini_demo_data.json (~0.3 MB), the curation\n# script, the notebook's small JSON results, its log and one PNG figure are all text/code or far below the 10 MB\n# auto-keep floor. The notebook test venv lives on local disk outside this workspace and is removed by the pipeline,\n# so there is nothing to keep or delete.\nentries: []\n", "structuredPatch": [], "originalFile": null, "userModified": false}
```

### [72] THINKING · 2026-10-26 10:04:59 UTC

```
Found a latent bug: negative `yerr` values can occur from tiny floating-point Wilson bounds or bootstrap CIs not containing the point estimate, which matplotlib ≥3.x rejects. I'll clamp both error-bar terms at 0 once the running test finishes, and in the meantime here's the README draft.
```

### [73] TOOL CALL — Write · 2026-10-26 10:04:59 UTC

````
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/README.md

# Demo: reading a coding ban inside Qwen3-8B

A runnable, CPU-only demo notebook for the experiment artifact **"Reading a coding ban inside Qwen3-8B"**
(`art_3iv5G76C3yoX`). The artifact asks what Qwen3-8B writes when a coding prompt bans its default algorithm:
- T1 grid path: BFS is banned;
- T2 weighted shortest path: Dijkstra is banned.

It also asks whether simple readouts of the model's residual stream can tell banned runs from substitute runs. Its
full pipeline needs a 16 GB GPU, vLLM and about one GPU-hour. This demo runs the CPU analysis stages of that pipeline
on stored per-run data. It finishes in seconds once the packages are installed.

## What the notebook does

`code_demo.ipynb` keeps the artifact's own code, copied from `method.py` and `src/`. It splits that code into cells
with explanations between them, and it changes only the input lines, so the functions read the demo data instead of
the pipeline's files. It runs:

1. `src/core.py` – the protocol constants (models, label maps, the five frozen ban templates W1–W5, seeds) and the
   IO, Wilson-interval and timing helpers.
2. `src/final.py::fresh_pool_summary` – for each task and template, how often the model still writes the banned
   algorithm, with Wilson 95% CIs, the event gate, the pass rate and where the runs landed.
3. `src/readout_i.py::auc / within_u / within_auc` and `src/analysis.py::_boot_runs` – pooled and within-template
   AUCs, with a bootstrap over runs.
4. `src/analysis.py::readout_i_replication` (scoring half) – the readout objects fitted on exp3 states were applied
   to each run's layer-27 residual state at `k_pre`; the stored scores are evaluated here. The readouts are:
   - the SAE top-1 latent;
   - the SAE top-20-latent logistic probe;
   - DiM on the SAE code;
   - the baselines: DiM on the raw residual, a raw logistic probe, and the top-1 / top-20 raw dimensions.
5. `src/verify_headlines.py` checks 1 and 5 – an independent pandas / scikit-learn re-derivation of the banned share
   and of the DiM AUC, plus a shuffled-label placebo.
6. A summary figure and table. The figure shows the banned share per template, the readout AUCs, and the per-run
   readout geometry (each run's state projected onto the DiM and SAE-probe directions). Every number is shown next
   to the artifact's full 200-run value.

These parts do not run here, because they need the 8B model, the SAE, or data outside this demo's one dataset:
- generation (vLLM);
- the labeller;
- the Hugging Face state, attention and transfer-test passes;
- the exp3 discovery;
- the nested selection inside the fresh pool;
- the same-seed CRN, thought-anchor and J-lens analyses.

The notebook marks each spot in the code with a `# notebook:` comment.

## Layout

| Path | What it is |
|---|---|
| `code_demo.ipynb` | The demo notebook (Colab-ready; loads `mini_demo_data.json` from GitHub, falls back to the local copy) |
| `mini_demo_data.json` | 100 of the 200 runs of the artifact's `fresh_ban_pool_protocol_v2` dataset, plus the full-pool reference numbers |
| `tools/build_mini_demo_data.py` | The deterministic curation script that produced `mini_demo_data.json` from the artifact's `full_method_out.json` and `results/labelled_c1.jsonl` |
| `results/` | Written by the notebook: `fresh_pool_summary.json`, `readout_i_replication.json`, `verify_headlines.json`, `timing.json` |
| `figures/demo_summary.png` | Written by the notebook: the summary figure |
| `logs/stage_demo.log` | Written by the notebook: the loguru debug log |
| `.aii/manifest.yaml` | Storage decisions (none needed: no large binaries or caches) |

## The demo data

`mini_demo_data.json` follows the artifact's `exp_gen_sol_out` layout: `{"metadata": ..., "datasets": [...]}`. It
holds one dataset, `fresh_ban_pool_protocol_v2`. That dataset has 10 of the 20 runs in each task × template cell.

Each example carries the following fields:
- `input`: the prompt;
- `output`: the canonical label of the generated program (`bfs`, `dfs`, `dijkstra`, `bf_spfa`, `other`);
- `metadata_*`: seed, template, hidden-test pass, commit token and index, and the per-run readout scores at
  L27 `k_pre`;
- `metadata_code`: the generated program itself, joined from the artifact's `results/labelled_c1.jsonl` and checked
  against `metadata_code_sha256`.

The selection is deterministic:
- Labels are allocated proportionally within each cell, and every label present in a cell keeps at least one run.
  So T1 W4 keeps 7 BFS + 3 DFS, and T2 keeps all four templates that produced Dijkstra.
- Seeds are evenly spaced. One T1 run without a `k_pre` state is kept on purpose.
- Classes alternate inside each cell, so the config value `N_PER_CELL` (runs per cell) can be lowered and both
  classes stay present.

`metadata.reference_full_pool` holds the artifact's own numbers for all 200 runs: the fresh-pool summary, the
replication AUCs, the class counts, the matching `verify_headlines` checks, and the SAE transfer-test ratios.

To rebuild the file from the artifact folder:

```bash
python3 tools/build_mini_demo_data.py --full <artifact>/full_method_out.json \
    --c1 <artifact>/results/labelled_c1.jsonl --out mini_demo_data.json
```

## How to run

**Colab:** open `code_demo.ipynb` and run all cells. The install cell installs only `loguru`, and uses Colab's
pre-installed numpy, pandas, scipy, scikit-learn and matplotlib.

**Locally** (Python 3.12). The install cell pins Colab's package versions outside Colab:

```bash
uv venv --seed --python 3.12 .venv-nb
uv pip install --python .venv-nb/bin/python jupyter ipykernel
.venv-nb/bin/jupyter nbconvert --to notebook --execute code_demo.ipynb --output code_demo.ipynb
```

Configuration (one cell near the top):

| Name | Value | Meaning |
|---|---|---|
| `N_PER_CELL` | 10 | runs per task × template; the whole demo file |
| `N_BOOT` | 2000 | the original bootstrap count |
| `N_PLACEBO` | 200 | the original placebo count |

Everything fits well inside a 10-minute budget. To use all 200 runs, every layer and position, and the GPU stages,
run the original artifact's pipeline: `uv run method.py --stage ...`, as described in its `README.md` and
`reproducibility.md`.

## Restoring removed files

Nothing is marked for deletion in `.aii/manifest.yaml`, so nothing needs restoring. Every file in this folder is
small text, JSON or PNG. The notebook's outputs (`results/`, `figures/`, `logs/`) are regenerated by running
`code_demo.ipynb`. `mini_demo_data.json` is regenerated by the command in "The demo data" above.

The full pipeline is not part of this demo. Its models and SAE live in the Hugging Face cache and can be downloaded
again with:

```bash
huggingface-cli download Qwen/Qwen3-8B
huggingface-cli download Qwen/Qwen3-8B-FP8
huggingface-cli download Qwen/Qwen3-8B-Base
huggingface-cli download Qwen/SAE-Res-Qwen3-8B-Base-W64K-L0_50 layer15.sae.pt layer20.sae.pt layer27.sae.pt config.json README.md
```
````

### [74] TOOL RESULT — Write · 2026-10-26 10:04:59 UTC

````
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/README.md", "content": "# Demo: reading a coding ban inside Qwen3-8B\n\nA runnable, CPU-only demo notebook for the experiment artifact **\"Reading a coding ban inside Qwen3-8B\"**\n(`art_3iv5G76C3yoX`). The artifact asks what Qwen3-8B writes when a coding prompt bans its default algorithm:\n- T1 grid path: BFS is banned;\n- T2 weighted shortest path: Dijkstra is banned.\n\nIt also asks whether simple readouts of the model's residual stream can tell banned runs from substitute runs. Its\nfull pipeline needs a 16 GB GPU, vLLM and about one GPU-hour. This demo runs the CPU analysis stages of that pipeline\non stored per-run data. It finishes in seconds once the packages are installed.\n\n## What the notebook does\n\n`code_demo.ipynb` keeps the artifact's own code, copied from `method.py` and `src/`. It splits that code into cells\nwith explanations between them, and it changes only the input lines, so the functions read the demo data instead of\nthe pipeline's files. It runs:\n\n1. `src/core.py` – the protocol constants (models, label maps, the five frozen ban templates W1–W5, seeds) and the\n   IO, Wilson-interval and timing helpers.\n2. `src/final.py::fresh_pool_summary` – for each task and template, how often the model still writes the banned\n   algorithm, with Wilson 95% CIs, the event gate, the pass rate and where the runs landed.\n3. `src/readout_i.py::auc / within_u / within_auc` and `src/analysis.py::_boot_runs` – pooled and within-template\n   AUCs, with a bootstrap over runs.\n4. `src/analysis.py::readout_i_replication` (scoring half) – the readout objects fitted on exp3 states were applied\n   to each run's layer-27 residual state at `k_pre`; the stored scores are evaluated here. The readouts are:\n   - the SAE top-1 latent;\n   - the SAE top-20-latent logistic probe;\n   - DiM on the SAE code;\n   - the baselines: DiM on the raw residual, a raw logistic probe, and the top-1 / top-20 raw dimensions.\n5. `src/verify_headlines.py` checks 1 and 5 – an independent pandas / scikit-learn re-derivation of the banned share\n   and of the DiM AUC, plus a shuffled-label placebo.\n6. A summary figure and table. The figure shows the banned share per template, the readout AUCs, and the per-run\n   readout geometry (each run's state projected onto the DiM and SAE-probe directions). Every number is shown next\n   to the artifact's full 200-run value.\n\nThese parts do not run here, because they need the 8B model, the SAE, or data outside this demo's one dataset:\n- generation (vLLM);\n- the labeller;\n- the Hugging Face state, attention and transfer-test passes;\n- the exp3 discovery;\n- the nested selection inside the fresh pool;\n- the same-seed CRN, thought-anchor and J-lens analyses.\n\nThe notebook marks each spot in the code with a `# notebook:` comment.\n\n## Layout\n\n| Path | What it is |\n|---|---|\n| `code_demo.ipynb` | The demo notebook (Colab-ready; loads `mini_demo_data.json` from GitHub, falls back to the local copy) |\n| `mini_demo_data.json` | 100 of the 200 runs of the artifact's `fresh_ban_pool_protocol_v2` dataset, plus the full-pool reference numbers |\n| `tools/build_mini_demo_data.py` | The deterministic curation script that produced `mini_demo_data.json` from the artifact's `full_method_out.json` and `results/labelled_c1.jsonl` |\n| `results/` | Written by the notebook: `fresh_pool_summary.json`, `readout_i_replication.json`, `verify_headlines.json`, `timing.json` |\n| `figures/demo_summary.png` | Written by the notebook: the summary figure |\n| `logs/stage_demo.log` | Written by the notebook: the loguru debug log |\n| `.aii/manifest.yaml` | Storage decisions (none needed: no large binaries or caches) |\n\n## The demo data\n\n`mini_demo_data.json` follows the artifact's `exp_gen_sol_out` layout: `{\"metadata\": ..., \"datasets\": [...]}`. It\nholds one dataset, `fresh_ban_pool_protocol_v2`. That dataset has 10 of the 20 runs in each task × template cell.\n\nEach example carries the following fields:\n- `input`: the prompt;\n- `output`: the canonical label of the generated program (`bfs`, `dfs`, `dijkstra`, `bf_spfa`, `other`);\n- `metadata_*`: seed, template, hidden-test pass, commit token and index, and the per-run readout scores at\n  L27 `k_pre`;\n- `metadata_code`: the generated program itself, joined from the artifact's `results/labelled_c1.jsonl` and checked\n  against `metadata_code_sha256`.\n\nThe selection is deterministic:\n- Labels are allocated proportionally within each cell, and every label present in a cell keeps at least one run.\n  So T1 W4 keeps 7 BFS + 3 DFS, and T2 keeps all four templates that produced Dijkstra.\n- Seeds are evenly spaced. One T1 run without a `k_pre` state is kept on purpose.\n- Classes alternate inside each cell, so the config value `N_PER_CELL` (runs per cell) can be lowered and both\n  classes stay present.\n\n`metadata.reference_full_pool` holds the artifact's own numbers for all 200 runs: the fresh-pool summary, the\nreplication AUCs, the class counts, the matching `verify_headlines` checks, and the SAE transfer-test ratios.\n\nTo rebuild the file from the artifact folder:\n\n```bash\npython3 tools/build_mini_demo_data.py --full <artifact>/full_method_out.json \\\n    --c1 <artifact>/results/labelled_c1.jsonl --out mini_demo_data.json\n```\n\n## How to run\n\n**Colab:** open `code_demo.ipynb` and run all cells. The install cell installs only `loguru`, and uses Colab's\npre-installed numpy, pandas, scipy, scikit-learn and matplotlib.\n\n**Locally** (Python 3.12). The install cell pins Colab's package versions outside Colab:\n\n```bash\nuv venv --seed --python 3.12 .venv-nb\nuv pip install --python .venv-nb/bin/python jupyter ipykernel\n.venv-nb/bin/jupyter nbconvert --to notebook --execute code_demo.ipynb --output code_demo.ipynb\n```\n\nConfiguration (one cell near the top):\n\n| Name | Value | Meaning |\n|---|---|---|\n| `N_PER_CELL` | 10 | runs per task × template; the whole demo file |\n| `N_BOOT` | 2000 | the original bootstrap count |\n| `N_PLACEBO` | 200 | the original placebo count |\n\nEverything fits well inside a 10-minute budget. To use all 200 runs, every layer and position, and the GPU stages,\nrun the original artifact's pipeline: `uv run method.py --stage ...`, as described in its `README.md` and\n`reproducibility.md`.\n\n## Restoring removed files\n\nNothing is marked for deletion in `.aii/manifest.yaml`, so nothing needs restoring. Every file in this folder is\nsmall text, JSON or PNG. The notebook's outputs (`results/`, `figures/`, `logs/`) are regenerated by running\n`code_demo.ipynb`. `mini_demo_data.json` is regenerated by the command in \"The demo data\" above.\n\nThe full pipeline is not part of this demo. Its models and SAE live in the Hugging Face cache and can be downloaded\nagain with:\n\n```bash\nhuggingface-cli download Qwen/Qwen3-8B\nhuggingface-cli download Qwen/Qwen3-8B-FP8\nhuggingface-cli download Qwen/Qwen3-8B-Base\nhuggingface-cli download Qwen/SAE-Res-Qwen3-8B-Base-W64K-L0_50 layer15.sae.pt layer20.sae.pt layer27.sae.pt config.json README.md\n```\n", "structuredPatch": [], "originalFile": null, "userModified": false}
````

### [75] TOOL CALL — Bash · 2026-10-26 10:05:03 UTC

```
Read test run 1 output:
cat /tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-2-art-3iv5G76C3yoX/036732a9-f32f-4b51-a450-1026af3e7c10/tasks/bdzeg2l3p.output | tail -20
```

### [76] TOOL RESULT — Bash · 2026-10-26 10:05:03 UTC

```
{"stdout": "venv setup: 3 s\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[IPKernelApp] WARNING | Kernel is running over TCP without encryption. All communication (including code and outputs) is sent in plain text and is susceptible to eavesdropping. Use IPC transport or launch with kernel manager-provisioned CurveZMQ keys to enable transport encryption.\n[NbConvertApp] Writing 231412 bytes to code_demo.ipynb\nnbconvert exit=0, notebook runtime: 17 s\n\n[exited with code 0]", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [77] ASSISTANT · 2026-10-26 10:05:11 UTC

```
Test run 1 passed (exit 0, 17 s including installs). Let me inspect every cell's outputs for errors, warnings and sanity of values:
```

### [78] TOOL CALL — Bash · 2026-10-26 10:05:11 UTC

```
Dump executed notebook outputs per cell:
python3 - <<'EOF'
import json
nb = json.load(open("code_demo.ipynb"))
for i, c in enumerate(nb["cells"]):
    if c["cell_type"] != "code":
        continue
    print(f"===== cell {i} (exec {c.get('execution_count')}) id={c['id']}")
    for o in c["outputs"]:
        if o["output_type"] == "stream":
            txt = "".join(o["text"])
            print(f"[{o['name']}]", txt[:2500] + ("...<trunc>" if len(txt) > 2500 else ""))
        elif o["output_type"] in ("execute_result", "display_data"):
            d = o["data"]
            if "text/plain" in d:
                t = "".join(d["text/plain"]); print("[result/plain]", t[:2500])
            if "image/png" in d:
                print("[image/png]", len(d["image/png"]), "b64 chars")
        elif o["output_type"] == "error":
            print("[ERROR]", o["ename"], o["evalue"])
EOF
```

### [79] TOOL RESULT — Bash · 2026-10-26 10:05:11 UTC

````
{"stdout": "===== cell 1 (exec 1) id=cell-01\n===== cell 2 (exec 2) id=cell-02\n===== cell 3 (exec 3) id=cell-03\n===== cell 4 (exec 4) id=cell-04\n[stdout] GitHub data unavailable, using local mini_demo_data.json: HTTP Error 404: Not Found\nfresh_ban_pool_protocol_v2: 100 runs in the demo file\nselection: 10 of 20 runs per task x template cell; proportional per label (largest remainder, >= 1 per label present, ties to the minority class); evenly spaced seeds; one T1 W2 run without a k_pre state kept; classes alternate inside a cell (minority first), runs the readout cannot use last. metadata_code = the generated program (results/labelled_c1.jsonl).\n\n===== cell 6 (exec 5) id=cell-06\n===== cell 8 (exec 6) id=cell-08\n===== cell 10 (exec 7) id=cell-10\n[stdout] 20 runs | readout layer L27 | runs with a k_pre score: 20\nlabel          bf_spfa  bfs  dfs  dijkstra\ntask template                             \nt1   W1              0    0    2         0\n     W2              0    0    2         0\n     W3              0    0    2         0\n     W4              0    1    1         0\n     W5              0    0    2         0\nt2   W1              1    0    0         1\n     W2              2    0    0         0\n     W3              1    0    0         1\n     W4              1    0    0         1\n     W5              1    0    0         1\n\n===== cell 12 (exec 8) id=cell-12\n[stdout] == t1: banned X = 'bfs', substitute X' = 'dfs'\n  W1  Do not use breadth-first search (BFS) for this task.       {'dfs': 2}\n  W2  Your solution must not rely on breadth-first search (BFS). {'dfs': 2}\n  W3  Avoid breadth-first search (BFS) entirely.                 {'dfs': 2}\n  W4  Breadth-first search (BFS) is not allowed here.            {'dfs': 1, 'bfs': 1}\n  W5  Write a correct solution that does not use breadth-first search (BFS). {'dfs': 2}\n== t2: banned X = 'dijkstra', substitute X' = 'bf_spfa'\n  W1  Do not use Dijkstra's algorithm for this task.             {'dijkstra': 1, 'bf_spfa': 1}\n  W2  Your solution must not rely on Dijkstra's algorithm.       {'bf_spfa': 2}\n  W3  Avoid Dijkstra's algorithm entirely.                       {'dijkstra': 1, 'bf_spfa': 1}\n  W4  Dijkstra's algorithm is not allowed here.                  {'dijkstra': 1, 'bf_spfa': 1}\n  W5  Write a correct solution that does not use Dijkstra's algorithm. {'dijkstra': 1, 'bf_spfa': 1}\n\n---- full prompt (t1, W4) ----\nBreadth-first search (BFS) is not allowed here.\n\nTask: write a Python function solve(grid, start, goal) that finds a path between two cells of a grid. grid is a list of equal-length strings with between 1 and 30 rows and between 1 and 30 columns; the character . is a free cell and the character # is a wall. start and goal are (row, col) tuples of 0-based indices. A move goes to one of the 4 orthogonal neighbours (up, down, left, right) and may not leave the grid or enter a wall. Return a list of (row, col) tuples that begins with start, ends with goal, and in which consecutive cells are neighbours and every cell is free. Any valid path is accepted; it does not have to be the shortest. If start equals goal and the cell is free, return [start]. If no path exists, or start or goal is a wall, return [].\n\nUse only the Python standard library. Return only one ```python code block containing the function solve and any helpers, with no example usage and no explanation.\n\n---- program written under the t1 W4 ban, labelled 'bfs' (seed 20261082, passed hidden tests: True, commit token 'queue' at generated token 118) ----\ndef solve(grid, start, goal):\n    if not (0 <= start[0] < len(grid) and 0 <= start[1] < len(grid[0]) or\n            0 <= goal[0] < len(grid) and 0 <= goal[1] < len(grid[0])):\n        return []\n    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':\n        return []\n    if start == goal:\n        return [start]\n    \n    visited = set()\n    queue = [(st...<trunc>\n===== cell 14 (exec 9) id=cell-14\n[stdout] 10:04:14|INFO   |[final] start\n\n[stdout] 10:04:14|INFO   |[final] done in 0.0 min\n\n===== cell 16 (exec 10) id=cell-16\n[result/plain]    task template   n  banned share    Wilson 95%  avoidance  event gate  \\\n0    t1       W1   2           0.0  [0.00, 0.66]        1.0       False   \n1    t1       W2   2           0.0  [0.00, 0.66]        1.0       False   \n2    t1       W3   2           0.0  [0.00, 0.66]        1.0       False   \n3    t1       W4   2           0.5  [0.09, 0.91]        0.5       False   \n4    t1       W5   2           0.0  [0.00, 0.66]        1.0       False   \n5    t1   pooled  10           0.1  [0.02, 0.40]        0.9       False   \n6    t2       W1   2           0.5  [0.09, 0.91]        0.5       False   \n7    t2       W2   2           0.0  [0.00, 0.66]        1.0       False   \n8    t2       W3   2           0.5  [0.09, 0.91]        0.5       False   \n9    t2       W4   2           0.5  [0.09, 0.91]        0.5       False   \n10   t2       W5   2           0.5  [0.09, 0.91]        0.5       False   \n11   t2   pooled  10           0.4  [0.17, 0.69]        0.6       False   \n\n    compliant share  pass rate                        landing  full pool: n  \\\n0               0.0        0.0                     {'dfs': 2}            20   \n1               1.0        1.0                     {'dfs': 2}            20   \n2               0.5        0.5                     {'dfs': 2}            20   \n3               0.5        1.0           {'dfs': 1, 'bfs': 1}            20   \n4               0.5        0.5                     {'dfs': 2}            20   \n5               0.5        0.6           {'dfs': 9, 'bfs': 1}           100   \n6               0.5        1.0  {'dijkstra': 1, 'bf_spfa': 1}            20   \n7               1.0        1.0                 {'bf_spfa': 2}            20   \n8               0.5        1.0  {'dijkstra': 1, 'bf_spfa': 1}            20   \n9               0.5        1.0  {'dijkstra': 1, 'bf_spfa': 1}            20   \n10              0.5        1.0  {'dijkstra': 1, 'bf_spfa': 1}            20   \n11              0.6        1.0  {'dijkstra': 4, 'bf_spfa': 6}           100   \n\n    full pool: banned share  full pool: event gate  \n0                      0.00                   True  \n1                      0.00                   True  \n2                      0.00                   True  \n3                      0.75                  False  \n4                      0.00                   True  \n5                      0.15                   True  \n6                      0.05                  False  \n7                      0.00                   True  \n8                  \n===== cell 18 (exec 11) id=cell-18\n===== cell 20 (exec 12) id=cell-20\n[stdout] 10:04:15|INFO   |[analyse_readout_i_replication] start\n\n[stdout] 10:04:15|INFO   |(i) t1|L27|k_pre: n=10 banned=1 sae_top1=0.00 sae_top20_lr=0.00 raw_dim=1.00 raw_lr=1.00 neuron_top1=0.00 neuron_top20_lr=1.00 sae_code_dim=1.00\n\n[stdout] 10:04:15|INFO   |(i) t2|L27|k_pre: n=10 banned=4 sae_top1=0.62 sae_top20_lr=1.00 raw_dim=0.75 raw_lr=0.50 neuron_top1=0.50 neuron_top20_lr=0.50 sae_code_dim=0.75\n\n[stdout] 10:04:15|INFO   |[analyse_readout_i_replication] done in 0.0 min\n\n===== cell 22 (exec 13) id=cell-22\n[result/plain]           config          readout   n  n banned  AUC pooled pooled 95% CI  \\\n0   t1|L27|k_pre         sae_top1  10         1       0.444             -   \n1   t1|L27|k_pre     sae_top20_lr  10         1       0.778             -   \n2   t1|L27|k_pre          raw_dim  10         1       1.000             -   \n3   t1|L27|k_pre           raw_lr  10         1       0.889             -   \n4   t1|L27|k_pre      neuron_top1  10         1       0.222             -   \n5   t1|L27|k_pre  neuron_top20_lr  10         1       0.889             -   \n6   t1|L27|k_pre     sae_code_dim  10         1       1.000             -   \n7   t2|L27|k_pre         sae_top1  10         4       0.583             -   \n8   t2|L27|k_pre     sae_top20_lr  10         4       0.750             -   \n9   t2|L27|k_pre          raw_dim  10         4       0.625             -   \n10  t2|L27|k_pre           raw_lr  10         4       0.417             -   \n11  t2|L27|k_pre      neuron_top1  10         4       0.625             -   \n12  t2|L27|k_pre  neuron_top20_lr  10         4       0.375             -   \n13  t2|L27|k_pre     sae_code_dim  10         4       0.583             -   \n\n    AUC within-template within 95% CI  within pairs  full pool: AUC within  \\\n0                 0.000             -             1                  0.520   \n1                 0.000             -             1                  0.707   \n2                 1.000             -             1                  1.000   \n3                 1.000             -             1                  1.000   \n4                 0.000             -             1                  0.707   \n5                 1.000             -             1                  1.000   \n6                 1.000             -             1                  1.000   \n7                 0.625             -             4                  0.513   \n8                 1.000             -             4                  0.768   \n9                 0.750             -             4                  0.760   \n10                0.500             -             4                  0.664   \n11                0.500             -             4                  0.677   \n12                0.500             -             4                  0.659   \n13                0.750             -             4                  0.766   \n\n    full pool: pairs  \n0                 75  \n1                 75  \n2                 75  \n3                 75  \n4                 75  \n5                 75  \n6           \n===== cell 24 (exec 14) id=cell-24\n[stdout] {\n \"n_checks\": 4,\n \"n_mismatches\": 0,\n \"mismatches\": []\n}\n\n[stdout] fresh_pool_banned_share_t1                 {'rederived': 0.1, 'pipeline': 0.1, 'match': True}\nfresh_pool_banned_share_t2                 {'rederived': 0.4, 'pipeline': 0.4, 'match': True}\nreplication_dim_auc_t1|L27|k_pre           {'rederived': 1.0, 'pipeline': 1.0, 'match': True}\nplacebo_replication_shuffled_t1|L27|k_pre  {'placebo_mean_auc': 0.5555555555555556}\nreplication_dim_auc_t2|L27|k_pre           {'rederived': 0.625, 'pipeline': 0.625, 'match': True}\nplacebo_replication_shuffled_t2|L27|k_pre  {'placebo_mean_auc': 0.8125}\n\n===== cell 26 (exec 15) id=cell-26\n[result/plain] <Figure size 1100x1300 with 6 Axes>\n[image/png] 136652 b64 chars\n[stdout] === key numbers: demo subset (full 200-run pool in brackets) ===\nt1: banned share 0.10 (0.15) | W4 alone 0.50 (0.75) | pooled event gate False (True) | landing {'dfs': 9, 'bfs': 1}\nt2: banned share 0.40 (0.13) | W4 alone 0.50 (0.30) | pooled event gate False (True) | landing {'dijkstra': 4, 'bf_spfa': 6}\nt1|L27|k_pre: within-template AUC  DiM 1.00 (1.00) | SAE top-1 latent 0.00 (0.52) | SAE top-20 probe 0.00 (0.71) | shuffled-label DiM pooled AUC 0.56\nt2|L27|k_pre: within-template AUC  DiM 0.75 (0.76) | SAE top-1 latent 0.62 (0.51) | SAE top-20 probe 1.00 (0.77) | shuffled-label DiM pooled AUC 0.81\nverify_headlines (checks 1 + 5): 4 checks, 0 mismatches\nSAE transfer test (full artifact): 0/3 layers pass; dCE ratio L15 3.29, L20 1.95, L27 1.59  [rule: PASS(L) := dCE_inst(L) <= 1.5 x dCE_base(L) (spliced-in CE over response tokens)]", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
````

### [80] THINKING · 2026-10-26 10:05:37 UTC

```
All cells run cleanly with verify passing 4/4 and DiM AUC results matching the full pool closely. Next I'll strip outputs to keep the Read small, then use NotebookEdit to apply the error-bar clamp and scaling round 2 before re-running tests.
```

### [81] TOOL CALL — Bash · 2026-10-26 10:05:37 UTC

```
Clear notebook outputs before reading:
/tmp/aii_nb_test_envs/art_3iv5G76C3yoX-2eaf8ea929eb/bin/jupyter nbconvert --clear-output --inplace code_demo.ipynb 2>&1 | tail -1 && ls -la code_demo.ipynb
```

### [82] TOOL RESULT — Bash · 2026-10-26 10:05:39 UTC

```
{"stdout": "[NbConvertApp] Writing 64624 bytes to code_demo.ipynb\n-rw-rw-rw- 1 aii-agent aii-agent 64653 Oct 26 10:05 code_demo.ipynb", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [83] TOOL CALL — Read · 2026-10-26 10:05:41 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/code_demo.ipynb
```

### [84] TOOL RESULT — Read · 2026-10-26 10:05:42 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [85] ASSISTANT · 2026-10-26 10:05:53 UTC

```
I've read the notebook. Before editing, let me check the commit-token claim in the cell-11 markdown against the data. Run 1 showed a BFS program committing at `queue`, not `deque`.
```

### [86] TOOL CALL — Bash · 2026-10-26 10:05:53 UTC

```
Tabulate commit tokens by task and label:
python3 - <<'EOF'
import json
from collections import Counter
for name, path in (("demo", "mini_demo_data.json"), ("full", "/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_12/full_method_out.json")):
    d = json.load(open(path))
    ex = d["datasets"][0]["examples"]
    c = Counter((e["metadata_task"], e["output"], e["metadata_evidence_term"]) for e in ex)
    print("==", name)
    for k in sorted(c, key=lambda k: (k[0], k[1], -c[k])):
        print("  ", k, c[k])
EOF
```

### [87] TOOL RESULT — Bash · 2026-10-26 10:05:53 UTC

```
{"stdout": "== demo\n   ('t1', 'bfs', 'queue') 4\n   ('t1', 'bfs', 'deque') 3\n   ('t1', 'dfs', 'dfs') 18\n   ('t1', 'dfs', 'stack') 10\n   ('t1', 'dfs', 'Recurs') 8\n   ('t1', 'dfs', 'DFS') 3\n   ('t1', 'dfs', 'depth-first') 2\n   ('t1', 'dfs', None) 1\n   ('t1', 'dfs', 'Depth-first') 1\n   ('t2', 'bf_spfa', 'deque') 34\n   ('t2', 'bf_spfa', 'Bellman') 8\n   ('t2', 'dijkstra', 'deque') 4\n   ('t2', 'dijkstra', 'heapq') 3\n   ('t2', 'other', 'deque') 1\n== full\n   ('t1', 'bfs', 'deque') 9\n   ('t1', 'bfs', 'queue') 6\n   ('t1', 'dfs', 'dfs') 39\n   ('t1', 'dfs', 'stack') 18\n   ('t1', 'dfs', 'Recurs') 14\n   ('t1', 'dfs', 'DFS') 5\n   ('t1', 'dfs', None) 3\n   ('t1', 'dfs', 'depth-first') 3\n   ('t1', 'dfs', 'Stack') 2\n   ('t1', 'dfs', 'Depth-first') 1\n   ('t2', 'bf_spfa', 'deque') 72\n   ('t2', 'bf_spfa', 'Bellman') 14\n   ('t2', 'dijkstra', 'deque') 7\n   ('t2', 'dijkstra', 'heapq') 6\n   ('t2', 'other', 'deque') 1", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [88] THINKING · 2026-10-26 10:06:09 UTC

```
I found that BFS and DFS commit at different lexical tokens on T1 (deque/queue vs dfs/stack/recursion), while on T2 both classes mostly commit at the same `deque` token, reducing that confound. I'll update cell-11's markdown to reflect this precisely.
```

### [89] TOOL CALL — NotebookEdit · 2026-10-26 10:06:09 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/code_demo.ipynb', 'cell_id': 'cell-11', 'cell_type': 'markdown', 'new_source': '### A look at the data: the ban sentences, and what the model wrote under them\n\nThe next cell prints three things:\n- the ban sentence of every template, with where the runs landed;\n- one full prompt;\n- the start of one BFS program and one DFS program written under the **same** W4 ban.\n\nIt ends with the *commit token* per label. The commit token is the first algorithm-identifying lexicon match that the\ncommit locator found, and `k_pre` is the token just before it. The commit token affects how to read the readouts:\n- On **T1** it differs by class. BFS programs commit at `deque` or `queue`, while DFS programs commit at `dfs`, a\n  `stack`, or a recursive call (`Recurs`).\n- On **T2** most runs of *both* classes commit at the same `deque` import, as exp3 also found.'}
```

### [90] TOOL RESULT — NotebookEdit · 2026-10-26 10:06:10 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [91] ASSISTANT · 2026-10-26 10:06:35 UTC

```
Edit 2, the visualisation cell: clamp both error-bar terms at 0 (Wilson float noise, and bootstrap CIs that don't bracket the point estimate) and make the row-1 title plainer.
```

### [92] TOOL CALL — NotebookEdit · 2026-10-26 10:06:35 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/code_demo.ipynb', 'cell_id': 'cell-26', 'new_source': 'plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})  # as in figures.py\nC = ["#3b6ea8", "#d1495b", "#66a182", "#edae49", "#7d5ba6", "#8d6a4f", "#4f4f4f"]          # figures.py palette\nMORDER = ["sae_top1", "sae_top20_lr", "sae_code_dim", "raw_dim", "raw_lr", "neuron_top1", "neuron_top20_lr"]\nMNAME = {"sae_top1": "SAE top-1\\nlatent", "sae_top20_lr": "SAE top-20\\nlogistic", "sae_code_dim": "DiM on\\nSAE code",\n         "raw_dim": "DiM\\n(raw)", "raw_lr": "raw\\nlogistic", "neuron_top1": "top-1\\nneuron",\n         "neuron_top20_lr": "top-20\\nneurons"}\n\n\ndef _f2(v):\n    return "n/a" if v is None or (isinstance(v, float) and not np.isfinite(v)) else f"{v:.2f}"\n\n\ndef _sc(r):\n    return SCORES[(r["task"], r["template"], r["sample_id"])]\n\n\ndef _yerr(v, lo, hi):\n    # error-bar lengths, clamped at 0: a Wilson bound at a share of 0 or 1 can sit ~1e-17 on the wrong side,\n    # and a bootstrap percentile CI need not contain the point estimate (matplotlib rejects negative lengths)\n    return [[max(v - lo, 0.0)], [max(hi - v, 0.0)]]\n\n\nfig, axes = plt.subplots(3, 2, figsize=(11, 13))\nfor col, t in enumerate(TASKS):\n    # row 1: banned share per template (Wilson 95% CI)\n    ax = axes[0, col]\n    ws = TEMPLATE_IDS + ["pooled"]\n    for j, w in enumerate(ws):\n        p = fresh["per_task"][t][w]\n        v, (lo, hi) = p["banned_share"], p["banned_share_wilson"]\n        ax.bar(j, v, 0.6, color=C[6] if w == "pooled" else C[1], alpha=0.85)\n        ax.errorbar(j, v, yerr=_yerr(v, lo, hi), fmt="none", ecolor="k", capsize=3, lw=0.8)\n    ax.scatter(range(len(ws)), [REF["fresh_pool_summary"][t][w]["banned_share"] for w in ws], marker="D", s=22,\n               color="k", zorder=3, label="full 200-run pool")\n    ax.set_xticks(range(len(ws)), ws)\n    ax.set_ylim(0, 1.05)\n    ax.set_ylabel(f"share of runs that still write {BANNED[t]}")\n    ax.set_title(f"{t}: runs that ignore the {BANNED[t]} ban, per template (bars: demo, {N_PER_CELL} runs each)",\n                 fontsize=9)\n    ax.legend(frameon=False, fontsize=7, loc="upper left")\n\n    # row 2: within-template AUC of every exp3-fitted readout (run-bootstrap 95% CI)\n    ax = axes[1, col]\n    key = f"{t}|L{READOUT_LAYER}|k_pre"\n    tr = rep_i["configs"].get(key, {}).get("transfer_from_exp3", {})\n    ref = REF["readout_i_replication"][key]["transfer_from_exp3"]\n    for j, m in enumerate(MORDER):\n        r = tr.get(m, {})\n        a = r.get("auc_within_template")\n        if a is not None and np.isfinite(a):\n            ax.bar(j, a, 0.6, color=C[j % len(C)])\n            ci = r.get("within_ci_runs") or [None, None]\n            if ci[0] is not None:\n                ax.errorbar(j, a, yerr=_yerr(a, ci[0], ci[1]), fmt="none", ecolor="k", capsize=3, lw=0.8)\n    ax.scatter(range(len(MORDER)), [ref[m]["auc_within_template"] for m in MORDER], marker="D", s=22, color="k",\n               zorder=3, label="full 200-run pool")\n    ax.axhline(0.5, color="grey", lw=0.6, ls="--")\n    pl = VER["checks"].get(f"placebo_replication_shuffled_{key}", {}).get("placebo_mean_auc")\n    if pl is not None:\n        ax.axhline(pl, color=C[3], lw=1.2, ls=":", label=f"DiM, shuffled labels (pooled, {N_PLACEBO}x): {pl:.2f}")\n    ax.set_xticks(range(len(MORDER)), [MNAME[m] for m in MORDER], fontsize=7)\n    ax.set_ylim(0, 1.05)\n    ax.set_ylabel("within-template AUC")\n    n_pairs = next(iter(tr.values()), {}).get("n_within_pairs", 0)\n    ax.set_title(f"{t}: exp3-fitted readouts at L{READOUT_LAYER} k_pre ({n_pairs} within-template pairs)", fontsize=9)\n    ax.legend(frameon=False, fontsize=7, loc="lower right")\n\n    # row 3: per-run readout geometry (L27 k_pre state projected on two exp3-fitted directions)\n    ax = axes[2, col]\n    for lab, colr in ((SUBSTITUTE[t], C[0]), (BANNED[t], C[1])):\n        for w, mk in zip(TEMPLATE_IDS, "osD^v"):\n            pts = [(_sc(r)["raw_dim"], _sc(r)["sae_top20_lr"]) for r in C1_ROWS\n                   if r["task"] == t and r["label"] == lab and r["template"] == w and _sc(r)]\n            if pts:\n                ax.scatter(*zip(*pts), color=colr, marker=mk, s=32, alpha=0.8, edgecolor="white", lw=0.4,\n                           label=f"{lab} | {w}")\n    ax.axvline(0, color="grey", lw=0.6, ls="--")\n    ax.axhline(0, color="grey", lw=0.6, ls="--")\n    ax.set_xlabel("DiM projection of the raw residual (exp3-fitted; > 0 = banned side)")\n    ax.set_ylabel("SAE top-20-latent logistic score (> 0 = banned)")\n    ax.set_title(f"{t}: one point per run (colour = algorithm written, marker = template)", fontsize=9)\n    ax.legend(frameon=False, fontsize=6, ncol=2)\nfig.tight_layout()\nfig.savefig(FIGS / "demo_summary.png", dpi=150)\nplt.show()\n\nprint("=== key numbers: demo subset (full 200-run pool in brackets) ===")\nfor t in TASKS:\n    p, f = fresh["per_task"][t]["pooled"], REF["fresh_pool_summary"][t]["pooled"]\n    w4, f4 = fresh["per_task"][t]["W4"], REF["fresh_pool_summary"][t]["W4"]\n    print(f"{t}: banned share {_f2(p[\'banned_share\'])} ({_f2(f[\'banned_share\'])}) | W4 alone {_f2(w4[\'banned_share\'])} "\n          f"({_f2(f4[\'banned_share\'])}) | pooled event gate {p[\'event_gate_pass\']} ({f[\'event_gate_pass\']}) | "\n          f"landing {p[\'landing\']}")\nfor t in TASKS:\n    key = f"{t}|L{READOUT_LAYER}|k_pre"\n    tr = rep_i["configs"].get(key, {}).get("transfer_from_exp3", {})\n    ref = REF["readout_i_replication"][key]["transfer_from_exp3"]\n    pl = VER["checks"].get(f"placebo_replication_shuffled_{key}", {}).get("placebo_mean_auc")\n    print(f"{key}: within-template AUC  DiM {_f2(tr.get(\'raw_dim\', {}).get(\'auc_within_template\'))} "\n          f"({_f2(ref[\'raw_dim\'][\'auc_within_template\'])}) | SAE top-1 latent "\n          f"{_f2(tr.get(\'sae_top1\', {}).get(\'auc_within_template\'))} ({_f2(ref[\'sae_top1\'][\'auc_within_template\'])}) | "\n          f"SAE top-20 probe {_f2(tr.get(\'sae_top20_lr\', {}).get(\'auc_within_template\'))} "\n          f"({_f2(ref[\'sae_top20_lr\'][\'auc_within_template\'])}) | shuffled-label DiM pooled AUC {_f2(pl)}")\nprint(f"verify_headlines (checks 1 + 5): {VER[\'n_checks\']} checks, {VER[\'n_mismatches\']} mismatches")\n_tt = REF["sae_transfer_test"]\nprint(f"SAE transfer test (full artifact): {_tt[\'n_pass\']}/3 layers pass; dCE ratio "\n      + ", ".join(f"L{L} {r:.2f}" for L, r in _tt["ratio_by_layer"].items()) + f"  [rule: {_tt[\'rule\']}]")'}
```

### [93] TOOL RESULT — NotebookEdit · 2026-10-26 10:06:36 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [94] ASSISTANT · 2026-10-26 10:06:44 UTC

```
Edit 3, scaling round 2 (about 2–10× up): `N_PER_CELL=5`, `N_BOOT=200`, `N_PLACEBO=20`.
```

### [95] TOOL CALL — NotebookEdit · 2026-10-26 10:06:44 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/code_demo.ipynb', 'cell_id': 'cell-06', 'new_source': '# ---- tunable parameters ------------------------------------------------------------------------------------------\nN_PER_CELL = 5        # runs used per task x template cell (max 10 = the whole demo file; the original pool has 20)\nN_BOOT = 200          # bootstrap resamples over runs for the AUC CIs (original: analysis.py N_BOOT = 2000)\nN_PLACEBO = 20        # shuffled-label placebo AUCs per config (original: verify_headlines.py, 200)\nC1_PER_TEMPLATE = 20  # runs per task x template in the original C1 pool (method.py default C1_PER_TEMPLATE=20)'}
```

### [96] TOOL RESULT — NotebookEdit · 2026-10-26 10:06:44 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [97] ASSISTANT · 2026-10-26 10:06:56 UTC

```
Running test round 2 in a freshly recreated venv:
```

### [98] TOOL CALL — Bash · 2026-10-26 10:06:56 UTC

```
Test-run notebook at scaling round 2:
T0=$(date +%s) && UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_3iv5G76C3yoX-2eaf8ea929eb && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_3iv5G76C3yoX-2eaf8ea929eb/bin/python jupyter ipykernel && T1=$(date +%s) && echo "venv setup: $((T1-T0)) s" && /tmp/aii_nb_test_envs/art_3iv5G76C3yoX-2eaf8ea929eb/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | grep -v "running over TCP"; T2=$(date +%s); echo "notebook runtime: $((T2-T1)) s"
```

### [99] TOOL RESULT — Bash · 2026-10-26 10:07:10 UTC

```
{"stdout": "venv setup: 1 s\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[NbConvertApp] Writing 240158 bytes to code_demo.ipynb\nnotebook runtime: 16 s", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [100] TOOL CALL — Bash · 2026-10-26 10:07:16 UTC

```
Check round 2 outputs for errors and key numbers:
python3 - <<'EOF'
import json
nb = json.load(open("code_demo.ipynb"))
errs = []
for i, c in enumerate(nb["cells"]):
    if c["cell_type"] != "code":
        continue
    for o in c["outputs"]:
        if o["output_type"] == "error":
            errs.append((c["id"], o["ename"], o["evalue"]))
        if o["output_type"] == "stream" and o["name"] == "stderr":
            print("STDERR in", c["id"], "".join(o["text"])[:500])
print("errors:", errs)
for cid in ("cell-20", "cell-24", "cell-26"):
    c = next(c for c in nb["cells"] if c["id"] == cid)
    for o in c["outputs"]:
        if o["output_type"] == "stream":
            print(f"--- {cid}:", "".join(o["text"])[:3000])
EOF
```

### [101] TOOL RESULT — Bash · 2026-10-26 10:07:16 UTC

```
{"stdout": "errors: []\n--- cell-20: 10:07:07|INFO   |[analyse_readout_i_replication] start\n\n--- cell-20: 10:07:07|INFO   |(i) t1|L27|k_pre: n=25 banned=2 sae_top1=0.33 sae_top20_lr=0.50 raw_dim=1.00 raw_lr=1.00 neuron_top1=0.50 neuron_top20_lr=1.00 sae_code_dim=1.00\n\n--- cell-20: 10:07:07|INFO   |(i) t2|L27|k_pre: n=25 banned=7 sae_top1=0.53 sae_top20_lr=0.80 raw_dim=0.75 raw_lr=0.55 neuron_top1=0.55 neuron_top20_lr=0.55 sae_code_dim=0.75\n\n--- cell-20: 10:07:07|INFO   |[analyse_readout_i_replication] done in 0.0 min\n\n--- cell-24: {\n \"n_checks\": 4,\n \"n_mismatches\": 0,\n \"mismatches\": []\n}\nfresh_pool_banned_share_t1                 {'rederived': 0.08, 'pipeline': 0.08, 'match': True}\nfresh_pool_banned_share_t2                 {'rederived': 0.28, 'pipeline': 0.28, 'match': True}\nreplication_dim_auc_t1|L27|k_pre           {'rederived': 0.9782608695652174, 'pipeline': 0.9782608695652174, 'match': True}\nplacebo_replication_shuffled_t1|L27|k_pre  {'placebo_mean_auc': 0.5010869565217393}\nreplication_dim_auc_t2|L27|k_pre           {'rederived': 0.7777777777777778, 'pipeline': 0.7777777777777778, 'match': True}\nplacebo_replication_shuffled_t2|L27|k_pre  {'placebo_mean_auc': 0.515079365079365}\n\n--- cell-26: === key numbers: demo subset (full 200-run pool in brackets) ===\nt1: banned share 0.08 (0.15) | W4 alone 0.40 (0.75) | pooled event gate True (True) | landing {'dfs': 23, 'bfs': 2}\nt2: banned share 0.28 (0.13) | W4 alone 0.60 (0.30) | pooled event gate False (True) | landing {'dijkstra': 7, 'bf_spfa': 18}\nt1|L27|k_pre: within-template AUC  DiM 1.00 (1.00) | SAE top-1 latent 0.33 (0.52) | SAE top-20 probe 0.50 (0.71) | shuffled-label DiM pooled AUC 0.50\nt2|L27|k_pre: within-template AUC  DiM 0.75 (0.76) | SAE top-1 latent 0.53 (0.51) | SAE top-20 probe 0.80 (0.77) | shuffled-label DiM pooled AUC 0.52\nverify_headlines (checks 1 + 5): 4 checks, 0 mismatches\nSAE transfer test (full artifact): 0/3 layers pass; dCE ratio L15 3.29, L20 1.95, L27 1.59  [rule: PASS(L) := dCE_inst(L) <= 1.5 x dCE_base(L) (spliced-in CE over response tokens)]", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [102] THINKING · 2026-10-26 10:07:36 UTC

```
Round 2 ran clean in 16s with placebo AUCs near 0.50 and DiM AUCs matching the full pool, confirming plenty of budget headroom. I'll now scale up to the final round 3 settings: N_PER_CELL=10, N_BOOT=2000, N_PLACEBO=200.
```

### [103] TOOL CALL — NotebookEdit · 2026-10-26 10:07:36 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/code_demo.ipynb', 'cell_id': 'cell-06', 'new_source': '# ---- tunable parameters ------------------------------------------------------------------------------------------\nN_PER_CELL = 10       # runs used per task x template cell (10 = the whole demo file; the original pool has 20)\nN_BOOT = 2000         # bootstrap resamples over runs for the AUC CIs (= the original, analysis.py N_BOOT = 2000)\nN_PLACEBO = 200       # shuffled-label placebo AUCs per config (= the original, verify_headlines.py)\nC1_PER_TEMPLATE = 20  # runs per task x template in the original C1 pool (method.py default C1_PER_TEMPLATE=20)\n# scaling log (local clean-venv test, incl. package install): N_PER_CELL=2/N_BOOT=1/N_PLACEBO=1 -> 17 s;\n# 5/200/20 -> 16 s; 10/2000/200 (original values) -> see README'}
```

### [104] TOOL RESULT — NotebookEdit [ERROR] · 2026-10-26 10:07:36 UTC

```
Error: File has been modified since read, either by the user or by a linter. Read it again before attempting to write it.
```

### [105] TOOL CALL — Bash · 2026-10-26 10:07:36 UTC

```
Clear old outputs and run final-scale test:
ls results logs figures && rm -f results/*.json logs/*.log figures/*.png && T0=$(date +%s) && UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_3iv5G76C3yoX-2eaf8ea929eb && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_3iv5G76C3yoX-2eaf8ea929eb/bin/python jupyter ipykernel && T1=$(date +%s) && echo "venv setup: $((T1-T0)) s" && /tmp/aii_nb_test_envs/art_3iv5G76C3yoX-2eaf8ea929eb/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | grep -v "running over TCP"; T2=$(date +%s); echo "notebook runtime: $((T2-T1)) s"
```

### [106] TOOL RESULT — Bash · 2026-10-26 10:07:52 UTC

```
{"stdout": "figures:\ndemo_summary.png\n\nlogs:\nstage_demo.log\n\nresults:\nfresh_pool_summary.json\nreadout_i_replication.json\ntiming.json\nverify_headlines.json\nvenv setup: 1 s\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[NbConvertApp] Writing 240158 bytes to code_demo.ipynb\nnotebook runtime: 16 s", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [107] THINKING · 2026-10-26 10:08:26 UTC

```
The edit got rejected since the notebook was rewritten by the round-2 nbconvert run after my last read. I'll preview the final-config numbers on a throwaway copy first, then do one fresh Read, make both remaining edits, and run the final conversion.
```

### [108] TOOL CALL — Bash · 2026-10-26 10:08:26 UTC

```
Preview final-config numbers on a throwaway notebook copy:
python3 - <<'EOF'
import json
nb = json.load(open("code_demo.ipynb"))
c = next(c for c in nb["cells"] if c["id"] == "cell-06")
src = "".join(c["source"]).replace("N_PER_CELL = 5 ", "N_PER_CELL = 10").replace("N_BOOT = 200 ", "N_BOOT = 2000").replace("N_PLACEBO = 20 ", "N_PLACEBO = 200")
c["source"] = src
print(src)
json.dump(nb, open("_preview_final.ipynb", "w"))
EOF
T1=$(date +%s); /tmp/aii_nb_test_envs/art_3iv5G76C3yoX-2eaf8ea929eb/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 _preview_final.ipynb --output _preview_final.ipynb 2>&1 | grep -v "running over TCP"; T2=$(date +%s); echo "preview runtime (packages already installed): $((T2-T1)) s"
python3 - <<'EOF'
import json
nb = json.load(open("_preview_final.ipynb"))
for c in nb["cells"]:
    if c["cell_type"] != "code": continue
    for o in c["outputs"]:
        if o["output_type"] == "error": print("ERROR", c["id"], o["ename"], o["evalue"])
for cid in ("cell-10", "cell-20", "cell-24", "cell-26"):
    c = next(c for c in nb["cells"] if c["id"] == cid)
    for o in c["outputs"]:
        if o["output_type"] == "stream": print(f"--- {cid}:", "".join(o["text"])[:2500])
c = next(c for c in nb["cells"] if c["id"] == "cell-22")
for o in c["outputs"]:
    if "data" in o and "text/plain" in o["data"]: print("".join(o["data"]["text/plain"]))
EOF
rm -f _preview_final.ipynb
```

### [109] TOOL RESULT — Bash · 2026-10-26 10:08:32 UTC

```
{"stdout": "# ---- tunable parameters ------------------------------------------------------------------------------------------\nN_PER_CELL = 10       # runs used per task x template cell (max 10 = the whole demo file; the original pool has 20)\nN_BOOT = 2000         # bootstrap resamples over runs for the AUC CIs (original: analysis.py N_BOOT = 2000)\nN_PLACEBO = 200       # shuffled-label placebo AUCs per config (original: verify_headlines.py, 200)\nC1_PER_TEMPLATE = 20  # runs per task x template in the original C1 pool (method.py default C1_PER_TEMPLATE=20)\n[NbConvertApp] Converting notebook _preview_final.ipynb to notebook\n[NbConvertApp] Writing 248187 bytes to _preview_final.ipynb\npreview runtime (packages already installed): 9 s\n--- cell-10: 100 runs | readout layer L27 | runs with a k_pre score: 98\nlabel          bf_spfa  bfs  dfs  dijkstra  other\ntask template                                    \nt1   W1              0    0   10         0      0\n     W2              0    0   10         0      0\n     W3              0    0   10         0      0\n     W4              0    7    3         0      0\n     W5              0    0   10         0      0\nt2   W1              9    0    0         1      0\n     W2             10    0    0         0      0\n     W3              7    0    0         2      1\n     W4              7    0    0         3      0\n     W5              9    0    0         1      0\n\n--- cell-20: 10:08:26|INFO   |[analyse_readout_i_replication] start\n\n--- cell-20: 10:08:27|INFO   |(i) t1|L27|k_pre: n=49 banned=7 sae_top1=0.29 sae_top20_lr=0.48 raw_dim=1.00 raw_lr=1.00 neuron_top1=0.57 neuron_top20_lr=1.00 sae_code_dim=1.00\n\n--- cell-20: 10:08:29|INFO   |(i) t2|L27|k_pre: n=49 banned=7 sae_top1=0.54 sae_top20_lr=0.82 raw_dim=0.76 raw_lr=0.61 neuron_top1=0.63 neuron_top20_lr=0.61 sae_code_dim=0.76\n\n--- cell-20: 10:08:29|INFO   |[analyse_readout_i_replication] done in 0.1 min\n\n--- cell-24: {\n \"n_checks\": 4,\n \"n_mismatches\": 0,\n \"mismatches\": []\n}\nfresh_pool_banned_share_t1                 {'rederived': 0.14, 'pipeline': 0.14, 'match': True}\nfresh_pool_banned_share_t2                 {'rederived': 0.14, 'pipeline': 0.14, 'match': True}\nreplication_dim_auc_t1|L27|k_pre           {'rederived': 0.9761904761904762, 'pipeline': 0.9761904761904762, 'match': True}\nplacebo_replication_shuffled_t1|L27|k_pre  {'placebo_mean_auc': 0.49278911564625844}\nreplication_dim_auc_t2|L27|k_pre           {'rederived': 0.7738095238095237, 'pipeline': 0.7738095238095238, 'match': True}\nplacebo_replication_shuffled_t2|L27|k_pre  {'placebo_mean_auc': 0.49392006802721083}\n\n--- cell-26: === key numbers: demo subset (full 200-run pool in brackets) ===\nt1: banned share 0.14 (0.15) | W4 alone 0.70 (0.75) | pooled event gate True (True) | landing {'dfs': 43, 'bfs': 7}\nt2: banned share 0.14 (0.13) | W4 alone 0.30 (0.30) | pooled event gate True (True) | landing {'dijkstra': 7, 'bf_spfa': 42, 'other': 1}\nt1|L27|k_pre: within-template AUC  DiM 1.00 (1.00) | SAE top-1 latent 0.29 (0.52) | SAE top-20 probe 0.48 (0.71) | shuffled-label DiM pooled AUC 0.49\nt2|L27|k_pre: within-template AUC  DiM 0.76 (0.76) | SAE top-1 latent 0.54 (0.51) | SAE top-20 probe 0.82 (0.77) | shuffled-label DiM pooled AUC 0.49\nverify_headlines (checks 1 + 5): 4 checks, 0 mismatches\nSAE transfer test (full artifact): 0/3 layers pass; dCE ratio L15 3.29, L20 1.95, L27 1.59  [rule: PASS(L) := dCE_inst(L) <= 1.5 x dCE_base(L) (spliced-in CE over response tokens)]\n\n          config          readout   n  n banned  AUC pooled pooled 95% CI  \\\n0   t1|L27|k_pre         sae_top1  49         7       0.609  [0.34, 0.90]   \n1   t1|L27|k_pre     sae_top20_lr  49         7       0.888  [0.76, 0.99]   \n2   t1|L27|k_pre          raw_dim  49         7       0.976  [0.93, 1.00]   \n3   t1|L27|k_pre           raw_lr  49         7       0.949  [0.86, 1.00]   \n4   t1|L27|k_pre      neuron_top1  49         7       0.554  [0.21, 0.89]   \n5   t1|L27|k_pre  neuron_top20_lr  49         7       0.932  [0.83, 1.00]   \n6   t1|L27|k_pre     sae_code_dim  49         7       0.969  [0.91, 1.00]   \n7   t2|L27|k_pre         sae_top1  49         7       0.571  [0.52, 0.62]   \n8   t2|L27|k_pre     sae_top20_lr  49         7       0.753  [0.53, 0.95]   \n9   t2|L27|k_pre          raw_dim  49         7       0.774  [0.59, 0.95]   \n10  t2|L27|k_pre           raw_lr  49         7       0.560  [0.24, 0.89]   \n11  t2|L27|k_pre      neuron_top1  49         7       0.655  [0.39, 0.91]   \n12  t2|L27|k_pre  neuron_top20_lr  49         7       0.543  [0.22, 0.88]   \n13  t2|L27|k_pre     sae_code_dim  49         7       0.767  [0.56, 0.95]   \n\n    AUC within-template within 95% CI  within pairs  full pool: AUC within  \\\n0                 0.286  [0.00, 0.75]            21                  0.520   \n1                 0.476  [0.04, 0.90]            21                  0.707   \n2                 1.000  [1.00, 1.00]            21                  1.000   \n3                 1.000  [1.00, 1.00]            21                  1.000   \n4                 0.571  [0.14, 1.00]            21                  0.707   \n5                 1.000  [1.00, 1.00]            21                  1.000   \n6                 1.000  [1.00, 1.00]            21                  1.000   \n7                 0.538  [0.50, 0.65]            53                  0.513   \n8                 0.821  [0.60, 1.00]            53                  0.768   \n9                 0.764  [0.48, 0.98]            53                  0.760   \n10                0.613  [0.27, 0.97]            53                  0.664   \n11                0.632  [0.29, 0.97]            53                  0.677   \n12                0.613  [0.27, 0.97]            53                  0.659   \n13                0.764  [0.48, 0.98]            53                  0.766   \n\n    full pool: pairs  \n0                 75  \n1                 75  \n2                 75  \n3                 75  \n4                 75  \n5                 75  \n6                 75  \n7                192  \n8                192  \n9                192  \n10               192  \n11               192  \n12               192  \n13               192", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [110] THINKING · 2026-10-26 10:08:44 UTC

```
The final run confirms the demo subset closely matches the full pool on banned share and DiM AUCs, with placebo at chance and zero verification mismatches; the one nuance is that the SAE probe roughly ties DiM on T2 but drops to chance on T1 within W4. I'll note this in the closing markdown, clear outputs, re-read, then apply both edits.
```

### [111] TOOL CALL — Bash · 2026-10-26 10:08:44 UTC

```
Clear outputs and stale notebook artifacts:
/tmp/aii_nb_test_envs/art_3iv5G76C3yoX-2eaf8ea929eb/bin/jupyter nbconvert --clear-output --inplace code_demo.ipynb 2>&1 | tail -1 && rm -f results/*.json logs/*.log figures/*.png && ls -la results logs figures
```

### [112] TOOL RESULT — Bash · 2026-10-26 10:08:46 UTC

```
{"stdout": "[NbConvertApp] Writing 65161 bytes to code_demo.ipynb\nfigures:\ntotal 1954\ndrwxrwxrwx 2 aii-agent aii-agent       1 Oct 26 10:08 .\ndrwxrwxrwx 7 aii-agent aii-agent 2000120 Oct 26 10:08 ..\n\nlogs:\ntotal 1954\ndrwxrwxrwx 2 aii-agent aii-agent       1 Oct 26 10:08 .\ndrwxrwxrwx 7 aii-agent aii-agent 2000120 Oct 26 10:08 ..\n\nresults:\ntotal 1954\ndrwxrwxrwx 2 aii-agent aii-agent       1 Oct 26 10:08 .\ndrwxrwxrwx 7 aii-agent aii-agent 2000120 Oct 26 10:08 ..", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [113] TOOL CALL — Read · 2026-10-26 10:08:52 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/code_demo.ipynb
```

### [114] TOOL RESULT — Read · 2026-10-26 10:08:52 UTC

```
{"type": "file_unchanged", "file": {"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/code_demo.ipynb"}}
```

### [115] THINKING · 2026-10-26 10:09:00 UTC

```
The notebook state matches what I last read, so I can edit directly. I'll start with the config cell containing the original values and scaling log.
```

### [116] TOOL CALL — NotebookEdit · 2026-10-26 10:09:00 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/code_demo.ipynb', 'cell_id': 'cell-06', 'new_source': '# ---- tunable parameters ------------------------------------------------------------------------------------------\nN_PER_CELL = 10       # runs used per task x template cell (10 = the whole demo file; the original pool has 20)\nN_BOOT = 2000         # bootstrap resamples over runs for the AUC CIs (= the original, analysis.py N_BOOT = 2000)\nN_PLACEBO = 200       # shuffled-label placebo AUCs per config (= the original, verify_headlines.py)\nC1_PER_TEMPLATE = 20  # runs per task x template in the original C1 pool (method.py default C1_PER_TEMPLATE=20)\n# scaling log (clean local venv, notebook runtime incl. package install):\n#   N_PER_CELL=2,  N_BOOT=1,    N_PLACEBO=1   -> 17 s\n#   N_PER_CELL=5,  N_BOOT=200,  N_PLACEBO=20  -> 16 s\n#   N_PER_CELL=10, N_BOOT=2000, N_PLACEBO=200 -> ~20 s (original analysis values; ~9 s once packages are installed)'}
```

### [117] TOOL RESULT — NotebookEdit · 2026-10-26 10:09:00 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [118] ASSISTANT · 2026-10-26 10:09:14 UTC

```
Now the closing "Reading the results" markdown, aligned with the final numbers and the T1/T2 commit-token nuance:
```

### [119] TOOL CALL — NotebookEdit · 2026-10-26 10:09:14 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/code_demo.ipynb', 'cell_id': 'cell-27', 'cell_type': 'markdown', 'new_source': '### Reading the results\n\n- **A ban mostly substitutes; it does not subtract, and it does not make the model inventive.** Under four of the five\n  templates, T1 never produces BFS. Instead the model writes DFS, the next most common grid-path algorithm. Under\n  W4, *"BFS is not allowed here."*, it still writes BFS most of the time. T2 shows the same pattern, with\n  Bellman-Ford/SPFA standing in for Dijkstra. On T2 the ban fails most often under W3 and W4. Across the pool almost\n  nothing lands outside the banned algorithm and its one natural substitute; the only exception is a single `other`\n  run. So the *wording* of a ban decides how often it works. What replaces the banned algorithm is the runner-up, not\n  a novel solution.\n- **The cheap baseline wins.** The class-mean-difference (DiM) direction was fitted on exp3 states. On the fresh pool\n  it separates banned from substitute runs *within the same template*:\n  - **T1**: perfectly. This rests on W4\'s pairs alone, the only template with both classes.\n  - **T2**: AUC about 0.76 in both the demo and the full pool, but with a wide CI.\n\n  The single best SAE latent from exp3 does not transfer. The top-20-latent probe roughly ties DiM on T2, with\n  overlapping CIs, but it falls to chance inside W4 on T1. Every SAE readout here is also out-of-distribution, because\n  the base→instruct transfer test failed. Shuffled labels give about 0.5.\n- **What `k_pre` measures.** `k_pre` is the state just before the first algorithm-identifying token.\n  - On **T1** that token differs by class: `deque`/`queue` for BFS, and `dfs`/`stack`/recursion for DFS. So the T1\n    readout may partly read *which word the model is about to write*, rather than an earlier decision.\n  - On **T2** most runs of both classes commit at the same `deque` token, so the T2 separation is less exposed to\n    this confound.\n\n  The artifact reports all these readouts as descriptive, not causal.\n- **Demo vs full run.** The demo uses half of the pool, 10 runs per template. Its CIs are therefore wider, and a few\n  per-template shares differ from the full pool. Each number sits next to its full-pool value, shown as black diamonds\n  in the figure and as bracketed values in the printout.\n  - `N_PER_CELL = 10` already uses the whole demo file.\n  - All 200 runs, every layer and position, and the GPU stages need the original pipeline:\n    `uv run method.py --stage vllm1 | label | hf | analyse | final | verify`.'}
```

### [120] TOOL RESULT — NotebookEdit · 2026-10-26 10:09:14 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [121] ASSISTANT · 2026-10-26 10:09:26 UTC

```
Final test run 3 at the original values (`N_PER_CELL=10, N_BOOT=2000, N_PLACEBO=200`) in a freshly recreated venv:
```

### [122] TOOL CALL — Bash · 2026-10-26 10:09:26 UTC

```
Final clean-venv test run at original parameters:
T0=$(date +%s) && UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_3iv5G76C3yoX-2eaf8ea929eb && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_3iv5G76C3yoX-2eaf8ea929eb/bin/python jupyter ipykernel && T1=$(date +%s) && echo "venv setup: $((T1-T0)) s" && /tmp/aii_nb_test_envs/art_3iv5G76C3yoX-2eaf8ea929eb/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | grep -v "running over TCP"; RC=${PIPESTATUS[0]}; T2=$(date +%s); echo "nbconvert exit=$RC, notebook runtime: $((T2-T1)) s"; ls -la code_demo.ipynb results logs figures
```

### [123] TOOL RESULT — Bash · 2026-10-26 10:09:46 UTC

```
{"stdout": "venv setup: 1 s\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[NbConvertApp] Writing 249246 bytes to code_demo.ipynb\nnbconvert exit=0, notebook runtime: 21 s\n-rw-rw-rw- 1 aii-agent aii-agent  249275 Oct 26 10:09 code_demo.ipynb\n\nfigures:\ntotal 3134\ndrwxrwxrwx 2 aii-agent aii-agent 1018512 Oct 26 10:09 .\ndrwxrwxrwx 7 aii-agent aii-agent 2000164 Oct 26 10:09 ..\n-rw-rw-rw- 1 aii-agent aii-agent  189566 Oct 26 10:09 demo_summary.png\n\nlogs:\ntotal 2034\ndrwxrwxrwx 2 aii-agent aii-agent   80600 Oct 26 10:09 .\ndrwxrwxrwx 7 aii-agent aii-agent 2000164 Oct 26 10:09 ..\n-rw-rw-rw- 1 aii-agent aii-agent     806 Oct 26 10:09 stage_demo.log\n\nresults:\ntotal 2956\ndrwxrwxrwx 2 aii-agent aii-agent 1002200 Oct 26 10:09 .\ndrwxrwxrwx 7 aii-agent aii-agent 2000164 Oct 26 10:09 ..\n-rw-rw-rw- 1 aii-agent aii-agent    4921 Oct 26 10:09 fresh_pool_summary.json\n-rw-rw-rw- 1 aii-agent aii-agent   16484 Oct 26 10:09 readout_i_replication.json\n-rw-rw-rw- 1 aii-agent aii-agent     397 Oct 26 10:09 timing.json\n-rw-rw-rw- 1 aii-agent aii-agent     731 Oct 26 10:09 verify_headlines.json", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [124] ASSISTANT · 2026-10-26 10:09:56 UTC

```
The final run passed: exit 0, 21 s against a 600 s budget. Let me confirm there are no errors or stderr in any cell, then look at the rendered figure.
```

### [125] TOOL CALL — Bash · 2026-10-26 10:09:56 UTC

```
Confirm final run has no errors and print key numbers:
python3 - <<'EOF'
import json
nb = json.load(open("code_demo.ipynb"))
n_code = sum(c["cell_type"] == "code" for c in nb["cells"])
executed = [c.get("execution_count") for c in nb["cells"] if c["cell_type"] == "code"]
errs = [(c["id"], o["ename"]) for c in nb["cells"] if c["cell_type"] == "code" for o in c["outputs"] if o["output_type"] == "error"]
stderr = [c["id"] for c in nb["cells"] if c["cell_type"] == "code" for o in c["outputs"] if o["output_type"] == "stream" and o["name"] == "stderr"]
print("code cells", n_code, "exec counts", executed)
print("errors", errs, "| stderr cells", stderr)
c = next(c for c in nb["cells"] if c["id"] == "cell-26")
for o in c["outputs"]:
    if o["output_type"] == "stream": print("".join(o["text"]))
EOF
cat results/timing.json
```

### [126] TOOL RESULT — Bash · 2026-10-26 10:09:56 UTC

```
{"stdout": "code cells 15 exec counts [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]\nerrors [] | stderr cells []\n=== key numbers: demo subset (full 200-run pool in brackets) ===\nt1: banned share 0.14 (0.15) | W4 alone 0.70 (0.75) | pooled event gate True (True) | landing {'dfs': 43, 'bfs': 7}\nt2: banned share 0.14 (0.13) | W4 alone 0.30 (0.30) | pooled event gate True (True) | landing {'dijkstra': 7, 'bf_spfa': 42, 'other': 1}\nt1|L27|k_pre: within-template AUC  DiM 1.00 (1.00) | SAE top-1 latent 0.29 (0.52) | SAE top-20 probe 0.48 (0.71) | shuffled-label DiM pooled AUC 0.49\nt2|L27|k_pre: within-template AUC  DiM 0.76 (0.76) | SAE top-1 latent 0.54 (0.51) | SAE top-20 probe 0.82 (0.77) | shuffled-label DiM pooled AUC 0.49\nverify_headlines (checks 1 + 5): 4 checks, 0 mismatches\nSAE transfer test (full artifact): 0/3 layers pass; dCE ratio L15 3.29, L20 1.95, L27 1.59  [rule: PASS(L) := dCE_inst(L) <= 1.5 x dCE_base(L) (spliced-in CE over response tokens)]\n\n{\n \"stages\": {\n  \"final\": {\n   \"runs\": [\n    {\n     \"seconds\": 0.0,\n     \"gpu\": false,\n     \"utc\": \"2026-10-26T10:09:39Z\",\n     \"ok\": true\n    }\n   ],\n   \"total_seconds\": 0.0\n  },\n  \"analyse_readout_i_replication\": {\n   \"runs\": [\n    {\n     \"seconds\": 3.6,\n     \"gpu\": false,\n     \"utc\": \"2026-10-26T10:09:43Z\",\n     \"ok\": true\n    }\n   ],\n   \"total_seconds\": 3.6\n  }\n },\n \"gpu_hours_total\": 0.0\n}", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [127] TOOL CALL — Read · 2026-10-26 10:09:56 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/figures/demo_summary.png
```

### [128] TOOL RESULT — Read · 2026-10-26 10:09:56 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [129] THINKING · 2026-10-26 10:10:12 UTC

```
The figure looks good overall, but I'll add a semi-opaque frame to the row-2 legend since it overlaps the bars, and I'll investigate the two separated bf_spfa clusters in the T2 geometry panel before noting a possible commit-token effect.
```

### [130] TOOL CALL — Bash · 2026-10-26 10:10:12 UTC

```
Check DiM score clusters against commit tokens:
python3 - <<'EOF'
import json
from collections import defaultdict
ex = json.load(open("mini_demo_data.json"))["datasets"][0]["examples"]
g = defaultdict(list)
for e in ex:
    s = e["metadata_readout_scores_k_pre"]
    if s:
        g[(e["metadata_task"], e["output"], e["metadata_evidence_term"])].append(round(s["raw_dim"]))
for k in sorted(g): print(k, sorted(g[k]))
EOF
```

### [131] TOOL RESULT — Bash · 2026-10-26 10:10:12 UTC

```
{"stdout": "('t1', 'bfs', 'deque') [50, 56, 62]\n('t1', 'bfs', 'queue') [-91, -87, -82, -56]\n('t1', 'dfs', 'DFS') [-148, -109, -109]\n('t1', 'dfs', 'Depth-first') [-152]\n('t1', 'dfs', 'Recurs') [-166, -162, -156, -154, -153, -150, -147, -145]\n('t1', 'dfs', 'depth-first') [-152, -143]\n('t1', 'dfs', 'dfs') [-130, -123, -123, -122, -121, -121, -120, -120, -118, -116, -116, -115, -113, -110, -110, -110, -110, -108]\n('t1', 'dfs', 'stack') [-102, -102, -99, -97, -97, -94, -93, -89, -80, -78]\n('t2', 'bf_spfa', 'Bellman') [81, 82, 82, 82, 83, 83, 83, 83]\n('t2', 'bf_spfa', 'deque') [-90, -87, -87, -87, -87, -87, -87, -85, -85, -85, -85, -84, -84, -84, -84, -84, -84, -84, -84, -84, -84, -83, -83, -83, -83, -83, -83, -81, -80, -80, -80, -80, -80, -64]\n('t2', 'dijkstra', 'deque') [-84, -83, -80, -80]\n('t2', 'dijkstra', 'heapq') [191, 208, 208]", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [132] THINKING · 2026-10-26 10:10:44 UTC

```
The DiM score at k_pre clusters by commit token rather than algorithm, confirming the artifact's caveat about capturing state at first lexicon match rather than at the decision point. I'll label each cluster by commit token in the geometry panels and note this in the write-up, starting by clearing outputs and re-syncing the Read state.
```

### [133] TOOL CALL — Bash · 2026-10-26 10:10:44 UTC

```
Clear notebook outputs before next edits:
/tmp/aii_nb_test_envs/art_3iv5G76C3yoX-2eaf8ea929eb/bin/jupyter nbconvert --clear-output --inplace code_demo.ipynb 2>&1 | tail -1
```

### [134] TOOL CALL — Read · 2026-10-26 10:10:44 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/code_demo.ipynb
```

### [135] TOOL RESULT — Bash · 2026-10-26 10:10:44 UTC

```
{"stdout": "[NbConvertApp] Writing 66220 bytes to code_demo.ipynb", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [136] TOOL RESULT — Read · 2026-10-26 10:10:44 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [137] THINKING · 2026-10-26 10:11:32 UTC

```
I need to correct my earlier claim that T2 is less exposed to the confound—its separation is actually also token-driven, carried by the `heapq` Dijkstra runs while `deque` runs show no distinction. I'll make three edits, starting with adding commit-token labels to the geometry panels and giving the row-2 legend a readable frame.
```

### [138] TOOL CALL — NotebookEdit · 2026-10-26 10:11:32 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/code_demo.ipynb', 'cell_id': 'cell-26', 'new_source': 'plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})  # as in figures.py\nC = ["#3b6ea8", "#d1495b", "#66a182", "#edae49", "#7d5ba6", "#8d6a4f", "#4f4f4f"]          # figures.py palette\nMORDER = ["sae_top1", "sae_top20_lr", "sae_code_dim", "raw_dim", "raw_lr", "neuron_top1", "neuron_top20_lr"]\nMNAME = {"sae_top1": "SAE top-1\\nlatent", "sae_top20_lr": "SAE top-20\\nlogistic", "sae_code_dim": "DiM on\\nSAE code",\n         "raw_dim": "DiM\\n(raw)", "raw_lr": "raw\\nlogistic", "neuron_top1": "top-1\\nneuron",\n         "neuron_top20_lr": "top-20\\nneurons"}\n\n\ndef _f2(v):\n    return "n/a" if v is None or (isinstance(v, float) and not np.isfinite(v)) else f"{v:.2f}"\n\n\ndef _sc(r):\n    return SCORES[(r["task"], r["template"], r["sample_id"])]\n\n\ndef _yerr(v, lo, hi):\n    # error-bar lengths, clamped at 0: a Wilson bound at a share of 0 or 1 can sit ~1e-17 on the wrong side,\n    # and a bootstrap percentile CI need not contain the point estimate (matplotlib rejects negative lengths)\n    return [[max(v - lo, 0.0)], [max(hi - v, 0.0)]]\n\n\nfig, axes = plt.subplots(3, 2, figsize=(11, 13))\nfor col, t in enumerate(TASKS):\n    # row 1: banned share per template (Wilson 95% CI)\n    ax = axes[0, col]\n    ws = TEMPLATE_IDS + ["pooled"]\n    for j, w in enumerate(ws):\n        p = fresh["per_task"][t][w]\n        v, (lo, hi) = p["banned_share"], p["banned_share_wilson"]\n        ax.bar(j, v, 0.6, color=C[6] if w == "pooled" else C[1], alpha=0.85)\n        ax.errorbar(j, v, yerr=_yerr(v, lo, hi), fmt="none", ecolor="k", capsize=3, lw=0.8)\n    ax.scatter(range(len(ws)), [REF["fresh_pool_summary"][t][w]["banned_share"] for w in ws], marker="D", s=22,\n               color="k", zorder=3, label="full 200-run pool")\n    ax.set_xticks(range(len(ws)), ws)\n    ax.set_ylim(0, 1.05)\n    ax.set_ylabel(f"share of runs that still write {BANNED[t]}")\n    ax.set_title(f"{t}: runs that ignore the {BANNED[t]} ban, per template (bars: demo, {N_PER_CELL} runs each)",\n                 fontsize=9)\n    ax.legend(frameon=False, fontsize=7, loc="upper left")\n\n    # row 2: within-template AUC of every exp3-fitted readout (run-bootstrap 95% CI)\n    ax = axes[1, col]\n    key = f"{t}|L{READOUT_LAYER}|k_pre"\n    tr = rep_i["configs"].get(key, {}).get("transfer_from_exp3", {})\n    ref = REF["readout_i_replication"][key]["transfer_from_exp3"]\n    for j, m in enumerate(MORDER):\n        r = tr.get(m, {})\n        a = r.get("auc_within_template")\n        if a is not None and np.isfinite(a):\n            ax.bar(j, a, 0.6, color=C[j % len(C)])\n            ci = r.get("within_ci_runs") or [None, None]\n            if ci[0] is not None:\n                ax.errorbar(j, a, yerr=_yerr(a, ci[0], ci[1]), fmt="none", ecolor="k", capsize=3, lw=0.8)\n    ax.scatter(range(len(MORDER)), [ref[m]["auc_within_template"] for m in MORDER], marker="D", s=22, color="k",\n               zorder=3, label="full 200-run pool")\n    ax.axhline(0.5, color="grey", lw=0.6, ls="--")\n    pl = VER["checks"].get(f"placebo_replication_shuffled_{key}", {}).get("placebo_mean_auc")\n    if pl is not None:\n        ax.axhline(pl, color=C[3], lw=1.2, ls=":", label=f"DiM, shuffled labels (pooled, {N_PLACEBO}x): {pl:.2f}")\n    ax.set_xticks(range(len(MORDER)), [MNAME[m] for m in MORDER], fontsize=7)\n    ax.set_ylim(0, 1.05)\n    ax.set_ylabel("within-template AUC")\n    n_pairs = next(iter(tr.values()), {}).get("n_within_pairs", 0)\n    ax.set_title(f"{t}: exp3-fitted readouts at L{READOUT_LAYER} k_pre ({n_pairs} within-template pairs)", fontsize=9)\n    ax.legend(frameon=True, framealpha=0.9, edgecolor="none", fontsize=7, loc="lower right")\n\n    # row 3: per-run readout geometry (L27 k_pre state projected on two exp3-fitted directions)\n    ax = axes[2, col]\n    for lab, colr in ((SUBSTITUTE[t], C[0]), (BANNED[t], C[1])):\n        for w, mk in zip(TEMPLATE_IDS, "osD^v"):\n            pts = [(_sc(r)["raw_dim"], _sc(r)["sae_top20_lr"]) for r in C1_ROWS\n                   if r["task"] == t and r["label"] == lab and r["template"] == w and _sc(r)]\n            if pts:\n                ax.scatter(*zip(*pts), color=colr, marker=mk, s=32, alpha=0.8, edgecolor="white", lw=0.4,\n                           label=f"{lab} | {w}")\n    # text: the commit token (first algorithm-identifying lexicon match, i.e. the token right after k_pre) of each\n    # (algorithm, token) cluster, with its run count, at the cluster median\n    groups = defaultdict(list)\n    for r in C1_ROWS:\n        if r["task"] == t and r["label"] in (BANNED[t], SUBSTITUTE[t]) and _sc(r):\n            groups[(r["label"], (r["evidence_term"] or "none").lower())].append((_sc(r)["raw_dim"],\n                                                                                 _sc(r)["sae_top20_lr"]))\n    for (lab, term), pts in groups.items():\n        xs, ys = zip(*pts)\n        ax.annotate(f"{term} ({len(pts)})", (float(np.median(xs)), float(np.median(ys))), textcoords="offset points",\n                    xytext=(0, -12 if lab == BANNED[t] else 7), ha="center", fontsize=7, fontweight="bold",\n                    color=C[1] if lab == BANNED[t] else C[0])\n    ax.axvline(0, color="grey", lw=0.6, ls="--")\n    ax.axhline(0, color="grey", lw=0.6, ls="--")\n    ax.set_xlabel("DiM projection of the raw residual (exp3-fitted; > 0 = banned side)")\n    ax.set_ylabel("SAE top-20-latent logistic score (> 0 = banned)")\n    ax.set_title(f"{t}: one point per run (colour = algorithm, marker = template, text = commit token)", fontsize=9)\n    ax.legend(frameon=False, fontsize=6, ncol=2)\nfig.tight_layout()\nfig.savefig(FIGS / "demo_summary.png", dpi=150)\nplt.show()\n\nprint("=== key numbers: demo subset (full 200-run pool in brackets) ===")\nfor t in TASKS:\n    p, f = fresh["per_task"][t]["pooled"], REF["fresh_pool_summary"][t]["pooled"]\n    w4, f4 = fresh["per_task"][t]["W4"], REF["fresh_pool_summary"][t]["W4"]\n    print(f"{t}: banned share {_f2(p[\'banned_share\'])} ({_f2(f[\'banned_share\'])}) | W4 alone {_f2(w4[\'banned_share\'])} "\n          f"({_f2(f4[\'banned_share\'])}) | pooled event gate {p[\'event_gate_pass\']} ({f[\'event_gate_pass\']}) | "\n          f"landing {p[\'landing\']}")\nfor t in TASKS:\n    key = f"{t}|L{READOUT_LAYER}|k_pre"\n    tr = rep_i["configs"].get(key, {}).get("transfer_from_exp3", {})\n    ref = REF["readout_i_replication"][key]["transfer_from_exp3"]\n    pl = VER["checks"].get(f"placebo_replication_shuffled_{key}", {}).get("placebo_mean_auc")\n    print(f"{key}: within-template AUC  DiM {_f2(tr.get(\'raw_dim\', {}).get(\'auc_within_template\'))} "\n          f"({_f2(ref[\'raw_dim\'][\'auc_within_template\'])}) | SAE top-1 latent "\n          f"{_f2(tr.get(\'sae_top1\', {}).get(\'auc_within_template\'))} ({_f2(ref[\'sae_top1\'][\'auc_within_template\'])}) | "\n          f"SAE top-20 probe {_f2(tr.get(\'sae_top20_lr\', {}).get(\'auc_within_template\'))} "\n          f"({_f2(ref[\'sae_top20_lr\'][\'auc_within_template\'])}) | shuffled-label DiM pooled AUC {_f2(pl)}")\nprint(f"verify_headlines (checks 1 + 5): {VER[\'n_checks\']} checks, {VER[\'n_mismatches\']} mismatches")\n_tt = REF["sae_transfer_test"]\nprint(f"SAE transfer test (full artifact): {_tt[\'n_pass\']}/3 layers pass; dCE ratio "\n      + ", ".join(f"L{L} {r:.2f}" for L, r in _tt["ratio_by_layer"].items()) + f"  [rule: {_tt[\'rule\']}]")'}
```

### [139] TOOL RESULT — NotebookEdit · 2026-10-26 10:11:32 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [140] ASSISTANT · 2026-10-26 10:11:38 UTC

```
Second edit, the section 7 markdown, so it describes the new labels:
```

### [141] TOOL CALL — NotebookEdit · 2026-10-26 10:11:38 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/code_demo.ipynb', 'cell_id': 'cell-25', 'cell_type': 'markdown', 'new_source': '## 7. Results and visualisation\n\nThe figure has three rows, with one column per task. In every panel the black diamonds are the full 200-run pool.\n- **Row 1**: the share of runs that still write the banned algorithm, per ban template, with Wilson 95% CIs.\n- **Row 2**: the within-template AUC of every exp3-fitted readout at L27 `k_pre`, with run-bootstrap 95% CIs. The\n  dotted line is the DiM AUC under shuffled labels.\n- **Row 3**: the readout geometry, with one point per run. Each run\'s layer-27 residual state at `k_pre` is projected\n  onto two exp3-fitted directions:\n  - x-axis: the DiM direction on the raw residual, as the signed distance from the exp3 class midpoint;\n  - y-axis: the SAE top-20-latent logistic probe, as log-odds.\n\n  Positive values are the readout\'s "banned" side. Colour is the algorithm the run wrote, and marker is the template.\n  Each text label gives a cluster\'s **commit token** and its run count. The commit token is the word right after\n  `k_pre`.'}
```

### [142] TOOL RESULT — NotebookEdit · 2026-10-26 10:11:38 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [143] ASSISTANT · 2026-10-26 10:11:50 UTC

```
Third edit, the closing notes, with the corrected `k_pre` interpretation backed by the cluster positions:
```

### [144] TOOL CALL — NotebookEdit · 2026-10-26 10:11:50 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/code_demo.ipynb', 'cell_id': 'cell-27', 'cell_type': 'markdown', 'new_source': '### Reading the results\n\n- **A ban mostly substitutes; it does not subtract, and it does not make the model inventive.** Under four of the five\n  templates, T1 never produces BFS. Instead the model writes DFS, the next most common grid-path algorithm. Under\n  W4, *"BFS is not allowed here."*, it still writes BFS most of the time. T2 shows the same pattern, with\n  Bellman-Ford/SPFA standing in for Dijkstra. On T2 the ban fails most often under W3 and W4. Across the pool almost\n  nothing lands outside the banned algorithm and its one natural substitute; the only exception is a single `other`\n  run. So the *wording* of a ban decides how often it works. What replaces the banned algorithm is the runner-up, not\n  a novel solution.\n- **The cheap baseline wins.** The class-mean-difference (DiM) direction was fitted on exp3 states. On the fresh pool\n  it separates banned from substitute runs *within the same template*:\n  - **T1**: perfectly. This rests on W4\'s pairs alone, the only template with both classes.\n  - **T2**: AUC about 0.76 in both the demo and the full pool, but with a wide CI.\n\n  The single best SAE latent from exp3 does not transfer. The top-20-latent probe roughly ties DiM on T2, with\n  overlapping CIs, but it falls to chance inside W4 on T1. Every SAE readout here is also out-of-distribution, because\n  the base→instruct transfer test failed. Shuffled labels give about 0.5.\n- **What `k_pre` measures: the geometry panels show it directly.** `k_pre` is the state just before the first\n  algorithm-identifying token. The runs cluster by *that token* much more than by the algorithm they end up writing.\n  - **T2.** Dijkstra runs that commit at `heapq` sit far out on the banned side. Dijkstra runs that commit at `deque`\n    sit inside the Bellman-Ford/SPFA `deque` cluster. Bellman-Ford runs whose first match is the word `Bellman` also\n    sit on the banned side. T2\'s AUC of about 0.76 is therefore mostly a `heapq`-versus-`deque` contrast.\n  - **T1.** BFS runs that commit at `deque` are far from every DFS run. BFS runs that commit at `queue` sit next to\n    the DFS `stack` runs.\n\n  So these readouts largely read *which word comes next*, not an earlier algorithm decision. The artifact flags this\n  itself: the readout is the state at the first lexicon match, not at the decision. That is why it reports all\n  readouts as descriptive, not causal.\n- **Demo vs full run.** The demo uses half of the pool, 10 runs per template. Its CIs are therefore wider, and a few\n  per-template shares differ from the full pool. Each number sits next to its full-pool value, shown as black diamonds\n  in the figure and as bracketed values in the printout.\n  - `N_PER_CELL = 10` already uses the whole demo file.\n  - All 200 runs, every layer and position, and the GPU stages need the original pipeline:\n    `uv run method.py --stage vllm1 | label | hf | analyse | final | verify`.'}
```

### [145] TOOL RESULT — NotebookEdit · 2026-10-26 10:11:50 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [146] ASSISTANT · 2026-10-26 10:12:02 UTC

```
All three edits are in. Final clean-venv re-run (removing stale outputs first, so `results/`, `logs/` and `figures/` reflect only this run):
```

### [147] TOOL CALL — Bash · 2026-10-26 10:12:02 UTC

```
Final re-run after edits and error check:
rm -f results/*.json logs/*.log figures/*.png && T0=$(date +%s) && UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_3iv5G76C3yoX-2eaf8ea929eb && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_3iv5G76C3yoX-2eaf8ea929eb/bin/python jupyter ipykernel && T1=$(date +%s) && echo "venv setup: $((T1-T0)) s" && /tmp/aii_nb_test_envs/art_3iv5G76C3yoX-2eaf8ea929eb/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | grep -v "running over TCP"; RC=${PIPESTATUS[0]}; T2=$(date +%s); echo "nbconvert exit=$RC, notebook runtime: $((T2-T1)) s"; python3 - <<'EOF'
import json
nb = json.load(open("code_demo.ipynb"))
errs = [(c["id"], o["ename"], o["evalue"]) for c in nb["cells"] if c["cell_type"] == "code" for o in c["outputs"] if o["output_type"] == "error"]
stderr = [(c["id"], "".join(o["text"])[:300]) for c in nb["cells"] if c["cell_type"] == "code" for o in c["outputs"] if o["output_type"] == "stream" and o["name"] == "stderr"]
print("exec counts", [c.get("execution_count") for c in nb["cells"] if c["cell_type"] == "code"])
print("errors", errs, "| stderr", stderr)
EOF
ls -la results logs figures | grep -v "^total\|^d"
```

### [148] TOOL RESULT — Bash · 2026-10-26 10:12:28 UTC

```
{"stdout": "venv setup: 1 s\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[NbConvertApp] Writing 264670 bytes to code_demo.ipynb\nnbconvert exit=0, notebook runtime: 24 s\nexec counts [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]\nerrors [] | stderr []\nfigures:\n-rw-rw-rw- 1 aii-agent aii-agent  208275 Oct 26 10:12 demo_summary.png\n\nlogs:\n-rw-rw-rw- 1 aii-agent aii-agent     806 Oct 26 10:12 stage_demo.log\n\nresults:\n-rw-rw-rw- 1 aii-agent aii-agent    4921 Oct 26 10:12 fresh_pool_summary.json\n-rw-rw-rw- 1 aii-agent aii-agent   16484 Oct 26 10:12 readout_i_replication.json\n-rw-rw-rw- 1 aii-agent aii-agent     397 Oct 26 10:12 timing.json\n-rw-rw-rw- 1 aii-agent aii-agent     731 Oct 26 10:12 verify_headlines.json", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [149] ASSISTANT · 2026-10-26 10:12:32 UTC

```
The final run passed: exit 0, 24 s, all 15 code cells executed, no errors and no stderr. Checking the updated figure:
```

### [150] TOOL CALL — Read · 2026-10-26 10:12:32 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/figures/demo_summary.png
```

### [151] TOOL RESULT — Read · 2026-10-26 10:12:32 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [152] THINKING · 2026-10-26 10:12:52 UTC

```
The figure is working well and shows the clustering clearly, but I spotted two cosmetic issues: overlapping T1 labels and a clipped title. I'll stagger the label offsets, wrap the title, then re-sync and re-run.
```

### [153] TOOL CALL — Bash · 2026-10-26 10:12:52 UTC

```
Clear outputs to re-sync notebook state:
/tmp/aii_nb_test_envs/art_3iv5G76C3yoX-2eaf8ea929eb/bin/jupyter nbconvert --clear-output --inplace code_demo.ipynb 2>&1 | tail -1
```

### [154] TOOL CALL — Read · 2026-10-26 10:12:52 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/code_demo.ipynb
```

### [155] TOOL RESULT — Bash · 2026-10-26 10:12:52 UTC

```
{"stdout": "[NbConvertApp] Writing 67944 bytes to code_demo.ipynb", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [156] TOOL RESULT — Read [ERROR] · 2026-10-26 10:12:52 UTC

```
Error: File content (25542 tokens) exceeds maximum allowed tokens (25000). Use offset and limit parameters to read specific portions of the file, or search for specific content instead of reading the whole file.
```

### [157] THINKING · 2026-10-26 10:13:26 UTC

```
The read failed since the notebook exceeded the 25k-token limit, so I'll attempt the edit directly, falling back to a large-allowed read if needed.
```

### [158] TOOL CALL — NotebookEdit · 2026-10-26 10:13:26 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/code_demo.ipynb', 'cell_id': 'cell-26', 'new_source': 'plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})  # as in figures.py\nC = ["#3b6ea8", "#d1495b", "#66a182", "#edae49", "#7d5ba6", "#8d6a4f", "#4f4f4f"]          # figures.py palette\nMORDER = ["sae_top1", "sae_top20_lr", "sae_code_dim", "raw_dim", "raw_lr", "neuron_top1", "neuron_top20_lr"]\nMNAME = {"sae_top1": "SAE top-1\\nlatent", "sae_top20_lr": "SAE top-20\\nlogistic", "sae_code_dim": "DiM on\\nSAE code",\n         "raw_dim": "DiM\\n(raw)", "raw_lr": "raw\\nlogistic", "neuron_top1": "top-1\\nneuron",\n         "neuron_top20_lr": "top-20\\nneurons"}\n\n\ndef _f2(v):\n    return "n/a" if v is None or (isinstance(v, float) and not np.isfinite(v)) else f"{v:.2f}"\n\n\ndef _sc(r):\n    return SCORES[(r["task"], r["template"], r["sample_id"])]\n\n\ndef _yerr(v, lo, hi):\n    # error-bar lengths, clamped at 0: a Wilson bound at a share of 0 or 1 can sit ~1e-17 on the wrong side,\n    # and a bootstrap percentile CI need not contain the point estimate (matplotlib rejects negative lengths)\n    return [[max(v - lo, 0.0)], [max(hi - v, 0.0)]]\n\n\nfig, axes = plt.subplots(3, 2, figsize=(11, 13))\nfor col, t in enumerate(TASKS):\n    # row 1: banned share per template (Wilson 95% CI)\n    ax = axes[0, col]\n    ws = TEMPLATE_IDS + ["pooled"]\n    for j, w in enumerate(ws):\n        p = fresh["per_task"][t][w]\n        v, (lo, hi) = p["banned_share"], p["banned_share_wilson"]\n        ax.bar(j, v, 0.6, color=C[6] if w == "pooled" else C[1], alpha=0.85)\n        ax.errorbar(j, v, yerr=_yerr(v, lo, hi), fmt="none", ecolor="k", capsize=3, lw=0.8)\n    ax.scatter(range(len(ws)), [REF["fresh_pool_summary"][t][w]["banned_share"] for w in ws], marker="D", s=22,\n               color="k", zorder=3, label="full 200-run pool")\n    ax.set_xticks(range(len(ws)), ws)\n    ax.set_ylim(0, 1.05)\n    ax.set_ylabel(f"share of runs that still write {BANNED[t]}")\n    ax.set_title(f"{t}: runs that ignore the {BANNED[t]} ban, per template\\n(bars: demo, {N_PER_CELL} runs each)",\n                 fontsize=9)\n    ax.legend(frameon=False, fontsize=7, loc="upper left")\n\n    # row 2: within-template AUC of every exp3-fitted readout (run-bootstrap 95% CI)\n    ax = axes[1, col]\n    key = f"{t}|L{READOUT_LAYER}|k_pre"\n    tr = rep_i["configs"].get(key, {}).get("transfer_from_exp3", {})\n    ref = REF["readout_i_replication"][key]["transfer_from_exp3"]\n    for j, m in enumerate(MORDER):\n        r = tr.get(m, {})\n        a = r.get("auc_within_template")\n        if a is not None and np.isfinite(a):\n            ax.bar(j, a, 0.6, color=C[j % len(C)])\n            ci = r.get("within_ci_runs") or [None, None]\n            if ci[0] is not None:\n                ax.errorbar(j, a, yerr=_yerr(a, ci[0], ci[1]), fmt="none", ecolor="k", capsize=3, lw=0.8)\n    ax.scatter(range(len(MORDER)), [ref[m]["auc_within_template"] for m in MORDER], marker="D", s=22, color="k",\n               zorder=3, label="full 200-run pool")\n    ax.axhline(0.5, color="grey", lw=0.6, ls="--")\n    pl = VER["checks"].get(f"placebo_replication_shuffled_{key}", {}).get("placebo_mean_auc")\n    if pl is not None:\n        ax.axhline(pl, color=C[3], lw=1.2, ls=":", label=f"DiM, shuffled labels (pooled, {N_PLACEBO}x): {pl:.2f}")\n    ax.set_xticks(range(len(MORDER)), [MNAME[m] for m in MORDER], fontsize=7)\n    ax.set_ylim(0, 1.05)\n    ax.set_ylabel("within-template AUC")\n    n_pairs = next(iter(tr.values()), {}).get("n_within_pairs", 0)\n    ax.set_title(f"{t}: exp3-fitted readouts at L{READOUT_LAYER} k_pre\\n({n_pairs} within-template pairs)", fontsize=9)\n    ax.legend(frameon=True, framealpha=0.9, edgecolor="none", fontsize=7, loc="lower right")\n\n    # row 3: per-run readout geometry (L27 k_pre state projected on two exp3-fitted directions)\n    ax = axes[2, col]\n    for lab, colr in ((SUBSTITUTE[t], C[0]), (BANNED[t], C[1])):\n        for w, mk in zip(TEMPLATE_IDS, "osD^v"):\n            pts = [(_sc(r)["raw_dim"], _sc(r)["sae_top20_lr"]) for r in C1_ROWS\n                   if r["task"] == t and r["label"] == lab and r["template"] == w and _sc(r)]\n            if pts:\n                ax.scatter(*zip(*pts), color=colr, marker=mk, s=32, alpha=0.8, edgecolor="white", lw=0.4,\n                           label=f"{lab} | {w}")\n    # text: the commit token (first algorithm-identifying lexicon match, i.e. the token right after k_pre) of each\n    # (algorithm, token) cluster, with its run count, at the cluster median; offsets alternate so labels do not overlap\n    groups = defaultdict(list)\n    for r in C1_ROWS:\n        if r["task"] == t and r["label"] in (BANNED[t], SUBSTITUTE[t]) and _sc(r):\n            groups[(r["label"], (r["evidence_term"] or "none").lower())].append((_sc(r)["raw_dim"],\n                                                                                 _sc(r)["sae_top20_lr"]))\n    for k, ((lab, term), pts) in enumerate(sorted(groups.items(), key=lambda kv: np.median([p[0] for p in kv[1]]))):\n        xs, ys = zip(*pts)\n        dy = -(12 + 10 * (k % 2)) if lab == BANNED[t] else 7 + 10 * (k % 2)\n        ax.annotate(f"{term} ({len(pts)})", (float(np.median(xs)), float(np.median(ys))), textcoords="offset points",\n                    xytext=(0, dy), ha="center", fontsize=7, fontweight="bold",\n                    color=C[1] if lab == BANNED[t] else C[0])\n    ax.axvline(0, color="grey", lw=0.6, ls="--")\n    ax.axhline(0, color="grey", lw=0.6, ls="--")\n    ax.set_xlabel("DiM projection of the raw residual (exp3-fitted; > 0 = banned side)")\n    ax.set_ylabel("SAE top-20-latent logistic score (> 0 = banned)")\n    ax.set_title(f"{t}: one point per run at L{READOUT_LAYER} k_pre\\n(colour = algorithm, marker = template, "\n                 f"text = commit token)", fontsize=9)\n    ax.legend(frameon=False, fontsize=6, ncol=2)\nfig.tight_layout()\nfig.savefig(FIGS / "demo_summary.png", dpi=150)\nplt.show()\n\nprint("=== key numbers: demo subset (full 200-run pool in brackets) ===")\nfor t in TASKS:\n    p, f = fresh["per_task"][t]["pooled"], REF["fresh_pool_summary"][t]["pooled"]\n    w4, f4 = fresh["per_task"][t]["W4"], REF["fresh_pool_summary"][t]["W4"]\n    print(f"{t}: banned share {_f2(p[\'banned_share\'])} ({_f2(f[\'banned_share\'])}) | W4 alone {_f2(w4[\'banned_share\'])} "\n          f"({_f2(f4[\'banned_share\'])}) | pooled event gate {p[\'event_gate_pass\']} ({f[\'event_gate_pass\']}) | "\n          f"landing {p[\'landing\']}")\nfor t in TASKS:\n    key = f"{t}|L{READOUT_LAYER}|k_pre"\n    tr = rep_i["configs"].get(key, {}).get("transfer_from_exp3", {})\n    ref = REF["readout_i_replication"][key]["transfer_from_exp3"]\n    pl = VER["checks"].get(f"placebo_replication_shuffled_{key}", {}).get("placebo_mean_auc")\n    print(f"{key}: within-template AUC  DiM {_f2(tr.get(\'raw_dim\', {}).get(\'auc_within_template\'))} "\n          f"({_f2(ref[\'raw_dim\'][\'auc_within_template\'])}) | SAE top-1 latent "\n          f"{_f2(tr.get(\'sae_top1\', {}).get(\'auc_within_template\'))} ({_f2(ref[\'sae_top1\'][\'auc_within_template\'])}) | "\n          f"SAE top-20 probe {_f2(tr.get(\'sae_top20_lr\', {}).get(\'auc_within_template\'))} "\n          f"({_f2(ref[\'sae_top20_lr\'][\'auc_within_template\'])}) | shuffled-label DiM pooled AUC {_f2(pl)}")\nprint(f"verify_headlines (checks 1 + 5): {VER[\'n_checks\']} checks, {VER[\'n_mismatches\']} mismatches")\n_tt = REF["sae_transfer_test"]\nprint(f"SAE transfer test (full artifact): {_tt[\'n_pass\']}/3 layers pass; dCE ratio "\n      + ", ".join(f"L{L} {r:.2f}" for L, r in _tt["ratio_by_layer"].items()) + f"  [rule: {_tt[\'rule\']}]")'}
```

### [159] TOOL RESULT — NotebookEdit [ERROR] · 2026-10-26 10:13:26 UTC

```
Error: File has been modified since read, either by the user or by a linter. Read it again before attempting to write it.
```

### [160] ASSISTANT · 2026-10-26 10:13:28 UTC

```
The tool wants a fresh Read, so I'll read the whole file with `allow_large` (outputs are already cleared, about 25k tokens):
```

### [161] TOOL CALL — Read · 2026-10-26 10:13:28 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/code_demo.ipynb
```

### [162] TOOL RESULT — Read [ERROR] · 2026-10-26 10:13:28 UTC

```
Error: File content (25542 tokens) exceeds maximum allowed tokens (25000). Use offset and limit parameters to read specific portions of the file, or search for specific content instead of reading the whole file.
```

### [163] ASSISTANT · 2026-10-26 10:13:34 UTC

```
`allow_large` isn't honoured for notebooks, so I'll try reading a cell range with `offset`/`limit`:
```

### [164] TOOL CALL — Read · 2026-10-26 10:13:34 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/code_demo.ipynb
```

### [165] TOOL RESULT — Read [ERROR] · 2026-10-26 10:13:34 UTC

```
Error: File content (25542 tokens) exceeds maximum allowed tokens (25000). Use offset and limit parameters to read specific portions of the file, or search for specific content instead of reading the whole file.
```

### [166] THINKING · 2026-10-26 10:14:16 UTC

```
The notebook is too large for NotebookEdit, so I'll make this last cosmetic change by splicing in new source for cell-26 via a temporary file and then deleting it.
```

### [167] TOOL CALL — Write · 2026-10-26 10:14:16 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/tools/_cell26.py

plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})  # as in figures.py
C = ["#3b6ea8", "#d1495b", "#66a182", "#edae49", "#7d5ba6", "#8d6a4f", "#4f4f4f"]          # figures.py palette
MORDER = ["sae_top1", "sae_top20_lr", "sae_code_dim", "raw_dim", "raw_lr", "neuron_top1", "neuron_top20_lr"]
MNAME = {"sae_top1": "SAE top-1\nlatent", "sae_top20_lr": "SAE top-20\nlogistic", "sae_code_dim": "DiM on\nSAE code",
         "raw_dim": "DiM\n(raw)", "raw_lr": "raw\nlogistic", "neuron_top1": "top-1\nneuron",
         "neuron_top20_lr": "top-20\nneurons"}


def _f2(v):
    return "n/a" if v is None or (isinstance(v, float) and not np.isfinite(v)) else f"{v:.2f}"


def _sc(r):
    return SCORES[(r["task"], r["template"], r["sample_id"])]


def _yerr(v, lo, hi):
    # error-bar lengths, clamped at 0: a Wilson bound at a share of 0 or 1 can sit ~1e-17 on the wrong side,
    # and a bootstrap percentile CI need not contain the point estimate (matplotlib rejects negative lengths)
    return [[max(v - lo, 0.0)], [max(hi - v, 0.0)]]


fig, axes = plt.subplots(3, 2, figsize=(11, 13))
for col, t in enumerate(TASKS):
    # row 1: banned share per template (Wilson 95% CI)
    ax = axes[0, col]
    ws = TEMPLATE_IDS + ["pooled"]
    for j, w in enumerate(ws):
        p = fresh["per_task"][t][w]
        v, (lo, hi) = p["banned_share"], p["banned_share_wilson"]
        ax.bar(j, v, 0.6, color=C[6] if w == "pooled" else C[1], alpha=0.85)
        ax.errorbar(j, v, yerr=_yerr(v, lo, hi), fmt="none", ecolor="k", capsize=3, lw=0.8)
    ax.scatter(range(len(ws)), [REF["fresh_pool_summary"][t][w]["banned_share"] for w in ws], marker="D", s=22,
               color="k", zorder=3, label="full 200-run pool")
    ax.set_xticks(range(len(ws)), ws)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel(f"share of runs that still write {BANNED[t]}")
    ax.set_title(f"{t}: runs that ignore the {BANNED[t]} ban, per template\n(bars: demo, {N_PER_CELL} runs each)",
                 fontsize=9)
    ax.legend(frameon=False, fontsize=7, loc="upper left")

    # row 2: within-template AUC of every exp3-fitted readout (run-bootstrap 95% CI)
    ax = axes[1, col]
    key = f"{t}|L{READOUT_LAYER}|k_pre"
    tr = rep_i["configs"].get(key, {}).get("transfer_from_exp3", {})
    ref = REF["readout_i_replication"][key]["transfer_from_exp3"]
    for j, m in enumerate(MORDER):
        r = tr.get(m, {})
        a = r.get("auc_within_template")
        if a is not None and np.isfinite(a):
            ax.bar(j, a, 0.6, color=C[j % len(C)])
            ci = r.get("within_ci_runs") or [None, None]
            if ci[0] is not None:
                ax.errorbar(j, a, yerr=_yerr(a, ci[0], ci[1]), fmt="none", ecolor="k", capsize=3, lw=0.8)
    ax.scatter(range(len(MORDER)), [ref[m]["auc_within_template"] for m in MORDER], marker="D", s=22, color="k",
               zorder=3, label="full 200-run pool")
    ax.axhline(0.5, color="grey", lw=0.6, ls="--")
    pl = VER["checks"].get(f"placebo_replication_shuffled_{key}", {}).get("placebo_mean_auc")
    if pl is not None:
        ax.axhline(pl, color=C[3], lw=1.2, ls=":", label=f"DiM, shuffled labels (pooled, {N_PLACEBO}x): {pl:.2f}")
    ax.set_xticks(range(len(MORDER)), [MNAME[m] for m in MORDER], fontsize=7)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("within-template AUC")
    n_pairs = next(iter(tr.values()), {}).get("n_within_pairs", 0)
    ax.set_title(f"{t}: exp3-fitted readouts at L{READOUT_LAYER} k_pre\n({n_pairs} within-template pairs)", fontsize=9)
    ax.legend(frameon=True, framealpha=0.9, edgecolor="none", fontsize=7, loc="lower right")

    # row 3: per-run readout geometry (L27 k_pre state projected on two exp3-fitted directions)
    ax = axes[2, col]
    for lab, colr in ((SUBSTITUTE[t], C[0]), (BANNED[t], C[1])):
        for w, mk in zip(TEMPLATE_IDS, "osD^v"):
            pts = [(_sc(r)["raw_dim"], _sc(r)["sae_top20_lr"]) for r in C1_ROWS
                   if r["task"] == t and r["label"] == lab and r["template"] == w and _sc(r)]
            if pts:
                ax.scatter(*zip(*pts), color=colr, marker=mk, s=32, alpha=0.8, edgecolor="white", lw=0.4,
                           label=f"{lab} | {w}")
    # text: the commit token (first algorithm-identifying lexicon match, i.e. the token right after k_pre) of each
    # (algorithm, token) cluster, with its run count, at the cluster median; offsets alternate so labels do not overlap
    groups = defaultdict(list)
    for r in C1_ROWS:
        if r["task"] == t and r["label"] in (BANNED[t], SUBSTITUTE[t]) and _sc(r):
            groups[(r["label"], (r["evidence_term"] or "none").lower())].append((_sc(r)["raw_dim"],
                                                                                 _sc(r)["sae_top20_lr"]))
    for k, ((lab, term), pts) in enumerate(sorted(groups.items(), key=lambda kv: np.median([p[0] for p in kv[1]]))):
        xs, ys = zip(*pts)
        dy = -(12 + 10 * (k % 2)) if lab == BANNED[t] else 7 + 10 * (k % 2)
        ax.annotate(f"{term} ({len(pts)})", (float(np.median(xs)), float(np.median(ys))), textcoords="offset points",
                    xytext=(0, dy), ha="center", fontsize=7, fontweight="bold",
                    color=C[1] if lab == BANNED[t] else C[0])
    ax.axvline(0, color="grey", lw=0.6, ls="--")
    ax.axhline(0, color="grey", lw=0.6, ls="--")
    ax.set_xlabel("DiM projection of the raw residual (exp3-fitted; > 0 = banned side)")
    ax.set_ylabel("SAE top-20-latent logistic score (> 0 = banned)")
    ax.set_title(f"{t}: one point per run at L{READOUT_LAYER} k_pre\n(colour = algorithm, marker = template, "
                 f"text = commit token)", fontsize=9)
    ax.legend(frameon=False, fontsize=6, ncol=2)
fig.tight_layout()
fig.savefig(FIGS / "demo_summary.png", dpi=150)
plt.show()

print("=== key numbers: demo subset (full 200-run pool in brackets) ===")
for t in TASKS:
    p, f = fresh["per_task"][t]["pooled"], REF["fresh_pool_summary"][t]["pooled"]
    w4, f4 = fresh["per_task"][t]["W4"], REF["fresh_pool_summary"][t]["W4"]
    print(f"{t}: banned share {_f2(p['banned_share'])} ({_f2(f['banned_share'])}) | W4 alone {_f2(w4['banned_share'])} "
          f"({_f2(f4['banned_share'])}) | pooled event gate {p['event_gate_pass']} ({f['event_gate_pass']}) | "
          f"landing {p['landing']}")
for t in TASKS:
    key = f"{t}|L{READOUT_LAYER}|k_pre"
    tr = rep_i["configs"].get(key, {}).get("transfer_from_exp3", {})
    ref = REF["readout_i_replication"][key]["transfer_from_exp3"]
    pl = VER["checks"].get(f"placebo_replication_shuffled_{key}", {}).get("placebo_mean_auc")
    print(f"{key}: within-template AUC  DiM {_f2(tr.get('raw_dim', {}).get('auc_within_template'))} "
          f"({_f2(ref['raw_dim']['auc_within_template'])}) | SAE top-1 latent "
          f"{_f2(tr.get('sae_top1', {}).get('auc_within_template'))} ({_f2(ref['sae_top1']['auc_within_template'])}) | "
          f"SAE top-20 probe {_f2(tr.get('sae_top20_lr', {}).get('auc_within_template'))} "
          f"({_f2(ref['sae_top20_lr']['auc_within_template'])}) | shuffled-label DiM pooled AUC {_f2(pl)}")
print(f"verify_headlines (checks 1 + 5): {VER['n_checks']} checks, {VER['n_mismatches']} mismatches")
_tt = REF["sae_transfer_test"]
print(f"SAE transfer test (full artifact): {_tt['n_pass']}/3 layers pass; dCE ratio "
      + ", ".join(f"L{L} {r:.2f}" for L, r in _tt["ratio_by_layer"].items()) + f"  [rule: {_tt['rule']}]")
```

### [168] TOOL RESULT — Write · 2026-10-26 10:14:16 UTC

```
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/tools/_cell26.py", "content": "plt.rcParams.update({\"font.size\": 9, \"axes.spines.top\": False, \"axes.spines.right\": False})  # as in figures.py\nC = [\"#3b6ea8\", \"#d1495b\", \"#66a182\", \"#edae49\", \"#7d5ba6\", \"#8d6a4f\", \"#4f4f4f\"]          # figures.py palette\nMORDER = [\"sae_top1\", \"sae_top20_lr\", \"sae_code_dim\", \"raw_dim\", \"raw_lr\", \"neuron_top1\", \"neuron_top20_lr\"]\nMNAME = {\"sae_top1\": \"SAE top-1\\nlatent\", \"sae_top20_lr\": \"SAE top-20\\nlogistic\", \"sae_code_dim\": \"DiM on\\nSAE code\",\n         \"raw_dim\": \"DiM\\n(raw)\", \"raw_lr\": \"raw\\nlogistic\", \"neuron_top1\": \"top-1\\nneuron\",\n         \"neuron_top20_lr\": \"top-20\\nneurons\"}\n\n\ndef _f2(v):\n    return \"n/a\" if v is None or (isinstance(v, float) and not np.isfinite(v)) else f\"{v:.2f}\"\n\n\ndef _sc(r):\n    return SCORES[(r[\"task\"], r[\"template\"], r[\"sample_id\"])]\n\n\ndef _yerr(v, lo, hi):\n    # error-bar lengths, clamped at 0: a Wilson bound at a share of 0 or 1 can sit ~1e-17 on the wrong side,\n    # and a bootstrap percentile CI need not contain the point estimate (matplotlib rejects negative lengths)\n    return [[max(v - lo, 0.0)], [max(hi - v, 0.0)]]\n\n\nfig, axes = plt.subplots(3, 2, figsize=(11, 13))\nfor col, t in enumerate(TASKS):\n    # row 1: banned share per template (Wilson 95% CI)\n    ax = axes[0, col]\n    ws = TEMPLATE_IDS + [\"pooled\"]\n    for j, w in enumerate(ws):\n        p = fresh[\"per_task\"][t][w]\n        v, (lo, hi) = p[\"banned_share\"], p[\"banned_share_wilson\"]\n        ax.bar(j, v, 0.6, color=C[6] if w == \"pooled\" else C[1], alpha=0.85)\n        ax.errorbar(j, v, yerr=_yerr(v, lo, hi), fmt=\"none\", ecolor=\"k\", capsize=3, lw=0.8)\n    ax.scatter(range(len(ws)), [REF[\"fresh_pool_summary\"][t][w][\"banned_share\"] for w in ws], marker=\"D\", s=22,\n               color=\"k\", zorder=3, label=\"full 200-run pool\")\n    ax.set_xticks(range(len(ws)), ws)\n    ax.set_ylim(0, 1.05)\n    ax.set_ylabel(f\"share of runs that still write {BANNED[t]}\")\n    ax.set_title(f\"{t}: runs that ignore the {BANNED[t]} ban, per template\\n(bars: demo, {N_PER_CELL} runs each)\",\n                 fontsize=9)\n    ax.legend(frameon=False, fontsize=7, loc=\"upper left\")\n\n    # row 2: within-template AUC of every exp3-fitted readout (run-bootstrap 95% CI)\n    ax = axes[1, col]\n    key = f\"{t}|L{READOUT_LAYER}|k_pre\"\n    tr = rep_i[\"configs\"].get(key, {}).get(\"transfer_from_exp3\", {})\n    ref = REF[\"readout_i_replication\"][key][\"transfer_from_exp3\"]\n    for j, m in enumerate(MORDER):\n        r = tr.get(m, {})\n        a = r.get(\"auc_within_template\")\n        if a is not None and np.isfinite(a):\n            ax.bar(j, a, 0.6, color=C[j % len(C)])\n            ci = r.get(\"within_ci_runs\") or [None, None]\n            if ci[0] is not None:\n                ax.errorbar(j, a, yerr=_yerr(a, ci[0], ci[1]), fmt=\"none\", ecolor=\"k\", capsize=3, lw=0.8)\n    ax.scatter(range(len(MORDER)), [ref[m][\"auc_within_template\"] for m in MORDER], marker=\"D\", s=22, color=\"k\",\n               zorder=3, label=\"full 200-run pool\")\n    ax.axhline(0.5, color=\"grey\", lw=0.6, ls=\"--\")\n    pl = VER[\"checks\"].get(f\"placebo_replication_shuffled_{key}\", {}).get(\"placebo_mean_auc\")\n    if pl is not None:\n        ax.axhline(pl, color=C[3], lw=1.2, ls=\":\", label=f\"DiM, shuffled labels (pooled, {N_PLACEBO}x): {pl:.2f}\")\n    ax.set_xticks(range(len(MORDER)), [MNAME[m] for m in MORDER], fontsize=7)\n    ax.set_ylim(0, 1.05)\n    ax.set_ylabel(\"within-template AUC\")\n    n_pairs = next(iter(tr.values()), {}).get(\"n_within_pairs\", 0)\n    ax.set_title(f\"{t}: exp3-fitted readouts at L{READOUT_LAYER} k_pre\\n({n_pairs} within-template pairs)\", fontsize=9)\n    ax.legend(frameon=True, framealpha=0.9, edgecolor=\"none\", fontsize=7, loc=\"lower right\")\n\n    # row 3: per-run readout geometry (L27 k_pre state projected on two exp3-fitted directions)\n    ax = axes[2, col]\n    for lab, colr in ((SUBSTITUTE[t], C[0]), (BANNED[t], C[1])):\n        for w, mk in zip(TEMPLATE_IDS, \"osD^v\"):\n            pts = [(_sc(r)[\"raw_dim\"], _sc(r)[\"sae_top20_lr\"]) for r in C1_ROWS\n                   if r[\"task\"] == t and r[\"label\"] == lab and r[\"template\"] == w and _sc(r)]\n            if pts:\n                ax.scatter(*zip(*pts), color=colr, marker=mk, s=32, alpha=0.8, edgecolor=\"white\", lw=0.4,\n                           label=f\"{lab} | {w}\")\n    # text: the commit token (first algorithm-identifying lexicon match, i.e. the token right after k_pre) of each\n    # (algorithm, token) cluster, with its run count, at the cluster median; offsets alternate so labels do not overlap\n    groups = defaultdict(list)\n    for r in C1_ROWS:\n        if r[\"task\"] == t and r[\"label\"] in (BANNED[t], SUBSTITUTE[t]) and _sc(r):\n            groups[(r[\"label\"], (r[\"evidence_term\"] or \"none\").lower())].append((_sc(r)[\"raw_dim\"],\n                                                                                 _sc(r)[\"sae_top20_lr\"]))\n    for k, ((lab, term), pts) in enumerate(sorted(groups.items(), key=lambda kv: np.median([p[0] for p in kv[1]]))):\n        xs, ys = zip(*pts)\n        dy = -(12 + 10 * (k % 2)) if lab == BANNED[t] else 7 + 10 * (k % 2)\n        ax.annotate(f\"{term} ({len(pts)})\", (float(np.median(xs)), float(np.median(ys))), textcoords=\"offset points\",\n                    xytext=(0, dy), ha=\"center\", fontsize=7, fontweight=\"bold\",\n                    color=C[1] if lab == BANNED[t] else C[0])\n    ax.axvline(0, color=\"grey\", lw=0.6, ls=\"--\")\n    ax.axhline(0, color=\"grey\", lw=0.6, ls=\"--\")\n    ax.set_xlabel(\"DiM projection of the raw residual (exp3-fitted; > 0 = banned side)\")\n    ax.set_ylabel(\"SAE top-20-latent logistic score (> 0 = banned)\")\n    ax.set_title(f\"{t}: one point per run at L{READOUT_LAYER} k_pre\\n(colour = algorithm, marker = template, \"\n                 f\"text = commit token)\", fontsize=9)\n    ax.legend(frameon=False, fontsize=6, ncol=2)\nfig.tight_layout()\nfig.savefig(FIGS / \"demo_summary.png\", dpi=150)\nplt.show()\n\nprint(\"=== key numbers: demo subset (full 200-run pool in brackets) ===\")\nfor t in TASKS:\n    p, f = fresh[\"per_task\"][t][\"pooled\"], REF[\"fresh_pool_summary\"][t][\"pooled\"]\n    w4, f4 = fresh[\"per_task\"][t][\"W4\"], REF[\"fresh_pool_summary\"][t][\"W4\"]\n    print(f\"{t}: banned share {_f2(p['banned_share'])} ({_f2(f['banned_share'])}) | W4 alone {_f2(w4['banned_share'])} \"\n          f\"({_f2(f4['banned_share'])}) | pooled event gate {p['event_gate_pass']} ({f['event_gate_pass']}) | \"\n          f\"landing {p['landing']}\")\nfor t in TASKS:\n    key = f\"{t}|L{READOUT_LAYER}|k_pre\"\n    tr = rep_i[\"configs\"].get(key, {}).get(\"transfer_from_exp3\", {})\n    ref = REF[\"readout_i_replication\"][key][\"transfer_from_exp3\"]\n    pl = VER[\"checks\"].get(f\"placebo_replication_shuffled_{key}\", {}).get(\"placebo_mean_auc\")\n    print(f\"{key}: within-template AUC  DiM {_f2(tr.get('raw_dim', {}).get('auc_within_template'))} \"\n          f\"({_f2(ref['raw_dim']['auc_within_template'])}) | SAE top-1 latent \"\n          f\"{_f2(tr.get('sae_top1', {}).get('auc_within_template'))} ({_f2(ref['sae_top1']['auc_within_template'])}) | \"\n          f\"SAE top-20 probe {_f2(tr.get('sae_top20_lr', {}).get('auc_within_template'))} \"\n          f\"({_f2(ref['sae_top20_lr']['auc_within_template'])}) | shuffled-label DiM pooled AUC {_f2(pl)}\")\nprint(f\"verify_headlines (checks 1 + 5): {VER['n_checks']} checks, {VER['n_mismatches']} mismatches\")\n_tt = REF[\"sae_transfer_test\"]\nprint(f\"SAE transfer test (full artifact): {_tt['n_pass']}/3 layers pass; dCE ratio \"\n      + \", \".join(f\"L{L} {r:.2f}\" for L, r in _tt[\"ratio_by_layer\"].items()) + f\"  [rule: {_tt['rule']}]\")\n", "structuredPatch": [], "originalFile": null, "userModified": false}
```

### [169] TOOL CALL — Bash · 2026-10-26 10:14:16 UTC

```
Splice new cell-26 source into notebook by id:
python3 - <<'EOF'
import json, ast
from pathlib import Path
nb_path = Path("code_demo.ipynb")
nb = json.loads(nb_path.read_text())
new = Path("tools/_cell26.py").read_text().rstrip("\n")
ast.parse(new)  # syntax check before splicing
cell = next(c for c in nb["cells"] if c["id"] == "cell-26")
lines = new.split("\n")
cell["source"] = [ln + "\n" for ln in lines[:-1]] + [lines[-1]]
nb_path.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")
print("cell-26 replaced;", len(lines), "lines")
EOF
rm tools/_cell26.py && ls tools/
```

### [170] TOOL RESULT — Bash · 2026-10-26 10:14:16 UTC

```
{"stdout": "cell-26 replaced; 121 lines\nbuild_mini_demo_data.py", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [171] ASSISTANT · 2026-10-26 10:14:24 UTC

```
Spliced in and syntax-checked. Final clean-venv run:
```

### [172] TOOL CALL — Bash · 2026-10-26 10:14:24 UTC

```
Final clean-venv run and output check:
rm -f results/*.json logs/*.log figures/*.png && T0=$(date +%s) && UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_3iv5G76C3yoX-2eaf8ea929eb && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_3iv5G76C3yoX-2eaf8ea929eb/bin/python jupyter ipykernel && T1=$(date +%s) && echo "venv setup: $((T1-T0)) s" && /tmp/aii_nb_test_envs/art_3iv5G76C3yoX-2eaf8ea929eb/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | grep -v "running over TCP"; RC=${PIPESTATUS[0]}; T2=$(date +%s); echo "nbconvert exit=$RC, notebook runtime: $((T2-T1)) s"; python3 - <<'EOF'
import json
nb = json.load(open("code_demo.ipynb"))
errs = [(c["id"], o["ename"], o["evalue"]) for c in nb["cells"] if c["cell_type"] == "code" for o in c["outputs"] if o["output_type"] == "error"]
stderr = [(c["id"], "".join(o["text"])[:300]) for c in nb["cells"] if c["cell_type"] == "code" for o in c["outputs"] if o["output_type"] == "stream" and o["name"] == "stderr"]
print("exec counts", [c.get("execution_count") for c in nb["cells"] if c["cell_type"] == "code"])
print("errors", errs, "| stderr", stderr)
c = next(c for c in nb["cells"] if c["id"] == "cell-26")
print("".join("".join(o["text"]) for o in c["outputs"] if o["output_type"] == "stream"))
EOF
```

### [173] TOOL RESULT — Bash · 2026-10-26 10:14:50 UTC

```
{"stdout": "venv setup: 1 s\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[NbConvertApp] Writing 267684 bytes to code_demo.ipynb\nnbconvert exit=0, notebook runtime: 24 s\nexec counts [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]\nerrors [] | stderr []\n=== key numbers: demo subset (full 200-run pool in brackets) ===\nt1: banned share 0.14 (0.15) | W4 alone 0.70 (0.75) | pooled event gate True (True) | landing {'dfs': 43, 'bfs': 7}\nt2: banned share 0.14 (0.13) | W4 alone 0.30 (0.30) | pooled event gate True (True) | landing {'dijkstra': 7, 'bf_spfa': 42, 'other': 1}\nt1|L27|k_pre: within-template AUC  DiM 1.00 (1.00) | SAE top-1 latent 0.29 (0.52) | SAE top-20 probe 0.48 (0.71) | shuffled-label DiM pooled AUC 0.49\nt2|L27|k_pre: within-template AUC  DiM 0.76 (0.76) | SAE top-1 latent 0.54 (0.51) | SAE top-20 probe 0.82 (0.77) | shuffled-label DiM pooled AUC 0.49\nverify_headlines (checks 1 + 5): 4 checks, 0 mismatches\nSAE transfer test (full artifact): 0/3 layers pass; dCE ratio L15 3.29, L20 1.95, L27 1.59  [rule: PASS(L) := dCE_inst(L) <= 1.5 x dCE_base(L) (spliced-in CE over response tokens)]", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [174] TOOL CALL — Read · 2026-10-26 10:14:54 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/figures/demo_summary.png
```

### [175] TOOL RESULT — Read · 2026-10-26 10:14:54 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [176] THINKING · 2026-10-26 10:15:12 UTC

```
The figure looks clean now—titles wrapped, cluster labels separated, and panels matching the printed numbers. Next I'll verify TODO 6 and scan for any absolute server paths in content meant for publication.
```

### [177] TOOL CALL — Bash · 2026-10-26 10:15:12 UTC

```
Verify URL, data file, loader pattern and path hygiene:
python3 - <<'EOF'
import json
from pathlib import Path
want = 'GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-2/experiment-12/demo/mini_demo_data.json"'
nb = json.load(open("code_demo.ipynb"))
srcs = ["".join(c["source"]) for c in nb["cells"]]
print("(1) exact GITHUB_DATA_URL line present:", any(want in s for s in srcs))
print("(2) mini_demo_data.json exists:", Path("mini_demo_data.json").exists(), Path("mini_demo_data.json").stat().st_size, "bytes")
loader = next(s for s in srcs if "def load_data" in s)
print("(3) loader uses urlopen(GITHUB_DATA_URL) with local fallback:", "urllib.request.urlopen(GITHUB_DATA_URL" in loader and 'Path("mini_demo_data.json")' in loader)
print("    load_data() called:", any("data = load_data()" in s for s in srcs))
print("    plain open('mini_demo_data.json') anywhere:", any("open('mini_demo_data.json')" in s or 'open("mini_demo_data.json")' in s for s in srcs))
d = json.load(open("mini_demo_data.json"))
print("    mini data: datasets", [(x["dataset"], len(x["examples"])) for x in d["datasets"]])
EOF
echo "--- absolute-path scan (published files) ---"
grep -rl "/ai-inventor\|/tmp/" --include="*.ipynb" --include="*.json" --include="*.md" --include="*.py" --include="*.log" --include="*.yaml" . 2>/dev/null | grep -v "^./.aii_claude_session.json$" || echo "no absolute server paths found"
echo "--- workspace size check (files > 1 MB) ---"
find . -type f -size +1M -exec ls -la {} \; ; du -sh .
```

### [178] TOOL RESULT — Bash · 2026-10-26 10:15:12 UTC

```
{"stdout": "(1) exact GITHUB_DATA_URL line present: True\n(2) mini_demo_data.json exists: True 312672 bytes\n(3) loader uses urlopen(GITHUB_DATA_URL) with local fallback: True\n    load_data() called: True\n    plain open('mini_demo_data.json') anywhere: False\n    mini data: datasets [('fresh_ban_pool_protocol_v2', 100)]\n--- absolute-path scan (published files) ---\ncode_demo.ipynb\n--- workspace size check (files > 1 MB) ---\n-rw-rw-rw- 1 aii-agent aii-agent 1258578 Oct 26 10:15 ./.repl_agent.ptylog\n7.0M\t.", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [179] ASSISTANT · 2026-10-26 10:15:18 UTC

```
All three TODO 6 checks pass. However, the scan found an absolute path somewhere in `code_demo.ipynb`. Let me locate it:
```

### [180] TOOL CALL — Bash · 2026-10-26 10:15:18 UTC

```
Locate absolute paths inside notebook:
python3 - <<'EOF'
import json, re
nb = json.load(open("code_demo.ipynb"))
for c in nb["cells"]:
    for part, txt in [("source", "".join(c["source"]))] + [("output", json.dumps(o)) for o in c.get("outputs", [])]:
        for m in re.finditer(r"(/ai-inventor|/tmp/)[^\"'\s\\]{0,120}", txt):
            print(c["id"], part, "->", m.group(0)[:160])
EOF
```

### [181] TOOL RESULT — Bash · 2026-10-26 10:15:18 UTC

```
{"stdout": "cell-03 source -> /ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-2/experiment-12/demo/mi", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [182] THINKING · 2026-10-26 10:15:50 UTC

```
That match was just the GitHub org name in a data URL, not a leak—no server paths exposed. Now finalizing the README with verified runtime, scaling log, and results.
```

### [183] TOOL CALL — Write · 2026-10-26 10:15:50 UTC

````
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/README.md

# Demo: reading a coding ban inside Qwen3-8B

A runnable, CPU-only demo notebook for the experiment artifact **"Reading a coding ban inside Qwen3-8B"**
(`art_3iv5G76C3yoX`). The artifact asks two questions:
1. What does Qwen3-8B write when a coding prompt bans its default algorithm? On T1 grid path, BFS is banned. On T2
   weighted shortest path, Dijkstra is banned.
2. Can simple readouts of the model's residual stream tell banned runs from substitute runs?

The full pipeline needs a 16 GB GPU, vLLM and about one GPU-hour. This demo runs the pipeline's CPU analysis stages
on stored per-run data, and finishes in about 25 s, package installation included.

## What the notebook does

`code_demo.ipynb` keeps the artifact's own code, taken from `method.py` and `src/`. It splits that code into cells
with explanations between them, and changes only the input lines, so each function reads the demo data instead of the
pipeline's files. It runs:

1. `src/core.py`: the protocol constants and helpers. The constants are the models, the label maps, the five frozen
   ban templates W1–W5, and the seeds. The helpers handle IO, the Wilson interval and timing.
2. `src/final.py::fresh_pool_summary`: for each task and template, how often the model still writes the banned
   algorithm. Reported with Wilson 95% CIs, the event gate, the pass rate and where the runs landed.
3. `src/readout_i.py::auc / within_u / within_auc` and `src/analysis.py::_boot_runs`: pooled and within-template
   AUCs, with a bootstrap over runs.
4. `src/analysis.py::readout_i_replication`, scoring half only. Readout objects were fitted on exp3 states, then
   applied to each run's layer-27 residual state at `k_pre`; the stored per-run scores are evaluated here. The readouts
   are:
   - SAE top-1 latent;
   - SAE top-20-latent logistic probe;
   - DiM on the SAE code;
   - baselines: DiM on the raw residual, a raw logistic probe, and the top-1 / top-20 raw dimensions.
5. `src/verify_headlines.py` checks 1 and 5: an independent pandas / scikit-learn re-derivation of the banned share and
   of the DiM AUC, plus a shuffled-label placebo.
6. A summary figure and table, shown next to the artifact's full 200-run values:
   - the banned share per template;
   - the readout AUCs;
   - the per-run readout geometry: each run's state projected onto the DiM and SAE-probe directions, with every
     cluster labelled by its commit token.

The following parts do not run here, because they need the 8B model, the SAE, or data outside this demo's one
dataset. The notebook marks each spot with a `# notebook:` comment.
- generation with vLLM;
- the labeller;
- the Hugging Face state, attention and transfer-test passes;
- the exp3 discovery;
- the nested selection inside the fresh pool;
- the same-seed CRN, thought-anchor and J-lens analyses.

## Results of the demo run

Each value is the demo subset of 100 runs; the artifact's full 200-run value is in brackets.

| Quantity | T1 (BFS banned) | T2 (Dijkstra banned) |
|---|---|---|
| Banned share, pooled | 0.14 (0.15) | 0.14 (0.13) |
| Banned share, template W4 *"X is not allowed here."* | 0.70 (0.75) | 0.30 (0.30) |
| Within-template AUC, DiM (raw), L27 `k_pre` | 1.00 (1.00) | 0.76 (0.76) |
| Within-template AUC, SAE top-1 latent | 0.29 (0.52) | 0.54 (0.51) |
| Within-template AUC, SAE top-20 probe | 0.48 (0.71) | 0.82 (0.77) |
| Shuffled-label DiM AUC (200 placebos) | 0.49 | 0.49 |

`verify_headlines` checks 1 and 5 pass: 4 checks, 0 mismatches.

What the run shows:
- **Bans substitute; they do not subtract.** The model nearly always writes the banned algorithm or its single
  natural substitute: DFS on T1, Bellman-Ford/SPFA on T2. How often a ban works depends on its wording.
- **The geometry panels make the artifact's main caveat visible.** At `k_pre` the runs cluster by the *next token*,
  the commit token, more than by the algorithm. On T2, Dijkstra runs that commit at `heapq` sit far on the banned
  side, while Dijkstra runs that commit at `deque` sit inside the Bellman-Ford/SPFA `deque` cluster.

## Layout

| Path | What it is |
|---|---|
| `code_demo.ipynb` | The demo notebook. Colab-ready: it loads `mini_demo_data.json` from GitHub and falls back to the local copy. |
| `mini_demo_data.json` | 100 of the 200 runs of the artifact's `fresh_ban_pool_protocol_v2` dataset, plus the full-pool reference numbers |
| `tools/build_mini_demo_data.py` | The deterministic curation script that produced `mini_demo_data.json` from the artifact's `full_method_out.json` and `results/labelled_c1.jsonl` |
| `results/` | Written by the notebook: `fresh_pool_summary.json`, `readout_i_replication.json`, `verify_headlines.json`, `timing.json` |
| `figures/demo_summary.png` | Written by the notebook: the summary figure |
| `logs/stage_demo.log` | Written by the notebook: the loguru debug log |
| `.aii/manifest.yaml` | Storage decisions. None are needed: there are no large binaries or caches. |

## The demo data

`mini_demo_data.json` follows the artifact's `exp_gen_sol_out` layout, `{"metadata": ..., "datasets": [...]}`. It
holds one dataset, `fresh_ban_pool_protocol_v2`, with 10 of the 20 runs in each task × template cell.

Each example has these fields:
- `input`: the prompt;
- `output`: the canonical label of the generated program: `bfs`, `dfs`, `dijkstra`, `bf_spfa` or `other`;
- `metadata_*`: the seed, template, hidden-test pass, commit token and index, and the per-run readout scores at L27
  `k_pre`;
- `metadata_code`: the generated program itself, joined from the artifact's `results/labelled_c1.jsonl` and checked
  against `metadata_code_sha256`.

The selection is deterministic:
- Labels are allocated proportionally within each cell, and every label present keeps at least one run. So T1 W4
  keeps 7 BFS and 3 DFS runs, and T2 keeps all four templates that produced Dijkstra.
- Seeds are evenly spaced.
- One T1 run without a `k_pre` state is kept on purpose.
- Classes alternate inside each cell, so lowering the config value `N_PER_CELL` (runs per cell) keeps both classes.

`metadata.reference_full_pool` holds the artifact's own numbers for all 200 runs:
- the fresh-pool summary;
- the replication AUCs;
- the class counts;
- the matching `verify_headlines` checks;
- the SAE transfer-test ratios.

To rebuild the file from the artifact folder:

```bash
python3 tools/build_mini_demo_data.py --full <artifact>/full_method_out.json \
    --c1 <artifact>/results/labelled_c1.jsonl --out mini_demo_data.json
```

## How to run

**Colab:** open `code_demo.ipynb` and run all cells. The install cell adds only `loguru`; numpy, pandas, scipy,
scikit-learn and matplotlib come pre-installed with Colab.

**Locally** (Python 3.12). Outside Colab, the install cell pins Colab's package versions:

```bash
uv venv --seed --python 3.12 .venv-nb
uv pip install --python .venv-nb/bin/python jupyter ipykernel
.venv-nb/bin/jupyter nbconvert --to notebook --execute code_demo.ipynb --output code_demo.ipynb
```

**Configuration** is one cell near the top:

| Parameter | Value | Meaning |
|---|---|---|
| `N_PER_CELL` | 10 | runs per task × template; 10 is the whole demo file |
| `N_BOOT` | 2000 | bootstrap resamples, the original count |
| `N_PLACEBO` | 200 | shuffled-label placebos, the original count |

Measured runtimes in a clean venv, package installation included:

| `N_PER_CELL` / `N_BOOT` / `N_PLACEBO` | Runtime |
|---|---|
| 2 / 1 / 1 | 17 s |
| 5 / 200 / 20 | 16 s |
| 10 / 2000 / 200 (the shipped values) | 24 s |

To use all 200 runs, every layer and position, and the GPU stages, run the original artifact's pipeline:
`uv run method.py --stage ...`, as described in its `README.md` and `reproducibility.md`.

## Restoring removed files

`.aii/manifest.yaml` marks nothing for deletion, so nothing needs restoring. Every file in this folder is small text,
JSON or PNG, and none is anywhere near the 100 MB publish limit.
- The notebook's outputs (`results/`, `figures/`, `logs/`) are regenerated by running `code_demo.ipynb`.
- `mini_demo_data.json` is regenerated by the command in "The demo data" above.

The full pipeline is not part of this demo. Its models and SAE live in the Hugging Face cache. To download them again:

```bash
huggingface-cli download Qwen/Qwen3-8B
huggingface-cli download Qwen/Qwen3-8B-FP8
huggingface-cli download Qwen/Qwen3-8B-Base
huggingface-cli download Qwen/SAE-Res-Qwen3-8B-Base-W64K-L0_50 layer15.sae.pt layer20.sae.pt layer27.sae.pt config.json README.md
```
````

### [184] TOOL RESULT — Write · 2026-10-26 10:15:50 UTC

```
{"type": "update", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/README.md", "content": "# Demo: reading a coding ban inside Qwen3-8B\n\nA runnable, CPU-only demo notebook for the experiment artifact **\"Reading a coding ban inside Qwen3-8B\"**\n(`art_3iv5G76C3yoX`). The artifact asks two questions:\n1. What does Qwen3-8B write when a coding prompt bans its default algorithm? On T1 grid pa... [truncated, 29935 chars total]
```

### [185] THINKING · 2026-10-26 10:16:04 UTC

```
I noticed the config comment says "~20 s" but I actually measured 24 s, so I'll fix that comment and re-run the notebook to keep it consistent with the source.
```

### [186] TOOL CALL — Bash · 2026-10-26 10:16:04 UTC

```
Fix runtime comment and re-run final notebook:
python3 - <<'EOF'
import json
from pathlib import Path
p = Path("code_demo.ipynb")
nb = json.loads(p.read_text())
c = next(c for c in nb["cells"] if c["id"] == "cell-06")
src = "".join(c["source"])
old = "#   N_PER_CELL=10, N_BOOT=2000, N_PLACEBO=200 -> ~20 s (original analysis values; ~9 s once packages are installed)"
new = "#   N_PER_CELL=10, N_BOOT=2000, N_PLACEBO=200 -> 24 s (original analysis values; ~9 s once packages are installed)"
assert src.count(old) == 1
src = src.replace(old, new)
lines = src.split("\n")
c["source"] = [ln + "\n" for ln in lines[:-1]] + [lines[-1]]
p.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")
print(src)
EOF
rm -f results/*.json logs/*.log figures/*.png && UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_3iv5G76C3yoX-2eaf8ea929eb && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_3iv5G76C3yoX-2eaf8ea929eb/bin/python jupyter ipykernel && T1=$(date +%s) && /tmp/aii_nb_test_envs/art_3iv5G76C3yoX-2eaf8ea929eb/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | grep -v "running over TCP"; RC=${PIPESTATUS[0]}; T2=$(date +%s); echo "nbconvert exit=$RC, notebook runtime: $((T2-T1)) s"; python3 -c "
import json; nb=json.load(open('code_demo.ipynb'))
print('errors', [(c['id'], o['ename']) for c in nb['cells'] if c['cell_type']=='code' for o in c['outputs'] if o['output_type']=='error'])
print('exec counts', [c.get('execution_count') for c in nb['cells'] if c['cell_type']=='code'])"; ls results logs figures
```

### [187] TOOL RESULT — Bash · 2026-10-26 10:16:30 UTC

```
{"stdout": "# ---- tunable parameters ------------------------------------------------------------------------------------------\nN_PER_CELL = 10       # runs used per task x template cell (10 = the whole demo file; the original pool has 20)\nN_BOOT = 2000         # bootstrap resamples over runs for the AUC CIs (= the original, analysis.py N_BOOT = 2000)\nN_PLACEBO = 200       # shuffled-label placebo AUCs per config (= the original, verify_headlines.py)\nC1_PER_TEMPLATE = 20  # runs per task x template in the original C1 pool (method.py default C1_PER_TEMPLATE=20)\n# scaling log (clean local venv, notebook runtime incl. package install):\n#   N_PER_CELL=2,  N_BOOT=1,    N_PLACEBO=1   -> 17 s\n#   N_PER_CELL=5,  N_BOOT=200,  N_PLACEBO=20  -> 16 s\n#   N_PER_CELL=10, N_BOOT=2000, N_PLACEBO=200 -> 24 s (original analysis values; ~9 s once packages are installed)\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[NbConvertApp] Writing 267683 bytes to code_demo.ipynb\nnbconvert exit=0, notebook runtime: 24 s\nerrors []\nexec counts [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]\nfigures:\ndemo_summary.png\n\nlogs:\nstage_demo.log\n\nresults:\nfresh_pool_summary.json\nreadout_i_replication.json\ntiming.json\nverify_headlines.json", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [188] ASSISTANT · 2026-10-26 10:16:36 UTC

```
The final run passed again: exit 0, 24 s, 15/15 cells, no errors. Writing the required structured output:
```

### [189] TOOL CALL — Write · 2026-10-26 10:16:36 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/.terminal_claude_agent_struct_out.json

{
 "out_expected_files": {
  "notebook": "code_demo.ipynb",
  "mini_data_file": "mini_demo_data.json"
 }
}
```

### [190] TOOL RESULT — Write · 2026-10-26 10:16:36 UTC

```
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_2/art_3iv5G76C3yoX/.terminal_claude_agent_struct_out.json", "content": "{\n \"out_expected_files\": {\n  \"notebook\": \"code_demo.ipynb\",\n  \"mini_data_file\": \"mini_demo_data.json\"\n }\n}\n", "structuredPatch": [], "originalFile": null, "userModified": false}
```

### [191] TOOL CALL — Bash · 2026-10-26 10:16:36 UTC

```
Validate struct output and list final workspace:
python3 -c "import json; print(json.load(open('.terminal_claude_agent_struct_out.json')))" && find . -path ./.repl_agent.ptylog -prune -o -type f -print | sort | xargs ls -la | awk '{print $5, $9}'
```

### [192] TOOL RESULT — Bash · 2026-10-26 10:16:36 UTC

```
{"stdout": "{'out_expected_files': {'notebook': 'code_demo.ipynb', 'mini_data_file': 'mini_demo_data.json'}}\n475 ./.aii/manifest.yaml\n54 ./.aii_claude_session.json\n107 ./.terminal_claude_agent_struct_out.json\n8487 ./README.md\n267712 ./code_demo.ipynb\n212442 ./figures/demo_summary.png\n806 ./logs/stage_demo.log\n312672 ./mini_demo_data.json\n4921 ./results/fresh_pool_summary.json\n16484 ./results/readout_i_replication.json\n397 ./results/timing.json\n731 ./results/verify_headlines.json\n7560 ./tools/build_mini_demo_data.py", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [193] ASSISTANT · 2026-10-26 10:16:55 UTC

```
I built the demo notebook and its data file. The notebook runs cleanly from a fresh Python 3.12 environment in 24 s, against a 10-minute budget, with no cell errors.

The full experiment needs a 16 GB GPU and the 8B model, so the notebook runs only the original pipeline's CPU analysis steps, on stored per-run results. Those steps are:
- the per-template count of how often the model still writes the banned algorithm;
- the scoring of each readout from stored per-run scores (AUCs with bootstrap confidence intervals);
- the independent re-check with a shuffled-label placebo.

The code is copied from the original with only the input lines changed. Every skipped GPU or tensor step is marked with a `# notebook:` comment.

**Data:** `mini_demo_data.json` holds 100 of the 200 fresh ban-pool runs, 10 per task × template, keeping every outcome label that appears. I added two things beyond the original records: each run's generated program text (checked against its stored hash), and the full 200-run reference numbers, so every demo figure is shown next to the original.

**Scaling:** all three rounds ran in a fresh venv with no errors.

| Runs per cell / bootstrap / placebo | Runtime |
|---|---|
| 2 / 1 / 1 (minimum) | 17 s |
| 5 / 200 / 20 | 16 s |
| 10 / 2000 / 200 (the original values, shipped) | 24 s |

**Results on the subset vs the full pool:**
- **How often the ban fails:** 0.14 vs 0.15 on T1 and 0.14 vs 0.13 on T2. One wording, "BFS is not allowed here", still gets BFS 0.70 of the time (0.75 in the full pool).
- **Simple class-mean direction (DiM):** it separates banned from substitute runs within the same template with AUC 1.00 on T1 and 0.76 on T2, the same as the full pool.
- **Single best SAE latent:** 0.29 on T1 and 0.54 on T2, roughly chance.
- **Shuffled labels:** 0.49.
- **Re-check:** 4 checks, 0 mismatches.

**Something I didn't expect:** in the scatter plot of the readout scores, runs cluster by the next token the model writes more than by the algorithm it ends up using. On T2, Dijkstra runs that import `heapq` sit far on the "banned" side. Dijkstra runs that import `deque` sit inside the Bellman-Ford cluster. So the 0.76 on T2 mostly reflects which word comes next, not an earlier choice of algorithm. This matches the original experiment's own caveat, and the notebook's closing notes say so.

Two process notes:
- No to-do tracking tool was available, so I worked through the six to-do items in order without one.
- I generated the notebook with a one-off script (since deleted) and made later edits with the notebook-editing tool. Once the notebook grew past what that tool can read back, the last two small edits (a figure tweak and a runtime comment) were made by editing the notebook file directly by cell id, followed by a full re-run.

Nothing in the folder is large, so `.aii/manifest.yaml` has no entries. The README covers what the demo does, the file layout, how to run it (Colab and local), and how to rebuild the data file.

Files are in the workspace:
- `code_demo.ipynb`
- `mini_demo_data.json`
- `README.md`
- `.aii/manifest.yaml`
- `tools/build_mini_demo_data.py`
- `figures/demo_summary.png`
- `.terminal_claude_agent_struct_out.json`
```
