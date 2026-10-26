## 2.6 Multi-ban experiment: the top-five prohibition and leave-one-survivor bans

**Why.** The request asks what happens when the top five algorithms are prohibited in one prompt: does the implemented algorithm move to the edge of the banned region, or to its opposite side? Iteration 1 could not reach that test through its greedy succession, because the model stopped complying after two bans. This experiment [ARTIFACT:art_IVZc3TWCeE9f] ran the prohibition as single prompt conditions, with a control for each reading of "where the mass goes", and asked on the shortest path task whether the model can and will write each algorithm when it is the only one allowed.

**Catalogue extension.** The grid catalogue was extended toward the ten algorithms the request imagines: greedy best-first search was split from A*, and IDA*, a 4-neighbour jump point search and bidirectional A* were added, with new references that both labellers got right (25 of 25) and targeted unit probes (4 of 4). The canonical labeller re-check gave 135 of 144 gold programs and 22 of 22 references. The 40-program gold gate of the extended labeller was missed: 33 of 40 at round 0 and 32 of 40 after the one allowed revision, runtime against AST kappa 0.53; unit weight Dijkstra, jump point search and bidirectional A* fell below three of four gold programs and were excluded. An algorithm was kept if at least 70% of its 40 forced programs were labelled as requested (Table 66). Only BFS, DFS, IDDFS, greedy best-first and IDA* passed, so the extension failed. The model mostly writes A* as a cost-only heap (unit weight Dijkstra 25 of 40), unit weight Dijkstra as BFS (18 of 40), and jump point search and bidirectional A* as BFS and A*. The analysis catalogue (seven algorithms) kept A* and bidirectional BFS, flagged, because each has at least 10 programs and passes the gold set. With seven algorithms the frozen set rule gives four-name sets: TOP (the four with the highest baseline likelihood: BFS, DFS, greedy, IDDFS), ARC (four contiguous on the manifold: BFS, bidirectional BFS, A*, greedy) and SCATTER (four spread out: BFS, DFS, greedy, IDA*). The literal five-name ban TOP5 (BFS, DFS, greedy, IDDFS, A*) was added. Six landing forecasts per set (ladder, prime-and-veto, proximity, likelihood under the ban, generic perturbation, corpus frequency) were hash-chained before the multi-bans were sampled, and the chain verifies.

**Table 66.** Keep rule for the extended catalogues: forced programs labelled as requested (source: `results/catalogue_keep.json`; 40 forced programs each).

| Task | Algorithm | Forced prompt | Labelled as requested | Of those, passing | Other labels | Kept |
|-|-|-|-|-|-|-|
| Grid | BFS | plain | 40 | 38 | none | yes |
| Grid | DFS | plain | 40 | 9 | none | yes |
| Grid | IDDFS | plain | 37 | 0 | DFS 3 | yes |
| Grid | greedy best-first | plain | 35 | 25 | BFS 2, other 2, A* 1 | yes |
| Grid | IDA* | descriptive | 36 | 0 | A* 3, BFS 1 | yes |
| Grid | bidirectional BFS | plain | 21 | 5 | BFS 16, other 3 | no (kept in analysis, flagged) |
| Grid | A* | plain | 11 | 11 | unit weight Dijkstra 25, other 3, BFS 1 | no (kept in analysis, flagged) |
| Grid | unit weight Dijkstra | plain | 13 | 11 | BFS 18, other 9 | no |
| Grid | jump point search | descriptive | 7 | 0 | BFS 21, other 11, unit weight Dijkstra 1 | no |
| Grid | bidirectional A* | descriptive | 5 | 0 | A* 28, BFS 3, other 3, bidirectional BFS 1 | no |
| Shortest path | Dijkstra | plain | 40 | 40 | none | always run |
| Shortest path | Bellman-Ford/SPFA | plain | 40 | 34 | none | always run |
| Shortest path | bidirectional Dijkstra | plain | 14 | 9 | Dijkstra 22, other 4 | always run |
| Shortest path | Floyd-Warshall | plain | 40 | 40 | none | always run |
| Shortest path | Dial | plain | 36 | 7 | other 4 | always run |

**Every multi-name ban fails.** With one name banned the model complies (avoidance 0.86 on the grid task, 0.84 on the shortest path task). With four or five names it mostly writes a banned algorithm anyway (Table 67): avoidance is 0.13 for TOP, 0.37 for ARC, 0.04 for SCATTER and 0.00 for the literal five-name ban, so every multi-ban fails the event gate. The banned programs are BFS and DFS re-implemented, often without naming their mechanism (Table 68). We call a banned-mechanism program *disguised* when its comments and identifiers never name its own mechanism; 41% to 92% of the banned programs under a multi-ban are disguised, DFS most often as "backtracking". The likelihoods committed before sampling foresaw the failure for three of the four sets: the implied avoidance was below 1e-8 for TOP, SCATTER and the five-name ban, against realised 0.13, 0.04 and 0.00. For ARC the implied avoidance was 0.9995 against a realised 0.37. A ban prompt raised the likelihood of the banned algorithms' own programs relative to the neutral twin (DFS gained about 10 nats under the first template of TOP), the same priming as in the likelihood screen.

**Table 67.** Grid multi-name bans and the single-name references (N = 100 each, five templates by 20; mechanism labels of attempted programs; source: `results/landing.json`).

| Condition | Banned | Landing (attempted programs) | Avoidance [Wilson 95%] | Template-cluster 95% CI | Avoidance per template (W1 to W5) | Pass rate |
|-|-|-|-|-|-|-|
| Grid baseline | none | BFS 100 | n/a | n/a | n/a | 0.89 |
| Grid single ban | BFS | DFS 86, BFS 14 | 0.86 [0.78, 0.91] | [0.58, 1.00] | 1.0, 1.0, 1.0, 0.30, 1.0 | 0.41 |
| TOP | BFS, DFS, greedy, IDDFS | BFS 59, DFS 26, greedy 2, other 13 | 0.13 [0.08, 0.21] | [0.01, 0.29] | 0.15, 0.05, 0.0, 0.0, 0.45 | 0.40 |
| ARC | BFS, bidirectional BFS, A*, greedy | BFS 63, DFS 37 (DFS allowed) | 0.37 [0.28, 0.47] | [0.09, 0.68] | 0.70, 0.15, 0.15, 0.0, 0.85 | 0.60 |
| SCATTER | BFS, DFS, greedy, IDA* | BFS 69, DFS 27, A* 2, other 2 | 0.04 [0.02, 0.10] | [0.00, 0.08] | 0.0, 0.10, 0.0, 0.0, 0.10 | 0.75 |
| TOP5 (literal) | BFS, DFS, greedy, IDDFS, A* | BFS 63, DFS 36, IDDFS 1 | 0.00 [0.00, 0.04] | [0.00, 0.00] | 0.0, 0.0, 0.0, 0.0, 0.0 | 0.68 |
| Shortest path baseline | none | Dijkstra 100 | n/a | n/a | n/a | 1.00 |
| Shortest path single ban | Dijkstra | Bellman-Ford/SPFA 83, Dijkstra 16, other 1 | 0.84 [0.76, 0.90] | [0.72, 0.95] | 0.90, 0.95, 0.70, 0.65, 1.0 | 0.95 |

**Table 68.** Disguise: banned-mechanism programs that never name their own mechanism (source: `results/landing.json`).

| Condition | Banned-mechanism programs | Disguised | Disguise rate | By mechanism (disguised / programs) | Most frequent self-descriptions |
|-|-|-|-|-|-|
| Grid single ban of BFS | 14 | 14 | 1.00 | BFS 14/14 | none named |
| Shortest path single ban of Dijkstra | 16 | 2 | 0.125 | Dijkstra 2/16 | none named |
| ARC | 63 | 58 | 0.92 | BFS 58/63 | `is_valid` 2 |
| SCATTER | 96 | 49 | 0.51 | BFS 43/69, DFS 6/27 | `backtrack` 10, `is_valid` 7, `depth-limited` 1 |
| TOP | 87 | 44 | 0.51 | BFS 37/59, DFS 6/26, greedy 1/2 | `backtrack` 10, `is_valid` 9 |
| TOP5 | 100 | 41 | 0.41 | BFS 34/63, DFS 6/36, IDDFS 1/1 | `is_valid` 10, `backtrack` 8, `find_path` 2 |

[FIGURE:fig_multiban]

**The list's content barely matters (post hoc).** Across the four multi-bans the model writes the same mix of BFS and DFS: the BFS share among BFS and DFS programs is 0.69 (TOP), 0.63 (ARC), 0.72 (SCATTER) and 0.64 (TOP5), chi-square p = 0.48 and permutation p = 0.57. This holds whether DFS is on the list (TOP, SCATTER, TOP5) or allowed (ARC). Avoidance differences therefore come from whether DFS happens to be banned, not from a list-specific landing. A single BFS ban moves the model to DFS 86%; a list of four or five names moves it to about one third DFS, which looks more like a generic perturbation of the default than a veto. This comparison was not preregistered.

**Landing tests are degenerate.** Only ARC (37 DFS programs) and SCATTER (2 A* programs) put any mass on a survivor. On ARC the ladder, prime-and-veto, likelihood, generic-perturbation and corpus forecasts all named DFS (log score +1.06 nats per program over uniform), and proximity named IDA* and missed (-0.02). With three survivors the exact permutation floor is 1/6, every per-set p is at least 0.33, and every pooled p is at least 0.11; the edge-against-opposite statistic was 0 on both sets with mass (p = 0.67). The request's literal question therefore has a behavioural answer that is neither of its two options: under a four- or five-name ban the model does not move to the edge or to the opposite side of the banned region, it re-implements the banned defaults. Over all programs, "no change" (the task's default algorithm) predicted 64% of multi-ban programs, against at most 10% for any committed survivor forecast; on single bans the highest-ranked non-banned algorithm predicted 85% and the default 15%; under forced prompts the requested algorithm was written 66% of the time.

**Leave-one-survivor bans: "can" against "will".** On the shortest path task each of the five algorithms was left as the only one allowed, by banning the other four (Table 69). The model writes Dijkstra when it is the survivor 95% of the time and Bellman-Ford/SPFA 51% of the time. It writes bidirectional Dijkstra, Floyd-Warshall and Dial 0% of the time, falling back to the banned Dijkstra or Bellman-Ford/SPFA instead, although when forced it writes Floyd-Warshall correctly 40 of 40 times and Dial 36 of 40 times. The likelihood gains follow the same split: banning the other four lowers Dijkstra by 3.35 nats and Bellman-Ford/SPFA by 0.21 when each is the survivor, and raises the three algorithms the model never writes by 7.6 to 24.3 nats without moving them into the sample.

**Table 69.** Shortest path leave-one-survivor bans (N = 100 each; "will" = share of programs implementing the survivor; "can" = share of 40 forced programs labelled as the survivor; source: `results/los.json`).

| Survivor (other four banned) | Will [Wilson 95%] | Banned mechanisms written | Other | Compliant share | Can (forced labelled as requested; forced pass) | Mean likelihood gain of the survivor (nats) | Disguised / banned programs |
|-|-|-|-|-|-|-|-|
| Dijkstra | 0.95 [0.89, 0.98] | Bellman-Ford/SPFA 0.05 | 0.0 | 0.95 | 1.00; 1.00 | -3.35 | 4 / 5 |
| Bellman-Ford/SPFA | 0.51 [0.41, 0.61] | Dijkstra 0.48 | 0.01 | 0.39 | 1.00; 0.85 | -0.21 | 8 / 48 |
| bidirectional Dijkstra | 0.00 [0.00, 0.04] | Dijkstra 0.52, Bellman-Ford/SPFA 0.48 | 0.0 | 0.0 | 0.35; 0.225 | +24.26 | 51 / 100 |
| Floyd-Warshall | 0.00 [0.00, 0.04] | Dijkstra 0.59, Bellman-Ford/SPFA 0.40 | 0.01 | 0.0 | 1.00; 1.00 | +7.63 | 46 / 99 |
| Dial | 0.00 [0.00, 0.04] | Dijkstra 0.52, Bellman-Ford/SPFA 0.44 | 0.04 | 0.0 | 0.90; 0.175 | +21.20 | 42 / 96 |

**Geometry and natural-run internals.** In the teacher-forced residual stream, centroid MDS stress-1 was 0.025 (grid) and 0.006 (shortest path). The nearest neighbours were BFS with bidirectional BFS, DFS with IDDFS, and A* with greedy best-first; nearest-neighbour stability was 0.70 across settings and 0.96 under a program bootstrap. Persistent homology, which tracks loops in a point cloud across distance scales, found no persistent loop (H1) on either task, which answers the request's question about a circle in the negative for these clouds. Within-ban probes at generated token 16, a position that does not depend on the label, were near chance on every grid condition and reached balanced accuracy 0.69 (p = 0.03) on the shortest path leave-one-survivor ban of Bellman-Ford/SPFA. Probes at the token before the commit token were confounded, because that position depends on the label. The difference-in-means direction from forced programs aligned with the natural within-ban direction at that position (cosine 0.6 to 0.95) and on the shortest path task at token 16 (0.3 to 0.99), but not for the grid BFS ban at token 16 (-0.13 to -0.01).

**Deviations and cost.** The experiment ran on an RTX 4090 in eager vLLM mode (no C compiler), replaced one duplicated forced paraphrase, missed the gold gate after its revision, and recorded bf16 scoring-path noise of about 1 nat per program; the shortest path likelihoods sum to 0.17, below the 0.3 calibration floor; the noun-B placebo ran after the multi-bans were sampled. It used about 1 GPU-hour and USD 0.42 of judge calls (857 calls).

## 2.7 Llama replication: the same protocol in a second model family

**Why.** A claim about what a ban does inside one model needs a second family. This experiment [ARTIFACT:art_-QPYRaFERCBX] ran shared protocol v2 on Llama-3.1-8B-Instruct [{{Grattafiori2024}}] in bf16 with its default chat template, on the canonical suite, re-tokenising the neutral-noun bank under Llama. It drew 1,780 seeded vLLM generations: baselines, modal bans, mention twins, listing controls, two non-default bans and two two-step bans per task (14 events), 880 forced programs and 220 free-form answers. It scored 248 name-scrubbed forced programs in 39,768 program scores (11.3 million tokens). Nothing was tuned to agree with Qwen3-8B.

**Llama's baseline is not collapsed on the grid task.** It writes BFS 77 times and DFS 20 times in 100, with a low pass rate (0.20). On the shortest path task it is collapsed (Dijkstra 92, pass rate 0.59). The BFS ban sends it to DFS 63 of 100; the Dijkstra ban sends it to Dijkstra 43, "other" 37 and Bellman-Ford/SPFA 18. Both two-step bans fail the gate (Table 70). Bidirectional Dijkstra and Dial could not be written (2 and 1 forced programs kept after up to 120 attempts), so the shortest path catalogue has three algorithms, no row there has three survivors, and the substitution test runs on the grid task only.

**Table 70.** The 14 sampled Llama events (mechanism labels of attempted programs; source: `results/events.json`).

| Task | Event | N | Labels | Banned share | Avoidance | Compliant share | Clear mode | Gate |
|-|-|-|-|-|-|-|-|-|
| Grid | baseline | 100 | BFS 77, DFS 20, other 3 | 0.0 | 1.0 | 0.20 | BFS | pass |
| Grid | ban BFS (modal) | 100 | DFS 63, BFS 29, other 6, A* 1, unit weight Dijkstra 1 | 0.29 | 0.71 | 0.08 | DFS | pass |
| Grid | mention BFS | 50 | BFS 47, other 2, DFS 1 | 0.0 | 1.0 | 0.28 | BFS | pass |
| Grid | listing control | 50 | BFS 36, other 7, DFS 6, unit weight Dijkstra 1 | 0.0 | 1.0 | 0.20 | BFS | pass |
| Grid | ban DFS | 50 | BFS 39, DFS 7, other 4 | 0.14 | 0.86 | 0.14 | BFS | pass |
| Grid | ban unit weight Dijkstra (absent) | 50 | BFS 30, DFS 18, unit weight Dijkstra 1, other 1 | 0.02 | 0.98 | 0.26 | BFS | pass |
| Grid | ban BFS and DFS | 50 | BFS 21, DFS 21, other 6, unit weight Dijkstra 2 | 0.84 | 0.16 | 0.0 | none | fail |
| Shortest path | baseline | 100 | Dijkstra 92, other 7, Bellman-Ford/SPFA 1 | 0.0 | 1.0 | 0.59 | Dijkstra | pass |
| Shortest path | ban Dijkstra (modal) | 100 | Dijkstra 43, other 37, Bellman-Ford/SPFA 18, Floyd-Warshall 2 | 0.43 | 0.57 | 0.05 | none | pass |
| Shortest path | mention Dijkstra | 50 | Dijkstra 39, other 11 | 0.0 | 1.0 | 0.46 | Dijkstra | pass |
| Shortest path | listing control | 50 | Dijkstra 19, Bellman-Ford/SPFA 15, other 14, Floyd-Warshall 2 | 0.0 | 1.0 | 0.24 | none | pass |
| Shortest path | ban Bellman-Ford/SPFA | 50 | Dijkstra 33, other 14, Bellman-Ford/SPFA 2, Floyd-Warshall 1 | 0.04 | 0.96 | 0.26 | Dijkstra | pass |
| Shortest path | ban Floyd-Warshall (absent) | 50 | Dijkstra 25, other 11, Bellman-Ford/SPFA 9, Floyd-Warshall 5 | 0.10 | 0.90 | 0.14 | Dijkstra | pass |
| Shortest path | ban Dijkstra and Bellman-Ford/SPFA | 50 | Dijkstra 22, other 21, Bellman-Ford/SPFA 6, Floyd-Warshall 1 | 0.56 | 0.44 | 0.0 | none | fail |

**The validity gate fails, and the substitution test is unresolved.** Calibration fails on the grid task: the instrument implies BFS 0.43 and DFS 0.55 against a sampled BFS share of 0.77 (Wilson [0.68, 0.84]); the shortest path task passes (Dijkstra 0.97, sum 0.87). Discrimination passes at 0.59 nats per program over uniform across 13 events (1.0 to 1.6 nats on the grid ban and mention events, 0.1 to 0.8 on the shortest path ones, negative for both listing controls). The argmax matches the realised mode in 7 of 10 clear-mode events, below the 0.8 bar; all three misses are on the grid task, where the instrument predicts DFS and sampling lands on BFS. The median cell ESS is 2.5 and 76% of cells are below 5. Under the neutral reference the X-specific share is 0.80 with a 95% percentile interval of [0.28, 0.94], with no aim and no ladder, so the result is not resolved at this sample size; under the mention reference it reads X-specific but unaimed (Table 71). The branch is not robust. Outside the frozen rule, the program-level importance-sampling noise dominates: the bootstrap variance of the mean gain is 5 to 11 times the replicate variance the frozen correction subtracts, the basic interval for the neutral V_u + V_s is [-15.1, 10.2] and covers zero, and the share falls to 0.41 without the five forced programs that the label audit disputed and to 0.44 with a raw-mean ladder profile.

**Table 71.** Llama substitution test, grid task only (source: `results/c1.json`).

| Reference | X-specific share (95% percentile CI) | V_u / V_s / V_u + V_s | Aim at prime-and-veto (null 95th pct; p) | Ladder exists (mean cosine) | Branch |
|-|-|-|-|-|-|
| neutral twin (primary) | 0.80 (0.28, 0.94) | 2.0 / 8.2 / 10.1 | 0.067 (0.258; p = 0.35) | no (0.14) | not resolved at this N |
| mention twin (secondary) | 0.78 (0.61, 0.91) | 7.1 / 25.5 / 32.6 | -0.28 (p = 0.96) | no | X-specific but unaimed |

The association aim did not pass either (-0.08 against a null 95th percentile of 0.30).

**Llama, like Qwen3-8B, primes the banned name.** Naming an absent algorithm in a ban raised its own likelihood in 5 of 6 cases: bidirectional BFS +3.9 nats, IDDFS +7.6, unit weight Dijkstra +1.8, Bellman-Ford/SPFA +4.1 and Floyd-Warshall +4.8; A* was the exception (-1.2). The mention twin primes these algorithms by +6.7 to +14.4 nats and the ban's veto (-4.9 to -10.1) cancels only part of the prime. Bans of present algorithms do lower them: BFS -1.7, DFS -3.0 and Dijkstra -1.0. Within a ban row, the X-specific residual is anti-correlated with how much a survivor's code resembles X (Spearman -0.6 to -0.9 in 5 of 6 grid rows): a ban lowers the survivors that look like the banned algorithm.

**The route, read by likelihood only.** On the two modal bans (20 cells), the ban's drop on the default (-27.2 nats summed) travels mostly by the prompt route: F_prompt 0.84 (bootstrap interval 0.62 to 1.46) and F_direct -0.21 (-1.03 to 0.09). On the grid task the prompt-route arm also reproduces the full ban's redistribution over survivors (cosine 0.98); the direct-route arm does not (0.20).

**Which forecast predicts the program written?** Over 743 attempted non-banned samples the empirical sampled ladder predicted the realised mechanism best (Table 72). The likelihood forecast lost to it overall (difference -0.11, paired sign-flip p < 1e-4) and tied it on single bans (+0.01, p = 0.71). Asked for the standard alternative, Llama answers DFS 20 of 20 times for BFS and Bellman-Ford/SPFA 19 of 20 times for Dijkstra; its top-1 answers match the OpenRouter Llama map of iteration 1 for 9 of 11 algorithms.

**Table 72.** Per-sample top-1 accuracy of each predictor against the realised mechanism label (source: `results/independent_rederivation_headlines.json`).

| Predictor | All 743 samples | Single bans (313 samples) |
|-|-|-|
| likelihood (FRLP) top-1 | 0.59 | 0.67 |
| empirical sampled ladder | 0.70 | 0.67 |
| free-form association | 0.52 | 0.67 |
| latent ladder from baseline likelihoods | 0.51 | 0.63 |

**Checks.** The canonical labeller re-check reproduced the association experiment exactly (22 of 22 references, combined against adjudicated 0.966, runtime against AST kappa 0.753). A blind audit of 50 Llama programs by a second judge agreed with the final labels at 0.78 (grid 0.74, shortest path 0.87), below 0.9 and flagged; most disputes were flawed attempts the audit judge called "other". HF and vLLM scores agreed within 0.003 to 0.007 nats per token. Key-value reuse failed its 0.02-nat tolerance (mean 0.16, maximum 0.40 nats per program, bf16 batch-shape numerics), so an fp32 language-model head was adopted. For 91% of forced prompts an algorithm's own likelihood lay in [-0.7, 0.2]; the default's likelihood matched its log sampled share within 0.11 nats on the shortest path task but was 0.59 nats off on the grid task, where the instrument under-weights BFS. Independent re-derivations matched 34 of 34 quantities and 63 of 63 headline numbers, and a random-predictor placebo never beat the ladder. Cost: USD 0.49 of OpenRouter calls and 0.64 logged GPU-hours on one RTX 4090. Table 72b lists every test the replication ran.

**Table 72b.** Tests of the Llama replication (source: the artifact's `README.md` test table and the `results/*.json` files it names).

| Test | Result |
|-|-|
| Labeller re-check and label audit | pass (22/22 references, combined against adjudicated 0.966); blind audit of 50 Llama programs 0.78, flagged |
| Prompts | pass: 71/71 task texts equal the association experiment's; one BOS token; identical task suffix; ban and neutral twins of equal length (at most 13 filler tokens, no token-level insertion); sampled token ids equal scored ids for 140 conditions |
| Engine agreement | pass: HF against vLLM 0.003 to 0.007 nats per token, program sums within 0.14 to 0.49 nats; 97% of outputs a single fenced code block, 94% exact re-tokenisation |
| Key-value reuse | fails the 0.02-nat tolerance: mean 0.16, maximum 0.40 nats per program (bf16 batch-shape numerics; fp32 language-model head adopted) |
| Scrubber | pass: 244 of 248 forced programs keep pass status and label after the full scrub, 4 after the conservative scrub, 8 unparsable originals dropped; on about 1,400 external programs every residual name is an attribute name |
| Likelihood sanity | an algorithm's own likelihood under its forced prompts lies in [-0.7, 0.2] for 91% of forced prompts; the default's likelihood matches its log sampled share within 0.11 nats on the shortest path task and is 0.59 nats off on the grid task |
| Edit hooks | zero coefficient leaves states exactly unchanged; no change outside the edited span or before the layer band; displacement within 4.3% of target (bf16), not 1e-3 |
| Hybrid caches | pass (difference 0.0) |
| Analysis on synthetic data | pass: ladder, substitution and pure subtraction recovered; uniform aim p under the null; unbiased under exchangeable noise, biased under crossed noise (hence a template-mean sensitivity) |
| Independent re-derivation | 34 of 34 quantities match to 1e-9; placebo p uniform (KS p = 0.61) |
| Headline re-derivation | 63 of 63 headline numbers match by a separate code path; the sampled ladder beats the likelihood forecast overall (-0.112, p < 1e-4) and ties it on single bans (+0.010, p = 0.71); a random-predictor placebo never beats the ladder |

## 2.8 Bench build: a frozen 12-task confirmation bench behind a presence pilot

**Why.** The review's arithmetic called for events, not predictors, and the hypothesis update needed tasks with a present minor algorithm so that present-minor bans and a non-degenerate typicality forecast could exist. This artifact [ARTIFACT:art_0ndRfWKBWclR] built the bench and ran a cheap baseline pilot before freezing any task. No ban prompt was rendered anywhere in it: an audit of 4,310 rendered prompts against a superset ban lexicon found no hit.

**Design.** Thirteen LeetCode-derived tasks [{{Xia2025}}] received a frozen specification in new wording on the canonical scaffold, a catalogue of three to six algorithms (54 in all), 684 hidden tests in total (parsed dataset cases filtered to the specification's bounds, plus generated edge and stress cases), order-free checkers where the answer is a set, and one verified reference per algorithm. Every reference passes at no more than a quarter of the per-case limit, which is the larger of 1 s and ten times the fastest reference; all 39 planted mutants fail. Each task has a runtime-signature labeller backed by an AST labeller, with a blind judge only on disagreement, gated against a gold set adjudicated by two judges and a tie-breaker (Cohen's kappa of at least 0.8, all references correct, runtime against adjudicated of at least 0.90). Qwen3-8B ran from its official FP8 checkpoint through vLLM's FP8 Marlin kernels, because the 16 GB GPU could not hold bf16 weights; decoding was T = 1.0, top-p 1.0, thinking off. Each task received a 50-sample pilot, 20 free-form "standard alternative to X" answers per algorithm, and at least 40 forced, name-scrubbed programs per algorithm, scored by vLLM prompt log-probabilities to give baseline likelihoods (adherence-corrected: L_corr = L + log adherence). Tasks were ordered by how much the ladder, association and proximity nominations disagree (Stage A, committed before gating) and the first 12 gated tasks were frozen with sha256 commitments.

**Table 73.** The 13 candidate tasks (source: `README.md` main table, `results/gate_summary.json`, `results/pilot_stats.json`, `results/frlp_validity.json`, `results/stageA_nominations.json`).

| Task | K | Tests | Gate: kappa runtime vs AST [95% CI] / PABAK / runtime vs adjudicated | Qwen pilot: modal algorithm (share, pass) | Baseline likelihood of the modal algorithm | Best alternative (likelihood) | Sum of exp(likelihood) | Association / proximity nomination | Llama-3.1-8B pilot modal (share) | Status |
|-|-|-|-|-|-|-|-|-|-|-|
| k-th smallest | 6 | 60 | 0.95 [0.84, 1.00] / 0.96 / 0.96 | full sort (1.00, 1.00) | -0.18 | quickselect (-1.5) | 1.05 | quickselect / heapify and pop | heapify and pop (0.34) | frozen |
| two-sum | 4 | 44 | 0.92 [0.75, 1.00] / 0.94 / 0.95 | hash map (1.00, 1.00) | -0.40 | sort and two pointers (-15.5) | 0.67 | sort and two pointers / brute force | hash map (0.96) | frozen |
| find duplicate | 5 | 54 | 1.00 [1.00, 1.00] / 1.00 / 1.00 | hash set (1.00, 1.00) | 0.02 | sort, adjacent check (-12.4) | 1.02 | Floyd cycle detection / sort, adjacent check | hash set (0.43) | frozen |
| top-k frequent | 4 | 38 | 0.84 [0.60, 1.00] / 0.88 / 0.91 | sort by count (1.00, 0.94) | -0.10 | bucket sort (-15.4) | 0.91 | heap / heap | heap (0.64) | frozen |
| connected components | 4 | 57 | 1.00 [1.00, 1.00] / 1.00 / 1.00 | union-find (1.00, 1.00) | -0.15 | DFS (-21.8) | 0.86 | DFS / label propagation | union-find (0.77) | frozen |
| Fibonacci | 4 | 36 | 0.85 [0.65, 1.00] / 0.89 / 0.91 | iteration (1.00, 1.00) | -0.02 | fast doubling (-11.4) | 0.98 | matrix power / fast doubling | matrix power (0.79) | frozen |
| substring search | 6 | 58 | 0.95 [0.82, 1.00] / 0.96 / 1.00 | naive (1.00, 1.00) | 0.24 | KMP (-14.3) | 1.28 | KMP / Boyer-Moore-Horspool | naive (0.53) | frozen |
| longest increasing subsequence | 3 | 57 | 1.00 [1.00, 1.00] / 1.00 / 1.00 | quadratic DP (1.00, 1.00) | -0.86 | patience sorting with bisect (-14.4) | 0.42 | patience sorting / patience sorting | quadratic DP (0.90) | frozen |
| merge intervals | 3 | 59 | 1.00 [1.00, 1.00] / 1.00 / 0.95 | sort and sweep (1.00, 1.00) | 0.74 | union-find (-35.5) | 2.09 | interval tree / union-find | sort and sweep (1.00) | frozen |
| non-overlapping intervals | 4 | 53 | 0.89 [0.63, 1.00] / 0.94 / 0.91 | greedy by end (1.00, 1.00) | -0.83 | DP with bisect (-28.1) | 0.44 | DP with bisect / DAG longest path | greedy by end (0.56) | frozen |
| cycle detection | 4 | 59 | 0.92 [0.73, 1.00] / 0.94 / 0.95 | DFS with parent (1.00, 0.92) | 2.39 | union-find (-14.2) | 10.9 | union-find / union-find | DFS with parent (0.59) | excluded (13th gated; 12-task cap) |
| topological order | 4 | 53 | 1.00 [1.00, 1.00] / 1.00 / 0.95 | Kahn (1.00, 1.00) | 2.44 | DFS post-order (-27.2) | 11.4 | DFS post-order / source removal | Kahn (0.98) | frozen |
| first and last position | 3 | 56 | 0.90 [0.61, 1.00] / 0.93 / 0.95 | binary search (0.98, 0.98) | 0.80 | bisect module (-12.6) | 2.21 | bisect module / exponential search | binary search (1.00) | frozen |

**Qwen3-8B is fully collapsed on all 13 tasks.** The modal share is 50 of 50 everywhere except first and last position (49 of 50), Wilson [0.929, 1.0], and the correctness-conditioned Hill number is 1.0 on every task. No task has a minor algorithm at 10% or more, although the presence check is weak at N = 50 (a true share of 0.10 reaches 5 of 50 with probability about 0.57). The pilot pass rate is at least 0.92 on every task. The collapse is specific to the model: Llama-3.1-8B-Instruct, run with the same specifications and decoding, splits over several algorithms on k-th smallest (heapify and pop 0.34, size-k heap, full sort and quickselect), substring search (naive 0.53) and find duplicate (hash set 0.43), and passes far fewer tests. The presence pilot therefore removes the present-minor stratum for Qwen3-8B on every candidate task: confirmation on this bench must rest on likelihood matrices and on modal bans for Qwen3-8B, and Llama is where sampled present-minor bans exist.

**Labeller, likelihoods and nominations.** All 13 tasks passed the labeller gate, 11 at round 0 and two (k-th smallest, merge intervals) after one revision round with a fresh holdout (5 of 6 and 6 of 6). Both labellers got all 54 references right; runtime and AST labels agreed on 0.91 of 3,230 Qwen attempts, and the judge was needed on 8.4%. The baseline likelihood's argmax equals the pilot mode on 13 of 13 tasks, its log score beats uniform on every task (for example -0.06 against -1.61 on two-sum), and the sum of exp(likelihood) lies in [0.3, 3] on 11 of 13 (cycle detection and topological order overshoot, an importance-sampling overestimate under low ESS). Of the 54 cells, 34 have Kish ESS below 5. One cell stands out: quickselect on k-th smallest has likelihood -1.5 (about 0.21 latent mass) while the pilot drew it 0 of 50 times. The free-form association answers are close to deterministic (the alternative to a full sort is quickselect 20 of 20 times); proximity nominates a different algorithm from association on 10 of 13 modal events; and under total collapse the sampled ladder ties over all survivors. The order re-computed after the likelihoods (Stage B) agrees with Stage A at Kendall tau 0.54. Forced adherence limits the exotic algorithms: 45 of 54 have adherence of at least 0.5, and the lowest are topological layering (0.04) and source removal (0.10), the interval tree (0.24), the DP variants of non-overlapping intervals (0.28), index marking (0.28) and label propagation (0.29).

**Deviations and what was not done.** Scoring used vLLM prompt log-probabilities instead of HF; single-request and batched scoring disagreed by 0.62 nats on 1 of 5 checked programs (the others within 0.015). The forced proposal used five paraphrases over eight rounds instead of ten over four. Not produced: the unscrubbed scoring sensitivity that the likelihood screen recommended, Llama forced programs and likelihoods, ban, mention and neutral likelihood matrices, and any sampled ban event. Cost: about 1.4 GPU-hours on one RTX 2000 Ada and USD 0.14 of judge calls (1,124 calls).

## 2.9 Readout experiment: the ban inside the model

**Why.** The request asks for internals read with sparse autoencoders, thought anchors and lenses, and for the literal "always same seed" test of temperature. This experiment [ARTIFACT:art_3iv5G76C3yoX] ran those readouts on the modal bans of the two path search tasks, each beside a matched baseline on identical rows and folds. Everything in it is descriptive.

**A fresh ban pool.** Under protocol v2 (five templates by 20 samples per task), the banned share was 0.15 on the grid task (Wilson [0.09, 0.23]) and 0.13 on the shortest path task ([0.08, 0.21]); both events pass the gate. On the grid task the not-allowed template gave BFS 15 of 20 times and every other template 0 of 20, the third independent draw in which that one template fails (Sections 2.5 and 2.6).

**The SAE transfer test failed.** The sparse autoencoders used were Qwen-Scope's, trained on Qwen3-8B-Base and covering all 36 layers [{{Deng2026}}] (64K latents, top-k activation with k = 50 [{{Gao2024}}]). Before using them on the instruct model, the experiment spliced their reconstructions into the residual stream at layers 15, 20 and 27 and compared the increase in cross-entropy over 200 instruct-model sequences with the increase on the base model; the preregistered bar was a ratio of at most 1.5. It failed at all three layers (Table 74). Reconstruction error was similar in the two models, but the instruct model's clean cross-entropy on its own code is far lower (0.030 against 0.260 nats), so the same error costs more. Every latent result below is labelled as computed on out-of-distribution activations, and the difference-in-means baselines lead.

**Table 74.** SAE transfer test: increase in cross-entropy when SAE reconstructions are spliced in (source: `results/transfer_summary.json`; ratio intervals 95%).

| Layer | Increase, instruct | Increase, base | Ratio [95% CI] | Pass (ratio at most 1.5) | Relative MSE instruct / base | Fraction of variance unexplained instruct / base | Cosine instruct / base |
|-|-|-|-|-|-|-|-|
| 15 | 0.173 | 0.053 | 3.29 [3.14, 3.45] | no | 0.196 / 0.165 | 0.366 / 0.288 | 0.896 / 0.914 |
| 20 | 0.150 | 0.077 | 1.95 [1.84, 2.06] | no | 0.230 / 0.203 | 0.094 / 0.243 | 0.877 / 0.893 |
| 27 | 0.097 | 0.061 | 1.59 [1.50, 1.67] | no | 0.229 / 0.197 | 0.153 / 0.325 | 0.877 / 0.896 |

**Readouts of the algorithm written.** On the forking token experiment's saved states, with nested leave-one-paraphrase-out selection, 200 within-paraphrase permutations and a maximum-statistic null, the shortest path contrast (Dijkstra against Bellman-Ford/SPFA, same prompts) is decodable at the token before the commit token and at token 16 by every method, with within-paraphrase held-out AUC 0.67 to 0.86 and permutation p at most 0.025 (Table 75). The grid contrast (BFS against DFS) is not decodable within paraphrase at the commitment point: most p-values exceed 0.05, no latent passes the maximum-statistic null, and only 57 within-paraphrase pairs exist. SAE latents never beat the difference-in-means direction or the top raw dimensions by a margin outside the intervals, which matches AxBench [{{Wu2025}}] and the MIB benchmark [{{Mueller2025}}]. The positive control was weak (within-paraphrase AUC at the token after the commit token peaks at 0.75 on the grid task and 0.79 on the shortest path task), because the commit token is the ` deque` import for most programs of both classes (DFS 55 of 78, Bellman-Ford/SPFA 78 of 80), so "the state at the commit token" means the state at the first lexicon match, not at the algorithm decision. The read position, identical within a paraphrase, gave within-paraphrase AUC of 0.37 to 0.62, as it must.

**Table 75.** Within-paraphrase held-out AUC of each readout of the algorithm written (permutation p in brackets; source: `results/readout_i_discovery.json`). DiM is the difference-in-means direction on raw states.

| Task, layer, position | Top-1 SAE latent | Top-20 SAE latents (logistic) | DiM | Raw logistic probe | Top-1 neuron | Top-20 neurons (logistic) | DiM on SAE codes |
|-|-|-|-|-|-|-|-|
| Grid, 15, before commit | 0.482 (0.881) | 0.588 (0.234) | 0.614 (0.199) | 0.596 (0.184) | 0.535 (0.388) | 0.570 (0.343) | 0.596 (0.249) |
| Grid, 15, token 16 | 0.640 (0.114) | 0.693 (0.040) | 0.544 (0.308) | 0.649 (0.114) | 0.588 (0.149) | 0.518 (0.483) | 0.649 (0.075) |
| Grid, 20, before commit | 0.570 (0.284) | 0.649 (0.124) | 0.719 (0.025) | 0.544 (0.378) | 0.640 (0.060) | 0.649 (0.080) | 0.535 (0.388) |
| Grid, 20, token 16 | 0.640 (0.065) | 0.675 (0.030) | 0.456 (0.682) | 0.667 (0.060) | 0.658 (0.100) | 0.491 (0.527) | 0.518 (0.448) |
| Grid, 27, before commit | 0.535 (0.308) | 0.649 (0.090) | 0.614 (0.179) | 0.526 (0.378) | 0.535 (0.284) | 0.579 (0.244) | 0.711 (0.020) |
| Grid, 27, token 16 | 0.640 (0.124) | 0.588 (0.279) | 0.684 (0.065) | 0.579 (0.294) | 0.675 (0.070) | 0.596 (0.229) | 0.684 (0.075) |
| Shortest path, 15, before commit | 0.761 (0.005) | 0.676 (0.015) | 0.768 (0.005) | 0.778 (0.005) | 0.782 (0.005) | 0.771 (0.005) | 0.757 (0.005) |
| Shortest path, 15, forking token | 0.613 (0.030) | 0.634 (0.025) | 0.553 (0.229) | 0.609 (0.144) | 0.581 (0.119) | 0.683 (0.010) | 0.630 (0.020) |
| Shortest path, 15, token 16 | 0.856 (0.005) | 0.845 (0.005) | 0.856 (0.005) | 0.852 (0.005) | 0.863 (0.005) | 0.856 (0.005) | 0.838 (0.005) |
| Shortest path, 20, before commit | 0.732 (0.005) | 0.665 (0.025) | 0.736 (0.005) | 0.792 (0.005) | 0.810 (0.005) | 0.746 (0.005) | 0.708 (0.005) |
| Shortest path, 20, forking token | 0.697 (0.005) | 0.616 (0.095) | 0.606 (0.104) | 0.581 (0.139) | 0.581 (0.169) | 0.570 (0.219) | 0.708 (0.005) |
| Shortest path, 20, token 16 | 0.863 (0.005) | 0.845 (0.005) | 0.810 (0.005) | 0.817 (0.005) | 0.835 (0.005) | 0.845 (0.005) | 0.856 (0.005) |
| Shortest path, 27, before commit | 0.789 (0.005) | 0.725 (0.005) | 0.764 (0.005) | 0.694 (0.005) | 0.711 (0.005) | 0.789 (0.005) | 0.764 (0.005) |
| Shortest path, 27, forking token | 0.574 (0.095) | 0.560 (0.249) | 0.641 (0.025) | 0.694 (0.020) | 0.623 (0.060) | 0.697 (0.005) | 0.676 (0.005) |
| Shortest path, 27, token 16 | 0.856 (0.005) | 0.803 (0.005) | 0.810 (0.005) | 0.838 (0.005) | 0.827 (0.005) | 0.806 (0.005) | 0.824 (0.005) |

Applied without refitting to the fresh pool's states at the token before the commit token, the difference-in-means direction transferred best. On the grid task its within-template AUC was 0.93, 0.97 and 1.00 at layers 15, 20 and 27, but only the not-allowed template produced both classes (15 BFS against 5 DFS, 75 pairs); the single top latent reached 0.27, 0.80 and 0.52. On the shortest path task the difference-in-means direction reached 0.66, 0.66 and 0.76 and the top-20-latent probe 0.65, 0.66 and 0.77. The top-20 latent lists overlapped above chance on the grid task (8 shared against 1.8 expected at layer 15) and at chance on the shortest path task, and shuffled labels gave AUC about 0.50.

**Attention to the ban.** The same three heads carry ban-specific attention on both tasks: layer 21 head 17, layer 26 head 21 and layer 26 head 25. From the query at the token before the commit token, head 21.17 sends 0.207 (grid) and 0.098 (shortest path) more of its attention mass to the ban segment than to the neutral segment of the token-matched twin, concentrated on the banned name's tokens (" breadth", "-first", "ijkstra"). On the grid task, runs that complied put more top-head attention on the ban than runs that did not (0.135 against 0.105, within-template permutation p = 0.0025); all non-compliant runs came from the not-allowed template, so this is a contrast within that template. The shortest path task shows no difference (p = 0.96). Attention weights are not a causal test, and the route experiment found the generated tokens' direct reads of the ban to matter only on the grid task.

**Prime and veto in the latents.** The preregistered pattern in which a forbidden concept is "activated in order to be suppressed" [{{Mann2025}}] appeared in none of the six task-by-layer configurations. The latents that fire on the banned algorithm's name were silent at the read position. At layer 27, both the name latents and the implementation latents of X were lower at the token before the commit token under the ban than under both twins for the same text (grid implementation latents 124 against 169 under the neutral twin; name latents 94 against 129 under the mention twin; implementation, ban against neutral, sign test p = 2e-24). The difference-in-means projection agreed in sign in only 2 of the 6 configurations, so most latent results here are flagged as not reproduced by the baseline.

**Thought anchors.** With thinking on and an 8,192-token cap, ten first-template ban traces were sampled (five per task), and four traces per task were resampled at nine sentence boundaries with six continuations each (432 continuations), following the thought-anchors method [{{Bogdan2025}}]. Grid traces think for 8.4k to 9.3k tokens and none completed within the cap, though 4 of 5 still emitted DFS code. In 4 of 4 resampled grid traces DFS was fixed at the first resample point (every continuation DFS from the first boundary on) and no anchor sentence exists; the traces open by restating the ban and naming DFS within four sentences ("The constraints say not to use BFS, so I can't use that approach. ... Maybe depth-first search (DFS)?"). Shortest path traces completed in 2.5k to 3.7k tokens (5 of 5) and showed one anchor among 32 sentences, a problem restatement. The early-label detector was valid on 13 of 16 checks (0.81).

**The same-seed test of temperature.** The request asked whether, with the seed held fixed, raising the temperature changes the idea or only the phrasing. Thirty seeds were run at T in {0.3, 0.7, 1.0, 1.3} with top-k = 10, for the baseline and the first-template ban on both tasks (480 rows), coupling samples by inverse-CDF sampling over the sorted top 10 tokens with one uniform stream per seed shared across temperatures. Under this coupling the idea never moved: the label changed against T = 0.3 in 0 of 30 seeds in 10 of 12 cells and in 1 of 30 in the other two, for same-seed and different-seed pairs alike (Table 76). With no idea-level variation left, the same-seed and different-seed agreement on ideas is identical. Phrasing (identifier-normalised AST 4-gram Jaccard below 0.8) changed less within a seed than across seeds, and the first token where a program diverged from its T = 0.3 twin fell at a median of 13 to 117 tokens. vLLM reproduced 5 of 8 rows byte for byte when rerun.

**Table 76.** Same-seed temperature test: rate of change against T = 0.3 for the same seed and for different seeds (30 seeds per cell; phrasing at Jaccard threshold 0.8; source: `results/same_seed.json`).

| Task | Condition | T | Idea change, same seed | Idea change, different seeds | Phrasing change, same seed | Phrasing change, different seeds | Median divergence token | Identical to T = 0.3 |
|-|-|-|-|-|-|-|-|-|
| Grid | baseline (all BFS) | 0.7 | 0/30 | 0.0 | 0.60 | 0.84 | 23 | 7 |
| Grid | baseline | 1.0 | 0/30 | 0.0 | 0.77 | 0.86 | 23 | 4 |
| Grid | baseline | 1.3 | 0/30 | 0.0 | 0.83 | 0.90 | 21 | 3 |
| Grid | ban (all DFS) | 0.7 | 0/30 | 0.0 | 0.87 | 0.94 | 27 | 3 |
| Grid | ban | 1.0 | 0/30 | 0.0 | 0.93 | 0.97 | 13 | 1 |
| Grid | ban | 1.3 | 0/30 | 0.0 | 1.00 | 1.00 | 13 | 0 |
| Shortest path | baseline (all Dijkstra) | 0.7 | 0/30 | 0.0 | 0.07 | 0.06 | 117 | 21 |
| Shortest path | baseline | 1.0 | 0/30 | 0.0 | 0.13 | 0.12 | 91 | 13 |
| Shortest path | baseline | 1.3 | 0/30 | 0.0 | 0.10 | 0.16 | 28 | 7 |
| Shortest path | ban (Bellman-Ford/SPFA) | 0.7 | 0/30 | 0.0 | 0.53 | 0.63 | 74 | 5 |
| Shortest path | ban | 1.0 | 1/30 | 0.033 | 0.59 | 0.68 | 28.5 | 2 |
| Shortest path | ban | 1.3 | 1/30 | 0.033 | 0.55 | 0.76 | 25 | 1 |

Across the four temperatures, each grid baseline seed produced 1.0 distinct idea and 2.37 phrasing clusters on average (3.17 under the ban), and each shortest path seed 1.0 idea and 1.13 phrasing clusters (1.03 ideas and 2.17 clusters under the ban). Under the ban the grid pass rate per temperature was 0.23, 0.57, 0.43 and 0.43: every program was DFS.

**Lenses: NLA and the j-lens.** A dated search in this experiment resolved the request's two unmapped terms. "NLA" denotes natural language autoencoders, an activation verbalizer and reconstructor trained jointly with reinforcement learning; released checkpoints cover Qwen2.5-7B-Instruct, two Gemma-3 models and Llama-3.3-70B-Instruct but not Qwen3-8B as of 2026-10-20, and training one is far outside a 16 GB budget, so NLA was not run. The "j-lens" is the Jacobian lens, which reads a layer's state through the unembedding after multiplying it by the mean Jacobian of the final state with respect to that layer. A community Jacobian lens for Qwen3-8B exists and was gated against the logit lens on 2,000 positions: its top-1 agreement with the model's own next token was below the logit lens at every source layer (layer 27: 0.104 against 0.291), so it failed and its readouts are descriptive only.

**Checks and cost.** The labeller re-check gave 0.965 on 141 gold programs. An independent script re-derived 69 headline numbers with no mismatch. Not run: a thinking-on same-seed arm, a Gumbel-max coupling sensitivity, NLA, an adaptive top-up and OpenRouter descriptions of latents. Cost: about 1.05 GPU-hours and USD 0.04 (112 judge calls).

