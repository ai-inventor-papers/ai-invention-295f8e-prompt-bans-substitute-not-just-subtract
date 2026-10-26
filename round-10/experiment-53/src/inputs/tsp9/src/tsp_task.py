"""TSP constructive task: instances, distance matrices, TSPLIB, LKH references (ReEvo/EoH interface)."""
from __future__ import annotations

import gzip
import math
import time
from pathlib import Path

import numpy as np
from scipy.spatial import distance_matrix as _scipy_dm

from common import DATA, sha256_file

INST_DIR = DATA / "instances"
TSPLIB_RAW = DATA / "tsplib_raw"

# Instance sets (seed, n). SELECTION is the only set the search ever sees.
SETS: dict[str, list[tuple[int, int]]] = {
    "selection": [(910001 + i, 50) for i in range(32)] + [(910101 + i, 100) for i in range(32)],
    "heldout": [(920001 + i, 200) for i in range(32)],
    "heldout_ext": [(920033 + i, 200) for i in range(96)],
    "probe": [(930001 + i, int(round(50 + 150 * i / 19))) for i in range(20)],
}

TSPLIB_OPT = {
    "eil51": 426, "berlin52": 7542, "st70": 675, "eil76": 538, "pr76": 108159,
    "kroA100": 21282, "kroB100": 22141, "eil101": 629, "lin105": 14379, "ch130": 6110,
    "ch150": 6528, "kroA150": 26524, "kroA200": 29368,
}
TSPLIB_SOURCE = "https://raw.githubusercontent.com/mastqe/tsplib/master/{name}.tsp"


def coords_for(seed: int, n: int) -> np.ndarray:
    return np.random.default_rng(seed).uniform(0, 1, (n, 2))


def dist_matrix(coords: np.ndarray) -> np.ndarray:
    D = _scipy_dm(coords, coords).astype(np.float64)
    return D


def tour_length(tour: list[int] | np.ndarray, D: np.ndarray) -> float:
    t = np.asarray(tour, dtype=np.int64)
    return float(D[t, np.roll(t, -1)].sum())


def build_sets() -> dict[str, dict]:
    """Create (or load) every random instance set; returns {set: {'seeds','ns','coords':[...], 'sha256'}}."""
    out = {}
    for name, spec in SETS.items():
        p = INST_DIR / f"{name}.npz"
        if not p.exists():
            arrs = {f"c_{s}": coords_for(s, n) for s, n in spec}
            np.savez(p, **arrs)
        z = np.load(p)
        coords = [z[f"c_{s}"] for s, _ in spec]
        out[name] = {"seeds": [s for s, _ in spec], "ns": [n for _, n in spec], "coords": coords,
                     "sha256": sha256_file(p), "path": str(p.relative_to(DATA.parent))}
    return out


# ---------------------------------------------------------------- TSPLIB
def parse_tsplib(path: Path) -> dict:
    raw = path.read_bytes()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    lines = raw.decode("latin-1").splitlines()
    meta, coords, in_sec = {}, [], False
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if s.startswith("NODE_COORD_SECTION"):
            in_sec = True
            continue
        if s.startswith("EOF"):
            break
        if in_sec:
            parts = s.split()
            if len(parts) >= 3:
                coords.append((float(parts[1]), float(parts[2])))
        elif ":" in s:
            k, v = s.split(":", 1)
            meta[k.strip()] = v.strip()
    c = np.array(coords, dtype=np.float64)
    assert meta.get("EDGE_WEIGHT_TYPE", "EUC_2D") == "EUC_2D", meta
    assert int(meta["DIMENSION"]) == len(c), (meta, len(c))
    return {"name": meta.get("NAME", path.stem), "coords": c, "meta": meta}


def euc2d_matrix(c: np.ndarray) -> np.ndarray:
    d = np.sqrt(((c[:, None, :] - c[None, :, :]) ** 2).sum(-1))
    return np.floor(d + 0.5).astype(np.int64)  # TSPLIB nint


def normalise_coords(c: np.ndarray) -> np.ndarray:
    lo = c.min(axis=0)
    rng = (c.max(axis=0) - lo).max()
    return (c - lo) / rng


def load_tsplib() -> list[dict]:
    out = []
    for name, opt in TSPLIB_OPT.items():
        p = TSPLIB_RAW / f"{name}.tsp"
        if not p.exists():
            continue
        inst = parse_tsplib(p)
        inst.update({"opt": opt, "sha256": sha256_file(p), "url": TSPLIB_SOURCE.format(name=name),
                     "D_int": euc2d_matrix(inst["coords"]),
                     "D_norm": dist_matrix(normalise_coords(inst["coords"]))})
        out.append(inst)
    return out


# ---------------------------------------------------------------- reference solver
def solve_reference(D: np.ndarray, *, integer: bool = False, runs: int = 10) -> tuple[list[int], str]:
    """LKH-3 via elkai on round(D*1e6) (or the integer matrix as given); OR-Tools GLS fallback."""
    try:
        import elkai

        M = D.astype(np.int64) if integer else np.rint(D * 1e6).astype(np.int64)
        tour = elkai.DistanceMatrix(M.tolist()).solve_tsp(runs=runs)
        tour = [int(x) for x in tour]
        if len(tour) == len(D) + 1 and tour[0] == tour[-1]:
            tour = tour[:-1]
        assert sorted(tour) == list(range(len(D))), "elkai returned an invalid permutation"
        return tour, "elkai"
    except ImportError:
        pass
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2

    n = len(D)
    M = D.astype(np.int64) if integer else np.rint(D * 1e6).astype(np.int64)
    man = pywrapcp.RoutingIndexManager(n, 1, 0)
    routing = pywrapcp.RoutingModel(man)
    cb = routing.RegisterTransitCallback(lambda i, j: int(M[man.IndexToNode(i), man.IndexToNode(j)]))
    routing.SetArcCostEvaluatorOfAllVehicles(cb)
    prm = pywrapcp.DefaultRoutingSearchParameters()
    prm.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    prm.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    prm.time_limit.seconds = 10 if n <= 100 else 30
    sol = routing.SolveWithParameters(prm)
    idx, tour = routing.Start(0), []
    while not routing.IsEnd(idx):
        tour.append(man.IndexToNode(idx))
        idx = sol.Value(routing.NextVar(idx))
    return tour, "ortools-gls"


def _ref_job(args):
    key, D, integer = args
    t0 = time.time()
    tour, solver = solve_reference(D, integer=integer)
    return key, tour, solver, time.time() - t0
