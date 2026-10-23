#!/usr/bin/env python3
"""Stages 6-10: label-only block selection + COMMIT #2; geometry, verdicts, landing, bootstrap, robustness,
crossnobis and z-scored sensitivities, frozen geodesics for iteration 10; lexical regressions; RSA with exact
label-permutation Mantel nulls; name evocation; per-program out-of-sample placement on M-code.

All geometry calls go through iteration 8's geometry.py (geodesics, knn_graph, class_matrix, g_values, classify,
classical_mds, stress1) and landing.py (landing) unchanged; the wrappers below only add (i) class sets with an
excluded algorithm (median over the remaining non-banned algorithms), (ii) a split-half threshold set to half the
number of groups, (iii) per-resample outputs for CIs.
"""

from __future__ import annotations

import itertools
import multiprocessing as mp
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger
from scipy.stats import mannwhitneyu, rankdata, spearmanr

import geometry
import landing
from common import (CANON_ORDER, commit, commit_time, deviation, read_json, read_jsonl, sha256_file, utc_now,
                    wilson_ci, write_json)
from tpg import (B5, DATA, IN_E44, K_SECOND, K_VERDICT, KS, LOO_GATE, MCODE_MIN, MODELS, N_BOOT_32B, N_BOOT_OTHER,
                 NB5, PRED, RELIABILITY_FLAG, RESULTS, ROOT, STATES_DIR, SURV_CONFIRM, SURV_SCREEN, UDIJ,
                 forced_rates_e44)

N_WORKERS = int(os.environ.get("TPG_WORKERS", "12"))
MANIFOLDS = ["mname", "mdesc", "mlex", "mcode_PRIMARY_R1", "mcode_PRIMARY_R2", "mcode_M32_R1"]
# Dropped for time (F10, logged): mcode_M8_R1, mcode_PRIMARY_R1g, mcode_PRIMARY_R3 (32B) and M-lex / R3 on Qwen3-8B.
VERDICT_MANIFOLDS = ["mname", "mdesc", "mlex", "mcode_PRIMARY_R1", "mcode_PRIMARY_R2", "mcode_M32_R1", "mcode_M8_R1"]
MANIFOLDS_8B = ["mname", "mdesc", "mcode_PRIMARY_R1"]   # second model: core manifolds only


def manifolds_for(model_tag: str) -> list[str]:
    return MANIFOLDS if model_tag == "32b" else MANIFOLDS_8B


def _pool() -> ProcessPoolExecutor:
    return ProcessPoolExecutor(max_workers=N_WORKERS, mp_context=mp.get_context("spawn"),
                               initializer=_init_worker)


def _init_worker() -> None:
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / "src"))
    os.environ.setdefault("OMP_NUM_THREADS", "1")


# ---------------------------------------------------------------------------------------------- loading
def load_manifold(model_tag: str, name: str) -> dict[str, Any] | None:
    """X [n, n_blocks, d] float32, labels, groups, ids, blocks, stimulus info."""
    f = None
    if name == "mname":
        f = STATES_DIR / f"mname_{model_tag}.npz"
        if not f.exists():
            return None
        z = np.load(f)
        return {"X": z["smean"].astype(np.float32), "labels": z["algorithm"], "groups": z["group"].astype(int),
                "ids": np.array([f"mname|{a}|t{t}|j{j}" for a, t, j in zip(z["algorithm"], z["template"],
                                                                           z["alias"])]),
                "blocks": [int(b) for b in z["blocks"]], "template": z["template"], "alias": z["alias"]}
    if name == "mdesc":
        f = STATES_DIR / f"mdesc_{model_tag}.npz"
        if not f.exists():
            return None
        z = np.load(f)
        return {"X": z["smean"].astype(np.float32), "labels": z["algorithm"], "groups": z["group"].astype(int),
                "ids": np.array([f"mdesc|{d}|t{t}" for d, t in zip(z["desc_id"], z["template"])]),
                "blocks": [int(b) for b in z["blocks"]], "desc_id": z["desc_id"], "desc_index": z["desc_index"]}
    if name == "mlex":
        f = STATES_DIR / f"mlex_{model_tag}.npz"
        if not f.exists():
            return None
        z = np.load(f)
        return {"X": z["delta"].astype(np.float32), "labels": z["algorithm"], "groups": z["group"].astype(int),
                "ids": np.array([f"mlex|{a}|t{t}|j{j}" for a, t, j in zip(z["algorithm"], z["template"],
                                                                          z["alias_index"])]),
                "blocks": [int(b) for b in z["blocks"]], "alias": z["alias_index"]}
    if name.startswith("mcode_"):
        _, frame, ro = name.split("_")
        f = STATES_DIR / f"mcode_{model_tag}.npz"
        if not f.exists():
            return None
        z = np.load(f)
        keys = list(z["keys"])
        ri = list(z["readouts"]).index(ro)
        ms = read_json(DATA / "mcode_sets.json")
        rows = []
        for a in CANON_ORDER:
            prog = ms["sets"][frame][a]
            if len(prog) < MCODE_MIN:
                continue
            for rank, p in enumerate(prog):
                rows.append((keys.index(p["scrubbed_sha256"]), a, rank % 10, p["uid"]))
        idx = np.array([r[0] for r in rows])
        X = z["R"][idx, ri].astype(np.float32)
        return {"X": X, "labels": np.array([r[1] for r in rows]), "groups": np.array([r[2] for r in rows]),
                "ids": np.array([r[3] for r in rows]), "blocks": [int(b) for b in z["blocks"]], "readout": ro,
                "frame": frame, "keys": np.array([keys[i] for i in idx])}
    raise ValueError(name)


# ---------------------------------------------------------------------------------------------- block selection
def _curve_one(args: tuple) -> tuple[int, float]:
    X, labels, groups, b = args
    import geometry as g

    lc = g.layer_curve(X[:, None, :], labels, groups, [b], [b], 64)
    return b, lc["curve"][b]


def layer_curve_parallel(X: np.ndarray, labels: np.ndarray, groups: np.ndarray, blocks: list[int],
                         sel: list[int], n_layers: int) -> dict[str, Any]:
    """Iteration 8's layer_curve, one block per worker; the selection rule is applied here verbatim."""
    with _pool() as ex:
        res = list(ex.map(_curve_one, [(X[:, blocks.index(b)].astype(np.float64), labels, groups, b) for b in sel]))
    curve = dict(res)
    best = max(curve.values())
    near = [b for b in sel if best - curve[b] <= 0.01]
    L = min(near, key=lambda b: (abs((b + 1) / n_layers - 0.5), b))
    ceiling = [b for b in sel if curve[b] >= 0.9999]
    rule = "argmax (ties within 0.01 -> nearest depth 0.5)"
    if len(ceiling) == len(sel):
        L = min(ceiling, key=lambda b: (abs((b + 1) / n_layers - 0.5), b))
        rule = "all blocks at ceiling -> nearest depth 0.5"
    return {"curve": curve, "L_star": int(L), "best": best, "tied_blocks": near, "rule": rule,
            "depth_of_L_star": (L + 1) / n_layers}


def stage_blocks(*args: str) -> None:
    deviation("F10-time", "analysis restricted to the 32B manifolds M-name, M-desc, M-lex, M-code PRIMARY R1/R2 and "
                          "the Qwen3-32B-only M-code frame, and to M-name, M-desc, M-code R1 on Qwen3-8B; dropped for "
                          "time: M8 frame, R1g and R3 readouts, Qwen3-8B M-lex (their states are kept in cache/states)")
    out: dict[str, Any] = {"utc": utc_now(), "manifolds": {}}
    for model_tag in ("32b", "8b"):
        cfg = MODELS[model_tag]
        for name in manifolds_for(model_tag):
            m = load_manifold(model_tag, name)
            if m is None:
                continue
            lc = layer_curve_parallel(m["X"], m["labels"], m["groups"], m["blocks"], cfg["sel_blocks"],
                                      cfg["n_layers"])
            out["manifolds"][f"{model_tag}|{name}"] = {**lc, "n_points": int(len(m["X"])),
                                                       "classes_present": sorted(set(m["labels"].tolist())),
                                                       "ref_block": cfg["ref_block"]}
            logger.info(f"blocks {model_tag} {name}: L*={lc['L_star']} best={lc['best']:.3f} ({lc['rule']})")
    # F8: M-code R1 must separate algorithms (CV balanced accuracy >= 0.5 somewhere) or R2 replaces it
    f8 = {}
    for model_tag in ("32b", "8b"):
        r1 = out["manifolds"].get(f"{model_tag}|mcode_PRIMARY_R1")
        r2 = out["manifolds"].get(f"{model_tag}|mcode_PRIMARY_R2")
        if r1:
            f8[model_tag] = {"R1_best": r1["best"], "R2_best": r2["best"] if r2 else None,
                             "verdict_readout": "R1" if r1["best"] >= 0.5 else ("R2" if r2 and r2["best"] >= 0.5
                                                                                 else "UNTESTABLE")}
            if f8[model_tag]["verdict_readout"] != "R1":
                deviation(f"F8-{model_tag}", f"M-code R1 does not separate algorithms: {f8[model_tag]}")
    out["F8"] = f8
    state_files = sorted(p.name for p in STATES_DIR.glob("*.npz"))
    out["state_sha256"] = {f: sha256_file(STATES_DIR / f) for f in state_files}
    out["k"] = {"verdict": K_VERDICT, "second": K_SECOND, "reported": list(KS)}
    out["readouts"] = {"mcode_centroids": "R1", "R2_frame": "R2 placements", "negative_control": "R3"}
    write_json(PRED / "commit2.json", out)
    commit(PRED / "commit2.json", "COMMIT2", "label-only blocks, k, readouts, state hashes; before landing/placement")


# ---------------------------------------------------------------------------------------------- geometry
def classes_of(g: dict[str, float]) -> tuple[dict[str, str], float]:
    return geometry.classify(g)


def describe(X: np.ndarray, labels: np.ndarray, ks: tuple[int, ...] = KS, embed: bool = False) -> dict[str, Any]:
    present = [a for a in CANON_ORDER if a in set(labels.tolist())]
    nb = [a for a in NB5 if a in present]
    bp = [b for b in B5 if b in present]
    out: dict[str, Any] = {"n_points": int(len(X)), "present": present, "nonbanned_used": nb, "banned_used": bp}
    from sklearn.decomposition import PCA

    pca = PCA(n_components=min(10, len(X) - 1), random_state=0).fit(X)
    out["pca_evr"] = pca.explained_variance_ratio_.tolist()
    D = geometry.squareform(geometry.pdist(X))
    Ym = geometry.classical_mds(D)
    out["mds_points_stress1"] = geometry.stress1(D, Ym)
    cent = np.stack([X[labels == c].mean(0) for c in present])
    Dc = geometry.squareform(geometry.pdist(cent))
    Ymc = geometry.classical_mds(Dc)
    out["mds_centroids_stress1"] = geometry.stress1(Dc, Ymc)
    out["centroid_distance_matrix"] = Dc.tolist()
    emb = {"pca": pca, "mds_points": Ym, "mds_centroids": Ymc, "geo": {}, "D": D}
    for k in ks:
        geo, info = geometry.geodesics(X, k)
        g, near = geometry.g_values(geo, labels, bp, nb)
        cls, med = classes_of(g)
        M = geometry.class_matrix(geo, labels, CANON_ORDER)
        rank = sorted(nb, key=lambda a: g[a]).index(UDIJ) + 1 if UDIJ in nb else None
        out[f"k{k}"] = {**info, "g": g, "nearest_banned": near, "classes": cls, "median": med,
                        "class_geodesic_matrix": M.tolist(), "udij_rank": rank,
                        "udij_ratio": (g[UDIJ] / med) if UDIJ in nb and med > 0 else None}
        emb["geo"][k] = geo
    gc_, nc_ = geometry.g_centroid(X, labels, bp, nb)
    clc, medc = classes_of(gc_)
    out["euclid_centroid"] = {"g": gc_, "nearest_banned": nc_, "classes": clc, "median": medc}
    if embed:
        from sklearn.manifold import Isomap

        iso = Isomap(n_neighbors=K_VERDICT, n_components=2).fit(X)
        emb["isomap"] = (iso, iso.embedding_)
    out["_emb"] = emb
    return out


def split_half(X: np.ndarray, labels: np.ndarray, groups: np.ndarray, k: int) -> dict[str, Any]:
    ug = np.unique(groups)
    thr = ug[len(ug) // 2]
    h1 = groups < thr
    mats = []
    for m in (h1, ~h1):
        geo, _ = geometry.geodesics(X[m], k)
        M = geometry.class_matrix(geo, labels[m], CANON_ORDER)
        mats.append((M + M.T) / 2)
    present = [i for i, a in enumerate(CANON_ORDER) if a in set(labels.tolist())]
    iu = [(i, j) for i, j in itertools.combinations(present, 2)]
    a = [mats[0][i, j] for i, j in iu]
    b = [mats[1][i, j] for i, j in iu]
    rho = float(spearmanr(a, b).statistic)
    sb = 2 * rho / (1 + rho) if rho > -1 else float("nan")
    return {"k": k, "split_threshold_group": int(thr), "spearman_halves": rho, "spearman_brown": sb,
            "noise_ceiling_upper": float(np.sqrt(max(sb, 0.0))), "flag_unreliable": sb < RELIABILITY_FLAG,
            "half_matrices": [m.tolist() for m in mats]}


def _boot_chunk(args: tuple) -> list[dict[str, Any]]:
    X, labels, groups, k, seeds = args
    import geometry as gm
    from tpg import B5 as b5, NB5 as nb5

    nb = [a for a in nb5 if a in set(labels.tolist())]
    b5 = [b for b in b5 if b in set(labels.tolist())]
    ug = np.unique(groups)
    out = []
    for s in seeds:
        rng = np.random.default_rng(s)
        gs = rng.choice(ug, size=len(ug), replace=True)
        idx = np.concatenate([np.where(groups == g)[0] for g in gs])
        Xb = X[idx] + rng.normal(0, 1e-9, size=X[idx].shape)
        geo, _ = gm.geodesics(Xb, k)
        g, near = gm.g_values(geo, labels[idx], b5, nb)
        M = gm.class_matrix(geo, labels[idx], list(__import__("common").CANON_ORDER))
        out.append({"g": g, "near": near, "M": ((M + M.T) / 2).tolist()})
    return out


def bootstrap(X: np.ndarray, labels: np.ndarray, groups: np.ndarray, k: int, n_boot: int, full: dict[str, Any],
              seed: int = 0) -> dict[str, Any]:
    seeds = [seed * 100000 + i for i in range(n_boot)]
    chunks = [seeds[i::N_WORKERS] for i in range(N_WORKERS)]
    with _pool() as ex:
        res = [r for part in ex.map(_boot_chunk, [(X, labels, groups, k, c) for c in chunks if c]) for r in part]
    nb = list(full["g"].keys())
    full_cls = full["classes"]
    cls_runs = [classes_of(r["g"])[0] for r in res]
    ratios = [r["g"][UDIJ] / float(np.median(list(r["g"].values()))) for r in res] if UDIJ in nb else []
    ranks = [sorted(nb, key=lambda a: r["g"][a]).index(UDIJ) + 1 for r in res] if UDIJ in nb else []
    return {"n_boot": len(res), "k": k,
            "class_stability": {a: float(np.mean([c[a] == full_cls[a] for c in cls_runs])) for a in nb},
            "edge_probability": {a: float(np.mean([c[a] == "EDGE" for c in cls_runs])) for a in nb},
            "opposite_probability": {a: float(np.mean([c[a] == "OPPOSITE" for c in cls_runs])) for a in nb},
            "nearest_banned_stability": {a: float(np.mean([r["near"][a] == full["nearest_banned"][a] for r in res]))
                                         for a in nb},
            "udij_ratio_ci95": [float(np.quantile(ratios, 0.025)), float(np.quantile(ratios, 0.975))] if ratios
            else None, "udij_rank_distribution": {int(v): ranks.count(v) for v in sorted(set(ranks))},
            "_matrices": [r["M"] for r in res]}


def crossnobis(X: np.ndarray, labels: np.ndarray, groups: np.ndarray) -> dict[str, Any]:
    """Split-half cross-validated squared centroid distances d2(a,b) = (mu_a^A - mu_b^A).(mu_a^B - mu_b^B)."""
    ug = np.unique(groups)
    thr = ug[len(ug) // 2]
    h1 = groups < thr
    present = [a for a in CANON_ORDER if a in set(labels.tolist())]
    muA = {a: X[h1 & (labels == a)].mean(0) for a in present}
    muB = {a: X[~h1 & (labels == a)].mean(0) for a in present}
    D = np.zeros((10, 10))
    for i, a in enumerate(CANON_ORDER):
        for j, b in enumerate(CANON_ORDER):
            if a in present and b in present and a != b:
                D[i, j] = float((muA[a] - muA[b]) @ (muB[a] - muB[b]))
    nb = [a for a in NB5 if a in present]
    g = {a: min(D[CANON_ORDER.index(a), CANON_ORDER.index(b)] for b in B5 if b in present) for a in nb}
    cls, med = classes_of(g)
    return {"d2_cv": D.tolist(), "g": g, "classes": cls, "median": med}


def landing_all(g: dict[str, float], cls: dict[str, str]) -> dict[str, Any]:
    base = read_jsonl(IN_E44 / "data" / "labelled_C6_baseline.jsonl")
    base_counts = {a: sum(1 for r in base if r.get("adj_label") == a) for a in g}
    rates = forced_rates_e44()
    out = {}
    for nm, surv in (("screen", SURV_SCREEN), ("confirm", SURV_CONFIRM), ("pooled", SURV_SCREEN + SURV_CONFIRM)):
        surv_ok = [s for s in surv if s in g]
        if not surv_ok:
            out[nm] = {"verdict": "UNTESTABLE (survivor algorithm not in the manifold)"}
            continue
        out[nm] = landing.strip(landing.landing(g, cls, surv_ok, base_counts, rates))
    return out


def robustness(Xb: np.ndarray, labels: np.ndarray, blocks: list[int], L: int) -> dict[str, Any]:
    cells = {}
    for b in range(L - 2, L + 3):
        if b not in blocks:
            continue
        X = Xb[:, blocks.index(b)].astype(np.float64)
        nb = [a for a in NB5 if a in set(labels.tolist())]
        bp = [b for b in B5 if b in set(labels.tolist())]
        for k in KS:
            geo, info = geometry.geodesics(X, k)
            g, _ = geometry.g_values(geo, labels, bp, nb)
            cls, _ = classes_of(g)
            lk = landing_all(g, cls)["pooled"]
            cells[f"L{b}_k{k}"] = {"udij_class": cls.get(UDIJ), "classes": cls, "verdict": lk.get("verdict"),
                                   "components": info["components_before_join"]}
    from collections import Counter

    return {"cells": cells, "udij_class_counts": dict(Counter(c["udij_class"] for c in cells.values())),
            "verdict_counts": dict(Counter(c["verdict"] for c in cells.values())), "n_cells": len(cells)}


def analyse_manifold(model_tag: str, name: str, blocks_rec: dict[str, Any]) -> dict[str, Any] | None:
    m = load_manifold(model_tag, name)
    if m is None:
        return None
    cfg = MODELS[model_tag]
    key = f"{model_tag}|{name}"
    L = blocks_rec["manifolds"][key]["L_star"]
    res: dict[str, Any] = {"model": model_tag, "manifold": name, "L_star": L, "ref_block": cfg["ref_block"],
                           "n_points": int(len(m["X"])), "layer_curve": blocks_rec["manifolds"][key]}
    n_boot = N_BOOT_32B if model_tag == "32b" and name in VERDICT_MANIFOLDS[:4] else N_BOOT_OTHER
    for tag_b, b in (("L_star", L), ("ref_block", cfg["ref_block"])):
        if tag_b == "ref_block" and b == L:
            res["ref_block_same_as_L_star"] = True
            continue
        X = m["X"][:, m["blocks"].index(b)].astype(np.float64)
        d = describe(X, m["labels"], embed=(tag_b == "L_star"))
        emb = d.pop("_emb")
        sec: dict[str, Any] = {"block": b, "describe": d}
        sec["landing"] = {f"k{k}": landing_all(d[f"k{k}"]["g"], d[f"k{k}"]["classes"]) for k in (K_SECOND, K_VERDICT)}
        sec["split_half"] = {f"k{k}": {kk: vv for kk, vv in split_half(X, m["labels"], m["groups"], k).items()
                                       if kk != "half_matrices"} for k in KS}
        if tag_b == "L_star":
            sec["bootstrap"] = {}
            for k in (K_VERDICT, K_SECOND):
                bs = bootstrap(X, m["labels"], m["groups"], k, n_boot, d[f"k{k}"], seed=k)
                mats = bs.pop("_matrices")
                np.save(STATES_DIR / f"boot_{model_tag}_{name}_k{k}.npy", np.array(mats, dtype=np.float32))
                sec["bootstrap"][f"k{k}"] = bs
            sec["robustness"] = robustness(m["X"], m["labels"], m["blocks"], L)
            sec["crossnobis"] = crossnobis(X, m["labels"], m["groups"])
            mu, sd = X.mean(0), X.std(0) + 1e-8
            dz = describe((X - mu) / sd, m["labels"], ks=(K_VERDICT,))
            dz.pop("_emb")
            sec["zscored"] = {"classes": dz[f"k{K_VERDICT}"]["classes"], "g": dz[f"k{K_VERDICT}"]["g"]}
            # freeze for iteration 10 (out-of-sample placement without refitting)
            for k in (K_SECOND, K_VERDICT):
                G, ncomp, added = geometry.knn_graph(X, k)
                np.savez_compressed(STATES_DIR / f"geo_{model_tag}_{name}_k{k}.npz", geo=emb["geo"][k],
                                    adjacency=G.toarray().astype(np.float32), X=X.astype(np.float32),
                                    labels=m["labels"], point_ids=m["ids"], block=L, readout=m.get("readout", "S-mean"),
                                    standardised=False, k=k)
            # figure inputs (2-D coordinates only)
            pca2 = emb["pca"].transform(X)[:, :2]
            iso = emb.get("isomap")
            np.savez_compressed(RESULTS.parent / "figures" / "coords" / f"{model_tag}_{name}.npz",
                                pca2=pca2, evr=np.array(d["pca_evr"][:2]), mds=emb["mds_points"],
                                mds_c=emb["mds_centroids"], iso=iso[1] if iso else np.zeros((0, 2)),
                                labels=m["labels"], geo=emb["geo"][K_VERDICT], block=L,
                                pca_components=emb["pca"].components_[:2].astype(np.float32),
                                pca_mean=emb["pca"].mean_.astype(np.float32))
        res[tag_b] = sec
    v = res["L_star"]["describe"]
    res["summary"] = {f"k{k}": {"udij_class": v[f"k{k}"]["classes"].get(UDIJ), "udij_rank": v[f"k{k}"]["udij_rank"],
                                "udij_ratio": v[f"k{k}"]["udij_ratio"], "udij_nearest_banned":
                                    v[f"k{k}"]["nearest_banned"].get(UDIJ), "classes": v[f"k{k}"]["classes"],
                                "verdict_pooled": res["L_star"]["landing"].get(f"k{k}", {}).get("pooled", {}).get(
                                    "verdict") if k in (K_SECOND, K_VERDICT) else None} for k in KS}
    logger.info(f"[{model_tag} {name}] L*={L} k15 {res['summary']['k15']['classes']} verdict "
                f"{res['summary']['k15']['verdict_pooled']} | k10 {res['summary']['k10']['udij_class']} "
                f"{res['summary']['k10']['verdict_pooled']}")
    return res


# ---------------------------------------------------------------------------------------------- lexical regression
def _perm_p(x: np.ndarray, y: np.ndarray, n: int = 100000, seed: int = 0) -> float:
    rng = np.random.default_rng(seed)
    r0 = spearmanr(x, y).statistic
    rx, ry = rankdata(x), rankdata(y)
    ry = ry - ry.mean()
    P = np.argsort(rng.random((n, len(x))), axis=1)
    rxp = rx[P] - rx.mean()
    rr = (rxp * ry).sum(1) / np.sqrt((rxp ** 2).sum(1) * (ry ** 2).sum())
    return float(np.mean(rr <= r0 + 1e-12)) if r0 < 0 else float(np.mean(rr >= r0 - 1e-12))


def partial_spearman(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> float:
    rx, ry, rz = rankdata(x), rankdata(y), rankdata(z)
    A = np.c_[np.ones(len(rz)), rz]
    ex = rx - A @ np.linalg.lstsq(A, rx, rcond=None)[0]
    ey = ry - A @ np.linalg.lstsq(A, ry, rcond=None)[0]
    den = np.sqrt((ex ** 2).sum() * (ey ** 2).sum())
    return float((ex * ey).sum() / den) if den > 0 else float("nan")


def alias_level(model_tag: str, name: str, L: int) -> dict[str, Any] | None:
    m = load_manifold(model_tag, name)
    if m is None:
        return None
    lex = read_json(RESULTS / "lexical.json")
    lx = {(r["algorithm"], r["alias_index"]): r for r in lex["aliases"]}
    X = m["X"][:, m["blocks"].index(L)].astype(np.float64)
    out = {}
    key_arr = m["alias"] if name in ("mname", "mlex") else None
    for k in (K_SECOND, K_VERDICT):
        geo, _ = geometry.geodesics(X, k)
        rows = []
        for a in NB5:
            for j in range(3):
                sel = (m["labels"] == a) & (key_arr == j)
                gm = min(float(np.mean(geo[np.ix_(sel, m["labels"] == b)])) for b in B5)
                rows.append({"algorithm": a, "alias_index": j, "g_alias": gm, **{f: lx[(a, j)][f] for f in
                                                                                 ("L1", "L2", "L3", "n_tokens")}})
        g = np.array([r["g_alias"] for r in rows])
        res: dict[str, Any] = {"rows": rows}
        for f in ("L1", "L2", "L3"):
            v = np.array([r[f] for r in rows], dtype=float)
            res[f"spearman_{f}"] = float(spearmanr(g, v).statistic)
            res[f"perm_p_{f}"] = _perm_p(g, v)
            res[f"partial_{f}_given_length"] = partial_spearman(g, v, np.array([r["n_tokens"] for r in rows]))
        # within-algorithm test: demean by algorithm, exact 6^5 within-algorithm permutations of L2
        algs = [r["algorithm"] for r in rows]
        gd = g - np.array([np.mean([g[i] for i in range(15) if algs[i] == algs[t]]) for t in range(15)])
        L2 = np.array([r["L2"] for r in rows])
        L2d = L2 - np.array([np.mean([L2[i] for i in range(15) if algs[i] == algs[t]]) for t in range(15)])
        r0 = float(np.corrcoef(gd, L2d)[0, 1]) if L2d.std() > 0 else float("nan")
        perms = list(itertools.permutations(range(3)))
        cnt, tot = 0, 0
        for combo in itertools.product(perms, repeat=5):
            L2p = np.concatenate([L2d[3 * i:3 * i + 3][list(p)] for i, p in enumerate(combo)])
            r = float(np.corrcoef(gd, L2p)[0, 1]) if L2p.std() > 0 else 0.0
            cnt += r <= r0 + 1e-12
            tot += 1
        res["within_algorithm"] = {"pearson_demeaned_g_L2": r0, "exact_p_lower": cnt / tot, "n_perms": tot}
        out[f"k{k}"] = res
    out["P4_pass"] = all(out[f"k{k}"]["spearman_L1"] <= -0.6 for k in (K_SECOND, K_VERDICT))
    return out


# ---------------------------------------------------------------------------------------------- RSA
_PERMS: dict[int, np.ndarray] = {}


def _perms(n: int) -> np.ndarray:
    if n not in _PERMS:
        _PERMS[n] = np.array(list(itertools.permutations(range(n))), dtype=np.int8)
    return _PERMS[n]


def mantel_exact(neural: np.ndarray, model: np.ndarray) -> dict[str, Any]:
    """Spearman over the upper triangle; exact p over all n! condition-label permutations (one-sided, >=)."""
    n = len(neural)
    iu = np.triu_indices(n, 1)
    rv = rankdata(neural[iu])
    rv = rv - rv.mean()
    RM = np.zeros((n, n))
    RM[iu] = rankdata(model[iu])
    RM = RM + RM.T
    rm = RM[iu] - RM[iu].mean()
    rho = float((rv * rm).sum() / np.sqrt((rv ** 2).sum() * (rm ** 2).sum()))
    P = _perms(n)
    flat = RM.ravel()
    mean_r = RM[iu].mean()
    den = np.sqrt((rv ** 2).sum() * (rm ** 2).sum())
    ge = 0
    for s in range(0, len(P), 200000):
        ch = P[s:s + 200000].astype(np.int64)
        vals = flat[ch[:, iu[0]] * n + ch[:, iu[1]]] - mean_r
        r = (vals @ rv) / den
        ge += int(np.sum(r >= rho - 1e-12))
    return {"rho": rho, "p_exact": ge / len(P), "n_perms": int(len(P)), "n_pairs": int(len(rv))}


def model_rdms(manifold: str) -> dict[str, np.ndarray]:
    beh = read_json(RESULTS / "behavioural_distance.json")
    lex = read_json(RESULTS / "lexical.json")
    out = {"R_lex": np.array(lex["R_lex"]), "R_beh": np.array(beh["d_beh_lambda0.5"]),
           "R_beh_order": np.array(beh["d_order"]), "R_DS": np.array(beh["d_DS"])}
    sur = RESULTS / "surface_rdm.json"
    if sur.exists():
        s = read_json(sur)
        out["R_surface"] = np.array(s["R_surface"])
        if manifold in s.get("R_len", {}):
            out["R_len"] = np.array(s["R_len"][manifold])
    dl = read_json(DATA / "descriptions_v0.json")
    out["R_desc_lex"] = np.array(dl["R_desc_lex"])
    return out


def surface_rdm() -> None:
    """R_surface: 1 - mean Jaccard of identifier-normalised AST 4-gram shingles between PRIMARY program sets;
    R_len: absolute difference of mean stimulus token length per manifold."""
    import ast

    ms = read_json(DATA / "mcode_sets.json")

    def shingles(code: str) -> set[tuple[str, ...]]:
        seq = [type(n).__name__ for n in ast.walk(ast.parse(code))]
        return {tuple(seq[i:i + 4]) for i in range(len(seq) - 3)}

    sh = {a: [shingles(p["scrubbed"]) for p in ms["sets"]["PRIMARY"][a]] for a in CANON_ORDER}
    R = np.zeros((10, 10))
    for i, j in itertools.combinations(range(10), 2):
        A, B = sh[CANON_ORDER[i]], sh[CANON_ORDER[j]]
        if A and B:
            js = [len(x & y) / len(x | y) for x in A for y in B]
            R[i, j] = R[j, i] = 1 - float(np.mean(js))
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(MODELS["32b"]["repo"], revision=MODELS["32b"]["revision"])
    lens: dict[str, dict[str, float]] = {}
    lex = read_json(RESULTS / "lexical.json")
    lens["mname"] = {a: float(np.mean([r["n_tokens"] for r in lex["aliases"] if r["algorithm"] == a]))
                     for a in CANON_ORDER}
    lens["mlex"] = lens["mname"]
    md = read_json(DATA / "mdesc_prompts.json")["rows"]
    lens["mdesc"] = {a: float(np.mean([len(tok(" " + r["text"], add_special_tokens=False)["input_ids"])
                                       for r in md if r["algorithm"] == a])) if any(r["algorithm"] == a for r in md)
                     else float("nan") for a in CANON_ORDER}
    lens["mcode"] = {a: float(np.mean([len(tok(p["scrubbed"], add_special_tokens=False)["input_ids"])
                                       for p in ms["sets"]["PRIMARY"][a]])) if ms["sets"]["PRIMARY"][a]
                     else float("nan") for a in CANON_ORDER}
    R_len = {}
    for nm, d in lens.items():
        v = np.array([d[a] for a in CANON_ORDER])
        R_len[nm] = np.abs(v[:, None] - v[None, :]).tolist()
    write_json(RESULTS / "surface_rdm.json", {"R_surface": R.tolist(), "R_len": R_len, "lengths": lens})


def rsa(geo_results: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, r in geo_results.items():
        if r is None:
            continue
        model_tag, name = key.split("|")
        d = r["L_star"]["describe"]
        M = np.array(d[f"k{K_VERDICT}"]["class_geodesic_matrix"])
        M = (M + M.T) / 2
        present = [i for i, a in enumerate(CANON_ORDER) if a in d["present"]]
        Mn = M[np.ix_(present, present)]
        mr = model_rdms("mcode" if name.startswith("mcode") else name)
        sh = r["L_star"]["split_half"][f"k{K_VERDICT}"]
        res = {"present": [CANON_ORDER[i] for i in present], "noise_ceiling_upper": sh["noise_ceiling_upper"],
               "split_half_spearman_brown": sh["spearman_brown"], "models": {}}
        for mn, R in mr.items():
            Rm = R[np.ix_(present, present)]
            if not np.isfinite(Rm).all():
                continue
            res["models"][mn] = mantel_exact(Mn, Rm)
        # bootstrap CIs of rho differences from the stored bootstrap matrices
        bp = STATES_DIR / f"boot_{model_tag}_{name}_k{K_VERDICT}.npy"
        if bp.exists():
            mats = np.load(bp)
            iu = np.triu_indices(len(present), 1)
            diffs = {}
            for a_, b_ in (("R_lex", "R_beh"), ("R_beh", "R_lex"), ("R_surface", "R_beh")):
                if a_ in mr and b_ in mr:
                    Ra = mr[a_][np.ix_(present, present)][iu]
                    Rb = mr[b_][np.ix_(present, present)][iu]
                    vals = []
                    for Mb in mats:
                        v = np.asarray(Mb)[np.ix_(present, present)][iu]
                        if not np.isfinite(v).all():
                            continue
                        vals.append(spearmanr(v, Ra).statistic - spearmanr(v, Rb).statistic)
                    if vals:
                        diffs[f"{a_}-{b_}"] = {"mean": float(np.mean(vals)),
                                               "ci95": [float(np.quantile(vals, 0.025)),
                                                        float(np.quantile(vals, 0.975))], "n": len(vals)}
            res["rho_differences_bootstrap"] = diffs
        if name.startswith("mcode") and "R_surface" in mr and "R_len" in mr:
            iu = np.triu_indices(len(present), 1)
            v = Mn[iu]
            rb = mr["R_beh"][np.ix_(present, present)][iu]
            z1 = mr["R_surface"][np.ix_(present, present)][iu]
            res["partial_beh_given_surface"] = partial_spearman(v, rb, z1)
        out[key] = res
        logger.info(f"RSA {key}: " + ", ".join(f"{k} {v['rho']:.2f} (p {v['p_exact']:.4f})"
                                               for k, v in res["models"].items()))
    return out


def name_evocation(model_tag: str, L: int) -> dict[str, Any]:
    from sklearn.decomposition import PCA
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import balanced_accuracy_score
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    mn = load_manifold(model_tag, "mname")
    if mn is None:
        return {}
    X = mn["X"][:, mn["blocks"].index(L)].astype(np.float64)
    clf = make_pipeline(StandardScaler(), PCA(n_components=64, random_state=0), LogisticRegression(C=1.0, max_iter=3000))
    clf.fit(X, mn["labels"])
    out = {"train": "M-name", "block": L}
    for nm in ("mdesc", "mcode_PRIMARY_R1", "mlex"):
        m = load_manifold(model_tag, nm)
        if m is None:
            continue
        Xt = m["X"][:, m["blocks"].index(L)].astype(np.float64)
        pred = clf.predict(Xt)
        out[nm] = {"transfer_balanced_accuracy": float(balanced_accuracy_score(m["labels"], pred)),
                   "chance": 1 / len(set(m["labels"].tolist())), "n": int(len(Xt))}
    return out


# ---------------------------------------------------------------------------------------------- placement
def oos(x: np.ndarray, F: np.ndarray, geo: np.ndarray, k: int) -> np.ndarray:
    d = np.linalg.norm(F - x, axis=1)
    nn = np.argsort(d)[:k]
    return np.min(d[nn][:, None] + geo[nn], axis=0)


def _loo_one(args: tuple) -> tuple[int, str]:
    i, F, labels, k = args
    import geometry as gm

    keep = np.ones(len(F), bool)
    keep[i] = False
    geo, _ = gm.geodesics(F[keep], k)
    dv = oos(F[i], F[keep], geo, k)
    lab = labels[keep]
    algs = sorted(set(lab.tolist()))
    means = {a: float(dv[lab == a].mean()) for a in algs}
    return i, min(means, key=means.get)


def placement(model_tag: str, frame_name: str, L: int, k: int = K_VERDICT) -> dict[str, Any] | None:
    m = load_manifold(model_tag, frame_name)
    if m is None:
        return None
    ro = m["readout"]
    F = m["X"][:, m["blocks"].index(L)].astype(np.float64)
    labels = m["labels"]
    geo, _ = geometry.geodesics(F, k)
    nb = [a for a in NB5 if a in set(labels.tolist())]
    g_frame, _ = geometry.g_values(geo, labels, [b for b in B5 if b in set(labels.tolist())], nb)
    cls_frame, med = classes_of(g_frame)
    with _pool() as ex:
        loo = dict(ex.map(_loo_one, [(i, F, labels, k) for i in range(len(F))]))
    acc = float(np.mean([loo[i] == labels[i] for i in range(len(F))]))
    z = np.load(STATES_DIR / f"mcode_{model_tag}.npz")
    keys = list(z["keys"])
    ri = list(z["readouts"]).index(ro)
    bi = [int(b) for b in z["blocks"]].index(L)
    ms = read_json(DATA / "mcode_sets.json")
    rows = []
    for p in ms["placement"]:
        if p["scrubbed_sha256"] not in keys:
            continue
        x = z["R"][keys.index(p["scrubbed_sha256"]), ri, bi].astype(np.float64)
        dv = oos(x, F, geo, k)
        means = {a: float(dv[labels == a].mean()) for a in sorted(set(labels.tolist()))}
        gb = {b: means[b] for b in B5 if b in means}
        gx = min(gb.values())
        rows.append({"uid": p["uid"], "set": p["set"], "label": p["algorithm"], "other_name": p.get("other_name"),
                     "nearest_algorithm": min(means, key=means.get), "g_x": gx,
                     "nearest_banned": min(gb, key=gb.get), "class": "EDGE" if gx < med - 1e-12 else
                     ("OPPOSITE" if gx > med + 1e-12 else "MIDDLE"), "mean_geodesic": means,
                     "g_scrub_pass": p.get("g_scrub_pass")})
    ud = [r for r in rows if r["set"] == "SURV" and r["label"] == UDIJ]
    n_edge = sum(r["class"] == "EDGE" for r in ud)
    base = [r for r in rows if r["set"] == "BASE"]
    # LOO g of frame uDij programs for the descriptive comparison
    frame_ud_g = []
    for i in np.where(labels == UDIJ)[0]:
        keep = np.ones(len(F), bool)
        keep[i] = False
        g2, _ = geometry.geodesics(F[keep], k)
        dv = oos(F[i], F[keep], g2, k)
        frame_ud_g.append(min(float(dv[labels[keep] == b].mean()) for b in B5 if (labels[keep] == b).any()))
    mw = None
    if ud and frame_ud_g:
        mw = mannwhitneyu([r["g_x"] for r in ud], frame_ud_g).pvalue
    return {"frame": frame_name, "model": model_tag, "block": L, "k": k, "readout": ro,
            "G_place": {"loo_accuracy": acc, "gate": LOO_GATE, "pass": acc >= LOO_GATE},
            "frame_g": g_frame, "frame_classes": cls_frame, "frame_median": med,
            "base_accuracy_own_label": float(np.mean([r["nearest_algorithm"] == r["label"] for r in base]))
            if base else None,
            "udij_survivors": {"n": len(ud), "n_edge": n_edge, "share_edge": n_edge / len(ud) if ud else None,
                               "wilson95": wilson_ci(n_edge, len(ud)) if ud else None,
                               "share_nearest_banned": float(np.mean([r["nearest_algorithm"] in B5 for r in ud]))
                               if ud else None,
                               "nearest_algorithm_counts": {a: sum(r["nearest_algorithm"] == a for r in ud)
                                                            for a in CANON_ORDER},
                               "mannwhitney_p_vs_frame_udij_loo": mw,
                               "frame_udij_loo_g_median": float(np.median(frame_ud_g)) if frame_ud_g else None,
                               "survivor_g_median": float(np.median([r["g_x"] for r in ud])) if ud else None},
            "P8_pass": (n_edge / len(ud) > 0.5) if ud and acc >= LOO_GATE else None,
            "rows": rows}


# ---------------------------------------------------------------------------------------------- stage
def stage_analyse(*args: str) -> None:
    assert commit_time("COMMIT2") is not None, "analysis requires COMMIT #2"
    (RESULTS.parent / "figures" / "coords").mkdir(parents=True, exist_ok=True)
    blocks_rec = read_json(PRED / "commit2.json")
    which = list(args) or ["geometry", "lexical", "rsa", "placement"]
    geo_path = RESULTS / "geometry_all.json"
    geo_results: dict[str, Any] = read_json(geo_path) if geo_path.exists() else {}
    if "geometry" in which:
        for model_tag in ("32b", "8b"):
            for name in VERDICT_MANIFOLDS + ["mcode_PRIMARY_R1g", "mcode_PRIMARY_R3"]:
                if f"{model_tag}|{name}" not in blocks_rec["manifolds"]:
                    continue
                r = analyse_manifold(model_tag, name, blocks_rec)
                if r is not None:
                    geo_results[f"{model_tag}|{name}"] = r
                    write_json(RESULTS / f"geometry_{model_tag}_{name}.json", r)
                    write_json(geo_path, geo_results)
    if "lexical" in which:
        lr = {}
        for model_tag in ("32b", "8b"):
            for name in ("mname", "mlex"):
                key = f"{model_tag}|{name}"
                if key in blocks_rec["manifolds"]:
                    lr[key] = alias_level(model_tag, name, blocks_rec["manifolds"][key]["L_star"])
        lr["descriptive_mdesc_mcode"] = _desc_overlap(geo_results)
        write_json(RESULTS / "lexical_regression.json", lr)
    if "rsa" in which:
        surface_rdm()
        rs = rsa(geo_results)
        rs["name_evocation"] = {m: name_evocation(m, blocks_rec["manifolds"][f"{m}|mname"]["L_star"])
                                for m in ("32b", "8b") if f"{m}|mname" in blocks_rec["manifolds"]}
        write_json(RESULTS / "rsa.json", rs)
    if "placement" in which:
        pl = {}
        for model_tag in ("32b", "8b"):
            for frame in ("mcode_PRIMARY_R1", "mcode_PRIMARY_R2", "mcode_M32_R1"):
                key = f"{model_tag}|{frame}"
                if key in blocks_rec["manifolds"]:
                    r = placement(model_tag, frame, blocks_rec["manifolds"][key]["L_star"])
                    if r:
                        pl[key] = r
                        logger.info(f"placement {key}: LOO {r['G_place']['loo_accuracy']:.2f}; uDij survivors "
                                    f"EDGE {r['udij_survivors']['n_edge']}/{r['udij_survivors']['n']}")
        write_json(RESULTS / "placement.json", pl)


def _desc_overlap(geo_results: dict[str, Any]) -> dict[str, Any]:
    """Descriptive: M-desc description-level g vs D-overlap; M-code algorithm-level g vs mean L1."""
    out: dict[str, Any] = {}
    dv = read_json(DATA / "descriptions_v0.json")
    dov = {(r["algorithm"], r["text"]): r["D_overlap"] for r in dv["descriptions"]}
    lex = read_json(RESULTS / "lexical.json")
    meanL1 = {a: float(np.mean([r["L1"] for r in lex["aliases"] if r["algorithm"] == a])) for a in NB5}
    for model_tag in ("32b", "8b"):
        key = f"{model_tag}|mdesc"
        if key in geo_results:
            m = load_manifold(model_tag, "mdesc")
            L = geo_results[key]["L_star"]["block"]
            X = m["X"][:, m["blocks"].index(L)].astype(np.float64)
            geo, _ = geometry.geodesics(X, K_VERDICT)
            md = read_json(DATA / "mdesc_prompts.json")["rows"]
            txt = {r["desc_id"]: r["text"] for r in md}
            rows = []
            for did in sorted(set(m["desc_id"].tolist())):
                a = did.split("|")[0]
                if a not in NB5:
                    continue
                sel = m["desc_id"] == did
                g = min(float(np.mean(geo[np.ix_(sel, m["labels"] == b)])) for b in B5)
                rows.append({"desc_id": did, "algorithm": a, "g_desc": g,
                             "D_overlap": dov.get((a, txt[did]), _overlap_new(txt[did], dv))})
            if len(rows) >= 4:
                out[key] = {"rows": rows, "spearman_g_Doverlap": float(spearmanr([r["g_desc"] for r in rows],
                                                                                  [r["D_overlap"] for r in rows]
                                                                                  ).statistic)}
        for name in ("mcode_PRIMARY_R1",):
            key = f"{model_tag}|{name}"
            if key in geo_results:
                g = geo_results[key]["L_star"]["describe"][f"k{K_VERDICT}"]["g"]
                al = [a for a in NB5 if a in g]
                out[key] = {"g": g, "mean_L1": meanL1,
                            "spearman_g_meanL1": float(spearmanr([g[a] for a in al], [meanL1[a] for a in al]
                                                                 ).statistic) if len(al) >= 3 else None}
    return out


def _overlap_new(text: str, dv: dict[str, Any]) -> float:
    import stage_cpu

    banned = [r["text"] for r in dv["descriptions"] if r["algorithm"] in B5]
    return max(stage_cpu.jacc(stage_cpu.content_words(text), stage_cpu.content_words(b)) for b in banned)


_ = (ROOT, deviation)
