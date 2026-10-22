"""Step 6: assemble ./.terminal_claude_agent_struct_out.json (research artifact schema) from research_report.md and
cache/sources_iter6.json (after the live literal passage check), and validate it: every [n] in the answer resolves to exactly
one source, indices are unique and contiguous, passages are non-empty, field lengths respect the schema.
Usage: python3 -I tools/build_struct_out_iter6.py"""
import json
import re
from pathlib import Path

WS = Path(__file__).resolve().parents[1]

TITLE = "Who already found the hidden plan?"
LAYMAN = ("Checks each new claim of this run about a hidden 'plan' inside a code-writing AI model against published papers, "
          "and says which ideas are already taken and which remain open.")
SUMMARY = (
    "Dated (2026-10-22) positioning audit for the iteration-6 claims P1-P5, N, S and E. It provides paste-ready Table 92e "
    "in research_report.md: 8 claim blocks plus CTRL rows. It has {NQ} new verbatim, versioned quotes from {NR} sources, all "
    "{QM} matched against cached source text and {QA} re-matched by an independent live fetch_grep pass. Statuses: "
    "{STAT}. It cites "
    "Tables 92b/92c (art_kjrCpQnPaniY) and 92d (art_ObxQOIlAM9MS) by row id without re-verifying them. "
    "Saturation search: protocol frozen and sha256-stamped before the first call; 21 strings over 7 lanes on arXiv API, "
    "Semantic Scholar, the OpenReview ICLR 2027 pool, OpenAlex/Crossref and grey literature; 6 round-2 strings; snowballing; "
    "a round 3 that met the stop rule; {NCALLS} logged calls (incl. 3 supplementary full-text checks). {RAW} raw hits gave {UNIQ} unique "
    "records, {INWIN} in the window and {NPAP} papers scored on the O/I/C rubric ({NROWS} claim-rows: {OCC} occupy, {ADJ} adjacent, {IRR} irrelevant). "
    "FLAGS: A (DAS localization of algorithm choice in code, validated by generation) NOT FIRED, narrowly. CDAS (ICLR 2026) does "
    "DAS steering validated by generation, but on refusal and a CoT backdoor. Algorithm choice in code is moved only by prompt "
    "cues (92c Invisible Lottery). Code attributes that are not the algorithm (language, library, coding habits) are moved by "
    "patching or difference-in-means vectors. The nearest same-model, same-site neighbour is the ICLR 2027 submission 'Before "
    "Reasoning Begins' (Qwen3-8B final-prompt SAE targets, code benchmarks, random nulls). "
    "B (activation quantization changes perturbation effects) PARTLY FIRED. Steering under quantization has been measured only "
    "with weight-only INT8/NF4 (2609.06473: activations stay FP16/BF16). Two ICLR 2027 submissions show effect changes across "
    "precision with aligned directions, but their abstracts do not say whether activations are quantized (PDFs 403). FP8 W8A8 "
    "appears only in a non-determinism study. No source found measures the effect size of random perturbations under "
    "activation rounding. "
    "C (editing verbaliser explanations to steer) FIRED. The NLA paper (Transformer Circuits, 7 May 2026; cite as "
    "Fraser-Taliente, Kantamneni, Ong et al.) edits a rhyme-plan explanation, reconstructs it with the AR and steers at the "
    "newline only (~50% success). LatentQA, SelfIE and Dreaming Vectors are kin. N is therefore a replication in a new setting. "
    "Cautions: about 2% claim-dependence of the AR (2607.20379), no newline plan in small open models (2609.18440), and "
    "published readout controls (ICLR 2027 'Auditing the Auditor'). "
    "D (resampling a fitted causal plan variable for diversity) PARTLY FIRED. Activation noise and latent-code sampling are "
    "occupied; the closest fitted-direction work is the ICLR 2027 'Random Choice in LMs'. "
    "Lane verdicts: P1 PARTLY OCCUPIED (method); P2, P3 and P4 ADJACENT-ONLY; P5 PARTLY OCCUPIED; N OCCUPIED (method); "
    "S PARTLY OCCUPIED (SAE-Steering, ACL 2026, beats prompt and activation baselines on reasoning strategies); E ADJACENT-ONLY "
    "in the published record but PARTLY OCCUPIED by contemporaneous submissions. "
    "Corrections: there is no official NLA for Qwen3-8B, but community NLAs exist at L24 (nanoNLA, EasyNLA); circuit-tracer has "
    "Qwen-3 PLTs including 8B (Hanna et al.), so justify Gemma for S; Gemma Scope 2 dates from 22 Dec 2025, with IT SAEs "
    "finetuned from PT; Sutter's 'any network to any algorithm' phrase is not in v2; Engels' v3 title. The report also gives "
    "permitted and forbidden wording per claim and reviewer baselines. Evidence files are in evidence/."
)
FOLLOW_UPS = [
    "Do the ICLR 2027 submissions 'Stable Directions, Different Effects' and 'Activation Steering under Low-Bit Quantization' "
    "quantize activations (W8A8/FP8) or only weights? Their full texts decide whether flag B fires.",
    "On the released Qwen2.5-7B-Instruct L20 NLA, how far does the AR reconstruction move when only the algorithm name in an "
    "explanation is edited? The ~2% claim-dependence result predicts a small move, so this should be measured before the "
    "edit-and-steer arm.",
    "Would interchange/DAS at Qwen3-8B's final prompt position find a low-rank variable for algorithm choice? How does it "
    "relate to the 23 SAE targets of 'Before Reasoning Begins' and to the Qwen-3 PLTs in circuit-tracer?",
]


def main():
    answer = (WS / "research_report.md").read_text()
    from collections import Counter
    qs = [json.loads(l) for l in (WS / "evidence" / "quotes_iter6.jsonl").read_text().splitlines()]
    qa = [json.loads(l) for l in (WS / "evidence" / "qa_second_pass_iter6.jsonl").read_text().splitlines()]
    st = Counter(q["status"] for q in qs)
    global SUMMARY
    SUMMARY = SUMMARY.replace("{NQ}", str(len(qs))).replace("{NR}", str(len({q["key"] for q in qs}))).replace(
        "{QM}", f"{sum(q['check'] == 'MATCH' for q in qs)}/{len(qs)}").replace(
        "{QA}", f"{sum(r['second_pass'] == 'MATCH' for r in qa)}/{len(qa)}").replace(
        "{STAT}", ", ".join(f"{v} {k}" for k, v in sorted(st.items())))
    cnt = json.loads((WS / "evidence" / "saturation_counts_iter6.json").read_text())
    ncalls = len((WS / "evidence" / "search_log_iter6.jsonl").read_text().splitlines())
    for k, v in {"{NCALLS}": ncalls, "{RAW}": f"{cnt['raw_hits_identified']:,}", "{UNIQ}": f"{cnt['unique_after_dedup']:,}",
                 "{INWIN}": f"{cnt['in_window']:,}", "{NPAP}": cnt["scored_unique_papers"], "{NROWS}": cnt["scored_rows"],
                 "{OCC}": cnt["scored_verdicts"].get("occupies", 0), "{ADJ}": cnt["scored_verdicts"].get("adjacent", 0),
                 "{IRR}": cnt["scored_verdicts"].get("irrelevant", 0)}.items():
        SUMMARY = SUMMARY.replace(k, str(v))
    src = json.loads((WS / "cache" / "sources_iter6.json").read_text())
    sources = []
    for s in sorted(src, key=lambda x: x["index"]):
        extra = "; ".join(x for x in [f"version: {s['version']}" if s.get("version") else "", f"venue: {s['venue']}" if s.get("venue") else "",
                                       f"status: {s['status']}" if s.get("status") else "", "retrieved 2026-10-22"] if x)
        raw_auth = [a for a in (s.get("authors") or []) if a and a.strip()]
        truncated = any(a.lower().startswith("et al") for a in raw_auth)
        authors = [a for a in raw_auth if not a.lower().startswith("et al")] or None
        if truncated:
            extra += "; author list truncated to the first names shown by the source"
        year = s.get("year") if isinstance(s.get("year"), int) and s.get("year") > 0 else None
        sources.append({"index": s["index"], "url": s["url"], "title": s["title"], "summary": f"{s['summary']} ({extra})",
                        "authors": authors, "year": year,
                        "supporting_passages": [{"quote": p["quote"], "locator": p.get("locator")} for p in s["supporting_passages"] if p["quote"].strip()]})
    idx = [s["index"] for s in sources]
    assert idx == list(range(1, len(idx) + 1)), "indices must be unique and contiguous"
    cited = set()
    for grp in re.findall(r"\[(\d+(?:,\s*\d+)*)\]", answer):
        cited |= {int(x) for x in grp.split(",")}
    missing = sorted(cited - set(idx))
    uncited = sorted(set(idx) - cited)
    assert not missing, f"citations without a source: {missing}"
    assert 12 <= len(TITLE) <= 90 and 80 <= len(LAYMAN) <= 250 and 500 <= len(SUMMARY) <= 5000, (len(TITLE), len(LAYMAN), len(SUMMARY))
    out = {"title": TITLE, "layman_summary": LAYMAN, "summary": SUMMARY,
           "out_expected_files": {"output": "research_out.json", "reproducibility": "reproducibility.md"},
           "upload_ignore_regexes": [r"(^|/)cache/", r"(^|/)tools/__pycache__/"],
           "answer": answer, "sources": sources, "follow_up_questions": FOLLOW_UPS}
    (WS / ".terminal_claude_agent_struct_out.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"struct out: answer {len(answer)} chars; sources {len(sources)}; cited {len(cited)}; uncited {uncited}; "
          f"passages {sum(len(s['supporting_passages']) for s in sources)}; summary {len(SUMMARY)} chars; layman {len(LAYMAN)}")


if __name__ == "__main__":
    main()
