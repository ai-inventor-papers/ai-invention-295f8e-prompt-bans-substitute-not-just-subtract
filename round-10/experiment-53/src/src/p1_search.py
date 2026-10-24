"""Tuned parametric baseline P1: random search, 2,000 evaluations on SELECTION only (rng 777).

Each evaluation is logged with the best-so-far F, so the comparator at exactly C* evaluations (C* = calls per arm)
is read off after COMMIT #2. The fast in-process tour builder mirrors the P1 program's numpy expressions; the
chosen weights are re-evaluated through the sandbox before they are reported.
"""
from __future__ import annotations

import multiprocessing as mp
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, append_jsonl, read_jsonl, setup_logging, utc_now  # noqa: E402

OUT = DATA / "p1_search.jsonl"
N_EVAL = 2000
_M: dict = {}


def _init() -> None:
    import os

    os.environ["OMP_NUM_THREADS"] = "1"
    from tsp_task import build_sets, dist_matrix

    sets = build_sets()
    _M["mats"] = [dist_matrix(c) for c in sets["selection"]["coords"]]


def _eval(args):
    k, w = args
    from baselines import p1_tour_fast

    return k, [p1_tour_fast(D, w) for D in _M["mats"]]


def main() -> None:
    logger = setup_logging("p1_search")
    import evaluator as ev
    from baselines import p1_draw_weights

    refs = ev.load_references()["selection"]
    nn = ev.load_baseline_nn()
    W = p1_draw_weights(N_EVAL, 777)
    done = {r["k"]: r for r in read_jsonl(OUT)}
    todo = [(k, W[k]) for k in range(N_EVAL) if k not in done]
    n_workers = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    logger.info(f"P1 random search: {len(todo)} evaluations to run on {n_workers} workers ({len(done)} done)")
    t0 = time.time()
    results = dict()
    with ProcessPoolExecutor(n_workers, mp_context=mp.get_context("spawn"), initializer=_init) as pool:
        for k, lengths in pool.map(_eval, todo, chunksize=4):
            gaps = ev.gaps_from_lengths(lengths, refs)
            F, g50, g100 = ev.fitness(gaps, nn["G50"], nn["G100"])
            results[k] = {"k": k, "w": W[k], "F": F, "G50": g50, "G100": g100, "utc": utc_now()}
            append_jsonl(OUT, results[k])
            if len(results) % 100 == 0:
                logger.info(f"  {len(results)} evals in {time.time() - t0:.0f}s")
    rows = {r["k"]: r for r in read_jsonl(OUT)}
    best, best_k, curve = np.inf, None, []
    for k in range(N_EVAL):
        if k in rows and rows[k]["F"] < best:
            best, best_k = rows[k]["F"], k
        curve.append({"k": k, "best_F": best, "best_k": best_k})
    import json

    (DATA / "p1_best_so_far.json").write_text(json.dumps(curve))
    logger.info(f"P1 done: best F {best:.4f} at evaluation {best_k}")


if __name__ == "__main__":
    main()
