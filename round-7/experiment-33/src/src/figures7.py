#!/usr/bin/env python3
"""Figures of iteration 7 (PDF + PNG in figures/), drawn from results/*.json and data/*.jsonl only.

F1 layer profile (TF gain per block, by source kind) + generation confirmation (single block vs band 12-23)
F2 recovery vs rank k per task: generation (DAS with bootstrap CI, random, permuted, read-position, null, DIM-1,
   PCA-16) and teacher-forced (DAS, random, permuted, projected) panels
F3 routing confusion matrices (forced source x correct landing) by k and under the full-state exchange
F4 causal manifold of T2 in R_16 coordinates: (a) DAS-1 x DAS-2 plane with arrows from the default centroid to bans,
   seeds and instructions; (b) metric MDS; (c) Isomap; centroids sized/coloured by implemented count (3 panels)
F5 leave-one-survivor ban placement (geodesic distance to each algorithm's forced points)
F6 discreteness: correct-Y share vs lambda with the logistic fit
F7 dormant checks: natural-variance share vs random subspaces, displacement share, projected retention, reverse
F8 DAS fit curves: the committed contrastive objective diverges; the amended LME_Y objective is bounded
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from cfg import FIG_DIR, ROOT, read_json, read_jsonl
from cfg7 import CATALOGUE7, DEFAULT7, PROFILE_LAYERS, RANKS, results7

plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9, "legend.fontsize": 7.5,
                     "pdf.fonttype": 42, "ps.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False})
COL = {"dijkstra": "#4c72b0", "bf_spfa": "#dd8452", "bidijkstra": "#55a868", "floyd": "#c44e52", "dial": "#8172b3",
       "bfs": "#dd8452", "dfs": "#c44e52", "union_find": "#4c72b0", "label_propagation": "#8172b3",
       "full_sort": "#4c72b0", "quickselect": "#dd8452", "size_k_heap": "#55a868", "heapify_pop": "#c44e52",
       "median_of_medians": "#8172b3", "counting_sort": "#937860", "other": "#999999", "invalid": "#dddddd"}


def save(fig: Any, name: str) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIG_DIR / f"{name}.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def f1(tasks: list[str]) -> None:
    fig, axes = plt.subplots(2, len(tasks), figsize=(4.2 * len(tasks), 6.2), squeeze=False)
    for j, t in enumerate(tasks):
        p = results7(f"site_{t}.json")
        if not p.exists():
            continue
        s = read_json(p)
        ax = axes[0, j]
        for kind, c in (("ban", "#c44e52"), ("forced", "#4c72b0")):
            d = s["profile"]["by_kind"].get(kind)
            if not d:
                continue
            ax.plot(PROFILE_LAYERS, [d[f"full@{l}"] for l in PROFILE_LAYERS], "-o", color=c, ms=3,
                    label=f"{kind} source, single block")
            ax.axhline(d["band12-23"], color=c, ls="--", lw=1, label=f"{kind}, band 12-23")
            ax.axhline(d["rpos_all"], color=c, ls=":", lw=1, label=f"{kind}, read position (all blocks)")
        ax.set_title(f"{t}: teacher-forced full-state exchange")
        ax.set_xlabel("decoder block (output) exchanged at spec positions")
        ax.set_ylabel("contrast gain C - C_none (nats)")
        ax.legend(frameon=False)
        ax = axes[1, j]
        cf = s["confirmation"]
        L = s["L_star"]
        bars = [("ban: base", cf["BASE_W5"]["correct_Y"]), (f"ban: full L{L}", cf[f"FULL_ban_L{L}"]["correct_Y"]),
                ("ban: full band", cf["FULL_ban_band"]["correct_Y"])]
        Yc = cf.get("forced_Y")
        if Yc:
            bars += [(f"F3 {Yc}: base", cf[f"PADBASE_F3_{Yc}"]["correct_Y"]),
                     (f"F3 {Yc}: full L{L}", cf[f"FULLF3_{Yc}_L{L}"]["correct_Y"]),
                     (f"F3 {Yc}: full band", cf[f"FULLF3_{Yc}_band"]["correct_Y"])]
        ax.bar(range(len(bars)), [b[1] / 30 for b in bars], color=["#bbbbbb", "#c44e52", "#c44e52", "#bbbbbb",
                                                                   "#4c72b0", "#4c72b0"][:len(bars)])
        for i, b in enumerate(bars):
            ax.text(i, b[1] / 30 + 0.02, f"{b[1]}/30", ha="center", fontsize=7)
        ax.set_xticks(range(len(bars)))
        ax.set_xticklabels([b[0] for b in bars], rotation=30, ha="right")
        ax.set_ylim(0, 1.1)
        ax.set_ylabel("correct source-Y share (N = 30)")
        ax.set_title(f"{t}: generation confirmation -> site = {s['site']}")
    fig.tight_layout()
    save(fig, "F1_layer_profile")


def f2(p1: dict[str, Any], tasks: list[str]) -> None:
    fig, axes = plt.subplots(2, len(tasks), figsize=(4.2 * len(tasks), 6.4), squeeze=False)
    for j, t in enumerate(tasks):
        r = p1["tasks"].get(t)
        ax = axes[0, j]
        if r:
            ks = [k for k in RANKS if r["per_k"].get(k, {}).get("recovery") is not None]
            ys = [r["per_k"][k]["recovery"] for k in ks]
            ci = [r["per_k"][k].get("recovery_ci") or [None, None] for k in ks]
            ax.plot(ks, ys, "-o", color="#4c72b0", label="DAS (LME_Y map), pooled sources")
            for k, (lo, hi) in zip(ks, ci):
                if lo is not None:
                    ax.plot([k, k], [lo, hi], color="#4c72b0", lw=1)
            for k in (16, r.get("k_star")):
                e = r["per_k"].get(k) or {}
                if e.get("random_recovery") is not None:
                    ax.plot(k, e["random_recovery"], "s", color="#999999", label="random rank-k" if k == 16 else None)
            ctrl = read_json(results7(f"p1_controls_{t}.json")) if results7(f"p1_controls_{t}.json").exists() else {}
            full = (r["per_source"].get("ban") or {}).get("full_transfer") or 0
            for arm, mk, lab in (("RPOSLY_ban_k16", "v", "read-position DAS k16"), ("DIM1_ban", "^", "DIM-1"),
                                 ("PCA16_ban", "D", "PCA-16")):
                e = ctrl.get(arm)
                if e and full > 0:
                    kk = 1 if arm == "DIM1_ban" else 16
                    ax.plot(kk, e["transfer"] / full, mk, color="#55a868" if "RPOS" in arm else "#8172b3", label=lab)
            pm = (r["per_source"].get("ban") or {}).get("perm") or {}
            for a, e in pm.items():
                if full > 0:
                    kk = int(a.rsplit("k", 1)[1])
                    ax.plot(kk, e["transfer"] / full, "x", color="#c44e52", label="permuted-label (ban)"
                            if kk == 16 else None)
        ax.axhline(0.8, color="k", ls=":", lw=0.8)
        ax.axhline(0, color="k", lw=0.5)
        ax.set_xscale("log", base=2)
        ax.set_xticks(RANKS)
        ax.set_xticklabels(RANKS)
        ax.set_xlabel("rank k")
        ax.set_ylabel("generation recovery (vs full-state, same site)")
        ax.set_title(f"{t}: held-out generation (N = 30 / source)")
        ax.legend(frameon=False, fontsize=6.5)
        ax = axes[1, j]
        p = results7(f"tf_eval_{t}_LY.json")
        q = results7(f"tf_eval_{t}.json")
        if p.exists():
            sm = read_json(p)["summary"]
            for kind, ls in (("ban", "-"), ("forced", "--")):
                d = sm.get(kind)
                if not d:
                    continue
                for nm, c in (("DASLY", "#4c72b0"), ("PERMLY", "#c44e52"), ("PROJLY", "#55a868")):
                    ys = [d.get(f"{nm}_k{k}", {}).get("tf_recovery") for k in RANKS]
                    ax.plot(RANKS, [np.nan if y is None else y for y in ys], ls, marker="o", ms=3, color=c,
                            label=f"{nm} ({kind})")
        if q.exists():
            sm = read_json(q)["summary"]
            for kind, ls in (("ban", "-"), ("forced", "--")):
                d = sm.get(kind)
                if not d:
                    continue
                ys = [np.mean([d.get(f"RAND{i}_k{k}", {}).get("tf_recovery") or 0 for i in (1, 2, 3)]) for k in RANKS]
                ax.plot(RANKS, ys, ls, marker="s", ms=3, color="#999999", label=f"random ({kind})")
        ax.axhline(1, color="k", ls=":", lw=0.8)
        ax.set_xscale("log", base=2)
        ax.set_xticks(RANKS)
        ax.set_xticklabels(RANKS)
        ax.set_xlabel("rank k")
        ax.set_ylabel("TF recovery of the contrast C")
        ax.set_title(f"{t}: teacher-forced (held-out pairs)")
        ax.legend(frameon=False, fontsize=6)
    fig.tight_layout()
    save(fig, "F2_recovery_vs_rank")


def f3(rt: dict[str, Any]) -> None:
    tasks = [t for t in rt if rt[t]["confusion"]]
    if not tasks:
        return
    cols = ["full", "k1", "k4", "k16"]
    fig, axes = plt.subplots(len(tasks), len(cols), figsize=(3.0 * len(cols), 2.3 * len(tasks)), squeeze=False)
    for i, t in enumerate(tasks):
        conf = rt[t]["confusion"]
        for j, c in enumerate(cols):
            ax = axes[i, j]
            if c not in conf:
                ax.axis("off")
                continue
            rows = list(conf[c])
            labs = CATALOGUE7[t] + ["other", "fail"]
            M = np.array([[conf[c][y].get(l, 0) for l in labs] for y in rows])
            ax.imshow(M, cmap="Blues", vmin=0, vmax=30)
            for a in range(M.shape[0]):
                for b in range(M.shape[1]):
                    if M[a, b]:
                        ax.text(b, a, int(M[a, b]), ha="center", va="center", fontsize=7)
            ax.set_xticks(range(len(labs)))
            ax.set_xticklabels(labs, rotation=45, ha="right", fontsize=6.5)
            ax.set_yticks(range(len(rows)))
            ax.set_yticklabels([f"forced {y}" for y in rows], fontsize=7)
            ax.set_title(f"{t}: {'full-state' if c == 'full' else 'DAS ' + c}", fontsize=8.5)
    fig.tight_layout()
    save(fig, "F3_routing_confusion")


def f4(m: dict[str, Any]) -> None:
    co = m["coords"]
    kinds = np.array(co["kind"])
    Ys = co["Y"]
    das = np.array(co["das12"])
    fig, axes = plt.subplots(2, 3, figsize=(13, 8.2))
    style = {"twin": ("o", "#bbbbbb", 12), "padtwin": ("o", "#dddddd", 10), "p0": ("*", "k", 80),
             "ban": ("X", "#c44e52", 45), "shamban": ("x", "#c44e52", 22), "multiban": ("P", "#8172b3", 40),
             "seed_rand1": ("^", "#55a868", 70), "seed_rand2": ("^", "#55a868", 70), "seed_sem": ("v", "#55a868", 70),
             "instr_new": ("s", "#937860", 60), "instr_novel": ("s", "#937860", 60)}
    for ax, XY, title in ((axes[0, 0], das, "(a) DAS-1 x DAS-2 (residual units)"),
                          (axes[0, 1], np.array(co["mds"]), f"(b) metric MDS of R16 coords (stress-1 "
                                                             f"{m['mds_stress1']:.3f})"),
                          (axes[0, 2], np.array(co["isomap"]), "(c) Isomap (kNN 10) of R16 coords")):
        for kd, (mk, c, sz) in style.items():
            sel = kinds == kd
            if sel.any():
                ax.scatter(XY[sel, 0], XY[sel, 1], marker=mk, c=c, s=sz, label=kd, lw=0.6)
        sel = kinds == "forced"
        for i in np.where(sel)[0]:
            ax.scatter(XY[i, 0], XY[i, 1], marker="D", s=26, c=COL.get(Ys[i], "#333"), edgecolor="k", lw=0.4)
        ax.set_title(title)
        if ax is axes[0, 0]:
            zb = np.array(co["zbar_das12"])
            for i, kd in enumerate(kinds):
                if kd in ("ban", "seed_rand1", "seed_rand2", "seed_sem", "instr_new", "instr_novel") and \
                        (kd != "ban" or True):
                    ax.annotate("", xy=XY[i], xytext=zb, arrowprops=dict(arrowstyle="->", lw=0.6, color="#555"))
            ax.set_xlabel("DAS-1 coordinate")
            ax.set_ylabel("DAS-2 coordinate")
    from matplotlib.lines import Line2D
    hs, ls_ = axes[0, 0].get_legend_handles_labels()
    for Y in sorted({y for y, kd in zip(Ys, kinds) if kd == "forced" and y}):
        hs.append(Line2D([], [], marker="D", ls="", color=COL.get(Y, "#333"), markeredgecolor="k", ms=5))
        ls_.append(f"forced {Y}")
    axes[0, 0].legend(hs, ls_, frameon=False, fontsize=5.5, ncol=2, loc="best")
    cent = co["centroids_das12"]
    for ax, (name, cnt) in zip(axes[1], [("twin (Stage 0)", m["implemented_counts"]["twin"]),
                                          ("Qwen3-8B-Base (exp24)", m["implemented_counts"]["base_model"]),
                                          ("knobs (edits + exp29 dirs)", m["implemented_counts"]["knobs"])]):
        ax.scatter(das[:, 0], das[:, 1], s=6, c="#dddddd")
        tot = max(1, sum(cnt.values()))
        for Y, xy in cent.items():
            n = cnt.get(Y, 0)
            ax.scatter([xy[0]], [xy[1]], s=40 + 900 * n / tot, c=COL.get(Y, "#333"), alpha=0.75, edgecolor="k")
            ax.annotate(f"{Y} ({n})", xy, fontsize=7, xytext=(4, 4), textcoords="offset points")
        ax.set_title(f"centroids sized by implemented count\nunder {name}", fontsize=8.5)
        ax.set_xlabel("DAS-1 coordinate")
        ax.set_ylabel("DAS-2 coordinate")
    fig.tight_layout()
    save(fig, "F4_causal_manifold")


def f5(m: dict[str, Any]) -> None:
    g = m["geodesic"].get("10") or m["geodesic"].get(10)
    if not g or not g["los_placement"]:
        return
    pl = g["los_placement"]
    cat = list(pl[0]["dist"])
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    w = 0.8 / len(cat)
    for i, a in enumerate(cat):
        ax.bar(np.arange(len(pl)) + i * w, [p["dist"][a] if np.isfinite(p["dist"][a]) else 0 for p in pl], w,
               color=COL.get(a, "#333"), label=a)
    ax.set_xticks(np.arange(len(pl)) + 0.4)
    ax.set_xticklabels([f"{p['w']}: keep {p['survivor']}" for p in pl], rotation=30, ha="right", fontsize=7)
    ax.set_ylabel("mean geodesic distance (kNN 10)")
    ax.set_title(f"T2 leave-one-survivor bans: survivor rank mean {g['mean_survivor_rank']:.2f} of 5 "
                 f"(random-relabel p {g['p_rank_le_observed']:.2f})")
    ax.legend(frameon=False, fontsize=7, ncol=5)
    fig.tight_layout()
    save(fig, "F5_topk_prohibition_placement")


def f6(r: dict[str, Any] | None) -> None:
    if not r:
        return
    lam = sorted(float(x) for x in r["curve"])
    cur = {float(k): v for k, v in r["curve"].items()}
    fig, ax = plt.subplots(figsize=(5, 3.4))
    ax.plot(lam, [cur[x]["correct_Y"] / cur[x]["n"] for x in lam], "o", color="#dd8452", label="correct Y share")
    ax.plot(lam, [cur[x]["correct_default"] / cur[x]["n"] for x in lam], "s", color="#4c72b0",
            label="correct default share")
    ax.plot(lam, [cur[x]["pass"] for x in lam], ":", color="#999", label="pass rate")
    xs = np.linspace(0, 1.5, 200)
    f = r["fit"]
    ax.plot(xs, 1 / (1 + np.exp(-(xs - f["lam0"]) / f["s"])), "-", color="#dd8452", lw=1,
            label=f"logistic: lam0 {f['lam0']:.2f}, width {f['width_10_90']:.2f}")
    ax.set_xlabel("lambda (interpolated DAS edit)")
    ax.set_ylabel("share of N = 20")
    ax.set_title("T2 discreteness of the plan coordinate")
    ax.legend(frameon=False)
    fig.tight_layout()
    save(fig, "F6_discreteness")


def f7(dm: dict[str, Any]) -> None:
    tasks = list(dm)
    if not tasks:
        return
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.4))
    for t in tasks:
        d = dm[t]["by_k"]
        ks = [int(k) for k in d]
        axes[0].plot(ks, [d[k]["natural_share"] for k in d], "-o", label=f"{t} DAS")
        axes[0].plot(ks, [d[k]["random_mean"] for k in d], ":", color="#999")
        axes[0].plot(ks, [d[k]["pca_upper"] for k in d], "--", lw=0.8, label=f"{t} top-k PCA (upper)")
        axes[1].plot(ks, [d[k]["displacement_share_heldout"] or np.nan for k in d], "-o", label=f"{t} DAS")
        axes[1].plot(ks, [d[k]["displacement_share_random_expect"] for k in d], ":", color="#999")
        axes[2].plot(ks, [d[k]["projected_tf_retention"] if d[k]["projected_tf_retention"] is not None else np.nan
                          for k in d], "-o", label=f"{t} projected-map TF retention")
        if dm[t].get("reverse_recovery") is not None:
            axes[2].axhline(dm[t]["reverse_recovery"], ls="--", lw=0.8, label=f"{t} reverse recovery (gen)")
    for ax, tt in zip(axes, ("natural cross-condition variance share", "held-out displacement share",
                             "dormancy checks")):
        ax.set_xscale("log", base=2)
        ax.set_xticks(RANKS)
        ax.set_xticklabels(RANKS)
        ax.set_xlabel("rank k")
        ax.set_title(tt)
        ax.legend(frameon=False, fontsize=6.5)
    axes[0].set_yscale("log")
    axes[1].set_yscale("log")
    axes[2].axhline(0.5, color="k", ls=":", lw=0.8)
    fig.tight_layout()
    save(fig, "F7_dormant_checks")


def f8(tasks: list[str]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.3))
    for t in tasks:
        for nm, fp, ax in (("MAIN (contrast C)", results7(f"das_fits_{t}.json"), axes[0]),
                           ("MAIN_LY (LME_Y)", results7(f"das_fits_ly_{t}.json"), axes[1])):
            if not fp.exists():
                continue
            d = read_json(fp)["fits"]
            for fit, f in d.items():
                if not f or not f.get("val"):
                    continue
                ax.plot([v["step"] for v in f["val"]], [v["mean_gain"] for v in f["val"]], "-o", ms=3,
                        label=f"{t} {fit}")
            ax.set_title(f"validation gain during fitting: {nm}")
            ax.set_xlabel("step")
            ax.set_ylabel("mean validation gain (nats)")
            ax.legend(frameon=False, fontsize=6.5)
    axes[0].set_yscale("symlog")
    fig.tight_layout()
    save(fig, "F8_fit_curves")
