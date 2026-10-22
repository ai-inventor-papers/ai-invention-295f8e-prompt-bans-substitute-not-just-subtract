"""Write evidence/flags_iter6.json (verdicts on frozen flags A-D with decisive sentences and quote ids) and
evidence/corrections_iter6.jsonl (corrections to the hypothesis' positioning text, venue/version lines, plan seed fixes).
Usage: python3 -I tools/write_flags_corrections_iter6.py"""
import json
from datetime import datetime, timezone
from pathlib import Path

EVID = Path(__file__).resolve().parents[1] / "evidence"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

FLAGS = {
    "retrieved": "2026-10-22",
    "A_P1": {
        "verdict": "NOT FIRED (narrowly)",
        "decisive": "No source found localizes which algorithm or solution strategy a code LLM will use as a low-rank causal variable by "
                    "interchange/DAS and validates it by generation. Each half exists separately: DAS-based steering validated by generation on a "
                    "non-plan attribute (CDAS, ICLR 2026: refusal and a CoT backdoor), algorithm choice in code moved by prompt cues only "
                    "(Invisible Lottery, 92c source [30]), and code attributes that are not the algorithm moved by patching or "
                    "difference-in-means vectors (Causal Syntax Circuits 2610.20683, next-token readout; Concept Vectors, ICLR 2027 "
                    "submission; Rahman et al., 92c source [45]). None of these is DAS/interchange plus generation on a strategy or code "
                    "attribute, so the PARTLY clause is not met either.",
        "quotes": ["P1-5", "P1-8", "P1-9", "P1-7", "P1-10"],
        "interpretation_note": "'Only one half holds' is read as both halves applying to the same object (code algorithm choice). "
                               "CDAS (refusal) is not a strategy, so it falls outside the PARTLY clause. Logged in protocol_amendments_iter6.jsonl.",
        "would_change_if": "A paper (or the full text of an ICLR 2027 submission) that applies DAS/interchange to algorithm or strategy choice "
                           "and scores the generated outputs.",
    },
    "B_E": {
        "verdict": "PARTLY FIRED",
        "decisive": "Steering effect sizes under quantization have been measured only for weight-only INT8/NF4, with activations kept in "
                    "FP16/BF16 (2609.06473: 'Activations remain in FP16/BF16 throughout the forward pass'). Two ICLR 2027 submissions show that "
                    "the effect of the same steering direction changes across precision even when directions stay aligned (Stable Directions, "
                    "desk-rejected; Activation Steering under Low-Bit Quantization). Their abstracts do not say whether activations are "
                    "quantized, and the PDFs returned HTTP 403. FP8 weight-and-activation quantization has been studied only for batch "
                    "non-determinism, with no perturbations (ICLR 2027 submission 9kskCmPMqd). Quantization also changes interpretability "
                    "readouts (patching 2604.19884, 2609.01587; SAE features 2606.03002; probes under numeric formats 2609.31796).",
        "quotes": ["E-1", "E-2", "E-5", "E-6", "E-7", "E-8", "E-9", "E-11", "E-13", "E-16"],
        "open_part": "Activation quantization (FP8 W8A8, dynamic per-token scales) and the size of the effect of RANDOM activation "
                     "perturbations relative to bf16 on the same directions: no source found.",
        "would_change_if": "The full text of 8iTqrW1sxY or h57duZqLOr includes W8A8/FP8 activation quantization. B would then FIRE as a "
                           "contemporaneous ICLR 2027 submission, for learned steering directions rather than random pushes.",
    },
    "C_N": {
        "verdict": "FIRED",
        "decisive": "The NLA paper itself (Transformer Circuits, 7 May 2026) edits an NLA explanation of a PLAN (the rhyme word on the newline), "
                    "reconstructs both versions with the AR, and steers with the difference at the newline token only. Steering succeeds "
                    "'roughly 50% of the time'. Its 'Reasoning about Rewards' case builds a steering vector the same way. Similar-verbaliser kin: "
                    "LatentQA (ICLR 2026) steers with a decoder-defined differentiable loss, SelfIE (ICML 2024) Supervised Control edits concepts "
                    "through one-layer gradients, and Dreaming Vectors (LessWrong) derives steering vectors from Activation Oracles.",
        "quotes": ["N-1", "N-2", "N-3", "N-4", "N-15", "N-16", "N-17", "N-20"],
        "cautions": "On a released Qwen-2.5-7B verbalizer, only a small share of specific claims are ones the reconstruction depends on "
                    "(2607.20379), so editing one algorithm name may barely move the AR output. Small open models showed no newline-resident "
                    "rhyme plan (2609.18440). Readout controls already published: shuffled activation, visible-text baseline, blinded judge "
                    "(PKToLtvIZl).",
    },
    "D_P5": {
        "verdict": "PARTLY FIRED",
        "decisive": "Per-sample activation noise for diversity is a saturated method lane (inherited: STARS ICLR 2026, Noise Steering, random "
                    "embedding injection, NC-GRPO; 92c sources [15, 14, 16, 52]). Latent-code sampling without a variable fitted inside a "
                    "frozen LM exists: Latent-Plan Block Diffusion, Parallelizable Probabilistic Latent Reasoning, Singular-Value "
                    "Perturbation (ICLR 2027 submissions). The closest fitted-variable work is Random Choice in LMs (ICLR 2027 submission). "
                    "There a causally tested direction shapes the answer distribution and 'a mechanism-guided intervention ... improves "
                    "sampling'. Its abstract does not say the variable is resampled once per generation, and its object is single-item "
                    "random choice, not a plan or algorithm.",
        "quotes": ["P5-1", "P5-2", "P5-3", "P5-4"],
        "would_change_if": "The full text of eZYeqPZlFr resamples its distribution direction per generation for diversity. D would then "
                           "come close to FIRED on a non-code object.",
    },
}

CORR = [
    ("NLA citation and date", "plan: 'Fraser-Taliente, Kantamneni, Marks et al.'",
     "The paper's own citation is 'Fraser-Taliente, Kantamneni, Ong et al.'; published May 7, 2026 (Transformer Circuits).", "N-8", "CORRECTION"),
    ("NLA poetry case", "hypothesis N: reading and editing the plan in words",
     "The NLA paper already edits an explanation of a plan (rhyme) and steers (~50% success). N's causal arm is a replication in a new domain/model, not a new method.",
     "N-1,N-3", "CONFIRMED (flag C fired)"),
    ("NLA checkpoints", "plan: 8-checkpoint table",
     "README lists 4 base models x (AV, AR) = 8 checkpoints: Qwen2.5-7B-Instruct L20/28, Gemma-3-12B-IT L32/48, Gemma-3-27B-IT L41/62, Llama-3.3-70B-Instruct L53/80; nla_meta.yaml must be loaded.",
     "N-9,N-10,N-11", "CONFIRMED"),
    ("NLA for Qwen3-8B", "iteration 5: 'NLA unavailable for Qwen3-8B'",
     "No official checkpoint, but community reimplementations exist at layer 24: ceselder nanoNLA AV (HF; Karvonen injection; faithfulness disclaimer) and EasyNLA (~70% held-out FVE on Qwen3-8B L24). Reword to 'no official NLA checkpoint for Qwen3-8B'.",
     "N-26,N-27,N-28", "CORRECTION"),
    ("friendli.ai/models/ceselder/nanoNLA", "plan: 'say what it is'",
     "A FriendliAI dedicated-endpoint listing of ceselder's nanoNLA activation verbalizer, fine-tuned from Qwen/Qwen3-8B (AV only; layer 24).",
     "N-26", "CLARIFICATION"),
    ("Gemma Scope 2 date and IT SAEs", "plan: December 2025; IT SAEs finetuned from PT",
     "Announced 22 Dec 2025 (LessWrong/AF). Tech report: IT SAEs are initialized from the PT SAEs and finetuned on rollout-derived data.", "S-2,S-3", "CONFIRMED"),
    ("circuit-tracer Qwen-3 PLTs", "plan: record checkpoint and trainer",
     "Qwen-3 PLTs (0.6B-14B, incl. 8B) are mwhanna/Hanna et al. (2025) transcoders. The HF card does not name the checkpoint; the ICLR 2026 paper using them calls its Qwen-3 models instruction-tuned, so most likely the post-trained Qwen/Qwen3-8B, not -Base (inference, unverified).",
     "S-6,S-7,S-8,S-9", "CLARIFICATION"),
    ("circuit-tracer Gemma-3 PLTs", "plan: grep 'require using the'",
     "Gemma-3 PLTs come from GemmaScope-2 (270M-27B, PT and IT) and require the nnsight backend.", "S-5", "CONFIRMED"),
    ("Sutter et al. grep target", "plan/handbook phrase: 'any neural network can be mapped to any algorithm'",
     "The phrase does not occur in v2 HTML (0 matches); use the verified 100% IIA sentence. NeurIPS 2025 Spotlight per the arXiv v2 comment.", "CTRL-1",
     "CORRECTION (quote)"),
    ("Makelov et al. venue", "arXiv comment: NeurIPS 2023 ATTRIB workshop",
     "Also an ICLR 2024 poster (iclr.cc/virtual/2024/poster/19100); cite as ICLR 2024.", "CTRL-3", "CONFIRMED"),
    ("SelfIE venue", "plan: ICML 2024, PMLR v235", "PMLR 235:7373-7388 (chen24ao), verified on the PMLR page.", "N-18", "CONFIRMED"),
    ("DAS venue", "plan: CLeaR 2024, PMLR v236", "Verified PMLR v236 record (geiger24a).", "P1-2", "CONFIRMED"),
    ("Engels et al. title", "plan: 'Not All Language Model Features Are Linear' (ICLR 2025)",
     "v3 title: 'Not All Language Model Features Are One-Dimensionally Linear' (ICLR 2025 per arXiv comment).", "P3-2", "CORRECTION"),
    ("2506.09501 title and number", "plan: v1 believed 'Give Me FP32 or Give Me Death?'; 'up to 9%'",
     "v1 (11 Jun 2025) is titled 'Give Me FP32 or Give Me Death? Challenges and Solutions for Reproducible Reasoning'; v2 (24 Oct 2025) is retitled. 'up to 9% variation in accuracy' is verified.",
     "E-18,E-19", "CONFIRMED"),
    ("2609.15504 title", "plan: 'Orthrus precision study'",
     "Current arXiv title (v2): 'Evaluating Losslessness in Speculative Decoding Under Finite-Precision Inference' (web listing: 'How Lossless Is Lossless Speculative Decoding? The Role of Numerical Precision in Orthrus'). Optional; no row.",
     "", "CLARIFICATION"),
    ("2609.06473 quantization type", "plan: weight-only INT8/NF4",
     "Confirmed: bitsandbytes W8A16 and W4A16 (NF4); activations stay FP16/BF16. 0 Semantic Scholar citations, so backward references were used for snowballing.",
     "E-1,E-2", "CONFIRMED"),
    ("Latent Plan Transformer venue", "plan: NeurIPS 2024", "The arXiv record (v4) has no comment or journal-ref, so the venue is unverified here; cite as arXiv 2402.04647v4.",
     "P5-5", "DOWNGRADE (venue unverified)"),
    ("AxBench venue", "handbook/plan: no venue", "The arXiv comment is empty and secondary listings disagree; give no venue line.", "S-10", "CLARIFICATION"),
    ("Patchscopes (92d [88])", "plan: 'readout only?'", "v4 HTML has 0 matches for steer|control: readout-only for flag C (absence check, not a quote).", "", "CONFIRMED"),
    ("Sood post", "plan: VERIFIED-BLOG", "Dated Aug 18, 2026; audits two released checkpoints (Qwen and Gemma).", "N-21", "CONFIRMED"),
    ("LatentQA venue/version", "plan: v2 March 2026; ICLR 2026", "v2 updated 2026-03-23; arXiv comment 'ICLR 2026'.", "N-15", "CONFIRMED"),
    ("SAE-Steering venue", "plan: ACL 2026 long 974", "arXiv v2 comment: 'Accepted to the ACL 2026 Main' (paper number not verified).", "S-13", "CONFIRMED (number unverified)"),
    ("Train the Model, Not the Reader number", "search snippet: '~2% of specific claims'",
     "v2 HTML renders the number twice (MathML), so the quote is split with [...]. The text says 'as few as ~2%'.", "N-24", "MathML split"),
    ("Inherited flag-critical versions", "Step 0(c)",
     "No newer arXiv version for 2601.22010, 2605.11936, 2608.21595, 2606.10302, 2603.23629, 2606.04057, 2605.05115, 2603.18353 (checked 2026-10-22).",
     "", "CONFIRMED"),
]


def main():
    (EVID / "flags_iter6.json").write_text(json.dumps(FLAGS, indent=1, ensure_ascii=False))
    with (EVID / "corrections_iter6.jsonl").open("w", encoding="utf-8") as fh:
        for i, (item, before, after, qids, status) in enumerate(CORR, 1):
            fh.write(json.dumps({"id": f"K{i}", "item": item, "as_written": before, "finding": after, "quote_ids": qids,
                                 "status": status, "logged_utc": NOW}, ensure_ascii=False) + "\n")
    with (EVID / "protocol_amendments_iter6.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"logged_utc": NOW, "type": "interpretation note (no change to frozen text)",
                             "text": "Flag A 'only one half holds' is applied to the same object (code algorithm/strategy choice); "
                                     "DAS+generation on a non-plan attribute (e.g., refusal) is outside the PARTLY clause and is reported "
                                     "as method-lane occupation instead."}) + "\n")
        fh.write(json.dumps({"logged_utc": NOW, "type": "tooling note",
                             "text": "Prior audits' tools (sat_search.py, grep_cache.py, fetch_texts.py, arxiv_meta.py, screen.py, "
                                     "qa_second_pass.py) were readable on disk and were copied and adapted; the plan had assumed they "
                                     "were unavailable."}) + "\n")
        fh.write(json.dumps({"logged_utc": NOW, "type": "stop rule",
                             "text": "Round 2 produced new hits >= 1.5 (2610.20683, sbVictHY9s, 2610.20808, eZYeqPZlFr, 2607.20469), "
                                     "so round 3 (forward and backward references of these) was run."}) + "\n")
    print("flags and corrections written:", len(CORR), "corrections")


if __name__ == "__main__":
    main()
