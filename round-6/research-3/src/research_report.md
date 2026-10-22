# Prior work on base landings and 8-bit nudges

## Summary

Dated (2026-10-21/22 UTC) positioning and saturation audit for iteration-6 Claims L, E, S/F and K. Provides paste-ready Table 92e (96 rows, same columns as 92b-92d; 80 new verbatim quotes plus 4 venue-page confirmations: 64 VERIFIED full text, 12 VERIFIED-ABSTRACT, 4 VERIFIED-BLOG; 84/84 re-matched by live fetch_grep; 64/64 supporting passages literal on live pages); inherited 92b-92d quotes cited by row id. Search under a protocol frozen before the first call (sha256 0e2dc2d7...): 6 families / 21 strings on OpenAlex/Crossref, arXiv API, Semantic Scholar, OpenReview ICLR 2027 + 14 grey-literature calls, forward citations of 8 seeds, rounds 2-4; 150 calls, 4446 raw hits, 3798 unique, 577 hand-screened, 61 scored (5 occupies, 52 adjacent, 4 irrelevant); same-agent re-screen kappa 0.791. Stopped after R4 by a logged deviation. FLAG E (activation quantisation changes an activation-level intervention's behavioural effect): PARTLY FIRED. Full-text evidence is weight-only (Steering Under Compression 2609.06473: bitsandbytes INT8/NF4, activations FP16/BF16, 'activation quantization (W8A8, W4A4) ... excluded by design'; PRISM 2610.20808 NF4) or joint W+A (PAHQ 2510.23264: FP32 vs 8-bit RTN of all weights and activations collapses ACDC patching AUC on GPT-2-scale). Two contemporaneous ICLR 2027 submissions report at abstract level that the SAME steering intervention's effect drifts across precision while fidelity/direction similarity are preserved (OpenReview 8iTqrW1sxY desk-rejected; h57duZqLOr), precision factor unstated, PDFs 403. Per-token-scaled FP8 W8A8 is accuracy-lossless (Kurtic et al., ACL 2025), supporting the 'same default' premise. So Claim E's general deployment statement is occupied; claimable: activation-vs-weight 2x2 attribution on identical hooks, per-token-scaled FP8 W8A8 engine, content-free nudges at matched dose with CRN, test-checked algorithm labels, absmax/scale readouts. E-deployment general form also occupied by KV-cache quantisation silently removing refusals (2606.09864) and flips (Dutta 2024). Reviewer baselines: kernel-swap control (Integer Alibi 2608.13756), batch invariance, weights-through-16-bit kernels (2609.04748), BF16 vs FP16 (TMLR 2609.26621). FLAG L (base forecast of where a perturbed tuned model lands, scored vs the tuned model's own tail/likelihood): PARTLY FIRED by Re-Emergent Misalignment 2507.03662 (retrospective likelihoods), Language Models Resist Alignment (ACL 2025) / Alignment Dynamics 2605.18309 (distribution-level rebound), Gravitational Safety Reversion 2606.28525 (prospective, geometric null); not fired: no algorithm-level, committed forecast vs q_lik/q_tail. Rival-supporting: jailbroken landings within the safe model's own top-10 (2401.17256), EM persona subspace in the frozen tuned model (2607.21356). Token-level: Sparse but Critical (ICLR 2026; ~30%/80%/90% at high-divergence positions). S: partly occupied (inherited site comparisons; Gaussian embedding perturbation 2602.02427; forks in the road 2605.17026); FLAG S not fired. F1 crowded (Forking Paths ICLR 2025, Forking Fast, Thought Anchors, Cliff tokens, Locked at the Entrance now arXiv 2608.29188). F2: the top-two-margin flip mechanism is occupied for numerics (2609.26621, MarginGate 2605.30218); present the temperature bound as a diagnostic. K: partly occupied (base merging restores diversity incl. code, ICLR 2027 MYXgOex05m; alignment-tax averaging EMNLP 2024; WiSE-FT); FLAG K not fired (no algorithm-level labels). Permitted wording: dated 'to our knowledge', never 'first'. 16 corrections (e.g., Give Me FP32 = NeurIPS 2025 oral under v2 title; URIAL/EFT ICLR 2024; Top-nσ ACL 2025 retitled; 'base model' in 2608.29118 = pre-EM instruct model). Files: research_report.md, evidence/{protocol_iter6,flags_iter6}.json, quotes/scored_hits/search_log/screening jsonl, reproducibility.md.

## Research Findings

# Prior work on base landings and 8-bit nudges: positioning and saturation audit for iteration-6 Claims L, E, S/F, K (Table 92e)

## 1. Scope, date and method

Dated audit (logged search calls 2026-10-21T23:35:20Z to 2026-10-21T23:56:15Z; quote verification and live re-match 2026-10-21/22 UTC) of the iteration-6 claims L1a/L1b/L2/L3 (landing identity), E/E-attribution/E-deployment (FP8 W8A8 engine control), S-a..S-d and F1/F2 (site of content-free nudges, forks, margins) and K (diversity knobs). It extends Tables 92b/92c (art_kjrCpQnPaniY) and 92d (art_ObxQOIlAM9MS); their verified quotes are cited by row id and not re-verified. Claim wording comes from the artifact plan (the iteration-6 hypothesis text was not passed to this executor), and the 'what this run adds' column uses design facts only. The protocol (claims, 6 query families / 21 frozen strings, engines E1 OpenAlex/Crossref, E3 arXiv API, E4 Semantic Scholar, E5 OpenReview ICLR 2027, E6 grey literature, rubric, flags, stop rule) was frozen before the first search call (evidence/protocol_iter6.json, sha256 0e2dc2d7...a9c52, written 2026-10-21T23:34:28Z) [107, 108, 109].

Totals: 150 logged search calls (E1 27, E3 27, E4 27, E5 28, E6 14, OpenAlex 4, S2 23; S2 = Semantic Scholar citation calls), 4446 raw hits, 3798 unique records after de-duplication against both earlier audits (618 seen before and re-screened), 2925 in the 2026 window, 2379 passing the lane keyword pre-screen, 577 title/abstract-screened by hand, 61 scored on the O/I/C rubric (5 occupies, 52 adjacent, 4 irrelevant). 84 new quote records: 80 Table 92e quotes (64 VERIFIED on versioned full text, 12 VERIFIED-ABSTRACT, 4 VERIFIED-BLOG/documentation) plus 4 venue-page confirmations; 0 unverified. A live second pass with the skill's fetch_grep re-matched 84/84. A same-agent re-screen of 54 hits gave observed agreement 0.981 and Cohen's kappa 0.791 (consistency, not independence: one screener). No OpenRouter calls were made; the built-in WebSearch tool used for E6 returns model-written result summaries, which served only to discover URLs and never as evidence.

## 2. Answer box

**FLAG E (activation quantisation changes what an activation-level intervention does): PARTLY FIRED.** No verified full text isolates ACTIVATION quantisation at matched weights and reports a changed behavioural effect of steering, noise, patching or ablation, so the flag does not fire. The nearest full text is weight-only: Steering Under Compression [1] keeps activations in FP16/BF16 and states: "We study only bitsandbytes weight-only quantization (INT8, NF4); activation quantization (W8A8, W4A4) and outlier-aware weight algorithms (GPTQ, AWQ, SmoothQuant, QuaRot) are excluded by design and may behave differently." PAHQ [4] quantises weights and activations together (FP32 vs 8-bit RTN) and finds that activation-patching circuit discovery fails: "when precision is reduced from 32 bits to 8 bits, direct quantization (also called Round-to-Nearest Quantization, RTN-Q) significantly increases the minimum quantization step size, causing activation values below this threshold to be truncated to zero and ultimately rendering the automated circuit discovery method ineffective." Two contemporaneous ICLR 2027 submissions (abstract only; PDFs HTTP 403) report the general effect without saying whether activations are quantised: "Preserving standard model quality or direction-level representation similarity does not guarantee that the intervention effect is preserved." [2]; "We show that ordinary output fidelity alone does not guarantee preservation of responses to the same intervention." [3].

**FLAG L (base-model forecast of where a perturbed tuned model lands, scored against the tuned model's own tail or likelihood): PARTLY FIRED.** No paper forecasts, from the base model, which enumerated alternative a perturbed tuned model lands on and scores that forecast against the tuned model's own sampled tail or likelihood ranking, so the flag does not fire. Fine-tuning-perturbation work reports reversion toward base behaviour at distribution or likelihood level. The closest candidate is retrospective: "The aligned model (instruct) sharply suppresses the likelihood of the harmful generation. In contrast, both the base and misaligned models assign significantly higher probabilities to the same tokens. They do so with strikingly similar distributions." [31]. The others are distribution-level rebound [32, 33] and a prospective direction toward base-descended helpful-only states scored against a matched geometric null [34]. Token-level candidate preservation is adjacent [30, 60, 61]. The rival the run must beat has support: "We observe that the top-ranked tokens in jailbroken LLMs are largely found within the top ten tokens ranked by safe LLMs." [35].

### 2.1 Verdict per claim (lane verdict; deciding references)

| Claim | Verdict | Deciding references | Note |
|---|---|---|---|
| L1a landing = base runner-up, forecast in advance | ADJACENT at algorithm level; concept partly occupied ('fine-tune-perturbed tuned models revert toward base behaviour') | [31, 32, 33, 34, 30, 60, 61, 38] | all fine-tuning perturbations, distribution/likelihood/token level; sealed base forecasts exist only for circuit change [38] |
| L1b scored against q_lik and q_tail | OPEN to our knowledge; rival-supporting evidence exists | [35, 36, 37, 63] | the tuned model's own ranking/subspace already contains landings in these settings |
| L2 support | ADJACENT / supporting | [40, 30, 91, 90] | theory and token-level evidence that post-training stays within base support |
| L3 power shape | ADJACENT / stylised | [41, 62] | power sampling of the base matches GRPO in-domain; no fit against rivals on a perturbed tuned model |
| E engine control (2x2 factorial) | PARTLY OCCUPIED (general precision-dependence of steering effects: contemporaneous, abstract-level) | [2, 3, 1, 4, 8] | activation-vs-weight attribution not found in any verified text |
| E-attribution (absmax/scale readout) | ADJACENT | [10, 16, 15, 11, 21, 22, 23] | scale-factor mechanisms are documented for KV cache and perplexity, not for nudges |
| E-deployment ('same default, different nudgeability') | GENERAL form OCCUPIED (activation-side KV-cache quantisation silently changes refusals at ~flat perplexity; flips at matched accuracy); nudgeability form open | [10, 18, 3, 99, 100, 19] | premise supported: per-token-scaled FP8 W8A8 is accuracy-lossless [19]; frame the finding as an instance of a known deployment hazard |
| S-a..S-d site at matched dose | PARTLY OCCUPIED (inherited site comparisons for narratives/test coverage); FLAG S not fired | [69, 70, 71, 42, 43, 72, 73] | no matched-dose comparison of prefill bands vs read position vs condition vs generated tokens on a categorical choice |
| F1 fork / entrance | CROWDED-ADJACENT | [44, 46, 47, 48, 49, 50, 68] | fork finding is published; the run's contribution is the margin readout at the algorithm opening |
| F2 margin bounds temperature | GENERAL margin mechanism OCCUPIED (precision flips); temperature form is textbook (logit/T) | [17, 54, 16, 51, 53, 75] | present as a diagnostic/application, not a finding |
| K knobs priced on algorithm labels | PARTLY OCCUPIED (base merging restores diversity on code benchmarks; weight averaging; base-aligned collaboration); FLAG K not fired | [57, 56, 55, 79, 83, 85, 84, 82, 43] | no test-checked algorithm-level labels in any neighbour |
| G scope | unchanged (no new search) | [92, 93] | cross-reference to 92c C3ca/C3cb |

### 2.2 Permitted wording (dated; 'first' is never licensed by a search)

- **L1a/L1b.** "Fine-tuning-perturbation studies report that tuned models revert toward base-model behaviour, at the level of output distributions, sequence likelihoods or activation-space directions [31, 32, 33, 34]. At the token level, post-training mostly reorders candidates the base model already ranks highly [60, 30, 61]. To our knowledge (dated search 2026-10-21/22; evidence/), no prior work commits in advance to an algorithm-level forecast, from the base model's composition, of which alternative a content-free perturbation of a tuned model lands on, and scores it against the tuned model's own likelihood ranking and sampled tail." The run must report the rival result even if it is unfavourable. The tuned model's own top-k contains jailbroken landings [35], and its own subspace forecasts fine-tuning landings [36].
- **E.** "Contemporaneous work reports that the behavioural effect of a fixed steering intervention need not survive quantisation even when output fidelity and direction similarity are preserved [2, 3]. Weight-only quantisation preserves steering directions [1], and joint 8-bit weight-activation quantisation disables patching-based circuit discovery [4]. To our knowledge (dated search), no verified full text separates activation from weight precision for activation-level interventions. Our 2x2 factorial does so for content-free nudges on a production FP8 W8A8 engine." If [2] or [3] turn out to quantise activations, write 'replicates ... in a new setting (content-free nudges, test-checked code-algorithm choice)'.
- **E-deployment.** "FP8 W8A8 with dynamic per-token activation scales is reported to be accuracy-lossless [19]. Yet, like activation-side KV-cache quantisation, which removes refusals at near-unchanged perplexity [10], and compression flips at matched accuracy [18], [result] shows that nudgeability is a deployment property not captured by default-output fidelity." Present it as an instance of a known hazard class, not a new class.
- **S.** "Site comparisons for noise-based diversity exist for narratives and test coverage [69, 70] and at text level [71]; we compare activation sites at matched per-position dose on a categorical, test-checked algorithm choice."
- **F1/F2.** "Forking tokens and entrance decisions are established [44, 46, 48, 49]. A top-two logit margin is known to govern which decisions flip under small numerical perturbations [17, 54]. We use the twin model's teacher-forced margin between algorithm openings to bound the effect of temperature on the algorithm choice." This describes a diagnostic, not a discovery.
- **K.** "Merging a fine-tuned model with its base restores output diversity [57, 85, 83], and pre/post-RLHF weight averaging trades alignment against forgetting [56]. We price these knobs on test-checked algorithm-level labels against base intent, enumerate-and-pick and plan noise."

### 2.3 Reviewer baselines this search implies

- **Precision arms.** Use a weight-only FP8 W8A16 kernel vs an FP8 W8A8 kernel at identical weights, and add an activation-only W16A8 fake-quant arm. Report the engine's actual scheme: the released Qwen3-8B-FP8 checkpoint uses fine-grained block-128 FP8 [26], while vLLM FP8_DYNAMIC uses per-channel weight scales and dynamic per-token activation scales [27]. Unscaled casting is a different regime [11, 4].
- **Numerics controls.** Add a kernel-swap arm at a fixed quantisation config [15], batch-invariant or fixed-batch execution [14, 12], weights-through-16-bit-kernels [16], and BF16 vs FP16 at the same weights [17].
- **Fidelity metrics from the closest neighbours.** Report steered-output KL vs unsteered-output KL [3] and a signed intervention-fidelity gap with a first-order local-sensitivity predictor [2], so the run's effect can be compared with theirs.
- **Landing rivals.** Compare q_lik (the teacher-forced ranking of the tuned model), q_tail (its sampled tail), the rebound/pre-training baseline [32], and token-level base top-k overlap [30].
- **Knobs.** Sweep base/instruct weight interpolation over lambda [55, 56]. Add base merging [57], BACo [79], proxy tuning/EFT [88, 87] and prefix perturbation at the fork [43], all against a temperature baseline.

## 3. Table 92e (paste-ready; same columns as 92d)

| Row | Claim (one line) | Neighbour (authors, arXiv v1 year, venue status) | Verbatim quote | URL; section; version | Retrieved | Relation | What this run adds, or 'replication' |
|---|---|---|---|---|---|---|---|
| 92e-Ea | E: is Qwen3-8B's plan-site sensitivity a property of its FP8 W8A8 engine (2x2 weight-by-activation factorial)? | Bhandari & Wade, 2026, arXiv preprint [1] | "We study only bitsandbytes weight-only quantization (INT8, NF4); activation quantization (W8A8, W4A4) and outlier-aware weight algorithms (GPTQ, AWQ, SmoothQuant, QuaRot) are excluded by design and may behave differently." | https://arxiv.org/html/2609.06473v1; Sec. 6 (Limitations); v1 | 2026-10-21 | adjacent; FLAG E partly (weight-only) [VERIFIED] | the activation-side arms (W16A8, W8A8) this neighbour excludes by design; 2x2 W8A8/W8A16/W16A8/W16A16 factorial with identical hook code, per-position doses and CRN slots; content-free random nudges; categorical test-checked algorithm labels; per-token absmax/FP8-scale readouts |
| 92e-Eb | E: is Qwen3-8B's plan-site sensitivity a property of its FP8 W8A8 engine (2x2 weight-by-activation factorial)? | Bhandari & Wade, 2026, arXiv preprint [1] | "Activations remain in FP16/BF16 throughout the forward pass. This isolates the primary comparison to weight quantization." | https://arxiv.org/html/2609.06473v1; Sec. 3.2 (Models and Quantization Schemes); v1 | 2026-10-21 | adjacent; FLAG E partly (weight-only) [VERIFIED] | an activation-precision factor at matched weights (W16A8 vs W16A16) on the same hooks |
| 92e-Ec | E: is Qwen3-8B's plan-site sensitivity a property of its FP8 W8A8 engine (2x2 weight-by-activation factorial)? | Bhandari & Wade, 2026, arXiv preprint [1] | "Despite this, steering vectors remain highly collinear with their FP16 siblings (cosine similarity 0.989-0.998 for INT8, 0.945-0.990 for NF4), confirming that the behavioral direction survives quantization even when the cost structure does not." | https://arxiv.org/html/2609.06473v1; Abstract; v1 | 2026-10-21 | adjacent (internal outcome: vector cosine) [VERIFIED] | a behavioural, categorical outcome at matched nudge (not vector cosine); direction is fixed (random nudges are not re-extracted per precision) |
| 92e-Ed | E: is Qwen3-8B's plan-site sensitivity a property of its FP8 W8A8 engine (2x2 weight-by-activation factorial)? | Bhandari & Wade, 2026, arXiv preprint [1] | "Steering vectors extracted independently per scheme (same contrast pairs, same resample) are nearly collinear with their FP16 siblings" | https://arxiv.org/html/2609.06473v1; Sec. 4.5; v1 | 2026-10-21 | adjacent (vectors recomputed per precision: C = 0.5) [VERIFIED] | the same nudge vector and CRN seed across precisions (no re-extraction) |
| 92e-Ee | E: is Qwen3-8B's plan-site sensitivity a property of its FP8 W8A8 engine (2x2 weight-by-activation factorial)? | Anonymous, 2026, ICLR 2027 desk-rejected submission (abstract) [2] | "Preserving standard model quality or direction-level representation similarity does not guarantee that the intervention effect is preserved." | https://api2.openreview.net/notes/search?term=Stable%20Directions%2C%20Different%20Effects%3A%20Intervention%2...; Abstract (OpenReview API record; keywords 'model quantization', 'cross-precision transfer'); - | 2026-10-21 | occupies the general claim (precision factor unstated); FLAG E unresolved-partly [VERIFIED-ABSTRACT] | if its full text varies weights only: the activation factor; if it includes activations: replication with content-free nudges on code-algorithm choice |
| 92e-Ef | E: is Qwen3-8B's plan-site sensitivity a property of its FP8 W8A8 engine (2x2 weight-by-activation factorial)? | Anonymous, 2026, ICLR 2027 desk-rejected submission (abstract) [2] | "Intervention effects can change even when directions remain strongly aligned" | https://api2.openreview.net/notes/search?term=Stable%20Directions%2C%20Different%20Effects%3A%20Intervention%2...; Abstract (OpenReview API record); - | 2026-10-21 | occupies the general claim; FLAG E unresolved-partly [VERIFIED-ABSTRACT] | a per-position dose and categorical-choice readout, and an attribution factorial |
| 92e-Eg | E: is Qwen3-8B's plan-site sensitivity a property of its FP8 W8A8 engine (2x2 weight-by-activation factorial)? | Anonymous, 2026, ICLR 2027 submission (abstract) [3] | "We study steering compatibility with the intervention layer, direction, and strength held fixed across full-precision and quantized models." | https://api2.openreview.net/notes/search?term=Activation%20Steering%20under%20Low-Bit%20Quantization%3A%20A%20...; Abstract (OpenReview API record; keywords 'Quantization', 'Activation Steering'); - | 2026-10-21 | occupies the general claim (scheme unstated; calibration/reconstruction language suggests weight PTQ); FLAG E unresolved-partly [VERIFIED-ABSTRACT] | per-token-scaled FP8 W8A8 production kernels vs weight-only arms; random (content-free) nudges, not a fixed steering vector |
| 92e-Eh | E: is Qwen3-8B's plan-site sensitivity a property of its FP8 W8A8 engine (2x2 weight-by-activation factorial)? | Anonymous, 2026, ICLR 2027 submission (abstract) [3] | "We show that ordinary output fidelity alone does not guarantee preservation of responses to the same intervention." | https://api2.openreview.net/notes/search?term=Activation%20Steering%20under%20Low-Bit%20Quantization%3A%20A%20...; Abstract (OpenReview API record); - | 2026-10-21 | occupies the general claim; FLAG E unresolved-partly [VERIFIED-ABSTRACT] | the same, plus test-checked algorithm labels instead of response/KL fidelity |
| 92e-Ei | E: is Qwen3-8B's plan-site sensitivity a property of its FP8 W8A8 engine (2x2 weight-by-activation factorial)? | Wang et al., 2025, arXiv preprint [4] | "We directly applied quantization from 32 bits to 8 bits to all weights and activations of the model Radford et al. (2019) in the ACDC Conmy et al. (2023) method, which is called Round-to-Nearest Quantization (RTN-Q), on the Indirect Object Identification (IOI) task Wang et al. (2022) and tested its performance." | https://arxiv.org/html/2510.23264v1; Sec. 2 (Direct Quantization Does Not Work on ACDC); v1 | 2026-10-21 | adjacent; FLAG E partly (weights and activations quantised jointly; circuit-recovery outcome) [VERIFIED] | weights and activations varied SEPARATELY; behavioural algorithm choice of an 8B instruct model instead of circuit-recovery AUC on GPT-2 |
| 92e-Ej | E: is Qwen3-8B's plan-site sensitivity a property of its FP8 W8A8 engine (2x2 weight-by-activation factorial)? | Wang et al., 2025, arXiv preprint [4] | "when precision is reduced from 32 bits to 8 bits, direct quantization (also called Round-to-Nearest Quantization, RTN-Q) significantly increases the minimum quantization step size, causing activation values below this threshold to be truncated to zero and ultimately rendering the automated circuit discovery method ineffective." | https://arxiv.org/html/2510.23264v1; Sec. 1 (Introduction); v1 | 2026-10-21 | adjacent; FLAG E partly [VERIFIED] | per-token-scaled FP8 (no fixed 2^-6 floor), so the underflow mechanism is tested rather than assumed; absmax/scale readouts |
| 92e-Ek | E: is Qwen3-8B's plan-site sensitivity a property of its FP8 W8A8 engine (2x2 weight-by-activation factorial)? | Wang et al., 2025, arXiv preprint [4] | "This means that if the difference between inference outputs before and after replacing activation values of selected edges is less than the minimum quantization step size, this difference will be truncated to zero." | https://arxiv.org/html/2510.23264v1; Sec. 2 (Numerical Underflow); v1 | 2026-10-21 | adjacent; FLAG E partly (mechanism is unscaled-format underflow) [VERIFIED] | measured per-position displacement after quantisation of the nudged state |
| 92e-El | E: is Qwen3-8B's plan-site sensitivity a property of its FP8 W8A8 engine (2x2 weight-by-activation factorial)? | Baligar, 2026, Computation (journal) [5] | "In matched float32/float64 experiments, at a descriptive 3 [...] floor, 13.0% and 51.2% of full-displacement interactions fell below the threshold" | https://api.semanticscholar.org/graph/v1/paper/DOI:10.3390/computation14090212?fields=title,abstract,venue,pub...; Abstract (Semantic Scholar API record; publisher page https://www.mdpi.com/2079-3197/14/9/212 returned HTTP 403); - | 2026-10-21 | adjacent; FLAG E partly (numerics precision floor; internal outcome; not activation quantisation) [VERIFIED-ABSTRACT] | 8-bit activation precision (not fp32/fp64) and a behavioural outcome |
| 92e-Em | E: is Qwen3-8B's plan-site sensitivity a property of its FP8 W8A8 engine (2x2 weight-by-activation factorial)? | Anonymous, 2026, ICLR 2027 submission (abstract) [6] | "On disagreeing inputs, we add these projections at their native magnitude to the quantized residual state, testing agreement with the original full-precision prediction regardless of correctness." | https://api2.openreview.net/notes/search?term=Quantization-Induced%20Decision%20Changes%20Have%20Regime-Depend...; Abstract (OpenReview API record); - | 2026-10-21 | adjacent (method-overlap: activation additions on quantised residual states as a repair) [VERIFIED-ABSTRACT] | nudges as the object of study (does precision change what a nudge does), not as a repair of flips |
| 92e-En | E: is Qwen3-8B's plan-site sensitivity a property of its FP8 W8A8 engine (2x2 weight-by-activation factorial)? | Anonymous, 2026, ICLR 2027 submission (abstract) [7] | "Targeted interventions link these changes to predictions: replacing selected quantized activations with their high-precision values can reverse naturally corrected answers" | https://api2.openreview.net/notes/search?term=When%20Quantization%20Helps%3A%20Corrective%20Computation%20in%2...; Abstract (OpenReview API record); - | 2026-10-21 | adjacent (weight-only GPTQ/AWQ/NF4; patching used to analyse quantisation) [VERIFIED-ABSTRACT] | activation-side precision; content-free nudges |
| 92e-Eo | E: is Qwen3-8B's plan-site sensitivity a property of its FP8 W8A8 engine (2x2 weight-by-activation factorial)? | Bonás et al., 2026, arXiv preprint [8] | "We explore 16-bit (BF16) and 4-bit (NF4) versions of smaller models to expose harmful tool-call compliance and estimate intervention directions." | https://arxiv.org/html/2610.20808v1; Sec. 1 (Introduction); v1 | 2026-10-21 | adjacent; FLAG E partly (weight-only NF4; directions transferred across precision) [VERIFIED] | the activation factor; the same intervention applied at both precisions |
| 92e-Ep | E: is Qwen3-8B's plan-site sensitivity a property of its FP8 W8A8 engine (2x2 weight-by-activation factorial)? | Bonás et al., 2026, arXiv preprint [8] | "Directions using NF4 labels act directly on the original BF16 model’s activations." | https://arxiv.org/html/2610.20808v1; Sec. 2.2 (Compression as behavioral supervision); v1 | 2026-10-21 | adjacent [VERIFIED] | same, with matched weights |
| 92e-Eq | E: is Qwen3-8B's plan-site sensitivity a property of its FP8 W8A8 engine (2x2 weight-by-activation factorial)? | Mishra et al., 2026, ICLR 2026 workshops [9] | "Noticeably, our theoretical claim does not cover quantization effects. However, we experiment with an INT4 quantized model and find that our empirical claims hold comfortably in this setting (§D)." | https://arxiv.org/html/2604.09839v2; Sec. 7 (Conclusion and Limitations; App. D); v2 | 2026-10-21 | context (new finding vs inherited rows 92b-b7c / 92c-C2-geod) [VERIFIED] | a behavioural test under activation quantisation |
| 92e-Er | E-deployment: activation quantisation changes nudgeability while default output and accuracy are unchanged | Xu et al., 2026, arXiv preprint [10] | "we find that low-bit quantization can silently destroy safety alignment (Mistral-7B loses 15.2% of its refusals at only 1.03× perplexity" | https://arxiv.org/pdf/2606.09864v2; Abstract (PDF p. 1); v2 | 2026-10-21 | adjacent (activation-side KV-cache quantisation changes behaviour; no activation-level intervention) [VERIFIED] | nudgeability (response to a fixed content-free nudge) rather than default behaviour; W8A8 matmul activations rather than KV cache |
| 92e-Es | E-attribution: activation vs weight precision; per-token absmax / FP8-scale readouts | Xu et al., 2026, arXiv preprint [10] | "where safety lives in non-outlier channels collaterally damaged by outlier-driven scale factors" | https://arxiv.org/pdf/2606.09864v2; Abstract (PDF p. 1); v2 | 2026-10-21 | adjacent (scale-factor mechanism analogous to per-token absmax readouts) [VERIFIED] | per-token absmax and FP8 scale readouts at the nudged positions (analogous mechanism, different site) |
| 92e-Et | E: is Qwen3-8B's plan-site sensitivity a property of its FP8 W8A8 engine (2x2 weight-by-activation factorial)? | Silva et al., 2026, PROPOR 2026 [11] | "INT8 with outlier handling preserves perplexity in both languages, while naive FP8 casting degrades English far more than PT-BR (+18% vs. +3.9%)." | https://aclanthology.org/2026.propor-1.108/; Abstract (ACL Anthology page; PDF pp. 1044-1048); - | 2026-10-21 | adjacent (no intervention; naive unscaled E4M3 casting) [VERIFIED] | per-token-scaled FP8 W8A8 (dynamic scales), not unscaled casting; interventions |
| 92e-Eu | E: is Qwen3-8B's plan-site sensitivity a property of its FP8 W8A8 engine (2x2 weight-by-activation factorial)? | Silva et al., 2026, PROPOR 2026 [11] | "Our FP8 results reflect a naive casting stress test (no calibration/scaling), not an optimized FP8 recipe." | https://aclanthology.org/2026.propor-1.108/; Abstract (ACL Anthology page); - | 2026-10-21 | adjacent (scope: not per-token-scaled W8A8) [VERIFIED] | the production recipe this stress test excludes |
| 92e-Ev | E: is Qwen3-8B's plan-site sensitivity a property of its FP8 W8A8 engine (2x2 weight-by-activation factorial)? | Yuan et al., 2025, NeurIPS 2025 oral [12, 13] | "For instance, under bfloat16 precision with greedy decoding, a reasoning model like DeepSeek-R1-Distill-Qwen-7B can exhibit up to 9% variation in accuracy and 9,000 tokens difference in response length due to differences in GPU count, type, and evaluation batch size." | https://arxiv.org/html/2506.09501v2; Abstract (v2); v2 | 2026-10-21 | adjacent (numerics change outputs; no intervention) [VERIFIED] | numerics controls (batch size 1, fixed kernels) so that precision, not batching, explains any difference |
| 92e-Ew | E: is Qwen3-8B's plan-site sensitivity a property of its FP8 W8A8 engine (2x2 weight-by-activation factorial)? | He / Thinking Machines, 2025, blog [14] | "Surprisingly, we generate 80 unique completions" | https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/; Experiments ('How nondeterministic are completions?'); - | 2026-10-21 | context (batch-dependent numerics; the run's model family) [VERIFIED-BLOG] | batch-invariant / fixed-batch execution as a control arm |
| 92e-Ex | E: is Qwen3-8B's plan-site sensitivity a property of its FP8 W8A8 engine (2x2 weight-by-activation factorial)? | He / Thinking Machines, 2025, blog [14] | "it's because our forward pass lacks "batch invariance", causing our request's output to depend on the batch size of our forward pass." | https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/; Batch invariance and 'determinism'; - | 2026-10-21 | context (reviewer baseline: batch-invariant kernels) [VERIFIED-BLOG] | same |
| 92e-Ey | E: is Qwen3-8B's plan-site sensitivity a property of its FP8 W8A8 engine (2x2 weight-by-activation factorial)? | Chen, 2026, arXiv preprint [15] | "At 1.7B each arm reproduces itself bit-for-bit across cold restarts, yet the arms agree on no sequence in any end-to-end comparison we ran (0/8, 0/16, and 0/64)." | https://arxiv.org/html/2608.13756v2; Abstract; v2 | 2026-10-21 | context (reviewer baseline: kernel-swap control at fixed W8A8 config) [VERIFIED] | kernel-swap control at fixed W8A8 config (reviewer baseline), to separate kernel numerics from quantisation |
| 92e-Ez | E-attribution: activation vs weight precision; per-token absmax / FP8-scale readouts | Patodiya, 2026, arXiv preprint [16] | "Serving four-bit weights through 16-bit kernels left divergence not detectably different from 16-bit, placing the amplification mainly in the quantized execution path." | https://arxiv.org/html/2609.04748v2; Abstract; v2 | 2026-10-21 | adjacent (weights-vs-execution-path control for numerics divergence, not for interventions) [VERIFIED] | the same separation (weights vs execution path) applied to nudge effects |
| 92e-Eaa | E: is Qwen3-8B's plan-site sensitivity a property of its FP8 W8A8 engine (2x2 weight-by-activation factorial)? | Du et al., 2026, TMLR [17] | "With FP8 confined to the head projection, a format-rescaled gate achieves exact agreement on TinyLlama and +56pp on Qwen2.5-3B." | https://arxiv.org/pdf/2609.26621v1; Sec. 1 (Introduction), p. 2; v1 | 2026-10-21 | context (numerics; end-to-end FP8 divergence is body-dominated) [VERIFIED] | end-to-end W8A8 vs weight-only arms with interventions |
| 92e-Eab | E-deployment: activation quantisation changes nudgeability while default output and accuracy are unchanged | Dutta et al., 2024, NeurIPS 2024 [18] | "However, even when the accuracy of baseline and compressed model are similar, we observe the phenomenon of flips, wherein answers change from correct to incorrect and vice versa in proportion." | https://arxiv.org/html/2407.09141v1; Abstract; v1 | 2026-10-21 | adjacent (deployment analogue: same accuracy, different behaviour) [VERIFIED] | flip-style audit of nudge responses at matched default accuracy |
| 92e-Eac | E-attribution: activation vs weight precision; per-token absmax / FP8-scale readouts | Xiao et al., 2022, ICML 2023 [21] | "Based on the fact that weights are easy to quantize while activations are not, SmoothQuant smooths the activation outliers by offline migrating the quantization difficulty from activations to weights with a mathematically equivalent transformation." | https://arxiv.org/html/2211.10438v7; Abstract; v7 | 2026-10-21 | context (mechanism anchor; per-token activation scales) [VERIFIED] | readout of which activations carry outliers at nudged positions |
| 92e-Ead | E-attribution: activation vs weight precision; per-token absmax / FP8-scale readouts | Dettmers et al., 2022, NeurIPS 2022 [22] | "the sparse but systematic large magnitude outlier features that ruin quantization precision once they emerge in all transformer layers starting at scales of 6.7B parameters" | https://arxiv.org/html/2208.07339v2; Sec. 1 (Introduction); v2 | 2026-10-21 | context (mechanism anchor) [VERIFIED] | context only |
| 92e-Eae | E-attribution: activation vs weight precision; per-token absmax / FP8-scale readouts | Sun et al., 2024, COLM 2024 [23] | "Many of these activations are found within the starting word token and delimiter tokens." | https://arxiv.org/html/2402.17762v2; Sec. 1 (Introduction); v2 | 2026-10-21 | context (position-specific spikes drive per-token scales) [VERIFIED] | per-token scales at task-spec vs read positions (massive-activation tokens set the scale) |
| 92e-Eaf | E-attribution: activation vs weight precision; per-token absmax / FP8-scale readouts | Sun et al., 2024, COLM 2024 [23] | "We show that massive activations act as fixed but crucial bias terms in LLMs." | https://arxiv.org/html/2402.17762v2; Sec. 1 (Introduction); v2 | 2026-10-21 | context [VERIFIED] | context only |
| 92e-Eag | E: is Qwen3-8B's plan-site sensitivity a property of its FP8 W8A8 engine (2x2 weight-by-activation factorial)? | Micikevicius et al., 2022, arXiv preprint [24] | "we propose an 8-bit floating point (FP8) binary interchange format consisting of two encodings - E4M3 (4-bit exponent and 3-bit mantissa) and E5M2 (5-bit exponent and 2-bit mantissa)." | https://arxiv.org/html/2209.05433v2; Abstract; v2 | 2026-10-21 | context (format definition) [VERIFIED] | context only (E4M3 range 448) |
| 92e-Eah | E-deployment: activation quantisation changes nudgeability while default output and accuracy are unchanged | Hong et al., 2024, ICML 2024 [25] | "For instance, a 4-bit quantized model retains the trustworthiness of its original counterpart, but model pruning significantly degrades trustworthiness, even at 50% sparsity." | https://arxiv.org/html/2403.15447v3; Abstract; v3 | 2026-10-21 | context (weight quantisation and behaviour) [VERIFIED] | context only |
| 92e-Eai | E: is Qwen3-8B's plan-site sensitivity a property of its FP8 W8A8 engine (2x2 weight-by-activation factorial)? | Qwen team, model card [26] | "The quantization method is fine-grained `fp8` quantization with block size of 128." | https://huggingface.co/Qwen/Qwen3-8B-FP8; Model card, 'Note on FP8'; - | 2026-10-21 | documentation (methods row; never a verdict) [VERIFIED-BLOG] | states which checkpoint/engine scheme the run used (block-128 fine-grained FP8 vs dynamic per-token) |
| 92e-Eaj | E: is Qwen3-8B's plan-site sensitivity a property of its FP8 W8A8 engine (2x2 weight-by-activation factorial)? | vLLM docs [27] | "Dynamic, per-token quantization on the activations" | https://docs.vllm.ai/en/stable/features/quantization/llm_compressor/fp8/; '2. Applying Quantization'; - | 2026-10-21 | documentation (what W8A8 FP8_DYNAMIC means; never a verdict) [VERIFIED-BLOG] | same |
| 92e-Eak | E-attribution: activation vs weight precision; per-token absmax / FP8-scale readouts | Azizi et al., 2026, NeurIPS 2026 poster [28] | "Its top eigenvectors are sharp directions: tiny perturbations along them can cause large, erratic, input-dependent behavioral swings." | https://neurips.cc/virtual/2026/poster/151909; Abstract (NeurIPS 2026 poster page); - | 2026-10-21 | context (why small numeric perturbations of a nudge can change behaviour; no precision factor) [VERIFIED-ABSTRACT] | context: why small numeric perturbations of a nudge could matter |
| 92e-Eal | E: is Qwen3-8B's plan-site sensitivity a property of its FP8 W8A8 engine (2x2 weight-by-activation factorial)? | 2026, arXiv preprint (abstract) [29] | "We apply it to GLM-5.3-Flash (320B parameters, 288 routed experts, a four-wide hyper-connection residual, block-FP8)." | https://arxiv.org/abs/2609.09793; Abstract (arXiv abs page); - | 2026-10-21 | context (activation-direction edit on a block-FP8 checkpoint; no precision contrast) [VERIFIED-ABSTRACT] | a precision contrast |
| 92e-Eam | E-deployment: activation quantisation changes nudgeability while default output and accuracy are unchanged | Kurtic et al., 2024, ACL 2025 [19] | "W8A8-FP quantization is essentially lossless, preserving the uncompressed model’s accuracy across all benchmarks, often within the evaluation’s margin of error. This result is achieved with a simple yet robust approach: dynamic per-token activation quantization combined with symmetric weight quantization via round-to-nearest assignment." | https://arxiv.org/html/2411.02355v4; Sec. 1 (main findings); v4 | 2026-10-21 | supports the premise (default accuracy is preserved under per-token-scaled FP8 W8A8); no intervention [VERIFIED] | the nudgeability half of the claim: a fixed content-free nudge's effect at this accuracy-lossless setting |
| 92e-L1a | L1a: a content-free nudge or ban moves the tuned model onto its BASE model's runner-up algorithm, forecast in advance | Meng et al., 2026, ICLR 2026 [30] | "Around 30% of RL top-1 tokens are already ranked first under the base model, and over 80% (DAPO) and 90% (SimpleRL) fall within the base top-3." | https://arxiv.org/html/2603.22446v1; Sec. 4 (rank-shift analysis, Figure 22 discussion); v1 | 2026-10-21 | adjacent (token-level, retrospective, no perturbation of the tuned model) [VERIFIED] | algorithm-level (test-checked) landing under a content-free perturbation, forecast before the outcome |
| 92e-L1b | L1a: a content-free nudge or ban moves the tuned model onto its BASE model's runner-up algorithm, forecast in advance | Meng et al., 2026, ICLR 2026 [30] | "This observation is further clarified in Figure 22, which shows where the RL model’s top-3 tokens appear in the base model’s ranking, among high divergence positions." | https://arxiv.org/html/2603.22446v1; Sec. 4 (scope of the figure); v1 | 2026-10-21 | adjacent (scope: high-divergence positions, JS > 0.1) [VERIFIED] | the run's landings are scored on all positions of the algorithm opening, not only high-divergence ones |
| 92e-L1c | L1b: the base forecast beats rivals built from the tuned model (likelihood ranking q_lik, sampled tail q_tail), incl. tail-empty events | Meng et al., 2026, ICLR 2026 [30] | "inserting only a small fraction of RL-sampled tokens into base generations progressively recovers RL performance gains, while injecting a similarly small number of base token choices into otherwise RL-generated sequences collapses performance to base levels" | https://arxiv.org/html/2603.22446v1; Abstract; v1 | 2026-10-21 | adjacent (cross-sampling perturbs the tuned trajectory with base tokens; outcome is accuracy, not landing identity) [VERIFIED] | landing identity rather than accuracy recovery |
| 92e-L1d | L1b: the base forecast beats rivals built from the tuned model (likelihood ranking q_lik, sampled tail q_tail), incl. tail-empty events | Giordani, 2025, arXiv preprint [31] | "The aligned model (instruct) sharply suppresses the likelihood of the harmful generation. In contrast, both the base and misaligned models assign significantly higher probabilities to the same tokens. They do so with strikingly similar distributions." | https://arxiv.org/html/2507.03662v1; Sec. 4.1 (Behavioral Analysis: Misaligned Model Reverts to Base Behavior); v1 | 2026-10-21 | adjacent; FLAG L partly ((ii)+(iii) retrospective, sequence likelihood) [VERIFIED] | a prospective (sha256-committed) forecast, enumerated algorithm labels, and explicit q_lik/q_tail rivals |
| 92e-L1e | L1a: a content-free nudge or ban moves the tuned model onto its BASE model's runner-up algorithm, forecast in advance | Giordani, 2025, arXiv preprint [31] | "we propose that these behaviors can be better understood as a regression to base model behavior." | https://arxiv.org/html/2507.03662v1; Sec. 1 (Introduction); v1 | 2026-10-21 | adjacent; FLAG L partly [VERIFIED] | same; content-free nudge instead of fine-tuning |
| 92e-L1f | L1a: a content-free nudge or ban moves the tuned model onto its BASE model's runner-up algorithm, forecast in advance | Giordani, 2025, arXiv preprint [31] | "Values are averaged over a set of 400 examples from each dataset." | https://arxiv.org/html/2507.03662v1; App. B.2 (Table 2 caption; rendered next to App. A in the HTML); v1 | 2026-10-21 | adjacent (scale of the likelihood comparison) [VERIFIED] | context (scale) |
| 92e-L1g | L1a: a content-free nudge or ban moves the tuned model onto its BASE model's runner-up algorithm, forecast in advance | Ji et al., 2024, ACL 2025 [32] | "Fine-tuning in the opposite direction of post-training (e.g., safe vs. unsafe) causes post-trained models to return quickly to the pre-training distribution." | https://arxiv.org/html/2406.06144v6; Sec. 5 (How Elasticity Resists Alignment?); v6 | 2026-10-21 | adjacent; FLAG L partly ((i)+(ii) at distribution/score level, no tuned-model rival) [VERIFIED] | identity-level forecast at the algorithm level vs a distribution/score-level rebound |
| 92e-L1h | L1a: a content-free nudge or ban moves the tuned model onto its BASE model's runner-up algorithm, forecast in advance | Huang et al., 2026, arXiv preprint [33] | "The Rebound Effect [14] refers to the tendency of fine-tuned models to revert toward their pre-trained state under reversed or perturbed fine-tuning." | https://arxiv.org/html/2605.18309v1; Sec. 3 (Revisiting Rebound Effect); v1 | 2026-10-21 | adjacent (rebound dynamics) [VERIFIED] | same |
| 92e-L1i | L1a: a content-free nudge or ban moves the tuned model onto its BASE model's runner-up algorithm, forecast in advance | Poppi & Lukas, 2026, arXiv preprint [34] | "We instead cast it as a single activation-space direction, pointing from the safety-aligned model toward independently built helpful-only states rather than toward the base model itself, and fixed before the prospective target trajectories are trained" | https://arxiv.org/html/2606.28525v2; Sec. 1 (Introduction); v2 | 2026-10-21 | adjacent; FLAG L partly ((i)+(ii) prospective; rival is a matched geometric null) [VERIFIED] | the tuned model's own tail and likelihood as rivals; base composition (not a helpful-only proxy) as the predictor |
| 92e-L1j | L1b: the base forecast beats rivals built from the tuned model (likelihood ranking q_lik, sampled tail q_tail), incl. tail-empty events | Poppi & Lukas, 2026, arXiv preprint [34] | "once we fixed the reference family and the test in advance, every additional trajectory we tried moved in the predicted direction more than its matched null" | https://arxiv.org/html/2606.28525v2; Sec. 1 (Introduction); v2 | 2026-10-21 | adjacent (prospective test against a matched null, not against the tuned model's tail) [VERIFIED] | rival scored against the tuned model, not a geometric null |
| 92e-L1k | L1b: the base forecast beats rivals built from the tuned model (likelihood ranking q_lik, sampled tail q_tail), incl. tail-empty events | Zhao et al., 2024, ICML 2025 [35] | "We observe that the top-ranked tokens in jailbroken LLMs are largely found within the top ten tokens ranked by safe LLMs." | https://arxiv.org/html/2401.17256v5; Sec. 1 (Introduction); v5 | 2026-10-21 | contradicts-in-part (the perturbed landing lies in the tuned model's OWN top-10: supports the q_lik rival at token level) [VERIFIED] | this is the rival the run must beat: q_lik (teacher-forced ranking) and q_tail |
| 92e-L1l | L1b: the base forecast beats rivals built from the tuned model (likelihood ranking q_lik, sampled tail q_tail), incl. tail-empty events | Nadaf, 2026, arXiv preprint [36] | "A persona subspace present in the model before fine-tuning carries broad misalignment. The subspace is extracted from the frozen instruction-tuned model." | https://arxiv.org/html/2607.21356v1; Fig. 1 caption; v1 | 2026-10-21 | contradicts-in-part (structure in the TUNED model forecasts where fine-tuning lands) [VERIFIED] | base vs tuned provenance of the landing structure is tested directly (base composition vs tuned ranking) |
| 92e-L1m | L1b: the base forecast beats rivals built from the tuned model (likelihood ranking q_lik, sampled tail q_tail), incl. tail-empty events | Nadaf, 2026, arXiv preprint [36] | "Provenance. The extraction is from a released instruction-tuned checkpoint, not a pre-alignment base model, so whether pretraining installed the structure or alignment post-training sharpened it is open." | https://arxiv.org/html/2607.21356v1; Sec. 9 (Limitations: Provenance); v1 | 2026-10-21 | contradicts-in-part (base vs tuned provenance left open) [VERIFIED] | same |
| 92e-L1n | L1b: the base forecast beats rivals built from the tuned model (likelihood ranking q_lik, sampled tail q_tail), incl. tail-empty events | Li et al., 2026, arXiv preprint [37] | "the representational distance between an evaluation prompt and the training data centroid, both in the base model’s activation space, strongly predicts how misaligned the finetuned model becomes on that prompt" | https://arxiv.org/html/2608.29118v1; Sec. 1 (Introduction); v1 | 2026-10-21 | context / contradicts-in-part ('base model' here = the pre-EM instruct model: a forecast from the tuned model itself) [VERIFIED] | a forecast from the BASE model, scored against forecasts from the tuned model itself |
| 92e-L1o | L1b: the base forecast beats rivals built from the tuned model (likelihood ranking q_lik, sampled tail q_tail), incl. tail-empty events | Li et al., 2026, arXiv preprint [37] | "We select models of various sizes and from multiple model families: Qwen2.5-14B-Instruct, Qwen2.5-32B-Instruct, Qwen2.5-Coder-32B-Instruct" | https://arxiv.org/html/2608.29118v1; Sec. 3 (Emergent Misalignment is Expected Generalization: Models and EM Training Data); v1 | 2026-10-21 | context (terminology: the forecasting 'base model' is instruction-tuned) [VERIFIED] | terminology guard for the paper ('base' = pretrained) |
| 92e-L1p | L1a: a content-free nudge or ban moves the tuned model onto its BASE model's runner-up algorithm, forecast in advance | Anonymous, 2026, ICLR 2027 submission (abstract) [38] | "We instead seal a per-head, signed forecast from the base model, fine-tune, and confirm it." | https://api2.openreview.net/notes/search?term=Predictive%20Mechanistic%20Interpretability%20of%20Post-Training...; Abstract (OpenReview API record); - | 2026-10-21 | adjacent (method-overlap: sealed forecasts from the base model; target is circuit change under post-training, not landing) [VERIFIED-ABSTRACT] | a committed forecast of landing identity rather than circuit change |
| 92e-L1q | L1a: a content-free nudge or ban moves the tuned model onto its BASE model's runner-up algorithm, forecast in advance | Zhou et al., 2024, ACL 2024 [39] | "our method achieves this reversal by contrasting the output token distribution of a safety-aligned language model (e.g., Llama-2-chat) against its pre-trained version (e.g., Llama-2), so that the token predictions are shifted towards the opposite direction of safety alignment." | https://arxiv.org/html/2402.12343v4; Abstract; v4 | 2026-10-21 | adjacent (base-vs-aligned contrast pushes the aligned model; no landing forecast) [VERIFIED] | context |
| 92e-L2a | L2: the perturbed tuned distribution stays inside base support | Mousavi-Hosseini & Erdogdu, 2026, ICML 2026 [40] | "However, a barrier arises for going beyond the support of the base model." | https://arxiv.org/html/2603.06957v2; Abstract; v2 | 2026-10-21 | supports (theory: policy-gradient post-training stays within base support) [VERIFIED] | empirical support test at the algorithm level |
| 92e-L3a | L3: the perturbed/tuned distribution is the base distribution raised to a power | Karan & Du, 2025, arXiv preprint [41] | "We introduce the power distribution as a useful sampling target for reasoning tasks. Since it can be explicitly specified with a base LLM, no additional training is required." | https://arxiv.org/html/2510.14901v1; Sec. 1 (contributions); v1 | 2026-10-21 | supports (stylised power account p^alpha of the base) [VERIFIED] | a fitted alpha compared with parametric rivals and the tuned tail |
| 92e-L3b | L3: the perturbed/tuned distribution is the base distribution raised to a power | Karan & Du, 2025, arXiv preprint [41] | "Our algorithm achieves comparable performance to GRPO within the posttraining domain (MATH500) but can outperform on out-of-domain tasks such as HumanEval and AlpacaEval." | https://arxiv.org/html/2510.14901v1; Fig. 1 caption; v1 | 2026-10-21 | supports [VERIFIED] | same |
| 92e-Sa | S-a: prefill task-spec states by block band as the site of content-free nudges | Wen et al., 2026, arXiv preprint [42] | "Embedding perturbation does not disrupt reasoning coherence." | https://arxiv.org/html/2602.02427v4; Sec. 3.2 (Random Perturbation); v4 | 2026-10-21 | adjacent (content-free Gaussian noise on token embeddings localises uncertain steps; no site comparison at matched dose) [VERIFIED] | matched per-position dose across sites (prefill task-spec bands vs read position vs condition vs generated tokens), categorical outcome |
| 92e-Sb | S-a: prefill task-spec states by block band as the site of content-free nudges | Wen et al., 2026, arXiv preprint [42] | "We find that the resulting continuations remain coherent and on-task." | https://arxiv.org/html/2602.02427v4; Sec. 3.2; v4 | 2026-10-21 | adjacent [VERIFIED] | same |
| 92e-Sc | S-c: condition vs generated tokens as sites | Nguyen et al., 2026, arXiv preprint [43] | "reasoning mode selection is driven by weak signals, making it a key source of instability and side effects such as coverage collapse, but also a natural point of intervention for control." | https://arxiv.org/html/2605.17026v2; Sec. 4.2 (Reasoning Mode Selection); v2 | 2026-10-21 | adjacent (decision-point fork between natural-language and code reasoning modes) [VERIFIED] | content-free nudges at the fork, with matched dose |
| 92e-Sd | F2: teacher-forced log-odds margin between algorithm openings bounds the temperature effect | Nguyen et al., 2026, arXiv preprint [43] | "We find that targeted prefix perturbation consistently outperforms temperature scaling across both model families, particularly for moderate sampling budgets (pass@8–32)" | https://arxiv.org/html/2605.17026v2; Sec. 5 (First-token Manipulation; App. C prefix perturbation vs temperature); v2 | 2026-10-21 | adjacent (prefix perturbation at forks beats temperature) [VERIFIED] | plan-state noise and base intent priced against temperature on the same test-checked labels |
| 92e-Fa | F1: the first divergence (entrance fork) decides the algorithm | Bigelow et al., 2024, ICLR 2025 [44, 45] | "We hypothesize that there exist key forking tokens, such that re-sampling the system at those specific tokens, but not others, leads to very different outcomes." | https://arxiv.org/html/2412.07961v1; Abstract; v1 | 2026-10-21 | adjacent (forks by resampling; outcome distributions) [VERIFIED] | fork position for the algorithm opening read from the twin model's teacher-forced margin |
| 92e-Fb | F1: the first divergence (entrance fork) decides the algorithm | Bigelow et al., 2024, ICLR 2025 [44, 45] | "We find many examples of forking tokens, including surprising ones such as punctuation marks, suggesting that LLMs are often just a single token away from saying something very different." | https://arxiv.org/html/2412.07961v1; Abstract; v1 | 2026-10-21 | adjacent [VERIFIED] | same |
| 92e-Fc | F1: the first divergence (entrance fork) decides the algorithm | Bigelow et al., 2026, arXiv preprint [46] | "This model uses change point detection to identify forking points, and kernel-pooling to smooth estimates between these points." | https://arxiv.org/html/2608.19611v1; Sec. 1 (contributions); v1 | 2026-10-21 | adjacent (efficient fork estimation) [VERIFIED] | context |
| 92e-Fd | F1: the first divergence (entrance fork) decides the algorithm | Bogdan et al., 2025, arXiv preprint [47] | "We term these sentences thought anchors. These are generally planning or uncertainty management sentences, and specialized attention heads consistently attend from subsequent sentences to thought anchors." | https://arxiv.org/html/2506.19143v4; Abstract; v4 | 2026-10-21 | adjacent (sentence-level resampling importance) [VERIFIED] | context |
| 92e-Fe | F1: the first divergence (entrance fork) decides the algorithm | Zhou & Li, 2026, arXiv preprint (+ ICLR 2027 submission) [48] | "we analyze the Countdown task, whose solution space can be exhaustively enumerated into discrete entrance families defined by the first operand and operator" | https://arxiv.org/html/2608.29188v1; Abstract; v1 | 2026-10-21 | adjacent (entrance = first decision; correction: now on arXiv) [VERIFIED] | the same entrance logic for code algorithms; margins rather than likelihood shifts |
| 92e-Ff | F1: the first divergence (entrance fork) decides the algorithm | Ko et al., 2026, arXiv preprint [49] | "We define the cliff token: the token in a reasoning trace where the probability of reaching the correct answer via Monte Carlo rollouts (success probability) drops significantly." | https://arxiv.org/html/2606.25524v3; Sec. 1 (Introduction); v3 | 2026-10-21 | adjacent [VERIFIED] | context |
| 92e-Fg | F1: the first divergence (entrance fork) decides the algorithm | Wang et al., 2025, NeurIPS 2025 [50] | "These findings highlight the significance of high-entropy tokens (i.e., forking tokens) to RLVR." | https://arxiv.org/html/2506.01939v2; Abstract; v2 | 2026-10-21 | adjacent [VERIFIED] | context |
| 92e-Fh | F2: teacher-forced log-odds margin between algorithm openings bounds the temperature effect | Tang et al., 2024, ACL 2025 [51, 52] | "that inadvertently include more noise tokens at higher temperatures, [...] maintains a stable sampling space regardless of temperature scaling." | https://arxiv.org/html/2411.07641v1; Abstract; v1 | 2026-10-21 | supports (a logit gap separates an informative region whose membership is temperature-invariant) [VERIFIED] | an algorithm-opening margin that bounds the temperature effect on the categorical choice (application, not mechanism) |
| 92e-Fi | F2: teacher-forced log-odds margin between algorithm openings bounds the temperature effect | Renze & Guven, 2024, Findings of EMNLP 2024 [53] | "our empirical results indicate that changes in temperature from 0.0 to 1.0 do not have a statistically significant impact on LLM performance for problem-solving tasks." | https://arxiv.org/html/2402.05201v3; Abstract; v3 | 2026-10-21 | supports (temperature-inert regime, accuracy outcome) [VERIFIED] | the margin explanation of why temperature is inert on algorithm choice |
| 92e-Fj | F2: teacher-forced log-odds margin between algorithm openings bounds the temperature effect | Du et al., 2026, TMLR [17] | "the outcome depends primarily on the top-two logit margin at the lm_head" | https://arxiv.org/pdf/2609.26621v1; Abstract (PDF p. 1); v1 | 2026-10-21 | adjacent (margin explains numerics-induced flips, not temperature) [VERIFIED] | temperature rather than precision as the perturbation explained by the margin |
| 92e-Fk | F2: teacher-forced log-odds margin between algorithm openings bounds the temperature effect | Chu et al., 2026, arXiv preprint [54] | "K/V perturbations remain flat before flips, while low top-1/top-2 logit margins expose much of the flip risk." | https://arxiv.org/html/2605.30218v1; Abstract; v1 | 2026-10-21 | adjacent (margins predict flips) [VERIFIED] | same |
| 92e-Fl | F2: teacher-forced log-odds margin between algorithm openings bounds the temperature effect | Patodiya, 2026, arXiv preprint [16] | "Near-tie decisions became only about 1.2 times as common, while the cache-path change in top-two margins grew 4.9-fold from 16-bit to three-bit." | https://arxiv.org/html/2609.04748v2; Abstract; v2 | 2026-10-21 | adjacent [VERIFIED] | same |
| 92e-Ka | K: test-checked algorithm-level prices of base intent, base/instruct interpolation, proxy tuning, enumerate-and-pick, plan noise | Wortsman et al., 2021, CVPR 2022 [55] | "Our method linearly interpolates between the zero-shot and fine-tuned models with a mixing coefficient" | https://arxiv.org/html/2109.01903v3; Fig. 1 caption; v3 | 2026-10-21 | context (definition of lambda interpolation) [VERIFIED] | lambda 0.25/0.5 between Qwen3-8B Base and Instruct, priced on test-checked algorithm labels |
| 92e-Kb | K: test-checked algorithm-level prices of base intent, base/instruct interpolation, proxy tuning, enumerate-and-pick, plan noise | Lin et al., 2023, EMNLP 2024 [56] | "In this paper we show that model averaging, which simply interpolates between pre and post RLHF model weights, surprisingly achieves the most strongest alignment-forgetting Pareto front among a wide range of competing methods." | https://arxiv.org/html/2309.06256v4; Abstract; v4 | 2026-10-21 | adjacent (base/aligned weight interpolation as a knob; outcome is forgetting, not diversity) [VERIFIED] | same, with a diversity outcome |
| 92e-Kc | K: test-checked algorithm-level prices of base intent, base/instruct interpolation, proxy tuning, enumerate-and-pick, plan noise | Anonymous, 2026, ICLR 2027 submission (abstract) [57] | "To mitigate this effect, we propose a simple recovery approach: merging the fine-tuned model with its pretrained base model before RL." | https://api2.openreview.net/notes/search?term=Should%20SFT%20Prefer%20the%20Familiar%3F%20Diversity%20Collapse...; Abstract (OpenReview API record); - | 2026-10-21 | adjacent (base/fine-tuned merging restores diversity; code-generation benchmarks) [VERIFIED-ABSTRACT] | algorithm-level, test-checked labels and a full-simplex price hull against other knobs |
| 92e-Kd | K: test-checked algorithm-level prices of base intent, base/instruct interpolation, proxy tuning, enumerate-and-pick, plan noise | Zhou & Li, 2026, arXiv preprint (+ ICLR 2027 submission) [48] | "Layer interpolation replaces blocks 20–28 by the midpoint of their step-50 and step-275 parameters." | https://arxiv.org/html/2608.29188v1; App. (Intervention definitions); v1 | 2026-10-21 | adjacent (interpolation between RL checkpoints, not base/instruct) [VERIFIED] | base/instruct (not checkpoint) interpolation |
| 92e-L1r | L1a: a content-free nudge or ban moves the tuned model onto its BASE model's runner-up algorithm, forecast in advance | Lin et al., 2023, ICLR 2024 [60, 59] | see Table 92d row 92d-A2b (not re-verified) | https://arxiv.org/html/2312.01552v1 | 2026-10-21 (inherited) | adjacent (token level, no perturbation); inherited | algorithm-level landing under perturbation |
| 92e-L1s | L1a: a content-free nudge or ban moves the tuned model onto its BASE model's runner-up algorithm, forecast in advance | Anonymous, 2026, ICLR 2027 submission [61] | see Table 92d row 92d-A2c (not re-verified; PDF 403 again 2026-10-21) | https://api2.openreview.net/notes/search?term=Same%20Candidates... | 2026-10-21 (inherited) | adjacent (token level, retrospective); inherited | same |
| 92e-L1t | L1b: the base forecast beats rivals built from the tuned model (likelihood ranking q_lik, sampled tail q_tail), incl. tail-empty events | Mohammadi, 2024, arXiv preprint [63] | see Table 92d row 92d-A1h (not re-verified) | https://arxiv.org/pdf/2406.05587v1 | 2026-10-21 (inherited) | contradicts-in-part (own attractor); inherited | explicit test of the own-attractor rival (q_tail, q_lik) |
| 92e-L1u | L1a: a content-free nudge or ban moves the tuned model onto its BASE model's runner-up algorithm, forecast in advance | Samanta et al., 2026, arXiv preprint [64] | see Table 92d row 92d-A2d (not re-verified) | https://arxiv.org/html/2606.29933v1 | 2026-10-21 (inherited) | adjacent; inherited | perturbation of the tuned model, forecast |
| 92e-L1v | L1a: a content-free nudge or ban moves the tuned model onto its BASE model's runner-up algorithm, forecast in advance | Zhou (T.) 2026; Duan 2026 [65, 66] | see Table 92d rows 92d-A1a..d (not re-verified) | https://arxiv.org/html/2607.20543v1 | 2026-10-21 (inherited) | adjacent (training-time forecasts; FLAG B partly); inherited | inference-time landing identity |
| 92e-L3c | L3: the perturbed/tuned distribution is the base distribution raised to a power | Zhang et al., 2025, arXiv preprint [62] | see Table 92d row 92d-A2a (not re-verified) | https://arxiv.org/html/2510.01171v4 | 2026-10-21 (inherited) | adjacent (stylised power sharpening); inherited | fitted alpha with rivals |
| 92e-L2b | L2: the perturbed tuned distribution stays inside base support | Wu et al. 2025; Yue et al. 2025 [91, 90] | see Table 92d A0 quotes (not re-verified) | https://arxiv.org/html/2507.14843v5 | 2026-10-21 (inherited) | supports; inherited | algorithm-level support test |
| 92e-Se | S-a: prefill task-spec states by block band as the site of content-free nudges | Khalid et al., 2026; Zhu et al., 2026 (STARS) [69, 70] | see Table 92c rows C1-sited, C1-sitee (not re-verified) | https://arxiv.org/html/2601.22010v1 | 2026-10-21 (inherited) | adjacent (site comparisons for narratives / test coverage); inherited | matched per-position dose; categorical algorithm choice |
| 92e-Sf | S-c: condition vs generated tokens as sites | Zhang et al., 2026 [71] | see Table 92c rows C1-sitea..c, 92d-Ci (not re-verified) | https://arxiv.org/html/2606.10302v1 | 2026-10-21 (inherited) | adjacent (text-level sites); inherited | activation-level, content-free sites |
| 92e-Sg | S-b | Jerge et al., 2026; Nagarajan et al., 2025 [72, 73] | see Table 92c rows C1-sitef, C1-siteg (not re-verified) | https://arxiv.org/html/2608.21595v1 | 2026-10-21 (inherited) | adjacent; inherited | same |
| 92e-Sh | S-a: prefill task-spec states by block band as the site of content-free nudges | Kim et al., 2026 (random embedding injection) [74] | see Table 92b row b6c (not re-verified) | https://arxiv.org/html/2605.11936v2 | 2026-10-21 (inherited) | adjacent (math; code future work); inherited | code, test-checked labels |
| 92e-Fm | F1: the first divergence (entrance fork) decides the algorithm | Anonymous, 2026, ICLR 2027 submission [68]; Dong et al. 2025 [76] | see Table 92c rows C2aa, C2ab, C2ac (not re-verified) | https://openreview.net/forum?id=knirOusGcq | 2026-10-21 (inherited) | adjacent (pre-generation plan states); inherited | fork margin at the algorithm opening |
| 92e-Fn | F2: teacher-forced log-odds margin between algorithm openings bounds the temperature effect | Zhu et al., 2024 (AdapT) [75] | see Table 92b row b3b (not re-verified) | https://arxiv.org/html/2309.02772v3 | 2026-10-21 (inherited) | adjacent; inherited | margin-based account of temperature robustness |
| 92e-Kf | K: test-checked algorithm-level prices of base intent, base/instruct interpolation, proxy tuning, enumerate-and-pick, plan noise | Wang et al. (BACo) [79]; Peeperkorn et al. [80]; Feng et al. [81] | see Table 92d rows 92d-B1i, Ca, Cb, Cc (not re-verified) | https://arxiv.org/html/2511.05650v2 | 2026-10-21 (inherited) | occupied lane (base-aligned collaboration; 92d); inherited | algorithm-level, test-checked prices |
| 92e-Kg | K: test-checked algorithm-level prices of base intent, base/instruct interpolation, proxy tuning, enumerate-and-pick, plan noise | SLR [82]; FrankenMerging [83]; Dang et al. [84]; Hindsight Merging [85] | see Table 92d rows 92d-B1f, B1g, Ce, Cf and Hindsight quotes (not re-verified) | https://arxiv.org/html/2610.22999v1 | 2026-10-21 (inherited) | adjacent (weight-level diversity restoration); inherited | base/instruct lambda 0.25/0.5 on algorithm labels |
| 92e-Kh | K: test-checked algorithm-level prices of base intent, base/instruct interpolation, proxy tuning, enumerate-and-pick, plan noise | EFT [87, 58]; proxy tuning [88]; Nudging [89] | see Table 92d quotes (B2/C) (not re-verified; venues corrected here) | https://arxiv.org/html/2401.08565v4 | 2026-10-21 (inherited) | adjacent (logit-level knobs); inherited | proxy tuning priced on algorithm labels |
| 92e-Ga | G | FunSearch; AlphaEvolve [92, 93] | see Table 92c rows C3ca, C3cb (not re-verified; no new search) | https://www.nature.com/articles/s41586-023-06924-6 | 2026-10-21 (inherited) | context (scope); inherited | scope statement unchanged |

### 3.1 Further verified or screened neighbours not in the table

- Screened at abstract level and scored but not quoted. Quantisation hides behavioural damage behind flat scores: [99, 100, 98, 102] (weight-only or compiled policies). Safety-preserving PTQ including W4A4 [101]. Flip repair by precision patching of weight groups [105]. A pre-SFT emergent-misalignment risk forecast from the base model [103]. A replication of the base/RL top-k overlap analysis [104]. bf16 export casting that reverts fine-tuning changes [97].
- Grey literature (E6): a GitHub study of NVFP4/FP8 damage with tuned lens and SAE features on bf16 vs low-bit activations [106] was not fetched; under the frozen rule a repository is context and never fires a flag.
- Mechanism anchors outside the window: [21, 22, 23, 24, 25, 18].
- Inherited rows used as background but not re-quoted: the base-to-tuned transplant/patching method rows 92d-B1a..B1e [94, 95], shallow safety alignment 92b-b3a [96], pre-generation planning rows 92c-C2ad and C2ah [77, 78], and sparse RL-token replacement 92d-Cd [86].

## 4. Saturation search (PRISMA-S style)

| Family | Calls | Raw hits | Unique records touching family | In window | Pass pre-screen | Manually screened |
|---|---|---|---|---|---|---|
| BC | 5 | 198 | 185 | 27 | 24 | 53 |
| FC | 22 | 492 | 476 | 366 | 297 | 115 |
| FE1 | 30 | 723 | 631 | 477 | 380 | 109 |
| FE2 | 12 | 402 | 372 | 320 | 252 | 38 |
| FK1 | 13 | 525 | 496 | 410 | 358 | 76 |
| FL1 | 20 | 530 | 511 | 411 | 351 | 64 |
| FL2 | 8 | 346 | 327 | 279 | 252 | 16 |
| FS1 | 16 | 595 | 570 | 485 | 377 | 32 |
| R2-FE | 12 | 293 | 282 | 251 | 208 | 113 |
| R2-FL | 8 | 239 | 237 | 175 | 150 | 37 |
| R2-FS | 4 | 103 | 97 | 88 | 62 | 31 |

Engines and settings were inherited from art_ObxQOIlAM9MS. E1 ran aii_fast_web_search.py --mode scholarly (25 results). E3 queried the arXiv API (cs.CL/cs.LG/cs.AI, newest first, 50 results). E4 queried the Semantic Scholar /paper/search endpoint (year=2026, 50 results). E5 queried OpenReview notes/search (ICLR.cc/2027/Conference, 50 results). E6 used the built-in WebSearch with allowed_domains set to the grey-literature list (FE1 and FL1), plus github.com for FE1. Forward citations came from Semantic Scholar; the one logged OpenAlex cites: attempt per mandatory neighbour returned 0, 0, 0 and 3 records. Records were de-duplicated by arXiv id, OpenReview id and normalised title against both earlier candidate sets (1,729 + 3,506). Of the 150 calls, one E5 call returned HTTP 429 and was retried successfully. Records failing the pre-screen in every lane: 918.

Rounds: R1 ran 21 strings on E1/E3/E4/E5, plus 14 E6 calls and forward citations of 4 + 4 seeds (Steering Under Compression 0 citing works, Sparse but Critical 24, Forking Paths 48, Give Me FP32 80, Reasoning with Sampling 95, Thought Anchors 148, Non-surjective 8, Lost in Quantization 0). R2 ran 6 vocabulary queries on 4 engines. R3 chased forward citations of 6 closest new hits and backward references of 2 per flag. R4 chased forward citations of 3 round-3 hits and backward references of 1. **Stop condition:** Rounds: R1 (21 strings x E1/E3/E4/E5 + 14 E6 calls + forward citations of 4+4 seeds), R2 (6 queries x 4 engines), R3 (forward citations of 6 closest new hits + backward references of 2 per flag), R4 (forward citations of 3 round-3 hits + backward references of 2610.24346). R3 and R4 each added hits scoring 1.5, all on the E-deployment context sub-lane ('quantisation hides behavioural damage behind flat aggregate scores', weight-only). The search was stopped after R4 by a logged DEVIATION from the frozen stop rule: neither frozen condition was met (new >=1.5 hits kept arriving; Stage-2 cap of 60 min not reached: ~21 min of logged search time, 23:35-23:56 UTC), but every new >=1.5 hit after R2 fell in one saturated context sub-lane that cannot move FLAG E (no activation-level intervention) or any other verdict.

## 5. Corrections and confirmations

- **Locked at the Entrance, Open Inside.** Previously: cited in 92d (rows 92d-A0i, 92d-B1h) as an anonymous ICLR 2027 submission (VERIFIED-ABSTRACT, OpenReview hu5mtofNd4). Now: on arXiv as 2608.29188 v1 (29 Aug 2026; Qiancheng Zhou and Ruizhe Li; comment 'Preprint'); full text verified in 92e-Fe/92e-Kd; layer interpolation is between RL checkpoints (blocks 20-28, midpoint of step-50 and step-275), not base/instruct.
- **A Gravitational Interpretation ... (2606.28525).** Previously: search-engine listing title 'A Gravitational Interpretation of Fine-Tuning Reversion'. Now: arXiv v2 (28 Sep 2026) title: 'A Gravitational Interpretation of Safety Reversion under Fine-Tuning'.
- **Give Me FP32 or Give Me Death? (2506.09501).** Previously: plan: NeurIPS 2025 oral per the virtual page (unverified). Now: confirmed: NeurIPS 2025 oral page https://neurips.cc/virtual/2025/oral/118170 lists it under the v2 title 'Understanding and Mitigating Numerical Sources of Nondeterminism in LLM Inference'.
- **URIAL (2312.01552).** Previously: 92d: venue unconfirmed. Now: confirmed ICLR 2024 poster (https://iclr.cc/virtual/2024/poster/17473).
- **EFT (2310.12962).** Previously: 92d: venue unconfirmed. Now: confirmed ICLR 2024 (proceedings.iclr.cc page).
- **Proxy tuning (2401.08565).** Previously: 92d: venue unconfirmed. Now: arXiv v4 comment: 'COLM 2024 camera-ready' (author-stated; no venue page fetched).
- **Top-nσ (2411.07641).** Previously: arXiv title 'Top-nσ: Not All Logits Are You Need'. Now: published at ACL 2025 (Long) as 'Top-nσ: Eliminating Noise in Logit Space for Robust Token Sampling of LLM' (Anthology 2025.acl-long.528).
- **Forking Paths (2412.07961).** Previously: plan: ICLR 2025. Now: confirmed ICLR 2025 poster (https://iclr.cc/virtual/2025/poster/30769).
- **Thought Anchors (2506.19143).** Previously: plan: 'confirm venue'. Now: no venue found (arXiv v4, 27 Oct 2025; comment lists equal contribution only); cited as arXiv preprint.
- **Sparse but Critical (2603.22446).** Previously: plan: the 30%/80%/90% figure sits in Sec. 4.1 'Top-k Overlap and Rank Reordering'. Now: confirmed in Sec. 4.1 of v1; the figures are restricted to high-divergence positions (JS > 0.1) and refer to the Figure 22 rank analysis.
- **Steering Under Compression (2609.06473).** Previously: plan: 'CAA vectors recomputed per condition'. Now: confirmed: 'Steering vectors extracted independently per scheme (same contrast pairs, same resample)'; negative check: 'FP8' 0 hits, 'per-token' 0 hits, 'W8A8' 1 hit (Limitations: excluded by design).
- **Lost in Quantization (PROPOR 2026).** Previously: plan: English +18% vs PT-BR +3.9%; spikes > 35. Now: confirmed on the Anthology page/PDF; scope is naive unscaled E4M3 casting ('no calibration/scaling'), not per-token-scaled W8A8.
- **Emergent Misalignment Is Not Magical (2608.29118).** Previously: search snippet: 'base-model activation space predicts EM'. Now: terminology: its 'base model' is the pre-EM INSTRUCT model (Qwen2.5-14B/32B-Instruct, Gemma-3-27B-IT, ...), i.e., a forecast from the tuned model itself.
- **Same Candidates (OpenReview ooV5M72O08), Before the First Token (knirOusGcq).** Previously: plan: one PDF attempt each. Now: PDF attempts on 2026-10-21 returned HTTP 403 again; kept VERIFIED-ABSTRACT; the notes?id= API endpoint now returns 403 ChallengeRequiredError, the notes/search endpoint still serves abstracts.
- **Float32-Induced Distortion in Activation Patching (DOI 10.3390/computation14090212).** Previously: found via S2 without URL. Now: publisher page (mdpi.com) returned HTTP 403; quoted from the Semantic Scholar API abstract record (VERIFIED-ABSTRACT).
- **Steering Under Compression authors.** Previously: plan: 'Bhandari and Wade'. Now: confirmed by the arXiv API: Saurav Bhandari; Benjamin Wade.

## 6. Unverified or partly verified references (no numbers taken beyond what is stated)

- OpenReview PDFs returned HTTP 403 for 8iTqrW1sxY [2], h57duZqLOr [3], 6t1egKiB0v [6], ooV5M72O08 [61] and knirOusGcq [68]. The notes?id= API returned 403 ChallengeRequiredError. Only abstract records from notes/search are used, so their precision factors, models and numbers beyond the abstracts are unknown.
- The publisher page of the Float32 patching paper (mdpi.com) returned 403. It is quoted from its Semantic Scholar abstract record [5].
- One E1 record had no abstract or URL and was not scored: 'Where the Answer Is Born: Causal Interventions on the Information Trajectory of a Quantized Hybrid Language Model'. It is UNVERIFIED and listed so a later round can resolve it. A second such record, 'From Weights to Activations: Is Steering the Next Frontier of Adaptation?', was resolved to arXiv 2604.14090 (ACL 2026 Main): it is a position paper with no precision factor, scored irrelevant [20].
- Thought Anchors has no venue found [47]. Proxy tuning's COLM 2024 venue rests on its arXiv comment [88].

## 7. Confidence, contradicting evidence, and what would change each verdict

- **FLAG E: medium confidence.** The verdict rests on abstract-level text for the two closest candidates. Full texts showing W8A8/FP8-activation arms would turn PARTLY into FIRES, and Claim E would become a replication [2, 3]. Contradicting in part: numerics alone change outputs and margins [12, 17, 15, 14], so a W8A8 effect could be a kernel or batching artefact unless numerics are controlled. Weight-only steering directions survive quantisation [1], which argues against large weight-side effects.
- **FLAG L: medium-high confidence.** It would FIRE if a paper commits to a base-model forecast of the landing identity and scores it against the tuned model's own ranking. The closest work is retrospective [31] or uses a geometric null [34]. Contradicting evidence favours the rival hypothesis that nudges walk the tuned model's own ladder [35, 36, 63]. Lee et al.'s mixed base-vs-instruct direction [67] warns that the base runner-up need not be the tuned model's runner-up.
- **S/F/K: medium confidence.** These lanes are crowded [44, 48, 17, 54, 57, 79]. The handbook's base rate for unchecked lanes being occupied is 11/11, and this audit added contemporaneous occupants in E and F2. A screener-risk caveat applies: one agent scored everything, and the re-screen is a consistency check (kappa 0.791).

## 8. Follow-up questions

- TOP (FLAG E partly fired at contemporaneous abstract level): once ICLR 2027 PDFs open (reviews due about end of October 2026), do OpenReview 8iTqrW1sxY ('Stable Directions, Different Effects') and h57duZqLOr ('Activation Steering under Low-Bit Quantization') include ACTIVATION quantisation (W8A8, FP8 activations, KV cache), or weights only? If they include activations, Claim E becomes a replication in a new setting (content-free nudges, code-algorithm choice).
- Does PAHQ's failure mode (small patch effects truncated to zero under unscaled FP8/RTN) appear under per-token-scaled FP8 W8A8? The run's W16A8 arm with per-token absmax readouts can answer this directly.
- In the run's own data, what fraction of nudge landings lie within the tuned model's own teacher-forced top-k (q_lik) or sampled tail (q_tail), compared with the base runner-up? Weak-to-strong jailbreaking predicts that the tuned model's own ranking already contains many landings.
- Re-check Same Candidates (ooV5M72O08) and Before the First Token (knirOusGcq) when their PDFs open, and confirm whether Locked at the Entrance (now arXiv 2608.29188) compares its entrance-family coverage with the base model.
- UNMAPPED citation numbers: the one-to-one assignment of the hypothesis's own reference numbers 88-91, 92/93/102, 98/99 and 81/82 to papers needs the hypothesis reference list (inherited/citation_map.json maps only the sets of inherited rows).
- Which FP8 scheme did the iteration-4 engine actually use: block-128 fine-grained checkpoint scales or dynamic per-token activation scales? The attribution readout depends on it.

## Sources

[1] [Steering Under Compression: Dose-Response, Capability Cost, and Failure Asymmetry in Quantized LLMs (arXiv 2609.06473v1)](https://arxiv.org/html/2609.06473v1) (Saurav Bhandari, Benjamin Wade; 2026) — Nearest FLAG E neighbour: CAA steering under bitsandbytes WEIGHT-ONLY INT8/NF4 on four 7-9B models; activations kept FP16/BF16; vectors recomputed per scheme stay collinear (cosine 0.989-0.998 INT8, 0.945-0.990 NF4); activation quantisation excluded by design.

> We study only bitsandbytes weight-only quantization (INT8, NF4); activation quantization (W8A8, W4A4) and outlier-aware weight algorithms (GPTQ, AWQ, SmoothQuant, QuaRot) are excluded by design and may behave differently.

Locator: Sec. 6 (Limitations)

> Despite this, steering vectors remain highly collinear with their FP16 siblings (cosine similarity 0.989-0.998 for INT8, 0.945-0.990 for NF4), confirming that the behavioral direction survives quantization even when the cost structure does not.

Locator: Abstract

[2] [Stable Directions, Different Effects: Intervention Fidelity Across Model Precision (ICLR 2027 desk-rejected submission, OpenReview 8iTqrW1sxY; API record)](https://api2.openreview.net/notes/search?term=Stable%20Directions%2C%20Different%20Effects%3A%20Intervention%20Fidelity%20Across%20Model%20Precision&group=ICLR.cc/2027/Conference&limit=10) (2026) — Abstract-level (PDF HTTP 403): the effect of a steering intervention transferred to a quantized version can change while directions stay aligned; precision factor not stated; keywords 'model quantization', 'cross-precision transfer'.

> Steering directions can remain aligned across model precision changes while their functional effects drift; local functional sensitivity predicts and corrects this cross-precision fidelity gap.

Locator: TLDR field of the OpenReview API record

[3] [Activation Steering under Low-Bit Quantization: A Geometric Perspective on Degradation and Recovery (ICLR 2027 submission, OpenReview h57duZqLOr; API record)](https://api2.openreview.net/notes/search?term=Activation%20Steering%20under%20Low-Bit%20Quantization%3A%20A%20Geometric%20Perspective%20on%20Degradation%20and%20Recovery&group=ICLR.cc/2027/Conference&limit=10) (2026) — Abstract-level: same intervention layer/direction/strength across full-precision and quantized models; output fidelity does not guarantee preserved responses to the intervention; quantisation scheme not stated.

> We study steering compatibility with the intervention layer, direction, and strength held fixed across full-precision and quantized models.

Locator: Abstract (OpenReview API record; keywords 'Quantization', 'Activation Steering')

[4] [PAHQ: Accelerating Automated Circuit Discovery through Mixed-Precision Inference Optimization (arXiv 2510.23264v1)](https://arxiv.org/html/2510.23264v1) (Xinhai Wang, Shu Yang, Liangyu Wang, Lin Zhang, Huanyi Xie, Lijie Hu, Di Wang; 2025) — 8-bit RTN quantisation of ALL weights and activations (FP32 baseline) collapses ACDC activation-patching circuit discovery (IOI/Greater-Than/Docstring, GPT-2-scale) via underflow and mantissa loss; the closest full-text FLAG E candidate (joint W+A, internal outcome).

> We directly applied quantization from 32 bits to 8 bits to all weights and activations of the model Radford et al. (2019) in the ACDC Conmy et al. (2023) method, which is called Round-to-Nearest Quantization (RTN-Q), on the Indirect Object Identification (IOI) task Wang et al. (2022) and tested its performance.

Locator: Sec. 2 (Direct Quantization Does Not Work on ACDC)

> when precision is reduced from 32 bits to 8 bits, direct quantization (also called Round-to-Nearest Quantization, RTN-Q) significantly increases the minimum quantization step size, causing activation values below this threshold to be truncated to zero and ultimately rendering the automated circuit discovery method ineffective.

Locator: Sec. 1 (Introduction)

[5] [Float32-Induced Distortion in Activation Patching: Precision Floors and Displacement-Dependent Endpoint-Curvature Error (Computation 2026; Semantic Scholar API record)](https://api.semanticscholar.org/graph/v1/paper/DOI:10.3390/computation14090212?fields=title,abstract,venue,publicationDate,authors,externalIds) (Yash Baligar; 2026) — fp32 vs fp64 numerics push many interaction-level patching estimates below a precision floor (GPT-2-medium, Pythia-410M); numerics, not activation quantisation.

> floor, 13.0% and 51.2% of full-displacement interactions fell below the threshold

Locator: Abstract (Semantic Scholar API record; publisher page https://www.mdpi.com/2079-3197/14/9/212 returned HTTP 403)

[6] [Quantization-Induced Decision Changes Have Regime-Dependent Intervention Spectra (ICLR 2027 submission, OpenReview 6t1egKiB0v)](https://api2.openreview.net/notes/search?term=Quantization-Induced%20Decision%20Changes%20Have%20Regime-Dependent%20Intervention%20Spectra&group=ICLR.cc/2027/Conference&limit=10) (2026) — Activation additions on quantized residual states used to restore full-precision predictions (repair use of interventions).

[7] [When Quantization Helps: Corrective Computation in Low-Bit Language Models (ICLR 2027 submission, OpenReview GYm4mg9yGQ)](https://api2.openreview.net/notes/search?term=When%20Quantization%20Helps%3A%20Corrective%20Computation%20in%20Low-Bit%20Language%20Models&group=ICLR.cc/2027/Conference&limit=10) (2026) — Weight-only GPTQ/AWQ/NF4; activation patching analyses quantisation-induced corrections.

[8] [PRISM: Transfer and Limits of Activation Interventions in Tool-Calling Language Models (arXiv 2610.20808v1)](https://arxiv.org/html/2610.20808v1) (Giovana Kerche Bonás, Thales Sales Almeida, Marcelo da Silva Reis, Rodrigo Nogueira, Marcos Meideiros Raimundo; 2026) — Directions estimated with labels from NF4 copies act on BF16 models; weight-only precision transfer of interventions.

> We explore 16-bit (BF16) and 4-bit (NF4) versions of smaller models to expose harmful tool-call compliance and estimate intervention directions.

Locator: Sec. 1 (Introduction)

[9] [Steered LLM Activations are Non-Surjective (arXiv 2604.09839v2)](https://arxiv.org/html/2604.09839v2) (Aayush Mishra, Daniel Khashabi, Anqi Liu; 2026) — Inherited 92b-b7c/92c-C2-geod; new finding quoted: its empirical claims hold on an INT4 model.

> Noticeably, our theoretical claim does not cover quantization effects. However, we experiment with an INT4 quantized model and find that our empirical claims hold comfortably in this setting (§D).

Locator: Sec. 7 (Conclusion and Limitations; App. D)

[10] [Alignment Collapse Under KV Cache Quantization: Diagnosis and Mitigation (arXiv 2606.09864v2)](https://arxiv.org/pdf/2606.09864v2) (Bruce Changlong Xu, Adarsh Kumarappan, Mu Zhou; 2026) — Activation-side KV-cache quantisation silently removes refusals at ~flat perplexity; outlier-driven scale factors crush safety channels; no activation-level intervention.

> where safety lives in non-outlier channels collaterally damaged by outlier-driven scale factors

Locator: Abstract (PDF p. 1)

[11] [Lost in Quantization: Activation Outliers Explain Language-Specific FP8 Sensitivity in Llama-3 (PROPOR 2026, ACL Anthology 2026.propor-1.108)](https://aclanthology.org/2026.propor-1.108/) (2026) — Naive unscaled E4M3 casting vs INT8 with outlier handling on Meta-Llama-3-8B; English +18% vs PT-BR +3.9% perplexity; no interventions; not per-token-scaled W8A8.

> INT8 with outlier handling preserves perplexity in both languages, while naive FP8 casting degrades English far more than PT-BR (+18% vs. +3.9%).

Locator: Abstract (ACL Anthology page; PDF pp. 1044-1048)

> Our FP8 results reflect a naive casting stress test (no calibration/scaling), not an optimized FP8 recipe.

Locator: Abstract (ACL Anthology page)

[12] [Understanding and Mitigating Numerical Sources of Nondeterminism in LLM Inference (v1 title 'Give Me FP32 or Give Me Death?'; arXiv 2506.09501v2)](https://arxiv.org/html/2506.09501v2) (Jiayi Yuan, Hao Li, Xinheng Ding, Wenya Xie, Yu-Jhe Li, Wentian Zhao, Kun Wan, Jing Shi, Xia Hu, Zirui Liu; 2025) — BF16 numerics plus batch size/GPU count change accuracy by up to 9% and length by 9,000 tokens under greedy decoding; LayerCast.

> For instance, under bfloat16 precision with greedy decoding, a reasoning model like DeepSeek-R1-Distill-Qwen-7B can exhibit up to 9% variation in accuracy and 9,000 tokens difference in response length due to differences in GPU count, type, and evaluation batch size.

Locator: Abstract (v2)

[13] [NeurIPS 2025 oral page: Understanding and Mitigating Numerical Sources of Nondeterminism in LLM Inference](https://neurips.cc/virtual/2025/oral/118170) (2025) — Venue confirmation (oral) for [12].

[14] [Defeating Nondeterminism in LLM Inference (Thinking Machines Lab blog, Sep 10, 2025)](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/) (Horace He; 2025) — Batch-invariance account of inference nondeterminism; 80 unique completions from 1000 temperature-0 samples of a Qwen3 model.

> We use `Qwen/Qwen3-235B-A22B-Instruct-2507` and sample 1000 completions at temperature 0

Locator: Experiments: How nondeterministic are completions?

[15] [The Integer Alibi: Localizing Cross-Kernel Divergence in INT8-Quantized LLM Inference (arXiv 2608.13756v2)](https://arxiv.org/html/2608.13756v2) (Teng-Ruei Chen; 2026) — Swapping only the INT8 W8A8 GEMM kernel (CUTLASS vs Triton) in vLLM on Qwen3-1.7B/8B changes every sequence (0/8, 0/16, 0/64 agree); FP8 GEMM differences grow with reduction depth.

> At 1.7B each arm reproduces itself bit-for-bit across cold restarts, yet the arms agree on no sequence in any end-to-end comparison we ran (0/8, 0/16, and 0/64).

Locator: Abstract

[16] [Same Request, Different Answer: Quantization Amplifies Cache-Induced Divergence in LLM Serving (arXiv 2609.04748v2)](https://arxiv.org/html/2609.04748v2) (Aditi Patodiya; 2026) — Quantised execution path (not rounded weights) amplifies cache-induced divergence; top-two margins; weights-through-16-bit-kernels control.

> Serving four-bit weights through 16-bit kernels left divergence not detectably different from 16-bit, placing the amplification mainly in the quantized execution path.

Locator: Abstract

> Near-tie decisions became only about 1.2 times as common, while the cache-path change in top-two margins grew 4.9-fold from 16-bit to three-bit.

Locator: Abstract

[17] [Greedy Decoding Is Not Precision-Invariant: Cross-Precision Output Divergence in LLM Inference (TMLR 2026; arXiv 2609.26621v1)](https://arxiv.org/pdf/2609.26621v1) (Gaoyuan Du, Anam Nawaz Khan, Rex Zhou, Xiaoyang Liu, Deepayan Chakrabarti, Fnu Suya, Xueping Li; 2026) — BF16 vs FP16 change greedy outputs on 49-100% of prompts; outcome governed by the top-two logit margin at the lm_head; end-to-end FP8 divergence is body-dominated.

> the outcome depends primarily on the top-two logit margin at the lm_head

Locator: Abstract (PDF p. 1)

[18] [Accuracy is Not All You Need (NeurIPS 2024; arXiv 2407.09141v1)](https://arxiv.org/html/2407.09141v1) (Abhinav Dutta, Sanjeev Krishnan, Nipun Kwatra, Ramachandran Ramjee; 2024) — Compressed models flip answers at matched accuracy: deployment analogue of 'same default, different behaviour'.

> However, even when the accuracy of baseline and compressed model are similar, we observe the phenomenon of flips, wherein answers change from correct to incorrect and vice versa in proportion.

Locator: Abstract

[19] ['Give Me BF16 or Give Me Death'? Accuracy-Performance Trade-Offs in LLM Quantization (ACL 2025; arXiv 2411.02355v4)](https://arxiv.org/html/2411.02355v4) (Eldar Kurtic, Alexandre Marques, Shubhra Pandit, Mark Kurtz, Dan Alistarh; 2024) — Over 500,000 evaluations on Llama-3.1: FP8 W8A8 with dynamic per-token activation scales is accuracy-lossless (premise of 'same default accuracy').

> W8A8-FP quantization is essentially lossless, preserving the uncompressed model’s accuracy across all benchmarks, often within the evaluation’s margin of error. This result is achieved with a simple yet robust approach: dynamic per-token activation quantization combined with symmetric weight quantization via round-to-nearest assignment.

Locator: Sec. 1 (main findings)

[20] [From Weights to Activations: Is Steering the Next Frontier of Adaptation? (ACL 2026; arXiv 2604.14090v1)](https://arxiv.org/html/2604.14090v1) (Simon Ostermann, Daniil Gurgurov, Tanja Baeumel, Michael A. Hedderich, Sebastian Lapuschkin, Wojciech Samek, Vera Schmitt; 2026) — Position paper: steering as a form of model adaptation; no precision factor (screened, irrelevant to FLAG E).

[21] [SmoothQuant: Accurate and Efficient Post-Training Quantization for Large Language Models (ICML 2023; arXiv 2211.10438v7)](https://arxiv.org/html/2211.10438v7) (Guangxuan Xiao, Ji Lin, Mickael Seznec, Hao Wu, Julien Demouth, Song Han; 2022) — W8A8 mechanism anchor: activations are hard to quantise because of outliers; per-token activation scales.

> Based on the fact that weights are easy to quantize while activations are not, SmoothQuant smooths the activation outliers by offline migrating the quantization difficulty from activations to weights with a mathematically equivalent transformation.

Locator: Abstract

[22] [LLM.int8(): 8-bit Matrix Multiplication for Transformers at Scale (NeurIPS 2022; arXiv 2208.07339v2)](https://arxiv.org/html/2208.07339v2) (Tim Dettmers, Mike Lewis, Younes Belkada, Luke Zettlemoyer; 2022) — Emergent outlier features from 6.7B parameters ruin quantisation precision.

> the sparse but systematic large magnitude outlier features that ruin quantization precision once they emerge in all transformer layers starting at scales of 6.7B parameters

Locator: Sec. 1 (Introduction)

[23] [Massive Activations in Large Language Models (COLM 2024; arXiv 2402.17762v2)](https://arxiv.org/html/2402.17762v2) (Mingjie Sun, Xinlei Chen, J. Zico Kolter, Zhuang Liu; 2024) — Massive activations sit at the starting and delimiter tokens and act as bias terms: position-specific spikes set per-token scales.

> Many of these activations are found within the starting word token and delimiter tokens.

Locator: Sec. 1 (Introduction)

[24] [FP8 Formats for Deep Learning (arXiv 2209.05433v2)](https://arxiv.org/html/2209.05433v2) (Paulius Micikevicius, Dusan Stosic, Neil Burgess, Marius Cornea, Pradeep Dubey, Richard Grisenthwaite, Sangwon Ha, Alexander Heinecke, Patrick Judd, John Kamalu, Naveen Mellempudi, Stuart Oberman, Mohammad Shoeybi, Michael Siu, Hao Wu; 2022) — Definition of E4M3/E5M2.

> we propose an 8-bit floating point (FP8) binary interchange format consisting of two encodings - E4M3 (4-bit exponent and 3-bit mantissa) and E5M2 (5-bit exponent and 2-bit mantissa).

Locator: Abstract

[25] [Decoding Compressed Trust: Scrutinizing the Trustworthiness of Efficient LLMs Under Compression (ICML 2024; arXiv 2403.15447v3)](https://arxiv.org/html/2403.15447v3) (Junyuan Hong, Jinhao Duan, Chenhui Zhang, Zhangheng Li, Chulin Xie, Kelsey Lieberman, James Diffenderfer, Brian Bartoldson, Ajay Jaiswal, Kaidi Xu, Bhavya Kailkhura, Dan Hendrycks, Dawn Song, Zhangyang Wang, Bo Li; 2024) — 4-bit weight quantisation retains trustworthiness while pruning degrades it.

> For instance, a 4-bit quantized model retains the trustworthiness of its original counterpart, but model pruning significantly degrades trustworthiness, even at 50% sparsity.

Locator: Abstract

[26] [Qwen/Qwen3-8B-FP8 model card (Hugging Face)](https://huggingface.co/Qwen/Qwen3-8B-FP8) — Documents the released FP8 checkpoint: fine-grained fp8 quantisation with block size 128 (methods row only).

> The quantization method is fine-grained `fp8` quantization with block size of 128.

Locator: Model card, 'Note on FP8'

[27] [vLLM documentation: FP8 W8A8 (llm-compressor FP8_DYNAMIC)](https://docs.vllm.ai/en/stable/features/quantization/llm_compressor/fp8/) — Documents W8A8 FP8_DYNAMIC: static per-channel weight scales, dynamic per-token activation scales (methods row only).

> Dynamic, per-token quantization on the activations

Locator: '2. Applying Quantization'

[28] [The Sharp Directions Are Against You: Curvature Analysis of Activation Steering (NeurIPS 2026 poster page)](https://neurips.cc/virtual/2026/poster/151909) (Seyedarmin Azizi, Arya Fayyazi, Parsa Razmara, Erfan Baghaei Potraghloo, Souvik Kundu, Massoud Pedram; 2026) — Steering curvature: tiny perturbations along sharp directions cause large input-dependent behaviour swings (a mechanism by which small numeric perturbations of a nudge could matter).

> tiny perturbations along them can cause large, erratic, input-dependent behavioral swings

Locator: Abstract (NeurIPS 2026 poster page)

[29] [How Fragile Is Safety Alignment at Frontier Scale? A Single-Direction Attack on a 320B MoE (arXiv 2609.09793)](https://arxiv.org/abs/2609.09793) (2026) — Directional ablation on a block-FP8 320B MoE checkpoint; no precision contrast.

> We apply it to GLM-5.3-Flash (320B parameters, 288 routed experts, a four-wide hyper-connection residual, block-FP8).

Locator: Abstract (arXiv abs page)

[30] [Sparse but Critical: A Token-Level Analysis of Distributional Shifts in RLVR Fine-Tuning of LLMs (ICLR 2026; arXiv 2603.22446v1)](https://arxiv.org/html/2603.22446v1) (Haoming Meng, Kexin Huang, Shaohang Wei, Chiyu Ma, Shuo Yang, Xue Wang, Guoyin Wang, Bolin Ding, Jingren Zhou; 2026) — At high-divergence positions ~30% of RL top-1 tokens are base top-1 and >80% (DAPO) / >90% (SimpleRL) are in the base top-3; cross-sampling with base tokens collapses RL gains.

> Around 30% of RL top-1 tokens are already ranked first under the base model, and over 80% (DAPO) and 90% (SimpleRL) fall within the base top-3.

Locator: Sec. 4 (rank-shift analysis, Figure 22 discussion)

> inserting only a small fraction of RL-sampled tokens into base generations progressively recovers RL performance gains, while injecting a similarly small number of base token choices into otherwise RL-generated sequences collapses performance to base levels

Locator: Abstract

[31] [Re-Emergent Misalignment: How Narrow Fine-Tuning Erodes Safety Alignment in LLMs (arXiv 2507.03662v1)](https://arxiv.org/html/2507.03662v1) (Jeremiah Giordani; 2025) — FLAG L partly: fine-tune-perturbed instruct model produces outputs the base model also rates likely while the instruct model suppresses them (retrospective, sequence likelihoods, 400 examples per dataset).

> The aligned model (instruct) sharply suppresses the likelihood of the harmful generation. In contrast, both the base and misaligned models assign significantly higher probabilities to the same tokens. They do so with strikingly similar distributions.

Locator: Sec. 4.1 (Behavioral Analysis: Misaligned Model Reverts to Base Behavior)

> we propose that these behaviors can be better understood as a regression to base model behavior.

Locator: Sec. 1 (Introduction)

[32] [Language Models Resist Alignment: Evidence From Data Compression (ACL 2025; arXiv 2406.06144v6)](https://arxiv.org/html/2406.06144v6) (Jiaming Ji, Kaile Wang, Tianyi Qiu, Boyuan Chen, Jiayi Zhou, Changye Li, Hantao Lou, Juntao Dai, Yunhuai Liu, Yaodong Yang; 2024) — Elasticity/rebound: reverse fine-tuning returns post-trained models quickly to the pre-training distribution.

> Fine-tuning in the opposite direction of post-training (e.g., safe vs. unsafe) causes post-trained models to return quickly to the pre-training distribution.

Locator: Sec. 5 (How Elasticity Resists Alignment?)

[33] [Alignment Dynamics in LLM Fine-Tuning (arXiv 2605.18309v1)](https://arxiv.org/html/2605.18309v1) (Yuhan Huang, Huanran Chen, Yinpeng Dong; 2026) — Rebound effect as a driving-vs-rebound force competition.

> The Rebound Effect [14] refers to the tendency of fine-tuned models to revert toward their pre-trained state under reversed or perturbed fine-tuning.

Locator: Sec. 3 (Revisiting Rebound Effect)

[34] [A Gravitational Interpretation of Safety Reversion under Fine-Tuning (arXiv 2606.28525v2)](https://arxiv.org/html/2606.28525v2) (Samuele Poppi, Nils Lukas; 2026) — Prospective, pre-fixed direction toward base-descended helpful-only states; benign fine-tuning moves along it more than a matched null.

> We instead cast it as a single activation-space direction, pointing from the safety-aligned model toward independently built helpful-only states rather than toward the base model itself, and fixed before the prospective target trajectories are trained

Locator: Sec. 1 (Introduction)

> once we fixed the reference family and the test in advance, every additional trajectory we tried moved in the predicted direction more than its matched null

Locator: Sec. 1 (Introduction)

[35] [Weak-to-Strong Jailbreaking on Large Language Models (ICML 2025; arXiv 2401.17256v5)](https://arxiv.org/html/2401.17256v5) (Xuandong Zhao, Xianjun Yang, Tianyu Pang, Chao Du, Lei Li, Yu-Xiang Wang, William Yang Wang; 2024) — Rival-supporting: jailbroken models' top tokens lie within the safe (tuned) model's own top ten.

> We observe that the top-ranked tokens in jailbroken LLMs are largely found within the top ten tokens ranked by safe LLMs.

Locator: Sec. 1 (Introduction)

[36] [Emergent Misalignment Recruits a Pre-existing Persona Subspace (arXiv 2607.21356v1)](https://arxiv.org/html/2607.21356v1) (Mohammed Suhail B Nadaf; 2026) — Rival-supporting: a subspace extracted from the frozen instruction-tuned model carries where fine-tuning lands.

> A persona subspace present in the model before fine-tuning carries broad misalignment. The subspace is extracted from the frozen instruction-tuned model.

Locator: Fig. 1 caption

> Provenance. The extraction is from a released instruction-tuned checkpoint, not a pre-alignment base model, so whether pretraining installed the structure or alignment post-training sharpened it is open.

Locator: Sec. 9 (Limitations: Provenance)

[37] [Emergent Misalignment Is Not Magical (arXiv 2608.29118v1)](https://arxiv.org/html/2608.29118v1) (Mingxuan Li, Qirun Dai, Heran Wang, Chenhao Tan; 2026) — Per-prompt forecast of EM from the pre-EM model's representations; its 'base model' is the pre-fine-tune INSTRUCT model.

> the representational distance between an evaluation prompt and the training data centroid, both in the base model’s activation space, strongly predicts how misaligned the finetuned model becomes on that prompt

Locator: Sec. 1 (Introduction)

> We select models of various sizes and from multiple model families: Qwen2.5-14B-Instruct, Qwen2.5-32B-Instruct, Qwen2.5-Coder-32B-Instruct

Locator: Sec. 3 (Emergent Misalignment is Expected Generalization: Models and EM Training Data)

[38] [Predictive Mechanistic Interpretability of Post-Training: A Priori Forecasts of Circuit Localization and Sign from the Base Model (ICLR 2027 submission, OpenReview BEcwcRFQdu)](https://api2.openreview.net/notes/search?term=Predictive%20Mechanistic%20Interpretability%20of%20Post-Training%3A%20A%20Priori%20Forecasts%20of%20Circuit%20Localization%20and%20Sign%20from%20the%20Base%20Model&group=ICLR.cc/2027/Conference&limit=10) (2026) — Sealed, pre-registered per-head forecasts from the base model of how post-training changes circuits (method overlap for committed forecasts).

> We instead seal a per-head, signed forecast from the base model, fine-tune, and confirm it.

Locator: Abstract (OpenReview API record)

[39] [Emulated Disalignment: Safety Alignment for Large Language Models May Backfire! (ACL 2024; arXiv 2402.12343v4)](https://arxiv.org/html/2402.12343v4) (Zhanhui Zhou, Jie Liu, Zhichen Dong, Jiaheng Liu, Chao Yang, Wanli Ouyang, Yu Qiao; 2024) — Contrasting aligned vs pre-trained token distributions pushes the aligned model toward harm (logit-level base/aligned knob).

> our method achieves this reversal by contrasting the output token distribution of a safety-aligned language model (e.g., Llama-2-chat) against its pre-trained version (e.g., Llama-2), so that the token predictions are shifted towards the opposite direction of safety alignment.

Locator: Abstract

[40] [Post-Training with Policy Gradients: Optimality and the Base Model Barrier (ICML 2026; arXiv 2603.06957v2)](https://arxiv.org/html/2603.06957v2) (Alireza Mousavi-Hosseini, Murat A. Erdogdu; 2026) — Theory: going beyond the base model's support is exponentially costly for outcome-reward policy gradient (supports L2).

> However, a barrier arises for going beyond the support of the base model.

Locator: Abstract

[41] [Reasoning with Sampling: Your Base Model is Smarter Than You Think (arXiv 2510.14901v1)](https://arxiv.org/html/2510.14901v1) (Aayush Karan, Yilun Du; 2025) — Power distribution p^alpha of the base model matches GRPO in-domain and beats it out of domain (supports L3's power account).

> We introduce the power distribution as a useful sampling target for reasoning tasks. Since it can be explicitly specified with a base LLM, no additional training is required.

Locator: Sec. 1 (contributions)

> Our algorithm achieves comparable performance to GRPO within the posttraining domain (MATH500) but can outperform on out-of-domain tasks such as HumanEval and AlpacaEval.

Locator: Fig. 1 caption

[42] [Uncertainty Localization in LLM Reasoning via Embedding Perturbations (arXiv 2602.02427v4)](https://arxiv.org/html/2602.02427v4) (Qihao Wen, Jiahao Wang, Yang Nan, Pengfei He, Ravi Tandon, Han Xu; 2026) — Content-free Gaussian perturbation of token embeddings localises uncertain reasoning steps; continuations stay coherent (no site comparison at matched dose).

> Embedding perturbation does not disrupt reasoning coherence.

Locator: Sec. 3.2 (Random Perturbation)

> We find that the resulting continuations remain coherent and on-task.

Locator: Sec. 3.2

[43] [Why Do Reasoning Models Lose Coverage? The Role of Data and Forks in the Road (arXiv 2605.17026v2)](https://arxiv.org/html/2605.17026v2) (Ngoc-Hieu Nguyen, Parshin Shojaee, Phuc Minh Nguyen, Nan Zhang, Chandan K Reddy, Khoa D Doan, Rui Zhang; 2026) — Reasoning-mode forks (natural language vs code) are driven by weak signals; targeted prefix perturbation beats temperature scaling for coverage.

> reasoning mode selection is driven by weak signals, making it a key source of instability and side effects such as coverage collapse, but also a natural point of intervention for control.

Locator: Sec. 4.2 (Reasoning Mode Selection)

> We find that targeted prefix perturbation consistently outperforms temperature scaling across both model families, particularly for moderate sampling budgets (pass@8–32)

Locator: Sec. 5 (First-token Manipulation; App. C prefix perturbation vs temperature)

[44] [Forking Paths in Neural Text Generation (ICLR 2025; arXiv 2412.07961v1)](https://arxiv.org/html/2412.07961v1) (Eric Bigelow, Ari Holtzman, Hidenori Tanaka, Tomer Ullman; 2024) — Forking tokens found by resampling, including punctuation.

> We hypothesize that there exist key forking tokens, such that re-sampling the system at those specific tokens, but not others, leads to very different outcomes.

Locator: Abstract

> We find many examples of forking tokens, including surprising ones such as punctuation marks, suggesting that LLMs are often just a single token away from saying something very different.

Locator: Abstract

[45] [ICLR 2025 poster page: Forking Paths in Neural Text Generation](https://iclr.cc/virtual/2025/poster/30769) (2025) — Venue confirmation for [42].

[46] [Forking Fast: Efficiently Estimating Uncertainty Dynamics in Text Generation (arXiv 2608.19611v1)](https://arxiv.org/html/2608.19611v1) (Eric Bigelow, Amir Zur, Satchel Grant, Tal Haklay, Can Rager, Owen Lewis, Thomas McGrath, Jack Merullo, Ekdeep Singh Lubana, Atticus Geiger; 2026) — Change-point detection of forking points from low-sample resampling.

> This model uses change point detection to identify forking points, and kernel-pooling to smooth estimates between these points.

Locator: Sec. 1 (contributions)

[47] [Thought Anchors: Which LLM Reasoning Steps Matter? (arXiv 2506.19143v4)](https://arxiv.org/html/2506.19143v4) (Paul C. Bogdan, Uzay Macar, Neel Nanda, Arthur Conmy; 2025) — Sentence-level resampling importance: planning and uncertainty-management sentences anchor reasoning.

> We term these sentences thought anchors. These are generally planning or uncertainty management sentences, and specialized attention heads consistently attend from subsequent sentences to thought anchors.

Locator: Abstract

[48] [Locked at the Entrance, Open Inside: Where RLVR Narrows the Solution Space (arXiv 2608.29188v1)](https://arxiv.org/html/2608.29188v1) (Qiancheng Zhou, Ruizhe Li; 2026) — Entrance families (first operand and operator) in Countdown; RLVR contraction concentrated at the entrance; layer interpolation between RL checkpoints.

> we analyze the Countdown task, whose solution space can be exhaustively enumerated into discrete entrance families defined by the first operand and operator

Locator: Abstract

> Layer interpolation replaces blocks 20–28 by the midpoint of their step-50 and step-275 parameters.

Locator: App. (Intervention definitions)

[49] [Cliff Tokens: Analyzing Failure Trigger Tokens in LLM Mathematical Reasoning (arXiv 2606.25524v3)](https://arxiv.org/html/2606.25524v3) (Jaeyong Ko, Jinu Lee, Pilsung Kang, Yukyung Lee; 2026) — Rollout-defined failure-trigger tokens.

> We define the cliff token: the token in a reasoning trace where the probability of reaching the correct answer via Monte Carlo rollouts (success probability) drops significantly.

Locator: Sec. 1 (Introduction)

[50] [Beyond the 80/20 Rule: High-Entropy Minority Tokens Drive Effective Reinforcement Learning for LLM Reasoning (NeurIPS 2025; arXiv 2506.01939v2)](https://arxiv.org/html/2506.01939v2) (Shenzhi Wang, Le Yu, Chang Gao, Chujie Zheng, Shixuan Liu, Rui Lu, Kai Dang, Xionghui Chen, Jianxin Yang, Zhenru Zhang, Yuqiong Liu, An Yang, Andrew Zhao, Yang Yue, Shiji Song, Bowen Yu, Gao Huang, Junyang Lin; 2025) — High-entropy 'forking' tokens carry RLVR's effect.

> These findings highlight the significance of high-entropy tokens (i.e., forking tokens) to RLVR.

Locator: Abstract

[51] [Top-nσ: Not All Logits Are You Need (arXiv 2411.07641v1; ACL 2025 as 'Top-nσ: Eliminating Noise in Logit Space for Robust Token Sampling of LLM')](https://arxiv.org/html/2411.07641v1) (Chenxia Tang, Jianchun Liu, Hongli Xu, Liusheng Huang; 2024) — Logits split into a noisy and an informative region; the candidate set is stable regardless of temperature.

[52] [ACL Anthology 2025.acl-long.528 (Top-nσ, ACL 2025)](https://aclanthology.org/2025.acl-long.528/) (2025) — Venue/title confirmation for [49].

[53] [The Effect of Sampling Temperature on Problem Solving in Large Language Models (Findings of EMNLP 2024; arXiv 2402.05201v3)](https://arxiv.org/html/2402.05201v3) (Matthew Renze, Erhan Guven; 2024) — Temperature 0.0-1.0 has no statistically significant effect on problem-solving accuracy.

> our empirical results indicate that changes in temperature from 0.0 to 1.0 do not have a statistically significant impact on LLM performance for problem-solving tasks.

Locator: Abstract

[54] [MarginGate: Sparse Margin-Triggered Verification for Batch-Invariant LLM Inference (arXiv 2605.30218v1)](https://arxiv.org/html/2605.30218v1) (Kexin Chu, Yang Zhou, Wei Zhang; 2026) — Low top-1/top-2 logit margins expose flip risk under batch numerics.

> K/V perturbations remain flat before flips, while low top-1/top-2 logit margins expose much of the flip risk.

Locator: Abstract

[55] [Robust fine-tuning of zero-shot models (WiSE-FT; CVPR 2022; arXiv 2109.01903v3)](https://arxiv.org/html/2109.01903v3) (Mitchell Wortsman, Gabriel Ilharco, Jong Wook Kim, Mike Li, Simon Kornblith, Rebecca Roelofs, Raphael Gontijo-Lopes, Hannaneh Hajishirzi, Ali Farhadi, Hongseok Namkoong, Ludwig Schmidt; 2021) — Definition of weight-space interpolation with a mixing coefficient.

> Our method linearly interpolates between the zero-shot and fine-tuned models with a mixing coefficient

Locator: Fig. 1 caption

[56] [Mitigating the Alignment Tax of RLHF (EMNLP 2024; arXiv 2309.06256v4)](https://arxiv.org/html/2309.06256v4) (Yong Lin, Hangyu Lin, Wei Xiong, Shizhe Diao, Jianmeng Liu, Jipeng Zhang, Rui Pan, Haoxiang Wang, Wenbin Hu, Hanning Zhang, Hanze Dong, Renjie Pi, Han Zhao, Nan Jiang, Heng Ji, Yuan Yao, Tong Zhang; 2023) — Averaging pre- and post-RLHF weights gives the best alignment-forgetting Pareto front: direct base/aligned interpolation precedent.

> In this paper we show that model averaging, which simply interpolates between pre and post RLHF model weights, surprisingly achieves the most strongest alignment-forgetting Pareto front among a wide range of competing methods.

Locator: Abstract

[57] [Should SFT Prefer the Familiar? Diversity Collapse and Recovery via Model Merging (ICLR 2027 submission, OpenReview MYXgOex05m)](https://api2.openreview.net/notes/search?term=Should%20SFT%20Prefer%20the%20Familiar%3F%20Diversity%20Collapse%20and%20Recovery%20via%20Model%20Merging&group=ICLR.cc/2027/Conference&limit=10) (2026) — Merging the fine-tuned model with its pretrained base restores diversity across math and code benchmarks (closest K neighbour).

> To mitigate this effect, we propose a simple recovery approach: merging the fine-tuned model with its pretrained base model before RL.

Locator: Abstract (OpenReview API record)

[58] [ICLR 2024 proceedings page: An Emulator for Fine-tuning Large Language Models using Small Language Models](https://proceedings.iclr.cc/paper_files/paper/2024/hash/389e161125965c0f0ba50420fee45774-Abstract-Conference.html) (2024) — Venue confirmation for EFT [85].

[59] [ICLR 2024 poster page: The Unlocking Spell on Base LLMs](https://iclr.cc/virtual/2024/poster/17473) (2024) — Venue confirmation for URIAL [58].

[60] [The Unlocking Spell on Base LLMs: Rethinking Alignment via In-Context Learning (URIAL; arXiv 2312.01552v1)](https://arxiv.org/html/2312.01552v1) (Bill Yuchen Lin, Abhilasha Ravichander, Ximing Lu, Nouha Dziri, Melanie Sclar, Khyathi Chandu, Chandra Bhagavatula, Yejin Choi; 2023) — Inherited 92d-A2b: aligned top tokens mostly within the base top five (token level, no perturbation).

[61] [Same Candidates, Stronger Reasoning: Rethinking What Post-Training Learns (ICLR 2027 submission, OpenReview ooV5M72O08)](https://api2.openreview.net/notes/search?term=Same%20Candidates%2C%20Stronger%20Reasoning%3A%20Rethinking%20What%20Post-Training%20Learns&group=ICLR.cc/2027/Conference&limit=10) (2026) — Inherited 92d-A2c (VERIFIED-ABSTRACT): 92.9% of post-training top-1 changes stay within the pretrained top-16.

[62] [Verbalized Sampling: How to Mitigate Mode Collapse and Unlock LLM Diversity (arXiv 2510.01171v4)](https://arxiv.org/html/2510.01171v4) (2025) — Inherited 92d-A2a: App. D.3 power-transform sharpening under typicality bias (stylised).

[63] [Creativity Has Left the Chat: The Price of Debiasing Language Models (arXiv 2406.05587v1)](https://arxiv.org/pdf/2406.05587v1) (2024) — Inherited 92d-A1h: a perturbed aligned model returns to its OWN attractor (rival-supporting).

[64] [Samanta et al. 2026 (behaviour crystallization; arXiv 2606.29933v1)](https://arxiv.org/html/2606.29933v1) (2026) — Inherited 92d-A2d: SFT collapses behaviour onto a seed distribution present in the pretrained model.

[65] [Zhou (T.) 2026 (training-time per-prompt forecasts from the base; arXiv 2607.20543v1)](https://arxiv.org/html/2607.20543v1) (2026) — Inherited 92d-A1a/b.

[66] [Duan 2026 (per-problem forecasts; arXiv 2610.04978v1)](https://arxiv.org/html/2610.04978v1) (2026) — Inherited 92d-A1c/d.

[67] [How Diversely Can Language Models Solve Problems? (Lee et al., Findings of EMNLP 2025; arXiv 2503.00691v2)](https://arxiv.org/html/2503.00691v2) (2025) — Inherited 92d-A0a-c: base vs instruct algorithmic diversity is mixed in direction.

[68] [Before the First Token: A Shared Causal Subspace for Response-Length Planning in LLMs (ICLR 2027 submission, OpenReview knirOusGcq)](https://openreview.net/forum?id=knirOusGcq) (2026) — Inherited 92c-C2aa/C2ab: causal pre-generation plan subspace (abstract-level).

[69] [Khalid et al. 2026 (activation noise steering; BEA workshop @ ACL 2026; arXiv 2604.03380v2)](https://arxiv.org/pdf/2604.03380v2) (2026) — Inherited 92c-C1-sited / 92b-b6a: site comparison (embedding/attention) for noise-based diversity.

[70] [Zhu et al. 2026 (STARS; ICLR 2026; arXiv 2601.22010v1)](https://arxiv.org/html/2601.22010v1) (2026) — Inherited 92c-C1-sitee / 92b-b6b: intra-layer site comparison for test-coverage diversity (App. B.3).

[71] [Where You Inject Diversity Matters: A Unified Framework (arXiv 2606.10302v1)](https://arxiv.org/html/2606.10302v1) (2026) — Inherited 92c-C1-sitea..c / 92d-Ci: text-level injection-site framework.

[72] [Jerge et al. 2026 (prompt-state noise vs temperature; arXiv 2608.21595v1)](https://arxiv.org/html/2608.21595v1) (2026) — Inherited 92c-C1-sitef.

[73] [Nagarajan et al. 2025 (input-layer vs output-layer randomness; ICML 2025; arXiv 2504.15266v4)](https://arxiv.org/html/2504.15266v4) (2025) — Inherited 92c-C1-siteg.

[74] [From Noise to Diversity: Random Embedding Injection in LLM Reasoning (arXiv 2605.11936v2)](https://arxiv.org/html/2605.11936v2) (2026) — Inherited 92b-b6c: random embedding injection widens Pass@N on math; code left to future work.

[75] [Hot or Cold? Adaptive Temperature Sampling for Code Generation (AdapT; AAAI 2024; arXiv 2309.02772v3)](https://arxiv.org/html/2309.02772v3) (2023) — Inherited 92b-b3b.

[76] [Emergent Response Planning in LLMs (ICML 2025; arXiv 2502.06258v3)](https://arxiv.org/html/2502.06258v3) (2025) — Inherited 92c-C2ac.

[77] [Where's the Plan? Locating Latent Planning in Language Models (ICML 2026 MI workshop; arXiv 2605.07984v2)](https://arxiv.org/html/2605.07984v2) (2026) — Inherited 92c-C2ad.

[78] [From Brewing to Resolution: Tracing the Internal Lifecycle of Code Reasoning in LLMs (arXiv 2606.17648v3)](https://arxiv.org/html/2606.17648v3) (2026) — Inherited 92c-C2ah.

[79] [Base-Aligned Model Collaboration (BACo; ICML 2026; arXiv 2511.05650v2)](https://arxiv.org/html/2511.05650v2) (2025) — Inherited 92d-B1i/92d-Ca.

[80] [Conformative decoding (Peeperkorn et al.; arXiv 2507.20956v1)](https://arxiv.org/html/2507.20956v1) (2025) — Inherited 92d-Cb.

[81] [Switch Generation (Feng et al.; arXiv 2510.09913v1)](https://arxiv.org/html/2510.09913v1) (2025) — Inherited 92d-Cc.

[82] [Selective Layer Restoration (Zhang et al.; arXiv 2602.06665v1)](https://arxiv.org/html/2602.06665v1) (2026) — Inherited 92d-B1f/92d-Eb.

[83] [Controlling the Diversity-Quality Trade-Off of LLMs by Merging Models Before and After Alignment (Sumita et al.; arXiv 2610.22999v1)](https://arxiv.org/html/2610.22999v1) (2026) — Inherited 92d-B1g/92d-Ce.

[84] [Weight ensembling improves reasoning in language models (Dang et al.; COLM 2025; arXiv 2504.10478v4)](https://arxiv.org/html/2504.10478v4) (2025) — Inherited 92d-Cf (WiSE-FT with an early SFT checkpoint).

[85] [Hindsight Merging: Diverse Data Generation with Language Models (PMLR v286)](https://proceedings.mlr.press/v286/veselovsky25a.html) (2025) — Inherited 92d quotes: +20-50% pass@10 on a coding benchmark from checkpoint interpolation.

[86] [Zhang et al. 2026 (sparse RL-token replacement; arXiv 2610.24663v1)](https://arxiv.org/html/2610.24663v1) (2026) — Inherited 92d-Cd.

[87] [An Emulator for Fine-Tuning Large Language Models using Small Language Models (EFT; ICLR 2024; arXiv 2310.12962v1)](https://arxiv.org/html/2310.12962v1) (Eric Mitchell, Rafael Rafailov, Archit Sharma, Chelsea Finn, Christopher D. Manning; 2023) — Inherited 92d quote (B2/C).

[88] [Tuning Language Models by Proxy (COLM 2024 per arXiv comment; arXiv 2401.08565v4)](https://arxiv.org/html/2401.08565v4) (Alisa Liu, Xiaochuang Han, Yizhong Wang, Yulia Tsvetkov, Yejin Choi, Noah A. Smith; 2024) — Inherited 92d quote (B2/C).

[89] [Nudging: Inference-time Alignment of LLMs via Guided Decoding (ACL 2025; arXiv 2410.09300v4)](https://arxiv.org/html/2410.09300v4) (Yu Fei, Yasaman Razeghi, Sameer Singh; 2024) — Inherited 92d quote (C/A2): base models are uncertain where alignment changes tokens.

[90] [Does Reinforcement Learning Really Incentivize Reasoning Capacity in LLMs Beyond the Base Model? (NeurIPS 2025 oral; arXiv 2504.13837v5)](https://arxiv.org/html/2504.13837v5) (2025) — Inherited 92d-A0 quotes.

[91] [The Invisible Leash: Why RLVR May or May Not Escape Its Origin (arXiv 2507.14843v5)](https://arxiv.org/html/2507.14843v5) (2025) — Inherited 92d-A0 quotes (net support shrinkage).

[92] [Mathematical discoveries from program search with large language models (FunSearch; Nature 625, 2024)](https://www.nature.com/articles/s41586-023-06924-6) (2024) — Inherited 92c-C3ca.

[93] [AlphaEvolve (Novikov et al.; arXiv 2506.13131v1)](https://arxiv.org/html/2506.13131v1) (2025) — Inherited 92c-C3cb.

[94] [Zhou (Y.) 2026 (cross-patching base states into a descendant; arXiv 2605.07284v2)](https://arxiv.org/html/2605.07284v2) (2026) — Inherited 92d-B1a/b.

[95] [Oozeer et al. 2025 (activation transfer between base and fine-tuned models; ICML 2025; arXiv 2503.04429v4)](https://arxiv.org/html/2503.04429v4) (2025) — Inherited 92d-B1c.

[96] [Safety Alignment Should Be Made More Than Just a Few Tokens Deep (Qi et al.; ICLR 2025; arXiv 2406.05946v1)](https://arxiv.org/html/2406.05946v1) (2024) — Inherited 92b-b3a.

[97] [Lost in the bf16 Cast: Exporting Ternary Language Models Can Revert Most Low-Learning-Rate Code Changes (arXiv 2610.07853)](https://arxiv.org/abs/2610.07853) (2026) — Screened (R2): bf16 export casting reverts fine-tuning changes (numerics context).

[98] [Measuring the Task Value of Precision Upgrades in Closed-Loop Agents (arXiv 2610.24346)](https://arxiv.org/abs/2610.24346) (2026) — Screened (R3): BF16 fallback actions in 4-bit-weight agents rescue and damage tasks in near-equal numbers.

[99] [Flat Score, Amplified Failures: How the Error Budget Masks Damage in Quantized LLM Agents (arXiv 2607.27275)](https://arxiv.org/abs/2607.27275) (2026) — Screened (R4): 4-bit weights look free on the score while amplifying existing failures.

[100] [Displacement Is Not Direction: Evaluating Fidelity Metrics for Quantized LLM Deployment (arXiv 2606.19558)](https://arxiv.org/abs/2606.19558) (2026) — Screened (R4): KL fidelity metrics lose predictive power near baseline.

[101] [SafeQ: Safety Alignment Preserving Post-Training Quantization for Language Models (ICLR 2027 submission)](https://openreview.net/forum?id=70RbLmZVvW) (2026) — Screened (R2): safety-preserving PTQ for W4A16 and W4A4 (activation quantisation included; no interventions).

[102] [Better Fixed-State Fidelity Need Not Improve Closed-Loop Performance in Quantized Neural Policies (ICLR 2027 submission)](https://openreview.net/forum?id=5R8LqE51Hr) (2026) — Screened (R2): fidelity on fixed states does not predict closed-loop return of quantised policies.

[103] [AlignRadar: Forecasting Emergent-Misalignment Risk Before Fine-Tuning (ICLR 2027 submission)](https://openreview.net/forum?id=xmDdTDx241) (2026) — Screened (R1): dataset-level forecast of EM risk from the base model before SFT (FLAG-B type).

[104] [Rebellious Student: Reversing Teacher Signals for Reasoning Exploration with Self-Distilled RLVR (arXiv 2605.10781v1)](https://arxiv.org/html/2605.10781v1) (2026) — Screened (R1): replicates the base/RL top-k overlap analysis at high-divergence positions.

[105] [QGATE: Counterexample-Guided Precision Patching of Quantized LLMs with Fail-Closed Slice Reporting (ICLR 2027 submission)](https://openreview.net/forum?id=Al2c9FzOI7) (2026) — Screened (R1): repairs quantisation flips by precision patching of weight groups (no activation-level intervention).

[106] [AARONKANG04/quantization-interpretability (GitHub repository)](https://github.com/AARONKANG04/quantization-interpretability) — E6 grey literature (not fetched): NVFP4/FP8 damage study with tuned lens and SAE features on bf16 vs low-bit activations; repositories never fire a flag.

[107] [arXiv API (id_list metadata and search_query)](https://export.arxiv.org/api/query) — Versions, v1 dates, titles, comments/journal_ref (evidence/arxiv_meta.json) and engine E3 of the saturation search.

[108] [Semantic Scholar Graph API (/paper/search, /citations, /references)](https://api.semanticscholar.org/graph/v1/paper/search) — Engine E4 and forward/backward citation chasing (FC/BC).

[109] [OpenReview API v2 notes/search (ICLR.cc/2027/Conference)](https://api2.openreview.net/notes/search) — Engine E5 and the abstract records quoted as VERIFIED-ABSTRACT; notes?id= and PDFs returned HTTP 403 on 2026-10-21/22.

## Verification

Numbered citations resolve to unique listed sources. Passage checks test text occurrence, not claim truth or entailment. Author/year metadata and locators are not independently verified. Details: `research_verification.json`.

- Source [1]: text found — We study only bitsandbytes weight-only quantization (INT8, NF4); activation quantization (W8A8, W4A4
- Source [1]: text found — Despite this, steering vectors remain highly collinear with their FP16 siblings (cosine similarity 0
- Source [2]: text found — Steering directions can remain aligned across model precision changes while their functional effects
- Source [3]: text found — We study steering compatibility with the intervention layer, direction, and strength held fixed acro
- Source [4]: text found — We directly applied quantization from 32 bits to 8 bits to all weights and activations of the model 
- Source [4]: text found — when precision is reduced from 32 bits to 8 bits, direct quantization (also called Round-to-Nearest 
- Source [5]: text found — floor, 13.0% and 51.2% of full-displacement interactions fell below the threshold
- Source [8]: text found — We explore 16-bit (BF16) and 4-bit (NF4) versions of smaller models to expose harmful tool-call comp
- Source [9]: text found — Noticeably, our theoretical claim does not cover quantization effects. However, we experiment with a
- Source [10]: text found — where safety lives in non-outlier channels collaterally damaged by outlier-driven scale factors
- Source [11]: text found — INT8 with outlier handling preserves perplexity in both languages, while naive FP8 casting degrades 
- Source [11]: text found — Our FP8 results reflect a naive casting stress test (no calibration/scaling), not an optimized FP8 r
- Source [12]: text found — For instance, under bfloat16 precision with greedy decoding, a reasoning model like DeepSeek-R1-Dist
- Source [14]: text found — We use `Qwen/Qwen3-235B-A22B-Instruct-2507` and sample 1000 completions at temperature 0
- Source [15]: text found — At 1.7B each arm reproduces itself bit-for-bit across cold restarts, yet the arms agree on no sequen
- Source [16]: text found — Serving four-bit weights through 16-bit kernels left divergence not detectably different from 16-bit
- Source [16]: text found — Near-tie decisions became only about 1.2 times as common, while the cache-path change in top-two mar
- Source [17]: text found — the outcome depends primarily on the top-two logit margin at the lm_head
- Source [18]: text found — However, even when the accuracy of baseline and compressed model are similar, we observe the phenome
- Source [19]: text found — W8A8-FP quantization is essentially lossless, preserving the uncompressed model’s accuracy across al
- Source [21]: text found — Based on the fact that weights are easy to quantize while activations are not, SmoothQuant smooths t
- Source [22]: text found — the sparse but systematic large magnitude outlier features that ruin quantization precision once the
- Source [23]: text found — Many of these activations are found within the starting word token and delimiter tokens.
- Source [24]: text found — we propose an 8-bit floating point (FP8) binary interchange format consisting of two encodings - E4M
- Source [25]: text found — For instance, a 4-bit quantized model retains the trustworthiness of its original counterpart, but m
- Source [26]: text found — The quantization method is fine-grained `fp8` quantization with block size of 128.
- Source [27]: text found — Dynamic, per-token quantization on the activations
- Source [28]: text found — tiny perturbations along them can cause large, erratic, input-dependent behavioral swings
- Source [29]: text found — We apply it to GLM-5.3-Flash (320B parameters, 288 routed experts, a four-wide hyper-connection resi
- Source [30]: text found — Around 30% of RL top-1 tokens are already ranked first under the base model, and over 80% (DAPO) and
- Source [30]: text found — inserting only a small fraction of RL-sampled tokens into base generations progressively recovers RL
- Source [31]: text found — The aligned model (instruct) sharply suppresses the likelihood of the harmful generation. In contras
- Source [31]: text found — we propose that these behaviors can be better understood as a regression to base model behavior.
- Source [32]: text found — Fine-tuning in the opposite direction of post-training (e.g., safe vs. unsafe) causes post-trained m
- Source [33]: text found — The Rebound Effect [14] refers to the tendency of fine-tuned models to revert toward their pre-train
- Source [34]: text found — We instead cast it as a single activation-space direction, pointing from the safety-aligned model to
- Source [34]: text found — once we fixed the reference family and the test in advance, every additional trajectory we tried mov
- Source [35]: text found — We observe that the top-ranked tokens in jailbroken LLMs are largely found within the top ten tokens
- Source [36]: text found — A persona subspace present in the model before fine-tuning carries broad misalignment. The subspace 
- Source [36]: text found — Provenance. The extraction is from a released instruction-tuned checkpoint, not a pre-alignment base
- Source [37]: text found — the representational distance between an evaluation prompt and the training data centroid, both in t
- Source [37]: text found — We select models of various sizes and from multiple model families: Qwen2.5-14B-Instruct, Qwen2.5-32
- Source [38]: text found — We instead seal a per-head, signed forecast from the base model, fine-tune, and confirm it.
- Source [39]: text found — our method achieves this reversal by contrasting the output token distribution of a safety-aligned l
- Source [40]: text found — However, a barrier arises for going beyond the support of the base model.
- Source [41]: text found — We introduce the power distribution as a useful sampling target for reasoning tasks. Since it can be
- Source [41]: text found — Our algorithm achieves comparable performance to GRPO within the posttraining domain (MATH500) but c
- Source [42]: text found — Embedding perturbation does not disrupt reasoning coherence.
- Source [42]: text found — We find that the resulting continuations remain coherent and on-task.
- Source [43]: text found — reasoning mode selection is driven by weak signals, making it a key source of instability and side e
- Source [43]: text found — We find that targeted prefix perturbation consistently outperforms temperature scaling across both m
- Source [44]: text found — We hypothesize that there exist key forking tokens, such that re-sampling the system at those specif
- Source [44]: text found — We find many examples of forking tokens, including surprising ones such as punctuation marks, sugges
- Source [46]: text found — This model uses change point detection to identify forking points, and kernel-pooling to smooth esti
- Source [47]: text found — We term these sentences thought anchors. These are generally planning or uncertainty management sent
- Source [48]: text found — we analyze the Countdown task, whose solution space can be exhaustively enumerated into discrete ent
- Source [48]: text found — Layer interpolation replaces blocks 20–28 by the midpoint of their step-50 and step-275 parameters.
- Source [49]: text found — We define the cliff token: the token in a reasoning trace where the probability of reaching the corr
- Source [50]: text found — These findings highlight the significance of high-entropy tokens (i.e., forking tokens) to RLVR.
- Source [53]: text found — our empirical results indicate that changes in temperature from 0.0 to 1.0 do not have a statistical
- Source [54]: text found — K/V perturbations remain flat before flips, while low top-1/top-2 logit margins expose much of the f
- Source [55]: text found — Our method linearly interpolates between the zero-shot and fine-tuned models with a mixing coefficie
- Source [56]: text found — In this paper we show that model averaging, which simply interpolates between pre and post RLHF mode
- Source [57]: text found — To mitigate this effect, we propose a simple recovery approach: merging the fine-tuned model with it

## Follow-up Questions

- TOP (FLAG E partly fired at contemporaneous abstract level): once ICLR 2027 PDFs open (reviews due about end of October 2026), do OpenReview 8iTqrW1sxY ('Stable Directions, Different Effects') and h57duZqLOr ('Activation Steering under Low-Bit Quantization') include ACTIVATION quantisation (W8A8, FP8 activations, KV cache), or weights only? If they include activations, Claim E becomes a replication in a new setting (content-free nudges, code-algorithm choice).
- Does PAHQ's failure mode (small patch effects truncated to zero under unscaled FP8/RTN) appear under per-token-scaled FP8 W8A8? The run's W16A8 arm with per-token absmax readouts can answer this directly.
- In the run's own data, what fraction of nudge landings lie within the tuned model's own teacher-forced top-k (q_lik) or sampled tail (q_tail), compared with the base runner-up? Weak-to-strong jailbreaking predicts that the tuned model's own ranking already contains many landings.
- Re-check Same Candidates (ooV5M72O08) and Before the First Token (knirOusGcq) when their PDFs open, and confirm whether Locked at the Entrance (now arXiv 2608.29188) compares its entrance-family coverage with the base model.
- UNMAPPED citation numbers: the one-to-one assignment of the hypothesis's own reference numbers 88-91, 92/93/102, 98/99 and 81/82 to papers needs the hypothesis reference list (inherited/citation_map.json maps only the sets of inherited rows).
- Which FP8 scheme did the iteration-4 engine actually use: block-128 fine-grained checkpoint scales or dynamic per-token activation scales? The attribution readout depends on it.

---
*Generated by AI Inventor Pipeline*
