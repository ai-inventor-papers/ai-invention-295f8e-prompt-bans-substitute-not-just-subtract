# Has prior work restored base-model variety?

## Summary

Dated (2026-10-21) positioning audit for iteration-5 Claims A-D, extending art_kjrCpQnPaniY (Tables 92b/92c; its 112 quotes cited by row id, not re-verified). Provides paste-ready Table 92d (55 rows: 92d-A0/A1/A2/B1/B2/C/E/G; design facts only) with 137 verbatim, versioned quotes from 93 references (111 VERIFIED full text, 21 VERIFIED-ABSTRACT ICLR 2027 submissions, 5 VERIFIED-BLOG; 0 mismatches; 137/137 re-matched by a live fetch_grep pass). Saturation search under a protocol frozen before the first call: 9 families/25 strings on OpenAlex/Crossref, arXiv API, Semantic Scholar, OpenReview ICLR 2027 + grey literature, forward citations of 8 seeds, round 2 (6 queries), round 3 (forward + backward snowballing); 169 calls, 4,508 raw hits, 3,506 unique, 49 scored; stop rule met after round 3. FLAG A (base states written into the tuned model + diversity outcome): NOT FIRED, narrowly — the method is published (cross-patching of base upstream states into a descendant: Zhou (Y.) arXiv 2605.07284, rubric 2.5; Oozeer et al. ICML 2025; Du et al. COLM 2025; Prakash et al. ICLR 2024 CMAP) and the goal is published at weight level (Selective Layer Restoration 2602.06665; aligned/base FrankenMerging 2610.22999; layer interpolation in ICLR 2027 'Locked at the Entrance'; WiSE-FT; Hindsight Merging +20-50% pass@10 on code) and token level (BACo ICML 2026, conformative decoding, Switch Generation). B1 may not say 'first' for the transplant; may claim the combination (prefill task-spec states, test-checked algorithm choice on code, matched-random and cross-task controls). FLAG B: PARTLY FIRED — training-time per-prompt forecasts from the frozen base exist (Zhou (T.) 2607.20543; Duan 2610.04978, where base pass rate/likelihood explain only 0.30/0.24 of explainable variance; Lookahead ICLR 2027; Reasoning Boundary Paradox NeurIPS 2026); inference-time movability (A1) and landing identity (A2) remain open; A2 has only stylised/retrospective support (Verbalized Sampling power-sharpening; URIAL top-5; 'Same Candidates' 92.9% within base top-16; seed-distribution collapse). FLAG C: PARTLY FIRED — Lee et al. (Findings EMNLP 2025) compare DeepSeek-Coder-6.7B Base vs Instruct (test-checked, LLM-judge clusters) and find a MIXED direction; 'first base-vs-tuned algorithm-level comparison' struck; premise row reads 'contradicting in part'. B2/D: PASTA (2605.30526) already ablates an aligned-minus-base residual direction during decoding with orthogonal random-direction controls (style outcome) -> frame as replication in a new setting. C: base-aligned collaboration is an occupied lane; base-intent arm = sentence-granularity instance. Reviewer baselines: Qwen3-8B Base/Instruct weight interpolation, SLR/FrankenMerging at B1 block ranges, BACo token routing, EFT/proxy-tuning, template-controlled contrasts (Nakamura 2026). 27 corrections (e.g., 2506.17871 is v4/TMLR 2026 and its 'order of magnitude' is the v1 figure; Decan is an ICML 2026 workshop paper; PASTA and Nudging retitled; OpenAlex cites: returned 0). Files: research_report.md, evidence/{quotes_iter5,saturation_hits_iter5,search_log_iter5}.jsonl, evidence/flags.json, evidence/protocol.json.

## Research Findings

# Has prior work restored base-model variety? Positioning audit for iteration 5 (Table 92d)

*Retrieval date: 2026-10-21. Every quote below was copied from the paper's own versioned text (arXiv HTML vN, the PDF where HTML is missing, the ACL Anthology / PMLR / NeurIPS page, an OpenReview API record or the grey-literature post) and checked with the inherited normalisation rule. This audit extends art_kjrCpQnPaniY (Tables 92b/92c): its 112 quotes are cited by row id and were not re-verified. It quotes no run-internal result: rows describe design facts only.*

## 1. Scope, date and method

- **Question.** As of 2026-10-21, has any paper, preprint or ICLR 2027 submission (a) predicted from a base model's own distribution where post-training narrows, whether the tuned model can be pushed off its default, or where the push lands (Claims A1/A2); (b) transplanted or interpolated base-model hidden states into the tuned descendant to restore output or solution diversity, or pushed along a base-minus-tuned direction (B1, B2/D); (c) measured test-checked, algorithm-level diversity of a base model against its tuned descendant on code (the premise, A0); (d) priced activation-level plan noise against text-level plan samplers, base-aligned collaboration and departure-matched decoding (C)?
- **Sources and versions.** Versions, v1 dates, titles, comment and journal_ref lines for every arXiv id come from the arXiv API [1]. Full texts of the latest versions were cached with the aii-web-tools fetch core (HTML first; PDF for 2406.05587v1, whose HTML is unavailable). Earlier versions were fetched where a number or title changed: 2506.17871 v1/v3/v4 and 2410.09300 v1/v4.
- **Quotes.** 137 quotes from 93 references: 111 VERIFIED on full text, 21 VERIFIED-ABSTRACT (ICLR 2027 submissions; OpenReview PDFs return HTTP 403), 5 VERIFIED-BLOG, 0 MISMATCH. Where arXiv HTML renders a MathML number twice ("0.300.30"), the quote is split with [...] at that point so the rendered number is matched once. An independent live second pass with the skill's fetch_grep re-matched **137/137** quotes (evidence/qa_second_pass_iter5.jsonl).
- **Saturation search (PRISMA-S items in reproducibility.md).** The protocol (lanes, 25 query strings in 9 families, engines, window, rubric, flags, stop rule) was frozen in evidence/protocol.json before the first call (written 14:50:21Z; first call 14:51:23Z; sha256 `96c720df49be3307...` after a logged timestamp-only amendment). Round 1: every family on E1 (OpenAlex/Crossref via the skill), E3 (arXiv API, cs.CL/LG/AI, newest first), E4 (Semantic Scholar, year=2026) and E5 (OpenReview ICLR 2027 pool); F4/F5/F7 also on E6 (grey literature via WebSearch); forward citations of 8 seeds (Semantic Scholar; OpenAlex `cites:` returned 0 because OpenAlex records zero citations for all four nearest neighbours). Round 2: 6 queries built from the vocabulary of included hits. Round 3: forward citations of the 6 closest new hits and backward references of the two closest hits per flag. Totals: 169 logged calls, 4508 raw hits, 3506 unique records after de-duplication (223 already seen by the iteration-4 audit and re-screened), 2587 in the window, 2298 passing the keyword pre-screen; manual title screens of the ranked shortlists (311 base-vs-tuned, 248 code-x-diversity, 108 activation-x-diversity, 344 round-2 and 25 round-3 new records); 49 hits scored on the rubric (40 in window).
- **Rubric.** The O/I/C axes of Tables 92b/92c, made claim-specific in the protocol; each axis scores 1 / 0.5 / 0; a total of at least 2.5 occupies, 1-2 is adjacent, below 1 irrelevant. The flags use the frozen definitions, including their PARTLY FIRED clauses.
- **Contemporaneity.** contemporaneous_4mo = v1 after 2026-06-21; ICLR 2027 rule = peer-reviewed publication after 2026-07-17 (arXiv-only exempt); every ICLR 2027 submission is tagged contemporaneous.
- **Stop rule.** Round 2 added one new hit scoring at least 1.5 (ICLR 2027 submission 'Same Candidates, Stronger Reasoning', 1.5). Round 3 added none (best new: 1.0). **The stop rule was met after round 3**, well inside the Stage-2 time cap.
- **Departures.** Single screener (borderline calls are published with axis scores and decisive sentences); ICLR 2027 rows are abstract-only; forward citations rest on Semantic Scholar alone; manual screening used ranked shortlists rather than exactly the top 100; venue status for several 2023-2024 anchors (Kirk et al., Huang et al., URIAL, EFT, model arithmetic) is given as unconfirmed.

## 2. Verdict box and flags (as of 2026-10-21)

| Claim | Lane verdict | Deciding references |
|---|---|---|
| A0 premise: tuning narrowed algorithm choice on code (FLAG C) | PARTLY OCCUPIED; contradicting in part | Lee et al. (base vs instruct, mixed direction) [2]; Le Bronnec et al. (base vs RLVR, structural) [3]; text-domain support [4, 5, 6] |
| A1 movability follows the base repertoire (FLAG B) | PARTLY OCCUPIED (training-time, correctness-coverage forecasts exist); inference-time movability OPEN | Zhou (T.) [7]; Duan [8]; Lookahead [9]; Reasoning Boundary Paradox [10] |
| A2 landing = base runner-up | ADJACENT-ONLY (stylised and retrospective support; no landing forecast) | power-sharpening [11]; base top-k inheritance [12, 13]; seed-distribution collapse [14] |
| B1 transplant of base prefill states (FLAG A) | PARTLY OCCUPIED: method occupied, diversity outcome open; FLAG A NOT FIRED | cross-patching [15]; base-activation patching [16, 17, 18]; weight-level diversity restoration [19, 20, 21] |
| B2/D de-sharpening push | PARTLY OCCUPIED: method and random-direction control occupied (style outcome) | PASTA [22]; TIRD [23]; ADL [24]; weight-space ExPO / Chat Vector / task negation [25, 26, 27] |
| C knobs head-on | PARTLY OCCUPIED (as in 92c), and base-aligned collaboration is an occupied lane | BACo [28]; conformative decoding [29]; Switch Generation [30]; IFG / PlanSearch / departure-matched decoding [31, 32, 33] |
| E second family (gemma-3-4b pt/it) | ADJACENT-ONLY | Gemma base/chat divergence caution [34]; Gemma in SLR [19] |
| G novelty boundary | unchanged from 92c C3c (no new 2026 hit) | [35, 36] |

**FLAG A — NOT FIRED (narrowly).** No paper writes base-model hidden states into the forward pass of its tuned descendant AND reports a change in output or solution diversity. Each half is published separately. *Mechanism:* Zhou's cross-patching replaces "the hidden state entering the late boundary ... for all sequence positions" with the base model's state and runs boundary and token controls, but its outcome is a next-token target margin at the first base/descendant divergence [15]. On the rubric it scores O 0.5 / I 1 / C 1 = 2.5, which occupies B1's *method*. Earlier anchors are Oozeer et al. (base activations replace the fine-tuned model's to remove a backdoor; single-layer patching cuts the trigger by up to 60%) [16], Du et al. (base-to-post patching of knowledge representations) [17] and Prakash et al.'s CMAP [18]. *Goal at other levels:* restoring a layer interval to pre-trained weights recovers diversity (SLR) [19]; splicing aligned lower layers with base upper layers raises semantic diversity and beats temperature sampling (FrankenMerging) [20]; layer interpolation restores entrance diversity on Countdown [21]; base-aligned token routing does the same at the token level [28]. The closest cross-domain analogue steers distilled diffusion students along teacher directions at an identified block [37]. Grey-literature search (LessWrong, Alignment Forum, transformer-circuits.pub) found only adjacent work [38, 34, 39].

**FLAG B — PARTLY FIRED.** Per-prompt forecasts from the frozen base model of where post-training narrows already exist, but at training time and for correctness coverage. Zhou (T.) decomposes prompts "by frozen base-model behavior" and predicts that coverage loss localizes to boundary prompts [7]. Duan forecasts per-problem post-training gains and finds that base pass rate and the likelihood of a correct solution explain only a minority of the explainable variance (0.30 and 0.24) [8]. Lookahead predicts which IFEval prompts degrade from the base model plus a reward model [9]. The Reasoning Boundary Paradox orders RLVR's winners and losers by base likelihood [10]. None forecasts the *inference-time* movability of the tuned model, or the *identity* of the algorithm a push or ban lands on, from the base model's per-task algorithm distribution. The landing prediction (A2) has only stylised or retrospective support: the KL-optimal aligned policy is a power-sharpened reference policy that "amplif[ies] its modes" [11]; aligned top tokens sit mostly within the base top-5 [12]; 92.9% of post-training top-1 changes stay within the pretrained top-16 [13]; SFT collapses onto a seed distribution present in the pretrained model [14].

**FLAG C — PARTLY FIRED.** Lee et al. compare DeepSeek-Coder-6.7B Base and Instruct with test-checked correctness and LLM-judge algorithm clusters. They find that instruction tuning "decreases algorithmic diversity in AtCoder-introductory problems, but increases it in other problems" [2]. Le Bronnec et al. find RLVR descendants lose structural (JPlag/Vendi) diversity against their base on most prompts, but not at the algorithm level [3]. DivAlgo has no base-vs-instruct pairing [40]. Generative Monoculture's code arm had no open-weight base model, because the open code models "were [not] able to produce code solutions" [41]. **'First base-versus-tuned algorithm-level comparison' is struck**, and the premise row reads *contradicting in part*.

### 2.1 Permitted novelty wording (each sentence carries the date and points to evidence/)

- **A0:** "Unlike prior LLM-judged comparisons of base and instruct code models, which found instruction tuning narrows algorithmic diversity on easy problems but widens it on harder ones [Lee et al.], we label algorithms by execution traces and AST over correct programs." Do not claim to be first, and do not state the premise as settled.
- **A1:** "Prior work forecasts, per prompt and from the frozen base model, which prompts RL training stops solving [Zhou; Duan; Lookahead]; to our knowledge (dated search 2026-10-21; evidence/), none forecasts whether the deployed instruct model can be pushed off its default algorithm from the base model's own per-task algorithm distribution." Report a simple base-signal baseline, because Duan finds such signals weak.
- **A2:** "To our knowledge, no prior work forecasts which alternative a push or prohibition installs in the tuned model; stylised accounts predict that alignment sharpens the base model's ranking [Verbalized Sampling; URIAL; Same Candidates]."
- **B1:** "To our knowledge (dated search 2026-10-21), no prior work writes base-model prefill states into the instruct model to test where post-training narrows solution choice. Cross-model patching of base states into a descendant exists for next-token decisions, backdoors and factual recall [Zhou 2026; Oozeer 2025; Du 2025; Prakash 2024], and base-aligned mixing for diversity exists at the token, logit and weight level [BACo; conformative decoding; Nudging; EFT; SLR; FrankenMerging; WiSE-FT; Hindsight Merging]." The word 'first' is not allowed for the transplant mechanism.
- **B2/D:** Frame it as a replication of aligned-minus-base direction ablation [PASTA] in a new setting (algorithm choice in code), scored against matched-norm isotropic pushes. Do not frame it as a new knob.
- **C:** "The base-intent arm is a sentence-granularity instance of base-aligned collaboration [BACo; Switch Generation; conformative decoding]." C1's contrast-set limits from 92c still apply.

### 2.2 Reviewer baselines the search implies (recommendations, not design changes)

1. **Weight interpolation between Qwen3-8B-Base and Qwen3-8B**, as the weight-space counterpart of T(lambda). Precedents: WiSE-FT recovers pass@k beyond what temperature can [42]; Hindsight Merging reports a "20-50% increase in pass@10 ... across a coding benchmark" [43]; base-model merging before RL on code [44].
2. **Layer restoration and splicing (SLR; FrankenMerging) at the B1 block ranges**, the closest diversity neighbours of the site-specific transplant [19, 20].
3. **BACo-style token routing** as the strongest base-aligned collaboration baseline for the base-intent arm [28]; rl-replace-style sparse substitution [45].
4. **Logit-level base/tuned arithmetic** (EFT / proxy-tuning) as the logit-space counterpart of B2/D [46, 47].
5. **pass@k coverage at large k** as context for A0 [48], judged against measured noise and template cells [49].
6. **Template control** for every base-minus-instruct contrast (B2/D direction, E family) [50].

## 3. Table 92d — paste-ready (design facts only; no run results)

| Row | Claim (one line) | Neighbour (authors, arXiv v1 year, venue status) | Verbatim quote | URL; section; version | Retrieved | Relation | What this run adds, or 'replication' |
|---|---|---|---|---|---|---|---|
| 92d-A0a | Premise: tuning narrowed an algorithm choice the base model makes more evenly (code, algorithm level) | Lee et al., 2025, Findings of EMNLP 2025 [2] | "When comparing the Deepseek-base and Deepseek-instruct models, algorithmic diversity shows different patterns: instruction tuning decreases algorithmic diversity in AtCoder-introductory problems, but increases it in other problems." | https://arxiv.org/html/2503.00691v2; Sec. 4.2, Findings 5; v2 | 2026-10-21 | contradicts-in-part | Test-checked mechanism labels over correct programs (runtime tracer + AST + blind judge) instead of LLM-judge clusters; same chat-templated prompt for base and instruct; a two-family base/instruct design (Qwen3-8B, gemma-3-4b); NOT 'first base-vs-tuned algorithm-level comparison' (FLAG C partly fired) |
| 92d-A0b | (same claim) | Lee et al., 2025, Findings of EMNLP 2025 [2] | "This suggests that instruction tuning favors single, straightforward answers for simple problems while promoting the exploration of multiple approaches for complex problems." | https://arxiv.org/html/2503.00691v2; Sec. 4.2, Findings 5; v2 | 2026-10-21 | contradicts-in-part | Per-task test of the premise; Lee et al.'s difficulty split predicts the premise can fail on harder tasks |
| 92d-A0c | (same claim) | Lee et al., 2025, Findings of EMNLP 2025 [2] | "we employ the Llama-3.1-8B-Instruct model (Llama, 2024) to assess algorithmic relevance between two implementations." | https://arxiv.org/html/2503.00691v2; Sec. 4.1, settings for diversity metrics; v2 | 2026-10-21 | context | Mechanism labels checked by execution traces rather than an LLM judge |
| 92d-A0d | (same claim) | Le Bronnec et al., 2026, arXiv preprint (under review) [3] | "Relative to the corresponding base model, Base-RLVR decreases JPlag diversity in 57.2% [...] of comparisons and decreases Vendi score in 65.3% [...] of comparisons." | https://arxiv.org/html/2605.28022v1; Sec. 4 (Correctness-only RLVR concentrates repeated implementations); v1 | 2026-10-21 | adjacent | Algorithm-level (not structural near-duplicate) diversity; instruction-tuned rather than RLVR descendant |
| 92d-A0e | (same claim) | Wu et al., 2024, ICLR 2025 (poster) [41] | "However, neither of the models were able to produce code solutions in our trials." | https://arxiv.org/html/2407.02209v1; App. E.4 (open-source code models); v1 | 2026-10-21 | context | Open-weight base/instruct code pair (none in Monoculture's code arm) |
| 92d-A0f | (same claim) | Jangra et al., 2026, arXiv preprint [40] | "For RQ1, we show that uncontrolled sampling (for 24 LLMs) yields considerably less diverse solutions than human solutions" | https://arxiv.org/html/2610.19157v1; Sec. 1 (contributions, RQ1); v1 | 2026-10-21 | context | Base-vs-instruct pairing (DivAlgo has none) |
| 92d-A0g | (same claim) | Yang et al., 2025, TMLR 2026 (v4 comment) [4] | "alignment tuning substantially sharpens the model’s output distribution from the outset, reducing BF by a factor of 2–5 overall, and up to an order of magnitude (e.g., from 12 to 1.2) at the beginning positions." | https://arxiv.org/html/2506.17871v4; Abstract (v4); v4 | 2026-10-21 | supports | replication of base-vs-aligned narrowing at the algorithm level on code |
| 92d-A0h | (same claim) | Liu, 2026, arXiv preprint [5] | "A base-vs-instruct ablation on Qwen3-14B confirms the causal role of alignment: the base model shows 1.0% single-cluster rate vs. 28.5% for the instruct model" | https://arxiv.org/html/2603.24124v2; Abstract; v2 | 2026-10-21 | supports | Code, test-checked; not semantic clusters of QA answers |
| 92d-A0i | (same claim) | Anonymous, 2026, ICLR 2027 submission (under review); contemporaneous by rule [21] | "We show that this contraction is heavily concentrated at the entrance: per-token likelihood shifts are 11x--16x larger prior to the first arithmetic operation than during downstream reasoning." | https://api2.openreview.net/notes/search?term=Locked%20at%20the%20Entrance%2C%20Open%20Inside%3A%20Where%20RLVR%20Narrows%20the%20Solution%20Space&group=ICLR.cc/2027/Conference&limit=10; Abstract (OpenReview API record); VERIFIED-ABSTRACT | 2026-10-21 | supports | Code algorithms instead of Countdown entrance families; base vs instruction-tuned rather than PPO/GRPO |
| 92d-A1a | Movability follows the base repertoire (the tuned model can be pushed off its default only where the base spreads) | Zhou (T.), 2026, arXiv preprint [7] | "decompose prompts by frozen base-model behavior into solved-easy, reachable, boundary, and out-of-reach regimes, turning an aggregate pass@k curve into an attribution problem." | https://arxiv.org/html/2607.20543v1; Sec. 1, contributions; v1 | 2026-10-21 | partly-fires (FLAG B) | Inference-time movability of the tuned model under pushes (not training-time coverage loss); algorithm choice, not correctness; base repertoire (beta, runner-up) committed by sha256 before any push |
| 92d-A1b | (same claim) | Zhou (T.), 2026, arXiv preprint [7] | "Per-Problem Base Anchoring (PBA) is a deliberately simple proof-of-concept: sharpen prompts with sufficient frozen-base correct evidence, and anchor risky prompts to the base distribution." | https://arxiv.org/html/2607.20543v1; Abstract; v1 | 2026-10-21 | partly-fires (FLAG B) | Forecast scored on matched events at inference time |
| 92d-A1c | (same claim) | Duan, 2026, arXiv preprint [8] | "A priori signals capture a minority of it: base pass rate, the likelihood of a correct solution, a larger model’s pass rate and their combinations explain only 0.30 [...] and 0.24 [...] of the explainable variance in gains." | https://arxiv.org/html/2610.04978v1; Abstract; v1 | 2026-10-21 | contradicts-in-part | Must beat (or report against) simple base signals; Duan et al. find base pass rate / likelihood weak predictors of training gains |
| 92d-A1d | (same claim) | Duan, 2026, arXiv preprint [8] | "The missing part lives in the base model’s behaviour on a problem, not in what the problem looks like." | https://arxiv.org/html/2610.04978v1; Sec. 1, contributions; v1 | 2026-10-21 | supports | Base-model behaviour on a task (its algorithm distribution) as the predictor |
| 92d-A1e | (same claim) | Anonymous, 2026, ICLR 2027 submission (under review); contemporaneous by rule [9] | "Lookahead outperforms BoN at predicting which IFEval prompts degrade after training" | https://api2.openreview.net/notes/search?term=Catching%20RLHF%20Failures%20before%20Training&group=ICLR.cc/2027/Conference&limit=10; Abstract (OpenReview API record); VERIFIED-ABSTRACT | 2026-10-21 | partly-fires (FLAG B) | Uses the base model alone (no reward model); outcome = movability under activation/prompt pushes |
| 92d-A1f | (same claim) | Nguyen et al., 2025, NeurIPS 2026 (poster) [10] | "RLVR disproportionately reinforces problems with high likelihood, correct solutions under the base model while suppressing other initially low-likelihood ones." | https://arxiv.org/html/2510.02230v1; Abstract; v1 | 2026-10-21 | adjacent | Per-task forecast tested on the deployed instruct model rather than a training-dynamics account |
| 92d-A1g | (same claim) | Anonymous, 2026, ICLR 2027 submission (under review); contemporaneous by rule [51] | "A dose- and schedule-matched control that anchors randomly chosen prompts protects as well as our signal-triggered scheme" | https://api2.openreview.net/notes/search?term=How%20Much%2C%20Not%20Where%3A%20RLVR%27s%20Capability%20Loss%20Is%20Dose-Controlled%20and%20Deep-Tail%20Only&group=ICLR.cc/2027/Conference&limit=10; Abstract (OpenReview API record); VERIFIED-ABSTRACT | 2026-10-21 | contradicts-in-part | A random-task control for any 'targeting' claim |
| 92d-A1h | (same claim) | Mohammadi, 2024, arXiv preprint [52] | "We demonstrate this by intentionally perturbing the model’s generation trajectory, effectively nudging it away from its usual output distribution. Surprisingly, the aligned model gracefully finds its way back to its own attractor state and in-distribution response." | https://arxiv.org/pdf/2406.05587v1; Sec. 1 (Introduction); v1 | 2026-10-21 | adjacent | Quantified per task with test-checked labels |
| 92d-A2a | Landing: a push or ban of the tuned model lands on the base model's runner-up algorithm | Zhang et al., 2025, arXiv preprint [11] | "sharpens the reference distribution, amplifying its modes while suppressing the tails. The effect strengthens as typicality bias" | https://arxiv.org/html/2510.01171v4; App. D.3 (Power-Transform Sharpening under Typicality Bias); v4 | 2026-10-21 | partly-fires (stylised) | A per-task, pre-registered forecast of the landing identity (runner-up) scored on matched events — none found |
| 92d-A2b | (same claim) | Lin et al., 2023, arXiv preprint (ICLR 2024 per plan; not confirmed here) [12] | "the top-ranked tokens in aligned LLMs are mostly found within the top five tokens ranked by base LLMs, and the distribution shift is more pronounced in earlier token positions." | https://arxiv.org/html/2312.01552v1; Sec. 1 (Introduction); v1 | 2026-10-21 | supports | Algorithm-level (whole-solution) landings rather than token ranks |
| 92d-A2c | (same claim) | Anonymous, 2026, ICLR 2027 submission (under review); contemporaneous by rule [13] | "92.9% of post-training Top-1 changes remain within the pretrained Top-16 on average, while their relative preferences are substantially reorganized." | https://api2.openreview.net/notes/search?term=Same%20Candidates%2C%20Stronger%20Reasoning%3A%20Rethinking%20What%20Post-Training%20Learns&group=ICLR.cc/2027/Conference&limit=10; Abstract (OpenReview API record); VERIFIED-ABSTRACT | 2026-10-21 | adjacent | Forecast before the push, not retrospective inheritance |
| 92d-A2d | (same claim) | Samanta et al., 2026, arXiv preprint [14] | "the nucleation phase caused by supervised finetuning, in which behavior collapses onto a single seed distribution present in the pretrained LLM; and (3) a settling phase in which reinforcement learning techniques redistribute probability of the collapsed distribution, but largely keep it concentrated on the same options as the seed distribution." | https://arxiv.org/html/2606.29933v1; Abstract; v1 | 2026-10-21 | supports | Code algorithms; prospective |
| 92d-A2e | (same claim) | Fortier et al., 2026, arXiv preprint [6] | "We find that convergence can be revealed and amplified, but not introduced by the SFT data, supporting its role as a catalyst rather than a cause." | https://arxiv.org/html/2608.11426v2; Abstract; v2 | 2026-10-21 | supports | Algorithm choice on code; landing under pushes |
| 92d-A2f | (same claim) | Zhao et al., 2025, COLM 2025 [53] | "Our study reveals that RL algorithms consistently converge towards a dominant output distribution, amplifying patterns in the pretraining data." | https://arxiv.org/html/2504.07912v2; Abstract; v2 | 2026-10-21 | supports | Released base/instruct pair instead of from-scratch models |
| 92d-A2g | (same claim) | Anonymous, 2026, ICLR 2027 submission (under review); contemporaneous by rule [54] | "Second, we demonstrate that RL itself learns to make these same starting cues more likely, while fixing these cues recovers much of its performance gain over the base model." | https://api2.openreview.net/notes/search?term=Base%20Models%20Can%20Reason%20by%20Taking%20a%20Cue%20from%20Their%20Training%20Data&group=ICLR.cc/2027/Conference&limit=10; Abstract (OpenReview API record); VERIFIED-ABSTRACT | 2026-10-21 | supports | Activation-level pushes; algorithm identity |
| 92d-B1a | Transplant: base prefill states (task-spec positions, blocks 12-23, lambda 0.25/0.5/1) written into the instruct model restore the base choice; controls: read position, blocks 0-11/24-35, matched-random, cross-task | Zhou (Y.), 2026, arXiv preprint [15] | "At evaluation, the hidden state entering the late boundary is replaced for all sequence positions and the downstream stack recomputes its own keys and values." | https://arxiv.org/html/2605.07284v2; Sec. 2.1; v2 | 2026-10-21 | occupies (method) | Outcome = test-checked algorithm choice / solution diversity (not a next-token margin); site = task-specification prefill positions; dose lambda; matched-norm random displacement and cross-task patch controls |
| 92d-B1b | (same claim) | Zhou (Y.), 2026, arXiv preprint [15] | "The result is also positive at every tested boundary from 40% depth through the final block, so it is not created by one global rotation or one specially chosen cut." | https://arxiv.org/html/2605.07284v2; Sec. 5 (focused validity tests); v2 | 2026-10-21 | occupies (method) | Site comparison includes read position and early/late block ranges at matched dose |
| 92d-B1c | (same claim) | Oozeer et al., 2025, ICML 2025 [16] | "By replacing the fine-tuned model’s activations with the corresponding base model activations, we assess the effectiveness of this technique in mitigating the backdoor." | https://arxiv.org/html/2503.04429v4; Sec. 4.4 (Switch from Fine-tuned to Base Models); v4 | 2026-10-21 | method-overlap | Diversity/algorithm outcome instead of backdoor removal |
| 92d-B1d | (same claim) | Du et al., 2025, COLM 2025 [17] | "We further conduct cross-model experiments by patching hidden representations from base to post (forward patching) and from post to base (backward patching)." | https://arxiv.org/html/2504.02904v3; Sec. 3 (knowledge storage); v3 | 2026-10-21 | method-overlap | Behavioural (solution) outcome instead of factual-recall log-probabilities |
| 92d-B1e | (same claim) | Prakash et al., 2024, ICLR 2024 [18] | "Cross-model activation patching shows evidence that (i) the internal representation of both the original model and the fine-tuned models is similar enough so that patching components of the entity-tracking circuit from the fine-tuned models to Llama-7B leads to enhanced performance." | https://arxiv.org/html/2402.14811v1; Sec. 1 (Introduction); v1 | 2026-10-21 | method-overlap | Direction base->tuned (CMAP patched tuned->base) |
| 92d-B1f | (same claim) | Zhang et al., 2026, arXiv preprint [19] | "we hypothesize that mode collapse can be localized to specific layers and that restoring a carefully chosen range of layers to their pre-trained weights can recover diversity while maintaining high output quality." | https://arxiv.org/html/2602.06665v1; Abstract; v1 | 2026-10-21 | adjacent | States rather than weights; code; matched-random control |
| 92d-B1g | (same claim) | Sumita et al., 2026, arXiv preprint [20] | "This approach combines the lower layers of an aligned model with the higher layers of its base model based on the hypothesis that lexical diversity is more closely associated with lower layers and semantic diversity with higher layers." | https://arxiv.org/html/2610.22999v1; Abstract; v1 | 2026-10-21 | adjacent | Per-position state transplant in the opposite composition (base states into instruct blocks) |
| 92d-B1h | (same claim) | Anonymous, 2026, ICLR 2027 submission (under review); contemporaneous by rule [21] | "Guided by this localization, layer interpolation restores entrance diversity and increases solution coverage by 37%, with pass@1 of 0.305 versus 0.278 for the late policy." | https://api2.openreview.net/notes/search?term=Locked%20at%20the%20Entrance%2C%20Open%20Inside%3A%20Where%20RLVR%20Narrows%20the%20Solution%20Space&group=ICLR.cc/2027/Conference&limit=10; Abstract (OpenReview API record); VERIFIED-ABSTRACT | 2026-10-21 | adjacent | Hidden-state transplant (not weights) on code |
| 92d-B1i | (same claim) | Wang et al., 2025, ICML 2026 [28] | "We propose Base-Aligned Model Collaboration (BACo), an inference-time token-level model collaboration framework that dynamically combines a base LLM with its aligned counterpart to optimize diversity and quality." | https://arxiv.org/html/2511.05650v2; Abstract; v2 | 2026-10-21 | occupies (goal, token level) | Activation level instead of token routing |
| 92d-B2a | De-sharpening push: push the instruct model along the base-minus-instruct direction vs isotropic pushes at matched norm | Anand et al., 2026, arXiv preprint [22] | "a training-free method that estimates a post-training alignment signature from aligned-base residual contrasts and ablates the corresponding direction during decoding." | https://arxiv.org/html/2605.30526v2; Abstract (v2; v1 title 'Measuring, Localizing, and Ablating Alignment Signatures in LLMs'); v2 | 2026-10-21 | occupies (method) | replication of PASTA-style aligned-minus-base ablation in a new setting: algorithm choice in code, against matched-norm isotropic pushes |
| 92d-B2b | (same claim) | Anand et al., 2026, arXiv preprint [22] | "Each random ablation uses the same residual-stream hook footprint and decoding seed as PASTA." | https://arxiv.org/html/2605.30526v2; Sec. 5.1 (Specificity of PASTA's direction); v2 | 2026-10-21 | occupies (control) | Matched-norm isotropic directions rather than orthogonal unit directions |
| 92d-B2c | (same claim) | Anonymous, 2026, ICLR 2027 submission (under review); contemporaneous by rule [23] | "injecting it into the Base model improves reasoning accuracy by up to 50.9 percentage points, while suppressing it substantially degrades the post-trained model." | https://api2.openreview.net/notes/search?term=Training-Induced%20Reasoning%20Directions%3A%20Uncovering%20Reusable%20Structure%20in%20Post-Training%20Reasoning&group=ICLR.cc/2027/Conference&limit=10; Abstract (OpenReview API record); VERIFIED-ABSTRACT | 2026-10-21 | adjacent | Diversity outcome rather than accuracy |
| 92d-B2d | (same claim) | Minder et al., 2025, ICLR 2026 [24] | "analyzing activation differences on the first few tokens of random text and steering by adding this difference to the model activations produces text similar to the format and general content of the finetuning data." | https://arxiv.org/html/2510.13900v3; Abstract; v3 | 2026-10-21 | adjacent | Opposite sign (toward base) and a diversity outcome |
| 92d-B2e | (same claim) | Zheng et al., 2024, ACL 2025 [25] | "Given a partially-trained model and its initial SFT checkpoint, ExPO improves the implicit optimization objective of alignment training by simply amplifying the parameter change based on a first-order approximation" | https://arxiv.org/html/2404.16792v5; Abstract; v5 | 2026-10-21 | adjacent (weight space) | Activation-space push; weight-space extrapolation is a reviewer baseline |
| 92d-B2f | (same claim) | Nakamura, 2026, arXiv preprint [50] | "The aligned model is evaluated under a chat template the base model never saw, so the naive difference conflates the alignment shift with chat formatting." | https://arxiv.org/html/2605.24583v3; Abstract; v3 | 2026-10-21 | supports (method caution) | Direction estimated with base and instruct under the same chat template |
| 92d-Ca | Knobs head-on: activation plan noise vs text-level plan samplers, base-aligned collaboration (base writes the intent, instruct writes the code) and departure-matched decoding | Wang et al., 2025, ICML 2026 [28] | "evaluate them across three open-ended generation tasks with 13 diversity and quality metrics. BACo consistently surpasses state-of-the-art inference-time baselines. With our best router, BACo achieves a 21.3% joint improvement in diversity and quality" | https://arxiv.org/html/2511.05650v2; Abstract; v2 | 2026-10-21 | occupies (collaboration lane) | Base-intent arm = sentence-granularity instance of base-aligned collaboration; the addition is pricing it against activation noise on test-checked algorithms |
| 92d-Cb | (same claim) | Peeperkorn et al., 2025, arXiv preprint [29] | "The results indicate that DPO has the most substantial impact on diversity. Motivated by these findings, we present a new decoding strategy, conformative decoding, which guides an instruct model using its more diverse base model to reintroduce output diversity." | https://arxiv.org/html/2507.20956v1; Abstract; v1 | 2026-10-21 | occupies (collaboration lane) | Code, algorithm-level outcome |
| 92d-Cc | (same claim) | Feng et al., 2025, arXiv preprint [30] | "we propose Switch Generation, where pretrained and aligned model versions take turns to “speak” in a response sequence." | https://arxiv.org/html/2510.09913v1; Abstract; v1 | 2026-10-21 | occupies (collaboration lane) | Code, algorithm-level outcome |
| 92d-Cd | (same claim) | Zhang et al., 2026, arXiv preprint [45] | "Sparse replacement also retains much of the base model’s diversity while staying close to the RL model at pass@1." | https://arxiv.org/html/2610.24663v1; Abstract; v1 | 2026-10-21 | adjacent | Code; activation-noise comparison |
| 92d-Ce | (same claim) | Sumita et al., 2026, arXiv preprint [20] | "They also demonstrated a better diversity–quality trade-off than temperature sampling in most settings." | https://arxiv.org/html/2610.22999v1; Abstract; v1 | 2026-10-21 | adjacent | Code; text-level plan samplers in the contrast set |
| 92d-Cf | (same claim) | Dang et al., 2025, COLM 2025 [42] | "Finally, we find that WiSE-FT provides complementary performance gains that cannot be achieved only through diversity-inducing decoding strategies, like temperature scaling." | https://arxiv.org/html/2504.10478v4; Abstract; v4 | 2026-10-21 | baseline-to-add | Weight interpolation as a contrast arm |
| 92d-Cg | (cross-ref 92c) | Intent Factored Generation: Unleashing the Diversity in Your Language  [31] | see Table 92c row C1b, C1-seedb (not re-verified) | https://arxiv.org/html/2506.09659v1 | 2026-10-21 (iteration 4) | inherited | intent-hot/response-cold text plan sampler (92c C1b) |
| 92d-Ch | (cross-ref 92c) | Planning In Natural Language Improves LLM Search For Code Generation [32] | see Table 92c row C1c (not re-verified) | https://arxiv.org/html/2409.03733v2 | 2026-10-21 (iteration 4) | inherited | natural-language plan search (92c C1c) |
| 92d-Ci | (cross-ref 92c) | Where You Inject Diversity Matters: A Unified Framework for Diverse Ge [55] | see Table 92c row C1-siteb/c (not re-verified) | https://arxiv.org/html/2606.10302v1 | 2026-10-21 (iteration 4) | inherited | Level-2 per-output specifications (92c C1-siteb/c) |
| 92d-Cj | (cross-ref 92c) | Gacha Decoding: Eliciting Diverse Generations Through Instruction Foll [56] | see Table 92c row C1j (not re-verified) | https://arxiv.org/html/2610.01382v1 | 2026-10-21 (iteration 4) | inherited | instruction-following diversity (92c C1j) |
| 92d-Ck | (cross-ref 92c) | Rethinking Activation Steering for Mathematical Reasoning: What Actual [33] | see Table 92c row C1g, C3cd (not re-verified) | https://api2.openreview.net/notes/search?term=Rethinking%20Activation%20Steering | 2026-10-21 (iteration 4) | inherited | decoding matched to steering's departure from greedy (92c C1g) |
| 92d-Cl | (cross-ref 92c) | Perturb the Thought, Not the Pixels: Latent-Space Rollout Diversificat [57] | see Table 92c row C1-sitef (not re-verified) | https://arxiv.org/html/2608.21595v1 | 2026-10-21 (iteration 4) | inherited | latent rollout perturbation in RL (92c C1-sitef) |
| 92d-Ea | Second family: gemma-3-4b pt vs it | Kissane et al., n.d., grey literature (blog/research update) [34] | "We find that the difference in weights between Gemma v1 2B base vs chat is unusually large compared to other fine-tuned models, explaining this phenomenon." | https://www.alignmentforum.org/posts/fmwk6qxrpW8d4jvbd/saes-usually-transfer-between-base-and-chat-models; Sec. 1 (introduction of results); VERIFIED-BLOG | 2026-10-21 | context (caution) | Report base/instruct activation-space similarity for gemma-3-4b before transplanting; Gemma base/chat pairs can diverge unusually |
| 92d-Eb | (same claim) | Zhang et al., 2026, arXiv preprint [19] | "Selective Layer Restoration (SLR), a training-free method that restores selected layers in a post-trained model to their pre-trained weights, yielding a hybrid model with the same architecture and parameter count, incurring no additional inference cost." | https://arxiv.org/html/2602.06665v1; Abstract; v1 | 2026-10-21 | adjacent | Gemma in a code setting; states not weights |
| 92d-Ec | (same claim) | Nakamura, 2026, arXiv preprint [50] | "The aligned model is evaluated under a chat template the base model never saw, so the naive difference conflates the alignment shift with chat formatting." | https://arxiv.org/html/2605.24583v3; Abstract; v3 | 2026-10-21 | supports (method caution) | Template-controlled contrasts on the second family |
| 92d-Ga | (cross-ref 92c C3c) | Mathematical discoveries from program search with large language model [35] | see Table 92c row C3ca (not re-verified) | https://www.nature.com/articles/s41586-023-06924-6 | 2026-10-21 (iteration 4) | inherited | novelty boundary unchanged; no new 2026 hit |

### 3.1 Further verified neighbours by lane (quoted in evidence/quotes_iter5.jsonl; not in the paste-ready table)

- **Lane 1, base vs aligned diversity and RLVR boundaries:**
  - Yang et al.'s v1 figure, kept for the version check: "nearly an order of magnitude (e.g., from 12 to 1.2) relative to base models" [58];
  - RLHF reduces output diversity relative to SFT [59];
  - base models beat aligned models at randomness and creativity, with an effective trade-off [60];
  - aligned models display less conceptual diversity [61];
  - larger post-trained models, but not larger base models, are less diverse [62];
  - lightly post-trained models are the most divergent in a 105-model census [63];
  - empirical support shrinkage outweighs expansion under RLVR [64];
  - post-training compresses variation in fiction across OLMo base/SFT/DPO/RLVR [65];
  - a diversity metric read from base-model log-probabilities [66];
  - execution-trajectory algorithm similarity (BehaveSim), a precedent for runtime-trace labels [67];
  - the definition of 'sharpening' [68];
  - power sampling from the base model avoids RL's diversity collapse [69].
- **Lane 1/5, predicting post-training from the base model (FLAG B adjacency):**
  - per-head signed forecasts from the base model alone [70];
  - data mean representations injected into a base model to predict unintended behaviours [71];
  - projection differences from base generations predict trait shifts [72];
  - forgetting predicted by the KL divergence from the base policy [73].
- **Lane 2, base-aligned collaboration:**
  - Nudging (alignment changes a small subset of stylistic tokens on which base models are uncertain) [74];
  - model arithmetic [75];
  - CreativeInstruct (two-model methods need released base models) [76];
  - ReDiPO (the base model recovers answer modes that post-training removed) [77];
  - a per-prompt diversity router [78];
  - word transplants at disagreement positions [79];
  - a prefix-transplant ledger [80];
  - logit grafting [81];
  - early planning-related decision tokens carry the base-reasoning gap [82].
- **Lane 3, base-to-tuned activation transfer:**
  - a base-model direction induces backtracking in the distilled model [83];
  - base mechanisms orchestrated by thinking-model heuristics [84];
  - instruct-to-base steering transfer [85];
  - instruction tuning changes later-layer activations only on targeted inputs [86];
  - KV-cache fusion between models [87];
  - cross-model patching for inspection [88];
  - module transplants between base and instruct [89];
  - weight patching [90];
  - base activations predicting long-CoT activations [91];
  - cross-family representation steering of base models [92];
  - hidden-state optimisation that elicits CoT in base models [93];
  - activation-patching practice [94, 95];
  - shallow alignment concentrated on the first output tokens [96].
- **Lane 5, model diffing:**
  - crosscoder L1 artefacts and the BatchTopK fix [97, 98];
  - SAEs transfer between base and chat models [34].

## 4. Saturation search (dated 2026-10-21)

### 4.1 Per-claim saturation verdict

- **A0 / FLAG C:** partly fired. Lee et al. (2025) is the only base-vs-instruct algorithm-level code comparison, and its direction is mixed; no 2026 paper repeats it with execution-based labels (searched F1, F9, FC(Lee), BC(Lee, Le Bronnec)).
- **A1 / A2 / FLAG B:** partly fired (A1, training time); A2 is adjacent-only. 2026 adds Duan, Lookahead, How-Much-Not-Where, Same Candidates and Predictive MI, all training-time, retrospective or head-level.
- **B1 / FLAG A:** not fired. 2026 adds cross-patching (method; 2.5), SLR, FrankenMerging, Locked-at-the-Entrance and ReDiverse (2.0 each).
- **B2/D:** PASTA (2.5) occupies the method and its random-direction control; the outcome differs.
- **C:** base-aligned collaboration is occupied (BACo, Switch Generation, conformative decoding, rl-replace, token-ledger, Not-Which-Path).

### 4.2 Counts per query family (PRISMA-style)

| Family | Identified (raw) | Unique records | In window | Keyword pre-screen (>=2 groups) | Scored | Adjacent or occupying | Occupying |
|---|---|---|---|---|---|---|---|
| BC | 190 | 169 | 18 | 15 | 4 | 4 | 1 |
| F1 | 490 | 457 | 397 | 368 | 12 | 10 | 1 |
| F2 | 412 | 370 | 306 | 277 | 15 | 13 | 4 |
| F3 | 491 | 446 | 314 | 300 | 7 | 6 | 1 |
| F4 | 523 | 469 | 363 | 341 | 7 | 7 | 0 |
| F5 | 420 | 377 | 281 | 251 | 6 | 6 | 0 |
| F6 | 368 | 337 | 288 | 254 | 8 | 6 | 2 |
| F7 | 257 | 222 | 174 | 164 | 5 | 5 | 1 |
| F8 | 214 | 212 | 165 | 139 | 1 | 1 | 0 |
| F9 | 254 | 242 | 179 | 170 | 1 | 1 | 0 |
| FC | 274 | 253 | 199 | 176 | 17 | 14 | 2 |
| R2 | 611 | 575 | 482 | 403 | 15 | 15 | 3 |

Families F1-F9 are round 1, R2 is round 2, FC is forward citations (rounds 1 and 3) and BC is backward references (round 3). A record can belong to several families. 'Scored' counts hits whose records carry that family tag. Out-of-window anchors are scored for context but excluded from the saturation verdicts.

### 4.3 Search-log summary (calls and hits per family x engine; full log in evidence/search_log_iter5.jsonl)

| Family | Engine | Calls | Hits | Status counts |
|---|---|---|---|---|
| BC | S2 | 6 | 190 | {'ok': 6} |
| F1 | E1 | 3 | 75 | {'ok': 3} |
| F1 | E3 | 3 | 150 | {'ok': 3} |
| F1 | E4 | 3 | 115 | {'ok': 3} |
| F1 | E5 | 3 | 150 | {'ok': 3} |
| F2 | E1 | 3 | 75 | {'ok': 3} |
| F2 | E3 | 3 | 56 | {'ok': 3} |
| F2 | E4 | 3 | 131 | {'ok': 3} |
| F2 | E5 | 3 | 150 | {'ok': 3} |
| F3 | E1 | 3 | 75 | {'ok': 3} |
| F3 | E3 | 3 | 116 | {'ok': 3} |
| F3 | E4 | 3 | 150 | {'ok': 3} |
| F3 | E5 | 3 | 150 | {'ok': 3} |
| F4 | E1 | 4 | 100 | {'ok': 4} |
| F4 | E3 | 4 | 36 | {'ok': 4} |
| F4 | E4 | 4 | 155 | {'ok': 4} |
| F4 | E5 | 4 | 200 | {'ok': 4} |
| F4 | E6 | 4 | 32 | {'ok': 4} |
| F5 | E1 | 3 | 75 | {'ok': 3} |
| F5 | E3 | 3 | 102 | {'ok': 3} |
| F5 | E4 | 3 | 67 | {'ok': 3} |
| F5 | E5 | 3 | 150 | {'ok': 3} |
| F5 | E6 | 3 | 26 | {'ok': 3} |
| F6 | E1 | 3 | 75 | {'ok': 3} |
| F6 | E3 | 3 | 33 | {'ok': 3} |
| F6 | E4 | 4 | 110 | {'ok': 3, 'rate-limited': 1} |
| F6 | E5 | 3 | 150 | {'ok': 3} |
| F7 | E1 | 2 | 50 | {'ok': 2} |
| F7 | E3 | 2 | 33 | {'ok': 2} |
| F7 | E4 | 2 | 56 | {'ok': 2} |
| F7 | E5 | 3 | 100 | {'ok': 2, 'HTTP': 1} |
| F7 | E6 | 2 | 18 | {'ok': 2} |
| F8 | E1 | 2 | 50 | {'ok': 2} |
| F8 | E3 | 2 | 19 | {'ok': 2} |
| F8 | E4 | 2 | 45 | {'ok': 2} |
| F8 | E5 | 4 | 100 | {'HTTP': 2, 'ok': 2} |
| F9 | E1 | 2 | 50 | {'ok': 2} |
| F9 | E3 | 2 | 66 | {'ok': 2} |
| F9 | E4 | 2 | 38 | {'ok': 2} |
| F9 | E5 | 4 | 100 | {'HTTP': 2, 'ok': 2} |
| FC | OpenAlex | 4 | 0 | {'ok': 4} |
| FC | S2 | 17 | 274 | {'rate-limited': 3, 'ok': 13, 'HTTP': 1} |
| R2 | E1 | 6 | 150 | {'ok': 6} |
| R2 | E3 | 6 | 104 | {'ok': 6} |
| R2 | E4 | 6 | 57 | {'ok': 6} |
| R2 | E5 | 6 | 300 | {'ok': 6} |
| lookup | Claude | 3 | 4 | {'ok': 3} |

### 4.4 Scored hits (O = outcome, I = intervention/predictor, C = contrast/forecast; claim-specific definitions in evidence/protocol.json)

| ID | Title | v1 | Venue | 4-mo tag | ICLR-2027 rule | Claim | O / I / C | Total | Verdict | Full text? | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2503.00691 | How Diversely Can Language Models Solve Problems? Exploring the Algori | 2025-03-02 | Findings of EMNLP 2025 | no | not contemporaneous (published before 2026-07-17) | A0 | 1 / 1 / 0.5 | 2.5 | occupies | yes | DeepSeek-Coder-6.7B Base vs Instruct, test-checked correctness, LLM-judge (Llama-3.1-8B-Instruct) algorithm clusters; instruction tuning lowers algorithmic diversity on AtCoder-introductory, raises it elsewhere. FLAG C PARTLY FIRE |
| 2607.20543 | When RLVR Shrinks the Reasoning Boundary: Diagnosing Pass@k Inversion | 2026-07-12 | arXiv preprint | yes | exempt (arXiv-only) | A1 | 1 / 1 / 0.5 | 2.5 | occupies | yes | Per-prompt regimes from frozen base-model behaviour predict where GRPO loses coverage (boundary prompts); PBA anchors risky prompts to the base. Training-time, correctness coverage (math) -> FLAG B PARTLY FIRED by the frozen rule. |
| 2610.04978 | What Will Post-Training Fix? Per-Problem Gains Are Shared Across Indep | 2026-10-04 | arXiv preprint | yes | exempt (arXiv-only) | A1 | 1 / 1 / 0.5 | 2.5 | occupies | yes | Per-problem post-training gains: a-priori base signals (pass rate, likelihood of a correct solution) explain only 0.30/0.24 of explainable variance; another checkpoint predicts better. Training-time, correctness (math). Contradict |
| 2510.02230 | The Reasoning Boundary Paradox: How Reinforcement Learning Constrains  | 2025-10-02 | NeurIPS 2026 (poster) | no | peer-reviewed 2026: check publication date vs 2026-07-17 | A1 | 1 / 1 / 0.5 | 2.5 | occupies | yes | Winner-take-all: RLVR reinforces problems with high base likelihood and suppresses low-likelihood ones. Anchor outside window. |
| 2605.07284 | Same Targets, Different Computation: How Post-Training Divides Work Ac | 2026-05-08 | arXiv preprint | no | exempt (arXiv-only) | B1 | 0.5 / 1 / 1 | 2.5 | occupies | yes | Cross-patching: base upstream hidden state written into the descendant's late stack at every sequence position (keys/values recomputed); boundary sweep 40% depth to final block, random-later-disagreement and history controls. Outc |
| 2605.30526 | Measuring, Localizing, and Ablating Alignment Signatures in LLMs | 2026-05-28 | arXiv preprint | no | exempt (arXiv-only) | B2_D | 0.5 / 1 / 1 | 2.5 | occupies | yes | PASTA: aligned-minus-base residual direction ablated during aligned-model decoding; five orthogonal unit random directions with the same hook footprint as control; outcome AI-detector visibility; 'greater stylistic variation' only |
| 2605.28022 | Beyond pass@k: Redundancy-Aware RLVR for Multi-Sample Code Generation | 2026-05-27 | arXiv preprint (under review) | no | exempt (arXiv-only) | A0 | 0.5 / 1 / 0.5 | 2.0 | adjacent | yes | Base vs RLVR descendants (Qwen3-4B/8B, Olmo3-7B) on MBPP/CodeContests/TACO: JPlag diversity decreases in 57.2% and Vendi in 65.3% of 2,745 prompt-level comparisons; structural, not algorithm-level. |
| or:6a4v7CpeAu | Catching RLHF Failures before Training | 2026 (ICLR 2027 submission) | ICLR 2027 submission | yes | contemporaneous (ICLR 2027 submission) | A1 | 1 / 0.5 / 0.5 | 2.0 | adjacent | abstract | Lookahead: base model + reward model predicts which IFEval prompts degrade after RLHF training (F1- margin over BoN). Training-time per-prompt forecast; FLAG B PARTLY FIRED. |
| or:uASUNrduuj | How Much, Not Where: RLVR's Capability Loss Is Dose-Controlled and Dee | 2026 (ICLR 2027 submission) | ICLR 2027 submission | yes | contemporaneous (ICLR 2027 submission) | A1 | 1 / 0.5 / 0.5 | 2.0 | adjacent | abstract | Per-prompt decay rate of likelihood of frozen base-correct trajectories (MATH, MBPP) predicts RLVR damage; random-prompt anchoring protects as well (contradicts targeting). |
| 2606.29933 | Towards Physical Intuitions for Alignment Dynamics: A Case Study With  | 2026-06-29 | arXiv preprint | yes | exempt (arXiv-only) | A2 | 0.5 / 1 / 0.5 | 2.0 | adjacent | yes | SFT 'nucleation' collapses onto a seed distribution present in the pretrained LLM; RL keeps the same options (random-generation tasks). Stylised support for A2. |
| or:iIw2d3AkJM | Base Models Can Reason by Taking a Cue from Their Training Data | 2026 (ICLR 2027 submission) | ICLR 2027 submission | yes | contemporaneous (ICLR 2027 submission) | A2 | 0.5 / 1 / 0.5 | 2.0 | adjacent | abstract | Base-model starting token cues recover much of the RL gain (math and coding); RL makes the same cues more likely. |
| 2602.06665 | Not All Layers Need Tuning: Selective Layer Restoration Recovers Diver | 2026-02-06 | arXiv preprint | no | exempt (arXiv-only) | B1 | 1 / 0.5 / 0.5 | 2.0 | adjacent | yes | Selective Layer Restoration: restores a chosen interval of layers of the post-trained model to pre-trained weights; recovers diversity (creative writing, open QA, reasoning; Llama/Qwen/Gemma). Weight-level, no code, no matched-ran |
| 2610.22999 | Controlling the Diversity-Quality Trade-Off of LLMs by Merging Models  | 2026-10-16 | arXiv preprint | yes | exempt (arXiv-only) | B1 | 1 / 0.5 / 0.5 | 2.0 | adjacent | yes | Depth-aware FrankenMerging: aligned lower layers + base higher layers; higher semantic diversity than aligned; better trade-off than temperature. Weight/layer splice (reverse composition of B1); text tasks only. |
| or:hu5mtofNd4 | Locked at the Entrance, Open Inside: Where RLVR Narrows the Solution S | 2026 (ICLR 2027 submission) | ICLR 2027 submission | yes | contemporaneous (ICLR 2027 submission) | B1 | 1 / 0.5 / 0.5 | 2.0 | adjacent | abstract | Locked at the Entrance: RLVR contraction concentrated at the entrance (first operand/operator family) on Countdown; entrance prefix restores low-access families; layer interpolation restores entrance diversity (+37% coverage). Wei |
| or:lZQK4G4Ktp | RESTORING DIVERSITY IN DISTILLED IMAGE AND VIDEO GENERATORS BY PROBING | 2026 (ICLR 2027 submission) | ICLR 2027 submission | yes | contemporaneous (ICLR 2027 submission) | B1 | 1 / 0.5 / 0.5 | 2.0 | adjacent | abstract | ReDiverse (diffusion distillation): diversity collapse localized to an intermediate block at the first denoising step; training-free steering along teacher principal directions restores diversity. Cross-domain analogue (images/vid |
| 2610.24663 | What RL Brings to Reasoning: A Few Decisions the Base Model Would Not  | 2026-10-17 | arXiv preprint | yes | exempt (arXiv-only) | C | 0.5 / 1 / 0.5 | 2.0 | adjacent | yes | rl-replace: borrow RL model's token only where greedy choices differ (~4%); keeps much of base diversity (pass@256 67.5% vs RL 61.4%). Token-level base/RL collaboration on math, not code. |
| 2603.24124 | The Alignment Tax: Response Homogenization in Aligned LLMs and Its Imp | 2026-03-25 | arXiv preprint | no | exempt (arXiv-only) | A0 | 0.5 / 1 / 0 | 1.5 | adjacent | yes | Base-vs-instruct single-cluster rate 1.0% vs 28.5% (Qwen3-14B, TruthfulQA); stage ablation points to DPO. Text QA, not code. |
| or:BEcwcRFQdu | Predictive Mechanistic Interpretability of Post-Training: A Priori For | 2026 (ICLR 2027 submission) | ICLR 2027 submission | yes | contemporaneous (ICLR 2027 submission) | A1 | 0 / 1 / 0.5 | 1.5 | adjacent | abstract | Per-head signed forecast of post-training changes from the base model alone (GPT-2 ... 1.5B). |
| 2602.04735 | From Data to Behavior: Predicting Unintended Model Behaviors Before Tr | 2026-02-04 | arXiv preprint | no | exempt (arXiv-only) | A1 | 0.5 / 0.5 / 0.5 | 1.5 | adjacent | yes | Data2Behavior/MDF: mean data representations injected into a base model's forward pass to predict unintended post-training behaviours. |
| 2603.06957 | Post-Training with Policy Gradients: Optimality and the Base Model Bar | 2026-03-07 | ICML 2026 | no | peer-reviewed 2026: check publication date vs 2026-07-17 | A1 | 0 / 1 / 0.5 | 1.5 | adjacent | yes | Theory: post-training error governed by the base model's Likelihood Quantile; barrier to leaving base support. |
| 2507.21509 | Persona Vectors: Monitoring and Controlling Character Traits in Langua | 2025-07-29 | arXiv preprint | no | exempt (arXiv-only) | A1 | 0.5 / 0.5 / 0.5 | 1.5 | adjacent | yes | Persona vectors: projection difference between training data and base generations predicts post-finetuning trait expression. |
| or:ooV5M72O08 | Same Candidates, Stronger Reasoning: Rethinking What Post-Training Lea | 2026 (ICLR 2027 submission) | ICLR 2027 submission | yes | contemporaneous (ICLR 2027 submission) | A2 | 0 / 1 / 0.5 | 1.5 | adjacent | abstract | 92.9% of post-training top-1 changes stay within the pretrained top-16 at consequential decisions; preferences reorganized. Token-level, retrospective. |
| 2510.01171 | Verbalized Sampling: How to Mitigate Mode Collapse and Unlock LLM Dive | 2025-10-01 | arXiv preprint | no | exempt (arXiv-only) | A2 | 0 / 1 / 0.5 | 1.5 | adjacent | yes | Stylised: aligned optimum is a power transform of pi_ref that amplifies its modes (typicality bias); no per-task test. FLAG B PARTLY FIRED (stylised). |
| 2312.01552 | The Unlocking Spell on Base LLMs: Rethinking Alignment via In-Context  | 2023-12-04 | arXiv preprint | no | exempt (arXiv-only) | A2 | 0 / 1 / 0.5 | 1.5 | adjacent | yes | Aligned top-ranked tokens mostly within base top-5; shift concentrated on stylistic tokens and earlier positions. |
| 2504.07912 | Echo Chamber: RL Post-training Amplifies Behaviors Learned in Pretrain | 2025-04-10 | COLM 2025 | no | not contemporaneous (published before 2026-07-17) | A2 | 0.5 / 0.5 / 0.5 | 1.5 | adjacent | yes | RL converges to a dominant output distribution amplifying pretraining patterns (models trained from scratch). Anchor. |
| 2605.24583 | Measuring Alignment-Induced Activation Shifts Correctly: A Template-Co | 2026-05-23 | arXiv preprint | no | exempt (arXiv-only) | B2_D | 0 / 0.5 / 1 | 1.5 | adjacent | yes | Template-controlled difference-in-differences for aligned-minus-base activation shifts: naive contrast confounded by the chat template the base never saw. |
| or:3QlKFFBcNO | Not Which Path, but What Happens Before You Would Stop: What Reasoning | 2026 (ICLR 2027 submission) | ICLR 2027 submission | yes | contemporaneous (ICLR 2027 submission) | C | 0 / 1 / 0.5 | 1.5 | adjacent | abstract | Word transplant at disagreement positions between base and reasoning model; random-position control. Accuracy outcome. |
| or:cMasrdysrX | Where Does RLVR Act? A Conserved Token Ledger for What Post-Training A | 2026 (ICLR 2027 submission) | ICLR 2027 submission | yes | contemporaneous (ICLR 2027 submission) | C | 0 / 1 / 0.5 | 1.5 | adjacent | abstract | Prefix transplantation (trained policy writes k tokens, base the rest) as a conserved ledger of RLVR gain; early credit mostly format. |
| 2604.02319 | No Single Best Model for Diversity: Learning a Router for Sample Diver | 2026-04-02 | COLM 2026 | no | peer-reviewed 2026: check publication date vs 2026-07-17 | C | 0.5 / 0.5 / 0.5 | 1.5 | adjacent | yes | Per-prompt router picks the model that gives the most diverse answer set (18 LLMs). |
| 2608.07460 | CreativeInstruct: Scalably Teaching LLMs to Balance Quality, Creativit | 2026-08-07 | arXiv preprint | yes | exempt (arXiv-only) | C | 0.5 / 0.5 / 0.5 | 1.5 | adjacent | yes | CreativeInstruct distils BACo-style base/aligned routing into one model; notes two-model methods need released base models. |
| 2610.19157 | DivAlgo: A systematic evaluation of algorithmic diversity for code gen | 2026-10-13 | arXiv preprint | yes | exempt (arXiv-only) | A0 | 1 / 0 / 0 | 1 | adjacent | yes | DivAlgo: 24 code models, no base-vs-instruct pairing (grep: 'base model' only for the metric's base classifier). |
| 2407.02209 | Generative Monoculture in Large Language Models | 2024-07-02 | ICLR 2025 | no | not contemporaneous (published before 2026-07-17) | A0 | 0.5 / 0.5 / 0 | 1.0 | adjacent | yes | Monoculture: pre-trained vs aligned Llama-2 compared on book reviews only; code experiments on GPT-3.5/GPT-4 (open code models failed to produce code). |
| 2607.12796 | The One-Word Census: Answer-Choice Conformity Across 105 Language Mode | 2026-07-14 | arXiv preprint | yes | exempt (arXiv-only) | A0 | 0.5 / 0.5 / 0 | 1.0 | adjacent | yes | 105-model one-word census: lightly post-trained models most divergent, heavily post-trained most conformist; base->SFT ladder moves most. |
| 2606.01811 | "I've Seen How This Goes": Characterizing Diversity via Progressive Co | 2026-06-01 | ICML 2026 workshop (non-archival) | no | not contemporaneous (published before 2026-07-17) | A1 | 0 / 1 / 0 | 1 | adjacent | yes | Decan: diversity read from a base model's per-token log-probabilities; drops base->SFT->DPO->RLVR on OLMo-2-7B. |
| 2609.33085 | The Model Knows Another Way: Strategy Switching for Effective RLVR Exp |  | arXiv preprint | no | exempt (arXiv-only) | A1 | 0.5 / 0 / 0.5 | 1.0 | adjacent | abstract | Finite sampling concentrates on a dominant strategy while alternatives already supported by the model stay unexplored (RLVR exploration). |
| 2608.11426 | Is Convergence Inevitable? Tracing Output Homogeneity Back to Base Mod | 2026-08-11 | arXiv preprint | yes | exempt (arXiv-only) | A2 | 0 / 0.5 / 0.5 | 1.0 | adjacent | yes | Homogeneity learned in pretraining, revealed/amplified by SFT; base models collapse under prompting alone (open-ended text). |
| or:MYXgOex05m | Should SFT Prefer the Familiar? Diversity Collapse and Recovery via Mo | 2026 (ICLR 2027 submission) | ICLR 2027 submission | yes | contemporaneous (ICLR 2027 submission) | B1 | 1 / 0 / 0 | 1 | adjacent | abstract | Merging the SFT model with its pretrained base before RL restores diversity (math and code benchmarks). Whole-model weight merge; no site or random controls. |
| 2602.16189 | Beyond Learning: A Training-Free Alternative to Model Adaptation | 2026-02-18 | arXiv preprint | no | exempt (arXiv-only) | B1 | 0 / 0.5 / 0.5 | 1.0 | adjacent | yes | Model transplant of activation-selected modules (weights) between Gemma-2-2B and -IT (mostly IT->base); outcome math accuracy. |
| 2604.13694 | Weight Patching: Toward Source-Level Mechanistic Localization in LLMs | 2026-04-15 | arXiv preprint | no | exempt (arXiv-only) | B1 | 0 / 0.5 / 0.5 | 1.0 | adjacent | yes | Weight Patching (specialized -> base, fixed input) with a cross-model activation-patching companion; instruction following. |
| 2605.30021 | Recovering Diversity Without Losing Alignment: A DPO Recipe for Post-T | 2026-05-28 | arXiv preprint (under review) | no | exempt (arXiv-only) | B1 | 0.5 / 0.5 / 0 | 1.0 | adjacent | yes | ReDiPO: base-model responses recover answer modes removed by post-training (DPO training). |
| 2608.04893 | When Does Latent Communication Pay? A Causal Audit of Relayed KV Cache |  | arXiv preprint | no | exempt (arXiv-only) | B1 | 0 / 0 / 1 | 1 | adjacent | abstract | Causal audit of relayed KV caches with deranged, zeroed and moment-matched random cache controls (multi-agent). |
| or:vkIOGTVcJP | Training-Induced Reasoning Directions: Uncovering Reusable Structure i | 2026 (ICLR 2027 submission) | ICLR 2027 submission | yes | contemporaneous (ICLR 2027 submission) | B2_D | 0 / 1 / 0 | 1 | adjacent | abstract | TIRD: post-minus-base activation directions; suppression degrades post-trained model; injection improves base. Accuracy outcome; no isotropic control stated in abstract. |
| 2605.16874 | Reasoning Can Be Restored by Correcting a Few Decision Tokens | 2026-05-16 | ICML 2026 | no | peer-reviewed 2026: check publication date vs 2026-07-17 | C | 0 / 0.5 / 0.5 | 1.0 | adjacent | yes | Base-reasoning gap concentrated on few early planning-related decision tokens; correcting them restores reasoning. |
| 2603.02787 | Rethinking Code Similarity for Automated Algorithm Design with LLMs | 2026-03-03 | ICLR 2026 | no | peer-reviewed 2026: check publication date vs 2026-07-17 | A0 | 0.5 / 0 / 0 | 0.5 | irrelevant | yes | BehaveSim: execution-trajectory algorithm similarity (precedent for runtime-trace mechanism labels); no base/instruct comparison. |
| 2608.30319 | Beyond Token-Level Guidance: Inference-Time Alignment of Specialized L | 2026-08-31 | EMNLP 2026 | yes | peer-reviewed 2026: check publication date vs 2026-07-17 | B1 | 0 / 0.5 / 0 | 0.5 | irrelevant | yes | CREST: steers base-model hidden representations with safety directions from a guidance model of another family. |
| or:tzXBBz5tmq | Logit Grafting: The Post-Training Delta is Sparse, Portable, and Power | 2026 (ICLR 2027 submission) | ICLR 2027 submission | yes | contemporaneous (ICLR 2027 submission) | C | 0 / 0.5 / 0 | 0.5 | irrelevant | abstract | Logit grafting: post-training delta changes argmax at 4-13% of steps; transfer of logit deltas to other models. |
| 2609.33936 | How Strong Is the Evidence for the Artificial Hivemind? Reevaluating E | 2026-09-27 | arXiv preprint | yes | exempt (arXiv-only) | A0 | 0 / 0 / 0 | 0 | irrelevant | yes | Contradicting evidence: Artificial Hivemind homogeneity results overstated (one dominant vehicle plus heavy tail). |
| 2609.16454 | Fine-Tuning Fixes Mode Collapse and Over-Dispersion in LLMs | 2026-09-15 | arXiv preprint | yes | exempt (arXiv-only) | A0 | 0 / 0 / 0 | 0 | irrelevant | yes | Contradicting evidence: mode collapse or over-dispersion depends on model and dataset; SFT converges toward the target distribution. |
| 2605.30844 | Fine-Tuning Improves Information Conveyance in Language Models | 2026-05-29 | arXiv preprint | no | exempt (arXiv-only) | A0 | 0 / 0 / 0 | 0 | irrelevant | yes | Contradicting evidence: length-confounded diversity analyses; canopy entropy. |

## 5. Corrections and confirmations

- **version/title/number** — 2506.17871: Yang, Li & Holtzman: latest version is v4 (2026-09-12, comment 'V4: TMLR 2026 Accepted'), not v3. Title v1 'How Alignment Shrinks the Generative Horizon' -> v3/v4 'LLM Probability Concentration: How Alignment Shrinks the Generative Horizon'. Headline: v1 'reducing BF by nearly an order of magnitude (e.g., from 12 to 1.2) relative to base models' -> v3/v4 'by a factor of 2–5 overall, and up to an order of magnitude ... at the beginning positions'. The strategy text's 'about an order of magnitude' is the v1 figure.
- **version/title** — 2410.09300: Nudging: v1 title 'Nudging: Inference-time Alignment via Model Collaboration' -> v4 'Nudging: Inference-time Alignment of LLMs via Guided Decoding'. Venue ACL 2025 (main) confirmed: Anthology ID 2025.acl-long.623.
- **version/title** — 2605.30526: PASTA: v1 'Measuring, Localizing, and Ablating Alignment Signatures in LLMs' -> v2 (2026-10-20) 'Measuring, Localizing, and Reducing the AI-Like Writing Style of Post-Trained LLMs'.
- **version/title** — 2607.12796: One-Word Census: v4 (2026-10-09) comment 'Updated title, no other changes'; quoted at v4.
- **version** — 2507.14843: Invisible Leash is at v5 (2026-10-14); quoted at v5.
- **name** — 2406.05587: Author is Behnam Mohammadi (plan wrote 'Mohammedi'). arXiv HTML v1 is unavailable (HTTP 404); quoted from PDF v1.
- **venue** — 2606.01811: Decan metric paper is an ICML 2026 WORKSHOP paper (Workshop on Generative AI, Creativity, and Human-AI Co-Creation, non-archival), not ICML 2026 main track.
- **venue confirmed** — 2510.02230: Reasoning Boundary Paradox: NeurIPS 2026 poster page https://neurips.cc/virtual/2026/poster/150680 lists the title (arXiv v1 2025-10-02, no newer version).
- **venue confirmed** — 2511.05650: BACo: ICML 2026 (arXiv v2 comment).
- **venue confirmed** — 2510.13900: Activation Difference Lens: ICLR 2026 (arXiv v3 comment).
- **venue confirmed** — 2503.00691: Lee et al.: Findings of EMNLP 2025, Anthology ID 2025.findings-emnlp.10 (page re-fetched).
- **venue** — 2507.12638: Ward et al. is an ICML 2025 Workshop on Actionable Interpretability paper (workshop, not main track).
- **resolved id** — 2510.07364: Venhoff et al. 'Base Models Know How to Reason, Thinking Models Learn When' = arXiv 2510.07364 (v4), ICML 2026 spotlight (comment).
- **resolved id** — 2510.03215: Cache-to-Cache = arXiv 2510.03215 (v2), ICLR 2026 (comment).
- **resolved id / description** — 2511.19131: 2511.19131 = 'Eliciting Chain-of-Thought in Base LLMs via Gradient-Based Representation Optimization' (AAAI 2026). A pre-trained classifier is the LIKELIHOOD TERM of a hidden-state optimisation (with a prior keeping states near the original), not a classifier 'deciding when to intervene' as the plan described.
- **description** — 2504.10478: Dang et al. WiSE-FT interpolates the latest SFT checkpoint with an EARLY SFT checkpoint (w0), not the base model; venue COLM 2025 (journal_ref). A coding appendix exists (Qwen2.5-coder-0.5B, Magicoder-Evol-Instruct-110K).
- **number verified** — Hindsight Merging (PMLR v286 veselovsky25a): Verified on the PMLR page: 'achieving a consistent 20-50% increase in pass@10 relative to the instruction tuned model across a coding benchmark and series of models'. Interpolation is with a previous training checkpoint.
- **author** — 2607.20543: Single author Todd Zhou; no venue line. Not the same author as Yifan Zhou (2605.07284, cross-patching).
- **author** — 2605.09995: 'Annotations Mitigate Post-Training Mode Collapse': first author Jacob Mitchell Springer; ICML 2026 (comment).
- **venue unconfirmed** — 2310.06452 / 2412.01951 / 2312.01552 / 2310.12962 / 2311.14479: ICLR venue status given in the plan for Kirk et al., Huang et al., URIAL, EFT and model arithmetic is NOT confirmed here (no venue in arXiv comment/journal_ref; no venue page fetched). They are cited as arXiv preprints with 'venue per plan, unconfirmed'.
- **scope check** — 2407.02209: Generative Monoculture compares pre-trained vs aligned Llama-2 only on book reviews; its code experiments use GPT-3.5/GPT-4 because 'neither of the models were able to produce code solutions' (CodeLlama, StarCoder). No base-vs-chat code comparison.
- **scope check** — 2610.19157: DivAlgo's 24 models contain no base-vs-instruct pairing analysis; 'base model' occurs only for the metric's base classifier.
- **tool limitation** — OpenAlex cites:: OpenAlex records cited_by_count = 0 for BACo, Lee et al., Ward et al. and Zhou (T.) 2026, so 'works?filter=cites:' returned 0 citing works; the plan's expectation that OpenAlex closes the Google-Scholar gap does not hold. Forward citations rest on Semantic Scholar only.
- **tool limitation** — 2507.20956: Conformative decoding is not indexed in Semantic Scholar (arXiv lookup HTTP 404; title match not found): its forward citations could not be chased.
- **tool limitation** — ICLR 2027 submissions: OpenReview PDFs return HTTP 403 (openreview.net/pdf?id=...); every ICLR 2027 row is VERIFIED-ABSTRACT via the public notes/search API.
- **citation mismatch** — 2503.00691 (inherited 92c C1d): Iteration-4 quoted only Lee et al.'s abstract; the base-vs-instruct finding (Findings 5) was not in Table 92c. 92d-A0 now quotes it.
- **protocol amendment** — evidence/protocol.json: Amendment A1: hand-typed frozen_utc corrected to the file's write time 14:50:21Z (before the first search call at 14:51:23Z); sha256 before/after in evidence/protocol_amendments.jsonl.

## 6. Unverified references (no numbers are taken from these)

- The LessWrong 'rephrase circuit' post (instruct attention heads patched into the base model) named in the plan was **not found** by two dated searches; it is not cited.
- The normalized cross-model transfer gains for base-to-instruct steering vectors (2509.06608) appeared only in a search-engine summary; the paper's text was quoted only for its qualitative transfer sentence [99].
- ICLR 2027 submissions are quoted from abstracts only: Locked at the Entrance, Token Ledger, Not Which Path, Token Cues, Lookahead, How Much Not Where, Predictive MI, TIRD, Merge-before-RL, Logit Grafting, Judging RLVR, ReDiverse, Same Candidates. Their full-text numbers are not used.
- 2609.33085 (strategy switching) and 2608.04893 (KV-relay audit) were screened from abstracts in the Semantic Scholar records and are not quoted.
- Venue status for Kirk et al. (ICLR 2024), Huang et al. (ICLR 2025), URIAL, EFT and model arithmetic (ICLR 2024) is as stated in the plan and is not confirmed on a venue page here.

## 7. Confidence, contradicting evidence, and what would change the verdicts

- **High confidence:** FLAG C partly fired; B1's method occupied; B2/D's method occupied; base-aligned collaboration occupied. These rest on full-text quotes that were re-matched live.
- **Moderate confidence:** FLAG A not fired and FLAG B partly fired. Thirteen ICLR 2027 submissions are abstract-only, and an ICLR 2027 submission whose full text measures diversity after a base-state patch would flip FLAG A.
- **Contradicting evidence the paper must face:**
  - instruction tuning *increases* algorithmic diversity on harder problems [2];
  - base-model signals predict little of where post-training acts [8];
  - random-prompt anchoring protects as well as targeted anchoring [51];
  - reported homogeneity can be overstated [100], depends on model and dataset [101], or is confounded by length [102];
  - RLVR boundary verdicts move with temperature and scoring rule, and base-ahead cells concentrate in chat-template conditions [49].
- **What would change the verdicts:**
  - a paper measuring solution or algorithm diversity after writing base states into a tuned model (FLAG A fires);
  - a paper forecasting inference-time movability or push landings from the base distribution (FLAG B fires fully);
  - a base-vs-instruct comparison with execution-labelled algorithms on code (FLAG C fires fully).


## Sources

[1] [arXiv API (id_list metadata: versions, v1 dates, titles, comments, journal_ref)](https://export.arxiv.org/api/query) — Authoritative version numbers, v1 dates, titles and comment/journal_ref lines for every arXiv id quoted here (evidence/arxiv_meta.json, retrieved 2026-10-21).

[2] [How Diversely Can Language Models Solve Problems? Exploring the Algorithmic Diversity of Model-Generated Code](https://arxiv.org/html/2503.00691v2) (Seonghyeon Lee, Heejae Chon, Joonwon Jang, Dongha Lee, Hwanjo Yu; 2025) — Findings of EMNLP 2025. Quoted (VERIFIED, v2) for 92d-A0, 92d-A1, FLAG_C; relation: context, contradicts-in-part.

> When comparing the Deepseek-base and Deepseek-instruct models, algorithmic diversity shows different patterns: instruction tuning decreases algorithmic diversity in AtCoder-introductory problems, but increases it in other problems.

Locator: Sec. 4.2, Findings 5 (v2)

> This suggests that instruction tuning favors single, straightforward answers for simple problems while promoting the exploration of multiple approaches for complex problems.

Locator: Sec. 4.2, Findings 5 (v2)

> The generated solutions are executed with test cases to verify their functional correctness.

Locator: Sec. 4.1, settings (v2)

> we employ the Llama-3.1-8B-Instruct model (Llama, 2024) to assess algorithmic relevance between two implementations.

Locator: Sec. 4.1, settings for diversity metrics (v2)

[3] [Beyond pass@k: Redundancy-Aware RLVR for Multi-Sample Code Generation](https://arxiv.org/html/2605.28022v1) (Le Bronnec Florian, Alexandre Verine, Rio Yokota, Benjamin Negrevergne; 2026) — arXiv preprint (under review). Quoted (VERIFIED, v1) for 92d-A0, FLAG_C; relation: adjacent, context.

> We focus on a more specific notion: whether repeated-sampling RLVR produces near-duplicate implementations, and how this redundancy relates to finite-budget performance.

Locator: Sec. 2 (related work) (v1)

[4] [LLM Probability Concentration: How Alignment Shrinks the Generative Horizon](https://arxiv.org/html/2506.17871v4) (Chenghao Yang, Sida Li, Ari Holtzman; 2025) — TMLR 2026 (v4 comment). Quoted (VERIFIED, v4) for 92d-A0, 92d-A2, 92d-B1, corrections; relation: supports.

> alignment tuning substantially sharpens the model’s output distribution from the outset, reducing BF by a factor of 2–5 overall, and up to an order of magnitude (e.g., from 12 to 1.2) at the beginning positions.

Locator: Abstract (v4) (v4)

> We hypothesize that alignment tuning does not fundamentally change a model’s behavior, but instead steers it toward stylistic tokens (e.g., “Sure”) that unlock low-entropy trajectories already present in the base model.

Locator: Abstract (v4) (v4)

[5] [The Alignment Tax: Response Homogenization in Aligned LLMs and Its Implications for Uncertainty Estimation](https://arxiv.org/html/2603.24124v2) (Mingyi Liu; 2026) — arXiv preprint. Quoted (VERIFIED, v2) for 92d-A0; relation: context, supports.

> A base-vs-instruct ablation on Qwen3-14B confirms the causal role of alignment: the base model shows 1.0% single-cluster rate vs. 28.5% for the instruct model

Locator: Abstract (v2)

> localizes the cause to DPO, not SFT.

Locator: Abstract (v2)

[6] [Is Convergence Inevitable? Tracing Output Homogeneity Back to Base Models](https://arxiv.org/html/2608.11426v2) (Alexandrine Fortier, Hazel Chen, Peter West; 2026) — arXiv preprint. Quoted (VERIFIED, v2) for 92d-A0, 92d-A2; relation: supports.

> We find that convergence can be revealed and amplified, but not introduced by the SFT data, supporting its role as a catalyst rather than a cause.

Locator: Abstract (v2)

> We find that instruct-like collapse can be induced through prompting alone, even without alignment.

Locator: Abstract (v2)

> We argue that output homogeneity is likely learned during the pretraining phase, and only

Locator: literal span of verified quote; Abstract (v2)

[7] [When RLVR Shrinks the Reasoning Boundary: Diagnosing Pass@k Inversion](https://arxiv.org/html/2607.20543v1) (Todd Zhou; 2026) — arXiv preprint. Quoted (VERIFIED, v1) for 92d-A1, FLAG_B; relation: partly-fires.

> Per-Problem Base Anchoring (PBA) is a deliberately simple proof-of-concept: sharpen prompts with sufficient frozen-base correct evidence, and anchor risky prompts to the base distribution.

Locator: Abstract (v1)

> decompose prompts by frozen base-model behavior into solved-easy, reachable, boundary, and out-of-reach regimes, turning an aggregate pass@k curve into an attribution problem.

Locator: Sec. 1, contributions (v1)

> where the base model contains rare correct trajectories that are recoverable by sampling but too sparse to reliably appear in finite RLVR rollout groups.

Locator: literal span of verified quote; Abstract (v1)

[8] [What Will Post-Training Fix? Per-Problem Gains Are Shared Across Independent RL Runs, and Existing Checkpoints Predict Them Better Than A Priori Signals](https://arxiv.org/html/2610.04978v1) (Xiaoxian Duan; 2026) — arXiv preprint. Quoted (VERIFIED, v1) for 92d-A1, FLAG_B; relation: contradicts-in-part, supports.

> The missing part lives in the base model’s behaviour on a problem, not in what the problem looks like.

Locator: Sec. 1, contributions (v1)

[9] [Catching RLHF Failures before Training](https://api2.openreview.net/notes/search?term=Catching%20RLHF%20Failures%20before%20Training&group=ICLR.cc/2027/Conference&limit=10) (2026) — ICLR 2027 submission (under review); contemporaneous by rule. Quoted (VERIFIED-ABSTRACT, ICLR 2027 submission record) for 92d-A1, FLAG_B; relation: partly-fires.

> Lookahead outperforms BoN at predicting which IFEval prompts degrade after training

Locator: Abstract (OpenReview API record) (ICLR 2027 submission record)

[10] [The Reasoning Boundary Paradox: How Reinforcement Learning Constrains Language Models](https://arxiv.org/html/2510.02230v1) (Phuc Minh Nguyen, Chinh D. La, Duy M. H. Nguyen, Nitesh V. Chawla, Binh T. Nguyen, Khoa D. Doan; 2025) — NeurIPS 2026 (poster). Quoted (VERIFIED, v1) for 92d-A1, FLAG_B; relation: adjacent.

> RLVR disproportionately reinforces problems with high likelihood, correct solutions under the base model while suppressing other initially low-likelihood ones.

Locator: Abstract (v1)

[11] [Verbalized Sampling: How to Mitigate Mode Collapse and Unlock LLM Diversity](https://arxiv.org/html/2510.01171v4) (Jiayi Zhang, Simon Yu, Derek Chong, Anthony Sicilia, Michael R. Tomz, Christopher D. Manning, Weiyan Shi; 2025) — arXiv preprint. Quoted (VERIFIED, v4) for 92d-A2, FLAG_B; relation: context, partly-fires.

> sharpens the reference distribution, amplifying its modes while suppressing the tails. The effect strengthens as typicality bias

Locator: App. D.3 (Power-Transform Sharpening under Typicality Bias) (v4)

> we identify a fundamental, pervasive data-level driver:

Locator: literal span of verified quote; Abstract (v4)

[12] [The Unlocking Spell on Base LLMs: Rethinking Alignment via In-Context Learning](https://arxiv.org/html/2312.01552v1) (Bill Yuchen Lin, Abhilasha Ravichander, Ximing Lu, Nouha Dziri, Melanie Sclar, Khyathi Chandu, Chandra Bhagavatula, Yejin Choi; 2023) — arXiv preprint (ICLR 2024 per plan; not confirmed here). Quoted (VERIFIED, v1) for 92d-A2; relation: context, supports.

> the top-ranked tokens in aligned LLMs are mostly found within the top five tokens ranked by base LLMs, and the distribution shift is more pronounced in earlier token positions.

Locator: Sec. 1 (Introduction) (v1)

> Most distribution shifts occur with stylistic tokens (e.g., discourse markers, safety disclaimers).

Locator: Abstract (v1)

[13] [Same Candidates, Stronger Reasoning: Rethinking What Post-Training Learns](https://api2.openreview.net/notes/search?term=Same%20Candidates%2C%20Stronger%20Reasoning%3A%20Rethinking%20What%20Post-Training%20Learns&group=ICLR.cc/2027/Conference&limit=10) (2026) — ICLR 2027 submission (under review); contemporaneous by rule. Quoted (VERIFIED-ABSTRACT, ICLR 2027 submission record) for 92d-A2, FLAG_B; relation: adjacent.

> 92.9% of post-training Top-1 changes remain within the pretrained Top-16 on average, while their relative preferences are substantially reorganized.

Locator: Abstract (OpenReview API record) (ICLR 2027 submission record)

[14] [Towards Physical Intuitions for Alignment Dynamics: A Case Study With Randomness Crystallization](https://arxiv.org/html/2606.29933v1) (Kunal Samanta, Ari Holtzman, Peter West; 2026) — arXiv preprint. Quoted (VERIFIED, v1) for 92d-A2, FLAG_B; relation: partly-fires.

> the nucleation phase caused by supervised finetuning, in which behavior collapses onto a single seed distribution present in the pretrained LLM; and (3) a settling phase in which reinforcement learning techniques redistribute probability of the collapsed distribution, but largely keep it concentrated on the same options as the seed distribution.

Locator: Abstract (v1)

[15] [Same Targets, Different Computation: How Post-Training Divides Work Across Model Layers](https://arxiv.org/html/2605.07284v2) (Yifan Zhou; 2026) — arXiv preprint. Quoted (VERIFIED, v2) for 92d-B1, FLAG_A; relation: method-overlap.

> We distinguish these cases with a four-cell diagnostic that crosses base or descendant upstream states with base or descendant late stacks.

Locator: Abstract (v2)

> At evaluation, the hidden state entering the late boundary is replaced for all sequence positions and the downstream stack recomputes its own keys and values.

Locator: Sec. 2.1 (v2)

> The result is also positive at every tested boundary from 40% depth through the final block, so it is not created by one global rotation or one specially chosen cut.

Locator: Sec. 5 (focused validity tests) (v2)

> Random later disagreements from the same rollouts retain 56% of the first-divergence interaction

Locator: Sec. 5 (token and history selection) (v2)

[16] [Activation Space Interventions Can Be Transferred Between Large Language Models](https://arxiv.org/html/2503.04429v4) (Narmeen Oozeer, Dhruv Nathawani, Nirmalendu Prakash, Michael Lan, Abir Harrasse, Amirali Abdullah; 2025) — ICML 2025. Quoted (VERIFIED, v4) for 92d-B1, FLAG_A; relation: method-overlap.

> By replacing the fine-tuned model’s activations with the corresponding base model activations, we assess the effectiveness of this technique in mitigating the backdoor.

Locator: Sec. 4.4 (Switch from Fine-tuned to Base Models) (v4)

> We observe that patching activations of a single layer can reduce backdoor trigger by up to 60% (refer Figure 23 for layer-wise values).

Locator: Sec. 4.4 (v4)

> The autoencoder successfully simulates direct activation patching at these layers, functioning as a binary switch between fine-tuned and base model behaviors.

Locator: Sec. 4.4 (v4)

[17] [How Post-Training Reshapes LLMs: A Mechanistic View on Knowledge, Truthfulness, Refusal, and Confidence](https://arxiv.org/html/2504.02904v3) (Hongzhe Du, Weikai Li, Min Cai, Karim Saraipour, Zimin Zhang, Himabindu Lakkaraju, Yizhou Sun, Shichang Zhang; 2025) — COLM 2025. Quoted (VERIFIED, v3) for 92d-B1, 92d-B2, FLAG_A; relation: adjacent, method-overlap.

> We further conduct cross-model experiments by patching hidden representations from base to post (forward patching) and from post to base (backward patching).

Locator: Sec. 3 (knowledge storage) (v3)

> The results demonstrate that the forward patching is almost always successful, but the backward patching often fails.

Locator: Sec. 3 (knowledge storage) (v3)

> The truthfulness direction is highly similar between the base and post-trained model, and it is effectively transferable for interventions

Locator: Abstract (v3)

[18] [Fine-Tuning Enhances Existing Mechanisms: A Case Study on Entity Tracking](https://arxiv.org/html/2402.14811v1) (Nikhil Prakash, Tamar Rott Shaham, Tal Haklay, Yonatan Belinkov, David Bau; 2024) — ICLR 2024. Quoted (VERIFIED, v1) for 92d-B1, FLAG_A; relation: method-overlap.

> Cross-model activation patching shows evidence that (i) the internal representation of both the original model and the fine-tuned models is similar enough so that patching components of the entity-tracking circuit from the fine-tuned models to Llama-7B leads to enhanced performance.

Locator: Sec. 1 (Introduction) (v1)

[19] [Not All Layers Need Tuning: Selective Layer Restoration Recovers Diversity](https://arxiv.org/html/2602.06665v1) (Bowen Zhang, Meiyi Wang, Harold Soh; 2026) — arXiv preprint. Quoted (VERIFIED, v1) for 92d-B1, FLAG_A; relation: adjacent.

> we hypothesize that mode collapse can be localized to specific layers and that restoring a carefully chosen range of layers to their pre-trained weights can recover diversity while maintaining high output quality.

Locator: Abstract (v1)

> Selective Layer Restoration (SLR), a training-free method that restores selected layers in a post-trained model to their pre-trained weights, yielding a hybrid model with the same architecture and parameter count, incurring no additional inference cost.

Locator: Abstract (v1)

[20] [Controlling the Diversity-Quality Trade-Off of LLMs by Merging Models Before and After Alignment](https://arxiv.org/html/2610.22999v1) (Yasuaki Sumita, Tomoharu Iwata, Toshiyuki Tanaka; 2026) — arXiv preprint. Quoted (VERIFIED, v1) for 92d-B1, 92d-C, FLAG_A; relation: adjacent.

> This approach combines the lower layers of an aligned model with the higher layers of its base model based on the hypothesis that lexical diversity is more closely associated with lower layers and semantic diversity with higher layers.

Locator: Abstract (v1)

> They also demonstrated a better diversity–quality trade-off than temperature sampling in most settings.

Locator: Abstract (v1)

[21] [Locked at the Entrance, Open Inside: Where RLVR Narrows the Solution Space](https://api2.openreview.net/notes/search?term=Locked%20at%20the%20Entrance%2C%20Open%20Inside%3A%20Where%20RLVR%20Narrows%20the%20Solution%20Space&group=ICLR.cc/2027/Conference&limit=10) (2026) — ICLR 2027 submission (under review); contemporaneous by rule. Quoted (VERIFIED-ABSTRACT, ICLR 2027 submission record) for 92d-A0, 92d-A1, 92d-B1, 92d-C, FLAG_A; relation: adjacent, supports.

> We show that this contraction is heavily concentrated at the entrance: per-token likelihood shifts are 11x--16x larger prior to the first arithmetic operation than during downstream reasoning.

Locator: Abstract (OpenReview API record) (ICLR 2027 submission record)

> Supplying only an unselected entrance prefix restores completion rates in low-access families by over an order of magnitude (0.018 to 0.212 under PPO), demonstrating that alternative solutions remain executable but are no longer initiated.

Locator: Abstract (OpenReview API record) (ICLR 2027 submission record)

> Guided by this localization, layer interpolation restores entrance diversity and increases solution coverage by 37%, with pass@1 of 0.305 versus 0.278 for the late policy.

Locator: Abstract (OpenReview API record) (ICLR 2027 submission record)

[22] [Measuring, Localizing, and Ablating Alignment Signatures in LLMs](https://arxiv.org/html/2605.30526v2) (Aniket Anand, Janvijay Singh, Zhewei Sun, Dilek Hakkani-Tür, Nick Feamster; 2026) — arXiv preprint. Quoted (VERIFIED, v2) for 92d-B2; relation: occupies.

> a training-free method that estimates a post-training alignment signature from aligned-base residual contrasts and ablates the corresponding direction during decoding.

Locator: Abstract (v2; v1 title 'Measuring, Localizing, and Ablating Alignment Signatures in LLMs') (v2)

> this effect transfers well across detectors and is not reproduced by random directions. Qualitative analysis suggests that PASTA generations remain relevant and coherent while exhibiting greater stylistic variation.

Locator: Abstract (v2)

> Each random ablation uses the same residual-stream hook footprint and decoding seed as PASTA.

Locator: Sec. 5.1 (Specificity of PASTA's direction) (v2)

[23] [Training-Induced Reasoning Directions: Uncovering Reusable Structure in Post-Training Reasoning](https://api2.openreview.net/notes/search?term=Training-Induced%20Reasoning%20Directions%3A%20Uncovering%20Reusable%20Structure%20in%20Post-Training%20Reasoning&group=ICLR.cc/2027/Conference&limit=10) (2026) — ICLR 2027 submission (under review); contemporaneous by rule. Quoted (VERIFIED-ABSTRACT, ICLR 2027 submission record) for 92d-B2; relation: adjacent.

> fixed activation directions extracted from computational differences between models before and after post-training.

Locator: Abstract (OpenReview API record) (ICLR 2027 submission record)

> injecting it into the Base model improves reasoning accuracy by up to 50.9 percentage points, while suppressing it substantially degrades the post-trained model.

Locator: Abstract (OpenReview API record) (ICLR 2027 submission record)

[24] [Narrow Finetuning Leaves Clearly Readable Traces in Activation Differences](https://arxiv.org/html/2510.13900v3) (Julian Minder, Clément Dumas, Stewart Slocum, Helena Casademunt, Cameron Holmes, Robert West, Neel Nanda; 2025) — ICLR 2026. Quoted (VERIFIED, v3) for 92d-B2; relation: adjacent.

> analyzing activation differences on the first few tokens of random text and steering by adding this difference to the model activations produces text similar to the format and general content of the finetuning data.

Locator: Abstract (v3)

[25] [Model Extrapolation Expedites Alignment](https://arxiv.org/html/2404.16792v5) (Chujie Zheng, Ziqi Wang, Heng Ji, Minlie Huang, Nanyun Peng; 2024) — ACL 2025. Quoted (VERIFIED, v5) for 92d-B2; relation: adjacent.

> Given a partially-trained model and its initial SFT checkpoint, ExPO improves the implicit optimization objective of alignment training by simply amplifying the parameter change based on a first-order approximation

Locator: Abstract (v5)

[26] [Chat Vector: A Simple Approach to Equip LLMs with Instruction Following and Model Alignment in New Languages](https://arxiv.org/html/2310.04799v3) (Shih-Cheng Huang, Pin-Zu Li, Yu-Chi Hsu, Kuang-Ming Chen, Yu Tung Lin, Shih-Kai Hsiao, Richard Tzong-Han Tsai, Hung-yi Lee; 2023) — ACL 2024. Quoted (VERIFIED, v3) for 92d-B2; relation: adjacent.

> The chat vector is derived by subtracting the weights of a pre-trained base model (e.g. LLaMA2) from those of its corresponding chat model (e.g. LLaMA2-chat).

Locator: Abstract (v3)

[27] [Editing Models with Task Arithmetic](https://arxiv.org/html/2212.04089v3) (Gabriel Ilharco, Marco Tulio Ribeiro, Mitchell Wortsman, Suchin Gururangan, Ludwig Schmidt, Hannaneh Hajishirzi, Ali Farhadi; 2022) — ICLR 2023. Quoted (VERIFIED, v3) for 92d-B2; relation: adjacent.

> Negating a task vector decreases performance on the target task, with little change in model behavior on control tasks.

Locator: Abstract (v3)

[28] [Optimizing Diversity and Quality through Base-Aligned Model Collaboration](https://arxiv.org/html/2511.05650v2) (Yichen Wang, Chenghao Yang, Tenghao Huang, Muhao Chen, Jonathan May, Mina Lee; 2025) — ICML 2026. Quoted (VERIFIED, v2) for 92d-B1, 92d-C; relation: occupies.

> We propose Base-Aligned Model Collaboration (BACo), an inference-time token-level model collaboration framework that dynamically combines a base LLM with its aligned counterpart to optimize diversity and quality.

Locator: Abstract (v2)

> Using uncertainty and content-based signals, BACo employs routing strategies to determine, at each token, which model to decode from.

Locator: Abstract (v2)

> evaluate them across three open-ended generation tasks with 13 diversity and quality metrics. BACo consistently surpasses state-of-the-art inference-time baselines. With our best router, BACo achieves a 21.3% joint improvement in diversity and quality

Locator: Abstract (v2)

[29] [Mind the Gap: Conformative Decoding to Improve Output Diversity of Instruction-Tuned Large Language Models](https://arxiv.org/html/2507.20956v1) (Max Peeperkorn, Tom Kouwenhoven, Dan Brown, Anna Jordanous; 2025) — arXiv preprint. Quoted (VERIFIED, v1) for 92d-B1, 92d-C; relation: occupies.

> The results indicate that DPO has the most substantial impact on diversity. Motivated by these findings, we present a new decoding strategy, conformative decoding, which guides an instruct model using its more diverse base model to reintroduce output diversity.

Locator: Abstract (v1)

[30] [Don't Throw Away Your Pretrained Model](https://arxiv.org/html/2510.09913v1) (Shangbin Feng, Wenhao Yu, Yike Wang, Hongming Zhang, Yulia Tsvetkov, Dong Yu; 2025) — arXiv preprint. Quoted (VERIFIED, v1) for 92d-C; relation: occupies.

> we propose Switch Generation, where pretrained and aligned model versions take turns to “speak” in a response sequence.

Locator: Abstract (v1)

[31] [Intent Factored Generation: Unleashing the Diversity in Your Language Model](https://arxiv.org/html/2506.09659v1) (Eltayeb Ahmed, Uljad Berdica, Martha Elliott, Danijela Horak, Jakob N. Foerster; 2025) — Inherited from art_kjrCpQnPaniY Table 92c row(s) C1b, C1-seedb; cited by row id, not re-verified in this audit.

> Current methods for increasing diversity often only operate at the token-level, paraphrasing the same response.

Locator: Abstract

> This factorisation allows us to use a higher temperature during the intent step to promote conceptual diversity, and a lower temperature during the final generation to ensure the outputs are coherent and self-consistent.

Locator: Abstract

[32] [Planning In Natural Language Improves LLM Search For Code Generation](https://arxiv.org/html/2409.03733v2) (Evan Wang, Federico Cassano, Catherine Wu, Yunfeng Bai, Will Song, Vaskar Nath, Ziwen Han, Sean Hendryx, Summer Yue, Hugh Zhang; 2024) — Inherited from art_kjrCpQnPaniY Table 92c row(s) C1c; cited by row id, not re-verified in this audit.

> We empirically demonstrate that this lack of diversity can be mitigated by searching over candidate plans for solving a problem in natural language.

Locator: Abstract

[33] [Rethinking Activation Steering for Mathematical Reasoning: What Actually Drives Its Reasoning Gains?](https://api2.openreview.net/notes/search?term=Rethinking%20Activation%20Steering%20for%20Mathematical%20Reasoning&group=ICLR.cc/2027/Conference&limit=10) (2026) — Inherited from art_kjrCpQnPaniY Table 92c row(s) C1g, C3cd; cited by row id, not re-verified in this audit.

> they alter local decoder preferences and redirect generation among reasoning trajectories already supported by the model. Correct solutions and related reasoning strategies are frequently accessible under unsteered sampling.

Locator: OpenReview abstract (ICLR 2027 submission)

> More directly, ordinary stochastic decoding whose parameters are selected to match steering's aggregate departure from greedy decoding achieves comparable accuracy while substantially reducing the remaining marginal benefit of steering; whole-thought exploration reproduces the same pattern.

Locator: OpenReview abstract (ICLR 2027 submission)

[34] [SAEs (usually) Transfer Between Base and Chat Models](https://www.alignmentforum.org/posts/fmwk6qxrpW8d4jvbd/saes-usually-transfer-between-base-and-chat-models) — grey literature (blog/research update). Quoted (VERIFIED-BLOG, web (2024)) for 92d-B1, 92d-E; relation: context.

> SAEs trained on the base model transfer surprisingly well to reconstructing chat activations

Locator: Executive summary (web (2024))

> We find that the difference in weights between Gemma v1 2B base vs chat is unusually large compared to other fine-tuned models, explaining this phenomenon.

Locator: Sec. 1 (introduction of results) (web (2024))

[35] [Mathematical discoveries from program search with large language models](https://www.nature.com/articles/s41586-023-06924-6) (Bernardino Romera-Paredes; 2024) — Inherited from art_kjrCpQnPaniY Table 92c row(s) C3ca; cited by row id, not re-verified in this audit.

> Applying FunSearch to a central problem in extremal combinatorics—the cap set problem—we discover new constructions of large cap sets going beyond the best-known ones, both in finite dimensional and asymptotic cases.

Locator: Abstract (Nature article page)

[36] [AlphaEvolve: A coding agent for scientific and algorithmic discovery](https://arxiv.org/html/2506.13131v1) (Alexander Novikov, Ngân Vũ, Marvin Eisenberger, Emilien Dupont, Po-Sen Huang, Adam Zsolt Wagner, Sergey Shirobokov, Borislav Kozlovskii, Francisco J. R. Ruiz, Abbas Mehrabian, M. Pawan Kumar, Abigail See, Swarat Chaudhuri, George Holland, Alex Davies, Sebastian Nowozin, Pushmeet Kohli, Matej Balog; 2025) — Inherited from art_kjrCpQnPaniY Table 92c row(s) C3cb; cited by row id, not re-verified in this audit.

> Using an evolutionary approach, continuously receiving feedback from one or more evaluators,

Locator: Abstract

[37] [RESTORING DIVERSITY IN DISTILLED IMAGE AND VIDEO GENERATORS BY PROBING ACTIVATIONS](https://api2.openreview.net/notes/search?term=RESTORING%20DIVERSITY%20IN%20DISTILLED%20IMAGE%20AND%20VIDEO%20GENERATORS%20BY%20PROBING%20ACTIVATIONS&group=ICLR.cc/2027/Conference&limit=10) (2026) — ICLR 2027 submission (under review); contemporaneous by rule. Quoted (VERIFIED-ABSTRACT, ICLR 2027 submission record) for 92d-B1, 92d-B2, FLAG_A; relation: adjacent.

> This directional collapse is localized to an identifiable intermediate block at the initial denoising step.

Locator: Abstract (OpenReview API record) (ICLR 2027 submission record)

> At inference time, ReDiverse-TF introduces a training-free mechanism that steers activations along precomputed teacher principal directions.

Locator: Abstract (OpenReview API record) (ICLR 2027 submission record)

[38] [Run-time Steering Can Surpass Post-Training: Reasoning Task Performance](https://www.lesswrong.com/posts/dvbRv97GpRg5gXKrf/run-time-steering-can-surpass-post-training-reasoning-task) — grey literature (blog/research update). Quoted (VERIFIED-BLOG, web) for 92d-B2; relation: adjacent.

> I haven't performed essential baseline tests including random vector patching

Locator: Limitations (web)

[39] [Sparse Crosscoders for Cross-Layer Features and Model Diffing](https://transformer-circuits.pub/2024/crosscoders/index.html) (Jack Lindsey, Adly Templeton, Jonathan Marcus, Thomas Conerly, Joshua Batson, Christopher Olah; 2024) — grey literature (blog/research update). Quoted (VERIFIED-BLOG, web (Oct 25, 2024)) for 92d-A2, 92d-B1; relation: context.

> finetuned models use similar mechanism as the base model from which they were trained

Locator: literal span of verified quote; Sec. 4 (Model diffing) (web (Oct 25, 2024))

[40] [DivAlgo: A systematic evaluation of algorithmic diversity for code generation models](https://arxiv.org/html/2610.19157v1) (Anubhav Jangra, Smaranda Muresan; 2026) — arXiv preprint. Quoted (VERIFIED, v1) for 92d-A0, FLAG_C; relation: context.

> For RQ1, we show that uncontrolled sampling (for 24 LLMs) yields considerably less diverse solutions than human solutions

Locator: Sec. 1 (contributions, RQ1) (v1)

[41] [Generative Monoculture in Large Language Models](https://arxiv.org/html/2407.02209v1) (Fan Wu, Emily Black, Varun Chandrasekaran; 2024) — ICLR 2025 (poster). Quoted (VERIFIED, v1) for 92d-A0, FLAG_C; relation: context, supports.

> The figures show that the pre-trained model enjoys much better diversity than the aligned model, and is much closer to the source.

Locator: App. C.4, Fig. 8 caption text (v1)

> However, neither of the models were able to produce code solutions in our trials.

Locator: App. E.4 (open-source code models) (v1)

[42] [Weight Ensembling Improves Reasoning in Language Models](https://arxiv.org/html/2504.10478v4) (Xingyu Dang, Christina Baek, Kaiyue Wen, Zico Kolter, Aditi Raghunathan; 2025) — COLM 2025. Quoted (VERIFIED, v4) for 92d-B1, 92d-C, baselines; relation: baseline-to-add.

> Surprisingly, a simple intervention of interpolating the weights of the latest SFT checkpoint with an early checkpoint, otherwise known as WiSE-FT, almost completely recovers Pass@k while also improving Pass@1.

Locator: Abstract (v4)

> Finally, we find that WiSE-FT provides complementary performance gains that cannot be achieved only through diversity-inducing decoding strategies, like temperature scaling.

Locator: Abstract (v4)

> To test whether coding tasks exhibit the same diversity collapse observed in reasoning benchmarks, we fine-tuned the Qwen2.5-coder-0.5B model for 10 epochs on the Magicoder-Evol-Instruct-110K dataset

Locator: App. H (coding task) (v4)

[43] [Hindsight Merging: Diverse Data Generation with Language Models](https://proceedings.mlr.press/v286/veselovsky25a.html) (Veniamin Veselovsky, Benedikt Stroebl, Gianluca Bencomo, Dilip Arumugam, Lisa Schut, Arvind Narayanan, Thomas L. Griffiths; 2025) — UAI 2025 (PMLR v286). Quoted (VERIFIED, UAI 2025 proceedings page) for 92d-B1, baselines; relation: baseline-to-add.

> we introduce hindsight merging, a technique that combines a fine-tuned model with a previous training checkpoint using linear interpolation to restore entropy and improve performance.

Locator: Abstract (PMLR page) (UAI 2025 proceedings page)

> achieving a consistent 20-50% increase in pass@10 relative to the instruction tuned model across a coding benchmark and series of models.

Locator: Abstract (PMLR page) (UAI 2025 proceedings page)

[44] [Should SFT Prefer the Familiar? Diversity Collapse and Recovery via Model Merging](https://api2.openreview.net/notes/search?term=Should%20SFT%20Prefer%20the%20Familiar%3F%20Diversity%20Collapse%20and%20Recovery%20via%20Model%20Merging&group=ICLR.cc/2027/Conference&limit=10) (2026) — ICLR 2027 submission (under review); contemporaneous by rule. Quoted (VERIFIED-ABSTRACT, ICLR 2027 submission record) for 92d-B1, baselines; relation: baseline-to-add.

> To mitigate this effect, we propose a simple recovery approach: merging the fine-tuned model with its pretrained base model before RL.

Locator: Abstract (OpenReview API record) (ICLR 2027 submission record)

> Across multiple mathematical reasoning and code generation benchmarks, base-model merging consistently outperforms recent SFT variants

Locator: Abstract (OpenReview API record) (ICLR 2027 submission record)

[45] [What RL Brings to Reasoning: A Few Decisions the Base Model Would Not Make](https://arxiv.org/html/2610.24663v1) (Siyu Zhang, Yuquan Lu, Yoshua Y. Li, Yifan Ding, Kun Zeng, Yu Huo, Yifu Guo, Rongxiang Weng, Xunliang Cai, Xiaoying Tang; 2026) — arXiv preprint. Quoted (VERIFIED, v1) for 92d-B1, 92d-C; relation: adjacent.

> Yet borrowing the RL model’s token only where the two models’ greedy choices differ, roughly 4% of generated positions, recovers 90.5% of the pass@1 gain

Locator: Abstract (v1)

> Sparse replacement also retains much of the base model’s diversity while staying close to the RL model at pass@1.

Locator: Abstract (v1)

[46] [An Emulator for Fine-Tuning Large Language Models using Small Language Models](https://arxiv.org/html/2310.12962v1) (Eric Mitchell, Rafael Rafailov, Archit Sharma, Chelsea Finn, Christopher D. Manning; 2023) — arXiv preprint (ICLR 2024 per plan; not confirmed here). Quoted (VERIFIED, v1) for 92d-B2, 92d-C; relation: baseline-to-add.

> Emulated fine-tuning is based on a simple factorization of the logits of a fine-tuned language model into a) the base log probabilities of a pre-trained base model and b) the ‘behavior delta’, or the difference between the log probabilities of a base model and fine-tuned model.

Locator: Sec. 1 (v1)

[47] [Tuning Language Models by Proxy](https://arxiv.org/html/2401.08565v4) (Alisa Liu, Xiaochuang Han, Yizhong Wang, Yulia Tsvetkov, Yejin Choi, Noah A. Smith; 2024) — COLM 2024. Quoted (VERIFIED, v4) for 92d-B2, 92d-C; relation: baseline-to-add.

> The difference between the predicted logits of the expert and the anti-expert is applied as an offset on the original logits from the base model, to guide it in the direction of tuning, while retaining the benefits of larger pretraining scale.

Locator: Fig. 1 caption (v4)

[48] [Does Reinforcement Learning Really Incentivize Reasoning Capacity in LLMs Beyond the Base Model?](https://arxiv.org/html/2504.13837v5) (Yang Yue, Zhiqi Chen, Rui Lu, Andrew Zhao, Zhaokai Wang, Yang Yue, Shiji Song, Gao Huang; 2025) — NeurIPS 2025 (oral). Quoted (VERIFIED, v5) for 92d-A0; relation: context, supports.

> systematically probing the reasoning capability boundaries of RLVR-trained LLMs across various model families, RL algorithms, and math/coding/visual reasoning benchmarks, using pass@k at large k values as the evaluation metric.

Locator: Abstract (v5)

> elicit fundamentally new reasoning patterns

Locator: literal span of verified quote; Abstract (v5)

[49] [Judging RLVR Boundary Comparisons Against Their Own Measured Noise](https://api2.openreview.net/notes/search?term=Judging%20RLVR%20Boundary%20Comparisons%20Against%20Their%20Own%20Measured%20Noise&group=ICLR.cc/2027/Conference&limit=10) (2026) — ICLR 2027 submission (under review); contemporaneous by rule. Quoted (VERIFIED-ABSTRACT, ICLR 2027 submission record) for 92d-A0, 92d-B1; relation: context, contradicts-in-part.

> We show that both published answers can be read off one fixed (base, RLVR) pair at every sampling budget we test by moving only sampling temperature and scoring rule

Locator: Abstract (OpenReview API record) (ICLR 2027 submission record)

> the base-ahead ones concentrate in chat-template cells at low temperature.

Locator: Abstract (OpenReview API record) (ICLR 2027 submission record)

[50] [Measuring Alignment-Induced Activation Shifts Correctly: A Template-Controlled Difference-in-Differences Protocol](https://arxiv.org/html/2605.24583v3) (Yuki Nakamura; 2026) — arXiv preprint. Quoted (VERIFIED, v3) for 92d-B1, 92d-B2; relation: supports.

> The aligned model is evaluated under a chat template the base model never saw, so the naive difference conflates the alignment shift with chat formatting.

Locator: Abstract (v3)

[51] [How Much, Not Where: RLVR's Capability Loss Is Dose-Controlled and Deep-Tail Only](https://api2.openreview.net/notes/search?term=How%20Much%2C%20Not%20Where%3A%20RLVR%27s%20Capability%20Loss%20Is%20Dose-Controlled%20and%20Deep-Tail%20Only&group=ICLR.cc/2027/Conference&limit=10) (2026) — ICLR 2027 submission (under review); contemporaneous by rule. Quoted (VERIFIED-ABSTRACT, ICLR 2027 submission record) for 92d-A1, FLAG_B; relation: adjacent, contradicts-in-part.

> we track a forward-only signal: the per-prompt decay rate λ̂ of the likelihood of frozen base-correct trajectories on boundary prompts, those the base model solves only rarely.

Locator: Abstract (OpenReview API record) (ICLR 2027 submission record)

> A dose- and schedule-matched control that anchors randomly chosen prompts protects as well as our signal-triggered scheme

Locator: Abstract (OpenReview API record) (ICLR 2027 submission record)

[52] [Creativity Has Left the Chat: The Price of Debiasing Language Models](https://arxiv.org/pdf/2406.05587v1) (Behnam Mohammadi; 2024) — arXiv preprint. Quoted (VERIFIED, v1) for 92d-A1, 92d-A2; relation: adjacent.

> We demonstrate this by intentionally perturbing the model’s generation trajectory, effectively nudging it away from its usual output distribution. Surprisingly, the aligned model gracefully finds its way back to its own attractor state and in-distribution response.

Locator: Sec. 1 (Introduction) (v1)

[53] [Echo Chamber: RL Post-training Amplifies Behaviors Learned in Pretraining](https://arxiv.org/html/2504.07912v2) (Rosie Zhao, Alexandru Meterez, Sham Kakade, Cengiz Pehlevan, Samy Jelassi, Eran Malach; 2025) — COLM 2025. Quoted (VERIFIED, v2) for 92d-A0, 92d-A2; relation: supports.

> Our study reveals that RL algorithms consistently converge towards a dominant output distribution, amplifying patterns in the pretraining data.

Locator: Abstract (v2)

[54] [Base Models Can Reason by Taking a Cue from Their Training Data](https://api2.openreview.net/notes/search?term=Base%20Models%20Can%20Reason%20by%20Taking%20a%20Cue%20from%20Their%20Training%20Data&group=ICLR.cc/2027/Conference&limit=10) (2026) — ICLR 2027 submission (under review); contemporaneous by rule. Quoted (VERIFIED-ABSTRACT, ICLR 2027 submission record) for 92d-A2; relation: supports.

> Second, we demonstrate that RL itself learns to make these same starting cues more likely, while fixing these cues recovers much of its performance gain over the base model.

Locator: Abstract (OpenReview API record) (ICLR 2027 submission record)

[55] [Where You Inject Diversity Matters: A Unified Framework for Diverse Generation](https://arxiv.org/html/2606.10302v1) (Cheng Zhang, Rui Xin, Chudi Zhong; 2026) — Inherited from art_kjrCpQnPaniY Table 92c row(s) C1-siteb/c; cited by row id, not re-verified in this audit.

> We introduce a framework that characterizes test-time diverse generation methods by the diversity source introduced during generation and provide a transmission score for measuring how effectively variation in the source reaches the final output.

Locator: Abstract

> It measures the fraction of source diversity that is realized in the final output.

Locator: Sec. 3.3, text after Definition 1 (Transmission Score)

[56] [Gacha Decoding: Eliciting Diverse Generations Through Instruction Following](https://arxiv.org/html/2610.01382v1) (Scott Geng, Yufei Zhang, Joseph Lee, Jerry Li, Marjan Ghazvininejad, Pang Wei Koh; 2026) — Inherited from art_kjrCpQnPaniY Table 92c row(s) C1j; cited by row id, not re-verified in this audit.

> Our key insight is to treat diversity as an instruction-following problem: rather than relying on the LM’s token entropy, we combine its instruction-following capability with randomness from an external RNG tool to scalably identify and realize distinct modes of the response space.

Locator: Abstract

[57] [Perturb the Thought, Not the Pixels: Latent-Space Rollout Diversification for Reinforcement Learning of Vision-Language Models](https://arxiv.org/html/2608.21595v1) (Michael Jerge, Joseph Pelczar, Justin Downes; 2026) — Inherited from art_kjrCpQnPaniY Table 92c row(s) C1-sitef; cited by row id, not re-verified in this audit.

> Existing approaches diversify through decoding temperature or pixel-space image distortion; we ask whether the perturbation belongs in the model’s latent space instead. We introduce Noise-Contrastive GRPO (NC-GRPO), which injects scale-calibrated Gaussian noise into the last hidden layer of the prompt-encoding pass for half of each rollout group, branching those rollouts from a displaced departure state.

Locator: Abstract

[58] [LLM Probability Concentration: How Alignment Shrinks the Generative Horizon](https://arxiv.org/html/2506.17871v1) (Chenghao Yang, Sida Li, Ari Holtzman; 2025) — TMLR 2026 (v4 comment). Quoted (VERIFIED, v1) for 92d-A0, corrections; relation: context.

> alignment tuning substantially sharpens the model’s output distribution from the outset, reducing BF by nearly an order of magnitude (e.g., from 12 to 1.2) relative to base models.

Locator: Abstract (v1, title 'How Alignment Shrinks the Generative Horizon') (v1)

[59] [Understanding the Effects of RLHF on LLM Generalisation and Diversity](https://arxiv.org/html/2310.06452v3) (Robert Kirk, Ishita Mediratta, Christoforos Nalmpantis, Jelena Luketina, Eric Hambro, Edward Grefenstette, Roberta Raileanu; 2023) — ICLR 2024 per plan; not confirmed on a venue page. Quoted (VERIFIED, v3) for 92d-A0; relation: supports.

> However, RLHF significantly reduces output diversity compared to SFT across a variety of measures, implying a tradeoff in current LLM fine-tuning methods between generalisation and diversity.

Locator: Abstract (v3)

[60] [Base Models Beat Aligned Models at Randomness and Creativity](https://arxiv.org/html/2505.00047v2) (Peter West, Christopher Potts; 2025) — arXiv preprint. Quoted (VERIFIED, v2) for 92d-A0; relation: supports.

> Across models tested, better performance on common benchmarks tends to correlate with worse performance on our tasks, suggesting an effective trade-off in the required capabilities.

Locator: Abstract (v2)

[61] [One fish, two fish, but not the whole sea: Alignment reduces language models' conceptual diversity](https://arxiv.org/html/2411.04427v3) (Sonia K. Murthy, Tomer Ullman, Jennifer Hu; 2024) — NAACL 2025. Quoted (VERIFIED, v3) for 92d-A0; relation: supports.

> While no model reaches human-like diversity, aligned models generally display less diversity than their instruction fine-tuned counterparts.

Locator: Abstract (v3)

[62] [Annotations Mitigate Post-Training Mode Collapse](https://arxiv.org/html/2605.09995v1) (Jacob Mitchell Springer, Madhu Advani, Lukas Aichberger, Arwen Bradley, Eran Malach, Omid Saremi, Sinead Williamson, Preetum Nakkiran, Etai Littwin, Aditi Raghunathan; 2026) — ICML 2026. Quoted (VERIFIED, v1) for 92d-A0; relation: supports.

> Larger base models are not less diverse, but larger post-trained models are.

Locator: Sec. 3 (results) (v1)

> We consistently find that models with lower post-training loss (higher likelihood) generate less diverse outputs

Locator: Sec. 4 (v1)

[63] [The One-Word Census: Answer-Choice Conformity Across 105 Language Models](https://arxiv.org/html/2607.12796v4) (Tapan Parikh; 2026) — arXiv preprint. Quoted (VERIFIED, v4) for 92d-A0; relation: supports.

> Lightly post-trained and persona-tuned models are the most divergent; heavily post-trained assistants from the major labs are the most conformist.

Locator: Abstract (v4)

[64] [The Invisible Leash: Why RLVR May or May Not Escape Its Origin](https://arxiv.org/html/2507.14843v5) (Fang Wu, Weihao Xuan, Danny Xing, Ximing Lu, Mingjie Liu, Yi Dong, Zaid Harchaoui, Yejin Choi; 2025) — arXiv preprint. Quoted (VERIFIED, v5) for 92d-A0; relation: context, supports.

> it remains unclear whether the current practice of RLVR truly expands models’ reasoning boundary or mainly amplifies high-reward outputs that base models already know.

Locator: Abstract (v5)

> Losses exceed gains in every model-level aggregate in Tab. 1, giving negative net support change

Locator: Sec. 3.2 (Empirical support shrinkage outweighs expansion) (v5)

[65] [Narrative Flattening: How Post-Training Compresses Thematic, Affective, and Stylistic Variation in LLM Fiction](https://arxiv.org/html/2605.27878v2) (Zehan Li, Yutong Zhu, Siyang Wu, Honglin Bao, James A. Evans; 2026) — EMNLP 2026 (main). Quoted (VERIFIED, v2) for 92d-A0; relation: supports.

> Across all three, post-training compresses dynamic variation

Locator: Abstract (v2)

[66] ["I've Seen How This Goes": Characterizing Diversity via Progressive Conditional Surprise](https://arxiv.org/html/2606.01811v1) (Matthew Khoriaty, David Williams-King, Shi Feng; 2026) — ICML 2026 workshop (non-archival); not main track. Quoted (VERIFIED, v1) for 92d-A0, 92d-A1; relation: adjacent, supports.

> a per-byte score read off the per-token log-probabilities of a base model

Locator: Abstract (v1)

> On the OLMo-2-7B post-training pipeline,

Locator: Abstract (v1)

[67] [Rethinking Code Similarity for Automated Algorithm Design with LLMs](https://arxiv.org/html/2603.02787v1) (Rui Zhang, Zhichao Lu; 2026) — ICLR 2026. Quoted (VERIFIED, v1) for 92d-A0; relation: method-overlap.

> We propose BehaveSim, a novel method to measure algorithmic similarity through the lens of problem-solving behavior as a sequence of intermediate solutions produced during execution

Locator: Abstract (v1)

[68] [Self-Improvement in Language Models: The Sharpening Mechanism](https://arxiv.org/html/2412.01951v2) (Audrey Huang, Adam Block, Dylan J. Foster, Dhruv Rohatgi, Cyril Zhang, Max Simchowitz, Jordan T. Ash, Akshay Krishnamurthy; 2024) — arXiv preprint (ICLR 2025 per plan; not confirmed here). Quoted (VERIFIED, v2) for 92d-B2; relation: context.

> We refer to the sharpening mechanism as the phenomenon where responses from a model with the highest certainty (in the sense of large self-reward

Locator: Sec. 1.1 (The Sharpening Mechanism) (v2)

[69] [Reasoning with Sampling: Your Base Model is Smarter Than You Think](https://arxiv.org/html/2510.14901v1) (Aayush Karan, Yilun Du; 2025) — arXiv preprint. Quoted (VERIFIED, v1) for 92d-B2, 92d-C; relation: baseline-to-add.

> Moreover, our sampler avoids the collapse in diversity over multiple samples that is characteristic of RL-posttraining.

Locator: Abstract (v1)

[70] [Predictive Mechanistic Interpretability of Post-Training: A Priori Forecasts of Circuit Localization and Sign from the Base Model](https://api2.openreview.net/notes/search?term=Predictive%20Mechanistic%20Interpretability%20of%20Post-Training%3A%20A%20Priori%20Forecasts%20of%20Circuit%20Localization%20and%20Sign%20from%20the%20Base%20Model&group=ICLR.cc/2027/Conference&limit=10) (2026) — ICLR 2027 submission (under review); contemporaneous by rule. Quoted (VERIFIED-ABSTRACT, ICLR 2027 submission record) for 92d-A1, FLAG_B; relation: adjacent.

> Which attention heads a post-training update will change, and in which direction, can be forecast before training, from the base model alone.

Locator: Abstract (OpenReview API record) (ICLR 2027 submission record)

[71] [From Data to Behavior: Predicting Unintended Model Behaviors Before Training](https://arxiv.org/html/2602.04735v1) (Mengru Wang, Zhenqian Xu, Junfeng Fang, Yunzhi Yao, Shumin Deng, Huajun Chen, Ningyu Zhang; 2026) — arXiv preprint (work in progress). Quoted (VERIFIED, v1) for 92d-A1, FLAG_B; relation: adjacent.

> summarizes candidate data through their mean representations and injects them into the forward pass of a base model

Locator: Abstract (v1)

[72] [Persona Vectors: Monitoring and Controlling Character Traits in Language Models](https://arxiv.org/html/2507.21509v3) (Runjin Chen, Andy Arditi, Henry Sleight, Owain Evans, Jack Lindsey; 2025) — arXiv preprint. Quoted (VERIFIED, v3) for 92d-A1, FLAG_B; relation: adjacent.

> Training data “projection difference” predicts post-finetuning trait expression before finetuning.

Locator: Sec. 6.1, Fig. 8 caption (v3)

[73] [RL's Razor: Why Online Reinforcement Learning Forgets Less](https://arxiv.org/html/2509.04259v1) (Idan Shenfeld, Jyothish Pari, Pulkit Agrawal; 2025) — arXiv preprint. Quoted (VERIFIED, v1) for 92d-A1; relation: context.

> the KL divergence between the fine-tuned and base policy evaluated on the new task.

Locator: Sec. 1 (v1)

[74] [Nudging: Inference-time Alignment of LLMs via Guided Decoding](https://arxiv.org/html/2410.09300v4) (Yu Fei, Yasaman Razeghi, Sameer Singh; 2024) — ACL 2025 (main). Quoted (VERIFIED, v4) for 92d-A2, 92d-C; relation: adjacent.

> Nudging is motivated by recent findings that alignment primarily alters the model’s behavior on a small subset of stylistic tokens (e.g., discourse markers). We find that base models are significantly more uncertain when generating these tokens.

Locator: Abstract (v4) (v4)

[75] [Controlled Text Generation via Language Model Arithmetic](https://arxiv.org/html/2311.14479v3) (Jasper Dekoninck, Marc Fischer, Luca Beurer-Kellner, Martin Vechev; 2023) — arXiv preprint (ICLR 2024 per plan; not confirmed here). Quoted (VERIFIED, v3) for 92d-C; relation: context.

> we introduce model arithmetic, a novel inference framework for composing and biasing LLMs without the need for model (re)training or highly specific datasets.

Locator: Abstract (v3)

[76] [CreativeInstruct: Scalably Teaching LLMs to Balance Quality, Creativity, and Diversity](https://arxiv.org/html/2608.07460v1) (Ananya Sahu, Mohit Bansal, Elias Stengel-Eskin; 2026) — arXiv preprint. Quoted (VERIFIED, v1) for 92d-C; relation: context.

> However, these methods incur latency and computational overhead at test-time, requiring two models. Moreover, these frameworks require access to base models, which are not always released.

Locator: Sec. 1 (v1)

[77] [Recovering Diversity Without Losing Alignment: A DPO Recipe for Post-Trained LLMs](https://arxiv.org/html/2605.30021v2) (Vinay Samuel, Yapei Chang, Mohit Iyyer; 2026) — arXiv preprint (under review). Quoted (VERIFIED, v2) for 92d-A2, 92d-B1; relation: adjacent.

> post-training can remove valid answer modes from the instruct model’s candidate distribution in the first place. We therefore use the base model to recover missing alternatives

Locator: Sec. 1 (v2)

[78] [No Single Best Model for Diversity: Learning a Router for Sample Diversity](https://arxiv.org/html/2604.02319v3) (Yuhan Liu, Fangyuan Xu, Vishakh Padmakumar, Daphne Ippolito, Eunsol Choi; 2026) — COLM 2026. Quoted (VERIFIED, v3) for 92d-C; relation: adjacent.

> Yet, per each prompt, there exists a model that outperforms all other models significantly at generating a diverse answer set. Motivated by this finding, we introduce a router that predicts the best model for each query.

Locator: Abstract (v3)

[79] [Not Which Path, but What Happens Before You Would Stop: What Reasoning Post-Training Changes](https://api2.openreview.net/notes/search?term=Not%20Which%20Path%2C%20but%20What%20Happens%20Before%20You%20Would%20Stop%3A%20What%20Reasoning%20Post-Training%20Changes&group=ICLR.cc/2027/Conference&limit=10) (2026) — ICLR 2027 submission (under review); contemporaneous by rule. Quoted (VERIFIED-ABSTRACT, ICLR 2027 submission record) for 92d-A2, 92d-B1, 92d-C; relation: adjacent, context.

> Our instrument is a transplant in which one model writes and, wherever the two disagree about the next token, at 3 to 6% of positions, the other model's word is substituted.

Locator: Abstract (OpenReview API record) (ICLR 2027 submission record)

> Forcing each option there shows that both models mostly agree and neither chooses reliably better.

Locator: Abstract (OpenReview API record) (ICLR 2027 submission record)

[80] [Where Does RLVR Act? A Conserved Token Ledger for What Post-Training Adds to a Base Model](https://api2.openreview.net/notes/search?term=Where%20Does%20RLVR%20Act%3F%20A%20Conserved%20Token%20Ledger%20for%20What%20Post-Training%20Adds%20to%20a%20Base%20Model&group=ICLR.cc/2027/Conference&limit=10) (2026) — ICLR 2027 submission (under review); contemporaneous by rule. Quoted (VERIFIED-ABSTRACT, ICLR 2027 submission record) for 92d-C; relation: adjacent.

> tokens, the base the rest) is a conserved ledger

Locator: Abstract (OpenReview API record) (ICLR 2027 submission record)

[81] [Logit Grafting: The Post-Training Delta is Sparse, Portable, and Powerful](https://api2.openreview.net/notes/search?term=Logit%20Grafting%3A%20The%20Post-Training%20Delta%20is%20Sparse%2C%20Portable%2C%20and%20Powerful&group=ICLR.cc/2027/Conference&limit=10) (2026) — ICLR 2027 submission (under review); contemporaneous by rule. Quoted (VERIFIED-ABSTRACT, ICLR 2027 submission record) for 92d-C; relation: adjacent.

> Decoding-time methods that take logit differences from auxiliary models and add it to a target model offer a viable solution to this transfer problem.

Locator: Abstract (OpenReview API record) (ICLR 2027 submission record)

[82] [Reasoning Can Be Restored by Correcting a Few Decision Tokens](https://arxiv.org/html/2605.16874v1) (Changshuo Shen, Leheng Sheng, Yuxin Chen, An Zhang, Xiang Wang; 2026) — ICML 2026. Quoted (VERIFIED, v1) for 92d-B1, 92d-C; relation: adjacent.

> we find that the reasoning advantage is highly sparse and concentrates on a small set of early, planning-related decision tokens.

Locator: Abstract (v1)

[83] [Reasoning-Finetuning Repurposes Latent Representations in Base Models](https://arxiv.org/html/2507.12638v1) (Jake Ward, Chuqiao Lin, Constantin Venhoff, Neel Nanda; 2025) — ICML 2025 Workshop on Actionable Interpretability. Quoted (VERIFIED, v1) for 92d-B1, 92d-B2, FLAG_A; relation: adjacent.

> Specifically, we identify a direction in base Llama-3.1-8B’s residual stream which systematically induces backtracking when used to steer the distilled reasoning model

Locator: Abstract (v1)

[84] [Base Models Know How to Reason, Thinking Models Learn When](https://arxiv.org/html/2510.07364v4) (Constantin Venhoff, Iván Arcuschin, Philip Torr, Arthur Conmy, Neel Nanda; 2025) — ICML 2026 (spotlight). Quoted (VERIFIED, v4) for 92d-A0, 92d-B1; relation: adjacent.

> hybrid models recover roughly 76% of the RL base-to-thinking gap but only 11% of the SFT gap. This indicates RL primarily teaches heuristics for orchestrating pre-existing base mechanisms, whereas SFT-distillation installs new ones

Locator: Abstract (v4)

[85] [Improving Instruction-Following in Language Models through Activation Steering](https://arxiv.org/html/2410.12877v2) (Alessandro Stolfo, Vidhisha Balachandran, Safoora Yousefi, Eric Horvitz, Besmira Nushi; 2024) — ICLR 2025. Quoted (VERIFIED, v2) for 92d-B1, 92d-B2, FLAG_A; relation: adjacent.

> Finally, we demonstrate that steering vectors computed on instruction-tuned models can transfer to improve base models.

Locator: Abstract (v2)

[86] [Layers at Similar Depths Generate Similar Activations Across LLM Architectures](https://arxiv.org/html/2504.08775v3) (Christopher Wolfram, Aaron Schein; 2025) — arXiv preprint. Quoted (VERIFIED, v3) for 92d-B1; relation: context.

> Instruction tuning changes the activations generated by models in later layers, but only when given inputs that are targeted by instruction tuning.

Locator: App. A.2, Fig. 8 caption (v3)

[87] [Cache-to-Cache: Direct Semantic Communication Between Large Language Models](https://arxiv.org/html/2510.03215v2) (Tianyu Fu, Zihan Min, Hanling Zhang, Jichao Yan, Guohao Dai, Wanli Ouyang, Yu Wang; 2025) — ICLR 2026. Quoted (VERIFIED, v2) for 92d-B1; relation: adjacent.

> C2C uses a neural network to project and fuse the source model’s KV-cache with that of the target model to enable direct semantic transfer.

Locator: Abstract (v2)

[88] [Patchscopes: A Unifying Framework for Inspecting Hidden Representations of Language Models](https://arxiv.org/html/2401.06102v4) (Asma Ghandeharioun, Avi Caciularu, Adam Pearce, Lucas Dixon, Mor Geva; 2024) — ICML 2024. Quoted (VERIFIED, v4) for 92d-B1; relation: context.

> A possible avenue for improving inspection capabilities is to explain a given model with a model that is more expressive (Bills et al., 2023).

Locator: Sec. 4.4 (Expressiveness from Cross-Model Patching) (v4)

[89] [Beyond Learning: A Training-Free Alternative to Model Adaptation](https://arxiv.org/html/2602.16189v1) (Namkyung Yoon, Kyeonghyun Yoo, Wooyong Jung, Sanghong Kim, Hwangnam Kim; 2026) — arXiv preprint (submitted to Pattern Recognition Letters). Quoted (VERIFIED, v1) for 92d-B1, FLAG_A; relation: adjacent.

> in transplant experiments between a base model and its instruction-tuned counterpart, transplantation improves the underperforming model toward the stronger baseline

Locator: Abstract (v1)

[90] [Weight Patching: Toward Source-Level Mechanistic Localization in LLMs](https://arxiv.org/html/2604.13694v1) (Chenghao Sun, Chengsheng Zhang, Guanzheng Qin, Rui Dai, Xinmei Tian; 2026) — arXiv preprint (submitted to IEEE). Quoted (VERIFIED, v1) for 92d-B1; relation: adjacent.

> Given a base model and a behavior-specialized counterpart, Weight Patching replaces selected module weights from the specialized model into the base model under a fixed input.

Locator: Abstract (v1)

[91] [Activation Control for Efficiently Eliciting Long Chain-of-thought Ability of Language Models](https://arxiv.org/html/2505.17697v1) (Zekai Zhao, Qi Liu, Kun Zhou, Zihan Liu, Yifei Shao, Zhiting Hu, Biwei Huang; 2025) — arXiv preprint. Quoted (VERIFIED, v1) for 92d-B1; relation: adjacent.

> Based on this finding, it is promising to use the base LLM itself to predict the long-CoT related activations.

Locator: Sec. 2.3, Finding-4 (v1)

[92] [Beyond Token-Level Guidance: Inference-Time Alignment of Specialized LLMs via Cross-Family Representation Steering](https://arxiv.org/html/2608.30319v1) (Jin Gan, Xin Li, Jun Luo; 2026) — EMNLP 2026. Quoted (VERIFIED, v1) for 92d-B1; relation: adjacent.

> we propose CREST, an inference-time alignment method that steers base model hidden representations using safety directions extracted from a guidance model of any family

Locator: Abstract (v1)

[93] [Eliciting Chain-of-Thought in Base LLMs via Gradient-Based Representation Optimization](https://arxiv.org/html/2511.19131v1) (Zijian Wang, Yanxiang Ma, Chang Xu; 2025) — AAAI 2026. Quoted (VERIFIED, v1) for 92d-B1; relation: adjacent.

> Can we solely manipulate the hidden states to elicit CoT reasoning from a base LLM, without distorting its language quality?

Locator: Sec. 1 (v1)

[94] [Towards Best Practices of Activation Patching in Language Models: Metrics and Methods](https://arxiv.org/html/2309.16042v2) (Fred Zhang, Neel Nanda; 2023) — ICLR 2024. Quoted (VERIFIED, v2) for 92d-B1; relation: context.

> At a high-level, our findings highlight the sensitivity of activation patching to methodological details.

Locator: Sec. 1 (Recommendations for practice) (v2)

[95] [How to use and interpret activation patching](https://arxiv.org/html/2404.15255v1) (Stefan Heimersheim, Neel Nanda; 2024) — arXiv preprint (tutorial). Quoted (VERIFIED, v1) for 92d-B1; relation: context.

> There are multiple ways to do activation patching. The techniques differ in what the source (source of activations / model run from which the activations are copied) and destination prompt

Locator: Sec. 2.3 (Noising and Denoising) (v1)

[96] [Safety Alignment Should Be Made More Than Just a Few Tokens Deep](https://arxiv.org/html/2406.05946v1) (Xiangyu Qi, Ashwinee Panda, Kaifeng Lyu, Xiao Ma, Subhrajit Roy, Ahmad Beirami, Prateek Mittal, Peter Henderson; 2024) — ICLR 2025 (Outstanding Paper). Quoted (VERIFIED, v1) for 92d-B1; relation: supports.

> safety alignment can take shortcuts, wherein the alignment adapts a model’s generative distribution primarily over only its very first few output tokens.

Locator: Abstract (v1)

[97] [Overcoming Sparsity Artifacts in Crosscoders to Interpret Chat-Tuning](https://arxiv.org/html/2504.02922v4) (Julian Minder, Clément Dumas, Caden Juang, Bilal Chugtai, Neel Nanda; 2025) — NeurIPS 2025. Quoted (VERIFIED, v4) for 92d-B2; relation: context.

> we identify two issues which stem from the crosscoders L1 training loss that can misattribute concepts as unique to the fine-tuned model, when they really exist in both models.

Locator: Abstract (v4)

[98] [What We Learned Trying to Diff Base and Chat Models (And Why It Matters)](https://www.lesswrong.com/posts/xmpauEXEerzYcJKNm/what-we-learned-trying-to-diff-base-and-chat-models-and-why) — grey literature (blog/research update). Quoted (VERIFIED-BLOG, web (2025)) for 92d-B2; relation: context.

> We show that you can resolve these issues with a simple architectural adjustment: using a BatchTopK instead of an L1 sparsity loss.

Locator: Summary (web (2025))

[99] [Small Vectors, Big Effects: A Mechanistic Study of RL-Induced Reasoning via Steering Vectors](https://arxiv.org/html/2509.06608v4) (Viacheslav Sinii, Nikita Balagansky, Gleb Gerasimov, Daniil Laptev, Yaroslav Aksenov, Vadim Kurochkin, Alexey Gorbatovski, Boris Shaposhnikov, Daniil Gavrilov; 2025) — arXiv preprint. Quoted (VERIFIED, v4) for 92d-B2, FLAG_A; relation: adjacent.

> steering vectors trained in one model often retain a non-trivial fraction of their performance when inserted into a closely matched model, suggesting that the underlying steering directions are largely preserved under fine-tuning and instruction tuning.

Locator: Sec. 1, findings (v4)

[100] [How Strong Is the Evidence for the Artificial Hivemind? Reevaluating Evidence for the Open-Ended Homogeneity of Language Models](https://arxiv.org/html/2609.33936v1) (Rylan Schaeffer, Brando Miranda, Joshua Kazdan, Jessica Chudnovsky, Sanmi Koyejo; 2026) — arXiv preprint. Quoted (VERIFIED, v1) for 92d-A0; relation: contradicts-in-part.

> Our responses and the original authors’ own show one dominant vehicle plus a heavy tail of distinct minority vehicles.

Locator: Abstract (v1)

[101] [Fine-Tuning Fixes Mode Collapse and Over-Dispersion in LLMs](https://arxiv.org/html/2609.16454v1) (Kirill Skobelev, Eric Fithian, X. Y. Han; 2026) — arXiv preprint. Quoted (VERIFIED, v1) for 92d-A0; relation: contradicts-in-part.

> In this work, we show that whether mode-collapse—or its opposite—occurs depends on the specific model and dataset used.

Locator: Abstract (v1)

[102] [Fine-Tuning Improves Information Conveyance in Language Models](https://arxiv.org/html/2605.30844v1) (Yuwei Cheng, Weiyi Tian, Haifeng Xu; 2026) — arXiv preprint. Quoted (VERIFIED, v1) for 92d-A0; relation: contradicts-in-part.

> Fine-tuning is often believed to reduce uncertainty and diversity in large language models, but existing analyses overlook output length, a key confounder

Locator: Abstract (v1)

## Verification

Numbered citations resolve to unique listed sources. Passage checks test text occurrence, not claim truth or entailment. Author/year metadata and locators are not independently verified. Details: `research_verification.json`.

- Source [2]: text found — When comparing the Deepseek-base and Deepseek-instruct models, algorithmic diversity shows different
- Source [2]: text found — This suggests that instruction tuning favors single, straightforward answers for simple problems whi
- Source [2]: text found — The generated solutions are executed with test cases to verify their functional correctness.
- Source [2]: text found — we employ the Llama-3.1-8B-Instruct model (Llama, 2024) to assess algorithmic relevance between two 
- Source [3]: text found — We focus on a more specific notion: whether repeated-sampling RLVR produces near-duplicate implement
- Source [4]: text found — alignment tuning substantially sharpens the model’s output distribution from the outset, reducing BF
- Source [4]: text found — We hypothesize that alignment tuning does not fundamentally change a model’s behavior, but instead s
- Source [5]: text found — A base-vs-instruct ablation on Qwen3-14B confirms the causal role of alignment: the base model shows
- Source [5]: text found — localizes the cause to DPO, not SFT.
- Source [6]: text found — We find that convergence can be revealed and amplified, but not introduced by the SFT data, supporti
- Source [6]: text found — We find that instruct-like collapse can be induced through prompting alone, even without alignment.
- Source [6]: text found — We argue that output homogeneity is likely learned during the pretraining phase, and only
- Source [7]: text found — Per-Problem Base Anchoring (PBA) is a deliberately simple proof-of-concept: sharpen prompts with suf
- Source [7]: text found — decompose prompts by frozen base-model behavior into solved-easy, reachable, boundary, and out-of-re
- Source [7]: text found — where the base model contains rare correct trajectories that are recoverable by sampling but too spa
- Source [8]: text found — The missing part lives in the base model’s behaviour on a problem, not in what the problem looks lik
- Source [9]: text found — Lookahead outperforms BoN at predicting which IFEval prompts degrade after training
- Source [10]: text found — RLVR disproportionately reinforces problems with high likelihood, correct solutions under the base m
- Source [11]: text found — sharpens the reference distribution, amplifying its modes while suppressing the tails. The effect st
- Source [11]: text found — we identify a fundamental, pervasive data-level driver:
- Source [12]: text found — the top-ranked tokens in aligned LLMs are mostly found within the top five tokens ranked by base LLM
- Source [12]: text found — Most distribution shifts occur with stylistic tokens (e.g., discourse markers, safety disclaimers).
- Source [13]: text found — 92.9% of post-training Top-1 changes remain within the pretrained Top-16 on average, while their rel
- Source [14]: text found — the nucleation phase caused by supervised finetuning, in which behavior collapses onto a single seed
- Source [15]: text found — We distinguish these cases with a four-cell diagnostic that crosses base or descendant upstream stat
- Source [15]: text found — At evaluation, the hidden state entering the late boundary is replaced for all sequence positions an
- Source [15]: text found — The result is also positive at every tested boundary from 40% depth through the final block, so it i
- Source [15]: text found — Random later disagreements from the same rollouts retain 56% of the first-divergence interaction
- Source [16]: text found — By replacing the fine-tuned model’s activations with the corresponding base model activations, we as
- Source [16]: text found — We observe that patching activations of a single layer can reduce backdoor trigger by up to 60% (ref
- Source [16]: text found — The autoencoder successfully simulates direct activation patching at these layers, functioning as a 
- Source [17]: text found — We further conduct cross-model experiments by patching hidden representations from base to post (for
- Source [17]: text found — The results demonstrate that the forward patching is almost always successful, but the backward patc
- Source [17]: text found — The truthfulness direction is highly similar between the base and post-trained model, and it is effe
- Source [18]: text found — Cross-model activation patching shows evidence that (i) the internal representation of both the orig
- Source [19]: text found — we hypothesize that mode collapse can be localized to specific layers and that restoring a carefully
- Source [19]: text found — Selective Layer Restoration (SLR), a training-free method that restores selected layers in a post-tr
- Source [20]: text found — This approach combines the lower layers of an aligned model with the higher layers of its base model
- Source [20]: text found — They also demonstrated a better diversity–quality trade-off than temperature sampling in most settin
- Source [21]: text found — We show that this contraction is heavily concentrated at the entrance: per-token likelihood shifts a
- Source [21]: text found — Supplying only an unselected entrance prefix restores completion rates in low-access families by ove
- Source [21]: text found — Guided by this localization, layer interpolation restores entrance diversity and increases solution 
- Source [22]: text found — a training-free method that estimates a post-training alignment signature from aligned-base residual
- Source [22]: text found — this effect transfers well across detectors and is not reproduced by random directions. Qualitative 
- Source [22]: text found — Each random ablation uses the same residual-stream hook footprint and decoding seed as PASTA.
- Source [23]: text found — fixed activation directions extracted from computational differences between models before and after
- Source [23]: text found — injecting it into the Base model improves reasoning accuracy by up to 50.9 percentage points, while 
- Source [24]: text found — analyzing activation differences on the first few tokens of random text and steering by adding this 
- Source [25]: text found — Given a partially-trained model and its initial SFT checkpoint, ExPO improves the implicit optimizat
- Source [26]: text found — The chat vector is derived by subtracting the weights of a pre-trained base model (e.g. LLaMA2) from
- Source [27]: text found — Negating a task vector decreases performance on the target task, with little change in model behavio
- Source [28]: text found — We propose Base-Aligned Model Collaboration (BACo), an inference-time token-level model collaboratio
- Source [28]: text found — Using uncertainty and content-based signals, BACo employs routing strategies to determine, at each t
- Source [28]: text found — evaluate them across three open-ended generation tasks with 13 diversity and quality metrics. BACo c
- Source [29]: text found — The results indicate that DPO has the most substantial impact on diversity. Motivated by these findi
- Source [30]: text found — we propose Switch Generation, where pretrained and aligned model versions take turns to “speak” in a
- Source [31]: text found — Current methods for increasing diversity often only operate at the token-level, paraphrasing the sam
- Source [31]: text found — This factorisation allows us to use a higher temperature during the intent step to promote conceptua
- Source [32]: text found — We empirically demonstrate that this lack of diversity can be mitigated by searching over candidate 
- Source [33]: text found — they alter local decoder preferences and redirect generation among reasoning trajectories already su
- Source [33]: text found — More directly, ordinary stochastic decoding whose parameters are selected to match steering's aggreg
- Source [34]: text found — SAEs trained on the base model transfer surprisingly well to reconstructing chat activations
- Source [34]: text found — We find that the difference in weights between Gemma v1 2B base vs chat is unusually large compared 
- Source [35]: text found — Applying FunSearch to a central problem in extremal combinatorics—the cap set problem—we discover ne
- Source [36]: text found — Using an evolutionary approach, continuously receiving feedback from one or more evaluators,
- Source [37]: text found — This directional collapse is localized to an identifiable intermediate block at the initial denoisin
- Source [37]: text found — At inference time, ReDiverse-TF introduces a training-free mechanism that steers activations along p
- Source [38]: text found — I haven't performed essential baseline tests including random vector patching
- Source [39]: text found — finetuned models use similar mechanism as the base model from which they were trained
- Source [40]: text found — For RQ1, we show that uncontrolled sampling (for 24 LLMs) yields considerably less diverse solutions
- Source [41]: text found — The figures show that the pre-trained model enjoys much better diversity than the aligned model, and
- Source [41]: text found — However, neither of the models were able to produce code solutions in our trials.
- Source [42]: text found — Surprisingly, a simple intervention of interpolating the weights of the latest SFT checkpoint with a
- Source [42]: text found — Finally, we find that WiSE-FT provides complementary performance gains that cannot be achieved only 
- Source [42]: text found — To test whether coding tasks exhibit the same diversity collapse observed in reasoning benchmarks, w
- Source [43]: text found — we introduce hindsight merging, a technique that combines a fine-tuned model with a previous trainin
- Source [43]: text found — achieving a consistent 20-50% increase in pass@10 relative to the instruction tuned model across a c
- Source [44]: text found — To mitigate this effect, we propose a simple recovery approach: merging the fine-tuned model with it
- Source [44]: text found — Across multiple mathematical reasoning and code generation benchmarks, base-model merging consistent
- Source [45]: text found — Yet borrowing the RL model’s token only where the two models’ greedy choices differ, roughly 4% of g
- Source [45]: text found — Sparse replacement also retains much of the base model’s diversity while staying close to the RL mod
- Source [46]: text found — Emulated fine-tuning is based on a simple factorization of the logits of a fine-tuned language model
- Source [47]: text found — The difference between the predicted logits of the expert and the anti-expert is applied as an offse
- Source [48]: text found — systematically probing the reasoning capability boundaries of RLVR-trained LLMs across various model
- Source [48]: text found — elicit fundamentally new reasoning patterns
- Source [49]: text found — We show that both published answers can be read off one fixed (base, RLVR) pair at every sampling bu
- Source [49]: text found — the base-ahead ones concentrate in chat-template cells at low temperature.
- Source [50]: text found — The aligned model is evaluated under a chat template the base model never saw, so the naive differen
- Source [51]: text found — we track a forward-only signal: the per-prompt decay rate λ̂ of the likelihood of frozen base-correc
- Source [51]: text found — A dose- and schedule-matched control that anchors randomly chosen prompts protects as well as our si
- Source [52]: text found — We demonstrate this by intentionally perturbing the model’s generation trajectory, effectively nudgi
- Source [53]: text found — Our study reveals that RL algorithms consistently converge towards a dominant output distribution, a
- Source [54]: text found — Second, we demonstrate that RL itself learns to make these same starting cues more likely, while fix
- Source [55]: text found — We introduce a framework that characterizes test-time diverse generation methods by the diversity so
- Source [55]: text found — It measures the fraction of source diversity that is realized in the final output.
- Source [56]: text found — Our key insight is to treat diversity as an instruction-following problem: rather than relying on th
- Source [57]: text found — Existing approaches diversify through decoding temperature or pixel-space image distortion; we ask w
- Source [58]: text found — alignment tuning substantially sharpens the model’s output distribution from the outset, reducing BF
- Source [59]: text found — However, RLHF significantly reduces output diversity compared to SFT across a variety of measures, i
- Source [60]: text found — Across models tested, better performance on common benchmarks tends to correlate with worse performa
- Source [61]: text found — While no model reaches human-like diversity, aligned models generally display less diversity than th
- Source [62]: text found — Larger base models are not less diverse, but larger post-trained models are.
- Source [62]: text found — We consistently find that models with lower post-training loss (higher likelihood) generate less div
- Source [63]: text found — Lightly post-trained and persona-tuned models are the most divergent; heavily post-trained assistant
- Source [64]: text found — it remains unclear whether the current practice of RLVR truly expands models’ reasoning boundary or 
- Source [64]: text found — Losses exceed gains in every model-level aggregate in Tab. 1, giving negative net support change
- Source [65]: text found — Across all three, post-training compresses dynamic variation
- Source [66]: text found — a per-byte score read off the per-token log-probabilities of a base model
- Source [66]: text found — On the OLMo-2-7B post-training pipeline,
- Source [67]: text found — We propose BehaveSim, a novel method to measure algorithmic similarity through the lens of problem-s
- Source [68]: text found — We refer to the sharpening mechanism as the phenomenon where responses from a model with the highest
- Source [69]: text found — Moreover, our sampler avoids the collapse in diversity over multiple samples that is characteristic 
- Source [70]: text found — Which attention heads a post-training update will change, and in which direction, can be forecast be
- Source [71]: text found — summarizes candidate data through their mean representations and injects them into the forward pass 
- Source [72]: text found — Training data “projection difference” predicts post-finetuning trait expression before finetuning.
- Source [73]: text found — the KL divergence between the fine-tuned and base policy evaluated on the new task.
- Source [74]: text found — Nudging is motivated by recent findings that alignment primarily alters the model’s behavior on a sm
- Source [75]: text found — we introduce model arithmetic, a novel inference framework for composing and biasing LLMs without th
- Source [76]: text found — However, these methods incur latency and computational overhead at test-time, requiring two models. 
- Source [77]: text found — post-training can remove valid answer modes from the instruct model’s candidate distribution in the 
- Source [78]: text found — Yet, per each prompt, there exists a model that outperforms all other models significantly at genera
- Source [79]: text found — Our instrument is a transplant in which one model writes and, wherever the two disagree about the ne
- Source [79]: text found — Forcing each option there shows that both models mostly agree and neither chooses reliably better.
- Source [80]: text found — tokens, the base the rest) is a conserved ledger
- Source [81]: text found — Decoding-time methods that take logit differences from auxiliary models and add it to a target model
- Source [82]: text found — we find that the reasoning advantage is highly sparse and concentrates on a small set of early, plan
- Source [83]: text found — Specifically, we identify a direction in base Llama-3.1-8B’s residual stream which systematically in
- Source [84]: text found — hybrid models recover roughly 76% of the RL base-to-thinking gap but only 11% of the SFT gap. This i
- Source [85]: text found — Finally, we demonstrate that steering vectors computed on instruction-tuned models can transfer to i
- Source [86]: text found — Instruction tuning changes the activations generated by models in later layers, but only when given 
- Source [87]: text found — C2C uses a neural network to project and fuse the source model’s KV-cache with that of the target mo
- Source [88]: text found — A possible avenue for improving inspection capabilities is to explain a given model with a model tha
- Source [89]: text found — in transplant experiments between a base model and its instruction-tuned counterpart, transplantatio
- Source [90]: text found — Given a base model and a behavior-specialized counterpart, Weight Patching replaces selected module 
- Source [91]: text found — Based on this finding, it is promising to use the base LLM itself to predict the long-CoT related ac
- Source [92]: text found — we propose CREST, an inference-time alignment method that steers base model hidden representations u
- Source [93]: text found — Can we solely manipulate the hidden states to elicit CoT reasoning from a base LLM, without distorti
- Source [94]: text found — At a high-level, our findings highlight the sensitivity of activation patching to methodological det
- Source [95]: text found — There are multiple ways to do activation patching. The techniques differ in what the source (source 
- Source [96]: text found — safety alignment can take shortcuts, wherein the alignment adapts a model’s generative distribution 
- Source [97]: text found — we identify two issues which stem from the crosscoders L1 training loss that can misattribute concep
- Source [98]: text found — We show that you can resolve these issues with a simple architectural adjustment: using a BatchTopK 
- Source [99]: text found — steering vectors trained in one model often retain a non-trivial fraction of their performance when 
- Source [100]: text found — Our responses and the original authors’ own show one dominant vehicle plus a heavy tail of distinct 
- Source [101]: text found — In this work, we show that whether mode-collapse—or its opposite—occurs depends on the specific mode
- Source [102]: text found — Fine-tuning is often believed to reduce uncertainty and diversity in large language models, but exis

## Follow-up Questions

- Which ICLR 2027 submissions must be re-checked once reviews and PDFs are public (Locked at the Entrance hu5mtofNd4, Same Candidates ooV5M72O08, Lookahead 6a4v7CpeAu, TIRD vkIOGTVcJP, Merge-before-RL MYXgOex05m, ReDiverse lZQK4G4Ktp) — does any full text measure solution diversity after writing base-model states into a tuned model, which would fire FLAG A?
- Should the B1 arm add weight-space and layer-level counterparts (Qwen3-8B Base/Instruct WiSE-FT-style interpolation, Selective Layer Restoration and FrankenMerging at blocks 12-23) and a template-controlled base-minus-instruct direction, so that reviewers can see whether the state transplant does anything weights cannot?
- Does Lee et al.'s mixed direction (instruction tuning narrows algorithmic diversity on easy problems but widens it on hard ones) hold under the run's execution-trace mechanism labels, and do simple base signals (base pass rate, per-algorithm share) predict inference-time movability better than Duan et al. found they predict training-time gains?

---
*Generated by AI Inventor Pipeline*
