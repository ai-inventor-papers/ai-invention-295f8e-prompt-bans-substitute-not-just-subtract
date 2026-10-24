# Who already found the hidden plan?

## Summary

Dated (2026-10-22) positioning audit for the iteration-6 claims P1-P5, N, S and E. It provides paste-ready Table 92e in research_report.md: 8 claim blocks plus CTRL rows. It has 123 new verbatim, versioned quotes from 94 sources, all 123/123 matched against cached source text and 123/123 re-matched by an independent live fetch_grep pass. Statuses: 82 VERIFIED, 22 VERIFIED-ABSTRACT, 4 VERIFIED-BLOG, 15 VERIFIED-README. It cites Tables 92b/92c (art_kjrCpQnPaniY) and 92d (art_ObxQOIlAM9MS) by row id without re-verifying them. Saturation search: protocol frozen and sha256-stamped before the first call; 21 strings over 7 lanes on arXiv API, Semantic Scholar, the OpenReview ICLR 2027 pool, OpenAlex/Crossref and grey literature; 6 round-2 strings; snowballing; a round 3 that met the stop rule; 126 logged calls (incl. 3 supplementary full-text checks). 2,191 raw hits gave 1,820 unique records, 1,401 in the window and 67 papers scored on the O/I/C rubric (75 claim-rows: 3 occupy, 66 adjacent, 6 irrelevant). FLAGS: A (DAS localization of algorithm choice in code, validated by generation) NOT FIRED, narrowly. CDAS (ICLR 2026) does DAS steering validated by generation, but on refusal and a CoT backdoor. Algorithm choice in code is moved only by prompt cues (92c Invisible Lottery). Code attributes that are not the algorithm (language, library, coding habits) are moved by patching or difference-in-means vectors. The nearest same-model, same-site neighbour is the ICLR 2027 submission 'Before Reasoning Begins' (Qwen3-8B final-prompt SAE targets, code benchmarks, random nulls). B (activation quantization changes perturbation effects) PARTLY FIRED. Steering under quantization has been measured only with weight-only INT8/NF4 (2609.06473: activations stay FP16/BF16). Two ICLR 2027 submissions show effect changes across precision with aligned directions, but their abstracts do not say whether activations are quantized (PDFs 403). FP8 W8A8 appears only in a non-determinism study. No source found measures the effect size of random perturbations under activation rounding. C (editing verbaliser explanations to steer) FIRED. The NLA paper (Transformer Circuits, 7 May 2026; cite as Fraser-Taliente, Kantamneni, Ong et al.) edits a rhyme-plan explanation, reconstructs it with the AR and steers at the newline only (~50% success). LatentQA, SelfIE and Dreaming Vectors are kin. N is therefore a replication in a new setting. Cautions: about 2% claim-dependence of the AR (2607.20379), no newline plan in small open models (2609.18440), and published readout controls (ICLR 2027 'Auditing the Auditor'). D (resampling a fitted causal plan variable for diversity) PARTLY FIRED. Activation noise and latent-code sampling are occupied; the closest fitted-direction work is the ICLR 2027 'Random Choice in LMs'. Lane verdicts: P1 PARTLY OCCUPIED (method); P2, P3 and P4 ADJACENT-ONLY; P5 PARTLY OCCUPIED; N OCCUPIED (method); S PARTLY OCCUPIED (SAE-Steering, ACL 2026, beats prompt and activation baselines on reasoning strategies); E ADJACENT-ONLY in the published record but PARTLY OCCUPIED by contemporaneous submissions. Corrections: there is no official NLA for Qwen3-8B, but community NLAs exist at L24 (nanoNLA, EasyNLA); circuit-tracer has Qwen-3 PLTs including 8B (Hanna et al.), so justify Gemma for S; Gemma Scope 2 dates from 22 Dec 2025, with IT SAEs finetuned from PT; Sutter's 'any network to any algorithm' phrase is not in v2; Engels' v3 title. The report also gives permitted and forbidden wording per claim and reviewer baselines. Evidence files are in evidence/.

## Research Findings

# Who already found the hidden plan? Positioning audit for iteration-6 claims (Table 92e)

*Retrieval date: 2026-10-22. This audit covers iteration-6 claims P1-P5, N, S and E. It extends Tables 92b/92c (art_kjrCpQnPaniY) and 92d (art_ObxQOIlAM9MS) and cites their rows by id without re-verifying them. Every new quote below is copied from the source's own versioned text: arXiv HTML (the PDF where no HTML exists), a transformer-circuits page, a PMLR or ICLR page, an OpenReview API record, a Hugging Face card or a GitHub README. Each quote was checked against a cached copy of that text, and then re-matched live by an independent fetch_grep pass. Rows state design facts only and quote no run-internal result.*

## 1. Summary

- **The four flags.** A: NOT FIRED (narrowly). B: PARTLY FIRED. C: FIRED. D: PARTLY FIRED.
- **N is a replication, not a new method.** The NLA paper (Transformer Circuits, 7 May 2026) already does what N proposes [1]. It edits the explanation of a *plan* (the rhyme word on the newline), turns the edit into an activation with the AR, and steers at the newline only. This works "roughly 50% of the time".
  - Verbaliser kin also steer: LatentQA [2], SelfIE [3, 4], and Dreaming Vectors, which takes steering vectors from Activation Oracles [5].
  - N's causal arm is therefore a **replication in a new setting**: algorithm choice in code, Qwen2.5-7B-Instruct at L20, and new controls.
  - Two 2026 results argue against assuming the edit will work. On a released Qwen-2.5-7B verbalizer, only "as few as" about 2% of specific claims are ones the reconstruction depends on [6]. A stress test on open models found no newline-resident rhyme plan [7].
- **E is open in the published record, but crowded by contemporaneous submissions.**
  - In the arXiv record, steering effect sizes under quantization have been compared with full precision only for weight-only INT8/NF4: "Activations remain in FP16/BF16 throughout the forward pass" [8].
  - Two ICLR 2027 submissions show that the same steering direction can have a different effect at another precision, even when the directions stay aligned [9, 10]. Their abstracts do not say whether activations are quantized, and their PDFs returned HTTP 403.
  - Among the sources found, FP8 weight-and-activation quantization appears only in a non-determinism study with no perturbations [11].
  - **No source found (search dated 2026-10-22) measures how activation rounding (FP8 W8A8, dynamic per-token scales [12]) changes the effect size of random activation perturbations.**
- **P1: the method is published, the object is open.**
  - DAS is the standard method for localizing a causal variable [13, 14].
  - DAS has already been used for steering validated by generation, but on refusal and a CoT backdoor, not on a plan [15].
  - In the sources found, algorithm choice in code has been moved only by prompt cues (92c source 30 [16]). Code attributes that are not the algorithm (language, library, coding habits) have been moved by patching or difference-in-means vectors [17, 18, 19].
  - The nearest same-model, same-site neighbour is an ICLR 2027 submission: SAE-feature targets at Qwen3-8B's final prompt position, with code benchmarks and random-null controls [20].
- **S: the method is occupied on a non-code strategy.** SAE-feature steering of *reasoning strategies* beats prompt-based and activation-based baselines, validated by generation [21] (ACL 2026).
  - Two priors pull in opposite directions. AxBench (prompting beats steering; SAEs not competitive [22]) is countered by its rebuttal [23]. On an open-model rhyme-planning task, only CLT-based steering succeeded [24].
  - Qwen-3 transcoders that include 8B exist in circuit-tracer [25, 26], and a planning study already uses them [27]. The paper must therefore say why S runs on Gemma Scope 2.
- **P2, P3 and P4 are ADJACENT-ONLY.**
- **P5 is PARTLY OCCUPIED.** Activation noise and latent-code sampling for diversity are occupied lanes [28, 29, 30, 31, 32, 33]. Resampling a *fitted, causally localized* plan variable is not published. The closest work, a fitted random-choice direction, is an ICLR 2027 submission [34].

## 2. Scope, date and method (PRISMA-S items)

- **Protocol.** Frozen and sha256-stamped before the first search call: sha256 `88e3bab2e451d477009ac5c62d284b00e2614a50fc583f86380cc71b26f3c4bc`, stamped 2026-10-22T06:19:27Z (evidence/protocol_iter6.json and .sha256). Amendments are logged with timestamps in evidence/protocol_amendments_iter6.jsonl:
  - an interpretation note on flag A;
  - reuse of prior audit tools;
  - two stop-rule entries.
- **Databases and engines.**
  - E1: OpenAlex/Crossref via the aii-web-tools scholarly search [35].
  - E3: arXiv API, sorted by submission date, newest first [36].
  - E4: Semantic Scholar search with year=2026, plus citations and references [37].
  - E5: the OpenReview ICLR 2027 pool through api2 notes/search [38].
  - E6: grey literature through the built-in web search, restricted to transformer-circuits.pub, lesswrong.com, alignmentforum.org, huggingface.co, github.com, neuronpedia.org and substack.com.
- **Strings and rounds.**
  - Round 1: 21 strings over 7 lanes (L1-L7). Every string ran on E3, E4 and E5; L1, L4 and L6 also ran on E1; L4, L5 and L6 also ran on E6.
  - Round 2: 6 strings, each motivated by a named round-1 hit (evidence/round2_queries_iter6.json), run on E1, E3, E4 and E5.
  - Snowballing: forward citations on Semantic Scholar for MIB (61 citers) and Emergent Response Planning (20 citers). Steering Under Compression had 0 citers, so the backward references of 2609.06473 and 2606.03002 were taken instead.
  - The NLA paper is not indexed by Semantic Scholar title search, so its forward search used E6.
  - Round 3 ran because round 2 produced new hits scoring at least 1.5: forward and backward references of those hits. It found no new hit scoring at least 1.5, so the search stopped (stop rule met).
  - In total: 126 logged calls (E1 15, E3 27, E4 43, E5 28, E6 10, SUPP 3), each with UTC time, engine, string, hit count and top-20 ids (evidence/search_log_iter6.jsonl).
- **Dates and limits.** Window: 2026-01-01 to 2026-10-22; anchors may be older. Contemporaneity rule inherited from 92d:
  - an arXiv v1 after 2026-06-22 is tagged contemporaneous_4mo;
  - every ICLR 2027 submission is tagged contemporaneous;
  - arXiv-only papers are exempt from the ICLR rule.
- **De-duplication.** 2191 raw hits reduced to 1820 unique records, keyed by arXiv id, then OpenReview forum id, then normalized title.
- **Screening.**
  - 1401 records were in the window. A documented keyword pre-screen (lane groups G1-G7, in tools/screen_iter6.py) passed 605.
  - Manual title and abstract screening, with full text for the shortlist, led to O/I/C scores for 75 claim-rows covering 67 papers (some anchors predate the window).
  - Results: 3 occupying, 66 adjacent, 6 irrelevant. In addition, 561 records were judged irrelevant at title/abstract and 790 were excluded at the keyword pre-screen.
  - Every in-window record has a one-line verdict in evidence/saturation_hits_iter6.jsonl.
- **Rubric (frozen).** Each axis scores 0, 0.5 or 1; a total of at least 2.5 occupies, 1-2 is adjacent, and below 1 is irrelevant.
  - O (object): 1 = which algorithm a code model writes; 0.5 = a categorical plan, strategy or attribute in another domain.
  - I (instrument): 1 = the claim's own intervention class; 0.5 = a neighbouring intervention.
  - C (criterion): 1 = validated by generation scored by tests or labels; 0.5 = a logit, probe or next-token readout.
- **Quote verification.**
  - 123 new quotes from 94 sources: 123/123 matched the cached source text under the inherited normalization rule (whitespace, ligatures, curly quotes and dashes, html2text emphasis; [...] segments must occur in order).
  - Statuses: 82 VERIFIED, 22 VERIFIED-ABSTRACT, 4 VERIFIED-BLOG, 15 VERIFIED-README.
  - QA (Step 4): an independent live fetch_grep pass re-matched 123/123 quotes (evidence/qa_second_pass_iter6.jsonl).
  - Where arXiv HTML renders a MathML number twice, the quote is split with [...] (2607.20379v2, 2602.17691v1, 2602.05234v2).
  - No number in this report comes from a text that could not be retrieved.
- **Inherited material.** 92b/92c/92d rows and quotes are cited by id (evidence/inherited_index.json: 207 sources). For the 8 flag-critical inherited references, the arXiv API was rechecked: none has a newer version than the one inherited (2601.22010, 2605.11936, 2608.21595, 2606.10302, 2603.23629, 2606.04057, 2605.05115, 2603.18353).

## 3. Verdict box

| Claim | Lane verdict | Deciding reference(s) |
|---|---|---|
| P1 low-rank causal PLAN variable (interchange/DAS) decides which algorithm Qwen3-8B writes; validated by generation | PARTLY OCCUPIED: the method is occupied (DAS; DAS steering validated by generation on a non-plan attribute); the object is open; flag A not fired | DAS/Boundless DAS [13, 39]; MIB [14]; CDAS [15]; Invisible Lottery [16]; Before Reasoning Begins [20] |
| P2 plan subspace mediates which random pushes switch the algorithm | ADJACENT-ONLY (unchanged from 92c C2a; prediction of random-push effects is still open) | Before the First Token [40]; AJR [41]; DecodeShare [42]; output-sensitive component [43]; coordinate outside a subspace [44] |
| P3 plan is discrete under interpolation | ADJACENT-ONLY | Park et al. [45]; Engels et al. [46]; Manifold Steering [47]; prolepsis [24]; random-choice switch [34] |
| P4 temperature leaves the plan untouched, state noise moves it, at matched KL | ADJACENT-ONLY | departure-matched decoding [48]; Peeperkorn [49]; Forking Paths [50]; future-behaviour forecasting [51] |
| P5 resampling the plan as a diversity knob | PARTLY OCCUPIED (activation noise and latent sampling for diversity are occupied; resampling a fitted causal plan variable is open); flag D partly fired | STARS / Noise Steering / REI [28, 29, 30]; LP-BD / PPLR / SVP [31, 32, 33]; Random Choice [34] |
| N read and edit the plan in words with NLAs | OCCUPIED (method): replication in a new setting; flag C fired | NLA [1]; LatentQA [2]; SelfIE [3]; cautions [6, 7, 52] |
| S the plan in Gemma Scope 2 SAE and transcoder features | PARTLY OCCUPIED (SAE-feature steering of reasoning strategies against prompt and activation baselines, validated by generation); algorithm choice in code is open | SAE-Steering [21]; AxBench and its rebuttal [22, 23]; Do SAEs Identify Reasoning Features [53]; prolepsis [24] |
| E FP8 W8A8 activation rounding inflates the apparent effect of activation perturbations | ADJACENT-ONLY in the published and arXiv record; the general claim is PARTLY OCCUPIED by contemporaneous ICLR 2027 submissions (abstract-level); flag B partly fired | weight-only steering [8]; Stable Directions [9]; Low-bit steering [10]; FP8 W8A8 non-determinism [11] |

**Optional lines (no new search):**
- **ST and L.** Site comparisons for diversity injection remain as in 92c C1-site: PARTLY OCCUPIED [54, 29, 28].
- **G.** The base-model variety lines remain as in 92d (A2/G rows: transplant and goal published; inference-time movability open) [55, 56].

## 4. Flags (frozen definitions in evidence/protocol_iter6.json; verdicts in evidence/flags_iter6.json)

### Flag A (P1): NOT FIRED, narrowly

No source localizes which algorithm or solution strategy a code LLM will use as a low-rank causal variable by interchange or DAS, and then checks the claim by scoring the generated programs. Each half exists on its own:

- **DAS-based steering checked by generation, on a non-plan attribute.** CDAS: "While we adopt the core mechanism of DAS, distributed interchange intervention (DII) [...] we introduce a novel distribution matching objective tailored for the steering task by aligning intervened output distributions with counterfactual distributions" [15]. Its targets are refusal and a CoT backdoor.
- **Algorithm choice in code, moved only by prompt cues** [16].
- **Code attributes that are not the algorithm.**
  - Causal Syntax Circuits: "Code models write Python when the prompt does not say which language to use" [17]. It uses patching, circuits and steering, read out at the next token.
  - Concept Vectors: difference-in-means directions for coding habits [18].
  - Rahman et al.: language and library [19].
- **Algorithm identity found by DAS, but in toy networks**, validated against transfer learning rather than generation [57].

None of these does DAS/interchange plus generation on a strategy or a code attribute, so the PARTLY clause is not met. The interpretation note is logged: "only one half" means both halves apply to the same object.

**Would change it:** a paper, or the full text of an ICLR 2027 submission, that applies interchange/DAS to algorithm or strategy choice and scores the generated outputs.

### Flag B (E): PARTLY FIRED

- **Weight-only quantization only, in the published record.** "We systematically study activation steering under weight-only quantization (INT8 and NF4) across four open-weight 7–9B models and two behavioral targets" and "Activations remain in FP16/BF16 throughout the forward pass" [8]. This is exactly the PARTLY clause.
- **Two ICLR 2027 submissions on precision and steering effects.**
  - "Preserving standard model quality or direction-level representation similarity does not guarantee that the intervention effect is preserved" [9] (desk-rejected).
  - "We study steering compatibility with the intervention layer, direction, and strength held fixed across full-precision and quantized models" [10].
  - Their abstracts do not say whether activations are quantized. The PDFs (openreview.net/pdf and api2 attachment) returned HTTP 403.
- **FP8 W8A8 appears only for non-determinism.** It is studied "using BF16, GPTQ, FP8 weight-and-activation quantization, and FP8 KV-cache quantization" for batch-context non-determinism, with no perturbations [11].
- **Readouts change under quantization.**
  - Patching [58, 59].
  - SAE features [60].
  - Probes under numeric formats [61].

**Open part:** activation quantization combined with the effect size of *random* perturbations, against bf16 on the same directions.

**Would change it:** if the full text of either flag-B submission includes W8A8/FP8 activation quantization, B FIRES. It would be a contemporaneous submission about learned steering directions, not random pushes.

### Flag C (N): FIRED, as the planner's pre-check predicted

From the NLA paper [1]:

- "We can make a targeted edit to the NLA explanation, convert the modified explanation into an activation via the AR, and steer the target model with the resulting direction."
- "We then steer with this direction at the newline token only, at the layer the NLA is trained on."
- "We note that steering is only successful roughly 50% of the time and the completions are not always clean."
- Its rewards case: "by editing an explanation and reconstructing both the original and edited versions with the AR, we obtain a steering vector from their difference."

Kin under the "similar verbaliser" clause:

- LatentQA: "The trained decoder also enables control by providing a differentiable loss to steer activations towards" [2].
- SelfIE: "We propose Supervised Control, which allows editing open-ended concepts while only requiring gradient computation of individual layer" [3].
- Dreaming Vectors (grey literature) [5].

Patchscopes (92d source 88 [62]) is readout-only: no steer/control match in v4.

### Flag D (P5): PARTLY FIRED

- **Per-sample activation noise for diversity is a saturated lane** (92c sources 15, 14, 16, 52 [28, 29, 30, 63]).
- **Latent-code sampling without a variable fitted inside a frozen LM:**
  - LP-BD: "before a block is decoded, a small conditional flow samples a low-dimensional plan given" a context [31].
  - PPLR: "current latent models remain largely deterministic, capturing only a single reasoning trajectory rather than modeling a distribution over" several trajectories [32].
  - SVP [33].
- **Closest work with a fitted variable:** Random Choice in LMs. "one direction acts as a switch into the random-choice mode, whereas a separate direction shapes the resulting answer distribution", and "This decomposition enables a mechanism-guided intervention that improves sampling without task-specific gradient training" [34]. Its abstract does not say the variable is resampled once per generation, and its object is single-item random choice.

## 5. Table 92e

Abbreviations:
- Status: V = VERIFIED (full text); VA = VERIFIED-ABSTRACT (OpenReview API record); VB = VERIFIED-BLOG; VR = VERIFIED-README.
- Contemporaneity: c = contemporaneous (ICLR 2027 submission); c4 = arXiv v1 after 2026-06-22; pub = published or older preprint.
- Quote ids (e.g. N-1) point to evidence/quotes_iter6.jsonl.

### P1: a low-rank causal PLAN variable, localized by interchange/DAS, decides which algorithm Qwen3-8B writes (validated by generation)

| Row | Neighbour (venue, version, v1, tag) | Verified quote(s) (id; locator; status) | Relation | Lane verdict | What this run adds | Reviewer baseline implied |
|---|---|---|---|---|---|---|
| 92e-P1-1 | DAS: Geiger, Wu, Potts, Icard, Goodman, CLeaR 2024 (PMLR 236), arXiv v4, v1 2023-03-05, pub [13, 64]; Boundless DAS, Wu et al., NeurIPS 2023, v3 [39] | "existing causal abstraction methods have two major limitations: they require a brute-force search over alignments [...]" (P1-1; Abstract; V). "We apply Boundless DAS to the Alpaca model (7B parameters), which, off the shelf, solves a simple numerical reasoning problem." (P1-3; Abstract; V) | method the claim uses | PARTLY OCCUPIED (method) | object = algorithm choice in code; validation by tests on emitted programs; Sutter-style controls | DAS with a declared rotation rank, against Boundless DAS |
| 92e-P1-2 | MIB: Mueller et al., ICML 2025, v2, v1 2025-04-17, pub [14] | "For causal variable localization, we find that the supervised DAS method performs best, while SAE features are not better than neurons, i.e., non-featurized hidden vectors." (P1-4; Abstract; V) | control the claim must meet (method ordering) | n/a | n/a | report neuron and SAE-feature arms beside DAS (MIB ordering) |
| 92e-P1-3 | CDAS: Bao et al., ICLR 2026, v2, v1 2026-02-05, pub [15] | "While we adopt the core mechanism of DAS, distributed interchange intervention (DII) [...] we introduce a novel distribution matching objective tailored for the steering task by aligning intervened output distributions with counterfactual distributions." (P1-5; Sec. 1; V) | occupies the method+criterion pair (rubric 2.5) on a non-plan attribute (refusal, CoT backdoor) | PARTLY OCCUPIED | a plan object (algorithm choice), route-derived predictions, random/shuffled controls | a CDAS-style distribution-matching DAS arm |
| 92e-P1-4 | Programmable Semantic Interventions, ICLR 2027 submission, c [65] | "a low-rank activation subspace learned so that interchanging it moves the model's answer the way the program declares." (P1-6; abstract; VA) | adjacent (rubric 1.5) | — | generation-validated plan object | PSI-style declared-program alignment |
| 92e-P1-5 | Finding Algorithms in Neural Networks (DAS vs transfer), ICLR 2027 submission, c [57] | "We find that, on toy arithmetic and vision tasks, the algorithms identified by DAS and TLA mostly agree" (P1-7; abstract; VA) | adjacent (1.5); supports declaring the map class (non-linear DAS needed in vision) | — | algorithm identity in a code LLM, checked by generation | linear vs non-linear map classes |
| 92e-P1-6 | Causal Syntax Circuits in CodeLMs, Kumar et al., NeurIPS 2026 workshop, v1 2026-10-14, c4 [17] | "Code models write Python when the prompt does not say which language to use. We ask a mechanistic question about that habit: is it produced by a small, findable group of components inside the model?" (P1-8; Abstract; V) | adjacent (1.5): a code attribute that is not the algorithm; next-token readout | — | algorithm (not language); low-rank DAS; generation | random-control significance test, as there |
| 92e-P1-7 | Steering LLM Coding Behaviors with Concept Vectors, ICLR 2027 submission, c [18] | "Adding them after the first sampled token changes held-out outputs, but effects depend on model and layer, strong scaling harms validity and correctness, and axis specificity remains unresolved without matched-norm causal controls." (P1-9; abstract; VA) | adjacent (2.0) | — | algorithm-level object with matched-norm controls | a difference-in-means direction for the algorithm, with matched-norm random controls |
| 92e-P1-8 | Before Reasoning Begins (Qwen3-8B, final prompt position, SAE targets), ICLR 2027 submission, c [20] | "This pipeline yields a compact set of 23 intervention targets in Qwen3-8B." (P1-10; abstract; VA). "We use this functionally aligned contrast to screen sparse autoencoder features at the final prompt position" (P1-11; abstract; VA) | adjacent (2.0): same model and site; object is reasoning, not algorithm | — | which algorithm (not whether reasoning happens); DAS rather than SAE suppression | layer-count-matched random null interventions |
| 92e-P1-9 | Committed Before Reasoning, Jo, v1 2026-07-17, c4 [66] | "Chat models sometimes commit to an answer and then produce reasoning that justifies the commitment rather than deriving it" (P1-12; Abstract; V) | supports (pre-generation commitment in Qwen3-8B) | — | — | — |
| 92e-P1-10 | Random Choice in LMs: linear choice state, ICLR 2027 submission, c [34] | "one direction acts as a switch into the random-choice mode, whereas a separate direction shapes the resulting answer distribution." (P1-13; abstract; VA) | adjacent (2.0) | — | code-algorithm object | switch-vs-distribution decomposition |
| 92e-P1-11 | Detecting and Characterizing Planning in LMs, Nainani et al., v1 2025-08-25, anchor [67] | "We apply this pipeline to both base and instruction-tuned Gemma-2-2B models on the MBPP code generation benchmark and a poem generation task where Claude 3.5 Haiku was previously shown to plan." (P1-14; Abstract; V) | adjacent (1.5); contradicts in part (the same abstract reports that planning is not universal) | — | algorithm-level plan, not a future-token plan | a planning-vs-improvisation criterion |
| 92e-P1-12 | Algorithmic Core Extraction, Schiffman, v2, v1 2026-02-26, pub [68] | "extracting algorithmic cores, compact subspaces that are necessary and sufficient for a task and that recur across independently trained models." (P1-15; Abstract; V) | adjacent (1.0) | — | choice among algorithms, not a task core | — |
| 92e-P1-13 | Invisible Lottery (algorithm choice in code moved by cues), ICML 2026: see 92c source 30 [16] | see 92c (not re-verified) | adjacent (2.0): object occupied behaviourally | — | internal causal variable | prompt-cue baseline |
| 92e-P1-CTRL-1 | Sutter, Minder, Hofmann, Pimentel, NeurIPS 2025 Spotlight, v2, v1 2025-07-11, pub [69] | "on an experiment using randomly initialised language models, our alignment maps reach 100% interchange-intervention accuracy on the indirect object identification task." (CTRL-1; Abstract; V) | control the claim must meet | — | declared linear map class and rank; random-init or random-rotation control | fit the same map on a randomly initialized Qwen3-8B, and with shuffled labels |
| 92e-P1-CTRL-2 | Makelov, Lange, Geiger, Nanda, ICLR 2024, v2, pub [70, 71] | "this effect may be achieved by activating a dormant parallel pathway leveraging another subspace that is causally disconnected from model outputs." (CTRL-2; Abstract; V) | control the claim must meet | — | nullspace/row-space decomposition of the patch | check that the patched subspace is not causally disconnected |
| 92e-P1-CTRL-3 | Reply: Wu, Geiger, Huang, Arora, Icard, Potts, Goodman, v1 2024-01-23 [72] | "their method of discovering "illusions" can reject explanations they consider "non-illusory"." (CTRL-4; Abstract; V) | cite with CTRL-2 | — | — | — |
| 92e-P1-CTRL-4 | Divergent representations: Grant et al., v5 (2026-04-22), v1 2025-11-06 [73] | "minimizing divergence magnitude does not guarantee elimination of hidden pathways; it only reduces the risk surface." (CTRL-6; Sec. 5; V) | control | — | on-distribution check of patched states | report divergence of the intervened states |
| 92e-P1-CTRL-5 | Right Answer, Wrong Mechanism, v2, v1 2026-09-30, c4 [74] | "No method currently tells the two cases apart." (CTRL-7; Abstract; V) | control (do not rely on distance checks alone) | — | — | planted-pathway or clamp test |
| 92e-P1-CTRL-6 | Curse of Multiple Mediators [75]; Many Circuits, One Mechanism (TMLR 2026) [76]; identification-assumptions position [77] | "we find that the NIE does not solely capture the causal effect through the specific component." (CTRL-8; V). "The discovered circuits appear specialized by frequency when compared structurally, but functional and representational analyses show no reliable evidence of corresponding differences." (CTRL-9; V) | controls | — | — | report interaction effects, cross-condition transfer and identification assumptions |

### P2: the plan subspace mediates which random pushes switch the algorithm

| Row | Neighbour | Verified quote(s) | Relation | Lane verdict | What this run adds | Reviewer baseline |
|---|---|---|---|---|---|---|
| 92e-P2-1 | Before the First Token (causal response-length subspace; parallel/orthogonal decomposition of interventions), ICLR 2027 submission: see 92c source 64 [40] | see 92c source 64 (not re-verified) | adjacent (nearest) | ADJACENT-ONLY | prediction of *random*-push effects on *algorithm* choice from projection onto the plan subspace | parallel/orthogonal decomposition of each push |
| 92e-P2-2 | AJR [41]; ASTEER [78]; decodability is not actionability [79] | see 92c (not re-verified) | adjacent | — | — | Jacobian-readout predictor of push effects |
| 92e-P2-3 | DecodeShare, v1 2026-05-21, pub [42] | "disturbing the discovered shared subspace degrades decision performance far more than disturbing either a prefill-derived or random subspace under the same intervention budget." (P2-2; Abstract; V) | adjacent (1.5) | — | random pushes classified by plan-subspace energy | matched-budget random-subspace control |
| 92e-P2-4 | What Does Activation Steering Control?, v1 2026-08-24, c4 [43] | "A low-rank output-sensitive component containing 15.4% of the direction's squared norm retains 96.3% of this effect." (P2-7; Abstract; V) | supports a projection account (1.0) | — | — | report the share of each push's norm inside the plan subspace |
| 92e-P2-5 | Jailbreak success coordinate outside the refusal subspace, ICLR 2027 submission, c [44] | "whether success is decodable before generation from a coordinate outside an evaluated refusal subspace, whether intervention on that coordinate moves the behavior" (P2-3; abstract; VA) | contradicts in part: the outcome-deciding coordinate can lie outside an evaluated subspace | — | — | test the orthogonal complement as well |
| 92e-P2-6 | Before Reasoning Begins (targeted vs random-null) [20]; Latent Planning Emerges with Scale, ICLR 2026 [27] | "same-size, layer-count-matched random null interventions reduce accuracy by only" (P2-5; VA). "even the less-successful Qwen-3 4B-8B have nascent planning mechanisms." (P2-4; Abstract; V) | adjacent / supports | — | — | random-null arm |
| 92e-P2-8 | On the Non-Identifiability of Steering Vectors, v4, v1 2026-02-06, pub (found by a supplementary search) [80] | "We show that, under white-box single-layer access, steering vectors are fundamentally non-identifiable due to large equivalence classes of behaviorally indistinguishable interventions." (P2-8; Abstract; V) | supports a subspace-level (not direction-level) account (1.0) | — | — | report plan claims at subspace level; orthogonal-perturbation control |
| 92e-P2-7 | Steering off Course, v1 2025-04-06, anchor [81]; Tele-Lens (ICML 2026) [82] | "Our analysis demonstrate fundamental flaws in the assumptions underlying these methods, challenging their reliability as scalable steering solutions" (P2-1; Abstract; V) | caution | — | — | per-sample effect distributions |

### P3: the plan is discrete under interpolation

| Row | Neighbour | Verified quote(s) | Relation | Lane verdict | What this run adds | Reviewer baseline |
|---|---|---|---|---|---|---|
| 92e-P3-1 | Park, Choe, Jiang, Veitch, ICLR 2025 oral, v3, anchor [45] | "This allows us to immediately formalize the representation of categorical concepts as polytopes in the representation space." (P3-1; Abstract; V) | supports (categorical geometry) | ADJACENT-ONLY | an interpolation sweep between plan centroids, with the emitted algorithm labelled at each step | polytope/simplex geometry of the plan centroids |
| 92e-P3-2 | Engels et al., ICLR 2025, v3 (retitled "...One-Dimensionally Linear"), anchor [46] | "we explore whether some language model representations may be inherently multi-dimensional." (P3-2; Abstract; V) | adjacent (2.0): interventions along circular features | — | discreteness vs continuity of a code plan | a test for irreducible multi-dimensional features |
| 92e-P3-3 | Manifold Steering (ICML 2026 MI-workshop spotlight): see 92c source 44 [47] | see 92c (not re-verified) | adjacent | — | — | geodesic vs linear paths |
| 92e-P3-4 | Prolepsis, Jacopin, v2, v1 2026-04-16 [24]; Random Choice switch [34]; manifold vs linear steering (ICLR 2027 submission) [83] | "We introduce prolepsis: a transformer commits early, task-specific attention heads sustain the commitment, and no layer corrects it." (P3-3; V). "show that both a linear direction and a low-dimensional manifold structure align with it." (P3-4; VA) | adjacent | — | — | linear vs manifold interpolation |

### P4: temperature leaves the plan untouched while state noise moves it, at matched KL

| Row | Neighbour | Verified quote(s) | Relation | Lane verdict | What this run adds | Reviewer baseline |
|---|---|---|---|---|---|---|
| 92e-P4-1 | departure-matched decoding (ICLR 2027 submission, "Rethinking Activation Steering for Mathematical Reasoning"): 92c source 66 [48]; Peeperkorn [49]; AdapT [84]; Gumbel counterfactuals [85]; Beneath the Diff [86] | see 92c (not re-verified) | adjacent; departure-matched decoding is the reviewer baseline | ADJACENT-ONLY | plan-level (algorithm) readout of temperature vs state noise at matched KL | decoding matched to the perturbation's departure from greedy |
| 92e-P4-2 | Forking Paths, Bigelow et al., v1 2024-12-10, anchor [50] | "We hypothesize that there exist key forking tokens, such that re-sampling the system at those specific tokens, but not others, leads to very different outcomes." (P4-1; Abstract; V) | adjacent (2.0) | — | — | forking-token resampling baseline |
| 92e-P4-3 | HELIX (4-bit Granite; temperature plus steering), v1 2026-02-06 [87]; Predicting Future Behaviors, ICLR 2027 submission [51] | "Quantized language models face a fundamental dilemma: low sampling temperatures yield repetitive, mode-collapsed outputs, while high temperatures [...] cause trajectory divergence and semantic incoherence." (P4-2; V). "We apply a forking-paths-style analysis to behavioral evaluations and find that as generation progresses, LRMs define evolving distributions over behavioral outcomes." (P4-3; VA) | adjacent | — | — | — |

### P5: resampling the plan as a diversity knob (flag D)

| Row | Neighbour | Verified quote(s) | Relation | Lane verdict | What this run adds | Reviewer baseline |
|---|---|---|---|---|---|---|
| 92e-P5-1 | STARS (ICLR 2026), Noise Steering, REI, NC-GRPO, 2606.10302, Diversity Without Discovery: 92c sources 15, 14, 16, 52, 31, 63 [28, 29, 30, 63, 54, 88] | see 92c (not re-verified) | occupies the method family (activation noise for diversity) | PARTLY OCCUPIED | resampling a *fitted, causally localized* plan variable | matched-dose activation noise; text-level plan samplers (IFG, PlanSearch) [89, 90] |
| 92e-P5-2 | Random Choice in LMs, ICLR 2027 submission, c [34] | "This decomposition enables a mechanism-guided intervention that improves sampling without task-specific gradient training." (P5-1; abstract; VA) | adjacent (2.0); closest to flag D | — | per-generation resampling for algorithm diversity | distribution-direction intervention |
| 92e-P5-3 | LP-BD [31]; PPLR [32]; SVP [33] (ICLR 2027 submissions, c) | "before a block is decoded, a small conditional flow samples a low-dimensional plan given" (P5-2; VA). "which diversifies latent trajectories by randomly rescaling coefficients in the fixed SVD basis of a weight matrix." (P5-4; VA) | adjacent (flag D partly) | — | a frozen LM; the variable is fitted, not trained | — |
| 92e-P5-4 | Latent Plan Transformer, v4, anchor (venue not stated in the arXiv record) [91] | "We introduce the Latent Plan Transformer (LPT), a novel model that leverages a latent variable to connect a Transformer-based trajectory generator and the final return." (P5-5; Abstract; V) | adjacent | — | — | — |

### N: reading and editing the plan in words with NLAs (flag C)

| Row | Neighbour | Verified quote(s) | Relation | Lane verdict | What this run adds | Reviewer baseline |
|---|---|---|---|---|---|---|
| 92e-N-1 | Fraser-Taliente, Kantamneni, Ong et al., "Natural Language Autoencoders Produce Unsupervised Explanations of LLM Activations", Transformer Circuits, published May 7, 2026, pub [1] | "We can make a targeted edit to the NLA explanation, convert the modified explanation into an activation via the AR, and steer the target model with the resulting direction." (N-1; Planning in Poetry; V). "We note that steering is only successful roughly 50% of the time and the completions are not always clean." (N-3; V) | OCCUPIES the method (rubric 2.5) | OCCUPIED (method) | replication in a new setting: algorithm choice in code, Qwen2.5-7B-Instruct L20, text-only judges, an unrelated-word edit, a matched-norm random displacement | the paper's own newline-only steering protocol and success rate |
| 92e-N-2 | same paper, Reasoning about Rewards [1] | "by editing an explanation and reconstructing both the original and edited versions with the AR, we obtain a steering vector from their difference." (N-4; V) | occupies | — | — | AR-difference steering vector, norm-matched |
| 92e-N-3 | same paper, Method and Limitations [1] | "NLA explanations can contain claims about the target model's input context that are verifiably false." (N-5; V). "with the NLAs evaluated in this paper reaching 0.6-0.8 FVE" (N-6; V) | control the claim must meet (confabulation) | — | — | confabulation audit of plan claims |
| 92e-N-4 | Released checkpoints: kitft README [92]; HF card [93]; nla_meta.yaml [94]; TransformerLens issue #1884 [95] | "Qwen2.5-7B-Instruct \| 20 / 28 \| 3584" (N-9; VR). "Each checkpoint ships an `nla_meta.yaml` sidecar [...] load those, never hardcode them." (N-11; VR). "In-distribution fve_nrm: 0.752" (N-13; VR) | design facts | — | — | load nla_meta.yaml injection settings |
| 92e-N-5 | LatentQA, Pan, Chen, Steinhardt, ICLR 2026, v2 [2]; SelfIE, ICML 2024, PMLR 235 [3, 4] | "The trained decoder also enables control by providing a differentiable loss to steer activations towards" (N-15; V). "We propose Supervised Control, which allows editing open-ended concepts while only requiring gradient computation of individual layer." (N-17; V) | occupies the "similar verbaliser" clause of flag C (rubric 2.0 each) | — | — | decoder-loss steering arm |
| 92e-N-6 | Activation Oracles, v2 [96]; Dreaming Vectors (LessWrong) [5] | "we study Activation Oracles (AOs): models trained to answer arbitrary natural-language questions about LLM activations." (N-19; V) | readout kin / steering kin (grey literature) | — | — | — |
| 92e-N-7 | Sood, Substack, 2026-08-18, c4 [97]; Auditing the Auditor, ICLR 2027 submission, c [52] | "We audit two released NLA checkpoints and find that the readout reports what pressure was applied and what the model answered, but not whether the pressure changed that answer." (N-21; VB). "under preregistered controls: a wrong-activation (shuffled) control, a visible-text baseline, a blinded judge, and supervised readability probes." (N-22; VA) | control set the readout must meet | — | — | shuffled-activation control; visible-text baseline; blinded judge |
| 92e-N-8 | Train the Model, Not the Reader, Dingeto, v2, v1 2026-07-22, c4 [6] | "On a released Qwen-2.5-7B verbalizer, explanations reconstruct well above chance while as few as [...] of their specific claims are ones the reconstruction depends on. The score therefore tracks the input's gist, not its specific" (N-24; Abstract; V) | contradicts in part: an edited claim may not move the AR output | — | measure the AR displacement caused by the edit before steering | claim-flip reconstruction test |
| 92e-N-9 | Colombian identity with NLA, v1 2026-07-23, c4 [98] | "We use Natural Language Autoencoders (NLA) to verbalize residual-stream activations from layer 20 across four positional quartiles per prompt." (N-25; V) | readout replication on the same checkpoint | — | — | — |
| 92e-N-10 | Community Qwen3-8B NLAs: nanoNLA [99, 100]; EasyNLA [101] | "This repo hosts the AV for Qwen3-8B @ layer 24." (N-26; VR). "On Qwen3-8B (layer 24) the default config reaches ~70% held-out FVE in ~3–4 hours on 4×H200." (N-28; VR) | corrects iteration 5's "NLA unavailable for Qwen3-8B" | — | — | an optional Qwen3-8B arm (unofficial; faithfulness disclaimer) |
| 92e-N-11 | Planning or Improvisation?, Jacopin, v1 2026-09-16, c4 [7] | "C2 and C3 are not recovered by any probe: a census of every active feature finds no rhyme-anticipating enrichment at the newline" (N-29; Abstract; V) | contradicts in part (no newline-resident plan in small open models) | — | — | site sweep (newline vs final prompt token) |
| 92e-N-12 | Measuring Activation Control [102]; Understanding Confabulation [103] | "this level of control can evade activation-based monitoring methods (including linear probes, natural language autoencoders, activation oracles, and the Jacobian lens), albeit imperfectly." (N-30; V) | context | — | — | — |

### S: the plan in Gemma Scope 2 SAE and transcoder features

| Row | Neighbour | Verified quote(s) | Relation | Lane verdict | What this run adds | Reviewer baseline |
|---|---|---|---|---|---|---|
| 92e-S-1 | Gemma Scope 2: announcement 22 Dec 2025 [104]; technical report [105]; HF card [106] | "every SAE trained on a PT model has a corresponding version finetuned for IT models" (S-1; VB). "we do not train IT SAEs from scratch: we initial [...] from the corresponding PT SAEs and finetune on the rollout-derived datasets." (S-3; V) | design facts | — | — | report the IT-vs-PT dictionary used |
| 92e-S-2 | circuit-tracer README [25]; Qwen-3 transcoders (Hanna et al.) [26, 27] | "Gemma-3 PLTs (originally from GemmaScope-2) can be found here for models of size 270M, 1B, 4B, 12B, and 27B, PT and IT. These require using the `nnsight` backend." (S-5; VR). "Qwen-3 PLTs: for Qwen-3 0.6B, 1.7B, 4B, 8B, and 14B" (S-6; VR) | design fact: Qwen3-8B transcoders exist, so a reviewer may ask why S uses Gemma | — | — | run S on the Qwen3-8B PLTs, or justify Gemma |
| 92e-S-3 | AxBench, v3, v1 2025-01-28 [22]; rebuttal, v1 2026-05-29 [23] | "For steering, we find that prompting outperforms all existing methods, followed by finetuning." (S-10; V). "We find that Sparse Autoencoders can, in fact, perform close to on par with the reference LoRA performance on the AxBench benchmark, when features are selected and labelled with our supervised pipeline." (S-12; V) | prior the claim must meet | — | — | difference-in-means and prompting arms |
| 92e-S-4 | SAE-Steering, Fang et al., ACL 2026 Main, v2 [21]; Galichin et al. [107] | "To identify the few strategy-specific features from the vast pool of SAE features, we propose SAE-Steering, an efficient two-stage feature identification pipeline." (S-13; V). "We compare SAE-Steering with three representative control methods [...] Think Intervention (Wu et al., 2025), which inserts human-crafted instructions into the middle of the reasoning process" (S-13b; Sec. 4.1; V) | OCCUPIES the method on a non-code strategy (rubric 2.5) | PARTLY OCCUPIED | algorithm choice in code; Gemma Scope 2; transcoder attribution | SAE-Steering-style logit-recall feature selection |
| 92e-S-5 | Do SAEs Identify Reasoning Features? (Gemma Scope 2), ICML 2026, v7 [53] | "use SAEs from the GemmaScope-2 release (McDougall et al., 2025), each with 16,384 features trained on residual stream activations." (S-15; V). "A small steering study yields minimal changes on the evaluated benchmarks." (S-16; V) | contradicts in part | — | — | token-injection falsification of candidate features |
| 92e-S-6 | Prolepsis [24]; Latent Planning Emerges with Scale [27] | "Planning is invisible to six residual-stream methods; among those tested, only CLT-based steering succeeds." (S-17; V) | adjacent; counter-evidence to the AxBench prior for plans | — | — | CLT/PLT arm against residual difference-in-means |
| 92e-S-7 | SAE Interventions are Unreliable [108]; variable roles in code LMs (ICLR 2027 submission) [109]; attribution-graph caveat [110] | "the clamp may block one visible route to a behavior without eliminating the behavior itself." (S-18; V). "residual probes outperform individual SAE features and tested lexical baselines" (S-19; VA). "we've found that our attribution graphs provide us with satisfying insight for about a quarter of the prompts we've tried" (S-20; V) | cautions | — | — | probe baseline; post-intervention recovery check |

### E: FP8 W8A8 activation rounding inflates the apparent effect of activation perturbations (flag B)

| Row | Neighbour | Verified quote(s) | Relation | Lane verdict | What this run adds | Reviewer baseline |
|---|---|---|---|---|---|---|
| 92e-E-1 | Steering Under Compression, Bhandari and Wade, v1 2026-09-06, c4 [8] | "Activations remain in FP16/BF16 throughout the forward pass." (E-2; Sec. 3; V). "demonstrating that compression can dominate the steering intervention." (E-4; V) | adjacent (1.5); flag B partly | ADJACENT-ONLY (published) | activation quantization; random perturbations; matched bf16 control | iso-effect comparison at matched behavioural effect |
| 92e-E-2 | Stable Directions, Different Effects, ICLR 2027, desk rejected, c [9] | "Preserving standard model quality or direction-level representation similarity does not guarantee that the intervention effect is preserved." (E-5; VA). "Intervention effects can change even when directions remain strongly aligned" (E-6; VA) | partly occupies the general claim (contemporaneous) | PARTLY OCCUPIED (contemporaneous) | random pushes; FP8 W8A8 named; noise-floor account | a first-order local-sensitivity predictor |
| 92e-E-3 | Activation Steering under Low-Bit Quantization, ICLR 2027 submission, c [10] | "We study steering compatibility with the intervention layer, direction, and strength held fixed across full-precision and quantized models." (E-7; VA) | adjacent (1.0) | — | — | hold layer, direction and strength fixed |
| 92e-E-4 | Quantization Modulates Batch-Context Non-Determinism, ICLR 2027 submission, c [11] | "using BF16, GPTQ, FP8 weight-and-activation quantization, and FP8 KV-cache quantization." (E-9; VA) | mechanism neighbour (noise floor) | — | perturbation effect sizes against the FP8 noise floor | same-batch-context repeat runs |
| 92e-E-5 | PRISM, v1 2026-10-14, c4 [111] | "we introduce PRISM, a framework for evaluating the transfer of activation interventions across precision, languages, and scales." (E-10; V) | adjacent (NF4) | — | — | — |
| 92e-E-6 | Readouts under quantization: Findings ACL 2026 [58]; [59]; [60]; AACL 2025 [112]; TrustNLP 2026 [113] | "These results show that behavioral metrics alone are insufficient evidence that full-precision interpretability findings transfer to quantized models, motivating feature-level audits of compression." (E-13; V) | flag B partly (readouts, not perturbation effect sizes) | — | — | — |
| 92e-E-7 | Precision-induced divergence: TMLR 2026 [114]; [115, 116]; [117]; [61] | "the same model, prompt, and decoding algorithm produce different outputs in BF16 versus FP16 on identical hardware." (E-17; V). "under bfloat16 precision with greedy decoding, a reasoning model like DeepSeek-R1-Distill-Qwen-7B can exhibit up to 9% variation in accuracy and 9,000 tokens difference in response length due to differences in GPU count, type, and evaluation batch size." (E-18; V) | supports the mechanism (rounding flips trajectories) | — | — | a zero-norm (unperturbed) re-run under the same engine |
| 92e-E-8 | Mechanism sources: LLM.int8() [118]; SmoothQuant [119]; massive activations [120]; FP8 formats [121]; llm-compressor FP8_DYNAMIC [12] | "SmoothQuant smooths the activation outliers by offline migrating the quantization difficulty from activations to weights with a mathematically equivalent transformation." (E-21; V). "Static, per-channel quantization on the weights [...] Dynamic, per-token quantization on the activations" (E-24; VR) | mechanism background | — | — | per-token-scale ablation |

## 6. Permitted wording (dated 2026-10-22; evidence: evidence/flags_iter6.json, evidence/quotes_iter6.jsonl)

- **P1.**
  - Permitted: "To our knowledge (search dated 2026-10-22), the first interchange/DAS localization of *which algorithm* a code LLM will write that is validated by scoring the generated programs, with Sutter-style map-class, random-initialization and shuffled-label controls."
  - Forbidden: "first causal localization of a plan", "new method", and "first DAS-based steering" (CDAS [15]).
  - Cite DAS [13], MIB [14], CDAS [15], Sutter [69], Makelov with the reply [70, 72], divergent representations [73], and the contemporaneous Before Reasoning Begins [20].
- **P2.**
  - Permitted: "we predict which random pushes switch the algorithm from their projection onto the plan subspace".
  - Forbidden: "first causal planning subspace" (Before the First Token [40]).
  - Frame the parallel/orthogonal decomposition as following [40].
- **P3.**
  - Permitted: "the plan behaves discretely under interpolation in our setting".
  - Forbidden: "categorical concepts are discrete" as a new finding ([45]).
- **P4.**
  - Permitted: "at matched KL, temperature did not move the plan while state noise did".
  - The departure-matched decoding baseline [48] must be run or named.
  - Forbidden: "temperature is not the creativity knob" as a new claim ([49]).
- **P5.**
  - Permitted: "resampling a fitted, causally localized plan variable"; activation noise for diversity is prior art [28, 29, 30].
  - Forbidden: "first latent diversity knob" and "new diversity method".
- **N.**
  - Permitted: "we replicate the NLA edit-and-steer protocol [1] on algorithm choice in code, with Qwen2.5-7B-Instruct and new controls".
  - Forbidden: "first", "new method", "we introduce editing explanations to steer".
- **S.**
  - Permitted: "Gemma Scope 2 SAE/transcoder features for an algorithm-choice plan in code, compared against difference-in-means and prompting".
  - Forbidden: "first SAE steering of strategies" ([21]).
  - State why Gemma Scope 2 is used when Qwen-3 PLTs exist [25].
- **E.**
  - Permitted: "we find that activation-quantized (FP8 W8A8, dynamic per-token) inference inflates the apparent effect of random activation perturbations relative to bf16".
  - Cite the weight-only [8] and contemporaneous [9, 10, 11] work.
  - Forbidden: "first to show quantization changes steering effects".

## 7. Reviewer baselines (implied by the neighbours)

1. **P1.**
   - DAS with a declared linear rotation and rank, fitted also on a randomly initialized model and with shuffled labels [69].
   - Neuron and SAE-feature arms [14].
   - A CDAS-style distribution-matching arm [15].
   - A difference-in-means direction with matched-norm random controls [18].
   - A prompt-cue baseline [16].
2. **P2.**
   - Parallel/orthogonal decomposition [40].
   - A matched-budget random subspace [42].
   - A test of the orthogonal complement [44].
3. **N.**
   - Shuffled-activation and visible-text controls, plus a blinded judge [52].
   - A claim-flip reconstruction test [6].
   - The paper's newline-only protocol [1].
4. **S.**
   - Difference-in-means and prompting [22].
   - A supervised SAE pipeline [23].
   - SAE-Steering feature selection [21].
   - CLT/PLT steering [24].
5. **E.**
   - A bf16 re-run of the same directions.
   - A zero-norm FP8 re-run (noise floor) [11, 114].
   - A weight-only (W8A16) arm [8].
   - A per-token-scale ablation [12].
6. **P4/P5.**
   - Departure-matched decoding [48].
   - IFG and PlanSearch [89, 90].

## 8. Departures (from the plan) and limitations

1. **Single screener.** O/I/C calls rest on one judgment, with every decisive sentence logged. Borderline calls:
   - CDAS's O = 0.5 for refusal;
   - SAE-Steering's I = 1;
   - E-row verdicts that rest on abstracts.
2. **ICLR 2027 rows are abstract-only.** OpenReview PDFs and api2 attachments returned HTTP 403, and the forum HTML is a browser check. Flag B and flag D both hinge on such abstracts.
3. **Forward citations are thin.** They come from Semantic Scholar only, and the NLA paper is not indexed there (E6 used instead), so recent follow-ups may be undercounted.
4. **Inherited quotes were not re-verified.** Only versions were rechecked, for 8 flag-critical references.
5. **The prior audits' tools were reused.** They were readable on disk although the plan assumed otherwise; they were copied into tools/ and adapted.
6. **Round 3 was run.** It found no new hit at or above 1.5.
7. **E6 timing.** E6 calls were logged within minutes of being made, with the logging time as the timestamp.
   Three supplementary general-web searches outside the frozen strings (round SUPP in the search log) looked for full-text versions of the abstract-only flag-B and flag-D neighbours. None was found. They surfaced one more P2-adjacent paper [80].
8. **No full-text checks for the method details in ICLR 2027 abstracts.** For example, whether "precision changes" includes activation quantization.

## 9. Corrections (evidence/corrections_iter6.jsonl)

- **NLA.**
  - Citation and date: "Fraser-Taliente, Kantamneni, Ong et al.", published May 7, 2026 [1].
  - The paper already edits and steers a plan, so N is a replication.
  - 4 base models × (AV, AR) = 8 checkpoints [92].
  - Qwen3-8B has no *official* NLA checkpoint, but community reimplementations exist at layer 24 [99, 101]. friendli.ai/models/ceselder/nanoNLA is a hosting listing of that AV.
- **Gemma Scope 2.** Announced 22 Dec 2025; IT SAEs are initialized from the PT SAEs and finetuned [104, 105].
- **circuit-tracer.**
  - Gemma-3 PLTs come from GemmaScope-2 and need the nnsight backend.
  - Qwen-3 PLTs, including 8B, are by Hanna et al. The card names no checkpoint; the ICLR 2026 paper that uses them calls its Qwen-3 models instruction-tuned [25, 26, 27].
- **Sutter et al.** NeurIPS 2025 Spotlight. The phrase "any neural network can be mapped to any algorithm" does not occur in v2; use the 100% IIA sentence [69].
- **Makelov et al.** ICLR 2024; the arXiv comment names a NeurIPS 2023 workshop [71].
- **SelfIE.** ICML 2024, PMLR 235:7373-7388 [4].
- **DAS.** CLeaR 2024, PMLR 236 [64].
- **Engels et al.** The current title is "Not All Language Model Features Are One-Dimensionally Linear" [46].
- **2506.09501.**
  - v1 is titled "Give Me FP32 or Give Me Death? Challenges and Solutions for Reproducible Reasoning"; v2 is retitled.
  - "up to 9% variation in accuracy" is verified [116, 115].
- **2609.15504.** The current title is "Evaluating Losslessness in Speculative Decoding Under Finite-Precision Inference" (no row).
- **Latent Plan Transformer.** Venue not stated in the arXiv record (v4) [91].
- **AxBench.** Venue not verified here: the arXiv comment is empty.
- **Inherited versions.** No newer arXiv versions for the 8 flag-critical inherited references.

## 10. Confidence and what would change it

- **High confidence (full-text quotes).**
  - Flag C fired.
  - 2609.06473 is weight-only.
  - Gemma Scope 2 and circuit-tracer facts.
  - DAS, MIB, Sutter and Makelov controls.
- **Medium confidence.**
  - Flag A not fired: the search is broad but single-screened, and code-interpretability work moves fast.
  - Flag D partly fired: Random Choice's full text is unread.
- **Low-to-medium confidence on flag B.** It rests on two ICLR 2027 abstracts whose quantization type is unknown. Reading their PDFs once OpenReview access works is the single most valuable follow-up.
- **Contradicting evidence logged.**
  - Planning may be absent or improvised in small open models [67, 7].
  - NLA reconstructions track the gist rather than specific claims [6].
  - SAE reasoning features may be token correlates [53].
  - Steering reliability is questioned [81, 108].

## 11. Follow-up questions

1. **Flag B.** Do the ICLR 2027 submissions "Stable Directions, Different Effects" and "Activation Steering under Low-Bit Quantization" quantize activations (W8A8/FP8) or only weights? Their full texts decide whether flag B fires. Re-read them once the OpenReview PDFs are reachable.
2. **N's causal arm.** On the released Qwen2.5-7B-Instruct L20 NLA, how far does the AR reconstruction move when only the algorithm name in an explanation is edited? The claim-dependence result [6] predicts a small move. Measure this before running the edit-and-steer arm.
3. **Flag A and P1.** Would interchange/DAS on the Qwen3-8B final prompt position find a low-rank variable for algorithm choice? Where does it sit relative to the 23 SAE targets of the contemporaneous Before Reasoning Begins submission [20] and to the Qwen-3 PLTs [25]?



## Sources

[1] [Natural Language Autoencoders Produce Unsupervised Explanations of LLM Activations](https://transformer-circuits.pub/2026/nla/index.html) (Kit Fraser-Taliente, Subhash Kantamneni, Euan Ong; 2026) — Decisive for flag C: edits an NLA explanation of a rhyme plan, reconstructs it with the AR and steers at the newline (about 50% success); a steering vector from the explanation difference in the rewards case; confabulation; FVE 0.6-0.8. (version: HTML (single version); venue: Transformer Circuits Thread (published May 7, 2026); status: VERIFIED; retrieved 2026-10-22; author list truncated to the first names shown by the source)

> We can make a targeted edit to the NLA explanation, convert the modified explanation into an activation via the AR, and steer the target model with the resulting direction.

Locator: Case Studies > Planning in Poetry (N-1; VERIFIED)

> We then steer with this direction at the newline token only, at the layer the NLA is trained on.

Locator: Case Studies > Planning in Poetry (N-2; VERIFIED)

> We note that steering is only successful roughly 50% of the time and the completions are not always clean.

Locator: Case Studies > Planning in Poetry (results) (N-3; VERIFIED)

> by editing an explanation and reconstructing both the original and edited versions with the AR, we obtain a steering vector from their difference.

Locator: Introduction (case-study overview: Reasoning about Rewards) (N-4; VERIFIED)

[2] [LatentQA: Teaching LLMs to Decode Activations Into Natural Language](https://arxiv.org/html/2412.08686v2) (Alexander Pan, Lijie Chen, Jacob Steinhardt; 2024) — LatentQA (Pan, Chen, Steinhardt); cited in rows 92e-N-5. (version: v2; venue: ICLR 2026; project page at https://latentqa.github.io; status: VERIFIED; retrieved 2026-10-22)

> The trained decoder also enables control by providing a differentiable loss to steer activations towards

Locator: Sec. 4, 'Using the decoder for control' (N-15; VERIFIED)

> we demonstrate that the decoder is precise enough to steer the target model to exhibit behaviors unseen during training.

Locator: Abstract (N-16; VERIFIED)

[3] [SelfIE: Self-Interpretation of Large Language Model Embeddings](https://arxiv.org/html/2403.10949v2) (Haozhe Chen, Carl Vondrick, Chengzhi Mao; 2024) — SelfIE (Chen, Vondrick, Mao); cited in rows 92e-N-5. (version: v2; venue: arXiv preprint; status: VERIFIED; retrieved 2026-10-22)

> We propose Supervised Control, which allows editing open-ended concepts while only requiring gradient computation of individual layer.

Locator: Abstract (N-17; VERIFIED)

[4] [SelfIE: Self-Interpretation of Large Language Model Embeddings (PMLR 235 record)](https://proceedings.mlr.press/v235/chen24ao.html) (Haozhe Chen, Carl Vondrick, Chengzhi Mao; 2024) — Venue record: ICML 2024, PMLR 235:7373-7388. (version: proceedings; venue: ICML 2024; status: VERIFIED; retrieved 2026-10-22)

> Proceedings of the 41st International Conference on Machine

Locator: PMLR record (N-18; VERIFIED)

[5] [Dreaming Vectors: Gradient-descented steering vectors from Activation Oracles and using them to Red-Team AOs (LessWrong)](https://www.lesswrong.com/posts/rdhyHtjf3LcZxuQPm/dreaming-vectors-gradient-descented-steering-vectors-from) (2026) — Grey-literature verbaliser-to-steering kin for flag C: steering vectors optimized against an Activation Oracle. (version: post; venue: LessWrong; status: VERIFIED-BLOG; retrieved 2026-10-22)

> Dreaming Vectors: Gradient-descented steering vectors from Activation Oracles and using them to Red-Team AOs

Locator: title (N-20; VERIFIED-BLOG)

[6] [Train the Model, Not the Reader: Decodability Supervision for Verifiable Activation Explanations](https://arxiv.org/html/2607.20379v2) (Hiskias Dingeto; 2026) — Train the Model, Not the Reader (Dingeto); cited in rows 92e-N-8. (version: v2; venue: arXiv preprint; status: VERIFIED; retrieved 2026-10-22)

> of their specific claims are ones the reconstruction depends on. The score therefore tracks the input

Locator: Abstract (N-24; VERIFIED)

[7] [Planning or Improvisation? Stress-Testing the Poetry Planning Site on Open Models and Open Cross-Layer Transcoders](https://arxiv.org/html/2609.18440v1) (Éric Jacopin; 2026) — Planning or Improvisation? (Jacopin); cited in rows 92e-N-11. (version: v1; venue: 17 pages, 3 figures, 8 tables. Code, data and analysis scripts: https://github.com/PCfVW/poetry-planning-site . An earlier version was submitted to the BlackboxNLP 2026 special track on reproducibility and reliability in interpretability analyses; this version adds a rerun composition-horizon experiment (36 runs, 8,640 sampled lines) and a transcoder-free activation-patching test; status: VERIFIED; retrieved 2026-10-22)

> C2 and C3 are not recovered by any probe: a census of every active feature finds no rhyme-anticipating enrichment at the newline

Locator: Abstract (N-29; VERIFIED)

[8] [Steering Under Compression: Dose-Response, Capability Cost, and Failure Asymmetry in Quantized LLMs](https://arxiv.org/html/2609.06473v1) (Saurav Bhandari, Benjamin Wade; 2026) — Steering Under Compression (Bhandari, Wade); cited in rows 92e-E-1. (version: v1; venue: 17 pages, 5 figures; status: VERIFIED; retrieved 2026-10-22)

> We systematically study activation steering under weight-only quantization (INT8 and NF4) across four open-weight

Locator: Abstract (E-1; VERIFIED)

> Activations remain in FP16/BF16 throughout the forward pass.

Locator: Sec. 3 (deployment conditions) (E-2; VERIFIED)

> we find that sentiment steering survives quantization intact.

Locator: Abstract (E-3; VERIFIED)

> demonstrating that compression can dominate the steering intervention.

Locator: Abstract (E-4; VERIFIED)

[9] [Stable Directions, Different Effects: Intervention Fidelity Across Model Precision (OpenReview forum 8iTqrW1sxY)](https://api2.openreview.net/notes/search?term=Stable%20Directions%2C%20Different%20Effects%3A%20Intervention%20Fidelity%20Across%20Model%20Precision&group=ICLR.cc/2027/Conference&limit=10) (2026) — ICLR 2027 Conference Desk Rejected Submission; contemporaneous. Cited in rows 92e-E-2. (version: submission; venue: ICLR 2027 Conference Desk Rejected Submission; status: VERIFIED-ABSTRACT; retrieved 2026-10-22)

> Preserving standard model quality or direction-level representation similarity does not guarantee that the

Locator: OpenReview abstract (forum 8iTqrW1sxY) (E-5; VERIFIED-ABSTRACT)

> Intervention effects can change even when directions

Locator: OpenReview abstract (E-6; VERIFIED-ABSTRACT)

[10] [Activation Steering under Low-Bit Quantization: A Geometric Perspective on Degradation and Recovery (OpenReview forum h57duZqLOr)](https://api2.openreview.net/notes/search?term=Activation%20Steering%20under%20Low-Bit%20Quantization%3A%20A%20Geometric%20Perspective%20on%20Degradation%20and%20Recovery&group=ICLR.cc/2027/Conference&limit=10) (2026) — ICLR 2027 Conference Submission; contemporaneous. Cited in rows 92e-E-3. (version: submission; venue: ICLR 2027 Conference Submission; status: VERIFIED-ABSTRACT; retrieved 2026-10-22)

> We study steering compatibility with the intervention layer, direction, and strength held fixed across full-precision and quantized models.

Locator: OpenReview abstract (forum h57duZqLOr) (E-7; VERIFIED-ABSTRACT)

> We show that ordinary output fidelity alone does not guarantee

Locator: OpenReview abstract (E-8; VERIFIED-ABSTRACT)

[11] [Quantization Modulates Batch-Context Non-Determinism in Greedy LLM Inference (OpenReview forum 9kskCmPMqd)](https://api2.openreview.net/notes/search?term=Quantization%20Modulates%20Batch-Context%20Non-Determinism%20in%20Greedy%20LLM%20Inference&group=ICLR.cc/2027/Conference&limit=10) (2026) — ICLR 2027 Conference Submission; contemporaneous. Cited in rows 92e-E-4. (version: submission; venue: ICLR 2027 Conference Submission; status: VERIFIED-ABSTRACT; retrieved 2026-10-22)

> using BF16, GPTQ, FP8 weight-and-activation quantization, and FP8 KV-cache quantization.

Locator: OpenReview abstract (forum 9kskCmPMqd) (E-9; VERIFIED-ABSTRACT)

[12] [llm-compressor examples/quantization_w8a8_fp8 README (vLLM project)](https://raw.githubusercontent.com/vllm-project/llm-compressor/main/examples/quantization_w8a8_fp8/README.md) (2024) — FP8_DYNAMIC scheme: static per-channel weight scales and dynamic per-token activation scales. (version: main; venue: GitHub (vLLM project); status: VERIFIED-README; retrieved 2026-10-22)

> Dynamic, per-token quantization on the activations

Locator: 2) Apply Quantization (E-24; VERIFIED-README)

[13] [Finding Alignments Between Interpretable Causal Variables and Distributed Neural Representations](https://arxiv.org/html/2303.02536v4) (Atticus Geiger, Zhengxuan Wu, Christopher Potts, Thomas Icard, Noah D. Goodman; 2023) — DAS (Geiger, Wu, Potts, Icard, Goodman); cited in rows 92e-P1-1. (version: v4; venue: arXiv preprint; status: VERIFIED; retrieved 2026-10-22)

> existing causal abstraction methods have two major limitations: they require a brute-force search over alignments between the high-level model and the low-level one, and they presuppose that variables in the high-level model will align with disjoint sets of neurons in the low-level one.

Locator: Abstract (P1-1; VERIFIED)

[14] [MIB: A Mechanistic Interpretability Benchmark](https://arxiv.org/html/2504.13151v2) (Aaron Mueller, Atticus Geiger, Sarah Wiegreffe, Dana Arad, Iván Arcuschin, Adam Belfki, Yik Siu Chan, Jaden Fiotto-Kaufman, Tal Haklay, Michael Hanna, Jing Huang, Rohan Gupta; 2025) — MIB (Mueller et al.); cited in rows 92e-P1-2. (version: v2; venue: Accepted to ICML 2025. Project website at https://mib-bench.github.io; status: VERIFIED; retrieved 2026-10-22; author list truncated to the first names shown by the source)

> For causal variable localization, we find that the supervised DAS method performs best, while SAE features are not better than neurons, i.e., non-featurized hidden vectors.

Locator: Abstract (P1-4; VERIFIED)

[15] [Faithful Bi-Directional Model Steering via Distribution Matching and Distributed Interchange Interventions](https://arxiv.org/html/2602.05234v2) (Yuntai Bao, Xuhong Zhang, Jintao Chen, Ge Su, Yuxiang Cai, Hao Peng, Bing Sun, Haiqin Weng, Liu Yan, Jianwei Yin; 2026) — CDAS (Bao et al.); cited in rows 92e-P1-3. (version: v2; venue: camera ready version; 55 pages, 25 figures; accepted for ICLR 2026 | Proceedings of the International Conference on Learning Representations (ICLR), 2026; status: VERIFIED; retrieved 2026-10-22)

> we introduce a novel distribution matching objective tailored for the steering task by aligning intervened output distributions with counterfactual distributions.

Locator: Sec. 1 Introduction (P1-5; VERIFIED)

[16] [The Invisible Lottery: How Subtle Cues Steer Algorithm Choice in LLM Code Generation](https://arxiv.org/html/2606.04057v1) (2026) — Inherited from art_kjrCpQnPaniY Table 92b/92c source [30]; its quotes are cited by row id and were not re-fetched here. (version: v1; status: INHERITED (cited by id; not re-verified); retrieved 2026-10-22)

[17] [Causal Syntax Circuits in CodeLMs: Budget and Probe Decide What Looks Localised](https://arxiv.org/html/2610.20683v1) (Harsh Kumar, Tanmay Shailesh Joshi, Rahul Maity, Anusa Saha; 2026) — Causal Syntax Circuits in CodeLMs (Kumar et al.); cited in rows 92e-P1-6. (version: v1; venue: Accepted at the NeurIPS 2026 Workshop on Linguistic Principles for Foundation Models (LP4FM). All four authors contributed equally; status: VERIFIED; retrieved 2026-10-22)

> Code models write Python when the prompt does not say which language to use. We ask a mechanistic question about that habit: is it produced by a small, findable group of components inside the model?

Locator: Abstract (P1-8; VERIFIED)

[18] [Steering LLM Coding Behaviors with Concept Vectors (OpenReview forum sbVictHY9s)](https://api2.openreview.net/notes/search?term=Steering%20LLM%20Coding%20Behaviors%20with%20Concept%20Vectors&group=ICLR.cc/2027/Conference&limit=10) (2026) — ICLR 2027 Conference Submission; contemporaneous. Cited in rows 92e-P1-7. (version: submission; venue: ICLR 2027 Conference Submission; status: VERIFIED-ABSTRACT; retrieved 2026-10-22)

> Adding them after the first sampled token changes held-out outputs, but effects depend on model and layer, strong scaling harms validity and correctness, and axis specificity remains unresolved without matched-norm causal

Locator: OpenReview abstract (forum sbVictHY9s) (P1-9; VERIFIED-ABSTRACT)

[19] [Steering Code LLMs with Activation Directions for Language and Library Control](https://arxiv.org/html/2603.23629v2) (2026) — Inherited from art_kjrCpQnPaniY Table 92b/92c source [45]; its quotes are cited by row id and were not re-fetched here. (version: v2; status: INHERITED (cited by id; not re-verified); retrieved 2026-10-22)

[20] [Before Reasoning Begins: Temporal Contrast Reveals a Causal Target Across Reasoning Tasks (OpenReview forum vH3g2k4lPB)](https://api2.openreview.net/notes/search?term=Before%20Reasoning%20Begins%3A%20Temporal%20Contrast%20Reveals%20a%20Causal%20Target%20Across%20Reasoning%20Tasks&group=ICLR.cc/2027/Conference&limit=10) (2026) — ICLR 2027 Conference Submission; contemporaneous. Cited in rows 92e-P1-8, 92e-P2-5. (version: submission; venue: ICLR 2027 Conference Submission; status: VERIFIED-ABSTRACT; retrieved 2026-10-22)

> This pipeline yields a compact set of 23 intervention targets in Qwen3-8B.

Locator: OpenReview abstract (forum vH3g2k4lPB) (P1-10; VERIFIED-ABSTRACT)

> We use this functionally aligned contrast to screen sparse autoencoder features at the final prompt position

Locator: OpenReview abstract (P1-11; VERIFIED-ABSTRACT)

> same-size, layer-count-matched random null interventions reduce accuracy by only

Locator: OpenReview abstract (P2-5; VERIFIED-ABSTRACT)

[21] [Controllable LLM Reasoning via Sparse Autoencoder-Based Steering](https://arxiv.org/html/2601.03595v2) (Yi Fang, Wenjie Wang, Mingfeng Xue, Boyi Deng, Fengli Xu, Dayiheng Liu, Fuli Feng; 2026) — SAE-Steering (Fang et al.); cited in rows 92e-S-4. (version: v2; venue: Accepted to the ACL 2026 Main; status: VERIFIED; retrieved 2026-10-22)

> To identify the few strategy-specific features from the vast pool of SAE features, we propose SAE-Steering, an efficient two-stage feature identification pipeline.

Locator: Abstract (S-13; VERIFIED)

> Think Intervention (Wu et al., 2025), which inserts human-crafted instructions into the middle of the reasoning process

Locator: Sec. 4.1, Baselines (S-13b; VERIFIED)

[22] [AxBench: Steering LLMs? Even Simple Baselines Outperform Sparse Autoencoders](https://arxiv.org/html/2501.17148v3) (Zhengxuan Wu, Aryaman Arora, Atticus Geiger, Zheng Wang, Jing Huang, Dan Jurafsky, Christopher D. Manning, Christopher Potts; 2025) — AxBench (Wu et al.); cited in rows 92e-S-3. (version: v3; venue: arXiv preprint; status: VERIFIED; retrieved 2026-10-22)

> For steering, we find that prompting outperforms all existing methods, followed by finetuning.

Locator: Abstract (S-10; VERIFIED)

> For concept detection, representation-based methods such as difference-in-means, perform the best. On both evaluations, SAEs are not competitive.

Locator: Abstract (S-11; VERIFIED)

[23] [Steering LLMs? Actually, Sparse Autoencoders can outperform simple baselines](https://arxiv.org/html/2605.31183v1) (Mikkel Godsk Jørgensen, Lars Kai Hansen; 2026) — AxBench rebuttal (Jorgensen et al.); cited in rows 92e-S-3. (version: v1; venue: arXiv preprint; status: VERIFIED; retrieved 2026-10-22)

> We find that Sparse Autoencoders can, in fact, perform close to on par with the reference LoRA performance on the AxBench benchmark, when features are selected and labelled with our supervised pipeline.

Locator: Abstract (S-12; VERIFIED)

[24] [What Is the Minimum Architecture for Prolepsis? Early Irrevocable Commitment Across Tasks in Small Transformers](https://arxiv.org/html/2604.15010v2) (Éric Jacopin; 2026) — Prolepsis (Jacopin); cited in rows 92e-P3-3, 92e-S-6. (version: v2; venue: v2: corrects three citations; reconciles main-text/appendix numbers (the two Llama sweeps now labeled); the effective last-token site differs from Anthropic's newline (position-specificity replicates, site identity does not); adds an erratum on a CLT encoder-hook mismatch (detection-side only); softens novelty, necessity, and depth claims per COLM 2026 reviews; defines prolepsis; status: VERIFIED; retrieved 2026-10-22)

> We introduce prolepsis: a transformer commits early, task-specific attention heads sustain the commitment, and no layer corrects it.

Locator: Abstract (P3-3; VERIFIED)

> Planning is invisible to six residual-stream methods; among those tested, only CLT-based steering succeeds.

Locator: Abstract (S-17; VERIFIED)

[25] [safety-research/circuit-tracer README](https://raw.githubusercontent.com/safety-research/circuit-tracer/main/README.md) (2026) — Gemma-3 PLTs from GemmaScope-2 (need the nnsight backend); Qwen-3 PLTs for 0.6B-14B, including 8B. (version: main; venue: GitHub; status: VERIFIED-README; retrieved 2026-10-22)

> here for models of size 270M, 1B, 4B, 12B, and 27B, PT and

Locator: Supported transcoders (S-5; VERIFIED-README)

[26] [mwhanna/qwen3-8b-transcoders (Hugging Face)](https://huggingface.co/mwhanna/qwen3-8b-transcoders) (2025) — Qwen-3 transcoder collection (0.6B-14B); the card does not name the exact checkpoint. (version: main; venue: Hugging Face; status: VERIFIED-README; retrieved 2026-10-22)

> Transcoders trained on Qwen-3 models from 0.6B to 14B

Locator: collection blurb (S-7; VERIFIED-README)

[27] [Latent Planning Emerges with Scale](https://arxiv.org/html/2604.12493v1) (Michael Hanna, Emmanuel Ameisen; 2026) — Latent Planning Emerges with Scale (Hanna et al.); cited in rows 92e-P2-4, 92e-S-2. (version: v1; venue: ICLR 2026; status: VERIFIED; retrieved 2026-10-22)

> even the less-successful Qwen-3 4B-8B have nascent planning mechanisms.

Locator: Abstract (P2-4; VERIFIED)

> For our experiments, we use Hanna et al.

Locator: App. A.1, Qwen-3 Transcoders (S-8; VERIFIED)

> Note that although these models are instruction-tuned

Locator: Sec. 4.1 Models and Data (S-9; VERIFIED)

[28] [Exploring Diverse Generation Paths via Inference-time Stiefel Activation Steering](https://arxiv.org/html/2601.22010v1) (2026) — Inherited from art_kjrCpQnPaniY Table 92b/92c source [15]; its quotes are cited by row id and were not re-fetched here. (version: v1; status: INHERITED (cited by id; not re-verified); retrieved 2026-10-22)

[29] [Noise Steering for Controlled Text Generation: Improving Diversity and Reading-Level Fidelity in Arabic Educational Story Generation](https://arxiv.org/pdf/2604.03380v2) (2026) — Inherited from art_kjrCpQnPaniY Table 92b/92c source [14]; its quotes are cited by row id and were not re-fetched here. (version: v2; status: INHERITED (cited by id; not re-verified); retrieved 2026-10-22)

[30] [From Noise to Diversity: Random Embedding Injection in LLM Reasoning](https://arxiv.org/html/2605.11936v2) (2026) — Inherited from art_kjrCpQnPaniY Table 92b/92c source [16]; its quotes are cited by row id and were not re-fetched here. (version: v2; status: INHERITED (cited by id; not re-verified); retrieved 2026-10-22)

[31] [Latent-Plan Block Diffusion: Sampling a Block-Level Intent for Few-Step Parallel Decoding (OpenReview forum IhQbFddkBp)](https://api2.openreview.net/notes/search?term=Latent-Plan%20Block%20Diffusion%3A%20Sampling%20a%20Block-Level%20Intent%20for%20Few-Step%20Parallel%20Decoding&group=ICLR.cc/2027/Conference&limit=10) (2026) — ICLR 2027 Conference Submission; contemporaneous. Cited in rows 92e-P5-2. (version: submission; venue: ICLR 2027 Conference Submission; status: VERIFIED-ABSTRACT; retrieved 2026-10-22)

> before a block is decoded, a small conditional flow samples a low-dimensional

Locator: OpenReview abstract (forum IhQbFddkBp) (P5-2; VERIFIED-ABSTRACT)

[32] [Parallelizable Probabilistic Latent Reasoning for Diverse Reasoning Trajectories (OpenReview forum CtluWEsiX7)](https://api2.openreview.net/notes/search?term=Parallelizable%20Probabilistic%20Latent%20Reasoning%20for%20Diverse%20Reasoning%20Trajectories&group=ICLR.cc/2027/Conference&limit=10) (2026) — ICLR 2027 Conference Submission; contemporaneous. Cited in rows 92e-P5-3. (version: submission; venue: ICLR 2027 Conference Submission; status: VERIFIED-ABSTRACT; retrieved 2026-10-22)

> current latent models remain largely deterministic, capturing only a single reasoning trajectory rather than modeling a distribution over

Locator: OpenReview abstract (forum CtluWEsiX7) (P5-3; VERIFIED-ABSTRACT)

[33] [Singular Value Perturbation: Unlocking RL Performance via Diverse Latent Reasoning (OpenReview forum oTt6XeccGk)](https://api2.openreview.net/notes/search?term=Singular%20Value%20Perturbation%3A%20Unlocking%20RL%20Performance%20via%20Diverse%20Latent%20Reasoning&group=ICLR.cc/2027/Conference&limit=10) (2026) — ICLR 2027 Conference Submission; contemporaneous. Cited in rows 92e-P5-3. (version: submission; venue: ICLR 2027 Conference Submission; status: VERIFIED-ABSTRACT; retrieved 2026-10-22)

> which diversifies latent trajectories by randomly rescaling coefficients in the fixed SVD basis of a weight matrix.

Locator: OpenReview abstract (forum oTt6XeccGk) (P5-4; VERIFIED-ABSTRACT)

[34] [Random Choice in Language Models: A Linear Choice State and Low-Rank Sampling Control (OpenReview forum eZYeqPZlFr)](https://api2.openreview.net/notes/search?term=Random%20Choice%20in%20Language%20Models%3A%20A%20Linear%20Choice%20State%20and%20Low-Rank%20Sampling%20Control&group=ICLR.cc/2027/Conference&limit=10) (2026) — ICLR 2027 Conference Submission; contemporaneous. Cited in rows 92e-P1-10, 92e-P5-1. (version: submission; venue: ICLR 2027 Conference Submission; status: VERIFIED-ABSTRACT; retrieved 2026-10-22)

> one direction acts as a switch into the random-choice mode, whereas a separate direction shapes the resulting answer distribution.

Locator: OpenReview abstract (forum eZYeqPZlFr) (P1-13; VERIFIED-ABSTRACT)

> This decomposition enables a mechanism-guided intervention that improves sampling without task-specific gradient training.

Locator: OpenReview abstract (P5-1; VERIFIED-ABSTRACT)

[35] [OpenAlex / Crossref scholarly search (via aii-web-tools aii_fast_web_search.py --mode scholarly)](https://api.openalex.org/works) (2026) — Engine E1 for lanes L1, L4 and L6 in round 1, and all lanes in round 2. (status: ENGINE; retrieved 2026-10-22)

[36] [arXiv API (export.arxiv.org/api/query): version, v1 date, comment and journal-ref metadata](https://export.arxiv.org/api/query) (2026) — Engine E3 and the source of all version, v1-date and venue-comment lines (evidence/arxiv_meta.json). (status: ENGINE; retrieved 2026-10-22)

[37] [Semantic Scholar Graph API (search, citations, references)](https://api.semanticscholar.org/graph/v1) (2026) — Engine E4 (year=2026 search) and snowballing (forward citations and backward references). (status: ENGINE; retrieved 2026-10-22)

[38] [OpenReview API v2 notes/search (ICLR.cc/2027/Conference)](https://api2.openreview.net/notes/search) (2026) — Engine E5 and the locator of every VERIFIED-ABSTRACT ICLR 2027 row. (status: ENGINE; retrieved 2026-10-22)

[39] [Interpretability at Scale: Identifying Causal Mechanisms in Alpaca](https://arxiv.org/html/2305.08809v3) (Zhengxuan Wu, Atticus Geiger, Thomas Icard, Christopher Potts, Noah D. Goodman; 2023) — Boundless DAS (Wu et al.); cited in rows 92e-P1-1. (version: v3; venue: NeurIPS 2023 with Author Corrections; status: VERIFIED; retrieved 2026-10-22)

> We apply Boundless DAS to the Alpaca model (7B parameters), which, off the shelf, solves a simple numerical reasoning problem.

Locator: Abstract (P1-3; VERIFIED)

[40] [Before the First Token: A Shared Causal Subspace for Response-Length Planning in LLMs](https://api2.openreview.net/notes/search?term=Before%20the%20First%20Token%3A%20A%20Shared%20Causal%20Subspace%20for%20Response-Length%20Planning%20in%20LLMs&group=ICLR.cc/2027/Conference&limit=10) (2026) — Inherited from art_kjrCpQnPaniY Table 92b/92c source [64]; its quotes are cited by row id and were not re-fetched here. (status: INHERITED (cited by id; not re-verified); retrieved 2026-10-22)

[41] [AJR: Amortized Jacobian Readouts for Prompt-Adaptive Steering](https://api2.openreview.net/notes/search?term=AJR%3A%20Amortized%20Jacobian%20Readouts%20for%20Prompt-Adaptive%20Steering&group=ICLR.cc/2027/Conference&limit=10) (2026) — Inherited from art_kjrCpQnPaniY Table 92b/92c source [65]; its quotes are cited by row id and were not re-fetched here. (status: INHERITED (cited by id; not re-verified); retrieved 2026-10-22)

[42] [DecodeShare: Tracing the Shared Subspace of LLM Decode-Time Decisions](https://arxiv.org/html/2607.20469v1) (Zishan Shao, Lixun Zhang, Kangning Cui, Yixiao Wang, Ting Jiang, Hancheng Ye, Qinsi Wang, Zhixu Du, Yuzhe Fu, Fan Yang, Danyang Zhuo, Yiran Chen; 2026) — DecodeShare (Shao et al.); cited in rows 92e-P2-2. (version: v1; venue: arXiv preprint; status: VERIFIED; retrieved 2026-10-22; author list truncated to the first names shown by the source)

> disturbing the discovered shared subspace degrades decision performance far more than disturbing either a prefill-derived or random subspace under the same intervention budget.

Locator: Abstract (P2-2; VERIFIED)

[43] [What Does Activation Steering Control? Attribution Across Answer Encodings and Output-Sensitive Subspaces](https://arxiv.org/html/2608.22985v1) (Zhiwei Gao, Shaowen Peng, Shoko Wakamiya, Eiji Aramaki; 2026) — What Does Activation Steering Control? (Gao et al.); cited in rows 92e-P2-7. (version: v1; venue: arXiv preprint; status: VERIFIED; retrieved 2026-10-22)

> A low-rank output-sensitive component containing 15.4% of the direction

Locator: Abstract (P2-7; VERIFIED)

[44] [A Jailbreak Success Coordinate Outside the Refusal Subspace: Decodable Before Generation, Reachable from the Input (OpenReview forum 4gvIW4C0bw)](https://api2.openreview.net/notes/search?term=A%20Jailbreak%20Success%20Coordinate%20Outside%20the%20Refusal%20Subspace&group=ICLR.cc/2027/Conference&limit=10) (2026) — ICLR 2027 Conference Submission; contemporaneous. Cited in rows 92e-P2-3. (version: submission; venue: ICLR 2027 Conference Submission; status: VERIFIED-ABSTRACT; retrieved 2026-10-22)

> whether success is decodable before generation from a coordinate outside an evaluated refusal subspace, whether intervention on that coordinate moves the behavior

Locator: OpenReview abstract (forum 4gvIW4C0bw) (P2-3; VERIFIED-ABSTRACT)

[45] [The Geometry of Categorical and Hierarchical Concepts in Large Language Models](https://arxiv.org/html/2406.01506v3) (Kiho Park, Yo Joong Choe, Yibo Jiang, Victor Veitch; 2024) — Park, Choe, Jiang, Veitch; cited in rows 92e-P3-1. (version: v3; venue: Accepted for an oral presentation at ICLR 2025. Best Paper Award at the ICML 2024 Workshop on Mechanistic Interpretability. Code is available at https://github.com/KihoPark/LLM_Categorical_Hierarchical_Representations; status: VERIFIED; retrieved 2026-10-22)

> This allows us to immediately formalize the representation of categorical concepts as polytopes in the representation space.

Locator: Abstract (P3-1; VERIFIED)

[46] [Not All Language Model Features Are One-Dimensionally Linear](https://arxiv.org/html/2405.14860v3) (Joshua Engels, Eric J. Michaud, Isaac Liao, Wes Gurnee, Max Tegmark; 2024) — Engels et al.; cited in rows 92e-P3-2. (version: v3; venue: Accepted to ICLR 2025. Code and data at https://github.com/JoshEngels/MultiDimensionalFeatures; status: VERIFIED; retrieved 2026-10-22)

> we explore whether some language model representations may be inherently multi-dimensional.

Locator: Abstract (P3-2; VERIFIED)

[47] [Manifold Steering Reveals the Shared Geometry of Neural Network Representation and Behavior](https://arxiv.org/html/2605.05115v1) (2026) — Inherited from art_kjrCpQnPaniY Table 92b/92c source [44]; its quotes are cited by row id and were not re-fetched here. (version: v1; status: INHERITED (cited by id; not re-verified); retrieved 2026-10-22)

[48] [Rethinking Activation Steering for Mathematical Reasoning: What Actually Drives Its Reasoning Gains?](https://api2.openreview.net/notes/search?term=Rethinking%20Activation%20Steering%20for%20Mathematical%20Reasoning&group=ICLR.cc/2027/Conference&limit=10) (2026) — Inherited from art_kjrCpQnPaniY Table 92b/92c source [66]; its quotes are cited by row id and were not re-fetched here. (status: INHERITED (cited by id; not re-verified); retrieved 2026-10-22)

[49] [Is Temperature the Creativity Parameter of Large Language Models?](https://arxiv.org/html/2405.00492v1) (2024) — Inherited from art_kjrCpQnPaniY Table 92b/92c source [25]; its quotes are cited by row id and were not re-fetched here. (version: v1; status: INHERITED (cited by id; not re-verified); retrieved 2026-10-22)

[50] [Forking Paths in Neural Text Generation](https://arxiv.org/html/2412.07961v1) (Eric Bigelow, Ari Holtzman, Hidenori Tanaka, Tomer Ullman; 2024) — Forking Paths in Neural Text Generation (Bigelow et al.); cited in rows 92e-P4-1. (version: v1; venue: arXiv preprint; status: VERIFIED; retrieved 2026-10-22)

> We hypothesize that there exist key forking tokens, such that re-sampling the system at those specific tokens, but not others, leads to very different outcomes.

Locator: Abstract (P4-1; VERIFIED)

[51] [Predicting Future Behaviors in Reasoning Models Enables Better Steering (OpenReview forum 5tVsS1vVLC)](https://api2.openreview.net/notes/search?term=Predicting%20Future%20Behaviors%20in%20Reasoning%20Models%20Enables%20Better%20Steering&group=ICLR.cc/2027/Conference&limit=10) (2026) — ICLR 2027 Conference Submission; contemporaneous. Cited in rows 92e-P4-3. (version: submission; venue: ICLR 2027 Conference Submission; status: VERIFIED-ABSTRACT; retrieved 2026-10-22)

> We apply a forking-paths-style analysis to behavioral evaluations and find that as generation progresses, LRMs define evolving distributions over behavioral outcomes.

Locator: OpenReview abstract (forum 5tVsS1vVLC) (P4-3; VERIFIED-ABSTRACT)

[52] [Auditing the Auditor: Ground-Truth Controls for Natural-Language Explanations of LLM Activations (OpenReview forum PKToLtvIZl)](https://api2.openreview.net/notes/search?term=Auditing%20the%20Auditor%3A%20Ground-Truth%20Controls%20for%20Natural-Language%20Explanations%20of%20LLM%20Activations&group=ICLR.cc/2027/Conference&limit=10) (2026) — ICLR 2027 Conference Submission; contemporaneous. Cited in rows 92e-N-7. (version: submission; venue: ICLR 2027 Conference Submission; status: VERIFIED-ABSTRACT; retrieved 2026-10-22)

> under preregistered controls: a wrong-activation (shuffled) control, a visible-text baseline, a blinded judge, and supervised readability probes.

Locator: OpenReview abstract (forum PKToLtvIZl) (N-22; VERIFIED-ABSTRACT)

> apparent successes on famous facts are indistinguishable from verbalizer prior-completion under a truthful-instruction control

Locator: OpenReview abstract (N-23; VERIFIED-ABSTRACT)

[53] [Do Sparse Autoencoders Identify Reasoning Features in Language Models?](https://arxiv.org/html/2601.05679v7) (George Ma, Zhongyuan Liang, Irene Y. Chen, Somayeh Sojoudi; 2026) — Do SAEs Identify Reasoning Features? (Ma et al.); cited in rows 92e-S-5. (version: v7; venue: In Forty-Third International Conference on Machine Learning (2026); status: VERIFIED; retrieved 2026-10-22)

> use SAEs from the GemmaScope-2 release (McDougall et al., 2025), each with 16,384 features trained on residual stream activations.

Locator: Sec. 5.1 Experimental Setup (S-15; VERIFIED)

> A small steering study yields minimal changes on the evaluated benchmarks.

Locator: Abstract (S-16; VERIFIED)

[54] [Where You Inject Diversity Matters: A Unified Framework for Diverse Generation](https://arxiv.org/html/2606.10302v1) (2026) — Inherited from art_kjrCpQnPaniY Table 92b/92c source [31]; its quotes are cited by row id and were not re-fetched here. (version: v1; status: INHERITED (cited by id; not re-verified); retrieved 2026-10-22)

[55] [Same Targets, Different Computation: How Post-Training Divides Work Across Model Layers](https://arxiv.org/html/2605.07284v2) (2026) — Inherited from art_ObxQOIlAM9MS Table 92d source [15]; its quotes are cited by row id and were not re-fetched here. (version: v2; status: INHERITED (cited by id; not re-verified); retrieved 2026-10-22)

[56] [Verbalized Sampling: How to Mitigate Mode Collapse and Unlock LLM Diversity](https://arxiv.org/html/2510.01171v4) (2025) — Inherited from art_ObxQOIlAM9MS Table 92d source [11]; its quotes are cited by row id and were not re-fetched here. (version: v4; status: INHERITED (cited by id; not re-verified); retrieved 2026-10-22)

[57] [Finding Algorithms in Neural Networks: Convergent Predictions Between Distributed Alignment Search and Speed of Transfer Learning (OpenReview forum aHSbJo4RHN)](https://api2.openreview.net/notes/search?term=Finding%20Algorithms%20in%20Neural%20Networks%3A%20Convergent%20Predictions%20Between%20Distributed%20Alignment%20Search%20and%20Speed%20of%20Transfer%20Learning&group=ICLR.cc/2027/Conference&limit=10) (2026) — ICLR 2027 Conference Submission; contemporaneous. Cited in rows 92e-P1-5. (version: submission; venue: ICLR 2027 Conference Submission; status: VERIFIED-ABSTRACT; retrieved 2026-10-22)

> We find that, on toy arithmetic and vision tasks, the algorithms identified by DAS and TLA mostly agree

Locator: OpenReview abstract (forum aHSbJo4RHN) (P1-7; VERIFIED-ABSTRACT)

[58] [From Signal Degradation to Computation Collapse: Uncovering the Two Failure Modes of LLM Quantization](https://arxiv.org/html/2604.19884v1) (Chenxi Zhou, Pengfei Cao, Jiang Li, Bohan Yu, Jinyu Ye, Jun Zhao, Kang Liu; 2026) — From Signal Degradation to Computation Collapse (Zhou et al.); cited in rows 92e-E-6. (version: v1; venue: Accepted to Findings of ACL 2026; status: VERIFIED; retrieved 2026-10-22)

> we employ causal activation patching Heimersheim and Nanda (2024) to assess the integrity of the information pathway.

Locator: Sec. 3.4 (E-11; VERIFIED)

[59] [The Structure of Quantization Damage in LLMs: Why the Next Bit Should Be Spent Globally](https://arxiv.org/html/2609.01587v1) (Jundong Hu, Shekar Ramachandran; 2026) — The Structure of Quantization Damage (Hu, et al.); cited in rows 92e-E-6. (version: v1; venue: Preprint. Under review at a NeurIPS 2026 workshop. 11 pages, 4 figures, 8 tables; status: VERIFIED; retrieved 2026-10-22)

> None of them predicts which layers benefit from restored precision.

Locator: Abstract (E-12; VERIFIED)

[60] [Perplexity Can Miss SAE Feature Damage Under Quantization](https://arxiv.org/html/2606.03002v2) (Evan Duan; 2026) — Perplexity Can Miss SAE Feature Damage Under Quantization (Duan); cited in rows 92e-E-6. (version: v2; venue: 12 Pages of Content, Submitted to TMLR; status: VERIFIED; retrieved 2026-10-22)

> These results show that behavioral metrics alone are insufficient evidence that full-precision interpretability findings transfer to quantized models, motivating feature-level audits of compression.

Locator: Abstract (E-13; VERIFIED)

[61] [Same Probe, Different Numbers: Are Activation Probes Robust to Inference-Time Numerical Non-Determinism?](https://arxiv.org/html/2609.31796v1) (Alizishaan Khatri; 2026) — Same Probe, Different Numbers (Khatri); cited in rows 92e-E-7. (version: v1; venue: arXiv preprint; status: VERIFIED; retrieved 2026-10-22)

> Because common GPU kernels are not batch-invariant and floating-point formats round differently, the activations seen at deployment are not the ones the probe was trained on.

Locator: Abstract (E-16; VERIFIED)

[62] [Patchscopes: A Unifying Framework for Inspecting Hidden Representations of Language Models](https://arxiv.org/html/2401.06102v4) (2024) — Inherited from art_ObxQOIlAM9MS Table 92d source [88]; its quotes are cited by row id and were not re-fetched here. (version: v4; status: INHERITED (cited by id; not re-verified); retrieved 2026-10-22)

[63] [Perturb the Thought, Not the Pixels: Latent-Space Rollout Diversification for Reinforcement Learning of Vision-Language Models](https://arxiv.org/html/2608.21595v1) (2026) — Inherited from art_kjrCpQnPaniY Table 92b/92c source [52]; its quotes are cited by row id and were not re-fetched here. (version: v1; status: INHERITED (cited by id; not re-verified); retrieved 2026-10-22)

[64] [Finding Alignments Between Interpretable Causal Variables and Distributed Neural Representations (PMLR 236 record)](https://proceedings.mlr.press/v236/geiger24a.html) (Atticus Geiger, Zhengxuan Wu, Christopher Potts, Thomas Icard, Noah Goodman; 2024) — Venue record for DAS: CLeaR 2024, PMLR 236. (version: proceedings; venue: CLeaR 2024; status: VERIFIED; retrieved 2026-10-22)

> Finding Alignments Between Interpretable Causal Variables and Distributed Neural Representations

Locator: PMLR record (P1-2; VERIFIED)

[65] [Programmable Semantic Interventions: Learning Causal Carriers from Behavioral Programs (OpenReview forum DLKIln4eAT)](https://api2.openreview.net/notes/search?term=Programmable%20Semantic%20Interventions%3A%20Learning%20Causal%20Carriers%20from%20Behavioral%20Programs&group=ICLR.cc/2027/Conference&limit=10) (2026) — ICLR 2027 Conference Submission; contemporaneous. Cited in rows 92e-P1-4. (version: submission; venue: ICLR 2027 Conference Submission; status: VERIFIED-ABSTRACT; retrieved 2026-10-22)

> a low-rank activation subspace learned so that interchanging it moves the model's answer the way the program declares.

Locator: OpenReview abstract (forum DLKIln4eAT) (P1-6; VERIFIED-ABSTRACT)

[66] [Committed Before Reasoning: Behavioral Reproduction and Preliminary Activation-Level Evidence of Answer Pre-Commitment in an Open-Weight LLM](https://arxiv.org/html/2607.16451v1) (Heejin Jo; 2026) — Committed Before Reasoning (Jo); cited in rows 92e-P1-9. (version: v1; venue: 8 pages. Code, data, and all reported statistics: https://github.com/JO-HEEJIN/interview_mate/tree/docs/car-wash-repro/car_wash/paper_4; status: VERIFIED; retrieved 2026-10-22)

> Chat models sometimes commit to an answer and then produce reasoning that justifies the commitment rather than deriving it

Locator: Abstract (P1-12; VERIFIED)

[67] [Detecting and Characterizing Planning in Language Models](https://arxiv.org/html/2508.18098v1) (Jatin Nainani, Sankaran Vaidyanathan, Connor Watts, Andre N. Assis, Alice Rigg; 2025) — Detecting and Characterizing Planning (Nainani et al.); cited in rows 92e-P1-11. (version: v1; venue: 9 pages, 4 figures; status: VERIFIED; retrieved 2026-10-22)

> We apply this pipeline to both base and instruction-tuned Gemma-2-2B models on the MBPP code generation benchmark and a poem generation task where Claude 3.5 Haiku was previously shown to plan.

Locator: Abstract (P1-14; VERIFIED)

[68] [Transformers converge to invariant algorithmic cores](https://arxiv.org/html/2602.22600v2) (Joshua S. Schiffman; 2026) — Algorithmic Core Extraction (Schiffman); cited in rows 92e-P1-12. (version: v2; venue: arXiv preprint; status: VERIFIED; retrieved 2026-10-22)

> compact subspaces that are necessary and sufficient for a task and that recur across independently trained models.

Locator: Abstract (P1-15; VERIFIED)

[69] [The Non-Linear Representation Dilemma: Is Causal Abstraction Enough for Mechanistic Interpretability?](https://arxiv.org/html/2507.08802v2) (Denis Sutter, Julian Minder, Thomas Hofmann, Tiago Pimentel; 2025) — Sutter, Minder, Hofmann, Pimentel; cited in rows 92e-P1-CTRL-1. (version: v2; venue: NeurIPS 2025 (Spotlight); status: VERIFIED; retrieved 2026-10-22)

> on an experiment using randomly initialised language models, our alignment maps reach 100% interchange-intervention accuracy on the indirect object identification task.

Locator: Abstract (CTRL-1; VERIFIED)

[70] [Is This the Subspace You Are Looking for? An Interpretability Illusion for Subspace Activation Patching](https://arxiv.org/html/2311.17030v2) (Aleksandar Makelov, Georg Lange, Neel Nanda; 2023) — Makelov, Lange, Geiger, Nanda; cited in rows 92e-P1-CTRL-2. (version: v2; venue: NeurIPS 2023 Workshop on Attributing Model Behavior at Scale; status: VERIFIED; retrieved 2026-10-22)

> this effect may be achieved by activating a

Locator: Abstract (CTRL-2; VERIFIED)

[71] [Is This the Subspace You Are Looking for? (ICLR 2024 poster page)](https://iclr.cc/virtual/2024/poster/19100) (Aleksandar Makelov, Georg Lange, Atticus Geiger, Neel Nanda; 2024) — Venue record: ICLR 2024 poster. (version: page; venue: ICLR 2024; status: VERIFIED; retrieved 2026-10-22)

> Is This the Subspace You Are Looking for? An Interpretability Illusion for Subspace Activation Patching

Locator: ICLR 2024 virtual poster page (CTRL-3; VERIFIED)

[72] [A Reply to Makelov et al. (2023)'s "Interpretability Illusion" Arguments](https://arxiv.org/html/2401.12631v1) (Zhengxuan Wu, Atticus Geiger, Jing Huang, Aryaman Arora, Thomas Icard, Christopher Potts, Noah D. Goodman; 2024) — Wu, Geiger, Huang, Arora, Icard, Potts, Goodman (reply); cited in rows 92e-P1-CTRL-3. (version: v1; venue: 20 pages, 14 figures; status: VERIFIED; retrieved 2026-10-22)

> can reject explanations they consider

Locator: Abstract (CTRL-4; VERIFIED)

> We then argue that the illusions Makelov et al. (2023) see in practice are artifacts of their training and evaluation paradigms.

Locator: Abstract (CTRL-5; VERIFIED)

[73] [Addressing divergent representations from causal interventions on neural networks](https://arxiv.org/html/2511.04638v5) (Satchel Grant, Simon Jerome Han, Alexa R. Tartaglini, Christopher Potts; 2025) — Grant et al., divergent representations; cited in rows 92e-P1-CTRL-4. (version: v5; venue: arXiv preprint; status: VERIFIED; retrieved 2026-10-22)

> minimizing divergence magnitude does not guarantee elimination of hidden pathways; it only reduces the risk surface.

Locator: Sec. 5 (CTRL-6; VERIFIED)

[74] [Right Answer, Wrong Mechanism: Detecting Pernicious Divergence in Causal Interventions](https://arxiv.org/html/2609.39243v2) (Beiming Liu, Minjie Chen; 2026) — Right Answer, Wrong Mechanism (Liu, Chen); cited in rows 92e-P1-CTRL-5. (version: v2; venue: 13 pages, 1 figure, 6 tables. Beiming Liu and Minjie Chen contributed equally; status: VERIFIED; retrieved 2026-10-22)

> No method currently tells the two cases apart.

Locator: Abstract (CTRL-7; VERIFIED)

[75] [The Curse of Multiple Mediators: Hidden Interaction Effects in Activation Patching](https://arxiv.org/html/2606.27510v1) (Sankaran Vaidyanathan, David Arbour, Aaron Mueller, Scott Niekum, David Jensen; 2026) — The Curse of Multiple Mediators (Vaidyanathan et al.); cited in rows 92e-P1-CTRL-6. (version: v1; venue: arXiv preprint; status: VERIFIED; retrieved 2026-10-22)

> we find that the NIE does not solely capture the causal effect through the specific component.

Locator: Abstract (CTRL-8; VERIFIED)

[76] [Many Circuits, One Mechanism: Input Variation and Evaluation Granularity in Circuit Discovery](https://arxiv.org/html/2606.06267v2) (Alireza Bayat Makou, Jingcheng Niu, Subhabrata Dutta, Iryna Gurevych; 2026) — Many Circuits, One Mechanism (Bayat Makou et al.); cited in rows 92e-P1-CTRL-6. (version: v2; venue: 101 pages, 44 figures | Transactions on Machine Learning Research, 2026; status: VERIFIED; retrieved 2026-10-22)

> The discovered circuits appear specialized by frequency when compared structurally, but functional and representational analyses show no reliable evidence of corresponding

Locator: Abstract (CTRL-9; VERIFIED)

[77] [Position: Mechanistic Interpretability Must Disclose Identification Assumptions for Causal Claims](https://arxiv.org/html/2605.08012v1) (Zezheng Lin, Fengming Liu; 2026) — Position: identification assumptions (Lin et al.); cited in rows 92e-P1-CTRL-6. (version: v1; venue: 10 pages, 2 figures. Submitted to NeurIPS 2026 (Position Track); status: VERIFIED; retrieved 2026-10-22)

> A purposive audit of 10 papers across four methodological strands finds no dedicated identification-assumptions section

Locator: Abstract (CTRL-10; VERIFIED)

[78] [When is Your LLM Steerable?](https://arxiv.org/html/2606.11599v1) (2026) — Inherited from art_kjrCpQnPaniY Table 92b/92c source [21]; its quotes are cited by row id and were not re-fetched here. (version: v1; status: INHERITED (cited by id; not re-verified); retrieved 2026-10-22)

[79] [Interpretability without actionability: mechanistic methods cannot correct language model errors despite near-perfect internal representations](https://arxiv.org/html/2603.18353v1) (2026) — Inherited from art_kjrCpQnPaniY Table 92b/92c source [43]; its quotes are cited by row id and were not re-fetched here. (version: v1; status: INHERITED (cited by id; not re-verified); retrieved 2026-10-22)

[80] [On the Non-Identifiability of Steering Vectors in Large Language Models](https://arxiv.org/html/2602.06801v4) (Sohan Venkatesh, Ashish Mahendran Kurapath; 2026) — On the Non-Identifiability of Steering Vectors (Venkatesh et al.); cited in rows 92e-P2-8. (version: v4; venue: Code available at https://github.com/sohv/non-identifiability; status: VERIFIED; retrieved 2026-10-22)

> We show that, under white-box single-layer access, steering vectors are fundamentally non-identifiable due to large equivalence classes of behaviorally indistinguishable interventions.

Locator: Abstract (P2-8; VERIFIED)

[81] [Steering off Course: Reliability Challenges in Steering Language Models](https://arxiv.org/html/2504.04635v1) (Patrick Queiroz Da Silva, Hari Sethuraman, Dheeraj Rajagopal, Hannaneh Hajishirzi, Sachin Kumar; 2025) — Steering off Course (Da Silva et al.); cited in rows 92e-P2-1. (version: v1; venue: arXiv preprint; status: VERIFIED; retrieved 2026-10-22)

> Our analysis demonstrate fundamental flaws in the assumptions underlying these methods, challenging their reliability as scalable steering solutions

Locator: Abstract (P2-1; VERIFIED)

[82] [How Far Ahead Do LLMs Plan? Uncovering the Latent Horizon in Chain-of-Thought Reasoning](https://arxiv.org/html/2602.02103v2) (Liyan Xu, Mo Yu, Fandong Meng, Jie Zhou; 2026) — How Far Ahead Do LLMs Plan? (Xu et al.); cited in rows 92e-P2-6. (version: v2; venue: Accepted to ICML 2026; status: VERIFIED; retrieved 2026-10-22)

> we investigate the latent planning strength of LLMs, through our probing method, Tele-Lens, applying to hidden states across diverse task domains.

Locator: Abstract (P2-6; VERIFIED)

[83] [Representing and Steering a Hypothesized Consciousness Spectrum: Manifold-Guided vs. Linear Directions (OpenReview forum MN9X374VhG)](https://api2.openreview.net/notes/search?term=Representing%20and%20Steering%20a%20Hypothesized%20Consciousness%20Spectrum&group=ICLR.cc/2027/Conference&limit=10) (2026) — ICLR 2027 Conference Submission; contemporaneous. Cited in rows 92e-P3-4. (version: submission; venue: ICLR 2027 Conference Submission; status: VERIFIED-ABSTRACT; retrieved 2026-10-22)

> show that both a linear direction and a low-dimensional manifold structure align with it.

Locator: OpenReview abstract (forum MN9X374VhG) (P3-4; VERIFIED-ABSTRACT)

[84] [Hot or Cold? Adaptive Temperature Sampling for Code Generation with Large Language Models](https://arxiv.org/html/2309.02772v3) (2023) — Inherited from art_kjrCpQnPaniY Table 92b/92c source [8]; its quotes are cited by row id and were not re-fetched here. (version: v3; status: INHERITED (cited by id; not re-verified); retrieved 2026-10-22)

[85] [Gumbel Counterfactual Generation From Language Models](https://arxiv.org/html/2411.07180v5) (2024) — Inherited from art_kjrCpQnPaniY Table 92b/92c source [33]; its quotes are cited by row id and were not re-fetched here. (version: v5; status: INHERITED (cited by id; not re-verified); retrieved 2026-10-22)

[86] [Beneath the Diff: Diagnosing and Mitigating Algorithmic Mode Collapse in Code-Level Autonomous Research Loops](https://arxiv.org/html/2609.00077v1) (2026) — Inherited from art_kjrCpQnPaniY Table 92b/92c source [29]; its quotes are cited by row id and were not re-fetched here. (version: v1; status: INHERITED (cited by id; not re-verified); retrieved 2026-10-22)

[87] [Tethered Reasoning: Decoupling Entropy from Hallucination in Quantized LLMs via Manifold Steering](https://arxiv.org/html/2602.17691v1) (Craig Atkinson; 2026) — HELIX / Tethered Reasoning (Atkinson); cited in rows 92e-P4-2. (version: v1; venue: 16 pages, 6 tables; status: VERIFIED; retrieved 2026-10-22)

> Quantized language models face a fundamental dilemma: low sampling temperatures yield repetitive, mode-collapsed outputs, while high temperatures

Locator: Abstract (P4-2; VERIFIED)

[88] [Diversity Without Discovery: Why Chain Perturbation Fails to Explore in Latent Test-Time Scaling](https://api2.openreview.net/notes/search?term=Diversity%20Without%20Discovery%3A%20Why%20Chain%20Perturbation%20Fails%20to%20Explore%20in%20Latent%20Test-Time%20Scaling&group=ICLR.cc/2027/Conference&limit=10) (2026) — Inherited from art_kjrCpQnPaniY Table 92b/92c source [63]; its quotes are cited by row id and were not re-fetched here. (status: INHERITED (cited by id; not re-verified); retrieved 2026-10-22)

[89] [Intent Factored Generation: Unleashing the Diversity in Your Language Model](https://arxiv.org/html/2506.09659v1) (2025) — Inherited from art_kjrCpQnPaniY Table 92b/92c source [26]; its quotes are cited by row id and were not re-fetched here. (version: v1; status: INHERITED (cited by id; not re-verified); retrieved 2026-10-22)

[90] [Planning In Natural Language Improves LLM Search For Code Generation](https://arxiv.org/html/2409.03733v2) (2024) — Inherited from art_kjrCpQnPaniY Table 92b/92c source [27]; its quotes are cited by row id and were not re-fetched here. (version: v2; status: INHERITED (cited by id; not re-verified); retrieved 2026-10-22)

[91] [Latent Plan Transformer for Trajectory Abstraction: Planning as Latent Space Inference](https://arxiv.org/html/2402.04647v4) (Deqian Kong, Dehong Xu, Minglu Zhao, Bo Pang, Jianwen Xie, Andrew Lizarraga, Yuhao Huang, Sirui Xie, Ying Nian Wu; 2024) — Latent Plan Transformer (Kong et al.); cited in rows 92e-P5-4. (version: v4; venue: arXiv preprint; status: VERIFIED; retrieved 2026-10-22)

> We introduce the Latent Plan Transformer (LPT), a novel model that leverages a latent variable to connect a Transformer-based trajectory generator and the final return.

Locator: Abstract (P5-5; VERIFIED)

[92] [kitft/natural_language_autoencoders README (released NLA checkpoints)](https://raw.githubusercontent.com/kitft/natural_language_autoencoders/main/README.md) (2026) — Lists the 8 released checkpoints (4 base models x AV/AR) with layers, and requires loading nla_meta.yaml. (version: main branch; venue: GitHub; status: VERIFIED-README; retrieved 2026-10-22)

> Qwen2.5-7B-Instruct | 20 / 28 | 3584

Locator: Released checkpoints table (N-9; VERIFIED-README)

> Llama-3.3-70B-Instruct | 53 / 80 | 8192

Locator: Released checkpoints table (N-10; VERIFIED-README)

> Each checkpoint ships an `nla_meta.yaml` sidecar with the prompt template, injection token IDs, and scale factors that the model was trained with — load those, never hardcode them.

Locator: below the checkpoints table (N-11; VERIFIED-README)

[93] [kitft/nla-qwen2.5-7b-L20-av model card (Hugging Face)](https://huggingface.co/kitft/nla-qwen2.5-7b-L20-av) (2026) — Qwen2.5-7B-Instruct AV: extraction at the residual output of block 20; in-distribution fve_nrm 0.752. (version: main; venue: Hugging Face; status: VERIFIED-README; retrieved 2026-10-22)

> Extraction layer: residual stream output of block

Locator: model card (N-12; VERIFIED-README)

[94] [nla_meta.yaml of kitft/nla-qwen2.5-7b-L20-av](https://huggingface.co/kitft/nla-qwen2.5-7b-L20-av/raw/main/nla_meta.yaml) (2026) — Sidecar metadata: extraction_layer_index 20, injection and MSE scales. (version: main; venue: Hugging Face; status: VERIFIED-README; retrieved 2026-10-22)

> extraction_layer_index: 20

Locator: training block (N-14; VERIFIED-README)

[95] [TransformerLens issue #1884: NLA explain/reconstruct proposal](https://github.com/TransformerLensOrg/TransformerLens/issues/1884) (2026) — Tooling proposal for the Qwen2.5-7B NLA pair that lists edited-explanation steering as a non-goal. (version: issue; venue: GitHub; status: VERIFIED-README; retrieved 2026-10-22)

> Edited-explanation steering or causal validation.

Locator: Non-goals (N-32; VERIFIED-README)

[96] [Activation Oracles: Training and Evaluating LLMs as General-Purpose Activation Explainers](https://arxiv.org/html/2512.15674v2) (Adam Karvonen, James Chua, Clément Dumas, Kit Fraser-Taliente, Subhash Kantamneni, Julian Minder, Euan Ong, Arnab Sen Sharma, Daniel Wen, Owain Evans, Samuel Marks; 2025) — Activation Oracles (Karvonen et al.); cited in rows 92e-N-6. (version: v2; venue: 36 pages; status: VERIFIED; retrieved 2026-10-22)

> we study Activation Oracles (AOs): models trained to answer arbitrary natural-language questions about LLM activations.

Locator: Sec. 1 Introduction (N-19; VERIFIED)

[97] [Natural Language Autoencoders can verbalize influence but don't report whether it changed the outcome](https://jaisood.substack.com/p/natural-language-autoencoders-can) (Jai Sood; 2026) — Grey-literature audit of two released NLA checkpoints: the readout reports applied pressure and answer, not whether the pressure changed the answer. (version: post (Aug 18, 2026); venue: Substack; status: VERIFIED-BLOG; retrieved 2026-10-22)

> We audit two released NLA checkpoints and find that the readout reports what pressure was applied and what the model answered, but not whether the pressure changed that answer.

Locator: Introduction (N-21; VERIFIED-BLOG)

[98] [Probing Latent Colombian Identity Inferences in Qwen2.5-7B with Natural Language Autoencoders](https://arxiv.org/html/2607.21774v1) (Pablo Santiago Potes Velasco, María del Mar García Matabanchoy, Óscar Julián Pérez Ladino, Jhoan Stevan Mosquera Ortiz, Nicolás Lozano Mazuera, Gilber Alexis Corrales Gallego; 2026) — Colombian identity with NLA (Potes Velasco et al.); cited in rows 92e-N-9. (version: v1; venue: arXiv preprint; status: VERIFIED; retrieved 2026-10-22)

> We use Natural Language Autoencoders (NLA) to verbalize residual-stream activations from layer 20 across four positional quartiles per prompt.

Locator: Abstract (N-25; VERIFIED)

[99] [ceselder/nanoNLA (nanonla-l24-av-qwen3-8b) model card](https://huggingface.co/ceselder/nanoNLA) (2026) — Community NLA activation verbalizer for Qwen3-8B at layer 24 (Karvonen injection). (version: main; venue: Hugging Face; status: VERIFIED-README; retrieved 2026-10-22)

[100] [ceselder/nanoNLA README](https://raw.githubusercontent.com/ceselder/nanoNLA/main/README.md) (2026) — Minimal NLA reimplementation; carries a faithfulness disclaimer and points users to another repository. (version: main; venue: GitHub; status: VERIFIED-README; retrieved 2026-10-22)

> Faithfulness disclaimer — this is a perpetual work-in-progress.

Locator: Faithfulness disclaimer (N-27; VERIFIED-README)

[101] [syvb/EasyNLA README](https://raw.githubusercontent.com/syvb/EasyNLA/main/README.md) (2026) — NLA training codebase built on nanoNLA; reports ~70% held-out FVE on Qwen3-8B layer 24. (version: main; venue: GitHub; status: VERIFIED-README; retrieved 2026-10-22)

> On Qwen3-8B (layer 24) the default config reaches

Locator: Overview (N-28; VERIFIED-README)

[102] [Measuring Activation Control in Large Language Models](https://arxiv.org/html/2608.21664v1) (Marek Mateusz Kowalski, Joshua Fonseca Rivera, Uzay Macar, David Demitri Africa; 2026) — Measuring Activation Control (Kowalski et al.); cited in rows 92e-N-12. (version: v1; venue: 19 figures, 4 tables. Code: https://github.com/mkobalski/activation-control. Data: https://huggingface.co/datasets/joshycodes/activation-control-battery; status: VERIFIED; retrieved 2026-10-22)

> this level of control can evade activation-based monitoring methods (including linear probes, natural language autoencoders, activation oracles, and the Jacobian lens), albeit imperfectly.

Locator: Abstract (N-30; VERIFIED)

[103] [Understanding Confabulation and Rethinking Reconstruction in Activation Explanations](https://arxiv.org/html/2609.33702v1) (Gert Lek, Zixuan Xia, Pin-Yu Chen, Lydia Y. Chen; 2026) — Understanding Confabulation (Lek et al.); cited in rows 92e-N-12. (version: v1; venue: 18 pages, 9 figures; status: VERIFIED; retrieved 2026-10-22)

> explanations become more useful for predicting model behavior while also increasingly introducing unsupported details and exhibiting writing defects.

Locator: Abstract (N-31; VERIFIED)

[104] [Announcing Gemma Scope 2 (LessWrong / AI Alignment Forum)](https://www.lesswrong.com/posts/YQro5LyYjDzZrBCdb/announcing-gemma-scope-2) (2025) — Release post dated 22 Dec 2025; every PT SAE has a version finetuned for IT models. (version: post; venue: LessWrong / AI Alignment Forum; status: VERIFIED-BLOG; retrieved 2026-10-22)

> every SAE trained on a PT model has a corresponding version finetuned for IT models

Locator: TLDR (S-1; VERIFIED-BLOG)

> 22nd Dec 2025

Locator: byline (S-2; VERIFIED-BLOG)

[105] [Gemma Scope 2 Technical Paper (Google DeepMind)](https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/gemma-scope-2-helping-the-ai-safety-community-deepen-understanding-of-complex-language-model-behavior/Gemma_Scope_2_Technical_Paper.pdf) (2025) — IT SAEs are initialized from PT SAEs and finetuned on rollout-derived data. (version: PDF; venue: Google DeepMind technical report; status: VERIFIED; retrieved 2026-10-22)

> from the corresponding PT SAEs and finetune on the rollout-derived datasets.

Locator: training of IT SAEs (S-3; VERIFIED)

[106] [google/gemma-scope-2-4b-it model card](https://huggingface.co/google/gemma-scope-2-4b-it) (2025) — Sites (resid_post, attn_out, mlp_out, transcoders) at 4 depths (25/50/65/85%) with several widths and L0 values. (version: main; venue: Hugging Face; status: VERIFIED-README; retrieved 2026-10-22)

> contain SAEs at 4 different layers (25%, 50%, 65% and 85% depth) and a variety of widths & L0 values

Locator: What is in this repo (S-4; VERIFIED-README)

[107] [I Have Covered All the Bases Here: Interpreting Reasoning Features in Large Language Models via Sparse Autoencoders](https://arxiv.org/html/2503.18878v2) (Andrey Galichin, Alexey Dontsov, Polina Druzhinina, Anton Razzhigaev, Oleg Y. Rogov, Elena Tutubalina, Ivan Oseledets; 2025) — I Have Covered All the Bases Here (Galichin et al.); cited in rows 92e-S-4. (version: v2; venue: arXiv preprint; status: VERIFIED; retrieved 2026-10-22)

> Through steering experiments, we demonstrate that amplifying these features increases performance on reasoning-intensive benchmarks

Locator: Abstract (S-14; VERIFIED)

[108] [SAE Interventions are Unreliable: Post-Intervention Recovery of Suppressed Behavior](https://arxiv.org/html/2606.18322v1) (Mingyue Cui, Linghui Shen, Xingyi Yang; 2026) — SAE Interventions are Unreliable (Cui et al.); cited in rows 92e-S-7. (version: v1; venue: Code: https://github.com/Mingyuee88/sae-post-intervention-recovery, Project page: https://mingyuee88.github.io/sae-post-intervention-recovery/; status: VERIFIED; retrieved 2026-10-22)

> the clamp may block one visible route to a behavior without eliminating the behavior itself.

Locator: Abstract (S-18; VERIFIED)

[109] [Do LMs Know What Variables Do? Interpreting Code Representations via Variable Roles (OpenReview forum 2AiBLDA67W)](https://api2.openreview.net/notes/search?term=Do%20LMs%20Know%20What%20Variables%20Do%3F%20Interpreting%20Code%20Representations%20via%20Variable%20Roles&group=ICLR.cc/2027/Conference&limit=10) (2026) — ICLR 2027 Conference Submission; contemporaneous. Cited in rows 92e-S-7. (version: submission; venue: ICLR 2027 Conference Submission; status: VERIFIED-ABSTRACT; retrieved 2026-10-22)

> residual probes outperform individual SAE features and tested lexical baselines

Locator: OpenReview abstract (forum 2AiBLDA67W) (S-19; VERIFIED-ABSTRACT)

[110] [On the Biology of a Large Language Model (Transformer Circuits)](https://transformer-circuits.pub/2025/attribution-graphs/biology.html) (2025) — Attribution-graph caveat: satisfying insight for about a quarter of the prompts tried. (version: HTML; venue: Transformer Circuits Thread; status: VERIFIED; retrieved 2026-10-22)

> ve found that our attribution graphs provide us with satisfying insight for about a quarter of the prompts we

Locator: Introduction (limitations) (S-20; VERIFIED)

[111] [PRISM: Transfer and Limits of Activation Interventions in Tool-Calling Language Models](https://arxiv.org/html/2610.20808v1) (Giovana Kerche Bonás, Thales Sales Almeida, Marcelo da Silva Reis, Rodrigo Nogueira, Marcos Meideiros Raimundo; 2026) — PRISM (Bonas et al.); cited in rows 92e-E-5. (version: v1; venue: arXiv preprint; status: VERIFIED; retrieved 2026-10-22)

> we introduce PRISM, a framework for evaluating the transfer of activation interventions across precision, languages, and scales.

Locator: Abstract (E-10; VERIFIED)

[112] [Interpreting the Effects of Quantization on LLMs](https://arxiv.org/html/2508.16785v3) (Manpreet Singh, Hassan Sajjad; 2025) — Interpreting the Effects of Quantization on LLMs (Singh, Sajjad); cited in rows 92e-E-6. (version: v3; venue: Accepted to AACL 2025 Main; status: VERIFIED; retrieved 2026-10-22)

> Our findings reveal that the impact of quantization on model calibration is generally minor.

Locator: Abstract (E-14; VERIFIED)

[113] [Through a Compressed Lens: Investigating The Impact of Quantization on Factual Knowledge Recall](https://arxiv.org/html/2505.13963v3) (Qianli Wang, Mingyang Wang, Nils Feldhus, Simon Ostermann, Yuan Cao, Hinrich Schütze, Sebastian Möller, Vera Schmitt; 2025) — Through a Compressed Lens (Wang et al.); cited in rows 92e-E-6. (version: v3; venue: TrustNLP @ ACL 2026; camera-ready version; status: VERIFIED; retrieved 2026-10-22)

> We show that quantization typically results in information loss within LLMs, consequently diminishing their capacity for FKR.

Locator: Abstract (E-15; VERIFIED)

[114] [Greedy Decoding Is Not Precision-Invariant: Cross-Precision Output Divergence in LLM Inference](https://arxiv.org/pdf/2609.26621v1) (Gaoyuan Du, Anam Nawaz Khan, Rex Zhou, Xiaoyang Liu, Deepayan Chakrabarti, Fnu Suya, Xueping Li; 2026) — Greedy Decoding Is Not Precision-Invariant (Du et al.); cited in rows 92e-E-7. (version: v1; venue: Accepted by Transactions on Machine Learning Research (TMLR), 2026 | Transactions on Machine Learning Research, 2026; status: VERIFIED; retrieved 2026-10-22)

> different outputs in BF16 versus FP16 on identical hardware.

Locator: Abstract (PDF; no arXiv HTML) (E-17; VERIFIED)

[115] [Understanding and Mitigating Numerical Sources of Nondeterminism in LLM Inference](https://arxiv.org/html/2506.09501v2) (Jiayi Yuan, Hao Li, Xinheng Ding, Wenya Xie, Yu-Jhe Li, Wentian Zhao, Kun Wan, Jing Shi, Xia Hu, Zirui Liu; 2025) — Understanding and Mitigating Numerical Sources of Nondeterminism (Yuan et al.); cited in rows 92e-E-7. (version: v2; venue: arXiv preprint; status: VERIFIED; retrieved 2026-10-22)

> under bfloat16 precision with greedy decoding, a reasoning model like DeepSeek-R1-Distill-Qwen-7B can exhibit up to 9% variation in accuracy and 9,000 tokens difference in response length due to differences in GPU count, type, and evaluation batch size.

Locator: Abstract / Sec. 1 (E-18; VERIFIED)

[116] [arXiv abs page 2506.09501v1: Give Me FP32 or Give Me Death? Challenges and Solutions for Reproducible Reasoning](https://arxiv.org/abs/2506.09501v1) (2025) — Confirms the v1 title and the 'up to 9%' abstract sentence. (version: v1; venue: arXiv; status: VERIFIED; retrieved 2026-10-22)

> Give Me FP32 or Give Me Death? Challenges and Solutions for Reproducible Reasoning

Locator: abs page v1 (E-19; VERIFIED)

[117] [Hidden Reliability Risks in Large Language Models: Systematic Identification of Precision-Induced Output Disagreements](https://arxiv.org/html/2604.19790v1) (Yifei Wang, Tianlin Li, Xiaohan Zhang, Xiaoyu Zhang, Wei Ma, Mingfei Cheng, Li Pan; 2026) — Hidden Reliability Risks: Precision-Induced Output Disagreements (Wang et al.); cited in rows 92e-E-7. (version: v1; venue: 12 pages, 5 figures; status: VERIFIED; retrieved 2026-10-22)

> Evaluations across five open-source models yield average detection success rates of 84.0% for bfloat16 vs. float16 and 99.5% for int16 vs. int8 transitions.

Locator: Sec. 1 contributions (E-25; VERIFIED)

[118] [LLM.int8(): 8-bit Matrix Multiplication for Transformers at Scale](https://arxiv.org/html/2208.07339v2) (Tim Dettmers, Mike Lewis, Younes Belkada, Luke Zettlemoyer; 2022) — LLM.int8() (Dettmers et al.); cited in rows 92e-E-8. (version: v2; venue: Published at NeurIPS 2022. Camera-ready version; status: VERIFIED; retrieved 2026-10-22)

> the sparse but systematic large magnitude outlier features that ruin quantization precision once they emerge in all transformer layers starting at scales of 6.7B parameters.

Locator: Abstract (E-20; VERIFIED)

[119] [SmoothQuant: Accurate and Efficient Post-Training Quantization for Large Language Models](https://arxiv.org/html/2211.10438v7) (Guangxuan Xiao, Ji Lin, Mickael Seznec, Hao Wu, Julien Demouth, Song Han; 2022) — SmoothQuant (Xiao et al.); cited in rows 92e-E-8. (version: v7; venue: ICML 2023. First two authors contributed equally to this work; status: VERIFIED; retrieved 2026-10-22)

> SmoothQuant smooths the activation outliers by offline migrating the quantization difficulty from activations to weights with a mathematically equivalent transformation.

Locator: Abstract (E-21; VERIFIED)

[120] [Massive Activations in Large Language Models](https://arxiv.org/html/2402.17762v2) (Mingjie Sun, Xinlei Chen, J. Zico Kolter, Zhuang Liu; 2024) — Massive Activations (Sun et al.); cited in rows 92e-E-8. (version: v2; venue: First Conference on Language Modeling (COLM), 2024. Website at https://eric-mingjie.github.io/massive-activations/index.html; status: VERIFIED; retrieved 2026-10-22)

> we find their values largely stay constant regardless of the input, and they function as indispensable bias terms in LLMs.

Locator: Abstract (E-22; VERIFIED)

[121] [FP8 Formats for Deep Learning](https://arxiv.org/html/2209.05433v2) (Paulius Micikevicius, Dusan Stosic, Neil Burgess, Marius Cornea, Pradeep Dubey, Richard Grisenthwaite, Sangwon Ha, Alexander Heinecke, Patrick Judd, John Kamalu, Naveen Mellempudi, Stuart Oberman; 2022) — FP8 Formats for Deep Learning (Micikevicius et al.); cited in rows 92e-E-8. (version: v2; venue: arXiv preprint; status: VERIFIED; retrieved 2026-10-22; author list truncated to the first names shown by the source)

> two encodings - E4M3 (4-bit exponent and 3-bit mantissa) and E5M2 (5-bit exponent and 2-bit mantissa).

Locator: Abstract (E-23; VERIFIED)

## Verification

Numbered citations resolve to unique listed sources. Passage checks test text occurrence, not claim truth or entailment. Author/year metadata and locators are not independently verified. Details: `research_verification.json`.

- Source [1]: text found — We can make a targeted edit to the NLA explanation, convert the modified explanation into an activat
- Source [1]: text found — We then steer with this direction at the newline token only, at the layer the NLA is trained on.
- Source [1]: text found — We note that steering is only successful roughly 50% of the time and the completions are not always 
- Source [1]: text found — by editing an explanation and reconstructing both the original and edited versions with the AR, we o
- Source [2]: text found — The trained decoder also enables control by providing a differentiable loss to steer activations tow
- Source [2]: text found — we demonstrate that the decoder is precise enough to steer the target model to exhibit behaviors uns
- Source [3]: text found — We propose Supervised Control, which allows editing open-ended concepts while only requiring gradien
- Source [4]: text found — Proceedings of the 41st International Conference on Machine
- Source [5]: text found — Dreaming Vectors: Gradient-descented steering vectors from Activation Oracles and using them to Red-
- Source [6]: text found — of their specific claims are ones the reconstruction depends on. The score therefore tracks the inpu
- Source [7]: text found — C2 and C3 are not recovered by any probe: a census of every active feature finds no rhyme-anticipati
- Source [8]: text found — We systematically study activation steering under weight-only quantization (INT8 and NF4) across fou
- Source [8]: text found — Activations remain in FP16/BF16 throughout the forward pass.
- Source [8]: text found — we find that sentiment steering survives quantization intact.
- Source [8]: text found — demonstrating that compression can dominate the steering intervention.
- Source [9]: text found — Preserving standard model quality or direction-level representation similarity does not guarantee th
- Source [9]: text found — Intervention effects can change even when directions
- Source [10]: text found — We study steering compatibility with the intervention layer, direction, and strength held fixed acro
- Source [10]: text found — We show that ordinary output fidelity alone does not guarantee
- Source [11]: text found — using BF16, GPTQ, FP8 weight-and-activation quantization, and FP8 KV-cache quantization.
- Source [12]: text found — Dynamic, per-token quantization on the activations
- Source [13]: text found — existing causal abstraction methods have two major limitations: they require a brute-force search ov
- Source [14]: text found — For causal variable localization, we find that the supervised DAS method performs best, while SAE fe
- Source [15]: text found — we introduce a novel distribution matching objective tailored for the steering task by aligning inte
- Source [17]: text found — Code models write Python when the prompt does not say which language to use. We ask a mechanistic qu
- Source [18]: text found — Adding them after the first sampled token changes held-out outputs, but effects depend on model and 
- Source [20]: text found — This pipeline yields a compact set of 23 intervention targets in Qwen3-8B.
- Source [20]: text found — We use this functionally aligned contrast to screen sparse autoencoder features at the final prompt 
- Source [20]: text found — same-size, layer-count-matched random null interventions reduce accuracy by only
- Source [21]: text found — To identify the few strategy-specific features from the vast pool of SAE features, we propose SAE-St
- Source [21]: text found — Think Intervention (Wu et al., 2025), which inserts human-crafted instructions into the middle of th
- Source [22]: text found — For steering, we find that prompting outperforms all existing methods, followed by finetuning.
- Source [22]: text found — For concept detection, representation-based methods such as difference-in-means, perform the best. O
- Source [23]: text found — We find that Sparse Autoencoders can, in fact, perform close to on par with the reference LoRA perfo
- Source [24]: text found — We introduce prolepsis: a transformer commits early, task-specific attention heads sustain the commi
- Source [24]: text found — Planning is invisible to six residual-stream methods; among those tested, only CLT-based steering su
- Source [25]: text found — here for models of size 270M, 1B, 4B, 12B, and 27B, PT and
- Source [26]: text found — Transcoders trained on Qwen-3 models from 0.6B to 14B
- Source [27]: text found — even the less-successful Qwen-3 4B-8B have nascent planning mechanisms.
- Source [27]: text found — For our experiments, we use Hanna et al.
- Source [27]: text found — Note that although these models are instruction-tuned
- Source [31]: text found — before a block is decoded, a small conditional flow samples a low-dimensional
- Source [32]: text found — current latent models remain largely deterministic, capturing only a single reasoning trajectory rat
- Source [33]: text found — which diversifies latent trajectories by randomly rescaling coefficients in the fixed SVD basis of a
- Source [34]: text found — one direction acts as a switch into the random-choice mode, whereas a separate direction shapes the 
- Source [34]: text found — This decomposition enables a mechanism-guided intervention that improves sampling without task-speci
- Source [39]: text found — We apply Boundless DAS to the Alpaca model (7B parameters), which, off the shelf, solves a simple nu
- Source [42]: text found — disturbing the discovered shared subspace degrades decision performance far more than disturbing eit
- Source [43]: text found — A low-rank output-sensitive component containing 15.4% of the direction
- Source [44]: text found — whether success is decodable before generation from a coordinate outside an evaluated refusal subspa
- Source [45]: text found — This allows us to immediately formalize the representation of categorical concepts as polytopes in t
- Source [46]: text found — we explore whether some language model representations may be inherently multi-dimensional.
- Source [50]: text found — We hypothesize that there exist key forking tokens, such that re-sampling the system at those specif
- Source [51]: text found — We apply a forking-paths-style analysis to behavioral evaluations and find that as generation progre
- Source [52]: text found — under preregistered controls: a wrong-activation (shuffled) control, a visible-text baseline, a blin
- Source [52]: text found — apparent successes on famous facts are indistinguishable from verbalizer prior-completion under a tr
- Source [53]: text found — use SAEs from the GemmaScope-2 release (McDougall et al., 2025), each with 16,384 features trained o
- Source [53]: text found — A small steering study yields minimal changes on the evaluated benchmarks.
- Source [57]: text found — We find that, on toy arithmetic and vision tasks, the algorithms identified by DAS and TLA mostly ag
- Source [58]: text found — we employ causal activation patching Heimersheim and Nanda (2024) to assess the integrity of the inf
- Source [59]: text found — None of them predicts which layers benefit from restored precision.
- Source [60]: text found — These results show that behavioral metrics alone are insufficient evidence that full-precision inter
- Source [61]: text found — Because common GPU kernels are not batch-invariant and floating-point formats round differently, the
- Source [64]: text found — Finding Alignments Between Interpretable Causal Variables and Distributed Neural Representations
- Source [65]: text found — a low-rank activation subspace learned so that interchanging it moves the model's answer the way the
- Source [66]: text found — Chat models sometimes commit to an answer and then produce reasoning that justifies the commitment r
- Source [67]: text found — We apply this pipeline to both base and instruction-tuned Gemma-2-2B models on the MBPP code generat
- Source [68]: text found — compact subspaces that are necessary and sufficient for a task and that recur across independently t
- Source [69]: text found — on an experiment using randomly initialised language models, our alignment maps reach 100% interchan
- Source [70]: text found — this effect may be achieved by activating a
- Source [71]: text found — Is This the Subspace You Are Looking for? An Interpretability Illusion for Subspace Activation Patch
- Source [72]: text found — can reject explanations they consider
- Source [72]: text found — We then argue that the illusions Makelov et al. (2023) see in practice are artifacts of their traini
- Source [73]: text found — minimizing divergence magnitude does not guarantee elimination of hidden pathways; it only reduces t
- Source [74]: text found — No method currently tells the two cases apart.
- Source [75]: text found — we find that the NIE does not solely capture the causal effect through the specific component.
- Source [76]: text found — The discovered circuits appear specialized by frequency when compared structurally, but functional a
- Source [77]: text found — A purposive audit of 10 papers across four methodological strands finds no dedicated identification-
- Source [80]: text found — We show that, under white-box single-layer access, steering vectors are fundamentally non-identifiab
- Source [81]: text found — Our analysis demonstrate fundamental flaws in the assumptions underlying these methods, challenging 
- Source [82]: text found — we investigate the latent planning strength of LLMs, through our probing method, Tele-Lens, applying
- Source [83]: text found — show that both a linear direction and a low-dimensional manifold structure align with it.
- Source [87]: text found — Quantized language models face a fundamental dilemma: low sampling temperatures yield repetitive, mo
- Source [91]: text found — We introduce the Latent Plan Transformer (LPT), a novel model that leverages a latent variable to co
- Source [92]: text found — Qwen2.5-7B-Instruct | 20 / 28 | 3584
- Source [92]: text found — Llama-3.3-70B-Instruct | 53 / 80 | 8192
- Source [92]: text found — Each checkpoint ships an `nla_meta.yaml` sidecar with the prompt template, injection token IDs, and 
- Source [93]: text found — Extraction layer: residual stream output of block
- Source [94]: text found — extraction_layer_index: 20
- Source [95]: text found — Edited-explanation steering or causal validation.
- Source [96]: text found — we study Activation Oracles (AOs): models trained to answer arbitrary natural-language questions abo
- Source [97]: text found — We audit two released NLA checkpoints and find that the readout reports what pressure was applied an
- Source [98]: text found — We use Natural Language Autoencoders (NLA) to verbalize residual-stream activations from layer 20 ac
- Source [100]: text found — Faithfulness disclaimer — this is a perpetual work-in-progress.
- Source [101]: text found — On Qwen3-8B (layer 24) the default config reaches
- Source [102]: text found — this level of control can evade activation-based monitoring methods (including linear probes, natura
- Source [103]: text found — explanations become more useful for predicting model behavior while also increasingly introducing un
- Source [104]: text found — every SAE trained on a PT model has a corresponding version finetuned for IT models
- Source [104]: text found — 22nd Dec 2025
- Source [105]: text found — from the corresponding PT SAEs and finetune on the rollout-derived datasets.
- Source [106]: text found — contain SAEs at 4 different layers (25%, 50%, 65% and 85% depth) and a variety of widths & L0 values
- Source [107]: text found — Through steering experiments, we demonstrate that amplifying these features increases performance on
- Source [108]: text found — the clamp may block one visible route to a behavior without eliminating the behavior itself.
- Source [109]: text found — residual probes outperform individual SAE features and tested lexical baselines
- Source [110]: text found — ve found that our attribution graphs provide us with satisfying insight for about a quarter of the p
- Source [111]: text found — we introduce PRISM, a framework for evaluating the transfer of activation interventions across preci
- Source [112]: text found — Our findings reveal that the impact of quantization on model calibration is generally minor.
- Source [113]: text found — We show that quantization typically results in information loss within LLMs, consequently diminishin
- Source [114]: text found — different outputs in BF16 versus FP16 on identical hardware.
- Source [115]: text found — under bfloat16 precision with greedy decoding, a reasoning model like DeepSeek-R1-Distill-Qwen-7B ca
- Source [116]: text found — Give Me FP32 or Give Me Death? Challenges and Solutions for Reproducible Reasoning
- Source [117]: text found — Evaluations across five open-source models yield average detection success rates of 84.0% for bfloat
- Source [118]: text found — the sparse but systematic large magnitude outlier features that ruin quantization precision once the
- Source [119]: text found — SmoothQuant smooths the activation outliers by offline migrating the quantization difficulty from ac
- Source [120]: text found — we find their values largely stay constant regardless of the input, and they function as indispensab
- Source [121]: text found — two encodings - E4M3 (4-bit exponent and 3-bit mantissa) and E5M2 (5-bit exponent and 2-bit mantissa

## Follow-up Questions

- Do the ICLR 2027 submissions 'Stable Directions, Different Effects' and 'Activation Steering under Low-Bit Quantization' quantize activations (W8A8/FP8) or only weights? Their full texts decide whether flag B fires.
- On the released Qwen2.5-7B-Instruct L20 NLA, how far does the AR reconstruction move when only the algorithm name in an explanation is edited? The ~2% claim-dependence result predicts a small move, so this should be measured before the edit-and-steer arm.
- Would interchange/DAS at Qwen3-8B's final prompt position find a low-rank variable for algorithm choice? How does it relate to the 23 SAE targets of 'Before Reasoning Begins' and to the Qwen-3 PLTs in circuit-tracer?

---
*Generated by AI Inventor Pipeline*
