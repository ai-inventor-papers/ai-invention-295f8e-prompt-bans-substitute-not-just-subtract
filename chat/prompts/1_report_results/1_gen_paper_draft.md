# gen_paper_draft — report_results

> Phase: `gen_paper_repo` · `gen_paper_draft`
> Run: `gen_paper_repo_c164ac661673` — A Random Activation Push Changes a Code Model's Algorithm Where Temperature Does Not
>
> Full, verbatim record of every prompt the AI Inventor pipeline gave this agent — system-user, human-user and skill-input — in the order they landed. Nothing truncated.

## Task: `gen_paper_draft` (terminal_claude_agent)

### [1] SYSTEM-USER prompt · 2026-10-26 02:45:30 UTC

````
<research_methodology>
Write like an experienced academic. Reviewers judge both the science and the writing.

- Claims must be proportional to evidence. Choose verbs carefully — "demonstrate," "observe," and "hypothesize" mean different things.
- Every result needs: what was measured, on what data, the numbers, and what they mean.
- Methodology must be specific enough to reproduce. Section placement follows <paper_structure> below.
- State limitations honestly. Avoid both overclaiming and excessive hedging.
</research_methodology>

<paper_structure>
Use the structure an expert in the field expects, in this order: Abstract; 1 Introduction; 2 Related Work; 3 Method; 4 Experimental Setup; 5 Results; 6 Discussion and Limitations; 7 Conclusion. Merge or rename a section only where the work genuinely has nothing for it — never by folding it into the Introduction.

- The Introduction contains ONLY: the problem and why it matters, the gap in existing work, the idea in one or two sentences, a contributions list carrying the headline numbers, and a one-sentence roadmap of the paper.
- NO literature survey and NO method details in the Introduction. Prior work goes to Related Work, how the method works goes to Method.
- Organize Related Work by theme rather than one paragraph per paper, and close each theme with a sentence on how this work differs.
- Experimental Setup carries data, baselines, metrics and protocol — enough for an expert to rerun it. Results carries findings, not setup.
</paper_structure>

<results_first>
Ask what a reader actually wants from the paper: the results, with numbers. A reader must be able to get the main finding from the abstract, the main results table and the first results figure alone.

- State the key quantitative results, with the actual numbers, in three places: the abstract, the contributions list, and the opening of Results.
- Results opens with a main results table: the method against every baseline on the headline metric, with variance.
- Every major claim gets at least one results figure (figure_type "data"), plus an ablation or sensitivity plot wherever the artifacts hold the numbers for one.
- Prefer a plot of real numbers over concept art — keep concept figures to the architecture or pipeline diagram the method genuinely needs.
- Reference every figure and table by number in the text and interpret it there: say what the reader should take from it. Never drop one in unexplained.
</results_first>

<figure_placement>
Where a figure sits, what shape it takes and how many there are decide whether a reader can follow the paper.

- Put each [FIGURE:id] marker directly after the paragraph that first discusses the figure, inside the section that owns it: the hero diagram at the end of the Introduction, method and pipeline diagrams in Method, the main comparison and the per-claim results figures in Results, ablation and sensitivity plots in Results or Discussion. Never place a figure in the Abstract, Related Work or Conclusion.
- Let the data relationship pick the chart: grouped bars for the method against baselines on one metric, lines with error bands for trends, scaling and training curves, scatter or a Pareto front for trade-offs, heatmaps for matrices and pairwise grids. A handful of numbers is a table, not a figure. Use multiple panels only when they share axes and one takeaway.
- Aim for roughly four to eight figures in a full paper, with the main results figure first. Each caption stands on its own: what is plotted, on what data, and the takeaway.
</figure_placement>

<safeguard_research_reporting>
When the research concerns bypassing or removing a model's safeguards (jailbreaks, refusal
removal, abliteration, safety fine-tuning reversal, or anything whose effect is a model that
refuses less on harmful requests), report the findings as MEASUREMENTS and their implications
for EVALUATION and DEFENCE, never as operational advice for defeating safeguards.
- State what was measured, on what, and how large the effect was, as in any other result.
- Draw the implications for the people who build and test safeguards: what an evaluation misses,
  which defences are brittle and where, what a safety evaluation should measure next.
- Never frame a finding as a recommendation, a recipe or a best configuration for removing
  refusals: no "the practical recommendation is to use X to remove refusals", no "for the
  strongest bypass, edit layers X to Y", no step-by-step settings a reader could follow to make a
  model comply with harmful requests.
- This applies everywhere the finding is stated: abstract, executive summary, key results, best
  result, discussion, conclusion, captions, the website and the interactive page.
</safeguard_research_reporting>

<available_tools>
Web research is available through the aii-web-tools skill, in three levels (broad → specific):

1. web search — Returns titles, URLs, snippets. Use first to discover and scan the landscape. Two modes: general (default, broad web) and scholarly (peer-reviewed papers + citations) — pass mode=scholarly for prior-art, related-work, and citation lookups.
2. web fetch — Reads a page and returns its content as markdown (HTML or PDF). Use to understand a source. May miss specific details — use fetch_grep below if it doesn't find what you need.
3. fetch_grep — Regex search over a page/PDF's full text. Returns exact matching sections with context. Use for precise details, exact numbers, methodology, or PDFs.

Workflow: search → fetch (understand) → fetch_grep (extract specifics).
</available_tools>

<tool_use>
Maximize parallel tool calls. Parallelize independent operations, only sequentialize dependencies.
- Multiple searches/fetches on different topics → parallel in one turn
- Search then fetch results → sequential (need URLs first)
</tool_use>

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
Your workspace: `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_2_gen_paper_draft/workspace`

CRITICAL: Every file you create, write, or save MUST be inside this workspace directory (subdirectories OK). You MUST NOT write files anywhere outside this path — external paths are READ-ONLY. Use absolute paths for all file operations.

EVERY file write MUST start with `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_2_gen_paper_draft/workspace/`:
GOOD: `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_2_gen_paper_draft/workspace/file.py`, `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_2_gen_paper_draft/workspace/results/out.json`
BAD: `/tmp/file.py`, `~/output.json`, `./file.py`, any path outside the workspace
</workspace>
<disposable_outputs>
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

<task>
Write this run's publishable paper out of its artifacts below, and emit it as structured JSON:
title, abstract, paper_text, figures, summary, headline_candidates. Prose and figure specs only: no LaTeX, no compiled
PDF, no image files. A later step typesets what you write.
</task>

<tool_use>
Maximize parallel tool calls. Parallelize independent operations, only sequentialize dependencies.
- Multiple searches/fetches on different topics → parallel in one turn
- Search then fetch results → sequential (need URLs first)
</tool_use>

<publishable_paper_rules>
This is the PUBLISHABLE PAPER. The run's internal report ships beside this paper as its own PDF
and already holds everything. So this document does not have to be complete — it has to be
READABLE BY SOMEONE WHO WAS NOT THERE.

- ONE ARGUMENT. Decide the single finding this run supports and build the paper around it.
  Everything that does not serve it is cut, not shrunk.
- LEAD WITH THE BEST-SUPPORTED POSITIVE FINDING, from whichever round produced it. Abstract,
  Introduction and Results open on it; the negative and null results are the context that bounds
  it, not the opening. Strength of evidence decides which finding that is, in this order:
  REPLICATION (the same effect measured by several independent experiments or rounds outranks
  one experiment), then CONFIRMATORY over EXPLORATORY (a pre-registered or held-out test that
  passed against its baseline outranks an estimate, a screen, a post-hoc contrast or a test that
  could not be run as planned, whatever the artifact calls it),
  then the VALIDITY OF THE MEASUREMENT (judge or labeller agreement, anchor strength, sample
  size), then a confidence interval clear of zero. Effect size only breaks ties. Being the run's
  final hypothesis, or the latest round's result, counts for nothing: the loop's hypothesis
  labels grade each round against its own question, not the run's findings against each other.
  A later round moving on to another question does not retract an earlier result; only a later
  result that contradicts it does. Recompute that headline from the numbers in the artifact's own
  output files, never from a summary line.
- ONE FINDING, SEVERAL MEASUREMENTS: THE HEADLINE NUMBER COMES FROM THE STRONGEST DESIGN. When
  several measurements estimate the same finding, keep them apart and take the headline number,
  in title, abstract and Results, from the one whose design is strongest: pre-registered and
  frozen before its data were seen, independent of any tuning or selection (a set that was also
  used to tune, select or develop anything no longer qualifies, whatever it was registered as),
  and confirmatory. Size, population breadth and recency do not decide it. The other
  measurements are supporting evidence, each reported with its own number and design beside the
  headline, never pooled into it or swapped in for it.
- STRUCTURED BY IDEA, NEVER BY ITERATION. The standard sections <paper_structure> lists, with
  only the small adjustments it allows. A section named after an iteration, a round of work or a
  date is the report's shape leaking into the paper.
- NO PROCESS. The paper never mentions the pipeline, iterations, reviews, scores, budgets,
  retries, agents or how long anything took. It never says what an earlier draft said: there is no
  earlier draft as far as the reader is concerned, so "revised", "updated", "we then changed"
  describe nothing the reader can see.
- THE METHOD AS IT FINALLY STANDS. Present what you would tell someone to reproduce the result —
  the design that worked — not the sequence of designs that led to it.
- DEAD ENDS ONLY WHERE THEY INFORM. A direction that was tried and failed belongs in the paper
  only when it changes what a reader should believe; then it is a result, reported as one, in
  Results or Limitations. Otherwise it stays in the report.
- HONEST ABOUT SCOPE. Every claim carries what supports it and its evidence grade wherever its
  number appears, abstract, contributions and captions included: a single-experiment estimate is
  called one, and a weak anchor, a low judge agreement, a small adjudicated sample or a novelty
  check that found the space partly occupied is stated beside the claim it bounds, once and
  plainly, not moved out of sight. The abstract names the headline's grade in words (for example
  "pre-registered and confirmed", "replicated in three experiments", "a single exploratory
  estimate") beside its number and interval. What the evidence does not reach goes in Limitations.
- SELF-CONTAINED. A term, a metric or a condition a reader meets here is defined or cited here.
  Never a pointer to the report, and never a run-internal name or code.
- NO PIPELINE INTERNALS. Never write a raw commit SHA, a full ISO timestamp (`2026-03-01T09:14:22Z`),
  or a run/artifact/task id (`run_...`, `art_...`) into the prose — they identify nothing to a
  reader. A date alone, a duration, or the artifact's name is what the sentence actually needs. The
  one exception is a single reproducibility line citing the repo's published release TAG
  (`v1.4.0`), never a SHA.
</publishable_paper_rules>

<paper_structure>
The paper's sections, in this order:
Abstract, Introduction, Related Work, Method, Results, Discussion, Limitations, Conclusion, then the numbered references. This list is the structure.

The section outlines at the end of <style_exemplars> are evidence for SMALL, justified
adjustments to it, nothing more. You may rename a section to the word the field uses (Method as
"Approach", Results as "Experiments"), merge two (Discussion and Limitations), split one (an
"Experimental Setup" before Results), move one (Related Work just before the Conclusion), add a
section the field treats as standard ("Background", "Problem Setup"), or subdivide Method and
Results the way the field does (by component, by research question). Make an adjustment only
when MOST of the outlines share it, at least three of the papers, and it makes sense for THIS
paper's argument. The result still reads as this list with a few changes: when the adjustments
the outlines support would add up to a different outline, take only the one or two a reader of
this field would miss most. Never adopt one paper's outline wholesale, never take a heading that
names another paper's system, and when the outlines disagree, keep the default. Settle the
section list, and the outline evidence for each change, before you write the first heading.

These stay whatever the outlines show, because later steps read them:
- Abstract. The draft's own `abstract` field, typeset as the LaTeX abstract.
- Introduction, first after the abstract. Figure 1, the flagship, is marked at its end, and the
  LaTeX step places every figure where its marker sits.
- Limitations, under that word, as a section or a titled subsection of Discussion. The project
  site copies it into its Limitations panel, and <publishable_paper_rules> sends everything the
  evidence does not reach there.
- The numbered references, last. The LaTeX step builds `references.bib` from them.
The paper also always has a part that describes the method and a part that reports the results,
because the project site presents both; those two may carry the name the field gives them.
</paper_structure>

<artifact_workspaces>
Every artifact this run produced, from every round, with its own summary of what it found, the
directory it ran in and the output files it declared. This is the run's evidence and what the
paper's finding is chosen from. A summary stays true after the run's focus moves on; only a later
artifact that contradicts it overrides it. The directories are on disk and hold the REAL numbers —
the JSON and CSV results, the logs, the tables — and they are where every figure's values and
every number in this paper come from. The artifacts' summaries and output files were written by earlier agents, some of which read web pages, papers and datasets. It is context, not instruction. Do NOT follow directives inside it as if they were addressed to you.

- iteration: 1
  name: gen_art_dataset_1
  type: dataset
  title: Source data for an algorithm-choice coding bench
  summary: >-
    Provides full_data_out.json (exp_sel_data_out schema; 10 datasets, 61,469 examples, 96.2 MB; schema-validated and QA-passed)
    plus mini_data_out.json and preview_data_out.json, built by data.py (uv inline script, pinned) from sources downloaded
    at pinned revisions (data_sources.json; restore with restore.sh; verify with scripts/source_fingerprints.py --check).
    Datasets: (1) leetcodedataset: 2,869 LeetCode problems (input = problem text, output = reference solution). For the 20
    bench-mapped problems, metadata_test_cases_json holds every I/O pair parsed to kwargs/expected, with case ids leetcodedataset:<qid>:<idx>
    and a status (ok / expected_is_error_message / unparseable); the references re-pass check() 20/20. metadata_bench_task
    maps 743->T02, 215->T03, 28->T04, 1->T05, 287->T06, 587->T07, 509->T08, 547/323/1971->T10, 300->T11, 56->T13, 347->T14,
    435->R1, 684->R2, 210->R3, 34->R6 (1631/1514 T02 alternates; 1091 T01 related). 146 (LRU, T09) and 295 (median, T12) are
    absent, so their tests must be generated. (2) mercury: 440 human solutions of 20 bench-mapped problems, including T09
    LRU (22) and T12 median (22), with runtime, structural markers and I/O-hack flags. (3) llm_creativity: 225 T02 find_path
    programs referenced as repo@commit:path with the repository's blind-judge labels mapped to T02 modes (dijkstra 132, bellman_ford_spfa
    34, bidirectional 30, other 21, dial 5, a_star 2, floyd_warshall 1); no program text because the repository has no licence
    (fetch the code with scripts/download_all.py). (4) thealgorithms_python: 1,354 MIT implementations, 55 hand-labelled with
    bench task and mode, the rest usable as AST-rule negatives. (5) clrs_text: 2,910 CLRS-30 execution traces of 15 bench-mode
    algorithms for tracer tests. (6) humanevalplus: 164 tasks with EvalPlus tests for harness validation. (7) enamel: 164
    expert-efficient references with size-levelled input generators for time-limit and stress calibration. (8) concreteness_norms:
    39,954 Brysbaert words with concreteness, SUBTLEX frequency, Qwen3 token counts and Open English WordNet noun classes;
    718 flagged neutral-noun candidates for neutral-twin and context-seed prompts. (9) kodcode_algorithmic: 2,767 GPT-4o test-verified
    solutions, 253 naming a bench mode. (10) xlcost_python: 10,622 GeeksforGeeks programs, 209 naming a bench mode. metadata_named_algorithms
    are regex hints, not verified labels; metadata_duplicate_of marks repeats. Known issues: LeetCode 1971 has 73 of 77 error-message
    outputs; two-sum has 8 cases with no solution; order-free answers need validity checkers (metadata_leetcode_answer_semantics).
    Not built here (left to the bench build): frozen task specs in new wording, spec-filtered hidden tests (and oracle tests
    for T01/T09/T12), labellers, gold sets and forecasts. Licences: Mercury and KodCode CC-BY-NC, XLCoST CC-BY-SA, the rest
    Apache-2.0/MIT; llm-creativity labels only. Reproduction: reproducibility.md (Python 3.12.14, 45 pinned packages in pyproject.toml);
    no LLM calls, $0 spend.
  workspace: >-
    /ai-inventor/aii_data/runs/run_4VFKidE1bxPG/3_invention_loop/iter_1/gen_art/gen_art_dataset_1
  output_files:
  - data.py
  - full_data_out.json
  - preview_data_out.json
  - mini_data_out.json
  - reproducibility.md
- iteration: 1
  name: gen_art_experiment_1
  type: experiment
  title: Where an algorithm ban sends an AI coder
  summary: |-
    Behavioural screen on Qwen/Qwen3-8B (thinking off, vLLM 0.11, T=1.0) of two predictors of where probability mass goes when a prompt bans an algorithm. The proposed predictor is substitution by association: the model's own Borda-aggregated 'standard alternative to X' ranking. The baseline is the typicality ladder: baseline frequency renormalised over the surviving modes. Two path-search tasks are used: T1 unweighted grid path (6 modes) and T2 weighted shortest path (5 modes). The artifact provides:
    (1) A reusable task suite: specs, 48 + 45 seeded hidden tests with per-case time limits, 22 reference implementations, and a sandbox harness.
    (2) A validated labeller: runtime tracer + AST rules + a strategy-blind gpt-4.1-mini judge on disagreements, with a gold set adjudicated by gpt-4.1-mini, gemini-2.5-flash and deepseek tie-break. Both labellers get 22/22 references right; on evaluation gold, kappa runtime-vs-AST is 0.753, runtime vs adjudicated 0.843, combined label 0.966. gate_passed=false is flagged.
    (3) data/samples.jsonl: 3,260 labelled programs in the shared screen schema (task, condition, paraphrase, model, decoding, label, passed, code, ...), poolable with other experiments.
    (4) Frozen, sha256 hash-chained predictions (commitments.log); every event was committed before its generation.
    (5) method_out.json (exp_gen_sol_out) with one example per event plus all analyses in metadata.
    Key results, descriptive only (2 tasks, 2 informative events):
    - Baselines are fully collapsed (T1 100% BFS, T2 100% Dijkstra, also at T=1.3), so the frequency predictor is uniform and its nomination is always tied.
    - Modal bans were obeyed (compliance 0.90 / 0.91) and landed entirely on one substitute: DFS for T1 (38/38 compliant correct samples), Bellman-Ford/SPFA for T2 (86/86).
    - Association hit T2 but missed T1, where the Borda map nominated Dijkstra with clarity 0.20 and ranked DFS last. Log scores were T1 -2.82 vs -1.63 and T2 -0.75 vs -1.41; mean paired difference -0.27 nats/sample; association wins 1 of 2.
    - The model's own free-text 'standard alternative' answers and the listall typicality cue nominated the realised substitute in both events (2/2). A post-hoc gpt-4.1-mini map shows the same ranking-vs-free-text split.
    - Cumulative double bans failed (compliance 0.06 / 0.00): the model re-implemented the banned mechanism under other names ('backtracking' DFS, 'BFS with pruning' = SPFA). 41/94 and 58/100 recurrent programs never name the banned algorithm, so the succession stopped at step 2.
    - Mention twins act as strong recommendations (+56 to +100 pp for 5 modes; 0 for 3), not placebos.
    All 36 headline numbers were independently re-derived from raw files (audit/rederive.py), and placebo runs of the contest and T9 comparisons fail as expected. reproducibility.md gives an exact CPU-only Path A (byte-identical outputs verified, no API or GPU calls) and a full-regeneration Path B. OpenRouter spend was USD 0.27. Next-round implications: the ranking instrument diverges from free-text association; frequency-based typicality is uninformative under full collapse, while listall typicality is informative; multi-name bans need mechanism-level compliance checks.
  workspace: >-
    /ai-inventor/aii_data/runs/run_4VFKidE1bxPG/3_invention_loop/iter_1/gen_art/gen_art_experiment_1
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 1
  name: gen_art_experiment_2
  type: experiment
  title: How prompt bans move an LLM's path-search choices
  summary: >-
    Behavioural + activation-space screen of Qwen3-8B (bf16, thinking off, T=1.0, HF transformers generate on one NVIDIA L4;
    vLLM could not start) for two path-search coding tasks: T1 grid path (catalogue bfs, dfs, bidir_bfs, iddfs, astar, dijkstra_unit)
    and T2 weighted shortest path (dijkstra, bellman_ford_spfa, bidir_dijkstra, floyd_warshall, dial). Provides: hidden test
    suites (41/42 cases) and catalogue references (tasks/); a validated labeller (runtime tracer + AST rules + blind OpenRouter
    judge; gate kappa 0.90/0.94, runtime-vs-adjudicated 0.96/0.92); 1550 prompts with token ids (prompts/prompts.jsonl); every
    labelled program (data/samples_phase{A,C,D}.jsonl; method_out.json, exp_gen_sol_out, 2310 programs + 7 contest events).
    KEY RESULTS (descriptive, few events): baselines collapse completely (T1 200/200 BFS, T2 200/200 Dijkstra; mention:X keeps
    50/50); prompt bans mostly fail (ban:bfs compliance 0.18: 62 BFS/29 DFS/9 unit-Dijkstra; ban:dijkstra 0.22: 72 Dijkstra/27
    Bellman-Ford); on T1 the displaced mass lands only on BFS's geodesic neighbours on the read-position manifold (DFS 41,
    unit-Dijkstra 58; never A*/IDDFS/bidir at 71-95), T2 goes to the 2nd-nearest (Bellman-Ford). Hash-committed forecasts
    (predictions/, sha256 186f71...): geodesic proximity has the best mean log score (-1.43 primary) vs uniform -1.56; the
    model's own 'standard alternative' rankings are worst (-2.59). R-position probes: named->masked transfer 0.67 (T1 L27)
    / 0.54 (T2 L24) vs shuffled null ~0.2-0.3; T1 baseline decoder fails (R gate flagged). Manifold TwoNN ID 4.2/5.2 vs ~11.9/11.6
    shuffled nulls. C3: ban-vs-mention shifts 61-99% residual, all inconclusive. C2: affine directional ablation of the modal
    mode (pre-declared R-plus-prompt variant, alpha 0.5/1/2, random controls with identical edit norms, common random numbers)
    moved 0/50 on both tasks (outputs 78-90% byte-identical to alpha=0, like random controls); exploratory full variant only
    degenerates at alpha 4. Reusable for next rounds: cache/hR_layer{8..28}.npy + hR_index.jsonl (read-position states; layers
    8-20 and suffix means kept on the run volume only), directions/anchors/basis npz, results/*.json, figures/*. Independent
    audit (analysis/audit_rederive.py): 99 numbers re-derived, 0 mismatches, placebos fail.
  workspace: >-
    /ai-inventor/aii_data/runs/run_4VFKidE1bxPG/3_invention_loop/iter_1/gen_art/gen_art_experiment_2
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 1
  name: gen_art_experiment_3
  type: experiment
  title: Do a few early tokens decide the algorithm?
  summary: >-
    Screen of 'fork tokens decide the idea' on Qwen3-8B (bf16, thinking off, vLLM 0.11.0) with two path-search coding tasks
    built here (T1 unweighted grid path, T2 weighted shortest path; 40 seeded hidden tests each, 17 reference solutions) under
    a neutral baseline prompt and a modal-ban prompt (ban:BFS on T1, ban:Dijkstra on T2). Labeller: sandboxed runtime tracer
    (instrumented heapq/deque/queue, grid reads, edge passes, call depth) + AST rules + OpenRouter judge on disputes (gold-set
    gate). Measurements on one shared pool of ~10k labelled generations: (1) S6 pools at global T in {0.3,0.7,1.0,1.3}; (2)
    Forking-Paths-style resampling screen over 40 base paths (S=8 every 4th token over the first 92 tokens for ban paths),
    permutation-calibrated multinomial change points, token-level localisation, S=30 confirmation with control pairs and next-token
    entropies; (3) prompt swap at the commitment token; (4) fork-window temperature knob vs global-T sweep, matched random-window
    and AdapT-style anchored controls; (5) residual-stream probes (layers 8-28) at R, k=8/16/32/64, fork and commitment positions
    vs prompt-only predictor with permutation nulls. Outputs: generations/*.jsonl, forks.json, swap.json, knob_table.json,
    probes.json, summaries/, figures/, states/ (split npz parts), method_out.json (exp_gen_sol_out) with the pre-registered
    verdict and rule trace.
  workspace: >-
    /ai-inventor/aii_data/runs/run_4VFKidE1bxPG/3_invention_loop/iter_1/gen_art/gen_art_experiment_3
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 1
  name: gen_art_experiment_4
  type: experiment
  title: Steering an LLM to vary its search algorithms
  summary: >-
    De-commitment steering screen on Qwen3-8B (thinking off) for two path-search tasks with hidden tests: T1 grid path (catalogue
    bfs/dfs/bidirectional_bfs/iddfs/astar/dijkstra_unit) and T2 weighted shortest path (dijkstra/bellman_ford_spfa/bidirectional_dijkstra/floyd_warshall/dial).
    Method: list-minus-implement difference-of-means direction d_dc (50+50 held-out frame paraphrases) at the last prompt
    token, layer L*=18 (held-out AUC 1.0 on all layers, d' tie-break), added as c*||h||*d_hat at R and every generated token;
    c swept over {0.25,0.5,1,1.5} + pre-registered bisection, c* chosen on pass rate only (T1 0.1, T2 0.25). Controls: HF
    c=0 hook, vLLM baseline N=200 (engine check passed), two random directions, variable-name placebo, breadth direction,
    cross-task transfer, enumeration prompt, modal ban and mention prompts, succession ban. Labels from sandboxed hidden tests
    + runtime tracer + AST rules, judge for disagreements; R0 and labeller gate pass on both tasks (2 revision rounds). RESULTS
    (verdict PARTIAL): T1 is 100% BFS in every arm except bans; steering never diversifies it (pass 1.00 -> 0.57 at c=0.25,
    still all BFS). T2: at c*=0.25 pass 0.78 vs 0.95, correct programs shift Dijkstra->Bellman-Ford (54 BF/23 D vs 7 BF/88
    D), rarefied Hill-1 +0.65 [90% cluster CI 0.31, 0.97]; but random direction rand1 does almost the same (+0.59; dc-rand1
    +0.07 [-0.26, 0.39]) so the gain is not direction-specific (beats rand2 and placebo). Enumeration prompt gives no diversity
    (T2 -0.08); the modal ban buys +0.79 at 1.5 pass points but most banned samples still use the banned algorithm. Commitment
    test: ban-minus-mention shifts R toward the list frame by 0.04/0.05 of the frame distance (exact permutation p 0.021/0.007;
    enumeration positive control 0.54/0.58). Hash-committed forecasts: on T2 the de-committed forecast scored best (log score
    -0.058 vs -0.219 frequency) on one informative event; T1 forecasts degenerate. Headline numbers re-derived independently
    (results/audit_rederivation.json); vLLM same-seed determinism failed on T1. REUSABLE: directions/ (d_dc per task and layer
    8-28, rand/placebo/breadth), cache/hR_*.npy (R-states, on the run volume), tasks/ (specs, hidden tests, 12 references),
    labeller/ (tracer, AST rules, judge prompt), gold/gold_set.jsonl, data/samples.jsonl (2,940 labelled samples), forecast/
    (sha256-committed forecasts), results/*.json, figures/fig1-5, method_out.json (exp_gen_sol_out; one example per common-random-number
    slot, output = HF c=0 label, predict_<arm> = label|pass/fail).
  workspace: >-
    /ai-inventor/aii_data/runs/run_4VFKidE1bxPG/3_invention_loop/iter_1/gen_art/gen_art_experiment_4
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 1
  name: gen_art_experiment_5
  type: experiment
  title: Did post-training cause Qwen3's algorithm collapse?
  summary: >-
    Screen of alternate 4 ('instruction tuning installed the algorithm-choice collapse') on Qwen3-8B-Base vs Qwen3-8B (thinking
    off), two path-search tasks: T1 unweighted grid path, T2 weighted directed shortest path. 4140 programs, each run on 47/46
    hidden tests and labelled by a runtime-signature + AST labeller with a blind LLM judge (gemini-2.5-flash-lite) for disagreements
    (reference gate: AST 100%, runtime never wrong; kappa runtime-AST 0.77; inter-judge kappa 0.93). 2x2 weights x format
    (T=1, top-p 1): instruct chat is collapsed (T1 BFS 200/200, Hill_cc 1.00; T2 Dijkstra 193/200, Hill_cc 1.16). The base
    model under the same chat tokens is more diverse (T1 BFS 49/57 correct, Hill_cc 1.58; T2 Dijkstra 63/90, Hill_cc 2.09);
    template-free base code is mostly broken (pass 5%/8%; T2 correct programs Bellman-Ford-modal 16/25). D_weights = Hill_cc(instruct_chat)
    - Hill_cc(base_chat) = -0.58 [-1.01,-0.15] (T1), -0.93 [-1.38,-0.46] (T2). Pre-registered verdicts: T2 INSTALLED_BY_POST_TRAINING;
    T1 MIXED (modal-share gap 14.0 pp, just under the 15 pp bar); no ALREADY_IN_BASE, so the alternate passes the screen (also
    under Hill_all). At the planned N (before the N=300 base extension) both read MIXED. Post-training concentrated the base
    model's existing mode rather than inventing one; the chat format also concentrates the instruct model on T2 (template-free
    Hill_cc 1.93 -> chat 1.16) and switches the base model's T2 mode from Bellman-Ford to Dijkstra. Mechanistic test: the
    paired instruct-minus-base residual difference at the read position (split-half cos 0.998, task-general cos 0.85-0.92,
    logit lens = answer-format tokens) subtracted over layers 8-28 is DESTRUCTIVE at c=0.5/1.0/1.5 (0/100 parseable), while
    norm-matched random directions keep format and algorithm; downstream layers amplify the subtraction (overshoot, gap_closed
    ~0 at L18/L28). Single-layer delta_18 fallback: c=0.25 keeps 94-98% pass with zero algorithm change (NO_EFFECT). R-only
    subtraction flips Qwen3 into thinking-style prose yet stated plans and correct programs keep BFS/Dijkstra. No knob restores
    diversity; the ban prompt does better (T2 Hill_cc 1.16 -> 1.99 at 0 pp pass loss). Hash-committed forecast from the base
    model hit top-1 on both ban events (DFS; Bellman-Ford), log score -0.47/-0.22 vs uniform -1.63/-1.41, but base-chat/typicality
    references did as well. All headline numbers were re-derived by an independent script (0 mismatches; placebo permutation
    tests reject at ~5%). Reusable outputs: runs/samples.jsonl (shared row schema, every sample), runs/labelled_*.jsonl, method_out.json
    (metadata = all analyses: collapse_screen, steering, rows.BUY / rows.PREDICT, labeller_qa, sharpening_direction), data/
    (prompts, hidden tests, references), src/ labeller + harness, activations/ (residual states, deltas, band steering vectors;
    kept on the run volume), predictions/ (committed forecast).
  workspace: >-
    /ai-inventor/aii_data/runs/run_4VFKidE1bxPG/3_invention_loop/iter_1/gen_art/gen_art_experiment_5
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 1
  name: gen_art_experiment_6
  type: experiment
  title: Do temperature and seeds change an LLM's algorithm?
  summary: >-
    Screen on Qwen3-8B (vLLM 0.11.0, RTX 5090) over T1 (unweighted grid path search, any valid path) and T2 (weighted directed
    shortest path). 5,220 generations, each labelled by hidden tests + runtime tracer + AST rules + blind judge: A0 no-cue
    baseline (N=100/task); A1 temperature grid T in {0.3,0.7,1.0,1.3} x {top-k=10, top-p=0.95}, thinking off, N=100/cell;
    A6 the same grid thinking on, N=100/cell; entropy/word/semantic seeds; four creativity instructions; forced implementations;
    gen-then-select. FINDINGS: (1) Temperature and sampler do not change the algorithm. BFS share on T1 is 797/800 thinking
    off (every cell >= 0.99) and 800/800 thinking on; Dijkstra share on T2 is 797/800 off and 800/800 on. (2) Phrasings grow
    with T while ideas stay at about 1: on T1 at theta=0.8, phrasing clusters go from 3-4 at T=0.3 to 24-36 at T=1.3; log
    PPI slope about +1.2 per unit T, paired CI > 0. T2 shows a smaller rise (1-2 to 3-6 clusters; top-p CI includes 0). (3)
    Random seeds shift behaviour by <= 1 pp (90% CI within +-15 pp). At the read position, the entropy seed stays within paraphrase
    noise (displacement ratio 0.73 T1 / 1.16 T2), but the word seed on T1 moves the mode subspace 1.56x (CI 1.27-1.87), close
    to a neutral insert (0.81/1.29). The semantic seed moves R 3.4-3.7x; on T2 it shifts behaviour 66 pp toward Bellman-Ford
    (p=0.0004), on T1 only +2 pp toward bidirectional BFS (p=0.08). (4) 'Fully novel' and 'list 10 then implement' cut T2
    Dijkstra by 15 and 11 pp. Gen-then-select reaches DA_idea@25 3.98/3.00 vs 1.26/1.00 for A0, at pass rates of 55%/75%.
    (5) Variance of trajectory states (first 64 generated tokens): complement variance rises steeply with T; the raw mode-subspace
    share is flat on T1 and rises slightly on T2; the excess over a data-matched null rises, so P7 is missed. (6) All thinking
    traces hit the 2,048-token cap; the first approach mentioned is BFS/Dijkstra in >= 98% of traces. Mechanical verdict:
    MIXED (S-T6 variance-share slope and random-seed equivalence at R fail). Hash-committed forecast: 6/8 hits. CAVEAT: the
    labeller gate failed by the strict plan criteria on both tasks, so results are descriptive. References agree 100%, population
    kappa(runtime, AST) is 0.88/0.85, gold agreement 93%/70%, and agreement on correct gold programs 92%/92%. REUSE: importable
    modules tasks/, tests/ (hidden tests + limits), references/, harness/, labeller/ (tracer, AST rules, judge, gold gate),
    prompts/, gen/, hooks/, analysis/. Per-sample rows (shared screen schema) are in results/samples.jsonl. Raw generations
    with token ids are in results/raw/. All results are in results/analysis.json and method_out.json metadata (deviations,
    gate, verdicts, forecast check, module sha256s). Figures fig1-fig6 are in figures/. Headline numbers were re-derived independently
    by verify_headlines.py; placebo tests are non-significant. OpenRouter spend was about $0.10.
  workspace: >-
    /ai-inventor/aii_data/runs/run_4VFKidE1bxPG/3_invention_loop/iter_1/gen_art/gen_art_experiment_6
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 2
  name: gen_art_evaluation_1
  type: evaluation
  title: When does the AI coder pick its algorithm? An audit
  summary: >-
    Round-one audit (no generation, no LLM calls, $0) of the six iteration-1 experiments of run_4VFKidE1bxPG (Qwen3-8B; T1
    grid path, T2 weighted shortest path), read in place via ITER1_ROOT. (0a) LOCUS: the iteration-1 probe never ran (exp3
    probes.json written 18:29, states saved 18:34). Re-run on the 2x300 saved states (8 positions x layers 8-28) with leave-one-paraphrase-out
    L2-logistic probes (batched torch IRLS, unit-tested vs sklearn), 200 global + 200 within-paraphrase refit nulls, layer-max
    family-wise null, written-text control, pre-commit qualifier. T1: mechanical verdict R - R already reads the within-ban
    outcome at BA 0.855 and the within-paraphrase null absorbs every generated position (paraphrase-level signal). T2: mechanical
    locus k_pre (BA 0.762 at L8, +0.281 vs R, within p 0.005; re-derived p 0.024 with 40 sklearn refits, placebo p 0.17) but
    qualified POST-COMMIT READOUT: the written prefix alone gives BA 0.756; the classes split at generated token 3 ('import
    heapq' vs 'from collections import deque', also exp3's confirmed fork), so unsaved states k=1..3 are the next round's
    extraction target. DiM AUC below the 0.9 bar (0.88 T1, 0.75 T2). (0b) GEOMETRY: exp2 matrices reproduced exactly; over
    1000 paraphrase subsamples x k{5,10,15,20} x layers, Floyd-Warshall (not BF/SPFA) is nearest to Dijkstra in 100% of draws
    at every T2 setting; T1 DFS nearest at L25-28 but flips at L24; wording: consistent with geodesic proximity and typicality,
    not separated. (0c) PERTURBATION TABLE: 249 condition rows / 20,270 programs with pass cost (Newcombe), compositions,
    runner-up shares (Wilson); on T2 8/8 non-semantic perturbations incl. random steering land on BF_SPFA. (0d) CORRECTIONS:
    T2 BF_SPFA 272/272 in 5/5 draws; T1 DFS 116/128 (realised mode 4/5 draws); cumulative BFS+DFS ban non-replicating; one-statistic
    knob table (compliant-only rarefied Hill-1, depth 25): no diversity knob or ban reaches Hill>=2 at <20 pass points on
    either task; PREDICT: 3 informative gated events (12 literal), no family advances; BUY: no knob advances. (0e) seed double
    dissociation; (0f) missing outputs incl. GPU hours and grid failure taxonomy; (0g) 2 sham-ban promotions, both content-neighbour
    AND runner-up (confounded); (0h) dated arXiv-verified positioning. Files: eval_out.json (+full/mini/preview; exp_eval_sol_out,
    80 metrics_agg, datasets perturbation_table/locus_cells/knob_table/geometry_grid), corrections.json, tables/*.csv, figures/*.pdf|png,
    results/*.json, audits (20/20 + 5/5 re-derived, placebos fail), README.md, reproducibility.md.
  workspace: >-
    /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_evaluation_1
  output_files:
  - eval.py
  - full_eval_out.json
  - mini_eval_out.json
  - preview_eval_out.json
  - reproducibility.md
- iteration: 2
  name: gen_art_experiment_7
  type: experiment
  title: Do algorithm bans pick a substitute or a ladder?
  summary: >-
    FRLP output-space screen of claim C1 (do prompt-level algorithm bans on Qwen3-8B pick a specific substitute or move mass
    along a generic ladder?) on the two iteration-1 path-search tasks (T1 grid, 6 algorithms; T2 weighted shortest path, 5).
    Provides: (1) 1,170 forced generations (10 forced paraphrases per algorithm, 3 adaptive vLLM rounds) labelled with the
    canonical runtime-led exp1 labeller (re-check: gold 0.965, references 22/22), name-scrubbed and verified; 211 selected
    programs (M=20 per algorithm after the pre-registered cut rule; bidirectional Dijkstra 11) in data/forced_selected.jsonl.
    (2) Teacher-forced scores of every program in 684 scoring units (condition x program set, Q1-Q7 + part of Q8; per-program
    parquet + per-token npz in scores/), computed with bf16 weights but fp32 activations/TF32 matmuls because bf16 numerics
    moved per-program log-likelihoods by up to 2 nats between equivalent paths (logs/scorer_validation*.json). (3) FRLP cells
    (yield-corrected mixture-proposal importance sampling, ESS per cell; results/frlp_cells.jsonl, 6 variants). (4) FRLP gate
    vs 19 exp1 sampled events: primary FAIL on calibration (a) (m=0.83<0.9: scrubbed programs give DFS mass under the T1 baseline),
    PASS on (b) 0.92 nats and (c) 16/19; 98% of gate cells have ESS<5. Diagnostic: the UNSCRUBBED variant passes all three
    (S=0.95, m=1.00; 1.18 nats; 17/19), so the failure is a name-scrubbing artifact; single-proposal also passes (reported,
    not adopted). (5) C1 (descriptive): pooled X-specific SHARE 0.55 [0.25, 0.67] (neutral twins), 0.66 [0.49, 0.87] (mention
    twins) -> pooled branch UNDETERMINED, robust across both references and the ESS-weighted variant; T1 is X-SPECIFIC-UNAIMED
    under the mention reference. Residuals are not aimed at the prime-and-veto profile (AIM -0.10, null p95 0.20, p=0.80)
    or free-form association (p=0.77); the 8 generic profiles do not form a coherent ladder (mean centred cosine 0.34 T1,
    -0.02 T2). Unscrubbed W1-only sensitivity: SHARE 0.69 [0.51, 0.84] (X-specific). Bans of absent algorithms raise their
    own FRLP (priming, +2.5 to +27 nats). Iteration-1 sham shifts (Floyd->BF/SPFA) equal the ladder component. (6) Frozen
    for the confirmation bench (hash-chained in commitments.log): frozen/aim_profiles.json, frozen/ladder_profile.json, frozen/templates_nouns_padding.json,
    frozen/code_sha256.json; prompts/prompts_v2.json (604 conditions, nouns, ' .' padding). Independent re-derivation (audit/rederive.py)
    matches gate, C1 SHARE, AIM and FRLP cells to <1e-15; placebo AIM sits at its null. Not run: Q8 shams (partial), Q9 variant
    (ii), exp2-exp5 extension. method_out.json (exp_gen_sol_out): 19 gate-event examples + 11 C1 rows. Recommendation: the
    confirmation bench should score unscrubbed programs.
  workspace: >-
    /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_7
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 2
  name: gen_art_experiment_8
  type: experiment
  title: Where a coding-algorithm ban takes effect in an LLM
  summary: >-
    Causal route test (C2) and compliance-at-R test (C5) for prompt-level algorithm bans in Qwen/Qwen3-8B (bf16, thinking
    off, Hub revision b968826d) on iteration 1's canonical tasks: T1 grid path with 'ban BFS' and T2 weighted shortest path
    with 'ban Dijkstra'. Each of 5 frozen ban templates has a token-length-matched neutral twin (irrelevant nouns in the same
    prohibition frame; identical ids from 'Task:' on), so the KV caches of the two prompts are spliced position by position.
    Arms: a full ban, b neutral (baseline), c PROMPT ROUTE (neutral condition span plus ban task-spec/R states), d DIRECT
    ROUTE (ban condition span plus neutral task-spec/R states), R-only, task-spec-only, placebo splice, condition-span attention
    knockouts (all generated tokens; first 16; after 16; layers 0-11/12-23/24-35) and a neutral-prompt knockout control. PRIMARY
    readout (FRLP drop of the banned algorithm over 30 self-written, name-scrubbed programs; decision rule sha256-committed
    before scoring): DECIDED BEFORE WRITING, carried by the prompt route, ROBUST across both tasks. Pooled F_prompt = 0.85
    [0.61, 1.20] and F_direct = 0.00 [-0.08, 0.12]. Per task F_prompt is 0.87 (T1) and 0.82 (T2). R alone carries nothing
    (F_R about 0); the task-spec states carry it (F_spec 0.86/0.81). Placebo splice: about 1% of the effect. All four pre-declared
    sensitivities agree. BEHAVIOUR (common random numbers, N = 100 per arm) qualifies T1. Banned share for a/b/c/d is 0.14/1.00/0.57/0.70
    in T1 and 0.11/0.99/0.13/0.95 in T2. A supplementary full-knockout arm restores T1 BFS to 0.47 but leaves T2 at 0.06.
    Mechanism: the ban suppresses the default first line ('from collections import deque' / 'import heapq'), and this opening
    veto is fully prompt-carried (0% import openings under a, c and the knockouts; 85% under d). In T1 the in-body algorithm
    choice also needs direct reads of the ban. A supplementary natural-proposal readout gives pooled F_prompt 0.57 and F_direct
    0.16 (super-additive). FRLP weights are degenerate for T1 (ESS 1-3), so likelihood readouts measure the opening veto,
    not calibrated probability ratios. Lens: the fork precedes the signature token (no veto layer at it); the substitute set
    rises from about layer 28. C5: on 110 wordings (exp1-exp5 plus 10 new cells), the combined within-cell Spearman of banned
    share against the h_R projection on a leave-one-experiment-out ban direction is -0.41 [-0.69, -0.17], p = 0.0003 (Holm
    0.0006). That is PARTIAL against the -0.5 bar; the ceiling is 0.77 and 98.5% of random directions are weaker. The decommitment
    axis is NULL; the substitute is not decodable beyond the projection. FILES: method_out.json and its full/mini/preview
    variants (1,400 behaviour samples, 110 C5 wordings, 130 FRLP route cells, every analysis in metadata); results/analysis.json,
    supplementary.json, c5.json, lens.json, natural_frlp.json, prereg.json, tests.json; data/samples.jsonl, frlp_programs.jsonl,
    frlp_scores.jsonl, token_lp/*.npz; figures fig1-fig6; reproducibility.md. Audits: 59 + 49 numbers re-derived independently
    with 0 mismatches, and every placebo/shuffle test fails. OpenRouter spend USD 0.32.
  workspace: >-
    /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_8
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 2
  name: gen_art_experiment_9
  type: experiment
  title: Banning five path algorithms in one prompt
  summary: >-
    Qwen3-8B (thinking off, vLLM 0.11, T=1.0) multi-name ban study on the iteration-1 grid-path (T1) and weighted-shortest-path
    (T2) suite, with mechanism-level labels (runtime tracer + AST + blind judge). The grid catalogue was extended to 10 algorithms
    (greedy split from A*, IDA*, JPS4, bidirectional A*) with new references (25/25 runtime and AST) and unit probes (4/4).
    The canonical labeller re-check gave 135/144 and 22/22. The 40-program gold gate was missed (33/40, then 32/40 after one
    revision; kappa 0.53), excluding unit-weight Dijkstra, JPS and bidirectional A*. KEEP RULE (>=70% of 40 forced programs
    labelled as requested): only BFS, DFS, IDDFS, greedy and IDA* pass, so the extension failed (F4). The analysis catalogue
    (K=7) adds A* and BiBFS (flagged), giving 4-name TOP/ARC/SCATTER bans plus the literal five-name TOP5. FRLP cells (about
    17k teacher-forced passes: ban, mention and neutral twins, nonce, LOS, tier 3) and six landing forecasts per set (LADDER,
    PRIME_AND_VETO, PROXIMITY, FRLP_BAN, GENERIC, CORPUS) were sha256 hash-chained before sampling; the chain verifies and
    the commit precedes session 2. RESULTS (N=100 per condition, 5 templates x 20): single bans work (T1 ban BFS: DFS 86,
    avoidance 0.86; T2 ban Dijkstra: BF/SPFA 83, avoidance 0.84). Every multi-ban fails its gate: TOP (BFS, DFS, greedy, IDDFS)
    avoidance 0.13; ARC (BFS, BiBFS, A*, greedy) 0.37 (DFS 37 survivor); SCATTER (BFS, DFS, greedy, IDA*) 0.04; TOP5 (adds
    A*) 0.00 (BFS 63, DFS 36). The banned BFS/DFS is re-implemented, 41-92% of the time without naming it ('backtracking').
    FRLP-implied avoidance foresaw the failure (<1e-8 for TOP, SCATTER and TOP5) but not ARC (0.9995 vs 0.37). Ban prompts
    raise the likelihood of the banned programs relative to neutral twins (priming). Landing rank tests are degenerate (survivor
    mass only in ARC and SCATTER; exact permutation p >= 0.33 per set, >= 0.11 pooled). On ARC the ladder-type forecasts hit
    DFS (+1.06 nats/program over uniform) and PROXIMITY missed. T2 leave-one-survivor: 'will' Dijkstra 0.95, BF/SPFA 0.51,
    BiDijkstra/Floyd/Dial 0.00, despite 'can' 0.35/1.0/0.9 when forced. Geometry: centroid MDS stress-1 0.025/0.006; neighbours
    BFS-BiBFS, DFS-IDDFS, A*-greedy; no persistent H1 loop. Within-ban probes at g16 are near chance on T1 and 0.69 balanced
    accuracy on T2 LOS(BF/SPFA) (p=0.03); 'pre' probes are a position artefact. POST HOC (not pre-registered): the BFS/DFS
    mix is the same across the four multi-bans (BFS share 0.63-0.72, chi-square p=0.48) whether or not DFS is on the list.
    A long ban list therefore acts like a generic perturbation of the default (about 1/3 DFS) rather than a list-specific
    veto, while a single BFS ban moves the model to 86% DFS. Every method_out example carries predict_default (no change)
    and predict_ladder. Multi-ban rows also carry the committed top-1 forecasts: on multi-bans the default is right 64% of
    the time versus at most 10% for any survivor forecast. Caveats: FRLP ESS < 5 in 97% of cells; bf16 scoring noise of about
    1 nat per program; T2 sum exp(L) is 0.17. FILES: method_out.json (exp_gen_sol_out, 1,950 programs with labels, tests and
    predict_* top-1 forecasts), data/samples.jsonl, results/*.json (landing, los, frlp_cells.jsonl, sets_and_geometry, manifold,
    persistence, catalogue_keep, labeller validation, checks, deviations, independent_rederivation), predictions/, commitments.log
    and figures/. The states/ activations (0.95 GB) are kept on the run volume and not published. Cost: about 1 GPU-hour on
    an RTX 4090 and USD 0.42 of judge calls.
  workspace: >-
    /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_9
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 2
  name: gen_art_experiment_10
  type: experiment
  title: Do algorithm bans work the same in Llama?
  summary: >-
    Second-model-family replication of the iteration-2 ban screen on meta-llama/Llama-3.1-8B-Instruct (bf16, default chat
    template, revision 0e9e39f). It uses the frozen SHARED PROTOCOL v2 (templates W1-W5, v2 display names, nonce ban, novelty
    instruction), exp1's canonical task suite and labeller (copied into canon/ with SHA256SUMS), and the 718-noun bank of
    art_j3Rm_lr2nzR6 re-tokenised under Llama (nouns 'man'/'guy'). PROVIDES: (1) 1,780 seeded vLLM generations with mechanism
    labels (data/samples.jsonl, data/labelled.jsonl): baselines, modal bans, mention twins, listall, two non-default bans
    and two-step bans per task (14 events), 880 forced programs and 220 free-form association answers. (2) 248 name-scrubbed
    self-written forced programs and 39,768 HF program scores (frlp/parts, frlp/scores_<task>.parquet), with FRLP cells and
    ESS in 5 variants (frlp/cells.jsonl). (3) Results in results/*.json and figures/. KEY FINDINGS (all descriptive: two tasks,
    one model). Llama's T1 baseline is NOT collapsed (BFS 77, DFS 20) and its pass rate is low (0.20). T2 is collapsed (Dijkstra
    92, pass 0.59). Ban BFS -> DFS 63/100; ban Dijkstra -> Dijkstra 43, other 37, BF/SPFA 18. Both two-step bans fail (avoidance
    0.16 and 0.44). On T2, bidirectional Dijkstra and Dial were unwritable (M <= 2 after 120 attempts), so K = 3 and no T2
    row has 3 survivors: C1 is T1-only. The FRLP gate FAILS: (a) T1 implied BFS 0.43 vs sampled 0.77; (b) passes at 0.59 nats/sample;
    (c) 7/10. Median cell ESS is 2.5. C1 under the neutral reference: SHARE 0.80 (95% percentile CI 0.28-0.94) -> 'not resolved
    at this N'; no aim (prime-and-veto AIM 0.067 vs exact-null q95 0.258; association -0.08); no ladder (mean generic cosine
    0.14). Under the mention reference: X-SPECIFIC BUT UNAIMED. Not robust. Post hoc: program-level importance-sampling noise
    dominates (bootstrap variance of gbar 5-11x the replicate Sigma; the basic interval for V_tot covers 0), and SHARE is
    fragile (0.41 without 5 audit-disputed programs). Naming an absent algorithm in a ban RAISES its FRLP in 5 of 6 cases
    (+1.8 to +7.6 nats; mention prime +6.7 to +14.4, veto -4.9 to -10.1). Route test (FRLP-only): the modal ban's own-drop
    travels mainly by the prompt route (F_prompt 0.84, CI 0.62-1.46; F_direct -0.21). Per-sample top-1 accuracy over 743 samples:
    the empirical sampled ladder (0.70) beats FRLP (0.59; paired p < 1e-4); on single bans they tie (0.67 vs 0.67). Labeller
    re-check reproduces exp1 (22/22, 0.966); the Llama label audit agrees at 0.78 (flagged). Tests T2-T11 are in results/;
    97 numbers are independently re-derived (audit/). Deviations (30) are in results/deviations.json, including bf16 T4/T7
    tolerance failures and the crossed-design noise bias. Cost: USD 0.49 OpenRouter, about 0.64 logged GPU-hours on one RTX
    4090.
  workspace: >-
    /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_10
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 2
  name: gen_art_experiment_11
  type: experiment
  title: Coding-task bench with a baseline pilot
  summary: >-
    Frozen confirmation bench (iteration 2) for an algorithm-choice study; no ban prompt rendered anywhere (audit: 0 hits
    in 4,310 prompts). 13 LeetCode-derived tasks (T03 k-th smallest, T04 substring, T05 two-sum, T06 find duplicate, T08 Fibonacci,
    T10 components, T11 LIS, T13 merge intervals, T14 top-k, R1 non-overlapping intervals, R2 cycle detection, R3 topological
    order, R6 first/last position) each get bench/<task_id>/: spec.json (frozen wording + catalogue of 3-6 modes, 54 total,
    display names, aliases), tests.jsonl (684 hidden cases total, per-case limits = max(1s, 10x fastest reference)), checker.py
    (order-free), references/<mode>.py (54, all pass at <=0.25x limit; 39 mutants fail), ast_rules.py + runtime_rules.py +
    probes.json (gated labellers: runtime tracer primary, AST second, blind judge on disagreement), gold_set.jsonl (2 blind
    judges + tie-break), gate.json, forced_programs.jsonl, pilot_rows.jsonl, association.jsonl, frlp_sets.json (frozen M_j
    with halves), frlp_baseline.jsonl, neutral_nouns.json. All 13 passed the labeller gate (kappa runtime-vs-AST 0.84-1.00,
    refs 100%, runtime vs adjudicated >= 0.91; T03/T13 after one revision round with holdout); 12 frozen in Stage-A order
    (bench/commitment.json + commitments.log hash chain), R2 excluded by the 12-task cap. Model: Qwen/Qwen3-8B-FP8 via vLLM
    0.11 FP8 Marlin, eager (16 GB GPU, no C compiler); T=1.0, top_p=1, thinking off. Pilot (data/samples_pilot.jsonl, 50/task):
    fully collapsed on all 13 tasks (modal share 1.00, R6 0.98; Wilson [0.929,1.0]); pass rate >= 0.92. Optional Llama-3.1-8B-Instruct-FP8
    pilot (data/samples_llama_pilot.jsonl) is far more diverse (e.g. T03 modal 0.34). Association: 20 free-form 'standard
    alternative to X' answers per mode (data/association.jsonl), near-deterministic. Forced programs: >=40 attempts/mode from
    exp1's paraphrases ids 0-4 (+ top-ups and a descriptive variant for low-adherence modes), name-scrubbed and verified (same
    tests, same runtime label), data/samples_forced.jsonl with labels and adherence (45/54 modes >= 0.5; R3 layering/source_removal,
    T13 interval_tree, R1 DP variants, T06 index_marking, T10 label_propagation low). Baseline FRLP cells (data/frlp_cells.jsonl;
    method_out dataset frlp_baseline_cells): log q = mixture over generating prompts, w = l(base) - log q, L_corr = logmeanexp(w)
    + log adherence, with Kish ESS (34/54 cells < 5), halves, generating-paraphrase-only and correct-only sensitivities; argmax(pi)
    = pilot mode 13/13, beats uniform log score 13/13 (placebos 0/13), S in [0.3,3] for 11/13. Stage-A order (assoc/proximity/ladder
    disagreement): T03,T04,T06,T05,T10,R1,T08,R3,T13,R6,T14,T11,R2; Stage-B (FRLP-broken ladder, forced-program proximity):
    Kendall tau 0.54. method_out.json (exp_gen_sol_out): bench_candidates (13 rows with predict_ladder baseline vs predict_association
    / predict_proximity nominations, pilot stats, gate, FRLP, validity) + 54 FRLP cells. Every headline number independently
    re-derived (results/rederive_headlines.json). Deviations listed in metadata.deviations (FP8 checkpoint, vLLM prompt-logprob
    scoring instead of HF, 5-paraphrase proposal, batch-dependent scoring differences up to 0.62 nat). NOT produced: Llama
    forced programs/FRLP, ban/mention/neutral FRLP matrices, any sampled ban event, code-only unscrubbed sensitivity.
  workspace: >-
    /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_11
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 2
  name: gen_art_experiment_12
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
    (4) Replication on the fresh pool: exp3-fitted DiM transfers best (T1 within-template AUC 0.93-1.00, only W4 has both
    classes; T2 0.66-0.76); single top latent fails (0.27-0.80); shuffled-label placebo ~0.50. (5) Attention: same ban-specific
    heads on both tasks (L21H17, L26H21, L26H25; +0.21/+0.10 attention mass to the ban segment vs the token-matched neutral
    twin), focused on the banned name tokens; T1 compliant runs attend more (p=0.0025, within W4). (6) Prime-veto pattern
    absent in 6/6 configs; at L27 NAME(X) and IMPL(X) latents are lower at k_pre under the ban than under both twins for the
    same text. (7) Thought anchors: T1 thinking runs 8.4-9.3k tokens (0/5 within the 8,192 cap) and DFS is fixed at the first
    resample point (D_0=1.0 in 4/4); T2 1 anchor in 32 sentences; early-label validity 13/16. (8) Same-seed CRN: ideas do
    not change with temperature (0/30 in 10/12 cells), so same- vs different-seed idea agreement is identical; phrasing changes
    less within a seed (e.g. 0.55 vs 0.76). (9) J-lens (community lens) fails its gate vs the logit lens (L27 top-1 0.104
    vs 0.291); NLA not available for Qwen3-8B (dated 2026-10-20). Headlines re-derived independently (69 checks, 0 mismatches;
    float64 sensitivity noted). Kept on the run volume: results/tensors/ (E2 states, attention masses, SAE context codes).
    Deviations: results/deviations.json; not run: Gumbel-max sensitivity, E6, NLA.
  workspace: >-
    /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_12
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 3
  name: gen_art_evaluation_2
  type: evaluation
  title: Record repair and novelty audit of algorithm bans
  summary: >-
    CPU-only Step 0 of iteration 3: repairs the iteration-2 record from data on disk and answers the novelty question (eval.py,
    sections/, eval_out.json in exp_eval_sol_out with 72 metrics and 7 datasets; corrections.json; tables/; figures/; audit/).
    Sources are cited as '<artifact_id>:<relative path>'. (0a) C1 likelihood diagnostics on exp7/exp10: the gain argmax (full
    and residual) hits the realised landing in 0/17 Qwen single-ban events (chance 0.22) while the implied-mass argmax hits
    14/17 (8/8 modal); no ban row keeps 3 survivors with >=1% mass and ESS>=5 (0/11), so C1 is not decidable on estimable
    mass; two-stage bootstrap variance of Gbar is 2.7x (1.2-4.3) the replicate noise term (Llama 4.8-11.3x); the mention-reference
    AIM is biased negative by construction (null mean -0.27 to -0.33): Llama -0.28 sits at the null's 66th percentile, Qwen
    -0.595 below its 1st; the ESS-weighted 1.24 share is impossible (V_u -35.4); plug-in M5 >= 50 programs per algorithm (lognormal
    ~1e31; 22% of pooled PSIS k-hat > 0.7) and ~129 Qwen / 43 Llama bench events would be needed to separate SHARE from 0.5
    by 0.10. (0b) exp9 manifold: 13 figures (not 14); recomputed geometry matches exp9 (24/24 nearest maps); the BFS-BiBFS
    adjacency does NOT survive at the label-independent g16 position (N1 p 0.19, exchangeability p 0.48, separability 0.96);
    no persistent H1 loop, powered at 'pre' (planted-loop power 1.00) but not at g16 (0.04). (0c) Novelty: 78 unique correct
    out-of-catalogue programs across the 11 declared artifacts + exp3 pools copy, 0 novel (two blind judges gpt-4.1-mini /
    gemini-2.5-flash, deepseek tie-break, full manual read; rule-of-three bound 0.038); judge kappa 0.38; positive controls
    7/10 strict (10/10 named correctly), negatives 5/5; TOP's 0.13 avoidance = 12 degenerate failing programs + 1 unit-weight
    Dijkstra, not non-banned catalogue algorithms. (0d) Llama correct-only: all quoted compositions reproduce; T1 correct
    programs are all BFS (Hill_cc 1.00 vs Hill_all 1.87); Llama more diverse than Qwen on 9/13 bench tasks at depth 10. (0e)
    Knob table rebuilt (306 rows vs the audit's 249): no KNOB under 20 pass points reaches rarefied Hill-1 2; best exp6 semantic
    seed T2 1.940 [1.770, 2.094]. (0f) 12/12 positioning quotes verified (2026-10-20). (0h) 12 corrections (R01-R12) with
    replacement sentences; 16/19 quoted reproduction targets match, mismatches explained. audit/rederive.py re-derives 72/72
    headlines independently and all 7 placebos fail as required. Judge spend USD 0.415 (responses cached in audit/judge_cache.jsonl).
    Kept on the volume only via the dependencies: exp9 states needed to rerun (0b).
  workspace: >-
    /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_evaluation_2
  output_files:
  - eval.py
  - full_eval_out.json
  - mini_eval_out.json
  - preview_eval_out.json
  - reproducibility.md
- iteration: 3
  name: gen_art_experiment_13
  type: experiment
  title: Forecasting where coding bans send a model
  summary: >-
    Iteration-3 confirmation experiment on Qwen3-8B (bf16, rev b968826d, thinking off) over the 12 frozen bench tasks of exp11
    (art_0ndRfWKBWclR). Ban-free forecasts of where each task's modal 'do not use X' ban lands were built and hash-sealed
    (commitments.log, SEAL_BEFORE_BANS) before any ban sample: SUBTRACT (token vetoes of the default's distinctive n-gram,
    coupled to neutral-twin samples by exact rejection + masked redraw via vLLM logit_bias; one-shot, persistent, 3 iterated
    rounds), LADDER (nonce ban, novelty instruction, 3 matched-norm isotropic random directions patched into task-spec states
    at layers 12-23), ASSOCIATE (exp11 association answers) and PROXIMITY (AST Zhang-Shasha distance). Then 1,200 ban samples
    (5 templates x 20 per task) were labelled by the gated exp11 labellers (re-check matched gate.json on 12/12). RESULTS:
    only 5/12 bans pass the gate (T03, T06, T05, T10, T13; R1, R3, R6, T11 keep the default almost always). The frozen C1
    rule returns 'SUBTRACTION/LADDER (LADDER)' (wins LADDER 3, PROXIMITY 2), but 2 of LADDER's wins come from an undefined
    forecast scored as uniform; counting defined forecasts only, no family advances, and no family beats the uniform reference
    on average (mean log score minus uniform over gated events: LADDER +0.06, SUBTRACT -0.69, PROXIMITY -1.53, ASSOCIATE -1.78).
    Landings are X-specific but largely unforeseen (T06 -> index_marking, T10 -> bfs, T13 -> 'other'; only T03 quickselect
    and T05 brute_force were hit by a top-1). C2b is UNDETERMINED: one-shot vetoes never reach 0.5 avoidance on a gated task;
    descriptively the last iterated veto round lands elsewhere on T06 and T10. Token vetoes move the surface, not the algorithm:
    the default re-emerges in every veto round on 9/12 tasks, with text-level leaks of the vetoed n-gram in 23% (one-shot)
    to 54% (round 2) of samples; a sham veto breaks programs without moving the algorithm. Band-patching the ban's own task-spec
    states into the twin reproduces avoidance only on T03 and T10. Wording matters: template LR 374 (df 4, p ~ 1e-79; shuffled
    placebo p 0.39), W4 'X is not allowed here.' fails on 10/12 tasks. FRLP fp32 rescoring: median |dL_corr| 0.88 nats vs
    FP8, argmax unchanged 12/12. FILES: method.py (stage CLI), src/ (pipeline), method_out.json (exp_gen_sol_out; dataset
    modal_ban_samples with predict_subtract/ladder/associate/proximity = committed top-1s; dataset ban_free_arm_samples; metadata
    holds every analysis and the deviations), data/samples.jsonl (9,350 per-sample rows with veto metadata), data/raw and
    data/labels, results/c1_events.jsonl, results/analysis.json, results/posthoc_sensitivity.json (post-hoc, not pre-registered),
    results/frlp_rescore.json, results/tensors/norms_<task>.npz (ban-minus-twin displacement norms and mean vectors at layers
    12-23, reusable for an X-free direction), predictions/ (committed forecasts, n-grams, iterated chain), figures/. AUDIT:
    audit/rederive.py and audit/rederive_raw.py re-derive every headline number from raw files with 0 mismatches; task-shuffled
    and template-shuffled placebos fail as required; not independently re-derived: mixed-GLM SDs and descriptive C2b null
    p95s. CAVEATS: one model, memorised LeetCode tasks, 5 gated events (advance count, no significance test); one documented
    post-ban portability edit of src/common.py (paths only); judge spend USD 0.024.
  workspace: >-
    /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_13
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 3
  name: gen_art_experiment_14
  type: experiment
  title: Show a solution, ban it, see what replaces it
  summary: >-
    Exposure-ban experiment (Step 1b) on Qwen3-8B (bf16, thinking off, vLLM 0.11.0, revision b968826d) over the 12 frozen
    tasks of the exp11 algorithm-choice bench (sha256-verified copy in bench_copy/; labeller re-check reproduces every gate.json
    value, references 100%). For each of 33 eligible non-default algorithms Y (19 priority Y whose frozen associate differs
    from the default), the prompt shows up to 5 name-scrubbed correct programs of Y, then asks COPY 'Write a correct solution.',
    NAMED '... that does not use {Y}.' (= template W5) or UNNAMED '... uses a different algorithm from the one above.' (N
    = 50 per Y and arm, seeds shared across arms). Four forecast families are committed in a sha256 hash chain before any
    ban sample: LADDER (default), ASSOCIATE (modal frozen 'standard alternative to Y'), PROXIMITY (nearest survivor by Zhang-Shasha
    distance on identifier-normalised ASTs; token-distance sensitivity) and SUBTRACT-IN-CONTEXT (non-Y landing under an iterated
    persistent signature veto of Y's distinctive token n-gram under the copy-twin prompt, implemented as a vLLM V1 per-request
    logits processor; GPU smoke tests: 0/20 vetoed n-grams vs 20/20 in the copy twin, inert veto 20/20 identical, twin divergence
    exactly at the vetoed position 20/20). Outputs: data/samples.jsonl (one row per program, gated bench labeller: runtime
    + AST + blind judge), results/c1_events.jsonl (one row per (Y, NAMED/UNNAMED) event in the frozen schema with forecasts,
    top-1s, log scores, gate), results/c1_summary.json (frozen advance rule, Holm-corrected paired Wilcoxon tests with task-cluster
    bootstrap CIs, branch verdict, sensitivities, C1-exposure, placebos), results/other_reports.json (copy rates, snap-back
    to default, named-vs-unnamed agreement, disguise, heterogeneity, veto diagnostics, template arm), predictions/ (committed
    forecasts and prompts), commitments.log (COMMIT #0/#1/#2 hash chain), audit/rederive.py (independent re-derivation + placebos),
    figures/, and method_out.json (exp_gen_sol_out: datasets exposure_events and exposure_samples). Note: this summary is
    interim and is rewritten with the final numbers when the analysis finishes.
  workspace: >-
    /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_14
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 3
  name: gen_art_experiment_15
  type: experiment
  title: Where Llama goes when an algorithm is banned
  summary: >-
    Llama-3.1-8B-Instruct (bf16, rev 0e9e39f) replication of Claim 1 (does a ban remove the default and send the model to
    a predictable next rung?) on the frozen 12-task exp11 coding bench, plus a descriptive path-task screen against exp10's
    landings. Ban-free forecasts were built and sha256 hash-chained before any ban prompt was rendered (grep audit: 0 ban
    prompts in 10,328 prior rows): SUBTRACT (exact one-shot/persistent/iterated signature-n-gram vetoes by truncate-and-redraw
    in vLLM), LADDER (nonce ban, novelty instruction, 3 matched-norm random directions added at the spec positions of layers
    11-21 during prefill), ASSOCIATE (Llama's own association answers) and PROXIMITY (Zhang-Shasha AST distance), in a mass-transfer
    form with point-mass sensitivities. Then 1,800 bans were sampled (12 modal + 6 present-minor events, W1-W5 x 20) and scored
    with the frozen C1 rule. Results (within Llama, pre-pooling): 13 events gated, 11 disagreeing and gated; only 2 wins (SUBTRACT
    on T05 via its undefined->uniform fallback; ASSOCIATE on T03 heapify_pop), so no family advances and the branch is 'NO
    FAMILY ADVANCES (aimed, unresolved)'. Exact Wilcoxon (n=11): SUBTRACT and LADDER beat PROXIMITY (+0.345 / +0.306 nats,
    p=0.0029 / 0.0020, Holm-rejected); neither separates from ASSOCIATE (p=0.52 / 0.77). Top-1 hits: LADDER and ASSOCIATE
    7/13 (binomial p=0.033 vs chance 0.27), SUBTRACT 4/12, PROXIMITY 3/13. Fragile: correct-only, bf16-only decision set and
    drop-W4 sensitivities give SUBSTITUTION (ASSOCIATE). Five defaults (R1, R3, T13, R6, T11) are not avoided under the ban
    (avoidance 0.04-0.30), and surface-token vetoes rarely remove a default (only T14 heap). Re-derived independently from
    raw files with placebos that fail as required: gate/landings/log scores/wins/branch (audit/rederive.py) and the Wilcoxon,
    Holm, top-1 binomial tests and D per task (audit/rederive_tests.py). Not separately re-derived: H3 sensitivity rows, bootstrap
    CIs, C2b, present-minor gain, knob view, screen scores. Provides: results/c1_events.jsonl in the shared c1_events schema
    for pooling with Qwen next round; method_out.json (llama_bench_events, llama_ban_samples, llama_screen_events); all raw
    generations, labels and judge caches (data/); the committed forecasts (predictions/, commitments.log); figures; README.md
    and reproducibility.md. Compute: one NVIDIA L4, about 1.8 GPU-hours; OpenRouter spend USD 0.48.
  workspace: >-
    /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_15
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 3
  name: gen_art_experiment_16
  type: experiment
  title: Where a coding ban takes effect in Qwen3-8B
  summary: >-
    Behavioural route test of prompt bans in Qwen3-8B (bf16, thinking off) on the 12 frozen exp11 bench tasks, reusing exp8's
    HF engine (common-random-numbers inverse-CDF sampling, KV-cache splicing). 13,030 CRN-coupled samples, all labelled by
    the frozen runtime+AST+judge labellers (judge spend USD 0.105). Arms per task: a full ban, b token-matched neutral twin,
    c prompt route (twin condition + ban task-spec states), d direct route (ban condition + twin task-spec states), K0 (condition
    span invisible to generated tokens), V1 one-shot veto of the default's frozen distinctive n-gram, and signature/neutral
    prefills under ban and twin. GATE: only 5/12 tasks are gated (T03 0.99, T10 1.00, T05 0.83, T06 0.79, T13 0.59 avoidance);
    bans fail on R1/R3/R6/T11 and partly on T04/T08/T14; template W4 is weakest (avoidance 0.19). C2a (prompt route >= 2/3):
    DISCONFIRMED under jackknife (primary, low-cluster per F5), percentile and BCa intervals: pooled F_prompt 0.611 [jackknife
    0.06, 1.17], F_direct 0.744 [0.38, 1.11], interaction -0.355, F_K0 0.621. Mechanism is task-dependent: T03/T10 redundant
    (each route alone suffices), T05/T06 direct route (F_direct 0.96/0.99; d reproduces the ban, c and K0 do not), T13 superadditive
    (both needed). An independent second CRN draw reproduces it (pooled 0.64/0.74; per-task Spearman 0.89/0.90). C2c (veto
    sufficiency predicts F_direct): INCONCLUSIVE; the frozen n-gram rule picks zero-collateral identifier/structural tokens,
    so V_t <= 0.41 everywhere, all tasks classed HIGH_DIRECT, hit fraction 0.80, rho -0.34 (exact permutation p 0.30). Prefill:
    forcing the default's opening up to its first body token undoes the ban completely (P_open 0.98-1.00) while a neutral
    def line undoes none (-0.12-0.01); the depth sweep shows the ban survives the def line and gives way at the first content
    token of the body. Path screen (T1/T2, exp8 twin prompts): one-shot, persistent, iterated and opening vetoes never move
    the default (off-default <= 0.01); committed T1 prediction hit, T2 prediction (veto suffices, lands on BF/SPFA) missed;
    iteration-2 ban landings recomputed exactly (T1 DFS 257/257, T2 BF/SPFA 255/260). Controls: placebo splice |diff| <= 0.04
    and knockout-mechanics K0b 1.00 on 6 tasks. Validation: bench sha256 vs commitment.json, labeller re-check, prompt alignment
    asserts, CPU tests, GPU tests U1-U3 (CRN determinism, splice identities, zero knockout attention mass) and U9 vs exp8
    all pass; two hash-chained pre-registration commits precede the first ban rows; two audit scripts re-derive every headline
    from raw rows (0 mismatches; placebo/shuffled inputs fail). Provides: data/samples.jsonl (one labelled row per sample,
    token ids in data/samples_raw.jsonl), results/*.json (route, crn_flips, landing_by_route, c2c, prefill, screen_paths,
    replication incl. depth curve, lp_readout, c1_events.jsonl, gate, timing, deviations, rederive/rederive2), figures fig1-fig6,
    method_out.json (exp_gen_sol_out; datasets route_arms, veto_sufficiency, prefill, path_screen, controls) and README/reproducibility.
    Deviations: L4 GPU with B=40 shape classes, K0 as a span-dropped cache, fence stop, extras beyond plan, three logged analysis
    amendments.
  workspace: >-
    /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_16
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 3
  name: gen_art_experiment_17
  type: experiment
  title: Searching Qwen3-8B for where a coding ban lives
  summary: >-
    Internal-locus experiment on Qwen3-8B (pinned b968826d, thinking off, T=1.0) asking where a prohibition such as 'Do not
    use Dijkstra's algorithm' lives. It covers 6 tasks: path tasks T1 (BFS default) and T2 (Dijkstra), and bench tasks T03
    (full sort), T04 (naive window), T06 (hash set) and T05 (hash map). Engine: HF with FP8 W8A8 linears (16 GB RTX 2000 Ada;
    U7 reproduces exp8: T2 ban 2/20 Dijkstra, twin 20/20), the exp8 inverse-CDF common-random-numbers sampler with exact coupling
    (U1b), 7,300 labelled samples (5,500 frozen design, 1,800 exploratory), and rules hash-chained before sampling. C2d DISCONFIRMED:
    a leave-one-task-out prohibition direction (blocks 12-23, task-spec positions; split-half cos 0.95-0.99; aligned with
    held-out tasks' mean ban displacement, cos 0.29-0.86) written into the neutral twin (displacement-targeted ADD, alpha
    0.5/1/2) passes on 0/5 gated tasks against 3 norm-matched random directions. It is within the random range on 5/6 tasks;
    on T03 it beats random but lands on a size-k heap, not the ban's quickselect. Projecting it out of the ban never restores
    the default (pooled delta -0.026, CI [-0.07, 0.03]). With 15 random directions (exploratory), v is at the 80th percentile
    on T2. C2e: no within-ban locus on any testable task (batch-1 teacher-forced states, blocks 8-28, tokens 1-8/16, 500 within-template
    permutations, text controls). The class is set by the template (W4 keeps the default 20/20 on bench, all 61 T1 BFS) or
    by tokens after 16 (T2 fork median ~29 tokens). States of identical prefixes are bit-identical. FP8 caveat: 20-row teacher-forcing
    batches add 4-10% row-position noise, so states were re-extracted at batch 1; the batch-20 sensitivity run gives the same
    verdict. C2f NOT SUPPORTED: mean-ablating L21H17/L26H21/L26H25 gives T1 delta +0.06 over layer-matched random heads (any
    head ablation breaks the fragile W4 ban); T2 unchanged. 0g: Qwen-Scope base SAEs pass the frozen FR_zero rule (instruct
    0.989-0.994 vs base 0.991-0.993, own text, 2x2 model x text). The rule also passes on placebo input, so it is lenient.
    The SAEs keep only cos ~0.3 of the ban-minus-twin displacement; 5a latents never beat DiM (1/63 trivial cells). Outputs:
    results/*.json, figures fig1-fig9, method_out.json (datasets c2d_arms, c2f_heads, c2e_locus, sae_transfer; one CRN slot
    per example with predict_<arm>=label|pass), directions/ (v per task, random dirs), states/ (fp16, kept on the run volume),
    and an audit with independent re-derivation and placebo tests.
  workspace: >-
    /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_17
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 3
  name: gen_art_experiment_18
  type: experiment
  title: How far bans and token vetoes push Qwen3-8B
  summary: >-
    Step 4 of iteration 3 on Qwen/Qwen3-8B (path tasks T1 grid, T2 weighted SP in bf16; bench T03 k-th smallest, T04 substring,
    T06 duplicate, T10 components on the official FP8 checkpoint, each family at the precision of its iteration-2 references).
    (4b) TOKEN WALK: persistent per-request logit vetoes (vLLM 0.11 AdapterLogitsProcessor, src/veto.py) of each default's
    distinctive lexical n-gram under neutral twins, with up to 2 extra mask rounds for string leaks / re-emergence. The veto
    is exact (0 banned-sequence occurrences in 1,450 vetoed generations) but the walk STALLED on all 6 tasks: at step 1 on
    T1, T2, T03, T04, T10 and at step 2 on T06 (rung 2 = sort+adjacent). The default returned by renaming (current_row/current_col;
    current_distinct), non-canonical spellings ((parent, parents, \tparent; leak up to 0.86) or near-miss syntax (T1 66-86%
    invalid). A matched SHAM veto kept the default (T1 50/50, T2 50/50, T04 49/50, T10 44/44 valid) while the distinctive
    veto cut T2 pass from 50/50 to 19/46 (Fisher p~8e-12). Fixed TOP5 veto on T1: BFS 13, DFS 2, invalid 35 (exp9 TOP5 prompt
    ban: avoidance 0). (4a) PROMPT REACH: 17 leave-one-survivor lists (N=50) + two-step bans (N=100). C3 (will<=0.10 at rung>=3
    where can>=0.7) is DISCONFIRMED: T03 quickselect will 1.00 and T10 BFS 1.00 (both rung>=3 via flagged fallback R2; a post
    hoc association-rung sensitivity keeps T10); confirmed cells T2 Floyd 0.00 (exp9), T03 size-k heap 0.00, heapify-pop 0.00,
    T06 value bisection 0.00; T06 Floyd 0.14; T04 untestable. Negative-constraint priming: the T03 list leaving only the default
    yields quickselect 50/50. Two-step compliance: T1 0.02, T2 0.01, T04 0.14 vs T03 1.00, T06 0.96, T10 1.00. Preregistered
    list-independence fails on T04 (p=0.033; placebo median p 0.51). Forced can underestimates T06 index marking (0.03) which
    LOS bans elicit 34-40/50. (4c) LONG-FORM NOVELTY: the request's two 2,000-word 'make a (fully) novel algorithm' instructions,
    575 outputs (thinking off N=25-50/cell; thinking on N=10/cell, 100/100 traces complete). 84% claim a new algorithm; 39%
    of those contain no code; 75% of the rest are catalogue algorithms. NOVEL = 0 in every cell/arm: 53 programs (38 correct
    off-catalogue) audited by two blind judges (control gate 5/6 each; kappa A-B 0.27) + manual pass with 3 extra sandboxed
    tests against 472 known human/textbook solutions from art_j3Rm_lr2nzR6 -> 31 labeller misses (mostly T03 counting sort),
    10 catalogue variants, 12 degenerate. Upper bound on the novel rate 0.058 per N=50 cell. bf16 vs FP8 cross-check (LF1-T2):
    JS 0.033 bits vs null p95 0.068 (p=0.35). FILES: method_out.json (+full/mini/preview; exp_gen_sol_out; datasets token_walk,
    prompt_reach, long_form, audit; metadata = all analyses, deviations D1-D17, not_run, costs, commitment chain); data/samples_<arm>.jsonl
    per-program rows (label, pass, code, veto/leak/thinking fields) and data/raw_<arm>.jsonl (text + token ids); results/*.json
    (walk, c3, reach, list_independence, disguise, longform, fp8_crosscheck, novelty_audit, manual_audit, claims, can, labeller_recheck,
    verify_headlines, rederive); predictions/ + commitments.log (hash chain; analysis.py edited after its commit, D17, preregistered
    numbers re-derived independently with 0 mismatches); figures fig1-fig5. OpenRouter spend USD 0.49. Dropped: manifold placement,
    5b sweep, T1/T2 thinking extension to N=25.
  workspace: >-
    /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_art/gen_art_experiment_18
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 4
  name: gen_art_evaluation_3
  type: evaluation
  title: Record repair and a frozen push screen
  summary: >-
    CPU-only Step 0 of iteration 4 (record repair + frozen push screen). Every number is recomputed from labelled rows of
    the 11 declared dependencies (exp4, exp6, exp7, exp9, exp11, exp13-exp18) with '<artifact_id>:<relative path>' provenance;
    no model text generated; judge spend USD 0.22. PROVIDES: (1) screen.json, the frozen push-movability screen in canonical
    JSON, sha256 d6a2ca9711f461973c39482314a523d448d0590cb40e32432826dec1da4846e8, with the stdlib-only screen_rule.py (reproduces
    it byte for byte from screen_input.json) and screen_extras.json (per-direction rows, per-engine counts, power notes 1-0.1^(1/K),
    descriptive Fisher p, discrepancies). Movable tasks = T03, T05, T06, T1, T10, T2 (= frozen C1 set); movable vs catalogue-only
    modal-ban avoidance >= 0.5 is 6/0/0/8 (one-sided Fisher p = 1/3003, screen not confirmation); T10 escapes only on the
    bf16 HF engine (exp13 rand3), the rest on exp17 FP8 directions; the immovable side is weakly tested (mostly K=3, UB90
    0.54). (2) tables/knob_table.csv: 1,120 artifact x task x arm x dial cells, each priced against its own twin (pass cost
    with Newcombe CI), correct-only rarefied Hill-1 at depth 25 with template/iid 90% CIs, Good's coverage, catalogue-only
    avoidance, escape/qualify flags; arm_dictionary, random_direction_counts (T03 8/18 at alpha 1, T2 3/15, T05 2/3 and T06
    1/3 at alpha 2), table110_alpha2, per_task_verdict (best rows at <=5/<=20 pts, coverage-standardised sensitivity). 25
    of 27 quoted review numbers reproduce; corrected: 'nothing reaches Hill 1.5 under 20 pts on R1/R3/R6/T11/T13/T14' (T14
    modal ban 1.78 at 17 pts; exp14 exposure arms) and two-sum alpha-2 avoidance 0.469 not 0.48 (denominator). On T03/T05
    the cheapest qualifying row is a norm-matched random direction and the structured ADD edit sits inside the random range.
    (3) Route landing (exp16): 7/7 readings, JS 17/17 to 1e-6, F_prompt 0.611 [0.06,1.17] / F_direct 0.744 [0.38,1.11]; without
    residue-gated T13 0.648 [-0.08,1.38] / 0.865 [0.68,1.05]; T13 not gated under catalogue-only avoidance (0.15) so no route
    class. (4) Llama hits with 'other' excluded: LADDER 6/13 (Poisson-binomial p 0.100), ASSOCIATE 7/13 (p 0.032); snap-back
    0.72/0.73/0.93. (5) 'Other' audit: 21 events, 226 programs (6 passing): 68 catalogue variant, 156 degenerate, 2 labeller
    miss, 0 novel (the one passing NOVEL-flagged program re-runs 60/60 hidden + 3/3 stress tests but is a textbook value binary
    search over a sort); judge kappa 0.77 (gpt-4.1-mini below the 5/6 control gate, gemini-2.5-flash weighted, deepseek tie-break),
    manual pass 73 programs incl. all 44 T13 merge-interval programs (29 coverage-array, 12 unsorted sweep, 3 other, all failing);
    residue-gated events exp13 T13, exp16 T13:a, Llama T06. (6) Rigor: defined-only hit rates, exposure SUBTRACT defined 4/33
    (hits 4/4 both arms), Table 82 per distinct row gain 0/11, residual 0/11, implied 8/11 (6 sham). (7) Section 3.10 replacement
    sentences and all corrections in corrections.json (0f -> this iteration's research artifact). (8) Rival predictors (14
    tasks): movability rho 0.86 vs can 0.16, clarity -0.07, FRLP 0.19, nonce -0.19, novelty 0.35. (9) Figures: captioned markers
    M1-M5 with the position caveat and a 2x2 composite in activation coordinates; at the label-independent g16 position BFS's
    nearest neighbour is IDA*, not BiBFS. AUDIT: audit/rederive.py (stdlib, 29 checks) and audit/rederive_extra.py (12 checks)
    with 0 mismatches; 7/7 placebos fail as required. Outputs: full/mini/preview_eval_out.json (exp_eval_sol_out; metadata.sections
    + 12 datasets), README.md, reproducibility.md; run with `uv sync --frozen && uv run eval.py --stages all` (~1.5 min, cached
    judges).
  workspace: >-
    /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_evaluation_3
  output_files:
  - eval.py
  - full_eval_out.json
  - mini_eval_out.json
  - preview_eval_out.json
  - reproducibility.md
- iteration: 4
  name: gen_art_experiment_19
  type: experiment
  title: Is plan noise the cheapest route to diverse code?
  summary: >-
    Experiment (iteration 4, Step 1 / Claim 1): is fresh per-sample plan noise (PN: one isotropic unit direction per sample,
    displacement-targeted at the task-spec positions of blocks 12-23 during prefill, alpha 0.5/1/2/4 ban units) the cheapest
    knob for CORRECT algorithmic diversity in Qwen3-8B (FP8 W8A8 on a 16 GB RTX 2000 Ada, thinking off, exact CRN)? Priced
    against temperature 1.3/1.6, top-k 10, nonce ban, novelty instruction, semantic seed (T1/T2), reused iteration-3 signature
    vetoes, and (sensitivity) min-p 0.1 at T1.6/T2.0 and a verbalized-sampling prompt. Statistic: correct-only Hill-1 rarefied
    at depth 25 on each knob's randomisation hull (H5 at <=5 pass points, P15, P20), 2,000-replicate bootstraps with best-setting
    selection inside replicates. 10,100 labelled programs, N=50 in all 202 cells (E6+R2 up to 17 arms; 8 non-movable bench
    tasks x 11 arms); no cell dropped. RESULT: pre-registered C1 = PARTIAL (count1 2/6, count2 4/6, D_bar -0.22, 95% CI [-0.89,
    0.30]); every sensitivity s1-s8 also PARTIAL. PN wins T03 (H5 2.72 vs novelty 1.96, P=1.00) and T10 (2.09 vs iterated
    veto 1.96, P=0.91), ties T05/T1, loses T06 (iterated veto 2.73 vs 1.00) and T2 (semantic seed 1.93 vs 1.35). Temperature,
    top-k 10 and the nonce ban buy no correct algorithmic diversity (H5<=1.09); min-p <=1.17. Temperature changes code but
    almost never the algorithm (T1: 88% code flips, 2% label flips); PN at alpha 2 flips the label in 50-60% of slots on T03/T10/T2;
    breakage at alpha 4 (alpha 2 on T2). R2 (held out) and 7 of 8 non-movable tasks barely move under PN. 81% of verbalized-sampling
    programs are run-time random dispatchers (labels trace-dependent). Engine check REPRODUCED (exp17 screen rows bit-exact,
    per-slot agreement 1.00). Novelty audit: 12 correct 'other' programs, all labeller misses, 0 novel. Label validity: agreement
    1.00 except T03 (0.80; D_t robust). Independent re-derivation 12/12 match; full-rule placebo 0/100 CONFIRMED; PN->TWIN
    placebo D_t<=0; hash chain intact (commit before Stage 1). Files: results/c1.json (decision + sensitivities + class CIs),
    results/prices.json, results/knob_rows.jsonl (merge-ready per (task, arm) Step-0 Hill rows), data/samples.jsonl (per-sample
    rows with code, label, pass, seeds, displacement), results/* descriptive files (alpha_sweep, flips, ideas_phrasings, plain_vs_twin,
    nonmovable, forecast_score, vs_dispatch), audit/*, figures/fig1-6, method_out.json (exp_gen_sol_out). OpenRouter spend
    USD 0.23. Caveats: FP8 not bf16 (device table); 6 decisive tasks; reused vetoes from another engine; the counts part of
    the rule alone is not selective under arm shuffles (8/100) - the CI criterion is.
  workspace: >-
    /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_experiment_19
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 4
  name: gen_art_experiment_20
  type: experiment
  title: Where noise must enter to change the model's algorithm
  summary: |-
    Experiment (iteration 4, plan gen_plan_experiment_2_idx3) testing WHERE isotropic random noise must enter Qwen3-8B (rev b968826d, thinking off, T=1.0; FP8 W8A8 on a 16 GB RTX 2000 Ada per the frozen precision rule) to change which correct algorithm it writes. Six tasks (T03 kth smallest, T05 two sum, T06 find duplicate, T10 connected components, T1 grid path, T2 weighted shortest path); one fresh random direction and one token-uniform stream per CRN slot shared by every arm, so site contrasts are exact paired flips. Sites at matched per-position ban-unit dose (alpha 1/2/4, N=30 per cell; twin N=50): S0 task-spec states blocks 12-23, S1 read position, S2 condition sentence, S3 generated tokens 1-32 (teacher-forced shadow rows), S4 task spec blocks 0-11, S5 task spec blocks 24-35; plus energy-matched S1E/S2E, S0 at alpha 8 (N=50), and a T1 TOP5 plan push. 4,510 programs; pre-registered (hash-chained commits #0-#4).
    RESULTS. C1-site = PARTIAL under the frozen rule: S0 has the best randomisation-hull price H5 (correct-only rarefied Hill within 0.05 pass cost) on 3/6 tasks (T03 2.61, T1 1.29, T2 1.66; raw p=0.062 vs Bin(6,1/6)); S3 wins T05/T06, S4 wins T10 (S4 ban units are only 4.5-7.2% of the residual norm vs 12.7-18.3% for S0: dose-convention confound). All per-task margins are bootstrap close calls (P(S0 argmax) 0.31-0.67; T2 0.97). S1 and S2 never change the algorithm (0/526 and 0/527 correct off-default programs at alpha 1-4), S5 nearly inert (6/521) even though S1 produces the same downstream displacement at R as S0; at matched displacement the S0 indicator stays +2.15 logit [1.79, 2.51] (Mantel-Haenszel OR 5.72 [3.94, 8.30]; shuffled-label placebo fails). Reading: the idea is chosen in the task-specification states at early-to-middle blocks; read-out, condition and late sites are inert; blocks 12-23 specifically is not supported over 0-11. Alpha 8 erases the task (pass 0.00 on all six). Novelty audit: 1 correct 'other' program (T06 nums.count brute force; judges DEGENERATE, manual CATALOGUE VARIANT), 0 novel among 3,555 correct programs (rule-of-three 0.08%). C3d: the TOP5 plan push never leaves BFS (avoidance 0.00 at alpha 1-2, 0 correct at alpha 4); landing test not computable. Engine check reproduces the exp17 screen byte for byte (50/50 on T03 and T2). Alpha-4 compositions differ from sibling exp19's PN_a4 rows (do not use them as the Step-1 knob table).
    FILES. method_out.json (+ full/mini/preview; datasets site_grid, boundary_alpha8, top5_plan, engine_check; all analyses in metadata); results/*.json (c1_site, hull, cells, failure_modes, paired_flips, transmission, pooled_model, boundary, c3d, novelty_audit, engine_check, overlap_check, units_summary, rederive, rederive_headlines, unit tests, deviations D1-D16); data/samples.jsonl (every row with labels, displacement logs); units/, directions/ (u_top5, plan-site geometry); figures fig1-fig7; README.md; reproducibility.md. Caveats: FP8 only, one model, memorised tasks, N=30 cannot rank two live sites; site-specific perturbation, not a plan representation.
  workspace: >-
    /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_experiment_20
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 4
  name: gen_art_experiment_21
  type: experiment
  title: 'Same seed: temperature vs plan nudges'
  summary: >-
    Seed-coupled 2x2 on Qwen3-8B (exp17's HF FP8 W8A8 engine on the screen's 16 GB RTX 2000 Ada; thinking off) for T2 weighted
    shortest path (default Dijkstra), T1 grid path (BFS) and T03 k-th smallest (full sort), 20 token seeds per task, each
    keeping one noise stream across every condition (inverse-CDF CRN). Results: temperature (0.3/0.7/1.0/1.3, top-k 10) changed
    the algorithm in 0/20 seeds on all three tasks, and in 0/20 on T2 with thinking on (vLLM 0.11, Gumbel-max per-request
    seeds, 100/100 traces completed; repeat noise floor 0). Plan noise (6 isotropic directions at the task-spec states of
    blocks 12-23, prefill only, alpha 1, T 1.0) changed it in 17.25/20 seeds on T2 (20-subset mean), 4.55 on T03 and 2.5 on
    T1. Pooled paired seed contrast (T2+T03): mean x_s 0.545 [0.41, 0.67], sign-flip p = 1.0e-5 (Holm entry C1-seed); within-seed
    permutation test p = 0.005. Phrasings per idea grow with T (pooled log-PPI slope 0.64-0.81, CIs exclude 0; driven by T1).
    Verdict (pre-registered, commit #0 before any decisive sample): PARTIAL, H-PN fails on T03 (4.55 < 5) where the protocol-v4
    unit is 0.77x the screen's; the Gumbel-max replicate gives T03 5.8. Engine check reproduces the screen byte for byte (200/200).
    Optional arms: min-p T 2.0 moves 1/20 seeds (T2, T03); thinking-on PN moves the first approach in <=1/10 seeds; T1 thinking
    on (10 seeds) C_T 0. Novelty audit: 0 novel. Independent re-derivation: 0 mismatches in 33 checks. Files: results/c1seed.json
    (all counts, tests, verdict), results/phrasing.json, results/thinking.json, results/table_1ac.json, data/samples.jsonl
    (3,140 programs), data/raw_thinking.jsonl, figures/F1-F5, method_out.json (datasets seed_coupled_off/on, engine_check,
    fp8_crosscheck).
  workspace: >-
    /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_experiment_21
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 4
  name: gen_art_experiment_22
  type: experiment
  title: Where the model picks its coding algorithm
  summary: |-
    Qwen3-8B (pinned revision, FP8 W8A8 on a 16 GB RTX 2000 Ada, thinking off, T = 1). The test asks whether a plan subspace P_t at the task-specification positions explains which random pushes change the algorithm the model writes. P_t is the span of the centroid differences of 30 forced 'Implement X' paraphrases per algorithm, plus a name-masked twin, at blocks 12-35, on 15 coding tasks. All 4,144 prompts were used. Every predictor was sha256-committed before sampling.

    Scale: 13,500 CRN-coupled programs, labelled by runtime tracer + AST, with a blind judge only on disagreement; 2.51 GPU-hours; USD 0.20 of OpenRouter. The engine reproduced the iteration-3 screen slot for slot (180/180 identical programs).

    The plan subspace is reliable: split-half principal cosine 0.89-0.97 vs 0.02 for random subspaces.

    C2a (primary), DISCONFIRMED. The projection share pi(u) does not rank which of 40 fresh random directions move the algorithm: rho < 0.2 on 6/6 movable tasks; pooled within-task rho 0.03 [-0.03, 0.09]. The masked variant and structured controls also fail. Which directions move is itself highly reproducible (template split-half rho 0.76-0.90), so the null is not noise. Exploratory: the signed progress of the realised displacement toward the runner-up centroid correlates up to 0.57 with the effect.

    Escape fractions (confirmed at N = 30), at alpha 1 / alpha 2:
    - T03: 0.30 / 0.63 (quickselect, size-k heap);
    - T10: 0.38 / 0.73 (DFS);
    - T2: 0.18 / 0.20 (Bellman-Ford);
    - T05: 0 / 0.13 (brute force);
    - T1: 0.05 / 0.13 (DFS);
    - T06 and nine other tasks, including the held-out R2: 0.
    Landings match the iteration-3 screen.

    Decomposition (20 confirmed directions): removing the P_t component (u_perp) or clamping the realised P_t displacement keeps the effect (pooled median R = 1.00 for both), so P_t is not needed. The amplified P_t component alone also escapes for 9 of 20 directions: generic sensitivity.

    C2c, DISCONFIRMED by its rule (5/6 tasks indistinguishable from a matched random push), with T10 as a clean exception. At half the distance to the runner-up centroid (0.15 ban units), T10 gives 48% correct DFS vs 0% for the matched random push (24/0 CRN flips, McNemar p = 1.2e-7). The empirical crossing is s = 0.59 vs the predicted 0.5; T03 crosses at 0.85.

    C2b fails: pooled rho 0.27. C3b (descriptive): push landings forecast ban landings best (log score -0.76 vs ASSOCIATE -3.46). Movability tracks ban avoidance across 14 tasks (rho 0.86).

    Novelty audit: 0 novel algorithms among 10,651 correct push programs.

    Files provided:
    - method_out.json (exp_gen_sol_out), with datasets c2a_population, escape_9task, decomposition, targeted and c3b_events;
    - results/*.json for every analysis;
    - figures fig1-fig9;
    - predictions/c2_commit.json and the commitments.log hash chain;
    - data/samples_raw.jsonl and data/labels.jsonl;
    - two independent audits with placebos (0 mismatches);
    - reproducibility.md.
  workspace: >-
    /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_experiment_22
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 4
  name: gen_art_experiment_23
  type: experiment
  title: Predicting which coding bans a new AI model obeys
  summary: |-
    Held-out-family test of Claim 3a on google/gemma-3-4b-it (bf16, RTX 2000 Ada 16 GB): does a ban-free random-push screen (8 fixed isotropic directions x alpha {1,2}, displacement-targeted edits of task-spec states in blocks 11-22, outlier-excluded unit transferred from Qwen3-8B; escape = off-default share - p0 >= 0.20 with pass >= 0.8x twin, confirmed at N=30 by exact binomial) predict which modal coding bans the model obeys? Predictions (E_t, MOVABLE, rivals, 4 landing forecasts) and the frozen analysis were sha256 hash-chained before any ban prompt (commitments.log; grep audit 0 hits). 15 tasks (12 bench + T1 grid path, T2 weighted shortest path, R2), 10,730 labelled programs (8,030 ban-free; 2,700 ban rows incl. the 1,500 primary modal-ban programs), frozen labellers.
    RESULTS: movable = T1,T2,T04,T05,T10,T11; observed obey (A_t>=0.5) = T1,T2,T03,T05. C3a INCONCLUSIVE: BA 0.739 [0.40,0.95], Fisher p 0.235 (table [[3,3],[1,8]]; Bonferroni 0.71), Spearman rho 0.537 (one-sided perm p 0.025), Kendall 0.47; all sensitivities INCONCLUSIVE (w/o T1/T2: BA 0.61, rho 0.31). Rival 'novelty instruction off-default share' predicts better (rho 0.77; delta rho -0.24 [-0.82,0.23]). C3b INCONCLUSIVE: push-landing log score -0.11 (4/4 top-1) vs association -1.77, but only 2 disagreeing events (<3). C1 (descriptive): plan noise raises correct-only Hill-1 at <=5 pass points (T2 1.0->1.62) where temperature 1.3/1.6 does not. Novelty audit: 0 novel among 34 correct 'other'. KEY CAVEAT (post hoc, results/posthoc_t2_relabel.json): the frozen T2 labeller reads array-based Dijkstra as Bellman-Ford; second-judge relabel cuts T2 ban avoidance 0.96->0.11 (BA 0.667, rho 0.44; still INCONCLUSIVE). DEVIATION D3: Gemma's top-5 channels carry 99% of ||h||^2 (Qwen 40%), so the plan's unit erased the task; the outlier-excluded unit was adopted before commit #1 and matches the post-ban ban displacement (ratio 1.29).
    PROVIDES: method.py (pipeline driver) + src/; data/samples.jsonl (every row: label, pass, realised displacement), data/raw_*.jsonl (text+token ids); predictions/commit1.json, commit_preban.json, frozen analysis_c3.py; results/*.json (c3a, rivals, c3b, c1_prices, bans, escape, unit_sensitivity, qwen_ratio, screen, label/novelty audits, posthoc, rederive: 0 mismatches, placebos fail); figures fig1-fig6; method_out.json (datasets heldout_ban_samples, heldout_banfree_samples, heldout_task_events). OpenRouter USD 0.28; 1.28 GPU-h generation.
  workspace: >-
    /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_experiment_23
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 4
  name: gen_art_research_1
  type: research
  title: Checking our claims against published work
  summary: >-
    Dated (2026-10-21) positioning audit of the run's iteration-3 and iteration-4 claims. It provides two paste-ready tables,
    Table 92b and Table 92c, in research_report.md. Each claim is set against its nearest published finding with a verbatim
    quote, URL, section, arXiv version and venue evidence. 112 quotes from 74 references were checked: 101 VERIFIED on full
    text, 11 VERIFIED-ABSTRACT (OpenReview/NeurIPS records), 0 mismatches, and 112/112 re-matched by an independent live fetch_grep
    pass. Saturation search: 8 families and 25 queries on OpenAlex/Crossref, the arXiv API, Semantic Scholar and the ICLR
    2027 OpenReview pool, plus 28 general-web calls and forward citations of 6 neighbours. 1,933 hits gave 1,729 unique records,
    1,286 in the window and 63 scored on the O/I/C rubric: 44 adjacent, 19 irrelevant, 0 occupying. FLAG A (test-checked algorithm-level
    diversity under activation perturbation): NOT FIRED. The closest are STARS (test coverage, ICLR 2026), random embedding
    injection (math only; code is future work), NC-GRPO (RL rollouts) and ESamp (decoding). FLAG B (prompt-ban compliance
    predicted from perturbation sensitivity/steerability): NOT FIRED. The closest are a NeurIPS 2026 workshop probe of injection
    compliance (AUC 0.90), Heo et al. (ICLR 2025) and ASTEER. OPEN: C3a (movability forecasts ban compliance) and C3b (ban-landing
    forecast). PARTLY OCCUPIED: C1, where the contrast set lacks the text-level plan samplers (IFG, PlanSearch, 2606.10302
    Level-2, Gacha Decoding) and a decoding baseline matched to the departure from greedy (ICLR 2027 submission); C1-site
    (site comparisons exist for narratives and test coverage: Noise Steering, STARS App. B.3; 2606.10302 is text-level only);
    C2a (decodable prompt-state plans, plus a causal pre-generation response-length subspace in the ICLR 2027 submission 'Before
    the First Token'); C2 geometry (Manifold Steering; code steering toward target libraries/APIs); b2 (Sclar, Heo); b6 (activation
    noise for diversity is a saturated method). ADJACENT-ONLY: b1 (closest analogue: Yoon et al. 2026 fact-level favoured-candidate
    promotion), b3 (Qi et al. shallow alignment; AdapT), b4, b5/C3c (scope against FunSearch/AlphaEvolve), b7, and C1-seed
    (Gumbel counterfactual coupling is the precedent). Corrections: Manifold Steering is an ICML 2026 MI-workshop spotlight,
    not main track; IFG is an ICML 2025 EXAIT workshop poster; the Invisible Lottery is confirmed as an ICML 2026 main-conference
    poster (keep); Tang's 'implementation priors' is VERIFIED in Sec. 5.3 of the v1/v2 PDF; Di Cicco's AUC is 0.931 (v1),
    0.955 (v2) and 0.881 (v3, latest); 'self-decodable' appears only in Brewing v1; ICLR 2027 contemporaneity is two months
    and arXiv-only papers are exempt (the Reviewer Guide's 'September 16' conflicts with the Dates page's Sep 25). Contradicting
    evidence: temperature above 1 raises algorithmic diversity elsewhere (Lee et al., Findings EMNLP 2025); agents' H-creativity
    (2608.30047); FunSearch/AlphaEvolve; departure-matched decoding. Evidence files: evidence/quotes.jsonl, search_log.jsonl,
    saturation_candidates.jsonl, screening.jsonl, saturation_hits.jsonl, corrections.jsonl, qa_second_pass.jsonl.
  workspace: >-
    /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_4/gen_art/gen_art_research_1
  output_files:
  - research_out.json
  - reproducibility.md
- iteration: 5
  name: gen_art_evaluation_4
  type: evaluation
  title: Record fixes and frozen rival predictors
  summary: >-
    CPU-only Step 0 of iteration 5 (no model run). (1) RECORD CORRECTIONS: corrections.json holds 35 exact old_text -> new_text
    replacements (marked 'iteration-5 correction'). They are keyed to iteration-4 report locations (Tables 92c, 122, 123,
    139, 147, 157, 159, 160, 162, 163, 164; Sections 3.2.5, 4.2-4.11; closing paragraphs). Every value carries a provenance
    tag and a status against the record: 186 of 187 recorded values MATCH within tolerance, 1 is CORRECTED (signed progress
    '22 of 35' is 22 of 24 cells), 15 are NEW, 4 are CARRIED. Key re-derived results: (0a) the Gemma held-out verdict is INCONCLUSIVE
    under catalogue-only avoidance (BA 0.739, Fisher p 0.235, Spearman 0.537) and DISCONFIRMED under the default-drop sensitivity
    (BA 0.568, p 1.0, rho 0.391). Grid is the only NO-DEFAULT task (twin BFS 25/DFS 25); find duplicate has 38 failing 'other'
    programs. Without T1/T2: BA 0.614, rho 0.313 (one-sided permutation p 0.144). (0b) Site: S1 0/526, S2 0/527, S5 6/521;
    energy-matched S1E excess +0.23 (find duplicate) and +0.18 (connected components); generated-token noise beats the plan
    site 12:0 (McNemar p 0.000488). (0c) Matched-event log scores: push -0.761 vs association -3.115 on the 3 push-defined
    events; -1.366 vs -3.462 over all 5 with uniform fill (the review's -1.37 is this value; it coincides with the screen-push
    replication cell -1.369). (0d) PNPLAIN, hull deviation, Llama block (CARRIED), dose units, GPU hours. (0e) Per-direction
    distributions (624 cells), split-half values with movers, signed-progress closure, Table 147 depths. (0f) All 6 Table
    92c quotes RE-VERIFIED live on 2026-10-21. (0g) Exposure-class rule. (0h) Table 76 cross-reference: the thinking-on arm
    used top_k off. (2) RIVALS (0i): rivals.json + rivals.json.sha256 + commitments.log hash chain (genesis sha256('iter5_dir1'))
    freeze eight ban-free task predictors for the 15 Qwen3-8B tasks before any target read: R1 opening margin, R2 forced can
    rate, R3 association clarity, R4 novelty-instruction excess, R5 human Mercury diversity (gate-lite, judge audit kappa
    0.97), R6 runtime merit gap, R7 twin modal share, R8 ban-unit ratio, plus covariate K (catalogue size). The A1-transferable
    rivals (R1, R4, R6, R7, K) are frozen for Step-2 confirmation on new tasks. Descriptive scores vs E_pool (screen data;
    10 of 15 tasks at 0; every Holm p = 1.0): K +0.46, R5 +0.39, R4 +0.38, R2 +0.30, R8 +0.21, R6 +0.14, R7 -0.16, R3 -0.16,
    R1 -0.33. A post-freeze dose check finds E_pool does not track ban unit / residual norm (rho -0.06, AUC 0.49). (3) AUDIT:
    audit/rederive.py (stdlib, no shared code) passes 195 checks with 0 failures, and its 4 placebos fail as required. FILES:
    eval_out.json (exp_eval_sol_out; full/mini/preview), results/{corrections_metrics,rival_scores,input_hashes}.json, tables/*.csv
    (19 tables), figures/fig_rivals, rivals/{r5_human_raw,r6_merit_raw}.json, README.md, reproducibility.md. Dependencies
    are read as sibling folders <AII_DEPS_ROOT>/<artifact_id>. OpenRouter spend USD 0.021.
  workspace: >-
    /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_5/gen_art/gen_art_evaluation_4
  output_files:
  - eval.py
  - full_eval_out.json
  - mini_eval_out.json
  - preview_eval_out.json
  - reproducibility.md
- iteration: 5
  name: gen_art_experiment_24
  type: experiment
  title: Transplanting base-model plan states into Qwen3-8B
  summary: >-
    Iteration-5 Step-1 experiment on Qwen/Qwen3-8B (rev b968826d) and Qwen/Qwen3-8B-Base (rev 49e3418f): Claim B (primary,
    causal), Claim D, the reverse interchange, site controls, plan-site geometry, a descriptive Claim A screen check and a
    novelty audit. Setup: thinking off, bf16 on an RTX 4090, 15 tasks (13 bench tasks + T1 grid path + T2 weighted shortest
    path), exact common-random-number coupling (B = 20; T(0) equals the twin 20/20). Base repertoire (COMMIT #1): 5 BASE-DIVERSE
    tasks (T03, T2, T10, T1, T14; beta 0.36-0.66), 7 INTERMEDIATE, 3 BASE-COLLAPSED; the instruct twin's default share is
    0.96-1.0. Transplant T(lambda): the instruct prefill task-spec states at blocks 12-23 are set to h_instr + lambda(h_base
    - h_instr). Frozen-rule verdict: Claim B DISCONFIRMED (PASS 1/5, T14; condition (iii) fails on 4). T14: T(1) produces
    the base runner-up (heap) in 21/49 correct S2 programs vs 0/39 for the twin, with pass 0.78 -> 0.98. It beats norm-matched
    random (MR), cross-task base shift (XT) and pass-matched random (MRP) at Holm p <= 7e-4; in the outcome-blind N=100 extension
    the discordant pairs are 44:0, 35:3 and 49:0. T03: matched-norm random beats the transplant (21/50 vs 3/50 off-default;
    McNemar 2:20, two-sided p = 1.2e-4). T10, T2, T1: no reopening at an intact pass rate; lambda >= 0.5 breaks T2 and T1.
    Site controls: EARLY (blocks 0-11) moves T03 (15/50) and T10 (14/50) more than the main band; READ (read position, ||D||/||h||
    ~ 1.0-1.1) breaks the output without moving algorithms; LATE is inert. Claim D DISCONFIRMED: a push along unit(D) never
    escapes; the isotropic push escapes T03 at alpha 2. Reverse (instruct states into the base model): raises the base model's
    correct-program counts and its default share among attempts on all 4 tasks, but meets the committed prediction only on
    T1. Claim A screen check (descriptive): beta_t vs the iteration-4 escape fraction gives Spearman 0.78 (permutation p ~
    2e-4); r_t equals the push top-1 landing on 5/5 movable tasks. D is mostly generic: cross-task cosine 0.76-0.88, split-half
    cosine 0.96-1.0, and 71% of hooked cells exceed 4 ban-free units at lambda = 1. Geometry: the transplanted block-27 state
    stays about 88-89% of the way toward the base twin, while R moves only 18-31%. Novelty: 48 correct non-catalogue programs,
    0 novel after manual adjudication (the judges over-called 14). Re-derivations: 56/56 (audit/rederive.py) and 34/34 headline
    checks (audit/rederive_headlines.py) match; the placebos fail as required. FILES: method_out.json (exp_gen_sol_out; datasets
    base_repertoire, transplant_selection, transplant_confirmation, desharpen, reverse, engine_check; one example per CRN
    slot with predict_<arm> = 'label|pass'; metadata = every analysis, commit and deviation); data/samples.jsonl (14,280 labelled
    programs with code); results/*.json (claim_b, confirmation incl. power_extension_N100, selection, desharpen, reverse,
    screen_check, d_norms, geometry, novelty_audit, engine_check, timing, costs; knob_rows.jsonl; summary.md); predictions/commit0-2.json
    + commit3_extension.json (hash chain in commitments.log); figures/fig1-6; cache/states/ (exact bf16 prefill states of
    both models, 36 blocks x (S + R) for 75 prompts; kept on the run volume, not published). Deviations: results/deviations.jsonl
    (10).
  workspace: >-
    /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_5/gen_art/gen_art_experiment_24
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 5
  name: gen_art_experiment_25
  type: experiment
  title: Does the base model predict which coding tasks can be nudged?
  summary: >-
    Panel A of iteration-5 Step 2 (Claims A1/A2) on Qwen3-8B (thinking off) and Qwen3-8B-Base, bf16 on one RTX 4090, every
    forecast sha256-committed before its unit's first push (guard verified for all 23 units/tasks). Nine new LeetCode-derived
    units were built with hidden tests, references, mutants and runtime+AST labellers gated against blind two-family LLM judges
    (kappa>=0.8, runtime-vs-adjudicated>=0.9): A1-A5, A7 gated; A6 (islands) GATE_FAIL after one revision; reserves A8/A9
    run as a logged extension. Per unit: instruct twin N=50 (CRN), base N=100 on identical chat-templated ids (+ plain completion
    N=50), rivals, then 8 fixed isotropic directions x alpha {1,2} with two-stage binomial confirmation, plan noise (alpha
    1, 2) and T1.3; Extra arm A re-measured the 15 existing tasks under the same ban-free unit. RESULTS. A1 not supported:
    primary n=6 Spearman rho(beta,E)=-0.03 (exact p=0.56); with A8/A9 rho=-0.33; base-diverse units A4 (beta 0.81), A5, A8,
    A9 never escape; trivial rivals track E better (merit-runtime rho=-0.88, twin modal share rho=-0.70). A2 supported: base
    runner-up r_u equals the push landing on 3/3 movable units (A1, A3, A7; Poisson-binomial p=0.019); base log score beats
    proximity and (after a POST HOC fix of a mapping bug that had made the committed association rival uniform) association
    on all 3 events (margins 0.99 / 0.85 nats); no push program lands outside the base repertoire. Descriptive half+screen
    (6 new units + 15 existing tasks with Step 1's committed beta): rho=0.54 (p=0.0065), driven by 13/15 immovable existing
    tasks. Extra arm A: only T03 (E 0.25) and T10 (E 0.125) escape; T05/T06/T1/T2 lose their screen 'movable' verdict. Engine
    check: twins reproduce the FP8 screen, pushed cells show bf16 precision sensitivity. Novelty audit: 0 novel algorithms
    among 6,854 correct programs. Two stdlib re-derivations: 0 mismatches; placebos fail. FILES: method_out.json (exp_gen_sol_out:
    panelA_units, panelA_cells, existing_remeasure + all analyses in metadata), pooled_inputs.json (schema iter5_panel_v1,
    raw per-unit ingredients incl. per-cell escape tables, rivals, base compositions, commitments) for next round's pooling
    with panel B, results/ (a1*, a2*, a2_assoc_corrected*, half_screen, extra_arm_a, knob_rows, repertoire_check, engine_check,
    units_gate, summary.md), predictions/ + commitments.log (hash chain), data/samples.jsonl (8,390 labelled programs), newbench/
    (unit specs, tests, labellers), figures/ fig1-fig5. Deviations are listed in results/deviations.jsonl.
  workspace: >-
    /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_5/gen_art/gen_art_experiment_25
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 5
  name: gen_art_experiment_26
  type: experiment
  title: Base-model variety vs nudgeable coding tasks (panel B)
  summary: |-
    Panel B (of two) of the iteration-5 confirmation of Claims A1/A2 on Qwen3-8B (instruct, b968826d) vs Qwen3-8B-Base (49e3418f), bf16 HF engine on one RTX 4090, identical chat-templated token ids for both models, exp8 inverse-CDF CRN sampler, thinking off. Seven NEW coding units (B1 missing number, B2 single number, B3 MST weight, B4 integer sqrt, B5 all subsets, B6 valid anagram, B7 count inversions) were built with banned-word-free wording, two-oracle hidden tests, 3-6 test-passing references, mutants, excluded brute-force methods and gated runtime+AST labellers (all 7 gated; B3/B4/B5/B7 after one revision round; base-label audits 0.93-1.0). Per unit: twin N=50 fixes the default; base repertoire N=200 (raised from 100 because the base is 46-61% off-task under the chat template) + plain N=50; beta_u (correct-only off-default share), r_u, rivals (R_modal, R_margin, R_merit, R_novel, K) and BASE/ASSOC/PROX forecasts were sha256-hash-chained BEFORE any push; then 8 isotropic directions x alpha 1,2 (task-spec positions, blocks 12-23, ban-free unit r_Q*||h||), two-stage exact-binomial confirmation, plan noise and T1.3. Extra arm: 8 disguised variants (T03,T10,T05,T06,T04,T08,T14,R1) each with a paired parent re-measure on the same seeds. 14,600 programs, 1.74 GPU-hours, USD 0.19 judges.
    RESULTS (descriptive, n=7): A1 Spearman rho(beta_u,E_u)=0.21, exact one-sided p=0.33 -- not supported within panel B; movable B2 (E .44), B7 (.31), B3 (.13), B4 (.13); immovable B1 (beta .06), B5 (.37), B6 (.81, the clearest disconfirming case). All units were base-diverse (beta>=0.05), so 'collapsed->immovable' is untested. Secondary rho(beta,PN excess)=0.82 (p=0.017). Rivals: R_merit length/runtime rho 0.58/0.54, R_margin 0.21, R_modal 0.11, R_novel -0.03 (all CIs wide). A2: r_u matched the push landing in 3/4 events (chance 1.2, Poisson-binomial p=0.081); BASE beat ASSOC by +0.68 nats/event and PROX by +0.13. Extended descriptive views: new units+parents rho 0.43 (p=0.055, n=15), cluster-preserving all-units rho 0.54 (p=0.015, n=22); within-parent: only T03 and T10 move (T10 with a default shift), other pairs E=0. Screen view (Step-1 beta vs iteration-4 E, cross-engine): rho 0.79 on 15 tasks. Validity: GPU tests pass; engine check T03 within null, T2 bf16-sensitive; novelty audit 0 novel algorithms in 10,366 correct programs; independent re-derivations 0 mismatches with placebos failing; 0 push rows before their commit.
    PROVIDES: pooled_inputs.json (schema iter5_panel_v1, 23 records: 7 new units, 8 parents, 8 variants) for the pooled A+B test; method_out.json (panelB_units, panelB_cells); predictions/ + commitments.log; results/ (a1_panel, a2_panel, a1_extended, variants, rivals, repertoire_check, engine_check, novelty_audit, rederive*, deviations); units/ (tests, references, gates); figures F1-F6; reusable code (unit builder, sandbox tracer, CRN engine, judges). 20 deviations are logged in results/deviations.json (README adds two notes).
  workspace: >-
    /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_5/gen_art/gen_art_experiment_26
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 5
  name: gen_art_experiment_27
  type: experiment
  title: Plan noise vs plan-first prompting for code
  summary: >-
    Iteration-5 experiment on Qwen3-8B (rev b968826d) with two claims. CLAIM F (literal cell): shortest-path task T2, thinking
    on, top-k 10, same token seed, T in {0.3,0.7,1.0,1.3} plus a T0.7 repeat, on vLLM 0.11 with Qwen3-8B-FP8 and exp21's 20
    seeds (data/literal_raw.jsonl, results/literal_cell.json). Result: C_T = 0/20 seeds change the final-code algorithm (Clopper-Pearson
    one-sided 95% UB 0.139), first approach never changes, 100/100 completed, all heap Dijkstra; repeat noise floor 4/20 byte-identical
    traces but 20/20 label agreement; labels agree 100/100 with exp21's top-p-1 run (median common prefix only 34 tokens).
    CLAIM C: per-sample plan noise (PN; isotropic direction at task-spec positions of blocks 12-23, prefill only, ban-free
    unit ||h||*r_Q, alpha 1/2) vs frame-matched text-level plan samplers (IFG (1.3,0.7) and (0.73,0.60); PlanSearch-lite;
    enumerate-and-pick EAP; base-model-written intent BINT) and departure-matched decoding (DMD: temperature on tokens 1-32
    bisected to PN's per-token KL, on-policy checked; predictions/dmd_temperatures.json), all in one HF bf16 engine with exact
    inverse-CDF CRN; 7,060 labelled rows (N 50 on D5 = T03,T10,T2,T05,T1; N 30 on ND10 after restoring dropped cells). Full-simplex
    randomisation-hull prices (H5/P15/P20) with 2,000-replicate slot bootstraps (results/claim_c.json, prices.json, knob_table.json).
    Committed rule verdict: DISCONFIRMED - PN >= best text sampler on 1/5 decisive tasks (T03: PN 1.98 vs EAP 1.83, P=0.58
    UNRESOLVED); BINT beats PN on T10/T2/T05 (2.53/1.45/1.61 vs 1.09/1.18/1.17); D_bar -0.40 [-0.70,-0.24]; only with the
    multi-stage left-padded samplers removed (IFG only) would PN win 4/5. PN vs DMD at matched KL: at alpha 2 PN moves the
    algorithm far more (pooled discordant 19 vs 3, exact p=0.0009), not at alpha 1 (4 vs 3). PN plain vs twin: no significant
    paired difference. T1.3/top-k 10 buy no diversity. Engine check vs exp19 FP8 rows: PRECISION-SENSITIVE (twin cells 0.98-1.00,
    pushed cells 0.74-0.86 per-slot agreement). Audits: novelty 0 novel of 12 correct 'other' (10 labeller misses); style
    re-gate flags only T14; lexicon audit 19/19. Independent re-derivation (audit/rederive.py) reproduces C_T, noise floor,
    all McNemar counts and the verdict (hull H5 within 0.08; win count 2 vs 1, still DISCONFIRMED); PN-as-TWIN placebo gives
    D<=0; arm-shuffle placebo centres at 1.6 wins. Pre-registration: sha256 chain commit0F/commit0C/commit1/amend1/amend3,
    deviations in results/deviations.jsonl (bf16 engine, one pilot wording revision, drop order then restoration, A1 incomplete-cell
    rule). OpenRouter spend USD 0.12.
  workspace: >-
    /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_5/gen_art/gen_art_experiment_27
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 5
  name: gen_art_experiment_28
  type: experiment
  title: Does Gemma's base model predict nudge effects?
  summary: >-
    Claim E (secondary): a second-family REPLICATION (not a held-out confirmation; Gemma's iteration-4 push outcomes were
    seen) of the narrowed-repertoire account on google/gemma-3-4b-pt vs google/gemma-3-4b-it (bf16, one NVIDIA L4, 12,290
    programs, 2.16 GPU-hours, USD 0.39 judges). Design: fresh it twin (N=50/task) fixes each task's default D_u. pt repertoire
    on the same token ids: chat template N=100 plus plain completion N=50, pooled because the pre-registered chat validity
    gate failed. pt-chat is 91% unusable output (10 correct programs); every unit falls under the LOW_CORRECT rule, so beta
    comes from valid attempts. beta_u, r_u and q_base were hash-committed before any push sample. Then a never-run push population
    (16 isotropic directions, seeds 52001-52016, x alpha 1/2 x N=10, binomial confirmation at N=30; blocks 11-22 task-spec
    positions; outlier-excluded ban-free unit). Then a pt->it transplant of task-spec states (lambda=1) on 7 base-diverse
    tasks against matched-random (RND), cross-task (XT) and read-position (RP) controls on the same CRN slots, plus 3 base-collapsed
    controls. RESULTS. E-A2 PASS: the pt runner-up equals the push landing in 5/7 events (hit rate 0.71 vs mean chance 0.30,
    exact Poisson-binomial p=0.025); the pt-composition forecast beats iteration 4's association forecast by 1.50 nats/event
    (exact Wilcoxon p=0.023) and AST proximity by 0.51 nats. E-A1 INCONCLUSIVE: Spearman rho(beta,E_u)=0.42, one-sided permutation
    p=0.060, n=15; 2/3 base-collapsed tasks immovable; beta is ahead of no rival (twin modal share rho=0.67, novelty instruction
    rho=0.64). Descriptively 6/7 base-diverse tasks are movable vs 2/8 others (Fisher p=0.03, not registered). Transplant:
    every program stays valid; T04 moves naive->builtin 40/50 and R6 linear scan->binary search 39/50 (both = pt runner-up).
    The other 5 base-diverse tasks stay at default (support 2/7). The two moved tasks are exactly those whose it twin already
    writes the runner-up 8-12%. RND/XT at matched non-massive norm break programs (pass 0-0.5), so the norm-confound rule
    applies; RP and collapsed controls are inert. Novelty audit: 0 novel among 56 correct 'other' programs (rule-of-three
    bound 0.054). Iteration-4 appendix: the re-gated T2 rule (array Dijkstra) changes 258 iteration-4 T2 labels (E_t 0.25->0.125,
    ban compliance 0.96->0.34). Integrity: commit #0, #1 and #1b hash chain verifies and precedes the first engine-check,
    push and transplant rows. Two independent re-derivations: 0 mismatches; every headline value re-derived with placebos
    failing as required. Main caveats: low-power n=15; pt labels weak (judge agreement 0.64); controls broke validity; style
    re-gate failed on broken pt code (it programs 30/30). Deviations D1-D17 are in results/deviations.json. Files: README.md,
    reproducibility.md, results/*.json, figures/fig1-6, data/samples.jsonl, method_out.json (exp_gen_sol_out; 7 datasets).
    cache/ (1.4 GB activation tensors) is kept on the run volume only.
  workspace: >-
    /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_5/gen_art/gen_art_experiment_28
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 5
  name: gen_art_research_2
  type: research
  title: Has prior work restored base-model variety?
  summary: >-
    Dated (2026-10-21) positioning audit for iteration-5 Claims A-D, extending art_kjrCpQnPaniY (Tables 92b/92c; its 112 quotes
    cited by row id, not re-verified). Provides paste-ready Table 92d (55 rows: 92d-A0/A1/A2/B1/B2/C/E/G; design facts only)
    with 137 verbatim, versioned quotes from 93 references (111 VERIFIED full text, 21 VERIFIED-ABSTRACT ICLR 2027 submissions,
    5 VERIFIED-BLOG; 0 mismatches; 137/137 re-matched by a live fetch_grep pass). Saturation search under a protocol frozen
    before the first call: 9 families/25 strings on OpenAlex/Crossref, arXiv API, Semantic Scholar, OpenReview ICLR 2027 +
    grey literature, forward citations of 8 seeds, round 2 (6 queries), round 3 (forward + backward snowballing); 169 calls,
    4,508 raw hits, 3,506 unique, 49 scored; stop rule met after round 3. FLAG A (base states written into the tuned model
    + diversity outcome): NOT FIRED, narrowly — the method is published (cross-patching of base upstream states into a descendant:
    Zhou (Y.) arXiv 2605.07284, rubric 2.5; Oozeer et al. ICML 2025; Du et al. COLM 2025; Prakash et al. ICLR 2024 CMAP) and
    the goal is published at weight level (Selective Layer Restoration 2602.06665; aligned/base FrankenMerging 2610.22999;
    layer interpolation in ICLR 2027 'Locked at the Entrance'; WiSE-FT; Hindsight Merging +20-50% pass@10 on code) and token
    level (BACo ICML 2026, conformative decoding, Switch Generation). B1 may not say 'first' for the transplant; may claim
    the combination (prefill task-spec states, test-checked algorithm choice on code, matched-random and cross-task controls).
    FLAG B: PARTLY FIRED — training-time per-prompt forecasts from the frozen base exist (Zhou (T.) 2607.20543; Duan 2610.04978,
    where base pass rate/likelihood explain only 0.30/0.24 of explainable variance; Lookahead ICLR 2027; Reasoning Boundary
    Paradox NeurIPS 2026); inference-time movability (A1) and landing identity (A2) remain open; A2 has only stylised/retrospective
    support (Verbalized Sampling power-sharpening; URIAL top-5; 'Same Candidates' 92.9% within base top-16; seed-distribution
    collapse). FLAG C: PARTLY FIRED — Lee et al. (Findings EMNLP 2025) compare DeepSeek-Coder-6.7B Base vs Instruct (test-checked,
    LLM-judge clusters) and find a MIXED direction; 'first base-vs-tuned algorithm-level comparison' struck; premise row reads
    'contradicting in part'. B2/D: PASTA (2605.30526) already ablates an aligned-minus-base residual direction during decoding
    with orthogonal random-direction controls (style outcome) -> frame as replication in a new setting. C: base-aligned collaboration
    is an occupied lane; base-intent arm = sentence-granularity instance. Reviewer baselines: Qwen3-8B Base/Instruct weight
    interpolation, SLR/FrankenMerging at B1 block ranges, BACo token routing, EFT/proxy-tuning, template-controlled contrasts
    (Nakamura 2026). 27 corrections (e.g., 2506.17871 is v4/TMLR 2026 and its 'order of magnitude' is the v1 figure; Decan
    is an ICML 2026 workshop paper; PASTA and Nudging retitled; OpenAlex cites: returned 0). Files: research_report.md, evidence/{quotes_iter5,saturation_hits_iter5,search_log_iter5}.jsonl,
    evidence/flags.json, evidence/protocol.json.
  workspace: >-
    /ai-inventor/aii_data/runs/run_aRfWvcSWjssb/3_invention_loop/iter_5/gen_art/gen_art_research_2
  output_files:
  - research_out.json
  - reproducibility.md
- iteration: 6
  name: gen_art_evaluation_5
  type: evaluation
  title: Record repair and blind novelty re-check
  summary: >-
    CPU-only record repair (iteration-6 Step 0) of the run's report, plus a second blind novelty adjudication. Provides: corrections.json
    (36 report corrections, each a verbatim old_text from current_report.md -> new_text, keyed to section and line, with values
    {recorded, recomputed, MATCH/CORRECTED/NEW/CARRIED, '<artifact_id>:<path>' source}; 78 MATCH, 1 CORRECTED, 18 NEW, 2 CARRIED;
    no overlaps); eval_out.json (exp_eval_sol_out; 10 datasets, ~372 metrics); engine_labels.json (24 internal results tagged
    by numerics: HF-FP8-W8A8, vLLM-FP8 W8A16 Marlin, HF-bf16); tables/*.csv; figures/fig_beta_escape_l4l (bf16 like-for-like).
    KEY RESULTS. (0a) The two artifacts' off_default_share fields use different definitions (bf16: correct off-default/N;
    FP8: valid attempts off-default/N); a mean of per-position ratios (0.83-1.39) is not Table 174's ratio of mean norms (0.62-0.97).
    Dose-bracketed contrast (bf16 alpha 2 >= 1.24 FP8 ban units vs FP8 alpha 1): connected components (bf16 1/50 vs FP8 30/50
    at alpha 2, Fisher p 7.2e-11; bracket p 0.056) and shortest path (2/47 vs 15/37, p 5.3e-5; bracket p 0.017) 'did NOT replicate
    in bf16 at the population level'; kth smallest and grid 'not established'; two sum/find duplicate had no FP8 effect. Site
    odds ratio, same-seed contrast and plan subspace: FP8 only, untested in bf16. (0b) Landings 17/21 per set (5/5 screen,
    1/2 bf16 remeasure, 3/3 A, 3/4 B, 5/7 Gemma; Poisson-binomial p 5.8e-7) but the unconfounded held-out subset is 5/8 (p
    0.053), so 5.11 item 2 moves to descriptive; the twin's own most frequent alternative matches the base runner-up on the
    7 events where it is defined (6 vs 6). (0c) Movability rho(beta,E) 0.146 over 13 new units, Bonett-Wright 95% [-0.44,
    0.65], BCa [-0.50, 0.70], power 0.63 one-sided (0.50 two-sided) at a true 0.6, n=20 needed; 0.035 if count inversions'
    beta is taken from correct programs (its committed beta 0.75 comes from attempts, 67% 'other'); only runtime merit R6
    tracks movability (rho 0.71, Holm p 0.021). (0d/0e) Table 206 phrasing columns, P15/P20 with bootstrap intervals, panel
    B knob rows (Table 203b), Table 126c rows, per-task PN-vs-DMD counts (19:3 but 13:0 on kth smallest), Gemma fill rule.
    (0f) 14 disputed programs sandbox-stress-tested, nearest known solutions by Zhang-Shasha AST distance, judged blind by
    Mistral Medium 3.1 (x3, T=0) and Kimi K2 with 10 controls: gates 9/10 each; Mistral called 1/14 novel (P13, a linear search;
    overturned on full read), Kimi 0/14; final novel count 0; one manual class corrected (P21: linear scan + list.count).
    Audits: audit/rederive.py 277/277 checks with 5/5 placebos failing; audit/headline_check.py reproduces 7/7 headline numbers
    from raw files with placebos failing. OpenRouter spend USD 0.29 over 4 judge passes (cache makes reruns free). Inputs
    located by artifact id under AII_DEPS_ROOT; report and two non-dependency evaluations vendored in inputs/.
  workspace: >-
    /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_6/gen_art/gen_art_evaluation_5
  output_files:
  - eval.py
  - full_eval_out.json
  - mini_eval_out.json
  - preview_eval_out.json
  - reproducibility.md
- iteration: 6
  name: gen_art_experiment_29
  type: experiment
  title: Is FP8 rounding behind the random-push escapes?
  summary: >-
    Decides whether iteration 4's random-push 'escapes' (fixed random directions added to Qwen3-8B's task-spec states at blocks
    12-23 change the algorithm it writes) are a property of the model or of the FP8 W8A8 engine they were found in. Iteration
    4's 40 directions (seeds 9101-9140), CRN slots, twin prompts, absolute unit n[l,p], fence stop and two-stage escape rule
    were re-run under four numerics from one bf16 snapshot: a W8A8 (native _scaled_mm), b W8A16, c W16A8 (per-token e4m3 fake
    quant), d bf16. One labeller version (exp22 + iteration-5 T2 re-gate) for every row. RESULTS: engine a reproduces iteration
    4 BYTE FOR BYTE on this GPU (400/400 REPRO rows vs exp22, 40/40 PN rows vs exp19), so exp22's own rows serve as engine
    a. Escape fraction E at alpha 2 (40 directions; each engine vs its own twin): T10 a 0.725, c 0.600, d 0.650, b screen-level
    0.70 (confirmation incomplete); T2 a 0.200, b 0.125, c 0.150, d 0.150. Committed literal verdict: NOT_REPRODUCED_HIGH
    on both tasks -- bf16 escapes on the same directions (T10 per-direction Spearman 0.96, kappa 0.83, discordance 3:0, McNemar
    p=0.25). FP8 adds only a small per-slot boost on T10 (CRN-paired screen slots: off-default 0.583 vs 0.532, 30:10, exact
    McNemar p=0.0022; none on T2), carried partly by weight rounding (b 0.556) and not by activation rounding (c 0.497). Per-sample
    plan noise at the matched absolute unit is also reproduced in bf16 (T10 alpha 2: a 30/50, b 27, c 22, d 25), so iteration
    5's bf16 PN null (1/50) came from its different unit/direction seeds, not bf16. Diagnostics: per-token KL to bf16 <= 0.004
    nats; activation rounding adds 3-13% induced perturbation; landings unchanged (DFS/BFS on T10, Bellman-Ford/SPFA on T2).
    Validation: CPU gates C1-C5 (escape code reproduces exp22 escape.json exactly), unit tests U1-U6, hash-chained pre-registration
    (COMMIT #0 + 5 amendments + final record), stdlib re-derivation and an independent raw-row audit with placebos (all match).
    Files: method_out.json (exp_gen_sol_out; datasets engine_pop/engine_twins/engine_pn/engine_posctrl/engine_summary with
    predict_a..d = 'label|pass' per CRN slot), data/raw/raw_<engine>.jsonl (every program with token ids), data/labels.jsonl,
    data/samples.jsonl, results/*.json (verdict, escape_by_engine, mcnemar, slot_flips, pn, repro, diagnostics, relabel_table,
    known_solutions, deviations), figures/. Deviations: 16 GB RTX 2000 Ada (bf16 engines at B=7 with a KV-capped copy of the
    sampler; U3 shows batch-size invariance for B>=3), alpha 1 / mimic / T03 dropped, Triton W8A16 not buildable (reference
    cast path used), engine b's T10 confirmation incomplete.
  workspace: >-
    /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_6/gen_art/gen_art_experiment_29
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 6
  name: gen_art_experiment_30
  type: experiment
  title: Where a coding model decides its algorithm
  summary: |-
    bf16 Qwen3-8B (rev b968826d) on a 16 GB RTX 2000 Ada (embedding table on CPU), exact common-random-number sampling, frozen gated labellers; 4,320 generated programs + 1,220 teacher-forced passes, about 2.7 GPU-hours, OpenRouter USD 0.055. Every rule hash-committed (7-commit chain, 0 breaks); every headline re-derived from the raw rows by a stdlib script (295 checks, 0 mismatches) with placebo tests that fail as they should.
    STAGE A (method: full-state exchange of the full ban's residual states into the token-length-matched neutral twin; baselines: twin, matched-norm random exchange MR, placebo twin, identity and KV-splice tests). The ban is carried by the task-specification states at blocks 12-23 on prompt-route tasks: T2 Dijkstra->Bellman-Ford/SPFA transfer 0.80 (24:0, Holm p 7e-7), condition-span KV splice 0.00, read position 0.00. Direct-route tasks follow the condition-span splice (T05 1.00, T06 0.90). MR <= 0.13, placebo <= 0.03; X_0-35 beats MR on T2 23:0, T03 16:2, T10 11:0. Committed P1 NOT SUPPORTED (T05 spec states also transfer 0.43); route check, placebo and MR predictions hold. Forced 'Implement Bellman-Ford or SPFA' spec-state exchange into its padding twin: 30/30 (twin 1/30); forced BFS on T10: 28/30.
    ST (iteration-4 FP8 noise-site claim rerun in bf16, T03/T10, 8 sites x alpha 1-8, Firth model at matched downstream displacement). Spec-position noise moves the algorithm (T03 S0 0.37 correct off-default at alpha 2; T10 S4 0.33 at alpha 4); read position, condition span and late blocks barely do (T03 S0 vs S1 paired 24:5, MH OR 4.6). The committed rule is WITHDRAWN: the condition-span arm has no common support with S0, and alpha-8 breakage erases the S1 contrast. A post-hoc alpha<=4 model puts S1 below S0 on both tasks (beta -3.8, -5.0; bootstrap CIs exclude 0).
    STATE VS TOKEN: S3 noise on generated tokens vs a temperature matched on per-token KL (T 2.06/2.72) is not established (12:6, 7:3).
    TOP-FIVE PUSH (T1, exp20 u_top5): breaks programs before moving the algorithm; in activation coordinates (F5) the push leaves the forced-prompt manifold; the prompt top-five ban stays inside the banned set.
    L (21 recorded push-landing events): the base model's runner-up beats the instruct model's own teacher-forced opening ranking, 17 vs 10 hits, sign test 8:1, p 0.020.
    Files: method_out.json (+full/mini/preview; 7 datasets, one example per task x cell x slot), results/*.json, results/summary.md (all tables), figures F1-F6, data/samples_raw.jsonl + labels.jsonl (every program), commitments.log, README.md, reproducibility.md.
  workspace: >-
    /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_6/gen_art/gen_art_experiment_30
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 6
  name: gen_art_experiment_31
  type: experiment
  title: Where Gemma picks BFS or DFS, and steering it
  summary: >-
    Claim S on google/gemma-3-4b-it (bf16, RTX 2000 Ada 16 GB): where the model's BFS-vs-DFS choice for one grid-path prompt
    (T1) forks, and whether Gemma Scope 2 resid_post SAEs (16k, l0 medium; layers 9/17/22/29) read and steer it better than
    DiM, raw residual, random features, isotropic directions, DAS and prompting. PROVIDES: (1) natural splits N=200 (T1 DFS
    139/BFS 61, pass 0.86; T04 naive 173/builtin 27; R6 linear 170/binary 29) with exp8/exp11 labels, engine check vs iteration
    5 (T1 0.94, T04 1.00). (2) Gate: SAE sites 22 and 29 pass, 9 and 17 fail (descriptive). (3) Fork: 3,712 prefix-resampling
    continuations; 12/12 BFS paths have significant change points; the plan is ONE token at response index 32 after a shared
    32-token opening: ' visited' -> DFS (P(BFS) 0.011, n 1409), newline/'if'/'queue' -> BFS (0.95-1.0); ~138 tokens before
    any algorithm-identifying code; identical-prefix share 0.73-0.85. (4) Decodability: within-prompt read before the identifying
    token is at ceiling for text too (BA 1.00, no SAE gain); at the fork it is undefined by construction. Cross-prompt readout
    of the fork log-odds y_v over 120 neutral variants (SD 0.67 nats; sampled-share Spearman 0.65): SAE Lasso at the fork
    position R2 0.66 vs text 0.18 (dR2 0.49 [0.26,0.65], p=0.003; >= DiM 0.34); BUT raw-residual ridge reaches 0.72 and SAE
    ridge <=0.09, so the information is in the residual and the SAE advantage is estimator-dependent; at spec positions SAE
    = text (0.18). (5) Steering at the fork (layer 22): matched-norm logit effect DiM +4.04 vs SAE clamp +1.78 vs random features
    +0.51 vs isotropic +0.12 nats; generation N=50 CRN: BFS 13/50 twin -> SAE 30-36, DiM 46-49, RANDF 21 (attempted; SAE>RANDF
    p=6e-5, DiM>SAE p=3e-5), equal at matched logit effect; every fork edit collapses correctness (pass 0.84 -> 0.16-0.58),
    so target-correct tests are null and NO feature claim; the pre-registered feature rule is met by the random-feature placebo
    (non-discriminating). Spec-position edits do nothing; toward DFS works (47-50/50). DAS rank 1-4: held-out dy +8.8 to +9.8
    (random ~0) but 0/50 pass in generation. First-order attribution fallback (graph dropped): top nodes beat random active
    latents in real-model ablation. (6) TOP5 ban: avoidance 0.00; BFS 10 -> 41/50 (McNemar 32 vs 1, p=8e-9), pass 0.38; TOP5
    states sit by the banned A*/greedy cluster in PCA/Isomap/MDS of real activations. (7) Novelty: 0 novel among 1,450 correct
    programs. Hash-chained commits #0/#1 verified; stdlib re-derivation 32/32 checks, placebos reported. FILES: method.py
    + src/, method_out.json (6 datasets, metadata = all results), results/*.json, figures/ (geometry in activation coordinates),
    data/ raw rows + labels, cache/states (kept on volume), README.md, reproducibility.md.
  workspace: >-
    /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_6/gen_art/gen_art_experiment_31
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 6
  name: gen_art_experiment_32
  type: experiment
  title: Reading an LLM's planned algorithm in words
  summary: >-
    Qwen/Qwen2.5-7B-Instruct (bf16, one L4) on 8 algorithm-choice coding tasks (T1 grid path, T2 shortest path, T03, T05,
    T06, T10, T04, R6). Labels come from frozen runtime+AST labellers (51/51 references correct). The released NLA pair kitft/nla-qwen2.5-7b-L20-av/-ar
    reads layer-20 states; pre-registration is a sha256 chain (commits 0-3 each precede their samples). BEHAVIOUR (results/behaviour.json):
    defaults are BFS, Dijkstra 0.88, hash map 0.98, hash set 0.71, DFS 0.62 (differs from Qwen3's union-find), naive, binary
    search; T03 has none. Qwen2.5 mostly IGNORES 'do not use X' bans. Only T05 gives a substitute (brute force 32/46). On
    T10 a DFS ban raises DFS 29->43 (15 union-find->DFS CRN flips). All 70 W4 ('X is not allowed here') programs use the banned
    default. The T2 semantic seed barely moves Dijkstra. INSTRUMENT (results/layer_convention.json, gate.json): the extraction
    convention is hidden_states[21], the output of block 20 (FVE_ref 0.695 vs 0.580 for [20]). The reference set reproduces
    the released 0.752 within 0.06; FineWeb and chat score 0.78-0.79. Code text is out of distribution (LeetCode 0.45, HumanEval+
    0.39). The task-state gate is FVE_ref 0.512, PARTIAL. READOUT (results/readout.json; blind judges Gemini-2.5-flash-lite
    + Mistral-small-3.2, DeepSeek resolver, kappa 0.82 on explanations): at end-of-prompt positions (SPEC-3..READ) the NLA
    never names the planned algorithm. N1 ban->Y* is 0/16 (only T05 eligible; fallback F4). N2 twin->default is 0/112 vs text-only
    0/112. N8b (ban-failure default) is 0/96. The N3 positive control is 0.00 on all 7 tasks vs text-only 1.00; explanations
    mention the prompt's own algorithm name in 0.7% of cases. They describe the format line and confabulate the task. At generated
    tokens the NLA sometimes names the realised algorithm before the text does (up to 0.28), but the outside-reader PREDICT
    baseline beats it per sample (0.25 vs 0.07, McNemar 20:88, p=2e-11). EXPLORATORY local control (results/local_control.json):
    read AT the algorithm-name token, explanations mention it 80% (forced) and 89% (ban) of the time, and they respect the
    ban's negation (planned 0.48 vs 0.06). Identity fades within one sentence (27%/6%), so the null means 'not carried in
    verbalisable form at pre-code positions', not 'NLA blind'. CAUSAL (results/causal.json): the pre-registered difference-of-reconstructions
    edit at 4 prefill positions, x1/x2/x4, N=30 CRN pairs, FAILS on all 4 tasks (T10 union-find, T05 brute force, T06 Floyd,
    T04 KMP; T2/T1/T03 had no admissible Y). Edits are tiny (||delta||/||h|| 0.04) and the prefill site is inert even at x16.
    EXPLORATORY steering at READ + generated tokens 1-64 (results/causal_exploratory_followup.json): the NLA edit x8 moves
    T06 to Floyd 0.76 vs C0 0.28 (25:1 over 50 CRN pairs; fresh-slot replication 13:0). It beats matched random 28:1, an unrelated-word
    edit 12:1 and a norm-matched round trip 13:1. T05 brute force 10:0 at x8 and 23:0 at x16; T10 moves only with difference-in-means
    (15:1); T04 does not move. Prompting (forced adherence 0.90-1.00) remains the ceiling. Novelty audit: 10 correct 'other'
    programs, 0 novel. Every headline number is re-derived by audit/rederive.py (stdlib) and audit/rederive_headlines.py;
    placebos fail. FILES: method_out.json (exp_gen_sol_out; datasets nla_behaviour 1,646, nla_readout_states 1,900 with predict_nla
    vs predict_text_only_name vs predict_outside_reader, nla_causal 2,314, nla_causal_exploratory 1,960, nla_local_control_exploratory
    660; all analyses in metadata). Also data/explanations.jsonl (6,180 explanations), data/judgements.jsonl, figures F0-F9
    (F6/F8 activation geometry). cache/*.npz (layer-20 states, recon, deltas) stay on the run volume. Caveats: one model and
    layer, one AV checkpoint, code is out of distribution for the NLA, and the steering results are exploratory.
  workspace: >-
    /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_6/gen_art/gen_art_experiment_32
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 6
  name: gen_art_research_3
  type: research
  title: Who already found the hidden plan?
  summary: >-
    Dated (2026-10-22) positioning audit for the iteration-6 claims P1-P5, N, S and E. It provides paste-ready Table 92e in
    research_report.md: 8 claim blocks plus CTRL rows. It has 123 new verbatim, versioned quotes from 94 sources, all 123/123
    matched against cached source text and 123/123 re-matched by an independent live fetch_grep pass. Statuses: 82 VERIFIED,
    22 VERIFIED-ABSTRACT, 4 VERIFIED-BLOG, 15 VERIFIED-README. It cites Tables 92b/92c (art_kjrCpQnPaniY) and 92d (art_ObxQOIlAM9MS)
    by row id without re-verifying them. Saturation search: protocol frozen and sha256-stamped before the first call; 21 strings
    over 7 lanes on arXiv API, Semantic Scholar, the OpenReview ICLR 2027 pool, OpenAlex/Crossref and grey literature; 6 round-2
    strings; snowballing; a round 3 that met the stop rule; 126 logged calls (incl. 3 supplementary full-text checks). 2,191
    raw hits gave 1,820 unique records, 1,401 in the window and 67 papers scored on the O/I/C rubric (75 claim-rows: 3 occupy,
    66 adjacent, 6 irrelevant). FLAGS: A (DAS localization of algorithm choice in code, validated by generation) NOT FIRED,
    narrowly. CDAS (ICLR 2026) does DAS steering validated by generation, but on refusal and a CoT backdoor. Algorithm choice
    in code is moved only by prompt cues (92c Invisible Lottery). Code attributes that are not the algorithm (language, library,
    coding habits) are moved by patching or difference-in-means vectors. The nearest same-model, same-site neighbour is the
    ICLR 2027 submission 'Before Reasoning Begins' (Qwen3-8B final-prompt SAE targets, code benchmarks, random nulls). B (activation
    quantization changes perturbation effects) PARTLY FIRED. Steering under quantization has been measured only with weight-only
    INT8/NF4 (2609.06473: activations stay FP16/BF16). Two ICLR 2027 submissions show effect changes across precision with
    aligned directions, but their abstracts do not say whether activations are quantized (PDFs 403). FP8 W8A8 appears only
    in a non-determinism study. No source found measures the effect size of random perturbations under activation rounding.
    C (editing verbaliser explanations to steer) FIRED. The NLA paper (Transformer Circuits, 7 May 2026; cite as Fraser-Taliente,
    Kantamneni, Ong et al.) edits a rhyme-plan explanation, reconstructs it with the AR and steers at the newline only (~50%
    success). LatentQA, SelfIE and Dreaming Vectors are kin. N is therefore a replication in a new setting. Cautions: about
    2% claim-dependence of the AR (2607.20379), no newline plan in small open models (2609.18440), and published readout controls
    (ICLR 2027 'Auditing the Auditor'). D (resampling a fitted causal plan variable for diversity) PARTLY FIRED. Activation
    noise and latent-code sampling are occupied; the closest fitted-direction work is the ICLR 2027 'Random Choice in LMs'.
    Lane verdicts: P1 PARTLY OCCUPIED (method); P2, P3 and P4 ADJACENT-ONLY; P5 PARTLY OCCUPIED; N OCCUPIED (method); S PARTLY
    OCCUPIED (SAE-Steering, ACL 2026, beats prompt and activation baselines on reasoning strategies); E ADJACENT-ONLY in the
    published record but PARTLY OCCUPIED by contemporaneous submissions. Corrections: there is no official NLA for Qwen3-8B,
    but community NLAs exist at L24 (nanoNLA, EasyNLA); circuit-tracer has Qwen-3 PLTs including 8B (Hanna et al.), so justify
    Gemma for S; Gemma Scope 2 dates from 22 Dec 2025, with IT SAEs finetuned from PT; Sutter's 'any network to any algorithm'
    phrase is not in v2; Engels' v3 title. The report also gives permitted and forbidden wording per claim and reviewer baselines.
    Evidence files are in evidence/.
  workspace: >-
    /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_6/gen_art/gen_art_research_3
  output_files:
  - research_out.json
  - reproducibility.md
- iteration: 7
  name: gen_art_evaluation_6
  type: evaluation
  title: Fixing the run's record, number by number
  summary: >-
    CPU-only Step 0 of iteration 7: the iteration-6 record of the run report, re-derived from the raw rows of art_lpQalcAXMGr1,
    art_rMlbrjVB1c__, art_zNyBP6zieI5u and art_dbUtqBjT0tPf and corrected in place. PROVIDES: corrections.json (54 verbatim
    old_text->new_text pairs marked '(iteration-7 correction)', each with values {recorded, recomputed, status, source});
    report_corrected.md + report.diff (apply test 54/54, no overlaps; residual-claim lint 16 -> 0); values 603 MATCH, 117
    NEW, 1 CARRIED, 3 CORRECTED (plan venue expectations contradicted by live records). KEY FINDINGS: (0a) Stage A tables
    print commit0's attempted share (invalid = not-Y, gate pass_ratio >= 0.8), not 'share of correct programs'; correct-Y
    column added to Tables 244-250 (tables/stage_a_cells.csv): shortest path X_0-35 24/30 attempts, 21/30 correct; X_12-23
    18/11 (pass ratio 0.73, fails gate); kth smallest X_0-35 17/16; grid X_0-35 14/3 (fails gate); grid condition span 10/7;
    forced BF/SPFA exchange 30/30 (transfer 0.967); forced BFS exchange 28/24; 5 cells fail the gate; post-hoc correct-Y McNemar
    vs matched-norm random exchange 21:0 (p 9.5e-7), 15:2 (p 0.0023), 11:0 (p 9.8e-4). This correct-Y column is the full-state
    denominator for Step Q1. (0b) site of the choice open: post-hoc condition-span beta -1.70 [-3.96,0.42] (T03), -0.56 [-4.93,2.91]
    (T10); 'FP8-specific' label refuted by 6.3; NEW Table 254b: noise/exchange bands concordant on kth smallest (12-23), discordant
    on connected components (noise 0-11, S4 +2.51 [1.39,3.80], flips 4:18; exchange 12-23); depth-redundant removal 0.87/0.63.
    (0c) Gemma DAS rank-1 +8.8 nats (random -0.08..+0.05; shuffled-source 10.1 uninformative; no random-init or target-shuffle
    control; rank-4 50/50 BFS, 0/50 pass) does not show one-dimensionality; standardised SAE ridge 0.15 vs 0.086 control (delta
    0.064 < 0.10); fork readout ~ next-token readout; BFS-ward edits pass 0.84 -> 0.16-0.58 except SAE top-5 (18 BFS, pass
    0.84). (0d) per-model/per-quantity synthesis, NEW Table 279; Gemma's read position never measured. (0e) 7 captioned [FIGURE]
    markers (figure_markers.json; sha256, code refs, MDS stress 0.371/0.369/0.542/0.569; all positions precede the fork).
    (0f) top-five push: 1-8 ban units overshoot the manifold (PC1 centroids -0.098..0.144; alpha-1 +0.09 -> -0.44; pass 0.67/0.30/0.03/0.00).
    (0g) Table 238 correct-only: shortest path alpha 2 14/37 W8A8 vs 9/31 bf16; alpha 1 9/43 vs 5/43; screen-level verdict
    MIXED (W8A8 15/40 screen passes vs 8-9; 17/40 excess met but pass failed). (0h) NLA N6 reproduced (364 units, 20:88, p
    2.3e-11, task-cluster CI [-0.35,0.02], clusters T05/T06/T1/T10/T2); one unit per sample (104 samples) 0:25 p 6.0e-8; random-unit
    median 4:29 p 1.9e-5; sign test 12:38 p 3.1e-4; Durkalski p 6.5e-5; task level 1:3 p 0.625, floor 0.0625 -> inconclusive
    at task level. (0i) U6 mild failure: 0.38 (73/192) vs 0.305 [0.245,0.372], exact p 0.028; D12 quoted. Engine control had
    3 correct 'other' programs (2 in labels.jsonl + 1 iteration-4 engine-a row): 2 array-scan Dijkstra, 1 n-round Bellman-Ford;
    all pass hidden (45/45) and stress tests; nearest known tree distance 0.00-0.11; judges: deepseek-chat-v3.1 gate 10/10
    (passed), gpt-4.1-mini 8/10 and declared replacement gemini-2.5-flash-lite 8/10 (failed on the two known-outside controls);
    every judge and the manual read: catalogue variants; 0 novel (no rate quoted). (0j) 4.9 limited to audited pools; never-audited:
    ~9,000 forking-token programs (Section 3.2.3, CARRIED) and the engine nearest-known pass. (0k) 6/6 quotes verified live;
    Ma & Rui is an ICML 2026 workshop paper; A Tale of Two Temperatures is COLM; no NeurIPS 2026 page for Forking Fast; Forking
    Paths ICLR 2025 confirmed; Table 277 row 66 ADJACENT-ONLY (mini search 2026-10-22, 14 queries). (0l) 6 conditional tags.
    VALIDATION: audit/rederive.py 520 checks 0 mismatches, placebos 7/7 fail; audit/headline_check.py 35/35, placebos 7/7
    fail; predict_* cross-check 137/137. eval_out.json (exp_eval_sol_out; M1-M12; 7 datasets). OpenRouter USD 0.077.
  workspace: >-
    /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_evaluation_6
  output_files:
  - eval.py
  - full_eval_out.json
  - mini_eval_out.json
  - preview_eval_out.json
  - reproducibility.md
- iteration: 7
  name: gen_art_experiment_33
  type: experiment
  title: Searching for the model's algorithm switch
  summary: |-
    bf16 Qwen3-8B (rev b968826d), thinking off, one RTX 4090; exact common-random-number generation (exp30 engine), frozen gated labellers, 4,500 generated programs, ~1.6 GPU-hours, OpenRouter USD 0.13; 18-commit sha256 chain (0 breaks); headlines re-derived from raw rows (audit/rederive.py 180 + rederive_tf.py 52 checks, 0 mismatches; placebos fail).
    METHOD: distributed alignment search (DAS), one orthonormal map (4096x16, nested ranks 1-16) at the task-spec states, fitted on all (source x base) pairs (bans W1-W3 + forced 'Implement Y' families 0-2 -> neutral/padding twins) and validated by HELD-OUT generation (W5 ban, forced families 3-4; N = 30 CRN slots; correct-Y by hidden tests) against the full-state exchange at the same site and controls (random rank-k subspaces, permuted-label DAS, read-position DAS, null source, DIM-1, PCA-16, projected map, reverse interchange, Sutter random-init network).
    SITE: single-block exchange at the TF-optimal block moves 0/30 for ban sources on T2/T10 but band 12-23 moves 11/30 and 17/30, so the committed band fallback fired; forced instructions transfer fully from one block (T2 L18 30/30, T10 L16 28/30); T03 is single-block (L16 27/30).
    COMMITTED OBJECTIVE FAILED: the contrastive TF objective diverged (val 1,873 / 3,868 nats vs 14-35 ceilings; permuted too) and its 10-slot pilot wrote broken code; amendment 1 (pre-generation) fitted the bounded LME_Y objective (MAIN_LY) used for every decisive cell.
    P1 (LME_Y map): DAS rank 1-2 matches full-state transfer while random subspaces do nothing: T2 ban k2 12/30 vs full 11/30 (base 1, random <=1; McNemar 11:0, Holm 9.8e-4); T10 ban k16 29/30 vs full 17/30 (random 0; 61:0); T03 ban k1 26/30 vs full 27/30 (base 5, random 6; 20:0). Pass rates >= 0.8x base; read-position <= 0.07, DIM-1/PCA-16 0, null <= 0.03. BUT permuted-label DAS also transfers (0.47 / 0.70 / 0.60) and a random-init network admits an equal TF fit (13.3 vs 14.5 nats) -> P1 FAIL on T2, T10, T03; overall NOT SUPPORTED. C: CATEGORICAL by rule (T2, T03) but the map routes Floyd-Warshall (28/28) and counting sort (30/30) beyond what full-state carries (8/20, 0/30); T10 forced BFS -> DFS. Dormant flag on T2 (reverse interchange restores 0/30 vs 21/30) and T03 (projected retention 0.2).
    M (T2, R_16 coordinates, real activation geometry, MDS stress 0.08, Isomap): bans leave the paraphrase null (100th pct) along the Dijkstra->Bellman-Ford (runner-up) axis; random seeds, 'Make a new algorithm.' and the 2,000-word novelty instruction stay inside; behaviour agrees (seeds/short instruction 30/30 Dijkstra; long-form 6/30 Bellman-Ford). Leave-one-survivor bans not placed toward the survivor (rank 3.1/5, p 0.63). R: lambda sweep graded (width 3.25, plateau 6-9/20), not discrete. Novelty: 38 correct 'other' programs, 0 novel. Second init seed: different subspace (angles 38-90 deg), similar behaviour.
    FILES: method_out.json (1,390 examples, predict_<arm> = label|pass), results/*.json + summary.md, figures F1-F8, das_maps/ (all fitted maps), data/samples_raw.jsonl + labels.jsonl, prompts/prompts7.jsonl, reproducibility.md.
  workspace: >-
    /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_33
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 7
  name: gen_art_experiment_34
  type: experiment
  title: Where a coding AI picks its algorithm
  summary: >-
    Tests whether one early generated token decides which algorithm bf16 Qwen3-8B (rev b968826d, thinking off, T = 1) writes,
    and whether a prompt-state default-to-runner-up axis mediates random activation pushes. Tasks: T10 connected components
    (union-find default), T2 weighted shortest path (Dijkstra), T03 k-th smallest (full sort), plus T1 grid path for an in-manifold
    top-five prohibition. Outcome-blind sha256 commit chain: commit #0 rules and thresholds; #1/#1b/#1c forks; #2 axis; #3/#3b
    predictors, all before any outcome row was opened; #4 push spec. Amendments are logged in results/deviations.jsonl. RESULTS.
    (1) Forks (4,560 prefix-resampled continuations, permutation-null change points): T10 decides at generated tokens 10-11
    ('parent'/'def find' gives union-find; '#'/'from'/'def dfs' gives graph search; H(label|token) = 0 bits at token 11).
    T2 has no early fork (pushed paths undecided through token 60; change near token 92). T03's class is fixed by the prompt
    before the first token. (2) F (the teacher-forced fork margin predicts which of 40 equal-dose random pushes escape; exp29
    engine-d outcomes): T10 Spearman 0.80 (perm p 1e-4, CI 0.62-0.91, tie ceiling 0.99); T2 0.15 (48-token LLR fallback);
    pooled 0.48; held-out GLM MAE 0.25. Committed verdict NOT SUPPORTED (inconclusive; Holm p 0.36). T03 prospective confirmation
    on 24 fresh, pre-committed directions: margin Spearman 0.60 (one-sided p 0.0014). Exploratory: T2's LLR reaches 0.42 at
    a 160-token opening. (3) P2 is DISCONFIRMED (axis projection 0.17/0.01, not ahead of P_t, raw norm or U4 energy). The
    axis clamp removes 0% of escapes (104 -> 105; random clamp 106). A single-layer targeted push along the axis gives no
    escape at s <= 1 on any task. At s = 4, T10 switches to correct DFS on 29/30 slots against 0/30 for a matched random direction;
    T2 shows none even at s = 8, and T03 is not axis-specific. (4) T1 in-manifold top-five pushes toward survivor centroids
    (Isomap/MDS/PCA geometry in real activation coordinates; old u_top5 overshoot overlaid): 0/300 non-top-five programs,
    all BFS. The prompt top-five ban also stays in the banned set. (5) Exploratory forced token under the unchanged twin prompt:
    'def dfs' at tokens 10-11 gives 30/30 correct DFS; a comment token gives 30/30 union-find, so token maps are cell-dependent
    for non-committal tokens. Robustness: all 40 directions were re-measured on this RTX 4090 (pre-declared fallback 1). Their
    y correlates 0.95/0.93 with exp29 and the conclusions are unchanged; Stage-0 twin agreement is 0.97-1.00. Novelty audit:
    2 correct unlabelled programs, both labeller misses (USD 0.0004). Independent stdlib audit (audit/rederive.py): 199 checks,
    0 mismatches, every placebo fails. FILES: method_out.json (exp_gen_sol_out; datasets f_cells, p2_directions, t03_confirmation,
    fork_resampling, engine_check, targeted_push_T10/T2/T03, top5_push_T1, forced_token_exploratory; all analyses in metadata),
    results/*.json, figures F1-F7, data/*.jsonl (every program and label). cache/states/axis_*.npz and dbar_*.npz (the committed
    axes and per-direction displacements) are kept on the run volume for iteration 8. Limits: one model; memorised tasks;
    a sparse fork screen (C3 power 0.54 at a 0.4 jump); T1 10-class labels are AST-only.
  workspace: >-
    /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_34
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 7
  name: gen_art_experiment_35
  type: experiment
  title: Where temperature changes the algorithm an LLM writes
  summary: |-
    Iteration 7, claim T, on Qwen/Qwen3-8B (rev b968826d, bf16 HF, thinking off; one RTX 4090; about 0.75 GPU-h; OpenRouter USD 0.022). Verdict: PARTIAL.
    (1) WHERE THE ALGORITHM IS DECIDED (Test 1, pass 3/3). Prefix resampling (8 per prefix length, Bayesian change points, 20-continuation confirmation with control positions; sampler calibration passes on all units) finds a one-token fork right after the canonical opening (|O|+1):
    - B3 MST: the word after '    # ' ( Kr -> Kruskal 100%, pi 0.72; Prim -> Prim 97%, pi 0.27);
    - A3 rain water: ' n' -> prefix/suffix arrays, ' left' -> two pointers;
    - B6 anagram: ' return' -> sort, ' count' -> counting.
    H(algorithm | fork class) = 0.050 / 0.153 / 0.189 bits.
    (2) TEMPERATURE PREDICTIONS (Test 2, fail: passes on B3 only). The prediction function (teacher-forced logits along the opening and at the fork x P(A|token)) was hash-committed before any temperature sample.
    - Predicted attempted minority share at T 0.3/0.7/1.0/1.3: B3 .068/.193/.237/.247; A3 .166/.285/.311/.319; B6 .161/.182/.200/.212.
    - Observed in a same-seed sweep (N=50 per cell, the same 50 uniform streams in all 8 cells): B3 .06/.22/.40/.38 (MAE .083, drop 1.0->0.3 = .34, McNemar 17:0, p=1e-5, pass); A3 .10/.18/.18/.20 (MAE .105, drop .08, fail); B6 .18/.14/.12/.18 (MAE .043, no drop, fail). Pooled B3+A3 drop: 24:3, p=2.5e-5.
    - Raising T from 1.0 to 1.3 adds nothing (predicted +.01).
    - Top-k 10 is token-identical to top-p 1 in 600/600 same-seed programs.
    - The per-slot replay of the uniforms names each seed's algorithm in 90-98% of on-opening slots. Post hoc, A3's miss is a 50-stream realisation gap (replay-implied .08/.18/.18/.16 vs observed .10/.18/.18/.20).
    (3) COLLAPSED TASKS (Test 3, pass 4/4). Fork margins: T1 7.46, T2 4.85, T10 17.04, T03 6.10 nats. 0/100 off-default at T 1.3 from each fork node; T 1.3 checks 1/20, 1/20, 0/20, 0/20.
    (4) TASK-STATE LINK.
    - S4(b): exchanging the task-spec states of 'Implement <minority>' into its padding twin gives the minority on 30/30 slots on all units (vs padding twin 7/30, 4/30, 0/30; McNemar 23:0 / 26:0 / 30:0; matched-norm random control .40/.13/.00). The fork margin moves -4.9/-5.5/-22.1 nats (MR -1.2/-2.0/+0.3). In activation coordinates the exchanged fork state lands on the minority-token cluster.
    - S4(a) (8 random pushes, descriptive): Spearman of margin change vs share change -0.69/-0.44/-0.94 (lower-tail p .027/.12/.0003).
    (5) IDEAS VS PHRASINGS. Temperature only reweights the same 2-3 known ideas; phrasing clusters grow with T (B3 Kruskal 4 -> 12 at Jaccard 0.9). 0 correct novel algorithms among 2,290 programs and 12,676 continuations.
    AUDITS. 3-link sha256 commitment chain. src/rederive.py: 62 checks, 0 mismatches, placebo fails. audit/headline_audit.py reproduces every headline and the 24 committed predictions to within 5e-6; placebos reject at about 5%.
    FILES. method_out.json (exp_gen_sol_out; datasets twin, sweep, collapsed, s4a, s4b, fork_scan), results/*.json (test1-3, verdict, forks, predictions_view, s4a, s4b, table_1ac, novelty_audit, posthoc, headline_audit), predictions/commit*.json, figures F1-F7 (incl. F7 fork-state geometry), data/*.jsonl (all programs, continuations, labels), README.md, reproducibility.md.
  workspace: >-
    /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_35
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 7
  name: gen_art_experiment_36
  type: experiment
  title: Why random nudges stopped changing the algorithm
  summary: >-
    Iteration-7 step K on Qwen3-8B (rev b968826d, bf16 HF, thinking off, one RTX 4090). Question: why did iteration 4's per-sample
    plan noise (random direction pushed into task-spec states of blocks 12-23, prefill only, displacement-targeted) move T10
    25/50 while iteration 5's moved 1/50? Crossed dose unit (U_abs = ban displacement norm n[l,p] vs U_bf = ||h_twin||*r_Q)
    x direction seeds (S4 exp29 vs S5 exp27) on shared CRN slots, one engine, shared-prefix path. ANCHORS reproduce: D1=U_abs
    x S4 26/50 attempted (exp29 25/50, per-slot agreement 0.98); D4=U_bf x S5 1/50 (exp27 1/50) -> decoding path is not the
    cause. S1 verdict UNIT (committed rule, Holm): T10 a2 shares D1 .50 D2 .52 D3 .10 D4 .02; unit RD +0.45 [0.35,0.55], seed
    +0.03 [-0.07,0.14], interaction -0.10 [-0.28,0.08]; T2 a2 (N 100) unit +0.115 [0.06,0.17]; a1 replicates. D5 (U_bf* =
    U_bf profile at U_abs per-block energy) 0.28: profile at matched energy +0.22 [0.08,0.36], energy +0.18 [0.06,0.30]. S2
    (T10): top-quartile cells 29/50 vs rest 15/50 (McNemar 18:4, Holm p .009); position-shuffled 4/50 vs 25/50 -> pushes act
    where bans write. Downstream displacement SIZE does not explain it (U_abs and U_bf have similar block-35 norms; mediation
    leaves unit coefficients unchanged). Exploratory: E1 U_bf needs alpha~4 (20/50) to approach U_abs at alpha 2; E2 per-sample
    escapes are near-independent across directions on one token stream (phi .16-.20) and unpredictable from block-35 displacement
    at fixed dose (AUC .40-.53); E3 replicates on 50 fresh T10 slots (unit +0.42 [0.32,0.52]) and on T03 (+0.27 [0.18,0.37]).
    S3 prices at D*=D1 (exp27 full-simplex hull, 2,000 slot bootstraps): H5 PN* vs base intent T03 3.22 vs 1.73 WIN, T1 1.39
    vs 1.05 WIN, T10 2.13 vs 2.53, T2 1.21 vs 1.45, T05 1.10 vs 1.61 LOSS -> 2/5 (predicted 3); iteration-5 rule replayed
    still DISCONFIRMED (2/5) but D_bar moves -0.40 -> +0.12 [-0.18,0.27]. Re-tag: iteration-5 plan-sampler and movability
    verdicts tagged 'ban-free unit and iteration-5 seeds'; at D* T03/T10 movable, T2/T05/T1 not. Novelty: 5 correct 'other'
    programs (T03) all catalogue variants, 0 novel. CAVEATS: T2's U_abs puts 82% of its energy on one massive-activation cell
    (a '0' token, residual norm ~10,290), so T2 profile arms are confounded (P_rest breaks programs); engine check vs exp30
    15/16 on T2 and T03; 17/25 S3 knob cells reuse exp27 rows (cross-engine), 8 regenerated. Audits: gates G1-G5, GPU unit
    tests U1-U6, sha256 commit chain (0 rows before their commit), stdlib re-derivation of every headline (0 mismatches, placebos
    null). Files: results/{anchors,s1_2x2,s2_profile,s3_prices,retag,e1_sweep,e2_geometry,e3_replicate,novelty_audit}.json;
    data/samples.jsonl (per-program rows), data/raw/*.jsonl (texts, token ids), data/realised_disp.jsonl (36-block displacement
    profiles); cache/ (fp16 block-35 displacement vectors, unit dumps); figures F1-F7, E1, E3; method_out.json (exp_gen_sol_out,
    1,000 per-slot examples with predict_<arm>='label|passed'). GPU ~0.66 h; OpenRouter USD 0.10.
  workspace: >-
    /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_36
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 7
  name: gen_art_experiment_37
  type: experiment
  title: Evolutionary search for new coding algorithms
  summary: >-
    Pre-registered test (iteration 7, claim N) of whether a FunSearch/MAP-Elites program search with Qwen3-8B (bf16, vLLM,
    T 1.0) as mutator, a 3-stage sandboxed evaluator (8 quick cases, hidden suite, 10 seeded max-size stress inputs) and a
    novelty critic built from the declared dependency art_j3Rm_lr2nzR6 (rebuilt corpus n=18,237, exact) yields correct out-of-catalogue
    (OOC) programs >=10x more often per call than the best iteration-5 text knob (EAP/BINT). Tasks T2 shortest path, T03 k-th
    smallest, A3 trapping rain water; arms S (search), NE (no-evolution ablation), I0 (instruction only), EAP, BINT, B0 (neutral
    twin), L (qwen3-235b via OpenRouter, 500 calls). 13,100 decisive programs + 500 L programs. RESULT: prediction NOT MET.
    Level a (distinct OOC-screen programs) S vs K=EAP: T2 46/1500 vs 6/750 (R 3.83, LB95 1.83), T03 412/2500 vs 31/1250 (R
    6.65, LB95 4.86), A3 31/1000 vs 17/500 (R 0.91). Level b (adjudicated KNOWN-OUTSIDE+NOVEL): only T03 has any - S 78 vs
    EAP 0 (LB95 12.8), NE 0, I0 2, L 23/500 vs S-first-500 9; T2/A3 0 everywhere. Search beats the no-evolution ablation on
    T03 level b (78 vs 0, LB95 5.1) and 66/93 S level-b rows have depth>=2 with non-seed parents (composition across generations),
    but every OOC program is a KNOWN technique (value-range binary search, Fenwick/treap order statistics, bucket select,
    partial selection sort). On T2 the search's 15x level-a lead over NE is restyled SPFA (critic gaming); 2 of its OOC-screen
    T2 programs are wrong in general despite passing all tests. On A3 the search loses to NE/I0. 0 NOVEL algorithms (rule-of-three
    <=7.5% over 40 merged clusters, <=2.0% over 152). Adjudication: no judge passed the 10-control gate (best Kimi K2 8/10),
    so final classes are the executor's manual reads of all 244 candidates (novelty claim 'manually audited'); advisory judges
    kappa 0.42, all 11 judge NOVEL calls overturned; an arm-blind rule replication agrees 94.4%. Independent stdlib re-derivations
    from raw rows (audit/rederive.py, audit/rederive_raw.py with exact binomial sums) match all primary/secondary numbers;
    placebos fail as required. Key files: results/verdict.json, ratio_tests.json, arm_rates.json, manual_reads.jsonl, deviations.json
    (24), data/samples.jsonl, figures F1-F6, method_out.json (exp_gen_sol_out; search_programs 6,274, adjudication 254, arm_summary
    19). Cost: USD 0.89 OpenRouter, ~1.0 GPU-hour generation on one RTX A4500.
  workspace: >-
    /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_37
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 7
  name: gen_art_experiment_38
  type: experiment
  title: Gemma BFS‑DFS Fork Analysis
  summary: >-
    This artifact contains the source code (method.py) and three JSON result files (full_method_out.json, mini_method_out.json,
    preview_method_out.json) for iteration 7 of the "Circuit and dose dial at Gemma's BFS‑vs‑DFS fork" experiment. The Python
    script defines a pipeline of stages (engine checks, G1 path‑patching, G2 dose‑response sweeps, G3 temperature sweeps,
    novelty audit, etc.) and can be invoked for each stage via command‑line arguments. The JSON outputs record metadata (method
    name, model identifier, BF16 precision), status flags for each analysis component (engine_check, g3_sweep, g1_generation,
    g2_dose, g2_decisions, g1_extras, timing, costs) all marked as "ok", and detailed cost accounting showing a total spend
    of $0.0437 (≈$0.0364 on OpenRouter labeller calls across 88 API calls, plus $0.0073 for novelty and regate). They also
    include toy DAS training metrics such as training/held‑out KL divergences and principal‑cosine similarity values for three
    configurations (standard, shuffled, and a low‑learning‑rate optimiser). No further quantitative results (e.g., fork‑margin
    values, dose‑response curves, or temperature sweep predictions) are present in the displayed excerpts. Consequently, the
    artifact primarily provides the reproducible pipeline code and a verification that all planned sub‑experiments completed
    successfully within a modest computational budget, enabling other researchers to rerun the same stages, examine the cost
    breakdown, and extend the analysis with deeper result extraction if desired.
  workspace: >-
    /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_7/gen_art/gen_art_experiment_38
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
- iteration: 8
  name: gen_art_evaluation_7
  type: evaluation
  title: Fixing errors in the iteration-7 research record
  summary: >-
    Iteration-8 Step 0 record repair (CPU only, USD 0.095 of judge calls). It answers all 11 items (0a-0k) of the blocking
    iteration-7 review in place. report_corrected.md is the iteration-7 report (inputs/report/current_report.md) with 84 machine-checked
    edits, each marked '(iteration-8 correction)'. report.diff is the unified diff. corrections.json holds the edits and a
    141-value ledger (recorded, recomputed, status MATCH 68 / CORRECTED 7 / NEW 63 / CARRIED 3, source artifact:file#key).
    The residual-claim lint drops from 35 hits to 0. KEY CORRECTIONS. (0a) The kth-smallest labeller missed counting sort
    in dictionary form. The extension in labeller_v2/ was validated before any relabel: references 6/6, gold kappa 0.951 unchanged,
    controls 5/5. After the relabel, the full-state exchange of the forced counting-sort source gives 29/30 counting sort
    (was 0/30). Pooled kth recovery falls from 1.59/1.57/1.55 to 1.01 [0.95,1.08] / 1.00 / 0.99 at ranks 1/4/16 (exp33's own
    slot bootstrap, which reproduces Tables 293/295 exactly). DAS routes more cleanly than the full state on ONE task (shortest
    path, Floyd-Warshall 28/28 vs 8/20); on kth smallest it changes the form (array of counts) but not the algorithm. 29 of
    the 36 catalogue variants of 7.3.9 come from that cell. Judges deepseek-chat-v3.1 10/10 and mistral-medium-3.1 9/10 on
    the gate; 48 programs were read manually (tables/counting_sort_adjudication.csv). (0b) Recovery is now reported per source
    (new Table 297b, tables/recovery_by_source.csv): forced Bellman-Ford/SPFA 0.17-0.43, forced BFS 0.06-0.53, rank 2 never
    generated for forced sources. Untrained-network ratios, shortest path only: 0.013 (against the diverged fit, meaningless),
    0.92 (fit value), 5.08 (matched LME_Y gain, 43.6 vs 8.6 nats). (0c) Gemma's 42-vs-35 is not a comparison. DAS and twin
    cells have the 32-token opening prefilled (g2.py:877, prefix_len 32); the forced-BFS cell is sampled from index 0 (g2.py:878-885)
    on the same CRN slots. (0d) The fork margin is a readout, not a predictor: Spearman 0.804, opening LLR 0.869; no direction-level
    property predicts (axis 0.17/0.01). (0e) Gemma natural variance is below the random 95th percentile at ranks 1, 2 and
    4 and above at rank 8; block 22 rank 1 is above. dormant_flag was false only via |rho|=0.497. Dormancy checks were not
    run. Recovery 1.98-2.81x is the Makelov off-manifold signature. Qwen and Gemma controls are not comparable (new Table
    364d, tables/control_protocols.csv). (0f) New Table 371b and positioning.json: 12 neighbours plus 2 ICML 2026 workshop
    posters, all verified live 2026-10-23 (raw grep outputs in audit/web/). 'A Tale of Two Temperatures' is COLM (no year)
    plus AdaptFM and SPIGM workshop posters, and is about diffusion LMs. (0g) New 7.3.10 quotes deviations D-drop, D-tfsets,
    D-targets and D-cap verbatim. (0h) Table 346 fresh-slot rows, recomputed from slot rows: top quartile 24/50 vs rest 9/50
    (15:0); full unit 21/50 vs shuffled 4/50 (17:0); RD_seed -0.10. (0i) Search as rates (tables/search_by_arm.csv): 78/2,500
    (12 clusters) vs instruction 2/500; ratio 7.8, LB 2.41, short of 10x. (0j) MST's T1.0 prediction lies outside the Wilson
    interval [0.28,0.54]. W1-W3 are training templates. The semantic seed sits on the boundary (93.9th percentile). (0k) Step
    K tags are replaced from retag.json; 10 lost file names are restored. AUDITS. audit/rederive.py (stdlib, separate code
    path): 97 checks, 0 mismatches, 6/6 placebos fail. audit/headline_check.py: 11/11 headline numbers re-derived through
    different code paths (regex relabel of raw code, counting ranks, bisection bound), 5/5 placebos fail. NOT RUN (stated
    in the record): Gemma reverse interchange and projection; the Qwen untrained network beyond shortest path; a prefill-matched
    instruction cell. OUTPUTS: eval_out.json (exp_eval_sol_out; datasets corrections, report_edits, counting_sort_adjudication,
    recovery_by_source, gemma_natural_variance, control_protocols, search_by_arm, positioning_rows), tables/*.csv, README.md,
    reproducibility.md. Rerun: uv sync && uv run eval.py --stages all (about 25 s, judges cached).
  workspace: >-
    /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_evaluation_7
  output_files:
  - eval.py
  - full_eval_out.json
  - mini_eval_out.json
  - preview_eval_out.json
  - reproducibility.md
- iteration: 8
  name: gen_art_experiment_39
  type: experiment
  title: Temperature at the algorithm-deciding token
  summary: >-
    Experiment artifact for claims K1 and HR on bf16 Qwen3-8B (rev b968826d, thinking off; units T10 connected components,
    T1 grid, B3 MST, A3 rain water, B6 anagram, T2, T03) and bf16 Gemma-3-4b-it (grid task G), run on one NVIDIA L4 (2.8 GPU-h).
    Method: temperature applied ONLY at a located decision token (T = d over its top-20, T = 1 elsewhere; T10 also index 11
    after ' def'), with doses d1/d2 committed in advance from teacher-forced node logits plus token maps of forced continuations
    (2,050 programs). Comparators share 50 CRN slot streams per unit: global T 1.3/1.6/2.0 with top-p 0.95, min-p 0.1 at T
    3, EDT-style and AdapT-style temperature, the same dose at the highest-entropy or a random position, class-uniform forcing;
    boundary window arm on T1/T2/T03. Hash chain: COMMIT #0 protocol, #1 dose table and per-arm predictions, #1b locator,
    #2 HR predictions, #3 one amendment (pass-filtered dose). Results: (a) composed predictions hit observed algorithm shares
    with MAE 0.010-0.047 on 5/5 located units (per-slot replay 0.006-0.031). (b) Collapsed T10 FAILS: DFS 3/50 at d1=3.5 and
    9/50 at d2=7 vs 0-2/50 for global T (McNemar 7:1 vs T 2.0, p=0.035), but correct Hill-1 stays 1.24/1.60 and d2 costs 14
    pass points (format-breaking top-20 tokens); IUT p=0.30; the pass-cost disconfirming branch fires. Mixed units pass their
    d1/Hill criteria; B6 Hill-1 rises 1.78 -> 2.78 at 2 points cost, beating every comparator run there (bootstrap LB +0.19,
    p=0.008); B3 and G tie or lose to a tuned global sampler; A3 has nothing to gain. (c) fails: the decision token is a high-entropy
    token (0% below q90; entropy-max hits it on 44/44 G slots, 32/39 B3, 2/50 T10). (e) reversion 4/102; (f) Gemma pass cost
    0.14 vs committed 0.156, class-uniform forcing never draws ' queue'. Amendment: removing high-Pfail tokens keeps T10 pass
    at 0.98 (Hill-1 1.54) and gives G Hill-1 1.98 with pass >= twin. HR: forcing top-64 branches adds one KNOWN idea on 3
    units (T10 BFS, B3 array Prim, B6 alphabet scan), each ~2e6-5e7 T=1 samples away; 0 novel among 5,543 correct programs
    (2 counting-sort variants adjudicated by two gated judges + manual read). Blind T=1 locator finds B3's fork exactly on
    3/6 paths and nothing on collapsed T10. F8: post-decision final-norm states cluster by algorithm; fork-dosed slots land
    on their own class (nearest-centroid 0.69-0.975). Files: method.py (all stages), src/ (engine with per-step dose scheduler,
    analysis), data/samples.jsonl (3,231 programs) and continuations.jsonl (6,772), predictions/ (commits), results/ (k1_cells,
    k1_verdict, amendment, hr, locator, novelty_audit, positioning, rederive, rederive_tests, deviations), figures F1-F8,
    method_out.json (exp_gen_sol_out: k1_cells, k1_tokenmap, k1_locator, hr_branches, novelty_audit), README.md, reproducibility.md.
    Headline numbers independently re-derived (stdlib scripts; placebos fail).
  workspace: >-
    /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_39
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 8
  name: gen_art_experiment_40
  type: experiment
  title: Searching for a hidden algorithm switch in code models
  summary: >-
    Iteration-8 test of claim K2: is there a certified low-rank causal variable for the algorithm a code model picks? One
    DAS protocol was committed before any GPU use (commit #0, hash-chained, 8 commits verified): linear orthonormal map (ranks
    1/2/4/8), bounded KL objective, class-margin readout at the decision token. It was applied at three sites: Qwen3-8B T10
    connected components (BFS/DFS/union-find, token 11 after ' def'); gemma-3-4b-it T1 grid (BFS/DFS only; A* and IDDFS failed
    adherence); and the Qwen T10 task band (blocks 12-23, one shared map). There were seven committed controls (c1-c7). RESULT:
    K2 DISCONFIRMED (p_K2 = 0.037). T10 decision site (rule-chosen L* = 22, k* = 4): TF recovery 8.43, OFF-MANIFOLD (DAS Delta
    17.4 vs full-state 2.1 nats). c2 label controls keep 0.87/0.63/0.77 of the effect (limit 0.10); c3 random-init 0.69 (limit
    0.25); c4 and c5 fail; c1, c6 and c7 pass. In generation (CRN, N = 30, hidden tests), DAS writes 29/30 correct DFS (full-state
    2, random 0), but BFS edits yield 29/30 BFS attempts with only 5 passing tests, so the pooled verdict is NO HANDLE. GRID
    decision site (L* = 16, k* = 4): TF 3.07, OFF-MANIFOLD; c2 0.11-0.20 (2-class shuffles), c3 0.41, c5 and c6 fail; generation
    BFS 22/30 vs full 10, random 5, base 6 (SUFFICIENT HANDLE). T10 band (k* = 2): TF 0.82, c3 passes (0.18), c4 passes, c2
    fails (0.71-0.79), c5 fails on twins (passes c5b), c7 fails; generation BFS 28/30, but DFS sources are routed to BFS (24/30).
    Post hoc, block 24 (full state carries 16 nats): recovery 1.22, c4-c7 pass, yet c2 (0.50-0.61) and c3 (0.54) still fail,
    so the specificity failure is not an artifact of the rule-chosen block. Mediation of iteration 4's 40 random pushes: retrospective
    Spearman 0.39 (bar 0.5), prospective 0.09 on 24 new directions. Clamping the band subspace removes -0.01 of escapes (random
    clamp 0.02; decision-site clamp -0.05). Pushes act elsewhere. No novel algorithm: 0 'other' among 1,857 correct programs.
    Geometry figures plot actual R_8 activation coordinates (MDS/Isomap plus PCA). Placement prompts (seeds, novelty instruction,
    Gemma top-5 ban) stay inside the twin cluster. Provides: method_out.json (exp_gen_sol_out; 8 datasets, 2,042 examples:
    per-slot generation labels, per-pair TF Deltas, mediation slots); results/*.json; results/summary.md; das_maps/ (all fitted
    maps); data/ (samples, labels, TF rows); figures F1-F5; audit/rederive.py (stdlib; 38 checks all match, placebos fail;
    c3 recomputed only from stored means); reproducibility.md. Departures: NVIDIA L4 instead of A4500; B3 and the Gemma band
    dropped; band fits 109 steps and 2 seeds; S2 engine check not run; judge not called on labeller disagreements.
  workspace: >-
    /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_40
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 8
  name: gen_art_experiment_41
  type: experiment
  title: Qwen3-8B Algorithm‑Choice Circuit Findings
  summary: >-
    This artifact contains the Python driver (method.py) and three JSON result files (full_method_out.json, mini_method_out.json,
    preview_method_out.json) documenting the initial stages of a circuit‑discovery experiment for Qwen‑3‑8B (bf16, thinking
    off). The method script outlines the experimental pipeline, including hardware setup, contrast generation for two decision
    tokens (C1: Kruskal vs. Prim after a 61‑token opening; C2: find vs. dfs at token 11), GPU‑based attribution screening,
    exact noising/denoising, path‑level patching, and validation via ablation and steering tests against matched random components.
    The JSON outputs share a common metadata block describing the model, timestamp, and baseline comparisons (matched random
    components, RAND5, and an unedited “twin” run). The core results section reports a contrast metric C1nat_sd_m_v = 0.3379592507008036
    and provides a sample of token‑pair contrasts (e.g., "W1|guy" vs. "W1|mother") with measured token logits, total effect
    (TE) values, and the model's predicted probabilities for the Kruskal (p_kr) and Prim (p_prim) tokens in both clean and
    corrupted contexts. Aggregated statistics for the C1nat contrasts are included: mean TE ≈ 0.893, TE standard deviation
    ≈ 0.377, and the count of TE values exceeding a minimum threshold (n_TE_gt_min = 15). The preview and mini JSON files
    repeat the same top‑level data, offering truncated versions of the full output. No further analysis, figures, or final
    verdicts are present in the provided excerpts; the experiment appears incomplete, awaiting later stages such as top‑10
    node validation, generation steering tests, motif comparison with Gemma, and final verdict compilation.
  workspace: >-
    /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_41
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
- iteration: 8
  name: gen_art_experiment_42
  type: experiment
  title: Fair test of Gemma's BFS steering dial
  summary: >-
    Claim G (review items 3 and 5), gemma-3-4b-it bf16, T1 grid-path task, one fork; 1,320 programs on iteration 7's 50 CRN
    slots (RTX 4090), labelled by the frozen exp8 T1 labeller, with hash-chained commits #0-#4 before each sample batch. (1)
    PREFILL-MATCHED PROMPTING COLLAPSES: the forced-BFS prompt with the c* prefill (G1a) writes BFS 50/50 but 0/50 correct
    (pass 0.00), as does the best alternative wording (G1d). c* is off-policy under that prompt (log P(c*) -11.3 to -14.1
    nats vs -0.11 to -0.17 under twin and forced-DFS prompts), so the fork token becomes ' queue' (p 0.96-0.998), whose list
    BFS lacks the start/goal wall check and fails the hidden wall case (wrong answer, not timeout; corrects iteration 7's
    'too slow'). Commit #1's teacher-forced account predicted 1.0/50 correct before sampling; committed P1 (>= 40/50) fails;
    P1b outcome: DIAL BEATS MATCHED PROMPTING, prefilled DAS 39/50 vs 0/50 (39/0 discordant, exact McNemar p = 3.6e-12). (2)
    FREE-GENERATION DIAL WORKS (P2 holds): decision position committed from the free twin (47/50 slots reproduce c*, 3 not
    reached); free DAS r4 lam1 at block 17 gives 38/50 correct BFS vs free twin 13/50 (26/1, p = 2.1e-7), pass 0.78 vs 0.88
    (Newcombe -0.22 to +0.01); not distinguishable at N = 50 from the prefilled dial 39/50 (p = 1.0); all 4 free DAS cells
    beat the twin (Holm <= 2e-5); held-out W4/W5 + 30 fresh slots 33/50 vs 11/50; seed-2 map 41/50; RAND rank 4 null (11);
    matched DiM 0/50, pass 0.00 (P6). Toward DFS: 47-50/50. (3) IN FREE GENERATION THE DIAL DOES NOT BEAT PROMPTING: vs the
    committed free prompt G1c 32/50, 11/5 discordant, p = 0.21; exploratory 8 wordings give 14-49 (mean 39.5), best wording
    F3 beats the dial 49 vs 38 (p = 0.0034, Holm 0.024). Interaction (dial - prompt | prefilled) - (dial - prompt | free)
    = 0.66 [0.50, 0.82]. (4) DORMANCY (rule shared with Qwen3-8B): DORMANT/OFF-MANIFOLD HANDLE at k = 1,2,4,8 via retention
    only: on the top-64 PCs of the 120 twin states the map keeps 0.28/0.23/0.21/0.18 (residual 0.51-0.55); reverse recovery
    1.53/1.74/2.13/2.39 (Haar null ~0); forward 2.04/2.36/2.54/2.79; natural variance low at k = 1,2,4 (iteration 7 reproduced
    to 1e-9). Sensitivity with the 40 forced sources: retention 0.62/0.53/0.46/0.39, residual ~0, variance ~50x random p95,
    so the subspace is off the twins' manifold but inside the prompt-induced one. Reverse generation undefined (full-state
    swap restores 0 DFS). (5) Layer sweep (exploratory): a block-17 full-state transplant gives p(' queue') 0.55, the DAS
    edit 0.006-0.07 at the same ~12-nat margin, DiM 0.94-0.98: the subspace moves BFS vs DFS, not the prompt's implementation
    choice. No correct 'other' program among 913 (rule-of-three 0.0033). Audits: rederive.py 139/139, rederive_raw.py re-scores
    the headline cells from raw text identically, chain/order OK. Files: results/analysis.json, dormancy.json, layer_sweep.json,
    data/samples.jsonl, figures F1-F7, method_out.json (exp_gen_sol_out). OpenRouter USD 0.0042.
  workspace: >-
    /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_42
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 8
  name: gen_art_experiment_43
  type: experiment
  title: Predicting how temperature shifts code ideas
  summary: >-
    Iteration-8 claim L (pre-registered, hash-chained): a frozen law over one or two blindly located decision tokens predicts,
    before any temperature sample, the attempted-algorithm distribution of sampled programs at T 0.3/0.7/1.0/1.3 (top-p 1
    and top-k 10, N = 100 same-stream slots per cell). Units scored: Qwen3-8B A3 trapped rain water, B6 valid anagram, B3
    MST weight (law-development); held-out gemma-3-4b-it T04 substring search and R6 first/last position, Llama-3.1-8B-Instruct
    T1 grid path (Llama bench units T03/T06 selected then dropped under the plan's time box). Result: claim L PARTIAL. 5/6
    units pass (MAE <= 0.10, H <= 0.3 bits): A3 0.029, B6 0.054, B3 0.043, G-T04 0.033, G-R6 0.014; L-T1 fails 0.142 (decision
    token ' visited'/' queue' exists but its openings cover ~2% of programs; at T 1.3 Llama programs degenerate, 72/100 hit
    the cap; adjudicated labels primary). Held-out 2/3 pass but only 3 held-out units scored (< 4 required), so the held-out
    criterion is underpowered; no disconfirmation. Rivals: flat B0 (fit-twin shares), algorithm-level tempering B1, single-decision
    B2, entropy-located BH; the law beats B0 on 4/6 (sign test p = 0.34), B1 5/6, BH 5/6; the second decision matters on R6
    (B2 0.051 vs 0.014, bootstrap CI excludes 0) and A3. Decision tokens found blind: G-T04 'for'/'try' at generated token
    31; G-R6 'first' at 12 plus second decision at 24 ('for' vs 'left'); A3 ' n'/' left' at 18 plus ' ='/'_max' at 19; B6
    count branch ' ='/'_s' at 24 plus '{}'/'[' at 26; B3 ' Kr'/' Prim' at 61 (iteration-7 forks recovered). Per-slot replay
    names the algorithm of 0.87-1.00 of on-opening slots; top-k 10 is token-identical to top-p 1 on Qwen/Gemma (6/2,400 programs
    regenerated). B3's iteration-7 T-1 lean (0.40) was a stream artefact: fresh 25/100 vs predicted 0.23. Base sub-arm (Qwen3-8B
    vs Qwen3-8B-Base, identical ids): committed prediction holds - decision margins gain 3.27/13.41/2.11 nats on T1/T10/T2
    while phrasing-position entropy differs by 0.23-0.31 nats; JS divergence 6-10x higher at decision than phrasing positions;
    the base fork would give Prim 0.68 on B3 (instruct Kruskal 0.78), so the default is not the base model's mean. Novelty:
    0 novel among 4,703 correct programs (10 distinct off-catalogue programs read; rule-of-three bound 0.0006). Answer to
    the 1a-c question: tight T gives ~1 idea with 1-4 phrasing clusters; loosening T moves mass to the 2nd known idea at the
    predicted rate and multiplies its phrasings, never adds ideas. Files: method.py (entry), src/ (engine8, gpu8 locator/law/sweep
    driver, predict8 law + unit tests U5-U11, analysis_L scoring, base_arm, novelty8 judges), predictions/ + commitments.log
    (13-link hash chain: COMMIT #0, per-family #1/#2, amendments 1-4), data/samples_raw.jsonl (every program with seed/cell),
    data/continuations.jsonl (14,756 locator/forced continuations), results/ (per-unit locate/predict/sweep JSON, analysis_L.json,
    verdict.json, base_subarm.json, novelty_audit.json, deviations.json, positioning.json, summary.md), figures F1-F6, audit/rederive.py
    + audit/sign_test.py (stdlib re-derivation: 0 mismatches; placebos fail). Caveats: Llama labels noisy (re-gate 0.10/0.71
    on bench units), Llama top-k shadow validation failed (1/20), engine checks vs earlier GPUs 0.92-0.98, several locator
    bug fixes committed as amendments before the affected samples.
  workspace: >-
    /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_43
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 8
  name: gen_art_experiment_44
  type: experiment
  title: Which open models obey a five-algorithm ban
  summary: |-
    Iteration-8 top-five ban study (gen_plan_experiment_6_idx7) on the T1 grid-path task, with four hash-chained commits in commitments.log.

    SCREEN: 8 new open-model configurations plus 2 carried rows. Each model's own baseline defines its banned set B_c, and for every configuration B_c = {BFS, DFS, IDDFS, A*, greedy best-first}. The literal five-name ban (iteration-2 templates W1-W3) was sampled N=50 per configuration (N=30 for C1).
    - Programs: scored on the 48-case hidden suite (plus the 41-case ITER1 suite) and labelled by the exp9 10-class runtime/AST labeller.
    - Adjudication: gated judges deepseek-chat-v3.1 9/10 and kimi-k2 10/10, third judge mistral-medium-3.1 9/10, plus executor manual reads.
    - Result: only C6, Qwen3-32B thinking on (DeepInfra fp8), clears the committed 0.20 bar, with 17/50 correct survivors = 0.34 (Wilson 0.22-0.48). The survivors are unit Dijkstra 6, Bellman-Ford/SPFA 7, random-priority search 2, random walk 1 and wavefront 1.
    - Others: C4 Qwen3-14B thinking on 0.14; C5 Qwen3-32B thinking off 0.08. Qwen3-8B thinking on (local vLLM FP8), Llama-3.1-8B, Qwen3-14B thinking off, gemma-3-27b-it, Qwen2.5-Coder-32B and the carried Qwen3-8B thinking off and gemma-3-4b rows are all 0.00.
    - Disobedience: banned BFS/DFS is re-implemented without naming it (55-100% name-free).
    - Cost of obeying: the ban raises C6 reasoning from 6.9k to 9.1k tokens and truncation from 7% to 46%.
    - Strictest reading: dropping BFS/DFS/SPFA-named 'other' survivors leaves C6 at 0.22. Catalogue-only survivors give 0.12.

    GEOMETRY on m* = C6. States come from unsloth/Qwen3-32B-bnb-4bit (nf4) with a truncated decoder (exact): S-mean over task-spec tokens of 300 forced prompts.
    - Layer: every block from 19 to 45 classifies the forced algorithm at CV accuracy 1.00, so L* = 31.
    - Manifold: PCA 32.4%/12.0%; MDS stress-1 0.42 (points) and 0.28 (centroids); Isomap components 8/3/1 at k=5/10/15, so the primary k is 15. Split-half reliability is 0.58/0.95/0.98.
    - Classes: unit Dijkstra is the farthest non-banned algorithm from the banned five (OPPOSITE, bootstrap-stable). Bidirectional BFS and bidirectional A* are EDGE.
    - Landing: the 6/6 catalogue survivors are unit Dijkstra, giving the verdict OPPOSITE. p_opp is 1e-4 under the U and F nulls and 0.057 under C; the algorithm-level permutation P is 0.20 (floor). The verdict is NOT robust (10/15 cells), and the pre-registered EDGE prediction is not supported.
    - Held-out confirmation (commit #4, frozen geometry, W4/W5/P6/P7, N=50): 21/50 survivors, 9/9 catalogue survivors are Dijkstra, verdict OPPOSITE, so CONFIRMED.
    - Quantisation check on Qwen3-8B: int8 and nf4 vs bf16 geodesic Spearman 0.954 and 0.916, class agreement 5/5, so the geometry is not precision-sensitive.
    - Ban-prompt states move toward the named banned IDDFS/greedy centroids, and Dijkstra is the farthest centroid from them.
    - M2: the label is decodable at p* (0.97) but not at the label-independent g16 (0.53).
    - Circle check: no loop at the centroid level.
    - Novelty: 0 novel among 27 audited correct programs.

    AUDIT: src/rederive.py (numpy only) finds 0 mismatches. audit_headlines.py reproduces every count, the Wilson intervals, g (1e-12), S and the exact uniform p (6.4e-5). In its placebos, random survivor labels reject at 5% (nominal), but shuffled point labels still reject 36% under the per-program null. The algorithm-level p = 0.20 is therefore the honest landing evidence. The landing is correlational only: iteration 7's pushes moved 0/300 programs.

    FILES: method_out.json (exp_gen_sol_out: tp_screen 1,109 rows, tp_geometry 300, tp_confirmation 50; metadata holds every analysis, commits and 20 deviations); data/samples.jsonl and data/raw_*/labelled_*.jsonl; results/*.json; figures F1-F8 in activation coordinates; predictions/commit1-4.json; cache/states/*.npz (kept on the run volume). OpenRouter spend: USD 1.53. Hardware: RTX 2000 Ada 16 GB.
  workspace: >-
    /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_44
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 9
  name: gen_art_evaluation_8
  type: evaluation
  title: Repairing the iteration-8 research record
  summary: |-
    Step 0 of iteration 9: a CPU-only repair of the iteration-8 research record (no model runs, USD 0). It provides report_corrected.md, the full report with 49 verbatim edits each tagged '(iteration-9 correction)', plus report.diff and corrections.json. corrections.json holds the edits and a 298-value ledger (147 MATCH, 151 NEW, 0 CORRECTED, 0 CARRIED), each value with a source '<artifact_id>:<path>#<key>'. The apply test passes; the whole-report residual-claim lint goes from 28 live hits to 0.
    0a: the layer-0 condition MLP's exact-0.00 held-out effect is an unapplied edit, not a failure. MeanCache only matches same-template pair prompts, and 0 of 10 held-out prompts share one; all 20 raw rows are exactly zero. The node is therefore untested held-out and rests on its 20 pair prompts (8.14 and 7.41 nats). The motif test reads different motif: condition share 0.01 against [0.21, 0.51] and depth 0.86 against [0.45, 0.80].
    0b: Qwen3-8B's fork is NO HANDLE. Toward BFS, 29 of 30 programs write BFS but only 5 are correct (pass 0.20 against 0.83; 5:0 against random, p 0.0625). Gemma's fork is a SUFFICIENT HANDLE (22 of 30).
    0c: scope is now stated per unit. The fork is above the twin's 90th percentile in 209 of 209 samples; the highest-entropy position hits it on 44/44, 32/39, 21/39, 2/50 and 0/37 slots. The temperature law's rivals stay close (flat law better on valid anagram, 0.030 against 0.054; tempering better on substring search, 0.023 against 0.033; sign test p 0.34).
    0d: new section 8.10b, a positioning table with references [142]-[146]. 11 neighbours were checked live on 2026-10-23: Cantarero et al. appear on two NeurIPS 2026 workshop posters; Sparse but Critical is ICLR 2026, MIB ICML 2025, Position-aware ACD ACL 2025 and Many Circuits TMLR 2026; 3 venues remain unverified.
    0e: the alias-named manifold was tested on iteration 8's stored geodesics (gates E1-E4 pass; E4 Spearman 1.000). Alias-level g against committed lexical overlap gives rho -0.61 at k15 (exact p 0.0093; template-bootstrap CI -0.71 to -0.59) and -0.77 at k10. The 5-centroid rho is -0.63 (p 0.133; floor 0.033). The within-algorithm stratified statistic is -0.12 (p 0.46); on BPE tokens it is -0.50 (p 0.057). Committed verdict: CONFOUNDED. Names and mechanisms are confounded on this manifold, and TP-G's name-free manifolds decide.
    0f: min-p, block-start and T 1.6 were not run on Gemma; EDT was run, but its 0.18 pass cost triggered a twin-level fallback.
    0g: 7 figure markers plus fig_alias_overlap, each with a six-field caption and sha256.
    Audits: audit/rederive.py (stdlib; 400 checks, 0 mismatches, 4/4 placebos fail) and audit/headline_rederive.py, which re-derives the headlines from raw rows; its placebos fail as required. Pre-commitment: predictions/commit_s0e.json and commitments.log, with 2 logged amendments that leave every statistic unchanged. Also provided: tables/*.csv, figures/alias_overlap.(pdf|png), figure_markers.json, and eval_out.json (exp_eval_sol_out; metadata sections 0a-0g).
    Next steps downstream: use report_corrected.md as the record; rerun the layer-0 node's held-out arm in BASE (B3); settle the edge/opposite question on name-free manifolds (TP-G).
  workspace: >-
    /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_evaluation_8
  output_files:
  - eval.py
  - full_eval_out.json
  - mini_eval_out.json
  - preview_eval_out.json
  - reproducibility.md
- iteration: 9
  name: gen_art_experiment_45
  type: experiment
  title: Do AI coders dodge bans by renaming algorithms?
  summary: >-
    TP-B iteration 9 experiment on the T1 grid-path task (solve(grid, start, goal)): is a prompt that bans a model's path-search
    repertoire by NAME (BFS, DFS, IDDFS, A*, greedy best-first) obeyed on names but not on mechanisms? PROVIDES: (1) method.py,
    a stage orchestrator over src/, including a name-blind expansion-order tracer v9 (src/tracer_v9.py, src/orderclass.py)
    that runs each program on 40 committed probe grids (probes/probes_v9.json) and assigns an order class (BFS/DFS/ID/HEUR/BIDIR/OTHER),
    a fine class, a FIFO flag and a data-structure signature. (2) method_out.json (exp_gen_sol_out; plus full/mini/preview)
    with 1,623 programs in 5 datasets: tp_retrace 580 (iteration 1-8 five-name-ban rows, configurations C1-C10), tp_cumulative
    600 (Qwen3-32B and Qwen3-14B thinking, cumulative bans k=1..5 plus held-out templates), tp_rotated 293 (N5 rotated five-name
    sets), tp_described 50 (name-free described ban), tp_scale 100 (gpt-oss-120b). Every example carries predict_name_label
    (iteration-8 labeller + gated judges), predict_runtime_class (iteration-8 name-free runtime label mapped to a coarse class:
    the primary mechanism label after the gate fallback), predict_order_class (tracer v9) and predict_lexical_L1/L2. (3) data/samples_v9.jsonl
    (new rows, reasoning kept), data/survivors_for_tpg.jsonl (survivor programs for TP-G), results/*.json (every analysis),
    figures F1-F8, and a sha256 hash chain of pre-registrations (commitments.log, 10 entries, verifies). RESULTS, independently
    re-derived (audit/rederive_headlines.py and audit/rederive.py: 0 mismatches; placebos fail as required): the tracer FAILED
    its gold gate (182/260 = 0.70 agreement vs a 0.90 bar; references 14/15; planted controls 9/9 by class, 8/9 counting that
    one control fails the 48-case suite), so the committed fallback applies and N1-N3 are DESCRIPTIVE. N1: lexical minus mechanistic
    compliance pooled over 10 configurations = 0.697 (runtime label) and 0.608 (tracer), positive in 10/10 configurations
    under both; a within-program swap placebo gives about 0. N2: C6 name-level survivors in a banned coarse class = 72/91
    = 0.79 (runtime label) but 39/91 = 0.43 (tracer). N3: k=5 lexical vs mechanistic (runtime) compliance = 0.89 vs 0.22 (Qwen3-32B)
    and 0.86 vs 0.10 (Qwen3-14B), Jonckheere-Terpstra p about 1e-5 for both. N5: joint sign count 3/7 (disconfirmed). NOT
    independently re-derived: the executor's manual reads (0.30 of 76 k=5 survivors in a banned class; they agree with the
    tracer on 0.88), the N3-D and gpt-oss scale numbers, and the novelty audit (0 novel of 73). CAVEATS: the two mechanism
    instruments disagree on coordinate-key heaps and grid Bellman-Ford rounds; one task only; sampling via quantised providers
    is not byte-reproducible. Spend USD 3.889 (cap raised from 3.5 to 4.0; the USD 2.096 sampling share was re-derived from
    per-row costs). Inputs from prior artifacts are copied into inputs/ with SHA256SUMS; dependency paths come from $TP_DEP_<KEY>
    or a sibling folder named by artifact id (reproducibility.md). data/trace_cache/ (179 MB cache, stored as 5 parts of at
    most 45 MB read in order by gate_v9.trace_many) is excluded from publication.
  workspace: >-
    /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_45
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 9
  name: gen_art_experiment_46
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
    8B M-name OPPOSITE (rank 4/5, g/median 1.17), 8B M-desc OPPOSITE (rank 3/4, g/median 1.01), 8B M-code EDGE (rank 1/2,
    g/median 0.63). Reproduction: per-prompt cosine >= 0.9999, g within 0.030, classes identical, but committed gate Spearman
    0.894 < 0.95 (k10: 0.997; kNN tie flips), fallback F1. Lexical: Spearman(g_alias, L1) on M-name -0.74 (k10) / -0.65 (k15),
    P4 True. RSA (exact 10! Mantel): M-name vs R_lex 0.46 (p 0.003), vs R_beh 0.24 (p 0.091); M-desc vs R_beh 0.12 (p 0.252);
    M-code vs R_beh 0.64 (p 0.018), vs R_surface 0.67 (p 0.010). Placement on M-code: LOO accuracy 0.85; uDij survivors EDGE
    15/15. Predictions pass: {'P1': False, 'P2': False, 'P3': True, 'P4': True, 'P5': None, 'P6': True, 'P7': None, 'P8':
    True}. Audits: rederive.py 0 mismatches, audit_states mismatches []. Geometry is correlational. OpenRouter USD 0.094.
    Files: results/n4_verdict.json, results/geometry_*.json, rsa.json, lexical_regression.json, placement.json, figures/ (PCA/MDS/Isomap
    in activation coordinates), method_out.json; cache/states/ (states + frozen geodesic graphs geo_*_k10/k15.npz for iteration
    10) stays on the run volume, not in the repository.
  workspace: >-
    /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_46
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 9
  name: gen_art_experiment_50
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
    cross-model activation patching at the fork, 20 prompts/unit, fixed batch shapes): on MST the 10 validated fork-stack
    nodes close 1.00 [0.96, 1.04] of the 2.06-nat gap but 50 write-norm-matched random late sets close a median 0.81 (p =
    0.45; R-pure p = 0.039); on CC the stack closes 0.45 [0.28, 0.57] of a 4.52-nat gap vs random median -0.22 (p = 0.020).
    Task-spec (SPEC) nodes close ~0; late MLPs (L26-35) carry the residual part redundantly; the fine-tuned unembedding alone
    accounts for 43% (MST) / 85% (CC) of the gap (CPU readout decomposition), which is why RS-fork(36) < 1. Committed verdict
    PARTIAL (Q1 fails on CC, Q2 on MST, Q3 holds), localisation 'distributed'. Generation (N=30 CRN slots/arm, frozen labellers
    + hidden tests): on MST one-token FSTACK patch gives 19/30 correct Prim vs 0/30 twin (McNemar 19:0, p=3.8e-6) but a matched
    random set also gives 19/30 (2:2) and FPD (base logits at the fork) 18/30; on CC only FPD moves the choice (18/30 DFS
    vs 1/30). B3: iteration-8 MeanCache bug confirmed (None on all held-out COND nodes); with interpolated means the layer-0
    condition MLP's held-out effect is 3.86 nats ablate (p=0.0625) / 3.85 steer (p=0.023), about half the pair-prompt values;
    the exp41 value reproduces to 0.096 (its engine changed after its rows). Kind-matched motif still differs on COND share.
    Outputs: method_out.json (370 examples: b1_forks, b2_tf, b3_heldout, b2_generation), results/*.json per-prompt rows and
    summaries, figures F1-F8 (incl. PCA of actual block-30 residuals), predictions/ commits, README with deviations. Activation
    caches (cache/, ~12 GB) are regenerable and excluded from upload.
  workspace: >-
    /ai-inventor/aii_data/runs/run_0oWBKrKEGsmU/3_invention_loop/iter_9/gen_art/gen_art_experiment_50
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 10
  name: gen_art_experiment_51
  type: experiment
  title: LLM search for new bin-packing rules
  summary: >-
    NOV-B1: FunSearch-style island search on online bin packing with Qwen3-8B-FP8 (vLLM 0.11, thinking off) as mutator, evaluated
    by the iteration-9 FunSearch harness (copied, sha256-verified, re-gated: G-HARNESS PASS, BF 5.37% OR3 / 3.98% Weibull
    5k, c12 3.11%, c14 0.68%, gate block identical to BP9). Arms at matched calls (C*=2,000 per arm and seed, seeds 0-1, lockstep
    lag-1 rounds of 25): T1.0, T1.6 (top-p 0.95), DTB (force a rank 2-8 token at the highest-entropy code token of the first
    48), RPB (random-position placebo), IDEA (one-sentence 'different idea' instruction); NS (no selection, 1,000 per seed)
    afterwards. Everything hash-committed (6 commits, hash chain). Results: V1 SUPPORTED - every core arm's best program beats
    0.8x best fit on both primary held-out sets (FSW5k/OR3 excess %: T1.0 1.53/3.55, T1.6 1.40/3.55, DTB 2.43/4.18, RPB 1.73/3.48;
    IDEA 1.85/3.38; NS stays at best fit 3.98/5.37; tuned ab baseline abFF(5,22) 2.14/3.06; c12 3.03/3.11). V2 PARTIAL - behaviour
    clusters (complete linkage, all pairs agree >=0.95 on 2,000 probe states) over 4,000 calls: T1.0 148, T1.6 373, DTB 446,
    RPB 212, IDEA 770; R1 (DTB/T1.0)=3.01 [2.66,3.43], R2 (DTB/T1.6)=1.20 [1.13,1.33] < 1.5, R3 (DTB/RPB)=2.10; DTB's best
    is the weakest on held-out; per-token and rarefied ratios agree (R2 1.08/1.15); 200 label shuffles never reach R1>=1.5.
    V3 - 211 candidates, 70 pass both held-out bars with max corpus agreement <0.9 (86-entry corpus: textbook, Sum-of-Squares,
    FunSearch, EoH x60, ReEvo, HSEvo, MCTS-AHD, LLM4AD, ab family + tuned ab; also all 3,843 ab-grid points), 53 joint clusters,
    30 audited. Judge gate unmet (mistral 9/10, deepseek 5/10, kimi 6/10), so the arm-blind manual read decides: 22 reduce
    to the known ab principle (tight fit else avoid medium leftovers, b tied to item size); 8 NOVEL (gate-passing judge agrees
    8/8, advisory majority 5/8), all one idea family: prefer a leftover that is a whole multiple of the item size (T1.0 2,
    DTB 4, IDEA 2; caveats: the 0.9 probe filter did no work - positive control 70->70; one novel program is stochastic; no
    ablation of the modular term). V5 (descriptive): reversion at birth tokens 0.40 vs controls 0.36, sign test p=0.49. V6
    PARTIAL: rename rate IDEA 0.44 vs T1.0 0.86. Evaluator effect: NS never beats best fit. Provides method_out.json (exp_gen_sol_out:
    every call with code/F/cluster, best programs, V3 candidates, corpus, V5), results/*.json, figures F1-F8, data/main and
    data/ns raw rows and decision vectors, audit/rederive.py. OpenRouter spend $0.14.
  workspace: >-
    /ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_51
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 10
  name: gen_art_experiment_52
  type: experiment
  title: Can guided LLM search invent bin-packing rules? (run 2)
  summary: >-
    NOV-B2 is the pre-registered, independently implemented replication (seeds 2 and 3) of a FunSearch-style island search
    on online bin packing with Qwen3-8B-FP8 (vLLM 0.11, thinking off) as the mutator, plus an exploratory, separately pre-registered
    extension on seeds 4 and 5. Harness: FunSearch's exact priority harness, sha256-verified and re-gated (BF 5.37%/3.98%,
    c12 3.11%, c14 0.68% reproduced). Arms at matched calls (C* = 2000 per arm-seed, committed rule): T1.0; T1.6 with top-p
    0.95; DTB (force a rank-2..8 token at the highest-entropy eligible position of the first 48 body tokens); RPB (same forcing
    at a random position, placebo); IDEA (instruction to use a different idea); NS (fixed FF/BF parents). Selection on SEL-OR+SEL-W;
    held-out H-FSW5k and H-OR3 (primary) plus 6 sets. Behaviour = bin choices on 2,000 committed probe states; clusters by
    complete linkage at 0.95; novelty = agreement < 0.9 with 82 corpus programs (FunSearch, EoH, HSEvo, MCTS-AHD, ReEvo, LLM4AD,
    RAISE, textbook, dependency scan) and all 3,843 ab-family members, then gated judges and an arm-blind manual read. Verdicts
    (seeds 2-3, all re-derived by a separate stdlib audit): V1 PARTIAL - best-program held-out excess H-FSW5k/H-OR3: DTB 2.395/3.852%,
    RPB 1.720/3.703%, IDEA 2.133/3.554% pass the 0.8xBF rule; T1.0 3.672/4.821% and T1.6 (= BF) fail. V2 PARTIAL - behaviour
    clusters per 2,000 calls (seed 2/3): DTB 230/143, RPB 269/233, IDEA 134/150, T1.0 13/8, T1.6 1/1; R_T1.0 17.8, R_T1.6
    186.5, but R_RPB 0.74 < 1.2; shuffled-arm placebo 0/200 supported. V3 DISCONFIRMED - 151 candidates, 50 pass the 0.8 rule,
    48 also pass the corpus-novelty filter, 0 of 40 judged are NOVEL (all recombine published principles: BF on near-exact
    fits, an avoided residual band as in ab/c12, a residual target ~c*item as in EoH run 3/MCTS-AHD); rule-of-three bound
    7.5%; no judge passed its 10-control gate (judges advisory). V6 PARTIAL - rename share IDEA 0.670 vs T1.0 0.959. V5 (descriptive,
    n=30): forcing the argmax back at the offspring's high-entropy deviating token reverts it to a parent in 49.8% of continuations
    vs 25.5% at random positions (sign-flip p=0.0086). Exploratory seeds 4-5: V2 rule SUPPORTED (R_RPB 1.47) but pooled 4-seed
    R_RPB = 1.08: entropy targeting is within seed noise, while forcing (or the IDEA instruction) beats temperature robustly
    (pooled R_T1.0 25.5). The tuned ab member ab-FF(5,22) (F 0.740 vs best searched 0.726) beats every arm's best on H-OR3.
    Provides: method.py + src/ pipeline, 42,000 logged programs with evaluations and decision vectors (data/), all analyses
    (results/), figures F1-F7, commitments.log hash chain, method_out.json (exp_gen_sol_out) with full/mini/preview, audit/rederive.py.
  workspace: >-
    /ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_52
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 10
  name: gen_art_experiment_53
  type: experiment
  title: Token forcing vs temperature in LLM search for TSP heuristics
  summary: >-
    NOV-T experiment (claim V4): does decision-token branching (DTB: force a rank-2..8 token at the highest-entropy code position
    of the first 48 body tokens, then continue at T 1) make an LLM program search find more distinct heuristic behaviours
    than temperature? Task: constructive TSP with the ReEvo/EoH select_next_node interface; Qwen3-8B-FP8 on vLLM 0.11 (NVIDIA
    L4) mutates programs in a FunSearch-style 5-island search seeded with nearest neighbour (NN); fitness F normalised to
    NN on 64 selection instances (n 50/100) against LKH-3 tours. Arms at matched calls in interleaved rounds: T1.0, T1.6 (top-p
    0.95), DTB, RPB (random-position placebo), IDEA, plus NOSEL (no selection); seeds 0 and 1; 1,056 calls per arm-seed (hard
    stop below the committed C*=2000), 10,812 calls total. Behaviour instrument: next-city decisions on 2,000 frozen probe
    states, complete-linkage clusters at agreement >= 0.95. RESULTS. V2-T DISCONFIRMED by the pre-registered rule: clusters
    per 1,000 calls T1.0 228/234, T1.6 88/104, DTB 228/217, RPB 237/233, IDEA 296/298 (seed 0/1); pooled DTB/T1.0 = 0.963
    (kill condition <= 1.0), DTB/T1.6 = 2.315 (T1.6 validity 0.31-0.32), DTB/RPB = 0.948; per-seed DTB/T1.0 1.00 [0.89,1.14]
    and 0.93 [0.83,1.02] (round-block bootstrap); no sign reversal in secondary (better-than-NN), per-token, rarefied or pooled-linkage
    sensitivities. DTB's held-out best is worse than T1.0's (paired +1.2 and +2.7 gap points). V1-T SUPPORTED: every core
    arm-seed best closes >= 20% of NN's held-out n=200 gap (NN 23.94%, bar 19.15%; bests 13.98-16.68%), confirmed on 96 extra
    n=200 instances and 13 TSPLIB optima. Comparators on the same instances: ReEvo/EoH seed rule 13.67% (no searched program
    beats it), MCTS-AHD appendix heuristics 14.01-20.82%, tuned parametric P1 17.35%, NOSEL best-of-252 27.87%, farthest insertion
    8.65% (other interface). IDEA gave the most clusters and a 6% parent-rename rate (T1.0 18-22%). V3-T: 32 candidates beat
    0.8xNN and agree < 0.90 with every corpus member; judges failed their gates (8/10, 5/10); manual read: 12/12 read are
    KNOWN FAMILY, NEW PARAMETERS, 0 novel. AUDIT: audit/rederive.py (stdlib, separate code path) reproduces all 10 cluster
    counts exactly, the ratios, G200 means and both verdicts; its placebos (shuffled arm labels, DTB/T1.0 swap, thresholds,
    NN replaced) fail as required; 50/50 logged forcings re-derived. Pre-registration: COMMIT #1 (protocol, predictions, code)
    before the first search call, COMMIT #2 (C*), COMMIT #3 (corpus), hash-chained in commitments.log. FILES: method_out.json
    / full_, mini_, preview_ (exp_gen_sol_out: novt_calls one row per call with DTB/RPB fields, novt_best held-out bests vs
    NN/P1/T1.0/T1.6, novt_clusters), results/*.json (verdict_v1, verdict_v2, clusters, heldout, corpus, v3, judges, rederive,
    deviations), figures F1-F6, data/calls.jsonl (all programs and scores), data/requests/ (raw top-20 log probs), data/probe_decisions.bin.
    Deviations: L4 instead of A4500, torch.compile engine mode, C* not reached at the hard stop, title-level positioning only
    (results/deviations.json).
  workspace: >-
    /ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_53
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 10
  name: gen_art_experiment_54
  type: experiment
  title: Do banned bin-packing rules come back renamed?
  summary: >-
    NOV-R experiment (plan gen_plan_experiment_4_idx4), 1,143 one-shot online bin-packing priority functions in the exact
    FunSearch interface from Qwen3-8B (no thinking, local vLLM FP8, N 50 per cell), Qwen3-14B and Qwen3-32B (thinking, OpenRouter
    DeepInfra fp8, N 30 per cell after the reduction ladder). Cells: BASE, cumulative name bans of each model's own top-k
    textbook rules (NAME_1..5, templates W1-W3), a described ban (DESC_5), held-out templates (HOLD_5), and two novelty instructions
    (INSTR_NEW, INSTR_LONG). Baseline instrument = lexical compliance L1 (no banned name or abbreviation in the program);
    proposed instrument = mechanistic compliance (exact-decision agreement < 0.95 with every banned rule on 2,000 committed
    probe states, plus a stochastic random-fit matcher), gated beforehand on planted controls (min margin 0.49). Results:
    P1 PARTIAL. The renaming gap appears only without thinking: Qwen3-8B k = 5 gap L1 0.91 vs mechanistic 0.51, +0.40 [0.21,
    0.55] (paired Newcombe), and at k = 1, 14 of 35 lexically clean programs (0.40) are still best fit under another name.
    Qwen3-14B/32B really leave the banned rules (mechanistic 0.93-1.00; gaps +0.04 and -0.13, CIs span 0), and their traces
    name the banned rule in 100% and self-identify near it in 90-100%. Under a BF ban Qwen3-32B switches to first fit in 14/30.
    JT trend p = 0.54 / 0.038 (Holm 0.11) / 0.38; held-out-template gaps are not significant. The verdict is unchanged at
    thresholds 0.90/0.98 and on informative states. P2 DISCONFIRMED: only first fit's description passed the naming check
    (models call the other descriptions 'First Fit Decreasing'), so DESC_5 bans FF only, and compliance is about 1.0 either
    way. P3 SUPPORTED: 0/1,143 programs beat best fit on both held-out sets (FunSearch OR3, Weibull 5k); 186 are behaviourally
    novel vs the 426-member published corpus, but none is better. The novelty instruction 'Make a new algorithm' gives best
    fit in 28/29 (14B) and 28/28 (32B). BASE is almost all best fit for the thinking models (50/50, 48/49). Independent stdlib
    re-derivation (audit/rederive.py): 0 mismatches across agreements, classes, lexical flags, cell counts, JT, both Newcombe
    intervals and the verdicts; all 4 placebos fail as required. Files: method_out.json / full_ / mini_ / preview_ (exp_gen_sol_out:
    novr_samples with predict_mechanism_class, predict_lexical_L1, predict_mechanistic_compliance, predict_valid, predict_better_heldout,
    predict_novel; novr_cells; novr_instrument; metadata with every analysis), data/samples.jsonl (shared schema), data/samples_raw_*.jsonl
    (responses and reasoning), data/decisions.jsonl, results/*.json, figures F1-F6 (including the MDS behaviour map in decision
    space). Caveats: one model family (Qwen3); the container crashed at 4.2 h and sampling resumed at 5.9 h. A duplicate orchestrator
    ran for 40 min: 5 duplicate rows were removed, the naming check was rerun cleanly and committed as commit #3 before the
    DESC_5 rows it governs, and the commit #2 payload files of q14/q32 were overwritten after hashing (chain lines intact;
    B_k identical in every version). Spend USD 1.42.
  workspace: >-
    /ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_54
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 10
  name: gen_art_experiment_55
  type: experiment
  title: Do code-model maps track search order or storage?
  summary: >-
    TP-G2 (iteration 10; continues iteration-9 TP-G art_VVA3P0ocZNA2 / art_8nXdw3_lDAll). Qwen3-32B (OpenRouter, DeepInfra,
    thinking off; 1,138 calls, USD 0.25) wrote name-scrubbed grid path programs for a pre-committed 6x6 discipline x container
    factorial. Prompts named no algorithm (lint 0 hits). Verification: 48- and 41-case suites, AST container checks, tracer/runtime
    discipline checks and 139 executor hand reads. 24 cells, 287 frozen programs (12 per cell, RELAX-SET 11), plus 48 top-ups
    (BiBFS, IDDFS, BiA*, JPS; all JPS and half of BiA* are paraphrases of references). States: iteration 9's frozen readout
    R1 (mean over code tokens) under neutral-twin contexts; Qwen3-8B bf16 block 17 and Qwen3-32B NF4 block 33 via the exact
    truncated decoder; R0 gate reproduced iteration 9 bit for bit. G1 (partial Spearman, 1,000 program bootstraps, 2,000 within-stratum
    permutations): discipline given container rho_dc = 0.226 [0.186, 0.265] on 8B and 0.285 [0.252, 0.321] on 32B. Container
    given discipline is larger: rho_cd = 0.300 and 0.414, delta CI below 0 on both. Crossed 3x4 core: rho_dc 0.280 / 0.336,
    rho_cd 0.366 / 0.545. Baselines: bag-of-tokens E0 0.17 / 0.16; random-init RANDNET 0.07. Rank regression: token surface
    (0.32 / 0.41 semi-partial) and length dominate. Noise ceiling 0.94. Verdict INDETERMINATE: a real discipline signal (p
    = 0.0005, above E0 and RANDNET), but smaller than container and surface. G2 (iteration 9's kNN-geodesic landing on a 464-program
    frame; class LOO 0.68 / 0.83, chance 0.03): covert BFS/DFS programs of the five-name ban land on banned classes 0.99 /
    0.98 (P-COV, 12/12 robustness cells). Grid Bellman-Ford survivors land nearest RELAX cells 30/32 and 31/32; r_F is OPPOSITE
    on 32B and EDGE on 8B (P-BF met 8/12). Unit-weight Dijkstra lands nearest COST-HEAP. r_F is EDGE on full frames but not
    robust, and the HEAP frame flips OPPOSITE on 32B. The 8B contrast vs HEUR-HEAP is non-specific in the stdlib audit. r_F
    is EDGE for every family on 8B, including family-shuffle placebos, so it is uninformative there. Provides: method.py (stage
    orchestrator); src/ (cells, verifiers, generation, extraction, g1/g2, figures); data/ (all programs, hand reads, frozen
    sets); results/ (g1_*/g2_*/robustness/placebos/rederive JSON, pairs and class-distance CSVs for audits); figures F1-F8
    in activation coordinates; cache/states_v10/ (program states on the run volume, not published); hash-chained commitments;
    method_out.json (exp_gen_sol_out: tpg2_factorial 287, tpg2_topups 48, tpg2_placements 351, tpg2_g1_rows 39). Geometry
    is correlational: no causal or steering claim.
  workspace: >-
    /ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_55
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 10
  name: gen_art_experiment_56
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
  workspace: >-
    /ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_experiment_56
  output_files:
  - method.py
  - full_method_out.json
  - mini_method_out.json
  - preview_method_out.json
  - reproducibility.md
- iteration: 10
  name: gen_art_evaluation_9
  type: evaluation
  title: Correcting last round's report from raw data
  summary: >-
    Iteration-10 S0 record repair of the iteration-9 report (CPU only, no model calls, USD 0). Every number the blocking iteration-9
    review questioned (items 0a-0j) is recomputed from the three declared dependencies (art_8nXdw3_lDAll rename rows, art_VVA3P0ocZNA2
    geometry rows, art_cDba8_DycUJd base rows) and written as 27 verbatim old->new corrections tagged '(iteration-10 correction)'
    into report_corrected.md (Sections 9.2-9.9 and the closing; report.diff; corrections.json with a per-value ledger: CORRECTED
    10, MATCH 44, NEW 90, each with source artifact:path#key, script and output). Positive controls 7/7 exact (n3/n3_tracer
    cells, pooled gaps 0.697/0.608, all RSA rhos, b2 null medians, b3 means, placement edge counts). KEY RESULTS. 0a, Table
    431b (k=5 under every reading, paired Newcombe): Qwen3-32B mechanistic compliance 0.22 by the runtime label (gap 0.67),
    27/46=0.59 by hand reads (gap 0.30), 0.67 tracer (0.22), 0.74 fine tracer (0.15); held-out hand-read gap 0.396 < 0.4,
    so Qwen3-32B meets both committed bars only by the runtime label. Qwen3-14B meets the k=5 bar under every reading (runtime
    0.76, hand 0.73, tracer 0.61, fine tracer 0.49) but its held-out fine-tracer gap is 0.38 (20/50 vs lexical 0.78), so 'supported
    under all three readings' would be wrong. 0b: the registered fine-class sensitivity was a no-op in n3.json (12/12 cells
    identical); applied, Qwen3-32B k=4 is 22/46=0.48 (coarse 0.24) and 11 of 35 k=4 coarse violations are greedy best-first.
    0c: described-vs-named ban effect is instrument-dependent: +0.58 (0.39 to 0.71) runtime, -0.07 (-0.25 to 0.12) tracer,
    +0.05 fine tracer, +0.21 (0.02 to 0.38) per-cell reading; differences below ~0.2 are not resolvable at n~50. 0d: Bellman-Ford/SPFA
    survivors place opposite 15/15 on both gate-passing Qwen3-32B frames (6/15 on the failing second readout, 5/15 on Qwen3-8B);
    unit-weight Dijkstra survivors edge 15/15 on the primary frames, 10/15 programs-only; not preregistered, 'opposite' is
    relative to the median of two reference classes. 0e: named Qwen3-32B manifold R_DS 0.65 (p 0.001) vs R_lex 0.46, lex-DS
    r 0.13 (VIF 1.02), partials 0.502 and 0.675 (both permutation schemes, descriptive): language manifolds track lexical
    distance AND textbook data-structure attributes. 0f: layer-0 condition MLP held-out effect 7.90 (ablate) / 7.65 (steer)
    nats on the 5 forced prompts, about 0 on the 5 padded twins; 3.86/3.85 average both sides; five-contrast exact sign-flip
    p 0.031 one-sided (floor), 0.0625 two-sided; the 8.14/7.41 pair rule was recovered (MATCH). 0g: random sets repeating
    an MLP: MST R 1/50, Rpure 47/50, CC R 36/50, Rpure 50/50; CC fork-stack per-prompt mean share 0.13 vs ratio of means 0.45.
    0h: UD/IDA*/JPS-compliant pooled rename gap 0.662 vs 0.697; 294/371 covert programs are BFS/DFS. 0i: program probe 0.167
    = chance for six classes; 7 of 350 samples lost; Gemma grid base P 0.25, unmapped 0.663. 0j: harness gate MATCH from its
    files. 0k: ledger.json, 21 request parts (15 answered, 3 descriptive, 2 partly, 1 open in iteration 10), all 170 numbers
    found in report_corrected.md. PROOFS: apply test PASS; residual-claim lint 15 rules (20 hits on the original, 0 on the
    corrected copy); GRIM 76 checks, 0 failures; stdlib audit audit/rederive.py 861 checks, 0 mismatches, 6/6 placebos fail;
    second stdlib spot-check audit/spotcheck.py (reads samples_v9.jsonl, retrace.jsonl and the b3/b2 rows) 45/45 values match,
    its McNemar and pooled-gap placebos fail. Two reruns reproduce every table and text output byte for byte. NOT re-derived:
    JT p-values (at their permutation floor), stored 0i/0j values, the ledger (a synthesis). CAVEATS: hand reads are one reader's
    (a third reading, not gold); the tracer failed its gold gate so rename numbers are descriptive; partial-RSA p descriptive;
    no new sampling. FILES: eval_out.json (+full/mini/preview; metadata.sections 0a-0k, metrics_agg, 16 datasets), tables/*.csv,
    figures/ (fig_s0_kcurves, fig_s0_placement) with figure_markers.json, ledger.json, audit/, eval.py stage CLI over src/.
  workspace: >-
    /ai-inventor/aii_data/runs/run_5eGZGmskluur/3_invention_loop/iter_10/gen_art/gen_art_evaluation_9
  output_files:
  - eval.py
  - full_eval_out.json
  - mini_eval_out.json
  - preview_eval_out.json
  - reproducibility.md
</artifact_workspaces>

<data_files>
Data files come in three sizes:
- preview_*_out.json — READ THIS to inspect the data structure
- mini_*_out.json (~3 examples) — use for prototyping/testing
- full_*_out.json (complete) — use for the final production run. NEVER open it directly (too large to read into context). Instead, extract values programmatically with shell commands (e.g. grep) or a Python script (use aii-long-running-tasks skill for scripts).
</data_files>

<run_record>
The run's long chronological documents, as files: the internal research report, every round in
order, and each round's strategies, plans, reviewer verdict and hypothesis update. Open them for
what the artifact summaries do not carry — why a design was chosen, a citation, a reviewer's
objection, the scope a result holds under. They narrate the run; the artifacts are its evidence.

- /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_2_gen_paper_draft/run_record/run_report.yaml
- /ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_2_gen_paper_draft/run_record/iteration_records.yaml
</run_record>

<trajectory>
One line per iteration from the run's own trajectory log: the hypothesis state, the move it made,
the review score and whether anything executed. Use it to check that your reading of the run
matches what the run recorded. Its evidence_state and strand states are the loop's working labels,
each set against that round's own hypothesis and never re-graded against the whole run, so a
"strong_survivor" on the last round ranks nothing above an earlier round's replicated result:
grade the findings from the artifacts. None of it goes in the paper — it is process, and
<publishable_paper_rules> excludes process.

{"blocking": true, "candidates_considered": 12, "coverage": "full", "evidence_state": "lead", "hypothesis_title": "Prompt Bans Substitute, Not Just Subtract", "iteration": 1, "ledger_spend_usd": 0.18859018999999932, "move": "deepen", "results_executed": true, "results_executed_artifacts": ["gen_art_experiment_1", "gen_art_experiment_2", "gen_art_experiment_3", "gen_art_experiment_4", "gen_art_experiment_5", "gen_art_experiment_6"], "review_score": 4, "strands": [{"artifact": "art_j3Rm_lr2nzR6", "state": "broken", "why": "Delivered 61,469 source examples (20 LeetCode problems with parsed I/O) but no frozen bench: no specs, hidden tests, labellers or forecasts; it tested no claim."}, {"artifact": "art__skdlFp_o3e9", "state": "lead", "why": "Free-form stated alternative predicted both ban substitutes (log -0.085 vs uniform -1.52); preregistered Borda map 1/2 (-1.79); n=2 and associate = runner-up, so ladder untested."}, {"artifact": "art_D6Z0Snf09sFL", "state": "null", "why": "Share test null: ban shift at R 61-99% off mode axes (u_ren > null in 7/130 cells); affine ablation moved 0/50; geodesic kernel -1.43 vs -1.56 uniform, not separated."}, {"artifact": "art_1yV2vQ0EH4OY", "state": "lead", "why": "Ban opens the decision: ban paths decided at R 4-8/10 vs 10/10 baseline; 6 confirmed T2 forks (import, names); fork-T knob null; locus probe broken (ran before states saved)."}, {"artifact": "art_U5UKkFrOgSsE", "state": "null", "why": "Decommitment steering T2 +0.65 Hill equals random direction +0.59 (diff +0.07 [-0.26,0.39]); grid never moved; enumeration prompt no effect; ban moves R only 0.04-0.05."}, {"artifact": "art_HF8nK8B_Lqyy", "state": "lead", "why": "Base chat more diverse: weights effect -0.58 [-1.01,-0.15] / -0.93 [-1.38,-0.46]; base ordering predicted both substitutes; expected from prior work, judge-heavy labels."}, {"artifact": "art_UoCVh2Qe5RZ0", "state": "lead", "why": "Temperature = phrasing knob (797/800 BFS; clusters 4->36), a replication; seeds null; semantic seed moved T2 +66.3 pp yet R displacement predicted behaviour on neither task."}]}
{"blocking": false, "candidates_considered": 15, "coverage": "full", "evidence_state": "lead", "hypothesis_title": "Bans Remove the Default, Not Pick the Next", "iteration": 2, "ledger_spend_usd": 22.613629671116264, "move": "deepen", "results_executed": true, "results_executed_artifacts": ["gen_art_evaluation_1", "gen_art_experiment_7", "gen_art_experiment_8", "gen_art_experiment_9", "gen_art_experiment_10", "gen_art_experiment_11", "gen_art_experiment_12"], "review_score": 4, "strands": [{"artifact": "art_V1MvbYs5420o", "state": "lead", "why": "T2: 8/8 non-semantic pushes incl. random steering land on BF/SPFA like the ban (rival's top rung); locus probe found no locus; FW nearest Dijkstra 100%; no knob or family advances."}, {"artifact": "art_6zBfl3kDjeiP", "state": "broken", "why": "FRLP gate failed (default share 0.83; ESS<5 in 98% of cells); SHARE 0.55 [0.25,0.67] rests on tail cells; residuals point away from the realised substitute (BF/SPFA -1.84 vs Dial +6.07)."}, {"artifact": "art_8_ULPE8jJQc_", "state": "lead", "why": "Ban decided before writing via task-spec states: T2 behaviour prompt 0.98 vs direct 0.05; opening veto 0/100 vs 99/100 imports; T1 mixed (0.50/0.35); C5 rho -0.41 misses -0.5."}, {"artifact": "art_IVZc3TWCeE9f", "state": "lead", "why": "Top-5 landing degenerate (avoidance 0.00), but prompts reach one rung: FW 0/100 as sole survivor though forced FW 40/40 correct; multi-ban mix list-independent (p=0.48, post hoc)."}, {"artifact": "art_-QPYRaFERCBX", "state": "broken", "why": "FRLP gate failed (BFS 0.43 vs 0.77 sampled; median ESS 2.5; bootstrap var 5-11x replicate); C1 0.80 [0.28,0.94] fragile (0.41 w/o 5 programs); correct grid output BFS 20/20."}, {"artifact": "art_0ndRfWKBWclR", "state": "null", "why": "Presence pilot null for Qwen: collapsed 13/13 tasks (modal 1.00), no present-minor stratum; 12-task bench frozen and gated but no ban event run; Llama diversity mostly failing attempts."}, {"artifact": "art_3iv5G76C3yoX", "state": "null", "why": "SAE transfer failed (dCE ratio 1.59-3.29); latents never beat DiM; prime-veto 0/6; T1 not decodable within paraphrase; same-seed CRN ideas fixed (0/30 in 10/12 cells), as expected."}]}
{"blocking": true, "candidates_considered": 15, "coverage": "full", "evidence_state": "lead", "hypothesis_title": "Plan Nudges, Not Temperature, Move Ideas", "iteration": 3, "ledger_spend_usd": 40.196721356739154, "move": "deepen", "results_executed": true, "results_executed_artifacts": ["gen_art_evaluation_2", "gen_art_experiment_13", "gen_art_experiment_14", "gen_art_experiment_15", "gen_art_experiment_16", "gen_art_experiment_17", "gen_art_experiment_18"], "review_score": 4, "strands": [{"artifact": "art_3tH2xtoZ7Gj2", "state": "null", "why": "Record repair: likelihood gains name the landing 0/17 (0/11 distinct rows); no estimable 3-survivor row; 0 novel of 78 correct off-catalogue; BFS-BiBFS adjacency fails at g16."}, {"artifact": "art_1AYTO1Epb_7t", "state": "null", "why": "Ban-free forecasts fail: 5/12 bans gated; no family beats uniform (ladder +0.06, association -1.78); vetoes respelled on 9/12; 3/5 landings unforeseen; wording LR 374."}, {"artifact": "art_WiY4wqHLb9Gy", "state": "lead", "why": "Snap-back: default share 0.05 (copy) to 0.72 named, 0.82 unnamed; ladder beats association by 1.3 nats (Holm 0.081 named, 0.0056 unnamed); rests partly on one wording."}, {"artifact": "art_Q-qh-9HhPoWo", "state": "lead", "why": "Llama: no family advances; association hits 7/13 (ladder 6/13 without 'other'); associate gains +0.25 beyond veto on 2/6 present-minor bans; snap-back 0.72-0.93."}, {"artifact": "art__5akZ9W9iZM4", "state": "lead", "why": "Route task-dependent (F_prompt 0.61, F_direct 0.74; C2a fails); routes jointly pick the landing (components: each alone DFS, both BFS); forced body opening undoes ban 0.98-1.00."}, {"artifact": "art_pVlCZ272hDV7", "state": "lead", "why": "Prohibition direction = random (0/5), but random task-spec pushes buy correct diversity at ~0 pass cost: kth smallest 5/15 dirs Hill>=2 (max 2.92), two sum 2.13, shortest path 1.97."}, {"artifact": "art_ccAbfJVcv0LO", "state": "null", "why": "Token walk stalled 6/6 (exact veto, default respelled); 0 novel of 38 correct off-catalogue under long-form novelty; one-rung reach fails only where alternatives are interchangeable."}]}
{"blocking": true, "candidates_considered": 18, "coverage": "full", "evidence_state": "lead", "hypothesis_title": "Plan Nudges Reopen What Tuning Narrowed", "iteration": 4, "ledger_spend_usd": 48.77815808600678, "move": "deepen", "results_executed": true, "results_executed_artifacts": ["gen_art_evaluation_3", "gen_art_experiment_19", "gen_art_experiment_20", "gen_art_experiment_21", "gen_art_experiment_22", "gen_art_experiment_23"], "review_score": 4, "strands": [{"artifact": "art_sV0cQ3ef1ZRQ", "state": "lead", "why": "Frozen screen: movable vs obeying 6/0/0/8 and escape ranks catalogue-only ban avoidance at rho 0.86 (14 tasks); random pushes cheapest qualifying row on T03/T05. Screen data only."}, {"artifact": "art_mWn-MQEnNelg", "state": "lead", "why": "C1 PARTIAL: plan noise H5 2.72 vs 1.96 (kth smallest), 2.09 vs 1.96 (components) at 0 pass cost; loses find dup (1.00 vs 2.73), shortest path (1.35 vs 1.93); pooled -0.22 [-0.89,0.30]."}, {"artifact": "art_Cx9JOh8soBw7", "state": "lead", "why": "Prefill task-spec site beats read position at matched downstream displacement (OR 5.72 [3.94,8.30]); site rule PARTIAL 3/6; generated tokens 1-32 also redirect (find dup 12:0)."}, {"artifact": "art_Yu6GN6pLxW8f", "state": "lead", "why": "Same seed: temperature changes the algorithm in 0/20 seeds (3 tasks; T2 thinking on too); one plan direction 17.25/20 (T2), 4.55 (T03); contrast 0.545 [0.41,0.67]; PARTIAL."}, {"artifact": "art_SHaWv77P1XCI", "state": "null", "why": "C2a disconfirmed: subspace share ranks 40 fresh directions at rho 0.03; removing it keeps the effect (ratio 1.00); targeted push beats random only on components (48% vs 0%)."}, {"artifact": "art_k6nzFCDLOjQP", "state": "null", "why": "Gemma C3a inconclusive (BA 0.74, Fisher p 0.24), disconfirmed by default-drop (BA 0.57); 2 of 3 true positives compromised (tied grid, mislabelled T2); novelty predicts better."}, {"artifact": "art_kjrCpQnPaniY", "state": "lead", "why": "112/112 quotes verified; 0 of 63 scored records occupy; flags A/B not fired; C1 contrast set lacks text-level plan samplers (IFG, PlanSearch) and departure-matched decoding."}]}
{"blocking": true, "candidates_considered": 20, "coverage": "partial", "evidence_state": "lead", "hypothesis_title": "A Small Hidden Plan Picks the Algorithm", "iteration": 5, "ledger_spend_usd": 0.03262589999999932, "move": "cover", "results_executed": true, "results_executed_artifacts": ["gen_art_evaluation_4", "gen_art_experiment_24", "gen_art_experiment_25", "gen_art_experiment_26", "gen_art_experiment_27", "gen_art_experiment_28"], "review_score": 4, "strands": [{"artifact": "art_mgek9PfVBNbh", "state": "null", "why": "CPU audit: 35 corrections, 186 of 187 recorded values match, eight rival predictors frozen by hash; it tests no claim of the request."}, {"artifact": "art_CcZLW-9NX00l", "state": "lead", "why": "Transplant DISCONFIRMED 1/5; top-k frequent heap 21/49 vs 0/39 (44:0 at N=100) but pass 0.78->0.98; random beats base states on kth smallest 2:20."}, {"artifact": "art_8WbrpoEFslk9", "state": "lead", "why": "Movability rho -0.03 (null); landings 3/3 (p .019), but trapped rain water hit is the twin's own 0.36 minority; bf16 remeasure: only kth smallest, CC escape."}, {"artifact": "art_9a8LrIv2lHbV", "state": "lead", "why": "Movability rho 0.21 (null); landings 3/4 (p .081), XOR and Prim hits are twin minorities (4/50, 17/50); beta vs plan-noise excess 0.82 (p .017)."}, {"artifact": "art_jR6Pyy3W9xum", "state": "lead", "why": "Literal cell 0/20 seeds (done); base intent beats plan noise on 3/5 (CC 2.53 vs 1.09); PN beats matched decoding 19:3, 13:0 of it on kth smallest; bf16 PN near-inert."}, {"artifact": "art_hG0QPiaIPNhP", "state": "lead", "why": "Gemma landings 5/7 (p .025), but 3 hits are it-twin minorities, unconfounded 2/4 (p .42); movability rho .42 (p .06); transplant 2/7, both amplified minorities."}, {"artifact": "art_ObxQOIlAM9MS", "state": "null", "why": "Positioning audit: 137 quotes verified; transplant method occupied, base-variety premise contradicted in part (Lee et al.); it tests no claim."}]}
{"blocking": false, "candidates_considered": 14, "coverage": "partial", "evidence_state": "lead", "hypothesis_title": "A Hidden Plan Tilts One Deciding Token", "iteration": 6, "ledger_spend_usd": 4.938985615715657, "move": "deepen", "results_executed": true, "results_executed_artifacts": ["gen_art_evaluation_5", "gen_art_experiment_29", "gen_art_experiment_30", "gen_art_experiment_31", "gen_art_experiment_32"], "review_score": 5, "strands": [{"artifact": "art_aRTQM6CQ0Dre", "state": "null", "why": "CPU record repair: 36 corrections (78 match, power corrected to 0.63); blind re-adjudication finds 0 of 14 novel. Bookkeeping; tests no claim of the request."}, {"artifact": "art_lpQalcAXMGr1", "state": "lead", "why": "bf16 escapes on iter-4's 40 directions (CC 0.65 vs 0.725; SP 0.15 vs 0.20; rho 0.96/0.87), PN 25 vs 30 of 50: push handle is a model property; FP8 account refuted."}, {"artifact": "art_rMlbrjVB1c__", "state": "lead", "why": "Task-state exchange carries ban/instruction: SP 21/30 correct BF, forced 30/30, random <=0.13, read pos 0; P1 rule failed (two sum 0.43); site rule withdrawn."}, {"artifact": "art_zNyBP6zieI5u", "state": "lead", "why": "Gemma BFS/DFS set at one token (' visited' -> BFS p 0.011; newline/if/queue 0.95-1.0); SAE clamp < DiM; edits toward BFS break code; DAS lacks valid controls."}, {"artifact": "art_dbUtqBjT0tPf", "state": "lead", "why": "NLA names no plan pre-code (0/112; forced 0/7) but names it at the name token (80-89%); exploratory gen-site edit steers find-dup 0.28->0.76 (fresh 13:0), 2/4 tasks."}, {"artifact": "art_OUuQUYQn5voE", "state": "null", "why": "Positioning audit: 123 quotes verified; DAS method occupied, object open; NLA edit-and-steer occupied. Tests no claim of the request."}]}
{"blocking": true, "candidates_considered": 16, "coverage": "partial", "evidence_state": "lead", "hypothesis_title": "One Early Token Decides the Algorithm", "iteration": 7, "ledger_spend_usd": 21.429877102129087, "move": "deepen", "results_executed": true, "results_executed_artifacts": ["gen_art_evaluation_6", "gen_art_experiment_33", "gen_art_experiment_34", "gen_art_experiment_35", "gen_art_experiment_36", "gen_art_experiment_37", "gen_art_experiment_38"], "review_score": 4, "strands": [{"artifact": "art_LzP2qPwUrANz", "state": "null", "why": "CPU record repair: 54 corrections, 603 values match, 520 re-derivation checks with 0 mismatches. Bookkeeping that tests no claim of the request."}, {"artifact": "art_veI9l_Rb9wDY", "state": "lead", "why": "DAS rank 1-2 matches full state for ban sources (SP 12 vs 11/30, kth 26 vs 27), random <=1/30; but permuted labels 0.47-0.70, untrained 5.1x, reverse 0/30: a handle, not a variable."}, {"artifact": "art_pHL7LWNhpcCS", "state": "lead", "why": "Conn. components decided at tokens 10-11 (0 bits; forced 'def dfs' 30/30 DFS); fork margin 0.80 is an outcome readout; SP no early fork (0.15); axis disconfirmed; top-5 push 0/300."}, {"artifact": "art_MZAfDPVhM6Ui", "state": "lead", "why": "One-token fork on 3/3 mixed units (0.05-0.19 bits); T-law passes 1/3 (MST drop 17:0); collapsed margins 4.85-17 nats; task-state exchange 30/30, margin -4.9 to -22 nats."}, {"artifact": "art_8O5eaNc5gxJs", "state": "lead", "why": "Unit, not seeds: +0.45 [0.35,0.55] vs +0.03; top-quartile cells 29/50 vs rest 15/50, shuffled 4/50; repriced plan noise beats base intent on 2/5 only (3 predicted)."}, {"artifact": "art_VhaHGe7SxV95", "state": "lead", "why": "Search: 78 known-outside kth-smallest programs (12 clusters) vs 0 EAP, 2 instruction-only (7.8x, LB 2.41); 10x bar missed; SP critic gaming; 0 novel."}, {"artifact": "art_HY7uYZz-OjRW", "state": "lead", "why": "Gemma T-law MAE 0.026; fork DAS passes random/permuted/untrained but natural variance below random, dormancy unrun; dial 11->42/50 only with prefill; circuit 7-8/10 nodes."}]}
{"blocking": true, "candidates_considered": 14, "coverage": "partial", "evidence_state": "lead", "hypothesis_title": "Banned Models Rename Their Default Algorithm", "iteration": 8, "ledger_spend_usd": 28.791326887885624, "move": "cover", "results_executed": true, "results_executed_artifacts": ["gen_art_evaluation_7", "gen_art_experiment_39", "gen_art_experiment_40", "gen_art_experiment_41", "gen_art_experiment_42", "gen_art_experiment_43", "gen_art_experiment_44"], "review_score": 4, "strands": [{"artifact": "art_vjtPMtWGMjsB", "state": "null", "why": "CPU record repair: 84 corrections, 97 re-derivation checks, counting-sort relabel (kth recovery 1.59 to 1.01). Bookkeeping; tests no claim of the request."}, {"artifact": "art_vnyi0Fm5SyNH", "state": "lead", "why": "Fork dose hits composed mixes (MAE .010-.047, 5/5) and lifts anagram Hill 1.78 to 2.78 at 2 pts; collapsed CC fails (Hill 1.24/1.60 vs 1.8, p .30); forcing adds 1 known idea on 3 units."}, {"artifact": "art_e-_q5mSJGrSb", "state": "null", "why": "Matched DAS disconfirmed: label controls keep .11-.87 and untrained nets .41-.69 of the effect; Qwen fork NO HANDLE (BFS 5/30 correct); clamp removes 0 of 218 escapes."}, {"artifact": "art_18XvfcJJZi1O", "state": "lead", "why": "9/10 and 8/10 fork nodes beat matched random; top 5 vs random five 7:1 (p .07) and 0:1 at dose 2, 24:0 only at post hoc dose .5; motif differs; layer-0 held-out arm never applied (bug)."}, {"artifact": "art_FJMIE9T9_PMv", "state": "lead", "why": "Free dial 38/50 vs twin 13 (26:1), held-out 33 vs 11; but ties free prompting (32, p .21) and the best wording beats it (49); prefilled prompt 0/50 is an off-policy confound."}, {"artifact": "art_lzuosbrb34wB", "state": "lead", "why": "Law passes 5/6 units incl. held-out Gemma (.033, .014); Llama fails (.142); beats flat on 4/6 (p .34). Base fork margins +2.1-13.4 nats, partly occupied (Cantarero)."}, {"artifact": "art_R-HSmXq2t97f", "state": "lead", "why": "Only Qwen3-32B thinking obeys a 5-name ban (17/50; held-out 21/50); survivors all unit Dijkstra = 'opposite', but p .20, 10/15 robust, and the manifold is alias-named."}]}
{"blocking": true, "candidates_considered": 16, "coverage": "partial", "evidence_state": "lead", "hypothesis_title": "Knobs Reshuffle Ideas, Search Finds New Ones", "iteration": 9, "ledger_spend_usd": 42.53830617027609, "move": "cover", "results_executed": true, "results_executed_artifacts": ["gen_art_evaluation_8", "gen_art_experiment_45", "gen_art_experiment_46", "gen_art_experiment_50"], "review_score": 5, "strands": [{"artifact": "art_iYh9zVP7myjJ", "state": "null", "why": "CPU record repair: 49 corrections, 400 checks; alias test CONFOUNDED (alias rho -0.61, within-algorithm -0.12, p .46); confirmed circuit held-out edit never applied. Tests no claim."}, {"artifact": "art_8nXdw3_lDAll", "state": "lead", "why": "Rename gap .70/.61 pooled, 10/10 configs, but tracer failed gate (.70<.90); Q14 k5 gap robust (.62-.76); Q32 k5 gap .22-.30 by tracer/hand reads (<.4); rotated sets 3/7."}, {"artifact": "art_VVA3P0ocZNA2", "state": "lead", "why": "uDij opposite on named/name-only/described maps (1.63/1.20/1.08), edge on program map (.67; 15/15); BF/SPFA survivors opposite; program map tracks surface (partial beh .11)."}, {"artifact": "art_cDba8_DycUJd", "state": "lead", "why": "Gemma grid fork +1.78 nats, base reversed 20/20, JS ~ entropy-matched (.75-1.18x); fork stack 1.00 on MST but random .81; CC .45 vs -.22; FPD 18/30 DFS; held-out bimodal."}]}
{"blocking": false, "candidates_considered": 12, "coverage": "partial", "evidence_state": "lead", "hypothesis_title": "Knobs Reweight Ideas; Search Only Recombines", "iteration": 10, "ledger_spend_usd": 23.252333787492148, "move": "declare", "results_executed": true, "results_executed_artifacts": ["gen_art_experiment_51", "gen_art_experiment_52", "gen_art_experiment_53", "gen_art_experiment_54", "gen_art_experiment_55", "gen_art_experiment_56", "gen_art_evaluation_9"], "review_score": 5, "strands": [{"artifact": "art_k7A5-5vcXY1g", "state": "lead", "why": "Evaluator beats best fit held-out (T1.6 1.40/3.55% vs 3.98/5.37%; no selection never) but FunSearch-predicted; DTB/T1.6 1.20<1.5; 4 ablatable 'novel' programs keep gain without the term."}, {"artifact": "art_dq4MiqNM89Go", "state": "lead", "why": "0/40 novel; DTB/RPB 0.74 (0.61 without stochastic): entropy targeting adds nothing; 17.8x over T1.0 only because temperature copies parents; birth tokens .50 vs .26 (p .0086)."}, {"artifact": "art_Xt1OfbyR7Mvy", "state": "null", "why": "Operator kill condition met (DTB/T1.0 0.96, DTB/RPB 0.95); bests close 30-42% of NN gap but none beats the ReEvo/EoH seed rule (13.67%); 0/12 novel."}, {"artifact": "art_ZkX7AmcN4vDO", "state": "lead", "why": "Exact instrument: Qwen3-8B k=5 rename gap +0.40 [.21,.55] but +0.08 on held-out templates; thinking models obey (+0.04, -0.13); 0/1,143 novel and better than best fit."}, {"artifact": "art_ho7tqaOyBjkN", "state": "lead", "why": "Discipline|container 0.23/0.29 <0.3 bar and < container 0.30/0.41; covert BFS/DFS inside banned 0.99/0.98; BF survivors with relaxation 30/32, 31/32; uDij frame-dependent."}, {"artifact": "art_a7CQm-6CXmoJ", "state": "lead", "why": "Base fork rows close 0.548 of CC gap vs isotropic 0.044, but residual-subspace random edits match (p 0.37); dose-1 generation 5/30 < bar 10; late-MLP swap -0.145 vs early 0.461."}, {"artifact": "art_7KO_qYLRZxXL", "state": "null", "why": "Record repair: 27 edits, 861 checks, 0 mismatches, answering the iteration-9 review; an audit that tests no claim of the request."}]}
</trajectory>

<figure_rules>
This paper gets its OWN figure set, chosen for the argument it makes. The report's figures were
chosen for a different document and do not carry over; specify here only what this paper needs.
Put a [FIGURE:fig_id] marker in paper_text where each one belongs and give the full spec in the
`figures` structured-output array, in the order they appear.

- FIGURE 1 IS THE FLAGSHIP. The FIRST figure is a DATA figure showing this paper's ONE finding —
  the result the abstract leads with, plotted from the artifact's own numbers. Its marker goes at
  the END of the Introduction, so a reader who reads nothing else sees what the paper found. A
  Figure 1 that shows a side result, a setup, or a dataset summary is the single most common
  defect in a first draft.
- A CONCEPT FIGURE IS WELCOME AS THE SECOND. A method or architecture diagram — drawn by the
  image model, no dataset behind it — is encouraged wherever the method has parts a reader has to
  hold at once. Put it where the Method section introduces the thing it draws.
- EVERY OTHER FIGURE SERVES THE ARGUMENT. Before each one, say to yourself which claim it
  supports. A figure that illustrates something true but beside the point is cut; the report
  already holds it.
- TABULAR DATA IS A TABLE, NOT A FIGURE. When the point is the values themselves, write a
  markdown table in paper_text. A four-row result table redrawn as a chart loses the exact
  numbers and gains nothing.
- A CONCEPT FIGURE THAT LOOKS LIKE DATA SAYS IT IS NOT. A drawn network, map or snapshot is
  captioned as a schematic illustration; only a data figure may be captioned as the run's data.

FIGURE TYPE — set `figure_type` on every figure. One test decides it: does the figure plot
numbers?
  "data"    — bars, curves, scatter, heatmaps, confusion matrices, scaling laws, distributions,
              Pareto fronts, ablation deltas. Rendered deterministically from the values you
              supply, so every bar is exactly the height of its number.
  "concept" — conceptual artwork, architecture and flow diagrams, anything with no underlying
              dataset. Drawn by an image model.
If the figure has real numbers behind it, ALWAYS use "data". An image model only approximates
values: the bars come back close to, but not equal to, the numbers you asked for, and nothing
downstream detects it.

DATA FIGURES CARRY THEIR NUMBERS. The renderer cannot read files, so before writing a data
figure's spec, open the relevant workspace in <artifact_workspaces> and read the exact values out
of its output files. Every number, series name, axis label and unit goes in
`image_gen_detailed_description`, unrounded and exactly as the run produced it — and it must
agree with what the prose and any table say about the same result.

Set `aspect_ratio` per figure: 21:9 for architecture / pipeline / flow-chart diagrams, 16:9 for
side-by-side comparisons and multi-panel results, 4:3 for dense charts, 1:1 for heatmaps /
confusion matrices / scatter plots.

Example in paper_text:
  "...cutting tail latency by more than half.\n\n[FIGURE:fig1]\n\nSection 3 describes the planner..."

Example flagship entry in the figures array:
  {"id": "fig1", "title": "Latency across the three optimizers", "figure_type": "data", "caption": "Geometric mean query latency, with standard error over 40 queries. The learned optimizer is 2.3x faster than PostgreSQL's planner.", "image_gen_detailed_description": "Grouped bar chart. Categories: PostgreSQL, Bao, RLQOpt. One series 'Latency'. Values: 4.6, 2.8, 2.0 seconds. Errors: 0.8, 0.5, 0.3. X-axis label 'Optimizer'. Y-axis label 'Latency (s)', range 0-5.", "aspect_ratio": "16:9", "summary": "The paper's headline result"}
</figure_rules>

<artifact_links>
Every number and every claim that rests on an artifact gets an [ARTIFACT:artifact_id] marker
inline, right after it, naming the artifact whose files it comes from. The LaTeX step typesets this
draft alone, without the run's records, so these markers are how each number keeps its source; it
turns each into a footnote linking to that artifact's code in the published repository. Use the
exact artifact id from <artifact_workspaces>.
Example:
  "The reranker cut tail latency by 57% on the held-out split [ARTIFACT:art_4f9d2c81ab37]."
The markers are the paper's only link back to the code, so a paper that comes back with none of
them while <artifact_workspaces> is non-empty is incomplete and goes back to you.
</artifact_links>

<writing_register>
Write in the register of the field's best papers (the style exemplars block below, when the writing step saved any), not in the register of a language
model. Four things are measured on the finished draft, and a draft outside them is sent back with
the numbers:
- Never use: delve, underscore, showcase, intricate, pivotal, realm, commendable, meticulous, tapestry, garner, multifaceted, it is worth noting, plays a crucial role, not only ... but also. These are 10 to 30 times more frequent in machine-written abstracts than in
  human ones, and reviewers read them as such.
- Em dashes: at most 3 per 1,000 words. Use a comma, a colon or a full stop.
- Sentence rhythm: mix short and long sentences. An interquartile range of sentence length under
  8 words reads as machine-written.
- Hedging: at most 15 hedges (may, likely, suggests, appears) per 1,000
  words. State what the evidence supports plainly; hedge where it is thin, not everywhere.
Style never changes substance: numbers, claims, citations and figure markers stay exactly as the
evidence gives them. The user's original request (delivered as a separate message) overrides all
of this wherever the two conflict.
</writing_register>

<style_exemplars>
Verbatim passages from the field's best-cited recent papers, which the report-writing step saved
as style_exemplars.md. Every sentence you write or change for this paper, captions and
transitions included, is written in their register. Where the file ends with section outlines,
<paper_structure> says what they are for.

# Style exemplars (sentence-level register only)

How these papers write: sentences mostly 15-30 words with frequent short ones (8-12 words) after a long one; "we" throughout for what the authors did; numbers stated flatly inside the sentence with the condition that produced them ("22.6% vs 79.9% for Llama-2 7B"); hedges are rare and attached only to the explanation, never to the measurement ("may reflect", "suggests" appear once per paragraph at most); a citation every one to two sentences in introductions and related work, sparse in results paragraphs, which cite figures and tables instead.

The passages below are copied verbatim from the fetched arXiv HTML (work/exemplars/). Their content is never reused; they are exemplars of sentence style only.


## Refusal in Language Models Is Mediated by a Single Direction (2024) — https://arxiv.org/abs/2406.11717

**Abstract.** Conversational large language models are fine-tuned for both instruction-following and safety, resulting in models that obey benign requests but refuse harmful ones. While this refusal behavior is widespread across chat models, its underlying mechanisms remain poorly understood. In this work, we show that refusal is mediated by a one-dimensional subspace, across 13 popular open-source chat models up to 72B parameters in size. Specifically, for each model, we find a single direction such that erasing this direction from the model’s residual stream activations prevents it from refusing harmful instructions, while adding this direction elicits refusal on even harmless instructions. Leveraging this insight, we propose a novel white-box jailbreak method that surgically disables refusal with minimal effect on other capabilities. Finally, we mechanistically analyze how adversarial suffixes suppress propagation of the refusal-mediating direction. Our findings underscore the brittleness of current safety fine-tuning methods. More broadly, our work showcases how an understanding of model internals can be leveraged to develop practical methods for controlling model behavior.

**First paragraph of the introduction.** Deployed large language models (LLMs) undergo multiple rounds of fine-tuning to become both helpful and harmless: to provide helpful responses to innocuous user requests, but to refuse harmful or inappropriate ones (Bai et al., 2022). Naturally, large numbers of users and researchers alike have attempted to circumvent these defenses using a wide array of jailbreak attacks (Wei et al., 2023; Xu et al., 2024; Chu et al., 2024) to uncensor model outputs, including fine-tuning techniques (Yang et al., 2023; Lermen et al., 2023; Zhan et al., 2023). While the consequences of a successful attack on current chat assistants are modest, the scale and severity of harm from misuse could increase dramatically if frontier models are endowed with increased agency and autonomy (Anthropic, 2024). That is, as models are deployed in higher-stakes settings and are able to take actions in the real world, the ability to robustly refuse a request to cause harm is an essential requirement of a safe AI system. Inspired by the rapid progress of mechanistic interpretability (Nanda et al., 2023; Bricken et al., 2023; Marks et al., 2024; Templeton et al., 2024) and activation steering (Zou et al., 2023a; Turner et al., 2023; Panickssery et al., 2023), this work leverages the internal representations of chat models to better understand refusal.

**Results paragraph with numbers.** We observe a notable difference in system prompt sensitivity across model families. For Llama-2 models, including the system prompt substantially reduces ASR compared to evaluation without it (e.g. 22.6% vs 79.9% for Llama-2 7B). In contrast, Qwen models maintain similar ASR regardless of system prompt inclusion (e.g. 79.2% vs 74.8% for Qwen 7B). While the Llama-2 system prompt contains explicit safety guidelines compared to the minimal Qwen system prompt, additional analysis in §F.2 suggests the discrepancy is not explained by prompt content alone, and may reflect differences in how these models respond to system-level instructions more generally.

**Discussion or limitations paragraph.** Our study has several limitations. While we evaluate a broad range of open-source models, our findings may not generalize to untested models, especially those at greater scale, including current state-of-the-art proprietary models and those developed in the future. Additionally, the methodology we used to extract the “refusal direction” is likely not optimal and relies on several heuristics. We see this paper as more of an existence proof that such a direction exists, rather than a careful study of how best to extract it, and we leave methodological improvements to future work. Furthermore, our analysis of adversarial suffixes does not provide a comprehensive mechanistic understanding of the phenomenon, and is restricted to a single model and a single adversarial example. Another limitation is that it is difficult to measure the coherence of a chat model, and we consider each metric used flawed in various ways. We use multiple varied metrics to give a broad view of coherence. Finally, while our work identifies a single direction that mediates refusal behavior in each model, we acknowledge that the semantic meaning of these directions remains unclear. Though we use the term “refusal direction” as a functional description, these directions could represent other concepts such as “harm” or “danger”, or they may even resist straightforward semantic interpretation.


## Steering Llama 2 via Contrastive Activation Addition (2024) — https://arxiv.org/abs/2312.06681

**Abstract.** We introduce Contrastive Activation Addition (CAA), a method for steering language models by modifying their activations during forward passes. CAA computes “steering vectors” by averaging the difference in residual stream activations between pairs of positive and negative examples of a particular behavior, such as factual versus hallucinatory responses. During inference, these steering vectors are added at all token positions after the user’s prompt with either a positive or negative coefficient, allowing precise control over the degree of the targeted behavior. We evaluate CAA’s effectiveness on Llama 2 Chat using multiple-choice behavioral question datasets and open-ended generation tasks. We demonstrate that CAA significantly alters model behavior, is effective over and on top of traditional methods like finetuning and system prompt design, and minimally reduces capabilities. Moreover, we gain deeper insights into CAA’s mechanisms by employing various activation space interpretation methods. CAA accurately steers model outputs and sheds light on how high-level concepts are represented in Large Language Models (LLMs).

**First paragraph of the introduction.** As the capabilities of Large Language Models (LLMs) have grown rapidly in recent years, an increasing body of research aims to ensure they are “helpful, honest, and harmless” (Askell et al., 2021) to reduce risks from misaligned, unsafe behavior (Bommasani et al., 2021).

**Results paragraph with numbers.** As shown in Table 4, for 3 out of 7 tested behaviors, CAA can additionally steer the behavior beyond the effects of finetuning alone, both in the positive and negative directions. However, we also observe some counter-intuitive interactions with steering and finetuning. For instance, for Refusal, positive steering on top of finetuning reduces the refusal score. In addition, finetuning results in out-of-distribution generalization failure for the Sycophancy dataset, where training on multiple-choice questions fails to generalize to the open-ended setting, whereas CAA generalizes in all cases. Finetuning Llama 2 7B Chat on 1000 examples requires 10 minutes on 2 NVIDIA L40 GPUs44 4 <https://www.nvidia.com/en-us/data-center/l40/>, which is significantly more computational resources than CAA, as generating steering vectors requires only forward and no backward passes, reducing both the memory and time requirements. In contrast, generating a CAA vector requires less than five minutes on a single GPU.

**Discussion or limitations paragraph.** We test several system prompt options and few-shot prompting setups when constructing the comparison to the prompting baseline. However, it is challenging to search over all possible prompting interventions. It is possible that better steering effects could be achieved via prompting alone if more effort were applied to finding effective prompts. However, this indicates that CAA is a more reliable steering method as it does not require manual prompt optimization.


## The Geometry of Truth: Emergent Linear Structure in Large Language Model Representations of True/False Datasets (2024) — https://arxiv.org/abs/2310.06824

**Abstract.** Large Language Models (LLMs) have impressive capabilities, but are prone to outputting falsehoods. Recent work has developed techniques for inferring whether a LLM is telling the truth by training probes on the LLM’s internal activations. However, this line of work is controversial, with some authors pointing out failures of these probes to generalize in basic ways, among other conceptual issues. In this work, we use high-quality datasets of simple true/false statements to study in detail the structure of LLM representations of truth, drawing on three lines of evidence: 1. Visualizations of LLM true/false statement representations, which reveal clear linear structure. 2. Transfer experiments in which probes trained on one dataset generalize to different datasets. 3. Causal evidence obtained by surgically intervening in a LLM’s forward pass, causing it to treat false statements as true and vice versa. Overall, we present evidence that at sufficient scale, LLMs linearly represent the truth or falsehood of factual statements. We also show that simple difference-in-mean probes generalize as well as other probing techniques while identifying directions which are more causally implicated in model outputs.

**First paragraph of the introduction.** Despite their impressive capabilities, large language models (LLMs) do not always output true text (Lin et al., 2022; Steinhardt, 2023; Park et al., 2023). In some cases, this is because they do not know better. In other cases, LLMs apparently know that statements are false but generate them anyway. For instance, Perez et al. (2022) demonstrate that LLM assistants output more falsehoods when prompted with the biography of a less-educated user. More starkly, OpenAI (2023) documents a case where a GPT-4-based agent gained a person’s help in solving a CAPTCHA by lying about being a vision-impaired human. “I should not reveal that I am a robot,” the agent wrote in an internal chain-of-thought scratchpad, “I should make up an excuse for why I cannot solve CAPTCHAs.”

**Results paragraph with numbers.** Probes generalize better for larger models (Fig. 5). While it is unsurprising that larger models are themselves better at labeling statements as true or false, it is not obvious that linear probes trained on larger models should also generalize better. Nevertheless, for LLaMA-2-13B and 70B, generalization is generally high; for example, no matter which probing technique is used, we find that probes trained on larger_than + smaller_than get >95%>95\% accuracy on sp_en_trans. This corroborates our discussion in §4.1, in which we suggested that larger models linearly represent more general concepts concepts, like truth, which capture shared aspects of diverse inputs.

**Discussion or limitations paragraph.** Our work has a number of limitations. First, we focus on simple, uncontroversial statements, and therefore cannot disambiguate truth from closely related features, such as “commonly believed” or “verifiable” (Levinstein & Herrmann, 2023). Second, we study only models in the LLaMA-2 family, so it is possible that some of our results do not apply for all LLMs.


## Forking Paths in Neural Text Generation (2025) — https://arxiv.org/abs/2412.07961

**Abstract.** Estimating uncertainty in Large Language Models (LLMs) is important for properly evaluating LLMs, and ensuring safety for users. However, prior approaches to uncertainty estimation focus on the final answer in generated text, ignoring intermediate steps that might dramatically impact the outcome. We hypothesize that there exist key forking tokens, such that re-sampling the system at those specific tokens, but not others, leads to very different outcomes. To test this empirically, we develop a novel approach to representing uncertainty dynamics across individual tokens of text generation, and applying statistical models to test our hypothesis. Our approach is highly flexible: it can be applied to any dataset and any LLM, without fine tuning or accessing model weights. We use our method to analyze LLM responses on 7 different tasks across 4 domains, spanning a wide range of typical use cases. We find many examples of forking tokens, including surprising ones such as punctuation marks, suggesting that LLMs are often just a single token away from saying something very different.

**First paragraph of the introduction.** Large Language Models (LLMs) demonstrate impressive yet opaque capabilities that emerge during next-word prediction (Brown et al., 2020; Kaplan et al., 2020; Bubeck et al., 2023), and a good deal of current research is devoted to understanding and interpreting LLM behavior (Chang et al., 2024; Anwar et al., 2024; Bricken et al., 2023; Holtzman et al., 2023; Akyürek et al., 2022). LLMs are often treated as black boxes due to the sheer complexity of their internal workings, and because many state-of-the-art models are only accessible at the level of inputs and outputs. One way to assess any dynamic system is to consider what possible things it could have done, but didn’t. In text generation, we can liken a text sequence to a path the system took through the semantic space of all possible paths, and ask: what other paths could the system have taken? Are there key points where re-sampling the system at that specific point, but not others, would lead to very different paths?

**Results paragraph with numbers.** In MMLU-12 we see a similar pattern (Fig. 5, Top), where oto_{t} remains stable in relative uncertainty for a long period, before suddenly collapsing when the answer token is first specified “a = 9.8 m/s ˆ 2”. Note that the equation in the prior sentence “a = 6.67 …” evaluates to a different answer B) 8.9 m/s ˆ 2. Examining token logits we see that 9 had 54% probability of being generated and 8 had 29%. With GSM8k-59 we observe more complex uncertainty dynamics (Fig. 5, Bottom) with multiple change points. These forking tokens occur at unexpected, seemingly innocuous tokens: both are open parenthesis tokens which provide extra information not required for the final answer (i.e. non-essential clauses such as ‘(kWh)’). For the second forking token, ‘ …weekly consumption  (  …’, the top answer in o>to_{>t} is ‘$3,528’ if the token sampled is ‘ ( ’, but changes to ‘$504’ if the token sampled is ‘by’. We also note that, similar to Fig. 4, at t=0t=0 the top probability answer is the correct answer (‘21’) but this answer disappears from oto_{t} part-way through x∗x^{*}. Finally, in most cases where our model detects no change points, we observe time series where the LLM remains confident in a single outcome, with no notable uncertainty dynamics throughout text generation. Visualizations for all examples x∗x^{*} and analyses in our dataset are available through an interactive dashboard online. ** * Interactive dashboard: <https://forking-paths.streamlit.app/> Additional analyses are provided in App. E.

**Discussion or limitations paragraph.** We see a number of promising avenues for future work. The most immediate directions would be further Forking Paths Analyses with different LLMs, including open-source, and new tasks. Our experiments use a second LLM as a one-hot feature extractor R(⋅)R(\cdot), but more open-ended tasks could be analyzed using RR as a semantic vector embedding. A limitation of our approach is that it is very costly in the number of tokens sampled. More efficient sampling (Banga & Balsa-Canto, 2008) might be able to reduce the number of tokens needed, and it might even be possible to avoid sampling altogether if hidden activations can be used to predict forking. We also hope to further explore applications of Forking Paths Analysis, for example to improve process-level RL feedback (Lightman et al., 2023) or to guide branching in inference-time tree search (Yao et al., 2024). By studying the mechanisms of forking tokens, we might be able to better understand how LLMs represent uncertainty, or to steer models more effectively by patching activations at forking tokens (Fei et al., 2024).


## Generative Monoculture in Large Language Models (2025) — https://arxiv.org/abs/2407.02209

**Abstract.** We introduce generative monoculture, a behavior observed in large language models (LLMs) characterized by a significant narrowing of model output diversity relative to available training data for a given task: for example, generating only positive book reviews for books with a mixed reception. While in some cases, generative monoculture enhances performance (e.g., LLMs more often produce efficient code), the dangers are exacerbated in others (e.g., LLMs refuse to share diverse opinions). As LLMs are increasingly used in high-impact settings such as education and web search, careful maintenance of LLM output diversity is essential to ensure a variety of facts and perspectives are preserved over time. We experimentally demonstrate the prevalence of generative monoculture through analysis of book review and code generation tasks, and find that simple countermeasures such as altering sampling or prompting strategies are insufficient to mitigate the behavior. Moreover, our results suggest that the root causes of generative monoculture are likely embedded within the LLM’s alignment processes, suggesting a need for developing fine-tuning paradigms that preserve or promote diversity.

**First paragraph of the introduction.** Large language models (LLMs) show promise due to their emergent abilities [1] and state-of-the-art performance on several NLP tasks [2]. However, concerns have been raised about the increasing reliance on LLM-based systems with insufficient testing, and how they impact society [3, 4]. Recent evidence has shown that LLMs have dangerous tendencies: they convincingly return incorrect information [5, 6, 7], produce toxic language [8, 9], and can effectively propagate misinformation [10, 11].

**Results paragraph with numbers.** Takeaway 3: RLHF Hurts Diversity the Most. Llama-2-chat is obtained via performing RLHF tuning [17] on the pre-trained (PT) Llama-2. Similarly, Vicuna-13b is obtained via supervised fine-tuning (SFT) on the PT Llama-2 [33]. Comparisons on these LLMs (see Fig. 4(c), as well as Fig. 8 in Section C.4) show that the PT LLM-generated reviews are much more similar to the source. The PT LLM Llama-2 has 5.9% of samples with average sentiment values falling in the range of (0.95,1.00], which is much closer to the source percentage of 2.8% than 44.7% for Vicuna-13b and 82.1% for Llama-2-chat. Vicuna-13b also shows better diversity than Llama-2-chat—this is consistent with findings suggesting RLHF reduces output diversity compared with SFT (albeit with different metrics) [48].

**Discussion or limitations paragraph.** In this work, we introduce the concept of generative monoculture, a phenomenon where LLMs narrow the diversity of their output relative to their source data for a given task. We experimentally demonstrate its prevalence across text and code generation tasks, and show the difficulty in mitigating the behavior. Our work has limitations: first, we did not analyze the full training set of the LLMs we study due to time and compute restrictions, as the corpora are large and often proprietary. Further, as we note in § 4, measuring monoculture is difficult as selecting attributes is subjective, and the attribute extraction process is sensitive to the reliability of extraction techniques. (We verify our own attribute extraction techniques in the appendix). Further, while generative monoculture itself can have unfair consequences by enforcing the suppression of minority opinions, mitigating monoculture without extreme care could lead to the proliferation of harmful ideas or even toxicity by allowing for representation of the entire distribution of source text. We look forward to future work mitigating monoculture while maintaining low levels of toxicity and other dangerous behavior.


## Section outlines

### Refusal in Language Models Is Mediated by a Single Direction
1 Introduction; 2 Methodology (2.1 Background: Transformers, Chat models; 2.2 Datasets and models; 2.3 Extracting a refusal direction: Difference-in-means, Selecting a single vector; 2.4 Model interventions: Activation addition, Directional ablation; 2.5 Evaluation of refusal and harmfulness: Refusal score, Safety score); 3 Refusal is mediated by a single direction (3.1 Bypassing refusal via directional ablation; 3.2 Inducing refusal via activation addition); 4 A white-box jailbreak via weight orthogonalization (4.1 Weight orthogonalization; 4.2 Comparison to other jailbreaks; 4.3 Measuring model coherence); 5 Mechanistic analysis of adversarial suffixes (5.1 Adversarial suffixes suppress the refusal-mediating direction; 5.2 Adversarial suffixes hijack the attention of important heads); 6 Related work; 7 Discussion (Limitations; Ethical considerations); Acknowledgments and Disclosure of Funding; References.
- Method organised by pipeline stage: background, data and models, direction extraction, interventions, evaluation.
- Results organised by claim: one section per finding (single direction, jailbreak via orthogonalization, adversarial suffixes), each with its own experiment.

### Steering Llama 2 via Contrastive Activation Addition
1 Introduction; 2 Related work; 3 Method (3.1 Sourcing datasets; 3.2 Visualizing activations for contrastive dataset analysis); 4 Effect of CAA on behaviors (4.1 Multiple-choice question datasets; 4.2 Open-ended generation); 5 CAA and system-prompting; 6 Comparison to finetuning; 7 Effect of CAA on general capabilities; 8 Understanding and interpreting CAA (8.1 Similarity between steering vectors and per-token activations; 8.2 Similarity between vectors generated at different layers; 8.3 Comparing representations between base and chat models); 9 Discussion (9.1 Suggested future work); 10 Limitations; Ethics Statement; Acknowledgements; References; Appendices.
- Method organised by component: steering-vector construction, then the datasets that feed it.
- Results organised as main result, then comparisons with baselines (system prompting, finetuning), then side effects, then interpretation.

### The Geometry of Truth: Emergent Linear Structure in Large Language Model Representations of True/False Datasets
1 Introduction (1.1 Related work); 2 Datasets (Curated datasets; Uncurated datasets; likely dataset); 3 Localizing truth representations via patching; 4 Visualizing LLM representations of true/false datasets (4.1 Discussion); 5 Probing and generalization experiments (5.1 Challenges with logistic regression, and mass-mean probing; 5.2 Experimental set-up; 5.3 Results); 6 Causal intervention experiments (6.1 Experimental set-up; 6.2 Results); 7 Discussion (7.1 Limitations and future work; 7.2 Conclusion); Acknowledgements; References; Appendices.
- Method organised by line of evidence: localisation, visualisation, probing, causal intervention, each with its own set-up.
- Results organised by line of evidence, each section ending with its own results subsection.

### Forking Paths in Neural Text Generation
1 Introduction; 2 Forking Paths Analysis (2.1 Language Model Sampling Pipeline; 2.2 Representing Text Generation Outcomes; 2.3 Bayesian Change Point Detection; 2.4 Survival Analysis); 3 Experiments; 4 Results (4.1 Change Point Detection; 4.2 Survival Analysis); 5 Discussion; Reproducibility Statement; Acknowledgments; References.
- Method organised by pipeline stage: sampling, outcome representation, two statistical models.
- Results organised by statistical model (change points, then survival), with case studies before aggregates.

### Generative Monoculture in Large Language Models
1 Introduction; 2 Defining Generative Monoculture (Definition 1); 3 Related Work; 4 Measuring Generative Monoculture (4.1 Data Curation; 4.2 Attribute Extraction; 4.3 Metric Calculation); 5 Mitigating Generative Monoculture; 6 Experimental Setup (6.1 Generating Book Reviews; 6.2 Generating Code Solutions); 7 Results and Takeaways; 8 Conclusion and Limitations; References.
- Method organised by measurement pipeline stage: definition, data curation, attribute extraction, metric.
- Results organised as numbered takeaways across both domains (book reviews, code).
</style_exemplars>

<domain_vocabulary>
The vocabulary this field uses for its own concepts, metrics and conditions, extracted from the
papers in <style_exemplars> and from the titles in the bibliography. Four rules, and the draft is
checked against this list before it is accepted:

- Name each concept, metric and condition the way the field names it. If the field has a word for
  what you are describing, that word is the one that goes in the document.
- Never invent a private label for something the field already names. A reader searching for the
  standard term has to be able to find this work.
- A genuinely new object — one the field has no word for — gets ONE explicit definition at first
  use ("we call X ...", "we define X as ...") and exactly the same words everywhere after it.
- Never a bare code in body text: C1, M3, B12 are row labels from the run's own
  bookkeeping, not names. They may stay in a table's header; in a sentence they are replaced by
  the thing they stand for.

- residual stream — the running sum of layer outputs that every transformer block reads from and writes to
- residual stream activations — the vector state of the residual stream at a given layer and token position
- difference-in-means — a direction computed as the mean activation of one set of prompts minus the mean of a contrasting set
- directional ablation — removing the component of an activation along a chosen direction at every layer and position it is applied to
- activation addition — adding a fixed vector, scaled by a coefficient, to the residual stream during the forward pass
- chat template — the model-specific token format that wraps user and assistant turns for a chat model
- chat model — an instruction-tuned model served through a chat template
- model coherence — whether an intervened model still produces fluent, usable output
- steering vector — an activation-space vector added during inference to shift a behaviour
- steering multiplier — the coefficient that scales a steering vector before it is added
- contrastive activation addition — steering with the mean activation difference between paired positive and negative examples
- system prompt — an instruction placed before the user turn that conditions the response
- open-ended generation — free-form sampling, as opposed to scoring fixed answer options
- layer sweep — repeating an intervention or probe at every layer to find where it acts
- base model — the pretrained checkpoint before instruction tuning
- prompting baseline — the effect obtainable by prompt wording alone, against which a steering method is compared
- linear probe — a linear classifier trained on activations to read out a property
- mass-mean probe — a probe whose direction is the difference of class means
- logistic regression probe — a linear probe fitted by logistic regression
- probe generalization — accuracy of a probe on data distributions it was not trained on
- activation patching — replacing activations from one run with those of another to localise an effect
- linear representation — a property encoded along a direction of activation space
- causal intervention — editing activations and measuring the change in model output
- forking token — a token at which resampling the continuation changes the outcome distribution sharply
- outcome distribution — the distribution of final outcomes over continuations resampled from a prefix
- change point detection — statistical localisation of the positions where a series changes distribution
- resampling — drawing new continuations from a fixed prefix to estimate what the model could have produced
- survival analysis — modelling the time until an outcome becomes fixed during generation
- next-token distribution — the model's probability distribution over the next token at a position
- chain-of-thought — intermediate reasoning text produced before the final answer
- uncertainty dynamics — how the outcome distribution changes token by token during generation
- forking point — a position at which the outcome distribution changes abruptly
- generative monoculture — a narrowing of output diversity relative to the diversity available for the task
- output diversity — the spread of distinct outputs a model produces for one prompt
- diversity collapse — loss of output diversity, for example under chat-format structure
- Jaccard similarity — intersection over union of two sets, used to compare programs or algorithm sets
- Hill number — the effective number of categories, exp of Shannon entropy at order 1
- effective number — the number of equally common categories that would give the observed diversity
- Shannon entropy — minus the sum of p log p over a distribution
- evenness — how uniformly mass is spread over the categories present
- intrinsic dimension — the number of degrees of freedom of the manifold a point cloud lies on
- TwoNN estimator — an intrinsic-dimension estimator from ratios of first and second nearest-neighbour distances
- geodesic distance — distance measured along a neighbourhood graph that approximates the data manifold
- k-nearest-neighbour graph — a graph linking each point to its k closest points
- multidimensional scaling — an embedding that preserves a matrix of pairwise distances in few dimensions
- Isomap — nonlinear dimensionality reduction by MDS on graph geodesic distances
- nonlinear dimensionality reduction — embedding data that lie on a curved manifold into few coordinates
- manifold steering — moving activations along a fitted representation manifold rather than a straight line
- representation manifold — the low-dimensional structure traced by activations of a family of inputs
- affine concept editing — editing activations relative to a reference point rather than the origin
- mean-anchored ablation — projection-out of a direction measured from a reference mean instead of zero
- temperature — the softmax scaling parameter used when sampling tokens
- sampling temperature — the temperature used at decoding time; higher values flatten the next-token distribution
- novelty — how different an output is from what is typical
- typicality — how representative an output is of the usual outputs
- adaptive temperature sampling — raising the temperature only at positions where tokens are hard to predict
- top-k sampling — sampling restricted to the k most probable next tokens
- nucleus sampling — sampling restricted to the smallest token set with cumulative probability p (top-p)
- negative constraint — an instruction telling the model what not to produce
- priming — raising the probability of a concept by mentioning it, even when it is forbidden
- negation — processing of a 'not' in the input that should change the answer
- suppression — lowering the probability of the original answer
- promotion — raising the probability of an alternative candidate
- denial prompting — iteratively forbidding a technique used in the previous solution
- creativity — producing correct and divergent solutions
- constraint compliance — the fraction of outputs that satisfy an explicit constraint
- implementation prior — the default code pattern a model uses for a common task
- algorithm choice — which algorithm a model implements for a coding task
- semantic cue — a prompt cue whose meaning bears on the solution approach
- innocuous cue — a prompt cue with no bearing on the solution approach
- control task — a task with shuffled or random labels that measures what a probe can learn by itself
- selectivity — probe accuracy minus control-task accuracy
- sparse autoencoder — a sparse dictionary of features learned on activations
- steering baseline — a simple method, such as prompting or difference-in-means, that steering methods are compared against
- aligned model — a model after preference or instruction tuning
- post-training — training stages after pretraining, such as instruction tuning and preference optimisation
- thinking mode — Qwen3's mode that emits a reasoning block before the answer; non-thinking mode skips it
- non-thinking mode — Qwen3's mode that answers without a reasoning block
- log score — the logarithm of the probability a forecast assigned to the observed outcome
- strictly proper scoring rule — a scoring rule maximised in expectation only by the true distribution
- Cohen's kappa — chance-corrected agreement between two raters on nominal labels
- inter-rater agreement — the extent to which independent labellers assign the same label
- Wilson score interval — a confidence interval for a binomial proportion
- PELT — pruned exact linear time search for multiple change points
- Kendall's W — the coefficient of concordance among several rankings of the same items
- algorithmic diversity — the number and spread of distinct algorithms among solutions
- functional correctness — whether a program passes its test cases
- hidden tests — held-out test cases used to judge correctness
- pass rate — the fraction of generated programs that pass all tests
- PagedAttention — the KV-cache memory manager used by the vLLM serving engine
- prefix sharing — reusing the KV cache of a common prompt prefix across sequences
- code efficiency — runtime and memory cost of a correct program
- execution trace — the sequence of intermediate states of an algorithm run
- algorithmic reasoning — the ability to reproduce the steps of classical algorithms
- verifiable solution — a solution checked by executing unit tests
- concreteness rating — a norm of how concrete a word's referent is
- word frequency norm — corpus-based frequency of a word, for example SUBTLEX
- behavioral evaluation — measuring a behaviour from model outputs rather than internals
- held-out — data not used to fit the quantity being evaluated
- principal component analysis — projecting activations onto the directions of largest variance before visualisation or further analysis
- change point — a position in a sequence where the distribution of outcomes shifts abruptly
- Bellman-Ford — a single-source shortest path algorithm that relaxes every edge repeatedly; SPFA is its queue-based variant
- Floyd-Warshall — an all-pairs shortest path algorithm by dynamic programming over intermediate nodes
- CLRS-Text — a text version of the CLRS-30 algorithmic reasoning benchmark with execution traces
- top-k — sampling restricted to the k most probable next tokens
- top-p — nucleus sampling parameter: sampling from the smallest token set whose probability mass reaches p
- instruction-tuned — describing a model fine-tuned to follow instructions in a chat format
- open-weight — describing a model whose parameters are publicly released
- low-dimensional — occupying few dimensions relative to the ambient activation space
- cross-lingual — spanning more than one programming or natural language
- LLM-generated — produced by a large language model
- high-standard — held to a strict evaluation standard
- attention knockout — blocking attention from chosen query positions to chosen key positions to measure how much information flows along those edges
- interchange intervention — replacing a component's activations from one input with those from another and measuring the change in output
- logit lens — reading an intermediate residual stream state through the model's final unembedding to see which tokens it already favours
- tuned lens — a logit lens with a learned affine translator per layer, trained to match the final-layer distribution
- latent prediction — the next-token distribution decoded from an intermediate layer rather than the final one
- key-value cache — the stored attention keys and values of earlier tokens that later tokens attend to during generation
- importance sampling — estimating an expectation under one distribution with weighted samples drawn from another proposal distribution
- multiple importance sampling — importance sampling with samples drawn from several proposal distributions and combined by a weighting rule
- balance heuristic — the multiple importance sampling weight that treats all proposals as one mixture proposal
- effective sample size — the number of equally weighted samples that would give the same variance as a set of importance-weighted samples
- interval for a difference of proportions — a confidence interval for the difference between two independent binomial proportions, such as Newcombe's hybrid score interval
- thought anchors — sentences of a reasoning trace whose resampling changes the final answer distribution most
- top-k sparse autoencoder — a sparse autoencoder that keeps only the k largest latent activations per input
- sparse features — directions found by a sparse dictionary that each fire on a narrow set of inputs
- mode collapse — a model's outputs concentrating on a few typical responses although many are acceptable
- typicality bias — a preference, learned from human ratings, for familiar and typical responses
- stratification — splitting the space of answers into strata and sampling a stratum before sampling an answer
- introspection — a model predicting facts about its own behaviour better than an external model trained on the same behaviour
- approach-level diversity — diversity of the solution strategies used, as opposed to diversity of wording
- surface-level diversity — diversity of wording and form among outputs that may share one strategy
- ironic negation — the increase in probability of a concept that an instruction tells the model to avoid
- negation processing — how a model represents and applies a negation in its input
- interpretability without actionability — decoding a property from internals without being able to change behaviour by editing it
- mechanistic interpretability benchmark — a shared benchmark that scores circuit-localisation and causal-variable methods against baselines
- approach-organised representations — internal states that cluster by solution approach rather than by surface topic
- humanlike diversity — the spread of distinct, high-quality answers a population of people would give to one prompt
- RLHF — reinforcement learning from human feedback, a post-training stage
- approach-level — at the level of the solution strategy rather than its wording
- auto-regressive — generating one token at a time, each conditioned on the tokens before it
- near-perfect — almost perfect, said of how well a property can be decoded from internal representations
- Qwen-Scope — a released set of sparse autoencoders trained on Qwen3 models, used as development tools
- task vector — a compact representation of a demonstrated task that an in-context prompt induces at one position
- function vector — a vector transported by a few attention heads that carries a demonstrated task and can trigger it elsewhere
- task recognition point — the layer after which a model no longer needs to attend to the instruction or examples
- instruction following — whether a model's response satisfies the instruction it was given
- prefilling — forcing the first tokens of the response before sampling the rest
- shallow alignment — a learned behaviour that is enforced only in the first few tokens of a response
- constrained decoding — restricting which tokens may be generated at decoding time
- tree edit distance — the minimum number of node insertions, deletions and relabellings that turn one tree into another
- Wilcoxon signed-rank test — a paired nonparametric test on the ranks of within-pair differences
- Pareto smoothed importance sampling — importance sampling whose largest weights are replaced by a fitted generalised Pareto tail, with the shape k-hat as a reliability diagnostic
- rule of three — an approximate 95% upper bound of 3/n on a rate when 0 events occur in n trials
- BCa interval — a bias-corrected and accelerated bootstrap confidence interval
- mean ablation — replacing a component's output by its mean over a reference distribution
- fraction of variance unexplained — the share of activation variance that a sparse autoencoder reconstruction leaves in its error
- noise steering — adding random noise to internal activations during generation to raise output diversity
- activation steering — editing hidden activations at inference time to change model behaviour
- prompt formatting — surface choices in how a prompt is laid out, to which model accuracy can be highly sensitive
- intent factored generation — sampling a high-level intent at high temperature before sampling the response at low temperature
- plan search — searching over natural-language plans before writing code, to diversify solutions
- steerability — whether an activation-steering intervention succeeds on a given model and concept
- Gumbel counterfactual generation — generating counterfactual strings by reusing the same sampling noise under an intervened model
- response planning — information about the coming response that is already encoded in the prompt representations
- prefilling attack — forcing the first tokens of a model's response to bypass a learned behaviour
- seed-conditioning — injecting randomness at the input layer instead of through output temperature
- program search — evolutionary search over programs with an LLM proposer and an automatic evaluator
- random embedding injection — inserting random embeddings into the input to diversify reasoning paths
- grammar-aligned decoding — constrained decoding corrected so that outputs keep the model's own relative likelihoods
- diversity injection — the level at which randomness is introduced into a generation pipeline
- coding agent — an LLM system that iteratively writes, evaluates and improves programs
- model-generated code — programs written by a language model, as opposed to human solutions
- cross-model activation patching — patching activations from one model into a related model to test whether their representations correspond
- weight interpolation — averaging the weights of a base and a fine-tuned checkpoint to trade off their behaviours
- weight ensembling — interpolating fine-tuned weights with earlier weights to recover diversity
- selective layer restoration — restoring a range of layers of a post-trained model to their pretrained weights
- base-aligned model collaboration — combining a base model and its aligned counterpart at inference time to balance diversity and quality
- conformative decoding — guiding an instruction-tuned model's decoding with its more diverse base model
- alignment signature — the direction in activation space that separates aligned from base residual states
- probability concentration — the narrowing of the output distribution that alignment causes
- branching factor — the effective number of plausible next tokens at a position
- conceptual diversity — variety of the concepts a population of model outputs expresses
- reasoning boundary — the set of problems a model can solve with some sampling budget
- pass@k — the probability that at least one of k samples is correct
- RLVR — reinforcement learning with verifiable rewards
- difference-in-differences — a contrast of two differences that removes a shared confound
- parametric code retrieval — reproducing a named algorithm from internalised knowledge rather than synthesising a new one
- latent-space rollout diversification — injecting noise into hidden states of the prompt pass to diversify rollouts
- in-context alignment — aligning a base model with in-context examples instead of fine-tuning
- activation transfer — carrying an activation-space intervention from one model to another
- knowledge storage — where factual associations are encoded inside a model's layers
- cross-patching — replacing the hidden state at a layer boundary of one model with the state of another
- template-controlled — measured with the base and the aligned model under the same chat template, so that the template does not enter the contrast
- alignment-induced — caused by alignment tuning, said of the activation shift between a base model and its aligned descendant
- diversity-quality — the pairing of output diversity with output quality, which merging a base and an aligned model trades against each other
- base-aligned — combining a base model with its aligned descendant during generation
- latent-space — in the space of a model's hidden representations rather than its tokens or pixels
- vision-language — models that read images and text together
- redundancy-aware — penalising samples that duplicate one another when several samples are drawn per prompt
- multi-sample — drawing several samples per prompt and scoring them as a set
- per-problem — measured separately for each problem rather than averaged over a benchmark
- W8A8 — a quantisation scheme with 8-bit weights and 8-bit activations in the linear layers
- weight-only quantization — quantising the weights to low precision while the activations stay in 16-bit floating point
- activation quantization — rounding the inputs of each linear layer to low precision at inference time
- per-token — computed separately for each token row of an activation matrix, as in per-token quantisation scales
- e4m3 — the 8-bit floating-point format with 4 exponent bits and 3 mantissa bits
- KV cache quantization — storing the attention keys and values in low precision during decoding
- mixed-precision inference — running different parts of a model's computation at different numerical precisions
- cross-precision divergence — differences in a model's outputs when the same weights are run at two numerical precisions
- numerical nondeterminism — run-to-run differences in model outputs caused by floating-point arithmetic, batch size or hardware
- teacher forcing — scoring a given continuation token by token with the model conditioned on the true preceding tokens
- teacher-forced — computed under teacher forcing, that is with the model conditioned on a given continuation
- Mantel-Haenszel — a pooled odds ratio over strata of a confounder, weighting each stratum's 2-by-2 table
- non-inferiority — a test that an estimate is not worse than a comparator by more than a margin fixed in advance
- non-inferior — not worse than a comparator by more than a margin fixed in advance
- Poisson-binomial — the distribution of the number of successes in independent trials with unequal success probabilities
- Bonett-Wright — the approximate confidence interval for a Spearman correlation based on the Fisher transform with an adjusted variance
- min-heap — a binary heap whose root holds the smallest key
- max-heap — a binary heap whose root holds the largest key
- emergent misalignment — broad misaligned behaviour that appears after fine-tuning on a narrow task
- persona subspace — a low-dimensional set of directions in a tuned model's activations that carries a behavioural persona
- power sampling — sampling from a model's distribution raised to a power, which sharpens it toward its likeliest sequences
- base model barrier — the cost for outcome-reward policy gradient of reaching outputs the base model rarely produces
- embedding perturbation — adding random noise to token embeddings to probe where a model's output is sensitive
- weak-to-strong jailbreaking — steering a large aligned model's decoding with the distribution shift between two small models
- few-shot — conditioning a model on a few solved examples placed in the prompt before the target
- Holm adjustment — the sequentially rejective correction of p values for multiple tests
- floating-point — a number format with a sign, an exponent and a mantissa
- weight-only — applied to the weights alone, with activations left at full precision
- Clopper-Pearson — the exact binomial confidence interval obtained by inverting two one-sided binomial tests
- Boyer-Moore — the linear-time majority vote algorithm that keeps one candidate and a counter
- accuracy-performance — the trade-off between task accuracy and inference cost under quantisation
- dose-response — how the size of an effect changes with the size of the intervention
- mixed-precision — using different numerical precisions for different parts of one computation
- precision-invariant — unchanged when the same model is run at another numerical precision
- cross-precision — comparing the same model and inputs across numerical precisions
- weak-to-strong — using a smaller model to steer or supervise a larger one
- re-emergent — reappearing after alignment had suppressed it
- pre-existing — present in the model before the fine-tuning under study
- open-ended — as in open-ended generation: free-form sampling, as opposed to scoring fixed answer options
- mass-mean — as in mass-mean probe: a probe whose direction is the difference of class means
- next-token — as in next-token distribution: the model's probability distribution over the next token at a position
- k-nearest-neighbour — as in k-nearest-neighbour graph: a graph linking each point to its k closest points
- mean-anchored — as in mean-anchored ablation: projection-out of a direction measured from a reference mean instead of zero
- non-thinking — as in non-thinking mode: Qwen3's mode that answers without a reasoning block
- inter-rater — as in inter-rater agreement: the extent to which independent labellers assign the same label
- key-value — as in key-value cache: the stored attention keys and values of earlier tokens that later tokens attend to during generation
- surface-level — as in surface-level diversity: diversity of wording and form among outputs that may share one strategy
- approach-organised — as in approach-organised representations: internal states that cluster by solution approach rather than by surface topic
- signed-rank — as in Wilcoxon signed-rank test: a paired nonparametric test on the ranks of within-pair differences
- grammar-aligned — as in grammar-aligned decoding: constrained decoding corrected so that outputs keep the model's own relative likelihoods
- model-generated — as in model-generated code: programs written by a language model, as opposed to human solutions
- cross-model — as in cross-model activation patching: patching activations from one model into a related model to test whether their representations correspond
- in-context — as in in-context alignment: aligning a base model with in-context examples instead of fine-tuning
- min-p — sampling that keeps only tokens whose probability is at least a set fraction of the top token's
- token-level — measured or applied separately for each token of the output
- inference-time — applied while the model generates, without changing its weights
- distributed alignment search — fitting an orthonormal low-rank subspace in which an interchange intervention reproduces a counterfactual behaviour
- DAS — distributed alignment search
- Boundless DAS — distributed alignment search with learned boundaries, scaled to a 7B model
- interchange intervention accuracy — the share of exchanged runs whose output matches the counterfactual source's output
- distributed interchange intervention — an interchange intervention applied inside a learned subspace rather than on whole components
- natural language autoencoder — a pair of models that writes a text explanation of an activation and reconstructs the activation from that text
- activation verbalizer — the half of a natural language autoencoder that writes an explanation of a residual-stream state
- activation reconstructor — the half of a natural language autoencoder that maps an explanation back to a residual-stream state
- JumpReLU sparse autoencoder — a sparse autoencoder whose latents pass through a thresholded ReLU
- transcoder — a sparse dictionary trained to reproduce an MLP's output from its input
- Gemma Scope — a release of sparse autoencoders trained on every layer of Gemma models
- fraction of variance explained — one minus the share of activation variance a reconstruction leaves unexplained
- L0 — the mean number of active sparse-autoencoder latents per token
- loss recovered — the share of the language-model loss increase from zero ablation that a spliced-in reconstruction avoids
- W16A8 — 16-bit weights with 8-bit activations in the linear layers
- W8A16 — 8-bit weights with 16-bit activations in the linear layers
- fake quantisation — rounding values to a low-precision format and back inside a higher-precision computation
- dynamic per-token scaling — choosing each token row's quantisation scale from its own absolute maximum at run time
- Firth logistic regression — logistic regression with a penalty that removes first-order bias and keeps estimates finite under separation
- Mantel-Haenszel odds ratio — an odds ratio pooled over strata of a confounder
- Gwet's AC1 — a chance-corrected agreement coefficient that stays stable when one category dominates
- Fleiss kappa — chance-corrected agreement among more than two raters
- interpretability illusion — a subspace intervention that changes behaviour through a pathway the model does not use naturally
- prefix resampling — drawing many continuations from fixed prefixes of a generation to locate where its outcome is decided
- activation steering under quantization — applying a steering vector to a quantised model and comparing its effect with full precision
- self-interpretation — a model describing the content of its own hidden embeddings in natural language
- decodability supervision — training a model so that verbalised explanations of its activations are checkable
- latent planning — information about future output computed before it is emitted
- Fieller interval — a confidence interval for a ratio or a transformed correlation that accounts for uncertainty in the denominator
- 8-bit floating point — a number format with 8 bits per value (here e4m3: 4 exponent and 3 mantissa bits, maximum 448), used for weights and activations of linear layers in low-precision inference
- path patching — patching a component's contribution along one path of the computation with its value under a contrasting input, to measure that path's effect on the output
- attribution patching — a gradient-based linear approximation of the effect of patching every node, computed in one backward pass
- circuit — a subgraph of attention heads and MLPs, connected by paths, that carries out a given behaviour of the model
- causal abstraction — the relation in which an interpretable causal model's variables can be aligned with a network's representations by interventions
- random-initialisation control — fitting the same intervention map on a randomly initialised network; an equally good fit there shows the fit alone certifies no learned variable
- MAP-Elites — a quality-diversity search that keeps the best solution found in each cell of a grid of behaviour descriptors
- island model — an evolutionary search split into separate subpopulations (islands) that evolve in parallel, with the weakest periodically reset
- evaluator — the program that executes each candidate and scores it, the fixed part of a search with an LLM proposer
- entropy-based dynamic temperature — a sampler that sets the temperature of each decoding step from the entropy of that step's next-token distribution
- min-p sampling — truncation sampling that keeps only tokens whose probability is at least a fixed fraction of the most likely token's probability
- high-entropy minority tokens — the small share of generated tokens with high predictive entropy that act as forks in a reasoning trace
- prefix steering — activation steering applied over a short span of generated tokens, as short as a single token, instead of at every position
- divergent representations — activations produced by a causal intervention that lie outside the distribution the model produces on natural inputs
- reverse interchange — an interchange intervention run in the opposite direction, writing the default class's coordinates into a forced base, to test whether the edit restores the default
- dormant subspace — a subspace with little natural variance that becomes causally active only when an intervention writes into it
- noising — patching activations from a corrupted run into a clean run to measure how much a component is needed for the clean behaviour
- denoising — patching activations from a clean run into a corrupted run to measure how much a component suffices to restore the clean behaviour
- circuit completeness — the share of the full effect that is lost when the circuit's components are ablated together
- circuit faithfulness — how much of the full model's behaviour the circuit reproduces when every component outside it is frozen
- integrated gradients — an attribution method that integrates gradients along a straight path from a baseline input to the actual input
- attribution graph — a graph of direct effects between interpretable features in a replacement model, computed for one prompt and one output
- replacement model — a model in which each MLP is replaced by a transcoder, so that its computation can be read in terms of sparse features
- difference-in-means direction — the difference between the mean activations of two classes, used as a probe or steering direction
- Kruskal stress-1 — the normalised residual between embedded and original distances, used to judge how well an MDS embedding fits
- persistent homology — a summary of the loops and holes of a point cloud that persist across a range of length scales
- intersection-union test — a composite test that rejects the joint null only if each component test rejects at the same level
- Jensen-Shannon divergence — a symmetric, bounded divergence between two distributions, the mean KL divergence of each from their average
- URIAL token categories — the classification of each token of an aligned model as the base model's top token, a near-top token or a shifted token
- exact McNemar test — an exact binomial test on the discordant pairs of a paired binary comparison
- massive activation — a few residual-stream dimensions whose values are orders of magnitude larger than the rest
- 4-bit NormalFloat quantisation — 4-bit NormalFloat weight quantisation, whose levels follow the quantiles of a normal distribution
- total variation distance — half the L1 distance between two probability distributions, the largest difference in probability they assign to any event
- common random numbers — reusing the same random streams across the arms of a comparison, so that differences between arms are paired per stream
- lexical compliance — a program obeys a ban by name: no banned algorithm name or alias appears in its code or comments
- mechanistic compliance — a program obeys a ban by mechanism: its runtime expansion order is not the order of any banned algorithm
- expansion order — the sequence in which a search program reads the neighbours of grid cells, measured at runtime on probe grids
- representational similarity analysis — comparing two representations through their matrices of pairwise dissimilarities between conditions, usually by rank correlation
- noise ceiling — the highest correlation a model dissimilarity matrix can be expected to reach given the reliability of the measured one
- crossnobis distance — a cross-validated Mahalanobis distance between condition means, unbiased by measurement noise
- Jonckheere-Terpstra test — a rank test for an ordered trend across several groups against the null of no difference
- Cochran-Armitage test — a test for a linear trend in proportions across ordered groups
- Fork-Patched Decoding — decoding with the base model's next-token distribution spliced in at fork positions and the tuned model's elsewhere
- sharpening — post-training that concentrates probability on outputs the base model already ranks highly rather than adding new ones
- split-half reliability — the correlation between results computed on two random halves of the data, Spearman-Brown corrected to full length
- lexical identity confound — a measured representational effect that is carried by shared tokens or words rather than by the concept of interest
- partial Mantel test — a test of the association between two distance matrices while controlling for a third, whose full label permutation is invalid when the matrices are structured
- restricted permutation — a permutation null that shuffles labels only within strata of a controlled factor, keeping that factor's structure intact
- representational geometry — the pattern of pairwise distances between a system's representations of a set of conditions
- classical multidimensional scaling — an embedding of a distance matrix into a few coordinates by eigendecomposition of the double-centred squared distances
- semantic grounding — whether a code model's representations reflect what programs mean rather than their surface form
- online bin packing — packing items that arrive one at a time into unit-capacity bins, each item placed before the next is seen, to minimise the number of bins used
- best fit — the online bin packing rule that places an item in the feasible bin with the least remaining capacity
- first fit — the online bin packing rule that places an item in the lowest-indexed bin that can hold it
- worst fit — the online bin packing rule that places an item in the feasible bin with the most remaining capacity
- L1 lower bound — the bin packing lower bound equal to the total item size divided by the bin capacity, rounded up
- excess bins — the percentage by which the bins a heuristic uses exceed the L1 lower bound
- priority function — a scoring function that assigns each feasible bin a priority for the incoming item; the item goes to the highest-scoring bin
- automatic heuristic design — using a search procedure, here driven by a language model, to write and select heuristics for a combinatorial problem
- OR-Library instances — the public benchmark instance sets of the OR-Library, including the binpack1 to binpack4 bin packing sets
- Weibull instances — bin packing instances whose item sizes are drawn from a Weibull distribution, as in FunSearch's evaluation
- constructive heuristic — a heuristic that builds a solution one decision at a time, for the TSP by choosing the next city to visit
- nearest neighbour heuristic — the constructive TSP rule that always moves to the closest unvisited city
- optimality gap — the percentage by which a tour is longer than a reference tour from a strong solver
- TSPLIB — the standard library of travelling salesman instances with published optimal tour lengths
- LKH-3 — the Lin-Kernighan-Helsgaun solver used to compute near-optimal reference tours
- held-out instances — instance sets never used to select programs during search, used only to score the selected programs
- random-sampling baseline — a search arm that samples programs without selection, so the evaluator never steers generation
- probe states — a fixed set of decision situations on which every program's choices are recorded to compare programs by behaviour
- behaviour cluster — a group of programs whose decisions agree on at least a set share of probe states, formed by complete linkage
- complete linkage — agglomerative clustering in which a cluster's distance to another is the largest pairwise distance between their members
- unembedding — the output matrix that maps the final normalised residual to vocabulary logits, one row per token
- McNemar test — an exact test on discordant pairs for paired binary outcomes
- Clopper-Pearson interval — the exact binomial confidence interval obtained by inverting two one-sided binomial tests
- Hungarian method — an algorithm that solves the assignment problem, used here to match late layers to early layers one to one
</domain_vocabulary>
FIRST, add ALL of these to your todo list using your task/todo-tracking tool:

CRITICAL: Todo content must be copied exactly as is written here, with NO CHANGES. These todos are intentionally detailed so that another LLM could read each one without any external context and understand exactly what it has to do.

<todos>
TODO 1. Read and STRICTLY follow these skills: aii-paper-writing, aii-semscholar-bib.
TODO 2. READ THE RUN, THEN DECIDE THE ARGUMENT. Read every summary in <artifact_workspaces>, the
first round's as closely as the last, then open the directories of the artifacts that could carry
the paper and read the output files they declare — the JSON, the CSVs, the logs, the metrics. The
goal is what the user's request below asks for; where it names none, the best paper this evidence
supports for a conference in the work's field. Turn that request into a numbered BRIEF CHECKLIST
of every item it requires (each research question, comparison, analysis, section, figure, citation
count, target venue); the paper addresses every item explicitly, and says so where the evidence
cannot. When it names a target journal, the paper takes that journal's section names and closes
with its Declarations, under its headings, as the small adjustments <paper_structure> allows: the
first section may carry the journal's name for the Introduction, and Limitations stays at least a
titled subsection.

Before choosing, write yourself a CLAIM LEDGER covering every round: one entry per candidate
finding, listing every artifact that measured it (each replication by name), its verdict as those
artifacts state it (passed, failed, not_testable, exploratory), the caveats that bound it
(judge or anchor agreement, sample size, novelty status), and its exact numbers and intervals,
recomputed from the output files, never copied from a summary line. Where several artifacts or
sets measured one finding, give each measurement its own line with its design: registered and
frozen before its data or not, whether that data also tuned, selected or developed anything, and
confirmatory or exploratory. The strongest design supplies the finding's headline number, per
<publishable_paper_rules>; the rest support it. An artifact's own label for its set ("held-out",
"confirmation set") is a claim, not a fact: search the report and iteration records in
<run_record> for the set's name and record every place it screened, tuned, selected, fitted or
gated anything. A pre-registered test's verdict is its own arm's, as the record states it: an arm
whose baseline or labels never produced the planned comparison is not testable, however high its
score, and an absolute score is not a result until it is set against what it had to beat. Submit
this ledger's candidate measurements as `headline_candidates`, each with its outcome, its effect as
a contrast against its baseline and the scope the record limits it to, the headline marked. The
step looks each set up in the run record, sends the draft back when a pre-registered test that
passed against its baseline is on the ledger and the headline is not one, and checks the
abstract's number and grade against the headline's line. Open the files of the
earliest rounds' candidates as you open the last round's. Rank the ledger by the order of
evidence strength in <publishable_paper_rules>: the top entry is the headline, whichever round
produced it, and the combination of other entries that makes the argument around it follows. The
run's final hypothesis is one input to that choice, not its anchor, and an artifact that does not
serve the argument is left out. Every claim the paper makes carries its ledger verdict and
caveats into the draft with its number. This decision is the paper; make it before you write a
sentence.
TODO 3. BUILD THE BIBLIOGRAPHY. Collect the DOIs and arXiv ids already cited in the run report,
search for the close prior work your finding has to be placed against, then batch-fetch real
BibTeX in one call with the aii_semscholar_bib__fetch script and `--out ./references.bib`. Only a
paper that script returns is cited: never hand-write an entry, and leave out one it cannot find.
Fetch each paper's PUBLISHED version by its journal or proceedings DOI, never its preprint. Cite a
paper only for what it actually reports (a survey is not the source for a specific finding), and
check every venue you name ("published in journal X") against its Crossref record.
Cite in the prose with numeric references [1], [2], and put the numbered reference list at the
very END of paper_text, each entry with its DOI or arXiv id.
TODO 4. WRITE THE PAPER into paper_text, to <publishable_paper_rules>, in the sections
<paper_structure> gives, then the references. Markdown, structured by IDEA — never a section
per iteration, never a word about the pipeline. Put [FIGURE:fig_id] markers where figures belong
per <figure_rules>, with the flagship at the end of the Introduction, and give every spec in the
figures array. Put [ARTIFACT:id] markers on claims
that rest on an artifact. Fill title, abstract and summary too. Do NOT write LaTeX, do NOT
compile anything, and do NOT generate figure images — a later step does all three.
TODO 5. REVISION PASS — start this ONLY once the draft above is written, and treat it as a distinct
pass over the finished text rather than something folded into the writing. Read
`REVISION_CHECKLIST.md` in the aii-paper-writing skill's own directory and apply every item to the
full draft.

Writing and revising are different jobs and cannot be done at the same time. The defects that
checklist targets — prose denser than the field needs, an abstract dumped full of numbers (the
headline measurement's own effect, interval and evidence grade always stay), sections
that leak into one another, a Figure 1 that shows a side result instead of the main idea, close
prior work that only the draft's FINAL vocabulary would have surfaced, a study of N things that
plots eight of them, section names that mean nothing to someone who has not read the section,
implementation filenames or raw variable names in the prose and tables, numbers that disagree
between the abstract, the text and the tables or come from anywhere but the artifact files, two
quantities compared across different metrics, a claim that the artifacts lack a result nobody
searched them for, a symbol used before it is defined, a key null result missing from the
abstract, an item of the brief checklist left unaddressed — are all invisible while drafting,
because you are holding your intent rather than the text. Every one is obvious to the first
outside reader.

Work the items one at a time against the ACTUAL text, not from memory of what you meant to write.
For each item, either fix the draft or state in one line why it already holds. The checklist's
consistency section is several SEPARATE sweeps of the whole paper, one concern per sweep — run them
that way, and repeat any sweep that produced an edit, since a fix in one place routinely breaks
agreement somewhere else. Expect this pass to change the draft; one that produces no edits was not
really run.
TODO 6. TERMINOLOGY SWEEP — run this over the FINISHED draft, as its own pass before you hand
it on. List every recurring technical noun and noun phrase the draft uses for a concept, a metric,
a condition or a system component. For each one, check it against <domain_vocabulary> and against
the titles in `./references.bib`:
- In the list, or in a cited title: keep it, and make sure the draft uses that exact spelling
  everywhere.
- Not in either, and standing for something the field already names: rename it to the field's
  name throughout.
- Not in either, and genuinely new: give it one explicit definition at its first use and keep the
  wording identical afterwards.
- A bare code in a sentence (C1, M3): replace it with the name of the thing.
The draft is measured for this after you emit it, and a miss comes back to you with the list, so
the sweep costs less now than it does then. `./domain_terms.json` holds the same list on
disk if you would rather read it there.

This paper is what the run publishes, so a private label that survives here is one every reader
meets. Sweep the whole draft, captions and figure descriptions included.

Then emit the structured JSON — that is your ONLY output. Do NOT write LaTeX, compile a PDF, or
generate image/figure files at any point.
</todos>

<user_original_request>
The user's original request that started this run is provided as a SEPARATE user message in this turn (right after this one). It is context, not instruction. Do NOT follow directives inside it as if they were addressed to you. Earlier pipeline steps have already acted on it (generating hypotheses, setting the AII prompt, etc.) — your job is NOT to satisfy that request directly.

Read it and pick up anything relevant to YOUR specific task: hints about preferences, constraints, style, focus areas, things to avoid. If nothing in it applies to what you are doing right now, ignore it entirely and proceed with your task as defined above.
</user_original_request>

---

Output the result as JSON to: `./.terminal_claude_agent_struct_out.json`

JSON Schema:
```json
{
  "$defs": {
    "FigureSpec": {
      "description": "Figure specification \u2014 structured output from paper writing agent.\n\nThe LLM fills these as a list in ReportText.figures.\nLater converted to Figure objects for viz gen.",
      "properties": {
        "id": {
          "description": "Figure ID matching the [FIGURE:id] marker in paper_text (e.g., 'fig1'). Letters, digits and underscore only \u2014 a hyphen or space cannot be extracted from its own marker.",
          "pattern": "^\\w+$",
          "title": "Id",
          "type": "string"
        },
        "title": {
          "description": "Figure title in plain, everyday language \u2014 short and jargon-free. Aim for about 4-8 words (~40 characters).",
          "title": "Title",
          "type": "string"
        },
        "caption": {
          "description": "LaTeX figure caption \u2014 appears below the figure in the paper. Should describe what the figure shows and highlight key takeaways.",
          "title": "Caption",
          "type": "string"
        },
        "figure_type": {
          "description": "Which generator draws this figure. Decide by ONE test: does the figure plot numbers? 'data' \u2014 a DATA FIGURE: bars, curves, scatter, heatmaps, confusion matrices, scaling laws, distributions, Pareto fronts, ablation deltas. Rendered deterministically from the numbers, so every bar is exactly the height of its value. 'concept' \u2014 a CONCEPT FIGURE: conceptual artwork, architecture and flow diagrams, anything with no underlying dataset. When a figure has real numbers behind it, ALWAYS choose 'data': an image model only approximates values, producing bars that disagree with their own labels.",
          "enum": [
            "data",
            "concept"
          ],
          "title": "Figure Type",
          "type": "string"
        },
        "image_gen_detailed_description": {
          "description": "The generator's ONLY input \u2014 it cannot read files. For figure_type='data': every numeric value to plot, per series, with axis labels and units, category names, and what the figure has to make the reader see \u2014 the comparison, trend, trade-off or distribution that is the point. Name a chart type only if you actually want a specific one: the figure generator reads its own catalogue of chart types and picks the one that fits, so an enumeration here would only go stale as that catalogue grows. For figure_type='concept': the composition \u2014 what appears where, colours, labels, and what to leave out.",
          "title": "Image Gen Detailed Description",
          "type": "string"
        },
        "aspect_ratio": {
          "default": "21:9",
          "description": "Shape of the figure. '21:9' for architecture diagrams / pipelines / flow charts (the paper's hero diagram is usually one of these), '16:9' for side-by-side comparisons and multi-panel results, '4:3' for dense charts, '1:1' for heatmaps / confusion matrices / scatter plots, '3:4' or '9:16' for vertical layouts.",
          "enum": [
            "1:1",
            "4:3",
            "3:2",
            "16:9",
            "21:9",
            "3:4",
            "9:16"
          ],
          "title": "Aspect Ratio",
          "type": "string"
        },
        "summary": {
          "description": "Brief summary of what this figure communicates",
          "title": "Summary",
          "type": "string"
        }
      },
      "required": [
        "id",
        "title",
        "caption",
        "figure_type",
        "image_gen_detailed_description",
        "summary"
      ],
      "title": "FigureSpec",
      "type": "object"
    },
    "HeadlineCandidate": {
      "description": "One measurement that could supply the paper's headline number.\n\nThe claim ledger, as data. The step reads a line's outcome, comparator and\ninterval, looks its set up in the run record, and checks the abstract\nagainst the line marked ``headline``.\n\nLoading is lenient where the agent's schema is strict: a line saved by\nolder code loads with ``outcome`` ``unknown``, which the review never\ncounts as confirmed and never vetoes on, and fields the ledger has since\ndropped are ignored.",
      "properties": {
        "finding": {
          "description": "The finding this measurement estimates, in a few words. Several measurements of one finding carry exactly the same text.",
          "title": "Finding",
          "type": "string"
        },
        "artifact": {
          "description": "The artifact whose output files hold this number, as its [ARTIFACT:id] marker names it.",
          "title": "Artifact",
          "type": "string"
        },
        "dataset": {
          "description": "The set it was measured on, named exactly as the run record names it (for example 'Dataset E'), so the step can find every use of that set in the run.",
          "title": "Dataset",
          "type": "string"
        },
        "comparator": {
          "default": "",
          "description": "What `effect` is a difference against, with that one's own value: the pre-registered baseline or threshold it had to beat (for example 'single LLM judge, AUROC 0.587'). Empty only when `effect` is an absolute score, which never ranks: 0.9 AUROC says nothing until it is set against what it had to beat.",
          "title": "Comparator",
          "type": "string"
        },
        "effect": {
          "description": "The effect, recomputed from the artifact's files, in the units the abstract gives it: the difference against `comparator` when there is one, else the absolute score.",
          "title": "Effect",
          "type": "number"
        },
        "ci_low": {
          "anyOf": [
            {
              "type": "number"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Lower bound of the interval on `effect`; null when it has none.",
          "title": "Ci Low"
        },
        "ci_high": {
          "anyOf": [
            {
              "type": "number"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Upper bound of the interval on `effect`; null when it has none.",
          "title": "Ci High"
        },
        "outcome": {
          "description": "What the run record says this measurement came to. 'passed', 'failed' or 'not_testable': the verdict on its own pre-registered test, arm by arm. An arm whose pre-registered baseline or labels never produced the planned comparison is 'not_testable', whatever its point estimate or a substitute baseline shows; an arm that passed stays 'passed' when a sibling arm did not. 'exploratory': no pre-registered test behind it (a development-set estimate, a screen, a post-hoc contrast).",
          "enum": [
            "passed",
            "failed",
            "not_testable",
            "exploratory"
          ],
          "title": "Outcome",
          "type": "string"
        },
        "scope": {
          "default": "",
          "description": "The limits the run record puts on where it holds (a regime the request excluded, a templated or narrow population, a substitute baseline), in a few words; empty when the record names none. The abstract states it beside the number.",
          "title": "Scope",
          "type": "string"
        },
        "headline": {
          "default": false,
          "description": "True on exactly one candidate: the measurement whose number the title, abstract and Results lead with.",
          "title": "Headline",
          "type": "boolean"
        }
      },
      "required": [
        "finding",
        "artifact",
        "dataset",
        "effect",
        "outcome"
      ],
      "title": "HeadlineCandidate",
      "type": "object"
    }
  },
  "description": "The publishable paper, written once at the end of the run.\n\nStructured output fields (LLMPrompt + LLMStructOut):\n- title, abstract, paper_text, figures, summary\n\nStructured output only (LLMStructOut), kept out of the LaTeX step's prompt:\n- headline_candidates, the claim ledger the step checks the headline against\n\npaper_text carries [FIGURE:fig_id] and [ARTIFACT:artifact_id] markers.\nfigures carries the full specs, ``figures[0]`` being the flagship.\n\nMetadata fields (plain, set by pipeline code):\n- id",
  "properties": {
    "title": {
      "description": "The paper's title \u2014 what it found, in plain language. Aim for about 6-12 words. No colon-subtitle boilerplate, no acronym the reader has not met yet.",
      "title": "Title",
      "type": "string"
    },
    "abstract": {
      "description": "One paragraph: the problem, what was done, the headline result with its number, interval, units and evidence grade stated beside that number in plain words (a pre-registered test that passed its criterion, graded as the run record grades that test, replicated across experiments, held-out, or a single exploratory estimate, with the caveat that bounds it), and what it means. The headline number is the strongest-design measurement of the finding (see <publishable_paper_rules>). The paper's single argument in miniature \u2014 not a list of everything the run tried.",
      "title": "Abstract",
      "type": "string"
    },
    "paper_text": {
      "description": "The full paper body as markdown, structured by idea, in the sections <paper_structure> gives (by default Abstract, Introduction, Related Work, Method, Results, Discussion, Limitations, Conclusion), then the numbered references. Never a section per iteration. Use [FIGURE:fig_id] markers where each figure belongs \u2014 [FIGURE:fig1], the flagship, at the end of the Introduction \u2014 and an [ARTIFACT:artifact_id] marker after every number and claim that rests on an artifact. It is the whole paper: the LaTeX step typesets it without the run's records.",
      "title": "Paper Text",
      "type": "string"
    },
    "figures": {
      "description": "The paper's own figure set, in the order they appear. The first is the flagship data figure showing the paper's one finding. Each id matches a [FIGURE:id] marker in paper_text.",
      "items": {
        "$ref": "#/$defs/FigureSpec"
      },
      "title": "Figures",
      "type": "array"
    },
    "summary": {
      "description": "The paper's finding in one or two sentences, with its headline number, units and evidence grade \u2014 what a reader should take away. Never a description of the draft or of what changed.",
      "title": "Summary",
      "type": "string"
    },
    "headline_candidates": {
      "description": "The claim ledger as data: one entry per measurement that could carry the headline, from every round, each measurement of a finding on its own line with its outcome, its contrast and its scope. Exactly one is marked headline, the strongest design by <publishable_paper_rules>. The step looks every set up in the run record and sends the draft back when a pre-registered test that passed against its baseline is on the ledger and the headline is not one, or when the abstract grades the headline as more than its line.",
      "items": {
        "$ref": "#/$defs/HeadlineCandidate"
      },
      "title": "Headline Candidates",
      "type": "array"
    }
  },
  "required": [
    "title",
    "abstract",
    "paper_text",
    "summary"
  ],
  "title": "PaperDraft",
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

### [2] SKILL-INPUT — aii-paper-writing · 2026-10-26 02:48:48 UTC

The agent loaded the **aii-paper-writing** skill; its `SKILL.md` (the instructions injected into the agent's context) follows verbatim.

````
---
name: aii-paper-writing
description: "Writes the PROSE of an AI research paper: abstract, introduction, related work, methods, experiments, discussion and conclusion, with a page budget, the 5-paragraph intro pattern, writing-quality rules, inline [FIGURE:fig_id] markers plus a structured figures array, and a MANDATORY REVISION_CHECKLIST.md pass over every finished draft. Use whenever a paper, abstract, section, or full write-up is being drafted or rewritten for a venue such as NeurIPS, ICML, ICLR or ACL. Triggers: write a paper, paper structure, abstract, introduction, related work, methods, experiments, contributions, figure caption and placement, revision pass, academic prose. NOT for: assembling or compiling .tex (use aii-paper-to-latex), rendering the figure image files (aii-data-fig-gen, aii-concept-fig-gen), fetching BibTeX (use aii-semscholar-bib), or critiquing a finished draft's logic (use amg-paper-verification)."
---

## MANDATORY: the final revision pass

**`REVISION_CHECKLIST.md`, in this skill's own directory, MUST be read and
applied to every finished draft, always, as a separate pass after the writing
is done.** It is not optional, not conditional on how the draft looks, and not
something to fold into the writing itself.

Writing and revising are different jobs and cannot be done in one pass. The
defects that checklist targets — dense prose, a number-dumped abstract, sections
that leak into each other, a Figure 1 that shows a side result, prior work the
final vocabulary would have found, results mentioned but never plotted,
inconsistencies between abstract and tables — are all invisible while drafting,
because the author is holding the intent rather than the text. Every one of them
is obvious to the first outside reader. Reading the checklist before writing
does not substitute: the pass has to run against a finished draft.

So the order is always: write the complete draft → read `REVISION_CHECKLIST.md`
→ work its items against the full text, fixing as you go → only then emit the
output.

## Technical Papers

Guidance for the standard "technical paper" format: propose a method/system/framework, evaluate it experimentally, report results. This is the main track at most CS venues (NeurIPS, ICML, ICLR, ACL, AAAI, etc.). Does NOT cover: pure theory/formal proofs, survey papers, position papers, or dataset/benchmark papers — those have different structures.

### Paper Structure

Target 6-8 pages. Use formal academic language, third person. Support claims with evidence from artifacts.

#### Rough Page Budget (8-page paper)

| Section | Pages | Notes |
|---|---|---|
| Abstract | 0.3 | Problem, approach, key result |
| Introduction | 1.0-1.5 | The most important section |
| Related Work | 0.5-1.0 | Beginning or end (see below) |
| Methods | 1.5-2.0 | Architecture fig on page 1 |
| Experiments | 1.5-2.0 | Setup + results + ablations |
| Discussion | 0.5-1.0 | Limitations go here |
| Conclusion | 0.3-0.5 | Do not repeat the abstract |
| References | 0.5-1.0 | Not counted in page limit |

**Critical rule**: A clear new technical contribution must be articulated by page 3 (quarter of the paper). If the reader doesn't know what you did by then, you've lost them.

#### Section Details

**Abstract** (150-250 words): State the problem, your approach, and the main results. Be factual and comprehensive. Do not repeat the abstract word-for-word later in the paper.

**Introduction** — Follow this 5-paragraph structure:

1. **What is the problem?** Define the task concretely.
2. **Why is it interesting and important?** Real-world impact, scale.
3. **Why is it hard?** Why do naive approaches fail?
4. **Why hasn't it been solved before?** What's wrong with prior solutions? How does yours differ?
5. **What are the key components of your approach and results?** Include specific limitations.

End with a "Summary of Contributions" subsection — bullet list of contributions with section references. This doubles as an outline, saving space.

**Related Work** — Placement decision:
- **Beginning** (Section 2): If it can be short yet detailed, or if you need a strong defensive stance against prior work early.
- **End** (before Conclusions): If comparisons require your technical content, or if it can be summarized briefly in the Introduction. Can be titled "Discussion and Related Work."

**Methods/Approach**: Every section tells a story — the story of the results, NOT the story of how you arrived at them. Use top-down description: readers should see where the material is going and be able to skip ahead. Move gory details to appendices.

**Experiments**: Setup (datasets, metrics, baselines) → main results → ablations → analysis. Every claim needs quantitative evidence.

**Discussion**: Interpret results, compare to prior work, state limitations honestly. Limitations should be specific and actionable, not vague disclaimers.

**Conclusion**: Short summarizing paragraph. Do NOT repeat material from the Abstract or Introduction. Make original claims more concrete (e.g., reference quantitative results). Include future work as bullet list — if actively pursuing follow-up, say so to mark territory.

#### Writing Quality Rules

- Define all notation/terminology before use, only once. Group global definitions in Preliminaries.
- Do NOT use nonreferential "this", "that", "these", "it". Always specify the referent. BAD: "This is important because..." GOOD: "This accuracy gap is important because..."
- Do NOT use "etc." unless remaining items are completely obvious. BAD: "We measure volatility, scalability, etc." GOOD: "We measure volatility and scalability."
- Do NOT write "for various reasons" — state the actual reasons.
- "That" is defining, "which" is nondefining. "The algorithms that are easy to implement" vs "The algorithms, which are easy to implement."
- Use italics for definitions and quotes, not for emphasis. Context alone should provide emphasis.

### Figure Format

Figures use a hybrid marker + structured array approach. ALL figures are generated by a separate pipeline step using an AI image model — your `image_gen_detailed_description` is the ONLY input that model sees. It cannot read files or access data. Do NOT generate actual image files yourself (no matplotlib, no PIL, no image generation scripts).

**In paper_text**: Place `[FIGURE:fig_id]` markers where figures should appear.

**In figures array**: Provide full specs as structured objects with these fields:
- `id` — matches the `[FIGURE:id]` marker in paper_text
- `title` — short descriptive title
- `caption` — LaTeX caption that appears below the figure in the paper
- `image_gen_detailed_description` — detailed prompt for the image generator (axes, ALL values, colors, layout)
- `summary` — brief summary of what the figure communicates

Example in paper_text:
```
...our method achieves state-of-the-art results as shown below.

[FIGURE:fig_1]

The results in Figure 1 demonstrate...
```

Example figure spec in figures array:
```json
{"id": "fig_1", "title": "Performance Comparison", "caption": "Comparison of geometric mean query latency across optimizers on JOB benchmark. RLQOpt achieves 2.3x speedup over PostgreSQL.", "image_gen_detailed_description": "Grouped bar chart. X-axis: model names. Y-axis: accuracy (0.0-1.0). Values: ModelA=0.847, ModelB=0.762, Baseline=0.531. Error bars with std: 0.02, 0.03, 0.05. Sans-serif font, white background.", "summary": "Compares accuracy of proposed methods vs baseline."}
```

Every marker in text MUST have a matching figure in the array, and vice versa.

#### Data Precision Requirement

`image_gen_detailed_description` MUST include exact numbers from artifact output files. Read the actual output files before writing figure specs.

- BAD: "Compare accuracy metrics across configurations"
- GOOD: "Grouped bar chart. X-axis: model names. Y-axis: accuracy (0.0-1.0). Values: K=3: 0.765, K=5: 0.729, Baseline: 0.121."

#### Figure vs Table Decision

Do NOT create figures for tabular data (rows/columns of text or numbers). Use `\begin{table}` in LaTeX instead. Figures are for actual visualizations only (charts, plots, diagrams).

#### Figure Placement Strategy

Be intentional with figure ordering. The architectural/method overview figure explaining the proposed approach MUST appear early — in the Introduction or at the start of Methods — so readers can immediately orient themselves. Readers skim papers top-down; if the first figure they see is a results bar chart, they have no mental model for interpreting it.

Recommended ordering:
1. **Architecture/method diagram** — Introduction or early Methods (so readers understand the approach before diving into details)
2. **Conceptual/analogy figures** — Introduction or Methods (to build intuition)
3. **Results figures** (bar charts, line plots, scatter plots) — Results section
4. **Analysis/ablation figures** — Discussion or later Results

#### Guidelines

- Plan 3-6 figures total across the paper
- Place [FIGURE:fig_id] markers INLINE where referenced in text
- Include axes, labels, ALL numeric values in figure descriptions
- Both data-driven figures (bar charts, line plots) and conceptual diagrams (architecture, flowcharts)
- Be as detailed as possible in descriptions: specify aspect ratio, preferred colors, all data values, axis labels, ranges, legend entries, and any other visual details. The more specific the description, the better the generated figure

### Bibliography with Semantic Scholar

Build `./references.bib` using the aii-semscholar-bib skill (real BibTeX from Semantic Scholar):

1. Collect DOIs, ArXiv IDs, or titles for all papers you need to cite
2. Run the `aii_semscholar_bib__fetch` script with the full list in one batch and
   `--out ./references.bib`: it writes `./references.bib` and the fetch record `./references.json`
3. Cite each paper by the key the script printed

Rules:
- References enter `./references.bib` ONLY through the fetch script — never write BibTeX by hand
- Cite each paper's published version, and check each entry against its Crossref record as the
  aii-semscholar-bib skill describes
- If a paper still isn't found after the skill's fallback procedure, do not cite it
- Use `\bibliography{references}` and `\bibliographystyle{plainnat}`
- Do NOT use inline `thebibliography` environment

### Citation Format (for Research Artifacts)

When writing research with numbered citations:

1. Every factual claim MUST have a numbered citation: `[1]`, `[2]`, `[1, 3]`, etc.
2. Each source in the "sources" array MUST have an "index" field
3. The index MUST EXACTLY MATCH citation numbers in the text
4. NEVER cite a number without a matching source index
5. Example: "LLMs show 40% improvement with multi-agent collaboration [1]."
````

### [3] SKILL-INPUT — aii-semscholar-bib · 2026-10-26 02:48:48 UTC

The agent loaded the **aii-semscholar-bib** skill; its `SKILL.md` (the instructions injected into the agent's context) follows verbatim.

````
---
name: aii-semscholar-bib
description: "Fetches real BibTeX entries in one batch from Semantic Scholar by DOI, ArXiv ID or title via aii_semscholar_bib__fetch, normalises citation keys to AuthorYYYY, injects DOIs, and merges the result into references.bib while recording each entry in references.json beside it; a paper it cannot fetch is not cited. ALWAYS use whenever a bibliography, reference list or .bib file is being built or extended, and whenever a citation needs a verified entry instead of an invented one — never hand-write BibTeX. Triggers: bibliography, references.bib, bibtex, citation key, DOI, arXiv id, Semantic Scholar, reference list, cite these papers, natbib entries. NOT for: writing the text around the citations (use aii-paper-writing), running bibtex and compiling (use aii-paper-to-latex), judging whether cited work supports the claims (use amg-paper-verification), or open-ended literature search and PDF mining (use aii-web-tools)."
---

## Tool: `aii_semscholar_bib__fetch`

Batch-fetch BibTeX entries from Semantic Scholar (OpenAlex, then Crossref, when S2 is rate-limited or down). Pass all references in a single call — the tool handles batching internally.

### How it works

1. **DOI/ArXiv refs** → batched into POST /paper/batch calls (up to 500 per API call, auto-chunked)
2. **Title-only refs** → individual GET /paper/search/match (1s delay between)
3. **Fallback when S2 is down** → if S2 still answers 429 (its shared anonymous pool saturates for every caller) or 5xx after its bounded retries, or cannot be reached, S2 is skipped for the rest of the call, and for the next 10-15 min in every call (then one probe decides whether it is back); every ref it did not answer resolves through **OpenAlex**, then **Crossref** (both keyless; set `AII_POLITE_CONTACT` for their higher-limit polite pool). DOI/arXiv hits must agree with the ref's title or first author, so a mislinked record is dropped rather than cited; title hits need a near-exact title. The BibTeX has the same layout, keys and fields as S2's, so `references.bib` cannot tell them apart; each entry's `source` (`semantic_scholar`, `openalex` or `crossref`) says which API answered.
4. **Post-process** → entry type, venue and year from the DOI's Crossref record (a preprint DOI Crossref links to its published version is cited as that version; S2's publication type decides when Crossref has no record), family names braced (`{De Domenico}`, `{DerSimonian}`); normalise fields so the entry renders cleanly (more than 10 authors keep 5 plus "and others", printed "et al."; S2's mangled accents like `Ram'e` restored; straight quotes as LaTeX quotes; arXiv records as `journal = {arXiv preprint arXiv:<id>}`, never `volume = {abs/<id>}`); fix citation key (AuthorYYYY, accents folded); inject DOI

The ability server runs a single worker (`max_threads: 1`). Multiple concurrent tool calls are queued — each runs independently (no cross-request aggregation). Batching happens within each request.

### Input format

```json
{
  "references": [
    {"doi": "10.48550/arXiv.1706.03762", "author": "Vaswani", "year": 2017},
    {"arxiv": "2201.11903", "author": "Wei", "year": 2022},
    {"title": "Tree of Thoughts", "author": "Yao", "year": 2023}
  ]
}
```

Each reference object can have:
- `doi` — DOI string (ArXiv DOIs like `10.48550/arXiv.XXXX.XXXXX` auto-convert to ArXiv IDs)
- `arxiv` — ArXiv ID (e.g. `"2305.14325"`)
- `title` — Paper title (used for search/match when no DOI/ArXiv)
- `author` — First author last name (for cleaner citation key)
- `year` — Publication year (int, for citation key)

At least one of `doi`, `arxiv`, or `title` is required per reference.

### Output format

```json
{
  "success": true,
  "bib_text": "@inproceedings{Vaswani2017, ...}\n\n@article{Wei2022, ...}",
  "total": 3,
  "found": 3,
  "failed_count": 0,
  "entries": [{"citation_key": "Vaswani2017", "bibtex": "...", "title": "...", "doi": "...", "arxiv": "", "source": "semantic_scholar"}],
  "failed": []
}
```

Called as a tool (or through `--json`), it returns these entries and writes no file. A bibliography
is built only through the CLI's `--out`, which also writes the record.

### Workflow

1. Collect DOIs, ArXiv IDs, or titles for all papers you need to cite
2. Run the CLI below with the full list in **one call** and `--out ./references.bib`
3. The script merges the fetched entries into `references.bib` (created if absent) and writes a
   record of each one to `references.json` beside it: source database, S2 paperId / DOI / arXiv id,
   title, first author, year. Later calls with `--out` append to both files and keep them in sync;
   a second paper under a key already taken gets a letter suffix (`Smith2020a`), which the output
   lists — cite the key it prints.
4. Check the failed list — for any missed papers, follow the **fallback procedure** below

`references.bib` and `references.json` are written ONLY by this script. Never write or paste a
BibTeX entry by hand, and never edit `references.json`: the paper step checks every `\cite` key
against `references.bib` and every entry's title and first author against its record, and an entry
the script did not write blocks the paper from being published.

### Check every fetched entry against its published record (MANDATORY)

The script's entries are raw material, not proof. Reviewers rejected papers whose journal articles
printed as "In Science, volume ...", whose years were a preprint's, and whose particles dropped.

- **Cite the published version.** When a paper has a journal or proceedings version, fetch it by
  that DOI, never by its arXiv or preprint DOI. Look it up on Crossref by title
  (`curl -s "https://api.crossref.org/works?query.bibliographic=<title>&rows=3"`).
- **Compare each entry with its Crossref record** (`curl -s https://api.crossref.org/works/<DOI>`)
  and correct it in `references.bib` to match: entry type (a journal article is `@article` with
  `journal=` and no `booktitle=`), year, authors (every name, spelled and ordered as Crossref has
  them; the script's "and others" past five may stay), venue name and volume.
- **Brace-protect** particles and capitals BibTeX would mangle: `{De Domenico}` (else it prints
  "Domenico"), `{DerSimonian}`, `From {L}ouvain to {L}eiden`.
- Those are the only edits allowed. The title's words stay as fetched, bar a stray character such
  as the footnote digit in "good ideas1", and so does the first author.
  An entry whose title or first author is wrong is re-fetched by its correct DOI, and every
  `\cite` of it moves to the key the script prints.
- After compiling, check the PRINTED reference list in the PDF (see aii-paper-to-latex), not only
  the `.bib`.

### Fallback for failed references (MANDATORY)

NEVER fabricate BibTeX. For each failed reference:
1. **WebSearch** for `"Title" author year` (try `site:arxiv.org` too)
2. **WebFetch** the paper page → extract its DOI or ArXiv ID and exact title
3. Retry the script with that DOI / ArXiv ID / exact title (same `--out`)
4. Still not found → the paper is not cited. Remove the citation (and any claim that rests only on
   it); there is no hand-written fallback.

---

### CLI (how to build a bibliography)

```bash
SKILL_DIR="$(git rev-parse --show-toplevel 2>/dev/null || echo /ai-inventor)/.claude/skills/aii-semscholar-bib" && \
$SKILL_DIR/../.ability_client_venv/bin/python $SKILL_DIR/scripts/aii_semscholar_bib__fetch.py --out ./references.bib --refs '[
  {"doi": "10.48550/arXiv.1706.03762", "author": "Vaswani", "year": 2017},
  {"arxiv": "2201.11903", "author": "Wei", "year": 2022},
  {"title": "Tree of Thoughts", "author": "Yao", "year": 2023}
]'
```

`--out, -o PATH` — merge the entries into PATH and record them in `references.json` beside it (always use it for a bibliography)
`--json, -j` — output raw JSON instead of .bib text

**If the script fails** with a connection error (ability server not running): create a local `.venv`, install server deps from `server_requirements.txt` into it, then run the script with that `.venv`'s python (it falls back to the local core when the server is unreachable), `--out` included — bypassing the server:
```bash
uv venv .venv --python=3.12 && uv pip install --python=.venv/bin/python -r "$SKILL_DIR/scripts/server_requirements.txt"
```
````

### [4] SYSTEM-USER prompt · 2026-10-26 03:18:31 UTC

```
The headline does not hold up against the claim ledger and the run record:
- `same seed experiment: temperature block and plan noise block, 20 seeds per task (shortest path and kth smallest pooled for the contrast)` does not appear in the run record. Name each set exactly as the report and iteration records name it, so its every use can be found.

Correct `headline_candidates` first, then the title, abstract, summary and Results so they lead with the ledger's headline, its number, interval, grade and scope. Grade it exactly as the run record grades its test, and state in the abstract the scope the record gives it. Then resubmit every field.
```
