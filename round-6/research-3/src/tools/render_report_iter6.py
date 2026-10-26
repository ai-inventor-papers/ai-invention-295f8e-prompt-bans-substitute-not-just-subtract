"""Step 5-6: render tools/report_template_iter6.md into research_report.md.

- {{key[,key...]}} placeholders become numbered citations [n] / [n, m] in order of first appearance.
- <<VAR>> placeholders are filled from the evidence files (search log, saturation counts, quotes, QA pass).
- Writes cache/sources_iter6.json: one record per cited source in the 92c/92d schema
  {index, url, title, summary, authors, year, version, venue, status, retrieved, supporting_passages[{quote, locator}]}.
  Supporting passages are the verified quotes of that source, reduced to the longest span that occurs LITERALLY
  (whitespace-collapsed) in the cached source text; tools/check_passages_live_iter6.py then re-checks them live.
Usage: python -I tools/render_report_iter6.py
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, EVID, load_text  # noqa: E402

WS = Path(__file__).resolve().parents[1]
META = json.loads((EVID / "arxiv_meta.json").read_text())
QUOTES = [json.loads(l) for l in (EVID / "quotes_iter6.jsonl").read_text().splitlines()]
INH = json.loads((EVID / "inherited_index.json").read_text())

MANUAL = {
    "nla": dict(title="Natural Language Autoencoders Produce Unsupervised Explanations of LLM Activations",
                authors=["Kit Fraser-Taliente", "Subhash Kantamneni", "Euan Ong", "et al. (Anthropic)"], year=2026,
                summary="Decisive for flag C: edits an NLA explanation of a rhyme plan, reconstructs it with the AR and steers at the newline "
                        "(about 50% success); a steering vector from the explanation difference in the rewards case; confabulation; FVE 0.6-0.8.",
                venue="Transformer Circuits Thread (published May 7, 2026)"),
    "nla_readme_raw": dict(title="kitft/natural_language_autoencoders README (released NLA checkpoints)", year=2026,
                           summary="Lists the 8 released checkpoints (4 base models x AV/AR) with layers, and requires loading nla_meta.yaml."),
    "hf_nla_qwen25_7b_L20_av": dict(title="kitft/nla-qwen2.5-7b-L20-av model card (Hugging Face)", year=2026,
                                    summary="Qwen2.5-7B-Instruct AV: extraction at the residual output of block 20; in-distribution fve_nrm 0.752."),
    "hf_nla_qwen25_7b_L20_av_meta": dict(title="nla_meta.yaml of kitft/nla-qwen2.5-7b-L20-av", year=2026,
                                         summary="Sidecar metadata: extraction_layer_index 20, injection and MSE scales."),
    "tl_issue_1884": dict(title="TransformerLens issue #1884: NLA explain/reconstruct proposal", year=2026,
                          summary="Tooling proposal for the Qwen2.5-7B NLA pair that lists edited-explanation steering as a non-goal."),
    "jaisood_nla": dict(title="Natural Language Autoencoders can verbalize influence but don't report whether it changed the outcome",
                        authors=["Jai Sood"], year=2026,
                        summary="Grey-literature audit of two released NLA checkpoints: the readout reports applied pressure and answer, not whether the pressure changed the answer."),
    "lw_dreaming_vectors": dict(title="Dreaming Vectors: Gradient-descented steering vectors from Activation Oracles and using them to Red-Team AOs (LessWrong)",
                                year=2026, summary="Grey-literature verbaliser-to-steering kin for flag C: steering vectors optimized against an Activation Oracle."),
    "hf_ceselder_nanonla": dict(title="ceselder/nanoNLA (nanonla-l24-av-qwen3-8b) model card", year=2026,
                                summary="Community NLA activation verbalizer for Qwen3-8B at layer 24 (Karvonen injection)."),
    "gh_nanonla_readme": dict(title="ceselder/nanoNLA README", year=2026,
                              summary="Minimal NLA reimplementation; carries a faithfulness disclaimer and points users to another repository."),
    "gh_easynla_readme": dict(title="syvb/EasyNLA README", year=2026,
                              summary="NLA training codebase built on nanoNLA; reports ~70% held-out FVE on Qwen3-8B layer 24."),
    "lw_gemma_scope_2": dict(title="Announcing Gemma Scope 2 (LessWrong / AI Alignment Forum)", year=2025,
                             summary="Release post dated 22 Dec 2025; every PT SAE has a version finetuned for IT models."),
    "gemma_scope_2_tech_report": dict(title="Gemma Scope 2 Technical Paper (Google DeepMind)", year=2025,
                                      summary="IT SAEs are initialized from PT SAEs and finetuned on rollout-derived data."),
    "hf_gemma_scope_2_4b_it": dict(title="google/gemma-scope-2-4b-it model card", year=2025,
                                   summary="Sites (resid_post, attn_out, mlp_out, transcoders) at 4 depths (25/50/65/85%) with several widths and L0 values."),
    "circuit_tracer_readme_raw": dict(title="safety-research/circuit-tracer README", year=2026,
                                      summary="Gemma-3 PLTs from GemmaScope-2 (need the nnsight backend); Qwen-3 PLTs for 0.6B-14B, including 8B."),
    "hf_mwhanna_qwen3_8b_transcoders": dict(title="mwhanna/qwen3-8b-transcoders (Hugging Face)", year=2025,
                                            summary="Qwen-3 transcoder collection (0.6B-14B); the card does not name the exact checkpoint."),
    "tc_biology": dict(title="On the Biology of a Large Language Model (Transformer Circuits)", year=2025,
                       summary="Attribution-graph caveat: satisfying insight for about a quarter of the prompts tried."),
    "llmcompressor_fp8_readme": dict(title="llm-compressor examples/quantization_w8a8_fp8 README (vLLM project)", year=2024,
                                     summary="FP8_DYNAMIC scheme: static per-channel weight scales and dynamic per-token activation scales."),
    "pmlr_selfie_chen24ao": dict(title="SelfIE: Self-Interpretation of Large Language Model Embeddings (PMLR 235 record)",
                                 authors=["Haozhe Chen", "Carl Vondrick", "Chengzhi Mao"], year=2024, summary="Venue record: ICML 2024, PMLR 235:7373-7388."),
    "pmlr_das_clear2024": dict(title="Finding Alignments Between Interpretable Causal Variables and Distributed Neural Representations (PMLR 236 record)",
                               authors=["Atticus Geiger", "Zhengxuan Wu", "Christopher Potts", "Thomas Icard", "Noah Goodman"], year=2024,
                               summary="Venue record for DAS: CLeaR 2024, PMLR 236."),
    "iclr2024_makelov_poster": dict(title="Is This the Subspace You Are Looking for? (ICLR 2024 poster page)",
                                    authors=["Aleksandar Makelov", "Georg Lange", "Atticus Geiger", "Neel Nanda"], year=2024,
                                    summary="Venue record: ICLR 2024 poster."),
    "arxiv_abs_2506.09501v1": dict(title="arXiv abs page 2506.09501v1: Give Me FP32 or Give Me Death? Challenges and Solutions for Reproducible Reasoning",
                                   year=2025, summary="Confirms the v1 title and the 'up to 9%' abstract sentence."),
    "arxiv_api": dict(title="arXiv API (export.arxiv.org/api/query): version, v1 date, comment and journal-ref metadata", year=2026,
                      url="https://export.arxiv.org/api/query",
                      summary="Engine E3 and the source of all version, v1-date and venue-comment lines (evidence/arxiv_meta.json)."),
    "s2_api": dict(title="Semantic Scholar Graph API (search, citations, references)", year=2026, url="https://api.semanticscholar.org/graph/v1",
                   summary="Engine E4 (year=2026 search) and snowballing (forward citations and backward references)."),
    "openreview_api": dict(title="OpenReview API v2 notes/search (ICLR.cc/2027/Conference)", year=2026, url="https://api2.openreview.net/notes/search",
                           summary="Engine E5 and the locator of every VERIFIED-ABSTRACT ICLR 2027 row."),
    "openalex": dict(title="OpenAlex / Crossref scholarly search (via aii-web-tools aii_fast_web_search.py --mode scholarly)", year=2026,
                     url="https://api.openalex.org/works", summary="Engine E1 for lanes L1, L4 and L6 in round 1, and all lanes in round 2."),
}


def or_record(key):
    txt = load_text(key)
    title = re.search(r"^title: (.*)$", txt, re.M).group(1)
    venue = re.search(r"^venue: (.*)$", txt, re.M).group(1)
    forum = re.search(r"^forum: (.*)$", txt, re.M).group(1)
    return title, venue, forum


def source_meta(key):
    if key.startswith("inh_"):
        _, tab, n = key.split("_")
        art = "art_kjrCpQnPaniY" if tab == "c" else "art_ObxQOIlAM9MS"
        r = next(x for x in INH if x["artifact"] == art and x["source_index"] == int(n))
        table = "92b/92c" if tab == "c" else "92d"
        return dict(url=r["url"], title=r["title"], authors=None, year=r.get("year"), version=r.get("url_version") or None, venue=None,
                    status="INHERITED (cited by id; not re-verified)",
                    summary=f"Inherited from {art} Table {table} source [{n}]; its quotes are cited by row id and were not re-fetched here.")
    if key in MANUAL:
        m = MANUAL[key]
        q = [x for x in QUOTES if x["key"] == key]
        url = m.get("url") or (q[0]["url"] if q else None)
        return dict(url=url, title=m["title"], authors=m.get("authors"), year=m.get("year"), version=(q[0]["version"] if q else None),
                    venue=m.get("venue") or (q[0]["venue"] if q else None), status=(q[0]["status"] if q else "ENGINE"), summary=m["summary"])
    if key.startswith("or_"):
        title, venue, forum = or_record(key)
        q = [x for x in QUOTES if x["key"] == key]
        return dict(url=q[0]["url"] if q else f"https://openreview.net/forum?id={forum}", title=title + f" (OpenReview forum {forum})",
                    authors=None, year=2026, version="submission", venue=venue, status="VERIFIED-ABSTRACT",
                    summary=f"{venue}; contemporaneous. Cited in rows " + ", ".join(sorted({x['row'] for x in q})) + "." if q else venue)
    aid, ver = re.match(r"(\d{4}\.\d{4,5})(v\d+)", key).groups()
    m = META[aid]
    q = [x for x in QUOTES if x["key"] == key]
    venue = (m.get("comment") or "") + ((" | " + m["journal_ref"]) if m.get("journal_ref") else "")
    cached = next((json.loads(l) for l in (CACHE / "index.jsonl").read_text().splitlines() if json.loads(l)["key"] == key), {})
    return dict(url=cached.get("url") or f"https://arxiv.org/html/{aid}{ver}", title=m["title"], authors=m["authors"][:12] + (["et al."] if len(m["authors"]) > 12 else []),
                year=int(m["v1_published"][:4]), version=ver, venue=venue.strip() or "arXiv preprint", status="VERIFIED",
                summary=(q[0]["ref"] + "; cited in rows " + ", ".join(sorted({x['row'] for x in q})) + "." if q else "Cited as a listed hit."))


def literal_span(quote, raw_flat):
    """Longest piece of the quote (split at [...] and at characters html2text/MathML may alter) found literally."""
    segs = [s.strip() for s in re.split(r"\s*\[\.\.\.\]\s*", quote) if s.strip()]
    cands = []
    for s in segs:
        cands.append(s)
        cands += [p.strip() for p in re.split(r"[\"'’“”–—`*_~]|\s-\s", s) if len(p.strip()) >= 30]
    cands = sorted(set(cands), key=len, reverse=True)
    for c in cands:
        if re.sub(r"\s+", " ", c) in raw_flat:
            return c
    # fallback: longest contiguous run of >= 6 words of any segment that occurs literally (handles PDF hyphenation,
    # markdown links/emphasis and MathML splits inside a sentence)
    best = None
    for s in segs:
        words = s.split()
        for n in range(len(words), 5, -1):
            for i in range(0, len(words) - n + 1):
                c = " ".join(words[i:i + n])
                if c in raw_flat:
                    if best is None or len(c) > len(best):
                        best = c
                    break
            if best and len(best.split()) >= n:
                break
    return best


def main():
    tpl = (WS / "tools" / "report_template_iter6.md").read_text()

    def _inh_numbers(m):  # "92c source {{inh_c_30}}" -> "92c source 30 {{inh_c_30}}", so the inherited index stays visible
        keys = [k.strip() for k in m.group(2).split(",")]
        nums = [k.split("_")[2] for k in keys if k.startswith("inh_")]
        return f"{m.group(1)} {', '.join(nums)} {{{{{m.group(2)}}}}}"
    tpl = re.sub(r"(92[cd] sources?) \{\{([^}]+)\}\}", _inh_numbers, tpl)
    order = []
    for grp in re.findall(r"\{\{([^}]+)\}\}", tpl):
        for k in [x.strip() for x in grp.split(",")]:
            if k not in order:
                order.append(k)
    idx = {k: i + 1 for i, k in enumerate(order)}
    # make sure the engine sources are cited in the method section
    text = re.sub(r"\{\{([^}]+)\}\}", lambda m: "[" + ", ".join(str(idx[k.strip()]) for k in m.group(1).split(",")) + "]", tpl)
    # numbers
    log = [json.loads(l) for l in (EVID / "search_log_iter6.jsonl").read_text().splitlines()]
    eng = Counter(r["engine"].split(" ")[0] for r in log)
    counts = json.loads((EVID / "saturation_counts_iter6.json").read_text())
    qa = [json.loads(l) for l in (EVID / "qa_second_pass_iter6.jsonl").read_text().splitlines()] if (EVID / "qa_second_pass_iter6.jsonl").exists() else []
    stat = Counter(q["status"] for q in QUOTES)
    fc = {r["query_id"]: r["n_results"] for r in log if r["query_id"].startswith("FC-")}
    sv = counts["scored_verdicts"]
    fill = {
        "FC_MIB": fc.get("FC-MIB", 0), "FC_ERP": fc.get("FC-ERP", 0),
        "N_CALLS": len(log), "N_CALLS_BY_ENGINE": ", ".join(f"{k} {v}" for k, v in sorted(eng.items())),
        "RAW": counts["raw_hits_identified"], "UNIQUE": counts["unique_after_dedup"], "IN_WINDOW": counts["in_window"],
        "KW_PASS": counts["keyword_pass_in_window"], "SCORED_ROWS": counts["scored_rows"], "SCORED_PAPERS": counts["scored_unique_papers"],
        "N_OCC": sv.get("occupies", 0), "N_ADJ": sv.get("adjacent", 0), "N_IRR": sv.get("irrelevant", 0),
        "IRR_TA": counts["irrelevant_at_title_abstract"], "PRE": counts["excluded_at_keyword_prescreen"],
        "N_QUOTES": len(QUOTES), "N_QREFS": len({q["key"] for q in QUOTES}), "Q_MATCH": f"{sum(q['check'] == 'MATCH' for q in QUOTES)}/{len(QUOTES)}",
        "Q_STATUS": ", ".join(f"{v} {k}" for k, v in sorted(stat.items())),
        "QA_OK": sum(r["second_pass"] == "MATCH" for r in qa), "QA_N": len(qa),
    }
    for k, v in fill.items():
        text = text.replace(f"<<{k}>>", str(v))
    assert "<<" not in text, re.findall(r"<<\w+>>", text)
    (WS / "research_report.md").write_text(text)
    # sources
    sources = []
    for k in order:
        m = source_meta(k)
        passages = []
        q = [x for x in QUOTES if x["key"] == k and x["check"] == "MATCH"]
        if q and (CACHE / f"{k}.txt").exists():
            raw = load_text(k)
            # OpenReview API JSON escapes line breaks, so a live literal match cannot cross a line of the abstract
            raw_flat = re.sub(r"\s+", " ", raw.replace("\n", " \u0000 ")) if k.startswith("or_") else re.sub(r"\s+", " ", raw)
            for x in q[:4]:
                span = literal_span(x["quote"], raw_flat)
                if span:
                    passages.append({"quote": span, "locator": f"{x['locator']} ({x['qid']}; {x['status']})"})
        sources.append({"index": idx[k], "key": k, "url": m["url"], "title": m["title"], "summary": m["summary"], "authors": m["authors"],
                        "year": m["year"], "version": m["version"], "venue": m["venue"], "status": m["status"],
                        "retrieved": "2026-10-22", "supporting_passages": passages})
    (CACHE / "sources_iter6.json").write_text(json.dumps(sources, indent=1, ensure_ascii=False))
    print(f"report: {len(text)} chars; sources: {len(sources)}; passages: {sum(len(s['supporting_passages']) for s in sources)}")
    print({k: fill[k] for k in ("N_CALLS", "N_CALLS_BY_ENGINE", "QA_OK", "QA_N", "Q_MATCH")})


if __name__ == "__main__":
    main()
