#!/usr/bin/env python3
"""S6 island database (FunSearch-style): 5 islands per arm-seed seeded with BF; clusters = identical signatures (the
tuple of 25 selection bin counts), cluster score = -F; parent draw = uniform island, 2 clusters with replacement by
softmax(score / T_c) with T_c = 0.1 * (1 - (n_island mod 30000) / 30000), a length-preferring draw within a cluster,
pair sorted by score (worse = priority_v0); reset of the 2 worst islands after every 400 calls."""
from __future__ import annotations

import numpy as np

import common as C

N_ISLANDS = 5
T_INIT = 0.1
PERIOD = 30000
RESET_EVERY = 400
N_RESET = 2


def softmax(x: np.ndarray, T: float) -> np.ndarray:
    z = np.asarray(x, dtype=np.float64) / T
    z = z - z.max()
    p = np.exp(z)
    return p / p.sum()


class Island:
    def __init__(self):
        self.clusters: dict[tuple, list[dict]] = {}
        self.n = 0

    def register(self, prog: dict) -> None:
        self.clusters.setdefault(tuple(prog["sig"]), []).append(prog)
        self.n += 1

    def best(self) -> dict:
        best = None
        for members in self.clusters.values():
            for m in members:
                if best is None or -m["F"] > -best["F"]:
                    best = m
        return best


class ArmDB:
    def __init__(self, S: int, arm: str, seed_prog: dict):
        self.S, self.arm = S, arm
        self.rng = np.random.default_rng([S, C.ARM_IDS[arm], 1])
        self.islands = [Island() for _ in range(N_ISLANDS)]
        for isl in self.islands:
            isl.register(dict(seed_prog))
        self.calls = 0
        self.resets: list[dict] = []
        self.n_registered = 0

    def draw_parents(self) -> tuple[int, dict, dict]:
        i = int(self.rng.integers(N_ISLANDS))
        isl = self.islands[i]
        sigs = list(isl.clusters.keys())
        scores = np.array([-isl.clusters[s][0]["F"] for s in sigs])
        T_c = T_INIT * (1 - (isl.n % PERIOD) / PERIOD)
        p = softmax(scores, T_c)
        picks = self.rng.choice(len(sigs), size=2, p=p)
        progs = []
        for ci in picks:
            members = isl.clusters[sigs[int(ci)]]
            lens = np.array([len(m["code"]) for m in members], dtype=np.float64)
            q = softmax(-(lens - lens.min()) / (lens.max() + 1e-6), 1.0)
            progs.append(members[int(self.rng.choice(len(members), p=q))])
        order = np.argsort([-progs[0]["F"], -progs[1]["F"]], kind="stable")  # ascending score: worse first
        return i, progs[int(order[0])], progs[int(order[1])]

    def register(self, island: int, prog: dict) -> None:
        self.islands[island].register(prog)
        self.n_registered += 1

    def maybe_reset(self) -> dict | None:
        """Called after each round's registration with the arm-seed's cumulative call count."""
        due = self.calls // RESET_EVERY
        if due <= len(self.resets):
            return None
        best = np.array([-isl.best()["F"] for isl in self.islands])
        order = np.argsort(best + self.rng.standard_normal(N_ISLANDS) * 1e-6)
        reset_ids, keep_ids = order[:N_RESET], order[N_RESET:]
        ev = {"at_calls": self.calls, "reset": [int(x) for x in reset_ids], "founders": []}
        for rid in reset_ids:
            founder_isl = int(self.rng.choice(keep_ids))
            founder = self.islands[founder_isl].best()
            self.islands[int(rid)] = Island()
            self.islands[int(rid)].register(dict(founder))
            ev["founders"].append([int(rid), founder_isl, founder["pid"]])
        self.resets.append(ev)
        return ev

    def best(self) -> dict:
        return min((isl.best() for isl in self.islands), key=lambda m: m["F"])

    def state_summary(self) -> dict:
        return {"calls": self.calls, "n_registered": self.n_registered,
                "island_sizes": [isl.n for isl in self.islands],
                "island_clusters": [len(isl.clusters) for isl in self.islands],
                "best_F": [round(isl.best()["F"], 6) for isl in self.islands], "n_resets": len(self.resets)}
