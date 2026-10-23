#!/usr/bin/env python3
"""The iteration-9 Step-0 edits of the iteration-8 record: verbatim old_text -> new_text tagged '(iteration-9 correction)'.

Every number inside a new_text is taken from the recomputed value ledger (P(name) returns the printed recomputed
value), from the 0e results (results/s0e.json), or from the positioning and figure tables built in eval.py; none is
retyped. Table edits replace caption + table as one unit so that the marker sits in the caption.
"""
from __future__ import annotations

from typing import Any, Callable

M = "(iteration-9 correction)"


def _table_block(report: str, caption_start: str) -> str:
    """Verbatim caption + table block starting at caption_start (through the last '|' line)."""
    i = report.index(caption_start)
    j = report.index("\n\n", i) + 2           # end of caption paragraph
    lines = report[j:].split("\n")
    k = 0
    while k < len(lines) and lines[k].startswith("|"):
        k += 1
    return report[i:j] + "\n".join(lines[:k])


def build(report: str, P: Callable[[str], str], Z: dict[str, Any], ctx: dict[str, Any]) -> list[dict[str, Any]]:
    E: list[dict[str, Any]] = []

    def add(eid: str, item: str, section: str, old: str, new: str, why: str, values: list[str]) -> None:
        E.append({"id": eid, "item": item, "section": section, "old_text": old, "new_text": new, "rationale": why,
                  "values": values})

    k15, k10 = Z["per_k"]["k15"], Z["per_k"]["k10"]

    # ============================================================================================ 0a circuit
    t395 = _table_block(report, "**Table 395.**")
    lines = t395.split("\n")
    cap = lines[0]
    rows395 = [l for l in lines if l.startswith("| ") and not l.startswith("| Node")]
    keys395 = list(ctx["rec395"].keys())
    new_rows, vals = [], []
    for row, k in zip(rows395, keys395):
        base = row.rstrip()
        if k == "mlp|L0|H-1|COND":
            new_rows.append(base + " 0.00 / 0.00 (edit not applied; see text) | n/a (edit not applied) |")
        else:
            new_rows.append(base + f" {P(f'0a.T395.{k}.abl_h')} / {P(f'0a.T395.{k}.ste_h')} | "
                                   f"{P(f'0a.T395.{k}.abl_hp')} / {P(f'0a.T395.{k}.ste_hp')} |")
        vals += [f"0a.T395.{k}.{s}" for s in ("abl", "abl_p", "ste", "ste_p", "abl_h", "ste_h", "abl_hp", "ste_hp")]
    q = ctx["code_quotes"]
    para = (
        f"\n\n**The held-out arm of the layer-0 node {M}.** The layer-0 MLP at the condition span has a held-out effect "
        f"of exactly {P('0a.L0.abl.heldout')} nats under ablation and steering because the held-out edit was never "
        f"applied. The class means that the edit writes are taken, for a condition-span node, only over pair prompts of "
        f"the held-out prompt's own template (`MeanCache.get` in `src/k3circuit.py`, line 482: `{q['482']}`; line 485 "
        f"also skips prompts whose span length differs). The 10 held-out prompts are templates F11 to F15 and the 20 "
        f"pair prompts F1 to F10, so {P('0a.cond_matches')} of the 10 held-out prompts has a matching pair prompt, the "
        f"mean is None (line 488), no edit is built, and the edited and unedited margins coincide; the stored rows show "
        f"the node and all 50 matched random components of the same class at exactly 0 on every held-out prompt "
        f"(20 of 20 prompt-by-mode rows). The node's {P('0a.L0.abl.mean_d')} nats (ablation) and {P('0a.L0.ste.mean_d')} "
        f"nats (steering) over 30 prompts are therefore {P('0a.L0.abl.pair')} and {P('0a.L0.ste.pair')} nats over the "
        f"{P('0a.C1forced.n_pair')} pair prompts plus ten zeros ({P('0a.L0.abl.pair')} x 20 / 30 = "
        f"{P('0a.L0.abl.mean_d')}); the identity mean x 30 = pair mean x 20 + held-out mean x 10 holds for every node of "
        f"both tables, and no other node has an exact-zero held-out effect ({P('0a.n_zero_nodes')} node in all, under "
        f"both modes). Its held-out status is untested, not failed: on the descriptive natural contrast, whose held-out "
        f"prompts share templates with its pairs, the same node gives {P('0a.nat.abl.heldout')} nats under ablation and "
        f"{P('0a.nat.ste.heldout')} under steering on {P('0a.nat.n_heldout')} held-out prompts (sign-flip p "
        f"{P('0a.nat.abl.p_heldout')}, the smallest one-sided p that five prompts allow, 1/32). BASE (B3) of iteration 9 "
        f"reruns the held-out arm with template-matched means.")
    hdr_old = "| Node | Ablation effect | Ablation p | Steering effect | Steering p | Both pass |\n|-|-|-|-|-|-|"
    hdr_new = ("| Node | Ablation effect | Ablation p | Steering effect | Steering p | Both pass | Held-out mean effect, "
               "ablation / steering (nats) | Held-out sign-flip p, ablation / steering |\n|-|-|-|-|-|-|-|-|")
    new395 = (cap + f" The two added columns give the mean effect over the 10 held-out prompts and its exact one-sided "
              f"sign-flip p (smallest possible 1/1024) {M}.\n\n" + hdr_new + "\n" + "\n".join(new_rows) + para)
    assert hdr_old in t395
    add("S0-0a-01", "0a", "8.5", t395, new395,
        "Table 395 gains the held-out columns; the layer-0 condition node's exact-zero held-out effect is an unapplied "
        "edit (MeanCache template filter), not a held-out failure", vals + ["0a.L0.abl.mean_d", "0a.L0.ste.mean_d",
                                                                          "0a.L0.abl.pair", "0a.L0.ste.pair",
                                                                          "0a.L0.abl.heldout", "0a.nat.abl.heldout",
                                                                          "0a.nat.ste.heldout", "0a.nat.abl.p_heldout",
                                                                          "0a.nat.n_heldout", "0a.cond_matches",
                                                                          "0a.n_zero_nodes", "0a.C1forced.n_pair"])
    t396 = _table_block(report, "**Table 396.**")
    lines = t396.split("\n")
    rows396 = [l for l in lines if l.startswith("| ") and not l.startswith("| Node")]
    keys396 = list(ctx["rec396"].keys())
    new_rows, vals = [], []
    for row, k in zip(rows396, keys396):
        new_rows.append(row.rstrip() + f" {P(f'0a.T396.{k}.abl_h')} / {P(f'0a.T396.{k}.ste_h')} | "
                                       f"{P(f'0a.T396.{k}.abl_hp')} / {P(f'0a.T396.{k}.ste_hp')} |")
        vals += [f"0a.T396.{k}.{s}" for s in ("abl", "abl_p", "ste", "ste_p", "abl_h", "ste_h", "abl_hp", "ste_hp")]
    new396 = (lines[0] + f" Held-out columns as in Table 395; no node here sits at the condition span, and every "
              f"held-out edit was applied {M}. {ctx['weak396']}\n\n" + hdr_new + "\n" + "\n".join(new_rows))
    add("S0-0a-02", "0a", "8.5", t396, new396, "Table 396 gains the held-out columns (connected components)",
        vals + ["0a.C2a.n_prompts", "0a.C2a.n_heldout"])
    add("S0-0a-03", "0a", "8.5",
        "The committed composition depends on the attribution screen, which missed Qwen3-8B's largest node; with the "
        "exhaustive sweep, the condition share of the primary contrast rises to 0.17 and the picture matches Gemma "
        "qualitatively: a layer-0 MLP at the condition span injects the instruction, and a late stack of fork-position "
        "MLPs and heads turns it into the fork logit. In Qwen3-8B that stack sits deeper (effect-weighted depth about "
        "0.86 against 0.69).",
        f"The committed composition depends on the attribution screen, which missed Qwen3-8B's largest node; with the "
        f"exhaustive sweep, the condition share of the primary contrast rises to {P('0a.motif.sweep_cond')}, still below "
        f"Gemma's band [{P('0a.band.cond.lo')}, {P('0a.band.cond.hi')}], and every minimum spanning tree row keeps a "
        f"fork-stack depth of {P('0a.motif.mst_depth_min')} to {P('0a.motif.mst_depth_max')}, above the band "
        f"[{P('0a.band.depth.lo')}, {P('0a.band.depth.hi')}] (the bands are constants of the committed motif code, "
        f"`src/k3motif.py` line {ctx['bands_line']}), so the post hoc sweep does not turn the committed different-motif "
        f"reading into a match {M}. What the two families share is a late stack of fork-position MLPs and heads that "
        f"carries the fork logit, deeper in Qwen3-8B (effect-weighted depth about {P('0a.motif.qwen_depth')} against "
        f"{P('0a.motif.gemma_depth')}); the layer-0 MLP at the condition span carries much of the forced contrast on the "
        f"20 pair prompts, but its held-out edit was never applied (see the paragraph after Table 395), and a structural "
        f"likeness or difference between discovered circuits is not by itself a likeness or difference of mechanism, the "
        f"phantom specialization that Bayat Makou et al. describe [146].",
        "The post hoc sweep was read as a qualitative match; recomputed, it still misses both committed bands",
        ["0a.motif.sweep_cond", "0a.band.cond.lo", "0a.band.cond.hi", "0a.motif.mst_depth_min",
         "0a.motif.mst_depth_max", "0a.band.depth.lo", "0a.band.depth.hi", "0a.motif.qwen_depth",
         "0a.motif.gemma_depth"])
    add("S0-0a-04", "0a", "8.9 Table 414",
        "| Shape of the circuit | Layer-0 condition MLP plus a late fork stack, depth about 0.86 | The same shape, depth "
        "0.69 | Section 8.5 |",
        f"| Shape of the circuit {M} | Late fork stack, depth {P('0a.motif.qwen_depth')}; condition share "
        f"{P('0a.motif.qwen_cond')}; committed motif test: {P('0a.motif.label').lower()} (condition share and depth "
        f"outside Gemma's bands [{P('0a.band.cond.lo')}, {P('0a.band.cond.hi')}] and [{P('0a.band.depth.lo')}, "
        f"{P('0a.band.depth.hi')}]); the layer-0 condition MLP rests on the 20 pair prompts (held-out edit not applied) "
        f"| Condition share {P('0a.motif.gemma_cond')}, depth {P('0a.motif.gemma_depth')} (motif match for its own "
        f"set) | Section 8.5 |",
        "Table 414 said 'the same shape'; the committed motif test says different motif",
        ["0a.motif.qwen_depth", "0a.motif.qwen_cond", "0a.motif.label", "0a.motif.gemma_cond", "0a.motif.gemma_depth",
         "0a.motif.gemma_label"])
    add("S0-0a-05", "0a", "8.10 Established",
        "carry the fork logit, with a layer-0 MLP at the condition span injecting the instruction, the same shape as "
        "Gemma's circuit.",
        f"carry the fork logit; the committed motif test reads {P('0a.motif.label').lower()} from Gemma's circuit "
        f"(condition share {P('0a.motif.qwen_cond')} against Gemma's band [{P('0a.band.cond.lo')}, "
        f"{P('0a.band.cond.hi')}]; fork-stack depth {P('0a.motif.qwen_depth')} against [{P('0a.band.depth.lo')}, "
        f"{P('0a.band.depth.hi')}]), and the layer-0 MLP at the condition span rests on the 20 pair prompts because its "
        f"held-out edit was never applied {M}.",
        "'Established' claimed Gemma's shape", ["0a.motif.label", "0a.motif.qwen_cond", "0a.motif.qwen_depth"])
    add("S0-0a-06", "0a", "What we have learned",
        "Path-patching circuits for the fork margin, validated against matched random components in the real model, "
        "have the same shape in both families: a layer-0 MLP at the condition span injects the instruction, and a late "
        "stack of fork-position MLPs and heads turns it into the fork logit, deeper in Qwen3-8B (effect-weighted depth "
        "about 0.86) than in Gemma (0.69); 9 of 10 and 8 of 10 Qwen3-8B nodes pass both tests.",
        f"Path-patching circuits for the fork margin, validated against matched random components in the real model, "
        f"show that a late stack of fork-position MLPs and heads carries the fork logit in both families; the committed "
        f"motif test reads {P('0a.motif.label').lower()} (condition share {P('0a.motif.qwen_cond')} against Gemma's band "
        f"[{P('0a.band.cond.lo')}, {P('0a.band.cond.hi')}]; fork-stack depth {P('0a.motif.qwen_depth')} against "
        f"[{P('0a.band.depth.lo')}, {P('0a.band.depth.hi')}]), and the post hoc sweep still misses both bands "
        f"(forced-Prim condition share {P('0a.motif.sweep_cond')}; every minimum spanning tree row depth "
        f"{P('0a.motif.mst_depth_min')} to {P('0a.motif.mst_depth_max')}). The layer-0 condition-span MLP rests on the "
        f"20 pair prompts ({P('0a.L0.abl.pair')} and {P('0a.L0.ste.pair')} nats under ablation and steering) plus the "
        f"descriptive natural contrast, because its held-out edit was never applied, and BASE (B3) reruns the held-out "
        f"arm; 9 of 10 and 8 of 10 Qwen3-8B nodes pass both tests {M}.",
        "The closing repeated 'the same shape'", ["0a.motif.label", "0a.motif.qwen_cond", "0a.motif.qwen_depth",
                                                  "0a.motif.sweep_cond", "0a.motif.mst_depth_min",
                                                  "0a.motif.mst_depth_max", "0a.L0.abl.pair", "0a.L0.ste.pair"])
    add("S0-0a-07", "0a", "8.10 Table 416",
        "but the matched random five also flip at dose 2 (7:1, p 0.070; 0:1); motif differs on condition share and depth |",
        f"but the matched random five also flip at dose 2 (7:1, p 0.070; 0:1); motif differs on condition share and "
        f"depth; the layer-0 condition MLP's held-out edit was never applied ({P('0a.L0.abl.heldout')} by construction), "
        f"so that node rests on its 20 pair prompts {M} |",
        "Table 416's circuit row gains the held-out note", ["0a.L0.abl.heldout"])

    # ============================================================================================ 0b DAS verdict
    das_sent = (f"Under the committed rule it is a sufficient handle in Gemma and {P('0b.T10.verdict')} at Qwen3-8B's "
                f"fork, where the edit toward BFS writes BFS in {P('0b.bfs.written')} of 30 programs but "
                f"{P('0b.bfs.fail')} fail (pass {P('0b.bfs.pass')} against {P('0b.bfs.base_pass')}; "
                f"{P('0b.bfs.mc_a')}:{P('0b.bfs.mc_b')} against random, p {P('0b.bfs.mc_p')}).")
    dasv = ["0b.T10.verdict", "0b.bfs.written", "0b.bfs.fail", "0b.bfs.pass", "0b.bfs.base_pass", "0b.bfs.mc_a",
            "0b.bfs.mc_b", "0b.bfs.mc_p"]
    add("S0-0b-01", "0b", "8.4 Verdict",
        "What the protocol finds in both families is a strong steering handle of low rank at the fork, not a certified "
        "variable: a certified variable would pass every control, while a steering handle moves the output without "
        "passing them.",
        f"What the protocol finds is a rank-4 edit at the fork that moves the written algorithm in both families, not a "
        f"certified variable: a certified variable would pass every control. {das_sent} Neither passes the specificity "
        f"controls {M}.",
        "The verdict paragraph called both forks a strong steering handle; the committed generation rule says NO HANDLE "
        "at Qwen3-8B's fork", dasv + ["0b.GRID.verdict"])
    add("S0-0b-02", "0b", "8.9",
        "the rank-4 DAS map at block 22 (29 of 30 correct), the top five circuit components at dose 2 (29 of 30)",
        f"the rank-4 DAS map at block 22 ({P('0b.dfs.correct')} of 30 correct toward DFS; toward BFS it writes BFS in "
        f"{P('0b.bfs.written')} of 30 programs but only {P('0b.bfs.correct')} correct, {P('0b.T10.verdict')} by the "
        f"committed rule) {M}, the top five circuit components at dose 2 (29 of 30)",
        "A DAS-fork-DFS '29 of 30' without the BFS direction", ["0b.dfs.correct", "0b.bfs.written", "0b.bfs.correct",
                                                                "0b.T10.verdict"])
    add("S0-0b-03", "0b", "8.9 Table 414",
        "| Steering handle at the fork in generation | Toward DFS 29 of 30 correct; toward BFS 29 of 30 written, 5 correct "
        "| Toward BFS 22 of 30 correct (twin 6) | Section 8.4 |",
        f"| Steering handle at the fork in generation | Toward DFS {P('0b.dfs.correct')} of 30 correct; toward BFS "
        f"{P('0b.bfs.written')} of 30 written, {P('0b.bfs.correct')} correct (pass {P('0b.bfs.pass')} against "
        f"{P('0b.bfs.base_pass')}): {P('0b.T10.verdict')} by the committed rule {M} | Toward BFS {P('0b.grid.das')} of "
        f"30 correct (twin {P('0b.grid.base')}): {P('0b.GRID.verdict').lower()} | Section 8.4 |",
        "Table 414's steering row lacked the committed verdicts", ["0b.dfs.correct", "0b.bfs.written", "0b.bfs.correct",
                                                                   "0b.bfs.pass", "0b.bfs.base_pass", "0b.T10.verdict",
                                                                   "0b.grid.das", "0b.grid.base", "0b.GRID.verdict"])
    add("S0-0b-04", "0b", "8.10 Established",
        "A rank-4 linear edit at the fork moves the written algorithm in both families, and under one protocol neither "
        "family's handle is a certified variable: permuted labels, an untrained network or matched random components "
        "reproduce most of each effect.",
        f"A rank-4 edit at the fork moves the written algorithm in both families. {das_sent} Neither passes the "
        f"specificity controls: permuted labels, an untrained network or matched random components reproduce most of "
        f"each effect {M}.", "'Established' pooled the two directions", dasv)
    add("S0-0b-05", "0b", "8.10 Table 416",
        "off-manifold overshoot at both forks; the band is a sufficient handle that fails the label control |",
        f"off-manifold overshoot at both forks; the band is a sufficient handle that fails the label control; in "
        f"generation Gemma's fork is a {P('0b.GRID.verdict').lower()} and Qwen3-8B's fork {P('0b.T10.verdict')} (toward "
        f"BFS {P('0b.bfs.written')} of 30 written, {P('0b.bfs.fail')} fail; pass {P('0b.bfs.pass')} against "
        f"{P('0b.bfs.base_pass')}) {M} |",
        "Table 416's DAS row lacked the per-site generation verdicts", ["0b.GRID.verdict", "0b.T10.verdict",
                                                                        "0b.bfs.written", "0b.bfs.fail", "0b.bfs.pass",
                                                                        "0b.bfs.base_pass"])
    add("S0-0b-06", "0b", "What we have learned",
        "At the fork itself, one DAS protocol with seven committed controls found a rank-4 handle in both families that "
        "writes the algorithm in generation (29 of 30 correct DFS on connected components; 22 of 30 correct BFS in Gemma "
        "against 6 unedited).",
        f"At the fork itself, one DAS protocol with seven committed controls found a rank-4 edit that moves the written "
        f"algorithm in both families ({P('0b.dfs.correct')} of 30 correct DFS on connected components; "
        f"{P('0b.grid.das')} of 30 correct BFS in Gemma against {P('0b.grid.base')} unedited). {das_sent[:-1]} {M}.",
        "The closing called it a handle in both families", dasv + ["0b.dfs.correct", "0b.grid.das", "0b.grid.base"])

    # ============================================================================================ 0c entropy and law
    ent = (f"the single highest-entropy position among the first 64 tokens on {P('0c.G.hits')} of {P('0c.G.n')} "
           f"(Gemma), {P('0c.B3.hits')} of {P('0c.B3.n')} (minimum spanning tree) and {P('0c.B6.hits')} of "
           f"{P('0c.B6.n')} (valid anagram) slots, but on {P('0c.T10.hits')} of {P('0c.T10.n')} (connected components) "
           f"and {P('0c.A3.hits')} of {P('0c.A3.n')} (trapped rain water), the two units where a highest-entropy rule "
           f"misses it")
    entv = [f"0c.{u}.{s}" for u in ("G", "B3", "B6", "T10", "A3") for s in ("hits", "n")]
    add("S0-0c-01", "0c", "8.3 entropy paragraph",
        "Code tokens are nearly deterministic, so the 90th percentile of the twin's per-token entropies is only 0.0003 to "
        "0.05 nats, and the fork's entropy at T 1 lies above it in every sample of every unit (median 0.13 nats on "
        "connected components and 0.53 to 0.81 nats on the mixed units). The fork is also the single highest-entropy "
        "position among the first 64 tokens on 44 of 44 Gemma slots that reach it, 32 of 39 minimum spanning tree slots "
        "and 21 of 39 valid anagram slots, but on only 2 of 50 connected components slots and 0 of 37 trapped rain water "
        "slots. A rule that doses the highest-entropy position therefore finds the fork on the mixed units (in Gemma it "
        "reproduces the fork-dosed arm exactly) and misses it on the collapsed one.",
        f"Code tokens are nearly deterministic, so the 90th percentile of the twin's per-token entropies is only "
        f"{P('0c.q90.min')} to {P('0c.q90.max')} nats, and the fork's entropy at T 1 lies above it in all "
        f"{P('0c.n_total')} twin samples that reach the fork on the five located units (median {P('0c.T10.median_H_rec')} "
        f"nats on connected components and {P('0c.mixed_median.min')} to {P('0c.mixed_median.max')} nats on the mixed "
        f"units). The fork is also {ent}. A rule that doses the highest-entropy position therefore finds the fork on most "
        f"slots of three of the four mixed units (on every Gemma slot, where it reproduces the fork-dosed arm exactly, but "
        f"on only {P('0c.B6.hits')} of {P('0c.B6.n')} valid anagram slots) and misses it on trapped rain water and on "
        f"the collapsed connected components {M}.",
        "The highest-entropy rule was said to find the fork on 'the mixed units'; it misses trapped rain water (0 of 37)",
        entv + ["0c.q90.min", "0c.q90.max", "0c.n_total", "0c.T10.median_H_rec", "0c.mixed_median.min",
                "0c.mixed_median.max"])
    add("S0-0c-02", "0c", "8.10 Table 416",
        "| Fork entropy prediction | Opposite holds | The fork lies above the 90th percentile of per-token entropy in every "
        "sample; it is the highest-entropy position on 44 of 44 Gemma slots but 2 of 50 on connected components |",
        f"| Fork entropy prediction | Opposite holds | The fork lies above the 90th percentile of per-token entropy in all "
        f"{P('0c.n_total')} twin samples that reach it; it is {ent} {M} |",
        "Table 416's entropy row carried a superlative", entv + ["0c.n_total"])
    add("S0-0c-03", "0c", "8.10 Established",
        "The fork is a high-entropy position relative to the near-deterministic code around it, though its entropy can "
        "be small in absolute terms (0.13 nats on connected components).",
        f"The fork's entropy lies above the 90th percentile of the twin's per-token entropies in all {P('0c.n_total')} "
        f"twin samples that reach it, though it can be small in absolute terms (median {P('0c.T10.median_H_rec')} nats "
        f"on connected components); it is {ent} {M}.",
        "'Established' needed the per-unit scope", entv + ["0c.n_total", "0c.T10.median_H_rec"])
    add("S0-0c-04", "0c", "What we have learned",
        "The fork is the highest-entropy position of the near-deterministic code around it in every sample, though its "
        "entropy can be small in absolute terms (median 0.13 nats on connected components).",
        f"The fork's entropy lies above the 90th percentile of per-token entropy in all {P('0c.n_total')} twin samples "
        f"that reach it, though it can be small in absolute terms (median {P('0c.T10.median_H_rec')} nats on connected "
        f"components); it is {ent} {M}.",
        "The closing claimed the highest-entropy position in every sample", entv + ["0c.n_total", "0c.T10.median_H_rec"])
    add("S0-0c-05", "0c", "What we have learned",
        "and at most 0.004 bits under iteration 8's blind locator, which adds a second fork inside impure branches",
        f"and at most {P('0c.law.Hmax5')} bits on the five Qwen3-8B and Gemma units of iteration 8's blind locator "
        f"({P('0c.law.H_llama')} bits on Llama's grid task, where the fork is reached through many openings) {M}, which "
        f"adds a second fork inside impure branches",
        "The 0.004-bit scope omitted Llama's 0.63 bits", ["0c.law.Hmax5", "0c.law.H_llama"])
    law = (f"on {P('0c.law.n_pass')} of {P('0c.law.n_scored')} units the fork tokens predict temperature's effect on the "
           f"algorithm mix, but the flat law is better on valid anagram ({P('0c.law.B6.flat')} against "
           f"{P('0c.law.B6.mae')}), algorithm-level tempering is better on substring search ({P('0c.law.GT04.temper')} "
           f"against {P('0c.law.G-T04.mae')}), the law beats the flat law on only {P('0c.law.beats_flat')} of 6 units "
           f"(sign test p {P('0c.law.sign_p')}), and on Llama's grid task every predictor fails ({P('0c.law.L-T1.mae')})")
    lawv = ["0c.law.n_pass", "0c.law.n_scored", "0c.law.B6.flat", "0c.law.B6.mae", "0c.law.GT04.temper",
            "0c.law.G-T04.mae", "0c.law.beats_flat", "0c.law.sign_p", "0c.law.L-T1.mae"]
    add("S0-0c-06", "0c", "8.9",
        "the temperature-law experiment predicted global temperature sweeps within 0.014 to 0.054 on five of six units, "
        "two of them in a held-out family, and both found nothing outside the catalogue.",
        f"the temperature-law experiment predicted global temperature sweeps within {P('0c.law.G-R6.mae')} to "
        f"{P('0c.law.B6.mae')} on five of six units, two of them in a held-out family, and both found nothing outside "
        f"the catalogue; {law} {M}.", "8.9 stated the law without its rivals", lawv + ["0c.law.G-R6.mae"])
    add("S0-0c-07", "0c", "8.10 Established",
        "and a law composed over one or two forks found blind predicts global temperature sweeps on held-out Gemma units "
        "(0.033 and 0.014) as well as on Qwen3-8B (0.029 to 0.054).",
        f"and a law composed over one or two forks found blind predicts global temperature sweeps on held-out Gemma units "
        f"({P('0c.law.G-T04.mae')} and {P('0c.law.G-R6.mae')}) as well as on Qwen3-8B ({P('0c.law.A3.mae')} to "
        f"{P('0c.law.B6.mae')}): {law} {M}.", "'Established' stated the law without its rivals",
        lawv + ["0c.law.G-R6.mae", "0c.law.A3.mae"])
    add("S0-0c-08", "0c", "8.10 Table 416",
        "| Temperature-law claim | Partial | 5 of 6 units pass including both held-out Gemma units; only 3 held-out units "
        "scored (4 required); Llama fails (0.142) |",
        f"| Temperature-law claim | Partial | {P('0c.law.n_pass')} of {P('0c.law.n_scored')} units pass including both "
        f"held-out Gemma units; only 3 held-out units scored (4 required); Llama fails ({P('0c.law.L-T1.mae')}); the "
        f"flat law beats the composed law on valid anagram ({P('0c.law.B6.flat')} against {P('0c.law.B6.mae')}) and "
        f"algorithm-level tempering on substring search ({P('0c.law.GT04.temper')} against {P('0c.law.G-T04.mae')}); "
        f"the law beats the flat law on {P('0c.law.beats_flat')} of 6 (sign test p {P('0c.law.sign_p')}) {M} |",
        "Table 416's law row omitted the rivals", lawv)
    add("S0-0c-09", "0c", "What we have learned",
        "predicted the minority share across T 0.3 to 1.3 within a mean total variation distance of 0.029 to 0.054 on "
        "three Qwen3-8B units and 0.033 and 0.014 on two held-out Gemma units.",
        f"predicted the minority share across T 0.3 to 1.3 within a mean total variation distance of "
        f"{P('0c.law.A3.mae')} to {P('0c.law.B6.mae')} on three Qwen3-8B units and {P('0c.law.G-T04.mae')} and "
        f"{P('0c.law.G-R6.mae')} on two held-out Gemma units; {law} {M}.", "The closing stated the law without rivals",
        lawv + ["0c.law.A3.mae", "0c.law.G-R6.mae"])

    # ============================================================================================ 0d positioning
    add("S0-0d-01", "0d", "8.10b (new)", "## 8.11 What the next iteration takes from this one",
        ctx["positioning_section"] + "\n\n## 8.11 What the next iteration takes from this one",
        "Iteration 8's claims were never positioned against the verified neighbours as a table", [])
    add("S0-0d-02", "0d", "8.7 base sub-arm",
        "The instruct default is therefore not the base model's mean: on minimum spanning tree weight",
        f"The instruct default is therefore not the base model's mean (that post-training shifts concentrate at the base "
        f"model's high-entropy forks is already shown by Cantarero et al. [142] and Sparse but Critical [143]; what this "
        f"sub-arm adds is the algorithm-level outcome on code at a counterfactually located fork) {M}: on minimum "
        f"spanning tree weight", "Base sub-arm stated without the neighbours that occupy the concentration result", [])
    add("S0-0d-03", "0d", "8.10 Established",
        "so the instruct default is a sharpened second or third choice of the base model, not its mean.",
        f"so the instruct default is a sharpened second or third choice of the base model, not its mean; the "
        f"concentration of post-training shifts at base-entropy forks is prior work (Cantarero et al. [142]; Sparse but "
        f"Critical [143]), and the contribution here is the algorithm-level reading on code {M}.",
        "'Established' needed the attribution", [])
    add("S0-0d-04", "0d", "What we have learned",
        "the instruct default is the base model's second or third choice at the fork, sharpened, not its mean answer.",
        f"the instruct default is the base model's second or third choice at the fork, sharpened, not its mean answer; "
        f"that post-training shifts concentrate at forks is shown by Cantarero et al. [142] and Sparse but Critical "
        f"[143], and the run adds the algorithm-level outcome on code at a counterfactually located fork {M}.",
        "The closing needed the attribution", [])
    last_ref = [l for l in report.rstrip("\n").split("\n") if l.startswith("[141] ")][0]
    add("S0-0d-05", "0d", "References", last_ref, last_ref + "\n" + "\n".join(f"{r} {M}" for r in ctx["new_refs"]),
        "References for the neighbours added by the positioning table", [])

    # ============================================================================================ 0e alias-named manifold
    zv = ctx["z_printed"]
    alias_facts = ("every bidirectional BFS alias contains 'BFS' or 'breadth-first', every bidirectional A* alias "
                   "contains 'A*', IDA*'s aliases contain 'A*', 'iterative deepening' or 'Manhattan heuristic', and jump "
                   "point search and unit-weight Dijkstra share no algorithm-specific term with any banned alias")
    add("S0-0e-01", "0e", "8.8 intro",
        "then placed that model's survivors on its own manifold of ten forced algorithms, in actual activation "
        "coordinates.",
        f"then placed that model's survivors on its own manifold of ten forced algorithms, in actual activation "
        f"coordinates; each forced prompt names its algorithm by one of three aliases, so the manifold is alias-named "
        f"{M}.", "The manifold's prompts name the algorithm", [])
    add("S0-0e-02", "0e", "8.8 classes",
        "and middle at the median; the landing statistic is the mean g over the correct catalogue survivors (Table 412).",
        f"and middle at the median; the landing statistic is the mean g over the correct catalogue survivors (Table "
        f"412). The manifold is built from 300 prompts that each name the algorithm by one of three aliases, so "
        f"'opposite' may reflect the distance between names: {alias_facts} {M}.",
        "The classes were stated without the alias caveat", [])
    add("S0-0e-03", "0e", "8.8 Table 412",
        "**Table 412.** Geodesic classes of the non-banned algorithms at block 31, k 15, and their stability under 1,000 "
        "bootstrap resamples of paraphrase groups.",
        f"**Table 412.** Geodesic classes of the non-banned algorithms at block 31, k 15, and their stability under 1,000 "
        f"bootstrap resamples of paraphrase groups, on the alias-named manifold {M}.", "Table caption", [])
    add("S0-0e-04", "0e", "8.8",
        "so edge and opposite are classes of geodesic distance on a manifold that is not a ring.",
        f"so edge and opposite are classes of geodesic distance on a manifold that is not a ring and whose prompts name "
        f"each algorithm by one of three aliases {M}.", "Alias caveat", [])
    add("S0-0e-05", "0e", "8.8 Landing",
        "and the committed verdict is opposite: the preregistered edge prediction is not supported.",
        f"and the committed verdict is opposite on the alias-named manifold {M}: the preregistered edge prediction is "
        f"not supported.", "Landing statement without the alias caveat", [])
    add("S0-0e-06", "0e", "8.8 alias analysis (new)",
        "**Held-out confirmation.** The fourth commit froze the block, k, the point set, the geodesic matrices,",
        ctx["alias_paragraph"] + "\n\n**Held-out confirmation.** The fourth commit froze the block, k, the point set of "
        f"alias-named prompts {M}, the geodesic matrices,",
        "The CPU computation answering the fifth MUST-FIX", ctx["alias_value_names"])
    add("S0-0e-07", "0e", "8.8",
        "Both lie above the 0.8 flag, and in Qwen3-8B's bf16 geometry unit-weight Dijkstra is also opposite the banned "
        "five.",
        f"Both lie above the 0.8 flag, and in Qwen3-8B's bf16 geometry unit-weight Dijkstra is also opposite the banned "
        f"five (that manifold is built from the same alias-named prompts) {M}.", "Alias caveat", [])
    add("S0-0e-08", "0e", "8.8 Other descriptive geometry",
        "and the off-catalogue survivors (Bellman-Ford, random walk, random-priority search) sit far from every class "
        "cloud (231 to 394).",
        f"and the off-catalogue survivors (Bellman-Ford, random walk, random-priority search) sit far from every class "
        f"cloud (231 to 394). At the one position whose choice does not depend on the label, the unit-Dijkstra survivors "
        f"therefore sit nearest a banned cloud (greedy best-first) rather than opposite the banned five, but that position "
        f"decodes the label at only {P('0e.M2.g16')} against chance 0.25 {M}.", "Connects the F5 fact to the alias caveat", ["0e.M2.g16"])
    add("S0-0e-09", "0e", "8.8 audits",
        "and gives the exact uniform p for opposite as 6.4e-5, (1/5) to the sixth.",
        f"and gives the exact uniform p for opposite as 6.4e-5, (1/5) to the sixth, on the alias-named manifold {M}.",
        "Alias caveat", [])
    add("S0-0e-10", "0e", "8.9",
        "and its catalogue survivors are all unit-weight Dijkstra, the farthest non-banned algorithm from the banned "
        "five, on the screen and on held-out templates.",
        f"and its catalogue survivors are all unit-weight Dijkstra, the farthest non-banned algorithm from the banned "
        f"five, on the screen and on held-out templates. That manifold is built from 300 prompts that each name the "
        f"algorithm by one of three aliases, and {ctx['alias_short']} {M}.", "Alias caveat with the computed result",
        ctx["alias_value_names"])
    add("S0-0e-11", "0e", "8.10 Table 416",
        "| Top-five prohibition claim | One configuration obeys; survivors land opposite, not at the edge; not robust; "
        "confirmed on held-out templates |",
        f"| Top-five prohibition claim | One configuration obeys; survivors land opposite, not at the edge, on the "
        f"alias-named manifold, where names and mechanisms are confounded (Section 8.8) {M}; not robust; confirmed on "
        f"held-out templates |", "Alias caveat", [])
    add("S0-0e-12", "0e", "8.10 Established",
        "and its catalogue survivors are all the algorithm farthest from the banned five on its manifold.",
        f"and its catalogue survivors are all the algorithm farthest from the banned five on its alias-named manifold, "
        f"where {ctx['alias_short']} {M}.", "Alias caveat", ctx["alias_value_names"])
    add("S0-0e-13", "0e", "8.10 Ruled out",
        "The edge prediction for the survivors of the top-five prohibition on the model that obeys.",
        f"The edge prediction for the survivors of the top-five prohibition on the model that obeys, on the alias-named "
        f"manifold {M}.", "Alias caveat", [])
    add("S0-0e-14", "0e", "8.11",
        "tasks where an obeying model writes several catalogue survivors are needed for the edge-against-opposite "
        "question.",
        f"tasks where an obeying model writes several catalogue survivors are needed for the edge-against-opposite "
        f"question, on a manifold whose prompts do not name the algorithm (TP-G), because on the alias-named manifold "
        f"names and mechanisms are confounded {M}.", "Third lead needs a name-free manifold", [])
    add("S0-0e-15", "0e", "What we have learned",
        "Its catalogue survivors are all unit-weight Dijkstra, the farthest non-banned algorithm from the banned five on "
        "its manifold of forced prompts at block 31, so they land on the opposite side, not at the edge as preregistered,",
        f"Its catalogue survivors are all unit-weight Dijkstra, the farthest non-banned algorithm from the banned five on "
        f"its manifold of forced prompts at block 31, so they land on the opposite side, not at the edge as "
        f"preregistered; that manifold is built from prompts that each name the algorithm by one of three aliases, and "
        f"{ctx['alias_short']} {M},", "Alias caveat with the computed result", ctx["alias_value_names"])
    add("S0-0e-16", "0e", "What we have learned",
        "Third, the edge-against-opposite question of the top-five prohibition needs tasks where an obeying model writes "
        "several catalogue survivors.",
        f"Third, the edge-against-opposite question of the top-five prohibition needs tasks where an obeying model writes "
        f"several catalogue survivors, on manifolds whose prompts do not name the algorithm (TP-G), because the alias-named "
        f"manifold confounds names with mechanisms {M}.", "Open question needs a name-free manifold", [])

    # ============================================================================================ 0f Gemma comparators
    add("S0-0f-01", "0f", "8.3",
        "The filtered dial beats global T by +0.08 (p 0.23) and min-p, entropy-triggered and block-start temperature "
        "with p 0.016 to 0.023.",
        f"The filtered dial beats the twin-level fallback of the entropy-triggered family (p {P('0f.G.EDT.p')}) and ties "
        f"global T (+{P('0f.G.globalT.diff')}, p {P('0f.G.globalT.p')}). Min-p and block-start temperature were not run "
        f"on Gemma, and the entropy-triggered arm that was run costs {P('0f.G.A5.pass_cost')} in pass rate, above the "
        f"5-point (0.05) rule, so every family except global T is scored at the twin's Hill of {P('0f.G.twin_hill')} "
        f"(`boot_family_best`, `src/analysis_k1.py`) {M}.",
        "Min-p and block-start were never run on Gemma; their 'wins' were twin-level fallbacks",
        ["0f.G.EDT.p", "0f.G.globalT.diff", "0f.G.globalT.p", "0f.G.A5.pass_cost", "0f.G.twin_hill"])

    # ============================================================================================ 0g figure markers
    for m in ctx["markers"]:
        add(m["edit_id"], "0g", m["section"], m["anchor"], m["anchor"] + "\n\n" + m["block"], m["why"], [])
    return E
