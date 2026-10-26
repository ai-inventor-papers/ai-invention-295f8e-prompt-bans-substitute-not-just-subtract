#!/usr/bin/env python3
"""locate8: pure functions of the blind decision-token locator (S3), committed at COMMIT #0.

3.1 clusters: the frontier of the >= 20%-coverage sub-trie of the fit twin's generated ids (nodes with coverage >= 0.2
    none of whose children has coverage >= 0.2); at most 4, largest first.
3.2 base paths: 6 per unit (8 if 4 clusters): >= 2 per cluster, >= 2 minority-labelled programs when the fit twin has
    >= 2, templates rotated.
3.3 grid: k in {0, 2, ..., 62} + {64, 68, ..., W_u}, W_u = min(160, max(64, deepest cluster + 8, p90 OC decision)).
3.4 change point (art_MZAfDPVhM6Ui forks.single_cp, Dirichlet(1), uniform tau, prior 0.5): detect if P(change) >= 0.9
    and TV(segment label distributions) >= 0.25; refine with 16 continuations at every single-token position of the
    bracket [k_(tau-1), k_tau]; the change position k* is the first k whose distribution differs from k-1 by TV >= 0.25
    (else the largest-TV step). The decision token is generated token index d = k* - 1; the opening is ids[:d].
3.5 forced tokens: Phat(A | t) from labelled forced continuations; classes = argmax_A Phat if >= 0.7 else UNDECIDED;
    H(A | class) weighted by T 1 class mass; confirmed if H <= 0.3 bits and >= 2 classes (mass >= 0.02) lead to
    different algorithms.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

import numpy as np

from forks import single_cp

UNDEC = "UNDECIDED"


# ------------------------------------------------------------------------------------------------ 3.1 / 3.2
def clusters(progs: list[list[int]], min_cov: float = 0.2, max_c: int = 4) -> list[dict[str, Any]]:
    n = len(progs)
    out: list[dict[str, Any]] = []

    def rec(prefix: list[int], members: list[int]) -> None:
        d = len(prefix)
        nxt = Counter(progs[i][d] for i in members if len(progs[i]) > d)
        big = [(t, m) for t, m in nxt.items() if m >= min_cov * n]
        if not big:
            out.append({"O": prefix, "members": members, "cov": len(members) / n})
            return
        for t, _ in big:
            rec(prefix + [t], [i for i in members if len(progs[i]) > d and progs[i][d] == t])
    rec([], list(range(n)))
    out.sort(key=lambda c: -c["cov"])
    out = out[:max_c]
    for j, c in enumerate(out):
        c["id"] = f"c{j}"
    return out


def choose_base_paths(progs: list[dict[str, Any]], cls: list[dict[str, Any]], minority: str | None,
                      n_paths: int = 6) -> list[int]:
    """progs: [{'gen_ids', 'label', 'w'}]; returns program indices."""
    picked: list[int] = []
    used_w: Counter = Counter()

    def take(cands: list[int], k: int) -> None:
        cands = [i for i in cands if i not in picked]
        # rotate templates; prefer label diversity
        cands.sort(key=lambda i: (used_w[progs[i]["w"]], i))
        labs_seen: set[str] = set()
        order = [i for i in cands if progs[i]["label"] not in labs_seen and not labs_seen.add(progs[i]["label"])]
        order += [i for i in cands if i not in order]
        for i in order[:k]:
            picked.append(i)
            used_w[progs[i]["w"]] += 1
    for c in cls:
        take(c["members"], 2)
    mins = [i for i, p in enumerate(progs) if p["label"] == minority]
    have = sum(progs[i]["label"] == minority for i in picked)
    if len(mins) >= 2 and have < 2:
        take(mins, 2 - have)
    if len(picked) < n_paths:
        rest = [i for i in range(len(progs)) if progs[i]["label"] not in ("invalid",)]
        take(rest, n_paths - len(picked))
    return picked[:max(n_paths, 2 * len(cls))]


def grid(w_u: int, path_len: int) -> list[int]:
    g = list(range(0, 63, 2)) + list(range(64, w_u + 1, 4))
    return [k for k in g if k < path_len]


# ------------------------------------------------------------------------------------------------ 3.4
def tv_counts(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    if a.sum() == 0 or b.sum() == 0:
        return 0.0
    return 0.5 * float(np.abs(a / a.sum() - b / b.sum()).sum())


def detect(series: np.ndarray, p_min: float = 0.9, tv_min: float = 0.25) -> dict[str, Any]:
    """series [K, C] label counts at the scanned positions. Single change point over the whole series."""
    if series.shape[0] < 3:
        return {"detected": False, "p_change": 0.0, "tau": None, "tv": 0.0}
    r = single_cp(series)
    if r["tau"] is None:
        return {"detected": False, "p_change": 0.0, "tau": None, "tv": 0.0}
    t = r["tau"]
    tv = tv_counts(series[:t].sum(0), series[t:].sum(0))
    return {"detected": bool(r["p_change"] >= p_min and tv >= tv_min), "p_change": float(r["p_change"]),
            "tau": int(t), "tv": tv, "post": r["post"]}


def change_position(dists: dict[int, np.ndarray], lo: int, hi: int, tv_min: float = 0.25) -> tuple[int, float]:
    """First k in (lo, hi] with TV(dist k, dist k-1) >= tv_min, else the largest-TV k."""
    best_k, best_tv = hi, -1.0
    for k in range(lo + 1, hi + 1):
        if k in dists and (k - 1) in dists:
            tv = tv_counts(dists[k], dists[k - 1])
            if tv >= tv_min:
                return k, tv
            if tv > best_tv:
                best_k, best_tv = k, tv
    return best_k, best_tv


# ------------------------------------------------------------------------------------------------ 3.5
def phat_from_counts(counts: Counter, bins: list[str]) -> np.ndarray:
    v = np.array([counts.get(b, 0) for b in bins], dtype=float)
    return v / v.sum() if v.sum() > 0 else np.full(len(bins), 1.0 / len(bins))


def classes(tokens: list[int], mass: np.ndarray, phat: dict[int, np.ndarray], resid_mass: float,
            resid_phat: np.ndarray, bins: list[str], pmin: float = 0.7) -> dict[str, Any]:
    cls_of: dict[str, str] = {}
    cmass: Counter = Counter()
    cmix: dict[str, np.ndarray] = {}
    items = [(str(t), float(m), phat[t]) for t, m in zip(tokens, mass)] + [("resid", float(resid_mass), resid_phat)]
    for key, m, ph in items:
        j = int(np.argmax(ph))
        c = bins[j] if ph[j] >= pmin else UNDEC
        cls_of[key] = c
        cmass[c] += m
        cmix[c] = cmix.get(c, np.zeros(len(bins))) + m * ph
    tot = sum(cmass.values())
    H = 0.0
    for c, m in cmass.items():
        if m > 0:
            p = cmix[c] / m
            p = p[p > 0]
            H += (m / tot) * float(-(p * np.log2(p)).sum())
    algs = {c for c, m in cmass.items() if c != UNDEC and m >= 0.02}
    return {"class_of": cls_of, "class_mass": dict(cmass), "H_bits": H, "n_alg_classes": len(algs),
            "alg_classes": sorted(algs)}


def h_bootstrap(tok_counts: dict[int, Counter], tokens: list[int], mass: np.ndarray, resid_mass: float,
                resid_phat: np.ndarray, bins: list[str], n_boot: int = 500, seed: int = 0) -> list[float]:
    rng = np.random.default_rng(seed)
    hs = []
    for _ in range(n_boot):
        ph = {}
        for t in tokens:
            c = tok_counts.get(t, Counter())
            n = sum(c.values())
            if n == 0:
                ph[t] = resid_phat
                continue
            p = phat_from_counts(c, bins)
            ph[t] = rng.multinomial(n, p) / n
        hs.append(classes(tokens, mass, ph, resid_mass, resid_phat, bins)["H_bits"])
    return [float(np.percentile(hs, 2.5)), float(np.percentile(hs, 97.5))]


def entropy_nats(p: np.ndarray) -> float:
    p = np.asarray(p, float)
    p = p[p > 0]
    return float(-(p * np.log(p)).sum())


def tok_entropy_bits(ph: np.ndarray) -> float:
    p = np.asarray(ph, float)
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum()) if len(p) else 0.0


def minimal_openings(cands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep openings that have no other candidate as a proper prefix; merge identical ones."""
    uniq: dict[tuple, dict[str, Any]] = {}
    for c in cands:
        key = tuple(c["O"])
        if key in uniq:
            uniq[key]["paths"] += c["paths"]
        else:
            uniq[key] = {**c, "paths": list(c["paths"])}
    keys = list(uniq)
    keep = []
    for k in keys:
        if any(len(o) < len(k) and k[:len(o)] == o for o in keys):
            continue
        keep.append(uniq[k])
    return keep


def _self_test() -> dict[str, Any]:
    """Change-point rule on synthetic label series (8 continuations per position): false-positive rate on 200 null
    series and power on planted TV-0.4 jumps (testing plan item 1)."""
    rng = np.random.default_rng(3)
    K, C = 32, 3
    fp = 0
    for _ in range(200):
        p = rng.dirichlet(np.ones(C) * 3)
        s = np.stack([rng.multinomial(8, p) for _ in range(K)])
        fp += detect(s)["detected"]
    power = 0
    for _ in range(200):
        p1 = np.array([0.7, 0.3, 0.0])
        p2 = np.array([0.3, 0.7, 0.0])               # TV 0.4
        tau = int(rng.integers(5, K - 5))
        s = np.stack([rng.multinomial(8, p1 if k < tau else p2) for k in range(K)])
        r = detect(s)
        power += r["detected"] and abs(r["tau"] - tau) <= 2
    return {"null_fp_rate": fp / 200, "power_tv04": power / 200, "pass": fp / 200 <= 0.05}


if __name__ == "__main__":
    print(_self_test())
