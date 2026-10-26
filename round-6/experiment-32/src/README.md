# Reading the planned algorithm in words

**Model:** Qwen/Qwen2.5-7B-Instruct, bf16. **Instrument:** the released natural-language autoencoder (NLA) pair
`kitft/nla-qwen2.5-7b-L20-av` / `-ar`, which reads layer 20.

When the model writes code for an algorithm-choice task, does its residual stream already "say", before the first
code token, which algorithm it will implement? Can a verbal edit of that state steer the choice?

This artifact is iteration 6, experiment 32, of an AI-Inventor run on *how creativity (algorithmic choice) shows up
inside an LLM and whether it can be influenced*. It has three stages. All three are pre-registered in a sha256 chain
(`commitments.log`, `predictions/commit0-3`). The steps that were not pre-registered are marked EXPLORATORY.

1. **Behaviour.** 8 tasks (T1 grid path, T2 weighted shortest path, T03 k-th smallest, T05 two-sum, T06 find
   duplicate, T10 connected components, T04 substring search, R6 first/last position). Conditions:
   - a neutral "twin" prompt (N=50);
   - a "do not use \<the model's default\>" ban (N=50, CRN-paired with the twin);
   - an "Implement Y" prompt for every catalogue algorithm (N=20 each);
   - the T2 semantic seed (N=50).

   Programs are labelled by hidden tests plus frozen runtime-trace and AST labellers; no LLM decides a label except
   on labeller disagreement.
2. **NLA readout.** The AV verbalises layer-20 states at the end of the prompt (SPEC-3..SPEC-1, READ) and at
   generated tokens g1-g16 (6,180 explanations). Two blind judges from different families (and a third on
   disagreement) map each explanation to a catalogue algorithm. The NLA is compared with:
   - the same judges reading the visible text (text-only NAME);
   - an outside-reader forecast (PREDICT);
   - swapped twin explanations;
   - explanations of matched-norm random perturbations;
   - a forced-prompt positive control.
3. **Causal edit.** The default's name in a twin explanation is replaced by (or appended as) Y. The difference of the
   two AR reconstructions is patched into the layer-20 states (×1/×2/×4, N=30 CRN pairs per cell). It is judged
   against the unedited round trip, an unrelated-word edit, a matched-norm random push and a matched-norm
   difference-in-means push. A generated-token site and a reverse variant are also run.

## Bottom line

- **Behaviour: Qwen2.5-7B mostly ignores "do not use X" bans.** Only T05 yields a substitute: the ban of the hash map
  gives a brute-force double loop in 32 of 46 correct programs.
  - On T10, banning DFS *increases* DFS: 29 → 43 correct programs. 15 slots flip union-find → DFS under the ban
    (paired CRN slots).
  - T04 and R6 keep their default in 94-96% of attempts.
  - T03 has no default (quickselect 0.40, size-k heap 0.34; correct-only Hill-1 3.8). It failed the style re-gate
    and is excluded.
  - The "\<X\> is not allowed here" template (W4) fails everywhere: all 70 W4 ban programs, across the 7 defaulted
    tasks, attempt the banned default.
- **Instrument fidelity is PARTIAL on these code prompts.**
  - The pipeline reproduces the checkpoint on its own distribution: reference-set FVE 0.695 vs the released 0.752.
    Ultra-FineWeb gives 0.78 and general chat 0.79.
  - The extraction convention is hidden_states[21] (= output of block 20), as the training code says. It beats the
    README snippet's hidden_states[20] by 0.115 FVE.
  - On the task states FVE falls to 0.51 (READ 0.65, SPEC 0.50, g2 0.28). Code and algorithm text is out of
    distribution for this NLA: LeetCode prompts 0.45, HumanEval+ 0.39, CLRS traces 0.33.
- **The NLA never verbalises the planned algorithm before the code starts.** Every pre-registered prefill readout is
  exactly 0:
  - N1 (ban states naming Y\*): 0/16.
  - N2 (twin states naming the default): 0/112. The text-only reader also scores 0, so the effect is 0.00.
  - N8b (ban-failure states naming the default the model still writes): 0/96.
  - N3, the positive control, also fails: on forced "Implement Y" prompts the explanations call Y planned in 0 of
    7 tasks, while the text-only reader gets 1.0. They mention the named algorithm in 0.7% of explanations.

  The explanations describe the local format line ("no explanation", "a Python code block follows") and confabulate
  the task (Fibonacci, medians, prime numbers). Per the plan's F5 rule: **the released L20 NLA does not verbalise
  algorithm identity at the end-of-prompt positions**. This is not evidence that no plan exists there.
- **At generated tokens the NLA sometimes names the realised algorithm before the visible text identifies it.**
  - Pre-identifying positions only: up to 0.28 (ban, g8) and 0.18 (twin, g4).
  - The outside reader is better. In the MIXED conditions it predicts the realised algorithm 0.25 of the time
    against the NLA's 0.07 (exact McNemar b=20, c=88, p = 2e-11, Holm-significant). This holds on the 120 samples
    behind 364 (sample, position) units.
- **Causal arm (pre-registered): FAIL on all 4 tasks** (T10 union-find, T05 brute force, T06 Floyd, T04 KMP).
  - The verbal edits barely move the reconstruction. Appending "The response will implement Y" instead of "... D"
    changes the AR output by cos 0.9992, so ‖Δ_edit‖/‖h‖ is 0.04 per position (×4 = 0.16).
  - Patching the four prefill positions changes nothing. All 15 PRE cells per task stay within 0-3 slots of C0, and
    none rises above it. This holds even for the unedited round trip at 0.8‖h‖, which does propagate (0.76‖h‖ at
    block 27).
  - The only pre-registered trend is T06 GEN ×2 vs C0, 4:0 discordant pairs (p = 0.125).
- **EXPLORATORY: the verbal edit does steer on 2 of 4 tasks, but only at the generated-token site and only at large
  doses.** This was added after the committed nulls and was never pre-registered.
  - **T06 (hash set → Floyd).** The NLA edit ×8, added at READ and generated positions 1-64, gives Floyd
    **0.76 vs 0.28 for C0** (N=50 CRN pairs, 25:1).
    - It replicates on fresh slots: 15/20, 13:0, p = 2e-4.
    - It beats the matched random push (28:1), the unrelated-word edit built the same way (12:1, p = 0.003) and the
      norm-matched round trip (13:1, p = 0.002).
  - **T05 (hash map → brute force).** Brute force rises from 0/50 to 10/50 at ×8, and to 23/30 at ×16 with a pass
    rate of 0.90. The random push never moves it.
  - **T10.** Only the forced-state difference-in-means push steers (union-find 0.80 at ×16, 15:1).
  - **T04.** Nothing steers short of breaking the program.
  - **Prefill site.** It stays inert even at ×16 or at the natural difference-in-means norm.
  - **Prompting stays the ceiling, as the field's AxBench prior predicts.** Simply asking for "Implement Y" yields
    0.90-1.00 adherence on all four tasks (T06 Floyd 0.95, T05 brute force 1.00, T10 union-find 0.95, T04 KMP
    0.90). That is above every steering cell. The best steering cells (T06 ×8 0.76, T05 ×16 0.77) also cost pass
    rate as the dose grows (T06 ×16: pass 0.37).
- **No novel algorithm anywhere.** All 10 correct "other" programs across every arm are labeller misses (8) or
  degenerate (2).


## Results in detail

### Behaviour (S3; `results/behaviour.json`, `figures/F0_behaviour.png`)

| task | default (share of correct twin) | twin pass | ban: attempts still using default | Y\* under ban | forced adherence of the causal Y |
|---|---|---|---|---|---|
| T1 grid path | BFS (13/13) | 0.26 | 0.68 | none (DFS 3) | — (best non-default 0.35) |
| T2 shortest path | Dijkstra (38/43) | 0.86 | 0.50 | none (Bellman-Ford/SPFA 9 < 10) | — (Bellman-Ford 0.65 < 0.7) |
| T03 k-th smallest | none (quickselect 0.40) | 0.94 | — | — | excluded (re-gate 26/30) |
| T05 two-sum | hash map (49/50) | 1.00 | 0.28 | **brute force (32/46)** | brute force 1.00 |
| T06 find duplicate | hash set (35/49) | 0.98 | 0.46 | none (Floyd 7) | Floyd 0.95 |
| T10 components | DFS (29/47) | 0.94 | 0.86 | none (DFS 43, union-find 2) | union-find 0.95 |
| T04 substring | naive (50/50) | 1.00 | 0.94 | none | KMP 0.90 |
| R6 first/last | binary search (38/38) | 0.76 | 0.96 | none | bisect 1.00 (not run) |

- Qwen2.5's defaults match Qwen3-8B's except two tasks: T10, where Qwen3 chose union-find, and T03, which has no
  default here.
- The T2 semantic seed (a story describing Bellman-Ford-like rounds) barely moves the model: Dijkstra 28, Bellman-Ford
  6, against 38 / 5 in the twin.
- Engine checks (S2):
  - CRN determinism 8/8;
  - the identity hook is byte-identical to no hook (20/20);
  - batch 1 vs the production batch agree on 15/16 labels (14/16 identical code);
  - identical prefixes give bit-identical states.
- Labeller and judge checks:
  - The labellers get 51/51 catalogue references right (runtime and AST), including the T2 array-Dijkstra rule.
  - Style re-gate: 7 of 8 tasks pass at ≥ 27/30 against two blind code judges (Gemini-2.5-flash, GPT-4.1-mini, with
    DeepSeek as tie-break).

### Instrument gate (S5/S6; `results/layer_convention.json`, `results/gate.json`, `results/av_smoke.json`, `figures/F1_gate.png`)

- **Smoke tests.**
  - Random unit vectors give 4/4 non-degenerate English.
  - The "The capital of France is" state gives explanations naming Paris/France in 3/3, under both conventions.
  - 0 CJK and 0 truncated explanations on the reference set. Among the 6,180 production explanations, 9 describe
    the marker.
- **Layer convention** (pre-registered rule: use [20] unless [21] wins by ≥ 0.05). FVE_ref is 0.580 with
  hidden_states[20] and 0.695 with hidden_states[21], so **[21] is used**. The patch hook sits on block 20.
- **Pipeline check.** |0.695 − 0.752| = 0.057 ≤ 0.10 (PASS). With the training denominator 0.7335 the value is 0.704.
- **Task gate.** FVE_ref (reference-set denominator) is 0.512 → **PARTIAL**. By position class:

  | class | READ | SPEC | g1 | g2 | g4 | g8 | g16 |
  |---|---|---|---|---|---|---|---|
  | FVE_ref | 0.65 | 0.50 | 0.48 | 0.28 | 0.64 | 0.57 | 0.51 |

  - Mean cosine is 0.83 (reference 0.89). Per task the FVE spans 0.47-0.54.
  - The docs formula (each set's own mean) gives 0.47 overall and is strongly negative for READ, g1 and g2. Those
    states are nearly identical across prompts, which is why the plan divides by the reference variance.

### Readout (S7/S9; `results/readout.json`, `data/judgements.jsonl`, `figures/F2-F4, F7`)

Judges: J1 google/gemini-2.5-flash-lite (calibration 1.00), J2 mistralai/mistral-small-3.2-24b-instruct (1.00; it
replaced openai/gpt-4.1-nano at 0.80) and J3 deepseek/deepseek-chat-v3.1 (1.00). Agreement between J1 and J2 by mode:

| mode | raw agreement | κ |
|---|---|---|
| EXPL | 0.94 | 0.82 |
| NAME | 0.67 | 0.56 |
| PREDICT | 0.77 | 0.75 |

J3 resolved 1,064 disagreements. The share left unresolved is 0.6% (EXPL), 1.6% (NAME) and 3.9% (PREDICT).

| test (units) | NLA | comparator | b : c | p | verdict |
|---|---|---|---|---|---|
| **N1** ban names Y\* (T05 only; 16 states) | 0/16 | text NAME 0/16 | 0 : 0 | 1 | FAIL, under-powered (F4) |
| N1-swap / N1-rand / N1-predict | 0/16 | twin 0/16 · random 0/8 · PREDICT 0/16 | 0 : 0 | 1 | — |
| **N2** twin names the default (7 tasks; 112) | 0/112 | text NAME 0/112 | 0 : 0 | 1 | FAIL |
| N3 forced state names the forced Y (7 tasks) | 0.00 on every task | text NAME 1.00 | — | — | FAIL (< 0.3 → F5) |
| N8b ban-failure state names the default it still writes (6 tasks; 96) | 0/96 | PREDICT 0/96, NAME 0/96 | 0 : 0 | 1 | null |
| **N6** per sample, MIXED conditions (364 units, 120 samples) | 0.066 correct | PREDICT 0.253 | 20 : 88 | 2e-11 | outside reader better |
| N5 pre-identifying generated positions | ban g8 0.28, twin g4 0.18 | NAME 0 by construction | — | — | descriptive |

- 4,733 of 5,700 explanations name no algorithm at all.
- At the prefill positions the explanations mention the algorithm named in the prompt in 0.7% of cases (forced 8/1080,
  ban 3/420).
- At generated tokens they mention the default in 19-23% of cases, mostly after the code prefix shows it, e.g.
  `from collections import deque`.
- N4 (seed): the NLA says "none named" on all 20 seed states. The text-only reader says Bellman-Ford; the model
  writes Dijkstra 28 / Bellman-Ford 6.
- N7 (template Spearman) is undefined because the NLA rate is constant at 0. N8: on every ban-failure task the NLA
  names neither the default nor the outside reader's substitute.

**EXPLORATORY local positive control** (`src/local_control.py`, `results/local_control.json`). Is the null an
instrument limit, or does the information fade along the prompt? To find out, the same NLA, judges and rubric read
states AT the algorithm-name token of the condition sentence (NAME), and at that sentence's final period (SENT).
This covers the 3 forced read-out modes × 5 paraphrases and the 5 ban templates per task, i.e. 220 states and 660
explanations. Scores are the majority of 3 explanations:

| position | forced: names Y as planned | forced: mentions Y | ban: names D as planned | ban: mentions D | AR cos |
|---|---|---|---|---|---|
| NAME (on the algorithm's name) | **0.48** | **0.80** | 0.06 (correctly *not* planned) | **0.89** | 0.92 |
| SENT (end of that sentence, 2-8 tokens later) | 0.11 | 0.27 | 0.00 | 0.06 | 0.90 |
| SPEC-3..READ (end of prompt, ~170 tokens later; committed readout) | 0.00 | 0.007 | 0.00 | 0.007 | 0.82-0.87 |

The instrument *can* verbalise algorithm identity, including the ban's negation, when the name is local. For example,
the state at ")" of "Implement breadth-first search (BFS)" reads "...requiring implementation of Breadth First
Search algorithm". The identity then fades from the verbalisable part of the layer-20 state within a sentence. So
the committed null says something specific: the pre-code positions do not carry the algorithm choice in a form this
NLA puts into words. It does not say the NLA is blind.

### Causal arm (S8; `results/causal.json`, `data/labels_causal.jsonl`, `figures/F5_causal_dose_response.png`)

| task (D → Y) | C0 Y-share | EDIT−RT at ×1 / ×2 / ×4 (b:c, p) | PASS |
|---|---|---|---|
| T10 DFS → union-find | 10/30 | −0.03 (0:1) / −0.03 (0:1) / +0.03 (3:2) | no |
| T05 hash map → brute force | 0/30 | 0 / 0 / 0 | no |
| T06 hash set → Floyd | 12/30 | 0 / +0.03 (2:1) / +0.10 (3:0, p = 0.25) | no |
| T04 naive → KMP | 0/30 | 0 / 0 / 0 | no |

- Every other pre-registered cell stays within ±1-2 slots of C0: unrelated edit, random, DIM, GEN ×1/×2, and the
  REV ×2/×4 on T05, the only task with a ban explanation naming Y\*.
- Pass rates stay at 0.93-1.00, so nothing broke.
- Realised push sizes:

  | cell | ‖Δ‖/‖h‖ at block 20 |
  |---|---|
  | EDIT ×1 | 0.041 |
  | UNREL ×1 | 0.036 |
  | RT ×1 | 0.201 |
  | RT ×4 | 0.80 (0.76 at block 27) |

  The read-back error is ≤ 0.08 relative in bf16. ‖Δ_edit‖/‖h‖ equals √(2(1−cos(r1, r0))) × dose to 5e-6 (U8).
  The edit direction is nearly orthogonal to the forced-state difference in means (median cosine 0.09) and to the
  round trip (0.005).
- In activation space (F6) the edit arrows do point from the twin cluster toward the forced-Y cluster on T04, T06
  and T10. The prefill positions simply do not control the algorithm.

**EXPLORATORY dose extension** (`src/causal_extra.py`, `results/causal_exploratory.json`; same slots and hook; Y-share
out of 30 on CRN pairs):

| task | C0 | PRE EDIT ×16 | PRE DIMfull ×2 | GEN EDIT ×8 | GEN RAND ×8 | GEN DIM ×8 | GEN DIMfull ×1 |
|---|---|---|---|---|---|---|---|
| T10 → union-find | 10 | 10 | 9 | 8 | 11 | **19** (10:1, p = 0.012) | 13 |
| T05 → brute force | 0 | 0 | 0 | 4 (4:0, p = 0.125) | 0 | 0 | 0 |
| T06 → Floyd | 12 | 11 | 12 | **23** (12:1, p = 0.003) | 8 | 2 | 6 |
| T04 → KMP | 0 | 0 | 0 | 0 | 0 | 2 (pass 0.83) | 0 |

- DIMfull is the forced-state difference in means at its natural norm: 5-19 residual units, i.e. 0.05-0.17‖h‖.
- The four prefill positions are inert even at 16× the committed edit or at the natural difference-in-means norm.
- Pushing through READ and the first 64 generated tokens can move the algorithm. Which direction works depends on
  the task: on T06 the NLA edit works and the matched DIM moves away from Floyd; on T10 DIM works and the edit does
  not. A matched random push does nothing.

**EXPLORATORY follow-up of the generated-token site** (`src/causal_extra2.py`,
`results/causal_exploratory_followup.json`, `figures/F9_gen_site_dose_exploratory.png`). It adds a dose response, the
same-construction controls and a replication on fresh CRN slots 6-9 (W1-W5 × 4 = 20). Y-share is shown with exact
McNemar on CRN pairs:

| task | GEN EDIT ×4 | ×8 (slots 0-9, N=50) | ×16 | ×8 replication (slots 6-9) | ×8 EDIT vs RAND (N=50) | ×8 EDIT vs unrelated edit | ×8 EDIT vs round trip (matched norm) | GEN DIM ×16 |
|---|---|---|---|---|---|---|---|---|
| T06 → Floyd | 0.60 (7:1, p = 0.07) | **0.76 vs C0 0.28 (25:1, p < 1e-6)** | 0.30, pass 0.37 (breaks) | **15/20 (13:0, p = 2e-4)** | **28:1** | **12:1, p = 0.003** | **13:1, p = 0.002** | 0.07, pass 0.27 |
| T05 → brute force | 0.00 | **0.20 vs 0.00 (10:0, p = 0.002)** | **0.77, pass 0.90 (23:0)** | 6/20 (6:0, p = 0.03) | **10:0, p = 0.002** | 4:0, p = 0.125 | 4:0, p = 0.125 | 0.37, pass 0.40 |
| T10 → union-find | 0.33 | 0.24 vs 0.36 (3:9) | 0.17 | 4/20 | 5:13 | 6:6 | 2:6 | **0.80 (15:1, p = 5e-4)** |
| T04 → KMP | 0.03 | 0.00 | 0.07, pass 0.27 (breaks) | 0/20 | 0:0 | 0:0 | 0:0 | 0.03, pass 0.10 |

**Reading.** On two of four tasks the NLA's verbal edit carries algorithm-specific causal content:
- **T06 (hash set → Floyd).** The effect replicates out of sample. It beats the matched random push, the
  unrelated-word edit built the same way, and the norm-matched round trip, and its dose response peaks at ×8. Beyond
  ×8 the programs break.
- **T05 (hash map → brute force).** The edit moves the choice at ×8-×16, and the random push never does.

This needs pushes far beyond the pre-registered grid (×8 means ≈ 0.3‖h‖ at READ and at each of the first 64
generated tokens) and the generated-token site. On T10 only the forced-state difference in means steers, and on T04
nothing steers short of breaking the program. Like the NLA paper's poetry case, which changed the planned rhyme in
about half of the trials, the edit works on some items and not others. It is not a reliable plan-level control knob,
and none of this is pre-registered.

### Exploratory activation geometry (`analysis/geometry.py`, `results/geometry.json`, `figures/F6_geometry.png`, `figures/F8_mds_centroids.png`)

- READ states are projected onto PC1/PC2 of the forced-prompt states (residual units), and classical MDS is run on
  the forced-algorithm centroids. Every forced algorithm occupies its own region.
- Twin and ban prompts sit apart from all of them, because their prompt form differs.
- **Ban displacement relative to the mode-specific directions** (cosine with c_m − mean_m c_m, the forced-algorithm
  directions after removing the component all algorithms share):
  - The ban moves the state **toward the banned default's own "Implement" direction** on T05 (+0.13), T06 (+0.26)
    and R6 (+0.15). The ban sentence names the default, and the state moves toward that name.
  - It moves toward an alternative on T2 (Bellman-Ford +0.13, Dijkstra −0.09), T10 (BFS +0.23), T04 (Z-algorithm
    / Rabin-Karp / KMP, naive −0.19) and T1 (DFS +0.18).
- Behaviourally the ban mostly fails either way. The prohibition does not move the model to "the edge" of the banned
  algorithm's region; on T10 it pulls it *into* it.

### Novelty audit (`results/novelty.json`)

The audit covers every correct program labelled "other", in every arm: behaviour, the committed causal arm and both
exploratory causal runs. There are 10 such programs. Two blind judges classified each one (Gemini-2.5-flash,
GPT-4.1-mini; DeepSeek on disagreement), and each was matched by similarity to the nearest known solution in the
dependency's pools (LeetCode references, Mercury, TheAlgorithms, KodCode, XLCoST). The nearest matches came from
KodCode or Mercury, at similarity 0.51-0.68.

- **8 are LABELLER_MISS.** Six are T03 counting sorts built with `collections.Counter`; the frozen T03 labeller had
  already failed the style re-gate. Two are T06 boolean "seen" arrays, i.e. a hash-set variant.
- **2 are DEGENERATE.** Reading them by hand confirms both:
  - T06 under the exploratory difference-in-means push: `for i in 1..n: if nums.count(i) > 1`, an O(n²)
    count-per-value scan outside the catalogue.
  - T04 under DIM ×8: a regex look-ahead `re.compile(f"(?={needle})")`, which hands the search to the library.
- **0 are NOVEL.** No push or prompt in this artifact produced a genuinely new algorithm.

### Costs and timing

**OpenRouter spend (this artifact): ≈ USD 2.0**, below the plan's 2.5 and the 10 USD ceiling.

| item | USD |
|---|---|
| NLA judges, incl. calibration, two interrupted passes, the local control and the novelty audit (`results/costs_judges.jsonl`) | 1.82 |
| bench code judges (labeller disagreements + style re-gate) | 0.11 |
| path-task code judges | 0.10 |

There were no budget refusals.

**GPU time** on one L4:

| stage | time |
|---|---|
| target generation, behaviour + committed causal arm (`results/timing.json`) | 68 min |
| exploratory causal cells | ≈ 27 min |
| AV production (6,180 explanations at 0.15 s each) | 16 min |
| AR passes and the state cache | ≈ 8 min |

## Deviations from the plan (all in `results/deviations.json`)

- **D-banpad-T10**: T10: ban of this model's default dfs was ' .'-padded to the twin's length (the twin was matched to the prior default's ban)
- **D-gpu**: Hardware: one NVIDIA L4 (24 GB, 6 CPUs, 66 GB RAM) instead of the planned RTX A4500; bf16 everywhere, no quantisation.
- **D-hfcache**: Model weights live in the run's shared HF cache (HF_HOME set by the pipeline), not in a workspace hf_cache/ (system instruction: never override HF_HOME).
- **D-engine**: The exp27 fixed-shape CRN engine was ported to HF generate: the identical inverse-CDF CRN rule runs as a logits processor (only the CRN token stays finite, greedy on top) and prompts of different lengths are left-padded in one batch. Engine checks: CRN determinism 8/8, identity hook byte-identical 20/20, batch-1 vs production batch label agreement 15/16 (0.94 >= 0.9).
- **D-qwen25-engine-check**: The Qwen3 engine check against earlier cells was replaced by S2 (a)-(d): no Qwen2.5 cells exist anywhere in the run.
- **D-analysis-freeze**: analysis/readout.py, analysis/causal.py and analysis/stats.py were frozen and hashed in commit #2 (before any AV call on a task state and before any causal sample), not in commit #0 (before behaviour sampling). The behaviour stage uses only the commit #0/#1 rules.
- **D-ref-minpos**: Reference-set positions are drawn at token index >= 50 (the NLA training extractor's _MIN_POSITION) instead of >= 16, to match the checkpoint's training distribution; three extra classes (CLRS traces, HumanEval+ prompts, enamel code) are reported apart from the gate set.
- **D-rubric-v2**: Judge rubric v1 -> v2 before commit #2 and before any explanation existed: the 'other' definition was made explicit (an off-catalogue method named as used -> 'other', never 'none_named'); with v1 every judge failed the calibration only on the off-catalogue items.
- **D-judge-swap**: J2 openai/gpt-4.1-nano scored 0.80 on the calibration set (< 0.9) and was swapped, as the plan prescribes, for the next-cheapest model of another family: mistralai/mistral-small-3.2-24b-instruct (1.00). J1 google/gemini-2.5-flash-lite 1.00, J3 deepseek/deepseek-chat-v3.1 1.00.
- **D-calib-forced**: The 30 forced-state calibration items cannot be frozen before the AV runs; commit #2 freezes the rule that selects them (first 30 forced-state explanations #1 in sorted state-id order); they are reported, not gated.
- **D-F4**: Fallback F4 is active: Qwen2.5-7B mostly ignores the W-template bans, so only T05 has a substitute Y* (brute force). The primary N1 test runs on T05 alone and is marked under-powered; N2-default, N8b (ban-failure default naming) and N6 per-sample carry the readout evidence.
- **D-T03-regate**: T03 failed the style re-gate (26/30 < 27) and is excluded from every readout test and from the causal arm, with no revision (plan rule). T03 had no default anyway.
- **D-causal-tasks**: Causal tasks: the priority list T2, T1, T10, T03, T05 yields only T10 (Y = union-find, forced adherence 0.95) and T05 (Y* = brute force): T2's best non-default adherence is 0.65 (Bellman-Ford/SPFA) < 0.7, T1's <= 0.35, T03 has no default. The 4-task cap is filled with the next defaulted bench tasks with an adherent Y: T06 (Y = Floyd, 0.95; tie with value binary search broken by the twin share) and T04 (Y = KMP, 0.90). Fixed in commit #2 before any NLA output.
- **D-judge-items**: After commit #2, src/judges.py was changed to judge only explanations #1-#3 of each state (the analyses use only #1-#3; #4-#6 serve the edit pool, which is selected by the frozen alias lexicon). Cost saving only; no analysis changes.
- **D-causal-batching**: After commit #2, src/causal_gen.py was changed to pack two 30-row cells into one 60-row batch (throughput only; cells, slots, doses and deltas unchanged).
- **D-judge-projection**: The first judge run computed its cost projection as (all earlier judge spend incl. calibration) / (this run's calls) = 6.67 USD and would have applied the S7 reductions; it was stopped after the 107-call pilot and restarted with the projection computed from this run's own calls (cached pilot calls reused).
- **D-judge-json**: J1 (gemini-2.5-flash-lite) answered many PREDICT items with reasoning prose instead of JSON (764 of 1,320 PREDICT items had no parsable J1 answer after one retry). Following F7 ('retry once with a stricter prompt'), the retry now uses JSON mode (response_format json_object) and a 400-token cap. The cost projection now counts only uncached items (an intermediate re-run had applied the S7 reductions on a projection made from a few failing retries; its judgements file was overwritten by the final pass). Items still unparsable keep J2 alone and count as unresolved.
- **D-judge-j3-missing**: J3 also judges items where J1 or J2 returned no parsable answer (87 PREDICT items had no J1 answer even with the JSON-mode retry), so they are resolved 2-of-3 when J2 and J3 agree instead of counting as unresolved.
- **D-exploratory**: Added after the committed causal arm returned nulls, and marked EXPLORATORY everywhere: (1) src/causal_extra.py (PRE x16, GEN x8, natural-norm difference-in-means pushes), (2) src/causal_extra2.py (GEN dose response x4/x16, unrelated-edit and matched round-trip controls, replication on fresh CRN slots 6-9), (3) src/local_control.py (NLA read AT the algorithm-name token: a local positive control for the instrument), (4) analysis/geometry.py (ban displacement vs forced-algorithm directions, MDS of centroids). None of them changes a pre-registered verdict.
- **D-av-hf**: Planned departure (i): AV generation runs in HF generate(inputs_embeds) instead of the reference SGLang server; equivalence checks: injection read-back (row norm 150), neighbours 29/522 asserted, smoke tests (random vectors 4/4 non-degenerate, France 3/3), reference-set FVE 0.695 vs the released 0.752.

## How to run

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml   # all 89 packages pinned
# models are fetched from the HF cache the pipeline sets (HF_HOME); see "Restoring removed files"
.venv/bin/python method.py                 # every stage in order (S0 ... S9)
.venv/bin/python method.py --from S5b      # resume from a stage
# exploratory additions (run after S8):
.venv/bin/python src/causal_extra.py && .venv/bin/python src/labels.py --raw data/samples_causal_extra_raw.jsonl --out data/labels_causal_extra.jsonl
.venv/bin/python src/causal_extra2.py && .venv/bin/python src/labels.py --raw data/samples_causal_extra2_raw.jsonl --out data/labels_causal_extra2.jsonl
.venv/bin/python src/local_control.py
.venv/bin/python analysis/causal_extra.py ; .venv/bin/python analysis/geometry.py
```

Requirements:
- One GPU with ≥ 22 GB. It ran on an NVIDIA L4 (24 GB), with 6 CPUs and 66 GB RAM.
- Python 3.12, with a `python3.12` on PATH for the labellers' sandboxes.
- OpenRouter access (`OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY`) for the judges.

Runtime and spend: GPU generation took ≈ 68 min for the pre-registered arms plus ≈ 27 min for the exploratory cells. AV/AR and the state cache took ≈ 25 min. OpenRouter spend was ≈ USD 2.0.

## Layout

| path | what it holds |
|---|---|
| `method.py` | the pipeline driver: runs every stage script below in order (`--from` / `--only` to resume) |
| `src/cfg.py` | constants (models and revisions, tasks, templates, positions, doses, thresholds) and I/O helpers |
| `src/engine.py` | the bf16 HF engine: exact inverse-CDF CRN sampling as a logits processor, fence stop, block-output delta hooks, teacher-forced state capture |
| `src/prompts.py` | twin / ban / forced / seed prompt builders (Qwen2.5 chat template), end-relative positions, the catalogue and alias lexicon |
| `src/gen.py` | S2 engine checks and S3 behaviour generation |
| `src/labels.py` | the frozen labellers (bench runtime trace + AST rules; exp8 suite for T1/T2 with exp28's array-Dijkstra rule; blind judge on disagreement) |
| `src/behaviour.py` | commit #1 defaults, per-task behaviour report, batch-invariance check, style re-gate |
| `src/states.py` | S4 layer-20 state cache (prefill, generated tokens, random perturbations, broad reference set, smoke states) |
| `src/nla_av.py` | S5 AV explanations (injection mirrored from `nla_inference.py`) |
| `src/nla_ar.py` | S6 AR reconstructions, FVE gate, layer-convention check, deterministic edits, causal deltas, commit #3 |
| `src/judges.py` | S7 blind judges (EXPL / NAME / PREDICT), calibration gate, cost control |
| `src/commit.py`, `src/commit0.py`, `src/commit2.py` | the sha256-chained pre-registration (`commitments.log`, `predictions/`) |
| `src/causal_gen.py` | S8 causal arm (PRE / GEN / REV cells, read-back and downstream displacement logs) |
| `src/novelty.py` | novelty audit of every correct 'other' program |
| `src/dep_usage.py` | uses all ten datasets of the dependency `art_j3Rm_lr2nzR6` and fetches the Ultra-FineWeb reference documents |
| `src/figures.py`, `src/outputs.py` | figures F0-F9 and `method_out.json` |
| `method_out.json` (= `full_method_out.json`), `mini_method_out.json`, `preview_method_out.json` | the exp_gen_sol_out output: datasets nla_behaviour (1,646 programs), nla_readout_states (1,900 states; predict_nla vs predict_text_only_name vs predict_outside_reader), nla_causal (2,314), nla_causal_exploratory (1,960), nla_local_control_exploratory (660); every analysis in `metadata` |
| `src/tests_cpu.py` | U1 labeller tests on all 51 catalogue references |
| `analysis/readout.py`, `analysis/causal.py`, `analysis/stats.py` | the committed analyses (sha256 in commit #2) |
| `analysis/geometry.py` | exploratory activation geometry (not pre-registered) |
| `analysis/causal_extra.py` | exploratory causal extension + follow-up analysis (not pre-registered) |
| `src/causal_extra.py`, `src/causal_extra2.py`, `src/local_control.py` | exploratory GPU additions (dose extension, GEN follow-up, local positive control) |
| `run_chain.sh` | the GPU chain used for S6-S8 (AR gate -> AV production -> AR production -> causal arm + judges) |
| `audit/rederive.py` | U12 independent re-derivation (standard library only) with placebos |
| `audit/rederive_headlines.py` | independent re-derivation of every README headline number (behaviour, FVE, N6, exploratory causal, local control) with placebos -> `results/rederive_headlines.json` |
| `reproducibility.md`, `pyproject.toml`, `env_freeze.txt` | exact reproduction steps; all 89 packages pinned to the installed versions |
| `inputs/` | read-only copies of the prior-run bench, suite, templates, engine and prompts (`inputs/SHA256SUMS`) |
| `third_party/` | `kitft/nla-inference` and `kitft/natural_language_autoencoders` (reference client, docs, worked examples) and the HF sidecars |
| `predictions/` | commits #0-#3 (design, defaults, readout plan, causal plan) |
| `data/` | prompts, raw samples, labels, explanations, judgements, reference sources, novelty pool |
| `cache/` | layer-20 states, AR reconstructions, causal deltas (kept on the run volume) |
| `results/` | every result JSON (behaviour, gate, readout, causal, novelty, geometry, costs, timing, deviations, ...) |
| `figures/` | F0-F9 as PDF and PNG |
| `logs/` | stage logs |

## Kept artifacts (on the run's storage volume; `cache/*.npz` is excluded from the published repository)

- `cache/states_L20.npz`: 2,552 layer-20 states (hidden_states[20] and [21], fp32, 73 MB), indexed by
  `cache/states_index.jsonl`.
- `cache/recon.npz`: the AR reconstruction of every explanation (91 MB).
- `cache/deltas.npz`: the 402 committed causal deltas (5.7 MB, below the size floor). Their sha256 values are in `predictions/commit3_causal.json`.
- `cache/local_states.npz`: the states of the exploratory local control.

## Restoring removed files

The manifest (`.aii/manifest.yaml`) deletes only things that can be rebuilt:

| deleted path | command that brings it back |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` (all 89 packages pinned) |
| `src/__pycache__/` | `.venv/bin/python -m compileall -q src` |
| `analysis/__pycache__/` | `.venv/bin/python -m compileall -q analysis` |
| `inputs/exp11/bench/__pycache__/` | `.venv/bin/python -m compileall -q inputs/exp11/bench` |
| `inputs/exp11/bench/common/__pycache__/` | `.venv/bin/python -m compileall -q inputs/exp11/bench/common` |
| `inputs/exp8/suite/__pycache__/` | `.venv/bin/python -m compileall -q inputs/exp8/suite` |
| `inputs/exp8/suite/labeller/__pycache__/` | `.venv/bin/python -m compileall -q inputs/exp8/suite/labeller` |
| `inputs/exp8/suite/tasks/__pycache__/` | `.venv/bin/python -m compileall -q inputs/exp8/suite/tasks` |
| `inputs/exp28/src/__pycache__/` | `.venv/bin/python -m compileall -q inputs/exp28/src` |

Every `__pycache__/` is also recreated automatically the first time a script imports those modules.

The two reference repositories under `third_party/` are kept, but their `.git/` folders are not published. To get a
fresh clone at the commits used:
- `git clone https://github.com/kitft/nla-inference.git third_party/nla-inference` (commit `38b802a`)
- `git clone https://github.com/kitft/natural_language_autoencoders.git third_party/natural_language_autoencoders`
  (commit `0577769`)

Model weights were never stored in the workspace. To fetch them into the HF cache:

```bash
hf download Qwen/Qwen2.5-7B-Instruct --revision a09a35458c702b33eeacc393d103063234e8bc28
hf download kitft/nla-qwen2.5-7b-L20-av --revision b88469162777ae6553bc14208eb0cb579336f8f4
hf download kitft/nla-qwen2.5-7b-L20-ar --revision e2c9e57eac213d37a31612087f645ab6332c1bb6
```

The dataset dependency `art_j3Rm_lr2nzR6` (`full_data_out.json`) is read through one constant, `cfg.DEP_DATASET_DIR`. It defaults to the sibling folder `../art_j3Rm_lr2nzR6` that the repository publishes, and the environment variable `ART_J3RM_DIR` overrides it. That artifact's `restore.sh` rebuilds its sources. Step-by-step reproduction, with every command actually run, is in `reproducibility.md`.
