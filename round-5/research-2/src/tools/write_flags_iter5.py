"""Write evidence/flags.json (FLAG A/B/C adjudication under the frozen protocol definitions) and
evidence/corrections_iter5.jsonl (title/version/number changes, venue confirmations, citation mismatches).
Candidate axis scores are read from evidence/saturation_hits_iter5.jsonl; decisive sentences from evidence/quotes_iter5.jsonl.
Usage: python -I tools/write_flags_iter5.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import EVID, now_utc  # noqa: E402

PROTO = json.loads((EVID / "protocol.json").read_text())
HITS = {json.loads(l)["id"]: json.loads(l) for l in (EVID / "saturation_hits_iter5.jsonl").read_text().splitlines()}
QUOTES = [json.loads(l) for l in (EVID / "quotes_iter5.jsonl").read_text().splitlines()]


def quote(ref, needle):
    for q in QUOTES:
        if q["ref_key"] == ref and needle in q["quote"]:
            return {"ref_key": ref, "quote": q["quote"], "url": q["url"], "section": q["section"], "status": q["status"]}
    raise KeyError((ref, needle))


def cand(i, ref, needle, why):
    h = HITS.get(i, {})
    return {"id": i, "axes": h.get("axes"), "total": h.get("score"), "claim_scored": h.get("best_claim"),
            "v1_date": h.get("v1_date"), "venue_status": h.get("venue_status"),
            "decisive_sentence": quote(ref, needle), "why_not_full_fire": why}


FLAGS = {
    "generated_utc": now_utc(),
    "protocol_sha256_after_amendment_A1": (EVID / "protocol.sha256").read_text().split()[0],
    "FLAG_A": {
        "definition": PROTO["flags"]["FLAG_A"],
        "verdict": "NOT FIRED",
        "candidates": [
            cand("2605.07284", "Zhou2026-CrossPatching", "hidden state entering the late boundary",
                 "Writes base upstream states into the descendant's late stack (all positions) with boundary and token controls, "
                 "but the outcome is a next-token target margin at the first base/descendant divergence, not output or solution diversity. "
                 "Rubric total 2.5 = occupies B1's METHOD."),
            cand("2503.04429", "Oozeer2025-Transfer", "By replacing the fine-tuned model",
                 "Base activations patched into the fine-tuned (backdoored) model; outcome = backdoor trigger rate, not diversity."),
            cand("2504.02904", "Du2025-PostTrainingReshapes", "patching hidden representations from base to post",
                 "Base-to-post patching of knowledge representations; outcome = factual log-probability ratio."),
            cand("2602.06665", "Zhang2026-SLR", "restoring a carefully chosen range of layers",
                 "Diversity outcome, but restores pre-trained WEIGHTS of a layer interval (weight level, adjacent by definition)."),
            cand("2610.22999", "Sumita2026-FrankenMerging", "combines the lower layers of an aligned model",
                 "Diversity outcome, but a layer splice of weights (aligned lower + base higher), the reverse composition."),
            cand("or:hu5mtofNd4", "Anon2026-LockedEntrance", "layer interpolation restores entrance diversity",
                 "Solution-family diversity restored by layer interpolation (weights) and by text entrance prefixes; Countdown, not code; abstract only."),
            cand("or:lZQK4G4Ktp", "Anon2026-ReDiverse", "precomputed teacher principal directions",
                 "Diversity restored by steering a distilled student along teacher directions: diffusion models, not a base->tuned LLM transplant."),
        ],
        "consequence_for_wording": "The word 'first' is NOT permitted for writing base-model states into a tuned descendant (cross-model "
                                   "patching exists: Prakash et al. 2024; Oozeer et al. 2025; Du et al. 2025; Zhou 2026 cross-patching). "
                                   "Permitted: 'to our knowledge (dated search 2026-10-21), no prior work writes base-model prefill states "
                                   "into the instruct model to test whether post-training's narrowing of solution (algorithm) choice is "
                                   "carried by those states; cross-model patching of base states exists for other outcomes, and "
                                   "base/aligned mixing for diversity exists at the token, logit and weight level.'",
    },
    "FLAG_B": {
        "definition": PROTO["flags"]["FLAG_B"],
        "verdict": "PARTLY FIRED",
        "candidates": [
            cand("2607.20543", "Zhou2026-PassK", "frozen base-model behavior",
                 "Per-prompt forecast from frozen-base evidence of where GRPO loses coverage: training time, correctness coverage (math). "
                 "PARTLY FIRED by the frozen rule."),
            cand("2610.04978", "Duan2026-WhatWillPTFix", "A priori signals capture a minority",
                 "Per-problem forecast of post-training gains from base pass rate / likelihood: training time, correctness; "
                 "the base signals explain only a minority of the explainable variance (contradicts-in-part)."),
            cand("or:6a4v7CpeAu", "Anon2026-Lookahead", "predicting which IFEval prompts degrade",
                 "Per-prompt forecast of post-training degradation from base model + reward model: training time."),
            cand("or:uASUNrduuj", "Anon2026-HowMuchNotWhere", "frozen base-correct trajectories",
                 "Per-prompt decay of base-correct likelihood forecasts RLVR damage during training; random-prompt anchoring protects as well."),
            cand("2510.02230", "Nguyen2025-RBP", "disproportionately reinforces",
                 "Base likelihood orders which problems RLVR reinforces vs suppresses (mechanism; anchor outside window)."),
            cand("2510.01171", "Zhang2025-VS", "amplifying its modes while suppressing the tails",
                 "Stylised: aligned optimum = power-sharpened reference policy; no per-task test (PARTLY FIRED: stylised)."),
            cand("2606.29933", "Samanta2026-Crystallization", "single seed distribution present in the pretrained",
                 "SFT collapses onto a seed distribution already present in the pretrained model; retrospective, random-generation tasks."),
            cand("or:ooV5M72O08", "Anon2026-SameCandidates", "remain within the pretrained Top-16",
                 "Post-training top-1 changes mostly stay within the base top-16 (retrospective, token level)."),
        ],
        "consequence_for_wording": "A1 may not claim to be the first to predict from the base model where post-training narrows: "
                                   "training-time, per-prompt forecasts of coverage loss from frozen-base evidence exist (Zhou 2026; Duan 2026; "
                                   "Lookahead). A1's defensible addition is an INFERENCE-TIME forecast of the tuned model's movability on "
                                   "algorithm choice from the base model's per-task algorithm distribution, scored on matched events. A2 "
                                   "(where a push or ban lands = the base model's runner-up) has only stylised/retrospective support "
                                   "(power-sharpening; base top-k inheritance; seed-distribution collapse) and may be worded 'to our knowledge'.",
    },
    "FLAG_C": {
        "definition": PROTO["flags"]["FLAG_C"],
        "verdict": "PARTLY FIRED",
        "candidates": [
            cand("2503.00691", "Lee2025-AlgoDiv", "decreases algorithmic diversity in AtCoder-introductory",
                 "Base vs Instruct DeepSeek-Coder-6.7B, test-checked correctness, LLM-judge (Llama-3.1-8B-Instruct) algorithm clusters, "
                 "one pair, MIXED direction (decrease on easy AtCoder-introductory problems, increase elsewhere)."),
            cand("2605.28022", "LeBronnec2026-RedundancyRLVR", "decreases JPlag diversity",
                 "Base vs RLVR descendants on code with execution tests; structural (JPlag) and embedding (Vendi) diversity, not algorithm-level."),
            cand("2610.19157", "Jangra2026-DivAlgo", "uncontrolled sampling",
                 "DivAlgo (24 code models) has NO base-vs-instruct pairing (checked by grep on the full text); included here as a negative check."),
        ],
        "consequence_for_wording": "Strike 'first base-versus-tuned algorithm-level comparison'. The premise row reads 'contradicting in part' "
                                   "(Lee et al. find instruction tuning increases algorithmic diversity on harder problems). The run may claim "
                                   "test-checked mechanism labels over correct programs (runtime tracer, AST, blind judge) rather than LLM-judge "
                                   "clusters, a per-task base repertoire committed by sha256 before any push, and the same chat-templated prompt "
                                   "for base and instruct (with the template confound flagged by Nakamura 2026).",
    },
}

CORR = [
    ("version/title/number", "2506.17871", "Yang, Li & Holtzman: latest version is v4 (2026-09-12, comment 'V4: TMLR 2026 Accepted'), not v3. Title v1 'How Alignment Shrinks the Generative Horizon' -> v3/v4 'LLM Probability Concentration: How Alignment Shrinks the Generative Horizon'. Headline: v1 'reducing BF by nearly an order of magnitude (e.g., from 12 to 1.2) relative to base models' -> v3/v4 'by a factor of 2–5 overall, and up to an order of magnitude ... at the beginning positions'. The strategy text's 'about an order of magnitude' is the v1 figure."),
    ("version/title", "2410.09300", "Nudging: v1 title 'Nudging: Inference-time Alignment via Model Collaboration' -> v4 'Nudging: Inference-time Alignment of LLMs via Guided Decoding'. Venue ACL 2025 (main) confirmed: Anthology ID 2025.acl-long.623."),
    ("version/title", "2605.30526", "PASTA: v1 'Measuring, Localizing, and Ablating Alignment Signatures in LLMs' -> v2 (2026-10-20) 'Measuring, Localizing, and Reducing the AI-Like Writing Style of Post-Trained LLMs'."),
    ("version/title", "2607.12796", "One-Word Census: v4 (2026-10-09) comment 'Updated title, no other changes'; quoted at v4."),
    ("version", "2507.14843", "Invisible Leash is at v5 (2026-10-14); quoted at v5."),
    ("name", "2406.05587", "Author is Behnam Mohammadi (plan wrote 'Mohammedi'). arXiv HTML v1 is unavailable (HTTP 404); quoted from PDF v1."),
    ("venue", "2606.01811", "Decan metric paper is an ICML 2026 WORKSHOP paper (Workshop on Generative AI, Creativity, and Human-AI Co-Creation, non-archival), not ICML 2026 main track."),
    ("venue confirmed", "2510.02230", "Reasoning Boundary Paradox: NeurIPS 2026 poster page https://neurips.cc/virtual/2026/poster/150680 lists the title (arXiv v1 2025-10-02, no newer version)."),
    ("venue confirmed", "2511.05650", "BACo: ICML 2026 (arXiv v2 comment)."),
    ("venue confirmed", "2510.13900", "Activation Difference Lens: ICLR 2026 (arXiv v3 comment)."),
    ("venue confirmed", "2503.00691", "Lee et al.: Findings of EMNLP 2025, Anthology ID 2025.findings-emnlp.10 (page re-fetched)."),
    ("venue", "2507.12638", "Ward et al. is an ICML 2025 Workshop on Actionable Interpretability paper (workshop, not main track)."),
    ("resolved id", "2510.07364", "Venhoff et al. 'Base Models Know How to Reason, Thinking Models Learn When' = arXiv 2510.07364 (v4), ICML 2026 spotlight (comment)."),
    ("resolved id", "2510.03215", "Cache-to-Cache = arXiv 2510.03215 (v2), ICLR 2026 (comment)."),
    ("resolved id / description", "2511.19131", "2511.19131 = 'Eliciting Chain-of-Thought in Base LLMs via Gradient-Based Representation Optimization' (AAAI 2026). A pre-trained classifier is the LIKELIHOOD TERM of a hidden-state optimisation (with a prior keeping states near the original), not a classifier 'deciding when to intervene' as the plan described."),
    ("description", "2504.10478", "Dang et al. WiSE-FT interpolates the latest SFT checkpoint with an EARLY SFT checkpoint (w0), not the base model; venue COLM 2025 (journal_ref). A coding appendix exists (Qwen2.5-coder-0.5B, Magicoder-Evol-Instruct-110K)."),
    ("number verified", "Hindsight Merging (PMLR v286 veselovsky25a)", "Verified on the PMLR page: 'achieving a consistent 20-50% increase in pass@10 relative to the instruction tuned model across a coding benchmark and series of models'. Interpolation is with a previous training checkpoint."),
    ("author", "2607.20543", "Single author Todd Zhou; no venue line. Not the same author as Yifan Zhou (2605.07284, cross-patching)."),
    ("author", "2605.09995", "'Annotations Mitigate Post-Training Mode Collapse': first author Jacob Mitchell Springer; ICML 2026 (comment)."),
    ("venue unconfirmed", "2310.06452 / 2412.01951 / 2312.01552 / 2310.12962 / 2311.14479", "ICLR venue status given in the plan for Kirk et al., Huang et al., URIAL, EFT and model arithmetic is NOT confirmed here (no venue in arXiv comment/journal_ref; no venue page fetched). They are cited as arXiv preprints with 'venue per plan, unconfirmed'."),
    ("scope check", "2407.02209", "Generative Monoculture compares pre-trained vs aligned Llama-2 only on book reviews; its code experiments use GPT-3.5/GPT-4 because 'neither of the models were able to produce code solutions' (CodeLlama, StarCoder). No base-vs-chat code comparison."),
    ("scope check", "2610.19157", "DivAlgo's 24 models contain no base-vs-instruct pairing analysis; 'base model' occurs only for the metric's base classifier."),
    ("tool limitation", "OpenAlex cites:", "OpenAlex records cited_by_count = 0 for BACo, Lee et al., Ward et al. and Zhou (T.) 2026, so 'works?filter=cites:' returned 0 citing works; the plan's expectation that OpenAlex closes the Google-Scholar gap does not hold. Forward citations rest on Semantic Scholar only."),
    ("tool limitation", "2507.20956", "Conformative decoding is not indexed in Semantic Scholar (arXiv lookup HTTP 404; title match not found): its forward citations could not be chased."),
    ("tool limitation", "ICLR 2027 submissions", "OpenReview PDFs return HTTP 403 (openreview.net/pdf?id=...); every ICLR 2027 row is VERIFIED-ABSTRACT via the public notes/search API."),
    ("citation mismatch", "2503.00691 (inherited 92c C1d)", "Iteration-4 quoted only Lee et al.'s abstract; the base-vs-instruct finding (Findings 5) was not in Table 92c. 92d-A0 now quotes it."),
    ("protocol amendment", "evidence/protocol.json", "Amendment A1: hand-typed frozen_utc corrected to the file's write time 14:50:21Z (before the first search call at 14:51:23Z); sha256 before/after in evidence/protocol_amendments.jsonl."),
]


def main():
    (EVID / "flags.json").write_text(json.dumps(FLAGS, indent=1, ensure_ascii=False))
    out = EVID / "corrections_iter5.jsonl"
    out.write_text("".join(json.dumps({"type": t, "item": i, "correction": c, "logged_utc": now_utc()}, ensure_ascii=False) + "\n"
                           for t, i, c in CORR))
    print("flags:", {k: v["verdict"] for k, v in FLAGS.items() if k.startswith("FLAG")}, "| corrections:", len(CORR))


if __name__ == "__main__":
    main()
