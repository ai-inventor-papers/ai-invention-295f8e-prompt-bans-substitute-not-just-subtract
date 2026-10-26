"""0e: captioned [FIGURE] markers for the seven activation-space geometry plots of iteration 6 (M10).

Captions are taken from the generating code and the text embedded in each PDF, not from regenerating the figures
(the activation caches are not staged here); each caption is tied to its exact file by sha256.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from pypdf import PdfReader

from common import MARK, inp, read_json, read_jsonl, sha256_file

EX, GE, NL = "art_rMlbrjVB1c__", "art_zNyBP6zieI5u", "art_dbUtqBjT0tPf"


def _span(art: str, rel: str, func: str) -> dict:
    src = inp(art, rel).read_text().split("\n")
    start = next(i for i, l in enumerate(src, 1) if re.match(rf"def {func}\(", l))
    end = next((i - 1 for i, l in enumerate(src, 1) if i > start and re.match(r"(def |class |if __name__)", l)), len(src))
    return {"file": f"{art}:{rel}", "function": func, "lines": [start, end]}


def _pdf_text(art: str, rel: str) -> str:
    try:
        return " ".join((p.extract_text() or "") for p in PdfReader(str(inp(art, rel))).pages)
    except Exception as e:  # noqa: BLE001 - a broken PDF must not stop the other figures
        return f"<pdf text extraction failed: {type(e).__name__}>"


def build() -> list[dict[str, Any]]:
    figs: list[dict[str, Any]] = []
    # ---- F5, Qwen3-8B grid task
    t5 = read_json(inp(EX, "results/top5_push.json"))["geometry"]
    e = t5["explained_by_pc1_pc2_of_centroids"]
    n5 = len(t5["points_pc"])
    kinds = Counter(k.split("__")[0] for k in t5["points_pc"])
    figs.append({
        "fig_id": "fig_qwen_top5_geometry", "artifact": EX, "stem": "figures/F5_top5_geometry",
        "code_ref": _span(EX, "src/figures6.py", "f5"),
        "position": "mean over the task-specification positions of each prompt (prefill, before any generated token)",
        "layer": "mean of the block outputs of blocks 12-23, divided by the median block norm",
        "projection": f"(a, b) PCA fitted on the 10 forced-prompt centroids (PC1 {100 * e[0]:.0f}%, PC2 {100 * e[1]:.0f}% "
                      f"of centroid variance); (c) classical MDS of geodesic distances on a k = {t5['mds_geodesic_knn']['k']}"
                      " nearest-neighbour graph (MDS stress not recorded in top5_push.json)",
        "points": f"{n5} prompt states, one per template: " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())),
        "centroids": "10 forced-prompt centroids (mean state of 'Implement <algorithm>' prompts), coloured by the "
                     "prompt-defined top-five ban set (banned five against survivors)",
        "n": n5 + 10, "mds_stress": None,
        "realised_label_dependence": "none: centroids and colours are defined by prompts, not by the programs written",
        "position_after_fork": False,
        "insert_after": "| prompt top-five ban | 50 | 0.62 | 0.50 | 10 (DFS 10, banned) | not computable |",
        "section": "6.4.4"})
    # ---- Gemma: four geometry plots
    gg = read_json(inp(GE, "results/geometry.json"))
    anchors = {"raw|L17": "the forced prompts gave BFS 50 of 50 (38 correct) and DFS 50 of 50 (45 correct).",
               "raw|L22": "| forced DFS | DFS 50 | DFS 45 | 0.90 | n/a |",
               "sae|L17": "| SAE codes, layer 22 | 0.569 | A* and greedy | 43.2 / 44.1 / 61.5 / 83.6 / 43.1 / 72.5 | 0.20 |",
               "sae|L22": "Judge spend was USD 0.034."}
    for key, sp in gg["spaces"].items():
        space, l = key.split("|")
        figs.append({
            "fig_id": f"fig_gemma_geometry_{space}_{l}", "artifact": GE, "stem": f"figures/geometry_{space}_{l}",
            "code_ref": _span(GE, "src/figures_S.py", "geometry"),
            "position": "mean over the task-specification positions (SPEC: from the first token of 'Task:' to the last "
                        "token of the user message, src/cfg.py line 7), so neither the read position nor the fork at "
                        "response index 32 is plotted",
            "layer": f"output of block {l[1:]} (resid_post)" + (", five massive channels zeroed" if space == "raw" else
                                                                ", Gemma Scope 2 SAE codes, log1p"),
            "projection": f"PCA (PC1 {sp['pca_var_explained'][0]:.2f}, PC2 {sp['pca_var_explained'][1]:.2f} of variance), "
                          f"Isomap (k = 10) and classical MDS (stress-1 {sp['mds_stress1']:.3f}), all fitted on the "
                          f"{gg['n_points']} points",
            "points": "prompt states: forced-algorithm prompts by mode, BFS and DFS bans, the top-five ban and its twin, and "
                      "120 neutral variants coloured by y_v, the fork log-odds of BFS measured at response index 32",
            "centroids": "per forced mode, the mean of its forced-prompt points (stars), with marker size growing with the "
                         f"natural implemented count out of 200 ({gg['implemented_counts']})",
            "n": gg["n_points"], "mds_stress": sp["mds_stress1"],
            "realised_label_dependence": "centroid positions none (prompt-defined); centroid marker size from realised "
                                         "labels of the 200 natural samples; variant colour from y_v, a quantity "
                                         "measured at the later fork position (readout target, not a partition)",
            "position_after_fork": False, "insert_after": anchors[key], "section": "6.5"})
    # ---- NLA F6 and F8
    idx = read_jsonl(inp(NL, "cache/states_index.jsonl"))
    read_rows = [r for r in idx if r["kind"] in ("PREFILL", "RAND") and r["position"] == "READ"]
    n6 = len(read_rows)
    figs.append({
        "fig_id": "fig_nla_read_geometry", "artifact": NL, "stem": "figures/F6_geometry",
        "code_ref": _span(NL, "src/figures.py", "f6_geometry"),
        "position": "the read position (last prompt token), before any generated token",
        "layer": "output of block 20 (hidden_states[21], the 'hs21' convention)",
        "projection": "per task, the plane of the first two principal components of that task's forced-prompt READ "
                      "states (SVD after centring on their mean)",
        "points": "single prompt states: forced 'Implement Y' prompts by mode and template, the twin and ban prompts of "
                  "each template (arrow twin to ban), the shortest path seed, twin plus random noise, and NLA edit "
                  "deltas (x1, x2, x4) and a difference-in-means delta (x4) drawn as arrows",
        "centroids": "per forced mode, the mean of its forced READ states (stars); the legend gives forced adherence",
        "n": n6, "mds_stress": None,
        "realised_label_dependence": "none for positions and centroids (prompt-defined); the legend's adherence is "
                                     "behavioural",
        "position_after_fork": False,
        "insert_after": "16 for 6,180 explanations and about 8 for reconstruction passes and the state cache).",
        "section": "6.6"})
    g8 = read_json(inp(NL, "results/geometry.json"))
    n8 = sum(len(v.get("READ", {}).get("mds", {})) for v in g8["tasks"].values())
    figs.append({
        "fig_id": "fig_nla_mds_centroids", "artifact": NL, "stem": "figures/F8_mds_centroids",
        "code_ref": _span(NL, "src/figures.py", "f8_mds"),
        "position": "the read position (last prompt token), before any generated token",
        "layer": "output of block 20 (hidden_states[21])",
        "projection": "classical MDS of the READ centroids per task (MDS stress not recorded in results/geometry.json)",
        "points": "one point per centroid: forced 'Implement Y' centroids, the twin centroid and the ban centroid",
        "centroids": "means of the READ states per forced algorithm, twin and ban; filled area grows with the number of "
                     "twin programs that implemented the algorithm, the dashed ring with the number under the ban",
        "n": n8, "mds_stress": None,
        "realised_label_dependence": "centroid positions none (prompt-defined); marker areas from realised labels of "
                                     "the twin and ban programs",
        "position_after_fork": False,
        "insert_after": "| substring search (to KMP) | 0.03 | 0.00 | 0.07, pass 0.27 | 0/20 | 0:0 | 0:0 | 0:0 | 0.03, pass 0.10 |",
        "section": "6.6"})
    axis_words = ("PC1", "PC2", "MDS", "Isomap", "dim 1", "PCA")
    for f in figs:
        png, pdf = f["stem"] + ".png", f["stem"] + ".pdf"
        f["files"] = [f"{f['artifact']}:{png}", f"{f['artifact']}:{pdf}"]
        f["exists"] = inp(f["artifact"], png).exists() and inp(f["artifact"], pdf).exists()
        f["sha256"] = {png: sha256_file(inp(f["artifact"], png)), pdf: sha256_file(inp(f["artifact"], pdf))}
        txt = _pdf_text(f["artifact"], pdf)
        f["pdf_axis_labels_found"] = [w for w in axis_words if w in txt]
        f["pdf_text_excerpt"] = re.sub(r"\s+", " ", txt)[:300]
        f["caveat"] = ("The plotted position precedes the fork and the generated code; "
                       + f["realised_label_dependence"] + ".")
        f["caption"] = (f"Actual activation coordinates: {f['position']}; {f['layer']}; projection: {f['projection']}. "
                        f"Points: {f['points']}. Centroids: {f['centroids']}. N = {f['n']}. Caveat: {f['caveat']}")
        req = ("position", "layer", "projection", "points", "centroids", "caveat")
        f["caption_fields_present"] = sum(bool(f.get(k)) for k in req)
        f["marker_text"] = f"\n\n[FIGURE:{f['fig_id']}]\n\n*Figure note {MARK}: {f['caption']}*"
    return figs
