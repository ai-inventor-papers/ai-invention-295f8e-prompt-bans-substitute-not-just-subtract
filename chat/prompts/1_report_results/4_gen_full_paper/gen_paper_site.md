# gen_paper_site — report_results

> Phase: `gen_paper_repo` · `gen_full_paper`
> Run: `gen_paper_repo_c164ac661673` — A Random Activation Push Changes a Code Model's Algorithm Where Temperature Does Not
>
> Full, verbatim record of every prompt the AI Inventor pipeline gave this agent — system-user, human-user and skill-input — in the order they landed. Nothing truncated.

## Task: `gen_paper_site` (terminal_claude_agent)

### [1] SYSTEM-USER prompt · 2026-10-26 18:19:51 UTC

````
<design_philosophy>
You are building ONE web page whose only job is to let a reader understand a research paper faster
than they could by opening the PDF. Every decision on the page is judged against that.

WHAT "FASTER" MEANS HERE
- A reader who leaves after thirty seconds still knows the finding and the number behind it.
- A reader who stays five minutes has the method, the figures and the caveats, in that order.
- Nothing on the page is there because a layout had a slot for it.

ACCURACY IS THE HARD CONSTRAINT
Every number, name and claim comes from the paper as written — you read them out of the LaTeX
source, the only source this page has. You never change a number's precision, never restate a
comparison the paper did not make, and never invent a headline figure to fill a card. A page that
looks excellent and misreports one result is worse than no page, because the PDF beside it says
something else and a reader will find that out.

CRAFT, AND THE LOOK TO AVOID
The failure mode for a generated page is a look every reader now recognises on sight: a
purple-to-blue gradient banner, three identical cards with emoji headings, and body text set in
one weight at one size. Avoid all of it.
- Type carries the design. One system font stack, a real scale with visible jumps between levels
  rather than a creep of similar sizes, long-form text around 17-19px with a measure of 65-75
  characters and generous line height. Weight and size do the emphasis; colour rarely does.
- Colour is restrained. A light, near-white ground, one dark ink for text, one accent used for
  links and the current-section marker and almost nothing else. No gradients as decoration.
- Space does the work that borders and boxes would do badly. Sections separated by real vertical
  rhythm, cards defined by alignment and a single hairline rather than by shadow stacks.
- Structure over ornament: no emoji as section markers, no icon fonts, no badge clutter, no
  animated counters.
- Motion is a courtesy. A short transition on a lightbox or a hover state is welcome; anything
  that moves on scroll, autoplays, or delays the reader is not — and all of it stops under
  prefers-reduced-motion.
- Every interactive element works with a keyboard and says what it is to a screen reader. That is
  part of the craft, not a checklist bolted on at the end.

FINISH IT
The page is done when you have opened it in a browser, read it at a phone width and a desktop
width, tabbed through every control, and found nothing to fix. Not before.
</design_philosophy>

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
Your workspace: `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_assemble_paper/paper`

CRITICAL: Every file you create, write, or save MUST be inside this workspace directory (subdirectories OK). You MUST NOT write files anywhere outside this path — external paths are READ-ONLY. Use absolute paths for all file operations.

EVERY file write MUST start with `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_assemble_paper/paper/`:
GOOD: `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_assemble_paper/paper/file.py`, `/ai-inventor/aii_data/runs/run_jSassd-YWLVC/4_gen_paper_repo/_4_assemble_paper/paper/results/out.json`
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
Build the paper's public web page: ONE self-contained `index.html` that lets a reader grasp
this paper faster than opening the PDF would. It is published as this run's GitHub Pages site, so
it is the first thing anyone sees.
</task>

<tool_use>
Maximize parallel tool calls. Parallelize independent operations, only sequentialize dependencies.
- Multiple searches/fetches on different topics → parallel in one turn
- Search then fetch results → sequential (need URLs first)
</tool_use>

<what_is_already_here>
Your workspace is the finished paper folder. It already holds everything the page is made of, and
you must not change any of it — you are adding one file, not revising the paper.

- `paper.tex` — the FINAL paper, as it was actually written. It is the ONLY source for
  every claim, name and NUMBER that goes on the page. Earlier versions of this paper, the research
  report and any page written in an earlier session are not sources: where your memory of one
  differs from `paper.tex`, the paper wins.
- `paper.pdf` — the compiled paper. The page must NOT link to it by this local name:
  the PDF is published on the code branch and the page on a different one. Link to it at the
  full URL below instead.
- `references.bib` — the bibliography, when the paper has one.
- `figures/` — every figure the paper uses, flattened into one folder.
- `workspace/` — the scratch folder the LaTeX task worked in. Ignore it.
</what_is_already_here>

<available_figures>
Each line gives the path the PAGE must use, then the figure's title and caption. It is the same
path the file has on disk here: the publish step copies the page and its figures into one folder,
so what works in this workspace is what works on the live site.

- figures/fig1_v0.png [render from fig1_v0.pdf first] — "Same-seed algorithm changes: temperature against a task-state push" (caption: "Seeds (of 20) whose algorithm label changed under one shared random stream per seed, for Qwen3-8B on an 8-bit (FP8 W8A8) engine; grouped by task on the x-axis (shortest path/Dijkstra, k-th smallest/full sort, grid path/BFS), with four bars per task as in the legend below the axes. Light and mid grey bars sweep temperature over T = 0.3, 0.7, 1.0, 1.3 with thinking off and on; a seed counts as changed if its label differs anywhere across those four temperatures, and temperature changed no seed on any task it was run on (exact 95% upper bound 0.168 per seed). Thinking-mode cells are marked where they depart from the full 20-seed design: not run for k-th smallest, and completed on only 10 of 20 seeds for grid path ("0 of 10"). Light and dark blue bars add a random push to the model's task-specification hidden state at alpha=1 and alpha=2 (T = 1.0); each bar is the mean, over the 20 three-direction subsets of 6 independently sampled push directions, of how many seeds had their label differ from the unpushed arm anywhere among that subset, with whiskers at the subsets' minimum and maximum. The bracket over shortest path and k-th smallest gives the pre-registered paired contrast, push (alpha=1) minus temperature, pooled over those two tasks: 0.545 seeds changed per seed, 95% CI [0.41, 0.67], one-sided sign-flip p = 1.0e-5. This design ran on one FP8 engine only -- bf16 does not fit the 16 GB GPU used -- and was not rerun in bf16.")
- figures/fig2_v0.jpg — "Where the algorithm is decided" (caption: "Schematic illustration of the account and of the measurements (not data), using one minimum-spanning-tree example. Left to right: a rounded 'Prompt' box contains the task text 'Return the total weight of a minimum spanning tree of the graph.', with the task-defining words 'minimum spanning tree of the graph.' highlighted in light blue and bracketed as 'task-specification states (residual stream, blocks 12 to 23)'; two downward arrows above the box, labelled 'task-state exchange' and 'random task-state push', denote interventions applied to these states. An arrow leads to the 'shared opening (61 tokens)', shown as three representative monospace code tokens ('import heapq', 'graph = [[] for _ in range(n)]', '#') followed by an ellipsis marking the rest of the shared opening. A second arrow leads to a 'forking token' node, above which a thermometer icon is labelled 'temperature T: softmax(logits / T)' with the note 'changes the algorithm only here'. From the forking token, two branches lead to the token chips 'Kr' and 'Prim'; the orange bar beside each chip shows the token's probability at the fork — 0.72 for 'Kr', leading to the 'Kruskal' outcome box, and 0.27 for 'Prim', leading to the 'Prim' outcome box, with each bar's fill proportional to its value. A fan of four thin lines labelled 'phrasings' beside each outcome box denotes that one algorithmic idea is written out in many surface forms. A grey band spanning the bottom states the composed law 'P_T(A) = sum over openings w_T(O) x sum over forking tokens pi_T(t | O) x P(A | t)'. Blue marks the prompt-to-fork pipeline (boxes, arrows, the forking-token node and chips); orange marks the two realized algorithm outcomes and their fork probabilities. The 61-token opening length and the 0.72/0.27 fork split are the only numbers in the figure, drawn from teacher-forced measurements on this example; the diagram as a whole is a schematic of the proposed mechanism, not a plotted dataset.")
- figures/fig3_v0.png [render from fig3_v0.pdf first] — "Temperature multiplies phrasings, not algorithms" (caption: "Phrasing-cluster and distinct-algorithm counts across sampling temperature, under a shared random stream (Qwen3-8B, non-thinking mode, top-p 1, 20 seeds per task, one program per seed and temperature; same seeds as Figure 1 and Table 1). Solid lines with markers give phrasing clusters among the 20 same-seed programs on each task -- blue circles for grid path (BFS), orange squares for shortest path (Dijkstra), green triangles for k-th smallest (full sort) -- where a cluster is a connected component of programs whose identifier-normalised AST 4-gram Jaccard similarity is at least 0.8. The black dashed line with diamond markers gives distinct algorithms among the same programs, which is 1 on all three tasks at every temperature, as the in-figure annotation states (algorithm changed in 0 of 20 seeds per task; exact 95% upper bound 0.168 on the per-seed change rate). Phrasing diversity rises steeply with temperature on the grid-path task (3 to 13 clusters) and stays close to flat on the other two (1 rising to 2 on shortest path; constant at 2 on k-th smallest), while the dashed line never leaves 1.")
- figures/fig4_v0.png [render from fig4_v0.pdf first] — "Forking-token law against observed shares" (caption: "Predicted and observed share of the minority algorithm at four sampling temperatures (0.3, 0.7, 1.0, 1.3; top-p = 1, N = 100 generations per cell, shared random streams across temperatures), for six algorithm-choice units: three Qwen3-8B development units -- (a) trapped rain water: two pointers, (b) valid anagram: fixed count array, (c) minimum spanning tree weight: Prim -- and three held-out units -- (d) Gemma-3-4B substring search: built-in index, (e) Gemma-3-4B first/last position: binary search, (f) Llama-3.1-8B grid path: DFS. Black circles give the observed minority share with vertical Wilson 95% confidence intervals; the solid blue line with small markers is the composed forking-token law's prediction, fixed before any temperature sample; the dashed grey line is a flat-law reference (the T = 1 share held constant across temperature). Each panel title gives the mean absolute error, over the four temperature points, of the composed law and the flat law respectively. The composed law tracks the observed trend, rising or near-flat, on five of six panels, including both held-out Gemma-3-4B units (d, e); on the held-out Llama-3.1-8B grid-path unit (f) both the composed and flat lines stay nearly constant and neither tracks the non-monotonic observed points, consistent with that unit's pass rate falling from 0.22 to 0.04 between T = 0.3 and T = 1.3, where most generated programs become unusable.")
- figures/fig5_v0.png [render from fig5_v0.pdf first] — "Post-training widened the fork margin" (caption: "Fork margin — the teacher-forced log-probability gap, in nats, between the token class leading to the instruct model's default algorithm and the best alternative class — for Qwen3-8B (instruct; dark blue bars) and Qwen3-8B-Base (grey bars) on identical chat-templated token ids, across five coding tasks. Bars show the mean over five prompt templates; whiskers span the minimum to the maximum over those templates. A dotted vertical line and italic headers separate the three default tasks (grid path/BFS, connected components/union-find, shortest path/Dijkstra) from the two mixed units (minimum spanning tree weight/Kruskal, trapped rain water/prefix-and-suffix maxima); the number above each pair is post-training's gain in mean fork margin, instruct minus base: +3.27, +13.41 and +2.11 nats on the default tasks, +1.84 and +1.53 nats on the mixed units. Over the same five templates and the same programs, the base model's next-token entropy at 64 ordinary (non-decision) phrasing positions per program was only 0.21-0.34 nats higher than the instruct model's, so post-training's effect on the output distribution is concentrated at the forking token rather than spread across the prompt.")
- figures/fig6_v0.png [render from fig6_v0.pdf first] — "Where the five-name ban lands" (caption: "Activation-space maps of ten grid-search algorithms in Qwen3-32B (4-bit weights, thinking mode), with point coordinates from classical multidimensional scaling (MDS; arbitrary axis orientation, arbitrary units) of Euclidean distances between each algorithm's residual-stream centroid. Marker shape distinguishes the five algorithms named in the ban (cross: BFS, DFS, IDDFS, A*, greedy best-first) from the rest (circle). Marker fill colour, on the shared colour bar at right ("programs under the ban (of 50)", light grey to dark red, 0-8), gives how many of 50 programs sampled under the five-name ban implemented that algorithm. A thick black ring marks unit-weight Dijkstra, the non-banned algorithm written most often under the ban (6/50); a thin ring marks BFS, the modal default with no ban in effect (91/100, noted beside it). (a) Map built from named prompts (block 31): centroids of 300 forced "Implement <algorithm>" prompts (30 per algorithm, 10 algorithms), mean-pooled over the task-specification tokens; the top two MDS axes carry 50% and 17% of the variance. On a k=15 nearest-neighbour geodesic graph, unit-weight Dijkstra sits opposite the banned set (geodesic distance 1.63x the median distance among non-banned algorithms). (b) Map built from name-scrubbed programs (block 33): centroids of name-scrubbed, hidden-test-verified programs for the six algorithms with at least 10 programs (20 each, 17 for IDA*; 117 programs total), mean-pooled over the generated code tokens; the top two axes carry 48% and 40% of the variance. On the same k=15 construction, unit-weight Dijkstra instead sits at the edge of the banned set (0.67x the median). The two maps disagree on whether the ban's main survivor lands opposite the banned algorithms or beside them; the geometry is correlational, not a steering result.")
</available_figures>

<figure_requirements>
- Reference every figure as `figures/` plus its filename, exactly as listed above.
  The publish step copies the page and its figures into one folder together, so that relative
  path is what resolves on the live site; anything else breaks once published.
- A browser cannot draw a PDF in an image element. Data figures are delivered as vector PDF for
  LaTeX's benefit, so for each one check whether a PNG of the same name already sits in
  `figures/`; if it does not, or it is older than the PDF (a PNG left from before
  a re-plot shows the old figure), render one there at about 200 DPI with pdftoppm or pymupdf
  before referencing it. Renderable formats: .avif, .gif, .jpeg, .jpg, .png, .svg, .webp.
- The page shows the same version of each figure as the PDF: the file `paper.tex`
  includes, or the PNG rendered from it, never a sibling version.
- Write those PNG files into `figures/` and nowhere else — that folder is published, a
  new folder of your own is not.
- Use each figure's own caption. It was written from the rendered image by the agent that drew
  the figure. Do not invent new ones, and do not describe a figure you did not place on the page.
- Look at every figure before you place it. A figure whose axis labels are unreadable at the size
  you give it is worse than no figure. Any colour, marker, axis or panel the page names must be
  one the image actually has, encoding what the image says it encodes.
</figure_requirements>

<page_structure>
In this order, top to bottom:

1. HERO — the paper's title, the author line as the paper gives it, and a one-paragraph TL;DR in
   plain language: what was asked, what was found, and the single number that carries the finding.
   Not the abstract, and not a rewrite of it. Below it, every link the links section below
   lists, each at the exact URL given there.
2. CONTRIBUTIONS — the paper's actual contributions as three to five scannable cards, each a short
   heading plus one or two sentences. If the paper claims four things, show four cards, not five.
3. METHOD — a walkthrough a technically literate non-specialist can follow: what goes in, what
   happens to it, what comes out, and why the design is the way it is. Lead with the paper's own
   method figure when it has one.
4. RESULTS — the paper's real headline numbers, read out of `paper.tex`, each next to what it was measured on and what it is being compared against.
   A number that is not in the paper does not go on the page, and neither does a comparison the
   paper did not make. If a slot has no number, drop the slot.
5. FIGURE GALLERY — every figure, each with its caption, click-to-enlarge into a lightbox that
   closes on Escape, on a click outside, and on a visible close control.
6. LIMITATIONS — what the paper says it does not show. Verbatim in substance; do not soften it.
7. FOOTER — every link from the links section again, and the citation if the paper carries one.

A sticky section navigation runs alongside all of it and marks where the reader currently is.
Do NOT write its highlighting yourself: hand-written ones kept a stale section lit after a jump
back to the top, or never reached the short last sections. Instead give the nav element a
`data-scrollspy` attribute, make each of its links `href="#<id of that section>"`, style the
current link through `a.active` (it also gets `aria-current`), and paste this script VERBATIM
into the page's script element at the end of the body. It lights the section in view, the last one once the page is
scrolled to its end, and nothing while the reader is above the first linked section:

```js
/* aii-scroll-spy v1: paste verbatim */
(function () {
  var links = [], targets = [];
  document.querySelectorAll('[data-scrollspy] a[href^="#"]').forEach(function (a) {
    var el = document.getElementById(a.getAttribute('href').slice(1));
    if (el) { links.push(a); targets.push(el); }
  });
  if (!links.length) return;
  var queued = false;
  function current() {
    var view = window.innerHeight;
    var doc = document.documentElement;
    var atEnd = window.scrollY > 0 && view + window.scrollY >= doc.scrollHeight - 2;
    var line = atEnd ? view - 1 : Math.min(view * 0.3, 200);
    var best = null, bestTop = -Infinity;
    targets.forEach(function (el) {
      var top = el.getBoundingClientRect().top;
      if (top <= line && top > bestTop) { best = el; bestTop = top; }
    });
    return best;
  }
  function update() {
    queued = false;
    var el = current();
    links.forEach(function (a, i) {
      var on = targets[i] === el;
      a.classList.toggle('active', on);
      if (on) a.setAttribute('aria-current', 'location');
      else a.removeAttribute('aria-current');
    });
  }
  function schedule() {
    if (!queued) { queued = true; window.requestAnimationFrame(update); }
  }
  window.addEventListener('scroll', schedule, { passive: true });
  window.addEventListener('resize', schedule);
  window.addEventListener('load', schedule);
  if (window.ResizeObserver) new ResizeObserver(schedule).observe(document.body);
  update();
})();
```
</page_structure>

<technical_requirements>
- ONE file. All CSS in a style element, all JavaScript in a script element, both inline in
  `index.html`. No build step, no bundler, no framework, no external script, stylesheet, web
  font or analytics — nothing fetched at load time. The page must render with the network off,
  and the only local files it may point at are the figures listed above; the PDF is linked at
  its full URL, never by its local name.
- A complete HTML document: the file opens with exactly this markup, then the title and the
  style element, and closes head before the body. The viewport tag is what makes a phone lay the
  page out at its own width; without it the page renders 980px wide and shrinks to tiny text.
```html
<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
```
- System font stack only, since no font may be downloaded.
- Light theme. Responsive from a 360px phone to a wide desktop, with no horizontal page scroll;
  wide content scrolls inside its own container.
- Honour prefers-reduced-motion: under it, transitions and any scroll-driven effect stop.
- Keyboard-navigable: every control reachable by Tab in a sensible order, a visible focus ring,
  the lightbox trapping focus while open and returning it to the thumbnail on close, and a skip
  link to the main content.
- Semantic HTML: one top-level heading, headings that descend without skipping, landmark elements,
  and alt text on every image that says what the figure shows rather than repeating its number.
- No emoji anywhere. No purple-to-blue gradients. No decorative icon fonts.
- Keep the whole file comfortably under a megabyte.
</technical_requirements>

<writing_register>
Write in the register of the field's best papers (the paper this page presents, which was written to them), not in the register of a language
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

<links>
Use these URLs VERBATIM wherever the page links to the paper, the report or the code. Do not
shorten them, do not turn any of them into a relative path, and do not compose one of your own.

- The paper PDF, labelled "Read the paper (PDF)": https://cdn.jsdelivr.net/gh/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract@fork/run_jSassd-YWLVC/paper.pdf
- The code repository, labelled "Code repository": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC
- The full research report — every experiment, every table and every dead end: https://cdn.jsdelivr.net/gh/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract@fork/run_jSassd-YWLVC/report.pdf
  Label this one "Read the full research report" and place it BESIDE the paper link, never in place of it.
- The executive summary, the short read of the run, labelled "Read the executive summary": https://cdn.jsdelivr.net/gh/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract@fork/run_jSassd-YWLVC/exec_summary.pdf
  Place it right beside "Read the full research report".
- The report of each research round, as ONE compact line introduced by "Round reports:" under the document links, each round labelled as given:
  - "Round 1": https://cdn.jsdelivr.net/gh/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract@fork/run_jSassd-YWLVC/round-1/report.pdf
  - "Round 2": https://cdn.jsdelivr.net/gh/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract@fork/run_jSassd-YWLVC/round-2/report.pdf
  - "Round 3": https://cdn.jsdelivr.net/gh/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract@fork/run_jSassd-YWLVC/round-3/report.pdf
  - "Round 4": https://cdn.jsdelivr.net/gh/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract@fork/run_jSassd-YWLVC/round-4/report.pdf
  - "Round 5": https://cdn.jsdelivr.net/gh/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract@fork/run_jSassd-YWLVC/round-5/report.pdf
  - "Round 6": https://cdn.jsdelivr.net/gh/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract@fork/run_jSassd-YWLVC/round-6/report.pdf
  - "Round 7": https://cdn.jsdelivr.net/gh/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract@fork/run_jSassd-YWLVC/round-7/report.pdf
  - "Round 8": https://cdn.jsdelivr.net/gh/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract@fork/run_jSassd-YWLVC/round-8/report.pdf
  - "Round 9": https://cdn.jsdelivr.net/gh/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract@fork/run_jSassd-YWLVC/round-9/report.pdf
  - "Round 10": https://cdn.jsdelivr.net/gh/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract@fork/run_jSassd-YWLVC/round-10/report.pdf

Each carries the branch this run publishes to. A link without it opens a DIFFERENT run's work —
it resolves and looks correct, which is why it must be copied rather than derived. They begin
resolving only after this run finishes publishing, so do NOT try to open or verify them.

`paper.tex` carries a third kind of link, per claim rather than per paper: where it attaches a
\footnote{Code: \url{...}} to a sentence, that URL points at the exact code behind THAT claim.
Carry each one onto the page as an inline link on the corresponding sentence, using the URL
verbatim, the same way you use the ones above. Do not collapse them into the repository link.

Every artifact this run produced is published with its code. Link EACH of these, verbatim, from the part of the page that discusses that artifact, labelled as given or as the page's own name for it; one the page does not otherwise discuss goes in a short code list above the footer:
- "Code: Source data for an algorithm-choice coding bench": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-1/dataset-1
- "Code: Where an algorithm ban sends an AI coder": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-1/experiment-1
- "Code: How prompt bans move an LLM's path-search choices": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-1/experiment-2
- "Code: Do a few early tokens decide the algorithm?": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-1/experiment-3
- "Code: Steering an LLM to vary its search algorithms": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-1/experiment-4
- "Code: Did post-training cause Qwen3's algorithm collapse?": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-1/experiment-5
- "Code: Do temperature and seeds change an LLM's algorithm?": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-1/experiment-6
- "Code: When does the AI coder pick its algorithm? An audit": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-2/evaluation-1
- "Code: Do algorithm bans pick a substitute or a ladder?": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-2/experiment-7
- "Code: Where a coding-algorithm ban takes effect in an LLM": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-2/experiment-8
- "Code: Banning five path algorithms in one prompt": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-2/experiment-9
- "Code: Do algorithm bans work the same in Llama?": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-2/experiment-10
- "Code: Coding-task bench with a baseline pilot": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-2/experiment-11
- "Code: Reading a coding ban inside Qwen3-8B": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-2/experiment-12
- "Code: Record repair and novelty audit of algorithm bans": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-3/evaluation-2
- "Code: Forecasting where coding bans send a model": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-3/experiment-13
- "Code: Show a solution, ban it, see what replaces it": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-3/experiment-14
- "Code: Where Llama goes when an algorithm is banned": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-3/experiment-15
- "Code: Where a coding ban takes effect in Qwen3-8B": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-3/experiment-16
- "Code: Searching Qwen3-8B for where a coding ban lives": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-3/experiment-17
- "Code: How far bans and token vetoes push Qwen3-8B": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-3/experiment-18
- "Code: Record repair and a frozen push screen": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-4/evaluation-3
- "Code: Is plan noise the cheapest route to diverse code?": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-4/experiment-19
- "Code: Where noise must enter to change the model's algorithm": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-4/experiment-20
- "Code: Same seed: temperature vs plan nudges": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-4/experiment-21
- "Code: Where the model picks its coding algorithm": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-4/experiment-22
- "Code: Predicting which coding bans a new AI model obeys": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-4/experiment-23
- "Code: Checking our claims against published work": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-4/research-1
- "Code: Record fixes and frozen rival predictors": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-5/evaluation-4
- "Code: Transplanting base-model plan states into Qwen3-8B": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-5/experiment-24
- "Code: Does the base model predict which coding tasks can be nudged?": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-5/experiment-25
- "Code: Base-model variety vs nudgeable coding tasks (panel B)": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-5/experiment-26
- "Code: Plan noise vs plan-first prompting for code": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-5/experiment-27
- "Code: Does Gemma's base model predict nudge effects?": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-5/experiment-28
- "Code: Has prior work restored base-model variety?": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-5/research-2
- "Code: Record repair and blind novelty re-check": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-6/evaluation-5
- "Code: Is FP8 rounding behind the random-push escapes?": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-6/experiment-29
- "Code: Where a coding model decides its algorithm": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-6/experiment-30
- "Code: Where Gemma picks BFS or DFS, and steering it": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-6/experiment-31
- "Code: Reading an LLM's planned algorithm in words": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-6/experiment-32
- "Code: Who already found the hidden plan?": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-6/research-3
- "Code: Fixing the run's record, number by number": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-7/evaluation-6
- "Code: Searching for the model's algorithm switch": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-7/experiment-33
- "Code: Where a coding AI picks its algorithm": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-7/experiment-34
- "Code: Where temperature changes the algorithm an LLM writes": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-7/experiment-35
- "Code: Why random nudges stopped changing the algorithm": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-7/experiment-36
- "Code: Evolutionary search for new coding algorithms": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-7/experiment-37
- "Code: Gemma BFS‑DFS Fork Analysis": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-7/experiment-38
- "Code: Fixing errors in the iteration-7 research record": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-8/evaluation-7
- "Code: Temperature at the algorithm-deciding token": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-8/experiment-39
- "Code: Searching for a hidden algorithm switch in code models": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-8/experiment-40
- "Code: Qwen3-8B Algorithm‑Choice Circuit Findings": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-8/experiment-41
- "Code: Fair test of Gemma's BFS steering dial": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-8/experiment-42
- "Code: Predicting how temperature shifts code ideas": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-8/experiment-43
- "Code: Which open models obey a five-algorithm ban": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-8/experiment-44
- "Code: Repairing the iteration-8 research record": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-9/evaluation-8
- "Code: Do AI coders dodge bans by renaming algorithms?": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-9/experiment-45
- "Code: Mapping grid algorithms with and without their names": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-9/experiment-46
- "Code: How tuning sharpens a code model's algorithm choice": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-9/experiment-50
- "Code: LLM search for new bin-packing rules": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-10/experiment-51
- "Code: Can guided LLM search invent bin-packing rules? (run 2)": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-10/experiment-52
- "Code: Token forcing vs temperature in LLM search for TSP heuristics": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-10/experiment-53
- "Code: Do banned bin-packing rules come back renamed?": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-10/experiment-54
- "Code: Do code-model maps track search order or storage?": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-10/experiment-55
- "Code: Which weights make the model pick one algorithm": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-10/experiment-56
- "Code: Correcting last round's report from raw data": https://github.com/ai-inventor-papers/ai-invention-295f8e-prompt-bans-substitute-not-just-subtract/tree/fork/run_jSassd-YWLVC/round-10/evaluation-9
</links>

FIRST, add ALL of these to your todo list using your task/todo-tracking tool:

CRITICAL: Todo content must be copied exactly as is written here, with NO CHANGES. These todos are intentionally detailed so that another LLM could read each one without any external context and understand exactly what it has to do.

<todos>
TODO 1. Read and STRICTLY follow these skills: aii-web-tools.
TODO 2. Read `paper.tex` end to end and list `figures/`. Write down the
paper's title, its author line, its contributions, and every headline number together with the
sentence it appears in — those sentences are the only numbers allowed on the page. Note which
figures are PDFs and so need a PNG rendered.
TODO 3. Render a PNG at about 200 DPI, into `figures/`, for every figure not already
in a browser-renderable format, then LOOK at each image you plan to use so you know what it shows
and how large it has to be on the page to stay legible.
TODO 4. Write `index.html` following the page_structure and technical_requirements sections
above: one file, inline CSS and JavaScript, every image referenced through the published figure
prefix.
TODO 5. VERIFY THE NUMBERS: for each number on the page, grep `paper.tex` for it and
confirm it appears there with the same meaning. Delete any number you cannot find. Then confirm
every claim on the page is one the paper actually makes.
TODO 6. VERIFY THE PAGE: confirm `index.html` has no external script, stylesheet or font
reference; that every image path starts with the published figure prefix and names a file that
exists in `figures/`; and that the PDF, repository and artifact code links are
character-for-character the URLs given in the links section — including the research report,
executive summary and round report links when they are listed there — and not `paper.pdf` nor any URL you composed. Then open the page in a browser, screenshot it at a phone width and a desktop width,
read both screenshots, and fix anything cramped, overlapping or cut off. Compare every figure on
the page with the one in `paper.pdf`: the same version, the same values. At the desktop width,
also screenshot the page scrolled to the top, the middle and the end, and confirm the nav marks
nothing, the section in view, and the last section respectively. `chromium-headless-shell`
is already installed: drive it with Playwright (`uv pip install playwright` in a scratch virtual
environment, then launch Chromium with `executable_path` set to the output of
`which chromium-headless-shell`, with no `playwright install`). Only if that command finds
nothing, run `playwright install --with-deps chromium` instead.
TODO 7. ACCESSIBILITY PASS: tab through the whole page and confirm every control is reachable with a
visible focus ring, the lightbox traps focus and closes on Escape, headings descend without
skipping, and every image has alt text. Fix what fails.
</todos>

---

Output the result as JSON to: `./.terminal_claude_agent_struct_out.json`

JSON Schema:
```json
{
  "$defs": {
    "PaperSiteExpectedFiles": {
      "description": "All expected output files from paper-site generation.",
      "properties": {
        "site_html_path": {
          "description": "Path to the single self-contained HTML page. Example: 'index.html'",
          "title": "Site Html Path",
          "type": "string"
        }
      },
      "required": [
        "site_html_path"
      ],
      "title": "PaperSiteExpectedFiles",
      "type": "object"
    }
  },
  "description": "Paper site \u2014 structured output from presentation-page generation.",
  "properties": {
    "summary": {
      "description": "Brief summary of the page you built: the sections it carries, which figures it shows, which numbers it quotes and where each came from in the paper.",
      "maxLength": 5000,
      "minLength": 300,
      "title": "Summary",
      "type": "string"
    },
    "out_expected_files": {
      "$ref": "#/$defs/PaperSiteExpectedFiles",
      "description": "All output files you created. Must include index.html."
    }
  },
  "required": [
    "summary",
    "out_expected_files"
  ],
  "title": "PaperSite",
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

### [2] SKILL-INPUT — aii-web-tools · 2026-10-26 18:20:25 UTC

The agent loaded the **aii-web-tools** skill; its `SKILL.md` (the instructions injected into the agent's context) follows verbatim.

````
---
name: aii-web-tools
description: "Runs web search, page fetch as markdown, and regex grep over full HTML or PDF text via this skill's own scripts (aii_fast_web_search.py, aii_fast_web_fetch.py) — a free-first keyless search stack with Serper fallback that works even where built-in WebSearch and WebFetch are absent. Use when a query, page, or paper must be searched, read, or mined for an exact quote, number, table value, or methodology sentence, and whenever a lossy summary would lose the detail. Triggers: web search, scholarly search, OpenAlex, Crossref, Serper, fetch a URL as markdown, read a PDF, arXiv, regex grep a page, exact quote, table value, citation check. NOT for: planning a broad multi-source literature review or mass verification campaign — use aii-web-research-tools; NOT for a PDF file already on disk — extraction, form filling, merging and PDF creation are anthropic-pdf; NOT for driving a browser or testing a UI."
---

## Web tools

You have three web capabilities: **search**, **fetch**, and **grep** (exact
regex extraction over a full page or PDF).

**Pick where they come from, in this order:**

1. **If you have built-in `WebSearch` / `WebFetch` tools, PREFER those over the
   scripts below.** They may be **deferred tools** (listed by name but with
   schemas not yet loaded) — if so, call `ToolSearch("select:WebSearch,WebFetch")`
   ONCE to load them, then use them normally. Do not skip them just because they
   need that one extra load step; they are the preferred path. Pair them with the
   `aii_web_tools__fetch_grep` script below when you need exact text / numbers /
   methodology that a summary would miss, or when reading a PDF.
2. **Only if you have NO built-in `WebSearch` / `WebFetch`** (e.g. the OpenHands
   backend), use the scripts in this skill (below). They are our own
   implementations — free-first web search (keyless general/scholarly engines,
   Serper fallback), html2text + PyMuPDF for fetch, and regex grep over the full
   document text. They work without any built-in web tools.

Workflow either way: **search** (discover) → **fetch** (read for the gist) →
**grep** (pull exact details / read PDFs).

---

## Running the scripts

Run every script with the skill's pre-provisioned interpreter (it already has
`requests`, `html2text`, `pymupdf`, `python-dotenv`). Set `PY` once:

```bash
export SKILL_DIR="$(git rev-parse --show-toplevel 2>/dev/null || echo /ai-inventor)/.claude/skills/aii-web-tools"
export PY="$SKILL_DIR/../.ability_client_venv/bin/python"
```

### 1. Search the web (free-first: general or scholarly)

```bash
# general web (default): keyless engines (ddgs, marginalia); Serper only if they miss
$PY "$SKILL_DIR/scripts/aii_fast_web_search.py" --query "neuro-symbolic FOL translation LLM" --max-results 10
# scholarly mode: OpenAlex + Crossref (DOIs, citation counts)
$PY "$SKILL_DIR/scripts/aii_fast_web_search.py" --query "neuro-symbolic FOL translation" --mode scholarly
```

Returns ranked title / URL / snippet lines. `--mode general` (default) uses
keyless general engines; `--mode scholarly` uses academic APIs. Both fall back
to Serper (paid) only when the free engines miss. Use search first to scan the
landscape; snippets are for discovery only — fetch a page before judging it.

### 2. Fetch a page as markdown (HTML or PDF)

```bash
$PY "$SKILL_DIR/scripts/aii_fast_web_fetch.py" fetch --url "https://arxiv.org/abs/2303.11366" --max-chars 10000
```

`--max-chars` caps output (default 10000); `--char-offset N` pages further in.
Handles PDFs transparently via PyMuPDF.

### 3. Grep a page or PDF (exact regex extraction)

```bash
$PY "$SKILL_DIR/scripts/aii_fast_web_fetch.py" grep --url "https://arxiv.org/pdf/2303.11366" --pattern "verbal reinforcement" --max-matches 20 --context-chars 200
```

Returns only the matching sections with surrounding context — the right tool
for exact numbers, table values, methodology, or long PDFs where a summary
would lose the detail. `-i` for case-insensitive.

**Parallelize** independent searches/fetches in one turn; only sequence a
fetch after the search that produced its URL.

---

## Notes

- The scripts call our ability server. If a script prints
  `Ability service not available`, the server is down — say so rather than
  silently improvising a different search method.
- Do **not** hand-roll your own `requests`/scraping for search when these
  tools are available: Serper returns clean Google results and the fetch/grep
  scripts already handle HTML, PDFs, and encoding.
````

### [3] SYSTEM-USER prompt · 2026-10-26 18:20:45 UTC

```
[Image: original 3819x1043, displayed at 2000x546. Multiply coordinates by 1.91 to map to original image.]
```

### [4] SYSTEM-USER prompt · 2026-10-26 18:20:54 UTC

```
[Image: original 2040x1148, displayed at 2000x1125. Multiply coordinates by 1.02 to map to original image.]
```

### [5] SYSTEM-USER prompt · 2026-10-26 18:20:54 UTC

```
[Image: original 2080x1170, displayed at 2000x1125. Multiply coordinates by 1.04 to map to original image.]
```

### [6] SYSTEM-USER prompt · 2026-10-26 18:51:47 UTC

```
<CRITICAL_ERROR>
The module-end file check FAILED (attempt 1/3).

PROBLEMS:
  - .aii/manifest.yaml: 'figures/' matches nothing that needs a decision — remove it (text, code and files under the auto-keep floor are always kept)
  - .aii/manifest.yaml: 'workspace/' matches nothing that needs a decision — remove it (text, code and files under the auto-keep floor are always kept)

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
