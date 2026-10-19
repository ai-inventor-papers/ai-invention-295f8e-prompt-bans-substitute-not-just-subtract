#!/usr/bin/env python3
"""8b Ideas x phrasings on correct programs: idea = labelled mode; phrasing = cluster of programs within one mode
whose identifier-normalised AST 4-gram shingles have Jaccard >= theta (single linkage = connected components;
complete linkage as robustness). DA@25 (Lee et al. Def. 3.1) for ideas and for (mode, cluster) phrasings, PPI,
slopes in T with program-bootstrap CIs and the paired difference of slopes (phrasings minus ideas)."""

from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis.metrics import clusters, da_at_k, hill1, jaccard_matrix, normalise_tokens, shingles  # noqa: E402

THETAS = (0.7, 0.8, 0.9)
LINKAGES = ("single", "complete")
TEMPS = [0.3, 0.7, 1.0, 1.3]


def _cell_key(s):
    d = s["decoding"]
    return (s["task"], s["arm"], d["sampler"], d["T"], d["thinking"], s["condition"])


def prepare(samples: list[dict]) -> dict:
    cells = defaultdict(list)
    for s in samples:
        if s["passed"] and s.get("code") and s["label"] not in ("unresolved", "unparseable"):
            cells[_cell_key(s)].append(s)
    prep = {}
    cache: dict[str, tuple] = {}
    for k, rows in cells.items():
        toks = []
        for r in rows:
            h = r["code_sha256"]
            if h not in cache:
                t = normalise_tokens(r["code"]) or []
                cache[h] = (tuple(t), shingles(t))
            toks.append(cache[h])
        J = jaccard_matrix([t[1] for t in toks])
        prep[k] = dict(labels=np.array([r["label"] for r in rows]), J=J,
                       sha=[r["code_sha256"] for r in rows], norm=[t[0] for t in toks])
    return prep


def cell_stats(labels: np.ndarray, J: np.ndarray, theta: float, linkage: str, K: int = 25) -> dict:
    n = len(labels)
    cats = []
    modal = Counter(labels).most_common(1)[0][0] if n else None
    modal_phr = []
    n_clusters = 0
    for m in sorted(set(labels)):
        idx = np.where(labels == m)[0]
        cl = clusters(J[np.ix_(idx, idx)], theta, linkage)
        n_clusters += len(set(cl.tolist()))
        cats.extend((m, int(c)) for c in cl)
        if m == modal:
            modal_phr = list(Counter(cl.tolist()).values())
    idea_counts = list(Counter(labels.tolist()).values())
    phr_counts = list(Counter(cats).values())
    da_i = da_at_k(idea_counts, K)
    da_p = da_at_k(phr_counts, K)
    return dict(n_correct=n, n_ideas=len(idea_counts), n_phrasings=n_clusters, EA_idea=hill1(idea_counts),
                EA_phr=hill1(phr_counts), DA_idea_25=da_i, DA_phr_25=da_p,
                PPI=(da_p / da_i) if (da_i and da_p) else None, DA_phr_modal_20=da_at_k(modal_phr, 20))


def _ols_slope(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = ~np.isnan(y)
    if ok.sum() < 3:
        return None
    xm = x[ok] - x[ok].mean()
    return float((xm * (y[ok] - y[ok].mean())).sum() / (xm ** 2).sum())


def run(samples: list[dict], n_boot: int = 1000, seed: int = 3) -> dict:
    prep = prepare(samples)
    rng = np.random.default_rng(seed)
    table = []
    for k, p in sorted(prep.items(), key=lambda kv: str(kv[0])):
        task, arm, sampler, T, think, cond = k
        base = dict(task=task, arm=arm, sampler=sampler, T=T, thinking=think, condition=cond,
                    n_correct=len(p["labels"]),
                    dup_rate_raw=1 - len(set(p["sha"])) / len(p["sha"]) if p["sha"] else None,
                    dup_rate_normalised=1 - len(set(p["norm"])) / len(p["norm"]) if p["norm"] else None,
                    idea_counts=dict(Counter(p["labels"].tolist())))
        for th in THETAS:
            for lk in LINKAGES:
                st = cell_stats(p["labels"], p["J"], th, lk)
                base[f"theta{th}_{lk}"] = st
        table.append(base)
    # slopes in T per (task, sampler, thinking, theta, linkage) over the A1 / A6 grids
    slopes = []
    groups = defaultdict(dict)
    for k, p in prep.items():
        task, arm, sampler, T, think, cond = k
        if arm == "A1" or arm.startswith("A6"):
            groups[(task, sampler, think)][T] = p
    for (task, sampler, think), byT in sorted(groups.items(), key=lambda kv: str(kv[0])):
        Ts = [t for t in TEMPS if t in byT]
        for th in THETAS:
            for lk in LINKAGES:
                def stats_for(idx_map):
                    ys = {"PPI": [], "DA_phr": [], "DA_idea": []}
                    for t in Ts:
                        pp = byT[t]
                        idx = idx_map[t]
                        st = cell_stats(pp["labels"][idx], pp["J"][np.ix_(idx, idx)], th, lk)
                        ys["PPI"].append(math.log(st["PPI"]) if st["PPI"] else np.nan)
                        ys["DA_phr"].append(math.log(st["DA_phr_25"]) if st["DA_phr_25"] else np.nan)
                        ys["DA_idea"].append(math.log(st["DA_idea_25"]) if st["DA_idea_25"] else np.nan)
                    return ys
                full = stats_for({t: np.arange(len(byT[t]["labels"])) for t in Ts})
                obs = {m: _ols_slope(Ts, full[m]) for m in full}
                nb = n_boot if lk == "single" else max(200, n_boot // 5)
                bs = {m: [] for m in ("PPI", "DA_phr", "DA_idea", "diff")}
                for _ in range(nb):
                    idx_map = {t: rng.integers(0, len(byT[t]["labels"]), len(byT[t]["labels"])) for t in Ts}
                    ys = stats_for(idx_map)
                    sl = {m: _ols_slope(Ts, ys[m]) for m in ys}
                    for m in ("PPI", "DA_phr", "DA_idea"):
                        if sl[m] is not None:
                            bs[m].append(sl[m])
                    if sl["DA_phr"] is not None and sl["DA_idea"] is not None:
                        bs["diff"].append(sl["DA_phr"] - sl["DA_idea"])
                rec = dict(task=task, sampler=sampler, thinking=think, theta=th, linkage=lk, n_boot=nb,
                           slope_log_PPI=obs["PPI"], slope_log_DA_phr=obs["DA_phr"], slope_log_DA_idea=obs["DA_idea"],
                           slope_diff_phr_minus_idea=(obs["DA_phr"] - obs["DA_idea"]) if obs["DA_phr"] is not None
                           and obs["DA_idea"] is not None else None)
                rec["p_one_sided_diff_le_0"] = float(np.mean(np.array(bs["diff"]) <= 0)) if bs["diff"] else None
                rec["p_one_sided_ppi_le_0"] = float(np.mean(np.array(bs["PPI"]) <= 0)) if bs["PPI"] else None
                for m, v in bs.items():
                    rec[f"ci95_{m}"] = [float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))] if v else None
                    rec[f"ci90_{m}"] = [float(np.quantile(v, 0.05)), float(np.quantile(v, 0.95))] if v else None
                slopes.append(rec)
    return dict(table=table, slopes=slopes)
