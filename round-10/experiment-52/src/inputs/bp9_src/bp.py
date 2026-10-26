#!/usr/bin/env python3
"""Exact FunSearch online bin-packing harness, instance sets, textbook/published heuristics and selection fitness.

Semantics copied from google-deepmind/funsearch bin_packing.ipynb (commit 2a2c864):
bins are pre-allocated (one per item, all at full capacity, int dtype); priority(item, bins[valid]) scores every
bin that fits (unused bins included); the item goes to valid[np.argmax(priorities)] (first index on ties, first NaN
if any NaN); score = number of bins whose remaining capacity != capacity.
"""
from __future__ import annotations

import ast
import hashlib
import json
import math
from pathlib import Path
from typing import Callable

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
INST_DIR = ROOT / "data" / "instances"
EXT = ROOT / "ext"


class ShapeError(Exception):
    """Priority output is not a 1-D array with one score per valid bin."""


# ----------------------------------------------------------------------------------------------- harness
def valid(item: int, bins: np.ndarray) -> np.ndarray:
    return np.nonzero((bins - item) >= 0)[0]


def pack(items: list[int], cap: int, prio: Callable) -> int:
    """Pack `items` online with FunSearch semantics; return the number of used bins."""
    bins = np.array([cap for _ in range(len(items))])
    for it in items:
        v = np.nonzero(bins >= it)[0]  # identical to (bins - item) >= 0 for integer data
        p = np.asarray(prio(it, bins[v]))
        if p.ndim != 1 or p.shape[0] != v.shape[0]:
            raise ShapeError(f"priority returned shape {p.shape} for {v.shape[0]} valid bins")
        b = v[np.argmax(p)]
        bins[b] -= it
    return int((bins != cap).sum())


def pack_trace(items: list[int], cap: int, prio: Callable) -> tuple[int, list[tuple[int, list[int], int, int]]]:
    """Pack and record states: (item, remaining caps of opened bins that fit in index order, n_empty, chosen cap)."""
    n = len(items)
    bins = np.array([cap for _ in range(n)])
    used = np.zeros(n, dtype=bool)
    states = []
    for it in items:
        v = np.nonzero(bins >= it)[0]
        vb = bins[v]
        p = np.asarray(prio(it, vb))
        b = v[np.argmax(p)]
        opened_fit = [int(x) for x, u in zip(vb, used[v]) if u]
        n_empty = int((~used).sum())
        states.append((int(it), opened_fit, n_empty, int(bins[b])))
        bins[b] -= it
        used[b] = True
    return int(used.sum()), states


def l1(items: list[int], cap: int) -> int:
    return int(math.ceil(sum(items) / cap))


def family_excess(bins: list[int] | np.ndarray, l1s: list[int] | np.ndarray) -> float:
    """FunSearch's excess: (mean bins - mean L1) / mean L1 over a family of instances."""
    mb, ml = float(np.mean(bins)), float(np.mean(l1s))
    return (mb - ml) / ml


# ----------------------------------------------------------------------------------------------- instances
def weibull_items(rng: np.random.Generator, n: int, shape: float = 3.0, scale: float = 45.0, hi: int = 100) -> list[int]:
    x = np.clip(np.round(rng.weibull(shape, size=n) * scale), 1, hi).astype(int)
    return [int(v) for v in x]


def uniform_items(rng: np.random.Generator, n: int, lo: int = 20, hi: int = 100) -> list[int]:
    return [int(v) for v in rng.integers(lo, hi + 1, size=n)]


def _inst(name: str, cap: int, items: list[int]) -> dict:
    return {"id": name, "capacity": int(cap), "num_items": len(items), "items": items, "l1": l1(items, cap)}


def gen_sets() -> dict[str, list[dict]]:
    """All generated instance sets (seeds fixed in the plan)."""
    s: dict[str, list[dict]] = {}
    s["SEL-OR"] = [_inst(f"selor_{i}", 150, uniform_items(np.random.default_rng(91001 + i), 120)) for i in range(20)]
    s["SEL-W"] = [_inst(f"selw_{i}", 100, weibull_items(np.random.default_rng(92001 + i), 5000)) for i in range(5)]
    s["H-W5k"] = [_inst(f"hw5k_{i}", 100, weibull_items(np.random.default_rng(93001 + i), 5000)) for i in range(5)]
    s["H-W10k"] = [_inst(f"hw10k_{i}", 100, weibull_items(np.random.default_rng(94001 + i), 10000)) for i in range(5)]
    s["H-SHIFT"] = [_inst(f"hshift_{i}", 150, weibull_items(np.random.default_rng(97001 + i), 5000, 7.0, 75.0, 150))
                    for i in range(5)]
    s["CALIB-W"] = [_inst(f"calw_{i}", 100, weibull_items(np.random.default_rng(99001 + i), 5000)) for i in range(20)]
    s["P1SRC-W"] = [_inst(f"p1w_{i}", 100, weibull_items(np.random.default_rng(95001 + i), 5000)) for i in range(5)]
    s["P1SRC-OR"] = [_inst(f"p1or_{i}", 150, uniform_items(np.random.default_rng(96001 + i), 500)) for i in range(5)]
    return s


def parse_orlib(path: Path) -> list[dict]:
    tok = path.read_text().split()
    p = int(tok[0])
    out, k = [], 1
    for _ in range(p):
        name = tok[k]
        cap, n, best = int(float(tok[k + 1])), int(tok[k + 2]), int(tok[k + 3])
        items = [int(float(x)) for x in tok[k + 4:k + 4 + n]]
        k += 4 + n
        d = _inst(name, cap, items)
        d["best_known"] = best
        out.append(d)
    return out


def funsearch_notebook() -> tuple[dict, dict, str, str]:
    """Return (OR3 dict, Weibull 5k dict, OR heuristic source, Weibull heuristic source) parsed as data."""
    nb = json.loads((EXT / "funsearch" / "bin_packing.ipynb").read_text())
    src = "".join(nb["cells"][2]["source"])
    tree = ast.parse(src)
    data = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Subscript):
            key = ast.literal_eval(node.targets[0].slice)
            data[key] = ast.literal_eval(node.value)
    or_src = "".join(nb["cells"][8]["source"]).split("\n\n\n# Test performance")[0]
    w_src = "".join(nb["cells"][9]["source"]).split("\n\n\n# Test performance")[0]
    return data["OR3"], data["Weibull 5k"], or_src, w_src


def nb_dict_to_insts(d: dict) -> list[dict]:
    return [_inst(k, v["capacity"], [int(x) for x in v["items"]]) for k, v in d.items()]


def sha_insts(insts: list[dict]) -> str:
    h = hashlib.sha256()
    for x in insts:
        h.update(json.dumps([x["id"], x["capacity"], x["items"]]).encode())
    return h.hexdigest()


def build_all_sets() -> dict[str, list[dict]]:
    sets = gen_sets()
    for i in range(1, 5):
        sets[f"H-OR{i}"] = parse_orlib(EXT / "orlib" / f"binpack{i}.txt")
    or3, w5k, _, _ = funsearch_notebook()
    sets["FS-OR3"] = nb_dict_to_insts(or3)
    sets["H-FSW5k"] = nb_dict_to_insts(w5k)
    return sets


def save_sets(sets: dict[str, list[dict]]) -> dict[str, str]:
    INST_DIR.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name, insts in sets.items():
        (INST_DIR / f"{name}.json").write_text(json.dumps(insts))
        hashes[name] = sha_insts(insts)
    return hashes


def load_set(name: str) -> list[dict]:
    return json.loads((INST_DIR / f"{name}.json").read_text())


# ----------------------------------------------------------------------------------------------- heuristics
def prio_ff(item, bins):
    return -np.arange(len(bins))


def prio_bf(item, bins):
    return -(bins - item)


def prio_wf(item, bins):
    score = (bins - item).astype(float)
    m = bins == bins.max()
    if not m.all():
        score[m] = -1e9
    return score


def prio_c12_vec(item, bins):
    """Vectorised exact equivalent of FunSearch's OR heuristic (c12)."""
    g = bins - item
    return np.select([g <= 2, g <= 3, g <= 5, g <= 7, g <= 9, g <= 12, g <= 15, g <= 18, g <= 20, g <= 21],
                     [4, 3, 2, 1, 0.9, 0.95, 0.97, 0.98, 0.98, 0.98], 0.99)


def prio_c14(item, bins):
    max_bin_cap = max(bins)
    score = (bins - max_bin_cap) ** 2 / item + bins ** 2 / (item ** 2)
    score += bins ** 2 / item ** 3
    score[bins > item] = -score[bins > item]
    score[1:] -= score[:-1]
    return score


def make_ab(a: int, b: int, base: str) -> Callable:
    """ab-heuristics of Herrmann & Pallez (arXiv 2510.27353, Algorithms 4-6); capacity = bins.max() (an unused bin
    at full capacity is always among the valid bins in the pre-allocated harness)."""
    def prio(item, bins):
        cap = bins.max()
        with np.errstate(divide="ignore", invalid="ignore"):
            first = cap - bins + 1
            if base == "FF":
                return np.where(bins <= item + a, first, np.where(bins < item + b, -2, 1))
            if base == "BF":
                return np.where(bins <= item + a, first, np.where(bins < item + b, -2.0, 1.0 / (bins - item)))
            return np.where(bins <= item + a, first, np.where(bins <= item + b, -2.0,
                                                              np.where(bins == cap, -1.0, -1.0 / (bins - item))))
    prio.__name__ = f"ab{base}_{a}_{b}"
    return prio


def ab_source(a: int, b: int, base: str) -> str:
    """Program text of an ab member in the search's program format (for probes/corpus)."""
    if base == "FF":
        tail = "np.where(bins < item + b, -2, 1)"
    elif base == "BF":
        tail = "np.where(bins < item + b, -2.0, 1.0 / (bins - item))"
    else:
        tail = "np.where(bins <= item + b, -2.0, np.where(bins == cap, -1.0, -1.0 / (bins - item)))"
    return (f"def priority(item, bins):\n    a, b = {a}, {b}\n    cap = bins.max()\n"
            f"    with np.errstate(divide='ignore', invalid='ignore'):\n"
            f"        return np.where(bins <= item + a, cap - bins + 1, {tail})\n")


SRC_FF = "def priority(item, bins):\n    return -np.arange(len(bins))\n"
SRC_BF = "def priority(item, bins):\n    return -(bins - item)\n"
SRC_WF = ("def priority(item, bins):\n    score = (bins - item).astype(float)\n    m = bins == bins.max()\n"
          "    if not m.all():\n        score[m] = -1e9\n    return score\n")


def harmonic_k(items: list[int], cap: int, k: int) -> int:
    """Lee & Lee Harmonic-k (standalone, stateful): class j<k items (cap/(j+1) < s <= cap/j) packed j per bin;
    class-k items (s <= cap/k) packed by Next Fit in their own bins."""
    count = {j: 0 for j in range(1, k)}
    bins_used = 0
    nf_rem = None
    for s in items:
        j = next((j for j in range(1, k) if s * (j + 1) > cap and s * j <= cap), k)
        if j < k:
            if count[j] == 0:
                bins_used += 1
            count[j] = (count[j] + 1) % j
        else:
            if nf_rem is None or nf_rem < s:
                bins_used += 1
                nf_rem = cap
            nf_rem -= s
    return bins_used


# ----------------------------------------------------------------------------------------------- fitness
class Fitness:
    """F = 0.5*exc_OR/exc_OR(BF) + 0.5*exc_W/exc_W(BF) on the 25 selection instances (lower is better, F(BF)=1)."""

    def __init__(self, sel_or: list[dict], sel_w: list[dict], bf_or_exc: float, bf_w_exc: float):
        self.l1_or = [x["l1"] for x in sel_or]
        self.l1_w = [x["l1"] for x in sel_w]
        self.n_or = len(sel_or)
        self.bf_or_exc, self.bf_w_exc = bf_or_exc, bf_w_exc

    def parts(self, bins25: list[int]) -> tuple[float, float]:
        return family_excess(bins25[:self.n_or], self.l1_or), family_excess(bins25[self.n_or:], self.l1_w)

    def F(self, bins25: list[int]) -> float:
        eo, ew = self.parts(bins25)
        return 0.5 * eo / self.bf_or_exc + 0.5 * ew / self.bf_w_exc


def eval_set(insts: list[dict], prio: Callable) -> list[int]:
    return [pack(x["items"], x["capacity"], prio) for x in insts]
