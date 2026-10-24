#!/usr/bin/env python3
"""FunSearch programs_database semantics (functions_per_prompt 2, cluster temperature init 0.1, period 30,000),
scaled to 5 islands with a reset of the worst 2 every 400 calls of an arm-seed.

Score s = -100 F (higher is better); signature = tuple of the 25 per-instance bin counts. Parent sampling uses
default_rng([seed, arm_idx, 1]); resets use default_rng([seed, arm_idx, 2]).
NS has no database: parents are fixed as FF (v0) and BF (v1) and offspring are never registered."""
from __future__ import annotations

import numpy as np

N_ISLANDS, FUNCS_PER_PROMPT, T_INIT, T_PERIOD, RESET_EVERY = 5, 2, 0.1, 30000, 400
SCORE_SCALE = -100.0


def softmax(logits: np.ndarray, temperature: float) -> np.ndarray:
    """FunSearch's _softmax: scipy-style softmax of logits / temperature, renormalised at the argmax."""
    x = np.asarray(logits, dtype=np.float64) / temperature
    x = x - x.max()
    p = np.exp(x)
    p /= p.sum()
    i = int(np.argmax(p))
    p[i] = 1.0 - (p[:i].sum() + p[i + 1:].sum())
    return p


class Cluster:
    def __init__(self, score: float, prog: dict):
        self.score = score
        self.programs = [prog]
        self.lengths = [len(prog["code"])]

    def register(self, prog: dict) -> None:
        self.programs.append(prog)
        self.lengths.append(len(prog["code"]))

    def sample(self, rng: np.random.Generator) -> dict:
        L = np.array(self.lengths, dtype=np.float64)
        p = softmax(-(L - L.min()) / (L.max() + 1e-6), 1.0)
        return self.programs[int(rng.choice(len(self.programs), p=p))]


class Island:
    def __init__(self):
        self.clusters: dict[tuple, Cluster] = {}
        self.n_programs = 0

    def register(self, prog: dict, score: float, sig: tuple) -> None:
        if sig in self.clusters:
            self.clusters[sig].register(prog)
        else:
            self.clusters[sig] = Cluster(score, prog)
        self.n_programs += 1

    def get_prompt_parents(self, rng: np.random.Generator) -> list[dict]:
        sigs = list(self.clusters.keys())
        scores = np.array([self.clusters[s].score for s in sigs])
        temp = T_INIT * (1 - (self.n_programs % T_PERIOD) / T_PERIOD)
        p = softmax(scores, temp)
        k = min(len(self.clusters), FUNCS_PER_PROMPT)
        idx = rng.choice(len(sigs), size=k, p=p)  # with replacement, as FunSearch
        chosen = [(self.clusters[sigs[i]].sample(rng), self.clusters[sigs[i]].score) for i in idx]
        order = np.argsort([s for _, s in chosen], kind="stable")  # worse first
        return [chosen[i][0] for i in order]


class Database:
    """One programs database per (seed, arm)."""

    def __init__(self, seed: int, arm_idx: int, seed_prog: dict, seed_score: float, seed_sig: tuple):
        self.rng_parents = np.random.default_rng([seed, arm_idx, 1])
        self.rng_reset = np.random.default_rng([seed, arm_idx, 2])
        self.islands = [Island() for _ in range(N_ISLANDS)]
        self.best_score = [-np.inf] * N_ISLANDS
        self.best_prog: list[dict | None] = [None] * N_ISLANDS
        self.best_sig: list[tuple | None] = [None] * N_ISLANDS
        for i in range(N_ISLANDS):
            self.register(seed_prog, seed_score, seed_sig, i)
        self.n_resets = 0
        self.log: list[dict] = []

    def register(self, prog: dict, score: float, sig: tuple, island: int) -> None:
        self.islands[island].register(prog, score, sig)
        if score > self.best_score[island]:
            self.best_score[island] = score
            self.best_prog[island] = prog
            self.best_sig[island] = sig

    def draw(self) -> tuple[int, list[dict]]:
        isl = int(self.rng_parents.integers(0, N_ISLANDS))
        return isl, self.islands[isl].get_prompt_parents(self.rng_parents)

    def reset(self) -> dict:
        noisy = np.array(self.best_score) + self.rng_reset.standard_normal(N_ISLANDS) * 1e-6
        order = np.argsort(noisy, kind="stable")
        n_reset = N_ISLANDS // 2
        reset_ids, keep_ids = order[:n_reset], order[n_reset:]
        ev = {"reset": [int(x) for x in reset_ids], "founders": []}
        for isl in reset_ids:
            isl = int(isl)
            founder = int(self.rng_reset.choice(keep_ids))
            prog, score, sig = self.best_prog[founder], self.best_score[founder], self.best_sig[founder]
            self.islands[isl] = Island()
            self.best_score[isl] = -np.inf
            self.best_prog[isl] = None
            self.register(prog, score, sig, isl)
            ev["founders"].append([isl, founder, prog["pid"], float(score)])
        self.n_resets += 1
        self.log.append(ev)
        return ev

    def n_clusters(self) -> list[int]:
        return [len(i.clusters) for i in self.islands]
