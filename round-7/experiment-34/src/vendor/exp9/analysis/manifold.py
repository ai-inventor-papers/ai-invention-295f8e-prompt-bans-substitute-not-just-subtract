#!/usr/bin/env python3
"""S11 MANIFOLD AND INTERNALS.

Geometry of the model's own programs in activation coordinates (context 'base': every program, forced or natural,
scrubbed and teacher-forced under a name-free baseline prompt): per task, layers 20-28, positions g16 and pre
(R, g8, g32 as sensitivities), PCA-50, k-NN geodesics, centroid geodesic matrix, SMACOF metric MDS with Kruskal
stress-1, Isomap for per-sample points (natural programs placed with transform()). k in {5, 10, 15, 20}; nearest-
neighbour rank stability over k, layer and position; 200 program-bootstrap resamples. Figures: manifold panels per
condition with landing arrows, k x layer MDS grid, landing bars with committed forecasts, LOS will-vs-can.
Within-ban internals: class-balanced logistic probes (leave-one-template-out, within-template label shuffles, R as the
negative control) and difference-in-means cosines. Persistent H1 against a label-shuffled and a covariance-matched null.
"""

from __future__ import annotations

import collections
import json
import math
from typing import Any

import numpy as np
from loguru import logger

from common import (DATA_DIR, FIG_DIR, LAYERS, MODES, RESULTS_DIR, ROOT, SHORT, read_json, read_jsonl, write_json)

POS = {"g8": 0, "g16": 1, "g32": 2, "pre": 3}
PRIMARY = {"layer": 24, "pos": "pre", "k": 10}
K_SWEEP = (5, 10, 15, 20)
CMAP = "viridis"


def _states(task: str, context: str) -> dict[str, Any]:
    from mb.score import load_states

    return load_states(task, context)


def forced_points(task: str, algs: list[str]) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]]]:
    st = _states(task, "base")
    keep = [i for i, m in enumerate(st["meta"]) if m.get("kind") == "forced" and m.get("algorithm") in algs]
    return st["X"][keep].astype(np.float32), np.array([st["meta"][i]["algorithm"] for i in keep]), \
        [st["meta"][i] for i in keep]


def natural_points(task: str, context: str = "base") -> tuple[np.ndarray, list[dict[str, Any]]]:
    st = _states(task, context)
    keep = [i for i, m in enumerate(st["meta"]) if m.get("kind") == "natural"]
    return st["X"][keep].astype(np.float32), [st["meta"][i] for i in keep]


def pca_fit(Y: np.ndarray, n: int = 50) -> tuple[np.ndarray, np.ndarray]:
    mu = Y.mean(axis=0, keepdims=True)
    _, _, Vt = np.linalg.svd(Y - mu, full_matrices=False)
    return mu, Vt[:min(n, Vt.shape[0])]


def stress1(D: np.ndarray, Z: np.ndarray) -> float:
    from scipy.spatial.distance import pdist, squareform

    E = squareform(pdist(Z))
    iu = np.triu_indices_from(D, 1)
    return float(math.sqrt(((D[iu] - E[iu]) ** 2).sum() / (D[iu] ** 2).sum()))


def mds2(D: np.ndarray) -> tuple[np.ndarray, float]:
    from sklearn.manifold import MDS

    m = MDS(n_components=2, dissimilarity="precomputed", n_init=8, random_state=0, normalized_stress=False)
    Z = m.fit_transform(D)
    return Z, stress1(D, Z)


def nn_rank(D: np.ndarray, algs: list[str]) -> dict[str, list[str]]:
    out = {}
    for i, a in enumerate(algs):
        order = [algs[j] for j in np.argsort(D[i]) if j != i]
        out[a] = order
    return out


# ------------------------------------------------------------------------------------------------ geometry sweep
def geometry_sweep(task: str, algs: list[str]) -> dict[str, Any]:
    from mb.sets import centroid_matrix, knn_geodesic

    X, lab, _ = forced_points(task, algs)
    res: dict[str, Any] = {"algorithms": algs, "n_points": int(len(lab)), "settings": []}
    nn_ref = None
    Dref = None
    for li, l in enumerate(LAYERS):
        for pos in ("g16", "pre", "g8", "g32"):
            Y = X[:, li, POS[pos], :]
            ok = ~np.isnan(Y).any(axis=1)
            mu, V = pca_fit(Y[ok])
            Z = (Y[ok] - mu) @ V.T
            for k in K_SWEEP if pos in ("g16", "pre") else (10,):
                G, info = knn_geodesic(Z, k)
                D = centroid_matrix(G, lab[ok], algs)
                _, st = mds2(D)
                nn = nn_rank(D, algs)
                row = {"layer": l, "position": pos, "k": k, "stress1": st, "bridges": info["bridges"],
                       "nearest": {a: nn[a][0] for a in algs}, "D": D}
                res["settings"].append(row)
                if l == PRIMARY["layer"] and pos == PRIMARY["pos"] and k == PRIMARY["k"]:
                    nn_ref, Dref = nn, D
    agree = [np.mean([s["nearest"][a] == nn_ref[a][0] for a in algs]) for s in res["settings"]]
    res["nearest_neighbour_stability_vs_primary"] = float(np.mean(agree))
    res["primary_D"] = Dref
    # program bootstrap at the primary setting
    li = LAYERS.index(PRIMARY["layer"])
    Y = X[:, li, POS[PRIMARY["pos"]], :]
    ok = ~np.isnan(Y).any(axis=1)
    mu, V = pca_fit(Y[ok])
    Z = (Y[ok] - mu) @ V.T
    G, _ = knn_geodesic(Z, PRIMARY["k"])
    rng = np.random.default_rng(0)
    labs = lab[ok]
    same = []
    for _ in range(200):
        sel = {a: rng.choice(np.where(labs == a)[0], size=(labs == a).sum(), replace=True) for a in algs}
        Db = centroid_matrix(G, labs, algs, sel)
        nb = nn_rank(Db, algs)
        same.append(np.mean([nb[a][0] == nn_ref[a][0] for a in algs]))
    res["bootstrap_nearest_same"] = float(np.mean(same))
    res["primary_nearest"] = {a: nn_ref[a][:3] for a in algs}
    return res


# ------------------------------------------------------------------------------------------------ figures
def isomap_layout(task: str, algs: list[str]) -> dict[str, Any]:
    from sklearn.manifold import Isomap

    X, lab, _ = forced_points(task, algs)
    li = LAYERS.index(PRIMARY["layer"])
    Y = X[:, li, POS[PRIMARY["pos"]], :]
    ok = ~np.isnan(Y).any(axis=1)
    mu, V = pca_fit(Y[ok])
    Z = (Y[ok] - mu) @ V.T
    iso = Isomap(n_neighbors=PRIMARY["k"], n_components=2)
    P = iso.fit_transform(Z)
    Xn, meta = natural_points(task, "base")
    Yn = Xn[:, li, POS[PRIMARY["pos"]], :]
    okn = ~np.isnan(Yn).any(axis=1)
    Pn = np.full((len(meta), 2), np.nan)
    if okn.any():
        Pn[okn] = iso.transform((Yn[okn] - mu) @ V.T)
    cent = {a: P[lab[ok] == a].mean(axis=0) for a in algs}
    return {"P": P, "lab": lab[ok], "Pn": Pn, "meta": meta, "cent": cent,
            "recon_error": float(iso.reconstruction_error())}


def fig_manifold(task: str, algs: list[str], lay: dict[str, Any], conds: list[tuple[str, list[str]]]) -> list[str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    files = []
    for cond, banned in conds:
        idx = [i for i, m in enumerate(lay["meta"]) if m["condition"] == cond]
        if not idx:
            continue
        cnt = collections.Counter(lay["meta"][i]["label"] for i in idx)
        fig, ax = plt.subplots(figsize=(5.2, 4.6))
        ax.scatter(lay["P"][:, 0], lay["P"][:, 1], s=6, c="#c8c8c8", alpha=0.6, label="forced programs")
        pn = lay["Pn"][idx]
        ax.scatter(pn[:, 0], pn[:, 1], s=10, c="#d62728", alpha=0.45, marker="x", label="natural programs")
        mx = max(max(cnt.values()), 1)
        cm = plt.get_cmap(CMAP)
        for a in algs:
            c = lay["cent"][a]
            n = cnt.get(a, 0)
            ax.scatter([c[0]], [c[1]], s=80 + 900 * n / mx, color=cm(n / mx), edgecolor="k", zorder=3)
            ax.annotate(f"{SHORT.get(a, a)} ({n})", c, xytext=(6, 6), textcoords="offset points", fontsize=8)
            if a in banned:
                ax.scatter([c[0]], [c[1]], s=160, marker="x", color="k", linewidths=2.2, zorder=4)
        surv = [a for a in algs if a not in banned]
        land = {a: cnt.get(a, 0) for a in surv}
        if banned and sum(land.values()) > 0:
            src = np.mean([lay["cent"][b] for b in banned if b in lay["cent"]], axis=0)
            dst = sum(lay["cent"][a] * v for a, v in land.items()) / sum(land.values())
            ax.annotate("", xy=dst, xytext=src, arrowprops=dict(arrowstyle="->", lw=2.2, color="#1f77b4"))
        ax.set_title(f"{task.upper()} {cond}: layer {PRIMARY['layer']}, {PRIMARY['pos']}, k={PRIMARY['k']}",
                     fontsize=9)
        ax.set_xlabel("Isomap 1")
        ax.set_ylabel("Isomap 2")
        ax.legend(fontsize=7, loc="best")
        fig.tight_layout()
        stem = f"fig_manifold_{task}_{cond.replace(':', '_')}"
        for ext in ("png", "pdf"):
            fig.savefig(FIG_DIR / f"{stem}.{ext}", dpi=150)
        plt.close(fig)
        files.append(stem)
    return files


def fig_kstab(task: str, algs: list[str], sweep: dict[str, Any]) -> str:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    layers = [20, 22, 24, 26, 28]
    fig, axes = plt.subplots(len(K_SWEEP), len(layers), figsize=(2.4 * len(layers), 2.3 * len(K_SWEEP)))
    for i, k in enumerate(K_SWEEP):
        for j, l in enumerate(layers):
            ax = axes[i, j]
            row = next((s for s in sweep["settings"] if s["layer"] == l and s["k"] == k and s["position"] == "pre"),
                       None)
            if row is None:
                ax.axis("off")
                continue
            Z, st = mds2(np.array(row["D"]))
            ax.scatter(Z[:, 0], Z[:, 1], s=18)
            for a, z in zip(algs, Z):
                ax.annotate(SHORT.get(a, a), z, fontsize=6)
            ax.set_title(f"L{l} k={k} s1={st:.2f}", fontsize=7)
            ax.set_xticks([])
            ax.set_yticks([])
    fig.tight_layout()
    stem = f"fig_kstab_{task}"
    for ext in ("png", "pdf"):
        fig.savefig(FIG_DIR / f"{stem}.{ext}", dpi=130)
    plt.close(fig)
    return stem


def fig_landing(landing: dict[str, Any]) -> str | None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sets = [s for s in landing.get("tests", {})]
    if not sets:
        return None
    fig, axes = plt.subplots(1, len(sets), figsize=(3.6 * len(sets), 3.8), squeeze=False)
    for ax, s in zip(axes[0], sets):
        c = landing["conditions"][f"t1|multi:{s}"]
        fc = read_json(ROOT / "predictions" / f"forecasts_{s}.json")
        cats = fc["survivors"] + ["banned", "other"]
        n = max(c["attempted"], 1)
        vals = [c["counts"].get(x, 0) / n for x in fc["survivors"]]
        vals.append(sum(v for k, v in c["counts"].items() if k.startswith("banned:")) / n)
        vals.append(c["counts"].get("other", 0) / n)
        ax.bar(range(len(cats)), vals, color=["#4c72b0"] * len(fc["survivors"]) + ["#c44e52", "#999999"])
        mk = {"LADDER": "o", "PRIME_AND_VETO": "s", "PROXIMITY": "^", "FRLP_BAN": "D", "GENERIC": "v", "CORPUS": "*"}
        surv_mass = sum(vals[:len(fc["survivors"])])
        for f, m in mk.items():
            if f not in fc["forecasts_raw"]:
                continue
            ys = [fc["forecasts_raw"][f][x] * surv_mass for x in fc["survivors"]]
            ax.scatter(range(len(fc["survivors"])), ys, marker=m, s=28, label=f, zorder=3, edgecolor="k")
        ax.set_xticks(range(len(cats)))
        ax.set_xticklabels([SHORT.get(x, x) for x in cats], rotation=45, fontsize=8)
        ax.set_title(f"{s}: ban {', '.join(SHORT.get(b, b) for b in fc['banned'])}", fontsize=8)
        ax.set_ylim(0, 1)
    axes[0][0].set_ylabel("share of attempted programs")
    axes[0][-1].legend(fontsize=6, loc="upper right")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIG_DIR / f"fig_landing.{ext}", dpi=150)
    plt.close(fig)
    return "fig_landing"


def fig_los(los: dict[str, Any]) -> str | None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if not los:
        return None
    keys = list(los)
    will = [los[k]["will_attempted_share"] for k in keys]
    can = [los[k]["can_labelled_as_requested"] for k in keys]
    fig, ax = plt.subplots(figsize=(5, 3.6))
    x = np.arange(len(keys))
    ax.bar(x - 0.2, will, 0.4, label="will (share under ban-the-other-four)")
    ax.bar(x + 0.2, can, 0.4, label="can (forced: labelled as requested)")
    ax.set_xticks(x)
    ax.set_xticklabels([SHORT.get(k, k) for k in keys])
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=7)
    ax.set_title("T2 leave-one-survivor: will vs can", fontsize=9)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIG_DIR / f"fig_los.{ext}", dpi=150)
    plt.close(fig)
    return "fig_los"


# ------------------------------------------------------------------------------------------------ internals (probes)
def within_ban_probes(task: str, cond: str, rng: np.random.Generator) -> dict[str, Any] | None:
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import balanced_accuracy_score
    from sklearn.preprocessing import StandardScaler

    st = _states(task, "own")
    idx = [i for i, m in enumerate(st["meta"]) if m["condition"] == cond]
    labs = [st["meta"][i]["label"] for i in idx]
    cnt = collections.Counter(labs)
    cls = [c for c, v in cnt.items() if v >= 10]
    if len(cls) < 2:
        return None
    cls = [c for c, _ in cnt.most_common() if c in cls][:2]
    idx = [i for i, l in zip(idx, labs) if l in cls]
    y = np.array([cls.index(st["meta"][i]["label"]) for i in idx])
    tpl = np.array([st["meta"][i]["template"] for i in idx])
    X = st["X"][idx].astype(np.float32)
    Rk = [st["meta"][i]["prompt_key"] for i in idx]
    R = np.stack([st["R"][k] for k in Rk]).astype(np.float32)

    def cv_bacc(F: np.ndarray, yy: np.ndarray) -> float:
        preds = np.zeros_like(yy)
        for t in np.unique(tpl):
            tr, te = tpl != t, tpl == t
            if len(np.unique(yy[tr])) < 2:
                preds[te] = yy[tr][0] if tr.any() else 0
                continue
            Ft = F[tr]
            mu, V = pca_fit(Ft, 50)
            Ztr, Zte = (Ft - mu) @ V.T, (F[te] - mu) @ V.T
            sc = StandardScaler().fit(Ztr)
            clf = LogisticRegression(C=0.1, class_weight="balanced", max_iter=2000)
            clf.fit(sc.transform(Ztr), yy[tr])
            preds[te] = clf.predict(sc.transform(Zte))
        return float(balanced_accuracy_score(yy, preds))

    def shuffled(yy: np.ndarray) -> np.ndarray:
        out = yy.copy()
        for t in np.unique(tpl):
            m = tpl == t
            out[m] = rng.permutation(yy[m])
        return out

    res: dict[str, Any] = {"classes": cls, "n": {c: int((y == i).sum()) for i, c in enumerate(cls)}, "acc": {}}
    for li, l in enumerate(LAYERS):
        for pos in ("R", "g8", "g16", "g32", "pre"):
            F = R[:, li, :] if pos == "R" else X[:, li, POS[pos], :]
            ok = ~np.isnan(F).any(axis=1)
            if ok.sum() < 20:
                continue
            res["acc"][f"L{l}|{pos}"] = cv_bacc(F[ok], y[ok])
    # shuffled-label nulls at the primary layer
    li = LAYERS.index(PRIMARY["layer"])
    res["null"] = {}
    for pos in ("R", "g16", "pre"):
        F = R[:, li, :] if pos == "R" else X[:, li, POS[pos], :]
        ok = ~np.isnan(F).any(axis=1)
        obs = res["acc"].get(f"L{PRIMARY['layer']}|{pos}")
        nulls = [cv_bacc(F[ok], shuffled(y)[ok]) for _ in range(100)]
        res["null"][pos] = {"observed": obs, "null_mean": float(np.mean(nulls)),
                            "null_95": float(np.percentile(nulls, 95)),
                            "p": float((np.array(nulls) >= (obs or 0) - 1e-12).mean()) if obs is not None else None}
    gen = {k: v for k, v in res["acc"].items() if not k.endswith("|R")}
    res["best_generated"] = max(gen.items(), key=lambda kv: kv[1]) if gen else None
    # difference-in-means cosine: natural (base context) vs forced centroids
    stb = _states(task, "base")
    nat = [i for i, m in enumerate(stb["meta"]) if m.get("kind") == "natural" and m["condition"] == cond
           and m["label"] in cls]
    frc = [i for i, m in enumerate(stb["meta"]) if m.get("kind") == "forced" and m.get("algorithm") in cls]
    cos = {}
    for pos in ("g16", "pre"):
        for l in (20, 24, 28):
            li = LAYERS.index(l)
            A = stb["X"][nat][:, li, POS[pos], :].astype(np.float32)
            la = np.array([stb["meta"][i]["label"] for i in nat])
            Bf = stb["X"][frc][:, li, POS[pos], :].astype(np.float32)
            lb = np.array([stb["meta"][i]["algorithm"] for i in frc])
            if any((la == c).sum() == 0 for c in cls) or any((lb == c).sum() == 0 for c in cls):
                continue
            dn = np.nanmean(A[la == cls[1]], 0) - np.nanmean(A[la == cls[0]], 0)
            dfc = np.nanmean(Bf[lb == cls[1]], 0) - np.nanmean(Bf[lb == cls[0]], 0)
            cos[f"L{l}|{pos}"] = float(dn @ dfc / (np.linalg.norm(dn) * np.linalg.norm(dfc) + 1e-12))
    res["dim_cosine_natural_vs_forced"] = {"direction": f"{cls[1]} - {cls[0]}", **cos}
    return res


# ------------------------------------------------------------------------------------------------ persistence
def persistence(task: str, algs: list[str], rng: np.random.Generator) -> dict[str, Any]:
    from ripser import ripser

    X, lab, _ = forced_points(task, algs)
    li = LAYERS.index(PRIMARY["layer"])
    Y = X[:, li, POS[PRIMARY["pos"]], :]
    ok = ~np.isnan(Y).any(axis=1)
    mu, V = pca_fit(Y[ok])
    Z = (Y[ok] - mu) @ V.T
    lab = lab[ok]

    def h1_stats(P: np.ndarray) -> tuple[float, float]:
        dg = ripser(P, maxdim=1)["dgms"][1]
        if len(dg) == 0:
            return 0.0, 0.0
        life = np.sort(dg[:, 1] - dg[:, 0])[::-1]
        return float(life[0]), float(life[0] / life[1]) if len(life) > 1 and life[1] > 0 else float("inf")

    def boot_cloud(labels: np.ndarray) -> np.ndarray:
        pts = []
        for a in algs:
            ids = np.where(labels == a)[0]
            for _ in range(40):
                pts.append(Z[rng.choice(ids, size=len(ids), replace=True)].mean(0))
        return np.array(pts)

    obs_life, obs_ratio = h1_stats(boot_cloud(lab))
    null = [h1_stats(boot_cloud(rng.permutation(lab)))[0] for _ in range(200)]
    p_shuf = float((np.array(null) >= obs_life).mean())
    life2, ratio2 = h1_stats(Z)
    cov = np.cov(Z.T)
    gnull = [h1_stats(rng.multivariate_normal(np.zeros(Z.shape[1]), cov, size=len(Z)))[0] for _ in range(100)]
    p_gauss = float((np.array(gnull) >= life2).mean())
    persist = []
    for _ in range(50):
        sub = rng.choice(len(Z), size=int(0.8 * len(Z)), replace=False)
        l2, _ = h1_stats(Z[sub])
        persist.append(l2 >= np.percentile(gnull, 95))
    frac = float(np.mean(persist))
    circle = p_shuf < 0.05 and p_gauss < 0.05 and frac >= 0.8
    return {"layer": PRIMARY["layer"], "position": PRIMARY["pos"],
            "centroid_bootstrap": {"max_h1_lifetime": obs_life, "ratio_to_second": obs_ratio,
                                   "label_shuffled_null_mean": float(np.mean(null)), "p": p_shuf, "n_null": 200},
            "per_sample": {"max_h1_lifetime": life2, "ratio_to_second": ratio2,
                           "gaussian_null_mean": float(np.mean(gnull)), "p": p_gauss, "n_null": 100,
                           "subsample80_persistence": frac, "n_subsamples": 50},
            "verdict": "circle" if circle else "no evidence of a loop",
            "note": "descriptive: persistent H1 on a handful of algorithm clouds is weakly powered"}


# ------------------------------------------------------------------------------------------------ main
def run_manifold() -> None:
    rng = np.random.default_rng(0)
    keep = read_json(RESULTS_DIR / "catalogue_keep.json")
    psets = read_json(DATA_DIR / "program_sets.json")
    out: dict[str, Any] = {"primary": PRIMARY, "tasks": {}}
    landing = read_json(RESULTS_DIR / "landing.json") if (RESULTS_DIR / "landing.json").exists() else {}
    los = read_json(RESULTS_DIR / "los.json") if (RESULTS_DIR / "los.json").exists() else {}
    plan = read_json(RESULTS_DIR / "planned_conditions.json")
    for task in MODES:
        algs = [k.split(":")[1] for k in psets if k.startswith(task + ":")]
        sweep = geometry_sweep(task, algs)
        lay = isomap_layout(task, algs)
        if task == "t1":
            conds = [("baseline", []), ("single:bfs", ["bfs"])] + [(f"multi:{s}", p["banned"])
                                                                    for s, p in plan["t1"].items()]
        else:
            conds = [("baseline", []), ("single:dijkstra", ["dijkstra"])] + [
                (f"los:{s}", [a for a in MODES["t2"] if a != s]) for s in MODES["t2"]]
        files = fig_manifold(task, algs, lay, conds)
        ks = fig_kstab(task, algs, sweep)
        D = np.array(sweep["primary_D"])
        Zc, st = mds2(D)
        out["tasks"][task] = {
            "algorithms": algs, "primary_centroid_D": D, "primary_mds": {a: z for a, z in zip(algs, Zc.tolist())},
            "primary_stress1": st, "isomap_reconstruction_error": lay["recon_error"],
            "nearest_neighbour_stability_vs_primary": sweep["nearest_neighbour_stability_vs_primary"],
            "bootstrap_nearest_same": sweep["bootstrap_nearest_same"], "primary_nearest": sweep["primary_nearest"],
            "sweep": [{k: v for k, v in s.items() if k != "D"} for s in sweep["settings"]],
            "figures": files + [ks],
            "isomap_centroids": {a: v.tolist() for a, v in lay["cent"].items()}}
        logger.info(f"manifold {task}: stress1 {st:.3f}; NN stability {sweep['nearest_neighbour_stability_vs_primary']:.2f}")
    # internals
    probes = {}
    for task, cond in [("t1", "single:bfs"), ("t2", "single:dijkstra")] + [("t2", f"los:{s}") for s in MODES["t2"]] + \
            [("t1", f"multi:{s}") for s in plan["t1"]]:
        try:
            r = within_ban_probes(task, cond, rng)
        except (ValueError, KeyError, IndexError) as e:
            logger.warning(f"probe {task} {cond} failed: {e}")
            r = {"error": str(e)}
        if r is not None:
            probes[f"{task}|{cond}"] = r
            logger.info(f"probe {task}|{cond}: best {r.get('best_generated')}; null {r.get('null')}")
    out["within_ban_internals"] = probes
    write_json(RESULTS_DIR / "manifold.json", out)
    pers = {}
    for task in MODES:
        algs = [k.split(":")[1] for k in psets if k.startswith(task + ":")]
        pers[task] = persistence(task, algs, rng)
        logger.info(f"persistence {task}: {pers[task]['verdict']}")
    write_json(RESULTS_DIR / "persistence.json", pers)
    figs = [fig_landing(landing) if landing else None, fig_los(los)]
    logger.info(f"figures: {figs}")


__all__ = ["run_manifold", "json"]
