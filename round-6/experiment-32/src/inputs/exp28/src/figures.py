#!/usr/bin/env python3
"""Figures F1-F6 (PDF + PNG) in the aii-data-fig-gen house style (hand-written matplotlib with its layout fitters).
F1 beta vs E_u scatter; F2 per-task correct compositions (pt pooled vs it twin vs push landing); F3 16 x 2
per-direction stage-1 off-default share per task; F4 transplant arms per S_T task (correct off-default share with
95% Wilson CIs); F5 transplant displacement per block in ban-free units with the massive-channel share; F6 re-gate
runtime label vs adjudicated label."""

from __future__ import annotations

import collections
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import ALL_TASKS, ALPHAS, BAND, DIR_SEEDS, FIG_DIR, PRED_DIR, RESULTS_DIR, read_json, setup_logging

SK = Path(__import__("os").environ.get("AII_DATA_FIG_GEN", "aii-data-fig-gen/scripts"))  # skill scripts dir
sys.path.insert(0, str(SK))
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

try:
    from chart_geometry import fit_point_labels  # noqa: E402
    from chart_style import (PALETTE, apply_house_style, clear_legends_of_data, fit_legends, fit_tick_labels,  # noqa: E402
                             fit_titles, literal, place_legend, place_point_label)
    HOUSE = True
except ImportError:  # the skill scripts are not part of the published repository
    HOUSE = False
    PALETTE = ["#0173B2", "#DE8F05", "#029E73", "#D55E00", "#CC78BC", "#CA9161", "#FBAFE4", "#949494"]


def style() -> None:
    if HOUSE:
        apply_house_style()


def finish(fig, name: str) -> None:
    if HOUSE:
        try:
            fit_legends(fig)
            clear_legends_of_data(fig)
            fit_tick_labels(fig)
            fit_titles(fig)
            clear_legends_of_data(fig)
            fit_point_labels(fig)
        except Exception as e:  # noqa: BLE001 - layout helpers are best effort
            print(f"layout helper failed on {name}: {e}")
    fig.savefig(FIG_DIR / f"{name}.pdf")
    fig.savefig(FIG_DIR / f"{name}.png", dpi=200)
    plt.close(fig)


def legend(ax, loc="best"):
    if HOUSE:
        place_legend(ax, loc=loc)
    else:
        ax.legend(loc=loc, fontsize=8)


def f1(c1, a1, esc) -> None:
    style()
    fig, ax = plt.subplots(figsize=(6.5, 4.2), layout="constrained")
    units = a1["units"]
    x = [a1["beta"][t] for t in units]
    y = [a1["E"][t] for t in units]
    cls = [c1["units"][t]["class"] for t in units]
    col = {"COLLAPSED": PALETTE[0], "INTERMEDIATE": PALETTE[1], "DIVERSE": PALETTE[2]}
    for c in ("COLLAPSED", "INTERMEDIATE", "DIVERSE"):
        xi = [a for a, k in zip(x, cls) if k == c]
        yi = [b for b, k in zip(y, cls) if k == c]
        if xi:
            ax.scatter(xi, yi, s=40, color=col[c], label=c.lower(), zorder=3)
    for t, a, b in zip(units, x, y):
        if HOUSE:
            place_point_label(ax, literal(t), (a, b))
        else:
            ax.annotate(t, (a, b), fontsize=8, xytext=(3, 3), textcoords="offset points")
    rho = a1["rho"]
    p = a1["p_one_sided_perm"]
    ax.set_title(f"pt repertoire vs fresh escape fraction (Spearman rho = {rho if rho is None else round(rho, 2)}, "
                 f"one-sided p = {p if p is None else round(p, 3)})")
    ax.set_xlabel("beta: pt share of non-default catalogue algorithms")
    ax.set_ylabel("E_u: share of 16 directions that escape")
    ax.axvline(0.05, color="0.6", lw=0.8, ls="--")
    ax.axvline(0.2, color="0.6", lw=0.8, ls=":")
    legend(ax)
    finish(fig, "fig1_beta_vs_escape")


def f2(c1, esc) -> None:
    """Per task: share of D_u, r_u, other catalogue algorithms and 'other' in the pt primary composition (LOW_CORRECT:
    valid attempts), the it twin's correct programs and the correct off-default programs of confirmed escapes."""
    style()
    tasks = list(ALL_TASKS)
    fig, axes = plt.subplots(3, 5, figsize=(6.5, 5.8), layout="constrained", sharey=True)
    cats = ["D_u", "r_u (pt runner-up)", "other catalogue", "'other' mechanism"]
    cols = ["0.15", PALETTE[1], PALETTE[2], "0.75"]
    for ax, t in zip(axes.flat, tasks):
        u = c1["units"][t]
        cat, D, r = u["catalogue"], u["D"], u["r_u"]
        src = u[u["primary_source"]]
        pt_c = src["attempt_counts"] if u["low_correct"] else src["correct_counts"]
        pt_c = {k: v for k, v in pt_c.items() if k not in ("invalid", "disputed")}
        srcs = [pt_c, u["default"]["correct_counts"],
                (esc[t].get("landing") or {}).get("composition", {}) if esc[t].get("defaulted") else {}]
        bottom = np.zeros(3)
        for ci, cname in enumerate(cats):
            vals = []
            for sdict in srcs:
                tot = sum(v for k, v in sdict.items() if k in cat or k == "other")
                if cname == "D_u":
                    x = sdict.get(D, 0)
                elif cname.startswith("r_u"):
                    x = sdict.get(r, 0) if r else 0
                elif cname == "other catalogue":
                    x = sum(v for k, v in sdict.items() if k in cat and k not in (D, r))
                else:
                    x = sdict.get("other", 0)
                vals.append(x / tot if tot else 0.0)
            ax.bar(range(3), vals, bottom=bottom, color=cols[ci], width=0.7, label=cname if t == tasks[0] else None)
            bottom += np.array(vals)
        ax.set_xticks(range(3), ["pt", "twin", "push"], fontsize=7)
        ax.set_title(f"{t}: D={D}\nr={r}", fontsize=6.5)
        ax.tick_params(axis="y", labelsize=7)
    fig.legend(*axes.flat[0].get_legend_handles_labels(), loc="outside lower center", ncols=4, fontsize=7)
    fig.suptitle("Composition: pt (pooled; valid attempts, LOW_CORRECT) vs it twin (correct) vs confirmed push landings",
                 fontsize=8.5)
    fig.savefig(FIG_DIR / "fig2_compositions.pdf")
    fig.savefig(FIG_DIR / "fig2_compositions.png", dpi=200)
    plt.close(fig)


def f3(c1, esc) -> None:
    style()
    tasks = [t for t in ALL_TASKS if esc[t].get("defaulted")]
    cols = [f"{s}_a{int(a)}" for a in ALPHAS for s in DIR_SEEDS]
    M = np.array([[esc[t]["per_direction"].get(c, {}).get("off_cat") or 0.0 for c in cols] for t in tasks])
    fig, ax = plt.subplots(figsize=(6.5, 4.6), layout="constrained")
    im = ax.imshow(M, aspect="auto", cmap="cividis", vmin=0, vmax=1)
    for i, t in enumerate(tasks):
        for j, c in enumerate(cols):
            if esc[t]["per_direction"].get(c, {}).get("confirmed"):
                ax.text(j, i, "*", ha="center", va="center", color="white", fontsize=9)
    ax.set_yticks(range(len(tasks)), tasks, fontsize=7)
    ax.set_xticks([7.5, 23.5], ["alpha 1 (16 directions)", "alpha 2 (16 directions)"], fontsize=8)
    ax.axvline(15.5, color="white", lw=1.5)
    ax.grid(False)
    ax.set_title("Stage-1 off-default share per direction (N=10); * = confirmed (N=30)", fontsize=9)
    cb = fig.colorbar(im, ax=ax)
    cb.set_label("off-default share")
    fig.savefig(FIG_DIR / "fig3_direction_heatmap.pdf")
    fig.savefig(FIG_DIR / "fig3_direction_heatmap.png", dpi=200)
    plt.close(fig)


def f4(tp) -> None:
    if not tp or not tp.get("per_unit"):
        return
    style()
    units = list(tp["per_unit"])
    arms = ["twin", "T", "RND", "XT", "RP"]
    fig, ax = plt.subplots(figsize=(6.5, 3.8), layout="constrained")
    w = 0.16
    for i, a in enumerate(arms):
        vals, lo, hi = [], [], []
        for u in units:
            d = tp["per_unit"][u].get(a, {})
            s = d.get("s")
            ci = d.get("s_ci95") or [s, s]
            vals.append(s if s is not None else 0)
            lo.append(max(0.0, (s or 0) - (ci[0] if ci[0] is not None else 0)))
            hi.append(max(0.0, (ci[1] if ci[1] is not None else 0) - (s or 0)))
        ax.bar(np.arange(len(units)) + (i - 2) * w, vals, width=w, yerr=[lo, hi], capsize=2, label=a,
               color=PALETTE[i % len(PALETTE)])
    for j, u in enumerate(units):
        b = tp["per_unit"][u].get("beta")
        if b is not None:
            ax.plot([j - 2.5 * w, j + 2.5 * w], [b, b], color="0.2", ls="--", lw=1)
    ax.set_xticks(range(len(units)), units)
    ax.set_ylabel("correct catalogue off-default share")
    ax.set_title(f"pt->it transplant (lambda={tp['lambda'].get('lambda')}) vs matched controls; dashed = beta")
    legend(ax, "upper right")
    finish(fig, "fig4_transplant")


def f5(norms) -> None:
    if not norms:
        return
    style()
    pb = norms["per_block"]
    ls = [int(l) for l in pb]
    med = [pb[str(l)]["median_units"] for l in ls]
    lo = [pb[str(l)]["iqr"][0] for l in ls]
    hi = [pb[str(l)]["iqr"][1] for l in ls]
    ms = [pb[str(l)]["massive_share_median"] for l in ls]
    fig, ax = plt.subplots(figsize=(6.5, 3.6), layout="constrained")
    ax.plot(ls, med, marker="o", color=PALETTE[0], label="median ||d_ox|| / n (ban-free units)")
    ax.fill_between(ls, lo, hi, color=PALETTE[0], alpha=0.2)
    ax.axhline(4, color="0.4", ls="--", lw=1, label="random-noise breakage dose (about 4 units)")
    ax.set_xlabel("block")
    ax.set_ylabel("transplant displacement (ban-free units)")
    ax2 = ax.twinx()
    ax2.plot(ls, ms, marker="s", color=PALETTE[1], label="massive-channel share of ||d||^2")
    ax2.set_ylabel("massive share")
    ax2.set_ylim(0, 1)
    ax.set_title("pt - it displacement at task-spec positions (transplant tasks)")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=7, loc="lower left")
    fig.savefig(FIG_DIR / "fig5_transplant_norms.pdf")
    fig.savefig(FIG_DIR / "fig5_transplant_norms.png", dpi=200)
    plt.close(fig)


def f6(reg) -> None:
    if not reg:
        return
    style()
    rows = [r for r in reg["sample"] if r.get("adjudicated") not in (None, "UNRESOLVED")]
    pairs = collections.Counter(("agree" if r["label"] == r["adjudicated"] else "disagree", r["model"], r["task"])
                                for r in rows)
    tasks = sorted({r["task"] for r in rows}, key=lambda t: ALL_TASKS.index(t))
    fig, ax = plt.subplots(figsize=(6.5, 3.4), layout="constrained")
    for k, (mdl, off) in enumerate((("it", -0.2), ("pt", 0.2))):
        ag = [pairs.get(("agree", mdl, t), 0) for t in tasks]
        dg = [pairs.get(("disagree", mdl, t), 0) for t in tasks]
        ax.bar(np.arange(len(tasks)) + off, ag, width=0.38, color=PALETTE[2 * k], label=f"{mdl}: agrees")
        ax.bar(np.arange(len(tasks)) + off, dg, width=0.38, bottom=ag, color=PALETTE[2 * k + 1],
               label=f"{mdl}: disagrees")
    ax.set_xticks(range(len(tasks)), tasks, fontsize=7)
    ax.set_ylabel("programs in the re-gate sample")
    g = reg["gate"]
    ax.set_title(f"Re-gate: final label vs adjudication (left bar it, right bar pt); runtime-AST kappa "
                 f"{g['bench']['kappa_runtime_vs_ast']:.2f} / {g['suite']['kappa_runtime_vs_ast']:.2f}", fontsize=8)
    fig.legend(*ax.get_legend_handles_labels(), loc="outside lower center", ncols=4, fontsize=8)
    fig.savefig(FIG_DIR / "fig6_regate.pdf")
    fig.savefig(FIG_DIR / "fig6_regate.png", dpi=200)
    plt.close(fig)


def main() -> None:
    setup_logging("figures")
    c1 = read_json(PRED_DIR / "commit_E1.json")
    esc = read_json(RESULTS_DIR / "escape.json")
    a1 = read_json(RESULTS_DIR / "e_a1.json")
    tp = read_json(RESULTS_DIR / "transplant.json") if (RESULTS_DIR / "transplant.json").exists() else None
    norms = read_json(RESULTS_DIR / "transplant_norms.json") if (RESULTS_DIR / "transplant_norms.json").exists() else None
    reg = read_json(RESULTS_DIR / "regate.json") if (RESULTS_DIR / "regate.json").exists() else None
    for fn, args in ((f1, (c1, a1, esc)), (f2, (c1, esc)), (f3, (c1, esc)), (f4, (tp,)), (f5, (norms,)), (f6, (reg,))):
        try:
            fn(*args)
            print(f"{fn.__name__} ok")
        except Exception as e:  # noqa: BLE001 - one failing figure must not block the others
            import traceback

            traceback.print_exc()
            print(f"{fn.__name__} failed: {e}")


if __name__ == "__main__":
    main()
