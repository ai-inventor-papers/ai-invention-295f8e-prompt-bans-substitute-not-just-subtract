### Per-arm results (vLLM arms; T=1.0, top-p 1.0, no top-k, thinking off)

| arm | task | N | parse | pass [95% Wilson] | n correct | modal (correct) | modal share | Hill_cc [95% cluster-bootstrap] | Hill_all [95%] | audit acc. vs judge | judge-label Hill_cc |
|---|---|---|---|---|---|---|---|---|---|---|---|
| base_tf | t1 | 300 | 0.97 | 0.05 [0.03, 0.08] | 15 | bfs | 0.80 [0.55, 0.93] | 1.65 [1.00, 2.00] | 3.34 [2.92, 3.73] | 1.00 [0.80, 1.00] | 1.65 |
| base_tf | t2 | 300 | 0.97 | 0.08 [0.06, 0.12] | 25 | bellman_ford_spfa | 0.64 [0.45, 0.80] | 2.18 [1.00, 2.73] | 3.24 [2.85, 3.52] | 1.00 [0.80, 1.00] | 2.53 |
| base_chat | t1 | 300 | 0.58 | 0.19 [0.15, 0.24] | 57 | bfs | 0.86 [0.75, 0.93] | 1.58 [1.10, 2.06] | 3.13 [2.44, 3.66] | 1.00 [0.80, 1.00] | 1.58 |
| base_chat | t2 | 300 | 0.66 | 0.30 [0.25, 0.35] | 90 | dijkstra | 0.70 [0.60, 0.78] | 2.09 [1.63, 2.54] | 2.67 [2.26, 3.00] | 0.93 [0.70, 0.99] | 2.19 |
| instruct_tf | t1 | 100 | 0.93 | 0.73 [0.64, 0.81] | 73 | bfs | 1.00 [0.95, 1.00] | 1.00 [1.00, 1.00] | 1.41 [1.11, 1.66] | 1.00 [0.80, 1.00] | 1.00 |
| instruct_tf | t2 | 100 | 0.89 | 0.72 [0.63, 0.80] | 72 | dijkstra | 0.79 [0.68, 0.87] | 1.93 [1.41, 2.37] | 2.60 [1.92, 3.15] | 1.00 [0.80, 1.00] | 1.93 |
| instruct_chat | t1 | 200 | 1.00 | 1.00 [0.98, 1.00] | 200 | bfs | 1.00 [0.98, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [0.80, 1.00] | 1.00 |
| instruct_chat | t2 | 200 | 1.00 | 1.00 [0.98, 1.00] | 200 | dijkstra | 0.96 [0.93, 0.98] | 1.16 [1.03, 1.31] | 1.16 [1.03, 1.31] | 1.00 [0.80, 1.00] | 1.16 |
| base_tf_ban | t1 | 100 | 0.95 | 0.01 [0.00, 0.05] | 1 | bfs | 1.00 [0.21, 1.00] | 1.00 [1.00, 1.00] | 3.50 [2.79, 4.07] | 1.00 [0.80, 1.00] | 1.00 |
| base_tf_ban | t2 | 100 | 0.98 | 0.08 [0.04, 0.15] | 8 | dijkstra | 0.50 [0.22, 0.78] | 2.00 [1.00, 2.00] | 3.43 [2.81, 3.88] | 1.00 [0.80, 1.00] | 2.00 |
| instruct_chat_ban | t1 | 100 | 1.00 | 0.70 [0.60, 0.78] | 70 | bfs | 0.81 [0.71, 0.89] | 1.70 [1.22, 2.25] | 2.10 [1.65, 2.40] | 1.00 [0.80, 1.00] | 1.70 |
| instruct_chat_ban | t2 | 100 | 1.00 | 1.00 [0.96, 1.00] | 100 | dijkstra | 0.54 [0.44, 0.63] | 1.99 [1.65, 2.00] | 1.99 [1.67, 2.00] | 1.00 [0.80, 1.00] | 1.99 |

Label counts over correct programs:

- **base_tf / t1** correct: `{'bfs': 12, 'dfs': 3}`; all parseable: `{'bfs': 134, 'dfs': 65, 'bidir_bfs': 2, 'astar_greedy': 7, 'dijkstra_unit': 2, 'other': 82}`
- **base_tf / t2** correct: `{'dijkstra': 8, 'bellman_ford_spfa': 16, 'floyd_warshall': 1}`; all parseable: `{'dijkstra': 74, 'bellman_ford_spfa': 55, 'bidir_dijkstra': 1, 'floyd_warshall': 10, 'dial': 2, 'other': 149}`
- **base_chat / t1** correct: `{'bfs': 49, 'dfs': 7, 'astar_greedy': 1}`; all parseable: `{'bfs': 109, 'dfs': 30, 'astar_greedy': 12, 'dijkstra_unit': 8, 'other': 16}`
- **base_chat / t2** correct: `{'dijkstra': 63, 'bellman_ford_spfa': 24, 'floyd_warshall': 1, 'other': 2}`; all parseable: `{'dijkstra': 125, 'bellman_ford_spfa': 47, 'bidir_dijkstra': 1, 'floyd_warshall': 4, 'other': 22}`
- **instruct_tf / t1** correct: `{'bfs': 73}`; all parseable: `{'bfs': 83, 'other': 10}`
- **instruct_tf / t2** correct: `{'dijkstra': 57, 'bellman_ford_spfa': 7, 'floyd_warshall': 8}`; all parseable: `{'dijkstra': 61, 'bellman_ford_spfa': 7, 'floyd_warshall': 8, 'other': 13}`
- **instruct_chat / t1** correct: `{'bfs': 200}`; all parseable: `{'bfs': 200}`
- **instruct_chat / t2** correct: `{'dijkstra': 193, 'bellman_ford_spfa': 7}`; all parseable: `{'dijkstra': 193, 'bellman_ford_spfa': 7}`
- **base_tf_ban / t1** correct: `{'bfs': 1}`; all parseable: `{'bfs': 34, 'dfs': 35, 'bidir_bfs': 1, 'astar_greedy': 2, 'dijkstra_unit': 1, 'other': 22}`
- **base_tf_ban / t2** correct: `{'dijkstra': 4, 'bellman_ford_spfa': 4}`; all parseable: `{'dijkstra': 26, 'bellman_ford_spfa': 18, 'floyd_warshall': 6, 'dial': 1, 'other': 47}`
- **instruct_chat_ban / t1** correct: `{'bfs': 57, 'dfs': 12, 'dijkstra_unit': 1}`; all parseable: `{'bfs': 62, 'dfs': 36, 'dijkstra_unit': 2}`
- **instruct_chat_ban / t2** correct: `{'dijkstra': 54, 'bellman_ford_spfa': 46}`; all parseable: `{'dijkstra': 54, 'bellman_ford_spfa': 46}`

### Collapse screen (2x2 weights x format), Hill_cc differences with paraphrase-joint cluster bootstrap

| task | D_weights = H(instruct_chat) - H(base_chat) | D_format = H(base_chat) - H(base_tf) | D_format_instruct = H(instruct_chat) - H(instruct_tf) | interaction | verdict (Hill_cc, pre-registered) | verdict (Hill_all, fallback-3 co-primary) |
|---|---|---|---|---|---|---|
| t1 | -0.58 [-1.01, -0.15] | -0.07 [-0.76, 0.88] | 0.00 [0.00, 0.00] | 0.07 [-0.83, 0.74] | **MIXED** | **INSTALLED_BY_POST_TRAINING** |
| t2 | -0.93 [-1.38, -0.46] | -0.09 [-0.79, 1.12] | -0.76 [-1.26, -0.23] | -0.67 [-1.73, 0.10] | **INSTALLED_BY_POST_TRAINING** | **INSTALLED_BY_POST_TRAINING** |

Same contrasts on Hill_all (all parseable labelled programs):

| task | D_weights_all | D_format_all | D_format_instruct_all | interaction_all |
|---|---|---|---|---|
| t1 | -2.13 [-2.66, -1.43] | -0.21 [-1.05, 0.55] | -0.41 [-0.66, -0.15] | -0.19 [-0.94, 0.63] |
| t2 | -1.50 [-1.91, -1.06] | -0.57 [-1.04, -0.10] | -1.44 [-2.03, -0.71] | -0.87 [-1.60, 0.04] |

Verdict ingredients (Hill_cc):

- t1: H(base_chat) - H(instruct_chat) = 0.58 [0.11, 1.04]; modal-share gap 14.0 pp (instruct modal `bfs`, base_tf modal `bfs`, base_chat modal `bfs`); H(base_tf) - H(instruct_chat) = 0.65 [0.00, 0.99]; bars met: weights=False, format=False, already_in_base=False
  - permutation chi-square p (correct labels): instruct_chat vs base_chat 0.0001, base_chat vs base_tf 0.7389, instruct_chat vs instruct_tf 1.0000
- t2: H(base_chat) - H(instruct_chat) = 0.93 [0.46, 1.38]; modal-share gap 26.5 pp (instruct modal `dijkstra`, base_tf modal `bellman_ford_spfa`, base_chat modal `dijkstra`); H(base_tf) - H(instruct_chat) = 1.02 [-0.16, 1.64]; bars met: weights=True, format=False, already_in_base=False
  - permutation chi-square p (correct labels): instruct_chat vs base_chat 0.0001, base_chat vs base_tf 0.0044, instruct_chat vs instruct_tf 0.0001

Alternate 4 passes the screen (Hill_cc rule): **True**; (Hill_all rule): **True**

Sensitivity of the verdict:

- t1|judge_labels: Hill_cc verdict MIXED (D_weights -0.58 [-1.01, -0.15]); Hill_all verdict INSTALLED_BY_POST_TRAINING (D_weights_all -2.14 [-2.68, -1.44]); sizes {'base_tf': {'N': 300, 'n_correct_labelled': 15}, 'base_chat': {'N': 300, 'n_correct_labelled': 57}, 'instruct_chat': {'N': 200, 'n_correct_labelled': 200}, 'instruct_tf': {'N': 100, 'n_correct_labelled': 73}}
- t1|planned_N_only: Hill_cc verdict MIXED (D_weights -0.59 [-0.99, 0.00]); Hill_all verdict INSTALLED_BY_POST_TRAINING (D_weights_all -2.04 [-2.80, -0.95]); sizes {'base_tf': {'N': 200, 'n_correct_labelled': 12}, 'base_chat': {'N': 100, 'n_correct_labelled': 23}, 'instruct_chat': {'N': 200, 'n_correct_labelled': 200}, 'instruct_tf': {'N': 100, 'n_correct_labelled': 73}}
- t2|judge_labels: Hill_cc verdict INSTALLED_BY_POST_TRAINING (D_weights -1.02 [-1.51, -0.51]); Hill_all verdict INSTALLED_BY_POST_TRAINING (D_weights_all -1.51 [-1.92, -1.06]); sizes {'base_tf': {'N': 300, 'n_correct_labelled': 25}, 'base_chat': {'N': 300, 'n_correct_labelled': 90}, 'instruct_chat': {'N': 200, 'n_correct_labelled': 200}, 'instruct_tf': {'N': 100, 'n_correct_labelled': 72}}
- t2|planned_N_only: Hill_cc verdict MIXED (D_weights -0.51 [-0.88, 0.25]); Hill_all verdict INSTALLED_BY_POST_TRAINING (D_weights_all -1.27 [-1.82, -0.51]); sizes {'base_tf': {'N': 200, 'n_correct_labelled': 18}, 'base_chat': {'N': 100, 'n_correct_labelled': 19}, 'instruct_chat': {'N': 200, 'n_correct_labelled': 200}, 'instruct_tf': {'N': 100, 'n_correct_labelled': 72}}

### Steering (HF, Qwen3-8B, coupled seeds; all deltas vs the hooked c=0 control S0)

| task | arm | N | parse | pass | format_ok_loose | degenerate | Hill_cc | dHill_cc vs S0 | dpass (pp) vs S0 | flip rate vs S0 | restoration idx vs base_chat (add-0.5 / unsmoothed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| t1 | S0 none c=0 | 100 | 1.00 | 1.00 [0.96, 1.00] | 1.00 | 0.00 | 1.00 | – | – | – | – |
| t1 | random1 | 100 | 0.96 | 0.41 [0.32, 0.51] | 1.00 | 0.00 | 1.00 | 0.00 [0.00, 0.00] | -59.0 [-72.0, -44.0] | 0.04 | 0.26 [0.11, 0.63] / 0.00 [0.00, 0.00] |
| t1 | random1_Ronly:c=1.0 | 100 | 1.00 | 1.00 [0.96, 1.00] | 1.00 | 0.00 | 1.00 | 0.00 [0.00, 0.00] | 0.0 [0.0, 0.0] | 0.00 | 0.00 [0.00, 0.00] / 0.00 [0.00, 0.00] |
| t1 | random2 | 100 | 0.98 | 0.68 [0.58, 0.76] | 1.00 | 0.00 | 1.00 | 0.00 [0.00, 0.00] | -32.0 [-44.0, -20.0] | 0.01 | 0.12 [0.04, 0.42] / 0.00 [0.00, 0.00] |
| t1 | sharpen:c=0.5 | 100 | 0.00 | 0.00 [0.00, 0.04] | 0.00 | 0.39 | – | – [–, –] | -100.0 [-100.0, -100.0] | – | – / – |
| t1 | sharpen:c=1.0 | 100 | 0.00 | 0.00 [0.00, 0.04] | 0.00 | 0.00 | – | – [–, –] | -100.0 [-100.0, -100.0] | – | – / – |
| t1 | sharpen:c=1.5 | 100 | 0.00 | 0.00 [0.00, 0.04] | 0.00 | 0.00 | – | – [–, –] | -100.0 [-100.0, -100.0] | – | – / – |
| t1 | sharpen_Ronly:c=1.0 | 100 | 0.28 | 0.14 [0.09, 0.22] | 0.07 | 0.03 | 1.00 | 0.00 [0.00, 0.00] | -86.0 [-94.0, -78.0] | 0.07 | 0.34 [-3.55, 0.50] / 0.00 [0.00, 0.00] |
| t1 | sharpen_Ronly:c=1.0+nocutoff | 20 | 0.55 | 0.15 [0.05, 0.36] | 0.05 | 0.70 | 1.00 | 0.00 [0.00, 0.00] | -85.0 [-100.0, -53.3] | 0.00 | -1.09 [-7.21, 0.38] / 0.00 [0.00, 0.00] |
| t1 | single18:c=0.25 | 50 | 1.00 | 0.94 [0.84, 0.98] | 1.00 | 0.00 | 1.00 | 0.00 [0.00, 0.00] | -6.0 [-15.0, 0.0] | 0.00 | 0.23 [0.04, 0.57] / 0.00 [0.00, 0.00] |
| t1 | single18:c=0.5 | 50 | 1.00 | 0.52 [0.39, 0.65] | 1.00 | 0.00 | 1.00 | 0.00 [0.00, 0.00] | -48.0 [-68.0, -30.0] | 0.00 | 0.35 [-0.39, 0.60] / 0.00 [0.00, 0.00] |
| t1 | single18:c=1.0 | 50 | 0.00 | 0.00 [0.00, 0.07] | 0.00 | 0.94 | – | – [–, –] | -100.0 [-100.0, -100.0] | – | – / – |
| t1 | **knob verdict (band 8-28)** | | | | | | | **DESTRUCTIVE** | c* = 0.5 no sharpening c kept pass >= 0.8 x S0; c* set to 0.5 (flagged) | | |
| t1 | **steer:single18** | | | | | | | **NO_EFFECT_WITHIN_BARS** | | | |
| t1 | **steer:sharpen_Ronly** | | | | | | | **DESTRUCTIVE** | | | |

- t1 random1: thinking-style opening rate 0.00; 4 rows without parseable code; algorithm keywords in those rows: `{'bfs': 4, 'dfs': 1, 'dijkstra': 0, 'astar': 3, 'bellman_ford': 0, 'floyd': 0}`
- t1 random2: thinking-style opening rate 0.00; 2 rows without parseable code; algorithm keywords in those rows: `{'bfs': 2, 'dfs': 0, 'dijkstra': 0, 'astar': 0, 'bellman_ford': 0, 'floyd': 0}`
- t1 sharpen:c=0.5: thinking-style opening rate 0.89; 100 rows without parseable code; algorithm keywords in those rows: `{'bfs': 1, 'dfs': 1, 'dijkstra': 0, 'astar': 0, 'bellman_ford': 0, 'floyd': 0}`
- t1 sharpen:c=1.0: thinking-style opening rate 0.00; 100 rows without parseable code; algorithm keywords in those rows: `{'bfs': 0, 'dfs': 4, 'dijkstra': 0, 'astar': 0, 'bellman_ford': 0, 'floyd': 0}`
- t1 sharpen:c=1.5: thinking-style opening rate 0.00; 100 rows without parseable code; algorithm keywords in those rows: `{'bfs': 1, 'dfs': 3, 'dijkstra': 0, 'astar': 0, 'bellman_ford': 0, 'floyd': 0}`
- t1 sharpen_Ronly:c=1.0: thinking-style opening rate 0.73; 72 rows without parseable code; algorithm keywords in those rows: `{'bfs': 72, 'dfs': 29, 'dijkstra': 0, 'astar': 0, 'bellman_ford': 0, 'floyd': 0}`
- t1 sharpen_Ronly:c=1.0+nocutoff: thinking-style opening rate 0.70; 9 rows without parseable code; algorithm keywords in those rows: `{'bfs': 9, 'dfs': 4, 'dijkstra': 0, 'astar': 0, 'bellman_ford': 0, 'floyd': 0}`
- t1 single18:c=1.0: thinking-style opening rate 1.00; 50 rows without parseable code; algorithm keywords in those rows: `{'bfs': 38, 'dfs': 0, 'dijkstra': 0, 'astar': 0, 'bellman_ford': 0, 'floyd': 0}`

t1: S0 (HF engine) vs B1 (vLLM) implementation check: Hill_cc 1.00 vs 1.00, pass 1.00 [0.96, 1.00] vs 1.00 [0.98, 1.00], permutation p = 1.0000

t1: 512-token no-code rule validation for steer:sharpen_Ronly:c=1.0 on 20 coupled samples: parse 0.30 with rule vs 0.55 without (max 1024 tokens); pass 0.15 vs 0.15; correct labels without rule `{'bfs': 3}`

t1: R-only sharpening vs R-only random control (c=1.0): Hill diff 0.00 [0.00, 0.00], flip diff 0.07 [0.00, 0.19], permutation p 1.0000

| t2 | S0 none c=0 | 100 | 1.00 | 1.00 [0.96, 1.00] | 1.00 | 0.00 | 1.00 | – | – | – | – |
| t2 | random1 | 100 | 1.00 | 0.00 [0.00, 0.04] | 0.99 | 0.01 | – | – [–, –] | -100.0 [-100.0, -100.0] | 0.00 | – / – |
| t2 | random1_Ronly:c=1.0 | 100 | 1.00 | 1.00 [0.96, 1.00] | 1.00 | 0.00 | 1.43 | 0.43 [0.12, 0.74] | 0.0 [0.0, 0.0] | 0.10 | 0.70 [0.31, 0.92] / 0.71 [0.30, 0.93] |
| t2 | random2 | 100 | 1.00 | 0.33 [0.25, 0.43] | 0.97 | 0.03 | 1.00 | 0.00 [0.00, 0.00] | -67.0 [-79.0, -54.0] | 0.36 | -2.10 [-6.94, -0.44] / -2.13 [-6.75, -0.54] |
| t2 | sharpen:c=0.5 | 100 | 0.00 | 0.00 [0.00, 0.04] | 0.00 | 0.95 | – | – [–, –] | -100.0 [-100.0, -100.0] | – | – / – |
| t2 | sharpen:c=1.0 | 100 | 0.00 | 0.00 [0.00, 0.04] | 0.00 | 0.00 | – | – [–, –] | -100.0 [-100.0, -100.0] | – | – / – |
| t2 | sharpen:c=1.5 | 100 | 0.00 | 0.00 [0.00, 0.04] | 0.00 | 0.00 | – | – [–, –] | -100.0 [-100.0, -100.0] | – | – / – |
| t2 | sharpen_Ronly:c=1.0 | 100 | 0.05 | 0.05 [0.02, 0.11] | 0.05 | 0.00 | 1.00 | 0.00 [0.00, 0.00] | -95.0 [-100.0, -88.0] | 0.00 | 0.27 [-0.85, 0.46] / 0.00 [0.00, 0.00] |
| t2 | sharpen_Ronly:c=1.0+nocutoff | 20 | 0.40 | 0.20 [0.08, 0.42] | 0.15 | 0.85 | 1.75 | 0.75 [0.00, 1.00] | -80.0 [-100.0, -60.0] | 0.50 | 0.43 [-2.60, 0.77] / 0.90 [-2.80, 0.98] |
| t2 | single18:c=0.25 | 50 | 1.00 | 0.98 [0.90, 1.00] | 1.00 | 0.00 | 1.00 | 0.00 [0.00, 0.00] | -2.0 [-10.0, 0.0] | 0.00 | 0.12 [0.03, 0.30] / 0.00 [0.00, 0.00] |
| t2 | single18:c=0.5 | 50 | 1.00 | 0.98 [0.90, 1.00] | 1.00 | 0.00 | 1.10 | 0.10 [0.00, 0.38] | -2.0 [-10.0, 0.0] | 0.02 | 0.33 [0.04, 0.77] / 0.27 [0.00, 0.71] |
| t2 | single18:c=1.0 | 50 | 0.00 | 0.00 [0.00, 0.07] | 0.00 | 0.92 | – | – [–, –] | -100.0 [-100.0, -100.0] | – | – / – |
| t2 | **knob verdict (band 8-28)** | | | | | | | **DESTRUCTIVE** | c* = 0.5 no sharpening c kept pass >= 0.8 x S0; c* set to 0.5 (flagged) | | |
| t2 | **steer:single18** | | | | | | | **NO_EFFECT_WITHIN_BARS** | | | |
| t2 | **steer:sharpen_Ronly** | | | | | | | **DESTRUCTIVE** | | | |

- t2 sharpen:c=0.5: thinking-style opening rate 0.22; 100 rows without parseable code; algorithm keywords in those rows: `{'bfs': 0, 'dfs': 0, 'dijkstra': 0, 'astar': 0, 'bellman_ford': 0, 'floyd': 0}`
- t2 sharpen:c=1.0: thinking-style opening rate 0.00; 100 rows without parseable code; algorithm keywords in those rows: `{'bfs': 0, 'dfs': 0, 'dijkstra': 0, 'astar': 0, 'bellman_ford': 0, 'floyd': 0}`
- t2 sharpen:c=1.5: thinking-style opening rate 0.00; 100 rows without parseable code; algorithm keywords in those rows: `{'bfs': 0, 'dfs': 0, 'dijkstra': 0, 'astar': 0, 'bellman_ford': 0, 'floyd': 0}`
- t2 sharpen_Ronly:c=1.0: thinking-style opening rate 0.95; 95 rows without parseable code; algorithm keywords in those rows: `{'bfs': 1, 'dfs': 0, 'dijkstra': 95, 'astar': 0, 'bellman_ford': 4, 'floyd': 0}`
- t2 sharpen_Ronly:c=1.0+nocutoff: thinking-style opening rate 0.85; 12 rows without parseable code; algorithm keywords in those rows: `{'bfs': 1, 'dfs': 0, 'dijkstra': 12, 'astar': 0, 'bellman_ford': 2, 'floyd': 0}`
- t2 single18:c=1.0: thinking-style opening rate 1.00; 50 rows without parseable code; algorithm keywords in those rows: `{'bfs': 1, 'dfs': 0, 'dijkstra': 5, 'astar': 0, 'bellman_ford': 10, 'floyd': 1}`

t2: S0 (HF engine) vs B1 (vLLM) implementation check: Hill_cc 1.00 vs 1.16, pass 1.00 [0.96, 1.00] vs 1.00 [0.98, 1.00], permutation p = 0.1030

t2: 512-token no-code rule validation for steer:sharpen_Ronly:c=1.0 on 20 coupled samples: parse 0.15 with rule vs 0.40 without (max 1024 tokens); pass 0.15 vs 0.20; correct labels without rule `{'dijkstra': 3, 'bellman_ford_spfa': 1}`

t2: R-only sharpening vs R-only random control (c=1.0): Hill diff -0.43 [-0.76, -0.14], flip diff -0.10 [-0.17, -0.04], permutation p 1.0000


Manipulation check, gap_closed = 1 - ||mean h_steered - mean h_B|| / ||mean h_I - mean h_B|| at R:

- manipulation_S t1 steer:sharpen:c=0.5: L8 0.50, L18 0.34, L28 0.38
- manipulation_S t1 steer:sharpen:c=1.0: L8 1.00, L18 0.05, L28 0.01
- manipulation_S t1 steer:sharpen:c=1.5: L8 0.50, L18 -0.38, L28 -0.40
- manipulation_S t2 steer:sharpen:c=0.5: L8 0.50, L18 0.37, L28 0.38
- manipulation_S t2 steer:sharpen:c=1.0: L8 1.00, L18 0.08, L28 0.04
- manipulation_S t2 steer:sharpen:c=1.5: L8 0.50, L18 -0.32, L28 -0.37
- manipulation_R t1 steer:random1: L8 -0.12, L18 0.06, L28 -0.07
- manipulation_R t1 steer:random2: L8 -0.12, L18 0.07, L28 -0.05
- manipulation_R t2 steer:random1: L8 -0.12, L18 0.05, L28 -0.08
- manipulation_R t2 steer:random2: L8 -0.12, L18 0.06, L28 -0.05
- manipulation_X t1 steer:sharpen_Ronly:c=1.0: L8 1.00, L18 0.05, L28 0.01
- manipulation_X t1 steer:random1_Ronly:c=1.0: L8 -0.42, L18 0.03, L28 -0.33
- manipulation_X t1 steer:single18:c=0.25: L8 0.00, L18 0.25, L28 0.04
- manipulation_X t1 steer:single18:c=0.5: L8 0.00, L18 0.50, L28 0.11
- manipulation_X t1 steer:single18:c=1.0: L8 0.00, L18 1.00, L28 0.36
- manipulation_X t1 steer:sharpen_Ronly:c=1.0+nocutoff: L8 1.00, L18 0.05, L28 0.01
- manipulation_X t2 steer:sharpen_Ronly:c=1.0: L8 1.00, L18 0.08, L28 0.04
- manipulation_X t2 steer:random1_Ronly:c=1.0: L8 -0.42, L18 0.03, L28 -0.31
- manipulation_X t2 steer:single18:c=0.25: L8 0.00, L18 0.25, L28 0.06
- manipulation_X t2 steer:single18:c=0.5: L8 0.00, L18 0.50, L28 0.13
- manipulation_X t2 steer:single18:c=1.0: L8 0.00, L18 1.00, L28 0.34
- manipulation_X t2 steer:sharpen_Ronly:c=1.0+nocutoff: L8 1.00, L18 0.08, L28 0.04

### BUY rows

| task | knob | Hill_cc | pass | dHill_cc | pass loss (pp) | efficiency | price Hill 2 | price Hill 3 |
|---|---|---|---|---|---|---|---|---|
| t1 | steer:random1 | 1.00 | 0.41 | 0.00 | 59.0 | 0.000 | – | – |
| t1 | steer:random1_Ronly:c=1.0 | 1.00 | 1.00 | 0.00 | 0.0 | 0.000 | – | – |
| t1 | steer:random2 | 1.00 | 0.68 | 0.00 | 32.0 | 0.000 | – | – |
| t1 | steer:sharpen:c=0.5 | – | 0.00 | – | 100.0 | – | not reached within the tested range | not reached within the tested range |
| t1 | steer:sharpen:c=1.0 | – | 0.00 | – | 100.0 | – | not reached within the tested range | not reached within the tested range |
| t1 | steer:sharpen:c=1.5 | – | 0.00 | – | 100.0 | – | not reached within the tested range | not reached within the tested range |
| t1 | steer:sharpen_Ronly:c=1.0 | 1.00 | 0.14 | 0.00 | 86.0 | 0.000 | not reached within the tested range | not reached within the tested range |
| t1 | steer:sharpen_Ronly:c=1.0+nocutoff | 1.00 | 0.15 | 0.00 | 85.0 | 0.000 | not reached within the tested range | not reached within the tested range |
| t1 | steer:single18:c=0.25 | 1.00 | 0.94 | 0.00 | 6.0 | 0.000 | – | – |
| t1 | steer:single18:c=0.5 | 1.00 | 0.52 | 0.00 | 48.0 | 0.000 | – | – |
| t1 | steer:single18:c=1.0 | – | 0.00 | – | 100.0 | – | – | – |
| t1 | prompt:ban:BFS | 1.70 | 0.70 | 0.70 | 30.0 | 0.023 | n/a (single setting) | n/a (single setting) |
| t2 | steer:random1 | – | 0.00 | – | 100.0 | – | – | – |
| t2 | steer:random1_Ronly:c=1.0 | 1.43 | 1.00 | 0.43 | 0.0 | 0.430 | – | – |
| t2 | steer:random2 | 1.00 | 0.33 | 0.00 | 67.0 | 0.000 | – | – |
| t2 | steer:sharpen:c=0.5 | – | 0.00 | – | 100.0 | – | not reached within the tested range | not reached within the tested range |
| t2 | steer:sharpen:c=1.0 | – | 0.00 | – | 100.0 | – | not reached within the tested range | not reached within the tested range |
| t2 | steer:sharpen:c=1.5 | – | 0.00 | – | 100.0 | – | not reached within the tested range | not reached within the tested range |
| t2 | steer:sharpen_Ronly:c=1.0 | 1.00 | 0.05 | 0.00 | 95.0 | 0.000 | not reached within the tested range | not reached within the tested range |
| t2 | steer:sharpen_Ronly:c=1.0+nocutoff | 1.75 | 0.20 | 0.75 | 80.0 | 0.009 | not reached within the tested range | not reached within the tested range |
| t2 | steer:single18:c=0.25 | 1.00 | 0.98 | 0.00 | 2.0 | 0.000 | – | – |
| t2 | steer:single18:c=0.5 | 1.10 | 0.98 | 0.10 | 2.0 | 0.052 | – | – |
| t2 | steer:single18:c=1.0 | – | 0.00 | – | 100.0 | – | – | – |
| t2 | prompt:ban:Dijkstra | 1.99 | 1.00 | 0.83 | 0.0 | 0.830 | n/a (single setting) | n/a (single setting) |

### PREDICT rows (hash-committed before phase C; primary = base_tf all-samples, fallback 3)

| task | predictor | primary | n compliant | realised mode | top-1 | hit | log score | JS to realised | hash match |
|---|---|---|---|---|---|---|---|---|---|
| t1 | base_chat_correct | False | 13 | dfs | dfs | True | -0.412 | 0.032 | True |
| t1 | base_tf_all | True | 13 | dfs | dfs | True | -0.470 | 0.066 | True |
| t1 | base_tf_correct | False | 13 | dfs | dfs | True | -0.412 | 0.032 | True |
| t1 | instruct_chat_correct | False | 13 | dfs | dfs | True | -1.630 | 0.352 | True |
| t1 | uniform | False | 13 | dfs | dfs | True | -1.630 | 0.352 | True |
| t2 | base_chat_correct | False | 46 | bellman_ford_spfa | bellman_ford_spfa | True | -0.058 | 0.020 | True |
| t2 | base_tf_all | True | 46 | bellman_ford_spfa | bellman_ford_spfa | True | -0.220 | 0.074 | True |
| t2 | base_tf_correct | False | 46 | bellman_ford_spfa | bellman_ford_spfa | True | -0.144 | 0.049 | True |
| t2 | instruct_chat_correct | False | 46 | bellman_ford_spfa | bellman_ford_spfa | True | -0.058 | 0.020 | True |
| t2 | uniform | False | 46 | bellman_ford_spfa | bellman_ford_spfa | True | -1.406 | 0.384 | True |

Realised compliant landing counts: t1: `{'dfs': 12, 'bidir_bfs': 0, 'iddfs': 0, 'astar_greedy': 0, 'dijkstra_unit': 1, 'other': 0}`; t2: `{'bellman_ford_spfa': 46, 'bidir_dijkstra': 0, 'floyd_warshall': 0, 'dial': 0, 'other': 0}`

### Base-model ban obedience (template-free A3 vs A1)

- t1: banned `bfs` share among parseable: ban 0.36 [0.27, 0.46] vs baseline 0.46 [0.40, 0.52] (diff -0.10 [-0.21, 0.01]); compliance (correct and not banned) 0.00 [0.00, 0.04]; base landing `{'dfs': 0, 'bidir_bfs': 0, 'iddfs': 0, 'astar_greedy': 0, 'dijkstra_unit': 0, 'other': 0}`; instruct landing `{'dfs': 12, 'bidir_bfs': 0, 'iddfs': 0, 'astar_greedy': 0, 'dijkstra_unit': 1, 'other': 0}` (instruct compliance 0.13 [0.08, 0.21]); JS(base, instruct landing) –
- t2: banned `dijkstra` share among parseable: ban 0.27 [0.19, 0.36] vs baseline 0.25 [0.21, 0.31] (diff 0.01 [-0.09, 0.11]); compliance (correct and not banned) 0.04 [0.02, 0.10]; base landing `{'bellman_ford_spfa': 4, 'bidir_dijkstra': 0, 'floyd_warshall': 0, 'dial': 0, 'other': 0}`; instruct landing `{'bellman_ford_spfa': 46, 'bidir_dijkstra': 0, 'floyd_warshall': 0, 'dial': 0, 'other': 0}` (instruct compliance 0.46 [0.37, 0.56]); JS(base, instruct landing) 0.068

### Labeller QA

- Reference gate (15 catalogue references + 10 variants/mutants): AST accuracy 1.00, runtime never-wrong rate 1.00 (exact 0.88; array-scan Dijkstra and Dial are 'unknown' at runtime by design), gate ok = True
- Cohen's kappa runtime vs AST (all parseable programs): 0.77
- Second judge (deepseek/deepseek-v4.1-flash) on 40 audit programs: inter-judge kappa 0.93, raw agreement 0.95

| arm / task | n parseable | kappa runtime-AST | audit acc. (15) | final vs judge (all) | runtime+AST labels vs judge | sources |
|---|---|---|---|---|---|---|
| base_tf|t1 | 292 | 0.45 | 1.00 [0.80, 1.00] | 0.98 [0.95, 0.99] | 0.91 [0.82, 0.95] | {'runtime+ast': 75, 'judge': 217, 'fallback': 0} |
| base_tf|t2 | 291 | 0.20 | 1.00 [0.80, 1.00] | 0.99 [0.98, 1.00] | 0.92 [0.75, 0.98] | {'runtime+ast': 25, 'judge': 266, 'fallback': 0} |
| base_chat|t1 | 175 | 0.40 | 1.00 [0.80, 1.00] | 0.99 [0.97, 1.00] | 0.99 [0.93, 1.00] | {'runtime+ast': 81, 'judge': 94, 'fallback': 0} |
| base_chat|t2 | 199 | 0.50 | 0.93 [0.70, 0.99] | 0.97 [0.94, 0.99] | 0.94 [0.88, 0.97] | {'runtime+ast': 105, 'judge': 94, 'fallback': 0} |
| base_tf_ban|t1 | 95 | 0.43 | 1.00 [0.80, 1.00] | 0.98 [0.93, 0.99] | 0.93 [0.77, 0.98] | {'runtime+ast': 27, 'judge': 68, 'fallback': 0} |
| base_tf_ban|t2 | 98 | 0.34 | 1.00 [0.80, 1.00] | 0.99 [0.94, 1.00] | 0.93 [0.70, 0.99] | {'runtime+ast': 15, 'judge': 83, 'fallback': 0} |
| instruct_chat|t1 | 200 | 1.00 | 1.00 [0.80, 1.00] | 1.00 [0.98, 1.00] | 1.00 [0.98, 1.00] | {'runtime+ast': 200, 'judge': 0, 'fallback': 0} |
| instruct_chat|t2 | 200 | 1.00 | 1.00 [0.80, 1.00] | 1.00 [0.98, 1.00] | 1.00 [0.98, 1.00] | {'runtime+ast': 193, 'judge': 7, 'fallback': 0} |
| instruct_tf|t1 | 93 | 0.71 | 1.00 [0.80, 1.00] | 1.00 [0.96, 1.00] | 1.00 [0.95, 1.00] | {'runtime+ast': 76, 'judge': 17, 'fallback': 0} |
| instruct_tf|t2 | 89 | 0.89 | 1.00 [0.80, 1.00] | 1.00 [0.96, 1.00] | 1.00 [0.94, 1.00] | {'runtime+ast': 66, 'judge': 23, 'fallback': 0} |
| instruct_chat_ban|t1 | 100 | 0.64 | 1.00 [0.80, 1.00] | 1.00 [0.96, 1.00] | 1.00 [0.95, 1.00] | {'runtime+ast': 80, 'judge': 20, 'fallback': 0} |
| instruct_chat_ban|t2 | 100 | 0.98 | 1.00 [0.80, 1.00] | 1.00 [0.96, 1.00] | 1.00 [0.93, 1.00] | {'runtime+ast': 54, 'judge': 46, 'fallback': 0} |
| steer:none:c=0|t1 | 100 | 1.00 | 1.00 [0.80, 1.00] | 1.00 [0.96, 1.00] | 1.00 [0.96, 1.00] | {'runtime+ast': 100, 'judge': 0, 'fallback': 0} |
| steer:none:c=0|t2 | 100 | 1.00 | 1.00 [0.80, 1.00] | 1.00 [0.96, 1.00] | 1.00 [0.96, 1.00] | {'runtime+ast': 100, 'judge': 0, 'fallback': 0} |
| steer:random1|t1 | 96 | 0.92 | 1.00 [0.80, 1.00] | 1.00 [0.96, 1.00] | 1.00 [0.92, 1.00] | {'runtime+ast': 45, 'judge': 51, 'fallback': 0} |
| steer:random1|t2 | 100 | 0.00 | 1.00 [0.80, 1.00] | 1.00 [0.96, 1.00] | – [–, –] | {'runtime+ast': 0, 'judge': 100, 'fallback': 0} |
| steer:random1_Ronly:c=1.0|t1 | 100 | 1.00 | 1.00 [0.80, 1.00] | 1.00 [0.96, 1.00] | 1.00 [0.96, 1.00] | {'runtime+ast': 100, 'judge': 0, 'fallback': 0} |
| steer:random1_Ronly:c=1.0|t2 | 100 | 0.85 | 1.00 [0.80, 1.00] | 1.00 [0.96, 1.00] | 1.00 [0.96, 1.00] | {'runtime+ast': 93, 'judge': 7, 'fallback': 0} |
| steer:random2|t1 | 98 | 0.30 | 1.00 [0.80, 1.00] | 1.00 [0.96, 1.00] | 1.00 [0.96, 1.00] | {'runtime+ast': 86, 'judge': 12, 'fallback': 0} |
| steer:random2|t2 | 100 | 0.85 | 1.00 [0.80, 1.00] | 1.00 [0.96, 1.00] | 1.00 [0.61, 1.00] | {'runtime+ast': 6, 'judge': 94, 'fallback': 0} |
| steer:sharpen_Ronly:c=1.0+nocutoff|t1 | 11 | 0.15 | 1.00 [0.74, 1.00] | 1.00 [0.74, 1.00] | 1.00 [0.44, 1.00] | {'runtime+ast': 3, 'judge': 8, 'fallback': 0} |
| steer:sharpen_Ronly:c=1.0+nocutoff|t2 | 8 | 0.79 | 1.00 [0.68, 1.00] | 1.00 [0.68, 1.00] | 1.00 [0.51, 1.00] | {'runtime+ast': 4, 'judge': 4, 'fallback': 0} |
| steer:sharpen_Ronly:c=1.0|t1 | 28 | 0.07 | 1.00 [0.80, 1.00] | 1.00 [0.88, 1.00] | 1.00 [0.78, 1.00] | {'runtime+ast': 14, 'judge': 14, 'fallback': 0} |
| steer:sharpen_Ronly:c=1.0|t2 | 5 | 1.00 | 1.00 [0.57, 1.00] | 1.00 [0.57, 1.00] | 1.00 [0.57, 1.00] | {'runtime+ast': 5, 'judge': 0, 'fallback': 0} |
| steer:single18:c=0.25|t1 | 50 | 1.00 | 1.00 [0.80, 1.00] | 1.00 [0.93, 1.00] | 1.00 [0.93, 1.00] | {'runtime+ast': 50, 'judge': 0, 'fallback': 0} |
| steer:single18:c=0.25|t2 | 50 | 0.00 | 1.00 [0.80, 1.00] | 1.00 [0.93, 1.00] | 1.00 [0.93, 1.00] | {'runtime+ast': 49, 'judge': 1, 'fallback': 0} |
| steer:single18:c=0.5|t1 | 50 | 1.00 | 1.00 [0.80, 1.00] | 1.00 [0.93, 1.00] | 1.00 [0.93, 1.00] | {'runtime+ast': 50, 'judge': 0, 'fallback': 0} |
| steer:single18:c=0.5|t2 | 50 | 0.66 | 1.00 [0.80, 1.00] | 1.00 [0.93, 1.00] | 1.00 [0.93, 1.00] | {'runtime+ast': 48, 'judge': 2, 'fallback': 0} |

### Priors (context, not tests)

- T2: {"invisible_lottery_table12": {"setting": "no cue, 15 configs, T=0, N=35 each", "dijkstra": 0.941, "bfs": 0.059}, "inspiration_repo_llm_creativity": {"setting": "claude-sonnet-5 weighted shortest path baseline", "dijkstra": "25/25", "cumulative_bans": "SPFA 16/25, Bellman-Ford 5/25", "ast_judge_agreement": "164/200"}}
- T1: {"note": "no published prior for the unweighted grid-path task"}
