"""Assemble the iteration-5 section, rewrite the closing section and extend the references."""
import json, re
from pathlib import Path
W = Path(__file__).resolve().parent
ROOT = W.parent
T = {}
T.update(json.load(open(W / "tables_part1.json")))
T.update(json.load(open(W / "tables_part2.json")))
for k in ["A_ec", "ec24", "ec27"]:
    T[k] = (T[k].replace("ECTWIN", "twin").replace("ECBAN_d9002_a1.0", "random direction 9002, alpha 1")
            .replace("ECBAN_d9004_a1.0", "random direction 9004, alpha 1"))

# Table 92d from the positioning audit, quotes and URLs dropped
rr = (ROOT.parents[1] / "research-2/src/research_report.md").read_text()
refmap = {"2": "72", "3": "107", "4": "101", "7": "98", "8": "99", "10": "109", "11": "46", "12": "100", "15": "91",
          "16": "89", "17": "90", "18": "88", "19": "92", "20": "93", "22": "97", "28": "94", "29": "95", "30": "96",
          "31": "73", "32": "74", "35": "81", "40": "3", "41": "2", "42": "102", "50": "103", "52": "108", "55": "83",
          "57": "104"}
rows = []
for line in rr.splitlines():
    if not line.startswith("| 92d-"):
        continue
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    rid, claim, neigh, quote, url, retr, rel, adds = cells[:8]
    def sub(m):
        n = m.group(1)
        return f"[{refmap[n]}]" if n in refmap else ""
    neigh = re.sub(r"\s*\[(\d+)\]", lambda m: (" " + sub(m)) if sub(m) else "", neigh).strip()
    rows.append(f"| {rid} | {claim} | {neigh} | {rel} | {adds} |")
T["table92d"] = "| Row | Claim | Neighbour | Relation | What this run adds |\n|-|-|-|-|-|\n" + "\n".join(rows)

HDR = {
 "A_units": [("| Unit | Gate (kappa / rt-vs-adj) | Default (twin share) | Base pass | beta [95% CI] | r_u | Pred. class | E (a1 / a2) | Landing L_u | PN excess S |",
              "| Unit | Gate (kappa / runtime against adjudicated) | Default (twin share) | Base pass | beta [95% CI] | Base runner-up | Predicted class | Escape fraction (alpha 1 / alpha 2) | Push landing | Plan-noise excess |")],
 "B_units": [("| unit | default | K | beta_u | beta (attempts) | beta (plain) | r_u | E (a=1) | E (a=2) | E_u | push landing | PN excess | flags |",
              "| Unit | Default | Catalogue size | beta | beta (attempts) | beta (plain completion) | Base runner-up | Escape, alpha 1 | Escape, alpha 2 | Escape fraction | Push landing | Plan-noise excess | Flags |")],
 "G_units": [("| Unit | D_u (twin share) | β (pt) | class | r_u | E_u (α1, α2) | E_u max | landing | r_u = landing | PN excess | novelty off | twin modal | open. margin |",
              "| Unit | it default (twin share) | beta (pt) | Class | pt runner-up | Escape fraction (alpha 1, alpha 2) | Maximum over alpha | Landing | Runner-up = landing | Plan-noise excess | Novelty-instruction off-default | Twin modal share | Opening margin |")],
 "A_a2": [("| Event | r_u | L_u | n realised |", "| Event | Base runner-up | Push landing | Programs realised |")],
 "A_assoc_corr": [("| Unit | Association top-1 | Base r_u | Corrected counts |", "| Unit | Association top-1 | Base runner-up | Corrected counts |")],
 "B_a2": [("| unit | r_u | push landing | hit | log score BASE | ASSOC | PROX |", "| Unit | Base runner-up | Push landing | Hit | Log score, base composition | Association | Proximity |")],
 "B_rivals": [("| beta_u (ours) |", "| beta |"), ("| R_margin |", "| opening margin |"), ("| R_merit_runtime |", "| runtime merit gap |"), ("| R_merit_length |", "| length merit gap |"), ("| R_modal |", "| twin modal share |"), ("| R_novel |", "| novelty-instruction share |"), ("| R_novel_correct |", "| novelty-instruction share, correct programs |"), ("| K_u |", "| catalogue size |")],
 "G_a2": [("| Event | r_u | landing |", "| Event | pt runner-up | Landing |")],
 "gemma_variants": [("primary: catalogue-only avoidance A_t", "primary: catalogue-only avoidance"), ("without T1 and T2 (A_t)", "without the grid and shortest path tasks (avoidance)"), ("without NO-DEFAULT tasks (A_t)", "without the no-default task (avoidance)"), ("without NO-DEFAULT tasks (drop)", "without the no-default task (drop)"), ("without NO-DEFAULT tasks and tasks whose rule default != frozen D (A_t)", "without the no-default task and the task whose rule default differs from the frozen one (avoidance)")],
}
for k, pairs in HDR.items():
    for a_, b_ in pairs:
        assert a_ in T[k], (k, a_[:50])
        T[k] = T[k].replace(a_, b_)
T["table92d"] = T["table92d"].replace("FLAG C", "premise flag").replace("FLAG B", "forecast flag").replace("FLAG A", "transplant flag")
sec = "\n\n".join((W / f"sec5_part{i}.md").read_text().strip() for i in range(1, 5))
missing = set(re.findall(r"\{\{T:(\w+)\}\}", sec)) - set(T)
assert not missing, missing
sec = re.sub(r"\{\{T:(\w+)\}\}", lambda m: T[m.group(1)], sec)

draft = (ROOT / "paper_draft.md").read_text()
i = draft.index("\n# What we have learned so far")
j = draft.index("\n# References")
closing = (W / "closing.md").read_text().strip()
new_refs = """[87] Murthy et al. One fish, two fish, but not the whole sea: Alignment reduces language models' conceptual diversity. North American Chapter of the Association for Computational Linguistics. 2025.
[88] Prakash et al. Fine-Tuning Enhances Existing Mechanisms: A Case Study on Entity Tracking. International Conference on Learning Representations. 2024.
[89] Oozeer et al. Activation Space Interventions Can Be Transferred Between Large Language Models. International Conference on Machine Learning. 2025.
[90] Du et al. How Post-Training Reshapes LLMs: A Mechanistic View on Knowledge, Truthfulness, Refusal, and Confidence. arXiv preprint arXiv:2504.02904. 2025.
[91] Zhou. Same Targets, Different Computation: How Post-Training Divides Work Across Model Layers. arXiv preprint arXiv:2605.07284. 2026.
[92] Zhang et al. Not All Layers Need Tuning: Selective Layer Restoration Recovers Diversity. arXiv preprint arXiv:2602.06665. 2026.
[93] Sumita et al. Controlling the Diversity-Quality Trade-Off of LLMs by Merging Models Before and After Alignment. arXiv preprint arXiv:2610.22999. 2026.
[94] Wang et al. Optimizing Diversity and Quality through Base-Aligned Model Collaboration. arXiv preprint arXiv:2511.05650. 2025.
[95] Peeperkorn et al. Mind the Gap: Conformative Decoding to Improve Output Diversity of Instruction-Tuned Large Language Models. arXiv preprint arXiv:2507.20956. 2025.
[96] Feng et al. Don't Throw Away Your Pretrained Model. arXiv preprint arXiv:2510.09913. 2025.
[97] Anand et al. Measuring, Localizing, and Ablating Alignment Signatures in LLMs. arXiv preprint arXiv:2605.30526. 2026.
[98] Zhou. When RLVR Shrinks the Reasoning Boundary: Diagnosing Pass@k Inversion. arXiv preprint arXiv:2607.20543. 2026.
[99] Duan. What Will Post-Training Fix? Per-Problem Gains Are Shared Across Independent RL Runs, and Existing Checkpoints Predict Them Better Than A Priori Signals. arXiv preprint arXiv:2610.04978. 2026.
[100] Lin et al. The Unlocking Spell on Base LLMs: Rethinking Alignment via In-Context Learning. arXiv preprint arXiv:2312.01552. 2023.
[101] Yang et al. LLM Probability Concentration: How Alignment Shrinks the Generative Horizon. arXiv preprint arXiv:2506.17871. 2025.
[102] Dang et al. Weight Ensembling Improves Reasoning in Language Models. arXiv preprint arXiv:2504.10478. 2025.
[103] Nakamura. Measuring Alignment-Induced Activation Shifts Correctly: A Template-Controlled Difference-in-Differences Protocol. arXiv preprint arXiv:2605.24583. 2026.
[104] Jerge et al. Perturb the Thought, Not the Pixels: Latent-Space Rollout Diversification for Reinforcement Learning of Vision-Language Models. arXiv preprint arXiv:2608.21595. 2026.
[105] Bhushan et al. Can LLM Agents Discover? Evaluating Creativity on ML Engineering Tasks. arXiv preprint arXiv:2608.30047. 2026.
[106] Maveli et al. Are you Synthesizing or Recalling? Evaluating LLMs on Algorithmic Code Retrieval. arXiv preprint arXiv:2610.02438. 2026.
[107] Le Bronnec et al. Beyond pass@k: Redundancy-Aware RLVR for Multi-Sample Code Generation. arXiv preprint arXiv:2605.28022. 2026.
[108] Mohammadi. Creativity Has Left the Chat: The Price of Debiasing Language Models. arXiv preprint arXiv:2406.05587. 2024.
[109] Nguyen et al. The Reasoning Boundary Paradox: How Reinforcement Learning Constrains Language Models. arXiv preprint arXiv:2510.02230. 2025."""
refs = draft[j:].rstrip("\n")
assert "[86]" in refs and "[87]" not in refs
out = draft[:i] + "\n\n" + sec + "\n\n" + closing + "\n" + refs + "\n" + new_refs + "\n"
(ROOT / "paper_draft.md").write_text(out)
print("assembled", len(out))
