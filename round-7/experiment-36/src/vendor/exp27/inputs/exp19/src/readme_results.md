## Results

**Design actually run.**

- 10,100 labelled programs, every cell at N = 50 (5 templates × 10 CRN slots). No cell was dropped: the time rule kept the whole queue.
- E6 + R2: 7 tasks × up to 17 arms.
- The 8 non-movable bench tasks: 11 arms each.
- Engine: Qwen3-8B FP8 W8A8 on a 16 GB RTX 2000 Ada; 2.53 GPU-hours of batch time.
- Judge and audit spend: USD 0.23.

**Bottom line.** Under the pre-registered rule, C1 is **PARTIAL**. Plan noise is not the uniformly cheapest knob.

**Where PN wins.** On 4 of the 6 decisive tasks, PN buys more correct diversity at a cost of at most 5 pass points than
any non-activation knob:

- T03 (k-th smallest): H5 2.72 against 1.96 for the novelty instruction; PN is ahead in every bootstrap replicate.
- T10 (connected components): 2.09 against 1.96 for the iterated veto; PN is ahead in 91% of replicates.
- T05 and T1: small, uncertain edges. T05: 1.29 vs 1.24; T1: 1.42 vs 1.34.

On T03 and T10, PN reaches Hill 1.5 and Hill 2 at zero pass cost.

**Where PN loses, and why the rule is not met.** PN loses decisively on two tasks:

- T06 (find duplicate): PN does not move hash_set at all at alpha <= 2. The reused iterated veto reaches 2.73.
- T2 (weighted shortest path): the semantic seed reaches 1.93 against PN's 1.35. PN's Bellman–Ford/SPFA programs
  cost 14–26 pass points.

The pooled margin D̄ is therefore −0.22 (task-bootstrap 95% CI [−0.89, 0.30]). Only 2 tasks reach H5 ≥ 1.5, against
the 3 required, and the CI includes 0. Every pre-registered sensitivity gives the same PARTIAL verdict (s1–s8):

- twin-segment hull;
- min-p and verbalized sampling added to the comparison set;
- dial interpolation;
- template-cluster and slot-paired bootstraps;
- both 'other' conventions;
- reused vetoes excluded;
- Step-0 vertices only.

With the reused iteration-3 vetoes excluded (s7), D̄ turns positive: +0.20, 95% CI [−0.19, 0.60]. Without them, PN
loses only to the semantic seed on T2.

**What the comparison knobs did.**

- **Temperature (1.3, 1.6), top-k 10 and the nonce ban buy no correct algorithmic diversity on any E6 task** (H5 ≤ 1.09
  everywhere).
- Min-p at T 1.6 / 2.0 stays at H5 ≤ 1.17.
- The novelty instruction switches T03 wholesale to quickselect. That gives Hill 1.0 on its own, and 1.96 only when
  mixed with the twin.
- The verbalized-sampling (VS) prompt mostly produces *programs that choose an algorithm at run time*: 46–49 of 50 on
  every bench task and T1 call `random.choice(s)` inside `solve()`. Their mechanism label is whichever branch the
  labeller's trace happened to execute, so VS "diversity" is partly a measurement artifact
  (`results/vs_dispatch.json`).

**Ideas vs phrasings (CRN flips).**

- Temperature rewrites code without changing the algorithm. On T1, T1.6 changes the code in 88% of CRN slots and the
  label in 2%; it raises phrasing clusters within BFS from 13.6 to 18.5 (20 programs, Jaccard ≥ 0.8).
- PN changes the algorithm. At alpha 2 the label differs from the twin's in 50% (T03), 60% (T10) and 54% (T2) of slots.
- Top-k 10 never changed a single token sequence: the model's top-10 mass is essentially 1 on these prompts.

**Dose-response.** Off-default share rises monotonically with alpha up to 2 on T03, T10, T1 and T2; T05 and T06 stay
pinned to their default until alpha 4. The breakage point (pass below 0.8 × the twin's) is alpha 4 on T03, T06, T10
and T1, alpha 2 on T2 and alpha 8 on T05; at alpha 8 almost nothing passes. The realised displacement at block 12 is within 0.15% of its target on
all 3,220 PN rows (relative error along u at most 0.0017).

**Held-out task and non-movable tasks.**

- R2 (cycle detection, held out) barely moves under PN: an off-default excess of 0.01 at alpha ≤ 2, H5 1.09, and
  P15 = 29 points.
- On the 8 non-movable bench tasks, PN at alpha ≤ 2 moves almost nothing: off-default excess ≤ 0.04, and H5 between 1.00 and 1.14. The exception is R6, at 1.37, where temperature also reaches 1.42. This agrees with the screen's classification. The strongest knob there is the novelty instruction on T04 (substring search, H5 2.57); the table is below.

**The neutral twin's prohibition frame is inert for algorithm choice.** PLAIN (specification only) and the twin have
identical off-default shares on 5 of the 6 E6 tasks (T2: +0.02), although the frame costs 18 pass points on T1 and
adds 22 on R2.

**Screen forecast** (committed before stage 100). The forecast treated fresh noise as an equal mixture of the screen's
fixed directions. It predicted the C1 outcome correctly (PARTIAL) and the PN alpha-1 composition within the
resampling null on 5 of 6 tasks. It over-predicted T06 (1.76 forecast against 1.00 realised) and T05, and
under-predicted T10.

**Engine and labeller checks.**

- **Engine:** reproduction is bit-exact. Two exp17 screen rows were re-run with the screen's own keys: per-slot label
  agreement 1.00 on all 4 cells, JSD 0 (REPRODUCED).
- **GPU unit tests U1–U6:** all pass. This includes exact alpha-0 coupling (20/20 and 10/10 with other batch-mates),
  displacement accuracy (relative error along u ≤ 0.001), and fence-stop invariance (20/20 bench, 20/20 path).
- **Labeller re-check:** bench labellers recover 100% of references on all 13 tasks, and gold agreement is within 0.02
  of every gate.
- **Novelty audit:** every correct 'other' program is a labeller miss; **0 novel algorithms**. Controls: 10/10 for both
  judges.
- **Label-validity audit:** judge–labeller agreement is 1.00 everywhere except T03 (0.80 for PN and for the novelty
  arm). Re-scoring T03 with the judge's labels leaves D_t at +0.71 (vs +0.76).
- **Placebos:**
  - Replacing every PN setting by the TWIN rows gives D_t ≤ 0 on all 6 tasks.
  - Arm labels shuffled within tasks (100 shuffles): the full committed rule, with the reused vetoes in the comparison set and the bootstrap CI, never returns CONFIRMED (0/100; the count criteria fire in 2/100; `results/placebo_full_rule.json`).
  - The independent re-derivation's stricter counts-only version, without the vetoes, fires in 8/100. That is above the 5% target: the count criteria alone are not selective under exchangeable arms, partly because PN has 4 settings against 1–3 per comparison class. The CI criterion is what keeps the rule specific.
- **Independent re-derivation** (`audit/rederive.py`): 12/12 checks match (counts, every D_t, engine-check JSD), and the hash chain is unbroken. Commit #1 (05:05:55Z) precedes the first row beyond stage 10 (05:06:15Z).

**Precision caveat (carried into every C1 statement).** This machine has a 16 GB GPU, so all rows ran with the FP8 W8A8
engine of the screen (`load_model(fp8=True)`), not the planned bf16. The engine check therefore shows that the
screen's engine is reproduced exactly. It does not measure an FP8-vs-bf16 gap.

### Numbers (generated from the result files: `results/summary.md`)

