#!/usr/bin/env python3
"""S7 measured-order matrix: exp46 expansion.py (unchanged) traces every frozen factorial program on the 40
iteration-9 probe grids; D_order[i, j] = expansion.pair_order_distance (1 - mean_grid J * (1 + tau_b) / 2).
Output: data/order_matrix_factorial.npz (D, uids)."""
import json
import multiprocessing as mp
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def _rows(args):
    i, traces = args
    import expansion
    return i, [expansion.pair_order_distance(traces[i], traces[j]) for j in range(i + 1, len(traces))]


def main():
    import expansion
    rows = [json.loads(l) for l in (ROOT / "data/factorial_set.jsonl").read_text().splitlines() if l.strip()]
    grids = json.loads((ROOT / "inputs/art_VVA3P0ocZNA2/data/probe_grids.json").read_text())["grids"]
    traces = expansion.trace_many([r["scrubbed"] for r in rows], grids, workers=3)
    n = len(rows)
    D = np.zeros((n, n))
    with ProcessPoolExecutor(max_workers=3, mp_context=mp.get_context("spawn")) as ex:
        for i, vals in ex.map(_rows, [(i, traces) for i in range(n)], chunksize=4):
            D[i, i + 1:] = vals
            D[i + 1:, i] = vals
    np.savez(ROOT / "data/order_matrix_factorial.npz", D=D, uids=np.array([r["uid"] for r in rows]))
    print("done", n)


if __name__ == "__main__":
    main()
