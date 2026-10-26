## 2.3 The audit: the iteration-1 record repaired, without new generation

The audit [ARTIFACT:art_V1MvbYs5420o] read the six iteration-1 experiments in place, generated nothing, made no LLM calls and spent nothing on OpenRouter. It ran first because several of this iteration's analyses depended on what it found: where the algorithm can be read out, whether the geometric neighbours survive resampling, and which iteration-1 events are informative at all. Every number it produced names its source file. Its own checks recomputed 40 numbers quoted in the plan and matched 38; the two mismatches are explained below (the count of gated events and the rarefied Hill number of the semantic seed). An independent script re-derived 20 headline numbers with no mismatch, a second one re-ran five headline tests, and every placebo failed as it should.

### 2.3.1 The locus probe that never ran

**Cause.** The forking token experiment's probe file is 28 bytes, an empty summary written at 18:29:22. Its state log records the start of the state phase at 18:31:55 and the grid and shortest path states saved at 18:34:34 and 18:34:50. The probe stage ran before its inputs existed and found an empty folder. The measurement was therefore a CPU job on files already on disk, not a missing experiment.

**Design.** The saved states hold 300 generations per task (200 baseline, 100 under the modal ban) at eight positions (the read position, generated tokens 8, 16, 32 and 64, and the tokens before, at and after the first algorithm-identifying token, which we call the commit token) and at layers 8 to 28. Within one ban prompt the model wrote BFS 21 times and DFS 78 times on the grid task (one unit weight Dijkstra) and Dijkstra 20 times and Bellman-Ford/SPFA 80 times on the shortest path task. These within-ban contrasts are the natural-run internals the request asks for: same prompts, different algorithms written. The probes are L2-regularised logistic regression probes with leave-one-paraphrase-out folds, which is the honest test because the read position is identical within a paraphrase. Each probe is compared with 200 refits on globally shuffled labels and 200 refits on labels shuffled within paraphrase (the null for "knows more than the paraphrase's base rate"), with a family-wise null over layers. A written-text control fits the same probe to features of the text written so far. A batched solver was unit-tested against scikit-learn (identical predictions; largest relative coefficient difference 3.9e-5). The preregistered rule moves the locus to the first generated position whose decoder beats the read position by at least 20 points of balanced accuracy and beats both nulls; a pre-commit qualifier asks whether the state carries more than the written text.

**Table 41.** Within-ban decoder of the algorithm written (grid: BFS against DFS; shortest path: Dijkstra against Bellman-Ford/SPFA), balanced accuracy at the best layer per position, with the read-position accuracy at that layer, both nulls and the written-text control (source: `results/locus.json`).

| Task | Position (median token) | Best layer | Balanced accuracy | Read position at that layer | Difference [95% CI] | Global null p95 | Within-paraphrase null p95 | Text control | Passes rule |
|-|-|-|-|-|-|-|-|-|-|
| Grid | read position | 16 | 0.855 | n/a | n/a | n/a | n/a | 0.5 | n/a |
| Grid | before commit token (6) | 20 | 0.855 | 0.791 | +0.064 [0.0, 0.201] | 0.639 | 0.855 | 0.673 | no |
| Grid | after commit token (7) | 23 | 0.855 | 0.791 | +0.064 [0.0, 0.201] | 0.652 | 0.855 | 0.673 | no |
| Grid | token 8 | 26 | 0.855 | 0.791 | +0.064 [0.0, 0.201] | 0.659 | 0.855 | 0.673 | no |
| Grid | token 16 | 9 | 0.798 | 0.402 | +0.396 [-0.065, 0.537] | 0.658 | 0.879 | 0.673 | no |
| Grid | token 32 | 23 | 0.798 | 0.791 | +0.006 [-0.16, 0.229] | 0.653 | 0.850 | 0.542 | no |
| Grid | token 64 | 27 | 0.739 | 0.791 | -0.052 [-0.203, 0.239] | 0.657 | 0.812 | 0.598 | no |
| Shortest path | read position | 13 | 0.625 | n/a | n/a | n/a | n/a | 0.5 | n/a |
| Shortest path | before commit token (6) | 8 | 0.762 | 0.481 | +0.281 [0.145, 0.388] | 0.669 | 0.681 | 0.756 | yes (mechanical) |
| Shortest path | forking token (7) | 17 | 0.731 | 0.550 | +0.181 [0.046, 0.261] | 0.650 | 0.644 | 0.675 | no |
| Shortest path | after commit token (7) | 10 | 0.762 | 0.456 | +0.306 [0.12, 0.463] | 0.656 | 0.675 | 0.762 | yes |
| Shortest path | token 8 | 8 | 0.831 | 0.481 | +0.350 [0.182, 0.525] | 0.663 | 0.682 | 0.831 | yes |
| Shortest path | token 16 | 8 | 0.837 | 0.481 | +0.356 [0.193, 0.525] | 0.650 | 0.650 | 0.837 | yes |
| Shortest path | token 32 | 15 | 0.837 | 0.550 | +0.287 [0.122, 0.399] | 0.675 | 0.669 | 0.831 | yes |
| Shortest path | token 64 | 8 | 0.831 | 0.481 | +0.350 [0.182, 0.525] | 0.669 | 0.662 | 0.819 | yes |

[FIGURE:fig_locus_text]

**What the locus probe showed.** On the grid task no position passes the rule, so the mechanical locus stays at the read position. The read position already separates the prompts that will produce DFS from those that will produce BFS (balanced accuracy 0.855 at layer 16), but at every generated position the within-paraphrase null reaches the observed accuracy: the signal is the paraphrase's base rate, not anything specific to a sample. BFS and DFS programs also share their commit token (`' deque'`; 51 of 78 DFS programs and all 21 BFS programs commit at token 6), so the commit index does not separate the classes on this task. On the shortest path task the first passing position is the token before the commit token (layer 8, +0.281 over the read position, within-paraphrase p = 0.005; a second implementation with 40 scikit-learn refits gave p = 0.024 against a placebo p of 0.17). The written-text control reaches 0.756 at the same position, so the state adds 0.006 over the text, below the preregistered 0.10 margin. The audit therefore qualified the shortest path locus as a post-commit readout. The text separates the classes from generated token 4 on: Dijkstra programs write `import heapq` and Bellman-Ford/SPFA programs write `from collections import deque`. The deciding token is generated token 3, emitted from states at tokens 1 to 3 that were never saved, and the forking token experiment had independently confirmed a forking token at that index (`import`, total variation 0.80; Table 19). The first token at which the text alone reaches 0.8 is token 8. No decision locus was found on either task.

Three further readings came out of the same states. The difference-in-means direction at the token before the commit token has held-out AUC 0.882 (grid) and 0.749 (shortest path), below the 0.9 bar that would reopen a generation-time removal. Per paraphrase, the read-position probe's held-out probability of the substitute tracks the share of the substitute that paraphrase produced (Spearman 0.63, exact p = 0.056, grid; 0.65, p = 0.045, shortest path; ten paraphrases each), a first sign that the read position knows how strongly a wording will be obeyed. The positive controls (baseline against ban states) were decoded at balanced accuracy close to 1.0.

### 2.3.2 Geometry under paraphrase resampling

The geometry experiment's stability figure of 0.985 came from resampling points on a fixed graph, which the hypothesis review had warned is uninformative. The audit rebuilt the principal component projection, the k-nearest-neighbour graph and the centroids on 1,000 paraphrase-level subsamples, for k in {5, 10, 15, 20} at every layer of the two gate bands (24 to 28 grid, 21 to 27 shortest path), after reproducing the committed distance matrices exactly (largest absolute difference 0.0000). Table 42 gives the k = 10 column.

**Table 42.** Nearest surviving centroid to the default algorithm under 1,000 paraphrase subsamples, k = 10 (source: `tables/geometry_stability.csv`; distances on full data).

| Task | Layer | P(DFS nearest) | P(unit weight Dijkstra nearest) | P(both are the two nearest) | Full-data order | MDS stress-1 |
|-|-|-|-|-|-|-|
| Grid | 24 | 0.523 | 0.477 | 1.0 | unit weight Dijkstra > DFS > A* > IDDFS > bidirectional BFS | 0.202 |
| Grid | 25 | 0.880 | 0.120 | 1.0 | DFS > unit weight Dijkstra > A* > IDDFS > bidirectional BFS | 0.212 |
| Grid | 26 | 0.954 | 0.046 | 1.0 | same | 0.213 |
| Grid | 27 | 1.0 | 0.0 | 1.0 | same | 0.217 |
| Grid | 28 | 1.0 | 0.0 | 1.0 | same | 0.230 |

| Task | Layer | P(Floyd-Warshall nearest) | P(Bellman-Ford/SPFA nearest) | P(Bellman-Ford/SPFA nearer than bidirectional Dijkstra) | Rank of Bellman-Ford/SPFA (full data) | Full-data order | MDS stress-1 |
|-|-|-|-|-|-|-|-|
| Shortest path | 21 | 1.0 | 0.0 | 0.555 | 3 | Floyd-Warshall > bidirectional Dijkstra > Bellman-Ford/SPFA > Dial | 0.205 |
| Shortest path | 22 | 1.0 | 0.0 | 0.633 | 3 | same | 0.239 |
| Shortest path | 23 | 1.0 | 0.0 | 0.829 | 2 | Floyd-Warshall > Bellman-Ford/SPFA > bidirectional Dijkstra > Dial | 0.235 |
| Shortest path | 24 | 1.0 | 0.0 | 0.820 | 2 | same | 0.224 |
| Shortest path | 25 | 1.0 | 0.0 | 0.810 | 2 | same | 0.226 |
| Shortest path | 26 | 1.0 | 0.0 | 0.897 | 2 | same | 0.227 |
| Shortest path | 27 | 1.0 | 0.0 | 0.964 | 2 | same | 0.229 |

Over all four values of k the picture is the same. On the shortest path task Floyd-Warshall is the nearest survivor to Dijkstra in 100% of subsamples at all 28 (layer, k) settings, and Bellman-Ford/SPFA, the algorithm every ban landed on, is never nearest; its full-data rank is 2 in 75% of settings and 3 in 25%. The geometry experiment's sensitivity matrix, which recomputes the two flagged centroids from correctly labelled forced samples only, puts bidirectional Dijkstra (40.91) closer to Dijkstra than Bellman-Ford/SPFA (42.18), with Floyd-Warshall at 25.49 and Dial at 58.01. On the grid task DFS is nearest to BFS at layers 25 to 28 (probability 0.87 to 1.00 over k) and unit weight Dijkstra overtakes it at layer 24 (DFS 0.52 to 0.60), while DFS and unit weight Dijkstra are always the two nearest. Neighbour orders agree across k and layer with mean Kendall tau 0.933 (grid) and 0.870 (shortest path). Centroids from name-masked prompts give different orders (grid top-1 stability 0.18 to 0.815). The grid ban's landing on DFS and unit weight Dijkstra is therefore consistent with geodesic proximity and with typicality, since both are also the model's runner-ups, and the two are not separated on these events. On the shortest path task geodesic proximity predicts the wrong substitute.

### 2.3.3 The substitute, draw by draw

The audit recomputed the modal-ban substitutes from the per-sample rows of every draw (Table 43). On the shortest path task the claim survives as written: all 272 compliant programs in the five draws were Bellman-Ford/SPFA. On the grid task DFS was the realised mode in four of five draws and took 116 of 128 compliant programs; in the geometry draw, the only one sampled with HF `generate` and the one with the highest banned share, 8 of 18 compliant programs were unit weight Dijkstra and the event had no clear mode.

**Table 43.** Compliant programs under the modal ban, per draw (source: `corrections.json`; Wilson 95% intervals for the substitute's share).

| Draw (engine) | Grid: DFS / compliant | Other compliant labels | DFS share [95%] | Shortest path: Bellman-Ford/SPFA / compliant | Share [95%] |
|-|-|-|-|-|-|
| Association (vLLM) | 38 / 38 | none | 1.0 [0.908, 1.000] | 86 / 86 | 1.0 [0.957, 1.000] |
| Geometry (HF) | 10 / 18 | unit weight Dijkstra 8 | 0.556 [0.337, 0.754] | 22 / 22 | 1.0 [0.851, 1.000] |
| Forking token (vLLM) | 40 / 41 | unit weight Dijkstra 1 | 0.976 [0.874, 0.996] | 80 / 80 | 1.0 [0.954, 1.000] |
| Decommitment (vLLM) | 16 / 18 | unit weight Dijkstra 2 | 0.889 [0.672, 0.969] | 38 / 38 | 1.0 [0.908, 1.000] |
| Instruction tuning (vLLM) | 12 / 13 | unit weight Dijkstra 1 | 0.923 [0.667, 0.986] | 46 / 46 | 1.0 [0.923, 1.000] |
| Pooled | 116 / 128 | unit weight Dijkstra 12 | 0.906 [0.843, 0.946]; draw-cluster bootstrap [0.75, 0.98] | 272 / 272 | 1.0 [0.986, 1.000] |

### 2.3.4 The cumulative ban of BFS and DFS does not replicate

The three draws that banned BFS and DFS together disagree on everything the knob table depends on (Table 44). The decommitment draw spread its 16 compliant programs over two algorithms, the geometry draw put all 18 on one, and in the association draw the model re-implemented a banned mechanism 94 times out of 100. The pairs the review quoted from Table 37 (0.88 / 1.00, 0.96 / 0.99, 0.53 / 0.933) are each draw's pass rate followed by its reference pass rate.

**Table 44.** The cumulative ban of BFS and DFS in three draws (source: `corrections.json#cumulative_bfs_dfs_ban`).

| Draw | N | Banned share (mechanism) | Pass rate | Compliant programs | Compliant composition |
|-|-|-|-|-|-|
| Decommitment | 100 | 0.81 | 0.88 | 16 | unit weight Dijkstra 13, A* 3 |
| Geometry | 50 | 0.62 | 0.96 | 18 | unit weight Dijkstra 18 |
| Association | 100 | 0.94 | 0.53 | 5 | unit weight Dijkstra 4, A* 1 |

### 2.3.5 Every perturbation, side by side: the generic-perturbation rival

The audit assembled one table of every condition in the six draws: 249 condition rows covering 20,270 programs, each with its pass cost against its own reference (Newcombe intervals [{{Newcombe1998}}]), the label composition among correct and among attempted programs, and the runner-up's share with a Wilson interval (`tables/perturbation_table.csv`). Tables 45 and 46 give the rows that bear on the generic-perturbation rival. On the shortest path task every non-semantic perturbation that produced at least 10 correct non-Dijkstra programs (8 of 8 such rows) had Bellman-Ford/SPFA as their majority, random directions included, and so did 3 of 4 semantic ones. Band random direction 2 of the instruction tuning experiment turned all 33 of its correct programs into Bellman-Ford/SPFA, against Dijkstra 100 of 100 in its control. On the grid task generic perturbations almost never left BFS: random directions broke programs (pass rates 0.41 and 0.68) but every correct program stayed BFS, and only two non-ban rows with at least 10 correct non-default programs exist, both mention twins (A* and DFS). On the shortest path task a ban and an arbitrary perturbation end in the same place; on the grid task only the ban reaches DFS at scale.

**Table 45.** Shortest path perturbations: label composition of correct programs and Bellman-Ford/SPFA share (source: `tables/perturbation_table.csv`).

| Draw | Perturbation | N | Pass (reference) | Correct programs | Bellman-Ford/SPFA share [95%] |
|-|-|-|-|-|-|
| Decommitment | random direction 1, c = 0.25 | 100 | 0.79 (0.95) | Dijkstra 53, Bellman-Ford/SPFA 26 | 0.329 [0.236, 0.439] |
| Decommitment | random direction 2, c = 0.25 | 100 | 0.87 (0.95) | Dijkstra 82, Bellman-Ford/SPFA 5 | 0.057 [0.025, 0.128] |
| Decommitment | decommitment direction, c = 0.25 | 100 | 0.78 (0.95) | Bellman-Ford/SPFA 54, Dijkstra 23, other 1 | 0.692 [0.583, 0.784] |
| Decommitment | decommitment direction, c = 0.375 | 100 | 0.67 (0.95) | Bellman-Ford/SPFA 47, Dijkstra 19, other 1 | 0.701 [0.583, 0.798] |
| Decommitment | decommitment direction, c = 0.5 | 100 | 0.37 (0.95) | Dijkstra 25, Bellman-Ford/SPFA 10, other 2 | 0.270 [0.154, 0.430] |
| Decommitment | breadth direction, c = 0.25 | 100 | 0.60 (0.95) | Bellman-Ford/SPFA 31, Dijkstra 28, Dial 1 | 0.516 [0.393, 0.638] |
| Decommitment | other task's direction, c = 0.25 | 50 | 0.72 (0.95) | Bellman-Ford/SPFA 28, Dijkstra 8 | 0.777 [0.619, 0.883] |
| Decommitment | variable-name placebo, c = 0.25 | 100 | 0.66 (0.95) | Dijkstra 60, Dial 3, Bellman-Ford/SPFA 2, other 1 | 0.030 [0.008, 0.104] |
| Decommitment | enumeration prompt | 100 | 0.82 (0.885) | Dijkstra 80, Bellman-Ford/SPFA 2 | 0.024 [0.007, 0.085] |
| Instruction tuning | band random direction 1 | 100 | 0.00 (1.00) | none | n/a |
| Instruction tuning | band random direction 2 | 100 | 0.33 (1.00) | Bellman-Ford/SPFA 33 | 1.0 [0.896, 1.000] |
| Instruction tuning | random direction 1, read position only, c = 1.0 | 100 | 1.00 (1.00) | Dijkstra 90, Bellman-Ford/SPFA 9, other 1 | 0.090 [0.048, 0.162] |
| Instruction tuning | sharpening subtraction, layer 18, c = 0.5 | 50 | 0.98 (1.00) | Dijkstra 48, Bellman-Ford/SPFA 1 | 0.020 [0.004, 0.107] |
| Instruction tuning | sharpening subtraction, read position only, no cutoff | 20 | 0.20 (1.00) | Dijkstra 3, Bellman-Ford/SPFA 1 | 0.25 [0.046, 0.699] |
| Instruction tuning | base model, chat template | 300 | 0.30 (1.00) | Dijkstra 63, Bellman-Ford/SPFA 24, other 2, Floyd-Warshall 1 | 0.266 [0.186, 0.366] |
| Instruction tuning | base model, plain completion | 300 | 0.083 (1.00) | Bellman-Ford/SPFA 16, Dijkstra 8, Floyd-Warshall 1 | 0.64 [0.445, 0.798] |
| Instruction tuning | instruct model, plain completion | 100 | 0.72 (1.00) | Dijkstra 57, Floyd-Warshall 8, Bellman-Ford/SPFA 7 | 0.097 [0.048, 0.187] |
| Decoding | semantic seed | 100 | 0.92 (0.99) | Bellman-Ford/SPFA 61, Dijkstra 30, Floyd-Warshall 1 | 0.663 [0.562, 0.751] |
| Decoding | novelty instruction | 100 | 0.96 (0.99) | Dijkstra 82, Bellman-Ford/SPFA 14 | 0.145 [0.089, 0.230] |
| Decoding | new algorithm instruction | 100 | 0.94 (0.99) | Dijkstra 90, Bellman-Ford/SPFA 4 | 0.042 [0.017, 0.104] |
| Decoding | enumeration prompt | 100 | 0.75 (0.99) | Dijkstra 67, Bellman-Ford/SPFA 8 | 0.106 [0.055, 0.197] |
| Decoding | T = 1.3, top-k = 10 | 100 | 1.00 (0.98) | Dijkstra 99, Bellman-Ford/SPFA 1 | 0.010 [0.002, 0.054] |
| Association | listing control | 100 | 1.00 (1.00) | Dijkstra 97, Bellman-Ford/SPFA 3 | 0.030 [0.010, 0.085] |
| Association | sham ban of Floyd-Warshall | 100 | 0.71 (1.00) | Dijkstra 68, Bellman-Ford/SPFA 3 | 0.042 [0.014, 0.117] |
| All five draws | modal ban of Dijkstra, pooled | 500 | 0.87 to 1.00 | Bellman-Ford/SPFA 272 (compliant) | 1.0 [0.986, 1.000] |

The sham ban of Floyd-Warshall shows why compliant and attempted programs must be told apart: 23 of its 100 attempted programs were Bellman-Ford/SPFA (Table 8), but only 3 of those passed the tests.

**Table 46.** Grid perturbations: label composition of correct programs and DFS share (source: `tables/perturbation_table.csv`).

| Draw | Perturbation | N | Pass (reference) | Correct programs | DFS share [95%] |
|-|-|-|-|-|-|
| Instruction tuning | band random direction 1 | 100 | 0.41 (1.00) | BFS 41 | 0.0 [0.000, 0.086] |
| Instruction tuning | band random direction 2 | 100 | 0.68 (1.00) | BFS 68 | 0.0 [0.000, 0.053] |
| Instruction tuning | random direction 1, read position only, c = 1.0 | 100 | 1.00 (1.00) | BFS 100 | 0.0 [0.000, 0.037] |
| Decommitment | decommitment direction, c = 0.25 | 100 | 0.57 (1.00) | BFS 57 | 0.0 [0.000, 0.063] |
| Decoding | semantic seed | 100 | 0.93 (0.97) | BFS 91, bidirectional BFS 2 | 0.0 [0.000, 0.040] |
| Decoding | novelty instruction | 100 | 0.85 (0.97) | BFS 81, unit weight Dijkstra 2, DFS 1, A* 1 | 0.011 [0.002, 0.064] |
| Decoding | new algorithm instruction | 100 | 0.94 (0.97) | BFS 92, DFS 2 | 0.021 [0.006, 0.074] |
| Decoding | enumeration prompt | 100 | 0.99 (0.97) | BFS 99 | 0.0 [0.000, 0.037] |
| Decoding | T = 1.3, top-k = 10 | 100 | 0.95 (0.98) | BFS 94, DFS 1 | 0.010 [0.002, 0.057] |
| Instruction tuning | base model, chat template | 300 | 0.19 (1.00) | BFS 49, DFS 7, A* 1 | 0.122 [0.061, 0.232] |
| Instruction tuning | base model, plain completion | 300 | 0.05 (1.00) | BFS 12, DFS 3 | 0.20 [0.070, 0.452] |
| Instruction tuning | instruct model, plain completion | 100 | 0.73 (1.00) | BFS 73 | 0.0 [0.000, 0.050] |
| Association | listing control | 100 | 0.92 (0.933) | BFS 92 | 0.0 [0.000, 0.040] |
| Association | sham ban of IDDFS | 100 | 0.80 (0.933) | BFS 76, DFS 4 | 0.05 [0.020, 0.122] |
| Association | sham ban of unit weight Dijkstra | 100 | 0.71 (0.933) | BFS 69, DFS 2 | 0.028 [0.008, 0.097] |
| All five draws | modal ban of BFS, pooled | 500 | 0.46 to 0.76 | DFS 116, unit weight Dijkstra 12 (compliant) | 0.906 [0.843, 0.946] |

### 2.3.6 The knob table on one statistic

The iteration-1 knob table mixed plug-in Hill numbers, rarefied differences, and Hill numbers that counted correct programs of the banned algorithm. The audit recomputed every knob with one statistic: the Hill number of order 1 [{{Hill1973}}] over compliant programs only (banned labels excluded), rarefied to a common depth of 25 by 1,000 draws without replacement, with a 90% interval from 1,000 paraphrase-cluster bootstrap resamples times 200 rarefaction draws; cells with fewer than 25 compliant programs are marked and never extrapolated. Pass points are measured against each condition's own reference. Generate then select is a ceiling row, because its diversity comes from an external random choice among model-proposed approaches, which is the mechanism of SimpleStrat [{{Wong2024}}]. Table 47 gives the rows that matter (all 183 rows are in `tables/knob_table.csv`).

**Table 47.** One-statistic knob table: rarefied Hill-1 over compliant programs at depth 25 (source: `tables/knob_table.csv`).

| Task | Knob (draw) | Class | Compliant programs | Composition | Hill-1 [90% CI] | Pass points lost |
|-|-|-|-|-|-|-|
| Grid | generate then select (decoding) | ceiling | 55 | BFS 26, A* 14, unit weight Dijkstra 9, DFS 6 | 3.358 [3.315, 3.381] | 42.0 |
| Grid | mention of A* (association) | named-mode cue | 41 | A* 24, BFS 11, unit weight Dijkstra 5, DFS 1 | 2.687 [1.861, 3.186] | 11.3 |
| Grid | base model, chat template (instruction tuning) | model swap | 57 | BFS 49, DFS 7, A* 1 | 1.549 [1.284, 1.814] | 81.0 |
| Grid | modal ban, five draws pooled | ban | 128 | DFS 116, unit weight Dijkstra 12 | 1.357 [1.250, 1.425] | 34.3 |
| Grid | novelty instruction (decoding) | diversity knob | 85 | BFS 81, unit weight Dijkstra 2, DFS 1, A* 1 | 1.227 [1.096, 1.346] | 12.0 |
| Grid | sham ban of IDDFS (association) | ban | 80 | BFS 76, DFS 4 | 1.205 [1.0, 1.542] | 13.3 |
| Grid | sham ban of unit weight Dijkstra (association) | ban | 71 | BFS 69, DFS 2 | 1.119 [1.0, 1.245] | 22.3 |
| Grid | modal ban (forking token) | ban | 41 | DFS 40, unit weight Dijkstra 1 | 1.111 [1.0, 1.243] | 35.0 |
| Grid | semantic seed (decoding) | diversity knob | 93 | BFS 91, bidirectional BFS 2 | 1.096 [1.0, 1.191] | 4.0 |
| Grid | new algorithm instruction (decoding) | diversity knob | 94 | BFS 92, DFS 2 | 1.093 [1.0, 1.187] | 3.0 |
| Grid | T = 1.3, top-k = 10 (decoding) | diversity knob | 95 | BFS 94, DFS 1 | 1.048 [1.0, 1.133] | 3.0 |
| Grid | modal ban (association) | ban | 38 | DFS 38 | 1.0 [1.0, 1.0] | 47.3 |
| Grid | cumulative ban of BFS and DFS (decommitment) | ban | 16 | unit weight Dijkstra 13, A* 3 | below depth (plug-in 1.620) | 12.0 |
| Grid | cumulative ban of BFS and DFS (geometry) | ban | 18 | unit weight Dijkstra 18 | below depth (plug-in 1.0) | 3.0 |
| Grid | cumulative ban of BFS and DFS (association) | ban | 5 | unit weight Dijkstra 4, A* 1 | below depth (plug-in 1.649) | 40.3 |
| Grid | every steering, removal, forking-window, random-seed and remaining temperature arm | diversity knob | 3 to 307 | BFS only | 1.0, or below depth | 0 to 97 |
| Shortest path | generate then select (decoding) | ceiling | 75 | Bellman-Ford/SPFA 31, Dijkstra 29, Floyd-Warshall 15 | 2.802 [2.778, 2.812] | 24.0 |
| Shortest path | base model, plain completion (instruction tuning) | model swap | 25 | Bellman-Ford/SPFA 16, Dijkstra 8, Floyd-Warshall 1 | 2.179 [1.704, 2.611] | 91.7 |
| Shortest path | decommitment direction, c = 0.5 | diversity knob | 37 | Dijkstra 25, Bellman-Ford/SPFA 10, other 2 | 2.139 [1.553, 2.495] | 58.0 |
| Shortest path | breadth direction, c = 0.25 | diversity knob | 60 | Bellman-Ford/SPFA 31, Dijkstra 28, Dial 1 | 2.096 [1.920, 2.297] | 35.0 |
| Shortest path | base model, chat template | model swap | 90 | Dijkstra 63, Bellman-Ford/SPFA 24, other 2, Floyd-Warshall 1 | 2.018 [1.737, 2.262] | 70.0 |
| Shortest path | semantic seed (decoding) | diversity knob | 92 | Bellman-Ford/SPFA 61, Dijkstra 30, Floyd-Warshall 1 | 1.935 [1.534, 2.076] | 7.0 |
| Shortest path | decommitment direction, c = 0.25 | diversity knob | 78 | Bellman-Ford/SPFA 54, Dijkstra 23, other 1 | 1.911 [1.735, 2.069] | 17.0 |
| Shortest path | decommitment direction, c = 0.375 | diversity knob | 67 | Bellman-Ford/SPFA 47, Dijkstra 19, other 1 | 1.901 [1.675, 2.079] | 28.0 |
| Shortest path | random direction 1, c = 0.25 (decommitment) | diversity knob | 79 | Dijkstra 53, Bellman-Ford/SPFA 26 | 1.861 [1.657, 1.964] | 16.0 |
| Shortest path | random directions, four arms pooled | diversity knob | 199 | Dijkstra 135, Bellman-Ford/SPFA 64 | 1.851 [1.774, 1.903] | 47.75 |
| Shortest path | other task's direction, c = 0.25 | diversity knob | 36 | Bellman-Ford/SPFA 28, Dijkstra 8 | 1.688 [1.412, 1.857] | 23.0 |
| Shortest path | novelty instruction (decoding) | diversity knob | 96 | Dijkstra 82, Bellman-Ford/SPFA 14 | 1.500 [1.275, 1.692] | 3.0 |
| Shortest path | variable-name placebo, c = 0.25 | diversity knob | 66 | Dijkstra 60, Dial 3, Bellman-Ford/SPFA 2, other 1 | 1.451 [1.129, 1.829] | 29.0 |
| Shortest path | random direction 1, read position only (instruction tuning) | diversity knob | 100 | Dijkstra 90, Bellman-Ford/SPFA 9, other 1 | 1.393 [1.209, 1.593] | 0.0 |
| Shortest path | enumeration prompt (decoding) | diversity knob | 75 | Dijkstra 67, Bellman-Ford/SPFA 8 | 1.382 [1.217, 1.581] | 24.0 |
| Shortest path | random direction 2, c = 0.25 (decommitment) | diversity knob | 87 | Dijkstra 82, Bellman-Ford/SPFA 5 | 1.231 [1.097, 1.371] | 8.0 |
| Shortest path | modal ban, five draws pooled | ban | 272 | Bellman-Ford/SPFA 272 | 1.0 [1.0, 1.0] | 2.4 |

**The positive target and the BUY rule.** The strategy's positive target was a knob that buys a second correct algorithm, a Hill number of at least 2 within its own compliant output, at a cost below 20 pass points. Under the single statistic no diversity knob and no ban meets it on either task. The closest is the semantic seed on the shortest path task (1.935 at 7 points). The mention of A* on the grid task reaches 2.69 at 11 points, but a mention recommends a named algorithm, so it meets only the literal reading of the target. The modal ban, the knob that iteration 1 ranked first on the shortest path task, scores exactly 1.0 there once banned programs no longer count: it replaces Dijkstra with one algorithm. The BUY rule names a best knob only when its 90% interval separates from the next; on the grid task the top rows (novelty instruction 1.227 [1.096, 1.346], sham ban of IDDFS 1.205 [1.0, 1.542]) do not separate, and on the shortest path task neither do the top five (Table 47). No knob advances.

### 2.3.7 The forecast contest on gated events

The rule, quoted in full from the strategy, is that a forecasting family advances if its calibrated mean log score beats the next best family by at least 0.10 nats on at least three events where the families' top-1 nominations disagree, scored on informative events only: banned mode present at 10% or more of the latent baseline, compliance of at least 50% and at least two survivors. The hypothesis update fixed compliance in this rule to mean avoidance and added a floor of 20 attempted non-banned programs. Of the 64 events with forecasts in the iteration-1 record, 24 were sampled (Table 48). Three informative events pass the gate: the association draw's two modal bans and the decommitment draw's grid modal ban, whose forecasts are all tied. The gate as written also admits the association draw's nine sham bans (12 events in all), but they land on the default by construction and their own artifact marked them uninformative. The geometry, instruction tuning and decommitment shortest path events fail the gate under either compliance definition, and the forking token draw made no family forecasts. On the gated events the families' mean log scores are: association map (Borda) -0.844 (2 events), free-form association -0.145 (2), listing-control typicality -0.120 (2), sampled frequency -1.579 (3), decommitted distribution -1.674 (1) and uniform -1.674 (1). Only two gated events have disagreeing nominations, and the largest margin on them is 0.05 nats. No family can advance, so the iteration-1 ranking of forecasts in Table 36 rests largely on events the rule excludes.

**Table 48.** Every sampled iteration-1 event with forecasts, with both gates and the log scores of the main families (nats per attempted non-banned program; 5% uniform mixing and a 2% "other" floor for every family; top-1 nomination in brackets). Source: `results/tables.json#predict_gated`.

| Draw | Event | N | Attempted non-banned | Avoidance | Compliant share | Avoidance gate | Compliant gate | Log scores [top-1] |
|-|-|-|-|-|-|-|-|-|
| Association | grid ban A* (sham) | 100 | 100 | 1.0 | 0.72 | pass | pass | Borda -1.022 [BFS]; free-form -0.101 [BFS]; frequency -0.101 [BFS]; listing -0.131 [BFS] |
| Association | grid ban BFS (modal) | 100 | 90 | 0.90 | 0.38 | pass | fail | Borda -2.710 [unit weight Dijkstra]; free-form -0.152 [DFS]; frequency -1.630 [tie]; listing -0.101 [DFS] |
| Association | grid ban bidirectional BFS (sham) | 100 | 100 | 1.0 | 0.92 | pass | pass | Borda -1.063 [BFS]; free-form -1.141 [A*]; frequency -0.140 [BFS]; listing -0.169 [BFS] |
| Association | grid ban DFS (sham) | 100 | 96 | 0.96 | 0.86 | pass | pass | Borda -0.998; free-form -0.101; frequency -0.101; listing -0.101 [all BFS] |
| Association | grid ban unit weight Dijkstra (sham) | 100 | 100 | 1.0 | 0.71 | pass | pass | Borda -1.113; free-form -0.410; frequency -0.410; listing -0.368 [all BFS] |
| Association | grid ban IDDFS (sham) | 100 | 100 | 1.0 | 0.80 | pass | pass | Borda -1.114; free-form -0.511; frequency -0.564; listing -0.486 [all BFS] |
| Association | grid ban BFS and DFS | 100 | 6 | 0.06 | 0.05 | fail | fail | Borda -1.398 [bidirectional BFS]; others -1.406 [tie] |
| Association | shortest path ban Bellman-Ford/SPFA (sham) | 100 | 95 | 0.95 | 0.92 | pass | pass | Borda -0.926; free-form, frequency, listing -0.136 [all Dijkstra] |
| Association | shortest path ban bidirectional Dijkstra (sham) | 100 | 100 | 1.0 | 1.0 | pass | pass | Borda -0.791; free-form -0.205; frequency -0.205; listing -0.212 [Dijkstra] |
| Association | shortest path ban Dial (sham) | 100 | 100 | 1.0 | 0.97 | pass | pass | Borda -0.803; free-form -0.278; frequency -0.278; listing -0.269 [Dijkstra] |
| Association | shortest path ban Dijkstra (modal) | 100 | 91 | 0.91 | 0.86 | pass | pass | Borda -0.813 [Bellman-Ford/SPFA]; free-form -0.138 [Bellman-Ford/SPFA]; frequency -1.434 [tie]; listing -0.138 [Bellman-Ford/SPFA] |
| Association | shortest path ban Floyd-Warshall (sham) | 100 | 100 | 1.0 | 0.71 | pass | pass | Borda -0.911; free-form -0.933; frequency -0.933; listing -0.784 [Dijkstra] |
| Association | shortest path ban Dijkstra and Bellman-Ford/SPFA | 100 | 0 | 0.0 | 0.0 | fail | fail | not scorable |
| Geometry | grid ban BFS | 100 | 38 | 0.38 | 0.18 | fail | fail | association -3.543 [A*]; frequency -1.630 [tie]; geodesic -1.337 [DFS]; decoder -1.287 [DFS] |
| Geometry | grid ban BFS and DFS | 50 | 19 | 0.38 | 0.36 | fail | fail | association -0.998 [unit weight Dijkstra]; geodesic -1.073 [unit weight Dijkstra]; decoder -4.124 [IDDFS] |
| Geometry | grid ban BFS and unit weight Dijkstra | 50 | 17 | 0.34 | 0.10 | fail | fail | association -3.966 [A*]; geodesic -1.280 [A*]; decoder -1.372 [IDDFS] |
| Geometry | shortest path ban Dijkstra | 100 | 28 | 0.28 | 0.22 | fail | fail | association -1.647 [Dial]; frequency -1.496 [tie]; geodesic -1.530 [Floyd-Warshall]; decoder -1.587 [bidirectional Dijkstra] |
| Geometry | shortest path ban Dijkstra and Bellman-Ford/SPFA | 50 | 1 | 0.02 | 0.0 | fail | fail | all -3.912 |
| Decommitment | grid ban BFS | 100 | 51 | 0.51 | 0.18 | pass | fail | every family -1.674 [tie] |
| Decommitment | grid ban BFS and DFS | 100 | 19 | 0.19 | 0.16 | fail | fail | every family -1.538 [tie] |
| Decommitment | shortest path ban Dijkstra | 100 | 46 | 0.46 | 0.38 | fail | fail | decommitted -0.594 [Bellman-Ford/SPFA]; frequency (vLLM) -0.731 [Bellman-Ford/SPFA]; uniform -1.733 |
| Decommitment | shortest path ban Dijkstra and Bellman-Ford/SPFA | 100 | 17 | 0.17 | 0.01 | fail | fail | all -3.912 [tie] |
| Instruction tuning | grid ban BFS | 100 | 38 | 0.38 | 0.13 | fail | fail | base plain completion -0.430 [DFS]; base chat -0.304 [DFS]; instruct chat -1.630 [tie] |
| Instruction tuning | shortest path ban Dijkstra | 100 | 46 | 0.46 | 0.46 | fail | fail | base plain completion -0.255; base chat -0.096; instruct chat -0.096 [all Bellman-Ford/SPFA] |

These scores are computed over attempted non-banned programs, so they differ slightly from the compliant-only scores of Tables 7, 14 and 36.

### 2.3.8 Seeds at the read position: both halves of the dissociation

Iteration 1 reported that the grid semantic seed moved the read-position state toward its implied algorithm while the output barely moved. The other half was in the same file and was not reported (Table 49). On the shortest path task the semantic seed's displacement did not point toward the Bellman-Ford/SPFA centroid, yet the output moved two thirds of the way to it. The word seed moved the grid probe's decoded distribution toward A* by 0.88 with no change in behaviour. The entropy seed's interval on the shortest path task reaches 1.596, above the 1.5 equivalence bound, so its equivalence with paraphrase noise was not shown. Displacement along the mode subspace built from forced prompts predicted behavioural movement in neither direction.

**Table 49.** Read-position displacement against behavioural movement for the seeds (sources: decoding experiment `results/analysis.json`, audit `results/tables.json#seeds`; behaviour shifts with Newcombe 95% intervals).

| Task | Seed | Read-position evidence | Behaviour among correct programs | Behaviour among attempted programs |
|-|-|-|-|-|
| Grid | semantic (implies bidirectional search) | cosine 0.493 with the bidirectional BFS centroid | bidirectional BFS +2.15 points [-1.97, 7.51]; BFS -1.12 | bidirectional BFS +5.0 points [0.33, 11.18]; BFS -4.0 |
| Shortest path | semantic (implies relaxation over all edges) | cosine -0.087 with the Bellman-Ford/SPFA centroid | Bellman-Ford/SPFA +66.30 points [55.50, 75.14]; Dijkstra -67.39 | Bellman-Ford/SPFA +61.0 points [50.53, 69.98]; Dijkstra -62.0 |
| Grid | word | ratio 1.555 [1.309, 1.85] of paraphrase noise; probe-decoded shift +0.88 toward A* | BFS +1.03 points; no non-BFS program | BFS +1.0 point |
| Shortest path | entropy | ratio 1.165 [1.0, 1.596]; upper bound above the 1.5 bound | Dijkstra share unchanged | unchanged |

### 2.3.9 Sham bans as a weak test of negation-triggered promotion

The audit compared each survivor's share under each of the nine bans of absent algorithms with its share in the association draw's baseline (N = 300), and called a survivor promoted if it gained at least 10 points with Fisher p below 0.05. Two promotions passed: banning IDDFS raised DFS by 12 points (p = 3.5e-8) and banning Floyd-Warshall raised Bellman-Ford/SPFA by 23 points (p = 1.7e-15). Two smaller shifts fell below the cut: banning unit weight Dijkstra raised DFS by 8 points (p = 1.2e-5) and banning Dial raised Bellman-Ford/SPFA by 5 points (p = 0.0009). In both promotions the gaining algorithm is a content neighbour of the banned one and also the model's runner-up, so the test cannot say whether the negation promoted an associate or merely disturbed the default toward the ladder's next rung. Shuffling the condition labels gave no promotion, as it should.

### 2.3.10 Executed outputs missing from the iteration-1 record, and bookkeeping

**Forced conditions of the association experiment.** Table 6 was captioned as every condition, but the experiment also ran eleven forced-implementation conditions of 10 samples each (Table 50). They match the geometry experiment's manipulation check (Table 11): the model cannot write a passing IDDFS on the grid task or a Dial on the shortest path task, and asked for bidirectional Dijkstra it writes plain Dijkstra every time.

**Table 50.** Forced implementations in the association experiment (N = 10 each; labels of attempted programs; source: association experiment `data/samples.jsonl`, conditions `forced:*`).

| Task | Requested algorithm | Pass | Labels |
|-|-|-|-|
| Grid | A* | 10/10 | A* 9, unit weight Dijkstra 1 |
| Grid | BFS | 9/10 | BFS 10 |
| Grid | bidirectional BFS | 4/10 | BFS 5, bidirectional BFS 5 |
| Grid | DFS | 3/10 | DFS 10 |
| Grid | unit weight Dijkstra | 10/10 | unit weight Dijkstra 8, BFS 1, DFS 1 |
| Grid | IDDFS | 0/10 | IDDFS 10 |
| Shortest path | Bellman-Ford/SPFA | 10/10 | Bellman-Ford/SPFA 10 |
| Shortest path | bidirectional Dijkstra | 4/10 | Dijkstra 10 |
| Shortest path | Dial | 0/10 | other 5, Dial 4, Dijkstra 1 |
| Shortest path | Dijkstra | 10/10 | Dijkstra 10 |
| Shortest path | Floyd-Warshall | 10/10 | Floyd-Warshall 10 |

**Other executed outputs.** The association experiment's robustness block held an in-sample, sharpness-matched sensitivity that the report omitted: with one sharpening power per family fitted on the two events, the Borda association map scored -1.386 and sampled frequency -1.475, the first-rank map -0.888, the external Llama map -0.437, and the free-form answer and listing control both -0.059. These are in-sample numbers, not calibrated out-of-sample scores. In the forking token experiment, the next-token entropy at the 13 forking-token candidates averaged 0.527 bits (maximum 1.494) against 0.017 bits (maximum 0.130) at the 10 control positions. Its change point detector, tested on planted changes, caught a total variation change of 0.2, 0.3 and 0.5 at the right position in 82.5%, 95% and 99% of trials with a 6% false-positive rate, and the grid forking-token candidate on ban path 0 at token 9 confirms at a total variation threshold of 0.10 and 0.15 but not at the preregistered 0.20. Its engine test found greedy prefixes identical in only 14% of runs at 10 tokens and in all runs at 40 tokens. The decommitment experiment's arms at c = 1 in layers 14 and 22 passed 0 of 10 on both tasks. The geometry experiment's Procrustes disparity between the named and name-masked centroid sets was 0.18 (grid) and 0.25 (shortest path), and it dropped two preregistered components under its drop order: the external-model association elicitation and the leave-one-condition-out distribution decoder. In the decoding experiment's enumeration arm on the shortest path task, the model wrote Bellman-Ford/SPFA 33 times but only 8 of those passed.

**GPU hours.** Iteration 1 recorded GPU time for two experiments. The audit took the first and last timestamp of every GPU-phase log and summed the union of the spans (an upper bound that includes waits): geometry 2.92 GPU-hours, forking token 1.55, decommitment 3.23, instruction tuning 2.47 and decoding 3.31. The association experiment has no GPU-phase log; its own report gave about 6 minutes.

**Grid failure taxonomy.** Because "compliant" means correct, low grid compliance could reflect test bias rather than broken programs. Of the 273 DFS programs in the association draw, 161 failed: 127 wrong answers, 31 timeouts and 3 runtime errors. The review's own re-run showed that reading a returned None as an empty path rescues only 2 to 3 programs per condition (under the BFS ban, DFS correct programs rise from 38 to 40); the audit could not repeat it because the stored failure fields do not hold returned values. Table 51 gives the failure kinds per grid condition for the draws that stored them.

**Table 51.** Failing grid programs by kind (source: `results/tables.json#missing_outputs.grid_failure_taxonomy`; the forking token and decommitment draws did not store failure kinds).

| Draw | Condition | Failing | Wrong answer | Timeout | Runtime error |
|-|-|-|-|-|-|
| Association | baseline | 20 | 15 | 4 | 1 |
| Association | baseline, T = 1.3 | 21 | 17 | 3 | 1 |
| Association | ban BFS | 54 | 44 | 8 | 2 |
| Association | ban DFS | 12 | 11 | 1 | 0 |
| Association | ban bidirectional BFS | 8 | 8 | 0 | 0 |
| Association | ban IDDFS | 20 | 19 | 1 | 0 |
| Association | ban A* | 28 | 23 | 4 | 1 |
| Association | ban unit weight Dijkstra | 29 | 20 | 8 | 1 |
| Association | ban BFS and DFS | 47 | 40 | 6 | 1 |
| Association | listing control | 8 | 8 | 0 | 0 |
| Association | mention DFS | 35 | 20 | 15 | 0 |
| Association | mention IDDFS | 41 | 25 | 16 | 0 |
| Association | mention bidirectional BFS | 14 | 10 | 1 | 3 |
| Association | forced DFS | 7 | 5 | 2 | 0 |
| Association | forced IDDFS | 10 | 3 | 7 | 0 |
| Geometry | ban BFS | 24 | 9 | 14 | 1 |
| Geometry | ban BFS and unit weight Dijkstra | 14 | 5 | 9 | 0 |
| Geometry | forced DFS | 21 | 3 | 18 | 0 |
| Geometry | forced IDDFS | 30 | 6 | 23 | 1 |
| Instruction tuning | instruct, chat template, ban BFS | 30 | 10 | 19 | 1 |
| Instruction tuning | base model, plain completion | 277 | 151 | 27 | 99 |
| Decoding | generate then select | 45 | 15 | 27 | 2 |
| Decoding | novelty instruction | 15 | 5 | 7 | 1 |

**Base-model caveats.** The instruction tuning experiment's base arms rest on few programs and weak labels. Under the chat template the base model produced parseable code in 0.583 [0.527, 0.638] of grid samples and 0.663 [0.608, 0.714] of shortest path samples, 57 and 90 correct programs out of 300, with runtime against AST kappa of 0.417 and 0.567 on those arms. In plain completion its correct shortest path programs were Bellman-Ford/SPFA 16, Dijkstra 8 and Floyd-Warshall 1, so its mode there is Bellman-Ford/SPFA, first rather than second. The preregistered verdicts stand as recorded: on the correctness-conditioned Hill number, MIXED on the grid task (modal-share gap 14.04 points against a 15-point bar) and INSTALLED_BY_POST_TRAINING on the shortest path task; INSTALLED_BY_POST_TRAINING on both under the Hill number over all programs; MIXED on both at the planned sample size.

### 2.3.11 Positioning against the nearest published work

The audit checked each positive claim against its nearest neighbours on the arXiv abstract pages on 2026-10-20 and recorded what this run adds (Table 52). All eight arXiv identifiers were verified. The venues of two papers (ICLR 2025 for self-simulation, NAACL 2025 for denial prompting) are not shown on their abstract pages and are marked unverified there.

**Table 52.** Each positive claim, its nearest neighbours and what this run adds (source: `results/positioning.json`).

| Claim | Nearest neighbours | What this run adds, or replication |
|-|-|-|
| Temperature and the sampler change phrasing, not the algorithm | Temperature correlates weakly with novelty [{{Peeperkorn2024}}]; NoveltyBench [{{Zhang2025a}}]; approach-level against surface-level diversity in math reasoning [{{Lee2026}}], whose paper uses temperature only as a sampling setting | An executed, mechanism-labelled measurement of algorithm choice in code across temperature, sampler and thinking mode: no change in algorithm beside a severalfold rise in phrasings. None of the three neighbours reports this measurement in code |
| Generate then select reaches several algorithms at a pass-rate cost | SimpleStrat [{{Wong2024}}] | Replication in code-algorithm space with the pass-rate price; a ceiling row, not a knob |
| The substitute is predictable before the ban from the model's own answers | Verbalized Sampling attributes mode collapse to typicality bias [{{Zhang2025}}]; self-simulation [{{Binder2024}}] | Forecasts of the realised substitute under prohibitions in code; descriptive, and no family advances under the rule |
| Internal states are organised by approach | Math reasoning organised by approach, not topic [{{Goudarzi2026}}] | Code algorithms, prohibitions and a test of the generation-time locus; the locus narrows to a paraphrase-level signal (grid) and a post-commit readout (shortest path) |
| Bans re-collapse on Bellman-Ford/SPFA | The inspiration repository (the specific re-collapse statement was not found in its README); denial prompting [{{Lu2024}}] | Per-draw counts across five independent draws with mechanism labels on an open model, and the generic-perturbation rival on the same task |

