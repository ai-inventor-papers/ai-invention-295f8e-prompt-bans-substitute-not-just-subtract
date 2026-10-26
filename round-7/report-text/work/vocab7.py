"""Terminology pass over the iteration-7 section, the closing and the figure specs.

The report step's vocabulary lint flags every hyphenated compound that is neither in domain_terms.json nor
defined in its own sentence. In the text written this iteration each one is renamed here: a standard term takes
its field spelling (post hoc, log odds), an ordinary compound modifier becomes plain words (fork at one token),
and a name the run coined is written out descriptively (share off the default) or renamed and defined at first
use in the prose (relative unit for the ban-free unit, second choice for the runner-up).

apply(text) leaves [ARTIFACT:...] and [FIGURE:...] markers, `code spans` and ⟦guarded⟧ text untouched; the
guards mark earlier names quoted inside a definition and are dropped from the output. Numbers are never edited.
"""
import re

PROTECT = re.compile(r"\[(?:ARTIFACT|FIGURE):[^\]]+\]|`[^`\n]*`|⟦[^⟧]*⟧")

# Ordered: whole phrases first, then the generic rename of each compound.
PAIRS = [
    # judge model identifiers (tables)
    ("deepseek/deepseek-chat-v3.1", "DeepSeek chat (version 3.1)"),
    ("DeepSeek-chat-v3.1", "DeepSeek chat (version 3.1)"),
    ("Gemini-2.5-flash-lite", "Gemini 2.5 Flash Lite"),
    ("mistralai/mistral-medium-3.1", "Mistral Medium 3.1"),
    ("moonshotai/kimi-k2-0905", "Kimi k2 from Moonshot AI (release 0905)"),
    # whole phrases that the generic renames below would garble
    ("ran temperature, DAS and a circuit at Gemma's one-token fork", "ran temperature, DAS and a circuit at the fork of Gemma"),
    ("returned to gemma-3-4b-it's one-token fork on the grid task", "returned to the fork of gemma-3-4b-it on the grid task"),
    ("is carried by a low-rank linear subspace of the task-specification states", "is carried by a linear subspace of the task specification states that has low rank"),
    ("each on the runner-up side of the axis from", "each displaced toward the second choice along the axis from"),
    ("outside a paraphrase null on the runner-up side", "outside a paraphrase null, displaced toward the second choice"),
    ("lie outside the null on the runner-up side", "lie outside the null, displaced toward the second choice"),
    ("leave the paraphrase null on the runner-up side", "leave the paraphrase null toward the second choice"),
    ("the off-default share of the continuations", "the share of continuations off the default"),
    ("against the five text-level knobs of iteration 5", "against the five knobs of iteration 5 that act on the text"),
    ("and three of five called a decreasing-height control novel", "and three of five called novel a control that processes heights in decreasing order"),
    ("two array-scan Dijkstra programs that run in quadratic time", "two Dijkstra programs that scan an array and run in quadratic time"),
    ("a signature of its data structures", "a signature of the program's data structures"),
    ("Does a fitted low-rank subspace of the task-specification states carry the choice, under permuted-label, "
     "random-initialisation and dormancy controls?",
     "Does a fitted subspace of low rank at the task specification states carry the choice, under controls with "
     "permuted labels, a randomly initialised network and dormancy?"),
    ("A *random-initialisation control* fits the same map on a randomly initialised copy of the network",
     "We call *random-initialisation control* a fit of the same map on a randomly initialised copy of the network"),
    ("readout, null-source and fourth-template controls", "readout controls, null source controls and fourth template controls"),
    ("quote-verified positioning row for the one-token fork", "positioning row, verified by quotation, for the fork of a single token"),
    ("teacher-forced and cached-prefill log-probabilities differ", "teacher-forced log probabilities and those from a cached prefill differ"),
    ("the joint top-five and top-ten sets", "the joint sets of the top five and the top ten"),
    ("the same-seed sweeps of iterations 1 to 4", "the sweeps of iterations 1 to 4 under a shared seed"),
    ("the same-seed contrast of plan noise", "the contrast of plan noise under the same seed"),
    ("per-model, per-quantity synthesis in place of one cross-model map", "synthesis per model and per quantity in place of one map across models"),
    ("invalid as not-Y, pass-ratio gate) with a correct-Y count beside every share",
     "invalid as not Y, gate on the pass ratio) with a count of correct Y programs beside every share"),
    ("correct-Y column for the extension cells", "column of correct Y programs for the extension cells"),
    # statistics
    ("post-hoc", "post hoc"), ("Post-hoc", "Post hoc"),
    ("one-sided", "one sided"), ("One-sided", "One sided"),
    ("lower-tail", "lower tail"), ("Lower-tail", "Lower tail"), ("upper-tail", "upper tail"),
    ("log-likelihood", "log likelihood"), ("log-odds", "log odds"), ("Log-odds", "Log odds"),
    ("log-probabilities", "log probabilities"),
    ("(cross-validated AUC", "(AUC under cross-validation"),
    ("rank-1 cross-validated recovery", "rank-1 recovery under cross-validation"),
    ("largest cross-validated rank-1 recovery", "largest rank-1 recovery under cross-validation"),
    ("Rank-1 cross-validated recovery", "Rank-1 recovery under cross-validation"),
    ("Pooled within-task Spearman", "Pooled Spearman within tasks"),
    ("parameter-free MAE", "MAE without fitted parameters"),
    ("all-cell Spearman", "Spearman over all cells"), ("All-cell Spearman", "Spearman over all cells"),
    ("An arm-shuffle placebo", "A placebo that shuffles the arms"),
    ("A temperature-shuffled placebo", "A placebo that shuffles the temperatures"),
    ("a token-map placebo", "a placebo that shuffles the token map"),
    ("Durkalski-adjusted McNemar", "McNemar with the Durkalski adjustment"),
    # exchanges and DAS arms
    ("read-position full-state exchange", "full state exchange at the read position"),
    ("read-position DAS", "DAS at the read position"),
    ("the read-position transplant", "the transplant at the read position"),
    ("read-position states", "states at the read position"), ("MDS of read-position centroids", "MDS of centroids at the read position"),
    ("the read-position centroids", "the centroids at the read position"), ("read-position", "read position"),
    ("forced-algorithm centroids", "centroids of prompts that force an algorithm"),
    ("A single-block full-state exchange", "A full state exchange at a single block"),
    ("the same single-block exchange", "the same exchange at a single block"),
    ("Single-block teacher-forced gain at that block", "Teacher-forced gain at that single block"),
    ("Full-state", "Full state"), ("full-state", "full state"),
    ("Permuted-label DAS", "DAS with permuted labels"), ("permuted-label DAS", "DAS with permuted labels"),
    ("Permuted-label transfer", "Transfer under permuted labels"),
    ("A *permuted-label fit*", "A *fit on permuted labels*"),
    ("a permuted-label fit", "a fit on permuted labels"), ("the permuted-label fit", "the fit on permuted labels"),
    ("The permuted-label fits", "The fits on permuted labels"),
    ("permuted-label and untrained-network versions", "versions with permuted labels and with an untrained network"),
    ("the random-subspace, permuted-label and untrained-network controls",
     "the controls with random subspaces, permuted labels and an untrained network"),
    ("permuted-label and untrained-network controls", "controls with permuted labels and an untrained network"),
    ("permuted-label", "permuted label"),
    ("random-init at most", "random initialisation at most"),
    ("Random-subspace recovery", "Recovery of random subspaces"),
    # dose units
    ("ban-free/iteration", "relative/iteration"),
    ("Ban-free profile", "Profile of the relative unit"), ("ban-free profile", "profile of the relative unit"),
    ("Ban-free unit", "Relative unit"), ("ban-free unit", "relative unit"), ("ban-free", "relative"),
    ("absolute per-block energy", "absolute energy per block"), ("per-block energy", "energy per block"),
    ("dose-unit", "dose unit"), ("Dose-unit", "Dose unit"),
    # second choice (the runner-up of earlier sections)
    ("a default-to-runner-up axis", "an axis from the default to the second choice"),
    ("A default-to-runner-up axis", "An axis from the default to the second choice"),
    ("the default-to-runner-up axis", "the axis from the default to the second choice"),
    ("The default-to-runner-up axis", "The axis from the default to the second choice"),
    ("the runner-up side of the axis", "the side of the second choice on the axis"),
    ("along the runner-up axis", "along the axis toward the second choice"),
    ("the runner-up axis", "the axis toward the second choice"),
    ("the opening of the runner-up algorithm", "the opening of the second choice"),
    ("forced runner-up prompt", "prompt forcing the second choice"),
    ("correct runner-up share", "correct share of the second choice"),
    ("the default and runner-up forced-prompt centroids", "the centroids of the prompts forcing the default and the second choice"),
    ("the runner-up centroid", "the centroid of the second choice"),
    ("the base runner-up", "the base model's second choice"),
    ("runner-up", "second choice"),
    # task specification, forced prompts, templates, bans
    ("task-specification", "task specification"), ("Task-specification", "Task specification"),
    ("top-five", "top five"), ("Top-five", "Top five"),
    ("forced-prompt", "forced prompt"), ("Forced-prompt", "Forced prompt"),
    ("fifth-template", "fifth template"), ("fourth-template", "fourth template"),
    ("forced-BFS", "forced BFS"), ("forced-DFS", "forced DFS"),
    ("size-k", "size k"),
    ("(leave-one-survivor bans)", "(bans that leave one survivor)"), ("of leave-one-survivor bans", "of bans that leave one survivor"),
    ("the survivor-region centroid", "the centroid of the survivor region"),
    ("the banned-region centroid", "the centroid of the banned region"),
    ("the in-manifold push", "the push inside the manifold"), ("in-manifold push", "push inside the manifold"),
    # forks, openings and temperature
    ("one-token fork", "fork of a single token"),
    ("end-of-text", "end of text"),
    ("of on-opening slots", "of slots on the opening"), ("the predicted on-opening share", "the predicted share on the opening"),
    ("On-opening forks", "Forks on the opening"), ("On-opening share", "Share on the opening"),
    ("no same-seed flips", "no flips under the same seed"), ("the same-seed test", "the test under the same seed"),
    ("their fork-margin change", "their change in fork margin"), ("Fork-margin Spearman", "Spearman of the fork margin"),
    ("Spearman of the L-token opening LLR", "Spearman of the opening LLR over L tokens"),
    ("The per-slot replay", "The replay per slot"), ("Per-slot replay", "Replay per slot"), ("(per-slot agreement", "(agreement per slot"),
    ("the replay-implied shares", "the shares implied by the replay"),
    ("are Prim-heavy at T 1.0", "lean toward Prim at T 1.0"),
    ("one low-probability fork token", "one fork token of low probability"),
    ("as a post-commit correction", "as a correction made after the commitment"),
    ("on byte-identical prompts", "on prompts identical byte for byte"),
    # DAS fits, edits and controls
    ("strong, low-rank steering handle", "strong steering handle of low rank"),
    ("a low-rank linear subspace", "a linear subspace of low rank"),
    ("fitted low-rank subspace", "fitted subspace of low rank"),
    ("A low-rank subspace", "A subspace of low rank"), ("a low-rank variable", "a variable of low rank"),
    ("low-rank", "low rank"),
    ("logit-only DAS lambda 1 (logit-only)", "DAS on the logits only, lambda 1"),
    ("logit-only DAS lambda 0.5 (logit-only)", "DAS on the logits only, lambda 0.5"),
    ("A logit-only version of the DAS edit, which", "A version of the DAS edit restricted to the logits, which"),
    ("logit-only", "logits only"),
    ("One-dimensionality without controls", "A single dimension claimed without controls"),
    ("one-dimensional", "one dimensional"),
    ("natural cross-prompt variance", "natural variance across prompts"), ("two cross-prompt readouts", "two readouts across prompts"),
    ("cross-prompt variance", "variance across prompts"),
    ("Twin-only share", "Share for the twin alone"),
    ("and projected-map retention", "and retention of the projected map"),
    ("Projected-map teacher-forced retention", "Teacher-forced retention of the projected map"),
    ("the class-mean edit", "the difference-in-means edit"), ("the class-mean coordinate", "the coordinate of the class mean"),
    ("Every non-direction cell", "Every cell other than the directions"),
    ("a random-direction clamp", "a clamp along a random direction"),
    ("Edit norm over the escaping-direction median", "Edit norm over the median escaping direction"),
    ("Axis-projection Spearman", "Spearman of the axis projection"),
    ("top-quartile cells", "cells of the top quartile"), ("the top-quartile arm", "the arm of the top quartile"),
    ("a plan-noise push", "a push of plan noise"), ("per-sample plan-noise rates", "per-sample rates of plan noise"),
    ("The per-unit contrast", "The contrast per unit"), ("per-direction outcomes", "outcomes per direction"),
    ("for the template-plus-noun-norm control", "for the control built from the template and the norm of the noun"),
    ("the massive-activation cell", "the cell with a massive activation"),
    ("unit-weight Dijkstra", "Dijkstra with unit weights"),
    ("a label-dependent position", "a position that depends on the label"),
    ("the activation-space geometry", "the geometry in activation space"),
    ("its condition-span clause", "its clause on the condition span"), ("the condition-span clause", "the clause on the condition span"),
    # Gemma circuit and engine checks
    ("and path-patched edges among the top 15", "and edges measured by path patching among the top 15"),
    ("whose path-patched effect", "whose effect under path patching"),
    ("from the BFS-leaning run of a pair into the DFS-leaning run", "from the run of a pair that leans toward BFS into the run that leans toward DFS"),
    ("are BFS-heavy", "lean toward BFS"),
    ("the multi-prompt path", "the path over several prompts"), ("the single-prompt path", "the path for a single prompt"),
    ("the single-position cache path", "the cache path for a single position"),
    ("a bf16 kernel and batch-shape effect", "an effect of bf16 kernels and batch shapes"),
    ("bf16 kernel-shape noise", "bf16 noise from kernel shapes"),
    # search, adjudication and the catalogue
    ("ran FunSearch-style evolution", "ran evolution in the style of FunSearch"),
    ("Distinct out-of-catalogue-screen programs", "Distinct programs passing the catalogue screen"),
    ("*out-of-catalogue screen*", "*catalogue screen*"),
    ("correct out-of-catalogue programs", "correct programs outside the catalogue"),
    ("distinct adjudicated outside-catalogue programs", "distinct adjudicated programs outside the catalogue"),
    ("Distinct outside-catalogue programs", "Distinct programs outside the catalogue"),
    ("the out-of-catalogue screen", "the catalogue screen"), ("out-of-catalogue", "outside the catalogue"),
    ("distinct screen-passing programs", "distinct programs passing the screen"),
    ("Distinct screen-passing programs", "Distinct programs passing the screen"),
    ("Search screen-passing programs", "Search programs passing the screen"),
    ("screen-passing idea clusters", "idea clusters passing the screen"),
    ("Screen-passing at depth", "Passing the screen at depth"),
    ("screen-passing", "passing the screen"),
    ("MIXED screen-level verdict", "MIXED verdict at the screen level"),
    ("level-a", "level a"), ("level-b", "level b"), ("Level-b", "Level b"),
    ("non-seed parents", "parents other than the seeds"),
    ("best single-sample knob", "best knob applied to single samples"),
    ("than single-sample knobs", "than knobs applied to single samples"),
    ("of single-sample generation", "of generation one sample at a time"),
    ("no single-sample arm", "no arm that draws single samples"),
    ("no single-sample knob", "no knob applied to single samples"),
    ("single-sample", "single sample"),
    ("five text-level knobs", "five knobs that act on the text"), ("the text-level knobs", "the knobs that act on the text"),
    ("Fenwick-tree order statistics", "order statistics on a Fenwick tree"),
    ("an order-statistic treap", "a treap with order statistics"), ("order-statistic treap", "treap with order statistics"),
    ("binary lifting find-kth", "binary lifting to find the kth"), ("(find-kth descent)", "(descent to find the kth)"),
    ("with value-indexed frequency counts", "with frequency counts indexed by value"),
    ("(fixed-width value buckets,", "(value buckets of fixed width,"),
    ("then value-range binary search", "then binary search on the value range"),
    ("(two-level histogram)", "(histogram in two levels)"), ("(frequency-table counts)", "(counts in a frequency table)"),
    ("(ten-algorithm catalogue)", "(catalogue of ten algorithms)"),
    ("10 maximum-size stress inputs", "10 stress inputs of maximum size"),
    ("a program that hard-codes hidden answers", "a program that embeds hidden answers as constants"),
    ("its identifier-normalised tokens", "its tokens after normalisation of identifiers"),
    ("a data-structure signature", "a signature of the program's data structures"),
    ("in near-equal numbers", "in nearly equal numbers"),
    ("D'Esopo-Pape", "D'Esopo–Pape"),
    ("a decreasing-height control", "a control that processes heights in decreasing order"),
    ("an n-round Bellman-Ford", "a Bellman-Ford of n rounds"), ("n-round Bellman-Ford", "Bellman-Ford of n rounds"),
    ("engine-control programs", "programs of the engine control"),
    # record audit
    ("An independent re-derivation through the standard library", "An independent recomputation with the standard library"),
    ("Headline re-derivation", "Headline recomputation"),
    ("Cross-check against", "Check against"), ("vendored and sha256-hashed", "vendored and hashed with SHA-256"),
    ("A residual-claim lint", "A lint for residual claims"), ("Residual-claim lint", "Lint for residual claims"),
    ("was rate-limited on", "hit rate limits on"), ("replacement, rate-limited on", "replacement hit rate limits on"),
    ("as adjacent-only to Forking Paths", "as only adjacent to Forking Paths"),
    ("a correct-only version of Table 238", "a version of Table 238 restricted to correct programs"),
    ("correct-only columns", "columns restricted to correct programs"), ("Correct-only rows", "Rows restricted to correct programs"),
    ("correct-Y", "correct Y"), ("not-Y", "not Y"), ("pass-ratio", "pass ratio"),
    ("re-pricing", "repricing"), ("re-priced", "repriced"), ("Re-priced", "Repriced"), ("re-tagged", "retagged"),
]

REGEX = [
    (re.compile(r"\bOff-default share ([yq])\b"), r"Share off the default (\1)"),
    (re.compile(r"\boff-default share ([yq])\b"), r"share off the default (\1)"),
    (re.compile(r"\boff-default (share|programs?|probability|rate|class|Y|y)\b"), r"\1 off the default"),
    (re.compile(r"\b[Oo]ff-default\b"), "off the default"),
    (re.compile(r"\b([Tt]he) empty-prefix (resampling|test|discrepancy)\b"), r"\1 \2 from the empty prefix"),
    (re.compile(r"\bmatched-norm random (exchanges?|subspaces?|directions?)\b"), r"random \1 of matched norm"),
    (re.compile(r"\bthe one-unit-per-sample NLA (\w+)"), r"the NLA \1 with one unit per sample"),
]


def apply(text: str) -> str:
    """``text`` with every rename applied outside markers, code spans and guarded spans."""
    kept: list[str] = []

    def stash(m: re.Match) -> str:
        kept.append(m.group(0))
        return f"\x00{len(kept) - 1}\x00"

    masked = PROTECT.sub(stash, text)
    for old, new in PAIRS:
        masked = masked.replace(old, new)
    for pattern, repl in REGEX:
        masked = pattern.sub(repl, masked)
    out = re.sub(r"\x00(\d+)\x00", lambda m: kept[int(m.group(1))], masked)
    return out.replace("⟦", "").replace("⟧", "")
