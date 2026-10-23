#!/usr/bin/env python3
"""Smoke test of the analysis functions on the 32B M-name / M-lex states (no commit, small bootstrap)."""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(1, str(ROOT / "vendor" / "exp9"))


def main():
    import numpy as np
    import stage_analysis as sa
    t0 = time.time()
    m = sa.load_manifold("32b", "mname")
    X = m["X"][:, m["blocks"].index(31)].astype(np.float64)
    d = sa.describe(X, m["labels"], embed=True)
    d.pop("_emb")
    print("describe", round(time.time() - t0, 1), d["k15"]["classes"], d["k15"]["udij_rank"], round(d["k15"]["udij_ratio"], 3))
    print("landing", {k: v.get("verdict") for k, v in sa.landing_all(d["k15"]["g"], d["k15"]["classes"]).items()})
    sh = sa.split_half(X, m["labels"], m["groups"], 15)
    print("split", round(sh["spearman_halves"], 3), round(sh["spearman_brown"], 3))
    bs = sa.bootstrap(X, m["labels"], m["groups"], 15, 24, d["k15"])
    bs.pop("_matrices")
    print("boot", bs["class_stability"], bs["udij_ratio_ci95"], round(time.time() - t0, 1))
    print("crossnobis", sa.crossnobis(X, m["labels"], m["groups"])["classes"])
    rb = sa.robustness(m["X"], m["labels"], m["blocks"], 31)
    print("robust", rb["udij_class_counts"], rb["verdict_counts"], round(time.time() - t0, 1))
    al = sa.alias_level("32b", "mname", 31)
    print("alias", {k: (round(al[k]["spearman_L1"], 3), al[k]["perm_p_L1"], round(al[k]["within_algorithm"]["exact_p_lower"], 3)) for k in ("k10", "k15")}, al["P4_pass"], round(time.time() - t0, 1))
    M = np.array(d["k15"]["class_geodesic_matrix"])
    M = (M + M.T) / 2
    R = np.array(json.load(open(ROOT / "results" / "behavioural_distance.json"))["d_beh_lambda0.5"])
    t1 = time.time()
    print("mantel", sa.mantel_exact(M, R), round(time.time() - t1, 1))
    m2 = sa.load_manifold("32b", "mlex")
    X2 = m2["X"][:, m2["blocks"].index(31)].astype(np.float64)
    d2 = sa.describe(X2, m2["labels"])
    print("mlex k15", d2["k15"]["classes"], d2["k10"]["classes"])


if __name__ == "__main__":
    main()
