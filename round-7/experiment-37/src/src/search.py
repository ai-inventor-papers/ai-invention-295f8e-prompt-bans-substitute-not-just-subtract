#!/usr/bin/env python3
"""FunSearch / MAP-Elites program database: 4 islands, each an archive {cell -> elite}.

CELL = (runtime label, DS-signature). ELITE = the correct program with the highest novelty nu (tie-break: lower runtime
ratio, then shorter code). PARENTS: 2 distinct cells drawn with p(c) ~ exp(nu_c / tau_t),
tau_t = 0.1 * (1 - (t mod 500) / 500) + 0.01 (FunSearch's periodic schedule scaled to this budget), t = S calls so far;
with fewer than 2 cells, draw with replacement. RESET: every 500 S calls the island with the lowest best-elite nu is
cleared and re-seeded with the best elite of a uniformly drawn other island plus the catalogue references.
"""

from __future__ import annotations

import math
import random
from typing import Any

N_ISLANDS = 4
PROMPTS_PER_ISLAND = 3
CHILDREN_PER_PROMPT = 4
RESET_EVERY = 500
TAU0 = 0.1
TAU_MIN = 0.01


def tau_at(t: int) -> float:
    return TAU0 * (1.0 - (t % RESET_EVERY) / RESET_EVERY) + TAU_MIN


def cell_key(runtime_label: str | None, ds_sig: str | None) -> str:
    return f"{runtime_label or 'unknown'}|{ds_sig or 'none'}"


def better(a: dict[str, Any], b: dict[str, Any] | None) -> bool:
    """Is program a a better elite than the current elite b?"""
    if b is None:
        return True
    if a["novelty"] != b["novelty"]:
        return a["novelty"] > b["novelty"]
    ra, rb = a.get("runtime_ratio") or 1e9, b.get("runtime_ratio") or 1e9
    if ra != rb:
        return ra < rb
    return len(a["code"]) < len(b["code"])


class Island:
    def __init__(self, idx: int) -> None:
        self.idx = idx
        self.cells: dict[str, dict[str, Any]] = {}

    def offer(self, prog: dict[str, Any]) -> bool:
        c = prog["cell"]
        if better(prog, self.cells.get(c)):
            self.cells[c] = prog
            return True
        return False

    def best_nu(self) -> float:
        return max((e["novelty"] for e in self.cells.values()), default=0.0)

    def qd_score(self) -> float:
        return float(sum(e["novelty"] for e in self.cells.values()))


class SearchDB:
    def __init__(self, seeds: list[dict[str, Any]], rng_seed: int, n_islands: int = N_ISLANDS) -> None:
        self.seeds = seeds
        self.islands = [Island(i) for i in range(n_islands)]
        for isl in self.islands:
            for s in seeds:
                isl.offer(dict(s))
        self.t = 0
        self.rng = random.Random(rng_seed)
        self.resets: list[dict[str, Any]] = []
        self.history: list[dict[str, Any]] = []
        self.archive_reads = 0

    # ------------------------------------------------------------------------------------------- parents
    def pick_parents(self, island: int) -> list[dict[str, Any]]:
        self.archive_reads += 1
        cells = list(self.islands[island].cells.values())
        tau = tau_at(self.t)
        if len(cells) == 1:
            return [cells[0], cells[0]]
        m = max(e["novelty"] for e in cells)
        w = [math.exp((e["novelty"] - m) / tau) for e in cells]
        first = self._draw(cells, w)
        rest = [(e, x) for e, x in zip(cells, w) if e is not first]
        second = self._draw([e for e, _ in rest], [x for _, x in rest])
        return [first, second]

    def _draw(self, items: list[dict[str, Any]], w: list[float]) -> dict[str, Any]:
        tot = sum(w)
        u = self.rng.random() * tot
        acc = 0.0
        for it, x in zip(items, w):
            acc += x
            if u <= acc:
                return it
        return items[-1]

    # ------------------------------------------------------------------------------------------- updates
    def offer(self, island: int, prog: dict[str, Any]) -> bool:
        return self.islands[island].offer(prog)

    def advance(self, n_calls: int) -> list[dict[str, Any]]:
        """Advance the S call counter; run every reset whose 500-call boundary was crossed."""
        before = self.t
        self.t += n_calls
        done = []
        for b in range((before // RESET_EVERY) + 1, (self.t // RESET_EVERY) + 1):
            done.append(self.reset(at_call=b * RESET_EVERY))
        return done

    def reset(self, at_call: int) -> dict[str, Any]:
        worst = min(range(len(self.islands)), key=lambda i: (self.islands[i].best_nu(), i))
        others = [i for i in range(len(self.islands)) if i != worst]
        donor = self.rng.choice(others)
        best = max(self.islands[donor].cells.values(), key=lambda e: (e["novelty"], -(e.get("runtime_ratio") or 1e9)))
        isl = Island(worst)
        for s in self.seeds:
            isl.offer(dict(s))
        isl.offer(dict(best))
        self.islands[worst] = isl
        rec = {"at_call": at_call, "reset_island": worst, "donor_island": donor, "donor_elite": best["id"],
               "donor_nu": best["novelty"]}
        self.resets.append(rec)
        return rec

    def snapshot(self) -> dict[str, Any]:
        return {"t": self.t, "islands": [{"idx": i.idx, "n_cells": len(i.cells), "qd_score": round(i.qd_score(), 4),
                                          "best_nu": round(i.best_nu(), 4),
                                          "cells": {c: {"id": e["id"], "novelty": e["novelty"],
                                                        "runtime_label": e.get("runtime_label"),
                                                        "ds_signature": e.get("ds_signature"),
                                                        "origin": e.get("origin"), "depth": e.get("depth", 0)}
                                                    for c, e in i.cells.items()}}
                                         for i in self.islands], "resets": self.resets}

    def state(self) -> dict[str, Any]:
        return {"t": self.t, "rng": self.rng.getstate(), "resets": self.resets, "history": self.history,
                "islands": [{"idx": i.idx, "cells": i.cells} for i in self.islands]}

    def load_state(self, st: dict[str, Any]) -> None:
        self.t = st["t"]
        r = st["rng"]
        self.rng.setstate((r[0], tuple(r[1]), r[2]))
        self.resets = st["resets"]
        self.history = st.get("history", [])
        self.islands = []
        for d in st["islands"]:
            isl = Island(d["idx"])
            isl.cells = d["cells"]
            self.islands.append(isl)


class FrozenSeedPool:
    """NE parent source: 2 distinct seed references drawn uniformly; never reads or writes the archive."""

    def __init__(self, seeds: list[dict[str, Any]], rng_seed: int) -> None:
        self.seeds = seeds
        self.rng = random.Random(rng_seed)

    def pick_parents(self) -> list[dict[str, Any]]:
        a, b = self.rng.sample(range(len(self.seeds)), 2)
        return [self.seeds[a], self.seeds[b]]
