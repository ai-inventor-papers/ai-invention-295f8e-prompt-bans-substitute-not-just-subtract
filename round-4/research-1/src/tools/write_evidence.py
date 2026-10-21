"""Write evidence/saturation_hits.jsonl, evidence/corrections.jsonl and evidence/saturation_counts.json.

Verdict rubric (plan 3.7), applied per hit against the claim it touches. Axes: O = object (algorithm/solution identity
checked by execution or mechanism label), I = intervention (claim-specific), C = contrast (claim-specific).
Each axis scores 1 (match), 0.5 (partial) or 0. Documented relaxation of the plan's integer rubric to allow partial
matches: occupies >= 2.5; adjacent 1-2; irrelevant < 1. (Under the plan's literal rubric - only full matches count -
no hit occupies any claim either.)
Contemporaneity: plan convention = v1 after 2026-06-21 (four months before 2026-10-21); ICLR 2027 Reviewer Guide =
peer-reviewed publication within two months of the deadline, arXiv-only papers never required.
Usage: python -I tools/write_evidence.py
"""
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, EVID  # noqa: E402

META = json.loads((EVID / "arxiv_meta.json").read_text())
CUTOFF_4M = "2026-06-21"

# id, claim(s), O, I, C, venue, one-line note, full_text_checked, source ("planning" pre-screen / "search" / "FC")
HITS = [
    ("2606.10302", "C1-site,C1", 0, 0.5, 1, "arXiv preprint; ICLR 2027 submission (OpenReview AnsxpIWvcZ)",
     "Text-level diversity sources (Level 0/1/2) + transmission score; no activation site, no code, no test-checked labels.", True, "planning"),
    ("2604.03380", "C1,C1-site,b6", 0, 1, 1, "BEA @ ACL 2026 (v2 comment)",
     "Four internal noise-injection sites vs high temperature on Arabic narratives; generated-token positions only; RMS-calibrated.", True, "planning"),
    ("2601.22010", "C1,b6,FLAG-A", 0, 1, 1, "ICLR 2026 (comment)",
     "Stiefel activation steering for diverse test cases (execution-checked validity, coverage) vs temperature; object is test coverage, not algorithm identity.", True, "planning"),
    ("2605.11936", "C1,C1-site,b6", 0, 1, 1, "ICML 2026 MI Workshop spotlight (comment + icml.cc)",
     "Random embedding vectors appended to input; branching in first tokens; math only; code named as future work.", True, "planning"),
    ("2605.08221", "b6", 0, 1, 0.5, "arXiv preprint",
     "Noise in latent (Coconut) trajectories for consensus/abstention; not diversity of solution identity.", True, "planning"),
    ("2606.15092", "b6", 0, 0.5, 0, "arXiv preprint; ICLR 2027 submission (MxTe9wDyk8)",
     "Steering-method upgrade (random projection); no diversity/knob contrast.", True, "planning"),
    ("2607.05615", "b6", 0, 0.5, 0, "arXiv preprint", "Stochastic token/block gating of SAE steering; method variant.", True, "planning"),
    ("2608.07852", "-", 0, 0, 0, "arXiv preprint", "SAE anatomy of assistant personas; unrelated.", True, "planning"),
    ("2606.11599", "b7,C3a,FLAG-B", 0, 0.5, 0.5, "arXiv preprint",
     "Predicts under/succeed/over-steer of the same white-box intervention (~0.7 macro-F1); no prompting outcome.", True, "planning"),
    ("2604.27251", "b7,C3a", 0.5, 0.5, 0, "Findings of EMNLP 2026 (comment)",
     "Reasoning-type instruction compliance; instruction decodable without compliance; steering toward compliance.", True, "planning"),
    ("2602.04297", "b2", 0, 0, 0, "arXiv preprint", "Prompt sensitivity in text classification due to underspecification.", True, "planning"),
    ("2604.18389", "b2", 0, 0, 0, "arXiv preprint", "Taylor-expansion account of prompt sensitivity.", True, "planning"),
    ("2604.01639", "C2,C3a", 0, 0.5, 0, "arXiv preprint (under review at COLM 2026)",
     "Answer flips under meaning-preserving perturbations localised by activation patching (GSM8K).", True, "planning"),
    ("2605.30789", "-", 0, 0, 0, "arXiv preprint", "Training-time GRPO rollout diversity from smaller models.", True, "planning"),
    ("2606.14530", "C2", 0.5, 0.5, 0, "arXiv preprint (v3)", "Code correctness decodable from final prompt token (AUC 0.881 in v3).", True, "planning"),
    ("2605.07984", "C2", 0, 1, 0.5, "ICML 2026 MI Workshop (comment)", "Probe vs patching dissociation for rhyme planning; only Gemma-3-27B causal.", True, "planning"),
    ("2606.17648", "C2", 0.5, 0.5, 0, "arXiv preprint (v3)", "Answer linearly recoverable before the model can read it (code reasoning).", True, "planning"),
    ("2610.19157", "C1,C3c", 1, 0, 1, "arXiv preprint", "Algorithmic diversity of code vs humans under temperature/verbalized/iterative prompting; prompt-based steering only.", True, "planning"),
    ("2609.00077", "C1-seed,C1", 1, 0, 0.5, "EMNLP 2026 (comment)", "Surface edit diversity stable while mechanism-level diversity collapses; HiTemp baseline.", True, "planning"),
    ("2606.04057", "C1,C3b", 1, 0.5, 0, "ICML 2026 poster (icml.cc)", "Incidental cues shift algorithm families up to 100 pp among correct outputs; direct naming best mitigation.", True, "planning"),
    ("2606.21619", "b4", 0, 0.5, 0, "arXiv preprint", "Incomplete constrainers push decoding into low-probability regions (-97% correctness).", True, "planning"),
    ("2610.09571", "C3b,b1", 0.5, 1, 0, "arXiv preprint (under review)", "Negation: suppress original + promote favoured in-category candidate; 37-71% repeat.", True, "planning"),
    # ---- new hits from the 2026-10-21 saturation search ----
    ("2608.21595", "C1,C1-site", 0, 1, 1, "arXiv preprint",
     "Gaussian noise in the last hidden layer of the prompt-encoding pass vs temperature/pixel noise, for RLVR rollouts (VLM geometry).", True, "search"),
    ("or:wJ8HkA8vGN", "C1,C3c,b6", 0, 1, 1, "ICLR 2027 submission",
     "Latent-chain perturbation adds answer diversity but no exploration gain vs explicit sampling (latent reasoners).", False, "search"),
    ("or:oag3wgNLRh", "C1,C3c,b6", 0, 1, 1, "ICLR 2027 submission",
     "Reasoning steering redirects among already-supported trajectories; departure-matched stochastic decoding matches it.", False, "search"),
    ("2604.24927", "C1,C1-seed", 0.5, 0.5, 1, "ICML 2026 (comment)",
     "ESamp: latent-prediction-error-guided decoding for semantic (not lexical) exploration; LiveCodeBench pass@k.", True, "search"),
    ("2608.30345", "C1,FLAG-A", 0.5, 0, 0.5, "EMNLP 2026 Main (comment)",
     "Tree search guided by hidden states of probed answers to separate distinct solution paths; no perturbation.", True, "search+FC"),
    ("2610.01382", "C1", 0, 0, 1, "arXiv preprint", "Gacha Decoding: diversity as instruction following + external RNG (text-level plan sampler; cites 2606.10302).", True, "FC"),
    ("2608.09351", "C1-site", 0, 0, 1, "NeurIPS/COLM 2026 workshops (comment)", "Where to inject diversity at the input level (rephrase/spelling/image) for aggregation accuracy.", False, "search"),
    ("2606.29604", "b6", 0, 1, 0, "arXiv preprint", "Unsupervised perturbative elicitation (LoRAs) of latent behavioural modes.", False, "search"),
    ("or:knirOusGcq", "C2", 0, 1, 0.5, "ICLR 2027 submission",
     "Causal pre-generation subspace for response length; parallel vs orthogonal intervention decomposition; held-out transfer.", False, "search"),
    ("or:Dl1xo5fqnj", "C2,C3a", 0, 1, 0.5, "ICLR 2027 submission", "Learns to predict how a hidden-state edit changes output preference; decoders mispredict intervention effects.", False, "search"),
    ("2606.24952", "C2", 0, 0.5, 0.5, "arXiv preprint", "Angle between detecting and controlling directions (detection-intervention gap).", True, "search"),
    ("or:tZaHwMrvq2", "C2,C3a", 0, 0.5, 0.5, "ICLR 2027 submission", "Injection compliance decodable early but causally decided in a late-layer bottleneck.", False, "search"),
    ("2604.12493", "C2", 0, 1, 0, "ICLR 2026 (comment)", "Latent planning features cause future tokens; ability grows with scale (Qwen-3).", False, "FC+search"),
    ("2602.02103", "C2", 0, 0.5, 0, "ICML 2026 (comment)", "Probing latent planning horizon in CoT (Tele-Lens).", False, "FC"),
    ("2607.05316", "C2", 0, 0.5, 0, "arXiv preprint", "Remaining output length linearly decodable from prompt's last hidden state.", False, "search"),
    ("2602.07080", "C2", 0.5, 0.5, 0, "arXiv preprint", "Code correctness inferred from attribution graphs.", False, "search"),
    ("2605.29737", "b2,C3a", 0.5, 0.5, 0, "arXiv preprint", "Single-character prompt mutations flip code security; hidden-state signals.", False, "search"),
    ("2610.25133", "C2-geometry", 0.5, 1, 0, "arXiv preprint", "One shared steering direction toward safer cryptographic API choices in code.", False, "search+FC"),
    ("venue:kotawala", "b7,C3a,FLAG-B", 0.5, 0.5, 0.5, "NeurIPS 2026 workshop poster",
     "Probe on last prompt token predicts prompt-injection compliance (AUC 0.90); only partly steerable.", False, "search(E2)"),
    ("2609.14151", "b7,C3a,FLAG-B", 0, 0.5, 0.5, "arXiv preprint", "Separation metrics predict steerability of concepts.", True, "search"),
    ("2607.10296", "C3a,FLAG-B", 0, 0.5, 0, "arXiv preprint", "Length-controlled hidden-state susceptibility diagnoses reasoning-state activation and guides steering.", True, "search"),
    ("or:uVn7IU6iPN", "C3a", 0, 0.5, 1, "ICLR 2027 submission", "Black-box prompt sensitivity as a frozen predictor of accuracy loss under shift.", False, "search"),
    ("or:L09agUoh7d", "C3b,b1", 0.5, 0.5, 0, "ICLR 2027 submission", "Compliant answers to negative instructions often echo/reintroduce the excluded object.", False, "search"),
    ("2605.03052", "C3b", 0, 1, 0, "ICML 2026 (comment)", "Negation by construction + suppression; late-layer shortcut heads promote the positive answer.", True, "planning"),
    ("2601.08070", "b1,C3b", 0, 1, 0, "arXiv preprint", "Priming failure: naming the forbidden word activates it (87.5% of violations).", True, "planning"),
    ("2604.07192", "C3a,b2", 0.5, 0, 0, "arXiv preprint", "Constraints opposing implementation priors fail 10-100%; negative harder than positive constraints.", True, "planning"),
    ("2604.13006", "b4", 0, 0.5, 0, "arXiv preprint", "Banning one punctuation character or word collapses response comprehensiveness (14-48%).", False, "search"),
    ("2610.02438", "C3c", 0.5, 0, 0.5, "arXiv preprint", "Code generation for named algorithms as parametric retrieval, not synthesis.", True, "search"),
    ("2608.30047", "C3c", 0.5, 0, 0.5, "arXiv preprint (COLM 2026 per comment)", "Agents show greater H-creativity than medal humans but lower performance (LLM-judge novelty).", True, "search(E2)"),
    ("2608.14669", "C3c", 0.5, 0, 1, "arXiv preprint", "Automated novelty verification of theorems against corpora (Lean 4).", False, "search"),
    ("2605.28664", "C3c", 0, 1, 0, "arXiv preprint", "Increasing steering strength reduces response diversity (synthetic safety data).", True, "planning"),
    ("2606.08251", "C3c", 0, 0, 0.5, "arXiv preprint", "Scientists rate LLM ideas: hivemind collapse, little divergence.", False, "search"),
    ("2607.13077", "C1", 0.5, 0, 0, "arXiv preprint", "AI-assisted human code homogenises syntax, not ML-algorithm calls.", True, "search(E2)"),
    ("2605.11128", "C1-seed", 0, 0, 0.5, "arXiv preprint", "Calibration (validity/diversity mass allocation) as the diversity bottleneck.", False, "search"),
    ("2602.20408", "C1", 0, 0, 0.5, "arXiv preprint", "Fixation and knowledge aggregation limit LLM idea diversity.", False, "search"),
    # in-window table neighbours supplied by the plan (scored for completeness)
    ("2603.23629", "C2-geometry", 0.5, 1, 0, "arXiv preprint", "Difference-in-means steering toward a target language/library in code LLMs.", True, "planning"),
    ("2605.05115", "C2-geometry", 0, 1, 0.5, "ICML 2026 MI Workshop spotlight (icml.cc)", "Manifold steering: geodesic/MDS isometry; linear steering cuts off-manifold.", True, "planning"),
    ("2603.18353", "C2", 0, 0.5, 0.5, "arXiv preprint", "98.2% AUROC probes vs 45.1% output sensitivity; steering ~ random perturbation.", True, "planning"),
    ("2607.05188", "C2", 0.5, 0.5, 0, "arXiv preprint", "Probes on coding-agent residual streams predict future edit outcomes.", True, "planning"),
    ("2604.09839", "b7,C3a", 0, 0.5, 0, "ICLR 2026 workshops (comment)", "Formal separation of white-box steering and black-box prompting (context).", True, "planning"),
    ("2608.12321", "C3a", 0, 0.5, 0, "arXiv preprint", "Implicit-constraint failure as routing, not knowledge (probes + patching).", True, "planning"),
]


def verdict(o, i, c):
    s = o + i + c
    return ("occupies the claim" if s >= 2.5 else "adjacent" if s >= 1 else "irrelevant"), s


def v1_date(hid):
    if hid in META:
        return META[hid]["v1_published"][:10]
    return None


def main():
    out = EVID / "saturation_hits.jsonl"
    out.write_text("")
    rows = []
    for hid, claims, o, i, c, venue, note, ft, src in HITS:
        v, s = verdict(o, i, c)
        d = v1_date(hid)
        is_or = hid.startswith("or:")
        rec = {"id": hid, "title": (META.get(hid) or {}).get("title"), "v1_date": d or ("ICLR 2027 submission (deadline 2026-09-25)" if is_or else
                                                                                      "NeurIPS 2026 workshop (2026)" if hid.startswith("venue:") else None),
               "in_window": True if (is_or or hid.startswith("venue:")) else bool(d and d >= "2026-01-01"),
               "claims": claims, "axes": {"O": o, "I": i, "C": c}, "score": s, "verdict": v, "venue_status": venue,
               "contemporaneous_4mo": bool(is_or or hid.startswith("venue:") or (d and d > CUTOFF_4M)),
               "iclr2027_rule": ("arXiv-only: no comparison required" if ("arXiv preprint" in venue and "ICLR 2027" not in venue)
                                 else "peer-reviewed venue: check publication date vs 2026-07-17" if not is_or else "concurrent submission"),
               "full_text_checked": ft, "source": src, "note": note}
        rows.append(rec)
        with out.open("a") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    # ----- per-family PRISMA-style counts -----
    raw = collections.Counter()
    for f in sorted((CACHE / "search_results").glob("*.json")):
        fam = "FC" if f.stem.startswith("FC_") else f.stem.split("_")[0]
        raw[fam] += len(json.loads(f.read_text()))
    cands = [json.loads(l) for l in (EVID / "saturation_candidates.jsonl").read_text().splitlines()]
    scr = {json.loads(l)["key"]: json.loads(l) for l in (EVID / "screening.jsonl").read_text().splitlines()}
    uniq, win, kp = collections.Counter(), collections.Counter(), collections.Counter()
    for c in cands:
        for fam in c["families"]:
            uniq[fam] += 1
            if scr[c["key"]]["in_window"]:
                win[fam] += 1
                if scr[c["key"]]["keyword_pass"]:
                    kp[fam] += 1
    fam_of = {}
    for c in cands:
        k = c.get("arxiv_id") or ("or:" + c["openreview_id"] if c.get("openreview_id") else None)
        if k:
            fam_of[k] = c["families"]
    inc, ftc = collections.Counter(), collections.Counter()
    for r in rows:
        if r["verdict"] == "irrelevant":
            continue
        for fam in fam_of.get(r["id"], ["planning/E2 only"]):
            inc[fam] += 1
            if r["full_text_checked"]:
                ftc[fam] += 1
    counts = {fam: {"identified_raw": raw.get(fam, 0), "unique_after_dedup": uniq.get(fam, 0),
                    "in_window_screened": win.get(fam, 0), "passed_keyword_prescreen": kp.get(fam, 0),
                    "full_text_checked_included": ftc.get(fam, 0), "included_adjacent_or_occupying": inc.get(fam, 0)}
              for fam in ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "FC", "planning/E2 only"]}
    counts["_totals"] = {"raw_hits": sum(raw.values()), "unique": len(cands),
                         "in_window": sum(1 for c in cands if scr[c["key"]]["in_window"]),
                         "keyword_pass_in_window": sum(1 for c in cands if scr[c["key"]]["in_window"] and scr[c["key"]]["keyword_pass"]),
                         "hits_given_verdicts": len(rows), "verdict_counts": dict(collections.Counter(r["verdict"] for r in rows))}
    (EVID / "saturation_counts.json").write_text(json.dumps(counts, indent=1))
    print(json.dumps(counts["_totals"], indent=1))
    for fam, v in counts.items():
        if fam != "_totals":
            print(fam, v)


if __name__ == "__main__":
    main()
