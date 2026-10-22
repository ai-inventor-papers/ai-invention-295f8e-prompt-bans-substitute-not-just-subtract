"""Step 3b: O/I/C scores (frozen rubric in evidence/protocol_iter6.json) for every manually shortlisted hit, plus a one-line
verdict for every other in-window candidate (keyword pre-screen or title/abstract screen). Single screener (plan departure 1).

Writes evidence/saturation_hits_iter6.jsonl and evidence/saturation_counts_iter6.json.
Usage: python3 -I tools/score_hits_iter6.py
"""
import json
from collections import Counter
from pathlib import Path

EVID = Path(__file__).resolve().parents[1] / "evidence"

# (key, short title, claim, O, I, C, decisive sentence per axis, tag, contemporaneity)
# contemporaneity per the inherited rule: arXiv v1 after 2026-06-22 -> contemporaneous_4mo; ICLR 2027 submission -> contemporaneous.
S = [
    # ---- P1 (and L1/L3) ----
    ("2602.05234", "CDAS: Faithful Bi-Directional Model Steering via DII (ICLR 2026)", "P1", 0.5, 1, 1,
     "O: refusal / CoT-backdoor behaviour is a categorical attribute, not a plan or strategy (borderline single-screener call); "
     "I: distributed interchange intervention (DAS) with a distribution-matching objective; C: steered generations scored.",
     "occupies the method+criterion pair on a non-plan attribute; object differs", "published"),
    ("or:DLKIln4eAT", "Programmable Semantic Interventions", "P1", 0, 1, 0.5,
     "O: MIB answers, no plan/strategy; I: low-rank interchange subspace with a declared semantic program; C: answer-level IIA.", "adjacent", "contemporaneous"),
    ("or:aHSbJo4RHN", "Finding Algorithms in Neural Networks: DAS vs transfer learning", "P1", 0.5, 1, 0,
     "O: which algorithm a toy network learned (not a code LLM); I: DAS incl. non-linear localization; C: transfer speed, not generation.",
     "adjacent", "contemporaneous"),
    ("2610.20683", "Causal Syntax Circuits in CodeLMs", "P1", 0.5, 0.5, 0.5,
     "O: default output language of code models (a code attribute, not the algorithm); I: patching/circuits/steering, not a low-rank DAS map; "
     "C: 'steering changes the most likely next token in 9 of 45'.", "adjacent", "contemporaneous_4mo"),
    ("or:sbVictHY9s", "Steering LLM Coding Behaviors with Concept Vectors", "P1", 0.5, 0.5, 1,
     "O: commenting/logging/defensive constructs/language (code attributes); I: difference-in-means vectors, no DAS; C: held-out outputs scored.",
     "adjacent", "contemporaneous"),
    ("or:vH3g2k4lPB", "Before Reasoning Begins (Qwen3-8B pre-generation SAE targets)", "P1", 0.5, 0.5, 1,
     "O: reasoning-mode target at the final prompt position; I: SAE-feature suppression with random nulls, no DAS; C: accuracy on GSM8K/CruxEval-O/HumanEvalPlus.",
     "adjacent", "contemporaneous"),
    ("2607.16451", "Committed Before Reasoning (Qwen3-8B)", "P1", 0.5, 0.5, 0.5,
     "O: answer pre-commitment; I: preliminary activation-level evidence; C: rollouts plus readouts.", "adjacent", "contemporaneous_4mo"),
    ("or:eZYeqPZlFr", "Random Choice in LMs: linear choice state and low-rank sampling control", "P1", 0.5, 0.5, 1,
     "O: random-choice mode and answer distribution; I: probes, SAEs, causal interventions on directions (not DAS); C: sampled answers.",
     "adjacent", "contemporaneous"),
    ("2508.18098", "Detecting and Characterizing Planning in LMs (MBPP, Gemma-2-2B) [anchor 2025]", "P1", 0.5, 0.5, 0.5,
     "O: planned future tokens in code, not the algorithm; I: SAE features with activation/attribution patching; C: causal influence readouts.",
     "adjacent", "anchor"),
    ("2602.22600", "Transformers converge to invariant algorithmic cores", "P1", 0, 0.5, 0.5,
     "O: task algorithm, not a choice among algorithms; I: causally validated core subspaces; C: task accuracy readouts.", "adjacent", "published"),
    ("or:IxSVZFIxAW", "Climbing the Causal Ladder: twenty LMs share a causal variable", "P1", 0, 1, 0.5,
     "O: grammatical number; I: causal-variable sameness test through interventions; C: readouts.", "adjacent", "contemporaneous"),
    ("2604.12493", "Latent Planning Emerges with Scale (Qwen-3 transcoders; ICLR 2026)", "P1", 0.5, 0.5, 0.5,
     "O: planned word (a/an, rhyme); I: transcoder feature circuits and steering; C: next-token choice.", "adjacent", "published"),
    ("2609.39243", "Right Answer, Wrong Mechanism (CTRL)", "P1", 0, 0.5, 0.5,
     "O: none; I: planted hidden pathways vs DAS/patching; C: IOI-style answers.", "adjacent (control)", "contemporaneous_4mo"),
    ("2606.27510", "The Curse of Multiple Mediators (CTRL)", "P1", 0, 0.5, 0.5, "control on the patching estimand", "adjacent (control)", "contemporaneous_4mo"),
    ("2606.06267", "Many Circuits, One Mechanism (CTRL; TMLR 2026)", "P1", 0, 0.5, 0.5, "control on circuit identity", "adjacent (control)", "published"),
    ("2605.08012", "Position: identification assumptions (CTRL)", "P1", 0, 0.5, 0, "control: disclose identification assumptions", "adjacent (control)", "published"),
    # ---- P2 ----
    ("2607.20469", "DecodeShare: shared decode-time subspace vs prefill/random subspace", "P2", 0, 0.5, 1,
     "O: task-general decisions; I: subspace vs random-subspace removal at matched budget (not prediction of random pushes); C: decision performance.",
     "adjacent", "published"),
    ("or:4gvIW4C0bw", "Jailbreak success coordinate outside the refusal subspace", "P2", 0.5, 0.5, 1,
     "O: categorical jailbreak outcome; I: coordinate outside an evaluated subspace, decodable pre-generation, intervened; C: behaviour.",
     "adjacent", "contemporaneous"),
    ("or:vH3g2k4lPB", "Before Reasoning Begins (targeted vs random-null interventions)", "P2", 0.5, 0.5, 1,
     "O: reasoning target; I: targeted vs layer-matched random nulls, no projection-based prediction; C: accuracy.", "adjacent", "contemporaneous"),
    ("2602.02103", "How Far Ahead Do LLMs Plan? (Tele-Lens; ICML 2026)", "P2", 0.5, 0, 0.5, "O: latent plan horizon; I: probing only; C: probe readouts.", "adjacent", "published"),
    ("2610.18121", "Narrative Lookahead in LLMs", "P2", 0.5, 0.5, 0.5, "O: narrative events; I: probes and steering; C: readouts.", "adjacent", "contemporaneous_4mo"),
    ("2608.22985", "What Does Activation Steering Control? (round-3 snowball)", "P2", 0, 0.5, 0.5,
     "O: answer identifiers; I: a low-rank output-sensitive component of a direction carries most of its effect (projection account, not random pushes); C: score changes.",
     "adjacent (supports a projection account)", "contemporaneous_4mo"),
    ("2602.06801", "On the Non-Identifiability of Steering Vectors (supplementary search)", "P2", 0, 0.5, 0.5,
     "O: none; I: equivalence classes of behaviourally indistinguishable interventions (orthogonal perturbations near-equivalent); C: behavioural efficacy readouts.",
     "adjacent (supports subspace-level rather than direction-level claims)", "published"),
    ("2504.04635", "Steering off Course [anchor 2025]", "P2", 0, 0.5, 0.5, "O: none; I: reliability of steering methods; C: task readouts.", "adjacent", "anchor"),
    # ---- P3 ----
    ("2405.14860", "Not All LM Features Are One-Dimensionally Linear [anchor; ICLR 2025]", "P3", 0.5, 1, 0.5,
     "O: categorical days/months on a circle; I: interventions along circular representations; C: next-token readouts.", "adjacent", "anchor"),
    ("2406.01506", "Geometry of Categorical and Hierarchical Concepts [anchor; ICLR 2025]", "P3", 0.5, 0.5, 0.5,
     "O: categorical concepts as polytopes; I: geometry plus interventions; C: readouts.", "adjacent", "anchor"),
    ("2604.15010", "Prolepsis: early irrevocable commitment (open models)", "P3", 0.5, 0.5, 0.5,
     "O: early commitment to a rhyme/decision; I: CLT steering, not interpolation; C: probability readouts.", "adjacent", "published"),
    ("or:MN9X374VhG", "Consciousness spectrum: manifold-guided vs linear steering", "P3", 0, 0.5, 1,
     "O: continuous spectrum, not a categorical plan; I: manifold vs linear steering; C: generated text.", "adjacent", "contemporaneous"),
    ("or:eZYeqPZlFr", "Random Choice in LMs (switch direction)", "P3", 0.5, 0.5, 1,
     "O: random-choice mode switch; I: direction interventions (not interpolation sweeps); C: sampled answers.", "adjacent", "contemporaneous"),
    # ---- P4 ----
    ("2412.07961", "Forking Paths in Neural Text Generation [anchor 2024]", "P4", 0.5, 0.5, 1,
     "O: outcome distributions; I: token resampling at forking tokens, no state noise; C: generated outcomes.", "adjacent", "anchor"),
    ("2602.17691", "HELIX: Tethered Reasoning in Quantized LLMs", "P4", 0, 0.5, 1,
     "O: hallucination/coherence; I: temperature plus steering, not matched-KL; C: benchmark generations.", "adjacent", "published"),
    ("or:5tVsS1vVLC", "Predicting Future Behaviors in Reasoning Models", "P4", 0.5, 0.5, 1,
     "O: behavioural outcome distributions; I: forking-paths analysis plus steering; C: behaviour.", "adjacent", "contemporaneous"),
    # ---- P5 / flag D ----
    ("or:eZYeqPZlFr", "Random Choice in LMs (mechanism-guided sampling)", "P5", 0.5, 0.5, 1,
     "O: single-item random choices; I: intervention on a fitted direction to improve sampling, per-generation resampling not stated; C: sampled answers.",
     "adjacent (closest to flag D)", "contemporaneous"),
    ("or:IhQbFddkBp", "Latent-Plan Block Diffusion", "P5", 0, 0.5, 0.5,
     "O: block-level plan for parallel decoding; I: samples a learned latent plan per block (trained, not localized in a frozen LM); C: likelihood/quality.",
     "adjacent", "contemporaneous"),
    ("or:CtluWEsiX7", "Parallelizable Probabilistic Latent Reasoning", "P5", 0.5, 0.5, 1,
     "O: reasoning trajectories; I: sampling a trained latent distribution; C: diverse trajectories scored.", "adjacent", "contemporaneous"),
    ("or:oTt6XeccGk", "Singular-Value Perturbation for diverse latent reasoning", "P5", 0.5, 0.5, 1,
     "O: latent reasoning paths; I: random weight-SVD rescaling, no fitted variable; C: RL performance.", "adjacent", "contemporaneous"),
    ("2402.04647", "Latent Plan Transformer [anchor]", "P5", 0, 0.5, 1, "O: RL trajectories; I: latent plan inference/sampling; C: returns.", "adjacent", "anchor"),
    # ---- N / flag C ----
    ("nla", "NLA paper: edit explanation -> AR -> steer (Transformer Circuits, 2026-05-07)", "N", 0.5, 1, 1,
     "O: rhyme plan on the newline (a categorical plan in another domain); I: edit explanation, reconstruct with the AR, steer with the difference; "
     "C: completions change, success 'roughly 50% of the time'.", "OCCUPIES (method)", "published"),
    ("2412.08686", "LatentQA (ICLR 2026) [anchor]", "N", 0.5, 0.5, 1,
     "O: personas/sentiment/bias; I: decoder loss used to steer (verbaliser-based control, no reconstruct-and-patch); C: generations.", "adjacent (flag C kin)", "anchor"),
    ("2403.10949", "SelfIE (ICML 2024) [anchor]", "N", 0.5, 0.5, 1,
     "O: concepts/knowledge; I: Supervised Control edits open-ended concepts via one-layer gradients; C: generations.", "adjacent (flag C kin)", "anchor"),
    ("lw_dreaming_vectors", "Dreaming Vectors: steering vectors from Activation Oracles (LessWrong)", "N", 0, 0.5, 1,
     "O: concepts; I: gradient-descended steering vectors from a verbaliser; C: steered outputs.", "adjacent (flag C kin, grey literature)", "published"),
    ("2607.20379", "Train the Model, Not the Reader", "N", 0, 0.5, 0.5,
     "O: none; I: claim flips vs reconstruction on a released Qwen-2.5-7B verbalizer (edit->reconstruct, no steering); C: reconstruction.",
     "adjacent (contradicts in part)", "contemporaneous_4mo"),
    ("or:PKToLtvIZl", "Auditing the Auditor: ground-truth controls for NLA explanations", "N", 0, 0, 0.5,
     "O: facts/evaluation mode; I: readout controls only; C: calibrated readouts.", "control set the readout must meet", "contemporaneous"),
    ("jaisood_nla", "Sood: NLAs verbalize influence but not whether it changed the outcome", "N", 0.5, 0, 0.5,
     "O: influence direction/answer; I: readout only; C: AUROC readouts.", "adjacent", "contemporaneous_4mo"),
    ("2607.21774", "Colombian identity with NLA (Qwen2.5-7B L20)", "N", 0.5, 0, 0.5, "O: identity attribute; I: readout only; C: descriptive.", "adjacent", "contemporaneous_4mo"),
    ("2609.18440", "Planning or Improvisation? poetry planning site on open models", "N", 0.5, 0.5, 1,
     "O: rhyme plan; I: CLT suppress-and-inject plus residual patching (no explanation edit); C: 8,640 sampled lines.",
     "adjacent (contradicts in part)", "contemporaneous_4mo"),
    ("2512.15674", "Activation Oracles [anchor]", "N", 0, 0, 0.5, "O: none; I: readout only; C: QA readouts.", "irrelevant to the causal arm (readout kin)", "anchor"),
    ("2608.21664", "Measuring Activation Control", "N", 0, 0, 0.5, "monitoring confound for NLA readouts", "irrelevant to the causal arm (context)", "contemporaneous_4mo"),
    ("2609.33702", "Understanding Confabulation in Activation Explanations", "N", 0, 0, 0.5, "readout evaluation", "irrelevant to the causal arm (context)", "contemporaneous_4mo"),
    ("2610.18727", "On the Monitorability of NLAs", "N", 0, 0, 0, "theory of NLA oversight", "irrelevant", "contemporaneous_4mo"),
    # ---- S ----
    ("2601.03595", "SAE-Steering of reasoning strategies (ACL 2026)", "S", 0.5, 1, 1,
     "O: reasoning strategy (backtracking, cross-verification); I: SAE features (logit-based recall) vs prompt-based and activation-based baselines; "
     "C: strategy control in generations ('SAE-based steering outperforms baselines').", "OCCUPIES (method, non-code strategy)", "published"),
    ("2601.05679", "Do SAEs Identify Reasoning Features? (Gemma Scope 2; ICML 2026)", "S", 0.5, 0.5, 1,
     "O: reasoning features; I: Gemma Scope 2 SAE features with falsification and steering (no diff-in-means/prompting arm); C: benchmarks, 'minimal changes'.",
     "adjacent (contradicts in part)", "published"),
    ("2604.15010", "Prolepsis: CLT steering succeeds where six residual methods fail", "S", 0.5, 1, 0.5,
     "O: rhyme plan; I: CLT features vs residual-stream methods incl. difference steering; C: output probabilities.", "adjacent (contradicts AxBench prior here)", "published"),
    ("2604.12493", "Latent Planning Emerges with Scale (Qwen-3 transcoders)", "S", 0.5, 0.5, 0.5,
     "O: planned word; I: transcoder feature circuits plus steering, no diff-in-means/prompting arm; C: next-token choice.", "adjacent", "published"),
    ("2609.18440", "Planning or Improvisation? (open CLTs)", "S", 0.5, 0.5, 1, "O: rhyme plan; I: CLT features bottom-up; C: sampled lines.", "adjacent (contradicts in part)", "contemporaneous_4mo"),
    ("or:vH3g2k4lPB", "Before Reasoning Begins (Qwen3-8B SAEs)", "S", 0.5, 0.5, 1, "O: reasoning target; I: SAE features with random nulls; C: accuracy.", "adjacent", "contemporaneous"),
    ("2605.31183", "AxBench rebuttal", "S", 0, 1, 1, "O: concepts; I: supervised SAE pipeline vs LoRA/baselines; C: AxBench steering scores.", "adjacent (prior)", "published"),
    ("or:2AiBLDA67W", "Variable roles in code LMs (SAEs vs probes)", "S", 0.5, 0.5, 1,
     "O: code variable roles (not the algorithm); I: SAE features vs residual probes and lexical baselines, no attribution; C: generation control.", "adjacent", "contemporaneous"),
    ("2606.18322", "SAE Interventions are Unreliable", "S", 0, 0.5, 1, "O: harmful behaviours; I: SAE clamps; C: recovered behaviour.", "adjacent (caution)", "published"),
    ("2501.17148", "AxBench [anchor]", "S", 0, 1, 1, "O: concepts; I: SAEs vs difference-in-means vs prompting; C: judged steering.", "adjacent (prior)", "anchor"),
    ("2503.18878", "I Have Covered All the Bases Here [anchor]", "S", 0.5, 0.5, 1, "O: reasoning behaviours; I: SAE feature steering; C: benchmarks.", "adjacent", "anchor"),
    # ---- E / flag B ----
    ("2609.06473", "Steering Under Compression (weight-only INT8/NF4)", "E", 0, 0.5, 1,
     "O: sentiment/length; I: same steering directions under weight-only quantization, activations kept in FP16/BF16; C: judged outputs.",
     "adjacent (flag B partly)", "contemporaneous_4mo"),
    ("or:8iTqrW1sxY", "Stable Directions, Different Effects (desk-rejected ICLR 2027)", "E", 0, 0.5, 1,
     "O: concepts/tasks; I: native vs transferred steering across 'precision changes' (activation quantization not stated in the abstract); C: steering effects.",
     "adjacent (flag B partly; would fire if activations are quantized)", "contemporaneous"),
    ("or:h57duZqLOr", "Activation Steering under Low-Bit Quantization", "E", 0, 0.5, 0.5,
     "O: none; I: fixed layer/direction/strength across full-precision and quantized models (calibration geometry suggests weight PTQ); C: steered output KL.",
     "adjacent (flag B partly)", "contemporaneous"),
    ("or:9kskCmPMqd", "Quantization Modulates Batch-Context Non-Determinism (incl. FP8 W8A8)", "E", 0, 0.5, 1,
     "O: none; I: FP8 weight-and-activation quantization vs BF16 on non-determinism, no perturbations; C: answer flips.", "adjacent (mechanism neighbour)", "contemporaneous"),
    ("2610.20808", "PRISM: transfer of activation interventions across precision (NF4)", "E", 0, 0.5, 1,
     "O: unsafe tool calls; I: interventions transferred across NF4 precision; C: tool-call behaviour.", "adjacent", "contemporaneous_4mo"),
    ("2604.19884", "From Signal Degradation to Computation Collapse (Findings ACL 2026)", "E", 0, 0.5, 0.5, "patching under 4/2-bit", "adjacent", "published"),
    ("2609.01587", "The Structure of Quantization Damage", "E", 0, 0.5, 0.5, "patching/circuit drift vs restored precision", "adjacent", "contemporaneous_4mo"),
    ("2606.03002", "Perplexity Can Miss SAE Feature Damage Under Quantization", "E", 0, 0.5, 0.5, "SAE features under quantization", "adjacent", "published"),
    ("2609.31796", "Same Probe, Different Numbers", "E", 0, 0.5, 0.5, "probes under bf16/fp16/fp32 and batch non-determinism", "adjacent", "contemporaneous_4mo"),
    ("2609.26621", "Greedy Decoding Is Not Precision-Invariant (TMLR 2026)", "E", 0, 0.5, 1, "BF16 vs FP16 output divergence, no perturbations", "adjacent", "contemporaneous_4mo"),
    ("2604.19790", "Precision-Induced Output Disagreements", "E", 0, 0.5, 1, "bf16 vs fp16 and int16 vs int8 output disagreements", "adjacent", "published"),
    ("2602.17691", "HELIX (4-bit Granite; temperature plus steering)", "E", 0, 0.5, 1, "steering inside a 4-bit model, no precision contrast", "adjacent", "published"),
    ("2606.21023", "Demystifying Numerical Instability in LLM Inference", "E", 0, 0.5, 1, "downcasting truncation errors drive divergence", "adjacent", "published"),
    ("2605.19537", "The Silent Hyperparameter: inference backends", "E", 0, 0.5, 1, "backend/reduced precision changes outputs", "adjacent", "published"),
]


def verdict(total):
    return "occupies" if total >= 2.5 else ("adjacent" if total >= 1 else "irrelevant")


def main():
    cands = {}
    for line in (EVID / "saturation_candidates_iter6.jsonl").read_text().splitlines():
        c = json.loads(line)
        cands[c["key"]] = c
    scr = {}
    for line in (EVID / "screening_iter6.jsonl").read_text().splitlines():
        r = json.loads(line)
        scr[r["key"]] = r
    out = EVID / "saturation_hits_iter6.jsonl"
    scored_keys = set()
    rows = []
    for key, title, claim, o, i, c, why, tag, contemp in S:
        tot = o + i + c
        cand = cands.get(key, {})
        rows.append({"key": key, "title": title, "claim": claim, "O": o, "I": i, "C": c, "total": tot, "rubric_verdict": verdict(tot),
                     "relation": tag, "decisive": why, "contemporaneity": contemp, "found_by": {"engines": cand.get("engines", ["seed"]),
                     "queries": cand.get("queries", ["seed"])}, "stage": "scored (manual title/abstract/full-text)"})
        scored_keys.add(key)
    n_kw_irrel = n_pre = 0
    for key, r in scr.items():
        if not r["in_window"] or key in scored_keys:
            continue
        if r["keyword_pass"]:
            rows.append({"key": key, "title": r["title"], "rubric_verdict": "irrelevant", "stage": "title/abstract screen (keyword pass, off-object)",
                         "groups": r["groups"], "keyword_score": r["score"]})
            n_kw_irrel += 1
        else:
            rows.append({"key": key, "title": r["title"], "rubric_verdict": "irrelevant", "stage": "keyword pre-screen (no lane group matched)"})
            n_pre += 1
    out.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows))
    sc = [x for x in rows if x["stage"].startswith("scored")]
    counts = {
        "raw_hits_identified": None, "unique_after_dedup": len(cands), "in_window": sum(1 for r in scr.values() if r["in_window"]),
        "keyword_pass_in_window": sum(1 for r in scr.values() if r["in_window"] and r["keyword_pass"]),
        "scored_rows": len(sc), "scored_unique_papers": len({x["key"] for x in sc}),
        "scored_verdicts": dict(Counter(x["rubric_verdict"] for x in sc)),
        "irrelevant_at_title_abstract": n_kw_irrel, "excluded_at_keyword_prescreen": n_pre,
        "occupying_rows": [(x["key"], x["claim"], x["total"]) for x in sc if x["rubric_verdict"] == "occupies"],
        "new_hits_ge_1_5_after_round2": sorted({x["key"] for x in sc if x["total"] >= 1.5}),
    }
    raw = 0
    for f in (EVID.parent / "cache" / "search_results").glob("*.json"):
        raw += len(json.loads(f.read_text()))
    counts["raw_hits_identified"] = raw
    (EVID / "saturation_counts_iter6.json").write_text(json.dumps(counts, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in counts.items() if k != "new_hits_ge_1_5_after_round2"}, indent=1))


if __name__ == "__main__":
    main()
