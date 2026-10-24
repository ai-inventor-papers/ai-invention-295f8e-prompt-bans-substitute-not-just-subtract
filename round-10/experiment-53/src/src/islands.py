"""FunSearch-style programs database (google-deepmind/funsearch semantics, adapted).

Per (arm, seed) search: 5 islands, each initialised with NN. Fitness F = 0.5 G50/G50(NN) + 0.5 G100/G100(NN)
(lower is better, NN = 1). Cluster key = tuple of the 64 per-instance gaps rounded to 1e-6; cluster score s = -F.
get_prompt: island uniform (rng [seed, arm, 1]); k = min(2, n_clusters) clusters drawn WITH replacement with
probability softmax(s / T_c), T_c = 0.1 (1 - (n_island mod 30000)/30000); within a cluster a program is drawn with
probability softmax(-(len - min_len)/(max_len + 1e-6)) on character length; parents sorted ascending by score.
Every VALID offspring is registered on the island of its prompt. Every 400 completed calls the 2 worst islands
(best score + 1e-6 Gaussian noise, rng stream 5) are cleared and re-seeded with the best program of an island drawn
uniformly from the 3 kept.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import numpy as np
import scipy.special

from dtb import ARM_CODE

N_ISLANDS = 5
FUNCS_PER_PROMPT = 2
T_INIT = 0.1
T_PERIOD = 30_000
RESET_EVERY = 400
N_RESET = 2


def _softmax(logits: np.ndarray, temperature: float) -> np.ndarray:
    logits = np.asarray(logits, dtype=np.float64)
    if not np.all(np.isfinite(logits)):
        raise ValueError(f"non-finite logits {logits}")
    result = scipy.special.softmax(logits / temperature, axis=-1)
    index = int(np.argmax(result))
    result[index] = 1 - np.sum(result[0:index]) - np.sum(result[index + 1:])
    return result


@dataclass
class Prog:
    pid: str            # call id "arm|seed|call" or "NN"
    body: str
    score: float        # -F
    length: int         # characters of the body


@dataclass
class Cluster:
    score: float
    programs: list[Prog] = field(default_factory=list)

    def sample(self, rng: np.random.Generator) -> Prog:
        lengths = np.array([p.length for p in self.programs], dtype=np.float64)
        normalized = (lengths - lengths.min()) / (lengths.max() + 1e-6)
        probs = _softmax(-normalized, 1.0)
        return self.programs[int(rng.choice(len(self.programs), p=probs))]


@dataclass
class Island:
    clusters: dict = field(default_factory=dict)  # signature -> Cluster
    num_programs: int = 0

    def register(self, prog: Prog, signature: tuple) -> None:
        if signature not in self.clusters:
            self.clusters[signature] = Cluster(score=prog.score)
        self.clusters[signature].programs.append(prog)
        self.num_programs += 1

    def get_prompt(self, rng: np.random.Generator) -> list[Prog]:
        sigs = list(self.clusters.keys())
        scores = np.array([self.clusters[s].score for s in sigs])
        temperature = T_INIT * (1 - (self.num_programs % T_PERIOD) / T_PERIOD)
        probs = _softmax(scores, temperature)
        k = min(len(self.clusters), FUNCS_PER_PROMPT)
        idx = rng.choice(len(sigs), size=k, p=probs)
        chosen = [self.clusters[sigs[i]] for i in idx]
        impl = [c.sample(rng) for c in chosen]
        sc = [c.score for c in chosen]
        order = np.argsort(sc, kind="stable")
        return [impl[i] for i in order]


class Database:
    def __init__(self, arm: str, seed: int, nn: Prog, nn_signature: tuple):
        self.arm, self.seed = arm, seed
        a = ARM_CODE[arm]
        self.rng_island = np.random.default_rng([seed, a, 1])
        self.rng_reset = np.random.default_rng([seed, a, 5])
        self.rng_sample = np.random.default_rng([seed, a, 6])
        self.islands = [Island() for _ in range(N_ISLANDS)]
        self.best_score = [-np.inf] * N_ISLANDS
        self.best_prog: list[Prog | None] = [None] * N_ISLANDS
        self.best_sig: list[tuple | None] = [None] * N_ISLANDS
        self.completed_calls = 0
        self.resets: list[dict] = []
        for i in range(N_ISLANDS):
            self._register_in_island(nn, i, nn_signature)

    def _register_in_island(self, prog: Prog, island: int, signature: tuple) -> None:
        self.islands[island].register(prog, signature)
        if prog.score > self.best_score[island]:
            self.best_score[island] = prog.score
            self.best_prog[island] = prog
            self.best_sig[island] = signature

    def get_prompt(self) -> tuple[int, list[Prog]]:
        island = int(self.rng_island.integers(N_ISLANDS))
        return island, self.islands[island].get_prompt(self.rng_sample)

    def complete_call(self, island: int, prog: Prog | None, signature: tuple | None) -> None:
        """Register one finished call in call order (invalid offspring are discarded but count as calls)."""
        if prog is not None:
            self._register_in_island(prog, island, signature)
        self.completed_calls += 1
        if self.completed_calls % RESET_EVERY == 0:
            self.reset_islands()

    def reset_islands(self) -> None:
        noisy = np.array(self.best_score) + self.rng_reset.standard_normal(N_ISLANDS) * 1e-6
        order = np.argsort(noisy, kind="stable")
        reset_ids, keep_ids = order[:N_RESET], order[N_RESET:]
        log = {"at_call": self.completed_calls, "reset": [int(i) for i in reset_ids], "seeded_from": []}
        for i in reset_ids:
            self.islands[int(i)] = Island()
            self.best_score[int(i)] = -np.inf
            self.best_prog[int(i)] = None
            founder = int(self.rng_reset.choice(keep_ids))
            log["seeded_from"].append(founder)
            self._register_in_island(self.best_prog[founder], int(i), self.best_sig[founder])
        self.resets.append(log)

    def snapshot(self) -> dict:
        return {"arm": self.arm, "seed": self.seed, "completed_calls": self.completed_calls, "resets": self.resets,
                "best_score": [float(s) for s in self.best_score],
                "best_pid": [p.pid if p else None for p in self.best_prog],
                "islands": [{"num_programs": isl.num_programs, "n_clusters": len(isl.clusters),
                             "clusters": [{"score": c.score, "pids": [p.pid for p in c.programs]}
                                          for c in isl.clusters.values()]} for isl in self.islands]}

    def snapshot_json(self) -> str:
        return json.dumps(self.snapshot(), sort_keys=True)
