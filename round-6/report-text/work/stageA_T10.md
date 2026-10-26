| Cell | n | Y share [CP 95%] | Transfer | Off-default transfer | Pass ratio | Recovery | Slot interchange intervention accuracy | McNemar b:c (p, Holm) | Correct composition |
|-|-|-|-|-|-|-|-|-|-|
| full ban | 30 | 0.90 [0.73, 0.98] | 0.90 | 1.00 | 1.00 | 1.00 | 1.00 | 27:0 (1.5e-08, 3.0e-08) | BFS 27, DFS 3 |
| exchange, blocks 0-11 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.87 | 0.70 | 0.00 | 0.10 | 0:0 (1.000, 1.000) | DFS 17, union find 4 |
| exchange, blocks 12-23 | 30 | 0.47 [0.28, 0.66] | 0.47 | 1.00 | 1.00 | 0.52 | 0.43 | 14:0 (1.2e-04, 4.9e-04) | DFS 16, BFS 14 |
| exchange, blocks 24-35 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.63 | 1.00 | 0.00 | 0.10 | 0:0 (1.000, 1.000) | DFS 19, union find 11 |
| exchange, blocks 0-35 | 30 | 0.37 [0.20, 0.56] | 0.37 | 1.00 | 1.00 | 0.41 | 0.40 | 11:0 (9.8e-04, 0.002) | DFS 19, BFS 11 |
| condition-span splice | 30 | 0.10 [0.02, 0.27] | 0.10 | 1.00 | 1.00 | 0.11 | 0.20 | 3:0 (0.250, 0.500) | DFS 27, BFS 3 |
| read-position exchange | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | union find 30 |
| matched-norm random exchange, blocks 0-35 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.07 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | union find 28, DFS 2 |
| matched-norm random exchange, blocks 12-23 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.03 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | union find 29, DFS 1 |
| placebo twin | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.03 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | union find 29, DFS 1 |
