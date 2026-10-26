"""Build evidence/quotes.jsonl: every positioning quote, checked against the cached primary text (plan rules 0.4-0.6).

A quote is VERIFIED only if every [...]-separated segment occurs, in order, in the normalised full text of the cited
version (whitespace collapsed, PDF hyphenation undone, ligatures/quotes/dashes mapped, markdown emphasis stripped).
VERIFIED-ABSTRACT = the only primary text available was an abstract (venue page / arXiv abstract).
Usage: python -I tools/build_quotes.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, EVID, load_text, normalise, quote_matches  # noqa: E402

RETRIEVED = "2026-10-21"
META = json.loads((EVID / "arxiv_meta.json").read_text())
INDEX = {}
for line in (CACHE / "index.jsonl").read_text().splitlines():
    r = json.loads(line)
    INDEX[r["key"]] = r

# Versions for papers fetched as unversioned HTML (the page stamp gives the version).
EXTRA_LATEST = {"2503.00691": "v2", "2504.15266": "v4", "2608.30047": "v1", "2507.06463": "v2", "2411.07180": "v5"}
EXTRA_TITLES = {
    "2503.00691": ("How Diversely Can Language Models Solve Problems? Exploring the Algorithmic Diversity of Model-Generated Code", "Seonghyeon Lee"),
    "2504.15266": ("Roll the dice & look before you leap: Going beyond the creative limits of next-token prediction", "Vaishnavh Nagarajan"),
    "2608.30047": ("Can LLM Agents Discover? Evaluating Creativity on ML Engineering Tasks", None),
    "2507.06463": ("Evaluating Efficiency and Novelty of LLM-Generated Code for Graph Analysis", None),
    "2411.07180": ("Gumbel Counterfactual Generation From Language Models", "Shauli Ravfogel"),
}

# venue status + the evidence for it (arXiv comment line, journal_ref, or a proceedings / virtual-site page)
VENUE = {
    "2407.09007": ("NAACL 2025 (Long)", "https://aclanthology.org/2025.naacl-long.141/ ('Anthology ID: 2025.naacl-long.141')"),
    "2601.08070": ("arXiv preprint", "no venue in arXiv comment"),
    "2610.09571": ("arXiv preprint (under review)", "arXiv comment: 'Under Review'"),
    "2310.11324": ("ICLR 2024", "arXiv comment: 'ICLR 2024 Camera Ready version'"),
    "2410.14516": ("ICLR 2025 (poster)", "https://iclr.cc/virtual/2025/poster/28257"),
    "2406.05946": ("ICLR 2025, Outstanding Paper Award", "https://blog.iclr.cc/2025/04/22/announcing-the-outstanding-paper-awards-at-iclr-2025/"),
    "2404.02151": ("ICLR 2025", "arXiv comment: 'Accepted at ICLR 2025'"),
    "2309.02772": ("AAAI 2024", "arXiv comment: 'This paper is accepted by AAAI 2024'"),
    "2606.21619": ("arXiv preprint", "no comment line"),
    "2405.21047": ("NeurIPS 2024", "arXiv comment: 'Accepted to NeurIPS 2024'"),
    "2504.05228": ("COLM 2025", "OpenReview API venue field 'COLM 2025' (forum XZm1ekzERf)"),
    "2610.19157": ("arXiv preprint", "comment: '24 pages, 18 figures'"),
    "2604.03380": ("BEA workshop @ ACL 2026", "arXiv v2 comment: \"Accepted to BEA @ ACL 26'\""),
    "2601.22010": ("ICLR 2026", "arXiv comment: 'Accepted for publication at ICLR 2026'"),
    "2605.11936": ("ICML 2026 Mechanistic Interpretability Workshop (spotlight); not main track",
                   "https://icml.cc/virtual/2026/79614 ('Spotlight in Workshop: Workshop on Mechanistic Interpretability')"),
    "2511.08305": ("AAAI 2026", "arXiv comment: 'Accepted for publication at AAAI 2026'"),
    "2605.08221": ("arXiv preprint", "no comment line"),
    "2606.11599": ("arXiv preprint", "no comment line"),
    "2608.12321": ("arXiv preprint", "no comment line"),
    "2604.27251": ("Findings of EMNLP 2026", "arXiv v3 comment: 'Accepted to the Findings of EMNLP 2026'"),
    "2604.09839": ("ICLR 2026 workshops (Sci4DL, Re-Align)", "arXiv comment"),
    "kotawala": ("NeurIPS 2026 workshop poster (Agents in the Wild); no arXiv record found",
                 "https://neurips.cc/virtual/2026/168286"),
    "2405.00492": ("ICCC 2024", "arXiv comment: 'To be published in the Proceedings of ... ICCC'24'"),
    "2506.09659": ("ICML 2025 workshop poster (EXAIT); not ICML 2025 main track",
                   "https://icml.cc/virtual/2025/51482 ('Poster in Workshop: Exploration in AI Today (EXAIT)')"),
    "2409.03733": ("ICLR 2025 (poster)", "https://iclr.cc/virtual/2025/poster/31034"),
    "2407.02209": ("ICLR 2025 (poster)", "https://iclr.cc/virtual/2025/poster/27717"),
    "2609.00077": ("EMNLP 2026", "arXiv comment: 'Accepted by EMNLP 2026'"),
    "2606.04057": ("ICML 2026 (main-conference poster)", "https://icml.cc/virtual/2026/poster/64782 (arXiv v1 has no comment line)"),
    "2606.10302": ("arXiv preprint", "no comment line"),
    "2505.18949": ("arXiv preprint", "comment: '14 pages, 7 figures'"),
    "2411.07180": ("ICLR 2025", "https://proceedings.iclr.cc/paper_files/paper/2025/hash/e15790966a4a9d85d688635c88ee6d8a-Abstract-Conference.html"),
    "2502.06258": ("ICML 2025", "arXiv journal_ref: 'Proceedings of the 42nd International Conference on Machine Learning (ICML 2025)'"),
    "2605.07984": ("ICML 2026 Workshop on Mechanistic Interpretability", "arXiv comment"),
    "2606.17648": ("arXiv preprint", "no comment line"),
    "2310.15916": ("Findings of EMNLP 2023", "arXiv comment"),
    "2310.15213": ("ICLR 2024", "arXiv comment"),
    "2311.04897": ("CoNLL 2023", "arXiv comment"),
    "2404.00859": ("COLM 2024", "arXiv comment: 'Camera-ready for COLM 2024'"),
    "2606.14530": ("arXiv preprint", "no venue in comment"),
    "2607.05188": ("arXiv preprint", "no comment line"),
    "2603.18353": ("arXiv preprint", "no venue in comment"),
    "2605.05115": ("ICML 2026 Mechanistic Interpretability Workshop (spotlight); not main track",
                   "https://icml.cc/virtual/2026/79460 ('Spotlight in Workshop: Workshop on Mechanistic Interpretability')"),
    "2603.23629": ("arXiv preprint", "no comment line"),
    "2604.07192": ("arXiv preprint", "no comment line"),
    "2605.03052": ("ICML 2026", "arXiv comment: 'ICML 2026'"),
    "2507.13874": ("arXiv preprint", "no comment line"),
    "2605.28664": ("arXiv preprint", "no comment line"),
    "funsearch": ("Nature 625, 468-475 (2024); published 14 December 2023", "https://www.nature.com/articles/s41586-023-06924-6"),
    "2506.13131": ("arXiv preprint (white paper)", "no comment line"),
    "2503.00691": ("Findings of EMNLP 2025", "https://aclanthology.org/2025.findings-emnlp.10/"),
    "2504.15266": ("ICML 2025 (spotlight poster; Outstanding Paper)", "https://icml.cc/virtual/2025/poster/45769"),
    "2608.30047": ("arXiv preprint (a COLM 2026 acceptance is reported only by secondary sites; unconfirmed)", "none primary"),
    "2507.06463": ("arXiv preprint", "no comment line"),
    # surfaced by the 2026-10-21 saturation search
    "or_wJ8HkA8vGN": ("ICLR 2027 submission (under review)", "OpenReview API venue field 'ICLR 2027 Conference Submission'"),
    "or_knirOusGcq": ("ICLR 2027 submission (under review)", "OpenReview API venue field 'ICLR 2027 Conference Submission'"),
    "or_Dl1xo5fqnj": ("ICLR 2027 submission (under review)", "OpenReview API venue field 'ICLR 2027 Conference Submission'"),
    "or_oag3wgNLRh": ("ICLR 2027 submission (under review)", "OpenReview API venue field 'ICLR 2027 Conference Submission'"),
    "or_tZaHwMrvq2": ("ICLR 2027 submission (under review)", "OpenReview API venue field 'ICLR 2027 Conference Submission'"),
    "or_L09agUoh7d": ("ICLR 2027 submission (under review)", "OpenReview API venue field 'ICLR 2027 Conference Submission'"),
    "2608.21595": ("arXiv preprint", "no comment line"),
    "2604.24927": ("ICML 2026", "arXiv v2 comment: 'Accepted in ICML 2026'"),
    "2610.01382": ("arXiv preprint", "no comment line"),
    "2610.02438": ("arXiv preprint", "comment: '30 pages (preprint)'"),
    "2606.24952": ("arXiv preprint", "no comment line"),
    "2609.14151": ("arXiv preprint", "no comment line"),
    "2607.10296": ("arXiv preprint", "no comment line"),
    "2608.30345": ("EMNLP 2026 (Main)", "arXiv comment: 'Accepted to the EMNLP 2026 Main'"),
    "2607.13077": ("arXiv preprint", "no comment line"),
}
OR_TITLES = {
    "or_wJ8HkA8vGN": "Diversity Without Discovery: Why Chain Perturbation Fails to Explore in Latent Test-Time Scaling",
    "or_knirOusGcq": "Before the First Token: A Shared Causal Subspace for Response-Length Planning in LLMs",
    "or_Dl1xo5fqnj": "AJR: Amortized Jacobian Readouts for Prompt-Adaptive Steering",
    "or_oag3wgNLRh": "Rethinking Activation Steering for Mathematical Reasoning: What Actually Drives Its Reasoning Gains?",
    "or_tZaHwMrvq2": "Where Do LLMs Decide to Break the Rules? Mechanistic Localization of Prompt Injection Compliance",
    "or_L09agUoh7d": "Silent Compliance: Separating Constraint Echoing from Instruction Following",
}

# (ref_key, cache_key, arxiv_id or pseudo-id, section, used_in, regex_used, quote)
Q = [
    # ---------- b1 snap-back ----------
    ("Lu2025-NeoCoder", "2407.09007v2", "2407.09007", "Abstract", "b1,b5,c7", "Denial Prompting",
     "We introduce Denial Prompting which pushes LLMs to develop more creative solutions to a given problem by incrementally imposing new constraints on the previous solution, compelling LLMs to adopt new strategies."),
    ("Lu2025-NeoCoder", "2407.09007v2", "2407.09007", "Sec. 5.2 (paragraph above Table 3)", "b1,c7", "copy previous solutions",
     "When stress-testing humans or LLMs to look for more creative solutions, they are very likely to make mistakes and may copy previous solutions during the process."),
    ("Lu2025-NeoCoder", "2407.09007v2", "2407.09007", "Sec. 5.2, text after Table 3 (GPT-4 constraint following 100.0 at t=0 to 14.4 at t=5)", "b1", "Table 3:",
     "It is evident that as the state increases (more hard constraints are imposed), the quality of solutions declines both in terms of correctness and constraint following."),
    ("Lu2025-NeoCoder", "2407.09007v2", "2407.09007", "Abstract", "b5,c8", "falls short",
     "We quantify NeoGauge for various proprietary and open-source models and find that even the most creative model, GPT-4, still falls short of demonstrating human-like creativity."),
    ("Rana2026", "2601.08070v1", "2601.08070", "Abstract", "b1", "87\\.5",
     "In priming failure (87.5% of violations), the instruction’s explicit mention of the forbidden word paradoxically activates rather than suppresses the target representation."),
    ("Yoon2026", "2610.09571v2", "2610.09571", "Abstract", "b1", "37.{0,3}71",
     "We evaluate recent open-source and closed-source LLMs on our negation benchmark and find that, in 37–71% of cases, they repeat the same answer under negation [...]"),
    ("Yoon2026", "2610.09571v2", "2610.09571", "Abstract", "c7", "promot",
     "Our main finding is that specialized attention heads and MLP neurons jointly implement negation by (1) suppressing retrieval of the original answer (e.g., ‘‘Madrid’’) while (2) promoting a favored candidate within the answer category (e.g., ‘‘Paris’’)."),
    ("Yoon2026", "2610.09571v2", "2610.09571", "Abstract", "c6,c7", "bias toward",
     "[...] so the model can repeat the original answer when suppression is too weak or when a bias toward particular answers prevents it from selecting an alternative."),
    # ---------- b2 wording ----------
    ("Sclar2024", "2310.11324v2", "2310.11324", "Abstract", "b2", "76 accuracy points",
     "We find that several widely used open-source LLMs are extremely sensitive to subtle changes in prompt formatting in few-shot settings, with performance differences of up to 76 accuracy points when evaluated using LLaMA-2-13B."),
    ("Heo2025", "2410.14516v5", "2410.14516", "Abstract", "b2,b7,c6", "instruction-following dimension|phrasing of prompts",
     "Our analysis identifies a direction in the input embedding space, termed the instruction-following dimension, that predicts whether a response will comply with a given instruction. [...] Further investigation reveals that this dimension is more closely related to the phrasing of prompts rather than the inherent difficulty of the task or instructions."),
    # ---------- b3 body opening ----------
    ("Qi2025", "2406.05946v1", "2406.05946", "Abstract", "b3", "first few output tokens",
     "safety alignment can take shortcuts, wherein the alignment adapts a model’s generative distribution primarily over only its very first few output tokens. We refer to this issue as shallow safety alignment."),
    ("Qi2025", "2406.05946v1", "2406.05946", "Sec. 1 Introduction", "b3", "prefill",
     "For example, simply prefilling an unaligned base model to start its output with a prefix “I cannot fulfill” is sufficient to make it as safe as aligned models."),
    ("Andriushchenko2025", "2404.02151v4", "2404.02151", "Abstract", "b3", "prefill",
     "We also show how to jailbreak all Claude models—that do not expose logprobs—via either a transfer or prefilling attack with a 100% success rate."),
    ("Zhu2024-AdapT", "2309.02772v3", "2309.02772", "Abstract", "b3,c3", "challenging tokens|code block",
     "With an analysis of loss distributions of code tokens, we find that code tokens can be divided into two categories: challenging tokens that are difficult to predict and confident tokens that can be easily inferred. Among them, the challenging tokens mainly appear at the beginning of a code block."),
    # ---------- b4 vetoes ----------
    ("Biagiola2026", "2606.21619v1", "2606.21619", "Abstract", "b4,c8", "low-probability regions",
     "Incompleteness pushes the model into low-probability regions of the program space, causing the generation to frequently time out, and reducing functional correctness by up to 97%."),
    ("Park2024-GAD", "2405.21047v4", "2405.21047", "Abstract", "b4", "distort|proportional",
     "In this paper we demonstrate that GCD techniques (and in general constrained decoding techniques) can distort the LLM’s distribution, leading to outputs that are grammatical but appear with likelihoods that are not proportional to the ones given by the LLM, and so ultimately are low-quality."),
    # ---------- b5 / c8 novelty ----------
    ("Zhang2025-NoveltyBench", "2504.05228v4", "2504.05228", "Abstract", "b5,c8", "less diversity|larger models",
     "Evaluating 20 leading language models, we find that current state-of-the-art systems generate significantly less diversity than human writers. Notably, larger models within a family often exhibit less diversity than their smaller counterparts, challenging the notion that capability on standard benchmarks translates directly to generative utility."),
    ("Jangra2026-DivAlgo", "2610.19157v1", "2610.19157", "Abstract", "b5,c1,c8", "unable to reproduce",
     "Moreover, while it was possible to steer the models to generate solutions based on human strategies, they were unable to reproduce the diversity of the human solutions."),
    ("Jangra2026-DivAlgo", "2610.19157v1", "2610.19157", "Sec. 1 Introduction", "c1", "verbali[sz]ed",
     "Even when using diverse code generation strategies such as temperature variations, verbalized sampling Zhang et al. (2025), and iterative constrained generation Ye et al. (2025), we can only achieve up to 70.5% diversity relative to human solutions with an equal number of samples (Section 5.1)."),
    ("Jangra2026-DivAlgo", "2610.19157v1", "2610.19157", "Sec. 5.1", "c1,c8", "70\\s?%",
     "The strongest single-model approach still captures only 70% of human diversity at a matched sample size, highlighting the limitations of LLMs in eliciting human-level algorithmic variety."),
    ("Lee2025", "2503.00691v2", "2503.00691", "Abstract", "c1,c3", "low algorithmic diversity|temperature",
     "Our analysis demonstrates that model-generated solutions exhibit low algorithmic diversity, which was neglected by the research community. [...] Our findings highlight that code diversity can be enhanced with the help of heterogeneous models and setting temperature beyond 1.0 that has not been fully explored due to the functional correctness degradation."),
    # ---------- b6 random pushes / activation noise ----------
    ("Khalid2026-NoiseSteering", "2604.03380v2", "2604.03380", "Abstract (p. 1, PDF)", "b6,c1", "Residual stream noise consistently",
     "Residual stream noise consistently improves narrative diversity with minimal quality or constraint cost and preserves early-grade reading level across all Arabic-centric models."),
    ("Khalid2026-NoiseSteering", "2604.03380v2", "2604.03380", "Abstract (p. 1, PDF)", "c2", "injection strateg",
     "We compare four injection strategies against high-temperature sampling baselines, measuring diversity, quality, constraint adherence, and reading grade level."),
    ("Khalid2026-NoiseSteering", "2604.03380v2", "2604.03380", "Sec. 4.4 (AENI), PDF", "c2", "only the last token position",
     "As with attention-logit noise, only the last token position of the attention output (shape (B, 1, D) during decoding) is perturbed and the KV cache is left intact."),
    ("Khalid2026-NoiseSteering", "2604.03380v2", "2604.03380", "Sec. 6.1, PDF", "c2", "earliest injection site",
     "Because embedding noise acts at the very first step of the residual stream, before any transformer computation has occurred, any perturbation there propagates through every subsequent layer."),
    ("Zhu2026-STARS", "2601.22010v1", "2601.22010", "Sec. 1 Introduction", "b6,c1", "Existing methods for inducing diversity primarily",
     "Existing methods for inducing diversity primarily perturb the token-level sampling process."),
    ("Zhu2026-STARS", "2601.22010v1", "2601.22010", "Sec. 6.1 Test Case Generation", "b6,flagA", "correctness check|coverage",
     "After generation, all test cases must undergo a correctness check. [...] The overall coverage for a program is computed by the proportion of lines/branches in the program that have been covered by at least one test case"),
    ("Zhu2026-STARS", "2601.22010v1", "2601.22010", "Sec. 6.1 Test Case Generation", "b6,flagA", "1\\.5-2b",
     "Table 1 demonstrates that the STARS method consistently outperforms the temperature sampling approach (labeled as sampling) across all temperature settings and evaluation metrics on both the GEMMA-1.5-2B-IT and QWEN3-1.7B models."),
    ("Zhu2026-STARS", "2601.22010v1", "2601.22010", "Appendix B.3 Compare intervention positions", "c2", "We investigate two natural intervention points",
     "We investigate two natural intervention points within each transformer layer: (1) before the output projection of the attention mechanism (o_proj), which captures the attended representations before they are projected back to the residual dimension, and (2) the output of the MLP block, which represents the processed information after the feed-forward transformation."),
    ("Kim2026-REI", "2605.11936v2", "2605.11936", "Abstract", "b6,c1,c2", "freshly drawn",
     "We study Random Soft Prompts (RSPs), which drop the training step entirely and append a freshly drawn sequence of random embedding vectors to the input."),
    ("Kim2026-REI", "2605.11936v2", "2605.11936", "Abstract", "c2", "first few|dilute",
     "because attention has to absorb a never-seen-before random position, the distribution over the first few generated tokens flattens and reasoning trajectories branch, and as generation continues this influence dilutes naturally so the response commits to a single completion."),
    ("Kim2026-REI", "2605.11936v2", "2605.11936", "Sec. 5 Conclusion (future work)", "b6,flagA", "whether the same diversity gains transfer",
     "Open questions include whether the mechanism extends beyond RoPE-based decoders and math reasoning, whether RSP admits a continuous control dial like temperature sampling (e.g., via the RSP norm or its mixing ratio with real tokens), and whether the same diversity gains transfer to tasks with multiple valid answers such as code generation or open-ended reasoning."),
    ("Ho2025-SPREAD", "2511.08305v1", "2511.08305", "Abstract", "b6,flagA", "mathematical",
     "Empirical evaluations on popular mathematical benchmarks demonstrate that our test-time Riemannian activation steering strategy outperforms vanilla sampling techniques in terms of generative diversity and solution accuracy."),
    ("Jerge2026-NoisyCoconut", "2605.08221v1", "2605.08221", "Abstract", "b6", "noise",
     "Rather than training models to reason in latent space, we inject controlled noise into latent trajectories to generate diverse reasoning paths. Agreement among these paths provides a confidence signal, enabling models to abstain when uncertain."),
    ("Nagarajan2025-SeedCond", "2504.15266v4", "2504.15266", "Abstract", "c1,c2", "seed-conditioning",
     "Secondly, to elicit randomness without hurting coherence, we find that injecting noise at the input layer (dubbed seed-conditioning) works surprisingly as well as (and in some conditions, better than) temperature sampling from the output layer."),
    ("Deshpande2026", "2605.28664v1", "2605.28664", "Abstract", "c8", "steering strength reduces",
     "[...] and find that increasing steering strength reduces response diversity."),
    # ---------- b7 / c6 compliance prediction ----------
    ("Fan2026-ASTEER", "2606.11599v1", "2606.11599", "Abstract", "b7,c6,flagB", "macro-F1|under-steer",
     "We then train a Gradient Boosting Decision Trees (GBDT) classifier on these features to predict whether an intervention will under-steer, succeed, or over-steer without requiring full rollout. Our predictor achieves around 0.7 macro-F1 score on unseen concepts, demonstrating that early hidden states encode substantial, structured information about eventual steering efficacy."),
    ("Fan2026-ASTEER", "2606.11599v1", "2606.11599", "Appendix A.1", "b7,flagB", "steering refers exclusively",
     "Although the term “steering” is sometimes used broadly in the literature to describe instruction following or prompt engineering, in this work, steering refers exclusively to inference-time activation engineering, where carefully calculated vectors are injected into the residual stream to alter model behavior without weight updates."),
    ("Li2026-Routing", "2608.12321v1", "2608.12321", "Abstract", "b7,c6", "routing problem",
     "Hidden-constraint failure is a routing problem, not a knowledge problem."),
    ("Tan2026-Compliance", "2604.27251v3", "2604.27251", "Abstract", "b7,c6", "compliance",
     "Probing reveals instruction decodability even without compliance, while CKA identifies geometric differences across models and spans."),
    ("Mishra2026", "2604.09839v2", "2604.09839", "Abstract", "b7,c5,c6", "Almost surely|formal separation",
     "Almost surely, no prompt can reproduce the same internal behavior induced by steering. [...] Our results establish a formal separation between white-box steerability and black-box prompting."),
    ("Kotawala2026", "venue_neurips26_injection", "kotawala", "Abstract on the NeurIPS 2026 virtual-site page", "b7,c6,flagB", "linear probe on the last prompt-token",
     "On Qwen2.5-3B-Instruct, a linear probe on the last prompt-token residual stream predicts whether an injected instruction will be obeyed at ROC-AUC 0.90 (0.92 document-grouped), read before the first token is generated."),
    # ---------- c1 knob price ----------
    ("Peeperkorn2024", "2405.00492v1", "2405.00492", "Abstract", "c1,c3", "weakly correlated with novelty",
     "We find that temperature is weakly correlated with novelty, and unsurprisingly, moderately correlated with incoherence, but there is no relationship with either cohesion or typicality."),
    ("Ahmed2025-IFG", "2506.09659v1", "2506.09659", "Abstract", "c1,c3", "token-level",
     "Current methods for increasing diversity often only operate at the token-level, paraphrasing the same response."),
    ("Ahmed2025-IFG", "2506.09659v1", "2506.09659", "Abstract", "c1", "higher temperature during the intent",
     "This factorisation allows us to use a higher temperature during the intent step to promote conceptual diversity, and a lower temperature during the final generation to ensure the outputs are coherent and self-consistent."),
    ("Ahmed2025-IFG", "2506.09659v1", "2506.09659", "Abstract", "c1", "pass@k",
     "We show this method improves both pass@k and Reinforcement Learning from Verifier Feedback (RLVF) on maths and code tasks."),
    ("Ahmed2025-IFG", "2506.09659v1", "2506.09659", "Sec. 3 (method)", "c3", "dominated by changes in phrasing",
     "As shown in Figure 2(a), when sampling from LLMs, intent and phrasing are latent variables, and although increasing temperature will increase the entropy of both, the increase tends to be dominated by changes in phrasing (Peeperkorn et al., 2024)."),
    ("Wang2025-PlanSearch", "2409.03733v2", "2409.03733", "Abstract", "c1", "lack of diversity",
     "We empirically demonstrate that this lack of diversity can be mitigated by searching over candidate plans for solving a problem in natural language."),
    ("Wu2025-Monoculture", "2407.02209v1", "2407.02209", "Abstract", "c1", "insufficient",
     "We experimentally demonstrate the prevalence of generative monoculture through analysis of book review and code generation tasks, and find that simple countermeasures such as altering sampling or prompting strategies are insufficient to mitigate the behavior."),
    ("He2026-BeneathDiff", "2609.00077v1", "2609.00077", "Abstract", "c1,c3", "surface-level edit diversity",
     "In this regime, surface-level edit diversity remains stable, but semantic and mechanism-level diversity collapse: the agent continues to edit different lines of code while repeatedly proposing the same kinds of algorithmic changes."),
    ("Narula2026-Lottery", "2606.04057v1", "2606.04057", "Abstract", "c1,c7", "up to 100|Direct algorithm naming",
     "We find large, systematic shifts in algorithm-family distributions (up to 100 pp), largely consistent with cue semantics, including in applied tasks such as rate limiting. Direct algorithm naming is the most reliable mitigation we tested."),
    ("Narula2026-Lottery", "2606.04057v1", "2606.04057", "Sec. 1 Introduction", "c1", "mean 26 pp shift",
     "Cues we designed as neutral placebos (team names, project codes, color themes) still produced a mean 26 pp shift [...]"),
    ("Narula2026-Lottery", "2606.04057v1", "2606.04057", "Sec. 5.6 Mitigation", "c6,c7", "strict compliance is 73/120",
     "Pass rate is 120/120 (100%); strict compliance is 73/120 (60.8%) and 118/120 (98.3%) after normalizing for label-granularity synonyms documented in Appendix A.6 (e.g., “dynamic programming” satisfied by bottom-up tabulation)."),
    # ---------- c2 site ----------
    ("Zhang2026-DiversityInjection", "2606.10302v1", "2606.10302", "Abstract", "c2", "transmission score",
     "We introduce a framework that characterizes test-time diverse generation methods by the diversity source introduced during generation and provide a transmission score for measuring how effectively variation in the source reaches the final output."),
    ("Zhang2026-DiversityInjection", "2606.10302v1", "2606.10302", "Sec. 3.3, text after Definition 1 (Transmission Score)", "c2", "fraction of source diversity",
     "It measures the fraction of source diversity that is realized in the final output."),
    ("Zhang2026-DiversityInjection", "2606.10302v1", "2606.10302", "Sec. 3.2, 'The Level 2 Gap'", "c1,c2", "no existing test-time method",
     "To our knowledge, no existing test-time method provides per-output specifications to promote diversity in general open-ended generation."),
    ("Zhang2026-DiversityInjection", "2606.10302v1", "2606.10302", "Sec. 3.2, 'Level 1 Methods' (on SSOT)", "c2", "no semantic content",
     "However, it carries no semantic content about the desired output’s topic or organization."),
    ("Zhang2026-DiversityInjection", "2606.10302v1", "2606.10302", "Sec. 5.1, Table 2 caption", "c2", "evaluated only on Qwen3-4B",
     "G2 and High Temperature require access to the model and are evaluated only on Qwen3-4B."),
    # ---------- c3 same seed ----------
    ("Yun2025-PriceOfFormat", "2505.18949v1", "2505.18949", "Abstract", "c3", "structural tokens",
     "We systematically evaluate this effect across tasks like story completion and free-form generation, finding that (1) diversity collapse persists even under high-temperature sampling, and (2) structural tokens in templates significantly constrain the model’s output space."),
    ("Ravfogel2025-Gumbel", "2411.07180v5", "2411.07180", "Abstract", "c3", "same instantiation of the sampling noise",
     "This reformulation allows us to model the joint distribution over original strings and their counterfactuals resulting from the same instantiation of the sampling noise."),
    # ---------- c4 plan subspace ----------
    ("Dong2025-ERP", "2502.06258v3", "2502.06258", "Abstract", "c4", "prompt representations",
     "Through simple probing, we demonstrate that LLM prompt representations encode global attributes of their entire responses, including structure attributes (e.g., response length, reasoning steps), content attributes (e.g., character choices in storywriting, multiple-choice answers at the end of response), and behavior attributes (e.g., answer confidence, factual consistency)."),
    ("Ma2026-WheresThePlan", "2605.07984v2", "2605.07984", "Abstract", "c4", "only Gemma-3-27B",
     "Activation patching reveals that only Gemma-3-27B causally relies on this encoding, exhibiting a handoff in which the causal driver migrates from the rhyme word to the line boundary around layer 30. Every other model we test conditions on the rhyme word throughout generation, with near-zero causal effect at the line boundary despite strong probe signal."),
    ("Chen2026-Brewing", "2606.17648v3", "2606.17648", "Sec. 1 Introduction", "c4", "linearly recoverable",
     "Our framework reveals three diagnostic notions that characterize how answer representations develop across model layers [...] the correct answer is linearly recoverable from the hidden representation."),
    ("Chen2026-Brewing", "2606.17648v1", "2606.17648", "Abstract (v1 only; wording removed in v2/v3)", "c4,corrections", "self-decodable",
     "We study an internal lifecycle of code reasoning in which models first brew the answer, making it linearly recoverable many layers before it becomes self-decodable, and then diverge into one of four resolution outcomes (Resolved, Overprocessed, Misresolved, or Unresolved)."),
    ("Hendel2023", "2310.15916v1", "2310.15916", "Sec. 8 Conclusions", "c4", "single task vector",
     "We have revealed a simple and elegant structure: ICL functions by compressing a given training set into a single task vector, which then guides the transformer to generate appropriate outputs given queries."),
    ("Todd2024", "2310.15213v2", "2310.15213", "Abstract", "c4", "compact representation",
     "Using causal mediation analysis on a diverse range of in-context-learning (ICL) tasks, we find that a small number attention heads transport a compact representation of the demonstrated task, which we call a function vector (FV)."),
    ("Pal2023-FutureLens", "2311.04897v1", "2311.04897", "Abstract", "c4", "48%",
     "We find that, at some layers, we can approximate a model’s output with more than 48% accuracy with respect to its prediction of subsequent tokens through a single hidden state."),
    ("Wu2024-PlanAhead", "2404.00859v2", "2404.00859", "Abstract", "c4", "pre-caching|breadcrumbs",
     "In a constructed synthetic data setting, we find clear evidence for pre-caching. In the autoregressive language modeling setting, our experiments are more suggestive of the breadcrumbs hypothesis, though pre-caching increases with model scale."),
    ("DiCicco2026", "2606.14530v3", "2606.14530", "Abstract (v3)", "c4,corrections", "AUC",
     "The correctness of the model’s first-attempt code is linearly decodable from the hidden state at the final prompt token, captured before any output token is generated, with a leakage-free held-out AUC of 0.881 [...]"),
    ("DiCicco2026", "2606.14530v1", "2606.14530", "Abstract (v1)", "corrections", "AUC",
     "First, the correctness of the model’s first-attempt code is linearly decodable from the prompt-final hidden state, with a leakage-free held-out AUC of 0.931 [...]"),
    ("DiCicco2026", "2606.14530v2", "2606.14530", "Abstract (v2)", "corrections", "AUC",
     "First, the correctness of the model’s first-attempt code is linearly decodable from the prompt-final hidden state, with a leakage-free held-out AUC of 0.955 [...]"),
    ("Silva2026", "2607.05188v1", "2607.05188", "Abstract", "c4", "residual streams",
     "We show that the residual streams of language models under coding agents linearly encode properties of the evolving program [...] Probes trained to predict the outcome of future edits (before they are materialized and written on disk) achieve performance above chance up to roughly 25 steps in advance."),
    ("Basu2026", "2603.18353v1", "2603.18353", "Abstract", "c4", "98\\.2",
     "Linear probes trained on Qwen’s internal representations discriminated hazardous from benign cases with 98.2% AUROC (95% CI 0.968 to 0.993), demonstrating a 53-percentage-point gap between internal knowledge and output behaviour."),
    # ---------- c5 geometry ----------
    ("Wurgaft2026-ManifoldSteering", "2605.05115v1", "2605.05115", "Abstract", "c5", "cuts through off-manifold",
     "[...] linear steering—which assumes a Euclidean geometry—cuts through off-manifold regions and hence produces unnatural outputs."),
    ("Wurgaft2026-ManifoldSteering", "2605.05115v1", "2605.05115", "Sec. 4, figure caption (isometry test)", "c5", "multidimensional scaling",
     "Furthermore, on-manifold distances in activation space show strong correlation with on-manifold distances in behavior space (right column), as well as a clear structural match via a multidimensional scaling (MDS) embedding (middle column)."),
    ("Rahman2026-CodeSteering", "2603.23629v2", "2603.23629", "Abstract", "c5", "difference-in-means",
     "Using a difference-in-means method, we estimate layer-wise steering vectors for five language/library pairs and add them to model hidden states during generation. Across three open-weight code LLMs, these interventions substantially increase generation toward the target ecosystem under neutral prompts and often remain effective even when prompts explicitly request the opposite choice."),
    # ---------- c6 Tang ----------
    ("Tang2026", "2604.07192v2", "2604.07192", "Sec. 5.3 'Why Counter-Intuitive Constraints Fail' (PDF)", "c6,corrections", "implementation prior",
     "It suggests that LLMs possess implementation priors—default code patterns for common tasks (e.g., \"styling React components\" → inline style objects)—that compete with explicit constraints."),
    ("Tang2026", "2604.07192v2", "2604.07192", "Abstract (PDF p. 1)", "c6", "10.{1,3}100%",
     "counter-intuitive constraints opposing model defaults fail at rates of 10–100% [...] while conventional constraints achieve 99%+ compliance regardless of encoding."),
    ("Tang2026", "2604.07192v2", "2604.07192", "Sec. 5.3 (PDF)", "c6,c7", "positive constraints",
     "First, positive constraints (\"use X\") appear easier to follow than negative constraints (\"do not use Y\"), presumably because the latter requires suppressing an activated implementation path."),
    # ---------- c7 negation ----------
    ("Zhou2026-Negation", "2605.03052v2", "2605.03052", "Sec. 1 Introduction (contributions)", "c7", "overshadowed",
     "We show that LLMs’ failures on negation queries arise not from the absence of negation ability, but because their negation processing mechanisms are overshadowed by other mechanisms at later layers."),
    ("Zhou2026-Negation", "2605.03052v2", "2605.03052", "Sec. 1 Introduction", "c7", "we reveal that construction",
     "Overall, we reveal that construction and suppression work collaboratively to compute negation; the model computes a negated representation in its mid-layer attention outputs (e.g. interpreting “not gas” as “solid”), while also suppressing the negated concept."),
    # ---------- c8 ----------
    ("Bystronski2025", "2507.13874v2", "2507.13874", "Abstract", "c8", "substantially increases generative diversity",
     "Our experiments demonstrate that this manifold-based conditioning substantially increases generative diversity, with direct benefits for enhancing divergent thinking, a core facet of creativity, in language models."),
    ("RomeraParedes2024-FunSearch", "funsearch_nature", "funsearch", "Abstract (Nature article page)", "c8", "systematic evaluator|cap set",
     "Here we introduce FunSearch (short for searching in the function space), an evolutionary procedure based on pairing a pretrained LLM with a systematic evaluator. [...] Applying FunSearch to a central problem in extremal combinatorics—the cap set problem—we discover new constructions of large cap sets going beyond the best-known ones, both in finite dimensional and asymptotic cases."),
    ("Novikov2025-AlphaEvolve", "2506.13131v1", "2506.13131", "Abstract", "c8", "evaluators",
     "Using an evolutionary approach, continuously receiving feedback from one or more evaluators, AlphaEvolve iteratively improves the algorithm, potentially leading to new scientific and practical discoveries."),
    ("Bhushan2026-AgentCreativity", "2608.30047v1", "2608.30047", "Abstract", "c8", "lack the capacity",
     "Our findings reveal that current agents can explore novel regions of the solution space but lack the capacity to convert this novelty into improved task performance."),
    ("GraphNovelty2025", "2507.06463v2", "2507.06463", "Abstract", "c8", "established algorithms",
     "Although our findings demonstrate that contemporary LLMs excel in optimizing and integrating established algorithms, the potential for these models to eventually invent transformative algorithmic techniques represents a compelling frontier for future research."),
    # ---------- saturation-search hits (2026-10-21) ----------
    ("ICLR27-DiversityWithoutDiscovery", "or_wJ8HkA8vGN", "or_wJ8HkA8vGN", "OpenReview abstract (ICLR 2027 submission)", "b6,c1,c8", "fairly compare latent perturbation",
     "we fairly compare latent perturbation methods with standard explicit reasoning on a shared backbone and find that, for unconstrained latent thoughts, i.e., thoughts not restricted to the embedding space, aggregating perturbed latent chains brings no gain over the no-sampling baseline, whereas explicit reasoning turns the same budget into accuracy gains."),
    ("ICLR27-DiversityWithoutDiscovery", "or_wJ8HkA8vGN", "or_wJ8HkA8vGN", "OpenReview abstract (ICLR 2027 submission)", "c8", "borderline samples",
     "Empirically, the added diversity comes predominantly from borderline samples and, unlike with explicit reasoners, a correct answer reached through perturbation carries no gain in confidence."),
    ("ICLR27-BeforeTheFirstToken", "or_knirOusGcq", "or_knirOusGcq", "OpenReview abstract (ICLR 2027 submission)", "c4", "encoded before the first generated token",
     "We first show that future response length is encoded before the first generated token: controlled length perturbations induce persistent changes in response length even when the explicit length signal is unavailable during subsequent decoding, supporting the existence of a pre-generation planning state rather than a purely autoregressive length effect."),
    ("ICLR27-BeforeTheFirstToken", "or_knirOusGcq", "or_knirOusGcq", "OpenReview abstract (ICLR 2027 submission)", "c4", "parallel and orthogonal",
     "We further establish its causal role by decomposing hidden-state interventions into components parallel and orthogonal to the learned subspace."),
    ("ICLR27-AJR", "or_Dl1xo5fqnj", "or_Dl1xo5fqnj", "OpenReview abstract (ICLR 2027 submission)", "c4,c6", "mispredict intervention effects",
     "Reading a language model's hidden state and predicting what will happen if we change it are different tasks. [...] learned decoders read unmodified states accurately but often mispredict intervention effects, whereas AJR learns their local response."),
    ("ICLR27-RethinkingSteeringMath", "or_oag3wgNLRh", "or_oag3wgNLRh", "OpenReview abstract (ICLR 2027 submission)", "b6,c1,c8", "already supported by the model",
     "they alter local decoder preferences and redirect generation among reasoning trajectories already supported by the model. Correct solutions and related reasoning strategies are frequently accessible under unsteered sampling."),
    ("ICLR27-RethinkingSteeringMath", "or_oag3wgNLRh", "or_oag3wgNLRh", "OpenReview abstract (ICLR 2027 submission)", "c1", "departure from greedy",
     "More directly, ordinary stochastic decoding whose parameters are selected to match steering's aggregate departure from greedy decoding achieves comparable accuracy while substantially reducing the remaining marginal benefit of steering; whole-thought exploration reproduces the same pattern."),
    ("ICLR27-BreakTheRules", "or_tZaHwMrvq2", "or_tZaHwMrvq2", "OpenReview abstract (ICLR 2027 submission)", "c4,c6", "late-layer bottleneck",
     "attack information is linearly decodable from the first layer, yet causal leverage over the model's behavior is negligible until a late-layer bottleneck in the final third of the network."),
    ("ICLR27-SilentCompliance", "or_L09agUoh7d", "or_L09agUoh7d", "OpenReview abstract (ICLR 2027 submission)", "b1,c7", "reintroduce the excluded object",
     "Modern language models increasingly follow negative instructions well. Yet even a compliant response may restate the rule, announce compliance, or reintroduce the excluded object."),
    ("Jerge2026-NCGRPO", "2608.21595v1", "2608.21595", "Abstract", "c1,c2", "last hidden layer of the prompt",
     "Existing approaches diversify through decoding temperature or pixel-space image distortion; we ask whether the perturbation belongs in the model’s latent space instead. We introduce Noise-Contrastive GRPO (NC-GRPO), which injects scale-calibrated Gaussian noise into the last hidden layer of the prompt-encoding pass for half of each rollout group, branching those rollouts from a displaced departure state."),
    ("Zeng2026-ESamp", "2604.24927v2", "2604.24927", "Sec. 1 Introduction", "c1,c3", "surface-level lexical variation",
     "Unfortunately, naive sampling strategies (Ackley et al., 1985) frequently fall into this trap, as stochastic perturbations at the token level tend to induce surface-level lexical variation without substantially altering the underlying reasoning strategy."),
    ("Geng2026-Gacha", "2610.01382v1", "2610.01382", "Abstract", "c1", "instruction-following problem",
     "Our key insight is to treat diversity as an instruction-following problem: rather than relying on the LM’s token entropy, we combine its instruction-following capability with randomness from an external RNG tool to scalably identify and realize distinct modes of the response space."),
    ("Maveli2026-AlgoREval", "2610.02438v1", "2610.02438", "Abstract", "c8", "parametric code retrieval",
     "We argue that for well-known algorithms whose canonical implementations are widely accessible in pretraining corpora, code generation is better measured as parametric code retrieval: reproducing a named algorithm from internalised knowledge rather than synthesizing a novel one."),
    ("Galeone2026-DetectionVsControl", "2606.24952v1", "2606.24952", "Abstract", "c4", "detection-intervention gap",
     "If not, the cosine between them quantifies what we call the detection-intervention gap."),
    ("Bhattarai2026-SteerabilitySignatures", "2609.14151v1", "2609.14151", "Abstract", "b7,c6,flagB", "strongly correlate",
     "We make this dataset-dependence claim more rigorous and show that simple separation metrics strongly correlate with the downstream steerability of language models across diverse settings, even after controlling for layers and dataset effects."),
    ("Zhang2026-SPARK", "2607.10296v1", "2607.10296", "Abstract", "b7,c6,flagB", "we introduce SPARK",
     "In this paper, we introduce SPARK, which uses hidden-state response to diagnose whether a model internally enters an effective reasoning state and to guide lightweight test-time steering."),
    ("Fang2026-APTS", "2608.30345v1", "2608.30345", "Abstract", "c1,flagA", "hidden states of probed answers",
     "We demonstrate that the hidden states of probed answers more effectively differentiate distinct solution paths than semantic embeddings, and the perplexity of probed answers serves as a practical proxy for reasoning correctness."),
    ("Burtch2026-Hitchhiker", "2607.13077v3", "2607.13077", "Results (PDF)", "c1", "notably not affected",
     "However, function calls involving machine-learning algorithms are notably not affected."),
    ("Kotawala2026", "venue_neurips26_injection", "kotawala", "Abstract on the NeurIPS 2026 virtual-site page", "b7,flagB", "only partly steerable",
     "We show that this decision is readable before generation and only partly steerable."),
    # ---------- venue / policy evidence ----------
    ("Policy-ICLR2027", "policy_iclr27_reviewer", "policy", "ICLR 2027 Reviewer Guide, FAQ", "contemporaneity", "contemporaneous",
     "We consider papers contemporaneous if they are published within the last two months. That means, since our full paper deadline is September 16, if a paper was published (i.e., at a peer-reviewed venue) on or after July 17, 2026, authors are not required to compare their own work to that paper."),
    ("Policy-ICLR2027", "policy_iclr27_reviewer", "policy", "ICLR 2027 Reviewer Guide, FAQ", "contemporaneity", "arXiv is not considered",
     "Note that arXiv is not considered a peer-reviewed venue."),
    ("Policy-ICLR2025", "policy_iclr25_faq", "policy", "ICLR 2025 FAQ", "contemporaneity", "contemporaneous",
     "We consider papers contemporaneous if they are published within the last four months."),
    ("Venue-ICML2025-IFG", "venue_icml25_ifg", "2506.09659", "icml.cc/virtual/2025/51482 page header", "corrections", "Poster in Workshop",
     "Poster in Workshop: Exploration in AI Today (EXAIT)"),
    ("Venue-ICML2026-Manifold", "venue_icml26_manifold", "2605.05115", "icml.cc/virtual/2026/79460 page header", "corrections", "Spotlight in Workshop",
     "Spotlight in Workshop: Workshop on Mechanistic Interpretability"),
    ("Venue-ICML2026-Lottery", "venue_icml26_lottery", "2606.04057", "icml.cc/virtual/2026/poster/64782 page header", "corrections", "HALL A",
     "The Invisible Lottery: How Subtle Cues Steer Algorithm Choice in LLM Code Generation"),
    ("Venue-NeurIPS2026-Kotawala", "venue_neurips26_injection", "kotawala", "neurips.cc/virtual/2026/168286 page header", "b7", "Poster in Workshop",
     "Poster in Workshop: The Third Workshop on Agents in the Wild: Safety, Security, and Beyond"),
]

URL_OVERRIDE = {"funsearch_nature": "https://www.nature.com/articles/s41586-023-06924-6"}


def auto_section(raw: str, quote: str) -> str:
    """Nearest preceding heading in the raw (newline-preserving) text, for a cross-check of the manual locator."""
    words = [w for w in re.split(r"\s+", quote.replace("[...]", " ").strip()) if w][:5]
    if not words:
        return ""
    rx = r"[\s*_]+".join(re.escape(w.strip("*_")) for w in words)
    m = re.search(rx, raw)
    if not m:
        return ""
    head = ""
    for hm in re.finditer(r"^(#{1,6}\s+.+|\d+(?:\.\d+)*\.?\s+[A-Z][^\n]{2,80})$", raw[:m.start()], re.M):
        head = hm.group(1)
    return head.strip("# ").strip()[:90]


def main():
    out = EVID / "quotes.jsonl"
    out.write_text("")
    n_ok = 0
    for ref, ckey, aid, section, used, rx, quote in Q:
        raw = load_text(ckey)
        ok = quote_matches(quote, normalise(raw))
        base = aid if aid in META else None
        m = META.get(aid, {})
        ver_q = re.search(r"v\d+$", ckey).group(0) if re.search(r"\d{4}\.\d{4,5}v\d+$", ckey) else ""
        latest = m.get("latest_version") or EXTRA_LATEST.get(aid, "")
        title = m.get("title") or EXTRA_TITLES.get(aid, ("", None))[0] or OR_TITLES.get(aid, "")
        first_author = (m.get("authors") or [EXTRA_TITLES.get(aid, ("", None))[1]])[0]
        url = URL_OVERRIDE.get(ckey) or INDEX.get(ckey, {}).get("url") or f"https://arxiv.org/html/{ckey}"
        venue, vev = VENUE.get(aid, ("", ""))
        abstract_only = ckey.startswith(("venue_", "or_"))
        status = ("VERIFIED-ABSTRACT" if abstract_only and aid != "policy" else "VERIFIED") if ok else "MISMATCH"
        if ckey.startswith(("venue_", "policy_")) and ok and "page header" in section:
            status = "VERIFIED"
        rec = {"ref_key": ref, "arxiv_id": base or (aid if re.match(r"\d{4}\.\d{4,5}$", aid) else None),
               "version_quoted": ver_q or None, "latest_version_seen": latest or None, "title_as_printed": title or None,
               "first_author": first_author, "venue_status": venue, "venue_evidence": vev, "url": url,
               "section_or_page": section, "auto_section": auto_section(raw, quote), "quote": quote, "regex_used": rx,
               "retrieved_utc": RETRIEVED, "status": status, "used_in": used,
               "source_type": "PDF" if INDEX.get(ckey, {}).get("is_pdf") else "HTML"}
        with out.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        n_ok += ok
        if not ok:
            print(f"MISMATCH: {ref} [{ckey}] :: {quote[:90]}")
    print(f"{n_ok}/{len(Q)} quotes matched after normalisation")


if __name__ == "__main__":
    main()
