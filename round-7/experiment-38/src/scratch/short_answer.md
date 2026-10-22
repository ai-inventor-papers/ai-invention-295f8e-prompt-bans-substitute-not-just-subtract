1. **Temperature acts only through the fork margin (G3, pre-registered).**
   - Predictions were committed (#1) from teacher-forced logits before any temperature sample: c* probability times
     the fork distribution softmax(z / T) times P(BFS | fork token).
   - They match every top-p-1 cell (T0.3: 0.015 vs 0.02; T0.7: 0.17 vs 0.24; T1.0: 0.32 vs 0.34; T1.3: 0.45 vs
     0.46; MAE 0.026, max 0.074, all inside the Wilson CIs), so G3-LAW holds.
   - The fork-token class nearly fixes the algorithm (H(label | class) = 0.15 bits), so G3-CONC holds.
   - Lowering T from 1.0 to 0.3 switches 16/50 CRN-paired programs to DFS and none back (p = 1.5e-5).
   - Top-k 10 leaves every program unchanged at every T, as committed.
   - In the run's own terms: at tight temperature the model has one idea (DFS). Loosening T only moves mass across the
     one fork it already has. It does not add new algorithms.
2. **A controlled DAS subspace at the fork works as a dose dial; difference in means does not (G2).**
   - At layer 17 (chosen by the committed CV rule), a rank-4 subspace carries the forced-prompt transfer on held-out
     templates and sources: IIA 1.00 and directional dy 7.6 nats, which is 2.6x the full-state swap (a weak
     ceiling at that layer).
   - It passes every committed control: RAND 0.00, SHUF -0.30, a randomly initialised Gemma <= 0.25x the trained
     effect. G2-DAS-REAL holds.
   - Dosed toward the BFS class mean in generation (N = 50, CRN), it raises correct BFS programs from 11 (twin) to 20,
     27, 31, 37, 38 and 42 at lambda 0.1-1, keeping the pass rate (0.68-0.88 vs 0.86). G2-KNOB holds at 5 of 6 doses
     (Holm p down to 2e-8). At lambda 1 that is 42 correct BFS programs, against 35 for an explicit "uses BFS" prompt (sampled from
     index 0).
   - Difference in means at the same teacher-forced effect also flips the algorithm (up to 50/50 BFS) but destroys the
     programs (correct BFS 15 -> 0, pass 0.70 -> 0.00).
   - Caveats:
     - The three seeds share only one direction (principal cosine about 0.5).
     - At layer 17 the subspace holds no more of the twin's natural variance than random, although its coordinate
       tracks y_v (Spearman -0.50).
     - The claim covers forced-prompt transfer at one fork. "One-dimensional" is not licensed.
3. **A circuit for the fork margin, validated in the real model (G1).**
   - Path patching over 1,224 head/MLP x position nodes points to two parts:
     - early MLPs at the condition sentence (L0, L14), where the prompt's noun enters;
     - a fork-position stack (MLP L21/L22, head L22.H5, MLP L25/L26, with head L33.H2 writing to the margin), connected
       by kept edges.
   - Against 50 write-norm-matched random components per node, 7 of 10 nodes pass the committed node claim under
     ABLATE and 8 of 10 under STEER (Holm). The joint top-5 set beats all 50 matched random sets.
   - In generation (N = 30, CRN), steering the top-5 nodes toward the BFS-leaning class doubles correct BFS
     programs, 8 -> 16 (vs twin p = 0.019; vs 5 matched random nodes p = 0.006; pass 0.83). Ablating them to the
     class mean does not move the algorithm (12 vs 9 attempted, n.s.).
4. **Iteration 6 re-checks.**
   - The engine reproduces iteration 6 (y_v Spearman 1.000; 0.94 per-slot label agreement). The twin share 0.38 lies
     just outside iteration 6's CI because these 50 slots are BFS-heavy (iteration 6's own share on them is 0.36).
   - The failed U6 calibration does not reproduce: both paths agree with the natural share. Batching changes 9 of 200
     CRN-coupled programs (p = 0.039).
   - The fork token also fixes the implementation: forcing `queue` yields 125/125 path-carrying BFS programs, and none
     pass the hidden tests.
5. **No novel algorithm, and the transcoder graph could not run here.**
   - Of 2,325 correct programs in all arms, none was labelled 'other' (rule-of-three upper bound 0.0013).
   - The style re-gate agrees 30/30 (mistral-small-3.2) and 9/9 parsed answers (gemini-2.5-flash-lite, 21 unparsed).
   - G1T_SENTENCE
