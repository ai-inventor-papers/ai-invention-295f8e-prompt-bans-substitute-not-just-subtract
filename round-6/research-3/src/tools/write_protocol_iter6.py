"""Step 1: write the frozen protocol (lanes, 21 strings, engines, window, O/I/C rubric, flags A-D, contemporaneity rule,
stop rule, time caps) to evidence/protocol_iter6.json and stamp its sha256 + UTC time BEFORE the first search call.
Usage: python3 -I tools/write_protocol_iter6.py   (refuses to overwrite an existing stamped protocol)"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

EVID = Path(__file__).resolve().parents[1] / "evidence"
P = EVID / "protocol_iter6.json"
S = EVID / "protocol_iter6.sha256"

# (id, lane, plan string, arXiv API search_query, Semantic Scholar / OpenReview term)
QUERIES = [
    ("q1", "L1", "'distributed alignment search' generation steering",
     'all:"distributed alignment search"', "distributed alignment search steering generation"),
    ("q2", "L1", "'interchange intervention' strategy OR algorithm language model",
     'all:"interchange intervention" AND (all:strategy OR all:algorithm)', "interchange intervention strategy algorithm language model"),
    ("q3", "L1", "causal variable localization code generation OR program synthesis",
     'all:"causal variable" AND (all:code OR all:program)', "causal variable localization code generation"),
    ("q4", "L2", "pre-generation planning subspace causal intervention language model",
     "all:planning AND all:subspace AND all:intervention", "pre-generation planning subspace causal intervention language model"),
    ("q5", "L2", "'response planning' OR 'latent plan' hidden state before generation code",
     'all:"response planning" OR all:"latent plan" OR all:"latent planning"', "latent planning hidden state before generation code"),
    ("q6", "L2", "predict which algorithm OR approach a language model will use from hidden states",
     'all:predict AND all:"hidden states" AND (all:algorithm OR all:strategy OR all:approach)', "predict which algorithm strategy language model will use from hidden states"),
    ("q7", "L3", "causal abstraction alignment map expressivity random model baseline",
     'all:"causal abstraction"', "causal abstraction alignment map expressivity random model"),
    ("q8", "L3", "'interpretability illusion' subspace patching",
     'all:"interpretability illusion" OR all:"interpretability illusions" OR (all:subspace AND all:patching)', "interpretability illusion subspace patching"),
    ("q9", "L3", "interventions off-distribution 'divergent representations' OR out-of-distribution activation patching",
     'all:"divergent representations" OR (all:"activation patching" AND all:"out-of-distribution")', "causal interventions divergent representations off-distribution activation patching"),
    ("q10", "L4", "'natural language autoencoder' OR 'activation verbalizer'",
     'all:"natural language autoencoder" OR all:"natural language autoencoders" OR all:"activation verbalizer" OR all:"activation verbalization"', "natural language autoencoder activation verbalizer"),
    ("q11", "L4", "LatentQA OR 'activation oracle' OR SelfIE steering OR control",
     'all:LatentQA OR all:"activation oracle" OR all:"activation oracles" OR all:SelfIE', "LatentQA activation oracle SelfIE steering control"),
    ("q12", "L4", "edit explanation reconstruct activation steering",
     "all:explanation AND all:activation AND all:steering AND (all:edit OR all:reconstruct OR all:reconstruction)", "edit natural language explanation reconstruct activation steering"),
    ("q13", "L5", "sparse autoencoder steering reasoning strategy OR algorithm OR code",
     'all:"sparse autoencoder" AND all:steering AND (all:strategy OR all:algorithm OR all:code)', "sparse autoencoder steering reasoning strategy code"),
    ("q14", "L5", "'Gemma Scope 2' OR transcoder attribution graph Gemma 3",
     'all:"Gemma Scope 2" OR (all:transcoder AND all:"attribution graph")', "Gemma Scope 2 transcoder attribution graph"),
    ("q15", "L5", "difference-in-means versus sparse autoencoder steering AxBench 2026",
     'all:AxBench OR (all:"difference-in-means" AND all:"sparse autoencoder")', "difference-in-means versus sparse autoencoder steering AxBench"),
    ("q16", "L6", "quantization 'steering vectors' OR 'activation steering'",
     'all:quantization AND (all:"steering vector" OR all:"steering vectors" OR all:"activation steering")', "quantization steering vectors activation steering"),
    ("q17", "L6", "FP8 OR W8A8 OR INT8 'activation patching' OR interpretability OR 'sparse autoencoder'",
     '(all:FP8 OR all:W8A8 OR all:INT8 OR all:quantization) AND (all:"activation patching" OR all:interpretability OR all:"sparse autoencoder")', "quantization FP8 INT8 activation patching interpretability sparse autoencoder"),
    ("q18", "L6", "numerical precision bf16 reproducibility LLM outputs",
     '(all:bf16 OR all:bfloat16 OR all:"numerical precision") AND (all:reproducibility OR all:nondeterminism OR all:"non-determinism")', "numerical precision bf16 reproducibility LLM outputs"),
    ("q19", "L7", "latent variable resampling output diversity language model",
     'all:latent AND all:diversity AND (all:resampling OR all:"latent variable")', "latent variable resampling output diversity language model"),
    ("q20", "L7", "activation noise OR hidden-state perturbation diversity code generation",
     '(all:"activation noise" OR all:"hidden state perturbation" OR all:"noise injection") AND all:diversity', "activation noise hidden-state perturbation diversity code generation"),
    ("q21", "L7", "plan sampling diverse solutions latent intent",
     '(all:"latent plan" OR all:"latent intent" OR all:"plan sampling") AND all:diversity', "plan sampling diverse solutions latent intent"),
]

PROTOCOL = {
    "artifact": "gen_art_research_3 (iteration 6) - Table 92e positioning audit",
    "frozen_before_first_call": True,
    "lanes": {
        "L1": "causal variable localization of a strategy (interchange / DAS)",
        "L2": "planning subspaces before generation",
        "L3": "the field's controls for DAS and subspace patching",
        "L4": "NLA and verbalised steering",
        "L5": "SAE and transcoder features of strategy choice",
        "L6": "quantization and interventions",
        "L7": "resampling a latent or causal variable for diversity",
    },
    "queries": [{"id": q, "lane": l, "plan_string": s, "arxiv_api": a, "s2_openreview_term": t} for q, l, s, a, t in QUERIES],
    "engines": {
        "E1": "OpenAlex/Crossref via aii-web-tools aii_fast_web_search.py --mode scholarly",
        "E3": "arXiv API export.arxiv.org/api/query (sortBy=submittedDate desc, 25 results; cs.CL/cs.LG/cs.AI not forced in query, applied at screening by window)",
        "E4": "Semantic Scholar graph/v1/paper/search (year=2026, 25 results); also forward citations",
        "E5": "OpenReview api2.openreview.net/notes/search?term=STRING&group=ICLR.cc/2027/Conference&limit=25",
        "E6": "grey literature via built-in WebSearch restricted to transformer-circuits.pub, lesswrong.com, alignmentforum.org, huggingface.co, github.com, neuronpedia.org, substack.com",
    },
    "round1_engine_assignment": {"all_queries": ["E3", "E4", "E5"], "L1,L4,L6": ["E1"], "L4,L5,L6": ["E6"]},
    "round2": "at most 6 queries built from vocabulary of included hits; motivating hit logged per query",
    "snowballing": {
        "forward_citations_E4": ["NLA paper (Transformer Circuits 2026, by title)", "MIB arXiv:2504.13151 (filter 2026 and strategy|plan|code|algorithm)",
                                 "Emergent Response Planning arXiv:2502.06258", "Steering Under Compression arXiv:2609.06473"],
        "fallback": "if 2609.06473 has 0 citations: backward references of 2609.06473 and 2606.03002",
        "swap_rule": "swap a default only for a round-1 hit that scores higher on that lane; log the swap",
    },
    "window": {"start": "2026-01-01", "end": "retrieval date (2026-10-22)", "anchors": "any date"},
    "rubric": {
        "O_object": {"1": "which algorithm or solution strategy a code model writes",
                     "0.5": "a categorical plan/strategy/attribute in another domain (reasoning strategy, rhyme, response length, language or library choice)",
                     "0": "otherwise"},
        "I_instrument": {"1": "the claim's own intervention class", "0.5": "a neighbouring intervention", "0": "none",
                         "classes": {"P1": "interchange or DAS with a declared map class",
                                     "P2": "predicting effects of random directions from subspace projection or energy",
                                     "P3": "interpolation or extrapolation along a causal variable",
                                     "P4": "state noise against token temperature at matched departure",
                                     "P5": "per-sample resampling of a fitted variable",
                                     "N": "edit an explanation, reconstruct it and patch the result",
                                     "S": "SAE or transcoder features against difference in means or prompting, with attribution",
                                     "E": "same perturbations under activation-quantised and unquantised inference"}},
        "C_criterion": {"1": "validated by generation (emitted outputs scored by tests or labels)",
                        "0.5": "logit, likelihood, probe or next-token readout", "0": "otherwise"},
        "thresholds": {"occupies": ">= 2.5", "adjacent": "1 to 2", "irrelevant": "< 1"},
    },
    "flags": {
        "A_P1": {"FIRED": "a paper localizes which algorithm or solution strategy a code LLM will use as a low-rank causal variable by interchange or DAS (a learned subspace patch) AND validates by generation (emitted programs change, scored by tests or labels)",
                 "PARTLY_FIRED": "only one half holds, or same work on a non-code strategy or on a code attribute that is not the algorithm (language or library)"},
        "B_E": {"FIRED": "a paper shows activation quantization (FP8 or INT8 W8A8, or fake-quantised activations) changes the effect size of activation perturbations, steering or patching relative to bf16/fp16 on the same directions",
                "PARTLY_FIRED": "weight-only quantization (as in 2609.06473), or quantization that changes interpretability readouts (patching recovery, SAE features) without measuring perturbation effect sizes"},
        "C_N": {"FIRED": "a paper edits NLA explanations, or the explanations of a similar verbaliser (LatentQA- or SelfIE-style decoder), and uses the result to steer the model",
                "planner_precheck": "the NLA paper itself does exactly this; expect FIRED on method; must be verified"},
        "D_P5": {"FIRED": "a paper resamples a fitted, causally localised plan or latent variable once per generation to raise output diversity",
                 "PARTLY_FIRED": "per-sample activation noise or latent-code sampling without a fitted causal variable"},
    },
    "contemporaneity_rule": "inherited from 92d: arXiv v1 after 2026-06-22 -> contemporaneous_4mo; every ICLR 2027 submission -> contemporaneous; arXiv-only papers exempt from the ICLR rule",
    "status_vocabulary": ["VERIFIED", "VERIFIED-ABSTRACT", "VERIFIED-BLOG", "VERIFIED-README", "UNVERIFIABLE (carries no number)"],
    "stop_rule": "after round 2 plus snowballing, stop if no new hit scores >= 1.5; otherwise one round 3 (forward and backward references of new hits >= 1.5) inside the time cap",
    "time_caps_min": {"step0": 15, "step1": 10, "step2_seed_verification": 50, "step3_search_scoring": 55, "step4_qa": 10, "step5_6_writeup": 35, "buffer": 5,
                      "hard_stop_search": "T+2h20m"},
    "failure_handling": ["OpenReview forum HTML blocked -> API", "arXiv HTML missing -> PDF", "long transformer-circuits page -> regex grep",
                         "Semantic Scholar 429 -> back off and log; OpenAlex cites: not relied on",
                         "over time -> drop round 3, then E6 for L7, then forward citations beyond 2 neighbours; never drop flag seeds, QA or verdict box"],
}


def main():
    if S.exists():
        raise SystemExit("protocol already stamped; record changes in evidence/protocol_amendments_iter6.jsonl")
    EVID.mkdir(exist_ok=True)
    P.write_text(json.dumps(PROTOCOL, indent=1, ensure_ascii=False))
    h = hashlib.sha256(P.read_bytes()).hexdigest()
    S.write_text(f"{h}  protocol_iter6.json\nstamped_utc: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}\n")
    print(S.read_text())


if __name__ == "__main__":
    main()
