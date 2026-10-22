#!/usr/bin/env python3
"""Figures F1-F6 (PDF + PNG, figures/): F1 base composition vs nudged landing per unit; F2 the L1a/L1b event table;
F3 per-direction escape (stage-1 off-default share) heatmap by alpha; F4 log-score differences (base minus rival) with
bootstrap lower bounds; F5 M candidates vs E_u; F6 K: rarefied Hill-1 vs pass cost per knob.
Every number is read from units.json, landing_events.json and results/*.json (no recomputation here)."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)
plt.rcParams.update({"font.size": 8, "pdf.fonttype": 42, "ps.fonttype": 42, "axes.spines.top": False,
                     "axes.spines.right": False})
C_BASE, C_LAND, C_TAIL, C_QLIK = "#4C72B0", "#DD8452", "#55A868", "#8172B3"


def save(fig, name: str) -> None:
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIG / f"{name}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def f1(units, events) -> None:
    n = len(units)
    cols = 5
    rows = math.ceil(n / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(2.2 * cols, 2.0 * rows), squeeze=False)
    for ax, U in zip(axes.flat, units):
        nd = [m for m in U["catalogue"] if m != U["default"]]
        qb = np.array([U["q_base"][m] for m in nd])
        qb = qb / qb.sum()
        land = np.zeros(len(nd))
        for e in events:
            if e["unit"] == U["unit"]:
                land += np.array([e["correct_off_default_counts"].get(m, 0) for m in nd])
        x = np.arange(len(nd))
        ax.bar(x - 0.2, qb, 0.4, color=C_BASE, label="base forecast q_base")
        tot = land.sum()
        ax.bar(x + 0.2, land / tot if tot else land, 0.4, color=C_LAND, label="nudged landings (share)")
        ax.set_xticks(x)
        ax.set_xticklabels([m.replace("_", "\n") for m in nd], fontsize=5)
        ax.set_title(f"{U['unit']} (D={U['default']})\nn landed={int(tot)}, r_u={U['r_u']}", fontsize=6)
        ax.set_ylim(0, 1)
    for ax in list(axes.flat)[n:]:
        ax.axis("off")
    axes.flat[0].legend(fontsize=5, frameon=False, loc="upper right")
    fig.suptitle("F1. Base-model forecast vs where correct off-default nudged programs landed", fontsize=9)
    fig.tight_layout()
    save(fig, "F1_base_vs_landing")


def f2(pool) -> None:
    rows = []
    for name, key in (("L1a (tail-empty)", "L1a"), ("L1b (discordant)", "L1b")):
        for e in pool["per_event"][key]["events"]:
            rows.append([name, e["unit"], e["nudge_type"], e.get("r_u"), e.get("q_lik_top1", "-"),
                         e.get("modal") or "-", "yes" if e.get("clear") else "no",
                         ("hit" if e.get("hit") else "miss") if "hit" in e else "-"])
    fig, ax = plt.subplots(figsize=(8, 0.3 * max(len(rows), 3) + 1.2))
    ax.axis("off")
    if rows:
        t = ax.table(cellText=rows, colLabels=["test", "unit", "nudge", "r_u (base)", "q_lik top-1", "modal landing",
                                               "clear", "r_u hit"], loc="center", cellLoc="center")
        t.auto_set_font_size(False)
        t.set_fontsize(7)
        t.scale(1, 1.2)
    a, b = pool["per_event"]["L1a"], pool["per_event"]["L1b"]
    ax.set_title(f"F2. Landing events. L1a: {a['hits']}/{a['n']} hits, Poisson-binomial p = "
                 f"{a['p_poisson_binomial']:.3f} ({a['verdict']}); L1b: b = {b['b_base_only']}, c = "
                 f"{b['c_qlik_only']}, p = {b['p_sign']:.3f} ({b['verdict']})", fontsize=8)
    save(fig, "F2_event_table")


def f3(units) -> None:
    alphas = ["1.0", "2.0", "4.0"]
    mat = np.full((len(units), 24), np.nan)
    conf = np.zeros((len(units), 24), bool)
    for i, U in enumerate(units):
        for j, a in enumerate(alphas):
            for k in range(8):
                d = U["per_direction_escape"].get(a, {}).get(str(k))
                if d:
                    mat[i, 8 * j + k] = d["off_share_stage1"]
                    conf[i, 8 * j + k] = d["confirmed"]
    fig, ax = plt.subplots(figsize=(8, 0.35 * len(units) + 1.2))
    im = ax.imshow(mat, aspect="auto", cmap="viridis", vmin=0, vmax=max(0.3, np.nanmax(mat) if np.isfinite(
        np.nanmax(mat)) else 0.3))
    for i in range(len(units)):
        for j in range(24):
            if conf[i, j]:
                ax.text(j, i, "*", ha="center", va="center", color="white", fontsize=9)
    ax.set_yticks(range(len(units)))
    ax.set_yticklabels([f"{U['unit']} E={U['E_u']:.2f}" for U in units])
    ax.set_xticks([3.5, 11.5, 19.5])
    ax.set_xticklabels(["alpha 1 (dirs 0-7)", "alpha 2", "alpha 4"])
    for x in (7.5, 15.5):
        ax.axvline(x, color="white", lw=1)
    fig.colorbar(im, ax=ax, label="stage-1 correct off-default share (N 10)")
    ax.set_title("F3. Per-direction escape by alpha (* = confirmed at N 30)", fontsize=9)
    save(fig, "F3_escape_heatmap")


def f4(pool) -> None:
    fig, ax = plt.subplots(figsize=(5, 2.6))
    labels, means, lows = [], [], []
    for scope, d in (("per event", pool["per_event"]["log_scores"]),
                     ("unit cluster", pool["unit_clustered"]["log_scores_cluster_bootstrap"])):
        for rival in ("q_lik", "q_lik_raw", "q_tail"):
            r = d[rival]["all"]
            labels.append(f"base - {rival}\n({scope}, n={r['n']})")
            means.append(r["mean_D"] if r["mean_D"] is not None else np.nan)
            lows.append(r["lower95"] if r["lower95"] is not None else np.nan)
    y = np.arange(len(labels))
    m = np.array(means, float)
    lo = np.array(lows, float)
    ax.errorbar(m, y, xerr=[np.where(np.isfinite(m - lo), m - lo, 0), np.zeros_like(m)], fmt="o", color=C_BASE,
                capsize=3)
    ax.axvline(-0.10, color="red", ls="--", lw=0.8, label="non-inferiority margin -0.10")
    ax.axvline(0, color="grey", lw=0.6)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=6)
    ax.set_xlabel("mean log-score difference (nats); bar = one-sided 95% lower bound")
    ax.legend(fontsize=6, frameon=False)
    ax.set_title("F4. Base forecast vs tuned-model rivals (matched events)", fontsize=9)
    save(fig, "F4_log_score_differences")


def f5(units, m) -> None:
    cands = list(m["candidates"])
    fig, axes = plt.subplots(2, 3, figsize=(7.5, 4.2))
    for ax, c in zip(axes.flat, cands):
        xs = [U["M"].get(c) for U in units]
        ys = [U["E_u"] for U in units]
        pts = [(float(x), y) for x, y in zip(xs, ys) if x is not None and y is not None]
        if pts:
            ax.scatter(*zip(*pts), s=14, color=C_BASE)
            for U, x, y in zip(units, xs, ys):
                if x is not None and y is not None:
                    ax.annotate(U["unit"], (float(x), y), fontsize=5)
        r = m["candidates"][c]
        rho = r.get("rho")
        ax.set_title(f"{c} ({r.get('direction', '')}): rho={rho if rho is None else round(rho, 2)}, "
                     f"p={r.get('p_one_sided') if r.get('p_one_sided') is None else round(r['p_one_sided'], 3)}",
                     fontsize=6)
        ax.set_ylabel("E_u", fontsize=6)
    fig.suptitle("F5. Movability candidates (M) vs escape fraction E_u (descriptive, one panel)", fontsize=9)
    fig.tight_layout()
    save(fig, "F5_M_vs_E")


def f6(k) -> None:
    us = k["units"]
    cols = 5
    rows = math.ceil(len(us) / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(2.2 * cols, 2.0 * rows), squeeze=False)
    for ax, U in zip(axes.flat, us):
        pr = U["pass_rate"]
        for name, col in (("twin", "black"), ("PN_a2", C_BASE), ("PN_a4", C_LAND), ("BINT", C_TAIL)):
            if name in pr and name in U["hill1_depth25"]:
                cost = 100 * (pr["twin"] - pr[name])
                ax.scatter(cost, U["hill1_depth25"][name], color=col, s=14, label=name)
        ax.set_title(U["unit"], fontsize=7)
        ax.set_xlabel("pass cost (points)", fontsize=6)
        ax.set_ylabel("Hill-1 (depth 25)", fontsize=6)
    for ax in list(axes.flat)[len(us):]:
        ax.axis("off")
    axes.flat[0].legend(fontsize=5, frameon=False)
    fig.suptitle("F6. Knobs: correct-only rarefied Hill-1 vs pass cost", fontsize=9)
    fig.tight_layout()
    save(fig, "F6_K_knobs")


def main() -> None:
    units = json.loads((ROOT / "units.json").read_text())["units"]
    events = json.loads((ROOT / "landing_events.json").read_text())["events"]
    pool = json.loads((ROOT / "results" / "pool_l1_panelI.json").read_text())
    f1(units, events)
    f2(pool)
    f3(units)
    f4(pool)
    mp = ROOT / "results" / "m.json"
    if mp.exists():
        f5(units, json.loads(mp.read_text()))
    kp = ROOT / "results" / "k.json"
    if kp.exists():
        f6(json.loads(kp.read_text()))
    print("figures written")


if __name__ == "__main__":
    sys.exit(main())
