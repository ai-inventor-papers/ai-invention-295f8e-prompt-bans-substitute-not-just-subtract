import sys
p='paper_draft.md'; t=open(p).read()
base=t.index('# Iteration 3:')
E=[]
def rep(start,end,new):
    E.append((start,end,new))

rep("Per readout, the record holds this:", "although the read position projection correlates with compliance across wordings.",
"Per readout, the record holds this. On the shortest path task the prompt route carries the ban in likelihood (0.82) and in behaviour (0.98 [0.89, 1.07], against a direct share of 0.05 [0.01, 0.09]). On the grid task the likelihood readout is dominated by the opening fork (0.87), while behaviour is mixed (prompt 0.50 [0.39, 0.62], direct 0.35 [0.25, 0.45]) and the natural proposal readout puts the direct route at 0.16 [0.11, 0.21]. Llama has the likelihood readout only (0.84 [0.62, 1.46]). Splicing the read position alone carries none of the effect (F_R about 0), even though the read position projection correlates with compliance across wordings.")

rep("The ban-free arms (600 samples each over the 12 tasks)", "(50 samples per task each).",
"The ban-free arms had 600 samples each over the 12 tasks: the neutral twin, the one-shot, persistent and sham signature vetoes, the nonce ban, the novelty instruction, and up to three iterated veto rounds. Three seeded isotropic random directions were patched into the task specification states at layers 12 to 23 at the ban's own displacement norm (50 samples per task each).")

rep("Every family's forecast was smoothed the same way", "an undefined forecast is scored as uniform.",
"Every family's forecast was smoothed the same way (93% forecast, 5% uniform over survivors, 2% on other) and scored by its mean log score per attempt not banned. The frozen rule advances a family that beats the next best by at least 0.10 nats on at least 3 gated events whose top-1 nominations disagree. An undefined forecast is scored as uniform.")

rep("**Wording.** The banned share differed by template far more than by chance (Table 97):", "Under the fourth template the default kept at least 70% of samples on 10 of 12 tasks.",
"**Wording.** The banned share differed by template far more than by chance (Table 97), with a likelihood ratio of 374 on 4 degrees of freedom (p about 1e-79). A mixed logistic model put the template standard deviation at 2.0 logits [1.1, 3.5] and the template by task deviation at 1.25 [1.05, 1.49]; a shuffled template placebo gave p = 0.44 (0.39 in the second audit's own likelihood ratio test). Under the fourth template the default kept at least 70% of samples on 10 of 12 tasks.")

rep("**Design.** For every non-default algorithm Y of the 12 frozen bench tasks", "with seeds shared across arms (Qwen3-8B bf16, vLLM 0.11.0, one NVIDIA L4).",
"**Design.** The experiment took every non-default algorithm Y of the 12 frozen bench tasks with at least one correct forced program: 33 Y, of which 19 are \"priority\" Y whose frozen associate differs from the default. The prompt shows up to 5 name-scrubbed correct programs of Y and then asks one of three things: write a correct solution (the copy twin), write a correct solution that does not use Y (named, the fifth template), or write a correct solution that uses a different algorithm from the one above (unnamed). Each arm had 50 samples per Y, with seeds shared across arms (Qwen3-8B bf16, vLLM 0.11.0, one NVIDIA L4).")

rep("The signature veto rarely removed Y:", "and 46% of final round outputs were invalid.",
"The signature veto rarely removed Y. The subtraction forecast in context was defined for only 4 of 33 Y (median of medians to quickselect, brute force to hash map, label propagation to union find, exponential search to binary search). For 25 of 33 Y, Y still re-emerged in at least 20% of attempts after three rounds. The veto cost a mean 0.70 of pass rate, and 46% of final round outputs were invalid.")

rep("The forecasts were the subtraction forecast (exact one-shot", "with point mass forms as sensitivities.",
"The four forecasts were built as in the Qwen3-8B experiment. The subtraction forecast used exact one-shot, persistent and iterated signature vetoes by truncate and redraw; the ladder pooled the nonce ban, the novelty instruction and three matched-norm random directions added at the task specification positions of layers 11 to 21 during prefill; association used Llama's own frozen answers; and proximity used Zhang-Shasha distance [64]. Association and proximity took a form that transfers the default's mass, with point mass forms as sensitivities.")

rep("**The contest does not resolve in Llama.** Thirteen of 18 events", "and association on kth smallest heapify and pop.",
"**The contest does not resolve in Llama.** Thirteen of 18 events passed the gate and 11 were gated and disagreeing, but only 2 had a winner by 0.10 nats (Table 102). One was the subtraction forecast on two sum, through its undefined forecast scored as uniform, because the ban split between sort and two pointers (42) and brute force (32). The other was association on kth smallest heapify and pop.")

rep("The Wilcoxon tests (exact enumeration over the 11 gated disagreeing events, Holm corrected)", "are not.",
"The exact Wilcoxon tests over the 11 gated disagreeing events, Holm corrected, separate the ban-free families from proximity but not from association. Subtraction minus proximity (+0.345 nats [0.190, 0.633], Holm 0.0088) and ladder minus proximity (+0.306 [0.204, 0.513], Holm 0.0078) are rejected; subtraction minus association (+0.172 [-0.049, 0.606], p = 0.52) and ladder minus association (+0.133 [-0.056, 0.542], p = 0.77) are not.")

rep("Each slot ran the full ban (a),", "N was 100 slots per arm (5 templates by 20); 13,030 samples were labelled by the frozen bench labellers.",
"Each slot ran seven kinds of arm. The full ban (a) and the token-length matched neutral twin (b) are the endpoints. The prompt route (c) splices the twin's condition segment with the ban's task specification and read position states; the direct route (d) splices the ban's condition segment with the twin's later states. The full knockout (K0) removes the condition span from the cache seen by generated tokens. The one-shot signature veto of the default (V1) runs under the twin, and prefills force the default's opening or a neutral `def` line under the ban and the twin. N was 100 slots per arm (5 templates by 20), and 13,030 samples were labelled by the frozen bench labellers.")

rep("Pooled over the five tasks, the prompt route carries 0.61 and the direct route 0.74 (Table 108),", "that F_direct is at least one third 0.99).",
"Pooled over the five tasks, the prompt route carries 0.61 and the direct route 0.74 (Table 108). The preregistered route claim is therefore disconfirmed under all three intervals: the direct route exceeds one third, and the prompt route falls below two thirds with a lower bound far under one half. The bootstrap probability that F_prompt is at most one half is 0.28, and that F_direct is at least one third, 0.99.")

rep("An independent second draw with fresh uniforms", "The task differences are not sampling noise.",
"An independent second draw with fresh uniforms (slots 20 to 39, arms a to d on the five gated tasks, N = 100 each) reproduced the picture. Pooled F_prompt was 0.64 [0.27, 0.94] and F_direct 0.74 [0.43, 0.94], per-task fractions moved by about 0.1 at most (find duplicate F_direct 0.99 then 0.93; two sum 0.96 then 0.93; merge intervals F_prompt 0.39 then 0.49), and the Spearman rank agreement between the draws was 0.89 and 0.90. The task differences are not sampling noise.")

rep("Every task was classed as needing a large direct route", "which fails the rule.",
"Every task was classed in the second commit as needing a large direct route (V_t below 0.5, predicting F_direct of at least 0.25). Four of the five gated tasks hit; merge intervals missed with F_direct 0.02. The Spearman correlation between V_t and F_direct was -0.34, with a one-sided permutation p of 0.30 over five points, which fails the rule.")

rep("**The direction exists, but adding it is no better than a random push.** The leave-one-task-out v was reliable", "yet it carried only 2% to 6% of each position's own ban displacement.",
"**The direction exists, but adding it is no better than a random push.** The leave-one-task-out v was reliable (split half cosine 0.95 to 0.99 across blocks 12 to 23). It was aligned with every held-out task's mean ban displacement (cosine 0.29 to 0.86 at block 18, against a 95th percentile of 0.03 for random directions), yet it carried only 2% to 6% of each position's own ban displacement.")

rep("With 12 more random directions (15 in all, alpha 1, exploratory),", "indistinguishable from random on the grid task (0.06 against a mean of 0.07).",
"An exploratory run added 12 random directions (15 in all, alpha 1). On kth smallest ADD exceeded all 15 (0.80 against a maximum of 0.70 and a mean of 0.24) but landed on the wrong algorithm. On the shortest path task it sat at the 80th percentile (3 of 15 random directions moved it more; random mean 0.20), and on the grid task it was indistinguishable from random (0.06 against a mean of 0.07).")

rep("Decoders of default against other were fitted on batch-1 teacher forced states", "No decoder passed the rule on any testable task.",
"Decoders of default against other were fitted on batch-1 teacher forced states at blocks 8 to 28: the task specification mean, the read position, and generated tokens 1 to 8 and 16. Each was compared with 500 within-template permutations for the path tasks (200 for the bench tasks), taking the maximum over layers, and with three written text controls of matched or greater capacity (token one-hots, layer-0 embeddings reduced to 64 principal components, exact prefix match). No decoder passed the rule on any testable task.")

rep("On the shortest path task the default is spread over templates (2, 0, 4, 3 and 3 of 20)", "neither state nor text decodes the choice within tokens 1 to 16.",
"On the shortest path task the default is spread over templates (2, 0, 4, 3 and 3 of 20), and the choice is made inside the program. The first token at which the two classes diverge comes at a median of about 29 generated tokens, after the frozen window, and neither state nor text decodes the choice within tokens 1 to 16.")

rep("An exploratory extension to tokens 24 to 96", "a single unreplicated point with 12 minority samples.",
"An exploratory extension to tokens 24 to 96 found text matching or beating the state on the grid and substring search tasks. On the shortest path task the state curve was noisy (0.57, 0.66, 0.45, 0.50 and 0.75 at tokens 24, 32, 48, 64 and 96). Only token 96 cleared both the null (0.66) and the text controls (at most 0.60), a single unreplicated point with 12 minority samples.")

rep("**The ban-attending heads are not special.** Mean ablation of layer 21 head 17", "short of the required 0.15.",
"**The ban-attending heads are not special.** Mean ablation of layer 21 head 17 and layer 26 heads 21 and 25 at generated positions under the full ban raised the grid BFS share from 0.12 (the ban, same slots) to 0.24. Every set of three random heads in the same layers raised it to 0.18, so the difference is +0.06 (90% interval [0.02, 0.12]; exact paired p = 0.125 against each random set), short of the required 0.15.")

rep("As the plan had computed, the zero-ablation denominator", "the values themselves (about 0.99 against about 0 on the placebo) carry the information.",
"As the plan had computed, the zero-ablation denominator of 12 to 15 nats makes this rule lenient. A placebo that swaps the SAE and zero-ablation cross-entropy per sequence drives FR_zero to about 0, yet still passes the 0.9 rule at layer 20; the values themselves (about 0.99, against about 0 on the placebo) carry the information.")

rep("This experiment [ARTIFACT:art_ccAbfJVcv0LO] asked three things:", "produces a correct novel algorithm.",
"This experiment [ARTIFACT:art_ccAbfJVcv0LO] asked three things. First, do cumulative token vetoes, an operation the model cannot ignore, reach algorithms that prompt bans cannot? We call this the *token walk*: veto the default's distinctive n-gram, then the next landing's, and so on, up to five algorithms. Second, does a ban that leaves exactly one survivor get that survivor written whenever the model can write it on request? We call the share of programs implementing the survivor *will*, and the share of forced programs labelled as the requested algorithm and correct *can*. Third, does the request's own long-form novelty instruction produce a correct novel algorithm?")

rep("A sham veto of an algorithm-generic n-gram of matched length and presence kept the default", "grid 0.76 against 0.96).",
"A sham veto of an algorithm-generic n-gram of matched length and presence kept the default: grid 50 of 50 (`' start == goal:\\n'`), shortest path 50 of 50 (`' u, v, w'`), substring search 49 of 50 (`' len'`) and connected components 44 of 44 valid (`' range'`). The distinctive veto cut correctness where the sham did not (shortest path pass rate 0.41 against 1.00, Newcombe difference 0.59 [0.43, 0.72]; grid 0.76 against 0.96).")

rep("On the grid task `current_row` and `current_col` replaced", "(`queue popleft()`, 66% to 86% invalid).",
"On the grid task `current_row` and `current_col` replaced `r, c` in 63% of re-emerged BFS programs (7% in references), and on the shortest path task `current_distinct` and `d` replaced `current_dist`. Vetoed strings also leaked through non-canonical spellings, in up to 0.86 of samples on connected components and 0.80 on find duplicate at step 2. The grid code degenerated into near-miss syntax (`queue popleft()`, 66% to 86% invalid).")

rep("The sanity check of the list that leaves only the default gave will 1.00", "while full sort was 45 of 50 under the twin.",
"The sanity check of the list that leaves only the default gave will 1.00 on substring search, 0.86 on find duplicate and 0.94 on connected components, but 0.00 on kth smallest. There the prompt read \"Do not use a size-k heap, heapify-and-pop, quickselect, median of medians or counting sort for this task.\", and all 50 programs implemented quickselect, 48 of them in a function named `quickselect`, while full sort was 45 of 50 under the twin.")

rep("The preregistered list independence test (the default's share", "and was not testable on kth smallest and connected components.",
"The preregistered list independence test asks whether the default's share among default and second-rung programs is the same across lists that ban both. It failed on substring search: 0.82 under the Rabin-Karp list against 0.98 under the built-in list (permutation chi-squared p = 0.033; largest difference 0.16 [0.04, 0.30]; placebos with shuffled membership gave p = 0.61, 0.56 and 0.06). It was descriptive on find duplicate and not testable on kth smallest and connected components.")

rep("The request's two instructions (\"Make a new algorithm\"", "100 of 100 traces completed, 4.1k to 12.4k thinking tokens).",
"The request's two instructions (\"Make a new algorithm\" and \"Make a fully novel algorithm never seen before\", each asking for a design rationale of about 2,000 words before the code) were run with thinking off (N = 25 to 50 per cell) and on (N = 10 per prompt and task, 16k thinking cap). All 100 thinking traces completed, at 4.1k to 12.4k thinking tokens.")

rep("Of 574 outputs with a claim record, 484 (84%) claimed a new algorithm;", "\"Optimized Dijkstra with Early Termination\".",
"Of 574 outputs with a claim record, 484 (84%) claimed a new algorithm. Of those, 189 (39%) contained no code at all, only a rationale of 1,300 to 1,700 words, and 220 of the 295 with code (75%) were catalogue algorithms by the mechanism labeller, under names such as \"Modified Bellman-Ford\", \"BFS with Dynamic Programming\" and \"Optimized Dijkstra with Early Termination\".")

rep("**One wording, everywhere.** The fourth template (`X is not allowed here`) is the weakest wording in every artifact that measured it:", "which is why every within-ban decoder there reduced to a template decoder.",
"**One wording, everywhere.** The fourth template (`X is not allowed here`) is the weakest wording in every artifact that measured it. In the bench forecast experiment it accounted for 197 of 240 banned programs, against 85 to 135 for the other templates. In the bench route experiment its pooled avoidance was 0.19, against 0.42 to 0.62, and it produced 29% of all ban failures. In the exposure template arm its mean avoidance was 0.81, against 0.93 to 0.96. In the locus experiment it kept the default in 20 of 20 bench samples and carried all 61 grid BFS programs under the ban, which is why every within-ban decoder there reduced to a template decoder.")

rep("**Signature vetoes, five times.** Every artifact that vetoed a default's distinctive n-gram found the default carried by more than its surface tokens:", "although the veto was exact.",
"**Signature vetoes, five times.** Every artifact that vetoed a default's distinctive n-gram found the default carried by more than its surface tokens. The default survived every round on 9 of 12 bench tasks in the bench forecast experiment, and Y re-emerged after three rounds for 25 of 33 shown algorithms in the exposure experiment. Only one Llama default (the heap of top-k frequent) was removed, the one-shot veto's avoidance was at most 0.41 in the bench route experiment, and the token walk stalled on all six tasks of the reach experiment although the veto was exact.")

rep("With the wording fixed, avoidance replicates within a few points and the landing replicates in kind:", "and merge intervals to a failing merge without sorting.",
"With the wording fixed, avoidance replicates within a few points and the landing replicates in kind. The same five tasks pass the gate in both artifacts that ran all twelve. Every Qwen3-8B draw sends kth smallest to quickselect and size-k heap, two sum to brute force, find duplicate to index marking, connected components to BFS, and merge intervals to a failing merge without sorting.")

rep("*The likelihood substitution test of iteration 2 cannot decide the title claim.* Its gain and residual argmax", "are not detectable with that instrument.",
"*The likelihood substitution test of iteration 2 cannot decide the title claim.* Its gain and residual argmax hit the realised landing in 0 of 17 Qwen3-8B single bans, against 14 of 17 for the implied mass. No row keeps three estimable survivors, the bootstrap variance of the mean gain is 2.7 times the noise term it subtracted, and a decision on mass would need about 50 programs per algorithm at the lower bound and 129 Qwen3-8B or 43 Llama events. \"Not pure subtraction\", \"not aimed\" and \"no coherent ladder\" are not detectable with that instrument.")

rep("*Shown a correct program of a non-default algorithm and told not to use it, Qwen3-8B snaps back to its default.* The default's share", "and the ladder forecast wins the frozen contest (7 wins; top-1 0.77).",
"*Shown a correct program of a non-default algorithm and told not to use it, Qwen3-8B snaps back to its default.* The default's share of attempts rises from 0.05 under the copy twin to 0.72 under the named ban and 0.82 under the unnamed one. The modal replacement is the default in 24 of 31 gated events, and the ladder forecast wins the frozen contest (7 wins; top-1 0.77).")

rep("*A ban's route is task dependent.* On the bench, pooled over five gated tasks,", "a second draw reproduces every task.",
"*A ban's route is task dependent.* On the bench, pooled over five gated tasks, generated tokens reading the ban carry 0.74 of the effect and the prompt states 0.61. The mechanism is redundant on kth smallest and connected components, direct on two sum and find duplicate, and superadditive on merge intervals, and a second draw reproduces every task.")

rep("The read position predicts how strongly a wording will be obeyed (-0.41 across 110 wordings) but splicing it alone carries none of the effect,", "where the template sets the class.",
"The read position predicts how strongly a wording will be obeyed (-0.41 across 110 wordings), but splicing it alone carries none of the effect. A shared prohibition direction written at the task specification positions is no better than a random push of the same norm. Ablating the three heads that attend to the banned name does no more than ablating random heads, and no within-ban locus exists at generated tokens 1 to 16, where the template sets the class.")

rep("Ban lists fail by reimplementing the banned mechanisms, disguised in 41% to 92% of cases;", "such as Floyd-Warshall.",
"Ban lists fail by reimplementing the banned mechanisms, disguised in 41% to 92% of cases. Cumulative token vetoes are exact but stall at the first or second rung on all six tasks tried. Bans that leave one survivor reach interchangeable alternatives (BFS for connected components) but not algorithms the model can write on request, such as Floyd-Warshall.")

rep("The cross-model sentence of iteration 2 therefore becomes:", "at small N.",
"The cross-model sentence of iteration 2 therefore becomes: Llama attempts more algorithms, but its correct grid output is as collapsed as Qwen3-8B's. Correct-only diversity appears on substring search, connected components, cycle detection and top-k frequent, at small N.")

rep("*The likelihood instrument (FRLP) as the decision instrument", "as the decision instrument for where a ban sends the mass.*",
"*The forced ratio latent probability as the decision instrument for where a ban sends the mass.*")

for start,end,new in E:
    i=t.find(start, base)
    if i<0: print('MISSING START', start[:70]); sys.exit(1)
    if t.find(start, i+1)>=0 and t.find(start,i+1) < len(t): 
        # ensure unique after base
        if t.find(start, i+1) > 0 and t.find(start,i+1) >= base:
            print('NONUNIQUE', start[:70]); sys.exit(1)
    j=t.find(end, i)
    if j<0: print('MISSING END', end[:70], 'for', start[:50]); sys.exit(1)
    j+=len(end)
    old=t[i:j]
    if len(old) > 2500: print('TOO LONG', start[:60], len(old)); sys.exit(1)
    t=t[:i]+new+t[j:]
open(p,'w').write(t)
print('applied',len(E))
