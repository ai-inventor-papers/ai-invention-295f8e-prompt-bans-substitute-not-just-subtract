"""Step 3: score hits on the frozen O/I/C rubric (evidence/protocol_iter6.json), write the flag verdicts, the manual
screening verdicts and the correction log.

Writes evidence/scored_hits_iter6.jsonl, evidence/flags_iter6.json, evidence/manual_screen_iter6.json,
evidence/corrections_iter6.jsonl. Scores are the single screener's (one agent) judgement from the verified text named in
'decisive' (a 92e row id = a quote in evidence/quotes_iter6.jsonl, or an inherited 92b-92d row); every axis value is
published so a reader can re-score. Usage: python -I tools/write_scores_iter6.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import EVID, now_utc  # noqa: E402

# id, short title, claim scored, O, I, C, relation, flag ('E','L','S','K' or ''), decisive row(s), status, v1/venue, round
S = [
    # ---- LE ----
    ("OR:8iTqrW1sxY", "Stable Directions, Different Effects: Intervention Fidelity Across Model Precision", "E", 1, 0.5, 1,
     "occupies the general claim; precision factor (weight vs activation) not stated in the abstract", "E", "92e-Ee;92e-Ef",
     "VERIFIED-ABSTRACT", "ICLR 2027 desk-rejected submission (contemporaneous)", "R1 (E5)"),
    ("OR:h57duZqLOr", "Activation Steering under Low-Bit Quantization: A Geometric Perspective on Degradation and Recovery", "E", 1, 0.5, 1,
     "occupies the general claim; scheme not stated (calibration/reconstruction wording suggests weight PTQ)", "E", "92e-Eg;92e-Eh",
     "VERIFIED-ABSTRACT", "ICLR 2027 submission (contemporaneous); seen in iteration 5 under another question", "R1 (E5)"),
    ("2510.23264", "PAHQ: Accelerating Automated Circuit Discovery through Mixed-Precision Inference Optimization", "E", 0.5, 0.5, 1,
     "adjacent; FLAG E partly (weights AND activations quantised together, FP32 vs 8-bit RTN; outcome = circuit-recovery AUC on GPT-2-scale models)",
     "E", "92e-Ei;92e-Ej;92e-Ek", "VERIFIED", "arXiv v1 2025-10-27; no venue", "R1 (E6)"),
    ("2609.06473", "Steering Under Compression", "E", 1, 0.5, 0.5,
     "adjacent; FLAG E partly (weight-only bitsandbytes INT8/NF4, activations FP16/BF16; vectors recomputed per scheme)", "E",
     "92e-Ea;92e-Eb;92e-Ec;92e-Ed", "VERIFIED", "arXiv v1 2026-09-06; contemporaneous_4mo", "seed + R1"),
    ("2610.20808", "PRISM: Transfer and Limits of Activation Interventions in Tool-Calling Language Models", "E", 1, 0.5, 0.5,
     "adjacent; FLAG E partly (weight-only NF4 copies supply labels; directions act on BF16)", "E", "92e-Eo;92e-Ep",
     "VERIFIED", "arXiv v1 2026-10-14; contemporaneous_4mo", "R1 (E1,E4)"),
    ("doi:10.3390/computation14090212", "Float32-Induced Distortion in Activation Patching", "E", 0.5, 0, 0.5,
     "adjacent (fp32 vs fp64 numerics change interaction-level patching estimates; internal outcome; not activation quantisation)",
     "E", "92e-El", "VERIFIED-ABSTRACT", "Computation (MDPI) 2026-09-09", "R1 (E4)"),
    ("OR:6t1egKiB0v", "Quantization-Induced Decision Changes Have Regime-Dependent Intervention Spectra", "E", 0.5, 0.5, 0.5,
     "adjacent (activation additions used to repair quantisation flips)", "", "92e-Em", "VERIFIED-ABSTRACT", "ICLR 2027 submission", "R1 (E5)"),
    ("OR:GYm4mg9yGQ", "When Quantization Helps: Corrective Computation in Low-Bit Language Models", "E", 0.5, 0.5, 0.5,
     "adjacent (weight-only GPTQ/AWQ/NF4; patching analyses quantisation-induced changes)", "", "92e-En", "VERIFIED-ABSTRACT", "ICLR 2027 submission", "R1 (E5)"),
    ("2604.09839", "Steered LLM Activations are Non-Surjective (INT4 check)", "E", 0.5, 0.5, 0.5,
     "context (internal claim survives an INT4 model)", "", "92e-Eq", "VERIFIED", "ICLR 2026 workshops", "seed (inherited 92b-b7c)"),
    ("2606.09864", "Alignment Collapse Under KV Cache Quantization", "E-deployment", 0.5, 1, 1,
     "occupies the GENERAL deployment statement (activation-side KV quantisation silently changes refusals at ~flat perplexity); not the nudgeability claim",
     "", "92e-Er;92e-Es", "VERIFIED", "arXiv v1 2026-06-01", "R1 (E3)"),
    ("2407.09141", "Accuracy is Not All You Need", "E-deployment", 0.5, 0.5, 1,
     "adjacent (flips at matched accuracy)", "", "92e-Eab", "VERIFIED", "NeurIPS 2024", "seed"),
    ("2608.13756", "The Integer Alibi: Localizing Cross-Kernel Divergence in INT8-Quantized LLM Inference", "E", 0.5, 0.5, 1,
     "adjacent (W8A8 INT8 kernel swap at fixed config changes every sequence; reviewer baseline)", "", "92e-Ey", "VERIFIED", "arXiv v1 2026-08-13", "R1 (E1,E3,FC)"),
    ("2609.04748", "Same Request, Different Answer: Quantization Amplifies Cache-Induced Divergence", "E-attribution", 0.5, 0.5, 1,
     "adjacent (weights-vs-execution-path control for divergence)", "", "92e-Ez;92e-Fl", "VERIFIED", "arXiv v1 2026-09-04", "R1 (E1,FC)"),
    ("2609.26621", "Greedy Decoding Is Not Precision-Invariant", "E", 0.5, 0, 1,
     "adjacent for E (numerics; no activation-level intervention)", "", "92e-Eaa", "VERIFIED", "TMLR 2026", "R1 (all engines)"),
    ("2506.09501", "Give Me FP32 or Give Me Death? / Understanding and Mitigating Numerical Sources of Nondeterminism", "E", 0.5, 0, 0.5,
     "adjacent (numerics change outputs; no intervention)", "", "92e-Ev", "VERIFIED", "NeurIPS 2025 oral", "seed"),
    ("blog:thinkingmachines-nondeterminism", "Defeating Nondeterminism in LLM Inference", "E", 0.5, 0, 0.5,
     "context (batch invariance)", "", "92e-Ew;92e-Ex", "VERIFIED-BLOG", "blog 2025-09-10", "seed"),
    ("propor:2026.propor-1.108", "Lost in Quantization (PROPOR 2026)", "E-attribution", 0.5, 0.5, 0.5,
     "adjacent (naive unscaled E4M3 casting vs INT8 with outlier handling; no intervention)", "", "92e-Et;92e-Eu", "VERIFIED", "PROPOR 2026", "seed"),
    ("OR:70RbLmZVvW", "SafeQ: Safety Alignment Preserving Post-Training Quantization", "E-deployment", 0.5, 0.5, 0.5,
     "adjacent (W4A4 includes activation quantisation; safety behaviour; no intervention)", "", "abstract only (not quoted)", "screened (abstract)", "ICLR 2027 submission", "R2"),
    ("OR:5R8LqE51Hr", "Better Fixed-State Fidelity Need Not Improve Closed-Loop Performance in Quantized Neural Policies", "E-deployment", 0.5, 0.5, 0.5,
     "adjacent (analogue in quantised control policies)", "", "abstract only (not quoted)", "screened (abstract)", "ICLR 2027 submission", "R2"),
    ("2610.24346", "Measuring the Task Value of Precision Upgrades in Closed-Loop Agents", "E-deployment", 0, 0.5, 1,
     "adjacent (BF16 action fallback in 4-bit-weight agents)", "", "abstract only (not quoted)", "screened (abstract)", "arXiv v1 2026-10-17", "R3 (FC)"),
    ("2607.27275", "Flat Score, Amplified Failures: How the Error Budget Masks Damage in Quantized LLM Agents", "E-deployment", 0.5, 0.5, 0.5,
     "adjacent (4-bit weights; flat score hides process damage)", "", "abstract only (not quoted)", "screened (abstract)", "arXiv v1 2026-07-29", "R4 (BC)"),
    ("2606.19558", "Displacement Is Not Direction: Evaluating Fidelity Metrics for Quantized LLM Deployment", "E-deployment", 0.5, 0.5, 0.5,
     "adjacent (fidelity metrics fail near baseline)", "", "abstract only (not quoted)", "screened (abstract)", "arXiv v1 2026-06-17", "R4 (BC)"),
    ("2609.09793", "How Fragile Is Safety Alignment at Frontier Scale? (block-FP8 320B MoE)", "E", 1, 0, 0,
     "context (activation-direction edit on a block-FP8 checkpoint, no precision contrast)", "", "92e-Eal", "VERIFIED-ABSTRACT", "arXiv v1 2026-09-09", "R1 (E1,E3)"),
    ("neurips2026:151909", "The Sharp Directions Are Against You: Curvature Analysis of Activation Steering", "E-attribution", 0.5, 0, 0.5,
     "context (tiny perturbations along sharp directions cause large behaviour swings; no precision factor)", "", "92e-Eak", "VERIFIED-ABSTRACT", "NeurIPS 2026 poster", "seed (E-8) + R2"),
    ("2411.02355", "'Give Me BF16 or Give Me Death'? Accuracy-Performance Trade-Offs in LLM Quantization", "E-deployment", 0, 1, 1,
     "adjacent / supports the premise (per-token-scaled FP8 W8A8 is accuracy-lossless on Llama-3.1); no intervention", "", "92e-Eam", "VERIFIED", "ACL 2025", "flag-candidate lookup (WebSearch)"),
    ("2604.14090", "From Weights to Activations: Is Steering the Next Frontier of Adaptation?", "E", 0, 0, 0,
     "irrelevant (position paper on steering as adaptation; no precision factor; resolves an E1 record that had no abstract)", "", "full text screened (not quoted)", "screened (full text)", "ACL 2026 Main", "R2 (E1) + lookup"),
    ("2211.10438", "SmoothQuant", "E-attribution", 0, 0.5, 0, "context (mechanism anchor)", "", "92e-Eac", "VERIFIED", "ICML 2023", "seed"),
    ("2208.07339", "LLM.int8()", "E-attribution", 0, 0.5, 0, "context (mechanism anchor)", "", "92e-Ead", "VERIFIED", "NeurIPS 2022", "seed"),
    ("2402.17762", "Massive Activations in Large Language Models", "E-attribution", 0, 0.5, 0, "context (mechanism anchor)", "", "92e-Eae;92e-Eaf", "VERIFIED", "COLM 2024", "seed"),
    ("2403.15447", "Decoding Compressed Trust", "E-deployment", 0.5, 0.5, 0, "context", "", "92e-Eah", "VERIFIED", "ICML 2024", "seed"),
    # ---- LL ----
    ("2507.03662", "Re-Emergent Misalignment", "L1b", 0.5, 0.5, 0.5,
     "adjacent; FLAG L partly ((ii)+(iii) retrospective: misaligned outputs carry base-like likelihoods that the instruct model suppresses)", "L",
     "92e-L1d;92e-L1e;92e-L1f", "VERIFIED", "arXiv v1 2025-07-04", "seed (L-7)"),
    ("2406.06144", "Language Models Resist Alignment: Evidence From Data Compression", "L1a", 0.5, 0.5, 0,
     "adjacent; FLAG L partly ((i)+(ii) at distribution/score level; no tuned-model rival)", "L", "92e-L1g", "VERIFIED", "ACL 2025 Main", "seed (L-8)"),
    ("2605.18309", "Alignment Dynamics in LLM Fine-Tuning", "L1a", 0.5, 0.5, 0, "adjacent (rebound dynamics)", "L", "92e-L1h", "VERIFIED", "arXiv v1 2026-05-18", "seed (L-8) + E6"),
    ("2606.28525", "A Gravitational Interpretation of Safety Reversion under Fine-Tuning", "L1a", 0.5, 0.5, 0.5,
     "adjacent; FLAG L partly ((i)+(ii) prospective, direction toward base-descended helpful-only states; rival is a matched geometric null)", "L",
     "92e-L1i;92e-L1j", "VERIFIED", "arXiv v1 2026-06-26 (v2 retitled)", "R1 (E6)"),
    ("2603.22446", "Sparse but Critical", "L1a", 1, 1, 0,
     "adjacent (token-level, retrospective; no perturbation of the tuned model)", "L", "92e-L1a;92e-L1b;92e-L1c", "VERIFIED", "ICLR 2026", "seed (L-4)"),
    ("2401.17256", "Weak-to-Strong Jailbreaking on Large Language Models", "L1b", 1, 0, 0.5,
     "contradicts-in-part (perturbed landing lies inside the tuned model's own top-10)", "", "92e-L1k", "VERIFIED", "ICML 2025", "seed (L-9)"),
    ("2607.21356", "Emergent Misalignment Recruits a Pre-existing Persona Subspace", "L1b", 0.5, 0, 1,
     "contradicts-in-part (forecast from the tuned model's own subspace; matched random-subspace null)", "", "92e-L1l;92e-L1m", "VERIFIED", "arXiv v1 2026-07-23", "R1 (E4)"),
    ("2608.29118", "Emergent Misalignment Is Not Magical", "L1b", 0.5, 0, 0.5,
     "context (per-prompt forecast from the pre-EM instruct model; 'base model' = pre-fine-tune model)", "", "92e-L1n;92e-L1o", "VERIFIED", "arXiv v1 2026-08-29", "R1 (E6)"),
    ("OR:BEcwcRFQdu", "Predictive Mechanistic Interpretability of Post-Training", "L1a", 0.5, 1, 0.5,
     "adjacent (method-overlap: sealed base-model forecasts of which heads change)", "", "92e-L1p", "VERIFIED-ABSTRACT", "ICLR 2027 submission", "R1 (E5)"),
    ("OR:xmDdTDx241", "AlignRadar: Forecasting Emergent-Misalignment Risk Before Fine-Tuning", "L1a", 0.5, 0.5, 0.5,
     "adjacent (FLAG-B-type dataset-level forecast from the base model)", "", "abstract only (not quoted)", "screened (abstract)", "ICLR 2027 submission", "R1 (E5)"),
    ("2402.12343", "Emulated Disalignment", "L1a", 0.5, 0.5, 0, "adjacent", "", "92e-L1q", "VERIFIED", "ACL 2024", "seed (L-9)"),
    ("2603.06957", "Post-Training with Policy Gradients: Optimality and the Base Model Barrier", "L2", 0.5, 1, 0,
     "supports (theory)", "", "92e-L2a", "VERIFIED", "ICML 2026", "R1 (FC)"),
    ("2510.14901", "Reasoning with Sampling: Your Base Model is Smarter Than You Think", "L3", 0.5, 1, 0.5,
     "supports / adjacent (power distribution of the base matches GRPO in-domain)", "", "92e-L3a;92e-L3b", "VERIFIED", "arXiv v1 2025-10-16", "seed (L-6)"),
    ("2605.10781", "Rebellious Student (top-k overlap replication)", "L1a", 1, 1, 0,
     "adjacent (replicates Sparse-but-Critical overlap analysis)", "", "not quoted (math-rendered numbers)", "screened (full text)", "arXiv v1 2026-05-11", "R1 (E6)"),
    # ---- LS ----
    ("2412.07961", "Forking Paths in Neural Text Generation", "F1", 1, 1, 0, "adjacent", "", "92e-Fa;92e-Fb", "VERIFIED", "ICLR 2025", "seed (S-1)"),
    ("2608.19611", "Forking Fast", "F1", 1, 1, 0, "adjacent", "", "92e-Fc", "VERIFIED", "arXiv v1 2026-08-20", "seed (S-2)"),
    ("2506.19143", "Thought Anchors", "F1", 0.5, 1, 0, "adjacent", "", "92e-Fd", "VERIFIED", "arXiv v4 (no venue found)", "seed (S-3)"),
    ("2608.29188", "Locked at the Entrance, Open Inside", "F1", 1, 0.5, 0.5, "adjacent (entrance = first decision; coverage)", "", "92e-Fe;92e-Kd", "VERIFIED", "arXiv v1 2026-08-29 (+ ICLR 2027 submission)", "R1 (E3,FC)"),
    ("2605.17026", "Why Do Reasoning Models Lose Coverage? The Role of Data and Forks in the Road", "F2", 1, 0.5, 0.5,
     "adjacent (NL-vs-code reasoning-mode forks; prefix perturbation beats temperature)", "", "92e-Sc;92e-Sd", "VERIFIED", "arXiv v1 2026-05-16", "R1 (E3)"),
    ("2606.25524", "Cliff Tokens", "F1", 1, 1, 0, "adjacent", "", "92e-Ff", "VERIFIED", "arXiv v1 2026-06-24", "R1 (E1,E5,FC)"),
    ("2506.01939", "Beyond the 80/20 Rule: High-Entropy Minority Tokens", "F1", 0.5, 1, 0, "adjacent", "", "92e-Fg", "VERIFIED", "NeurIPS 2025", "seed (S-6)"),
    ("2411.07641", "Top-nσ", "F2", 0.5, 1, 0.5, "supports (logit gap; temperature-invariant candidate set)", "", "92e-Fh", "VERIFIED", "ACL 2025", "seed (S-6)"),
    ("2402.05201", "The Effect of Sampling Temperature on Problem Solving", "F2", 0.5, 0, 1, "supports (temperature-inert regime)", "", "92e-Fi", "VERIFIED", "Findings EMNLP 2024", "seed (S-6)"),
    ("2609.26621#F2", "Greedy Decoding Is Not Precision-Invariant (margin mechanism)", "F2", 1, 1, 0.5,
     "occupies the GENERAL statement that a top-two logit margin decides which decisions flip under a small perturbation (precision, not temperature)", "", "92e-Fj", "VERIFIED", "TMLR 2026", "R1"),
    ("2605.30218", "MarginGate", "F2", 1, 1, 0.5, "occupies the same general statement (numerics flips)", "", "92e-Fk", "VERIFIED", "arXiv v1 2026-05-28", "R1 (E1,E5,FC)"),
    ("2609.04748#F2", "Same Request, Different Answer (margins)", "F2", 0.5, 1, 0.5, "adjacent", "", "92e-Fl", "VERIFIED", "arXiv v1 2026-09-04", "R1"),
    ("2602.02427", "Uncertainty Localization in LLM Reasoning via Embedding Perturbations", "S-a", 0.5, 1, 0,
     "adjacent (content-free Gaussian noise on token embeddings; no site comparison at matched dose)", "S", "92e-Sa;92e-Sb", "VERIFIED", "arXiv v1 2026-02-02", "R1 (FC)"),
    # ---- LK ----
    ("OR:MYXgOex05m", "Should SFT Prefer the Familiar? Diversity Collapse and Recovery via Model Merging", "K", 0.5, 1, 0.5,
     "adjacent; FLAG K not fired (base/fine-tuned merging restores policy diversity incl. code generation; not algorithm-level labels)", "K", "92e-Kc",
     "VERIFIED-ABSTRACT", "ICLR 2027 submission", "R1 (E5)"),
    ("2309.06256", "Mitigating the Alignment Tax of RLHF", "K", 0, 1, 0.5, "adjacent (pre/post-RLHF weight averaging; forgetting outcome)", "", "92e-Kb", "VERIFIED", "EMNLP 2024", "seed (K-2)"),
    ("2109.01903", "Robust fine-tuning of zero-shot models (WiSE-FT)", "K", 0, 1, 0.5, "context (definition)", "", "92e-Ka", "VERIFIED", "CVPR 2022", "seed (K-2)"),
    ("2608.29188#K", "Locked at the Entrance (layer interpolation between RL checkpoints)", "K", 0.5, 0.5, 0.5, "adjacent", "", "92e-Kd", "VERIFIED", "arXiv 2026", "R1"),
]

FLAGS = {
    "protocol": "evidence/protocol_iter6.json (sha256 in evidence/protocol_iter6.sha256)",
    "dated": "search 2026-10-21 23:34 UTC .. 2026-10-22 ~00:05 UTC; verification 2026-10-21/22",
    "FLAG_E": {
        "definition": None,
        "verdict": "PARTLY FIRED",
        "summary": ("No verified full text isolates ACTIVATION quantisation and shows it changes the behavioural effect of an "
                    "activation-level intervention at matched weights, so FLAG E does not FIRE. It is PARTLY FIRED three ways: "
                    "(1) weight-only evidence (Steering Under Compression: bitsandbytes INT8/NF4, activations kept FP16/BF16; PRISM: NF4); "
                    "(2) joint weight+activation 8-bit RTN quantisation breaks activation-patching circuit discovery (PAHQ; FP32 vs 8-bit, "
                    "GPT-2-scale, circuit-recovery AUC); (3) two contemporaneous ICLR 2027 submissions report, at abstract level, that the "
                    "SAME steering intervention changes its behavioural effect across precision/low-bit quantisation while output fidelity "
                    "and direction similarity are preserved, without stating whether activations are quantised (OpenReview PDFs HTTP 403)."),
        "candidates": [],
        "consequence_for_wording": ("Claim E's 'deployment finding' must not be framed as new in its general form ('quantisation can "
                                    "change what a fixed activation intervention does although quality and direction similarity are "
                                    "preserved'): that is occupied (contemporaneous, abstract-level). Claim E may claim, dated and "
                                    "'to our knowledge': the activation-vs-weight attribution (2x2 W8A8/W8A16/W16A8/W16A16 factorial "
                                    "on identical hook code), a per-token-scaled FP8 W8A8 production engine (not unscaled casting or "
                                    "RTN), content-free random nudges at matched per-position dose with CRN slots, a categorical "
                                    "test-checked algorithm-choice outcome, and per-token absmax/FP8-scale readouts. If the full texts "
                                    "of OR:8iTqrW1sxY or OR:h57duZqLOr show activation quantisation, Claim E becomes a replication in "
                                    "a new setting (content-free nudges, code algorithm choice)."),
    },
    "FLAG_L": {
        "definition": None,
        "verdict": "PARTLY FIRED",
        "summary": ("No paper forecasts, from the base model, which enumerated alternative a perturbed TUNED model lands on and scores "
                    "that forecast against the tuned model's own sampled tail or likelihood ranking, so FLAG L does not FIRE. It is "
                    "PARTLY FIRED by fine-tuning-perturbation work on reversion toward base behaviour: Re-Emergent Misalignment "
                    "((ii)+(iii) retrospective, sequence likelihoods: the instruct model suppresses what base and misaligned models "
                    "share), Language Models Resist Alignment and Alignment Dynamics ((i)+(ii) at distribution/score level, no tuned "
                    "rival), and the Gravitational Interpretation of Safety Reversion ((i)+(ii) prospective, direction toward "
                    "base-descended helpful-only states, rival = matched geometric null). Token-level candidate preservation remains "
                    "adjacent (URIAL, Sparse but Critical, Same Candidates). Rival-supporting evidence exists: jailbroken landings lie "
                    "in the safe model's own top-10 (Weak-to-Strong), and an EM persona subspace extracted from the frozen tuned "
                    "model forecasts where fine-tuning lands (Nadaf 2026)."),
        "candidates": [],
        "consequence_for_wording": ("Not a replication. The 92d A2 sentence is updated: reversion of fine-tune-perturbed tuned models "
                                    "toward base behaviour is reported at distribution/likelihood level (retrospective, or prospective "
                                    "against a geometric null), and candidate preservation is reported at token level; to our knowledge "
                                    "(dated search), no work commits in advance to an algorithm-level landing forecast from the base "
                                    "composition and scores it against the tuned model's own likelihood ranking (q_lik) and sampled "
                                    "tail (q_tail), including tail-empty events. 'First' is not licensed."),
    },
    "FLAG_S_secondary": {"verdict": "NOT FIRED",
                         "summary": ("No paper compares sites (prefill task-spec states by layer band vs read position vs condition "
                                     "tokens vs generated tokens) for content-free perturbations at matched dose on a categorical "
                                     "solution choice. Closest: inherited site comparisons for narratives/test coverage (92c C1-site: "
                                     "Noise Steering, STARS App. B.3), Gaussian embedding perturbation for uncertainty localisation "
                                     "(2602.02427), prefix perturbation at reasoning-mode forks (2605.17026).")},
    "FLAG_K_secondary": {"verdict": "NOT FIRED",
                         "summary": ("No test-checked ALGORITHM-level code diversity under base/aligned interpolation, collaboration "
                                     "or proxy tuning. Closest: base-model merging restores policy diversity on code benchmarks "
                                     "(OR:MYXgOex05m, abstract), Hindsight Merging +20-50% pass@10 on code (92d), FrankenMerging "
                                     "lexical/semantic diversity (92d), BACo open-ended text (92d).")},
}

CORRECTIONS = [
    ("Locked at the Entrance, Open Inside", "cited in 92d (rows 92d-A0i, 92d-B1h) as an anonymous ICLR 2027 submission (VERIFIED-ABSTRACT, OpenReview hu5mtofNd4)",
     "on arXiv as 2608.29188 v1 (29 Aug 2026; Qiancheng Zhou and Ruizhe Li; comment 'Preprint'); full text verified in 92e-Fe/92e-Kd; layer interpolation is between RL checkpoints (blocks 20-28, midpoint of step-50 and step-275), not base/instruct"),
    ("A Gravitational Interpretation ... (2606.28525)", "search-engine listing title 'A Gravitational Interpretation of Fine-Tuning Reversion'",
     "arXiv v2 (28 Sep 2026) title: 'A Gravitational Interpretation of Safety Reversion under Fine-Tuning'"),
    ("Give Me FP32 or Give Me Death? (2506.09501)", "plan: NeurIPS 2025 oral per the virtual page (unverified)",
     "confirmed: NeurIPS 2025 oral page https://neurips.cc/virtual/2025/oral/118170 lists it under the v2 title 'Understanding and Mitigating Numerical Sources of Nondeterminism in LLM Inference'"),
    ("URIAL (2312.01552)", "92d: venue unconfirmed", "confirmed ICLR 2024 poster (https://iclr.cc/virtual/2024/poster/17473)"),
    ("EFT (2310.12962)", "92d: venue unconfirmed", "confirmed ICLR 2024 (proceedings.iclr.cc page)"),
    ("Proxy tuning (2401.08565)", "92d: venue unconfirmed", "arXiv v4 comment: 'COLM 2024 camera-ready' (author-stated; no venue page fetched)"),
    ("Top-nσ (2411.07641)", "arXiv title 'Top-nσ: Not All Logits Are You Need'",
     "published at ACL 2025 (Long) as 'Top-nσ: Eliminating Noise in Logit Space for Robust Token Sampling of LLM' (Anthology 2025.acl-long.528)"),
    ("Forking Paths (2412.07961)", "plan: ICLR 2025", "confirmed ICLR 2025 poster (https://iclr.cc/virtual/2025/poster/30769)"),
    ("Thought Anchors (2506.19143)", "plan: 'confirm venue'", "no venue found (arXiv v4, 27 Oct 2025; comment lists equal contribution only); cited as arXiv preprint"),
    ("Sparse but Critical (2603.22446)", "plan: the 30%/80%/90% figure sits in Sec. 4.1 'Top-k Overlap and Rank Reordering'",
     "confirmed in Sec. 4.1 of v1; the figures are restricted to high-divergence positions (JS > 0.1) and refer to the Figure 22 rank analysis"),
    ("Steering Under Compression (2609.06473)", "plan: 'CAA vectors recomputed per condition'",
     "confirmed: 'Steering vectors extracted independently per scheme (same contrast pairs, same resample)'; negative check: 'FP8' 0 hits, 'per-token' 0 hits, 'W8A8' 1 hit (Limitations: excluded by design)"),
    ("Lost in Quantization (PROPOR 2026)", "plan: English +18% vs PT-BR +3.9%; spikes > 35",
     "confirmed on the Anthology page/PDF; scope is naive unscaled E4M3 casting ('no calibration/scaling'), not per-token-scaled W8A8"),
    ("Emergent Misalignment Is Not Magical (2608.29118)", "search snippet: 'base-model activation space predicts EM'",
     "terminology: its 'base model' is the pre-EM INSTRUCT model (Qwen2.5-14B/32B-Instruct, Gemma-3-27B-IT, ...), i.e., a forecast from the tuned model itself"),
    ("Same Candidates (OpenReview ooV5M72O08), Before the First Token (knirOusGcq)", "plan: one PDF attempt each",
     "PDF attempts on 2026-10-21 returned HTTP 403 again; kept VERIFIED-ABSTRACT; the notes?id= API endpoint now returns 403 ChallengeRequiredError, the notes/search endpoint still serves abstracts"),
    ("Float32-Induced Distortion in Activation Patching (DOI 10.3390/computation14090212)", "found via S2 without URL",
     "publisher page (mdpi.com) returned HTTP 403; quoted from the Semantic Scholar API abstract record (VERIFIED-ABSTRACT)"),
    ("Steering Under Compression authors", "plan: 'Bhandari and Wade'", "confirmed by the arXiv API: Saurav Bhandari; Benjamin Wade"),
]


def main():
    out = EVID / "scored_hits_iter6.jsonl"
    out.write_text("")
    n = {"occupies": 0, "adjacent": 0, "irrelevant": 0}
    for (hid, title, claim, O, I, C, rel, flag, dec, status, venue, rnd) in S:
        tot = O + I + C
        verdict = "occupies" if tot >= 2.5 else ("adjacent" if tot >= 1 else "irrelevant")
        n[verdict] += 1
        rec = {"id": hid, "title": title, "claim_scored": claim, "O": O, "I": I, "C": C, "total": tot, "verdict": verdict,
               "relation": rel, "flag_candidate": flag, "decisive": dec, "text_status": status, "venue_or_date": venue,
               "found_in": rnd, "scored_utc": now_utc(), "screener": "single agent (Claude); see blind re-screen"}
        out.write_text(out.read_text() + json.dumps(rec, ensure_ascii=False) + "\n")
        for fk in ("E", "L"):
            if flag == fk:
                FLAGS[f"FLAG_{fk}"]["candidates"].append({k: rec[k] for k in ("id", "title", "claim_scored", "O", "I", "C", "total",
                                                                               "relation", "decisive", "text_status", "venue_or_date")})
    proto = json.loads((EVID / "protocol_iter6.json").read_text())
    FLAGS["FLAG_E"]["definition"] = proto["flags"]["FLAG_E"]
    FLAGS["FLAG_L"]["definition"] = proto["flags"]["FLAG_L"]
    (EVID / "flags_iter6.json").write_text(json.dumps(FLAGS, indent=1, ensure_ascii=False))
    cpath = EVID / "corrections_iter6.jsonl"
    cpath.write_text("".join(json.dumps({"item": a, "was": b, "now": c, "logged_utc": now_utc()}, ensure_ascii=False) + "\n"
                             for a, b, c in CORRECTIONS))
    print(f"scored hits: {len(S)} -> {n}; flags written; corrections: {len(CORRECTIONS)}")


if __name__ == "__main__":
    main()
