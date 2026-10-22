"""Freeze the iteration-6 audit protocol (plan step 0.4) BEFORE the first search call.

Writes evidence/protocol_iter6.json and evidence/protocol_iter6.sha256 (sha256 + write time). Any later change must be
logged as an amendment (old/new sha256) in evidence/protocol_amendments_iter6.jsonl; this script refuses to overwrite.
Engines, settings, rubric scale, quote rules and stop-rule logic are copied from the iteration-5 protocol
(inherited/iter5/protocol.json) so that counts are comparable with Table 92d.
Usage: python -I tools/write_protocol_iter6.py
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import EVID, WS, now_utc  # noqa: E402

INH5 = json.loads((WS / "inherited" / "iter5" / "protocol.json").read_text())

CLAIMS = {
    "_source": ("One-line statements written from the artifact plan gen_plan_research_1_idx7 (title, summary, question, "
                "explanation, Step 5.2 'what this run adds' design facts). The iteration-6 hypothesis text itself was not "
                "passed to this executor, so the wording is the plan's, not the hypothesis's."),
    "L1a": "Landing identity: a content-free nudge (random activation perturbation) or a ban moves the tuned model "
           "(Qwen3-8B) off its default algorithm onto the BASE model's runner-up algorithm, forecast in advance "
           "(sha256-committed) from the base model's composition and checked by tests/algorithm labels.",
    "L1b": "Rival-aware landing: the base-runner-up forecast is scored against rivals built from the tuned model itself "
           "(its teacher-forced likelihood ranking q_lik and its own sampled tail q_tail), including tail-empty events "
           "(twin N 300).",
    "L2": "Support: the perturbed tuned model's algorithm distribution stays inside the base model's support.",
    "L3": "Shape: the perturbed/tuned distribution is fit by the base distribution raised to a power (p^alpha sharpening) "
          "better than parametric rivals or the tuned tail.",
    "E": "Engine control: the iteration-4 plan-site sensitivity of Qwen3-8B may be a property of its FP8 W8A8 serving "
         "engine; a 2x2 weight-by-activation precision factorial (W8A8, W8A16, W16A8, W16A16) with identical hook code, "
         "per-position doses and CRN slots decides it.",
    "E-attribution": "Attribution of any precision effect to activation vs weight quantisation, with per-token absmax and "
                     "FP8-scale readouts as the mechanism readout.",
    "E-deployment": "Deployment finding (if positive): activation quantisation changes how far a model can be nudged "
                    "(nudgeability) while its default output and accuracy are unchanged.",
    "S-a": "Site: content-free perturbation of prefill task-specification states, by block band, changes the categorical "
           "algorithm choice (bf16).",
    "S-b": "Site: the read position (last prompt token) compared with task-spec positions at matched per-position dose.",
    "S-c": "Site: condition/instruction tokens vs generated tokens as perturbation sites at matched dose.",
    "S-d": "Site comparison method: matched per-position dose or downstream-displacement match with paired CRN flips.",
    "F1": "Forks: the position of first divergence (an 'entrance' fork) is where algorithm choice is decided.",
    "F2": "Margins: the twin's teacher-forced log-odds margin between algorithm openings bounds (explains) the "
          "temperature effect; a large logit margin makes temperature inert.",
    "K": "Knobs: algorithm-level, test-checked prices (H5/P15/P20, full-simplex hull) of base intent, base/instruct "
         "weight interpolation (lambda 0.25/0.5), enumerate-and-pick, proxy tuning/EFT and bf16 plan noise.",
    "G": "Generality/scope: cross-reference to Table 92c row C3c (scope against FunSearch/AlphaEvolve); no new search.",
}

FAMILIES = [
    {"family": "FE1", "lane": "LE", "flag": "E", "e6": True, "queries": [
        {"q": "activation quantization steering vector effect", "e3_terms": ["quantization", "steering"]},
        {"q": "FP8 activation quantization interpretability intervention", "e3_terms": ["FP8", "(activation OR intervention)"]},
        {"q": "quantized model activation patching reproducibility precision", "e3_terms": ["quantized", "patching"]},
        {"q": "W8A8 INT8 activation steering robustness", "e3_terms": ["(W8A8 OR (INT8 AND steering))"]},
        {"q": "numerical precision bf16 fp32 mechanistic interpretability results differ", "e3_terms": ["precision", "interpretability"]}]},
    {"family": "FE2", "lane": "LE", "flag": "E-context", "e6": False, "queries": [
        {"q": "batch invariance nondeterminism LLM inference precision", "e3_terms": ["nondeterminism", "inference"]},
        {"q": "quantization changes model behaviour flips beyond accuracy", "e3_terms": ["quantization", "flips"]},
        {"q": "activation outliers FP8 per-token scale perturbation sensitivity", "e3_terms": ["outlier", "FP8"]}]},
    {"family": "FL1", "lane": "LL", "flag": "L", "e6": True, "queries": [
        {"q": "base model predicts aligned model alternatives after perturbation", "e3_terms": ["\"base model\"", "perturbation", "aligned"]},
        {"q": "post-training preserves base model ranking of candidates", "e3_terms": ["\"base model\"", "ranking", "post-training"]},
        {"q": "steered or perturbed tuned model reverts to pretraining distribution", "e3_terms": ["steering", "\"base model\"", "revert"]},
        {"q": "token-level distribution shift RL fine-tuning base top-k", "e3_terms": ["token-level", "RLVR", "\"base model\""]}]},
    {"family": "FL2", "lane": "LL", "flag": "L3", "e6": False, "queries": [
        {"q": "power sharpening base distribution alignment typicality", "e3_terms": ["sharpening", "\"base model\""]},
        {"q": "fine-tuning reweights rather than adds capabilities support", "e3_terms": ["fine-tuning", "support", "\"base model\""]}]},
    {"family": "FS1", "lane": "LS", "flag": "S/F", "e6": False, "queries": [
        {"q": "forking tokens algorithm choice code generation", "e3_terms": ["forking", "code"]},
        {"q": "pre-generation planning state causal intervention", "e3_terms": ["pre-generation", "planning"]},
        {"q": "noise injection site layer comparison LLM generation diversity", "e3_terms": ["noise", "injection", "diversity"]},
        {"q": "logit margin temperature invariance sampling", "e3_terms": ["temperature", "margin", "sampling"]}]},
    {"family": "FK1", "lane": "LK", "flag": "K", "e6": False, "queries": [
        {"q": "weight interpolation base instruct model code diversity", "e3_terms": ["interpolation", "diversity", "code"]},
        {"q": "base model guided decoding diversity code", "e3_terms": ["\"base model\"", "decoding", "code"]},
        {"q": "proxy tuning emulated fine-tuning diversity", "e3_terms": ["(proxy-tuning OR \"emulated fine-tuning\")"]}]},
]

PROTOCOL = {
    "protocol_id": "iter6-positioning-audit-92e",
    "frozen_utc": None,  # filled with the actual write time below
    "note": ("Written before the first search call of this module (plan step 0.4). Query strings, engines, window, "
             "rubric, flags and stop rule are frozen; deviations are logged in evidence/search_log_iter6.jsonl with "
             "status 'deviation' and reported in research_report.md section 4; amendments go to "
             "evidence/protocol_amendments_iter6.jsonl with old/new sha256."),
    "extends": ["art_ObxQOIlAM9MS (iteration-5 audit, Table 92d)", "art_kjrCpQnPaniY (iteration-4 audit, Tables 92b/92c)"],
    "claims": CLAIMS,
    "lanes": {"LL": "landing identity / order preservation (L1a, L1b, L2, L3; FLAG L)",
              "LE": "precision dependence of activation-level interventions (E, E-attribution, E-deployment; FLAG E)",
              "LS": "site of content-free perturbations, forks, pre-generation plan states, token margins (S-a..S-d, F1, F2; FLAG S)",
              "LK": "diversity knobs: base-aligned collaboration, base/instruct weight interpolation, proxy tuning/EFT (K; FLAG K)"},
    "window": {"counts_window": "arXiv v1 (or first public posting) 2026-01-01 .. 2026-10-21",
               "flags_any_date": "a flag may fire on a paper of ANY date: every pre-2026 hit matching a flag's three axes is scored",
               "contemporaneity_tags": INH5["window"]["contemporaneity_tags"]},
    "engines": {
        "E1": INH5["engines"]["E1"],
        "E3": INH5["engines"]["E3"],
        "E4": INH5["engines"]["E4"],
        "E5": INH5["engines"]["E5"],
        "E6": ("grey literature: Claude Code built-in WebSearch with allowed_domains lesswrong.com, alignmentforum.org, "
               "transformer-circuits.pub, thinkingmachines.ai, blog.vllm.ai, docs.vllm.ai, pytorch.org, huggingface.co "
               "(families FE1 and FL1), plus github.com for family FE1 only (issues/discussions of steering and hooking "
               "libraries; such reports can be 'adjacent' context but never fire a flag)"),
        "FC": ("forward citations: Semantic Scholar /graph/v1/paper/arXiv:{id}/citations (filtered to publication date >= "
               "2026-01-01 at screening); one logged OpenAlex cites: attempt per mandatory neighbour (returned 0 for every "
               "neighbour in iteration 5)"),
        "BC": "backward citations: Semantic Scholar /graph/v1/paper/arXiv:{id}/references for the two closest hits per flag (round 3)",
    },
    "query_families": FAMILIES,
    "e6_families": ["FE1", "FL1"],
    "citation_chasing": {
        "forward_round1_mandatory": {"SteeringUnderCompression": "2609.06473", "SparseButCritical": "2603.22446",
                                     "ForkingPaths": "2412.07961", "GiveMeFP32": "2506.09501"},
        "forward_round1_as_time_allows": {"ReasoningWithSampling": "2510.14901", "ThoughtAnchors": "2506.19143",
                                          "NonSurjectiveSteering": "2604.09839",
                                          "LostInQuantization": "title:Lost in Quantization: Activation Outliers Explain Language-Specific FP8 Sensitivity in Llama-3"},
        "backward_round3": "references of the two closest hits per flag (chosen after screening)"},
    "dedup": ("against inherited/iter4/saturation_candidates.jsonl (1,729) and inherited/iter5/saturation_candidates_iter5.jsonl "
              "(3,506) and the inherited source lists, by arXiv id, OpenReview id, DOI, then normalised title; in-window "
              "records already seen that match an iteration-6 lane are RE-SCREENED against the iteration-6 claims"),
    "prescreen_keyword_groups": {
        "LE": {"PRECISION": r"quantiz|fp8|int8|w8a8|w4a8|bf16|fp16|fp32|precision|numeric|nondetermin|e4m3",
               "INTERVENTION": r"steer|patch|ablat|activation addition|noise|perturb|edit|intervention|\bsae\b",
               "OUTCOME": r"behavio|output|success|effect|flip|generation|accuracy"},
        "LL": {"MODEL": r"base|pretrained|pre-trained|aligned|instruct|chat|rlhf|rlvr|post-train|fine-tun",
               "RANK": r"rank|top-k|top-1|candidate|support|sharpen|rerank|tail|prior",
               "PERTURB": r"perturb|steer|ban|prohibit|jailbreak|nudg|intervention|fine-tun"},
        "LS": {"SITE": r"layer|position|token|prefill|prompt|site|fork|anchor|plan",
               "INTERVENTION": r"steer|patch|ablat|activation addition|noise|perturb|edit|intervention|\bsae\b",
               "OUTCOME": r"strategy|solution|algorithm|answer|divers"},
        "LK": {"KNOB": r"interpolat|merg|collaborat|proxy|emulat|guided decod|nudg|restor",
               "MODEL": r"base|pretrained|pre-trained|aligned|instruct|chat|rlhf|rlvr|post-train|fine-tun",
               "OUTCOME": r"divers|pass@k|coverage|creativ"}},
    "screening": ("rank in-window records by groups matched within their best lane; every record gets a one-line verdict "
                  "in evidence/screening_iter6.jsonl (machine reason 'prescreen-fail' for records matching fewer than 2 "
                  "groups in every lane); manual title/abstract verdict for the top 100 per lane (or all if fewer); full "
                  "text for every hit scoring >= 1.5 on its best claim"),
    "rubric": {
        "scale": INH5["rubric"]["scale"],
        "relation_tags": ["supports", "contradicts-in-part", "context", "method-overlap", "replication-of", "inherited"],
        "L1": {"O": "identity of where a perturbed/steered/prompt-banned/fine-tune-perturbed tuned model lands, checked by exact token, answer key, execution or mechanism label (0.5 if judged by an LLM or embedding)",
               "I": "the base model's ranking or composition of alternatives used as the forecast",
               "C": "a rival built from the tuned model itself (sampled tail, likelihood ranking, pre-perturbation distribution) OR a forecast committed before the outcome (1 if both, 0.5 if one)"},
        "L2_L3": {"O": "support or shape of the perturbed/tuned distribution", "I": "base support or base distribution raised to a power",
                  "C": "compared with other parametric rivals or with the tuned tail"},
        "E": {"O": "behavioural effect of an activation-level intervention (rate, size, direction)",
              "I": "activation precision varied at matched weights (1); weight-only precision (0.5); numerics/batch only (0, scored 0.5 on C)",
              "C": "same intervention, same inputs, across precisions (1); different vectors per precision (0.5)"},
        "E_deployment": {"O": "whether nudgeability/steerability differs while the default/accuracy is unchanged",
                         "I": "deployment engine (quantised kernel)", "C": "matched comparison"},
        "S": {"O": "categorical solution or strategy choice (1), continuous attribute (0.5)",
              "I": "content-free (random/isotropic) perturbation at declared sites and layer bands",
              "C": "matched per-position dose or downstream-displacement match across sites"},
        "F": {"O": "position of first divergence or a fork's outcome shift", "I": "token-level margin, entropy or resampling",
              "C": "temperature sweep explained by the margin"},
        "K": {"O": "algorithm- or strategy-level, test-checked diversity",
              "I": "base-aligned collaboration, base/instruct weight interpolation, proxy tuning/EFT",
              "C": "priced against other knobs at matched correctness"}},
    "flags": {
        "FLAG_E": ("FIRES if a paper reports that ACTIVATION quantisation (FP8 or INT8 activations, any scale granularity; "
                   "W8A8, W4A8, FP8 activations with per-token or per-tensor scales; FP8 KV-cache counts as activation-side) "
                   "changes the behavioural effect, success rate or direction of an activation-level intervention "
                   "(steering/activation addition, noise injection, patching, ablation, SAE-latent editing) relative to "
                   "higher-precision activations on the same or matched weights. PARTLY FIRED if the varied factor is "
                   "weight-only (INT8/NF4/INT4/GPTQ/AWQ), or the outcome is internal only (vector cosine, probe accuracy), or "
                   "numerics change intervention outcomes only via batch/kernel nondeterminism. ADJACENT if numerics or "
                   "quantisation change outputs with no intervention (nondeterminism, FP8 outlier sensitivity, flips)."),
        "FLAG_L": ("FIRES if a paper (i) perturbs, steers, prompts against or fine-tunes a tuned model away from its default "
                   "output, (ii) forecasts from the base model where it lands (identity or distribution, any granularity), "
                   "and (iii) scores that forecast against a rival built from the tuned model itself (its own sampled tail, "
                   "its own likelihood ranking of alternatives, or its pre-perturbation distribution). PARTLY FIRED if "
                   "(i)+(ii) without (iii); or (ii)+(iii) retrospective rather than forecast; or token-level only with "
                   "(i)-(iii). ADJACENT: candidate preservation under post-training without a perturbation (URIAL, Same "
                   "Candidates, Sparse but Critical, crystallization), stylised accounts (power sharpening)."),
        "FLAG_S_secondary": ("fires if a paper compares sites (prompt/prefill positions by layer band vs last token vs "
                             "condition tokens vs generated tokens) for content-free perturbations at matched dose and "
                             "reports which site changes a categorical solution choice"),
        "FLAG_K_secondary": ("fires if a paper reports test-checked, algorithm- or strategy-level code diversity under "
                             "base/aligned weight interpolation, base-aligned collaboration or proxy tuning"),
        "consequences": {
            "FLAG_E_FIRES": "Claim E's deployment finding is written as a replication; only what the neighbour lacks may be claimed",
            "FLAG_E_NOT_FIRED": "dated 'to our knowledge' wording; weight-only evidence named as the closest neighbour",
            "FLAG_L_FIRES": "L1 framed as a replication at the algorithm level; only prospective commitment, tail-empty events and test-checked labels claimed",
            "FLAG_L_NOT_FIRED": "the 92d A2 sentence is updated with the new neighbours and the tail/likelihood rivals",
            "first": "the word 'first' is never licensed by a search"}},
    "stop_rule": ("After all families and one forward-citation round, build up to 6 round-2 queries from the vocabulary of "
                  "included hits; then round 3 = forward citations of the closest new hits plus backward references (BC) "
                  "of the two closest hits per flag. Stop when a round adds no new hit scoring >= 1.5 on any claim, or at "
                  "the Stage-2 cap (60 min wall time). Report which condition stopped the search."),
    "quote_rules": INH5["quote_rules"],
    "inherited_not_reverified": ("the 112 quotes of art_kjrCpQnPaniY (Tables 92b/92c) and the 137 quotes of "
                                 "art_ObxQOIlAM9MS (Table 92d) are cited by row id, not re-verified; a new quote from an "
                                 "inherited reference is allowed only when it states a finding the inherited row does not"),
    "second_pass": ("live fetch_grep re-match of every new quote; blind same-agent re-screen of every hit scoring 1.0-2.0 "
                    "plus every flag candidate, Cohen's kappa on the three verdict classes"),
}


def main():
    out = EVID / "protocol_iter6.json"
    if out.exists():
        raise SystemExit("protocol_iter6.json already frozen; log an amendment instead")
    PROTOCOL["frozen_utc"] = now_utc()
    data = json.dumps(PROTOCOL, indent=1, ensure_ascii=False)
    out.write_text(data, encoding="utf-8")
    h = hashlib.sha256(data.encode("utf-8")).hexdigest()
    (EVID / "protocol_iter6.sha256").write_text(f"{h}  protocol_iter6.json\nwritten_utc {PROTOCOL['frozen_utc']}\n")
    n_q = sum(len(f["queries"]) for f in FAMILIES)
    print(f"frozen {out.name} at {PROTOCOL['frozen_utc']} sha256={h} families={len(FAMILIES)} strings={n_q}")


if __name__ == "__main__":
    main()
