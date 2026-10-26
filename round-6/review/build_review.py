#!/usr/bin/env python3
"""Builds the structured review of the iteration-6 research record and writes it to
.terminal_claude_agent_struct_out.json next to this script. All numbers quoted below were
recomputed from the artifacts' raw rows or result files (see recompute/*.py and *.out.txt)."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

overall = (
    "Iteration 6 answers the previous blocking review almost item for item, and the record is traceable. "
    "I recomputed the headline numbers from the artifacts' own rows: "
    "(i) engine control (art_lpQalcAXMGr1, data/samples.jsonl, with an independent implementation of the two-stage escape rule): "
    "escape fraction at alpha 2 on connected components W8A8 0.725 / W16A8 0.600 / bf16 0.650 (W8A16 27 of 40 confirmed on top-ups of 22-26 rows, "
    "so 'incomplete' is right); shortest path 0.200 / 0.125 / 0.150 / 0.150; screen passes 30/28/27/27 and 15/8/8/9; per-slot flips W8A8 vs bf16 30:10 "
    "(p 0.0022), W16A8 vs bf16 9:23 (p 0.020); per-sample plan noise 30/27/22/25 and 22/19/18/22 of 50, block-12 displacement 13.75. "
    "(ii) Stage A (art_rMlbrjVB1c__ data/labels.jsonl): every cell count of Tables 244-250 matches. "
    "(iii) movability (art_aRTQM6CQ0Dre tables/movability_units.csv): Spearman 0.146, Bonett-Wright [-0.44, 0.65], permutation p 0.32, 0.035 with count inversions' "
    "correct-only beta, runtime merit 0.713. (iv) Landing contest, Gemma fork/readout/clamp/geometry and NLA readout/local-control values match their result JSONs. "
    "The not-run DAS/plan-coordinate experiment is correctly named as planned and not run (6.1, 6.8, 6.10, closing). The previous must-fix items are addressed with "
    "marked in-place corrections: the decisive engine control ran and shows the iteration-4 escapes are a property of Qwen3-8B; the landing tally is per set (17 of 21) "
    "with the twin-minority rival (6 vs 6) and moved to descriptive; movability has its interval, power and pooled rivals; the missing outputs are added; the site "
    "comparison and top-five push were rerun in bf16; the novelty zero was re-adjudicated by two new judge families. "
    "The remaining problems are new and concern iteration 6's own internal claims, several of which say more than their artifacts: "
    "(1) Stage A's outcome is described as the share of CORRECT programs implementing Y, but the preregistered and computed metric counts all attempts; correct-only "
    "transfers are lower (shortest path blocks 0-35: 21/30, not 24/30; blocks 12-23: 11/30, not 18/30; grid blocks 0-35: 3/30 correct DFS against a quoted 0.47). "
    "(2) 6.4.2 says the post-hoc site model 'survives', but the post-hoc alpha<=4 model fails the rule's condition-span clause on both tasks, the artifact's own verdict "
    "is 'WITHDRAWN ... the site of the choice is open', and on connected components the early blocks beat the plan site. "
    "(3) The Gemma 'one direction' DAS claim lacks the random-initialisation and label-shuffled controls that the run's own positioning audit makes a condition for "
    "that wording, the interchange leaves 0/50 programs passing, and the SAE-beyond-text readout margin did not reproduce under the artifact's own second estimator. "
    "(4) The closing synthesises 'where the choice is held' across three models from three different quantities and asserts that the read position is inert in Gemma, "
    "where the read position was never read or edited. "
    "Coverage of the request stays partial: the representation-level account in the main model was lost with the DAS experiment, and the iteration-6 "
    "activation-space geometry figures have no figure markers although the request demands actual activation-space plots. "
    "Research quality: technically careful, exceptionally reproducible and honest about nulls; the new internal positives (engine robustness, a ban/instruction carried "
    "by task-spec states, a one-token fork in Gemma, an NLA null) are modest and partly overstated, and the central internal question remains open. Score 5."
)

strengths = [
    "The previous blocking review is answered item by item (Table 224) with in-place, marked corrections (Table 226: 36 corrections, 78 MATCH / 1 CORRECTED / 18 NEW / 2 CARRIED), and the earlier sections keep their chronology.",
    "The engine control is the right decisive experiment and is well executed: four numerics built from one bf16 snapshot, iteration-4 directions, slots and uniforms held fixed, the W8A8 engine reproducing iteration-4 rows byte for byte (400/400, 40/40), each engine scored against its own twin. Every headline cell recomputes exactly from data/samples.jsonl.",
    "Traceability is strong: each table names its artifact and file, and my independent recomputations of the escape fractions, per-slot flips, plan-noise counts, Stage A cell counts and the movability Spearman/Bonett-Wright interval all matched.",
    "The record now states what survives the engine change (Table 229 with a status-after-6.3 column; closing list of bf16-robust internal results) and tags iteration-4/5 verdicts as conditional on their design.",
    "Stage A has good controls (matched-norm random exchange, placebo twin, read-position exchange, condition-span splice) and an informative extension: forced positive instructions are carried by the same task-spec states (shortest path 30/30, connected components 28/30).",
    "Dead ends and nulls are kept with their evidence (activation-rounding account, preregistered Stage A rule, feature claim, verbal readout, state-noise vs temperature), and the lost DAS experiment is recorded as planned and not run, never as a null.",
    "The Gemma natural BFS/DFS split is a clean within-prompt contrast the request asked for, and the NLA exploratory local control turns a null readout into an interpretable one (the algorithm is verbalisable at its name token and fades within a sentence).",
    "The novelty question is handled conservatively: the 14 disputed programs were stress-tested and re-adjudicated blind by two new judge families with controls, and the closing scopes the novelty null to single-sample generation without search.",
]

dimension_scores = [
    {
        "dimension": "soundness",
        "score": 3,
        "justification": (
            "Headline numbers recompute exactly and the main conclusions (escapes are a model property; ban/instruction effects are carried by task-spec states on "
            "prompt-route tasks; Gemma's choice forks at one generated token; the NLA does not verbalise a pre-code plan; no novel algorithm) follow from the data. "
            "Several iteration-6 sentences overreach: the Stage A metric is misdescribed (attempts reported as correct programs), the post-hoc site model is said to "
            "'survive' although it fails the condition-span clause, the Gemma DAS 'one direction' claim lacks its own required controls, and the read position is "
            "called inert in Gemma where it was not tested. None reverses a headline, so not 1, but they are more than polish."
        ),
        "improvements": [
            "Restate the Stage A outcome as share of attempts (as preregistered) and add correct-only Y columns; quote both in 6.10 item 2 and the closing.",
            "Replace 'its post-hoc form survives' with the read-position-only result and the artifact's verdict 'the site of the choice is open'.",
            "Qualify the Gemma DAS claim (no random-init/label-shuffled control, 0/50 valid under interchange) and report the second-estimator readout result.",
            "Rewrite the three-model synthesis per quantity and drop the untested Gemma read-position claim.",
        ],
    },
    {
        "dimension": "presentation",
        "score": 3,
        "justification": (
            "A reader can follow the record in order: each iteration opens with the review it answers, the hypothesis update and the strategy, and each table is "
            "introduced by what it settles. The length is very large, and in iteration 6 a few synthesis sentences (6.9, closing) merge quantities that the "
            "sections keep apart."
        ),
        "improvements": [
            "Keep each cross-model statement tied to the quantity measured in that model (carried instruction vs natural fork vs verbal readout).",
            "Wrap the iteration-6 insertion in Section 4.9 as a marked correction like the others.",
        ],
    },
    {
        "dimension": "contribution",
        "score": 3,
        "justification": (
            "The record preserves almost everything the run did, including nulls and the lost experiment, with tables in full. A few executed outputs are missing: "
            "the iteration-6 activation-space geometry figures (no markers), the exchange experiment's ST x Stage A concordance, the Gemma sampler-calibration check "
            "(U6) and dropped sub-analyses (D12), the NLA clustered interval, the T2 screen-level engine verdict, and correct-only counts for the engine control."
        ),
        "improvements": [
            "Add figure markers for exp30 F5_top5_geometry, exp31 geometry_raw/sae_L17/L22 and exp32 F6_geometry/F8_mds_centroids.",
            "Add a short 'executed but not yet reported' list: ST x Stage A concordance, Gemma U6 and D12, NLA N6 cluster interval, T2 screen-level verdict, 3 unjudged correct 'other' programs in the engine control.",
        ],
    },
]

critiques = [
    {
        "category": "evidence",
        "severity": "major",
        "description": (
            "Stage A's outcome is misdescribed. Section 6.4.1 says 'The outcome is the share of correct programs implementing the substitute Y', but the preregistered metric "
            "(art_rMlbrjVB1c__ predictions/commit0.json: transfer = share(label == Y | cell) - share(label == Y | TWIN), 'all samples') and every Y share/transfer in Tables 244-250 "
            "count all attempted programs; correctness enters only through the pass-ratio clause. Recomputed from data/labels.jsonl: shortest path exchange at blocks 0-35 is 24/30 "
            "Bellman-Ford/SPFA attempts but 21/30 correct programs (0.70, not 0.80); blocks 12-23 is 18/30 attempts but 11/30 correct (0.37, not 0.60); kth smallest blocks 0-35 is "
            "17 quickselect attempts, 16 correct; on the grid task the exchange at blocks 0-35 'transfers 0.47 toward DFS' with only 3/30 correct DFS programs and the condition-span "
            "splice '0.33' with 7/30. The 0.80 and 0.57 figures are carried into 6.9, 6.10 item 2 and the closing as if they were correct-program transfers; the paper step will "
            "publish a wrong metric definition."
        ),
        "suggested_action": (
            "Rewrite the definition to match commit0 ('share of all attempted programs labelled Y; invalid rows count as not-Y; correctness gated by pass ratio >= 0.8'), add a "
            "correct-Y column to Tables 244-250 (e.g. T2 blocks 0-35 21/30, blocks 12-23 11/30; T03 blocks 0-35 16/30; grid blocks 0-35 3/30, condition splice 7/30; forced "
            "Bellman-Ford exchange 30/30), and quote both numbers wherever 0.80/0.57/0.47/0.33 appear. Expected impact: +0.25 soundness."
        ),
    },
    {
        "category": "rigor",
        "severity": "major",
        "description": (
            "The post-hoc site result is overstated. 6.4.2 ends 'withdrawn as preregistered, and its post-hoc form survives in bf16', and the closing lists 'the post-hoc "
            "ordering of noise sites' among bf16-robust internal results. The artifact's committed verdict (art_rMlbrjVB1c__ results/site_grid.json RULE) is 'WITHDRAWN as "
            "FP8-specific: the site of the choice is open', and the rule required BOTH the read-position and the condition-span coefficient below the task-spec site with "
            "intervals excluding 0. In the post-hoc alpha<=4 model only the read-position clause holds; the condition-span clause fails on both tasks (S2 -1.70, bootstrap "
            "[-3.96, 0.42] on kth smallest; -0.56, [-4.93, 2.91] on connected components). On connected components the early blocks beat the plan site (S4 +2.51 [1.39, 3.80]; "
            "paired flips 4:18; MH odds ratio plan site vs read position 0.82 [0.31, 2.18]), the artifact's ST x Stage A concordance check is false and unreported (noise acts "
            "at blocks 0-11, the exchange at 12-23), and the exchange at blocks 0-11 and 24-35 alone already moves 0.87 and 0.63 of attempts off union find. The rule's own label "
            "'FP8-specific' is never discussed although the engine control contradicts it."
        ),
        "suggested_action": (
            "Replace 'its post-hoc form survives' with: 'post hoc (alpha<=4) the read position is below the task-spec site on both tasks; the condition-span clause fails post "
            "hoc as well, so the site of the choice remains open, as the artifact concludes'. Report the rule's 'FP8-specific' label and say why Section 6.3 makes it "
            "inapplicable. Add the ST x Stage A concordance (kth smallest concordant at blocks 12-23; connected components discordant) and the depth-redundant removal on "
            "connected components. Expected impact: +0.25."
        ),
    },
    {
        "category": "rigor",
        "severity": "major",
        "description": (
            "Two Gemma claims outrun their controls. (a) 'The plan is close to one direction at one position' (6.5) and 'DAS finds it in essentially one direction' (closing) "
            "rest on a rank-1 DAS trained with forced-BFS prompts as sources. The shuffled-source control is uninformative by construction (deviation D9: it still imports a "
            "BFS state and moves y by 10.1 nats); no DAS was fitted on a randomly initialised model or with shuffled targets, which the run's own positioning audit "
            "(art_OUuQUYQn5voE permitted wording; Table 277 rows 14-15) makes a precondition for a DAS localization claim; and in generation the rank-4 interchange gives "
            "50/50 BFS with 0/50 passing, an off-distribution intervention of the kind [122] warns about. Shifting a log-odds whose natural SD is 0.67 nats by 8.8 nats is not "
            "evidence of one-dimensionality. (b) The preregistered SAE readout margin (Lasso R2 0.66 vs text 0.18) did not reproduce under the artifact's own second "
            "estimator: standardized ridge on the same layer-29 SAE codes gives 0.15 against 0.086 for a template+noun-norm control (delta 0.064, below the 0.10 bar; "
            "results/rederive_headlines.json H1). The report quotes only the unstandardized '<=0.09' and keeps the Lasso result as 6.10 Established item 3. (c) 'Every edit "
            "at the fork lowered the pass rate' is contradicted by Table 262's own SAE top-5 row (pass 0.84, equal to the twin)."
        ),
        "suggested_action": (
            "Restate (a) as 'a rank-1 DAS subspace fitted on forced-BFS sources moves the held-out fork log-odds by 8.8 nats (random subspaces about 0); without "
            "random-initialisation and target-shuffled controls, and with 0/50 valid programs under interchange, this does not show that the choice is one-dimensional'. "
            "If budget allows, fit DAS on a randomly initialised Gemma and with shuffled targets, and sweep the interchange scale to find a dose that keeps programs valid. "
            "Report (b) beside the Lasso result in 6.5 and 6.10 item 3, and fix (c). Expected impact: +0.25."
        ),
    },
    {
        "category": "rigor",
        "severity": "major",
        "description": (
            "The closing and 6.9 merge three different quantities into one 'location of the choice' and assert an untested result. 'Where the choice is held has now been "
            "measured in three models' compares where an external instruction's effect is carried in Qwen3-8B (full-state exchange from another prompt; Qwen3-8B has no "
            "natural split on these tasks), where a natural within-prompt choice forks during generation in Gemma, and what a verbalizer says in Qwen2.5. 'In all three "
            "models the read position is inert as a carrier ... Gemma's readout there is no better than the text' is wrong for Gemma: its 'SPEC' site is the mean over "
            "task-spec positions (art_zNyBP6zieI5u src/cfg.py: from 'Task:' to the last user token), not the read position, which was never read or edited. The Gemma "
            "result is that task-spec edits and readouts do not reach the choice, the opposite of Qwen3-8B's task-spec states carrying a ban."
        ),
        "suggested_action": (
            "Rewrite the synthesis per model and per quantity: Qwen3-8B - task-spec states carry an external ban/instruction on prompt-route tasks; Gemma - the natural "
            "choice forks at a generated token and task-spec edits/readouts do not reach it; Qwen2.5 - no verbalisable plan at pre-code positions. Drop Gemma from the "
            "read-position sentence or test the read position in Gemma. Expected impact: +0.25."
        ),
    },
    {
        "category": "scope",
        "severity": "major",
        "description": (
            "Coverage of the original request is still partial on its central question, how creativity manifests inside the model. In the main model the record shows where "
            "a ban or instruction is carried, not how Qwen3-8B represents its own algorithm choice: the DAS/plan-subspace/causal-manifold experiment "
            "(experiment_iter6_dir4) was lost at planning (correctly recorded as not run). The request also demands 'actual geometry plots, actual activation space'. "
            "Iteration 6 produced them - art_rMlbrjVB1c__ figures/F5_top5_geometry, art_zNyBP6zieI5u figures/geometry_raw_L17/L22 and geometry_sae_L17/L22 (centroids with "
            "implemented counts and the top-five prompt states), art_dbUtqBjT0tPf figures/F6_geometry and F8_mds_centroids - but none has a [FIGURE] marker; 6.4.4, 6.5 "
            "(Table 266) and 6.6 describe them only in prose or tables, so the paper step will not know they exist."
        ),
        "suggested_action": (
            "Next iteration, run the lost experiment: DAS at the task-spec positions of shortest path and kth smallest with the Stage A full-state exchange as ceiling, "
            "held-out templates, declared map class and random-init/shuffled-label controls, then project iteration 4's 40 directions (now known to escape in bf16 at the "
            "absolute unit) onto the fitted subspace and draw the algorithm manifold and the top-five prohibition in it. Now: add [FIGURE] markers for the five geometry "
            "figures listed, each captioned with its position (task-spec mean vs read position) and any label-dependence caveat. Expected impact: +0.5 on coverage and contribution."
        ),
    },
    {
        "category": "methodology",
        "severity": "minor",
        "description": (
            "The bf16 top-five plan push (6.4.4) was tested only at doses far beyond the forced-prompt manifold, so 'the activation version of the prohibition breaks "
            "programs before it moves the algorithm' (6.9) is confounded with dose. In art_rMlbrjVB1c__ results/top5_push.json the ten centroids span about 0.24 on PC1 "
            "(-0.098 to 0.144) while the alpha-1 push already moves the state from about +0.09 to -0.44, over twice that spread; the pass rate falls 0.92 to 0.67 at alpha 1. "
            "Iteration 4's targeted push on connected components crossed to DFS at 0.15 ban units (half the centroid distance), so an in-manifold dose is the informative one."
        ),
        "suggested_action": (
            "Parameterise the top-five push by the fraction s of the banned-to-survivor centroid distance (s = 0.25, 0.5, 1) as the targeted pushes were, and until then "
            "restate 6.9 as 'at doses of 1 to 8 ban units, which overshoot the forced-prompt manifold, the push breaks programs before it moves the algorithm'."
        ),
    },
    {
        "category": "rigor",
        "severity": "minor",
        "description": (
            "The engine-control plan-noise comparison (Table 238) is given only as valid attempts off the default, while the iteration-5 null it explains and the audit's "
            "own reconciliation (Table 228) use correct programs. On correct programs (art_lpQalcAXMGr1 data/samples.jsonl) shortest path alpha 2 is 14 of 37 correct under "
            "W8A8 against 9 of 31 under bf16 (alpha 1: 9/43 vs 5/43), so 'reproduces' holds against iteration 5's 2/47 but the 22 = 22 equality is partly a definitional "
            "artefact. The T2 screen-level verdict in results/verdict.json is MIXED (W8A8 passes the screen on 15 of 40 directions vs 8-9 for the others) and is not mentioned."
        ),
        "suggested_action": "Add a correct-only column to Table 238 and report the T2 screen-level verdict beside the literal one.",
    },
    {
        "category": "rigor",
        "severity": "minor",
        "description": (
            "The NLA per-sample comparison is pseudoreplicated. 'An outside reader ... predicts the realised algorithm better, per sample (0.25 against 0.07; exact McNemar "
            "20:88, p 2e-11)' treats 364 units drawn from 120 samples as independent; the artifact's own cluster bootstrap (art_dbUtqBjT0tPf results/readout.json N6, "
            "5 clusters) gives an effect interval of [-0.35, 0.02], which includes 0."
        ),
        "suggested_action": "Report the clustered interval beside the McNemar p, or test at the sample level (one unit per sample).",
    },
    {
        "category": "evidence",
        "severity": "minor",
        "description": (
            "Executed checks and drops are missing from the record. Gemma: the sampler-calibration unit test U6 failed - continuations from the empty prefix give BFS 0.38 "
            "(n 192) against the natural 0.305 [0.245, 0.372] (results/fork.json) - although the fork analysis rests on resampled continuations; deviation D12 (T04/R6 forks "
            "and cross-prompt readouts, U4/U5 not run) is not mentioned. Engine control: 3 correct programs labelled other (one reused, one W16A8, one bf16) were classed only "
            "by nearest-known-solution Jaccard and never judged. Exchange experiment: the ST x Stage A concordance result."
        ),
        "suggested_action": "Add a short 'executed but not yet reported' paragraph to 6.9 listing these with their numbers and files.",
    },
    {
        "category": "clarity",
        "severity": "minor",
        "description": (
            "Section 4.9 (iteration 4) carries an iteration-6 insertion that is not wrapped as a marked correction, and its claim that 'every correct program outside the "
            "catalogue that the run produced has been read by two blind judges and the executor' is contradicted by Table 278 (engine control: 'not judged') and by "
            "iteration 3's note that about 9,000 programs of the forking-token experiment were not audited."
        ),
        "suggested_action": "Wrap the text as '(Correction, iteration 6: ...)' and restrict the claim to the pools actually audited.",
    },
    {
        "category": "novelty",
        "severity": "minor",
        "description": (
            "The Gemma one-token fork is a positive result without a stated nearest-neighbour comparison. Forking-token analyses ([30], [31]) already locate outcome-deciding "
            "single tokens, and latent planning in Gemma/Qwen models is reported by Hanna et al. [123] and Nainani et al. (Table 277 rows 11, 33, 56), but the record does not "
            "say what the fork adds beyond them (an algorithm-level fork in code at a non-identifying token about 138 tokens before identifying code, readable across prompts)."
        ),
        "suggested_action": "Add a positioning row for the fork claim stating the nearest neighbour and what this run adds.",
    },
    {
        "category": "methodology",
        "severity": "minor",
        "description": (
            "Two iteration-5 verdicts that bear on 'can we influence it' - plan sampler comparison DISCONFIRMED and the movability half - are now known to rest on a design "
            "(ban-free unit, its direction seeds) in which plan noise is nearly inert, while at the absolute unit plan noise moves connected components 25 of 50 in bf16. "
            "The record tags them as conditional but leaves the deciding comparison (unit profile vs seeds) untested."
        ),
        "suggested_action": (
            "Run a 2 x 2 (ban-free vs absolute unit x iteration-4 vs iteration-5 direction seeds) on connected components and shortest path, then repeat the plan-sampler "
            "price comparison at whichever design moves the model, about 1 GPU hour."
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
    "blocking": False,
    "score": 5,
    "confidence": 4,
}

# Blocking is derived: soundness <= 1 or results not reported.
sound = next(d["score"] for d in dimension_scores if d["dimension"] == "soundness")
assert review["blocking"] == (sound <= 1 or not review["results_reported"])

out = HERE / ".terminal_claude_agent_struct_out.json"
out.write_text(json.dumps(review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"wrote {out} ({out.stat().st_size} bytes), {len(critiques)} critiques")
