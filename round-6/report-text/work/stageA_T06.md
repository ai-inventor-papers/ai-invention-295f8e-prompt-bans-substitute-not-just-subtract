| Cell | n | Y share [CP 95%] | Transfer | Off-default transfer | Pass ratio | Recovery | Slot interchange intervention accuracy | McNemar b:c (p, Holm) | Correct composition |
|-|-|-|-|-|-|-|-|-|-|
| full ban | 30 | 0.97 [0.83, 1.00] | 0.97 | 1.00 | 0.87 | 1.00 | 1.00 | 29:0 (3.7e-09, 1.5e-08) | index marking 25, Floyd cycle detection 1 |
| exchange, blocks 0-11 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | hash set 30 |
| exchange, blocks 12-23 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.10 | 1.00 | 0.00 | 0.03 | 0:0 (1.000, 1.000) | hash set 27, Floyd cycle detection 3 |
| exchange, blocks 24-35 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | hash set 30 |
| exchange, blocks 0-35 | 30 | 0.03 [8.4e-04, 0.17] | 0.03 | 0.13 | 1.00 | 0.03 | 0.07 | 1:0 (1.000, 1.000) | hash set 26, Floyd cycle detection 2, index marking 1, sort and adjacent check 1 |
| condition-span splice | 30 | 0.90 [0.73, 0.98] | 0.90 | 0.90 | 0.97 | 0.93 | 0.90 | 27:0 (1.5e-08, 6.0e-08) | index marking 26, hash set 3 |
| read-position exchange | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | hash set 30 |
