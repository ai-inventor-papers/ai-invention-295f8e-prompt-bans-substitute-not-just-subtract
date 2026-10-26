"""Assemble the structured review and write it to ../.terminal_claude_agent_struct_out.json (run from audit/)."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / ".terminal_claude_agent_struct_out.json"

overall = (
    "This is the iteration-1 record of a six-account screen of algorithm choice in Qwen3-8B on the request's two path-search tasks "
    "(seven artifacts: one dataset, six experiments). As a lab record it is unusually complete and accurate. Every executed artifact "
    "is written up with its tables, the dead ends are kept with the evidence that killed them, and the preregistration bookkeeping "
    "(hash-committed forecasts with commit times, spend, the hypothesis-review scores 5,6,6,7,7,7,7, which I checked) is preserved. "
    "I recomputed the sample-level tables from each artifact's per-sample rows and found no mismatch. This covers Table 3 (61,469 examples; "
    "inspiration-repo labels Dijkstra 132 / Bellman-Ford-SPFA 34 / ...), Table 4 (1,199/1,200 BFS; 1,174/1,200 Dijkstra), all 40 "
    "conditions of Table 6 including Hill_cc, Tables 11, 13 and 16 (geometry), the label counts of Table 22, Table 24, Tables 27 and 31, "
    "and Table 34. By hand I recomputed the Table 7 log scores (-2.817, -0.755, -1.630, -1.406, -0.112, -0.061) and the Table 14 "
    "geodesic score (-1.337, median centroid distance 71.06). I also re-ran the association experiment's grid hidden tests on 250 programs "
    "and reproduced the artifact's pass/fail labels on 250 of 250. Bootstrap intervals, slopes and activation statistics (Tables 15, 25, 29, 32, 33) "
    "were checked against the artifacts' result files (for example analysis.json subspace_test), not recomputed from raw activations, and I "
    "treat them as verified-by-file. No projected, illustrative or placeholder number was found, so results_reported is true. "
    "BLOCKING: two conclusions contradict the report's own tables, so by rule soundness is 1 and blocking is true. (1) The headline "
    "that the post-ban substitute 'replicated in five independent draws' ('landed on the same substitute every time', 'collapses again "
    "on one substitute') is false for the grid task. In the geometry draw the 18 compliant programs split DFS 10 / unit-weight Dijkstra 8, "
    "and Section 1.6 itself calls this 'no clear realised mode'. (2) Section 1.11 states 'On the grid task no knob that kept 80% of the "
    "pass rate produced a second algorithm among compliant programs'. Table 37's own decommitment row contradicts it (cumulative "
    "BFS+DFS ban, pass 0.88 of 1.00, 16 compliant programs: unit-weight Dijkstra 13, A* 3), and so does Table 13 (geometry BFS+DFS "
    "ban, pass 0.96, 18 compliant, all unit-weight Dijkstra). The measurements are sound. The fix is to rewrite these conclusions and "
    "to re-run the selection rule as preregistered. Section 1.1 omits the PREDICT gate that defines an informative event (compliance "
    ">= 50%, >= 2 survivors). Under either compliance definition, the geometry and instruction-tuning modal events and the decommitment "
    "shortest-path event fail that gate, yet Tables 14 and 36 score them, and the BUY tie is decided on one task although the rule "
    "asks for pooled tasks plus the same direction on each. Other major gaps: "
    "(a) the random-direction controls move the shortest-path task to the same substitute (exp5 random-2: 33/33 correct "
    "programs Bellman-Ford/SPFA, shown in Table 26 only as 'Hill 1.00, delta 0'). This is a generic-perturbation rival to ban-specific "
    "promotion, and the report never states it. (b) The geodesic-neighbour claim rests on a failed grid read-position gate. It is "
    "confounded with typicality, has no k/layer robustness check, and an unreported sensitivity file reverses the shortest-path rank. (c) The "
    "locus probe ran at 18:29, before its states were saved at 18:34, so it is a CPU-only re-run, but the report does not record this "
    "cause. (d) The read-position evidence on seeds is half-reported: on the shortest-path task the semantic seed's displacement points "
    "away from the implied centroid (cos -0.087) while behaviour moves 66 pp toward it. (e) The final hypothesis review's objections "
    "are not recorded. (f) No positive claim is compared with its nearest published neighbour (SimpleStrat, Verbalized Sampling, "
    "Lee et al. 2026, Goudarzi et al. 2026). (g) The iteration added forecasters (15 families) to two informative events instead of "
    "adding events. Coverage of the request is partial: SAE, thought anchors, NLA and j-lens are absent, the top-5 prohibition was "
    "never run, and the internals of natural BFS versus DFS runs were not analysed. Score 4: the descriptive behavioural findings are "
    "solid and reproducible (total collapse, temperature as a phrasing knob, bans that re-collapse onto a substitute, ban compliance "
    "driven by wording). The mechanistic hypothesis is untested, the scope is one model and two tasks, and the positive findings sit "
    "close to published work."
)

strengths = [
    "Completeness verified by recomputation, not taken on trust. Every one of the seven artifacts is written up, and the sample-level "
    "tables I rebuilt from the per-sample JSONL rows match the report to the last digit: Tables 3, 4, 6 (all 40 conditions, including "
    "Hill_cc), 11, 13, 16, 22 (label counts), 24, 27, 31 and 34. The Table 7 and Table 14 log scores also match when recomputed by hand. "
    "An independent re-run of the grid hidden tests reproduced the association experiment's pass/fail labels on 250 of 250 programs.",
    "Dead ends are kept and labelled with the evidence that killed them. Affine ablation moved 0/50 at alpha <= 2 with 78-90% of "
    "texts byte-identical to alpha=0. Sharpening subtraction left 0/100 programs parseable. The forking-window temperature arms were "
    "100% the default. The decommitment direction did no better than a random direction (+0.07 [-0.26, 0.39]). The Borda map was "
    "unstable across two elicitations. Typicality is uniform under total collapse. Mention twins act as recommendations. The locus "
    "probe failed and the reserved bench was never built. The paper step will know these were tried.",
    "The preregistration bookkeeping is preserved in the record: commit times precede first generation in each experiment (for "
    "example 15:18:30 vs 15:20:05 UTC; sha256 186f7182... at 16:36:57), along with spend per artifact and the hypothesis-review "
    "score trajectory, which matches the review files (5,6,6,7,7,7,7; final soundness 3, presentation 3, contribution 3, fidelity 4).",
    "The replicated-draw design yields a real, correctly drawn finding. Five independent draws of the same modal ban (Table 34, which "
    "I recomputed) show that compliance depends on the ban sentence: banned share 0.09-0.72, with per-paraphrase counts from 0/10 to "
    "10/10. The report states the right consequence: any ladder-limit analysis must hold wording fixed or model it.",
    "Limits are stated without selling. The section on what iteration 1 established is explicitly descriptive. The labeller gate "
    "failures are disclosed with their numbers (Table 2). The Hill_cc flaw (correct banned programs count as a second idea) is "
    "admitted. The two conflicting 'compliance' definitions are neutralised by reporting banned share and compliant counts "
    "recomputed from rows. The central quantitative hypothesis is declared untested rather than confirmed.",
    "Direct, data-backed answers to the request's literal questions 1a-c and 2. The BFS share is 797/800 (thinking off) and 800/800 "
    "(thinking on) across 4 temperatures x 2 samplers. A full ideas-by-phrasings table is given at three Jaccard thresholds with "
    "bootstrap slopes. The seed equivalence tests sit within +/-15 pp. The requested activation-space manifold plot with centroids "
    "coloured by implemented count exists (geometry artifact figures/manifold_t1.png).",
]

dimension_scores = [
    {
        "dimension": "soundness",
        "score": 1,
        "justification": (
            "Set by the review rule. Two conclusions contradict the report's own tables. First, the grid-task claim that the "
            "substitute replicated in five draws is contradicted by the geometry draw: DFS 10 / unit-weight Dijkstra 8, which Section "
            "1.6 calls no clear mode. Second, 'no grid knob at the 80% floor produced a second algorithm among compliant programs' is "
            "contradicted by Table 37's decommitment row (16 compliant: unit-weight Dijkstra 13, A* 3) and by Table 13 (18 compliant, "
            "unit-weight Dijkstra). The underlying measurements are sound and reproduce. Further soundness defects: the selection rule "
            "is misreported and misapplied (informative-event gate omitted, BUY tie decided on one task, mixed Hill statistics); the "
            "geodesic-neighbour claim is presented as established despite a failed grid gate and no k/layer robustness; and "
            "'sharpened, not installed' relabels a preregistered INSTALLED_BY_POST_TRAINING verdict."
        ),
        "improvements": [
            "Rewrite established item 4, the Section 1.11 replication paragraph and the closing summary. The shortest-path task: "
            "Bellman-Ford/SPFA in 5/5 draws (272/272 compliant). The grid task: DFS was the realised mode in 4/5 draws (pooled DFS "
            "116/128 = 90.6%); in the HF-engine geometry draw the 18 compliant programs split DFS 10 / unit-weight Dijkstra 8. Also "
            "drop 'bans collapse the output again; they do not spread it' for the grid task, where the step-2 bans in exp2 and exp4 "
            "sent compliant programs to unit-weight Dijkstra and A*. Expected impact: removes one blocking contradiction (with the "
            "next item, soundness 1 -> 2-3).",
            "Replace the grid BUY sentence with what the table shows. The cumulative BFS+DFS ban reached the floor with a second "
            "correct algorithm in the decommitment draw (0.88/1.00; unit-weight Dijkstra 13, A* 3) and in the exploratory geometry "
            "draw (0.96/0.99; unit-weight Dijkstra 18). It failed by disguise in the association draw (pass 0.53; 5 compliant). Record "
            "it as a non-replicating grid BUY candidate. Expected impact: removes the second blocking contradiction.",
            "Quote the full selection rule from gen_strat_1 and choose one compliance definition. Add a per-event gate column "
            "(banned-mode presence, compliance >= 50%, >= 2 survivors) to Tables 14 and 36, recompute PREDICT on gated events only, and "
            "recompute BUY on one statistic, pooled and per task. Expected impact: +0.5 to +1 on the overall score.",
            "Downgrade established item 6 (displaced mass moved to geodesic neighbours) to 'consistent with both proximity and "
            "typicality'. Keep it there until a k x layer sweep from the cached states and the manipulation-sensitivity matrix are "
            "reported.",
        ],
    },
    {
        "dimension": "presentation",
        "score": 3,
        "justification": (
            "A researcher who was not on the run can follow the record in order. Each experiment has why / design / results / what "
            "it settled, each table is introduced by the question it answers, and the conventions (read position, compliant sample, "
            "realised mode, Hill_cc, log score) are defined once in Section 1.2. It loses a point on three counts. Table 37 mixes raw "
            "Hill_cc with rarefied delta-Hill against different references. Table 26 reports Hill without label composition, which "
            "hides a complete Dijkstra-to-Bellman-Ford flip. Tables are tied to artifacts but not to the result file each came from."
        ),
        "improvements": [
            "Under each table, name the output file it came from, e.g. Table 15 <- gen_art_experiment_2/results/c3_decomposition.json, "
            "Table 32 <- gen_art_experiment_6/results/analysis.json:subspace_test, Table 20 <- gen_art_experiment_3/swap.json "
            "(aggregate).",
            "Add a 'labels of correct programs' column to Table 26 and to every BUY row, so that a change of algorithm at Hill 1.00 is "
            "visible.",
            "Put Table 37 on one statistic: rarefied Hill over compliant programs at a common depth, each experiment against its own "
            "baseline, with the 90% interval the rule asks for.",
        ],
    },
    {
        "dimension": "contribution",
        "score": 3,
        "justification": (
            "Almost the whole run is preserved: all seven artifacts, their tables with correct numbers, dead ends with evidence, spend "
            "and review scores. Missing: the association experiment's 11 forced-implementation conditions (N=10 each), although "
            "Table 6 claims 'every condition'; the geometry manipulation-sensitivity matrix, which changes the shortest-path rank; "
            "the forking-token next-token entropies and confirmation-threshold sensitivity; the decommitment layer-14/22 arms; the "
            "label compositions of the steering arms; the shortest-path semantic-seed direction result (cos -0.087); the cause of "
            "the empty probes.json; GPU hours for four experiments; and the content of the hypothesis review's objections."
        ),
        "improvements": [
            "Add the missing artifact outputs listed in the minor completeness critique, each as one table row or one sentence with "
            "its file name.",
            "Add a subsection on what the final hypothesis review objected to and what the screen showed for each objection.",
            "Record the probe failure cause (timestamps) and the location of the saved states, so the next iteration runs the locus "
            "probe on CPU first.",
        ],
    },
]

critiques = [
    {
        "category": "evidence",
        "severity": "major",
        "description": (
            "BLOCKING CONTRADICTION 1, the five-draw substitute claim. Established item 4 ('that substitute replicated in five independent "
            "draws: DFS for BFS'), Section 1.11 ('Where the ban had compliant samples, they landed on the same substitute every time: "
            "DFS on the grid task (with a few unit weight Dijkstra programs)') and the closing summary ('collapses again on one "
            "substitute ... the same substitute in five independent draws') contradict Table 13, Table 34 and Section 1.6. In the geometry "
            "draw the 18 compliant grid programs are DFS 10 and unit-weight Dijkstra 8, and Section 1.6 calls this 'no clear realised "
            "mode'. Eight of 18 is not 'a few'. Recomputed per draw from the per-sample rows (compliant grid programs): association DFS 38/38, "
            "forking token DFS 40/41, decommitment DFS 16/18, instruction tuning DFS 12/13, geometry DFS 10/18; pooled DFS 116/128 "
            "(90.6%). The shortest-path claim holds: Bellman-Ford/SPFA 272/272 in all five draws. Moreover 'bans collapse the output "
            "again; they do not spread it' is contradicted on the grid task by the step-2 bans: geometry BFS+DFS sent 18 compliant "
            "programs to unit-weight Dijkstra, and decommitment BFS+DFS gave unit-weight Dijkstra 13 and A* 3."
        ),
        "suggested_action": (
            "Rewrite the three passages with per-draw counts. Shortest-path task: 5/5 draws, 272/272. Grid task: DFS realised mode in "
            "4/5 draws; one HF-engine draw (62% banned share) with no clear mode (DFS 10, unit-weight Dijkstra 8). Add a pooled row to "
            "Table 34 with Wilson intervals. State that second-step bans on the grid task can spread compliant output over unit-weight "
            "Dijkstra and A*. Expected impact: clears half of the blocking flag. The headline survives in a weaker, correct form."
        ),
    },
    {
        "category": "evidence",
        "severity": "major",
        "description": (
            "BLOCKING CONTRADICTION 2, the grid BUY verdict. Section 1.11 states: 'On the grid task no knob that kept 80% of the pass "
            "rate produced a second algorithm among compliant programs: the cumulative ban's gain came from programs that still used "
            "BFS'. Table 37's own row 'cumulative ban of BFS and DFS (decommitment) | 0.88 / 1.00 | yes | ... | BFS 65, unit weight "
            "Dijkstra 13, DFS 7, A* 3' shows 16 compliant programs over two non-banned algorithms. Table 13's exploratory geometry "
            "BFS+DFS ban shows pass 0.96 with 18 compliant unit-weight Dijkstra programs. Both counts reproduce from "
            "gen_art_experiment_4/data/samples.jsonl and gen_art_experiment_2/data/samples_phaseC.jsonl. The same knob failed by "
            "disguise in the association draw (pass 0.53, 5 compliant). The report therefore also never says whether the strategy's "
            "preregistered POSITIVE TARGET ('a knob that buys a second correct algorithm at under 20 points of pass rate') was met. "
            "It was met on the shortest-path task by the prompt ban (exp5, 0 points) and the semantic seed (7 points), and on the grid "
            "task only by this non-replicating cumulative ban."
        ),
        "suggested_action": (
            "Replace the sentence with the three draws of the cumulative BFS+DFS ban (decommitment 0.88/1.00 with 16 compliant; geometry "
            "0.96/0.99 with 18; association 0.53/0.933 with 5) and call the grid BUY candidate non-replicating. Add one line stating the "
            "POSITIVE TARGET outcome per task. Expected impact: clears the other half of the blocking flag."
        ),
    },
    {
        "category": "methodology",
        "severity": "major",
        "description": (
            "The selection rule is misreported and misapplied. The strategy (gen_strat_1 rationale) scores PREDICT 'on every "
            "informative event (banned mode present at >= 10% of the latent baseline, compliance >= 50%, >= 2 survivors)'. Section 1.1 "
            "omits this gate. Modal-ban compliance per draw, as 1 - banned share / as the compliant share: association 0.90/0.38 (grid) "
            "and 0.91/0.86 (shortest path); geometry 0.38/0.18 and 0.28/0.22; decommitment 0.51/0.18 and 0.46/0.38; instruction tuning "
            "0.38/0.13 and 0.46/0.46. So the geometry events (which Table 14 calls 'primary'), both instruction-tuning events and the "
            "decommitment shortest-path event fail the gate under either definition. Under the stricter definition even the "
            "association grid event fails. Table 36's descriptive ranking ('the highest scoring forecasts ... the base model's own "
            "distribution and ... the decommitted distribution') therefore rests largely on gated-out events: the base-model forecast "
            "was scored only on instruction-tuning events, the decommitted forecast only on the decommitment shortest-path event, and "
            "the geodesic kernel only on geometry events. The BUY rule requires a winner 'on the pooled tasks and in direction on each "
            "task'. The report declares the prompt ban and the semantic seed tied using the shortest-path task alone (1.99 vs 1.988, "
            "from different experiments with different baselines). Table 37 also mixes raw Hill_cc and rarefied delta-Hill, and Hill_cc "
            "counts correct banned programs, which the report itself calls a flaw."
        ),
        "suggested_action": (
            "Quote the full PREDICT/BUY rule in Section 1.1. Fix one compliance definition (state which one the strategy meant, or report "
            "both). Add gate columns to Tables 14 and 36 and recompute the PREDICT means on gated events only. Recompute BUY with one "
            "statistic (rarefied Hill over compliant programs, i.e. excluding banned labels, at a common depth, with the 90% sample "
            "bootstrap the rule names), pooled and per task, and state the rule's outcome (which knobs advance) explicitly. Expected "
            "impact: +0.5 to +1. It makes the scorecard the next iteration acts on trustworthy."
        ),
    },
    {
        "category": "methodology",
        "severity": "major",
        "description": (
            "The iteration added metrics, not samples, to an underpowered panel. Table 36 scores 15 forecast families on the same two "
            "modal-ban events, while the selection rule needs at least 3 events on which nominations disagree. The final hypothesis "
            "review's own power arithmetic needed roughly 66 pooled events for the confirmatory test. Running the same two events in "
            "five experiments buys replication of the substitute, not more events. More predictors and more readouts (decoder, "
            "geodesic kernel, decommitted, base-model, free-form, listing, first-rank, external map) over two events cannot select a "
            "survivor. The report concludes only that 'the contests need tasks whose baselines are not fully collapsed'. It does not "
            "say that the budget belonged on events, nor that the planned 12-task LeetCode bench may also be fully collapsed, which "
            "would make the typicality predictor uniform again."
        ),
        "suggested_action": (
            "State in the 'what we have learned' section that the next iteration's budget goes to events, not to predictors. Before "
            "freezing any bench task, run a cheap baseline pilot (N=50 at T=1.0) and keep only tasks whose second algorithm reaches the "
            "10% presence cut. Add ban targets in the present-minor stratum, and hold ban wording fixed or model paraphrase as a random "
            "effect. Freeze the predictor set at the families that already exist. Expected impact: +0.5 on contribution of the next record."
        ),
    },
    {
        "category": "evidence",
        "severity": "major",
        "description": (
            "Missing synthesis: random directions push the shortest-path task to the same substitute. The report treats Bellman-Ford/SPFA "
            "as the model's 'second preference' revealed by bans, but its own controls show that any perturbation lands there. In the "
            "decommitment experiment, random direction rand1 at c=0.25 moved correct programs to Bellman-Ford/SPFA 26 of 79 (vs 7/95 at "
            "c=0; dc minus rand1 +0.07). In the instruction-tuning experiment, band random direction 2 (c=0.5) turned all 33 correct "
            "programs into Bellman-Ford/SPFA, against Dijkstra 100/100 in the control. Table 26 shows this arm only as 'Hill_cc 1.00, delta "
            "0.00, flip 0.36', hiding a complete algorithm switch. random1_Ronly gave Bellman-Ford/SPFA 9. The breadth and placebo "
            "directions, the semantic seed, the novelty instruction, the enumeration prompt and the base model all move toward the "
            "same algorithm. This is a direct rival to the main hypothesis (a ban-specific promotion of an associate), namely that any "
            "perturbation of the read-position state, semantic or not, spills mass onto the runner-up. The report never names it. It "
            "also bears on established item 5."
        ),
        "suggested_action": (
            "Add label composition to Table 26. Add a cross-experiment table of every shortest-path perturbation (prompts, steering, "
            "random and placebo directions, seeds, instructions) with the Bellman-Ford/SPFA share among correct programs and its "
            "pass cost. State the generic-perturbation rival in the 'what we have learned' section and list it among the alternates. "
            "Plan a discriminating test: matched-norm random read-position edits versus the ban at equal displacement, with common "
            "seeds, on tasks where the runner-up and the associate differ. Expected impact: +0.5. It changes what the next iteration "
            "should test."
        ),
    },
    {
        "category": "evidence",
        "severity": "major",
        "description": (
            "The geometric claim (established item 6, 'mass moved to the edge of the banned region rather than to the opposite side') "
            "overreaches its evidence. (i) The grid read-position gate failed: the decoder reads the baseline as DFS 0.60 / unit-Dijkstra "
            "0.27 / BFS 0.12 while the model writes BFS every time. (ii) DFS and unit-weight Dijkstra are also the model's typical "
            "runner-ups (free-form answers, base model), so proximity and typicality are not separated. On the grid event the geodesic "
            "kernel scored -1.337, behind the free-form answer (-0.112) and the listing control (-0.061). (iii) The claim rests on 18 "
            "compliant programs plus exploratory step-2 events with 18 and 5. (iv) Geodesic stability was assessed only by resampling "
            "point clouds (results/contest.json, geodesic_share_same_nearest 0.985), which the final hypothesis review warned is "
            "uninformative. No k or layer sweep exists, and MDS stress-1 is 0.22. (v) results/manipulation_sensitivity.json, not in the "
            "report, recomputes the flagged centroids and puts bidirectional Dijkstra (40.91) closer to Dijkstra than Bellman-Ford/SPFA "
            "(42.18). So 'the mass went to the second nearest centroid, Bellman-Ford/SPFA' does not survive the artifact's own "
            "sensitivity analysis. (vi) The request's literal test, prohibiting the top five, was not run."
        ),
        "suggested_action": (
            "Report the sensitivity matrix next to Table 12. From cache/hR_layer*.npy (CPU only), recompute the geodesic nearest "
            "neighbours for k in {5, 10, 15, 20} x every layer in the gate bands (24-28 for the grid task, 21-27 for the shortest-path "
            "task) and report rank stability. Rephrase item 6 as 'consistent with geodesic proximity and with typicality; not separated "
            "on these events'. Expected impact: +0.25 to +0.5, and it prevents an overclaim from reaching the paper."
        ),
    },
    {
        "category": "rigor",
        "severity": "major",
        "description": (
            "The locus-diagnostic dead end is recorded but its cause is not, and the cause changes what to do next. "
            "gen_art_experiment_3/probes.json is 28 bytes ('{\"summary\": {}, \"cells\": {}}') with mtime 18:29. logs/states.out logs "
            "'T1: states (300, 8, 21, 4096) saved' at 18:34:34 and T2 at 18:34:50. The probe stage ran before its inputs existed. The "
            "states are on disk (states/T{1,2}_part_001-005.npz, 790 MB, read-position cosine >= 0.9997), so the measurement that "
            "decides whether every geometric analysis should move to generated tokens is a CPU-only re-run, not a missing experiment. "
            "The report calls it 'a technical failure, not a negative result' but gives the next iteration no route to it."
        ),
        "suggested_action": (
            "Add the timestamps and the state file locations to the dead-end entry. Make 'run the locus probe on the saved states "
            "(read position, generated tokens 8/16/32/64, fork and commitment positions vs shuffled labels; the preregistered 20-point "
            "rule)' the first step of the next iteration, before any new generation. Expected impact: resolves an undetermined "
            "preregistered diagnostic at near-zero cost."
        ),
    },
    {
        "category": "scope",
        "severity": "major",
        "description": (
            "Coverage against the original request is partial. Not addressed: (1) 'analyze with thought anchors, NLA, SAE'. None was "
            "run, j-lens is never mapped, and the logit lens appears only for the sharpening direction. (2) 'prohibit the top 5 in "
            "prompt, and see if the implemented count moves to the edge of those 5, or to the opposite side'. It was never run. The "
            "report says the succession 'could not reach' it, but a simultaneous five-name ban is a single prompt condition that "
            "needs no greedy succession. (3) 'analyze the internals, all the runs that produced BFS vs all runs that produced DFS vs "
            "dijkstra'. Only forced-prompt centroids were analysed, although natural BFS and DFS runs under the ban exist with saved "
            "states (exp3: 300 per task). (4) Question 1's '(always same seed)'. Common random numbers across temperature cells were "
            "not used, and same-seed determinism failed in vLLM (39/64 identical texts; failed on the grid task in the decommitment "
            "experiment). The report lists SAE, thought anchors and the top-five ban as open, but not (3), (4), NLA or j-lens."
        ),
        "suggested_action": (
            "List every unaddressed request item in the open-questions paragraph with a planned artifact. Run the simultaneous ban of 5 "
            "of the 6 grid algorithms, leaving each survivor in turn, and of 4 of the 5 shortest-path algorithms, or extend the catalogue toward "
            "the ten algorithms the request imagines. Probe the BFS-labelled versus DFS-labelled natural ban runs from the exp3 states. Use a "
            "public SAE where one exists for the model, or switch the mechanistic arm to a model with released SAEs. Run thought-anchor "
            "resampling on the thinking-on traces that exp6 already has (raise the 2,048-token cap so traces complete). Expected impact: "
            "+0.5 to +1 on coverage."
        ),
    },
    {
        "category": "novelty",
        "severity": "major",
        "description": (
            "No positive claim is compared with its nearest published neighbour, so none has earned novelty credit in this record. "
            "(a) 'Temperature is a phrasing knob' and the ideas-by-phrasings split sit next to Lee et al. 2026, 'Are We Measuring Strategy "
            "or Phrasing?' (arXiv 2606.29985, ICML 2026: diversity metrics capture surface variation, not approach), Peeperkorn et al. "
            "2024 [37], and NoveltyBench (arXiv 2504.05228). (b) Generate-then-select is the SimpleStrat mechanism: model-proposed strata, "
            "then an external random choice (Wong et al., NeurIPS 2025, arXiv 2410.09038), which also shows that temperature does not "
            "buy coverage. Its diversity is imposed by the experimenter's random draw, so it is closer to forced implementation than to "
            "model choice and should not sit in the BUY column as a knob on equal footing. (c) The free-form and listing-control "
            "predictors and the 'sharpened by post-training' reading neighbour Verbalized Sampling (Zhang et al. 2025, arXiv 2510.01171: "
            "mode collapse from typicality bias in preference data, recovered by verbalised distributions), Kirk et al. (ICLR 2024) and "
            "West et al. 2025 [35]. (d) Approach-organised internal states neighbour Goudarzi et al. 2026 (arXiv 2609.27041), which "
            "the final hypothesis review flagged and the report omits. (e) Bans re-collapsing onto SPFA/Bellman-Ford were already seen "
            "in the inspiration repository, and constraint violation under denial prompting in Lu et al. [23]."
        ),
        "suggested_action": (
            "For each positive claim add one line: the nearest neighbour, then what this run adds. Candidate additions: a five-draw "
            "replication with mechanism-level labels on an open model; within-model compliance driven by wording (0.09-0.72); the "
            "inversion of the mention twin against the sham-ban control; disguise counts (41/94, 58/100); and the read-position double "
            "dissociation for seeds. Where nothing is added (generate-then-select versus SimpleStrat, the temperature result versus "
            "Peeperkorn/Lee), say it is a replication on code. Expected impact: +0.25 to +0.5."
        ),
    },
    {
        "category": "evidence",
        "severity": "major",
        "description": (
            "The read-position evidence on seeds, which bears directly on the request's hypothesis 2 ('only context pushes you into "
            "a different subspace'), is half-reported. The report says that on the grid task the semantic seed's displacement pointed "
            "toward the implied centroid (cos 0.493) while the output did not follow. It omits the other half from the same file "
            "(analysis.json, forecast_check P5): on the shortest-path task the displacement did NOT point toward the Bellman-Ford "
            "centroid (cos -0.087), yet behaviour moved +66.30 pp toward it. The report's '67 points toward Bellman-Ford/SPFA' is the "
            "Dijkstra-share drop (-67.39); the implied-mode gain is 66.30. Also omitted: the word seed shifted the grid probe-decoded "
            "distribution toward A* by +0.88 with zero behavioural change. The shortest-path entropy seed's 90% CI upper bound is "
            "1.596, above the 1.5 bound, yet the report says it 'stayed within the paraphrase noise'. Together these are a double "
            "dissociation: displacement along the forced-prompt mode subspace predicts behavioural movement in neither direction."
        ),
        "suggested_action": (
            "Add both halves, the probe shifts and the entropy-seed interval to Section 1.10. Correct 67 -> 66.3 for the shift toward "
            "Bellman-Ford/SPFA. Revise established item 3 and the summary: read-position displacement in the mode subspace did not "
            "predict which algorithm the output moved to, on either task. Expected impact: +0.25. It is the run's most direct "
            "evidence on the user's subspace hypothesis."
        ),
    },
    {
        "category": "clarity",
        "severity": "major",
        "description": (
            "The reasoning behind the iteration is only partly recorded. The report gives the hypothesis-review scores (verified: "
            "5,6,6,7,7,7,7) but not what the final review objected to, or whether the screen answered it. Several objections are "
            "settled by this iteration's data and should be linked. (i) The review said S1's equivalence prediction was inconsistent "
            "with the negation-promotion mechanism: if processing a negation promotes an associate, bans of absent algorithms should "
            "still move mass toward a related algorithm. Two of nine sham bans did so (ban Floyd-Warshall -> Bellman-Ford/SPFA 23%; "
            "ban IDDFS -> DFS 12%). The report lists these shifts but files the sham control only as untestable, without saying "
            "what they mean for the mechanism. (ii) The review raised self-simulation (Binder et al., ICLR 2025) as a rival reason why the model's "
            "own stated alternative predicts its behaviour. That is exactly the free-form predictor's success. (iii) The review warned "
            "that point-cloud resampling would make geodesic stability uninformative. (iv) It flagged the missing Goudarzi et al. "
            "precedent and the unmapped j-lens."
        ),
        "suggested_action": (
            "Add a short subsection to Section 1.1 or 1.12, 'What the hypothesis review asked for and what the screen showed', with one "
            "line per objection and the evidence that now answers it. In particular, re-read the sham-ban vs baseline shifts as a "
            "(weak, 2 of 9 events) test of negation-triggered promotion, and state self-simulation as a live account of the free-form "
            "result. Expected impact: +0.25 on contribution."
        ),
    },
    {
        "category": "evidence",
        "severity": "minor",
        "description": (
            "Executed outputs missing from the record. Association experiment: 11 forced-implementation conditions (N=10 each, e.g. "
            "forced IDDFS 0/10 pass, forced Dial 0/10, forced bidirectional Dijkstra written as plain Dijkstra 10/10), although Table 6 "
            "is captioned 'Every condition'; and the sharpness-matched in-sample scores (association -1.386 vs frequency -1.475). "
            "Forking token: summaries/next_token.json (next-token entropies at fork candidates vs controls), confirmation-threshold "
            "sensitivity (grid candidate T1|ban|0 confirms at TVD 0.10 and 0.15 but not 0.20), and engine tests (greedy prefix identity "
            "0.14 at 10 tokens). Decommitment: the c=1 arms at layers 14 and 22 (N=10 each, pass 0). Geometry: Procrustes disparity "
            "0.18/0.25 and the pre-declared components that were dropped (external-model elicitation, LOCO decoder). Decoding: the "
            "all-label composition of the shortest-path enumeration arm (Bellman-Ford/SPFA 33 written, 8 correct)."
        ),
        "suggested_action": (
            "Add these as table rows or single sentences with their file names (data/samples.jsonl conditions 'forced:*'; "
            "summaries/next_token.json; forks.json 'confirmed_tvd0.10/0.15'; logs/test_engine.json; results/deviations.json). "
            "Expected impact: small, but it completes the record the paper step draws on."
        ),
    },
    {
        "category": "methodology",
        "severity": "minor",
        "description": (
            "Established item 8 ('Post-training sharpened an ordering the base model already had, rather than installing a new "
            "attractor') relabels a preregistered verdict, INSTALLED_BY_POST_TRAINING on the shortest-path task (MIXED on the grid "
            "task; MIXED on both at the planned N). Its support is thin: the base model under the chat template parses only 0.58/0.66 "
            "and yields 57/90 correct programs, the base arms are mostly judge-labelled (runtime vs AST kappa 0.20-0.50), and in "
            "plain completion the base model's shortest-path mode is Bellman-Ford/SPFA (16 of 25 correct), first rather than second."
        ),
        "suggested_action": (
            "Keep the preregistered verdict label beside the interpretation. Give the base-model counts with intervals. Say that the "
            "base model's ordering matches the instruct model's only under the chat template."
        ),
    },
    {
        "category": "rigor",
        "severity": "minor",
        "description": (
            "Bookkeeping and traceability gaps. GPU hours are missing for the forking token, decommitment and decoding experiments. "
            "Tables carry artifact markers but not the result "
            "file each was compiled from. The forking-token artifact has no README. Because 'compliant = correct' drives every grid "
            "number, the grid failure taxonomy belongs in the record. In the association experiment, 161 of 273 DFS programs fail "
            "(127 wrong answers, 81 of them on three_by_three_blocked and 35 on two_by_two_open; 31 timeouts; 3 runtime errors). My "
            "re-run shows this is not an I/O artefact: reading a None return as [] rescues only 2-3 programs per condition (ban BFS: "
            "DFS 38 -> 40)."
        ),
        "suggested_action": (
            "Fill GPU hours from each artifact's logs (exp3 logs/throughput.log, exp4 and exp6 logs). Name the source file under "
            "each table. Add a one-line failure taxonomy per grid condition, so readers know that low grid compliance reflects DFS "
            "implementation bugs rather than test bias."
        ),
    },
]

review = {
    "overall_assessment": overall,
    "strengths": strengths,
    "dimension_scores": dimension_scores,
    "critiques": critiques,
    "results_reported": True,
    "coverage": "partial",
    "blocking": True,
    "score": 4,
    "confidence": 4,
}

# Blocking is derived: true exactly when soundness <= 1 or results_reported is false.
soundness = next(d["score"] for d in dimension_scores if d["dimension"] == "soundness")
assert review["blocking"] == (soundness <= 1 or not review["results_reported"])
OUT.write_text(json.dumps(review, indent=2, ensure_ascii=False))
print("wrote", OUT, len(critiques), "critiques")
