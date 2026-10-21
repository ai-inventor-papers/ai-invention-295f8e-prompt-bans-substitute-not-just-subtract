"""Build evidence/quotes_iter5.jsonl: every Table 92d neighbour quote, checked against the cached primary text.

A quote is VERIFIED only if every [...]-separated segment occurs, in order, in the normalised full text of the cited
version (rule inherited from art_kjrCpQnPaniY: whitespace collapsed, PDF hyphenation undone, ligatures/quotes/dashes
mapped, markdown emphasis stripped). Where arXiv HTML renders a MathML number twice ("0.300.30"), the quote is split
with [...] at that point so that the rendered number is matched exactly once.
VERIFIED-ABSTRACT = only an abstract record exists (OpenReview ICLR 2027 submissions: PDFs return HTTP 403).
VERIFIED-BLOG = grey literature (LessWrong / Alignment Forum / transformer-circuits.pub).
Usage: python -I tools/build_quotes_iter5.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, EVID, load_text, normalise, quote_matches  # noqa: E402

RETRIEVED = "2026-10-21"
META = json.loads((EVID / "arxiv_meta.json").read_text())

# key -> (venue status, venue evidence)
VENUE = {
    "2503.00691": ("Findings of EMNLP 2025", "https://aclanthology.org/2025.findings-emnlp.10/ ('Anthology ID: 2025.findings-emnlp.10'; re-fetched 2026-10-21)"),
    "2407.02209": ("ICLR 2025 (poster)", "inherited: iclr.cc/virtual/2025/poster/27717"),
    "2610.19157": ("arXiv preprint", "comment '24 pages, 18 figures'"),
    "2506.17871": ("TMLR 2026 (v4 comment)", "arXiv v4 comment: 'V4: TMLR 2026 Accepted'"),
    "2510.01171": ("arXiv preprint", "no venue in comment/journal_ref (v4)"),
    "2505.00047": ("arXiv preprint", "no venue in comment/journal_ref (v2)"),
    "2310.06452": ("ICLR 2024 per plan; not confirmed on a venue page", "arXiv comment gives code link only"),
    "2411.04427": ("NAACL 2025", "arXiv journal_ref: 'Proceedings of the 2025 Conference of the Nations of the Americas Chapter...'"),
    "2406.05587": ("arXiv preprint", "no venue in comment"),
    "2504.13837": ("NeurIPS 2025 (oral)", "arXiv journal_ref: 'NeurIPS 2025 Oral; ICML 2025 AI4MATH workshop best paper'"),
    "2510.02230": ("NeurIPS 2026 (poster)", "https://neurips.cc/virtual/2026/poster/150680 (title listed on the NeurIPS 2026 virtual-site poster page; fetched 2026-10-21)"),
    "2507.14843": ("arXiv preprint", "no venue in comment (v5, 2026-10-14)"),
    "2607.20543": ("arXiv preprint", "no comment line"),
    "2605.09995": ("ICML 2026", "arXiv comment: 'Accepted at ICML 2026'"),
    "2412.01951": ("arXiv preprint (ICLR 2025 per plan; not confirmed here)", "no venue in comment"),
    "2510.14901": ("arXiv preprint", "no venue in comment"),
    "2606.01811": ("ICML 2026 workshop (non-archival); not main track", "arXiv comment: 'Accepted to the Workshop on Generative AI, Creativity, and Human-AI Co-Creation @ ICML 2026 (non-archival)'"),
    "2608.11426": ("arXiv preprint", "no comment line"),
    "2606.29933": ("arXiv preprint", "no comment line"),
    "2607.12796": ("arXiv preprint", "v4 comment: 'Updated title, no other changes'"),
    "2603.24124": ("arXiv preprint", "comment lists experiments only"),
    "2610.04978": ("arXiv preprint", "comment '10 pages, 2 figures'"),
    "2605.16874": ("ICML 2026", "arXiv comment: 'Accepted at ICML 2026'"),
    "2605.28022": ("arXiv preprint (under review)", "arXiv comment: 'Preprint under review'"),
    "2603.02787": ("ICLR 2026", "arXiv comment: 'Accepted to ICLR 2026'"),
    "2511.05650": ("ICML 2026", "arXiv v2 comment: 'ICML 2026. (47 pages, 22 figures)'"),
    "2507.20956": ("arXiv preprint", "comment '9 pages, 3 figures'"),
    "2410.09300": ("ACL 2025 (main)", "https://aclanthology.org/2025.acl-long.623/ ('Anthology ID: 2025.acl-long.623'); arXiv v4 comment 'Accepted to ACL 2025 (main)'"),
    "2312.01552": ("arXiv preprint (ICLR 2024 per plan; not confirmed here)", "comment gives project website only"),
    "2310.12962": ("arXiv preprint (ICLR 2024 per plan; not confirmed here)", "no comment line"),
    "2401.08565": ("COLM 2024", "arXiv comment: 'COLM 2024 camera-ready'"),
    "2311.14479": ("arXiv preprint (ICLR 2024 per plan; not confirmed here)", "no comment line (v3, 2026-10-12)"),
    "2608.07460": ("arXiv preprint", "comment gives code link"),
    "2605.30021": ("arXiv preprint (under review)", "comment: 'Under Review'"),
    "2510.09913": ("arXiv preprint", "no comment line"),
    "2604.02319": ("COLM 2026", "arXiv v3 comment: 'Accepted to COLM 2026'"),
    "2610.24663": ("arXiv preprint", "comment gives code link"),
    "2507.12638": ("ICML 2025 Workshop on Actionable Interpretability", "arXiv comment: '6 pages, 6 figures. ICML 2025 Workshop on Actionable Interpretability'"),
    "2510.07364": ("ICML 2026 (spotlight)", "arXiv v4 comment: 'Accepted as a Spotlight at the International Conference on Machine Learning 2026'"),
    "2503.04429": ("ICML 2025", "arXiv comment: '75 pages. Accepted to ICML 2025'"),
    "2401.06102": ("ICML 2024", "arXiv comment: 'ICML 2024 (to appear)'"),
    "2510.13900": ("ICLR 2026", "arXiv comment: 'ICLR 2026'"),
    "2504.08775": ("arXiv preprint", "no comment line"),
    "2510.03215": ("ICLR 2026", "arXiv comment: 'Published in ICLR'26'"),
    "2309.16042": ("ICLR 2024", "arXiv comment: '27 pages. ICLR 2024'"),
    "2404.15255": ("arXiv preprint (tutorial)", "comment: 'A tutorial on activation patching'"),
    "2410.12877": ("ICLR 2025", "arXiv comment: 'ICLR 2025'"),
    "2511.19131": ("AAAI 2026", "arXiv comment: 'AAAI2026'"),
    "2605.07284": ("arXiv preprint", "comment gives code link (v2, 2026-08-10)"),
    "2509.06608": ("arXiv preprint", "comment: 'Preprint'"),
    "2604.13694": ("arXiv preprint (submitted to IEEE)", "comment: 'Submitted to IEEE for possible publication'"),
    "2505.17697": ("arXiv preprint", "no comment line"),
    "2602.04735": ("arXiv preprint (work in progress)", "comment: 'Work in progress'"),
    "2608.30319": ("EMNLP 2026", "arXiv comment: 'Accepted by EMNLP 2026'"),
    "2602.16189": ("arXiv preprint (submitted to Pattern Recognition Letters)", "comment"),
    "2605.24583": ("arXiv preprint", "v3 comment: 'substantially revised and reframed as a measurement-methodology paper'"),
    "2605.30526": ("arXiv preprint", "no comment line; v2 retitled (2026-10-20)"),
    "2504.10478": ("COLM 2025", "arXiv journal_ref: 'COLM 2025'"),
    "2404.16792": ("ACL 2025", "arXiv comment: 'ACL 2025'"),
    "2310.04799": ("ACL 2024", "arXiv comment: 'ACL 2024 camera-ready version'"),
    "2212.04089": ("ICLR 2023", "arXiv comment: 'In Proceedings of the 11th International Conference on Learning Representations (ICLR 2023)'"),
    "2406.05946": ("ICLR 2025 (Outstanding Paper)", "inherited: blog.iclr.cc outstanding paper awards"),
    "2509.04259": ("arXiv preprint", "no comment line"),
    "2602.06665": ("arXiv preprint", "comment '16 pages, 7 figures, 12 tables'"),
    "2610.22999": ("arXiv preprint", "comment '13 pages, 5 figures'"),
    "2504.02922": ("NeurIPS 2025", "arXiv comment: 'Accepted at 39th Conference on Neural Information Processing Systems (NeurIPS 2025)'"),
    "2507.21509": ("arXiv preprint", "no comment line"),
    "2603.06957": ("ICML 2026", "arXiv v2 comment: 'Published at the International Conference on Machine Learning (ICML) 2026'"),
    "2609.33936": ("arXiv preprint", "comment '43 pages'"),
    "2609.16454": ("arXiv preprint", "no comment line"),
    "2605.30844": ("arXiv preprint", "no comment line"),
    "2605.27878": ("EMNLP 2026 (main)", "arXiv v2 comment: 'Accepted by EMNLP 2026, Main Conference'"),
    "2504.07912": ("COLM 2025", "arXiv comment: 'COLM 2025'"),
    "2402.14811": ("ICLR 2024", "arXiv comment: 'ICLR 2024. 26 pages, 13 figures'"),
    "2504.02904": ("COLM 2025", "arXiv comment: 'COLM 2025'"),
}
OR_VENUE = ("ICLR 2027 submission (under review); contemporaneous by rule", "OpenReview API v2 venue field 'ICLR 2027 Conference Submission'")


def A(aid, ver):
    return f"https://arxiv.org/html/{aid}{ver}"


# (ref_key, cache key, id, version_quoted, url, section, quote, regex, lane, rows, relation, status)
Q = []


def q(ref, key, ident, ver, url, sec, quote, rx, lane, rows, rel, status="VERIFIED"):
    Q.append(dict(ref_key=ref, cache_key=key, id=ident, version_quoted=ver, url=url, section=sec, quote=quote,
                  regex=rx, lane=lane, rows=rows, relation=rel, status=status))


# ---------------- LANE 1: base vs aligned diversity; RLVR boundary ----------------
q("Lee2025-AlgoDiv", "2503.00691v2", "2503.00691", "v2", A("2503.00691", "v2"), "Sec. 4.2, Findings 5",
  "When comparing the Deepseek-base and Deepseek-instruct models, algorithmic diversity shows different patterns: instruction tuning decreases algorithmic diversity in AtCoder-introductory problems, but increases it in other problems.",
  "decreases algorithmic diversity", "L1", "92d-A0;FLAG_C", "contradicts-in-part")
q("Lee2025-AlgoDiv", "2503.00691v2", "2503.00691", "v2", A("2503.00691", "v2"), "Sec. 4.2, Findings 5",
  "This suggests that instruction tuning favors single, straightforward answers for simple problems while promoting the exploration of multiple approaches for complex problems.",
  "instruction tuning favors single", "L1", "92d-A0;92d-A1;FLAG_C", "contradicts-in-part")
q("Lee2025-AlgoDiv", "2503.00691v2", "2503.00691", "v2", A("2503.00691", "v2"), "Sec. 4.1, settings",
  "The generated solutions are executed with test cases to verify their functional correctness.",
  "executed with test cases", "L1", "92d-A0;FLAG_C", "context")
q("Lee2025-AlgoDiv", "2503.00691v2", "2503.00691", "v2", A("2503.00691", "v2"), "Sec. 4.1, settings for diversity metrics",
  "we employ the Llama-3.1-8B-Instruct model (Llama, 2024) to assess algorithmic relevance between two implementations.",
  "Llama-3.1-8B-Instruct", "L1", "92d-A0;FLAG_C", "context")
q("Wu2025-Monoculture", "2407.02209v1", "2407.02209", "v1", A("2407.02209", "v1"), "App. C.4, Fig. 8 caption text",
  "The figures show that the pre-trained model enjoys much better diversity than the aligned model, and is much closer to the source.",
  "enjoys much better diversity", "L1", "92d-A0", "supports")
q("Wu2025-Monoculture", "2407.02209v1", "2407.02209", "v1", A("2407.02209", "v1"), "App. E.4 (open-source code models)",
  "However, neither of the models were able to produce code solutions in our trials.",
  "neither of the models were able to produce code", "L1", "92d-A0;FLAG_C", "context")
q("Jangra2026-DivAlgo", "2610.19157v1", "2610.19157", "v1", A("2610.19157", "v1"), "Sec. 1 (contributions, RQ1)",
  "For RQ1, we show that uncontrolled sampling (for 24 LLMs) yields considerably less diverse solutions than human solutions",
  "uncontrolled sampling", "L1", "92d-A0;FLAG_C", "context")
q("Yang2025-BF-v1", "2506.17871v1", "2506.17871", "v1", A("2506.17871", "v1"), "Abstract (v1, title 'How Alignment Shrinks the Generative Horizon')",
  "alignment tuning substantially sharpens the model’s output distribution from the outset, reducing BF by nearly an order of magnitude (e.g., from 12 to 1.2) relative to base models.",
  "nearly an order of magnitude", "L1", "92d-A0;corrections", "context")
q("Yang2026-BF-v4", "2506.17871v4", "2506.17871", "v4", A("2506.17871", "v4"), "Abstract (v4)",
  "alignment tuning substantially sharpens the model’s output distribution from the outset, reducing BF by a factor of 2–5 overall, and up to an order of magnitude (e.g., from 12 to 1.2) at the beginning positions.",
  "factor of 2", "L1", "92d-A0;92d-B1;corrections", "supports")
q("Yang2026-BF-v4", "2506.17871v4", "2506.17871", "v4", A("2506.17871", "v4"), "Abstract (v4)",
  "We hypothesize that alignment tuning does not fundamentally change a model’s behavior, but instead steers it toward stylistic tokens (e.g., “Sure”) that unlock low-entropy trajectories already present in the base model.",
  "already present in the base model", "L1", "92d-A2", "supports")
q("Zhang2025-VS", "2510.01171v4", "2510.01171", "v4", A("2510.01171", "v4"), "Abstract",
  "we identify a fundamental, pervasive data-level driver: typicality bias in preference data, whereby annotators systematically favor familiar text",
  "typicality bias", "L1", "92d-A2;FLAG_B", "context")
q("Zhang2025-VS", "2510.01171v4", "2510.01171", "v4", A("2510.01171", "v4"), "App. D.3 (Power-Transform Sharpening under Typicality Bias)",
  "sharpens the reference distribution, amplifying its modes while suppressing the tails. The effect strengthens as typicality bias",
  "amplifying its modes while suppressing the tails", "L1", "92d-A2;FLAG_B", "partly-fires")
q("WestPotts2025", "2505.00047v2", "2505.00047", "v2", A("2505.00047", "v2"), "Abstract",
  "Across models tested, better performance on common benchmarks tends to correlate with worse performance on our tasks, suggesting an effective trade-off in the required capabilities.",
  "effective trade-off", "L1", "92d-A0", "supports")
q("Kirk2024-RLHF", "2310.06452v3", "2310.06452", "v3", A("2310.06452", "v3"), "Abstract",
  "However, RLHF significantly reduces output diversity compared to SFT across a variety of measures, implying a tradeoff in current LLM fine-tuning methods between generalisation and diversity.",
  "significantly reduces output diversity", "L1", "92d-A0", "supports")
q("Murthy2025-Concept", "2411.04427v3", "2411.04427", "v3", A("2411.04427", "v3"), "Abstract",
  "While no model reaches human-like diversity, aligned models generally display less diversity than their instruction fine-tuned counterparts.",
  "aligned models generally display less", "L1", "92d-A0", "supports")
q("Mohammadi2024-Attractor", "2406.05587v1", "2406.05587", "v1", A("2406.05587", "v1"), "Sec. 1 (Introduction)",
  "We demonstrate this by intentionally perturbing the model’s generation trajectory, effectively nudging it away from its usual output distribution. Surprisingly, the aligned model gracefully finds its way back to its own attractor state and in-distribution response.",
  "gracefully finds its way back", "L1", "92d-A1;92d-A2", "adjacent")
q("Yue2025-RLVR", "2504.13837v5", "2504.13837", "v5", A("2504.13837", "v5"), "Abstract",
  "systematically probing the reasoning capability boundaries of RLVR-trained LLMs across various model families, RL algorithms, and math/coding/visual reasoning benchmarks, using pass@k at large k values as the evaluation metric.",
  "pass@k at large k values", "L1", "92d-A0", "context")
q("Yue2025-RLVR", "2504.13837v5", "2504.13837", "v5", A("2504.13837", "v5"), "Abstract",
  "we surprisingly find that current training rarely elicit fundamentally new reasoning patterns.",
  "rarely elicit fundamentally new", "L1", "92d-A0", "supports")
q("Nguyen2025-RBP", "2510.02230v1", "2510.02230", "v1", A("2510.02230", "v1"), "Abstract",
  "RLVR disproportionately reinforces problems with high likelihood, correct solutions under the base model while suppressing other initially low-likelihood ones.",
  "winner-take-all", "L1", "92d-A1;FLAG_B", "adjacent")
q("Wu2026-InvisibleLeash", "2507.14843v5", "2507.14843", "v5", A("2507.14843", "v5"), "Abstract",
  "it remains unclear whether the current practice of RLVR truly expands models’ reasoning boundary or mainly amplifies high-reward outputs that base models already know.",
  "amplifies high-reward outputs", "L1", "92d-A0", "context")
q("Wu2026-InvisibleLeash", "2507.14843v5", "2507.14843", "v5", A("2507.14843", "v5"), "Sec. 3.2 (Empirical support shrinkage outweighs expansion)",
  "Losses exceed gains in every model-level aggregate in Tab. 1, giving negative net support change",
  "Losses exceed gains", "L1", "92d-A0", "supports")
q("Zhou2026-PassK", "2607.20543v1", "2607.20543", "v1", A("2607.20543", "v1"), "Abstract",
  "The failure concentrates on boundary prompts, where the base model contains rare correct trajectories that are recoverable by sampling but too sparse to reliably appear in finite RLVR rollout groups.",
  "boundary prompts", "L1", "92d-A1;FLAG_B", "partly-fires")
q("Zhou2026-PassK", "2607.20543v1", "2607.20543", "v1", A("2607.20543", "v1"), "Abstract",
  "Per-Problem Base Anchoring (PBA) is a deliberately simple proof-of-concept: sharpen prompts with sufficient frozen-base correct evidence, and anchor risky prompts to the base distribution.",
  "Per-Problem Base Anchoring", "L1", "92d-A1;FLAG_B", "partly-fires")
q("Zhou2026-PassK", "2607.20543v1", "2607.20543", "v1", A("2607.20543", "v1"), "Sec. 1, contributions",
  "decompose prompts by frozen base-model behavior into solved-easy, reachable, boundary, and out-of-reach regimes, turning an aggregate pass@k curve into an attribution problem.",
  "frozen base-model behavior", "L1", "92d-A1;FLAG_B", "partly-fires")
q("Springer2026-Annotations", "2605.09995v1", "2605.09995", "v1", A("2605.09995", "v1"), "Sec. 3 (results)",
  "Larger base models are not less diverse, but larger post-trained models are.",
  "Larger base models are not less diverse", "L1", "92d-A0", "supports")
q("Springer2026-Annotations", "2605.09995v1", "2605.09995", "v1", A("2605.09995", "v1"), "Sec. 4",
  "We consistently find that models with lower post-training loss (higher likelihood) generate less diverse outputs",
  "lower post-training loss", "L1", "92d-A0", "supports")
q("Huang2024-Sharpening", "2412.01951v2", "2412.01951", "v2", A("2412.01951", "v2"), "Sec. 1.1 (The Sharpening Mechanism)",
  "We refer to the sharpening mechanism as the phenomenon where responses from a model with the highest certainty (in the sense of large self-reward",
  "We refer to the sharpening mechanism", "L1", "92d-B2", "context")
q("KaranDu2025-PowerSampling", "2510.14901v1", "2510.14901", "v1", A("2510.14901", "v1"), "Abstract",
  "Moreover, our sampler avoids the collapse in diversity over multiple samples that is characteristic of RL-posttraining.",
  "avoids the collapse in diversity", "L4", "92d-B2;92d-C", "baseline-to-add")
q("Khoriaty2026-Decan", "2606.01811v1", "2606.01811", "v1", A("2606.01811", "v1"), "Abstract",
  "a per-byte score read off the per-token log-probabilities of a base model",
  "per-token log-probabilities of a base model", "L1", "92d-A1", "adjacent")
q("Khoriaty2026-Decan", "2606.01811v1", "2606.01811", "v1", A("2606.01811", "v1"), "Abstract",
  "On the OLMo-2-7B post-training pipeline,",
  "OLMo-2-7B post-training pipeline", "L1", "92d-A0", "supports")
q("Fortier2026-Convergence", "2608.11426v2", "2608.11426", "v2", A("2608.11426", "v2"), "Abstract",
  "We argue that output homogeneity is likely learned during the pretraining phase, and only revealed or magnified during the alignment process.",
  "only revealed or magnified", "L1", "92d-A0;92d-A2", "supports")
q("Fortier2026-Convergence", "2608.11426v2", "2608.11426", "v2", A("2608.11426", "v2"), "Abstract",
  "We find that convergence can be revealed and amplified, but not introduced by the SFT data, supporting its role as a catalyst rather than a cause.",
  "but not introduced by the SFT data", "L1", "92d-A2", "supports")
q("Fortier2026-Convergence", "2608.11426v2", "2608.11426", "v2", A("2608.11426", "v2"), "Abstract",
  "We find that instruct-like collapse can be induced through prompting alone, even without alignment.",
  "instruct-like collapse can be induced", "L1", "92d-A2", "supports")
q("Samanta2026-Crystallization", "2606.29933v1", "2606.29933", "v1", A("2606.29933", "v1"), "Abstract",
  "the nucleation phase caused by supervised finetuning, in which behavior collapses onto a single seed distribution present in the pretrained LLM; and (3) a settling phase in which reinforcement learning techniques redistribute probability of the collapsed distribution, but largely keep it concentrated on the same options as the seed distribution.",
  "single seed distribution present in the pretrained", "L1", "92d-A2;FLAG_B", "partly-fires")
q("Parikh2026-Census", "2607.12796v4", "2607.12796", "v4", A("2607.12796", "v4"), "Abstract",
  "Lightly post-trained and persona-tuned models are the most divergent; heavily post-trained assistants from the major labs are the most conformist.",
  "Lightly post-trained", "L1", "92d-A0", "supports")
q("Liu2026-AlignmentTax", "2603.24124v2", "2603.24124", "v2", A("2603.24124", "v2"), "Abstract",
  "A base-vs-instruct ablation on Qwen3-14B confirms the causal role of alignment: the base model shows 1.0% single-cluster rate vs. 28.5% for the instruct model",
  "1.0% single-cluster rate", "L1", "92d-A0", "supports")
q("Liu2026-AlignmentTax", "2603.24124v2", "2603.24124", "v2", A("2603.24124", "v2"), "Abstract",
  "localizes the cause to DPO, not SFT.",
  "localizes the cause to DPO", "L1", "92d-A0", "context")
q("Duan2026-WhatWillPTFix", "2610.04978v1", "2610.04978", "v1", A("2610.04978", "v1"), "Abstract",
  "A priori signals capture a minority of it: base pass rate, the likelihood of a correct solution, a larger model’s pass rate and their combinations explain only 0.30 [...] and 0.24 [...] of the explainable variance in gains.",
  "A priori signals capture a minority", "L1", "92d-A1;FLAG_B", "contradicts-in-part")
q("Duan2026-WhatWillPTFix", "2610.04978v1", "2610.04978", "v1", A("2610.04978", "v1"), "Sec. 1, contributions",
  "The missing part lives in the base model’s behaviour on a problem, not in what the problem looks like.",
  "The missing part lives in the base model", "L1", "92d-A1;FLAG_B", "supports")
q("Shen2026-DecisionTokens", "2605.16874v1", "2605.16874", "v1", A("2605.16874", "v1"), "Abstract",
  "we find that the reasoning advantage is highly sparse and concentrates on a small set of early, planning-related decision tokens.",
  "planning-related decision tokens", "L2", "92d-B1;92d-C", "adjacent")
q("LeBronnec2026-RedundancyRLVR", "2605.28022v1", "2605.28022", "v1", A("2605.28022", "v1"), "Sec. 4 (Correctness-only RLVR concentrates repeated implementations)",
  "Relative to the corresponding base model, Base-RLVR decreases JPlag diversity in 57.2% [...] of comparisons and decreases Vendi score in 65.3% [...] of comparisons.",
  "decreases JPlag diversity", "L1", "92d-A0;FLAG_C", "adjacent")
q("LeBronnec2026-RedundancyRLVR", "2605.28022v1", "2605.28022", "v1", A("2605.28022", "v1"), "Sec. 2 (related work)",
  "We focus on a more specific notion: whether repeated-sampling RLVR produces near-duplicate implementations, and how this redundancy relates to finite-budget performance.",
  "near-duplicate implementations", "L1", "92d-A0;FLAG_C", "context")
q("ZhangLu2026-BehaveSim", "2603.02787v1", "2603.02787", "v1", A("2603.02787", "v1"), "Abstract",
  "We propose BehaveSim, a novel method to measure algorithmic similarity through the lens of problem-solving behavior as a sequence of intermediate solutions produced during execution",
  "BehaveSim", "L1", "92d-A0", "method-overlap")
q("Schaeffer2026-Hivemind", "2609.33936v1", "2609.33936", "v1", A("2609.33936", "v1"), "Abstract",
  "Our responses and the original authors’ own show one dominant vehicle plus a heavy tail of distinct minority vehicles.",
  "heavy tail of distinct minority vehicles", "L1", "92d-A0", "contradicts-in-part")
q("Skobelev2026-FTFixes", "2609.16454v1", "2609.16454", "v1", A("2609.16454", "v1"), "Abstract",
  "In this work, we show that whether mode-collapse—or its opposite—occurs depends on the specific model and dataset used.",
  "or its opposite", "L1", "92d-A0", "contradicts-in-part")
q("Cheng2026-CanopyEntropy", "2605.30844v1", "2605.30844", "v1", A("2605.30844", "v1"), "Abstract",
  "Fine-tuning is often believed to reduce uncertainty and diversity in large language models, but existing analyses overlook output length, a key confounder",
  "overlook output length", "L1", "92d-A0", "contradicts-in-part")
q("Li2026-NarrativeFlattening", "2605.27878v2", "2605.27878", "v2", A("2605.27878", "v2"), "Abstract",
  "Across all three, post-training compresses dynamic variation",
  "post-training compresses dynamic variation", "L1", "92d-A0", "supports")

# ---------------- LANE 2: inference-time base-aligned collaboration ----------------
q("Wang2026-BACo", "2511.05650v2", "2511.05650", "v2", A("2511.05650", "v2"), "Abstract",
  "We propose Base-Aligned Model Collaboration (BACo), an inference-time token-level model collaboration framework that dynamically combines a base LLM with its aligned counterpart to optimize diversity and quality.",
  "Base-Aligned Model Collaboration", "L2", "92d-B1;92d-C", "occupies")
q("Wang2026-BACo", "2511.05650v2", "2511.05650", "v2", A("2511.05650", "v2"), "Abstract",
  "Using uncertainty and content-based signals, BACo employs routing strategies to determine, at each token, which model to decode from.",
  "routing strategies to determine", "L2", "92d-C", "occupies")
q("Wang2026-BACo", "2511.05650v2", "2511.05650", "v2", A("2511.05650", "v2"), "Abstract",
  "evaluate them across three open-ended generation tasks with 13 diversity and quality metrics. BACo consistently surpasses state-of-the-art inference-time baselines. With our best router, BACo achieves a 21.3% joint improvement in diversity and quality",
  "21.3%", "L2", "92d-C", "occupies")
q("Peeperkorn2025-Conformative", "2507.20956v1", "2507.20956", "v1", A("2507.20956", "v1"), "Abstract",
  "The results indicate that DPO has the most substantial impact on diversity. Motivated by these findings, we present a new decoding strategy, conformative decoding, which guides an instruct model using its more diverse base model to reintroduce output diversity.",
  "conformative decoding", "L2", "92d-B1;92d-C", "occupies")
q("Fei2025-Nudging", "2410.09300v4", "2410.09300", "v4", A("2410.09300", "v4"), "Abstract (v4)",
  "Nudging is motivated by recent findings that alignment primarily alters the model’s behavior on a small subset of stylistic tokens (e.g., discourse markers). We find that base models are significantly more uncertain when generating these tokens.",
  "small subset of stylistic tokens", "L2", "92d-C;92d-A2", "adjacent")
q("Lin2024-URIAL", "2312.01552v1", "2312.01552", "v1", A("2312.01552", "v1"), "Sec. 1 (Introduction)",
  "the top-ranked tokens in aligned LLMs are mostly found within the top five tokens ranked by base LLMs, and the distribution shift is more pronounced in earlier token positions.",
  "top five tokens ranked by base LLMs", "L2", "92d-A2", "supports")
q("Lin2024-URIAL", "2312.01552v1", "2312.01552", "v1", A("2312.01552", "v1"), "Abstract",
  "Most distribution shifts occur with stylistic tokens (e.g., discourse markers, safety disclaimers).",
  "Most distribution shifts occur with stylistic tokens", "L2", "92d-A2", "context")
q("Mitchell2023-EFT", "2310.12962v1", "2310.12962", "v1", A("2310.12962", "v1"), "Sec. 1",
  "Emulated fine-tuning is based on a simple factorization of the logits of a fine-tuned language model into a) the base log probabilities of a pre-trained base model and b) the ‘behavior delta’, or the difference between the log probabilities of a base model and fine-tuned model.",
  "behavior delta", "L2", "92d-B2;92d-C", "baseline-to-add")
q("Liu2024-ProxyTuning", "2401.08565v4", "2401.08565", "v4", A("2401.08565", "v4"), "Fig. 1 caption",
  "The difference between the predicted logits of the expert and the anti-expert is applied as an offset on the original logits from the base model, to guide it in the direction of tuning, while retaining the benefits of larger pretraining scale.",
  "applied as an offset on the original logits", "L2", "92d-B2;92d-C", "baseline-to-add")
q("Dekoninck2024-ModelArithmetic", "2311.14479v3", "2311.14479", "v3", A("2311.14479", "v3"), "Abstract",
  "we introduce model arithmetic, a novel inference framework for composing and biasing LLMs without the need for model (re)training or highly specific datasets.",
  "model arithmetic", "L2", "92d-C", "context")
q("Feng2025-SwitchGeneration", "2510.09913v1", "2510.09913", "v1", A("2510.09913", "v1"), "Abstract",
  "we propose Switch Generation, where pretrained and aligned model versions take turns to “speak” in a response sequence.",
  "Switch Generation", "L2", "92d-C", "occupies")
q("Sahu2026-CreativeInstruct", "2608.07460v1", "2608.07460", "v1", A("2608.07460", "v1"), "Sec. 1",
  "However, these methods incur latency and computational overhead at test-time, requiring two models. Moreover, these frameworks require access to base models, which are not always released.",
  "require access to base models", "L2", "92d-C", "context")
q("Samuel2026-ReDiPO", "2605.30021v2", "2605.30021", "v2", A("2605.30021", "v2"), "Sec. 1",
  "post-training can remove valid answer modes from the instruct model’s candidate distribution in the first place. We therefore use the base model to recover missing alternatives",
  "remove valid answer modes", "L2", "92d-B1;92d-A2", "adjacent")
q("Liu2026-DiversityRouter", "2604.02319v3", "2604.02319", "v3", A("2604.02319", "v3"), "Abstract",
  "Yet, per each prompt, there exists a model that outperforms all other models significantly at generating a diverse answer set. Motivated by this finding, we introduce a router that predicts the best model for each query.",
  "a router that predicts the best model", "L2", "92d-C", "adjacent")
q("Zhang2026-RLReplace", "2610.24663v1", "2610.24663", "v1", A("2610.24663", "v1"), "Abstract",
  "Yet borrowing the RL model’s token only where the two models’ greedy choices differ, roughly 4% of generated positions, recovers 90.5% of the pass@1 gain",
  "recovers 90.5%", "L2", "92d-C;92d-B1", "adjacent")
q("Zhang2026-RLReplace", "2610.24663v1", "2610.24663", "v1", A("2610.24663", "v1"), "Abstract",
  "Sparse replacement also retains much of the base model’s diversity while staying close to the RL model at pass@1.",
  "retains much of the base model", "L2", "92d-C;92d-B1", "adjacent")

# ---------------- LANE 3: base-to-tuned activation transfer / patching ----------------
q("Ward2025-Backtracking", "2507.12638v1", "2507.12638", "v1", A("2507.12638", "v1"), "Abstract",
  "Specifically, we identify a direction in base Llama-3.1-8B’s residual stream which systematically induces backtracking when used to steer the distilled reasoning model",
  "residual stream which systematically induces backtracking", "L3", "92d-B1;92d-B2;FLAG_A", "adjacent")
q("Venhoff2026-BaseKnows", "2510.07364v4", "2510.07364", "v4", A("2510.07364", "v4"), "Abstract",
  "hybrid models recover roughly 76% of the RL base-to-thinking gap but only 11% of the SFT gap. This indicates RL primarily teaches heuristics for orchestrating pre-existing base mechanisms, whereas SFT-distillation installs new ones",
  "orchestrating pre-existing base mechanisms", "L3", "92d-B1;92d-A0", "adjacent")
q("Oozeer2025-Transfer", "2503.04429v4", "2503.04429", "v4", A("2503.04429", "v4"), "Sec. 4.4 (Switch from Fine-tuned to Base Models)",
  "By replacing the fine-tuned model’s activations with the corresponding base model activations, we assess the effectiveness of this technique in mitigating the backdoor.",
  "replacing the fine-tuned model", "L3", "92d-B1;FLAG_A", "method-overlap")
q("Oozeer2025-Transfer", "2503.04429v4", "2503.04429", "v4", A("2503.04429", "v4"), "Sec. 4.4",
  "We observe that patching activations of a single layer can reduce backdoor trigger by up to 60% (refer Figure 23 for layer-wise values).",
  "patching activations of a single layer", "L3", "92d-B1;FLAG_A", "method-overlap")
q("Oozeer2025-Transfer", "2503.04429v4", "2503.04429", "v4", A("2503.04429", "v4"), "Sec. 4.4",
  "The autoencoder successfully simulates direct activation patching at these layers, functioning as a binary switch between fine-tuned and base model behaviors.",
  "binary switch between fine-tuned and base", "L3", "92d-B1;FLAG_A", "method-overlap")
q("Zhou2026-CrossPatching", "2605.07284v2", "2605.07284", "v2", A("2605.07284", "v2"), "Abstract",
  "We distinguish these cases with a four-cell diagnostic that crosses base or descendant upstream states with base or descendant late stacks.",
  "four-cell diagnostic", "L3", "92d-B1;FLAG_A", "method-overlap")
q("Zhou2026-CrossPatching", "2605.07284v2", "2605.07284", "v2", A("2605.07284", "v2"), "Sec. 2.1",
  "At evaluation, the hidden state entering the late boundary is replaced for all sequence positions and the downstream stack recomputes its own keys and values.",
  "hidden state entering the late boundary is replaced", "L3", "92d-B1;FLAG_A", "method-overlap")
q("Zhou2026-CrossPatching", "2605.07284v2", "2605.07284", "v2", A("2605.07284", "v2"), "Sec. 5 (focused validity tests)",
  "The result is also positive at every tested boundary from 40% depth through the final block, so it is not created by one global rotation or one specially chosen cut.",
  "every tested boundary from 40% depth", "L3", "92d-B1;FLAG_A", "method-overlap")
q("Zhou2026-CrossPatching", "2605.07284v2", "2605.07284", "v2", A("2605.07284", "v2"), "Sec. 5 (token and history selection)",
  "Random later disagreements from the same rollouts retain 56% of the first-divergence interaction",
  "Random later disagreements", "L3", "92d-B1;FLAG_A", "method-overlap")
q("Ghandeharioun2024-Patchscopes", "2401.06102v4", "2401.06102", "v4", A("2401.06102", "v4"), "Sec. 4.4 (Expressiveness from Cross-Model Patching)",
  "A possible avenue for improving inspection capabilities is to explain a given model with a model that is more expressive (Bills et al., 2023).",
  "Cross-Model Patching", "L3", "92d-B1", "context")
q("Minder2026-ADL", "2510.13900v3", "2510.13900", "v3", A("2510.13900", "v3"), "Abstract",
  "analyzing activation differences on the first few tokens of random text and steering by adding this difference to the model activations produces text similar to the format and general content of the finetuning data.",
  "Activation Difference Lens", "L5", "92d-B2", "adjacent")
q("Wolfram2025-Layers", "2504.08775v3", "2504.08775", "v3", A("2504.08775", "v3"), "App. A.2, Fig. 8 caption",
  "Instruction tuning changes the activations generated by models in later layers, but only when given inputs that are targeted by instruction tuning.",
  "later layers, but only when given inputs", "L3", "92d-B1", "context")
q("Fu2026-C2C", "2510.03215v2", "2510.03215", "v2", A("2510.03215", "v2"), "Abstract",
  "C2C uses a neural network to project and fuse the source model’s KV-cache with that of the target model to enable direct semantic transfer.",
  "project and fuse the source model", "L3", "92d-B1", "adjacent")
q("ZhangNanda2024-Patching", "2309.16042v2", "2309.16042", "v2", A("2309.16042", "v2"), "Sec. 1 (Recommendations for practice)",
  "At a high-level, our findings highlight the sensitivity of activation patching to methodological details.",
  "sensitivity of activation patching", "L3", "92d-B1", "context")
q("HeimersheimNanda2024", "2404.15255v1", "2404.15255", "v1", A("2404.15255", "v1"), "Sec. 2.3 (Noising and Denoising)",
  "There are multiple ways to do activation patching. The techniques differ in what the source (source of activations / model run from which the activations are copied) and destination prompt",
  "Noising and Denoising", "L3", "92d-B1", "context")
q("Stolfo2025-IFSteering", "2410.12877v2", "2410.12877", "v2", A("2410.12877", "v2"), "Abstract",
  "Finally, we demonstrate that steering vectors computed on instruction-tuned models can transfer to improve base models.",
  "transfer to improve base models", "L3", "92d-B1;92d-B2;FLAG_A", "adjacent")
q("Wang2026-CoTBase", "2511.19131v1", "2511.19131", "v1", A("2511.19131", "v1"), "Sec. 1",
  "Can we solely manipulate the hidden states to elicit CoT reasoning from a base LLM, without distorting its language quality?",
  "solely manipulate the hidden states", "L3", "92d-B1", "adjacent")
q("Sinii2026-SmallVectors", "2509.06608v4", "2509.06608", "v4", A("2509.06608", "v4"), "Sec. 1, findings",
  "steering vectors trained in one model often retain a non-trivial fraction of their performance when inserted into a closely matched model, suggesting that the underlying steering directions are largely preserved under fine-tuning and instruction tuning.",
  "largely preserved under fine-tuning", "L3", "92d-B2;FLAG_A", "adjacent")
q("Sun2026-WeightPatching", "2604.13694v1", "2604.13694", "v1", A("2604.13694", "v1"), "Abstract",
  "Given a base model and a behavior-specialized counterpart, Weight Patching replaces selected module weights from the specialized model into the base model under a fixed input.",
  "Weight Patching replaces selected module weights", "L3", "92d-B1", "adjacent")
q("Zhao2025-ActivationControl", "2505.17697v1", "2505.17697", "v1", A("2505.17697", "v1"), "Sec. 2.3, Finding-4",
  "Based on this finding, it is promising to use the base LLM itself to predict the long-CoT related activations.",
  "use the base LLM itself", "L3", "92d-B1", "adjacent")
q("Wang2026-Data2Behavior", "2602.04735v1", "2602.04735", "v1", A("2602.04735", "v1"), "Abstract",
  "summarizes candidate data through their mean representations and injects them into the forward pass of a base model",
  "injects them into the forward pass of a base model", "L3", "92d-A1;FLAG_B", "adjacent")
q("Gan2026-CREST", "2608.30319v1", "2608.30319", "v1", A("2608.30319", "v1"), "Abstract",
  "we propose CREST, an inference-time alignment method that steers base model hidden representations using safety directions extracted from a guidance model of any family",
  "we propose CREST", "L3", "92d-B1", "adjacent")
q("Yoon2026-Transplant", "2602.16189v1", "2602.16189", "v1", A("2602.16189", "v1"), "Abstract",
  "in transplant experiments between a base model and its instruction-tuned counterpart, transplantation improves the underperforming model toward the stronger baseline",
  "transplant experiments between a base model", "L3", "92d-B1;FLAG_A", "adjacent")
q("Nakamura2026-TemplateDiD", "2605.24583v3", "2605.24583", "v3", A("2605.24583", "v3"), "Abstract",
  "The aligned model is evaluated under a chat template the base model never saw, so the naive difference conflates the alignment shift with chat formatting.",
  "chat template the base model never saw", "L5", "92d-B1;92d-B2", "supports")
q("Anand2026-PASTA", "2605.30526v2", "2605.30526", "v2", A("2605.30526", "v2"), "Abstract (v2; v1 title 'Measuring, Localizing, and Ablating Alignment Signatures in LLMs')",
  "a training-free method that estimates a post-training alignment signature from aligned-base residual contrasts and ablates the corresponding direction during decoding.",
  "aligned-base residual contrasts", "L4", "92d-B2", "occupies")
q("Anand2026-PASTA", "2605.30526v2", "2605.30526", "v2", A("2605.30526", "v2"), "Abstract",
  "this effect transfers well across detectors and is not reproduced by random directions. Qualitative analysis suggests that PASTA generations remain relevant and coherent while exhibiting greater stylistic variation.",
  "not reproduced by random directions", "L4", "92d-B2", "occupies")
q("Anand2026-PASTA", "2605.30526v2", "2605.30526", "v2", A("2605.30526", "v2"), "Sec. 5.1 (Specificity of PASTA's direction)",
  "Each random ablation uses the same residual-stream hook footprint and decoding seed as PASTA.",
  "same residual-stream hook footprint", "L4", "92d-B2", "occupies")

# ---------------- LANE 4: reversibility of sharpening (weights) ----------------
q("Dang2025-WiSEFT", "2504.10478v4", "2504.10478", "v4", A("2504.10478", "v4"), "Abstract",
  "Surprisingly, a simple intervention of interpolating the weights of the latest SFT checkpoint with an early checkpoint, otherwise known as WiSE-FT, almost completely recovers Pass@k while also improving Pass@1.",
  "WiSE-FT", "L4", "92d-B1;baselines", "baseline-to-add")
q("Dang2025-WiSEFT", "2504.10478v4", "2504.10478", "v4", A("2504.10478", "v4"), "Abstract",
  "Finally, we find that WiSE-FT provides complementary performance gains that cannot be achieved only through diversity-inducing decoding strategies, like temperature scaling.",
  "cannot be achieved only through diversity-inducing decoding", "L4", "92d-C;baselines", "baseline-to-add")
q("Dang2025-WiSEFT", "2504.10478v4", "2504.10478", "v4", A("2504.10478", "v4"), "App. H (coding task)",
  "To test whether coding tasks exhibit the same diversity collapse observed in reasoning benchmarks, we fine-tuned the Qwen2.5-coder-0.5B model for 10 epochs on the Magicoder-Evol-Instruct-110K dataset",
  "Qwen2.5-coder-0.5B", "L4", "92d-B1;baselines", "baseline-to-add")
q("Veselovsky2025-Hindsight", "pmlr_hindsight_merging", "PMLR v286 veselovsky25a", "UAI 2025 proceedings page",
  "https://proceedings.mlr.press/v286/veselovsky25a.html", "Abstract (PMLR page)",
  "we introduce hindsight merging, a technique that combines a fine-tuned model with a previous training checkpoint using linear interpolation to restore entropy and improve performance.",
  "hindsight merging", "L4", "92d-B1;baselines", "baseline-to-add")
q("Veselovsky2025-Hindsight", "pmlr_hindsight_merging", "PMLR v286 veselovsky25a", "UAI 2025 proceedings page",
  "https://proceedings.mlr.press/v286/veselovsky25a.html", "Abstract (PMLR page)",
  "achieving a consistent 20-50% increase in pass@10 relative to the instruction tuned model across a coding benchmark and series of models.",
  "20-50% increase in pass@10", "L4", "92d-B1;baselines", "baseline-to-add")
q("Zheng2025-ExPO", "2404.16792v5", "2404.16792", "v5", A("2404.16792", "v5"), "Abstract",
  "Given a partially-trained model and its initial SFT checkpoint, ExPO improves the implicit optimization objective of alignment training by simply amplifying the parameter change based on a first-order approximation",
  "amplifying the parameter change", "L4", "92d-B2", "adjacent")
q("Huang2024-ChatVector", "2310.04799v3", "2310.04799", "v3", A("2310.04799", "v3"), "Abstract",
  "The chat vector is derived by subtracting the weights of a pre-trained base model (e.g. LLaMA2) from those of its corresponding chat model (e.g. LLaMA2-chat).",
  "chat vector is derived by subtracting", "L4", "92d-B2", "adjacent")
q("Ilharco2023-TaskArithmetic", "2212.04089v3", "2212.04089", "v3", A("2212.04089", "v3"), "Abstract",
  "Negating a task vector decreases performance on the target task, with little change in model behavior on control tasks.",
  "Negating a task vector", "L4", "92d-B2", "adjacent")
q("Qi2025-Shallow", "2406.05946v1", "2406.05946", "v1", A("2406.05946", "v1"), "Abstract",
  "safety alignment can take shortcuts, wherein the alignment adapts a model’s generative distribution primarily over only its very first few output tokens.",
  "very first few output tokens", "L4", "92d-B1", "supports")
q("Shenfeld2025-RLsRazor", "2509.04259v1", "2509.04259", "v1", A("2509.04259", "v1"), "Sec. 1",
  "the KL divergence between the fine-tuned and base policy evaluated on the new task.",
  "KL divergence between the fine-tuned and base policy", "L4", "92d-A1", "context")
q("Zhang2026-SLR", "2602.06665v1", "2602.06665", "v1", A("2602.06665", "v1"), "Abstract",
  "we hypothesize that mode collapse can be localized to specific layers and that restoring a carefully chosen range of layers to their pre-trained weights can recover diversity while maintaining high output quality.",
  "restoring a carefully chosen range of layers", "L4", "92d-B1;FLAG_A", "adjacent")
q("Zhang2026-SLR", "2602.06665v1", "2602.06665", "v1", A("2602.06665", "v1"), "Abstract",
  "Selective Layer Restoration (SLR), a training-free method that restores selected layers in a post-trained model to their pre-trained weights, yielding a hybrid model with the same architecture and parameter count, incurring no additional inference cost.",
  "Selective Layer Restoration", "L4", "92d-B1;FLAG_A", "adjacent")
q("Sumita2026-FrankenMerging", "2610.22999v1", "2610.22999", "v1", A("2610.22999", "v1"), "Abstract",
  "This approach combines the lower layers of an aligned model with the higher layers of its base model based on the hypothesis that lexical diversity is more closely associated with lower layers and semantic diversity with higher layers.",
  "combines the lower layers of an aligned model", "L4", "92d-B1;FLAG_A", "adjacent")
q("Sumita2026-FrankenMerging", "2610.22999v1", "2610.22999", "v1", A("2610.22999", "v1"), "Abstract",
  "They also demonstrated a better diversity–quality trade-off than temperature sampling in most settings.",
  "better diversity–quality trade-off than temperature", "L4", "92d-B1;92d-C", "adjacent")

# ---------------- LANE 5: model diffing ----------------
q("Lindsey2024-Crosscoders", "tc_crosscoders_2024", "transformer-circuits.pub/2024/crosscoders", "web (Oct 25, 2024)",
  "https://transformer-circuits.pub/2024/crosscoders/index.html", "Sec. 4 (Model diffing)",
  "Several recent results suggest that finetuned models use similar mechanism as the base model from which they were trained, or mask underlying capabilities in a way that is easily reversible.",
  "easily reversible", "L5", "92d-B1;92d-A2", "context", "VERIFIED-BLOG")
q("Minder2025-Crosscoder", "2504.02922v4", "2504.02922", "v4", A("2504.02922", "v4"), "Abstract",
  "we identify two issues which stem from the crosscoders L1 training loss that can misattribute concepts as unique to the fine-tuned model, when they really exist in both models.",
  "misattribute concepts as unique", "L5", "92d-B2", "context")
q("Kissane2024-SAETransfer", "af_kissane_sae_transfer", "alignmentforum.org/posts/fmwk6qxrpW8d4jvbd", "web (2024)",
  "https://www.alignmentforum.org/posts/fmwk6qxrpW8d4jvbd/saes-usually-transfer-between-base-and-chat-models", "Executive summary",
  "SAEs trained on the base model transfer surprisingly well to reconstructing chat activations",
  "transfer surprisingly well", "L5", "92d-B1", "context", "VERIFIED-BLOG")
q("Kissane2024-SAETransfer", "af_kissane_sae_transfer", "alignmentforum.org/posts/fmwk6qxrpW8d4jvbd", "web (2024)",
  "https://www.alignmentforum.org/posts/fmwk6qxrpW8d4jvbd/saes-usually-transfer-between-base-and-chat-models", "Sec. 1 (introduction of results)",
  "We find that the difference in weights between Gemma v1 2B base vs chat is unusually large compared to other fine-tuned models, explaining this phenomenon.",
  "unusually large compared to other fine-tuned models", "L5", "92d-E", "context", "VERIFIED-BLOG")
q("Minder2025-DiffBlog", "lw_diff_base_chat", "lesswrong.com/posts/xmpauEXEerzYcJKNm", "web (2025)",
  "https://www.lesswrong.com/posts/xmpauEXEerzYcJKNm/what-we-learned-trying-to-diff-base-and-chat-models-and-why", "Summary",
  "We show that you can resolve these issues with a simple architectural adjustment: using a BatchTopK instead of an L1 sparsity loss.",
  "BatchTopK instead of an L1", "L5", "92d-B2", "context", "VERIFIED-BLOG")
q("LW2025-RuntimeSteering", "lw_runtime_steering", "lesswrong.com/posts/dvbRv97GpRg5gXKrf", "web",
  "https://www.lesswrong.com/posts/dvbRv97GpRg5gXKrf/run-time-steering-can-surpass-post-training-reasoning-task", "Limitations",
  "I haven't performed essential baseline tests including random vector patching",
  "random vector patching", "L3", "92d-B2", "adjacent", "VERIFIED-BLOG")
q("Chen2025-PersonaVectors", "2507.21509v3", "2507.21509", "v3", A("2507.21509", "v3"), "Sec. 6.1, Fig. 8 caption",
  "Training data “projection difference” predicts post-finetuning trait expression before finetuning.",
  "projection difference", "L5", "92d-A1;FLAG_B", "adjacent")

# ---------------- round-3 backward snowball anchors (outside the verdict window; context) ----------------
q("Zhao2025-EchoChamber", "2504.07912v2", "2504.07912", "v2", A("2504.07912", "v2"), "Abstract",
  "Our study reveals that RL algorithms consistently converge towards a dominant output distribution, amplifying patterns in the pretraining data.",
  "converge towards a dominant output distribution", "L1", "92d-A2;92d-A0", "supports")
q("Prakash2024-CMAP", "2402.14811v1", "2402.14811", "v1", A("2402.14811", "v1"), "Sec. 1 (Introduction)",
  "Cross-model activation patching shows evidence that (i) the internal representation of both the original model and the fine-tuned models is similar enough so that patching components of the entity-tracking circuit from the fine-tuned models to Llama-7B leads to enhanced performance.",
  "Cross-model activation patching shows evidence", "L3", "92d-B1;FLAG_A", "method-overlap")
q("Du2025-PostTrainingReshapes", "2504.02904v3", "2504.02904", "v3", A("2504.02904", "v3"), "Sec. 3 (knowledge storage)",
  "We further conduct cross-model experiments by patching hidden representations from base to post (forward patching) and from post to base (backward patching).",
  "patching hidden representations from base to post", "L3", "92d-B1;FLAG_A", "method-overlap")
q("Du2025-PostTrainingReshapes", "2504.02904v3", "2504.02904", "v3", A("2504.02904", "v3"), "Sec. 3 (knowledge storage)",
  "The results demonstrate that the forward patching is almost always successful, but the backward patching often fails.",
  "forward patching is almost always successful", "L3", "92d-B1;FLAG_A", "method-overlap")
q("Du2025-PostTrainingReshapes", "2504.02904v3", "2504.02904", "v3", A("2504.02904", "v3"), "Abstract",
  "The truthfulness direction is highly similar between the base and post-trained model, and it is effectively transferable for interventions",
  "truthfulness direction is highly similar", "L3", "92d-B2", "adjacent")

# ---------------- ICLR 2027 submissions (VERIFIED-ABSTRACT) ----------------
OR = "https://api2.openreview.net/notes/search?term="


def orq(ref, fid, quote, rx, lane, rows, rel):
    idx = {}
    for line in (CACHE / "index.jsonl").read_text().splitlines():
        r = json.loads(line)
        idx[r["key"]] = r
    url = idx[f"or_{fid}"]["url"]
    q(ref, f"or_{fid}", f"OpenReview {fid}", "ICLR 2027 submission record", url, "Abstract (OpenReview API record)",
      quote, rx, lane, rows, rel, "VERIFIED-ABSTRACT")


orq("Anon2026-LockedEntrance", "hu5mtofNd4",
    "We show that this contraction is heavily concentrated at the entrance: per-token likelihood shifts are 11x--16x larger prior to the first arithmetic operation than during downstream reasoning.",
    "concentrated at the entrance", "L1", "92d-A0;92d-B1", "supports")
orq("Anon2026-LockedEntrance", "hu5mtofNd4",
    "Supplying only an unselected entrance prefix restores completion rates in low-access families by over an order of magnitude (0.018 to 0.212 under PPO), demonstrating that alternative solutions remain executable but are no longer initiated.",
    "unselected entrance prefix", "L1", "92d-A1;92d-C", "adjacent")
orq("Anon2026-LockedEntrance", "hu5mtofNd4",
    "Guided by this localization, layer interpolation restores entrance diversity and increases solution coverage by 37%, with pass@1 of 0.305 versus 0.278 for the late policy.",
    "layer interpolation restores entrance diversity", "L4", "92d-B1;FLAG_A", "adjacent")
orq("Anon2026-TokenLedger", "cMasrdysrX",
    "tokens, the base the rest) is a conserved ledger",
    "conserved ledger", "L2", "92d-C", "adjacent")
orq("Anon2026-NotWhichPath", "3QlKFFBcNO",
    "Our instrument is a transplant in which one model writes and, wherever the two disagree about the next token, at 3 to 6% of positions, the other model's word is substituted.",
    "the other model's word is substituted", "L2", "92d-B1;92d-C", "adjacent")
orq("Anon2026-NotWhichPath", "3QlKFFBcNO",
    "Forcing each option there shows that both models mostly agree and neither chooses reliably better.",
    "both models mostly agree", "L2", "92d-A2", "context")
orq("Anon2026-TokenCues", "iIw2d3AkJM",
    "Second, we demonstrate that RL itself learns to make these same starting cues more likely, while fixing these cues recovers much of its performance gain over the base model.",
    "same starting cues more likely", "L1", "92d-A2", "supports")
orq("Anon2026-Lookahead", "6a4v7CpeAu",
    "Lookahead outperforms BoN at predicting which IFEval prompts degrade after training",
    "predicting which IFEval prompts degrade", "L1", "92d-A1;FLAG_B", "partly-fires")
orq("Anon2026-HowMuchNotWhere", "uASUNrduuj",
    "we track a forward-only signal: the per-prompt decay rate λ̂ of the likelihood of frozen base-correct trajectories on boundary prompts, those the base model solves only rarely.",
    "frozen base-correct trajectories", "L1", "92d-A1;FLAG_B", "adjacent")
orq("Anon2026-HowMuchNotWhere", "uASUNrduuj",
    "A dose- and schedule-matched control that anchors randomly chosen prompts protects as well as our signal-triggered scheme",
    "anchors randomly chosen prompts", "L1", "92d-A1;FLAG_B", "contradicts-in-part")
orq("Anon2026-PredictiveMI", "BEcwcRFQdu",
    "Which attention heads a post-training update will change, and in which direction, can be forecast before training, from the base model alone.",
    "forecast before training, from the base model alone", "L5", "92d-A1;FLAG_B", "adjacent")
orq("Anon2026-TIRD", "vkIOGTVcJP",
    "fixed activation directions extracted from computational differences between models before and after post-training.",
    "computational differences between models before and after", "L3", "92d-B2", "adjacent")
orq("Anon2026-TIRD", "vkIOGTVcJP",
    "injecting it into the Base model improves reasoning accuracy by up to 50.9 percentage points, while suppressing it substantially degrades the post-trained model.",
    "suppressing it substantially degrades", "L3", "92d-B2", "adjacent")
orq("Anon2026-MergeBeforeRL", "MYXgOex05m",
    "To mitigate this effect, we propose a simple recovery approach: merging the fine-tuned model with its pretrained base model before RL.",
    "merging the fine-tuned model with its pretrained base model", "L4", "92d-B1;baselines", "baseline-to-add")
orq("Anon2026-MergeBeforeRL", "MYXgOex05m",
    "Across multiple mathematical reasoning and code generation benchmarks, base-model merging consistently outperforms recent SFT variants",
    "base-model merging consistently outperforms", "L4", "92d-B1;baselines", "baseline-to-add")
orq("Anon2026-LogitGrafting", "tzXBBz5tmq",
    "Decoding-time methods that take logit differences from auxiliary models and add it to a target model offer a viable solution to this transfer problem.",
    "logit differences from auxiliary models", "L2", "92d-C", "adjacent")
orq("Anon2026-JudgingRLVR", "fnMHUImLl3",
    "We show that both published answers can be read off one fixed (base, RLVR) pair at every sampling budget we test by moving only sampling temperature and scoring rule",
    "moving only sampling temperature and scoring rule", "L1", "92d-A0", "contradicts-in-part")
orq("Anon2026-JudgingRLVR", "fnMHUImLl3",
    "the base-ahead ones concentrate in chat-template cells at low temperature.",
    "chat-template cells", "L1", "92d-A0;92d-B1", "context")
orq("Anon2026-SameCandidates", "ooV5M72O08",
    "92.9% of post-training Top-1 changes remain within the pretrained Top-16 on average, while their relative preferences are substantially reorganized.",
    "remain within the pretrained Top-16", "L1", "92d-A2;FLAG_B", "adjacent")
orq("Anon2026-ReDiverse", "lZQK4G4Ktp",
    "This directional collapse is localized to an identifiable intermediate block at the initial denoising step.",
    "localized to an identifiable intermediate block", "L3", "92d-B1;FLAG_A", "adjacent")
orq("Anon2026-ReDiverse", "lZQK4G4Ktp",
    "At inference time, ReDiverse-TF introduces a training-free mechanism that steers activations along precomputed teacher principal directions.",
    "precomputed teacher principal directions", "L3", "92d-B1;92d-B2;FLAG_A", "adjacent")


def main():
    out = EVID / "quotes_iter5.jsonl"
    out.write_text("")
    idx = {}
    for line in (CACHE / "index.jsonl").read_text().splitlines():
        r = json.loads(line)
        idx[r["key"]] = r
    for rec in Q:  # quote the URL the cached text actually came from (arXiv HTML vN, else PDF vN)
        if rec["cache_key"] in idx and rec["cache_key"][:2].isdigit():
            rec["url"] = idx[rec["cache_key"]]["url"]
            rec["source_type"] = "PDF" if idx[rec["cache_key"]].get("is_pdf") else "HTML"
    texts = {}
    n_ok, bad = 0, []
    for rec in Q:
        key = rec["cache_key"]
        if key not in texts:
            texts[key] = normalise(load_text(key))
        ok = quote_matches(rec["quote"], texts[key])
        aid = rec["id"] if rec["id"][:2].isdigit() else ""
        m = META.get(aid, {})
        venue, ev = VENUE.get(aid, OR_VENUE if rec["status"] == "VERIFIED-ABSTRACT" else
                              (("UAI 2025 (PMLR v286)", "https://proceedings.mlr.press/v286/veselovsky25a.html")
                               if "pmlr" in key else ("grey literature (blog/research update)", rec["url"])))
        rec2 = dict(rec)
        rec2.update({
            "latest_version": m.get("latest_version", ""), "v1_date": (m.get("v1_published") or "")[:10],
            "title_at_latest_version": m.get("title", ""), "first_author": (m.get("authors") or [""])[0],
            "venue_status": venue, "venue_evidence": ev, "retrieval_date": RETRIEVED,
            "status": rec["status"] if ok else "MISMATCH",
        })
        if aid and m and rec["version_quoted"] != m.get("latest_version") and aid != "2506.17871":
            rec2["version_note"] = f"quoted {rec['version_quoted']}, latest {m.get('latest_version')}"
        with out.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec2, ensure_ascii=False) + "\n")
        n_ok += ok
        if not ok:
            bad.append((rec["ref_key"], key, rec["quote"][:90]))
    print(f"{n_ok}/{len(Q)} quotes matched in cached primary text; references: {len(set(r['ref_key'] for r in Q))}")
    for b in bad:
        print("MISMATCH:", *b)


if __name__ == "__main__":
    main()
