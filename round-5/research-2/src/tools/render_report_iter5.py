"""Render research_report.md, cache/answer_iter5.md and cache/sources_iter5.json from the evidence files.

Citations are written in the narrative as {{ref_key}} and resolved to [n] in order of first appearance; every source's
supporting passages are verified quotes from evidence/quotes_iter5.jsonl (or, for the inherited Table 92c rows,
the passages art_kjrCpQnPaniY published). Usage: python -I tools/render_report_iter5.py
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, EVID, WS  # noqa: E402

QUOTES = [json.loads(l) for l in (EVID / "quotes_iter5.jsonl").read_text().splitlines()]
QA = [json.loads(l) for l in (EVID / "qa_second_pass_iter5.jsonl").read_text().splitlines()]
HITS = [json.loads(l) for l in (EVID / "saturation_hits_iter5.jsonl").read_text().splitlines()]
COUNTS = json.loads((EVID / "saturation_counts_iter5.json").read_text())
FLAGS = json.loads((EVID / "flags.json").read_text())
CORR = [json.loads(l) for l in (EVID / "corrections_iter5.jsonl").read_text().splitlines()]
LOG = [json.loads(l) for l in (EVID / "search_log_iter5.jsonl").read_text().splitlines()]
META = json.loads((EVID / "arxiv_meta.json").read_text())
INH = json.loads((WS / "inherited" / "research_out.json").read_text())
PROTO_SHA = (EVID / "protocol.sha256").read_text().split()[0]

BYREF = defaultdict(list)
for q in QUOTES:
    BYREF[q["ref_key"]].append(q)

# inherited Table 92c sources reused by row id (not re-verified here)
INH_SRC = {s["index"]: s for s in INH["sources"]}
INHERITED = {"Inh-IFG": (26, "C1b, C1-seedb"), "Inh-PlanSearch": (27, "C1c"), "Inh-DiversityInjection": (31, "C1-siteb/c"),
             "Inh-NCGRPO": (52, "C1-sitef"), "Inh-Gacha": (54, "C1j"), "Inh-DepartureMatched": (66, "C1g, C3cd"),
             "Inh-BeforeFirstToken": (64, "C2ab"), "Inh-Nagarajan": (19, "C1-siteg"), "Inh-FunSearch": (62, "C3ca"),
             "Inh-AlphaEvolve": (49, "C3cb"), "Inh-Maveli": (55, "C3ce"), "Inh-DiversityWithoutDiscovery": (63, "b6d, C3cc")}
EXTRA = {
    "Venue-NeurIPS-RBP": {"url": "https://neurips.cc/virtual/2026/poster/150680",
                          "title": "NeurIPS 2026 virtual-site poster page: The Reasoning Boundary Paradox",
                          "summary": "Venue evidence: the NeurIPS 2026 poster page lists 'The Reasoning Boundary Paradox: How Reinforcement Learning Constrains Language Models' (fetched 2026-10-21).",
                          "passages": [{"quote": "Reasoning Boundary Paradox: How Reinforcement Learning Constrains Language Models", "locator": "page title"}]},
    "Venue-ACL-Nudging": {"url": "https://aclanthology.org/2025.acl-long.623/", "title": "ACL Anthology 2025.acl-long.623 (Nudging)",
                          "summary": "Venue evidence for Nudging (ACL 2025 long).", "passages": [{"quote": "Anthology ID: 2025.acl-long.623", "locator": "metadata block"}]},
    "Venue-ACL-Lee": {"url": "https://aclanthology.org/2025.findings-emnlp.10/", "title": "ACL Anthology 2025.findings-emnlp.10 (Lee et al.)",
                      "summary": "Venue evidence for Lee et al. (Findings of EMNLP 2025).", "passages": [{"quote": "Anthology ID: 2025.findings-emnlp.10", "locator": "metadata block"}]},
    "arXivAPI": {"url": "https://export.arxiv.org/api/query", "title": "arXiv API (id_list metadata: versions, v1 dates, titles, comments, journal_ref)",
                 "summary": "Authoritative version numbers, v1 dates, titles and comment/journal_ref lines for every arXiv id quoted here (evidence/arxiv_meta.json, retrieved 2026-10-21).", "passages": []},
}

ORDER, NUM = [], {}


def cite(m):
    keys = [k.strip() for k in m.group(1).split(",")]
    out = []
    for k in keys:
        if k not in BYREF and k not in INHERITED and k not in EXTRA:
            raise KeyError(f"unknown ref {k}")
        if k not in NUM:
            ORDER.append(k)
            NUM[k] = len(ORDER)
        out.append(str(NUM[k]))
    return "[" + ", ".join(out) + "]"


def R(text):
    return re.sub(r"\{\{([^}]+)\}\}", cite, text)


def qrec(ref, needle):
    for q in BYREF[ref]:
        if needle in q["quote"]:
            return q
    raise KeyError((ref, needle))


def neighbour(ref):
    q = BYREF[ref][0]
    aid = q["id"] if q["id"][:2].isdigit() else ""
    m = META.get(aid, {})
    if aid and m:
        au = m["authors"]
        last = au[0].split()[-1] if au else "?"
        last = {"LeBronnec2026-RedundancyRLVR": "Le Bronnec", "Zhou2026-PassK": "Zhou (T.)",
                "Zhou2026-CrossPatching": "Zhou (Y.)"}.get(ref, last)
        name = f"{last}{' et al.' if len(au) > 1 else ''}"
        year = m["v1_published"][:4]
    elif q["status"] == "VERIFIED-ABSTRACT":
        name, year = "Anonymous", "2026"
    else:
        name = {"Lindsey2024-Crosscoders": "Lindsey et al.", "Kissane2024-SAETransfer": "Kissane et al.",
                "Minder2025-DiffBlog": "Minder et al. (blog)", "LW2025-RuntimeSteering": "LessWrong post",
                "Veselovsky2025-Hindsight": "Veselovsky et al."}.get(ref, ref)
        year = {"Lindsey2024-Crosscoders": "2024", "Veselovsky2025-Hindsight": "2025"}.get(ref, "n.d.")
    return f"{name}, {year}, {q['venue_status']}"


# ---------------- Table 92d spec: (row, claim text, ref, needle, adds) ----------------
ADD_A0 = ("Test-checked mechanism labels over correct programs (runtime tracer + AST + blind judge) instead of LLM-judge clusters; "
          "same chat-templated prompt for base and instruct; a two-family base/instruct design (Qwen3-8B, gemma-3-4b)")
ROWS = [
    ("92d-A0", "Premise: tuning narrowed an algorithm choice the base model makes more evenly (code, algorithm level)",
     "Lee2025-AlgoDiv", "decreases algorithmic diversity", "contradicts-in-part", ADD_A0 + "; NOT 'first base-vs-tuned algorithm-level comparison' (FLAG C partly fired)"),
    ("92d-A0", "", "Lee2025-AlgoDiv", "instruction tuning favors single", "contradicts-in-part",
     "Per-task test of the premise; Lee et al.'s difficulty split predicts the premise can fail on harder tasks"),
    ("92d-A0", "", "Lee2025-AlgoDiv", "Llama-3.1-8B-Instruct", "context", "Mechanism labels checked by execution traces rather than an LLM judge"),
    ("92d-A0", "", "LeBronnec2026-RedundancyRLVR", "decreases JPlag diversity", "adjacent", "Algorithm-level (not structural near-duplicate) diversity; instruction-tuned rather than RLVR descendant"),
    ("92d-A0", "", "Wu2025-Monoculture", "neither of the models were able to produce code", "context", "Open-weight base/instruct code pair (none in Monoculture's code arm)"),
    ("92d-A0", "", "Jangra2026-DivAlgo", "uncontrolled sampling", "context", "Base-vs-instruct pairing (DivAlgo has none)"),
    ("92d-A0", "", "Yang2026-BF-v4", "factor of 2", "supports", "replication of base-vs-aligned narrowing at the algorithm level on code"),
    ("92d-A0", "", "Liu2026-AlignmentTax", "1.0% single-cluster rate", "supports", "Code, test-checked; not semantic clusters of QA answers"),
    ("92d-A0", "", "Anon2026-LockedEntrance", "concentrated at the entrance", "supports", "Code algorithms instead of Countdown entrance families; base vs instruction-tuned rather than PPO/GRPO"),
    ("92d-A1", "Movability follows the base repertoire (the tuned model can be pushed off its default only where the base spreads)",
     "Zhou2026-PassK", "frozen base-model behavior", "partly-fires (FLAG B)",
     "Inference-time movability of the tuned model under pushes (not training-time coverage loss); algorithm choice, not correctness; base repertoire (beta, runner-up) committed by sha256 before any push"),
    ("92d-A1", "", "Zhou2026-PassK", "Per-Problem Base Anchoring", "partly-fires (FLAG B)", "Forecast scored on matched events at inference time"),
    ("92d-A1", "", "Duan2026-WhatWillPTFix", "A priori signals capture a minority", "contradicts-in-part",
     "Must beat (or report against) simple base signals; Duan et al. find base pass rate / likelihood weak predictors of training gains"),
    ("92d-A1", "", "Duan2026-WhatWillPTFix", "The missing part lives", "supports", "Base-model behaviour on a task (its algorithm distribution) as the predictor"),
    ("92d-A1", "", "Anon2026-Lookahead", "predicting which IFEval prompts degrade", "partly-fires (FLAG B)", "Uses the base model alone (no reward model); outcome = movability under activation/prompt pushes"),
    ("92d-A1", "", "Nguyen2025-RBP", "disproportionately reinforces", "adjacent", "Per-task forecast tested on the deployed instruct model rather than a training-dynamics account"),
    ("92d-A1", "", "Anon2026-HowMuchNotWhere", "anchors randomly chosen prompts", "contradicts-in-part", "A random-task control for any 'targeting' claim"),
    ("92d-A1", "", "Mohammadi2024-Attractor", "gracefully finds its way back", "adjacent", "Quantified per task with test-checked labels"),
    ("92d-A2", "Landing: a push or ban of the tuned model lands on the base model's runner-up algorithm",
     "Zhang2025-VS", "amplifying its modes while suppressing the tails", "partly-fires (stylised)",
     "A per-task, pre-registered forecast of the landing identity (runner-up) scored on matched events — none found"),
    ("92d-A2", "", "Lin2024-URIAL", "top five tokens ranked by base LLMs", "supports", "Algorithm-level (whole-solution) landings rather than token ranks"),
    ("92d-A2", "", "Anon2026-SameCandidates", "remain within the pretrained Top-16", "adjacent", "Forecast before the push, not retrospective inheritance"),
    ("92d-A2", "", "Samanta2026-Crystallization", "single seed distribution present in the pretrained", "supports", "Code algorithms; prospective"),
    ("92d-A2", "", "Fortier2026-Convergence", "but not introduced by the SFT data", "supports", "Algorithm choice on code; landing under pushes"),
    ("92d-A2", "", "Zhao2025-EchoChamber", "converge towards a dominant output distribution", "supports", "Released base/instruct pair instead of from-scratch models"),
    ("92d-A2", "", "Anon2026-TokenCues", "same starting cues more likely", "supports", "Activation-level pushes; algorithm identity"),
    ("92d-B1", "Transplant: base prefill states (task-spec positions, blocks 12-23, lambda 0.25/0.5/1) written into the instruct model restore the base choice; controls: read position, blocks 0-11/24-35, matched-random, cross-task",
     "Zhou2026-CrossPatching", "hidden state entering the late boundary", "occupies (method)",
     "Outcome = test-checked algorithm choice / solution diversity (not a next-token margin); site = task-specification prefill positions; dose lambda; matched-norm random displacement and cross-task patch controls"),
    ("92d-B1", "", "Zhou2026-CrossPatching", "every tested boundary from 40% depth", "occupies (method)", "Site comparison includes read position and early/late block ranges at matched dose"),
    ("92d-B1", "", "Oozeer2025-Transfer", "By replacing the fine-tuned model", "method-overlap", "Diversity/algorithm outcome instead of backdoor removal"),
    ("92d-B1", "", "Du2025-PostTrainingReshapes", "patching hidden representations from base to post", "method-overlap", "Behavioural (solution) outcome instead of factual-recall log-probabilities"),
    ("92d-B1", "", "Prakash2024-CMAP", "Cross-model activation patching shows evidence", "method-overlap", "Direction base->tuned (CMAP patched tuned->base)"),
    ("92d-B1", "", "Zhang2026-SLR", "restoring a carefully chosen range of layers", "adjacent", "States rather than weights; code; matched-random control"),
    ("92d-B1", "", "Sumita2026-FrankenMerging", "combines the lower layers of an aligned model", "adjacent", "Per-position state transplant in the opposite composition (base states into instruct blocks)"),
    ("92d-B1", "", "Anon2026-LockedEntrance", "layer interpolation restores entrance diversity", "adjacent", "Hidden-state transplant (not weights) on code"),
    ("92d-B1", "", "Wang2026-BACo", "Base-Aligned Model Collaboration", "occupies (goal, token level)", "Activation level instead of token routing"),
    ("92d-B2", "De-sharpening push: push the instruct model along the base-minus-instruct direction vs isotropic pushes at matched norm",
     "Anand2026-PASTA", "aligned-base residual contrasts", "occupies (method)",
     "replication of PASTA-style aligned-minus-base ablation in a new setting: algorithm choice in code, against matched-norm isotropic pushes"),
    ("92d-B2", "", "Anand2026-PASTA", "same residual-stream hook footprint", "occupies (control)", "Matched-norm isotropic directions rather than orthogonal unit directions"),
    ("92d-B2", "", "Anon2026-TIRD", "suppressing it substantially degrades", "adjacent", "Diversity outcome rather than accuracy"),
    ("92d-B2", "", "Minder2026-ADL", "analyzing activation differences", "adjacent", "Opposite sign (toward base) and a diversity outcome"),
    ("92d-B2", "", "Zheng2025-ExPO", "amplifying the parameter change", "adjacent (weight space)", "Activation-space push; weight-space extrapolation is a reviewer baseline"),
    ("92d-B2", "", "Nakamura2026-TemplateDiD", "chat template the base model never saw", "supports (method caution)", "Direction estimated with base and instruct under the same chat template"),
    ("92d-C", "Knobs head-on: activation plan noise vs text-level plan samplers, base-aligned collaboration (base writes the intent, instruct writes the code) and departure-matched decoding",
     "Wang2026-BACo", "21.3%", "occupies (collaboration lane)",
     "Base-intent arm = sentence-granularity instance of base-aligned collaboration; the addition is pricing it against activation noise on test-checked algorithms"),
    ("92d-C", "", "Peeperkorn2025-Conformative", "conformative decoding", "occupies (collaboration lane)", "Code, algorithm-level outcome"),
    ("92d-C", "", "Feng2025-SwitchGeneration", "Switch Generation", "occupies (collaboration lane)", "Code, algorithm-level outcome"),
    ("92d-C", "", "Zhang2026-RLReplace", "retains much of the base model", "adjacent", "Code; activation-noise comparison"),
    ("92d-C", "", "Sumita2026-FrankenMerging", "better diversity–quality trade-off than temperature", "adjacent", "Code; text-level plan samplers in the contrast set"),
    ("92d-C", "", "Dang2025-WiSEFT", "cannot be achieved only through diversity-inducing decoding", "baseline-to-add", "Weight interpolation as a contrast arm"),
    ("92d-E", "Second family: gemma-3-4b pt vs it", "Kissane2024-SAETransfer", "unusually large compared to other fine-tuned models", "context (caution)",
     "Report base/instruct activation-space similarity for gemma-3-4b before transplanting; Gemma base/chat pairs can diverge unusually"),
    ("92d-E", "", "Zhang2026-SLR", "Selective Layer Restoration", "adjacent", "Gemma in a code setting; states not weights"),
    ("92d-E", "", "Nakamura2026-TemplateDiD", "chat template the base model never saw", "supports (method caution)", "Template-controlled contrasts on the second family"),
]

ROW_INHERITED = [
    ("92d-C", "(cross-ref 92c)", "Inh-IFG", "intent-hot/response-cold text plan sampler (92c C1b)"),
    ("92d-C", "(cross-ref 92c)", "Inh-PlanSearch", "natural-language plan search (92c C1c)"),
    ("92d-C", "(cross-ref 92c)", "Inh-DiversityInjection", "Level-2 per-output specifications (92c C1-siteb/c)"),
    ("92d-C", "(cross-ref 92c)", "Inh-Gacha", "instruction-following diversity (92c C1j)"),
    ("92d-C", "(cross-ref 92c)", "Inh-DepartureMatched", "decoding matched to steering's departure from greedy (92c C1g)"),
    ("92d-C", "(cross-ref 92c)", "Inh-NCGRPO", "latent rollout perturbation in RL (92c C1-sitef)"),
    ("92d-G", "(cross-ref 92c C3c)", "Inh-FunSearch", "novelty boundary unchanged; no new 2026 hit"),
]


def esc(s):
    return s.replace("|", "\\|").replace("\n", " ")


def table_92d():
    head = ("| Row | Claim (one line) | Neighbour (authors, arXiv v1 year, venue status) | Verbatim quote | URL; section; version | Retrieved | "
            "Relation | What this run adds, or 'replication' |\n|---|---|---|---|---|---|---|---|\n")
    out, sub = [], Counter()
    flushed = False

    def flush_inherited(kind):
        for row, claim, ref, what in ROW_INHERITED:
            if row != kind:
                continue
            sub[row] += 1
            rid = f"{row}{chr(96 + sub[row])}"
            s = INH_SRC[INHERITED[ref][0]]
            out.append(f"| {rid} | {claim} | {esc(s['title'][:70])} {{{{{ref}}}}} | see Table 92c row {INHERITED[ref][1]} (not re-verified) | "
                       f"{s['url'][:80]} | 2026-10-21 (iteration 4) | inherited | {esc(what)} |")

    for row, claim, ref, needle, rel, adds in ROWS:
        if row == "92d-E" and not flushed:
            flush_inherited("92d-C")
            flushed = True
        q = qrec(ref, needle)
        sub[row] += 1
        rid = f"{row}{chr(96 + sub[row])}"
        ver = q["version_quoted"] if q["id"][:2].isdigit() else q["status"]
        out.append(f"| {rid} | {esc(claim) if claim else '(same claim)'} | {esc(neighbour(ref))} {{{{{ref}}}}} | \"{esc(q['quote'])}\" | "
                   f"{q['url']}; {esc(q['section'])}; {ver} | {q['retrieval_date']} | {rel} | {esc(adds)} |")
    flush_inherited("92d-G")
    return head + "\n".join(out)


def hits_table():
    head = ("| ID | Title | v1 | Venue | 4-mo tag | ICLR-2027 rule | Claim | O / I / C | Total | Verdict | Full text? | Note |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|---|\n")
    rows = []
    for h in sorted(HITS, key=lambda h: (-h["score"], h["best_claim"])):
        a = h["axes"]
        rows.append(f"| {h['id']} | {esc(h['title'][:70])} | {h['v1_date']} | {esc(h['venue_status'])} | "
                    f"{'yes' if h['contemporaneous_4mo'] else 'no'} | {esc(h['iclr2027_rule'])} | {h['best_claim']} | "
                    f"{a['O']} / {a['I']} / {a['C']} | {h['score']} | {h['verdict']} | {'yes' if h['full_text_checked'] else 'abstract'} | {esc(h['note'][:230])} |")
    return head + "\n".join(rows)


def counts_table():
    head = ("| Family | Identified (raw) | Unique records | In window | Keyword pre-screen (>=2 groups) | Scored | Adjacent or occupying | Occupying |\n"
            "|---|---|---|---|---|---|---|---|\n")
    rows = []
    for f, c in COUNTS.items():
        if f.startswith("_"):
            continue
        rows.append(f"| {f} | {c['identified_raw']} | {c['unique_records']} | {c['in_window']} | {c['passed_keyword_prescreen']} | "
                    f"{c['full_text_or_abstract_checked_scored']} | {c['included_adjacent_or_occupying']} | {c['occupying']} |")
    return head + "\n".join(rows)


def log_table():
    agg = defaultdict(lambda: [0, 0, Counter()])
    for r in LOG:
        eng = r["engine"].split(" ")[0]
        k = (r["family"], eng)
        agg[k][0] += 1
        agg[k][1] += int(r.get("n_results") or 0)
        agg[k][2][r["status"].split(" ")[0][:14]] += 1
    head = "| Family | Engine | Calls | Hits | Status counts |\n|---|---|---|---|---|\n"
    rows = [f"| {f} | {e} | {v[0]} | {v[1]} | {dict(v[2])} |" for (f, e), v in sorted(agg.items())]
    return head + "\n".join(rows)


def corrections_md():
    return "\n".join(f"- **{c['type']}** — {c['item']}: {c['correction']}" for c in CORR)


st = Counter(q["status"] for q in QUOTES)
qa_ok = sum(r["second_pass"] == "MATCH" for r in QA)
T = COUNTS["_totals"]

BODY = f"""# Has prior work restored base-model variety? Positioning audit for iteration 5 (Table 92d)

*Retrieval date: 2026-10-21. Every quote below was copied from the paper's own versioned text (arXiv HTML vN, the PDF where HTML is missing, the ACL Anthology / PMLR / NeurIPS page, an OpenReview API record or the grey-literature post) and checked with the inherited normalisation rule. This audit extends art_kjrCpQnPaniY (Tables 92b/92c): its 112 quotes are cited by row id and were not re-verified. It quotes no run-internal result: rows describe design facts only.*

## 1. Scope, date and method

- **Question.** As of 2026-10-21, has any paper, preprint or ICLR 2027 submission (a) predicted from a base model's own distribution where post-training narrows, whether the tuned model can be pushed off its default, or where the push lands (Claims A1/A2); (b) transplanted or interpolated base-model hidden states into the tuned descendant to restore output or solution diversity, or pushed along a base-minus-tuned direction (B1, B2/D); (c) measured test-checked, algorithm-level diversity of a base model against its tuned descendant on code (the premise, A0); (d) priced activation-level plan noise against text-level plan samplers, base-aligned collaboration and departure-matched decoding (C)?
- **Sources and versions.** Versions, v1 dates, titles, comment and journal_ref lines for every arXiv id come from the arXiv API {{{{arXivAPI}}}}. Full texts of the latest versions were cached with the aii-web-tools fetch core (HTML first; PDF for 2406.05587v1, whose HTML is unavailable). Earlier versions were fetched where a number or title changed: 2506.17871 v1/v3/v4 and 2410.09300 v1/v4.
- **Quotes.** {len(QUOTES)} quotes from {len(BYREF)} references: {st.get('VERIFIED', 0)} VERIFIED on full text, {st.get('VERIFIED-ABSTRACT', 0)} VERIFIED-ABSTRACT (ICLR 2027 submissions; OpenReview PDFs return HTTP 403), {st.get('VERIFIED-BLOG', 0)} VERIFIED-BLOG, {st.get('MISMATCH', 0)} MISMATCH. Where arXiv HTML renders a MathML number twice ("0.300.30"), the quote is split with [...] at that point so the rendered number is matched once. An independent live second pass with the skill's fetch_grep re-matched **{qa_ok}/{len(QA)}** quotes (evidence/qa_second_pass_iter5.jsonl).
- **Saturation search (PRISMA-S items in reproducibility.md).** The protocol (lanes, 25 query strings in 9 families, engines, window, rubric, flags, stop rule) was frozen in evidence/protocol.json before the first call (written 14:50:21Z; first call 14:51:23Z; sha256 `{PROTO_SHA[:16]}...` after a logged timestamp-only amendment). Round 1: every family on E1 (OpenAlex/Crossref via the skill), E3 (arXiv API, cs.CL/LG/AI, newest first), E4 (Semantic Scholar, year=2026) and E5 (OpenReview ICLR 2027 pool); F4/F5/F7 also on E6 (grey literature via WebSearch); forward citations of 8 seeds (Semantic Scholar; OpenAlex `cites:` returned 0 because OpenAlex records zero citations for all four nearest neighbours). Round 2: 6 queries built from the vocabulary of included hits. Round 3: forward citations of the 6 closest new hits and backward references of the two closest hits per flag. Totals: {T['logged_calls']} logged calls, {T['raw_hits']} raw hits, {T['unique_records']} unique records after de-duplication ({T['seen_in_iteration4_audit']} already seen by the iteration-4 audit and re-screened), {T['in_window']} in the window, {T['keyword_prescreen_pass_in_window']} passing the keyword pre-screen; manual title screens of the ranked shortlists (311 base-vs-tuned, 248 code-x-diversity, 108 activation-x-diversity, 344 round-2 and 25 round-3 new records); {T['scored_hits']} hits scored on the rubric ({T['scored_in_window']} in window).
- **Rubric.** The O/I/C axes of Tables 92b/92c, made claim-specific in the protocol; each axis scores 1 / 0.5 / 0; a total of at least 2.5 occupies, 1-2 is adjacent, below 1 irrelevant. The flags use the frozen definitions, including their PARTLY FIRED clauses.
- **Contemporaneity.** contemporaneous_4mo = v1 after 2026-06-21; ICLR 2027 rule = peer-reviewed publication after 2026-07-17 (arXiv-only exempt); every ICLR 2027 submission is tagged contemporaneous.
- **Stop rule.** Round 2 added one new hit scoring at least 1.5 (ICLR 2027 submission 'Same Candidates, Stronger Reasoning', 1.5). Round 3 added none (best new: 1.0). **The stop rule was met after round 3**, well inside the Stage-2 time cap.
- **Departures.** Single screener (borderline calls are published with axis scores and decisive sentences); ICLR 2027 rows are abstract-only; forward citations rest on Semantic Scholar alone; manual screening used ranked shortlists rather than exactly the top 100; venue status for several 2023-2024 anchors (Kirk et al., Huang et al., URIAL, EFT, model arithmetic) is given as unconfirmed.

## 2. Verdict box and flags (as of 2026-10-21)

| Claim | Lane verdict | Deciding references |
|---|---|---|
| A0 premise: tuning narrowed algorithm choice on code (FLAG C) | PARTLY OCCUPIED; contradicting in part | Lee et al. (base vs instruct, mixed direction) {{{{Lee2025-AlgoDiv}}}}; Le Bronnec et al. (base vs RLVR, structural) {{{{LeBronnec2026-RedundancyRLVR}}}}; text-domain support {{{{Yang2026-BF-v4, Liu2026-AlignmentTax, Fortier2026-Convergence}}}} |
| A1 movability follows the base repertoire (FLAG B) | PARTLY OCCUPIED (training-time, correctness-coverage forecasts exist); inference-time movability OPEN | Zhou (T.) {{{{Zhou2026-PassK}}}}; Duan {{{{Duan2026-WhatWillPTFix}}}}; Lookahead {{{{Anon2026-Lookahead}}}}; Reasoning Boundary Paradox {{{{Nguyen2025-RBP}}}} |
| A2 landing = base runner-up | ADJACENT-ONLY (stylised and retrospective support; no landing forecast) | power-sharpening {{{{Zhang2025-VS}}}}; base top-k inheritance {{{{Lin2024-URIAL, Anon2026-SameCandidates}}}}; seed-distribution collapse {{{{Samanta2026-Crystallization}}}} |
| B1 transplant of base prefill states (FLAG A) | PARTLY OCCUPIED: method occupied, diversity outcome open; FLAG A NOT FIRED | cross-patching {{{{Zhou2026-CrossPatching}}}}; base-activation patching {{{{Oozeer2025-Transfer, Du2025-PostTrainingReshapes, Prakash2024-CMAP}}}}; weight-level diversity restoration {{{{Zhang2026-SLR, Sumita2026-FrankenMerging, Anon2026-LockedEntrance}}}} |
| B2/D de-sharpening push | PARTLY OCCUPIED: method and random-direction control occupied (style outcome) | PASTA {{{{Anand2026-PASTA}}}}; TIRD {{{{Anon2026-TIRD}}}}; ADL {{{{Minder2026-ADL}}}}; weight-space ExPO / Chat Vector / task negation {{{{Zheng2025-ExPO, Huang2024-ChatVector, Ilharco2023-TaskArithmetic}}}} |
| C knobs head-on | PARTLY OCCUPIED (as in 92c), and base-aligned collaboration is an occupied lane | BACo {{{{Wang2026-BACo}}}}; conformative decoding {{{{Peeperkorn2025-Conformative}}}}; Switch Generation {{{{Feng2025-SwitchGeneration}}}}; IFG / PlanSearch / departure-matched decoding {{{{Inh-IFG, Inh-PlanSearch, Inh-DepartureMatched}}}} |
| E second family (gemma-3-4b pt/it) | ADJACENT-ONLY | Gemma base/chat divergence caution {{{{Kissane2024-SAETransfer}}}}; Gemma in SLR {{{{Zhang2026-SLR}}}} |
| G novelty boundary | unchanged from 92c C3c (no new 2026 hit) | {{{{Inh-FunSearch, Inh-AlphaEvolve}}}} |

**FLAG A — NOT FIRED (narrowly).** No paper writes base-model hidden states into the forward pass of its tuned descendant AND reports a change in output or solution diversity. Each half is published separately. *Mechanism:* Zhou's cross-patching replaces "the hidden state entering the late boundary ... for all sequence positions" with the base model's state and runs boundary and token controls, but its outcome is a next-token target margin at the first base/descendant divergence {{{{Zhou2026-CrossPatching}}}}. On the rubric it scores O 0.5 / I 1 / C 1 = 2.5, which occupies B1's *method*. Earlier anchors are Oozeer et al. (base activations replace the fine-tuned model's to remove a backdoor; single-layer patching cuts the trigger by up to 60%) {{{{Oozeer2025-Transfer}}}}, Du et al. (base-to-post patching of knowledge representations) {{{{Du2025-PostTrainingReshapes}}}} and Prakash et al.'s CMAP {{{{Prakash2024-CMAP}}}}. *Goal at other levels:* restoring a layer interval to pre-trained weights recovers diversity (SLR) {{{{Zhang2026-SLR}}}}; splicing aligned lower layers with base upper layers raises semantic diversity and beats temperature sampling (FrankenMerging) {{{{Sumita2026-FrankenMerging}}}}; layer interpolation restores entrance diversity on Countdown {{{{Anon2026-LockedEntrance}}}}; base-aligned token routing does the same at the token level {{{{Wang2026-BACo}}}}. The closest cross-domain analogue steers distilled diffusion students along teacher directions at an identified block {{{{Anon2026-ReDiverse}}}}. Grey-literature search (LessWrong, Alignment Forum, transformer-circuits.pub) found only adjacent work {{{{LW2025-RuntimeSteering, Kissane2024-SAETransfer, Lindsey2024-Crosscoders}}}}.

**FLAG B — PARTLY FIRED.** Per-prompt forecasts from the frozen base model of where post-training narrows already exist, but at training time and for correctness coverage. Zhou (T.) decomposes prompts "by frozen base-model behavior" and predicts that coverage loss localizes to boundary prompts {{{{Zhou2026-PassK}}}}. Duan forecasts per-problem post-training gains and finds that base pass rate and the likelihood of a correct solution explain only a minority of the explainable variance (0.30 and 0.24) {{{{Duan2026-WhatWillPTFix}}}}. Lookahead predicts which IFEval prompts degrade from the base model plus a reward model {{{{Anon2026-Lookahead}}}}. The Reasoning Boundary Paradox orders RLVR's winners and losers by base likelihood {{{{Nguyen2025-RBP}}}}. None forecasts the *inference-time* movability of the tuned model, or the *identity* of the algorithm a push or ban lands on, from the base model's per-task algorithm distribution. The landing prediction (A2) has only stylised or retrospective support: the KL-optimal aligned policy is a power-sharpened reference policy that "amplif[ies] its modes" {{{{Zhang2025-VS}}}}; aligned top tokens sit mostly within the base top-5 {{{{Lin2024-URIAL}}}}; 92.9% of post-training top-1 changes stay within the pretrained top-16 {{{{Anon2026-SameCandidates}}}}; SFT collapses onto a seed distribution present in the pretrained model {{{{Samanta2026-Crystallization}}}}.

**FLAG C — PARTLY FIRED.** Lee et al. compare DeepSeek-Coder-6.7B Base and Instruct with test-checked correctness and LLM-judge algorithm clusters. They find that instruction tuning "decreases algorithmic diversity in AtCoder-introductory problems, but increases it in other problems" {{{{Lee2025-AlgoDiv}}}}. Le Bronnec et al. find RLVR descendants lose structural (JPlag/Vendi) diversity against their base on most prompts, but not at the algorithm level {{{{LeBronnec2026-RedundancyRLVR}}}}. DivAlgo has no base-vs-instruct pairing {{{{Jangra2026-DivAlgo}}}}. Generative Monoculture's code arm had no open-weight base model, because the open code models "were [not] able to produce code solutions" {{{{Wu2025-Monoculture}}}}. **'First base-versus-tuned algorithm-level comparison' is struck**, and the premise row reads *contradicting in part*.

### 2.1 Permitted novelty wording (each sentence carries the date and points to evidence/)

- **A0:** "Unlike prior LLM-judged comparisons of base and instruct code models, which found instruction tuning narrows algorithmic diversity on easy problems but widens it on harder ones [Lee et al.], we label algorithms by execution traces and AST over correct programs." Do not claim to be first, and do not state the premise as settled.
- **A1:** "Prior work forecasts, per prompt and from the frozen base model, which prompts RL training stops solving [Zhou; Duan; Lookahead]; to our knowledge (dated search 2026-10-21; evidence/), none forecasts whether the deployed instruct model can be pushed off its default algorithm from the base model's own per-task algorithm distribution." Report a simple base-signal baseline, because Duan finds such signals weak.
- **A2:** "To our knowledge, no prior work forecasts which alternative a push or prohibition installs in the tuned model; stylised accounts predict that alignment sharpens the base model's ranking [Verbalized Sampling; URIAL; Same Candidates]."
- **B1:** "To our knowledge (dated search 2026-10-21), no prior work writes base-model prefill states into the instruct model to test where post-training narrows solution choice. Cross-model patching of base states into a descendant exists for next-token decisions, backdoors and factual recall [Zhou 2026; Oozeer 2025; Du 2025; Prakash 2024], and base-aligned mixing for diversity exists at the token, logit and weight level [BACo; conformative decoding; Nudging; EFT; SLR; FrankenMerging; WiSE-FT; Hindsight Merging]." The word 'first' is not allowed for the transplant mechanism.
- **B2/D:** Frame it as a replication of aligned-minus-base direction ablation [PASTA] in a new setting (algorithm choice in code), scored against matched-norm isotropic pushes. Do not frame it as a new knob.
- **C:** "The base-intent arm is a sentence-granularity instance of base-aligned collaboration [BACo; Switch Generation; conformative decoding]." C1's contrast-set limits from 92c still apply.

### 2.2 Reviewer baselines the search implies (recommendations, not design changes)

1. **Weight interpolation between Qwen3-8B-Base and Qwen3-8B**, as the weight-space counterpart of T(lambda). Precedents: WiSE-FT recovers pass@k beyond what temperature can {{{{Dang2025-WiSEFT}}}}; Hindsight Merging reports a "20-50% increase in pass@10 ... across a coding benchmark" {{{{Veselovsky2025-Hindsight}}}}; base-model merging before RL on code {{{{Anon2026-MergeBeforeRL}}}}.
2. **Layer restoration and splicing (SLR; FrankenMerging) at the B1 block ranges**, the closest diversity neighbours of the site-specific transplant {{{{Zhang2026-SLR, Sumita2026-FrankenMerging}}}}.
3. **BACo-style token routing** as the strongest base-aligned collaboration baseline for the base-intent arm {{{{Wang2026-BACo}}}}; rl-replace-style sparse substitution {{{{Zhang2026-RLReplace}}}}.
4. **Logit-level base/tuned arithmetic** (EFT / proxy-tuning) as the logit-space counterpart of B2/D {{{{Mitchell2023-EFT, Liu2024-ProxyTuning}}}}.
5. **pass@k coverage at large k** as context for A0 {{{{Yue2025-RLVR}}}}, judged against measured noise and template cells {{{{Anon2026-JudgingRLVR}}}}.
6. **Template control** for every base-minus-instruct contrast (B2/D direction, E family) {{{{Nakamura2026-TemplateDiD}}}}.

## 3. Table 92d — paste-ready (design facts only; no run results)

{table_92d()}

### 3.1 Further verified neighbours by lane (quoted in evidence/quotes_iter5.jsonl; not in the paste-ready table)

- **Lane 1, base vs aligned diversity and RLVR boundaries:**
  - Yang et al.'s v1 figure, kept for the version check: "nearly an order of magnitude (e.g., from 12 to 1.2) relative to base models" {{{{Yang2025-BF-v1}}}};
  - RLHF reduces output diversity relative to SFT {{{{Kirk2024-RLHF}}}};
  - base models beat aligned models at randomness and creativity, with an effective trade-off {{{{WestPotts2025}}}};
  - aligned models display less conceptual diversity {{{{Murthy2025-Concept}}}};
  - larger post-trained models, but not larger base models, are less diverse {{{{Springer2026-Annotations}}}};
  - lightly post-trained models are the most divergent in a 105-model census {{{{Parikh2026-Census}}}};
  - empirical support shrinkage outweighs expansion under RLVR {{{{Wu2026-InvisibleLeash}}}};
  - post-training compresses variation in fiction across OLMo base/SFT/DPO/RLVR {{{{Li2026-NarrativeFlattening}}}};
  - a diversity metric read from base-model log-probabilities {{{{Khoriaty2026-Decan}}}};
  - execution-trajectory algorithm similarity (BehaveSim), a precedent for runtime-trace labels {{{{ZhangLu2026-BehaveSim}}}};
  - the definition of 'sharpening' {{{{Huang2024-Sharpening}}}};
  - power sampling from the base model avoids RL's diversity collapse {{{{KaranDu2025-PowerSampling}}}}.
- **Lane 1/5, predicting post-training from the base model (FLAG B adjacency):**
  - per-head signed forecasts from the base model alone {{{{Anon2026-PredictiveMI}}}};
  - data mean representations injected into a base model to predict unintended behaviours {{{{Wang2026-Data2Behavior}}}};
  - projection differences from base generations predict trait shifts {{{{Chen2025-PersonaVectors}}}};
  - forgetting predicted by the KL divergence from the base policy {{{{Shenfeld2025-RLsRazor}}}}.
- **Lane 2, base-aligned collaboration:**
  - Nudging (alignment changes a small subset of stylistic tokens on which base models are uncertain) {{{{Fei2025-Nudging}}}};
  - model arithmetic {{{{Dekoninck2024-ModelArithmetic}}}};
  - CreativeInstruct (two-model methods need released base models) {{{{Sahu2026-CreativeInstruct}}}};
  - ReDiPO (the base model recovers answer modes that post-training removed) {{{{Samuel2026-ReDiPO}}}};
  - a per-prompt diversity router {{{{Liu2026-DiversityRouter}}}};
  - word transplants at disagreement positions {{{{Anon2026-NotWhichPath}}}};
  - a prefix-transplant ledger {{{{Anon2026-TokenLedger}}}};
  - logit grafting {{{{Anon2026-LogitGrafting}}}};
  - early planning-related decision tokens carry the base-reasoning gap {{{{Shen2026-DecisionTokens}}}}.
- **Lane 3, base-to-tuned activation transfer:**
  - a base-model direction induces backtracking in the distilled model {{{{Ward2025-Backtracking}}}};
  - base mechanisms orchestrated by thinking-model heuristics {{{{Venhoff2026-BaseKnows}}}};
  - instruct-to-base steering transfer {{{{Stolfo2025-IFSteering}}}};
  - instruction tuning changes later-layer activations only on targeted inputs {{{{Wolfram2025-Layers}}}};
  - KV-cache fusion between models {{{{Fu2026-C2C}}}};
  - cross-model patching for inspection {{{{Ghandeharioun2024-Patchscopes}}}};
  - module transplants between base and instruct {{{{Yoon2026-Transplant}}}};
  - weight patching {{{{Sun2026-WeightPatching}}}};
  - base activations predicting long-CoT activations {{{{Zhao2025-ActivationControl}}}};
  - cross-family representation steering of base models {{{{Gan2026-CREST}}}};
  - hidden-state optimisation that elicits CoT in base models {{{{Wang2026-CoTBase}}}};
  - activation-patching practice {{{{ZhangNanda2024-Patching, HeimersheimNanda2024}}}};
  - shallow alignment concentrated on the first output tokens {{{{Qi2025-Shallow}}}}.
- **Lane 5, model diffing:**
  - crosscoder L1 artefacts and the BatchTopK fix {{{{Minder2025-Crosscoder, Minder2025-DiffBlog}}}};
  - SAEs transfer between base and chat models {{{{Kissane2024-SAETransfer}}}}.

## 4. Saturation search (dated 2026-10-21)

### 4.1 Per-claim saturation verdict

- **A0 / FLAG C:** partly fired. Lee et al. (2025) is the only base-vs-instruct algorithm-level code comparison, and its direction is mixed; no 2026 paper repeats it with execution-based labels (searched F1, F9, FC(Lee), BC(Lee, Le Bronnec)).
- **A1 / A2 / FLAG B:** partly fired (A1, training time); A2 is adjacent-only. 2026 adds Duan, Lookahead, How-Much-Not-Where, Same Candidates and Predictive MI, all training-time, retrospective or head-level.
- **B1 / FLAG A:** not fired. 2026 adds cross-patching (method; 2.5), SLR, FrankenMerging, Locked-at-the-Entrance and ReDiverse (2.0 each).
- **B2/D:** PASTA (2.5) occupies the method and its random-direction control; the outcome differs.
- **C:** base-aligned collaboration is occupied (BACo, Switch Generation, conformative decoding, rl-replace, token-ledger, Not-Which-Path).

### 4.2 Counts per query family (PRISMA-style)

{counts_table()}

Families F1-F9 are round 1, R2 is round 2, FC is forward citations (rounds 1 and 3) and BC is backward references (round 3). A record can belong to several families. 'Scored' counts hits whose records carry that family tag. Out-of-window anchors are scored for context but excluded from the saturation verdicts.

### 4.3 Search-log summary (calls and hits per family x engine; full log in evidence/search_log_iter5.jsonl)

{log_table()}

### 4.4 Scored hits (O = outcome, I = intervention/predictor, C = contrast/forecast; claim-specific definitions in evidence/protocol.json)

{hits_table()}

## 5. Corrections and confirmations

{corrections_md()}

## 6. Unverified references (no numbers are taken from these)

- The LessWrong 'rephrase circuit' post (instruct attention heads patched into the base model) named in the plan was **not found** by two dated searches; it is not cited.
- The normalized cross-model transfer gains for base-to-instruct steering vectors (2509.06608) appeared only in a search-engine summary; the paper's text was quoted only for its qualitative transfer sentence {{{{Sinii2026-SmallVectors}}}}.
- ICLR 2027 submissions are quoted from abstracts only: Locked at the Entrance, Token Ledger, Not Which Path, Token Cues, Lookahead, How Much Not Where, Predictive MI, TIRD, Merge-before-RL, Logit Grafting, Judging RLVR, ReDiverse, Same Candidates. Their full-text numbers are not used.
- 2609.33085 (strategy switching) and 2608.04893 (KV-relay audit) were screened from abstracts in the Semantic Scholar records and are not quoted.
- Venue status for Kirk et al. (ICLR 2024), Huang et al. (ICLR 2025), URIAL, EFT and model arithmetic (ICLR 2024) is as stated in the plan and is not confirmed on a venue page here.

## 7. Confidence, contradicting evidence, and what would change the verdicts

- **High confidence:** FLAG C partly fired; B1's method occupied; B2/D's method occupied; base-aligned collaboration occupied. These rest on full-text quotes that were re-matched live.
- **Moderate confidence:** FLAG A not fired and FLAG B partly fired. Thirteen ICLR 2027 submissions are abstract-only, and an ICLR 2027 submission whose full text measures diversity after a base-state patch would flip FLAG A.
- **Contradicting evidence the paper must face:**
  - instruction tuning *increases* algorithmic diversity on harder problems {{{{Lee2025-AlgoDiv}}}};
  - base-model signals predict little of where post-training acts {{{{Duan2026-WhatWillPTFix}}}};
  - random-prompt anchoring protects as well as targeted anchoring {{{{Anon2026-HowMuchNotWhere}}}};
  - reported homogeneity can be overstated {{{{Schaeffer2026-Hivemind}}}}, depends on model and dataset {{{{Skobelev2026-FTFixes}}}}, or is confounded by length {{{{Cheng2026-CanopyEntropy}}}};
  - RLVR boundary verdicts move with temperature and scoring rule, and base-ahead cells concentrate in chat-template conditions {{{{Anon2026-JudgingRLVR}}}}.
- **What would change the verdicts:**
  - a paper measuring solution or algorithm diversity after writing base states into a tuned model (FLAG A fires);
  - a paper forecasting inference-time movability or push landings from the base distribution (FLAG B fires fully);
  - a base-vs-instruct comparison with execution-labelled algorithms on code (FLAG C fires fully).
"""


def main():
    body = R(BODY)
    srcs = []
    for k in ORDER:
        n = NUM[k]
        if k in BYREF:
            qs = BYREF[k]
            q0 = qs[0]
            aid = q0["id"] if q0["id"][:2].isdigit() else ""
            m = META.get(aid, {})
            title = m.get("title") or q0.get("title_at_latest_version") or {
                "Lindsey2024-Crosscoders": "Sparse Crosscoders for Cross-Layer Features and Model Diffing",
                "Kissane2024-SAETransfer": "SAEs (usually) Transfer Between Base and Chat Models",
                "Minder2025-DiffBlog": "What We Learned Trying to Diff Base and Chat Models (And Why It Matters)",
                "LW2025-RuntimeSteering": "Run-time Steering Can Surpass Post-Training: Reasoning Task Performance",
                "Veselovsky2025-Hindsight": "Hindsight Merging: Diverse Data Generation with Language Models"}.get(k)
            if not title and q0["status"] == "VERIFIED-ABSTRACT":
                fid = q0["cache_key"][3:]
                txt = (CACHE / f"or_{fid}.txt").read_text()
                title = re.search(r"^title: (.*)$", txt, re.M).group(1)
            authors = m.get("authors") if m else None
            if k == "Lindsey2024-Crosscoders":
                authors = ["Jack Lindsey", "Adly Templeton", "Jonathan Marcus", "Thomas Conerly", "Joshua Batson", "Christopher Olah"]
            if k == "Veselovsky2025-Hindsight":
                authors = ["Veniamin Veselovsky", "Benedikt Stroebl", "Gianluca Bencomo", "Dilip Arumugam", "Lisa Schut",
                           "Arvind Narayanan", "Thomas L. Griffiths"]
            year = int(m["v1_published"][:4]) if m else ({"Lindsey2024-Crosscoders": 2024, "Veselovsky2025-Hindsight": 2025}.get(k)
                                                          or (2026 if q0["status"] == "VERIFIED-ABSTRACT" else None))
            rels = sorted(set(q["relation"] for q in qs))
            rows = sorted(set(r for q in qs for r in q["rows"].split(";")))
            summ = (f"{q0['venue_status']}. Quoted ({q0['status']}, {q0['version_quoted']}) for {', '.join(rows)}; relation: {', '.join(rels)}. "
                    + (f"Version note: {q0.get('version_note')}. " if q0.get("version_note") else ""))
            srcs.append({"index": n, "url": q0["url"], "title": title, "summary": summ.strip(), "authors": authors, "year": year,
                         "supporting_passages": [{"quote": q["quote"], "locator": f"{q['section']} ({q['version_quoted']})"} for q in qs
                                                 if "[...]" not in q["quote"]]})
        elif k in INHERITED:
            s = INH_SRC[INHERITED[k][0]]
            srcs.append({"index": n, "url": s["url"], "title": s["title"],
                         "summary": f"Inherited from art_kjrCpQnPaniY Table 92c row(s) {INHERITED[k][1]}; cited by row id, not re-verified in this audit.",
                         "authors": s.get("authors"), "year": s.get("year"),
                         "supporting_passages": s.get("supporting_passages", [])[:2]})
        else:
            e = EXTRA[k]
            srcs.append({"index": n, "url": e["url"], "title": e["title"], "summary": e["summary"], "authors": None, "year": None,
                         "supporting_passages": e["passages"]})
    (WS / "research_report.md").write_text(body + "\n\n## Sources\n\n" + "\n".join(
        f"{s['index']}. [{s['title']}]({s['url']}) — {s['summary']}" for s in srcs) + "\n")
    (CACHE / "answer_iter5.md").write_text(body)
    (CACHE / "sources_iter5.json").write_text(json.dumps(srcs, ensure_ascii=False, indent=1))
    print(f"report: {len(body)} chars; sources: {len(srcs)}; unused quoted refs: {sorted(set(BYREF) - set(ORDER))}")


if __name__ == "__main__":
    main()
