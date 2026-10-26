"""Apply the iteration-5 record corrections (art_mgek9PfVBNbh corrections.json) in place.

Each edit keeps the earlier wording and adds a marked correction, or replaces a phrase and
marks the replacement. Every anchor must occur exactly once.
"""
from pathlib import Path

P = Path(__file__).resolve().parent.parent / "paper_draft.md"
s = P.read_text()

def once(anchor):
    n = s.count(anchor)
    assert n == 1, (n, anchor[:90])

def insert_after(anchor, add):
    global s
    once(anchor)
    s = s.replace(anchor, anchor + add, 1)

def replace(anchor, new):
    global s
    once(anchor)
    s = s.replace(anchor, new, 1)

# (0g) Section 3.2.5: exposure class
insert_after(
    "Generate then select is a ceiling, and baselines are references.",
    " *(Correction, iteration 5: the class rule omitted a class. Exposure arms, any arm whose prompt shows a correct program of an algorithm (the copy twin, the named and unnamed exposure bans and the exposure vetoes), supply the text of the alternative and are therefore controls, like the mention twin; their Hill-1 is reported beside the knob verdict and never as the best knob. The per-task verdict with exposure arms as controls is in Table 172, Section 5.2.)*")

# (0d) Table 122: exp21 GPU hours
replace(
    "3,140 programs, thinking-on traces included | under USD 0.10 |",
    "3,140 programs, thinking-on traces included; 2.74 GPU hours (HF 3,297 s, vLLM 6,580 s; added in iteration 5) | under USD 0.10 |")

# (0e, 0g, 0d) Section 4.2.1 'Read per task' paragraph
insert_after(
    "the other mismatch was the two sum avoidance at alpha 2, 0.469 on the attempted denominator (one row had no program) against the quoted 0.48.",
    " *(Correction, iteration 5: three qualifications. First, the random-direction numbers above are maxima over directions, not the effect of a typical direction: on kth smallest 2.92 is the best of 21 direction and dose cells, of which 7 qualify, and on two sum 2.12 is the best of 9 directions, of which 1 qualifies; fresh per-sample plan noise reaches 1.29 on two sum, and 0 of 40 fresh directions escape there at alpha 1 and 5 of 40 at alpha 2 (Sections 4.3 and 4.6; per-direction distributions in Table 175). Second, under the exposure class now declared in Section 3.2.5, exposure arms are controls. With them set aside, in the knob rows of the plan noise experiment a non-exposure knob reaches 1.5 within 20 pass points on the grid, shortest path, kth smallest, substring search, two sum, find duplicate and connected components tasks; longest increasing subsequence and first and last position join the tasks where nothing does, and the modal ban of top-k frequent (1.78 at 17 points) is carried from the record because ban arms are not among those rows (Table 172). Third, the record omitted the Llama block of the same table (Table 126c, below Table 126b).)*")

# (0d) Llama block after Table 126b: find the paragraph that follows Table 126b's last row
anchor_126b_tail = "The two mismatches are explained in the text above: the two sum share uses the attempted denominator (1 - 26/49), and the six-task sentence ignored the top-k frequent modal ban and two exposure arms."
insert_after(anchor_126b_tail,
    "\n\n*(Added in iteration 5: the Llama-3.1-8B-Instruct block of the knob table, which this section did not report. Source: iteration-5 record audit `tables/llama_block.csv`, carried from the iteration-4 record audit's knob table.)*\n\n"
    "**Table 126c.** Llama-3.1-8B-Instruct cells of the knob table (175 cells): random directions against the knob cells that qualify (Hill-1 of at least 2 within 20 pass points).\n\n"
    "| Row | Value | Note |\n|-|-|-|\n"
    "| random-direction cells | 0 of 36 qualify | pushed at about 3 times the ban displacement at layer 21; the dose was never swept down |\n"
    "| qualifying knob cells | 5 | prompt bans and one veto |\n"
    "| Fibonacci modal ban | 2.43 | prompt ban |\n"
    "| substring search one-shot veto | 2.54 | signature veto |\n"
    "| the other three qualifying cells | not staged in the iteration-5 audit | prompt bans |\n\n"
    "In Llama the cheapest diversity came from prompt bans, not from random pushes, and the pushes ran only at a dose about three times the ban's own displacement, where they broke programs rather than redirected them.")

# (0c) Section 4.2.2 route-landing lead
insert_after(
    "We carry this forward as the route-landing lead: where a single route suffices to remove the default, it lands on the generic neighbour that pushes and the stated alternative of the model agree on, and departures from that neighbour appear when both routes act.",
    " *(Correction, iteration 5: this generalises from one task. It is a single-task observation on connected components, where either route alone lands mostly on DFS, the neighbour that pushes and association agree on, and both routes together choose BFS. Find duplicate is the counter-example in the same table: the direct route alone removes the default and lands on index marking (74 of 78), which is neither the push landing (sort and adjacent check) nor the association answer (Floyd cycle detection). On two sum pushes and association disagree, so there is no agreed neighbour to land on.)*")

# (0d) Section 4.3: PNPLAIN rows, executed but not reported
insert_after(
    "although the frame costs 18 pass points on the grid task and adds 22 on cycle detection.",
    " *(Added in iteration 5: plan noise was also run on the plain prompt without the prohibition frame of the twin (alpha 1, 350 programs on the same common-random-number slots), and the record did not report it. Its off-default shares were 0.16 on kth smallest (0.28 under the twin frame), 0.24 on connected components (0.12), 0.26 on the shortest path task (0.26), 0.02 on the grid task (0.06) and 0 on two sum, find duplicate and cycle detection. Plan noise does not need the frame on kth smallest, connected components and the shortest path task; under plan noise at alpha 1 the frame costs 10 pass points on the grid task (interval -6 to 28). Table 173 gives the rows.)*")

# (0d) Table 139: hull deviation and triangle check rows
replace(
    "| hull vertices from the record audit only | PARTIAL | 2 | 3 | -0.134 [-0.721, 0.512] |",
    "| hull vertices from the record audit only | PARTIAL | 2 | 3 | -0.134 [-0.721, 0.512] |\n"
    "| deviation D-hull-edges (added in iteration 5): the preregistered hull search is restricted to edges; it matched a full-simplex optimiser within 0.02 on the unit cases but fell short by up to 0.19 Hill-1 on random 5-vertex Dirichlet(0.5) cases, a shortfall that falls on plan noise (5 hull vertices against 2 or 3 for most comparison knobs) | not re-evaluated | n/a | n/a | n/a |\n"
    "| triangle check on the real data (added in iteration 5): the largest gain of a 3-vertex face over the best edge, over all classes, is +0.008 (connected components, plan noise; 42 non-null entries, 113 null) | verdict unaffected | 2 | 4 | -0.22 |")

# (0b) Section 4.4: 'at any dose'
replace(
    "The read position and the condition sentence never change the algorithm at any dose: 0 of 526 and 0 of 527 correct programs off the default at alpha 1 to 4.",
    "The read position and the condition sentence never changed the algorithm at per-position doses of 1 to 4 ban units (corrected in iteration 5 from 'at any dose'; the energy-matched read position below is weaker but not inert): 0 of 526 and 0 of 527 correct programs off the default at alpha 1 to 4.")

# (0e) Table 147 depths
insert_after(
    "| shortest path | 1.00 / 0.00 / 1.00 | 1.00 / 0.00 / 1.65 | 0.90 / 0.00 / 1.70 | 0.03 / 0.07 / 1.00 | 0.00 / 0.88 / n/a |",
    "\n\n*(Correction, iteration 5: the alpha-4 peaks of this table rest on few correct programs and were rarefied at those depths, not at 25: two sum 9, find duplicate 5 and connected components 7 correct programs (kth smallest 20, grid 6, shortest path 1). 'Correct-only diversity peaks at alpha 4' on three tasks is therefore a statement about 5 to 9 programs. Depth per cell in Table 178.)*")

# (0h) Section 4.5: cross-reference to Table 76 and the literal cell
insert_after(
    "Thinking on ran in vLLM with per-request seeds (an exponential race coupling, confirmed by recomputing the first token in 32 of 32 requests), a 16k cap and the completion rate reported.",
    " *(Correction, iteration 5: the top-k 10 answer to the request with thinking off is Table 76 of iteration 2: with seeds coupled, the label changed in 0 of 30 seeds in 10 of 12 cells. The thinking-on arm of this experiment ran without top-k (top-k off, Gumbel-max coupling through per-request seeds, temperatures 0.3, 0.7, 1.0 and 1.3), so the literal cell of the request, thinking on with top-k 10 and the same seed, was not run in iteration 4. It ran in iteration 5, Section 5.7.)*")

# (0e) Section 4.5: what 17.25 of 20 means
insert_after(
    "One random plan direction at alpha 1 changed the algorithm in 17.25 of 20 seeds on the shortest path task, 4.55 on kth smallest and 2.5 on the grid task.",
    " *(Correction, iteration 5: these are not per-direction rates. Each is the mean, over the 20 three-direction subsets of the 6 directions, of the number of seeds whose label differs anywhere among the no-noise arm and the three directions of the subset, a union over three directions. The single-direction counts of changed seeds at alpha 1 and temperature 1.0 are 7, 10, 15, 17, 3 and 8 of 20 on the shortest path task, 2, 0, 0, 7, 2 and 0 on kth smallest, and 0, 0, 1, 1, 3 and 0 on the grid task.)*")

# (0c, 0e) Section 4.6: landing a property of the task; matched events; Table 157
replace(
    "The landing is a property of the task, not of the direction: on every movable task the excess-weighted landing of the 40 fresh directions reproduces the landing of the screen.",
    "The landing is a property of the task, not of the direction, at a given site (qualified in iteration 5: on find duplicate the landing depends on the site; generated-token noise and the energy-matched read position land on Floyd cycle detection, the single plan-site escape of the screen on sort and adjacent check): on every movable task the excess-weighted landing of the 40 fresh directions reproduces the landing of the screen.")
insert_after(
    "Across 14 tasks, the escape fraction of this run correlates with the avoidance of the bench ban at Spearman 0.86: the five movable tasks have avoidance 0.86 to 1.00 and the nine immovable ones 0.00 to 0.79. The opening margin does not track avoidance (0.19).",
    " *(Correction, iteration 5: the comparison above sets the push forecast's mean over its 3 defined events against the association mean over 5. On matched events, on the 3 events where the push forecast is defined (kth smallest, two sum, connected components) it scores -0.76 against -3.11 for association and -2.92 for proximity; over all 5 gated events, with an undefined forecast scored as uniform, it scores -1.37 against -3.46. The -1.37 coincides at two decimals with the route replication cell of the screen push in Table 157 (-1.369), a different quantity. Table 171 gives the matched means.)*")

# (0a) Table 159 grid row and shortest path caveat
replace(
    "| grid (DFS) | 0.125 | obeys | 0.83 | obeys | BFS 83, DFS 17 |",
    "| grid (DFS; corrected in iteration 5: NO DEFAULT, twin BFS 25 and DFS 25; DFS was frozen from a 10-sample pilot with correct BFS 4 and DFS 5, attempts 5 and 5) | 0.125 | obeys | 0.83 | obeys, but against no default | BFS 83, DFS 17 |")
replace(
    "Every sensitivity stays inconclusive (Table 160).",
    "Every sensitivity stays inconclusive (Table 160) *(correction, iteration 5: except the preregistered default-drop sensitivity, which disconfirms the claim: balanced accuracy 0.57, Fisher p 1.0, Spearman 0.39; see below and Table 169)*.")

# (0a) Table 160: add rows
replace(
    "| post hoc: shortest path relabelled by the structural rule | 15 | 0.74 | 0.24 | 0.46 |",
    "| post hoc: shortest path relabelled by the structural rule | 15 | 0.74 | 0.24 | 0.46 |\n"
    "| without NO-DEFAULT tasks (added in iteration 5; the grid task) | 14 | 0.70 | 0.51 | 0.48 |\n\n"
    "*(Correction, iteration 5: the default-drop row is the preregistered sensitivity, and under it the claim is DISCONFIRMED, not inconclusive. The two compliance measures are separated by two tasks: the grid task, whose twin is tied (BFS 25, DFS 25), so that 'obeys' (catalogue-only avoidance 0.83) is measured against a non-default baseline of 0.50 and the default share drops by only 0.33; and find duplicate, where 38 failing programs labelled other count as leaving the default under the drop measure (catalogue-only avoidance 0.34, drop 0.72). Two of the three true positives behind the Spearman of 0.54 are compromised, the grid task by its tied baseline and the shortest path task by the mislabelled array-based Dijkstra; without both, balanced accuracy is 0.61 and Spearman 0.31 (one-sided permutation p 0.144). Table 169 gives every variant.)*")

# (0a) Table 162 caveat and Table 163 caveat
replace(
    "| push landing | -0.11 | 4 of 4 |",
    "| push landing | -0.11 | 4 of 4 (corrected in iteration 5: of the 4, 2 disagree with association, kth smallest and two sum; the other 2 are compromised, the grid task having no default and the shortest path landing being mostly array-based Dijkstra) |")
replace(
    "| shortest path | 1.62 [1.37, 1.87] | 1.00 | 1.96 |",
    "| shortest path (labeller caveat added in iteration 5: the frozen labeller reads array-based Dijkstra as Bellman-Ford/SPFA; plan noise 1.62 rests on 5 and 12 programs labelled Bellman-Ford/SPFA at alpha 1 and 2, and the novelty instruction 1.96 on 29) | 1.62 [1.37, 1.87] | 1.00 | 1.96 |")

# (0f) Table 92c rows
replace(
    "| No correct novel algorithm up to breakage | Romera-Paredes et al. [81]; Novikov et al. [82] | Search with an evaluator produces new programs | Scope the claim to single-sample generation under knobs, without search or an evaluator | adjacent, scoped |",
    "| No correct novel algorithm up to breakage | Romera-Paredes et al. [81]; Novikov et al. [82] | Search with an evaluator produces new programs | Scope the claim to single-sample generation under knobs, without search or an evaluator | adjacent, scoped |\n"
    "| Plan noise (row added in iteration 5) | Jerge, Pelczar and Downes, arXiv 2608.21595 (NC-GRPO) | Scale-calibrated Gaussian noise in the last hidden layer of the prompt-encoding pass diversifies reinforcement learning rollouts of vision-language models | Test-checked mechanism labels on code, a site comparison at matched dose, and seed coupling; theirs is rollouts scored by reward | partly occupied |\n"
    "| Plan noise against temperature (row added in iteration 5) | Nagarajan et al. [80] | Noise injected at the input layer works as well as, and sometimes better than, temperature sampling at the output layer | The nearest prior answer; this run adds task-specification-state noise against temperature with the token seed held fixed, on execution-checked algorithm labels | adjacent |\n"
    "| Novelty boundary (row added in iteration 5) | Bhushan, Zhang and Wang, arXiv 2608.30047 | Agents with iterative search explore novel regions of the solution space but do not convert novelty into better task performance | Scope: single-sample generation without search; the no-novelty bound (0 among 14,206 correct programs) | contradicting in part |\n"
    "| Novelty boundary (row added in iteration 5) | Maveli, Vergari and Cohen, arXiv 2610.02438 | Code generation is better measured as parametric retrieval of a named algorithm than as synthesis of a novel one | Execution-checked labels and the bound under activation pushes | supporting |\n"
    "| Novelty boundary and knob (row added in iteration 5) | ICLR 2027 submission oag3wgNLRh (OpenReview) | Activation steering redirects generation among trajectories the model already supports, and decoding matched to the departure of steering from greedy decoding reaches comparable accuracy | Algorithm-level labels; departure-matched decoding was not run in iteration 4 and ran in iteration 5 (Section 5.7) | partly occupied |\n"
    "| Plan subspace (row added in iteration 5) | ICLR 2027 submission knirOusGcq (OpenReview), 'Before the First Token' | A shared causal subspace for response-length planning, tested by decomposing interventions into parallel and orthogonal components | A categorical, test-checked object; the forced-prompt subspace does not predict random-push effects (0.03) and removing it keeps the effect (ratio 1.00) | partly occupied |")

# (0d) Table 164: dose units
insert_after(
    "The fixed-direction escape fraction and the per-sample off-default share measure different things: a task with a few strong directions (two sum, where 5 of 40 directions escape at alpha 2) can show almost no movement under per-sample noise, which averages over directions.",
    " *(Correction, iteration 5: alpha does not mean the same push in every column. The screen uses the displacement of the ban itself; the bench unit of the plan subspace experiment is 9% to 16% smaller (its deviation 'ban_unit_scale'); the kth smallest unit of the same seed experiment is 0.77 of the screen's; the site experiment uses per-position ban units (blocks 0 to 11 at 4.5% to 7.2% of the residual norm against 12.7% to 18.3% for blocks 12 to 23); cycle detection and Gemma use a ban-free unit, which across tasks is 0.30 to 0.97 of the ban unit. Substring search has by far the largest ban unit (58.5 against 11.6 to 19.0 elsewhere) and does not move. Table 174 gives the units.)*")

# (0b) Section 4.10 item 3
insert_after(
    "Blocks 12 to 23 are not distinguished from blocks 0 to 11.\n4. *Plan noise",
    "")  # placeholder no-op to assert presence of item boundary
replace(
    "(indicator +2.15 [1.79, 2.51]; odds ratio 5.72 [3.94, 8.30]). Blocks 12 to 23 are not distinguished from blocks 0 to 11.\n4. *Plan noise",
    "(indicator +2.15 [1.79, 2.51]; odds ratio 5.72 [3.94, 8.30]). Blocks 12 to 23 are not distinguished from blocks 0 to 11. *(Correction, iteration 5: 'at any dose' and 'the site is' say more than the experiment supports. Restated: among prefill positions, perturbing the task-specification states changes the algorithm; the read position and the condition sentence are inert at per-position doses up to 4 ban units and far weaker at matched energy (energy-matched read position: +0.23 on find duplicate, Floyd cycle detection 6 of 26 correct programs, and +0.18 on connected components, 5 of 28 off the default); noise in generated tokens 1 to 32 also redirects the choice, more than the plan site on find duplicate (12:0 paired flips at alpha 2 over the 30 pairs, exact McNemar p 0.0005; 6:0 among pairs where both programs are correct). Blocks 0 to 11 against 12 to 23: -0.31 [-0.75, 0.13]. This is a prefill site at which noise is effective, not a locus of the decision, and it is reconciled with the PARTIAL site rule under Inconclusive below.)*\n4. *Plan noise")

# (0e) Section 4.10 item 5
insert_after(
    "Template halves rank 40 directions alike (0.76 to 0.90), the projection share on the plan subspace ranks them at 0.03, and removing the in-subspace component of a push leaves its effect intact (median ratio 1.00).",
    " *(Correction, iteration 5: the range 0.76 to 0.90 covers four tasks. On all six: kth smallest 0.80 (34 movers, 27 escaping direction-dose cells), shortest path 0.81 (37, 14), two sum 0.76 (10, 5), connected components 0.90 (36, 30), find duplicate 0.59 (3, 0) and the grid task 0.39 (22, 6); Table 176.)*")

# (0c) Section 4.10 item 6 moves to the descriptive results
insert_after(
    "in Gemma it hits 4 of 4, on too few disagreeing events for the rule.",
    " *(Correction, iteration 5: this item moves from Established to the descriptive results. Where pushes escape, the landing replicates across 40 fresh directions and the screen at the plan site (kth smallest quickselect 0.66 and size-k heap 0.31; connected components DFS 0.83 and BFS 0.17; shortest path Bellman-Ford/SPFA 0.99; two sum brute force; grid DFS). As a forecast of the seen bench ban landings it hits 2 of 3 defined Qwen3-8B events (it misses connected components) and scores -0.76 against -3.11 for association on those events, and -1.37 against -3.46 over all 5 with undefined forecasts scored as uniform; in Gemma it hits 4 of 4, of which 2 disagree with association and 2 are compromised. The landing depends on the site on find duplicate.)*")

# (0c) Section 4.10 item 7
insert_after(
    "7. *Route landings.* On connected components either route of a ban alone lands mostly on DFS, the generic neighbour, and only both routes together choose BFS. On kth smallest the size-k heap share travels by the prompt states.",
    " *(Correction, iteration 5: a single-task observation, with find duplicate as its counter-example: there the direct route alone lands on index marking, 74 of 78, neither the push landing nor the association answer; on two sum pushes and association disagree.)*")

# (0a, 0b) Section 4.10 Inconclusive entries
insert_after(
    "the novelty instruction predicts better (0.77), and one correct prediction rests on a labelling failure.",
    " *(Correction, iteration 5: INCONCLUSIVE under the primary measure, catalogue-only avoidance, and DISCONFIRMED under the preregistered default-drop sensitivity (balanced accuracy 0.57, Fisher p 1.0, Spearman 0.39). The grid task (tied twin, BFS 25 and DFS 25; no default under the iteration-5 rule) and find duplicate (38 failing other programs; 0.34 against 0.72) separate the two measures. Without the two compromised true positives, balanced accuracy is 0.61 and Spearman 0.31, one-sided permutation p 0.144.)*")
insert_after(
    "- *The site claim.* PARTIAL: the plan site is best on 3 of 6 tasks, with every margin but one a bootstrap close call.",
    " *(Added in iteration 5: the site rule is PARTIAL, so no site is established as best; what is established is the prefill specificity at matched displacement, odds ratio 5.72 [3.94, 8.30] for the task-specification states against the other prefill sites. The price of 1.5, the pass cost at which a site's randomisation hull first reaches correct-only Hill-1 of 1.5, is 0.12 for generated-token noise against 0.53 for the plan site on two sum.)*")

# (0e, 0c) Section 4.11
insert_after(
    "and the read position, the condition sentence and the late blocks are inert.",
    " *(Correction, iteration 5: the read position and the condition sentence are inert at per-position doses up to 4 ban units, weaker but not inert at matched energy, and the late blocks almost inert.)*")
insert_after(
    "A preregistered test of signed progress on fresh directions, with the reproducible ranking of the directions as the target, is the next step.",
    " *(Correction, iteration 5: that step was not taken, and signed progress is closed. Its positive cells concentrate on one task, it is negative on average on two, and on connected components the committed signed component was matched by a within-class control (0.33 against 0.37). Per task over 24 block cells: kth smallest 1 cell with p below 0.05 and a mean of -0.02 over the edited blocks (-0.29 at block 15); shortest path 3 and +0.20; two sum 7 and +0.31; connected components 22 and +0.37; find duplicate 0 and -0.12; grid 2 and +0.05 (Table 177; the record's '22 of 35 cells' was 22 of 24). The next budget goes to more tasks, not to a further direction-level predictor on the same five: new tasks with the base model's repertoire committed before any push, so that which tasks move can be predicted from the base model and tested on units never seen.)*")
insert_after(
    "The route-landing lead from Section 4.2.2 ties these threads together: where one route alone removes the default, the landing is the generic neighbour that pushes reach, and the ban departs from it only when both routes act.",
    " *(Correction, iteration 5: this lead rests on connected components alone; find duplicate is the counter-example and two sum has no agreed neighbour, Section 4.2.2. Movability as a forecast of ban compliance and the ban-landing contest are closed beyond descriptive reporting; the next test is the narrowed-repertoire account, Section 5.1.)*")

P.write_text(s)
print("applied; length", len(s))
