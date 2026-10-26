#!/usr/bin/env python3
"""Figures F1-F8 (matplotlib, PNG + PDF). Every geometry figure is drawn in actual activation coordinates (PCA /
classical MDS / Isomap of S-mean or per-sample residual states), never as summary bars. Centroid marker area is
proportional to sqrt(baseline implemented count + 1), centroid colour = count on a log colour bar, the banned five are
ringed in red, and survivor algorithms are annotated with their survivor counts."""

from __future__ import annotations

import collections
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LogNorm  # noqa: E402

from common import CANON_ORDER, CONFIGS, FIGS, SHORT  # noqa: E402

plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "pdf.fonttype": 42, "ps.fonttype": 42})
CMAP = plt.get_cmap("tab10")
ALG_COLOR = {a: CMAP(i) for i, a in enumerate(CANON_ORDER)}


def _save(fig: Any, name: str) -> None:
    for ext in ("png", "pdf"):
        fig.savefig(FIGS / f"{name}.{ext}", dpi=150, bbox_inches="tight")
    plt.close(fig)


def _engine(ms: str) -> str:
    from common import STATE_CHECKPOINTS

    c = CONFIGS.get(ms, {})
    ck = STATE_CHECKPOINTS.get(ms, {})
    return f"{ms} {c.get('name', '')} | states: {ck.get('repo', '')} [{ck.get('precision', '')}]"


def _panel(ax: Any, Y: np.ndarray, labels: np.ndarray, banned: list[str], impl: dict[str, int],
           surv_counts: dict[str, int], title: str, xlabel: str, ylabel: str, overlays: dict[str, Any] | None = None,
           okey: str | None = None, norm: Any = None, show_points: bool = True) -> Any:
    sc = None
    for a in CANON_ORDER:
        mk = labels == a
        if show_points:
            ax.scatter(Y[mk, 0], Y[mk, 1], s=10, color=ALG_COLOR[a], alpha=0.45, lw=0)
    cents = np.stack([Y[labels == a].mean(0) for a in CANON_ORDER])
    counts = np.array([impl.get(a, 0) for a in CANON_ORDER], dtype=float)
    sizes = 60 + 220 * np.sqrt(counts + 1)
    sc = ax.scatter(cents[:, 0], cents[:, 1], s=sizes, c=counts + 1, cmap="viridis", norm=norm, edgecolor="k",
                    lw=0.8, zorder=4)
    for i, a in enumerate(CANON_ORDER):
        if a in banned:
            ax.scatter(cents[i, 0], cents[i, 1], s=sizes[i] * 1.9, facecolor="none", edgecolor="red", lw=2.0,
                       zorder=5)
        txt = f"{SHORT[a]} ({int(counts[i])})"
        if surv_counts.get(a):
            txt += f"\nsurv {surv_counts[a]}"
        ax.annotate(txt, cents[i], xytext=(6, 6), textcoords="offset points", fontsize=8, weight="bold",
                    color="darkred" if a in banned else "black", zorder=6)
    if overlays and okey:
        mk = {"baseline": ("o", "black", "baseline prompts"), "ban": ("X", "red", "screen ban prompts W1-W3"),
              "confirm": ("P", "purple", "held-out ban prompts W4/W5/P6/P7")}
        for kd, (m, c, lab) in mk.items():
            if kd in overlays and len(overlays[kd][okey]):
                Q = np.array(overlays[kd][okey])[:, :2]
                ax.scatter(Q[:, 0], Q[:, 1], marker=m, s=70, color=c, edgecolor="white", lw=0.6, zorder=7, label=lab)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    return sc


def manifold_figures(m: dict[str, Any], X: np.ndarray, labels: np.ndarray, banned: list[str], impl: dict[str, int],
                     over: dict[str, Any], L: int, kp: int, ms: str, tag: str, surv: list[str], att: list[str]) -> None:
    sc_counts = dict(collections.Counter(surv))
    norm = LogNorm(vmin=1, vmax=max(2, max([impl.get(a, 0) for a in CANON_ORDER]) + 1))
    emb = m["_emb"]
    pca = emb["pca"]
    P = pca.transform(X)
    ev = m["pca_evr"]
    # F2 PCA
    fig, ax = plt.subplots(figsize=(8.5, 7))
    sc = _panel(ax, P[:, :2], labels, banned, impl, sc_counts,
                f"F2  PCA of forced-prompt S-mean states, block {L}  ({_engine(ms)})",
                f"PC1 ({ev[0]:.1%} var)", f"PC2 ({ev[1]:.1%} var)", over, "pca", norm)
    cb = fig.colorbar(sc, ax=ax)
    cb.set_label("baseline implemented count + 1 (log)")
    ax.legend(loc="best", fontsize=7)
    _legend_algs(ax)
    _save(fig, f"F2_pca_{tag}")
    # F3 MDS (points + centroids)
    fig, axs = plt.subplots(1, 2, figsize=(15, 6.5))
    _panel(axs[0], emb["mds_points"], labels, banned, impl, sc_counts,
           f"F3a classical MDS of 300 forced states, block {L} (Kruskal stress-1 = {m['mds_points_stress1']:.3f})",
           "MDS-1", "MDS-2", None, None, norm)
    Yc = emb["mds_centroids"]
    lab_c = np.array(CANON_ORDER)
    sc = _panel(axs[1], Yc, lab_c, banned, impl, sc_counts,
                f"F3b classical MDS of the 10 centroids (stress-1 = {m['mds_centroids_stress1']:.3f})",
                "MDS-1", "MDS-2", None, None, norm, show_points=False)
    fig.colorbar(sc, ax=axs[1]).set_label("baseline implemented count + 1 (log)")
    fig.suptitle(f"{_engine(ms)}", fontsize=9)
    _legend_algs(axs[0])
    _save(fig, f"F3_mds_{tag}")
    # F4 Isomap k5/k10/k15
    fig, axs = plt.subplots(1, 3, figsize=(21, 6.5))
    for ax, k in zip(axs, (5, 10, 15)):
        iso, Y = emb["isomap"][k]
        info = m[f"k{k}"]
        cl = info["classes"]
        sc = _panel(ax, Y, labels, banned, impl, sc_counts,
                    f"Isomap k={k} (kNN components {info['components_before_join']})\nclasses: "
                    + ", ".join(f"{SHORT[a]}:{c[0]}" for a, c in cl.items()),
                    f"Isomap-1 (k={k}, block {L})", f"Isomap-2 (k={k}, block {L})", over, "isomap" if k == kp else
                    None, norm)
    fig.colorbar(sc, ax=axs[2]).set_label("baseline implemented count + 1 (log)")
    fig.suptitle(f"F4  Isomap of forced-prompt states (geodesic kNN graph), banned set ringed red; overlays at k={kp}  "
                 f"| {_engine(ms)}", fontsize=10)
    _legend_algs(axs[0])
    axs[kp // 5 - 1].legend(loc="best", fontsize=7)
    _save(fig, f"F4_isomap_{tag}")


def _legend_algs(ax: Any) -> None:
    from matplotlib.lines import Line2D

    h = [Line2D([0], [0], marker="o", color="w", markerfacecolor=ALG_COLOR[a], markersize=6, label=SHORT[a])
         for a in CANON_ORDER]
    leg = ax.legend(handles=h, loc="lower left", fontsize=6.5, ncol=2, title="points (forced)", title_fontsize=7)
    ax.add_artist(leg)


def null_figure(land: dict[str, Any], land_att: dict[str, Any], kinfo: dict[str, Any], ms: str, L: int,
                kp: int) -> None:
    rows = [("correct survivors", land), ("attempted survivors", land_att)]
    rows = [(n, d) for n, d in rows if d.get("_nulls_raw")]
    fig, axs = plt.subplots(len(rows), 5, figsize=(24, 4.6 * len(rows)), squeeze=False)
    for r, (name, d) in enumerate(rows):
        for c, key in enumerate(("U", "F", "P", "C")):
            ax = axs[r, c]
            nl = d["_nulls_raw"][key]
            ax.hist(nl, bins=40 if key != "P" else 30, color="grey", alpha=0.8)
            ax.axvline(d["S"], color="red", lw=2, label=f"S = {d['S']:.3f}")
            pv = d["nulls"][key]
            ax.set_title(f"null {key}: p_edge={pv['p_edge']:.3g}, p_opp={pv['p_opp']:.3g}", fontsize=9)
            ax.set_xlabel(f"S under null (k={kp}, block {L})", fontsize=8)
            if c == 0:
                ax.set_ylabel(f"{name} (n={d['n_surv']})\ncount", fontsize=9)
            ax.legend(fontsize=7)
        ax = axs[r, 4]
        g = kinfo["g"]
        order = sorted(g, key=lambda a: g[a])
        cnt = collections.Counter(d.get("survivor_counts") or {})
        ax.bar(range(len(order)), [cnt.get(a, 0) for a in order],
               color=["tab:green" if kinfo["classes"][a] == "EDGE" else "tab:orange" if kinfo["classes"][a] == "MIDDLE"
                      else "tab:blue" for a in order])
        ax.set_xticks(range(len(order)))
        ax.set_xticklabels([f"{SHORT[a]}\n{kinfo['classes'][a][:4]}\ng={g[a]:.2f}" for a in order], fontsize=7)
        ax.set_title(f"survivors by class (EDGE -> OPPOSITE)\nverdict {d['verdict']}", fontsize=9)
    fig.suptitle(f"F6  Landing statistic vs nulls U (uniform), F (baseline frequency), P (exact identity permutation), "
                 f"C (correct-when-forced) | {_engine(ms)}", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    _save(fig, f"F6_landing_nulls_{ms}")


def forest(tab: dict[str, Any], sel: dict[str, Any]) -> None:
    items = sorted(tab.items(), key=lambda kv: (kv[1].get("carried", False), kv[0]))
    fig, ax = plt.subplots(figsize=(9, 0.55 * len(items) + 1.5))
    for i, (cid, mt) in enumerate(items):
        lo, hi = mt["share_cs_wilson95"]
        y = len(items) - 1 - i
        col = "grey" if mt.get("carried") else "tab:blue"
        ax.plot([lo, hi], [y, y], color=col, lw=2)
        ax.plot(mt["share_cs"], y, "o", color=col)
        eng = mt.get("engine") or ""
        ax.text(1.02, y, f"{mt['n_correct_survivors']}/{mt['n']}  [{eng}]", va="center", fontsize=7,
                transform=ax.get_yaxis_transform())
    ax.axvline(sel["threshold"], color="red", ls="--", label=f"selection threshold {sel['threshold']}")
    ax.set_yticks(range(len(items)))
    ax.set_yticklabels([f"{cid} {mt['name']}" + (" (CARRIED)" if mt.get("carried") else "")
                        for cid, mt in reversed(items)], fontsize=8)
    ax.set_xlim(-0.02, 1.0)
    ax.set_xlabel("share of correct survivors under the literal five-name ban (Wilson 95%)")
    ax.set_title(f"F1  Top-five ban screen: {sel['TP_RESULT']}")
    ax.legend(loc="lower right", fontsize=8)
    _save(fig, "F1_screen_forest")


def m2_figure(P2: np.ndarray, Yi: np.ndarray, labels: list[str], arms: list[str], surv: list[bool], banned: list[str],
              ms: str, L: int, sig: str) -> None:
    fig, axs = plt.subplots(1, 2, figsize=(15, 6.5))
    for ax, Y, xl in ((axs[0], P2, "PC"), (axs[1], Yi, "Isomap")):
        for a in sorted(set(labels), key=lambda x: CANON_ORDER.index(x) if x in CANON_ORDER else 99):
            for arm, mk in (("baseline", "o"), ("ban", "^")):
                sel = [i for i, (l, r, s) in enumerate(zip(labels, arms, surv)) if l == a and r == arm and not s]
                if sel:
                    ax.scatter(Y[sel, 0], Y[sel, 1], marker=mk, s=28, color=ALG_COLOR.get(a, "black"), alpha=0.7,
                               edgecolor="red" if a in banned else "none", lw=0.6,
                               label=f"{SHORT.get(a, a)} {arm}")
        si = [i for i, s in enumerate(surv) if s]
        if si:
            ax.scatter(Y[si, 0], Y[si, 1], marker="*", s=220, color=[ALG_COLOR.get(labels[i], "black") for i in si],
                       edgecolor="k", lw=0.8, label="correct survivor", zorder=6)
        ax.set_xlabel(f"{xl}-1 (block {L}, {sig})")
        ax.set_ylabel(f"{xl}-2")
    axs[0].legend(fontsize=6, ncol=2, loc="best")
    axs[0].set_title("F5a PCA of per-program states at p* (first class-signature token)")
    axs[1].set_title("F5b Isomap (k=10) of the same states; banned-class programs edged red")
    fig.suptitle(f"M2 per-sample states of every screen program | {_engine(ms)}", fontsize=10)
    _save(fig, f"F5_M2_{ms}")


def quant_figure(qc: dict[str, Any]) -> None:
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.5))
    for prec, d in qc["per_precision"].items():
        bl = sorted(int(b) for b in d["cosine_by_block"])
        axs[0].plot(bl, [d["cosine_by_block"][str(b)] for b in bl], "o-", label=prec)
    axs[0].set_xlabel("block")
    axs[0].set_ylabel("mean cosine(state_quantised, state_bf16)")
    axs[0].set_title("F8a Qwen3-8B forced S-mean states: quantised vs bf16")
    axs[0].legend()
    precs = list(qc["per_precision"])
    axs[1].bar(precs, [qc["per_precision"][p]["spearman_geodesic_k10"] for p in precs], color="tab:blue")
    axs[1].axhline(0.8, color="red", ls="--", label="precision-sensitive below 0.8")
    axs[1].set_ylim(0, 1.05)
    axs[1].set_title(f"F8b Spearman of 10x10 geodesic matrices (k=10, block {qc['L']}) vs bf16")
    axs[1].legend()
    _save(fig, "F8_quant_check")


def confirmation_figure(geo: dict[str, Any], X: np.ndarray, labels: np.ndarray, conf: dict[str, Any],
                        impl: dict[str, int], Y_iso: np.ndarray, iso: Any, pca: Any, Qconf: np.ndarray,
                        ms: str) -> None:
    """F7: held-out ban prompt states (W4/W5/P6/P7) placed on the FROZEN M1 axes (transform only), with the screen and
    confirmation survivor counts annotated."""
    kp = geo["M1"]["k_primary"]
    banned = geo["banned"]
    sc_conf = dict(collections.Counter(conf.get("survivors", [])))
    norm = LogNorm(vmin=1, vmax=max(2, max([impl.get(a, 0) for a in CANON_ORDER]) + 1))
    fig, axs = plt.subplots(1, 2, figsize=(16, 6.8))
    P = pca.transform(X)
    ev = geo["M1"]["pca_evr"]
    over_c = {"confirm": {"pca": pca.transform(Qconf)[:, :2].tolist(), "isomap": iso.transform(Qconf).tolist()}}
    _panel(axs[0], P[:, :2], labels, banned, impl, sc_conf, f"F7a frozen PCA (block {geo['L_star']}): held-out ban "
           f"prompts", f"PC1 ({ev[0]:.1%} var)", f"PC2 ({ev[1]:.1%} var)", over_c, "pca", norm)
    sc = _panel(axs[1], Y_iso, labels, banned, impl, sc_conf, f"F7b frozen Isomap k={kp}: held-out ban prompts",
                f"Isomap-1 (k={kp}, block {geo['L_star']})", f"Isomap-2 (k={kp}, block {geo['L_star']})", over_c,
                "isomap", norm)
    fig.colorbar(sc, ax=axs[1]).set_label("baseline implemented count + 1 (log)")
    lv = (conf.get("landing") or {}).get("verdict")
    fig.suptitle(f"Held-out confirmation on frozen geometry: {len(conf.get('survivors', []))} catalogue survivors "
                 f"{sc_conf}; verdict {lv} vs screen {conf.get('screen_verdict')}; CONFIRMED={conf.get('CONFIRMED')} "
                 f"| {_engine(ms)}", fontsize=10)
    axs[0].legend(loc="best", fontsize=7)
    _legend_algs(axs[0])
    _save(fig, f"F7_confirmation_{ms}")
