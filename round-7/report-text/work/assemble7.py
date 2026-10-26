"""Assemble the iteration-7 section into paper_draft.md.

Inserts the section before the closing, replaces the closing, and appends references [132]-[136].
Reads work/paper_draft_corrected.md (the draft after the 54 record-audit corrections) so reruns are idempotent.
"""
import json
import re
import sys
from pathlib import Path

W = Path(__file__).parent
ROOT = W.parent
T = json.loads((W / "tables7.json").read_text())

TASK_CODES = [("T10", "connected components"), ("T03", "kth smallest"), ("T05", "two sum"), ("T06", "sixth task"),
              ("T2", "shortest path"), ("T1", "grid"), ("A3", "trapped rain water"), ("B3", "minimum spanning tree weight"),
              ("B6", "valid anagram")]
FIX = [
    ("H(algorithm | fork class)", "H(algorithm given fork class)"), ("H(label | token)", "H(label given token)"),
    ("Canonical opening length |O| (tokens)", "Canonical opening length (tokens)"),
    ("On-opening forks confirmed at |O|+1", "On-opening forks confirmed one token after the opening"),
    ("neutral twin(EAP)", "neutral twin"), ("{bfs: [12, 39]}", "BFS at tokens 12 and 39"), ("{bf_spfa: [92]}", "Bellman-Ford/SPFA at token 92"),
    ("| {} |", "| none |"), ("TWIN 6", "neutral twin 6"), ("; PN ", "; plan noise "), ("; BAN ", "; ban "),
    ("P_top > P_rest", "top quartile > rest"), ("D1 > P_shuf", "full absolute unit > shuffled positions"), ("BINT", "base intent"),
    ("| EAP |", "| enumerate and pick |"), ("fork found", "fork found"),
    ("Block chosen by teacher forcing (L*)", "Block chosen by teacher forcing"), ("gain at L* (nats)", "gain at that block (nats)"),
    ("full state at L* / band", "full state at that block / band"), ("at L* / band / base", "at that block / band / base"),
    ("brute_force", "brute force"), ("sort_two_pointers", "sort and two pointers"), ("sort_binary_search", "sort and binary search"),
    ("find_kth", "find-kth"), ("astar_gbfs", "A* or greedy best first"), ("| Y_any |", "| Y, any named algorithm |"),
    ("Minority algorithm A_min | A_min share", "Minority algorithm | Minority share"),
    ("| X_a | Rate a | 95% CI | X_b | Rate b |", "| Distinct screen-passing programs | Rate (level a) | 95% CI | Distinct outside-catalogue programs | Rate (level b) |"),
    ("Search X_a per island", "Search screen-passing programs per island"),
    ("0 in `report_corrected.md`", "0 in the corrected report"), ("(`audit/headline_check.py`, stdlib, its own code path)", "(standard library, its own code path)"),
    ("(`audit/rederive.py`, stdlib only)", "(standard library only)"), ("dependencies' own `predict_*` fields", "dependencies' own prediction fields"),
    ("U6 and D12 executed or logged but never reported", "the empty-prefix resampling test and the Gemma list of what did not run, executed or logged but never reported"),
    ("D12 into 6.8", "the Gemma list of what did not run, into Section 6.8"),
    ("plan noise at the moving design", "plan noise (absolute unit)"), ("commit0's", "the first commitment's"),
    ("N6 restated with its clustered interval", "the NLA contrast restated with its clustered interval"), ("captioned [FIGURE] markers", "captioned figure markers"), ("enumerate-and-pick", "enumerate and pick"),
    ("H(A \\| fork class)", "H(algorithm given fork class)"), ("\\|dObs - dPred\\|", "the absolute prediction error"),
    ("F Spearman on this engine's outcomes", "Fork-margin Spearman on the outcomes of this engine"), ("| P2 Spearman |", "| Axis-projection Spearman |"),
    ("Spearman of y with the engine control's bf16 y", "Spearman of y with the bf16 y of the engine control"),
    ("PCA variance (PC1, PC2)", "PCA variance (first and second components)"),
    ("One-sided LB95", "One-sided lower 95% bound"), ("LB95", "one-sided lower 95% bound"), ("(matched dy)", "(matched teacher-forced effect)"),
    ("| id | prediction | observed | verdict |", "| Prediction | What was predicted | Observed | Verdict |"),
    ("| P-S1a |", "| Unit effect |"), ("| P-S1b |", "| Seed effect |"), ("| P-S1c |", "| Interaction |"), ("| P-S1d |", "| Shortest path unit effect |"),
    ("| P-S1e |", "| Ban-free profile at absolute energy |"), ("| P-S2a |", "| Top quartile against rest |"), ("| P-S2b |", "| Full unit against shuffled positions |"),
    ("| S3 | plan noise (absolute unit) matches", "| Pricing against base intent | plan noise (absolute unit) matches"),
    ("| S3 | H5(plan noise (absolute unit)) ≥ 2", "| Pricing, 5-point Hill-1 | 5-point Hill-1 of plan noise (absolute unit) ≥ 2"),
    ("unit main effect (RD)", "unit main effect (risk difference)"), ("seed main effect (RD)", "seed main effect (risk difference)"),
    ("unit RD", "unit risk difference"), ("seed RD", "seed risk difference"),
    ("| shortest path | a | 3.83 | 1.83 | NOT MET |", "| shortest path | a | 3.83 | 1.82 | NOT MET |"),
]

D12_BODY_OLD = ('"Not run: U4 (clamp readback) and U5 (matched-norm realisation) as separate unit tests (the matched norm is imposed by construction in '
                "src/clamp.py and each edit's realised norm is logged per row); the clamp-cell overlay on the S11 generated-position panel; the T04 fork and "
                'the T04/R6 cross-prompt readouts (drop order); per-sample displacement at generated tokens 1-32 (prefill displacement at blocks 11-33 is logged)."')
D12_BODY_NEW = ("the clamp read-back and matched-norm realisation tests as separate unit tests (the matched norm is imposed by construction in the clamp code, "
                "and the realised norm of each edit is logged per row); the clamp-cell overlay on the generated-position panel; the fork and the cross-prompt "
                "readouts of two further bench tasks (dropped in order); and per-sample displacement at generated tokens 1-32 (prefill displacement at blocks "
                "11-33 is logged).")
EARLY = [
    ("The deviation log records what did not run (D12, verbatim): " + D12_BODY_OLD, "The deviation log records what did not run: " + D12_BODY_NEW, 1),
    ("The Gemma experiment's deviation D12 adds what it did not run: " + D12_BODY_OLD, "The deviation log of the Gemma experiment adds what it did not run: " + D12_BODY_NEW, 1),
    ("The fork's unit test U6 failed mildly", "The empty-prefix unit test of the fork failed mildly", 1),
    ("its rule label reads 'WITHDRAWN as FP8-specific: the site of the choice is open'. The 'FP8-specific' half of that label cannot apply:",
     "its rule label withdraws the site claim as specific to 8-bit floating point and states that the site of the choice is open. The half of that label about 8-bit floating point cannot apply:", 1),
    ("as the artifact's rule label says ('WITHDRAWN as FP8-specific: the site of the choice is open'); its engine half is refuted by Section 6.3.",
     "as the rule label of the artifact says (withdrawn as specific to 8-bit floating point, with the site of the choice open); its engine half is refuted by Section 6.3.", 1),
    ("where Gemma's natural choice is made (one generated token), and whether Qwen2.5-7B-Instruct's plan is verbalisable before the code (not to this NLA); Qwen3-8B's natural choice and Gemma's read position were never measured.",
     "where the natural choice of Gemma is made (one generated token), and whether the plan of Qwen2.5-7B-Instruct is verbalisable before the code (not to this NLA); the natural choice of Qwen3-8B and the read position of Gemma were never measured.", 1),
    ("on PC1, against centroids spread", "on that component, against centroids spread", 1),
    ("(mean state of 'Implement <algorithm>' prompts)", "(mean state of the forced prompts that ask for each algorithm)", 1),
    ("(MDS stress not recorded in top5_push.json)", "(MDS stress not recorded)", 1),
    ("(MDS stress not recorded in results/geometry.json)", "(MDS stress not recorded)", 1),
    ("(hidden_states[21], the 'hs21' convention)", "(the hidden state after block 20)", 1),
    ("(SPEC: from the first token of 'Task:' to the last token of the user message, src/cfg.py line 7)", "(from the first token of the task statement to the last token of the user message)", 4),
    ("({'dfs': 139, 'bfs': 61})", "(DFS 139, BFS 61)", 4),
    ("(resid_post)", "(the residual stream after the block)", 4),
    ("(its SPEC site is a mean over the task-specification positions, from the first token of 'Task:' to the last token of the user message, `src/cfg.py` line 7)",
     "(its task-specification site is a mean over the task-specification positions, from the first token of the task statement to the last token of the user message)", 1),
    ("forced 'Implement Y' centroids", "centroids of the forced prompts that ask for each algorithm", 1),
    ("forced 'Implement Y' prompts by mode and template", "forced prompts that ask for each algorithm, by mode and template", 1),
    ("Points: 28 prompt states, one per template: ban1 4, push1 4, push2 4, push4 4, push8 4, top5ban 4, twin 4.",
     "Points: 28 prompt states, one per template and condition: single-name ban 4, pushes of 1, 2, 4 and 8 ban units 4 each, top-five ban 4, twin 4.", 1),
    ("Source: engine control `results/pn.json`, `data/samples.jsonl`. The two added columns count only programs that pass every hidden test (from the per-row labels of `data/samples.jsonl`, the engine-a rows being iteration 4's), first over the engine's correct programs and then over all 50.",
     "Source: the plan-noise results and per-row samples of the engine control. The two added columns count only programs that pass every hidden test (from the per-row labels of the samples, the engine-a rows coming from iteration 4), first over the correct programs of each engine and then over all 50.", 1),
    ("the *transfer* of a cell is that share minus the twin's; a cell counts only if its pass rate is at least 0.8 times the twin's (commit0: \"pass_X / pass_TWIN (validity gate >= 0.8)\")",
     "the *transfer* of a cell is that share minus the share under the twin; a cell counts only if its pass rate is at least 0.8 times that of the twin (the validity gate of the first commitment)", 1),
]


def fix_earlier(text, before_text):
    for old, new, cnt in EARLY:
        assert text.count(old) == cnt, (old[:60], text.count(old))
        assert old not in before_text, old[:60]
        text = text.replace(old, new)
    text = re.sub(r"\(PC1 ([\d.]+%?), PC2 ([\d.]+%?) of", r"(first component \1, second \2 of", text)
    for a, b in (("commit0's outcome", "the outcome of the first commitment"), ("commit0's validity gate", "the validity gate of the first commitment"),
                 ("commit0's transfer", "the transfer of the first commitment"), ("commit0's", "the first commitment's"), ("commit0", "the first commitment")):
        text = text.replace(a, b)
    return text


def clean_table(tab):
    out = []
    for ln in tab.splitlines():
        for a, b in FIX:
            ln = ln.replace(a, b)
        ln = re.sub(r"\bhead L(\d+)\.H(\d+)\b", r"attention head \2 of layer \1", ln)
        ln = re.sub(r"\bMLP L(\d+)\b", r"MLP of layer \1", ln)
        ln = ln.replace("\u2014", "-")
        if ln.startswith("|"):
            for code, name in TASK_CODES:
                ln = re.sub(rf"(?<![\w.]){code}(?![\w.])", name, ln)
        out.append(ln)
    return "\n".join(out)


def fill(md):
    def rep(m):
        k = m.group(1)
        if k not in T:
            raise KeyError(k)
        return clean_table(T[k])
    return re.sub(r"\{\{(\w+)\}\}", rep, md)


section = "\n".join(fill((W / f"iter7_part{i}.md").read_text()).rstrip() + "\n" for i in (1, 2, 3))
for _a, _b in (("canonical opening", "shared opening"), ("Canonical opening", "Shared opening"), ("default opening", "shared opening"), ("Default opening", "Shared opening")):
    section = section.replace(_a, _b)
closing = (W / "closing7.md").read_text().rstrip() + "\n"

# Terminology pass (work/vocab7.py) over the text written this iteration; earlier sections keep their words.
sys.path.insert(0, str(W))
sys.dont_write_bytecode = True  # keep work/__pycache__/ out of the workspace
import vocab7  # noqa: E402

section = vocab7.apply(section)
closing = vocab7.apply(closing)

draft = (W / "paper_draft_corrected.md").read_text()
i_close = draft.index("\n# What we have learned so far\n")
i_refs = draft.index("\n# References\n")
refs = draft[i_refs + 1:].rstrip() + "\n"
new_refs = [
    "[132] Sutter et al. The Non-Linear Representation Dilemma: Is Causal Abstraction Enough for Mechanistic Interpretability? Neural Information Processing Systems. 2025.",
    "[133] Mouret and Clune. Illuminating search spaces by mapping elites. arXiv preprint arXiv:1504.04909. 2015.",
    "[134] Wang et al. Interpretability in the Wild: a Circuit for Indirect Object Identification in GPT-2 small. International Conference on Learning Representations. 2023.",
    "[135] Goldowsky-Dill et al. Localizing Model Behavior with Path Patching. arXiv preprint arXiv:2304.05969. 2023.",
    "[136] Syed et al. Attribution Patching Outperforms Automated Circuit Discovery. Proceedings of the 7th BlackboxNLP Workshop: Analyzing and Interpreting Neural Networks for NLP. 2024.",
]
refs = refs + "\n".join(new_refs) + "\n"
before_text = (W / "paper_draft_before_iter7.md").read_text()
prefix = fix_earlier(draft[:i_close + 1], before_text)
out = prefix + section + "\n" + closing + "\n" + refs
(ROOT / "paper_draft.md").write_text(out)
print("written", len(out))
