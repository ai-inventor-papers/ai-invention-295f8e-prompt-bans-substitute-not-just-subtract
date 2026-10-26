"""Write the review of the iteration-4 research record to .terminal_claude_agent_struct_out.json.

Every number cited below is recomputed in verify_iter4.py (output in verify_iter4.log) or read from the
artifact result file named next to it. Run: python3 build_review.py
"""
import json

OUT = ".terminal_claude_agent_struct_out.json"

overall = (
    "The record has absorbed the previous review. Every must-fix and minor item is answered with new analysis, and "
    "Table 121 maps each to its section: "
    "a 1,120-cell knob table with per-task verdicts and random-direction counts; "
    "landings per route arm; the Llama hit rule; "
    "a two-judge audit of every 'other' landing with catalogue-only avoidance; "
    "activation-space Isomaps with the position caveat; "
    "a seed-coupled thinking-on arm; "
    "and positioning Tables 92b and 92c. "
    "The chronology holds: I diffed Sections 1 to 3 against the iteration-3 draft, and all 18 changed hunks carry an "
    "'iteration 4' marker. "
    "I recomputed the iteration-4 headlines from raw files (verify_iter4.py, verify_iter4.log), and every one I checked "
    "matches. "
    "Plan noise (exp19): the alpha sweep (Table 141), flips (Table 140), per-template shares (Table 142c) and the price "
    "decision (PARTIAL; count1 2, count2 4; mean margin -0.22 [-0.89, 0.30]; per-task 5-point Hill-1 2.72, 1.29, 1.00, "
    "2.09, 1.42, 1.35). "
    "Site (exp20): 0 of 526 and 0 of 527 correct programs off the default at the read position and the condition "
    "sentence, 6 of 521 at the late blocks; the boundary; the top-five push (BFS only); plan-site indicator +2.15 "
    "[1.79, 2.51]. "
    "Same seed (exp21): temperature changes the algorithm in 0 of 20 seeds on all three tasks; plan-noise counts 17.25, "
    "4.55 and 2.5; pooled contrast 0.545. "
    "Plan subspace (exp22): escape counts (kth smallest 12/40 and 25/40, and so on); pooled rho 0.033 [-0.03, 0.09]. "
    "Held-out family (exp23): table [[3,3],[1,8]], BA 0.739, Fisher 0.235, rho 0.537. "
    "results_reported is true. "
    "Soundness is 1, because four conclusions of the new section contradict the record's own evidence. "
    "(1) 'Every sensitivity stays inconclusive' (Section 4.7). The preregistered sensitivity that measures compliance "
    "as the drop in default share returns DISCONFIRMED in c3a.json, and Table 160 labels that row 'disconfirmed'. "
    "(2) The read position and the condition sentence 'changed no algorithm at any dose' (4.10 item 3; closing). "
    "Section 4.4 reports that the energy-matched read-position arm moved two tasks. "
    "(3) The choice of algorithm is 'located' in the task-specification states (closing). The site rule returned "
    "PARTIAL, 4.10 lists the site claim as inconclusive, and generated-token noise flips find duplicate 12:0 over the "
    "plan site. "
    "(4) The route-landing lead carried into 4.11 and the closing. Find duplicate in Table 127 contradicts it. "
    "Two confounds of the held-out test are undisclosed. Gemma's grid 'default' was frozen from a 10-sample pilot, and "
    "its twin is BFS 25, DFS 25. Its shortest path 'obey' and its top price row rest on array Dijkstra labelled "
    "Bellman-Ford. "
    "Executed results missing from the record: plan noise on the plain prompt; a hull-search deviation and its check "
    "(harmless on the real data); the Llama knob verdict. "
    "What the record does support: "
    "with coupled seeds, temperature does not change the algorithm in Qwen3-8B, thinking off or on, and it buys no "
    "correct diversity in gemma-3-4b-it either; "
    "a random displacement of the task-specification prefill states changes it on 4 to 5 of 15 tasks, cheaply on kth "
    "smallest and connected components; "
    "per unit of downstream displacement, the read position, condition sentence and late blocks are far less "
    "effective; "
    "the forced-prompt subspace does not explain which directions work; "
    "no knob produced a correct novel algorithm. "
    "The fixes are restatements of conclusions, plus reporting arms that are already on disk."
)

strengths = [
    "Every item of the blocking iteration-3 review is answered with new analysis rather than wording: one knob table "
    "of 1,120 cells under a declared class rule with per-task verdicts and random-direction counts (Tables 123 to 126), "
    "landings per route arm (Table 127), the Llama hit rule under five labelling rules (Table 129), a two-judge audit "
    "of all 226 'other' programs plus catalogue-only avoidance (Tables 131 to 132b), defined-only hit rates (Table 134) "
    "and Table 82 per distinct row (Table 135). Table 121 maps each item to its answer.",
    "The chronology is intact. Diffing Sections 1 to 3 against the iteration-3 draft gives 18 changed hunks, all "
    "marked 'Correction, iteration 4' or 'Added in iteration 4'; old wording is kept inside the marks.",
    "Every iteration-4 headline I recomputed from raw rows matches the report exactly: Tables 137, 140, 141, 142c, "
    "the inert-site counts (0/526, 0/527, 6/521), the boundary and top-five rows, the seed counts of Table 150 and the "
    "0.545 contrast, the escape counts of Table 154, the pooled subspace rho 0.033, and the Gemma confusion table, BA, "
    "Fisher p and Spearman rho.",
    "The new experiments are well controlled. Decision rules were hash-committed before the decisive samples. Common "
    "random numbers turn site and temperature contrasts into exact paired flips (Tables 140, 146, 150). Downstream "
    "displacement is matched (indicator +2.15 [1.79, 2.51]; Mantel-Haenszel odds ratio 5.72). Every Qwen engine "
    "reproduced the iteration-3 screen byte for byte. Independent rederivations and placebos ran in every artifact.",
    "Negative and partial verdicts are kept as such, with their evidence: the price claim is PARTIAL; the plan "
    "subspace is disconfirmed, with a decomposition showing the subspace is not needed (Table 155); the targeted push "
    "fails on 5 of 6 tasks; verbalized sampling is closed as a run-time dispatcher artifact; the frozen counting rule "
    "is abandoned because it fires on noise.",
    "The request's temperature question (1a to 1c) now has an executed answer in both thinking modes, with an "
    "uncoupled check in gemma-3-4b-it. Under seed coupling the algorithm never changes while phrasings grow, and the "
    "thinking-on result is read against a measured repeat noise floor.",
    "Novelty is audited in every artifact with two blind judges plus a manual read (0 novel among 14,206 correct "
    "programs of the site and subspace experiments alone). The positioning audit checked 112 verbatim quotes and "
    "records which lanes are partly occupied and which baselines are missing (text-level plan samplers, "
    "departure-matched decoding).",
    "The bookkeeping is preserved: hardware departures (FP8 W8A8 on a 16 GB card; gemma-3-4b-it instead of "
    "gemma-2-9b-it), spend per artifact, unit changes made before commitment, and the dropped Llama screen body.",
]

dimension_scores = [
    {
        "dimension": "soundness",
        "score": 1,
        "justification": (
            "The experiments are sound and every headline number I recomputed matches. Four summary conclusions of the "
            "new section contradict the record's own tables. "
            "(a) Section 4.7 says 'Every sensitivity stays inconclusive (Table 160)'. The preregistered sensitivity "
            "'compliance as the drop in default share' returns DISCONFIRMED (BA 0.568, Fisher p 1.0; "
            "art_k6nzFCDLOjQP results/c3a.json), and Table 160 itself labels the row 'disconfirmed'. "
            "(b) 4.10 item 3 and the closing say that the read position and the condition sentence change no algorithm "
            "'at any dose'. The energy-matched read-position arm reported in Section 4.4 moved find duplicate (+0.23) "
            "and connected components (+0.18). "
            "(c) The closing calls the choice of algorithm 'located' in the task-specification states. The site rule "
            "returned PARTIAL, 4.10 lists the site claim under 'Inconclusive', and generated-token noise flips find "
            "duplicate 12:0 over the plan site (Table 146). "
            "(d) The route-landing lead of 4.2.2, 4.11 and the closing is contradicted by find duplicate in Table 127. "
            "Under the rule, a conclusion that contradicts the run's own evidence scores 1."
        ),
        "improvements": [
            "Section 4.7, 4.10 and the closing: report the held-out verdict per compliance measure, INCONCLUSIVE "
            "(primary) and DISCONFIRMED (drop in default share). Name the tasks that separate the two measures. "
            "Expected impact: removes contradiction (a).",
            "4.10 item 3 and the closing: replace 'at any dose' with 'at per-position doses up to 4 ban units', and add "
            "the energy-matched result. Replace 'located' with 'the prefill site where noise is effective; noise in the "
            "first 32 generated tokens also redirects the choice'. Expected impact: removes contradictions (b) and (c).",
            "4.2.2, 4.11 and the closing: restate the route-landing lead as a connected-components observation, with "
            "find duplicate as its counter-example. Expected impact: removes contradiction (d). With (a) to (c), this "
            "returns soundness to 2 or 3.",
        ],
    },
    {
        "dimension": "presentation",
        "score": 3,
        "justification": (
            "A reader who was not on the run can follow iteration 4: "
            "why each claim was tested (Section 4.1), the review items and where each is answered (Table 121), "
            "and per experiment its design, results, committed predictions and checks. "
            "The weaknesses are conventions the text does not state: "
            "4.10 lists the site claim as both established (item 3) and inconclusive; "
            "Table 147 reports Hill numbers rarefied to depths 20, 9, 5, 7, 6 and 1 at alpha 4 without saying so; "
            "Table 157 and the closing compare means over 3 events and over 5 events; "
            "Table 159 shows each Gemma default without the twin composition that defines it."
        ),
        "improvements": [
            "Give the rarefaction depth of every Hill number in Table 147, and drop the claim that diversity 'peaks at "
            "alpha 4' on tasks where that rests on 5 to 9 correct programs.",
            "Report Table 157 on matched event sets (push -0.76 vs association -3.11 on the same 3 events; -1.37 vs "
            "-3.46 over 5 with undefined forecasts as uniform).",
            "Add the twin composition and the pilot that froze the default to Table 159.",
        ],
    },
    {
        "dimension": "contribution",
        "score": 3,
        "justification": (
            "The report preserves nearly all of a very large run. Every iteration-4 artifact appears with its full "
            "tables, dead ends and bookkeeping, and the earlier gaps are filled. "
            "Executed outputs still missing: "
            "the plan-noise arm on the plain prompt (exp19 PNPLAIN_a1); "
            "the hull edge-restriction deviation and its triangle check (exp19 D-hull-edges; at most +0.008 on the real "
            "data); "
            "a Llama verdict from the 175 Llama knob cells; "
            "the Gemma grid pilot and twin compositions; "
            "the 10 to 16% weaker dose unit of the exp22 bench pushes; "
            "the 2.74 GPU hours of exp21. "
            "Several neighbour rows of the positioning artifact were dropped, among them the nearest method to plan "
            "noise (NC-GRPO) and a contradicting row for the novelty claim."
        ),
        "improvements": [
            "Add the PNPLAIN_a1 rows (plan noise without the twin frame) to Section 4.3.",
            "Add the hull deviation and the triangle_minus_edge check to Section 4.3.",
            "Add a per-task Llama knob verdict to Section 4.2.1.",
            "Restore the dropped positioning rows in Table 92c.",
        ],
    },
]

critiques = [
    {
        "category": "evidence",
        "severity": "major",
        "description": (
            "The held-out test of the movability claim (Section 4.7, 4.10, closing) is reported as inconclusive under "
            "every sensitivity, but one preregistered sensitivity disconfirms it.\n"
            "- Verdict. Section 4.7 says 'Every sensitivity stays inconclusive (Table 160)'. In art_k6nzFCDLOjQP "
            "results/c3a.json, 'compliance_as_default_share_drop' returns DISCONFIRMED (BA 0.568, Fisher p 1.0, "
            "rho 0.39). The experiment plan lists this sensitivity, and Table 160 itself labels the row "
            "'disconfirmed'. The artifact README makes the same contradiction, and the report copied it.\n"
            "- True positives. Two of the three true positives behind rho 0.54 are compromised, and the record "
            "discloses only one.\n"
            "  - Grid task: the 'default' DFS was frozen from a 10-sample pilot (correct programs BFS 4, DFS 5; "
            "attempts 5 and 5; predictions/commit1.json). The 50-sample twin is BFS 25, DFS 25. 'Obeys' (avoidance "
            "0.83) is therefore measured against a non-default baseline of 0.50. The grid escape (1 of 8 directions) "
            "measures BFS rising from 50%. Table 159 shows 'grid (DFS)' without the twin.\n"
            "  - Shortest path task: the 'obey' rests on array-based Dijkstra labelled Bellman-Ford (disclosed). "
            "Without both tasks, BA is 0.61 and rho 0.31 (p 0.146).\n"
            "- Same labelling failure elsewhere. It produces the top Gemma row of Table 163: plan noise 1.62 from 5 "
            "and 12 'bf_spfa' correct programs at alpha 1 and 2; the novelty instruction 1.96 from 29. The "
            "push-landing 4 of 4 (Table 162) includes both compromised tasks, and every family hits on both."
        ),
        "suggested_action": (
            "1. In 4.7, 4.10 and the closing, state the verdict per compliance measure: INCONCLUSIVE (primary, "
            "catalogue-only avoidance) and DISCONFIRMED (drop in default share).\n"
            "2. Say which tasks separate the two measures:\n"
            "   - the grid task's tied baseline (drop 0.33);\n"
            "   - find duplicate, where 38 failing 'other' programs count as leaving the default under the drop "
            "measure (catalogue-only avoidance 0.34; drop 0.72).\n"
            "3. Add twin composition and pilot counts to Table 159, and mark the grid task as having no default.\n"
            "4. Put the labeller caveat on Table 163's shortest path row and on the 4 of 4 of Table 162.\n"
            "5. Rewrite the closing sentence: 'inconclusive under the primary rule, disconfirmed under the "
            "default-drop sensitivity; the positive rank correlation rests on a tied-baseline task and a "
            "mislabelled task'.\n"
            "Expected impact: removes one contradiction behind soundness 1 (+0.5 with the next two)."
        ),
    },
    {
        "category": "evidence",
        "severity": "major",
        "description": (
            "The site conclusions (4.10 item 3; closing paragraphs 1 and 3) say more than the site experiment "
            "[ARTIFACT:art_Cx9JOh8soBw7] supports.\n"
            "- 'At any dose'. The record says the read position and the condition sentence 'changed no algorithm at "
            "any dose (0 of 526 and 0 of 527 ...)'. Those counts cover only the per-position doses alpha 1 to 4. The "
            "energy-matched read-position arm S1E, reported in Section 4.4, moved two tasks:\n"
            "  - find duplicate: Floyd cycle detection 6 of 26 correct;\n"
            "  - connected components: 5 of 28 correct programs off the default.\n"
            "- 'Located'. The closing says 'Where the choice is made inside the model is located ... The "
            "task-specification states carry it'. Noise in generated tokens 1 to 32 (S3) is not inert:\n"
            "  - it moves four tasks;\n"
            "  - it has the best 5-point Hill-1 on two sum and find duplicate (Table 143);\n"
            "  - its price of 1.5 on two sum is 0.12 against 0.53 (Table 144);\n"
            "  - it flips find duplicate 12:0 over the plan site at alpha 2 (exact McNemar p 0.0005; Table 146).\n"
            "- The record disagrees with itself. The frozen rule returned PARTIAL, and Section 4.10 lists the site "
            "claim under 'Inconclusive' while item 3 states 'The site is the task-specification states' under "
            "'Established'.\n"
            "What the experiment establishes is narrower:\n"
            "- among prefill positions, the task-specification states (blocks 0 to 23; blocks 0 to 11 vs 12 to 23 "
            "not separated, -0.31 [-0.75, 0.13] in results/transmission.json) are the effective site per unit "
            "downstream displacement;\n"
            "- the choice is still open during the first 32 generated tokens."
        ),
        "suggested_action": (
            "1. Rewrite 4.10 item 3: 'Among prefill positions, perturbing the task-specification states changes the "
            "algorithm; the read position and the condition sentence are inert at per-position doses up to 4 ban "
            "units, and far weaker at matched energy (S1E: +0.23 on find duplicate, +0.18 on connected components); "
            "noise in generated tokens 1 to 32 also redirects the choice, more than the plan site on find duplicate.'\n"
            "2. In the closing, replace 'a located site for the choice of algorithm' with 'a prefill site at which "
            "noise is effective, not a locus of the decision'.\n"
            "3. Reconcile item 3 with the 'Inconclusive' entry for the site claim.\n"
            "Expected impact: removes two contradictions behind soundness 1."
        ),
    },
    {
        "category": "rigor",
        "severity": "major",
        "description": (
            "Several landing conclusions generalise from one task or compare unmatched event sets.\n"
            "(a) Route-landing lead. Sections 4.2.2 and 4.11 and the closing carry it forward: 'where a single route "
            "suffices to remove the default, it lands on the generic neighbour that pushes and the stated alternative "
            "agree on'. It comes from connected components. Table 127 contradicts it on find duplicate: the direct "
            "route alone removes the default (F_direct 0.99) and lands on index marking (74 of 78). That is neither "
            "the push landing (sort and adjacent check) nor the association answer (Floyd cycle detection). On two "
            "sum, pushes and association disagree, so there is no agreed neighbour.\n"
            "(b) Item 6 of 4.10, 'that runner-up forecasts where a ban lands', is listed as established. It rests on:\n"
            "  - 3 Qwen events, all seen before, with 2 top-1 hits (it misses connected components);\n"
            "  - Gemma's 4 of 4, where only 2 events disagree and the other 2 are the tied grid task and the "
            "mislabelled shortest path task.\n"
            "(c) Unmatched event sets. The closing and Table 157 compare the push forecast's mean over its 3 defined "
            "events (-0.76) with association's mean over 5 (-3.46). On the same 3 events association scores -3.11. "
            "With undefined forecasts scored as uniform, the push forecast scores -1.37 over all 5 "
            "(art_SHaWv77P1XCI results/c3b.json). This is the log-score form of the hit-rate defect the previous "
            "review raised.\n"
            "(d) 'The landing is a property of the task, not of the direction' (4.6) holds across directions at one "
            "site, not across sites. On find duplicate, generated-token noise and the energy-matched read position "
            "land on Floyd cycle detection (5 and 6 correct programs). The plan-site screen escape landed on sort and "
            "adjacent check."
        ),
        "suggested_action": (
            "1. Restate the route-landing lead as a single-task observation (connected components), with find "
            "duplicate as its counter-example.\n"
            "2. Move item 6 from 'Established' to the descriptive results, with its counts: 2 of 3 seen Qwen events, "
            "2 disagreeing Gemma events.\n"
            "3. Report every forecast comparison on matched events, with the rule for undefined forecasts stated.\n"
            "4. Qualify the 'property of the task' sentence with the site dependence on find duplicate.\n"
            "Expected impact: +0.25."
        ),
    },
    {
        "category": "evidence",
        "severity": "major",
        "description": (
            "Executed results bearing on the iteration's primary claim are missing from the record.\n"
            "(1) Plan noise without the twin frame. art_mWn-MQEnNelg ran plan noise on the plain prompt (PNPLAIN_a1, "
            "350 programs): off-default share 0.16 on kth smallest (0.28 on the twin), 0.24 on connected components "
            "(0.12), 0.26 on the shortest path task (0.26), 0 on two sum and find duplicate. It is the only test that "
            "the knob works without the twin's 'Do not use <noun>' frame; that frame costs 18 pass points on the grid "
            "task. Section 4.3 reports the plain prompt without noise only.\n"
            "(2) Hull deviation. Deviation D-hull-edges: the pre-registered hull search is restricted to edges. On "
            "random 5-vertex test cases it fell short of the full-simplex optimum by up to 0.19 Hill. Plan noise has "
            "5 hull vertices against 2 or 3 for most comparison knobs, so any shortfall falls on it. On the real data "
            "the triangle_minus_edge check in results/prices.json shows at most +0.008 (connected components), so the "
            "verdict is unaffected. Neither the deviation nor the check is in the record.\n"
            "(3) Llama knob verdict. The record audit priced 175 Llama cells but reports no Llama verdict. In "
            "tables/knob_table.csv, 0 of 36 Llama random-direction cells qualify, though they were three times the "
            "ban's displacement at layer 21. The 5 qualifying Llama knob cells are prompt bans and one veto "
            "(Fibonacci modal ban 2.43; substring one-shot veto 2.54). This cross-family check bears directly on "
            "'random pushes buy correct diversity'.\n"
            "(4) Dose units. The exp22 bench pushes used a unit 9 to 16% smaller than the screen's (its deviation "
            "'ban_unit_scale'). Table 164 compares movability across experiments as if alpha meant the same push.\n"
            "(5) Bookkeeping. Table 122 omits exp21's 2.74 GPU hours (results/gpu_hours.json)."
        ),
        "suggested_action": (
            "1. Add the PNPLAIN_a1 rows to Section 4.3 with one sentence on what they show.\n"
            "2. Add the hull deviation and its triangle check to the sensitivity list of Table 139.\n"
            "3. Add a Llama row block to Table 123 or 126 and one sentence in 4.2.1.\n"
            "4. Note the unit per experiment beside Table 164.\n"
            "5. Add exp21's GPU hours to Table 122.\n"
            "Expected impact: +0.25 on contribution."
        ),
    },
    {
        "category": "rigor",
        "severity": "major",
        "description": (
            "The summary picks the best cell where the evidence is a distribution, and the lead chosen for the next "
            "iteration rests mostly on one task.\n"
            "(a) Two sum. The closing says fixed random directions 'reach above 2 at no cost on kth smallest and two "
            "sum'. On two sum this is the best of 9 directions, and 1 qualifies. Fresh per-sample plan noise reaches "
            "1.29 there; 0 of 40 fresh directions escape at alpha 1 and 5 of 40 at alpha 2.\n"
            "(b) Reliability. Item 5 of 4.10 ('Template halves rank 40 directions alike (0.76 to 0.90)') omits the "
            "grid task, 0.39 with 22 movers, and find duplicate, 0.59 (exp22 results/explore.json).\n"
            "(c) Signed progress, which the closing names as 'the next preregistered predictor':\n"
            "  - 117 of 144 cells are positive, but 22 of the 35 cells with p < 0.05 (uncorrected) are on connected "
            "components;\n"
            "  - on kth smallest, the most movable task, the mean over the edited blocks 12 to 23 is -0.02 (-0.29 at "
            "block 15); on find duplicate it is -0.12;\n"
            "  - on connected components the committed signed component was matched by the within-class control "
            "(0.37 against 0.33).\n"
            "(d) Underpowered panel. The movable panel is 5 tasks on fresh draws. A new predictor on the same 5 tasks "
            "adds a metric, not samples.\n"
            "(e) Depths. Table 147's 'peaks at alpha 4 on three tasks' rests on 5, 7 and 9 correct programs, rarefied "
            "at those depths, not at 25."
        ),
        "suggested_action": (
            "1. Quote the per-direction distribution (7 of 21 on kth smallest, 1 of 9 on two sum) with any best-cell "
            "number, and say which numbers are maxima over directions.\n"
            "2. Report the reliability on all six tasks.\n"
            "3. Restate the signed-progress lead with its per-task breakdown and the control match on connected "
            "components.\n"
            "4. In Section 4.11, put the next budget on more movable tasks (more of the bench, or new tasks screened "
            "ban-free), so that 'a property of the task' can be tested; do not add a further predictor on the same "
            "five.\n"
            "Expected impact: +0.25 and better steering."
        ),
    },
    {
        "category": "novelty",
        "severity": "minor",
        "description": (
            "Table 92c drops neighbour rows that the positioning artifact (art_kjrCpQnPaniY research_report.md) found "
            "and verified.\n"
            "(a) Plan noise. The nearest method is Jerge et al. 2026 (arXiv 2608.21595, NC-GRPO): scale-calibrated "
            "Gaussian noise in the last hidden layer of the prompt-encoding pass, to diversify rollouts. Nagarajan et "
            "al. [80] (input-layer seed-conditioning works as well as output temperature on algorithmic-creativity "
            "tasks) is positioned only against the site claim, but it is the nearest prior answer to 'plan noise vs "
            "temperature'.\n"
            "(b) Novelty boundary. The artifact lists:\n"
            "  - a 'contradicting in part' row (Bhushan et al. 2026, arXiv 2608.30047: agents reach LLM-judged "
            "human-novel solutions);\n"
            "  - a supporting row (Maveli et al. 2026, arXiv 2610.02438: named-algorithm generation as parametric "
            "retrieval);\n"
            "  - the ICLR 2027 submission oag3wgNLRh: steering redirects among trajectories the model already "
            "supports, and departure-matched decoding matches it.\n"
            "  Only FunSearch and AlphaEvolve remain in the record.\n"
            "(c) Plan subspace. The submission 'Before the First Token' (knirOusGcq) uses the same parallel and "
            "orthogonal decomposition for a causal pre-generation subspace. The artifact says 'cite and contrast'."
        ),
        "suggested_action": (
            "Add these rows to Table 92c. Name the submissions by OpenReview id if they are not to be numbered. For "
            "each, write what this run adds: test-checked mechanism labels; site comparison at matched dose; seed "
            "coupling; no-novelty bound."
        ),
    },
    {
        "category": "rigor",
        "severity": "minor",
        "description": (
            "The rebuilt knob table counts exposure arms as knobs. An exposure prompt supplies a correct program of "
            "the alternative, which is the reason the A* mention is a control (Section 3.2.5). Table 123's verdicts "
            "rest on exposure arms on several tasks:\n"
            "- connected components (unnamed exposure ban of BFS, 1.85);\n"
            "- longest increasing subsequence (named exposure ban of the Fenwick tree, 1.78);\n"
            "- first and last position (exposure vetoes, 1.78 to 1.84);\n"
            "- nonoverlapping intervals (1.26).\n"
            "Each of these is priced against its own copy twin, in which the shown algorithm is the default."
        ),
        "suggested_action": (
            "1. Declare a class for exposure arms in the class rule.\n"
            "2. Give the per-task verdict with exposure arms as controls beside the current one."
        ),
    },
    {
        "category": "scope",
        "severity": "minor",
        "description": (
            "Request item 1a to 1c asks what a tight temperature with top-k 10 and the same seed does to reasoning "
            "trajectories. The iteration-4 seed-coupled temperature block ran without top-k (top-p 1; top-k 10 only "
            "as one cell at T 0.7, thinking off). The thinking-on arm used Gumbel coupling without top-k. The only "
            "seed-coupled top-k 10 sweep is iteration 2's readout experiment (Table 76, thinking off)."
        ),
        "suggested_action": (
            "In Section 4.5, cross-reference Table 76 as the top-k 10 answer, and state that the literal cell (thinking "
            "on, top-k 10, same seed) was not run. Running it is cheap if wanted: 20 seeds x 4 temperatures on the "
            "shortest path task."
        ),
    },
]

review = {
    "overall_assessment": overall,
    "strengths": strengths,
    "dimension_scores": dimension_scores,
    "critiques": critiques,
    "results_reported": True,
    "coverage": "full",
    "blocking": True,
    "score": 4,
    "confidence": 4,
}

# Blocking is derived: soundness <= 1 or results not reported.
sound = next(d["score"] for d in dimension_scores if d["dimension"] == "soundness")
assert review["blocking"] == (sound <= 1 or not review["results_reported"])

with open(OUT, "w") as f:
    json.dump(review, f, indent=2, ensure_ascii=False)
print("wrote", OUT, "critiques", len(critiques), "major", sum(c["severity"] == "major" for c in critiques))
