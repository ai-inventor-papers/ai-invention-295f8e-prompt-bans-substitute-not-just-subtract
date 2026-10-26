#!/usr/bin/env python3
"""T0(f): the frozen analysis code on SYNTHETIC units (planted rho ~0.8 and ~0.0), placebo calibration, and the
Poisson-binomial / Wilcoxon / Spearman routines against brute force and scipy."""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "analysis"))
import a1a2  # noqa: E402

rng = np.random.default_rng(0)
res = {}


def synth(n, rho):
    z = rng.multivariate_normal([0, 0], [[1, rho], [rho, 1]], size=n)
    beta = list(1 / (1 + np.exp(-z[:, 0])))
    E = list(np.round(np.clip((z[:, 1] + 1) / 3, 0, 1) * 8) / 8)
    units = [{"unit": f"S{i}", "default": "m0", "beta_u": beta[i], "E_u": E[i], "PN_excess_u": E[i] / 2, "K_u": 4,
              "rivals": {"R_modal": float(rng.random()), "K_u": 4}, "flags": [], "beta_attempt": beta[i],
              "beta_plain": beta[i], "beta_correct": beta[i], "P_beta_ge_0.05": 1.0} for i in range(n)]
    return units


for name, rho in (("planted_0.8", 0.8), ("planted_0.0", 0.0)):
    rr = []
    for rep in range(40):
        u = synth(12, rho)
        r = a1a2.spearman([x["beta_u"] for x in u], [x["E_u"] for x in u])
        if r is not None:
            rr.append(r)
    res[name] = {"mean_rho_n12": float(np.mean(rr))}
assert res["planted_0.8"]["mean_rho_n12"] > 0.5 and abs(res["planted_0.0"]["mean_rho_n12"]) < 0.2, res
# end-to-end a1 on a synthetic panel of 7
out = a1a2.a1(synth(7, 0.8))
res["a1_synthetic_7"] = {"rho": out["primary"]["rho"], "p": out["primary"]["p"], "method": out["primary"]["method"],
                         "placebo": out["placebo_shuffled_beta"]}
assert out["placebo_shuffled_beta"]["rejection_rate_p_lt_0.05"] < 0.12, out["placebo_shuffled_beta"]
# exact permutation p vs brute force
x, y = [0.1, 0.5, 0.3, 0.9, 0.7], [0.0, 0.25, 0.125, 0.5, 0.375]
pp = a1a2.perm_p(x, y)
r0 = stats.spearmanr(x, y).statistic
bf = np.mean([stats.spearmanr(x, [y[i] for i in p]).statistic >= r0 - 1e-12 for p in itertools.permutations(range(5))])
assert abs(pp["p"] - bf) < 1e-12 and abs(pp["rho"] - r0) < 1e-12
res["perm_p_check"] = {"ours": pp["p"], "brute": float(bf)}
# Poisson-binomial vs brute force
probs = [0.2, 0.5, 0.33, 0.25]
sf = a1a2.poisson_binomial_sf(2, probs)
bf = sum(np.prod([p if b else 1 - p for p, b in zip(probs, bits)]) for bits in itertools.product([0, 1], repeat=4)
         if sum(bits) >= 2)
assert abs(sf - bf) < 1e-12
res["poisson_binomial_check"] = {"ours": sf, "brute": float(bf)}
# Wilcoxon (exact) as used in a2
d = [0.3, 0.1, -0.05, 0.2, 0.4]
res["wilcoxon_exact_p"] = float(stats.wilcoxon(d, alternative="greater", method="exact").pvalue)
# a2 on a toy event
ev = [{"unit": "S0", "default": "m0", "E_u": 0.25, "beta_u": 0.3, "push_landing": "m1", "r_u": "m1", "K_u": 4,
       "push_landing_composition": {"m1": 5, "m2": 1}, "base_correct_composition": {"m0": 10, "m1": 4},
       "forecasts": {"BASE": {"m1": 0.6, "m2": 0.2, "m3": 0.18, "other": 0.02},
                     "ASSOC": {"m1": 0.3, "m2": 0.5, "m3": 0.18, "other": 0.02},
                     "PROX": {"m1": 0.33, "m2": 0.33, "m3": 0.32, "other": 0.02}}}]
o2 = a1a2.a2(ev)
assert o2["top1"]["hits"] == 1.0 and abs(o2["top1"]["poisson_binomial_p"] - 1 / 3) < 1e-12
res["a2_toy"] = o2["top1"]
(ROOT / "results").mkdir(exist_ok=True)
(ROOT / "results" / "tests_analysis.json").write_text(json.dumps(res, indent=1, default=float))
print(json.dumps(res, indent=1, default=float))
