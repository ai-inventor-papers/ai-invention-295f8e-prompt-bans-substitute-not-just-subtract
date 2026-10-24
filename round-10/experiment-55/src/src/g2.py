#!/usr/bin/env python3
"""G2 (plan Stage 5, frozen in COMMIT1c): where do the five-name-ban survivor families land on a frame built from the
factorial cells plus the ten-algorithm catalogue? Built on iteration 9's geometry.py unchanged (knn_graph,
geodesics, g_values, classify) and its out-of-sample rule (stage_analysis.oos, copied verbatim in r0.py).

Frame F = factorial programs (label = cell) + catalogue programs (129 iteration-9 M-code PRIMARY programs + verified
top-ups; label = algorithm); classes with >= 10 programs. BANNED = bfs, dfs, iddfs, astar, gbfs + every BFSO / DFSO /
HEUR cell; NON-BANNED = dijkstra_unit, idastar, bibfs, jps, biastar + every COST / RELAX / RAND cell.
Placement: attach x to its k nearest frame programs (Euclidean, raw R1), geodesic to every frame program =
min_nn(|x - nn| + geo[nn, :]) through the fixed frame graph (no edges between placed programs); d(a, C) = mean
geodesic to C; g(a) = min over banned C; nearest class = argmin_C d(a, C).
r_F = median_{a in F} g(a) / median over the non-banned frame classes of the class g (geometry.g_values); EDGE if
r_F < 1, OPPOSITE if r_F > 1; robust if the family-bootstrap 95% CI of r_F excludes 1."""

from __future__ import annotations

import math
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from typing import Any

import numpy as np
from scipy.stats import binomtest

import geometry
import v10
from r0 import oos

ALG_DISC = {"bfs": "BFSO", "bibfs": "BFSO", "dfs": "DFSO", "iddfs": "DFSO", "astar": "HEUR", "gbfs": "HEUR",
            "jps": "HEUR", "biastar": "HEUR", "idastar": "HEUR", "dijkstra_unit": "COST"}


def disc_of(label: str) -> str:
    return label.split("-")[0] if "-" in label else ALG_DISC.get(label, "OTHER")


def cont_of(label: str, ast_cont: str | None = None) -> str:
    return label.split("-")[1] if "-" in label else (ast_cont or "OTHER")


def is_banned(label: str) -> bool:
    return (label in v10.BANNED_ALGS) or ("-" in label and label.split("-")[0] in v10.BANNED_DISC)


def is_nonbanned(label: str) -> bool:
    return (label in v10.NONBANNED_ALGS) or ("-" in label and label.split("-")[0] in v10.NONBANNED_DISC)


def wilson(k: int, n: int, z: float = 1.959963984540054) -> list[float]:
    if n <= 0:
        return [float("nan"), float("nan")]
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [max(0.0, c - h), min(1.0, c + h)]


# ---------------------------------------------------------------------------------------------- frame
class Frame:
    def __init__(self, X: np.ndarray, labels: np.ndarray, meta: list[dict[str, Any]], k: int, name: str) -> None:
        self.X, self.labels, self.meta, self.k, self.name = X, labels, meta, k, name
        self.geo, self.info = geometry.geodesics(X, k)
        self.classes = sorted(set(labels.tolist()))
        self.banned = [c for c in self.classes if is_banned(c)]
        self.nonbanned = [c for c in self.classes if is_nonbanned(c)]
        if self.banned and self.nonbanned:
            self.class_g, self.class_near = geometry.g_values(self.geo, labels, self.banned, self.nonbanned)
            self.median = float(np.median(list(self.class_g.values())))
            cat_nb = [c for c in self.nonbanned if "-" not in c]
            self.median_catalogue = float(np.median([self.class_g[c] for c in cat_nb])) if cat_nb else None
        else:
            self.class_g, self.class_near, self.median, self.median_catalogue = {}, {}, None, None

    def place(self, x: np.ndarray) -> dict[str, Any]:
        dv = oos(x, self.X, self.geo, self.k)
        d = {c: float(dv[self.labels == c].mean()) for c in self.classes}
        near = min(d, key=d.get)
        out = {"d": d, "nearest_class": near, "nearest_discipline": disc_of(near),
               "nearest_container": self.meta_cont.get(near, cont_of(near))}
        if self.banned:
            gb = {c: d[c] for c in self.banned}
            out["g"] = min(gb.values())
            out["nearest_banned"] = min(gb, key=gb.get)
            out["nearest_is_banned"] = is_banned(near)
            if self.median is not None:
                out["class"] = "EDGE" if out["g"] < self.median - 1e-12 else (
                    "OPPOSITE" if out["g"] > self.median + 1e-12 else "MIDDLE")
        return out

    @property
    def meta_cont(self) -> dict[str, str]:
        if not hasattr(self, "_mc"):
            self._mc = {}
            for lab, m in zip(self.labels, self.meta):
                self._mc.setdefault(str(lab), m.get("container") or cont_of(str(lab)))
        return self._mc

    def summary(self) -> dict[str, Any]:
        return {"name": self.name, "n": int(len(self.X)), "k": self.k, "classes": {c: int((self.labels == c).sum())
                                                                                   for c in self.classes},
                "banned": self.banned, "nonbanned": self.nonbanned, "class_g": self.class_g,
                "class_nearest_banned": self.class_near, "median_nonbanned_class_g": self.median,
                "median_nonbanned_catalogue_g": self.median_catalogue, **self.info}


def subframe(fr: Frame, keep: np.ndarray, name: str, min_class: int = 10) -> Frame | None:
    labs = fr.labels[keep]
    ok = np.array([int((labs == c).sum()) >= min_class for c in labs])
    idx = np.where(keep)[0][ok]
    if len(set(fr.labels[idx].tolist())) < 2:
        return None
    return Frame(fr.X[idx], fr.labels[idx], [fr.meta[i] for i in idx], fr.k, name)


# ---------------------------------------------------------------------------------------------- family statistics
def family_stats(fr: Frame, placed: list[dict[str, Any]], n_boot: int = 1000, seed: int = 0) -> dict[str, Any]:
    gs = np.array([p["g"] for p in placed if "g" in p])
    out: dict[str, Any] = {"n": len(placed)}
    if not len(placed):
        return out
    near = [p["nearest_class"] for p in placed]
    out["nearest_class_counts"] = {c: near.count(c) for c in sorted(set(near))}
    nd = [p["nearest_discipline"] for p in placed]
    out["nearest_discipline_counts"] = {c: nd.count(c) for c in sorted(set(nd))}
    nc = [p["nearest_container"] for p in placed]
    out["nearest_container_counts"] = {c: nc.count(c) for c in sorted(set(nc))}
    if len(gs) and fr.median:
        rF = float(np.median(gs) / fr.median)
        rng = np.random.default_rng(seed)
        boots = [float(np.median(rng.choice(gs, size=len(gs), replace=True)) / fr.median) for _ in range(n_boot)]
        lo, hi = float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))
        out.update({"median_g": float(np.median(gs)), "frame_median": fr.median, "r_F": rF, "r_F_ci95": [lo, hi],
                    "verdict": "EDGE" if rF < 1 else ("OPPOSITE" if rF > 1 else "MIDDLE"),
                    "robust": bool(hi < 1 or lo > 1), "descriptive_only": len(placed) < v10.CLASS_FLOOR,
                    "share_EDGE_programs": float(np.mean([p.get("class") == "EDGE" for p in placed])),
                    "r_F_catalogue_median": float(np.median(gs) / fr.median_catalogue) if fr.median_catalogue else None,
                    "g_quantiles": np.quantile(gs, [0.1, 0.25, 0.5, 0.75, 0.9]).tolist()})
        kb = sum(p.get("nearest_is_banned", False) for p in placed)
        out["share_nearest_banned"] = kb / len(placed)
        out["share_nearest_banned_wilson"] = wilson(kb, len(placed))
    return out


def contrast(placed: list[dict[str, Any]], a_classes: list[str], b_classes: list[str]) -> dict[str, Any]:
    """share of programs with min_a d(x, A) < min_b d(x, B); exact one-sided sign test against 0.5."""
    wins, n = 0, 0
    for p in placed:
        da = [p["d"][c] for c in a_classes if c in p["d"]]
        db = [p["d"][c] for c in b_classes if c in p["d"]]
        if not da or not db:
            continue
        n += 1
        wins += int(min(da) < min(db))
    if n == 0:
        return {"n": 0}
    return {"n": n, "wins": wins, "share": wins / n, "sign_test_p_greater": float(binomtest(wins, n, 0.5,
                                                                                         "greater").pvalue),
            "A": a_classes, "B": b_classes}


# ---------------------------------------------------------------------------------------------- LOO
def _loo_one(args: tuple) -> tuple[int, str, str | None]:
    i, X, labels, k = args
    import geometry as gm
    from r0 import oos as _oos

    keep = np.ones(len(X), bool)
    keep[i] = False
    geo, _ = gm.geodesics(X[keep], k)
    dv = _oos(X[i], X[keep], geo, k)
    lab = labels[keep]
    means = {c: float(dv[lab == c].mean()) for c in sorted(set(lab.tolist()))}
    near = min(means, key=means.get)
    other = {c: v for c, v in means.items() if c != labels[i]}
    return i, near, (min(other, key=other.get) if other else None)


def loo(fr: Frame, workers: int = 5) -> dict[str, Any]:
    items = [(i, fr.X, fr.labels, fr.k) for i in range(len(fr.X))]
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn")) as ex:
        res = list(ex.map(_loo_one, items, chunksize=8))
    acc = np.mean([near == fr.labels[i] for i, near, _ in res])
    dacc = np.mean([disc_of(near) == disc_of(str(fr.labels[i])) for i, near, _ in res])
    nb = [(i, other) for i, _near, other in res if is_nonbanned(str(fr.labels[i])) and other is not None]
    fi = float(np.mean([is_banned(o) for _, o in nb])) if nb else None
    nb_cells = [(i, o) for i, o in nb if "-" in str(fr.labels[i])]
    nb_cat = [(i, o) for i, o in nb if "-" not in str(fr.labels[i])]
    return {"class_loo_accuracy": float(acc), "discipline_loo_accuracy": float(dacc), "chance_class": 1 / len(fr.classes),
            "false_inside_rate": fi, "false_inside_n": len(nb),
            "false_inside_rate_cells": float(np.mean([is_banned(o) for _, o in nb_cells])) if nb_cells else None,
            "false_inside_rate_catalogue": float(np.mean([is_banned(o) for _, o in nb_cat])) if nb_cat else None,
            "banned_class_share": len(fr.banned) / len(fr.classes),
            "per_class_accuracy": {c: float(np.mean([near == c for i, near, _ in res if fr.labels[i] == c]))
                                   for c in fr.classes}}


def t8(seed: int = 0) -> dict[str, Any]:
    """T8 placement tests on the synthetic ring: a planted point equal to a class mean lands in that class; a point
    midway between two classes gives a near-tie."""
    X, lab, _ = geometry.synthetic_ring(n_per=20, dim=30, seed=seed)
    labels = np.array(lab)
    meta = [{} for _ in labels]
    fr = Frame(X, labels, meta, 10, "synthetic")
    a, b = "bfs", "dfs"
    ma, mb = X[labels == a].mean(0), X[labels == b].mean(0)
    pa = fr.place(ma)
    pm = fr.place((ma + mb) / 2)
    ratio = pm["d"][a] / pm["d"][b]
    return {"mean_lands_in_class": pa["nearest_class"] == a, "midpoint_d_ratio": ratio,
            "midpoint_near_tie": abs(ratio - 1) < 0.25, "pass": pa["nearest_class"] == a and abs(ratio - 1) < 0.25}
