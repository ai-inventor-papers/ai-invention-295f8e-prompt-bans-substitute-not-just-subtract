warning: The `fitz` API is deprecated and will be removed in future. Use `import pymupdf` instead.
URL: https://arxiv.org/pdf/2606.29985
Type: PDF
Pattern: temperature (5 matches in 106527 chars)

--- Content ---

52835:...meter
Value
Learning Rate (LR)
1 × 10−6
Optimizer
AdamW
Training Batch Size
128
PPO Mini-batch Size
32
Rollouts per Question (N)
8
KL Coefficient
0.001
Rollout Temperature
1.0
Max Input Tokens
1024
Max Response Tokens
4096
Table 4: Common hyperparameters used for diversity-
aware RLVR training.
A.4
RLVR Training Details
Unless ot...
--
53500:...DQO/DIVER-ED. We used the verl framework
(Sheng et al., 2024) for experiments.
For quality evaluation on OlympiadBench, we
sample 32 solutions per problem with temperature
0.7, following common practice. For approach cov-
erage analysis, we sample 64 solutions per problem
with temperature 1.0 to better capture the range of
approaches each policy can generate.
B
Human Annotation and LLM Judge
B.1
Details in Dataset Construction
For the main analy...
--
63713:...tation, restated conditions, and answer-
formatting patterns.
C.2
Detailed Concordance Implementation
For each problem and model, we sample N = 32
solutions at temperature T = 1.0, keep only cor-
rect ones, and cluster them into approach groups
using the LLM judge. For each tier t and subset
size k, we construct comparison pairs ...
--
72790:...ems after
filtering, we conduct the additional analysis on
OlympiadBench only, following the procedure of
the main paper (N = 32 solutions from Qwen3-
8B-Base, temperature 1.0, subset size k = 4). The
results in Figure 15 mirror our main results in Fig-
ure 3: all metrics retain reasonable discriminative
power in Tier 1, while co...
