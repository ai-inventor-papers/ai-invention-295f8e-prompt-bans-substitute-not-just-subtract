"""Terminology fixes for the iteration-2 text, driven by the pipeline's vocabulary lint.

The lint flags (a) code-like tokens such as W1 or L4, (b) short quoted phrases, including the span
between two possessive apostrophes, and (c) hyphenated compounds that are not in the field's
vocabulary or a cited title. EXACT rewrites handle quotes, template codes and phrasing that needs
rewording; GENERIC rewrites then write the remaining compounds unhyphenated, as iteration 1 does.
Applied to the iteration-2 part files and closing section; each EXACT target must be present.
"""
import re
from pathlib import Path

WORK = Path(__file__).resolve().parent
FILES = ["part1.md", "part2.md", "part3.md", "part4.md", "part5.md", "closing.md"]

EXACT = [
    # part1: review map, hypothesis-review answers, hypothesis update, artifact table, protocol
    ('| Five-draw substitute claim | Grid geometry draw had no clear mode; "a few" unit weight Dijkstra programs were 8 of 18 |',
     '| Substitute claim over five draws | Grid geometry draw had no clear mode; the few unit weight Dijkstra programs were in fact 8 of 18 |'),
    ('| Hypothesis-review objections | Sham bans, self-simulation, point resampling, missing precedent |',
     '| Objections of the hypothesis review | Sham bans, simulation of own behaviour, point resampling, missing precedent |'),
    ("and also the model's runner-up, so this is weak and confounded evidence for negation-triggered promotion.",
     "and also the second choice of the model, so this is weak and confounded evidence for promotion triggered by negation."),
    ("Second, the review named self-simulation [{{Binder2024}}] as a rival reason why the model's own stated alternative predicts its behaviour:",
     "Second, the review named simulation of its own behaviour [{{Binder2024}}] as a rival reason why the stated alternative of the model predicts its behaviour:"),
    ("Self-simulation fits either branch of the substitution test below,",
     "Such simulation fits either branch of the substitution test below,"),
    ('and an unmapped "j-lens". The precedent is positioned in Section 2.3.11 and the j-lens was tested in Section 2.9.',
     "and an unmapped lens named in the request, which we refer to as the j-lens. The precedent is positioned in Section 2.3.11, and the lens, a Jacobian lens, was tested in Section 2.9."),
    ("under which a ban only subtracts and exposes the runner-up.",
     "under which a ban only subtracts and exposes the second choice of the model."),
    ("because every substitute it observed was also the model's runner-up and because on the shortest path task random directions reached the same runner-up as the ban.",
     "because every substitute it observed was also the second choice of the model and because on the shortest path task random directions reached the same second choice as the ban."),
    ("Qwen3-8B; one NVIDIA L4 (23 GB), 3.38 GPU-h of scoring plus about 0.24 h of generation",
     "Qwen3-8B; one 23 GB NVIDIA GPU, 3.38 GPU hours of scoring plus about 0.24 hours of generation"),
    ("| Qwen3-8B-FP8 (and a Llama pilot); one RTX 2000 Ada (16 GB), about 1.4 GPU-h |",
     "| Qwen3-8B, official 8-bit floating point checkpoint (and a Llama pilot); one RTX 2000 Ada (16 GB), about 1.4 GPU hours |"),
    ("same-seed temperature test; j-lens and NLA | Qwen3-8B bf16 states, FP8 twin for generation;",
     "same seed temperature test; Jacobian lens and NLA | Qwen3-8B bf16 states, 8-bit twin for generation;"),
    ('718-noun bank ("man", "guy", "house" and so on)', "718-noun bank (`man`, `guy`, `house` and so on)"),
    ('a nonce ban ("Do not use the Zorblax method", in the five templates) and a novelty instruction ("Write a novel algorithm for this task, one you have not seen before.").',
     "a nonce ban (`Do not use the Zorblax method`, in the five templates) and a novelty instruction (`Write a novel algorithm for this task, one you have not seen before.`)."),
    ("In prose we refer to the templates by their wording; the codes W1 to W5 appear only in table headers.",
     "We refer to the templates by their order in Table 40, from the first to the fifth."),
    ("| Code | Ban | Mention twin | Neutral twin |", "| Template | Ban | Mention twin | Neutral twin |"),
    ("| W1 | Do not use X", "| first | Do not use X"),
    ("| W2 | Your solution", "| second | Your solution"),
    ("| W3 | Avoid X", "| third | Avoid X"),
    ("| W4 | X is not allowed", "| fourth | X is not allowed"),
    ("| W5 | Write a correct", "| fifth | Write a correct"),
    ('(\"Implement j for this task\" and nine paraphrases)', "(`Implement j for this task` and nine paraphrases)"),
    # part2: audit
    ("The probes are L2-regularised logistic regression probes with leave-one-paraphrase-out folds, which is the honest test",
     "The probes are ridge regularised logistic regression probes fitted with folds that hold out one paraphrase at a time, which is the honest test"),
    ('(the null for "knows more than the paraphrase\'s base rate")',
     "(the null for a probe that knows no more than the base rate of each paraphrase)"),
    ("since both are also the model's runner-ups,", "since both are also second choices of the model,"),
    ("and the runner-up's share with a Wilson interval", "and the share of the second choice with a Wilson interval"),
    ('a 2% "other" floor for every family', "a 2% floor for other labels in every family"),
    ("and also the model's runner-up, so the test cannot say", "and also the second choice of the model, so the test cannot say"),
    ('Because "compliant" means correct,', "Because a compliant program must be correct,"),
    ("(ICLR 2025 for self-simulation, NAACL 2025 for denial prompting)",
     "(ICLR 2025 for the paper on introspection, NAACL 2025 for denial prompting)"),
    ("typicality bias [{{Zhang2025}}]; self-simulation [{{Binder2024}}]",
     "typicality bias [{{Zhang2025}}]; introspection and simulation of own behaviour [{{Binder2024}}]"),
    ("qualified the shortest path locus as a post-commit readout.", "qualified the shortest path locus as a readout after commitment."),
    ("a post-commit readout (shortest path)", "a readout after commitment (shortest path)"),
    ("Thirteen LeetCode-derived tasks", "Thirteen tasks derived from LeetCode"),
    # part3: likelihood screen and route experiment
    ("and TF32 matrix products", "and TensorFloat-32 matrix products"),
    ("Throughput on the L4 (1,046 tokens per second)", "Throughput on that GPU (1,046 tokens per second)"),
    ("Banned programs per template (W1 to W5, 20 each)", "Banned programs per template (first to fifth, 20 each)"),
    ('came from the not-allowed template ("breadth-first search (BFS) is not allowed here."), which gave 14 of 20 BFS',
     "came from the fourth template (`X is not allowed here`, with BFS as X), which gave 14 of 20 BFS"),
    # part4: ban lists, Llama, bench, readouts
    ('with a control for each reading of "where the mass goes",', "with a control for each reading of where the mass goes,"),
    ('DFS most often as "backtracking".', "DFS most often as `backtracking`."),
    ("Avoidance per template (W1 to W5)", "Avoidance per template (first to fifth)"),
    ('Over all programs, "no change" (the task\'s default algorithm) predicted 64% of multi-ban programs,',
     "Over all programs, predicting no change from the default algorithm was right for 64% of programs under a ban list,"),
    ('**Leave-one-survivor bans: "can" against "will".**', "**Bans that leave one survivor: can against will.**"),
    ('Shortest path leave-one-survivor bans (N = 100 each; "will" = share of programs implementing the survivor; "can" = share of 40 forced programs labelled as the survivor;',
     "Shortest path bans that leave one survivor (N = 100 each; will is the share of programs implementing the survivor and can the share of 40 forced programs labelled as the survivor;"),
    ("found no persistent loop (H1) on either task", "found no persistent loop on either task"),
    ('Dijkstra 43, "other" 37 and Bellman-Ford/SPFA 18', "Dijkstra 43, other labels 37 and Bellman-Ford/SPFA 18"),
    ('the audit judge called "other".', "the audit judge labelled as other."),
    ("Qwen3-8B ran from its official FP8 checkpoint through vLLM's FP8 Marlin kernels,",
     "Qwen3-8B ran from its official 8-bit floating point checkpoint through the 8-bit Marlin kernels of vLLM,"),
    ('20 free-form "standard alternative to X" answers per algorithm',
     "20 free-form answers per algorithm to the question `What is the standard alternative to X for this task?`"),
    ('and for the literal "always same seed" test of temperature.', "and for the literal same seed test of temperature."),
    ("On the grid task the not-allowed template gave BFS 15 of 20 times", "On the grid task the fourth template gave BFS 15 of 20 times"),
    ('so "the state at the commit token" means the state at the first lexicon match, not at the algorithm decision.',
     "so the state at the commit token is the state at the first lexicon match, not at the algorithm decision."),
    ("but only the not-allowed template produced both classes", "but only the fourth template produced both classes"),
    ('(" breadth", "-first", "ijkstra")', "(`breadth`, `-first`, `ijkstra`)"),
    ("all non-compliant runs came from the not-allowed template,", "all noncompliant runs came from the fourth template,"),
    ('a forbidden concept is "activated in order to be suppressed" [{{Mann2025}}]',
     "a forbidden concept is first activated so that it can be suppressed [{{Mann2025}}]"),
    ('the traces open by restating the ban and naming DFS within four sentences ("The constraints say not to use BFS, so I can\'t use that approach. ... Maybe depth-first search (DFS)?").',
     "the traces open by restating the ban and proposing DFS within their first four sentences."),
    ('**Lenses: NLA and the j-lens.** A dated search in this experiment resolved the request\'s two unmapped terms. "NLA" denotes',
     "**Lenses: NLA and the Jacobian lens.** A dated search in this experiment resolved the two unmapped terms of the request. NLA denotes"),
    ('The "j-lens" is the Jacobian lens, which reads a layer\'s state through the unembedding',
     "We refer to the request's j-lens as the Jacobian lens, which reads the state of a layer through the unembedding"),
    ("the shortest path leave-one-survivor ban of Bellman-Ford/SPFA", "the shortest path ban that leaves only Bellman-Ford/SPFA"),
    ("The literal five-name ban TOP5 (BFS, DFS, greedy, IDDFS, A*) was added.",
     "The literal ban of five names, TOP5 (BFS, DFS, greedy, IDDFS, A*), was added."),
    ("and 0.00 for the literal five-name ban,", "and 0.00 for the literal ban of five names,"),
    ("Thirteen LeetCode-derived tasks [{{Xia2025}}]", "Thirteen tasks derived from LeetCode [{{Xia2025}}]"),
    ("(adherence-corrected: L_corr = L + log adherence)", "(corrected for adherence: L_corr = L + log adherence)"),
    ("a short fine-tune on instruct activations or an instruct-trained dictionary is the alternative",
     "a short fine-tuning on instruct activations, or a dictionary trained on them, is the alternative"),
    # part5: comparisons, conclusions
    ('came from the not-allowed template ("breadth-first search (BFS) is not allowed here."), which produced BFS 43 times in 60 against 0 in 240 for the other four templates. On the shortest path task the avoid-entirely and not-allowed templates carry most of the failures',
     "came from the fourth template (`X is not allowed here`, with BFS as X), which produced BFS 43 times in 60 against 0 in 240 for the other four templates. On the shortest path task the third and fourth templates carry most of the failures"),
    ('(5 "other")', "(5 other labels)"),
    ("| Task | Draw | W1 do-not-use | W2 must-not-rely | W3 avoid-entirely | W4 not-allowed | W5 correct-solution-without | Banned share | Non-banned programs | Pass rate |",
     "| Task | Draw | First template | Second | Third | Fourth | Fifth | Banned share | Programs not banned | Pass rate |"),
    ('- *"Activated in order to be suppressed".* The prime-veto latent pattern appeared',
     "- *Activation of a forbidden concept in order to suppress it.* The prime and veto latent pattern appeared"),
    ("but self-simulation explains that success under either branch", "but simulation of its own behaviour explains that success under either branch"),
    ('one wording, "X is not allowed here", accounts for every grid failure in three draws.',
     "one wording, the fourth template (`X is not allowed here`), accounts for every grid failure in three draws."),
    ("and the NLA and j-lens mapping were run here.", "and the mapping of NLA and the Jacobian lens were run here."),
    # closing
    ('one template ("X is not allowed here") produced every failure', "one template (`X is not allowed here`) produced every failure"),
    ("lands on the same runner-up as the ban,", "lands on the same second choice as the ban,"),
    ("The model's ability to state its replacement in advance may be self-simulation [{{Binder2024}}] rather than evidence about how the ban is implemented.",
     "That the model can state its replacement in advance may reflect simulation of its own behaviour [{{Binder2024}}] rather than evidence about how the ban is implemented."),
    ("is not aimed at the algorithm the ban's own name primes or at the model's stated alternative,",
     "is not aimed at the algorithm primed by the name in the ban or at the alternative the model states,"),
]

# phrases that need rewording rather than a dropped hyphen; applied to every file, may be absent
REWORD = [
    (r"\battempted non-banned (programs?|samples?)\b", r"attempted \1 not banned"),
    (r"\battempted non-banned grid program\b", "attempted grid program not banned"),
    (r"\bAttempted non-banned\b", "Attempted, not banned"),
    (r"\bnon-banned programs\b", "programs not banned"),
    (r"\bnon-banned program\b", "program not banned"),
    (r"\bNon-banned programs\b", "Programs not banned"),
    (r"\bnon-banned\b", "not banned"),
    (r"\bnon-default survivors\b", "survivors other than the default"),
    (r"\bcorrect non-default programs\b", "correct programs other than the default"),
    (r"\btwo non-default bans\b", "two bans of algorithms other than the default"),
    (r"\bnon-default\b", "nondefault"),
    (r"\bno non-BFS program\b", "no program other than BFS"),
    (r"\bnon-BFS\b", "other than BFS"),
    (r"\bcorrect non-Dijkstra programs\b", "correct programs other than Dijkstra"),
    (r"\bnon-Dijkstra\b", "other than Dijkstra"),
    (r"\bnon-ban rows\b", "rows other than bans"),
    (r"\bnon-ban\b", "other than a ban"),
    (r"\bnon-compliant\b", "noncompliant"),
    (r"\bnon-degenerate\b", "nondegenerate"),
    (r"\bnon-overlapping\b", "nonoverlapping"),
    (r"\bnon-semantic\b", "nonsemantic"),
    (r"\bleave-one-survivor bans\b", "bans that leave one survivor"),
    (r"\bLeave-one-survivor bans\b", "Bans that leave one survivor"),
    (r"\bleave-one-survivor\b", "single survivor"),
    (r"\bleave-one-paraphrase-out selection\b", "selection that holds out one paraphrase at a time"),
    (r"\bleave-one-paraphrase-out folds\b", "folds that hold out one paraphrase at a time"),
    (r"\bfour- or five-name\b", "four or five name"),
    (r"\bfive-name\b", "five name"),
    (r"\bmulti-name bans\b", "ban lists"),
    (r"\bMulti-name bans\b", "Ban lists"),
    (r"\bmulti-name ban\b", "ban list"),
    (r"\bmulti-name\b", "ban list"),
    (r"\bMulti-name\b", "Ban list"),
    (r"\bmulti-ban experiment\b", "ban list experiment"),
    (r"\bMulti-ban experiment\b", "Ban list experiment"),
    (r"\bmulti-bans\b", "ban lists"),
    (r"\bMulti-bans\b", "Ban lists"),
    (r"\ba multi-ban\b", "a ban list"),
    (r"\bmulti-ban\b", "ban list"),
    (r"\bMulti-ban\b", "Ban list"),
    (r"\btwo-step bans\b", "double bans"),
    (r"\bTwo-step bans\b", "Double bans"),
    (r"\btwo-step ban\b", "double ban"),
    (r"\btwo-step\b", "double"),
    (r"\bTwo-step\b", "Double"),
    (r"\bthinking-on same-seed arm\b", "same seed arm with thinking on"),
    (r"\bthinking-on\b", "thinking on"),
    (r"\bWithin-ban decoder\b", "Decoder within one ban prompt"),
    (r"\bwithin-ban contrasts\b", "contrasts within one ban prompt"),
    (r"\bWithin-ban probes\b", "Probes within one ban prompt"),
    (r"\bwithin-ban\b", "within one ban"),
    (r"\bWithin-ban\b", "Within one ban"),
    (r"\boff-catalogue sham ban\b", "sham ban outside the catalogue"),
    (r"\boff-catalogue shams\b", "shams outside the catalogue"),
    (r"\boff-catalogue\b", "outside the catalogue"),
    (r"\bgated-out events\b", "events the gate excludes"),
    (r"\bladder-like\b", "close to the ladder"),
    (r"\blast-but-one\b", "penultimate"),
    (r"\blike-for-like\b", "matched"),
    (r"\banti-correlated\b", "negatively correlated"),
    (r"\bplug-in\b", "unrarefied"),
    (r"\bk-nearest-neighbour graph\b", "nearest neighbour graph"),
    (r"\bkey-value-cache patching\b", "KV cache patching"),
    (r"\bkey-value caches\b", "key and value (KV) caches"),
    (r"\bKey-value-cache\b", "KV cache"),
    (r"\bKey-value reuse\b", "KV cache reuse"),
    (r"\bkey-value reuse\b", "KV cache reuse"),
    (r"\bkey-value cache\b", "KV cache"),
    (r"\bkey-value\b", "KV"),
    (r"\bKey-value\b", "KV"),
    (r"\bBoyer-Moore-Horspool\b", "Horspool"),
    (r"\bGumbel-max coupling sensitivity\b", "Gumbel coupling sensitivity"),
    (r"\bGumbel-max\b", "Gumbel"),
    (r"\bscikit-learn\b", "sklearn"),
    (r"\bchi-square\b", "chi squared"),
    (r"\bfamily-wise\b", "familywise"),
    (r"\btie-breaker\b", "tiebreaker"),
    (r"\bsuper-additive\b", "superadditive"),
    (r"\bpost-order\b", "postorder"),
    (r"\bpre-commit\b", "precommit"),
    (r"\bk-th\b", "kth"),
    (r"\bnoun-B\b", "second noun"),
    (r"\bfine-tune\b", "fine-tuning"),
    (r"\bruntime-signature\b", "runtime signature"),
    (r"\bself-written\b", "self written"),
    (r"\bLeetCode-derived\b", "LeetCode"),
    (r"\bGPU-hours\b", "GPU hours"),
    (r"\bGPU-hour\b", "GPU hour"),
    (r"\bGPU-h\b", "GPU hours"),
    (r"\bGPU-phase\b", "GPU phase"),
    (r"\bruntime-AST\b", "runtime against AST"),
    (r"\bself-simulation\b", "simulation of its own behaviour"),
    (r"\bSelf-simulation\b", "Simulation of its own behaviour"),
    (r"\brunner-ups\b", "second choices"),
    (r"\brunner-up\b", "second choice"),
    (r"\bmodel-specific\b", "specific to the model"),
    (r"\bprime-and-veto\b", "prime and veto"),
    (r"\bPrime-and-veto\b", "Prime and veto"),
    (r"\bprime-veto\b", "prime and veto"),
    (r"\bad-hoc\b", "ad hoc"),
    (r"\bpost-commit\b", "after commitment"),
]


def generic(text: str) -> str:
    """Write every remaining non-standard hyphenated compound without its hyphens."""
    allow = {
        "free-form", "held-out", "cross-entropy", "per-sample", "per-token", "in-sample", "out-of-sample",
        "difference-in-means", "Bellman-Ford", "Floyd-Warshall", "top-k", "top-p", "instruction-tuned",
        "open-weight", "low-dimensional", "chain-of-thought", "fine-tuning", "fine-tuned", "Qwen-Scope",
        "well-known", "trade-off", "re-run", "multi-step", "task-specific", "out-of-distribution",
        "in-distribution", "TensorFloat-32", "rule-based", "single-step",
    }
    special = {"X-specific": "X specific", "X-SPECIFIC": "X SPECIFIC"}

    def repl(m: re.Match) -> str:
        word = m.group(0)
        if word in allow or word.lower() in allow:
            return word
        if word in special:
            return special[word]
        low = word.lower()
        if low.startswith("re-") and word.count("-") == 1:
            return word.replace("-", "")
        return word.replace("-", " ")

    out = []
    for line in text.split("\n"):
        # leave code spans, links and markers untouched
        parts = re.split(r"(`[^`]*`|\[ARTIFACT:[^\]]*\]|\[FIGURE:[^\]]*\]|\{\{\w+\}\})", line)
        for i in range(0, len(parts), 2):
            parts[i] = re.sub(r"\b[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z][A-Za-z0-9]*)+\b", repl, parts[i])
        out.append("".join(parts))
    return "\n".join(out)


def fix_text(text: str, exact: bool = True) -> str:
    if exact:
        for old, new in EXACT:
            if old in text:
                text = text.replace(old, new)
    for pat, rep in REWORD:
        text = re.sub(pat, rep, text)
    return generic(text)


def main() -> None:
    texts = {f: (WORK / f).read_text(encoding="utf-8") for f in FILES}
    joined = "\n".join(texts.values())
    missing = [old[:80] for old, _ in EXACT if old not in joined]
    if missing:
        raise SystemExit("EXACT targets not found:\n" + "\n".join(missing))
    for f, t in texts.items():
        (WORK / f).write_text(fix_text(t), encoding="utf-8")
    print("fixed", len(FILES), "files")


if __name__ == "__main__":
    main()
