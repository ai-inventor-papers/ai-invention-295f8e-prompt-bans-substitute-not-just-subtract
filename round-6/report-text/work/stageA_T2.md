| Cell | n | Y share [CP 95%] | Transfer | Off-default transfer | Pass ratio | Recovery | Slot interchange intervention accuracy | McNemar b:c (p, Holm) | Correct composition |
|-|-|-|-|-|-|-|-|-|-|
| full ban | 30 | 0.97 [0.83, 1.00] | 0.97 | 0.97 | 1.00 | 1.00 | 1.00 | 29:0 (3.7e-09, 1.5e-08) | Bellman-Ford/SPFA 29, Dijkstra 1 |
| exchange, blocks 0-11 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.03 | 0:0 (1.000, 1.000) | Dijkstra 30 |
| exchange, blocks 12-23 | 30 | 0.60 [0.41, 0.77] | 0.60 | 0.60 | 0.73 | 0.62 | 0.63 | 18:0 (7.6e-06, 4.6e-05) | Dijkstra 11, Bellman-Ford/SPFA 11 |
| exchange, blocks 24-35 | 30 | 0.37 [0.20, 0.56] | 0.37 | 0.37 | 1.00 | 0.38 | 0.40 | 11:0 (9.8e-04, 0.006) | Dijkstra 19, Bellman-Ford/SPFA 11 |
| exchange, blocks 0-35 | 30 | 0.80 [0.61, 0.92] | 0.80 | 0.80 | 0.90 | 0.83 | 0.83 | 24:0 (1.2e-07, 7.2e-07) | Bellman-Ford/SPFA 21, Dijkstra 6 |
| condition-span splice | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.03 | 0:0 (1.000, 1.000) | Dijkstra 30 |
| read-position exchange | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.03 | 0:0 (1.000, 1.000) | Dijkstra 30 |
| matched-norm random exchange, blocks 0-35 | 30 | 0.03 [8.4e-04, 0.17] | 0.03 | 0.03 | 0.97 | 0.03 | 0.07 | 1:0 (1.000, 1.000) | Dijkstra 29 |
| matched-norm random exchange, blocks 12-23 | 30 | 0.03 [8.4e-04, 0.17] | 0.03 | 0.03 | 0.93 | 0.03 | 0.07 | 1:0 (1.000, 1.000) | Dijkstra 28 |
| placebo twin | 30 | 0.03 [8.4e-04, 0.17] | 0.03 | 0.03 | 1.00 | 0.03 | 0.07 | 1:0 (1.000, 1.000) | Dijkstra 29, Bellman-Ford/SPFA 1 |
