#!/usr/bin/env python3
"""Stage-0 (g) metric checks: DA@K vs hand computation and Monte Carlo, EA of a uniform distribution, Jaccard of
an identifier-renamed copy, BFS vs DFS reference Jaccard, isotropic subspace null share, checker rejections."""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis.metrics import da_at_k, hill1, jaccard_matrix, normalise_tokens, shingles  # noqa: E402
from common import REFS_DIR, write_json, RESULTS  # noqa: E402
from tasks.t1_grid import check  # noqa: E402


def main():
    out = {}
    # hand example: counts (3,1), N=4, K=2: 1 - C(1,2)/C(4,2) + 1 - C(3,2)/C(4,2) = 1 + (1 - 3/6) = 1.5
    out["da_hand"] = da_at_k([3, 1], 2)
    assert abs(out["da_hand"] - 1.5) < 1e-12
    counts = [60, 25, 10, 5]
    rng = np.random.default_rng(0)
    pool = np.repeat(np.arange(4), counts)
    mc = np.mean([len(set(rng.choice(pool, 25, replace=False))) for _ in range(20000)])
    out["da_formula"], out["da_mc"] = da_at_k(counts, 25), float(mc)
    assert abs(out["da_formula"] - mc) / mc < 0.01
    out["ea_uniform4"] = hill1([5, 5, 5, 5])
    assert abs(out["ea_uniform4"] - 4) < 1e-9
    bfs = (REFS_DIR / "t1_bfs.py").read_text()
    renamed = bfs.replace("queue", "frontier_q").replace("parent", "came_from").replace("rows", "H").replace(
        "cols", "W")
    J = jaccard_matrix([shingles(normalise_tokens(bfs)), shingles(normalise_tokens(renamed)),
                        shingles(normalise_tokens((REFS_DIR / "t1_dfs.py").read_text()))])
    out["jaccard_renamed"], out["jaccard_bfs_dfs"] = float(J[0, 1]), float(J[0, 2])
    assert J[0, 1] == 1.0, J[0, 1]
    assert J[0, 2] < 0.5, J[0, 2]
    d, k = 4096, 5
    sh = []
    for _ in range(200):
        Q, _ = np.linalg.qr(rng.standard_normal((d, k)))
        x = rng.standard_normal(d)
        sh.append(float(((Q.T @ x) ** 2).sum() / (x ** 2).sum()))
    out["isotropic_share_mean"], out["isotropic_expected"] = float(np.mean(sh)), k / d
    assert abs(np.mean(sh) - k / d) / (k / d) < 0.1
    case = dict(grid=["...", ".#.", "..."], start=[0, 0], goal=[2, 2], reachable=True)
    out["checker_rejects"] = {
        "diagonal": not check(case, [(0, 0), (1, 1), (2, 2)])[0],
        "wall": not check(case, [(0, 0), (0, 1), (1, 1), (2, 1), (2, 2)])[0],
        "wrong_start": not check(case, [(0, 1), (0, 2), (1, 2), (2, 2)])[0],
        "valid_accepted": check(case, [(0, 0), (0, 1), (0, 2), (1, 2), (2, 2)])[0],
    }
    assert all(out["checker_rejects"].values())
    write_json(RESULTS / "metric_checks.json", out)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
