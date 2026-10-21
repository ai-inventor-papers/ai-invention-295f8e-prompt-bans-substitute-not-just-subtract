#!/usr/bin/env python3
"""Figures (PDF + PNG, matplotlib, Type-42 fonts, colour-blind-safe Okabe-Ito palette), drawn only from results/*.json:
fig1 hull frontiers per task; fig2 dose-response; fig3 paired-flip matrix; fig4 transmission; fig5 boundary;
fig6 plan-site MDS (C3d); fig7 phrasing clusters per idea by site."""

from __future__ import annotations

import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from cfg import FIG_DIR, RESULTS_DIR, SITES, TASKS, read_json  # noqa: E402

plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 150})
COL = {"S0": "#000000", "S1": "#E69F00", "S2": "#56B4E9", "S3": "#009E73", "S4": "#CC79A7", "S5": "#0072B2",
       "S1E": "#D55E00", "S2E": "#999999", "TOP5": "#D55E00", "TWIN": "#999999"}
SITE_NAME = {"S0": "S0 task spec, blocks 12-23", "S1": "S1 read position R", "S2": "S2 condition span",
             "S3": "S3 generated tokens 1-32", "S4": "S4 task spec, blocks 0-11", "S5": "S5 task spec, blocks 24-35"}


def save(fig, name: str) -> None:
    fig.savefig(FIG_DIR / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIG_DIR / f"{name}.png", bbox_inches="tight", dpi=200)
    plt.close(fig)


def fig1() -> None:
    h = read_json(RESULTS_DIR / "hull.json")["point"]
    fig, axs = plt.subplots(2, 3, figsize=(10, 5.6), sharey=True)
    for ax, t in zip(axs.ravel(), TASKS):
        for s in SITES:
            fr = h.get(f"{t}|{s}", {}).get("frontier")
            if fr:
                x, y = zip(*fr)
                ax.step(x, y, where="post", color=COL[s], lw=1.6 if s == "S0" else 1.1, label=s)
        ax.axvline(0.05, color="#bbbbbb", ls=":", lw=0.8)
        ax.set_title(t)
        ax.set_xlabel("pass-rate cost vs twin")
    axs[0, 0].set_ylabel("correct-only Hill-1 (depth 25)")
    axs[1, 0].set_ylabel("correct-only Hill-1 (depth 25)")
    axs[0, 0].legend(frameon=False, fontsize=7, ncol=2)
    fig.suptitle("Randomisation-hull frontiers per site (dotted: the H5 cost bound 0.05)")
    fig.tight_layout()
    save(fig, "fig1_hull_frontiers")


def fig2() -> None:
    c = read_json(RESULTS_DIR / "cells.json")
    fig, axs = plt.subplots(3, 6, figsize=(13, 6.2), sharex=True)
    for j, t in enumerate(TASKS):
        tw = c.get(f"{t}|TWIN|0", {})
        for s in SITES:
            xs, ex, pr, iv = [0], [0.0], [tw.get("pass_rate")], [tw.get("invalid_rate")]
            for a in (1, 2, 4):
                cc = c.get(f"{t}|{s}|{a}")
                if cc:
                    xs.append(a)
                    ex.append(cc.get("excess_correct_off") if cc.get("excess_correct_off") is not None else np.nan)
                    pr.append(cc.get("pass_rate"))
                    iv.append(cc.get("invalid_rate"))
            xx = [0.5 if x == 0 else x for x in xs]
            for i, v in enumerate((ex, pr, iv)):
                axs[i, j].plot(xx, v, marker="o", ms=3, color=COL[s], lw=1.5 if s == "S0" else 1, label=s)
        axs[0, j].set_title(t)
        for i in range(3):
            axs[i, j].set_xscale("log", base=2)
            axs[i, j].set_xticks([0.5, 1, 2, 4])
            axs[i, j].set_xticklabels(["twin", "1", "2", "4"])
    axs[0, 0].set_ylabel("correct-only off-default\nexcess over twin")
    axs[1, 0].set_ylabel("pass rate")
    axs[2, 0].set_ylabel("invalid rate")
    axs[0, 0].legend(frameon=False, fontsize=6)
    fig.supxlabel("alpha (per-position ban units)")
    fig.tight_layout()
    save(fig, "fig2_dose_response")


def fig3() -> None:
    pf = read_json(RESULTS_DIR / "paired_flips.json")
    for a in (1, 2, 4):
        M = np.full((len(SITES) - 1, len(TASKS)), np.nan)
        P = np.full_like(M, np.nan)
        for i, s in enumerate(SITES[1:]):
            for j, t in enumerate(TASKS):
                r = pf.get(f"{t}|{s}|{a}")
                if r:
                    tb = r["table_attempts[both,S0only,siteonly,neither]"]
                    M[i, j] = tb[1] - tb[2]
                    P[i, j] = r["mcnemar_p_attempts"]
        if a == 2:
            fig, ax = plt.subplots(figsize=(6, 3.2))
            lim = np.nanmax(np.abs(M)) if np.isfinite(M).any() else 1
            im = ax.imshow(M, cmap="RdBu_r", vmin=-lim, vmax=lim)
            for i in range(M.shape[0]):
                for j in range(M.shape[1]):
                    if np.isfinite(M[i, j]):
                        ax.text(j, i, f"{int(M[i, j]):+d}\np={P[i, j]:.2g}", ha="center", va="center", fontsize=6)
            ax.set_xticks(range(len(TASKS)), TASKS)
            ax.set_yticks(range(len(SITES) - 1), SITES[1:])
            fig.colorbar(im, ax=ax, label="flips off default: S0-only minus site-only")
            ax.set_title("Paired flips under CRN, alpha 2 (30 shared slots; exact McNemar p)")
            fig.tight_layout()
            save(fig, "fig3_paired_flips")


def fig4() -> None:
    from analysis import load_rows

    rows = [r for r in load_rows() if r.get("disp35") and r["correct"] and r["k"] < 6 and
            r["site"] in ("S0", "S1", "S2", "S4", "S5", "S1E", "S2E")]
    fig, ax = plt.subplots(figsize=(6, 4))
    for s in ("S0", "S1", "S2", "S4", "S5", "S1E", "S2E"):
        rs = [r for r in rows if r["site"] == s]
        if not rs:
            continue
        x = np.log10([r["disp35"] for r in rs])
        y = np.array([float(r["off"]) for r in rs])
        bins = np.quantile(x, np.linspace(0, 1, 5))
        mx, my = [], []
        for i in range(4):
            m = (x >= bins[i]) & (x <= bins[i + 1])
            if m.sum():
                mx.append(x[m].mean())
                my.append(y[m].mean())
        ax.plot(mx, my, marker="o", color=COL[s], label=s, lw=1.6 if s == "S0" else 1)
    ax.set_xlabel("log10 realised displacement at R, block 35 (vs clean twin)")
    ax.set_ylabel("off-default share among correct programs")
    ax.set_title("Transmission: off-default vs downstream dose (quartile bins per site)")
    ax.legend(frameon=False, fontsize=7)
    fig.tight_layout()
    save(fig, "fig4_transmission")


def fig5() -> None:
    b = read_json(RESULTS_DIR / "boundary.json")["per_task"]
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.3))
    for t in TASKS:
        cv = b.get(t, {}).get("curve", [])
        xs = [0.5 if x["alpha"] == 0 else x["alpha"] for x in cv]
        axs[0].plot(xs, [x["pass"] for x in cv], marker="o", ms=3, label=t)
        axs[1].plot(xs, [x["invalid"] for x in cv], marker="o", ms=3, label=t)
        axs[2].plot(xs, [x["hill_correct"] if x["hill_correct"] is not None else np.nan for x in cv], marker="o",
                    ms=3, label=t)
    for ax, yl in zip(axs, ("pass rate", "invalid rate", "correct-only Hill-1")):
        ax.set_xscale("log", base=2)
        ax.set_xticks([0.5, 1, 2, 4, 8])
        ax.set_xticklabels(["twin", "1", "2", "4", "8"])
        ax.set_xlabel("alpha (S0)")
        ax.set_ylabel(yl)
    axs[0].legend(frameon=False, fontsize=7)
    fig.suptitle("C3c boundary: S0 plan noise from alpha 1 to 8")
    fig.tight_layout()
    save(fig, "fig5_boundary")


def fig6() -> None:
    g = read_json(RESULTS_DIR / "plan_geometry_T1.json")
    c = read_json(RESULTS_DIR / "c3d.json")
    co = g.get("mds", {}).get("coords")
    if not co:
        return
    names = sorted(co)
    G = g["k10"]["G"]
    fig, axs = plt.subplots(1, 3, figsize=(12, 4))
    for ax, (title, arm) in zip(axs, (("neutral twin", "TWIN"), ("random plan noise S0, alpha 2", "S0_a2"),
                                      ("TOP5 plan push, alpha 2", "TOP5_a2"))):
        comp = c["by_arm"].get(arm, {}).get("k7", {}).get("composition_correct", {})
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                d = G[a][b]
                if d <= np.quantile([G[x][y] for x in names for y in names if x != y], 0.2):
                    ax.plot([co[a][0], co[b][0]], [co[a][1], co[b][1]], color="#dddddd", lw=0.8, zorder=0)
        for a in names:
            n = comp.get(a, 0)
            top5 = a in ("bfs", "dfs", "gbfs", "iddfs", "astar")
            ax.scatter(*co[a], s=30 + 12 * n, color="#D55E00" if top5 else "#0072B2", alpha=0.8, zorder=2)
            ax.annotate(f"{a} ({n})", co[a], fontsize=7, xytext=(3, 3), textcoords="offset points")
        ax.set_title(f"{title}\n(size = correct programs, K=7 labels)")
        ax.set_xticks([])
        ax.set_yticks([])
    st = g.get("mds", {}).get("stress1")
    fig.suptitle(f"C3d: plan-site geometry of 10 forced T1 algorithms (MDS of geodesic medians, stress-1 "
                 f"{st:.3f}); orange = TOP5, blue = survivors" if st is not None else "C3d plan-site geometry")
    fig.tight_layout()
    save(fig, "fig6_plan_site_mds")


def fig7() -> None:
    c = read_json(RESULTS_DIR / "cells.json")
    fig, ax = plt.subplots(figsize=(8, 3.4))
    width = 0.12
    for i, s in enumerate(SITES):
        vals = []
        for a in (1, 2, 4):
            v = [c.get(f"{t}|{s}|{a}", {}).get("phrasing", {}).get("0.8", {}).get("clusters_per_10_programs")
                 for t in TASKS]
            v = [x for x in v if x is not None]
            vals.append(np.mean(v) if v else np.nan)
        ax.bar(np.arange(3) + (i - 2.5) * width, vals, width, color=COL[s], label=s)
    tw = [c.get(f"{t}|TWIN|0", {}).get("phrasing", {}).get("0.8", {}).get("clusters_per_10_programs") for t in TASKS]
    tw = [x for x in tw if x is not None]
    if tw:
        ax.axhline(np.mean(tw), color="#999999", ls="--", lw=1, label="twin")
    ax.set_xticks(range(3), ["alpha 1", "alpha 2", "alpha 4"])
    ax.set_ylabel("phrasing clusters per 10 correct\nprograms (theta 0.8, task mean)")
    ax.legend(frameon=False, fontsize=7, ncol=4)
    ax.set_title("Surface variation: AST-shingle phrasing clusters by site")
    fig.tight_layout()
    save(fig, "fig7_phrasing_clusters")


def main() -> None:
    for f in (fig1, fig2, fig3, fig4, fig5, fig6, fig7):
        try:
            f()
        except Exception as e:  # noqa: BLE001 - one broken figure must not stop the others
            print(f"{f.__name__} failed: {e}")


if __name__ == "__main__":
    main()
