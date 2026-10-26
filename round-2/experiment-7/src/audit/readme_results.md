**Headline (descriptive; two tasks, one model; FRLP gate failed, so every C1 number below is descriptive).**

1. **Instrument checks.** The canonical labeller reproduces exp1 (combined vs adjudicated 0.965; references 22/22;
   `results/labeller_recheck.json`). All 11 algorithms became FRLP-measurable (bidirectional Dijkstra only through the
   descriptive forced family: 14 labelled of 120, comment-only scrubbing; `results/yields.json`). The teacher-forced
   scorer needed fp32 activations: bf16 numerics moved per-program log-likelihoods by up to 2 nats between equivalent
   computation paths (`logs/scorer_validation*.json`). Throughput (about 1,000 tok/s on an L4) fired the cut rule:
   M = 20 programs per algorithm, 3 gate paraphrases (`logs/throughput.json`).
2. **FRLP validity gate: FAIL on calibration (a), pass on discrimination (b) and argmax (c)** (`results/gate.json`).
   Under the exp1 baseline prompts FRLP gives DFS a large share on T1 (default-mode share m = 0.83 < 0.9) although
   exp1 sampled 0/300 DFS; (b) 0.92 nats over uniform, (c) 16/19 argmax hits, pooled Spearman 0.74. 298/303 gate
   cells have ESS < 5: the importance weights are dominated by one or two programs. **Diagnosis:** the failure is a
   name-scrubbing artifact. Removing `dfs`/`bfs` identifiers and comments makes a forced program much less likely under
   its own forced prompts than under a neutral prompt, which inflates the weights of minority algorithms. Scored on the
   *unscrubbed* programs (with their own mixture denominators), FRLP passes all three criteria on all 19 events:
   (a) S = 0.95, m = 1.00; (b) 1.18 nats; (c) 17/19. These numbers are in the sensitivity table below and are
   reported, not adopted, per the frozen rule. The single-proposal denominator also passes; the code-body-only and
   256-token-truncated variants do not.
3. **C1 share test: pooled branch UNDETERMINED under both references and the ESS-weighted variant** (robust;
   `results/c1.json`). Per task it is UNDETERMINED everywhere except T1, which is X-SPECIFIC-UNAIMED under the
   mention-twin reference and the ESS-weighted variant. Pooled X-specific SHARE 0.55, 95% CI [0.25, 0.67] (neutral-twin reference); 0.66
   [0.49, 0.87] with mention twins. The CIs straddle 0.5. The gains are far above replicate noise
   (V_u + V_s CI well above 0, F = 16-22), so this is not pure subtraction.
4. **Neither rival account fits cleanly.** (i) No aimed substitute: the X-specific residuals are not aimed at the
   prime-and-veto profile (AIM -0.10, null 95th percentile 0.20, p = 0.80) nor at the free-form association profile
   (-0.12, p = 0.77). (ii) No coherent generic ladder: the 8 generic perturbation profiles (nonce ban, 6 matched-norm
   random prompt edits, novelty instruction) do not agree with one another (mean centred cosine 0.34 on T1, -0.02 on
   T2; the threshold is 0.5), and the random-edit profile is only partly reproducible across seed families
   (r = 0.53 and -0.26).
5. **Bans prime the banned name.** Banning an *absent* algorithm raises its own FRLP by +2.5 to +27 nats in 8 of 9
   cases (e.g. IDDFS +23.5, Floyd-Warshall +15.4, Dial +26.9). Only the modal bans (BFS -8.3, Dijkstra -5.0) and A*
   (-5.9) lower their own label. This is the lexical-priming effect that the mention twins control for.
6. **Iteration-1 sham observations are absorbed by the shared component.** In the Floyd-Warshall ban row the
   Bellman-Ford/SPFA gain (2.73) equals the fitted ladder part (2.79); its X-specific residual is -0.06
   [-2.76, 3.67]. The IDDFS -> DFS residual is -0.77 [-7.20, 4.02].
7. **Unscrubbed sensitivity points the other way from UNDETERMINED.** With the gate-passing unscrubbed programs
   (template W1 only, the only template scored raw), the pooled X-specific SHARE is 0.69 [0.51, 0.84]: X-specific,
   T1 X-SPECIFIC-UNAIMED, T2 UNDETERMINED. The like-for-like scrubbed W1-only value is 0.55 [0.18, 0.78]. The aim
   cannot be tested in this variant, because mention twins were not scored on raw programs.
   Two-step bans: FRLP puts essentially all mass on the banned pair (0.9996-1.0, vs exp1's sampled 0.98 and 1.00) and
   lands the remainder on IDDFS/A* (T1) and Floyd-Warshall (T2) (`results/secondary.json`).
   All other sensitivity variants (code-body-only, correct-only, single-proposal, 256-token truncation, and every u
   variant) keep the pooled branch UNDETERMINED (`results/sensitivity.json`).
8. **Caveats.** FRLP is descriptive (gate failed). M = 20 programs per algorithm with ESS mostly < 5 makes every
   cell high-variance. Free-form association answers were often cut at the frozen 32 tokens. Two tasks give no
   generalisation. Q8 (off-catalogue shams) ran only partly (jump point search, 3 of 5 templates; its residual
   does not single out A*), and Q9 (variant ii) was not run (GPU time). The scrubbed-vs-unscrubbed gate contrast suggests the confirmation bench should score unscrubbed
   (or name-matched) programs.

Not run, with reasons: Q8 shams and Q9 variant (ii) (dropped first under the pre-registered drop order when the GPU
cutoff arrived); the exp2-exp5 extension (requires >= 75 min of slack after all analyses; none was left).
