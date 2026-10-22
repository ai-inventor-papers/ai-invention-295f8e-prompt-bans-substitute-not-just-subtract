"""Assemble ./.terminal_claude_agent_struct_out.json (the published structured output; research_out.json is saved from it).
answer = research_report.md; sources = cache/sources_iter6.json after the live literal passage check; follow-ups from the
renderer. Runs basic schema checks (lengths, required fields, unique indices, every [n] resolves).
Usage: python -I tools/write_struct_out_iter6.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, EVID, WS  # noqa: E402

report = (WS / "research_report.md").read_text(encoding="utf-8")
sources = json.loads((CACHE / "sources_iter6.json").read_text())
follow = json.loads((CACHE / "follow_up_iter6.json").read_text())
counts = json.loads((EVID / "saturation_counts_iter6.json").read_text())
kappa = json.loads((EVID / "rescreen_kappa_iter6.json").read_text())

for s in sources:
    s.pop("key", None)
    if s.get("authors") == []:
        s["authors"] = None

title = "Prior work on base landings and 8-bit nudges"
layman = ("Checks, with dated searches and verified quotes, whether earlier papers already showed that 8-bit (FP8) number formats "
          "change what activation nudges do, or that a nudged chat model falls back onto its base model's second choice.")
quotes = [json.loads(l) for l in (EVID / "quotes_iter6.jsonl").read_text().splitlines()]
tabq = [x for x in quotes if x["row"] != "venue"]
nst = {k: sum(x["status"] == k for x in tabq) for k in ("VERIFIED", "VERIFIED-ABSTRACT", "VERIFIED-BLOG")}
qa = [json.loads(l) for l in (EVID / "qa_second_pass_iter6.jsonl").read_text().splitlines()]
pl = [json.loads(l) for l in (EVID / "passages_live_check_iter6.jsonl").read_text().splitlines()]
scored = [json.loads(l) for l in (EVID / "scored_hits_iter6.jsonl").read_text().splitlines()]
sv = {k: sum(x["verdict"] == k for x in scored) for k in ("occupies", "adjacent", "irrelevant")}
nrows = len(re.findall(r"^\| 92e-", report, re.M))
summary = (
    "Dated (2026-10-21/22 UTC) positioning and saturation audit for iteration-6 Claims L, E, S/F and K. Provides paste-ready Table 92e "
    f"({nrows} rows, same columns as 92b-92d; {len(tabq)} new verbatim quotes plus {len(quotes) - len(tabq)} venue-page confirmations: {nst['VERIFIED']} VERIFIED full text, "
    f"{nst['VERIFIED-ABSTRACT']} VERIFIED-ABSTRACT, {nst['VERIFIED-BLOG']} VERIFIED-BLOG; {sum(r['second_pass'] == 'MATCH' for r in qa)}/{len(qa)} re-matched by live fetch_grep; "
    f"{sum(x['literal_match'] for x in pl)}/{len(pl)} supporting passages literal on live pages); inherited 92b-92d quotes cited by row id. "
    f"Search under a protocol frozen before the first call (sha256 0e2dc2d7...): 6 families / 21 strings on OpenAlex/Crossref, arXiv API, "
    f"Semantic Scholar, OpenReview ICLR 2027 + 14 grey-literature calls, forward citations of 8 seeds, rounds 2-4; {counts['logged_calls']} calls, "
    f"{counts['raw_hits_total']} raw hits, {counts['unique_after_dedup']} unique, {counts['manually_screened']} hand-screened, {len(scored)} scored "
    f"({sv['occupies']} occupies, {sv['adjacent']} adjacent, {sv['irrelevant']} irrelevant); same-agent re-screen kappa {kappa['cohens_kappa']}. Stopped after R4 by a logged deviation. "
    "FLAG E (activation quantisation changes an activation-level intervention's behavioural effect): PARTLY FIRED. Full-text evidence is weight-only "
    "(Steering Under Compression 2609.06473: bitsandbytes INT8/NF4, activations FP16/BF16, 'activation quantization (W8A8, W4A4) ... excluded by design'; "
    "PRISM 2610.20808 NF4) or joint W+A (PAHQ 2510.23264: FP32 vs 8-bit RTN of all weights and activations collapses ACDC patching AUC on GPT-2-scale). "
    "Two contemporaneous ICLR 2027 submissions report at abstract level that the SAME steering intervention's effect drifts across precision while "
    "fidelity/direction similarity are preserved (OpenReview 8iTqrW1sxY desk-rejected; h57duZqLOr), precision factor unstated, PDFs 403. "
    "Per-token-scaled FP8 W8A8 is accuracy-lossless (Kurtic et al., ACL 2025), supporting the 'same default' premise. So Claim E's general deployment statement is occupied; claimable: activation-vs-weight 2x2 attribution on identical hooks, per-token-scaled FP8 "
    "W8A8 engine, content-free nudges at matched dose with CRN, test-checked algorithm labels, absmax/scale readouts. E-deployment general form also "
    "occupied by KV-cache quantisation silently removing refusals (2606.09864) and flips (Dutta 2024). Reviewer baselines: kernel-swap control "
    "(Integer Alibi 2608.13756), batch invariance, weights-through-16-bit kernels (2609.04748), BF16 vs FP16 (TMLR 2609.26621). "
    "FLAG L (base forecast of where a perturbed tuned model lands, scored vs the tuned model's own tail/likelihood): PARTLY FIRED by "
    "Re-Emergent Misalignment 2507.03662 (retrospective likelihoods), Language Models Resist Alignment (ACL 2025) / Alignment Dynamics 2605.18309 "
    "(distribution-level rebound), Gravitational Safety Reversion 2606.28525 (prospective, geometric null); not fired: no algorithm-level, committed "
    "forecast vs q_lik/q_tail. Rival-supporting: jailbroken landings within the safe model's own top-10 (2401.17256), EM persona subspace in the "
    "frozen tuned model (2607.21356). Token-level: Sparse but Critical (ICLR 2026; ~30%/80%/90% at high-divergence positions). "
    "S: partly occupied (inherited site comparisons; Gaussian embedding perturbation 2602.02427; forks in the road 2605.17026); FLAG S not fired. "
    "F1 crowded (Forking Paths ICLR 2025, Forking Fast, Thought Anchors, Cliff tokens, Locked at the Entrance now arXiv 2608.29188). F2: the "
    "top-two-margin flip mechanism is occupied for numerics (2609.26621, MarginGate 2605.30218); present the temperature bound as a diagnostic. "
    "K: partly occupied (base merging restores diversity incl. code, ICLR 2027 MYXgOex05m; alignment-tax averaging EMNLP 2024; WiSE-FT); FLAG K "
    "not fired (no algorithm-level labels). Permitted wording: dated 'to our knowledge', never 'first'. 16 corrections (e.g., Give Me FP32 = NeurIPS 2025 "
    "oral under v2 title; URIAL/EFT ICLR 2024; Top-nσ ACL 2025 retitled; 'base model' in 2608.29118 = pre-EM instruct model). "
    "Files: research_report.md, evidence/{protocol_iter6,flags_iter6}.json, quotes/scored_hits/search_log/screening jsonl, reproducibility.md."
)
out = {
    "title": title,
    "layman_summary": layman,
    "summary": summary,
    "out_expected_files": {"output": "research_out.json", "reproducibility": "reproducibility.md"},
    "upload_ignore_regexes": [r"(^|/)cache/[^/]+\.txt$", r"(^|/)cache/grep_out/", r"(^|/)tools/__pycache__/",
                              r"(^|/)inherited/iter[45]/research_verification\.json$"],
    "answer": report,
    "sources": sources,
    "follow_up_questions": follow,
}
# ---- checks ----
assert 12 <= len(title) <= 90, len(title)
assert 80 <= len(layman) <= 250, len(layman)
assert 500 <= len(summary) <= 5000, len(summary)
idx = [s["index"] for s in sources]
assert len(idx) == len(set(idx)) and all(i > 0 for i in idx)
for s in sources:
    assert s["url"] and s["title"] and s["summary"], s
    for p in s["supporting_passages"]:
        assert p["quote"], s["index"]
cited = {int(x) for m in re.finditer(r"\[(\d+(?:, \d+)*)\]", report) for x in m.group(1).split(", ")}
assert cited <= set(idx), sorted(cited - set(idx))
(WS / ".terminal_claude_agent_struct_out.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"written: answer {len(report)} chars, {len(sources)} sources, {sum(len(s['supporting_passages']) for s in sources)} passages, "
      f"{len(follow)} follow-ups; summary {len(summary)} chars; layman {len(layman)} chars; cited {len(cited)}/{len(idx)}")
