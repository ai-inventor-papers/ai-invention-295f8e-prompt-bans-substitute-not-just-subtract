"""Evaluator pool: spawned workers that hold every instance set and fork one sandboxed child per program."""
from __future__ import annotations

import json
import multiprocessing as mp
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from common import DATA, read_jsonl

SET_NAMES = ("selection", "heldout", "heldout_ext")
TSPLIB_SEED0 = 940000


def load_payload() -> dict:
    """Matrices and per-instance RNG seeds of every set, plus the frozen probe states (built in each worker)."""
    from tsp_task import build_sets, dist_matrix, load_tsplib
    from probes import build_probe_states, probe_matrices

    sets = build_sets()
    payload = {}
    for name in SET_NAMES:
        payload[name] = ([dist_matrix(c) for c in sets[name]["coords"]], list(sets[name]["seeds"]))
    ts = load_tsplib()
    payload["tsplib"] = ([t["D_norm"] for t in ts], [TSPLIB_SEED0 + i for i in range(len(ts))], True)
    payload["tsplib_names"] = [t["name"] for t in ts]
    pst = build_probe_states()
    payload["probe_states"] = [(int(i), int(c), list(u)) for i, c, u in pst["states"]]
    payload["probe_mats"] = probe_matrices()
    return payload


def _init() -> None:
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    import sandbox

    sandbox.worker_init(load_payload())


def job_program(code: str, with_probes: bool = True) -> dict:
    import sandbox

    return sandbox.evaluate_program(code, with_probes=with_probes)


def job_set(code: str, set_name: str, cpu_limit: int = 600) -> dict:
    import sandbox

    return sandbox.evaluate_set(code, set_name, cpu_limit)


def job_probe(code: str) -> dict:
    import sandbox

    return sandbox.probe_program(code)


def job_pid() -> int:
    return os.getpid()


def make_pool(n: int) -> ProcessPoolExecutor:
    return ProcessPoolExecutor(max_workers=n, mp_context=mp.get_context("spawn"), initializer=_init)


# ------------------------------------------------------------------ references and gaps
REF_PATH = DATA / "references.jsonl"


def load_references() -> dict[str, np.ndarray]:
    """{set: array of L_ref (float D)} plus 'tsplib_opt' as given by TSPLIB."""
    rows = read_jsonl(REF_PATH)
    out: dict[str, dict[int, float]] = {}
    for r in rows:
        out.setdefault(r["set"], {})[int(r["idx"])] = float(r["L_ref"])
    return {k: np.array([v[i] for i in range(len(v))]) for k, v in out.items()}


def gaps_from_lengths(lengths, L_ref: np.ndarray) -> np.ndarray:
    L = np.asarray(lengths, dtype=np.float64)
    return 100.0 * (L - L_ref) / L_ref


def tsplib_gaps(tours: list, names: list[str]) -> dict[str, float]:
    """gap = 100 (cost_int - opt)/opt on the TSPLIB EUC_2D integer metric."""
    from tsp_task import TSPLIB_OPT, load_tsplib

    ts = {t["name"]: t for t in load_tsplib()}
    out = {}
    for tour, nm in zip(tours, names):
        Di = ts[nm]["D_int"]
        t = np.asarray(tour)
        cost = int(Di[t, np.roll(t, -1)].sum())
        out[nm] = 100.0 * (cost - TSPLIB_OPT[nm]) / TSPLIB_OPT[nm]
    return out


def fitness(gaps64: np.ndarray, nn_g50: float, nn_g100: float) -> tuple[float, float, float]:
    """F = 0.5 G50/G50(NN) + 0.5 G100/G100(NN); lower is better, NN = 1."""
    g50 = float(np.mean(gaps64[:32]))
    g100 = float(np.mean(gaps64[32:64]))
    return 0.5 * g50 / nn_g50 + 0.5 * g100 / nn_g100, g50, g100


def load_baseline_nn() -> dict:
    return json.loads((DATA.parent / "results" / "baselines.json").read_text())["NN"]
