# gen_demo_art_experiment_36 — report_results

> Phase: `gen_paper_repo` · `gen_demo_art`
> Run: `gen_paper_repo_c164ac661673` — A Random Activation Push Changes a Code Model's Algorithm Where Temperature Does Not
>
> Full, verbatim transcript of this agent task — every system/user prompt, assistant response, thinking block, tool call and tool result — in the order they occurred. Nothing truncated.

## Task: `gen_demo_art_experiment_36` (terminal_claude_agent, claude-opus-5-5)

### [1] CONFIG · 2026-10-26 12:59:58 UTC

```
model: Claude Opus 5.5 | effort: max | permission: bypassPermissions
```

### [2] SYSTEM-USER prompt · 2026-10-26 13:00:08 UTC

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
Your workspace: `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs`

CRITICAL: Every file you create, write, or save MUST be inside this workspace directory (subdirectories OK). You MUST NOT write files anywhere outside this path — external paths are READ-ONLY. Use absolute paths for all file operations.

EVERY file write MUST start with `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/`:
GOOD: `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/file.py`, `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/results/out.json`
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
id: art_8O5eaNc5gxJs
type: experiment
title: Why random nudges stopped changing the algorithm
summary: >-
  Iteration-7 step K on Qwen3-8B (rev b968826d, bf16 HF, thinking off, one RTX 4090). Question: why did iteration 4's per-sample
  plan noise (random direction pushed into task-spec states of blocks 12-23, prefill only, displacement-targeted) move T10
  25/50 while iteration 5's moved 1/50? Crossed dose unit (U_abs = ban displacement norm n[l,p] vs U_bf = ||h_twin||*r_Q)
  x direction seeds (S4 exp29 vs S5 exp27) on shared CRN slots, one engine, shared-prefix path. ANCHORS reproduce: D1=U_abs
  x S4 26/50 attempted (exp29 25/50, per-slot agreement 0.98); D4=U_bf x S5 1/50 (exp27 1/50) -> decoding path is not the
  cause. S1 verdict UNIT (committed rule, Holm): T10 a2 shares D1 .50 D2 .52 D3 .10 D4 .02; unit RD +0.45 [0.35,0.55], seed
  +0.03 [-0.07,0.14], interaction -0.10 [-0.28,0.08]; T2 a2 (N 100) unit +0.115 [0.06,0.17]; a1 replicates. D5 (U_bf* = U_bf
  profile at U_abs per-block energy) 0.28: profile at matched energy +0.22 [0.08,0.36], energy +0.18 [0.06,0.30]. S2 (T10):
  top-quartile cells 29/50 vs rest 15/50 (McNemar 18:4, Holm p .009); position-shuffled 4/50 vs 25/50 -> pushes act where
  bans write. Downstream displacement SIZE does not explain it (U_abs and U_bf have similar block-35 norms; mediation leaves
  unit coefficients unchanged). Exploratory: E1 U_bf needs alpha~4 (20/50) to approach U_abs at alpha 2; E2 per-sample escapes
  are near-independent across directions on one token stream (phi .16-.20) and unpredictable from block-35 displacement at
  fixed dose (AUC .40-.53); E3 replicates on 50 fresh T10 slots (unit +0.42 [0.32,0.52]) and on T03 (+0.27 [0.18,0.37]). S3
  prices at D*=D1 (exp27 full-simplex hull, 2,000 slot bootstraps): H5 PN* vs base intent T03 3.22 vs 1.73 WIN, T1 1.39 vs
  1.05 WIN, T10 2.13 vs 2.53, T2 1.21 vs 1.45, T05 1.10 vs 1.61 LOSS -> 2/5 (predicted 3); iteration-5 rule replayed still
  DISCONFIRMED (2/5) but D_bar moves -0.40 -> +0.12 [-0.18,0.27]. Re-tag: iteration-5 plan-sampler and movability verdicts
  tagged 'ban-free unit and iteration-5 seeds'; at D* T03/T10 movable, T2/T05/T1 not. Novelty: 5 correct 'other' programs
  (T03) all catalogue variants, 0 novel. CAVEATS: T2's U_abs puts 82% of its energy on one massive-activation cell (a '0'
  token, residual norm ~10,290), so T2 profile arms are confounded (P_rest breaks programs); engine check vs exp30 15/16 on
  T2 and T03; 17/25 S3 knob cells reuse exp27 rows (cross-engine), 8 regenerated. Audits: gates G1-G5, GPU unit tests U1-U6,
  sha256 commit chain (0 rows before their commit), stdlib re-derivation of every headline (0 mismatches, placebos null).
  Files: results/{anchors,s1_2x2,s2_profile,s3_prices,retag,e1_sweep,e2_geometry,e3_replicate,novelty_audit}.json; data/samples.jsonl
  (per-program rows), data/raw/*.jsonl (texts, token ids), data/realised_disp.jsonl (36-block displacement profiles); cache/
  (fp16 block-35 displacement vectors, unit dumps); figures F1-F7, E1, E3; method_out.json (exp_gen_sol_out, 1,000 per-slot
  examples with predict_<arm>='label|passed'). GPU ~0.66 h; OpenRouter USD 0.10.
workspace_path: >-
  /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36
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
Raw data URL: https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-7/experiment-36/demo/mini_demo_data.json

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
GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-7/experiment-36/demo/mini_demo_data.json"
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
To test-run the notebook in a clean environment (simulating Colab), use the disposable venv at `/tmp/aii_nb_test_envs/art_8O5eaNc5gxJs-e3ffb3a2e51e`. It is on this machine's local disk, outside your workspace, which is on a slow network volume: never create a venv inside your workspace.
```bash
UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_8O5eaNc5gxJs-e3ffb3a2e51e
UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_8O5eaNc5gxJs-e3ffb3a2e51e/bin/python jupyter ipykernel
/tmp/aii_nb_test_envs/art_8O5eaNc5gxJs-e3ffb3a2e51e/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb
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
TODO 6. Verify: (1) code_demo.ipynb contains GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-7/experiment-36/demo/mini_demo_data.json" exactly, (2) mini_demo_data.json exists, (3) uses GitHub URL pattern not just open('mini_demo_data.json').
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

### [3] ASSISTANT · 2026-10-26 13:00:20 UTC

```
I'll start by loading the two required skills and looking at the workspace and the artifact source in parallel.
```

### [4] TOOL CALL — Skill · 2026-10-26 13:00:20 UTC

```
aii-colab
```

### [5] TOOL CALL — Skill · 2026-10-26 13:00:21 UTC

```
aii-long-running-tasks
```

### [6] TOOL RESULT — Skill · 2026-10-26 13:00:21 UTC

```
{"success": true, "commandName": "aii-colab"}
```

### [7] TOOL RESULT — Skill · 2026-10-26 13:00:21 UTC

```
{"success": true, "commandName": "aii-long-running-tasks"}
```

### [8] TOOL CALL — Bash · 2026-10-26 13:00:21 UTC

```
List workspace and artifact directory contents:
ls -la && ls -la .aii 2>/dev/null && git log --oneline | head -5; echo "---ARTIFACT---"; ls -la /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36/
```

### [9] TOOL RESULT — Bash · 2026-10-26 13:00:21 UTC

```
{"stdout": "total 2966\ndrwxrwxrwx 3 aii-agent aii-agent 1003036 Oct 26 12:59 .\ndrwxrwxrwx 7 aii-agent aii-agent 2000818 Oct 26 12:59 ..\ndrwxrwxrwx 2 aii-agent aii-agent       1 Oct 26 12:59 .aii\n-rw-rw-rw- 1 aii-agent aii-agent      54 Oct 26 12:59 .aii_claude_session.json\n-rw-rw-rw- 1 aii-agent aii-agent   31111 Oct 26 13:00 .repl_agent.ptylog\ntotal 981\ndrwxrwxrwx 2 aii-agent aii-agent       1 Oct 26 12:59 .\ndrwxrwxrwx 3 aii-agent aii-agent 1003036 Oct 26 12:59 ..\nfatal: not a git repository (or any parent up to mount point /ai-inventor)\nStopping at filesystem boundary (GIT_DISCOVERY_ACROSS_FILESYSTEM not set).\n---ARTIFACT---\ntotal 26547\ndrwxrwxrwx 13 aii-agent aii-agent 2042518 Oct 23 00:07 .\ndrwxrwxrwx  9 aii-agent aii-agent 3000174 Oct 22 15:23 ..\ndrwxrwxrwx  2 aii-agent aii-agent   51200 Oct 22 15:21 .aii\n-rw-rw-rw-  1 aii-agent aii-agent      54 Oct 22 13:03 .aii_claude_session.json\n-rw-rw-rw-  1 aii-agent aii-agent    9263 Oct 22 15:21 .aii_worker_result.json\n-rw-rw-rw-  1 aii-agent aii-agent 2140776 Oct 22 15:21 .repl_agent.ptylog\n-rw-rw-rw-  1 aii-agent aii-agent    3623 Oct 22 15:19 .terminal_claude_agent_struct_out.json\n-rw-rw-rw-  1 aii-agent aii-agent   24997 Oct 22 15:19 README.md\ndrwxrwxrwx  2 aii-agent aii-agent 1001603 Oct 22 14:02 audit\ndrwxrwxrwx  4 aii-agent aii-agent 2007115 Oct 22 14:06 cache\n-rw-rw-rw-  1 aii-agent aii-agent    3878 Oct 22 14:49 commitments.log\ndrwxrwxrwx  3 aii-agent aii-agent 2003239 Oct 22 14:53 data\ndrwxrwxrwx  2 aii-agent aii-agent 2000191 Oct 22 14:42 figures\n-rw-rw-rw-  1 aii-agent aii-agent 1603968 Oct 22 15:15 full_method_out.json\ndrwxrwxrwx 13 aii-agent aii-agent 2017522 Oct 22 13:11 inputs\ndrwxrwxrwx  2 aii-agent aii-agent 1029994 Oct 22 15:08 logs\n-rw-rw-rw-  1 aii-agent aii-agent    6661 Oct 22 14:31 method.py\n-rw-rw-rw-  1 aii-agent aii-agent 1464527 Oct 22 15:15 method_out.json\n-rw-rw-rw-  1 aii-agent aii-agent  318649 Oct 22 15:15 mini_method_out.json\ndrwxrwxrwx  2 aii-agent aii-agent 1000873 Oct 22 13:47 predictions\n-rw-rw-rw-  1 aii-agent aii-agent  242996 Oct 22 15:15 preview_method_out.json\n-rw-rw-rw-  1 aii-agent aii-agent    2686 Oct 22 13:07 pyproject.toml\n-rw-rw-rw-  1 aii-agent aii-agent    9834 Oct 22 15:13 reproducibility.md\ndrwxrwxrwx  2 aii-agent aii-agent 2000509 Oct 22 15:02 results\ndrwxrwxrwx  2 aii-agent aii-agent 1020563 Oct 23 00:07 src\n-rw-rw-rw-  1 aii-agent aii-agent  155103 Oct 22 14:31 uv.lock\ndrwxrwxrwx  6 aii-agent aii-agent 2013317 Oct 22 13:10 vendor", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [10] THINKING · 2026-10-26 13:00:33 UTC

```
Both skills are loaded, and since there's no todo-tracking tool here, I'll track the six TODOs inline. TODO 1 is done—now I'll read `method.py` and the surrounding artifact structure for TODO 2.
```

### [11] TOOL CALL — Bash · 2026-10-26 13:00:33 UTC

```
Read method.py, pyproject, and list artifact subdirectories:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36; cat -n $A/method.py; echo "=====PYPROJECT"; cat $A/pyproject.toml; echo "=====SRC"; ls -la $A/src; echo "====RESULTS"; ls -la $A/results $A/data $A/figures $A/cache $A/inputs $A/audit $A/predictions $A/vendor | head -150
```

### [12] TOOL RESULT — Bash · 2026-10-26 13:00:33 UTC

```
{"stdout": "     1\t#!/usr/bin/env python3\n     2\t\"\"\"Step K of iteration 7: why random nudges stopped changing the algorithm.\n     3\t\n     4\tEntry point. Every step is a module in src/ (run in its own process; the GPU steps load one 8B model at a time) and is\n     5\tresumable: generation is keyed by <task>|<template>|<arm>|<sample_id>, labels by the same key, and the commits only\n     6\tappend to the hash chain when their file is missing.\n     7\t\n     8\t  setup      copy and sha256-verify every earlier-artifact input into inputs/ and vendor/   (src/setup_inputs.py)\n     9\t  gates      CPU gates G1-G5 -> results/cpu_gates.json                                      (src/s3_prices.py g5, src/cpu_gates.py)\n    10\t  label      start the label worker in the background (follows data/raw/*.jsonl)          (src/label_k.py)\n    11\t  gpu0       hardware record, memory probe, GPU unit tests U1-U6, S0 twins                 (src/gen_k.py tests s0)\n    12\t  commit1    COMMIT #1: design table, units, seeds, rules, predictions, analysis code hash (src/make_commits.py)\n    13\t  gpu1       S1 2x2 (anchors first) + D5 + S2 profiles                                     (src/gen_k.py s1 d5 s2)\n    14\t  commit2    COMMIT #2: D* rule applied to the labelled S1 rows, S3 predictions and rules  (src/make_commits.py)\n    15\t  gpu2       S3 plan-noise cells at D* on T03, T05, T1                                      (src/gen_k.py s3pn)\n    16\t  knobs      base-model intents, exp27 knob rows relabelled, knob check, reruns            (src/knobs_k.py)\n    17\t  units      dose units in activation coordinates for the figures                          (src/dump_units.py)\n    18\t  e1         exploratory dose sweep of the ban-free unit (committed before its first row)  (src/e1_sweep.py)\n    19\t  analyse    anchors, S1 2x2, D5 split, mediation, S2, D*, E1                               (src/analysis_k.py all)\n    20\t  prices     S3 hull prices + 2,000 bootstraps, readings, re-tag                            (src/s3_prices.py prices / retag)\n    21\t  novelty    nearest-known search over the dependency corpus + two-family judge audit      (src/novelty_k.py)\n    22\t  geometry   exploratory E2: downstream displacement direction vs size                     (src/geometry_k.py)\n    23\t  figures    F1-F7 and E1 in figures/                                                       (src/figures_k.py)\n    24\t  report     engine check, timing, costs, deviations, commit-order audit                   (src/report_k.py)\n    25\t  rederive   independent stdlib re-derivation with placebos                                 (audit/rederive.py)\n    26\t  outputs    method_out.json (+ full/mini/preview) in the exp_gen_sol_out schema           (src/outputs_k.py)\n    27\t  all        every step above in order\n    28\t\n    29\tusage: uv run method.py <step> [<step> ...]      (or .venv/bin/python method.py ...)\n    30\t\"\"\"\n    31\t\n    32\tfrom __future__ import annotations\n    33\t\n    34\timport os\n    35\timport subprocess\n    36\timport sys\n    37\timport time\n    38\tfrom pathlib import Path\n    39\t\n    40\tfrom loguru import logger\n    41\t\n    42\tROOT = Path(__file__).resolve().parent\n    43\tPY = str(ROOT / \".venv\" / \"bin\" / \"python\") if (ROOT / \".venv\" / \"bin\" / \"python\").exists() else sys.executable\n    44\tLOGS = ROOT / \"logs\"\n    45\tLOGS.mkdir(exist_ok=True)\n    46\tlogger.remove()\n    47\tlogger.add(sys.stdout, level=\"INFO\", format=\"{time:HH:mm:ss}|{level:<7}|{message}\")\n    48\tlogger.add(str(LOGS / \"method.log\"), rotation=\"30 MB\", level=\"DEBUG\")\n    49\t\n    50\tSTEPS: dict[str, list[list[str]]] = {\n    51\t    \"setup\": [[\"src/setup_inputs.py\"]],\n    52\t    \"gates\": [[\"src/s3_prices.py\", \"g5\"], [\"src/cpu_gates.py\"]],\n    53\t    \"gpu0\": [[\"src/gen_k.py\", \"tests\", \"s0\"]],\n    54\t    \"commit1\": [[\"src/make_commits.py\", \"commit1\"]],\n    55\t    \"gpu1\": [[\"src/gen_k.py\", \"s1\", \"d5\", \"s2\"]],\n    56\t    \"commit2\": [[\"src/make_commits.py\", \"commit2\"]],\n    57\t    \"gpu2\": [[\"src/gen_k.py\", \"s3pn\"]],\n    58\t    \"knobs\": [[\"src/knobs_k.py\", \"base,reuse,check,verdict,rerun\"]],\n    59\t    \"units\": [[\"src/dump_units.py\"]],\n    60\t    \"e1\": [[\"src/e1_sweep.py\"]],\n    61\t    \"analyse\": [[\"src/analysis_k.py\", \"all\"]],\n    62\t    \"prices\": [[\"src/s3_prices.py\", \"prices\"], [\"src/s3_prices.py\", \"retag\"]],\n    63\t    \"novelty\": [[\"src/novelty_k.py\"], [\"src/novelty_k.py\", \"--manual-only\"]],\n    64\t    \"geometry\": [[\"src/geometry_k.py\"]],\n    65\t    \"figures\": [[\"src/figures_k.py\"]],\n    66\t    \"report\": [[\"src/report_k.py\"]],\n    67\t    \"rederive\": [[\"audit/rederive.py\"]],\n    68\t    \"outputs\": [[\"src/outputs_k.py\"]],\n    69\t}\n    70\tORDER = [\"setup\", \"gates\", \"label\", \"gpu0\", \"commit1\", \"gpu1\", \"commit2\", \"gpu2\", \"knobs\", \"units\", \"e1\", \"analyse\",\n    71\t         \"prices\", \"novelty\", \"geometry\", \"figures\", \"report\", \"rederive\", \"outputs\"]\n    72\tSKIP_IF_EXISTS = {\"commit1\": ROOT / \"predictions\" / \"commit1.json\", \"commit2\": ROOT / \"predictions\" / \"commit2.json\"}\n    73\t\n    74\t\n    75\tdef run(cmd: list[str]) -> None:\n    76\t    t0 = time.time()\n    77\t    logger.info(f\"run {' '.join(cmd)}\")\n    78\t    r = subprocess.run([PY, *cmd], cwd=ROOT)\n    79\t    if r.returncode != 0:\n    80\t        raise RuntimeError(f\"{' '.join(cmd)} exited with {r.returncode}\")\n    81\t    logger.info(f\"done {' '.join(cmd)} in {time.time() - t0:.0f}s\")\n    82\t\n    83\t\n    84\tdef start_labeller() -> None:\n    85\t    pid_file = LOGS / \"label_worker.pid\"\n    86\t    if pid_file.exists():\n    87\t        try:\n    88\t            os.kill(int(pid_file.read_text().strip()), 0)\n    89\t            logger.info(\"label worker already running\")\n    90\t            return\n    91\t        except (OSError, ValueError):\n    92\t            pass\n    93\t    with open(LOGS / \"label_k.stdout\", \"a\") as out:\n    94\t        p = subprocess.Popen([PY, \"src/label_k.py\"], cwd=ROOT, stdout=out, stderr=subprocess.STDOUT)\n    95\t    pid_file.write_text(str(p.pid))\n    96\t    logger.info(f\"label worker started (PID {p.pid})\")\n    97\t\n    98\t\n    99\tdef wait_labelled(timeout_s: float = 3600) -> None:\n   100\t    \"\"\"Block until every generated row has a label (needed before COMMIT #2, the knob verdict and the analyses).\"\"\"\n   101\t    sys.path.insert(0, str(ROOT / \"src\"))\n   102\t    import k_cfg as K\n   103\t\n   104\t    t0 = time.time()\n   105\t    while time.time() - t0 < timeout_s:\n   106\t        keys = {K.row_key(r) for n in (\"raw_k.jsonl\", \"knobs_norm.jsonl\", \"reuse_exp27.jsonl\")\n   107\t                for r in K.read_jsonl(K.RAW_DIR / n)}\n   108\t        done = {l[\"key\"] for l in K.read_jsonl(K.LABELS)}\n   109\t        miss = len(keys - done)\n   110\t        if miss == 0:\n   111\t            return\n   112\t        logger.info(f\"waiting for {miss} labels\")\n   113\t        time.sleep(20)\n   114\t    raise TimeoutError(\"labels incomplete\")\n   115\t\n   116\t\n   117\t@logger.catch(reraise=True)\n   118\tdef main() -> None:\n   119\t    steps = sys.argv[1:] or [\"all\"]\n   120\t    if steps == [\"all\"]:\n   121\t        steps = ORDER\n   122\t    for s in steps:\n   123\t        if s == \"label\":\n   124\t            start_labeller()\n   125\t            continue\n   126\t        if s not in STEPS:\n   127\t            raise SystemExit(f\"unknown step {s}; choose from {ORDER + ['all']}\")\n   128\t        if s in SKIP_IF_EXISTS and SKIP_IF_EXISTS[s].exists():\n   129\t            logger.info(f\"{s}: {SKIP_IF_EXISTS[s].name} exists (hash-chained); not rewritten\")\n   130\t            continue\n   131\t        if s in (\"commit2\", \"analyse\", \"prices\"):\n   132\t            wait_labelled()\n   133\t        for cmd in STEPS[s]:\n   134\t            run(cmd)\n   135\t\n   136\t\n   137\tif __name__ == \"__main__\":\n   138\t    main()\n=====PYPROJECT\n[project]\nname = \"plan-noise-crosswalk-k\"\nversion = \"1.0.0\"\ndescription = \"Iteration 7 step K: plan-noise unit x seeds crosswalk, profile split and prices on bf16 Qwen3-8B.\"\nrequires-python = \"==3.12.*\"\n# Every package is pinned to the exact version installed in .venv (`uv pip freeze --python .venv/bin/python`; the\n# uv-created venv has no pip). Python 3.12.14. torch 2.8.0+cu128 wheels come from PyPI's default CUDA 12.8 build.\ndependencies = [\n    \"accelerate==1.15.0\",\n    \"annotated-types==0.8.0\",\n    \"anyio==4.15.1\",\n    \"astor==0.8.1\",\n    \"attrs==26.1.0\",\n    \"certifi==2026.10.19\",\n    \"charset-normalizer==3.5.2\",\n    \"cloudpickle==3.1.2\",\n    \"contourpy==1.4.0\",\n    \"cycler==0.12.1\",\n    \"filelock==4.2.4\",\n    \"fonttools==4.67.0\",\n    \"formulaic==1.2.2\",\n    \"fsspec==2026.9.0\",\n    \"h11==0.16.0\",\n    \"hf-xet==1.7.0\",\n    \"httpcore2==2.16.0\",\n    \"httpx2==2.16.0\",\n    \"huggingface-hub==0.36.2\",\n    \"idna==3.20\",\n    \"interface-meta==2.0.1\",\n    \"jinja2==3.1.6\",\n    \"jiter==0.17.0\",\n    \"joblib==1.6.0\",\n    \"jsonschema-specifications==2025.9.1\",\n    \"jsonschema==4.26.0\",\n    \"kiwisolver==1.5.1\",\n    \"loguru==0.7.3\",\n    \"markupsafe==3.0.4\",\n    \"matplotlib==3.11.2\",\n    \"mpmath==1.3.0\",\n    \"narwhals==2.27.1\",\n    \"networkx==3.7\",\n    \"numpy==2.2.6\",\n    \"nvidia-cublas-cu12==12.8.4.1\",\n    \"nvidia-cuda-cupti-cu12==12.8.90\",\n    \"nvidia-cuda-nvrtc-cu12==12.8.93\",\n    \"nvidia-cuda-runtime-cu12==12.8.90\",\n    \"nvidia-cudnn-cu12==9.10.2.21\",\n    \"nvidia-cufft-cu12==11.3.3.83\",\n    \"nvidia-cufile-cu12==1.13.1.3\",\n    \"nvidia-curand-cu12==10.3.9.90\",\n    \"nvidia-cusolver-cu12==11.7.3.90\",\n    \"nvidia-cusparse-cu12==12.5.8.93\",\n    \"nvidia-cusparselt-cu12==0.7.1\",\n    \"nvidia-nccl-cu12==2.27.3\",\n    \"nvidia-nvjitlink-cu12==12.8.93\",\n    \"nvidia-nvtx-cu12==12.8.90\",\n    \"openai==3.35.1\",\n    \"packaging==26.3\",\n    \"pandas==3.0.6\",\n    \"patsy==1.0.3\",\n    \"pillow==13.0.0\",\n    \"psutil==7.2.2\",\n    \"pydantic-core==2.50.1\",\n    \"pydantic==2.14.1\",\n    \"pyparsing==3.3.3\",\n    \"python-dateutil==3.0.0\",\n    \"pyyaml==6.0.3\",\n    \"rapidfuzz==3.14.6\",\n    \"referencing==0.37.0\",\n    \"regex==2026.9.29\",\n    \"requests==2.34.2\",\n    \"rpds-py==2026.9.1\",\n    \"safetensors==0.8.0\",\n    \"scikit-learn==1.9.1\",\n    \"scipy==1.18.1\",\n    \"setuptools==84.2.1\",\n    \"six==1.17.0\",\n    \"sniffio==1.3.1\",\n    \"statsmodels==0.15.0\",\n    \"sympy==1.14.0\",\n    \"tenacity==9.2.1\",\n    \"threadpoolctl==3.7.0\",\n    \"tokenizers==0.22.2\",\n    \"torch==2.8.0\",\n    \"tqdm==4.70.1\",\n    \"transformers==4.57.6\",\n    \"triton==3.4.0\",\n    \"truststore==0.10.5\",\n    \"typing-extensions==4.16.0\",\n    \"typing-inspection==0.4.4\",\n    \"tzdata==2026.5\",\n    \"urllib3==2.8.0\",\n    \"wrapt==2.5.1\",\n]\n=====SRC\ntotal 3202\ndrwxrwxrwx  2 aii-agent aii-agent 1020563 Oct 23 00:07 .\ndrwxrwxrwx 13 aii-agent aii-agent 2042518 Oct 23 00:07 ..\n-rw-rw-rw-  1 aii-agent aii-agent   26529 Oct 22 14:46 analysis_k.py\n-rw-rw-rw-  1 aii-agent aii-agent    2105 Oct 22 13:28 commit_k.py\n-rw-rw-rw-  1 aii-agent aii-agent   13352 Oct 22 14:59 cpu_gates.py\n-rw-rw-rw-  1 aii-agent aii-agent    3113 Oct 22 14:01 dump_units.py\n-rw-rw-rw-  1 aii-agent aii-agent    1228 Oct 22 14:03 e1_sweep.py\n-rw-rw-rw-  1 aii-agent aii-agent    1514 Oct 22 14:32 e3_replicate.py\n-rw-rw-rw-  1 aii-agent aii-agent    2981 Oct 22 14:34 extensions_k.py\n-rw-rw-rw-  1 aii-agent aii-agent   16217 Oct 22 14:46 figures_k.py\n-rw-rw-rw-  1 aii-agent aii-agent   29628 Oct 22 13:21 gen_k.py\n-rw-rw-rw-  1 aii-agent aii-agent   10142 Oct 22 14:48 geometry_k.py\n-rw-rw-rw-  1 aii-agent aii-agent    7013 Oct 22 13:15 k_cfg.py\n-rw-rw-rw-  1 aii-agent aii-agent    5102 Oct 22 13:16 k_units.py\n-rw-rw-rw-  1 aii-agent aii-agent    9232 Oct 22 13:39 knobs_k.py\n-rw-rw-rw-  1 aii-agent aii-agent    5479 Oct 22 13:40 label_k.py\n-rw-rw-rw-  1 aii-agent aii-agent    9277 Oct 22 13:33 make_commits.py\n-rw-rw-rw-  1 aii-agent aii-agent   17197 Oct 22 14:17 novelty_k.py\n-rw-rw-rw-  1 aii-agent aii-agent    9074 Oct 22 14:42 outputs_k.py\n-rw-rw-rw-  1 aii-agent aii-agent   14101 Oct 22 14:53 report_k.py\n-rw-rw-rw-  1 aii-agent aii-agent   16858 Oct 22 13:43 s3_prices.py\n-rw-rw-rw-  1 aii-agent aii-agent   10427 Oct 22 15:10 setup_inputs.py\n====RESULTS\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36/audit:\ntotal 2990\ndrwxrwxrwx  2 aii-agent aii-agent 1001603 Oct 22 14:02 .\ndrwxrwxrwx 13 aii-agent aii-agent 2042518 Oct 23 00:07 ..\n-rw-rw-rw-  1 aii-agent aii-agent   16416 Oct 22 15:11 rederive.py\n\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36/cache:\ntotal 6960\ndrwxrwxrwx  4 aii-agent aii-agent 2007115 Oct 22 14:06 .\ndrwxrwxrwx 13 aii-agent aii-agent 2042518 Oct 23 00:07 ..\ndrwxrwxrwx  2 aii-agent aii-agent 2007048 Oct 22 14:38 disp\ndrwxrwxrwx  2 aii-agent aii-agent 1068737 Oct 22 14:06 units\n\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36/data:\ntotal 23054\ndrwxrwxrwx  3 aii-agent aii-agent 2003239 Oct 22 14:53 .\ndrwxrwxrwx 13 aii-agent aii-agent 2042518 Oct 23 00:07 ..\n-rw-rw-rw-  1 aii-agent aii-agent  222434 Oct 22 13:53 bint_intents.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent   22419 Oct 22 14:37 judge_cache.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent  111213 Oct 22 14:12 judge_cache_paths.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent  290490 Oct 22 14:03 knobs_stages.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent 5891957 Oct 22 14:38 labels.jsonl\ndrwxrwxrwx  2 aii-agent aii-agent 2001565 Oct 22 13:58 raw\n-rw-rw-rw-  1 aii-agent aii-agent 4214705 Oct 22 14:38 realised_disp.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent 6804465 Oct 22 15:02 samples.jsonl\n\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36/figures:\ntotal 5910\ndrwxrwxrwx  2 aii-agent aii-agent 2000191 Oct 22 14:42 .\ndrwxrwxrwx 13 aii-agent aii-agent 2042518 Oct 23 00:07 ..\n-rw-rw-rw-  1 aii-agent aii-agent   18992 Oct 22 14:50 E1_dose_response.pdf\n-rw-rw-rw-  1 aii-agent aii-agent  135493 Oct 22 14:50 E1_dose_response.png\n-rw-rw-rw-  1 aii-agent aii-agent   21774 Oct 22 14:50 E3_replicate.pdf\n-rw-rw-rw-  1 aii-agent aii-agent   62075 Oct 22 14:50 E3_replicate.png\n-rw-rw-rw-  1 aii-agent aii-agent   21575 Oct 22 14:50 F1_s1_interaction.pdf\n-rw-rw-rw-  1 aii-agent aii-agent  101729 Oct 22 14:50 F1_s1_interaction.png\n-rw-rw-rw-  1 aii-agent aii-agent   59554 Oct 22 14:50 F2_unit_heatmaps.pdf\n-rw-rw-rw-  1 aii-agent aii-agent  257581 Oct 22 14:50 F2_unit_heatmaps.png\n-rw-rw-rw-  1 aii-agent aii-agent   26501 Oct 22 14:50 F3_displacement_blocks.pdf\n-rw-rw-rw-  1 aii-agent aii-agent  281631 Oct 22 14:50 F3_displacement_blocks.png\n-rw-rw-rw-  1 aii-agent aii-agent   41692 Oct 22 14:50 F4_escape_vs_disp.pdf\n-rw-rw-rw-  1 aii-agent aii-agent  180278 Oct 22 14:50 F4_escape_vs_disp.png\n-rw-rw-rw-  1 aii-agent aii-agent   52453 Oct 22 14:50 F5_pca_disp35.pdf\n-rw-rw-rw-  1 aii-agent aii-agent  251738 Oct 22 14:50 F5_pca_disp35.png\n-rw-rw-rw-  1 aii-agent aii-agent   33527 Oct 22 14:50 F6_price_frontiers.pdf\n-rw-rw-rw-  1 aii-agent aii-agent  143130 Oct 22 14:50 F6_price_frontiers.png\n-rw-rw-rw-  1 aii-agent aii-agent   50383 Oct 22 14:48 F7_escape_axis.pdf\n-rw-rw-rw-  1 aii-agent aii-agent  262726 Oct 22 14:48 F7_escape_axis.png\n\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36/inputs:\ntotal 19003\ndrwxrwxrwx 13 aii-agent aii-agent 2017522 Oct 22 13:11 .\ndrwxrwxrwx 13 aii-agent aii-agent 2042518 Oct 23 00:07 ..\n-rw-rw-rw-  1 aii-agent aii-agent  236574 Oct 22 15:10 MANIFEST.tsv\ndrwxrwxrwx  2 aii-agent aii-agent 2009208 Oct 22 13:09 dep_art_j3Rm\ndrwxrwxrwx  3 aii-agent aii-agent 1001569 Oct 22 13:09 exp11\ndrwxrwxrwx  3 aii-agent aii-agent 1038523 Oct 22 13:09 exp13\ndrwxrwxrwx  3 aii-agent aii-agent 1001885 Oct 22 13:09 exp17\ndrwxrwxrwx  3 aii-agent aii-agent   91800 Oct 22 13:09 exp18\ndrwxrwxrwx  4 aii-agent aii-agent 2001395 Oct 22 13:09 exp19\ndrwxrwxrwx  2 aii-agent aii-agent 1006369 Oct 22 13:11 exp22\ndrwxrwxrwx  3 aii-agent aii-agent 1000729 Oct 22 13:09 exp23\ndrwxrwxrwx  5 aii-agent aii-agent 2003098 Oct 22 13:09 exp27\ndrwxrwxrwx  6 aii-agent aii-agent 2003085 Oct 22 13:11 exp29\ndrwxrwxrwx  5 aii-agent aii-agent 2000663 Oct 22 13:11 exp30\n\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36/predictions:\ntotal 2982\ndrwxrwxrwx  2 aii-agent aii-agent 1000873 Oct 22 13:47 .\ndrwxrwxrwx 13 aii-agent aii-agent 2042518 Oct 23 00:07 ..\n-rw-rw-rw-  1 aii-agent aii-agent    5665 Oct 22 13:33 commit1.json\n-rw-rw-rw-  1 aii-agent aii-agent    2886 Oct 22 13:47 commit2.json\n-rw-rw-rw-  1 aii-agent aii-agent     396 Oct 22 13:23 hardware.json\n\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36/results:\ntotal 9180\ndrwxrwxrwx  2 aii-agent aii-agent 2000509 Oct 22 15:02 .\ndrwxrwxrwx 13 aii-agent aii-agent 2042518 Oct 23 00:07 ..\n-rw-rw-rw-  1 aii-agent aii-agent     669 Oct 22 14:46 anchors.json\n-rw-rw-rw-  1 aii-agent aii-agent     261 Oct 22 13:53 bint_intent_identity.json\n-rw-rw-rw-  1 aii-agent aii-agent     539 Oct 22 15:02 commit_audit.json\n-rw-rw-rw-  1 aii-agent aii-agent     125 Oct 22 15:02 commit_chain_verify.json\n-rw-rw-rw-  1 aii-agent aii-agent     293 Oct 22 15:02 costs.json\n-rw-rw-rw-  1 aii-agent aii-agent    9083 Oct 22 15:00 cpu_gates.json\n-rw-rw-rw-  1 aii-agent aii-agent    4383 Oct 22 15:02 deviations.json\n-rw-rw-rw-  1 aii-agent aii-agent   73670 Oct 22 15:02 displacement.json\n-rw-rw-rw-  1 aii-agent aii-agent      41 Oct 22 14:12 e1_done.json\n-rw-rw-rw-  1 aii-agent aii-agent   14609 Oct 22 14:47 e1_sweep.json\n-rw-rw-rw-  1 aii-agent aii-agent    4387 Oct 22 14:48 e2_geometry.json\n-rw-rw-rw-  1 aii-agent aii-agent      41 Oct 22 14:38 e3_done.json\n-rw-rw-rw-  1 aii-agent aii-agent   20108 Oct 22 14:40 e3_replicate.json\n-rw-rw-rw-  1 aii-agent aii-agent    1202 Oct 22 15:02 engine_check.json\n-rw-rw-rw-  1 aii-agent aii-agent     410 Oct 22 14:10 g5_hull_gate.json\n-rw-rw-rw-  1 aii-agent aii-agent     110 Oct 22 13:51 gpu_done.json\n-rw-rw-rw-  1 aii-agent aii-agent      12 Oct 22 13:24 gpu_state.json\n-rw-rw-rw-  1 aii-agent aii-agent   24374 Oct 22 13:58 knob_check.json\n-rw-rw-rw-  1 aii-agent aii-agent     101 Oct 22 14:04 knobs_done.json\n-rw-rw-rw-  1 aii-agent aii-agent   15959 Oct 22 14:04 knobs_timing.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent     107 Oct 22 13:24 memory_probe.json\n-rw-rw-rw-  1 aii-agent aii-agent   36309 Oct 22 14:17 novelty_audit.json\n-rw-rw-rw-  1 aii-agent aii-agent      70 Oct 22 14:14 novelty_costs.json\n-rw-rw-rw-  1 aii-agent aii-agent     721 Oct 22 14:17 novelty_manual.json\n-rw-rw-rw-  1 aii-agent aii-agent    8599 Oct 22 14:14 novelty_programs.json\n-rw-rw-rw-  1 aii-agent aii-agent     160 Oct 22 14:12 openrouter_cost_paths.json\n-rw-rw-rw-  1 aii-agent aii-agent    3774 Oct 22 15:11 rederive.json\n-rw-rw-rw-  1 aii-agent aii-agent    2121 Oct 22 14:11 retag.json\n-rw-rw-rw-  1 aii-agent aii-agent   31819 Oct 22 14:47 s1_2x2.json\n-rw-rw-rw-  1 aii-agent aii-agent    5954 Oct 22 15:02 s1_clogit.json\n-rw-rw-rw-  1 aii-agent aii-agent    2231 Oct 22 15:02 s1_mediation.json\n-rw-rw-rw-  1 aii-agent aii-agent    9669 Oct 22 14:47 s2_profile.json\n-rw-rw-rw-  1 aii-agent aii-agent 4861112 Oct 22 14:11 s3_bootstrap.json\n-rw-rw-rw-  1 aii-agent aii-agent  115557 Oct 22 14:11 s3_prices.json\n-rw-rw-rw-  1 aii-agent aii-agent    2549 Oct 22 15:02 timing.json\n-rw-rw-rw-  1 aii-agent aii-agent   66818 Oct 22 14:38 timing.jsonl\n-rw-rw-rw-  1 aii-agent aii-agent   20453 Oct 22 14:06 unit_profiles.json\n-rw-rw-rw-  1 aii-agent aii-agent    7009 Oct 22 13:25 unit_tests_gpu.json\n\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36/vendor:\ntotal 9909\ndrwxrwxrwx  6 aii-agent aii-agent 2013317 Oct 22 13:10 .\ndrwxrwxrwx 13 aii-agent aii-agent 2042518 Oct 23 00:07 ..\n-rw-rw-rw-  1 aii-agent aii-agent   69036 Oct 22 05:02 SHA256SUMS_exp29\ndrwxrwxrwx  3 aii-agent aii-agent 1005492 Oct 22 05:02 exp19\ndrwxrwxrwx 15 aii-agent aii-agent 2005509 Oct 22 13:22 exp22\ndrwxrwxrwx 11 aii-agent aii-agent 2007794 Oct 22 13:49 exp27\ndrwxrwxrwx  3 aii-agent aii-agent 1000715 Oct 22 05:02 exp28", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [13] THINKING · 2026-10-26 13:00:53 UTC

```
method.py orchestrates by running src/ modules as subprocesses, with GPU steps requiring Qwen3-8B in bf16, so the notebook needs to mirror that code. Next I'll read the README, reproducibility notes, and core config/analysis modules.
```

### [14] TOOL CALL — Bash · 2026-10-26 13:00:53 UTC

```
Read the artifact README:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36; cat $A/README.md
```

### [15] TOOL RESULT — Bash · 2026-10-26 13:00:53 UTC

```
{"stdout": "# Why random nudges stopped changing the algorithm\n\nIteration 7, step K of a research run on **Qwen/Qwen3-8B** (revision `b968826d…`, bf16, HF transformers 4.57.6,\nthinking off). The model nearly always writes one default algorithm per task (union-find for connected components\nT10, Dijkstra for weighted shortest paths T2, a full sort for the k-th smallest T03, a hash map for two-sum T05, BFS for\ngrid paths T1).\n\n**Plan noise (PN)** pushes a fresh, isotropic ... [truncated, 25261 chars total]
```

### [16] TOOL CALL — Bash · 2026-10-26 13:00:53 UTC

```
Read reproducibility notes and config module:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36; cat $A/reproducibility.md; echo "=====K_CFG"; cat -n $A/src/k_cfg.py
```

### [17] TOOL RESULT — Bash · 2026-10-26 13:00:53 UTC

````
{"stdout": "# Reproducing step K: plan-noise unit × seeds crosswalk, profile split and prices\n\nThese are the steps that were actually run, in the order they were run, on 2026-10-22, with what each produced. Every\npath below is relative to this artifact's folder.\n\n## 1. Get the artifact\n\n```bash\ngit clone <the run's public repository URL>\ncd <repository>/<this artifact's folder>        # the folder that holds this file, method.py and src/\n```\n\n- **Inputs ship with the folder.** `inputs/` and `vendor/` hold sha256-verified copies of every earlier-artifact\n  input: code, prompts, unit tensors, anchor rows, and the iteration-5 knob rows (`inputs/MANIFEST.tsv` lists source,\n  size and sha256). You do not need the earlier artifacts.\n- **The declared dependency.** `art_j3Rm_lr2nzR6` (dataset) is published as the sibling folder\n  `../art_j3Rm_lr2nzR6`. Its files are also copied into `inputs/dep_art_j3Rm/`.\n- **User uploads.** None were used; the run's user-uploads folder was empty.\n\n## 2. System, Python and libraries\n\n| item | what was used |\n|---|---|\n| OS | Debian GNU/Linux 12 container. The commands below work unchanged on Ubuntu 22.04 / 24.04. |\n| GPU | 1 × NVIDIA GeForce RTX 4090, 24 GB, compute capability 8.9 |\n| NVIDIA driver | 595.91.07 (any driver that runs CUDA 12.8 wheels) |\n| CPU / RAM | 32 cores, 124 GB visible |\n| Python | 3.12.14 |\n| uv | 0.6.14 |\n\n- **System packages:** `git`, `curl`, and a recent `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh`). No\n  compiler is needed.\n- **Hugging Face CLI:** the `hf` command, from the pinned `huggingface-hub==0.36.2`, either installed in `.venv` or\n  through `uvx --from huggingface-hub==0.36.2 hf`.\n\nCreate the environment exactly as it was created:\n\n```bash\nuv venv --python 3.12 .venv\nuv pip install --python .venv/bin/python -r pyproject.toml\n```\n\n- `pyproject.toml` pins all 85 installed packages to the exact versions in `.venv`. The list equals\n  `uv pip freeze --python .venv/bin/python`; uv venvs have no `pip`. `uv.lock` was written by `uv run`.\n- Key versions:\n\n  | package | version |\n  |---|---|\n  | torch | 2.8.0 (+cu128 wheels from PyPI) |\n  | transformers | 4.57.6 |\n  | accelerate | 1.15.0 |\n  | safetensors | 0.8.0 |\n  | tokenizers | 0.22.2 |\n  | huggingface-hub | 0.36.2 |\n  | numpy | 2.2.6 |\n  | scipy | 1.18.1 |\n  | statsmodels | 0.15.0 |\n  | scikit-learn | 1.9.1 |\n  | pandas | 3.0.6 |\n  | matplotlib | 3.11.2 |\n  | openai | 3.35.1 |\n  | loguru | 0.7.3 |\n\n## 3. Models, data and environment variables\n\n```bash\nhf download Qwen/Qwen3-8B      --revision b968826d9c46dd6066d109eabc6255188de91218   # instruct, bf16, ~16 GB\nhf download Qwen/Qwen3-8B-Base --revision 49e3418fbbbca6ecbdf9608b4d22e5a407081db4   # base, ~16 GB (S3 base intents)\n```\n\n**Environment variables, by name only:**\n\n| variable | needed | purpose |\n|---|---|---|\n| `HF_HUB_CACHE` (or `HF_HOME`) | yes | where the snapshots live. The code finds the snapshot through `HF_HUB_CACHE`, as the vendored exp22 `cfg.model_path` does. |\n| `HF_TOKEN` | optional | Hugging Face access token |\n| `OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY` | yes | the labeller's tie-break judges and the novelty audit (USD 0.10 in total in this run) |\n| `AII_DEP_ART_J3RM` | optional | location of the dependency folder (default `../art_j3Rm_lr2nzR6`) |\n| `AII_ITER6_ROOT`, `AII_ITER25_RUN` | optional | locations of the earlier run folders. Used only to re-copy inputs; the copies already ship. |\n\n## 4. Commands, in the order they were run\n\nThe entry point `uv run method.py all` runs the same sequence. In the actual run the steps were launched as separate\nprocesses in this order (start times are UTC on 2026-10-22).\n\n| # | start | command | what it did | wall time |\n|---|---|---|---|---|\n| 1 | 13:05 | `.venv/bin/python src/setup_inputs.py` | copied the inputs; wrote `inputs/MANIFEST.tsv` (1,167 files) | 2 min |\n| 2 | 13:23 | `.venv/bin/python src/gen_k.py tests s0 s1 d5 s2 s3pn` | one GPU process, see step 2 below | 28 min |\n| 3 | 13:26 | `.venv/bin/python src/label_k.py` | label worker in the background for the whole session; restarted at 13:48 after AMENDMENT 1 | — |\n| 4 | 13:33 | `.venv/bin/python src/make_commits.py commit1` | COMMIT #1 | — |\n| 5 | 13:47 | `.venv/bin/python src/make_commits.py commit2` | COMMIT #2 | — |\n| 6 | 13:49 | `.venv/bin/python src/knobs_k.py reuse` | queued exp27's 1,250 knob rows for relabelling | CPU |\n| 7 | 13:52 | `.venv/bin/python src/knobs_k.py base,check,verdict,rerun` | see step 7 below | 13 min |\n| 8 | 13:54 | `.venv/bin/python src/s3_prices.py g5` and `.venv/bin/python src/cpu_gates.py` | gates G1–G5, all pass | — |\n| 9 | 14:05 | `.venv/bin/python src/dump_units.py` | dose units in activation coordinates → `cache/units/` | 1 min |\n| 10 | 14:06 | `.venv/bin/python src/e1_sweep.py` | exploratory E1, hash-committed at 14:04 before its first row | 6 min |\n| 11 | 14:10 | `.venv/bin/python src/s3_prices.py all` | S3 hulls; 2,000 bootstraps × 5 tasks on 16 spawn workers; readings and re-tag | 1.5 min |\n| 12 | 14:14 | `.venv/bin/python src/novelty_k.py`, then `.venv/bin/python src/novelty_k.py --manual-only` | judges (38 calls, USD 0.03), then the manual pass | — |\n| 13 | 14:15 | `.venv/bin/python src/analysis_k.py all`, `src/geometry_k.py`, `src/figures_k.py`, `src/report_k.py`, `src/outputs_k.py`, `python3 audit/rederive.py` | analyses, figures, outputs, re-derivation | — |\n| 14 | 14:32 | `.venv/bin/python src/e3_replicate.py`, then `.venv/bin/python src/extensions_k.py` | exploratory E3, hash-committed at 14:31 before its first row | 7 min |\n| 15 | 14:44–15:15 | AMENDMENT 3, then step 13 again, then `uv run method.py report outputs` and the aii-json mini/preview script | final pass | — |\n\n**Step 2: the single GPU process (`src/gen_k.py`).** It ran these stages in order:\n\n- the hardware record;\n- the model load (22 s);\n- the memory probe (constant B = 12);\n- unit tests U1–U6, all pass;\n- S0 twins;\n- a wait for `predictions/commit1.json`;\n- S1, with the anchors first;\n- D5;\n- S2;\n- a wait for `predictions/commit2.json`;\n- S3 plan noise at D\\* = D1.\n\n**Step 7: the knob process (`src/knobs_k.py`).** It ran exp27's code paths unchanged:\n\n1. The base model (bf16) wrote 250 intents. All 250 match exp27's intents in text and ids.\n2. The base model was unloaded and the instruct model reloaded.\n3. The knob check: 250 rows.\n4. The verdict: 17 of 25 (task, knob) cells reuse exp27's rows.\n5. Reruns at k 2–9: 320 rows.\n\n**Seeds and randomness.**\n\n- Every token stream is `PCG64(stable_seed(task, template, k))`, shared by every arm of a slot.\n- Directions are `S4 = PCG64(stable_seed(task, 'PN_a<α>', w, k))` and `S5 = PCG64(stable_seed(task, 'PN5', w, k))`.\n- `P_shuf` uses `PCG64(stable_seed(task, 'SHUF'))`.\n- The S1 bootstrap seed is 20261022. The S3 bootstrap seeds are `20261021*1000 + i + 7919*task_index`, as in exp27.\n  The hull's point-estimate seed is 0.\n- The sampler is exact inverse-CDF at T 1.0, with no top-k and top-p 1.\n\n**Totals.**\n\n- **GPU time:** about 0.66 GPU-h (`results/timing.json`). That is 2,880 instruct-runner programs at 0.3–0.8\n  s/program with B = 12, plus the knob process (10 min).\n- **OpenRouter spend:** USD 0.10 (`results/costs.json`).\n\n**Determinism.**\n\n- **Same GPU.** On one GPU the runs are bitwise reproducible (U4).\n- **Batch shape.** Batch size does not change a row's tokens (U3).\n- **Another GPU model or driver.** Individual programs can diverge mid-decode. The S0 engine check against exp30\n  (another GPU) agrees on labels 15/16 on T2 and T03 and 40/40 on T10 and T05. So expect shares within sampling noise,\n  not identical token ids.\n\n**Resuming.** Every step resumes by row key, and the commit steps never rewrite an existing commit.\n\n## 5. What you should get\n\n| result | file | value |\n|---|---|---|\n| anchors | `results/anchors.json` | D1 (U_abs × S4) T10 α 2 attempted off-default 26/50 (exp29 25/50; per-slot agreement 0.98); D4 (U_bf × S5) correct off-default 1/50 (exp27 1/50) |\n| S1 decision | `results/s1_2x2.json` | UNIT. T10 α 2 shares D1 0.50, D2 0.52, D3 0.10, D4 0.02; unit RD +0.45 [0.35, 0.55]; seed +0.03 [−0.07, 0.14]; interaction −0.10 [−0.28, 0.08]. T2 α 2 (N 100): unit +0.115 [0.06, 0.17] |\n| D5 split | `results/s1_2x2.json` → `D5_split` | U_bf\\* 0.28; profile at matched energy +0.22 [0.08, 0.36]; energy at the ban-free shape +0.18 [0.06, 0.30] |\n| S2 | `results/s2_profile.json` | T10: P_top 29/50 vs P_rest 15/50 (McNemar 18:4, Holm p 0.009); D1 25/50 vs P_shuf 4/50 (21:0) → \"pushes act where bans write\" |\n| S3 | `results/s3_prices.json` | D\\* = D1. H5 PN\\* vs base intent: T03 3.22 vs 1.73 WIN, T10 2.13 vs 2.53 LOSS, T2 1.21 vs 1.45 LOSS, T05 1.10 vs 1.61 LOSS, T1 1.39 vs 1.05 WIN (2 of 5). Iteration 5's rule replayed: 2 of 5, DISCONFIRMED; D̄ = +0.12 [−0.18, 0.27] |\n| re-tag | `results/retag.json` | T03 and T10 movable at D\\*; T2, T05 and T1 not |\n| novelty | `results/novelty_audit.json` | 5 correct \"other\" programs, all catalogue variants; 0 novel |\n| E1 / E2 / E3 (exploratory) | `results/e1_sweep.json`, `e2_geometry.json`, `e3_replicate.json` | U_bf needs α ≈ 4 (20/50) to approach U_abs at α 2. Escape is near-independent across directions on one stream (φ 0.16–0.20). Fresh T10 slots: unit +0.42 [0.32, 0.52]. T03: unit +0.27 [0.18, 0.37] |\n| audits | `results/cpu_gates.json`, `unit_tests_gpu.json`, `rederive.json`, `commit_audit.json`, `commit_chain_verify.json` | all pass; the re-derivation has 0 mismatches and the placebos stay null |\n| per-slot outputs | `method_out.json` (+ `full_`/`mini_`/`preview_`) | `exp_gen_sol_out`, 6 datasets, 1,000 examples |\n\nFigures are in `figures/` (F1–F7, E1, E3); the README maps each one to its result. Monte-Carlo quantities (the hull\nH5, bootstraps and sign-flip p) are seeded and reproduce exactly on the same software stack.\n=====K_CFG\n     1\t#!/usr/bin/env python3\n     2\t\"\"\"Paths, constants and small utilities of iteration-7 step K (plan-noise unit x seeds crosswalk).\n     3\t\n     4\tThe vendored iteration-4 code lives in vendor/exp22 (its cfg.ROOT resolves there, so its inputs/, prompts/ and\n     5\tdirections/ resolve to the verified copies); vendor/exp28/src holds the iteration-5 T2 re-gate rule. This module\n     6\tAPPENDS those folders to sys.path (this artifact's own modules always win a name lookup); nothing in vendor/ is edited.\n     7\tThe exp27 code (vendor/exp27/src) has its own `cfg` module and therefore only ever runs in its own process\n     8\t(src/knobs_k.py).\n     9\t\n    10\tDesigns (S1): D1 = U_abs x S4, D2 = U_abs x S5, D3 = U_bf x S4, D4 = U_bf x S5, D5 = U_bf* x S4.\n    11\tProfiles (S2, S4 seeds): PTOP, PREST, PSHUF.  Arms are '<design>_a<alpha>' (e.g. 'D1_a2'); TWIN is the clean twin.\n    12\tRow keys: <task>|<template>|<arm>|<sample_id>.\n    13\t\"\"\"\n    14\t\n    15\tfrom __future__ import annotations\n    16\t\n    17\timport hashlib\n    18\timport json\n    19\timport math\n    20\timport os\n    21\timport sys\n    22\timport time\n    23\tfrom datetime import datetime, timezone\n    24\tfrom pathlib import Path\n    25\tfrom typing import Any, Iterable\n    26\t\n    27\tROOT = Path(__file__).resolve().parents[1]\n    28\tV22 = ROOT / \"vendor\" / \"exp22\"\n    29\tV28 = ROOT / \"vendor\" / \"exp28\"\n    30\tV27 = ROOT / \"vendor\" / \"exp27\"\n    31\t_SRC = Path(__file__).resolve().parent\n    32\tif str(_SRC) not in sys.path:\n    33\t    sys.path.insert(0, str(_SRC))\n    34\tfor _p in (V22 / \"src_base\", V22 / \"src\", V22 / \"analysis\", V28 / \"src\"):\n    35\t    if str(_p) not in sys.path:\n    36\t        sys.path.append(str(_p))\n    37\t\n    38\tINPUTS = ROOT / \"inputs\"\n    39\tE29 = INPUTS / \"exp29\"\n    40\tE27 = INPUTS / \"exp27\"\n    41\tE19 = INPUTS / \"exp19\"\n    42\tE23 = INPUTS / \"exp23\"\n    43\tE30 = INPUTS / \"exp30\"\n    44\tE22 = INPUTS / \"exp22\"\n    45\tDATA = ROOT / \"data\"\n    46\tRAW_DIR = DATA / \"raw\"\n    47\tRAW = RAW_DIR / \"raw_k.jsonl\"\n    48\tLABELS = DATA / \"labels.jsonl\"\n    49\tREALISED = DATA / \"realised_disp.jsonl\"\n    50\tRESULTS = ROOT / \"results\"\n    51\tFIGS = ROOT / \"figures\"\n    52\tPRED = ROOT / \"predictions\"\n    53\tLOGS = ROOT / \"logs\"\n    54\tCACHE = ROOT / \"cache\"\n    55\tAUDIT = ROOT / \"audit\"\n    56\tCOMMIT_LOG = ROOT / \"commitments.log\"\n    57\tfor _d in (DATA, RAW_DIR, RESULTS, FIGS, PRED, LOGS, CACHE, AUDIT):\n    58\t    _d.mkdir(parents=True, exist_ok=True)\n    59\t\n    60\tMODEL_ID = \"Qwen/Qwen3-8B\"\n    61\tMODEL_REVISION = \"b968826d9c46dd6066d109eabc6255188de91218\"\n    62\tBASE_MODEL_ID = \"Qwen/Qwen3-8B-Base\"\n    63\tBASE_REVISION = \"49e3418fbbbca6ecbdf9608b4d22e5a407081db4\"\n    64\tPRECISION = \"BF16 weights and activations (HF transformers 4.57.6, sdpa, torch 2.8.0+cu128); engine d of exp29\"\n    65\tTEMPLATES = (\"W1\", \"W2\", \"W3\", \"W4\", \"W5\")\n    66\tS1_TASKS = (\"T10\", \"T2\")\n    67\tD5_TASKS = (\"T03\", \"T10\", \"T2\", \"T05\", \"T1\")          # S3 decisive tasks (exp27 D5)\n    68\tEDIT_BLOCKS = list(range(12, 24))\n    69\tALL_BLOCKS = list(range(36))\n    70\tD_MODEL = 4096\n    71\tFENCE = {\"T10\": \"bench\", \"T03\": \"bench\", \"T05\": \"bench\", \"T2\": \"path\", \"T1\": \"path\"}\n    72\tMAX_NEW = {\"T10\": 1024, \"T03\": 1024, \"T05\": 1024, \"T2\": 1536, \"T1\": 1536}\n    73\tDEFAULTS = {\"T10\": \"union_find\", \"T2\": \"dijkstra\", \"T03\": \"full_sort\", \"T05\": \"hash_map\", \"T1\": \"bfs\"}\n    74\tDESIGNS = (\"D1\", \"D2\", \"D3\", \"D4\", \"D5\")\n    75\tPROFILES = (\"PTOP\", \"PREST\", \"PSHUF\")\n    76\tDESIGN_DEF = {\"D1\": (\"U_abs\", \"S4\"), \"D2\": (\"U_abs\", \"S5\"), \"D3\": (\"U_bf\", \"S4\"), \"D4\": (\"U_bf\", \"S5\"),\n    77\t              \"D5\": (\"U_bf_star\", \"S4\"), \"PTOP\": (\"P_top\", \"S4\"), \"PREST\": (\"P_rest\", \"S4\"),\n    78\t              \"PSHUF\": (\"P_shuf\", \"S4\")}\n    79\tK10 = list(range(10))\n    80\tK20 = list(range(20))\n    81\tBUDGET_MSG = \"AI Inventor per-run OpenRouter budget\"\n    82\tOPENROUTER_CAP_USD = 0.50\n    83\tGENESIS = hashlib.sha256(b\"iter7_K_genesis\").hexdigest()\n    84\tB_CANDIDATES = (12, 10, 8, 7, 6, 4)\n    85\t\n    86\t\n    87\tdef utc_now() -> str:\n    88\t    return datetime.now(timezone.utc).strftime(\"%Y-%m-%dT%H:%M:%S.%fZ\")\n    89\t\n    90\t\n    91\tdef sha256_text(s: str) -> str:\n    92\t    return hashlib.sha256(s.encode()).hexdigest()\n    93\t\n    94\t\n    95\tdef sha256_file(p: Path) -> str:\n    96\t    h = hashlib.sha256()\n    97\t    with open(p, \"rb\") as f:\n    98\t        for chunk in iter(lambda: f.read(1 << 20), b\"\"):\n    99\t            h.update(chunk)\n   100\t    return h.hexdigest()\n   101\t\n   102\t\n   103\tdef stable_seed(*parts: Any) -> int:\n   104\t    \"\"\"exp8/exp17/exp19 convention: sha256 of the '|'-joined str() of the parts, mod 2^63.\"\"\"\n   105\t    return int(hashlib.sha256(\"|\".join(str(p) for p in parts).encode()).hexdigest(), 16) % (2 ** 63)\n   106\t\n   107\t\n   108\tdef read_jsonl(p: Path) -> list[dict[str, Any]]:\n   109\t    p = Path(p)\n   110\t    if not p.exists():\n   111\t        return []\n   112\t    out = []\n   113\t    with open(p) as f:\n   114\t        for line in f:\n   115\t            line = line.strip()\n   116\t            if line:\n   117\t                try:\n   118\t                    out.append(json.loads(line))\n   119\t                except json.JSONDecodeError:\n   120\t                    continue   # a torn last line of a file still being appended\n   121\t    return out\n   122\t\n   123\t\n   124\tdef _json_default(o: Any) -> Any:\n   125\t    try:\n   126\t        import numpy as np\n   127\t        if isinstance(o, np.integer):\n   128\t            return int(o)\n   129\t        if isinstance(o, np.floating):\n   130\t            return float(o)\n   131\t        if isinstance(o, np.ndarray):\n   132\t            return o.tolist()\n   133\t        if isinstance(o, np.bool_):\n   134\t            return bool(o)\n   135\t    except ImportError:\n   136\t        pass\n   137\t    return str(o)\n   138\t\n   139\t\n   140\tdef append_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:\n   141\t    p = Path(p)\n   142\t    p.parent.mkdir(parents=True, exist_ok=True)\n   143\t    with open(p, \"a\") as f:\n   144\t        for r in rows:\n   145\t            f.write(json.dumps(r, default=_json_default) + \"\\n\")\n   146\t        f.flush()\n   147\t        os.fsync(f.fileno())\n   148\t\n   149\t\n   150\tdef write_json(p: Path, obj: Any) -> None:\n   151\t    p = Path(p)\n   152\t    p.parent.mkdir(parents=True, exist_ok=True)\n   153\t    tmp = p.with_suffix(p.suffix + \".tmp\")\n   154\t    tmp.write_text(json.dumps(obj, indent=1, default=_json_default))\n   155\t    tmp.replace(p)\n   156\t\n   157\t\n   158\tdef read_json(p: Path) -> Any:\n   159\t    return json.loads(Path(p).read_text())\n   160\t\n   161\t\n   162\tdef row_key(r: dict[str, Any]) -> str:\n   163\t    return f\"{r['task']}|{r['template']}|{r['arm']}|{r['sample_id']}\"\n   164\t\n   165\t\n   166\tdef parse_arm(arm: str) -> dict[str, Any]:\n   167\t    if arm == \"TWIN\":\n   168\t        return {\"family\": \"TWIN\", \"design\": \"TWIN\", \"alpha\": None}\n   169\t    d, a = arm.rsplit(\"_a\", 1)\n   170\t    unit, seeds = DESIGN_DEF[d]\n   171\t    return {\"family\": \"S2\" if d in PROFILES else \"S1\", \"design\": d, \"alpha\": float(a), \"unit\": unit, \"seeds\": seeds}\n   172\t\n   173\t\n   174\tdef s4_arm(alpha: float) -> str:\n   175\t    \"\"\"exp29/exp19 PN arm string used inside the S4 seed (asserted against logged seeds in gate G3).\"\"\"\n   176\t    return \"PN_a1\" if float(alpha) == 1.0 else \"PN_a2\"\n   177\t\n   178\t\n   179\tdef wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:\n   180\t    if n == 0:\n   181\t        return (float(\"nan\"), float(\"nan\"))\n   182\t    p = k / n\n   183\t    den = 1 + z * z / n\n   184\t    c = (p + z * z / (2 * n)) / den\n   185\t    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den\n   186\t    return (max(0.0, c - h), min(1.0, c + h))\n   187\t\n   188\t\n   189\tdef setup_logging(name: str) -> None:\n   190\t    from loguru import logger\n   191\t\n   192\t    logger.remove()\n   193\t    logger.add(sys.stdout, level=\"INFO\", format=\"{time:HH:mm:ss}|{level:<7}|{message}\")\n   194\t    logger.add(str(LOGS / f\"{name}.log\"), rotation=\"30 MB\", level=\"DEBUG\")\n   195\t\n   196\t\n   197\tdef add_deviation(code: str, text: str, consequence: str) -> None:\n   198\t    append_jsonl(RESULTS / \"deviations.jsonl\", [{\"code\": code, \"deviation\": text, \"consequence\": consequence,\n   199\t                                                 \"utc\": utc_now()}])\n   200\t\n   201\t\n   202\tclass Timer:\n   203\t    def __init__(self) -> None:\n   204\t        self.t0 = time.time()\n   205\t\n   206\t    def __call__(self) -> float:\n   207\t        return time.time() - self.t0", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
````

### [18] ASSISTANT · 2026-10-26 13:01:01 UTC

```
The README gives the full picture. The CPU-side analysis in `src/analysis_k.py` is the most portable part, so I'll read it next, along with `k_units.py`, which defines the dose units.
```

### [19] TOOL CALL — Bash · 2026-10-26 13:01:01 UTC

```
Read the main analysis module:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36; cat -n $A/src/analysis_k.py
```

### [20] TOOL RESULT — Bash · 2026-10-26 13:01:01 UTC

```
{"stdout": "     1\t#!/usr/bin/env python3\n     2\t\"\"\"S1 / S2 analysis of step K (hashed in COMMIT #1 before the first S1/S2 sample): anchors, the unit x seeds 2x2\n     3\t(+ U_bf*), the profile split, descriptive mediation and the D* rule of COMMIT #2.\n     4\t\n     5\tOutcomes per program (labels: data/labels.jsonl, one labeller version for every row):\n     6\t  Y      (primary)  passed AND label in the task catalogue minus the default (correct named off-default algo... [truncated, 32413 chars total]
```

### [21] TOOL CALL — Bash · 2026-10-26 13:01:01 UTC

```
Read the dose units module:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36; cat -n $A/src/k_units.py
```

### [22] TOOL RESULT — Bash · 2026-10-26 13:01:01 UTC

```
{"stdout": "     1\t#!/usr/bin/env python3\n     2\t\"\"\"Dose units, direction seeds and profile masks of step K (CPU parts; the twin-norm unit U_bf needs the twin states\n     3\tand is finished on the GPU by gen_k.TaskCtxK.unit()).\n     4\t\n     5\t  U_abs[task]      exp19 load_norms(task, 'stage1') = the ban's own per-block, per-position displacement norm n[l, p]:\n     6\t                   exp13 norms_<task>.npz['norm'] (T10, T03, T05) or exp17 norms_<task>.npy (T1, T2); [12, |S|].\n     7\t  U_bf[task, w]    ||h_twin_w[l, p]||_2 * r_Q(l), r_Q(l) = interp((l + 1) / 36, depth, median) over exp23\n     8\t                   qwen_ratio.json['r_Q'] (exp27 gen5.r_at / Ctx.banfree, verbatim arithmetic).\n     9\t  U_bf*[task, w]   U_bf[l, :] * ||U_abs[l, :]||_2 / ||U_bf[l, :]||_2 (U_abs's per-block energy, U_bf's profile).\n    10\t  P_top / P_rest   U_abs restricted to its top-quartile cells (n >= 75th percentile of the 12 x |S| grid) / to the\n    11\t                   other cells, each rescaled to U_abs's Frobenius norm; masked cells are NOT edited.\n    12\t  P_shuf           U_abs with spec positions permuted by one permutation shared by all blocks\n    13\t                   (PCG64(stable_seed(task, 'SHUF'))); every cell edited.\n    14\t  S4 seeds         PCG64(stable_seed(task, 'PN_a<alpha>', w, k)).standard_normal(4096), normalised (exp29 gen.pn_direction).\n    15\t  S5 seeds         PCG64(stable_seed(task, 'PN5', w, k)).standard_normal(4096), normalised (exp27 gen5.pn5_direction).\n    16\t\"\"\"\n    17\t\n    18\tfrom __future__ import annotations\n    19\t\n    20\timport numpy as np\n    21\t\n    22\tfrom k_cfg import D_MODEL, E23, V22, read_json, s4_arm, stable_seed\n    23\t\n    24\tE13V = V22 / \"inputs\" / \"exp13\"\n    25\tE17V = V22 / \"inputs\" / \"exp17\"\n    26\tPATH_TASKS = (\"T1\", \"T2\")\n    27\t\n    28\t\n    29\tdef u_abs(task: str) -> np.ndarray:\n    30\t    \"\"\"exp22 ctx4.ban_unit(task) (== exp19 load_norms(task, 'stage1')): float32 [12, |S|].\"\"\"\n    31\t    if task in PATH_TASKS:\n    32\t        return np.load(E17V / \"directions\" / f\"norms_{task}.npy\").astype(np.float32)\n    33\t    return np.load(E13V / \"results\" / \"tensors\" / f\"norms_{task}.npz\")[\"norm\"].astype(np.float32)\n    34\t\n    35\t\n    36\tdef r_q_table() -> tuple[np.ndarray, np.ndarray]:\n    37\t    q = read_json(E23 / \"results\" / \"qwen_ratio.json\")[\"r_Q\"]\n    38\t    d = np.array([v[\"depth\"] for v in q.values()])\n    39\t    r = np.array([v[\"median\"] for v in q.values()])\n    40\t    o = np.argsort(d)\n    41\t    return d[o], r[o]\n    42\t\n    43\t\n    44\t_RQ: tuple[np.ndarray, np.ndarray] | None = None\n    45\t\n    46\t\n    47\tdef r_at(l: int) -> float:\n    48\t    \"\"\"exp27 gen5.r_at, verbatim.\"\"\"\n    49\t    global _RQ\n    50\t    if _RQ is None:\n    51\t        _RQ = r_q_table()\n    52\t    return float(np.interp((l + 1) / 36, _RQ[0], _RQ[1]))\n    53\t\n    54\t\n    55\tdef s4_direction(task: str, alpha: float, w: str, k: int) -> tuple[int, np.ndarray]:\n    56\t    \"\"\"exp29 gen.pn_direction(task, arm, w, k) with arm = 'PN_a1' / 'PN_a2', verbatim arithmetic.\"\"\"\n    57\t    seed = stable_seed(task, s4_arm(alpha), w, k)\n    58\t    x = np.random.Generator(np.random.PCG64(seed)).standard_normal(4096)\n    59\t    return seed, (x / np.linalg.norm(x)).astype(np.float32)\n    60\t\n    61\t\n    62\tdef s5_direction(task: str, w: str, k: int, tag: str = \"PN5\") -> tuple[int, np.ndarray]:\n    63\t    \"\"\"exp27 gen5.pn5_direction, verbatim arithmetic (same u at alpha 1 and 2).\"\"\"\n    64\t    seed = stable_seed(task, tag, w, k)\n    65\t    x = np.random.Generator(np.random.PCG64(seed)).standard_normal(D_MODEL)\n    66\t    return seed, (x / np.linalg.norm(x)).astype(np.float32)\n    67\t\n    68\t\n    69\tdef direction(seeds: str, task: str, alpha: float, w: str, k: int) -> tuple[int, np.ndarray]:\n    70\t    return s4_direction(task, alpha, w, k) if seeds == \"S4\" else s5_direction(task, w, k)\n    71\t\n    72\t\n    73\tdef profile_masks(n: np.ndarray, task: str) -> dict[str, dict[str, np.ndarray]]:\n    74\t    \"\"\"S2 profiles of U_abs: unit [12, |S|] float32 and edit mask [12, |S|] bool for P_top, P_rest, P_shuf.\"\"\"\n    75\t    n = n.astype(np.float64)\n    76\t    q75 = float(np.percentile(n, 75))\n    77\t    top = n >= q75\n    78\t    rest = ~top\n    79\t    fro = float(np.linalg.norm(n))\n    80\t    out = {}\n    81\t    for name, m in ((\"P_top\", top), (\"P_rest\", rest)):\n    82\t        part = n * m\n    83\t        scale = fro / float(np.linalg.norm(part))\n    84\t        out[name] = {\"unit\": (part * scale).astype(np.float32), \"mask\": m.copy(), \"scale\": scale,\n    85\t                     \"energy_share\": float((part ** 2).sum() / (n ** 2).sum()), \"q75\": q75}\n    86\t    perm = np.random.Generator(np.random.PCG64(stable_seed(task, \"SHUF\"))).permutation(n.shape[1])\n    87\t    out[\"P_shuf\"] = {\"unit\": n[:, perm].astype(np.float32), \"mask\": np.ones_like(top), \"perm\": perm.tolist(),\n    88\t                     \"scale\": 1.0, \"energy_share\": 1.0, \"q75\": q75}\n    89\t    return out\n    90\t\n    91\t\n    92\tdef bf_star(u_bf: np.ndarray, n_abs: np.ndarray) -> np.ndarray:\n    93\t    \"\"\"U_bf*[l, :] = U_bf[l, :] * ||U_abs[l, :]|| / ||U_bf[l, :]|| (float64 arithmetic, float32 result).\"\"\"\n    94\t    ub = u_bf.astype(np.float64)\n    95\t    na = n_abs.astype(np.float64)\n    96\t    s = np.linalg.norm(na, axis=1) / np.linalg.norm(ub, axis=1)\n    97\t    return (ub * s[:, None]).astype(np.float32)\n    98\t\n    99\t\n   100\tdef dose_ratios(unit: np.ndarray, ref: np.ndarray) -> dict[str, float]:\n   101\t    \"\"\"Dose of a unit relative to D1's U_abs: mean of per-cell ratios, ratio of Frobenius norms, block-12 means.\"\"\"\n   102\t    u = unit.astype(np.float64)\n   103\t    r = ref.astype(np.float64)\n   104\t    return {\"mean_cell_ratio\": float((u / np.maximum(r, 1e-6)).mean()),\n   105\t            \"fro_ratio\": float(np.linalg.norm(u) / np.linalg.norm(r)),\n   106\t            \"b12_mean_ratio\": float(u[0].mean() / r[0].mean())}", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [23] TOOL CALL — Read · 2026-10-26 13:01:05 UTC

```
/var/lib/aii-agent/claude/projects/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-7-art-8O5eaNc5gxJs/af59f795-b06d-4e3e-8812-aa2d20336c88/tool-results/bwj6ipcht.txt
```

### [24] TOOL RESULT — Read · 2026-10-26 13:01:05 UTC

```
{"type": "text", "file": {"filePath": "/var/lib/aii-agent/claude/projects/-ai-inventor-aii-data-runs-run-jSassd-YWLVC-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-7-art-8O5eaNc5gxJs/af59f795-b06d-4e3e-8812-aa2d20336c88/tool-results/bwj6ipcht.txt", "content": "     1\t#!/usr/bin/env python3\n     2\t\"\"\"S1 / S2 analysis of step K (hashed in COMMIT #1 before the first S1/S2 sample): anchors, the unit x seeds 2x2\n     3\t(+ U_bf*), the profile split, descriptive m... [truncated, 32710 chars total]
```

### [25] ASSISTANT · 2026-10-26 13:01:19 UTC

```
`analysis_k.py` is self-contained CPU statistics over joined rows (label, passed, valid, per arm and slot). Now I'll look at the output data structure through the preview file, as TODO 2 asks.
```

### [26] TOOL CALL — Bash · 2026-10-26 13:01:19 UTC

```
Inspect preview output JSON structure:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36; head -c 6000 $A/preview_method_out.json; echo; echo "....."; python3 -c "
import json
d=json.load(open('$A/preview_method_out.json'))
print(type(d), list(d.keys()) if isinstance(d,dict) else len(d))
for k,v in d.items():
    if k!='datasets': print(k, str(v)[:1500])
ds=d['datasets']
print('n datasets', len(ds))
for x in ds:
    print('DATASET', x['dataset'], 'n ex', len(x['examples']))
    ex=x['examples'][0]
    print(' keys:', list(ex.keys()))
"
```

### [27] TOOL RESULT — Bash · 2026-10-26 13:01:19 UTC

```
{"stdout": "{\n  \"metadata\": {\n    \"method_name\": \"Plan-noise crosswalk: dose unit x direction seeds, profile split and prices at D* (step K)\",\n    \"description\": \"Qwen/Qwen3-8B b968826d, bf16 HF transformers 4.57.6 (exp29 engine d numerics), thinking off. Per-sample isotropic random direction u at the task-spec positions of blocks 12-23, prefill only, displacem...\",\n    \"model\": \"Qwen/Qwen3-8B\",\n    \"model_revision\": \"b968826d9c46dd6066d109eabc6255188de91218\",\n    \"precision\": \"BF16 weights and activations (HF transformers 4.57.6, sdpa, torch 2.8.0+cu128); engine d of exp29\",\n    \"prediction_format\": \"'<label>|<passed>' per arm; output = the clean twin's own label|passed on the slot\",\n    \"anchors\": {\n      \"A1\": {\n        \"attempted_off_default\": 26,\n        \"N\": 50,\n        \"exp29\": \"25/50\",\n        \"fisher_p\": 1.0,\n        \"pass_rate\": 0.98,\n        \"pass\": true,\n        \"correct_off_default_Y_any\": 25\n      },\n      \"A2\": {\n        \"correct_off_default\": 1,\n        \"N\": 50,\n        \"exp27\": \"1/50\",\n        \"fisher_p\": 1.0,\n        \"attempted\": 1,\n        \"pass_rate\": 1.0,\n        \"pass\": true\n      },\n      \"A3\": {\n        \"attempted_off_default\": 24,\n        \"N\": 50,\n        \"correct_off_default\": 8,\n        \"pass_rate\": 0.62,\n        \"exp29\": \"22/50 attempts, pass 0.62, 9/50 correct\",\n        \"fisher_p_attempts\": 0.8411162923429207,\n        \"per_slot_label_agreement_vs_exp29\": 0.88,\n        \"n_paired\": 50\n      },\n      \"D1_T10_per_slot_agreement_vs_exp29\": {\n        \"agreement\": 0.98,\n        \"n\": 50\n      },\n      \"both_pass\": true\n    },\n    \"s1_2x2\": {\n      \"cells\": {\n        \"T10|TWIN\": {\n          \"N\": 50,\n          \"Y\": {\n            \"k\": 0,\n            \"n\": 50,\n            \"share\": 0.0,\n            \"wilson95\": [\n              6.938893903907228e-18,\n              0.07134759913335872\n            ]\n          },\n          \"Y_any\": {\n            \"k\": 0,\n            \"n\": 50,\n            \"share\": 0.0,\n            \"wilson95\": [\n              6.938893903907228e-18,\n              0.07134759913335872\n            ]\n          },\n          \"A\": {\n            \"k\": 0,\n            \"n\": 50,\n            \"share\": 0.0,\n            \"wilson95\": [\n              6.938893903907228e-18,\n              0.07134759913335872\n            ]\n          },\n          \"pass_rate\": 1.0,\n          \"disputed\": 0,\n          \"composition\": {\n            \"union_find\": 50\n          },\n          \"composition_correct\": {\n            \"union_find\": 50\n          },\n          \"length_finish\": 0\n        },\n        \"T10|D1_a1\": {\n          \"N\": 50,\n          \"Y\": {\n            \"k\": 6,\n            \"n\": 50,\n            \"share\": 0.12,\n            \"wilson95\": [\n              0.05617600150932274,\n              0.23804817383202992\n            ]\n          },\n          \"Y_any\": {\n            \"k\": 6,\n            \"n\": 50,\n            \"share\": 0.12,\n            \"wilson95\": [\n              0.05617600150932274,\n              0.23804817383202992\n            ]\n          },\n          \"A\": {\n            \"k\": 6,\n            \"n\": 50,\n            \"share\": 0.12,\n            \"wilson95\": [\n              0.05617600150932274,\n              0.23804817383202992\n            ]\n          },\n          \"pass_rate\": 1.0,\n          \"disputed\": 0,\n          \"composition\": {\n            \"union_find\": 44,\n            \"dfs\": 6\n          },\n          \"composition_correct\": {\n            \"union_find\": 44,\n            \"dfs\": 6\n          },\n          \"length_finish\": 0\n        },\n        \"T10|D2_a1\": {\n          \"N\": 50,\n          \"Y\": {\n            \"k\": 7,\n            \"n\": 50,\n            \"share\": 0.14,\n            \"wilson95\": [\n              0.06950833427016294,\n              0.2618619371058554\n            ]\n          },\n          \"Y_any\": {\n            \"k\": 7,\n            \"n\": 50,\n            \"share\": 0.14,\n            \"wilson95\": [\n              0.06950833427016294,\n              0.2618619371058554\n            ]\n          },\n          \"A\": {\n            \"k\": 7,\n            \"n\": 50,\n            \"share\": 0.14,\n            \"wilson95\": [\n              0.06950833427016294,\n              0.2618619371058554\n            ]\n          },\n          \"pass_rate\": 1.0,\n          \"disputed\": 0,\n          \"composition\": {\n            \"dfs\": 7,\n            \"union_find\": 43\n          },\n          \"composition_correct\": {\n            \"dfs\": 7,\n            \"union_find\": 43\n          },\n          \"length_finish\": 0\n        },\n        \"T10|D3_a1\": {\n          \"N\": 50,\n          \"Y\": {\n            \"k\": 0,\n            \"n\": 50,\n            \"share\": 0.0,\n            \"wilson95\": [\n              6.938893903907228e-18,\n              0.07134759913335872\n            ]\n          },\n          \"Y_any\": {\n            \"k\": 0,\n            \"n\": 50,\n            \"share\": 0.0,\n            \"wilson95\": [\n              6.938893903907228e-18,\n              0.07134759913335872\n            ]\n          },\n          \"A\": {\n            \"k\": 0,\n            \"n\": 50,\n            \"share\": 0.0,\n            \"wilson95\": [\n              6.938893903907228e-18,\n              0.07134759913335872\n            ]\n          },\n          \"pass_rate\": 1.0,\n          \"disputed\": 0,\n          \"composition\": {\n            \"union_find\": 50\n          },\n          \"composition_correct\": {\n            \"union_find\": 50\n          },\n          \"length_finish\": 0\n        },\n        \"T10|D4_a1\": {\n          \"N\": 50,\n          \"Y\": {\n            \"k\": 1,\n            \"n\": 50,\n            \"share\": 0.02,\n            \"wilson95\": [\n              0.003539259271646236,\n              0.10495443589637815\n            ]\n          },\n          \"Y_any\": {\n            \"k\": 1,\n            \"n\": 50,\n            \"share\": 0.02,\n            \"wilson95\": [\n              0.003539259271646236,\n              0.10495443589637815\n            ]\n          },\n          \"A\": {\n            \"k\": 1,\n            \"n\": 50,\n            \"share\": 0.02,\n            \"wilson95\": [\n              0.003539259271646236,\n              0.10495443589637815\n            ]\n          },\n          \"pass_rate\":\n.....\n<class 'dict'> ['metadata', 'datasets']\nmetadata {'method_name': 'Plan-noise crosswalk: dose unit x direction seeds, profile split and prices at D* (step K)', 'description': 'Qwen/Qwen3-8B b968826d, bf16 HF transformers 4.57.6 (exp29 engine d numerics), thinking off. Per-sample isotropic random direction u at the task-spec positions of blocks 12-23, prefill only, displacem...', 'model': 'Qwen/Qwen3-8B', 'model_revision': 'b968826d9c46dd6066d109eabc6255188de91218', 'precision': 'BF16 weights and activations (HF transformers 4.57.6, sdpa, torch 2.8.0+cu128); engine d of exp29', 'prediction_format': \"'<label>|<passed>' per arm; output = the clean twin's own label|passed on the slot\", 'anchors': {'A1': {'attempted_off_default': 26, 'N': 50, 'exp29': '25/50', 'fisher_p': 1.0, 'pass_rate': 0.98, 'pass': True, 'correct_off_default_Y_any': 25}, 'A2': {'correct_off_default': 1, 'N': 50, 'exp27': '1/50', 'fisher_p': 1.0, 'attempted': 1, 'pass_rate': 1.0, 'pass': True}, 'A3': {'attempted_off_default': 24, 'N': 50, 'correct_off_default': 8, 'pass_rate': 0.62, 'exp29': '22/50 attempts, pass 0.62, 9/50 correct', 'fisher_p_attempts': 0.8411162923429207, 'per_slot_label_agreement_vs_exp29': 0.88, 'n_paired': 50}, 'D1_T10_per_slot_agreement_vs_exp29': {'agreement': 0.98, 'n': 50}, 'both_pass': True}, 's1_2x2': {'cells': {'T10|TWIN': {'N': 50, 'Y': {'k': 0, 'n': 50, 'share': 0.0, 'wilson95': [6.938893903907228e-18, 0.07134759913335872]}, 'Y_any': {'k': 0, 'n': 50, 'share': 0.0, 'wilson95': [6.938893903907228e-18, 0.07134759913335872]}, 'A': \nn datasets 3\nDATASET k_2x2 n ex 3\n keys: ['input', 'output', 'predict_D1', 'predict_D2', 'predict_D3', 'predict_D4', 'metadata_task', 'metadata_template', 'metadata_k', 'metadata_uniform_seed', 'metadata_alpha', 'metadata_family', 'metadata_designs']\nDATASET k_profile n ex 3\n keys: ['input', 'output', 'predict_D1', 'predict_PTOP', 'predict_PREST', 'predict_PSHUF', 'metadata_task', 'metadata_template', 'metadata_k', 'metadata_uniform_seed', 'metadata_alpha', 'metadata_family']\nDATASET k_prices n ex 3\n keys: ['input', 'output', 'predict_PNstar_a1', 'predict_PNstar_a2', 'predict_BINT', 'predict_EAP', 'predict_IFG_hot', 'predict_T1_3', 'predict_TOPK10', 'metadata_task', 'metadata_template', 'metadata_k', 'metadata_uniform_seed', 'metadata_family', 'metadata_D_star', 'metadata_knob_row_sources']", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [28] THINKING · 2026-10-26 13:01:47 UTC

```
The output lacks the `valid` field needed for attempt outcome A, so `data/samples.jsonl` is likely the better data source. I'll now look at the GPU runner and exploratory modules to understand the edit itself.
```

### [29] TOOL CALL — Bash · 2026-10-26 13:01:47 UTC

```
Read first part of the GPU runner:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36; cat -n $A/src/gen_k.py | head -400
```

### [30] TOOL RESULT — Bash · 2026-10-26 13:01:47 UTC

```
{"stdout": "     1\t#!/usr/bin/env python3\n     2\t\"\"\"GPU process of step K (instruct model, bf16): hardware record, memory probe, unit tests U1-U6, S0 twins, S1 2x2\n     3\t(+ D5), S2 profiles and S3's plan-noise cells at D*. Resumable by row key <task>|<template>|<arm>|<sample_id>.\n     4\t\n     5\tEngine and sampler are the vendored exp22 ones run in bf16 (= exp29 engine d numerics): engine.load_model(fp8=False),\n     6\tengine.prefill with block-output edit hooks, ... [truncated, 24890 chars total]
```

### [31] TOOL CALL — Bash · 2026-10-26 13:01:47 UTC

```
Read exploratory E1/E3 and unit dump modules:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36; for f in e1_sweep.py e3_replicate.py extensions_k.py dump_units.py; do echo "=================== $f"; cat -n $A/src/$f; done
```

### [32] TOOL RESULT — Bash · 2026-10-26 13:01:47 UTC

```
{"stdout": "=================== e1_sweep.py\n     1\t#!/usr/bin/env python3\n     2\t\"\"\"E1 (exploratory, NOT pre-registered; run after COMMIT #2): dose sweep of the ban-free unit. D3 (U_bf x S4) at\n     3\talpha 3, 4 and 6 on T10 and T2 (W1-W5 x k 0-9), same runner, same slots, uniforms and per-slot directions as the S1\n     4\tcells (the S4 seed of a slot at alpha >= 2 is its alpha-2 seed, so only the dose changes). Question: does the ban-free\n     5\tprofile reach U_abs's escape share once its realised downstream displacement matches, and at what pass cost?\n     6\t\n     7\tusage: .venv/bin/python src/e1_sweep.py\n     8\t\"\"\"\n     9\t\n    10\tfrom __future__ import annotations\n    11\t\n    12\timport sys\n    13\tfrom pathlib import Path\n    14\t\n    15\tfrom loguru import logger\n    16\t\n    17\tsys.path.insert(0, str(Path(__file__).resolve().parent))\n    18\t\n    19\timport k_cfg as K  # noqa: E402\n    20\timport gen_k as G  # noqa: E402\n    21\t\n    22\t\n    23\t@logger.catch(reraise=True)\n    24\tdef main() -> None:\n    25\t    K.setup_logging(\"e1_sweep\")\n    26\t    tok, model = G.load_model(fp8=False, vram_fraction=0.97)\n    27\t    prompts = G.load_prompts()\n    28\t    B = K.read_json(G.STATE)[\"B\"]\n    29\t    run = G.RunnerK(model, tok, prompts, B)\n    30\t    for t in (\"T10\", \"T2\"):\n    31\t        run.run_cells(t, [(\"D3_a3\", K.K10), (\"D3_a4\", K.K10), (\"D3_a6\", K.K10)], \"E1_sweep\")\n    32\t    K.write_json(K.RESULTS / \"e1_done.json\", {\"utc\": K.utc_now()})\n    33\t\n    34\t\n    35\tif __name__ == \"__main__\":\n    36\t    main()\n=================== e3_replicate.py\n     1\t#!/usr/bin/env python3\n     2\t\"\"\"E3 (exploratory, NOT pre-registered; hash-committed before its first row): an internal replication and a\n     3\tgenerality check of the S1/S2 answers with spare GPU time.\n     4\t\n     5\t  (a) fresh slots: T10 alpha 2, k 10-19 x W1-W5 (N 50 slots never used by S1/S2) for D1-D5 and P_top/P_rest/P_shuf;\n     6\t  (b) third task: T03 alpha 2, k 0-9, D2/D3/D4 (D1_a2 already exists from S3), completing a T03 2x2.\n     7\tSame runner, uniforms and seeds as S1 (S4/S5 directions of each slot).\n     8\t\n     9\tusage: .venv/bin/python src/e3_replicate.py\n    10\t\"\"\"\n    11\t\n    12\tfrom __future__ import annotations\n    13\t\n    14\timport sys\n    15\tfrom pathlib import Path\n    16\t\n    17\tfrom loguru import logger\n    18\t\n    19\tsys.path.insert(0, str(Path(__file__).resolve().parent))\n    20\t\n    21\timport k_cfg as K  # noqa: E402\n    22\timport gen_k as G  # noqa: E402\n    23\t\n    24\tK_FRESH = list(range(10, 20))\n    25\t\n    26\t\n    27\t@logger.catch(reraise=True)\n    28\tdef main() -> None:\n    29\t    K.setup_logging(\"e3_replicate\")\n    30\t    tok, model = G.load_model(fp8=False, vram_fraction=0.97)\n    31\t    prompts = G.load_prompts()\n    32\t    B = K.read_json(G.STATE)[\"B\"]\n    33\t    run = G.RunnerK(model, tok, prompts, B)\n    34\t    run.run_cells(\"T10\", [(\"TWIN\", K_FRESH), (\"D1_a2\", K_FRESH), (\"D2_a2\", K_FRESH), (\"D3_a2\", K_FRESH),\n    35\t                          (\"D4_a2\", K_FRESH), (\"D5_a2\", K_FRESH), (\"PTOP_a2\", K_FRESH), (\"PREST_a2\", K_FRESH),\n    36\t                          (\"PSHUF_a2\", K_FRESH)], \"E3_fresh\")\n    37\t    run.run_cells(\"T03\", [(\"D2_a2\", K.K10), (\"D3_a2\", K.K10), (\"D4_a2\", K.K10)], \"E3_T03\")\n    38\t    K.write_json(K.RESULTS / \"e3_done.json\", {\"utc\": K.utc_now()})\n    39\t\n    40\t\n    41\tif __name__ == \"__main__\":\n    42\t    main()\n=================== extensions_k.py\n     1\t#!/usr/bin/env python3\n     2\t\"\"\"E3 analysis (exploratory): the S1 2x2 and the S2 profile tests re-run with the committed analysis functions on\n     3\t(a) T10 fresh slots k 10-19 (an internal replication on 50 slots never used by S1/S2), (b) T10 pooled k 0-19 (N 100),\n     4\tand (c) the T03 2x2 at alpha 2 (k 0-9; D1_a2 from S3). Writes results/e3_replicate.json.\n     5\t\n     6\tusage: .venv/bin/python src/extensions_k.py\n     7\t\"\"\"\n     8\t\n     9\tfrom __future__ import annotations\n    10\t\n    11\timport sys\n    12\tfrom pathlib import Path\n    13\tfrom typing import Any\n    14\t\n    15\tfrom loguru import logger\n    16\t\n    17\tsys.path.insert(0, str(Path(__file__).resolve().parent))\n    18\t\n    19\timport k_cfg as K  # noqa: E402\n    20\timport analysis_k as A  # noqa: E402\n    21\t\n    22\tK_FRESH = list(range(10, 20))\n    23\tK_ALL = list(range(20))\n    24\t\n    25\t\n    26\tdef profile_tests(rows: list[dict[str, Any]], task: str, ks: list[int]) -> dict[str, Any]:\n    27\t    arms = {\"D1\": \"D1_a2\", \"PTOP\": \"PTOP_a2\", \"PREST\": \"PREST_a2\", \"PSHUF\": \"PSHUF_a2\", \"D5\": \"D5_a2\"}\n    28\t    cells = {k: A.cell(rows, task, a, ks) for k, a in arms.items()}\n    29\t    out: dict[str, Any] = {\"cells\": {k: A.describe(c) for k, c in cells.items() if c}}\n    30\t    for name, (x, y) in {\"PTOP_vs_PREST\": (\"PTOP\", \"PREST\"), \"D1_vs_PSHUF\": (\"D1\", \"PSHUF\"),\n    31\t                         \"D1_vs_PTOP\": (\"D1\", \"PTOP\")}.items():\n    32\t        cx, cy = cells[x], cells[y]\n    33\t        common = sorted(set(cx) & set(cy))\n    34\t        if len(common) >= 10:\n    35\t            t = A.mcnemar_exact([cx[s][\"Y\"] for s in common], [cy[s][\"Y\"] for s in common])\n    36\t            t.update({\"n\": len(common), \"share_x\": sum(cx[s][\"Y\"] for s in common) / len(common),\n    37\t                      \"share_y\": sum(cy[s][\"Y\"] for s in common) / len(common)})\n    38\t            out[name] = t\n    39\t    return out\n    40\t\n    41\t\n    42\t@logger.catch(reraise=True)\n    43\tdef main() -> None:\n    44\t    K.setup_logging(\"extensions_k\")\n    45\t    rows = A.load_joined()\n    46\t    res: dict[str, Any] = {\"note\": \"exploratory (E3), not pre-registered; committed before its first row\"}\n    47\t    for label, task, ks in ((\"T10_fresh_k10_19\", \"T10\", K_FRESH), (\"T10_pooled_k0_19\", \"T10\", K_ALL),\n    48\t                            (\"T03_k0_9\", \"T03\", K.K10)):\n    49\t        r: dict[str, Any] = {}\n    50\t        for key in (\"Y\", \"A\"):\n    51\t            r[f\"2x2|{key}\"] = A.s1_table(rows, task, 2.0, key, ks)\n    52\t            r[f\"2x2|{key}\"][\"decision_rule_applied\"] = A.decision(r[f\"2x2|{key}\"])\n    53\t        r[\"twin\"] = A.describe(A.cell(rows, task, \"TWIN\", ks))\n    54\t        if task == \"T10\":\n    55\t            r[\"profiles\"] = profile_tests(rows, task, ks)\n    56\t        else:\n    57\t            r[\"cells\"] = {d: A.describe(A.cell(rows, task, f\"{d}_a2\", ks)) for d in (\"D1\", \"D2\", \"D3\", \"D4\")}\n    58\t        res[label] = r\n    59\t    K.write_json(K.RESULTS / \"e3_replicate.json\", res)\n    60\t    for label in (\"T10_fresh_k10_19\", \"T10_pooled_k0_19\", \"T03_k0_9\"):\n    61\t        t = res[label][\"2x2|Y\"]\n    62\t        if not t.get(\"incomplete\"):\n    63\t            logger.info(f\"{label}: shares {t['shares']} RD_unit {t['RD_unit']:.3f} {t['RD_unit_ci95']} RD_seed \"\n    64\t                        f\"{t['RD_seed']:.3f} {t['RD_seed_ci95']} INT {t['RD_int']:.3f} -> {t['decision_rule_applied']}\")\n    65\t\n    66\t\n    67\tif __name__ == \"__main__\":\n    68\t    main()\n=================== dump_units.py\n     1\t#!/usr/bin/env python3\n     2\t\"\"\"Dump every dose unit in activation coordinates (GPU, instruct model, bf16; one twin prefill per template):\n     3\tU_abs, U_bf, U_bf*, P_top, P_rest, P_shuf, the twin's per-cell residual norm ||h_twin[l, p]|| and the spec tokens,\n     4\tfor T10, T2, T03, T05, T1 x W1-W5 -> cache/units/<task>.npz and results/unit_profiles.json (per-block energies,\n     5\tratio of mean norms and mean per-position ratio of U_bf / U_abs: the confound the U_bf* arm splits).\n     6\t\n     7\tusage: .venv/bin/python src/dump_units.py\n     8\t\"\"\"\n     9\t\n    10\tfrom __future__ import annotations\n    11\t\n    12\timport sys\n    13\tfrom pathlib import Path\n    14\t\n    15\timport numpy as np\n    16\tfrom loguru import logger\n    17\t\n    18\tsys.path.insert(0, str(Path(__file__).resolve().parent))\n    19\t\n    20\timport k_cfg as K  # noqa: E402\n    21\timport gen_k as G  # noqa: E402\n    22\t\n    23\t\n    24\t@logger.catch(reraise=True)\n    25\tdef main() -> None:\n    26\t    K.setup_logging(\"dump_units\")\n    27\t    tok, model = G.load_model(fp8=False, vram_fraction=0.97)\n    28\t    prompts = G.load_prompts()\n    29\t    out_dir = K.CACHE / \"units\"\n    30\t    out_dir.mkdir(parents=True, exist_ok=True)\n    31\t    summary = {}\n    32\t    for task in K.D5_TASKS:\n    33\t        ctx = G.TaskCtxK(model, prompts, task)\n    34\t        arrs: dict[str, np.ndarray] = {\"U_abs\": ctx.n_abs}\n    35\t        for name in (\"P_top\", \"P_rest\", \"P_shuf\"):\n    36\t            arrs[name] = ctx.profiles[name][\"unit\"]\n    37\t        arrs[\"mask_top\"] = ctx.profiles[\"P_top\"][\"mask\"]\n    38\t        rec = {}\n    39\t        for w in K.TEMPLATES:\n    40\t            tw = ctx.twin(w)\n    41\t            arrs[f\"U_bf_{w}\"] = tw[\"U_bf\"]\n    42\t            arrs[f\"U_bf_star_{w}\"] = tw[\"U_bf_star\"]\n    43\t            arrs[f\"h_norm_{w}\"] = tw[\"h_norm\"]\n    44\t            p = tw[\"prompt\"]\n    45\t            toks = [tok.decode([i]) for i in p[\"ids\"][p[\"p1\"]:p[\"spec_end\"]]]\n    46\t            arrs[f\"tokens_{w}\"] = np.array(toks, dtype=object)\n    47\t            ub, ua = tw[\"U_bf\"].astype(np.float64), ctx.n_abs.astype(np.float64)\n    48\t            rec[w] = {\"ratio_of_mean_norms_per_block\": (ub.mean(1) / ua.mean(1)).round(4).tolist(),\n    49\t                      \"mean_per_position_ratio_per_block\": (ub / ua).mean(1).round(4).tolist(),\n    50\t                      \"fro_ratio_per_block\": (np.linalg.norm(ub, axis=1) / np.linalg.norm(ua, axis=1)).round(4).tolist(),\n    51\t                      \"fro_ratio_total\": float(np.linalg.norm(ub) / np.linalg.norm(ua)),\n    52\t                      \"U_abs_over_hnorm_max\": float((ua / tw[\"h_norm\"]).max()),\n    53\t                      \"U_bf_over_hnorm_max\": float((ub / tw[\"h_norm\"]).max()),\n    54\t                      \"top_quartile_energy_share_U_abs\": float(ctx.profiles[\"P_top\"][\"energy_share\"]),\n    55\t                      \"top_quartile_energy_share_U_bf\": float(((ub * ctx.profiles[\"P_top\"][\"mask\"]) ** 2).sum()\n    56\t                                                              / (ub ** 2).sum())}\n    57\t            ctx.release()\n    58\t        np.savez_compressed(out_dir / f\"{task}.npz\", **{k: v for k, v in arrs.items() if v.dtype != object},\n    59\t                            **{k: v.astype(str) for k, v in arrs.items() if v.dtype == object})\n    60\t        summary[task] = rec\n    61\t        logger.info(f\"{task}: units dumped; W1 fro ratio U_bf/U_abs {rec['W1']['fro_ratio_total']:.3f}\")\n    62\t    K.write_json(K.RESULTS / \"unit_profiles.json\", summary)\n    63\t\n    64\t\n    65\tif __name__ == \"__main__\":\n    66\t    main()", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [33] ASSISTANT · 2026-10-26 13:02:07 UTC

```
Next, the rest of `gen_k.py` (unit tests and stages) and the vendored edit function `make_edits_v4`, to see whether the core edit can be shown on CPU.
```

### [34] TOOL CALL — Bash · 2026-10-26 13:02:07 UTC

```
Read remaining part of the GPU runner:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36; sed -n 400,700p $A/src/gen_k.py | cat -n | sed 's/^/   +399 /' | head -330
```

### [35] TOOL RESULT — Bash · 2026-10-26 13:02:07 UTC

```
{"stdout": "   +399      1\t                                    use_cache=True).last_hidden_state\n   +399      2\t                    lg = model.lm_head(h[:, -1]).double()\n   +399      3\t                    pr = torch.softmax(lg, -1).cumsum(-1)\n   +399      4\t                    del lg, pr\n   +399      5\t            peak = torch.cuda.max_memory_allocated() / 2 ** 30\n   +399      6\t            free, total = torch.cuda.mem_get_info(0)\n   +399      7\t            del cache, kv, copies\n   +399      8\t            torch.cuda.empty_cache()\n   +399      9\t            ok = peak + 1.5 < total / 2 ** 30\n   +399     10\t            res[\"tried\"][B] = {\"peak_GiB\": round(peak, 2), \"ok\": ok}\n   +399     11\t            logger.info(f\"memory probe B={B}: peak {peak:.2f} GiB (ok={ok})\")\n   +399     12\t            if ok:\n   +399     13\t                chosen = B\n   +399     14\t                break\n   +399     15\t        except torch.cuda.OutOfMemoryError:\n   +399     16\t            res[\"tried\"][B] = {\"oom\": True}\n   +399     17\t            torch.cuda.empty_cache()\n   +399     18\t    res[\"B\"] = chosen or 4\n   +399     19\t    write_json(RESULTS / \"memory_probe.json\", res)\n   +399     20\t    return res[\"B\"]\n   +399     21\t\n   +399     22\t\n   +399     23\t# ------------------------------------------------------------------------------------------------ unit tests\n   +399     24\tdef unit_tests(model: Any, tok: Any, prompts: dict, B: int) -> dict[str, Any]:\n   +399     25\t    if UNIT_TESTS.exists():\n   +399     26\t        return read_json(UNIT_TESTS)\n   +399     27\t    res: dict[str, Any] = {\"utc\": utc_now(), \"B\": B}\n   +399     28\t    # U1 / U2 / U6 on T10 W1 and T2 W1\n   +399     29\t    e27 = defaultdict(list)\n   +399     30\t    for r in read_jsonl(K.E27 / \"data\" / \"samples_raw.jsonl\"):\n   +399     31\t        if r[\"arm\"] in (\"PN_a1\", \"PN_a2\") and r.get(\"unit_mean_b12\") is not None:\n   +399     32\t            e27[(r[\"task\"], r[\"template\"])].append(r[\"unit_mean_b12\"])\n   +399     33\t    u1, u2, u5 = {}, {}, {}\n   +399     34\t    for task in (\"T10\", \"T2\", \"T03\", \"T05\", \"T1\"):\n   +399     35\t        ctx = TaskCtxK(model, prompts, task)\n   +399     36\t        for w in TEMPLATES:\n   +399     37\t            tw = ctx.twin(w)\n   +399     38\t            here = float(tw[\"U_bf\"][0].mean())\n   +399     39\t            ref = float(np.median(e27[(task, w)])) if e27.get((task, w)) else None\n   +399     40\t            u5[f\"{task}|{w}\"] = {\"here\": here, \"exp27\": ref,\n   +399     41\t                                 \"rel\": None if ref is None else abs(here - ref) / ref}\n   +399     42\t            if task in (\"T10\", \"T2\") and w == \"W1\":\n   +399     43\t                dseed, u = KU.s4_direction(task, 2.0, w, 0)\n   +399     44\t                for name in (\"U_abs\", \"U_bf\", \"U_bf_star\", \"P_top\", \"P_rest\", \"P_shuf\"):\n   +399     45\t                    unit, mask = ctx.unit(w, name)\n   +399     46\t                    pre0, rec0, _ = ctx.edited_prefill(w, u, unit, 0.0, mask, 0.5, want_gen1=False)\n   +399     47\t                    same_logits = bool(torch.equal(pre0[\"r_logits\"], tw[\"pre\"][\"r_logits\"]))\n   +399     48\t                    same_kv = all(torch.equal(x[0], y[0]) and torch.equal(x[1], y[1])\n   +399     49\t                                  for x, y in zip(pre0[\"kv\"], tw[\"pre\"][\"kv\"]))\n   +399     50\t                    u1[f\"{task}|{name}\"] = {\"logits_bitwise\": same_logits, \"kv_bitwise\": same_kv}\n   +399     51\t                    pre2, rec2, _ = ctx.edited_prefill(w, u, unit, 2.0, mask, 0.5, want_gen1=True)\n   +399     52\t                    u2[f\"{task}|{name}\"] = {\"rel_err_mean\": rec2[\"rel_err_mean\"], \"rel_err_max\": rec2[\"rel_err_max\"],\n   +399     53\t                                            \"masked_b12_max_abs_disp\": rec2[\"masked_b12_max_abs_disp\"],\n   +399     54\t                                            \"spec_mean_b0_11_max\": max(rec2[\"spec_mean\"][:12]),\n   +399     55\t                                            \"lens\": [len(rec2[\"spec_mean\"]), len(rec2[\"R\"]), len(rec2[\"gen1\"])],\n   +399     56\t                                            \"S_b12\": rec2[\"spec_mean\"][12], \"R_b35\": rec2[\"R\"][35],\n   +399     57\t                                            \"G1_b35\": rec2[\"gen1\"][35]}\n   +399     58\t                    del pre0, pre2\n   +399     59\t        ctx.release()\n   +399     60\t    res[\"U1_alpha0_bitwise_twin\"] = u1\n   +399     61\t    res[\"U1_pass\"] = all(v[\"logits_bitwise\"] and v[\"kv_bitwise\"] for v in u1.values())\n   +399     62\t    res[\"U2_displacement\"] = u2\n   +399     63\t    res[\"U2_pass\"] = all(v[\"rel_err_mean\"] <= 1e-3 and (v[\"masked_b12_max_abs_disp\"] in (None, 0.0)) for v in u2.values())\n   +399     64\t    res[\"U6_lengths_36\"] = all(v[\"lens\"] == [36, 36, 36] and v[\"spec_mean_b0_11_max\"] == 0.0 for v in u2.values())\n   +399     65\t    res[\"U5_ubf_vs_exp27\"] = u5\n   +399     66\t    rels = [v[\"rel\"] for v in u5.values() if v[\"rel\"] is not None]\n   +399     67\t    res[\"U5_max_rel\"] = max(rels) if rels else None\n   +399     68\t    res[\"U5_pass\"] = bool(rels) and max(rels) <= 0.01\n   +399     69\t    # U3 batch-shape invariance and U4 self-reproduction (T10 W1 twin slots, max_new 256)\n   +399     70\t    ctx = TaskCtxK(model, prompts, \"T10\")\n   +399     71\t    tw = ctx.twin(\"W1\")\n   +399     72\t\n   +399     73\t    def twin_batch(ks: list[int]) -> list[dict[str, Any]]:\n   +399     74\t        g = [{\"pre\": tw[\"pre\"], \"us\": [u_stream(\"T10\", \"W1\", k, n=256) for k in ks]}]\n   +399     75\t        return sample4(model, tok, g, fence=FENCE[\"T10\"], max_new=256)\n   +399     76\t    full = twin_batch(list(range(B)))\n   +399     77\t    again = twin_batch(list(range(B)))\n   +399     78\t    half = twin_batch(list(range(max(3, B // 2))))\n   +399     79\t    res[\"U4_self_reproduction\"] = sum(x[\"token_ids\"] == y[\"token_ids\"] for x, y in zip(full, again)) / B\n   +399     80\t    res[\"U3_batch_shape_identical_rows\"] = sum(full[i][\"token_ids\"] == half[i][\"token_ids\"] for i in range(3))\n   +399     81\t    res[\"U3_pass\"] = res[\"U3_batch_shape_identical_rows\"] == 3\n   +399     82\t    res[\"U4_pass\"] = res[\"U4_self_reproduction\"] == 1.0\n   +399     83\t    ctx.release()\n   +399     84\t    write_json(UNIT_TESTS, res)\n   +399     85\t    logger.info(f\"unit tests: U1 {res['U1_pass']} U2 {res['U2_pass']} U3 {res['U3_pass']} U4 {res['U4_pass']} \"\n   +399     86\t                f\"U5 {res['U5_pass']} (max rel {res['U5_max_rel']}) U6 {res['U6_lengths_36']}\")\n   +399     87\t    return res\n   +399     88\t\n   +399     89\t\n   +399     90\t# ------------------------------------------------------------------------------------------------ stage helpers\n   +399     91\tdef wait_for(path: Path, what: str, max_wait_s: float = 3 * 3600) -> None:\n   +399     92\t    t0 = time.time()\n   +399     93\t    while not path.exists():\n   +399     94\t        if time.time() - t0 > max_wait_s:\n   +399     95\t            raise TimeoutError(f\"{what} never appeared\")\n   +399     96\t        logger.info(f\"waiting for {what} ({path.name})\")\n   +399     97\t        time.sleep(30)\n   +399     98\t\n   +399     99\t\n   +399    100\tdef labelled(keys: list[str]) -> dict[str, dict[str, Any]]:\n   +399    101\t    want = set(keys)\n   +399    102\t    return {l[\"key\"]: l for l in read_jsonl(LABELS) if l[\"key\"] in want}\n   +399    103\t\n   +399    104\t\n   +399    105\tdef wait_labels(keys: list[str], timeout: float = 900.0, frac: float = 1.0) -> dict[str, dict[str, Any]]:\n   +399    106\t    t0 = time.time()\n   +399    107\t    while True:\n   +399    108\t        got = labelled(keys)\n   +399    109\t        if len(got) >= frac * len(keys) or time.time() - t0 > timeout:\n   +399    110\t            return got\n   +399    111\t        time.sleep(15)\n   +399    112\t\n   +399    113\t\n   +399    114\tdef s1_cells(task: str, alpha: float, ks: list[int]) -> list[tuple[str, list[int]]]:\n   +399    115\t    a = \"a1\" if alpha == 1.0 else \"a2\"\n   +399    116\t    return [(f\"D1_{a}\", ks), (f\"D2_{a}\", ks), (f\"D3_{a}\", ks), (f\"D4_{a}\", ks)]\n   +399    117\t\n   +399    118\t\n   +399    119\t# ------------------------------------------------------------------------------------------------ main\n   +399    120\t@logger.catch(reraise=True)\n   +399    121\tdef main() -> None:\n   +399    122\t    K.setup_logging(\"gen_k\")\n   +399    123\t    stages = sys.argv[1:] or [\"tests\", \"s0\", \"s1\", \"d5\", \"s2\", \"s3pn\"]\n   +399    124\t    hw = hardware_record()\n   +399    125\t    logger.info(f\"hardware: {hw['gpu']} free {hw['free_GiB_before_load']:.1f} GiB; stages {stages}\")\n   +399    126\t    tok, model = load_model(fp8=False, vram_fraction=0.97)\n   +399    127\t    prompts = load_prompts()\n   +399    128\t    st = read_json(STATE) if STATE.exists() else {}\n   +399    129\t    if \"B\" not in st:\n   +399    130\t        st[\"B\"] = memory_probe(model, prompts)\n   +399    131\t        write_json(STATE, st)\n   +399    132\t    B = st[\"B\"]\n   +399    133\t    logger.info(f\"constant batch size B = {B}\")\n   +399    134\t    run = RunnerK(model, tok, prompts, B)\n   +399    135\t    if \"tests\" in stages:\n   +399    136\t        unit_tests(model, tok, prompts, B)\n   +399    137\t    if \"s0\" in stages:\n   +399    138\t        # 2.1 engine-check slots first (k 0-3 of T2 and T03), then the full twin cells (k 0-9; T2 also 10-19)\n   +399    139\t        run.run_cells(\"T2\", [(\"TWIN\", [0, 1, 2, 3])], \"S0_check\")\n   +399    140\t        run.run_cells(\"T03\", [(\"TWIN\", [0, 1, 2, 3])], \"S0_check\")\n   +399    141\t        for t in (\"T10\", \"T2\", \"T03\", \"T05\", \"T1\"):\n   +399    142\t            run.run_cells(t, [(\"TWIN\", K20 if t == \"T2\" else K10)], \"S0_twin\")\n   +399    143\t    if any(s in stages for s in (\"s1\", \"d5\", \"s2\", \"s3pn\")):\n   +399    144\t        wait_for(PRED / \"commit1.json\", \"COMMIT #1\")\n   +399    145\t    if \"s1\" in stages:\n   +399    146\t        # (a) anchors on T10 alpha 2: W1 first (the 10-slot stage), then W2-W5\n   +399    147\t        anchors = [(\"D1_a2\", K10), (\"D4_a2\", K10)]\n   +399    148\t        run.run_cells(\"T10\", anchors, \"S1_anchor\", templates=(\"W1\",))\n   +399    149\t        run.run_cells(\"T10\", anchors, \"S1_anchor\")\n   +399    150\t        # (b) the rest of T10; (c) T2 alpha 2 (N 100) and alpha 1 (N 50)\n   +399    151\t        run.run_cells(\"T10\", s1_cells(\"T10\", 2.0, K10), \"S1\")\n   +399    152\t        run.run_cells(\"T10\", s1_cells(\"T10\", 1.0, K10), \"S1\")\n   +399    153\t        run.run_cells(\"T2\", s1_cells(\"T2\", 2.0, K20), \"S1\")\n   +399    154\t        run.run_cells(\"T2\", s1_cells(\"T2\", 1.0, K10), \"S1\")\n   +399    155\t    if \"d5\" in stages:\n   +399    156\t        run.run_cells(\"T10\", [(\"D5_a2\", K10)], \"S1_D5\")\n   +399    157\t        run.run_cells(\"T2\", [(\"D5_a2\", K20)], \"S1_D5\")\n   +399    158\t    if \"s2\" in stages:\n   +399    159\t        for t in (\"T10\", \"T2\"):\n   +399    160\t            run.run_cells(t, [(\"PTOP_a2\", K10), (\"PREST_a2\", K10), (\"PSHUF_a2\", K10)], \"S2\")\n   +399    161\t    if \"diag9101\" in stages:\n   +399    162\t        logger.warning(\"diag9101 requested: fixed direction rand_9101 is run by gen_k only on demand\")\n   +399    163\t    if \"s3pn\" in stages:\n   +399    164\t        wait_for(PRED / \"commit2.json\", \"COMMIT #2\")\n   +399    165\t        dstar = read_json(PRED / \"commit2.json\")[\"D_star\"]\n   +399    166\t        for t in (\"T03\", \"T05\", \"T1\"):\n   +399    167\t            run.run_cells(t, [(f\"{dstar}_a1\", K10), (f\"{dstar}_a2\", K10)], \"S3_PN\")\n   +399    168\t        if dstar not in (\"D1\", \"D2\", \"D3\", \"D4\"):\n   +399    169\t            for t in (\"T10\", \"T2\"):\n   +399    170\t                run.run_cells(t, [(f\"{dstar}_a1\", K10), (f\"{dstar}_a2\", K10)], \"S3_PN\")\n   +399    171\t    write_json(RESULTS / \"gpu_done.json\", {\"stages\": stages, \"utc\": utc_now()})\n   +399    172\t    logger.info(\"GPU process finished\")\n   +399    173\t\n   +399    174\t\n   +399    175\tif __name__ == \"__main__\":\n   +399    176\t    main()", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [36] TOOL CALL — Bash · 2026-10-26 13:02:07 UTC

```
Locate vendored make_edits_v4 function:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36; ls -la $A/vendor/exp22 $A/vendor/exp22/src 2>/dev/null | head -60; grep -rn "def make_edits_v4" $A/vendor/ | head
```

### [37] TOOL RESULT — Bash · 2026-10-26 13:02:09 UTC

```
{"stdout": "/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36/vendor/exp22:\ntotal 14946\ndrwxrwxrwx 15 aii-agent aii-agent 2005509 Oct 22 13:22 .\ndrwxrwxrwx  6 aii-agent aii-agent 2013317 Oct 22 13:10 ..\ndrwxrwxrwx  2 aii-agent aii-agent 1011993 Oct 21 10:54 analysis\ndrwxrwxrwx  2 aii-agent aii-agent       1 Oct 22 05:10 audit\ndrwxrwxrwx  3 aii-agent aii-agent 1081407 Oct 22 05:10 data\ndrwxrwxrwx  2 aii-agent aii-agent 1098362 Oct 21 04:27 directions\ndrwxrwxrwx  2 aii-agent aii-agent       1 Oct 22 13:22 figures\ndrwxrwxrwx 10 aii-agent aii-agent 2004338 Oct 21 03:33 inputs\ndrwxrwxrwx  2 aii-agent aii-agent       1 Oct 22 13:22 logs\ndrwxrwxrwx  2 aii-agent aii-agent 1044820 Oct 22 05:02 predictions\ndrwxrwxrwx  2 aii-agent aii-agent 2000903 Oct 21 03:43 prompts\ndrwxrwxrwx  2 aii-agent aii-agent 1001557 Oct 22 05:37 results\ndrwxrwxrwx  2 aii-agent aii-agent 1013688 Oct 23 00:07 src\ndrwxrwxrwx  3 aii-agent aii-agent 1022892 Oct 23 00:07 src_base\ndrwxrwxrwx  2 aii-agent aii-agent       1 Oct 22 13:22 states\n\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36/vendor/exp22/src:\ntotal 3091\ndrwxrwxrwx  2 aii-agent aii-agent 1013688 Oct 23 00:07 .\ndrwxrwxrwx 15 aii-agent aii-agent 2005509 Oct 22 13:22 ..\n-rw-rw-rw-  1 aii-agent aii-agent    6350 Oct 21 07:53 cfg4.py\n-rw-rw-rw-  1 aii-agent aii-agent    2151 Oct 21 05:14 commit4.py\n-rw-rw-rw-  1 aii-agent aii-agent    1320 Oct 21 07:15 costs.py\n-rw-rw-rw-  1 aii-agent aii-agent    6440 Oct 21 03:48 ctx4.py\n-rw-rw-rw-  1 aii-agent aii-agent    8639 Oct 21 03:37 describe.py\n-rw-rw-rw-  1 aii-agent aii-agent    4857 Oct 21 04:53 deviations.py\n-rw-rw-rw-  1 aii-agent aii-agent    5652 Oct 21 03:45 engine4.py\n-rw-rw-rw-  1 aii-agent aii-agent    1526 Oct 21 04:38 extract_known.py\n-rw-rw-rw-  1 aii-agent aii-agent   13412 Oct 21 08:14 gpu_phase1.py\n-rw-rw-rw-  1 aii-agent aii-agent    9958 Oct 21 04:05 gpu_phase2.py\n-rw-rw-rw-  1 aii-agent aii-agent    5730 Oct 21 04:35 gpu_phase3.py\n-rw-rw-rw-  1 aii-agent aii-agent    2181 Oct 21 03:45 hooks4.py\n-rw-rw-rw-  1 aii-agent aii-agent    3500 Oct 21 03:53 label4.py\n-rw-rw-rw-  1 aii-agent aii-agent    5203 Oct 21 07:38 make_commit.py\n-rw-rw-rw-  1 aii-agent aii-agent    2509 Oct 21 08:11 npz_parts.py\n-rw-rw-rw-  1 aii-agent aii-agent   11639 Oct 21 03:40 prompts4.py\n-rw-rw-rw-  1 aii-agent aii-agent    3218 Oct 21 04:16 recheck4.py\n-rw-rw-rw-  1 aii-agent aii-agent    8818 Oct 21 07:53 s0_setup.py\n-rw-rw-rw-  1 aii-agent aii-agent   10001 Oct 21 03:49 sampling4.py\n-rw-rw-rw-  1 aii-agent aii-agent    6598 Oct 21 03:54 screen.py\n-rw-rw-rw-  1 aii-agent aii-agent   20470 Oct 21 08:14 subspace.py\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36/vendor/exp22/src/hooks4.py:22:def make_edits_v4(kind: str, a: int, b: int, U: dict[int, torch.Tensor], M: dict[int, torch.Tensor],", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [38] TOOL CALL — Bash · 2026-10-26 13:02:17 UTC

```
Read vendored edit hooks and task catalogues:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36; cat -n $A/vendor/exp22/src/hooks4.py; echo ======; grep -n "PATH_CATALOGUE" -A12 $A/vendor/exp22/src/cfg4.py | head -40; echo =====; find $A/vendor/exp22/inputs/exp11 -name "catalogue.py" | head; 
```

### [39] TOOL RESULT — Bash · 2026-10-26 13:02:17 UTC

```
{"stdout": "     1\t#!/usr/bin/env python3\n     2\t\"\"\"make_edits_v4: block-output edits at the task-spec positions S = [a, b) of EDIT_BLOCKS during the prompt prefill.\n     3\t\n     4\tTARGET: h_S <- h_S + (M[l] - (h_S - h_ref[l]) . U[l]) U[l]   -- the displacement from the clean twin along U[l] is\n     5\t        exactly M[l][p] at every edited block (no compounding); with U[l] = u and M = alpha * n this is exp17 RAND,\n     6\t        written with the same fp32 operations in the same order.\n     7\tCLAMP:  TARGET, then h_S <- h_S - ((h_S - h_ref[l]) Q_l) Q_l^T, so the displacement's component in the plan subspace\n     8\t        P_t (orthonormal basis Q_l, [D, k]) is zero at that block.\n     9\tAll edits are computed in fp32 and cast back to the block's dtype. `log` collects the mean |coefficient| per block.\n    10\t\"\"\"\n    11\t\n    12\tfrom __future__ import annotations\n    13\t\n    14\tfrom typing import Any, Callable\n    15\t\n    16\timport numpy as np\n    17\timport torch\n    18\t\n    19\tfrom cfg4 import EDIT_BLOCKS\n    20\t\n    21\t\n    22\tdef make_edits_v4(kind: str, a: int, b: int, U: dict[int, torch.Tensor], M: dict[int, torch.Tensor],\n    23\t                  h_ref: dict[int, torch.Tensor], Q: dict[int, torch.Tensor] | None = None,\n    24\t                  log: dict[int, list[float]] | None = None) -> dict[int, Callable[[torch.Tensor], torch.Tensor]]:\n    25\t    assert kind in (\"TARGET\", \"CLAMP\"), kind\n    26\t    edits = {}\n    27\t    for l in EDIT_BLOCKS:\n    28\t        def f(h: torch.Tensor, l: int = l) -> torch.Tensor:\n    29\t            hs = h[:, a:b].float()\n    30\t            ul = U[l]\n    31\t            comp = (hs - h_ref[l]) @ ul\n    32\t            coef = M[l] - comp\n    33\t            new = hs + coef[..., None] * ul\n    34\t            if kind == \"CLAMP\":\n    35\t                Ql = Q[l]\n    36\t                dproj = (new - h_ref[l]) @ Ql\n    37\t                new = new - dproj @ Ql.T\n    38\t            if log is not None:\n    39\t                log.setdefault(l, []).append(float(coef.abs().mean()))\n    40\t            h = h.clone()\n    41\t            h[:, a:b] = new.to(h.dtype)\n    42\t            return h\n    43\t        edits[l] = f\n    44\t    return edits\n    45\t\n    46\t\n    47\tdef to_dev(d: dict[int, Any], device: torch.device) -> dict[int, torch.Tensor]:\n    48\t    return {int(k): torch.as_tensor(np.asarray(v), dtype=torch.float32, device=device) for k, v in d.items()}\n    49\t\n    50\t\n    51\tdef unit(x: np.ndarray) -> np.ndarray:\n    52\t    return (x / max(float(np.linalg.norm(x)), 1e-12)).astype(np.float32)\n======\n56:PATH_CATALOGUE: dict[str, dict[str, list[str]]] = {\n57-    \"T1\": {\"bfs\": [\"breadth-first search (BFS)\", \"BFS\", \"breadth-first search\"],\n58-           \"dfs\": [\"depth-first search (DFS)\", \"DFS\", \"depth-first search\"],\n59-           \"bibfs\": [\"bidirectional BFS\", \"bidirectional breadth-first search\", \"two-ended BFS\"],\n60-           \"iddfs\": [\"iterative deepening DFS (IDDFS)\", \"IDDFS\", \"iterative deepening depth-first search\"],\n61-           \"astar_gbfs\": [\"A* or greedy best-first search\", \"A* search\", \"greedy best-first search\"],\n62-           \"dijkstra\": [\"Dijkstra's algorithm\", \"Dijkstra\", \"Dijkstra's shortest-path algorithm\"]},\n63-    \"T2\": {\"dijkstra\": [\"Dijkstra's algorithm\", \"Dijkstra\", \"Dijkstra's shortest-path algorithm\"],\n64-           \"bf_spfa\": [\"Bellman-Ford or SPFA\", \"Bellman-Ford\", \"SPFA\"],\n65-           \"bidijkstra\": [\"bidirectional Dijkstra\", \"bidirectional Dijkstra's algorithm\", \"two-ended Dijkstra\"],\n66-           \"floyd\": [\"Floyd-Warshall\", \"the Floyd-Warshall algorithm\", \"Floyd's all-pairs algorithm\"],\n67-           \"dial\": [\"Dial's algorithm\", \"a bucket-queue Dijkstra\", \"bucket-based shortest paths\"]},\n68-}\n=====\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36/vendor/exp22/inputs/exp11/bench/common/catalogue.py", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [40] TOOL CALL — Bash · 2026-10-26 13:02:17 UTC

```
Inspect per-program samples.jsonl fields and arm counts:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36; head -c 3000 $A/data/samples.jsonl; echo; echo ....; python3 -c "
import json
from collections import Counter
rows=[json.loads(l) for l in open('$A/data/samples.jsonl')]
print('n rows', len(rows)); print('keys', list(rows[0].keys()))
c=Counter((r['task'], r['arm']) for r in rows)
for k,v in sorted(c.items()): print(k, v)
"
```

### [41] TOOL RESULT — Bash · 2026-10-26 13:02:17 UTC

```
{"stdout": "{\"key\": \"T2|W1|TWIN|0\", \"source\": \"raw_k.jsonl\", \"task\": \"T2\", \"template\": \"W1\", \"arm\": \"TWIN\", \"k\": 0, \"stage\": \"S0_check\", \"design\": \"TWIN\", \"alpha\": null, \"unit_id\": null, \"seed_scheme\": null, \"direction_seed\": null, \"uniform_seed\": 3493292318901305229, \"temperature\": 1.0, \"top_k\": null, \"B\": 12, \"engine_path\": \"shared\", \"prompt_sha256\": \"b6110af926ba9508f90373cc6b9a836db6cf5cca7f83ff03dd15821ed571c0a9\", \"n_tokens\": 179, \"finish_reason\": \"stop\", \"realised_disp\": null, \"unit_mean_b12\": null, \"label\": \"dijkstra\", \"passed\": true, \"valid\": true, \"labeller_source\": \"agree\", \"Y\": 0, \"Y_any\": 0, \"A\": 0, \"code\": \"import heapq\\n\\ndef solve(n, edges, s, t):\\n    if s == t:\\n        return 0\\n    \\n    adj = [[] for _ in range(n)]\\n    for u, v, w in edges:\\n        adj[u].append((v, w))\\n    \\n    dist = [float('inf')] * n\\n    dist[s] = 0\\n    heap = [(0, s)]\\n    \\n    while heap:\\n        current_dist, u = heapq.heappop(heap)\\n        if current_dist > dist[u]:\\n            continue\\n        for v, weight in adj[u]:\\n            if dist[v] > dist[u] + weight:\\n                dist[v] = dist[u] + weight\\n                heapq.heappush(heap, (dist[v], v))\\n    \\n    return dist[t] if dist[t] != float('inf') else -1\\n\"}\n{\"key\": \"T2|W1|TWIN|1\", \"source\": \"raw_k.jsonl\", \"task\": \"T2\", \"template\": \"W1\", \"arm\": \"TWIN\", \"k\": 1, \"stage\": \"S0_check\", \"design\": \"TWIN\", \"alpha\": null, \"unit_id\": null, \"seed_scheme\": null, \"direction_seed\": null, \"uniform_seed\": 4665173263526197234, \"temperature\": 1.0, \"top_k\": null, \"B\": 12, \"engine_path\": \"shared\", \"prompt_sha256\": \"b6110af926ba9508f90373cc6b9a836db6cf5cca7f83ff03dd15821ed571c0a9\", \"n_tokens\": 198, \"finish_reason\": \"stop\", \"realised_disp\": null, \"unit_mean_b12\": null, \"label\": \"bf_spfa\", \"passed\": false, \"valid\": true, \"labeller_source\": \"agree\", \"Y\": 0, \"Y_any\": 0, \"A\": 1, \"code\": \"from collections import deque\\n\\ndef solve(n, edges, s, t):\\n    if s == t:\\n        return 0\\n    \\n    # Build adjacency list\\n    adj = [[] for _ in range(n)]\\n    for u, v, w in edges:\\n        adj[u].append((v, w))\\n    \\n    # Dijkstra's algorithm\\n    dist = [float('inf')] * n\\n    dist[s] = 0\\n    visited = [False] * n\\n    pq = [(0, s)]\\n    \\n    while pq:\\n        current_dist, u = pq.pop(0)\\n        if visited[u]:\\n            continue\\n        visited[u] = True\\n        if u == t:\\n            return current_dist\\n        for v, w in adj[u]:\\n            if dist[v] > current_dist + w:\\n                dist[v] = current_dist + w\\n                pq.append((dist[v], v))\\n    \\n    return -1\\n\"}\n{\"key\": \"T2|W1|TWIN|2\", \"source\": \"raw_k.jsonl\", \"task\": \"T2\", \"template\": \"W1\", \"arm\": \"TWIN\", \"k\": 2, \"stage\": \"S0_check\", \"design\": \"TWIN\", \"alpha\": null, \"unit_id\": null, \"seed_scheme\": null, \"direction_seed\": null, \"uniform_seed\": 883993129541335778, \"temperature\": 1.0, \"top_k\": null, \"B\": 12, \"engine_path\": \"shared\", \"prompt_sha256\": \"b6110af926ba9508f90373cc6b9a836db6cf5cca7f83ff03dd15821ed571c0a9\", \"n_tokens\": 179, \"finish_r\n....\nn rows 5360\nkeys ['key', 'source', 'task', 'template', 'arm', 'k', 'stage', 'design', 'alpha', 'unit_id', 'seed_scheme', 'direction_seed', 'uniform_seed', 'temperature', 'top_k', 'B', 'engine_path', 'prompt_sha256', 'n_tokens', 'finish_reason', 'realised_disp', 'unit_mean_b12', 'label', 'passed', 'valid', 'labeller_source', 'Y', 'Y_any', 'A', 'code']\n('T03', 'BINT') 10\n('T03', 'D1_a1') 50\n('T03', 'D1_a2') 50\n('T03', 'D2_a2') 50\n('T03', 'D3_a2') 50\n('T03', 'D4_a2') 50\n('T03', 'E27:BINT') 50\n('T03', 'E27:EAP') 50\n('T03', 'E27:IFG_hot') 50\n('T03', 'E27:T1.3') 50\n('T03', 'E27:TOPK10') 50\n('T03', 'EAP') 50\n('T03', 'IFG_hot') 50\n('T03', 'T1.3') 50\n('T03', 'TOPK10') 10\n('T03', 'TWIN') 170\n('T05', 'BINT') 10\n('T05', 'D1_a1') 50\n('T05', 'D1_a2') 50\n('T05', 'E27:BINT') 50\n('T05', 'E27:EAP') 50\n('T05', 'E27:IFG_hot') 50\n('T05', 'E27:T1.3') 50\n('T05', 'E27:TOPK10') 50\n('T05', 'EAP') 50\n('T05', 'IFG_hot') 10\n('T05', 'T1.3') 10\n('T05', 'TOPK10') 10\n('T05', 'TWIN') 80\n('T1', 'BINT') 50\n('T1', 'D1_a1') 50\n('T1', 'D1_a2') 50\n('T1', 'E27:BINT') 50\n('T1', 'E27:EAP') 50\n('T1', 'E27:IFG_hot') 50\n('T1', 'E27:T1.3') 50\n('T1', 'E27:TOPK10') 50\n('T1', 'EAP') 50\n('T1', 'IFG_hot') 10\n('T1', 'T1.3') 10\n('T1', 'TOPK10') 10\n('T1', 'TWIN') 80\n('T10', 'BINT') 10\n('T10', 'D1_a1') 50\n('T10', 'D1_a2') 100\n('T10', 'D2_a1') 50\n('T10', 'D2_a2') 100\n('T10', 'D3_a1') 50\n('T10', 'D3_a2') 100\n('T10', 'D3_a3') 50\n('T10', 'D3_a4') 50\n('T10', 'D3_a6') 50\n('T10', 'D4_a1') 50\n('T10', 'D4_a2') 100\n('T10', 'D5_a2') 100\n('T10', 'E27:BINT') 50\n('T10', 'E27:EAP') 50\n('T10', 'E27:IFG_hot') 50\n('T10', 'E27:T1.3') 50\n('T10', 'E27:TOPK10') 50\n('T10', 'EAP') 50\n('T10', 'IFG_hot') 10\n('T10', 'PREST_a2') 100\n('T10', 'PSHUF_a2') 100\n('T10', 'PTOP_a2') 100\n('T10', 'T1.3') 10\n('T10', 'TOPK10') 10\n('T10', 'TWIN') 290\n('T2', 'BINT') 10\n('T2', 'D1_a1') 50\n('T2', 'D1_a2') 100\n('T2', 'D2_a1') 50\n('T2', 'D2_a2') 100\n('T2', 'D3_a1') 50\n('T2', 'D3_a2') 100\n('T2', 'D3_a3') 50\n('T2', 'D3_a4') 50\n('T2', 'D3_a6') 50\n('T2', 'D4_a1') 50\n('T2', 'D4_a2') 100\n('T2', 'D5_a2') 100\n('T2', 'E27:BINT') 50\n('T2', 'E27:EAP') 50\n('T2', 'E27:IFG_hot') 50\n('T2', 'E27:T1.3') 50\n('T2', 'E27:TOPK10') 50\n('T2', 'EAP') 50\n('T2', 'IFG_hot') 10\n('T2', 'PREST_a2') 50\n('T2', 'PSHUF_a2') 50\n('T2', 'PTOP_a2') 50\n('T2', 'T1.3') 10\n('T2', 'TOPK10') 10\n('T2', 'TWIN') 320", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [42] THINKING · 2026-10-26 13:03:27 UTC

```
`data/samples.jsonl` matches the expected joined per-program shape with T10's 100 CRN slots carrying up to 17 arms each. Next I'll check the remaining supporting modules: geometry, figures, outputs, and the T10 catalogue.
```

### [43] TOOL CALL — Bash · 2026-10-26 13:03:27 UTC

```
Read the E2 geometry module:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36; cat -n $A/src/geometry_k.py
```

### [44] TOOL RESULT — Bash · 2026-10-26 13:03:27 UTC

```
{"stdout": "     1\t#!/usr/bin/env python3\n     2\t\"\"\"E2 (exploratory, CPU only, not pre-registered): is the downstream displacement's DIRECTION, not its size, what\n     3\tseparates escapes? Uses the fp16 displacement vectors logged for every pushed row (cache/disp: spec-mean at blocks 23\n     4\tand 35, read position R at block 35, generated position 1 at block 35) of the S1 designs, D5 and E1 on T10 and T2.\n     5\t\n     6\t  (a) 5-fold CV AUC of the attempt indicator A from: the two log norms (S35, R35); the unit-normalised R35 direction;\n     7\t      the unit-normalised gen-1 direction; the spec-mean-35 direction (PCA-32 inside each fold, then logistic).\n     8\t  (b) transfer: an escape axis = difference of the mean unit-normalised R35 vectors of attempted and default rows of\n     9\t      the U_abs designs (D1, D2; alpha 1-2); AUC of the projection on held-out U_abs rows (2-fold by template) and on\n    10\t      every U_bf-family row (D3, D4, D5, E1) never used to build it.\n    11\t  (c) per-design mean projection on the axis (figure F7: projection vs block-35 R norm, coloured by outcome).\n    12\t\n    13\tusage: .venv/bin/python src/geometry_k.py\n    14\t\"\"\"\n    15\t\n    16\tfrom __future__ import annotations\n    17\t\n    18\timport sys\n    19\tfrom collections import defaultdict\n    20\tfrom pathlib import Path\n    21\t\n    22\timport matplotlib\n    23\t\n    24\tmatplotlib.use(\"Agg\")\n    25\timport matplotlib.pyplot as plt  # noqa: E402\n    26\timport numpy as np  # noqa: E402\n    27\tfrom loguru import logger  # noqa: E402\n    28\t\n    29\tsys.path.insert(0, str(Path(__file__).resolve().parent))\n    30\t\n    31\timport k_cfg as K  # noqa: E402\n    32\tfrom k_cfg import FIGS, RESULTS, write_json  # noqa: E402\n    33\t\n    34\t\n    35\tdef load_vectors() -> dict[str, dict[str, np.ndarray]]:\n    36\t    vecs: dict[str, dict[str, np.ndarray]] = defaultdict(dict)\n    37\t    for p in sorted((K.CACHE / \"disp\").glob(\"*.npz\")):\n    38\t        z = np.load(p)\n    39\t        for k in z.files:\n    40\t            key, kind = k.split(\"::\")\n    41\t            vecs[key][kind] = z[k].astype(np.float32)\n    42\t    return vecs\n    43\t\n    44\t\n    45\tdef unit_rows(X: np.ndarray) -> np.ndarray:\n    46\t    return X / np.maximum(np.linalg.norm(X, axis=1, keepdims=True), 1e-9)\n    47\t\n    48\t\n    49\tdef cv_auc(X: np.ndarray, y: np.ndarray, pca: int | None = 32) -> float | None:\n    50\t    from sklearn.decomposition import PCA\n    51\t    from sklearn.linear_model import LogisticRegression\n    52\t    from sklearn.metrics import roc_auc_score\n    53\t    from sklearn.model_selection import StratifiedKFold, cross_val_predict\n    54\t    from sklearn.pipeline import make_pipeline\n    55\t    from sklearn.preprocessing import StandardScaler\n    56\t\n    57\t    if y.sum() < 5 or (len(y) - y.sum()) < 5:\n    58\t        return None\n    59\t    steps = [StandardScaler()]\n    60\t    if pca:\n    61\t        steps.append(PCA(n_components=min(pca, X.shape[1], len(y) // 3)))\n    62\t    steps.append(LogisticRegression(C=0.1, max_iter=5000))\n    63\t    pr = cross_val_predict(make_pipeline(*steps), X, y, cv=StratifiedKFold(5, shuffle=True, random_state=0),\n    64\t                           method=\"predict_proba\")[:, 1]\n    65\t    return float(roc_auc_score(y, pr))\n    66\t\n    67\t\n    68\tdef auc(score: np.ndarray, y: np.ndarray) -> float | None:\n    69\t    from sklearn.metrics import roc_auc_score\n    70\t    if y.sum() == 0 or y.sum() == len(y):\n    71\t        return None\n    72\t    return float(roc_auc_score(y, score))\n    73\t\n    74\t\n    75\tdef slot_concordance() -> dict:\n    76\t    \"\"\"Per-slot concordance of outcomes across designs that share the slot's token stream (phi coefficient, joint\n    77\t    count vs independence) and across doses with the same direction (D1 alpha 1 -> alpha 2).\"\"\"\n    78\t    import analysis_k as A\n    79\t\n    80\t    rows = A.load_joined()\n    81\t    out: dict = {}\n    82\t\n    83\t    def phi(a: np.ndarray, b: np.ndarray) -> float | None:\n    84\t        if a.std() == 0 or b.std() == 0:\n    85\t            return None\n    86\t        return float(np.corrcoef(a, b)[0, 1])\n    87\t    for task in (\"T10\", \"T2\"):\n    88\t        for key in (\"Y\", \"A\"):\n    89\t            slots, M = A.paired_matrix(rows, task, 2.0, [\"D1\", \"D2\", \"D3\", \"D4\"], key, A.COMMITTED_KS[(task, 2.0)])\n    90\t            if len(slots) < 10:\n    91\t                continue\n    92\t            d1, d2, d3, d4 = M.T\n    93\t            out[f\"{task}|{key}|alpha2\"] = {\n    94\t                \"n_slots\": len(slots), \"phi_D1_D2_same_stream_diff_u\": phi(d1, d2),\n    95\t                \"joint_D1_D2\": int(((d1 == 1) & (d2 == 1)).sum()),\n    96\t                \"joint_expected_if_independent\": float(d1.mean() * d2.mean() * len(d1)),\n    97\t                \"phi_D1_D3_same_u_diff_unit\": phi(d1, d3), \"phi_D2_D4_same_u_diff_unit\": phi(d2, d4)}\n    98\t        c1, c2 = A.cell(rows, task, \"D1_a1\", K.K10), A.cell(rows, task, \"D1_a2\", K.K10)\n    99\t        s_ = sorted(set(c1) & set(c2))\n   100\t        a = np.array([c1[x][\"A\"] for x in s_])\n   101\t        b = np.array([c2[x][\"A\"] for x in s_])\n   102\t        out[f\"{task}|A|D1_alpha1_to_alpha2_same_u_same_stream\"] = {\n   103\t            \"n\": len(s_), \"P_escape_a2_given_escape_a1\": float(b[a == 1].mean()) if a.sum() else None,\n   104\t            \"P_escape_a2_marginal\": float(b.mean()), \"n_escape_a1\": int(a.sum())}\n   105\t    return out\n   106\t\n   107\t\n   108\t@logger.catch(reraise=True)\n   109\tdef main() -> None:\n   110\t    import analysis_k as A\n   111\t\n   112\t    K.setup_logging(\"geometry_k\")\n   113\t    rows = {r[\"key\"]: r for r in A.load_joined() if r.get(\"labelled\")}\n   114\t    vecs = load_vectors()\n   115\t    out: dict = {}\n   116\t    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))\n   117\t    for ax, task in zip(axes, (\"T10\", \"T2\")):\n   118\t        sel = [k for k in vecs if k in rows and rows[k][\"task\"] == task and rows[k][\"design\"] in\n   119\t               (\"D1\", \"D2\", \"D3\", \"D4\", \"D5\") and all(f in vecs[k] for f in (\"R35\", \"smean35\", \"gen1_35\"))\n   120\t               and rows[k][\"k\"] in A.COMMITTED_KS.get((task, rows[k][\"alpha\"]), list(range(10)))]\n   121\t        if len(sel) < 40:\n   122\t            continue\n   123\t        y = np.array([rows[k][\"A\"] for k in sel])\n   124\t        R = np.stack([vecs[k][\"R35\"] for k in sel])\n   125\t        G = np.stack([vecs[k][\"gen1_35\"] for k in sel])\n   126\t        S = np.stack([vecs[k][\"smean35\"] for k in sel])\n   127\t        norms = np.column_stack([np.log(np.linalg.norm(S, axis=1)), np.log(np.linalg.norm(R, axis=1))])\n   128\t        res = {\"n\": len(sel), \"n_attempted\": int(y.sum()),\n   129\t               \"cv_auc_log_norms\": cv_auc(norms, y, pca=None),\n   130\t               \"cv_auc_R35_direction\": cv_auc(unit_rows(R), y),\n   131\t               \"cv_auc_gen1_direction\": cv_auc(unit_rows(G), y),\n   132\t               \"cv_auc_specmean35_direction\": cv_auc(unit_rows(S), y)}\n   133\t        # (b) escape axis built on U_abs rows only (alpha 1-2), 2-fold by template for its own AUC\n   134\t        des = np.array([rows[k][\"design\"] for k in sel])\n   135\t        alp = np.array([rows[k][\"alpha\"] for k in sel])\n   136\t        # (a') the same comparison at a FIXED unit family and dose (alpha 2), so dose cannot drive the norm AUC\n   137\t        strata = {}\n   138\t        for name, m in ((\"U_abs_alpha2 (D1+D2)\", np.isin(des, (\"D1\", \"D2\")) & (alp == 2.0)),\n   139\t                        (\"U_bf_family_alpha2 (D3+D4+D5)\", np.isin(des, (\"D3\", \"D4\", \"D5\")) & (alp == 2.0))):\n   140\t            if m.sum() >= 40:\n   141\t                strata[name] = {\"n\": int(m.sum()), \"n_attempted\": int(y[m].sum()),\n   142\t                                \"cv_auc_log_norms\": cv_auc(norms[m], y[m], pca=None),\n   143\t                                \"cv_auc_R35_direction\": cv_auc(unit_rows(R[m]), y[m], pca=16),\n   144\t                                \"cv_auc_gen1_direction\": cv_auc(unit_rows(G[m]), y[m], pca=16)}\n   145\t        res[\"fixed_dose_strata\"] = strata\n   146\t        tmpl = np.array([rows[k][\"template\"] for k in sel])\n   147\t        Ru = unit_rows(R)\n   148\t        absm = np.isin(des, (\"D1\", \"D2\")) & np.isin(alp, (1.0, 2.0))\n   149\t        own = np.zeros(len(sel))\n   150\t        for fold in ((\"W1\", \"W2\"), (\"W3\", \"W4\", \"W5\")):\n   151\t            tr = absm & ~np.isin(tmpl, fold)\n   152\t            te = absm & np.isin(tmpl, fold)\n   153\t            ax_ = Ru[tr & (y == 1)].mean(0) - Ru[tr & (y == 0)].mean(0)\n   154\t            own[te] = Ru[te] @ (ax_ / np.linalg.norm(ax_))\n   155\t        axis = Ru[absm & (y == 1)].mean(0) - Ru[absm & (y == 0)].mean(0)\n   156\t        axis /= np.linalg.norm(axis)\n   157\t        proj = Ru @ axis\n   158\t        bfm = np.isin(des, (\"D3\", \"D4\", \"D5\"))\n   159\t        res[\"escape_axis\"] = {\"built_on\": \"U_abs designs D1, D2 at alpha 1-2 (attempted vs default)\",\n   160\t                              \"auc_heldout_templates_U_abs\": auc(own[absm], y[absm]),\n   161\t                              \"auc_transfer_to_U_bf_family\": auc(proj[bfm], y[bfm]),\n   162\t                              \"mean_projection_by_design_alpha\": {\n   163\t                                  f\"{d}_a{a:g}\": float(proj[(des == d) & (alp == a)].mean())\n   164\t                                  for d in (\"D1\", \"D2\", \"D3\", \"D4\", \"D5\") for a in sorted(set(alp))\n   165\t                                  if ((des == d) & (alp == a)).any()},\n   166\t                              \"mean_projection_attempted_vs_default_U_bf\": [\n   167\t                                  float(proj[bfm & (y == 1)].mean()) if (bfm & (y == 1)).any() else None,\n   168\t                                  float(proj[bfm & (y == 0)].mean()) if (bfm & (y == 0)).any() else None]}\n   169\t        out[task] = res\n   170\t        rn = np.linalg.norm(R, axis=1)\n   171\t        for d, mk in ((\"D1\", \"o\"), (\"D2\", \"s\"), (\"D3\", \"^\"), (\"D4\", \"v\"), (\"D5\", \"D\")):\n   172\t            for yy, c in ((0, \"#9a9a9a\"), (1, \"#1b6ca8\" if d in (\"D1\", \"D2\") else \"#d1495b\")):\n   173\t                m = (des == d) & (y == yy)\n   174\t                if m.any():\n   175\t                    ax.scatter(rn[m], proj[m], marker=mk, s=14, color=c, alpha=0.7, edgecolor=\"none\",\n   176\t                               label=f\"{d} {'attempted' if yy else 'default'}\")\n   177\t        ax.set_xscale(\"log\")\n   178\t        ax.set_xlabel(\"||delta h|| at block 35, read position (log)\")\n   179\t        ax.set_ylabel(\"projection of unit delta h on the U_abs escape axis\")\n   180\t        ax.set_title(f\"{task}: axis AUC held-out {res['escape_axis']['auc_heldout_templates_U_abs']:.2f}, \"\n   181\t                     f\"transfer to U_bf {res['escape_axis']['auc_transfer_to_U_bf_family'] or float('nan'):.2f}\")\n   182\t        ax.legend(frameon=False, fontsize=6, ncol=2, loc=\"lower right\")\n   183\t    fig.suptitle(\"F7 (exploratory E2): projection on an escape axis built from U_abs rows vs the size of the downstream displacement\",\n   184\t                 y=1.02)\n   185\t    fig.savefig(FIGS / \"F7_escape_axis.pdf\", bbox_inches=\"tight\")\n   186\t    fig.savefig(FIGS / \"F7_escape_axis.png\", bbox_inches=\"tight\", dpi=170)\n   187\t    plt.close(fig)\n   188\t    out[\"slot_concordance\"] = slot_concordance()\n   189\t    write_json(RESULTS / \"e2_geometry.json\", out)\n   190\t    logger.info({t: {k: v for k, v in r.items() if k not in (\"escape_axis\",)} for t, r in out.items()})\n   191\t    logger.info({t: {k: v for k, v in r[\"escape_axis\"].items() if k != \"mean_projection_by_design_alpha\"}\n   192\t                 for t, r in out.items()})\n   193\t\n   194\t\n   195\tif __name__ == \"__main__\":\n   196\t    main()", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [45] TOOL CALL — Bash · 2026-10-26 13:03:27 UTC

```
Read outputs module and T10 catalogue entry:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36; cat -n $A/src/outputs_k.py | head -120; echo ====CAT; grep -n "T10" -A8 $A/vendor/exp22/inputs/exp11/bench/common/catalogue.py | head -40
```

### [46] TOOL RESULT — Bash · 2026-10-26 13:03:27 UTC

```
{"stdout": "     1\t#!/usr/bin/env python3\n     2\t\"\"\"method_out.json (exp_gen_sol_out schema): one example per CRN slot and cell family, with predict_<arm> =\n     3\t'<label>|<passed>' for every arm that ran on that slot; input = the slot's twin prompt (user text), output = the\n     4\tclean twin's own 'label|passed' on the same slot (the unpushed reference). Metadata = every analysis, gate, commit\n     5\tand deviation of the artifact.\n     6\t\n     7\tDatasets: k_2x2 (S1: D1-D5 per task x alpha x slot), k_profile (S2: D1, P_top, P_rest, P_shuf), k_prices (S3: PN* at\n     8\tD* = D1 and the five knobs, with the source of each knob's rows), engine_check (S0 twins vs exp30), e1_sweep\n     9\t(exploratory dose sweep of the ban-free unit).\n    10\t\n    11\tusage: .venv/bin/python src/outputs_k.py\n    12\t\"\"\"\n    13\t\n    14\tfrom __future__ import annotations\n    15\t\n    16\timport json\n    17\timport sys\n    18\tfrom pathlib import Path\n    19\tfrom typing import Any\n    20\t\n    21\tfrom loguru import logger\n    22\t\n    23\tsys.path.insert(0, str(Path(__file__).resolve().parent))\n    24\t\n    25\timport k_cfg as K  # noqa: E402\n    26\tfrom k_cfg import LABELS, RESULTS, read_json, read_jsonl  # noqa: E402\n    27\t\n    28\tOUT = K.ROOT / \"method_out.json\"\n    29\t\n    30\t\n    31\tdef prompts() -> dict[tuple[str, str], str]:\n    32\t    out = {}\n    33\t    for line in open(K.V22 / \"prompts\" / \"prompts4.jsonl\"):\n    34\t        r = json.loads(line)\n    35\t        if r[\"kind\"] == \"twin\":\n    36\t            out[(r[\"task\"], r[\"template_id\"])] = r[\"user_text\"]\n    37\t    return out\n    38\t\n    39\t\n    40\tdef lab_index() -> dict[tuple[str, str, str, int], str]:\n    41\t    labs = {l[\"key\"]: l for l in read_jsonl(LABELS)}\n    42\t    idx = {}\n    43\t    for name in (\"raw_k.jsonl\", \"knobs_norm.jsonl\", \"reuse_exp27.jsonl\"):\n    44\t        for r in read_jsonl(K.RAW_DIR / name):\n    45\t            l = labs.get(K.row_key(r))\n    46\t            if l is not None:\n    47\t                idx[(r[\"task\"], r[\"template\"], r[\"arm\"], int(r[\"sample_id\"]))] = f\"{l['label']}|{bool(l['passed'])}\"\n    48\t    return idx\n    49\t\n    50\t\n    51\tdef safe(arm: str) -> str:\n    52\t    return arm.replace(\"E27:\", \"E27_\").replace(\".\", \"_\").replace(\"*\", \"star\")\n    53\t\n    54\t\n    55\tdef ex(pr: dict, idx: dict, task: str, w: str, k: int, arms: dict[str, str], meta: dict[str, Any]) -> dict | None:\n    56\t    preds = {f\"predict_{name}\": idx[(task, w, arm, k)] for name, arm in arms.items() if (task, w, arm, k) in idx}\n    57\t    if not preds:\n    58\t        return None\n    59\t    e = {\"input\": f\"[task {task} | template {w} | CRN slot k={k}]\\n{pr[(task, w)]}\",\n    60\t         \"output\": idx.get((task, w, \"TWIN\", k), \"unlabelled\"), **preds,\n    61\t         \"metadata_task\": task, \"metadata_template\": w, \"metadata_k\": k,\n    62\t         \"metadata_uniform_seed\": K.stable_seed(task, w, k)}\n    63\t    e.update({f\"metadata_{k_}\": v for k_, v in meta.items()})\n    64\t    return e\n    65\t\n    66\t\n    67\tdef build() -> dict[str, Any]:\n    68\t    pr = prompts()\n    69\t    idx = lab_index()\n    70\t    ds: dict[str, list] = {\"k_2x2\": [], \"k_profile\": [], \"k_prices\": [], \"engine_check\": [], \"e1_sweep\": [],\n    71\t                           \"e3_replicate\": []}\n    72\t    for task in K.S1_TASKS:\n    73\t        for alpha in (1, 2):\n    74\t            ks = K.K20 if (task == \"T2\" and alpha == 2) else K.K10\n    75\t            for w in K.TEMPLATES:\n    76\t                for k in ks:\n    77\t                    e = ex(pr, idx, task, w, k, {d: f\"{d}_a{alpha}\" for d in (\"D1\", \"D2\", \"D3\", \"D4\", \"D5\")},\n    78\t                           {\"alpha\": alpha, \"family\": \"S1\",\n    79\t                            \"designs\": \"D1=U_abs x S4, D2=U_abs x S5, D3=U_bf x S4, D4=U_bf x S5, D5=U_bf* x S4\"})\n    80\t                    if e:\n    81\t                        ds[\"k_2x2\"].append(e)\n    82\t        for w in K.TEMPLATES:\n    83\t            for k in K.K10:\n    84\t                e = ex(pr, idx, task, w, k, {\"D1\": \"D1_a2\", \"PTOP\": \"PTOP_a2\", \"PREST\": \"PREST_a2\",\n    85\t                                             \"PSHUF\": \"PSHUF_a2\"}, {\"alpha\": 2, \"family\": \"S2\"})\n    86\t                if e:\n    87\t                    ds[\"k_profile\"].append(e)\n    88\t                e = ex(pr, idx, task, w, k, {f\"D3_a{a}\": f\"D3_a{a}\" for a in (1, 2, 3, 4, 6)} |\n    89\t                       {\"D1_a1\": \"D1_a1\", \"D1_a2\": \"D1_a2\"}, {\"family\": \"E1 (exploratory)\"})\n    90\t                if e:\n    91\t                    ds[\"e1_sweep\"].append(e)\n    92\t    for w in K.TEMPLATES:\n    93\t        for k in range(10, 20):\n    94\t            e = ex(pr, idx, \"T10\", w, k, {d: f\"{d}_a2\" for d in (\"D1\", \"D2\", \"D3\", \"D4\", \"D5\", \"PTOP\", \"PREST\",\n    95\t                                                                  \"PSHUF\")}, {\"alpha\": 2, \"family\": \"E3 fresh slots\"})\n    96\t            if e:\n    97\t                ds[\"e3_replicate\"].append(e)\n    98\t        for k in K.K10:\n    99\t            e = ex(pr, idx, \"T03\", w, k, {d: f\"{d}_a2\" for d in (\"D1\", \"D2\", \"D3\", \"D4\")},\n   100\t                   {\"alpha\": 2, \"family\": \"E3 T03 2x2\"})\n   101\t            if e:\n   102\t                ds[\"e3_replicate\"].append(e)\n   103\t    s3 = read_json(RESULTS / \"s3_prices.json\")\n   104\t    dstar = s3[\"D_star\"]\n   105\t    for task in K.D5_TASKS:\n   106\t        src = s3[\"knob_sources\"][task]\n   107\t        for w in K.TEMPLATES:\n   108\t            for k in K.K10:\n   109\t                arms = {\"PNstar_a1\": f\"{dstar}_a1\", \"PNstar_a2\": f\"{dstar}_a2\"}\n   110\t                arms.update({safe(knob): arm for knob, arm in src.items()})\n   111\t                e = ex(pr, idx, task, w, k, arms, {\"family\": \"S3\", \"D_star\": dstar,\n   112\t                                                   \"knob_row_sources\": json.dumps(src)})\n   113\t                if e:\n   114\t                    ds[\"k_prices\"].append(e)\n   115\t    e30 = {}\n   116\t    for l in read_jsonl(K.E30 / \"data\" / \"labels.jsonl\"):\n   117\t        if l.get(\"arm\") == \"TWIN\":\n   118\t            e30[(l[\"task\"], l[\"template\"], int(l[\"slot\"]))] = f\"{l['label']}|{bool(l['passed'])}\"\n   119\t    for task in K.D5_TASKS:\n   120\t        for w in K.TEMPLATES:\n====CAT\n37:TASK_ORDER = [\"T03\", \"T05\", \"T06\", \"T14\", \"T10\", \"T08\", \"T04\", \"T11\", \"T13\", \"R1\", \"R2\", \"R3\", \"R6\"]\n38-\n39-TASKS: dict[str, dict] = {\n40-    \"T03\": {\n41-        \"task_id\": \"T03_kth_smallest\",\n42-        \"leetcode_ids\": [215],\n43-        \"signature\": \"solve(nums, k)\",\n44-        \"description\": (\n45-            \"Task: write a Python function solve(nums, k) that returns the k-th smallest value in nums. \"\n--\n173:    \"T10\": {\n174:        \"task_id\": \"T10_connected_components\",\n175-        \"leetcode_ids\": [547, 323],\n176-        \"signature\": \"solve(n, edges)\",\n177-        \"description\": (\n178-            \"Task: write a Python function solve(n, edges) that returns the number of connected components \"\n179-            \"of an undirected graph. The nodes are the integers 0 to n - 1, with 1 <= n <= 300. The argument \"\n180-            \"edges is a list of pairs [u, v] with 0 <= u, v < n and u != v, each joining nodes u and v; \"\n181-            \"0 <= len(edges) <= 1500 and no pair of nodes is joined twice. A node with no edges forms a \"\n182-            \"component on its own.\"", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [47] THINKING · 2026-10-26 13:04:07 UTC

```
I'll check the format and size of the fp16 block-35 displacement vectors in `cache/disp`, along with the unit dumps, 36-block profiles, and anchor labels, since E2's vector analyses needs these for plotting actual activation space.
```

### [48] TOOL CALL — Bash · 2026-10-26 13:04:07 UTC

```
Inspect unit dumps and displacement vector cache:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36; du -sh $A/cache/disp $A/cache/units; ls $A/cache/disp | head -5; ls $A/cache/disp | wc -l; ls -la $A/cache/units; python3 -c "
import numpy as np, glob
z=np.load('$A/cache/units/T10.npz', allow_pickle=False)
for k in z.files: print(k, z[k].shape, z[k].dtype, (z[k][:3] if z[k].dtype.kind in 'U' else ''))
fs=sorted(glob.glob('$A/cache/disp/T10_*.npz'))
print('n T10 disp files', len(fs))
z=np.load(fs[0]); print(fs[0].split('/')[-1], len(z.files)); 
for k in z.files[:6]: print(' ', k, z[k].shape, z[k].dtype)
"
```

### [49] TOOL RESULT — Bash · 2026-10-26 13:04:07 UTC

```
{"stdout": "73M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36/cache/disp\n1.7M\t/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36/cache/units\nT03_W1_1792676914022.npz\nT03_W1_1792676918643.npz\nT03_W1_1792679851774.npz\nT03_W1_1792679857566.npz\nT03_W1_1792679862097.npz\n255\ntotal 3693\ndrwxrwxrwx 2 aii-agent aii-agent 1068737 Oct 22 14:06 .\ndrwxrwxrwx 4 aii-agent aii-agent 2007115 Oct 22 14:06 ..\n-rw-rw-rw- 1 aii-agent aii-agent  136613 Oct 22 14:06 T03.npz\n-rw-rw-rw- 1 aii-agent aii-agent  123955 Oct 22 14:06 T05.npz\n-rw-rw-rw- 1 aii-agent aii-agent  178315 Oct 22 14:06 T1.npz\n-rw-rw-rw- 1 aii-agent aii-agent  119689 Oct 22 14:06 T10.npz\n-rw-rw-rw- 1 aii-agent aii-agent  145304 Oct 22 14:06 T2.npz\nU_abs (12, 145) float32 \nP_top (12, 145) float32 \nP_rest (12, 145) float32 \nP_shuf (12, 145) float32 \nmask_top (12, 145) bool \nU_bf_W1 (12, 145) float32 \nU_bf_star_W1 (12, 145) float32 \nh_norm_W1 (12, 145) float32 \nU_bf_W2 (12, 145) float32 \nU_bf_star_W2 (12, 145) float32 \nh_norm_W2 (12, 145) float32 \nU_bf_W3 (12, 145) float32 \nU_bf_star_W3 (12, 145) float32 \nh_norm_W3 (12, 145) float32 \nU_bf_W4 (12, 145) float32 \nU_bf_star_W4 (12, 145) float32 \nh_norm_W4 (12, 145) float32 \nU_bf_W5 (12, 145) float32 \nU_bf_star_W5 (12, 145) float32 \nh_norm_W5 (12, 145) float32 \ntokens_W1 (145,) <U12 ['Task' ':' ' write']\ntokens_W2 (145,) <U12 ['Task' ':' ' write']\ntokens_W3 (145,) <U12 ['Task' ':' ' write']\ntokens_W4 (145,) <U12 ['Task' ':' ' write']\ntokens_W5 (145,) <U12 ['Task' ':' ' write']\nn T10 disp files 115\nT10_W1_1792676034670.npz 48\n  T10|W1|D1_a2|0::smean23 (4096,) float16\n  T10|W1|D1_a2|0::smean35 (4096,) float16\n  T10|W1|D1_a2|0::R35 (4096,) float16\n  T10|W1|D1_a2|0::gen1_35 (4096,) float16\n  T10|W1|D4_a2|0::smean23 (4096,) float16\n  T10|W1|D4_a2|0::smean35 (4096,) float16", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [50] TOOL CALL — Bash · 2026-10-26 13:04:07 UTC

```
Inspect displacement profiles, anchor labels, r_Q table, prompt:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36; head -c 1500 $A/data/realised_disp.jsonl; echo; echo ===E29; ls -la $A/inputs/exp29 $A/inputs/exp29/data | head; head -c 800 $A/inputs/exp29/data/labels.jsonl; echo; echo ===E23; ls $A/inputs/exp23/results/; python3 -c "
import json; q=json.load(open('$A/inputs/exp23/results/qwen_ratio.json'))['r_Q']; print(list(q.items())[:3], len(q))"; echo ===PROMPTS; python3 -c "
import json
for l in open('$A/vendor/exp22/prompts/prompts4.jsonl'):
    r=json.loads(l)
    if r['kind']=='twin' and r['task']=='T10':
        print({k:(v if k!='ids' else len(v)) for k,v in r.items() if k!='user_text'}); print(r['user_text'][:3000]); break
"
```

### [51] TOOL RESULT — Bash · 2026-10-26 13:04:07 UTC

````
{"stdout": "{\"key\": \"T10|W1|D1_a2|0\", \"task\": \"T10\", \"template\": \"W1\", \"arm\": \"D1_a2\", \"sample_id\": 0, \"design\": \"D1\", \"alpha\": 2.0, \"spec_mean\": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 13.7549, 16.5425, 19.8474, 23.0492, 26.7972, 31.4179, 36.481, 43.9553, 49.228, 55.8226, 67.0587, 79.9859, 92.3332, 101.8745, 111.9437, 124.2357, 137.0078, 149.2791, 173.4957, 188.6519, 206.0102, 210.6548, 255.0483, 269.5158], \"spec_pos\": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 13.7557, 18.2843, 23.2453, 28.1753, 33.8041, 40.4696, 48.3399, 58.7249, 67.3044, 78.458, 93.3677, 113.0383, 134.3844, 153.1044, 173.5725, 199.4492, 229.3968, 259.882, 304.2231, 342.468, 383.0237, 420.8813, 499.0512, 636.7249], \"R\": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.6123, 2.7268, 3.3502, 5.8576, 7.4227, 10.2317, 13.5951, 18.0422, 24.0645, 26.6069, 36.7941, 54.8999, 65.7102, 83.2739, 95.5992, 109.911, 127.5087, 146.5308, 168.9894, 187.0275, 210.5918, 235.1356, 247.5732], \"rel_err_along_u\": {\"12\": 0.000143, \"13\": 0.000115, \"14\": 0.0001138, \"15\": 9.94e-05, \"16\": 9.41e-05, \"17\": 9.05e-05, \"18\": 9.62e-05, \"19\": 9.38e-05, \"20\": 7.36e-05, \"21\": 8.19e-05, \"22\": 6.97e-05, \"23\": 9.13e-05}, \"rel_err_mean\": 9.684362460878522e-05, \"rel_err_max\": 0.00014300890325102955, \"masked_b12_max_abs_disp\": null, \"gen1\": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.7061, 2.9092, 4.3968, 5.5448, 7.377, 10.6166, 14.5171, 17.7626, 21.4068, 23.9786, 29.8639, 43.356\n===E29\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36/inputs/exp29:\ntotal 9814\ndrwxrwxrwx  6 aii-agent aii-agent 2003085 Oct 22 13:11 .\ndrwxrwxrwx 13 aii-agent aii-agent 2017522 Oct 22 13:11 ..\ndrwxrwxrwx  3 aii-agent aii-agent 2001673 Oct 22 13:11 data\ndrwxrwxrwx  3 aii-agent aii-agent 2001388 Oct 22 13:11 inputs\ndrwxrwxrwx  2 aii-agent aii-agent 1001949 Oct 22 13:11 results\ndrwxrwxrwx  2 aii-agent aii-agent 1022031 Oct 22 12:14 src\n\n/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36/inputs/exp29/data:\n{\"key\": \"a|T10|W1|TWIN|0\", \"task\": \"T10\", \"template\": \"W1\", \"arm\": \"TWIN\", \"sample_id\": 0, \"block_id\": \"a:REPRO:T10:W1:1792646989833\", \"label\": \"union_find\", \"labeller_source\": \"runtime+ast\", \"passed\": true, \"valid\": true, \"runtime_label\": \"union_find\", \"ast_label\": \"union_find\", \"judge_label\": null, \"fallback_label\": \"union_find\", \"n_pass\": 57, \"n_cases\": 57, \"code_sha256\": \"aaef86bfc0e35a8aaf56c6c7f72229b15e3940422cb6498aae19c15e11aa944f\", \"code\": \"def solve(n, edges):\\n    parent = list(range(n))\\n    \\n    def find(x):\\n        if parent[x] != x:\\n            parent[x] = find(parent[x])\\n        return parent[x]\\n    \\n    def union(x, y):\\n        rootX = find(x)\\n        rootY = find(y)\\n        if rootX != rootY:\\n            parent[rootY] = rootX\\n    \\n    for u, v in edges:\\n    \n===E23\nqwen_ratio.json\n[('12', {'median': 0.06980449706315994, 'q25': 0.05178554356098175, 'q75': 0.09988057613372803, 'depth': 0.3611111111111111, 'n': 10515}), ('13', {'median': 0.07784001529216766, 'q25': 0.058433447033166885, 'q75': 0.11136050522327423, 'depth': 0.3888888888888889, 'n': 10515}), ('14', {'median': 0.08328081667423248, 'q25': 0.062419191002845764, 'q75': 0.1209300309419632, 'depth': 0.4166666666666667, 'n': 10515})] 12\n===PROMPTS\n{'pid': 'T10|twin|-|W1|-', 'task': 'T10', 'kind': 'twin', 'segment': 'Do not use ship for this task. . . . . . . .', 'ids': 172, 'P': 172, 'p0': 3, 'p1': 18, 'spec_end': 163, 'prompt_sha256': '77b9a34abbbb189b14b9ddd9aedcb08be8a7ff167988282ac819a1df0749f36c', 'template_id': 'W1', 'X': None, 'noun': 'ship', 'n_pad': 7, 'source': 'exp17 prompts.jsonl'}\nDo not use ship for this task. . . . . . . .\n\nTask: write a Python function solve(n, edges) that returns the number of connected components of an undirected graph. The nodes are the integers 0 to n - 1, with 1 <= n <= 300. The argument edges is a list of pairs [u, v] with 0 <= u, v < n and u != v, each joining nodes u and v; 0 <= len(edges) <= 1500 and no pair of nodes is joined twice. A node with no edges forms a component on its own.\n\nUse only the Python standard library. Return only one ```python code block containing the function solve and any helpers, with no example usage and no explanation.", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
````

### [52] THINKING · 2026-10-26 13:04:17 UTC

```
U_abs turns out to be a [12 blocks × 145 spec tokens] map, with each 4096-d fp16 displacement vector matched against a decoy prompt of the same length. I'll now check `figures_k.py` to reuse the original plotting code and review two of the original figures.
```

### [53] TOOL CALL — Bash · 2026-10-26 13:04:17 UTC

```
Read the figures module:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36; cat -n $A/src/figures_k.py
```

### [54] TOOL RESULT — Bash · 2026-10-26 13:04:17 UTC

```
{"stdout": "     1\t#!/usr/bin/env python3\n     2\t\"\"\"Figures of step K (PDF + PNG in figures/), drawn only from data/ and results/ files.\n     3\t\n     4\tF1 s1_interaction      2x2 shares (Y, Wilson 95%) per task and alpha: unit on x, seeds as lines, D5 beside\n     5\tF2 unit_heatmaps       dose units [block 12-23 x spec token] in activation-norm units (T10 W1): U_abs, U_bf, U_bf*,\n     6\t                       P_top, P_rest, P_shuf, plus the twin's residual norm ||h_twin|| for scale\n     7\tF3 displacement_blocks realised displacement ||delta h|| vs block 0-35 (spec-mean, read position R, generated pos. 1)\n     8\t                       per design at alpha 2, mean over rows (log y)\n     9\tF4 escape_vs_disp      per-sample outcome (escaped = Y) vs block-35 R displacement norm, by design (alpha 1, 2)\n    10\tF5 pca_disp35          PCA of block-35 R displacement vectors (actual residual coordinates, fp16 logs) per task,\n    11\t                       colour = realised algorithm, marker = design\n    12\tF6 price_frontiers     pass cost vs best reachable correct-only Hill-1 per task for PN* and the knobs\n    13\tE1 dose_response       exploratory: share Y and pass vs alpha for U_bf (D3) and U_abs (D1), x = alpha and x = block-35\n    14\t                       spec-mean displacement\n    15\t\n    16\tusage: .venv/bin/python src/figures_k.py\n    17\t\"\"\"\n    18\t\n    19\tfrom __future__ import annotations\n    20\t\n    21\timport sys\n    22\tfrom collections import defaultdict\n    23\tfrom pathlib import Path\n    24\t\n    25\timport matplotlib\n    26\t\n    27\tmatplotlib.use(\"Agg\")\n    28\timport matplotlib.pyplot as plt  # noqa: E402\n    29\timport numpy as np  # noqa: E402\n    30\tfrom loguru import logger  # noqa: E402\n    31\t\n    32\tsys.path.insert(0, str(Path(__file__).resolve().parent))\n    33\t\n    34\timport k_cfg as K  # noqa: E402\n    35\tfrom k_cfg import FIGS, RESULTS, read_json, read_jsonl, wilson  # noqa: E402\n    36\t\n    37\tplt.rcParams.update({\"font.size\": 9, \"axes.titlesize\": 10, \"axes.labelsize\": 9, \"legend.fontsize\": 8,\n    38\t                     \"pdf.fonttype\": 42, \"ps.fonttype\": 42, \"axes.spines.top\": False, \"axes.spines.right\": False})\n    39\tCOL = {\"D1\": \"#1b6ca8\", \"D2\": \"#5fa8d3\", \"D3\": \"#d1495b\", \"D4\": \"#edae49\", \"D5\": \"#66a182\", \"PTOP\": \"#2e294e\",\n    40\t       \"PREST\": \"#8d6a9f\", \"PSHUF\": \"#999999\", \"TWIN\": \"#444444\"}\n    41\tNAME = {\"D1\": \"D1 U_abs x S4\", \"D2\": \"D2 U_abs x S5\", \"D3\": \"D3 U_bf x S4\", \"D4\": \"D4 U_bf x S5\",\n    42\t        \"D5\": \"D5 U_bf* x S4\", \"PTOP\": \"P_top\", \"PREST\": \"P_rest\", \"PSHUF\": \"P_shuf\"}\n    43\t\n    44\t\n    45\tdef save(fig, name: str) -> None:\n    46\t    fig.savefig(FIGS / f\"{name}.pdf\", bbox_inches=\"tight\")\n    47\t    fig.savefig(FIGS / f\"{name}.png\", bbox_inches=\"tight\", dpi=170)\n    48\t    plt.close(fig)\n    49\t    logger.info(f\"figure {name}\")\n    50\t\n    51\t\n    52\tdef f1(rows) -> None:\n    53\t    import analysis_k as A\n    54\t\n    55\t    fig, axes = plt.subplots(1, 4, figsize=(12, 3.2), sharey=True)\n    56\t    for ax, (task, alpha) in zip(axes, [(\"T10\", 1.0), (\"T10\", 2.0), (\"T2\", 1.0), (\"T2\", 2.0)]):\n    57\t        a = \"a1\" if alpha == 1 else \"a2\"\n    58\t        for seeds, (du, db), ls in ((\"S4\", (\"D1\", \"D3\"), \"-\"), (\"S5\", (\"D2\", \"D4\"), \"--\")):\n    59\t            ys, lo, hi = [], [], []\n    60\t            for d in (du, db):\n    61\t                c = A.cell(rows, task, f\"{d}_{a}\", A.COMMITTED_KS[(task, alpha)])\n    62\t                k = sum(r[\"Y\"] for r in c.values())\n    63\t                n = len(c)\n    64\t                ys.append(k / n if n else np.nan)\n    65\t                l, h = wilson(k, n)\n    66\t                lo.append(max(0.0, ys[-1] - l))\n    67\t                hi.append(max(0.0, h - ys[-1]))\n    68\t            x = np.array([0, 1]) + (-0.04 if seeds == \"S4\" else 0.04)\n    69\t            ax.errorbar(x, ys, yerr=[lo, hi], fmt=\"o\", ls=ls, color=\"#1b6ca8\" if seeds == \"S4\" else \"#d1495b\",\n    70\t                        capsize=3, label=f\"seeds {seeds}\")\n    71\t        c5 = A.cell(rows, task, f\"D5_{a}\", A.COMMITTED_KS[(task, alpha)])\n    72\t        if c5:\n    73\t            k = sum(r[\"Y\"] for r in c5.values())\n    74\t            n = len(c5)\n    75\t            l, h = wilson(k, n)\n    76\t            ax.errorbar([1.45], [k / n], yerr=[[max(0.0, k / n - l)], [max(0.0, h - k / n)]], fmt=\"s\", color=COL[\"D5\"], capsize=3,\n    77\t                        label=\"U_bf* x S4 (D5)\")\n    78\t        tw = A.cell(rows, task, \"TWIN\", K.K20 if task == \"T2\" else K.K10)\n    79\t        ax.axhline(sum(r[\"Y\"] for r in tw.values()) / max(len(tw), 1), color=\"#888\", lw=0.8, ls=\":\", label=\"twin\")\n    80\t        ax.set_xticks([0, 1, 1.45])\n    81\t        ax.set_xticklabels([\"U_abs\", \"U_bf\", \"U_bf*\"])\n    82\t        ax.set_title(f\"{task}, alpha {int(alpha)} (N {len(A.cell(rows, task, f'D1_{a}', A.COMMITTED_KS[(task, alpha)]))}/design)\")\n    83\t        ax.set_xlim(-0.3, 1.7)\n    84\t    axes[0].set_ylabel(\"share correct named off-default (Y)\")\n    85\t    axes[0].legend(loc=\"upper right\", frameon=False)\n    86\t    fig.suptitle(\"S1: the dose unit, not the seeds, decides whether plan noise moves the algorithm\", y=1.03)\n    87\t    save(fig, \"F1_s1_interaction\")\n    88\t\n    89\t\n    90\tdef f2() -> None:\n    91\t    p = K.CACHE / \"units\" / \"T10.npz\"\n    92\t    if not p.exists():\n    93\t        logger.warning(\"F2 skipped: cache/units/T10.npz missing (run src/dump_units.py)\")\n    94\t        return\n    95\t    z = np.load(p, allow_pickle=False)\n    96\t    toks = [t.replace(\"\\n\", \"\\\\n\") for t in z[\"tokens_W1\"]]\n    97\t    mats = [(\"||h_twin|| (residual norm)\", z[\"h_norm_W1\"]), (\"U_abs (ban displacement n[l,p])\", z[\"U_abs\"]),\n    98\t            (\"U_bf = ||h_twin|| x r_Q(l)\", z[\"U_bf_W1\"]), (\"U_bf* (U_abs per-block energy)\", z[\"U_bf_star_W1\"]),\n    99\t            (\"P_top (top-quartile cells)\", z[\"P_top\"]), (\"P_rest (other cells)\", z[\"P_rest\"]),\n   100\t            (\"P_shuf (positions permuted)\", z[\"P_shuf\"])]\n   101\t    fig, axes = plt.subplots(len(mats), 1, figsize=(13, 2.0 * len(mats)), sharex=True)\n   102\t    vmax = max(float(np.percentile(m, 99.5)) for _, m in mats[1:])\n   103\t    for ax, (title, m) in zip(axes, mats):\n   104\t        im = ax.imshow(m, aspect=\"auto\", cmap=\"magma\", vmin=0, vmax=(None if title.startswith(\"||h\") else vmax),\n   105\t                       interpolation=\"nearest\")\n   106\t        ax.set_yticks(range(0, 12, 2))\n   107\t        ax.set_yticklabels([str(12 + i) for i in range(0, 12, 2)])\n   108\t        ax.set_ylabel(\"block\")\n   109\t        ax.set_title(title, loc=\"left\")\n   110\t        plt.colorbar(im, ax=ax, pad=0.01, fraction=0.02, label=\"norm\")\n   111\t    step = max(1, len(toks) // 60)\n   112\t    axes[-1].set_xticks(range(0, len(toks), step))\n   113\t    axes[-1].set_xticklabels([toks[i][:10] for i in range(0, len(toks), step)], rotation=90, fontsize=6)\n   114\t    axes[-1].set_xlabel(\"task-spec token (T10, template W1)\")\n   115\t    fig.suptitle(\"F2: dose units at blocks 12-23 x task-spec positions, in residual-stream norm units (T10 W1)\", y=0.995)\n   116\t    fig.tight_layout(rect=(0, 0, 1, 0.985))\n   117\t    save(fig, \"F2_unit_heatmaps\")\n   118\t\n   119\t\n   120\tdef f3() -> None:\n   121\t    rec = read_jsonl(K.REALISED)\n   122\t    fig, axes = plt.subplots(2, 3, figsize=(12, 6), sharex=True)\n   123\t    for i, task in enumerate((\"T10\", \"T2\")):\n   124\t        for j, (fld, lab) in enumerate(((\"spec_mean\", \"spec-mean\"), (\"R\", \"read position R\"),\n   125\t                                        (\"gen1\", \"generated position 1\"))):\n   126\t            ax = axes[i, j]\n   127\t            by = defaultdict(list)\n   128\t            for r in rec:\n   129\t                if r[\"task\"] == task and r.get(\"alpha\") == 2.0 and r.get(fld):\n   130\t                    by[r[\"design\"]].append(r[fld])\n   131\t            for d in (\"D1\", \"D2\", \"D3\", \"D4\", \"D5\", \"PTOP\", \"PREST\", \"PSHUF\"):\n   132\t                if by.get(d):\n   133\t                    m = np.mean(np.array(by[d]), axis=0)\n   134\t                    ax.plot(range(12, 36), m[12:], color=COL[d], label=NAME[d],\n   135\t                            ls=\"--\" if d in (\"D2\", \"D4\") else \"-\")\n   136\t            ax.set_yscale(\"log\")\n   137\t            ax.axvspan(12, 23, color=\"#eee\", zorder=0)\n   138\t            ax.set_title(f\"{task}: {lab}\")\n   139\t            if j == 0:\n   140\t                ax.set_ylabel(\"||delta h|| (residual units)\")\n   141\t            if i == 1:\n   142\t                ax.set_xlabel(\"block\")\n   143\t    axes[0, 0].legend(frameon=False, ncol=2, fontsize=7)\n   144\t    fig.suptitle(\"F3: realised displacement against the clean twin, alpha 2 (grey band = edited blocks; blocks 0-11 are exactly 0)\", y=1.01)\n   145\t    save(fig, \"F3_displacement_blocks\")\n   146\t\n   147\t\n   148\tdef f4(rows) -> None:\n   149\t    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))\n   150\t    rng = np.random.default_rng(0)\n   151\t    for ax, task in zip(axes, (\"T10\", \"T2\")):\n   152\t        for i, d in enumerate((\"D1\", \"D2\", \"D3\", \"D4\", \"D5\")):\n   153\t            sel = [r for r in rows if r[\"task\"] == task and r[\"design\"] == d and r.get(\"labelled\")\n   154\t                   and r.get(\"realised_disp\") and r[\"alpha\"] in (1.0, 2.0)]\n   155\t            if not sel:\n   156\t                continue\n   157\t            x = np.array([r[\"realised_disp\"][\"R_b35\"] for r in sel])\n   158\t            y = np.array([r[\"Y\"] for r in sel]) + rng.uniform(-0.12, 0.12, len(sel)) + (i - 2) * 0.03\n   159\t            ax.scatter(x, y, s=8, alpha=0.6, color=COL[d], label=NAME[d])\n   160\t        ax.set_yticks([0, 1])\n   161\t        ax.set_yticklabels([\"default / other\", \"escaped (Y=1)\"])\n   162\t        ax.set_xscale(\"log\")\n   163\t        ax.set_xlabel(\"||delta h|| at block 35, read position (log)\")\n   164\t        ax.set_title(f\"{task}: outcome vs block-35 R displacement (alpha 1, 2)\")\n   165\t    axes[0].legend(frameon=False, fontsize=7, loc=\"center right\")\n   166\t    save(fig, \"F4_escape_vs_disp\")\n   167\t\n   168\t\n   169\tdef f5(rows) -> None:\n   170\t    lab = {r[\"key\"]: r for r in rows}\n   171\t    vecs = defaultdict(dict)\n   172\t    for p in sorted((K.CACHE / \"disp\").glob(\"*.npz\")):\n   173\t        z = np.load(p)\n   174\t        for k in z.files:\n   175\t            key, kind = k.split(\"::\")\n   176\t            if kind == \"R35\":\n   177\t                vecs[key.split(\"|\")[0]][key] = z[k].astype(np.float32)\n   178\t    fig, axes = plt.subplots(1, 2, figsize=(12, 5))\n   179\t    marks = {\"D1\": \"o\", \"D2\": \"s\", \"D3\": \"^\", \"D4\": \"v\", \"D5\": \"D\", \"PTOP\": \"P\", \"PREST\": \"X\", \"PSHUF\": \"*\"}\n   180\t    cmap = {\"union_find\": \"#888888\", \"dfs\": \"#1b6ca8\", \"bfs\": \"#d1495b\", \"dijkstra\": \"#888888\", \"bf_spfa\": \"#1b6ca8\",\n   181\t            \"other\": \"#66a182\", \"invalid\": \"#edae49\", \"floyd\": \"#8d6a9f\", \"disputed\": \"#000000\"}\n   182\t    for ax, task in zip(axes, (\"T10\", \"T2\")):\n   183\t        keys = [k for k in vecs.get(task, {}) if k in lab and lab[k].get(\"labelled\") and lab[k][\"alpha\"] == 2.0\n   184\t                and lab[k][\"design\"] != \"PREST\"]     # P_rest breaks T2 (pass 0) and would own PC1\n   185\t        if len(keys) < 10:\n   186\t            continue\n   187\t        X = np.stack([vecs[task][k] for k in keys])\n   188\t        Xc = X - X.mean(0)\n   189\t        U, S, Vt = np.linalg.svd(Xc, full_matrices=False)\n   190\t        pcs = Xc @ Vt[:2].T\n   191\t        ev = (S ** 2) / (S ** 2).sum()\n   192\t        for d, mk in marks.items():\n   193\t            for lb, c in cmap.items():\n   194\t                idx = [i for i, k in enumerate(keys) if lab[k][\"design\"] == d and lab[k][\"label\"] == lb]\n   195\t                if idx:\n   196\t                    ax.scatter(pcs[idx, 0], pcs[idx, 1], marker=mk, s=18, color=c, alpha=0.75, edgecolor=\"none\")\n   197\t        from matplotlib.lines import Line2D\n   198\t        h1 = [Line2D([], [], marker=mk, ls=\"\", color=\"#333\", label=NAME[d]) for d, mk in marks.items()\n   199\t              if any(lab[k][\"design\"] == d for k in keys)]\n   200\t        h2 = [Line2D([], [], marker=\"o\", ls=\"\", color=c, label=lb) for lb, c in cmap.items()\n   201\t              if any(lab[k][\"label\"] == lb for k in keys)]\n   202\t        ax.legend(handles=h1 + h2, frameon=False, fontsize=6.5, ncol=2, loc=\"best\")\n   203\t        ax.set_xlabel(f\"PC1 ({100 * ev[0]:.1f}% var.) of delta h, block 35, read position\")\n   204\t        ax.set_ylabel(f\"PC2 ({100 * ev[1]:.1f}% var.)\")\n   205\t        ax.set_title(f\"{task}: block-35 displacement vectors at alpha 2 (n {len(keys)}; P_rest excluded)\")\n   206\t    save(fig, \"F5_pca_disp35\")\n   207\t\n   208\t\n   209\tdef f6() -> None:\n   210\t    p = RESULTS / \"s3_prices.json\"\n   211\t    if not p.exists():\n   212\t        logger.warning(\"F6 skipped: results/s3_prices.json missing\")\n   213\t        return\n   214\t    s3 = read_json(p)\n   215\t    fig, axes = plt.subplots(1, 5, figsize=(16, 3.4), sharey=True)\n   216\t    cc = {\"PN*\": \"#1b6ca8\", \"BINT\": \"#d1495b\", \"EAP\": \"#edae49\", \"IFG\": \"#66a182\", \"TEMP\": \"#999999\",\n   217\t          \"TOPK10\": \"#2e294e\"}\n   218\t    for ax, t in zip(axes, (\"T03\", \"T10\", \"T2\", \"T05\", \"T1\")):\n   219\t        for cls, v in s3[\"per_task\"].get(t, {}).items():\n   220\t            fr = v.get(\"frontier\") or []\n   221\t            if fr:\n   222\t                x = [max(f[0], -0.02) for f in fr]\n   223\t                y = [f[1] for f in fr]\n   224\t                ax.step(x, y, where=\"post\", color=cc.get(cls, \"#000\"), label=f\"{cls} (H5 {v['H5']:.2f})\",\n   225\t                        lw=2 if cls == \"PN*\" else 1.2)\n   226\t        ax.axvline(0.05, color=\"#888\", ls=\":\", lw=0.8)\n   227\t        ax.set_xlim(-0.02, 0.6)\n   228\t        ax.set_title(t)\n   229\t        ax.set_xlabel(\"pass cost (twin pass - mixture pass)\")\n   230\t        ax.legend(frameon=False, fontsize=6.5, loc=\"lower right\")\n   231\t    axes[0].set_ylabel(\"best correct-only Hill-1 (depth 25)\")\n   232\t    fig.suptitle(f\"F6: price frontiers, plan noise at D* = {s3['D_star']} vs iteration 5's knobs (dotted: 5-point budget)\",\n   233\t                 y=1.03)\n   234\t    save(fig, \"F6_price_frontiers\")\n   235\t\n   236\t\n   237\tdef e1() -> None:\n   238\t    p = RESULTS / \"e1_sweep.json\"\n   239\t    if not p.exists():\n   240\t        return\n   241\t    r = read_json(p)\n   242\t    fig, axes = plt.subplots(1, 2, figsize=(10, 3.4))\n   243\t    for task, mk in ((\"T10\", \"o\"), (\"T2\", \"s\")):\n   244\t        d = r.get(task, {})\n   245\t        for unit, arms, c in ((\"U_bf (D3)\", [\"D3_a1\", \"D3_a2\", \"D3_a3\", \"D3_a4\", \"D3_a6\"], \"#d1495b\"),\n   246\t                              (\"U_abs (D1)\", [\"D1_a1\", \"D1_a2\"], \"#1b6ca8\")):\n   247\t            xs = [float(a.split(\"_a\")[1]) for a in arms if a in d]\n   248\t            ys = [d[a][\"Y\"][\"share\"] for a in arms if a in d]\n   249\t            ps = [d[a][\"pass_rate\"] for a in arms if a in d]\n   250\t            dx = [d[a][\"realised_mean\"][\"S_b35\"] for a in arms if a in d and d[a].get(\"realised_mean\")]\n   251\t            axes[0].plot(xs, ys, marker=mk, color=c, label=f\"{task} {unit} share Y\")\n   252\t            axes[0].plot(xs, ps, marker=mk, color=c, ls=\":\", alpha=0.6, label=f\"{task} {unit} pass\")\n   253\t            if len(dx) == len(ys):\n   254\t                axes[1].plot(dx, ys, marker=mk, color=c, label=f\"{task} {unit}\")\n   255\t    axes[0].set_xlabel(\"alpha\")\n   256\t    axes[0].set_ylabel(\"share / pass rate\")\n   257\t    axes[0].legend(frameon=False, fontsize=6.5)\n   258\t    axes[1].set_xlabel(\"mean ||spec-mean delta h|| at block 35\")\n   259\t    axes[1].set_ylabel(\"share Y\")\n   260\t    axes[1].set_xscale(\"log\")\n   261\t    axes[1].legend(frameon=False, fontsize=7)\n   262\t    fig.suptitle(\"E1 (exploratory): ban-free unit dose response vs the absolute unit\", y=1.03)\n   263\t    save(fig, \"E1_dose_response\")\n   264\t\n   265\t\n   266\tdef e3() -> None:\n   267\t    p = RESULTS / \"e3_replicate.json\"\n   268\t    if not p.exists():\n   269\t        return\n   270\t    r = read_json(p)\n   271\t    fig, axes = plt.subplots(1, 3, figsize=(12, 3.3), sharey=True)\n   272\t    for ax, (lab, title) in zip(axes, ((\"T10_k0_9\", \"T10, committed slots k 0-9 (S1/S2)\"),\n   273\t                                       (\"T10_fresh_k10_19\", \"T10, fresh slots k 10-19 (E3)\"),\n   274\t                                       (\"T03_k0_9\", \"T03, k 0-9 (E3 2x2)\"))):\n   275\t        if lab == \"T10_k0_9\":\n   276\t            s1 = read_json(RESULTS / \"s1_2x2.json\")[\"cells\"]\n   277\t            s2 = read_json(RESULTS / \"s2_profile.json\")[\"T10\"][\"cells\"]\n   278\t            cells = {d: s1[f\"T10|{d}_a2\"] for d in (\"D1\", \"D2\", \"D3\", \"D4\", \"D5\")} | {\n   279\t                {\"PTOP\": \"PTOP\", \"PREST\": \"PREST\", \"PSHUF\": \"PSHUF\"}[k]: v for k, v in s2.items() if k != \"D1\"}\n   280\t        elif lab == \"T03_k0_9\":\n   281\t            cells = r[lab][\"cells\"]\n   282\t        else:\n   283\t            cells = r[lab][\"profiles\"][\"cells\"] | {d: v for d, v in r[lab].get(\"cells\", {}).items()}\n   284\t            s1c = {}\n   285\t            n_sl = r[lab][\"2x2|Y\"][\"n_slots\"]\n   286\t            for d in (\"D2\", \"D3\", \"D4\"):\n   287\t                t = r[lab][\"2x2|Y\"][\"shares\"][d]\n   288\t                s1c[d] = {\"Y\": {\"share\": t, \"wilson95\": list(wilson(int(round(t * n_sl)), n_sl))}}\n   289\t            cells = {**s1c, **cells}\n   290\t        order = [d for d in (\"D1\", \"D2\", \"D3\", \"D4\", \"D5\", \"PTOP\", \"PREST\", \"PSHUF\") if d in cells]\n   291\t        ys = [cells[d][\"Y\"][\"share\"] for d in order]\n   292\t        lo = [max(0.0, cells[d][\"Y\"][\"share\"] - cells[d][\"Y\"][\"wilson95\"][0]) for d in order]\n   293\t        hi = [max(0.0, cells[d][\"Y\"][\"wilson95\"][1] - cells[d][\"Y\"][\"share\"]) for d in order]\n   294\t        ax.bar(range(len(order)), ys, yerr=[lo, hi], color=[COL[d] for d in order], capsize=2)\n   295\t        ax.set_xticks(range(len(order)))\n   296\t        ax.set_xticklabels(order, rotation=45, fontsize=7)\n   297\t        ax.set_title(title)\n   298\t    axes[0].set_ylabel(\"share Y at alpha 2 (Wilson 95%)\")\n   299\t    fig.suptitle(\"E3 (exploratory): the unit effect and the top-quartile effect replicate on fresh slots and on T03\",\n   300\t                 y=1.04)\n   301\t    save(fig, \"E3_replicate\")\n   302\t\n   303\t\n   304\t@logger.catch(reraise=True)\n   305\tdef main() -> None:\n   306\t    import analysis_k as A\n   307\t\n   308\t    K.setup_logging(\"figures_k\")\n   309\t    rows = A.load_joined()\n   310\t    for fn in (lambda: f1(rows), f2, f3, lambda: f4(rows), lambda: f5(rows), f6, e1, e3):\n   311\t        try:\n   312\t            fn()\n   313\t        except (KeyError, ValueError, IndexError, FileNotFoundError) as e:\n   314\t            logger.exception(f\"figure failed: {e}\")\n   315\t\n   316\t\n   317\tif __name__ == \"__main__\":\n   318\t    main()", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [55] TOOL CALL — Read · 2026-10-26 13:04:17 UTC

```
/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36/figures/F5_pca_disp35.png
```

### [56] TOOL RESULT — Read · 2026-10-26 13:04:17 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [57] TOOL CALL — Read · 2026-10-26 13:04:17 UTC

```
/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36/figures/F1_s1_interaction.png
```

### [58] TOOL RESULT — Read · 2026-10-26 13:04:17 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [59] THINKING · 2026-10-26 13:06:11 UTC

```
I've mapped out method.py's 19-step pipeline (GPU vs CPU steps, tunable parameters like N_BOOT/N_FLIP, and the plan to rerun CPU analysis on real T10 data while verifying the GPU edit on toy tensors). Next I'll check the T10 catalogue, code sizes, and expected data file piece sizes.
```

### [60] TOOL CALL — Bash · 2026-10-26 13:06:11 UTC

```
Check T10 catalogue, row stats and local environment:
A=/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36; cd /tmp && python3 -I -c "
import sys, json
sys.path.insert(0, '$A/vendor/exp22/inputs/exp11')
from bench.common.catalogue import TASKS
print('T10 modes', TASKS['T10']['modes'])
print('T10 keys', list(TASKS['T10'].keys()))
rows=[json.loads(l) for l in open('$A/data/samples.jsonl')]
t10=[r for r in rows if r['task']=='T10' and (r['arm'] in ('TWIN',) or r['arm'].startswith(('D','P')))]
print('T10 rows (twin + designs)', len(t10))
import statistics
print('mean code len', statistics.mean(len(r.get('code') or '') for r in t10))
print('k values TWIN', sorted({r['k'] for r in t10 if r['arm']=='TWIN'}))
print('stages', sorted({r['stage'] for r in t10}))
print('labels', sorted({r['label'] for r in t10}))
print('labeller_source', sorted({r['labeller_source'] for r in t10}))
print('realised keys', [ (r['realised_disp'] or {}).keys() for r in t10 if r['realised_disp']][:1])
"; echo; env | grep -iE "PIP_CACHE|UV_CACHE|HF_HOME" ; which uv; uv --version; ls /usr/local/bin/python3.12; nproc; free -g | head -2
```

### [61] TOOL RESULT — Bash · 2026-10-26 13:06:11 UTC

```
{"stdout": "T10 modes {'bfs': ('breadth-first search (BFS)', 'start a breadth-first traversal with a FIFO queue from every unvisited node and count the starts'), 'dfs': ('depth-first search (DFS)', 'start a depth-first traversal (recursion or an explicit LIFO stack) from every unvisited node and count the starts'), 'union_find': ('union-find (disjoint set union)', 'union the endpoints of every edge in a disjoint-set forest and count the roots'), 'label_propagation': ('label propagation', 'give every node its own label and repeatedly sweep the edges, lowering labels to the neighbour minimum until nothing changes')}\nT10 keys ['task_id', 'leetcode_ids', 'signature', 'description', 'bounds', 'modes', 'aliases']\nT10 rows (twin + designs) 1440\nmean code len 512.14375\nk values TWIN [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137]\nstages ['E1_sweep', 'E3_fresh', 'S0_twin', 'S1', 'S1_D5', 'S1_anchor', 'S2']\nlabels ['bfs', 'dfs', 'disputed', 'invalid', 'other', 'union_find']\nlabeller_source ['extraction', 'judge', 'judge_unavailable', 'runtime+ast']\nrealised keys [dict_keys(['S_b12', 'S_b23', 'S_b35', 'R_b23', 'R_b35', 'G1_b35', 'rel_err_mean', 'rel_err_max'])]\n\nUV_CACHE_DIR=/ai-inventor/aii_data/runs/run_jSassd-YWLVC/.shared_cache/uv\nPIP_CACHE_DIR=/ai-inventor/aii_data/runs/run_jSassd-YWLVC/.shared_cache/pip\nHF_HOME=/ai-inventor/aii_data/runs/run_jSassd-YWLVC/.shared_cache/hf\n/usr/bin/uv\nuv 0.6.14\n/usr/local/bin/python3.12\n2\n               total        used        free      shared  buff/cache   available\nMem:             755         101         369           0         289         653", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [62] THINKING · 2026-10-26 13:07:57 UTC

```
I'll measure runtimes directly given the 2-CPU box rather than assuming them, then write a reproducible builder script that takes the artifact path as an argument to generate `mini_demo_data.json`, with each of the 100 examples representing one T10 CRN slot and its arms.
```

### [63] TOOL CALL — Write · 2026-10-26 13:07:57 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/build_mini_demo_data.py

#!/usr/bin/env python3
"""Build mini_demo_data.json for code_demo.ipynb from the step-K artifact folder (gen_art_experiment_36).

One dataset only: T10 (connected components), 100 CRN slots = 5 templates (W1-W5) x k 0-19.
  k 0-9   committed S1/S2/E1 slots: TWIN, D1-D4 at alpha 1, D1-D5 at alpha 2, D3 at alpha 3/4/6, P_top/P_rest/P_shuf
  k 10-19 fresh E3 slots:           TWIN, D1-D5 at alpha 2, P_top/P_rest/P_shuf
Every example is one slot in the artifact's exp_gen_sol_out style (input = twin prompt, output = twin 'label|passed',
predict_<arm> = 'label|passed') plus, under metadata_*, the joined per-program rows of data/samples.jsonl (label,
passed, valid, realised-displacement summary, generated code), the 36-block displacement profiles of the alpha-2 rows
and their block-35 read-position displacement vectors (fp16, base64) on the committed slots.
Top-level metadata carries the T10 dose-unit maps (cache/units/T10.npz), the r_Q table (exp23), exp29's engine-d
PN_a2 labels (anchor agreement), the T10 catalogue and the published reference numbers (results/*.json).

usage: python build_mini_demo_data.py <path to gen_art_experiment_36> [out.json]
"""

from __future__ import annotations

import base64
import glob
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

TASK = "T10"
TEMPLATES = ("W1", "W2", "W3", "W4", "W5")
KS = list(range(20))
DESIGN_ARMS = ("D1_a1", "D2_a1", "D3_a1", "D4_a1", "D1_a2", "D2_a2", "D3_a2", "D4_a2", "D5_a2", "D3_a3", "D3_a4",
               "D3_a6", "PTOP_a2", "PREST_a2", "PSHUF_a2")
VEC_ARMS = ("D1_a2", "D2_a2", "D3_a2", "D4_a2", "D5_a2", "PTOP_a2", "PSHUF_a2")   # F5 / E2 (P_rest excluded, as F5)
PROFILE_ARMS = ("D1_a2", "D2_a2", "D3_a2", "D4_a2", "D5_a2", "PTOP_a2", "PREST_a2", "PSHUF_a2")   # F3
ROW_FIELDS = ("key", "task", "template", "arm", "k", "stage", "design", "alpha", "unit_id", "seed_scheme",
              "direction_seed", "n_tokens", "finish_reason", "realised_disp", "unit_mean_b12", "label", "passed",
              "valid", "labeller_source", "Y", "Y_any", "A", "code")


def stable_seed(*parts) -> int:
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest(), 16) % (2 ** 63)


def read_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in open(p) if l.strip()]


def r4(m: np.ndarray) -> list:
    return np.round(m.astype(np.float64), 4).tolist()


def main() -> None:
    art = Path(sys.argv[1]).resolve()
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent / "mini_demo_data.json"

    # ---- per-program joined rows (data/samples.jsonl), T10, twin + design arms, slots k 0-19
    rows = [r for r in read_jsonl(art / "data" / "samples.jsonl")
            if r["task"] == TASK and r["k"] in KS and (r["arm"] == "TWIN" or r["arm"] in DESIGN_ARMS)]
    by_slot: dict[tuple[str, int], dict[str, dict]] = {}
    for r in rows:
        by_slot.setdefault((r["template"], r["k"]), {})[r["arm"]] = {f: r.get(f) for f in ROW_FIELDS}

    # ---- 36-block displacement profiles (data/realised_disp.jsonl), alpha-2 arms, committed slots k 0-9
    prof: dict[tuple[str, int], dict[str, dict]] = {}
    for r in read_jsonl(art / "data" / "realised_disp.jsonl"):
        if r["task"] == TASK and r["arm"] in PROFILE_ARMS and int(r["sample_id"]) < 10:
            prof.setdefault((r["template"], int(r["sample_id"])), {})[r["arm"]] = {
                f: [round(float(x), 3) for x in r[f]] for f in ("spec_mean", "R", "gen1")}

    # ---- block-35 read-position displacement vectors (cache/disp/*.npz, fp16), committed slots k 0-9
    vecs: dict[tuple[str, int], dict[str, str]] = {}
    for p in sorted(glob.glob(str(art / "cache" / "disp" / f"{TASK}_*.npz"))):
        z = np.load(p)
        for name in z.files:
            key, kind = name.split("::")
            task, w, arm, k = key.split("|")
            if kind == "R35" and arm in VEC_ARMS and int(k) < 10:
                v = z[name].astype(np.float16)
                vecs.setdefault((w, int(k)), {})[arm] = base64.b64encode(v.tobytes()).decode()

    # ---- twin prompts (vendored exp22 prompts4.jsonl)
    prompts = {}
    for r in read_jsonl(art / "vendor" / "exp22" / "prompts" / "prompts4.jsonl"):
        if r["kind"] == "twin" and r["task"] == TASK:
            prompts[r["template_id"]] = {"user_text": r["user_text"], "p1": r["p1"], "spec_end": r["spec_end"],
                                         "P": r["P"], "noun": r.get("noun")}

    examples = []
    for w in TEMPLATES:
        for k in KS:
            progs = by_slot[(w, k)]
            tw = progs["TWIN"]
            e = {"input": f"[task {TASK} | template {w} | CRN slot k={k}]\n{prompts[w]['user_text']}",
                 "output": f"{tw['label']}|{bool(tw['passed'])}"}
            for arm in DESIGN_ARMS:
                if arm in progs:
                    e[f"predict_{arm}"] = f"{progs[arm]['label']}|{bool(progs[arm]['passed'])}"
            e.update({"metadata_task": TASK, "metadata_template": w, "metadata_k": k,
                      "metadata_uniform_seed": stable_seed(TASK, w, k),
                      "metadata_slot_set": "committed k 0-9 (S1, S2, E1)" if k < 10 else "fresh k 10-19 (E3)",
                      "metadata_programs": [progs[a] for a in ("TWIN",) + DESIGN_ARMS if a in progs],
                      "metadata_disp_profiles": prof.get((w, k), {}),
                      "metadata_R35_fp16_b64": vecs.get((w, k), {})})
            examples.append(e)

    # ---- dose units (cache/units/T10.npz), r_Q (exp23), exp29 anchor labels, catalogue, published numbers
    z = np.load(art / "cache" / "units" / f"{TASK}.npz", allow_pickle=False)
    units = {"U_abs": r4(z["U_abs"]), "tokens_W1": [str(t) for t in z["tokens_W1"]]}
    for w in TEMPLATES:
        units[f"h_norm_{w}"] = r4(z[f"h_norm_{w}"])
        units[f"U_bf_{w}"] = r4(z[f"U_bf_{w}"])
    q = json.loads((art / "inputs" / "exp23" / "results" / "qwen_ratio.json").read_text())["r_Q"]
    r_q = {"block": [int(b) for b in q], "depth": [v["depth"] for v in q.values()],
           "median": [v["median"] for v in q.values()]}
    e29 = [{"template": l["template"], "sample_id": int(l["sample_id"]), "label": l["label"],
            "passed": l.get("passed"), "arm": l["arm"], "engine": l.get("engine")}
           for l in read_jsonl(art / "inputs" / "exp29" / "data" / "labels.jsonl")
           if l.get("engine") == "d" and l["task"] == TASK and l["arm"] == "PN_a2"]
    sys.path.insert(0, str(art / "vendor" / "exp22" / "inputs" / "exp11"))
    from bench.common.catalogue import TASKS  # noqa: E402  (vendored exp11 catalogue, read-only)
    cat = {m: list(v) for m, v in TASKS[TASK]["modes"].items()}

    res = art / "results"
    rj = lambda n: json.loads((res / n).read_text())  # noqa: E731
    s1 = rj("s1_2x2.json")
    s2 = rj("s2_profile.json")
    e1 = rj("e1_sweep.json")
    e2 = rj("e2_geometry.json")
    e3 = rj("e3_replicate.json")
    published = {
        "anchors": rj("anchors.json"),
        "s1_tables_T10": {k: v for k, v in s1["tables"].items() if k.startswith("T10|")},
        "s1_decision_T10_a2": s1["decision_T10_a2"],
        "D5_split_T10": {k: v for k, v in s1["D5_split"].items() if k.startswith("T10|")},
        "mediation_T10": s1["mediation"].get("T10"),
        "s2_T10": s2["T10"], "s2_reading_T10": s2["reading_T10"],
        "e1_T10": e1["T10"],
        "e2_T10": e2["T10"], "e2_slot_concordance": e2["slot_concordance"],
        "e3_T10": {k: v for k, v in e3.items() if k.startswith("T10_")},
        "unit_profiles_T10": rj("unit_profiles.json")["T10"],
        "s3_prices_H5": {t: {cls: round(v["H5"], 3) for cls, v in d.items() if isinstance(v, dict) and "H5" in v}
                         for t, d in rj("s3_prices.json")["per_task"].items()},
    }

    data = {
        "metadata": {
            "description": ("Iteration-7 step K of the plan-noise study on Qwen/Qwen3-8B (rev b968826d, bf16, thinking "
                            "off). Demo subset: task T10 (connected components), 100 CRN slots (W1-W5 x k 0-19); "
                            "every slot carries the clean twin and every pushed arm (dose unit x direction seeds x "
                            "alpha) with its label, pass flag, validity, realised displacement summary and code."),
            "source_files": ["data/samples.jsonl", "data/realised_disp.jsonl", "cache/disp/T10_*.npz",
                             "cache/units/T10.npz", "inputs/exp23/results/qwen_ratio.json",
                             "inputs/exp29/data/labels.jsonl", "vendor/exp22/prompts/prompts4.jsonl",
                             "vendor/exp22/inputs/exp11/bench/common/catalogue.py", "results/*.json"],
            "model": "Qwen/Qwen3-8B", "model_revision": "b968826d9c46dd6066d109eabc6255188de91218",
            "task": TASK, "default_algorithm": "union_find", "catalogue_modes": cat,
            "twin_prompts": prompts,
            "edit_blocks": list(range(12, 24)),
            "units_T10": units, "r_Q": r_q,
            "exp29_T10_PN_a2_labels_engine_d": e29,
            "published": published,
            "vector_encoding": "base64 of float16 little-endian bytes, 4096 values (block-35 delta h at read position R)",
        },
        "datasets": [{"dataset": "T10_connected_components_crn_slots", "examples": examples}],
    }
    out.write_text(json.dumps(data, separators=(",", ":")))
    n_prog = sum(len(e["metadata_programs"]) for e in examples)
    n_vec = sum(len(e["metadata_R35_fp16_b64"]) for e in examples)
    print(f"wrote {out} ({out.stat().st_size / 1e6:.2f} MB): {len(examples)} slots, {n_prog} programs, "
          f"{n_vec} block-35 vectors, {sum(len(e['metadata_disp_profiles']) for e in examples)} profiles")


if __name__ == "__main__":
    main()
```

### [64] TOOL RESULT — Write · 2026-10-26 13:07:57 UTC

```
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/build_mini_demo_data.py", "content": "#!/usr/bin/env python3\n\"\"\"Build mini_demo_data.json for code_demo.ipynb from the step-K artifact folder (gen_art_experiment_36).\n\nOne dataset only: T10 (connected components), 100 CRN slots = 5 templates (W1-W5) x k 0-19.\n  k 0-9   committed S1/S2/E1 slots: TWIN, D1-D4 at alpha 1, D1-D5 at alpha 2, D3 at alpha 3/4/6, P_top/P_rest/P_shuf\n  k 10-19 fresh E3 slots:           TWIN, D1-D5 at alpha 2, P_top/P_rest/P_shuf\nEvery example is one slot in the artifact's exp_gen_sol_out style (input = twin prompt, output = twin 'label|passed',\npredict_<arm> = 'label|passed') plus, under metadata_*, the joined per-program rows of data/samples.jsonl (label,\npassed, valid, realised-displacement summary, generated code), the 36-block displacement profiles of the alpha-2 rows\nand their block-35 read-position displacement vectors (fp16, base64) on the committed slots.\nTop-level metadata carries the T10 dose-unit maps (cache/units/T10.npz), the r_Q table (exp23), exp29's engine-d\nPN_a2 labels (anchor agreement), the T10 catalogue and the published reference numbers (results/*.json).\n\nusage: python build_mini_demo_data.py <path to gen_art_experiment_36> [out.json]\n\"\"\"\n\nfrom __future__ import annotations\n\nimport base64\nimport glob\nimport hashlib\nimport json\nimport sys\nfrom pathlib import Path\n\nimport numpy as np\n\nTASK = \"T10\"\nTEMPLATES = (\"W1\", \"W2\", \"W3\", \"W4\", \"W5\")\nKS = list(range(20))\nDESIGN_ARMS = (\"D1_a1\", \"D2_a1\", \"D3_a1\", \"D4_a1\", \"D1_a2\", \"D2_a2\", \"D3_a2\", \"D4_a2\", \"D5_a2\", \"D3_a3\", \"D3_a4\",\n               \"D3_a6\", \"PTOP_a2\", \"PREST_a2\", \"PSHUF_a2\")\nVEC_ARMS = (\"D1_a2\", \"D2_a2\", \"D3_a2\", \"D4_a2\", \"D5_a2\", \"PTOP_a2\", \"PSHUF_a2\")   # F5 / E2 (P_rest excluded, as F5)\nPROFILE_ARMS = (\"D1_a2\", \"D2_a2\", \"D3_a2\", \"D4_a2\", \"D5_a2\", \"PTOP_a2\", \"PREST_a2\", \"PSHUF_a2\")   # F3\nROW_FIELDS = (\"key\", \"task\", \"template\", \"arm\", \"k\", \"stage\", \"design\", \"alpha\", \"unit_id\", \"seed_scheme\",\n              \"direction_seed\", \"n_tokens\", \"finish_reason\", \"realised_disp\", \"unit_mean_b12\", \"label\", \"passed\",\n              \"valid\", \"labeller_source\", \"Y\", \"Y_any\", \"A\", \"code\")\n\n\ndef stable_seed(*parts) -> int:\n    return int(hashlib.sha256(\"|\".join(str(p) for p in parts).encode()).hexdigest(), 16) % (2 ** 63)\n\n\ndef read_jsonl(p: Path) -> list[dict]:\n    return [json.loads(l) for l in open(p) if l.strip()]\n\n\ndef r4(m: np.ndarray) -> list:\n    return np.round(m.astype(np.float64), 4).tolist()\n\n\ndef main() -> None:\n    art = Path(sys.argv[1]).resolve()\n    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent / \"mini_demo_data.json\"\n\n    # ---- per-program joined rows (data/samples.jsonl), T10, twin + design arms, slots k 0-19\n    rows = [r for r in read_jsonl(art / \"data\" / \"samples.jsonl\")\n            if r[\"task\"] == TASK and r[\"k\"] in KS and (r[\"arm\"] == \"TWIN\" or r[\"arm\"] in DESIGN_ARMS)]\n    by_slot: dict[tuple[str, int], dict[str, dict]] = {}\n    for r in rows:\n        by_slot.setdefault((r[\"template\"], r[\"k\"]), {})[r[\"arm\"]] = {f: r.get(f) for f in ROW_FIELDS}\n\n    # ---- 36-block displacement profiles (data/realised_disp.jsonl), alpha-2 arms, committed slots k 0-9\n    prof: dict[tuple[str, int], dict[str, dict]] = {}\n    for r in read_jsonl(art / \"data\" / \"realised_disp.jsonl\"):\n        if r[\"task\"] == TASK and r[\"arm\"] in PROFILE_ARMS and int(r[\"sample_id\"]) < 10:\n            prof.setdefault((r[\"template\"], int(r[\"sample_id\"])), {})[r[\"arm\"]] = {\n                f: [round(float(x), 3) for x in r[f]] for f in (\"spec_mean\", \"R\", \"gen1\")}\n\n    # ---- block-35 read-position displacement vectors (cache/disp/*.npz, fp16), committed slots k 0-9\n    vecs: dict[tuple[str, int], dict[str, str]] = {}\n    for p in sorted(glob.glob(str(art / \"cache\" / \"disp\" / f\"{TASK}_*.npz\"))):\n        z = np.load(p)\n        for name in z.files:\n            key, kind = name.split(\"::\")\n            task, w, arm, k = key.split(\"|\")\n            if kind == \"R35\" and arm in VEC_ARMS and int(k) < 10:\n                v = z[name].astype(np.float16)\n                vecs.setdefault((w, int(k)), {})[arm] = base64.b64encode(v.tobytes()).decode()\n\n    # ---- twin prompts (vendored exp22 prompts4.jsonl)\n    prompts = {}\n    for r in read_jsonl(art / \"vendor\" / \"exp22\" / \"prompts\" / \"prompts4.jsonl\"):\n        if r[\"kind\"] == \"twin\" and r[\"task\"] == TASK:\n            prompts[r[\"template_id\"]] = {\"user_text\": r[\"user_text\"], \"p1\": r[\"p1\"], \"spec_end\": r[\"spec_end\"],\n                                         \"P\": r[\"P\"], \"noun\": r.get(\"noun\")}\n\n    examples = []\n    for w in TEMPLATES:\n        for k in KS:\n            progs = by_slot[(w, k)]\n            tw = progs[\"TWIN\"]\n            e = {\"input\": f\"[task {TASK} | template {w} | CRN slot k={k}]\\n{prompts[w]['user_text']}\",\n                 \"output\": f\"{tw['label']}|{bool(tw['passed'])}\"}\n            for arm in DESIGN_ARMS:\n                if arm in progs:\n                    e[f\"predict_{arm}\"] = f\"{progs[arm]['label']}|{bool(progs[arm]['passed'])}\"\n            e.update({\"metadata_task\": TASK, \"metadata_template\": w, \"metadata_k\": k,\n                      \"metadata_uniform_seed\": stable_seed(TASK, w, k),\n                      \"metadata_slot_set\": \"committed k 0-9 (S1, S2, E1)\" if k < 10 else \"fresh k 10-19 (E3)\",\n                      \"metadata_programs\": [progs[a] for a in (\"TWIN\",) + DESIGN_ARMS if a in progs],\n                      \"metadata_disp_profiles\": prof.get((w, k), {}),\n                      \"metadata_R35_fp16_b64\": vecs.get((w, k), {})})\n            examples.append(e)\n\n    # ---- dose units (cache/units/T10.npz), r_Q (exp23), exp29 anchor labels, catalogue, published numbers\n    z = np.load(art / \"cache\" / \"units\" / f\"{TASK}.npz\", allow_pickle=False)\n    units = {\"U_abs\": r4(z[\"U_abs\"]), \"tokens_W1\": [str(t) for t in z[\"tokens_W1\"]]}\n    for w in TEMPLATES:\n        units[f\"h_norm_{w}\"] = r4(z[f\"h_norm_{w}\"])\n        units[f\"U_bf_{w}\"] = r4(z[f\"U_bf_{w}\"])\n    q = json.loads((art / \"inputs\" / \"exp23\" / \"results\" / \"qwen_ratio.json\").read_text())[\"r_Q\"]\n    r_q = {\"block\": [int(b) for b in q], \"depth\": [v[\"depth\"] for v in q.values()],\n           \"median\": [v[\"median\"] for v in q.values()]}\n    e29 = [{\"template\": l[\"template\"], \"sample_id\": int(l[\"sample_id\"]), \"label\": l[\"label\"],\n            \"passed\": l.get(\"passed\"), \"arm\": l[\"arm\"], \"engine\": l.get(\"engine\")}\n           for l in read_jsonl(art / \"inputs\" / \"exp29\" / \"data\" / \"labels.jsonl\")\n           if l.get(\"engine\") == \"d\" and l[\"task\"] == TASK and l[\"arm\"] == \"PN_a2\"]\n    sys.path.insert(0, str(art / \"vendor\" / \"exp22\" / \"inputs\" / \"exp11\"))\n    from bench.common.catalogue import TASKS  # noqa: E402  (vendored exp11 catalogue, read-only)\n    cat = {m: list(v) for m, v in TASKS[TASK][\"modes\"].items()}\n\n    res = art / \"results\"\n    rj = lambda n: json.loads((res / n).read_text())  # noqa: E731\n    s1 = rj(\"s1_2x2.json\")\n    s2 = rj(\"s2_profile.json\")\n    e1 = rj(\"e1_sweep.json\")\n    e2 = rj(\"e2_geometry.json\")\n    e3 = rj(\"e3_replicate.json\")\n    published = {\n        \"anchors\": rj(\"anchors.json\"),\n        \"s1_tables_T10\": {k: v for k, v in s1[\"tables\"].items() if k.startswith(\"T10|\")},\n        \"s1_decision_T10_a2\": s1[\"decision_T10_a2\"],\n        \"D5_split_T10\": {k: v for k, v in s1[\"D5_split\"].items() if k.startswith(\"T10|\")},\n        \"mediation_T10\": s1[\"mediation\"].get(\"T10\"),\n        \"s2_T10\": s2[\"T10\"], \"s2_reading_T10\": s2[\"reading_T10\"],\n        \"e1_T10\": e1[\"T10\"],\n        \"e2_T10\": e2[\"T10\"], \"e2_slot_concordance\": e2[\"slot_concordance\"],\n        \"e3_T10\": {k: v for k, v in e3.items() if k.startswith(\"T10_\")},\n        \"unit_profiles_T10\": rj(\"unit_profiles.json\")[\"T10\"],\n        \"s3_prices_H5\": {t: {cls: round(v[\"H5\"], 3) for cls, v in d.items() if isinstance(v, dict) and \"H5\" in v}\n                         for t, d in rj(\"s3_prices.json\")[\"per_task\"].items()},\n    }\n\n    data = {\n        \"metadata\": {\n            \"description\": (\"Iteration-7 step K of the plan-noise study on Qwen/Qwen3-8B (rev b968826d, bf16, thinking \"\n                            \"off). Demo subset: task T10 (connected components), 100 CRN slots (W1-W5 x k 0-19); \"\n                            \"every slot carries the clean twin and every pushed arm (dose unit x direction seeds x \"\n                            \"alpha) with its label, pass flag, validity, realised displacement summary and code.\"),\n            \"source_files\": [\"data/samples.jsonl\", \"data/realised_disp.jsonl\", \"cache/disp/T10_*.npz\",\n                             \"cache/units/T10.npz\", \"inputs/exp23/results/qwen_ratio.json\",\n                             \"inputs/exp29/data/labels.jsonl\", \"vendor/exp22/prompts/prompts4.jsonl\",\n                             \"vendor/exp22/inputs/exp11/bench/common/catalogue.py\", \"results/*.json\"],\n            \"model\": \"Qwen/Qwen3-8B\", \"model_revision\": \"b968826d9c46dd6066d109eabc6255188de91218\",\n            \"task\": TASK, \"default_algorithm\": \"union_find\", \"catalogue_modes\": cat,\n            \"twin_prompts\": prompts,\n            \"edit_blocks\": list(range(12, 24)),\n            \"units_T10\": units, \"r_Q\": r_q,\n            \"exp29_T10_PN_a2_labels_engine_d\": e29,\n            \"published\": published,\n            \"vector_encoding\": \"base64 of float16 little-endian bytes, 4096 values (block-35 delta h at read position R)\",\n        },\n        \"datasets\": [{\"dataset\": \"T10_connected_components_crn_slots\", \"examples\": examples}],\n    }\n    out.write_text(json.dumps(data, separators=(\",\", \":\")))\n    n_prog = sum(len(e[\"metadata_programs\"]) for e in examples)\n    n_vec = sum(len(e[\"metadata_R35_fp16_b64\"]) for e in examples)\n    print(f\"wrote {out} ({out.stat().st_size / 1e6:.2f} MB): {len(examples)} slots, {n_prog} programs, \"\n          f\"{n_vec} block-35 vectors, {sum(len(e['metadata_disp_profiles']) for e in examples)} profiles\")\n\n\nif __name__ == \"__main__\":\n    main()\n", "structuredPatch": [], "originalFile": null, "userModified": false}
```

### [65] ASSISTANT · 2026-10-26 13:08:13 UTC

```
Now I'll run the builder. In parallel, I'll create the test venv and time how long the Colab-pinned packages and a CPU torch wheel take to install, which decides whether the edit demo can use torch.
```

### [66] TOOL CALL — Bash · 2026-10-26 13:08:13 UTC

```
Build mini_demo_data.json from the artifact:
time python3 build_mini_demo_data.py /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36 && ls -la mini_demo_data.json
```

### [67] TOOL RESULT — Bash · 2026-10-26 13:08:13 UTC

```
{"stdout": "wrote /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/mini_demo_data.json (5.78 MB): 100 slots, 1250 programs, 350 block-35 vectors, 400 profiles\n\nreal\t0m1.488s\nuser\t0m0.537s\nsys\t0m0.057s\n-rw-rw-rw- 1 aii-agent aii-agent 5784655 Oct 26 13:08 mini_demo_data.json", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [68] TOOL CALL — Bash · 2026-10-26 13:08:13 UTC

```
Create test venv and time package installs:
E=/tmp/aii_nb_test_envs/art_8O5eaNc5gxJs-e3ffb3a2e51e; mkdir -p /tmp/aii_nb_test_envs; UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 $E && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python $E/bin/python jupyter ipykernel && echo VENV_OK; t0=$(date +%s); $E/bin/python -m pip install -q numpy==2.0.2 pandas==2.2.2 scikit-learn==1.6.1 scipy==1.16.3 matplotlib==3.10.0 statsmodels==0.14.6 loguru==0.7.3 2>&1 | tail -3; t1=$(date +%s); echo "core install: $((t1-t0))s"; $E/bin/python -m pip install -q torch==2.9.0 --index-url https://download.pytorch.org/whl/cpu 2>&1 | tail -3; t2=$(date +%s); echo "torch install: $((t2-t1))s"; $E/bin/python -c "import torch, numpy, scipy, statsmodels, sklearn; print(torch.__version__, numpy.__version__, scipy.__version__, statsmodels.__version__, sklearn.__version__)"
```

### [69] TOOL RESULT — Bash · 2026-10-26 13:08:41 UTC

```
{"stdout": "VENV_OK\ncore install: 13s\ntorch install: 13s\n2.9.0+cpu 2.0.2 1.16.3 0.14.6 1.6.1", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [70] THINKING · 2026-10-26 13:12:11 UTC

```
Both installs cache quickly (~13s each), so torch is cheap to include, and the 5.8MB data file has 100 slots, 1,250 programs, 350 block-35 vectors, and 400 profiles. Before writing the notebook, I'll validate the data file and add a `task` field to the exp29 anchor labels so `exp29_labels_d()`'s filter works unchanged.
```

### [71] TOOL CALL — Bash · 2026-10-26 13:12:11 UTC

```
Rebuild data with task field and validate contents:
sed -i 's/    e29 = \[{"template": l\["template"\], "sample_id": int(l\["sample_id"\]), "label": l\["label"\],/    e29 = [{"task": l["task"], "template": l["template"], "sample_id": int(l["sample_id"]), "label": l["label"],/' build_mini_demo_data.py && grep -n 'e29 = ' build_mini_demo_data.py && python3 build_mini_demo_data.py /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36 && python3 -c "
import json, base64, numpy as np
from collections import Counter
d=json.load(open('mini_demo_data.json'))
m=d['metadata']; ex=d['datasets'][0]['examples']
print('top keys', list(d.keys()), '| metadata keys', list(m.keys()))
print('n examples', len(ex)); print('example keys', list(ex[0].keys()))
print('arms per slot', Counter(len(e['metadata_programs']) for e in ex))
print('e29 n', len(m['exp29_T10_PN_a2_labels_engine_d']), m['exp29_T10_PN_a2_labels_engine_d'][0])
# vector check: norm of decoded R35 vs realised_disp R_b35
e=ex[0]; p={r['arm']:r for r in e['metadata_programs']}
for arm,s in list(e['metadata_R35_fp16_b64'].items())[:3]:
    v=np.frombuffer(base64.b64decode(s), dtype=np.float16).astype(np.float32)
    print(arm, v.shape, float(np.linalg.norm(v)), p[arm]['realised_disp']['R_b35'])
print('published e2 T10 keys', list(m['published']['e2_T10'].keys()))
print(json.dumps(m['published']['e2_T10']['fixed_dose_strata'], indent=0)[:800])
print(json.dumps(m['published']['e2_slot_concordance'])[:600])
sz={k: len(json.dumps(v)) for k,v in m.items()}; print('metadata sizes', sz)
print('example field sizes', {k: sum(len(json.dumps(e[k])) for e in ex) for k in ex[0].keys() if k.startswith('metadata_') and k in ('metadata_programs','metadata_disp_profiles','metadata_R35_fp16_b64')})
"
```

### [72] TOOL RESULT — Bash · 2026-10-26 13:12:13 UTC

```
{"stdout": "115:    e29 = [{\"task\": l[\"task\"], \"template\": l[\"template\"], \"sample_id\": int(l[\"sample_id\"]), \"label\": l[\"label\"],\nwrote /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/mini_demo_data.json (5.79 MB): 100 slots, 1250 programs, 350 block-35 vectors, 400 profiles\ntop keys ['metadata', 'datasets'] | metadata keys ['description', 'source_files', 'model', 'model_revision', 'task', 'default_algorithm', 'catalogue_modes', 'twin_prompts', 'edit_blocks', 'units_T10', 'r_Q', 'exp29_T10_PN_a2_labels_engine_d', 'published', 'vector_encoding']\nn examples 100\nexample keys ['input', 'output', 'predict_D1_a1', 'predict_D2_a1', 'predict_D3_a1', 'predict_D4_a1', 'predict_D1_a2', 'predict_D2_a2', 'predict_D3_a2', 'predict_D4_a2', 'predict_D5_a2', 'predict_D3_a3', 'predict_D3_a4', 'predict_D3_a6', 'predict_PTOP_a2', 'predict_PREST_a2', 'predict_PSHUF_a2', 'metadata_task', 'metadata_template', 'metadata_k', 'metadata_uniform_seed', 'metadata_slot_set', 'metadata_programs', 'metadata_disp_profiles', 'metadata_R35_fp16_b64']\narms per slot Counter({16: 50, 9: 50})\ne29 n 50 {'task': 'T10', 'template': 'W1', 'sample_id': 0, 'label': 'union_find', 'passed': True, 'arm': 'PN_a2', 'engine': 'd'}\nD1_a2 (4096,) 247.57289123535156 247.5732\nD4_a2 (4096,) 199.53123474121094 199.5313\nD2_a2 (4096,) 229.8159942626953 229.8158\npublished e2 T10 keys ['n', 'n_attempted', 'cv_auc_log_norms', 'cv_auc_R35_direction', 'cv_auc_gen1_direction', 'cv_auc_specmean35_direction', 'fixed_dose_strata', 'escape_axis']\n{\n\"U_abs_alpha2 (D1+D2)\": {\n\"n\": 100,\n\"n_attempted\": 52,\n\"cv_auc_log_norms\": 0.5232371794871795,\n\"cv_auc_R35_direction\": 0.39783653846153844,\n\"cv_auc_gen1_direction\": 0.5208333333333334\n},\n\"U_bf_family_alpha2 (D3+D4+D5)\": {\n\"n\": 150,\n\"n_attempted\": 23,\n\"cv_auc_log_norms\": 0.6881205066757959,\n\"cv_auc_R35_direction\": 0.7226977062649778,\n\"cv_auc_gen1_direction\": 0.6966792194453955\n}\n}\n{\"T10|Y|alpha2\": {\"n_slots\": 50, \"phi_D1_D2_same_stream_diff_u\": 0.16012815380508702, \"joint_D1_D2\": 15, \"joint_expected_if_independent\": 13.0, \"phi_D1_D3_same_u_diff_unit\": 0.20000000000000015, \"phi_D2_D4_same_u_diff_unit\": 0.1372527032615032}, \"T10|A|alpha2\": {\"n_slots\": 50, \"phi_D1_D2_same_stream_diff_u\": 0.19871794871794848, \"joint_D1_D2\": 16, \"joint_expected_if_independent\": 13.520000000000001, \"phi_D1_D3_same_u_diff_unit\": 0.1868161794392684, \"phi_D2_D4_same_u_diff_unit\": 0.1372527032615032}, \"T10|A|D1_alpha1_to_alpha2_same_u_same_stream\": {\"n\": 50, \"P_escape_a2_given_escape_a1\": 0.33333\nmetadata sizes {'description': 345, 'source_files': 283, 'model': 15, 'model_revision': 42, 'task': 5, 'default_algorithm': 12, 'catalogue_modes': 599, 'twin_prompts': 3435, 'edit_blocks': 48, 'units_T10': 170469, 'r_Q': 555, 'exp29_T10_PN_a2_labels_engine_d': 5876, 'published': 33224, 'vector_encoding': 90}\nexample field sizes {'metadata_programs': 1436764, 'metadata_disp_profiles': 318894, 'metadata_R35_fp16_b64': 3828300}", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [73] THINKING · 2026-10-26 13:14:55 UTC

```
Data validation passed: decoded norms, slot program counts, and reference numbers all match. Now I'll keep `r_Q` in its original nested shape so `k_units.r_q_table()` stays unchanged, then load the NotebookEdit schema for the next fixes.
```

### [74] TOOL CALL — Bash · 2026-10-26 13:14:55 UTC

```
Store r_Q table in original format and rebuild data:
python3 - <<'EOF'
from pathlib import Path
p = Path("build_mini_demo_data.py")
s = p.read_text()
old = '''    r_q = {"block": [int(b) for b in q], "depth": [v["depth"] for v in q.values()],
           "median": [v["median"] for v in q.values()]}
'''
new = '''    r_q = q          # exp23 qwen_ratio.json['r_Q'] as is: {block: {median, q25, q75, depth, n}}
'''
assert s.count(old) == 1
p.write_text(s.replace(old, new))
EOF
python3 build_mini_demo_data.py /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36 && python3 -c "
import json; d=json.load(open('mini_demo_data.json')); print(list(d['metadata']['r_Q'].items())[:2])"
```

### [75] TOOL CALL — ToolSearch · 2026-10-26 13:14:55 UTC

```
{'query': 'select:NotebookEdit', 'max_results': 1}
```

### [76] TOOL RESULT — Bash · 2026-10-26 13:14:55 UTC

```
{"stdout": "wrote /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/mini_demo_data.json (5.79 MB): 100 slots, 1250 programs, 350 block-35 vectors, 400 profiles\n[('12', {'median': 0.06980449706315994, 'q25': 0.05178554356098175, 'q75': 0.09988057613372803, 'depth': 0.3611111111111111, 'n': 10515}), ('13', {'median': 0.07784001529216766, 'q25': 0.058433447033166885, 'q75': 0.11136050522327423, 'depth': 0.3888888888888889, 'n': 10515})]", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [77] TOOL RESULT — ToolSearch · 2026-10-26 13:14:55 UTC

```
{"matches": ["NotebookEdit"], "query": "select:NotebookEdit", "total_deferred_tools": 28}
```

### [78] THINKING · 2026-10-26 13:19:33 UTC

```
TODO 3 is complete — mini_demo_data.json now holds 100 curated T10 CRN slot examples. Moving to TODO 4, I'll build the ~50-cell notebook with a temporary script first (more reliable than sequential inserts) and use NotebookEdit for fixes, making sure to record the original vector load order since E2's cross-validated AUCs depend on row order.
```

### [79] TOOL CALL — Bash · 2026-10-26 13:19:33 UTC

```
Record original vector order in data and rebuild:
python3 - <<'EOF'
from pathlib import Path
p = Path("build_mini_demo_data.py")
s = p.read_text()
old1 = '''    vecs: dict[tuple[str, int], dict[str, str]] = {}
'''
new1 = '''    vecs: dict[tuple[str, int], dict[str, str]] = {}
    vec_order: list[str] = []     # geometry_k.load_vectors() order (sorted npz files, keys in file order): the CV folds
'''
old2 = '''                vecs.setdefault((w, int(k)), {})[arm] = base64.b64encode(v.tobytes()).decode()
'''
new2 = '''                vecs.setdefault((w, int(k)), {})[arm] = base64.b64encode(v.tobytes()).decode()
                vec_order.append(key)
'''
old3 = '''            "vector_encoding": "base64 of float16 little-endian bytes, 4096 values (block-35 delta h at read position R)",
'''
new3 = '''            "vector_encoding": "base64 of float16 little-endian bytes, 4096 values (block-35 delta h at read position R)",
            "vector_order": vec_order,
'''
for o, n in ((old1, new1), (old2, new2), (old3, new3)):
    assert s.count(o) == 1, o
    s = s.replace(o, n)
p.write_text(s)
EOF
python3 build_mini_demo_data.py /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36 && python3 -c "
import json; d=json.load(open('mini_demo_data.json')); vo=d['metadata']['vector_order']; print(len(vo), vo[:6])"; mkdir -p .dev
```

### [80] TOOL RESULT — Bash · 2026-10-26 13:19:35 UTC

```
{"stdout": "wrote /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/mini_demo_data.json (5.79 MB): 100 slots, 1250 programs, 350 block-35 vectors, 400 profiles\n350 ['T10|W1|D1_a2|0', 'T10|W1|D4_a2|0', 'T10|W1|D1_a2|1', 'T10|W1|D4_a2|1', 'T10|W1|D1_a2|2', 'T10|W1|D4_a2|2']", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [81] THINKING · 2026-10-26 13:25:31 UTC

```
Building the notebook generator (a temporary dev file to be deleted later) that assembles each cell from the original source files, with data-source and T10-only tweaks marked `# demo:`.
```

### [82] TOOL CALL — Write · 2026-10-26 13:25:31 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [83] TOOL RESULT — Write · 2026-10-26 13:25:31 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [84] THINKING · 2026-10-26 13:26:03 UTC

```
I'll clean up the summary cell—swapping the dict-wrapping hack for a plain `fmt_ci` helper and printing the table as text instead of a pandas Styler, so it displays well in plain-text viewers too.
```

### [85] TOOL CALL — Edit · 2026-10-26 13:26:03 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/.dev/make_notebook.py
OLD: pub = data["metadata"]["published"]
t2, p2 = s1_res["tables"]["T10|a2|Y"], pub["s1_tables_T10"]["T10|a2|Y"]
fmt_rd = lambda v, c: f"{v[c]:+.3f} [{v[c + '_ci95'][0]:+.2f}, {v[c + '_ci95'][1]:+.2f}]"  # noqa: E731
d5n, d5p = s1_res["D5_split"]["T10|Y"], pub["D5_split_T10"]["T10|Y"]
NEW: pub = data["metadata"]["published"]
t2, p2 = s1_res["tables"]["T10|a2|Y"], pub["s1_tables_T10"]["T10|a2|Y"]
fmt_ci = lambda rd, ci: f"{rd:+.3f} [{ci[0]:+.2f}, {ci[1]:+.2f}]"  # noqa: E731
fmt_rd = lambda v, c: fmt_ci(v[c], v[c + "_ci95"])  # noqa: E731
d5n, d5p = s1_res["D5_split"]["T10|Y"], pub["D5_split_T10"]["T10|Y"]
PRO, ENE = "profile_at_matched_energy (D1 - D5)", "energy_at_banfree_shape (D5 - D3)"
```

### [86] TOOL RESULT — Edit · 2026-10-26 13:26:03 UTC

```
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/.dev/make_notebook.py", "oldString": "pub = data[\"metadata\"][\"published\"]\nt2, p2 = s1_res[\"tables\"][\"T10|a2|Y\"], pub[\"s1_tables_T10\"][\"T10|a2|Y\"]\nfmt_rd = lambda v, c: f\"{v[c]:+.3f} [{v[c + '_ci95'][0]:+.2f}, {v[c + '_ci95'][1]:+.2f}]\"  # noqa: E731\nd5n, d5p = s1_res[\"D5_split\"][\"T10|Y\"], pub[\"D5_split_T10\"][\"T10|Y\"]", "newString": "pub = data[\"metadata\"][\"published\"]\nt2, p2 = s1_res[\"tables\"][\"T10|a2|Y\"], pub[\"s1_tables_T10\"][\"T10|a2|Y\"]\nfmt_ci = lambda rd, ci: f\"{rd:+.3f} [{ci[0]:+.2f}, {ci[1]:+.2f}]\"  # noqa: E731\nfmt_rd = lambda v, c: fmt_ci(v[c], v[c + \"_ci95\"])  # noqa: E731\nd5n, d5p = s1_res[\"D5_split\"][\"T10|Y\"], pub[\"D5_split_T10\"][\"T10|Y\"]\nPRO, ENE = \"profile_at_matched_energy (D1 - D5)\", \"energy_at_banfree_shape (D5 - D3)\"", "originalFile": null, "structuredPatch": [{"oldStart": 1674, "oldLines": 8, "newStart": 1674, "newLines": 10, "lines": [" code(r'''", " pub = data[\"metadata\"][\"published\"]", " t2, p2 = s1_res[\"tables\"][\"T10|a2|Y\"], pub[\"s1_tables_T10\"][\"T10|a2|Y\"]", "-fmt_rd = lambda v, c: f\"{v[c]:+.3f} [{v[c + '_ci95'][0]:+.2f}, {v[c + '_ci95'][1]:+.2f}]\"  # noqa: E731", "+fmt_ci = lambda rd, ci: f\"{rd:+.3f} [{ci[0]:+.2f}, {ci[1]:+.2f}]\"  # noqa: E731", "+fmt_rd = lambda v, c: fmt_ci(v[c], v[c + \"_ci95\"])  # noqa: E731", " d5n, d5p = s1_res[\"D5_split\"][\"T10|Y\"], pub[\"D5_split_T10\"][\"T10|Y\"]", "+PRO, ENE = \"profile_at_matched_energy (D1 - D5)\", \"energy_at_banfree_shape (D5 - D3)\"", " s2n, s2p = s2_res[\"T10\"][\"tests\"], pub[\"s2_T10\"][\"tests\"]", " mcn = lambda t: f\"{t['share_x']:.2f} vs {t['share_y']:.2f} ({t['n10']}:{t['n01']}, p {t['p']:.2g})\"  # noqa: E731", " e3n, e3p = e3_res[\"T10_fresh_k10_19\"][\"2x2|Y\"], pub[\"e3_T10\"][\"T10_fresh_k10_19\"][\"2x2|Y\"]"]}], "userModified": false, "replaceAll": false}
```

### [87] TOOL CALL — Edit · 2026-10-26 13:26:03 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/.dev/make_notebook.py
OLD:     ("D5 split: profile at matched energy (D1-D5)", fmt_rd({"x": d5n["profile_at_matched_energy (D1 - D5)"]["RD"], "x_ci95": d5n["profile_at_matched_energy (D1 - D5)"]["ci95"]}, "x"),
     fmt_rd({"x": d5p["profile_at_matched_energy (D1 - D5)"]["RD"], "x_ci95": d5p["profile_at_matched_energy (D1 - D5)"]["ci95"]}, "x")),
    ("D5 split: energy at ban-free shape (D5-D3)", fmt_rd({"x": d5n["energy_at_banfree_shape (D5 - D3)"]["RD"], "x_ci95": d5n["energy_at_banfree_shape (D5 - D3)"]["ci95"]}, "x"),
     fmt_rd({"x": d5p["energy_at_banfree_shape (D5 - D3)"]["RD"], "x_ci95": d5p["energy_at_banfree_shape (D5 - D3)"]["ci95"]}, "x")),
NEW:     ("D5 split: profile at matched energy (D1-D5)", fmt_ci(d5n[PRO]["RD"], d5n[PRO]["ci95"]),
     fmt_ci(d5p[PRO]["RD"], d5p[PRO]["ci95"])),
    ("D5 split: energy at ban-free shape (D5-D3)", fmt_ci(d5n[ENE]["RD"], d5n[ENE]["ci95"]),
     fmt_ci(d5p[ENE]["RD"], d5p[ENE]["ci95"])),
```

### [88] TOOL RESULT — Edit · 2026-10-26 13:26:03 UTC

```
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/.dev/make_notebook.py", "oldString": "    (\"D5 split: profile at matched energy (D1-D5)\", fmt_rd({\"x\": d5n[\"profile_at_matched_energy (D1 - D5)\"][\"RD\"], \"x_ci95\": d5n[\"profile_at_matched_energy (D1 - D5)\"][\"ci95\"]}, \"x\"),\n     fmt_rd({\"x\": d5p[\"profile_at_matched_energy (D1 - D5)\"][\"RD\"], \"x_ci95\": d5p[\"profile_at_matched_energy (D1 - D5)\"][\"ci95\"]}, \"x\")),\n    (\"D5 split: energy at ban-free shape (D5-D3)\", fmt_rd({\"x\": d5n[\"energy_at_banfree_shape (D5 - D3)\"][\"RD\"], \"x_ci95\": d5n[\"energy_at_banfree_shape (D5 - D3)\"][\"ci95\"]}, \"x\"),\n     fmt_rd({\"x\": d5p[\"energy_at_banfree_shape (D5 - D3)\"][\"RD\"], \"x_ci95\": d5p[\"energy_at_banfree_shape (D5 - D3)\"][\"ci95\"]}, \"x\")),", "newString": "    (\"D5 split: profile at matched energy (D1-D5)\", fmt_ci(d5n[PRO][\"RD\"], d5n[PRO][\"ci95\"]),\n     fmt_ci(d5p[PRO][\"RD\"], d5p[PRO][\"ci95\"])),\n    (\"D5 split: energy at ban-free shape (D5-D3)\", fmt_ci(d5n[ENE][\"RD\"], d5n[ENE][\"ci95\"]),\n     fmt_ci(d5p[ENE][\"RD\"], d5p[ENE][\"ci95\"])),", "originalFile": null, "structuredPatch": [{"oldStart": 1701, "oldLines": 10, "newStart": 1701, "newLines": 10, "lines": ["     (\"S1 conditional logit beta_unit\", f\"{t2['clogit']['coef']['unit']:.2f}\", f\"{p2['clogit']['coef']['unit']:.2f}\"),", "     (\"S1 decision (committed rule)\", s1_res[\"decision_T10_a2\"], pub[\"s1_decision_T10_a2\"]),", "     (\"D5 (U_bf*) share Y\", f\"{d5n['shares']['D5']:.2f}\", f\"{d5p['shares']['D5']:.2f}\"),", "-    (\"D5 split: profile at matched energy (D1-D5)\", fmt_rd({\"x\": d5n[\"profile_at_matched_energy (D1 - D5)\"][\"RD\"], \"x_ci95\": d5n[\"profile_at_matched_energy (D1 - D5)\"][\"ci95\"]}, \"x\"),", "-     fmt_rd({\"x\": d5p[\"profile_at_matched_energy (D1 - D5)\"][\"RD\"], \"x_ci95\": d5p[\"profile_at_matched_energy (D1 - D5)\"][\"ci95\"]}, \"x\")),", "-    (\"D5 split: energy at ban-free shape (D5-D3)\", fmt_rd({\"x\": d5n[\"energy_at_banfree_shape (D5 - D3)\"][\"RD\"], \"x_ci95\": d5n[\"energy_at_banfree_shape (D5 - D3)\"][\"ci95\"]}, \"x\"),", "-     fmt_rd({\"x\": d5p[\"energy_at_banfree_shape (D5 - D3)\"][\"RD\"], \"x_ci95\": d5p[\"energy_at_banfree_shape (D5 - D3)\"][\"ci95\"]}, \"x\")),", "+    (\"D5 split: profile at matched energy (D1-D5)\", fmt_ci(d5n[PRO][\"RD\"], d5n[PRO][\"ci95\"]),", "+     fmt_ci(d5p[PRO][\"RD\"], d5p[PRO][\"ci95\"])),", "+    (\"D5 split: energy at ban-free shape (D5-D3)\", fmt_ci(d5n[ENE][\"RD\"], d5n[ENE][\"ci95\"]),", "+     fmt_ci(d5p[ENE][\"RD\"], d5p[ENE][\"ci95\"])),", "     (\"S2 P_top vs P_rest (Y, McNemar)\", mcn(s2n[\"PTOP_vs_PREST|Y\"]), mcn(s2p[\"PTOP_vs_PREST|Y\"])),", "     (\"S2 D1 vs P_shuf (Y, McNemar)\", mcn(s2n[\"D1_vs_PSHUF|Y\"]), mcn(s2p[\"D1_vs_PSHUF|Y\"])),", "     (\"S2 reading\", s2_res[\"reading_T10\"], pub[\"s2_reading_T10\"]),"]}], "userModified": false, "replaceAll": false}
```

### [89] TOOL CALL — Edit · 2026-10-26 13:26:03 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/.dev/make_notebook.py
OLD: print(f"N_BOOT = {N_BOOT}, N_FLIP = {N_FLIP}: {int((summary_df['match'] == 'yes').sum())}/{len(summary_df)} "
      f"quantities identical to the artifact")
summary_df.style.hide(axis="index")
NEW: print(f"N_BOOT = {N_BOOT}, N_FLIP = {N_FLIP}: {int((summary_df['match'] == 'yes').sum())}/{len(summary_df)} "
      f"quantities identical to the artifact\n")
print(summary_df.to_string(index=False))
```

### [90] TOOL RESULT — Edit · 2026-10-26 13:26:03 UTC

```
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/.dev/make_notebook.py", "oldString": "print(f\"N_BOOT = {N_BOOT}, N_FLIP = {N_FLIP}: {int((summary_df['match'] == 'yes').sum())}/{len(summary_df)} \"\n      f\"quantities identical to the artifact\")\nsummary_df.style.hide(axis=\"index\")", "newString": "print(f\"N_BOOT = {N_BOOT}, N_FLIP = {N_FLIP}: {int((summary_df['match'] == 'yes').sum())}/{len(summary_df)} \"\n      f\"quantities identical to the artifact\\n\")\nprint(summary_df.to_string(index=False))", "originalFile": null, "structuredPatch": [{"oldStart": 1724, "oldLines": 8, "newStart": 1724, "newLines": 8, "lines": [" summary_df = pd.DataFrame(summary_rows, columns=[\"quantity\", \"this notebook\", \"published (artifact)\"])", " summary_df[\"match\"] = np.where(summary_df[\"this notebook\"] == summary_df[\"published (artifact)\"], \"yes\", \"no\")", " print(f\"N_BOOT = {N_BOOT}, N_FLIP = {N_FLIP}: {int((summary_df['match'] == 'yes').sum())}/{len(summary_df)} \"", "-      f\"quantities identical to the artifact\")", "-summary_df.style.hide(axis=\"index\")", "+      f\"quantities identical to the artifact\\n\")", "+print(summary_df.to_string(index=False))", " ''')", " ", " md(r'''"]}], "userModified": false, "replaceAll": false}
```

### [91] ASSISTANT · 2026-10-26 13:26:13 UTC

```
Now I'll generate the notebook and run the first test exactly as specified, with the minimum config (`N_BOOT = 20`, `N_FLIP = 1000`), in a fresh venv and timed.
```

### [92] TOOL CALL — Bash · 2026-10-26 13:26:13 UTC

```
Generate notebook and run first minimal test:
python3 .dev/make_notebook.py && UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_8O5eaNc5gxJs-e3ffb3a2e51e && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_8O5eaNc5gxJs-e3ffb3a2e51e/bin/python jupyter ipykernel && t0=$(date +%s) && /tmp/aii_nb_test_envs/art_8O5eaNc5gxJs-e3ffb3a2e51e/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | tail -40; echo "EXIT ${PIPESTATUS[0]} runtime $(( $(date +%s) - t0 ))s"
```

### [93] TOOL RESULT — Bash · 2026-10-26 13:26:53 UTC

```
{"stdout": "wrote /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/code_demo.ipynb with 50 cells\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[IPKernelApp] WARNING | Kernel is running over TCP without encryption. All communication (including code and outputs) is sent in plain text and is susceptible to eavesdropping. Use IPC transport or launch with kernel manager-provisioned CurveZMQ keys to enable transport encryption.\n[NbConvertApp] Writing 798296 bytes to code_demo.ipynb\nEXIT 0 runtime 38s", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [94] ASSISTANT · 2026-10-26 13:27:01 UTC

```
The first run passed in 38 s, install cell included. Before scaling, I'll check that every output is right, not just that the run finished.
```

### [95] TOOL CALL — Bash · 2026-10-26 13:27:01 UTC

```
Print executed notebook cell outputs:
python3 - <<'EOF'
import json
nb = json.load(open("code_demo.ipynb"))
for i, c in enumerate(nb["cells"]):
    if c["cell_type"] != "code":
        continue
    outs = []
    for o in c.get("outputs", []):
        if o["output_type"] == "stream":
            outs.append("".join(o["text"]))
        elif o["output_type"] in ("execute_result", "display_data"):
            d = o["data"]
            outs.append("[image/png]" if "image/png" in d else "".join(d.get("text/plain", "")))
        elif o["output_type"] == "error":
            outs.append("ERROR " + o["ename"] + ": " + o["evalue"])
    txt = "\n".join(outs)
    print(f"===== cell {i} ({c['id']}) =====")
    print(txt[:3500])
EOF
```

### [96] TOOL RESULT — Bash · 2026-10-26 13:27:01 UTC

```
{"stdout": "===== cell 1 (cell-01) =====\n\n===== cell 2 (cell-02) =====\nnumpy 2.0.2 | torch 2.9.0+cpu | pandas 2.2.2\n\n===== cell 3 (cell-03) =====\n\n===== cell 4 (cell-04) =====\nGitHub data unavailable, using local mini_demo_data.json: HTTP Error 404: Not Found\nIteration-7 step K of the plan-noise study on Qwen/Qwen3-8B (rev b968826d, bf16, thinking off). Demo subset: task T10 (connected components), 100 CRN slots (W1-W5 x k 0-19); every slot carries the clean twin and every pushed arm (dose unit x direction seeds x alpha) with its label, pass flag, validity, realised displacement summary and code.\n\n100 CRN slots | 1250 generated programs | 350 block-35 displacement vectors\n\nfirst slot: [task T10 | template W1 | CRN slot k=0] -> twin wrote union_find|True | D1 at alpha 2 wrote union_find|True\n\n===== cell 6 (cell-06) =====\n\n===== cell 8 (cell-08) =====\nsetup     src/setup_inputs.py                                     \ngates     src/s3_prices.py g5; src/cpu_gates.py                   \nlabel     src/label_k.py (background worker)                      \ngpu0      src/gen_k.py tests s0                                   <- section 6: the edit arithmetic of GPU unit test U2, on toy tensors (no model)\ncommit1   src/make_commits.py commit1                             \ngpu1      src/gen_k.py s1 d5 s2                                   \ncommit2   src/make_commits.py commit2                             \ngpu2      src/gen_k.py s3pn                                       \nknobs     src/knobs_k.py base,reuse,check,verdict,rerun           \nunits     src/dump_units.py                                       <- section 5: dose units U_abs / U_bf / U_bf* / P_top / P_rest / P_shuf of T10\ne1        src/e1_sweep.py                                         \nanalyse   src/analysis_k.py all                                   <- sections 8-11: anchors, S1 2x2, D5 split, mediation, S2, E1\nprices    src/s3_prices.py prices; src/s3_prices.py retag         \nnovelty   src/novelty_k.py; src/novelty_k.py --manual-only        \ngeometry  src/geometry_k.py                                       <- section 13: E2 slot concordance and fixed-dose AUCs\nfigures   src/figures_k.py                                        <- section 14: F1-F5, E1, E3\nreport    src/report_k.py                                         \nrederive  audit/rederive.py                                       \noutputs   src/outputs_k.py                                        \n\n(E3's analysis, src/extensions_k.py, ran outside the step table; section 12 re-runs it.)\n\n===== cell 10 (cell-10) =====\n\n===== cell 12 (cell-12) =====\n1250 programs over 100 CRN slots\n          D1_a1  D1_a2  D2_a1  D2_a2  D3_a1  D3_a2  D3_a3  D3_a4  D3_a6  D4_a1  D4_a2  D5_a2  PREST_a2  PSHUF_a2  PTOP_a2  TWIN\nprograms     50    100     50    100     50    100     50     50     50     50    100    100       100       100      100   100\n\n===== cell 14 (cell-14) =====\n\n===== cell 15 (cell-15) =====\n1250 joined rows | T10 catalogue ['bfs', 'dfs', 'label_propagation', 'union_find'], default 'union_find' | outcome mismatches vs the artifact: 0\n\n----- [task T10 | template W1 | CRN slot k=3]   arm TWIN: label union_find, passed True -----\ndef solve(n, edges):\n    parent = list(range(n))\n    \n    def find(x):\n        if parent[x] != x:\n            parent[x] = find(parent[x])\n        return parent[x]\n    \n    def union(x, y):\n        root_x = find(x)\n        root_y = find(y)\n        if root_x != root_y:\n            parent[root_y] = root_x\n    \n    for u, v in edges:\n        union(u, v)\n    \n    components = set()\n    for i in range(n):\n        components.add(find(i))\n    \n    return len(components)\n\n\n----- [task T10 | template W1 | CRN slot k=3]   arm D1_a2: label dfs, passed True -----\ndef solve(n, edges):\n    def dfs(node):\n        visited.add(node)\n        for neighbor in adj[node]:\n            if neighbor not in visited:\n                dfs(neighbor)\n    \n    adj = [[] for _ in range(n)]\n    for u, v in edges:\n        adj[u].append(v)\n        adj[v].append(u)\n    \n    visited = set()\n    components = 0\n    \n    for i in range(n):\n        if i not in visited:\n            dfs(i)\n            components += 1\n    \n    return components\n\n\n===== cell 17 (cell-17) =====\n\n===== cell 19 (cell-19) =====\n   U_bf recomputed - dumped (max abs) fro_ratio_total U_abs_over_hnorm_max U_bf_over_hnorm_max top_quartile_energy_share_U_abs top_quartile_energy_share_U_bf ratio_of_mean_norms (b12..b23) mean_per_position_ratio (mean)  fro_ratio_total (published)\nW1                          5.436e-05           0.616                 1.05              0.1233                          0.8078                          0.417                     0.66..0.79                         0.9941                        0.616\nW2                          5.531e-05           0.612                1.053              0.1233                          0.8078                         0.4153                     0.66..0.78                         0.9899                        0.612\nW3                          5.531e-05          0.6148               0.9963              0.1233                          0.8078                         0.4161                     0.66..0.78                         0.9929                       0.6148\nW4                          5.531e-05          0.6113               0.8196              0.1233                          0.8078                          0.416                     0.66..0.78                         0.9883                       0.6113\nW5                          5.531e-05          0.6091                1.621              0.1233                          0.8078                         0.4144                     0.66..0.78                          0.987                       0.6091\n\n\ndose_ratios vs U_abs (T10, W1):\n                 U_abs   U_bf  U_bf*  P_top  P_rest  P_shuf\nmean_cell_ratio    1.0  0.994  1.803  0.278   1.711   1.308\nfro_ratio          1.0  0.616  1.000  1.000   1.000   1.000\nb12_mean_ratio     1.0  0.661  1.540  0.338   1.589   1.000\n\nP_top: top-quartile cells hold 81% of U_abs's energy (rescaled x1.11); P_rest rescaled x2.28\n\n===== cell 21 (cell-21) =====\nrecomputed direction seed vs logged seed: {('S4', 'match'): 850, ('S5', 'match'): 300}\nslot (T10, W1, k 0): S4 seed 322596924058654721, S5 seed 2689073420633678604; |u4| = 1.0000, |u5| = 1.0000; cos(u4, u5) = +0.0238 (two isotropic draws in R^4096: |cos| ~ 1/sqrt(4096) = 0.016)\n\n===== cell 23 (cell-23) =====\n\n===== cell 24 (cell-24) =====\n                        mean rel. error of (h - h_twin).u vs alpha*n max |hook step orthogonal to u| positions outside S unchanged (bitwise) max |change| at masked-out cells\nTARGET, U_abs, float32                                           0.0                        0.000107                                    True                              0.0\nmasked, P_top, float32                                           0.0                        0.000077                                    True                              0.0\nTARGET, U_abs, bfloat16                                     0.000114                        0.523504                                    True                              0.0\nmasked, P_top, bfloat16                                     0.000052                        0.572326                                    True                              0.0\n\n===== cell 26 (cell-26) =====\n\n===== cell 27 (cell-27) =====\n\n===== cell 29 (cell-29) =====\n{\n \"A1\": {\n  \"attempted_off_default\": 26,\n  \"N\": 50,\n  \"exp29\": \"25/50\",\n  \"fisher_p\": 1.0,\n  \"pass_rate\": 0.98,\n  \"pass\": true,\n  \"correct_off_default_Y_any\": 25\n },\n \"A2\": {\n  \"correct_off_default\": 1,\n  \"N\": 50,\n  \"exp27\": \"1/50\",\n  \"fisher_p\": 1.0,\n  \"attempted\": 1,\n  \"pass_rate\": 1.0,\n  \"pass\": true\n },\n \"D1_T10_per_slot_agreement_vs_exp29\": {\n  \"agreement\": 0.98,\n  \"n\": 50\n },\n \"both_pass\": true\n}\n\n===== cell 31 (cell-31) =====\n\n===== cell 32 (cell-32) =====\ns1() took 0.3s with N_BOOT=20, N_FLIP=1000\n\nDECISION (T10, alpha 2, outcome Y): UNIT\nshares: {'D1': 0.5, 'D2': 0.52, 'D3': 0.1, 'D4': 0.02} (paired slots: 50)\n  RD_unit +0.450  95% CI [+0.360, +0.527]  sign-flip p 0.001  Holm 0.003\n  RD_seed +0.030  95% CI [-0.082, +0.110]  sign-flip p 0.72  Holm 0.76\n  RD_int  -0.100  95% CI [-0.251, +0.031]  sign-flip p 0.38  Holm 0.76\n  ConditionalLogit: beta_unit +4.34 (p 0.00011), beta_seed +1.68 (p 0.13), beta_unit:seed -1.77 (p 0.14)\n\nall T10 2x2 tables (task|alpha|outcome):\n             n_slots    D1    D2   D3    D4 RD_unit RD_seed   INT decision rule\nT10|a1|Y          50  0.12  0.14  0.0  0.02    0.12   -0.02   0.0          UNIT\nT10|a1|Y_any      50  0.12  0.14  0.0  0.02    0.12   -0.02   0.0          UNIT\nT10|a1|A          50  0.12  0.14  0.0  0.02    0.12   -0.02   0.0          UNIT\nT10|a2|Y          50   0.5  0.52  0.1  0.02    0.45    0.03  -0.1          UNIT\nT10|a2|Y_any      50   0.5  0.52  0.1  0.02    0.45    0.03  -0.1          UNIT\nT10|a2|A          50  0.52  0.52  0.1  0.02    0.46    0.04 -0.08          UNIT\n\nD5 split (T10, alpha 2):\n  Y: shares D1 0.50, D5 0.28, D3 0.10\n     profile_at_matched_energy (D1 - D5)    RD +0.22 [+0.06, +0.32]  McNemar 13:2, p 0.00739\n     energy_at_banfree_shape (D5 - D3)      RD +0.18 [+0.06, +0.33]  McNemar 10:1, p 0.0117\n  A: shares D1 0.52, D5 0.34, D3 0.10\n     profile_at_matched_energy (D1 - D5)    RD +0.18 [+0.03, +0.28]  McNemar 13:4, p 0.049\n     energy_at_banfree_shape (D5 - D3)      RD +0.24 [+0.14, +0.38]  McNemar 13:1, p 0.00183\n\nmediation (T10, outcome Y; reference design D1):\n           without mediators  with log-norm mediators\nD2                      0.11                     0.13\nD3                     -2.35                    -2.54\nD4                     -3.31                    -3.49\nD5                     -0.93                    -0.92\nalpha2                  1.94                     2.21\nlog_S_b35                NaN                    -0.37\nlog_R_b35                NaN                     0.01\nCV AUC of A from the two downstream norms: 0.77\n\n/tmp/aii_nb_test_envs/art_8O5eaNc5gxJs-e3ffb3a2e51e/lib/python3.12/site-packages/statsmodels/discrete/conditional_models.py:80: UserWarning: Dropped 13 groups and 52 observations for having no within-group variance\n  warnings.warn(msg)\n/tmp/aii_nb_test_envs/art_8O5eaNc5gxJs-e3ffb3a2e51e/lib/python3.12/site-packages/statsmodels/discrete/conditional_models.py:80: UserWarning: Dropped 13 groups and 52 observations for having no within-group variance\n  warnings.warn(msg)\n/tmp/aii_nb_test_envs/art_8O5eaNc5gxJs-e3ffb3a2e51e/lib/python3.12/site-packages/statsmodels/discrete/conditional_models.py:80: UserWarning: Dropped 13 groups and 52 observations for having no within-group variance\n  warnings.warn(msg)\n\n===== cell 34 (cell-34) =====\nreading (T10): PUSHES ACT WHERE BANS WRITE\nU_abs top-quartile energy share 0.81; rescale factors P_top x1.11, P_rest x2.28, P_shuf x1.00\n          N     Y  share Y     A  pass  mean S_b12  mean S_b23  mean S_b35  mean R_b35\nD1     50.0  25.0     0.50  26.0  0.98       13.76       72.10      260.83      240.50\nPTOP   50.0  29.0     0.58  29.0  1.00        4.64       59.05      211.73      159.51\nPREST  50.0  15.0     0.30  16.0  0.92       21.86       91.86      300.01      367.51\nPSHUF  50.0   4.0     0.08   5.0  0.98       13.75       69.29      203.98      248.24\nPTOP_vs_PREST|Y    0.58 vs 0.30   McNemar 18:4   p 0.0043   Holm 0.0087\nD1_vs_PSHUF|Y      0.50 vs 0.08   McNemar 21:0   p 9.5e-07   Holm 2.9e-06\nD1_vs_PTOP|Y       0.50 vs 0.58   McNemar 4:8   p 0.39   Holm 0.39\n\n===== cell 36 (cell-36) =====\n        Y   N share Y   A pass  McNemar vs D1_a2 mean S_b12 mean S_b35 mean R_b35\nTWIN    0  50    0.00   0 1.00    0:25 (p 6e-08)        NaN        NaN        NaN\nD1_a1   6  50    0.12   6 1.00  4:23 (p 0.00031)       6.88     120.23     129.33\nD1_a2  25  50    0.50  26 0.98                        13.76     260.83     240.50\nD3_a1   0  50    0.00   0 1.00    0:25 (p 6e-08)       4.53      72.77     117.14\nD3_a2   5  50    0.10   5 1.00  1:21 (p 1.1e-05)       9.07     151.76     222.26\nD3_a3   9  50    0.18  10 0.98  1:17 (p 0.00014)      13.60     234.93     320.76\nD3_a4  20  50    0.40  21 0.98      3:8 (p 0.23)      18.13     329.22     423.31\nD3_a6  14  50    0.28  22 0.46    4:15 (p 0.019)      27.20     546.22     692.77\nD5_a2  14  50    0.28  17 0.94   2:13 (p 0.0074)      21.17     270.49     381.96\n\n===== cell 38 (cell-38) =====\n/tmp/aii_nb_test_envs/art_8O5eaNc5gxJs-e3ffb3a2e51e/lib/python3.12/site-packages/statsmodels/discrete/conditional_models.py:80: UserWarning: Dropped 14 groups and 56 observations for having no within-group variance\n  warnings.warn(msg)\n\n13:26:46|INFO   |T10_fresh_k10_19: shares {'D1': 0.42, 'D2': 0.6, 'D3': 0.08, 'D4': 0.1} RD_unit 0.420 (0.32425000000000004, 0.5105) RD_seed -0.100 (-0.18575, 0.04149999999999992) INT -0.160 -> UNIT\n\n13:26:46|INFO   |T10_pooled_k0_19: shares {'D1': 0.46, 'D2': 0.56, 'D3': 0.09, 'D4': 0.06} RD_unit 0.435 (0.38475000000000004, 0.47762499999999997) RD_seed -0.035 (-0.097625, 0.040499999999999974) INT -0.130 -> UNIT\n\nT10_fresh_k10_19: PTOP_vs_PREST 0.48 vs 0.18 (McNemar 15:0, p 6.1e-05); D1_vs_PSHUF 0.42 vs 0.08 (McNemar 17:0, p 1.5e-05); D1_vs_PTOP 0.42 vs 0.48 (McNemar 4:7, p 0.55)\nT10_pooled_k0_19: PTOP_vs_PREST 0.53 vs 0.24 (McNemar 33:4, p 1.1e-06); D1_vs_PSHUF 0.46 vs 0.08 (McNemar 38:0, p 7.3e-12); D1_vs_PTOP 0.46 vs 0.53 (McNemar 8:15, p 0.21)\nT03_k0_9: INCOMPLETE (T03 is not in the demo data)\n\n/tmp/aii_nb_test_envs/art_8O5eaNc5gxJs-e3ffb3a2e51e/lib/python3.12/site-packages/statsmodels/discrete/conditional_models.py:80: UserWarning: Dropped 14 groups and 56 observations for having no within-group variance\n  warnings.warn(msg)\n/tmp/aii_nb_test_envs/art_8O5eaNc5gxJs-e3ffb3a2e51e/lib/python3.12/site-packages/statsmodels/discrete/conditional_models.py:80: UserWarning: Dropped 27 groups and 108 observations for having no within-group variance\n  warnings.warn(msg)\n/tmp/aii_nb_test_envs/art_8O5eaNc5gxJs-e3ffb3a2e51e/lib/python3.12/site-packages/statsmodels/discrete/conditional_models.py:80: UserWarning: Dropped 27 groups and 108 observations for having no within-group variance\n  warnings.warn(msg)\n\n===== cell 40 (cell-40) =====\n                                    n  attempted  CV AUC log norms  published  CV AUC R35 direction  published \nU_abs_alpha2 (D1+D2)          100.000     52.000             0.523      0.523                 0.409       0.398\nU_bf_family_alpha2 (D3+D4+D5) 150.000     23.000             0.688      0.688                 0.687       0.723\n\nphi(D1, D2) on the same CRN stream, different u:  Y 0.16, A 0.20 (joint D1&D2 escapes 15 vs 13.0 expected if independent)\nsame u, alpha 1 -> 2: P(escape at a2 | escape at a1) = 0.33 (6 escapes at a1) vs marginal 0.52\n\n===== cell 42 (cell-42) =====\n[image/png]\n13:26:47|INFO   |figure F1_s1_interaction\n\n===== cell 43 (cell-43) =====\n[image/png]\n13:26:48|INFO   |figure F2_unit_heatmaps\n\n===== cell 44 (cell-44) =====\n[image/png]\n13:26:49|INFO   |figure F3_displacement_blocks\n\n===== cell 45 (cell-45) =====\n[image/png]\n13:26:49|INFO   |figure F4_escape_vs_disp\n\n[image/png]\n13:26:50|INFO   |figure F5_pca_disp35\n\n===== cell 46 (cell-46) =====\n[image/png]\n13:26:50|INFO   |figure E1_dose_response\n\n[image/png]\n13:26:51|INFO   |figure E3_replicate\n\n===== cell 48 (cell-48) =====\nN_BOOT = 20, N_FLIP = 1000: 14/23 quantities identical to the artifact\n\n                                          quantity                  this notebook           published (artifact) match\nA1: D1 attempted off-default, T10 a2 (exp29 25/50)                          26/50                          26/50   yes\n           A1: per-slot label agreement with exp29                           0.98                           0.98   yes\n           A2: D4 correct off-default (exp27 1/50)                           1/50                           1/50   yes\n                  S1 shares Y, D1/D2/D3/D4, T10 a2            0.50/0.52/0.10/0.02            0.50/0.52/0.10/0.02   yes\n                        S1 unit effect RD [95% CI]          +0.450 [+0.36, +0.53]          +0.450 [+0.35, +0.55]    no\n                        S1 seed effect RD [95% CI]          +0.030 [-0.08, +0.11]          +0.030 [-0.07, +0.14]    no\n                           S1 interaction [95% CI]          -0.100 [-0.25, +0.03]          -0.100 [-0.28, +0.08]    no\n                                   S1 Holm p, unit                          0.003                          3e-05    no\n                    S1 conditional logit beta_unit                           4.34                           4.34   yes\n                      S1 decision (committed rule)                           UNIT                           UNIT   yes\n                                D5 (U_bf*) share Y                           0.28                           0.28   yes\n       D5 split: profile at matched energy (D1-D5)          +0.220 [+0.06, +0.32]          +0.220 [+0.08, +0.36]    no\n        D5 split: energy at ban-free shape (D5-D3)          +0.180 [+0.06, +0.33]          +0.180 [+0.06, +0.30]    no\n                   S2 P_top vs P_rest (Y, McNemar)  0.58 vs 0.30 (18:4, p 0.0043)  0.58 vs 0.30 (18:4, p 0.0043)   yes\n                      S2 D1 vs P_shuf (Y, McNemar) 0.50 vs 0.08 (21:0, p 9.5e-07) 0.50 vs 0.08 (21:0, p 9.5e-07)   yes\n                                        S2 reading    PUSHES ACT WHERE BANS WRITE    PUSHES ACT WHERE BANS WRITE   yes\n                 E1 D3 (U_bf) Y at alpha 3 / 4 / 6                    9 / 20 / 14                    9 / 20 / 14   yes\n           E3 fresh slots k10-19: unit RD [95% CI]          +0.420 [+0.32, +0.51]          +0.420 [+0.32, +0.52]    no\n                 E3 pooled k0-19: unit RD [95% CI]          +0.435 [+0.38, +0.48]          +0.435 [+0.36, +0.52]    no\n                 E2 phi(D1, D2) same stream, Y / A                    0.16 / 0.20                    0.16 / 0.20   yes\n               E2 P(escape a2 | escape a1), same u                           0.33                           0.33   yes\n                E2 CV AUC, R35 direction, U_abs a2                          0.409                          0.398    no\n                    E2 CV AUC, log norms, U_abs a2                          0.523                          0.523   yes", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [97] THINKING · 2026-10-26 13:28:01 UTC

```
14 of 23 headline quantities already match exactly, with CI/p mismatches expected at low N_BOOT. One real discrepancy remains—the E2 R35-direction AUC—which I suspect stems from PCA's unseeded randomized solver on 80×4096 folds, so I'll test that directly.
```

### [98] TOOL CALL — Bash · 2026-10-26 13:28:01 UTC

```
Test whether PCA in cv_auc is nondeterministic:
cat > .dev/check_pca.py <<'EOF'
import base64, json, sys
import numpy as np
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

d = json.load(open("mini_demo_data.json"))
ex = d["datasets"][0]["examples"]
enc, lab = {}, {}
for e in ex:
    for p in e["metadata_programs"]:
        lab[p["key"]] = p
    for arm, s in e["metadata_R35_fp16_b64"].items():
        enc[f"T10|{e['metadata_template']}|{arm}|{e['metadata_k']}"] = s
keys = [k for k in d["metadata"]["vector_order"] if lab[k]["design"] in ("D1", "D2")]
R = np.stack([np.frombuffer(base64.b64decode(enc[k]), dtype=np.float16).astype(np.float32) for k in keys])
R /= np.linalg.norm(R, axis=1, keepdims=True)
y = np.array([lab[k]["A"] for k in keys])

def auc(solver, rs=None):
    pipe = make_pipeline(StandardScaler(), PCA(n_components=16, svd_solver=solver, random_state=rs),
                         LogisticRegression(C=0.1, max_iter=5000))
    pr = cross_val_predict(pipe, R, y, cv=StratifiedKFold(5, shuffle=True, random_state=0), method="predict_proba")[:, 1]
    return round(float(roc_auc_score(y, pr)), 3)

p = PCA(n_components=16); p.fit(StandardScaler().fit_transform(R[:80])); print("auto solver resolves to:", p._fit_svd_solver)
print("auto (unseeded), 6 runs:", [auc("auto") for _ in range(6)])
print("full (exact):", auc("full"))
EOF
/tmp/aii_nb_test_envs/art_8O5eaNc5gxJs-e3ffb3a2e51e/bin/python .dev/check_pca.py
```

### [99] TOOL RESULT — Bash · 2026-10-26 13:28:05 UTC

```
{"stdout": "auto solver resolves to: randomized\nauto (unseeded), 6 runs: [0.355, 0.415, 0.436, 0.421, 0.393, 0.412]\nfull (exact): 0.422", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [100] THINKING · 2026-10-26 13:29:00 UTC

```
Confirmed that `cv_auc`'s PCA uses the randomized solver with no seed, making the published 0.398 AUC non-reproducible exactly (repeated runs range 0.355–0.436). I'll leave the code unseeded per the minimal-changes rule, document this in the notebook, and fix a few cosmetic issues: the statsmodels warnings, scientific formatting in the edit-check table, updated units markdown with verified numbers, and a note on bf16 rounding.
```

### [101] TOOL CALL — Edit · 2026-10-26 13:29:00 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/.dev/make_notebook.py
OLD: # --- notebook additions: decoding the fp16 vectors, figures, tables ---
import base64
import matplotlib.pyplot as plt
import pandas as pd

print("numpy", np.__version__, "| torch", torch.__version__, "| pandas", pd.__version__)
NEW: # --- notebook additions: decoding the fp16 vectors, figures, tables ---
import base64
import warnings
import matplotlib.pyplot as plt
import pandas as pd

# statsmodels' ConditionalLogit warns on every fit that slots with the same outcome under all four designs carry no
# conditional information and are dropped -- expected for a paired 2x2, so silenced to keep the outputs readable
warnings.filterwarnings("ignore", message="Dropped .* groups and .* observations for having no within-group variance")
print("numpy", np.__version__, "| torch", torch.__version__, "| pandas", pd.__version__)
```

### [102] TOOL RESULT — Edit · 2026-10-26 13:29:00 UTC

```
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/.dev/make_notebook.py", "oldString": "# --- notebook additions: decoding the fp16 vectors, figures, tables ---\nimport base64\nimport matplotlib.pyplot as plt\nimport pandas as pd\n\nprint(\"numpy\", np.__version__, \"| torch\", torch.__version__, \"| pandas\", pd.__version__)", "newString": "# --- notebook additions: decoding the fp16 vectors, figures, tables ---\nimport base64\nimport warnings\nimport matplotlib.pyplot as plt\nimport pandas as pd\n\n# statsmodels' ConditionalLogit warns on every fit that slots with the same outcome under all four designs carry no\n# conditional information and are dropped -- expected for a paired 2x2, so silenced to keep the outputs readable\nwarnings.filterwarnings(\"ignore\", message=\"Dropped .* groups and .* observations for having no within-group variance\")\nprint(\"numpy\", np.__version__, \"| torch\", torch.__version__, \"| pandas\", pd.__version__)", "originalFile": null, "structuredPatch": [{"oldStart": 99, "oldLines": 9, "newStart": 99, "newLines": 13, "lines": [" ", " # --- notebook additions: decoding the fp16 vectors, figures, tables ---", " import base64", "+import warnings", " import matplotlib.pyplot as plt", " import pandas as pd", " ", "+# statsmodels' ConditionalLogit warns on every fit that slots with the same outcome under all four designs carry no", "+# conditional information and are dropped -- expected for a paired 2x2, so silenced to keep the outputs readable", "+warnings.filterwarnings(\"ignore\", message=\"Dropped .* groups and .* observations for having no within-group variance\")", " print(\"numpy\", np.__version__, \"| torch\", torch.__version__, \"| pandas\", pd.__version__)", " ''')", " "]}], "userModified": false, "replaceAll": false}
```

### [103] TOOL CALL — Edit · 2026-10-26 13:29:00 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/.dev/make_notebook.py
OLD: The GPU runner builds `U_bf` from the twin's prefill (`gen_k.TaskCtxK.twin`: `‖h_twin[l, p]‖ · r_at(l)`), and `src/dump_units.py` dumped the twin norms `‖h_twin‖` of every template. Recomputing `U_bf` from those norms reproduces the dumped unit. The table is `dump_units.py`'s per-template record, and it shows the key asymmetry between the two units:
- **U_abs is peaky.** Its top quartile of cells carries most of its energy, and at α 2 its largest cell dose exceeds that cell's own residual norm.
- **U_bf is flat by construction.**
NEW: The GPU runner builds `U_bf` from the twin's prefill (`gen_k.TaskCtxK.twin`: `‖h_twin[l, p]‖ · r_at(l)`), and `src/dump_units.py` dumped the twin norms `‖h_twin‖` of every template. Recomputing `U_bf` from those norms reproduces the dumped unit up to the data file's 4-decimal rounding. The table is `dump_units.py`'s per-template record, and it shows the key asymmetry between the two units:
- **U_abs is peaky.** Its top quartile of cells carries 81% of its energy. At α 2 its largest cell dose is about 2× that cell's own residual norm (`U_abs_over_hnorm_max` ≈ 1.05 on W1).
- **U_bf is flat by construction.** Its top quartile carries 42%, and its peak dose at α 2 is 0.25× the residual norm.

Two summaries of their size disagree, which is the confound that the D5 arm (`U_bf*`) splits. The per-block mean norms of U_bf are 0.66–0.79× those of U_abs, but the mean per-position ratio is ≈ 1.0. The total Frobenius ratio is 0.62.
```

### [104] TOOL RESULT — Edit · 2026-10-26 13:29:00 UTC

```
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/.dev/make_notebook.py", "oldString": "The GPU runner builds `U_bf` from the twin's prefill (`gen_k.TaskCtxK.twin`: `‖h_twin[l, p]‖ · r_at(l)`), and `src/dump_units.py` dumped the twin norms `‖h_twin‖` of every template. Recomputing `U_bf` from those norms reproduces the dumped unit. The table is `dump_units.py`'s per-template record, and it shows the key asymmetry between the two units:\n- **U_abs is peaky.** Its top quartile of cells carries most of its energy, and at α 2 its largest cell dose exceeds that cell's own residual norm.\n- **U_bf is flat by construction.**", "newString": "The GPU runner builds `U_bf` from the twin's prefill (`gen_k.TaskCtxK.twin`: `‖h_twin[l, p]‖ · r_at(l)`), and `src/dump_units.py` dumped the twin norms `‖h_twin‖` of every template. Recomputing `U_bf` from those norms reproduces the dumped unit up to the data file's 4-decimal rounding. The table is `dump_units.py`'s per-template record, and it shows the key asymmetry between the two units:\n- **U_abs is peaky.** Its top quartile of cells carries 81% of its energy. At α 2 its largest cell dose is about 2× that cell's own residual norm (`U_abs_over_hnorm_max` ≈ 1.05 on W1).\n- **U_bf is flat by construction.** Its top quartile carries 42%, and its peak dose at α 2 is 0.25× the residual norm.\n\nTwo summaries of their size disagree, which is the confound that the D5 arm (`U_bf*`) splits. The per-block mean norms of U_bf are 0.66–0.79× those of U_abs, but the mean per-position ratio is ≈ 1.0. The total Frobenius ratio is 0.62.", "originalFile": null, "structuredPatch": [{"oldStart": 546, "oldLines": 9, "newStart": 546, "newLines": 11, "lines": [" ", " md(r'''", " ### 5a. The two units in activation coordinates", "-The GPU runner builds `U_bf` from the twin's prefill (`gen_k.TaskCtxK.twin`: `‖h_twin[l, p]‖ · r_at(l)`), and `src/dump_units.py` dumped the twin norms `‖h_twin‖` of every template. Recomputing `U_bf` from those norms reproduces the dumped unit. The table is `dump_units.py`'s per-template record, and it shows the key asymmetry between the two units:", "-- **U_abs is peaky.** Its top quartile of cells carries most of its energy, and at α 2 its largest cell dose exceeds that cell's own residual norm.", "-- **U_bf is flat by construction.**", "+The GPU runner builds `U_bf` from the twin's prefill (`gen_k.TaskCtxK.twin`: `‖h_twin[l, p]‖ · r_at(l)`), and `src/dump_units.py` dumped the twin norms `‖h_twin‖` of every template. Recomputing `U_bf` from those norms reproduces the dumped unit up to the data file's 4-decimal rounding. The table is `dump_units.py`'s per-template record, and it shows the key asymmetry between the two units:", "+- **U_abs is peaky.** Its top quartile of cells carries 81% of its energy. At α 2 its largest cell dose is about 2× that cell's own residual norm (`U_abs_over_hnorm_max` ≈ 1.05 on W1).", "+- **U_bf is flat by construction.** Its top quartile carries 42%, and its peak dose at α 2 is 0.25× the residual norm.", "+", "+Two summaries of their size disagree, which is the confound that the D5 arm (`U_bf*`) splits. The per-block mean norms of U_bf are 0.66–0.79× those of U_abs, but the mean per-position ratio is ≈ 1.0. The total Frobenius ratio is 0.62.", " ''')", " ", " code(r'''"]}], "userModified": false, "replaceAll": false}
```

### [105] TOOL CALL — Edit · 2026-10-26 13:29:00 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/.dev/make_notebook.py
OLD:     res_edit[f"masked, P_top, {str(dtype)[6:]}"] = check(make_edits_masked(a, b, u, Mt, h_ref, mk), tw, inc, Mt, mk)
print(pd.DataFrame(res_edit).T.to_string())
''')
NEW:     res_edit[f"masked, P_top, {str(dtype)[6:]}"] = check(make_edits_masked(a, b, u, Mt, h_ref, mk), tw, inc, Mt, mk)
print(pd.DataFrame(res_edit).T.to_string(float_format=lambda x: f"{x:.2g}"))
''')

md(r'''
How to read the check:
- **In fp32** the displacement along `u` is exactly `α·n` up to float error, and the hook's step is parallel to `u`.
- **In bf16**, the model's real dtype, casting the edited state back rounds every coordinate. This leaves a ~1e-4 relative error along `u`, the same size as the real run's realised error (`rel_err_mean` ≈ 1e-4 on Qwen3-8B). It also adds an orthogonal rounding component of norm ≈ ‖h‖·2⁻⁹.
- **Untouched cells.** Positions outside the spec, and the cells that P_top masks out, are never touched (bitwise identical).
''')
```

### [106] TOOL RESULT — Edit · 2026-10-26 13:29:00 UTC

```
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/.dev/make_notebook.py", "oldString": "    res_edit[f\"masked, P_top, {str(dtype)[6:]}\"] = check(make_edits_masked(a, b, u, Mt, h_ref, mk), tw, inc, Mt, mk)\nprint(pd.DataFrame(res_edit).T.to_string())\n''')", "newString": "    res_edit[f\"masked, P_top, {str(dtype)[6:]}\"] = check(make_edits_masked(a, b, u, Mt, h_ref, mk), tw, inc, Mt, mk)\nprint(pd.DataFrame(res_edit).T.to_string(float_format=lambda x: f\"{x:.2g}\"))\n''')\n\nmd(r'''\nHow to read the check:\n- **In fp32** the displacement along `u` is exactly `α·n` up to float error, and the hook's step is parallel to `u`.\n- **In bf16**, the model's real dtype, casting the edited state back rounds every coordinate. This leaves a ~1e-4 relative error along `u`, the same size as the real run's realised error (`rel_err_mean` ≈ 1e-4 on Qwen3-8B). It also adds an orthogonal rounding component of norm ≈ ‖h‖·2⁻⁹.\n- **Untouched cells.** Positions outside the spec, and the cells that P_top masks out, are never touched (bitwise identical).\n''')", "originalFile": null, "structuredPatch": [{"oldStart": 726, "oldLines": 10, "newStart": 726, "newLines": 17, "lines": ["     h_ref = {l: tw[l][0, a:b].float() for l in EDIT_BLOCKS}         # gen_k: h_ref = the twin's spec states (fp32)", "     res_edit[f\"TARGET, U_abs, {str(dtype)[6:]}\"] = check(make_edits_v4(\"TARGET\", a, b, U, M, h_ref), tw, inc, M)", "     res_edit[f\"masked, P_top, {str(dtype)[6:]}\"] = check(make_edits_masked(a, b, u, Mt, h_ref, mk), tw, inc, Mt, mk)", "-print(pd.DataFrame(res_edit).T.to_string())", "+print(pd.DataFrame(res_edit).T.to_string(float_format=lambda x: f\"{x:.2g}\"))", " ''')", " ", " md(r'''", "+How to read the check:", "+- **In fp32** the displacement along `u` is exactly `α·n` up to float error, and the hook's step is parallel to `u`.", "+- **In bf16**, the model's real dtype, casting the edited state back rounds every coordinate. This leaves a ~1e-4 relative error along `u`, the same size as the real run's realised error (`rel_err_mean` ≈ 1e-4 on Qwen3-8B). It also adds an orthogonal rounding component of norm ≈ ‖h‖·2⁻⁹.", "+- **Untouched cells.** Positions outside the spec, and the cells that P_top masks out, are never touched (bitwise identical).", "+''')", "+", "+md(r'''", " ## 7. Statistics (`src/analysis_k.py`, part 2)", " All contrasts are **paired on CRN slots**. A slot `(template w, k)` fixes the prompt and the sampler's uniform stream, so each slot contributes one 0/1 outcome per design.", " - **Contrasts.**"]}], "userModified": false, "replaceAll": false}
```

### [107] TOOL CALL — Edit · 2026-10-26 13:29:00 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/.dev/make_notebook.py
OLD: The demo data ships the block-35 read-position vectors `R35` of the α-2 rows on the committed slots, in the artifact's load order. The spec-mean norm comes from each row's logged realised-displacement summary; the artifact took it from the fp16 vector, so the norm AUC can differ in the last digit. Three analyses are not re-run because they need vectors the demo does not ship: the generated-position-1 direction AUC, the spec-mean direction AUC, and the escape axis (which also uses α-1 vectors).
''')
NEW: The demo data ships the block-35 read-position vectors `R35` of the α-2 rows on the committed slots, in the artifact's load order. The spec-mean norm comes from each row's logged realised-displacement summary; the artifact took it from the fp16 vector, so the norm AUC can differ in the last digit. Three analyses are not re-run because they need vectors the demo does not ship: the generated-position-1 direction AUC, the spec-mean direction AUC, and the escape axis (which also uses α-1 vectors).

**Reproducibility note on the direction AUCs.** `cv_auc` lets sklearn's `PCA` choose its solver. On these 80 × 4096 training folds it chooses the *randomized* solver without a seed, so the direction AUCs change from run to run, both in the artifact and here. For U_abs at α 2, six repeated runs gave 0.36–0.44; the artifact's 0.40 is one draw, and the exact solver gives 0.42. The code is kept as it was. Every draw supports the same conclusion: within U_abs at α 2, the direction of the downstream displacement does not predict which samples escape.
''')
```

### [108] TOOL RESULT — Edit · 2026-10-26 13:29:00 UTC

```
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/.dev/make_notebook.py", "oldString": "The demo data ships the block-35 read-position vectors `R35` of the α-2 rows on the committed slots, in the artifact's load order. The spec-mean norm comes from each row's logged realised-displacement summary; the artifact took it from the fp16 vector, so the norm AUC can differ in the last digit. Three analyses are not re-run because they need vectors the demo does not ship: the generated-position-1 direction AUC, the spec-mean direction AUC, and the escape axis (which also uses α-1 vectors).\n''')", "newString": "The demo data ships the block-35 read-position vectors `R35` of the α-2 rows on the committed slots, in the artifact's load order. The spec-mean norm comes from each row's logged realised-displacement summary; the artifact took it from the fp16 vector, so the norm AUC can differ in the last digit. Three analyses are not re-run because they need vectors the demo does not ship: the generated-position-1 direction AUC, the spec-mean direction AUC, and the escape axis (which also uses α-1 vectors).\n\n**Reproducibility note on the direction AUCs.** `cv_auc` lets sklearn's `PCA` choose its solver. On these 80 × 4096 training folds it chooses the *randomized* solver without a seed, so the direction AUCs change from run to run, both in the artifact and here. For U_abs at α 2, six repeated runs gave 0.36–0.44; the artifact's 0.40 is one draw, and the exact solver gives 0.42. The code is kept as it was. Every draw supports the same conclusion: within U_abs at α 2, the direction of the downstream displacement does not predict which samples escape.\n''')", "originalFile": null, "structuredPatch": [{"oldStart": 1284, "oldLines": 6, "newStart": 1284, "newLines": 8, "lines": ["   - the unit-normalised direction of the block-35 read-position displacement (PCA-16 inside each fold).", " ", " The demo data ships the block-35 read-position vectors `R35` of the α-2 rows on the committed slots, in the artifact's load order. The spec-mean norm comes from each row's logged realised-displacement summary; the artifact took it from the fp16 vector, so the norm AUC can differ in the last digit. Three analyses are not re-run because they need vectors the demo does not ship: the generated-position-1 direction AUC, the spec-mean direction AUC, and the escape axis (which also uses α-1 vectors).", "+", "+**Reproducibility note on the direction AUCs.** `cv_auc` lets sklearn's `PCA` choose its solver. On these 80 × 4096 training folds it chooses the *randomized* solver without a seed, so the direction AUCs change from run to run, both in the artifact and here. For U_abs at α 2, six repeated runs gave 0.36–0.44; the artifact's 0.40 is one draw, and the exact solver gives 0.42. The code is kept as it was. Every draw supports the same conclusion: within U_abs at α 2, the direction of the downstream displacement does not predict which samples escape.", " ''')", " ", " code(r'''"]}], "userModified": false, "replaceAll": false}
```

### [109] TOOL CALL — Edit · 2026-10-26 13:29:00 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/.dev/make_notebook.py
OLD:     ("E2 CV AUC, R35 direction, U_abs a2", f"{stn['U_abs_alpha2 (D1+D2)']['cv_auc_R35_direction']:.3f}",
     f"{stp['U_abs_alpha2 (D1+D2)']['cv_auc_R35_direction']:.3f}"),
    ("E2 CV AUC, log norms, U_abs a2", f"{stn['U_abs_alpha2 (D1+D2)']['cv_auc_log_norms']:.3f}",
     f"{stp['U_abs_alpha2 (D1+D2)']['cv_auc_log_norms']:.3f}"),
]
summary_df = pd.DataFrame(summary_rows, columns=["quantity", "this notebook", "published (artifact)"])
summary_df["match"] = np.where(summary_df["this notebook"] == summary_df["published (artifact)"], "yes", "no")
print(f"N_BOOT = {N_BOOT}, N_FLIP = {N_FLIP}: {int((summary_df['match'] == 'yes').sum())}/{len(summary_df)} "
      f"quantities identical to the artifact\n")
NEW:     ("E2 CV AUC, log norms, U_abs a2", f"{stn['U_abs_alpha2 (D1+D2)']['cv_auc_log_norms']:.3f}",
     f"{stp['U_abs_alpha2 (D1+D2)']['cv_auc_log_norms']:.3f}"),
    ("E2 CV AUC, R35 direction, U_abs a2 (randomized PCA)", f"{stn['U_abs_alpha2 (D1+D2)']['cv_auc_R35_direction']:.3f}",
     f"{stp['U_abs_alpha2 (D1+D2)']['cv_auc_R35_direction']:.3f}"),
]
summary_df = pd.DataFrame(summary_rows, columns=["quantity", "this notebook", "published (artifact)"])
summary_df["match"] = np.where(summary_df["this notebook"] == summary_df["published (artifact)"], "yes", "no")
summary_df.loc[summary_df["quantity"].str.contains("randomized PCA"), "match"] = "varies by run"   # see section 13
n_det = int((summary_df["match"] != "varies by run").sum())
print(f"N_BOOT = {N_BOOT}, N_FLIP = {N_FLIP}: {int((summary_df['match'] == 'yes').sum())}/{n_det} "
      f"deterministic quantities identical to the artifact\n")
```

### [110] TOOL RESULT — Edit · 2026-10-26 13:29:00 UTC

```
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/.dev/make_notebook.py", "oldString": "    (\"E2 CV AUC, R35 direction, U_abs a2\", f\"{stn['U_abs_alpha2 (D1+D2)']['cv_auc_R35_direction']:.3f}\",\n     f\"{stp['U_abs_alpha2 (D1+D2)']['cv_auc_R35_direction']:.3f}\"),\n    (\"E2 CV AUC, log norms, U_abs a2\", f\"{stn['U_abs_alpha2 (D1+D2)']['cv_auc_log_norms']:.3f}\",\n     f\"{stp['U_abs_alpha2 (D1+D2)']['cv_auc_log_norms']:.3f}\"),\n]\nsummary_df = pd.DataFrame(summary_rows, columns=[\"quantity\", \"this notebook\", \"published (artifact)\"])\nsummary_df[\"match\"] = np.where(summary_df[\"this notebook\"] == summary_df[\"published (artifact)\"], \"yes\", \"no\")\nprint(f\"N_BOOT = {N_BOOT}, N_FLIP = {N_FLIP}: {int((summary_df['match'] == 'yes').sum())}/{len(summary_df)} \"\n      f\"quantities identical to the artifact\\n\")", "newString": "    (\"E2 CV AUC, log norms, U_abs a2\", f\"{stn['U_abs_alpha2 (D1+D2)']['cv_auc_log_norms']:.3f}\",\n     f\"{stp['U_abs_alpha2 (D1+D2)']['cv_auc_log_norms']:.3f}\"),\n    (\"E2 CV AUC, R35 direction, U_abs a2 (randomized PCA)\", f\"{stn['U_abs_alpha2 (D1+D2)']['cv_auc_R35_direction']:.3f}\",\n     f\"{stp['U_abs_alpha2 (D1+D2)']['cv_auc_R35_direction']:.3f}\"),\n]\nsummary_df = pd.DataFrame(summary_rows, columns=[\"quantity\", \"this notebook\", \"published (artifact)\"])\nsummary_df[\"match\"] = np.where(summary_df[\"this notebook\"] == summary_df[\"published (artifact)\"], \"yes\", \"no\")\nsummary_df.loc[summary_df[\"quantity\"].str.contains(\"randomized PCA\"), \"match\"] = \"varies by run\"   # see section 13\nn_det = int((summary_df[\"match\"] != \"varies by run\").sum())\nprint(f\"N_BOOT = {N_BOOT}, N_FLIP = {N_FLIP}: {int((summary_df['match'] == 'yes').sum())}/{n_det} \"\n      f\"deterministic quantities identical to the artifact\\n\")", "originalFile": null, "structuredPatch": [{"oldStart": 1731, "oldLines": 15, "newStart": 1731, "newLines": 17, "lines": ["      f\"{scp['T10|Y|alpha2']['phi_D1_D2_same_stream_diff_u']:.2f} / {scp['T10|A|alpha2']['phi_D1_D2_same_stream_diff_u']:.2f}\"),", "     (\"E2 P(escape a2 | escape a1), same u\", f\"{scn['T10|A|D1_alpha1_to_alpha2_same_u_same_stream']['P_escape_a2_given_escape_a1']:.2f}\",", "      f\"{scp['T10|A|D1_alpha1_to_alpha2_same_u_same_stream']['P_escape_a2_given_escape_a1']:.2f}\"),", "-    (\"E2 CV AUC, R35 direction, U_abs a2\", f\"{stn['U_abs_alpha2 (D1+D2)']['cv_auc_R35_direction']:.3f}\",", "-     f\"{stp['U_abs_alpha2 (D1+D2)']['cv_auc_R35_direction']:.3f}\"),", "     (\"E2 CV AUC, log norms, U_abs a2\", f\"{stn['U_abs_alpha2 (D1+D2)']['cv_auc_log_norms']:.3f}\",", "      f\"{stp['U_abs_alpha2 (D1+D2)']['cv_auc_log_norms']:.3f}\"),", "+    (\"E2 CV AUC, R35 direction, U_abs a2 (randomized PCA)\", f\"{stn['U_abs_alpha2 (D1+D2)']['cv_auc_R35_direction']:.3f}\",", "+     f\"{stp['U_abs_alpha2 (D1+D2)']['cv_auc_R35_direction']:.3f}\"),", " ]", " summary_df = pd.DataFrame(summary_rows, columns=[\"quantity\", \"this notebook\", \"published (artifact)\"])", " summary_df[\"match\"] = np.where(summary_df[\"this notebook\"] == summary_df[\"published (artifact)\"], \"yes\", \"no\")", "-print(f\"N_BOOT = {N_BOOT}, N_FLIP = {N_FLIP}: {int((summary_df['match'] == 'yes').sum())}/{len(summary_df)} \"", "-      f\"quantities identical to the artifact\\n\")", "+summary_df.loc[summary_df[\"quantity\"].str.contains(\"randomized PCA\"), \"match\"] = \"varies by run\"   # see section 13", "+n_det = int((summary_df[\"match\"] != \"varies by run\").sum())", "+print(f\"N_BOOT = {N_BOOT}, N_FLIP = {N_FLIP}: {int((summary_df['match'] == 'yes').sum())}/{n_det} \"", "+      f\"deterministic quantities identical to the artifact\\n\")", " print(summary_df.to_string(index=False))", " ''')", " "]}], "userModified": false, "replaceAll": false}
```

### [111] ASSISTANT · 2026-10-26 13:29:10 UTC

```
Before regenerating, I'll check the figures from the first run. F5 (the activation-space PCA), F2 (the unit maps) and F3 matter most.
```

### [112] TOOL CALL — Read · 2026-10-26 13:29:10 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/figures/F5_pca_disp35.png
```

### [113] TOOL RESULT — Read · 2026-10-26 13:29:10 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [114] TOOL CALL — Read · 2026-10-26 13:29:10 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/figures/F2_unit_heatmaps.png
```

### [115] TOOL RESULT — Read · 2026-10-26 13:29:10 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [116] SYSTEM-USER prompt · 2026-10-26 13:29:10 UTC

```
[Image: original 2188x2376, displayed at 1842x2000. Multiply coordinates by 1.19 to map to original image.]
```

### [117] TOOL CALL — Read · 2026-10-26 13:29:10 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/figures/F3_displacement_blocks.png
```

### [118] TOOL RESULT — Read · 2026-10-26 13:29:10 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [119] THINKING · 2026-10-26 13:29:20 UTC

```
All three figures (F5, F2, F3) render correctly and match the artifact's originals. Now I'll regenerate the clean notebook with the fixes and read it, as required before applying the scaling edits.
```

### [120] TOOL CALL — Bash · 2026-10-26 13:29:20 UTC

```
Regenerate clean notebook with fixes:
python3 .dev/make_notebook.py && python3 -c "
import json; nb=json.load(open('code_demo.ipynb')); print([ (c['id'], c['cell_type']) for c in nb['cells']][:8])"
```

### [121] TOOL RESULT — Bash · 2026-10-26 13:29:20 UTC

```
{"stdout": "wrote /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/code_demo.ipynb with 51 cells\n[('cell-00', 'markdown'), ('cell-01', 'code'), ('cell-02', 'code'), ('cell-03', 'code'), ('cell-04', 'code'), ('cell-05', 'markdown'), ('cell-06', 'code'), ('cell-07', 'markdown')]", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [122] TOOL CALL — Read · 2026-10-26 13:29:24 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/code_demo.ipynb
```

### [123] TOOL RESULT — Read [ERROR] · 2026-10-26 13:29:24 UTC

```
Error: File content (52377 tokens) exceeds maximum allowed tokens (25000). Use offset and limit parameters to read specific portions of the file, or search for specific content instead of reading the whole file.
```

### [124] TOOL CALL — Read · 2026-10-26 13:29:28 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/code_demo.ipynb
```

### [125] TOOL RESULT — Read [ERROR] · 2026-10-26 13:29:28 UTC

```
Error: File content (52377 tokens) exceeds maximum allowed tokens (25000). Use offset and limit parameters to read specific portions of the file, or search for specific content instead of reading the whole file.
```

### [126] TOOL CALL — Read · 2026-10-26 13:29:36 UTC

```
/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/code_demo.ipynb
```

### [127] TOOL RESULT — Read [ERROR] · 2026-10-26 13:29:36 UTC

```
Error: File content (52377 tokens) exceeds maximum allowed tokens (25000). Use offset and limit parameters to read specific portions of the file, or search for specific content instead of reading the whole file.
```

### [128] THINKING · 2026-10-26 13:29:56 UTC

```
Since the notebook exceeds Read's 25k-token limit, NotebookEdit won't work on it, so I'll instead use a small JSON-level script to edit just the config cell (cell-06) and note this workaround in the final report. First scaling pass: setting N_BOOT = 200 and N_FLIP = 10,000.
```

### [129] TOOL CALL — Bash · 2026-10-26 13:29:56 UTC

```
Scale config 10x and re-run notebook test:
cat > .dev/set_config.py <<'EOF'
"""Set N_BOOT / N_FLIP in the config cell (cell-06) of code_demo.ipynb (dev helper)."""
import json, re, sys
nb_path, n_boot, n_flip = "code_demo.ipynb", sys.argv[1], sys.argv[2]
nb = json.load(open(nb_path))
c = next(c for c in nb["cells"] if c["id"] == "cell-06")
src = "".join(c["source"])
src = re.sub(r"^N_BOOT = [0-9_]+ ", f"N_BOOT = {n_boot}".ljust(len("N_BOOT = 20")) + " ", src, flags=re.M)
src = re.sub(r"^N_FLIP = [0-9_]+ ", f"N_FLIP = {n_flip}".ljust(len("N_FLIP = 1_000")) + " ", src, flags=re.M)
lines = src.split("\n")
c["source"] = [l + "\n" for l in lines[:-1]] + [lines[-1]]
json.dump(nb, open(nb_path, "w"), indent=1, ensure_ascii=False)
open(nb_path, "a").write("\n")
print(src)
EOF
python3 .dev/set_config.py 200 10_000 && UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_8O5eaNc5gxJs-e3ffb3a2e51e && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_8O5eaNc5gxJs-e3ffb3a2e51e/bin/python jupyter ipykernel && t0=$(date +%s) && /tmp/aii_nb_test_envs/art_8O5eaNc5gxJs-e3ffb3a2e51e/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | grep -v "TCP without encryption" | tail -20; echo "EXIT ${PIPESTATUS[0]} runtime $(( $(date +%s) - t0 ))s"
```

### [130] TOOL RESULT — Bash · 2026-10-26 13:30:40 UTC

```
{"stdout": "# ---- tunable parameters (original values in the comments) ----\nN_BOOT = 200            # slot-cluster bootstrap replicates behind every 95% CI              (original: 2000)\nN_FLIP = 10_000         # Monte-Carlo sign flips when a contrast has > 20 non-zero slots      (original: 100_000)\nBOOT_SEED = 20261022   # seed of the bootstraps and of the Monte-Carlo sign flips            (original: 20261022)\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[NbConvertApp] Writing 798627 bytes to code_demo.ipynb\nEXIT 0 runtime 40s", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [131] THINKING · 2026-10-26 13:30:50 UTC

```
Round 1 finished in 40s and stayed cheap, so I'll run round 2 with the original N_BOOT=2000 and N_FLIP=100,000, plus the comment alignment fix—first checking round 1's timing and match count.
```

### [132] TOOL CALL — Bash · 2026-10-26 13:30:50 UTC

```
Check round-1 results and set original config values:
python3 - <<'EOF'
import json
nb = json.load(open("code_demo.ipynb"))
for c in nb["cells"]:
    if c["cell_type"] != "code":
        continue
    txt = "".join("".join(o.get("text", "")) for o in c.get("outputs", []) if o["output_type"] == "stream")
    for line in txt.splitlines():
        if "took" in line or "deterministic quantities" in line or "ERROR" in line or "Warning" in line:
            print(c["id"], "|", line)
    for o in c.get("outputs", []):
        if o["output_type"] == "error":
            print(c["id"], "ERROR", o["ename"], o["evalue"])
EOF
python3 - <<'EOF'
import json
p = "code_demo.ipynb"
nb = json.load(open(p))
c = next(c for c in nb["cells"] if c["id"] == "cell-06")
src = """# ---- tunable parameters (original values in the comments) ----
N_BOOT = 2000          # slot-cluster bootstrap replicates behind every 95% CI              (original: 2000)
N_FLIP = 100_000       # Monte-Carlo sign flips when a contrast has > 20 non-zero slots      (original: 100_000)
BOOT_SEED = 20261022   # seed of the bootstraps and of the Monte-Carlo sign flips            (original: 20261022)"""
lines = src.split("\n")
c["source"] = [l + "\n" for l in lines[:-1]] + [lines[-1]]
open(p, "w").write(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")
print(src)
EOF
```

### [133] TOOL RESULT — Bash · 2026-10-26 13:30:50 UTC

```
{"stdout": "cell-33 | s1() took 0.3s with N_BOOT=200, N_FLIP=10000\ncell-49 | N_BOOT = 200, N_FLIP = 10000: 15/22 deterministic quantities identical to the artifact\n# ---- tunable parameters (original values in the comments) ----\nN_BOOT = 2000          # slot-cluster bootstrap replicates behind every 95% CI              (original: 2000)\nN_FLIP = 100_000       # Monte-Carlo sign flips when a contrast has > 20 non-zero slots      (original: 100_000)\nBOOT_SEED = 20261022   # seed of the bootstraps and of the Monte-Carlo sign flips            (original: 20261022)", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [134] TOOL CALL — Bash · 2026-10-26 13:31:02 UTC

```
Run notebook with original parameter values:
UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_8O5eaNc5gxJs-e3ffb3a2e51e && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_8O5eaNc5gxJs-e3ffb3a2e51e/bin/python jupyter ipykernel && t0=$(date +%s) && /tmp/aii_nb_test_envs/art_8O5eaNc5gxJs-e3ffb3a2e51e/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | grep -v "TCP without encryption" | tail -20; echo "EXIT ${PIPESTATUS[0]} runtime $(( $(date +%s) - t0 ))s"; python3 - <<'EOF'
import json
nb = json.load(open("code_demo.ipynb"))
for c in nb["cells"]:
    if c["cell_type"] != "code":
        continue
    for o in c.get("outputs", []):
        if o["output_type"] == "error":
            print(c["id"], "ERROR", o["ename"], o["evalue"])
    txt = "".join("".join(o.get("text", "")) for o in c.get("outputs", []) if o["output_type"] == "stream")
    if c["id"] in ("cell-33", "cell-49", "cell-39"):
        print(f"===== {c['id']}\n{txt[:4000]}")
EOF
```

### [135] TOOL RESULT — Bash · 2026-10-26 13:31:42 UTC

```
{"stdout": "[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[NbConvertApp] Writing 798732 bytes to code_demo.ipynb\nEXIT 0 runtime 40s\n===== cell-33\ns1() took 1.0s with N_BOOT=2000, N_FLIP=100000\n\nDECISION (T10, alpha 2, outcome Y): UNIT\nshares: {'D1': 0.5, 'D2': 0.52, 'D3': 0.1, 'D4': 0.02} (paired slots: 50)\n  RD_unit +0.450  95% CI [+0.350, +0.550]  sign-flip p 1e-05  Holm 3e-05\n  RD_seed +0.030  95% CI [-0.070, +0.140]  sign-flip p 0.72  Holm 0.81\n  RD_int  -0.100  95% CI [-0.280, +0.080]  sign-flip p 0.41  Holm 0.81\n  ConditionalLogit: beta_unit +4.34 (p 0.00011), beta_seed +1.68 (p 0.13), beta_unit:seed -1.77 (p 0.14)\n\nall T10 2x2 tables (task|alpha|outcome):\n             n_slots    D1    D2   D3    D4 RD_unit RD_seed   INT decision rule\nT10|a1|Y          50  0.12  0.14  0.0  0.02    0.12   -0.02   0.0          UNIT\nT10|a1|Y_any      50  0.12  0.14  0.0  0.02    0.12   -0.02   0.0          UNIT\nT10|a1|A          50  0.12  0.14  0.0  0.02    0.12   -0.02   0.0          UNIT\nT10|a2|Y          50   0.5  0.52  0.1  0.02    0.45    0.03  -0.1          UNIT\nT10|a2|Y_any      50   0.5  0.52  0.1  0.02    0.45    0.03  -0.1          UNIT\nT10|a2|A          50  0.52  0.52  0.1  0.02    0.46    0.04 -0.08          UNIT\n\nD5 split (T10, alpha 2):\n  Y: shares D1 0.50, D5 0.28, D3 0.10\n     profile_at_matched_energy (D1 - D5)    RD +0.22 [+0.08, +0.36]  McNemar 13:2, p 0.00739\n     energy_at_banfree_shape (D5 - D3)      RD +0.18 [+0.06, +0.30]  McNemar 10:1, p 0.0117\n  A: shares D1 0.52, D5 0.34, D3 0.10\n     profile_at_matched_energy (D1 - D5)    RD +0.18 [+0.02, +0.34]  McNemar 13:4, p 0.049\n     energy_at_banfree_shape (D5 - D3)      RD +0.24 [+0.12, +0.38]  McNemar 13:1, p 0.00183\n\nmediation (T10, outcome Y; reference design D1):\n           without mediators  with log-norm mediators\nD2                      0.11                     0.13\nD3                     -2.35                    -2.54\nD4                     -3.31                    -3.49\nD5                     -0.93                    -0.92\nalpha2                  1.94                     2.21\nlog_S_b35                NaN                    -0.37\nlog_R_b35                NaN                     0.01\nCV AUC of A from the two downstream norms: 0.77\n\n===== cell-39\n13:31:33|INFO   |T10_fresh_k10_19: shares {'D1': 0.42, 'D2': 0.6, 'D3': 0.08, 'D4': 0.1} RD_unit 0.420 (0.32, 0.52) RD_seed -0.100 (-0.22, 0.02) INT -0.160 -> UNIT\n13:31:33|INFO   |T10_pooled_k0_19: shares {'D1': 0.46, 'D2': 0.56, 'D3': 0.09, 'D4': 0.06} RD_unit 0.435 (0.36, 0.515) RD_seed -0.035 (-0.11512499999999999, 0.045) INT -0.130 -> UNIT\nT10_fresh_k10_19: PTOP_vs_PREST 0.48 vs 0.18 (McNemar 15:0, p 6.1e-05); D1_vs_PSHUF 0.42 vs 0.08 (McNemar 17:0, p 1.5e-05); D1_vs_PTOP 0.42 vs 0.48 (McNemar 4:7, p 0.55)\nT10_pooled_k0_19: PTOP_vs_PREST 0.53 vs 0.24 (McNemar 33:4, p 1.1e-06); D1_vs_PSHUF 0.46 vs 0.08 (McNemar 38:0, p 7.3e-12); D1_vs_PTOP 0.46 vs 0.53 (McNemar 8:15, p 0.21)\nT03_k0_9: INCOMPLETE (T03 is not in the demo data)\n\n===== cell-49\nN_BOOT = 2000, N_FLIP = 100000: 22/22 deterministic quantities identical to the artifact\n\n                                           quantity                  this notebook           published (artifact)         match\n A1: D1 attempted off-default, T10 a2 (exp29 25/50)                          26/50                          26/50           yes\n            A1: per-slot label agreement with exp29                           0.98                           0.98           yes\n            A2: D4 correct off-default (exp27 1/50)                           1/50                           1/50           yes\n                   S1 shares Y, D1/D2/D3/D4, T10 a2            0.50/0.52/0.10/0.02            0.50/0.52/0.10/0.02           yes\n                         S1 unit effect RD [95% CI]          +0.450 [+0.35, +0.55]          +0.450 [+0.35, +0.55]           yes\n                         S1 seed effect RD [95% CI]          +0.030 [-0.07, +0.14]          +0.030 [-0.07, +0.14]           yes\n                            S1 interaction [95% CI]          -0.100 [-0.28, +0.08]          -0.100 [-0.28, +0.08]           yes\n                                    S1 Holm p, unit                          3e-05                          3e-05           yes\n                     S1 conditional logit beta_unit                           4.34                           4.34           yes\n                       S1 decision (committed rule)                           UNIT                           UNIT           yes\n                                 D5 (U_bf*) share Y                           0.28                           0.28           yes\n        D5 split: profile at matched energy (D1-D5)          +0.220 [+0.08, +0.36]          +0.220 [+0.08, +0.36]           yes\n         D5 split: energy at ban-free shape (D5-D3)          +0.180 [+0.06, +0.30]          +0.180 [+0.06, +0.30]           yes\n                    S2 P_top vs P_rest (Y, McNemar)  0.58 vs 0.30 (18:4, p 0.0043)  0.58 vs 0.30 (18:4, p 0.0043)           yes\n                       S2 D1 vs P_shuf (Y, McNemar) 0.50 vs 0.08 (21:0, p 9.5e-07) 0.50 vs 0.08 (21:0, p 9.5e-07)           yes\n                                         S2 reading    PUSHES ACT WHERE BANS WRITE    PUSHES ACT WHERE BANS WRITE           yes\n                  E1 D3 (U_bf) Y at alpha 3 / 4 / 6                    9 / 20 / 14                    9 / 20 / 14           yes\n            E3 fresh slots k10-19: unit RD [95% CI]          +0.420 [+0.32, +0.52]          +0.420 [+0.32, +0.52]           yes\n                  E3 pooled k0-19: unit RD [95% CI]          +0.435 [+0.36, +0.52]          +0.435 [+0.36, +0.52]           yes\n                  E2 phi(D1, D2) same stream, Y / A                    0.16 / 0.20                    0.16 / 0.20           yes\n                E2 P(escape a2 | escape a1), same u                           0.33                           0.33           yes\n                     E2 CV AUC, log norms, U_abs a2                          0.523                          0.523           yes\nE2 CV AUC, R35 direction, U_abs a2 (randomized PCA)                          0.431                          0.398 varies by run", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [136] THINKING · 2026-10-26 13:32:26 UTC

```
Round 2 passed in 40s with original parameters—all 22 deterministic quantities match the artifact exactly, and the randomized-PCA AUC (0.431) falls within the documented spread. TODO 5 is complete; next I'll scan the executed notebook for leftover stderr warnings and absolute server paths before publishing.
```

### [137] TOOL CALL — Bash · 2026-10-26 13:32:26 UTC

```
Scan executed notebook for stderr and absolute paths:
python3 - <<'EOF'
import json, re
nb = json.load(open("code_demo.ipynb"))
for c in nb["cells"]:
    for o in c.get("outputs", []):
        if o["output_type"] == "stream" and o["name"] == "stderr":
            print(c["id"], "STDERR:", "".join(o["text"])[:600])
raw = open("code_demo.ipynb").read()
for pat in ("/ai-inventor", "/tmp/", "run_0oWBKrKEGsmU", "aii-agent", "marko"):
    print(pat, "occurrences:", raw.count(pat))
EOF
ls -la; du -sh figures results logs .dev 2>/dev/null
```

### [138] TOOL RESULT — Bash · 2026-10-26 13:32:26 UTC

```
{"stdout": "/ai-inventor occurrences: 1\n/tmp/ occurrences: 0\nrun_0oWBKrKEGsmU occurrences: 0\naii-agent occurrences: 0\nmarko occurrences: 0\ntotal 16613\ndrwxrwxrwx 7 aii-agent aii-agent 2000878 Oct 26 13:26 .\ndrwxrwxrwx 9 aii-agent aii-agent 2002618 Oct 26 13:05 ..\ndrwxrwxrwx 2 aii-agent aii-agent       1 Oct 26 12:59 .aii\n-rw-rw-rw- 1 aii-agent aii-agent      54 Oct 26 12:59 .aii_claude_session.json\ndrwxrwxrwx 2 aii-agent aii-agent 1009794 Oct 26 13:29 .dev\n-rw-rw-rw- 1 aii-agent aii-agent 1390702 Oct 26 13:32 .repl_agent.ptylog\n-rw-rw-rw- 1 aii-agent aii-agent    9950 Oct 26 13:19 build_mini_demo_data.py\n-rw-rw-rw- 1 aii-agent aii-agent  798888 Oct 26 13:31 code_demo.ipynb\ndrwxrwxrwx 2 aii-agent aii-agent 2000102 Oct 26 13:26 figures\ndrwxrwxrwx 2 aii-agent aii-agent 1000297 Oct 26 13:26 logs\n-rw-rw-rw- 1 aii-agent aii-agent 5792484 Oct 26 13:19 mini_demo_data.json\ndrwxrwxrwx 2 aii-agent aii-agent 1004527 Oct 26 13:31 results\n3.0M\tfigures\n1.1M\tresults\n980K\tlogs\n1.1M\t.dev", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [139] ASSISTANT · 2026-10-26 13:32:32 UTC

```
No stderr output remains, but there's one `/ai-inventor` string in the notebook. I'll find it.
```

### [140] TOOL CALL — Bash · 2026-10-26 13:32:32 UTC

```
Locate absolute path string in notebook and data:
grep -o ".\{200\}/ai-inventor.\{120\}" code_demo.ipynb | head -3; grep -rn "ai-inventor" mini_demo_data.json | head -2 | cut -c1-300; python3 -c "
import json; d=json.load(open('mini_demo_data.json')); s=json.dumps(d); i=s.find('/ai-inventor'); print('data occurrences', s.count('/ai-inventor'), s[max(0,i-200):i+100] if i>=0 else '')"
```

### [141] TOOL RESULT — Bash · 2026-10-26 13:32:32 UTC

```
{"stdout": "data occurrences 0", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [142] TOOL CALL — Bash · 2026-10-26 13:32:36 UTC

```
Show context around absolute path string:
python3 - <<'EOF'
raw = open("code_demo.ipynb").read()
i = raw.find("/ai-inventor")
print(repr(raw[max(0, i - 300): i + 150]))
EOF
```

### [143] TOOL RESULT — Bash · 2026-10-26 13:32:36 UTC

```
{"stdout": "'10-26T13:31:29.858200Z\",\\n     \"iopub.status.busy\": \"2026-10-26T13:31:29.857997Z\",\\n     \"iopub.status.idle\": \"2026-10-26T13:31:29.860992Z\",\\n     \"shell.execute_reply\": \"2026-10-26T13:31:29.860607Z\"\\n    }\\n   },\\n   \"outputs\": [],\\n   \"source\": [\\n    \"GITHUB_DATA_URL = \\\\\"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-7/experiment-36/demo/mini_demo_data.json\\\\'", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [144] THINKING · 2026-10-26 13:33:00 UTC

```
No hidden server path found—just the GitHub URL mention. I'll finalize the generator with the original config defaults plus a runtime note, soften the overly strong conclusion to match the E1 evidence, then regenerate and run a final clean test.
```

### [145] TOOL CALL — Edit · 2026-10-26 13:33:00 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/.dev/make_notebook.py
OLD: ## Configuration
Only the resampling sizes of the statistics drive the runtime. Every published number used the original values, which are given in the comments. Re-run the cells below after changing them: `boot_ci` and `sign_flip_p` bind these values when they are defined.
''')

code(r'''
# ---- tunable parameters (original values in the comments) ----
N_BOOT = 20            # slot-cluster bootstrap replicates behind every 95% CI              (original: 2000)
N_FLIP = 1_000         # Monte-Carlo sign flips when a contrast has > 20 non-zero slots      (original: 100_000)
BOOT_SEED = 20261022   # seed of the bootstraps and of the Monte-Carlo sign flips            (original: 20261022)
''')
NEW: ## Configuration
Only the resampling sizes of the statistics drive the runtime. The values below are the artifact's original ones: 2,000 bootstrap replicates and 100,000 Monte-Carlo sign flips. With them, the whole notebook ran in about 40 s on a 2-core CPU, install cell included. That was measured over three test runs, scaling from 20 / 1,000 through 200 / 10,000 to these values.

For a faster pass, lower them, for example to `N_BOOT = 200` and `N_FLIP = 10_000`. Counts, shares, McNemar tables and decisions do not depend on these values; the CI endpoints and Monte-Carlo p-values do. After changing them, re-run the cells below, because `boot_ci` and `sign_flip_p` bind these values when they are defined.
''')

code(r'''
# ---- tunable parameters (original values in the comments) ----
N_BOOT = 2000          # slot-cluster bootstrap replicates behind every 95% CI              (original: 2000)
N_FLIP = 100_000       # Monte-Carlo sign flips when a contrast has > 20 non-zero slots      (original: 100_000)
BOOT_SEED = 20261022   # seed of the bootstraps and of the Monte-Carlo sign flips            (original: 20261022)
''')
```

### [146] TOOL RESULT — Edit · 2026-10-26 13:33:00 UTC

```
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/.dev/make_notebook.py", "oldString": "## Configuration\nOnly the resampling sizes of the statistics drive the runtime. Every published number used the original values, which are given in the comments. Re-run the cells below after changing them: `boot_ci` and `sign_flip_p` bind these values when they are defined.\n''')\n\ncode(r'''\n# ---- tunable parameters (original values in the comments) ----\nN_BOOT = 20            # slot-cluster bootstrap replicates behind every 95% CI              (original: 2000)\nN_FLIP = 1_000         # Monte-Carlo sign flips when a contrast has > 20 non-zero slots      (original: 100_000)\nBOOT_SEED = 20261022   # seed of the bootstraps and of the Monte-Carlo sign flips            (original: 20261022)\n''')", "newString": "## Configuration\nOnly the resampling sizes of the statistics drive the runtime. The values below are the artifact's original ones: 2,000 bootstrap replicates and 100,000 Monte-Carlo sign flips. With them, the whole notebook ran in about 40 s on a 2-core CPU, install cell included. That was measured over three test runs, scaling from 20 / 1,000 through 200 / 10,000 to these values.\n\nFor a faster pass, lower them, for example to `N_BOOT = 200` and `N_FLIP = 10_000`. Counts, shares, McNemar tables and decisions do not depend on these values; the CI endpoints and Monte-Carlo p-values do. After changing them, re-run the cells below, because `boot_ci` and `sign_flip_p` bind these values when they are defined.\n''')\n\ncode(r'''\n# ---- tunable parameters (original values in the comments) ----\nN_BOOT = 2000          # slot-cluster bootstrap replicates behind every 95% CI              (original: 2000)\nN_FLIP = 100_000       # Monte-Carlo sign flips when a contrast has > 20 non-zero slots      (original: 100_000)\nBOOT_SEED = 20261022   # seed of the bootstraps and of the Monte-Carlo sign flips            (original: 20261022)\n''')", "originalFile": null, "structuredPatch": [{"oldStart": 140, "oldLines": 13, "newStart": 140, "newLines": 15, "lines": [" ", " md(r'''", " ## Configuration", "-Only the resampling sizes of the statistics drive the runtime. Every published number used the original values, which are given in the comments. Re-run the cells below after changing them: `boot_ci` and `sign_flip_p` bind these values when they are defined.", "+Only the resampling sizes of the statistics drive the runtime. The values below are the artifact's original ones: 2,000 bootstrap replicates and 100,000 Monte-Carlo sign flips. With them, the whole notebook ran in about 40 s on a 2-core CPU, install cell included. That was measured over three test runs, scaling from 20 / 1,000 through 200 / 10,000 to these values.", "+", "+For a faster pass, lower them, for example to `N_BOOT = 200` and `N_FLIP = 10_000`. Counts, shares, McNemar tables and decisions do not depend on these values; the CI endpoints and Monte-Carlo p-values do. After changing them, re-run the cells below, because `boot_ci` and `sign_flip_p` bind these values when they are defined.", " ''')", " ", " code(r'''", " # ---- tunable parameters (original values in the comments) ----", "-N_BOOT = 20            # slot-cluster bootstrap replicates behind every 95% CI              (original: 2000)", "-N_FLIP = 1_000         # Monte-Carlo sign flips when a contrast has > 20 non-zero slots      (original: 100_000)", "+N_BOOT = 2000          # slot-cluster bootstrap replicates behind every 95% CI              (original: 2000)", "+N_FLIP = 100_000       # Monte-Carlo sign flips when a contrast has > 20 non-zero slots      (original: 100_000)", " BOOT_SEED = 20261022   # seed of the bootstraps and of the Monte-Carlo sign flips            (original: 20261022)", " ''')", " "]}], "userModified": false, "replaceAll": false}
```

### [147] TOOL CALL — Edit · 2026-10-26 13:33:00 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/.dev/make_notebook.py
OLD: In short, a random push moves the model off its default algorithm only when the push has the **shape of what a ban writes**: concentrated on the few task tokens where the ban's displacement is largest. That shape matters more than the push's raw size or its random direction. Even so, the push lands on *known* alternatives (DFS, BFS), not on novel algorithms.
NEW: In short, the S1 numbers above show that a random internal push moves Qwen3-8B off its default algorithm far more often when the push has the **shape of what a ban writes** than when it is spread flat over the prompt. A ban's shape is concentrated on the few task tokens where the ban's own displacement is largest.
- **Shape, not seeds.** Which seed scheme drew the direction does not matter.
- **Dose.** The flat, ban-free unit needs about twice the dose (α 4) to approach the ban-shaped unit at α 2, and at α 6 it breaks the programs.
- **Size, not mediator.** The size of the displacement that reaches the last block does not explain the difference.
- **Which samples escape is close to a coin flip per direction.**
- **No novelty.** The escapes land on *known* alternatives (DFS, BFS), not on novel algorithms.
```

### [148] TOOL RESULT — Edit · 2026-10-26 13:33:00 UTC

```
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/.dev/make_notebook.py", "oldString": "In short, a random push moves the model off its default algorithm only when the push has the **shape of what a ban writes**: concentrated on the few task tokens where the ban's displacement is largest. That shape matters more than the push's raw size or its random direction. Even so, the push lands on *known* alternatives (DFS, BFS), not on novel algorithms.", "newString": "In short, the S1 numbers above show that a random internal push moves Qwen3-8B off its default algorithm far more often when the push has the **shape of what a ban writes** than when it is spread flat over the prompt. A ban's shape is concentrated on the few task tokens where the ban's own displacement is largest.\n- **Shape, not seeds.** Which seed scheme drew the direction does not matter.\n- **Dose.** The flat, ban-free unit needs about twice the dose (α 4) to approach the ban-shaped unit at α 2, and at α 6 it breaks the programs.\n- **Size, not mediator.** The size of the displacement that reaches the last block does not explain the difference.\n- **Which samples escape is close to a coin flip per direction.**\n- **No novelty.** The escapes land on *known* alternatives (DFS, BFS), not on novel algorithms.", "originalFile": null, "structuredPatch": [{"oldStart": 1754, "oldLines": 7, "newStart": 1754, "newLines": 12, "lines": [" - **D\\* and the S3 prices.** These need all five tasks, the iteration-5 knob rows and exp27's full-simplex hull. Plan noise at D\\* = D1 matches or beats base-model-written intents on 2 of 5 tasks (T03, T1); the committed prediction was 3. Iteration 5's rule, replayed, is still DISCONFIRMED, but the mean margin moves from −0.40 to +0.12.", " - **The novelty audit.** All five correct \"other\" programs are catalogue variants: 0 novel algorithms.", " ", "-In short, a random push moves the model off its default algorithm only when the push has the **shape of what a ban writes**: concentrated on the few task tokens where the ban's displacement is largest. That shape matters more than the push's raw size or its random direction. Even so, the push lands on *known* alternatives (DFS, BFS), not on novel algorithms.", "+In short, the S1 numbers above show that a random internal push moves Qwen3-8B off its default algorithm far more often when the push has the **shape of what a ban writes** than when it is spread flat over the prompt. A ban's shape is concentrated on the few task tokens where the ban's own displacement is largest.", "+- **Shape, not seeds.** Which seed scheme drew the direction does not matter.", "+- **Dose.** The flat, ban-free unit needs about twice the dose (α 4) to approach the ban-shaped unit at α 2, and at α 6 it breaks the programs.", "+- **Size, not mediator.** The size of the displacement that reaches the last block does not explain the difference.", "+- **Which samples escape is close to a coin flip per direction.**", "+- **No novelty.** The escapes land on *known* alternatives (DFS, BFS), not on novel algorithms.", " ''')", " ", " # ====================================================================================================================="]}], "userModified": false, "replaceAll": false}
```

### [149] ASSISTANT · 2026-10-26 13:33:14 UTC

```
Before the final run, one fact check. The markdown quotes the ban as "Do not use union-find", and I want the exact wording from the vendored prompts rather than a paraphrase.
```

### [150] TOOL CALL — Bash · 2026-10-26 13:33:14 UTC

```
Check ban vs twin prompt wording for T10:
python3 -I -c "
import json
from collections import Counter
p='/ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36/vendor/exp22/prompts/prompts4.jsonl'
rows=[json.loads(l) for l in open(p)]
print(Counter(r['kind'] for r in rows))
for r in rows:
    if r['task']=='T10' and r.get('template_id')=='W1':
        print(r['kind'], '|', r['pid'], '|', repr(r['user_text'][:120]))
"
```

### [151] TOOL RESULT — Bash · 2026-10-26 13:33:14 UTC

```
{"stdout": "Counter({'named': 1950, 'masked': 1950, 'twin': 75, 'ban': 70, 'knob_nonce': 60, 'plain': 15, 'knob_novelty': 14, 'knob_mention': 10})\nban | T10|ban|union_find|W1|- | 'Do not use union-find (disjoint set union) for this task.\\n\\nTask: write a Python function solve(n, edges) that returns th'\ntwin | T10|twin|-|W1|- | 'Do not use ship for this task. . . . . . . .\\n\\nTask: write a Python function solve(n, edges) that returns the number of c'\nknob_nonce | T10|knob_nonce|-|W1|- | 'Do not use the Zorblax method for this task.\\n\\nTask: write a Python function solve(n, edges) that returns the number of c'", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [152] THINKING · 2026-10-26 13:33:30 UTC

```
The wording is confirmed: the ban is on union-find (disjoint set union), with a length-matched decoy banning "ship." I'll add this exact wording to the markdown, then regenerate and run the final test.
```

### [153] TOOL CALL — Edit · 2026-10-26 13:33:30 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/.dev/make_notebook.py
OLD: it writes **union-find** on 50 of 50 clean samples. A prompt *ban* ("Do not use union-find") does move it, because the ban writes a displacement into the residual stream at the task-specification tokens. **Plan noise (PN)** asks whether a *random* internal push does the same.
NEW: it writes **union-find** on 50 of 50 clean samples. A prompt *ban* ("Do not use union-find (disjoint set union) for this task.") does move it, and the ban leaves a measurable displacement in the residual stream at the task-specification tokens. Every prompt has a length-matched **twin** in which the banned name is replaced by an unrelated noun ("Do not use ship for this task. . . . . . . ."). Plan noise is applied to the twin, and the unpushed twin is each slot's clean reference. **Plan noise (PN)** asks whether a *random* internal push does the same as the ban.
```

### [154] TOOL RESULT — Edit · 2026-10-26 13:33:30 UTC

```
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/.dev/make_notebook.py", "oldString": "it writes **union-find** on 50 of 50 clean samples. A prompt *ban* (\"Do not use union-find\") does move it, because the ban writes a displacement into the residual stream at the task-specification tokens. **Plan noise (PN)** asks whether a *random* internal push does the same.", "newString": "it writes **union-find** on 50 of 50 clean samples. A prompt *ban* (\"Do not use union-find (disjoint set union) for this task.\") does move it, and the ban leaves a measurable displacement in the residual stream at the task-specification tokens. Every prompt has a length-matched **twin** in which the banned name is replaced by an unrelated noun (\"Do not use ship for this task. . . . . . . .\"). Plan noise is applied to the twin, and the unpushed twin is each slot's clean reference. **Plan noise (PN)** asks whether a *random* internal push does the same as the ban.", "originalFile": null, "structuredPatch": [{"oldStart": 21, "oldLines": 7, "newStart": 21, "newLines": 7, "lines": [" # Why random nudges stopped changing the algorithm", " **Plan-noise crosswalk on Qwen3-8B: dose unit × direction seeds** — iteration 7, step K of a study of whether an LLM can be pushed, from *inside*, into writing a different algorithm than its default one.", " ", "-**Background.** Qwen3-8B (instruct, bf16, thinking off) nearly always writes one default algorithm per task. For **T10**, *\"write `solve(n, edges)` that returns the number of connected components of an undirected graph\"*, it writes **union-find** on 50 of 50 clean samples. A prompt *ban* (\"Do not use union-find\") does move it, because the ban writes a displacement into the residual stream at the task-specification tokens. **Plan noise (PN)** asks whether a *random* internal push does the same. During the prompt prefill only, a fresh isotropic random direction `u` (one per sample) is pushed into decoder blocks 12–23 at the task-spec positions. The edit is displacement-targeted:", "+**Background.** Qwen3-8B (instruct, bf16, thinking off) nearly always writes one default algorithm per task. For **T10**, *\"write `solve(n, edges)` that returns the number of connected components of an undirected graph\"*, it writes **union-find** on 50 of 50 clean samples. A prompt *ban* (\"Do not use union-find (disjoint set union) for this task.\") does move it, and the ban leaves a measurable displacement in the residual stream at the task-specification tokens. Every prompt has a length-matched **twin** in which the banned name is replaced by an unrelated noun (\"Do not use ship for this task. . . . . . . .\"). Plan noise is applied to the twin, and the unpushed twin is each slot's clean reference. **Plan noise (PN)** asks whether a *random* internal push does the same as the ban. During the prompt prefill only, a fresh isotropic random direction `u` (one per sample) is pushed into decoder blocks 12–23 at the task-spec positions. The edit is displacement-targeted:", " ", " `h ← h + (α·n[l,p] − (h − h_twin)·u) u`", " "]}], "userModified": false, "replaceAll": false}
```

### [155] TOOL CALL — Edit · 2026-10-26 13:33:30 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/.dev/make_notebook.py
OLD: - **`U_abs[l, p]`**: the ban's own displacement norm. It measures how far the prompt "Do not use union-find" moves the residual stream at block `l`, task-spec token `p`, relative to a matched twin prompt (exp13/exp19). It is a [12 × |S|] map: blocks 12–23 × 145 spec tokens for T10.
NEW: - **`U_abs[l, p]`**: the ban's own displacement norm. It measures how far the ban sentence moves the residual stream at block `l`, task-spec token `p`, relative to its length-matched twin prompt (measured in exp13/exp19; one map per task). It is a [12 × |S|] map: blocks 12–23 × 145 spec tokens for T10.
```

### [156] TOOL RESULT — Edit · 2026-10-26 13:33:30 UTC

```
{"filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/.dev/make_notebook.py", "oldString": "- **`U_abs[l, p]`**: the ban's own displacement norm. It measures how far the prompt \"Do not use union-find\" moves the residual stream at block `l`, task-spec token `p`, relative to a matched twin prompt (exp13/exp19). It is a [12 × |S|] map: blocks 12–23 × 145 spec tokens for T10.", "newString": "- **`U_abs[l, p]`**: the ban's own displacement norm. It measures how far the ban sentence moves the residual stream at block `l`, task-spec token `p`, relative to its length-matched twin prompt (measured in exp13/exp19; one map per task). It is a [12 × |S|] map: blocks 12–23 × 145 spec tokens for T10.", "originalFile": null, "structuredPatch": [{"oldStart": 452, "oldLines": 7, "newStart": 452, "newLines": 7, "lines": [" ", " md(r'''", " ## 5. Dose units and direction seeds (`src/k_units.py`)", "-- **`U_abs[l, p]`**: the ban's own displacement norm. It measures how far the prompt \"Do not use union-find\" moves the residual stream at block `l`, task-spec token `p`, relative to a matched twin prompt (exp13/exp19). It is a [12 × |S|] map: blocks 12–23 × 145 spec tokens for T10.", "+- **`U_abs[l, p]`**: the ban's own displacement norm. It measures how far the ban sentence moves the residual stream at block `l`, task-spec token `p`, relative to its length-matched twin prompt (measured in exp13/exp19; one map per task). It is a [12 × |S|] map: blocks 12–23 × 145 spec tokens for T10.", " - **`U_bf[l, p] = ‖h_twin[l, p]‖ · r_Q(l)`**: iteration 5's ban-free unit. It is the twin's own residual norm times a per-depth ratio `r_Q`, exp23's median relative ban displacement of Qwen at that depth.", " - **`U_bf*`**: U_bf's within-block profile rescaled to U_abs's per-block energy (design D5).", " - **`P_top`, `P_rest`, `P_shuf`**: U_abs restricted to its top-quartile cells, to the other cells, or with its spec positions permuted. `P_top` and `P_rest` are rescaled to U_abs's Frobenius norm, and their masked cells are not edited."]}], "userModified": false, "replaceAll": false}
```

### [157] ASSISTANT · 2026-10-26 13:33:44 UTC

```
Now the final clean test: regenerate the notebook, clear the old run outputs, recreate the venv, and execute with the exact prescribed commands.
```

### [158] TOOL CALL — Bash · 2026-10-26 13:33:44 UTC

```
Final clean regeneration and notebook test run:
rm -rf figures results logs && python3 .dev/make_notebook.py && grep -c "N_BOOT = 2000 " code_demo.ipynb && UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_8O5eaNc5gxJs-e3ffb3a2e51e && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_8O5eaNc5gxJs-e3ffb3a2e51e/bin/python jupyter ipykernel && t0=$(date +%s) && /tmp/aii_nb_test_envs/art_8O5eaNc5gxJs-e3ffb3a2e51e/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | grep -v "TCP without encryption" | tail -20; echo "EXIT ${PIPESTATUS[0]} runtime $(( $(date +%s) - t0 ))s"; python3 - <<'EOF'
import json
nb = json.load(open("code_demo.ipynb"))
n_err = n_img = n_code = n_exec = 0
for c in nb["cells"]:
    if c["cell_type"] != "code":
        continue
    n_code += 1
    n_exec += c.get("execution_count") is not None
    for o in c.get("outputs", []):
        if o["output_type"] == "error":
            n_err += 1
            print(c["id"], "ERROR", o["ename"], o["evalue"])
        if o["output_type"] == "stream" and o["name"] == "stderr":
            print(c["id"], "STDERR", "".join(o["text"])[:300])
        if o["output_type"] == "display_data" and "image/png" in o["data"]:
            n_img += 1
print(f"cells {len(nb['cells'])}, code {n_code}, executed {n_exec}, errors {n_err}, figures {n_img}")
txt = "".join("".join(o.get("text", "")) for c in nb["cells"] for o in c.get("outputs", []) if o["output_type"] == "stream")
for line in txt.splitlines():
    if "deterministic quantities" in line or "took" in line or "DECISION" in line or "reading (T10)" in line:
        print(line)
EOF
```

### [159] TOOL RESULT — Bash · 2026-10-26 13:34:24 UTC

```
{"stdout": "wrote /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/code_demo.ipynb with 51 cells\n1\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[NbConvertApp] Writing 799904 bytes to code_demo.ipynb\nEXIT 0 runtime 41s\ncells 51, code 30, executed 30, errors 0, figures 7\ns1() took 1.0s with N_BOOT=2000, N_FLIP=100000\nDECISION (T10, alpha 2, outcome Y): UNIT\nreading (T10): PUSHES ACT WHERE BANS WRITE\nN_BOOT = 2000, N_FLIP = 100000: 22/22 deterministic quantities identical to the artifact", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [160] THINKING · 2026-10-26 13:34:34 UTC

```
The final test passed cleanly—30/30 cells ran with no errors, 7 figures generated, and all 22 deterministic headline quantities matched the artifact, so TODO 4 is complete. Moving on to TODO 6 to verify the three required properties.
```

### [161] TOOL CALL — Bash · 2026-10-26 13:34:34 UTC

```
Verify GitHub URL, data file and loading pattern:
URL='https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/fork/run_jSassd-YWLVC/round-7/experiment-36/demo/mini_demo_data.json' && python3 - "$URL" <<'EOF'
import json, sys
url = sys.argv[1]
nb = json.load(open("code_demo.ipynb"))
srcs = ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]
loader = next(s for s in srcs if "GITHUB_DATA_URL =" in s)
print("(1) exact GITHUB_DATA_URL line present:", f'GITHUB_DATA_URL = "{url}"' in loader)
print("(3) loader uses urllib.request.urlopen(GITHUB_DATA_URL):", "urllib.request.urlopen(GITHUB_DATA_URL" in loader,
      "| local fallback only after the URL attempt:", loader.index("urlopen") < loader.index('Path("mini_demo_data.json")'))
print("    'data = load_data()' called:", any("data = load_data()" in s for s in srcs))
print("    bare open('mini_demo_data.json') anywhere:", any("open('mini_demo_data.json')" in s or 'open("mini_demo_data.json")' in s for s in srcs))
d = json.load(open("mini_demo_data.json"))
print("(2) mini_demo_data.json exists and parses:", len(d["datasets"]), "dataset,", len(d["datasets"][0]["examples"]), "examples")
EOF
ls -la mini_demo_data.json code_demo.ipynb
```

### [162] TOOL RESULT — Bash · 2026-10-26 13:34:34 UTC

```
{"stdout": "(1) exact GITHUB_DATA_URL line present: True\n(3) loader uses urllib.request.urlopen(GITHUB_DATA_URL): True | local fallback only after the URL attempt: True\n    'data = load_data()' called: True\n    bare open('mini_demo_data.json') anywhere: False\n(2) mini_demo_data.json exists and parses: 1 dataset, 100 examples\n-rw-rw-rw- 1 aii-agent aii-agent  800063 Oct 26 13:34 code_demo.ipynb\n-rw-rw-rw- 1 aii-agent aii-agent 5792484 Oct 26 13:19 mini_demo_data.json", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [163] THINKING · 2026-10-26 13:35:06 UTC

```
All three TODO 6 checks pass—the GITHUB_DATA_URL line is correct, mini_demo_data.json parses with 1 dataset/100 examples, and loading properly goes through urlopen with local file only as fallback. Before final repo housekeeping, I'll review the edit-check and units tables I modified but haven't inspected yet.
```

### [164] TOOL CALL — Bash · 2026-10-26 13:35:06 UTC

```
Inspect final outputs of edited cells:
python3 - <<'EOF'
import json
nb = json.load(open("code_demo.ipynb"))
for c in nb["cells"]:
    if c["id"] in ("cell-19", "cell-24", "cell-40", "cell-41"):
        txt = "".join("".join(o.get("text", "")) for o in c.get("outputs", []) if o["output_type"] == "stream")
        print(f"===== {c['id']}\n{txt[:2500]}")
EOF
```

### [165] TOOL RESULT — Bash · 2026-10-26 13:35:06 UTC

```
{"stdout": "===== cell-19\n   U_bf recomputed - dumped (max abs) fro_ratio_total U_abs_over_hnorm_max U_bf_over_hnorm_max top_quartile_energy_share_U_abs top_quartile_energy_share_U_bf ratio_of_mean_norms (b12..b23) mean_per_position_ratio (mean)  fro_ratio_total (published)\nW1                          5.436e-05           0.616                 1.05              0.1233                          0.8078                          0.417                     0.66..0.79                         0.9941                        0.616\nW2                          5.531e-05           0.612                1.053              0.1233                          0.8078                         0.4153                     0.66..0.78                         0.9899                        0.612\nW3                          5.531e-05          0.6148               0.9963              0.1233                          0.8078                         0.4161                     0.66..0.78                         0.9929                       0.6148\nW4                          5.531e-05          0.6113               0.8196              0.1233                          0.8078                          0.416                     0.66..0.78                         0.9883                       0.6113\nW5                          5.531e-05          0.6091                1.621              0.1233                          0.8078                         0.4144                     0.66..0.78                          0.987                       0.6091\n\ndose_ratios vs U_abs (T10, W1):\n                 U_abs   U_bf  U_bf*  P_top  P_rest  P_shuf\nmean_cell_ratio    1.0  0.994  1.803  0.278   1.711   1.308\nfro_ratio          1.0  0.616  1.000  1.000   1.000   1.000\nb12_mean_ratio     1.0  0.661  1.540  0.338   1.589   1.000\n\nP_top: top-quartile cells hold 81% of U_abs's energy (rescaled x1.11); P_rest rescaled x2.28\n\n===== cell-24\n                        mean rel. error of (h - h_twin).u vs alpha*n max |hook step orthogonal to u| positions outside S unchanged (bitwise) max |change| at masked-out cells\nTARGET, U_abs, float32                                       1.9e-07                         0.00011                                    True                                0\nmasked, P_top, float32                                         2e-07                         7.7e-05                                    True                                0\nTARGET, U_abs, bfloat16                                      0.00011                            0.52                                    True                                0\nmasked, P_top, bfloat16                                      5.2e-05                            0.57                                    True                                0\n\n===== cell-40\n\n===== cell-41\n                                    n  attempted  CV AUC log norms  published  CV AUC R35 direction  published \nU_abs_alpha2 (D1+D2)          100.000     52.000             0.523      0.523                 0.424       0.398\nU_bf_family_alpha2 (D3+D4+D5) 150.000     23.000             0.688      0.688                 0.701       0.723\n\nphi(D1, D2) on the same CRN stream, different u:  Y 0.16, A 0.20 (joint D1&D2 escapes 15 vs 13.0 expected if independent)\nsame u, alpha 1 -> 2: P(escape at a2 | escape at a1) = 0.33 (6 escapes at a1) vs marginal 0.52", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [166] THINKING · 2026-10-26 13:35:48 UTC

```
All checks pass as expected: fp32/bf16 edit errors match the real run, and the E2 AUC (0.424) is in range. Now I'll create the README, .gitignore, and manifest—no large files found, so the manifest will be empty.
```

### [167] TOOL CALL — Write · 2026-10-26 13:35:48 UTC

````
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/README.md

# Demo: why random nudges stopped changing the algorithm

This folder is a runnable notebook demo of **experiment 36 (iteration 7, step K)**, the plan-noise crosswalk on
**Qwen/Qwen3-8B**. The experiment asks why an internal random push moved Qwen3-8B off its default algorithm for T10
(connected components; the default is union-find) on 25 of 50 programs in iteration 4, but on only 1 of 50 in
iteration 5. It crosses the two candidate causes on shared common-random-number (CRN) slots: the **dose unit**
(`U_abs`, the ban's own displacement norm, vs `U_bf`, a fixed fraction of the residual norm) and the **direction seeds**
(`S4` vs `S5`). The answer is the **unit**.

`code_demo.ipynb` is the artifact's own code, split into cells with explanations between them. `method.py` is only a
dispatcher, so the notebook follows its step table and inlines the code of the CPU steps from `src/`:
`k_cfg.py`, `k_units.py`, `analysis_k.py`, `extensions_k.py`, `geometry_k.py` and `figures_k.py`, plus the edit
functions `make_edits_v4` (vendored exp22 `hooks4.py`) and `make_edits_masked` (`gen_k.py`). It runs them on the real
outcomes of all 100 T10 CRN slots.

**Not re-run here:** the generation steps, which need Qwen3-8B in bf16 on a ≥ 20 GB GPU. The edit arithmetic is
checked on toy tensors instead (GPU unit test U2 in miniature).

## What the notebook reproduces

With the artifact's original resampling sizes (2,000 bootstraps, 100,000 Monte-Carlo sign flips), **22 of 22
deterministic headline quantities are identical to the artifact's `results/*.json`**, including every bootstrap CI.

| quantity (T10) | value |
|---|---|
| anchors | D1 attempted off-default 26/50 (exp29 25/50, per-slot agreement 0.98); D4 correct off-default 1/50 (exp27 1/50) |
| S1 shares Y at α 2, D1 / D2 / D3 / D4 | 0.50 / 0.52 / 0.10 / 0.02 |
| unit effect | +0.45 [0.35, 0.55], Holm p 3e-5 |
| seed effect | +0.03 [−0.07, 0.14] |
| interaction | −0.10 [−0.28, 0.08] |
| decision | **UNIT**; conditional logit β_unit 4.34 |
| D5 split | profile at matched energy +0.22 [0.08, 0.36]; energy at the ban-free shape +0.18 [0.06, 0.30] |
| S2 | P_top 0.58 vs P_rest 0.30 (McNemar 18:4); D1 0.50 vs P_shuf 0.08 (21:0) → "pushes act where bans write" |
| E1 | U_bf (D3) at α 3 / 4 / 6: 9 / 20 / 14 of 50 |
| E3, fresh slots k 10–19 | unit +0.42 [0.32, 0.52] |
| E2 | φ(D1, D2) on one stream 0.16 / 0.20; P(escape at α 2 \| escape at α 1) 0.33 |

The 23rd quantity, the E2 cross-validated AUC from the block-35 displacement *direction*, differs from run to run
**in the original code as well**. `geometry_k.cv_auc` lets sklearn's `PCA` choose its solver, and on the 80 × 4096
training folds it chooses the randomized solver without a seed:
- six repeated runs gave 0.36–0.44 for U_abs at α 2;
- the artifact's 0.40 is one draw;
- the exact solver gives 0.42.

The code is kept unchanged, and every draw supports the same conclusion (near chance).

The notebook also draws the artifact's figures in activation coordinates, for T10:
- **F1**: the 2×2 shares.
- **F2**: the dose units as block × token maps in residual-norm units.
- **F3**: the realised displacement through blocks 12–35.
- **F4**: the outcome vs the block-35 displacement.
- **F5**: a PCA of the actual 4096-d block-35 displacement vectors.
- **E1**: the dose response.
- **E3**: the replication.

## Layout

| path | what |
|---|---|
| `code_demo.ipynb` | the demo notebook, executed (outputs and figures included) |
| `mini_demo_data.json` | demo data (5.8 MB), one dataset of 100 T10 CRN slots; see below |
| `build_mini_demo_data.py` | the script that built `mini_demo_data.json` from the artifact folder |
| `.gitignore` | ignores `results/`, `figures/` and `logs/`, which the notebook writes when it runs |
| `.aii/manifest.yaml` | storage manifest (nothing heavy: no entries) |

### `mini_demo_data.json`

- **`datasets[0].examples`**: 100 examples, one per CRN slot `(template W1–W5, k 0–19)`, in the artifact's
  `exp_gen_sol_out` style:
  - `input`: the twin prompt;
  - `output`: the clean twin's `label|passed`;
  - `predict_<arm>`: each pushed arm's `label|passed`;
  - `metadata_programs`: the 1,250 joined program rows of `data/samples.jsonl` (label, pass flag, validity, Y / Y_any
    / A, seeds, realised-displacement summary, generated code);
  - `metadata_disp_profiles`: the 36-block displacement profiles of the α-2 rows on k 0–9 (`data/realised_disp.jsonl`);
  - `metadata_R35_fp16_b64`: their block-35 read-position displacement vectors, 350 in all (`cache/disp/*.npz`; fp16,
    base64).
- **`metadata`**:
  - the T10 dose-unit maps (`cache/units/T10.npz`);
  - the `r_Q` table (exp23);
  - exp29's engine-d labels (for the anchor);
  - the T10 catalogue and the twin prompts;
  - the published reference numbers (`results/*.json`).

## How to run

- **Colab.** Open `code_demo.ipynb` and run all cells. The first cell installs `loguru`; everything else is
  pre-installed on Colab. The notebook downloads `mini_demo_data.json` from this repository and falls back to a local
  copy next to the notebook.
- **Locally.** Use Python 3.12 and a clean environment. The install cell pins Colab's versions (numpy 2.0.2, scipy
  1.16.3, scikit-learn 1.6.1, statsmodels 0.14.6, pandas 2.2.2, matplotlib 3.10.0, torch 2.9.0 CPU).

```bash
uv venv --seed --python 3.12 .venv
uv pip install --python .venv/bin/python jupyter ipykernel
.venv/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb
```

- **Runtime.** About 40 s on a 2-core CPU, install cell included, measured with the original parameters.
- **Faster pass.** Lower `N_BOOT` / `N_FLIP` in the configuration cell. Only the CI endpoints and Monte-Carlo
  p-values depend on them.

### Changes from the original code

The changes are kept to what the notebook context requires, and each is marked `# demo:` in the code:
- **Data sources.** File reads go to `mini_demo_data.json`: `load_joined` takes the two in-memory halves, and
  `u_abs`, `r_q_table`, `catalogue` and `exp29_labels_d` read from the data. Output paths point to local `results/`,
  `figures/` and `logs/`.
- **T10 only.** `S1_TASKS = ("T10",)`, because the demo data ships T10 only. The T2 decision line in `s1()` returns
  `INCOMPLETE` explicitly, and the figure functions draw only their T10 panels.
- **Cross-module imports.** A `_Module` shim stands in for them, so `K.x`, `KU.x` and `A.x` resolve in the notebook
  namespace.
- **E2.** It runs its slot concordance and its fixed-dose AUCs on the shipped block-35 read-position vectors. The
  generated-position-1 and spec-mean direction AUCs and the escape axis need vectors the demo does not ship.
- **Figures.** `save()` shows each figure inline instead of closing it.
- **Notebook additions.** A check that the recomputed outcomes and direction seeds match the artifact, the toy-tensor
  edit check, and the summary table against the published numbers. A warnings filter silences statsmodels'
  "dropped groups" notice.

**Not re-run here** (see the notebook's last section):
- generation;
- the T2 half of S1/S2;
- D\* and the S3 prices;
- the novelty audit.

## Restoring removed files

Nothing in this folder is marked `delete` in `.aii/manifest.yaml`. Every file is text or code under the 10 MB
floor, and no cache, environment or weights were stored here. The only files left out of the folder are regenerable:

| not shipped | how to regenerate |
|---|---|
| `results/*.json`, `figures/*.pdf/png`, `logs/method.log` | run the notebook; it writes them next to itself |
| `mini_demo_data.json`, if deleted | `python build_mini_demo_data.py <artifact folder>`, where the artifact folder holds the step-K `method.py`, `data/`, `cache/`, `results/`, `inputs/` and `vendor/` (`round-7/experiment-36/` of the published run) |
| the Python environment | the local commands above (`uv venv` and the notebook's install cell) |

To regenerate the programs themselves, download the model and run the full pipeline in the artifact folder (GPU with
at least 20 GB):

```bash
hf download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218
uv run method.py all
```
````

### [168] TOOL RESULT — Write · 2026-10-26 13:35:48 UTC

````
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/README.md", "content": "# Demo: why random nudges stopped changing the algorithm\n\nThis folder is a runnable notebook demo of **experiment 36 (iteration 7, step K)**, the plan-noise crosswalk on\n**Qwen/Qwen3-8B**. The experiment asks why an internal random push moved Qwen3-8B off its default algorithm for T10\n(connected components; the default is union-find) on 25 of 50 programs in iteration 4, but on only 1 of 50 in\niteration 5. It crosses the two candidate causes on shared common-random-number (CRN) slots: the **dose unit**\n(`U_abs`, the ban's own displacement norm, vs `U_bf`, a fixed fraction of the residual norm) and the **direction seeds**\n(`S4` vs `S5`). The answer is the **unit**.\n\n`code_demo.ipynb` is the artifact's own code, split into cells with explanations between them. `method.py` is only a\ndispatcher, so the notebook follows its step table and inlines the code of the CPU steps from `src/`:\n`k_cfg.py`, `k_units.py`, `analysis_k.py`, `extensions_k.py`, `geometry_k.py` and `figures_k.py`, plus the edit\nfunctions `make_edits_v4` (vendored exp22 `hooks4.py`) and `make_edits_masked` (`gen_k.py`). It runs them on the real\noutcomes of all 100 T10 CRN slots.\n\n**Not re-run here:** the generation steps, which need Qwen3-8B in bf16 on a ≥ 20 GB GPU. The edit arithmetic is\nchecked on toy tensors instead (GPU unit test U2 in miniature).\n\n## What the notebook reproduces\n\nWith the artifact's original resampling sizes (2,000 bootstraps, 100,000 Monte-Carlo sign flips), **22 of 22\ndeterministic headline quantities are identical to the artifact's `results/*.json`**, including every bootstrap CI.\n\n| quantity (T10) | value |\n|---|---|\n| anchors | D1 attempted off-default 26/50 (exp29 25/50, per-slot agreement 0.98); D4 correct off-default 1/50 (exp27 1/50) |\n| S1 shares Y at α 2, D1 / D2 / D3 / D4 | 0.50 / 0.52 / 0.10 / 0.02 |\n| unit effect | +0.45 [0.35, 0.55], Holm p 3e-5 |\n| seed effect | +0.03 [−0.07, 0.14] |\n| interaction | −0.10 [−0.28, 0.08] |\n| decision | **UNIT**; conditional logit β_unit 4.34 |\n| D5 split | profile at matched energy +0.22 [0.08, 0.36]; energy at the ban-free shape +0.18 [0.06, 0.30] |\n| S2 | P_top 0.58 vs P_rest 0.30 (McNemar 18:4); D1 0.50 vs P_shuf 0.08 (21:0) → \"pushes act where bans write\" |\n| E1 | U_bf (D3) at α 3 / 4 / 6: 9 / 20 / 14 of 50 |\n| E3, fresh slots k 10–19 | unit +0.42 [0.32, 0.52] |\n| E2 | φ(D1, D2) on one stream 0.16 / 0.20; P(escape at α 2 \\| escape at α 1) 0.33 |\n\nThe 23rd quantity, the E2 cross-validated AUC from the block-35 displacement *direction*, differs from run to run\n**in the original code as well**. `geometry_k.cv_auc` lets sklearn's `PCA` choose its solver, and on the 80 × 4096\ntraining folds it chooses the randomized solver without a seed:\n- six repeated runs gave 0.36–0.44 for U_abs at α 2;\n- the artifact's 0.40 is one draw;\n- the exact solver gives 0.42.\n\nThe code is kept unchanged, and every draw supports the same conclusion (near chance).\n\nThe notebook also draws the artifact's figures in activation coordinates, for T10:\n- **F1**: the 2×2 shares.\n- **F2**: the dose units as block × token maps in residual-norm units.\n- **F3**: the realised displacement through blocks 12–35.\n- **F4**: the outcome vs the block-35 displacement.\n- **F5**: a PCA of the actual 4096-d block-35 displacement vectors.\n- **E1**: the dose response.\n- **E3**: the replication.\n\n## Layout\n\n| path | what |\n|---|---|\n| `code_demo.ipynb` | the demo notebook, executed (outputs and figures included) |\n| `mini_demo_data.json` | demo data (5.8 MB), one dataset of 100 T10 CRN slots; see below |\n| `build_mini_demo_data.py` | the script that built `mini_demo_data.json` from the artifact folder |\n| `.gitignore` | ignores `results/`, `figures/` and `logs/`, which the notebook writes when it runs |\n| `.aii/manifest.yaml` | storage manifest (nothing heavy: no entries) |\n\n### `mini_demo_data.json`\n\n- **`datasets[0].examples`**: 100 examples, one per CRN slot `(template W1–W5, k 0–19)`, in the artifact's\n  `exp_gen_sol_out` style:\n  - `input`: the twin prompt;\n  - `output`: the clean twin's `label|passed`;\n  - `predict_<arm>`: each pushed arm's `label|passed`;\n  - `metadata_programs`: the 1,250 joined program rows of `data/samples.jsonl` (label, pass flag, validity, Y / Y_any\n    / A, seeds, realised-displacement summary, generated code);\n  - `metadata_disp_profiles`: the 36-block displacement profiles of the α-2 rows on k 0–9 (`data/realised_disp.jsonl`);\n  - `metadata_R35_fp16_b64`: their block-35 read-position displacement vectors, 350 in all (`cache/disp/*.npz`; fp16,\n    base64).\n- **`metadata`**:\n  - the T10 dose-unit maps (`cache/units/T10.npz`);\n  - the `r_Q` table (exp23);\n  - exp29's engine-d labels (for the anchor);\n  - the T10 catalogue and the twin prompts;\n  - the published reference numbers (`results/*.json`).\n\n## How to run\n\n- **Colab.** Open `code_demo.ipynb` and run all cells. The first cell installs `loguru`; everything else is\n  pre-installed on Colab. The notebook downloads `mini_demo_data.json` from this repository and falls back to a local\n  copy next to the notebook.\n- **Locally.** Use Python 3.12 and a clean environment. The install cell pins Colab's versions (numpy 2.0.2, scipy\n  1.16.3, scikit-learn 1.6.1, statsmodels 0.14.6, pandas 2.2.2, matplotlib 3.10.0, torch 2.9.0 CPU).\n\n```bash\nuv venv --seed --python 3.12 .venv\nuv pip install --python .venv/bin/python jupyter ipykernel\n.venv/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb\n```\n\n- **Runtime.** About 40 s on a 2-core CPU, install cell included, measured with the original parameters.\n- **Faster pass.** Lower `N_BOOT` / `N_FLIP` in the configuration cell. Only the CI endpoints and Monte-Carlo\n  p-values depend on them.\n\n### Changes from the original code\n\nThe changes are kept to what the notebook context requires, and each is marked `# demo:` in the code:\n- **Data sources.** File reads go to `mini_demo_data.json`: `load_joined` takes the two in-memory halves, and\n  `u_abs`, `r_q_table`, `catalogue` and `exp29_labels_d` read from the data. Output paths point to local `results/`,\n  `figures/` and `logs/`.\n- **T10 only.** `S1_TASKS = (\"T10\",)`, because the demo data ships T10 only. The T2 decision line in `s1()` returns\n  `INCOMPLETE` explicitly, and the figure functions draw only their T10 panels.\n- **Cross-module imports.** A `_Module` shim stands in for them, so `K.x`, `KU.x` and `A.x` resolve in the notebook\n  namespace.\n- **E2.** It runs its slot concordance and its fixed-dose AUCs on the shipped block-35 read-position vectors. The\n  generated-position-1 and spec-mean direction AUCs and the escape axis need vectors the demo does not ship.\n- **Figures.** `save()` shows each figure inline instead of closing it.\n- **Notebook additions.** A check that the recomputed outcomes and direction seeds match the artifact, the toy-tensor\n  edit check, and the summary table against the published numbers. A warnings filter silences statsmodels'\n  \"dropped groups\" notice.\n\n**Not re-run here** (see the notebook's last section):\n- generation;\n- the T2 half of S1/S2;\n- D\\* and the S3 prices;\n- the novelty audit.\n\n## Restoring removed files\n\nNothing in this folder is marked `delete` in `.aii/manifest.yaml`. Every file is text or code under the 10 MB\nfloor, and no cache, environment or weights were stored here. The only files left out of the folder are regenerable:\n\n| not shipped | how to regenerate |\n|---|---|\n| `results/*.json`, `figures/*.pdf/png`, `logs/method.log` | run the notebook; it writes them next to itself |\n| `mini_demo_data.json`, if deleted | `python build_mini_demo_data.py <artifact folder>`, where the artifact folder holds the step-K `method.py`, `data/`, `cache/`, `results/`, `inputs/` and `vendor/` (`round-7/experiment-36/` of the published run) |\n| the Python environment | the local commands above (`uv venv` and the notebook's install cell) |\n\nTo regenerate the programs themselves, download the model and run the full pipeline in the artifact folder (GPU with\nat least 20 GB):\n\n```bash\nhf download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218\nuv run method.py all\n```\n", "structuredPatch": [], "originalFile": null, "userModified": false}
````

### [169] TOOL CALL — Write · 2026-10-26 13:35:48 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/.gitignore

# written by code_demo.ipynb when it runs
results/
figures/
logs/
.venv/
.ipynb_checkpoints/
```

### [170] TOOL RESULT — Write · 2026-10-26 13:35:48 UTC

```
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/.gitignore", "content": "# written by code_demo.ipynb when it runs\nresults/\nfigures/\nlogs/\n.venv/\n.ipynb_checkpoints/\n", "structuredPatch": [], "originalFile": null, "userModified": false}
```

### [171] TOOL CALL — Write · 2026-10-26 13:35:48 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/.aii/manifest.yaml

# Storage manifest of the step-K demo folder.
# Nothing here needs a keep/delete decision: every file is text or code under the 10 MB floor
# (code_demo.ipynb 0.8 MB, mini_demo_data.json 5.8 MB, build_mini_demo_data.py, README.md, .gitignore);
# no environment, cache, checkpoint or model weights were written into this folder (the notebook test venv lives
# outside it). See README.md "Restoring removed files".
entries: []
```

### [172] TOOL RESULT — Write · 2026-10-26 13:35:48 UTC

```
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/.aii/manifest.yaml", "content": "# Storage manifest of the step-K demo folder.\n# Nothing here needs a keep/delete decision: every file is text or code under the 10 MB floor\n# (code_demo.ipynb 0.8 MB, mini_demo_data.json 5.8 MB, build_mini_demo_data.py, README.md, .gitignore);\n# no environment, cache, checkpoint or model weights were written into this folder (the notebook test venv lives\n# outside it). See README.md \"Restoring removed files\".\nentries: []\n", "structuredPatch": [], "originalFile": null, "userModified": false}
```

### [173] THINKING · 2026-10-26 13:36:00 UTC

```
README, .gitignore, and manifest are done. Now I'll clean up temporary dev tools and test output folders, fix the builder's usage line, then verify the manifest parses and no published file leaks a server path.
```

### [174] TOOL CALL — Bash · 2026-10-26 13:36:00 UTC

```
Clean up dev files and verify deliverables:
sed -i 's|^usage: python build_mini_demo_data.py <path to gen_art_experiment_36> \[out.json\]$|usage: python build_mini_demo_data.py <artifact folder: the step-K folder with method.py, data/, cache/, results/> [out.json]|' build_mini_demo_data.py && grep -n "^usage" build_mini_demo_data.py && rm -rf .dev figures results logs && python3 -c "
import yaml; print('manifest:', yaml.safe_load(open('.aii/manifest.yaml')))" 2>/dev/null || python3 -c "print(open('.aii/manifest.yaml').read())"; for f in README.md build_mini_demo_data.py code_demo.ipynb .gitignore .aii/manifest.yaml; do printf "%-26s server-path hits: %s\n" "$f" "$(grep -c -E '/ai-inventor/|/tmp/|/var/lib|run_0oWBKrKEGsmU' $f)"; done; python3 -m py_compile build_mini_demo_data.py && echo "builder compiles"; ls -la; du -sh .
```

### [175] TOOL RESULT — Bash · 2026-10-26 13:36:00 UTC

```
{"stdout": "14:usage: python build_mini_demo_data.py <artifact folder: the step-K folder with method.py, data/, cache/, results/> [out.json]\nmanifest: {'entries': []}\nREADME.md                  server-path hits: 0\nbuild_mini_demo_data.py    server-path hits: 0\ncode_demo.ipynb            server-path hits: 0\n.gitignore                 server-path hits: 0\n.aii/manifest.yaml         server-path hits: 0\nbuilder compiles\ntotal 12993\ndrwxrwxrwx  4 aii-agent aii-agent 2000788 Oct 26 13:35 .\ndrwxrwxrwx  9 aii-agent aii-agent 2002486 Oct 26 13:05 ..\ndrwxrwxrwx  2 aii-agent aii-agent   42500 Oct 26 13:35 .aii\n-rw-rw-rw-  1 aii-agent aii-agent      54 Oct 26 12:59 .aii_claude_session.json\n-rw-rw-rw-  1 aii-agent aii-agent      93 Oct 26 13:35 .gitignore\n-rw-rw-rw-  1 aii-agent aii-agent 1646826 Oct 26 13:35 .repl_agent.ptylog\n-rw-rw-rw-  1 aii-agent aii-agent    8209 Oct 26 13:35 README.md\ndrwxrwxrwx  2 aii-agent aii-agent 1001411 Oct 26 13:35 __pycache__\n-rw-rw-rw-+ 1 aii-agent aii-agent    9995 Oct 26 13:35 build_mini_demo_data.py\n-rw-rw-rw-  1 aii-agent aii-agent  800063 Oct 26 13:34 code_demo.ipynb\n-rw-rw-rw-  1 aii-agent aii-agent 5792484 Oct 26 13:19 mini_demo_data.json\n11M\t.", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [176] ASSISTANT · 2026-10-26 13:36:10 UTC

```
The `py_compile` check left a `__pycache__/` behind. I'll remove it and add it to `.gitignore`. I'll also confirm that the shipped builder reproduces the shipped data byte for byte.
```

### [177] TOOL CALL — Bash · 2026-10-26 13:36:10 UTC

```
Verify builder reproduces data, remove pycache:
rm -rf __pycache__ && printf '__pycache__/\n' >> .gitignore && python3 -B build_mini_demo_data.py /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36 rebuild_check.json && cmp rebuild_check.json mini_demo_data.json && echo "IDENTICAL: shipped builder reproduces mini_demo_data.json byte for byte"; sha256sum rebuild_check.json mini_demo_data.json | cut -c1-20; rm -f rebuild_check.json; ls -A; cat .gitignore
```

### [178] TOOL RESULT — Bash · 2026-10-26 13:36:12 UTC

```
{"stdout": "wrote rebuild_check.json (5.79 MB): 100 slots, 1250 programs, 350 block-35 vectors, 400 profiles\nIDENTICAL: shipped builder reproduces mini_demo_data.json byte for byte\n84ebc47f57a0ca946ffd\n84ebc47f57a0ca946ffd\n.aii\n.aii_claude_session.json\n.gitignore\n.repl_agent.ptylog\nREADME.md\nbuild_mini_demo_data.py\ncode_demo.ipynb\nmini_demo_data.json\n# written by code_demo.ipynb when it runs\nresults/\nfigures/\nlogs/\n.venv/\n.ipynb_checkpoints/\n__pycache__/", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [179] ASSISTANT · 2026-10-26 13:36:18 UTC

```
The builder reproduces `mini_demo_data.json` byte for byte (identical sha256), and the folder now holds only the deliverables. Last step: the structured output file the task requires.
```

### [180] TOOL CALL — Write · 2026-10-26 13:36:18 UTC

```
File: /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/.terminal_claude_agent_struct_out.json

{
  "out_expected_files": {
    "notebook": "code_demo.ipynb",
    "mini_data_file": "mini_demo_data.json"
  }
}
```

### [181] TOOL RESULT — Write · 2026-10-26 13:36:18 UTC

```
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_7/art_8O5eaNc5gxJs/.terminal_claude_agent_struct_out.json", "content": "{\n  \"out_expected_files\": {\n    \"notebook\": \"code_demo.ipynb\",\n    \"mini_data_file\": \"mini_demo_data.json\"\n  }\n}\n", "structuredPatch": [], "originalFile": null, "userModified": false}
```

### [182] TOOL CALL — Bash · 2026-10-26 13:36:22 UTC

```
Validate the structured output file:
python3 -c "
import json
d = json.load(open('.terminal_claude_agent_struct_out.json'))
assert set(d) == {'out_expected_files'} and set(d['out_expected_files']) == {'notebook', 'mini_data_file'}
from pathlib import Path
for k, v in d['out_expected_files'].items():
    print(k, v, Path(v).exists(), Path(v).stat().st_size)
print('struct output valid')"
```

### [183] TOOL RESULT — Bash · 2026-10-26 13:36:22 UTC

```
{"stdout": "notebook code_demo.ipynb True 800063\nmini_data_file mini_demo_data.json True 5792484\nstruct output valid", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [184] ASSISTANT · 2026-10-26 13:36:37 UTC

```
I built and tested the demo notebook and its data file. With the artifact's original settings, the notebook runs end to end in 41 s and reproduces all 22 deterministic headline numbers in the artifact's `results/*.json` exactly, including every bootstrap confidence interval.

**How I handled `method.py`:** it only dispatches 19 steps, each a script in `src/`. The notebook keeps its step table as is and puts the code of the steps that can run on CPU into cells with explanations between them. My changes are limited to where data is read from and restricting to T10; each one is marked `# demo:`. The generation steps need Qwen3-8B on a GPU with at least 20 GB, so they are not re-run. Instead, the original edit functions are checked on toy tensors with the real T10 dose map: in bf16 the error is 1.1e-4, about the same size as the real run's ~1e-4.

**Data (`mini_demo_data.json`, 5.8 MB):** one dataset of 100 examples, one per T10 slot (5 prompt templates × 20 samples). It holds the 1,250 generated programs with their code and labels, the dose maps, and 350 internal displacement vectors used for the PCA plot. The included `build_mini_demo_data.py` rebuilds it byte for byte from the artifact folder.

**Scaling (TODO 5):** I ran three rounds of bootstrap / sign-flip sizes: 20 / 1,000 took 38 s, 200 / 10,000 took 40 s, and the original 2,000 / 100,000 took 40 s. The original values stay, well under the 600 s budget.

**Results reproduced, all identical to the artifact:**
- **Anchors:** D1 26/50 (iteration 4's 25/50), D4 1/50 (iteration 5's 1/50).
- **Main result, UNIT:** unit effect +0.45 [0.35, 0.55], seed effect +0.03 [−0.07, 0.14].
- **D5 split** and the **S2 profile tests** (top quartile 18:4, position-shuffled 21:0).
- **E1, E2 and E3** headline numbers.
- **Seven figures**, including the PCA of the actual block-35 displacement vectors.

**Things you should know:**
- **One E2 number isn't reproducible, even in the original code.** The AUC from the displacement direction lets sklearn pick its PCA solver, and it picks a randomized one with no fixed seed. Six repeated runs gave 0.36–0.44; the artifact's 0.398 is one draw. I left the code unchanged and documented this in the notebook and README. The conclusion (near chance) holds for every draw.
- **I couldn't use NotebookEdit.** It needs a prior Read, and the Read tool refuses notebooks over 25k tokens; this one is about 52k without outputs. I built the notebook with a temporary generator script and made the config changes with a small JSON edit, then deleted both.
- **No todo-tracking tool existed in this session,** so I tracked the six TODOs inline. All six are done.
- **The GitHub data URL currently returns 404** because nothing is pushed yet, so the test runs used the local fallback, as intended. TODO 6 checks pass: the exact URL line, the URL-first loader, and no bare `open()` of the data file.

The README lists exactly what changed from the original code and what is not re-run. `.aii/manifest.yaml` has no entries because nothing in the folder is heavy, and `.terminal_claude_agent_struct_out.json` is written.

Files are in the workspace folder:
- `code_demo.ipynb`
- `mini_demo_data.json`
- `build_mini_demo_data.py`
- `README.md`
```
