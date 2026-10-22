
### Prediction scorecard (committed in `predictions/s_commit.json` before the first decisive sample)

| Prediction | Outcome |
|---|---|
| S-a: the better of S0/S4 beats S1, S2 and S5 by >= 0.15 on T03 and T10 (Holm over 6) | **PASS, robust to selection** (S0 alpha 4; diffs 0.40-0.42 on T03 and 0.28 on T10) |
| (i) S4 >= S0 at their best gated dose, both above S1/S2/S5 | **Missed** at equal alpha (S4 0.26 vs S0 0.42 on T03; 0.14 vs 0.28 on T10). Both are above the comparators. On the residual-fraction axis S4 >= S0 (dose axis, descriptive) |
| (ii) every moving cell lands modally on the base runner-up | **Missed as stated** (T03 10/12 cells, T10 2/3, T2 1/1). Per event: 241/286, 35/51, 14/14, all far above chance |
| (iii) S3 moves T10 >= 0.10 above the twin at a gated dose | **Missed** (excess 0.10 at alpha 2 but p 0.12). S-c passes on T03 |
| (iv) F1 share >= 0.80 | **Hit** (0.99), but the label-preserving control is also 0.82 |
| (v) m > 5.70 nats on T2, T03, T1 | **Hit** (12.8, 8.6, 7.3); at the fork token 5.25-5.49 (just under) |
| (vi) T03 top-5 avoidance < 0.5 at alpha <= 2; T1 push stays on BFS | **Hit** for T03 (0.00). For T1, hit at alpha 1-2; at alpha 4 the push leaves BFS for unit-weight Dijkstra |

### Per-site cells (correct off-default share of N with Wilson 95% CI / pass rate / invalid rate / byte-identical rate vs the twin)

S0/S4/S1/S2/S5 on T03 and T10 are N = 50 (k 0-9, outcome-blind top-up included). S3 and S1E are N = 30, and so is
every T2 cell.
