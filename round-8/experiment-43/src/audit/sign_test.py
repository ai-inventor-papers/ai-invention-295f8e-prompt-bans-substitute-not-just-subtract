#!/usr/bin/env python3
"""Holm input re-derived: exact one-sided sign test of MAE_L < MAE_B0 over the scored units, from the MAEs that
audit/rederive.py recomputed from raw rows (math.comb, no scipy); placebo: the same test with L/B0 swapped at random."""
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
r = json.loads((ROOT / "results" / "rederive.json").read_text())
wins = [u["mae"]["L"] < u["mae"]["B0"] for u in r["units"].values() if u["mae"]["L"] != u["mae"]["B0"]]
n, k = len(wins), sum(wins)
p = sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n
rng = random.Random(20261023)
null = []
for _ in range(2000):
    w = [x if rng.random() < 0.5 else not x for x in wins]
    kk = sum(w)
    null.append(sum(math.comb(n, i) for i in range(kk, n + 1)) / 2 ** n)
out = {"n_units": n, "n_L_better_than_B0": k, "p_one_sided": p,
       "placebo_random_swap_reject_rate_at_0.05": sum(x < 0.05 for x in null) / len(null)}
(ROOT / "results" / "sign_test_rederived.json").write_text(json.dumps(out, indent=1))
print(out)
