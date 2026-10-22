"""Log the E6 grey-literature calls (Claude Code built-in WebSearch, run by the agent, not by a script) into
evidence/search_log_iter6.jsonl and save their result lists as raw files in cache/search_results/ so that
sat_search_iter6.py --aggregate folds them into the de-duplicated candidate set.

The built-in tool does not timestamp calls; 'call_time_note' gives the window in which they were issued.
The domain filter is not strictly enforced by the tool (arXiv PDFs come back too); every returned URL is kept.
Usage: python -I tools/log_e6_iter6.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, EVID, append_jsonl, now_utc  # noqa: E402

GREY = "lesswrong.com, alignmentforum.org, transformer-circuits.pub, thinkingmachines.ai, blog.vllm.ai, docs.vllm.ai, pytorch.org, huggingface.co"
CALLS = [
    ("FE1", "activation quantization steering vector effect", GREY, [
        ("Steering Under Compression: Dose-Response, Capability Cost, and Failure Asymmetry in Quantized LLMs", "https://arxiv.org/pdf/2609.06473"),
        ("Activation Steering Induces Emergent Misalignment: A More Comprehensive Evaluation", "https://arxiv.org/pdf/2606.08682"),
        ("White-Box Sensitivity Auditing with Steering Vectors", "https://arxiv.org/pdf/2601.16398"),
        ("Forecasting Side Effects of Activation Steering", "https://arxiv.org/pdf/2608.11227"),
        ("Activation Steering with a Feedback Controller", "https://arxiv.org/pdf/2510.04309"),
        ("High-Dimensional Random Projection for Activation Steering in Language Models", "https://arxiv.org/pdf/2606.15092"),
        ("Steering GPT-2-XL by adding an activation vector", "https://www.lesswrong.com/posts/5spBue2z2tw4JuDCx/steering-gpt-2-xl-by-adding-an-activation-vector"),
        ("When Does Activation Steering Change What a Model Computes From?", "https://arxiv.org/pdf/2606.29522"),
        ("Steering Awareness: Detecting Activation Steering from Within", "https://arxiv.org/pdf/2511.21399")]),
    ("FE1", "FP8 activation quantization interpretability intervention", GREY, [
        ("Every Activation Boosted: Scaling General Reasoner to 1 Trillion Open Language Foundation", "https://arxiv.org/pdf/2510.22115"),
        ("The Llama 3 Herd of Models", "https://arxiv.org/pdf/2407.21783"),
        ("Daily Papers - Hugging Face (q=FP8 format)", "https://huggingface.co/papers?q=FP8+format"),
        ("FP8 W8A8 - vLLM", "https://docs.vllm.ai/en/stable/features/quantization/llm_compressor/fp8/"),
        ("Is INT8 Portable? A Cross-Platform Measurement Study of Quantized Inference on Embedded and Automotive Accelerators", "https://arxiv.org/pdf/2609.16085"),
        ("ZeroQuant-FP: A Leap Forward in LLMs Post-Training W4A8 Quantization Using Floating-Point Formats", "https://arxiv.org/pdf/2307.09782"),
        ("FP8 versus INT8 for efficient deep learning inference", "https://arxiv.org/pdf/2303.17951"),
        ("AIS: Adaptive Importance Sampling for Quantized RL", "https://arxiv.org/pdf/2605.13907"),
        ("Towards Full Pipeline FP8 Reinforcement Learning for LLMs", "https://arxiv.org/pdf/2609.22870")]),
    ("FE1", "quantized model activation patching reproducibility precision", GREY, [
        ("Exploring the Robustness and Transferability of Patch-Based Adversarial Attacks in Quantized Neural Networks", "https://arxiv.org/pdf/2411.15246"),
        ("Value-Driven Mixed-Precision Quantization for Patch-Based Inference on Microcontrollers", "https://arxiv.org/pdf/2401.13714"),
        ("Adaptive quantization and mixed precision in a network (patent)", "https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11507823"),
        ("PAHQ: Accelerating Automated Circuit Discovery through Mixed-Precision Inference Optimization", "https://arxiv.org/pdf/2510.23264"),
        ("Breaking the Limits of Quantization-Aware Defenses: QADT-R for Robustness Against Patch-Based Adversarial Attacks in QNNs", "https://arxiv.org/pdf/2503.07058"),
        ("Practical Quantization in PyTorch", "https://pytorch.org/blog/quantization-in-practice/"),
        ("Quantized Convolutional Neural Networks Robustness under Perturbation", "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12041843/"),
        ("Daily Papers - Hugging Face (q=LLM quantization)", "https://huggingface.co/papers?q=LLM+quantization"),
        ("TorchAO Quantized Models and Quantization Recipes Now Available on HuggingFace Hub", "https://pytorch.org/blog/torchao-quantized-models-and-quantization-recipes-now-available-on-huggingface-hub/")]),
    ("FE1", "W8A8 INT8 activation steering robustness", GREY, [
        ("Daily Papers - Hugging Face (q=quantization format)", "https://huggingface.co/papers?q=quantization+format"),
        ("moeshawky/humanizer-abliterated-INT8-W8A8 (model card)", "https://huggingface.co/moeshawky/humanizer-abliterated-INT8-W8A8"),
        ("Freaksterz/Qwen3.8-27B-SmoothQuant-W8A8-INT8 (model card)", "https://huggingface.co/Freaksterz/Qwen3.8-27B-SmoothQuant-W8A8-INT8"),
        ("Avesed/Qwen3.6-27B-INT8-W8A8 (model card)", "https://huggingface.co/Avesed/Qwen3.6-27B-INT8-W8A8"),
        ("Steering Robustness into World Action Models via Mechanistic Interpretability and Optimal Control", "https://arxiv.org/pdf/2607.14943"),
        ("RedHatAI/Llama-3.3-70B-Instruct-quantized.w8a8 (model card)", "https://huggingface.co/RedHatAI/Llama-3.3-70B-Instruct-quantized.w8a8"),
        ("ZYT-World: A Real-Time Controllable World Model for Closed-Loop Autonomous-Driving Simulation", "https://arxiv.org/pdf/2609.21712"),
        ("transformerlab/ideogram-4-int8-w8a8 (model card)", "https://huggingface.co/transformerlab/ideogram-4-int8-w8a8"),
        ("Overcoming State Inertia in Full-Duplex Spoken Language Models via Activation Steering", "https://arxiv.org/pdf/2606.11386"),
        ("orcarouter/Qwen3.8-27B-Uncensored-INT8 (model card)", "https://huggingface.co/orcarouter/Qwen3.8-27B-Uncensored-INT8")]),
    ("FE1", "numerical precision bf16 fp32 mechanistic interpretability results differ", GREY, [
        ("Different output when we inference through packing with flash attention in bf16 (HF forum)", "https://discuss.huggingface.co/t/different-output-when-we-inference-through-packing-with-flash-attention-in-bf16/174030"),
        ("Greedy Decoding Is Not Precision-Invariant: Cross-Precision Output Divergence in LLM Inference", "https://arxiv.org/pdf/2609.26621"),
        ("Defeating the Training-Inference Mismatch via FP16", "https://arxiv.org/pdf/2510.26788"),
        ("Leveraging the bfloat16 Artificial Intelligence Datatype For Higher-Precision Computations", "https://arxiv.org/pdf/1904.06376"),
        ("TOPLOC: A Locality Sensitive Hashing Scheme for Trustless Verifiable Inference", "https://arxiv.org/pdf/2501.16007"),
        ("MPGemmFI: A Fault Injection Technique for Mixed Precision GEMM in ML Applications", "https://arxiv.org/pdf/2311.05782"),
        ("Efficient Large-Scale Training with Pytorch FSDP and AWS", "https://pytorch.org/blog/efficient-large-scale-training-with-pytorch/"),
        ("Relax: An Asynchronous Reinforcement Learning Engine for Omni-Modal Post-Training at Scale", "https://arxiv.org/pdf/2604.11554")]),
    ("FL1", "base model predicts aligned model alternatives after perturbation", GREY, [
        ("Emergent Misalignment Is Not Magical", "https://arxiv.org/pdf/2608.29118"),
        ("Alignment is Localized: A Causal Probe into Preference Layers", "https://arxiv.org/pdf/2510.16167"),
        ("Language models and brains align due to more than next-word prediction and word-level information", "https://arxiv.org/pdf/2212.00596"),
        ("Harmonised benchmarking of foundation models for single-cell and spatial transcriptomics", "https://arxiv.org/pdf/2607.17227"),
        ("scDFM: Distributional Flow Matching Model for Robust Single-Cell Perturbation Prediction", "https://arxiv.org/pdf/2602.07103"),
        ("Pre-Registered External Evaluation Yields a Consistent Partial-Replication Category across Three Transcriptomic Foundation Models", "https://arxiv.org/pdf/2608.26170")]),
    ("FL1", "post-training preserves base model ranking of candidates", GREY, [
        ("OpenDataArena: A Fair and Open Arena for Benchmarking Post-Training Dataset Value", "https://arxiv.org/pdf/2512.14051"),
        ("On Predicting the Post-training Potential of Pre-trained LLMs", "https://arxiv.org/pdf/2605.11978"),
        ("A Systematic Analysis of Base Model Choice for Reward Modeling", "https://arxiv.org/pdf/2505.10775"),
        ("Post-Training Leaves Behavioral Shadows on Unrelated Decisions (HF paper page)", "https://huggingface.co/papers/2609.29233"),
        ("Automatic Configuration of LLM Post-Training Pipelines", "https://arxiv.org/pdf/2603.18773"),
        ("How post-training shapes legal representations: probing SCOTUS opinions across model families (LessWrong)", "https://www.lesswrong.com/posts/52eFBikdqDMXT2tph/how-post-training-shapes-legal-representations-probing"),
        ("Verbalizable Representations Form a Global Workspace in Language Models", "https://transformer-circuits.pub/2026/workspace/")]),
    ("FL1", "steered or perturbed tuned model reverts to pretraining distribution", GREY, [
        ("Alignment Dynamics in LLM Fine-Tuning", "https://arxiv.org/pdf/2605.18309"),
        ("Spectrum Tuning: Post-Training for Distributional Coverage and In-Context Steerability", "https://arxiv.org/pdf/2510.06084"),
        ("Does Fine-Tuning Undo Activation Steering? Behavioural Recovery Without Weight-Edit Reversal", "https://arxiv.org/pdf/2608.24988"),
        ("A Gravitational Interpretation of Fine-Tuning Reversion", "https://arxiv.org/pdf/2606.28525"),
        ("Curvature Tuning: Provable Training-free Model Steering From a Single Parameter", "https://arxiv.org/pdf/2502.07783"),
        ("Perturbation is All You Need for Extrapolating Language Models", "https://arxiv.org/pdf/2605.04344"),
        ("Perturbational Validity for Foundation Models of Brain Dynamics", "https://arxiv.org/pdf/2609.12710")]),
    ("FL1", "token-level distribution shift RL fine-tuning base top-k", GREY, [
        ("Sparse but Critical: A Token-Level Analysis of Distributional Shifts in RLVR Fine-Tuning of LLMs", "https://arxiv.org/pdf/2603.22446"),
        ("Rebellious Student: Reversing Teacher Signals for Reasoning Exploration with Self-Distilled RLVR", "https://arxiv.org/pdf/2605.10781"),
        ("What Models Know, How Well They Know It: Knowledge-Weighted Fine-Tuning", "https://arxiv.org/pdf/2604.05779"),
        ("Analyzing the Effects of Supervised Fine-Tuning on Model Knowledge from Token and Parameter Levels", "https://arxiv.org/pdf/2509.16596"),
        ("Token-Level Off-Policy Learning for Faithful Generation Under Distribution Shift", "https://arxiv.org/pdf/2607.17524"),
        ("Does Math Reasoning Improve General LLM Capabilities? Understanding Transferability of LLM Reasoning", "https://arxiv.org/pdf/2507.00432"),
        ("ReMiT: RL-Guided Mid-Training for Iterative LLM Evolution", "https://arxiv.org/pdf/2602.03075")]),
    ("FE1", "activation quantization steering vector effect", "github.com", [
        ("GitHub - cma1114/activation_steering", "https://github.com/cma1114/activation_steering"),
        ("What Can We Actually Steer? A Multi-Behavior Study of Activation Control", "https://arxiv.org/pdf/2511.18284")]),
    ("FE1", "FP8 activation quantization interpretability intervention", "github.com", [
        ("GitHub - AARONKANG04/quantization-interpretability (NVFP4/FP8 damage; tuned-lens, SAE features, bf16 vs low-bit)", "https://github.com/AARONKANG04/quantization-interpretability"),
        ("jagrutsharma/inference-benchmark-lab 01-fp8-quantization README", "https://github.com/jagrutsharma/inference-benchmark-lab/blob/main/01-fp8-quantization/README.md"),
        ("sgl-project/sglang issue #31504: fuse static FP8 activation quantization into producer kernels", "https://github.com/sgl-project/sglang/issues/31504"),
        ("huggingface/transformers docs: finegrained_fp8.md", "https://github.com/huggingface/transformers/blob/main/docs/source/en/quantization/finegrained_fp8.md"),
        ("lvyufeng/RelicLLM PR #161: wire the activation-quant flag to every reference fp8 site", "https://github.com/lvyufeng/RelicLLM/pull/161")]),
    ("FE1", "quantized model activation patching reproducibility precision", "github.com", [
        ("localai-org/apex-quant APEX Technical Report", "https://github.com/mudler/apex-quant/blob/main/paper/APEX_Technical_Report.md"),
        ("GitHub - Will65536/safety-repair-of-quantized-agent", "https://github.com/Will65536/safety-repair-of-quantized-agent"),
        ("GitHub - jiuyixu25/VLAQuantBench", "https://github.com/jiuyixu25/VLAQuantBench")]),
    ("FE1", "W8A8 INT8 activation steering robustness", "github.com", [
        ("Ar4ikov/vibevoice.c PR #27: W8A8 and W4A8 int8 activations", "https://github.com/Ar4ikov/vibevoice.c/pull/27"),
        ("kadirnar/kernel-agent PR #200: INT8 W8A8 and INT8 weight-only precision classes", "https://github.com/kadirnar/kernel-agent/pull/200"),
        ("ddalcu/mlx-serve PR #885: rotated int8 prefill (--w8a8-prefill)", "https://github.com/ddalcu/mlx-serve/pull/885"),
        ("AbdelStark/tessera PR #294: quantize W8A8 with power-of-two and affine scales", "https://github.com/AbdelStark/tessera/pull/294")]),
    ("FE1", "numerical precision bf16 fp32 mechanistic interpretability results differ", "github.com", [
        ("drewster99/drews-chess-machine issue #11: fp16 inference and training gaps", "https://github.com/drewster99/drews-chess-machine/issues/11"),
        ("adamyhe/TROGDOR PR #10: run the output head in fp32 under bf16 autocast", "https://github.com/adamyhe/TROGDOR/pull/10"),
        ("GitHub - Gelato1337/mechanistic-interpretability (saepipe: SAE capture for Gemma 3)", "https://github.com/Gelato1337/mechanistic-interpretability"),
        ("chandar-lab/AMPLIFY issue #19: FP16 and FP32 predictions are completely different", "https://github.com/chandar-lab/AMPLIFY/issues/19"),
        ("Pseudogiant-xr/Pseudolife-MCP PR #340: bf16 and fp32 runs no longer compare silently", "https://github.com/Pseudogiant-xr/Pseudolife-MCP/pull/340")]),
]


def main():
    raw = CACHE / "search_results"
    raw.mkdir(parents=True, exist_ok=True)
    for i, (fam, q, domains, res) in enumerate(CALLS):
        items = []
        for title, url in res:
            m = re.search(r"arxiv\.org/(?:abs|pdf|html)/(\d{4}\.\d{4,5})", url)
            items.append({"title": title, "url": url, "arxiv_id": m.group(1) if m else ""})
        (raw / f"{fam}_e6q{i}_E6.json").write_text(json.dumps(items, ensure_ascii=False, indent=1))
        append_jsonl(EVID / "search_log_iter6.jsonl", {
            "family": fam, "query": q, "engine": f"E6 Claude Code built-in WebSearch (allowed_domains={domains}; domain filter not strictly enforced by the tool)",
            "date_filter": "none", "n_results": len(items), "status": "ok", "timestamp_utc": now_utc(),
            "call_time_note": "issued 2026-10-21 ~23:40-23:44 UTC; logged after the call (the built-in tool does not timestamp)"})
    print(f"logged {len(CALLS)} E6 calls")


if __name__ == "__main__":
    main()
