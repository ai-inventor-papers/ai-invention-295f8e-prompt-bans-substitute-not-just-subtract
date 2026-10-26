"""Build the structured review of the iteration-2 research record.

Writes .terminal_claude_agent_struct_out.json next to this script. The review text lives here;
the recomputations it cites are reproduced by verify_numbers.py in the same directory.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / ".terminal_claude_agent_struct_out.json"

overall_assessment = (
    "This record is much sounder than the iteration-1 version. All eleven must-fix items of the previous review were addressed. "
    "The iteration-1 section was changed only through corrections marked in place: I diffed it against the iteration-1 draft, and the only "
    "unmarked change is one inserted clause in item 6 of Section 1.12. Every iteration-2 artifact is written up with full tables and named source files. "
    "I recomputed the behavioural headlines from the raw per-sample rows and they match exactly: "
    "route arms a/b/c/d/K0/K1/K2 (banned share 0.14/1.00/0.57/0.70/0.47/0.16/0.19 on the grid task, 0.11/0.99/0.13/0.95/0.06/0.11/0.11 on the shortest path task), "
    "per-template counts (0,0,0,14,0), import first lines (Table 64), "
    "the ban lists (TOP BFS 59, DFS 26; ARC 63/37; SCATTER 69/27; TOP5 63/36), the post hoc chi-square p of 0.48, "
    "the leave-one-survivor 'will' shares (0.95/0.51/0/0/0), the 14 Llama events, the 13-task Qwen pilot (all collapsed), "
    "the route fractions from the per-arm drops (0.87, 0.82, pooled 0.85) and rarefied Hill-1 for nine knob rows (within Monte Carlo error). "
    "The locus numbers in results/locus.json and the C1 shares in results/c1.json match the report. I did not recompute the importance-sampling "
    "cells or the geometry subsampling from raw scores; those numbers are traceable to result files, but I have not independently verified them.\n\n"
    "What the record now supports. On two path-search tasks Qwen3-8B is collapsed (BFS, Dijkstra). Temperature, sampler, thinking mode and coupled seeds "
    "change phrasing, not the algorithm. A single ban is obeyed at a rate set by its wording: with five frozen templates, three draws on different engines gave "
    "0.14/0.14/0.15 and 0.11/0.16/0.13, and one template caused every grid failure. An obeyed ban recollapses onto one substitute. Four- and five-name bans fail by "
    "reimplementing BFS and DFS. On the shortest path task, generic perturbations land on the same substitute as the ban. KV-cache patching shows the shortest path "
    "ban carried by the prompt states, via a veto on the default program's opening import line. These are careful, replicated, mostly behavioural findings.\n\n"
    "What it does not yet support. The title claim, substitution against a latent ladder, is undetermined in both models, and the instrument behind it "
    "(the forced-ratio latent probability, FRLP) failed its preregistered gate in both. Its X-specific residuals point away from the realised substitute on the only "
    "rows where behaviour is known: on the Dijkstra-ban row, Bellman-Ford/SPFA has residual -1.84 while 272 of 272 compliant programs are Bellman-Ford/SPFA. "
    "The decomposition is dominated by survivors with negligible mass and ESS near 1. Several summary sentences outrun their evidence: 'the direct route none' "
    "ignores the natural-proposal readout (0.16 [0.11, 0.21]) and the grid behaviour (0.35); 'Llama is not collapsed on the grid task' ignores that all 20 correct "
    "Llama baseline programs are BFS; 'no knob buys a second correct algorithm' ignores that the semantic seed's correct output is Bellman-Ford/SPFA 61 and "
    "Dijkstra 30 at 7 pass points; and 'a coherent latent ladder' is listed as ruled out while the behavioural evidence supports a shared top rung. "
    "The record also omits executed outputs that answer the request directly. The ban-list artifact drew 14 activation-space manifold figures with centroids "
    "coloured by implemented count under the top-five ban, which is exactly the user's requested plot, and the report calls that item still open. The roughly "
    "25 correct out-of-catalogue programs, the only candidates for 'truly novel' output, were never inspected. No contradiction of the kind that blocked the "
    "last record remains, so soundness is 2, not 1. The record is not blocking. Its score is held at 4 by the undetermined central claim, the failed instrument, "
    "two tasks and the overstatements listed below. Fixing critiques 1, 2, 3 and 7 would make the record a sound basis for the bench confirmation."
)

strengths = [
    "Every blocking and must-fix item of the previous review was repaired. Corrections in the iteration-1 section are marked in place with what changed and why. "
    "The five-draw substitute claim now carries per-draw counts (Table 43), the cumulative ban gets its three draws (Table 44), the selection rule is quoted in full and "
    "applied to gated events (Table 48), the knob table uses one statistic (Table 47), and the locus probe's cause is recorded with timestamps and the probe re-run.",
    "Traceability is strong. Iteration-2 tables name their source files (results/c1.json, results/analysis.json#behaviour, tables/knob_table.csv, ...), every "
    "artifact carries an [ARTIFACT:id] marker, and the raw-row recomputations I ran reproduced the reported counts exactly.",
    "The route experiment is a real causal test. Token-length-matched neutral twins allow position-by-position KV splicing, attention knockouts include a "
    "generic-damage control, and sampling uses common random numbers. The opening-line veto is concretely supported: 0 of 100 import first lines under the ban "
    "and the prompt route, against 99 of 100 under the neutral twin. The record also says where behaviour qualifies the likelihood readout on the grid task.",
    "Fixed-wording replication across three engines (0.14/0.14/0.15 and 0.11/0.16/0.13), with every grid failure traced to one template, converts "
    "iteration 1's unexplained compliance spread into a measured wording effect. It is the cleanest behavioural result in the run.",
    "Dead ends are kept with their numbers: the FRLP gate failure and its scrubbing diagnosis, the failed catalogue extension (5 of 10 kept), the SAE transfer "
    "test (ratios 3.29/1.95/1.59), the Jacobian-lens gate (0.104 vs 0.291), the unavailable NLA, and a presence pilot showing Qwen collapsed on all 13 bench tasks.",
    "Bookkeeping is thorough: GPU hours from phase logs, OpenRouter spend per artifact, deviations, labeller rechecks, and independent rederivations with placebos.",
]

dimension_scores = [
    {
        "dimension": "soundness",
        "score": 2,
        "justification": (
            "The previous internal contradictions are resolved and the behavioural numbers reproduce from raw rows. But the iteration's central instrument "
            "failed its preregistered validity gate in both models. The C1 decomposition built on it is dominated by negligible-mass survivors with ESS "
            "near 1, and its residuals disagree with the observed landing on both modal-ban rows. Four summary claims outrun the evidence beside them "
            "(direct route 'none', Llama 'not collapsed', 'no second correct algorithm', ladder 'ruled out')."
        ),
        "improvements": [
            "Recompute C1 on implied probability mass, or restrict it to survivors with at least 1% mass and ESS of at least 5. Put residual argmax beside "
            "behavioural landing for every sampled single ban. Run the Llama bootstrap-versus-replicate noise diagnostic on Qwen (critique 1).",
            "Reconcile the two ladder verdicts in one paragraph and take the ladder off the ruled-out list until a behavioural test exists (critique 2).",
            "State the route result per task and per readout. Replace 'none' with the three readouts. Qualify C5 with F_R of about 0 (critique 7).",
            "Report correct-program compositions next to attempted ones for Llama and the bench pilot (critique 4).",
        ],
    },
    {
        "dimension": "presentation",
        "score": 3,
        "justification": (
            "A researcher not on the run can follow the record in order. Each iteration-2 section opens with why it ran, the protocol is defined once "
            "(Section 2.2), and tables are introduced by what they settle and name their source. Weaknesses: summary paraphrases sometimes drift from the "
            "defined metrics (Hill of at least 2 becomes 'buys a second correct algorithm'), a few rows are mislabelled (Table 66), and one inserted "
            "clause in the iteration-1 section is not marked."
        ),
        "improvements": [
            "Wherever a summary sentence paraphrases a thresholded metric, quote the metric and its interval next to it (critique 9).",
            "Fix the small factual slips listed in critique 12 and mark the inserted clause in item 6 of Section 1.12 as an iteration-2 insertion.",
        ],
    },
    {
        "dimension": "contribution",
        "score": 3,
        "justification": (
            "Nearly every executed output of the seven iteration-2 artifacts is written up with its tables, and dead ends are kept with evidence. "
            "Missing: the ban-list artifact's 14 manifold figures, coloured by implemented count (the user's requested plot), which the report says do not "
            "exist; the Qwen mention-reference aim (-0.595); correct-only compositions for Llama; an explicit record that both of the strategy's positive "
            "targets failed; and any look at the roughly 25 correct out-of-catalogue programs."
        ),
        "improvements": [
            "Add the exp9 manifold figures with a table of implemented counts per centroid and condition, and the position caveat (critique 3).",
            "Add a table of correct 'other' programs by condition with a characterisation, as the run's direct answer to the novelty question (critique 8).",
            "List the strategy's two positive targets and their outcomes in Section 2.11 (critique 10).",
        ],
    },
]

critiques = [
    {
        "category": "methodology",
        "severity": "major",
        "description": (
            "The likelihood-based substitution test (C1) in [ARTIFACT:art_6zBfl3kDjeiP] and its Llama replication cannot settle where a ban sends the mass, "
            "and the record does not say so. (i) On the only rows where behaviour is known, the X-specific residual points away from the realised substitute. "
            "In results/c1.json (primary_neutral rows), the Dijkstra-ban row has residuals Bellman-Ford/SPFA -1.84, bidirectional Dijkstra -7.92, "
            "Floyd-Warshall +3.68 and Dial +6.07. Yet all 272 compliant programs in the five iteration-1 draws, and 255 of 260 non-banned programs in the three "
            "protocol-v2 draws, are Bellman-Ford/SPFA. The BFS-ban row's largest residual is IDDFS (+7.99; DFS +0.83), while DFS takes 257 of 257 "
            "non-banned programs and IDDFS none. The route experiment repeats the pattern: its full-ban survivor gains on the shortest path task "
            "(results/analysis.json#survivor_gains) are Bellman-Ford/SPFA +2.53, the smallest, against bidirectional Dijkstra +30.64, Floyd-Warshall +12.64 "
            "and Dial +6.79, and the Bellman-Ford/SPFA cells have median ESS 1.0 to 1.2. The generic ladder profile ranks Dial (6.55) above "
            "Bellman-Ford/SPFA (5.87), although every sampled perturbation lands on Bellman-Ford/SPFA. (ii) Log gains count a +18-nat move of an algorithm "
            "with negligible implied mass the same as the realised substitute's move, and those tail cells are the least reliable ones (median ESS 1.0 to "
            "1.4, Table 61). 'Not pure subtraction' (F 16 to 22), 'not aimed' and 'no coherent ladder' therefore rest mainly on cells that are behaviourally "
            "irrelevant and close to unestimable. (iii) The Llama post hoc check found the bootstrap variance of the mean gain to be 5 to 11 times the "
            "replicate variance the frozen correction subtracts. It was never run on Qwen, whose intervals show the same upward skew: pooled V_tot is "
            "1,069.5 inside [924.8, 2,106.7], and V_u is 483.9 inside [356.8, 1,406.8]. If the noise is underestimated by that factor, both F and SHARE are "
            "inflated. The ESS-weighted 'share' of 1.24 [0.57, 1.62] is impossible for a proportion and is given without comment. (iv) The Qwen aim under "
            "the mention reference (-0.595, p of about 1.0) is omitted from Tables 56, 57 and 78, while the Llama equivalent (-0.28) is reported. Neither is "
            "flagged as negative by construction: the mention twin enters both the gain and the prime-and-veto profile, with opposite signs."
        ),
        "suggested_action": (
            "Add a table for every sampled single-ban event in both models: the argmax of the full gain, the argmax of the X-specific residual, and the "
            "behavioural landing distribution. Recompute C1 on implied probability mass after renormalisation, or restrict it to survivors with at least 1% "
            "implied mass and ESS of at least 5, weighting rows by mass, and report whether the branch changes. Run the Llama bootstrap-versus-replicate "
            "variance diagnostic on the Qwen screen and report basic intervals for V_u, V_s and SHARE. Report both models' mention-reference aims with their "
            "built-in negative bias. Until these checks pass, rewrite 'not pure subtraction', 'not aimed' and 'no coherent ladder' in Sections 2.11 and 2.12 "
            "and the closing summary as 'not detectable with the current instrument'. Expected impact: +0.5 to +1. This decides whether the title claim can "
            "be tested with FRLP on the bench at all."
        ),
    },
    {
        "category": "evidence",
        "severity": "major",
        "description": (
            "The record holds two verdicts on the rival account and never reconciles them. Section 2.11 item 2 and the closing summary say the "
            "generic-perturbation rival holds on the shortest path task. Every nonsemantic perturbation with at least 10 correct programs other than Dijkstra "
            "(8 of 8 rows, random directions included; Table 45) landed mostly on Bellman-Ford/SPFA, so 'a ban behaves like an arbitrary push'. In Llama, the "
            "empirical sampled ladder is the best per-sample predictor of the mechanism written (top-1 0.70 against 0.59 for FRLP, paired p < 1e-4; Table 72). "
            "Yet the same section lists 'A coherent latent ladder' under 'Ruled out, or not supported'. That verdict rests on mean cosines among FRLP "
            "generic-perturbation profiles (0.34 and -0.02 for Qwen, 0.14 for Llama), computed mostly over survivors with ESS near 1, from an instrument that "
            "failed its own gate in both models. The closing summary states both in consecutive sentences ('lands on the same second choice as the ban' and "
            "'the generic perturbations do not form a coherent ladder either'). The behavioural evidence supports at least a shared top rung on the shortest "
            "path task. The likelihood evidence cannot resolve the order below it."
        ),
        "suggested_action": (
            "Add one reconciling paragraph to Section 2.11. Behaviour shows a shared top rung (Bellman-Ford/SPFA on the shortest path task; DFS only under "
            "bans on the grid task). The order below the top rung is unmeasured, because it is behaviourally unobservable and FRLP is unreliable there. Move "
            "'a coherent latent ladder' out of 'ruled out' or qualify it as 'not detected by an uncalibrated instrument'. Plan a behavioural discriminating "
            "test: sampled landings under matched-norm random edits at the ban's own displacement, plus second-step bans after a random edit, on bench tasks "
            "(using Llama where present-minor events exist) where the runner-up and the associate differ. Expected impact: +0.25 to +0.5."
        ),
    },
    {
        "category": "evidence",
        "severity": "major",
        "description": (
            "An executed output that answers the user's literal request is missing, and the report says it does not exist. The ban-list artifact "
            "[ARTIFACT:art_IVZc3TWCeE9f] drew 14 activation-space manifold figures (figures/fig_manifold_t1_{baseline, single_bfs, multi_TOP, multi_ARC, "
            "multi_SCATTER, multi_TOP5} and fig_manifold_t2_{baseline, single_dijkstra, los_*}, plus fig_kstab_*; results/manifold.json). Each is an Isomap "
            "of teacher-forced states at layer 24, position 'pre', k = 10, with centroids sized and coloured by implemented count, banned centroids crossed "
            "out and natural programs overlaid. That is the request's 'manifold, colour each centroid by implemented count, then prohibit the top 5'. "
            "Section 2.12 nonetheless lists 'the activation space manifold plots with centroids coloured by implemented count' as still open, and Section 2.6 "
            "carries only [FIGURE:fig_multiban] beside the landing and disguise tables. The geometry claims of Section 2.6 also rest on the 'pre' position, "
            "which the same artifact calls a label-dependent position artefact for probes. At that position the BFS and bidirectional BFS centroids coincide "
            "(centroid distance 0.0147; Isomap coordinates (-100.99, -118.52) and (-100.92, -118.52)), so 'BFS with bidirectional BFS' as nearest neighbours "
            "may be a position effect. results/persistence.json labels its own null 'weakly powered', yet the report says it 'answers the request's question "
            "about a circle in the negative'."
        ),
        "suggested_action": (
            "Add the exp9 manifold figures to Section 2.6 with a table of implemented counts per centroid for each condition (baseline, single ban, TOP, ARC, "
            "SCATTER, TOP5, and the shortest path bans that leave one survivor). State plainly that the counts stay on the banned BFS and DFS centroids under "
            "TOP5. Recompute nearest neighbours and persistence at a position that does not depend on the label (the g16 sweep already in manifold.json) and "
            "report whether the order holds. Rephrase the circle result as 'no evidence of a loop at weak power, at a label-dependent position'. Correct "
            "Section 2.12 to say the plots exist, but not at a validated locus. Expected impact: +0.5 on coverage and contribution."
        ),
    },
    {
        "category": "evidence",
        "severity": "major",
        "description": (
            "The cross-model contrast rests on failing programs. In [ARTIFACT:art_-QPYRaFERCBX] data/labelled.jsonl, Llama's grid baseline is BFS 77, DFS 20 "
            "and other 3 among attempted programs, but its 20 correct programs are BFS 20 of 20. All 20 DFS attempts fail, so the correctness-conditioned "
            "Hill number that the run used throughout iteration 1 is 1.0: collapsed. Under the BFS ban Llama's correct programs are DFS 7, BFS 4 and other 1 "
            "(8 compliant), and under the Dijkstra ban Dijkstra 20, Bellman-Ford/SPFA 4 and other 1. The bench pilot's Llama 'diversity' is also largely "
            "failed attempts. On kth smallest the attempted programs are heapify-and-pop 16, size-k heap 11 and full sort 7, but the 10 correct ones are full "
            "sort 6, heapify 2, quickselect 1 and size-k 1, so the correct mode equals Qwen's mode. Section 2.7's heading ('Llama's baseline is not collapsed "
            "on the grid task') and the closing summary ('Llama-3.1-8B-Instruct is not collapsed on the grid task ... so the collapse is a property of the "
            "model as well as the task') report attempts only. For a request about creative solutions that work, that distinction is the result."
        ),
        "suggested_action": (
            "Add correct-program compositions beside the attempted ones in Tables 70 and 73. Restate the cross-model claim: 'Llama attempts more algorithms, "
            "but its correct grid output is as collapsed as Qwen's (BFS 20 of 20). On the bench, correct-only diversity appears on substring search (naive 18, "
            "KMP 5, Rabin-Karp 1), connected components (union-find 30, DFS 5), cycle detection and top-k at small N.' Compute Hill_cc for every Llama event "
            "so it is comparable to the Qwen tables. Expected impact: +0.25."
        ),
    },
    {
        "category": "methodology",
        "severity": "major",
        "description": (
            "Where samples were the binding constraint, the iteration again added variants and readouts instead of samples, and the PREDICT contest of the "
            "four frozen families was never run on any new event. FRLP precision is limited by the number of proposal programs. The screen fixed M = 20 "
            "programs per algorithm at the GPU deadline (bidirectional Dijkstra 11; 211 programs in all), leaving median ESS of 1.0 to 1.4 outside the "
            "forced cells (Table 61) and 98% of gate cells below 5. Instead of raising M, the run added 12 sensitivity variants over the same 211 programs "
            "(Table 59) and a Llama replication with the same problem (median ESS 2.5). The route, ban-list and readout experiments spent three more draws "
            "on the same two modal-ban events. The bench was frozen, but no ban event was run on it, so the event count behind the title claim is still 11 "
            "single-ban rows in Qwen and 6 in Llama, on two tasks. The four families frozen in Section 2.1 (ladder, association, prime and veto, proximity) "
            "were never scored together under the preregistered rule (0.10 nats on at least 3 disagreeing gated events). Table 72 is per-sample top-1 "
            "accuracy, not that rule, and the ban-list landing forecasts were degenerate. The iteration's PREDICT outcome is not stated anywhere."
        ),
        "suggested_action": (
            "State the iteration-2 PREDICT outcome explicitly: either a gated log-score table for the four frozen families on every iteration-2 event "
            "(Llama's 14 events include present-minor bans), or 'not run'. Add to Section 2.12 the arithmetic for the next budget: the M needed for median "
            "ESS of at least 5, given the observed weight dispersion per algorithm, and the number of bench ban events needed to separate SHARE from 0.5. "
            "Commit the budget to M and to bench ban events, not further variants. Expected impact: +0.5 on the contribution of the next record."
        ),
    },
    {
        "category": "novelty",
        "severity": "major",
        "description": (
            "The iteration-2 positive claims are not set against their nearest published neighbours. Table 52 positions only iteration-1 claims. "
            "(a) The claim that the read position knows how hard a wording will be obeyed (C5, rho -0.41) neighbours Heo et al. 2024, 'Do LLMs \"know\" "
            "internally when they follow instructions?' (arXiv 2410.14516). That paper finds a pre-generation dimension in input-embedding space that predicts "
            "instruction-following success, is driven by prompt phrasing, and raises success when intervened along. This run adds a wording-level correlation "
            "for prohibitions in code, but its own route test finds the read position alone causally inert (F_R of about 0), a contrast with Heo's intervention "
            "that should be recorded. (b) The SAE dead end neighbours Kissane et al. 2024, 'SAEs (usually) transfer between base and chat models' (Alignment "
            "Forum; Mistral-7B and Qwen1.5-0.5B transfer, Gemma v1 2B does not). Here the fraction of variance unexplained is lower on instruct than on base at "
            "layers 20 and 27 (0.094 vs 0.243; 0.153 vs 0.325; results/transfer_summary.json). The failure comes from the CE-increase ratio, with the instruct "
            "model's clean CE nine times lower (0.030 vs 0.260), so the dead end may be an artefact of the criterion. The remedy Section 2.12 proposes, "
            "fine-tuning the base SAE on instruct activations, is Kissane et al.'s, and they are not cited. (c) The prompt-route, knockout and priming results "
            "neighbour Rana 2026 [7] (activation patching of negative constraints; naming primes the forbidden item) and Mann et al. [53]. Both are cited "
            "inline, without a line on what this run adds. (d) Ban lists failing by reimplementation and disguise neighbour denial prompting [23]."
        ),
        "suggested_action": (
            "Extend Table 52 with one row per iteration-2 positive claim: compliance predictable at the read position (Heo et al. 2024), the opening-line "
            "veto and prompt route (Rana 2026; Geva et al. 2023 for the knockout method), priming by naming (Rana 2026; Mann et al.), ban-list reimplementation "
            "(Lu et al.), and SAE transfer (Kissane et al. 2024). For each, give the neighbour's finding, then what this run adds or 'replication'. Rerun or "
            "rephrase the SAE transfer verdict with a criterion that does not penalise the instruct model's lower clean CE (for example, the fraction of CE "
            "loss recovered against a zero-ablation baseline, computed per model on its own outputs). Expected impact: +0.25 to +0.5."
        ),
    },
    {
        "category": "evidence",
        "severity": "major",
        "description": (
            "The headline route claim is stated more strongly in the summary than its evidence allows. 'In Qwen3-8B the prompt route carries 0.85 of the "
            "banned algorithm's likelihood drop and the direct route none, and Llama agrees (0.84)' rests on the preregistered FRLP readout. Section 2.5 "
            "itself says that readout is degenerate on the grid task (ESS 1 to 3 of 30; exp(D) 3e-7 against a behavioural ratio of 0.14) and measures the "
            "opening-line veto. Two other readouts in the same artifact show a direct route. The natural-proposal readout gives F_direct 0.16 [0.11, 0.21], "
            "an interval that excludes 0, with superadditive routes. Grid behaviour gives direct 0.35 [0.25, 0.45], and the full knockout restores BFS to "
            "0.47, which I recomputed from data/samples.jsonl (condition K0): about 38% of the grid ban's behavioural effect needs generated tokens to read "
            "the ban. The Llama number is FRLP-only, on an instrument that failed its gate there (median ESS 2.5). C5 ('the read position carries part of "
            "how strongly a wording will be obeyed') sits next to F_R of about 0, so that site is decodable but carries none of the ban's effect causally. "
            "This is the decodability-versus-actionability gap the field now tests for routinely."
        ),
        "suggested_action": (
            "Rewrite item 3 of Section 2.11 and the summary per task and per readout. Shortest path: the prompt route carries the ban in likelihood (0.82) "
            "and in behaviour (0.98). Grid: the likelihood readout is dominated by the opening fork (0.87), behaviour is mixed (prompt 0.50, direct 0.35), "
            "and the natural readout puts the direct route at 0.16. Llama: likelihood only. Remove 'none'. Add 'splicing the read position alone carries "
            "none of the effect (F_R of about 0)' to every C5 statement, and list a causal test of the shared ban direction (add or subtract it at the "
            "task-specification positions and measure compliance) as next work. Expected impact: +0.25."
        ),
    },
    {
        "category": "scope",
        "severity": "major",
        "description": (
            "The core request ('can we make llms give truly creative and novel solutions?') is answered only inside a fixed catalogue, and the run never "
            "looks at the one place a novel solution could appear. Across the per-sample files of exp1, exp4, exp5 and exp6 (iteration 1), and exp8, exp9, "
            "exp10 and exp12 (iteration 2), about 22,000 programs, I count roughly 25 correct programs labelled 'other', i.e. outside the catalogue: exp9 13 "
            "(mostly forced conditions), iteration-1 decommitment steering 6, Llama 5 and association 1. None came from the creativity, new-algorithm or "
            "novelty instructions, whose correct programs are all catalogue algorithms (for example novelty, grid: BFS 81, unit-weight Dijkstra 2, DFS 1, "
            "A* 1). The 'other' programs are never inspected. Under the TOP ban, the 13 'not banned' programs that make its avoidance 0.13 are 12 failing "
            "programs labelled 'other' that are visibly DFS or BFS reimplementations ('def dfs(r, c)', '# Use a queue to perform BFS (but we av...') plus "
            "1 unit-weight Dijkstra. The request's long-form instruction ('Make a fully novel algorithm never seen before ... 2000 words ...') was run only "
            "as the one-line 'Make a fully novel algorithm never seen before.' (exp6 prompts.json), and never with thinking on. The same-seed arm with "
            "thinking on and an SAE readout that passes transfer remain open, as the report says."
        ),
        "suggested_action": (
            "Add a table of every correct out-of-catalogue program by condition and model, with a blind judge or manual characterisation (novel algorithm, "
            "variant of a catalogue algorithm, or labeller miss). State the result as the run's direct answer to the novelty question: across about 22,000 "
            "programs, no instruction produced a correct non-catalogue algorithm, if that holds. Run the request's long-form novelty prompt, with thinking on "
            "and off, as one cheap condition on both tasks. Report the 'other' share separately from avoidance in the ban-list tables. Expected impact: "
            "+0.25 to +0.5 on coverage."
        ),
    },
    {
        "category": "clarity",
        "severity": "major",
        "description": (
            "The answer to the user's 'can we influence it?' is paraphrased past its metric. The summary says 'Under one statistic, no ban and no diversity "
            "knob buys a second correct algorithm for less than 20 points of pass rate on either task.' The operational target is rarefied Hill-1 of at least "
            "2, which a 2:1 split can never reach. The semantic seed's correct output on the shortest path task is Bellman-Ford/SPFA 61, Dijkstra 30 and "
            "Floyd-Warshall 1 at 7 pass points (Table 47). It moves the mode and plainly buys a second correct algorithm, and its Hill-1 interval "
            "[1.534, 2.076] includes 2 (I recomputed 1.934 by rarefaction). The BUY-rule outcome also depends on an unregistered class rule. The A* mention "
            "on the grid task (Hill-1 2.69 at 11 points, 88% of the reference pass rate) beats the next row by more than the 0.5 margin, but is excluded as "
            "a 'named mode cue', while sham bans, which are also controls, are ranked as knobs (Table 47, IDDFS sham 1.205)."
        ),
        "suggested_action": (
            "Rewrite the verdict in Sections 2.3.6 and 2.11 and the summary as: 'No knob reaches an even two-algorithm split (Hill-1 of at least 2) under 20 "
            "points. The semantic seed (Bellman-Ford/SPFA 61, Dijkstra 30 at 7 points; interval includes 2) and the A* mention (2.69 at 11 points) are the two "
            "conditions that buy a second correct algorithm, and both name or describe it.' Declare the knob-class rule (which controls count as knobs) and "
            "apply it consistently to mention twins and sham bans. Expected impact: +0.25."
        ),
    },
    {
        "category": "rigor",
        "severity": "minor",
        "description": (
            "The strategy's two positive targets failed, and the record never says so in those terms. The strategy predicted (1) an X-specific gain for DFS "
            "under the BFS ban that the ladder cannot match, but Table 58's largest residual for that row is IDDFS and DFS's residual is +0.83; and (2) that "
            "the direct generation-time route would carry at least two thirds of the ban's effect, but F_direct is 0.00 in likelihood, 0.35 in grid behaviour "
            "and 0.05 in shortest path behaviour. Section 2.5 says the update 'predicted ... a direct route', but Section 2.11 lists no failed predictions. "
            "Separately, the readout experiment ran about 11 hours after the audit had named generated tokens 1 to 3 as the extraction target "
            "(results/locus.json written 02:40 UTC; readout results/e2_meta.json 13:31 UTC), yet saved only R, k16, k_pre, k_post and meangen "
            "(results/tensors/e2_states.npz pos_keys). The record does not say why: presumably the plan was frozen before the audit."
        ),
        "suggested_action": (
            "Add a 'preregistered predictions and outcomes' list to Section 2.11 with both positive targets marked failed and their numbers. Add one line to "
            "Section 2.9 or 2.12 explaining why tokens 1 to 3 were not saved in this iteration, so the next strategy treats them as the first extraction."
        ),
    },
    {
        "category": "methodology",
        "severity": "minor",
        "description": (
            "The confirmation bench inherits an instrument that is not commensurable with the screen. The bench's frozen baseline likelihoods "
            "[ARTIFACT:art_0ndRfWKBWclR] come from FP8 weights through vLLM prompt log-probabilities, and batched and single-request scoring disagreed by "
            "0.62 nats on 1 of 5 checked programs. The screen had to move to fp32 activations because bf16 moved per-program log-likelihoods by up to 2.1 "
            "nats, comparable to the between-survivor SDs being measured (1.5 to 7.8 nats, Table 58). The recommendation to score unscrubbed programs is "
            "validated only on baseline, mention and listing events. On ban rows, the algorithm names left in identifiers and comments interact with the "
            "ban's own naming, which is the mechanism scrubbing was introduced to remove."
        ),
        "suggested_action": (
            "Before forecasts are committed, rescore the bench baselines on the screen's fp32-activation path, and validate the unscrubbed variant, or a "
            "name-matched one (names replaced by neutral identifiers of equal token length), on the iteration-1 ban rows against their sampled landings. "
            "Record both checks in the bench section."
        ),
    },
    {
        "category": "clarity",
        "severity": "minor",
        "description": (
            "Several small factual slips. (1) Table 66 labels the bidirectional Dijkstra and Dial rows 'plain', but the 14 of 40 and 36 of 40 counts come "
            "from the descriptive prompts. In exp9 data/samples.jsonl, forced:bidijkstra has 10 samples (Dijkstra 9) and forced_desc:bidijkstra 40; "
            "forced:dial has 10 and forced_desc:dial 40. (2) Section 2.11 item 2 says no nonsemantic perturbation left BFS among correct programs on the "
            "grid task, but Table 46's T = 1.3, top-k = 10 row has DFS 1. (3) Item 6 says the model 'can write ... Dial when told to', but forced Dial passes "
            "7 of 40 (0.175). (4) TOP's avoidance of 0.13 is labeller residue: 12 failing BFS/DFS variants labelled 'other' plus 1 unit-weight Dijkstra. "
            "(5) The clause added to item 6 of Section 1.12 ('which is consistent with geodesic proximity and with typicality ... not separated on these "
            "events') is not marked as an insertion; its correction note covers only the layer-24 instability."
        ),
        "suggested_action": (
            "Correct the five items in place, with iteration-3 markers where they touch earlier sections."
        ),
    },
]

review = {
    "overall_assessment": overall_assessment,
    "strengths": strengths,
    "dimension_scores": dimension_scores,
    "critiques": critiques,
    "results_reported": True,
    "coverage": "partial",
    "blocking": False,
    "score": 4,
    "confidence": 4,
}

# Derived-rule check: blocking iff soundness <= 1 or results not reported.
soundness = next(d["score"] for d in dimension_scores if d["dimension"] == "soundness")
assert review["blocking"] == (soundness <= 1 or not review["results_reported"])

OUT.write_text(json.dumps(review, indent=2, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {len(critiques)} critiques)")
