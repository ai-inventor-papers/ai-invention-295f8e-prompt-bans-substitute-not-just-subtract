| Cell | n | Y share [CP 95%] | Transfer | Off-default transfer | Pass ratio | Recovery | Slot interchange intervention accuracy | McNemar b:c (p, Holm) | Correct composition |
|-|-|-|-|-|-|-|-|-|-|
| full ban | 30 | 1.00 [0.88, 1.00] | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 30:0 (1.9e-09, 1.1e-08) | brute force 30 |
| exchange, blocks 0-11 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | hash map 30 |
| exchange, blocks 12-23 | 30 | 0.43 [0.25, 0.63] | 0.43 | 0.43 | 1.00 | 0.43 | 0.43 | 13:0 (2.4e-04, 7.3e-04) | hash map 17, brute force 13 |
| exchange, blocks 24-35 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | hash map 30 |
| exchange, blocks 0-35 | 30 | 0.43 [0.25, 0.63] | 0.43 | 0.43 | 1.00 | 0.43 | 0.43 | 13:0 (2.4e-04, 7.3e-04) | hash map 17, brute force 13 |
| condition-span splice | 30 | 1.00 [0.88, 1.00] | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 30:0 (1.9e-09, 1.1e-08) | brute force 30 |
| read-position exchange | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | hash map 30 |
