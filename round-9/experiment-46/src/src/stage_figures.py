#!/usr/bin/env python3
"""Stage 11 figures (PDF + PNG), all in actual activation coordinates unless labelled otherwise.

Per model x manifold: (a) PCA of the points with centroids sized/coloured by implemented counts (C6 baseline; C6
ban screen + confirm), banned algorithms outlined, ban-prompt states as stars (S-mean manifolds) or survivor
programs as crosses (M-code); (b) classical MDS of points and centroids; (c) Isomap at the verdict k with the
geodesic path from unit-weight Dijkstra to its nearest banned algorithm. Plus the class table heatmap, RDM heatmaps
and the behavioural MDS ('behavioural coordinates, not activations')."""

from __future__ import annotations

from collections import Counter
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402
from scipy.sparse.csgraph import shortest_path  # noqa: E402

import geometry  # noqa: E402
from common import CANON_ORDER, SHORT, read_json, read_jsonl  # noqa: E402
from tpg import B5, DATA, IN_E44, K_VERDICT, MODELS, NB5, RESULTS, ROOT, STATES_DIR, UDIJ  # noqa: E402

FIG = ROOT / "figures"
COL = dict(zip(CANON_ORDER, plt.cm.tab10(np.linspace(0, 1, 10))))
TITLES = {"mname": "M-name (alias prompts, S-mean)", "mdesc": "M-desc (name-free descriptions, S-mean)",
          "mlex": "M-lex (alias minus neutral twin, S-mean delta)",
          "mcode_PRIMARY_R1": "M-code PRIMARY (mean over code tokens, R1)",
          "mcode_PRIMARY_R2": "M-code PRIMARY (pop-position token, R2)",
          "mcode_M32_R1": "M-code Qwen3-32B-only frame (R1)", "mcode_M8_R1": "M-code Qwen3-8B-only frame (R1)",
          "mcode_PRIMARY_R1g": "M-code PRIMARY (R1 without massive tokens)",
          "mcode_PRIMARY_R3": "M-code PRIMARY (16th code token, R3: negative control)"}


def _save(fig: Any, name: str) -> None:
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIG / f"{name}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def counts() -> tuple[Counter, Counter]:
    base = Counter(r.get("adj_label") for r in read_jsonl(IN_E44 / "data" / "labelled_C6_baseline.jsonl"))
    ban = Counter(r.get("adj_label") for f in ("labelled_C6_ban.jsonl", "labelled_C6_confirm.jsonl")
                  for r in read_jsonl(IN_E44 / "data" / f))
    return base, ban


def _overlay(model_tag: str, name: str, z: Any) -> tuple[np.ndarray | None, str]:
    comps, mean, L = z["pca_components"], z["pca_mean"], int(z["block"])
    if name in ("mname", "mdesc"):
        f = STATES_DIR / f"ban_{model_tag}.npz"
        if f.exists():
            b = np.load(f)
            Q = b["smean"][:, [int(x) for x in b["blocks"]].index(L)].astype(np.float32)
            return (Q - mean) @ comps.T, "7 ban prompts (W1-W5, P6, P7)"
    if name.startswith("mcode"):
        f = STATES_DIR / f"mcode_{model_tag}.npz"
        if f.exists():
            m = np.load(f)
            ro = name.split("_")[2]
            ri = list(m["readouts"]).index(ro)
            ms = read_json(DATA / "mcode_sets.json")
            keys = list(m["keys"])
            sel = [keys.index(p["scrubbed_sha256"]) for p in ms["placement"] if p["set"] == "SURV" and
                   p["algorithm"] == UDIJ and p["scrubbed_sha256"] in keys]
            if sel:
                Q = m["R"][sel, ri, [int(x) for x in m["blocks"]].index(L)].astype(np.float32)
                return (Q - mean) @ comps.T, f"{len(sel)} unit-Dijkstra survivor programs (C6)"
    return None, ""


def manifold_figs(model_tag: str, name: str, geo_res: dict[str, Any]) -> None:
    f = FIG / "coords" / f"{model_tag}_{name}.npz"
    if not f.exists():
        return
    z = np.load(f, allow_pickle=False)
    labels = z["labels"]
    L = int(z["block"])
    present = [a for a in CANON_ORDER if a in set(labels.tolist())]
    base, ban = counts()
    cfg = MODELS[model_tag]
    prec = "nf4" if model_tag == "32b" else "bf16"
    mdl = "Qwen3-32B" if model_tag == "32b" else "Qwen3-8B"
    readout = "SPEC-token mean (S-mean)" if not name.startswith("mcode") else TITLES[name].split("(")[-1].rstrip(")")
    cap = f"{mdl} {prec}, block {L}, readout {readout}, N={len(labels)}"
    P = z["pca2"]
    evr = z["evr"]
    Q, qlab = _overlay(model_tag, name, z)
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    for ax, (cnt, ttl) in zip(axes, ((base, "C6 baseline implemented counts"), (ban, "C6 ban implemented counts "
                                                                                    "(screen + confirm)"))):
        for a in present:
            s = labels == a
            ax.scatter(P[s, 0], P[s, 1], s=10, color=COL[a], alpha=0.35)
        vmax = max(1, max(cnt.get(a, 0) for a in present))
        for a in present:
            c = P[labels == a].mean(0)
            n = cnt.get(a, 0)
            ax.scatter([c[0]], [c[1]], s=60 + 40 * np.sqrt(n + 1), c=[[n / vmax]], cmap="viridis", vmin=0, vmax=1,
                       edgecolors="red" if a in B5 else "black", linewidths=2.5 if a in B5 else 1.0, zorder=5)
            ax.annotate(f"{SHORT[a]} ({n})", c, fontsize=8, xytext=(4, 4), textcoords="offset points")
        if Q is not None:
            mk = "*" if not name.startswith("mcode") else "x"
            ax.scatter(Q[:, 0], Q[:, 1], marker=mk, s=110 if mk == "*" else 45, color="black", label=qlab, zorder=6)
            ax.legend(loc="best", fontsize=8)
        elif not name.startswith("mcode"):
            c = P[labels == UDIJ].mean(0) if UDIJ in present else None
            if c is not None:
                th = np.linspace(0, 2 * np.pi, 15, endpoint=False)
                r = 0.04 * (P.max() - P.min())
                ax.scatter(c[0] + r * np.cos(th), c[1] + r * np.sin(th), s=12, marker="o", facecolors="none",
                           edgecolors="black", label="15 unit-Dijkstra survivors (label-level)")
                ax.legend(loc="best", fontsize=8)
        ax.set_xlabel(f"PC1 ({100 * evr[0]:.1f}% var.)")
        ax.set_ylabel(f"PC2 ({100 * evr[1]:.1f}% var.)")
        ax.set_title(ttl, fontsize=10)
    fig.suptitle(f"(a) PCA of residual states: {TITLES[name]}\n{cap}; banned (red outline): "
                 f"{', '.join(SHORT[b] for b in B5)}", fontsize=10)
    _save(fig, f"pca_{model_tag}_{name}")
    # (b) MDS
    d = geo_res["L_star"]["describe"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    Ym = z["mds"]
    for a in present:
        s = labels == a
        axes[0].scatter(Ym[s, 0], Ym[s, 1], s=10, color=COL[a], label=SHORT[a], alpha=0.6)
    axes[0].legend(fontsize=7, ncol=2)
    axes[0].set_title(f"classical MDS of the {len(labels)} points (stress-1 {d['mds_points_stress1']:.2f})", fontsize=10)
    Yc = z["mds_c"]
    for i, a in enumerate(present):
        axes[1].scatter([Yc[i, 0]], [Yc[i, 1]], s=120, color=COL[a], edgecolors="red" if a in B5 else "black",
                        linewidths=2.5 if a in B5 else 1)
        axes[1].annotate(SHORT[a], Yc[i], fontsize=9, xytext=(5, 5), textcoords="offset points")
    axes[1].set_title(f"classical MDS of the {len(present)} centroids (stress-1 {d['mds_centroids_stress1']:.2f})",
                      fontsize=10)
    for ax in axes:
        ax.set_xlabel("MDS 1")
        ax.set_ylabel("MDS 2")
    fig.suptitle(f"(b) {TITLES[name]} - {cap}", fontsize=10)
    _save(fig, f"mds_{model_tag}_{name}")
    # (c) Isomap with geodesic path uDij -> nearest banned
    Y = z["iso"]
    if len(Y):
        geo = z["geo"]
        fig, ax = plt.subplots(figsize=(8, 7))
        for a in present:
            s = labels == a
            ax.scatter(Y[s, 0], Y[s, 1], s=12, color=COL[a], label=SHORT[a], alpha=0.7,
                       edgecolors="red" if a in B5 else "none", linewidths=0.6)
        kd = d[f"k{K_VERDICT}"]
        if UDIJ in present:
            nb = kd["nearest_banned"][UDIJ]
            iu = np.where(labels == UDIJ)[0]
            ib = np.where(labels == nb)[0]
            sub = geo[np.ix_(iu, ib)]
            i, j = np.unravel_index(np.argmin(sub), sub.shape)
            X = np.load(STATES_DIR / f"geo_{model_tag}_{name}_k{K_VERDICT}.npz")
            G = X["adjacency"]
            _, pred = shortest_path(G, method="D", directed=False, indices=[iu[i]], return_predecessors=True)
            path, cur = [], ib[j]
            while cur >= 0 and cur != iu[i]:
                path.append(cur)
                cur = pred[0, cur]
            path.append(iu[i])
            ax.plot(Y[path, 0], Y[path, 1], "k-", lw=1.5, label=f"geodesic {SHORT[UDIJ]} -> {SHORT[nb]}")
            ttl = (f"class(uDij)={kd['classes'][UDIJ]}, g={kd['g'][UDIJ]:.2f}, median {kd['median']:.2f}, "
                   f"rank {kd['udij_rank']}/{len(kd['g'])}")
        else:
            ttl = "unit Dijkstra not in this manifold"
        ax.legend(fontsize=7, ncol=2)
        ax.set_xlabel("Isomap 1")
        ax.set_ylabel("Isomap 2")
        ax.set_title(f"(c) Isomap k={K_VERDICT}: {TITLES[name]}\n{cap}; {ttl}", fontsize=9)
        _save(fig, f"isomap_{model_tag}_{name}")
    _ = cfg


def class_table(geo_all: dict[str, Any]) -> None:
    rows, cells, txt = [], [], []
    cmap = {"EDGE": 0, "MIDDLE": 1, "OPPOSITE": 2}
    for key, r in geo_all.items():
        if r is None:
            continue
        kd = r["L_star"]["describe"][f"k{K_VERDICT}"]
        rows.append(f"{key} (L{r['L_star']['block']})")
        cells.append([cmap.get(kd["classes"].get(a), np.nan) for a in NB5])
        txt.append([(f"{kd['classes'][a][:3]}\n{kd['g'][a] / kd['median']:.2f}" if a in kd["classes"] else "not run")
                    for a in NB5])
    if not rows:
        return
    fig, ax = plt.subplots(figsize=(9, 0.55 * len(rows) + 1.5))
    ax.imshow(np.array(cells, dtype=float), cmap="coolwarm", vmin=0, vmax=2, aspect="auto")
    for i in range(len(rows)):
        for j in range(5):
            ax.text(j, i, txt[i][j], ha="center", va="center", fontsize=7,
                    fontweight="bold" if NB5[j] == UDIJ else "normal")
    ax.set_xticks(range(5), [SHORT[a] for a in NB5])
    ax.set_yticks(range(len(rows)), rows, fontsize=7)
    ax.set_title(f"EDGE / MIDDLE / OPPOSITE of the non-banned algorithms (k={K_VERDICT}, cell = class, g/median)",
                 fontsize=9)
    _save(fig, "class_table")


def rdm_figs() -> None:
    rs = read_json(RESULTS / "rsa.json") if (RESULTS / "rsa.json").exists() else {}
    beh = read_json(RESULTS / "behavioural_distance.json")
    lex = read_json(RESULTS / "lexical.json")
    mats = {"R_beh (behavioural)": np.array(beh["d_beh_lambda0.5"]), "R_lex (alias 3-grams)": np.array(lex["R_lex"])}
    sur = RESULTS / "surface_rdm.json"
    if sur.exists():
        mats["R_surface (AST 4-grams)"] = np.array(read_json(sur)["R_surface"])
    geo_all = read_json(RESULTS / "geometry_all.json")
    for key in ("32b|mname", "32b|mdesc", "32b|mlex", "32b|mcode_PRIMARY_R1"):
        if key in geo_all:
            M = np.array(geo_all[key]["L_star"]["describe"][f"k{K_VERDICT}"]["class_geodesic_matrix"])
            M = (M + M.T) / 2
            np.fill_diagonal(M, 0)
            r = rs.get(key, {}).get("models", {})
            lab = f"{key} neural; rho beh {r.get('R_beh', {}).get('rho', float('nan')):.2f}, lex " \
                  f"{r.get('R_lex', {}).get('rho', float('nan')):.2f}"
            mats[lab] = M
    n = len(mats)
    fig, axes = plt.subplots(2, (n + 1) // 2, figsize=(4.2 * ((n + 1) // 2), 8.5))
    for ax, (t, M) in zip(axes.ravel(), mats.items()):
        ax.imshow(np.nan_to_num(M), cmap="magma")
        ax.set_xticks(range(10), [SHORT[a] for a in CANON_ORDER], rotation=90, fontsize=7)
        ax.set_yticks(range(10), [SHORT[a] for a in CANON_ORDER], fontsize=7)
        ax.set_title(t, fontsize=7)
    for ax in axes.ravel()[n:]:
        ax.axis("off")
    _save(fig, "rdms")
    Y = beh["behavioural_coordinates_mds"]
    fig, ax = plt.subplots(figsize=(6, 5))
    for a in CANON_ORDER:
        ax.scatter([Y[a][0]], [Y[a][1]], s=120, color=COL[a], edgecolors="red" if a in B5 else "black",
                   linewidths=2.5 if a in B5 else 1)
        ax.annotate(SHORT[a], Y[a], xytext=(5, 5), textcoords="offset points")
    ax.set_title(f"Behavioural coordinates, not activations: classical MDS of d_beh\n(expansion-order traces of the "
                 f"15 T1 references on 40 probe grids; stress-1 {beh['behavioural_mds_stress1']:.2f})", fontsize=9)
    ax.set_xlabel("behavioural MDS 1")
    ax.set_ylabel("behavioural MDS 2")
    _save(fig, "behavioural_mds")


def lexical_fig() -> None:
    lr = read_json(RESULTS / "lexical_regression.json") if (RESULTS / "lexical_regression.json").exists() else {}
    r = lr.get("32b|mname")
    if not r:
        return
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for ax, k in zip(axes, ("k10", "k15")):
        rows = r[k]["rows"]
        for row in rows:
            ax.scatter(row["L1"] + np.random.default_rng(len(row["alias"] if "alias" in row else "") + row[
                "alias_index"]).uniform(-0.08, 0.08), row["g_alias"], color=COL[row["algorithm"]], s=50)
        for a in NB5:
            ax.scatter([], [], color=COL[a], label=SHORT[a])
        ax.set_xlabel("L1 = banned algorithms whose alias regex matches the alias")
        ax.set_ylabel("g_alias (min mean geodesic to a banned algorithm)")
        ax.set_title(f"M-name alias level, {k}: Spearman {r[k]['spearman_L1']:.2f} (perm p {r[k]['perm_p_L1']:.4f})",
                     fontsize=9)
        ax.legend(fontsize=7)
    _save(fig, "lexical_alias_level_32b")


def stage_figures(*args: str) -> None:
    FIG.mkdir(exist_ok=True)
    geo_all = read_json(RESULTS / "geometry_all.json")
    for key, r in geo_all.items():
        if r is None:
            continue
        m, name = key.split("|")
        try:
            manifold_figs(m, name, r)
        except (ValueError, KeyError, IndexError, FileNotFoundError) as e:
            logger.error(f"figure {key} failed: {type(e).__name__}: {e}")
    class_table(geo_all)
    rdm_figs()
    lexical_fig()
    logger.info(f"figures: {len(list(FIG.glob('*.png')))} PNG files")
