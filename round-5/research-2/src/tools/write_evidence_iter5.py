"""Write the scored saturation hits (rubric of evidence/protocol.json), flag adjudication, PRISMA-style counts per
query family, the inherited-id list and the corrections log for the iteration-5 audit.

Scores are the executor's manual screening decisions after reading title+abstract (all) and full text (every hit
scoring >= 1.5 on its best claim, except ICLR 2027 submissions whose PDFs return HTTP 403 -> abstract only).
Usage: python -I tools/write_evidence_iter5.py
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import EVID, WS, now_utc  # noqa: E402

META = json.loads((EVID / "arxiv_meta.json").read_text())

# id, claim, O, I, C, venue_status, full_text_checked, source, note
H = [
    # ---- B1 / FLAG A (transplant of base states into the tuned model) ----
    ("2605.07284", "B1", 0.5, 1, 1, "arXiv preprint", True, "FC(Minder crosscoder)+R2",
     "Cross-patching: base upstream hidden state written into the descendant's late stack at every sequence position (keys/values recomputed); boundary sweep 40% depth to final block, random-later-disagreement and history controls. Outcome = next-token target margin at first divergence (+ suffix exact-answer accuracy), not solution diversity. Occupies B1's method; FLAG A not fired (no diversity outcome)."),
    ("2602.06665", "B1", 1, 0.5, 0.5, "arXiv preprint", True, "FC(VerbalizedSampling)",
     "Selective Layer Restoration: restores a chosen interval of layers of the post-trained model to pre-trained weights; recovers diversity (creative writing, open QA, reasoning; Llama/Qwen/Gemma). Weight-level, no code, no matched-random control."),
    ("2610.22999", "B1", 1, 0.5, 0.5, "arXiv preprint", True, "F1/F3/F5 (E3,E4); seen by iter-4, re-screened",
     "Depth-aware FrankenMerging: aligned lower layers + base higher layers; higher semantic diversity than aligned; better trade-off than temperature. Weight/layer splice (reverse composition of B1); text tasks only."),
    ("or:hu5mtofNd4", "B1", 1, 0.5, 0.5, "ICLR 2027 submission", False, "F2 (E5)",
     "Locked at the Entrance: RLVR contraction concentrated at the entrance (first operand/operator family) on Countdown; entrance prefix restores low-access families; layer interpolation restores entrance diversity (+37% coverage). Weight-level; arithmetic puzzle, not code. Abstract only (PDF 403)."),
    ("or:lZQK4G4Ktp", "B1", 1, 0.5, 0.5, "ICLR 2027 submission", False, "F5 (E5)",
     "ReDiverse (diffusion distillation): diversity collapse localized to an intermediate block at the first denoising step; training-free steering along teacher principal directions restores diversity. Cross-domain analogue (images/video)."),
    ("or:MYXgOex05m", "B1", 1, 0, 0, "ICLR 2027 submission", False, "F1/F3/F5/F6/F9 (E5)",
     "Merging the SFT model with its pretrained base before RL restores diversity (math and code benchmarks). Whole-model weight merge; no site or random controls."),
    ("2602.16189", "B1", 0, 0.5, 0.5, "arXiv preprint", True, "E6 (WebSearch)",
     "Model transplant of activation-selected modules (weights) between Gemma-2-2B and -IT (mostly IT->base); outcome math accuracy."),
    ("2604.13694", "B1", 0, 0.5, 0.5, "arXiv preprint", True, "F4 (E4), E6",
     "Weight Patching (specialized -> base, fixed input) with a cross-model activation-patching companion; instruction following."),
    ("2608.30319", "B1", 0, 0.5, 0, "EMNLP 2026", True, "F3 (E3)",
     "CREST: steers base-model hidden representations with safety directions from a guidance model of another family."),
    ("2610.24663", "C", 0.5, 1, 0.5, "arXiv preprint", True, "F1/F3 (E3)",
     "rl-replace: borrow RL model's token only where greedy choices differ (~4%); keeps much of base diversity (pass@256 67.5% vs RL 61.4%). Token-level base/RL collaboration on math, not code."),
    ("or:3QlKFFBcNO", "C", 0, 1, 0.5, "ICLR 2027 submission", False, "F2 (E5)",
     "Word transplant at disagreement positions between base and reasoning model; random-position control. Accuracy outcome."),
    ("or:cMasrdysrX", "C", 0, 1, 0.5, "ICLR 2027 submission", False, "F2 (E5)",
     "Prefix transplantation (trained policy writes k tokens, base the rest) as a conserved ledger of RLVR gain; early credit mostly format."),
    ("2604.02319", "C", 0.5, 0.5, 0.5, "COLM 2026", True, "FC(BACo? no) / screened from candidates",
     "Per-prompt router picks the model that gives the most diverse answer set (18 LLMs)."),
    ("2608.07460", "C", 0.5, 0.5, 0.5, "arXiv preprint", True, "planning seed; FC(BACo)",
     "CreativeInstruct distils BACo-style base/aligned routing into one model; notes two-model methods need released base models."),
    ("or:tzXBBz5tmq", "C", 0, 0.5, 0, "ICLR 2027 submission", False, "F2/F6 (E5)",
     "Logit grafting: post-training delta changes argmax at 4-13% of steps; transfer of logit deltas to other models."),
    ("2605.30021", "B1", 0.5, 0.5, 0, "arXiv preprint (under review)", True, "planning seed; FC(BACo)",
     "ReDiPO: base-model responses recover answer modes removed by post-training (DPO training)."),
    # ---- B2/D (push along base-minus-tuned direction) ----
    ("2605.30526", "B2_D", 0.5, 1, 1, "arXiv preprint", True, "FC(BACo)",
     "PASTA: aligned-minus-base residual direction ablated during aligned-model decoding; five orthogonal unit random directions with the same hook footprint as control; outcome AI-detector visibility; 'greater stylistic variation' only qualitative. Occupies B2/D's method and control; outcome not diversity. v2 retitled."),
    ("or:vkIOGTVcJP", "B2_D", 0, 1, 0, "ICLR 2027 submission", False, "F4/F5 (E5)",
     "TIRD: post-minus-base activation directions; suppression degrades post-trained model; injection improves base. Accuracy outcome; no isotropic control stated in abstract."),
    ("2605.24583", "B2_D", 0, 0.5, 1, "arXiv preprint", True, "F4/F7 (E4)",
     "Template-controlled difference-in-differences for aligned-minus-base activation shifts: naive contrast confounded by the chat template the base never saw."),
    # ---- A1 / A2 / FLAG B ----
    ("2607.20543", "A1", 1, 1, 0.5, "arXiv preprint", True, "planning seed; FC(Zhou) round",
     "Per-prompt regimes from frozen base-model behaviour predict where GRPO loses coverage (boundary prompts); PBA anchors risky prompts to the base. Training-time, correctness coverage (math) -> FLAG B PARTLY FIRED by the frozen rule."),
    ("2610.04978", "A1", 1, 1, 0.5, "arXiv preprint", True, "F2 (E3,E4)",
     "Per-problem post-training gains: a-priori base signals (pass rate, likelihood of a correct solution) explain only 0.30/0.24 of explainable variance; another checkpoint predicts better. Training-time, correctness (math). Contradicts-in-part any 'base distribution predicts narrowing' claim; FLAG B PARTLY FIRED."),
    ("or:6a4v7CpeAu", "A1", 1, 0.5, 0.5, "ICLR 2027 submission", False, "F2 (E5)",
     "Lookahead: base model + reward model predicts which IFEval prompts degrade after RLHF training (F1- margin over BoN). Training-time per-prompt forecast; FLAG B PARTLY FIRED."),
    ("or:uASUNrduuj", "A1", 1, 0.5, 0.5, "ICLR 2027 submission", False, "F2 (E5)",
     "Per-prompt decay rate of likelihood of frozen base-correct trajectories (MATH, MBPP) predicts RLVR damage; random-prompt anchoring protects as well (contradicts targeting)."),
    ("2510.02230", "A1", 1, 1, 0.5, "NeurIPS 2026 (poster)", True, "planning seed (anchor, v1 2025-10)",
     "Winner-take-all: RLVR reinforces problems with high base likelihood and suppresses low-likelihood ones. Anchor outside window."),
    ("or:BEcwcRFQdu", "A1", 0, 1, 0.5, "ICLR 2027 submission", False, "F1-F7 (E5)",
     "Per-head signed forecast of post-training changes from the base model alone (GPT-2 ... 1.5B)."),
    ("2602.04735", "A1", 0.5, 0.5, 0.5, "arXiv preprint", True, "F2 (E4)",
     "Data2Behavior/MDF: mean data representations injected into a base model's forward pass to predict unintended post-training behaviours."),
    ("2603.06957", "A1", 0, 1, 0.5, "ICML 2026", True, "F2 (E3,E4)",
     "Theory: post-training error governed by the base model's Likelihood Quantile; barrier to leaving base support."),
    ("2507.21509", "A1", 0.5, 0.5, 0.5, "arXiv preprint", True, "planning seed (anchor)",
     "Persona vectors: projection difference between training data and base generations predicts post-finetuning trait expression."),
    ("or:ooV5M72O08", "A2", 0, 1, 0.5, "ICLR 2027 submission", False, "R2 (E5)",
     "92.9% of post-training top-1 changes stay within the pretrained top-16 at consequential decisions; preferences reorganized. Token-level, retrospective."),
    ("2606.29933", "A2", 0.5, 1, 0.5, "arXiv preprint", True, "FC(Yang-Holtzman)",
     "SFT 'nucleation' collapses onto a seed distribution present in the pretrained LLM; RL keeps the same options (random-generation tasks). Stylised support for A2."),
    ("or:iIw2d3AkJM", "A2", 0.5, 1, 0.5, "ICLR 2027 submission", False, "F2 (E5)",
     "Base-model starting token cues recover much of the RL gain (math and coding); RL makes the same cues more likely."),
    ("2608.11426", "A2", 0, 0.5, 0.5, "arXiv preprint", True, "F1 (E3), E6",
     "Homogeneity learned in pretraining, revealed/amplified by SFT; base models collapse under prompting alone (open-ended text)."),
    ("2510.01171", "A2", 0, 1, 0.5, "arXiv preprint", True, "planning seed (anchor)",
     "Stylised: aligned optimum is a power transform of pi_ref that amplifies its modes (typicality bias); no per-task test. FLAG B PARTLY FIRED (stylised)."),
    ("2312.01552", "A2", 0, 1, 0.5, "arXiv preprint", True, "planning seed (anchor)",
     "Aligned top-ranked tokens mostly within base top-5; shift concentrated on stylistic tokens and earlier positions."),
    ("2504.07912", "A2", 0.5, 0.5, 0.5, "COLM 2025", True, "BC(Zhou)",
     "RL converges to a dominant output distribution amplifying pretraining patterns (models trained from scratch). Anchor."),
    # ---- A0 / FLAG C ----
    ("2503.00691", "A0", 1, 1, 0.5, "Findings of EMNLP 2025", True, "planning seed; inherited",
     "DeepSeek-Coder-6.7B Base vs Instruct, test-checked correctness, LLM-judge (Llama-3.1-8B-Instruct) algorithm clusters; instruction tuning lowers algorithmic diversity on AtCoder-introductory, raises it elsewhere. FLAG C PARTLY FIRED; contradicts the premise in part."),
    ("2605.28022", "A0", 0.5, 1, 0.5, "arXiv preprint (under review)", True, "FC(Lee)",
     "Base vs RLVR descendants (Qwen3-4B/8B, Olmo3-7B) on MBPP/CodeContests/TACO: JPlag diversity decreases in 57.2% and Vendi in 65.3% of 2,745 prompt-level comparisons; structural, not algorithm-level."),
    ("2603.02787", "A0", 0.5, 0, 0, "ICLR 2026", True, "FC(DivAlgo) / screened",
     "BehaveSim: execution-trajectory algorithm similarity (precedent for runtime-trace mechanism labels); no base/instruct comparison."),
    ("2610.19157", "A0", 1, 0, 0, "arXiv preprint", True, "inherited; FC(Lee)",
     "DivAlgo: 24 code models, no base-vs-instruct pairing (grep: 'base model' only for the metric's base classifier)."),
    ("2407.02209", "A0", 0.5, 0.5, 0, "ICLR 2025", True, "planning seed (anchor)",
     "Monoculture: pre-trained vs aligned Llama-2 compared on book reviews only; code experiments on GPT-3.5/GPT-4 (open code models failed to produce code)."),
    ("2603.24124", "A0", 0.5, 1, 0, "arXiv preprint", True, "FC(VerbalizedSampling)",
     "Base-vs-instruct single-cluster rate 1.0% vs 28.5% (Qwen3-14B, TruthfulQA); stage ablation points to DPO. Text QA, not code."),
    ("2607.12796", "A0", 0.5, 0.5, 0, "arXiv preprint", True, "FC(Yang-Holtzman)",
     "105-model one-word census: lightly post-trained models most divergent, heavily post-trained most conformist; base->SFT ladder moves most."),
    ("2609.33936", "A0", 0, 0, 0, "arXiv preprint", True, "FC(VerbalizedSampling)",
     "Contradicting evidence: Artificial Hivemind homogeneity results overstated (one dominant vehicle plus heavy tail)."),
    ("2609.16454", "A0", 0, 0, 0, "arXiv preprint", True, "FC(VerbalizedSampling)",
     "Contradicting evidence: mode collapse or over-dispersion depends on model and dataset; SFT converges toward the target distribution."),
    ("2605.30844", "A0", 0, 0, 0, "arXiv preprint", True, "FC(BACo, Yang-Holtzman)",
     "Contradicting evidence: length-confounded diversity analyses; canopy entropy."),
    ("2606.01811", "A1", 0, 1, 0, "ICML 2026 workshop (non-archival)", True, "E6 lookup",
     "Decan: diversity read from a base model's per-token log-probabilities; drops base->SFT->DPO->RLVR on OLMo-2-7B."),
    ("2605.16874", "C", 0, 0.5, 0.5, "ICML 2026", True, "FC(Ward)",
     "Base-reasoning gap concentrated on few early planning-related decision tokens; correcting them restores reasoning."),
    ("2609.33085", "A1", 0.5, 0, 0.5, "arXiv preprint", False, "BC(Duan) round 3",
     "Finite sampling concentrates on a dominant strategy while alternatives already supported by the model stay unexplored (RLVR exploration)."),
    ("2608.04893", "B1", 0, 0, 1, "arXiv preprint", False, "FC(Oozeer) round 3",
     "Causal audit of relayed KV caches with deranged, zeroed and moment-matched random cache controls (multi-agent)."),
]

WINDOW_START = "2026-01-01"


def v1_of(i):
    m = META.get(i)
    return (m or {}).get("v1_published", "")[:10]


def tags(i, venue, v1):
    t4 = bool(v1) and v1 > "2026-06-21"
    if i.startswith("or:"):
        return True, "contemporaneous (ICLR 2027 submission)"
    if "preprint" in venue:
        return t4, "exempt (arXiv-only)"
    pub_year = re.search(r"20\d\d", venue)
    if pub_year and int(pub_year.group(0)) >= 2026 and "workshop" not in venue.lower():
        return t4, "peer-reviewed 2026: check publication date vs 2026-07-17"
    return t4, "not contemporaneous (published before 2026-07-17)"


def main():
    cands = {json.loads(l)["key"]: json.loads(l) for l in (EVID / "saturation_candidates_iter5.jsonl").read_text().splitlines()}
    out = EVID / "saturation_hits_iter5.jsonl"
    out.write_text("")
    verdicts = Counter()
    rows = []
    for (i, claim, o, ii, c, venue, ft, src, note) in H:
        v1 = v1_of(i)
        if i.startswith("or:"):
            title = (cands.get(i) or {}).get("title", "")
            v1 = "2026 (ICLR 2027 submission)"
        else:
            title = (META.get(i) or {}).get("title", "") or (cands.get(i) or {}).get("title", "")
        score = o + ii + c
        verdict = "occupies" if score >= 2.5 else ("adjacent" if score >= 1 else "irrelevant")
        in_window = i.startswith("or:") or (v1 >= WINDOW_START)
        t4, iclr = tags(i, venue, v1 if not i.startswith("or:") else "")
        rec = {"id": i, "title": title, "v1_date": v1, "in_window": in_window, "best_claim": claim,
               "axes": {"O": o, "I": ii, "C": c}, "score": score, "verdict": verdict,
               "venue_status": venue, "contemporaneous_4mo": t4, "iclr2027_rule": iclr,
               "full_text_checked": ft, "source": src, "note": note, "scored_utc": now_utc()}
        rows.append(rec)
        verdicts[(verdict, in_window)] += 1
        with out.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print("scored hits:", len(rows), dict(verdicts))

    # ---------------- PRISMA-style counts per family ----------------
    log = [json.loads(l) for l in (EVID / "search_log_iter5.jsonl").read_text().splitlines()]
    raw = Counter()
    for r in log:
        raw[r["family"]] += int(r.get("n_results") or 0)
    scr = {json.loads(l)["key"]: json.loads(l) for l in (EVID / "screening_iter5.jsonl").read_text().splitlines()}
    fam_records = defaultdict(set)
    for k, c in cands.items():
        for f in c.get("families", []):
            fam_records[f].add(k)

    def inw(c):
        aid = c.get("arxiv_id") or ""
        return bool(re.match(r"26(0[1-9]|1[0-2])\.", aid)) or "E5" in c.get("engines", []) or \
            any(str(d).startswith("2026") for d in c.get("dates", []))

    groups = json.loads((EVID / "protocol.json").read_text())["prescreen_keyword_groups"]
    grx = {g: re.compile(p, re.I) for g, p in groups.items()}
    hit_ids = {r["id"] for r in rows}
    key_of = {}
    for k, c in cands.items():
        if c.get("arxiv_id"):
            key_of[c["arxiv_id"]] = k
        if c.get("openreview_id"):
            key_of["or:" + c["openreview_id"]] = k
    counts = {}
    for f in sorted(fam_records):
        recs = [cands[k] for k in fam_records[f]]
        w = [c for c in recs if inw(c)]
        kp = [c for c in w if sum(bool(rx.search((c.get("title", "") + " " + c.get("abstract", "")).lower()))
                                  for rx in grx.values()) >= 2]
        inc = [r for r in rows if key_of.get(r["id"]) in fam_records[f]]
        counts[f] = {"identified_raw": raw.get(f, 0), "unique_records": len(recs), "in_window": len(w),
                     "passed_keyword_prescreen": len(kp),
                     "full_text_or_abstract_checked_scored": len(inc),
                     "included_adjacent_or_occupying": sum(r["verdict"] != "irrelevant" for r in inc),
                     "occupying": sum(r["verdict"] == "occupies" for r in inc)}
    allc = list(cands.values())
    counts["_totals"] = {
        "logged_calls": len(log), "raw_hits": sum(int(r.get("n_results") or 0) for r in log),
        "unique_records": len(allc), "seen_in_iteration4_audit": sum(bool(c.get("seen_in_iter4")) for c in allc),
        "in_window": sum(inw(c) for c in allc),
        "keyword_prescreen_pass_in_window": sum(
            1 for c in allc if inw(c) and sum(bool(rx.search((c.get("title", "") + " " + c.get("abstract", "")).lower()))
                                              for rx in grx.values()) >= 2),
        "manual_title_screen_shortlists": {"base_vs_tuned (in window, not limited to top 100)": 311,
                                           "code_x_diversity": 248, "activation_x_diversity": 108,
                                           "round2_new_in_window": 344, "round3_new_in_window": 25},
        "scored_hits": len(rows), "scored_in_window": sum(r["in_window"] for r in rows),
        "verdicts": {f"{k[0]}|{'in' if k[1] else 'out'}-window": v for k, v in verdicts.items()},
        "note": "Families F1-F9 = round 1 (protocol queries); R2 = round 2 (6 queries from included-hit vocabulary); "
                "FC = forward citations (S2; OpenAlex returned 0 citing works because cited_by_count=0 for all four seeds); "
                "BC = backward references of the two closest hits per flag (round 3). Raw counts include E6 grey-literature "
                "calls only via evidence/search_log_iter5.jsonl entries.",
    }
    (EVID / "saturation_counts_iter5.json").write_text(json.dumps(counts, indent=1))
    print(json.dumps(counts["_totals"], indent=1))


if __name__ == "__main__":
    main()
