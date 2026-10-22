"""Build evidence/quotes_iter6.jsonl: one record per NEW Table 92e quote, verified against the cached versioned text with
the inherited normalisation rule (common.normalise / quote_matches: whitespace, ligatures, curly quotes, dashes, PDF
line-end hyphenation, markdown/html2text emphasis). A quote that does not match is written with status UNVERIFIED and
printed, and carries no number in the report. The nearest preceding markdown heading of the match is recorded as
'auto_section' (arXiv HTML); 'section' is the locator written by hand from the grep output.

Usage: python -I tools/build_quotes_iter6.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import EVID, WS, append_jsonl, load_text, normalise, quote_matches  # noqa: E402

META = json.loads((EVID / "arxiv_meta.json").read_text())
RET = "2026-10-21"


def ax(aid, ver):
    return f"https://arxiv.org/html/{aid}{ver}"


def axpdf(aid, ver):
    return f"https://arxiv.org/pdf/{aid}{ver}"


def orsearch(title):
    import urllib.parse
    return ("https://api2.openreview.net/notes/search?term=" + urllib.parse.quote(title) +
            "&group=ICLR.cc/2027/Conference&limit=10")


T_STABLE = "Stable Directions, Different Effects: Intervention Fidelity Across Model Precision"
T_LOWBIT = "Activation Steering under Low-Bit Quantization: A Geometric Perspective on Degradation and Recovery"
T_SPECTRA = "Quantization-Induced Decision Changes Have Regime-Dependent Intervention Spectra"
T_PREDMI = ("Predictive Mechanistic Interpretability of Post-Training: A Priori Forecasts of Circuit Localization and "
            "Sign from the Base Model")
T_FAMILIAR = "Should SFT Prefer the Familiar? Diversity Collapse and Recovery via Model Merging"
T_HELPS = "When Quantization Helps: Corrective Computation in Low-Bit Language Models"

# (row, claim, ref_key, cache_key, url, section, quote, relation, status_target, venue_status, venue_evidence)
Q = [
    # ---------------- LANE LE (FLAG E) ----------------
    ("92e-Ea", "E", "Bhandari2026-SteeringUnderCompression", "2609.06473v1", ax("2609.06473", "v1"), "Sec. 6 (Limitations)",
     "We study only bitsandbytes weight-only quantization (INT8, NF4); activation quantization (W8A8, W4A4) and outlier-aware weight algorithms (GPTQ, AWQ, SmoothQuant, QuaRot) are excluded by design and may behave differently.",
     "adjacent; FLAG E partly (weight-only)", "VERIFIED", "arXiv preprint (v1, 6 Sep 2026; no venue in comment)", "arXiv API comment: '17 pages, 5 figures'"),
    ("92e-Eb", "E", "Bhandari2026-SteeringUnderCompression", "2609.06473v1", ax("2609.06473", "v1"), "Sec. 3.2 (Models and Quantization Schemes)",
     "Activations remain in FP16/BF16 throughout the forward pass. This isolates the primary comparison to weight quantization.",
     "adjacent; FLAG E partly (weight-only)", "VERIFIED", "arXiv preprint", "-"),
    ("92e-Ec", "E", "Bhandari2026-SteeringUnderCompression", "2609.06473v1", ax("2609.06473", "v1"), "Abstract",
     "Despite this, steering vectors remain highly collinear with their FP16 siblings (cosine similarity 0.989-0.998 for INT8, 0.945-0.990 for NF4), confirming that the behavioral direction survives quantization even when the cost structure does not.",
     "adjacent (internal outcome: vector cosine)", "VERIFIED", "arXiv preprint", "-"),
    ("92e-Ed", "E", "Bhandari2026-SteeringUnderCompression", "2609.06473v1", ax("2609.06473", "v1"), "Sec. 4.5",
     "Steering vectors extracted independently per scheme (same contrast pairs, same resample) are nearly collinear with their FP16 siblings",
     "adjacent (vectors recomputed per precision: C = 0.5)", "VERIFIED", "arXiv preprint", "-"),
    ("92e-Ee", "E", "Anon2026-StableDirections", "or_8iTqrW1sxY", orsearch(T_STABLE), "Abstract (OpenReview API record; keywords 'model quantization', 'cross-precision transfer')",
     "Preserving standard model quality or direction-level representation similarity does not guarantee that the intervention effect is preserved.",
     "occupies the general claim (precision factor unstated); FLAG E unresolved-partly", "VERIFIED-ABSTRACT",
     "ICLR 2027 Conference Desk Rejected Submission (OpenReview venue field); contemporaneous", "OpenReview venue field"),
    ("92e-Ef", "E", "Anon2026-StableDirections", "or_8iTqrW1sxY", orsearch(T_STABLE), "Abstract (OpenReview API record)",
     "Intervention effects can change even when directions remain strongly aligned",
     "occupies the general claim; FLAG E unresolved-partly", "VERIFIED-ABSTRACT", "ICLR 2027 desk-rejected submission", "OpenReview venue field"),
    ("92e-Eg", "E", "Anon2026-SteeringLowBit", "or_h57duZqLOr", orsearch(T_LOWBIT), "Abstract (OpenReview API record; keywords 'Quantization', 'Activation Steering')",
     "We study steering compatibility with the intervention layer, direction, and strength held fixed across full-precision and quantized models.",
     "occupies the general claim (scheme unstated; calibration/reconstruction language suggests weight PTQ); FLAG E unresolved-partly",
     "VERIFIED-ABSTRACT", "ICLR 2027 Conference Submission; contemporaneous", "OpenReview venue field"),
    ("92e-Eh", "E", "Anon2026-SteeringLowBit", "or_h57duZqLOr", orsearch(T_LOWBIT), "Abstract (OpenReview API record)",
     "We show that ordinary output fidelity alone does not guarantee preservation of responses to the same intervention.",
     "occupies the general claim; FLAG E unresolved-partly", "VERIFIED-ABSTRACT", "ICLR 2027 Conference Submission", "OpenReview venue field"),
    ("92e-Ei", "E", "Wang2025-PAHQ", "2510.23264v1", ax("2510.23264", "v1"), "Sec. 2 (Direct Quantization Does Not Work on ACDC)",
     "We directly applied quantization from 32 bits to 8 bits to all weights and activations of the model Radford et al. (2019) in the ACDC Conmy et al. (2023) method, which is called Round-to-Nearest Quantization (RTN-Q), on the Indirect Object Identification (IOI) task Wang et al. (2022) and tested its performance.",
     "adjacent; FLAG E partly (weights and activations quantised jointly; circuit-recovery outcome)", "VERIFIED",
     "arXiv preprint (v1, 27 Oct 2025; no venue in comment)", "arXiv API comment empty"),
    ("92e-Ej", "E", "Wang2025-PAHQ", "2510.23264v1", ax("2510.23264", "v1"), "Sec. 1 (Introduction)",
     "when precision is reduced from 32 bits to 8 bits, direct quantization (also called Round-to-Nearest Quantization, RTN-Q) significantly increases the minimum quantization step size, causing activation values below this threshold to be truncated to zero and ultimately rendering the automated circuit discovery method ineffective.",
     "adjacent; FLAG E partly", "VERIFIED", "arXiv preprint", "-"),
    ("92e-Ek", "E", "Wang2025-PAHQ", "2510.23264v1", ax("2510.23264", "v1"), "Sec. 2 (Numerical Underflow)",
     "This means that if the difference between inference outputs before and after replacing activation values of selected edges is less than the minimum quantization step size, this difference will be truncated to zero.",
     "adjacent; FLAG E partly (mechanism is unscaled-format underflow)", "VERIFIED", "arXiv preprint", "-"),
    ("92e-El", "E", "Baligar2026-Float32Patching", "s2_computation14090212",
     "https://api.semanticscholar.org/graph/v1/paper/DOI:10.3390/computation14090212?fields=title,abstract,venue,publicationDate,authors,externalIds",
     "Abstract (Semantic Scholar API record; publisher page https://www.mdpi.com/2079-3197/14/9/212 returned HTTP 403)",
     "In matched float32/float64 experiments, at a descriptive 3 [...] floor, 13.0% and 51.2% of full-displacement interactions fell below the threshold",
     "adjacent; FLAG E partly (numerics precision floor; internal outcome; not activation quantisation)", "VERIFIED-ABSTRACT",
     "Computation (MDPI) 2026, DOI 10.3390/computation14090212 (journal)", "S2 venue/DOI fields"),
    ("92e-Em", "E", "Anon2026-InterventionSpectra", "or_6t1egKiB0v", orsearch(T_SPECTRA), "Abstract (OpenReview API record)",
     "On disagreeing inputs, we add these projections at their native magnitude to the quantized residual state, testing agreement with the original full-precision prediction regardless of correctness.",
     "adjacent (method-overlap: activation additions on quantised residual states as a repair)", "VERIFIED-ABSTRACT",
     "ICLR 2027 Conference Submission", "OpenReview venue field"),
    ("92e-En", "E", "Anon2026-QuantHelps", "or_GYm4mg9yGQ", orsearch(T_HELPS), "Abstract (OpenReview API record)",
     "Targeted interventions link these changes to predictions: replacing selected quantized activations with their high-precision values can reverse naturally corrected answers",
     "adjacent (weight-only GPTQ/AWQ/NF4; patching used to analyse quantisation)", "VERIFIED-ABSTRACT",
     "ICLR 2027 Conference Submission", "OpenReview venue field"),
    ("92e-Eo", "E", "Bonas2026-PRISM", "2610.20808v1", ax("2610.20808", "v1"), "Sec. 1 (Introduction)",
     "We explore 16-bit (BF16) and 4-bit (NF4) versions of smaller models to expose harmful tool-call compliance and estimate intervention directions.",
     "adjacent; FLAG E partly (weight-only NF4; directions transferred across precision)", "VERIFIED",
     "arXiv preprint (v1, 14 Oct 2026)", "arXiv API comment empty"),
    ("92e-Ep", "E", "Bonas2026-PRISM", "2610.20808v1", ax("2610.20808", "v1"), "Sec. 2.2 (Compression as behavioral supervision)",
     "Directions using NF4 labels act directly on the original BF16 model’s activations.",
     "adjacent", "VERIFIED", "arXiv preprint", "-"),
    ("92e-Eq", "E", "Mishra2026-NonSurjective", "2604.09839v2", ax("2604.09839", "v2"), "Sec. 7 (Conclusion and Limitations; App. D)",
     "Noticeably, our theoretical claim does not cover quantization effects. However, we experiment with an INT4 quantized model and find that our empirical claims hold comfortably in this setting (§D).",
     "context (new finding vs inherited rows 92b-b7c / 92c-C2-geod)", "VERIFIED",
     "ICLR 2026 Workshops (Sci4DL, Re-Align) per arXiv comment", "arXiv API comment"),
    ("92e-Er", "E-deployment", "Xu2026-KVCacheAlignmentCollapse", "2606.09864v2", axpdf("2606.09864", "v2"), "Abstract (PDF p. 1)",
     "we find that low-bit quantization can silently destroy safety alignment (Mistral-7B loses 15.2% of its refusals at only 1.03× perplexity",
     "adjacent (activation-side KV-cache quantisation changes behaviour; no activation-level intervention)", "VERIFIED",
     "arXiv preprint (comment: 'Preprint. 61 pages')", "arXiv API comment"),
    ("92e-Es", "E-attribution", "Xu2026-KVCacheAlignmentCollapse", "2606.09864v2", axpdf("2606.09864", "v2"), "Abstract (PDF p. 1)",
     "where safety lives in non-outlier channels collaterally damaged by outlier-driven scale factors",
     "adjacent (scale-factor mechanism analogous to per-token absmax readouts)", "VERIFIED", "arXiv preprint", "-"),
    ("92e-Et", "E", "Silva2026-LostInQuantization", "propor2026_108_page", "https://aclanthology.org/2026.propor-1.108/", "Abstract (ACL Anthology page; PDF pp. 1044-1048)",
     "INT8 with outlier handling preserves perplexity in both languages, while naive FP8 casting degrades English far more than PT-BR (+18% vs. +3.9%).",
     "adjacent (no intervention; naive unscaled E4M3 casting)", "VERIFIED",
     "PROPOR 2026 Vol. 1, pp. 1044-1048 (ACL Anthology 2026.propor-1.108)", "Anthology ID: 2026.propor-1.108; Pages: 1044–1048"),
    ("92e-Eu", "E", "Silva2026-LostInQuantization", "propor2026_108_page", "https://aclanthology.org/2026.propor-1.108/", "Abstract (ACL Anthology page)",
     "Our FP8 results reflect a naive casting stress test (no calibration/scaling), not an optimized FP8 recipe.",
     "adjacent (scope: not per-token-scaled W8A8)", "VERIFIED", "PROPOR 2026", "Anthology page"),
    ("92e-Ev", "E", "Yuan2025-GiveMeFP32", "2506.09501v2", ax("2506.09501", "v2"), "Abstract (v2)",
     "For instance, under bfloat16 precision with greedy decoding, a reasoning model like DeepSeek-R1-Distill-Qwen-7B can exhibit up to 9% variation in accuracy and 9,000 tokens difference in response length due to differences in GPU count, type, and evaluation batch size.",
     "adjacent (numerics change outputs; no intervention)", "VERIFIED",
     "NeurIPS 2025 oral (as 'Understanding and Mitigating Numerical Sources of Nondeterminism in LLM Inference')",
     "https://neurips.cc/virtual/2025/oral/118170 (page header 'Oral')"),
    ("92e-Ew", "E", "He2025-DefeatingNondeterminism", "tm_nondeterminism", "https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/", "Experiments ('How nondeterministic are completions?')",
     "Surprisingly, we generate 80 unique completions",
     "context (batch-dependent numerics; the run's model family)", "VERIFIED-BLOG", "Thinking Machines Lab blog, Sep 10, 2025", "post header 'Sep 10, 2025'"),
    ("92e-Ex", "E", "He2025-DefeatingNondeterminism", "tm_nondeterminism", "https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/", "Batch invariance and 'determinism'",
     "it's because our forward pass lacks \"batch invariance\", causing our request's output to depend on the batch size of our forward pass.",
     "context (reviewer baseline: batch-invariant kernels)", "VERIFIED-BLOG", "blog", "-"),
    ("92e-Ey", "E", "Chen2026-IntegerAlibi", "2608.13756v2", ax("2608.13756", "v2"), "Abstract",
     "At 1.7B each arm reproduces itself bit-for-bit across cold restarts, yet the arms agree on no sequence in any end-to-end comparison we ran (0/8, 0/16, and 0/64).",
     "context (reviewer baseline: kernel-swap control at fixed W8A8 config)", "VERIFIED",
     "arXiv preprint (comment: 'Pre-registered protocol with append-only amendments')", "arXiv API comment"),
    ("92e-Ez", "E-attribution", "Patodiya2026-SameRequestDifferentAnswer", "2609.04748v2", ax("2609.04748", "v2"), "Abstract",
     "Serving four-bit weights through 16-bit kernels left divergence not detectably different from 16-bit, placing the amplification mainly in the quantized execution path.",
     "adjacent (weights-vs-execution-path control for numerics divergence, not for interventions)", "VERIFIED",
     "arXiv preprint (v2 comment: revised after peer review at IEEE Access; resubmission under review)", "arXiv API comment"),
    ("92e-Eaa", "E", "Du2026-GreedyNotPrecisionInvariant", "2609.26621v1", axpdf("2609.26621", "v1"), "Sec. 1 (Introduction), p. 2",
     "With FP8 confined to the head projection, a format-rescaled gate achieves exact agreement on TinyLlama and +56pp on Qwen2.5-3B.",
     "context (numerics; end-to-end FP8 divergence is body-dominated)", "VERIFIED",
     "Transactions on Machine Learning Research (TMLR), 2026 (arXiv comment/journal_ref; reviewed on OpenReview QDOKyg7a5e)", "arXiv API comment + PDF header"),
    ("92e-Eab", "E-deployment", "Dutta2024-AccuracyNotAllYouNeed", "2407.09141v1", ax("2407.09141", "v1"), "Abstract",
     "However, even when the accuracy of baseline and compressed model are similar, we observe the phenomenon of flips, wherein answers change from correct to incorrect and vice versa in proportion.",
     "adjacent (deployment analogue: same accuracy, different behaviour)", "VERIFIED", "NeurIPS 2024", "arXiv journal_ref: proceedings.neurips.cc 2024"),
    ("92e-Eac", "E-attribution", "Xiao2023-SmoothQuant", "2211.10438v7", ax("2211.10438", "v7"), "Abstract",
     "Based on the fact that weights are easy to quantize while activations are not, SmoothQuant smooths the activation outliers by offline migrating the quantization difficulty from activations to weights with a mathematically equivalent transformation.",
     "context (mechanism anchor; per-token activation scales)", "VERIFIED", "ICML 2023", "arXiv comment 'ICML 2023'"),
    ("92e-Ead", "E-attribution", "Dettmers2022-LLMint8", "2208.07339v2", ax("2208.07339", "v2"), "Sec. 1 (Introduction)",
     "the sparse but systematic large magnitude outlier features that ruin quantization precision once they emerge in all transformer layers starting at scales of 6.7B parameters",
     "context (mechanism anchor)", "VERIFIED", "NeurIPS 2022", "arXiv comment 'Published at NeurIPS 2022'"),
    ("92e-Eae", "E-attribution", "Sun2024-MassiveActivations", "2402.17762v2", ax("2402.17762", "v2"), "Sec. 1 (Introduction)",
     "Many of these activations are found within the starting word token and delimiter tokens.",
     "context (position-specific spikes drive per-token scales)", "VERIFIED", "COLM 2024", "arXiv comment 'COLM 2024'"),
    ("92e-Eaf", "E-attribution", "Sun2024-MassiveActivations", "2402.17762v2", ax("2402.17762", "v2"), "Sec. 1 (Introduction)",
     "We show that massive activations act as fixed but crucial bias terms in LLMs.",
     "context", "VERIFIED", "COLM 2024", "-"),
    ("92e-Eag", "E", "Micikevicius2022-FP8Formats", "2209.05433v2", ax("2209.05433", "v2"), "Abstract",
     "we propose an 8-bit floating point (FP8) binary interchange format consisting of two encodings - E4M3 (4-bit exponent and 3-bit mantissa) and E5M2 (5-bit exponent and 2-bit mantissa).",
     "context (format definition)", "VERIFIED", "arXiv preprint (2022)", "arXiv API comment empty"),
    ("92e-Eah", "E-deployment", "Hong2024-DecodingCompressedTrust", "2403.15447v3", ax("2403.15447", "v3"), "Abstract",
     "For instance, a 4-bit quantized model retains the trustworthiness of its original counterpart, but model pruning significantly degrades trustworthiness, even at 50% sparsity.",
     "context (weight quantisation and behaviour)", "VERIFIED", "ICML 2024", "arXiv comment 'Accepted to ICML'24'"),
    ("92e-Eai", "E", "Qwen2025-Qwen3-8B-FP8-card", "hf_qwen3_8b_fp8", "https://huggingface.co/Qwen/Qwen3-8B-FP8", "Model card, 'Note on FP8'",
     "The quantization method is fine-grained `fp8` quantization with block size of 128.",
     "documentation (methods row; never a verdict)", "VERIFIED-BLOG", "model card (Hugging Face)", "-"),
    ("92e-Eaj", "E", "vLLM-FP8-W8A8-docs", "vllm_fp8_w8a8_docs", "https://docs.vllm.ai/en/stable/features/quantization/llm_compressor/fp8/", "'2. Applying Quantization'",
     "Dynamic, per-token quantization on the activations",
     "documentation (what W8A8 FP8_DYNAMIC means; never a verdict)", "VERIFIED-BLOG", "vLLM documentation (stable)", "-"),
    ("92e-Eak", "E-attribution", "Azizi2026-SharpDirections", "neurips2026_poster_151909", "https://neurips.cc/virtual/2026/poster/151909", "Abstract (NeurIPS 2026 poster page)",
     "Its top eigenvectors are sharp directions: tiny perturbations along them can cause large, erratic, input-dependent behavioral swings.",
     "context (why small numeric perturbations of a nudge can change behaviour; no precision factor)", "VERIFIED-ABSTRACT",
     "NeurIPS 2026 poster (Sat, Dec 12, 2026; OpenReview WyedqmCk4O); arXiv 2610.16084", "NeurIPS virtual poster page"),
    ("92e-Eam", "E-deployment", "Kurtic2025-GiveMeBF16", "2411.02355v4", ax("2411.02355", "v4"), "Sec. 1 (main findings)",
     "W8A8-FP quantization is essentially lossless, preserving the uncompressed model’s accuracy across all benchmarks, often within the evaluation’s margin of error. This result is achieved with a simple yet robust approach: dynamic per-token activation quantization combined with symmetric weight quantization via round-to-nearest assignment.",
     "supports the premise (default accuracy is preserved under per-token-scaled FP8 W8A8); no intervention", "VERIFIED", "ACL 2025 (arXiv comment)", "arXiv API comment 'Accepted to ACL 2025'"),
    ("92e-Eal", "E", "Anon2026-GLMDirectionalAblation", "abs_2609.09793", "https://arxiv.org/abs/2609.09793", "Abstract (arXiv abs page)",
     "We apply it to GLM-5.3-Flash (320B parameters, 288 routed experts, a four-wide hyper-connection residual, block-FP8).",
     "context (activation-direction edit on a block-FP8 checkpoint; no precision contrast)", "VERIFIED-ABSTRACT", "arXiv preprint (v1 9 Sep 2026)", "-"),
    # ---------------- LANE LL (FLAG L) ----------------
    ("92e-L1a", "L1a", "Meng2026-SparseButCritical", "2603.22446v1", ax("2603.22446", "v1"), "Sec. 4 (rank-shift analysis, Figure 22 discussion)",
     "Around 30% of RL top-1 tokens are already ranked first under the base model, and over 80% (DAPO) and 90% (SimpleRL) fall within the base top-3.",
     "adjacent (token-level, retrospective, no perturbation of the tuned model)", "VERIFIED",
     "ICLR 2026 (arXiv comment: 'Published as a conference paper at ... ICLR 2026')", "arXiv API comment"),
    ("92e-L1b", "L1a", "Meng2026-SparseButCritical", "2603.22446v1", ax("2603.22446", "v1"), "Sec. 4 (scope of the figure)",
     "This observation is further clarified in Figure 22, which shows where the RL model’s top-3 tokens appear in the base model’s ranking, among high divergence positions.",
     "adjacent (scope: high-divergence positions, JS > 0.1)", "VERIFIED", "ICLR 2026", "-"),
    ("92e-L1c", "L1b", "Meng2026-SparseButCritical", "2603.22446v1", ax("2603.22446", "v1"), "Abstract",
     "inserting only a small fraction of RL-sampled tokens into base generations progressively recovers RL performance gains, while injecting a similarly small number of base token choices into otherwise RL-generated sequences collapses performance to base levels",
     "adjacent (cross-sampling perturbs the tuned trajectory with base tokens; outcome is accuracy, not landing identity)", "VERIFIED", "ICLR 2026", "-"),
    ("92e-L1d", "L1b", "Giordani2025-ReEmergentMisalignment", "2507.03662v1", ax("2507.03662", "v1"), "Sec. 4.1 (Behavioral Analysis: Misaligned Model Reverts to Base Behavior)",
     "The aligned model (instruct) sharply suppresses the likelihood of the harmful generation. In contrast, both the base and misaligned models assign significantly higher probabilities to the same tokens. They do so with strikingly similar distributions.",
     "adjacent; FLAG L partly ((ii)+(iii) retrospective, sequence likelihood)", "VERIFIED", "arXiv preprint (v1, 4 Jul 2025)", "arXiv API comment empty"),
    ("92e-L1e", "L1a", "Giordani2025-ReEmergentMisalignment", "2507.03662v1", ax("2507.03662", "v1"), "Sec. 1 (Introduction)",
     "we propose that these behaviors can be better understood as a regression to base model behavior.",
     "adjacent; FLAG L partly", "VERIFIED", "arXiv preprint", "-"),
    ("92e-L1f", "L1a", "Giordani2025-ReEmergentMisalignment", "2507.03662v1", ax("2507.03662", "v1"), "App. B.2 (Table 2 caption; rendered next to App. A in the HTML)",
     "Values are averaged over a set of 400 examples from each dataset.",
     "adjacent (scale of the likelihood comparison)", "VERIFIED", "arXiv preprint", "-"),
    ("92e-L1g", "L1a", "Ji2025-ResistAlignment", "2406.06144v6", ax("2406.06144", "v6"), "Sec. 5 (How Elasticity Resists Alignment?)",
     "Fine-tuning in the opposite direction of post-training (e.g., safe vs. unsafe) causes post-trained models to return quickly to the pre-training distribution.",
     "adjacent; FLAG L partly ((i)+(ii) at distribution/score level, no tuned-model rival)", "VERIFIED", "ACL 2025 Main (arXiv comment)", "arXiv API comment 'Accepted by ACL2025 Main'"),
    ("92e-L1h", "L1a", "Huang2026-AlignmentDynamics", "2605.18309v1", ax("2605.18309", "v1"), "Sec. 3 (Revisiting Rebound Effect)",
     "The Rebound Effect [14] refers to the tendency of fine-tuned models to revert toward their pre-trained state under reversed or perturbed fine-tuning.",
     "adjacent (rebound dynamics)", "VERIFIED", "arXiv preprint (v1, 18 May 2026)", "arXiv API comment empty"),
    ("92e-L1i", "L1a", "Poppi2026-GravitationalReversion", "2606.28525v2", ax("2606.28525", "v2"), "Sec. 1 (Introduction)",
     "We instead cast it as a single activation-space direction, pointing from the safety-aligned model toward independently built helpful-only states rather than toward the base model itself, and fixed before the prospective target trajectories are trained",
     "adjacent; FLAG L partly ((i)+(ii) prospective; rival is a matched geometric null)", "VERIFIED",
     "arXiv preprint (v2, 28 Sep 2026; retitled)", "arXiv API title at v2"),
    ("92e-L1j", "L1b", "Poppi2026-GravitationalReversion", "2606.28525v2", ax("2606.28525", "v2"), "Sec. 1 (Introduction)",
     "once we fixed the reference family and the test in advance, every additional trajectory we tried moved in the predicted direction more than its matched null",
     "adjacent (prospective test against a matched null, not against the tuned model's tail)", "VERIFIED", "arXiv preprint", "-"),
    ("92e-L1k", "L1b", "Zhao2025-WeakToStrongJailbreak", "2401.17256v5", ax("2401.17256", "v5"), "Sec. 1 (Introduction)",
     "We observe that the top-ranked tokens in jailbroken LLMs are largely found within the top ten tokens ranked by safe LLMs.",
     "contradicts-in-part (the perturbed landing lies in the tuned model's OWN top-10: supports the q_lik rival at token level)", "VERIFIED",
     "ICML 2025 (arXiv comment)", "arXiv API comment 'ICML 2025'"),
    ("92e-L1l", "L1b", "Nadaf2026-PersonaSubspace", "2607.21356v1", ax("2607.21356", "v1"), "Fig. 1 caption",
     "A persona subspace present in the model before fine-tuning carries broad misalignment. The subspace is extracted from the frozen instruction-tuned model.",
     "contradicts-in-part (structure in the TUNED model forecasts where fine-tuning lands)", "VERIFIED", "arXiv preprint (v1, 23 Jul 2026)", "-"),
    ("92e-L1m", "L1b", "Nadaf2026-PersonaSubspace", "2607.21356v1", ax("2607.21356", "v1"), "Sec. 9 (Limitations: Provenance)",
     "Provenance. The extraction is from a released instruction-tuned checkpoint, not a pre-alignment base model, so whether pretraining installed the structure or alignment post-training sharpened it is open.",
     "contradicts-in-part (base vs tuned provenance left open)", "VERIFIED", "arXiv preprint", "-"),
    ("92e-L1n", "L1b", "Li2026-EMNotMagical", "2608.29118v1", ax("2608.29118", "v1"), "Sec. 1 (Introduction)",
     "the representational distance between an evaluation prompt and the training data centroid, both in the base model’s activation space, strongly predicts how misaligned the finetuned model becomes on that prompt",
     "context / contradicts-in-part ('base model' here = the pre-EM instruct model: a forecast from the tuned model itself)", "VERIFIED",
     "arXiv preprint (v1, 29 Aug 2026)", "-"),
    ("92e-L1o", "L1b", "Li2026-EMNotMagical", "2608.29118v1", ax("2608.29118", "v1"), "Sec. 3 (Emergent Misalignment is Expected Generalization: Models and EM Training Data)",
     "We select models of various sizes and from multiple model families: Qwen2.5-14B-Instruct, Qwen2.5-32B-Instruct, Qwen2.5-Coder-32B-Instruct",
     "context (terminology: the forecasting 'base model' is instruction-tuned)", "VERIFIED", "arXiv preprint", "-"),
    ("92e-L1p", "L1a", "Anon2026-PredictiveMIPostTraining", "or_BEcwcRFQdu", orsearch(T_PREDMI), "Abstract (OpenReview API record)",
     "We instead seal a per-head, signed forecast from the base model, fine-tune, and confirm it.",
     "adjacent (method-overlap: sealed forecasts from the base model; target is circuit change under post-training, not landing)",
     "VERIFIED-ABSTRACT", "ICLR 2027 Conference Submission", "OpenReview venue field"),
    ("92e-L1q", "L1a", "Zhou2024-EmulatedDisalignment", "2402.12343v4", ax("2402.12343", "v4"), "Abstract",
     "our method achieves this reversal by contrasting the output token distribution of a safety-aligned language model (e.g., Llama-2-chat) against its pre-trained version (e.g., Llama-2), so that the token predictions are shifted towards the opposite direction of safety alignment.",
     "adjacent (base-vs-aligned contrast pushes the aligned model; no landing forecast)", "VERIFIED", "ACL 2024 (arXiv comment)", "arXiv API comment 'ACL 2024'"),
    ("92e-L2a", "L2", "MousaviHosseini2026-BaseModelBarrier", "2603.06957v2", ax("2603.06957", "v2"), "Abstract",
     "However, a barrier arises for going beyond the support of the base model.",
     "supports (theory: policy-gradient post-training stays within base support)", "VERIFIED",
     "ICML 2026 (arXiv comment: 'Published at the International Conference on Machine Learning (ICML) 2026')", "arXiv API comment"),
    ("92e-L3a", "L3", "Karan2025-ReasoningWithSampling", "2510.14901v1", ax("2510.14901", "v1"), "Sec. 1 (contributions)",
     "We introduce the power distribution as a useful sampling target for reasoning tasks. Since it can be explicitly specified with a base LLM, no additional training is required.",
     "supports (stylised power account p^alpha of the base)", "VERIFIED", "arXiv preprint (v1, 16 Oct 2025)", "arXiv API comment empty"),
    ("92e-L3b", "L3", "Karan2025-ReasoningWithSampling", "2510.14901v1", ax("2510.14901", "v1"), "Fig. 1 caption",
     "Our algorithm achieves comparable performance to GRPO within the posttraining domain (MATH500) but can outperform on out-of-domain tasks such as HumanEval and AlpacaEval.",
     "supports", "VERIFIED", "arXiv preprint", "-"),
    # ---------------- LANE LS (site, forks, margins) ----------------
    ("92e-Sa", "S-a", "Wen2026-EmbeddingPerturbationUncertainty", "2602.02427v4", ax("2602.02427", "v4"), "Sec. 3.2 (Random Perturbation)",
     "Embedding perturbation does not disrupt reasoning coherence.",
     "adjacent (content-free Gaussian noise on token embeddings localises uncertain steps; no site comparison at matched dose)", "VERIFIED",
     "arXiv preprint (v4, 5 Oct 2026)", "arXiv API comment empty"),
    ("92e-Sb", "S-a", "Wen2026-EmbeddingPerturbationUncertainty", "2602.02427v4", ax("2602.02427", "v4"), "Sec. 3.2",
     "We find that the resulting continuations remain coherent and on-task.",
     "adjacent", "VERIFIED", "arXiv preprint", "-"),
    ("92e-Sc", "S-c", "Nguyen2026-ForksInTheRoad", "2605.17026v2", ax("2605.17026", "v2"), "Sec. 4.2 (Reasoning Mode Selection)",
     "reasoning mode selection is driven by weak signals, making it a key source of instability and side effects such as coverage collapse, but also a natural point of intervention for control.",
     "adjacent (decision-point fork between natural-language and code reasoning modes)", "VERIFIED", "arXiv preprint (v2, 1 Sep 2026)", "-"),
    ("92e-Sd", "F2", "Nguyen2026-ForksInTheRoad", "2605.17026v2", ax("2605.17026", "v2"), "Sec. 5 (First-token Manipulation; App. C prefix perturbation vs temperature)",
     "We find that targeted prefix perturbation consistently outperforms temperature scaling across both model families, particularly for moderate sampling budgets (pass@8–32)",
     "adjacent (prefix perturbation at forks beats temperature)", "VERIFIED", "arXiv preprint", "-"),
    ("92e-Fa", "F1", "Bigelow2025-ForkingPaths", "2412.07961v1", ax("2412.07961", "v1"), "Abstract",
     "We hypothesize that there exist key forking tokens, such that re-sampling the system at those specific tokens, but not others, leads to very different outcomes.",
     "adjacent (forks by resampling; outcome distributions)", "VERIFIED", "ICLR 2025 poster", "https://iclr.cc/virtual/2025/poster/30769 ('2025 Poster')"),
    ("92e-Fb", "F1", "Bigelow2025-ForkingPaths", "2412.07961v1", ax("2412.07961", "v1"), "Abstract",
     "We find many examples of forking tokens, including surprising ones such as punctuation marks, suggesting that LLMs are often just a single token away from saying something very different.",
     "adjacent", "VERIFIED", "ICLR 2025", "-"),
    ("92e-Fc", "F1", "Bigelow2026-ForkingFast", "2608.19611v1", ax("2608.19611", "v1"), "Sec. 1 (contributions)",
     "This model uses change point detection to identify forking points, and kernel-pooling to smooth estimates between these points.",
     "adjacent (efficient fork estimation)", "VERIFIED", "arXiv preprint (v1, 20 Aug 2026)", "-"),
    ("92e-Fd", "F1", "Bogdan2025-ThoughtAnchors", "2506.19143v4", ax("2506.19143", "v4"), "Abstract",
     "We term these sentences thought anchors. These are generally planning or uncertainty management sentences, and specialized attention heads consistently attend from subsequent sentences to thought anchors.",
     "adjacent (sentence-level resampling importance)", "VERIFIED", "arXiv preprint (v4, 27 Oct 2025; no venue found)", "arXiv API comment lists equal contribution only"),
    ("92e-Fe", "F1", "Zhou2026-LockedAtEntrance", "2608.29188v1", ax("2608.29188", "v1"), "Abstract",
     "we analyze the Countdown task, whose solution space can be exhaustively enumerated into discrete entrance families defined by the first operand and operator",
     "adjacent (entrance = first decision; correction: now on arXiv)", "VERIFIED",
     "arXiv preprint 2608.29188 v1 (29 Aug 2026; comment 'Preprint'); also ICLR 2027 submission hu5mtofNd4", "arXiv API"),
    ("92e-Ff", "F1", "Ko2026-CliffTokens", "2606.25524v3", ax("2606.25524", "v3"), "Sec. 1 (Introduction)",
     "We define the cliff token: the token in a reasoning trace where the probability of reaching the correct answer via Monte Carlo rollouts (success probability) drops significantly.",
     "adjacent", "VERIFIED", "arXiv preprint (v3, 28 Sep 2026)", "-"),
    ("92e-Fg", "F1", "Wang2025-HighEntropyMinority", "2506.01939v2", ax("2506.01939", "v2"), "Abstract",
     "These findings highlight the significance of high-entropy tokens (i.e., forking tokens) to RLVR.",
     "adjacent", "VERIFIED", "NeurIPS 2025 (arXiv comment)", "arXiv API comment 'Accepted to NeurIPS 2025'"),
    ("92e-Fh", "F2", "Tang2025-TopNSigma", "2411.07641v1", ax("2411.07641", "v1"), "Abstract",
     "that inadvertently include more noise tokens at higher temperatures, [...] maintains a stable sampling space regardless of temperature scaling.",
     "supports (a logit gap separates an informative region whose membership is temperature-invariant)", "VERIFIED",
     "ACL 2025 Long (retitled 'Top-nσ: Eliminating Noise in Logit Space for Robust Token Sampling of LLM')", "https://aclanthology.org/2025.acl-long.528/ ('Anthology ID: 2025.acl-long.528')"),
    ("92e-Fi", "F2", "Renze2024-TemperatureProblemSolving", "2402.05201v3", ax("2402.05201", "v3"), "Abstract",
     "our empirical results indicate that changes in temperature from 0.0 to 1.0 do not have a statistically significant impact on LLM performance for problem-solving tasks.",
     "supports (temperature-inert regime, accuracy outcome)", "VERIFIED", "Findings of EMNLP 2024", "arXiv journal_ref"),
    ("92e-Fj", "F2", "Du2026-GreedyNotPrecisionInvariant", "2609.26621v1", axpdf("2609.26621", "v1"), "Abstract (PDF p. 1)",
     "the outcome depends primarily on the top-two logit margin at the lm_head",
     "adjacent (margin explains numerics-induced flips, not temperature)", "VERIFIED", "TMLR 2026", "-"),
    ("92e-Fk", "F2", "Chu2026-MarginGate", "2605.30218v1", ax("2605.30218", "v1"), "Abstract",
     "K/V perturbations remain flat before flips, while low top-1/top-2 logit margins expose much of the flip risk.",
     "adjacent (margins predict flips)", "VERIFIED", "arXiv preprint (v1, 28 May 2026)", "-"),
    ("92e-Fl", "F2", "Patodiya2026-SameRequestDifferentAnswer", "2609.04748v2", ax("2609.04748", "v2"), "Abstract",
     "Near-tie decisions became only about 1.2 times as common, while the cache-path change in top-two margins grew 4.9-fold from 16-bit to three-bit.",
     "adjacent", "VERIFIED", "arXiv preprint", "-"),
    # ---------------- LANE LK (knobs) ----------------
    ("92e-Ka", "K", "Wortsman2022-WiSEFT", "2109.01903v3", ax("2109.01903", "v3"), "Fig. 1 caption",
     "Our method linearly interpolates between the zero-shot and fine-tuned models with a mixing coefficient",
     "context (definition of lambda interpolation)", "VERIFIED", "CVPR 2022", "arXiv comment 'CVPR 2022'"),
    ("92e-Kb", "K", "Lin2024-AlignmentTax", "2309.06256v4", ax("2309.06256", "v4"), "Abstract",
     "In this paper we show that model averaging, which simply interpolates between pre and post RLHF model weights, surprisingly achieves the most strongest alignment-forgetting Pareto front among a wide range of competing methods.",
     "adjacent (base/aligned weight interpolation as a knob; outcome is forgetting, not diversity)", "VERIFIED", "EMNLP 2024 Main", "arXiv comment 'EMNLP 2024 Main'"),
    ("92e-Kc", "K", "Anon2026-SFTFamiliarMerging", "or_MYXgOex05m", orsearch(T_FAMILIAR), "Abstract (OpenReview API record)",
     "To mitigate this effect, we propose a simple recovery approach: merging the fine-tuned model with its pretrained base model before RL.",
     "adjacent (base/fine-tuned merging restores diversity; code-generation benchmarks)", "VERIFIED-ABSTRACT",
     "ICLR 2027 Conference Submission", "OpenReview venue field"),
    ("92e-Kd", "K", "Zhou2026-LockedAtEntrance", "2608.29188v1", ax("2608.29188", "v1"), "App. (Intervention definitions)",
     "Layer interpolation replaces blocks 20–28 by the midpoint of their step-50 and step-275 parameters.",
     "adjacent (interpolation between RL checkpoints, not base/instruct)", "VERIFIED", "arXiv preprint", "-"),
    ("92e-Ke", "K", "Mitchell2024-EFT", "venue_eft_iclr2024", "https://proceedings.iclr.cc/paper_files/paper/2024/hash/389e161125965c0f0ba50420fee45774-Abstract-Conference.html",
     "ICLR 2024 proceedings page", "International Conference on Learning Representations 2024 (ICLR 2024)",
     "venue confirmation (correction to 92d 'venue unconfirmed')", "VERIFIED-ABSTRACT", "ICLR 2024", "proceedings.iclr.cc"),
]

VENUE_PAGES = [  # venue-confirmation quotes (kept in the same file, row 'venue')
    ("venue", "-", "Yuan2025-GiveMeFP32", "venue_givemefp32_neurips2025", "https://neurips.cc/virtual/2025/oral/118170", "page header",
     "Understanding and Mitigating Numerical Sources of Nondeterminism in LLM Inference", "venue confirmation", "VERIFIED-ABSTRACT", "NeurIPS 2025 oral", "-"),
    ("venue", "-", "Lin2024-URIAL", "venue_urial_iclr2024", "https://iclr.cc/virtual/2024/poster/17473", "page header",
     "The Unlocking Spell on Base LLMs: Rethinking Alignment via In-Context Learning", "venue confirmation (correction to 92d)", "VERIFIED-ABSTRACT", "ICLR 2024 poster", "-"),
    ("venue", "-", "Bigelow2025-ForkingPaths", "venue_forkingpaths_iclr2025", "https://iclr.cc/virtual/2025/poster/30769", "page header",
     "Forking Paths in Neural Text Generation", "venue confirmation", "VERIFIED-ABSTRACT", "ICLR 2025 poster", "-"),
    ("venue", "-", "Tang2025-TopNSigma", "venue_topnsigma_acl2025", "https://aclanthology.org/2025.acl-long.528/", "Anthology record",
     "Anthology ID: 2025.acl-long.528", "venue confirmation (retitled at ACL)", "VERIFIED-ABSTRACT", "ACL 2025 Long", "-"),
]


def heading_before(text, pos):
    best = ""
    for m in re.finditer(r"^#{1,6} [^\n]{2,120}$", text[:pos], re.M):
        best = m.group(0).lstrip("# ").strip()
    return best


def main():
    out = EVID / "quotes_iter6.jsonl"
    out.write_text("")
    ok = bad = 0
    for row, claim, ref, ck, url, sec, quote, rel, status, venue, vev in Q + VENUE_PAGES:
        try:
            text = load_text(ck)
        except FileNotFoundError:
            text = ""
        tn = normalise(text)
        match = bool(text) and quote_matches(quote, tn)
        seg0 = normalise(re.split(r"\s*\[\.\.\.\]\s*", quote)[0])[:60]
        pos_norm = tn.find(seg0)
        auto = ""
        if match and pos_norm >= 0:
            # map back approximately: search the raw text for the first 40 chars of the first segment
            probe = re.escape(seg0[:30]).replace(r"\ ", r"\s+")
            m = re.search(probe, text)
            if m:
                auto = heading_before(text, m.start())
        aid = re.match(r"(\d{4}\.\d{4,5})(v\d+)?", ck)
        meta = META.get(aid.group(1)) if aid else None
        rec = {"row": row, "claim": claim, "ref_key": ref, "cache_key": ck, "url": url, "section": sec, "auto_section": auto,
               "quote": quote, "relation": rel, "status": status if match else "UNVERIFIED", "status_target": status,
               "venue_status": venue, "venue_evidence": vev, "retrieved": RET,
               "arxiv_id": aid.group(1) if aid else "", "version_quoted": (aid.group(2) or "") if aid else "",
               "latest_version": meta["latest_version"] if meta else "", "v1_date": meta["v1_published"][:10] if meta else "",
               "title_at_latest_version": meta["title"] if meta else "", "first_author": (meta["authors"][0] if meta and meta["authors"] else ""),
               "n_authors": len(meta["authors"]) if meta else None}
        append_jsonl(out, rec)
        if match:
            ok += 1
        else:
            bad += 1
            print(f"NO MATCH: {row} {ck} :: {quote[:90]}")
    print(f"quotes written: {ok + bad}; verified against cache: {ok}; unverified: {bad}")


if __name__ == "__main__":
    main()
