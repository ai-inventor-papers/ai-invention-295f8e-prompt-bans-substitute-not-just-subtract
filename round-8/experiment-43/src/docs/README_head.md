# Predicting how temperature shifts code ideas (iteration 8, claim L)

**Question.** Is sampling temperature a "creativity knob" for which *algorithm* a language model writes, and if it
acts on the algorithm at all, can its effect be predicted *in advance* from a handful of tokens? Iteration 7 found, on
one model (Qwen3-8B), that the algorithm is fixed by a single sampled "decision token" and that a law over that token's
tempered probability predicted the temperature sweep on one unit of three. This artifact turns that into a
pre-registered test across **three model families**, with **held-out units that were never used to build the law**.

**What is predicted.** For each unit (a coding task on one model) the pipeline:

1. finds the decision token(s) *blind*: prefix resampling along stratified base programs, a pre-registered Bayesian
   change-point rule, single-token refinement, and forced-token confirmation (each of the 20 most likely tokens at the
   decision position is forced and its continuations are labelled), with a second decision searched inside any impure
   branch (the plan's composition level);
2. commits, by sha256 hash chain and before any temperature sample, the law's prediction of the attempted-label
   distribution at T 0.3 / 0.7 / 1.0 / 1.3 under top-p 1 and top-k 10, computed only from teacher-forced logits along
   the openings and at the decision token(s) plus the T-1 token conditionals P(A | token):

   P_T(A) = sum over openings c of w_T(O_c) * [sum_t pi_T(t | O_c) G_T(t, A) + residual] + (1 - sum_c w_T(O_c)) q_rest(A),
   where G_T(t, A) = P(A | t), or, when a second decision follows t, the same mixture over the second token after the
   intermediate tokens O2;

3. commits four rivals: **B0** the fit twin's shares at every T (no temperature effect), **B1** the shares tempered as if
   the algorithm were one token (q(A)^(1/T)), **B2** the single-decision law (no second level) and **BH** the same law at
   the highest-entropy position (the entropy-fork rival of the RLVR/forking-token literature);
4. samples the same 100 fresh random streams at every temperature (common random numbers, exact McNemar pairing) and
   scores MAE = mean over temperatures of the total-variation distance between predicted and observed label
   distributions. A unit passes at MAE <= 0.10 with H(algorithm | decision classes) <= 0.3 bits; the claim passes on
   >= 70% of scored units including >= 3 held-out units (>= 4 scored).

Units: Qwen3-8B A3 trapped rain water, B6 valid anagram, B3 minimum spanning tree weight (law-development units);
held-out gemma-3-4b-it T04 substring search and R6 first-and-last position, and Llama-3.1-8B-Instruct T1 grid path
(the two Llama bench units selected from its pilot, T03 and T06, were dropped under the plan's time box; their fit
twins, selection and label re-gate stay in the data). All in bf16, no quantisation, one RTX A4500.
