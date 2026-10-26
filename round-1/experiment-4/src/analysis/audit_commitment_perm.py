#!/usr/bin/env python3
"""Exact paired sign-flip and unpaired label-permutation p-values for the ban-minus-mention shift (layer 18),
complementing the paraphrase-split null band of analysis/directions.py. Writes results/audit_commitment_perm.json."""
import itertools
import json
from pathlib import Path

import numpy as np

WS = Path(__file__).resolve().parents[1]
out = {}
rng = np.random.default_rng(7)
for task, X in (("T1", "bfs"), ("T2", "dijkstra")):
    li = 18 - 8
    ld = lambda g: np.load(WS / f"cache/hR_{task}_{g}.npy")[:, li].astype(np.float64)  # noqa: E731
    d = ld("LIST").mean(0) - ld("IMPLEMENT").mean(0)
    proj = lambda H: H @ d / (d @ d)  # noqa: E731
    b, m = proj(ld(f"ban-{X}")[:10]), proj(ld(f"mention-{X}")[:10])
    delta = b - m
    obs = float(delta.mean())
    flips = np.array([np.mean(np.array(s) * delta) for s in itertools.product((1, -1), repeat=10)])
    p_sign = float(np.mean(np.abs(flips) >= abs(obs) - 1e-12))
    pool = np.r_[b, m]
    perm = np.array([pool[p[:10]].mean() - pool[p[10:]].mean() for p in (rng.permutation(20) for _ in range(20000))])
    p_perm = float((1 + np.sum(np.abs(perm) >= abs(obs))) / (1 + len(perm)))
    out[task] = {"X": X, "delta_kappa": obs, "n_pairs_positive": int((delta > 0).sum()),
                 "paired_signflip_p_exact": p_sign, "unpaired_label_perm_p": p_perm}
(WS / "results/audit_commitment_perm.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
