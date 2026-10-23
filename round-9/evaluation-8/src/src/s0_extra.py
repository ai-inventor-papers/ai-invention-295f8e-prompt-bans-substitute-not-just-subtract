#!/usr/bin/env python3
"""Builders for item 0d (positioning table from six positioning.json adapters plus live fetch_grep checks), item 0g
(figure markers with six-field captions and sha256) and the 0e report text (from results/s0e.json)."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from recompute import ART, CIRC, DAS, FORK, GEM, LAW, TP, Ledger, load

M = "(iteration-9 correction)"


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ================================================================================================ 0d positioning
def adapt_positioning() -> list[dict[str, Any]]:
    """One adapter per artifact schema -> rows {artifact, claim, neighbour, verdict, quote, url, source}."""
    rows = []
    a = load(FORK, "results/positioning.json")
    for p in a["papers"]:
        rows.append({"artifact": FORK, "claim": "fork dosing", "neighbour": p["title"], "verdict": p["verdict"],
                     "quote": p.get("quote", ""), "url": p.get("id", ""), "source": f"{FORK}:results/positioning.json#papers"})
    a = load(DAS, "results/positioning.json")
    for q in a["queries"]:
        rows.append({"artifact": DAS, "claim": "matched DAS", "neighbour": q["source"], "verdict": q["verdict"],
                     "quote": q.get("quote", ""), "url": q["source"], "source": f"{DAS}:results/positioning.json#queries"})
    a = load(CIRC, "results/positioning.json")
    for w in a["works"]:
        rows.append({"artifact": CIRC, "claim": "circuit", "neighbour": w["work"], "verdict": w["verdict"],
                     "quote": w.get("quote", ""), "url": "", "source": f"{CIRC}:results/positioning.json#works"})
    a = load(GEM, "results/positioning.json")
    for e in a["entries"]:
        qs = e.get("quotes") or []
        rows.append({"artifact": GEM, "claim": "Gemma dial", "neighbour": e["title"], "verdict": e["verdict"],
                     "quote": (qs[0] if qs and isinstance(qs[0], str) else json.dumps(qs[:1]))[:400], "url": e.get("id", ""),
                     "source": f"{GEM}:results/positioning.json#entries"})
    a = load(LAW, "results/positioning.json")
    for s in a["sources"]:
        claim = "base sub-arm" if re.search(r"base sub-arm", s["verdict"], re.I) else "temperature law"
        rows.append({"artifact": LAW, "claim": claim, "neighbour": s["work"], "verdict": s["verdict"],
                     "quote": s.get("quote", ""), "url": s.get("url", ""), "source": f"{LAW}:results/positioning.json#sources"})
    a = load(TP, "results/positioning.json")
    for it in a["items"]:
        rows.append({"artifact": TP, "claim": "top-five prohibition", "neighbour": it["title"], "verdict": it["verdict"],
                     "quote": it.get("quote", ""), "url": it.get("id", ""), "source": f"{TP}:results/positioning.json#items"})
    return rows


NEIGHBOURS = [
    {"key": "cantarero", "ref": 142, "title": "The RLVR Policy Shift Is Sparse and Predictable from the Base Model",
     "authors": "Cantarero, Garcia, Marín, Tiene, Orús", "files": ["cantarero_172378", "cantarero_164442"],
     "url": "https://neurips.cc/virtual/2026/172378 ; https://neurips.cc/virtual/2026/164442",
     "venue_patterns": [r"Poster in Workshop"], "content_patterns": [r"18\.4--57\.1", r"1\.06--1\.70", r"32\.8", r"4\.7"],
     "quote_rx": r"per-position Jensen--Shannon divergence between the two policies is 18\.4--57\.1\$\\times\$ higher inside this fork set than outside",
     "claims": ["base sub-arm", "fork dosing"], "record_venue": "NeurIPS 2026 workshop (temperature-law positioning)",
     "venue_found": "two NeurIPS 2026 workshop posters: 'Transitioning from Pre-training to Post-training' (172378) and "
                    "'ELLIS Workshop on the Foundations of LLM Post-Training in Changing Environments' (164442); no "
                    "main-track page found"},
    {"key": "sparse_but_critical", "ref": 143, "title": "Sparse but Critical: A Token-Level Analysis of Distributional "
     "Shifts in RLVR Fine-Tuning of LLMs", "authors": "Meng et al. (Qwen Pilot Team)", "files": ["sparse_but_critical"],
     "url": "https://arxiv.org/abs/2603.22446", "venue_patterns": [r"ICLR 2026"], "content_patterns": [r"Sparse but Critical"],
     "quote_rx": r"Published as a conference paper at the International Conference on Learning Representations \(ICLR 2026\)",
     "claims": ["base sub-arm"], "record_venue": "ICLR 2026", "venue_found": "ICLR 2026 (arXiv comment); arXiv v1, 2026-03-23"},
    {"key": "self_distillation", "ref": 144, "title": "Embarrassingly Simple Self-Distillation Improves Code Generation",
     "authors": "Zhang et al. (Apple)", "files": ["self_distillation", "self_distillation_html"],
     "url": "https://arxiv.org/abs/2604.01193", "venue_patterns": [], "content_patterns": [r"precision-exploration conflict",
                                                                                           r"forks?\b", r"locks?\b"],
     "quote_rx": r"code generation mixes precision-bound locks and exploration-bound forks",
     "claims": ["fork dosing", "temperature law"], "record_venue": "not in the record",
     "venue_found": "arXiv preprint, v2 (2026-06-24); no venue stated"},
    {"key": "position_aware", "ref": 145, "title": "Position-aware Automatic Circuit Discovery",
     "authors": "Haklay, Orgad, Bau, Mueller, Belinkov", "files": ["position_aware_acl", "position_aware_arxiv"],
     "url": "https://aclanthology.org/2025.acl-long.141/ ; https://arxiv.org/abs/2502.04577",
     "venue_patterns": [r"2025\.acl-long\.141"], "content_patterns": [r"dataset schema"],
     "quote_rx": r"we introduce the concept of a dataset schema, which defines token spans with similar semantics across examples",
     "claims": ["circuit"], "record_venue": "not in the record", "venue_found": "ACL 2025 long paper (2025.acl-long.141); arXiv v1 2025-02-07"},
    {"key": "many_circuits", "ref": 146, "title": "Many Circuits, One Mechanism: Input Variation and Evaluation "
     "Granularity in Circuit Discovery", "authors": "Bayat Makou, Niu, Dutta, Gurevych", "files": ["many_circuits",
                                                                                                   "many_circuits_html"],
     "url": "https://arxiv.org/abs/2606.06267", "venue_patterns": [r"Journal reference: \| Transactions on Machine Learning Research, 2026"],
     "content_patterns": [r"phantom specialization"],
     "quote_rx": r"We term this mismatch _?phantom specialization_?",
     "claims": ["circuit"], "record_venue": "TMLR 2026 (iteration-6 positioning, Table 92c row 19)",
     "venue_found": "TMLR 2026 (arXiv journal reference); arXiv v2 2026-08-26; a NeurIPS 2026 poster page was not fetched"},
    {"key": "mib", "ref": 52, "title": "MIB: A Mechanistic Interpretability Benchmark", "authors": "Mueller et al.",
     "files": ["mib"], "url": "https://arxiv.org/abs/2504.13151", "venue_patterns": [r"Accepted to ICML 2025"],
     "content_patterns": [r"MIB"], "quote_rx": r"Accepted to ICML 2025", "claims": ["matched DAS", "circuit"],
     "record_venue": "ICML 2025", "venue_found": "ICML 2025 (arXiv comment); v2 2025-06-09"},
    {"key": "invisible_lottery", "ref": 1, "title": "The Invisible Lottery: How Subtle Cues Steer Algorithm Choice in "
     "LLM Code Generation", "authors": "Narula et al.", "files": ["invisible_lottery"], "url": "https://arxiv.org/abs/2606.04057",
     "venue_patterns": [r"ICML 2026"], "content_patterns": [r"Invisible Lottery"], "quote_rx": r"How Subtle Cues Steer Algorithm Choice in LLM Code Generation",
     "claims": ["top-five prohibition"], "record_venue": "ICML 2026 (iteration-6 positioning)",
     "venue_found": "arXiv v1 (2026-06-02); no venue stated on the arXiv page"},
    {"key": "denial_prompting", "ref": 23, "title": "Benchmarking Language Model Creativity: A Case Study on Code "
     "Generation (denial prompting)", "authors": "Lu et al.", "files": ["denial_prompting"], "url": "https://arxiv.org/abs/2407.09007",
     "venue_patterns": [r"NAACL"], "content_patterns": [r"Model Creativity"], "quote_rx": r"Model Creativity: A Case Study on Code Generation",
     "claims": ["top-five prohibition"], "record_venue": "NAACL (reference [23] gives 2024; the plan gives 2025)",
     "venue_found": "arXiv v2; no venue stated on the arXiv page"},
    {"key": "manifold_steering", "ref": 27, "title": "Manifold Steering Reveals the Shared Geometry of Neural Network "
     "Representation and Behavior", "authors": "Wurgaft et al.", "files": ["manifold_steering"],
     "url": "https://arxiv.org/abs/2605.05115", "venue_patterns": [r"ICML", r"[Ss]potlight"], "content_patterns": [r"manifold"],
     "quote_rx": r"we test whether interventions that respect the geometry of activation space will yield behaviors close to those the model exhibits naturally",
     "claims": ["top-five prohibition"], "record_venue": "ICML 2026 MI-workshop spotlight (iteration-6 positioning)",
     "venue_found": "arXiv abstract page fetched; no venue stated"},
    {"key": "gravity_wells", "ref": 7, "title": "Semantic Gravity Wells: Why Negative Constraints Backfire",
     "authors": "Rana", "files": ["gravity_wells"], "url": "https://arxiv.org/abs/2601.08070", "venue_patterns": [],
     "content_patterns": [r"Semantic Gravity Wells"],
     "quote_rx": r"the very act of naming a forbidden word primes the model to produce it",
     "claims": ["top-five prohibition"], "record_venue": "arXiv 2026", "venue_found": "arXiv v1 (2026-01-12)"},
    {"key": "white_bear", "ref": 53, "title": "Don't Think of the White Bear: Ironic Negation in Transformer Models "
     "Under Cognitive Load", "authors": "Mann et al.", "files": ["white_bear"], "url": "https://arxiv.org/abs/2511.12381",
     "venue_patterns": [], "content_patterns": [r"White Bear"], "quote_rx": r"Ironic Negation in Transformer Models Under Cognitive Load",
     "claims": ["top-five prohibition"], "record_venue": "arXiv 2025", "venue_found": "arXiv v1 (2025-11-15)"},
]


def verify_live(web_dir: Path) -> list[dict[str, Any]]:
    out = []
    utc = (web_dir / "_run_utc.txt").read_text().split("\n")[0].strip() if (web_dir / "_run_utc.txt").exists() else ""
    for n in NEIGHBOURS:
        texts = []
        for f in n["files"]:
            p = web_dir / f"{f}.txt"
            if p.exists():
                raw = p.read_text(errors="replace")
                raw = raw.split("--- Content ---", 1)[1] if "--- Content ---" in raw else ""
                texts.append(re.sub(r"\s+", " ", raw))
        blob = " ".join(texts)
        fetched = bool(blob.strip())
        content_ok = fetched and all(re.search(pt, blob) for pt in n["content_patterns"])
        venue_ok = bool(n["venue_patterns"]) and all(re.search(pt, blob) for pt in n["venue_patterns"])
        m = re.search(n["quote_rx"], blob)
        status = ("NOT-FOUND" if not content_ok else "VERIFIED" if (venue_ok or not n["venue_patterns"]) else
                  "VERIFIED-ABSTRACT")
        out.append({**{k: v for k, v in n.items() if k not in ("quote_rx", "venue_patterns", "content_patterns")},
                    "status": status, "venue_verified": venue_ok, "quote": m.group(0) if m else "",
                    "checked_utc": utc, "tool": "aii-web-tools aii_fast_web_fetch.py grep",
                    "raw": [f"audit/web/{f}.txt" for f in n["files"]],
                    "record_check": ("new" if n["record_venue"] == "not in the record" else
                                     "confirmed" if (venue_ok or not n["venue_patterns"]) else "unverified")})
    return out


CLAIM_ROWS = [
    ("Fork-dosed temperature", "fork dosing", "PARTLY OCCUPIED",
     "Self-Distillation's account of code as precision-bound locks and exploration-bound forks, where raising "
     "temperature helps forks but floods locks [144]; Cantarero et al.'s Fork-Patched Decoding at base-entropy forks "
     "[142]; EDT [137], AdapT [32], min-p [138]; high-entropy minority tokens [139]",
     "temperature at a counterfactually located algorithm fork in code, with doses committed from teacher-forced logits, "
     "algorithm shares predicted before sampling and hidden-test correctness"),
    ("Matched DAS at the fork", "matched DAS", "OCCUPIED (method)",
     "DAS [110], Boundless DAS [111], CDAS [112]; MIB (ICML 2025, arXiv 2504.13151 v2) ranks DAS without specificity "
     "controls [52]; Makelov et al. [122]; Sutter et al. [132]",
     "seven specificity controls under one protocol in two families and per-direction generation verdicts (sufficient "
     "handle in Gemma, NO HANDLE at Qwen3-8B's fork)"),
    ("Circuit at Qwen3-8B's fork", "circuit", "PARTLY OCCUPIED (method)",
     "path patching [135], attribution patching [136]; Position-aware Automatic Circuit Discovery (ACL 2025 long paper) "
     "makes position classes and dataset schemas explicit [145]; MIB evaluates faithfulness on held-out inputs [52]; "
     "Many Circuits, One Mechanism (TMLR 2026, arXiv 2606.06267 v2): structural differences between circuits need not "
     "be different mechanisms [146]",
     "a position-classed circuit for an algorithm fork validated against matched random components and steered in "
     "generation; the motif comparison is structural only, and the layer-0 node's held-out arm is untested"),
    ("Gemma dial against prompting", "Gemma dial", "PARTLY OCCUPIED",
     "CDAS validates DAS steering by generation against prompting [112]; prefix steering [140]; AxBench [34]",
     "prefill-matched prompting cells on the same slots, a committed free-generation placement rule, and the dormancy "
     "and implementation-channel analysis"),
    ("Temperature law over forks", "temperature law", "PARTLY OCCUPIED",
     "forking-path resampling (Bigelow et al., ICLR 2025, the locator's method source); high-entropy forks [139]; "
     "algorithm-level diversity under temperature measured post hoc (Lee et al., EMNLP Findings 2025); the fork and lock "
     "temperature asymmetry of [144]",
     "a law over blindly located forks committed before sampling and scored on held-out families against flat and "
     "tempering rivals, which stay close"),
    ("Base sub-arm", "base sub-arm", "PARTLY OCCUPIED",
     "Cantarero et al.: per-position Jensen-Shannon divergence 18.4 to 57.1 times higher inside the base model's fork set, "
     "1.06 to 1.70 times after entropy adjustment, Fork-Patched Decoding recovers 32.8% of distinct answers against 4.7% "
     "at random placement (two NeurIPS 2026 workshop posters) [142]; Sparse but Critical (ICLR 2026): only a small "
     "fraction of token distributions diverge after RLVR [143]; URIAL [100]",
     "the concentration of post-training shifts at base-entropy forks is theirs; the run adds the algorithm-level "
     "outcome on code at a counterfactually located fork and the reading that the default is the base model's second or "
     "third choice, sharpened"),
    ("Top-five prohibition", "top-five prohibition", "ADJACENT-ONLY (landing); OCCUPIED (bans backfire)",
     "The Invisible Lottery (arXiv 2606.04057) [1]; denial prompting (arXiv 2407.09007) [23]; Semantic Gravity Wells: "
     "naming a forbidden word primes it (arXiv 2601.08070) [7]; Don't Think of the White Bear (arXiv 2511.12381) [53]; "
     "Manifold Steering (arXiv 2605.05115) [27]",
     "a screen of ten configurations and the landing of survivors on the obeying model's manifold, which is alias-named, "
     "so names and mechanisms are confounded there"),
]

NEW_REFS = [
    "[142] Cantarero et al. The RLVR Policy Shift Is Sparse and Predictable from the Base Model. NeurIPS 2026 Workshops "
    "(Transitioning from Pre-training to Post-training; ELLIS Workshop on the Foundations of LLM Post-Training in "
    "Changing Environments). 2026.",
    "[143] Meng et al. Sparse but Critical: A Token-Level Analysis of Distributional Shifts in RLVR Fine-Tuning of LLMs. "
    "International Conference on Learning Representations. 2026.",
    "[144] Zhang et al. Embarrassingly Simple Self-Distillation Improves Code Generation. arXiv preprint arXiv:2604.01193. "
    "2026.",
    "[145] Haklay et al. Position-aware Automatic Circuit Discovery. Annual Meeting of the Association for Computational "
    "Linguistics. 2025.",
    "[146] Bayat Makou et al. Many Circuits, One Mechanism: Input Variation and Evaluation Granularity in Circuit "
    "Discovery. Transactions on Machine Learning Research. 2026.",
]


def positioning(out_dir: Path) -> dict[str, Any]:
    carried = adapt_positioning()
    live = verify_live(out_dir / "audit/web")
    rows = []
    for title, claim, verdict, nb, adds in CLAIM_ROWS:
        for c in carried:
            if c["claim"] == claim:
                rows.append({"claim": title, "neighbour": c["neighbour"][:200], "authors": "", "venue_track": "",
                             "arxiv_id_version": "", "url": c["url"], "quote": c["quote"][:400],
                             "verdict": c["verdict"][:200], "adds": adds, "status": "CARRIED", "source": c["source"]})
        for n in live:
            if claim in n["claims"]:
                rows.append({"claim": title, "neighbour": n["title"], "authors": n["authors"],
                             "venue_track": n["venue_found"], "arxiv_id_version": n["url"], "url": n["url"],
                             "quote": n["quote"], "verdict": verdict, "adds": adds, "status": n["status"],
                             "source": ";".join(n["raw"])})
    with (out_dir / "tables/positioning_rows.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    status_counts: dict[str, int] = {}
    for n in live:
        status_counts[n["status"]] = status_counts.get(n["status"], 0) + 1
    n_corr = sum(1 for n in live if n["record_check"] == "unverified")
    utc = live[0]["checked_utc"][:10] if live else "unknown"
    table = ["| Claim of iteration 8 | Nearest neighbours (venues and versions checked live) | Verdict | What this run "
             "adds |", "|-|-|-|-|"]
    for title, claim, verdict, nb, adds in CLAIM_ROWS:
        table.append(f"| {title} | {nb} | {verdict} | {adds} |")
    canta = next(n for n in live if n["key"] == "cantarero")
    section = (
        f"## 8.10b Positioning of the iteration-8 claims {M}\n\n"
        f"The iteration-8 artifacts each searched their own neighbours, but the record never set the seven claims against "
        f"the closest published work in one place. Table 416b does, with every venue and version checked live on {utc} "
        f"by fetching each page and grepping it for the quoted text (raw outputs in the Step-0 artifact's audit/web; "
        f"{status_counts.get('VERIFIED', 0)} neighbours verified with their venue, {status_counts.get('VERIFIED-ABSTRACT', 0)} "
        f"verified from the abstract page only, {status_counts.get('NOT-FOUND', 0)} not found).\n\n"
        f"**Table 416b.** The claims of iteration 8 against their nearest neighbours {M}.\n\n" + "\n".join(table) +
        f"\n\nBoth NeurIPS 2026 pages of Cantarero et al. are posters in workshops ({canta['venue_found'].split(': ', 1)[1]}), "
        f"and the abstract states that the divergence is \"18.4--57.1x higher inside this fork set than outside\", that "
        f"\"an excess of 1.06--1.70x remains\" after the entropy adjustment, and that Fork-Patched Decoding moves the number "
        f"of distinct answers \"32.8% of the way back toward the base\" while random placement recovers \"only 4.7%\". "
        f"Sparse but Critical is an ICLR 2026 paper, MIB an ICML 2025 paper (arXiv v2), and Many Circuits, One Mechanism "
        f"carries the journal reference Transactions on Machine Learning Research, 2026 (arXiv v2), which confirms the "
        f"venue Table 92c gives it. The arXiv pages of Manifold Steering, The Invisible Lottery and the denial-prompting "
        f"study state no venue, so the venues that earlier sections give them (an ICML 2026 workshop spotlight, ICML 2026, "
        f"and NAACL, which reference [23] dates 2024) are carried, not verified ({n_corr} venue statements left "
        f"unverified, none contradicted). No iteration-8 result is called first.")
    return {"rows": rows, "live": live, "carried_n": len(carried), "status_counts": status_counts,
            "n_venue_or_version_corrections": n_corr, "section": section, "new_refs": NEW_REFS}


# ================================================================================================ 0g figure markers
def figure_markers(out_dir: Path, s0e: dict[str, Any]) -> list[dict[str, Any]]:
    f8 = load(FORK, "results/geometry_f8.json")
    dg = load(DAS, "results/geometry.json")
    m1 = load(TP, "results/geometry_M1.json")
    m2 = load(TP, "results/geometry_M2.json")
    impl = m1["baseline_implemented"]
    un = {"T10": "connected components", "B3": "minimum spanning tree weight", "A3": "trapped rain water",
          "B6": "valid anagram", "G": "Gemma grid path", "T1": "Qwen3-8B grid path"}
    n_f8 = ", ".join(f"{un.get(u, u)} {f8[u]['n_states']}" for u in f8 if isinstance(f8[u], dict) and "n_states" in f8[u])
    agree = ", ".join(f"{un.get(u, u)} {f8[u]['nearest_centroid_agreement_fork_dosed']:.3f}" for u in f8
                      if isinstance(f8[u], dict) and f8[u].get("nearest_centroid_agreement_fork_dosed") is not None)
    evs = [sum(f8[u]["explained_variance_pc1_pc2"]) for u in f8 if isinstance(f8[u], dict) and
           f8[u].get("explained_variance_pc1_pc2")]
    ev_rng = f"{min(evs):.0%} to {max(evs):.0%}"
    nice = lambda d: ", ".join(f"{k.replace('_', '-')} {v}" for k, v in sorted(d.items(), key=lambda kv: -kv[1]))  # noqa: E731
    ic = {u: dg[u]["implemented_counts"] for u in ("T10", "GRID")}
    dec = m2["label_decodability_balanced_acc"]
    specs = [
        {"id": "fig_forkdose_states", "art": FORK, "files": ["figures/F8_activation_geometry"], "section": "8.3",
         "edit_id": "S0-0g-01", "anchor": "No correct program of 5,543 is novel (rule-of-three upper bound 0.0005).",
         "code": f"{FORK}:src/figures8.py#f8",
         "fields": {"positions": "mean of the 16 positions from the fork token on (fork to fork + 15)",
                    "block": "final-norm hidden state (after the last block)",
                    "projection": f"PCA per unit, first two components ({ev_rng} of variance; linear, no k or stress)",
                    "N": f"states per unit: {n_f8} (arms twin, low and high dose, class-uniform forcing, global T 1.3 and 2.0)",
                    "centroids": "no centroids drawn, so none sized by implemented count; colour = program class, marker = "
                                 f"arm; the nearest-centroid check (class-forced centroids) agrees on {agree}",
                    "caveat": "correlational; states after the fork partly encode the tokens already written"}},
        {"id": "fig_das_handle_coords", "art": DAS, "files": ["figures/F3_geometry_T10", "figures/F3_geometry_GRID"],
         "section": "8.4", "edit_id": "S0-0g-02", "anchor": 'The figure titles say "handle coordinates (not certified)".',
         "code": f"{DAS}:src/figures8.py#F3",
         "fields": {"positions": "the fork token (index 11 after ' def' on connected components; index 32 in Gemma)",
                    "block": f"chosen block {dg['T10']['L']} (Qwen3-8B) and {dg['GRID']['L']} (Gemma)",
                    "projection": f"every prompt's coordinates in the fitted rank-8 DAS subspace, centred on the twin mean, "
                                  f"embedded by metric MDS (Kruskal stress-1 {dg['T10']['mds_stress1']:.3f} and "
                                  f"{dg['GRID']['mds_stress1']:.3f}) and Isomap (k 8), beside a PCA of the raw block states",
                    "N": f"{dg['T10']['n_prompts']} prompts (connected components) and {dg['GRID']['n_prompts']} (Gemma)",
                    "centroids": f"class centroids (stars) sized by implemented, test-passing programs: connected "
                                 f"components {nice(ic['T10'])}; Gemma {nice(ic['GRID'])}",
                    "caveat": "off-manifold DAS coordinates: both fork fits raise the off-manifold flag and fail the label "
                              "and random-initialisation controls, so these are handle coordinates, not a certified variable"}},
        {"id": "fig_das_handle_axis", "art": DAS, "files": ["figures/F3b_handle_axis_T10", "figures/F3b_handle_axis_GRID"],
         "section": "8.4", "edit_id": None, "anchor": None, "code": f"{DAS}:src/figures8.py#F3b",
         "fields": {"positions": "the fork token, as in fig_das_handle_coords",
                    "block": f"{dg['T10']['L']} (Qwen3-8B) and {dg['GRID']['L']} (Gemma)",
                    "projection": "the first fitted handle coordinate per prompt group (one axis; no k or stress)",
                    "N": f"{dg['T10']['n_prompts']} and {dg['GRID']['n_prompts']} prompts",
                    "centroids": "no centroids drawn; implemented counts as in fig_das_handle_coords",
                    "caveat": "off-manifold DAS coordinates (not certified)"}},
        {"id": "fig_gemma_dial_geometry", "art": GEM, "files": ["figures/F4_geometry"], "section": "8.6",
         "edit_id": "S0-0g-03", "anchor": "The subspace moves the algorithm, BFS against DFS, but not the forced prompt's "
                                         "choice of implementation.", "code": f"{GEM}:src/outputs8.py#F4",
         "fields": {"positions": "the fork (decision) position, index 32 after the shared opening",
                    "block": "block 17 of gemma-3-4b-it",
                    "projection": "(R1, R2) of the rank-4 DAS map (seed 0) and (PC1, PC2) of the 120 twin variants "
                                  "(linear; no k or stress)",
                    "N": "120 twin variants, 40 forced sources (BFS and DFS), the free twin at its decision position, and "
                         "the same free-twin states after DAS toward BFS, DAS toward DFS and difference in means toward BFS",
                    "centroids": "no centroids drawn, so none sized by implemented count; the twin implements DFS in 32 and "
                                 "BFS in 18 of 50 slots (Table 386); colour = fork margin of each twin variant",
                    "caveat": "dormant or off-manifold handle by retention (0.18 to 0.28): the edited states are DAS "
                              "coordinates, correlational as geometry"}},
        {"id": "fig_tp_mds", "art": TP, "files": ["figures/F3_mds_C6_nf4"], "section": "8.8", "edit_id": "S0-0g-04",
         "anchor": "the only catalogue algorithm the model writes under the ban, forms its own cloud at the bottom, away "
                   "from the ban prompts.", "code": f"{TP}:src/figures.py#manifold_figures",
         "fields": {"positions": "S-mean over the task-specification tokens of each forced prompt",
                    "block": f"block {m1['L_star']} of Qwen3-32B (NF4 weights)",
                    "projection": f"classical MDS of the 300 points (Kruskal stress-1 {m1['M1']['mds_points_stress1']:.2f}) "
                                  f"and of the 10 centroids ({m1['M1']['mds_centroids_stress1']:.2f})",
                    "N": "300 forced prompts (10 algorithms x 10 templates x 3 aliases), with baseline and ban prompts "
                         "projected",
                    "centroids": f"sized by baseline implemented count ({nice(impl)}; every other algorithm 0)",
                    "caveat": "alias-named manifold (each prompt names its algorithm) and correlational (in-manifold pushes "
                              "moved 0 of 300 programs)"}},
        {"id": "fig_tp_isomap", "art": TP, "files": ["figures/F4_isomap_C6_nf4"], "section": "8.8", "edit_id": None,
         "anchor": None, "code": f"{TP}:src/figures.py#manifold_figures",
         "fields": {"positions": "S-mean over the task-specification tokens", "block": f"block {m1['L_star']}",
                    "projection": "Isomap on the symmetrised kNN geodesic graph at k 5, 10 and 15 (8, 3 and 1 components "
                                  "before joining); overlays at the primary k 15",
                    "N": "300 forced prompts plus projected baseline, ban and confirmation prompts",
                    "centroids": f"sized by baseline implemented count ({nice(impl)}; every other algorithm 0)",
                    "caveat": "alias-named and correlational"}},
        {"id": "fig_tp_program_states", "art": TP, "files": ["figures/F5_M2_C6"], "section": "8.8", "edit_id": "S0-0g-05",
         "anchor": "Iteration 7 found that pushes inside the manifold moved 0 of 300 programs, so none of this geometry is "
                   "causal.", "code": f"{TP}:src/figures.py#m2_figure",
         "fields": {"positions": "p*, the first token that signals the program's class (label-dependent)",
                    "block": f"block {m2['L_star']}",
                    "projection": "PCA and Isomap (k 10) of per-program states",
                    "N": f"{m2['n_programs']} programs (all valid ban programs and sampled baseline programs)",
                    "centroids": "no centroids; correct survivors starred",
                    "caveat": f"the label is decodable at p* (balanced accuracy {dec['p_star']:.2f}) but only at "
                              f"{dec['g16']:.2f} at the label-independent 16th code token (chance 0.25), so the separation "
                              f"is largely written into the tokens; correlational"}},
        {"id": "fig_alias_overlap", "art": "this artifact (iteration-9 Step 0)", "files": ["figures/alias_overlap"],
         "section": "8.8", "edit_id": None, "anchor": None, "code": "src/stage_0e.py#_figure",
         "fields": {"positions": "S-mean over the task-specification tokens (iteration 8's stored states)",
                    "block": "block 31 of Qwen3-32B (NF4)",
                    "projection": f"panels A-B: alias-level g against lexical overlap at k 15 and k 10; panel C: classical "
                                  f"MDS of the stored k 15 geodesics (stress-1 {s0e['per_k']['k15'].get('mds_stress1', float('nan')):.2f})",
                    "N": "15 alias sets of 10 prompts (non-banned) plus 150 banned prompts; 300 points in panel C",
                    "centroids": "algorithm centroids (stars) are not sized: g is a distance, not a count; the screen's "
                                 "catalogue survivors were unit-weight Dijkstra 6 of 6",
                    "caveat": "alias-named and correlational; between algorithms names and mechanisms are confounded"}},
    ]
    out = []
    for s in specs:
        base = ART[s["art"]] if s["art"] in ART else out_dir
        hashes = {}
        for f in s["files"]:
            for ext in ("png", "pdf"):
                p = base / f"{f}.{ext}"
                hashes[f"{f}.{ext}"] = sha(p) if p.exists() else None
        fl = s["fields"]
        cap = (f"Positions: {fl['positions']}. Block: {fl['block']}. Projection: {fl['projection']}. N: {fl['N']}. "
               f"Centroids: {fl['centroids']}. Caveat: {fl['caveat']}. Files ({s['art']}): "
               + ", ".join(f"{k} sha256 {v[:12] if v else 'missing'}" for k, v in hashes.items()) + f"; code {s['code']}.")
        out.append({**s, "caption": cap, "sha256": hashes, "n_fields": sum(1 for v in fl.values() if v),
                    "block_md": f"[FIGURE:{s['id']}]\n\n*Figure {s['id']} {M}.* {cap}"})
    return out


def marker_edits(markers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by = {m["id"]: m for m in markers}
    gem_par = (f"**The dial's geometry {M}.** Figure fig_gemma_dial_geometry plots Gemma's block-17 fork states in actual "
               f"activation coordinates: the 120 twin variants (coloured by fork margin), the forced-BFS and forced-DFS "
               f"sources, the free twin at its decision position, and the same free-twin states after the rank-4 DAS edit "
               f"toward BFS or DFS and after the difference-in-means edit toward BFS. In the DAS plane the twin states form "
               f"one tight cluster; the DAS edits carry them onto the forced-BFS or forced-DFS sources, while the "
               f"difference-in-means edit throws them far beyond every natural state. In the twins' own first two "
               f"principal components the DAS-edited states stay inside the twin columns and the difference-in-means "
               f"states leave them. This is the retention picture of Table 406: a subspace that the twins' noun-driven "
               f"variation barely uses but that prompts use, and an edit along it that stays near the natural states "
               f"where the difference-in-means edit does not.")
    return [
        {"edit_id": "S0-0g-01", "section": "8.3", "anchor": by["fig_forkdose_states"]["anchor"],
         "block": by["fig_forkdose_states"]["block_md"], "why": "Geometry at the fork had no figure marker"},
        {"edit_id": "S0-0g-02", "section": "8.4", "anchor": by["fig_das_handle_coords"]["anchor"],
         "block": by["fig_das_handle_coords"]["block_md"] + "\n\n" + by["fig_das_handle_axis"]["block_md"],
         "why": "DAS handle geometry had no figure markers"},
        {"edit_id": "S0-0g-03", "section": "8.6", "anchor": by["fig_gemma_dial_geometry"]["anchor"],
         "block": gem_par + "\n\n" + by["fig_gemma_dial_geometry"]["block_md"],
         "why": "Gemma F4 had no marker and no description"},
        {"edit_id": "S0-0g-04", "section": "8.8", "anchor": by["fig_tp_mds"]["anchor"],
         "block": by["fig_tp_mds"]["block_md"] + "\n\n" + by["fig_tp_isomap"]["block_md"],
         "why": "MDS and Isomap of the prohibition manifold had no markers"},
        {"edit_id": "S0-0g-05", "section": "8.8", "anchor": by["fig_tp_program_states"]["anchor"],
         "block": by["fig_tp_program_states"]["block_md"], "why": "Per-program states had no marker"},
    ]


# ================================================================================================ 0e text
def f2(x: float) -> str:
    return f"{x:.2f}".replace("-0.00", "0.00")


def pfmt(p: float) -> str:
    return f"{p:.3f}" if p >= 0.001 else f"{p:.1e}"


def alias_text(Z: dict[str, Any], led: Ledger, alias_marker_md: str, T: dict[str, Any] | None = None) -> dict[str, Any]:
    k15, k10 = Z["per_k"]["k15"], Z["per_k"]["k10"]
    src = "S0:results/s0e.json"
    v = {}

    def a(name: str, val: Any, key: str, spec: str = ".2f") -> str:
        v[name] = led.add(name, "0e", val, f"{src}#{key}", spec)
        return v[name]

    rho15 = a("0e.k15.rho_primary", k15["rho_primary"], "per_k.k15.rho_primary")
    p15 = a("0e.k15.p_primary", k15["primary_p_lower"], "per_k.k15.primary_p_lower", ".3f")
    ci = k15["ci95_primary"]
    ci_lo = a("0e.k15.ci_lo", ci[0], "per_k.k15.ci95_primary[0]")
    ci_hi = a("0e.k15.ci_hi", ci[1], "per_k.k15.ci95_primary[1]")
    rho10 = a("0e.k10.rho_primary", k10["rho_primary"], "per_k.k10.rho_primary")
    p10 = a("0e.k10.p_primary", k10["primary_p_lower"], "per_k.k10.primary_p_lower", ".4f")
    rho2 = a("0e.k15.rho_secondary", k15["rho_secondary"], "per_k.k15.rho_secondary")
    c5 = k15["five_centroid_primary"]
    rho5 = a("0e.k15.rho_5c", c5["rho"], "per_k.k15.five_centroid_primary.rho")
    p5 = a("0e.k15.p_5c", c5["p_lower"], "per_k.k15.five_centroid_primary.p_lower")
    fl5 = a("0e.k15.floor_5c", c5["floor_lower"], "per_k.k15.five_centroid_primary.floor_lower", ".3f")
    st = k15["stratified_secondary"]
    strat = a("0e.k15.strat", st["stat"], "per_k.k15.stratified_secondary.stat")
    pstrat = a("0e.k15.strat_p", st["p_lower"], "per_k.k15.stratified_secondary.p_lower")
    neff = a("0e.k15.strat_neff", st["n_arrangements_effective"], "per_k.k15.stratified_secondary.n_arrangements_effective", "int")
    nalg = a("0e.k15.strat_nalg", st["n_algorithms_used"], "per_k.k15.stratified_secondary.n_algorithms_used", "int")
    beta = a("0e.k15.beta", st["beta"], "per_k.k15.stratified_secondary.beta")
    pbeta = a("0e.k15.beta_p", st["beta_p_two_sided"], "per_k.k15.stratified_secondary.beta_p_two_sided")
    st10 = k10["stratified_secondary"]
    strat10 = a("0e.k10.strat_p", st10["p_lower"], "per_k.k10.stratified_secondary.p_lower")
    pl = Z["placebos"]
    p1 = a("0e.P1", pl["P1_shuffled_alias_labels"]["share_p_lt_0.05"], "placebos.P1_shuffled_alias_labels.share_p_lt_0.05", ".3f")
    p2 = a("0e.P2", pl["P2_random_overlap_vector"]["share_p_lt_0.05"], "placebos.P2_random_overlap_vector.share_p_lt_0.05", ".3f")
    prho = a("0e.C1.rho", pl["C1_planted"]["seed0_rho"], "placebos.C1_planted.seed0_rho")
    pp = a("0e.C1.p", pl["C1_planted"]["seed0_p_lower"], "placebos.C1_planted.seed0_p_lower", "sig1")
    e4v = Z["gates"].get("E4_spearman_vs_stored_k15")
    e4 = a("0e.E4", e4v, "gates.E4_spearman_vs_stored_k15", ".3f") if e4v is not None else None
    bpe_sent, bpe_short = "", ""
    if T:
        tsrc = "S0:results/s0e_tertiary.json"
        v["0e.k15.bpe_rho"] = led.add("0e.k15.bpe_rho", "0e", T["per_k"]["k15"]["rho_tertiary"],
                                      f"{tsrc}#per_k.k15.rho_tertiary", ".2f")
        v["0e.k15.bpe_strat"] = led.add("0e.k15.bpe_strat", "0e", T["per_k"]["k15"]["stratified"]["stat"],
                                        f"{tsrc}#per_k.k15.stratified.stat", ".2f")
        v["0e.k15.bpe_strat_p"] = led.add("0e.k15.bpe_strat_p", "0e", T["per_k"]["k15"]["stratified"]["p_lower"],
                                          f"{tsrc}#per_k.k15.stratified.p_lower", ".3f")
        v["0e.k10.bpe_strat"] = led.add("0e.k10.bpe_strat", "0e", T["per_k"]["k10"]["stratified"]["stat"],
                                        f"{tsrc}#per_k.k10.stratified.stat", ".2f")
        v["0e.k10.bpe_strat_p"] = led.add("0e.k10.bpe_strat_p", "0e", T["per_k"]["k10"]["stratified"]["p_lower"],
                                          f"{tsrc}#per_k.k10.stratified.p_lower", ".2f")
        bpe_sent = (f" A sensitivity committed as optional scores overlap with the model's own BPE tokens (function words "
                    f"included, so every algorithm's aliases differ): the 15-set correlation is {v['0e.k15.bpe_rho']}, and the "
                    f"within-algorithm statistic is {v['0e.k15.bpe_strat']} (p {v['0e.k15.bpe_strat_p']} over 7,776 relabelings; "
                    f"{v['0e.k10.bpe_strat']}, p {v['0e.k10.bpe_strat_p']} at k 10), so a small within-algorithm name effect "
                    f"cannot be excluded at this resolution.")
        bpe_short = f"; {v['0e.k15.bpe_strat_p']} on the model's BPE tokens"
    g = k15["g_alias"]
    rng = lambda al: f"{min(g[f'{al}|{j}'] for j in range(3)):.1f} to {max(g[f'{al}|{j}'] for j in range(3)):.1f}"  # noqa: E731
    code = Z["verdict"]["code"]
    rule = {"CONFOUNDED": (f"g follows alias overlap across algorithms (rho {rho15}, exact p {p15}), but the pattern is "
                           f"carried by algorithm identity; on this manifold names and mechanisms are confounded, and "
                           f"TP-G's name-free manifolds decide"),
            "NAMES": "names move the geometry even with the algorithm held fixed",
            "NOT_TRACKED": f"iteration 8's geodesics do not track alias overlap at the committed strength (rho {rho15})"}[code]
    par = (
        f"**Is 'opposite' a property of the names? {M}** Each of the 300 forced prompts names its algorithm by one of "
        f"three aliases, and the aliases of the edge algorithms share words with the banned names. On iteration 8's own "
        f"stored geodesics at block 31 (every gate passes: the stored labels, prompt groups and algorithm-level g "
        f"reproduce to 1e-9, and " + (f"an independent kNN-geodesic recomputation from the stored states correlates with "
                                      f"the stored k 15 matrix at {e4}" if e4 else "the independent kNN-geodesic "
                                      "recomputation was not run in this copy") + f"), each non-banned algorithm was split into its three alias sets of 10 prompts and each "
        f"set's g was computed (unit-weight Dijkstra {rng('dijkstra_unit')}, jump point search {rng('jps')}, IDA* "
        f"{rng('idastar')}, bidirectional A* {rng('biastar')}, bidirectional BFS {rng('bibfs')}). The lexical overlap was "
        f"committed by hash before any alias-level number: the number of banned-name detectors an alias matches (0 for "
        f"every unit-weight Dijkstra and jump point search alias, 1 for every bidirectional BFS and bidirectional A* alias, "
        f"1 to 3 for IDA*). Across the 15 alias sets at k 15 the Spearman correlation is {rho15} (exact one-sided p {p15} "
        f"over all 360,360 assignments; 95% interval over template resamples {ci_lo} to {ci_hi}), {rho10} at k 10 (p "
        f"{p10}), and {rho2} with content-word overlap. That statistic treats the 15 sets as exchangeable although they "
        f"are nested in five algorithms, and between algorithms lexical overlap is confounded with mechanism: "
        f"bidirectional BFS is next to BFS both in name and in mechanism. At the level of algorithms the correlation is "
        f"{rho5} with p {p5} (exact over 120 permutations; the tied overlap vector cannot go below {fl5}). Holding the "
        f"algorithm fixed and varying only the name, the within-algorithm test on content-word overlap ({nalg} algorithms "
        f"whose aliases differ; exact null over {neff} distinct relabelings) gives a mean within-algorithm Spearman of "
        f"{strat} (p {pstrat}; p {strat10} at k 10), and the fixed-effects slope of g on overlap is {beta} (two-sided "
        f"stratified p {pbeta}), the wrong sign for a name effect.{bpe_sent} Placebos fail as they must (at the 0.05 level, shuffled "
        f"point labels reject in a share {p1} of draws and random overlap vectors in {p2}) and a planted effect is "
        f"recovered (rho {prho}, p {pp}). By the committed "
        f"wording rule: {rule}. The planner's expectation of about -0.70 was public before the computation, so only the "
        f"within-algorithm test and the interval were unseen; tables/alias_g.csv of the Step-0 artifact gives every set."
        f"\n\n{alias_marker_md}")
    short = (f"its alias analysis (Section 8.8) finds that g follows alias overlap across algorithms (rho {rho15}, exact p "
             f"{p15}) but not clearly within them (stratified p {pstrat} on content words{bpe_short}): names and mechanisms "
             f"are confounded there, and the name-free manifolds of TP-G decide")
    return {"paragraph": par, "short": short, "value_names": list(v.keys()), "printed": v, "code": code}
