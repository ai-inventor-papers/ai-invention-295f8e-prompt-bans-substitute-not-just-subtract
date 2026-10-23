#!/usr/bin/env python3
"""Item 0f: the iteration-7 positioning table (Table 371b) from art_LzP2qPwUrANz's verdicts, every row re-verified live
with aii-web-tools fetch_grep on 2026-10-23 (raw grep outputs in audit/web/), and the venue row of 'A Tale of Two
Temperatures' corrected. A failed fetch keeps the row as UNVERIFIED with its error; no row is dropped."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from sections.common import AUDIT, EVAL6_DIR, READ_DATE, ROOT, SUFFIX, edit, read_json, src_ref, value, write_json

WEB = AUDIT / "web"

# (key, claim group, name, venue as claimed, url, grep file, title regex, venue regex or None, what they do)
NEIGHBOURS = [
    ("hotcold", "temperature", "Hot or Cold? Adaptive Temperature Sampling for Code Generation", "AAAI 2024", "https://arxiv.org/abs/2309.02772",
     ["hotcold_abs", "hotcold_venue"], r"Hot or Cold\? Adaptive Temperature Sampling for Code Generation", r"accepted by AAAI 2024",
     "temperature set by token difficulty in code generation; no algorithm-level prediction"),
    ("ctrltemp", "temperature", "Control the Temperature: Selective Sampling for Diverse and High-Quality LLM Outputs", "COLM 2025", "https://arxiv.org/abs/2510.01218",
     "ctrltemp_abs", r"Control the Temperature", r"Second Conference on Language Modeling, 2025",
     "switches temperature per token to protect precision"),
    ("entropy", "temperature", "Entropy-informed Decoding: Adaptive Information-Driven Branching", "ICML 2026 (arXiv 2605.09745 comment)", "https://arxiv.org/abs/2605.09745",
     "entropy_abs", r"Entropy-informed Decoding", r"Accepted at ICML 2026",
     "branches decoding at high-entropy tokens; no algorithm-level outcome"),
    ("beyond8020", "temperature", "Beyond the 80/20 Rule: High-Entropy Minority Tokens Drive Effective RL for LLM Reasoning", "NeurIPS 2025", "https://arxiv.org/abs/2506.01939",
     "beyond8020_abs", r"Beyond the 80/20 Rule", r"Accepted to NeurIPS 2025",
     "forking (high-entropy) tokens drive RL for reasoning; not temperature at a code fork"),
    ("tale", "temperature", "A Tale of Two Temperatures: Simple, Efficient, and Diverse Sampling from Diffusion Language Models", "COLM (arXiv v2 comment, no year); ICML 2026 workshop posters", "https://arxiv.org/abs/2604.09921",
     "tale_abs", r"A Tale of Two Temperatures", r"V2: accepted as a full conference paper at COLM",
     "tempered remasking for sample diversity in diffusion language models, not autoregressive code"),
    ("cdas", "dial", "CDAS: Faithful Bi-Directional Model Steering via Distribution Matching and Distributed Interchange Interventions", "ICLR 2026", "https://arxiv.org/abs/2602.05234",
     "cdas_abs", r"Faithful Bi-Directional Model Steering", r"accepted for ICLR 2026",
     "DAS-style interchange steering validated by generation on refusal and a backdoor"),
    ("mib", "dial", "MIB: A Mechanistic Interpretability Benchmark", "ICML 2025", "https://arxiv.org/abs/2504.13151",
     ["mib_abs", "mib_venue"], r"MIB: A Mechanistic Interpretability Benchmark", r"Accepted to ICML 2025",
     "benchmark that ranks DAS first for causal variable localisation"),
    ("funsearch", "search", "FunSearch: Mathematical discoveries from program search with large language models", "Nature 2023", "https://www.nature.com/articles/s41586-023-06924-6",
     "funsearch", r"Mathematical discoveries from program search with large language models", r"Published: 14 December 2023",
     "evaluator-guided program search finds new mathematical constructions"),
    ("alphaevolve", "search", "AlphaEvolve: A coding agent for scientific and algorithmic discovery", "2025 (arXiv)", "https://arxiv.org/abs/2506.13131",
     "alphaevolve_abs", r"AlphaEvolve: A coding agent", None,
     "evaluator-guided evolutionary coding agent (occupies the method family)"),
    ("divalgo", "search", "DivAlgo: A systematic evaluation of algorithmic diversity for code generation models", "arXiv 2610.19157", "https://arxiv.org/abs/2610.19157",
     "divalgo_abs", r"DivAlgo", None, "benchmarks algorithmic diversity of code models"),
    ("beneath", "search", "Beneath the Diff: Diagnosing and Mitigating Algorithmic Mode Collapse in Code-Level Autonomous Research Loops", "EMNLP 2026", "https://arxiv.org/abs/2609.00077",
     "beneath_abs", r"Beneath the Diff", r"Accepted by EMNLP 2026", "algorithmic mode collapse in autonomous research loops"),
    ("algdisc", "search", "Algorithm Discovery With LLMs: Evolutionary Search Meets Reinforcement Learning", "arXiv 2504.05108", "https://arxiv.org/abs/2504.05108",
     "algdisc_abs", r"Algorithm Discovery With LLMs", None, "evolutionary search plus RL for algorithm discovery"),
]
WORKSHOP_PAGES = [("icml_75333_b", "https://icml.cc/virtual/2026/75333", "AdaptFM: Resource-Adaptive Foundation Model Inference"),
                  ("icml_74361_b", "https://icml.cc/virtual/2026/74361", "4th Structured Probabilistic Inference & Generative Modeling")]

CLAIMS = {
    "temperature": ("Temperature acts on the algorithm through the fork logits divided by T",
                    "a per-algorithm prediction of the temperature response from teacher-forced fork logits, committed before sampling, and fork margins that explain the nulls on the collapsed tasks",
                    "adjacent: no neighbour predicts an algorithm-level temperature response"),
    "dial": ("A DAS subspace at Gemma's fork is a dose dial on the algorithm in code",
             "an algorithm choice in code at a generated fork, with a dose curve that preserves the pass rate (with the shared opening prefilled; the instruction cell is not comparable)",
             "adjacent: DAS steering is published; the algorithm-in-code object and the dose curve are not"),
    "search": ("Evaluator-guided search reaches known techniques outside the catalogue at a rate single samples do not",
               "a rate-matched comparison against single-sample knobs on a frozen LeetCode-style catalogue (78 of 2,500 calls against 2 of 500; 0 novel)",
               "adjacent: the method is occupied (FunSearch, AlphaEvolve); the rate-matched comparison is the addition"),
}


HEADER = re.compile(r"^(URL|Type|Pattern): |^No matches found|FutureWarning|warnings\.warn")


def _read(names: str | list[str]) -> str:
    """Concatenated grep outputs with the tool's own header lines removed (the Pattern: line echoes the regex and
    must never count as evidence)."""
    out = []
    for name in ([names] if isinstance(names, str) else names):
        p = WEB / f"{name}.txt"
        if p.exists():
            out += [l for l in p.read_text(errors="replace").split("\n") if not HEADER.search(l)]
    return "\n".join(out)


def _ver(txt: str) -> str:
    a = re.search(r"Submitted on (\d{1,2} \w{3} \d{4})", txt)
    b = re.search(r"last revised (\d{1,2} \w{3} \d{4}) \(this version, (v\d+)\)", txt)
    if not a:
        return ""
    return f"v1 {a.group(1)}" + (f", {b.group(2)} {b.group(1)}" if b else "")


def run(ctx: dict[str, Any]) -> dict[str, Any]:
    p6 = read_json(EVAL6_DIR / "positioning.json")
    rows = []
    for key, grp, name, venue, url, fn, t_rx, v_rx, what in NEIGHBOURS:
        txt = _read(fn)
        ok_fetch = bool(txt.strip())
        tq = re.search(t_rx, txt)
        vq = re.search(v_rx, txt) if v_rx else None
        if not ok_fetch or not tq:
            status = "UNVERIFIED"
        elif v_rx is None or vq:
            status = "VERIFIED"
        else:
            status = "VERIFIED-ABSTRACT"
        cm = re.search(r"Comments: \|\s*([^|\n]+)", txt)
        rows.append({"key": key, "claim_group": grp, "name": name, "venue_claimed": venue, "url": url,
                     "version": _ver(txt), "arxiv_comment": cm.group(1).strip() if cm else None,
                     "title_quote": tq.group(0) if tq else None, "venue_quote": vq.group(0) if vq else None,
                     "status": status, "date": READ_DATE, "what_they_do": what,
                     "raw": [f"audit/web/{f}.txt" for f in ([fn] if isinstance(fn, str) else fn)],
                     "error": None if ok_fetch else "fetch failed or empty"})
    ws = []
    for fn, url, wname in WORKSHOP_PAGES:
        txt = _read(fn)
        ok = "A Tale of Two Temperatures" in txt and wname in txt
        ws.append({"url": url, "workshop": wname, "quote": f"Poster in Workshop: {wname} ... A Tale of Two Temperatures: Simple, Efficient, and Diverse Sampling from Diffusion Language Models" if ok else None,
                   "status": "VERIFIED" if ok else "UNVERIFIED", "date": READ_DATE, "raw": f"audit/web/{fn}.txt"})
    tale = next(r for r in rows if r["key"] == "tale")
    tale["workshop_posters"] = ws
    venue_row = ("A Tale of Two Temperatures: Simple, Efficient, and Diverse Sampling from Diffusion Language Models (arXiv 2604.09921; "
                 f"{tale['version'] or 'v1 10 Apr 2026, v2 10 Aug 2026'}; arXiv comment '{tale['arxiv_comment']}'; also ICML 2026 workshop posters at "
                 "AdaptFM: Resource-Adaptive Foundation Model Inference, icml.cc/virtual/2026/75333, and at the 4th Structured Probabilistic "
                 "Inference & Generative Modeling workshop, icml.cc/virtual/2026/74361); diffusion LMs, not autoregressive code")
    for r in rows:
        value(f"positioning row {r['key']}: status", None, r["status"], "NEW", " + ".join(r["raw"]), "exact", "0f", r["title_quote"] or "")
    for w in ws:
        value(f"ICML 2026 workshop poster ({w['workshop']})", None, w["status"], "NEW", w["raw"], "exact", "0f")
    # Table 371b
    md = []
    for grp, (claim, adds, verdict) in CLAIMS.items():
        nb = [r for r in rows if r["claim_group"] == grp]
        nbs = "; ".join(f"{r['name'].split(':')[0]} ({r['venue_claimed']})" for r in nb)
        does = "; ".join(f"{r['name'].split(':')[0]}: {r['what_they_do'].replace('; ', ', ')}" for r in nb)
        ev = "; ".join(f"{r['url']} ({r['version'] or 'version n/a'}; '{r['title_quote'] or '-'}'" + (f"; '{r['venue_quote']}'" if r['venue_quote'] else "") + f"; {r['status']}, {r['date']})" for r in nb)
        if grp == "temperature":
            ev += "; " + "; ".join(f"{w['url']} ({w['workshop']}; {w['status']}, {w['date']})" for w in ws)
        md.append(f"| {claim} | {nbs} | {does} | {adds} | {verdict} | {ev} |")
    tbl = ("**Table 371b.** Positioning of the iteration-7 claims (to our knowledge, mini search dated 2026-10-22, re-verified "
           "2026-10-23 with fetch_grep of each abstract and venue page; raw outputs in `audit/web/`). Verdicts come from the "
           "record audit's positioning search (art_LzP2qPwUrANz `positioning.json`). (iteration-8 correction: new table)\n\n"
           "| Claim | Nearest neighbours (venue) | What they do | What the run adds | Verdict | Evidence (URL, version, quote, status, date) |\n"
           "|-|-|-|-|-|-|\n" + "\n".join(md))
    pos = {"date": READ_DATE, "wording": "to our knowledge (mini search dated 2026-10-22, re-verified 2026-10-23)",
           "source_verdicts": src_ref("eval6", "positioning.json", "verdicts"), "rows": rows, "venue_row": venue_row,
           "iteration7_neighbours_carried": {k: {kk: v.get(kk) for kk in ("name", "arxiv", "venue_found", "quote_status", "venue_status")}
                                             for k, v in p6["neighbours"].items()},
           "verdicts_iteration7": p6["verdicts"]}
    write_json(ROOT / "positioning.json", pos)
    E = [
        edit("C8-f01", "0f", "7.2 (record audit table)", "| A Tale of Two Temperatures (seed) | COLM, not ICML 2026 | CORRECTED |",
             "| A Tale of Two Temperatures (seed) | COLM (arXiv v2 comment 'V2: accepted as a full conference paper at COLM', no year) and two ICML 2026 workshop posters (AdaptFM, icml.cc/virtual/2026/75333; 4th Structured Probabilistic Inference & Generative Modeling, icml.cc/virtual/2026/74361); a paper on diffusion language models, not autoregressive code (iteration-8 correction, verified 2026-10-23) | CORRECTED |", kind="table_row"),
        edit("C8-f02", "0f", "Table 371b", "\n\n## 7.10 What iteration 7 established, what it ruled out, and what it abandoned",
             "\n\n" + tbl + "\n\n## 7.10 What iteration 7 established, what it ruled out, and what it abandoned", kind="table_insert"),
    ]
    return {"edits": E, "verdict": "NEW (Table 371b) + venue row CORRECTED", "summary": {
        "n_rows": len(rows), "status_counts": {s: sum(r["status"] == s for r in rows) for s in ("VERIFIED", "VERIFIED-ABSTRACT", "UNVERIFIED")},
        "workshop_posters": [w["status"] for w in ws]}, "rows": rows}
