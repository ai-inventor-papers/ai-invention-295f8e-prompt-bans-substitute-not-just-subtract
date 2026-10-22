"""Step 5: render research_report.md (with paste-ready Table 92e) and cache/sources_iter6.json from the evidence files.

Inputs: evidence/quotes_iter6.jsonl (verified quotes), evidence/scored_hits_iter6.jsonl, evidence/flags_iter6.json,
evidence/saturation_counts_iter6.json, evidence/rescreen_kappa_iter6.json, evidence/corrections_iter6.jsonl,
evidence/qa_second_pass_iter6.jsonl. Citation numbers [n] index the SOURCES list below (same order in research_out.json).
Usage: python -I tools/render_report_iter6.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, EVID, WS  # noqa: E402

Q = [json.loads(l) for l in (EVID / "quotes_iter6.jsonl").read_text().splitlines()]
QROW = {q["row"]: q for q in Q if q["row"] != "venue"}
COUNTS = json.loads((EVID / "saturation_counts_iter6.json").read_text())
KAPPA = json.loads((EVID / "rescreen_kappa_iter6.json").read_text())
QA = [json.loads(l) for l in (EVID / "qa_second_pass_iter6.jsonl").read_text().splitlines()]
CORR = [json.loads(l) for l in (EVID / "corrections_iter6.jsonl").read_text().splitlines()]
META = json.loads((EVID / "arxiv_meta.json").read_text())
OR = "https://api2.openreview.net/notes/search?term="


def au(aid):
    m = META.get(aid)
    return m["authors"] if m else None


# key, url, title, authors, year, summary, quote rows used as supporting passages
SOURCES = [
    ("SUC", "https://arxiv.org/html/2609.06473v1", "Steering Under Compression: Dose-Response, Capability Cost, and Failure Asymmetry in Quantized LLMs (arXiv 2609.06473v1)", au("2609.06473"), 2026,
     "Nearest FLAG E neighbour: CAA steering under bitsandbytes WEIGHT-ONLY INT8/NF4 on four 7-9B models; activations kept FP16/BF16; vectors recomputed per scheme stay collinear (cosine 0.989-0.998 INT8, 0.945-0.990 NF4); activation quantisation excluded by design.", ["92e-Ea", "92e-Ec"]),
    ("STABLE", OR + "Stable%20Directions%2C%20Different%20Effects%3A%20Intervention%20Fidelity%20Across%20Model%20Precision&group=ICLR.cc/2027/Conference&limit=10",
     "Stable Directions, Different Effects: Intervention Fidelity Across Model Precision (ICLR 2027 desk-rejected submission, OpenReview 8iTqrW1sxY; API record)", None, 2026,
     "Abstract-level (PDF HTTP 403): the effect of a steering intervention transferred to a quantized version can change while directions stay aligned; precision factor not stated; keywords 'model quantization', 'cross-precision transfer'.", ["92e-Ef"]),
    ("LOWBIT", OR + "Activation%20Steering%20under%20Low-Bit%20Quantization%3A%20A%20Geometric%20Perspective%20on%20Degradation%20and%20Recovery&group=ICLR.cc/2027/Conference&limit=10",
     "Activation Steering under Low-Bit Quantization: A Geometric Perspective on Degradation and Recovery (ICLR 2027 submission, OpenReview h57duZqLOr; API record)", None, 2026,
     "Abstract-level: same intervention layer/direction/strength across full-precision and quantized models; output fidelity does not guarantee preserved responses to the intervention; quantisation scheme not stated.", ["92e-Eg"]),
    ("PAHQ", "https://arxiv.org/html/2510.23264v1", "PAHQ: Accelerating Automated Circuit Discovery through Mixed-Precision Inference Optimization (arXiv 2510.23264v1)", au("2510.23264"), 2025,
     "8-bit RTN quantisation of ALL weights and activations (FP32 baseline) collapses ACDC activation-patching circuit discovery (IOI/Greater-Than/Docstring, GPT-2-scale) via underflow and mantissa loss; the closest full-text FLAG E candidate (joint W+A, internal outcome).", ["92e-Ei", "92e-Ej"]),
    ("F32", "https://api.semanticscholar.org/graph/v1/paper/DOI:10.3390/computation14090212?fields=title,abstract,venue,publicationDate,authors,externalIds",
     "Float32-Induced Distortion in Activation Patching: Precision Floors and Displacement-Dependent Endpoint-Curvature Error (Computation 2026; Semantic Scholar API record)", ["Yash Baligar"], 2026,
     "fp32 vs fp64 numerics push many interaction-level patching estimates below a precision floor (GPT-2-medium, Pythia-410M); numerics, not activation quantisation.", ["92e-El"]),
    ("SPECTRA", OR + "Quantization-Induced%20Decision%20Changes%20Have%20Regime-Dependent%20Intervention%20Spectra&group=ICLR.cc/2027/Conference&limit=10",
     "Quantization-Induced Decision Changes Have Regime-Dependent Intervention Spectra (ICLR 2027 submission, OpenReview 6t1egKiB0v)", None, 2026,
     "Activation additions on quantized residual states used to restore full-precision predictions (repair use of interventions).", []),
    ("QHELPS", OR + "When%20Quantization%20Helps%3A%20Corrective%20Computation%20in%20Low-Bit%20Language%20Models&group=ICLR.cc/2027/Conference&limit=10",
     "When Quantization Helps: Corrective Computation in Low-Bit Language Models (ICLR 2027 submission, OpenReview GYm4mg9yGQ)", None, 2026,
     "Weight-only GPTQ/AWQ/NF4; activation patching analyses quantisation-induced corrections.", []),
    ("PRISM", "https://arxiv.org/html/2610.20808v1", "PRISM: Transfer and Limits of Activation Interventions in Tool-Calling Language Models (arXiv 2610.20808v1)", au("2610.20808"), 2026,
     "Directions estimated with labels from NF4 copies act on BF16 models; weight-only precision transfer of interventions.", ["92e-Eo"]),
    ("NONSURJ", "https://arxiv.org/html/2604.09839v2", "Steered LLM Activations are Non-Surjective (arXiv 2604.09839v2)", au("2604.09839"), 2026,
     "Inherited 92b-b7c/92c-C2-geod; new finding quoted: its empirical claims hold on an INT4 model.", ["92e-Eq"]),
    ("KVCOL", "https://arxiv.org/pdf/2606.09864v2", "Alignment Collapse Under KV Cache Quantization: Diagnosis and Mitigation (arXiv 2606.09864v2)", au("2606.09864"), 2026,
     "Activation-side KV-cache quantisation silently removes refusals at ~flat perplexity; outlier-driven scale factors crush safety channels; no activation-level intervention.", ["92e-Es"]),
    ("LIQ", "https://aclanthology.org/2026.propor-1.108/", "Lost in Quantization: Activation Outliers Explain Language-Specific FP8 Sensitivity in Llama-3 (PROPOR 2026, ACL Anthology 2026.propor-1.108)", None, 2026,
     "Naive unscaled E4M3 casting vs INT8 with outlier handling on Meta-Llama-3-8B; English +18% vs PT-BR +3.9% perplexity; no interventions; not per-token-scaled W8A8.", ["92e-Et", "92e-Eu"]),
    ("FP32", "https://arxiv.org/html/2506.09501v2", "Understanding and Mitigating Numerical Sources of Nondeterminism in LLM Inference (v1 title 'Give Me FP32 or Give Me Death?'; arXiv 2506.09501v2)", au("2506.09501"), 2025,
     "BF16 numerics plus batch size/GPU count change accuracy by up to 9% and length by 9,000 tokens under greedy decoding; LayerCast.", ["92e-Ev"]),
    ("FP32VENUE", "https://neurips.cc/virtual/2025/oral/118170", "NeurIPS 2025 oral page: Understanding and Mitigating Numerical Sources of Nondeterminism in LLM Inference", None, 2025,
     "Venue confirmation (oral) for [12].", []),
    ("TMBLOG", "https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/", "Defeating Nondeterminism in LLM Inference (Thinking Machines Lab blog, Sep 10, 2025)", ["Horace He"], 2025,
     "Batch-invariance account of inference nondeterminism; 80 unique completions from 1000 temperature-0 samples of a Qwen3 model.", ["92e-Ew"]),
    ("ALIBI", "https://arxiv.org/html/2608.13756v2", "The Integer Alibi: Localizing Cross-Kernel Divergence in INT8-Quantized LLM Inference (arXiv 2608.13756v2)", au("2608.13756"), 2026,
     "Swapping only the INT8 W8A8 GEMM kernel (CUTLASS vs Triton) in vLLM on Qwen3-1.7B/8B changes every sequence (0/8, 0/16, 0/64 agree); FP8 GEMM differences grow with reduction depth.", ["92e-Ey"]),
    ("SAMEREQ", "https://arxiv.org/html/2609.04748v2", "Same Request, Different Answer: Quantization Amplifies Cache-Induced Divergence in LLM Serving (arXiv 2609.04748v2)", au("2609.04748"), 2026,
     "Quantised execution path (not rounded weights) amplifies cache-induced divergence; top-two margins; weights-through-16-bit-kernels control.", ["92e-Ez", "92e-Fl"]),
    ("GREEDY", "https://arxiv.org/pdf/2609.26621v1", "Greedy Decoding Is Not Precision-Invariant: Cross-Precision Output Divergence in LLM Inference (TMLR 2026; arXiv 2609.26621v1)", au("2609.26621"), 2026,
     "BF16 vs FP16 change greedy outputs on 49-100% of prompts; outcome governed by the top-two logit margin at the lm_head; end-to-end FP8 divergence is body-dominated.", ["92e-Fj"]),
    ("DUTTA", "https://arxiv.org/html/2407.09141v1", "Accuracy is Not All You Need (NeurIPS 2024; arXiv 2407.09141v1)", au("2407.09141"), 2024,
     "Compressed models flip answers at matched accuracy: deployment analogue of 'same default, different behaviour'.", ["92e-Eab"]),
    ("KURTIC", "https://arxiv.org/html/2411.02355v4", "'Give Me BF16 or Give Me Death'? Accuracy-Performance Trade-Offs in LLM Quantization (ACL 2025; arXiv 2411.02355v4)", au("2411.02355"), 2024,
     "Over 500,000 evaluations on Llama-3.1: FP8 W8A8 with dynamic per-token activation scales is accuracy-lossless (premise of 'same default accuracy').", ["92e-Eam"]),
    ("OSTERMANN", "https://arxiv.org/html/2604.14090v1", "From Weights to Activations: Is Steering the Next Frontier of Adaptation? (ACL 2026; arXiv 2604.14090v1)", au("2604.14090"), 2026,
     "Position paper: steering as a form of model adaptation; no precision factor (screened, irrelevant to FLAG E).", []),
    ("SQ", "https://arxiv.org/html/2211.10438v7", "SmoothQuant: Accurate and Efficient Post-Training Quantization for Large Language Models (ICML 2023; arXiv 2211.10438v7)", au("2211.10438"), 2022,
     "W8A8 mechanism anchor: activations are hard to quantise because of outliers; per-token activation scales.", ["92e-Eac"]),
    ("INT8", "https://arxiv.org/html/2208.07339v2", "LLM.int8(): 8-bit Matrix Multiplication for Transformers at Scale (NeurIPS 2022; arXiv 2208.07339v2)", au("2208.07339"), 2022,
     "Emergent outlier features from 6.7B parameters ruin quantisation precision.", ["92e-Ead"]),
    ("MASSIVE", "https://arxiv.org/html/2402.17762v2", "Massive Activations in Large Language Models (COLM 2024; arXiv 2402.17762v2)", au("2402.17762"), 2024,
     "Massive activations sit at the starting and delimiter tokens and act as bias terms: position-specific spikes set per-token scales.", ["92e-Eae"]),
    ("FP8FMT", "https://arxiv.org/html/2209.05433v2", "FP8 Formats for Deep Learning (arXiv 2209.05433v2)", au("2209.05433"), 2022, "Definition of E4M3/E5M2.", ["92e-Eag"]),
    ("HONG", "https://arxiv.org/html/2403.15447v3", "Decoding Compressed Trust: Scrutinizing the Trustworthiness of Efficient LLMs Under Compression (ICML 2024; arXiv 2403.15447v3)", au("2403.15447"), 2024,
     "4-bit weight quantisation retains trustworthiness while pruning degrades it.", ["92e-Eah"]),
    ("QWENCARD", "https://huggingface.co/Qwen/Qwen3-8B-FP8", "Qwen/Qwen3-8B-FP8 model card (Hugging Face)", None, None,
     "Documents the released FP8 checkpoint: fine-grained fp8 quantisation with block size 128 (methods row only).", ["92e-Eai"]),
    ("VLLM", "https://docs.vllm.ai/en/stable/features/quantization/llm_compressor/fp8/", "vLLM documentation: FP8 W8A8 (llm-compressor FP8_DYNAMIC)", None, None,
     "Documents W8A8 FP8_DYNAMIC: static per-channel weight scales, dynamic per-token activation scales (methods row only).", ["92e-Eaj"]),
    ("SHARP", "https://neurips.cc/virtual/2026/poster/151909", "The Sharp Directions Are Against You: Curvature Analysis of Activation Steering (NeurIPS 2026 poster page)",
     ["Seyedarmin Azizi", "Arya Fayyazi", "Parsa Razmara", "Erfan Baghaei Potraghloo", "Souvik Kundu", "Massoud Pedram"], 2026,
     "Steering curvature: tiny perturbations along sharp directions cause large input-dependent behaviour swings (a mechanism by which small numeric perturbations of a nudge could matter).", ["92e-Eak"]),
    ("GLM", "https://arxiv.org/abs/2609.09793", "How Fragile Is Safety Alignment at Frontier Scale? A Single-Direction Attack on a 320B MoE (arXiv 2609.09793)", None, 2026,
     "Directional ablation on a block-FP8 320B MoE checkpoint; no precision contrast.", ["92e-Eal"]),
    ("SBC", "https://arxiv.org/html/2603.22446v1", "Sparse but Critical: A Token-Level Analysis of Distributional Shifts in RLVR Fine-Tuning of LLMs (ICLR 2026; arXiv 2603.22446v1)", au("2603.22446"), 2026,
     "At high-divergence positions ~30% of RL top-1 tokens are base top-1 and >80% (DAPO) / >90% (SimpleRL) are in the base top-3; cross-sampling with base tokens collapses RL gains.", ["92e-L1a", "92e-L1c"]),
    ("REM", "https://arxiv.org/html/2507.03662v1", "Re-Emergent Misalignment: How Narrow Fine-Tuning Erodes Safety Alignment in LLMs (arXiv 2507.03662v1)", au("2507.03662"), 2025,
     "FLAG L partly: fine-tune-perturbed instruct model produces outputs the base model also rates likely while the instruct model suppresses them (retrospective, sequence likelihoods, 400 examples per dataset).", ["92e-L1d", "92e-L1e"]),
    ("RESIST", "https://arxiv.org/html/2406.06144v6", "Language Models Resist Alignment: Evidence From Data Compression (ACL 2025; arXiv 2406.06144v6)", au("2406.06144"), 2024,
     "Elasticity/rebound: reverse fine-tuning returns post-trained models quickly to the pre-training distribution.", ["92e-L1g"]),
    ("ADYN", "https://arxiv.org/html/2605.18309v1", "Alignment Dynamics in LLM Fine-Tuning (arXiv 2605.18309v1)", au("2605.18309"), 2026,
     "Rebound effect as a driving-vs-rebound force competition.", ["92e-L1h"]),
    ("GRAV", "https://arxiv.org/html/2606.28525v2", "A Gravitational Interpretation of Safety Reversion under Fine-Tuning (arXiv 2606.28525v2)", au("2606.28525"), 2026,
     "Prospective, pre-fixed direction toward base-descended helpful-only states; benign fine-tuning moves along it more than a matched null.", ["92e-L1i", "92e-L1j"]),
    ("W2S", "https://arxiv.org/html/2401.17256v5", "Weak-to-Strong Jailbreaking on Large Language Models (ICML 2025; arXiv 2401.17256v5)", au("2401.17256"), 2024,
     "Rival-supporting: jailbroken models' top tokens lie within the safe (tuned) model's own top ten.", ["92e-L1k"]),
    ("PERSONA", "https://arxiv.org/html/2607.21356v1", "Emergent Misalignment Recruits a Pre-existing Persona Subspace (arXiv 2607.21356v1)", au("2607.21356"), 2026,
     "Rival-supporting: a subspace extracted from the frozen instruction-tuned model carries where fine-tuning lands.", ["92e-L1l", "92e-L1m"]),
    ("EMNM", "https://arxiv.org/html/2608.29118v1", "Emergent Misalignment Is Not Magical (arXiv 2608.29118v1)", au("2608.29118"), 2026,
     "Per-prompt forecast of EM from the pre-EM model's representations; its 'base model' is the pre-fine-tune INSTRUCT model.", ["92e-L1n", "92e-L1o"]),
    ("PREDMI", OR + "Predictive%20Mechanistic%20Interpretability%20of%20Post-Training%3A%20A%20Priori%20Forecasts%20of%20Circuit%20Localization%20and%20Sign%20from%20the%20Base%20Model&group=ICLR.cc/2027/Conference&limit=10",
     "Predictive Mechanistic Interpretability of Post-Training: A Priori Forecasts of Circuit Localization and Sign from the Base Model (ICLR 2027 submission, OpenReview BEcwcRFQdu)", None, 2026,
     "Sealed, pre-registered per-head forecasts from the base model of how post-training changes circuits (method overlap for committed forecasts).", ["92e-L1p"]),
    ("ED", "https://arxiv.org/html/2402.12343v4", "Emulated Disalignment: Safety Alignment for Large Language Models May Backfire! (ACL 2024; arXiv 2402.12343v4)", au("2402.12343"), 2024,
     "Contrasting aligned vs pre-trained token distributions pushes the aligned model toward harm (logit-level base/aligned knob).", ["92e-L1q"]),
    ("BARRIER", "https://arxiv.org/html/2603.06957v2", "Post-Training with Policy Gradients: Optimality and the Base Model Barrier (ICML 2026; arXiv 2603.06957v2)", au("2603.06957"), 2026,
     "Theory: going beyond the base model's support is exponentially costly for outcome-reward policy gradient (supports L2).", ["92e-L2a"]),
    ("RWS", "https://arxiv.org/html/2510.14901v1", "Reasoning with Sampling: Your Base Model is Smarter Than You Think (arXiv 2510.14901v1)", au("2510.14901"), 2025,
     "Power distribution p^alpha of the base model matches GRPO in-domain and beats it out of domain (supports L3's power account).", ["92e-L3a", "92e-L3b"]),
    ("EMBPERT", "https://arxiv.org/html/2602.02427v4", "Uncertainty Localization in LLM Reasoning via Embedding Perturbations (arXiv 2602.02427v4)", au("2602.02427"), 2026,
     "Content-free Gaussian perturbation of token embeddings localises uncertain reasoning steps; continuations stay coherent (no site comparison at matched dose).", ["92e-Sa", "92e-Sb"]),
    ("FORKSROAD", "https://arxiv.org/html/2605.17026v2", "Why Do Reasoning Models Lose Coverage? The Role of Data and Forks in the Road (arXiv 2605.17026v2)", au("2605.17026"), 2026,
     "Reasoning-mode forks (natural language vs code) are driven by weak signals; targeted prefix perturbation beats temperature scaling for coverage.", ["92e-Sc", "92e-Sd"]),
    ("FORKING", "https://arxiv.org/html/2412.07961v1", "Forking Paths in Neural Text Generation (ICLR 2025; arXiv 2412.07961v1)", au("2412.07961"), 2024,
     "Forking tokens found by resampling, including punctuation.", ["92e-Fa", "92e-Fb"]),
    ("FORKINGVENUE", "https://iclr.cc/virtual/2025/poster/30769", "ICLR 2025 poster page: Forking Paths in Neural Text Generation", None, 2025, "Venue confirmation for [42].", []),
    ("FORKFAST", "https://arxiv.org/html/2608.19611v1", "Forking Fast: Efficiently Estimating Uncertainty Dynamics in Text Generation (arXiv 2608.19611v1)", au("2608.19611"), 2026,
     "Change-point detection of forking points from low-sample resampling.", ["92e-Fc"]),
    ("ANCHORS", "https://arxiv.org/html/2506.19143v4", "Thought Anchors: Which LLM Reasoning Steps Matter? (arXiv 2506.19143v4)", au("2506.19143"), 2025,
     "Sentence-level resampling importance: planning and uncertainty-management sentences anchor reasoning.", ["92e-Fd"]),
    ("LOCKED", "https://arxiv.org/html/2608.29188v1", "Locked at the Entrance, Open Inside: Where RLVR Narrows the Solution Space (arXiv 2608.29188v1)", au("2608.29188"), 2026,
     "Entrance families (first operand and operator) in Countdown; RLVR contraction concentrated at the entrance; layer interpolation between RL checkpoints.", ["92e-Fe", "92e-Kd"]),
    ("CLIFF", "https://arxiv.org/html/2606.25524v3", "Cliff Tokens: Analyzing Failure Trigger Tokens in LLM Mathematical Reasoning (arXiv 2606.25524v3)", au("2606.25524"), 2026,
     "Rollout-defined failure-trigger tokens.", ["92e-Ff"]),
    ("HIGHENT", "https://arxiv.org/html/2506.01939v2", "Beyond the 80/20 Rule: High-Entropy Minority Tokens Drive Effective Reinforcement Learning for LLM Reasoning (NeurIPS 2025; arXiv 2506.01939v2)", au("2506.01939"), 2025,
     "High-entropy 'forking' tokens carry RLVR's effect.", ["92e-Fg"]),
    ("TOPN", "https://arxiv.org/html/2411.07641v1", "Top-nσ: Not All Logits Are You Need (arXiv 2411.07641v1; ACL 2025 as 'Top-nσ: Eliminating Noise in Logit Space for Robust Token Sampling of LLM')", au("2411.07641"), 2024,
     "Logits split into a noisy and an informative region; the candidate set is stable regardless of temperature.", []),
    ("TOPNVENUE", "https://aclanthology.org/2025.acl-long.528/", "ACL Anthology 2025.acl-long.528 (Top-nσ, ACL 2025)", None, 2025, "Venue/title confirmation for [49].", []),
    ("RENZE", "https://arxiv.org/html/2402.05201v3", "The Effect of Sampling Temperature on Problem Solving in Large Language Models (Findings of EMNLP 2024; arXiv 2402.05201v3)", au("2402.05201"), 2024,
     "Temperature 0.0-1.0 has no statistically significant effect on problem-solving accuracy.", ["92e-Fi"]),
    ("MARGINGATE", "https://arxiv.org/html/2605.30218v1", "MarginGate: Sparse Margin-Triggered Verification for Batch-Invariant LLM Inference (arXiv 2605.30218v1)", au("2605.30218"), 2026,
     "Low top-1/top-2 logit margins expose flip risk under batch numerics.", ["92e-Fk"]),
    ("WISE", "https://arxiv.org/html/2109.01903v3", "Robust fine-tuning of zero-shot models (WiSE-FT; CVPR 2022; arXiv 2109.01903v3)", au("2109.01903"), 2021,
     "Definition of weight-space interpolation with a mixing coefficient.", ["92e-Ka"]),
    ("ATAX", "https://arxiv.org/html/2309.06256v4", "Mitigating the Alignment Tax of RLHF (EMNLP 2024; arXiv 2309.06256v4)", au("2309.06256"), 2023,
     "Averaging pre- and post-RLHF weights gives the best alignment-forgetting Pareto front: direct base/aligned interpolation precedent.", ["92e-Kb"]),
    ("FAMILIAR", OR + "Should%20SFT%20Prefer%20the%20Familiar%3F%20Diversity%20Collapse%20and%20Recovery%20via%20Model%20Merging&group=ICLR.cc/2027/Conference&limit=10",
     "Should SFT Prefer the Familiar? Diversity Collapse and Recovery via Model Merging (ICLR 2027 submission, OpenReview MYXgOex05m)", None, 2026,
     "Merging the fine-tuned model with its pretrained base restores diversity across math and code benchmarks (closest K neighbour).", ["92e-Kc"]),
    ("EFTVENUE", "https://proceedings.iclr.cc/paper_files/paper/2024/hash/389e161125965c0f0ba50420fee45774-Abstract-Conference.html", "ICLR 2024 proceedings page: An Emulator for Fine-tuning Large Language Models using Small Language Models", None, 2024,
     "Venue confirmation for EFT [85].", []),
    ("URIALVENUE", "https://iclr.cc/virtual/2024/poster/17473", "ICLR 2024 poster page: The Unlocking Spell on Base LLMs", None, 2024, "Venue confirmation for URIAL [58].", []),
    # ---- inherited (cited by row id; not re-verified) ----
    ("URIAL", "https://arxiv.org/html/2312.01552v1", "The Unlocking Spell on Base LLMs: Rethinking Alignment via In-Context Learning (URIAL; arXiv 2312.01552v1)", au("2312.01552"), 2023,
     "Inherited 92d-A2b: aligned top tokens mostly within the base top five (token level, no perturbation).", []),
    ("SAMECAND", OR + "Same%20Candidates%2C%20Stronger%20Reasoning%3A%20Rethinking%20What%20Post-Training%20Learns&group=ICLR.cc/2027/Conference&limit=10",
     "Same Candidates, Stronger Reasoning: Rethinking What Post-Training Learns (ICLR 2027 submission, OpenReview ooV5M72O08)", None, 2026,
     "Inherited 92d-A2c (VERIFIED-ABSTRACT): 92.9% of post-training top-1 changes stay within the pretrained top-16.", []),
    ("VS", "https://arxiv.org/html/2510.01171v4", "Verbalized Sampling: How to Mitigate Mode Collapse and Unlock LLM Diversity (arXiv 2510.01171v4)", None, 2025,
     "Inherited 92d-A2a: App. D.3 power-transform sharpening under typicality bias (stylised).", []),
    ("MOHAMMADI", "https://arxiv.org/pdf/2406.05587v1", "Creativity Has Left the Chat: The Price of Debiasing Language Models (arXiv 2406.05587v1)", None, 2024,
     "Inherited 92d-A1h: a perturbed aligned model returns to its OWN attractor (rival-supporting).", []),
    ("SAMANTA", "https://arxiv.org/html/2606.29933v1", "Samanta et al. 2026 (behaviour crystallization; arXiv 2606.29933v1)", None, 2026,
     "Inherited 92d-A2d: SFT collapses behaviour onto a seed distribution present in the pretrained model.", []),
    ("ZHOUT", "https://arxiv.org/html/2607.20543v1", "Zhou (T.) 2026 (training-time per-prompt forecasts from the base; arXiv 2607.20543v1)", None, 2026, "Inherited 92d-A1a/b.", []),
    ("DUAN", "https://arxiv.org/html/2610.04978v1", "Duan 2026 (per-problem forecasts; arXiv 2610.04978v1)", None, 2026, "Inherited 92d-A1c/d.", []),
    ("LEE", "https://arxiv.org/html/2503.00691v2", "How Diversely Can Language Models Solve Problems? (Lee et al., Findings of EMNLP 2025; arXiv 2503.00691v2)", None, 2025,
     "Inherited 92d-A0a-c: base vs instruct algorithmic diversity is mixed in direction.", []),
    ("BFT", "https://openreview.net/forum?id=knirOusGcq", "Before the First Token: A Shared Causal Subspace for Response-Length Planning in LLMs (ICLR 2027 submission, OpenReview knirOusGcq)", None, 2026,
     "Inherited 92c-C2aa/C2ab: causal pre-generation plan subspace (abstract-level).", []),
    ("NOISESTEER", "https://arxiv.org/pdf/2604.03380v2", "Khalid et al. 2026 (activation noise steering; BEA workshop @ ACL 2026; arXiv 2604.03380v2)", None, 2026,
     "Inherited 92c-C1-sited / 92b-b6a: site comparison (embedding/attention) for noise-based diversity.", []),
    ("STARS", "https://arxiv.org/html/2601.22010v1", "Zhu et al. 2026 (STARS; ICLR 2026; arXiv 2601.22010v1)", None, 2026,
     "Inherited 92c-C1-sitee / 92b-b6b: intra-layer site comparison for test-coverage diversity (App. B.3).", []),
    ("WHEREINJECT", "https://arxiv.org/html/2606.10302v1", "Where You Inject Diversity Matters: A Unified Framework (arXiv 2606.10302v1)", None, 2026,
     "Inherited 92c-C1-sitea..c / 92d-Ci: text-level injection-site framework.", []),
    ("JERGE", "https://arxiv.org/html/2608.21595v1", "Jerge et al. 2026 (prompt-state noise vs temperature; arXiv 2608.21595v1)", None, 2026, "Inherited 92c-C1-sitef.", []),
    ("NAGARAJAN", "https://arxiv.org/html/2504.15266v4", "Nagarajan et al. 2025 (input-layer vs output-layer randomness; ICML 2025; arXiv 2504.15266v4)", None, 2025, "Inherited 92c-C1-siteg.", []),
    ("REI", "https://arxiv.org/html/2605.11936v2", "From Noise to Diversity: Random Embedding Injection in LLM Reasoning (arXiv 2605.11936v2)", None, 2026,
     "Inherited 92b-b6c: random embedding injection widens Pass@N on math; code left to future work.", []),
    ("ADAPT", "https://arxiv.org/html/2309.02772v3", "Hot or Cold? Adaptive Temperature Sampling for Code Generation (AdapT; AAAI 2024; arXiv 2309.02772v3)", None, 2023, "Inherited 92b-b3b.", []),
    ("DONG", "https://arxiv.org/html/2502.06258v3", "Emergent Response Planning in LLMs (ICML 2025; arXiv 2502.06258v3)", None, 2025, "Inherited 92c-C2ac.", []),
    ("WHEREPLAN", "https://arxiv.org/html/2605.07984v2", "Where's the Plan? Locating Latent Planning in Language Models (ICML 2026 MI workshop; arXiv 2605.07984v2)", None, 2026, "Inherited 92c-C2ad.", []),
    ("BREWING", "https://arxiv.org/html/2606.17648v3", "From Brewing to Resolution: Tracing the Internal Lifecycle of Code Reasoning in LLMs (arXiv 2606.17648v3)", None, 2026, "Inherited 92c-C2ah.", []),
    ("BACO", "https://arxiv.org/html/2511.05650v2", "Base-Aligned Model Collaboration (BACo; ICML 2026; arXiv 2511.05650v2)", None, 2025, "Inherited 92d-B1i/92d-Ca.", []),
    ("CONFORM", "https://arxiv.org/html/2507.20956v1", "Conformative decoding (Peeperkorn et al.; arXiv 2507.20956v1)", None, 2025, "Inherited 92d-Cb.", []),
    ("SWITCH", "https://arxiv.org/html/2510.09913v1", "Switch Generation (Feng et al.; arXiv 2510.09913v1)", None, 2025, "Inherited 92d-Cc.", []),
    ("SLR", "https://arxiv.org/html/2602.06665v1", "Selective Layer Restoration (Zhang et al.; arXiv 2602.06665v1)", None, 2026, "Inherited 92d-B1f/92d-Eb.", []),
    ("FRANKEN", "https://arxiv.org/html/2610.22999v1", "Controlling the Diversity-Quality Trade-Off of LLMs by Merging Models Before and After Alignment (Sumita et al.; arXiv 2610.22999v1)", None, 2026,
     "Inherited 92d-B1g/92d-Ce.", []),
    ("DANG", "https://arxiv.org/html/2504.10478v4", "Weight ensembling improves reasoning in language models (Dang et al.; COLM 2025; arXiv 2504.10478v4)", None, 2025, "Inherited 92d-Cf (WiSE-FT with an early SFT checkpoint).", []),
    ("HINDSIGHT", "https://proceedings.mlr.press/v286/veselovsky25a.html", "Hindsight Merging: Diverse Data Generation with Language Models (PMLR v286)", None, 2025,
     "Inherited 92d quotes: +20-50% pass@10 on a coding benchmark from checkpoint interpolation.", []),
    ("RLREPLACE", "https://arxiv.org/html/2610.24663v1", "Zhang et al. 2026 (sparse RL-token replacement; arXiv 2610.24663v1)", None, 2026, "Inherited 92d-Cd.", []),
    ("EFT", "https://arxiv.org/html/2310.12962v1", "An Emulator for Fine-Tuning Large Language Models using Small Language Models (EFT; ICLR 2024; arXiv 2310.12962v1)", au("2310.12962"), 2023,
     "Inherited 92d quote (B2/C).", []),
    ("PROXY", "https://arxiv.org/html/2401.08565v4", "Tuning Language Models by Proxy (COLM 2024 per arXiv comment; arXiv 2401.08565v4)", au("2401.08565"), 2024, "Inherited 92d quote (B2/C).", []),
    ("NUDGING", "https://arxiv.org/html/2410.09300v4", "Nudging: Inference-time Alignment of LLMs via Guided Decoding (ACL 2025; arXiv 2410.09300v4)", au("2410.09300"), 2024,
     "Inherited 92d quote (C/A2): base models are uncertain where alignment changes tokens.", []),
    ("YUE", "https://arxiv.org/html/2504.13837v5", "Does Reinforcement Learning Really Incentivize Reasoning Capacity in LLMs Beyond the Base Model? (NeurIPS 2025 oral; arXiv 2504.13837v5)", None, 2025,
     "Inherited 92d-A0 quotes.", []),
    ("LEASH", "https://arxiv.org/html/2507.14843v5", "The Invisible Leash: Why RLVR May or May Not Escape Its Origin (arXiv 2507.14843v5)", None, 2025, "Inherited 92d-A0 quotes (net support shrinkage).", []),
    ("FUNSEARCH", "https://www.nature.com/articles/s41586-023-06924-6", "Mathematical discoveries from program search with large language models (FunSearch; Nature 625, 2024)", None, 2024, "Inherited 92c-C3ca.", []),
    ("ALPHAEVOLVE", "https://arxiv.org/html/2506.13131v1", "AlphaEvolve (Novikov et al.; arXiv 2506.13131v1)", None, 2025, "Inherited 92c-C3cb.", []),
    ("ZHOUY", "https://arxiv.org/html/2605.07284v2", "Zhou (Y.) 2026 (cross-patching base states into a descendant; arXiv 2605.07284v2)", None, 2026, "Inherited 92d-B1a/b.", []),
    ("OOZEER", "https://arxiv.org/html/2503.04429v4", "Oozeer et al. 2025 (activation transfer between base and fine-tuned models; ICML 2025; arXiv 2503.04429v4)", None, 2025, "Inherited 92d-B1c.", []),
    ("QISHALLOW", "https://arxiv.org/html/2406.05946v1", "Safety Alignment Should Be Made More Than Just a Few Tokens Deep (Qi et al.; ICLR 2025; arXiv 2406.05946v1)", None, 2024, "Inherited 92b-b3a.", []),
    # ---- screened (abstract-level, not quoted) ----
    ("BF16CAST", "https://arxiv.org/abs/2610.07853", "Lost in the bf16 Cast: Exporting Ternary Language Models Can Revert Most Low-Learning-Rate Code Changes (arXiv 2610.07853)", None, 2026,
     "Screened (R2): bf16 export casting reverts fine-tuning changes (numerics context).", []),
    ("PRECUP", "https://arxiv.org/abs/2610.24346", "Measuring the Task Value of Precision Upgrades in Closed-Loop Agents (arXiv 2610.24346)", None, 2026,
     "Screened (R3): BF16 fallback actions in 4-bit-weight agents rescue and damage tasks in near-equal numbers.", []),
    ("FLATSCORE", "https://arxiv.org/abs/2607.27275", "Flat Score, Amplified Failures: How the Error Budget Masks Damage in Quantized LLM Agents (arXiv 2607.27275)", None, 2026,
     "Screened (R4): 4-bit weights look free on the score while amplifying existing failures.", []),
    ("DISPL", "https://arxiv.org/abs/2606.19558", "Displacement Is Not Direction: Evaluating Fidelity Metrics for Quantized LLM Deployment (arXiv 2606.19558)", None, 2026,
     "Screened (R4): KL fidelity metrics lose predictive power near baseline.", []),
    ("SAFEQ", "https://openreview.net/forum?id=70RbLmZVvW", "SafeQ: Safety Alignment Preserving Post-Training Quantization for Language Models (ICLR 2027 submission)", None, 2026,
     "Screened (R2): safety-preserving PTQ for W4A16 and W4A4 (activation quantisation included; no interventions).", []),
    ("QPOLICY", "https://openreview.net/forum?id=5R8LqE51Hr", "Better Fixed-State Fidelity Need Not Improve Closed-Loop Performance in Quantized Neural Policies (ICLR 2027 submission)", None, 2026,
     "Screened (R2): fidelity on fixed states does not predict closed-loop return of quantised policies.", []),
    ("ALIGNRADAR", "https://openreview.net/forum?id=xmDdTDx241", "AlignRadar: Forecasting Emergent-Misalignment Risk Before Fine-Tuning (ICLR 2027 submission)", None, 2026,
     "Screened (R1): dataset-level forecast of EM risk from the base model before SFT (FLAG-B type).", []),
    ("REBEL", "https://arxiv.org/html/2605.10781v1", "Rebellious Student: Reversing Teacher Signals for Reasoning Exploration with Self-Distilled RLVR (arXiv 2605.10781v1)", None, 2026,
     "Screened (R1): replicates the base/RL top-k overlap analysis at high-divergence positions.", []),
    ("QGATE", "https://openreview.net/forum?id=Al2c9FzOI7", "QGATE: Counterexample-Guided Precision Patching of Quantized LLMs with Fail-Closed Slice Reporting (ICLR 2027 submission)", None, 2026,
     "Screened (R1): repairs quantisation flips by precision patching of weight groups (no activation-level intervention).", []),
    ("GITHUB-QI", "https://github.com/AARONKANG04/quantization-interpretability", "AARONKANG04/quantization-interpretability (GitHub repository)", None, None,
     "E6 grey literature (not fetched): NVFP4/FP8 damage study with tuned lens and SAE features on bf16 vs low-bit activations; repositories never fire a flag.", []),
    ("ARXIVAPI", "https://export.arxiv.org/api/query", "arXiv API (id_list metadata and search_query)", None, None,
     "Versions, v1 dates, titles, comments/journal_ref (evidence/arxiv_meta.json) and engine E3 of the saturation search.", []),
    ("S2API", "https://api.semanticscholar.org/graph/v1/paper/search", "Semantic Scholar Graph API (/paper/search, /citations, /references)", None, None,
     "Engine E4 and forward/backward citation chasing (FC/BC).", []),
    ("ORAPI", "https://api2.openreview.net/notes/search", "OpenReview API v2 notes/search (ICLR.cc/2027/Conference)", None, None,
     "Engine E5 and the abstract records quoted as VERIFIED-ABSTRACT; notes?id= and PDFs returned HTTP 403 on 2026-10-21/22.", []),
]
IDX = {k: i + 1 for i, (k, *_rest) in enumerate(SOURCES)}


def c(*keys):
    return "[" + ", ".join(str(IDX[k]) for k in keys) + "]"


# Table 92e row specs: row -> (claim one-liner, neighbour label (with [n]), what this run adds)
CL = {
    "E": "E: is Qwen3-8B's plan-site sensitivity a property of its FP8 W8A8 engine (2x2 weight-by-activation factorial)?",
    "E-attribution": "E-attribution: activation vs weight precision; per-token absmax / FP8-scale readouts",
    "E-deployment": "E-deployment: activation quantisation changes nudgeability while default output and accuracy are unchanged",
    "L1a": "L1a: a content-free nudge or ban moves the tuned model onto its BASE model's runner-up algorithm, forecast in advance",
    "L1b": "L1b: the base forecast beats rivals built from the tuned model (likelihood ranking q_lik, sampled tail q_tail), incl. tail-empty events",
    "L2": "L2: the perturbed tuned distribution stays inside base support",
    "L3": "L3: the perturbed/tuned distribution is the base distribution raised to a power",
    "S-a": "S-a: prefill task-spec states by block band as the site of content-free nudges",
    "S-c": "S-c: condition vs generated tokens as sites",
    "F1": "F1: the first divergence (entrance fork) decides the algorithm",
    "F2": "F2: teacher-forced log-odds margin between algorithm openings bounds the temperature effect",
    "K": "K: test-checked algorithm-level prices of base intent, base/instruct interpolation, proxy tuning, enumerate-and-pick, plan noise",
}
ADD_E = ("2x2 W8A8/W8A16/W16A8/W16A16 factorial with identical hook code, per-position doses and CRN slots; content-free random "
         "nudges; categorical test-checked algorithm labels; per-token absmax/FP8-scale readouts")
ADD = {
    "92e-Ea": "the activation-side arms (W16A8, W8A8) this neighbour excludes by design; " + ADD_E,
    "92e-Eb": "an activation-precision factor at matched weights (W16A8 vs W16A16) on the same hooks",
    "92e-Ec": "a behavioural, categorical outcome at matched nudge (not vector cosine); direction is fixed (random nudges are not re-extracted per precision)",
    "92e-Ed": "the same nudge vector and CRN seed across precisions (no re-extraction)",
    "92e-Ee": "if its full text varies weights only: the activation factor; if it includes activations: replication with content-free nudges on code-algorithm choice",
    "92e-Ef": "a per-position dose and categorical-choice readout, and an attribution factorial",
    "92e-Eg": "per-token-scaled FP8 W8A8 production kernels vs weight-only arms; random (content-free) nudges, not a fixed steering vector",
    "92e-Eh": "the same, plus test-checked algorithm labels instead of response/KL fidelity",
    "92e-Ei": "weights and activations varied SEPARATELY; behavioural algorithm choice of an 8B instruct model instead of circuit-recovery AUC on GPT-2",
    "92e-Ej": "per-token-scaled FP8 (no fixed 2^-6 floor), so the underflow mechanism is tested rather than assumed; absmax/scale readouts",
    "92e-Ek": "measured per-position displacement after quantisation of the nudged state",
    "92e-El": "8-bit activation precision (not fp32/fp64) and a behavioural outcome",
    "92e-Em": "nudges as the object of study (does precision change what a nudge does), not as a repair of flips",
    "92e-En": "activation-side precision; content-free nudges",
    "92e-Eo": "the activation factor; the same intervention applied at both precisions",
    "92e-Ep": "same, with matched weights",
    "92e-Eq": "a behavioural test under activation quantisation",
    "92e-Er": "nudgeability (response to a fixed content-free nudge) rather than default behaviour; W8A8 matmul activations rather than KV cache",
    "92e-Es": "per-token absmax and FP8 scale readouts at the nudged positions (analogous mechanism, different site)",
    "92e-Et": "per-token-scaled FP8 W8A8 (dynamic scales), not unscaled casting; interventions",
    "92e-Eu": "the production recipe this stress test excludes",
    "92e-Ev": "numerics controls (batch size 1, fixed kernels) so that precision, not batching, explains any difference",
    "92e-Ew": "batch-invariant / fixed-batch execution as a control arm",
    "92e-Ex": "same",
    "92e-Ey": "kernel-swap control at fixed W8A8 config (reviewer baseline), to separate kernel numerics from quantisation",
    "92e-Ez": "the same separation (weights vs execution path) applied to nudge effects",
    "92e-Eaa": "end-to-end W8A8 vs weight-only arms with interventions",
    "92e-Eab": "flip-style audit of nudge responses at matched default accuracy",
    "92e-Eac": "readout of which activations carry outliers at nudged positions",
    "92e-Ead": "context only",
    "92e-Eae": "per-token scales at task-spec vs read positions (massive-activation tokens set the scale)",
    "92e-Eaf": "context only",
    "92e-Eag": "context only (E4M3 range 448)",
    "92e-Eah": "context only",
    "92e-Eai": "states which checkpoint/engine scheme the run used (block-128 fine-grained FP8 vs dynamic per-token)",
    "92e-Eaj": "same",
    "92e-Eak": "context: why small numeric perturbations of a nudge could matter",
    "92e-Eal": "a precision contrast",
    "92e-Eam": "the nudgeability half of the claim: a fixed content-free nudge's effect at this accuracy-lossless setting",
    "92e-L1a": "algorithm-level (test-checked) landing under a content-free perturbation, forecast before the outcome",
    "92e-L1b": "the run's landings are scored on all positions of the algorithm opening, not only high-divergence ones",
    "92e-L1c": "landing identity rather than accuracy recovery",
    "92e-L1d": "a prospective (sha256-committed) forecast, enumerated algorithm labels, and explicit q_lik/q_tail rivals",
    "92e-L1e": "same; content-free nudge instead of fine-tuning",
    "92e-L1f": "context (scale)",
    "92e-L1g": "identity-level forecast at the algorithm level vs a distribution/score-level rebound",
    "92e-L1h": "same",
    "92e-L1i": "the tuned model's own tail and likelihood as rivals; base composition (not a helpful-only proxy) as the predictor",
    "92e-L1j": "rival scored against the tuned model, not a geometric null",
    "92e-L1k": "this is the rival the run must beat: q_lik (teacher-forced ranking) and q_tail",
    "92e-L1l": "base vs tuned provenance of the landing structure is tested directly (base composition vs tuned ranking)",
    "92e-L1m": "same",
    "92e-L1n": "a forecast from the BASE model, scored against forecasts from the tuned model itself",
    "92e-L1o": "terminology guard for the paper ('base' = pretrained)",
    "92e-L1p": "a committed forecast of landing identity rather than circuit change",
    "92e-L1q": "context",
    "92e-L2a": "empirical support test at the algorithm level",
    "92e-L3a": "a fitted alpha compared with parametric rivals and the tuned tail",
    "92e-L3b": "same",
    "92e-Sa": "matched per-position dose across sites (prefill task-spec bands vs read position vs condition vs generated tokens), categorical outcome",
    "92e-Sb": "same",
    "92e-Sc": "content-free nudges at the fork, with matched dose",
    "92e-Sd": "plan-state noise and base intent priced against temperature on the same test-checked labels",
    "92e-Fa": "fork position for the algorithm opening read from the twin model's teacher-forced margin",
    "92e-Fb": "same",
    "92e-Fc": "context",
    "92e-Fd": "context",
    "92e-Fe": "the same entrance logic for code algorithms; margins rather than likelihood shifts",
    "92e-Ff": "context",
    "92e-Fg": "context",
    "92e-Fh": "an algorithm-opening margin that bounds the temperature effect on the categorical choice (application, not mechanism)",
    "92e-Fi": "the margin explanation of why temperature is inert on algorithm choice",
    "92e-Fj": "temperature rather than precision as the perturbation explained by the margin",
    "92e-Fk": "same",
    "92e-Fl": "same",
    "92e-Ka": "lambda 0.25/0.5 between Qwen3-8B Base and Instruct, priced on test-checked algorithm labels",
    "92e-Kb": "same, with a diversity outcome",
    "92e-Kc": "algorithm-level, test-checked labels and a full-simplex price hull against other knobs",
    "92e-Kd": "base/instruct (not checkpoint) interpolation",
    "92e-Ke": "venue only",
}
NEIGH = {
    "Bhandari2026-SteeringUnderCompression": "Bhandari & Wade, 2026, arXiv preprint " + c("SUC"),
    "Anon2026-StableDirections": "Anonymous, 2026, ICLR 2027 desk-rejected submission (abstract) " + c("STABLE"),
    "Anon2026-SteeringLowBit": "Anonymous, 2026, ICLR 2027 submission (abstract) " + c("LOWBIT"),
    "Wang2025-PAHQ": "Wang et al., 2025, arXiv preprint " + c("PAHQ"),
    "Baligar2026-Float32Patching": "Baligar, 2026, Computation (journal) " + c("F32"),
    "Anon2026-InterventionSpectra": "Anonymous, 2026, ICLR 2027 submission (abstract) " + c("SPECTRA"),
    "Anon2026-QuantHelps": "Anonymous, 2026, ICLR 2027 submission (abstract) " + c("QHELPS"),
    "Bonas2026-PRISM": "Bonás et al., 2026, arXiv preprint " + c("PRISM"),
    "Mishra2026-NonSurjective": "Mishra et al., 2026, ICLR 2026 workshops " + c("NONSURJ"),
    "Xu2026-KVCacheAlignmentCollapse": "Xu et al., 2026, arXiv preprint " + c("KVCOL"),
    "Silva2026-LostInQuantization": "Silva et al., 2026, PROPOR 2026 " + c("LIQ"),
    "Yuan2025-GiveMeFP32": "Yuan et al., 2025, NeurIPS 2025 oral " + c("FP32", "FP32VENUE"),
    "He2025-DefeatingNondeterminism": "He / Thinking Machines, 2025, blog " + c("TMBLOG"),
    "Chen2026-IntegerAlibi": "Chen, 2026, arXiv preprint " + c("ALIBI"),
    "Patodiya2026-SameRequestDifferentAnswer": "Patodiya, 2026, arXiv preprint " + c("SAMEREQ"),
    "Du2026-GreedyNotPrecisionInvariant": "Du et al., 2026, TMLR " + c("GREEDY"),
    "Dutta2024-AccuracyNotAllYouNeed": "Dutta et al., 2024, NeurIPS 2024 " + c("DUTTA"),
    "Kurtic2025-GiveMeBF16": "Kurtic et al., 2024, ACL 2025 " + c("KURTIC"),
    "Xiao2023-SmoothQuant": "Xiao et al., 2022, ICML 2023 " + c("SQ"),
    "Dettmers2022-LLMint8": "Dettmers et al., 2022, NeurIPS 2022 " + c("INT8"),
    "Sun2024-MassiveActivations": "Sun et al., 2024, COLM 2024 " + c("MASSIVE"),
    "Micikevicius2022-FP8Formats": "Micikevicius et al., 2022, arXiv preprint " + c("FP8FMT"),
    "Hong2024-DecodingCompressedTrust": "Hong et al., 2024, ICML 2024 " + c("HONG"),
    "Qwen2025-Qwen3-8B-FP8-card": "Qwen team, model card " + c("QWENCARD"),
    "vLLM-FP8-W8A8-docs": "vLLM docs " + c("VLLM"),
    "Azizi2026-SharpDirections": "Azizi et al., 2026, NeurIPS 2026 poster " + c("SHARP"),
    "Anon2026-GLMDirectionalAblation": "2026, arXiv preprint (abstract) " + c("GLM"),
    "Meng2026-SparseButCritical": "Meng et al., 2026, ICLR 2026 " + c("SBC"),
    "Giordani2025-ReEmergentMisalignment": "Giordani, 2025, arXiv preprint " + c("REM"),
    "Ji2025-ResistAlignment": "Ji et al., 2024, ACL 2025 " + c("RESIST"),
    "Huang2026-AlignmentDynamics": "Huang et al., 2026, arXiv preprint " + c("ADYN"),
    "Poppi2026-GravitationalReversion": "Poppi & Lukas, 2026, arXiv preprint " + c("GRAV"),
    "Zhao2025-WeakToStrongJailbreak": "Zhao et al., 2024, ICML 2025 " + c("W2S"),
    "Nadaf2026-PersonaSubspace": "Nadaf, 2026, arXiv preprint " + c("PERSONA"),
    "Li2026-EMNotMagical": "Li et al., 2026, arXiv preprint " + c("EMNM"),
    "Anon2026-PredictiveMIPostTraining": "Anonymous, 2026, ICLR 2027 submission (abstract) " + c("PREDMI"),
    "Zhou2024-EmulatedDisalignment": "Zhou et al., 2024, ACL 2024 " + c("ED"),
    "MousaviHosseini2026-BaseModelBarrier": "Mousavi-Hosseini & Erdogdu, 2026, ICML 2026 " + c("BARRIER"),
    "Karan2025-ReasoningWithSampling": "Karan & Du, 2025, arXiv preprint " + c("RWS"),
    "Wen2026-EmbeddingPerturbationUncertainty": "Wen et al., 2026, arXiv preprint " + c("EMBPERT"),
    "Nguyen2026-ForksInTheRoad": "Nguyen et al., 2026, arXiv preprint " + c("FORKSROAD"),
    "Bigelow2025-ForkingPaths": "Bigelow et al., 2024, ICLR 2025 " + c("FORKING", "FORKINGVENUE"),
    "Bigelow2026-ForkingFast": "Bigelow et al., 2026, arXiv preprint " + c("FORKFAST"),
    "Bogdan2025-ThoughtAnchors": "Bogdan et al., 2025, arXiv preprint " + c("ANCHORS"),
    "Zhou2026-LockedAtEntrance": "Zhou & Li, 2026, arXiv preprint (+ ICLR 2027 submission) " + c("LOCKED"),
    "Ko2026-CliffTokens": "Ko et al., 2026, arXiv preprint " + c("CLIFF"),
    "Wang2025-HighEntropyMinority": "Wang et al., 2025, NeurIPS 2025 " + c("HIGHENT"),
    "Tang2025-TopNSigma": "Tang et al., 2024, ACL 2025 " + c("TOPN", "TOPNVENUE"),
    "Renze2024-TemperatureProblemSolving": "Renze & Guven, 2024, Findings of EMNLP 2024 " + c("RENZE"),
    "Chu2026-MarginGate": "Chu et al., 2026, arXiv preprint " + c("MARGINGATE"),
    "Wortsman2022-WiSEFT": "Wortsman et al., 2021, CVPR 2022 " + c("WISE"),
    "Lin2024-AlignmentTax": "Lin et al., 2023, EMNLP 2024 " + c("ATAX"),
    "Anon2026-SFTFamiliarMerging": "Anonymous, 2026, ICLR 2027 submission (abstract) " + c("FAMILIAR"),
    "Mitchell2024-EFT": "Mitchell et al., 2023, ICLR 2024 " + c("EFT", "EFTVENUE"),
}
INHERITED_ROWS = [  # row, claim, neighbour, pointer, url, relation, adds
    ("92e-L1r", "L1a", "Lin et al., 2023, ICLR 2024 " + c("URIAL", "URIALVENUE"), "see Table 92d row 92d-A2b (not re-verified)", "https://arxiv.org/html/2312.01552v1", "adjacent (token level, no perturbation)", "algorithm-level landing under perturbation"),
    ("92e-L1s", "L1a", "Anonymous, 2026, ICLR 2027 submission " + c("SAMECAND"), "see Table 92d row 92d-A2c (not re-verified; PDF 403 again 2026-10-21)", OR + "Same%20Candidates...", "adjacent (token level, retrospective)", "same"),
    ("92e-L1t", "L1b", "Mohammadi, 2024, arXiv preprint " + c("MOHAMMADI"), "see Table 92d row 92d-A1h (not re-verified)", "https://arxiv.org/pdf/2406.05587v1", "contradicts-in-part (own attractor)", "explicit test of the own-attractor rival (q_tail, q_lik)"),
    ("92e-L1u", "L1a", "Samanta et al., 2026, arXiv preprint " + c("SAMANTA"), "see Table 92d row 92d-A2d (not re-verified)", "https://arxiv.org/html/2606.29933v1", "adjacent", "perturbation of the tuned model, forecast"),
    ("92e-L1v", "L1a", "Zhou (T.) 2026; Duan 2026 " + c("ZHOUT", "DUAN"), "see Table 92d rows 92d-A1a..d (not re-verified)", "https://arxiv.org/html/2607.20543v1", "adjacent (training-time forecasts; FLAG B partly)", "inference-time landing identity"),
    ("92e-L3c", "L3", "Zhang et al., 2025, arXiv preprint " + c("VS"), "see Table 92d row 92d-A2a (not re-verified)", "https://arxiv.org/html/2510.01171v4", "adjacent (stylised power sharpening)", "fitted alpha with rivals"),
    ("92e-L2b", "L2", "Wu et al. 2025; Yue et al. 2025 " + c("LEASH", "YUE"), "see Table 92d A0 quotes (not re-verified)", "https://arxiv.org/html/2507.14843v5", "supports", "algorithm-level support test"),
    ("92e-Se", "S-a", "Khalid et al., 2026; Zhu et al., 2026 (STARS) " + c("NOISESTEER", "STARS"), "see Table 92c rows C1-sited, C1-sitee (not re-verified)", "https://arxiv.org/html/2601.22010v1", "adjacent (site comparisons for narratives / test coverage)", "matched per-position dose; categorical algorithm choice"),
    ("92e-Sf", "S-c", "Zhang et al., 2026 " + c("WHEREINJECT"), "see Table 92c rows C1-sitea..c, 92d-Ci (not re-verified)", "https://arxiv.org/html/2606.10302v1", "adjacent (text-level sites)", "activation-level, content-free sites"),
    ("92e-Sg", "S-b", "Jerge et al., 2026; Nagarajan et al., 2025 " + c("JERGE", "NAGARAJAN"), "see Table 92c rows C1-sitef, C1-siteg (not re-verified)", "https://arxiv.org/html/2608.21595v1", "adjacent", "same"),
    ("92e-Sh", "S-a", "Kim et al., 2026 (random embedding injection) " + c("REI"), "see Table 92b row b6c (not re-verified)", "https://arxiv.org/html/2605.11936v2", "adjacent (math; code future work)", "code, test-checked labels"),
    ("92e-Fm", "F1", "Anonymous, 2026, ICLR 2027 submission " + c("BFT") + "; Dong et al. 2025 " + c("DONG"), "see Table 92c rows C2aa, C2ab, C2ac (not re-verified)", "https://openreview.net/forum?id=knirOusGcq", "adjacent (pre-generation plan states)", "fork margin at the algorithm opening"),
    ("92e-Fn", "F2", "Zhu et al., 2024 (AdapT) " + c("ADAPT"), "see Table 92b row b3b (not re-verified)", "https://arxiv.org/html/2309.02772v3", "adjacent", "margin-based account of temperature robustness"),
    ("92e-Kf", "K", "Wang et al. (BACo) " + c("BACO") + "; Peeperkorn et al. " + c("CONFORM") + "; Feng et al. " + c("SWITCH"), "see Table 92d rows 92d-B1i, Ca, Cb, Cc (not re-verified)", "https://arxiv.org/html/2511.05650v2", "occupied lane (base-aligned collaboration; 92d)", "algorithm-level, test-checked prices"),
    ("92e-Kg", "K", "SLR " + c("SLR") + "; FrankenMerging " + c("FRANKEN") + "; Dang et al. " + c("DANG") + "; Hindsight Merging " + c("HINDSIGHT"), "see Table 92d rows 92d-B1f, B1g, Ce, Cf and Hindsight quotes (not re-verified)", "https://arxiv.org/html/2610.22999v1", "adjacent (weight-level diversity restoration)", "base/instruct lambda 0.25/0.5 on algorithm labels"),
    ("92e-Kh", "K", "EFT " + c("EFT", "EFTVENUE") + "; proxy tuning " + c("PROXY") + "; Nudging " + c("NUDGING"), "see Table 92d quotes (B2/C) (not re-verified; venues corrected here)", "https://arxiv.org/html/2401.08565v4", "adjacent (logit-level knobs)", "proxy tuning priced on algorithm labels"),
    ("92e-Ga", "G", "FunSearch; AlphaEvolve " + c("FUNSEARCH", "ALPHAEVOLVE"), "see Table 92c rows C3ca, C3cb (not re-verified; no new search)", "https://www.nature.com/articles/s41586-023-06924-6", "context (scope)", "scope statement unchanged"),
]


def esc(s):
    return s.replace("|", "\\|")


def table():
    out = ["| Row | Claim (one line) | Neighbour (authors, arXiv v1 year, venue status) | Verbatim quote | URL; section; version | Retrieved | Relation | What this run adds, or 'replication' |",
           "|---|---|---|---|---|---|---|---|"]
    order = sorted(QROW, key=lambda r: ({"E": 0, "L": 1, "S": 2, "F": 3, "K": 4}.get(r[4], 9), len(r), r))
    order = [r for r in order if r != "92e-Ke"]
    for r in order:
        q = QROW[r]
        ver = q.get("version_quoted") or "-"
        out.append(f"| {r} | {esc(CL.get(q['claim'], q['claim']))} | {esc(NEIGH[q['ref_key']])} | \"{esc(q['quote'])}\" | {q['url'] if len(q['url']) < 120 else q['url'][:110] + '...'}; {esc(q['section'])}; {ver} | {q['retrieved']} | {esc(q['relation'])} [{q['status']}] | {esc(ADD.get(r, '-'))} |")
    for (r, cl, ne, ptr, url, rel, adds) in INHERITED_ROWS:
        out.append(f"| {r} | {esc(CL.get(cl, cl))} | {esc(ne)} | {ptr} | {url} | 2026-10-21 (inherited) | {esc(rel)}; inherited | {esc(adds)} |")
    return "\n".join(out)


def q(r):
    return QROW[r]["quote"]


def report():
    C = COUNTS
    qa_ok = sum(r["second_pass"] == "MATCH" for r in QA)
    n_new = len(QROW)
    n_ver = sum(QROW[r]["status"] == "VERIFIED" for r in QROW)
    n_abs = sum(QROW[r]["status"] == "VERIFIED-ABSTRACT" for r in QROW)
    n_blog = sum(QROW[r]["status"] == "VERIFIED-BLOG" for r in QROW)
    L = []
    A = L.append
    A("# Prior work on base landings and 8-bit nudges: positioning and saturation audit for iteration-6 Claims L, E, S/F, K (Table 92e)")
    A("")
    A("## 1. Scope, date and method")
    A("")
    A(f"Dated audit (logged search calls {C['search_window_utc'][0]} to {C['search_window_utc'][1]}; quote verification and live re-match 2026-10-21/22 UTC) of the iteration-6 claims L1a/L1b/L2/L3 (landing identity), E/E-attribution/E-deployment (FP8 W8A8 engine control), S-a..S-d and F1/F2 (site of content-free nudges, forks, margins) and K (diversity knobs). It extends Tables 92b/92c (art_kjrCpQnPaniY) and 92d (art_ObxQOIlAM9MS); their verified quotes are cited by row id and not re-verified. Claim wording comes from the artifact plan (the iteration-6 hypothesis text was not passed to this executor), and the 'what this run adds' column uses design facts only. The protocol (claims, 6 query families / 21 frozen strings, engines E1 OpenAlex/Crossref, E3 arXiv API, E4 Semantic Scholar, E5 OpenReview ICLR 2027, E6 grey literature, rubric, flags, stop rule) was frozen before the first search call (evidence/protocol_iter6.json, sha256 0e2dc2d7...a9c52, written 2026-10-21T23:34:28Z) {c('ARXIVAPI', 'S2API', 'ORAPI')}.")
    A("")
    eng = ", ".join(f"{k} {v}" for k, v in sorted(C['calls_by_engine'].items()))
    sv = ", ".join(f"{v} {k}" for k, v in C['scored_verdicts'].items())
    A(f"Totals: {C['logged_calls']} logged search calls ({eng}; S2 = Semantic Scholar citation calls), {C['raw_hits_total']} raw hits, {C['unique_after_dedup']} unique records after de-duplication against both earlier audits ({C['seen_in_either']} seen before and re-screened), {C['in_window']} in the 2026 window, {C['pass_prescreen_in_window']} passing the lane keyword pre-screen, {C['manually_screened']} title/abstract-screened by hand, {C['scored']} scored on the O/I/C rubric ({sv}). {len(Q)} new quote records: {n_new} Table 92e quotes ({n_ver} VERIFIED on versioned full text, {n_abs} VERIFIED-ABSTRACT, {n_blog} VERIFIED-BLOG/documentation) plus {len(Q) - n_new} venue-page confirmations; 0 unverified. A live second pass with the skill's fetch_grep re-matched {qa_ok}/{len(QA)}. A same-agent re-screen of {KAPPA['n_rescreened']} hits gave observed agreement {KAPPA['observed_agreement']} and Cohen's kappa {KAPPA['cohens_kappa']} (consistency, not independence: one screener). No OpenRouter calls were made; the built-in WebSearch tool used for E6 returns model-written result summaries, which served only to discover URLs and never as evidence.")
    A("")
    A("## 2. Answer box")
    A("")
    A(f"**FLAG E (activation quantisation changes what an activation-level intervention does): PARTLY FIRED.** No verified full text isolates ACTIVATION quantisation at matched weights and reports a changed behavioural effect of steering, noise, patching or ablation, so the flag does not fire. The nearest full text is weight-only: Steering Under Compression {c('SUC')} keeps activations in FP16/BF16 and states: \"{q('92e-Ea')}\" PAHQ {c('PAHQ')} quantises weights and activations together (FP32 vs 8-bit RTN) and finds that activation-patching circuit discovery fails: \"{q('92e-Ej')}\" Two contemporaneous ICLR 2027 submissions (abstract only; PDFs HTTP 403) report the general effect without saying whether activations are quantised: \"{q('92e-Ee')}\" {c('STABLE')}; \"{q('92e-Eh')}\" {c('LOWBIT')}.")
    A("")
    A(f"**FLAG L (base-model forecast of where a perturbed tuned model lands, scored against the tuned model's own tail or likelihood): PARTLY FIRED.** No paper forecasts, from the base model, which enumerated alternative a perturbed tuned model lands on and scores that forecast against the tuned model's own sampled tail or likelihood ranking, so the flag does not fire. Fine-tuning-perturbation work reports reversion toward base behaviour at distribution or likelihood level. The closest candidate is retrospective: \"{q('92e-L1d')}\" {c('REM')}. The others are distribution-level rebound {c('RESIST', 'ADYN')} and a prospective direction toward base-descended helpful-only states scored against a matched geometric null {c('GRAV')}. Token-level candidate preservation is adjacent {c('SBC', 'URIAL', 'SAMECAND')}. The rival the run must beat has support: \"{q('92e-L1k')}\" {c('W2S')}.")
    A("")
    A("### 2.1 Verdict per claim (lane verdict; deciding references)")
    A("")
    A("| Claim | Verdict | Deciding references | Note |")
    A("|---|---|---|---|")
    A(f"| L1a landing = base runner-up, forecast in advance | ADJACENT at algorithm level; concept partly occupied ('fine-tune-perturbed tuned models revert toward base behaviour') | {c('REM', 'RESIST', 'ADYN', 'GRAV', 'SBC', 'URIAL', 'SAMECAND', 'PREDMI')} | all fine-tuning perturbations, distribution/likelihood/token level; sealed base forecasts exist only for circuit change {c('PREDMI')} |")
    A(f"| L1b scored against q_lik and q_tail | OPEN to our knowledge; rival-supporting evidence exists | {c('W2S', 'PERSONA', 'EMNM', 'MOHAMMADI')} | the tuned model's own ranking/subspace already contains landings in these settings |")
    A(f"| L2 support | ADJACENT / supporting | {c('BARRIER', 'SBC', 'LEASH', 'YUE')} | theory and token-level evidence that post-training stays within base support |")
    A(f"| L3 power shape | ADJACENT / stylised | {c('RWS', 'VS')} | power sampling of the base matches GRPO in-domain; no fit against rivals on a perturbed tuned model |")
    A(f"| E engine control (2x2 factorial) | PARTLY OCCUPIED (general precision-dependence of steering effects: contemporaneous, abstract-level) | {c('STABLE', 'LOWBIT', 'SUC', 'PAHQ', 'PRISM')} | activation-vs-weight attribution not found in any verified text |")
    A(f"| E-attribution (absmax/scale readout) | ADJACENT | {c('KVCOL', 'SAMEREQ', 'ALIBI', 'LIQ', 'SQ', 'INT8', 'MASSIVE')} | scale-factor mechanisms are documented for KV cache and perplexity, not for nudges |")
    A(f"| E-deployment ('same default, different nudgeability') | GENERAL form OCCUPIED (activation-side KV-cache quantisation silently changes refusals at ~flat perplexity; flips at matched accuracy); nudgeability form open | {c('KVCOL', 'DUTTA', 'LOWBIT', 'FLATSCORE', 'DISPL', 'KURTIC')} | premise supported: per-token-scaled FP8 W8A8 is accuracy-lossless {c('KURTIC')}; frame the finding as an instance of a known deployment hazard |")
    A(f"| S-a..S-d site at matched dose | PARTLY OCCUPIED (inherited site comparisons for narratives/test coverage); FLAG S not fired | {c('NOISESTEER', 'STARS', 'WHEREINJECT', 'EMBPERT', 'FORKSROAD', 'JERGE', 'NAGARAJAN')} | no matched-dose comparison of prefill bands vs read position vs condition vs generated tokens on a categorical choice |")
    A(f"| F1 fork / entrance | CROWDED-ADJACENT | {c('FORKING', 'FORKFAST', 'ANCHORS', 'LOCKED', 'CLIFF', 'HIGHENT', 'BFT')} | fork finding is published; the run's contribution is the margin readout at the algorithm opening |")
    A(f"| F2 margin bounds temperature | GENERAL margin mechanism OCCUPIED (precision flips); temperature form is textbook (logit/T) | {c('GREEDY', 'MARGINGATE', 'SAMEREQ', 'TOPN', 'RENZE', 'ADAPT')} | present as a diagnostic/application, not a finding |")
    A(f"| K knobs priced on algorithm labels | PARTLY OCCUPIED (base merging restores diversity on code benchmarks; weight averaging; base-aligned collaboration); FLAG K not fired | {c('FAMILIAR', 'ATAX', 'WISE', 'BACO', 'FRANKEN', 'HINDSIGHT', 'DANG', 'SLR', 'FORKSROAD')} | no test-checked algorithm-level labels in any neighbour |")
    A(f"| G scope | unchanged (no new search) | {c('FUNSEARCH', 'ALPHAEVOLVE')} | cross-reference to 92c C3ca/C3cb |")
    A("")
    A("### 2.2 Permitted wording (dated; 'first' is never licensed by a search)")
    A("")
    A(f"- **L1a/L1b.** \"Fine-tuning-perturbation studies report that tuned models revert toward base-model behaviour, at the level of output distributions, sequence likelihoods or activation-space directions {c('REM', 'RESIST', 'ADYN', 'GRAV')}. At the token level, post-training mostly reorders candidates the base model already ranks highly {c('URIAL', 'SBC', 'SAMECAND')}. To our knowledge (dated search 2026-10-21/22; evidence/), no prior work commits in advance to an algorithm-level forecast, from the base model's composition, of which alternative a content-free perturbation of a tuned model lands on, and scores it against the tuned model's own likelihood ranking and sampled tail.\" The run must report the rival result even if it is unfavourable. The tuned model's own top-k contains jailbroken landings {c('W2S')}, and its own subspace forecasts fine-tuning landings {c('PERSONA')}.")
    A(f"- **E.** \"Contemporaneous work reports that the behavioural effect of a fixed steering intervention need not survive quantisation even when output fidelity and direction similarity are preserved {c('STABLE', 'LOWBIT')}. Weight-only quantisation preserves steering directions {c('SUC')}, and joint 8-bit weight-activation quantisation disables patching-based circuit discovery {c('PAHQ')}. To our knowledge (dated search), no verified full text separates activation from weight precision for activation-level interventions. Our 2x2 factorial does so for content-free nudges on a production FP8 W8A8 engine.\" If [2] or [3] turn out to quantise activations, write 'replicates ... in a new setting (content-free nudges, test-checked code-algorithm choice)'.")
    A(f"- **E-deployment.** \"FP8 W8A8 with dynamic per-token activation scales is reported to be accuracy-lossless {c('KURTIC')}. Yet, like activation-side KV-cache quantisation, which removes refusals at near-unchanged perplexity {c('KVCOL')}, and compression flips at matched accuracy {c('DUTTA')}, [result] shows that nudgeability is a deployment property not captured by default-output fidelity.\" Present it as an instance of a known hazard class, not a new class.")
    A(f"- **S.** \"Site comparisons for noise-based diversity exist for narratives and test coverage {c('NOISESTEER', 'STARS')} and at text level {c('WHEREINJECT')}; we compare activation sites at matched per-position dose on a categorical, test-checked algorithm choice.\"")
    A(f"- **F1/F2.** \"Forking tokens and entrance decisions are established {c('FORKING', 'FORKFAST', 'LOCKED', 'CLIFF')}. A top-two logit margin is known to govern which decisions flip under small numerical perturbations {c('GREEDY', 'MARGINGATE')}. We use the twin model's teacher-forced margin between algorithm openings to bound the effect of temperature on the algorithm choice.\" This describes a diagnostic, not a discovery.")
    A(f"- **K.** \"Merging a fine-tuned model with its base restores output diversity {c('FAMILIAR', 'HINDSIGHT', 'FRANKEN')}, and pre/post-RLHF weight averaging trades alignment against forgetting {c('ATAX')}. We price these knobs on test-checked algorithm-level labels against base intent, enumerate-and-pick and plan noise.\"")
    A("")
    A("### 2.3 Reviewer baselines this search implies")
    A("")
    A(f"- **Precision arms.** Use a weight-only FP8 W8A16 kernel vs an FP8 W8A8 kernel at identical weights, and add an activation-only W16A8 fake-quant arm. Report the engine's actual scheme: the released Qwen3-8B-FP8 checkpoint uses fine-grained block-128 FP8 {c('QWENCARD')}, while vLLM FP8_DYNAMIC uses per-channel weight scales and dynamic per-token activation scales {c('VLLM')}. Unscaled casting is a different regime {c('LIQ', 'PAHQ')}.")
    A(f"- **Numerics controls.** Add a kernel-swap arm at a fixed quantisation config {c('ALIBI')}, batch-invariant or fixed-batch execution {c('TMBLOG', 'FP32')}, weights-through-16-bit-kernels {c('SAMEREQ')}, and BF16 vs FP16 at the same weights {c('GREEDY')}.")
    A(f"- **Fidelity metrics from the closest neighbours.** Report steered-output KL vs unsteered-output KL {c('LOWBIT')} and a signed intervention-fidelity gap with a first-order local-sensitivity predictor {c('STABLE')}, so the run's effect can be compared with theirs.")
    A(f"- **Landing rivals.** Compare q_lik (the teacher-forced ranking of the tuned model), q_tail (its sampled tail), the rebound/pre-training baseline {c('RESIST')}, and token-level base top-k overlap {c('SBC')}.")
    A(f"- **Knobs.** Sweep base/instruct weight interpolation over lambda {c('WISE', 'ATAX')}. Add base merging {c('FAMILIAR')}, BACo {c('BACO')}, proxy tuning/EFT {c('PROXY', 'EFT')} and prefix perturbation at the fork {c('FORKSROAD')}, all against a temperature baseline.")
    A("")
    A("## 3. Table 92e (paste-ready; same columns as 92d)")
    A("")
    A(table())
    A("")
    A("### 3.1 Further verified or screened neighbours not in the table")
    A("")
    A(f"- Screened at abstract level and scored but not quoted. Quantisation hides behavioural damage behind flat scores: {c('FLATSCORE', 'DISPL', 'PRECUP', 'QPOLICY')} (weight-only or compiled policies). Safety-preserving PTQ including W4A4 {c('SAFEQ')}. Flip repair by precision patching of weight groups {c('QGATE')}. A pre-SFT emergent-misalignment risk forecast from the base model {c('ALIGNRADAR')}. A replication of the base/RL top-k overlap analysis {c('REBEL')}. bf16 export casting that reverts fine-tuning changes {c('BF16CAST')}.")
    A(f"- Grey literature (E6): a GitHub study of NVFP4/FP8 damage with tuned lens and SAE features on bf16 vs low-bit activations {c('GITHUB-QI')} was not fetched; under the frozen rule a repository is context and never fires a flag.")
    A(f"- Mechanism anchors outside the window: {c('SQ', 'INT8', 'MASSIVE', 'FP8FMT', 'HONG', 'DUTTA')}.")
    A(f"- Inherited rows used as background but not re-quoted: the base-to-tuned transplant/patching method rows 92d-B1a..B1e {c('ZHOUY', 'OOZEER')}, shallow safety alignment 92b-b3a {c('QISHALLOW')}, pre-generation planning rows 92c-C2ad and C2ah {c('WHEREPLAN', 'BREWING')}, and sparse RL-token replacement 92d-Cd {c('RLREPLACE')}.")
    A("")
    A("## 4. Saturation search (PRISMA-S style)")
    A("")
    A("| Family | Calls | Raw hits | Unique records touching family | In window | Pass pre-screen | Manually screened |")
    A("|---|---|---|---|---|---|---|")
    for f, v in C["per_family"].items():
        A(f"| {f} | {v['calls']} | {v['raw_hits']} | {v['unique_records_touching_family']} | {v['in_window']} | {v['pass_prescreen_in_window']} | {v['manually_screened']} |")
    A("")
    A(f"Engines and settings were inherited from art_ObxQOIlAM9MS. E1 ran aii_fast_web_search.py --mode scholarly (25 results). E3 queried the arXiv API (cs.CL/cs.LG/cs.AI, newest first, 50 results). E4 queried the Semantic Scholar /paper/search endpoint (year=2026, 50 results). E5 queried OpenReview notes/search (ICLR.cc/2027/Conference, 50 results). E6 used the built-in WebSearch with allowed_domains set to the grey-literature list (FE1 and FL1), plus github.com for FE1. Forward citations came from Semantic Scholar; the one logged OpenAlex cites: attempt per mandatory neighbour returned 0, 0, 0 and 3 records. Records were de-duplicated by arXiv id, OpenReview id and normalised title against both earlier candidate sets (1,729 + 3,506). Of the {C['logged_calls']} calls, one E5 call returned HTTP 429 and was retried successfully. Records failing the pre-screen in every lane: {C['prescreen_fail']}.")
    A("")
    A(f"Rounds: R1 ran 21 strings on E1/E3/E4/E5, plus 14 E6 calls and forward citations of 4 + 4 seeds (Steering Under Compression 0 citing works, Sparse but Critical 24, Forking Paths 48, Give Me FP32 80, Reasoning with Sampling 95, Thought Anchors 148, Non-surjective 8, Lost in Quantization 0). R2 ran 6 vocabulary queries on 4 engines. R3 chased forward citations of 6 closest new hits and backward references of 2 per flag. R4 chased forward citations of 3 round-3 hits and backward references of 1. **Stop condition:** {C['stop_condition']}")
    A("")
    A("## 5. Corrections and confirmations")
    A("")
    for r in CORR:
        A(f"- **{r['item']}.** Previously: {r['was']}. Now: {r['now']}.")
    A("")
    A("## 6. Unverified or partly verified references (no numbers taken beyond what is stated)")
    A("")
    A(f"- OpenReview PDFs returned HTTP 403 for 8iTqrW1sxY {c('STABLE')}, h57duZqLOr {c('LOWBIT')}, 6t1egKiB0v {c('SPECTRA')}, ooV5M72O08 {c('SAMECAND')} and knirOusGcq {c('BFT')}. The notes?id= API returned 403 ChallengeRequiredError. Only abstract records from notes/search are used, so their precision factors, models and numbers beyond the abstracts are unknown.")
    A(f"- The publisher page of the Float32 patching paper (mdpi.com) returned 403. It is quoted from its Semantic Scholar abstract record {c('F32')}.")
    A(f"- One E1 record had no abstract or URL and was not scored: 'Where the Answer Is Born: Causal Interventions on the Information Trajectory of a Quantized Hybrid Language Model'. It is UNVERIFIED and listed so a later round can resolve it. A second such record, 'From Weights to Activations: Is Steering the Next Frontier of Adaptation?', was resolved to arXiv 2604.14090 (ACL 2026 Main): it is a position paper with no precision factor, scored irrelevant {c('OSTERMANN')}.")
    A(f"- Thought Anchors has no venue found {c('ANCHORS')}. Proxy tuning's COLM 2024 venue rests on its arXiv comment {c('PROXY')}.")
    A("")
    A("## 7. Confidence, contradicting evidence, and what would change each verdict")
    A("")
    A(f"- **FLAG E: medium confidence.** The verdict rests on abstract-level text for the two closest candidates. Full texts showing W8A8/FP8-activation arms would turn PARTLY into FIRES, and Claim E would become a replication {c('STABLE', 'LOWBIT')}. Contradicting in part: numerics alone change outputs and margins {c('FP32', 'GREEDY', 'ALIBI', 'TMBLOG')}, so a W8A8 effect could be a kernel or batching artefact unless numerics are controlled. Weight-only steering directions survive quantisation {c('SUC')}, which argues against large weight-side effects.")
    A(f"- **FLAG L: medium-high confidence.** It would FIRE if a paper commits to a base-model forecast of the landing identity and scores it against the tuned model's own ranking. The closest work is retrospective {c('REM')} or uses a geometric null {c('GRAV')}. Contradicting evidence favours the rival hypothesis that nudges walk the tuned model's own ladder {c('W2S', 'PERSONA', 'MOHAMMADI')}. Lee et al.'s mixed base-vs-instruct direction {c('LEE')} warns that the base runner-up need not be the tuned model's runner-up.")
    A(f"- **S/F/K: medium confidence.** These lanes are crowded {c('FORKING', 'LOCKED', 'GREEDY', 'MARGINGATE', 'FAMILIAR', 'BACO')}. The handbook's base rate for unchecked lanes being occupied is 11/11, and this audit added contemporaneous occupants in E and F2. A screener-risk caveat applies: one agent scored everything, and the re-screen is a consistency check (kappa {KAPPA['cohens_kappa']}).")
    A("")
    A("## 8. Follow-up questions")
    A("")
    for fq in FOLLOW:
        A(f"- {fq}")
    return "\n".join(L)


OVERRIDE = {  # passages taken verbatim from the live page where the table quote's markup/escapes differ (literal check)
    "STABLE": [{"quote": "Steering directions can remain aligned across model precision changes while their functional effects drift; local functional sensitivity predicts and corrects this cross-precision fidelity gap.",
                "locator": "TLDR field of the OpenReview API record"}],
    "TMBLOG": [{"quote": "We use `Qwen/Qwen3-235B-A22B-Instruct-2507` and sample 1000 completions at temperature 0", "locator": "Experiments: How nondeterministic are completions?"}],
    "SHARP": [{"quote": "tiny perturbations along them can cause large, erratic, input-dependent behavioral swings", "locator": "Abstract (NeurIPS 2026 poster page)"}],
}

FOLLOW = [
    "TOP (FLAG E partly fired at contemporaneous abstract level): once ICLR 2027 PDFs open (reviews due about end of October 2026), do OpenReview 8iTqrW1sxY ('Stable Directions, Different Effects') and h57duZqLOr ('Activation Steering under Low-Bit Quantization') include ACTIVATION quantisation (W8A8, FP8 activations, KV cache), or weights only? If they include activations, Claim E becomes a replication in a new setting (content-free nudges, code-algorithm choice).",
    "Does PAHQ's failure mode (small patch effects truncated to zero under unscaled FP8/RTN) appear under per-token-scaled FP8 W8A8? The run's W16A8 arm with per-token absmax readouts can answer this directly.",
    "In the run's own data, what fraction of nudge landings lie within the tuned model's own teacher-forced top-k (q_lik) or sampled tail (q_tail), compared with the base runner-up? Weak-to-strong jailbreaking predicts that the tuned model's own ranking already contains many landings.",
    "Re-check Same Candidates (ooV5M72O08) and Before the First Token (knirOusGcq) when their PDFs open, and confirm whether Locked at the Entrance (now arXiv 2608.29188) compares its entrance-family coverage with the base model.",
    "UNMAPPED citation numbers: the one-to-one assignment of the hypothesis's own reference numbers 88-91, 92/93/102, 98/99 and 81/82 to papers needs the hypothesis reference list (inherited/citation_map.json maps only the sets of inherited rows).",
    "Which FP8 scheme did the iteration-4 engine actually use: block-128 fine-grained checkpoint scales or dynamic per-token activation scales? The attribution readout depends on it.",
]


def main():
    text = report()
    (WS / "research_report.md").write_text(text, encoding="utf-8")
    srcs = []
    for i, (k, url, title, authors, year, summ, rows) in enumerate(SOURCES):
        sp = list(OVERRIDE.get(k, []))
        for r in ([] if k in OVERRIDE else rows):
            qq = QROW.get(r)
            if qq and qq["status"].startswith("VERIFIED"):
                seg = max([s for s in qq["quote"].split(" [...] ")], key=len)
                sp.append({"quote": seg, "locator": qq["section"]})
        srcs.append({"index": i + 1, "key": k, "url": url, "title": title, "summary": summ, "authors": authors, "year": year,
                     "supporting_passages": sp})
    (CACHE / "sources_iter6.json").write_text(json.dumps(srcs, ensure_ascii=False, indent=1))
    (CACHE / "follow_up_iter6.json").write_text(json.dumps(FOLLOW, ensure_ascii=False, indent=1))
    print(f"report: {len(text)} chars; sources: {len(srcs)}; passages: {sum(len(s['supporting_passages']) for s in srcs)}")


if __name__ == "__main__":
    main()
