#!/usr/bin/env python3
"""Figures F1-F6 (PDF + PNG) drawn from the result files only (no recomputation)."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import FIG_DIR, PRED_DIR, RESULTS_DIR, read_json  # noqa: E402
from cfg5 import D5  # noqa: E402

plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42, "ps.fonttype": 42, "axes.spines.top": False,
                     "axes.spines.right": False})
PAL = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3", "#937860", "#DA8BC3", "#8C8C8C", "#CCB974", "#64B5CD"]
CLS = ["PN", "IFG", "PSL", "EAP", "BINT", "DMD"]


def save(fig, name: str) -> None:
    for ext in ("pdf", "png"):
        fig.savefig(FIG_DIR / f"{name}.{ext}", bbox_inches="tight", dpi=160)
    plt.close(fig)


def f1() -> None:
    lc = read_json(RESULTS_DIR / "literal_cell.json")
    grid = lc["seed_grid"]
    Ts = ["0.3", "0.7", "1.0", "1.3"]
    labs = sorted({c["labels"][t] for c in grid for t in Ts if c["labels"][t]})
    col = {l: PAL[i % len(PAL)] for i, l in enumerate(labs)}
    fig, ax = plt.subplots(figsize=(4.2, 6.0))
    for i, c in enumerate(grid):
        for j, t in enumerate(Ts):
            lab = c["labels"][t]
            ax.add_patch(plt.Rectangle((j, i), 0.95, 0.9, color=col.get(lab, "#eeeeee")))
            fa = (c["first_approach"][t] or "-")[:4]
            ax.text(j + 0.47, i + 0.45, fa + ("" if c["completed"][t] else "*"), ha="center", va="center", fontsize=6,
                    color="white")
    ax.set_xlim(0, 4)
    ax.set_ylim(0, len(grid))
    ax.set_xticks(np.arange(4) + 0.47, [f"T={t}" for t in Ts])
    ax.set_yticks(np.arange(len(grid)) + 0.45, [c["seed"] for c in grid], fontsize=6)
    ax.invert_yaxis()
    ct = lc["C_T"]
    ax.set_title(f"Literal cell (T2, thinking on, top-k 10): final label per seed x T\n"
                 f"C_T = {ct['n_change_final_label']}/{ct['n_seeds_all4_completed']} "
                 f"(CP one-sided 95% UB {ct['clopper_pearson']['upper95_one_sided']:.3f}); text = first approach",
                 fontsize=8)
    handles = [plt.Rectangle((0, 0), 1, 1, color=col[l]) for l in labs]
    ax.legend(handles, labs, loc="upper center", bbox_to_anchor=(0.5, -0.04), ncol=3, fontsize=7, frameon=False)
    save(fig, "F1_literal_cell")


def f2() -> None:
    pr = read_json(RESULTS_DIR / "prices.json")
    fig, axs = plt.subplots(1, len(D5), figsize=(3.0 * len(D5), 2.8), sharey=True)
    for ax, t in zip(axs, D5):
        for i, c in enumerate(CLS):
            p = pr.get(t, {}).get(c)
            if not p or not p.get("frontier"):
                continue
            fr = np.array(p["frontier"])
            ax.step(fr[:, 0] * 100, fr[:, 1], where="post", color=PAL[i], label=c, lw=1.4)
        ax.axvline(5, color="#999", ls=":", lw=0.8)
        ax.set_title(t)
        ax.set_xlabel("pass cost (points)")
        ax.set_xlim(-30, 40)
    axs[0].set_ylabel("correct-only Hill-1 (depth 25)")
    axs[-1].legend(fontsize=7, frameon=False)
    fig.suptitle("Randomisation-hull frontiers per decisive task (dotted line: the 5-point budget of H5)", fontsize=9,
                 y=1.04)
    save(fig, "F2_hull_frontiers")


def f3() -> None:
    cells = read_json(RESULTS_DIR / "cells.json")
    arms = ["TWIN", "PN_a1", "PN_a2", "DMD_a1", "DMD_a2", "IFG_hot", "IFG_paper", "PSL", "EAP", "BINT", "T1.3", "NOVELTY"]
    fig, axs = plt.subplots(len(D5), 1, figsize=(8.5, 2.0 * len(D5)))
    for ax, t in zip(axs, D5):
        present = [a for a in arms if f"{t}|{a}" in cells]
        labs = sorted({l for a in present for l in cells[f"{t}|{a}"]["correct_composition"]})
        col = {l: PAL[i % len(PAL)] for i, l in enumerate(labs)}
        for j, a in enumerate(present):
            c = cells[f"{t}|{a}"]
            bottom = 0.0
            for l in labs:
                v = c["correct_composition"].get(l, 0) / max(c["N"], 1)
                if v:
                    ax.bar(j, v, bottom=bottom, color=col[l], width=0.8)
                    bottom += v
        ax.set_xticks(range(len(present)), present, fontsize=7)
        ax.set_ylabel(f"{t}\nshare of N", fontsize=8)
        ax.legend([plt.Rectangle((0, 0), 1, 1, color=col[l]) for l in labs], labs, fontsize=6, ncol=4,
                  loc="upper left", bbox_to_anchor=(1.0, 1.0), frameon=False)
    fig.suptitle("Correct-only compositions by arm (bar height = pass rate)", fontsize=9)
    save(fig, "F3_compositions")


def f4() -> None:
    dmd = read_json(PRED_DIR / "dmd_temperatures.json")
    pvd = read_json(RESULTS_DIR / "pn_vs_dmd.json")["per_task"]
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.0))
    for i, t in enumerate(D5):
        for a, ls in (("1.0", "-"), ("2.0", "--")):
            v = dmd.get(t, {}).get(a)
            if v:
                axs[0].plot(range(1, len(v["kl_curve_PN"]) + 1), v["kl_curve_PN"], ls=ls, color=PAL[i],
                            label=f"{t} a{a[0]}" if a == "1.0" else None)
    axs[0].set_xlabel("generated token")
    axs[0].set_ylabel("KL(p_push || p_clean)")
    axs[0].set_title("PN per-token departure (calibration rows; dashed = alpha 2)", fontsize=8)
    axs[0].legend(fontsize=6, frameon=False)
    x = np.arange(len(D5))
    wd = 0.2
    for k, (key, lab, c) in enumerate((("PN_off_default_share", "PN", PAL[0]), ("DMD_off_default_share", "DMD", PAL[5]))):
        for a, off in (("alpha1", -1.5), ("alpha2", 0.5)):
            vals = [pvd.get(t, {}).get(a, {}).get(key, np.nan) for t in D5]
            axs[1].bar(x + (off + k) * wd, vals, width=wd, color=c, alpha=1.0 if a == "alpha1" else 0.55,
                       label=f"{lab} {a}")
    axs[1].set_xticks(x, D5)
    axs[1].set_ylabel("correct off-default share of N")
    axs[1].set_title("PN vs departure-matched decoding", fontsize=8)
    axs[1].legend(fontsize=6, frameon=False)
    save(fig, "F4_pn_vs_dmd")


def f5() -> None:
    pvt = read_json(RESULTS_DIR / "plain_vs_twin.json")
    ts = [t for t in pvt if "PNPLAIN_a1_vs_PN_a1" in pvt[t]]
    fig, ax = plt.subplots(figsize=(6, 2.6))
    x = np.arange(len(ts))
    a = [pvt[t]["PNPLAIN_a1_vs_PN_a1"]["mcnemar"]["x_only"] for t in ts]
    b = [pvt[t]["PNPLAIN_a1_vs_PN_a1"]["mcnemar"]["y_only"] for t in ts]
    ax.bar(x - 0.2, a, 0.4, color=PAL[2], label="off-default only under PN plain")
    ax.bar(x + 0.2, b, 0.4, color=PAL[0], label="off-default only under PN twin")
    for i, t in enumerate(ts):
        p = pvt[t]["PNPLAIN_a1_vs_PN_a1"]["mcnemar"]["p_exact"]
        ax.text(i, max(a[i], b[i]) + 0.3, f"p={p:.2f}", ha="center", fontsize=6)
    ax.set_xticks(x, ts, fontsize=7)
    ax.set_ylabel("discordant slots")
    ax.set_title("PN plain vs PN twin, paired by direction and slot (exact McNemar)", fontsize=8)
    ax.legend(fontsize=6, frameon=False)
    save(fig, "F5_plain_vs_twin")


def f6() -> None:
    land = read_json(RESULTS_DIR / "landings.json")
    base = land["base_compositions_iter1"]
    fig, axs = plt.subplots(1, 2, figsize=(9, 2.8))
    for ax, t in zip(axs, ("T1", "T2")):
        sets = {"base (iter 1)": Counter(base.get(t, {}))}
        for k, v in land["moves"].items():
            if k.startswith(t + "|") and v.get("moves"):
                sets[k.split("|")[1]] = Counter(v["landing_set"])
        labs = sorted({l for c in sets.values() for l in c})
        col = {l: PAL[i % len(PAL)] for i, l in enumerate(labs)}
        for j, (nm, c) in enumerate(sets.items()):
            tot = max(sum(c.values()), 1)
            bottom = 0.0
            for l in labs:
                v = c.get(l, 0) / tot
                if v:
                    ax.bar(j, v, bottom=bottom, color=col[l])
                    bottom += v
        ax.set_xticks(range(len(sets)), list(sets), rotation=30, fontsize=7)
        ax.set_title(f"{t}: landing sets of moving knobs vs base composition", fontsize=8)
        ax.legend([plt.Rectangle((0, 0), 1, 1, color=col[l]) for l in labs], labs, fontsize=6, frameon=False,
                  loc="upper left", bbox_to_anchor=(1.0, 1.0))
    save(fig, "F6_landings")


if __name__ == "__main__":
    FIG_DIR.mkdir(exist_ok=True)
    for f in (f1, f2, f3, f4, f5, f6):
        try:
            f()
            print(f"{f.__name__} ok")
        except (FileNotFoundError, KeyError, ValueError, TypeError) as e:
            print(f"{f.__name__} skipped: {e}")
