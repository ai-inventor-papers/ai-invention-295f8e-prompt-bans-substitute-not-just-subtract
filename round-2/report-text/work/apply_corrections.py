"""Apply the marked iteration-2 corrections to the iteration-1 section of paper_draft.md.

Every target string must occur exactly once; the script aborts otherwise, so nothing is
replaced by accident. Each replacement keeps the original text or states what it read.
"""
from pathlib import Path

DRAFT = Path(__file__).resolve().parent.parent / "paper_draft.md"

EDITS = [
    (
        "All work so far uses Qwen3-8B [5] with thinking mode off unless stated, on the request's two path search tasks.",
        "All work so far uses Qwen3-8B [5] with thinking mode off unless stated, on the request's two path search tasks. *(Note added in "
        'iteration 2: iteration 2 adds Llama-3.1-8B-Instruct [22] and a bench of 13 further coding tasks; Sections 2.7 and 2.8.)*',
    ),
    (
        'a knob survives if it beats the next best knob by at least 0.5 effective algorithms.',
        'a knob survives if it beats the next best knob by at least 0.5 effective algorithms. *(Correction, iteration 2: as written in the '
        'strategy, the PREDICT rule scores only informative events, those with the banned mode present at 10% or more of the latent '
        'baseline, compliance of at least 50% and at least two survivors, and the BUY rule names a winner only if it leads on the pooled '
        'tasks and in direction on each task. This paragraph omitted both conditions, and Section 1.11 applied the rules without them. '
        'Sections 2.3.6 and 2.3.7 recompute both.)*',
    ),
    (
        '| Shortest path | succession step 2 (ban Dijkstra and Bellman-Ford/SPFA) | 100 | Bellman-Ford/SPFA 65, Dijkstra 35 | 0.85 | 1.960 '
        '|',
        '| Shortest path | succession step 2 (ban Dijkstra and Bellman-Ford/SPFA) | 100 | Bellman-Ford/SPFA 65, Dijkstra 35 | 0.85 | 1.960 '
        '|\n\n*(Added in iteration 2: the caption says every condition, but the experiment also ran eleven forced implementation conditions '
        'of 10 samples each, which this table omits; they are given in Table 50, Section 2.3.10. Forced IDDFS passed 0 of 10, forced Dial 0'
        ' of 10, and forced bidirectional Dijkstra was written as plain Dijkstra 10 of 10 times.)*',
    ),
    (
        'On the shortest path task the mass went to the second nearest centroid, Bellman-Ford/SPFA, and the nearest, Floyd-Warshall, '
        'received none.',
        'On the shortest path task the mass went to the second nearest centroid, Bellman-Ford/SPFA, and the nearest, Floyd-Warshall, '
        'received none. *(Correction, iteration 2: the claim that Bellman-Ford/SPFA is second nearest does not survive the sensitivity '
        'matrix of this experiment, which puts bidirectional Dijkstra (40.91) closer to Dijkstra than Bellman-Ford/SPFA (42.18) once the '
        'two flagged centroids are recomputed from correctly labelled forced samples. Under paraphrase level resampling Floyd-Warshall is '
        'nearest in every subsample, and Bellman-Ford/SPFA is second at layers 23 to 27 and third at layers 21 and 22; Section 2.3.2.)*',
    ),
    (
        'the geodesic kernel was the least bad forecaster on the primary events.',
        'the geodesic kernel was the least bad forecaster on the primary events. *(Correction, iteration 2: those neighbours, DFS and unit '
        'weight Dijkstra, are also second choices of the model, so the observation is consistent with geodesic proximity and with '
        "typicality and does not separate them; both events called primary here fail the forecast contest's compliance gate; Sections 2.3.2"
        ' and 2.3.7.)*',
    ),
    (
        "The strategy's locus diagnostic is therefore undetermined.",
        "The strategy's locus diagnostic is therefore undetermined. *(Correction, iteration 2: the cause is now recorded. `probes.json` (28"
        ' bytes, an empty summary) was written at 18:29:22, while the state log records the state phase starting at 18:31:55 and the grid '
        'and shortest path states saved at 18:34:34 and 18:34:50: the probe stage ran before its inputs existed. The states '
        '(`states/T{1,2}_part_001-005.npz`, about 790 MB, kept on the run volume) were intact, and the audit ran the probe on them in '
        'iteration 2; Section 2.3.1.)*',
    ),
    (
        'Table 26b shows why the band subtraction broke the model.',
        '*(Correction, iteration 2: Table 26 reports Hill numbers and flip rates but not what the correct programs were, which hides a '
        'complete algorithm switch. On the shortest path task band random direction 2 turned all 33 of its correct programs into '
        'Bellman-Ford/SPFA, against Dijkstra 100 of 100 in the control, and band random direction 1 left no correct program; the read '
        'position only random edit gave Dijkstra 90, Bellman-Ford/SPFA 9 and other 1; layer-18 sharpening at c = 0.5 gave Dijkstra 48 and '
        'Bellman-Ford/SPFA 1; read position sharpening without the cutoff gave Dijkstra 3 and Bellman-Ford/SPFA 1. On the grid task every '
        'correct program in every arm was BFS (41 under band random direction 1, 68 under band random direction 2, 100 under the read '
        'position random edit). Source: audit `tables/perturbation_table.csv`; Section 2.3.5.)*\n\nTable 26b shows why the band subtraction '
        'broke the model.',
    ),
    (
        'it did not install a new attractor.',
        'it did not install a new attractor. *(Correction, iteration 2: the preregistered verdicts stay as recorded above, '
        'INSTALLED_BY_POST_TRAINING on the shortest path task and MIXED on the grid task, and MIXED on both at the planned sample size; the'
        " base ordering matches the instruct ordering only under the chat template, and in plain completion the base model's shortest path "
        'mode is Bellman-Ford/SPFA, first rather than second.)*',
    ),
    (
        'The semantic seed moved the shortest path task by 67 points toward Bellman-Ford/SPFA (61 of 92 correct programs; permutation p < '
        '0.001)',
        'The semantic seed moved the shortest path task by 66.3 points toward Bellman-Ford/SPFA among correct programs (61 of 92 correct '
        'programs, while the Dijkstra share fell by 67.39 points; permutation p < 0.001; corrected in iteration 2 from 67 points, which is '
        'the fall in the Dijkstra share)',
    ),
    (
        'The entropy seed stayed within the paraphrase noise (0.734 and 1.165).',
        'The entropy seed stayed within the paraphrase noise (0.734 and 1.165). *(Correction, iteration 2: on the shortest path task its '
        '90% interval reaches 1.596, above the 1.5 equivalence bound, so equivalence with paraphrase noise was not shown there.)*',
    ),
    (
        'while the output did not follow.',
        'while the output did not follow. *(Added in iteration 2: the other half of the same result was omitted. On the shortest path task '
        "the semantic seed's displacement did not point toward the Bellman-Ford/SPFA centroid (cosine -0.087), yet the output moved 66.3 "
        "points toward it, and the fixed word seed moved the grid probe's decoded distribution 0.88 toward A* with no behavioural change. "
        'Displacement along the mode subspace predicted behavioural movement in neither direction; Section 2.3.8.)*',
    ),
    (
        'the same semantic seed moved the shortest path task by 67 points and the grid task by 2.',
        'the same semantic seed moved the shortest path task by 66.3 points and the grid task by 2.2 (among correct programs; corrected in '
        'iteration 2 from 67 and 2).',
    ),
    (
        'Where the ban had compliant samples, they landed on the same substitute every time: DFS on the grid task (with a few unit weight '
        'Dijkstra programs) and Bellman-Ford/SPFA on the shortest path task (Table 34).',
        'Where the ban had compliant samples, they landed on Bellman-Ford/SPFA on the shortest path task in all five draws (272 of 272 '
        'compliant programs), and on DFS on the grid task in four of five draws; in the geometry draw, sampled with HF `generate` and with '
        'the highest banned share (0.62), the 18 compliant programs split into DFS 10 and unit weight Dijkstra 8, with no clear mode (Table'
        ' 34). *(Corrected in iteration 2; this sentence previously said that the compliant samples landed on the same substitute every '
        'time, DFS on the grid task with a few unit weight Dijkstra programs, which Tables 13 and 34 contradict. Section 2.3.3 gives the '
        'per draw counts.)*',
    ),
    (
        '| Instruction tuning (vLLM) | BFS 62, DFS 36, unit weight Dijkstra 2 | 0.62 | 13 (DFS 12, unit weight Dijkstra 1) | Dijkstra 54, '
        'Bellman-Ford/SPFA 46 | 0.54 | 46 (Bellman-Ford/SPFA 46) |',
        '| Instruction tuning (vLLM) | BFS 62, DFS 36, unit weight Dijkstra 2 | 0.62 | 13 (DFS 12, unit weight Dijkstra 1) | Dijkstra 54, '
        'Bellman-Ford/SPFA 46 | 0.54 | 46 (Bellman-Ford/SPFA 46) |\n| Pooled, five draws (row added in iteration 2) | n/a | 0.41 | 128 (DFS '
        '116, unit weight Dijkstra 12); DFS share 0.906, Wilson [0.843, 0.946] | n/a | 0.42 | 272 (Bellman-Ford/SPFA 272); share 1.0, '
        'Wilson [0.986, 1.000] |',
    ),
    (
        'so the rule cannot name a survivor.',
        'so the rule cannot name a survivor. *(Correction, iteration 2: the rule also gates events on compliance of at least 50%. Under '
        'that gate the geometry, instruction tuning and decommitment shortest path events in Table 36 are excluded, the base model, '
        'decommitted and geodesic forecasts were scored only on excluded events, and the ranking that follows rests largely on them. On '
        'gated events no family can advance; Section 2.3.7.)*',
    ),
    (
        "On the grid task no knob that kept 80% of the pass rate produced a second algorithm among compliant programs: the cumulative ban's"
        ' gain came from programs that still used BFS, and the novelty instruction raised Hill_cc to 1.27.',
        'On the grid task the cumulative ban of BFS and DFS kept 88% of its reference pass rate in the decommitment draw and produced 16 '
        'compliant programs over two algorithms (unit weight Dijkstra 13, A* 3), but it does not replicate: the geometry draw (pass 0.96 '
        'against 0.99) put all 18 of its compliant programs on unit weight Dijkstra, and the association draw (pass 0.53 against 0.933) '
        'left 5 compliant programs; the novelty instruction raised Hill_cc to 1.27. *(Corrected in iteration 2; this sentence previously '
        'said that no knob keeping 80% of the pass rate produced a second algorithm among compliant programs and that the gain of the '
        'cumulative ban came from programs that still used BFS, which the decommitment row of Table 37 contradicts. Section 2.3.4.)*',
    ),
    (
        "By the rule's 0.5 margin the prompt ban and the semantic seed tie, so both would advance.",
        "By the rule's 0.5 margin the prompt ban and the semantic seed tie, so both would advance. *(Correction, iteration 2: the BUY rule "
        'names a winner only on the pooled tasks and in direction on each task, and this comparison used the shortest path task alone, with'
        ' Hill numbers from different statistics. Recomputed with one statistic, rarefied Hill-1 over compliant programs, no knob advances '
        'on either task, the prompt ban scores 1.0 on the shortest path task, and the positive target of a second correct algorithm at '
        'under 20 pass points is met on neither task; Section 2.3.6.)*',
    ),
    (
        'Context with meaning moves the state three to four times the paraphrase noise and can move the output, by 67 points on the '
        'shortest path task and by 2 points on the grid task.',
        'Context with meaning moves the state three to four times the paraphrase noise and can move the output, by 66.3 points on the '
        'shortest path task and by 2.2 points on the grid task (among correct programs). *(Corrected in iteration 2; the item previously '
        'gave 67 and 2 points, 67 being the fall in the Dijkstra share. It also omitted that read position displacement did not predict '
        'which algorithm the output moved to on either task: the grid semantic seed pointed at its implied algorithm and behaviour barely '
        'moved, the shortest path seed did not point at Bellman-Ford/SPFA and behaviour moved two thirds of the way; and the shortest path '
        "entropy seed's interval reaches 1.596, above the equivalence bound. Section 2.3.8.)*",
    ),
    (
        '4. When a prompt ban is obeyed, the compliant programs land on one substitute, and that substitute replicated in five independent '
        'draws: DFS for BFS, Bellman-Ford/SPFA for Dijkstra. Bans collapse the output again; they do not spread it.',
        '4. When a prompt ban is obeyed, the compliant programs land mostly on one substitute. On the shortest path task it was '
        'Bellman-Ford/SPFA in five of five draws (272 of 272 compliant programs); on the grid task DFS was the realised mode in four of '
        'five draws (116 of 128 pooled, 0.906, Wilson [0.843, 0.946]), and the HF engine geometry draw, with the highest banned share '
        '(0.62), had no clear mode (DFS 10, unit weight Dijkstra 8). A single ban collapses the output again; a second step grid ban can '
        'spread compliant output over unit weight Dijkstra and A* (decommitment draw: 13 and 3) or put all of it on unit weight Dijkstra '
        '(geometry draw: 18). *(Corrected in iteration 2; the item previously said that the substitute replicated in five independent draws'
        ' and that bans collapse the output again without spreading it, which the geometry draw and the second step bans contradict. '
        'Section 2.3.3.)*',
    ),
    (
        'The preregistered ranked association map did not identify it on the grid task and gave different answers under two elicitation '
        'wordings.',
        'The preregistered ranked association map did not identify it on the grid task and gave different answers under two elicitation '
        'wordings. *(Note added in iteration 2: on the shortest path task random activation directions and every other perturbation that '
        'moved the model off Dijkstra also landed on Bellman-Ford/SPFA (Section 2.3.5), so there the second preference of the model cannot '
        'be told apart from wherever any perturbation lands.)*',
    ),
    (
        "On the grid task the mass displaced by bans moved to BFS's geodesic neighbours and never to the far side.",
        "On the grid task the mass displaced by bans moved to BFS's geodesic neighbours and never to the far side, which is consistent with"
        ' geodesic proximity and with typicality, since those neighbours are also second choices of the model; the two are not separated on'
        ' these events. *(Corrected in iteration 2: the geodesic order is unstable at layer 24 under paraphrase resampling, and on the '
        'shortest path task Floyd-Warshall, not the realised Bellman-Ford/SPFA, is the nearest survivor in every subsample. Section '
        '2.3.2.)*',
    ),
    (
        '8. Post-training sharpened an ordering the base model already had, rather than installing a new attractor; the chat format '
        'sharpens it further on the shortest path task.',
        '8. Post training sharpened an ordering the base model already had, rather than installing a new attractor; the chat format '
        'sharpens it further on the shortest path task. *(Correction, iteration 2: this item replaced the preregistered verdicts with an '
        'interpretation. The verdicts are INSTALLED_BY_POST_TRAINING on the shortest path task and MIXED on the grid task under the '
        'correctness conditioned Hill number (INSTALLED_BY_POST_TRAINING on both under the Hill number over all programs), and MIXED on '
        'both at the planned sample size. The base ordering matches the instruct ordering only under the chat template, where the base '
        'model parsed 0.58 and 0.66 of samples and wrote 57 and 90 correct programs, labelled with runtime against AST kappa of 0.20 to '
        '0.50 (Table 24b); in plain completion its shortest path mode is Bellman-Ford/SPFA, 16 of 25 correct programs.)*',
    ),
    (
        'this is a technical failure, not a negative result, and the measurement is still missing.',
        'this is a technical failure, not a negative result, and the measurement is still missing. *(Correction, iteration 2: the probe '
        'stage ran before the states were written (Section 1.7); the audit ran it in iteration 2 and found no decision locus among the '
        'saved positions, Section 2.3.1.)*',
    ),
    (
        'the other experiments did not record GPU hours.',
        "the other experiments did not record GPU hours. *(Correction, iteration 2: from the union of each experiment's GPU phase log "
        'spans, an upper bound that includes waits, geometry 2.92, forking token 1.55, decommitment 3.23, instruction tuning 2.47 and '
        'decoding 3.31 GPU hours; Section 2.3.10. The answers this screen gives to the objections of the hypothesis review are recorded in '
        'Section 2.1.)*',
    ),
]


def main() -> None:
    text = DRAFT.read_text(encoding="utf-8")
    for old, new in EDITS:
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"expected exactly one occurrence, found {n}: {old[:90]!r}")
        text = text.replace(old, new)
    DRAFT.write_text(text, encoding="utf-8")
    print(f"applied {len(EDITS)} corrections")


if __name__ == "__main__":
    main()
