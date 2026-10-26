# gen_demo_art_experiment_16 — report_results

> Phase: `gen_paper_repo` · `gen_demo_art`
> Run: `gen_paper_repo_c164ac661673` — A Random Activation Push Changes a Code Model's Algorithm Where Temperature Does Not
>
> Full, verbatim transcript of this agent task — every system/user prompt, assistant response, thinking block, tool call and tool result — in the order they occurred. Nothing truncated.

## Task: `gen_demo_art_experiment_16` (terminal_claude_agent, claude-opus-5-5)

### [1] CONFIG · 2026-10-26 10:17:48 UTC

```
model: Claude Opus 5.5 | effort: max | permission: bypassPermissions
```

### [2] SYSTEM-USER prompt · 2026-10-26 10:17:58 UTC

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
Your workspace: `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4`

CRITICAL: Every file you create, write, or save MUST be inside this workspace directory (subdirectories OK). You MUST NOT write files anywhere outside this path — external paths are READ-ONLY. Use absolute paths for all file operations.

EVERY file write MUST start with `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/`:
GOOD: `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/file.py`, `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/results/out.json`
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
id: art__5akZ9W9iZM4
type: experiment
title: Where a coding ban takes effect in Qwen3-8B
summary: >-
  Behavioural route test of prompt bans in Qwen3-8B (bf16, thinking off) on the 12 frozen exp11 bench tasks, reusing exp8's
  HF engine (common-random-numbers inverse-CDF sampling, KV-cache splicing). 13,030 CRN-coupled samples, all labelled by the
  frozen runtime+AST+judge labellers (judge spend USD 0.105). Arms per task: a full ban, b token-matched neutral twin, c prompt
  route (twin condition + ban task-spec states), d direct route (ban condition + twin task-spec states), K0 (condition span
  invisible to generated tokens), V1 one-shot veto of the default's frozen distinctive n-gram, and signature/neutral prefills
  under ban and twin. GATE: only 5/12 tasks are gated (T03 0.99, T10 1.00, T05 0.83, T06 0.79, T13 0.59 avoidance); bans fail
  on R1/R3/R6/T11 and partly on T04/T08/T14; template W4 is weakest (avoidance 0.19). C2a (prompt route >= 2/3): DISCONFIRMED
  under jackknife (primary, low-cluster per F5), percentile and BCa intervals: pooled F_prompt 0.611 [jackknife 0.06, 1.17],
  F_direct 0.744 [0.38, 1.11], interaction -0.355, F_K0 0.621. Mechanism is task-dependent: T03/T10 redundant (each route
  alone suffices), T05/T06 direct route (F_direct 0.96/0.99; d reproduces the ban, c and K0 do not), T13 superadditive (both
  needed). An independent second CRN draw reproduces it (pooled 0.64/0.74; per-task Spearman 0.89/0.90). C2c (veto sufficiency
  predicts F_direct): INCONCLUSIVE; the frozen n-gram rule picks zero-collateral identifier/structural tokens, so V_t <= 0.41
  everywhere, all tasks classed HIGH_DIRECT, hit fraction 0.80, rho -0.34 (exact permutation p 0.30). Prefill: forcing the
  default's opening up to its first body token undoes the ban completely (P_open 0.98-1.00) while a neutral def line undoes
  none (-0.12-0.01); the depth sweep shows the ban survives the def line and gives way at the first content token of the body.
  Path screen (T1/T2, exp8 twin prompts): one-shot, persistent, iterated and opening vetoes never move the default (off-default
  <= 0.01); committed T1 prediction hit, T2 prediction (veto suffices, lands on BF/SPFA) missed; iteration-2 ban landings
  recomputed exactly (T1 DFS 257/257, T2 BF/SPFA 255/260). Controls: placebo splice |diff| <= 0.04 and knockout-mechanics
  K0b 1.00 on 6 tasks. Validation: bench sha256 vs commitment.json, labeller re-check, prompt alignment asserts, CPU tests,
  GPU tests U1-U3 (CRN determinism, splice identities, zero knockout attention mass) and U9 vs exp8 all pass; two hash-chained
  pre-registration commits precede the first ban rows; two audit scripts re-derive every headline from raw rows (0 mismatches;
  placebo/shuffled inputs fail). Provides: data/samples.jsonl (one labelled row per sample, token ids in data/samples_raw.jsonl),
  results/*.json (route, crn_flips, landing_by_route, c2c, prefill, screen_paths, replication incl. depth curve, lp_readout,
  c1_events.jsonl, gate, timing, deviations, rederive/rederive2), figures fig1-fig6, method_out.json (exp_gen_sol_out; datasets
  route_arms, veto_sufficiency, prefill, path_screen, controls) and README/reproducibility. Deviations: L4 GPU with B=40 shape
  classes, K0 as a span-dropped cache, fence stop, extras beyond plan, three logged analysis amendments.
workspace_path: >-
  /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16
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
Raw data URL: https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-3/experiment-16/demo/mini_demo_data.json

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
GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-3/experiment-16/demo/mini_demo_data.json"
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
To test-run the notebook in a clean environment (simulating Colab), use the disposable venv at `/tmp/aii_nb_test_envs/art__5akZ9W9iZM4-bfb6955ec1d9`. It is on this machine's local disk, outside your workspace, which is on a slow network volume: never create a venv inside your workspace.
```bash
UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art__5akZ9W9iZM4-bfb6955ec1d9
UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art__5akZ9W9iZM4-bfb6955ec1d9/bin/python jupyter ipykernel
/tmp/aii_nb_test_envs/art__5akZ9W9iZM4-bfb6955ec1d9/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb
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
TODO 6. Verify: (1) code_demo.ipynb contains GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-3/experiment-16/demo/mini_demo_data.json" exactly, (2) mini_demo_data.json exists, (3) uses GitHub URL pattern not just open('mini_demo_data.json').
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

### [3] ASSISTANT · 2026-10-26 10:18:16 UTC

```
I'll start by loading the required skills and exploring the artifact and my workspace in parallel.
```

### [4] TOOL CALL — Skill · 2026-10-26 10:18:16 UTC

```
aii-colab
```

### [5] TOOL RESULT — Skill · 2026-10-26 10:18:16 UTC

```
{"success": true, "commandName": "aii-colab"}
```

### [6] TOOL CALL — Skill · 2026-10-26 10:18:16 UTC

```
aii-long-running-tasks
```

### [7] TOOL RESULT — Skill · 2026-10-26 10:18:16 UTC

```
{"success": true, "commandName": "aii-long-running-tasks"}
```

### [8] TOOL CALL — Bash · 2026-10-26 10:18:16 UTC

```
List workspace and artifact directory contents:
pwd && ls -la && ls -la .aii 2>/dev/null; git log --oneline | head -5; echo "---ARTIFACT---"; ls -la /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16
```

### [9] TOOL RESULT — Bash · 2026-10-26 10:18:16 UTC

```
{"stdout": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4\ntotal 2973\ndrwxrwxrwx 3 aii-agent aii-agent 1003720 Oct 26 10:17 .\ndrwxrwxrwx 7 aii-agent aii-agent 2000381 Oct 26 10:17 ..\ndrwxrwxrwx 2 aii-agent aii-agent       1 Oct 26 10:17 .aii\n-rw-rw-rw- 1 aii-agent aii-agent      54 Oct 26 10:17 .aii_claude_session.json\n-rw-rw-rw- 1 aii-agent aii-agent   42135 Oct 26 10:18 .repl_agent.ptylog\ntotal 981\ndrwxrwxrwx 2 aii-agent aii-agent       1 Oct 26 10:17 .\ndrwxrwxrwx 3 aii-agent aii-agent 1003720 Oct 26 10:17 ..\nfatal: not a git repository (or any parent up to mount point /ai-inventor)\nStopping at filesystem boundary (GIT_DISCOVERY_ACROSS_FILESYSTEM not set).\n---ARTIFACT---\ntotal 27030\ndrwxrwxrwx 16 aii-agent aii-agent 2012015 Oct 21 02:37 .\ndrwxrwxrwx  9 aii-agent aii-agent 3000543 Oct 20 20:17 ..\ndrwxrwxrwx  2 aii-agent aii-agent   57500 Oct 20 20:54 .aii\n-rw-rw-rw-  1 aii-agent aii-agent      54 Oct 20 17:37 .aii_claude_session.json\n-rw-rw-rw-  1 aii-agent aii-agent   15552 Oct 20 20:54 .aii_worker_result.json\n-rw-rw-rw-  1 aii-agent aii-agent      32 Oct 20 20:29 .gitignore\n-rw-rw-rw-  1 aii-agent aii-agent 3745084 Oct 20 20:54 .repl_agent.ptylog\n-rw-rw-rw-  1 aii-agent aii-agent    3811 Oct 20 20:49 .terminal_claude_agent_struct_out.json\n-rw-rw-rw-  1 aii-agent aii-agent   25989 Oct 20 20:52 README.md\ndrwxrwxrwx  2 aii-agent aii-agent 1001868 Oct 21 02:37 audit\n-rw-rw-rw-  1 aii-agent aii-agent    2793 Oct 20 18:52 commitments.log\ndrwxrwxrwx  2 aii-agent aii-agent 2007117 Oct 20 20:21 data\ndrwxrwxrwx  2 aii-agent aii-agent 1051913 Oct 20 20:35 figures\n-rw-rw-rw-  1 aii-agent aii-agent 1680681 Oct 20 20:39 full_method_out.json\ndrwxrwxrwx  9 aii-agent aii-agent 2003837 Oct 20 17:50 inputs\ndrwxrwxrwx  4 aii-agent aii-agent 2000115 Oct 20 17:50 labelling\ndrwxrwxrwx  2 aii-agent aii-agent 1042375 Oct 20 20:31 logs\n-rw-rw-rw-  1 aii-agent aii-agent    4327 Oct 20 18:50 method.py\n-rw-rw-rw-  1 aii-agent aii-agent 1464536 Oct 20 20:32 method_out.json\n-rw-rw-rw-  1 aii-agent aii-agent  172058 Oct 20 20:39 mini_method_out.json\ndrwxrwxrwx  2 aii-agent aii-agent 1027819 Oct 20 20:08 predictions\n-rw-rw-rw-  1 aii-agent aii-agent  158442 Oct 20 20:39 preview_method_out.json\ndrwxrwxrwx  2 aii-agent aii-agent 1025540 Oct 20 17:57 prompts\n-rw-rw-rw-  1 aii-agent aii-agent    2167 Oct 20 20:39 pyproject.toml\n-rw-rw-rw-  1 aii-agent aii-agent   14076 Oct 20 20:48 reproducibility.md\n-rw-rw-rw-  1 aii-agent aii-agent    1431 Oct 20 20:39 requirements.txt\n-rwxrwxrwx  1 aii-agent aii-agent     514 Oct 20 19:10 restore.sh\ndrwxrwxrwx  2 aii-agent aii-agent 1081924 Oct 20 20:40 results\n-rwxrwxrwx  1 aii-agent aii-agent     930 Oct 20 20:34 run_final.sh\ndrwxrwxrwx  3 aii-agent aii-agent 1019344 Oct 21 02:37 src\ndrwxrwxrwx  2 aii-agent aii-agent 1001146 Oct 21 02:37 tests\ndrwxrwxrwx  2 aii-agent aii-agent 1002877 Oct 20 19:38 token_lp\ndrwxrwxrwx  2 aii-agent aii-agent   40500 Oct 20 20:30 work", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [10] ASSISTANT · 2026-10-26 10:18:20 UTC

```
Skills loaded (TODO 1). There's no todo-tracking tool in this session, so I'll track the 6 TODOs in order myself. Now TODO 2: reading the demo file and its surroundings.
```

### [11] TOOL CALL — Bash · 2026-10-26 10:18:20 UTC

```
Show method.py and list source files with sizes:
A=/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16; cat $A/method.py; echo "=====SRC====="; find $A/src $A/tests $A/audit -type f | head -80; echo "=====SIZES====="; du -sh $A/* 2>/dev/null | sort -h | tail -30
```

### [12] TOOL RESULT — Bash · 2026-10-26 10:18:20 UTC

```
{"stdout": "#!/usr/bin/env python3\n\"\"\"Where a coding ban takes effect, on 12 frozen bench tasks (Qwen3-8B bf16, thinking off).\n\nEntry point for every stage. The method is the CRN-coupled KV-splice route test (arms c = prompt route,\nd = direct route, K0 = condition-span knockout) plus the one-shot veto (V1) and prefill probes; the baselines are\nthe clean/corrupted endpoints (a = full ban, b = token-length-matched neutral twin) sampled in the same pipeline with\nthe same uniforms, plus the placebo splice and the knockout-mechanics control.\n\n  uv run method.py s0        # snapshot inputs read-only + verify bench sha256 (results/input_hashes.json)\n  uv run method.py recheck   # S0.5 labeller re-check (results/labeller_recheck.json)\n  uv run method.py s1        # S1 prompts with alignment assertions (prompts/prompts.jsonl)\n  uv run method.py s2        # S2 frozen forecast objects (predictions/*.json)\n  uv run method.py tests     # CPU tests T3-T5 (results/tests_cpu.json)\n  uv run method.py label     # label worker (streams data/samples_raw.jsonl -> data/samples.jsonl)\n  uv run method.py gpu       # GPU queue S3.2 -> S4 -> screen -> U-tests -> commit #2 -> S6/Q1 -> gate -> Q2 -> Q4 -> S8\n  uv run method.py close1    # append the analysis code to commit #1 (releases the GPU queue's ban-prompt gate)\n  uv run method.py analysis  # S9 (results/*.json)\n  uv run method.py figures   # figures/*.png|pdf\n  uv run method.py outputs   # method_out.json (+ full/mini/preview), results/deviations.json\n  uv run method.py audit     # audit/rederive.py (results/rederive.json)\n\n`label` and `gpu` run concurrently (two terminals or background jobs); the GPU queue waits for the labels it needs.\nEnvironment: BRT_BATCH (default 40), BRT_PRUNE_AFTER (560), BRT_GPU_DEADLINE (epoch seconds, optional).\n\"\"\"\n\nfrom __future__ import annotations\n\nimport os\nimport subprocess\nimport sys\nfrom pathlib import Path\n\nROOT = Path(__file__).resolve().parent\nsys.path.insert(0, str(ROOT / \"src\"))\nsys.path.insert(0, str(ROOT / \"src\" / \"analysis\"))\n\nfrom loguru import logger  # noqa: E402\n\nfrom cfg import setup_logging  # noqa: E402\n\n\ndef _tok():\n    from transformers import AutoTokenizer\n\n    from cfg import model_path\n\n    return AutoTokenizer.from_pretrained(model_path())\n\n\n@logger.catch(reraise=True)\ndef main() -> None:\n    stage = sys.argv[1] if len(sys.argv) > 1 else \"help\"\n    setup_logging(f\"method_{stage}\")\n    if stage == \"s0\":\n        from s0_inputs import stage_s0\n\n        stage_s0()\n    elif stage == \"recheck\":\n        from s0_recheck import stage_recheck\n\n        stage_recheck()\n    elif stage == \"s1\":\n        from prompts_s1 import stage_s1\n\n        stage_s1(_tok())\n    elif stage == \"s2\":\n        from forecast_s2 import stage_s2\n\n        stage_s2(_tok())\n    elif stage == \"tests\":\n        subprocess.run([sys.executable, str(ROOT / \"tests\" / \"test_cpu.py\")], check=True)\n    elif stage == \"label\":\n        from labelq import run_label_worker\n\n        run_label_worker()\n    elif stage == \"gpu\":\n        from gpu import run\n\n        dl = os.environ.get(\"BRT_GPU_DEADLINE\")\n        pa = os.environ.get(\"BRT_PRUNE_AFTER\", \"560\")\n        run(int(os.environ.get(\"BRT_BATCH\", \"40\")), float(dl) if dl else None, int(pa) if pa else None)\n    elif stage == \"close1\":\n        from cfg import RAW, WORK_DIR, read_jsonl, utc_now\n        from commit import commit_files\n\n        bans = [r for r in read_jsonl(RAW) if r[\"arm\"] in (\"a\", \"c\", \"d\", \"K0\") or r[\"arm\"].startswith(\"BAN\")]\n        if bans:\n            raise RuntimeError(\"a ban sample already exists: commit #1 can no longer be closed honestly\")\n        commit_files(\"commit1\", [ROOT / \"src\" / \"analysis\" / \"analysis.py\", ROOT / \"src\" / \"gpu.py\",\n                                 ROOT / \"src\" / \"screen.py\", ROOT / \"tests\" / \"test_cpu.py\"])\n        (WORK_DIR / \"commit1_closed\").write_text(utc_now())\n    elif stage == \"analysis\":\n        from analysis import run_analysis\n\n        run_analysis()\n    elif stage == \"figures\":\n        from figures import make_figures\n\n        make_figures()\n    elif stage == \"outputs\":\n        from outputs import build_outputs\n\n        build_outputs()\n    elif stage == \"audit\":\n        subprocess.run([sys.executable, str(ROOT / \"audit\" / \"rederive.py\")], check=True)\n    else:\n        print(__doc__)\n\n\nif __name__ == \"__main__\":\n    main()\n=====SRC=====\n/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/audit/rederive2.py\n/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/audit/rederive.py\n/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/cfg.py\n/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/figures.py\n/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/replication.py\n/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/gpu_extras.py\n/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/supplementary.py\n/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/outputs.py\n/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/labelq.py\n/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/forecast_s2.py\n/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/screen.py\n/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/gpu.py\n/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/engine.py\n/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/gpu_tests.py\n/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/commit.py\n/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/run_s2.py\n/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/prompts_s1.py\n/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/s0_recheck.py\n/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/s0_inputs.py\n/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/analysis/analysis.py\n/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/tests/test_analysis_smoke.py\n/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/tests/test_cpu.py\n/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/tests/gpu_timing2.py\n/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/tests/gpu_smoke.py\n=====SIZES=====\n1.0K\t/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/restore.sh\n1.0K\t/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/run_final.sh\n1.5K\t/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/requirements.txt\n2.5K\t/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/pyproject.toml\n3.0K\t/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/commitments.log\n4.5K\t/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/method.py\n14K\t/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/reproducibility.md\n26K\t/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/README.md\n46K\t/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/work\n155K\t/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/preview_method_out.json\n169K\t/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/mini_method_out.json\n991K\t/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/tests\n998K\t/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/audit\n1010K\t/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/token_lp\n1.3M\t/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/predictions\n1.3M\t/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/prompts\n1.4M\t/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/method_out.json\n1.5M\t/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/logs\n1.6M\t/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/figures\n1.7M\t/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/full_method_out.json\n1.9M\t/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/results\n2.2M\t/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src\n6.0M\t/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/labelling\n74M\t/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/data\n98M\t/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/inputs", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [13] ASSISTANT · 2026-10-26 10:18:28 UTC

```
`method.py` is a stage dispatcher; the real code lives in `src/`. Let me check the sizes of the source modules and read the README/reproducibility docs.
```

### [14] TOOL CALL — Bash · 2026-10-26 10:18:28 UTC

```
Count lines in source files and show config files:
A=/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16; wc -l $A/src/*.py $A/src/analysis/*.py $A/tests/*.py $A/audit/*.py; echo; cat $A/pyproject.toml; echo; cat $A/requirements.txt; echo; cat $A/run_final.sh; echo; cat $A/restore.sh; cat $A/.gitignore
```

### [15] TOOL RESULT — Bash · 2026-10-26 10:18:28 UTC

```
{"stdout": "   318 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/cfg.py\n    59 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/commit.py\n   419 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/engine.py\n   138 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/figures.py\n   280 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/forecast_s2.py\n   530 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/gpu.py\n    95 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/gpu_extras.py\n   164 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/gpu_tests.py\n   343 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/labelq.py\n   187 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/outputs.py\n   128 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/prompts_s1.py\n   110 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/replication.py\n    17 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/run_s2.py\n   146 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/s0_inputs.py\n   127 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/s0_recheck.py\n    44 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/screen.py\n   118 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/supplementary.py\n   781 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/analysis/analysis.py\n    50 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/tests/gpu_smoke.py\n    35 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/tests/gpu_timing2.py\n    45 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/tests/test_analysis_smoke.py\n   122 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/tests/test_cpu.py\n   232 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/audit/rederive.py\n   125 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/audit/rederive2.py\n  4613 total\n\n[project]\nname = \"ban-route-bench\"\nversion = \"0.1.0\"\ndescription = \"Where a coding ban takes effect: CRN-coupled KV-splice route arms, one-shot vetoes and prefills on 12 frozen bench tasks (Qwen3-8B)\"\nrequires-python = \"==3.12.*\"\n# every package installed in .venv, pinned to the exact installed version (uv pip freeze; Python 3.12.14, uv 0.6.14)\ndependencies = [\n  \"accelerate==1.15.0\",\n  \"annotated-types==0.8.0\",\n  \"anyio==4.15.1\",\n  \"certifi==2026.10.19\",\n  \"charset-normalizer==3.5.2\",\n  \"contourpy==1.4.0\",\n  \"cycler==0.12.1\",\n  \"filelock==4.2.4\",\n  \"fonttools==4.67.0\",\n  \"formulaic==1.2.2\",\n  \"fsspec==2026.9.0\",\n  \"h11==0.16.0\",\n  \"hf-xet==1.7.0\",\n  \"httpcore2==2.15.1\",\n  \"httpx2==2.15.1\",\n  \"huggingface-hub==0.36.2\",\n  \"idna==3.20\",\n  \"interface-meta==2.0.1\",\n  \"jinja2==3.1.6\",\n  \"jiter==0.17.0\",\n  \"kiwisolver==1.5.1\",\n  \"loguru==0.7.3\",\n  \"markupsafe==3.0.4\",\n  \"matplotlib==3.11.2\",\n  \"mpmath==1.3.0\",\n  \"narwhals==2.27.1\",\n  \"networkx==3.7\",\n  \"numpy==2.2.6\",\n  \"nvidia-cublas-cu12==12.8.4.1\",\n  \"nvidia-cuda-cupti-cu12==12.8.90\",\n  \"nvidia-cuda-nvrtc-cu12==12.8.93\",\n  \"nvidia-cuda-runtime-cu12==12.8.90\",\n  \"nvidia-cudnn-cu12==9.10.2.21\",\n  \"nvidia-cufft-cu12==11.3.3.83\",\n  \"nvidia-cufile-cu12==1.13.1.3\",\n  \"nvidia-curand-cu12==10.3.9.90\",\n  \"nvidia-cusolver-cu12==11.7.3.90\",\n  \"nvidia-cusparse-cu12==12.5.8.93\",\n  \"nvidia-cusparselt-cu12==0.7.1\",\n  \"nvidia-nccl-cu12==2.27.3\",\n  \"nvidia-nvjitlink-cu12==12.8.93\",\n  \"nvidia-nvtx-cu12==12.8.90\",\n  \"openai==3.35.1\",\n  \"packaging==26.3\",\n  \"pandas==3.0.6\",\n  \"patsy==1.0.3\",\n  \"pillow==13.0.0\",\n  \"psutil==7.2.2\",\n  \"pydantic==2.14.1\",\n  \"pydantic-core==2.50.1\",\n  \"pyparsing==3.3.3\",\n  \"python-dateutil==2.9.0.post0\",\n  \"pyyaml==6.0.3\",\n  \"regex==2026.9.29\",\n  \"requests==2.34.2\",\n  \"safetensors==0.8.0\",\n  \"scipy==1.18.1\",\n  \"setuptools==84.2.0\",\n  \"six==1.17.0\",\n  \"sniffio==1.3.1\",\n  \"statsmodels==0.15.0\",\n  \"sympy==1.14.0\",\n  \"tenacity==9.2.1\",\n  \"tokenizers==0.22.2\",\n  \"torch==2.8.0\",\n  \"tqdm==4.70.1\",\n  \"transformers==4.57.6\",\n  \"triton==3.4.0\",\n  \"truststore==0.10.5\",\n  \"typing-extensions==4.16.0\",\n  \"typing-inspection==0.4.4\",\n  \"urllib3==2.8.0\",\n  \"wrapt==2.5.1\",\n  \"zss==1.2.0\",\n]\n\naccelerate==1.15.0\nannotated-types==0.8.0\nanyio==4.15.1\ncertifi==2026.10.19\ncharset-normalizer==3.5.2\ncontourpy==1.4.0\ncycler==0.12.1\nfilelock==4.2.4\nfonttools==4.67.0\nformulaic==1.2.2\nfsspec==2026.9.0\nh11==0.16.0\nhf-xet==1.7.0\nhttpcore2==2.15.1\nhttpx2==2.15.1\nhuggingface-hub==0.36.2\nidna==3.20\ninterface-meta==2.0.1\njinja2==3.1.6\njiter==0.17.0\nkiwisolver==1.5.1\nloguru==0.7.3\nmarkupsafe==3.0.4\nmatplotlib==3.11.2\nmpmath==1.3.0\nnarwhals==2.27.1\nnetworkx==3.7\nnumpy==2.2.6\nnvidia-cublas-cu12==12.8.4.1\nnvidia-cuda-cupti-cu12==12.8.90\nnvidia-cuda-nvrtc-cu12==12.8.93\nnvidia-cuda-runtime-cu12==12.8.90\nnvidia-cudnn-cu12==9.10.2.21\nnvidia-cufft-cu12==11.3.3.83\nnvidia-cufile-cu12==1.13.1.3\nnvidia-curand-cu12==10.3.9.90\nnvidia-cusolver-cu12==11.7.3.90\nnvidia-cusparse-cu12==12.5.8.93\nnvidia-cusparselt-cu12==0.7.1\nnvidia-nccl-cu12==2.27.3\nnvidia-nvjitlink-cu12==12.8.93\nnvidia-nvtx-cu12==12.8.90\nopenai==3.35.1\npackaging==26.3\npandas==3.0.6\npatsy==1.0.3\npillow==13.0.0\npsutil==7.2.2\npydantic==2.14.1\npydantic-core==2.50.1\npyparsing==3.3.3\npython-dateutil==2.9.0.post0\npyyaml==6.0.3\nregex==2026.9.29\nrequests==2.34.2\nsafetensors==0.8.0\nscipy==1.18.1\nsetuptools==84.2.0\nsix==1.17.0\nsniffio==1.3.1\nstatsmodels==0.15.0\nsympy==1.14.0\ntenacity==9.2.1\ntokenizers==0.22.2\ntorch==2.8.0\ntqdm==4.70.1\ntransformers==4.57.6\ntriton==3.4.0\ntruststore==0.10.5\ntyping-extensions==4.16.0\ntyping-inspection==0.4.4\nurllib3==2.8.0\nwrapt==2.5.1\nzss==1.2.0\n\n#!/usr/bin/env bash\n# Final CPU stages after the GPU queues: analysis, replication, supplementary, figures, outputs, audit, JSON checks.\nset -euo pipefail\ncd \"$(dirname \"$0\")\"\nPY=.venv/bin/python\n$PY method.py analysis\n$PY src/replication.py\n$PY src/supplementary.py\nAII_SKILLS_DIR=\"${AII_SKILLS_DIR:-}\" $PY method.py figures\n$PY method.py outputs\n$PY method.py audit\nif [ -z \"${AII_SKILLS_DIR:-}\" ]; then echo \"AII_SKILLS_DIR not set: skipping JSON mini/preview + schema validation\"; exit 0; fi\nSKILL_DIR=\"$AII_SKILLS_DIR/aii-json\"\n$SKILL_DIR/../.ability_client_venv/bin/python $SKILL_DIR/scripts/aii_json_format_mini_preview.py --input \"$(pwd)/method_out.json\" || true\n$SKILL_DIR/../.ability_client_venv/bin/python $SKILL_DIR/scripts/aii_json_validate_schema.py --format exp_gen_sol_out --file \"$(pwd)/method_out.json\"\nls -lh method_out.json full_method_out.json mini_method_out.json preview_method_out.json 2>/dev/null || true\n\n#!/usr/bin/env bash\n# Rebuild everything the manifest marks `delete`. The model weights live in the Hugging Face cache, not here.\nset -euo pipefail\ncd \"$(dirname \"$0\")\"\ncommand -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh\nuv venv .venv --python=3.12\nuv pip install --python .venv/bin/python -r requirements.txt\n# model (bf16, ~16.4 GB) at the pinned revision, into $HF_HOME / $HF_HUB_CACHE\n.venv/bin/huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218\n.venv/\n__pycache__/\n*.pyc\n*.tmp", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [16] TOOL CALL — Bash · 2026-10-26 10:18:28 UTC

```
Read the artifact README:
A=/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16; cat $A/README.md
```

### [17] TOOL RESULT — Bash · 2026-10-26 10:18:28 UTC

```
{"stdout": "# Where a coding ban takes effect: a route test on 12 frozen bench tasks (Qwen3-8B)\n\nA prompt ban (\"Do not use a hash map of seen values for this task.\") makes Qwen3-8B write a different algorithm.\nThis artifact asks **which internal route carries that effect** on the 12 frozen bench tasks of exp11, using\nexp8's HF engine (bf16, thinking off): common random numbers (CRN), inverse-CDF sampling and KV-cache splicing by\nposition class. Every arm of a CRN slot u... [truncated, 26461 chars total]
```

### [18] ASSISTANT · 2026-10-26 10:18:48 UTC

```
This is a GPU-heavy Qwen3-8B experiment whose `method.py` dispatches to stage modules. Let me inspect the output data structure (preview only) to see what a CPU demo can be built on.
```

### [19] TOOL CALL — Bash · 2026-10-26 10:18:48 UTC

```
Print structure of the preview output JSON:
A=/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16; python3 -I - "$A/preview_method_out.json" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))
def show(o, ind=0, maxd=4):
    pad = "  "*ind
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, (dict, list)):
                print(f"{pad}{k}: {type(v).__name__}({len(v)})")
                if ind < maxd: show(v, ind+1, maxd)
            else:
                s = repr(v)
                print(f"{pad}{k}: {s[:150]}")
    elif isinstance(o, list):
        if o:
            print(f"{pad}[0] of {len(o)}:")
            show(o[0], ind+1, maxd)
show(d, 0, 3)
EOF
```

### [20] TOOL RESULT — Bash · 2026-10-26 10:18:48 UTC

```
{"stdout": "metadata: dict(26)\n  method_name: 'Bench route test of prompt bans (CRN KV-splice arms, one-shot veto, prefill) in Qwen3-8B'\n  model: 'Qwen/Qwen3-8B'\n  model_revision: 'b968826d9c46dd6066d109eabc6255188de91218'\n  dtype: 'bfloat16'\n  thinking: False\n  decoding: 'T=1.0, top-p 1.0, no top-k, max 1024 new tokens, CRN inverse-CDF sampling'\n  hardware: '1 x NVIDIA L4 23 GB, 6 CPUs, 66 GB RAM'\n  baselines: 'arm a (full ban) and arm b (token-length-matched neutral twin) in the same pipeline with the same uniforms; placebo splice and knockout-mechanics con\n  gated_tasks: list(3)\n    [0] of 3:\n  gate: dict(12)\n    T03: dict(6)\n      s_a: 0.01\n      avoidance: 0.99\n      n_attempted: 100\n      n_nondefault: 99\n      n_rows: 100\n      gated: True\n    T04: dict(6)\n      s_a: 0.58\n      avoidance: 0.42000000000000004\n      n_attempted: 100\n      n_nondefault: 42\n      n_rows: 100\n      gated: False\n    T06: dict(6)\n      s_a: 0.21\n      avoidance: 0.79\n      n_attempted: 100\n      n_nondefault: 79\n      n_rows: 100\n      gated: True\n    T05: dict(6)\n      s_a: 0.17\n      avoidance: 0.83\n      n_attempted: 100\n      n_nondefault: 83\n      n_rows: 100\n      gated: True\n    T10: dict(6)\n      s_a: 0.0\n      avoidance: 1.0\n      n_attempted: 100\n      n_nondefault: 100\n      n_rows: 100\n      gated: True\n    R1: dict(6)\n      s_a: 1.0\n      avoidance: 0.0\n      n_attempted: 100\n      n_nondefault: 0\n      n_rows: 100\n      gated: False\n    T08: dict(6)\n      s_a: 0.69\n      avoidance: 0.31000000000000005\n      n_attempted: 100\n      n_nondefault: 31\n      n_rows: 100\n      gated: False\n    R3: dict(6)\n      s_a: 0.96\n      avoidance: 0.040000000000000036\n      n_attempted: 100\n      n_nondefault: 4\n      n_rows: 100\n      gated: False\n    T13: dict(6)\n      s_a: 0.41\n      avoidance: 0.5900000000000001\n      n_attempted: 100\n      n_nondefault: 59\n      n_rows: 100\n      gated: True\n    R6: dict(6)\n      s_a: 0.98\n      avoidance: 0.020000000000000018\n      n_attempted: 100\n      n_nondefault: 2\n      n_rows: 100\n      gated: False\n    T14: dict(6)\n      s_a: 0.59\n      avoidance: 0.41000000000000003\n      n_attempted: 100\n      n_nondefault: 41\n      n_rows: 100\n      gated: False\n    T11: dict(6)\n      s_a: 0.98\n      avoidance: 0.020000000000000018\n      n_attempted: 100\n      n_nondefault: 2\n      n_rows: 100\n      gated: False\n  C2a: dict(9)\n    verdict: 'DISCONFIRMED'\n    verdict_by_interval: dict(3)\n      percentile: 'DISCONFIRMED'\n      bca: 'DISCONFIRMED'\n      jackknife: 'DISCONFIRMED'\n    point: dict(6)\n      F_prompt: 0.6111111111111112\n      F_direct: 0.7439613526570049\n      I: -0.3550724637681161\n      F_prompt_mean: 0.5674887492471494\n      F_direct_mean: 0.7021613990849292\n      F_K0: 0.6207729468599033\n    intervals: dict(6)\n      F_prompt: dict(3)\n      F_direct: dict(3)\n      I: dict(3)\n      F_prompt_mean: dict(3)\n      F_direct_mean: dict(3)\n      F_K0: dict(3)\n    p_boot_F_prompt_le_half: 0.2819\n    p_boot_F_direct_ge_third: 0.99\n    per_task: dict(5)\n      T03: dict(6)\n      T06: dict(6)\n      T05: dict(6)\n      T10: dict(6)\n      T13: dict(6)\n    mixed_glm: dict(7)\n      fixed_effects_mean: dict(4)\n      fixed_effects_sd: dict(4)\n      vcp_mean: list(2)\n      probabilities_at_zero_random_effects: dict(4)\n      F_prompt_glm: 0.7382383004294235\n      F_direct_glm: 0.8876943821237946\n      note: 'descriptive sensitivity (variational Bayes); logit-scale fixed effects at zero random effects'\n    leave_one_template_out: dict(5)\n      W1: dict(6)\n      W2: dict(6)\n      W3: dict(6)\n      W4: dict(6)\n      W5: dict(6)\n  C2c: dict(9)\n    rows: list(3)\n      [0] of 3:\n        task: 'T03'\n        gated: True\n        V: 0.41000000000000003\n        class: 'HIGH_DIRECT'\n        F_direct: 0.7446808510638298\n        F_direct_ci95: list(2)\n        hit: True\n        fire_rate: 0.86\n        V_fired: 0.4186046511627907\n    n_scored: 5\n    hit_fraction: 0.8\n    spearman_rho: -0.3354101966249684\n    perm_p_one_sided: 0.30418\n    rho_task_bootstrap_ci95: list(2)\n      [0] of 2:\n    n_points: 5\n    decision: 'INCONCLUSIVE'\n    rule: 'SUPPORTED if hit fraction >= 2/3 AND rho < 0 with permutation p < 0.05; DISCONFIRMED if rho >= 0 or hit fraction < 1/2; else INCONCLUSIVE (committed \n  C2b_sensitivity: dict(4)\n    per_task: dict(0)\n    eligible: list(0)\n    n_hold: 0\n    holds_overall: None\n  prefill: dict(5)\n    T03: dict(2)\n      SIG: dict(9)\n      NEU: dict(9)\n    T06: dict(2)\n      SIG: dict(9)\n      NEU: dict(9)\n    T05: dict(2)\n      SIG: dict(9)\n      NEU: dict(9)\n    T10: dict(2)\n      SIG: dict(9)\n      NEU: dict(9)\n    T13: dict(2)\n      SIG: dict(9)\n      NEU: dict(9)\n  controls: dict(3)\n    T03: dict(8)\n      s_pl: 0.96\n      s_b_nounB: 1.0\n      diff: -0.040000000000000036\n      placebo_pass: True\n      s_K0b: 1.0\n      s_b: 0.95\n      K0b_ratio: 1.0526315789473684\n      K0b_pass: True\n    T04: dict(8)\n      s_pl: 1.0\n      s_b_nounB: 1.0\n      diff: 0.0\n      placebo_pass: True\n      s_K0b: 1.0\n      s_b: 1.0\n      K0b_ratio: 1.0\n      K0b_pass: True\n    T06: dict(8)\n      s_pl: 1.0\n      s_b_nounB: 1.0\n      diff: 0.0\n      placebo_pass: True\n      s_K0b: 1.0\n      s_b: 1.0\n      K0b_ratio: 1.0\n      K0b_pass: True\n  screen: dict(5)\n    iteration2_ban_landings: dict(2)\n      t1: dict(7)\n      t2: dict(7)\n    exp12_mechanical_crosscheck: dict(2)\n      n_runtime_ast_agree: 119\n      agreement_with_exp12_labels: 1.0\n    committed_predictions: dict(2)\n      T2_oneshot_suffices_and_lands_bf_spfa: dict(3)\n      T1_oneshot_does_not_suffice: dict(2)\n    exp8_behaviour_route: dict(2)\n      t1: dict(13)\n      t2: dict(13)\n    rounds: dict(2)\n      t1: dict(8)\n      t2: dict(8)\n  lp_readout: dict(3)\n    F_lp_prompt: 0.39749485082974134\n    F_lp_direct: 0.45067516643947486\n    note: \"descriptive companion readout (teacher-forced log-prob of the default's signature prefix)\"\n  shares: dict(12)\n    R1: dict(6)\n      K0: dict(14)\n      V1: dict(14)\n      a: dict(14)\n      b: dict(14)\n      c: dict(14)\n      d: dict(14)\n    R3: dict(6)\n      K0: dict(14)\n      V1: dict(14)\n      a: dict(14)\n      b: dict(14)\n      c: dict(14)\n      d: dict(14)\n    R6: dict(6)\n      K0: dict(14)\n      V1: dict(14)\n      a: dict(14)\n      b: dict(14)\n      c: dict(14)\n      d: dict(14)\n    T03: dict(23)\n      BAN+D25: dict(14)\n      BAN+D50: dict(14)\n      BAN+D75: dict(14)\n      BAN+NEU: dict(14)\n      BAN+SIG: dict(14)\n      K0: dict(14)\n      K0b: dict(14)\n      TWIN+D25: dict(14)\n      TWIN+D50: dict(14)\n      TWIN+D75: dict(14)\n      TWIN+NEU: dict(14)\n      TWIN+SIG: dict(14)\n      V1: dict(14)\n      a: dict(14)\n      a@r2: dict(14)\n      b: dict(14)\n      b@r2: dict(14)\n      bB: dict(14)\n      c: dict(14)\n      c@r2: dict(14)\n      d: dict(14)\n      d@r2: dict(14)\n      pl: dict(14)\n    T04: dict(9)\n      K0: dict(14)\n      K0b: dict(14)\n      V1: dict(14)\n      a: dict(14)\n      b: dict(14)\n      bB: dict(14)\n      c: dict(14)\n      d: dict(14)\n      pl: dict(14)\n    T05: dict(23)\n      BAN+D25: dict(14)\n      BAN+D50: dict(14)\n      BAN+D75: dict(14)\n      BAN+NEU: dict(14)\n      BAN+SIG: dict(14)\n      K0: dict(14)\n      K0b: dict(14)\n      TWIN+D25: dict(14)\n      TWIN+D50: dict(14)\n      TWIN+D75: dict(14)\n      TWIN+NEU: dict(14)\n      TWIN+SIG: dict(14)\n      V1: dict(14)\n      a: dict(14)\n      a@r2: dict(14)\n      b: dict(14)\n      b@r2: dict(14)\n      bB: dict(14)\n      c: dict(14)\n      c@r2: dict(14)\n      d: dict(14)\n      d@r2: dict(14)\n      pl: dict(14)\n    T06: dict(23)\n      BAN+D25: dict(14)\n      BAN+D50: dict(14)\n      BAN+D75: dict(14)\n      BAN+NEU: dict(14)\n      BAN+SIG: dict(14)\n      K0: dict(14)\n      K0b: dict(14)\n      TWIN+D25: dict(14)\n      TWIN+D50: dict(14)\n      TWIN+D75: dict(14)\n      TWIN+NEU: dict(14)\n      TWIN+SIG: dict(14)\n      V1: dict(14)\n      a: dict(14)\n      a@r2: dict(14)\n      b: dict(14)\n      b@r2: dict(14)\n      bB: dict(14)\n      c: dict(14)\n      c@r2: dict(14)\n      d: dict(14)\n      d@r2: dict(14)\n      pl: dict(14)\n    T08: dict(6)\n      K0: dict(14)\n      V1: dict(14)\n      a: dict(14)\n      b: dict(14)\n      c: dict(14)\n      d: dict(14)\n    T10: dict(23)\n      BAN+D25: dict(14)\n      BAN+D50: dict(14)\n      BAN+D75: dict(14)\n      BAN+NEU: dict(14)\n      BAN+SIG: dict(14)\n      K0: dict(14)\n      K0b: dict(14)\n      TWIN+D25: dict(14)\n      TWIN+D50: dict(14)\n      TWIN+D75: dict(14)\n      TWIN+NEU: dict(14)\n      TWIN+SIG: dict(14)\n      V1: dict(14)\n      a: dict(14)\n      a@r2: dict(14)\n      b: dict(14)\n      b@r2: dict(14)\n      bB: dict(14)\n      c: dict(14)\n      c@r2: dict(14)\n      d: dict(14)\n      d@r2: dict(14)\n      pl: dict(14)\n    T11: dict(6)\n      K0: dict(14)\n      V1: dict(14)\n      a: dict(14)\n      b: dict(14)\n      c: dict(14)\n      d: dict(14)\n    T13: dict(23)\n      BAN+D25: dict(14)\n      BAN+D50: dict(14)\n      BAN+D75: dict(14)\n      BAN+NEU: dict(14)\n      BAN+SIG: dict(14)\n      K0: dict(14)\n      K0b: dict(14)\n      TWIN+D25: dict(14)\n      TWIN+D50: dict(14)\n      TWIN+D75: dict(14)\n      TWIN+NEU: dict(14)\n      TWIN+SIG: dict(14)\n      V1: dict(14)\n      a: dict(14)\n      a@r2: dict(14)\n      b: dict(14)\n      b@r2: dict(14)\n      bB: dict(14)\n      c: dict(14)\n      c@r2: dict(14)\n      d: dict(14)\n      d@r2: dict(14)\n      pl: dict(14)\n    T14: dict(6)\n      K0: dict(14)\n      V1: dict(14)\n      a: dict(14)\n      b: dict(14)\n      c: dict(14)\n      d: dict(14)\n  engine_validation: dict(18)\n    utc: '2026-10-20T18:50:28.480042Z'\n    B: 40\n    U9_rows_written: 80\n    U1_identical_fraction: 1.0\n    U2_splice_ban_ban_equals_a: 1.0\n    U2_splice_twin_twin_equals_b: 1.0\n    U3_max_mass_under_K0: 0.0\n    U3_min_mass_without_K0: 0.5405977964401245\n    U3_n_layers: 36\n    U3_pass: True\n    U3_spandrop_vs_masked_max_abs_logit_diff: 0.34375\n    U3_rowmask_vs_masked_max_abs_logit_diff: 0.0\n    U3_spandrop_vs_masked_tv_distance: 1.1541274602677731e-07\n    U3_spandrop_pass: True\n    U9: dict(4)\n      a: dict(6)\n      b: dict(6)\n      c: dict(6)\n      d: dict(6)\n    U9_pass: True\n    U9_ordering_holds: True\n    seconds: 116.96000266075134\n  labeller_recheck: dict(4)\n    suite_t1_t2: dict(10)\n      gold_n: 144\n      gold_n_resolved: 141\n      acc_combined_vs_adjudicated: 0.9574468085106383\n      exp8_acc: 0.9645390070921985\n      within_tol: True\n      references_ok: 22\n      references_n: 22\n      references: list(3)\n      label_sources: dict(2)\n      pass: True\n    bench_all_pass: True\n    failed_tasks: list(0)\n    suite_pass: True\n  deviations: list(3)\n    [0] of 3:\n      id: 'D1'\n      what: \"Hardware: one NVIDIA L4 (23 GB; about a third of the RTX 4090's memory bandwidth) instead of the planned RTX A4500. Measured decode latency was 89 ms\n      consequence: 'Batch shape is constant within each shape class (task, cache length, first position); CRN partners of a slot always meet identical kernels (U1 = 1.00\n  extras_replication_and_depth: dict(7)\n    tasks: list(3)\n      [0] of 3:\n    pooled_r2: dict(5)\n      F_prompt: dict(2)\n      F_direct: dict(2)\n      I: dict(2)\n      F_prompt_mean: dict(2)\n      F_direct_mean: dict(2)\n    per_task_main_vs_r2: list(3)\n      [0] of 3:\n        task: 'T03'\n        F_prompt_main: 1.0\n        F_prompt_r2: 1.0\n        F_direct_main: 0.7446808510638298\n        F_direct_r2: 0.7731958762886598\n    spearman_main_vs_r2: dict(2)\n      F_prompt: 0.8947368421052632\n      F_direct: 0.8999999999999998\n    verdict_r2_same_rule: 'DISCONFIRMED'\n    controls_all: dict(6)\n      T03: dict(8)\n      T04: dict(8)\n      T06: dict(8)\n      T05: dict(8)\n      T10: dict(8)\n      T13: dict(8)\n    prefill_depth_curve: dict(5)\n      T03: dict(5)\n      T06: dict(5)\n      T05: dict(5)\n      T10: dict(5)\n      T13: dict(5)\n  supplementary: dict(7)\n    ban_failures: dict(3)\n      per_template_pooled: dict(5)\n      W4_share_of_failures: 0.2948328267477204\n      per_task: dict(12)\n    label_sources: dict(5)\n      runtime+ast: 11090\n      extraction: 271\n      judge: 939\n      runtime(ast_unknown): 104\n      agree: 626\n    n_disputed_final: 0\n    bench_judge_spend_usd: 0.0531198\n    path_judge_spend_usd: 0.052398\n    pruned_rows: 0\n    finish_reasons: dict(1)\n      fence: 13030\n  audit: dict(7)\n    n_mismatches: 0\n    U4_pass: True\n    U5_pass: True\n    U6_pass: True\n    placebo_shuffle: dict(4)\n      observed_mean_gap_b_minus_a: 0.828\n      shuffled_gap_mean: -0.0013699999999999988\n      shuffled_gap_q975: 0.05199999999999999\n      route_structure_destroyed: True\n    hash_chain_ok: True\n    ordering: dict(7)\n      commit1_last_utc: '2026-10-20T18:41:06.517778Z'\n      commit2_last_utc: '2026-10-20T18:52:25.751265Z'\n      first_ban_row_utc: '2026-10-20T18:50:55.743395Z'\n      first_bench_ban_row_utc: '2026-10-20T18:52:46.592629Z'\n      first_arm_a_row_utc: '2026-10-20T18:52:46.592629Z'\n      commit1_before_first_ban: True\n      commit2_before_first_bench_ban: True\n  prereg_amendments: list(3)\n    [0] of 3:\n      id: 'A1'\n      utc: '2026-10-20T19:00:42.790492Z'\n      file: 'src/analysis/analysis.py'\n      sha256_committed: '8879bc2a52b3957e0f2cab18687d59e381bce8bcdc8606d5f8fca1bc11776eb3'\n      sha256_after: '5006fe669ee100cecea73e7fd9aac534ebc8d2033ad3371b746228ed4bb76722'\n      change: \"iter2_ban_landings(): recount exp12's fresh-pool landings from exp12's per-row labels (same frozen exp8/exp1 suite labeller) instead of re-judging th\n      reason: 'judge budget (the suite judge costs ~USD 0.002/call); descriptive screen reference only -- no decision rule, threshold or primary statistic changed'\n      what_had_been_seen: 'ban-free S4 summaries, the first path-screen rows and the T2 engine-validation counts (U9); bench ban-arm rows existed on disk but no bench ban-arm s\n  files: dict(5)\n    samples: 'data/samples.jsonl'\n    raw: 'data/samples_raw.jsonl'\n    analysis: 'results/analysis.json'\n    commitments: 'commitments.log'\n    predictions: 'predictions/'\ndatasets: list(3)\n  [0] of 3:\n    dataset: 'route_arms'\n    examples: list(3)\n      [0] of 3:\n        input: \"task T03 | template W1 | slot k=0 | ban segment: 'Do not use a full sort for this task.' | neutral twin: 'Do not use man for this task. . .'\"\n        output: 'quickselect'\n        metadata_task: 'T03'\n        metadata_template: 'W1'\n        metadata_k: 0\n        metadata_default: 'full_sort'\n        metadata_gated: True\n        metadata_a_passed: True\n        predict_b: 'full_sort|pass'\n        predict_c: 'quickselect|pass'\n        predict_d: 'quickselect|pass'\n        predict_K0: 'quickselect|pass'", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [21] THINKING · 2026-10-26 10:18:56 UTC

```
I'll pull full example rows from every dataset and programmatically count the examples in the full file.
```

### [22] TOOL CALL — Bash · 2026-10-26 10:18:56 UTC

```
Show example rows per dataset and full-file counts:
A=/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16; python3 -I - "$A/preview_method_out.json" "$A/full_method_out.json" <<'EOF'
import json, sys
from collections import Counter
p = json.load(open(sys.argv[1]))
for ds in p["datasets"]:
    print("=== DATASET", ds["dataset"], "preview n =", len(ds["examples"]))
    ex = ds["examples"][0]
    for k, v in ex.items():
        print(f"  {k}: {repr(v)[:300]}")
f = json.load(open(sys.argv[2]))
print("\n=== FULL counts ===")
for ds in f["datasets"]:
    exs = ds["examples"]
    keys = Counter()
    for e in exs: keys.update(e.keys())
    print(ds["dataset"], len(exs))
    print("   keys:", dict(keys))
    tasks = Counter(e.get("metadata_task") for e in exs)
    print("   tasks:", dict(tasks))
EOF
```

### [23] TOOL RESULT — Bash · 2026-10-26 10:18:56 UTC

```
{"stdout": "=== DATASET route_arms preview n = 3\n  input: \"task T03 | template W1 | slot k=0 | ban segment: 'Do not use a full sort for this task.' | neutral twin: 'Do not use man for this task. . .'\"\n  output: 'quickselect'\n  metadata_task: 'T03'\n  metadata_template: 'W1'\n  metadata_k: 0\n  metadata_default: 'full_sort'\n  metadata_gated: True\n  metadata_a_passed: True\n  predict_b: 'full_sort|pass'\n  predict_c: 'quickselect|pass'\n  predict_d: 'quickselect|pass'\n  predict_K0: 'quickselect|pass'\n=== DATASET veto_sufficiency preview n = 3\n  input: \"task T03 | template W1 | slot k=0 | vetoed n-gram '    nums'\"\n  output: 'full_sort'\n  predict_V1: 'full_sort|pass'\n  predict_V1_fired: 'True'\n  metadata_fire_step: 10\n  metadata_task: 'T03'\n  metadata_template: 'W1'\n  metadata_k: 0\n  metadata_default: 'full_sort'\n=== DATASET prefill preview n = 3\n  input: 'task T03 | template W1 | slot k=0 | prefills: signature + neutral'\n  output: 'quickselect'\n  predict_BAN_SIG: 'full_sort|pass'\n  predict_TWIN_SIG: 'full_sort|pass'\n  predict_BAN_NEU: 'quickselect|pass'\n  predict_TWIN_NEU: 'full_sort|pass'\n  metadata_task: 'T03'\n  metadata_template: 'W1'\n  metadata_k: 0\n\n=== FULL counts ===\nroute_arms 1200\n   keys: {'input': 1200, 'output': 1200, 'metadata_task': 1200, 'metadata_template': 1200, 'metadata_k': 1200, 'metadata_default': 1200, 'metadata_gated': 1200, 'metadata_a_passed': 1200, 'predict_b': 1200, 'predict_c': 1200, 'predict_d': 1200, 'predict_K0': 1200}\n   tasks: {'T03': 100, 'T04': 100, 'T06': 100, 'T05': 100, 'T10': 100, 'R1': 100, 'T08': 100, 'R3': 100, 'T13': 100, 'R6': 100, 'T14': 100, 'T11': 100}\nveto_sufficiency 1200\n   keys: {'input': 1200, 'output': 1200, 'predict_V1': 1200, 'predict_V1_fired': 1200, 'metadata_fire_step': 1200, 'metadata_task': 1200, 'metadata_template': 1200, 'metadata_k': 1200, 'metadata_default': 1200}\n   tasks: {'T03': 100, 'T04': 100, 'T06': 100, 'T05': 100, 'T10': 100, 'R1': 100, 'T08': 100, 'R3': 100, 'T13': 100, 'R6': 100, 'T14': 100, 'T11': 100}\nprefill 250\n   keys: {'input': 250, 'output': 250, 'predict_BAN_SIG': 250, 'predict_TWIN_SIG': 250, 'predict_BAN_NEU': 250, 'predict_TWIN_NEU': 250, 'metadata_task': 250, 'metadata_template': 250, 'metadata_k': 250}\n   tasks: {'T03': 50, 'T06': 50, 'T05': 50, 'T10': 50, 'T13': 50}\npath_screen 200\n   keys: {'input': 200, 'output': 200, 'predict_V1': 100, 'predict_VP': 200, 'predict_OPEN': 100, 'predict_R2': 100, 'predict_R3': 100, 'metadata_task': 200, 'metadata_template': 200, 'metadata_k': 200, 'metadata_output_source': 200}\n   tasks: {'t1': 100, 't2': 100}\ncontrols_placebo_K0b 300\n   keys: {'input': 300, 'output': 300, 'predict_pl': 300, 'predict_K0b': 300, 'predict_b': 300, 'metadata_task': 300, 'metadata_template': 300, 'metadata_k': 300}\n   tasks: {'T03': 50, 'T04': 50, 'T06': 50, 'T05': 50, 'T10': 50, 'T13': 50}", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [24] ASSISTANT · 2026-10-26 10:19:12 UTC

```
The full `route_arms` dataset has 1,200 rows (12 tasks × 100 CRN slots). Now let me read the CPU analysis code (`src/analysis/analysis.py`), which is what a CPU demo can actually run.
```

### [25] TOOL CALL — Read · 2026-10-26 10:19:12 UTC

```
/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/analysis/analysis.py
```

### [26] TOOL RESULT — Read · 2026-10-26 10:19:12 UTC

```
{"type": "text", "file": {"filePath": "/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/analysis/analysis.py", "content": "#!/usr/bin/env python3\n\"\"\"S9 analysis (CPU). Committed in commit #1 before any ban sample; reads data/samples.jsonl and predictions/*.\n\n9.1 shares per task x arm (+ per template); 9.2 route fractions with a hierarchical bootstrap (task -> template ->\nCRN slot, all arms of a slot kept together), BC... [truncated, 43188 chars total]
```

### [27] THINKING · 2026-10-26 10:20:12 UTC

```
The analysis stage is CPU-only and uses per-slot labels from `route_arms`. Now I'll check `cfg.py` and the engine to see how much of the GPU method translates to a CPU notebook.
```

### [28] TOOL CALL — Read · 2026-10-26 10:20:12 UTC

```
/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/cfg.py
```

### [29] TOOL RESULT — Read · 2026-10-26 10:20:12 UTC

````
{"type": "text", "file": {"filePath": "/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/cfg.py", "content": "#!/usr/bin/env python3\n\"\"\"Shared constants, paths, frozen protocol text and small utilities for the bench route test.\n\nPorted from exp8's cfg.py (art_8_ULPE8jJQc_) with paths re-pointed to this workspace. stable_seed() and the\nu_stream() keying are byte-for-byte exp8's, so the T1/T2 screen and the engine validation reuse exp8's uniforms.\n\"\"\"\n\nfrom __future__ import annotations\n\nimport hashlib\nimport json\nimport math\nimport os\nimport resource\nimport sys\nfrom datetime import datetime, timezone\nfrom pathlib import Path\nfrom typing import Any, Iterable\n\nfrom loguru import logger\n\nROOT = Path(__file__).resolve().parents[1]\n# Upstream artifacts (read-only). Only S0 (src/s0_inputs.py) and the dataset check in src/supplementary.py read them;\n# everything used is snapshotted under inputs/ and published with this folder. ONE environment variable per artifact\n# overrides the location; otherwise the run volume's layout is used when present (ROOT = <run>/3_invention_loop/iter_3/\n# gen_art/<this>), else the published repository's sibling layout (ROOT = <repo>/round-3/experiment-16/src).\nARTIFACT_IDS = {\"exp7\": \"art_6zBfl3kDjeiP\", \"exp8\": \"art_8_ULPE8jJQc_\", \"exp9\": \"art_IVZc3TWCeE9f\",\n                \"exp11\": \"art_0ndRfWKBWclR\", \"exp12\": \"art_3iv5G76C3yoX\", \"dataset\": \"art_j3Rm_lr2nzR6\"}\n\n\ndef _upstream(env: str, run_layout: Path, published_layout: Path) -> Path:\n    if os.environ.get(env):\n        return Path(os.environ[env])\n    return run_layout if run_layout.exists() else published_layout\n\n\nEXP_DIRS = {e: _upstream(f\"BRT_{e.upper()}_DIR\", ROOT.parents[2] / \"iter_2\" / \"gen_art\" / f\"gen_art_experiment_{e[3:]}\",\n                         ROOT.parents[2] / \"round-2\" / f\"experiment-{e[3:]}\" / \"src\")\n            for e in (\"exp7\", \"exp8\", \"exp9\", \"exp11\", \"exp12\")}\n# art_j3Rm_lr2nzR6 (the declared dataset dependency, produced in another run of the same study)\nDATASET_DIR = _upstream(\"BRT_DATASET_DIR\", ROOT.parents[4] / \"run_4VFKidE1bxPG\" / \"3_invention_loop\" / \"iter_1\" / \"gen_art\"\n                        / \"gen_art_dataset_1\", ROOT.parents[2] / \"round-1\" / \"dataset-1\" / \"src\")\n\nINPUTS = ROOT / \"inputs\"\nBENCH = INPUTS / \"bench\"                 # copy of exp11 bench/ (12 frozen tasks + common/)\nE8 = INPUTS / \"exp8\"                     # copy of exp8 suite/, prompts, data, results\nE7 = INPUTS / \"exp7\"\nE9 = INPUTS / \"exp9\"\nE12 = INPUTS / \"exp12\"\nLABEL_ROOT = ROOT / \"labelling\"          # bench judge cache + spend log live here (Judge(root) layout)\nPROMPTS_DIR = ROOT / \"prompts\"\nPRED_DIR = ROOT / \"predictions\"\nDATA_DIR = ROOT / \"data\"\nTOKEN_LP_DIR = ROOT / \"token_lp\"\nRESULTS_DIR = ROOT / \"results\"\nFIG_DIR = ROOT / \"figures\"\nLOG_DIR = ROOT / \"logs\"\nWORK_DIR = ROOT / \"work\"\nCOMMIT_LOG = ROOT / \"commitments.log\"\nfor _d in (PROMPTS_DIR, PRED_DIR, DATA_DIR, TOKEN_LP_DIR, RESULTS_DIR, FIG_DIR, LOG_DIR, WORK_DIR,\n           LABEL_ROOT / \"data\", LABEL_ROOT / \"logs\"):\n    _d.mkdir(parents=True, exist_ok=True)\n\nSAMPLES = DATA_DIR / \"samples.jsonl\"          # labelled rows (protocol schema)\nRAW = DATA_DIR / \"samples_raw.jsonl\"          # raw generations (written by the GPU worker)\nSTATE = WORK_DIR / \"gpu_state.json\"\n\n# ------------------------------------------------------------------------------------------------ model\nMODEL_ID = \"Qwen/Qwen3-8B\"\nMODEL_REVISION = \"b968826d9c46dd6066d109eabc6255188de91218\"\n\n\ndef model_path() -> str:\n    env = os.environ.get(\"BRT_MODEL_PATH\")\n    if env:\n        return env\n    cache = os.environ.get(\"HF_HUB_CACHE\")\n    if cache:\n        snap = Path(cache) / \"models--Qwen--Qwen3-8B\" / \"snapshots\" / MODEL_REVISION\n        if all((snap / f\"model-0000{i}-of-00005.safetensors\").exists() for i in range(1, 6)):\n            return str(snap)\n    return MODEL_ID\n\n\ndef hf_kwargs() -> dict[str, str]:\n    return {\"revision\": MODEL_REVISION} if model_path() == MODEL_ID else {}\n\n\nN_LAYERS = 36\nIM_END = 151645\nENDOFTEXT = 151643\nMAX_NEW_TOKENS = 1024\nTEMPERATURE = 1.0\nDECODING = \"T1.0_topp1.0_topk-off_max1024_thinkoff\"\nTEMPLATE_TAIL = \"<|im_end|>\\n<|im_start|>assistant\\n<think>\\n\\n</think>\\n\\n\"\nBATCH = 20  # constant batch shape for every sampled batch (two CRN blocks of 10); see deviations\n\n# ------------------------------------------------------------------------------------------------ bench\nSTAGE_A = [\"T03\", \"T04\", \"T06\", \"T05\", \"T10\", \"R1\", \"T08\", \"R3\", \"T13\", \"R6\", \"T14\", \"T11\"]\nTASK_DIR = {\"T03\": \"T03_kth_smallest\", \"T04\": \"T04_substring_search\", \"T06\": \"T06_find_duplicate\",\n            \"T05\": \"T05_two_sum\", \"T10\": \"T10_connected_components\", \"R1\": \"R1_non_overlapping_intervals\",\n            \"T08\": \"T08_fibonacci\", \"R3\": \"R3_topological_order\", \"T13\": \"T13_merge_intervals\",\n            \"R6\": \"R6_first_last_position\", \"T14\": \"T14_top_k_frequent\", \"T11\": \"T11_longest_increasing_subsequence\"}\nDEFAULT = {\"T03\": \"full_sort\", \"T04\": \"naive\", \"T06\": \"hash_set\", \"T05\": \"hash_map\", \"T10\": \"union_find\",\n           \"R1\": \"greedy_end\", \"T08\": \"iteration\", \"R3\": \"kahn\", \"T13\": \"sort_sweep\", \"R6\": \"binary_search\",\n           \"T14\": \"sort_by_count\", \"T11\": \"quadratic_dp\"}\nPATH_TASKS = (\"t1\", \"t2\")\nPATH_DEFAULT = {\"t1\": \"bfs\", \"t2\": \"dijkstra\"}\nPATH_SUB = {\"t1\": \"dfs\", \"t2\": \"bf_spfa\"}\nALL_TASKS = STAGE_A + list(PATH_TASKS)\n\n# W1-W5 (ban, mention, neutral) verbatim from the shared protocol v2 (exp8 cfg.TEMPLATES).\nTEMPLATES: dict[str, tuple[str, str, str]] = {\n    \"W1\": (\"Do not use {X} for this task.\", \"You could use {X} for this task.\", \"Do not use {N} for this task.\"),\n    \"W2\": (\"Your solution must not rely on {X}.\", \"Your solution may rely on {X}.\", \"Your solution must not rely on {N}.\"),\n    \"W3\": (\"Avoid {X} entirely.\", \"Consider {X} first.\", \"Avoid {N} entirely.\"),\n    \"W4\": (\"{X} is not allowed here.\", \"{X} is allowed here.\", \"{N} is not allowed here.\"),\n    \"W5\": (\"Write a correct solution that does not use {X}.\", \"Write a correct solution that may use {X}.\",\n           \"Write a correct solution that does not use {N}.\"),\n}\nTEMPLATE_IDS = list(TEMPLATES.keys())\nFILLER = \" .\"  # exp7 frozen neutral-twin padding filler\nN_PER_TEMPLATE = 20\nBLOCK = 10\n\nTHRESHOLDS = {\n    \"F_confirm\": 2.0 / 3.0, \"F_ci_lower\": 0.5, \"F_direct_disconfirm\": 1.0 / 3.0,\n    \"gate_avoidance\": 0.5, \"gate_min_nondefault\": 20,\n    \"veto_low_direct\": 0.8, \"veto_high_direct\": 0.5, \"pred_low_direct_F\": 0.15, \"pred_high_direct_F\": 0.25,\n    \"veto_min_fire_rate\": 0.5, \"c2c_hit_fraction\": 2.0 / 3.0, \"c2c_disconfirm_hit\": 0.5, \"c2c_alpha\": 0.05,\n    \"ngram_presence\": 0.8, \"coveto\": 0.5, \"reemerge\": 0.2, \"screen_min_nond\": 20, \"placebo_tol\": 0.1,\n    \"c2b_eligible_V\": 0.5, \"c2b_task_share\": 2.0 / 3.0,\n}\nN_BOOT = 10000\nN_PERM = 100000\nRNG_SEED = 20261020\nJUDGE_CAP_USD = 0.15  # per judge family (bench j1 + exp8 suite judge); total <= USD 0.30\nJUDGE_SOFT_USD = 0.12\nEXP8_JUDGE_MODEL = \"openai/gpt-4.1-mini\"\n\n\n# ------------------------------------------------------------------------------------------------ utils\ndef setup_logging(name: str) -> None:\n    logger.remove()\n    logger.add(sys.stdout, level=\"INFO\", format=\"{time:HH:mm:ss}|{level:<7}|{message}\")\n    logger.add(str(LOG_DIR / f\"{name}.log\"), rotation=\"30 MB\", level=\"DEBUG\")\n\n\ndef set_ram_limit(gb: float) -> None:\n    lim = int(gb * 1024 ** 3)\n    try:\n        resource.setrlimit(resource.RLIMIT_AS, (lim, lim))\n    except (ValueError, OSError) as e:\n        logger.warning(f\"could not set RLIMIT_AS: {e}\")\n\n\ndef container_ram_gb() -> float | None:\n    for p in (\"/sys/fs/cgroup/memory.max\", \"/sys/fs/cgroup/memory/memory.limit_in_bytes\"):\n        try:\n            v = Path(p).read_text().strip()\n            if v != \"max\" and int(v) < 1_000_000_000_000:\n                return int(v) / 1e9\n        except (FileNotFoundError, ValueError):\n            pass\n    return None\n\n\ndef detect_cpus() -> int:\n    try:\n        parts = Path(\"/sys/fs/cgroup/cpu.max\").read_text().split()\n        if parts[0] != \"max\":\n            return math.ceil(int(parts[0]) / int(parts[1]))\n    except (FileNotFoundError, ValueError):\n        pass\n    try:\n        q = int(Path(\"/sys/fs/cgroup/cpu/cpu.cfs_quota_us\").read_text())\n        p = int(Path(\"/sys/fs/cgroup/cpu/cpu.cfs_period_us\").read_text())\n        if q > 0:\n            return math.ceil(q / p)\n    except (FileNotFoundError, ValueError):\n        pass\n    try:\n        return len(os.sched_getaffinity(0))\n    except (AttributeError, OSError):\n        return os.cpu_count() or 1\n\n\ndef utc_now() -> str:\n    return datetime.now(timezone.utc).strftime(\"%Y-%m-%dT%H:%M:%S.%fZ\")\n\n\ndef sha256_text(s: str) -> str:\n    return hashlib.sha256(s.encode(\"utf-8\")).hexdigest()\n\n\ndef sha256_file(p: Path) -> str:\n    h = hashlib.sha256()\n    with open(p, \"rb\") as fh:\n        for chunk in iter(lambda: fh.read(1 << 20), b\"\"):\n            h.update(chunk)\n    return h.hexdigest()\n\n\ndef stable_seed(*parts: Any) -> int:\n    \"\"\"exp8: deterministic 63-bit seed from arbitrary parts (sha256 of their '|'-joined repr).\"\"\"\n    return int(hashlib.sha256(\"|\".join(str(p) for p in parts).encode()).hexdigest(), 16) % (2 ** 63)\n\n\ndef read_jsonl(p: Path) -> list[dict[str, Any]]:\n    if not Path(p).exists():\n        return []\n    out = []\n    with open(p) as fh:\n        for line in fh:\n            line = line.strip()\n            if line:\n                try:\n                    out.append(json.loads(line))\n                except json.JSONDecodeError:\n                    logger.warning(f\"skipping a corrupt line in {p}\")\n    return out\n\n\ndef write_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:\n    p = Path(p)\n    p.parent.mkdir(parents=True, exist_ok=True)\n    tmp = p.with_suffix(p.suffix + \".tmp\")\n    with open(tmp, \"w\") as fh:\n        for r in rows:\n            fh.write(json.dumps(r, default=_json_default) + \"\\n\")\n    tmp.replace(p)\n\n\ndef append_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:\n    with open(p, \"a\") as fh:\n        for r in rows:\n            fh.write(json.dumps(r, default=_json_default) + \"\\n\")\n        fh.flush()\n\n\ndef _json_default(o: Any) -> Any:\n    try:\n        import numpy as np\n\n        if isinstance(o, np.integer):\n            return int(o)\n        if isinstance(o, np.floating):\n            return None if not np.isfinite(o) else float(o)\n        if isinstance(o, np.ndarray):\n            return o.tolist()\n        if isinstance(o, np.bool_):\n            return bool(o)\n    except ImportError:\n        pass\n    if isinstance(o, Path):\n        return str(o)\n    if isinstance(o, (set, frozenset)):\n        return sorted(o)\n    if isinstance(o, tuple):\n        return list(o)\n    raise TypeError(f\"not JSON serialisable: {type(o)}\")\n\n\ndef _finite(o: Any) -> Any:\n    if isinstance(o, float):\n        return o if math.isfinite(o) else None\n    if isinstance(o, dict):\n        return {str(k): _finite(v) for k, v in o.items()}\n    if isinstance(o, (list, tuple)):\n        return [_finite(v) for v in o]\n    return o\n\n\ndef write_json(p: Path, obj: Any, indent: int | None = 1) -> None:\n    p = Path(p)\n    p.parent.mkdir(parents=True, exist_ok=True)\n    tmp = p.with_suffix(p.suffix + \".tmp\")\n    tmp.write_text(json.dumps(_finite(obj), indent=indent, default=_json_default))\n    tmp.replace(p)\n\n\ndef read_json(p: Path) -> Any:\n    return json.loads(Path(p).read_text())\n\n\ndef wilson_ci(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:\n    if n == 0:\n        return (float(\"nan\"), float(\"nan\"))\n    p = k / n\n    den = 1 + z * z / n\n    c = (p + z * z / (2 * n)) / den\n    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den\n    return (max(0.0, c - h), min(1.0, c + h))\n\n\ndef cap_first(s: str) -> str:\n    return s[:1].upper() + s[1:] if s else s\n\n\ndef chat_ids(tok: Any, user_text: str) -> list[int]:\n    s = chat_text(tok, user_text)\n    return list(tok(s, add_special_tokens=False).input_ids)\n\n\ndef chat_text(tok: Any, user_text: str) -> str:\n    s = tok.apply_chat_template([{\"role\": \"user\", \"content\": user_text}], tokenize=False,\n                                add_generation_prompt=True, enable_thinking=False)\n    assert s.endswith(TEMPLATE_TAIL), repr(s[-80:])\n    return s\n\n\ndef resp_ids(tok: Any, code: str) -> list[int]:\n    \"\"\"Frozen protocol: resp(code) = tokens of '```python\\\\n' + code.rstrip('\\\\n') + '\\\\n```'.\"\"\"\n    return list(tok(\"```python\\n\" + code.rstrip(\"\\n\") + \"\\n```\", add_special_tokens=False).input_ids)\n\n\ndef default_of(task: str) -> str:\n    return PATH_DEFAULT[task] if task in PATH_TASKS else DEFAULT[task]\n", "numLines": 319, "startLine": 1, "totalLines": 319}}
````

### [30] TOOL CALL — Read · 2026-10-26 10:20:12 UTC

```
/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/engine.py
```

### [31] TOOL RESULT — Read · 2026-10-26 10:20:12 UTC

````
{"type": "text", "file": {"filePath": "/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/engine.py", "content": "#!/usr/bin/env python3\n\"\"\"HF engine for Qwen3-8B bf16, ported from exp8's engine.py (art_8_ULPE8jJQc_) and extended.\n\nKept from exp8 unchanged: knockout-capable SDPA attention 'ko_sdpa' (+ eager twin for the knockout test), prefill(),\nsplice(), replace_positions(), teacher-forced score() at batch 1, u_stream() keyed by exp8's stable_seed, the\ninverse-CDF common-random-numbers draw (vocabulary order, float64 CDF) and unpruned constant-shape batches.\n\nExtensions (this artifact):\n- per-row knockout: sample() takes a per-row condition-span mask; a batch holding any knockout row passes one\n  explicit boolean attention mask (all-True on the other rows); batches without knockout rows run stock SDPA, so the\n  non-knockout arms (a, b, c, d, V1, ...) are bit-identical whenever their inputs are;\n- token vetoes: one-shot (mask the n-gram's completing id at its first completion only) and persistent (mask every\n  completing id of every masked n-gram at every step). A masked draw is redrawn from the renormalised distribution\n  with a FRESH independent uniform from a separate stream ('veto' key), never the conditioning uniform; an unmasked\n  draw is kept, so a vetoed row equals its unvetoed CRN twin up to the firing step;\n- fence stop: a row is finished once its first fenced code block is closed (the labeller extracts exactly that\n  block, so later tokens cannot change the label) -- this only shortens generation.\n\"\"\"\n\nfrom __future__ import annotations\n\nimport contextlib\nimport gc\nimport math\nimport re\nimport time\nfrom typing import Any, Callable, Iterator\n\nimport numpy as np\nimport torch\nfrom loguru import logger\n\nfrom cfg import ENDOFTEXT, IM_END, MAX_NEW_TOKENS, hf_kwargs, model_path, stable_seed\n\nKO: dict[str, Any] = {\"active\": False, \"p0\": 0, \"p1\": 0, \"P\": 0, \"g_lo\": 0, \"g_hi\": 10 ** 9, \"layers\": None,\n                      \"rowmask\": None}\nRECORD: dict[str, Any] = {\"on\": False, \"weights\": {}}\n_REGISTERED = False\n\n# bench extractor (exp11 harness.FENCE_RE) and exp8 suite extractor (closed python block)\nBENCH_FENCE = re.compile(r\"```[ \\t]*(?:python3?|py|Python)?[ \\t]*\\n(.*?)```\", re.S)\nPATH_FENCE = re.compile(r\"```(?:python|py|Python|python3)[ \\t]*\\n(.*?)```\", re.S)\n\n\ndef fence_closed_bench(text: str) -> bool:\n    return BENCH_FENCE.search(text) is not None\n\n\ndef fence_closed_path(text: str) -> bool:\n    m = PATH_FENCE.search(text)\n    return bool(m and m.group(1).strip())\n\n\n# ------------------------------------------------------------------------------------------------ attention\ndef _ko_on(module: Any) -> bool:\n    return bool(KO[\"active\"]) and (KO[\"layers\"] is None or module.layer_idx in KO[\"layers\"])\n\n\ndef _ko_allowed(q_len: int, k_len: int, device: torch.device) -> torch.Tensor:\n    offset = k_len - q_len\n    qpos = torch.arange(offset, k_len, device=device)\n    kpos = torch.arange(k_len, device=device)\n    allowed = kpos[None, :] <= qpos[:, None]\n    g = qpos - int(KO[\"P\"])\n    qblock = (g >= int(KO[\"g_lo\"])) & (g < int(KO[\"g_hi\"]))\n    kblock = (kpos >= int(KO[\"p0\"])) & (kpos < int(KO[\"p1\"]))\n    return allowed & ~(qblock[:, None] & kblock[None, :])\n\n\ndef _combine(allowed: torch.Tensor, attention_mask: torch.Tensor | None, k_len: int) -> torch.Tensor:\n    allowed = allowed[None, None]\n    if attention_mask is not None:\n        am = attention_mask[:, :, :, :k_len]\n        if am.dtype == torch.bool:\n            allowed = allowed & am\n        else:\n            allowed = allowed & (am == 0)\n    return allowed\n\n\ndef ko_sdpa(module, query, key, value, attention_mask, **kwargs):\n    from transformers.integrations.sdpa_attention import sdpa_attention_forward\n\n    rm = KO.get(\"rowmask\")\n    if rm is not None:  # sampling: one explicit [B,1,q,k] boolean mask for every layer (q = 1 at decode)\n        kwargs.pop(\"is_causal\", None)\n        return sdpa_attention_forward(module, query, key, value, rm[:, :, :, :key.shape[2]], is_causal=False, **kwargs)\n    if _ko_on(module):\n        q_len, k_len = query.shape[2], key.shape[2]\n        allowed = _combine(_ko_allowed(q_len, k_len, query.device), attention_mask, k_len)\n        kwargs.pop(\"is_causal\", None)\n        return sdpa_attention_forward(module, query, key, value, allowed, is_causal=False, **kwargs)\n    return sdpa_attention_forward(module, query, key, value, attention_mask, **kwargs)\n\n\ndef ko_eager(module, query, key, value, attention_mask, **kwargs):\n    \"\"\"Eager twin used only by the knockout-correctness test (U3); records attention probabilities.\"\"\"\n    from transformers.models.qwen3.modeling_qwen3 import eager_attention_forward\n\n    q_len, k_len = query.shape[2], key.shape[2]\n    if _ko_on(module):\n        allowed = _combine(_ko_allowed(q_len, k_len, query.device), attention_mask, k_len)\n    else:\n        base = torch.ones(q_len, k_len, dtype=torch.bool, device=query.device).tril(k_len - q_len)\n        allowed = _combine(base, attention_mask, k_len)\n    fmask = torch.zeros(allowed.shape, dtype=query.dtype, device=query.device)\n    fmask = fmask.masked_fill(~allowed, torch.finfo(query.dtype).min)\n    out, w = eager_attention_forward(module, query, key, value, fmask, **kwargs)\n    if RECORD[\"on\"]:\n        RECORD[\"weights\"][module.layer_idx] = w.detach().float().cpu()\n    return out, w\n\n\ndef register() -> None:\n    global _REGISTERED\n    if _REGISTERED:\n        return\n    from transformers import AttentionInterface\n    from transformers.masking_utils import AttentionMaskInterface, eager_mask, sdpa_mask\n\n    AttentionInterface.register(\"ko_sdpa\", ko_sdpa)\n    AttentionInterface.register(\"ko_eager\", ko_eager)\n    AttentionMaskInterface.register(\"ko_sdpa\", sdpa_mask)\n    AttentionMaskInterface.register(\"ko_eager\", eager_mask)\n    _REGISTERED = True\n\n\n@contextlib.contextmanager\ndef knockout(cfg: dict[str, Any] | None) -> Iterator[None]:\n    \"\"\"cfg: {'p0','p1','P','g_lo','g_hi','layers'} or None (no knockout). Used by score() and prefill-time tests.\"\"\"\n    old = dict(KO)\n    try:\n        if cfg is not None:\n            KO.update({\"active\": True, \"g_lo\": 0, \"g_hi\": 10 ** 9, \"layers\": None})\n            KO.update(cfg)\n        else:\n            KO[\"active\"] = False\n        yield\n    finally:\n        KO.clear()\n        KO.update(old)\n\n\ndef set_attn(model: Any, name: str) -> None:\n    model.config._attn_implementation = name\n    for m in model.modules():\n        if hasattr(m, \"config\") and m.config is not model.config and hasattr(m.config, \"_attn_implementation\"):\n            m.config._attn_implementation = name\n\n\ndef load_model(vram_fraction: float = 0.95):\n    from transformers import AutoModelForCausalLM, AutoTokenizer\n\n    register()\n    t0 = time.time()\n    tok = AutoTokenizer.from_pretrained(model_path(), **hf_kwargs())\n    model = AutoModelForCausalLM.from_pretrained(model_path(), dtype=torch.bfloat16, attn_implementation=\"ko_sdpa\",\n                                                 **hf_kwargs(), device_map={\"\": 0})\n    model.eval()\n    torch.cuda.set_per_process_memory_fraction(vram_fraction, 0)\n    free, total = torch.cuda.mem_get_info(0)\n    logger.info(f\"HF model loaded in {time.time() - t0:.0f}s; attn={model.config._attn_implementation}; \"\n                f\"free VRAM {free / 1e9:.1f}/{total / 1e9:.1f} GB\")\n    return tok, model\n\n\n# ------------------------------------------------------------------------------------------------ caches\ndef _kv_list(cache: Any) -> list[tuple[torch.Tensor, torch.Tensor]]:\n    if hasattr(cache, \"layers\"):\n        return [(L.keys, L.values) for L in cache.layers]\n    return list(zip(cache.key_cache, cache.value_cache))\n\n\ndef build_cache(kv: list[tuple[torch.Tensor, torch.Tensor]], batch: int = 1):\n    from transformers.cache_utils import DynamicCache\n\n    cache = DynamicCache()\n    for l, (K, V) in enumerate(kv):\n        if K.shape[0] != batch:\n            K = K.expand(batch, -1, -1, -1)\n            V = V.expand(batch, -1, -1, -1)\n        cache.update(K.contiguous(), V.contiguous(), l)\n    return cache\n\n\n@torch.no_grad()\ndef prefill(model: Any, ids: list[int]) -> dict[str, Any]:\n    \"\"\"Returns {'kv': per-layer (K, V) [1, 8, P, 128] on GPU, 'r_logits': float32 [V], 'P'}.\"\"\"\n    from transformers.cache_utils import DynamicCache\n\n    inp = torch.tensor([ids], device=model.device)\n    cache = DynamicCache()\n    out = model.model(input_ids=inp, past_key_values=cache, use_cache=True)\n    r_logits = model.lm_head(out.last_hidden_state[:, -1]).float()[0]\n    kv = [(K.clone(), V.clone()) for K, V in _kv_list(cache)]\n    del cache, out\n    return {\"kv\": kv, \"r_logits\": r_logits, \"P\": len(ids)}\n\n\ndef splice(kv_a: list, kv_b: list, cut: int) -> list:\n    \"\"\"Positions [0, cut) from A and [cut, P) from B, every layer.\"\"\"\n    return [(torch.cat([Ka[:, :, :cut], Kb[:, :, cut:]], dim=2), torch.cat([Va[:, :, :cut], Vb[:, :, cut:]], dim=2))\n            for (Ka, Va), (Kb, Vb) in zip(kv_a, kv_b)]\n\n\ndef drop_span(kv: list, p0: int, p1: int) -> list:\n    \"\"\"K0 without a mask: remove the condition span [p0, p1) from every layer's cache. Keys carry their RoPE rotation\n    from prefill and generated queries keep position ids P + step, so attention of every generated query over the\n    remaining keys equals exp8's masked knockout (softmax renormalises over the unmasked keys) -- see test U3.\"\"\"\n    return [(torch.cat([K[:, :, :p0], K[:, :, p1:]], dim=2), torch.cat([V[:, :, :p0], V[:, :, p1:]], dim=2))\n            for K, V in kv]\n\n\ndef replace_positions(kv_base: list, kv_src: list, positions: list[int]) -> list:\n    out = []\n    idx = torch.tensor(positions, device=kv_base[0][0].device)\n    for (Kb, Vb), (Ks, Vs) in zip(kv_base, kv_src):\n        K, V = Kb.clone(), Vb.clone()\n        K[:, :, idx] = Ks[:, :, idx]\n        V[:, :, idx] = Vs[:, :, idx]\n        out.append((K, V))\n    return out\n\n\n# ------------------------------------------------------------------------------------------------ scoring\n@torch.no_grad()\ndef _token_logprobs(model: Any, h: torch.Tensor, tgt: torch.Tensor, chunk: int = 256) -> torch.Tensor:\n    out = []\n    for i in range(0, h.shape[0], chunk):\n        logits = model.lm_head(h[i:i + chunk]).float()\n        out.append(torch.log_softmax(logits, dim=-1).gather(-1, tgt[i:i + chunk, None])[:, 0])\n    return torch.cat(out) if out else torch.zeros(0, device=h.device)\n\n\n@torch.no_grad()\ndef score(model: Any, arm: dict[str, Any], seqs: list[list[int]], ko: dict[str, Any] | None = None) -> list[np.ndarray]:\n    \"\"\"exp8: teacher-forced per-token log-probs of each sequence placed after the arm's prompt cache, batch 1.\n    Token 0 is scored with the arm's R logits; token t >= 1 with the hidden state at position P + t - 1.\"\"\"\n    kv, r_logits = arm[\"kv\"], arm[\"r_logits\"]\n    P = kv[0][0].shape[2]\n    r_lp = torch.log_softmax(r_logits.float(), dim=-1)\n    res = []\n    for s in seqs:\n        T = len(s)\n        inp = torch.tensor([s], device=model.device)\n        cache = build_cache(kv, 1)\n        pos = torch.arange(P, P + T, device=model.device)[None]\n        kcfg = None if ko is None else {**ko, \"P\": P}\n        with knockout(kcfg):\n            h = model.model(input_ids=inp, past_key_values=cache, position_ids=pos, use_cache=True).last_hidden_state\n        lp = _token_logprobs(model, h[0, :T - 1], inp[0, 1:T])\n        first = r_lp[s[0]].reshape(1)\n        res.append(torch.cat([first, lp]).float().cpu().numpy())\n        del cache, h, inp\n    return res\n\n\n# ------------------------------------------------------------------------------------------------ sampling\ndef u_stream(*key: Any, n: int = MAX_NEW_TOKENS) -> np.ndarray:\n    return np.random.Generator(np.random.PCG64(stable_seed(*key))).random(n)\n\n\ndef _inverse_cdf(probs: torch.Tensor, u: torch.Tensor) -> torch.Tensor:\n    cdf = probs.cumsum(dim=-1)\n    cdf = cdf / cdf[:, -1:]\n    tok = torch.searchsorted(cdf, u[:, None].to(cdf.dtype)).squeeze(-1)\n    return tok.clamp_(max=probs.shape[-1] - 1)\n\n\ndef _completing_ids(gen: list[int], ngrams: list[list[int]]) -> set[int]:\n    \"\"\"Ids that would complete any n-gram given the row's generated tail.\"\"\"\n    out = set()\n    for g in ngrams:\n        n = len(g)\n        if n == 1 or (len(gen) >= n - 1 and gen[len(gen) - (n - 1):] == g[:-1]):\n            out.add(int(g[-1]))\n    return out\n\n\n@torch.no_grad()\ndef sample(model: Any, rows: list[dict[str, Any]], max_new: int = MAX_NEW_TOKENS, temperature: float = 1.0,\n           tick_ids: set[int] | None = None, decode: Callable[[list[int]], str] | None = None,\n           prune_after: int | None = None) -> list[dict[str, Any]]:\n    \"\"\"rows: [{'kv': per-layer (K,V) [1,8,P,128], 'r_logits': [V], 'u': np.ndarray[max_new],\n               optional 'u2': np.ndarray (veto redraw stream), 'veto': {'mode': 'oneshot'|'persistent',\n               'ngrams': [[ids]]}, 'ko': (p0, p1) or None, 'stop': 'bench'|'path'|None, 'prefix_text': str}]\n    All rows share P. One uniform per (row, step); token = first index whose CDF >= u. Finished rows stay in the batch\n    (fed <|im_end|>) so the shape is constant; prune_after (memory guard) drops finished rows after that step.\"\"\"\n    B = len(rows)\n    P = rows[0][\"kv\"][0][0].shape[2]          # cache length (shorter than the prompt for span-dropped K0 rows)\n    pos0 = int(rows[0].get(\"pos0\", P))        # position id of the first generated token (= prompt length)\n    assert all(r[\"kv\"][0][0].shape[2] == P and int(r.get(\"pos0\", P)) == pos0 for r in rows)\n    dev = model.device\n    kv = [(torch.cat([r[\"kv\"][l][0] for r in rows], 0), torch.cat([r[\"kv\"][l][1] for r in rows], 0))\n          for l in range(len(rows[0][\"kv\"]))]\n    cache = build_cache(kv, B)\n    del kv\n    # explicit per-row mask only in batches that hold knockout rows (an explicit mask disables SDPA's native GQA\n    # path, so knockout batches run a different kernel -- K0 is CRN-coupled to the other arms only approximately,\n    # exactly as in exp8); every other batch runs stock SDPA with no mask\n    rowmask = None\n    if any(r.get(\"ko\") for r in rows):\n        rowmask = torch.ones((B, 1, 1, P + max_new + 1), dtype=torch.bool, device=dev)\n        for i, r in enumerate(rows):\n            if r.get(\"ko\"):\n                p0, p1 = r[\"ko\"]\n                rowmask[i, :, :, p0:p1] = False\n    U = torch.tensor(np.stack([r[\"u\"][:max_new] for r in rows]), dtype=torch.float64, device=dev)\n    logits = torch.stack([r[\"r_logits\"] for r in rows]).double()\n    alive = list(range(B))\n    toks: list[list[int]] = [[] for _ in range(B)]\n    lps: list[list[float]] = [[] for _ in range(B)]\n    finish = [\"length\"] * B\n    done: set[int] = set()\n    veto = [r.get(\"veto\") for r in rows]\n    fired = [False] * B\n    fire_step: list[int | None] = [None] * B\n    n_redraw = [0] * B\n    redraw_steps: list[list[int]] = [[] for _ in range(B)]\n    n_compl = [0] * B\n    pruned_at = None\n    step = 0\n    while True:\n        probs = torch.softmax(logits / temperature, dim=-1)\n        nxt_t = _inverse_cdf(probs, U[alive, step])\n        nxt = nxt_t.tolist()\n        # vetoes (rare events; handled per row on the CPU side)\n        for j, r in enumerate(alive):\n            v = veto[r]\n            if v is None or r in done:\n                continue\n            comp = _completing_ids(toks[r], v[\"ngrams\"])\n            if not comp or nxt[j] not in comp:\n                continue\n            n_compl[r] += 1\n            if v[\"mode\"] == \"oneshot\":\n                if fired[r]:\n                    continue\n                mask_ids = {nxt[j]}\n            else:\n                mask_ids = comp\n            p = probs[j].clone()\n            p[list(mask_ids)] = 0.0\n            if float(p.sum()) <= 0:\n                continue\n            u2 = float(rows[r][\"u2\"][n_redraw[r]])\n            nxt[j] = int(_inverse_cdf((p / p.sum())[None], torch.tensor([u2], dtype=torch.float64, device=dev))[0])\n            n_redraw[r] += 1\n            redraw_steps[r].append(step)\n            if not fired[r]:\n                fired[r] = True\n                fire_step[r] = step\n        nxt_dev = torch.tensor(nxt, device=dev)\n        plp = torch.log(probs.gather(-1, nxt_dev[:, None])[:, 0]).tolist()\n        keep = []\n        for j, (r, t) in enumerate(zip(alive, nxt)):\n            if r in done:\n                continue\n            toks[r].append(int(t))\n            lps[r].append(float(plp[j]))\n            if t in (IM_END, ENDOFTEXT):\n                finish[r] = \"stop\"\n                done.add(r)\n                continue\n            st = rows[r].get(\"stop\")\n            if st and tick_ids is not None and decode is not None and int(t) in tick_ids:\n                text = rows[r].get(\"prefix_text\", \"\") + decode(toks[r])\n                if (fence_closed_bench(text) if st == \"bench\" else fence_closed_path(text)):\n                    finish[r] = \"fence\"\n                    done.add(r)\n                    continue\n            if len(toks[r]) < max_new:\n                keep.append(j)\n            else:\n                done.add(r)\n        if not keep:\n            break\n        if prune_after is not None and step >= prune_after and len(keep) < len(alive):\n            idx = torch.tensor(keep, device=dev)\n            if hasattr(cache, \"batch_select_indices\"):\n                cache.batch_select_indices(idx)\n            else:\n                kvn = [(K[idx], V[idx]) for K, V in _kv_list(cache)]\n                cache = build_cache(kvn, len(keep))\n            if rowmask is not None:\n                rowmask = rowmask[idx]\n            alive = [alive[j] for j in keep]\n            nxt = [nxt[j] for j in keep]\n            if pruned_at is None:\n                pruned_at = step\n        else:\n            nxt = [IM_END if r in done else t for r, t in zip(alive, nxt)]\n        inp = torch.tensor(nxt, device=dev)[:, None]\n        pos = torch.full((len(alive), 1), pos0 + step, device=dev, dtype=torch.long)\n        KO[\"rowmask\"] = rowmask\n        try:\n            h = model.model(input_ids=inp, past_key_values=cache, position_ids=pos, use_cache=True).last_hidden_state\n        finally:\n            KO[\"rowmask\"] = None\n        logits = model.lm_head(h[:, -1]).double()\n        step += 1\n    del cache\n    return [{\"token_ids\": toks[r], \"finish_reason\": finish[r], \"n_tokens\": len(toks[r]),\n             \"logprob_sum\": float(np.sum(lps[r])), \"veto_fired\": fired[r], \"fire_step\": fire_step[r],\n             \"n_redraws\": n_redraw[r], \"redraw_steps\": redraw_steps[r], \"n_completions_drawn\": n_compl[r],\n             \"pruned_at\": pruned_at, \"steps\": step} for r in range(B)]\n\n\ndef free(*objs: Any) -> None:\n    for o in objs:\n        del o\n    gc.collect()\n    torch.cuda.empty_cache()\n\n\ndef logmeanexp(x: np.ndarray) -> float:\n    x = np.asarray(x, dtype=np.float64)\n    m = np.max(x)\n    return float(m + math.log(np.mean(np.exp(x - m))))\n", "numLines": 420, "startLine": 1, "totalLines": 420}}
````

### [32] THINKING · 2026-10-26 10:20:54 UTC

```
I'll check the available hardware and shared HF cache, review the prompt records, and look at how `gpu.py` builds arms c/d/K0 and the gate, since the engine's HF/torch code only depends on `model.device` and could run on CPU with a smaller Qwen3 model.
```

### [33] TOOL CALL — Bash · 2026-10-26 10:20:54 UTC

```
Check GPU, CPU, RAM and cached HF models:
nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv 2>&1 | head -5; echo "---"; nproc; free -g | head -2; echo "--- HF cache:"; echo "HF_HOME=$HF_HOME HF_HUB_CACHE=$HF_HUB_CACHE"; ls "$HF_HUB_CACHE" 2>/dev/null | head -50; du -sh "$HF_HUB_CACHE"/models--Qwen* 2>/dev/null
```

### [34] TOOL RESULT — Bash · 2026-10-26 10:20:54 UTC

```
{"stdout": "/bin/bash: line 1: nvidia-smi: command not found\n---\n2\n               total        used        free      shared  buff/cache   available\nMem:             755          43         173           0         543         711\n--- HF cache:\nHF_HOME=/ai-inventor/aii_data/runs/run_jSassd-YWLVC/.shared_cache/hf HF_HUB_CACHE=/ai-inventor/aii_data/runs/run_jSassd-YWLVC/.shared_cache/hf/hub\nmodels--Qwen--Qwen3-0.6B\nmodels--Qwen--Qwen3-8B\n1.5G\t/ai-inventor/aii_data/runs/run_jSassd-YWLVC/.shared_cache/hf/hub/models--Qwen--Qwen3-0.6B\n20M\t/ai-inventor/aii_data/runs/run_jSassd-YWLVC/.shared_cache/hf/hub/models--Qwen--Qwen3-8B", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [35] TOOL CALL — Bash · 2026-10-26 10:20:54 UTC

```
Locate arm construction and gate code in gpu.py:
A=/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16; grep -n "splice\|drop_span\|def \|gate\|p0\|p1" $A/src/gpu.py | head -120
```

### [36] TOOL RESULT — Bash · 2026-10-26 10:20:54 UTC

```
{"stdout": "2:\"\"\"GPU worker: S3 tests, S4 ban-free arms, commit #2, S6 full ban + route arms, gate, K0, prefills, screen, S8.\n8:K0 / K0b drop the condition span from the cache (engine.drop_span), so they form their own class.\n30:from engine import drop_span, load_model, prefill, sample, score, splice, u_stream\n37:def u_key(task: str, w: str, k: int) -> tuple:\n42:    def __init__(self, B: int, deadline: float | None, prune_after: int | None) -> None:\n58:    def decode(self, ids: list[int]) -> str:\n61:    def remaining(self) -> float:\n64:    def pre(self, ids: list[int]) -> dict[str, Any]:\n70:    def clear(self) -> None:\n76:    def prefix_ids(self, task: str, pf: str) -> list[int]:\n85:    def shape_of(self, task: str, w: str, arm: str) -> tuple[int, int]:\n88:        P, p0, p1 = b[\"P\"], b[\"p0\"], b[\"p1\"]\n90:            return P - (p1 - p0), P\n96:    def arm_state(self, task: str, w: str, arm: str) -> dict[str, Any]:\n102:        P, p0, p1 = ban[\"P\"], ban[\"p0\"], ban[\"p1\"]\n108:            st = {\"kv\": drop_span(s[\"kv\"], p0, p1), \"r_logits\": s[\"r_logits\"], \"ids\": ban[\"ids\"],\n115:            st = {\"kv\": drop_span(s[\"kv\"], p0, p1), \"r_logits\": s[\"r_logits\"], \"ids\": ta[\"ids\"],\n122:            st = {\"kv\": splice(A[\"kv\"], X[\"kv\"], p1), \"r_logits\": X[\"r_logits\"], \"ids\": ta[\"ids\"][:p1] + ban[\"ids\"][p1:],\n123:                  \"kind\": \"splice:twinA[0,p1)|ban[p1,P)+R(ban)\"}\n126:            st = {\"kv\": splice(X[\"kv\"], A[\"kv\"], p1), \"r_logits\": A[\"r_logits\"], \"ids\": ban[\"ids\"][:p1] + ta[\"ids\"][p1:],\n127:                  \"kind\": \"splice:ban[0,p1)|twinA[p1,P)+R(twinA)\"}\n130:            st = {\"kv\": splice(A[\"kv\"], Bn[\"kv\"], p1), \"r_logits\": Bn[\"r_logits\"], \"ids\": ta[\"ids\"][:p1] + tb[\"ids\"][p1:],\n131:                  \"kind\": \"splice:twinA[0,p1)|twinB[p1,P)+R(twinB)\"}\n144:    def veto_for(self, task: str, arm: str) -> dict[str, Any] | None:\n156:    def uid(self, s: dict[str, Any]) -> str:\n160:    def run_rows(self, stage: str, specs: list[dict[str, Any]], est_steps: int = 300) -> int:\n191:    def _run_batch(self, stage: str, chunk: list[dict[str, Any]], n_real: int, L: int, pos0: int,\n251:    def wait_for(self, cond: Callable[[], bool], what: str, poll: float = 15.0) -> None:\n261:    def stage_time(self, name: str, t0: float, n: int) -> None:\n269:def labelled_uids() -> dict[str, dict[str, Any]]:\n273:def all_labelled(uids: list[str]) -> bool:\n278:def share_default(rows: list[dict[str, Any]], task: str) -> tuple[int, int]:\n283:def compute_commit2(tasks: list[str]) -> dict[str, Any]:\n319:def compute_gate(tasks: list[str]) -> dict[str, Any]:\n327:                  \"gated\": bool(na and (1 - s_a) >= THRESHOLDS[\"gate_avoidance\"]\n328:                                and (na - nd) >= THRESHOLDS[\"gate_min_nondefault\"])}\n332:def specs(tasks: list[str], arm_ks: list[tuple[str, range]]) -> list[dict[str, Any]]:\n341:def run(B: int, deadline: float | None, prune_after: int | None) -> None:\n414:    # ---- gate (needs arm-a labels)\n416:    gate = compute_gate(bench)\n417:    write_json(RESULTS_DIR / \"gate.json\", gate)\n418:    gated = [t for t in bench if gate[t][\"gated\"]]\n419:    logger.info(f\"gate: gated={gated}; avoidance=\" + json.dumps({t: round(v['avoidance'], 3) for t, v in gate.items()}))\n421:    # ---- Q2: K0 on gated tasks (N = 100)\n423:    n = W.run_rows(\"Q2\", specs(gated, [(\"K0\", R20)]), est_steps=350)\n426:    # ---- Q4 (+Q7 twin references in the same batches): prefills on gated tasks, N = 50\n428:    n = W.run_rows(\"Q4\", specs(gated, [(\"BAN+SIG\", R10), (\"TWIN+SIG\", R10)]) +\n429:                   specs(gated, [(\"BAN+NEU\", R10), (\"TWIN+NEU\", R10)]), est_steps=300)\n448:    lp_readout(W, gated if gated else bench)\n451:    # ---- droppable tail, in reverse drop order: Q5 (non-gated c/d already run in S6), Q6, Q8, Q9 rest\n463:    nongated = [t for t in bench if t not in gated]\n464:    if nongated and W.remaining() > 15 * 60:\n466:        n = W.run_rows(\"Q8\", specs(nongated, [(\"K0\", R10)]), est_steps=350)\n469:        TIMING[\"decisions\"].append({\"utc\": utc_now(), \"event\": \"Q8 not run\", \"reason\": \"no non-gated task or time\"})\n475:def lp_readout(W: Worker, tasks: list[str]) -> None:\n496:            lps = score(W.model, st, [sig] + list(surv.values()), ko={\"p0\": b[\"p0\"], \"p1\": b[\"p1\"]})\n507:def survivor_openings(tok: Any, task: str) -> dict[str, list[int]]:", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [37] ASSISTANT · 2026-10-26 10:21:02 UTC

```
No GPU and only 2 CPU cores here, but `Qwen/Qwen3-0.6B` (same tokenizer family as Qwen3-8B) is already in the shared HF cache. Let me read the arm-construction and gate code in `gpu.py`.
```

### [38] TOOL CALL — Read · 2026-10-26 10:21:02 UTC

```
/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/gpu.py
```

### [39] TOOL RESULT — Read · 2026-10-26 10:21:02 UTC

```
{"type": "text", "file": {"filePath": "/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/src/gpu.py", "content": "#!/usr/bin/env python3\n\"\"\"GPU worker: S3 tests, S4 ban-free arms, commit #2, S6 full ban + route arms, gate, K0, prefills, screen, S8.\n\nBatch shape: every sampled batch has exactly B rows that share one SHAPE CLASS = (task, cache length, position of the\nfirst generated token). Rows of one class may come from different templates (W1/W2 usually have equal prompt\nlengths) and different arms; a CRN slot (task, template, k) therefore meets identical kernels in every arm of its\nclass (rows of a batch never interact). The last batch of a class is padded with duplicate rows that are discarded.\nK0 / K0b drop the condition span from the cache (engine.drop_span), so they form their own class.\nOrdering guarantees: no ban prompt is sampled before work/commit1_closed exists; no bench ban sample is drawn before\ncommit #2 (computed here from the labelled S4 rows) is in commitments.log. Resumable by row uid.\n\"\"\"\n\nfrom __future__ import annotations\n\nimport collections\nimport gc\nimport json\nimport os\nimport time\nfrom typing import Any, Callable\n\nimport numpy as np\nimport torch\nfrom loguru import logger\n\nfrom cfg import (DECODING, MAX_NEW_TOKENS, MODEL_ID, PATH_TASKS, PRED_DIR, RAW, RESULTS_DIR, SAMPLES, STAGE_A,\n                 TEMPLATE_IDS, THRESHOLDS, TOKEN_LP_DIR, WORK_DIR, append_jsonl, default_of, read_json, read_jsonl,\n                 sha256_text, stable_seed, utc_now, write_json)\nfrom commit import commit_files\nfrom engine import drop_span, load_model, prefill, sample, score, splice, u_stream\nfrom prompts_s1 import load_prompts\n\nTIMING: dict[str, Any] = {\"batches\": [], \"stages\": {}, \"decisions\": []}\nATTEMPT_EXCLUDE = (\"invalid\", \"no_code\", \"disputed\")\n\n\ndef u_key(task: str, w: str, k: int) -> tuple:\n    return (\"beh\", task, w, k)  # exp8's behaviour key: the T1/T2 screen and U9 reuse exp8's uniforms exactly\n\n\nclass Worker:\n    def __init__(self, B: int, deadline: float | None, prune_after: int | None) -> None:\n        self.B = B\n        self.deadline = deadline\n        self.prune_after = prune_after\n        self.tok, self.model = load_model(vram_fraction=0.98)\n        vocab = self.tok.convert_ids_to_tokens(list(range(len(self.tok))))\n        self.tick_ids = {i for i, s in enumerate(vocab) if s and \"`\" in s}\n        self.prompts = load_prompts()\n        self.ngrams = read_json(PRED_DIR / \"ngrams.json\")\n        self.prefills = read_json(PRED_DIR / \"prefills.json\")\n        self.done_uids = {r[\"uid\"] for r in read_jsonl(RAW)}\n        self._pre: dict[str, dict[str, Any]] = {}\n        self._arm: dict[tuple, dict[str, Any]] = {}\n        self.max_new = MAX_NEW_TOKENS\n        self.extra: dict[str, Any] = {}\n\n    def decode(self, ids: list[int]) -> str:\n        return self.tok.decode(ids, skip_special_tokens=True)\n\n    def remaining(self) -> float:\n        return float(\"inf\") if self.deadline is None else self.deadline - time.time()\n\n    def pre(self, ids: list[int]) -> dict[str, Any]:\n        key = sha256_text(\",\".join(map(str, ids)))\n        if key not in self._pre:\n            self._pre[key] = prefill(self.model, ids)\n        return self._pre[key]\n\n    def clear(self) -> None:\n        self._pre.clear()\n        self._arm.clear()\n        gc.collect()\n        torch.cuda.empty_cache()\n\n    def prefix_ids(self, task: str, pf: str) -> list[int]:\n        if pf == \"SIG\":\n            return self.prefills[task][\"signature\"][\"ids\"]\n        if pf == \"NEU\":\n            return self.prefills[task][\"neutral_ids\"]\n        if pf == \"HEAPQ\":\n            return self.prefills[task][\"heapq_prefill_ids\"]\n        raise ValueError(pf)\n\n    def shape_of(self, task: str, w: str, arm: str) -> tuple[int, int]:\n        \"\"\"(cache length, first generated position) from prompt metadata only.\"\"\"\n        b = self.prompts[(task, w, \"ban\")]\n        P, p0, p1 = b[\"P\"], b[\"p0\"], b[\"p1\"]\n        if arm in (\"K0\", \"K0b\"):\n            return P - (p1 - p0), P\n        if \"+\" in arm:\n            L = P + len(self.prefix_ids(task, arm.split(\"+\")[1]))\n            return L, L\n        return P, P\n\n    def arm_state(self, task: str, w: str, arm: str) -> dict[str, Any]:\n        key = (task, w, arm)\n        if key in self._arm:\n            return self._arm[key]\n        pr = self.prompts\n        ban, ta, tb = pr[(task, w, \"ban\")], pr[(task, w, \"twin_A\")], pr[(task, w, \"twin_B\")]\n        P, p0, p1 = ban[\"P\"], ban[\"p0\"], ban[\"p1\"]\n        if arm == \"a\":\n            s = self.pre(ban[\"ids\"])\n            st = {\"kv\": s[\"kv\"], \"r_logits\": s[\"r_logits\"], \"ids\": ban[\"ids\"], \"kind\": \"ban\"}\n        elif arm == \"K0\":\n            s = self.pre(ban[\"ids\"])\n            st = {\"kv\": drop_span(s[\"kv\"], p0, p1), \"r_logits\": s[\"r_logits\"], \"ids\": ban[\"ids\"],\n                  \"kind\": \"ban|K0(span dropped)\", \"pos0\": P}\n        elif arm in (\"b\", \"V1\", \"VP\", \"R2\", \"R3\", \"OPEN\"):\n            s = self.pre(ta[\"ids\"])\n            st = {\"kv\": s[\"kv\"], \"r_logits\": s[\"r_logits\"], \"ids\": ta[\"ids\"], \"kind\": \"twin_A\"}\n        elif arm == \"K0b\":\n            s = self.pre(ta[\"ids\"])\n            st = {\"kv\": drop_span(s[\"kv\"], p0, p1), \"r_logits\": s[\"r_logits\"], \"ids\": ta[\"ids\"],\n                  \"kind\": \"twin_A|K0(span dropped)\", \"pos0\": P}\n        elif arm == \"bB\":\n            s = self.pre(tb[\"ids\"])\n            st = {\"kv\": s[\"kv\"], \"r_logits\": s[\"r_logits\"], \"ids\": tb[\"ids\"], \"kind\": \"twin_B\"}\n        elif arm == \"c\":\n            A, X = self.pre(ta[\"ids\"]), self.pre(ban[\"ids\"])\n            st = {\"kv\": splice(A[\"kv\"], X[\"kv\"], p1), \"r_logits\": X[\"r_logits\"], \"ids\": ta[\"ids\"][:p1] + ban[\"ids\"][p1:],\n                  \"kind\": \"splice:twinA[0,p1)|ban[p1,P)+R(ban)\"}\n        elif arm == \"d\":\n            A, X = self.pre(ta[\"ids\"]), self.pre(ban[\"ids\"])\n            st = {\"kv\": splice(X[\"kv\"], A[\"kv\"], p1), \"r_logits\": A[\"r_logits\"], \"ids\": ban[\"ids\"][:p1] + ta[\"ids\"][p1:],\n                  \"kind\": \"splice:ban[0,p1)|twinA[p1,P)+R(twinA)\"}\n        elif arm == \"pl\":\n            A, Bn = self.pre(ta[\"ids\"]), self.pre(tb[\"ids\"])\n            st = {\"kv\": splice(A[\"kv\"], Bn[\"kv\"], p1), \"r_logits\": Bn[\"r_logits\"], \"ids\": ta[\"ids\"][:p1] + tb[\"ids\"][p1:],\n                  \"kind\": \"splice:twinA[0,p1)|twinB[p1,P)+R(twinB)\"}\n        elif \"+\" in arm:\n            base, pf = arm.split(\"+\")\n            src = ban if base == \"BAN\" else ta\n            pids = self.prefix_ids(task, pf)\n            s = self.pre(src[\"ids\"] + pids)\n            st = {\"kv\": s[\"kv\"], \"r_logits\": s[\"r_logits\"], \"ids\": src[\"ids\"] + pids, \"kind\": f\"{base.lower()}+{pf.lower()}\",\n                  \"prefix_ids\": pids, \"prefix_text\": self.tok.decode(pids)}\n        else:\n            raise ValueError(arm)\n        self._arm[key] = st\n        return st\n\n    def veto_for(self, task: str, arm: str) -> dict[str, Any] | None:\n        ng = self.ngrams[task]\n        if arm == \"V1\":\n            return {\"mode\": \"oneshot\", \"ngrams\": [ng[\"ids\"]]} if ng.get(\"defined\") else None\n        if arm == \"VP\":\n            return {\"mode\": \"persistent\", \"ngrams\": [ng[\"ids\"]]} if ng.get(\"defined\") else None\n        if arm in (\"R2\", \"R3\"):\n            return {\"mode\": \"persistent\", \"ngrams\": self.extra[arm][task][\"ngrams\"]}\n        if arm == \"OPEN\":\n            return {\"mode\": \"oneshot\", \"ngrams\": [self.prefills[task][\"opening_veto\"][\"line_ids\"]]}\n        return None\n\n    def uid(self, s: dict[str, Any]) -> str:\n        return f\"{s['task']}|{s['arm']}|{s['w']}|{s['k']}\"\n\n    # -------------------------------------------------------------------------------------------- batches\n    def run_rows(self, stage: str, specs: list[dict[str, Any]], est_steps: int = 300) -> int:\n        todo = [s for s in specs if self.uid(s) not in self.done_uids]\n        if not todo:\n            return 0\n        groups: dict[tuple, list[dict[str, Any]]] = collections.OrderedDict()\n        for s in todo:\n            L, pos0 = self.shape_of(s[\"task\"], s[\"w\"], s[\"arm\"])\n            groups.setdefault((s[\"task\"], L, pos0), []).append(s)\n        n = 0\n        cur_task = None\n        for (task, L, pos0), lst in groups.items():\n            if cur_task is not None and task != cur_task:\n                self.clear()\n                # whole tasks only: stop before a task whose batches cannot finish in the remaining budget\n                n_b = sum(-(-len(v) // self.B) for (t2, _, _), v in groups.items() if t2 == task)\n                need = n_b * est_steps * 0.105\n                if self.remaining() < need:\n                    TIMING[\"decisions\"].append({\"utc\": utc_now(), \"event\": \"stage truncated\", \"stage\": stage,\n                                                \"skipped_from_task\": task, \"need_s\": need, \"remaining_s\": self.remaining()})\n                    logger.warning(f\"[{stage}] stopping before {task}: need ~{need:.0f}s, have {self.remaining():.0f}s\")\n                    break\n            cur_task = task\n            for i in range(0, len(lst), self.B):\n                chunk = lst[i:i + self.B]\n                n_real = len(chunk)\n                chunk = chunk + [dict(chunk[-1], dup=True) for _ in range(self.B - n_real)]\n                self._run_batch(stage, chunk, n_real, L, pos0)\n                n += n_real\n        self.clear()\n        return n\n\n    def _run_batch(self, stage: str, chunk: list[dict[str, Any]], n_real: int, L: int, pos0: int,\n                   prune_after: int | None = None) -> None:\n        rows, meta = [], []\n        for s in chunk:\n            st = self.arm_state(s[\"task\"], s[\"w\"], s[\"arm\"])\n            assert st[\"kv\"][0][0].shape[2] == L and st.get(\"pos0\", L) == pos0, (s, L, pos0)\n            uk = u_key(s[\"task\"], s[\"w\"], s[\"k\"])\n            veto = self.veto_for(s[\"task\"], s[\"arm\"])\n            rows.append({\"kv\": st[\"kv\"], \"r_logits\": st[\"r_logits\"], \"u\": u_stream(*uk),\n                         \"u2\": u_stream(*uk, \"veto\", n=256), \"veto\": veto, \"pos0\": pos0,\n                         \"stop\": \"path\" if s[\"task\"] in PATH_TASKS else \"bench\",\n                         \"prefix_text\": st.get(\"prefix_text\", \"\")})\n            meta.append((s, st, uk, veto))\n        t0 = time.time()\n        try:\n            res = sample(self.model, rows, max_new=self.max_new, tick_ids=self.tick_ids, decode=self.decode,\n                         prune_after=prune_after if prune_after is not None else self.prune_after)\n        except torch.cuda.OutOfMemoryError:\n            del rows\n            gc.collect()\n            torch.cuda.empty_cache()\n            if prune_after is not None and prune_after <= 300:\n                raise\n            logger.error(f\"OOM in {stage} {chunk[0]['task']} L={L}; retrying with memory-guard pruning after step 300\")\n            TIMING[\"decisions\"].append({\"utc\": utc_now(), \"event\": \"oom_retry_prune300\", \"stage\": stage,\n                                        \"task\": chunk[0][\"task\"], \"L\": L})\n            return self._run_batch(stage, chunk, n_real, L, pos0, prune_after=300)\n        dt = time.time() - t0\n        out = []\n        bid = f\"{stage}|{chunk[0]['task']}|{L}|{int(t0)}\"\n        for (s, st, uk, veto), r in list(zip(meta, res))[:n_real]:\n            gen = self.decode(r[\"token_ids\"])\n            pre_text = st.get(\"prefix_text\", \"\")\n            fire_ctx = None\n            if r[\"veto_fired\"] and r[\"fire_step\"] is not None:\n                fs = r[\"fire_step\"]\n                fire_ctx = self.decode(r[\"token_ids\"][max(0, fs - 12):fs + 12])\n            out.append({\n                \"uid\": self.uid(s), \"stage\": stage, \"task\": s[\"task\"], \"template\": s[\"w\"], \"w\": s[\"w\"], \"k\": s[\"k\"],\n                \"sample_id\": s[\"k\"], \"arm\": s[\"arm\"], \"condition\": s[\"arm\"], \"block\": 0 if s[\"k\"] < 10 else 1,\n                \"model\": MODEL_ID, \"decoding\": DECODING, \"seed\": stable_seed(*uk), \"u_key\": list(uk),\n                \"prompt_kind\": st[\"kind\"], \"prompt_sha256\": sha256_text(\",\".join(map(str, st[\"ids\"]))),\n                \"P\": pos0, \"cache_len\": L, \"prefill_id\": st[\"kind\"] if \"+\" in s[\"arm\"] else None,\n                \"prefix_text\": pre_text, \"prefix_ids\": st.get(\"prefix_ids\"), \"text\": pre_text + gen, \"gen_text\": gen,\n                \"token_ids\": r[\"token_ids\"], \"n_new_tokens\": r[\"n_tokens\"], \"finish_reason\": r[\"finish_reason\"],\n                \"logprob_sum\": r[\"logprob_sum\"], \"veto\": veto, \"veto_fired\": r[\"veto_fired\"],\n                \"fire_step\": r[\"fire_step\"], \"fire_context\": fire_ctx, \"n_redraws\": r[\"n_redraws\"],\n                \"redraw_steps\": r[\"redraw_steps\"], \"n_completions_drawn\": r[\"n_completions_drawn\"],\n                \"batch_id\": bid, \"batch_B\": self.B, \"batch_steps\": r[\"steps\"], \"pruned_at\": r[\"pruned_at\"],\n                \"utc\": utc_now(), \"token_ids_file\": \"data/samples_raw.jsonl\"})\n        append_jsonl(RAW, out)\n        self.done_uids.update(o[\"uid\"] for o in out)\n        TIMING[\"batches\"].append({\"stage\": stage, \"task\": chunk[0][\"task\"], \"L\": L, \"n_real\": n_real,\n                                  \"arms\": sorted({c[\"arm\"] for c in chunk}), \"steps\": res[0][\"steps\"], \"s\": dt,\n                                  \"pruned_at\": res[0][\"pruned_at\"], \"utc\": utc_now()})\n        logger.info(f\"[{stage}] {chunk[0]['task']} L={L} arms={sorted({c['arm'] for c in chunk[:n_real]})} rows={n_real} \"\n                    f\"steps={res[0]['steps']} {dt:.1f}s\" + (f\" pruned@{res[0]['pruned_at']}\" if res[0][\"pruned_at\"] else \"\"))\n        if len(TIMING[\"batches\"]) % 5 == 0:\n            write_json(RESULTS_DIR / \"timing.json\", TIMING)\n\n    def wait_for(self, cond: Callable[[], bool], what: str, poll: float = 15.0) -> None:\n        t0 = time.time()\n        last = 0.0\n        while not cond():\n            if time.time() - last > 120:\n                logger.info(f\"waiting for {what} ({time.time() - t0:.0f}s)\")\n                last = time.time()\n            time.sleep(poll)\n        TIMING[\"decisions\"].append({\"utc\": utc_now(), \"event\": f\"waited for {what}\", \"s\": time.time() - t0})\n\n    def stage_time(self, name: str, t0: float, n: int) -> None:\n        dt = time.time() - t0\n        TIMING[\"stages\"][name] = {\"s\": dt, \"rows\": n, \"utc_end\": utc_now()}\n        write_json(RESULTS_DIR / \"timing.json\", TIMING)\n        logger.info(f\"stage {name}: {n} rows in {dt / 60:.1f} min; remaining budget {self.remaining() / 60:.1f} min\")\n\n\n# ------------------------------------------------------------------------------------------------ labels\ndef labelled_uids() -> dict[str, dict[str, Any]]:\n    return {r[\"uid\"]: r for r in read_jsonl(SAMPLES)}\n\n\ndef all_labelled(uids: list[str]) -> bool:\n    lab = labelled_uids()\n    return all(u in lab for u in uids)\n\n\ndef share_default(rows: list[dict[str, Any]], task: str) -> tuple[int, int]:\n    att = [r for r in rows if r[\"label\"] not in ATTEMPT_EXCLUDE]\n    return sum(r[\"label\"] == default_of(task) for r in att), len(att)\n\n\ndef compute_commit2(tasks: list[str]) -> dict[str, Any]:\n    lab = labelled_uids()\n    ngrams = read_json(PRED_DIR / \"ngrams.json\")\n    c2c, landings = {}, {}\n    for t in tasks:\n        rows = [r for r in lab.values() if r[\"task\"] == t and r[\"arm\"] == \"V1\"]\n        D = default_of(t)\n        nd, na = share_default(rows, t)\n        fire = float(np.mean([bool(r[\"veto_fired\"]) for r in rows])) if rows else float(\"nan\")\n        fired = [r for r in rows if r[\"veto_fired\"] and r[\"label\"] not in ATTEMPT_EXCLUDE]\n        V = 1 - nd / na if na else float(\"nan\")\n        Vf = float(np.mean([r[\"label\"] != D for r in fired])) if fired else float(\"nan\")\n        if not ngrams[t].get(\"defined\") or not rows or not (fire >= THRESHOLDS[\"veto_min_fire_rate\"]):\n            cls = \"UNDEFINED\"\n        elif V >= THRESHOLDS[\"veto_low_direct\"]:\n            cls = \"LOW_DIRECT\"\n        elif V < THRESHOLDS[\"veto_high_direct\"]:\n            cls = \"HIGH_DIRECT\"\n        else:\n            cls = \"NONE\"\n        cov = set(ngrams[t].get(\"co_vetoed\") or [])\n        nond = [r for r in rows if r[\"label\"] not in ATTEMPT_EXCLUDE and r[\"label\"] != D]\n        land = collections.Counter(r[\"label\"] for r in nond if r[\"label\"] not in cov)\n        tot = sum(land.values())\n        corr = collections.Counter(r[\"label\"] for r in nond if r[\"label\"] not in cov and r.get(\"passed\"))\n        c2c[t] = {\"V\": V, \"n_attempted\": na, \"n_default\": nd, \"fire_rate\": fire, \"V_fired\": Vf,\n                  \"n_fired_attempted\": len(fired), \"class\": cls,\n                  \"prediction\": {\"LOW_DIRECT\": \"F_direct <= 0.15\", \"HIGH_DIRECT\": \"F_direct >= 0.25\"}.get(cls)}\n        landings[t] = {\"counts\": dict(land), \"dist\": {k: v / tot for k, v in land.items()} if tot else {},\n                       \"modal\": land.most_common(1)[0][0] if land else None, \"correct_only\": dict(corr),\n                       \"pass_rate\": float(np.mean([bool(r.get(\"passed\")) for r in rows])) if rows else None,\n                       \"co_vetoed_excluded\": sorted(cov), \"n_nondefault\": len(nond),\n                       \"subtract_oneshot_forecast\": {k: v / tot for k, v in land.items()} if tot else {}}\n    return {\"c2c\": c2c, \"landings\": landings}\n\n\ndef compute_gate(tasks: list[str]) -> dict[str, Any]:\n    lab = labelled_uids()\n    out = {}\n    for t in tasks:\n        rows = [r for r in lab.values() if r[\"task\"] == t and r[\"arm\"] == \"a\"]\n        nd, na = share_default(rows, t)\n        s_a = nd / na if na else float(\"nan\")\n        out[t] = {\"s_a\": s_a, \"avoidance\": 1 - s_a, \"n_attempted\": na, \"n_nondefault\": na - nd, \"n_rows\": len(rows),\n                  \"gated\": bool(na and (1 - s_a) >= THRESHOLDS[\"gate_avoidance\"]\n                                and (na - nd) >= THRESHOLDS[\"gate_min_nondefault\"])}\n    return out\n\n\ndef specs(tasks: list[str], arm_ks: list[tuple[str, range]]) -> list[dict[str, Any]]:\n    \"\"\"Rows ordered task -> template -> arm -> k (so each template's arms sit together in its shape class).\"\"\"\n    return [{\"task\": t, \"w\": w, \"k\": k, \"arm\": a} for t in tasks for w in TEMPLATE_IDS for a, ks in arm_ks for k in ks]\n\n\nR20, R10 = range(20), range(10)\n\n\n# ------------------------------------------------------------------------------------------------ main queue\ndef run(B: int, deadline: float | None, prune_after: int | None) -> None:\n    W = Worker(B, deadline, prune_after)\n    TIMING.update({\"B\": B, \"deadline_epoch\": deadline, \"prune_after\": prune_after})\n    bench = list(STAGE_A)\n    # ---- S3.2 signature-prefix scoring where the exact-prefix rule did not decide (twin_A prompts only)", "numLines": 345, "startLine": 1, "totalLines": 531}}
```

### [40] THINKING · 2026-10-26 10:21:40 UTC

```
Arms are built from `c` (twin_A states on [0,p1) plus ban states with ban read-logits on [p1,P)), its reverse `d`, and `K0` which drops [p0,p1) from the ban cache. Next I'll check the frozen prompt records for the ids needed in a live CRN-slot demo.
```

### [41] TOOL CALL — Bash · 2026-10-26 10:21:41 UTC

```
Inspect the frozen prompt records format:
A=/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16; ls -la $A/prompts $A/predictions; wc -l $A/prompts/prompts.jsonl; python3 -I - "$A/prompts/prompts.jsonl" <<'EOF'
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1])]
print(len(rows))
r = rows[0]
for k, v in r.items():
    print(f"  {k}: {repr(v)[:400]}")
from collections import Counter
print(Counter((r.get('task'), r.get('kind') or r.get('variant')) for r in rows).most_common(8))
EOF
```

### [42] TOOL RESULT — Bash · 2026-10-26 10:21:41 UTC

```
{"stdout": "/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/predictions:\ntotal 3250\ndrwxrwxrwx  2 aii-agent aii-agent 1027819 Oct 20 20:08 .\ndrwxrwxrwx 16 aii-agent aii-agent 2012015 Oct 21 02:37 ..\n-rw-rw-rw-  1 aii-agent aii-agent    6684 Oct 20 18:04 associate_proximity.json\n-rw-rw-rw-  1 aii-agent aii-agent    2412 Oct 20 18:52 c2c.json\n-rw-rw-rw-  1 aii-agent aii-agent   10054 Oct 20 18:04 ngrams.json\n-rw-rw-rw-  1 aii-agent aii-agent    8267 Oct 20 20:08 prefill_depths.json\n-rw-rw-rw-  1 aii-agent aii-agent  245883 Oct 20 18:31 prefills.json\n-rw-rw-rw-  1 aii-agent aii-agent    5029 Oct 20 18:27 prereg.md\n-rw-rw-rw-  1 aii-agent aii-agent    1394 Oct 20 19:31 screen_round2.json\n-rw-rw-rw-  1 aii-agent aii-agent    1429 Oct 20 19:38 screen_round3.json\n-rw-rw-rw-  1 aii-agent aii-agent     876 Oct 20 18:27 seeds.json\n-rw-rw-rw-  1 aii-agent aii-agent    2846 Oct 20 18:52 veto_landings.json\n\n/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/prompts:\ntotal 3223\ndrwxrwxrwx  2 aii-agent aii-agent 1025540 Oct 20 17:57 .\ndrwxrwxrwx 16 aii-agent aii-agent 2012015 Oct 21 02:37 ..\n-rw-rw-rw-  1 aii-agent aii-agent  252260 Oct 20 17:57 prompts.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent    9274 Oct 20 17:57 prompts_summary.json\n210 /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16/prompts/prompts.jsonl\n210\n  task: 'T03'\n  w: 'W1'\n  kind: 'ban'\n  noun: None\n  cond: 'Do not use a full sort for this task.'\n  pad: 0\n  ids: [151644, 872, 198, 5404, 537, 990, 264, 2480, 3378, 369, 419, 3383, 382, 6262, 25, 3270, 264, 13027, 729, 11625, 21096, 11, 595, 8, 429, 4675, 279, 595, 7563, 24632, 897, 304, 10307, 13, 576, 5693, 10307, 374, 264, 1140, 315, 25780, 448, 220, 16, 2651, 2422, 21096, 8, 2651, 220, 17, 15, 15, 15, 11, 323, 1449, 897, 15448, 1948, 481, 16, 15, 15, 15, 15, 323, 220, 16, 15, 15, 15, 15, 28308, 26, 2750,\n  p0: 3\n  p1: 13\n  P: 188\n  prompt_sha256: '4cd1b7114b609f3b758e1de79c41d1f96f976df56f14ca4a509036310ec0951e'\n[(('T03', 'ban'), 5), (('T03', 'twin_A'), 5), (('T03', 'twin_B'), 5), (('T04', 'ban'), 5), (('T04', 'twin_A'), 5), (('T04', 'twin_B'), 5), (('T06', 'ban'), 5), (('T06', 'twin_A'), 5)]", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [43] THINKING · 2026-10-26 10:22:47 UTC

```
Prompts are short enough that a live CRN slot on a small model is cheap. Next, I'll check the label formats in `route_arms` and see how well ≤100-example subsets reproduce the full-run per-task shares.
```

### [44] TOOL CALL — Bash · 2026-10-26 10:22:47 UTC

```
Check label formats and candidate subset statistics:
A=/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16; python3 -I - "$A/full_method_out.json" <<'EOF'
import json, sys
from collections import Counter, defaultdict
f = json.load(open(sys.argv[1]))
ra = next(d for d in f["datasets"] if d["dataset"] == "route_arms")["examples"]
suf = Counter(); labs = Counter()
for e in ra:
    for a in ("b", "c", "d", "K0"):
        lab, _, p = e[f"predict_{a}"].partition("|")
        suf[p] += 1; labs[lab] += 1
    labs[e["output"]] += 1
print("suffixes:", suf); print("labels:", labs.most_common(40))
print("k range:", sorted(Counter(e["metadata_k"] for e in ra).items())[:25])
print("a_passed:", Counter(e["metadata_a_passed"] for e in ra))
EXCL = ("invalid", "no_code", "disputed")
def rows_of(e):
    out = [("a", e["output"], e["metadata_a_passed"])]
    for a in ("b", "c", "d", "K0"):
        lab, _, p = e[f"predict_{a}"].partition("|")
        out.append((a, lab, p == "pass"))
    return out
def stats(sub):
    by = defaultdict(lambda: defaultdict(list))
    for e in sub:
        for a, lab, p in rows_of(e):
            by[e["metadata_task"]][a].append(lab)
    res = {}
    for t, arms in by.items():
        D = next(e["metadata_default"] for e in sub if e["metadata_task"] == t)
        s = {}
        for a, labl in arms.items():
            att = [l for l in labl if l not in EXCL]
            s[a] = sum(l == D for l in att) / len(att) if att else float("nan")
        den = s["b"] - s["a"]
        Fp = (s["b"] - s["c"]) / den if den else float("nan")
        Fd = (s["b"] - s["d"]) / den if den else float("nan")
        na = len([l for l in arms["a"] if l not in EXCL]); nnd = sum(l != D for l in arms["a"] if l not in EXCL)
        res[t] = (round(s["a"],2), round(s["b"],2), round(s["c"],2), round(s["d"],2), round(s["K0"],2), round(Fp,2), round(Fd,2), na, nnd)
    return res
gated = ["T03","T06","T05","T10","T13"]
print("\nFULL:"); [print(" ", t, v) for t, v in stats(ra).items()]
subC = [e for e in ra if (e["metadata_task"] in gated and e["metadata_k"] < 3)] + \
       [e for e in ra if e["metadata_task"] in ("T04","R1","T08","R3","R6") and e["metadata_k"] < 1]
print("\nDesign C (gated k<3, T04/R1/T08/R3/R6 k<1): n =", len(subC)); [print(" ", t, v) for t, v in stats(subC).items()]
subA = [e for e in ra if (e["metadata_task"] in gated and e["metadata_k"] < 4)]
print("\nDesign A (gated k<4): n =", len(subA)); [print(" ", t, v) for t, v in stats(subA).items()]
EOF
```

### [45] TOOL RESULT — Bash · 2026-10-26 10:22:47 UTC

```
{"stdout": "suffixes: Counter({'pass': 4168, '': 350, 'fail': 282})\nlabels: [('greedy_end', 450), ('quadratic_dp', 448), ('kahn', 446), ('binary_search', 400), ('naive', 397), ('sort_sweep', 391), ('iteration', 388), ('sort_by_count', 373), ('not_run', 350), ('hash_set', 335), ('hash_map', 270), ('quickselect', 268), ('brute_force', 230), ('dfs', 209), ('other', 206), ('bfs', 172), ('index_marking', 156), ('union_find', 142), ('full_sort', 123), ('size_k_heap', 106), ('quickselect_counts', 39), ('heap', 30), ('builtin', 26), ('kmp', 20), ('bmh', 5), ('floyd', 4), ('dfs_postorder', 4), ('linear_scan', 4), ('heapify_pop', 3), ('rabin_karp', 2), ('sort_adjacent', 1), ('bisect_module', 1), ('patience_bisect', 1)]\nk range: [(0, 60), (1, 60), (2, 60), (3, 60), (4, 60), (5, 60), (6, 60), (7, 60), (8, 60), (9, 60), (10, 60), (11, 60), (12, 60), (13, 60), (14, 60), (15, 60), (16, 60), (17, 60), (18, 60), (19, 60)]\na_passed: Counter({True: 1013, False: 187})\n\nFULL:\n  T03 (0.01, 0.95, 0.01, 0.25, 0.01, 1.0, 0.74, 100, 99)\n  T04 (0.58, 1.0, 1.0, 0.89, 0.5, 0.0, 0.26, 100, 42)\n  T06 (0.21, 1.0, 0.97, 0.22, 0.95, 0.04, 0.99, 100, 79)\n  T05 (0.17, 1.0, 0.66, 0.2, 0.67, 0.41, 0.96, 100, 83)\n  T10 (0.0, 0.99, 0.0, 0.2, 0.0, 1.0, 0.8, 100, 100)\n  R1 (1.0, 1.0, 1.0, 1.0, 0.5, nan, nan, 100, 0)\n  T08 (0.69, 1.0, 0.99, 0.72, 0.48, 0.03, 0.9, 100, 31)\n  R3 (0.96, 1.0, 1.0, 1.0, 0.5, 0.0, 0.0, 100, 4)\n  T13 (0.41, 1.0, 0.77, 0.99, 0.74, 0.39, 0.02, 100, 59)\n  R6 (0.98, 0.76, 1.0, 0.76, 0.5, 1.09, -0.0, 100, 2)\n  T14 (0.59, 0.93, 0.97, 0.77, 0.47, -0.12, 0.47, 100, 41)\n  T11 (0.98, 1.0, 1.0, 1.0, 0.5, 0.0, 0.0, 100, 2)\n\nDesign C (gated k<3, T04/R1/T08/R3/R6 k<1): n = 100\n  T03 (0.0, 0.93, 0.0, 0.2, 0.0, 1.0, 0.79, 15, 15)\n  T06 (0.2, 1.0, 1.0, 0.27, 1.0, 0.0, 0.92, 15, 12)\n  T05 (0.13, 1.0, 0.73, 0.2, 0.67, 0.31, 0.92, 15, 13)\n  T10 (0.0, 1.0, 0.0, 0.2, 0.0, 1.0, 0.8, 15, 15)\n  T13 (0.33, 1.0, 0.73, 1.0, 0.67, 0.4, 0.0, 15, 10)\n  T04 (0.4, 1.0, 1.0, 0.8, 1.0, 0.0, 0.33, 5, 3)\n  R1 (1.0, 1.0, 1.0, 1.0, 1.0, nan, nan, 5, 0)\n  T08 (1.0, 1.0, 1.0, 1.0, 1.0, nan, nan, 5, 0)\n  R3 (1.0, 1.0, 1.0, 1.0, 1.0, nan, nan, 5, 0)\n  R6 (0.8, 0.8, 1.0, 0.8, 1.0, nan, nan, 5, 1)\n\nDesign A (gated k<4): n = 100\n  T03 (0.0, 0.95, 0.0, 0.2, 0.0, 1.0, 0.79, 20, 20)\n  T06 (0.2, 1.0, 1.0, 0.25, 1.0, 0.0, 0.94, 20, 16)\n  T05 (0.15, 1.0, 0.7, 0.2, 0.65, 0.35, 0.94, 20, 17)\n  T10 (0.0, 1.0, 0.0, 0.2, 0.0, 1.0, 0.8, 20, 20)\n  T13 (0.3, 1.0, 0.8, 1.0, 0.7, 0.29, 0.0, 20, 14)", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [46] THINKING · 2026-10-26 10:23:53 UTC

```
Design C closely reproduces the full-run per-task route fractions, though I need to drop `not_run` K0 labels since those rows don't exist in the original. I'll now check the helpers the analysis relies on: `forecast_s2.catalogue`, the frozen `c2c.json`, and `outputs.py`'s route_arms construction.
```

### [47] TOOL CALL — Bash · 2026-10-26 10:23:53 UTC

```
Read catalogue helper, frozen c2c predictions, outputs builder:
A=/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16; grep -n "def catalogue" -A 22 $A/src/forecast_s2.py; echo ----; cat $A/predictions/c2c.json | head -c 2500; echo; echo ----; grep -n "route_arms" -B 3 -A 30 $A/src/outputs.py | head -80
```

### [48] TOOL RESULT — Bash · 2026-10-26 10:23:53 UTC

```
{"stdout": "37:def catalogue(task: str) -> list[str]:\n38-    if task == \"t1\":\n39-        return [\"bfs\", \"dfs\", \"bibfs\", \"iddfs\", \"astar_gbfs\", \"dijkstra\"]\n40-    if task == \"t2\":\n41-        return [\"dijkstra\", \"bf_spfa\", \"bidijkstra\", \"floyd\", \"dial\"]\n42-    return [c[\"mode\"] for c in read_json(BENCH / TASK_DIR[task] / \"spec.json\")[\"catalogue\"]]\n43-\n44-\n45-def baseline_codes(task: str) -> tuple[list[str], str]:\n46-    if task in PATH_TASKS:\n47-        rows = read_jsonl(E8 / \"data\" / \"samples.jsonl\")\n48-        codes = [r[\"code\"] for r in rows if r[\"task\"] == task and r[\"condition\"] == \"b\"\n49-                 and r[\"label\"] == PATH_DEFAULT[task] and r.get(\"code\")]\n50-        return codes, \"exp8 data/samples.jsonl arm b, label == default\"\n51-    rows = read_jsonl(BENCH / TASK_DIR[task] / \"pilot_rows.jsonl\")\n52-    return [r[\"code\"] for r in rows if r[\"label\"] == default_of(task) and r.get(\"code\")], \"bench pilot_rows, label == default\"\n53-\n54-\n55-def forced_sets(task: str) -> tuple[dict[str, list[dict]], str]:\n56-    D = default_of(task)\n57-    out: dict[str, list[dict]] = {m: [] for m in catalogue(task) if m != D}\n58-    if task in PATH_TASKS:\n59-        for r in read_jsonl(E7 / \"data\" / \"forced_labelled.jsonl\"):\n----\n{\n \"T03\": {\n  \"V\": 0.41000000000000003,\n  \"n_attempted\": 100,\n  \"n_default\": 59,\n  \"fire_rate\": 0.86,\n  \"V_fired\": 0.4186046511627907,\n  \"n_fired_attempted\": 86,\n  \"class\": \"HIGH_DIRECT\",\n  \"prediction\": \"F_direct >= 0.25\"\n },\n \"T04\": {\n  \"V\": 0.0,\n  \"n_attempted\": 94,\n  \"n_default\": 94,\n  \"fire_rate\": 1.0,\n  \"V_fired\": 0.0,\n  \"n_fired_attempted\": 94,\n  \"class\": \"HIGH_DIRECT\",\n  \"prediction\": \"F_direct >= 0.25\"\n },\n \"T06\": {\n  \"V\": 0.0,\n  \"n_attempted\": 100,\n  \"n_default\": 100,\n  \"fire_rate\": 1.0,\n  \"V_fired\": 0.0,\n  \"n_fired_attempted\": 100,\n  \"class\": \"HIGH_DIRECT\",\n  \"prediction\": \"F_direct >= 0.25\"\n },\n \"T05\": {\n  \"V\": 0.0,\n  \"n_attempted\": 100,\n  \"n_default\": 100,\n  \"fire_rate\": 1.0,\n  \"V_fired\": 0.0,\n  \"n_fired_attempted\": 100,\n  \"class\": \"HIGH_DIRECT\",\n  \"prediction\": \"F_direct >= 0.25\"\n },\n \"T10\": {\n  \"V\": 0.30000000000000004,\n  \"n_attempted\": 20,\n  \"n_default\": 14,\n  \"fire_rate\": 0.99,\n  \"V_fired\": 0.2631578947368421,\n  \"n_fired_attempted\": 19,\n  \"class\": \"HIGH_DIRECT\",\n  \"prediction\": \"F_direct >= 0.25\"\n },\n \"R1\": {\n  \"V\": 0.0,\n  \"n_attempted\": 97,\n  \"n_default\": 97,\n  \"fire_rate\": 0.61,\n  \"V_fired\": 0.0,\n  \"n_fired_attempted\": 58,\n  \"class\": \"HIGH_DIRECT\",\n  \"prediction\": \"F_direct >= 0.25\"\n },\n \"T08\": {\n  \"V\": 0.0,\n  \"n_attempted\": 100,\n  \"n_default\": 100,\n  \"fire_rate\": 1.0,\n  \"V_fired\": 0.0,\n  \"n_fired_attempted\": 100,\n  \"class\": \"HIGH_DIRECT\",\n  \"prediction\": \"F_direct >= 0.25\"\n },\n \"R3\": {\n  \"V\": 0.0,\n  \"n_attempted\": 46,\n  \"n_default\": 46,\n  \"fire_rate\": 1.0,\n  \"V_fired\": 0.0,\n  \"n_fired_attempted\": 46,\n  \"class\": \"HIGH_DIRECT\",\n  \"prediction\": \"F_direct >= 0.25\"\n },\n \"T13\": {\n  \"V\": 0.0,\n  \"n_attempted\": 69,\n  \"n_default\": 69,\n  \"fire_rate\": 1.0,\n  \"V_fired\": 0.0,\n  \"n_fired_attempted\": 69,\n  \"class\": \"HIGH_DIRECT\",\n  \"prediction\": \"F_direct >= 0.25\"\n },\n \"R6\": {\n  \"V\": 0.3870967741935484,\n  \"n_attempted\": 62,\n  \"n_default\": 38,\n  \"fire_rate\": 0.62,\n  \"V_fired\": 0.0,\n  \"n_fired_attempted\": 24,\n  \"class\": \"HIGH_DIRECT\",\n  \"prediction\": \"F_direct >= 0.25\"\n },\n \"T14\": {\n  \"V\": 0.06999999999999995,\n  \"n_attempted\": 100,\n  \"n_default\": 93,\n  \"fire_rate\": 0.71,\n  \"V_fired\": 0.0,\n  \"n_fired_attempted\": 71,\n  \"class\": \"HIGH_DIRECT\",\n  \"prediction\": \"F_direct >= 0.25\"\n },\n \"T11\": {\n  \"V\": 0.0,\n  \"n_attempted\": 42,\n  \"n_default\": 42,\n  \"fire_rate\": 1.0,\n  \"V_fired\": 0.0,\n  \"n_fired_attempted\": 42,\n  \"class\": \"HIGH_DIRECT\",\n  \"prediction\": \"F_direct >= 0.25\"\n }\n}\n----\n1-#!/usr/bin/env python3\n2-\"\"\"S10 outputs: results/deviations.json and method_out.json (exp_gen_sol_out). One dataset per readout:\n3:route_arms (one example per CRN slot; output = arm-a label; predict_<arm> = 'label|pass'), veto_sufficiency,\n4-prefill, path_screen, controls. metadata carries every analysis summary and the deviations list.\"\"\"\n5-\n6-from __future__ import annotations\n7-\n8-import json\n9-from pathlib import Path\n10-from typing import Any\n11-\n12-from loguru import logger\n13-\n14-from cfg import (MODEL_ID, MODEL_REVISION, PATH_DEFAULT, PATH_TASKS, PRED_DIR, RESULTS_DIR, ROOT, STAGE_A, TEMPLATE_IDS,\n15-                 default_of, read_json, read_jsonl, write_json)\n16-\n17-DEVIATIONS = [\n18-    {\"id\": \"D1\", \"what\": \"Hardware: one NVIDIA L4 (23 GB; about a third of the RTX 4090's memory bandwidth) instead of the \"\n19-     \"planned RTX A4500. Measured decode latency was 89 ms/step at B=20 and 101 ms/step at B=40, so batches are B=40 rows \"\n20-     \"instead of B=10.\", \"consequence\": \"Batch shape is constant within each shape class (task, cache length, first \"\n21-     \"position); CRN partners of a slot always meet identical kernels (U1 = 1.00, U2 = 1.00).\"},\n22-    {\"id\": \"D2\", \"what\": \"Rows of different templates with equal prompt length share a batch (cross-template packing); the \"\n23-     \"last batch of a class is padded with discarded duplicate rows.\", \"consequence\": \"None on the estimates; rows never \"\n24-     \"interact inside a batch.\"},\n25-    {\"id\": \"D3\", \"what\": \"V1 (one-shot veto) runs at N=100 (k 0-19) instead of N=50; VP (persistent veto) at N=100 on the \"\n26-     \"path screen; route arms c/d also run on non-gated tasks at N=100 (descriptive, Q5 upgraded).\", \"consequence\":\n27-     \"More precision at no extra batch cost (B=40 pairs b with V1, a with c, etc.).\"},\n28-    {\"id\": \"D4\", \"what\": \"K0 is implemented by removing the condition span [p0, p1) from the cache instead of masking it \"\n29-     \"(keys keep their RoPE rotation; generated queries keep positions P + step).\", \"consequence\": \"Exact for every \"\n30-     \"generated query; checked in U3 against exp8's masked knockout (TV distance 1.2e-7 on the first generated position; \"\n31-     \"eager attention mass on the span exactly 0 in all 36 layers). Lets every batch run stock SDPA with native GQA.\"},\n32-    {\"id\": \"D5\", \"what\": \"A row stops once its first fenced code block is closed (both labellers extract exactly that \"\n33-     \"block).\", \"consequence\": \"Labels unchanged; generation shortened.\"},\n--\n126-                                **{f\"predict_{x}\": _lab(r) for x, r in arms.items() if r is not None},\n127-                                \"metadata_task\": t, \"metadata_template\": w, \"metadata_k\": k,\n128-                                \"metadata_output_source\": \"exp8 arm a (full ban) label for the same slot\"})\n129:    datasets = [{\"dataset\": n, \"examples\": ex} for n, ex in ((\"route_arms\", ds_route), (\"veto_sufficiency\", ds_veto),\n130-                                                             (\"prefill\", ds_pre), (\"path_screen\", ds_path),\n131-                                                             (\"controls_placebo_K0b\", ds_ctrl)) if ex]\n132-    write_json(RESULTS_DIR / \"deviations.json\", DEVIATIONS)\n133-    rt = an[\"route\"]\n134-    meta = {\n135-        \"method_name\": \"Bench route test of prompt bans (CRN KV-splice arms, one-shot veto, prefill) in Qwen3-8B\",\n136-        \"model\": MODEL_ID, \"model_revision\": MODEL_REVISION, \"dtype\": \"bfloat16\", \"thinking\": False,\n137-        \"decoding\": \"T=1.0, top-p 1.0, no top-k, max 1024 new tokens, CRN inverse-CDF sampling\",\n138-        \"hardware\": \"1 x NVIDIA L4 23 GB, 6 CPUs, 66 GB RAM\",\n139-        \"baselines\": \"arm a (full ban) and arm b (token-length-matched neutral twin) in the same pipeline with the same \"\n140-                     \"uniforms; placebo splice and knockout-mechanics controls\",\n141-        \"gated_tasks\": an[\"gated\"], \"gate\": an[\"gate\"],\n142-        \"C2a\": {\"verdict\": rt.get(\"verdict\"), \"verdict_by_interval\": rt.get(\"verdict_by_interval\"),\n143-                \"point\": rt.get(\"point\"), \"intervals\": {k: {kk: vv for kk, vv in v.items() if kk != \"jackknife_values\"}\n144-                                                        for k, v in (rt.get(\"intervals\") or {}).items()},\n145-                \"p_boot_F_prompt_le_half\": rt.get(\"p_boot_F_prompt_le_half\"),\n146-                \"p_boot_F_direct_ge_third\": rt.get(\"p_boot_F_direct_ge_third\"),\n147-                \"per_task\": rt.get(\"per_task\"), \"mixed_glm\": rt.get(\"mixed_glm\"),\n148-                \"leave_one_template_out\": rt.get(\"leave_one_template_out\")},\n149-        \"C2c\": {k: v for k, v in an[\"c2c\"].items()},\n150-        \"C2b_sensitivity\": an[\"c2b_sensitivity\"], \"prefill\": an[\"prefill\"], \"controls\": an[\"controls\"],\n151-        \"screen\": {k: v for k, v in an[\"screen\"].items() if k != \"rounds\"} | {\"rounds\": {\n152-            t: {arm: {kk: vv for kk, vv in rd.items() if kk != \"reemergence_surfaces\"} if isinstance(rd, dict) else rd\n153-                for arm, rd in r.items()} for t, r in an[\"screen\"].get(\"rounds\", {}).items()}},\n154-        \"lp_readout\": an[\"lp_readout\"].get(\"pooled_gated\") if isinstance(an[\"lp_readout\"], dict) else None,\n155-        \"shares\": {t: {a: {k: v for k, v in s.items() if k != \"per_template\"} for a, s in x.items()}\n156-                   for t, x in an[\"shares\"].items()},\n157-        \"engine_validation\": read_json(RESULTS_DIR / \"engine_validation.json\"),\n158-        \"labeller_recheck\": {k: v for k, v in read_json(RESULTS_DIR / \"labeller_recheck.json\").items() if k != \"bench\"},\n159-        \"deviations\": DEVIATIONS,", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [49] TOOL CALL — Bash · 2026-10-26 10:23:59 UTC

```
Read route_arms builder and per-task mechanism catalogues:
A=/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16; sed -n 60,110p $A/src/outputs.py; echo; ls $A/inputs/bench/ | head; python3 -I -c "
import json,sys
for t in ['T03_kth_smallest','T06_find_duplicate','T05_two_sum','T10_connected_components','T13_merge_intervals','T04_substring_search','R1_non_overlapping_intervals','T08_fibonacci','R3_topological_order','R6_first_last_position']:
    s=json.load(open('$A/inputs/bench/'+t+'/spec.json'))
    print(t, [c['mode'] for c in s['catalogue']], list(s.keys())[:12])
"
```

### [50] TOOL RESULT — Bash · 2026-10-26 10:23:59 UTC

```
{"stdout": "    {\"id\": \"D12\", \"what\": \"The bench pilot was generated with Qwen3-8B-FP8 in vLLM; this artifact samples bf16 weights in \"\n     \"HF transformers (as planned).\", \"consequence\": \"Arm-b default shares are 0.95 (T03), 0.76 (R6), 0.92 (T14) instead of \"\n     \"the pilot's ~1.0; the distinctive n-gram was frozen on the pilot programs.\"},\n]\n\n\ndef _lab(r: dict[str, Any] | None) -> str:\n    if r is None:\n        return \"not_run\"\n    return f\"{r['label']}|{'pass' if r.get('passed') else 'fail'}\"\n\n\ndef build_outputs() -> dict[str, Any]:\n    rows = {}\n    for r in read_jsonl(ROOT / \"data\" / \"samples.jsonl\"):\n        rows[r[\"uid\"]] = r\n    an = read_json(RESULTS_DIR / \"analysis.json\")\n    ngr = read_json(PRED_DIR / \"ngrams.json\")\n    prompts = {(r[\"task\"], r[\"w\"], r[\"kind\"]): r for r in read_jsonl(ROOT / \"prompts\" / \"prompts.jsonl\")}\n    get = lambda t, a, w, k: rows.get(f\"{t}|{a}|{w}|{k}\")  # noqa: E731\n    gated = set(an[\"gated\"])\n    ds_route, ds_veto, ds_pre, ds_path, ds_ctrl = [], [], [], [], []\n    for t in STAGE_A:\n        for w in TEMPLATE_IDS:\n            ban_cond = prompts[(t, w, \"ban\")][\"cond\"]\n            twin = prompts[(t, w, \"twin_A\")][\"cond\"]\n            for k in range(20):\n                a = get(t, \"a\", w, k)\n                if a is None:\n                    continue\n                inp = f\"task {t} | template {w} | slot k={k} | ban segment: {ban_cond!r} | neutral twin: {twin!r}\"\n                ex = {\"input\": inp, \"output\": a[\"label\"], \"metadata_task\": t, \"metadata_template\": w, \"metadata_k\": k,\n                      \"metadata_default\": default_of(t), \"metadata_gated\": t in gated,\n                      \"metadata_a_passed\": bool(a.get(\"passed\"))}\n                for arm in (\"b\", \"c\", \"d\", \"K0\"):\n                    ex[f\"predict_{arm}\"] = _lab(get(t, arm, w, k))\n                ds_route.append(ex)\n                b, v = get(t, \"b\", w, k), get(t, \"V1\", w, k)\n                if b is not None and v is not None:\n                    ds_veto.append({\"input\": f\"task {t} | template {w} | slot k={k} | vetoed n-gram {ngr[t].get('text')!r}\",\n                                    \"output\": b[\"label\"], \"predict_V1\": _lab(v),\n                                    \"predict_V1_fired\": str(bool(v.get(\"veto_fired\"))),\n                                    \"metadata_fire_step\": v.get(\"fire_step\"), \"metadata_task\": t, \"metadata_template\": w,\n                                    \"metadata_k\": k, \"metadata_default\": default_of(t)})\n                if k < 10 and get(t, \"BAN+SIG\", w, k) is not None:\n                    ds_pre.append({\"input\": f\"task {t} | template {w} | slot k={k} | prefills: signature + neutral\",\n                                   \"output\": a[\"label\"],\n                                   **{f\"predict_{x.replace('+', '_')}\": _lab(get(t, x, w, k))\n                                      for x in (\"BAN+SIG\", \"TWIN+SIG\", \"BAN+NEU\", \"TWIN+NEU\")},\n                                   \"metadata_task\": t, \"metadata_template\": w, \"metadata_k\": k})\n                if k < 10 and get(t, \"pl\", w, k) is not None:\n\nR1_non_overlapping_intervals\nR3_topological_order\nR6_first_last_position\nT03_kth_smallest\nT04_substring_search\nT05_two_sum\nT06_find_duplicate\nT08_fibonacci\nT10_connected_components\nT11_longest_increasing_subsequence\nT03_kth_smallest ['full_sort', 'size_k_heap', 'heapify_pop', 'quickselect', 'median_of_medians', 'counting_sort'] ['task', 'task_id', 'leetcode_ids', 'signature', 'description', 'format_line', 'spec_text', 'bounds', 'catalogue', 'aliases', 'forced_templates', 'descriptive_forced_template']\nT06_find_duplicate ['hash_set', 'sort_adjacent', 'floyd', 'value_binary_search', 'index_marking'] ['task', 'task_id', 'leetcode_ids', 'signature', 'description', 'format_line', 'spec_text', 'bounds', 'catalogue', 'aliases', 'forced_templates', 'descriptive_forced_template']\nT05_two_sum ['hash_map', 'sort_two_pointers', 'brute_force', 'sort_binary_search'] ['task', 'task_id', 'leetcode_ids', 'signature', 'description', 'format_line', 'spec_text', 'bounds', 'catalogue', 'aliases', 'forced_templates', 'descriptive_forced_template']\nT10_connected_components ['bfs', 'dfs', 'union_find', 'label_propagation'] ['task', 'task_id', 'leetcode_ids', 'signature', 'description', 'format_line', 'spec_text', 'bounds', 'catalogue', 'aliases', 'forced_templates', 'descriptive_forced_template']\nT13_merge_intervals ['sort_sweep', 'interval_tree', 'union_find'] ['task', 'task_id', 'leetcode_ids', 'signature', 'description', 'format_line', 'spec_text', 'bounds', 'catalogue', 'aliases', 'forced_templates', 'descriptive_forced_template']\nT04_substring_search ['naive', 'kmp', 'rabin_karp', 'z_algorithm', 'bmh', 'builtin'] ['task', 'task_id', 'leetcode_ids', 'signature', 'description', 'format_line', 'spec_text', 'bounds', 'catalogue', 'aliases', 'forced_templates', 'descriptive_forced_template']\nR1_non_overlapping_intervals ['greedy_end', 'dp_bisect', 'memo_recursion', 'dag_longest_path'] ['task', 'task_id', 'leetcode_ids', 'signature', 'description', 'format_line', 'spec_text', 'bounds', 'catalogue', 'aliases', 'forced_templates', 'descriptive_forced_template']\nT08_fibonacci ['iteration', 'memo_recursion', 'matrix_power', 'fast_doubling'] ['task', 'task_id', 'leetcode_ids', 'signature', 'description', 'format_line', 'spec_text', 'bounds', 'catalogue', 'aliases', 'forced_templates', 'descriptive_forced_template']\nR3_topological_order ['kahn', 'dfs_postorder', 'source_removal', 'layering'] ['task', 'task_id', 'leetcode_ids', 'signature', 'description', 'format_line', 'spec_text', 'bounds', 'catalogue', 'aliases', 'forced_templates', 'descriptive_forced_template']\nR6_first_last_position ['binary_search', 'bisect_module', 'exponential_search'] ['task', 'task_id', 'leetcode_ids', 'signature', 'description', 'format_line', 'spec_text', 'bounds', 'catalogue', 'aliases', 'forced_templates', 'descriptive_forced_template']", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [51] THINKING · 2026-10-26 10:24:05 UTC

```
I'll keep catalogues as short lists in the demo metadata. Before committing to a live engine section, I'm setting up a test venv with Colab's torch/transformers versions in the background while writing the mini-data builder to check feasibility.
```

### [52] TOOL CALL — Bash · 2026-10-26 10:24:05 UTC

```
Check caches, python binary and cached model files:
echo "PIP_CACHE_DIR=$PIP_CACHE_DIR UV_CACHE_DIR=$UV_CACHE_DIR"; ls -la /usr/local/bin/python3.12; ls /tmp/aii_nb_test_envs/ 2>/dev/null | head; ls $HF_HUB_CACHE/models--Qwen--Qwen3-0.6B/snapshots/*/ 2>/dev/null
```

### [53] TOOL RESULT — Bash · 2026-10-26 10:24:05 UTC

```
{"stdout": "PIP_CACHE_DIR=/ai-inventor/aii_data/runs/run_jSassd-YWLVC/.shared_cache/pip UV_CACHE_DIR=/ai-inventor/aii_data/runs/run_jSassd-YWLVC/.shared_cache/uv\n-rwxr-xr-x 1 root root 14480 Sep 19 01:07 /usr/local/bin/python3.12\nconfig.json\ngeneration_config.json\nmerges.txt\nmodel.safetensors\ntokenizer.json\ntokenizer_config.json\nvocab.json", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [54] TOOL CALL — Bash · 2026-10-26 10:24:15 UTC

```
Create test venv and install Colab-matching packages, timing each step:
mkdir -p /tmp/aii_nb_test_envs && cd /tmp/aii_nb_test_envs && T0=$(date +%s); UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art__5akZ9W9iZM4-bfb6955ec1d9 && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art__5akZ9W9iZM4-bfb6955ec1d9/bin/python jupyter ipykernel && T1=$(date +%s); echo "venv+jupyter: $((T1-T0))s"; /tmp/aii_nb_test_envs/art__5akZ9W9iZM4-bfb6955ec1d9/bin/python -m pip install -q --index-url https://download.pytorch.org/whl/cpu torch==2.9.0+cpu 2>&1 | tail -3; T2=$(date +%s); echo "torch cpu: $((T2-T1))s"; /tmp/aii_nb_test_envs/art__5akZ9W9iZM4-bfb6955ec1d9/bin/python -m pip install -q numpy==2.0.2 pandas==2.2.2 scipy==1.16.3 statsmodels==0.14.6 matplotlib==3.10.0 transformers==5.0.0 tokenizers==0.22.2 huggingface_hub==1.4.0 loguru==0.7.3 2>&1 | tail -3; T3=$(date +%s); echo "rest: $((T3-T2))s"; /tmp/aii_nb_test_envs/art__5akZ9W9iZM4-bfb6955ec1d9/bin/python -c "import torch, transformers, numpy, scipy, statsmodels; print(torch.__version__, transformers.__version__, numpy.__version__, scipy.__version__, statsmodels.__version__)"
```

### [55] TOOL RESULT — Bash · 2026-10-26 10:24:15 UTC

```
{"stdout": "", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false, "backgroundTaskId": "br19m1lqh", "backgroundCwdHint": "Session cwd remains /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4; directory changes made by the backgrounded command do not apply to subsequent commands."}
```

### [56] ASSISTANT · 2026-10-26 10:24:37 UTC

```
While that installs, let me check the labelled-row schema in `data/samples.jsonl` (first row only), since the notebook's row adapter must reproduce the fields `analysis.py` reads.
```

### [57] TOOL CALL — Bash · 2026-10-26 10:24:37 UTC

```
Show the schema of one labelled sample row:
A=/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16; ls -la $A/data/; head -n 1 $A/data/samples.jsonl | python3 -I -c "
import json,sys
r=json.loads(sys.stdin.readline())
for k,v in r.items(): print(' ',k,':',repr(v)[:160])
"
```

### [58] TOOL RESULT — Bash · 2026-10-26 10:24:37 UTC

````
{"stdout": "total 76810\ndrwxrwxrwx  2 aii-agent aii-agent  2007117 Oct 20 20:21 .\ndrwxrwxrwx 16 aii-agent aii-agent  2012015 Oct 21 02:37 ..\n-rw-rw-rw-  1 aii-agent aii-agent  3205616 Oct 20 20:13 label_mech_cache.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent   223576 Oct 20 19:57 path_eval_cache.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent 40262520 Oct 20 20:21 samples.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent 30941502 Oct 20 20:15 samples_raw.jsonl\n  uid : 'T03|b|W1|0'\n  stage : 'S4'\n  task : 'T03'\n  template : 'W1'\n  w : 'W1'\n  k : 0\n  sample_id : 0\n  arm : 'b'\n  condition : 'b'\n  block : 0\n  model : 'Qwen/Qwen3-8B'\n  decoding : 'T1.0_topp1.0_topk-off_max1024_thinkoff'\n  seed : 1256873131154169166\n  u_key : ['beh', 'T03', 'W1', 0]\n  prompt_kind : 'twin_A'\n  prompt_sha256 : '55d08fb62ac8db32f7689da08a02d017ffbec1eaf9bd07a472650565c0d528b9'\n  P : 188\n  cache_len : 188\n  prefill_id : None\n  prefix_text : ''\n  prefix_ids : None\n  gen_text : '```python\\ndef solve(nums, k):\\n    nums.sort()\\n    return nums[k-1]\\n```'\n  token_ids : [73594, 12669, 198, 750, 11625, 21096, 11, 595, 982, 262, 10307, 10614, 741, 262, 470, 10307, 6732, 12, 16, 921, 73594]\n  n_new_tokens : 21\n  finish_reason : 'fence'\n  logprob_sum : -0.1340830030066036\n  veto : None\n  veto_fired : False\n  fire_step : None\n  fire_context : None\n  n_redraws : 0\n  redraw_steps : []\n  n_completions_drawn : 0\n  batch_id : 'S4|T03|188|1792521104'\n  batch_B : 40\n  batch_steps : 20\n  pruned_at : None\n  utc : '2026-10-20T18:31:46.776949Z'\n  token_ids_file : 'data/samples_raw.jsonl'\n  label : 'full_sort'\n  labeller_source : 'runtime+ast'\n  passed : True\n  runtime_label : 'full_sort'\n  ast_label : 'full_sort'\n  judge_label : None\n  valid : True\n  n_pass : 60\n  n_cases : 60\n  code : 'def solve(nums, k):\\n    nums.sort()\\n    return nums[k-1]\\n'\n  code_sha256 : 'f10fd15169b5d847f5b789707d5af4ab019681daa7e41912643507156201a4db'\n  text : '```python\\ndef solve(nums, k):\\n    nums.sort()\\n    return nums[k-1]\\n```'\n  is_default : True", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
````

### [59] THINKING · 2026-10-26 10:25:03 UTC

```
Since programs are short (T03 defaults to 21 tokens), generating full ones with a small model stays cheap. Next I'll check the candidate CRN slots for the live engine cell, comparing labels against Qwen3-8B texts per arm for T06 and T03 under W1.
```

### [60] TOOL CALL — Bash · 2026-10-26 10:25:03 UTC

```
Show Qwen3-8B outputs per arm for candidate CRN slots:
A=/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16; python3 -I - "$A/data/samples.jsonl" <<'EOF'
import json, sys
want = {(t, "W1", k) for t in ("T06", "T03") for k in range(3)}
rows = {}
with open(sys.argv[1]) as fh:
    for line in fh:
        if '"arm": "' not in line:
            continue
        r = json.loads(line)
        key = (r["task"], r["template"], r["k"])
        if key in want and r["arm"] in ("a", "b", "c", "d", "K0"):
            rows[(key, r["arm"])] = r  # last row per uid wins
for key in sorted(want):
    print("==", key)
    for a in ("a", "b", "c", "d", "K0"):
        r = rows.get((key, a))
        if r: print(f"  {a:3s} {r['label']:15s} pass={r['passed']} ntok={r['n_new_tokens']:4d} {r['gen_text'][:150]!r}")
EOF
```

### [61] TOOL RESULT — Bash · 2026-10-26 10:25:03 UTC

````
{"stdout": "== ('T03', 'W1', 0)\n  a   quickselect     pass=True ntok= 198 '```python\\ndef solve(nums, k):\\n    def partition(arr, low, high):\\n        pivot = arr[high]\\n        i = low\\n        for j in range(low, high):\\n        '\n  b   full_sort       pass=True ntok=  21 '```python\\ndef solve(nums, k):\\n    nums.sort()\\n    return nums[k-1]\\n```'\n  c   quickselect     pass=True ntok= 198 '```python\\ndef solve(nums, k):\\n    def partition(arr, low, high):\\n        pivot = arr[high]\\n        i = low\\n        for j in range(low, high):\\n        '\n  d   quickselect     pass=True ntok= 198 '```python\\ndef solve(nums, k):\\n    def partition(arr, low, high):\\n        pivot = arr[high]\\n        i = low\\n        for j in range(low, high):\\n        '\n  K0  quickselect     pass=True ntok= 198 '```python\\ndef solve(nums, k):\\n    def partition(arr, low, high):\\n        pivot = arr[high]\\n        i = low\\n        for j in range(low, high):\\n        '\n== ('T03', 'W1', 1)\n  a   quickselect     pass=True ntok= 198 '```python\\ndef solve(nums, k):\\n    def partition(arr, low, high):\\n        pivot = arr[high]\\n        i = low\\n        for j in range(low, high):\\n        '\n  b   full_sort       pass=True ntok=  19 '```python\\ndef solve(nums, k):\\n    return sorted(nums)[k-1]\\n```'\n  c   quickselect     pass=True ntok= 198 '```python\\ndef solve(nums, k):\\n    def partition(arr, low, high):\\n        pivot = arr[high]\\n        i = low\\n        for j in range(low, high):\\n        '\n  d   quickselect     pass=True ntok= 198 '```python\\ndef solve(nums, k):\\n    def partition(arr, low, high):\\n        pivot = arr[high]\\n        i = low\\n        for j in range(low, high):\\n        '\n  K0  quickselect     pass=True ntok= 198 '```python\\ndef solve(nums, k):\\n    def partition(arr, low, high):\\n        pivot = arr[high]\\n        i = low\\n        for j in range(low, high):\\n        '\n== ('T03', 'W1', 2)\n  a   quickselect     pass=True ntok= 198 '```python\\ndef solve(nums, k):\\n    def partition(arr, low, high):\\n        pivot = arr[high]\\n        i = low\\n        for j in range(low, high):\\n        '\n  b   full_sort       pass=True ntok=  21 '```python\\ndef solve(nums, k):\\n    nums.sort()\\n    return nums[k-1]\\n```'\n  c   quickselect     pass=True ntok= 198 '```python\\ndef solve(nums, k):\\n    def partition(arr, low, high):\\n        pivot = arr[high]\\n        i = low\\n        for j in range(low, high):\\n        '\n  d   quickselect     pass=True ntok= 198 '```python\\ndef solve(nums, k):\\n    def partition(arr, low, high):\\n        pivot = arr[high]\\n        i = low\\n        for j in range(low, high):\\n        '\n  K0  quickselect     pass=True ntok= 198 '```python\\ndef solve(nums, k):\\n    def partition(arr, low, high):\\n        pivot = arr[high]\\n        i = low\\n        for j in range(low, high):\\n        '\n== ('T06', 'W1', 0)\n  a   index_marking   pass=True ntok=  49 '```python\\ndef solve(nums):\\n    while nums[0] != nums[nums[0]]:\\n        nums[nums[0]], nums[0] = nums[0], nums[nums[0]]\\n    return nums[0]\\n```'\n  b   hash_set        pass=True ntok=  34 '```python\\ndef solve(nums):\\n    seen = set()\\n    for num in nums:\\n        if num in seen:\\n            return num\\n        seen.add(num)\\n```'\n  c   hash_set        pass=True ntok=  34 '```python\\ndef solve(nums):\\n    seen = set()\\n    for num in nums:\\n        if num in seen:\\n            return num\\n        seen.add(num)\\n```'\n  d   hash_set        pass=True ntok=  33 '```python\\ndef solve(nums):\\n    seen = []\\n    for num in nums:\\n        if num in seen:\\n            return num\\n        seen.append(num)\\n```'\n  K0  hash_set        pass=True ntok=  34 '```python\\ndef solve(nums):\\n    seen = set()\\n    for num in nums:\\n        if num in seen:\\n            return num\\n        seen.add(num)\\n```'\n== ('T06', 'W1', 1)\n  a   index_marking   pass=True ntok=  53 '```python\\ndef solve(nums):\\n    for i in range(len(nums)):\\n        if nums[abs(nums[i]) - 1] < 0:\\n            return abs(nums[i])\\n        nums[abs(nums'\n  b   hash_set        pass=True ntok=  39 '```python\\ndef solve(nums):\\n    seen = set()\\n    for num in nums:\\n        if num in seen:\\n            return num\\n        seen.add(num)\\n    return -1\\n``'\n  c   hash_set        pass=True ntok=  34 '```python\\ndef solve(nums):\\n    seen = set()\\n    for num in nums:\\n        if num in seen:\\n            return num\\n        seen.add(num)\\n```'\n  d   index_marking   pass=True ntok=  53 '```python\\ndef solve(nums):\\n    for i in range(len(nums)):\\n        if nums[abs(nums[i]) - 1] < 0:\\n            return abs(nums[i])\\n        nums[abs(nums'\n  K0  hash_set        pass=True ntok=  34 '```python\\ndef solve(nums):\\n    seen = set()\\n    for num in nums:\\n        if num in seen:\\n            return num\\n        seen.add(num)\\n```'\n== ('T06', 'W1', 2)\n  a   index_marking   pass=True ntok=  53 '```python\\ndef solve(nums):\\n    for i in range(len(nums)):\\n        if nums[abs(nums[i]) - 1] < 0:\\n            return abs(nums[i])\\n        nums[abs(nums'\n  b   hash_set        pass=True ntok=  34 '```python\\ndef solve(nums):\\n    seen = set()\\n    for num in nums:\\n        if num in seen:\\n            return num\\n        seen.add(num)\\n```'\n  c   hash_set        pass=True ntok=  34 '```python\\ndef solve(nums):\\n    seen = set()\\n    for num in nums:\\n        if num in seen:\\n            return num\\n        seen.add(num)\\n```'\n  d   index_marking   pass=True ntok=  49 '```python\\ndef solve(nums):\\n    while nums[0] != nums[nums[0]]:\\n        nums[nums[0]], nums[0] = nums[0], nums[nums[0]]\\n    return nums[0]\\n```'\n  K0  hash_set        pass=True ntok=  34 '```python\\ndef solve(nums):\\n    seen = set()\\n    for num in nums:\\n        if num in seen:\\n            return num\\n        seen.add(num)\\n```'", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
````

### [62] THINKING · 2026-10-26 10:25:11 UTC

```
T06/W1 slots k=1 and k=2 confirm the "direct route only" pattern—arm d matches the ban's `index_marking` program exactly under CRN while c and K0 default to `hash_set`—so this is the right slot set for the live engine cell. Next, I'll check the install timings.
```

### [63] TOOL CALL — Bash · 2026-10-26 10:25:11 UTC

```
Read venv install timing output:
cat /tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-3-art--5akZ9W9iZM4/c71db1cb-129d-4e37-954d-e401f6949d31/tasks/br19m1lqh.output
```

### [64] TOOL RESULT — Bash · 2026-10-26 10:25:11 UTC

```
{"stdout": "venv+jupyter: 3s\ntorch cpu: 15s\nrest: 20s\n2.9.0+cpu 5.0.0 2.0.2 1.16.3 0.14.6\n\n[exited with code 0]", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [65] THINKING · 2026-10-26 10:25:33 UTC

```
Installs completed quickly (~40s) with torch 2.9.0+cpu and transformers 5.0.0 resolving fine. Now I'll run the artifact's own engine.py (KO attention registration, prefill, splice, drop_span, CRN sample) on CPU with Qwen3-0.6B for one T06/W1 slot to check feasibility and timing.
```

### [66] TOOL CALL — Bash · 2026-10-26 10:25:33 UTC

```
Prototype engine CRN slot with Qwen3-0.6B on CPU:
cd /tmp/aii_nb_test_envs && A=/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16 && timeout 900 /tmp/aii_nb_test_envs/art__5akZ9W9iZM4-bfb6955ec1d9/bin/python - "$A" <<'EOF'
import sys, json, time
A = sys.argv[1]
sys.path.insert(0, A + "/src")
import torch
torch.set_num_threads(2)
import engine
from engine import register, prefill, splice, drop_span, sample, u_stream
from transformers import AutoModelForCausalLM, AutoTokenizer
t0 = time.time()
register()
tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B")
model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3-0.6B", dtype=torch.float32, attn_implementation="ko_sdpa")
model.eval()
print("load", round(time.time()-t0,1), "s", model.config._attn_implementation, model.device)
pr = {}
for l in open(A + "/prompts/prompts.jsonl"):
    r = json.loads(l)
    if r["task"] == "T06" and r["w"] == "W1": pr[r["kind"]] = r
ban, ta = pr["ban"], pr["twin_A"]
P, p0, p1 = ban["P"], ban["p0"], ban["p1"]
print("P", P, "p0", p0, "p1", p1, repr(ban["cond"]), repr(ta["cond"]))
print(repr(tok.decode(ban["ids"])[:400]))
t1 = time.time()
X = prefill(model, ban["ids"]); Aa = prefill(model, ta["ids"])
print("prefill x2", round(time.time()-t1,1), "s")
arms = {"a": {"kv": X["kv"], "r_logits": X["r_logits"]},
        "b": {"kv": Aa["kv"], "r_logits": Aa["r_logits"]},
        "c": {"kv": splice(Aa["kv"], X["kv"], p1), "r_logits": X["r_logits"]},
        "d": {"kv": splice(X["kv"], Aa["kv"], p1), "r_logits": Aa["r_logits"]}}
k0 = {"kv": drop_span(X["kv"], p0, p1), "r_logits": X["r_logits"], "pos0": P}
vocab = tok.convert_ids_to_tokens(list(range(len(tok))))
tick_ids = {i for i, s in enumerate(vocab) if s and "`" in s}
dec = lambda ids: tok.decode(ids, skip_special_tokens=True)
k = 1
uk = ("beh", "T06", "W1", k)
rows = [{"kv": st["kv"], "r_logits": st["r_logits"], "u": u_stream(*uk), "stop": "bench"} for st in arms.values()]
t2 = time.time()
res = sample(model, rows, max_new=120, tick_ids=tick_ids, decode=dec)
print("sample a-d", round(time.time()-t2,1), "s, steps", res[0]["steps"])
t3 = time.time()
resk = sample(model, [{"kv": k0["kv"], "r_logits": k0["r_logits"], "u": u_stream(*uk), "pos0": P, "stop": "bench"}], max_new=120, tick_ids=tick_ids, decode=dec)
print("sample K0", round(time.time()-t3,1), "s, steps", resk[0]["steps"])
for name, r in list(zip(arms, res)) + [("K0", resk[0])]:
    print("---", name, r["finish_reason"], r["n_tokens"]); print(dec(r["token_ids"]))
EOF
```

### [67] TOOL RESULT — Bash · 2026-10-26 10:25:53 UTC

```
{"stdout": "\rLoading weights:   0%|          | 0/311 [00:00<?, ?it/s]\rLoading weights:   0%|          | 1/311 [00:00<00:00, 15420.24it/s, Materializing param=lm_head.weight]\rLoading weights:   0%|          | 1/311 [00:00<00:00, 7570.95it/s, Materializing param=lm_head.weight] \rLoading weights:   1%|          | 2/311 [00:01<02:49,  1.82it/s, Materializing param=lm_head.weight]  \rLoading weights:   1%|          | 2/311 [00:01<02:49,  1.82it/s, Materializing param=model.embe... [truncated, 29742 chars total]
```

### [68] TOOL CALL — Bash · 2026-10-26 10:25:55 UTC

```
Show prototype output without progress bars:
F=/var/lib/aii-agent/claude/projects/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-3-art--5akZ9W9iZM4/c71db1cb-129d-4e37-954d-e401f6949d31/tool-results/b6hj09s1e.txt; tr '\r' '\n' < $F | grep -v "Loading weights" | head -120
```

### [69] TOOL RESULT — Bash · 2026-10-26 10:25:55 UTC

````
{"stdout": "The tied weights mapping and config for this model specifies to tie model.embed_tokens.weight to lm_head.weight, but both are present in the checkpoints, so we will NOT tie them. You should update the config with `tie_word_embeddings=False` to silence this warning\nload 4.7 s ko_sdpa cpu\nP 142 p0 3 p1 16 'Do not use a hash set of seen values for this task.' 'Do not use fire for this task. . . . . .'\n'<|im_start|>user\\nDo not use a hash set of seen values for this task.\\n\\nTask: write a Python function solve(nums) that returns the repeated value in nums. The argument nums is a list of n + 1 integers, where 1 <= n <= 10000, and every value lies between 1 and n inclusive. Exactly one value occurs more than once, and it may occur two or more times; every other value occurs at most once. Return the re'\nprefill x2 2.6 s\nsample a-d 8.8 s, steps 34\nsample K0 3.0 s, steps 22\n--- a fence 34\n```python\ndef solve(nums):\n    seen = set()\n    for num in nums:\n        if num in seen:\n            return num\n        seen.add(num)\n```\n--- b fence 35\n```python\ndef solve(nums):\n    return {v: i for i, v in enumerate(nums)}.get(None, None)  # Get the first repeated value\n```\n--- c fence 29\n```python\ndef solve(nums):\n    return {x for x in nums if x != nums[i] for i in range(len(nums))}\n```\n--- d fence 34\n```python\ndef solve(nums):\n    seen = set()\n    for num in nums:\n        if num in seen:\n            return num\n        seen.add(num)\n```\n--- K0 fence 23\n```python\ndef solve(nums):\n    return {x for x in nums if x != nums.index(x)}\n```", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
````

### [70] THINKING · 2026-10-26 10:27:19 UTC

```
The engine works fine unchanged on CPU with transformers 5.0/torch 2.9 using Qwen3-0.6B, but the small model ignores the ban (arm a still writes `seen = set()`), so I'll pair this live run with the Qwen3-8B rows for the same CRN slot. Now I'll use NotebookEdit to update the TODO names.
```

### [71] TOOL CALL — ToolSearch · 2026-10-26 10:27:19 UTC

```
{'query': 'select:NotebookEdit', 'max_results': 1}
```

### [72] TOOL RESULT — ToolSearch · 2026-10-26 10:27:19 UTC

```
{"matches": ["NotebookEdit"], "query": "select:NotebookEdit", "total_deferred_tools": 24}
```

### [73] THINKING · 2026-10-26 10:27:39 UTC

```
I'll build the notebook starting with a one-cell skeleton, inserting the rest via NotebookEdit. First, let me check the frozen n-gram file that `crn_analysis` reads to get the data.
```

### [74] TOOL CALL — Bash · 2026-10-26 10:27:39 UTC

```
Inspect the frozen distinctive n-gram predictions:
A=/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16; python3 -I -c "
import json
n=json.load(open('$A/predictions/ngrams.json'))
print(list(n.keys()))
for t in ['T06','T03','R1']:
    print(t, {k:(v if not isinstance(v,(list,dict)) or len(str(v))<200 else str(v)[:200]) for k,v in n[t].items()})
"
```

### [75] TOOL RESULT — Bash · 2026-10-26 10:27:39 UTC

```
{"stdout": "['T03', 'T04', 'T06', 'T05', 'T10', 'R1', 'T08', 'R3', 'T13', 'R6', 'T14', 'T11', 't1', 't2']\nT06 {'defined': True, 'ids': [738], 'n': 1, 'baseline_frequency': 1.0, 'max_collateral': 0.0, 'collateral': {'sort_adjacent': 0.0, 'floyd': 0.0, 'value_binary_search': 0.0, 'index_marking': 0.0}, 'co_vetoed': [], 'median_first_occurrence': 10.0, 'n_candidates': 173, 'n_baseline': 50, 'n_forced': {'sort_adjacent': 35, 'floyd': 40, 'value_binary_search': 40, 'index_marking': 1}, 'task': 'T06', 'default': 'hash_set', 'baseline_source': 'bench pilot_rows, label == default', 'forced_source': 'bench forced_programs.jsonl code field (unscrubbed: identical to exp11 samples_forced extract)', 'text': ' set', 'token_class': 'API call', 'tokens': [' set']}\nT03 {'defined': True, 'ids': [262, 10307], 'n': 2, 'baseline_frequency': 0.88, 'max_collateral': 0.0, 'collateral': {'size_k_heap': 0.0, 'heapify_pop': 0.0, 'quickselect': 0.0, 'median_of_medians': 0.0, 'counting_sort': 0.0}, 'co_vetoed': [], 'median_first_occurrence': 9.0, 'n_candidates': 108, 'n_baseline': 50, 'n_forced': {'size_k_heap': 36, 'heapify_pop': 29, 'quickselect': 40, 'median_of_medians': 40, 'counting_sort': 29}, 'task': 'T03', 'default': 'full_sort', 'baseline_source': 'bench pilot_rows, label == default', 'forced_source': 'bench forced_programs.jsonl code field (unscrubbed: identical to exp11 samples_forced extract)', 'text': '    nums', 'token_class': 'identifier', 'tokens': ['   ', ' nums']}\nR1 {'defined': True, 'ids': [75781], 'n': 1, 'baseline_frequency': 0.88, 'max_collateral': 0.0, 'collateral': {'dp_bisect': 0.0, 'memo_recursion': 0.0, 'dag_longest_path': 0.0}, 'co_vetoed': [], 'median_first_occurrence': 64.0, 'n_candidates': 318, 'n_baseline': 50, 'n_forced': {'dp_bisect': 1, 'memo_recursion': 39, 'dag_longest_path': 3}, 'task': 'R1', 'default': 'greedy_end', 'baseline_source': 'bench pilot_rows, label == default', 'forced_source': 'bench forced_programs.jsonl code field (unscrubbed: identical to exp11 samples_forced extract)', 'text': ':]:\\n', 'token_class': 'structural', 'tokens': [':]:\\n']}", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [76] ASSISTANT · 2026-10-26 10:28:09 UTC

```
I have everything needed for the demo data. Writing the builder script into the workspace (kept as a reproducibility deliverable), applying the selection rule chosen above.
```

### [77] TOOL CALL — Write · 2026-10-26 10:28:09 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/scripts/build_mini_demo_data.py

#!/usr/bin/env python3
"""Build mini_demo_data.json for code_demo.ipynb from the experiment-16 artifact folder (read-only).

The examples are a curated subset of ONE dataset, `route_arms` of full_method_out.json: one example per CRN slot
(task, template, slot k), output = arm-a (full ban) label, predict_<arm> = '<label>|pass|fail' or 'not_run'.
Selection rule (fixed in advance, no outcome-based picking):
  - the 5 gated tasks (frozen gate, all 100 arm-a rows per task): slots k = 0, 1, 2 of every template W1-W5 -> 75
  - the first 5 non-gated tasks in STAGE_A order (T04, R1, T08, R3, R6): slot k = 0 of every template -> 25
Each example also carries the generated token ids of its five arms (from data/samples.jsonl, last row per uid), which
the CRN flip / first-divergence analysis needs.

metadata carries the small frozen inputs the notebook reads instead of files: the gate (results/gate.json), the
commit-#2 veto classes (predictions/c2c.json), the distinctive n-grams (predictions/ngrams.json), the mechanism
catalogues (bench spec.json), full-run reference numbers for comparison, and one CRN slot set (T06 / W1 / k = 0-2:
frozen prompt ids + the Qwen3-8B rows) for the live engine cell.

usage: python scripts/build_mini_demo_data.py <artifact_dir> mini_demo_data.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

STAGE_A = ["T03", "T04", "T06", "T05", "T10", "R1", "T08", "R3", "T13", "R6", "T14", "T11"]
TEMPLATE_IDS = ["W1", "W2", "W3", "W4", "W5"]
TASK_DIR = {"T03": "T03_kth_smallest", "T04": "T04_substring_search", "T06": "T06_find_duplicate",
            "T05": "T05_two_sum", "T10": "T10_connected_components", "R1": "R1_non_overlapping_intervals",
            "T08": "T08_fibonacci", "R3": "R3_topological_order", "T13": "T13_merge_intervals",
            "R6": "R6_first_last_position", "T14": "T14_top_k_frequent", "T11": "T11_longest_increasing_subsequence"}
ARMS = ("a", "b", "c", "d", "K0")
GATED_SLOTS = 3        # k = 0..2 per template on gated tasks
NONGATED_TASKS = 5     # first five non-gated tasks in STAGE_A order
NONGATED_SLOTS = 1     # k = 0 per template
ENGINE = {"task": "T06", "template": "W1", "ks": [0, 1, 2]}


def read_jsonl(p: Path) -> list[dict]:
    with open(p) as fh:
        return [json.loads(line) for line in fh if line.strip()]


def main() -> None:
    art, out = Path(sys.argv[1]), Path(sys.argv[2])
    full = json.loads((art / "full_method_out.json").read_text())
    meta = full["metadata"]
    route = next(d for d in full["datasets"] if d["dataset"] == "route_arms")["examples"]

    gate = meta["gate"]
    gated = [t for t in STAGE_A if gate[t]["gated"]]
    nongated = [t for t in STAGE_A if not gate[t]["gated"]][:NONGATED_TASKS]
    n_slots = {**{t: GATED_SLOTS for t in gated}, **{t: NONGATED_SLOTS for t in nongated}}
    order = {t: i for i, t in enumerate(STAGE_A)}
    examples = [e for e in route if e["metadata_task"] in n_slots and e["metadata_k"] < n_slots[e["metadata_task"]]]
    examples.sort(key=lambda e: (order[e["metadata_task"]], e["metadata_template"], e["metadata_k"]))
    assert len(examples) == 100, len(examples)

    # token ids (and, for the engine slot set, the full rows) from the labelled samples; last row per uid wins
    want = {(e["metadata_task"], e["metadata_template"], e["metadata_k"]) for e in examples}
    rows: dict[tuple, dict] = {}
    with open(art / "data" / "samples.jsonl") as fh:
        for line in fh:
            r = json.loads(line)
            if r["arm"] in ARMS and (r["task"], r["template"], r["k"]) in want:
                rows[(r["task"], r["template"], r["k"], r["arm"])] = r
    for e in examples:
        key = (e["metadata_task"], e["metadata_template"], e["metadata_k"])
        e["metadata_token_ids"] = {a: rows[key + (a,)]["token_ids"] for a in ARMS if key + (a,) in rows}
        for a in ("b", "c", "d", "K0"):  # consistency: the dataset label is the labelled row's label
            if key + (a,) in rows:
                assert e[f"predict_{a}"].split("|")[0] == rows[key + (a,)]["label"], (key, a)

    prompts = {(r["task"], r["w"], r["kind"]): r for r in read_jsonl(art / "prompts" / "prompts.jsonl")}
    t, w = ENGINE["task"], ENGINE["template"]
    engine_slot = {
        "task": t, "template": w, "ks": ENGINE["ks"], "u_key": ["beh", t, w, "<k>"],
        "note": "frozen Qwen3 prompt ids (ban / token-length-matched neutral twin_A) and the Qwen3-8B rows of the same "
                "CRN slots (same uniforms) from data/samples.jsonl",
        "prompts": {kind: {f: prompts[(t, w, kind)][f] for f in ("kind", "cond", "ids", "p0", "p1", "P", "prompt_sha256")}
                    for kind in ("ban", "twin_A")},
        "qwen3_8b_rows": {str(k): {a: {f: rows[(t, w, k, a)][f] for f in ("label", "passed", "gen_text", "token_ids",
                                                                         "n_new_tokens", "finish_reason")}
                                   for a in ARMS} for k in ENGINE["ks"]},
    }

    ngrams = json.loads((art / "predictions" / "ngrams.json").read_text())
    c2c = json.loads((art / "predictions" / "c2c.json").read_text())
    catalogue = {t: [c["mode"] for c in json.loads((art / "inputs" / "bench" / TASK_DIR[t] / "spec.json").read_text())
                     ["catalogue"]] for t in STAGE_A}
    c2a = meta["C2a"]
    reference = {
        "note": "headline numbers of the full run (all 13,030 samples; N = 100 CRN slots per task and arm)",
        "C2a": {"verdict": c2a["verdict"], "verdict_by_interval": c2a["verdict_by_interval"], "point": c2a["point"],
                "intervals": c2a["intervals"], "per_task": c2a["per_task"],
                "p_boot_F_prompt_le_half": c2a["p_boot_F_prompt_le_half"],
                "p_boot_F_direct_ge_third": c2a["p_boot_F_direct_ge_third"],
                "mixed_glm": {k: c2a["mixed_glm"][k] for k in ("F_prompt_glm", "F_direct_glm")}},
        "C2c": {k: meta["C2c"][k] for k in ("hit_fraction", "spearman_rho", "perm_p_one_sided", "decision", "n_points")},
        "shares": {t: {a: meta["shares"][t][a]["s"] for a in ARMS if a in meta["shares"][t]} for t in STAGE_A},
    }

    demo = {
        "metadata": {
            "description": "Curated demo subset of the route_arms dataset of 'Where a coding ban takes effect in "
                           "Qwen3-8B' (CRN-coupled KV-splice route test on 12 frozen bench tasks).",
            "source": "full_method_out.json -> datasets[route_arms] (+ per-arm token ids from data/samples.jsonl)",
            "selection_rule": f"gated tasks {gated}: slots k < {GATED_SLOTS} of every template; first "
                              f"{NONGATED_TASKS} non-gated tasks in STAGE_A order {nongated}: slot k < {NONGATED_SLOTS} "
                              "of every template",
            "n_examples": len(examples),
            "example_format": "output = arm-a (full ban) label; predict_<arm> = '<mechanism label>|pass' or '|fail' "
                              "(program passed the task tests) or 'not_run'; metadata_token_ids = generated ids per arm",
            "model": meta["model"], "model_revision": meta["model_revision"], "dtype": meta["dtype"],
            "decoding": meta["decoding"], "hardware": meta["hardware"],
            "gate": gate, "gated_tasks": gated,
            "c2c_predictions": c2c,
            "ngrams": {t: {f: ngrams[t].get(f) for f in ("defined", "ids", "text", "token_class", "co_vetoed")}
                       for t in STAGE_A},
            "catalogue": catalogue,
            "full_run_reference": reference,
            "engine_slot": engine_slot,
        },
        "datasets": [{"dataset": "route_arms", "examples": examples}],
    }
    out.write_text(json.dumps(demo, indent=1))
    print(f"wrote {out} ({out.stat().st_size / 1e3:.0f} kB): {len(examples)} examples; gated={gated}; "
          f"non-gated={nongated}")


if __name__ == "__main__":
    main()
```

### [78] TOOL RESULT — Write · 2026-10-26 10:28:09 UTC

```
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/scripts/build_mini_demo_data.py", "content": "#!/usr/bin/env python3\n\"\"\"Build mini_demo_data.json for code_demo.ipynb from the experiment-16 artifact folder (read-only).\n\nThe examples are a curated subset of ONE dataset, `route_arms` of full_method_out.json: one example per CRN slot\n(task, template, slot k), output = arm-a (full ban) label, predict_<arm> = '<label>|pass|fail' or 'not_run'.\nSelection rule (fixed in advance, no outcome-based picking):\n  - the 5 gated tasks (frozen gate, all 100 arm-a rows per task): slots k = 0, 1, 2 of every template W1-W5 -> 75\n  - the first 5 non-gated tasks in STAGE_A order (T04, R1, T08, R3, R6): slot k = 0 of every template -> 25\nEach example also carries the generated token ids of its five arms (from data/samples.jsonl, last row per uid), which\nthe CRN flip / first-divergence analysis needs.\n\nmetadata carries the small frozen inputs the notebook reads instead of files: the gate (results/gate.json), the\ncommit-#2 veto classes (predictions/c2c.json), the distinctive n-grams (predictions/ngrams.json), the mechanism\ncatalogues (bench spec.json), full-run reference numbers for comparison, and one CRN slot set (T06 / W1 / k = 0-2:\nfrozen prompt ids + the Qwen3-8B rows) for the live engine cell.\n\nusage: python scripts/build_mini_demo_data.py <artifact_dir> mini_demo_data.json\n\"\"\"\n\nfrom __future__ import annotations\n\nimport json\nimport sys\nfrom pathlib import Path\n\nSTAGE_A = [\"T03\", \"T04\", \"T06\", \"T05\", \"T10\", \"R1\", \"T08\", \"R3\", \"T13\", \"R6\", \"T14\", \"T11\"]\nTEMPLATE_IDS = [\"W1\", \"W2\", \"W3\", \"W4\", \"W5\"]\nTASK_DIR = {\"T03\": \"T03_kth_smallest\", \"T04\": \"T04_substring_search\", \"T06\": \"T06_find_duplicate\",\n            \"T05\": \"T05_two_sum\", \"T10\": \"T10_connected_components\", \"R1\": \"R1_non_overlapping_intervals\",\n            \"T08\": \"T08_fibonacci\", \"R3\": \"R3_topological_order\", \"T13\": \"T13_merge_intervals\",\n            \"R6\": \"R6_first_last_position\", \"T14\": \"T14_top_k_frequent\", \"T11\": \"T11_longest_increasing_subsequence\"}\nARMS = (\"a\", \"b\", \"c\", \"d\", \"K0\")\nGATED_SLOTS = 3        # k = 0..2 per template on gated tasks\nNONGATED_TASKS = 5     # first five non-gated tasks in STAGE_A order\nNONGATED_SLOTS = 1     # k = 0 per template\nENGINE = {\"task\": \"T06\", \"template\": \"W1\", \"ks\": [0, 1, 2]}\n\n\ndef read_jsonl(p: Path) -> list[dict]:\n    with open(p) as fh:\n        return [json.loads(line) for line in fh if line.strip()]\n\n\ndef main() -> None:\n    art, out = Path(sys.argv[1]), Path(sys.argv[2])\n    full = json.loads((art / \"full_method_out.json\").read_text())\n    meta = full[\"metadata\"]\n    route = next(d for d in full[\"datasets\"] if d[\"dataset\"] == \"route_arms\")[\"examples\"]\n\n    gate = meta[\"gate\"]\n    gated = [t for t in STAGE_A if gate[t][\"gated\"]]\n    nongated = [t for t in STAGE_A if not gate[t][\"gated\"]][:NONGATED_TASKS]\n    n_slots = {**{t: GATED_SLOTS for t in gated}, **{t: NONGATED_SLOTS for t in nongated}}\n    order = {t: i for i, t in enumerate(STAGE_A)}\n    examples = [e for e in route if e[\"metadata_task\"] in n_slots and e[\"metadata_k\"] < n_slots[e[\"metadata_task\"]]]\n    examples.sort(key=lambda e: (order[e[\"metadata_task\"]], e[\"metadata_template\"], e[\"metadata_k\"]))\n    assert len(examples) == 100, len(examples)\n\n    # token ids (and, for the engine slot set, the full rows) from the labelled samples; last row per uid wins\n    want = {(e[\"metadata_task\"], e[\"metadata_template\"], e[\"metadata_k\"]) for e in examples}\n    rows: dict[tuple, dict] = {}\n    with open(art / \"data\" / \"samples.jsonl\") as fh:\n        for line in fh:\n            r = json.loads(line)\n            if r[\"arm\"] in ARMS and (r[\"task\"], r[\"template\"], r[\"k\"]) in want:\n                rows[(r[\"task\"], r[\"template\"], r[\"k\"], r[\"arm\"])] = r\n    for e in examples:\n        key = (e[\"metadata_task\"], e[\"metadata_template\"], e[\"metadata_k\"])\n        e[\"metadata_token_ids\"] = {a: rows[key + (a,)][\"token_ids\"] for a in ARMS if key + (a,) in rows}\n        for a in (\"b\", \"c\", \"d\", \"K0\"):  # consistency: the dataset label is the labelled row's label\n            if key + (a,) in rows:\n                assert e[f\"predict_{a}\"].split(\"|\")[0] == rows[key + (a,)][\"label\"], (key, a)\n\n    prompts = {(r[\"task\"], r[\"w\"], r[\"kind\"]): r for r in read_jsonl(art / \"prompts\" / \"prompts.jsonl\")}\n    t, w = ENGINE[\"task\"], ENGINE[\"template\"]\n    engine_slot = {\n        \"task\": t, \"template\": w, \"ks\": ENGINE[\"ks\"], \"u_key\": [\"beh\", t, w, \"<k>\"],\n        \"note\": \"frozen Qwen3 prompt ids (ban / token-length-matched neutral twin_A) and the Qwen3-8B rows of the same \"\n                \"CRN slots (same uniforms) from data/samples.jsonl\",\n        \"prompts\": {kind: {f: prompts[(t, w, kind)][f] for f in (\"kind\", \"cond\", \"ids\", \"p0\", \"p1\", \"P\", \"prompt_sha256\")}\n                    for kind in (\"ban\", \"twin_A\")},\n        \"qwen3_8b_rows\": {str(k): {a: {f: rows[(t, w, k, a)][f] for f in (\"label\", \"passed\", \"gen_text\", \"token_ids\",\n                                                                         \"n_new_tokens\", \"finish_reason\")}\n                                   for a in ARMS} for k in ENGINE[\"ks\"]},\n    }\n\n    ngrams = json.loads((art / \"predictions\" / \"ngrams.json\").read_text())\n    c2c = json.loads((art / \"predictions\" / \"c2c.json\").read_text())\n    catalogue = {t: [c[\"mode\"] for c in json.loads((art / \"inputs\" / \"bench\" / TASK_DIR[t] / \"spec.json\").read_text())\n                     [\"catalogue\"]] for t in STAGE_A}\n    c2a = meta[\"C2a\"]\n    reference = {\n        \"note\": \"headline numbers of the full run (all 13,030 samples; N = 100 CRN slots per task and arm)\",\n        \"C2a\": {\"verdict\": c2a[\"verdict\"], \"verdict_by_interval\": c2a[\"verdict_by_interval\"], \"point\": c2a[\"point\"],\n                \"intervals\": c2a[\"intervals\"], \"per_task\": c2a[\"per_task\"],\n                \"p_boot_F_prompt_le_half\": c2a[\"p_boot_F_prompt_le_half\"],\n                \"p_boot_F_direct_ge_third\": c2a[\"p_boot_F_direct_ge_third\"],\n                \"mixed_glm\": {k: c2a[\"mixed_glm\"][k] for k in (\"F_prompt_glm\", \"F_direct_glm\")}},\n        \"C2c\": {k: meta[\"C2c\"][k] for k in (\"hit_fraction\", \"spearman_rho\", \"perm_p_one_sided\", \"decision\", \"n_points\")},\n        \"shares\": {t: {a: meta[\"shares\"][t][a][\"s\"] for a in ARMS if a in meta[\"shares\"][t]} for t in STAGE_A},\n    }\n\n    demo = {\n        \"metadata\": {\n            \"description\": \"Curated demo subset of the route_arms dataset of 'Where a coding ban takes effect in \"\n                           \"Qwen3-8B' (CRN-coupled KV-splice route test on 12 frozen bench tasks).\",\n            \"source\": \"full_method_out.json -> datasets[route_arms] (+ per-arm token ids from data/samples.jsonl)\",\n            \"selection_rule\": f\"gated tasks {gated}: slots k < {GATED_SLOTS} of every template; first \"\n                              f\"{NONGATED_TASKS} non-gated tasks in STAGE_A order {nongated}: slot k < {NONGATED_SLOTS} \"\n                              \"of every template\",\n            \"n_examples\": len(examples),\n            \"example_format\": \"output = arm-a (full ban) label; predict_<arm> = '<mechanism label>|pass' or '|fail' \"\n                              \"(program passed the task tests) or 'not_run'; metadata_token_ids = generated ids per arm\",\n            \"model\": meta[\"model\"], \"model_revision\": meta[\"model_revision\"], \"dtype\": meta[\"dtype\"],\n            \"decoding\": meta[\"decoding\"], \"hardware\": meta[\"hardware\"],\n            \"gate\": gate, \"gated_tasks\": gated,\n            \"c2c_predictions\": c2c,\n            \"ngrams\": {t: {f: ngrams[t].get(f) for f in (\"defined\", \"ids\", \"text\", \"token_class\", \"co_vetoed\")}\n                       for t in STAGE_A},\n            \"catalogue\": catalogue,\n            \"full_run_reference\": reference,\n            \"engine_slot\": engine_slot,\n        },\n        \"datasets\": [{\"dataset\": \"route_arms\", \"examples\": examples}],\n    }\n    out.write_text(json.dumps(demo, indent=1))\n    print(f\"wrote {out} ({out.stat().st_size / 1e3:.0f} kB): {len(examples)} examples; gated={gated}; \"\n          f\"non-gated={nongated}\")\n\n\nif __name__ == \"__main__\":\n    main()\n", "structuredPatch": [], "originalFile": null, "userModified": false}
```

### [79] TOOL CALL — Bash · 2026-10-26 10:28:15 UTC

```
Build mini_demo_data.json and verify its contents:
python3 -I scripts/build_mini_demo_data.py /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16 mini_demo_data.json && ls -la mini_demo_data.json && python3 -I -c "
import json
d=json.load(open('mini_demo_data.json'))
ex=d['datasets'][0]['examples']
from collections import Counter
print(Counter(e['metadata_task'] for e in ex))
print(Counter(len(e['metadata_token_ids']) for e in ex))
print({k: (len(v) if hasattr(v,'__len__') else v) for k,v in d['metadata'].items()})
e=ex[0]; print({k:(v if k!='metadata_token_ids' else {a:len(x) for a,x in v.items()}) for k,v in e.items()})
"
```

### [80] TOOL RESULT — Bash · 2026-10-26 10:28:15 UTC

```
{"stdout": "wrote mini_demo_data.json (748 kB): 100 examples; gated=['T03', 'T06', 'T05', 'T10', 'T13']; non-gated=['T04', 'R1', 'T08', 'R3', 'R6']\n-rw-rw-rw- 1 aii-agent aii-agent 747988 Oct 26 10:28 mini_demo_data.json\nCounter({'T03': 15, 'T06': 15, 'T05': 15, 'T10': 15, 'T13': 15, 'T04': 5, 'R1': 5, 'T08': 5, 'R3': 5, 'R6': 5})\nCounter({5: 100})\n{'description': 155, 'source': 90, 'selection_rule': 183, 'n_examples': 100, 'example_format': 173, 'model': 13, 'model_revision': 40, 'dtype': 8, 'decoding': 73, 'hardware': 38, 'gate': 12, 'gated_tasks': 5, 'c2c_predictions': 12, 'ngrams': 12, 'catalogue': 12, 'full_run_reference': 4, 'engine_slot': 7}\n{'input': \"task T03 | template W1 | slot k=0 | ban segment: 'Do not use a full sort for this task.' | neutral twin: 'Do not use man for this task. . .'\", 'output': 'quickselect', 'metadata_task': 'T03', 'metadata_template': 'W1', 'metadata_k': 0, 'metadata_default': 'full_sort', 'metadata_gated': True, 'metadata_a_passed': True, 'predict_b': 'full_sort|pass', 'predict_c': 'quickselect|pass', 'predict_d': 'quickselect|pass', 'predict_K0': 'quickselect|pass', 'metadata_token_ids': {'a': 198, 'b': 21, 'c': 198, 'd': 198, 'K0': 198}}", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [81] THINKING · 2026-10-26 10:30:29 UTC

```
I've built mini_demo_data.json with 100 route_arms slots and the frozen inputs. Since Qwen3-0.6B ignored the T06 ban, I'll check in the background whether it respects the ban on any other task/template to pick the most informative slot set, while also fetching the pinned model revision.
```

### [82] TOOL CALL — Bash · 2026-10-26 10:30:29 UTC

```
Test whether Qwen3-0.6B follows bans on several tasks:
cd /tmp/aii_nb_test_envs && A=/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16 && timeout 1200 /tmp/aii_nb_test_envs/art__5akZ9W9iZM4-bfb6955ec1d9/bin/python - "$A" 2>&1 <<'EOF' | tr '\r' '\n' | grep -v "Loading weights"
import sys, json, time
A = sys.argv[1]
sys.path.insert(0, A + "/src")
import torch
from engine import register, prefill, sample, u_stream
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.utils import logging as hl
hl.disable_progress_bar()
register()
tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B")
model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3-0.6B", dtype=torch.float32, attn_implementation="ko_sdpa").eval()
pr = {}
for l in open(A + "/prompts/prompts.jsonl"):
    r = json.loads(l); pr[(r["task"], r["w"], r["kind"])] = r
vocab = tok.convert_ids_to_tokens(list(range(len(tok))))
tick_ids = {i for i, s in enumerate(vocab) if s and "`" in s}
dec = lambda ids: tok.decode(ids, skip_special_tokens=True)
for task, ws in (("T03", ["W1", "W3", "W5"]), ("T06", ["W2", "W5"]), ("T10", ["W1"]), ("T05", ["W1"])):
    for w in ws:
        X = prefill(model, pr[(task, w, "ban")]["ids"]); Aa = prefill(model, pr[(task, w, "twin_A")]["ids"])
        rows = []
        for k in range(3):
            uk = ("beh", task, w, k)
            rows += [{"kv": X["kv"], "r_logits": X["r_logits"], "u": u_stream(*uk), "stop": "bench"},
                     {"kv": Aa["kv"], "r_logits": Aa["r_logits"], "u": u_stream(*uk), "stop": "bench"}]
        t0 = time.time()
        res = sample(model, rows, max_new=160, tick_ids=tick_ids, decode=dec)
        print(f"===== {task} {w} cond={pr[(task, w, 'ban')]['cond']!r} ({time.time()-t0:.0f}s, steps {res[0]['steps']})")
        for i, r in enumerate(res):
            body = dec(r["token_ids"]).replace("\n", " \\n ")
            print(f"  k={i//2} {'a(ban)' if i%2==0 else 'b(twin)'} {r['finish_reason']:6s} {body[:230]}")
EOF
```

### [83] TOOL RESULT — Bash · 2026-10-26 10:30:29 UTC

```
{"stdout": "", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false, "backgroundTaskId": "bt22a3kph", "backgroundCwdHint": "Session cwd remains /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4; directory changes made by the backgrounded command do not apply to subsequent commands."}
```

### [84] TOOL CALL — Bash · 2026-10-26 10:30:29 UTC

```
Get cached Qwen3-0.6B revision and config:
ls $HF_HUB_CACHE/models--Qwen--Qwen3-0.6B/snapshots/; cat $HF_HUB_CACHE/models--Qwen--Qwen3-0.6B/refs/main 2>/dev/null; echo; python3 -c "import json;c=json.load(open('$(ls -d $HF_HUB_CACHE/models--Qwen--Qwen3-0.6B/snapshots/*)/config.json'));print({k:c[k] for k in ('num_hidden_layers','num_key_value_heads','head_dim','vocab_size','tie_word_embeddings','torch_dtype') if k in c})"
```

### [85] TOOL RESULT — Bash · 2026-10-26 10:30:29 UTC

```
{"stdout": "c1899de289a04d12100db370d81485cdf75e47ca\nc1899de289a04d12100db370d81485cdf75e47ca\n{'num_hidden_layers': 28, 'num_key_value_heads': 8, 'head_dim': 128, 'vocab_size': 151936, 'tie_word_embeddings': True, 'torch_dtype': 'bfloat16'}", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [86] ASSISTANT · 2026-10-26 10:32:15 UTC

```
Pinned revision for Qwen3-0.6B: `c1899de2…`. Now TODO 4. I'll create a minimal valid notebook holding the title cell, then add every other cell with NotebookEdit.
```

### [87] TOOL CALL — Write · 2026-10-26 10:32:15 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb

{
 "cells": [
  {
   "cell_type": "markdown",
   "id": "title",
   "metadata": {},
   "source": [
    "# Where a coding ban takes effect in Qwen3-8B: route-test demo\n",
    "\n",
    "**Artifact:** experiment-16 (`art__5akZ9W9iZM4`) of *Prompt bans substitute, not just subtract*.\n",
    "\n",
    "A prompt ban such as *\"Do not use a hash set of seen values for this task.\"* makes Qwen3-8B (bf16, thinking off) write a different algorithm. This experiment asks **which internal route carries that effect**, on the 12 frozen coding tasks of the bench. Every arm of a CRN slot `(task, template, k)` is sampled with the same **common random numbers** (CRN): one fixed stream of uniforms, turned into tokens by inverse-CDF sampling. The arms are built by **splicing KV caches** by position, so they differ only in the cache their generated tokens read:\n",
    "\n",
    "| arm | cache read by the generated tokens | what it tests |\n",
    "|---|---|---|\n",
    "| `a` | full ban prompt | clean endpoint |\n",
    "| `b` | token-length-matched neutral twin (*\"Do not use fire for this task. . .\"*) | corrupted endpoint |\n",
    "| `c` | twin condition segment + ban task-spec states | **prompt route**: do the later prompt states alone carry the ban? |\n",
    "| `d` | ban condition segment + twin task-spec states | **direct route**: is generated tokens reading the ban itself enough? |\n",
    "| `K0` | full ban, but the condition span is invisible to every generated token | removal of the direct route |\n",
    "\n",
    "Each generated program is labelled with its mechanism: runtime trace first, AST second, and a blind LLM judge on disagreement. For a task with default mechanism D, `s_X` is the share of arm X's attempts labelled D. The route fractions are\n",
    "\n",
    "$$F_\\text{prompt}=\\frac{s_b-s_c}{s_b-s_a},\\quad F_\\text{direct}=\\frac{s_b-s_d}{s_b-s_a},\\quad I=1-F_\\text{prompt}-F_\\text{direct},\\quad F_\\text{K0}=\\frac{s_b-s_{K0}}{s_b-s_a}.$$\n",
    "\n",
    "**Full-run result (13,030 samples).**\n",
    "- **Gate:** only 5 of the 12 tasks pass the gate, i.e. the ban moves the model.\n",
    "- **C2a disconfirmed:** the claim \"the prompt route carries >= 2/3 of the ban\" fails. Pooled F_prompt = 0.61 and F_direct = 0.74.\n",
    "- **Task-dependent mechanism:**\n",
    "  - T03/T10: either route alone suffices.\n",
    "  - T05/T06: the ban works through the direct route.\n",
    "  - T13: both routes are needed.\n",
    "\n",
    "### What this notebook runs (CPU, a few minutes)\n",
    "1. **The S9 analysis code** (`src/analysis/analysis.py`) on a curated subset: 100 CRN slots of the `route_arms` dataset, i.e. 500 labelled programs by Qwen3-8B. It covers the gate, shares and route fractions, with a hierarchical bootstrap, BCa and leave-one-task-out jackknife intervals. It also runs leave-one-template-out, a Bayesian mixed GLM, the C2a verdict, CRN flip tables and first divergence, landings and C2c.\n",
    "2. **The original HF engine** (`src/engine.py`) on one CRN slot set, with a small Qwen3 model on CPU. This is the same prefill / KV-splice / span-drop / CRN-sampling code that ran Qwen3-8B on an L4 GPU. It uses the frozen prompt ids and the exact uniforms of the real run, and shows the Qwen3-8B rows of those slots beside its own output.\n",
    "\n",
    "Some stages are not re-run: the Qwen3-8B GPU queue (about 1.8 GPU-hours), the frozen labellers (bench harness + LLM judge) and the stages that need the upstream bench folders. Their outputs come in as the labelled `route_arms` data.\n",
    "\n",
    "### `method.py` stages and where they appear here\n",
    "| `uv run method.py <stage>` | what it does | in this notebook |\n",
    "|---|---|---|\n",
    "| `s0`, `recheck`, `s1`, `s2`, `tests` | input snapshot + bench sha256, labeller re-check, prompts with alignment asserts, frozen forecasts (n-grams, veto classes), CPU tests | not run; their frozen outputs (prompt ids, n-grams, veto classes, catalogues) ship in the data |\n",
    "| `gpu` + `label` | GPU queue: CRN-coupled sampling of every arm with Qwen3-8B, plus the streaming labeller | section 5 runs the engine on one slot set with a small model; the labels ship in the data |\n",
    "| `close1` | hash-chain commit of the analysis code before any ban sample | not applicable |\n",
    "| `analysis` | S9 analysis | sections 2-4, on the subset |\n",
    "| `figures`, `outputs`, `audit` | figures, `method_out.json`, independent re-derivation | section 6 (visualisation, demo vs. full run) |"
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

### [88] TOOL RESULT — Write · 2026-10-26 10:32:15 UTC

```
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb", "content": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"title\",\n   \"metadata\": {},\n   \"source\": [\n    \"# Where a coding ban takes effect in Qwen3-8B: route-test demo\\n\",\n    \"\\n\",\n    \"**Artifact:** experiment-16 (`art__5akZ9W9iZM4`) of *Prompt bans substitute, not just subtract*.\\n\",\n    \"\\n\",\n    \"A prompt ban such as *\\\"Do not use a hash set of seen values for this task.\\\"* makes Qwen3-8B (bf16, thinking off) write a different algorithm. This experiment asks **which internal route carries that effect**, on the 12 frozen coding tasks of the bench. Every arm of a CRN slot `(task, template, k)` is sampled with the same **common random numbers** (CRN): one fixed stream of uniforms, turned into tokens by inverse-CDF sampling. The arms are built by **splicing KV caches** by position, so they differ only in the cache their generated tokens read:\\n\",\n    \"\\n\",\n    \"| arm | cache read by the generated tokens | what it tests |\\n\",\n    \"|---|---|---|\\n\",\n    \"| `a` | full ban prompt | clean endpoint |\\n\",\n    \"| `b` | token-length-matched neutral twin (*\\\"Do not use fire for this task. . .\\\"*) | corrupted endpoint |\\n\",\n    \"| `c` | twin condition segment + ban task-spec states | **prompt route**: do the later prompt states alone carry the ban? |\\n\",\n    \"| `d` | ban condition segment + twin task-spec states | **direct route**: is generated tokens reading the ban itself enough? |\\n\",\n    \"| `K0` | full ban, but the condition span is invisible to every generated token | removal of the direct route |\\n\",\n    \"\\n\",\n    \"Each generated program is labelled with its mechanism: runtime trace first, AST second, and a blind LLM judge on disagreement. For a task with default mechanism D, `s_X` is the share of arm X's attempts labelled D. The route fractions are\\n\",\n    \"\\n\",\n    \"$$F_\\\\text{prompt}=\\\\frac{s_b-s_c}{s_b-s_a},\\\\quad F_\\\\text{direct}=\\\\frac{s_b-s_d}{s_b-s_a},\\\\quad I=1-F_\\\\text{prompt}-F_\\\\text{direct},\\\\quad F_\\\\text{K0}=\\\\frac{s_b-s_{K0}}{s_b-s_a}.$$\\n\",\n    \"\\n\",\n    \"**Full-run result (13,030 samples).**\\n\",\n    \"- **Gate:** only 5 of the 12 tasks pass the gate, i.e. the ban moves the model.\\n\",\n    \"- **C2a disconfirmed:** the claim \\\"the prompt route carries >= 2/3 of the ban\\\" fails. Pooled F_prompt = 0.61 and F_direct = 0.74.\\n\",\n    \"- **Task-dependent mechanism:**\\n\",\n    \"  - T03/T10: either route alone suffices.\\n\",\n    \"  - T05/T06: the ban works through the direct route.\\n\",\n    \"  - T13: both routes are needed.\\n\",\n    \"\\n\",\n    \"### What this notebook runs (CPU, a few minutes)\\n\",\n    \"1. **The S9 analysis code** (`src/analysis/analysis.py`) on a curated subset: 100 CRN slots of the `route_arms` dataset, i.e. 500 labelled programs by Qwen3-8B. It covers the gate, shares and route fractions, with a hierarchical bootstrap, BCa and leave-one-task-out jackknife intervals. It also runs leave-one-template-out, a Bayesian mixed GLM, the C2a verdict, CRN flip tables and first divergence, landings and C2c.\\n\",\n    \"2. **The original HF engine** (`src/engine.py`) on one CRN slot set, with a small Qwen3 model on CPU. This is the same prefill / KV-splice / span-drop / CRN-sampling code that ran Qwen3-8B on an L4 GPU. It uses the frozen prompt ids and the exact uniforms of the real run, and shows the Qwen3-8B rows of those slots beside its own output.\\n\",\n    \"\\n\",\n    \"Some stages are not re-run: the Qwen3-8B GPU queue (about 1.8 GPU-hours), the frozen labellers (bench harness + LLM judge) and the stages that need the upstream bench folders. Their outputs come in as the labelled `route_arms` data.\\n\",\n    \"\\n\",\n    \"### `method.py` stages and where they appear here\\n\",\n    \"| `uv run method.py <stage>` | what it does | in this notebook |\\n\",\n    \"|---|---|---|\\n\",\n    \"| `s0`, `recheck`, `s1`, `s2`, `tests` | input snapshot + bench sha256, labeller re-check, prompts with alignment asserts, frozen forecasts (n-grams, veto classes), CPU tests | not run; their frozen outputs (prompt ids, n-grams, veto classes, catalogues) ship in the data |\\n\",\n    \"| `gpu` + `label` | GPU queue: CRN-coupled sampling of every arm with Qwen3-8B, plus the streaming labeller | section 5 runs the engine on one slot set with a small model; the labels ship in the data |\\n\",\n    \"| `close1` | hash-chain commit of the analysis code before any ban sample | not applicable |\\n\",\n    \"| `analysis` | S9 analysis | sections 2-4, on the subset |\\n\",\n    \"| `figures`, `outputs`, `audit` | figures, `method_out.json`, independent re-derivation | section 6 (visualisation, demo vs. full run) |\"\n   ]\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}\n", "structuredPatch": [], "originalFile": null, "userModified": false}
```

### [89] TOOL CALL — Read · 2026-10-26 10:32:19 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb
```

### [90] TOOL RESULT — Read · 2026-10-26 10:32:19 UTC

```
{"type": "notebook", "file": {"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb", "cells": [{"cellType": "markdown", "source": "# Where a coding ban takes effect in Qwen3-8B: route-test demo\n\n**Artifact:** experiment-16 (`art__5akZ9W9iZM4`) of *Prompt bans substitute, not just subtract*.\n\nA prompt ban such as *\"Do not use a hash set of seen values for this task.\"* makes Qwen3-8B (bf16, thinking off) write a different algorithm. This experiment asks **which internal route carries that effect**, on the 12 frozen coding tasks of the bench. Every arm of a CRN slot `(task, template, k)` is sampled with the same **common random numbers** (CRN): one fixed stream of uniforms, turned into tokens by inverse-CDF sampling. The arms are built by **splicing KV caches** by position, so they differ only in the cache their generated tokens read:\n\n| arm | cache read by the generated tokens | what it tests |\n|---|---|---|\n| `a` | full ban prompt | clean endpoint |\n| `b` | token-length-matched neutral twin (*\"Do not use fire for this task. . .\"*) | corrupted endpoint |\n| `c` | twin condition segment + ban task-spec states | **prompt route**: do the later prompt states alone carry the ban? |\n| `d` | ban condition segment + twin task-spec states | **direct route**: is generated tokens reading the ban itself enough? |\n| `K0` | full ban, but the condition span is invisible to every generated token | removal of the direct route |\n\nEach generated program is labelled with its mechanism: runtime trace first, AST second, and a blind LLM judge on disagreement. For a task with default mechanism D, `s_X` is the share of arm X's attempts labelled D. The route fractions are\n\n$$F_\\text{prompt}=\\frac{s_b-s_c}{s_b-s_a},\\quad F_\\text{direct}=\\frac{s_b-s_d}{s_b-s_a},\\quad I=1-F_\\text{prompt}-F_\\text{direct},\\quad F_\\text{K0}=\\frac{s_b-s_{K0}}{s_b-s_a}.$$\n\n**Full-run result (13,030 samples).**\n- **Gate:** only 5 of the 12 tasks pass the gate, i.e. the ban moves the model.\n- **C2a disconfirmed:** the claim \"the prompt route carries >= 2/3 of the ban\" fails. Pooled F_prompt = 0.61 and F_direct = 0.74.\n- **Task-dependent mechanism:**\n  - T03/T10: either route alone suffices.\n  - T05/T06: the ban works through the direct route.\n  - T13: both routes are needed.\n\n### What this notebook runs (CPU, a few minutes)\n1. **The S9 analysis code** (`src/analysis/analysis.py`) on a curated subset: 100 CRN slots of the `route_arms` dataset, i.e. 500 labelled programs by Qwen3-8B. It covers the gate, shares and route fractions, with a hierarchical bootstrap, BCa and leave-one-task-out jackknife intervals. It also runs leave-one-template-out, a Bayesian mixed GLM, the C2a verdict, CRN flip tables and first divergence, landings and C2c.\n2. **The original HF engine** (`src/engine.py`) on one CRN slot set, with a small Qwen3 model on CPU. This is the same prefill / KV-splice / span-drop / CRN-sampling code that ran Qwen3-8B on an L4 GPU. It uses the frozen prompt ids and the exact uniforms of the real run, and shows the Qwen3-8B rows of those slots beside its own output.\n\nSome stages are not re-run: the Qwen3-8B GPU queue (about 1.8 GPU-hours), the frozen labellers (bench harness + LLM judge) and the stages that need the upstream bench folders. Their outputs come in as the labelled `route_arms` data.\n\n### `method.py` stages and where they appear here\n| `uv run method.py <stage>` | what it does | in this notebook |\n|---|---|---|\n| `s0`, `recheck`, `s1`, `s2`, `tests` | input snapshot + bench sha256, labeller re-check, prompts with alignment asserts, frozen forecasts (n-grams, veto classes), CPU tests | not run; their frozen outputs (prompt ids, n-grams, veto classes, catalogues) ship in the data |\n| `gpu` + `label` | GPU queue: CRN-coupled sampling of every arm with Qwen3-8B, plus the streaming labeller | section 5 runs the engine on one slot set with a small model; the labels ship in the data |\n| `close1` | hash-chain commit of the analysis code before any ban sample | not applicable |\n| `analysis` | S9 analysis | sections 2-4, on the subset |\n| `figures`, `outputs`, `audit` | figures, `method_out.json`, independent re-derivation | section 6 (visualisation, demo vs. full run) |", "cell_id": "title"}]}}
```

### [91] ASSISTANT · 2026-10-26 10:32:27 UTC

```
Now the install cell (aii-colab pattern), inserted after the title.
```

### [92] TOOL CALL — NotebookEdit · 2026-10-26 10:32:27 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': 'title', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': "import subprocess, sys\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\n\n# loguru -- NOT pre-installed on Colab, always install\n_pip('loguru==0.7.3')\n\n# numpy, pandas, scipy, statsmodels, matplotlib, torch, transformers -- pre-installed on Colab, install locally only\n# (torch: Colab's CPU build, from the PyTorch CPU index, so a local run does not pull the CUDA wheels)\nif 'google.colab' not in sys.modules:\n    _pip('--index-url', 'https://download.pytorch.org/whl/cpu', 'torch==2.9.0+cpu')\n    _pip('numpy==2.0.2', 'pandas==2.2.2', 'scipy==1.16.3', 'statsmodels==0.14.6', 'matplotlib==3.10.0',\n         'transformers==5.0.0', 'tokenizers==0.22.2', 'huggingface_hub==1.4.0')"}
```

### [93] TOOL RESULT — NotebookEdit · 2026-10-26 10:32:27 UTC

```
{"new_source": "import subprocess, sys\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\n\n# loguru -- NOT pre-installed on Colab, always install\n_pip('loguru==0.7.3')\n\n# numpy, pandas, scipy, statsmodels, matplotlib, torch, transformers -- pre-installed on Colab, install locally only\n# (torch: Colab's CPU build, from the PyTorch CPU index, so a local run does not pull the CUDA wheels)\nif 'google.colab' not in sys.modules:\n    _pip('--index-url', 'https://download.pytorch.org/whl/cpu', 'torch==2.9.0+cpu')\n    _pip('numpy==2.0.2', 'pandas==2.2.2', 'scipy==1.16.3', 'statsmodels==0.14.6', 'matplotlib==3.10.0',\n         'transformers==5.0.0', 'tokenizers==0.22.2', 'huggingface_hub==1.4.0')", "cell_type": "code", "language": "python", "edit_mode": "insert", "cell_id": "fc03631f", "error": "", "notebook_path": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb", "original_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"title\",\n   \"metadata\": {},\n   \"source\": [\n    \"# Where a coding ban takes effect in Qwen3-8B: route-test demo\\n\",\n    \"\\n\",\n    \"**Artifact:** experiment-16 (`art__5akZ9W9iZM4`) of *Prompt bans substitute, not just subtract*.\\n\",\n    \"\\n\",\n    \"A prompt ban such as *\\\"Do not use a hash set of seen values for this task.\\\"* makes Qwen3-8B (bf16, thinking off) write a different algorithm. This experiment asks **which internal route carries that effect**, on the 12 frozen coding tasks of the bench. Every arm of a CRN slot `(task, template, k)` is sampled with the same **common random numbers** (CRN): one fixed stream of uniforms, turned into tokens by inverse-CDF sampling. The arms are built by **splicing KV caches** by position, so they differ only in the cache their generated tokens read:\\n\",\n    \"\\n\",\n    \"| arm | cache read by the generated tokens | what it tests |\\n\",\n    \"|---|---|---|\\n\",\n    \"| `a` | full ban prompt | clean endpoint |\\n\",\n    \"| `b` | token-length-matched neutral twin (*\\\"Do not use fire for this task. . .\\\"*) | corrupted endpoint |\\n\",\n    \"| `c` | twin condition segment + ban task-spec states | **prompt route**: do the later prompt states alone carry the ban? |\\n\",\n    \"| `d` | ban condition segment + twin task-spec states | **direct route**: is generated tokens reading the ban itself enough? |\\n\",\n    \"| `K0` | full ban, but the condition span is invisible to every generated token | removal of the direct route |\\n\",\n    \"\\n\",\n    \"Each generated program is labelled with its mechanism: runtime trace first, AST second, and a blind LLM judge on disagreement. For a task with default mechanism D, `s_X` is the share of arm X's attempts labelled D. The route fractions are\\n\",\n    \"\\n\",\n    \"$$F_\\\\text{prompt}=\\\\frac{s_b-s_c}{s_b-s_a},\\\\quad F_\\\\text{direct}=\\\\frac{s_b-s_d}{s_b-s_a},\\\\quad I=1-F_\\\\text{prompt}-F_\\\\text{direct},\\\\quad F_\\\\text{K0}=\\\\frac{s_b-s_{K0}}{s_b-s_a}.$$\\n\",\n    \"\\n\",\n    \"**Full-run result (13,030 samples).**\\n\",\n    \"- **Gate:** only 5 of the 12 tasks pass the gate, i.e. the ban moves the model.\\n\",\n    \"- **C2a disconfirmed:** the claim \\\"the prompt route carries >= 2/3 of the ban\\\" fails. Pooled F_prompt = 0.61 and F_direct = 0.74.\\n\",\n    \"- **Task-dependent mechanism:**\\n\",\n    \"  - T03/T10: either route alone suffices.\\n\",\n    \"  - T05/T06: the ban works through the direct route.\\n\",\n    \"  - T13: both routes are needed.\\n\",\n    \"\\n\",\n    \"### What this notebook runs (CPU, a few minutes)\\n\",\n    \"1. **The S9 analysis code** (`src/analysis/analysis.py`) on a curated subset: 100 CRN slots of the `route_arms` dataset, i.e. 500 labelled programs by Qwen3-8B. It covers the gate, shares and route fractions, with a hierarchical bootstrap, BCa and leave-one-task-out jackknife intervals. It also runs leave-one-template-out, a Bayesian mixed GLM, the C2a verdict, CRN flip tables and first divergence, landings and C2c.\\n\",\n    \"2. **The original HF engine** (`src/engine.py`) on one CRN slot set, with a small Qwen3 model on CPU. This is the same prefill / KV-splice / span-drop / CRN-sampling code that ran Qwen3-8B on an L4 GPU. It uses the frozen prompt ids and the exact uniforms of the real run, and shows the Qwen3-8B rows of those slots beside its own output.\\n\",\n    \"\\n\",\n    \"Some stages are not re-run: the Qwen3-8B GPU queue (about 1.8 GPU-hours), the frozen labellers (bench harness + LLM judge) and the stages that need the upstream bench folders. Their outputs come in as the labelled `route_arms` data.\\n\",\n    \"\\n\",\n    \"### `method.py` stages and where they appear here\\n\",\n    \"| `uv run method.py <stage>` | what it does | in this notebook |\\n\",\n    \"|---|---|---|\\n\",\n    \"| `s0`, `recheck`, `s1`, `s2`, `tests` | input snapshot + bench sha256, labeller re-check, prompts with alignment asserts, frozen forecasts (n-grams, veto classes), CPU tests | not run; their frozen outputs (prompt ids, n-grams, veto classes, catalogues) ship in the data |\\n\",\n    \"| `gpu` + `label` | GPU queue: CRN-coupled sampling of every arm with Qwen3-8B, plus the streaming labeller | section 5 runs the engine on one slot set with a small model; the labels ship in the data |\\n\",\n    \"| `close1` | hash-chain commit of the analysis code before any ban sample | not applicable |\\n\",\n    \"| `analysis` | S9 analysis | sections 2-4, on the subset |\\n\",\n    \"| `figures`, `outputs`, `audit` | figures, `method_out.json`, independent re-derivation | section 6 (visualisation, demo vs. full run) |\"\n   ]\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}\n", "updated_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"title\",\n   \"metadata\": {},\n   \"source\": [\n    \"# Where a coding ban takes effect in Qwen3-8B: route-test demo\\n\",\n    \"\\n\",\n    \"**Artifact:** experiment-16 (`art__5akZ9W9iZM4`) of *Prompt bans substitute, not just subtract*.\\n\",\n    \"\\n\",\n    \"A prompt ban such as *\\\"Do not use a hash set of seen values for this task.\\\"* makes Qwen3-8B (bf16, thinking off) write a different algorithm. This experiment asks **which internal route carries that effect**, on the 12 frozen coding tasks of the bench. Every arm of a CRN slot `(task, template, k)` is sampled with the same **common random numbers** (CRN): one fixed stream of uniforms, turned into tokens by inverse-CDF sampling. The arms are built by **splicing KV caches** by position, so they differ only in the cache their generated tokens read:\\n\",\n    \"\\n\",\n    \"| arm | cache read by the generated tokens | what it tests |\\n\",\n    \"|---|---|---|\\n\",\n    \"| `a` | full ban prompt | clean endpoint |\\n\",\n    \"| `b` | token-length-matched neutral twin (*\\\"Do not use fire for this task. . .\\\"*) | corrupted endpoint |\\n\",\n    \"| `c` | twin condition segment + ban task-spec states | **prompt route**: do the later prompt states alone carry the ban? |\\n\",\n    \"| `d` | ban condition segment + twin task-spec states | **direct route**: is generated tokens reading the ban itself enough? |\\n\",\n    \"| `K0` | full ban, but the condition span is invisible to every generated token | removal of the direct route |\\n\",\n    \"\\n\",\n    \"Each generated program is labelled with its mechanism: runtime trace first, AST second, and a blind LLM judge on disagreement. For a task with default mechanism D, `s_X` is the share of arm X's attempts labelled D. The route fractions are\\n\",\n    \"\\n\",\n    \"$$F_\\\\text{prompt}=\\\\frac{s_b-s_c}{s_b-s_a},\\\\quad F_\\\\text{direct}=\\\\frac{s_b-s_d}{s_b-s_a},\\\\quad I=1-F_\\\\text{prompt}-F_\\\\text{direct},\\\\quad F_\\\\text{K0}=\\\\frac{s_b-s_{K0}}{s_b-s_a}.$$\\n\",\n    \"\\n\",\n    \"**Full-run result (13,030 samples).**\\n\",\n    \"- **Gate:** only 5 of the 12 tasks pass the gate, i.e. the ban moves the model.\\n\",\n    \"- **C2a disconfirmed:** the claim \\\"the prompt route carries >= 2/3 of the ban\\\" fails. Pooled F_prompt = 0.61 and F_direct = 0.74.\\n\",\n    \"- **Task-dependent mechanism:**\\n\",\n    \"  - T03/T10: either route alone suffices.\\n\",\n    \"  - T05/T06: the ban works through the direct route.\\n\",\n    \"  - T13: both routes are needed.\\n\",\n    \"\\n\",\n    \"### What this notebook runs (CPU, a few minutes)\\n\",\n    \"1. **The S9 analysis code** (`src/analysis/analysis.py`) on a curated subset: 100 CRN slots of the `route_arms` dataset, i.e. 500 labelled programs by Qwen3-8B. It covers the gate, shares and route fractions, with a hierarchical bootstrap, BCa and leave-one-task-out jackknife intervals. It also runs leave-one-template-out, a Bayesian mixed GLM, the C2a verdict, CRN flip tables and first divergence, landings and C2c.\\n\",\n    \"2. **The original HF engine** (`src/engine.py`) on one CRN slot set, with a small Qwen3 model on CPU. This is the same prefill / KV-splice / span-drop / CRN-sampling code that ran Qwen3-8B on an L4 GPU. It uses the frozen prompt ids and the exact uniforms of the real run, and shows the Qwen3-8B rows of those slots beside its own output.\\n\",\n    \"\\n\",\n    \"Some stages are not re-run: the Qwen3-8B GPU queue (about 1.8 GPU-hours), the frozen labellers (bench harness + LLM judge) and the stages that need the upstream bench folders. Their outputs come in as the labelled `route_arms` data.\\n\",\n    \"\\n\",\n    \"### `method.py` stages and where they appear here\\n\",\n    \"| `uv run method.py <stage>` | what it does | in this notebook |\\n\",\n    \"|---|---|---|\\n\",\n    \"| `s0`, `recheck`, `s1`, `s2`, `tests` | input snapshot + bench sha256, labeller re-check, prompts with alignment asserts, frozen forecasts (n-grams, veto classes), CPU tests | not run; their frozen outputs (prompt ids, n-grams, veto classes, catalogues) ship in the data |\\n\",\n    \"| `gpu` + `label` | GPU queue: CRN-coupled sampling of every arm with Qwen3-8B, plus the streaming labeller | section 5 runs the engine on one slot set with a small model; the labels ship in the data |\\n\",\n    \"| `close1` | hash-chain commit of the analysis code before any ban sample | not applicable |\\n\",\n    \"| `analysis` | S9 analysis | sections 2-4, on the subset |\\n\",\n    \"| `figures`, `outputs`, `audit` | figures, `method_out.json`, independent re-derivation | section 6 (visualisation, demo vs. full run) |\"\n   ]\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"fc03631f\",\n   \"source\": \"import subprocess, sys\\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\\n\\n# loguru -- NOT pre-installed on Colab, always install\\n_pip('loguru==0.7.3')\\n\\n# numpy, pandas, scipy, statsmodels, matplotlib, torch, transformers -- pre-installed on Colab, install locally only\\n# (torch: Colab's CPU build, from the PyTorch CPU index, so a local run does not pull the CUDA wheels)\\nif 'google.colab' not in sys.modules:\\n    _pip('--index-url', 'https://download.pytorch.org/whl/cpu', 'torch==2.9.0+cpu')\\n    _pip('numpy==2.0.2', 'pandas==2.2.2', 'scipy==1.16.3', 'statsmodels==0.14.6', 'matplotlib==3.10.0',\\n         'transformers==5.0.0', 'tokenizers==0.22.2', 'huggingface_hub==1.4.0')\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}"}
```

### [94] ASSISTANT · 2026-10-26 10:32:33 UTC

```
NotebookEdit returns each new cell id, so I can chain inserts in order. Next, the imports cell.
```

### [95] TOOL CALL — NotebookEdit · 2026-10-26 10:32:33 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': 'fc03631f', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '# original imports of the code used below (src/cfg.py, src/engine.py, src/gpu.py, src/analysis/analysis.py)\nimport collections\nimport contextlib\nimport gc\nimport hashlib\nimport json\nimport math\nimport os\nimport re\nimport sys\nimport time\nfrom pathlib import Path\nfrom typing import Any, Callable, Iterable, Iterator\n\nimport numpy as np\nimport torch\nfrom loguru import logger\nfrom scipy import stats\n\n# notebook additions: tables and figures\nimport matplotlib.pyplot as plt\nimport pandas as pd\n\npd.set_option("display.width", 200)\npd.set_option("display.max_columns", 30)\nprint("torch", torch.__version__, "| numpy", np.__version__, "| cuda available:", torch.cuda.is_available())'}
```

### [96] TOOL RESULT — NotebookEdit · 2026-10-26 10:32:33 UTC

```
{"new_source": "# original imports of the code used below (src/cfg.py, src/engine.py, src/gpu.py, src/analysis/analysis.py)\nimport collections\nimport contextlib\nimport gc\nimport hashlib\nimport json\nimport math\nimport os\nimport re\nimport sys\nimport time\nfrom pathlib import Path\nfrom typing import Any, Callable, Iterable, Iterator\n\nimport numpy as np\nimport torch\nfrom loguru import logger\nfrom scipy import stats\n\n# notebook additions: tables and figures\nimport matplotlib.pyplot as plt\nimport pandas as pd\n\npd.set_option(\"display.width\", 200)\npd.set_option(\"display.max_columns\", 30)\nprint(\"torch\", torch.__version__, \"| numpy\", np.__version__, \"| cuda available:\", torch.cuda.is_available())", "cell_type": "code", "language": "python", "edit_mode": "insert", "cell_id": "bc3a2b51", "error": "", "notebook_path": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb", "original_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"title\",\n   \"metadata\": {},\n   \"source\": [\n    \"# Where a coding ban takes effect in Qwen3-8B: route-test demo\\n\",\n    \"\\n\",\n    \"**Artifact:** experiment-16 (`art__5akZ9W9iZM4`) of *Prompt bans substitute, not just subtract*.\\n\",\n    \"\\n\",\n    \"A prompt ban such as *\\\"Do not use a hash set of seen values for this task.\\\"* makes Qwen3-8B (bf16, thinking off) write a different algorithm. This experiment asks **which internal route carries that effect**, on the 12 frozen coding tasks of the bench. Every arm of a CRN slot `(task, template, k)` is sampled with the same **common random numbers** (CRN): one fixed stream of uniforms, turned into tokens by inverse-CDF sampling. The arms are built by **splicing KV caches** by position, so they differ only in the cache their generated tokens read:\\n\",\n    \"\\n\",\n    \"| arm | cache read by the generated tokens | what it tests |\\n\",\n    \"|---|---|---|\\n\",\n    \"| `a` | full ban prompt | clean endpoint |\\n\",\n    \"| `b` | token-length-matched neutral twin (*\\\"Do not use fire for this task. . .\\\"*) | corrupted endpoint |\\n\",\n    \"| `c` | twin condition segment + ban task-spec states | **prompt route**: do the later prompt states alone carry the ban? |\\n\",\n    \"| `d` | ban condition segment + twin task-spec states | **direct route**: is generated tokens reading the ban itself enough? |\\n\",\n    \"| `K0` | full ban, but the condition span is invisible to every generated token | removal of the direct route |\\n\",\n    \"\\n\",\n    \"Each generated program is labelled with its mechanism: runtime trace first, AST second, and a blind LLM judge on disagreement. For a task with default mechanism D, `s_X` is the share of arm X's attempts labelled D. The route fractions are\\n\",\n    \"\\n\",\n    \"$$F_\\\\text{prompt}=\\\\frac{s_b-s_c}{s_b-s_a},\\\\quad F_\\\\text{direct}=\\\\frac{s_b-s_d}{s_b-s_a},\\\\quad I=1-F_\\\\text{prompt}-F_\\\\text{direct},\\\\quad F_\\\\text{K0}=\\\\frac{s_b-s_{K0}}{s_b-s_a}.$$\\n\",\n    \"\\n\",\n    \"**Full-run result (13,030 samples).**\\n\",\n    \"- **Gate:** only 5 of the 12 tasks pass the gate, i.e. the ban moves the model.\\n\",\n    \"- **C2a disconfirmed:** the claim \\\"the prompt route carries >= 2/3 of the ban\\\" fails. Pooled F_prompt = 0.61 and F_direct = 0.74.\\n\",\n    \"- **Task-dependent mechanism:**\\n\",\n    \"  - T03/T10: either route alone suffices.\\n\",\n    \"  - T05/T06: the ban works through the direct route.\\n\",\n    \"  - T13: both routes are needed.\\n\",\n    \"\\n\",\n    \"### What this notebook runs (CPU, a few minutes)\\n\",\n    \"1. **The S9 analysis code** (`src/analysis/analysis.py`) on a curated subset: 100 CRN slots of the `route_arms` dataset, i.e. 500 labelled programs by Qwen3-8B. It covers the gate, shares and route fractions, with a hierarchical bootstrap, BCa and leave-one-task-out jackknife intervals. It also runs leave-one-template-out, a Bayesian mixed GLM, the C2a verdict, CRN flip tables and first divergence, landings and C2c.\\n\",\n    \"2. **The original HF engine** (`src/engine.py`) on one CRN slot set, with a small Qwen3 model on CPU. This is the same prefill / KV-splice / span-drop / CRN-sampling code that ran Qwen3-8B on an L4 GPU. It uses the frozen prompt ids and the exact uniforms of the real run, and shows the Qwen3-8B rows of those slots beside its own output.\\n\",\n    \"\\n\",\n    \"Some stages are not re-run: the Qwen3-8B GPU queue (about 1.8 GPU-hours), the frozen labellers (bench harness + LLM judge) and the stages that need the upstream bench folders. Their outputs come in as the labelled `route_arms` data.\\n\",\n    \"\\n\",\n    \"### `method.py` stages and where they appear here\\n\",\n    \"| `uv run method.py <stage>` | what it does | in this notebook |\\n\",\n    \"|---|---|---|\\n\",\n    \"| `s0`, `recheck`, `s1`, `s2`, `tests` | input snapshot + bench sha256, labeller re-check, prompts with alignment asserts, frozen forecasts (n-grams, veto classes), CPU tests | not run; their frozen outputs (prompt ids, n-grams, veto classes, catalogues) ship in the data |\\n\",\n    \"| `gpu` + `label` | GPU queue: CRN-coupled sampling of every arm with Qwen3-8B, plus the streaming labeller | section 5 runs the engine on one slot set with a small model; the labels ship in the data |\\n\",\n    \"| `close1` | hash-chain commit of the analysis code before any ban sample | not applicable |\\n\",\n    \"| `analysis` | S9 analysis | sections 2-4, on the subset |\\n\",\n    \"| `figures`, `outputs`, `audit` | figures, `method_out.json`, independent re-derivation | section 6 (visualisation, demo vs. full run) |\"\n   ]\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"fc03631f\",\n   \"source\": \"import subprocess, sys\\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\\n\\n# loguru -- NOT pre-installed on Colab, always install\\n_pip('loguru==0.7.3')\\n\\n# numpy, pandas, scipy, statsmodels, matplotlib, torch, transformers -- pre-installed on Colab, install locally only\\n# (torch: Colab's CPU build, from the PyTorch CPU index, so a local run does not pull the CUDA wheels)\\nif 'google.colab' not in sys.modules:\\n    _pip('--index-url', 'https://download.pytorch.org/whl/cpu', 'torch==2.9.0+cpu')\\n    _pip('numpy==2.0.2', 'pandas==2.2.2', 'scipy==1.16.3', 'statsmodels==0.14.6', 'matplotlib==3.10.0',\\n         'transformers==5.0.0', 'tokenizers==0.22.2', 'huggingface_hub==1.4.0')\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}", "updated_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"title\",\n   \"metadata\": {},\n   \"source\": [\n    \"# Where a coding ban takes effect in Qwen3-8B: route-test demo\\n\",\n    \"\\n\",\n    \"**Artifact:** experiment-16 (`art__5akZ9W9iZM4`) of *Prompt bans substitute, not just subtract*.\\n\",\n    \"\\n\",\n    \"A prompt ban such as *\\\"Do not use a hash set of seen values for this task.\\\"* makes Qwen3-8B (bf16, thinking off) write a different algorithm. This experiment asks **which internal route carries that effect**, on the 12 frozen coding tasks of the bench. Every arm of a CRN slot `(task, template, k)` is sampled with the same **common random numbers** (CRN): one fixed stream of uniforms, turned into tokens by inverse-CDF sampling. The arms are built by **splicing KV caches** by position, so they differ only in the cache their generated tokens read:\\n\",\n    \"\\n\",\n    \"| arm | cache read by the generated tokens | what it tests |\\n\",\n    \"|---|---|---|\\n\",\n    \"| `a` | full ban prompt | clean endpoint |\\n\",\n    \"| `b` | token-length-matched neutral twin (*\\\"Do not use fire for this task. . .\\\"*) | corrupted endpoint |\\n\",\n    \"| `c` | twin condition segment + ban task-spec states | **prompt route**: do the later prompt states alone carry the ban? |\\n\",\n    \"| `d` | ban condition segment + twin task-spec states | **direct route**: is generated tokens reading the ban itself enough? |\\n\",\n    \"| `K0` | full ban, but the condition span is invisible to every generated token | removal of the direct route |\\n\",\n    \"\\n\",\n    \"Each generated program is labelled with its mechanism: runtime trace first, AST second, and a blind LLM judge on disagreement. For a task with default mechanism D, `s_X` is the share of arm X's attempts labelled D. The route fractions are\\n\",\n    \"\\n\",\n    \"$$F_\\\\text{prompt}=\\\\frac{s_b-s_c}{s_b-s_a},\\\\quad F_\\\\text{direct}=\\\\frac{s_b-s_d}{s_b-s_a},\\\\quad I=1-F_\\\\text{prompt}-F_\\\\text{direct},\\\\quad F_\\\\text{K0}=\\\\frac{s_b-s_{K0}}{s_b-s_a}.$$\\n\",\n    \"\\n\",\n    \"**Full-run result (13,030 samples).**\\n\",\n    \"- **Gate:** only 5 of the 12 tasks pass the gate, i.e. the ban moves the model.\\n\",\n    \"- **C2a disconfirmed:** the claim \\\"the prompt route carries >= 2/3 of the ban\\\" fails. Pooled F_prompt = 0.61 and F_direct = 0.74.\\n\",\n    \"- **Task-dependent mechanism:**\\n\",\n    \"  - T03/T10: either route alone suffices.\\n\",\n    \"  - T05/T06: the ban works through the direct route.\\n\",\n    \"  - T13: both routes are needed.\\n\",\n    \"\\n\",\n    \"### What this notebook runs (CPU, a few minutes)\\n\",\n    \"1. **The S9 analysis code** (`src/analysis/analysis.py`) on a curated subset: 100 CRN slots of the `route_arms` dataset, i.e. 500 labelled programs by Qwen3-8B. It covers the gate, shares and route fractions, with a hierarchical bootstrap, BCa and leave-one-task-out jackknife intervals. It also runs leave-one-template-out, a Bayesian mixed GLM, the C2a verdict, CRN flip tables and first divergence, landings and C2c.\\n\",\n    \"2. **The original HF engine** (`src/engine.py`) on one CRN slot set, with a small Qwen3 model on CPU. This is the same prefill / KV-splice / span-drop / CRN-sampling code that ran Qwen3-8B on an L4 GPU. It uses the frozen prompt ids and the exact uniforms of the real run, and shows the Qwen3-8B rows of those slots beside its own output.\\n\",\n    \"\\n\",\n    \"Some stages are not re-run: the Qwen3-8B GPU queue (about 1.8 GPU-hours), the frozen labellers (bench harness + LLM judge) and the stages that need the upstream bench folders. Their outputs come in as the labelled `route_arms` data.\\n\",\n    \"\\n\",\n    \"### `method.py` stages and where they appear here\\n\",\n    \"| `uv run method.py <stage>` | what it does | in this notebook |\\n\",\n    \"|---|---|---|\\n\",\n    \"| `s0`, `recheck`, `s1`, `s2`, `tests` | input snapshot + bench sha256, labeller re-check, prompts with alignment asserts, frozen forecasts (n-grams, veto classes), CPU tests | not run; their frozen outputs (prompt ids, n-grams, veto classes, catalogues) ship in the data |\\n\",\n    \"| `gpu` + `label` | GPU queue: CRN-coupled sampling of every arm with Qwen3-8B, plus the streaming labeller | section 5 runs the engine on one slot set with a small model; the labels ship in the data |\\n\",\n    \"| `close1` | hash-chain commit of the analysis code before any ban sample | not applicable |\\n\",\n    \"| `analysis` | S9 analysis | sections 2-4, on the subset |\\n\",\n    \"| `figures`, `outputs`, `audit` | figures, `method_out.json`, independent re-derivation | section 6 (visualisation, demo vs. full run) |\"\n   ]\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"fc03631f\",\n   \"source\": \"import subprocess, sys\\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\\n\\n# loguru -- NOT pre-installed on Colab, always install\\n_pip('loguru==0.7.3')\\n\\n# numpy, pandas, scipy, statsmodels, matplotlib, torch, transformers -- pre-installed on Colab, install locally only\\n# (torch: Colab's CPU build, from the PyTorch CPU index, so a local run does not pull the CUDA wheels)\\nif 'google.colab' not in sys.modules:\\n    _pip('--index-url', 'https://download.pytorch.org/whl/cpu', 'torch==2.9.0+cpu')\\n    _pip('numpy==2.0.2', 'pandas==2.2.2', 'scipy==1.16.3', 'statsmodels==0.14.6', 'matplotlib==3.10.0',\\n         'transformers==5.0.0', 'tokenizers==0.22.2', 'huggingface_hub==1.4.0')\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"bc3a2b51\",\n   \"source\": \"# original imports of the code used below (src/cfg.py, src/engine.py, src/gpu.py, src/analysis/analysis.py)\\nimport collections\\nimport contextlib\\nimport gc\\nimport hashlib\\nimport json\\nimport math\\nimport os\\nimport re\\nimport sys\\nimport time\\nfrom pathlib import Path\\nfrom typing import Any, Callable, Iterable, Iterator\\n\\nimport numpy as np\\nimport torch\\nfrom loguru import logger\\nfrom scipy import stats\\n\\n# notebook additions: tables and figures\\nimport matplotlib.pyplot as plt\\nimport pandas as pd\\n\\npd.set_option(\\\"display.width\\\", 200)\\npd.set_option(\\\"display.max_columns\\\", 30)\\nprint(\\\"torch\\\", torch.__version__, \\\"| numpy\\\", np.__version__, \\\"| cuda available:\\\", torch.cuda.is_available())\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}"}
```

### [97] TOOL CALL — NotebookEdit · 2026-10-26 10:32:41 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': 'bc3a2b51', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-3/experiment-16/demo/mini_demo_data.json"\nimport http.client\nimport json\nimport urllib.request\nfrom pathlib import Path\n\ndef load_data():\n    try:\n        with urllib.request.urlopen(GITHUB_DATA_URL, timeout=15) as response:\n            return json.loads(response.read().decode())\n    # Network errors, timeouts, a placeholder URL, bad JSON, a cut-off response.\n    except (OSError, ValueError, http.client.HTTPException) as e:\n        print("GitHub data unavailable, using local mini_demo_data.json:", e)\n    local = Path("mini_demo_data.json")\n    if local.exists(): return json.loads(local.read_text())\n    raise FileNotFoundError("Could not load mini_demo_data.json")'}
```

### [98] TOOL RESULT — NotebookEdit · 2026-10-26 10:32:41 UTC

```
{"new_source": "GITHUB_DATA_URL = \"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-3/experiment-16/demo/mini_demo_data.json\"\nimport http.client\nimport json\nimport urllib.request\nfrom pathlib import Path\n\ndef load_data():\n    try:\n        with urllib.request.urlopen(GITHUB_DATA_URL, timeout=15) as response:\n            return json.loads(response.read().decode())\n    # Network errors, timeouts, a placeholder URL, bad JSON, a cut-off response.\n    except (OSError, ValueError, http.client.HTTPException) as e:\n        print(\"GitHub data unavailable, using local mini_demo_data.json:\", e)\n    local = Path(\"mini_demo_data.json\")\n    if local.exists(): return json.loads(local.read_text())\n    raise FileNotFoundError(\"Could not load mini_demo_data.json\")", "cell_type": "code", "language": "python", "edit_mode": "insert", "cell_id": "4c26f4ad", "error": "", "notebook_path": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb", "original_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"title\",\n   \"metadata\": {},\n   \"source\": [\n    \"# Where a coding ban takes effect in Qwen3-8B: route-test demo\\n\",\n    \"\\n\",\n    \"**Artifact:** experiment-16 (`art__5akZ9W9iZM4`) of *Prompt bans substitute, not just subtract*.\\n\",\n    \"\\n\",\n    \"A prompt ban such as *\\\"Do not use a hash set of seen values for this task.\\\"* makes Qwen3-8B (bf16, thinking off) write a different algorithm. This experiment asks **which internal route carries that effect**, on the 12 frozen coding tasks of the bench. Every arm of a CRN slot `(task, template, k)` is sampled with the same **common random numbers** (CRN): one fixed stream of uniforms, turned into tokens by inverse-CDF sampling. The arms are built by **splicing KV caches** by position, so they differ only in the cache their generated tokens read:\\n\",\n    \"\\n\",\n    \"| arm | cache read by the generated tokens | what it tests |\\n\",\n    \"|---|---|---|\\n\",\n    \"| `a` | full ban prompt | clean endpoint |\\n\",\n    \"| `b` | token-length-matched neutral twin (*\\\"Do not use fire for this task. . .\\\"*) | corrupted endpoint |\\n\",\n    \"| `c` | twin condition segment + ban task-spec states | **prompt route**: do the later prompt states alone carry the ban? |\\n\",\n    \"| `d` | ban condition segment + twin task-spec states | **direct route**: is generated tokens reading the ban itself enough? |\\n\",\n    \"| `K0` | full ban, but the condition span is invisible to every generated token | removal of the direct route |\\n\",\n    \"\\n\",\n    \"Each generated program is labelled with its mechanism: runtime trace first, AST second, and a blind LLM judge on disagreement. For a task with default mechanism D, `s_X` is the share of arm X's attempts labelled D. The route fractions are\\n\",\n    \"\\n\",\n    \"$$F_\\\\text{prompt}=\\\\frac{s_b-s_c}{s_b-s_a},\\\\quad F_\\\\text{direct}=\\\\frac{s_b-s_d}{s_b-s_a},\\\\quad I=1-F_\\\\text{prompt}-F_\\\\text{direct},\\\\quad F_\\\\text{K0}=\\\\frac{s_b-s_{K0}}{s_b-s_a}.$$\\n\",\n    \"\\n\",\n    \"**Full-run result (13,030 samples).**\\n\",\n    \"- **Gate:** only 5 of the 12 tasks pass the gate, i.e. the ban moves the model.\\n\",\n    \"- **C2a disconfirmed:** the claim \\\"the prompt route carries >= 2/3 of the ban\\\" fails. Pooled F_prompt = 0.61 and F_direct = 0.74.\\n\",\n    \"- **Task-dependent mechanism:**\\n\",\n    \"  - T03/T10: either route alone suffices.\\n\",\n    \"  - T05/T06: the ban works through the direct route.\\n\",\n    \"  - T13: both routes are needed.\\n\",\n    \"\\n\",\n    \"### What this notebook runs (CPU, a few minutes)\\n\",\n    \"1. **The S9 analysis code** (`src/analysis/analysis.py`) on a curated subset: 100 CRN slots of the `route_arms` dataset, i.e. 500 labelled programs by Qwen3-8B. It covers the gate, shares and route fractions, with a hierarchical bootstrap, BCa and leave-one-task-out jackknife intervals. It also runs leave-one-template-out, a Bayesian mixed GLM, the C2a verdict, CRN flip tables and first divergence, landings and C2c.\\n\",\n    \"2. **The original HF engine** (`src/engine.py`) on one CRN slot set, with a small Qwen3 model on CPU. This is the same prefill / KV-splice / span-drop / CRN-sampling code that ran Qwen3-8B on an L4 GPU. It uses the frozen prompt ids and the exact uniforms of the real run, and shows the Qwen3-8B rows of those slots beside its own output.\\n\",\n    \"\\n\",\n    \"Some stages are not re-run: the Qwen3-8B GPU queue (about 1.8 GPU-hours), the frozen labellers (bench harness + LLM judge) and the stages that need the upstream bench folders. Their outputs come in as the labelled `route_arms` data.\\n\",\n    \"\\n\",\n    \"### `method.py` stages and where they appear here\\n\",\n    \"| `uv run method.py <stage>` | what it does | in this notebook |\\n\",\n    \"|---|---|---|\\n\",\n    \"| `s0`, `recheck`, `s1`, `s2`, `tests` | input snapshot + bench sha256, labeller re-check, prompts with alignment asserts, frozen forecasts (n-grams, veto classes), CPU tests | not run; their frozen outputs (prompt ids, n-grams, veto classes, catalogues) ship in the data |\\n\",\n    \"| `gpu` + `label` | GPU queue: CRN-coupled sampling of every arm with Qwen3-8B, plus the streaming labeller | section 5 runs the engine on one slot set with a small model; the labels ship in the data |\\n\",\n    \"| `close1` | hash-chain commit of the analysis code before any ban sample | not applicable |\\n\",\n    \"| `analysis` | S9 analysis | sections 2-4, on the subset |\\n\",\n    \"| `figures`, `outputs`, `audit` | figures, `method_out.json`, independent re-derivation | section 6 (visualisation, demo vs. full run) |\"\n   ]\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"fc03631f\",\n   \"source\": \"import subprocess, sys\\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\\n\\n# loguru -- NOT pre-installed on Colab, always install\\n_pip('loguru==0.7.3')\\n\\n# numpy, pandas, scipy, statsmodels, matplotlib, torch, transformers -- pre-installed on Colab, install locally only\\n# (torch: Colab's CPU build, from the PyTorch CPU index, so a local run does not pull the CUDA wheels)\\nif 'google.colab' not in sys.modules:\\n    _pip('--index-url', 'https://download.pytorch.org/whl/cpu', 'torch==2.9.0+cpu')\\n    _pip('numpy==2.0.2', 'pandas==2.2.2', 'scipy==1.16.3', 'statsmodels==0.14.6', 'matplotlib==3.10.0',\\n         'transformers==5.0.0', 'tokenizers==0.22.2', 'huggingface_hub==1.4.0')\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"bc3a2b51\",\n   \"source\": \"# original imports of the code used below (src/cfg.py, src/engine.py, src/gpu.py, src/analysis/analysis.py)\\nimport collections\\nimport contextlib\\nimport gc\\nimport hashlib\\nimport json\\nimport math\\nimport os\\nimport re\\nimport sys\\nimport time\\nfrom pathlib import Path\\nfrom typing import Any, Callable, Iterable, Iterator\\n\\nimport numpy as np\\nimport torch\\nfrom loguru import logger\\nfrom scipy import stats\\n\\n# notebook additions: tables and figures\\nimport matplotlib.pyplot as plt\\nimport pandas as pd\\n\\npd.set_option(\\\"display.width\\\", 200)\\npd.set_option(\\\"display.max_columns\\\", 30)\\nprint(\\\"torch\\\", torch.__version__, \\\"| numpy\\\", np.__version__, \\\"| cuda available:\\\", torch.cuda.is_available())\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}", "updated_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"title\",\n   \"metadata\": {},\n   \"source\": [\n    \"# Where a coding ban takes effect in Qwen3-8B: route-test demo\\n\",\n    \"\\n\",\n    \"**Artifact:** experiment-16 (`art__5akZ9W9iZM4`) of *Prompt bans substitute, not just subtract*.\\n\",\n    \"\\n\",\n    \"A prompt ban such as *\\\"Do not use a hash set of seen values for this task.\\\"* makes Qwen3-8B (bf16, thinking off) write a different algorithm. This experiment asks **which internal route carries that effect**, on the 12 frozen coding tasks of the bench. Every arm of a CRN slot `(task, template, k)` is sampled with the same **common random numbers** (CRN): one fixed stream of uniforms, turned into tokens by inverse-CDF sampling. The arms are built by **splicing KV caches** by position, so they differ only in the cache their generated tokens read:\\n\",\n    \"\\n\",\n    \"| arm | cache read by the generated tokens | what it tests |\\n\",\n    \"|---|---|---|\\n\",\n    \"| `a` | full ban prompt | clean endpoint |\\n\",\n    \"| `b` | token-length-matched neutral twin (*\\\"Do not use fire for this task. . .\\\"*) | corrupted endpoint |\\n\",\n    \"| `c` | twin condition segment + ban task-spec states | **prompt route**: do the later prompt states alone carry the ban? |\\n\",\n    \"| `d` | ban condition segment + twin task-spec states | **direct route**: is generated tokens reading the ban itself enough? |\\n\",\n    \"| `K0` | full ban, but the condition span is invisible to every generated token | removal of the direct route |\\n\",\n    \"\\n\",\n    \"Each generated program is labelled with its mechanism: runtime trace first, AST second, and a blind LLM judge on disagreement. For a task with default mechanism D, `s_X` is the share of arm X's attempts labelled D. The route fractions are\\n\",\n    \"\\n\",\n    \"$$F_\\\\text{prompt}=\\\\frac{s_b-s_c}{s_b-s_a},\\\\quad F_\\\\text{direct}=\\\\frac{s_b-s_d}{s_b-s_a},\\\\quad I=1-F_\\\\text{prompt}-F_\\\\text{direct},\\\\quad F_\\\\text{K0}=\\\\frac{s_b-s_{K0}}{s_b-s_a}.$$\\n\",\n    \"\\n\",\n    \"**Full-run result (13,030 samples).**\\n\",\n    \"- **Gate:** only 5 of the 12 tasks pass the gate, i.e. the ban moves the model.\\n\",\n    \"- **C2a disconfirmed:** the claim \\\"the prompt route carries >= 2/3 of the ban\\\" fails. Pooled F_prompt = 0.61 and F_direct = 0.74.\\n\",\n    \"- **Task-dependent mechanism:**\\n\",\n    \"  - T03/T10: either route alone suffices.\\n\",\n    \"  - T05/T06: the ban works through the direct route.\\n\",\n    \"  - T13: both routes are needed.\\n\",\n    \"\\n\",\n    \"### What this notebook runs (CPU, a few minutes)\\n\",\n    \"1. **The S9 analysis code** (`src/analysis/analysis.py`) on a curated subset: 100 CRN slots of the `route_arms` dataset, i.e. 500 labelled programs by Qwen3-8B. It covers the gate, shares and route fractions, with a hierarchical bootstrap, BCa and leave-one-task-out jackknife intervals. It also runs leave-one-template-out, a Bayesian mixed GLM, the C2a verdict, CRN flip tables and first divergence, landings and C2c.\\n\",\n    \"2. **The original HF engine** (`src/engine.py`) on one CRN slot set, with a small Qwen3 model on CPU. This is the same prefill / KV-splice / span-drop / CRN-sampling code that ran Qwen3-8B on an L4 GPU. It uses the frozen prompt ids and the exact uniforms of the real run, and shows the Qwen3-8B rows of those slots beside its own output.\\n\",\n    \"\\n\",\n    \"Some stages are not re-run: the Qwen3-8B GPU queue (about 1.8 GPU-hours), the frozen labellers (bench harness + LLM judge) and the stages that need the upstream bench folders. Their outputs come in as the labelled `route_arms` data.\\n\",\n    \"\\n\",\n    \"### `method.py` stages and where they appear here\\n\",\n    \"| `uv run method.py <stage>` | what it does | in this notebook |\\n\",\n    \"|---|---|---|\\n\",\n    \"| `s0`, `recheck`, `s1`, `s2`, `tests` | input snapshot + bench sha256, labeller re-check, prompts with alignment asserts, frozen forecasts (n-grams, veto classes), CPU tests | not run; their frozen outputs (prompt ids, n-grams, veto classes, catalogues) ship in the data |\\n\",\n    \"| `gpu` + `label` | GPU queue: CRN-coupled sampling of every arm with Qwen3-8B, plus the streaming labeller | section 5 runs the engine on one slot set with a small model; the labels ship in the data |\\n\",\n    \"| `close1` | hash-chain commit of the analysis code before any ban sample | not applicable |\\n\",\n    \"| `analysis` | S9 analysis | sections 2-4, on the subset |\\n\",\n    \"| `figures`, `outputs`, `audit` | figures, `method_out.json`, independent re-derivation | section 6 (visualisation, demo vs. full run) |\"\n   ]\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"fc03631f\",\n   \"source\": \"import subprocess, sys\\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\\n\\n# loguru -- NOT pre-installed on Colab, always install\\n_pip('loguru==0.7.3')\\n\\n# numpy, pandas, scipy, statsmodels, matplotlib, torch, transformers -- pre-installed on Colab, install locally only\\n# (torch: Colab's CPU build, from the PyTorch CPU index, so a local run does not pull the CUDA wheels)\\nif 'google.colab' not in sys.modules:\\n    _pip('--index-url', 'https://download.pytorch.org/whl/cpu', 'torch==2.9.0+cpu')\\n    _pip('numpy==2.0.2', 'pandas==2.2.2', 'scipy==1.16.3', 'statsmodels==0.14.6', 'matplotlib==3.10.0',\\n         'transformers==5.0.0', 'tokenizers==0.22.2', 'huggingface_hub==1.4.0')\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"bc3a2b51\",\n   \"source\": \"# original imports of the code used below (src/cfg.py, src/engine.py, src/gpu.py, src/analysis/analysis.py)\\nimport collections\\nimport contextlib\\nimport gc\\nimport hashlib\\nimport json\\nimport math\\nimport os\\nimport re\\nimport sys\\nimport time\\nfrom pathlib import Path\\nfrom typing import Any, Callable, Iterable, Iterator\\n\\nimport numpy as np\\nimport torch\\nfrom loguru import logger\\nfrom scipy import stats\\n\\n# notebook additions: tables and figures\\nimport matplotlib.pyplot as plt\\nimport pandas as pd\\n\\npd.set_option(\\\"display.width\\\", 200)\\npd.set_option(\\\"display.max_columns\\\", 30)\\nprint(\\\"torch\\\", torch.__version__, \\\"| numpy\\\", np.__version__, \\\"| cuda available:\\\", torch.cuda.is_available())\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"4c26f4ad\",\n   \"source\": \"GITHUB_DATA_URL = \\\"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-3/experiment-16/demo/mini_demo_data.json\\\"\\nimport http.client\\nimport json\\nimport urllib.request\\nfrom pathlib import Path\\n\\ndef load_data():\\n    try:\\n        with urllib.request.urlopen(GITHUB_DATA_URL, timeout=15) as response:\\n            return json.loads(response.read().decode())\\n    # Network errors, timeouts, a placeholder URL, bad JSON, a cut-off response.\\n    except (OSError, ValueError, http.client.HTTPException) as e:\\n        print(\\\"GitHub data unavailable, using local mini_demo_data.json:\\\", e)\\n    local = Path(\\\"mini_demo_data.json\\\")\\n    if local.exists(): return json.loads(local.read_text())\\n    raise FileNotFoundError(\\\"Could not load mini_demo_data.json\\\")\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}"}
```

### [99] TOOL CALL — NotebookEdit · 2026-10-26 10:32:47 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': '4c26f4ad', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'data = load_data()\nmeta = data["metadata"]\nexamples = data["datasets"][0]["examples"]  # the route_arms dataset: one example per CRN slot (task, template, k)\nprint(meta["description"])\nprint("source:   ", meta["source"])\nprint("selection:", meta["selection_rule"])\nprint(f"{len(examples)} CRN slots | full-run model: {meta[\'model\']} ({meta[\'dtype\']}) | {meta[\'decoding\']}")\nprint("example:", {k: v for k, v in examples[0].items() if k != "metadata_token_ids"})'}
```

### [100] TOOL RESULT — NotebookEdit · 2026-10-26 10:32:47 UTC

```
{"new_source": "data = load_data()\nmeta = data[\"metadata\"]\nexamples = data[\"datasets\"][0][\"examples\"]  # the route_arms dataset: one example per CRN slot (task, template, k)\nprint(meta[\"description\"])\nprint(\"source:   \", meta[\"source\"])\nprint(\"selection:\", meta[\"selection_rule\"])\nprint(f\"{len(examples)} CRN slots | full-run model: {meta['model']} ({meta['dtype']}) | {meta['decoding']}\")\nprint(\"example:\", {k: v for k, v in examples[0].items() if k != \"metadata_token_ids\"})", "cell_type": "code", "language": "python", "edit_mode": "insert", "cell_id": "14389e18", "error": "", "notebook_path": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb", "original_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"title\",\n   \"metadata\": {},\n   \"source\": [\n    \"# Where a coding ban takes effect in Qwen3-8B: route-test demo\\n\",\n    \"\\n\",\n    \"**Artifact:** experiment-16 (`art__5akZ9W9iZM4`) of *Prompt bans substitute, not just subtract*.\\n\",\n    \"\\n\",\n    \"A prompt ban such as *\\\"Do not use a hash set of seen values for this task.\\\"* makes Qwen3-8B (bf16, thinking off) write a different algorithm. This experiment asks **which internal route carries that effect**, on the 12 frozen coding tasks of the bench. Every arm of a CRN slot `(task, template, k)` is sampled with the same **common random numbers** (CRN): one fixed stream of uniforms, turned into tokens by inverse-CDF sampling. The arms are built by **splicing KV caches** by position, so they differ only in the cache their generated tokens read:\\n\",\n    \"\\n\",\n    \"| arm | cache read by the generated tokens | what it tests |\\n\",\n    \"|---|---|---|\\n\",\n    \"| `a` | full ban prompt | clean endpoint |\\n\",\n    \"| `b` | token-length-matched neutral twin (*\\\"Do not use fire for this task. . .\\\"*) | corrupted endpoint |\\n\",\n    \"| `c` | twin condition segment + ban task-spec states | **prompt route**: do the later prompt states alone carry the ban? |\\n\",\n    \"| `d` | ban condition segment + twin task-spec states | **direct route**: is generated tokens reading the ban itself enough? |\\n\",\n    \"| `K0` | full ban, but the condition span is invisible to every generated token | removal of the direct route |\\n\",\n    \"\\n\",\n    \"Each generated program is labelled with its mechanism: runtime trace first, AST second, and a blind LLM judge on disagreement. For a task with default mechanism D, `s_X` is the share of arm X's attempts labelled D. The route fractions are\\n\",\n    \"\\n\",\n    \"$$F_\\\\text{prompt}=\\\\frac{s_b-s_c}{s_b-s_a},\\\\quad F_\\\\text{direct}=\\\\frac{s_b-s_d}{s_b-s_a},\\\\quad I=1-F_\\\\text{prompt}-F_\\\\text{direct},\\\\quad F_\\\\text{K0}=\\\\frac{s_b-s_{K0}}{s_b-s_a}.$$\\n\",\n    \"\\n\",\n    \"**Full-run result (13,030 samples).**\\n\",\n    \"- **Gate:** only 5 of the 12 tasks pass the gate, i.e. the ban moves the model.\\n\",\n    \"- **C2a disconfirmed:** the claim \\\"the prompt route carries >= 2/3 of the ban\\\" fails. Pooled F_prompt = 0.61 and F_direct = 0.74.\\n\",\n    \"- **Task-dependent mechanism:**\\n\",\n    \"  - T03/T10: either route alone suffices.\\n\",\n    \"  - T05/T06: the ban works through the direct route.\\n\",\n    \"  - T13: both routes are needed.\\n\",\n    \"\\n\",\n    \"### What this notebook runs (CPU, a few minutes)\\n\",\n    \"1. **The S9 analysis code** (`src/analysis/analysis.py`) on a curated subset: 100 CRN slots of the `route_arms` dataset, i.e. 500 labelled programs by Qwen3-8B. It covers the gate, shares and route fractions, with a hierarchical bootstrap, BCa and leave-one-task-out jackknife intervals. It also runs leave-one-template-out, a Bayesian mixed GLM, the C2a verdict, CRN flip tables and first divergence, landings and C2c.\\n\",\n    \"2. **The original HF engine** (`src/engine.py`) on one CRN slot set, with a small Qwen3 model on CPU. This is the same prefill / KV-splice / span-drop / CRN-sampling code that ran Qwen3-8B on an L4 GPU. It uses the frozen prompt ids and the exact uniforms of the real run, and shows the Qwen3-8B rows of those slots beside its own output.\\n\",\n    \"\\n\",\n    \"Some stages are not re-run: the Qwen3-8B GPU queue (about 1.8 GPU-hours), the frozen labellers (bench harness + LLM judge) and the stages that need the upstream bench folders. Their outputs come in as the labelled `route_arms` data.\\n\",\n    \"\\n\",\n    \"### `method.py` stages and where they appear here\\n\",\n    \"| `uv run method.py <stage>` | what it does | in this notebook |\\n\",\n    \"|---|---|---|\\n\",\n    \"| `s0`, `recheck`, `s1`, `s2`, `tests` | input snapshot + bench sha256, labeller re-check, prompts with alignment asserts, frozen forecasts (n-grams, veto classes), CPU tests | not run; their frozen outputs (prompt ids, n-grams, veto classes, catalogues) ship in the data |\\n\",\n    \"| `gpu` + `label` | GPU queue: CRN-coupled sampling of every arm with Qwen3-8B, plus the streaming labeller | section 5 runs the engine on one slot set with a small model; the labels ship in the data |\\n\",\n    \"| `close1` | hash-chain commit of the analysis code before any ban sample | not applicable |\\n\",\n    \"| `analysis` | S9 analysis | sections 2-4, on the subset |\\n\",\n    \"| `figures`, `outputs`, `audit` | figures, `method_out.json`, independent re-derivation | section 6 (visualisation, demo vs. full run) |\"\n   ]\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"fc03631f\",\n   \"source\": \"import subprocess, sys\\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\\n\\n# loguru -- NOT pre-installed on Colab, always install\\n_pip('loguru==0.7.3')\\n\\n# numpy, pandas, scipy, statsmodels, matplotlib, torch, transformers -- pre-installed on Colab, install locally only\\n# (torch: Colab's CPU build, from the PyTorch CPU index, so a local run does not pull the CUDA wheels)\\nif 'google.colab' not in sys.modules:\\n    _pip('--index-url', 'https://download.pytorch.org/whl/cpu', 'torch==2.9.0+cpu')\\n    _pip('numpy==2.0.2', 'pandas==2.2.2', 'scipy==1.16.3', 'statsmodels==0.14.6', 'matplotlib==3.10.0',\\n         'transformers==5.0.0', 'tokenizers==0.22.2', 'huggingface_hub==1.4.0')\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"bc3a2b51\",\n   \"source\": \"# original imports of the code used below (src/cfg.py, src/engine.py, src/gpu.py, src/analysis/analysis.py)\\nimport collections\\nimport contextlib\\nimport gc\\nimport hashlib\\nimport json\\nimport math\\nimport os\\nimport re\\nimport sys\\nimport time\\nfrom pathlib import Path\\nfrom typing import Any, Callable, Iterable, Iterator\\n\\nimport numpy as np\\nimport torch\\nfrom loguru import logger\\nfrom scipy import stats\\n\\n# notebook additions: tables and figures\\nimport matplotlib.pyplot as plt\\nimport pandas as pd\\n\\npd.set_option(\\\"display.width\\\", 200)\\npd.set_option(\\\"display.max_columns\\\", 30)\\nprint(\\\"torch\\\", torch.__version__, \\\"| numpy\\\", np.__version__, \\\"| cuda available:\\\", torch.cuda.is_available())\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"4c26f4ad\",\n   \"source\": \"GITHUB_DATA_URL = \\\"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-3/experiment-16/demo/mini_demo_data.json\\\"\\nimport http.client\\nimport json\\nimport urllib.request\\nfrom pathlib import Path\\n\\ndef load_data():\\n    try:\\n        with urllib.request.urlopen(GITHUB_DATA_URL, timeout=15) as response:\\n            return json.loads(response.read().decode())\\n    # Network errors, timeouts, a placeholder URL, bad JSON, a cut-off response.\\n    except (OSError, ValueError, http.client.HTTPException) as e:\\n        print(\\\"GitHub data unavailable, using local mini_demo_data.json:\\\", e)\\n    local = Path(\\\"mini_demo_data.json\\\")\\n    if local.exists(): return json.loads(local.read_text())\\n    raise FileNotFoundError(\\\"Could not load mini_demo_data.json\\\")\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}", "updated_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"title\",\n   \"metadata\": {},\n   \"source\": [\n    \"# Where a coding ban takes effect in Qwen3-8B: route-test demo\\n\",\n    \"\\n\",\n    \"**Artifact:** experiment-16 (`art__5akZ9W9iZM4`) of *Prompt bans substitute, not just subtract*.\\n\",\n    \"\\n\",\n    \"A prompt ban such as *\\\"Do not use a hash set of seen values for this task.\\\"* makes Qwen3-8B (bf16, thinking off) write a different algorithm. This experiment asks **which internal route carries that effect**, on the 12 frozen coding tasks of the bench. Every arm of a CRN slot `(task, template, k)` is sampled with the same **common random numbers** (CRN): one fixed stream of uniforms, turned into tokens by inverse-CDF sampling. The arms are built by **splicing KV caches** by position, so they differ only in the cache their generated tokens read:\\n\",\n    \"\\n\",\n    \"| arm | cache read by the generated tokens | what it tests |\\n\",\n    \"|---|---|---|\\n\",\n    \"| `a` | full ban prompt | clean endpoint |\\n\",\n    \"| `b` | token-length-matched neutral twin (*\\\"Do not use fire for this task. . .\\\"*) | corrupted endpoint |\\n\",\n    \"| `c` | twin condition segment + ban task-spec states | **prompt route**: do the later prompt states alone carry the ban? |\\n\",\n    \"| `d` | ban condition segment + twin task-spec states | **direct route**: is generated tokens reading the ban itself enough? |\\n\",\n    \"| `K0` | full ban, but the condition span is invisible to every generated token | removal of the direct route |\\n\",\n    \"\\n\",\n    \"Each generated program is labelled with its mechanism: runtime trace first, AST second, and a blind LLM judge on disagreement. For a task with default mechanism D, `s_X` is the share of arm X's attempts labelled D. The route fractions are\\n\",\n    \"\\n\",\n    \"$$F_\\\\text{prompt}=\\\\frac{s_b-s_c}{s_b-s_a},\\\\quad F_\\\\text{direct}=\\\\frac{s_b-s_d}{s_b-s_a},\\\\quad I=1-F_\\\\text{prompt}-F_\\\\text{direct},\\\\quad F_\\\\text{K0}=\\\\frac{s_b-s_{K0}}{s_b-s_a}.$$\\n\",\n    \"\\n\",\n    \"**Full-run result (13,030 samples).**\\n\",\n    \"- **Gate:** only 5 of the 12 tasks pass the gate, i.e. the ban moves the model.\\n\",\n    \"- **C2a disconfirmed:** the claim \\\"the prompt route carries >= 2/3 of the ban\\\" fails. Pooled F_prompt = 0.61 and F_direct = 0.74.\\n\",\n    \"- **Task-dependent mechanism:**\\n\",\n    \"  - T03/T10: either route alone suffices.\\n\",\n    \"  - T05/T06: the ban works through the direct route.\\n\",\n    \"  - T13: both routes are needed.\\n\",\n    \"\\n\",\n    \"### What this notebook runs (CPU, a few minutes)\\n\",\n    \"1. **The S9 analysis code** (`src/analysis/analysis.py`) on a curated subset: 100 CRN slots of the `route_arms` dataset, i.e. 500 labelled programs by Qwen3-8B. It covers the gate, shares and route fractions, with a hierarchical bootstrap, BCa and leave-one-task-out jackknife intervals. It also runs leave-one-template-out, a Bayesian mixed GLM, the C2a verdict, CRN flip tables and first divergence, landings and C2c.\\n\",\n    \"2. **The original HF engine** (`src/engine.py`) on one CRN slot set, with a small Qwen3 model on CPU. This is the same prefill / KV-splice / span-drop / CRN-sampling code that ran Qwen3-8B on an L4 GPU. It uses the frozen prompt ids and the exact uniforms of the real run, and shows the Qwen3-8B rows of those slots beside its own output.\\n\",\n    \"\\n\",\n    \"Some stages are not re-run: the Qwen3-8B GPU queue (about 1.8 GPU-hours), the frozen labellers (bench harness + LLM judge) and the stages that need the upstream bench folders. Their outputs come in as the labelled `route_arms` data.\\n\",\n    \"\\n\",\n    \"### `method.py` stages and where they appear here\\n\",\n    \"| `uv run method.py <stage>` | what it does | in this notebook |\\n\",\n    \"|---|---|---|\\n\",\n    \"| `s0`, `recheck`, `s1`, `s2`, `tests` | input snapshot + bench sha256, labeller re-check, prompts with alignment asserts, frozen forecasts (n-grams, veto classes), CPU tests | not run; their frozen outputs (prompt ids, n-grams, veto classes, catalogues) ship in the data |\\n\",\n    \"| `gpu` + `label` | GPU queue: CRN-coupled sampling of every arm with Qwen3-8B, plus the streaming labeller | section 5 runs the engine on one slot set with a small model; the labels ship in the data |\\n\",\n    \"| `close1` | hash-chain commit of the analysis code before any ban sample | not applicable |\\n\",\n    \"| `analysis` | S9 analysis | sections 2-4, on the subset |\\n\",\n    \"| `figures`, `outputs`, `audit` | figures, `method_out.json`, independent re-derivation | section 6 (visualisation, demo vs. full run) |\"\n   ]\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"fc03631f\",\n   \"source\": \"import subprocess, sys\\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\\n\\n# loguru -- NOT pre-installed on Colab, always install\\n_pip('loguru==0.7.3')\\n\\n# numpy, pandas, scipy, statsmodels, matplotlib, torch, transformers -- pre-installed on Colab, install locally only\\n# (torch: Colab's CPU build, from the PyTorch CPU index, so a local run does not pull the CUDA wheels)\\nif 'google.colab' not in sys.modules:\\n    _pip('--index-url', 'https://download.pytorch.org/whl/cpu', 'torch==2.9.0+cpu')\\n    _pip('numpy==2.0.2', 'pandas==2.2.2', 'scipy==1.16.3', 'statsmodels==0.14.6', 'matplotlib==3.10.0',\\n         'transformers==5.0.0', 'tokenizers==0.22.2', 'huggingface_hub==1.4.0')\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"bc3a2b51\",\n   \"source\": \"# original imports of the code used below (src/cfg.py, src/engine.py, src/gpu.py, src/analysis/analysis.py)\\nimport collections\\nimport contextlib\\nimport gc\\nimport hashlib\\nimport json\\nimport math\\nimport os\\nimport re\\nimport sys\\nimport time\\nfrom pathlib import Path\\nfrom typing import Any, Callable, Iterable, Iterator\\n\\nimport numpy as np\\nimport torch\\nfrom loguru import logger\\nfrom scipy import stats\\n\\n# notebook additions: tables and figures\\nimport matplotlib.pyplot as plt\\nimport pandas as pd\\n\\npd.set_option(\\\"display.width\\\", 200)\\npd.set_option(\\\"display.max_columns\\\", 30)\\nprint(\\\"torch\\\", torch.__version__, \\\"| numpy\\\", np.__version__, \\\"| cuda available:\\\", torch.cuda.is_available())\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"4c26f4ad\",\n   \"source\": \"GITHUB_DATA_URL = \\\"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-3/experiment-16/demo/mini_demo_data.json\\\"\\nimport http.client\\nimport json\\nimport urllib.request\\nfrom pathlib import Path\\n\\ndef load_data():\\n    try:\\n        with urllib.request.urlopen(GITHUB_DATA_URL, timeout=15) as response:\\n            return json.loads(response.read().decode())\\n    # Network errors, timeouts, a placeholder URL, bad JSON, a cut-off response.\\n    except (OSError, ValueError, http.client.HTTPException) as e:\\n        print(\\\"GitHub data unavailable, using local mini_demo_data.json:\\\", e)\\n    local = Path(\\\"mini_demo_data.json\\\")\\n    if local.exists(): return json.loads(local.read_text())\\n    raise FileNotFoundError(\\\"Could not load mini_demo_data.json\\\")\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"14389e18\",\n   \"source\": \"data = load_data()\\nmeta = data[\\\"metadata\\\"]\\nexamples = data[\\\"datasets\\\"][0][\\\"examples\\\"]  # the route_arms dataset: one example per CRN slot (task, template, k)\\nprint(meta[\\\"description\\\"])\\nprint(\\\"source:   \\\", meta[\\\"source\\\"])\\nprint(\\\"selection:\\\", meta[\\\"selection_rule\\\"])\\nprint(f\\\"{len(examples)} CRN slots | full-run model: {meta['model']} ({meta['dtype']}) | {meta['decoding']}\\\")\\nprint(\\\"example:\\\", {k: v for k, v in examples[0].items() if k != \\\"metadata_token_ids\\\"})\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}"}
```

### [101] ASSISTANT · 2026-10-26 10:32:57 UTC

```
Now the config section, starting at the minimum values for the first test run.
```

### [102] TOOL CALL — NotebookEdit · 2026-10-26 10:32:57 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': '14389e18', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': '## Config\n\nEvery tunable parameter is set here, and each comment gives the original value.\n\n- **Resampling counts:** the bootstrap, permutation and resampling-null counts can go straight back to the original values. They cost seconds at this data size.\n- **`N_SLOTS`:** must match the demo data, which has 3 CRN slots per template on the gated tasks. The full run has 20.\n- **Engine model:** the engine cell runs a small Qwen3 model. It shares Qwen3-8B\'s tokenizer, so the frozen prompt ids and the CRN uniforms of the real run apply unchanged. Set `ENGINE_MODEL_ID = "Qwen/Qwen3-8B"` (with `ENGINE_REVISION` = the original revision, `ENGINE_DTYPE = torch.bfloat16` and a GPU with more than 17 GB) to run the original model.\n\nFunctions take some of these values as defaults when they are defined. After editing this cell, re-run the notebook from here.'}
```

### [103] TOOL RESULT — NotebookEdit · 2026-10-26 10:32:57 UTC

```
{"new_source": "## Config\n\nEvery tunable parameter is set here, and each comment gives the original value.\n\n- **Resampling counts:** the bootstrap, permutation and resampling-null counts can go straight back to the original values. They cost seconds at this data size.\n- **`N_SLOTS`:** must match the demo data, which has 3 CRN slots per template on the gated tasks. The full run has 20.\n- **Engine model:** the engine cell runs a small Qwen3 model. It shares Qwen3-8B's tokenizer, so the frozen prompt ids and the CRN uniforms of the real run apply unchanged. Set `ENGINE_MODEL_ID = \"Qwen/Qwen3-8B\"` (with `ENGINE_REVISION` = the original revision, `ENGINE_DTYPE = torch.bfloat16` and a GPU with more than 17 GB) to run the original model.\n\nFunctions take some of these values as defaults when they are defined. After editing this cell, re-run the notebook from here.", "cell_type": "markdown", "language": "python", "edit_mode": "insert", "cell_id": "4e32fa9b", "error": "", "notebook_path": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb", "original_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"title\",\n   \"metadata\": {},\n   \"source\": [\n    \"# Where a coding ban takes effect in Qwen3-8B: route-test demo\\n\",\n    \"\\n\",\n    \"**Artifact:** experiment-16 (`art__5akZ9W9iZM4`) of *Prompt bans substitute, not just subtract*.\\n\",\n    \"\\n\",\n    \"A prompt ban such as *\\\"Do not use a hash set of seen values for this task.\\\"* makes Qwen3-8B (bf16, thinking off) write a different algorithm. This experiment asks **which internal route carries that effect**, on the 12 frozen coding tasks of the bench. Every arm of a CRN slot `(task, template, k)` is sampled with the same **common random numbers** (CRN): one fixed stream of uniforms, turned into tokens by inverse-CDF sampling. The arms are built by **splicing KV caches** by position, so they differ only in the cache their generated tokens read:\\n\",\n    \"\\n\",\n    \"| arm | cache read by the generated tokens | what it tests |\\n\",\n    \"|---|---|---|\\n\",\n    \"| `a` | full ban prompt | clean endpoint |\\n\",\n    \"| `b` | token-length-matched neutral twin (*\\\"Do not use fire for this task. . .\\\"*) | corrupted endpoint |\\n\",\n    \"| `c` | twin condition segment + ban task-spec states | **prompt route**: do the later prompt states alone carry the ban? |\\n\",\n    \"| `d` | ban condition segment + twin task-spec states | **direct route**: is generated tokens reading the ban itself enough? |\\n\",\n    \"| `K0` | full ban, but the condition span is invisible to every generated token | removal of the direct route |\\n\",\n    \"\\n\",\n    \"Each generated program is labelled with its mechanism: runtime trace first, AST second, and a blind LLM judge on disagreement. For a task with default mechanism D, `s_X` is the share of arm X's attempts labelled D. The route fractions are\\n\",\n    \"\\n\",\n    \"$$F_\\\\text{prompt}=\\\\frac{s_b-s_c}{s_b-s_a},\\\\quad F_\\\\text{direct}=\\\\frac{s_b-s_d}{s_b-s_a},\\\\quad I=1-F_\\\\text{prompt}-F_\\\\text{direct},\\\\quad F_\\\\text{K0}=\\\\frac{s_b-s_{K0}}{s_b-s_a}.$$\\n\",\n    \"\\n\",\n    \"**Full-run result (13,030 samples).**\\n\",\n    \"- **Gate:** only 5 of the 12 tasks pass the gate, i.e. the ban moves the model.\\n\",\n    \"- **C2a disconfirmed:** the claim \\\"the prompt route carries >= 2/3 of the ban\\\" fails. Pooled F_prompt = 0.61 and F_direct = 0.74.\\n\",\n    \"- **Task-dependent mechanism:**\\n\",\n    \"  - T03/T10: either route alone suffices.\\n\",\n    \"  - T05/T06: the ban works through the direct route.\\n\",\n    \"  - T13: both routes are needed.\\n\",\n    \"\\n\",\n    \"### What this notebook runs (CPU, a few minutes)\\n\",\n    \"1. **The S9 analysis code** (`src/analysis/analysis.py`) on a curated subset: 100 CRN slots of the `route_arms` dataset, i.e. 500 labelled programs by Qwen3-8B. It covers the gate, shares and route fractions, with a hierarchical bootstrap, BCa and leave-one-task-out jackknife intervals. It also runs leave-one-template-out, a Bayesian mixed GLM, the C2a verdict, CRN flip tables and first divergence, landings and C2c.\\n\",\n    \"2. **The original HF engine** (`src/engine.py`) on one CRN slot set, with a small Qwen3 model on CPU. This is the same prefill / KV-splice / span-drop / CRN-sampling code that ran Qwen3-8B on an L4 GPU. It uses the frozen prompt ids and the exact uniforms of the real run, and shows the Qwen3-8B rows of those slots beside its own output.\\n\",\n    \"\\n\",\n    \"Some stages are not re-run: the Qwen3-8B GPU queue (about 1.8 GPU-hours), the frozen labellers (bench harness + LLM judge) and the stages that need the upstream bench folders. Their outputs come in as the labelled `route_arms` data.\\n\",\n    \"\\n\",\n    \"### `method.py` stages and where they appear here\\n\",\n    \"| `uv run method.py <stage>` | what it does | in this notebook |\\n\",\n    \"|---|---|---|\\n\",\n    \"| `s0`, `recheck`, `s1`, `s2`, `tests` | input snapshot + bench sha256, labeller re-check, prompts with alignment asserts, frozen forecasts (n-grams, veto classes), CPU tests | not run; their frozen outputs (prompt ids, n-grams, veto classes, catalogues) ship in the data |\\n\",\n    \"| `gpu` + `label` | GPU queue: CRN-coupled sampling of every arm with Qwen3-8B, plus the streaming labeller | section 5 runs the engine on one slot set with a small model; the labels ship in the data |\\n\",\n    \"| `close1` | hash-chain commit of the analysis code before any ban sample | not applicable |\\n\",\n    \"| `analysis` | S9 analysis | sections 2-4, on the subset |\\n\",\n    \"| `figures`, `outputs`, `audit` | figures, `method_out.json`, independent re-derivation | section 6 (visualisation, demo vs. full run) |\"\n   ]\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"fc03631f\",\n   \"source\": \"import subprocess, sys\\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\\n\\n# loguru -- NOT pre-installed on Colab, always install\\n_pip('loguru==0.7.3')\\n\\n# numpy, pandas, scipy, statsmodels, matplotlib, torch, transformers -- pre-installed on Colab, install locally only\\n# (torch: Colab's CPU build, from the PyTorch CPU index, so a local run does not pull the CUDA wheels)\\nif 'google.colab' not in sys.modules:\\n    _pip('--index-url', 'https://download.pytorch.org/whl/cpu', 'torch==2.9.0+cpu')\\n    _pip('numpy==2.0.2', 'pandas==2.2.2', 'scipy==1.16.3', 'statsmodels==0.14.6', 'matplotlib==3.10.0',\\n         'transformers==5.0.0', 'tokenizers==0.22.2', 'huggingface_hub==1.4.0')\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"bc3a2b51\",\n   \"source\": \"# original imports of the code used below (src/cfg.py, src/engine.py, src/gpu.py, src/analysis/analysis.py)\\nimport collections\\nimport contextlib\\nimport gc\\nimport hashlib\\nimport json\\nimport math\\nimport os\\nimport re\\nimport sys\\nimport time\\nfrom pathlib import Path\\nfrom typing import Any, Callable, Iterable, Iterator\\n\\nimport numpy as np\\nimport torch\\nfrom loguru import logger\\nfrom scipy import stats\\n\\n# notebook additions: tables and figures\\nimport matplotlib.pyplot as plt\\nimport pandas as pd\\n\\npd.set_option(\\\"display.width\\\", 200)\\npd.set_option(\\\"display.max_columns\\\", 30)\\nprint(\\\"torch\\\", torch.__version__, \\\"| numpy\\\", np.__version__, \\\"| cuda available:\\\", torch.cuda.is_available())\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"4c26f4ad\",\n   \"source\": \"GITHUB_DATA_URL = \\\"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-3/experiment-16/demo/mini_demo_data.json\\\"\\nimport http.client\\nimport json\\nimport urllib.request\\nfrom pathlib import Path\\n\\ndef load_data():\\n    try:\\n        with urllib.request.urlopen(GITHUB_DATA_URL, timeout=15) as response:\\n            return json.loads(response.read().decode())\\n    # Network errors, timeouts, a placeholder URL, bad JSON, a cut-off response.\\n    except (OSError, ValueError, http.client.HTTPException) as e:\\n        print(\\\"GitHub data unavailable, using local mini_demo_data.json:\\\", e)\\n    local = Path(\\\"mini_demo_data.json\\\")\\n    if local.exists(): return json.loads(local.read_text())\\n    raise FileNotFoundError(\\\"Could not load mini_demo_data.json\\\")\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"14389e18\",\n   \"source\": \"data = load_data()\\nmeta = data[\\\"metadata\\\"]\\nexamples = data[\\\"datasets\\\"][0][\\\"examples\\\"]  # the route_arms dataset: one example per CRN slot (task, template, k)\\nprint(meta[\\\"description\\\"])\\nprint(\\\"source:   \\\", meta[\\\"source\\\"])\\nprint(\\\"selection:\\\", meta[\\\"selection_rule\\\"])\\nprint(f\\\"{len(examples)} CRN slots | full-run model: {meta['model']} ({meta['dtype']}) | {meta['decoding']}\\\")\\nprint(\\\"example:\\\", {k: v for k, v in examples[0].items() if k != \\\"metadata_token_ids\\\"})\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}", "updated_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"title\",\n   \"metadata\": {},\n   \"source\": [\n    \"# Where a coding ban takes effect in Qwen3-8B: route-test demo\\n\",\n    \"\\n\",\n    \"**Artifact:** experiment-16 (`art__5akZ9W9iZM4`) of *Prompt bans substitute, not just subtract*.\\n\",\n    \"\\n\",\n    \"A prompt ban such as *\\\"Do not use a hash set of seen values for this task.\\\"* makes Qwen3-8B (bf16, thinking off) write a different algorithm. This experiment asks **which internal route carries that effect**, on the 12 frozen coding tasks of the bench. Every arm of a CRN slot `(task, template, k)` is sampled with the same **common random numbers** (CRN): one fixed stream of uniforms, turned into tokens by inverse-CDF sampling. The arms are built by **splicing KV caches** by position, so they differ only in the cache their generated tokens read:\\n\",\n    \"\\n\",\n    \"| arm | cache read by the generated tokens | what it tests |\\n\",\n    \"|---|---|---|\\n\",\n    \"| `a` | full ban prompt | clean endpoint |\\n\",\n    \"| `b` | token-length-matched neutral twin (*\\\"Do not use fire for this task. . .\\\"*) | corrupted endpoint |\\n\",\n    \"| `c` | twin condition segment + ban task-spec states | **prompt route**: do the later prompt states alone carry the ban? |\\n\",\n    \"| `d` | ban condition segment + twin task-spec states | **direct route**: is generated tokens reading the ban itself enough? |\\n\",\n    \"| `K0` | full ban, but the condition span is invisible to every generated token | removal of the direct route |\\n\",\n    \"\\n\",\n    \"Each generated program is labelled with its mechanism: runtime trace first, AST second, and a blind LLM judge on disagreement. For a task with default mechanism D, `s_X` is the share of arm X's attempts labelled D. The route fractions are\\n\",\n    \"\\n\",\n    \"$$F_\\\\text{prompt}=\\\\frac{s_b-s_c}{s_b-s_a},\\\\quad F_\\\\text{direct}=\\\\frac{s_b-s_d}{s_b-s_a},\\\\quad I=1-F_\\\\text{prompt}-F_\\\\text{direct},\\\\quad F_\\\\text{K0}=\\\\frac{s_b-s_{K0}}{s_b-s_a}.$$\\n\",\n    \"\\n\",\n    \"**Full-run result (13,030 samples).**\\n\",\n    \"- **Gate:** only 5 of the 12 tasks pass the gate, i.e. the ban moves the model.\\n\",\n    \"- **C2a disconfirmed:** the claim \\\"the prompt route carries >= 2/3 of the ban\\\" fails. Pooled F_prompt = 0.61 and F_direct = 0.74.\\n\",\n    \"- **Task-dependent mechanism:**\\n\",\n    \"  - T03/T10: either route alone suffices.\\n\",\n    \"  - T05/T06: the ban works through the direct route.\\n\",\n    \"  - T13: both routes are needed.\\n\",\n    \"\\n\",\n    \"### What this notebook runs (CPU, a few minutes)\\n\",\n    \"1. **The S9 analysis code** (`src/analysis/analysis.py`) on a curated subset: 100 CRN slots of the `route_arms` dataset, i.e. 500 labelled programs by Qwen3-8B. It covers the gate, shares and route fractions, with a hierarchical bootstrap, BCa and leave-one-task-out jackknife intervals. It also runs leave-one-template-out, a Bayesian mixed GLM, the C2a verdict, CRN flip tables and first divergence, landings and C2c.\\n\",\n    \"2. **The original HF engine** (`src/engine.py`) on one CRN slot set, with a small Qwen3 model on CPU. This is the same prefill / KV-splice / span-drop / CRN-sampling code that ran Qwen3-8B on an L4 GPU. It uses the frozen prompt ids and the exact uniforms of the real run, and shows the Qwen3-8B rows of those slots beside its own output.\\n\",\n    \"\\n\",\n    \"Some stages are not re-run: the Qwen3-8B GPU queue (about 1.8 GPU-hours), the frozen labellers (bench harness + LLM judge) and the stages that need the upstream bench folders. Their outputs come in as the labelled `route_arms` data.\\n\",\n    \"\\n\",\n    \"### `method.py` stages and where they appear here\\n\",\n    \"| `uv run method.py <stage>` | what it does | in this notebook |\\n\",\n    \"|---|---|---|\\n\",\n    \"| `s0`, `recheck`, `s1`, `s2`, `tests` | input snapshot + bench sha256, labeller re-check, prompts with alignment asserts, frozen forecasts (n-grams, veto classes), CPU tests | not run; their frozen outputs (prompt ids, n-grams, veto classes, catalogues) ship in the data |\\n\",\n    \"| `gpu` + `label` | GPU queue: CRN-coupled sampling of every arm with Qwen3-8B, plus the streaming labeller | section 5 runs the engine on one slot set with a small model; the labels ship in the data |\\n\",\n    \"| `close1` | hash-chain commit of the analysis code before any ban sample | not applicable |\\n\",\n    \"| `analysis` | S9 analysis | sections 2-4, on the subset |\\n\",\n    \"| `figures`, `outputs`, `audit` | figures, `method_out.json`, independent re-derivation | section 6 (visualisation, demo vs. full run) |\"\n   ]\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"fc03631f\",\n   \"source\": \"import subprocess, sys\\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\\n\\n# loguru -- NOT pre-installed on Colab, always install\\n_pip('loguru==0.7.3')\\n\\n# numpy, pandas, scipy, statsmodels, matplotlib, torch, transformers -- pre-installed on Colab, install locally only\\n# (torch: Colab's CPU build, from the PyTorch CPU index, so a local run does not pull the CUDA wheels)\\nif 'google.colab' not in sys.modules:\\n    _pip('--index-url', 'https://download.pytorch.org/whl/cpu', 'torch==2.9.0+cpu')\\n    _pip('numpy==2.0.2', 'pandas==2.2.2', 'scipy==1.16.3', 'statsmodels==0.14.6', 'matplotlib==3.10.0',\\n         'transformers==5.0.0', 'tokenizers==0.22.2', 'huggingface_hub==1.4.0')\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"bc3a2b51\",\n   \"source\": \"# original imports of the code used below (src/cfg.py, src/engine.py, src/gpu.py, src/analysis/analysis.py)\\nimport collections\\nimport contextlib\\nimport gc\\nimport hashlib\\nimport json\\nimport math\\nimport os\\nimport re\\nimport sys\\nimport time\\nfrom pathlib import Path\\nfrom typing import Any, Callable, Iterable, Iterator\\n\\nimport numpy as np\\nimport torch\\nfrom loguru import logger\\nfrom scipy import stats\\n\\n# notebook additions: tables and figures\\nimport matplotlib.pyplot as plt\\nimport pandas as pd\\n\\npd.set_option(\\\"display.width\\\", 200)\\npd.set_option(\\\"display.max_columns\\\", 30)\\nprint(\\\"torch\\\", torch.__version__, \\\"| numpy\\\", np.__version__, \\\"| cuda available:\\\", torch.cuda.is_available())\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"4c26f4ad\",\n   \"source\": \"GITHUB_DATA_URL = \\\"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-3/experiment-16/demo/mini_demo_data.json\\\"\\nimport http.client\\nimport json\\nimport urllib.request\\nfrom pathlib import Path\\n\\ndef load_data():\\n    try:\\n        with urllib.request.urlopen(GITHUB_DATA_URL, timeout=15) as response:\\n            return json.loads(response.read().decode())\\n    # Network errors, timeouts, a placeholder URL, bad JSON, a cut-off response.\\n    except (OSError, ValueError, http.client.HTTPException) as e:\\n        print(\\\"GitHub data unavailable, using local mini_demo_data.json:\\\", e)\\n    local = Path(\\\"mini_demo_data.json\\\")\\n    if local.exists(): return json.loads(local.read_text())\\n    raise FileNotFoundError(\\\"Could not load mini_demo_data.json\\\")\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"14389e18\",\n   \"source\": \"data = load_data()\\nmeta = data[\\\"metadata\\\"]\\nexamples = data[\\\"datasets\\\"][0][\\\"examples\\\"]  # the route_arms dataset: one example per CRN slot (task, template, k)\\nprint(meta[\\\"description\\\"])\\nprint(\\\"source:   \\\", meta[\\\"source\\\"])\\nprint(\\\"selection:\\\", meta[\\\"selection_rule\\\"])\\nprint(f\\\"{len(examples)} CRN slots | full-run model: {meta['model']} ({meta['dtype']}) | {meta['decoding']}\\\")\\nprint(\\\"example:\\\", {k: v for k, v in examples[0].items() if k != \\\"metadata_token_ids\\\"})\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"4e32fa9b\",\n   \"source\": \"## Config\\n\\nEvery tunable parameter is set here, and each comment gives the original value.\\n\\n- **Resampling counts:** the bootstrap, permutation and resampling-null counts can go straight back to the original values. They cost seconds at this data size.\\n- **`N_SLOTS`:** must match the demo data, which has 3 CRN slots per template on the gated tasks. The full run has 20.\\n- **Engine model:** the engine cell runs a small Qwen3 model. It shares Qwen3-8B's tokenizer, so the frozen prompt ids and the CRN uniforms of the real run apply unchanged. Set `ENGINE_MODEL_ID = \\\"Qwen/Qwen3-8B\\\"` (with `ENGINE_REVISION` = the original revision, `ENGINE_DTYPE = torch.bfloat16` and a GPU with more than 17 GB) to run the original model.\\n\\nFunctions take some of these values as defaults when they are defined. After editing this cell, re-run the notebook from here.\",\n   \"metadata\": {}\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}"}
```

### [104] TOOL CALL — NotebookEdit · 2026-10-26 10:32:57 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': '14389e18', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': 'PLACEHOLDER'}
```

### [105] TOOL RESULT — NotebookEdit · 2026-10-26 10:32:57 UTC

```
{"new_source": "PLACEHOLDER", "cell_type": "markdown", "language": "python", "edit_mode": "insert", "cell_id": "352080db", "error": "", "notebook_path": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb", "original_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"title\",\n   \"metadata\": {},\n   \"source\": [\n    \"# Where a coding ban takes effect in Qwen3-8B: route-test demo\\n\",\n    \"\\n\",\n    \"**Artifact:** experiment-16 (`art__5akZ9W9iZM4`) of *Prompt bans substitute, not just subtract*.\\n\",\n    \"\\n\",\n    \"A prompt ban such as *\\\"Do not use a hash set of seen values for this task.\\\"* makes Qwen3-8B (bf16, thinking off) write a different algorithm. This experiment asks **which internal route carries that effect**, on the 12 frozen coding tasks of the bench. Every arm of a CRN slot `(task, template, k)` is sampled with the same **common random numbers** (CRN): one fixed stream of uniforms, turned into tokens by inverse-CDF sampling. The arms are built by **splicing KV caches** by position, so they differ only in the cache their generated tokens read:\\n\",\n    \"\\n\",\n    \"| arm | cache read by the generated tokens | what it tests |\\n\",\n    \"|---|---|---|\\n\",\n    \"| `a` | full ban prompt | clean endpoint |\\n\",\n    \"| `b` | token-length-matched neutral twin (*\\\"Do not use fire for this task. . .\\\"*) | corrupted endpoint |\\n\",\n    \"| `c` | twin condition segment + ban task-spec states | **prompt route**: do the later prompt states alone carry the ban? |\\n\",\n    \"| `d` | ban condition segment + twin task-spec states | **direct route**: is generated tokens reading the ban itself enough? |\\n\",\n    \"| `K0` | full ban, but the condition span is invisible to every generated token | removal of the direct route |\\n\",\n    \"\\n\",\n    \"Each generated program is labelled with its mechanism: runtime trace first, AST second, and a blind LLM judge on disagreement. For a task with default mechanism D, `s_X` is the share of arm X's attempts labelled D. The route fractions are\\n\",\n    \"\\n\",\n    \"$$F_\\\\text{prompt}=\\\\frac{s_b-s_c}{s_b-s_a},\\\\quad F_\\\\text{direct}=\\\\frac{s_b-s_d}{s_b-s_a},\\\\quad I=1-F_\\\\text{prompt}-F_\\\\text{direct},\\\\quad F_\\\\text{K0}=\\\\frac{s_b-s_{K0}}{s_b-s_a}.$$\\n\",\n    \"\\n\",\n    \"**Full-run result (13,030 samples).**\\n\",\n    \"- **Gate:** only 5 of the 12 tasks pass the gate, i.e. the ban moves the model.\\n\",\n    \"- **C2a disconfirmed:** the claim \\\"the prompt route carries >= 2/3 of the ban\\\" fails. Pooled F_prompt = 0.61 and F_direct = 0.74.\\n\",\n    \"- **Task-dependent mechanism:**\\n\",\n    \"  - T03/T10: either route alone suffices.\\n\",\n    \"  - T05/T06: the ban works through the direct route.\\n\",\n    \"  - T13: both routes are needed.\\n\",\n    \"\\n\",\n    \"### What this notebook runs (CPU, a few minutes)\\n\",\n    \"1. **The S9 analysis code** (`src/analysis/analysis.py`) on a curated subset: 100 CRN slots of the `route_arms` dataset, i.e. 500 labelled programs by Qwen3-8B. It covers the gate, shares and route fractions, with a hierarchical bootstrap, BCa and leave-one-task-out jackknife intervals. It also runs leave-one-template-out, a Bayesian mixed GLM, the C2a verdict, CRN flip tables and first divergence, landings and C2c.\\n\",\n    \"2. **The original HF engine** (`src/engine.py`) on one CRN slot set, with a small Qwen3 model on CPU. This is the same prefill / KV-splice / span-drop / CRN-sampling code that ran Qwen3-8B on an L4 GPU. It uses the frozen prompt ids and the exact uniforms of the real run, and shows the Qwen3-8B rows of those slots beside its own output.\\n\",\n    \"\\n\",\n    \"Some stages are not re-run: the Qwen3-8B GPU queue (about 1.8 GPU-hours), the frozen labellers (bench harness + LLM judge) and the stages that need the upstream bench folders. Their outputs come in as the labelled `route_arms` data.\\n\",\n    \"\\n\",\n    \"### `method.py` stages and where they appear here\\n\",\n    \"| `uv run method.py <stage>` | what it does | in this notebook |\\n\",\n    \"|---|---|---|\\n\",\n    \"| `s0`, `recheck`, `s1`, `s2`, `tests` | input snapshot + bench sha256, labeller re-check, prompts with alignment asserts, frozen forecasts (n-grams, veto classes), CPU tests | not run; their frozen outputs (prompt ids, n-grams, veto classes, catalogues) ship in the data |\\n\",\n    \"| `gpu` + `label` | GPU queue: CRN-coupled sampling of every arm with Qwen3-8B, plus the streaming labeller | section 5 runs the engine on one slot set with a small model; the labels ship in the data |\\n\",\n    \"| `close1` | hash-chain commit of the analysis code before any ban sample | not applicable |\\n\",\n    \"| `analysis` | S9 analysis | sections 2-4, on the subset |\\n\",\n    \"| `figures`, `outputs`, `audit` | figures, `method_out.json`, independent re-derivation | section 6 (visualisation, demo vs. full run) |\"\n   ]\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"fc03631f\",\n   \"source\": \"import subprocess, sys\\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\\n\\n# loguru -- NOT pre-installed on Colab, always install\\n_pip('loguru==0.7.3')\\n\\n# numpy, pandas, scipy, statsmodels, matplotlib, torch, transformers -- pre-installed on Colab, install locally only\\n# (torch: Colab's CPU build, from the PyTorch CPU index, so a local run does not pull the CUDA wheels)\\nif 'google.colab' not in sys.modules:\\n    _pip('--index-url', 'https://download.pytorch.org/whl/cpu', 'torch==2.9.0+cpu')\\n    _pip('numpy==2.0.2', 'pandas==2.2.2', 'scipy==1.16.3', 'statsmodels==0.14.6', 'matplotlib==3.10.0',\\n         'transformers==5.0.0', 'tokenizers==0.22.2', 'huggingface_hub==1.4.0')\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"bc3a2b51\",\n   \"source\": \"# original imports of the code used below (src/cfg.py, src/engine.py, src/gpu.py, src/analysis/analysis.py)\\nimport collections\\nimport contextlib\\nimport gc\\nimport hashlib\\nimport json\\nimport math\\nimport os\\nimport re\\nimport sys\\nimport time\\nfrom pathlib import Path\\nfrom typing import Any, Callable, Iterable, Iterator\\n\\nimport numpy as np\\nimport torch\\nfrom loguru import logger\\nfrom scipy import stats\\n\\n# notebook additions: tables and figures\\nimport matplotlib.pyplot as plt\\nimport pandas as pd\\n\\npd.set_option(\\\"display.width\\\", 200)\\npd.set_option(\\\"display.max_columns\\\", 30)\\nprint(\\\"torch\\\", torch.__version__, \\\"| numpy\\\", np.__version__, \\\"| cuda available:\\\", torch.cuda.is_available())\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"4c26f4ad\",\n   \"source\": \"GITHUB_DATA_URL = \\\"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-3/experiment-16/demo/mini_demo_data.json\\\"\\nimport http.client\\nimport json\\nimport urllib.request\\nfrom pathlib import Path\\n\\ndef load_data():\\n    try:\\n        with urllib.request.urlopen(GITHUB_DATA_URL, timeout=15) as response:\\n            return json.loads(response.read().decode())\\n    # Network errors, timeouts, a placeholder URL, bad JSON, a cut-off response.\\n    except (OSError, ValueError, http.client.HTTPException) as e:\\n        print(\\\"GitHub data unavailable, using local mini_demo_data.json:\\\", e)\\n    local = Path(\\\"mini_demo_data.json\\\")\\n    if local.exists(): return json.loads(local.read_text())\\n    raise FileNotFoundError(\\\"Could not load mini_demo_data.json\\\")\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"14389e18\",\n   \"source\": \"data = load_data()\\nmeta = data[\\\"metadata\\\"]\\nexamples = data[\\\"datasets\\\"][0][\\\"examples\\\"]  # the route_arms dataset: one example per CRN slot (task, template, k)\\nprint(meta[\\\"description\\\"])\\nprint(\\\"source:   \\\", meta[\\\"source\\\"])\\nprint(\\\"selection:\\\", meta[\\\"selection_rule\\\"])\\nprint(f\\\"{len(examples)} CRN slots | full-run model: {meta['model']} ({meta['dtype']}) | {meta['decoding']}\\\")\\nprint(\\\"example:\\\", {k: v for k, v in examples[0].items() if k != \\\"metadata_token_ids\\\"})\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"4e32fa9b\",\n   \"source\": \"## Config\\n\\nEvery tunable parameter is set here, and each comment gives the original value.\\n\\n- **Resampling counts:** the bootstrap, permutation and resampling-null counts can go straight back to the original values. They cost seconds at this data size.\\n- **`N_SLOTS`:** must match the demo data, which has 3 CRN slots per template on the gated tasks. The full run has 20.\\n- **Engine model:** the engine cell runs a small Qwen3 model. It shares Qwen3-8B's tokenizer, so the frozen prompt ids and the CRN uniforms of the real run apply unchanged. Set `ENGINE_MODEL_ID = \\\"Qwen/Qwen3-8B\\\"` (with `ENGINE_REVISION` = the original revision, `ENGINE_DTYPE = torch.bfloat16` and a GPU with more than 17 GB) to run the original model.\\n\\nFunctions take some of these values as defaults when they are defined. After editing this cell, re-run the notebook from here.\",\n   \"metadata\": {}\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}", "updated_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"title\",\n   \"metadata\": {},\n   \"source\": [\n    \"# Where a coding ban takes effect in Qwen3-8B: route-test demo\\n\",\n    \"\\n\",\n    \"**Artifact:** experiment-16 (`art__5akZ9W9iZM4`) of *Prompt bans substitute, not just subtract*.\\n\",\n    \"\\n\",\n    \"A prompt ban such as *\\\"Do not use a hash set of seen values for this task.\\\"* makes Qwen3-8B (bf16, thinking off) write a different algorithm. This experiment asks **which internal route carries that effect**, on the 12 frozen coding tasks of the bench. Every arm of a CRN slot `(task, template, k)` is sampled with the same **common random numbers** (CRN): one fixed stream of uniforms, turned into tokens by inverse-CDF sampling. The arms are built by **splicing KV caches** by position, so they differ only in the cache their generated tokens read:\\n\",\n    \"\\n\",\n    \"| arm | cache read by the generated tokens | what it tests |\\n\",\n    \"|---|---|---|\\n\",\n    \"| `a` | full ban prompt | clean endpoint |\\n\",\n    \"| `b` | token-length-matched neutral twin (*\\\"Do not use fire for this task. . .\\\"*) | corrupted endpoint |\\n\",\n    \"| `c` | twin condition segment + ban task-spec states | **prompt route**: do the later prompt states alone carry the ban? |\\n\",\n    \"| `d` | ban condition segment + twin task-spec states | **direct route**: is generated tokens reading the ban itself enough? |\\n\",\n    \"| `K0` | full ban, but the condition span is invisible to every generated token | removal of the direct route |\\n\",\n    \"\\n\",\n    \"Each generated program is labelled with its mechanism: runtime trace first, AST second, and a blind LLM judge on disagreement. For a task with default mechanism D, `s_X` is the share of arm X's attempts labelled D. The route fractions are\\n\",\n    \"\\n\",\n    \"$$F_\\\\text{prompt}=\\\\frac{s_b-s_c}{s_b-s_a},\\\\quad F_\\\\text{direct}=\\\\frac{s_b-s_d}{s_b-s_a},\\\\quad I=1-F_\\\\text{prompt}-F_\\\\text{direct},\\\\quad F_\\\\text{K0}=\\\\frac{s_b-s_{K0}}{s_b-s_a}.$$\\n\",\n    \"\\n\",\n    \"**Full-run result (13,030 samples).**\\n\",\n    \"- **Gate:** only 5 of the 12 tasks pass the gate, i.e. the ban moves the model.\\n\",\n    \"- **C2a disconfirmed:** the claim \\\"the prompt route carries >= 2/3 of the ban\\\" fails. Pooled F_prompt = 0.61 and F_direct = 0.74.\\n\",\n    \"- **Task-dependent mechanism:**\\n\",\n    \"  - T03/T10: either route alone suffices.\\n\",\n    \"  - T05/T06: the ban works through the direct route.\\n\",\n    \"  - T13: both routes are needed.\\n\",\n    \"\\n\",\n    \"### What this notebook runs (CPU, a few minutes)\\n\",\n    \"1. **The S9 analysis code** (`src/analysis/analysis.py`) on a curated subset: 100 CRN slots of the `route_arms` dataset, i.e. 500 labelled programs by Qwen3-8B. It covers the gate, shares and route fractions, with a hierarchical bootstrap, BCa and leave-one-task-out jackknife intervals. It also runs leave-one-template-out, a Bayesian mixed GLM, the C2a verdict, CRN flip tables and first divergence, landings and C2c.\\n\",\n    \"2. **The original HF engine** (`src/engine.py`) on one CRN slot set, with a small Qwen3 model on CPU. This is the same prefill / KV-splice / span-drop / CRN-sampling code that ran Qwen3-8B on an L4 GPU. It uses the frozen prompt ids and the exact uniforms of the real run, and shows the Qwen3-8B rows of those slots beside its own output.\\n\",\n    \"\\n\",\n    \"Some stages are not re-run: the Qwen3-8B GPU queue (about 1.8 GPU-hours), the frozen labellers (bench harness + LLM judge) and the stages that need the upstream bench folders. Their outputs come in as the labelled `route_arms` data.\\n\",\n    \"\\n\",\n    \"### `method.py` stages and where they appear here\\n\",\n    \"| `uv run method.py <stage>` | what it does | in this notebook |\\n\",\n    \"|---|---|---|\\n\",\n    \"| `s0`, `recheck`, `s1`, `s2`, `tests` | input snapshot + bench sha256, labeller re-check, prompts with alignment asserts, frozen forecasts (n-grams, veto classes), CPU tests | not run; their frozen outputs (prompt ids, n-grams, veto classes, catalogues) ship in the data |\\n\",\n    \"| `gpu` + `label` | GPU queue: CRN-coupled sampling of every arm with Qwen3-8B, plus the streaming labeller | section 5 runs the engine on one slot set with a small model; the labels ship in the data |\\n\",\n    \"| `close1` | hash-chain commit of the analysis code before any ban sample | not applicable |\\n\",\n    \"| `analysis` | S9 analysis | sections 2-4, on the subset |\\n\",\n    \"| `figures`, `outputs`, `audit` | figures, `method_out.json`, independent re-derivation | section 6 (visualisation, demo vs. full run) |\"\n   ]\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"fc03631f\",\n   \"source\": \"import subprocess, sys\\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\\n\\n# loguru -- NOT pre-installed on Colab, always install\\n_pip('loguru==0.7.3')\\n\\n# numpy, pandas, scipy, statsmodels, matplotlib, torch, transformers -- pre-installed on Colab, install locally only\\n# (torch: Colab's CPU build, from the PyTorch CPU index, so a local run does not pull the CUDA wheels)\\nif 'google.colab' not in sys.modules:\\n    _pip('--index-url', 'https://download.pytorch.org/whl/cpu', 'torch==2.9.0+cpu')\\n    _pip('numpy==2.0.2', 'pandas==2.2.2', 'scipy==1.16.3', 'statsmodels==0.14.6', 'matplotlib==3.10.0',\\n         'transformers==5.0.0', 'tokenizers==0.22.2', 'huggingface_hub==1.4.0')\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"bc3a2b51\",\n   \"source\": \"# original imports of the code used below (src/cfg.py, src/engine.py, src/gpu.py, src/analysis/analysis.py)\\nimport collections\\nimport contextlib\\nimport gc\\nimport hashlib\\nimport json\\nimport math\\nimport os\\nimport re\\nimport sys\\nimport time\\nfrom pathlib import Path\\nfrom typing import Any, Callable, Iterable, Iterator\\n\\nimport numpy as np\\nimport torch\\nfrom loguru import logger\\nfrom scipy import stats\\n\\n# notebook additions: tables and figures\\nimport matplotlib.pyplot as plt\\nimport pandas as pd\\n\\npd.set_option(\\\"display.width\\\", 200)\\npd.set_option(\\\"display.max_columns\\\", 30)\\nprint(\\\"torch\\\", torch.__version__, \\\"| numpy\\\", np.__version__, \\\"| cuda available:\\\", torch.cuda.is_available())\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"4c26f4ad\",\n   \"source\": \"GITHUB_DATA_URL = \\\"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-3/experiment-16/demo/mini_demo_data.json\\\"\\nimport http.client\\nimport json\\nimport urllib.request\\nfrom pathlib import Path\\n\\ndef load_data():\\n    try:\\n        with urllib.request.urlopen(GITHUB_DATA_URL, timeout=15) as response:\\n            return json.loads(response.read().decode())\\n    # Network errors, timeouts, a placeholder URL, bad JSON, a cut-off response.\\n    except (OSError, ValueError, http.client.HTTPException) as e:\\n        print(\\\"GitHub data unavailable, using local mini_demo_data.json:\\\", e)\\n    local = Path(\\\"mini_demo_data.json\\\")\\n    if local.exists(): return json.loads(local.read_text())\\n    raise FileNotFoundError(\\\"Could not load mini_demo_data.json\\\")\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"14389e18\",\n   \"source\": \"data = load_data()\\nmeta = data[\\\"metadata\\\"]\\nexamples = data[\\\"datasets\\\"][0][\\\"examples\\\"]  # the route_arms dataset: one example per CRN slot (task, template, k)\\nprint(meta[\\\"description\\\"])\\nprint(\\\"source:   \\\", meta[\\\"source\\\"])\\nprint(\\\"selection:\\\", meta[\\\"selection_rule\\\"])\\nprint(f\\\"{len(examples)} CRN slots | full-run model: {meta['model']} ({meta['dtype']}) | {meta['decoding']}\\\")\\nprint(\\\"example:\\\", {k: v for k, v in examples[0].items() if k != \\\"metadata_token_ids\\\"})\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"352080db\",\n   \"source\": \"PLACEHOLDER\",\n   \"metadata\": {}\n  },\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"4e32fa9b\",\n   \"source\": \"## Config\\n\\nEvery tunable parameter is set here, and each comment gives the original value.\\n\\n- **Resampling counts:** the bootstrap, permutation and resampling-null counts can go straight back to the original values. They cost seconds at this data size.\\n- **`N_SLOTS`:** must match the demo data, which has 3 CRN slots per template on the gated tasks. The full run has 20.\\n- **Engine model:** the engine cell runs a small Qwen3 model. It shares Qwen3-8B's tokenizer, so the frozen prompt ids and the CRN uniforms of the real run apply unchanged. Set `ENGINE_MODEL_ID = \\\"Qwen/Qwen3-8B\\\"` (with `ENGINE_REVISION` = the original revision, `ENGINE_DTYPE = torch.bfloat16` and a GPU with more than 17 GB) to run the original model.\\n\\nFunctions take some of these values as defaults when they are defined. After editing this cell, re-run the notebook from here.\",\n   \"metadata\": {}\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}"}
```

### [106] ASSISTANT · 2026-10-26 10:33:03 UTC

```
I accidentally sent a stray placeholder insert alongside the config markdown. Deleting it:
```

### [107] TOOL CALL — NotebookEdit · 2026-10-26 10:33:03 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': '352080db', 'edit_mode': 'delete', 'new_source': ''}
```

### [108] TOOL RESULT — NotebookEdit · 2026-10-26 10:33:03 UTC

```
{"new_source": "", "old_source": "PLACEHOLDER", "cell_type": "code", "language": "python", "edit_mode": "delete", "cell_id": "352080db", "error": "", "notebook_path": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb", "original_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"title\",\n   \"metadata\": {},\n   \"source\": [\n    \"# Where a coding ban takes effect in Qwen3-8B: route-test demo\\n\",\n    \"\\n\",\n    \"**Artifact:** experiment-16 (`art__5akZ9W9iZM4`) of *Prompt bans substitute, not just subtract*.\\n\",\n    \"\\n\",\n    \"A prompt ban such as *\\\"Do not use a hash set of seen values for this task.\\\"* makes Qwen3-8B (bf16, thinking off) write a different algorithm. This experiment asks **which internal route carries that effect**, on the 12 frozen coding tasks of the bench. Every arm of a CRN slot `(task, template, k)` is sampled with the same **common random numbers** (CRN): one fixed stream of uniforms, turned into tokens by inverse-CDF sampling. The arms are built by **splicing KV caches** by position, so they differ only in the cache their generated tokens read:\\n\",\n    \"\\n\",\n    \"| arm | cache read by the generated tokens | what it tests |\\n\",\n    \"|---|---|---|\\n\",\n    \"| `a` | full ban prompt | clean endpoint |\\n\",\n    \"| `b` | token-length-matched neutral twin (*\\\"Do not use fire for this task. . .\\\"*) | corrupted endpoint |\\n\",\n    \"| `c` | twin condition segment + ban task-spec states | **prompt route**: do the later prompt states alone carry the ban? |\\n\",\n    \"| `d` | ban condition segment + twin task-spec states | **direct route**: is generated tokens reading the ban itself enough? |\\n\",\n    \"| `K0` | full ban, but the condition span is invisible to every generated token | removal of the direct route |\\n\",\n    \"\\n\",\n    \"Each generated program is labelled with its mechanism: runtime trace first, AST second, and a blind LLM judge on disagreement. For a task with default mechanism D, `s_X` is the share of arm X's attempts labelled D. The route fractions are\\n\",\n    \"\\n\",\n    \"$$F_\\\\text{prompt}=\\\\frac{s_b-s_c}{s_b-s_a},\\\\quad F_\\\\text{direct}=\\\\frac{s_b-s_d}{s_b-s_a},\\\\quad I=1-F_\\\\text{prompt}-F_\\\\text{direct},\\\\quad F_\\\\text{K0}=\\\\frac{s_b-s_{K0}}{s_b-s_a}.$$\\n\",\n    \"\\n\",\n    \"**Full-run result (13,030 samples).**\\n\",\n    \"- **Gate:** only 5 of the 12 tasks pass the gate, i.e. the ban moves the model.\\n\",\n    \"- **C2a disconfirmed:** the claim \\\"the prompt route carries >= 2/3 of the ban\\\" fails. Pooled F_prompt = 0.61 and F_direct = 0.74.\\n\",\n    \"- **Task-dependent mechanism:**\\n\",\n    \"  - T03/T10: either route alone suffices.\\n\",\n    \"  - T05/T06: the ban works through the direct route.\\n\",\n    \"  - T13: both routes are needed.\\n\",\n    \"\\n\",\n    \"### What this notebook runs (CPU, a few minutes)\\n\",\n    \"1. **The S9 analysis code** (`src/analysis/analysis.py`) on a curated subset: 100 CRN slots of the `route_arms` dataset, i.e. 500 labelled programs by Qwen3-8B. It covers the gate, shares and route fractions, with a hierarchical bootstrap, BCa and leave-one-task-out jackknife intervals. It also runs leave-one-template-out, a Bayesian mixed GLM, the C2a verdict, CRN flip tables and first divergence, landings and C2c.\\n\",\n    \"2. **The original HF engine** (`src/engine.py`) on one CRN slot set, with a small Qwen3 model on CPU. This is the same prefill / KV-splice / span-drop / CRN-sampling code that ran Qwen3-8B on an L4 GPU. It uses the frozen prompt ids and the exact uniforms of the real run, and shows the Qwen3-8B rows of those slots beside its own output.\\n\",\n    \"\\n\",\n    \"Some stages are not re-run: the Qwen3-8B GPU queue (about 1.8 GPU-hours), the frozen labellers (bench harness + LLM judge) and the stages that need the upstream bench folders. Their outputs come in as the labelled `route_arms` data.\\n\",\n    \"\\n\",\n    \"### `method.py` stages and where they appear here\\n\",\n    \"| `uv run method.py <stage>` | what it does | in this notebook |\\n\",\n    \"|---|---|---|\\n\",\n    \"| `s0`, `recheck`, `s1`, `s2`, `tests` | input snapshot + bench sha256, labeller re-check, prompts with alignment asserts, frozen forecasts (n-grams, veto classes), CPU tests | not run; their frozen outputs (prompt ids, n-grams, veto classes, catalogues) ship in the data |\\n\",\n    \"| `gpu` + `label` | GPU queue: CRN-coupled sampling of every arm with Qwen3-8B, plus the streaming labeller | section 5 runs the engine on one slot set with a small model; the labels ship in the data |\\n\",\n    \"| `close1` | hash-chain commit of the analysis code before any ban sample | not applicable |\\n\",\n    \"| `analysis` | S9 analysis | sections 2-4, on the subset |\\n\",\n    \"| `figures`, `outputs`, `audit` | figures, `method_out.json`, independent re-derivation | section 6 (visualisation, demo vs. full run) |\"\n   ]\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"fc03631f\",\n   \"source\": \"import subprocess, sys\\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\\n\\n# loguru -- NOT pre-installed on Colab, always install\\n_pip('loguru==0.7.3')\\n\\n# numpy, pandas, scipy, statsmodels, matplotlib, torch, transformers -- pre-installed on Colab, install locally only\\n# (torch: Colab's CPU build, from the PyTorch CPU index, so a local run does not pull the CUDA wheels)\\nif 'google.colab' not in sys.modules:\\n    _pip('--index-url', 'https://download.pytorch.org/whl/cpu', 'torch==2.9.0+cpu')\\n    _pip('numpy==2.0.2', 'pandas==2.2.2', 'scipy==1.16.3', 'statsmodels==0.14.6', 'matplotlib==3.10.0',\\n         'transformers==5.0.0', 'tokenizers==0.22.2', 'huggingface_hub==1.4.0')\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"bc3a2b51\",\n   \"source\": \"# original imports of the code used below (src/cfg.py, src/engine.py, src/gpu.py, src/analysis/analysis.py)\\nimport collections\\nimport contextlib\\nimport gc\\nimport hashlib\\nimport json\\nimport math\\nimport os\\nimport re\\nimport sys\\nimport time\\nfrom pathlib import Path\\nfrom typing import Any, Callable, Iterable, Iterator\\n\\nimport numpy as np\\nimport torch\\nfrom loguru import logger\\nfrom scipy import stats\\n\\n# notebook additions: tables and figures\\nimport matplotlib.pyplot as plt\\nimport pandas as pd\\n\\npd.set_option(\\\"display.width\\\", 200)\\npd.set_option(\\\"display.max_columns\\\", 30)\\nprint(\\\"torch\\\", torch.__version__, \\\"| numpy\\\", np.__version__, \\\"| cuda available:\\\", torch.cuda.is_available())\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"4c26f4ad\",\n   \"source\": \"GITHUB_DATA_URL = \\\"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-3/experiment-16/demo/mini_demo_data.json\\\"\\nimport http.client\\nimport json\\nimport urllib.request\\nfrom pathlib import Path\\n\\ndef load_data():\\n    try:\\n        with urllib.request.urlopen(GITHUB_DATA_URL, timeout=15) as response:\\n            return json.loads(response.read().decode())\\n    # Network errors, timeouts, a placeholder URL, bad JSON, a cut-off response.\\n    except (OSError, ValueError, http.client.HTTPException) as e:\\n        print(\\\"GitHub data unavailable, using local mini_demo_data.json:\\\", e)\\n    local = Path(\\\"mini_demo_data.json\\\")\\n    if local.exists(): return json.loads(local.read_text())\\n    raise FileNotFoundError(\\\"Could not load mini_demo_data.json\\\")\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"14389e18\",\n   \"source\": \"data = load_data()\\nmeta = data[\\\"metadata\\\"]\\nexamples = data[\\\"datasets\\\"][0][\\\"examples\\\"]  # the route_arms dataset: one example per CRN slot (task, template, k)\\nprint(meta[\\\"description\\\"])\\nprint(\\\"source:   \\\", meta[\\\"source\\\"])\\nprint(\\\"selection:\\\", meta[\\\"selection_rule\\\"])\\nprint(f\\\"{len(examples)} CRN slots | full-run model: {meta['model']} ({meta['dtype']}) | {meta['decoding']}\\\")\\nprint(\\\"example:\\\", {k: v for k, v in examples[0].items() if k != \\\"metadata_token_ids\\\"})\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"352080db\",\n   \"source\": \"PLACEHOLDER\",\n   \"metadata\": {}\n  },\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"4e32fa9b\",\n   \"source\": \"## Config\\n\\nEvery tunable parameter is set here, and each comment gives the original value.\\n\\n- **Resampling counts:** the bootstrap, permutation and resampling-null counts can go straight back to the original values. They cost seconds at this data size.\\n- **`N_SLOTS`:** must match the demo data, which has 3 CRN slots per template on the gated tasks. The full run has 20.\\n- **Engine model:** the engine cell runs a small Qwen3 model. It shares Qwen3-8B's tokenizer, so the frozen prompt ids and the CRN uniforms of the real run apply unchanged. Set `ENGINE_MODEL_ID = \\\"Qwen/Qwen3-8B\\\"` (with `ENGINE_REVISION` = the original revision, `ENGINE_DTYPE = torch.bfloat16` and a GPU with more than 17 GB) to run the original model.\\n\\nFunctions take some of these values as defaults when they are defined. After editing this cell, re-run the notebook from here.\",\n   \"metadata\": {}\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}", "updated_file": "{\n \"cells\": [\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"title\",\n   \"metadata\": {},\n   \"source\": [\n    \"# Where a coding ban takes effect in Qwen3-8B: route-test demo\\n\",\n    \"\\n\",\n    \"**Artifact:** experiment-16 (`art__5akZ9W9iZM4`) of *Prompt bans substitute, not just subtract*.\\n\",\n    \"\\n\",\n    \"A prompt ban such as *\\\"Do not use a hash set of seen values for this task.\\\"* makes Qwen3-8B (bf16, thinking off) write a different algorithm. This experiment asks **which internal route carries that effect**, on the 12 frozen coding tasks of the bench. Every arm of a CRN slot `(task, template, k)` is sampled with the same **common random numbers** (CRN): one fixed stream of uniforms, turned into tokens by inverse-CDF sampling. The arms are built by **splicing KV caches** by position, so they differ only in the cache their generated tokens read:\\n\",\n    \"\\n\",\n    \"| arm | cache read by the generated tokens | what it tests |\\n\",\n    \"|---|---|---|\\n\",\n    \"| `a` | full ban prompt | clean endpoint |\\n\",\n    \"| `b` | token-length-matched neutral twin (*\\\"Do not use fire for this task. . .\\\"*) | corrupted endpoint |\\n\",\n    \"| `c` | twin condition segment + ban task-spec states | **prompt route**: do the later prompt states alone carry the ban? |\\n\",\n    \"| `d` | ban condition segment + twin task-spec states | **direct route**: is generated tokens reading the ban itself enough? |\\n\",\n    \"| `K0` | full ban, but the condition span is invisible to every generated token | removal of the direct route |\\n\",\n    \"\\n\",\n    \"Each generated program is labelled with its mechanism: runtime trace first, AST second, and a blind LLM judge on disagreement. For a task with default mechanism D, `s_X` is the share of arm X's attempts labelled D. The route fractions are\\n\",\n    \"\\n\",\n    \"$$F_\\\\text{prompt}=\\\\frac{s_b-s_c}{s_b-s_a},\\\\quad F_\\\\text{direct}=\\\\frac{s_b-s_d}{s_b-s_a},\\\\quad I=1-F_\\\\text{prompt}-F_\\\\text{direct},\\\\quad F_\\\\text{K0}=\\\\frac{s_b-s_{K0}}{s_b-s_a}.$$\\n\",\n    \"\\n\",\n    \"**Full-run result (13,030 samples).**\\n\",\n    \"- **Gate:** only 5 of the 12 tasks pass the gate, i.e. the ban moves the model.\\n\",\n    \"- **C2a disconfirmed:** the claim \\\"the prompt route carries >= 2/3 of the ban\\\" fails. Pooled F_prompt = 0.61 and F_direct = 0.74.\\n\",\n    \"- **Task-dependent mechanism:**\\n\",\n    \"  - T03/T10: either route alone suffices.\\n\",\n    \"  - T05/T06: the ban works through the direct route.\\n\",\n    \"  - T13: both routes are needed.\\n\",\n    \"\\n\",\n    \"### What this notebook runs (CPU, a few minutes)\\n\",\n    \"1. **The S9 analysis code** (`src/analysis/analysis.py`) on a curated subset: 100 CRN slots of the `route_arms` dataset, i.e. 500 labelled programs by Qwen3-8B. It covers the gate, shares and route fractions, with a hierarchical bootstrap, BCa and leave-one-task-out jackknife intervals. It also runs leave-one-template-out, a Bayesian mixed GLM, the C2a verdict, CRN flip tables and first divergence, landings and C2c.\\n\",\n    \"2. **The original HF engine** (`src/engine.py`) on one CRN slot set, with a small Qwen3 model on CPU. This is the same prefill / KV-splice / span-drop / CRN-sampling code that ran Qwen3-8B on an L4 GPU. It uses the frozen prompt ids and the exact uniforms of the real run, and shows the Qwen3-8B rows of those slots beside its own output.\\n\",\n    \"\\n\",\n    \"Some stages are not re-run: the Qwen3-8B GPU queue (about 1.8 GPU-hours), the frozen labellers (bench harness + LLM judge) and the stages that need the upstream bench folders. Their outputs come in as the labelled `route_arms` data.\\n\",\n    \"\\n\",\n    \"### `method.py` stages and where they appear here\\n\",\n    \"| `uv run method.py <stage>` | what it does | in this notebook |\\n\",\n    \"|---|---|---|\\n\",\n    \"| `s0`, `recheck`, `s1`, `s2`, `tests` | input snapshot + bench sha256, labeller re-check, prompts with alignment asserts, frozen forecasts (n-grams, veto classes), CPU tests | not run; their frozen outputs (prompt ids, n-grams, veto classes, catalogues) ship in the data |\\n\",\n    \"| `gpu` + `label` | GPU queue: CRN-coupled sampling of every arm with Qwen3-8B, plus the streaming labeller | section 5 runs the engine on one slot set with a small model; the labels ship in the data |\\n\",\n    \"| `close1` | hash-chain commit of the analysis code before any ban sample | not applicable |\\n\",\n    \"| `analysis` | S9 analysis | sections 2-4, on the subset |\\n\",\n    \"| `figures`, `outputs`, `audit` | figures, `method_out.json`, independent re-derivation | section 6 (visualisation, demo vs. full run) |\"\n   ]\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"fc03631f\",\n   \"source\": \"import subprocess, sys\\ndef _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])\\n\\n# loguru -- NOT pre-installed on Colab, always install\\n_pip('loguru==0.7.3')\\n\\n# numpy, pandas, scipy, statsmodels, matplotlib, torch, transformers -- pre-installed on Colab, install locally only\\n# (torch: Colab's CPU build, from the PyTorch CPU index, so a local run does not pull the CUDA wheels)\\nif 'google.colab' not in sys.modules:\\n    _pip('--index-url', 'https://download.pytorch.org/whl/cpu', 'torch==2.9.0+cpu')\\n    _pip('numpy==2.0.2', 'pandas==2.2.2', 'scipy==1.16.3', 'statsmodels==0.14.6', 'matplotlib==3.10.0',\\n         'transformers==5.0.0', 'tokenizers==0.22.2', 'huggingface_hub==1.4.0')\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"bc3a2b51\",\n   \"source\": \"# original imports of the code used below (src/cfg.py, src/engine.py, src/gpu.py, src/analysis/analysis.py)\\nimport collections\\nimport contextlib\\nimport gc\\nimport hashlib\\nimport json\\nimport math\\nimport os\\nimport re\\nimport sys\\nimport time\\nfrom pathlib import Path\\nfrom typing import Any, Callable, Iterable, Iterator\\n\\nimport numpy as np\\nimport torch\\nfrom loguru import logger\\nfrom scipy import stats\\n\\n# notebook additions: tables and figures\\nimport matplotlib.pyplot as plt\\nimport pandas as pd\\n\\npd.set_option(\\\"display.width\\\", 200)\\npd.set_option(\\\"display.max_columns\\\", 30)\\nprint(\\\"torch\\\", torch.__version__, \\\"| numpy\\\", np.__version__, \\\"| cuda available:\\\", torch.cuda.is_available())\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"4c26f4ad\",\n   \"source\": \"GITHUB_DATA_URL = \\\"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-3/experiment-16/demo/mini_demo_data.json\\\"\\nimport http.client\\nimport json\\nimport urllib.request\\nfrom pathlib import Path\\n\\ndef load_data():\\n    try:\\n        with urllib.request.urlopen(GITHUB_DATA_URL, timeout=15) as response:\\n            return json.loads(response.read().decode())\\n    # Network errors, timeouts, a placeholder URL, bad JSON, a cut-off response.\\n    except (OSError, ValueError, http.client.HTTPException) as e:\\n        print(\\\"GitHub data unavailable, using local mini_demo_data.json:\\\", e)\\n    local = Path(\\\"mini_demo_data.json\\\")\\n    if local.exists(): return json.loads(local.read_text())\\n    raise FileNotFoundError(\\\"Could not load mini_demo_data.json\\\")\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"code\",\n   \"id\": \"14389e18\",\n   \"source\": \"data = load_data()\\nmeta = data[\\\"metadata\\\"]\\nexamples = data[\\\"datasets\\\"][0][\\\"examples\\\"]  # the route_arms dataset: one example per CRN slot (task, template, k)\\nprint(meta[\\\"description\\\"])\\nprint(\\\"source:   \\\", meta[\\\"source\\\"])\\nprint(\\\"selection:\\\", meta[\\\"selection_rule\\\"])\\nprint(f\\\"{len(examples)} CRN slots | full-run model: {meta['model']} ({meta['dtype']}) | {meta['decoding']}\\\")\\nprint(\\\"example:\\\", {k: v for k, v in examples[0].items() if k != \\\"metadata_token_ids\\\"})\",\n   \"metadata\": {},\n   \"execution_count\": null,\n   \"outputs\": []\n  },\n  {\n   \"cell_type\": \"markdown\",\n   \"id\": \"4e32fa9b\",\n   \"source\": \"## Config\\n\\nEvery tunable parameter is set here, and each comment gives the original value.\\n\\n- **Resampling counts:** the bootstrap, permutation and resampling-null counts can go straight back to the original values. They cost seconds at this data size.\\n- **`N_SLOTS`:** must match the demo data, which has 3 CRN slots per template on the gated tasks. The full run has 20.\\n- **Engine model:** the engine cell runs a small Qwen3 model. It shares Qwen3-8B's tokenizer, so the frozen prompt ids and the CRN uniforms of the real run apply unchanged. Set `ENGINE_MODEL_ID = \\\"Qwen/Qwen3-8B\\\"` (with `ENGINE_REVISION` = the original revision, `ENGINE_DTYPE = torch.bfloat16` and a GPU with more than 17 GB) to run the original model.\\n\\nFunctions take some of these values as defaults when they are defined. After editing this cell, re-run the notebook from here.\",\n   \"metadata\": {}\n  }\n ],\n \"metadata\": {\n  \"kernelspec\": {\n   \"display_name\": \"Python 3\",\n   \"language\": \"python\",\n   \"name\": \"python3\"\n  },\n  \"language_info\": {\n   \"name\": \"python\",\n   \"version\": \"3.12\"\n  }\n },\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}"}
```

### [109] TOOL CALL — NotebookEdit · 2026-10-26 10:33:13 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': '4e32fa9b', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '# ------------------------------------------------------------------ analysis (src/analysis/analysis.py, src/cfg.py)\nN_SLOTS = 3            # CRN slots k per template in the demo data (original: 20 = cfg.N_PER_TEMPLATE)\nN_BOOT = 100           # hierarchical task -> template -> slot bootstrap reps, pooled F (original: 10000 = cfg.N_BOOT)\nN_BOOT_TASK = 100      # template -> slot bootstrap reps per task (original: 4000, per_task_route default)\nN_PERM = 100           # permutations of the one-sided C2c Spearman test (original: 100000 = cfg.N_PERM)\nN_BOOT_RHO = 100       # task bootstrap reps of the C2c rho interval (original: 4000)\nLANDING_N_REP = 20     # resamples of the landing JS null (original: 2000, landing_null default)\nRNG_SEED = 20261020    # cfg.RNG_SEED (unchanged)\n\n# ------------------------------------------------------------------ engine (src/engine.py, src/gpu.py)\nRUN_ENGINE = True                      # False skips the model download and the live CRN slots (section 5)\nENGINE_MODEL_ID = "Qwen/Qwen3-0.6B"    # original: "Qwen/Qwen3-8B" (cfg.MODEL_ID); same tokenizer and chat template\nENGINE_REVISION = "c1899de289a04d12100db370d81485cdf75e47ca"  # pinned; original: "b968826d9c46dd6066d109eabc6255188de91218"\nENGINE_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"  # original: one NVIDIA L4 (23 GB)\nENGINE_DTYPE = torch.float32           # original: torch.bfloat16\nENGINE_MAX_NEW = 8                     # max new tokens per row; a row also stops once its first code fence closes (original: 1024)\nENGINE_N_SLOTS = 1                     # CRN slots k of the engine slot set to sample, of the k = 0, 1, 2 in the data (original: 20 per template)'}
```

### [110] TOOL RESULT — NotebookEdit · 2026-10-26 10:33:13 UTC

```
{"new_source": "# ------------------------------------------------------------------ analysis (src/analysis/analysis.py, src/cfg.py)\nN_SLOTS = 3            # CRN slots k per template in the demo data (original: 20 = cfg.N_PER_TEMPLATE)\nN_BOOT = 100           # hierarchical task -> template -> slot bootstrap reps, pooled F (original: 10000 = cfg.N_BOOT)\nN_BOOT_TASK = 100      # template -> slot bootstrap reps per task (original: 4000, per_task_route default)\nN_PERM ... [truncated, 23134 chars total]
```

### [111] ASSISTANT · 2026-10-26 10:33:21 UTC

```
Section 1: the constants and helpers from `src/cfg.py`, copied verbatim, with paths replaced.
```

### [112] TOOL CALL — NotebookEdit · 2026-10-26 10:33:21 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': '90440e47', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': '## 1. Frozen protocol constants and helpers (`src/cfg.py`)\n\nThese are the bench tasks in run order (`STAGE_A`) and each task\'s **default mechanism** (what Qwen3-8B writes without a ban). They are followed by the five ban templates W1-W5 (ban / mention / neutral wording) and the pre-registered decision thresholds.\n\nThe neutral twin of a ban fills the template\'s `{N}` slot with a concrete noun such as *fire*. It is padded with `" ."` to exactly the ban\'s token length, so positions line up and KV caches can be spliced position by position.\n\nThe helpers are copied verbatim. `stable_seed` is exp8\'s sha256-based seed, which keys the CRN uniform streams. Only the file-based logging sink and the file paths are dropped.'}
```

### [113] TOOL RESULT — NotebookEdit · 2026-10-26 10:33:21 UTC

```
{"new_source": "## 1. Frozen protocol constants and helpers (`src/cfg.py`)\n\nThese are the bench tasks in run order (`STAGE_A`) and each task's **default mechanism** (what Qwen3-8B writes without a ban). They are followed by the five ban templates W1-W5 (ban / mention / neutral wording) and the pre-registered decision thresholds.\n\nThe neutral twin of a ban fills the template's `{N}` slot with a concrete noun such as *fire*. It is padded with `\" .\"` to exactly the ... [truncated, 24918 chars total]
```

### [114] TOOL CALL — NotebookEdit · 2026-10-26 10:33:39 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': '92ea3a37', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '# ------------------------------------------------------------------------------------------------ model\nMODEL_ID = "Qwen/Qwen3-8B"\nMODEL_REVISION = "b968826d9c46dd6066d109eabc6255188de91218"\n\nN_LAYERS = 36\nIM_END = 151645\nENDOFTEXT = 151643\nMAX_NEW_TOKENS = 1024\nTEMPERATURE = 1.0\nDECODING = "T1.0_topp1.0_topk-off_max1024_thinkoff"\nTEMPLATE_TAIL = "<|im_end|>\\n<|im_start|>assistant\\n<think>\\n\\n</think>\\n\\n"\nBATCH = 20  # constant batch shape for every sampled batch (two CRN blocks of 10); see deviations\n\n# ------------------------------------------------------------------------------------------------ bench\nSTAGE_A = ["T03", "T04", "T06", "T05", "T10", "R1", "T08", "R3", "T13", "R6", "T14", "T11"]\nTASK_DIR = {"T03": "T03_kth_smallest", "T04": "T04_substring_search", "T06": "T06_find_duplicate",\n            "T05": "T05_two_sum", "T10": "T10_connected_components", "R1": "R1_non_overlapping_intervals",\n            "T08": "T08_fibonacci", "R3": "R3_topological_order", "T13": "T13_merge_intervals",\n            "R6": "R6_first_last_position", "T14": "T14_top_k_frequent", "T11": "T11_longest_increasing_subsequence"}\nDEFAULT = {"T03": "full_sort", "T04": "naive", "T06": "hash_set", "T05": "hash_map", "T10": "union_find",\n           "R1": "greedy_end", "T08": "iteration", "R3": "kahn", "T13": "sort_sweep", "R6": "binary_search",\n           "T14": "sort_by_count", "T11": "quadratic_dp"}\nPATH_TASKS = ("t1", "t2")\nPATH_DEFAULT = {"t1": "bfs", "t2": "dijkstra"}\nPATH_SUB = {"t1": "dfs", "t2": "bf_spfa"}\nALL_TASKS = STAGE_A + list(PATH_TASKS)\n\n# W1-W5 (ban, mention, neutral) verbatim from the shared protocol v2 (exp8 cfg.TEMPLATES).\nTEMPLATES: dict[str, tuple[str, str, str]] = {\n    "W1": ("Do not use {X} for this task.", "You could use {X} for this task.", "Do not use {N} for this task."),\n    "W2": ("Your solution must not rely on {X}.", "Your solution may rely on {X}.", "Your solution must not rely on {N}."),\n    "W3": ("Avoid {X} entirely.", "Consider {X} first.", "Avoid {N} entirely."),\n    "W4": ("{X} is not allowed here.", "{X} is allowed here.", "{N} is not allowed here."),\n    "W5": ("Write a correct solution that does not use {X}.", "Write a correct solution that may use {X}.",\n           "Write a correct solution that does not use {N}."),\n}\nTEMPLATE_IDS = list(TEMPLATES.keys())\nFILLER = " ."  # exp7 frozen neutral-twin padding filler\nN_PER_TEMPLATE = 20\nBLOCK = 10\n\nTHRESHOLDS = {\n    "F_confirm": 2.0 / 3.0, "F_ci_lower": 0.5, "F_direct_disconfirm": 1.0 / 3.0,\n    "gate_avoidance": 0.5, "gate_min_nondefault": 20,\n    "veto_low_direct": 0.8, "veto_high_direct": 0.5, "pred_low_direct_F": 0.15, "pred_high_direct_F": 0.25,\n    "veto_min_fire_rate": 0.5, "c2c_hit_fraction": 2.0 / 3.0, "c2c_disconfirm_hit": 0.5, "c2c_alpha": 0.05,\n    "ngram_presence": 0.8, "coveto": 0.5, "reemerge": 0.2, "screen_min_nond": 20, "placebo_tol": 0.1,\n    "c2b_eligible_V": 0.5, "c2b_task_share": 2.0 / 3.0,\n}\n# N_BOOT, N_PERM and RNG_SEED are set in the config cell (cfg.py: 10000, 100000, 20261020)\nPRED_DIR = Path("predictions")  # not shipped with the demo: the frozen predictions are read from data["metadata"]\n\n\n# ------------------------------------------------------------------------------------------------ utils\ndef setup_logging(name: str) -> None:\n    logger.remove()\n    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")\n    # original also writes logs/<name>.log: logger.add(str(LOG_DIR / f"{name}.log"), rotation="30 MB", level="DEBUG")\n\n\ndef sha256_text(s: str) -> str:\n    return hashlib.sha256(s.encode("utf-8")).hexdigest()\n\n\ndef stable_seed(*parts: Any) -> int:\n    """exp8: deterministic 63-bit seed from arbitrary parts (sha256 of their \'|\'-joined repr)."""\n    return int(hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest(), 16) % (2 ** 63)\n\n\ndef read_json(p: Path) -> Any:\n    return json.loads(Path(p).read_text())\n\n\ndef wilson_ci(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:\n    if n == 0:\n        return (float("nan"), float("nan"))\n    p = k / n\n    den = 1 + z * z / n\n    c = (p + z * z / (2 * n)) / den\n    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den\n    return (max(0.0, c - h), min(1.0, c + h))\n\n\ndef default_of(task: str) -> str:\n    return PATH_DEFAULT[task] if task in PATH_TASKS else DEFAULT[task]\n\n\nsetup_logging("demo")\nprint({t: DEFAULT[t] for t in STAGE_A})'}
```

### [115] TOOL RESULT — NotebookEdit · 2026-10-26 10:33:39 UTC

```
{"new_source": "# ------------------------------------------------------------------------------------------------ model\nMODEL_ID = \"Qwen/Qwen3-8B\"\nMODEL_REVISION = \"b968826d9c46dd6066d109eabc6255188de91218\"\n\nN_LAYERS = 36\nIM_END = 151645\nENDOFTEXT = 151643\nMAX_NEW_TOKENS = 1024\nTEMPERATURE = 1.0\nDECODING = \"T1.0_topp1.0_topk-off_max1024_thinkoff\"\nTEMPLATE_TAIL = \"<|im_end|>\\n<|im_start|>assistant\\n<think>\\n\\n</think>\\n\\n\"\nBATCH = 20  # constan... [truncated, 35354 chars total]
```

### [116] TOOL CALL — Bash · 2026-10-26 10:33:43 UTC

```
Read the Qwen3-0.6B ban-following test output:
cat /tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-3-art--5akZ9W9iZM4/c71db1cb-129d-4e37-954d-e401f6949d31/tasks/bt22a3kph.output | grep -v "^$" | grep -v "tied weights" | cut -c1-260
```

### [117] TOOL RESULT — Bash · 2026-10-26 10:33:43 UTC

````
{"stdout": "===== T03 W1 cond='Do not use a full sort for this task.' (33s, steps 108)\n  k=0 a(ban) fence  ```python \\n def solve(nums, k): \\n     # Sort the list to find the k-th smallest (this is a hint to avoid using a full sort) \\n     sorted_nums = sorted(nums) \\n      \\n     # Use a two-pointer approach to efficiently find the k-\n  k=0 b(twin) fence  ```python \\n def solve(nums, k): \\n     pass  # Implement the solution here \\n ```\n  k=1 a(ban) fence  ```python \\n def solve(nums, k): \\n     return sorted(nums)[k - 1] \\n ```\n  k=1 b(twin) fence  ```python \\n def solve(nums, k): \\n     return sorted(nums)[k - 1] \\n ```\n  k=2 a(ban) fence  ```python \\n def solve(nums, k): \\n     return sorted(nums)[k - 1] \\n ```\n  k=2 b(twin) fence  ```python \\n def solve(nums, k): \\n     return sorted(nums)[k - 1] \\n ```\n===== T03 W3 cond='Avoid a full sort entirely.' (14s, steps 50)\n  k=0 a(ban) fence  ```python \\n def solve(nums, k): \\n     return sorted(nums)[k - 1] \\n ```\n  k=0 b(twin) fence  ```python \\n def solve(nums, k): \\n     return sorted(nums)[k - 1] \\n ```\n  k=1 a(ban) fence  ```python \\n def solve(nums, k): \\n     return nums[k - 1] \\n ```\n  k=1 b(twin) fence  ```python \\n def solve(nums, k): \\n     return nums[k - 1] \\n ```\n  k=2 a(ban) fence  ```python \\n def solve(nums, k): \\n     # Use the built-in sort function (as no other sorting library is available) \\n     nums.sort() \\n     # Return the k-th smallest value (1-based index) \\n     return nums[k-1] \\n ```\n  k=2 b(twin) fence  ```python \\n def solve(nums, k): \\n     \"\"\"Return the k-th smallest value in the list nums.\"\"\" \\n     return sorted(nums)[k-1] \\n ```\n===== T03 W5 cond='Write a correct solution that does not use a full sort.' (17s, steps 61)\n  k=0 a(ban) fence  ```python \\n import bisect \\n  \\n def solve(nums, k): \\n     # Use the bisect module to get the k-th smallest element \\n     # We sort the list, but since we don't use sort directly \\n     arr = nums.copy() \\n     arr.sort() \\n   \n  k=0 b(twin) fence  ```python \\n def solve(nums, k): \\n     return sorted(nums)[k-1] \\n ```\n  k=1 a(ban) fence  ```python \\n def solve(nums, k): \\n     return sorted(nums)[k - 1] \\n ```\n  k=1 b(twin) fence  ```python \\n def solve(nums, k): \\n     return sorted(nums)[k - 1] \\n ```\n  k=2 a(ban) fence  ```python \\n def solve(nums, k): \\n     return nums[k-1] \\n ```\n  k=2 b(twin) fence  ```python \\n def solve(nums, k): \\n     return sorted(nums)[k - 1] if k <= len(nums) else None \\n ```\n===== T06 W2 cond='Your solution must not rely on a hash set of seen values.' (20s, steps 73)\n  k=0 a(ban) fence  ```python \\n def solve(nums): \\n     seen = set() \\n     for num in nums: \\n         if num in seen: \\n             return num \\n         seen.add(num) \\n ```\n  k=0 b(twin) fence  ```python \\n def solve(nums): \\n     # Use a hash set to track seen values \\n     seen = set() \\n     for num in nums: \\n         if num in seen: \\n             return num \\n         seen.add(num) \\n ```\n  k=1 a(ban) fence  ```python \\n def solve(nums): \\n     # Use a set to optimize the checking for duplicates \\n     seen = set() \\n     for num in nums: \\n         if num in seen: \\n             return num \\n         seen.add(num) \\n     return None \n  k=1 b(twin) fence  ```python \\n def solve(nums): \\n     n = len(nums) \\n     for i in range(n-1): \\n         num = nums[i] \\n         if num not in nums[:i+1]: \\n             return num \\n ```\n  k=2 a(ban) fence  ```python \\n def solve(nums): \\n     seen = {} \\n     for n in nums: \\n         seen[n] = seen.get(n, 0) + 1 \\n     for n in nums: \\n         if seen[n] > 1: \\n             return n \\n ```\n  k=2 b(twin) fence  ```python \\n def solve(nums): \\n     # Create a frequency dictionary \\n     freq = dict() \\n      \\n     # Populate the frequency dictionary \\n     for num in nums: \\n         if num in freq: \\n             freq[num] += 1 \\n      \n===== T06 W5 cond='Write a correct solution that does not use a hash set of seen values.' (11s, steps 39)\n  k=0 a(ban) fence  ```python \\n def solve(nums): \\n     seen = set() \\n     for num in nums: \\n         if num in seen: \\n             return num \\n         seen.add(num) \\n     return None \\n ```\n  k=0 b(twin) fence  ```python \\n def solve(nums): \\n     return nums.index(nums[-1]) if len(set(nums)) == 1 else nums.index(nums[-1]) \\n ```\n  k=1 a(ban) fence  ```python \\n def solve(nums): \\n     n = len(nums) \\n     seen = set() \\n     for num in nums: \\n         if num in seen: \\n             return num \\n         seen.add(num) \\n ```\n  k=1 b(twin) fence  ```python \\n def solve(nums): \\n     n = len(nums) \\n     seen = set() \\n     for num in nums: \\n         if num in seen: \\n             return num \\n         seen.add(num) \\n ```\n  k=2 a(ban) fence  ```python \\n def solve(nums): \\n     seen = set() \\n     for num in nums: \\n         if num in seen: \\n             return num \\n         seen.add(num) \\n ```\n  k=2 b(twin) fence  ```python \\n def solve(nums): \\n     seen = set() \\n     for num in nums: \\n         if num in seen: \\n             return num \\n         seen.add(num) \\n ```\n===== T10 W1 cond='Do not use union-find (disjoint set union) for this task.' (45s, steps 159)\n  k=0 a(ban) fence  ```python \\n def solve(n, edges): \\n     visited = set() \\n     count = 0 \\n     for u in range(n): \\n         if u not in visited: \\n             count += 1 \\n             visited.add(u) \\n             for v in edges: \\n         \n  k=0 b(twin) fence  ```python \\n def solve(n, edges): \\n     import collections \\n  \\n     graph = {i: set() for i in range(n)} \\n      \\n     for u, v in edges: \\n         graph[u].add(v) \\n         graph[v].add(u) \\n      \\n     visited = set() \\n \n  k=1 a(ban) length ```python \\n def solve(n, edges): \\n     # Create an adjacency list for the graph \\n     graph = [[] for _ in range(n)] \\n     for u, v in edges: \\n         graph[u].append(v) \\n         graph[v].append(u) \\n      \\n     # Use a v\n  k=1 b(twin) fence  ```python \\n def solve(n, edges): \\n     from collections import defaultdict, deque \\n  \\n     graph = defaultdict(list) \\n     for u, v in edges: \\n         graph[u].append(v) \\n         graph[v].append(u) \\n  \\n     visited = [F\n  k=2 a(ban) fence  ```python \\n def solve(n, edges): \\n     visited = set() \\n     components = set() \\n  \\n     for u in range(n): \\n         if u not in visited: \\n             # Start a new component \\n             components.add(u) \\n           \n  k=2 b(twin) fence  ```python \\n def solve(n, edges): \\n     import sys \\n     import collections \\n  \\n     graph = [[] for _ in range(n)] \\n  \\n     for u, v in edges: \\n         graph[u].append(v) \\n         graph[v].append(u) \\n  \\n     visited =\n===== T05 W1 cond='Do not use a hash map of seen values for this task.' (21s, steps 77)\n  k=0 a(ban) fence  ```python \\n def solve(nums, target): \\n     j = 1 \\n     while j < len(nums): \\n         if nums[j] == target - nums[j - 1]: \\n             return [j - 1, j] \\n         if nums[j] < target - nums[j - 1]: \\n             j += 1 \\n \n  k=0 b(twin) fence  ```python \\n def solve(nums, target): \\n     j = 0 \\n     for i in range(len(nums)): \\n         j = i + 1 \\n         if nums[i] + nums[j] == target: \\n             return [i, j] \\n     return []  # This line should never be reache\n  k=1 a(ban) fence  ```python \\n def solve(nums, target): \\n     i = 0 \\n     j = len(nums) - 1 \\n     while i < j: \\n         if nums[i] + nums[j] == target: \\n             return [i, j] \\n         elif nums[i] + nums[j] < target: \\n             i +\n  k=1 b(twin) fence  ```python \\n def solve(nums, target): \\n     i = 0 \\n     j = len(nums) - 1 \\n     while i < j: \\n         if nums[i] + nums[j] == target: \\n             return [i, j] \\n         elif nums[i] + nums[j] < target: \\n             i +\n  k=2 a(ban) fence  ```python \\n def solve(nums, target): \\n     for i in range(len(nums)): \\n         for j in range(i + 1, len(nums)): \\n             if nums[i] + nums[j] == target: \\n                 return [i, j] \\n ```\n  k=2 b(twin) fence  ```python \\n def solve(nums, target): \\n     for i in range(len(nums) - 1): \\n         for j in range(i + 1, len(nums)): \\n             if nums[i] + nums[j] == target: \\n                 return [i, j] \\n ```\n[exited with code 0]", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
````

### [118] THINKING · 2026-10-26 10:33:59 UTC

```
Qwen3-0.6B doesn't reliably follow the bans and has unstable defaults, so the live cell will only demonstrate the mechanics while the actual phenomenon relies on the paired Qwen3-8B rows—I'll note this clearly in the notebook, keep T06/W1 as the engine slot set, and move on to section 2's labelled rows.
```

### [119] TOOL CALL — NotebookEdit · 2026-10-26 10:33:59 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': '95ac415d', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "## 2. Labelled rows (replaces `analysis.load_rows()` on `data/samples.jsonl`)\n\nIn the original pipeline the GPU queue writes one raw row per generated program. The label worker runs the frozen labellers, and `data/samples.jsonl` ends up with one labelled row per `uid = task|arm|template|k`.\n\nThe demo data stores the same information per CRN slot:\n- `output` is the arm-`a` label.\n- `predict_<arm>` is `'<mechanism>|pass'` or `'<mechanism>|fail'` for the other arms.\n- `metadata_token_ids` holds the generated ids of each arm.\n\n`load_rows()` below rebuilds exactly the fields the analysis reads. An arm marked `not_run` gets no row, as in the original. `catalogue()` is `forecast_s2.catalogue()` reading the per-task mechanism lists from the data instead of `bench/<task>/spec.json`."}
```

### [120] TOOL RESULT — NotebookEdit · 2026-10-26 10:33:59 UTC

```
{"new_source": "## 2. Labelled rows (replaces `analysis.load_rows()` on `data/samples.jsonl`)\n\nIn the original pipeline the GPU queue writes one raw row per generated program. The label worker runs the frozen labellers, and `data/samples.jsonl` ends up with one labelled row per `uid = task|arm|template|k`.\n\nThe demo data stores the same information per CRN slot:\n- `output` is the arm-`a` label.\n- `predict_<arm>` is `'<mechanism>|pass'` or `'<mechanism>|fail'` for... [truncated, 37847 chars total]
```

### [121] TOOL CALL — NotebookEdit · 2026-10-26 10:34:11 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': '0f27d9a4', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'EXCL = ("invalid", "no_code", "disputed")\nROUTE_ARMS = ("a", "b", "c", "d")\n\n\n# ------------------------------------------------------------------------------------------------ helpers\ndef load_rows() -> list[dict[str, Any]]:\n    # notebook version: rebuild one labelled row per (task, arm, template, k) from the route_arms examples\n    # (original: rows = read_jsonl(SAMPLES)); an arm marked \'not_run\' has no row, as in data/samples.jsonl\n    rows = []\n    for e in examples:\n        t, w, k = e["metadata_task"], e["metadata_template"], e["metadata_k"]\n        labs = {"a": (e["output"], bool(e["metadata_a_passed"]))}\n        for a in ("b", "c", "d", "K0"):\n            if e[f"predict_{a}"] != "not_run":\n                lab, _, res = e[f"predict_{a}"].partition("|")\n                labs[a] = (lab, res == "pass")\n        for a, (lab, passed) in labs.items():\n            rows.append({"uid": f"{t}|{a}|{w}|{k}", "stage": "demo", "task": t, "template": w, "w": w, "k": k,\n                         "arm": a, "label": lab, "passed": passed, "token_ids": e["metadata_token_ids"].get(a)})\n    seen = {}\n    for r in rows:  # last label wins if a uid was relabelled\n        seen[r["uid"]] = r\n    return list(seen.values())\n\n\ndef catalogue(task: str) -> list[str]:\n    # original: forecast_s2.catalogue() -> [c["mode"] for c in read_json(BENCH / TASK_DIR[task] / "spec.json")["catalogue"]]\n    return meta["catalogue"][task]\n\n\ndef survivors(task: str) -> list[str]:\n    return [m for m in catalogue(task) if m != default_of(task)] + ["other"]\n\n\nrows = load_rows()\nbench_rows = [r for r in rows if r["task"] in STAGE_A and r["stage"] not in ("U9",)]  # as in run_analysis()\ndemo_tasks = [t for t in STAGE_A if any(r["task"] == t for r in bench_rows)]\nprint(f"{len(rows)} labelled rows over {len(demo_tasks)} tasks; rows per task x arm:")\nprint(pd.crosstab(pd.Series([r["task"] for r in rows], name="task"), pd.Series([r["arm"] for r in rows], name="arm"))\n      .reindex(demo_tasks))\nprint("\\none CRN slot (T06, W1, k=1) -- every arm read the same uniforms:")\nfor r in rows:\n    if (r["task"], r["template"], r["k"]) == ("T06", "W1", 1):\n        print(f"  arm {r[\'arm\']:3s} label={r[\'label\']:15s} passed={r[\'passed\']}  n_tokens={len(r[\'token_ids\'])}")'}
```

### [122] TOOL RESULT — NotebookEdit · 2026-10-26 10:34:11 UTC

```
{"new_source": "EXCL = (\"invalid\", \"no_code\", \"disputed\")\nROUTE_ARMS = (\"a\", \"b\", \"c\", \"d\")\n\n\n# ------------------------------------------------------------------------------------------------ helpers\ndef load_rows() -> list[dict[str, Any]]:\n    # notebook version: rebuild one labelled row per (task, arm, template, k) from the route_arms examples\n    # (original: rows = read_jsonl(SAMPLES)); an arm marked 'not_run' has no row, as in data/samples.js... [truncated, 43211 chars total]
```

### [123] ASSISTANT · 2026-10-26 10:34:19 UTC

```
Section 3: the gate (`gpu.compute_gate`).
```

### [124] TOOL CALL — NotebookEdit · 2026-10-26 10:34:19 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': 'd62567d8', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "## 3. Gate: does the ban move the model at all? (`gpu.compute_gate`)\n\nThe route analysis only makes sense where the full ban changes the program. The pre-registered gate needs two things from arm `a`: **avoidance** `1 - s_a >= 0.5`, and **at least 20 non-default attempts** (out of 100 CRN slots per task).\n\nIn the original, `compute_gate()` runs inside the GPU queue on the labelled arm-a rows and writes `results/gate.json`. `run_analysis()` then reads that file. The demo does the same:\n- `compute_gate()` runs verbatim on the subset. `labelled_uids()` returns the demo rows instead of reading `data/samples.jsonl`.\n- The confirmatory analysis uses the **frozen gate** shipped in the data, i.e. `results/gate.json` from all 100 arm-a rows per task.\n\nThe subset has at most 15 arm-a rows per task, so no task can reach 20 non-default attempts here. The subset's avoidance column still shows the same split as the full run."}
```

### [125] TOOL RESULT — NotebookEdit · 2026-10-26 10:34:19 UTC

```
{"new_source": "## 3. Gate: does the ban move the model at all? (`gpu.compute_gate`)\n\nThe route analysis only makes sense where the full ban changes the program. The pre-registered gate needs two things from arm `a`: **avoidance** `1 - s_a >= 0.5`, and **at least 20 non-default attempts** (out of 100 CRN slots per task).\n\nIn the original, `compute_gate()` runs inside the GPU queue on the labelled arm-a rows and writes `results/gate.json`. `run_analysis()` then read... [truncated, 45634 chars total]
```

### [126] TOOL CALL — NotebookEdit · 2026-10-26 10:34:29 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': '61f906af', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'ATTEMPT_EXCLUDE = ("invalid", "no_code", "disputed")\n\n\n# ------------------------------------------------------------------------------------------------ labels\ndef labelled_uids() -> dict[str, dict[str, Any]]:\n    return {r["uid"]: r for r in rows}  # original: {r["uid"]: r for r in read_jsonl(SAMPLES)}\n\n\ndef share_default(rows: list[dict[str, Any]], task: str) -> tuple[int, int]:\n    att = [r for r in rows if r["label"] not in ATTEMPT_EXCLUDE]\n    return sum(r["label"] == default_of(task) for r in att), len(att)\n\n\ndef compute_gate(tasks: list[str]) -> dict[str, Any]:\n    lab = labelled_uids()\n    out = {}\n    for t in tasks:\n        rows = [r for r in lab.values() if r["task"] == t and r["arm"] == "a"]\n        nd, na = share_default(rows, t)\n        s_a = nd / na if na else float("nan")\n        out[t] = {"s_a": s_a, "avoidance": 1 - s_a, "n_attempted": na, "n_nondefault": na - nd, "n_rows": len(rows),\n                  "gated": bool(na and (1 - s_a) >= THRESHOLDS["gate_avoidance"]\n                                and (na - nd) >= THRESHOLDS["gate_min_nondefault"])}\n    return out\n\n\ngate_demo = compute_gate(demo_tasks)\n\n# run_analysis(): gate = read_json(RESULTS_DIR / "gate.json"); failed = labeller_recheck["failed_tasks"]\ngate = meta["gate"]  # frozen results/gate.json (all 100 arm-a rows per task)\nfailed = set()       # results/labeller_recheck.json: failed_tasks = [] (every bench labeller passed its re-check)\ngated = [t for t in STAGE_A if gate.get(t, {}).get("gated") and t not in failed]\n\ngate_tbl = pd.DataFrame({t: {"default": DEFAULT[t],\n                             "full: avoidance": gate[t]["avoidance"], "full: n_nondefault/100": gate[t]["n_nondefault"],\n                             "full: gated": gate[t]["gated"],\n                             "demo: avoidance": gate_demo[t]["avoidance"] if t in gate_demo else None,\n                             "demo: n_nondefault": gate_demo[t]["n_nondefault"] if t in gate_demo else None,\n                             "demo: n_attempted": gate_demo[t]["n_attempted"] if t in gate_demo else None}\n                         for t in STAGE_A}).T\nprint(gate_tbl.to_string(float_format=lambda x: f"{x:.2f}"))\nprint("\\ngated (frozen gate, used below):", gated)'}
```

### [127] TOOL RESULT — NotebookEdit · 2026-10-26 10:34:29 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [128] ASSISTANT · 2026-10-26 10:34:37 UTC

```
Section 4.1: per-task × arm shares (analysis 9.1), copied verbatim.
```

### [129] TOOL CALL — NotebookEdit · 2026-10-26 10:34:37 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': '7b28a7ae', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "## 4. S9 analysis (`src/analysis/analysis.py`)\n\nThe analysis code was committed in a hash chain *before any ban sample existed* (commit #1). The functions below are copied from it. The only changes are reading from the loaded data instead of files, and the resampling counts from the config cell.\n\n### 4.1 Default share per task and arm (9.1)\n\n`share()` counts, among the *attempted* programs (not `invalid`, `no_code` or `disputed`), the fraction labelled with the task's default mechanism, with a Wilson 95% interval. It also records the **landing**, i.e. which other mechanism the model wrote instead, together with pass rates and Hill diversity.\n\nFor a working ban, `s_a` (full ban) is far below `s_b` (neutral twin). Where `s_c` and `s_d` fall between the two tells which route carries the effect."}
```

### [130] TOOL RESULT — NotebookEdit · 2026-10-26 10:34:37 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [131] TOOL CALL — NotebookEdit · 2026-10-26 10:34:49 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': '36bf6d79', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'def hill1(labels: list[str]) -> float:\n    if not labels:\n        return float("nan")\n    c = np.array(list(collections.Counter(labels).values()), float)\n    p = c / c.sum()\n    return float(np.exp(-(p * np.log(p)).sum()))\n\n\ndef share(rows: list[dict[str, Any]], task: str) -> dict[str, Any]:\n    D = default_of(task)\n    att = [r for r in rows if r["label"] not in EXCL]\n    nd = sum(r["label"] == D for r in att)\n    n = len(att)\n    lo, hi = wilson_ci(nd, n) if n else (float("nan"), float("nan"))\n    nond = [r for r in att if r["label"] != D]\n    land = collections.Counter(r["label"] for r in nond)\n    corr = collections.Counter(r["label"] for r in nond if r.get("passed"))\n    return {"n_rows": len(rows), "n_attempted": n, "n_default": nd, "s": nd / n if n else float("nan"),\n            "ci95": [lo, hi], "landing": dict(land), "modal_survivor": land.most_common(1)[0][0] if land else None,\n            "correct_landing": dict(corr),\n            "other_share": (sum(r["label"] == "other" for r in att) / n) if n else float("nan"),\n            "invalid_share": (sum(r["label"] in ("invalid", "no_code") for r in rows) / len(rows)) if rows else float("nan"),\n            "disputed": sum(r["label"] == "disputed" for r in rows),\n            "pass_rate": float(np.mean([bool(r.get("passed")) for r in rows])) if rows else float("nan"),\n            "hill_cc": hill1([r["label"] for r in att if r.get("passed")]),\n            "hill_cc_nondefault": hill1([r["label"] for r in nond if r.get("passed")])}\n\n\ndef by(rows: list[dict[str, Any]], *keys: str) -> dict[tuple, list[dict[str, Any]]]:\n    out: dict[tuple, list] = collections.defaultdict(list)\n    for r in rows:\n        out[tuple(r[k] for k in keys)].append(r)\n    return out\n\n\n# ------------------------------------------------------------------------------------------------ 9.1\ndef shares_table(rows: list[dict[str, Any]]) -> dict[str, Any]:\n    out: dict[str, Any] = {}\n    g = by(rows, "task", "arm")\n    for (t, a), lst in sorted(g.items()):\n        out.setdefault(t, {})[a] = share(lst, t)\n        per_w = {}\n        for w in TEMPLATE_IDS:\n            sub = [r for r in lst if r["template"] == w]\n            if sub:\n                s = share(sub, t)\n                per_w[w] = {k: s[k] for k in ("n_attempted", "n_default", "s", "modal_survivor", "pass_rate")}\n        out[t][a]["per_template"] = per_w\n    return out\n\n\nshares = shares_table(bench_rows)\nARMS5 = ("a", "b", "c", "d", "K0")\nshare_tbl = pd.DataFrame({t: {f"s_{a}": shares[t][a]["s"] for a in ARMS5 if a in shares[t]} for t in demo_tasks}).T\nshare_tbl["n/arm"] = [shares[t]["a"]["n_attempted"] for t in demo_tasks]\nshare_tbl["arm-a modal survivor"] = [shares[t]["a"]["modal_survivor"] for t in demo_tasks]\nshare_tbl["gated"] = [t in gated for t in demo_tasks]\nprint(share_tbl.to_string(float_format=lambda x: f"{x:.2f}"))'}
```

### [132] TOOL RESULT — NotebookEdit · 2026-10-26 10:34:49 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [133] ASSISTANT · 2026-10-26 10:35:03 UTC

```
Section 4.2: route fractions (analysis 9.2). The only code change is `slot_arrays`' hardcoded `K = 20` becoming `N_SLOTS`.
```

### [134] TOOL CALL — NotebookEdit · 2026-10-26 10:35:03 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': 'd6f7cfbc', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': '### 4.2 Route fractions with CRN-respecting resampling (9.2)\n\n`slot_arrays()` builds two 0/1 tensors indexed `[task, template, slot k, arm]`: `banned` (the program is the default mechanism) and `att` (an attempt was made). The pooled fractions are a **ratio of sums** over tasks, not a mean of per-task ratios.\n\nAll intervals resample *whole CRN slots*, keeping every arm of a slot together, because the arms share their uniforms:\n- **Hierarchical bootstrap:** task → template → slot.\n- **Leave-one-task-out jackknife:** with 3-5 gated tasks the pooled estimate is low-cluster. Pre-registered fallback F5, a logged amendment, makes the jackknife t-interval the *primary* interval.\n- **BCa:** bias-corrected and accelerated, using the jackknife for acceleration.\n\nC2a decision rule:\n- **SUPPORTED:** `F_prompt >= 2/3` with a CI lower bound > 1/2, and not `F_direct >= 1/3`.\n- **DISCONFIRMED:** `F_direct >= 1/3` without support.\n- **MIXED:** otherwise.\n\nThe only code change: `slot_arrays()` used `K = 20` slots per template, and here it uses `N_SLOTS` from the config.'}
```

### [135] TOOL RESULT — NotebookEdit · 2026-10-26 10:35:03 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [136] TOOL CALL — NotebookEdit · 2026-10-26 10:35:17 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': 'bdfa771f', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '# ------------------------------------------------------------------------------------------------ 9.2\ndef slot_arrays(rows: list[dict[str, Any]], tasks: list[str], arms: tuple[str, ...] = ROUTE_ARMS) -> dict[str, Any]:\n    """banned[t, w, k, arm] in {0,1}, att[t, w, k, arm] in {0,1} (attempted)."""\n    T, Wn, K, A = len(tasks), len(TEMPLATE_IDS), N_SLOTS, len(arms)  # original: K = 20\n    ban = np.zeros((T, Wn, K, A), np.int8)\n    att = np.zeros((T, Wn, K, A), np.int8)\n    idx = {(r["task"], r["template"], r["k"], r["arm"]): r for r in rows}\n    for i, t in enumerate(tasks):\n        D = default_of(t)\n        for j, w in enumerate(TEMPLATE_IDS):\n            for k in range(K):\n                for a_i, a in enumerate(arms):\n                    r = idx.get((t, w, k, a))\n                    if r is not None and r["label"] not in EXCL:\n                        att[i, j, k, a_i] = 1\n                        ban[i, j, k, a_i] = int(r["label"] == D)\n    return {"ban": ban, "att": att, "tasks": tasks, "arms": arms}\n\n\ndef fractions_from_counts(nb: np.ndarray, na: np.ndarray, arms: tuple[str, ...]) -> dict[str, np.ndarray]:\n    """nb, na: [..., T, A] counts -> pooled (ratio of sums over T) F values [...]."""\n    s = nb / np.maximum(na, 1)\n    ai = {a: i for i, a in enumerate(arms)}\n    sa, sb, sc, sd = (s[..., ai[x]] for x in ("a", "b", "c", "d"))\n    den = (sb - sa).sum(-1)\n    with np.errstate(divide="ignore", invalid="ignore"):\n        Fp = (sb - sc).sum(-1) / den\n        Fd = (sb - sd).sum(-1) / den\n        out = {"F_prompt": Fp, "F_direct": Fd, "I": 1 - Fp - Fd,\n               "F_prompt_mean": np.nanmean((sb - sc) / (sb - sa), -1),\n               "F_direct_mean": np.nanmean((sb - sd) / (sb - sa), -1)}\n        if "K0" in ai:\n            out["F_K0"] = (sb - s[..., ai["K0"]]).sum(-1) / den\n    return out\n\n\ndef point_fractions(arr: dict[str, Any]) -> dict[str, float]:\n    nb = arr["ban"].sum((1, 2)).astype(float)\n    na = arr["att"].sum((1, 2)).astype(float)\n    f = fractions_from_counts(nb, na, arr["arms"])\n    return {k: float(v) for k, v in f.items()}'}
```

### [137] TOOL RESULT — NotebookEdit · 2026-10-26 10:35:18 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [138] TOOL CALL — NotebookEdit · 2026-10-26 10:35:29 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': 'f096a19f', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'def hier_boot(arr: dict[str, Any], n_boot: int = N_BOOT, seed: int = RNG_SEED) -> dict[str, np.ndarray]:\n    rng = np.random.default_rng(seed)\n    ban, att = arr["ban"], arr["att"]\n    T, Wn, K, A = ban.shape\n    out = collections.defaultdict(list)\n    chunk = 500\n    for s in range(0, n_boot, chunk):\n        R = min(chunk, n_boot - s)\n        ti = rng.integers(0, T, (R, T))\n        wi = rng.integers(0, Wn, (R, T, Wn))\n        ki = rng.integers(0, K, (R, T, Wn, K))\n        tt = ti[:, :, None, None]\n        ww = wi[:, :, :, None]\n        b = ban[tt, ww, ki]  # [R, T, Wn, K, A]\n        a = att[tt, ww, ki]\n        nb = b.sum((2, 3)).astype(float)\n        na = a.sum((2, 3)).astype(float)\n        f = fractions_from_counts(nb, na, arr["arms"])\n        for k, v in f.items():\n            out[k].append(v)\n    return {k: np.concatenate(v) for k, v in out.items()}\n\n\ndef jackknife(arr: dict[str, Any]) -> dict[str, np.ndarray]:\n    T = arr["ban"].shape[0]\n    res = collections.defaultdict(list)\n    for i in range(T):\n        keep = [j for j in range(T) if j != i]\n        sub = {"ban": arr["ban"][keep], "att": arr["att"][keep], "arms": arr["arms"]}\n        for k, v in point_fractions(sub).items():\n            res[k].append(v)\n    return {k: np.array(v) for k, v in res.items()}\n\n\ndef bca_ci(theta: float, boot: np.ndarray, jack: np.ndarray, alpha: float = 0.05) -> list[float]:\n    boot = boot[np.isfinite(boot)]\n    if len(boot) < 100 or not np.isfinite(theta) or len(jack) < 3:\n        return [float("nan"), float("nan")]\n    z0 = stats.norm.ppf(np.clip(np.mean(boot < theta), 1e-6, 1 - 1e-6))\n    d = jack.mean() - jack\n    den = 6 * (np.sum(d ** 2) ** 1.5)\n    a = float(np.sum(d ** 3) / den) if den > 0 else 0.0\n    zs = stats.norm.ppf([alpha / 2, 1 - alpha / 2])\n    adj = stats.norm.cdf(z0 + (z0 + zs) / (1 - a * (z0 + zs)))\n    return [float(np.quantile(boot, adj[0])), float(np.quantile(boot, adj[1]))]\n\n\ndef jack_ci(theta: float, jack: np.ndarray) -> list[float]:\n    n = len(jack)\n    if n < 3:\n        return [float("nan"), float("nan")]\n    se = math.sqrt((n - 1) / n * np.sum((jack - jack.mean()) ** 2))\n    tq = stats.t.ppf(0.975, n - 1)\n    return [theta - tq * se, theta + tq * se]\n\n\ndef pct_ci(boot: np.ndarray) -> list[float]:\n    b = boot[np.isfinite(boot)]\n    return [float(np.quantile(b, 0.025)), float(np.quantile(b, 0.975))] if len(b) else [float("nan")] * 2'}
```

### [139] TOOL RESULT — NotebookEdit · 2026-10-26 10:35:30 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [140] TOOL CALL — NotebookEdit · 2026-10-26 10:35:51 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': 'b166b928', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'def per_task_route(arr: dict[str, Any], n_boot: int = N_BOOT_TASK) -> dict[str, Any]:  # original default: 4000\n    out = {}\n    for i, t in enumerate(arr["tasks"]):\n        sub = {"ban": arr["ban"][i:i + 1], "att": arr["att"][i:i + 1], "arms": arr["arms"], "tasks": [t]}\n        pt = point_fractions(sub)\n        rng = np.random.default_rng(RNG_SEED + 7 + i)\n        ban, att = sub["ban"][0], sub["att"][0]\n        Wn, K, A = ban.shape\n        wi = rng.integers(0, Wn, (n_boot, Wn))\n        ki = rng.integers(0, K, (n_boot, Wn, K))\n        b = ban[wi[:, :, None], ki]\n        a = att[wi[:, :, None], ki]\n        f = fractions_from_counts(b.sum((1, 2))[:, None, :].astype(float), a.sum((1, 2))[:, None, :].astype(float),\n                                  arr["arms"])\n        out[t] = {k: {"point": pt[k], "ci95": pct_ci(f[k])} for k in ("F_prompt", "F_direct", "I") + (("F_K0",) if "F_K0" in pt else ())}\n        out[t]["N_prompt"] = 1 - pt["F_direct"]\n        out[t]["N_direct"] = 1 - pt["F_prompt"]\n    return out\n\n\ndef mixed_glm(rows: list[dict[str, Any]], tasks: list[str]) -> dict[str, Any]:\n    try:\n        import pandas as pd\n        from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM\n\n        recs = [{"banned": int(r["label"] == default_of(r["task"])), "arm": r["arm"], "task": r["task"],\n                 "tt": f"{r[\'task\']}:{r[\'template\']}"} for r in rows\n                if r["task"] in tasks and r["arm"] in ROUTE_ARMS and r["label"] not in EXCL]\n        df = pd.DataFrame(recs)\n        df["arm"] = pd.Categorical(df["arm"], categories=["b", "a", "c", "d"])\n        m = BinomialBayesMixedGLM.from_formula("banned ~ C(arm)", {"task": "0 + C(task)", "tt": "0 + C(tt)"}, df)\n        fit = m.fit_vb()\n        names = list(m.exog_names)\n        fe = dict(zip(names, map(float, fit.fe_mean)))\n        sd = dict(zip(names, map(float, fit.fe_sd)))\n        b0 = fe["Intercept"]\n        p = {"b": 1 / (1 + math.exp(-b0))}\n        for a in ("a", "c", "d"):\n            p[a] = 1 / (1 + math.exp(-(b0 + fe[f"C(arm)[T.{a}]"])))\n        Fp = (p["b"] - p["c"]) / (p["b"] - p["a"]) if p["b"] != p["a"] else float("nan")\n        Fd = (p["b"] - p["d"]) / (p["b"] - p["a"]) if p["b"] != p["a"] else float("nan")\n        return {"fixed_effects_mean": fe, "fixed_effects_sd": sd, "vcp_mean": list(map(float, fit.vcp_mean)),\n                "probabilities_at_zero_random_effects": p, "F_prompt_glm": Fp, "F_direct_glm": Fd,\n                "note": "descriptive sensitivity (variational Bayes); logit-scale fixed effects at zero random effects"}\n    except Exception as e:  # noqa: BLE001 - descriptive sensitivity; record the failure\n        logger.exception("mixed GLM failed")\n        return {"error": str(e)[:300]}\n\n\ndef route_analysis(rows: list[dict[str, Any]], gated: list[str]) -> dict[str, Any]:\n    full = [t for t in gated if all(any(r["task"] == t and r["arm"] == a for r in rows) for a in ROUTE_ARMS)]\n    if not full:\n        return {"n_tasks": 0, "verdict": "NOT_RUN", "tasks": []}\n    arms = ROUTE_ARMS + (("K0",) if all(any(r["task"] == t and r["arm"] == "K0" for r in rows) for t in full) else ())\n    arr = slot_arrays(rows, full, arms)\n    pt = point_fractions(arr)\n    boot = hier_boot(arr)\n    jack = jackknife(arr)\n    res: dict[str, Any] = {"tasks": full, "n_tasks": len(full), "arms": list(arms), "point": pt, "intervals": {}}\n    for k in pt:\n        res["intervals"][k] = {"percentile": pct_ci(boot[k]), "bca": bca_ci(pt[k], boot[k], jack[k]),\n                               "jackknife": jack_ci(pt[k], jack[k]), "jackknife_values": jack[k].tolist()}\n    res["p_boot_F_prompt_le_half"] = float(np.mean(boot["F_prompt"][np.isfinite(boot["F_prompt"])] <= 0.5))\n    res["p_boot_F_direct_ge_third"] = float(np.mean(boot["F_direct"][np.isfinite(boot["F_direct"])] >= 1 / 3))\n    lot = {}\n    for j, w in enumerate(TEMPLATE_IDS):\n        keep = [x for x in range(len(TEMPLATE_IDS)) if x != j]\n        sub = {"ban": arr["ban"][:, keep], "att": arr["att"][:, keep], "arms": arr["arms"]}\n        lot[w] = point_fractions(sub)\n    res["leave_one_template_out"] = lot\n    verdicts = {}\n    for kind in ("percentile", "bca", "jackknife"):\n        lo = res["intervals"]["F_prompt"][kind][0]\n        sup = bool(pt["F_prompt"] >= THRESHOLDS["F_confirm"] and np.isfinite(lo) and lo > THRESHOLDS["F_ci_lower"])\n        dis = bool(pt["F_direct"] >= THRESHOLDS["F_direct_disconfirm"])\n        verdicts[kind] = "SUPPORTED" if sup and not dis else ("DISCONFIRMED" if dis and not sup else "MIXED")\n    res["verdict_by_interval"] = verdicts\n    res["low_cluster"] = len(full) < 6\n    # amendment 2 (logged): plan fallback F5 -- with 3-5 gated tasks the pooled estimate is \'low-cluster\' and the\n    # leave-one-task-out jackknife CI is the primary interval\n    res["primary_interval"] = "jackknife" if 3 <= len(full) <= 5 else "percentile"\n    res["verdict"] = verdicts[res["primary_interval"]]\n    res["per_task"] = per_task_route(arr)\n    res["mixed_glm"] = mixed_glm(rows, full)\n    res["holm_note"] = "bootstrap p values enter the cross-artifact primary Holm family next round"\n    return res'}
```

### [141] TOOL RESULT — NotebookEdit · 2026-10-26 10:35:51 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [142] ASSISTANT · 2026-10-26 10:36:07 UTC

```
Now the cell that runs the route analysis (the `run_analysis()` lines) and prints it next to the full-run reference.
```

### [143] TOOL CALL — NotebookEdit · 2026-10-26 10:36:07 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': 'ce9dcbb7', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '# run_analysis(): confirmatory route analysis on the gated tasks + descriptive per-task fractions on the others\nt0 = time.time()\nroute = route_analysis(bench_rows, gated)\nnongated = [t for t in STAGE_A if t not in gated]\nroute_ng = {}\nif nongated:\n    arr = slot_arrays(bench_rows, [t for t in nongated if all((t, a) in by(bench_rows, "task", "arm") for a in ROUTE_ARMS)])\n    route_ng = per_task_route(arr) if arr["tasks"] else {}\nprint(f"route analysis: {time.time() - t0:.1f}s (N_BOOT={N_BOOT}, N_BOOT_TASK={N_BOOT_TASK})")\n\nref = meta["full_run_reference"]  # the same quantities from the full run (N = 100 slots per task and arm)\nprint(f"\\nC2a verdict -- demo: {route[\'verdict\']} (primary interval: {route[\'primary_interval\']}, by interval "\n      f"{route[\'verdict_by_interval\']})  |  full run: {ref[\'C2a\'][\'verdict\']}")\npooled = pd.DataFrame({k: {"demo point": route["point"][k],\n                           "demo jackknife (primary)": "[{:.2f}, {:.2f}]".format(*route["intervals"][k]["jackknife"]),\n                           "demo percentile": "[{:.2f}, {:.2f}]".format(*route["intervals"][k]["percentile"]),\n                           "demo BCa": "[{:.2f}, {:.2f}]".format(*route["intervals"][k]["bca"]),\n                           "full point": ref["C2a"]["point"][k],\n                           "full jackknife": "[{:.2f}, {:.2f}]".format(*ref["C2a"]["intervals"][k]["jackknife"])}\n                       for k in ("F_prompt", "F_direct", "I", "F_K0")}).T\nprint(pooled.to_string(float_format=lambda x: f"{x:.3f}"))\nprint(f"P_boot(F_prompt <= 1/2) = {route[\'p_boot_F_prompt_le_half\']:.2f}  P_boot(F_direct >= 1/3) = "\n      f"{route[\'p_boot_F_direct_ge_third\']:.2f}   (full run: {ref[\'C2a\'][\'p_boot_F_prompt_le_half\']:.2f} / "\n      f"{ref[\'C2a\'][\'p_boot_F_direct_ge_third\']:.2f})")\nmg = route["mixed_glm"]\nprint(f"mixed GLM sensitivity: F_prompt {mg.get(\'F_prompt_glm\', float(\'nan\')):.2f}, F_direct "\n      f"{mg.get(\'F_direct_glm\', float(\'nan\')):.2f}  (full run: {ref[\'C2a\'][\'mixed_glm\'][\'F_prompt_glm\']:.2f}, "\n      f"{ref[\'C2a\'][\'mixed_glm\'][\'F_direct_glm\']:.2f})")\nprint("leave-one-template-out F_prompt:", {w: round(v["F_prompt"], 2) for w, v in route["leave_one_template_out"].items()})\nprint("leave-one-template-out F_direct:", {w: round(v["F_direct"], 2) for w, v in route["leave_one_template_out"].items()})\n\nper_task_tbl = pd.DataFrame({t: {"F_prompt": v["F_prompt"]["point"], "F_prompt ci95": "[{:.2f}, {:.2f}]".format(*v["F_prompt"]["ci95"]),\n                                 "F_direct": v["F_direct"]["point"], "F_direct ci95": "[{:.2f}, {:.2f}]".format(*v["F_direct"]["ci95"]),\n                                 "I": v["I"]["point"], "F_K0": v.get("F_K0", {}).get("point"),\n                                 "full F_prompt": ref["C2a"]["per_task"][t]["F_prompt"]["point"],\n                                 "full F_direct": ref["C2a"]["per_task"][t]["F_direct"]["point"]}\n                             for t, v in route["per_task"].items()}).T\nprint("\\nper gated task (template -> slot bootstrap 95%):")\nprint(per_task_tbl.to_string(float_format=lambda x: f"{x:.2f}"))'}
```

### [144] TOOL RESULT — NotebookEdit · 2026-10-26 10:36:07 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [145] ASSISTANT · 2026-10-26 10:36:19 UTC

```
Section 4.3: CRN flip tables and first divergence (analysis 9.3). The only change is that the n-grams come from the data instead of `predictions/ngrams.json`.
```

### [146] TOOL CALL — NotebookEdit · 2026-10-26 10:36:19 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': '58044007', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "### 4.3 Paired CRN evidence: flip tables, identical outputs, first divergence (9.3)\n\nArms of one slot read the same uniforms, so they can be compared **pair by pair** rather than only as shares.\n\n- **Flip table:** for each pair of arms, a 2×2 table counts slots by whether each arm wrote the default. An exact McNemar test runs on the discordant cells.\n- **Identical rate:** under CRN, two arms whose next-token distributions agree produce *exactly* the same tokens. So `d==b` being high means the direct-route arm behaves like the twin.\n- **First divergence:** the first generated token at which an arm leaves arm `b`'s token sequence. In the full run this is the first content token of the function body (median token 8-10).\n\n`crn_analysis()` is verbatim except that the frozen n-grams come from the data, not `predictions/ngrams.json`. Its loops still run over `k < 20` and skip slots that are absent from the subset."}
```

### [147] TOOL RESULT — NotebookEdit · 2026-10-26 10:36:19 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [148] TOOL CALL — NotebookEdit · 2026-10-26 10:36:37 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': '32d709ec', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '# ------------------------------------------------------------------------------------------------ 9.3\ndef crn_analysis(rows: list[dict[str, Any]], tasks: list[str]) -> dict[str, Any]:\n    idx = {(r["task"], r["template"], r["k"], r["arm"]): r for r in rows}\n    ngr = meta["ngrams"]  # original: read_json(PRED_DIR / "ngrams.json")\n    out = {}\n    for t in tasks:\n        D = default_of(t)\n        res: dict[str, Any] = {"flip_tables": {}, "identical": {}, "first_divergence": {}}\n        for X, Y in (("a", "c"), ("a", "d"), ("b", "d"), ("a", "K0"), ("c", "K0"), ("b", "V1"), ("b", "c")):\n            n = np.zeros((2, 2), int)\n            for w in TEMPLATE_IDS:\n                for k in range(20):\n                    rx, ry = idx.get((t, w, k, X)), idx.get((t, w, k, Y))\n                    if rx is None or ry is None or rx["label"] in EXCL or ry["label"] in EXCL:\n                        continue\n                    n[int(rx["label"] == D), int(ry["label"] == D)] += 1\n            if n.sum() == 0:\n                continue\n            b01, b10 = int(n[1, 0]), int(n[0, 1])\n            p = float(stats.binomtest(min(b01, b10), b01 + b10, 0.5).pvalue) if b01 + b10 > 0 else 1.0\n            res["flip_tables"][f"{X}-{Y}"] = {"table[X_banned][Y_banned]": n.tolist(), "X_only": b01, "Y_only": b10,\n                                              "mcnemar_exact_p": p, "n_pairs": int(n.sum())}\n        for X, Y in (("c", "a"), ("d", "b"), ("V1", "b"), ("K0", "a")):\n            same = [idx[(t, w, k, X)]["token_ids"] == idx[(t, w, k, Y)]["token_ids"] for w in TEMPLATE_IDS\n                    for k in range(20) if (t, w, k, X) in idx and (t, w, k, Y) in idx]\n            if same:\n                res["identical"][f"{X}=={Y}"] = float(np.mean(same))\n        g = ngr.get(t, {})\n        first_occ = []\n        for w in TEMPLATE_IDS:\n            for k in range(20):\n                rb = idx.get((t, w, k, "b"))\n                if rb and g.get("defined"):\n                    ids = rb["token_ids"]\n                    n_ = len(g["ids"])\n                    for i in range(len(ids) - n_ + 1):\n                        if ids[i:i + n_] == g["ids"]:\n                            first_occ.append(i)\n                            break\n        res["ngram_first_occurrence_in_b"] = {"median": float(np.median(first_occ)) if first_occ else None,\n                                               "n": len(first_occ)}\n        for X in ("a", "c", "d", "K0", "V1"):\n            divs, n_ident = [], 0\n            for w in TEMPLATE_IDS:\n                for k in range(20):\n                    rx, rb = idx.get((t, w, k, X)), idx.get((t, w, k, "b"))\n                    if rx is None or rb is None:\n                        continue\n                    x, b = rx["token_ids"], rb["token_ids"]\n                    m = min(len(x), len(b))\n                    d = next((i for i in range(m) if x[i] != b[i]), None)\n                    if d is None:\n                        if len(x) == len(b):\n                            n_ident += 1\n                            continue\n                        d = m\n                    divs.append(d)\n            if divs or n_ident:\n                res["first_divergence"][X] = {"median": float(np.median(divs)) if divs else None,\n                                              "iqr": [float(np.quantile(divs, .25)), float(np.quantile(divs, .75))] if divs else None,\n                                              "n_diverged": len(divs), "n_identical_to_b": n_ident, "values": divs}\n        out[t] = res\n    return out\n\n\ncrn = crn_analysis(bench_rows, STAGE_A)\nflip_rows = []\nfor t in gated:\n    for pair, ft in crn[t]["flip_tables"].items():\n        flip_rows.append({"task": t, "pair X-Y": pair, "X default only": ft["X_only"], "Y default only": ft["Y_only"],\n                          "both default": ft["table[X_banned][Y_banned]"][1][1], "neither": ft["table[X_banned][Y_banned]"][0][0],\n                          "McNemar exact p": ft["mcnemar_exact_p"]})\nprint(pd.DataFrame(flip_rows).pivot(index="task", columns="pair X-Y", values="McNemar exact p")\n      .to_string(float_format=lambda x: f"{x:.1e}"))\nprint("\\nflip tables (gated tasks): \'X default only\' vs \'Y default only\' are the discordant CRN slots")\nprint(pd.DataFrame(flip_rows).set_index(["task", "pair X-Y"]).to_string(float_format=lambda x: f"{x:.2g}"))\nident = pd.DataFrame({t: crn[t]["identical"] for t in gated}).T\nprint("\\nidentical-token rate between arms of the same slot:")\nprint(ident.to_string(float_format=lambda x: f"{x:.2f}"))\nfd = pd.DataFrame({t: {X: v["median"] for X, v in crn[t]["first_divergence"].items()} for t in gated}).T\nfd["n-gram first occurrence in b"] = [crn[t]["ngram_first_occurrence_in_b"]["median"] for t in gated]\nprint("\\nmedian first token at which arm X leaves arm b (CRN partner):")\nprint(fd.to_string(float_format=lambda x: f"{x:.1f}"))'}
```

### [149] TOOL RESULT — NotebookEdit · 2026-10-26 10:36:37 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [150] ASSISTANT · 2026-10-26 10:36:47 UTC

```
Section 4.4: where each arm lands instead of the default (analysis 9.4).
```

### [151] TOOL CALL — NotebookEdit · 2026-10-26 10:36:47 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': 'e2b90bf7', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "### 4.4 Where does each route land? (9.4)\n\nA ban does not only *subtract* the default. It *substitutes* a specific alternative, for example T06's `hash_set` gives way to `index_marking` (negating visited entries).\n\nFor each arm, `landing_by_route()` collects the non-default mechanisms and compares their distribution with the full ban's (arm `a`) by Jensen-Shannon divergence. The comparison is against a resampling null: template-then-program resamples of arm `a` at the same size, with `LANDING_N_REP` resamples (original 2000). `within_null = True` means the route lands where the full ban lands."}
```

### [152] TOOL RESULT — NotebookEdit · 2026-10-26 10:36:48 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [153] TOOL CALL — NotebookEdit · 2026-10-26 10:37:01 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': '1798f0d7', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'def js_div(p: np.ndarray, q: np.ndarray) -> float:\n    p = p / p.sum()\n    q = q / q.sum()\n    m = 0.5 * (p + q)\n\n    def kl(a, b):\n        mask = a > 0\n        return float((a[mask] * np.log2(a[mask] / b[mask])).sum())\n\n    return 0.5 * kl(p, m) + 0.5 * kl(q, m)\n\n\ndef dist_vec(counts: dict[str, int], cats: list[str], pseudo: float = 0.5) -> np.ndarray:\n    return np.array([counts.get(c, 0) + pseudo for c in cats], float)\n\n\n# ------------------------------------------------------------------------------------------------ 9.4\ndef landing_null(rows_a: list[dict[str, Any]], task: str, n: int, cats: list[str], n_rep: int = LANDING_N_REP,\n                 seed: int = RNG_SEED + 2) -> float:  # original default: n_rep = 2000\n    """q95 of JS(resample of a\'s non-default attempts at size n, a) -- resampling template then program."""\n    D = default_of(task)\n    nond = [r for r in rows_a if r["label"] not in EXCL and r["label"] != D]\n    if not nond or n <= 0:\n        return float("nan")\n    byw = collections.defaultdict(list)\n    for r in nond:\n        byw[r["template"]].append(r["label"])\n    ws = sorted(byw)\n    full = dist_vec(collections.Counter(r["label"] for r in nond), cats)\n    rng = np.random.default_rng(seed)\n    vals = []\n    for _ in range(n_rep):\n        labs = []\n        for _ in range(n):\n            w = ws[rng.integers(len(ws))]\n            labs.append(byw[w][rng.integers(len(byw[w]))])\n        vals.append(js_div(dist_vec(collections.Counter(labs), cats), full))\n    return float(np.quantile(vals, 0.95))\n\n\ndef landing_by_route(rows: list[dict[str, Any]], tasks: list[str]) -> dict[str, Any]:\n    g = by(rows, "task", "arm")\n    out = {}\n    for t in tasks:\n        D = default_of(t)\n        cats = survivors(t)\n        ra = g.get((t, "a"), [])\n        ca = collections.Counter(r["label"] for r in ra if r["label"] not in EXCL and r["label"] != D)\n        res = {"a": {"counts": dict(ca), "modal": ca.most_common(1)[0][0] if ca else None}}\n        for X in ("c", "d", "K0", "V1"):\n            rx = g.get((t, X), [])\n            cx = collections.Counter(r["label"] for r in rx if r["label"] not in EXCL and r["label"] != D)\n            n = sum(cx.values())\n            if not n or not ca:\n                continue\n            js = js_div(dist_vec(cx, cats), dist_vec(ca, cats))\n            q95 = landing_null(ra, t, n, cats)\n            res[X] = {"counts": dict(cx), "modal": cx.most_common(1)[0][0], "same_modal_as_a": cx.most_common(1)[0][0] == res["a"]["modal"],\n                      "JS_vs_a": js, "null_q95": q95, "within_null": bool(js < q95)}\n        out[t] = res\n    return out\n\n\nt0 = time.time()\nland = landing_by_route(bench_rows, STAGE_A)\nprint(f"landing analysis: {time.time() - t0:.1f}s (LANDING_N_REP={LANDING_N_REP})")\nfor t in gated:\n    print(f"\\n{t} (default {DEFAULT[t]}; catalogue {catalogue(t)})")\n    print(f"  arm a  : non-default landings {land[t][\'a\'][\'counts\']}")\n    for X in ("c", "d", "K0"):\n        if X in land[t]:\n            v = land[t][X]\n            print(f"  arm {X:3s}: {v[\'counts\']}  modal={v[\'modal\']} (same as a: {v[\'same_modal_as_a\']}); "\n                  f"JS vs a = {v[\'JS_vs_a\']:.3f}, null q95 = {v[\'null_q95\']:.3f} -> within null: {v[\'within_null\']}")\n        else:\n            print(f"  arm {X:3s}: no non-default attempt")'}
```

### [154] TOOL RESULT — NotebookEdit · 2026-10-26 10:37:02 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [155] ASSISTANT · 2026-10-26 10:37:12 UTC

```
Section 4.5: C2c, scoring the frozen commit-#2 veto classes against the demo's per-task `F_direct`.
```

### [156] TOOL CALL — NotebookEdit · 2026-10-26 10:37:12 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': '99839706', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "### 4.5 C2c: does veto sufficiency predict the direct route? (9.5)\n\nBefore any bench ban sample was drawn, commit #2 froze one prediction per task. It comes from the **one-shot veto** arm V1: the neutral twin, but with the default's frozen distinctive n-gram (e.g. T06 `' set'`) masked once. `V_t` is the share of V1 attempts that leave the default.\n\nTasks with `V_t < 0.5` are classed `HIGH_DIRECT`, a prediction that `F_direct >= 0.25`. Every task got that class, because the frozen n-gram rule picked zero-collateral identifier and structural tokens. The model just renames them.\n\n`c2c_analysis()` scores these frozen classes against the per-task `F_direct` from 4.2. It also tests Spearman ρ(V_t, F_direct) with a one-sided permutation test (`N_PERM`, original 100,000).\n\nIt is verbatim, except that the rho bootstrap uses `N_BOOT_RHO` reps (original 4000). The frozen predictions are passed in through its `c2c` argument."}
```

### [157] TOOL RESULT — NotebookEdit · 2026-10-26 10:37:12 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [158] TOOL CALL — NotebookEdit · 2026-10-26 10:37:30 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': '16e0dbee', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '# ------------------------------------------------------------------------------------------------ 9.5 / 9.6\ndef c2c_analysis(route: dict[str, Any], gated: list[str], c2c: dict[str, Any] | None = None) -> dict[str, Any]:\n    if c2c is None:\n        if not (PRED_DIR / "c2c.json").exists():\n            return {"decision": "NOT_AVAILABLE (commit #2 missing)", "hit_fraction": float("nan"),\n                    "spearman_rho": float("nan"), "rows": []}\n        c2c = read_json(PRED_DIR / "c2c.json")\n    per = route.get("per_task", {})\n    rows = []\n    for t in STAGE_A:\n        cls = c2c.get(t, {}).get("class")\n        Fd = per.get(t, {}).get("F_direct", {}).get("point")\n        ci = per.get(t, {}).get("F_direct", {}).get("ci95")\n        hit = None\n        if t in gated and Fd is not None and cls in ("LOW_DIRECT", "HIGH_DIRECT"):\n            hit = bool(Fd <= THRESHOLDS["pred_low_direct_F"]) if cls == "LOW_DIRECT" else bool(Fd >= THRESHOLDS["pred_high_direct_F"])\n        rows.append({"task": t, "gated": t in gated, "V": c2c.get(t, {}).get("V"), "class": cls, "F_direct": Fd,\n                     "F_direct_ci95": ci, "hit": hit, "fire_rate": c2c.get(t, {}).get("fire_rate"),\n                     "V_fired": c2c.get(t, {}).get("V_fired")})\n    scored = [r for r in rows if r["hit"] is not None]\n    hf = float(np.mean([r["hit"] for r in scored])) if scored else float("nan")\n    pts = [(r["V"], r["F_direct"]) for r in rows if r["gated"] and r["V"] is not None and r["F_direct"] is not None\n           and np.isfinite(r["V"]) and np.isfinite(r["F_direct"])]\n    rho = p_perm = float("nan")\n    rho_ci = [float("nan"), float("nan")]\n    if len(pts) >= 3:\n        v = np.array([p[0] for p in pts])\n        f = np.array([p[1] for p in pts])\n        rho = float(stats.spearmanr(v, f).statistic)\n        rng = np.random.default_rng(RNG_SEED + 1)\n        rv, rf = stats.rankdata(v), stats.rankdata(f)\n        perm = np.array([np.corrcoef(rv, rf[rng.permutation(len(rf))])[0, 1] for _ in range(N_PERM)])\n        p_perm = float(np.mean(perm <= rho)) if np.isfinite(rho) else float("nan")\n        bs = []\n        for _ in range(N_BOOT_RHO):  # original: range(4000)\n            ii = rng.integers(0, len(v), len(v))\n            if len(set(ii)) > 2:\n                r_ = stats.spearmanr(v[ii], f[ii]).statistic\n                if np.isfinite(r_):\n                    bs.append(r_)\n        rho_ci = pct_ci(np.array(bs)) if bs else rho_ci\n    if not scored or not np.isfinite(rho):\n        decision = "INCONCLUSIVE (insufficient classed gated tasks)"\n    elif hf >= THRESHOLDS["c2c_hit_fraction"] and rho < 0 and p_perm < THRESHOLDS["c2c_alpha"]:\n        decision = "SUPPORTED"\n    elif rho >= 0 or hf < THRESHOLDS["c2c_disconfirm_hit"]:\n        decision = "DISCONFIRMED"\n    else:\n        decision = "INCONCLUSIVE"\n    return {"rows": rows, "n_scored": len(scored), "hit_fraction": hf, "spearman_rho": rho, "perm_p_one_sided": p_perm,\n            "rho_task_bootstrap_ci95": rho_ci, "n_points": len(pts), "decision": decision,\n            "rule": "SUPPORTED if hit fraction >= 2/3 AND rho < 0 with permutation p < 0.05; DISCONFIRMED if rho >= 0 "\n                    "or hit fraction < 1/2; else INCONCLUSIVE (committed in commit #1)"}\n\n\nt0 = time.time()\nc2c = c2c_analysis(route, gated, c2c=meta["c2c_predictions"])  # frozen predictions/c2c.json (commit #2)\nprint(f"C2c: {time.time() - t0:.1f}s (N_PERM={N_PERM}, N_BOOT_RHO={N_BOOT_RHO})")\nprint(pd.DataFrame([r for r in c2c["rows"] if r["gated"]]).set_index("task")[["V", "class", "F_direct", "hit", "fire_rate"]]\n      .to_string(float_format=lambda x: f"{x:.2f}"))\nprint(f"\\nhit fraction {c2c[\'hit_fraction\']:.2f}, Spearman rho {c2c[\'spearman_rho\']:.2f} (one-sided permutation p "\n      f"{c2c[\'perm_p_one_sided\']:.2f}, task-bootstrap 95% {np.round(c2c[\'rho_task_bootstrap_ci95\'], 2).tolist()}) "\n      f"-> C2c {c2c[\'decision\']}")\nprint(f"full run: hit fraction {ref[\'C2c\'][\'hit_fraction\']:.2f}, rho {ref[\'C2c\'][\'spearman_rho\']:.2f}, "\n      f"p {ref[\'C2c\'][\'perm_p_one_sided\']:.2f} -> {ref[\'C2c\'][\'decision\']}")'}
```

### [159] TOOL RESULT — NotebookEdit · 2026-10-26 10:37:30 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [160] ASSISTANT · 2026-10-26 10:37:40 UTC

```
A short summary cell reproducing `run_analysis()`'s result dict and log line:
```

### [161] TOOL CALL — NotebookEdit · 2026-10-26 10:37:40 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': 'b6c7d5b8', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': '### 4.6 Analysis result (end of `run_analysis()`)\n\n`run_analysis()` collects everything into one result dict, which the original writes to `results/analysis.json` and the per-section files, then logs a one-line summary. Some analyses need arms or inputs that are not in the `route_arms` subset, so they are not reproduced here:\n- C2b sensitivity, which needs the V1 rows.\n- Prefill P_open, which needs the prefill rows.\n- The T1/T2 path screen, which needs the exp8/9/12 rows.\n- The C1 forecast rows.\n- The log-prob readout, which needs `token_lp/*.npz`.\n- Controls, which need the placebo and K0b rows.'}
```

### [162] TOOL RESULT — NotebookEdit · 2026-10-26 10:37:40 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [163] TOOL CALL — NotebookEdit · 2026-10-26 10:37:40 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': 'b6c7d5b8', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'PLACEHOLDER2'}
```

### [164] TOOL RESULT — NotebookEdit · 2026-10-26 10:37:40 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [165] ASSISTANT · 2026-10-26 10:37:48 UTC

```
I repeated the parallel-insert mistake, so the placeholder landed before the markdown. Deleting it, and from here on I'll insert strictly one cell per call:
```

### [166] TOOL CALL — NotebookEdit · 2026-10-26 10:37:48 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': 'b6dc635b', 'edit_mode': 'delete', 'new_source': ''}
```

### [167] TOOL RESULT — NotebookEdit · 2026-10-26 10:37:48 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [168] TOOL CALL — NotebookEdit · 2026-10-26 10:37:54 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': 'ca67a434', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'res = {"gated": gated, "gate": gate, "shares": shares, "route": route, "route_nongated_descriptive": route_ng,\n       "crn": crn, "landing_by_route": land, "c2c": c2c, "n_rows": len(rows)}\nlogger.info(f"analysis: gated={gated}; C2a={route.get(\'verdict\')} point={ {k: round(v, 3) for k, v in route.get(\'point\', {}).items()} }; "\n            f"C2c={c2c[\'decision\']} (hit {c2c[\'hit_fraction\']}, rho {c2c[\'spearman_rho\']:.3f})")\nprint("descriptive route fractions on non-gated tasks (ban mostly fails there; s_b - s_a ~ 0 makes F unstable):")\nprint(pd.DataFrame({t: {k: v[k]["point"] for k in ("F_prompt", "F_direct")} for t, v in route_ng.items()}).T\n      .to_string(float_format=lambda x: f"{x:.2f}"))'}
```

### [169] TOOL RESULT — NotebookEdit · 2026-10-26 10:37:54 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [170] ASSISTANT · 2026-10-26 10:38:12 UTC

```
Section 5: the engine. First the explanatory markdown.
```

### [171] TOOL CALL — NotebookEdit · 2026-10-26 10:38:12 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': 'aa71d527', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': '## 5. The engine: CRN-coupled KV-splice sampling (`src/engine.py`, `src/gpu.py`)\n\nThis section runs the code that *produced* the samples, on one CRN slot set: **T06 (find the duplicate), template W1, slots k = 0..`ENGINE_N_SLOTS`-1**. It uses the frozen prompt ids (`prompts/prompts.jsonl`). The condition segment sits at positions `[p0, p1)`, just after `<|im_start|>user\\n`, and the task specification follows it.\n\n1. **Prefill.** The ban prompt and its neutral twin are each prefilled once. That gives a per-layer `(K, V)` cache and the logits `R` at the read position.\n2. **Arms are caches** (`gpu.Worker.arm_state`):\n   - `c = splice(twin, ban, p1)`: twin states on `[0, p1)`, ban states on `[p1, P)`, and the ban\'s read logits.\n   - `d` is the reverse.\n   - `K0 = drop_span(ban, p0, p1)` removes the condition span from the cache. Keys keep their RoPE rotation and generated queries keep positions `P + step`, so this equals masking the span (test U3).\n3. **CRN sampling** (`engine.sample`). Each slot has one uniform stream, `u_stream("beh", task, w, k)`, keyed by exp8\'s sha256 seed. At every step each row draws `token = first index whose CDF >= u[step]`. Two arms whose next-token distributions agree therefore pick **the same token**, so arms diverge exactly where their distributions differ. A row stops once its first code fence closes.\n4. **Batching.** Rows are grouped by shape class `(task, cache length, first position)`. K0\'s cache is shorter, so it runs in its own batch, as on the GPU.\n\nTwo changes only, for CPU:\n- **Loader:** `load_model()` loads `ENGINE_MODEL_ID` on `ENGINE_DEVICE`, without `device_map` or the VRAM cap.\n- **Batch size:** a batch holds the demo\'s rows instead of B = 40 padded rows.\n\n> **Scale note.** Qwen3-0.6B is a *mechanics stand-in*. It shares Qwen3-8B\'s tokenizer and chat template, so the frozen prompt ids and uniforms apply unchanged, but it is far below the study\'s ≥1B model floor and does not reliably follow these bans. The cells below therefore print the **Qwen3-8B rows of the same CRN slots** (same uniforms, same splices) beside the live output. For example, on T06/W1 the 8B arm `d` reproduces the ban\'s `index_marking` program token for token, while `c` and `K0` fall back to the `hash_set` default.'}
```

### [172] TOOL RESULT — NotebookEdit · 2026-10-26 10:38:12 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [173] ASSISTANT · 2026-10-26 10:38:26 UTC

```
One overstatement to fix: the 8B arm `d` matches arm `a` token-for-token only at k=1 (at k=2 it writes a different `index_marking` program). Correcting the note:
```

### [174] TOOL CALL — NotebookEdit · 2026-10-26 10:38:26 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': '8231e090', 'edit_mode': 'replace', 'cell_type': 'markdown', 'new_source': '## 5. The engine: CRN-coupled KV-splice sampling (`src/engine.py`, `src/gpu.py`)\n\nThis section runs the code that *produced* the samples, on one CRN slot set: **T06 (find the duplicate), template W1, slots k = 0..`ENGINE_N_SLOTS`-1**. It uses the frozen prompt ids (`prompts/prompts.jsonl`). The condition segment sits at positions `[p0, p1)`, just after `<|im_start|>user\\n`, and the task specification follows it.\n\n1. **Prefill.** The ban prompt and its neutral twin are each prefilled once. That gives a per-layer `(K, V)` cache and the logits `R` at the read position.\n2. **Arms are caches** (`gpu.Worker.arm_state`):\n   - `c = splice(twin, ban, p1)`: twin states on `[0, p1)`, ban states on `[p1, P)`, and the ban\'s read logits.\n   - `d` is the reverse.\n   - `K0 = drop_span(ban, p0, p1)` removes the condition span from the cache. Keys keep their RoPE rotation and generated queries keep positions `P + step`, so this equals masking the span (test U3).\n3. **CRN sampling** (`engine.sample`). Each slot has one uniform stream, `u_stream("beh", task, w, k)`, keyed by exp8\'s sha256 seed. At every step each row draws `token = first index whose CDF >= u[step]`. Two arms whose next-token distributions agree therefore pick **the same token**, so arms diverge exactly where their distributions differ. A row stops once its first code fence closes.\n4. **Batching.** Rows are grouped by shape class `(task, cache length, first position)`. K0\'s cache is shorter, so it runs in its own batch, as on the GPU.\n\nTwo changes only, for CPU:\n- **Loader:** `load_model()` loads `ENGINE_MODEL_ID` on `ENGINE_DEVICE`, without `device_map` or the VRAM cap.\n- **Batch size:** a batch holds the demo\'s rows instead of B = 40 padded rows.\n\n> **Scale note.** Qwen3-0.6B is a *mechanics stand-in*. It shares Qwen3-8B\'s tokenizer and chat template, so the frozen prompt ids and uniforms apply unchanged, but it is far below the study\'s ≥1B model floor and does not reliably follow these bans. The cells below therefore print the **Qwen3-8B rows of the same CRN slots** (same uniforms, same splices) beside the live output.\n>\n> On T06/W1 at k = 1 and 2, the 8B arm `d` (ban condition read directly) lands on the ban\'s `index_marking` program, and at k = 1 it is token-for-token arm `a`\'s program. Arms `c` and `K0` fall back to the twin\'s `hash_set` default.'}
```

### [175] TOOL RESULT — NotebookEdit · 2026-10-26 10:38:26 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [176] ASSISTANT · 2026-10-26 10:38:46 UTC

```
Engine cell E1: the knockout-capable attention and fence detection, verbatim from `engine.py`.
```

### [177] TOOL CALL — NotebookEdit · 2026-10-26 10:38:46 UTC

````
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': '8231e090', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '# ---- src/engine.py: knockout-capable attention + fence detection (verbatim)\nKO: dict[str, Any] = {"active": False, "p0": 0, "p1": 0, "P": 0, "g_lo": 0, "g_hi": 10 ** 9, "layers": None,\n                      "rowmask": None}\nRECORD: dict[str, Any] = {"on": False, "weights": {}}\n_REGISTERED = False\n\n# bench extractor (exp11 harness.FENCE_RE) and exp8 suite extractor (closed python block)\nBENCH_FENCE = re.compile(r"```[ \\t]*(?:python3?|py|Python)?[ \\t]*\\n(.*?)```", re.S)\nPATH_FENCE = re.compile(r"```(?:python|py|Python|python3)[ \\t]*\\n(.*?)```", re.S)\n\n\ndef fence_closed_bench(text: str) -> bool:\n    return BENCH_FENCE.search(text) is not None\n\n\ndef fence_closed_path(text: str) -> bool:\n    m = PATH_FENCE.search(text)\n    return bool(m and m.group(1).strip())\n\n\n# ------------------------------------------------------------------------------------------------ attention\ndef _ko_on(module: Any) -> bool:\n    return bool(KO["active"]) and (KO["layers"] is None or module.layer_idx in KO["layers"])\n\n\ndef _ko_allowed(q_len: int, k_len: int, device: torch.device) -> torch.Tensor:\n    offset = k_len - q_len\n    qpos = torch.arange(offset, k_len, device=device)\n    kpos = torch.arange(k_len, device=device)\n    allowed = kpos[None, :] <= qpos[:, None]\n    g = qpos - int(KO["P"])\n    qblock = (g >= int(KO["g_lo"])) & (g < int(KO["g_hi"]))\n    kblock = (kpos >= int(KO["p0"])) & (kpos < int(KO["p1"]))\n    return allowed & ~(qblock[:, None] & kblock[None, :])\n\n\ndef _combine(allowed: torch.Tensor, attention_mask: torch.Tensor | None, k_len: int) -> torch.Tensor:\n    allowed = allowed[None, None]\n    if attention_mask is not None:\n        am = attention_mask[:, :, :, :k_len]\n        if am.dtype == torch.bool:\n            allowed = allowed & am\n        else:\n            allowed = allowed & (am == 0)\n    return allowed\n\n\ndef ko_sdpa(module, query, key, value, attention_mask, **kwargs):\n    from transformers.integrations.sdpa_attention import sdpa_attention_forward\n\n    rm = KO.get("rowmask")\n    if rm is not None:  # sampling: one explicit [B,1,q,k] boolean mask for every layer (q = 1 at decode)\n        kwargs.pop("is_causal", None)\n        return sdpa_attention_forward(module, query, key, value, rm[:, :, :, :key.shape[2]], is_causal=False, **kwargs)\n    if _ko_on(module):\n        q_len, k_len = query.shape[2], key.shape[2]\n        allowed = _combine(_ko_allowed(q_len, k_len, query.device), attention_mask, k_len)\n        kwargs.pop("is_causal", None)\n        return sdpa_attention_forward(module, query, key, value, allowed, is_causal=False, **kwargs)\n    return sdpa_attention_forward(module, query, key, value, attention_mask, **kwargs)\n\n\ndef ko_eager(module, query, key, value, attention_mask, **kwargs):\n    """Eager twin used only by the knockout-correctness test (U3); records attention probabilities."""\n    from transformers.models.qwen3.modeling_qwen3 import eager_attention_forward\n\n    q_len, k_len = query.shape[2], key.shape[2]\n    if _ko_on(module):\n        allowed = _combine(_ko_allowed(q_len, k_len, query.device), attention_mask, k_len)\n    else:\n        base = torch.ones(q_len, k_len, dtype=torch.bool, device=query.device).tril(k_len - q_len)\n        allowed = _combine(base, attention_mask, k_len)\n    fmask = torch.zeros(allowed.shape, dtype=query.dtype, device=query.device)\n    fmask = fmask.masked_fill(~allowed, torch.finfo(query.dtype).min)\n    out, w = eager_attention_forward(module, query, key, value, fmask, **kwargs)\n    if RECORD["on"]:\n        RECORD["weights"][module.layer_idx] = w.detach().float().cpu()\n    return out, w\n\n\ndef register() -> None:\n    global _REGISTERED\n    if _REGISTERED:\n        return\n    from transformers import AttentionInterface\n    from transformers.masking_utils import AttentionMaskInterface, eager_mask, sdpa_mask\n\n    AttentionInterface.register("ko_sdpa", ko_sdpa)\n    AttentionInterface.register("ko_eager", ko_eager)\n    AttentionMaskInterface.register("ko_sdpa", sdpa_mask)\n    AttentionMaskInterface.register("ko_eager", eager_mask)\n    _REGISTERED = True'}
````

### [178] TOOL RESULT — NotebookEdit · 2026-10-26 10:38:46 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [179] ASSISTANT · 2026-10-26 10:39:00 UTC

```
Engine cell E2: `load_model` (the device change only) and the cache operations, verbatim.
```

### [180] TOOL CALL — NotebookEdit · 2026-10-26 10:39:00 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': 'b6497aad', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'def load_model(vram_fraction: float = 0.95):\n    from transformers import AutoModelForCausalLM, AutoTokenizer\n\n    register()\n    t0 = time.time()\n    # original: model_path() = Qwen/Qwen3-8B at MODEL_REVISION, dtype=torch.bfloat16, device_map={"": 0},\n    # then torch.cuda.set_per_process_memory_fraction(vram_fraction, 0)\n    tok = AutoTokenizer.from_pretrained(ENGINE_MODEL_ID, revision=ENGINE_REVISION)\n    model = AutoModelForCausalLM.from_pretrained(ENGINE_MODEL_ID, revision=ENGINE_REVISION, dtype=ENGINE_DTYPE,\n                                                 attn_implementation="ko_sdpa")\n    model.to(ENGINE_DEVICE)\n    model.eval()\n    if ENGINE_DEVICE == "cuda":\n        torch.cuda.set_per_process_memory_fraction(vram_fraction, 0)\n    logger.info(f"HF model {ENGINE_MODEL_ID} loaded in {time.time() - t0:.0f}s; attn={model.config._attn_implementation}; "\n                f"device={model.device}; dtype={model.dtype}")\n    return tok, model\n\n\n# ------------------------------------------------------------------------------------------------ caches\ndef _kv_list(cache: Any) -> list[tuple[torch.Tensor, torch.Tensor]]:\n    if hasattr(cache, "layers"):\n        return [(L.keys, L.values) for L in cache.layers]\n    return list(zip(cache.key_cache, cache.value_cache))\n\n\ndef build_cache(kv: list[tuple[torch.Tensor, torch.Tensor]], batch: int = 1):\n    from transformers.cache_utils import DynamicCache\n\n    cache = DynamicCache()\n    for l, (K, V) in enumerate(kv):\n        if K.shape[0] != batch:\n            K = K.expand(batch, -1, -1, -1)\n            V = V.expand(batch, -1, -1, -1)\n        cache.update(K.contiguous(), V.contiguous(), l)\n    return cache\n\n\n@torch.no_grad()\ndef prefill(model: Any, ids: list[int]) -> dict[str, Any]:\n    """Returns {\'kv\': per-layer (K, V) [1, 8, P, 128] on GPU, \'r_logits\': float32 [V], \'P\'}."""\n    from transformers.cache_utils import DynamicCache\n\n    inp = torch.tensor([ids], device=model.device)\n    cache = DynamicCache()\n    out = model.model(input_ids=inp, past_key_values=cache, use_cache=True)\n    r_logits = model.lm_head(out.last_hidden_state[:, -1]).float()[0]\n    kv = [(K.clone(), V.clone()) for K, V in _kv_list(cache)]\n    del cache, out\n    return {"kv": kv, "r_logits": r_logits, "P": len(ids)}\n\n\ndef splice(kv_a: list, kv_b: list, cut: int) -> list:\n    """Positions [0, cut) from A and [cut, P) from B, every layer."""\n    return [(torch.cat([Ka[:, :, :cut], Kb[:, :, cut:]], dim=2), torch.cat([Va[:, :, :cut], Vb[:, :, cut:]], dim=2))\n            for (Ka, Va), (Kb, Vb) in zip(kv_a, kv_b)]\n\n\ndef drop_span(kv: list, p0: int, p1: int) -> list:\n    """K0 without a mask: remove the condition span [p0, p1) from every layer\'s cache. Keys carry their RoPE rotation\n    from prefill and generated queries keep position ids P + step, so attention of every generated query over the\n    remaining keys equals exp8\'s masked knockout (softmax renormalises over the unmasked keys) -- see test U3."""\n    return [(torch.cat([K[:, :, :p0], K[:, :, p1:]], dim=2), torch.cat([V[:, :, :p0], V[:, :, p1:]], dim=2))\n            for K, V in kv]'}
```

### [181] TOOL RESULT — NotebookEdit · 2026-10-26 10:39:00 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [182] ASSISTANT · 2026-10-26 10:39:24 UTC

```
Engine cell E3: the CRN sampler (`u_stream`, inverse-CDF draw, veto helpers, `sample`), verbatim.
```

### [183] TOOL CALL — NotebookEdit · 2026-10-26 10:39:24 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': 'b5e86edd', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '# ------------------------------------------------------------------------------------------------ sampling\ndef u_stream(*key: Any, n: int = MAX_NEW_TOKENS) -> np.ndarray:\n    return np.random.Generator(np.random.PCG64(stable_seed(*key))).random(n)\n\n\ndef _inverse_cdf(probs: torch.Tensor, u: torch.Tensor) -> torch.Tensor:\n    cdf = probs.cumsum(dim=-1)\n    cdf = cdf / cdf[:, -1:]\n    tok = torch.searchsorted(cdf, u[:, None].to(cdf.dtype)).squeeze(-1)\n    return tok.clamp_(max=probs.shape[-1] - 1)\n\n\ndef _completing_ids(gen: list[int], ngrams: list[list[int]]) -> set[int]:\n    """Ids that would complete any n-gram given the row\'s generated tail."""\n    out = set()\n    for g in ngrams:\n        n = len(g)\n        if n == 1 or (len(gen) >= n - 1 and gen[len(gen) - (n - 1):] == g[:-1]):\n            out.add(int(g[-1]))\n    return out\n\n\n@torch.no_grad()\ndef sample(model: Any, rows: list[dict[str, Any]], max_new: int = MAX_NEW_TOKENS, temperature: float = 1.0,\n           tick_ids: set[int] | None = None, decode: Callable[[list[int]], str] | None = None,\n           prune_after: int | None = None) -> list[dict[str, Any]]:\n    """rows: [{\'kv\': per-layer (K,V) [1,8,P,128], \'r_logits\': [V], \'u\': np.ndarray[max_new],\n               optional \'u2\': np.ndarray (veto redraw stream), \'veto\': {\'mode\': \'oneshot\'|\'persistent\',\n               \'ngrams\': [[ids]]}, \'ko\': (p0, p1) or None, \'stop\': \'bench\'|\'path\'|None, \'prefix_text\': str}]\n    All rows share P. One uniform per (row, step); token = first index whose CDF >= u. Finished rows stay in the batch\n    (fed <|im_end|>) so the shape is constant; prune_after (memory guard) drops finished rows after that step."""\n    B = len(rows)\n    P = rows[0]["kv"][0][0].shape[2]          # cache length (shorter than the prompt for span-dropped K0 rows)\n    pos0 = int(rows[0].get("pos0", P))        # position id of the first generated token (= prompt length)\n    assert all(r["kv"][0][0].shape[2] == P and int(r.get("pos0", P)) == pos0 for r in rows)\n    dev = model.device\n    kv = [(torch.cat([r["kv"][l][0] for r in rows], 0), torch.cat([r["kv"][l][1] for r in rows], 0))\n          for l in range(len(rows[0]["kv"]))]\n    cache = build_cache(kv, B)\n    del kv\n    # explicit per-row mask only in batches that hold knockout rows (an explicit mask disables SDPA\'s native GQA\n    # path, so knockout batches run a different kernel -- K0 is CRN-coupled to the other arms only approximately,\n    # exactly as in exp8); every other batch runs stock SDPA with no mask\n    rowmask = None\n    if any(r.get("ko") for r in rows):\n        rowmask = torch.ones((B, 1, 1, P + max_new + 1), dtype=torch.bool, device=dev)\n        for i, r in enumerate(rows):\n            if r.get("ko"):\n                p0, p1 = r["ko"]\n                rowmask[i, :, :, p0:p1] = False\n    U = torch.tensor(np.stack([r["u"][:max_new] for r in rows]), dtype=torch.float64, device=dev)\n    logits = torch.stack([r["r_logits"] for r in rows]).double()\n    alive = list(range(B))\n    toks: list[list[int]] = [[] for _ in range(B)]\n    lps: list[list[float]] = [[] for _ in range(B)]\n    finish = ["length"] * B\n    done: set[int] = set()\n    veto = [r.get("veto") for r in rows]\n    fired = [False] * B\n    fire_step: list[int | None] = [None] * B\n    n_redraw = [0] * B\n    redraw_steps: list[list[int]] = [[] for _ in range(B)]\n    n_compl = [0] * B\n    pruned_at = None\n    step = 0\n    while True:\n        probs = torch.softmax(logits / temperature, dim=-1)\n        nxt_t = _inverse_cdf(probs, U[alive, step])\n        nxt = nxt_t.tolist()\n        # vetoes (rare events; handled per row on the CPU side)\n        for j, r in enumerate(alive):\n            v = veto[r]\n            if v is None or r in done:\n                continue\n            comp = _completing_ids(toks[r], v["ngrams"])\n            if not comp or nxt[j] not in comp:\n                continue\n            n_compl[r] += 1\n            if v["mode"] == "oneshot":\n                if fired[r]:\n                    continue\n                mask_ids = {nxt[j]}\n            else:\n                mask_ids = comp\n            p = probs[j].clone()\n            p[list(mask_ids)] = 0.0\n            if float(p.sum()) <= 0:\n                continue\n            u2 = float(rows[r]["u2"][n_redraw[r]])\n            nxt[j] = int(_inverse_cdf((p / p.sum())[None], torch.tensor([u2], dtype=torch.float64, device=dev))[0])\n            n_redraw[r] += 1\n            redraw_steps[r].append(step)\n            if not fired[r]:\n                fired[r] = True\n                fire_step[r] = step\n        nxt_dev = torch.tensor(nxt, device=dev)\n        plp = torch.log(probs.gather(-1, nxt_dev[:, None])[:, 0]).tolist()\n        keep = []\n        for j, (r, t) in enumerate(zip(alive, nxt)):\n            if r in done:\n                continue\n            toks[r].append(int(t))\n            lps[r].append(float(plp[j]))\n            if t in (IM_END, ENDOFTEXT):\n                finish[r] = "stop"\n                done.add(r)\n                continue\n            st = rows[r].get("stop")\n            if st and tick_ids is not None and decode is not None and int(t) in tick_ids:\n                text = rows[r].get("prefix_text", "") + decode(toks[r])\n                if (fence_closed_bench(text) if st == "bench" else fence_closed_path(text)):\n                    finish[r] = "fence"\n                    done.add(r)\n                    continue\n            if len(toks[r]) < max_new:\n                keep.append(j)\n            else:\n                done.add(r)\n        if not keep:\n            break\n        if prune_after is not None and step >= prune_after and len(keep) < len(alive):\n            idx = torch.tensor(keep, device=dev)\n            if hasattr(cache, "batch_select_indices"):\n                cache.batch_select_indices(idx)\n            else:\n                kvn = [(K[idx], V[idx]) for K, V in _kv_list(cache)]\n                cache = build_cache(kvn, len(keep))\n            if rowmask is not None:\n                rowmask = rowmask[idx]\n            alive = [alive[j] for j in keep]\n            nxt = [nxt[j] for j in keep]\n            if pruned_at is None:\n                pruned_at = step\n        else:\n            nxt = [IM_END if r in done else t for r, t in zip(alive, nxt)]\n        inp = torch.tensor(nxt, device=dev)[:, None]\n        pos = torch.full((len(alive), 1), pos0 + step, device=dev, dtype=torch.long)\n        KO["rowmask"] = rowmask\n        try:\n            h = model.model(input_ids=inp, past_key_values=cache, position_ids=pos, use_cache=True).last_hidden_state\n        finally:\n            KO["rowmask"] = None\n        logits = model.lm_head(h[:, -1]).double()\n        step += 1\n    del cache\n    return [{"token_ids": toks[r], "finish_reason": finish[r], "n_tokens": len(toks[r]),\n             "logprob_sum": float(np.sum(lps[r])), "veto_fired": fired[r], "fire_step": fire_step[r],\n             "n_redraws": n_redraw[r], "redraw_steps": redraw_steps[r], "n_completions_drawn": n_compl[r],\n             "pruned_at": pruned_at, "steps": step} for r in range(B)]'}
```

### [184] TOOL RESULT — NotebookEdit · 2026-10-26 10:39:24 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [185] ASSISTANT · 2026-10-26 10:40:18 UTC

```
Engine cell E4 needs a short markdown first, then the `gpu.Worker` arm construction and batch loop.
```

### [186] TOOL CALL — NotebookEdit · 2026-10-26 10:40:18 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': 'bfb4dd51', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': '### 5.1 Build the five arm caches and sample one CRN slot set (`gpu.Worker.arm_state`, `run_rows`, `_run_batch`)\n\n`arm_state()` below is the GPU worker\'s method, restricted to the arms whose prompts ship with the demo (ban and twin_A). The loop is `run_rows()` / `_run_batch()` without file output:\n- Specs are grouped into shape classes.\n- Each class is sampled as one batch.\n- Every row of slot `k` gets `u = u_stream("beh", task, w, k)`, the exact uniforms the Qwen3-8B run used for that slot.\n\nThe first printout checks the prompt alignment invariant of stage S1: ban and twin have equal length and differ only inside `[p0, p1)`.'}
```

### [187] TOOL RESULT — NotebookEdit · 2026-10-26 10:40:18 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [188] TOOL CALL — NotebookEdit · 2026-10-26 10:40:42 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': '040ef815', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'eng = meta["engine_slot"]\nPROMPTS = {(eng["task"], eng["template"], kind): p for kind, p in eng["prompts"].items()}  # original: load_prompts()\nENGINE_KS = eng["ks"][:ENGINE_N_SLOTS]\n_pre: dict[str, dict[str, Any]] = {}\n_arm: dict[tuple, dict[str, Any]] = {}\n\n\ndef u_key(task: str, w: str, k: int) -> tuple:\n    return ("beh", task, w, k)  # exp8\'s behaviour key: the T1/T2 screen and U9 reuse exp8\'s uniforms exactly\n\n\n# ---- gpu.Worker methods (self.prompts -> PROMPTS, self.pre -> pre, self.model -> model)\ndef pre(ids: list[int]) -> dict[str, Any]:\n    key = sha256_text(",".join(map(str, ids)))\n    if key not in _pre:\n        _pre[key] = prefill(model, ids)\n    return _pre[key]\n\n\ndef shape_of(task: str, w: str, arm: str) -> tuple[int, int]:\n    """(cache length, first generated position) from prompt metadata only."""\n    b = PROMPTS[(task, w, "ban")]\n    P, p0, p1 = b["P"], b["p0"], b["p1"]\n    if arm in ("K0", "K0b"):\n        return P - (p1 - p0), P\n    return P, P\n\n\ndef arm_state(task: str, w: str, arm: str) -> dict[str, Any]:\n    key = (task, w, arm)\n    if key in _arm:\n        return _arm[key]\n    pr = PROMPTS\n    ban, ta = pr[(task, w, "ban")], pr[(task, w, "twin_A")]\n    P, p0, p1 = ban["P"], ban["p0"], ban["p1"]\n    if arm == "a":\n        s = pre(ban["ids"])\n        st = {"kv": s["kv"], "r_logits": s["r_logits"], "ids": ban["ids"], "kind": "ban"}\n    elif arm == "K0":\n        s = pre(ban["ids"])\n        st = {"kv": drop_span(s["kv"], p0, p1), "r_logits": s["r_logits"], "ids": ban["ids"],\n              "kind": "ban|K0(span dropped)", "pos0": P}\n    elif arm in ("b", "V1", "VP", "R2", "R3", "OPEN"):\n        s = pre(ta["ids"])\n        st = {"kv": s["kv"], "r_logits": s["r_logits"], "ids": ta["ids"], "kind": "twin_A"}\n    elif arm == "c":\n        A, X = pre(ta["ids"]), pre(ban["ids"])\n        st = {"kv": splice(A["kv"], X["kv"], p1), "r_logits": X["r_logits"], "ids": ta["ids"][:p1] + ban["ids"][p1:],\n              "kind": "splice:twinA[0,p1)|ban[p1,P)+R(ban)"}\n    elif arm == "d":\n        A, X = pre(ta["ids"]), pre(ban["ids"])\n        st = {"kv": splice(X["kv"], A["kv"], p1), "r_logits": A["r_logits"], "ids": ban["ids"][:p1] + ta["ids"][p1:],\n              "kind": "splice:ban[0,p1)|twinA[p1,P)+R(twinA)"}\n    else:  # K0b, bB, pl and the prefill arms need twin_B / prefill ids, which the demo does not ship\n        raise ValueError(arm)\n    _arm[key] = st\n    return st\n\n\nengine_rows: list[dict[str, Any]] = []\nif RUN_ENGINE:\n    from transformers.utils import logging as hf_logging\n\n    hf_logging.disable_progress_bar()  # notebook: no weight-loading progress bar\n    tok, model = load_model()\n    vocab = tok.convert_ids_to_tokens(list(range(len(tok))))\n    tick_ids = {i for i, s in enumerate(vocab) if s and "`" in s}\n\n    def decode(ids: list[int]) -> str:\n        return tok.decode(ids, skip_special_tokens=True)\n\n    ban, twin = PROMPTS[(eng["task"], eng["template"], "ban")], PROMPTS[(eng["task"], eng["template"], "twin_A")]\n    print(f"ban  condition [p0={ban[\'p0\']}, p1={ban[\'p1\']}): {tok.decode(ban[\'ids\'][ban[\'p0\']:ban[\'p1\']])!r}")\n    print(f"twin condition [p0={twin[\'p0\']}, p1={twin[\'p1\']}): {tok.decode(twin[\'ids\'][twin[\'p0\']:twin[\'p1\']])!r}")\n    print(f"P = {ban[\'P\']} prompt tokens (twin: {twin[\'P\']}); ids identical outside [p0, p1): "\n          f"{all(x == y for i, (x, y) in enumerate(zip(ban[\'ids\'], twin[\'ids\'])) if not ban[\'p0\'] <= i < ban[\'p1\'])}")\n    print("ban prompt:", repr(tok.decode(ban["ids"])))\n\n    # gpu.Worker.run_rows: group by shape class (task, cache length, first generated position), one batch per class\n    specs = [{"task": eng["task"], "w": eng["template"], "k": k, "arm": a} for a in ("a", "b", "c", "d", "K0")\n             for k in ENGINE_KS]\n    groups: dict[tuple, list[dict[str, Any]]] = collections.OrderedDict()\n    for s in specs:\n        L, pos0 = shape_of(s["task"], s["w"], s["arm"])\n        groups.setdefault((s["task"], L, pos0), []).append(s)\n    t_engine = time.time()\n    for (task, L, pos0), chunk in groups.items():\n        # gpu.Worker._run_batch (no duplicate-row padding to B, no file output)\n        batch = []\n        for s in chunk:\n            st = arm_state(s["task"], s["w"], s["arm"])\n            assert st["kv"][0][0].shape[2] == L and st.get("pos0", L) == pos0, (s, L, pos0)\n            uk = u_key(s["task"], s["w"], s["k"])\n            batch.append({"kv": st["kv"], "r_logits": st["r_logits"], "u": u_stream(*uk),\n                          "u2": u_stream(*uk, "veto", n=256), "veto": None, "pos0": pos0, "stop": "bench",\n                          "prefix_text": st.get("prefix_text", "")})\n        t0 = time.time()\n        res_b = sample(model, batch, max_new=ENGINE_MAX_NEW, tick_ids=tick_ids, decode=decode)\n        dt = time.time() - t0\n        for s, r in zip(chunk, res_b):\n            uk = u_key(s["task"], s["w"], s["k"])\n            engine_rows.append({"uid": f"{s[\'task\']}|{s[\'arm\']}|{s[\'w\']}|{s[\'k\']}", "task": s["task"],\n                                "template": s["w"], "k": s["k"], "arm": s["arm"], "seed": stable_seed(*uk),\n                                "u_key": list(uk), "prompt_kind": arm_state(s["task"], s["w"], s["arm"])["kind"],\n                                "P": pos0, "cache_len": L, "token_ids": r["token_ids"],\n                                "gen_text": decode(r["token_ids"]), "n_new_tokens": r["n_tokens"],\n                                "finish_reason": r["finish_reason"], "logprob_sum": r["logprob_sum"]})\n        logger.info(f"[demo] {task} L={L} arms={sorted({c[\'arm\'] for c in chunk})} rows={len(chunk)} "\n                    f"steps={res_b[0][\'steps\']} {dt:.1f}s")\n    print(f"engine: {time.time() - t_engine:.1f}s for {len(engine_rows)} rows "\n          f"(ENGINE_MAX_NEW={ENGINE_MAX_NEW}, ENGINE_N_SLOTS={ENGINE_N_SLOTS}, device={ENGINE_DEVICE})")\nelse:\n    print("RUN_ENGINE = False: engine section skipped")'}
```

### [189] TOOL RESULT — NotebookEdit · 2026-10-26 10:40:42 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [190] ASSISTANT · 2026-10-26 10:40:50 UTC

```
Engine cell E5: live output beside the Qwen3-8B rows of the same CRN slots.
```

### [191] TOOL CALL — NotebookEdit · 2026-10-26 10:40:50 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': '9d1dcc44', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': '### 5.2 Same slot, same uniforms: live small model vs. the Qwen3-8B rows of the full run\n\nFor each slot and arm, the cell below shows:\n- the live program;\n- the Qwen3-8B program the full run sampled with the **same uniforms and the same spliced cache layout**, with its frozen mechanism label;\n- the first token at which each arm leaves arm `b`, using the same rule as `crn_analysis()`.\n\nWith CRN, arms that agree on the next-token distribution emit identical tokens. So the divergence position marks where the ban starts to matter.'}
```

### [192] TOOL RESULT — NotebookEdit · 2026-10-26 10:40:50 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [193] TOOL CALL — NotebookEdit · 2026-10-26 10:40:58 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': 'd5928767', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'def first_divergence(x: list[int], b: list[int]) -> int | None:\n    # the rule of crn_analysis(): first index where arm X leaves arm b\'s tokens; None = identical sequences\n    m = min(len(x), len(b))\n    d = next((i for i in range(m) if x[i] != b[i]), None)\n    if d is None:\n        return None if len(x) == len(b) else m\n    return d\n\n\nref8 = eng["qwen3_8b_rows"]  # Qwen3-8B rows of the same CRN slots (data/samples.jsonl)\nlive = {(r["k"], r["arm"]): r for r in engine_rows}\nfor k in ENGINE_KS:\n    print(f"\\n=================== CRN slot ({eng[\'task\']}, {eng[\'template\']}, k={k}): "\n          f"uniform-stream seed {stable_seed(*u_key(eng[\'task\'], eng[\'template\'], k))}")\n    b8 = ref8[str(k)]["b"]["token_ids"]\n    for a in ("a", "b", "c", "d", "K0"):\n        r8 = ref8[str(k)][a]\n        print(f"--- arm {a}")\n        if (k, a) in live:\n            lv = live[(k, a)]\n            print(f"  {ENGINE_MODEL_ID} (live, {lv[\'prompt_kind\']}): {lv[\'n_new_tokens\']} tokens, {lv[\'finish_reason\']}, "\n                  f"leaves arm b at token {first_divergence(lv[\'token_ids\'], live[(k, \'b\')][\'token_ids\'])}")\n            print("      " + lv["gen_text"].replace("\\n", "\\n      "))\n        print(f"  Qwen3-8B (full run): label = {r8[\'label\']} (passed tests: {r8[\'passed\']}), {r8[\'n_new_tokens\']} tokens, "\n              f"leaves arm b at token {first_divergence(r8[\'token_ids\'], b8)}")\n        print("      " + r8["gen_text"].replace("\\n", "\\n      "))'}
```

### [194] TOOL RESULT — NotebookEdit · 2026-10-26 10:40:58 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [195] ASSISTANT · 2026-10-26 10:41:38 UTC

```
Section 6: the visualisation. First its markdown:
```

### [196] TOOL CALL — NotebookEdit · 2026-10-26 10:41:38 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': 'c6ac5e69', 'edit_mode': 'insert', 'cell_type': 'markdown', 'new_source': "## 6. Results: demo subset vs. full run\n\n**Figure 1.**\n- **Left:** default share per arm on the gated tasks. Bars are the demo subset; black diamonds are the full run with 100 slots per task.\n- **Right:** the **route plane**.\n  - Each task is placed by how much of the ban the later prompt states carry (`F_prompt`, arm c) and how much reading the ban itself carries (`F_direct`, arm d).\n  - Points on the dotted diagonal are additive routes (`I = 0`). Points near `(1, 1)` are redundant, since either route alone suffices. Points near `(0, 0)` are superadditive, since both routes are needed.\n  - C2a needed the pooled star to the right of the blue line (`F_prompt >= 2/3`) and below the green one (`F_direct < 1/3`).\n\n**Figure 2.**\n- **Left:** pooled fractions with the three interval types.\n- **Middle:** where the arms of a CRN slot first leave arm `b`'s tokens, using the Qwen3-8B tokens of the demo slots.\n- **Right:** the same token-level picture for the engine slot. The green part of each strip is identical to arm `b`, and the orange part follows the divergence, with the diverging token printed."}
```

### [197] TOOL RESULT — NotebookEdit · 2026-10-26 10:41:38 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [198] ASSISTANT · 2026-10-26 10:42:02 UTC

```
Figure 1: arm shares and the route plane.
```

### [199] TOOL CALL — NotebookEdit · 2026-10-26 10:42:02 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': '40d910b7', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'ARM_COL = {"a": "#d62728", "b": "#7f7f7f", "c": "#1f77b4", "d": "#2ca02c", "K0": "#9467bd"}\n\n\ndef _err(p: float, ci: list[float]) -> list[list[float]]:\n    # matplotlib error-bar lengths from a point and an interval (NaN-safe, never negative)\n    lo, hi = ci\n    return [[max(0.0, p - lo) if np.isfinite(lo) else 0.0], [max(0.0, hi - p) if np.isfinite(hi) else 0.0]]\n\n\nfig, axes = plt.subplots(1, 2, figsize=(15, 5.8))\n\n# (A) default share per arm on the gated tasks: demo subset (bars, Wilson 95%) vs full run (diamonds)\nax = axes[0]\nwidth, x = 0.16, np.arange(len(gated))\nfor i, a in enumerate(ARMS5):\n    s = np.array([shares[t][a]["s"] if a in shares[t] else np.nan for t in gated])\n    lo = np.array([shares[t][a]["ci95"][0] if a in shares[t] else np.nan for t in gated])\n    hi = np.array([shares[t][a]["ci95"][1] if a in shares[t] else np.nan for t in gated])\n    ax.bar(x + (i - 2) * width, s, width, yerr=[np.clip(s - lo, 0, None), np.clip(hi - s, 0, None)], capsize=2,\n           color=ARM_COL[a], alpha=0.85, error_kw={"lw": 0.8}, label=f"arm {a}")\n    ax.scatter(x + (i - 2) * width, [ref["shares"][t].get(a, np.nan) for t in gated], marker="D", s=16, color="black",\n               zorder=3, label="full run (N = 100 per arm)" if i == 0 else None)\nax.set_xticks(x, [f"{t}\\ndefault: {DEFAULT[t]}" for t in gated], fontsize=8)\nax.set_ylim(0, 1.12)\nax.set_ylabel("share of attempts = default mechanism")\nax.set_title(f"Default share per arm on the gated tasks (demo: {N_SLOTS * len(TEMPLATE_IDS)} slots per task, Wilson 95%)",\n             fontsize=10)\nax.legend(ncol=3, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.16))\n\n# (B) route plane: per-task F_prompt x F_direct (demo with template->slot bootstrap 95%; full run hollow)\nax = axes[1]\nax.plot([-0.1, 1.1], [1.1, -0.1], ls=":", color="grey", lw=1)\nax.text(0.02, 0.9, "I = 0 (additive)", fontsize=7, color="grey", rotation=-38)\nax.axvline(THRESHOLDS["F_confirm"], color="#1f77b4", ls="--", lw=0.8)\nax.axhline(THRESHOLDS["F_direct_disconfirm"], color="#2ca02c", ls="--", lw=0.8)\nax.text(THRESHOLDS["F_confirm"] + 0.01, -0.12, "F_prompt = 2/3", fontsize=7, color="#1f77b4")\nax.text(-0.13, THRESHOLDS["F_direct_disconfirm"] + 0.015, "F_direct = 1/3", fontsize=7, color="#2ca02c")\ntask_col = dict(zip(gated, plt.cm.tab10(np.arange(len(gated)))))\nfor t, v in route["per_task"].items():\n    fp, fdr = v["F_prompt"], v["F_direct"]\n    ax.errorbar(fp["point"], fdr["point"], xerr=_err(fp["point"], fp["ci95"]), yerr=_err(fdr["point"], fdr["ci95"]),\n                fmt="o", ms=7, capsize=2, lw=0.8, color=task_col[t])\n    rf = ref["C2a"]["per_task"][t]\n    ax.scatter(rf["F_prompt"]["point"], rf["F_direct"]["point"], marker="o", s=90, facecolors="none",\n               edgecolors=task_col[t], linewidths=1.5)\n    ax.annotate(f"{t} ({DEFAULT[t]})", (fp["point"], fdr["point"]), xytext=(7, 5), textcoords="offset points", fontsize=8)\npt = route["point"]\nax.scatter(pt["F_prompt"], pt["F_direct"], marker="*", s=300, color="gold", edgecolors="black", zorder=4,\n           label=f"pooled, demo ({route[\'verdict\']})")\nax.scatter(ref["C2a"]["point"]["F_prompt"], ref["C2a"]["point"]["F_direct"], marker="*", s=300, facecolors="none",\n           edgecolors="black", zorder=4, label=f"pooled, full run ({ref[\'C2a\'][\'verdict\']})")\nax.scatter([], [], marker="o", color="grey", label="per task, demo (bootstrap 95%)")\nax.scatter([], [], marker="o", facecolors="none", edgecolors="grey", label="per task, full run")\nax.set_xlim(-0.15, 1.15)\nax.set_ylim(-0.15, 1.15)\nax.set_xlabel("F_prompt = (s_b - s_c)/(s_b - s_a): later prompt states alone (arm c)")\nax.set_ylabel("F_direct = (s_b - s_d)/(s_b - s_a): reading the ban itself (arm d)")\nax.set_title("Route plane: which route carries the ban, per task", fontsize=10)\nax.legend(fontsize=7, loc="center left")\nplt.tight_layout()\nplt.show()'}
```

### [200] TOOL RESULT — NotebookEdit · 2026-10-26 10:42:02 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [201] ASSISTANT · 2026-10-26 10:42:20 UTC

```
Figure 2: pooled intervals, first-divergence ECDF, and the engine-slot token strips.
```

### [202] TOOL CALL — NotebookEdit · 2026-10-26 10:42:20 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': 'fb2f15fe', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': 'fig, axes = plt.subplots(1, 3, figsize=(18, 5.2), gridspec_kw={"width_ratios": [1, 1, 1.3]})\n\n# (C) pooled route fractions: demo point with jackknife (primary) / percentile / BCa 95%, full run with jackknife 95%\nax = axes[0]\nqs = ["F_prompt", "F_direct", "I", "F_K0"]\nfor j, q in enumerate(qs):\n    p = route["point"][q]\n    for off, (kind, col) in enumerate([("jackknife", "#d62728"), ("percentile", "#1f77b4"), ("bca", "#2ca02c")]):\n        ax.errorbar(j + (off - 1.5) * 0.14, p, yerr=_err(p, route["intervals"][q][kind]), fmt="o", color=col, capsize=3,\n                    label=f"demo, {kind}" + (" (primary)" if kind == route["primary_interval"] else "") if j == 0 else None)\n    rp = ref["C2a"]["point"][q]\n    ax.errorbar(j + 1.5 * 0.14, rp, yerr=_err(rp, ref["C2a"]["intervals"][q]["jackknife"]), fmt="D", color="black",\n                mfc="white", capsize=3, label="full run, jackknife" if j == 0 else None)\nax.axhline(THRESHOLDS["F_confirm"], color="#1f77b4", ls="--", lw=0.7)\nax.axhline(THRESHOLDS["F_direct_disconfirm"], color="#2ca02c", ls="--", lw=0.7)\nax.axhline(0, color="grey", lw=0.5)\nax.set_xticks(range(len(qs)), qs)\nax.set_title(f"Pooled over {route[\'n_tasks\']} gated tasks (ratio of sums)\\nC2a: demo {route[\'verdict\']} | "\n             f"full run {ref[\'C2a\'][\'verdict\']}", fontsize=10)\nax.legend(fontsize=7, loc="lower left")\n\n# (D) first token at which arm X leaves its CRN partner in arm b (Qwen3-8B tokens of the demo slots)\nax = axes[1]\nfor X in ("a", "c", "d", "K0"):\n    vals = np.sort(np.concatenate([np.asarray(crn[t]["first_divergence"].get(X, {}).get("values", []), float)\n                                   for t in gated]))\n    n_id = sum(crn[t]["first_divergence"].get(X, {}).get("n_identical_to_b", 0) for t in gated)\n    if len(vals):\n        ax.step(vals, np.arange(1, len(vals) + 1) / len(vals), where="post", color=ARM_COL[X], lw=1.6,\n                label=f"arm {X}: median {np.median(vals):.0f} ({len(vals)} diverged, {n_id} identical to b)")\nax.set_xlim(0, 60)\nax.set_xlabel("generated token index of the first divergence from arm b")\nax.set_ylabel("ECDF over diverged slots (gated tasks)")\nax.set_title("Where the arms leave the neutral twin (CRN partners)", fontsize=10)\nax.legend(fontsize=7, loc="lower right")\n\n# (E) the engine slot: token strips identical to arm b (green) until the first divergence (orange after)\nax = axes[2]\nk0 = ENGINE_KS[0]\nstrips = [(f"8B  arm {a}", ref8[str(k0)][a]["token_ids"], ref8[str(k0)]["b"]["token_ids"]) for a in ("a", "c", "d", "K0")]\nif RUN_ENGINE:\n    strips += [(f"live arm {a}", live[(k0, a)]["token_ids"], live[(k0, "b")]["token_ids"]) for a in ("a", "c", "d", "K0")]\nfor i, (name, xs, bs) in enumerate(strips):\n    d = first_divergence(xs, bs)\n    n_same = len(xs) if d is None else d\n    ax.barh(i, n_same, color="#2ca02c", height=0.6)\n    if d is not None:\n        ax.barh(i, len(xs) - d, left=d, color="#ff7f0e", height=0.6)\n        if RUN_ENGINE and d < len(xs):\n            ax.text(d + 0.5, i, f"{tok.decode([xs[d]])!r} (b: {tok.decode([bs[d]])!r})" if d < len(bs)\n                    else f"{tok.decode([xs[d]])!r}", va="center", fontsize=7)\n    else:\n        ax.text(n_same + 0.5, i, "identical to b", va="center", fontsize=7)\nax.set_yticks(range(len(strips)), [s[0] for s in strips], fontsize=8)\nax.invert_yaxis()\nax.set_xlabel("generated token index")\nax.set_title(f"Engine slot ({eng[\'task\']}, {eng[\'template\']}, k={k0}): Qwen3-8B (full run) vs live "\n             f"{ENGINE_MODEL_ID.split(\'/\')[-1] if RUN_ENGINE else \'(skipped)\'}", fontsize=10)\nplt.tight_layout()\nplt.show()'}
```

### [203] TOOL RESULT — NotebookEdit · 2026-10-26 10:42:20 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [204] ASSISTANT · 2026-10-26 10:42:34 UTC

```
Last cell: the headline table, demo vs. full run.
```

### [205] TOOL CALL — NotebookEdit · 2026-10-26 10:42:34 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': 'ea928a4a', 'edit_mode': 'insert', 'cell_type': 'code', 'new_source': '# ---- headline numbers: demo subset (100 CRN slots, 500 labelled programs) vs full run (13,030 samples)\ndef _ci(v: list[float]) -> str:\n    return f"[{v[0]:.2f}, {v[1]:.2f}]"\n\n\nrp = ref["C2a"]\nsummary = [("gated tasks (frozen gate)", ", ".join(gated), ", ".join(meta["gated_tasks"]))]\nfor q in ("F_prompt", "F_direct", "I", "F_K0"):\n    summary.append((f"pooled {q} [jackknife 95%, primary]",\n                    f"{route[\'point\'][q]:.3f} {_ci(route[\'intervals\'][q][\'jackknife\'])}",\n                    f"{rp[\'point\'][q]:.3f} {_ci(rp[\'intervals\'][q][\'jackknife\'])}"))\nsummary += [\n    ("C2a verdict (percentile / BCa / jackknife)", " / ".join(route["verdict_by_interval"][k] for k in ("percentile", "bca", "jackknife")),\n     " / ".join(rp["verdict_by_interval"][k] for k in ("percentile", "bca", "jackknife"))),\n    ("P_boot(F_prompt <= 1/2), P_boot(F_direct >= 1/3)",\n     f"{route[\'p_boot_F_prompt_le_half\']:.2f}, {route[\'p_boot_F_direct_ge_third\']:.2f}",\n     f"{rp[\'p_boot_F_prompt_le_half\']:.2f}, {rp[\'p_boot_F_direct_ge_third\']:.2f}"),\n    ("mixed GLM F_prompt, F_direct", f"{route[\'mixed_glm\'].get(\'F_prompt_glm\', float(\'nan\')):.2f}, "\n     f"{route[\'mixed_glm\'].get(\'F_direct_glm\', float(\'nan\')):.2f}",\n     f"{rp[\'mixed_glm\'][\'F_prompt_glm\']:.2f}, {rp[\'mixed_glm\'][\'F_direct_glm\']:.2f}"),\n    ("C2c: hit fraction, Spearman rho (perm p) -> decision",\n     f"{c2c[\'hit_fraction\']:.2f}, {c2c[\'spearman_rho\']:.2f} (p {c2c[\'perm_p_one_sided\']:.2f}) -> {c2c[\'decision\']}",\n     f"{ref[\'C2c\'][\'hit_fraction\']:.2f}, {ref[\'C2c\'][\'spearman_rho\']:.2f} (p {ref[\'C2c\'][\'perm_p_one_sided\']:.2f}) -> "\n     f"{ref[\'C2c\'][\'decision\']}"),\n]\nfor t in gated:\n    v, rv = route["per_task"][t], rp["per_task"][t]\n    summary.append((f"{t} F_prompt / F_direct", f"{v[\'F_prompt\'][\'point\']:.2f} / {v[\'F_direct\'][\'point\']:.2f}",\n                    f"{rv[\'F_prompt\'][\'point\']:.2f} / {rv[\'F_direct\'][\'point\']:.2f}"))\nprint(pd.DataFrame(summary, columns=["quantity", "demo subset", "full run"]).set_index("quantity").to_string())'}
```

### [206] TOOL RESULT — NotebookEdit · 2026-10-26 10:42:35 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [207] ASSISTANT · 2026-10-26 10:42:40 UTC

```
All cells are in. Let me verify the cell order and types before the first test run.
```

### [208] TOOL CALL — Bash · 2026-10-26 10:42:40 UTC

```
List notebook cells in order with first lines:
python3 -I -c "
import json
nb = json.load(open('code_demo.ipynb'))
for i, c in enumerate(nb['cells']):
    src = ''.join(c['source'])
    print(f'{i:2d} {c[\"cell_type\"]:8s} {c.get(\"id\"):10s} {src.splitlines()[0][:100]!r}')
print('nbformat', nb['nbformat'], nb['nbformat_minor'])
"
```

### [209] TOOL RESULT — Bash · 2026-10-26 10:42:40 UTC

```
{"stdout": " 0 markdown title      '# Where a coding ban takes effect in Qwen3-8B: route-test demo'\n 1 code     fc03631f   'import subprocess, sys'\n 2 code     bc3a2b51   '# original imports of the code used below (src/cfg.py, src/engine.py, src/gpu.py, src/analysis/analy'\n 3 code     4c26f4ad   'GITHUB_DATA_URL = \"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-b'\n 4 code     14389e18   'data = load_data()'\n 5 markdown 4e32fa9b   '## Config'\n 6 code     90440e47   '# ------------------------------------------------------------------ analysis (src/analysis/analysis'\n 7 markdown 92ea3a37   '## 1. Frozen protocol constants and helpers (`src/cfg.py`)'\n 8 code     95ac415d   '# ------------------------------------------------------------------------------------------------ m'\n 9 markdown 0f27d9a4   '## 2. Labelled rows (replaces `analysis.load_rows()` on `data/samples.jsonl`)'\n10 code     d62567d8   'EXCL = (\"invalid\", \"no_code\", \"disputed\")'\n11 markdown 61f906af   '## 3. Gate: does the ban move the model at all? (`gpu.compute_gate`)'\n12 code     7b28a7ae   'ATTEMPT_EXCLUDE = (\"invalid\", \"no_code\", \"disputed\")'\n13 markdown 36bf6d79   '## 4. S9 analysis (`src/analysis/analysis.py`)'\n14 code     d6f7cfbc   'def hill1(labels: list[str]) -> float:'\n15 markdown bdfa771f   '### 4.2 Route fractions with CRN-respecting resampling (9.2)'\n16 code     f096a19f   '# ------------------------------------------------------------------------------------------------ 9'\n17 code     b166b928   'def hier_boot(arr: dict[str, Any], n_boot: int = N_BOOT, seed: int = RNG_SEED) -> dict[str, np.ndarr'\n18 code     ce9dcbb7   'def per_task_route(arr: dict[str, Any], n_boot: int = N_BOOT_TASK) -> dict[str, Any]:  # original de'\n19 code     58044007   '# run_analysis(): confirmatory route analysis on the gated tasks + descriptive per-task fractions on'\n20 markdown 32d709ec   '### 4.3 Paired CRN evidence: flip tables, identical outputs, first divergence (9.3)'\n21 code     e2b90bf7   '# ------------------------------------------------------------------------------------------------ 9'\n22 markdown 1798f0d7   '### 4.4 Where does each route land? (9.4)'\n23 code     99839706   'def js_div(p: np.ndarray, q: np.ndarray) -> float:'\n24 markdown 16e0dbee   '### 4.5 C2c: does veto sufficiency predict the direct route? (9.5)'\n25 code     b6c7d5b8   '# ------------------------------------------------------------------------------------------------ 9'\n26 markdown ca67a434   '### 4.6 Analysis result (end of `run_analysis()`)'\n27 code     aa71d527   'res = {\"gated\": gated, \"gate\": gate, \"shares\": shares, \"route\": route, \"route_nongated_descriptive\":'\n28 markdown 8231e090   '## 5. The engine: CRN-coupled KV-splice sampling (`src/engine.py`, `src/gpu.py`)'\n29 code     b6497aad   '# ---- src/engine.py: knockout-capable attention + fence detection (verbatim)'\n30 code     b5e86edd   'def load_model(vram_fraction: float = 0.95):'\n31 code     bfb4dd51   '# ------------------------------------------------------------------------------------------------ s'\n32 markdown 040ef815   '### 5.1 Build the five arm caches and sample one CRN slot set (`gpu.Worker.arm_state`, `run_rows`, `'\n33 code     9d1dcc44   'eng = meta[\"engine_slot\"]'\n34 markdown d5928767   '### 5.2 Same slot, same uniforms: live small model vs. the Qwen3-8B rows of the full run'\n35 code     c6ac5e69   'def first_divergence(x: list[int], b: list[int]) -> int | None:'\n36 markdown 40d910b7   '## 6. Results: demo subset vs. full run'\n37 code     fb2f15fe   'ARM_COL = {\"a\": \"#d62728\", \"b\": \"#7f7f7f\", \"c\": \"#1f77b4\", \"d\": \"#2ca02c\", \"K0\": \"#9467bd\"}'\n38 code     ea928a4a   'fig, axes = plt.subplots(1, 3, figsize=(18, 5.2), gridspec_kw={\"width_ratios\": [1, 1, 1.3]})'\n39 code     2f633168   '# ---- headline numbers: demo subset (100 CRN slots, 500 labelled programs) vs full run (13,030 samp'\nnbformat 4 5", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [210] ASSISTANT · 2026-10-26 10:42:52 UTC

```
Cell order is correct. TODO 4 test run at minimum config, using the exact `<test_environment>` commands (fresh venv) and timing the whole run:
```

### [211] TOOL CALL — Bash · 2026-10-26 10:42:52 UTC

```
Test-run the notebook in a clean venv at minimum config:
UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art__5akZ9W9iZM4-bfb6955ec1d9 && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art__5akZ9W9iZM4-bfb6955ec1d9/bin/python jupyter ipykernel && T0=$(date +%s) && /tmp/aii_nb_test_envs/art__5akZ9W9iZM4-bfb6955ec1d9/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb; echo "EXIT=$? RUNTIME=$(( $(date +%s) - T0 ))s"
```

### [212] TOOL RESULT — Bash · 2026-10-26 10:42:52 UTC

```
{"stdout": "", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false, "backgroundTaskId": "befz6borp"}
```

### [213] ASSISTANT · 2026-10-26 10:43:10 UTC

```
While the first test runs, I'll check the workspace for anything heavy so the manifest has the right entries.
```

### [214] TOOL CALL — Bash · 2026-10-26 10:43:10 UTC

```
Find large files and list workspace contents:
find . -type f -size +1M -exec ls -la {} \; ; echo "---all:"; find . -path ./.aii -prune -o -type f -print | head -30; du -sh .
```

### [215] TOOL RESULT — Bash · 2026-10-26 10:43:10 UTC

```
{"stdout": "-rw-rw-rw- 1 aii-agent aii-agent 1412240 Oct 26 10:43 ./.repl_agent.ptylog\n---all:\n./code_demo.ipynb\n./mini_demo_data.json\n./.repl_agent.ptylog\n./.aii_claude_session.json\n./scripts/build_mini_demo_data.py\n5.1M\t.", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [216] ASSISTANT · 2026-10-26 10:43:20 UTC

```
Nothing heavy is in the workspace (the largest file is the 1.4 MB harness log), so the manifest will have no entries. I'll wait for the test run to finish.
```

### [217] TOOL CALL — Bash · 2026-10-26 10:43:20 UTC

```
Placeholder to yield while test runs:
sleep 1; echo waiting
```

### [218] TOOL RESULT — Bash · 2026-10-26 10:43:20 UTC

```
{"stdout": "waiting", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [219] ASSISTANT · 2026-10-26 10:43:28 UTC

```
While waiting, I'll write the manifest. The workspace has no large binaries or caches, so the entry list is empty.
```

### [220] TOOL CALL — Write · 2026-10-26 10:43:28 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/.aii/manifest.yaml

# Storage decisions for this folder. Nothing here is heavy: the deliverables (code_demo.ipynb, mini_demo_data.json,
# scripts/, README.md) are text/code files under the 10 MB auto-keep floor. No virtualenv, model weights or caches are
# stored in this folder -- the test venv lives on local disk outside it, and the Qwen3-0.6B weights the notebook loads
# sit in the shared Hugging Face cache (redownloadable: `huggingface-cli download Qwen/Qwen3-0.6B
# --revision c1899de289a04d12100db370d81485cdf75e47ca`).
entries: []
```

### [221] TOOL RESULT — Write · 2026-10-26 10:43:28 UTC

```
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/.aii/manifest.yaml", "content": "# Storage decisions for this folder. Nothing here is heavy: the deliverables (code_demo.ipynb, mini_demo_data.json,\n# scripts/, README.md) are text/code files under the 10 MB auto-keep floor. No virtualenv, model weights or caches are\n# stored in this folder -- the test venv lives on local disk outside it, and the Qwen3-0.6B weights the notebook loads\n# sit in the shared Hugging Face cache (redownloadable: `huggingface-cli download Qwen/Qwen3-0.6B\n# --revision c1899de289a04d12100db370d81485cdf75e47ca`).\nentries: []\n", "structuredPatch": [], "originalFile": null, "userModified": false}
```

### [222] ASSISTANT · 2026-10-26 10:43:48 UTC

```
The manifest is written. While the test is still running, here is a quick check that the f-string nesting in the summary log line parses under Python 3.12 (the only syntax-sensitive spot I see):
```

### [223] TOOL CALL — Bash · 2026-10-26 10:43:48 UTC

```
Check f-string and label expressions parse correctly:
/usr/local/bin/python3.12 -c "
route={'point':{'F_prompt':0.6111,'F_direct':float('nan')},'verdict':'X'}
print(f\"C2a={route.get('verdict')} point={ {k: round(v, 3) for k, v in route.get('point', {}).items()} }\")
lab = None if 0 else 1
j=0; kind='jackknife'; prim='jackknife'
print(f'demo, {kind}' + (' (primary)' if kind == prim else '') if j == 0 else None)
"
```

### [224] TOOL RESULT — Bash · 2026-10-26 10:43:48 UTC

```
{"stdout": "C2a=X point={'F_prompt': 0.611, 'F_direct': nan}\ndemo, jackknife (primary)", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [225] TOOL CALL — Bash · 2026-10-26 10:43:56 UTC

```
Show test result and executed cell outputs:
tail -5 /tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-3-art--5akZ9W9iZM4/c71db1cb-129d-4e37-954d-e401f6949d31/tasks/befz6borp.output; cd /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4 && python3 -I - <<'EOF'
import json
nb = json.load(open("code_demo.ipynb"))
for i, c in enumerate(nb["cells"]):
    if c["cell_type"] != "code":
        continue
    outs = c.get("outputs", [])
    for o in outs:
        if o["output_type"] == "error":
            print(f"CELL {i} ERROR: {o['ename']}: {o['evalue']}")
        elif o["output_type"] == "stream":
            txt = "".join(o["text"])
            print(f"--- cell {i} [{o['name']}]\n{txt[:3000]}")
        elif o["output_type"] in ("display_data", "execute_result"):
            print(f"--- cell {i} [{o['output_type']}] keys={list(o['data'].keys())}")
EOF
```

### [226] TOOL RESULT — Bash · 2026-10-26 10:43:56 UTC

````
{"stdout": "[IPKernelApp] WARNING | Kernel is running over TCP without encryption. All communication (including code and outputs) is sent in plain text and is susceptible to eavesdropping. Use IPC transport or launch with kernel manager-provisioned CurveZMQ keys to enable transport encryption.\n[NbConvertApp] Writing 397630 bytes to code_demo.ipynb\nEXIT=0 RUNTIME=44s\n\n[exited with code 0]\n--- cell 2 [stdout]\ntorch 2.9.0+cpu | numpy 2.0.2 | cuda available: False\n\n--- cell 4 [stdout]\nGitHub data unavailable, using local mini_demo_data.json: HTTP Error 404: Not Found\nCurated demo subset of the route_arms dataset of 'Where a coding ban takes effect in Qwen3-8B' (CRN-coupled KV-splice route test on 12 frozen bench tasks).\nsource:    full_method_out.json -> datasets[route_arms] (+ per-arm token ids from data/samples.jsonl)\nselection: gated tasks ['T03', 'T06', 'T05', 'T10', 'T13']: slots k < 3 of every template; first 5 non-gated tasks in STAGE_A order ['T04', 'R1', 'T08', 'R3', 'R6']: slot k < 1 of every template\n100 CRN slots | full-run model: Qwen/Qwen3-8B (bfloat16) | T=1.0, top-p 1.0, no top-k, max 1024 new tokens, CRN inverse-CDF sampling\nexample: {'input': \"task T03 | template W1 | slot k=0 | ban segment: 'Do not use a full sort for this task.' | neutral twin: 'Do not use man for this task. . .'\", 'output': 'quickselect', 'metadata_task': 'T03', 'metadata_template': 'W1', 'metadata_k': 0, 'metadata_default': 'full_sort', 'metadata_gated': True, 'metadata_a_passed': True, 'predict_b': 'full_sort|pass', 'predict_c': 'quickselect|pass', 'predict_d': 'quickselect|pass', 'predict_K0': 'quickselect|pass'}\n\n--- cell 8 [stdout]\n{'T03': 'full_sort', 'T04': 'naive', 'T06': 'hash_set', 'T05': 'hash_map', 'T10': 'union_find', 'R1': 'greedy_end', 'T08': 'iteration', 'R3': 'kahn', 'T13': 'sort_sweep', 'R6': 'binary_search', 'T14': 'sort_by_count', 'T11': 'quadratic_dp'}\n\n--- cell 10 [stdout]\n500 labelled rows over 10 tasks; rows per task x arm:\narm   K0   a   b   c   d\ntask                    \nT03   15  15  15  15  15\nT04    5   5   5   5   5\nT06   15  15  15  15  15\nT05   15  15  15  15  15\nT10   15  15  15  15  15\nR1     5   5   5   5   5\nT08    5   5   5   5   5\nR3     5   5   5   5   5\nT13   15  15  15  15  15\nR6     5   5   5   5   5\n\none CRN slot (T06, W1, k=1) -- every arm read the same uniforms:\n  arm a   label=index_marking   passed=True  n_tokens=53\n  arm b   label=hash_set        passed=True  n_tokens=39\n  arm c   label=hash_set        passed=True  n_tokens=34\n  arm d   label=index_marking   passed=True  n_tokens=53\n  arm K0  label=hash_set        passed=True  n_tokens=34\n\n--- cell 12 [stdout]\n           default full: avoidance full: n_nondefault/100 full: gated demo: avoidance demo: n_nondefault demo: n_attempted\nT03      full_sort            0.99                     99        True            1.00                 15                15\nT04          naive            0.42                     42       False            0.60                  3                 5\nT06       hash_set            0.79                     79        True            0.80                 12                15\nT05       hash_map            0.83                     83        True            0.87                 13                15\nT10     union_find            1.00                    100        True            1.00                 15                15\nR1      greedy_end            0.00                      0       False            0.00                  0                 5\nT08      iteration            0.31                     31       False            0.00                  0                 5\nR3            kahn            0.04                      4       False            0.00                  0                 5\nT13     sort_sweep            0.59                     59        True            0.67                 10                15\nR6   binary_search            0.02                      2       False            0.20                  1                 5\nT14  sort_by_count            0.41                     41       False            None               None              None\nT11   quadratic_dp            0.02                      2       False            None               None              None\n\ngated (frozen gate, used below): ['T03', 'T06', 'T05', 'T10', 'T13']\n\n--- cell 14 [stdout]\n     s_a  s_b  s_c  s_d  s_K0  n/arm arm-a modal survivor  gated\nT03 0.00 0.93 0.00 0.20  0.00     15          quickselect   True\nT04 0.40 1.00 1.00 0.80  1.00      5                  bmh  False\nT06 0.20 1.00 1.00 0.27  1.00     15        index_marking   True\nT05 0.13 1.00 0.73 0.20  0.67     15          brute_force   True\nT10 0.00 1.00 0.00 0.20  0.00     15                  bfs   True\nR1  1.00 1.00 1.00 1.00  1.00      5                 None  False\nT08 1.00 1.00 1.00 1.00  1.00      5                 None  False\nR3  1.00 1.00 1.00 1.00  1.00      5                 None  False\nT13 0.33 1.00 0.73 1.00  0.67     15                other   True\nR6  0.80 0.80 1.00 0.80  1.00      5                other  False\n\n--- cell 19 [stdout]\nroute analysis: 0.1s (N_BOOT=100, N_BOOT_TASK=100)\n\nC2a verdict -- demo: DISCONFIRMED (primary interval: jackknife, by interval {'percentile': 'DISCONFIRMED', 'bca': 'DISCONFIRMED', 'jackknife': 'DISCONFIRMED'})  |  full run: DISCONFIRMED\n         demo point demo jackknife (primary) demo percentile       demo BCa full point full jackknife\nF_prompt      0.578            [-0.00, 1.16]    [0.13, 0.93]   [0.12, 0.92]      0.611   [0.06, 1.17]\nF_direct      0.719             [0.34, 1.10]    [0.47, 0.95]   [0.40, 0.89]      0.744   [0.38, 1.11]\nI            -0.297            [-0.99, 0.40]   [-0.76, 0.11]  [-0.69, 0.13]     -0.355  [-0.98, 0.27]\nF_K0          0.609             [0.06, 1.16]    [0.18, 0.94]   [0.17, 0.92]      0.621   [0.08, 1.16]\nP_boot(F_prompt <= 1/2) = 0.34  P_boot(F_direct >= 1/3) = 1.00   (full run: 0.28 / 0.99)\nmixed GLM sensitivity: F_prompt 0.57, F_direct 0.77  (full run: 0.74, 0.89)\nleave-one-template-out F_prompt: {'W1': 0.6, 'W2': 0.61, 'W3': 0.51, 'W4': 0.55, 'W5': 0.62}\nleave-one-template-out F_direct: {'W1': 0.7, 'W2': 0.69, 'W3': 0.69, 'W4': 0.82, 'W5': 0.67}\n\nper gated task (template -> slot bootstrap 95%):\n    F_prompt F_prompt ci95 F_direct F_direct ci95     I F_K0 full F_prompt full F_direct\nT03     1.00  [1.00, 1.00]     0.79  [0.47, 1.00] -0.79 1.00          1.00          0.74\nT06     0.00  [0.00, 0.00]     0.92  [0.73, 1.00]  0.08 0.00          0.04          0.99\nT05     0.31  [0.00, 0.63]     0.92  [0.75, 1.00] -0.23 0.38          0.41          0.96\nT10     1.00  [1.00, 1.00]     0.80  [0.40, 1.00] -0.80 1.00          1.00          0.80\nT13     0.40  [0.00, 0.91]     0.00  [0.00, 0.00]  0.60 0.50          0.39          0.02\n\n--- cell 19 [stderr]\n/tmp/ipykernel_644/94586597.py:30: RuntimeWarning: Mean of empty slice\n  \"F_prompt_mean\": np.nanmean((sb - sc) / (sb - sa), -1),\n/tmp/ipykernel_644/94586597.py:31: RuntimeWarning: Mean of empty slice\n  \"F_direct_mean\": np.nanmean((sb - sd) / (sb - sa), -1)}\n\n--- cell 21 [stdout]\npair X-Y    a-K0     a-c     a-d     b-c     b-d    c-K0\ntask                                                    \nT03      1.0e+00 1.0e+00 2.5e-01 1.2e-04 9.8e-04 1.0e+00\nT05      7.8e-03 3.9e-03 1.0e+00 1.2e-01 4.9e-04 1.0e+00\nT06      4.9e-04 4.9e-04 1.0e+00 1.0e+00 9.8e-04 1.0e+00\nT10      1.0e+00 1.0e+00 2.5e-01 6.1e-05 4.9e-04 1.0e+00\nT13      6.2e-02 3.1e-02 2.0e-03 1.2e-01 1.0e+00 1.0e+00\n\nflip tables (gated tasks): 'X default only' vs 'Y default only' are the discordant CRN slots\n               X default only  Y default only  both default  neither  McNemar exact p\ntask pair X-Y                                                                        \nT03  a-c                    0               0             0       15                1\n     a-d                    0               3             0       12             0.25\n     b-d                   11               0             3        1          0.00098\n     a-K0                   0               0             0       15                1\n     c-K0                   0               0             0       15                1\n     b-c                   14               0             0        1          0.00012\nT06  a-c                    0              12             3        0          0.00049\n     a-d                    0               1             3       11                1\n     b-d                   11               0             4        0          0.00098\n     a-K0                   0              12             3        0          0.00049\n     c-K0                   0               0            15        0                1\n     b-c                    0               0            15        0                1\nT05  a-c                    0               9             2        4           0.0039\n     a-d                    0               1             2       12                1\n     b-d                   12               0             3        0          0.00049\n     a-K0                   0               8             2        5           0.0078\n     c-K0                   1               0            10        4                1\n     b-c                    4               0            11        0             0.12\nT10  a-c                    0               0             0       15                1\n     a-d                    0               3             0       12             0.25\n     b-d                   12               0             3        0          0.00049\n     a-K0                   0               0             0       15                1\n     c-K0                   0               0             0       15                1\n     b-c                   15               0             0        0          6.1e-05\nT13  a-c                    0               6             5        4            0.031\n     a-d                    0              10             5        0            0.002\n     b-d                    0               0            15        0                1\n     a-K0    \n--- cell 23 [stdout]\nlanding analysis: 0.0s (LANDING_N_REP=20)\n\nT03 (default full_sort; catalogue ['full_sort', 'size_k_heap', 'heapify_pop', 'quickselect', 'median_of_medians', 'counting_sort'])\n  arm a  : non-default landings {'quickselect': 9, 'size_k_heap': 6}\n  arm c  : {'quickselect': 8, 'size_k_heap': 7}  modal=quickselect (same as a: True); JS vs a = 0.003, null q95 = 0.051 -> within null: True\n  arm d  : {'quickselect': 12}  modal=quickselect (same as a: True); JS vs a = 0.140, null q95 = 0.070 -> within null: False\n  arm K0 : {'quickselect': 8, 'size_k_heap': 7}  modal=quickselect (same as a: True); JS vs a = 0.003, null q95 = 0.051 -> within null: True\n\nT06 (default hash_set; catalogue ['hash_set', 'sort_adjacent', 'floyd', 'value_binary_search', 'index_marking'])\n  arm a  : non-default landings {'index_marking': 12}\n  arm c  : no non-default attempt\n  arm d  : {'index_marking': 11}  modal=index_marking (same as a: True); JS vs a = 0.000, null q95 = 0.000 -> within null: False\n  arm K0 : no non-default attempt\n\nT05 (default hash_map; catalogue ['hash_map', 'sort_two_pointers', 'brute_force', 'sort_binary_search'])\n  arm a  : non-default landings {'brute_force': 13}\n  arm c  : {'brute_force': 4}  modal=brute_force (same as a: True); JS vs a = 0.029, null q95 = 0.029 -> within null: False\n  arm d  : {'brute_force': 12}  modal=brute_force (same as a: True); JS vs a = 0.000, null q95 = 0.000 -> within null: False\n  arm K0 : {'brute_force': 5}  modal=brute_force (same as a: True); JS vs a = 0.018, null q95 = 0.018 -> within null: False\n\nT10 (default union_find; catalogue ['bfs', 'dfs', 'union_find', 'label_propagation'])\n  arm a  : non-default landings {'bfs': 10, 'dfs': 5}\n  arm c  : {'dfs': 8, 'bfs': 7}  modal=dfs (same as a: False); JS vs a = 0.024, null q95 = 0.033 -> within null: True\n  arm d  : {'dfs': 11, 'bfs': 1}  modal=dfs (same as a: False); JS vs a = 0.225, null q95 = 0.055 -> within null: False\n  arm K0 : {'dfs': 6, 'bfs': 9}  modal=bfs (same as a: True); JS vs a = 0.003, null q95 = 0.033 -> within null: True\n\nT13 (default sort_sweep; catalogue ['sort_sweep', 'interval_tree', 'union_find'])\n  arm a  : non-default landings {'union_find': 2, 'other': 8}\n  arm c  : {'other': 3, 'union_find': 1}  modal=other (same as a: True); JS vs a = 0.011, null q95 = 0.067 -> within null: True\n  arm d  : no non-default attempt\n  arm K0 : {'other': 5}  modal=other (same as a: True); JS vs a = 0.031, null q95 = 0.035 -> within null: True\n\n--- cell 25 [stdout]\nC2c: 0.0s (N_PERM=100, N_BOOT_RHO=100)\n        V        class  F_direct    hit  fire_rate\ntask                                              \nT03  0.41  HIGH_DIRECT      0.79   True       0.86\nT06  0.00  HIGH_DIRECT      0.92   True       1.00\nT05  0.00  HIGH_DIRECT      0.92   True       1.00\nT10  0.30  HIGH_DIRECT      0.80   True       0.99\nT13  0.00  HIGH_DIRECT      0.00  False       1.00\n\nhit fraction 0.80, Spearman rho -0.34 (one-sided permutation p 0.29, task-bootstrap 95% [-1.0, 0.67]) -> C2c INCONCLUSIVE\nfull run: hit fraction 0.80, rho -0.34, p 0.30 -> INCONCLUSIVE\n\n--- cell 25 [stderr]\n/tmp/ipykernel_644/377182169.py:38: ConstantInputWarning: An input array is constant; the correlation coefficient is not defined.\n  r_ = stats.spearmanr(v[ii], f[ii]).statistic\n\n--- cell 27 [stdout]\n10:43:25|INFO   |analysis: gated=['T03', 'T06', 'T05', 'T10', 'T13']; C2a=DISCONFIRMED point={'F_prompt': 0.578, 'F_direct': 0.719, 'I': -0.297, 'F_prompt_mean': 0.542, 'F_direct_mean': 0.685, 'F_K0': 0.609}; C2c=INCONCLUSIVE (hit 0.8, rho -0.335)\n\n--- cell 27 [stdout]\ndescriptive route fractions on non-gated tasks (ban mostly fails there; s_b - s_a ~ 0 makes F unstable):\n     F_prompt  F_direct\nT04      0.00      0.33\nR1        NaN       NaN\nT08       NaN       NaN\nR3        NaN       NaN\nR6       -inf       NaN\n\n--- cell 33 [stderr]\nThe tied weights mapping and config for this model specifies to tie model.embed_tokens.weight to lm_head.weight, but both are present in the checkpoints, so we will NOT tie them. You should update the config with `tie_word_embeddings=False` to silence this warning\n\n--- cell 33 [stdout]\n10:43:30|INFO   |HF model Qwen/Qwen3-0.6B loaded in 4s; attn=ko_sdpa; device=cpu; dtype=torch.float32\n\n--- cell 33 [stdout]\nban  condition [p0=3, p1=16): 'Do not use a hash set of seen values for this task.\\n\\n'\ntwin condition [p0=3, p1=16): 'Do not use fire for this task. . . . . .\\n\\n'\nP = 142 prompt tokens (twin: 142); ids identical outside [p0, p1): True\nban prompt: '<|im_start|>user\\nDo not use a hash set of seen values for this task.\\n\\nTask: write a Python function solve(nums) that returns the repeated value in nums. The argument nums is a list of n + 1 integers, where 1 <= n <= 10000, and every value lies between 1 and n inclusive. Exactly one value occurs more than once, and it may occur two or more times; every other value occurs at most once. Return the repeated value as an int.\\n\\nUse only the Python standard library. Return only one ```python code block containing the function solve and any helpers, with no example usage and no explanation.<|im_end|>\\n<|im_start|>assistant\\n<think>\\n\\n</think>\\n\\n'\n\n--- cell 33 [stdout]\n10:43:34|INFO   |[demo] T06 L=142 arms=['a', 'b', 'c', 'd'] rows=4 steps=7 1.6s\n\n--- cell 33 [stdout]\n10:43:35|INFO   |[demo] T06 L=129 arms=['K0'] rows=1 steps=7 0.8s\n\n--- cell 33 [stdout]\nengine: 4.8s for 5 rows (ENGINE_MAX_NEW=8, ENGINE_N_SLOTS=1, device=cpu)\n\n--- cell 35 [stdout]\n\n=================== CRN slot (T06, W1, k=0): uniform-stream seed 8601073648214344221\n--- arm a\n  Qwen/Qwen3-0.6B (live, ban): 8 tokens, length, leaves arm b at token None\n      ```python\n      def solve(nums):\n         \n  Qwen3-8B (full run): label = index_marking (passed tests: True), 49 tokens, leaves arm b at token 8\n      ```python\n      def solve(nums):\n          while nums[0] != nums[nums[0]]:\n              nums[nums[0]], nums[0] = nums[0], nums[nums[0]]\n          return nums[0]\n      ```\n--- arm b\n  Qwen/Qwen3-0.6B (live, twin_A): 8 tokens, length, leaves arm b at token None\n      ```python\n      def solve(nums):\n         \n  Qwen3-8B (full run): label = hash_set (passed tests: True), 34 tokens, leaves arm b at token None\n      ```python\n      def solve(nums):\n          seen = set()\n          for num in nums:\n              if num in seen:\n                  return num\n              seen.add(num)\n      ```\n--- arm c\n  Qwen/Qwen3-0.6B (live, splice:twinA[0,p1)|ban[p1,P)+R(ban)): 8 tokens, length, leaves arm b at token None\n      ```python\n      def solve(nums):\n         \n  Qwen3-8B (full run): label = hash_set (passed tests: True), 34 tokens, leaves arm b at token None\n      ```python\n      def solve(nums):\n          seen = set()\n          for num in nums:\n              if num in seen:\n                  return num\n              seen.add(num)\n      ```\n--- arm d\n  Qwen/Qwen3-0.6B (live, splice:ban[0,p1)|twinA[p1,P)+R(twinA)): 8 tokens, length, leaves arm b at token None\n      ```python\n      def solve(nums):\n         \n  Qwen3-8B (full run): label = hash_set (passed tests: True), 33 tokens, leaves arm b at token 10\n      ```python\n      def solve(nums):\n          seen = []\n          for num in nums:\n              if num in seen:\n                  return num\n              seen.append(num)\n      ```\n--- arm K0\n  Qwen/Qwen3-0.6B (live, ban|K0(span dropped)): 8 tokens, length, leaves arm b at token None\n      ```python\n      def solve(nums):\n         \n  Qwen3-8B (full run): label = hash_set (passed tests: True), 34 tokens, leaves arm b at token None\n      ```python\n      def solve(nums):\n          seen = set()\n          for num in nums:\n              if num in seen:\n                  return num\n              seen.add(num)\n      ```\n\n--- cell 37 [display_data] keys=['image/png', 'text/plain']\n--- cell 38 [display_data] keys=['image/png', 'text/plain']\n--- cell 39 [stdout]\n                                                                                     demo subset                                    full run\nquantity                                                                                                                                    \ngated tasks (frozen gate)                                                T03, T06, T05, T10, T13                     T03, T06, T05, T10, T13\npooled F_prompt [jackknife 95%, primary]                                     0.578 [-0.00, 1.16]                          0.611 [0.06, 1.17]\npooled F_direct [jackknife 95%, primary]                                      0.719 [0.34, 1.10]                          0.744 [0.38, 1.11]\npooled I [jackknife 95%, primary]                                           -0.297 [-0.99, 0.40]                        -0.355 [-0.98, 0.27]\npooled F_K0 [jackknife 95%, primary]                                          0.609 [0.06, 1.16]                          0.621 [0.08, 1.16]\nC2a verdict (percentile / BCa / jackknife)            DISCONFIRMED / DISCONFIRMED / DISCONFIRMED  DISCONFIRMED / DISCONFIRMED / DISCONFIRMED\nP_boot(F_prompt <= 1/2), P_boot(F_direct >= 1/3)                                      0.34, 1.00                                  0.28, 0.99\nmixed GLM F_prompt, F_direct                                                          0.57, 0.77                                  0.74, 0.89\nC2c: hit fraction, Spearman rho (perm p) -> decision        0.80, -0.34 (p 0.29) -> INCONCLUSIVE        0.80, -0.34 (p 0.30) -> INCONCLUSIVE\nT03 F_prompt / F_direct                                                              1.00 / 0.79                                 1.00 / 0.74\nT06 F_prompt / F_direct                                                              0.00 / 0.92                                 0.04 / 0.99\nT05 F_prompt / F_direct                                                              0.31 / 0.92                                 0.41 / 0.96\nT10 F_prompt / F_direct                                                              1.00 / 0.80                                 1.00 / 0.80\nT13 F_prompt / F_direct                                                              0.40 / 0.00                                 0.39 / 0.02", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
````

### [227] THINKING · 2026-10-26 10:44:16 UTC

```
The minimal-config run finished in 44s and reproduces the headline verdicts (C2a DISCONFIRMED, similar F and ρ values). Before scaling up, I'll check whether the full run shows the same `within_null=False` quirk so I can describe it accurately.
```

### [228] TOOL CALL — Bash · 2026-10-26 10:44:16 UTC

```
Check full-run landing results for the strict-null quirk:
A=/ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16; python3 -I -c "
import json
d=json.load(open('$A/results/landing_by_route.json'))
for t in ['T06','T05','T03']:
    for X in ['c','d','K0']:
        v=d[t].get(X)
        if v: print(t, X, {k: v[k] for k in ('modal','JS_vs_a','null_q95','within_null')})
"
```

### [229] TOOL RESULT — Bash · 2026-10-26 10:44:16 UTC

```
{"stdout": "T06 c {'modal': 'index_marking', 'JS_vs_a': 0.12450042152760885, 'null_q95': 0.24362787686326068, 'within_null': True}\nT06 d {'modal': 'index_marking', 'JS_vs_a': 0.008556779383390868, 'null_q95': 0.007426662009941947, 'within_null': False}\nT06 K0 {'modal': 'floyd', 'JS_vs_a': 0.3506894937609967, 'null_q95': 0.1454747976509406, 'within_null': False}\nT05 c {'modal': 'brute_force', 'JS_vs_a': 0.003718275007380818, 'null_q95': 0.003718275007380818, 'within_null': False}\nT05 d {'modal': 'brute_force', 'JS_vs_a': 4.259878336288414e-06, 'null_q95': 4.259878336288414e-06, 'within_null': False}\nT05 K0 {'modal': 'brute_force', 'JS_vs_a': 0.004024812674086405, 'null_q95': 0.004024812674086405, 'within_null': False}\nT03 c {'modal': 'quickselect', 'JS_vs_a': 0.013263425940496974, 'null_q95': 0.008400022561967778, 'within_null': False}\nT03 d {'modal': 'quickselect', 'JS_vs_a': 0.11461383562440827, 'null_q95': 0.010559458586885472, 'within_null': False}\nT03 K0 {'modal': 'quickselect', 'JS_vs_a': 0.005193030244134297, 'null_q95': 0.008400022561967778, 'within_null': True}", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [230] THINKING · 2026-10-26 10:44:32 UTC

```
The full run confirms this is existing behavior (e.g. T05's `within_null: False`), so I'll leave the code as-is and just add a note. Next, I'll add a filter in the imports cell to suppress the two benign warnings.
```

### [231] TOOL CALL — NotebookEdit · 2026-10-26 10:44:32 UTC

```
{'notebook_path': '/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb', 'cell_id': 'bc3a2b51', 'edit_mode': 'replace', 'cell_type': 'code', 'new_source': '# original imports of the code used below (src/cfg.py, src/engine.py, src/gpu.py, src/analysis/analysis.py)\nimport collections\nimport contextlib\nimport gc\nimport hashlib\nimport json\nimport math\nimport os\nimport re\nimport sys\nimport time\nfrom pathlib import Path\nfrom typing import Any, Callable, Iterable, Iterator\n\nimport numpy as np\nimport torch\nfrom loguru import logger\nfrom scipy import stats\n\n# notebook additions: tables and figures; silence two benign warnings the original code also raises\n# (nanmean over bootstrap draws where every task has s_b == s_a; Spearman on a constant bootstrap resample)\nimport warnings\n\nimport matplotlib.pyplot as plt\nimport pandas as pd\n\nwarnings.filterwarnings("ignore", message="Mean of empty slice", category=RuntimeWarning)\nwarnings.filterwarnings("ignore", message="An input array is constant")\npd.set_option("display.width", 200)\npd.set_option("display.max_columns", 30)\nprint("torch", torch.__version__, "| numpy", np.__version__, "| cuda available:", torch.cuda.is_available())'}
```

### [232] TOOL RESULT — NotebookEdit [ERROR] · 2026-10-26 10:44:32 UTC

```
Error: File has been modified since read, either by the user or by a linter. Read it again before attempting to write it.
```

### [233] ASSISTANT · 2026-10-26 10:44:35 UTC

```
nbconvert rewrote the notebook, so NotebookEdit needs a fresh Read. That also lets me look at the rendered figures.
```

### [234] TOOL CALL — Read · 2026-10-26 10:44:35 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb
```

### [235] TOOL RESULT — Read [ERROR] · 2026-10-26 10:44:35 UTC

```
Error: File content (56387 tokens) exceeds maximum allowed tokens (25000). Use offset and limit parameters to read specific portions of the file, or search for specific content instead of reading the whole file.
```

### [236] THINKING · 2026-10-26 10:44:45 UTC

```
I'll extract the two figures to a temporary folder to inspect them, then clear the notebook outputs so NotebookEdit can process it—the next test run will regenerate those outputs anyway.
```

### [237] TOOL CALL — Bash · 2026-10-26 10:44:45 UTC

```
Extract rendered figures from the executed notebook:
mkdir -p _tmp_figs && python3 -I - <<'EOF'
import json, base64
nb = json.load(open("code_demo.ipynb"))
n = 0
for i, c in enumerate(nb["cells"]):
    for o in c.get("outputs", []):
        if o["output_type"] == "display_data" and "image/png" in o["data"]:
            n += 1
            open(f"_tmp_figs/fig{n}_cell{i}.png", "wb").write(base64.b64decode(o["data"]["image/png"]))
print(n, "figures")
EOF
ls -la _tmp_figs
```

### [238] TOOL RESULT — Bash · 2026-10-26 10:44:45 UTC

```
{"stdout": "2 figures\ntotal 3136\ndrwxrwxrwx 2 aii-agent aii-agent 1018630 Oct 26 10:44 .\ndrwxrwxrwx 5 aii-agent aii-agent 2000274 Oct 26 10:44 ..\n-rw-rw-rw- 1 aii-agent aii-agent   96897 Oct 26 10:44 fig1_cell37.png\n-rw-rw-rw- 1 aii-agent aii-agent   93881 Oct 26 10:44 fig2_cell38.png", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [239] TOOL CALL — Read · 2026-10-26 10:44:51 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/_tmp_figs/fig1_cell37.png
```

### [240] TOOL RESULT — Read · 2026-10-26 10:44:51 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [241] TOOL CALL — Read · 2026-10-26 10:44:51 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/_tmp_figs/fig2_cell38.png
```

### [242] TOOL RESULT — Read · 2026-10-26 10:44:51 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [243] THINKING · 2026-10-26 10:45:03 UTC

```
Both figures render correctly, though the T03/T10 labels overlap at (1.0, 0.8) and the "I = 0" text collides with T06 on the route plane. I'll remove the temp figures and clear outputs so NotebookEdit can read the notebook.
```

### [244] TOOL CALL — Bash · 2026-10-26 10:45:03 UTC

```
Remove temp figures and clear notebook outputs:
rm -rf _tmp_figs && python3 -I - <<'EOF'
import json
p = "code_demo.ipynb"
nb = json.load(open(p))
for c in nb["cells"]:
    if c["cell_type"] == "code":
        c["outputs"] = []
        c["execution_count"] = None
json.dump(nb, open(p, "w"), indent=1, ensure_ascii=False)
open(p, "a").write("\n")
print("cleared;", len(nb["cells"]), "cells")
EOF
ls -la code_demo.ipynb
```

### [245] TOOL RESULT — Bash · 2026-10-26 10:45:03 UTC

```
{"stdout": "cleared; 40 cells\n-rw-rw-rw- 1 aii-agent aii-agent 117840 Oct 26 10:45 code_demo.ipynb", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [246] TOOL CALL — Read · 2026-10-26 10:45:07 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb
```

### [247] TOOL RESULT — Read [ERROR] · 2026-10-26 10:45:07 UTC

```
Error: File content (47060 tokens) exceeds maximum allowed tokens (25000). Use offset and limit parameters to read specific portions of the file, or search for specific content instead of reading the whole file.
```

### [248] ASSISTANT · 2026-10-26 10:45:13 UTC

```
Even without outputs the notebook exceeds the Read limit, so I'll read it in cell ranges, which should satisfy NotebookEdit's read requirement.
```

### [249] TOOL CALL — Read · 2026-10-26 10:45:13 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/code_demo.ipynb
```

### [250] TOOL RESULT — Read [ERROR] · 2026-10-26 10:45:13 UTC

```
Error: File content (47060 tokens) exceeds maximum allowed tokens (25000). Use offset and limit parameters to read specific portions of the file, or search for specific content instead of reading the whole file.
```

### [251] THINKING · 2026-10-26 10:45:35 UTC

```
Since the Read tool can't page the .ipynb and loading 47K tokens each run is wasteful, I'll instead apply the remaining fixes as exact, assert-checked string replacements on cell sources by cell id (equivalent to NotebookEdit's replace), covering round-1 fixes plus the round-2 scaling config.
```

### [252] TOOL CALL — Bash · 2026-10-26 10:45:35 UTC

```
Apply round-1 fixes and round-2 scaling config to the notebook:
python3 -I - <<'PYEOF'
import json
p = "code_demo.ipynb"
nb = json.load(open(p))
cells = {c["id"]: c for c in nb["cells"]}

def edit(cid, old, new):
    src = "".join(cells[cid]["source"])
    assert src.count(old) == 1, (cid, src.count(old), old[:60])
    src = src.replace(old, new)
    cells[cid]["source"] = src.splitlines(keepends=True)

# 1. imports: silence two benign warnings that the original code also raises
edit("bc3a2b51",
'''# notebook additions: tables and figures
import matplotlib.pyplot as plt
import pandas as pd

pd.set_option''',
'''# notebook additions: tables and figures; silence two benign warnings the original code also raises
# (nanmean over bootstrap draws where every task has s_b == s_a; Spearman on a constant bootstrap resample)
import warnings

import matplotlib.pyplot as plt
import pandas as pd

warnings.filterwarnings("ignore", message="Mean of empty slice", category=RuntimeWarning)
warnings.filterwarnings("ignore", message="An input array is constant")
pd.set_option''')

# 2. landing markdown: explain the strict-inequality quirk of the original null test
edit("1798f0d7",
"`within_null = True` means the route lands where the full ban lands.",
"`within_null = True` means the route lands where the full ban lands.\n\n"
"One quirk of the original test is kept. When arm `a` lands on a single mechanism (e.g. T05: all `brute_force`), the "
"JS divergence and its null quantile coincide, and the strict `js < q95` reports `False`. The full run shows the "
"same on T05, so in that case read `same_modal_as_a` instead.")

# 3. config: scaling round 2 (~10x)
for old, new in [("N_BOOT = 100           #", "N_BOOT = 1000          #"),
                 ("N_BOOT_TASK = 100      #", "N_BOOT_TASK = 1000     #"),
                 ("N_PERM = 100           #", "N_PERM = 10000         #"),
                 ("N_BOOT_RHO = 100       #", "N_BOOT_RHO = 1000      #"),
                 ("LANDING_N_REP = 20     #", "LANDING_N_REP = 200    #"),
                 ("ENGINE_MAX_NEW = 8                     #", "ENGINE_MAX_NEW = 64                    #"),
                 ("ENGINE_N_SLOTS = 1                     #", "ENGINE_N_SLOTS = 2                     #")]:
    edit("90440e47", old, new)

# 4. route plane: separate overlapping task labels, move the I = 0 label, widen x range for labels
edit("fb2f15fe", 'ax.text(0.02, 0.9, "I = 0 (additive)", fontsize=7, color="grey", rotation=-38)',
     'ax.text(0.86, 0.17, "I = 0 (additive)", fontsize=7, color="grey", rotation=-38)')
edit("fb2f15fe", "for t, v in route[\"per_task\"].items():\n    fp, fdr = v[\"F_prompt\"], v[\"F_direct\"]\n    ax.errorbar(",
     "for i, (t, v) in enumerate(route[\"per_task\"].items()):\n    fp, fdr = v[\"F_prompt\"], v[\"F_direct\"]\n    ax.errorbar(")
edit("fb2f15fe", 'xytext=(7, 5), textcoords="offset points", fontsize=8)',
     'xytext=(7, 6 if i % 2 == 0 else -13), textcoords="offset points",\n                fontsize=8)')
edit("fb2f15fe", "ax.set_xlim(-0.15, 1.15)", "ax.set_xlim(-0.15, 1.35)")

json.dump(nb, open(p, "w"), indent=1, ensure_ascii=False)
open(p, "a").write("\n")
print("edits applied")
PYEOF
```

### [253] TOOL RESULT — Bash · 2026-10-26 10:45:35 UTC

```
{"stdout": "edits applied", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [254] ASSISTANT · 2026-10-26 10:45:43 UTC

```
Scaling round 1 (≈10× resampling counts; engine at 64 tokens × 2 slots). Re-running the full clean-venv test:
```

### [255] TOOL CALL — Bash · 2026-10-26 10:45:43 UTC

```
Test-run notebook at scaling round 1 in a clean venv:
UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art__5akZ9W9iZM4-bfb6955ec1d9 && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art__5akZ9W9iZM4-bfb6955ec1d9/bin/python jupyter ipykernel && T0=$(date +%s) && /tmp/aii_nb_test_envs/art__5akZ9W9iZM4-bfb6955ec1d9/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb; echo "EXIT=$? RUNTIME=$(( $(date +%s) - T0 ))s"
```

### [256] TOOL RESULT — Bash · 2026-10-26 10:45:43 UTC

```
{"stdout": "", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false, "backgroundTaskId": "b16ra3jkh"}
```

### [257] THINKING · 2026-10-26 10:45:57 UTC

```
Edits so far: the analysis code is verbatim aside from path/constant updates, the engine is unchanged except for device/dtype loading, and I've added a row adapter, warning filters, and figures. Now I'll wait for the test notification before continuing.
```

### [258] TOOL CALL — Bash · 2026-10-26 10:45:57 UTC

```
Wait briefly then check test progress:
sleep 45; tail -3 /tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-3-art--5akZ9W9iZM4/c71db1cb-129d-4e37-954d-e401f6949d31/tasks/b16ra3jkh.output
```

### [259] TOOL RESULT — Bash [ERROR] · 2026-10-26 10:45:57 UTC

```
Error: Blocked: sleep 45 followed by: tail -3 /tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-3-art--5akZ9W9iZM4/c71db1cb-129d-4e37-954d-e401f6949d31/tasks/b16ra3jkh.output. To wait for a condition, use Monitor with an until-loop (e.g. `until <check>; do sleep 2; done`). To wait for a command you started, use run_in_background: true. Do not chain shorter sleeps to work around this block.
```

### [260] ASSISTANT · 2026-10-26 10:46:21 UTC

```
I'll draft the README while the test runs. The deterministic numbers (point estimates, jackknife intervals) won't change with scaling, and I'll fill in the rest after the final run.
```

### [261] TOOL CALL — Write · 2026-10-26 10:46:21 UTC

````
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/README.md

# Demo: where a coding ban takes effect in Qwen3-8B (experiment-16)

A runnable, Colab-ready walkthrough of the experiment **"Where a coding ban takes effect in Qwen3-8B"**
(`art__5akZ9W9iZM4`, part of *Prompt bans substitute, not just subtract*).

The experiment asks which internal route carries a prompt ban such as *"Do not use a hash set of seen values for this
task."* into Qwen3-8B's code. It samples every arm of a slot with common random numbers (CRN) and builds the arms by
splicing KV caches:

| arm | cache read by the generated tokens |
|---|---|
| `a` | full ban prompt |
| `b` | token-length-matched neutral twin |
| `c` | twin condition + ban task-spec states (prompt route) |
| `d` | ban condition + twin task-spec states (direct route) |
| `K0` | the ban with its condition span knocked out |

Each arm writes programs, and frozen labellers name the mechanism of each program.

## What the notebook does

`code_demo.ipynb` converts the experiment's `method.py` pipeline into notebook cells. The original code is kept
verbatim except for file paths and resampling counts.

1. **S9 analysis** (`src/analysis/analysis.py`, `gpu.compute_gate`) on a curated subset of the labelled route arms:
   100 CRN slots, i.e. 500 programs written by Qwen3-8B. It covers:
   - the gate;
   - per-arm default shares;
   - route fractions `F_prompt`, `F_direct`, `I`, `F_K0`, with the hierarchical task → template → slot bootstrap,
     leave-one-task-out jackknife (primary), BCa, leave-one-template-out and the Bayesian mixed GLM;
   - the C2a verdict;
   - CRN flip tables with exact McNemar tests;
   - identical-output rates and first divergence;
   - landing by route;
   - C2c.
2. **The HF engine** (`src/engine.py` + `gpu.Worker.arm_state`): prefill, KV splice, span drop and CRN inverse-CDF
   sampling.
   - It runs on one CRN slot set (T06 / W1) on CPU with **Qwen/Qwen3-0.6B**, a mechanics stand-in. It shares Qwen3-8B's
     tokenizer, so the frozen prompt ids and the run's exact uniform streams apply unchanged.
   - The Qwen3-8B rows of the same slots are shown beside the live output.
3. **Figures and a summary table** comparing the subset with the full run.

The demo does not re-run the Qwen3-8B GPU queue (about 1.8 L4 GPU-hours), the frozen labellers (bench harness + LLM
judge), or the stages that need the upstream bench folders.

## Results of the executed notebook

The demo has 15 slots per gated task; the full run has 100. Point estimates and the leave-one-task-out jackknife
intervals are deterministic.

| quantity | demo subset | full run |
|---|---|---|
| gated tasks | T03, T06, T05, T10, T13 (frozen gate) | same |
| pooled F_prompt [jackknife 95%] | 0.578 [-0.00, 1.16] | 0.611 [0.06, 1.17] |
| pooled F_direct [jackknife 95%] | 0.719 [0.34, 1.10] | 0.744 [0.38, 1.11] |
| pooled I | -0.297 | -0.355 |
| pooled F_K0 | 0.609 | 0.621 |
| C2a ("prompt route carries >= 2/3") | DISCONFIRMED under all three intervals | DISCONFIRMED |
| C2c (veto sufficiency predicts F_direct) | hit fraction 0.80, rho -0.34 -> INCONCLUSIVE | 0.80, -0.34 -> INCONCLUSIVE |
| per task F_prompt / F_direct | T03 1.00/0.79, T06 0.00/0.92, T05 0.31/0.92, T10 1.00/0.80, T13 0.40/0.00 | T03 1.00/0.74, T06 0.04/0.99, T05 0.41/0.96, T10 1.00/0.80, T13 0.39/0.02 |

The 100-slot subset reproduces the experiment's conclusions. The route mechanism is task-dependent:
- **T03/T10:** redundant, since either route alone suffices.
- **T05/T06:** the direct route carries the ban.
- **T13:** superadditive, since both routes are needed.

So the pre-registered "prompt route carries >= 2/3 of the ban" claim is disconfirmed.

## Layout

| path | what it is |
|---|---|
| `code_demo.ipynb` | the demo notebook, executed, with outputs |
| `mini_demo_data.json` | demo data (~750 kB). One dataset, `route_arms`: 100 CRN-slot examples, each with its five arms' labels and token ids. `metadata` holds the frozen inputs the notebook reads instead of files: gate, commit-#2 veto classes, n-grams, mechanism catalogues, full-run reference numbers, and the prompt ids + Qwen3-8B rows of the engine slots |
| `scripts/build_mini_demo_data.py` | rebuilds `mini_demo_data.json` from the experiment-16 folder, with the selection rule in its docstring |
| `.aii/manifest.yaml` | storage decisions; nothing in this folder is heavy |

## How to run

**Colab.** Open `code_demo.ipynb` and run all cells.
- The install cell adds only `loguru` there.
- The notebook fetches `mini_demo_data.json` from this repository's raw GitHub URL and falls back to a local copy.
- It downloads Qwen/Qwen3-0.6B (about 1.5 GB) from the Hugging Face Hub.

**Locally** (Python 3.12):

```bash
uv venv .venv --python 3.12 --seed
uv pip install --python .venv/bin/python jupyter ipykernel
.venv/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb
```

Off Colab, the install cell pins Colab's versions:
- torch 2.9.0+cpu from the PyTorch CPU index;
- transformers 5.0.0, numpy 2.0.2, pandas 2.2.2, scipy 1.16.3, statsmodels 0.14.6 and matplotlib 3.10.0.

**Knobs** are in the config cell, each commented with its original value. The resampling counts already equal the
experiment's (`N_BOOT` 10000, `N_PERM` 100000, ...).
- `RUN_ENGINE = False` skips the model.
- `ENGINE_MODEL_ID = "Qwen/Qwen3-8B"` runs the original model, with its revision, `ENGINE_DTYPE = torch.bfloat16` and
  a GPU with more than 17 GB.

**Rebuild the demo data** from the experiment folder (`<experiment-16>` is the folder holding `full_method_out.json`,
`data/`, `prompts/`, `predictions/` and `inputs/bench/`):

```bash
python scripts/build_mini_demo_data.py <experiment-16> mini_demo_data.json
```

## Restoring removed files

Nothing in this folder is marked `delete` in `.aii/manifest.yaml`. Every file here is a small text or code file and
is kept. The notebook needs two things from outside this folder, and both are fetched on demand:

| what | where it lives | how to get it |
|---|---|---|
| Qwen/Qwen3-0.6B weights at revision `c1899de289a04d12100db370d81485cdf75e47ca` (~1.5 GB) | Hugging Face cache (`$HF_HOME`), not this folder | downloaded automatically by the engine cell, or `huggingface-cli download Qwen/Qwen3-0.6B --revision c1899de289a04d12100db370d81485cdf75e47ca` |
| Python packages | the notebook's environment | installed by the notebook's first cell (see "How to run") |
````

### [262] TOOL RESULT — Write · 2026-10-26 10:46:21 UTC

````
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/README.md", "content": "# Demo: where a coding ban takes effect in Qwen3-8B (experiment-16)\n\nA runnable, Colab-ready walkthrough of the experiment **\"Where a coding ban takes effect in Qwen3-8B\"**\n(`art__5akZ9W9iZM4`, part of *Prompt bans substitute, not just subtract*).\n\nThe experiment asks which internal route carries a prompt ban such as *\"Do not use a hash set of seen values for this\ntask.\"* into Qwen3-8B's code. It samples every arm of a slot with common random numbers (CRN) and builds the arms by\nsplicing KV caches:\n\n| arm | cache read by the generated tokens |\n|---|---|\n| `a` | full ban prompt |\n| `b` | token-length-matched neutral twin |\n| `c` | twin condition + ban task-spec states (prompt route) |\n| `d` | ban condition + twin task-spec states (direct route) |\n| `K0` | the ban with its condition span knocked out |\n\nEach arm writes programs, and frozen labellers name the mechanism of each program.\n\n## What the notebook does\n\n`code_demo.ipynb` converts the experiment's `method.py` pipeline into notebook cells. The original code is kept\nverbatim except for file paths and resampling counts.\n\n1. **S9 analysis** (`src/analysis/analysis.py`, `gpu.compute_gate`) on a curated subset of the labelled route arms:\n   100 CRN slots, i.e. 500 programs written by Qwen3-8B. It covers:\n   - the gate;\n   - per-arm default shares;\n   - route fractions `F_prompt`, `F_direct`, `I`, `F_K0`, with the hierarchical task → template → slot bootstrap,\n     leave-one-task-out jackknife (primary), BCa, leave-one-template-out and the Bayesian mixed GLM;\n   - the C2a verdict;\n   - CRN flip tables with exact McNemar tests;\n   - identical-output rates and first divergence;\n   - landing by route;\n   - C2c.\n2. **The HF engine** (`src/engine.py` + `gpu.Worker.arm_state`): prefill, KV splice, span drop and CRN inverse-CDF\n   sampling.\n   - It runs on one CRN slot set (T06 / W1) on CPU with **Qwen/Qwen3-0.6B**, a mechanics stand-in. It shares Qwen3-8B's\n     tokenizer, so the frozen prompt ids and the run's exact uniform streams apply unchanged.\n   - The Qwen3-8B rows of the same slots are shown beside the live output.\n3. **Figures and a summary table** comparing the subset with the full run.\n\nThe demo does not re-run the Qwen3-8B GPU queue (about 1.8 L4 GPU-hours), the frozen labellers (bench harness + LLM\njudge), or the stages that need the upstream bench folders.\n\n## Results of the executed notebook\n\nThe demo has 15 slots per gated task; the full run has 100. Point estimates and the leave-one-task-out jackknife\nintervals are deterministic.\n\n| quantity | demo subset | full run |\n|---|---|---|\n| gated tasks | T03, T06, T05, T10, T13 (frozen gate) | same |\n| pooled F_prompt [jackknife 95%] | 0.578 [-0.00, 1.16] | 0.611 [0.06, 1.17] |\n| pooled F_direct [jackknife 95%] | 0.719 [0.34, 1.10] | 0.744 [0.38, 1.11] |\n| pooled I | -0.297 | -0.355 |\n| pooled F_K0 | 0.609 | 0.621 |\n| C2a (\"prompt route carries >= 2/3\") | DISCONFIRMED under all three intervals | DISCONFIRMED |\n| C2c (veto sufficiency predicts F_direct) | hit fraction 0.80, rho -0.34 -> INCONCLUSIVE | 0.80, -0.34 -> INCONCLUSIVE |\n| per task F_prompt / F_direct | T03 1.00/0.79, T06 0.00/0.92, T05 0.31/0.92, T10 1.00/0.80, T13 0.40/0.00 | T03 1.00/0.74, T06 0.04/0.99, T05 0.41/0.96, T10 1.00/0.80, T13 0.39/0.02 |\n\nThe 100-slot subset reproduces the experiment's conclusions. The route mechanism is task-dependent:\n- **T03/T10:** redundant, since either route alone suffices.\n- **T05/T06:** the direct route carries the ban.\n- **T13:** superadditive, since both routes are needed.\n\nSo the pre-registered \"prompt route carries >= 2/3 of the ban\" claim is disconfirmed.\n\n## Layout\n\n| path | what it is |\n|---|---|\n| `code_demo.ipynb` | the demo notebook, executed, with outputs |\n| `mini_demo_data.json` | demo data (~750 kB). One dataset, `route_arms`: 100 CRN-slot examples, each with its five arms' labels and token ids. `metadata` holds the frozen inputs the notebook reads instead of files: gate, commit-#2 veto classes, n-grams, mechanism catalogues, full-run reference numbers, and the prompt ids + Qwen3-8B rows of the engine slots |\n| `scripts/build_mini_demo_data.py` | rebuilds `mini_demo_data.json` from the experiment-16 folder, with the selection rule in its docstring |\n| `.aii/manifest.yaml` | storage decisions; nothing in this folder is heavy |\n\n## How to run\n\n**Colab.** Open `code_demo.ipynb` and run all cells.\n- The install cell adds only `loguru` there.\n- The notebook fetches `mini_demo_data.json` from this repository's raw GitHub URL and falls back to a local copy.\n- It downloads Qwen/Qwen3-0.6B (about 1.5 GB) from the Hugging Face Hub.\n\n**Locally** (Python 3.12):\n\n```bash\nuv venv .venv --python 3.12 --seed\nuv pip install --python .venv/bin/python jupyter ipykernel\n.venv/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb\n```\n\nOff Colab, the install cell pins Colab's versions:\n- torch 2.9.0+cpu from the PyTorch CPU index;\n- transformers 5.0.0, numpy 2.0.2, pandas 2.2.2, scipy 1.16.3, statsmodels 0.14.6 and matplotlib 3.10.0.\n\n**Knobs** are in the config cell, each commented with its original value. The resampling counts already equal the\nexperiment's (`N_BOOT` 10000, `N_PERM` 100000, ...).\n- `RUN_ENGINE = False` skips the model.\n- `ENGINE_MODEL_ID = \"Qwen/Qwen3-8B\"` runs the original model, with its revision, `ENGINE_DTYPE = torch.bfloat16` and\n  a GPU with more than 17 GB.\n\n**Rebuild the demo data** from the experiment folder (`<experiment-16>` is the folder holding `full_method_out.json`,\n`data/`, `prompts/`, `predictions/` and `inputs/bench/`):\n\n```bash\npython scripts/build_mini_demo_data.py <experiment-16> mini_demo_data.json\n```\n\n## Restoring removed files\n\nNothing in this folder is marked `delete` in `.aii/manifest.yaml`. Every file here is a small text or code file and\nis kept. The notebook needs two things from outside this folder, and both are fetched on demand:\n\n| what | where it lives | how to get it |\n|---|---|---|\n| Qwen/Qwen3-0.6B weights at revision `c1899de289a04d12100db370d81485cdf75e47ca` (~1.5 GB) | Hugging Face cache (`$HF_HOME`), not this folder | downloaded automatically by the engine cell, or `huggingface-cli download Qwen/Qwen3-0.6B --revision c1899de289a04d12100db370d81485cdf75e47ca` |\n| Python packages | the notebook's environment | installed by the notebook's first cell (see \"How to run\") |\n", "structuredPatch": [], "originalFile": null, "userModified": false}
````

### [263] ASSISTANT · 2026-10-26 10:46:27 UTC

```
The README draft is written. To wait for the test without polling, I'll load the Monitor tool.
```

### [264] TOOL CALL — ToolSearch · 2026-10-26 10:46:27 UTC

```
{'query': 'select:Monitor', 'max_results': 1}
```

### [265] TOOL RESULT — ToolSearch · 2026-10-26 10:46:27 UTC

```
{"matches": ["Monitor"], "query": "select:Monitor", "total_deferred_tools": 24}
```

### [266] ASSISTANT · 2026-10-26 10:46:33 UTC

```
For a single completion signal, a background `until` loop on the test's `EXIT=` line is the right tool:
```

### [267] TOOL CALL — Bash · 2026-10-26 10:46:33 UTC

```
Wait until the scaling-round-1 test finishes:
F=/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-3-art--5akZ9W9iZM4/c71db1cb-129d-4e37-954d-e401f6949d31/tasks/b16ra3jkh.output; until grep -q "EXIT=" "$F" 2>/dev/null; do sleep 2; done; grep "EXIT=" "$F"
```

### [268] TOOL RESULT — Bash · 2026-10-26 10:46:33 UTC

```
{"stdout": "", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false, "backgroundTaskId": "b2m3nwpst"}
```

### [269] ASSISTANT · 2026-10-26 10:46:37 UTC

```
While waiting, I'll write the required structured-output file, which doesn't depend on the test result:
```

### [270] TOOL CALL — Write · 2026-10-26 10:46:37 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/.terminal_claude_agent_struct_out.json

{
  "out_expected_files": {
    "notebook": "code_demo.ipynb",
    "mini_data_file": "mini_demo_data.json"
  }
}
```

### [271] TOOL RESULT — Write · 2026-10-26 10:46:37 UTC

```
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/.terminal_claude_agent_struct_out.json", "content": "{\n  \"out_expected_files\": {\n    \"notebook\": \"code_demo.ipynb\",\n    \"mini_data_file\": \"mini_demo_data.json\"\n  }\n}\n", "structuredPatch": [], "originalFile": null, "userModified": false}
```

### [272] TOOL CALL — Bash · 2026-10-26 10:46:43 UTC

```
Block until the round-1 test prints its exit line:
F=/tmp/claude-10001/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-3-art--5akZ9W9iZM4/c71db1cb-129d-4e37-954d-e401f6949d31/tasks/b16ra3jkh.output; until grep -q "EXIT=" "$F" 2>/dev/null; do sleep 2; done; grep "EXIT=" "$F"
```

### [273] TOOL RESULT — Bash · 2026-10-26 10:47:01 UTC

```
{"stdout": "EXIT=0 RUNTIME=77s", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [274] ASSISTANT · 2026-10-26 10:47:07 UTC

```
Scaling round 1 passed: **77 s** end to end. Checking per-section timings, stderr, and the live engine output at 64 tokens:
```

### [275] TOOL CALL — Bash · 2026-10-26 10:47:07 UTC

```
Show timings, stderr and engine outputs of round-1 run:
python3 -I - <<'EOF'
import json, re
nb = json.load(open("code_demo.ipynb"))
for i, c in enumerate(nb["cells"]):
    if c["cell_type"] != "code":
        continue
    for o in c.get("outputs", []):
        if o["output_type"] == "error":
            print(f"CELL {i} ERROR: {o['ename']}: {o['evalue']}")
        elif o["output_type"] == "stream":
            txt = "".join(o["text"])
            if o["name"] == "stderr":
                print(f"--- cell {i} STDERR: {txt[:400]}")
            for line in txt.splitlines():
                if re.search(r"(analysis|C2c|engine|landing analysis|\[demo\]|loaded in): ?", line) and len(line) < 220:
                    print(f"  cell {i}: {line}")
    if i == 35:
        print("=== cell 35 (engine vs 8B) ===")
        print("".join(o.get("text", "") for o in c["outputs"] if o["output_type"] == "stream")[:6000])
EOF
```

### [276] TOOL RESULT — Bash [ERROR] · 2026-10-26 10:47:07 UTC

```
Error: Exit code 1
  cell 19: route analysis: 0.1s (N_BOOT=1000, N_BOOT_TASK=1000)
  cell 23: landing analysis: 0.1s (LANDING_N_REP=200)
  cell 25: C2c: 0.3s (N_PERM=10000, N_BOOT_RHO=1000)
--- cell 33 STDERR: The tied weights mapping and config for this model specifies to tie model.embed_tokens.weight to lm_head.weight, but both are present in the checkpoints, so we will NOT tie them. You should update the config with `tie_word_embeddings=False` to silence this warning

  cell 33: engine: 38.1s for 10 rows (ENGINE_MAX_NEW=64, ENGINE_N_SLOTS=2, device=cpu)
=== cell 35 (engine vs 8B) ===
Traceback (most recent call last):
  File "<stdin>", line 18, in <module>
TypeError: sequence item 0: expected str instance, list found
```

### [277] ASSISTANT · 2026-10-26 10:47:15 UTC

```
My inspection script mishandled list-valued stream text; the timings came through, though: analysis well under 1 s, engine 38 s for 10 rows. Printing the engine-vs-8B cell properly:
```

### [278] TOOL CALL — Bash · 2026-10-26 10:47:15 UTC

```
Print engine vs Qwen3-8B comparison output:
python3 -I - <<'EOF'
import json
nb = json.load(open("code_demo.ipynb"))
c = nb["cells"][35]
txt = "".join("".join(o["text"]) if isinstance(o["text"], list) else o["text"] for o in c["outputs"] if o["output_type"] == "stream")
print(txt[:7000])
EOF
```

### [279] TOOL RESULT — Bash · 2026-10-26 10:47:15 UTC

````
{"stdout": "=================== CRN slot (T06, W1, k=0): uniform-stream seed 8601073648214344221\n--- arm a\n  Qwen/Qwen3-0.6B (live, ban): 46 tokens, fence, leaves arm b at token 8\n      ```python\n      def solve(nums):\n          repeated = None\n          for num in nums:\n              if repeated is None:\n                  repeated = num\n              else:\n                  if repeated == num:\n                      continue\n          return repeated\n      ```\n  Qwen3-8B (full run): label = index_marking (passed tests: True), 49 tokens, leaves arm b at token 8\n      ```python\n      def solve(nums):\n          while nums[0] != nums[nums[0]]:\n              nums[nums[0]], nums[0] = nums[0], nums[nums[0]]\n          return nums[0]\n      ```\n--- arm b\n  Qwen/Qwen3-0.6B (live, twin_A): 34 tokens, fence, leaves arm b at token None\n      ```python\n      def solve(nums):\n          visited = set()\n          for num in nums:\n              if num in visited:\n                  return num\n              visited.add(num)\n      ```\n  Qwen3-8B (full run): label = hash_set (passed tests: True), 34 tokens, leaves arm b at token None\n      ```python\n      def solve(nums):\n          seen = set()\n          for num in nums:\n              if num in seen:\n                  return num\n              seen.add(num)\n      ```\n--- arm c\n  Qwen/Qwen3-0.6B (live, splice:twinA[0,p1)|ban[p1,P)+R(ban)): 62 tokens, fence, leaves arm b at token 8\n      ```python\n      def solve(nums):\n          frequency = {}\n          for num in nums:\n              if num in frequency:\n                  frequency[num] += 1\n              else:\n                  frequency[num] = 1\n          for num in frequency:\n              if frequency[num] > 1:\n                  return num\n      ```\n  Qwen3-8B (full run): label = hash_set (passed tests: True), 34 tokens, leaves arm b at token None\n      ```python\n      def solve(nums):\n          seen = set()\n          for num in nums:\n              if num in seen:\n                  return num\n              seen.add(num)\n      ```\n--- arm d\n  Qwen/Qwen3-0.6B (live, splice:ban[0,p1)|twinA[p1,P)+R(twinA)): 20 tokens, fence, leaves arm b at token 8\n      ```python\n      def solve(nums):\n          nums = set(nums)\n          return next(iter(nums))\n      ```\n  Qwen3-8B (full run): label = hash_set (passed tests: True), 33 tokens, leaves arm b at token 10\n      ```python\n      def solve(nums):\n          seen = []\n          for num in nums:\n              if num in seen:\n                  return num\n              seen.append(num)\n      ```\n--- arm K0\n  Qwen/Qwen3-0.6B (live, ban|K0(span dropped)): 62 tokens, fence, leaves arm b at token 8\n      ```python\n      def solve(nums):\n          frequency = {}\n          for num in nums:\n              if num in frequency:\n                  frequency[num] += 1\n              else:\n                  frequency[num] = 1\n          for num in frequency:\n              if frequency[num] > 1:\n                  return num\n      ```\n  Qwen3-8B (full run): label = hash_set (passed tests: True), 34 tokens, leaves arm b at token None\n      ```python\n      def solve(nums):\n          seen = set()\n          for num in nums:\n              if num in seen:\n                  return num\n              seen.add(num)\n      ```\n\n=================== CRN slot (T06, W1, k=1): uniform-stream seed 6666425756183774977\n--- arm a\n  Qwen/Qwen3-0.6B (live, ban): 34 tokens, fence, leaves arm b at token 8\n      ```python\n      def solve(nums):\n          seen = set()\n          for num in nums:\n              if num in seen:\n                  return num\n              seen.add(num)\n      ```\n  Qwen3-8B (full run): label = index_marking (passed tests: True), 53 tokens, leaves arm b at token 8\n      ```python\n      def solve(nums):\n          for i in range(len(nums)):\n              if nums[abs(nums[i]) - 1] < 0:\n                  return abs(nums[i])\n              nums[abs(nums[i]) - 1] *= -1\n      ```\n--- arm b\n  Qwen/Qwen3-0.6B (live, twin_A): 35 tokens, fence, leaves arm b at token None\n      ```python\n      def solve(nums):\n          return {v: i for i, v in enumerate(nums)}.get(None, None)  # Get the first repeated value\n      ```\n  Qwen3-8B (full run): label = hash_set (passed tests: True), 39 tokens, leaves arm b at token None\n      ```python\n      def solve(nums):\n          seen = set()\n          for num in nums:\n              if num in seen:\n                  return num\n              seen.add(num)\n          return -1\n      ```\n--- arm c\n  Qwen/Qwen3-0.6B (live, splice:twinA[0,p1)|ban[p1,P)+R(ban)): 29 tokens, fence, leaves arm b at token 10\n      ```python\n      def solve(nums):\n          return {x for x in nums if x != nums[i] for i in range(len(nums))}\n      ```\n  Qwen3-8B (full run): label = hash_set (passed tests: True), 34 tokens, leaves arm b at token 33\n      ```python\n      def solve(nums):\n          seen = set()\n          for num in nums:\n              if num in seen:\n                  return num\n              seen.add(num)\n      ```\n--- arm d\n  Qwen/Qwen3-0.6B (live, splice:ban[0,p1)|twinA[p1,P)+R(twinA)): 34 tokens, fence, leaves arm b at token 8\n      ```python\n      def solve(nums):\n          seen = set()\n          for num in nums:\n              if num in seen:\n                  return num\n              seen.add(num)\n      ```\n  Qwen3-8B (full run): label = index_marking (passed tests: True), 53 tokens, leaves arm b at token 8\n      ```python\n      def solve(nums):\n          for i in range(len(nums)):\n              if nums[abs(nums[i]) - 1] < 0:\n                  return abs(nums[i])\n              nums[abs(nums[i]) - 1] *= -1\n      ```\n--- arm K0\n  Qwen/Qwen3-0.6B (live, ban|K0(span dropped)): 23 tokens, fence, leaves arm b at token 10\n      ```python\n      def solve(nums):\n          return {x for x in nums if x != nums.index(x)}\n      ```\n  Qwen3-8B (full run): label = hash_set (passed tests: True), 34 tokens, leaves arm b at token 33\n      ```python\n      def solve(nums):\n          seen = set()\n          for num in nums:\n              if num in seen:\n                  return num\n              seen.add(num)\n      ```", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
````

### [280] THINKING · 2026-10-26 10:47:41 UTC

```
Confirmed the 0.6B model's arm `d` mirrors arm `a` exactly under CRN at k=1, matching the 8B coupling pattern, though it still uses the banned `hash_set`. For the final scaling round, I'll restore original resampling counts (10000/4000/100000/4000/2000) and run the engine across all 3 slots, keeping the 160-token cap since CPU batches can't handle the full 1024 if a row's fence never closes.
```

### [281] TOOL CALL — Bash · 2026-10-26 10:47:41 UTC

```
Set config to original analysis values and full engine slot set:
python3 -I - <<'PYEOF'
import json
p = "code_demo.ipynb"
nb = json.load(open(p))
cells = {c["id"]: c for c in nb["cells"]}

def edit(cid, old, new):
    src = "".join(cells[cid]["source"])
    assert src.count(old) == 1, (cid, src.count(old), old[:60])
    cells[cid]["source"] = src.replace(old, new).splitlines(keepends=True)

for old, new in [
    ("N_BOOT = 1000          # hierarchical task -> template -> slot bootstrap reps, pooled F (original: 10000 = cfg.N_BOOT)",
     "N_BOOT = 10000         # hierarchical task -> template -> slot bootstrap reps, pooled F (= original cfg.N_BOOT)"),
    ("N_BOOT_TASK = 1000     # template -> slot bootstrap reps per task (original: 4000, per_task_route default)",
     "N_BOOT_TASK = 4000     # template -> slot bootstrap reps per task (= original per_task_route default)"),
    ("N_PERM = 10000         # permutations of the one-sided C2c Spearman test (original: 100000 = cfg.N_PERM)",
     "N_PERM = 100000        # permutations of the one-sided C2c Spearman test (= original cfg.N_PERM)"),
    ("N_BOOT_RHO = 1000      # task bootstrap reps of the C2c rho interval (original: 4000)",
     "N_BOOT_RHO = 4000      # task bootstrap reps of the C2c rho interval (= original)"),
    ("LANDING_N_REP = 200    # resamples of the landing JS null (original: 2000, landing_null default)",
     "LANDING_N_REP = 2000   # resamples of the landing JS null (= original landing_null default)"),
    ("ENGINE_MAX_NEW = 64                    # max new tokens per row; a row also stops once its first code fence closes (original: 1024)",
     "ENGINE_MAX_NEW = 160                   # max new tokens per row; rows stop at their closing code fence, T06 programs need\n"
     "                                       # < 80 (original: 1024 -- a never-closing row would cost minutes per batch on CPU)"),
    ("ENGINE_N_SLOTS = 2                     # CRN slots k of the engine slot set to sample, of the k = 0, 1, 2 in the data (original: 20 per template)",
     "ENGINE_N_SLOTS = 3                     # CRN slots k of the engine slot set to sample: all k = 0, 1, 2 in the data (original: 20 per template)"),
]:
    edit("90440e47", old, new)
json.dump(nb, open(p, "w"), indent=1, ensure_ascii=False)
open(p, "a").write("\n")
print("".join(cells["90440e47"]["source"]))
PYEOF
```

### [282] TOOL RESULT — Bash · 2026-10-26 10:47:41 UTC

```
{"stdout": "# ------------------------------------------------------------------ analysis (src/analysis/analysis.py, src/cfg.py)\nN_SLOTS = 3            # CRN slots k per template in the demo data (original: 20 = cfg.N_PER_TEMPLATE)\nN_BOOT = 10000         # hierarchical task -> template -> slot bootstrap reps, pooled F (= original cfg.N_BOOT)\nN_BOOT_TASK = 4000     # template -> slot bootstrap reps per task (= original per_task_route default)\nN_PERM = 100000        # permutations of the one-sided C2c Spearman test (= original cfg.N_PERM)\nN_BOOT_RHO = 4000      # task bootstrap reps of the C2c rho interval (= original)\nLANDING_N_REP = 2000   # resamples of the landing JS null (= original landing_null default)\nRNG_SEED = 20261020    # cfg.RNG_SEED (unchanged)\n\n# ------------------------------------------------------------------ engine (src/engine.py, src/gpu.py)\nRUN_ENGINE = True                      # False skips the model download and the live CRN slots (section 5)\nENGINE_MODEL_ID = \"Qwen/Qwen3-0.6B\"    # original: \"Qwen/Qwen3-8B\" (cfg.MODEL_ID); same tokenizer and chat template\nENGINE_REVISION = \"c1899de289a04d12100db370d81485cdf75e47ca\"  # pinned; original: \"b968826d9c46dd6066d109eabc6255188de91218\"\nENGINE_DEVICE = \"cuda\" if torch.cuda.is_available() else \"cpu\"  # original: one NVIDIA L4 (23 GB)\nENGINE_DTYPE = torch.float32           # original: torch.bfloat16\nENGINE_MAX_NEW = 160                   # max new tokens per row; rows stop at their closing code fence, T06 programs need\n                                       # < 80 (original: 1024 -- a never-closing row would cost minutes per batch on CPU)\nENGINE_N_SLOTS = 3                     # CRN slots k of the engine slot set to sample: all k = 0, 1, 2 in the data (original: 20 per template)", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [283] ASSISTANT · 2026-10-26 10:47:57 UTC

```
The config markdown should now say the resampling counts *are* at the original values. Updating it, then launching the final test:
```

### [284] TOOL CALL — Bash · 2026-10-26 10:47:57 UTC

```
Run the final-config test in a clean venv:
python3 -I - <<'PYEOF'
import json
p = "code_demo.ipynb"
nb = json.load(open(p))
cells = {c["id"]: c for c in nb["cells"]}
cid = "4e32fa9b"
src = "".join(cells[cid]["source"])
old = ("- **Resampling counts:** the bootstrap, permutation and resampling-null counts can go straight back to the "
       "original values. They cost seconds at this data size.")
new = ("- **Resampling counts:** the bootstrap, permutation and resampling-null counts are at the original values. "
       "They cost seconds at this data size.")
assert src.count(old) == 1
cells[cid]["source"] = src.replace(old, new).splitlines(keepends=True)
json.dump(nb, open(p, "w"), indent=1, ensure_ascii=False)
open(p, "a").write("\n")
print("ok")
PYEOF
UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art__5akZ9W9iZM4-bfb6955ec1d9 && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art__5akZ9W9iZM4-bfb6955ec1d9/bin/python jupyter ipykernel && T0=$(date +%s) && /tmp/aii_nb_test_envs/art__5akZ9W9iZM4-bfb6955ec1d9/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb > /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/.nbtest.log 2>&1; echo "EXIT=$? RUNTIME=$(( $(date +%s) - T0 ))s" | tee -a /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/.nbtest.log
```

### [285] TOOL RESULT — Bash · 2026-10-26 10:49:17 UTC

```
{"stdout": "ok\nEXIT=0 RUNTIME=81s", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [286] THINKING · 2026-10-26 10:49:27 UTC

```
The final config runs in 81s end to end in a clean venv, comfortably within the 600s budget while preserving the original resampling counts. I'll now check the outputs—timings, summary table, and any errors or stderr.
```

### [287] TOOL CALL — Bash · 2026-10-26 10:49:27 UTC

```
Inspect final run timings, verdicts and summary:
python3 -I - <<'EOF'
import json, re
nb = json.load(open("code_demo.ipynb"))
def txt(o):
    t = o.get("text", "")
    return "".join(t) if isinstance(t, list) else t
n_err = 0
for i, c in enumerate(nb["cells"]):
    if c["cell_type"] != "code":
        continue
    for o in c.get("outputs", []):
        if o["output_type"] == "error":
            n_err += 1; print(f"CELL {i} ERROR: {o['ename']}: {o['evalue']}")
        elif o["output_type"] == "stream":
            if o["name"] == "stderr":
                print(f"--- cell {i} STDERR: {txt(o)[:300]!r}")
            for line in txt(o).splitlines():
                if re.search(r"^(route analysis|landing analysis|C2c:|engine:|C2a verdict|P_boot|mixed GLM|hit fraction|full run:)", line) or "[demo]" in line or "loaded in" in line:
                    print(f"  cell {i}: {line[:230]}")
print("errors:", n_err, "| execution counts:", [c.get("execution_count") for c in nb["cells"] if c["cell_type"] == "code"])
print("\n=== final summary cell ===")
print("".join(txt(o) for o in nb["cells"][-1]["outputs"] if o["output_type"] == "stream"))
EOF
ls -la code_demo.ipynb
```

### [288] TOOL RESULT — Bash · 2026-10-26 10:49:27 UTC

```
{"stdout": "  cell 19: route analysis: 0.1s (N_BOOT=10000, N_BOOT_TASK=4000)\n  cell 19: C2a verdict -- demo: DISCONFIRMED (primary interval: jackknife, by interval {'percentile': 'DISCONFIRMED', 'bca': 'DISCONFIRMED', 'jackknife': 'DISCONFIRMED'})  |  full run: DISCONFIRMED\n  cell 19: P_boot(F_prompt <= 1/2) = 0.35  P_boot(F_direct >= 1/3) = 0.99   (full run: 0.28 / 0.99)\n  cell 19: mixed GLM sensitivity: F_prompt 0.57, F_direct 0.77  (full run: 0.74, 0.89)\n  cell 23: landing analysis: 0.8s (LANDING_N_REP=2000)\n  cell 25: C2c: 2.2s (N_PERM=100000, N_BOOT_RHO=4000)\n  cell 25: hit fraction 0.80, Spearman rho -0.34 (one-sided permutation p 0.30, task-bootstrap 95% [-1.0, 0.67]) -> C2c INCONCLUSIVE\n  cell 25: full run: hit fraction 0.80, rho -0.34, p 0.30 -> INCONCLUSIVE\n--- cell 33 STDERR: 'The tied weights mapping and config for this model specifies to tie model.embed_tokens.weight to lm_head.weight, but both are present in the checkpoints, so we will NOT tie them. You should update the config with `tie_word_embeddings=False` to silence this warning\\n'\n  cell 33: 10:48:33|INFO   |HF model Qwen/Qwen3-0.6B loaded in 3s; attn=ko_sdpa; device=cpu; dtype=torch.float32\n  cell 33: 10:48:58|INFO   |[demo] T06 L=142 arms=['a', 'b', 'c', 'd'] rows=12 steps=61 22.6s\n  cell 33: 10:49:14|INFO   |[demo] T06 L=129 arms=['K0'] rows=3 steps=61 15.8s\n  cell 33: engine: 40.8s for 15 rows (ENGINE_MAX_NEW=160, ENGINE_N_SLOTS=3, device=cpu)\n  cell 39: C2a verdict (percentile / BCa / jackknife)            DISCONFIRMED / DISCONFIRMED / DISCONFIRMED  DISCONFIRMED / DISCONFIRMED / DISCONFIRMED\n  cell 39: P_boot(F_prompt <= 1/2), P_boot(F_direct >= 1/3)                                      0.35, 0.99                                  0.28, 0.99\n  cell 39: mixed GLM F_prompt, F_direct                                                          0.57, 0.77                                  0.74, 0.89\n  cell 39: C2c: hit fraction, Spearman rho (perm p) -> decision        0.80, -0.34 (p 0.30) -> INCONCLUSIVE        0.80, -0.34 (p 0.30) -> INCONCLUSIVE\nerrors: 0 | execution counts: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]\n\n=== final summary cell ===\n                                                                                     demo subset                                    full run\nquantity                                                                                                                                    \ngated tasks (frozen gate)                                                T03, T06, T05, T10, T13                     T03, T06, T05, T10, T13\npooled F_prompt [jackknife 95%, primary]                                     0.578 [-0.00, 1.16]                          0.611 [0.06, 1.17]\npooled F_direct [jackknife 95%, primary]                                      0.719 [0.34, 1.10]                          0.744 [0.38, 1.11]\npooled I [jackknife 95%, primary]                                           -0.297 [-0.99, 0.40]                        -0.355 [-0.98, 0.27]\npooled F_K0 [jackknife 95%, primary]                                          0.609 [0.06, 1.16]                          0.621 [0.08, 1.16]\nC2a verdict (percentile / BCa / jackknife)            DISCONFIRMED / DISCONFIRMED / DISCONFIRMED  DISCONFIRMED / DISCONFIRMED / DISCONFIRMED\nP_boot(F_prompt <= 1/2), P_boot(F_direct >= 1/3)                                      0.35, 0.99                                  0.28, 0.99\nmixed GLM F_prompt, F_direct                                                          0.57, 0.77                                  0.74, 0.89\nC2c: hit fraction, Spearman rho (perm p) -> decision        0.80, -0.34 (p 0.30) -> INCONCLUSIVE        0.80, -0.34 (p 0.30) -> INCONCLUSIVE\nT03 F_prompt / F_direct                                                              1.00 / 0.79                                 1.00 / 0.74\nT06 F_prompt / F_direct                                                              0.00 / 0.92                                 0.04 / 0.99\nT05 F_prompt / F_direct                                                              0.31 / 0.92                                 0.41 / 0.96\nT10 F_prompt / F_direct                                                              1.00 / 0.80                                 1.00 / 0.80\nT13 F_prompt / F_direct                                                              0.40 / 0.00                                 0.39 / 0.02\n\n-rw-rw-rw- 1 aii-agent aii-agent 411777 Oct 26 10:49 code_demo.ipynb", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [289] THINKING · 2026-10-26 10:49:39 UTC

```
All 25 cells ran cleanly and the demo matches the full run on every verdict, with only a harmless transformers tied-weights notice to silence. Now I'll extract the final figures to check them.
```

### [290] TOOL CALL — Bash · 2026-10-26 10:49:39 UTC

```
Extract final figures for visual check:
mkdir -p _tmp_figs && python3 -I - <<'EOF'
import json, base64
nb = json.load(open("code_demo.ipynb"))
n = 0
for i, c in enumerate(nb["cells"]):
    for o in c.get("outputs", []):
        if o["output_type"] == "display_data" and "image/png" in o["data"]:
            n += 1
            open(f"_tmp_figs/fig{n}.png", "wb").write(base64.b64decode(o["data"]["image/png"]))
print(n)
EOF
```

### [291] TOOL RESULT — Bash · 2026-10-26 10:49:39 UTC

```
{"stdout": "2", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [292] TOOL CALL — Read · 2026-10-26 10:49:43 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/_tmp_figs/fig1.png
```

### [293] TOOL RESULT — Read · 2026-10-26 10:49:43 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [294] TOOL CALL — Read · 2026-10-26 10:49:43 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/_tmp_figs/fig2.png
```

### [295] TOOL RESULT — Read · 2026-10-26 10:49:43 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [296] THINKING · 2026-10-26 10:50:03 UTC

```
Both figures now look correct, with arms leaving arm `b` at token 8 as expected per the study's definition. Next, I'll silence the tied-weights notice and check whether the install cell is noisy.
```

### [297] TOOL CALL — Bash · 2026-10-26 10:50:03 UTC

```
Remove temp figures, check install output, silence HF notice:
rm -rf _tmp_figs && python3 -I - <<'PYEOF'
import json
p = "code_demo.ipynb"
nb = json.load(open(p))
print("install cell outputs:", [("".join(o.get("text", "")) if isinstance(o.get("text"), list) else o.get("text", ""))[:300] for o in nb["cells"][1]["outputs"]])
cells = {c["id"]: c for c in nb["cells"]}
cid = "9d1dcc44"
src = "".join(cells[cid]["source"])
old = "    hf_logging.disable_progress_bar()  # notebook: no weight-loading progress bar\n"
new = ("    hf_logging.disable_progress_bar()  # notebook: no weight-loading progress bar\n"
       "    hf_logging.set_verbosity_error()   # notebook: hide the Qwen3-0.6B tied-embedding notice\n")
assert src.count(old) == 1
cells[cid]["source"] = src.replace(old, new).splitlines(keepends=True)
json.dump(nb, open(p, "w"), indent=1, ensure_ascii=False)
open(p, "a").write("\n")
print("edited")
PYEOF
```

### [298] TOOL RESULT — Bash · 2026-10-26 10:50:03 UTC

```
{"stdout": "install cell outputs: []\nedited", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [299] ASSISTANT · 2026-10-26 10:50:15 UTC

```
The install cell is already silent with `pip -q`, so no `%%capture` is needed. Running the final clean-venv execution so the saved outputs match the final source:
```

### [300] TOOL CALL — Bash · 2026-10-26 10:50:15 UTC

```
Final clean-venv execution and output verification:
UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art__5akZ9W9iZM4-bfb6955ec1d9 && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art__5akZ9W9iZM4-bfb6955ec1d9/bin/python jupyter ipykernel && T0=$(date +%s) && /tmp/aii_nb_test_envs/art__5akZ9W9iZM4-bfb6955ec1d9/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb > .nbtest.log 2>&1; echo "EXIT=$? RUNTIME=$(( $(date +%s) - T0 ))s"; tail -2 .nbtest.log; python3 -I - <<'EOF'
import json
nb = json.load(open("code_demo.ipynb"))
def txt(o):
    t = o.get("text", "")
    return "".join(t) if isinstance(t, list) else t
errs = [(i, o["ename"]) for i, c in enumerate(nb["cells"]) for o in c.get("outputs", []) if o["output_type"] == "error"]
stderr = [(i, txt(o)[:120]) for i, c in enumerate(nb["cells"]) for o in c.get("outputs", []) if o.get("name") == "stderr"]
imgs = sum(1 for c in nb["cells"] for o in c.get("outputs", []) if o["output_type"] == "display_data")
print("errors:", errs, "| stderr:", stderr, "| figures:", imgs)
print([l for c in nb["cells"] for o in c.get("outputs", []) if o["output_type"] == "stream" for l in txt(o).splitlines() if l.startswith("engine:") or "[demo]" in l])
EOF
```

### [301] TOOL RESULT — Bash · 2026-10-26 10:51:37 UTC

```
{"stdout": "EXIT=0 RUNTIME=83s\n[IPKernelApp] WARNING | Kernel is running over TCP without encryption. All communication (including code and outputs) is sent in plain text and is susceptible to eavesdropping. Use IPC transport or launch with kernel manager-provisioned CurveZMQ keys to enable transport encryption.\n[NbConvertApp] Writing 411508 bytes to code_demo.ipynb\nerrors: [] | stderr: [] | figures: 2\n[\"10:51:18|INFO   |[demo] T06 L=142 arms=['a', 'b', 'c', 'd'] rows=12 steps=61 23.1s\", \"10:51:34|INFO   |[demo] T06 L=129 arms=['K0'] rows=3 steps=61 15.9s\", 'engine: 41.4s for 15 rows (ENGINE_MAX_NEW=160, ENGINE_N_SLOTS=3, device=cpu)']", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [302] ASSISTANT · 2026-10-26 10:51:51 UTC

```
Final execution: **exit 0, 83 s, no errors, no stderr, both figures rendered.** Now TODO 6, the verification, plus an nbformat schema validation of the notebook:
```

### [303] TOOL CALL — Bash · 2026-10-26 10:51:51 UTC

```
Verify URL, data file, loading pattern and notebook validity:
rm -f .nbtest.log && URL='GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-3/experiment-16/demo/mini_demo_data.json"' && /tmp/aii_nb_test_envs/art__5akZ9W9iZM4-bfb6955ec1d9/bin/python -I - "$URL" <<'EOF'
import json, sys
import nbformat
url_line = sys.argv[1]
nb = nbformat.read("code_demo.ipynb", as_version=4)
nbformat.validate(nb)
src = "\n".join(c.source for c in nb.cells if c.cell_type == "code")
print("(1) exact GITHUB_DATA_URL line present:", url_line in src)
import os
print("(2) mini_demo_data.json exists:", os.path.exists("mini_demo_data.json"), os.path.getsize("mini_demo_data.json"), "bytes;",
      "valid JSON with", len(json.load(open("mini_demo_data.json"))["datasets"][0]["examples"]), "examples")
print("(3) GitHub URL pattern used: urlopen(GITHUB_DATA_URL) ->", "urllib.request.urlopen(GITHUB_DATA_URL" in src,
      "| local fallback ->", 'Path("mini_demo_data.json")' in src, "| data = load_data() ->", "data = load_data()" in src,
      "| bare open('mini_demo_data.json') ->", "open('mini_demo_data.json')" in src or 'open("mini_demo_data.json")' in src)
print("nbformat validation: OK;", len(nb.cells), "cells,", sum(c.cell_type == "code" for c in nb.cells), "code")
EOF
ls -la; ls -la .aii scripts
```

### [304] TOOL RESULT — Bash · 2026-10-26 10:51:51 UTC

```
{"stdout": "(1) exact GITHUB_DATA_URL line present: True\n(2) mini_demo_data.json exists: True 747988 bytes; valid JSON with 100 examples\n(3) GitHub URL pattern used: urlopen(GITHUB_DATA_URL) -> True | local fallback -> True | data = load_data() -> True | bare open('mini_demo_data.json') -> False\nnbformat validation: OK; 40 cells, 25 code\ntotal 7931\ndrwxrwxrwx 4 aii-agent aii-agent 2000293 Oct 26 10:51 .\ndrwxrwxrwx 9 aii-agent aii-agent 2001654 Oct 26 10:38 ..\ndrwxrwxrwx 2 aii-agent aii-agent   52100 Oct 26 10:43 .aii\n-rw-rw-rw- 1 aii-agent aii-agent      54 Oct 26 10:17 .aii_claude_session.json\n-rw-rw-rw- 1 aii-agent aii-agent 1897929 Oct 26 10:51 .repl_agent.ptylog\n-rw-rw-rw- 1 aii-agent aii-agent     113 Oct 26 10:46 .terminal_claude_agent_struct_out.json\n-rw-rw-rw- 1 aii-agent aii-agent    6409 Oct 26 10:46 README.md\n-rw-rw-rw- 1 aii-agent aii-agent  411516 Oct 26 10:51 code_demo.ipynb\n-rw-rw-rw- 1 aii-agent aii-agent  747988 Oct 26 10:28 mini_demo_data.json\ndrwxrwxrwx 2 aii-agent aii-agent 1000774 Oct 26 10:28 scripts\n.aii:\ntotal 2006\ndrwxrwxrwx 2 aii-agent aii-agent   52100 Oct 26 10:43 .\ndrwxrwxrwx 4 aii-agent aii-agent 2000293 Oct 26 10:51 ..\n-rw-rw-rw- 1 aii-agent aii-agent     521 Oct 26 10:43 manifest.yaml\n\nscripts:\ntotal 2939\ndrwxrwxrwx 2 aii-agent aii-agent 1000774 Oct 26 10:28 .\ndrwxrwxrwx 4 aii-agent aii-agent 2000293 Oct 26 10:51 ..\n-rw-rw-rw- 1 aii-agent aii-agent    7934 Oct 26 10:28 build_mini_demo_data.py", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [305] ASSISTANT · 2026-10-26 10:52:05 UTC

```
All three TODO-6 checks pass, and the notebook validates against the nbformat schema. Last step: put the final run's numbers and runtime into the README.
```

### [306] TOOL CALL — Edit · 2026-10-26 10:52:05 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/README.md
OLD: ## Results of the executed notebook

The demo has 15 slots per gated task; the full run has 100. Point estimates and the leave-one-task-out jackknife
intervals are deterministic.

| quantity | demo subset | full run |
|---|---|---|
| gated tasks | T03, T06, T05, T10, T13 (frozen gate) | same |
| pooled F_prompt [jackknife 95%] | 0.578 [-0.00, 1.16] | 0.611 [0.06, 1.17] |
| pooled F_direct [jackknife 95%] | 0.719 [0.34, 1.10] | 0.744 [0.38, 1.11] |
| pooled I | -0.297 | -0.355 |
| pooled F_K0 | 0.609 | 0.621 |
| C2a ("prompt route carries >= 2/3") | DISCONFIRMED under all three intervals | DISCONFIRMED |
| C2c (veto sufficiency predicts F_direct) | hit fraction 0.80, rho -0.34 -> INCONCLUSIVE | 0.80, -0.34 -> INCONCLUSIVE |
NEW: ## Results of the executed notebook

The demo has 15 slots per gated task; the full run has 100. Resampling counts are at the original values.

| quantity | demo subset | full run |
|---|---|---|
| gated tasks | T03, T06, T05, T10, T13 (frozen gate) | same |
| pooled F_prompt [jackknife 95%, primary] | 0.578 [-0.00, 1.16] | 0.611 [0.06, 1.17] |
| pooled F_direct [jackknife 95%, primary] | 0.719 [0.34, 1.10] | 0.744 [0.38, 1.11] |
| pooled I | -0.297 | -0.355 |
| pooled F_K0 | 0.609 | 0.621 |
| P_boot(F_prompt <= 1/2), P_boot(F_direct >= 1/3) | 0.35, 0.99 | 0.28, 0.99 |
| C2a ("prompt route carries >= 2/3") | DISCONFIRMED under percentile, BCa and jackknife | DISCONFIRMED under all three |
| C2c (veto sufficiency predicts F_direct) | hit fraction 0.80, rho -0.34, perm p 0.30 -> INCONCLUSIVE | 0.80, -0.34, p 0.30 -> INCONCLUSIVE |
```

### [307] TOOL RESULT — Edit · 2026-10-26 10:52:05 UTC

````
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/README.md", "oldString": "## Results of the executed notebook\n\nThe demo has 15 slots per gated task; the full run has 100. Point estimates and the leave-one-task-out jackknife\nintervals are deterministic.\n\n| quantity | demo subset | full run |\n|---|---|---|\n| gated tasks | T03, T06, T05, T10, T13 (frozen gate) | same |\n| pooled F_prompt [jackknife 95%] | 0.578 [-0.00, 1.16] | 0.611 [0.06, 1.17] |\n| pooled F_direct [jackknife 95%] | 0.719 [0.34, 1.10] | 0.744 [0.38, 1.11] |\n| pooled I | -0.297 | -0.355 |\n| pooled F_K0 | 0.609 | 0.621 |\n| C2a (\"prompt route carries >= 2/3\") | DISCONFIRMED under all three intervals | DISCONFIRMED |\n| C2c (veto sufficiency predicts F_direct) | hit fraction 0.80, rho -0.34 -> INCONCLUSIVE | 0.80, -0.34 -> INCONCLUSIVE |", "newString": "## Results of the executed notebook\n\nThe demo has 15 slots per gated task; the full run has 100. Resampling counts are at the original values.\n\n| quantity | demo subset | full run |\n|---|---|---|\n| gated tasks | T03, T06, T05, T10, T13 (frozen gate) | same |\n| pooled F_prompt [jackknife 95%, primary] | 0.578 [-0.00, 1.16] | 0.611 [0.06, 1.17] |\n| pooled F_direct [jackknife 95%, primary] | 0.719 [0.34, 1.10] | 0.744 [0.38, 1.11] |\n| pooled I | -0.297 | -0.355 |\n| pooled F_K0 | 0.609 | 0.621 |\n| P_boot(F_prompt <= 1/2), P_boot(F_direct >= 1/3) | 0.35, 0.99 | 0.28, 0.99 |\n| C2a (\"prompt route carries >= 2/3\") | DISCONFIRMED under percentile, BCa and jackknife | DISCONFIRMED under all three |\n| C2c (veto sufficiency predicts F_direct) | hit fraction 0.80, rho -0.34, perm p 0.30 -> INCONCLUSIVE | 0.80, -0.34, p 0.30 -> INCONCLUSIVE |", "originalFile": "# Demo: where a coding ban takes effect in Qwen3-8B (experiment-16)\n\nA runnable, Colab-ready walkthrough of the experiment **\"Where a coding ban takes effect in Qwen3-8B\"**\n(`art__5akZ9W9iZM4`, part of *Prompt bans substitute, not just subtract*).\n\nThe experiment asks which internal route carries a prompt ban such as *\"Do not use a hash set of seen values for this\ntask.\"* into Qwen3-8B's code. It samples every arm of a slot with common random numbers (CRN) and builds the arms by\nsplicing KV caches:\n\n| arm | cache read by the generated tokens |\n|---|---|\n| `a` | full ban prompt |\n| `b` | token-length-matched neutral twin |\n| `c` | twin condition + ban task-spec states (prompt route) |\n| `d` | ban condition + twin task-spec states (direct route) |\n| `K0` | the ban with its condition span knocked out |\n\nEach arm writes programs, and frozen labellers name the mechanism of each program.\n\n## What the notebook does\n\n`code_demo.ipynb` converts the experiment's `method.py` pipeline into notebook cells. The original code is kept\nverbatim except for file paths and resampling counts.\n\n1. **S9 analysis** (`src/analysis/analysis.py`, `gpu.compute_gate`) on a curated subset of the labelled route arms:\n   100 CRN slots, i.e. 500 programs written by Qwen3-8B. It covers:\n   - the gate;\n   - per-arm default shares;\n   - route fractions `F_prompt`, `F_direct`, `I`, `F_K0`, with the hierarchical task → template → slot bootstrap,\n     leave-one-task-out jackknife (primary), BCa, leave-one-template-out and the Bayesian mixed GLM;\n   - the C2a verdict;\n   - CRN flip tables with exact McNemar tests;\n   - identical-output rates and first divergence;\n   - landing by route;\n   - C2c.\n2. **The HF engine** (`src/engine.py` + `gpu.Worker.arm_state`): prefill, KV splice, span drop and CRN inverse-CDF\n   sampling.\n   - It runs on one CRN slot set (T06 / W1) on CPU with **Qwen/Qwen3-0.6B**, a mechanics stand-in. It shares Qwen3-8B's\n     tokenizer, so the frozen prompt ids and the run's exact uniform streams apply unchanged.\n   - The Qwen3-8B rows of the same slots are shown beside the live output.\n3. **Figures and a summary table** comparing the subset with the full run.\n\nThe demo does not re-run the Qwen3-8B GPU queue (about 1.8 L4 GPU-hours), the frozen labellers (bench harness + LLM\njudge), or the stages that need the upstream bench folders.\n\n## Results of the executed notebook\n\nThe demo has 15 slots per gated task; the full run has 100. Point estimates and the leave-one-task-out jackknife\nintervals are deterministic.\n\n| quantity | demo subset | full run |\n|---|---|---|\n| gated tasks | T03, T06, T05, T10, T13 (frozen gate) | same |\n| pooled F_prompt [jackknife 95%] | 0.578 [-0.00, 1.16] | 0.611 [0.06, 1.17] |\n| pooled F_direct [jackknife 95%] | 0.719 [0.34, 1.10] | 0.744 [0.38, 1.11] |\n| pooled I | -0.297 | -0.355 |\n| pooled F_K0 | 0.609 | 0.621 |\n| C2a (\"prompt route carries >= 2/3\") | DISCONFIRMED under all three intervals | DISCONFIRMED |\n| C2c (veto sufficiency predicts F_direct) | hit fraction 0.80, rho -0.34 -> INCONCLUSIVE | 0.80, -0.34 -> INCONCLUSIVE |\n| per task F_prompt / F_direct | T03 1.00/0.79, T06 0.00/0.92, T05 0.31/0.92, T10 1.00/0.80, T13 0.40/0.00 | T03 1.00/0.74, T06 0.04/0.99, T05 0.41/0.96, T10 1.00/0.80, T13 0.39/0.02 |\n\nThe 100-slot subset reproduces the experiment's conclusions. The route mechanism is task-dependent:\n- **T03/T10:** redundant, since either route alone suffices.\n- **T05/T06:** the direct route carries the ban.\n- **T13:** superadditive, since both routes are needed.\n\nSo the pre-registered \"prompt route carries >= 2/3 of the ban\" claim is disconfirmed.\n\n## Layout\n\n| path | what it is |\n|---|---|\n| `code_demo.ipynb` | the demo notebook, executed, with outputs |\n| `mini_demo_data.json` | demo data (~750 kB). One dataset, `route_arms`: 100 CRN-slot examples, each with its five arms' labels and token ids. `metadata` holds the frozen inputs the notebook reads instead of files: gate, commit-#2 veto classes, n-grams, mechanism catalogues, full-run reference numbers, and the prompt ids + Qwen3-8B rows of the engine slots |\n| `scripts/build_mini_demo_data.py` | rebuilds `mini_demo_data.json` from the experiment-16 folder, with the selection rule in its docstring |\n| `.aii/manifest.yaml` | storage decisions; nothing in this folder is heavy |\n\n## How to run\n\n**Colab.** Open `code_demo.ipynb` and run all cells.\n- The install cell adds only `loguru` there.\n- The notebook fetches `mini_demo_data.json` from this repository's raw GitHub URL and falls back to a local copy.\n- It downloads Qwen/Qwen3-0.6B (about 1.5 GB) from the Hugging Face Hub.\n\n**Locally** (Python 3.12):\n\n```bash\nuv venv .venv --python 3.12 --seed\nuv pip install --python .venv/bin/python jupyter ipykernel\n.venv/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb\n```\n\nOff Colab, the install cell pins Colab's versions:\n- torch 2.9.0+cpu from the PyTorch CPU index;\n- transformers 5.0.0, numpy 2.0.2, pandas 2.2.2, scipy 1.16.3, statsmodels 0.14.6 and matplotlib 3.10.0.\n\n**Knobs** are in the config cell, each commented with its original value. The resampling counts already equal the\nexperiment's (`N_BOOT` 10000, `N_PERM` 100000, ...).\n- `RUN_ENGINE = False` skips the model.\n- `ENGINE_MODEL_ID = \"Qwen/Qwen3-8B\"` runs the original model, with its revision, `ENGINE_DTYPE = torch.bfloat16` and\n  a GPU with more than 17 GB.\n\n**Rebuild the demo data** from the experiment folder (`<experiment-16>` is the folder holding `full_method_out.json`,\n`data/`, `prompts/`, `predictions/` and `inputs/bench/`):\n\n```bash\npython scripts/build_mini_demo_data.py <experiment-16> mini_demo_data.json\n```\n\n## Restoring removed files\n\nNothing in this folder is marked `delete` in `.aii/manifest.yaml`. Every file here is a small text or code file and\nis kept. The notebook needs two things from outside this folder, and both are fetched on demand:\n\n| what | where it lives | how to get it |\n|---|---|---|\n| Qwen/Qwen3-0.6B weights at revision `c1899de289a04d12100db370d81485cdf75e47ca` (~1.5 GB) | Hugging Face cache (`$HF_HOME`), not this folder | downloaded automatically by the engine cell, or `huggingface-cli download Qwen/Qwen3-0.6B --revision c1899de289a04d12100db370d81485cdf75e47ca` |\n| Python packages | the notebook's environment | installed by the notebook's first cell (see \"How to run\") |\n", "structuredPatch": [{"oldStart": 45, "oldLines": 18, "newStart": 45, "newLines": 18, "lines": [" ", " ## Results of the executed notebook", " ", "-The demo has 15 slots per gated task; the full run has 100. Point estimates and the leave-one-task-out jackknife", "-intervals are deterministic.", "+The demo has 15 slots per gated task; the full run has 100. Resampling counts are at the original values.", " ", " | quantity | demo subset | full run |", " |---|---|---|", " | gated tasks | T03, T06, T05, T10, T13 (frozen gate) | same |", "-| pooled F_prompt [jackknife 95%] | 0.578 [-0.00, 1.16] | 0.611 [0.06, 1.17] |", "-| pooled F_direct [jackknife 95%] | 0.719 [0.34, 1.10] | 0.744 [0.38, 1.11] |", "+| pooled F_prompt [jackknife 95%, primary] | 0.578 [-0.00, 1.16] | 0.611 [0.06, 1.17] |", "+| pooled F_direct [jackknife 95%, primary] | 0.719 [0.34, 1.10] | 0.744 [0.38, 1.11] |", " | pooled I | -0.297 | -0.355 |", " | pooled F_K0 | 0.609 | 0.621 |", "-| C2a (\"prompt route carries >= 2/3\") | DISCONFIRMED under all three intervals | DISCONFIRMED |", "-| C2c (veto sufficiency predicts F_direct) | hit fraction 0.80, rho -0.34 -> INCONCLUSIVE | 0.80, -0.34 -> INCONCLUSIVE |", "+| P_boot(F_prompt <= 1/2), P_boot(F_direct >= 1/3) | 0.35, 0.99 | 0.28, 0.99 |", "+| C2a (\"prompt route carries >= 2/3\") | DISCONFIRMED under percentile, BCa and jackknife | DISCONFIRMED under all three |", "+| C2c (veto sufficiency predicts F_direct) | hit fraction 0.80, rho -0.34, perm p 0.30 -> INCONCLUSIVE | 0.80, -0.34, p 0.30 -> INCONCLUSIVE |", " | per task F_prompt / F_direct | T03 1.00/0.79, T06 0.00/0.92, T05 0.31/0.92, T10 1.00/0.80, T13 0.40/0.00 | T03 1.00/0.74, T06 0.04/0.99, T05 0.41/0.96, T10 1.00/0.80, T13 0.39/0.02 |", " ", " The 100-slot subset reproduces the experiment's conclusions. The route mechanism is task-dependent:"]}], "userModified": false, "replaceAll": false}
````

### [308] TOOL CALL — Edit · 2026-10-26 10:52:05 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/README.md
OLD: So the pre-registered "prompt route carries >= 2/3 of the ban" claim is disconfirmed.
NEW: So the pre-registered "prompt route carries >= 2/3 of the ban" claim is disconfirmed.

In the engine section, Qwen3-0.6B does not follow the T06 ban (it still writes hash-set code), but the CRN mechanics
match the full run. Every arm keeps arm `b`'s tokens up to the first body token (token 8) and diverges there. At slot
k = 1, arm `d` reproduces arm `a` token for token, as it does in the Qwen3-8B rows.

**Runtime.** The notebook ran end to end in 83 s, installs included, in a fresh Python 3.12 venv on 2 CPU cores (no
GPU):
- the analysis cells took about 4 s at the original resampling counts;
- the 15 live engine rows took 41 s.
```

### [309] TOOL RESULT — Edit · 2026-10-26 10:52:05 UTC

````
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/README.md", "oldString": "So the pre-registered \"prompt route carries >= 2/3 of the ban\" claim is disconfirmed.", "newString": "So the pre-registered \"prompt route carries >= 2/3 of the ban\" claim is disconfirmed.\n\nIn the engine section, Qwen3-0.6B does not follow the T06 ban (it still writes hash-set code), but the CRN mechanics\nmatch the full run. Every arm keeps arm `b`'s tokens up to the first body token (token 8) and diverges there. At slot\nk = 1, arm `d` reproduces arm `a` token for token, as it does in the Qwen3-8B rows.\n\n**Runtime.** The notebook ran end to end in 83 s, installs included, in a fresh Python 3.12 venv on 2 CPU cores (no\nGPU):\n- the analysis cells took about 4 s at the original resampling counts;\n- the 15 live engine rows took 41 s.", "originalFile": "# Demo: where a coding ban takes effect in Qwen3-8B (experiment-16)\n\nA runnable, Colab-ready walkthrough of the experiment **\"Where a coding ban takes effect in Qwen3-8B\"**\n(`art__5akZ9W9iZM4`, part of *Prompt bans substitute, not just subtract*).\n\nThe experiment asks which internal route carries a prompt ban such as *\"Do not use a hash set of seen values for this\ntask.\"* into Qwen3-8B's code. It samples every arm of a slot with common random numbers (CRN) and builds the arms by\nsplicing KV caches:\n\n| arm | cache read by the generated tokens |\n|---|---|\n| `a` | full ban prompt |\n| `b` | token-length-matched neutral twin |\n| `c` | twin condition + ban task-spec states (prompt route) |\n| `d` | ban condition + twin task-spec states (direct route) |\n| `K0` | the ban with its condition span knocked out |\n\nEach arm writes programs, and frozen labellers name the mechanism of each program.\n\n## What the notebook does\n\n`code_demo.ipynb` converts the experiment's `method.py` pipeline into notebook cells. The original code is kept\nverbatim except for file paths and resampling counts.\n\n1. **S9 analysis** (`src/analysis/analysis.py`, `gpu.compute_gate`) on a curated subset of the labelled route arms:\n   100 CRN slots, i.e. 500 programs written by Qwen3-8B. It covers:\n   - the gate;\n   - per-arm default shares;\n   - route fractions `F_prompt`, `F_direct`, `I`, `F_K0`, with the hierarchical task → template → slot bootstrap,\n     leave-one-task-out jackknife (primary), BCa, leave-one-template-out and the Bayesian mixed GLM;\n   - the C2a verdict;\n   - CRN flip tables with exact McNemar tests;\n   - identical-output rates and first divergence;\n   - landing by route;\n   - C2c.\n2. **The HF engine** (`src/engine.py` + `gpu.Worker.arm_state`): prefill, KV splice, span drop and CRN inverse-CDF\n   sampling.\n   - It runs on one CRN slot set (T06 / W1) on CPU with **Qwen/Qwen3-0.6B**, a mechanics stand-in. It shares Qwen3-8B's\n     tokenizer, so the frozen prompt ids and the run's exact uniform streams apply unchanged.\n   - The Qwen3-8B rows of the same slots are shown beside the live output.\n3. **Figures and a summary table** comparing the subset with the full run.\n\nThe demo does not re-run the Qwen3-8B GPU queue (about 1.8 L4 GPU-hours), the frozen labellers (bench harness + LLM\njudge), or the stages that need the upstream bench folders.\n\n## Results of the executed notebook\n\nThe demo has 15 slots per gated task; the full run has 100. Resampling counts are at the original values.\n\n| quantity | demo subset | full run |\n|---|---|---|\n| gated tasks | T03, T06, T05, T10, T13 (frozen gate) | same |\n| pooled F_prompt [jackknife 95%, primary] | 0.578 [-0.00, 1.16] | 0.611 [0.06, 1.17] |\n| pooled F_direct [jackknife 95%, primary] | 0.719 [0.34, 1.10] | 0.744 [0.38, 1.11] |\n| pooled I | -0.297 | -0.355 |\n| pooled F_K0 | 0.609 | 0.621 |\n| P_boot(F_prompt <= 1/2), P_boot(F_direct >= 1/3) | 0.35, 0.99 | 0.28, 0.99 |\n| C2a (\"prompt route carries >= 2/3\") | DISCONFIRMED under percentile, BCa and jackknife | DISCONFIRMED under all three |\n| C2c (veto sufficiency predicts F_direct) | hit fraction 0.80, rho -0.34, perm p 0.30 -> INCONCLUSIVE | 0.80, -0.34, p 0.30 -> INCONCLUSIVE |\n| per task F_prompt / F_direct | T03 1.00/0.79, T06 0.00/0.92, T05 0.31/0.92, T10 1.00/0.80, T13 0.40/0.00 | T03 1.00/0.74, T06 0.04/0.99, T05 0.41/0.96, T10 1.00/0.80, T13 0.39/0.02 |\n\nThe 100-slot subset reproduces the experiment's conclusions. The route mechanism is task-dependent:\n- **T03/T10:** redundant, since either route alone suffices.\n- **T05/T06:** the direct route carries the ban.\n- **T13:** superadditive, since both routes are needed.\n\nSo the pre-registered \"prompt route carries >= 2/3 of the ban\" claim is disconfirmed.\n\n## Layout\n\n| path | what it is |\n|---|---|\n| `code_demo.ipynb` | the demo notebook, executed, with outputs |\n| `mini_demo_data.json` | demo data (~750 kB). One dataset, `route_arms`: 100 CRN-slot examples, each with its five arms' labels and token ids. `metadata` holds the frozen inputs the notebook reads instead of files: gate, commit-#2 veto classes, n-grams, mechanism catalogues, full-run reference numbers, and the prompt ids + Qwen3-8B rows of the engine slots |\n| `scripts/build_mini_demo_data.py` | rebuilds `mini_demo_data.json` from the experiment-16 folder, with the selection rule in its docstring |\n| `.aii/manifest.yaml` | storage decisions; nothing in this folder is heavy |\n\n## How to run\n\n**Colab.** Open `code_demo.ipynb` and run all cells.\n- The install cell adds only `loguru` there.\n- The notebook fetches `mini_demo_data.json` from this repository's raw GitHub URL and falls back to a local copy.\n- It downloads Qwen/Qwen3-0.6B (about 1.5 GB) from the Hugging Face Hub.\n\n**Locally** (Python 3.12):\n\n```bash\nuv venv .venv --python 3.12 --seed\nuv pip install --python .venv/bin/python jupyter ipykernel\n.venv/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb\n```\n\nOff Colab, the install cell pins Colab's versions:\n- torch 2.9.0+cpu from the PyTorch CPU index;\n- transformers 5.0.0, numpy 2.0.2, pandas 2.2.2, scipy 1.16.3, statsmodels 0.14.6 and matplotlib 3.10.0.\n\n**Knobs** are in the config cell, each commented with its original value. The resampling counts already equal the\nexperiment's (`N_BOOT` 10000, `N_PERM` 100000, ...).\n- `RUN_ENGINE = False` skips the model.\n- `ENGINE_MODEL_ID = \"Qwen/Qwen3-8B\"` runs the original model, with its revision, `ENGINE_DTYPE = torch.bfloat16` and\n  a GPU with more than 17 GB.\n\n**Rebuild the demo data** from the experiment folder (`<experiment-16>` is the folder holding `full_method_out.json`,\n`data/`, `prompts/`, `predictions/` and `inputs/bench/`):\n\n```bash\npython scripts/build_mini_demo_data.py <experiment-16> mini_demo_data.json\n```\n\n## Restoring removed files\n\nNothing in this folder is marked `delete` in `.aii/manifest.yaml`. Every file here is a small text or code file and\nis kept. The notebook needs two things from outside this folder, and both are fetched on demand:\n\n| what | where it lives | how to get it |\n|---|---|---|\n| Qwen/Qwen3-0.6B weights at revision `c1899de289a04d12100db370d81485cdf75e47ca` (~1.5 GB) | Hugging Face cache (`$HF_HOME`), not this folder | downloaded automatically by the engine cell, or `huggingface-cli download Qwen/Qwen3-0.6B --revision c1899de289a04d12100db370d81485cdf75e47ca` |\n| Python packages | the notebook's environment | installed by the notebook's first cell (see \"How to run\") |\n", "structuredPatch": [{"oldStart": 66, "oldLines": 6, "newStart": 66, "newLines": 15, "lines": [" ", " So the pre-registered \"prompt route carries >= 2/3 of the ban\" claim is disconfirmed.", " ", "+In the engine section, Qwen3-0.6B does not follow the T06 ban (it still writes hash-set code), but the CRN mechanics", "+match the full run. Every arm keeps arm `b`'s tokens up to the first body token (token 8) and diverges there. At slot", "+k = 1, arm `d` reproduces arm `a` token for token, as it does in the Qwen3-8B rows.", "+", "+**Runtime.** The notebook ran end to end in 83 s, installs included, in a fresh Python 3.12 venv on 2 CPU cores (no", "+GPU):", "+- the analysis cells took about 4 s at the original resampling counts;", "+- the 15 live engine rows took 41 s.", "+", " ## Layout", " ", " | path | what it is |"]}], "userModified": false, "replaceAll": false}
````

### [310] THINKING · 2026-10-26 10:52:17 UTC

```
I'll verify the two claims I just added to the README against the final saved outputs, since the batch size changed from round 1 and could affect CPU numerics.
```

### [311] TOOL CALL — Bash · 2026-10-26 10:52:17 UTC

```
Verify live-engine claims against final notebook outputs:
python3 -I - <<'EOF'
import json, re
nb = json.load(open("code_demo.ipynb"))
def txt(o):
    t = o.get("text", "")
    return "".join(t) if isinstance(t, list) else t
out = "".join(txt(o) for o in nb["cells"][35]["outputs"] if o["output_type"] == "stream")
k = None; arm = None; progs = {}
lines = out.splitlines()
for i, line in enumerate(lines):
    m = re.search(r"CRN slot \(T06, W1, k=(\d)\)", line)
    if m: k = int(m.group(1))
    m = re.match(r"--- arm (\w+)", line)
    if m: arm = m.group(1)
    m = re.search(r"^  (Qwen/Qwen3-0.6B|Qwen3-8B) .*?(\d+) tokens, (\w+), leaves arm b at token (\w+)", line)
    if m:
        model = "live" if "0.6B" in m.group(1) else "8B"
        body = []
        for l2 in lines[i+1:]:
            if not l2.startswith("      "): break
            body.append(l2)
        progs[(k, arm, model)] = "\n".join(body)
        print(f"k={k} arm={arm:3s} {model:4s} ntok={m.group(2):>3s} finish={m.group(3):6s} first_div_from_b={m.group(4)}")
for k in (0, 1, 2):
    for model in ("live", "8B"):
        print(f"k={k} {model}: d==a program text: {progs[(k,'d',model)] == progs[(k,'a',model)]}")
EOF
```

### [312] TOOL RESULT — Bash [ERROR] · 2026-10-26 10:52:17 UTC

```
Error: Exit code 1
k=0 arm=a   live ntok= 46 finish=fence  first_div_from_b=8
k=0 arm=b   live ntok= 34 finish=fence  first_div_from_b=None
k=0 arm=c   live ntok= 62 finish=fence  first_div_from_b=8
k=0 arm=d   live ntok= 20 finish=fence  first_div_from_b=8
k=0 arm=K0  live ntok= 62 finish=fence  first_div_from_b=8
k=1 arm=a   live ntok= 34 finish=fence  first_div_from_b=8
k=1 arm=b   live ntok= 35 finish=fence  first_div_from_b=None
k=1 arm=c   live ntok= 29 finish=fence  first_div_from_b=10
k=1 arm=d   live ntok= 34 finish=fence  first_div_from_b=8
k=1 arm=K0  live ntok= 23 finish=fence  first_div_from_b=10
k=2 arm=a   live ntok= 34 finish=fence  first_div_from_b=None
k=2 arm=b   live ntok= 34 finish=fence  first_div_from_b=None
k=2 arm=c   live ntok= 34 finish=fence  first_div_from_b=None
k=2 arm=d   live ntok= 34 finish=fence  first_div_from_b=None
k=2 arm=K0  live ntok= 34 finish=fence  first_div_from_b=None
k=0 live: d==a program text: False
Traceback (most recent call last):
  File "<stdin>", line 25, in <module>
KeyError: (0, 'd', '8B')
```

### [313] THINKING · 2026-10-26 10:52:31 UTC

```
The actual results don't match what I wrote: divergence points vary by k (token 8 for k=0, a mix of 8/10 for k=1, none for k=2), so the "every arm diverges at token 8" claim is incorrect. I'll verify the k=1 `d == a` case (my regex missed some differently-formatted 8B lines) and then fix the README.
```

### [314] TOOL CALL — Bash · 2026-10-26 10:52:31 UTC

```
Compare arm programs per slot for live and 8B rows:
python3 -I - <<'EOF'
import json, re
nb = json.load(open("code_demo.ipynb"))
def txt(o):
    t = o.get("text", "")
    return "".join(t) if isinstance(t, list) else t
lines = "".join(txt(o) for o in nb["cells"][35]["outputs"] if o["output_type"] == "stream").splitlines()
k = arm = None; progs = {}
for i, line in enumerate(lines):
    m = re.search(r"CRN slot \(T06, W1, k=(\d)\)", line)
    if m: k = int(m.group(1))
    m = re.match(r"--- arm (\w+)", line)
    if m: arm = m.group(1)
    if line.startswith("  Qwen/Qwen3-0.6B") or line.startswith("  Qwen3-8B"):
        model = "live" if "0.6B" in line else "8B"
        body = []
        for l2 in lines[i + 1:]:
            if not l2.startswith("      "): break
            body.append(l2)
        progs[(k, arm, model)] = "\n".join(body)
        if model == "8B":
            print(f"k={k} arm={arm:3s} 8B  : {line.strip()[:120]}")
for k in (0, 1, 2):
    for model in ("live", "8B"):
        print(f"k={k} {model:4s}: d==a {progs[(k, 'd', model)] == progs[(k, 'a', model)]} | c==b {progs[(k, 'c', model)] == progs[(k, 'b', model)]} | K0==b {progs[(k, 'K0', model)] == progs[(k, 'b', model)]}")
EOF
```

### [315] TOOL RESULT — Bash · 2026-10-26 10:52:31 UTC

```
{"stdout": "k=0 arm=a   8B  : Qwen3-8B (full run): label = index_marking (passed tests: True), 49 tokens, leaves arm b at token 8\nk=0 arm=b   8B  : Qwen3-8B (full run): label = hash_set (passed tests: True), 34 tokens, leaves arm b at token None\nk=0 arm=c   8B  : Qwen3-8B (full run): label = hash_set (passed tests: True), 34 tokens, leaves arm b at token None\nk=0 arm=d   8B  : Qwen3-8B (full run): label = hash_set (passed tests: True), 33 tokens, leaves arm b at token 10\nk=0 arm=K0  8B  : Qwen3-8B (full run): label = hash_set (passed tests: True), 34 tokens, leaves arm b at token None\nk=1 arm=a   8B  : Qwen3-8B (full run): label = index_marking (passed tests: True), 53 tokens, leaves arm b at token 8\nk=1 arm=b   8B  : Qwen3-8B (full run): label = hash_set (passed tests: True), 39 tokens, leaves arm b at token None\nk=1 arm=c   8B  : Qwen3-8B (full run): label = hash_set (passed tests: True), 34 tokens, leaves arm b at token 33\nk=1 arm=d   8B  : Qwen3-8B (full run): label = index_marking (passed tests: True), 53 tokens, leaves arm b at token 8\nk=1 arm=K0  8B  : Qwen3-8B (full run): label = hash_set (passed tests: True), 34 tokens, leaves arm b at token 33\nk=2 arm=a   8B  : Qwen3-8B (full run): label = index_marking (passed tests: True), 53 tokens, leaves arm b at token 8\nk=2 arm=b   8B  : Qwen3-8B (full run): label = hash_set (passed tests: True), 34 tokens, leaves arm b at token None\nk=2 arm=c   8B  : Qwen3-8B (full run): label = hash_set (passed tests: True), 34 tokens, leaves arm b at token None\nk=2 arm=d   8B  : Qwen3-8B (full run): label = index_marking (passed tests: True), 49 tokens, leaves arm b at token 8\nk=2 arm=K0  8B  : Qwen3-8B (full run): label = hash_set (passed tests: True), 34 tokens, leaves arm b at token None\nk=0 live: d==a False | c==b False | K0==b False\nk=0 8B  : d==a False | c==b True | K0==b True\nk=1 live: d==a True | c==b False | K0==b False\nk=1 8B  : d==a True | c==b False | K0==b False\nk=2 live: d==a True | c==b True | K0==b True\nk=2 8B  : d==a False | c==b True | K0==b True", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [316] THINKING · 2026-10-26 10:52:41 UTC

```
Confirmed the live outputs match the notebook's 8B rows (k=1 `d==a` exactly, k=2 arms converge, divergence from `b` at tokens 8/10) and the section-5 note checks out. Now I'll fix the incorrect sentence in the README.
```

### [317] TOOL CALL — Edit · 2026-10-26 10:52:41 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/README.md
OLD: In the engine section, Qwen3-0.6B does not follow the T06 ban (it still writes hash-set code), but the CRN mechanics
match the full run. Every arm keeps arm `b`'s tokens up to the first body token (token 8) and diverges there. At slot
k = 1, arm `d` reproduces arm `a` token for token, as it does in the Qwen3-8B rows.
NEW: In the engine section, Qwen3-0.6B does not follow the T06 ban: it keeps writing hash-set or counting-dict code. The
CRN coupling still behaves as in the full run:
- Arms that leave arm `b` do so at the first body tokens, token 8 or 10, right after the `def` line.
- At slot k = 1, arm `d` reproduces arm `a` token for token, as in the Qwen3-8B rows.
- At k = 2, all five arms write the same program.
```

### [318] TOOL RESULT — Edit · 2026-10-26 10:52:41 UTC

````
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_3/art__5akZ9W9iZM4/README.md", "oldString": "In the engine section, Qwen3-0.6B does not follow the T06 ban (it still writes hash-set code), but the CRN mechanics\nmatch the full run. Every arm keeps arm `b`'s tokens up to the first body token (token 8) and diverges there. At slot\nk = 1, arm `d` reproduces arm `a` token for token, as it does in the Qwen3-8B rows.", "newString": "In the engine section, Qwen3-0.6B does not follow the T06 ban: it keeps writing hash-set or counting-dict code. The\nCRN coupling still behaves as in the full run:\n- Arms that leave arm `b` do so at the first body tokens, token 8 or 10, right after the `def` line.\n- At slot k = 1, arm `d` reproduces arm `a` token for token, as in the Qwen3-8B rows.\n- At k = 2, all five arms write the same program.", "originalFile": "# Demo: where a coding ban takes effect in Qwen3-8B (experiment-16)\n\nA runnable, Colab-ready walkthrough of the experiment **\"Where a coding ban takes effect in Qwen3-8B\"**\n(`art__5akZ9W9iZM4`, part of *Prompt bans substitute, not just subtract*).\n\nThe experiment asks which internal route carries a prompt ban such as *\"Do not use a hash set of seen values for this\ntask.\"* into Qwen3-8B's code. It samples every arm of a slot with common random numbers (CRN) and builds the arms by\nsplicing KV caches:\n\n| arm | cache read by the generated tokens |\n|---|---|\n| `a` | full ban prompt |\n| `b` | token-length-matched neutral twin |\n| `c` | twin condition + ban task-spec states (prompt route) |\n| `d` | ban condition + twin task-spec states (direct route) |\n| `K0` | the ban with its condition span knocked out |\n\nEach arm writes programs, and frozen labellers name the mechanism of each program.\n\n## What the notebook does\n\n`code_demo.ipynb` converts the experiment's `method.py` pipeline into notebook cells. The original code is kept\nverbatim except for file paths and resampling counts.\n\n1. **S9 analysis** (`src/analysis/analysis.py`, `gpu.compute_gate`) on a curated subset of the labelled route arms:\n   100 CRN slots, i.e. 500 programs written by Qwen3-8B. It covers:\n   - the gate;\n   - per-arm default shares;\n   - route fractions `F_prompt`, `F_direct`, `I`, `F_K0`, with the hierarchical task → template → slot bootstrap,\n     leave-one-task-out jackknife (primary), BCa, leave-one-template-out and the Bayesian mixed GLM;\n   - the C2a verdict;\n   - CRN flip tables with exact McNemar tests;\n   - identical-output rates and first divergence;\n   - landing by route;\n   - C2c.\n2. **The HF engine** (`src/engine.py` + `gpu.Worker.arm_state`): prefill, KV splice, span drop and CRN inverse-CDF\n   sampling.\n   - It runs on one CRN slot set (T06 / W1) on CPU with **Qwen/Qwen3-0.6B**, a mechanics stand-in. It shares Qwen3-8B's\n     tokenizer, so the frozen prompt ids and the run's exact uniform streams apply unchanged.\n   - The Qwen3-8B rows of the same slots are shown beside the live output.\n3. **Figures and a summary table** comparing the subset with the full run.\n\nThe demo does not re-run the Qwen3-8B GPU queue (about 1.8 L4 GPU-hours), the frozen labellers (bench harness + LLM\njudge), or the stages that need the upstream bench folders.\n\n## Results of the executed notebook\n\nThe demo has 15 slots per gated task; the full run has 100. Resampling counts are at the original values.\n\n| quantity | demo subset | full run |\n|---|---|---|\n| gated tasks | T03, T06, T05, T10, T13 (frozen gate) | same |\n| pooled F_prompt [jackknife 95%, primary] | 0.578 [-0.00, 1.16] | 0.611 [0.06, 1.17] |\n| pooled F_direct [jackknife 95%, primary] | 0.719 [0.34, 1.10] | 0.744 [0.38, 1.11] |\n| pooled I | -0.297 | -0.355 |\n| pooled F_K0 | 0.609 | 0.621 |\n| P_boot(F_prompt <= 1/2), P_boot(F_direct >= 1/3) | 0.35, 0.99 | 0.28, 0.99 |\n| C2a (\"prompt route carries >= 2/3\") | DISCONFIRMED under percentile, BCa and jackknife | DISCONFIRMED under all three |\n| C2c (veto sufficiency predicts F_direct) | hit fraction 0.80, rho -0.34, perm p 0.30 -> INCONCLUSIVE | 0.80, -0.34, p 0.30 -> INCONCLUSIVE |\n| per task F_prompt / F_direct | T03 1.00/0.79, T06 0.00/0.92, T05 0.31/0.92, T10 1.00/0.80, T13 0.40/0.00 | T03 1.00/0.74, T06 0.04/0.99, T05 0.41/0.96, T10 1.00/0.80, T13 0.39/0.02 |\n\nThe 100-slot subset reproduces the experiment's conclusions. The route mechanism is task-dependent:\n- **T03/T10:** redundant, since either route alone suffices.\n- **T05/T06:** the direct route carries the ban.\n- **T13:** superadditive, since both routes are needed.\n\nSo the pre-registered \"prompt route carries >= 2/3 of the ban\" claim is disconfirmed.\n\nIn the engine section, Qwen3-0.6B does not follow the T06 ban (it still writes hash-set code), but the CRN mechanics\nmatch the full run. Every arm keeps arm `b`'s tokens up to the first body token (token 8) and diverges there. At slot\nk = 1, arm `d` reproduces arm `a` token for token, as it does in the Qwen3-8B rows.\n\n**Runtime.** The notebook ran end to end in 83 s, installs included, in a fresh Python 3.12 venv on 2 CPU cores (no\nGPU):\n- the analysis cells took about 4 s at the original resampling counts;\n- the 15 live engine rows took 41 s.\n\n## Layout\n\n| path | what it is |\n|---|---|\n| `code_demo.ipynb` | the demo notebook, executed, with outputs |\n| `mini_demo_data.json` | demo data (~750 kB). One dataset, `route_arms`: 100 CRN-slot examples, each with its five arms' labels and token ids. `metadata` holds the frozen inputs the notebook reads instead of files: gate, commit-#2 veto classes, n-grams, mechanism catalogues, full-run reference numbers, and the prompt ids + Qwen3-8B rows of the engine slots |\n| `scripts/build_mini_demo_data.py` | rebuilds `mini_demo_data.json` from the experiment-16 folder, with the selection rule in its docstring |\n| `.aii/manifest.yaml` | storage decisions; nothing in this folder is heavy |\n\n## How to run\n\n**Colab.** Open `code_demo.ipynb` and run all cells.\n- The install cell adds only `loguru` there.\n- The notebook fetches `mini_demo_data.json` from this repository's raw GitHub URL and falls back to a local copy.\n- It downloads Qwen/Qwen3-0.6B (about 1.5 GB) from the Hugging Face Hub.\n\n**Locally** (Python 3.12):\n\n```bash\nuv venv .venv --python 3.12 --seed\nuv pip install --python .venv/bin/python jupyter ipykernel\n.venv/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb\n```\n\nOff Colab, the install cell pins Colab's versions:\n- torch 2.9.0+cpu from the PyTorch CPU index;\n- transformers 5.0.0, numpy 2.0.2, pandas 2.2.2, scipy 1.16.3, statsmodels 0.14.6 and matplotlib 3.10.0.\n\n**Knobs** are in the config cell, each commented with its original value. The resampling counts already equal the\nexperiment's (`N_BOOT` 10000, `N_PERM` 100000, ...).\n- `RUN_ENGINE = False` skips the model.\n- `ENGINE_MODEL_ID = \"Qwen/Qwen3-8B\"` runs the original model, with its revision, `ENGINE_DTYPE = torch.bfloat16` and\n  a GPU with more than 17 GB.\n\n**Rebuild the demo data** from the experiment folder (`<experiment-16>` is the folder holding `full_method_out.json`,\n`data/`, `prompts/`, `predictions/` and `inputs/bench/`):\n\n```bash\npython scripts/build_mini_demo_data.py <experiment-16> mini_demo_data.json\n```\n\n## Restoring removed files\n\nNothing in this folder is marked `delete` in `.aii/manifest.yaml`. Every file here is a small text or code file and\nis kept. The notebook needs two things from outside this folder, and both are fetched on demand:\n\n| what | where it lives | how to get it |\n|---|---|---|\n| Qwen/Qwen3-0.6B weights at revision `c1899de289a04d12100db370d81485cdf75e47ca` (~1.5 GB) | Hugging Face cache (`$HF_HOME`), not this folder | downloaded automatically by the engine cell, or `huggingface-cli download Qwen/Qwen3-0.6B --revision c1899de289a04d12100db370d81485cdf75e47ca` |\n| Python packages | the notebook's environment | installed by the notebook's first cell (see \"How to run\") |\n", "structuredPatch": [{"oldStart": 66, "oldLines": 9, "newStart": 66, "newLines": 11, "lines": [" ", " So the pre-registered \"prompt route carries >= 2/3 of the ban\" claim is disconfirmed.", " ", "-In the engine section, Qwen3-0.6B does not follow the T06 ban (it still writes hash-set code), but the CRN mechanics", "-match the full run. Every arm keeps arm `b`'s tokens up to the first body token (token 8) and diverges there. At slot", "-k = 1, arm `d` reproduces arm `a` token for token, as it does in the Qwen3-8B rows.", "+In the engine section, Qwen3-0.6B does not follow the T06 ban: it keeps writing hash-set or counting-dict code. The", "+CRN coupling still behaves as in the full run:", "+- Arms that leave arm `b` do so at the first body tokens, token 8 or 10, right after the `def` line.", "+- At slot k = 1, arm `d` reproduces arm `a` token for token, as in the Qwen3-8B rows.", "+- At k = 2, all five arms write the same program.", " ", " **Runtime.** The notebook ran end to end in 83 s, installs included, in a fresh Python 3.12 venv on 2 CPU cores (no", " GPU):"]}], "userModified": false, "replaceAll": false}
````

### [319] ASSISTANT · 2026-10-26 10:52:51 UTC

```
Last hygiene check: published files must not contain absolute server paths. I'll grep the deliverables and confirm the final file set.
```

### [320] TOOL CALL — Bash · 2026-10-26 10:52:51 UTC

```
Check deliverables for absolute paths and list final files:
for f in README.md code_demo.ipynb mini_demo_data.json scripts/build_mini_demo_data.py .aii/manifest.yaml .terminal_claude_agent_struct_out.json; do printf "%-45s %8s bytes  server-paths: %s\n" "$f" "$(stat -c %s "$f")" "$(grep -c -E '/ai-inventor|/var/lib|/tmp/' "$f")"; done; python3 -I -c "import json; print(json.load(open('.terminal_claude_agent_struct_out.json')))"; cat .aii/manifest.yaml | tail -2
```

### [321] TOOL RESULT — Bash · 2026-10-26 10:52:51 UTC

```
{"stdout": "README.md                                         7149 bytes  server-paths: 0\ncode_demo.ipynb                                 411516 bytes  server-paths: 1\nmini_demo_data.json                             747988 bytes  server-paths: 0\nscripts/build_mini_demo_data.py                   7934 bytes  server-paths: 0\n.aii/manifest.yaml                                 521 bytes  server-paths: 0\n.terminal_claude_agent_struct_out.json             113 bytes  server-paths: 0\n{'out_expected_files': {'notebook': 'code_demo.ipynb', 'mini_data_file': 'mini_demo_data.json'}}\n# --revision c1899de289a04d12100db370d81485cdf75e47ca`).\nentries: []", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [322] TOOL CALL — Bash · 2026-10-26 10:52:53 UTC

```
Show the context of the path match in the notebook:
grep -o -E '.{120}(/ai-inventor|/var/lib|/tmp/).{80}' code_demo.ipynb | head -3
```

### [323] TOOL RESULT — Bash · 2026-10-26 10:52:53 UTC

```
{"stdout": "", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [324] TOOL CALL — Bash · 2026-10-26 10:52:57 UTC

```
Locate the absolute path match in the notebook:
grep -n -o -E '.{0,100}(/ai-inventor|/var/lib|/tmp/).{0,60}' code_demo.ipynb | cut -c1-260
```

### [325] TOOL RESULT — Bash · 2026-10-26 10:52:57 UTC

```
{"stdout": "ugrep: error: error at position 106\nlib|/tmp/)(?:[^\\n\\x80-\\xbf][\\x80-\\xbf]*){0,60}\n                 exceeds complexity limits___/", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [326] TOOL CALL — Bash · 2026-10-26 10:53:01 UTC

```
Print context around the path match with Python:
python3 -I -c "
import re
s = open('code_demo.ipynb').read()
for m in re.finditer(r'/ai-inventor|/var/lib|/tmp/', s):
    print(repr(s[max(0, m.start()-150): m.end()+60]))
"
```

### [327] TOOL RESULT — Bash · 2026-10-26 10:53:01 UTC

```
{"stdout": "'.execute_reply\": \"2026-10-26T10:50:44.408467Z\"\\n    }\\n   },\\n   \"outputs\": [],\\n   \"source\": [\\n    \"GITHUB_DATA_URL = \\\\\"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-'", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [328] ASSISTANT · 2026-10-26 10:53:23 UTC

```
The demo notebook and its data are built and tested. `code_demo.ipynb` runs top to bottom in a fresh Python 3.12 environment in **83 seconds** (installs included, 2 CPU cores, no GPU), well under the 10-minute limit. On the 100-example subset it reaches the same verdicts as the full run.

**What the notebook covers:**
- **Analysis:** the experiment's statistical analysis code, copied unchanged except for reading from the loaded data. On 100 sampling slots (500 labelled Qwen3-8B programs) it computes:
  - which tasks the ban affects;
  - per-arm default shares;
  - the route fractions and their intervals;
  - the paired comparisons;
  - where each arm lands instead of the default;
  - the veto-prediction test (C2c).
- **Sampler:** the original cache-splicing sampler, run live on one task (find the duplicate, first ban wording, slots 0–2) with the run's exact random streams.
- **Results:** two figures and a demo-vs-full-run summary table.

| | demo subset | full run |
|---|---|---|
| tasks the ban affects | T03, T06, T05, T10, T13 | same |
| prompt-route share (F_prompt) | 0.578 [−0.00, 1.16] | 0.611 [0.06, 1.17] |
| direct-route share (F_direct) | 0.719 [0.34, 1.10] | 0.744 [0.38, 1.11] |
| "prompt route carries ≥ 2/3" | disconfirmed (all three intervals) | disconfirmed |
| veto test | ρ −0.34, p 0.30 → inconclusive | ρ −0.34, p 0.30 → inconclusive |

**Things that differ from the original:**
- **Live model:** the live sampler uses Qwen/Qwen3-0.6B on CPU instead of Qwen3-8B. It shares the 8B tokenizer, so the frozen prompts and random streams apply unchanged. But it is below the brief's 1B floor and ignores the ban: it keeps writing hash-set code. The 8B outputs for the same slots are shown beside it, and the sampling mechanics match. At slot 1 the direct-route arm reproduces the full-ban output token for token, as in the 8B run.
- **Scaling:** I went from minimum settings (44 s) to about 10× (77 s) to the original bootstrap and permutation counts (83 s). Two settings stay below the original:
  - The live sampler is capped at 160 new tokens instead of 1,024. One output that never finished could cost minutes on CPU, and these programs finish in under 80.
  - It uses 3 slots per wording instead of 20, because that is all the subset holds.
- **Coverage:** analyses that need data outside this one dataset are not reproduced: the prefill tests, the path screen, the controls and the log-prob readout.
- **Data URL:** the GitHub data link returns 404 until the files are pushed. The tests ran on the local fallback copy.
- **NotebookEdit:** I created the notebook with NotebookEdit. After the first run, the Read tool couldn't load the executed file, which NotebookEdit requires first. So the later fixes were exact text replacements in the notebook source.

There was no todo-tracking tool in this session, so I worked through the six TODOs in order. I treated the creativity research brief at the end of the paste as background for the wider study, not as part of this conversion.

Files are in the workspace:
- `code_demo.ipynb`
- `mini_demo_data.json`
- `scripts/build_mini_demo_data.py` — rebuilds the demo data
- `README.md`
- `.aii/manifest.yaml` — no heavy files to declare
- `.terminal_claude_agent_struct_out.json`
```
