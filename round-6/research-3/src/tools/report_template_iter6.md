# Who already found the hidden plan? Positioning audit for iteration-6 claims (Table 92e)

*Retrieval date: 2026-10-22. This audit covers iteration-6 claims P1-P5, N, S and E. It extends Tables 92b/92c (art_kjrCpQnPaniY) and 92d (art_ObxQOIlAM9MS) and cites their rows by id without re-verifying them. Every new quote below is copied from the source's own versioned text: arXiv HTML (the PDF where no HTML exists), a transformer-circuits page, a PMLR or ICLR page, an OpenReview API record, a Hugging Face card or a GitHub README. Each quote was checked against a cached copy of that text, and then re-matched live by an independent fetch_grep pass. Rows state design facts only and quote no run-internal result.*

## 1. Summary

- **The four flags.** A: NOT FIRED (narrowly). B: PARTLY FIRED. C: FIRED. D: PARTLY FIRED.
- **N is a replication, not a new method.** The NLA paper (Transformer Circuits, 7 May 2026) already does what N proposes {{nla}}. It edits the explanation of a *plan* (the rhyme word on the newline), turns the edit into an activation with the AR, and steers at the newline only. This works "roughly 50% of the time".
  - Verbaliser kin also steer: LatentQA {{2412.08686v2}}, SelfIE {{2403.10949v2,pmlr_selfie_chen24ao}}, and Dreaming Vectors, which takes steering vectors from Activation Oracles {{lw_dreaming_vectors}}.
  - N's causal arm is therefore a **replication in a new setting**: algorithm choice in code, Qwen2.5-7B-Instruct at L20, and new controls.
  - Two 2026 results argue against assuming the edit will work. On a released Qwen-2.5-7B verbalizer, only "as few as" about 2% of specific claims are ones the reconstruction depends on {{2607.20379v2}}. A stress test on open models found no newline-resident rhyme plan {{2609.18440v1}}.
- **E is open in the published record, but crowded by contemporaneous submissions.**
  - In the arXiv record, steering effect sizes under quantization have been compared with full precision only for weight-only INT8/NF4: "Activations remain in FP16/BF16 throughout the forward pass" {{2609.06473v1}}.
  - Two ICLR 2027 submissions show that the same steering direction can have a different effect at another precision, even when the directions stay aligned {{or_8iTqrW1sxY,or_h57duZqLOr}}. Their abstracts do not say whether activations are quantized, and their PDFs returned HTTP 403.
  - Among the sources found, FP8 weight-and-activation quantization appears only in a non-determinism study with no perturbations {{or_9kskCmPMqd}}.
  - **No source found (search dated 2026-10-22) measures how activation rounding (FP8 W8A8, dynamic per-token scales {{llmcompressor_fp8_readme}}) changes the effect size of random activation perturbations.**
- **P1: the method is published, the object is open.**
  - DAS is the standard method for localizing a causal variable {{2303.02536v4,2504.13151v2}}.
  - DAS has already been used for steering validated by generation, but on refusal and a CoT backdoor, not on a plan {{2602.05234v2}}.
  - In the sources found, algorithm choice in code has been moved only by prompt cues (92c source {{inh_c_30}}). Code attributes that are not the algorithm (language, library, coding habits) have been moved by patching or difference-in-means vectors {{2610.20683v1,or_sbVictHY9s,inh_c_45}}.
  - The nearest same-model, same-site neighbour is an ICLR 2027 submission: SAE-feature targets at Qwen3-8B's final prompt position, with code benchmarks and random-null controls {{or_vH3g2k4lPB}}.
- **S: the method is occupied on a non-code strategy.** SAE-feature steering of *reasoning strategies* beats prompt-based and activation-based baselines, validated by generation {{2601.03595v2}} (ACL 2026).
  - Two priors pull in opposite directions. AxBench (prompting beats steering; SAEs not competitive {{2501.17148v3}}) is countered by its rebuttal {{2605.31183v1}}. On an open-model rhyme-planning task, only CLT-based steering succeeded {{2604.15010v2}}.
  - Qwen-3 transcoders that include 8B exist in circuit-tracer {{circuit_tracer_readme_raw,hf_mwhanna_qwen3_8b_transcoders}}, and a planning study already uses them {{2604.12493v1}}. The paper must therefore say why S runs on Gemma Scope 2.
- **P2, P3 and P4 are ADJACENT-ONLY.**
- **P5 is PARTLY OCCUPIED.** Activation noise and latent-code sampling for diversity are occupied lanes {{inh_c_15,inh_c_14,inh_c_16,or_IhQbFddkBp,or_CtluWEsiX7,or_oTt6XeccGk}}. Resampling a *fitted, causally localized* plan variable is not published. The closest work, a fitted random-choice direction, is an ICLR 2027 submission {{or_eZYeqPZlFr}}.

## 2. Scope, date and method (PRISMA-S items)

- **Protocol.** Frozen and sha256-stamped before the first search call: sha256 `88e3bab2e451d477009ac5c62d284b00e2614a50fc583f86380cc71b26f3c4bc`, stamped 2026-10-22T06:19:27Z (evidence/protocol_iter6.json and .sha256). Amendments are logged with timestamps in evidence/protocol_amendments_iter6.jsonl:
  - an interpretation note on flag A;
  - reuse of prior audit tools;
  - two stop-rule entries.
- **Databases and engines.**
  - E1: OpenAlex/Crossref via the aii-web-tools scholarly search {{openalex}}.
  - E3: arXiv API, sorted by submission date, newest first {{arxiv_api}}.
  - E4: Semantic Scholar search with year=2026, plus citations and references {{s2_api}}.
  - E5: the OpenReview ICLR 2027 pool through api2 notes/search {{openreview_api}}.
  - E6: grey literature through the built-in web search, restricted to transformer-circuits.pub, lesswrong.com, alignmentforum.org, huggingface.co, github.com, neuronpedia.org and substack.com.
- **Strings and rounds.**
  - Round 1: 21 strings over 7 lanes (L1-L7). Every string ran on E3, E4 and E5; L1, L4 and L6 also ran on E1; L4, L5 and L6 also ran on E6.
  - Round 2: 6 strings, each motivated by a named round-1 hit (evidence/round2_queries_iter6.json), run on E1, E3, E4 and E5.
  - Snowballing: forward citations on Semantic Scholar for MIB (<<FC_MIB>> citers) and Emergent Response Planning (<<FC_ERP>> citers). Steering Under Compression had 0 citers, so the backward references of 2609.06473 and 2606.03002 were taken instead.
  - The NLA paper is not indexed by Semantic Scholar title search, so its forward search used E6.
  - Round 3 ran because round 2 produced new hits scoring at least 1.5: forward and backward references of those hits. It found no new hit scoring at least 1.5, so the search stopped (stop rule met).
  - In total: <<N_CALLS>> logged calls (<<N_CALLS_BY_ENGINE>>), each with UTC time, engine, string, hit count and top-20 ids (evidence/search_log_iter6.jsonl).
- **Dates and limits.** Window: 2026-01-01 to 2026-10-22; anchors may be older. Contemporaneity rule inherited from 92d:
  - an arXiv v1 after 2026-06-22 is tagged contemporaneous_4mo;
  - every ICLR 2027 submission is tagged contemporaneous;
  - arXiv-only papers are exempt from the ICLR rule.
- **De-duplication.** <<RAW>> raw hits reduced to <<UNIQUE>> unique records, keyed by arXiv id, then OpenReview forum id, then normalized title.
- **Screening.**
  - <<IN_WINDOW>> records were in the window. A documented keyword pre-screen (lane groups G1-G7, in tools/screen_iter6.py) passed <<KW_PASS>>.
  - Manual title and abstract screening, with full text for the shortlist, led to O/I/C scores for <<SCORED_ROWS>> claim-rows covering <<SCORED_PAPERS>> papers (some anchors predate the window).
  - Results: <<N_OCC>> occupying, <<N_ADJ>> adjacent, <<N_IRR>> irrelevant. In addition, <<IRR_TA>> records were judged irrelevant at title/abstract and <<PRE>> were excluded at the keyword pre-screen.
  - Every in-window record has a one-line verdict in evidence/saturation_hits_iter6.jsonl.
- **Rubric (frozen).** Each axis scores 0, 0.5 or 1; a total of at least 2.5 occupies, 1-2 is adjacent, and below 1 is irrelevant.
  - O (object): 1 = which algorithm a code model writes; 0.5 = a categorical plan, strategy or attribute in another domain.
  - I (instrument): 1 = the claim's own intervention class; 0.5 = a neighbouring intervention.
  - C (criterion): 1 = validated by generation scored by tests or labels; 0.5 = a logit, probe or next-token readout.
- **Quote verification.**
  - <<N_QUOTES>> new quotes from <<N_QREFS>> sources: <<Q_MATCH>> matched the cached source text under the inherited normalization rule (whitespace, ligatures, curly quotes and dashes, html2text emphasis; [...] segments must occur in order).
  - Statuses: <<Q_STATUS>>.
  - QA (Step 4): an independent live fetch_grep pass re-matched <<QA_OK>>/<<QA_N>> quotes (evidence/qa_second_pass_iter6.jsonl).
  - Where arXiv HTML renders a MathML number twice, the quote is split with [...] (2607.20379v2, 2602.17691v1, 2602.05234v2).
  - No number in this report comes from a text that could not be retrieved.
- **Inherited material.** 92b/92c/92d rows and quotes are cited by id (evidence/inherited_index.json: 207 sources). For the 8 flag-critical inherited references, the arXiv API was rechecked: none has a newer version than the one inherited (2601.22010, 2605.11936, 2608.21595, 2606.10302, 2603.23629, 2606.04057, 2605.05115, 2603.18353).

## 3. Verdict box

| Claim | Lane verdict | Deciding reference(s) |
|---|---|---|
| P1 low-rank causal PLAN variable (interchange/DAS) decides which algorithm Qwen3-8B writes; validated by generation | PARTLY OCCUPIED: the method is occupied (DAS; DAS steering validated by generation on a non-plan attribute); the object is open; flag A not fired | DAS/Boundless DAS {{2303.02536v4,2305.08809v3}}; MIB {{2504.13151v2}}; CDAS {{2602.05234v2}}; Invisible Lottery {{inh_c_30}}; Before Reasoning Begins {{or_vH3g2k4lPB}} |
| P2 plan subspace mediates which random pushes switch the algorithm | ADJACENT-ONLY (unchanged from 92c C2a; prediction of random-push effects is still open) | Before the First Token {{inh_c_64}}; AJR {{inh_c_65}}; DecodeShare {{2607.20469v1}}; output-sensitive component {{2608.22985v1}}; coordinate outside a subspace {{or_4gvIW4C0bw}} |
| P3 plan is discrete under interpolation | ADJACENT-ONLY | Park et al. {{2406.01506v3}}; Engels et al. {{2405.14860v3}}; Manifold Steering {{inh_c_44}}; prolepsis {{2604.15010v2}}; random-choice switch {{or_eZYeqPZlFr}} |
| P4 temperature leaves the plan untouched, state noise moves it, at matched KL | ADJACENT-ONLY | departure-matched decoding {{inh_c_66}}; Peeperkorn {{inh_c_25}}; Forking Paths {{2412.07961v1}}; future-behaviour forecasting {{or_5tVsS1vVLC}} |
| P5 resampling the plan as a diversity knob | PARTLY OCCUPIED (activation noise and latent sampling for diversity are occupied; resampling a fitted causal plan variable is open); flag D partly fired | STARS / Noise Steering / REI {{inh_c_15,inh_c_14,inh_c_16}}; LP-BD / PPLR / SVP {{or_IhQbFddkBp,or_CtluWEsiX7,or_oTt6XeccGk}}; Random Choice {{or_eZYeqPZlFr}} |
| N read and edit the plan in words with NLAs | OCCUPIED (method): replication in a new setting; flag C fired | NLA {{nla}}; LatentQA {{2412.08686v2}}; SelfIE {{2403.10949v2}}; cautions {{2607.20379v2,2609.18440v1,or_PKToLtvIZl}} |
| S the plan in Gemma Scope 2 SAE and transcoder features | PARTLY OCCUPIED (SAE-feature steering of reasoning strategies against prompt and activation baselines, validated by generation); algorithm choice in code is open | SAE-Steering {{2601.03595v2}}; AxBench and its rebuttal {{2501.17148v3,2605.31183v1}}; Do SAEs Identify Reasoning Features {{2601.05679v7}}; prolepsis {{2604.15010v2}} |
| E FP8 W8A8 activation rounding inflates the apparent effect of activation perturbations | ADJACENT-ONLY in the published and arXiv record; the general claim is PARTLY OCCUPIED by contemporaneous ICLR 2027 submissions (abstract-level); flag B partly fired | weight-only steering {{2609.06473v1}}; Stable Directions {{or_8iTqrW1sxY}}; Low-bit steering {{or_h57duZqLOr}}; FP8 W8A8 non-determinism {{or_9kskCmPMqd}} |

**Optional lines (no new search):**
- **ST and L.** Site comparisons for diversity injection remain as in 92c C1-site: PARTLY OCCUPIED {{inh_c_31,inh_c_14,inh_c_15}}.
- **G.** The base-model variety lines remain as in 92d (A2/G rows: transplant and goal published; inference-time movability open) {{inh_d_15,inh_d_11}}.

## 4. Flags (frozen definitions in evidence/protocol_iter6.json; verdicts in evidence/flags_iter6.json)

### Flag A (P1): NOT FIRED, narrowly

No source localizes which algorithm or solution strategy a code LLM will use as a low-rank causal variable by interchange or DAS, and then checks the claim by scoring the generated programs. Each half exists on its own:

- **DAS-based steering checked by generation, on a non-plan attribute.** CDAS: "While we adopt the core mechanism of DAS, distributed interchange intervention (DII) [...] we introduce a novel distribution matching objective tailored for the steering task by aligning intervened output distributions with counterfactual distributions" {{2602.05234v2}}. Its targets are refusal and a CoT backdoor.
- **Algorithm choice in code, moved only by prompt cues** {{inh_c_30}}.
- **Code attributes that are not the algorithm.**
  - Causal Syntax Circuits: "Code models write Python when the prompt does not say which language to use" {{2610.20683v1}}. It uses patching, circuits and steering, read out at the next token.
  - Concept Vectors: difference-in-means directions for coding habits {{or_sbVictHY9s}}.
  - Rahman et al.: language and library {{inh_c_45}}.
- **Algorithm identity found by DAS, but in toy networks**, validated against transfer learning rather than generation {{or_aHSbJo4RHN}}.

None of these does DAS/interchange plus generation on a strategy or a code attribute, so the PARTLY clause is not met. The interpretation note is logged: "only one half" means both halves apply to the same object.

**Would change it:** a paper, or the full text of an ICLR 2027 submission, that applies interchange/DAS to algorithm or strategy choice and scores the generated outputs.

### Flag B (E): PARTLY FIRED

- **Weight-only quantization only, in the published record.** "We systematically study activation steering under weight-only quantization (INT8 and NF4) across four open-weight 7–9B models and two behavioral targets" and "Activations remain in FP16/BF16 throughout the forward pass" {{2609.06473v1}}. This is exactly the PARTLY clause.
- **Two ICLR 2027 submissions on precision and steering effects.**
  - "Preserving standard model quality or direction-level representation similarity does not guarantee that the intervention effect is preserved" {{or_8iTqrW1sxY}} (desk-rejected).
  - "We study steering compatibility with the intervention layer, direction, and strength held fixed across full-precision and quantized models" {{or_h57duZqLOr}}.
  - Their abstracts do not say whether activations are quantized. The PDFs (openreview.net/pdf and api2 attachment) returned HTTP 403.
- **FP8 W8A8 appears only for non-determinism.** It is studied "using BF16, GPTQ, FP8 weight-and-activation quantization, and FP8 KV-cache quantization" for batch-context non-determinism, with no perturbations {{or_9kskCmPMqd}}.
- **Readouts change under quantization.**
  - Patching {{2604.19884v1,2609.01587v1}}.
  - SAE features {{2606.03002v2}}.
  - Probes under numeric formats {{2609.31796v1}}.

**Open part:** activation quantization combined with the effect size of *random* perturbations, against bf16 on the same directions.

**Would change it:** if the full text of either flag-B submission includes W8A8/FP8 activation quantization, B FIRES. It would be a contemporaneous submission about learned steering directions, not random pushes.

### Flag C (N): FIRED, as the planner's pre-check predicted

From the NLA paper {{nla}}:

- "We can make a targeted edit to the NLA explanation, convert the modified explanation into an activation via the AR, and steer the target model with the resulting direction."
- "We then steer with this direction at the newline token only, at the layer the NLA is trained on."
- "We note that steering is only successful roughly 50% of the time and the completions are not always clean."
- Its rewards case: "by editing an explanation and reconstructing both the original and edited versions with the AR, we obtain a steering vector from their difference."

Kin under the "similar verbaliser" clause:

- LatentQA: "The trained decoder also enables control by providing a differentiable loss to steer activations towards" {{2412.08686v2}}.
- SelfIE: "We propose Supervised Control, which allows editing open-ended concepts while only requiring gradient computation of individual layer" {{2403.10949v2}}.
- Dreaming Vectors (grey literature) {{lw_dreaming_vectors}}.

Patchscopes (92d source {{inh_d_88}}) is readout-only: no steer/control match in v4.

### Flag D (P5): PARTLY FIRED

- **Per-sample activation noise for diversity is a saturated lane** (92c sources {{inh_c_15,inh_c_14,inh_c_16,inh_c_52}}).
- **Latent-code sampling without a variable fitted inside a frozen LM:**
  - LP-BD: "before a block is decoded, a small conditional flow samples a low-dimensional plan given" a context {{or_IhQbFddkBp}}.
  - PPLR: "current latent models remain largely deterministic, capturing only a single reasoning trajectory rather than modeling a distribution over" several trajectories {{or_CtluWEsiX7}}.
  - SVP {{or_oTt6XeccGk}}.
- **Closest work with a fitted variable:** Random Choice in LMs. "one direction acts as a switch into the random-choice mode, whereas a separate direction shapes the resulting answer distribution", and "This decomposition enables a mechanism-guided intervention that improves sampling without task-specific gradient training" {{or_eZYeqPZlFr}}. Its abstract does not say the variable is resampled once per generation, and its object is single-item random choice.

## 5. Table 92e

Abbreviations:
- Status: V = VERIFIED (full text); VA = VERIFIED-ABSTRACT (OpenReview API record); VB = VERIFIED-BLOG; VR = VERIFIED-README.
- Contemporaneity: c = contemporaneous (ICLR 2027 submission); c4 = arXiv v1 after 2026-06-22; pub = published or older preprint.
- Quote ids (e.g. N-1) point to evidence/quotes_iter6.jsonl.

### P1: a low-rank causal PLAN variable, localized by interchange/DAS, decides which algorithm Qwen3-8B writes (validated by generation)

| Row | Neighbour (venue, version, v1, tag) | Verified quote(s) (id; locator; status) | Relation | Lane verdict | What this run adds | Reviewer baseline implied |
|---|---|---|---|---|---|---|
| 92e-P1-1 | DAS: Geiger, Wu, Potts, Icard, Goodman, CLeaR 2024 (PMLR 236), arXiv v4, v1 2023-03-05, pub {{2303.02536v4,pmlr_das_clear2024}}; Boundless DAS, Wu et al., NeurIPS 2023, v3 {{2305.08809v3}} | "existing causal abstraction methods have two major limitations: they require a brute-force search over alignments [...]" (P1-1; Abstract; V). "We apply Boundless DAS to the Alpaca model (7B parameters), which, off the shelf, solves a simple numerical reasoning problem." (P1-3; Abstract; V) | method the claim uses | PARTLY OCCUPIED (method) | object = algorithm choice in code; validation by tests on emitted programs; Sutter-style controls | DAS with a declared rotation rank, against Boundless DAS |
| 92e-P1-2 | MIB: Mueller et al., ICML 2025, v2, v1 2025-04-17, pub {{2504.13151v2}} | "For causal variable localization, we find that the supervised DAS method performs best, while SAE features are not better than neurons, i.e., non-featurized hidden vectors." (P1-4; Abstract; V) | control the claim must meet (method ordering) | n/a | n/a | report neuron and SAE-feature arms beside DAS (MIB ordering) |
| 92e-P1-3 | CDAS: Bao et al., ICLR 2026, v2, v1 2026-02-05, pub {{2602.05234v2}} | "While we adopt the core mechanism of DAS, distributed interchange intervention (DII) [...] we introduce a novel distribution matching objective tailored for the steering task by aligning intervened output distributions with counterfactual distributions." (P1-5; Sec. 1; V) | occupies the method+criterion pair (rubric 2.5) on a non-plan attribute (refusal, CoT backdoor) | PARTLY OCCUPIED | a plan object (algorithm choice), route-derived predictions, random/shuffled controls | a CDAS-style distribution-matching DAS arm |
| 92e-P1-4 | Programmable Semantic Interventions, ICLR 2027 submission, c {{or_DLKIln4eAT}} | "a low-rank activation subspace learned so that interchanging it moves the model's answer the way the program declares." (P1-6; abstract; VA) | adjacent (rubric 1.5) | — | generation-validated plan object | PSI-style declared-program alignment |
| 92e-P1-5 | Finding Algorithms in Neural Networks (DAS vs transfer), ICLR 2027 submission, c {{or_aHSbJo4RHN}} | "We find that, on toy arithmetic and vision tasks, the algorithms identified by DAS and TLA mostly agree" (P1-7; abstract; VA) | adjacent (1.5); supports declaring the map class (non-linear DAS needed in vision) | — | algorithm identity in a code LLM, checked by generation | linear vs non-linear map classes |
| 92e-P1-6 | Causal Syntax Circuits in CodeLMs, Kumar et al., NeurIPS 2026 workshop, v1 2026-10-14, c4 {{2610.20683v1}} | "Code models write Python when the prompt does not say which language to use. We ask a mechanistic question about that habit: is it produced by a small, findable group of components inside the model?" (P1-8; Abstract; V) | adjacent (1.5): a code attribute that is not the algorithm; next-token readout | — | algorithm (not language); low-rank DAS; generation | random-control significance test, as there |
| 92e-P1-7 | Steering LLM Coding Behaviors with Concept Vectors, ICLR 2027 submission, c {{or_sbVictHY9s}} | "Adding them after the first sampled token changes held-out outputs, but effects depend on model and layer, strong scaling harms validity and correctness, and axis specificity remains unresolved without matched-norm causal controls." (P1-9; abstract; VA) | adjacent (2.0) | — | algorithm-level object with matched-norm controls | a difference-in-means direction for the algorithm, with matched-norm random controls |
| 92e-P1-8 | Before Reasoning Begins (Qwen3-8B, final prompt position, SAE targets), ICLR 2027 submission, c {{or_vH3g2k4lPB}} | "This pipeline yields a compact set of 23 intervention targets in Qwen3-8B." (P1-10; abstract; VA). "We use this functionally aligned contrast to screen sparse autoencoder features at the final prompt position" (P1-11; abstract; VA) | adjacent (2.0): same model and site; object is reasoning, not algorithm | — | which algorithm (not whether reasoning happens); DAS rather than SAE suppression | layer-count-matched random null interventions |
| 92e-P1-9 | Committed Before Reasoning, Jo, v1 2026-07-17, c4 {{2607.16451v1}} | "Chat models sometimes commit to an answer and then produce reasoning that justifies the commitment rather than deriving it" (P1-12; Abstract; V) | supports (pre-generation commitment in Qwen3-8B) | — | — | — |
| 92e-P1-10 | Random Choice in LMs: linear choice state, ICLR 2027 submission, c {{or_eZYeqPZlFr}} | "one direction acts as a switch into the random-choice mode, whereas a separate direction shapes the resulting answer distribution." (P1-13; abstract; VA) | adjacent (2.0) | — | code-algorithm object | switch-vs-distribution decomposition |
| 92e-P1-11 | Detecting and Characterizing Planning in LMs, Nainani et al., v1 2025-08-25, anchor {{2508.18098v1}} | "We apply this pipeline to both base and instruction-tuned Gemma-2-2B models on the MBPP code generation benchmark and a poem generation task where Claude 3.5 Haiku was previously shown to plan." (P1-14; Abstract; V) | adjacent (1.5); contradicts in part (the same abstract reports that planning is not universal) | — | algorithm-level plan, not a future-token plan | a planning-vs-improvisation criterion |
| 92e-P1-12 | Algorithmic Core Extraction, Schiffman, v2, v1 2026-02-26, pub {{2602.22600v2}} | "extracting algorithmic cores, compact subspaces that are necessary and sufficient for a task and that recur across independently trained models." (P1-15; Abstract; V) | adjacent (1.0) | — | choice among algorithms, not a task core | — |
| 92e-P1-13 | Invisible Lottery (algorithm choice in code moved by cues), ICML 2026: see 92c source {{inh_c_30}} | see 92c (not re-verified) | adjacent (2.0): object occupied behaviourally | — | internal causal variable | prompt-cue baseline |
| 92e-P1-CTRL-1 | Sutter, Minder, Hofmann, Pimentel, NeurIPS 2025 Spotlight, v2, v1 2025-07-11, pub {{2507.08802v2}} | "on an experiment using randomly initialised language models, our alignment maps reach 100% interchange-intervention accuracy on the indirect object identification task." (CTRL-1; Abstract; V) | control the claim must meet | — | declared linear map class and rank; random-init or random-rotation control | fit the same map on a randomly initialized Qwen3-8B, and with shuffled labels |
| 92e-P1-CTRL-2 | Makelov, Lange, Geiger, Nanda, ICLR 2024, v2, pub {{2311.17030v2,iclr2024_makelov_poster}} | "this effect may be achieved by activating a dormant parallel pathway leveraging another subspace that is causally disconnected from model outputs." (CTRL-2; Abstract; V) | control the claim must meet | — | nullspace/row-space decomposition of the patch | check that the patched subspace is not causally disconnected |
| 92e-P1-CTRL-3 | Reply: Wu, Geiger, Huang, Arora, Icard, Potts, Goodman, v1 2024-01-23 {{2401.12631v1}} | "their method of discovering "illusions" can reject explanations they consider "non-illusory"." (CTRL-4; Abstract; V) | cite with CTRL-2 | — | — | — |
| 92e-P1-CTRL-4 | Divergent representations: Grant et al., v5 (2026-04-22), v1 2025-11-06 {{2511.04638v5}} | "minimizing divergence magnitude does not guarantee elimination of hidden pathways; it only reduces the risk surface." (CTRL-6; Sec. 5; V) | control | — | on-distribution check of patched states | report divergence of the intervened states |
| 92e-P1-CTRL-5 | Right Answer, Wrong Mechanism, v2, v1 2026-09-30, c4 {{2609.39243v2}} | "No method currently tells the two cases apart." (CTRL-7; Abstract; V) | control (do not rely on distance checks alone) | — | — | planted-pathway or clamp test |
| 92e-P1-CTRL-6 | Curse of Multiple Mediators {{2606.27510v1}}; Many Circuits, One Mechanism (TMLR 2026) {{2606.06267v2}}; identification-assumptions position {{2605.08012v1}} | "we find that the NIE does not solely capture the causal effect through the specific component." (CTRL-8; V). "The discovered circuits appear specialized by frequency when compared structurally, but functional and representational analyses show no reliable evidence of corresponding differences." (CTRL-9; V) | controls | — | — | report interaction effects, cross-condition transfer and identification assumptions |

### P2: the plan subspace mediates which random pushes switch the algorithm

| Row | Neighbour | Verified quote(s) | Relation | Lane verdict | What this run adds | Reviewer baseline |
|---|---|---|---|---|---|---|
| 92e-P2-1 | Before the First Token (causal response-length subspace; parallel/orthogonal decomposition of interventions), ICLR 2027 submission: see 92c source {{inh_c_64}} | see 92c source 64 (not re-verified) | adjacent (nearest) | ADJACENT-ONLY | prediction of *random*-push effects on *algorithm* choice from projection onto the plan subspace | parallel/orthogonal decomposition of each push |
| 92e-P2-2 | AJR {{inh_c_65}}; ASTEER {{inh_c_21}}; decodability is not actionability {{inh_c_43}} | see 92c (not re-verified) | adjacent | — | — | Jacobian-readout predictor of push effects |
| 92e-P2-3 | DecodeShare, v1 2026-05-21, pub {{2607.20469v1}} | "disturbing the discovered shared subspace degrades decision performance far more than disturbing either a prefill-derived or random subspace under the same intervention budget." (P2-2; Abstract; V) | adjacent (1.5) | — | random pushes classified by plan-subspace energy | matched-budget random-subspace control |
| 92e-P2-4 | What Does Activation Steering Control?, v1 2026-08-24, c4 {{2608.22985v1}} | "A low-rank output-sensitive component containing 15.4% of the direction's squared norm retains 96.3% of this effect." (P2-7; Abstract; V) | supports a projection account (1.0) | — | — | report the share of each push's norm inside the plan subspace |
| 92e-P2-5 | Jailbreak success coordinate outside the refusal subspace, ICLR 2027 submission, c {{or_4gvIW4C0bw}} | "whether success is decodable before generation from a coordinate outside an evaluated refusal subspace, whether intervention on that coordinate moves the behavior" (P2-3; abstract; VA) | contradicts in part: the outcome-deciding coordinate can lie outside an evaluated subspace | — | — | test the orthogonal complement as well |
| 92e-P2-6 | Before Reasoning Begins (targeted vs random-null) {{or_vH3g2k4lPB}}; Latent Planning Emerges with Scale, ICLR 2026 {{2604.12493v1}} | "same-size, layer-count-matched random null interventions reduce accuracy by only" (P2-5; VA). "even the less-successful Qwen-3 4B-8B have nascent planning mechanisms." (P2-4; Abstract; V) | adjacent / supports | — | — | random-null arm |
| 92e-P2-8 | On the Non-Identifiability of Steering Vectors, v4, v1 2026-02-06, pub (found by a supplementary search) {{2602.06801v4}} | "We show that, under white-box single-layer access, steering vectors are fundamentally non-identifiable due to large equivalence classes of behaviorally indistinguishable interventions." (P2-8; Abstract; V) | supports a subspace-level (not direction-level) account (1.0) | — | — | report plan claims at subspace level; orthogonal-perturbation control |
| 92e-P2-7 | Steering off Course, v1 2025-04-06, anchor {{2504.04635v1}}; Tele-Lens (ICML 2026) {{2602.02103v2}} | "Our analysis demonstrate fundamental flaws in the assumptions underlying these methods, challenging their reliability as scalable steering solutions" (P2-1; Abstract; V) | caution | — | — | per-sample effect distributions |

### P3: the plan is discrete under interpolation

| Row | Neighbour | Verified quote(s) | Relation | Lane verdict | What this run adds | Reviewer baseline |
|---|---|---|---|---|---|---|
| 92e-P3-1 | Park, Choe, Jiang, Veitch, ICLR 2025 oral, v3, anchor {{2406.01506v3}} | "This allows us to immediately formalize the representation of categorical concepts as polytopes in the representation space." (P3-1; Abstract; V) | supports (categorical geometry) | ADJACENT-ONLY | an interpolation sweep between plan centroids, with the emitted algorithm labelled at each step | polytope/simplex geometry of the plan centroids |
| 92e-P3-2 | Engels et al., ICLR 2025, v3 (retitled "...One-Dimensionally Linear"), anchor {{2405.14860v3}} | "we explore whether some language model representations may be inherently multi-dimensional." (P3-2; Abstract; V) | adjacent (2.0): interventions along circular features | — | discreteness vs continuity of a code plan | a test for irreducible multi-dimensional features |
| 92e-P3-3 | Manifold Steering (ICML 2026 MI-workshop spotlight): see 92c source {{inh_c_44}} | see 92c (not re-verified) | adjacent | — | — | geodesic vs linear paths |
| 92e-P3-4 | Prolepsis, Jacopin, v2, v1 2026-04-16 {{2604.15010v2}}; Random Choice switch {{or_eZYeqPZlFr}}; manifold vs linear steering (ICLR 2027 submission) {{or_MN9X374VhG}} | "We introduce prolepsis: a transformer commits early, task-specific attention heads sustain the commitment, and no layer corrects it." (P3-3; V). "show that both a linear direction and a low-dimensional manifold structure align with it." (P3-4; VA) | adjacent | — | — | linear vs manifold interpolation |

### P4: temperature leaves the plan untouched while state noise moves it, at matched KL

| Row | Neighbour | Verified quote(s) | Relation | Lane verdict | What this run adds | Reviewer baseline |
|---|---|---|---|---|---|---|
| 92e-P4-1 | departure-matched decoding (ICLR 2027 submission, "Rethinking Activation Steering for Mathematical Reasoning"): 92c source {{inh_c_66}}; Peeperkorn {{inh_c_25}}; AdapT {{inh_c_8}}; Gumbel counterfactuals {{inh_c_33}}; Beneath the Diff {{inh_c_29}} | see 92c (not re-verified) | adjacent; departure-matched decoding is the reviewer baseline | ADJACENT-ONLY | plan-level (algorithm) readout of temperature vs state noise at matched KL | decoding matched to the perturbation's departure from greedy |
| 92e-P4-2 | Forking Paths, Bigelow et al., v1 2024-12-10, anchor {{2412.07961v1}} | "We hypothesize that there exist key forking tokens, such that re-sampling the system at those specific tokens, but not others, leads to very different outcomes." (P4-1; Abstract; V) | adjacent (2.0) | — | — | forking-token resampling baseline |
| 92e-P4-3 | HELIX (4-bit Granite; temperature plus steering), v1 2026-02-06 {{2602.17691v1}}; Predicting Future Behaviors, ICLR 2027 submission {{or_5tVsS1vVLC}} | "Quantized language models face a fundamental dilemma: low sampling temperatures yield repetitive, mode-collapsed outputs, while high temperatures [...] cause trajectory divergence and semantic incoherence." (P4-2; V). "We apply a forking-paths-style analysis to behavioral evaluations and find that as generation progresses, LRMs define evolving distributions over behavioral outcomes." (P4-3; VA) | adjacent | — | — | — |

### P5: resampling the plan as a diversity knob (flag D)

| Row | Neighbour | Verified quote(s) | Relation | Lane verdict | What this run adds | Reviewer baseline |
|---|---|---|---|---|---|---|
| 92e-P5-1 | STARS (ICLR 2026), Noise Steering, REI, NC-GRPO, 2606.10302, Diversity Without Discovery: 92c sources {{inh_c_15,inh_c_14,inh_c_16,inh_c_52,inh_c_31,inh_c_63}} | see 92c (not re-verified) | occupies the method family (activation noise for diversity) | PARTLY OCCUPIED | resampling a *fitted, causally localized* plan variable | matched-dose activation noise; text-level plan samplers (IFG, PlanSearch) {{inh_c_26,inh_c_27}} |
| 92e-P5-2 | Random Choice in LMs, ICLR 2027 submission, c {{or_eZYeqPZlFr}} | "This decomposition enables a mechanism-guided intervention that improves sampling without task-specific gradient training." (P5-1; abstract; VA) | adjacent (2.0); closest to flag D | — | per-generation resampling for algorithm diversity | distribution-direction intervention |
| 92e-P5-3 | LP-BD {{or_IhQbFddkBp}}; PPLR {{or_CtluWEsiX7}}; SVP {{or_oTt6XeccGk}} (ICLR 2027 submissions, c) | "before a block is decoded, a small conditional flow samples a low-dimensional plan given" (P5-2; VA). "which diversifies latent trajectories by randomly rescaling coefficients in the fixed SVD basis of a weight matrix." (P5-4; VA) | adjacent (flag D partly) | — | a frozen LM; the variable is fitted, not trained | — |
| 92e-P5-4 | Latent Plan Transformer, v4, anchor (venue not stated in the arXiv record) {{2402.04647v4}} | "We introduce the Latent Plan Transformer (LPT), a novel model that leverages a latent variable to connect a Transformer-based trajectory generator and the final return." (P5-5; Abstract; V) | adjacent | — | — | — |

### N: reading and editing the plan in words with NLAs (flag C)

| Row | Neighbour | Verified quote(s) | Relation | Lane verdict | What this run adds | Reviewer baseline |
|---|---|---|---|---|---|---|
| 92e-N-1 | Fraser-Taliente, Kantamneni, Ong et al., "Natural Language Autoencoders Produce Unsupervised Explanations of LLM Activations", Transformer Circuits, published May 7, 2026, pub {{nla}} | "We can make a targeted edit to the NLA explanation, convert the modified explanation into an activation via the AR, and steer the target model with the resulting direction." (N-1; Planning in Poetry; V). "We note that steering is only successful roughly 50% of the time and the completions are not always clean." (N-3; V) | OCCUPIES the method (rubric 2.5) | OCCUPIED (method) | replication in a new setting: algorithm choice in code, Qwen2.5-7B-Instruct L20, text-only judges, an unrelated-word edit, a matched-norm random displacement | the paper's own newline-only steering protocol and success rate |
| 92e-N-2 | same paper, Reasoning about Rewards {{nla}} | "by editing an explanation and reconstructing both the original and edited versions with the AR, we obtain a steering vector from their difference." (N-4; V) | occupies | — | — | AR-difference steering vector, norm-matched |
| 92e-N-3 | same paper, Method and Limitations {{nla}} | "NLA explanations can contain claims about the target model's input context that are verifiably false." (N-5; V). "with the NLAs evaluated in this paper reaching 0.6-0.8 FVE" (N-6; V) | control the claim must meet (confabulation) | — | — | confabulation audit of plan claims |
| 92e-N-4 | Released checkpoints: kitft README {{nla_readme_raw}}; HF card {{hf_nla_qwen25_7b_L20_av}}; nla_meta.yaml {{hf_nla_qwen25_7b_L20_av_meta}}; TransformerLens issue #1884 {{tl_issue_1884}} | "Qwen2.5-7B-Instruct \| 20 / 28 \| 3584" (N-9; VR). "Each checkpoint ships an `nla_meta.yaml` sidecar [...] load those, never hardcode them." (N-11; VR). "In-distribution fve_nrm: 0.752" (N-13; VR) | design facts | — | — | load nla_meta.yaml injection settings |
| 92e-N-5 | LatentQA, Pan, Chen, Steinhardt, ICLR 2026, v2 {{2412.08686v2}}; SelfIE, ICML 2024, PMLR 235 {{2403.10949v2,pmlr_selfie_chen24ao}} | "The trained decoder also enables control by providing a differentiable loss to steer activations towards" (N-15; V). "We propose Supervised Control, which allows editing open-ended concepts while only requiring gradient computation of individual layer." (N-17; V) | occupies the "similar verbaliser" clause of flag C (rubric 2.0 each) | — | — | decoder-loss steering arm |
| 92e-N-6 | Activation Oracles, v2 {{2512.15674v2}}; Dreaming Vectors (LessWrong) {{lw_dreaming_vectors}} | "we study Activation Oracles (AOs): models trained to answer arbitrary natural-language questions about LLM activations." (N-19; V) | readout kin / steering kin (grey literature) | — | — | — |
| 92e-N-7 | Sood, Substack, 2026-08-18, c4 {{jaisood_nla}}; Auditing the Auditor, ICLR 2027 submission, c {{or_PKToLtvIZl}} | "We audit two released NLA checkpoints and find that the readout reports what pressure was applied and what the model answered, but not whether the pressure changed that answer." (N-21; VB). "under preregistered controls: a wrong-activation (shuffled) control, a visible-text baseline, a blinded judge, and supervised readability probes." (N-22; VA) | control set the readout must meet | — | — | shuffled-activation control; visible-text baseline; blinded judge |
| 92e-N-8 | Train the Model, Not the Reader, Dingeto, v2, v1 2026-07-22, c4 {{2607.20379v2}} | "On a released Qwen-2.5-7B verbalizer, explanations reconstruct well above chance while as few as [...] of their specific claims are ones the reconstruction depends on. The score therefore tracks the input's gist, not its specific" (N-24; Abstract; V) | contradicts in part: an edited claim may not move the AR output | — | measure the AR displacement caused by the edit before steering | claim-flip reconstruction test |
| 92e-N-9 | Colombian identity with NLA, v1 2026-07-23, c4 {{2607.21774v1}} | "We use Natural Language Autoencoders (NLA) to verbalize residual-stream activations from layer 20 across four positional quartiles per prompt." (N-25; V) | readout replication on the same checkpoint | — | — | — |
| 92e-N-10 | Community Qwen3-8B NLAs: nanoNLA {{hf_ceselder_nanonla,gh_nanonla_readme}}; EasyNLA {{gh_easynla_readme}} | "This repo hosts the AV for Qwen3-8B @ layer 24." (N-26; VR). "On Qwen3-8B (layer 24) the default config reaches ~70% held-out FVE in ~3–4 hours on 4×H200." (N-28; VR) | corrects iteration 5's "NLA unavailable for Qwen3-8B" | — | — | an optional Qwen3-8B arm (unofficial; faithfulness disclaimer) |
| 92e-N-11 | Planning or Improvisation?, Jacopin, v1 2026-09-16, c4 {{2609.18440v1}} | "C2 and C3 are not recovered by any probe: a census of every active feature finds no rhyme-anticipating enrichment at the newline" (N-29; Abstract; V) | contradicts in part (no newline-resident plan in small open models) | — | — | site sweep (newline vs final prompt token) |
| 92e-N-12 | Measuring Activation Control {{2608.21664v1}}; Understanding Confabulation {{2609.33702v1}} | "this level of control can evade activation-based monitoring methods (including linear probes, natural language autoencoders, activation oracles, and the Jacobian lens), albeit imperfectly." (N-30; V) | context | — | — | — |

### S: the plan in Gemma Scope 2 SAE and transcoder features

| Row | Neighbour | Verified quote(s) | Relation | Lane verdict | What this run adds | Reviewer baseline |
|---|---|---|---|---|---|---|
| 92e-S-1 | Gemma Scope 2: announcement 22 Dec 2025 {{lw_gemma_scope_2}}; technical report {{gemma_scope_2_tech_report}}; HF card {{hf_gemma_scope_2_4b_it}} | "every SAE trained on a PT model has a corresponding version finetuned for IT models" (S-1; VB). "we do not train IT SAEs from scratch: we initial [...] from the corresponding PT SAEs and finetune on the rollout-derived datasets." (S-3; V) | design facts | — | — | report the IT-vs-PT dictionary used |
| 92e-S-2 | circuit-tracer README {{circuit_tracer_readme_raw}}; Qwen-3 transcoders (Hanna et al.) {{hf_mwhanna_qwen3_8b_transcoders,2604.12493v1}} | "Gemma-3 PLTs (originally from GemmaScope-2) can be found here for models of size 270M, 1B, 4B, 12B, and 27B, PT and IT. These require using the `nnsight` backend." (S-5; VR). "Qwen-3 PLTs: for Qwen-3 0.6B, 1.7B, 4B, 8B, and 14B" (S-6; VR) | design fact: Qwen3-8B transcoders exist, so a reviewer may ask why S uses Gemma | — | — | run S on the Qwen3-8B PLTs, or justify Gemma |
| 92e-S-3 | AxBench, v3, v1 2025-01-28 {{2501.17148v3}}; rebuttal, v1 2026-05-29 {{2605.31183v1}} | "For steering, we find that prompting outperforms all existing methods, followed by finetuning." (S-10; V). "We find that Sparse Autoencoders can, in fact, perform close to on par with the reference LoRA performance on the AxBench benchmark, when features are selected and labelled with our supervised pipeline." (S-12; V) | prior the claim must meet | — | — | difference-in-means and prompting arms |
| 92e-S-4 | SAE-Steering, Fang et al., ACL 2026 Main, v2 {{2601.03595v2}}; Galichin et al. {{2503.18878v2}} | "To identify the few strategy-specific features from the vast pool of SAE features, we propose SAE-Steering, an efficient two-stage feature identification pipeline." (S-13; V). "We compare SAE-Steering with three representative control methods [...] Think Intervention (Wu et al., 2025), which inserts human-crafted instructions into the middle of the reasoning process" (S-13b; Sec. 4.1; V) | OCCUPIES the method on a non-code strategy (rubric 2.5) | PARTLY OCCUPIED | algorithm choice in code; Gemma Scope 2; transcoder attribution | SAE-Steering-style logit-recall feature selection |
| 92e-S-5 | Do SAEs Identify Reasoning Features? (Gemma Scope 2), ICML 2026, v7 {{2601.05679v7}} | "use SAEs from the GemmaScope-2 release (McDougall et al., 2025), each with 16,384 features trained on residual stream activations." (S-15; V). "A small steering study yields minimal changes on the evaluated benchmarks." (S-16; V) | contradicts in part | — | — | token-injection falsification of candidate features |
| 92e-S-6 | Prolepsis {{2604.15010v2}}; Latent Planning Emerges with Scale {{2604.12493v1}} | "Planning is invisible to six residual-stream methods; among those tested, only CLT-based steering succeeds." (S-17; V) | adjacent; counter-evidence to the AxBench prior for plans | — | — | CLT/PLT arm against residual difference-in-means |
| 92e-S-7 | SAE Interventions are Unreliable {{2606.18322v1}}; variable roles in code LMs (ICLR 2027 submission) {{or_2AiBLDA67W}}; attribution-graph caveat {{tc_biology}} | "the clamp may block one visible route to a behavior without eliminating the behavior itself." (S-18; V). "residual probes outperform individual SAE features and tested lexical baselines" (S-19; VA). "we've found that our attribution graphs provide us with satisfying insight for about a quarter of the prompts we've tried" (S-20; V) | cautions | — | — | probe baseline; post-intervention recovery check |

### E: FP8 W8A8 activation rounding inflates the apparent effect of activation perturbations (flag B)

| Row | Neighbour | Verified quote(s) | Relation | Lane verdict | What this run adds | Reviewer baseline |
|---|---|---|---|---|---|---|
| 92e-E-1 | Steering Under Compression, Bhandari and Wade, v1 2026-09-06, c4 {{2609.06473v1}} | "Activations remain in FP16/BF16 throughout the forward pass." (E-2; Sec. 3; V). "demonstrating that compression can dominate the steering intervention." (E-4; V) | adjacent (1.5); flag B partly | ADJACENT-ONLY (published) | activation quantization; random perturbations; matched bf16 control | iso-effect comparison at matched behavioural effect |
| 92e-E-2 | Stable Directions, Different Effects, ICLR 2027, desk rejected, c {{or_8iTqrW1sxY}} | "Preserving standard model quality or direction-level representation similarity does not guarantee that the intervention effect is preserved." (E-5; VA). "Intervention effects can change even when directions remain strongly aligned" (E-6; VA) | partly occupies the general claim (contemporaneous) | PARTLY OCCUPIED (contemporaneous) | random pushes; FP8 W8A8 named; noise-floor account | a first-order local-sensitivity predictor |
| 92e-E-3 | Activation Steering under Low-Bit Quantization, ICLR 2027 submission, c {{or_h57duZqLOr}} | "We study steering compatibility with the intervention layer, direction, and strength held fixed across full-precision and quantized models." (E-7; VA) | adjacent (1.0) | — | — | hold layer, direction and strength fixed |
| 92e-E-4 | Quantization Modulates Batch-Context Non-Determinism, ICLR 2027 submission, c {{or_9kskCmPMqd}} | "using BF16, GPTQ, FP8 weight-and-activation quantization, and FP8 KV-cache quantization." (E-9; VA) | mechanism neighbour (noise floor) | — | perturbation effect sizes against the FP8 noise floor | same-batch-context repeat runs |
| 92e-E-5 | PRISM, v1 2026-10-14, c4 {{2610.20808v1}} | "we introduce PRISM, a framework for evaluating the transfer of activation interventions across precision, languages, and scales." (E-10; V) | adjacent (NF4) | — | — | — |
| 92e-E-6 | Readouts under quantization: Findings ACL 2026 {{2604.19884v1}}; {{2609.01587v1}}; {{2606.03002v2}}; AACL 2025 {{2508.16785v3}}; TrustNLP 2026 {{2505.13963v3}} | "These results show that behavioral metrics alone are insufficient evidence that full-precision interpretability findings transfer to quantized models, motivating feature-level audits of compression." (E-13; V) | flag B partly (readouts, not perturbation effect sizes) | — | — | — |
| 92e-E-7 | Precision-induced divergence: TMLR 2026 {{2609.26621v1}}; {{2506.09501v2,arxiv_abs_2506.09501v1}}; {{2604.19790v1}}; {{2609.31796v1}} | "the same model, prompt, and decoding algorithm produce different outputs in BF16 versus FP16 on identical hardware." (E-17; V). "under bfloat16 precision with greedy decoding, a reasoning model like DeepSeek-R1-Distill-Qwen-7B can exhibit up to 9% variation in accuracy and 9,000 tokens difference in response length due to differences in GPU count, type, and evaluation batch size." (E-18; V) | supports the mechanism (rounding flips trajectories) | — | — | a zero-norm (unperturbed) re-run under the same engine |
| 92e-E-8 | Mechanism sources: LLM.int8() {{2208.07339v2}}; SmoothQuant {{2211.10438v7}}; massive activations {{2402.17762v2}}; FP8 formats {{2209.05433v2}}; llm-compressor FP8_DYNAMIC {{llmcompressor_fp8_readme}} | "SmoothQuant smooths the activation outliers by offline migrating the quantization difficulty from activations to weights with a mathematically equivalent transformation." (E-21; V). "Static, per-channel quantization on the weights [...] Dynamic, per-token quantization on the activations" (E-24; VR) | mechanism background | — | — | per-token-scale ablation |

## 6. Permitted wording (dated 2026-10-22; evidence: evidence/flags_iter6.json, evidence/quotes_iter6.jsonl)

- **P1.**
  - Permitted: "To our knowledge (search dated 2026-10-22), the first interchange/DAS localization of *which algorithm* a code LLM will write that is validated by scoring the generated programs, with Sutter-style map-class, random-initialization and shuffled-label controls."
  - Forbidden: "first causal localization of a plan", "new method", and "first DAS-based steering" (CDAS {{2602.05234v2}}).
  - Cite DAS {{2303.02536v4}}, MIB {{2504.13151v2}}, CDAS {{2602.05234v2}}, Sutter {{2507.08802v2}}, Makelov with the reply {{2311.17030v2,2401.12631v1}}, divergent representations {{2511.04638v5}}, and the contemporaneous Before Reasoning Begins {{or_vH3g2k4lPB}}.
- **P2.**
  - Permitted: "we predict which random pushes switch the algorithm from their projection onto the plan subspace".
  - Forbidden: "first causal planning subspace" (Before the First Token {{inh_c_64}}).
  - Frame the parallel/orthogonal decomposition as following {{inh_c_64}}.
- **P3.**
  - Permitted: "the plan behaves discretely under interpolation in our setting".
  - Forbidden: "categorical concepts are discrete" as a new finding ({{2406.01506v3}}).
- **P4.**
  - Permitted: "at matched KL, temperature did not move the plan while state noise did".
  - The departure-matched decoding baseline {{inh_c_66}} must be run or named.
  - Forbidden: "temperature is not the creativity knob" as a new claim ({{inh_c_25}}).
- **P5.**
  - Permitted: "resampling a fitted, causally localized plan variable"; activation noise for diversity is prior art {{inh_c_15,inh_c_14,inh_c_16}}.
  - Forbidden: "first latent diversity knob" and "new diversity method".
- **N.**
  - Permitted: "we replicate the NLA edit-and-steer protocol {{nla}} on algorithm choice in code, with Qwen2.5-7B-Instruct and new controls".
  - Forbidden: "first", "new method", "we introduce editing explanations to steer".
- **S.**
  - Permitted: "Gemma Scope 2 SAE/transcoder features for an algorithm-choice plan in code, compared against difference-in-means and prompting".
  - Forbidden: "first SAE steering of strategies" ({{2601.03595v2}}).
  - State why Gemma Scope 2 is used when Qwen-3 PLTs exist {{circuit_tracer_readme_raw}}.
- **E.**
  - Permitted: "we find that activation-quantized (FP8 W8A8, dynamic per-token) inference inflates the apparent effect of random activation perturbations relative to bf16".
  - Cite the weight-only {{2609.06473v1}} and contemporaneous {{or_8iTqrW1sxY,or_h57duZqLOr,or_9kskCmPMqd}} work.
  - Forbidden: "first to show quantization changes steering effects".

## 7. Reviewer baselines (implied by the neighbours)

1. **P1.**
   - DAS with a declared linear rotation and rank, fitted also on a randomly initialized model and with shuffled labels {{2507.08802v2}}.
   - Neuron and SAE-feature arms {{2504.13151v2}}.
   - A CDAS-style distribution-matching arm {{2602.05234v2}}.
   - A difference-in-means direction with matched-norm random controls {{or_sbVictHY9s}}.
   - A prompt-cue baseline {{inh_c_30}}.
2. **P2.**
   - Parallel/orthogonal decomposition {{inh_c_64}}.
   - A matched-budget random subspace {{2607.20469v1}}.
   - A test of the orthogonal complement {{or_4gvIW4C0bw}}.
3. **N.**
   - Shuffled-activation and visible-text controls, plus a blinded judge {{or_PKToLtvIZl}}.
   - A claim-flip reconstruction test {{2607.20379v2}}.
   - The paper's newline-only protocol {{nla}}.
4. **S.**
   - Difference-in-means and prompting {{2501.17148v3}}.
   - A supervised SAE pipeline {{2605.31183v1}}.
   - SAE-Steering feature selection {{2601.03595v2}}.
   - CLT/PLT steering {{2604.15010v2}}.
5. **E.**
   - A bf16 re-run of the same directions.
   - A zero-norm FP8 re-run (noise floor) {{or_9kskCmPMqd,2609.26621v1}}.
   - A weight-only (W8A16) arm {{2609.06473v1}}.
   - A per-token-scale ablation {{llmcompressor_fp8_readme}}.
6. **P4/P5.**
   - Departure-matched decoding {{inh_c_66}}.
   - IFG and PlanSearch {{inh_c_26,inh_c_27}}.

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
   Three supplementary general-web searches outside the frozen strings (round SUPP in the search log) looked for full-text versions of the abstract-only flag-B and flag-D neighbours. None was found. They surfaced one more P2-adjacent paper {{2602.06801v4}}.
8. **No full-text checks for the method details in ICLR 2027 abstracts.** For example, whether "precision changes" includes activation quantization.

## 9. Corrections (evidence/corrections_iter6.jsonl)

- **NLA.**
  - Citation and date: "Fraser-Taliente, Kantamneni, Ong et al.", published May 7, 2026 {{nla}}.
  - The paper already edits and steers a plan, so N is a replication.
  - 4 base models × (AV, AR) = 8 checkpoints {{nla_readme_raw}}.
  - Qwen3-8B has no *official* NLA checkpoint, but community reimplementations exist at layer 24 {{hf_ceselder_nanonla,gh_easynla_readme}}. friendli.ai/models/ceselder/nanoNLA is a hosting listing of that AV.
- **Gemma Scope 2.** Announced 22 Dec 2025; IT SAEs are initialized from the PT SAEs and finetuned {{lw_gemma_scope_2,gemma_scope_2_tech_report}}.
- **circuit-tracer.**
  - Gemma-3 PLTs come from GemmaScope-2 and need the nnsight backend.
  - Qwen-3 PLTs, including 8B, are by Hanna et al. The card names no checkpoint; the ICLR 2026 paper that uses them calls its Qwen-3 models instruction-tuned {{circuit_tracer_readme_raw,hf_mwhanna_qwen3_8b_transcoders,2604.12493v1}}.
- **Sutter et al.** NeurIPS 2025 Spotlight. The phrase "any neural network can be mapped to any algorithm" does not occur in v2; use the 100% IIA sentence {{2507.08802v2}}.
- **Makelov et al.** ICLR 2024; the arXiv comment names a NeurIPS 2023 workshop {{iclr2024_makelov_poster}}.
- **SelfIE.** ICML 2024, PMLR 235:7373-7388 {{pmlr_selfie_chen24ao}}.
- **DAS.** CLeaR 2024, PMLR 236 {{pmlr_das_clear2024}}.
- **Engels et al.** The current title is "Not All Language Model Features Are One-Dimensionally Linear" {{2405.14860v3}}.
- **2506.09501.**
  - v1 is titled "Give Me FP32 or Give Me Death? Challenges and Solutions for Reproducible Reasoning"; v2 is retitled.
  - "up to 9% variation in accuracy" is verified {{arxiv_abs_2506.09501v1,2506.09501v2}}.
- **2609.15504.** The current title is "Evaluating Losslessness in Speculative Decoding Under Finite-Precision Inference" (no row).
- **Latent Plan Transformer.** Venue not stated in the arXiv record (v4) {{2402.04647v4}}.
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
  - Planning may be absent or improvised in small open models {{2508.18098v1,2609.18440v1}}.
  - NLA reconstructions track the gist rather than specific claims {{2607.20379v2}}.
  - SAE reasoning features may be token correlates {{2601.05679v7}}.
  - Steering reliability is questioned {{2504.04635v1,2606.18322v1}}.

## 11. Follow-up questions

1. **Flag B.** Do the ICLR 2027 submissions "Stable Directions, Different Effects" and "Activation Steering under Low-Bit Quantization" quantize activations (W8A8/FP8) or only weights? Their full texts decide whether flag B fires. Re-read them once the OpenReview PDFs are reachable.
2. **N's causal arm.** On the released Qwen2.5-7B-Instruct L20 NLA, how far does the AR reconstruction move when only the algorithm name in an explanation is edited? The claim-dependence result {{2607.20379v2}} predicts a small move. Measure this before running the edit-and-steer arm.
3. **Flag A and P1.** Would interchange/DAS on the Qwen3-8B final prompt position find a low-rank variable for algorithm choice? Where does it sit relative to the 23 SAE targets of the contemporaneous Before Reasoning Begins submission {{or_vH3g2k4lPB}} and to the Qwen-3 PLTs {{circuit_tracer_readme_raw}}?

