"""0k assembly: neighbours with live-verified quotes, versions and venues; the logged mini saturation search; and the
executor's one-line verdicts (occupies | adjacent | irrelevant), written after reading the fetched abstracts."""

from __future__ import annotations

import re
from typing import Any

from common import READ_DATE
import positioning as P

VERDICTS = {
    "temperature_fork_margin": [
        ("arXiv 2604.09921 A Tale of Two Temperatures", "adjacent",
         "tempered remasking raises sample diversity in diffusion LMs; no fork-margin test, not autoregressive code; "
         "its arXiv comment gives COLM (v2), not ICML 2026"),
        ("arXiv 2510.01218 Control the Temperature (COLM 2025)", "adjacent",
         "switches temperature per token to protect precision; does not ask whether temperature moves an algorithm "
         "only where a fork margin is small"),
        ("arXiv 2309.02772 Hot or Cold? (AAAI 2024)", "adjacent",
         "adaptive temperature at hard tokens of code; closest in spirit, but token difficulty, not an algorithm-level fork"),
        ("'Improving Diversity in Language Models: When Temperature Fails, Change the Loss' (found for 'Lee 2025')",
         "adjacent", "temperature versus loss for diversity; the 'Lee et al. 2025' seed could not be pinned to one paper"),
        ("arXiv 2605.09745 Entropy-informed Decoding: Adaptive Information-Driven Branching", "adjacent",
         "branches decoding at high-entropy tokens; no algorithm-level outcome"),
        ("Beyond the 80/20 Rule: High-Entropy Minority Tokens (NeurIPS 2025)", "adjacent",
         "forking (high-entropy) tokens drive RL for reasoning; not temperature at a code fork"),
    ],
    "das_algorithm_choice_code": [
        ("CDAS: Faithful Bi-Directional Model Steering via Distribution Matching and Distributed Interchange "
         "Interventions (ICLR 2026)", "adjacent",
         "DAS-style interchange steering validated by generation on refusal and a backdoor, not on algorithm choice in "
         "code (Table 277 row 3)"),
        ("MIB: A Mechanistic Interpretability Benchmark (ICML 2025, arXiv 2504.13151 v2)", "adjacent",
         "method-ordering benchmark (DAS ahead of SAE features and neurons); a control, not the object"),
        ("Before Reasoning Begins (ICLR 2027 submission, Table 277 row 8)", "adjacent",
         "not returned by this search; carried from the iteration-6 audit (same model and site, reasoning not algorithm)"),
        ("scholarly hits for both DAS queries (sequence alignment, detoxification heads, VLM safety subspaces)",
         "irrelevant", "none localizes which algorithm a code model writes"),
    ],
    "evaluator_search_novel_algorithms": [
        ("FunSearch: Mathematical discoveries from program search with large language models (Nature 2023)",
         "adjacent", "evaluator-guided program search finds new constructions; not LeetCode-style algorithm choice"),
        ("AlphaEvolve: a coding agent for scientific and algorithmic discovery (2025)", "adjacent",
         "occupies the method family (evaluator-guided evolutionary search) but not the run's question of single-sample "
         "algorithm choice"),
        ("arXiv 2610.19157 DivAlgo (2026-10-13)", "adjacent",
         "benchmarks algorithmic diversity of code models with a similarity metric; a measurement neighbour for the "
         "collapse claim, not an internal or search result"),
        ("arXiv 2609.00077 Beneath the Diff (EMNLP 2026)", "adjacent",
         "algorithmic mode collapse in code-level autonomous research loops; diagnoses collapse in a loop, not in "
         "single-sample generation"),
        ("arXiv 2504.05108 Algorithm Discovery With LLMs: Evolutionary Search Meets Reinforcement Learning", "adjacent",
         "evolutionary search plus RL for algorithm discovery; no algorithm-choice internals"),
    ],
}


def _quote_check(k: str, n: dict, prior: dict, web: dict) -> dict:
    a = n["arxiv"]
    absx = web.get(f"abs_{a}", "")
    meta = P.parse_abs(absx)
    out = {"name": n["name"], "arxiv": a, "claimed": n["claimed"], "row_in_table_277": n["row"],
           "title_found": meta["title"], "fetched": meta["ok"]}
    sub = re.search(r"Submitted on (\d{1,2} [A-Z][a-z]{2} \d{4})", absx)
    last = re.search(r"last revised (\d{1,2} [A-Z][a-z]{2} \d{4}) \(this version, (v\d+)\)", absx)
    out["version_found"] = (f"v1 {sub.group(1)}" + (f", {last.group(2)} {last.group(1)}" if last else "")) if sub else None
    com = re.search(r"Comments:\s*\|\s*(.+?)\s*---", absx)
    out["arxiv_comment"] = com.group(1).strip()[:220] if com else None
    vf = None
    if out["arxiv_comment"]:
        m = re.search(r"(ICLR|ICML|NeurIPS|COLM|AAAI|EMNLP|ACL)[^.;|]*\d{4}|Workshop[^.;|]*@ ?ICML \d{4}",
                      out["arxiv_comment"])
        vf = m.group(0) if m else None
    out["venue_found"] = vf
    if k in prior:
        q = prior[k]["quote"]
        nm = lambda t: int(m.group(1)) if (m := re.search(r"\((\d+) matches in", t)) else 0
        hit = nm(web.get(f"grephtml_{a}", "")) >= 1
        hit_abs = nm(web.get(f"grepabs_{a}", "")) >= 1
        out.update({"quote": q, "quote_source": "art_OUuQUYQn5voE:evidence/quotes_iter6.jsonl (re-matched live)",
                    "quote_status": "VERIFIED" if hit else ("VERIFIED-ABSTRACT" if hit_abs else "NOT_VERIFIED"),
                    "quote_url": prior[k]["url"]})
    else:
        q = P.first_abstract_sentence(absx.replace("> Abstract:", "Abstract: "))
        out.update({"quote": q, "quote_source": "first sentence of the live arXiv abstract",
                    "quote_status": "VERIFIED-ABSTRACT" if q else "NOT_VERIFIED", "quote_url": f"https://arxiv.org/abs/{a}"})
    if k == "forking_fast":
        s = web.get("s_forkingfast_neurips", "")
        paper_page = [u for u in re.findall(r"https?://neurips\.cc/\S+", s) if "2608.19611" in u or "poster" in u]
        out["neurips_2026_page"] = paper_page[0] if paper_page else None
        out["venue_note"] = ("no paper-specific NeurIPS 2026 page was returned by the dated search (only generic "
                             "neurips.cc listings); the arXiv record carries no venue comment") if not paper_page else \
            "NeurIPS 2026 page found"
    if k == "forking_paths":
        s = web.get("s_forkingpaths_iclr", "")
        pages = [u for u in re.findall(r"https?://(?:openreview\.net|iclr\.cc|proceedings\.iclr\.cc)\S+", s)]
        if pages and re.search(r"ICLR\s*2025|iclr\.cc/virtual/2025|/2025/", s):
            out["venue_found"] = "ICLR 2025"
            out["venue_evidence"] = pages[0]
    vf = out["venue_found"]
    claimed_venue = re.search(r"(ICLR|ICML|NeurIPS|COLM) \d{4}", n["claimed"])
    if claimed_venue:
        cv = claimed_venue.group(0)
        if vf and cv in vf and "Workshop" not in vf:
            out["venue_status"] = "MATCH"
        elif vf:
            out["venue_status"] = f"CORRECTED (arXiv comment: {vf})"
        else:
            out["venue_status"] = "UNVERIFIED (no venue on the arXiv record)"
    else:
        out["venue_status"] = "n/a (claimed as a preprint)"
    return out


def assemble(run_web: bool = True) -> dict[str, Any]:
    web = P.collect() if run_web else {f.stem: f.read_text() for f in P.WEB.glob("*.txt")}
    prior = P.prior_quotes()
    neigh = {k: _quote_check(k, n, prior, web) for k, n in P.NEIGHBOURS.items()}
    log = []
    for topic, qs in P.QUERIES.items():
        for i, q in enumerate(qs):
            txt = web.get(f"s_{topic}_{i}", "")
            hits = P._hits(txt)
            eng = re.search(r"\[(scholarly|general) via ([a-z]+)\]", txt)
            log.append({"topic": topic, "query": q, "mode": "scholarly", "engine": eng.group(2) if eng else None,
                        "date": READ_DATE, "hits": len(hits), "screened": len(hits),
                        "urls": [h["url"] for h in hits]})
    for topic, qs in P.NAMED_SEEDS.items():
        for i, q in enumerate(qs):
            txt = web.get(f"n_{topic}_{i}", "")
            hits = P._hits(txt)
            eng = re.search(r"\[(scholarly|general) via ([a-z]+)\]", txt)
            log.append({"topic": topic, "query": q, "mode": "general (named seed)", "engine": eng.group(2) if eng else None,
                        "date": READ_DATE, "hits": len(hits), "screened": len(hits), "urls": [h["url"] for h in hits]})
    txt = web.get("s_forkingfast_neurips", "")
    t2 = web.get("s_forkingpaths_iclr", "")
    log.append({"topic": "venue check", "query": "Forking Paths in Neural Text Generation ICLR 2025 OpenReview",
                "mode": "general", "engine": "exa", "date": READ_DATE, "hits": len(P._hits(t2)),
                "screened": len(P._hits(t2)), "urls": [h["url"] for h in P._hits(t2)]})
    log.append({"topic": "venue check", "query": "Forking Fast NeurIPS 2026", "mode": "general", "engine": "exa",
                "date": READ_DATE, "hits": len(P._hits(txt)), "screened": len(P._hits(txt)),
                "urls": [h["url"] for h in P._hits(txt)]})
    uniq = sorted({u for r in log for u in r["urls"]})
    verdict_counts = {t: {v: sum(1 for x in vs if x[1] == v) for v in ("occupies", "adjacent", "irrelevant")}
                      for t, vs in VERDICTS.items()}
    n_q = len(log)
    n_sch = sum(r["mode"] == "scholarly" for r in log)
    stop_rule = ("stop after at least 2 scholarly queries per topic once a query returns no candidate that is not already "
                 "screened or is off-topic; all three topics met it at 2 queries")
    q_att = len(neigh)
    q_ok = sum(v["quote_status"] in ("VERIFIED", "VERIFIED-ABSTRACT") for v in neigh.values())
    return {"date": READ_DATE, "neighbours": neigh, "quotes_attempted": q_att, "quotes_verified": q_ok,
            "search_log": log, "n_queries": n_q, "n_scholarly_queries": n_sch,
            "n_hits": sum(r["hits"] for r in log), "n_unique_hits": len(uniq), "n_screened": sum(r["screened"] for r in log),
            "verdicts": {t: [{"candidate": c, "verdict": v, "why": w} for c, v, w in vs] for t, vs in VERDICTS.items()},
            "verdict_counts": verdict_counts, "stop_rule": stop_rule,
            "wording": f"to our knowledge, mini search dated {READ_DATE}"}
