| Cell | n | Y share [CP 95%] | Transfer | Off-default transfer | Pass ratio | Recovery | Slot interchange intervention accuracy | McNemar b:c (p, Holm) | Correct composition |
|-|-|-|-|-|-|-|-|-|-|
| full ban | 30 | 0.67 [0.47, 0.83] | 0.67 | 1.00 | 0.93 | 1.00 | 1.00 | 20:0 (1.9e-06, 1.9e-06) | quickselect 18, size-k heap 10 |
| exchange, blocks 0-11 | 30 | 0.40 [0.23, 0.59] | 0.40 | 0.53 | 1.00 | 0.60 | 0.33 | 12:0 (4.9e-04, 0.003) | full sort 14, quickselect 12, size-k heap 4 |
| exchange, blocks 12-23 | 30 | 0.57 [0.37, 0.75] | 0.57 | 1.00 | 0.93 | 0.85 | 0.90 | 17:0 (1.5e-05, 7.6e-05) | quickselect 15, size-k heap 13 |
| exchange, blocks 24-35 | 30 | 0.03 [8.4e-04, 0.17] | 0.03 | 0.03 | 1.00 | 0.05 | 0.03 | 1:0 (1.000, 1.000) | full sort 29, quickselect 1 |
| exchange, blocks 0-35 | 30 | 0.57 [0.37, 0.75] | 0.57 | 1.00 | 0.97 | 0.85 | 0.90 | 17:0 (1.5e-05, 7.6e-05) | quickselect 16, size-k heap 13 |
| condition-span splice | 30 | 0.93 [0.78, 0.99] | 0.93 | 1.00 | 0.90 | 1.40 | 0.60 | 28:0 (7.5e-09, 3.7e-08) | quickselect 25, size-k heap 2 |
| read-position exchange | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | full sort 30 |
| matched-norm random exchange, blocks 0-35 | 30 | 0.10 [0.02, 0.27] | 0.10 | 0.10 | 1.00 | 0.15 | 0.03 | 3:0 (0.250, 0.750) | full sort 27, quickselect 3 |
| matched-norm random exchange, blocks 12-23 | 30 | 0.13 [0.04, 0.31] | 0.13 | 0.13 | 1.00 | 0.20 | 0.00 | 4:0 (0.125, 0.375) | full sort 26, quickselect 4 |
| placebo twin | 30 | 0.03 [8.4e-04, 0.17] | 0.03 | 0.03 | 1.00 | 0.05 | 0.00 | 1:0 (1.000, 1.000) | full sort 29, quickselect 1 |
