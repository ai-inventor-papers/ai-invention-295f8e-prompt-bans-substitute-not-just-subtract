#!/usr/bin/env python3
"""Figures F1-F6 (PDF + PNG) from results/*.json (deterministic; matplotlib, Type-42 fonts, colourblind palette).

F1 locator curves (own-label share vs prefix length per base path; detected decision positions marked)
F2 decision-token probabilities at d (template-averaged T 1) coloured by Phat(minority | token), top-10 cut marked
F3 predicted (L, B0, B1, B2, BH) vs observed shares of the T-1 minority over T, Wilson 95% CIs, per unit
F4 calibration scatter: predicted vs observed share for every (unit, T, label bin), by family
F5 base vs instruct: decision margins per task and phrasing-entropy differences
F6 per-slot replay accuracy and realisation vs mechanism gaps
"""

from __future__ import annotations

import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from cfg8 import FIG_DIR, RESULTS_DIR, TEMPS, UNITS, read_json  # noqa: E402

plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False})
PAL = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00", "#F0E442", "#000000"]
FAM_COL = {"gemma": "#009E73", "llama": "#CC79A7", "qwen": "#0072B2"}
MCOL = {"L": "#D55E00", "B0": "#999999", "B1": "#56B4E9", "B2": "#E69F00", "BH": "#CC79A7"}


def save(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"{name}.pdf")
    fig.savefig(FIG_DIR / f"{name}.png", dpi=160)
    plt.close(fig)


def units_done() -> list[str]:
    return [u for u in UNITS if (RESULTS_DIR / f"locate_{u}.json").exists()]


def f1() -> None:
    us = units_done()
    if not us:
        return
    n = len(us)
    fig, axs = plt.subplots(1, n, figsize=(3.2 * n, 2.8), squeeze=False)
    for ax, u in zip(axs[0], us):
        loc = read_json(RESULTS_DIR / f"locate_{u}.json")
        bins = loc["bins"]
        for i, cp in enumerate(loc["change_points"]):
            bp = loc["base_paths"][i]
            if "series" not in cp:
                continue
            s = np.array(cp["series"], float)
            own = bins.index(bp["label"]) if bp["label"] in bins else 0
            sh = s[:, own] / np.maximum(s.sum(1), 1)
            ax.plot(cp["ks"], sh, "-o", ms=2, lw=1, color=PAL[i % len(PAL)], label=f"{bp['pid']} ({bp['label'][:10]})")
            if cp.get("detected") and cp.get("d") is not None:
                ax.axvline(cp["d"] + 1, color=PAL[i % len(PAL)], ls=":", lw=1)
        ax.set_title(f"{u}", fontsize=9)
        ax.set_xlabel("prefix length k (generated tokens)")
        ax.set_ylim(-0.05, 1.05)
        ax.legend(fontsize=5, loc="lower right")
    axs[0][0].set_ylabel("share of continuations\nwith the path's own label")
    save(fig, "F1_locator_curves")


def f2() -> None:
    items = []
    for u in units_done():
        loc = read_json(RESULTS_DIR / f"locate_{u}.json")
        for o in loc["openings"]:
            items.append((u, loc, o))
    if not items:
        return
    n = len(items)
    fig, axs = plt.subplots(1, n, figsize=(3.0 * n, 2.9), squeeze=False)
    cmap = plt.get_cmap("coolwarm")
    for ax, (u, loc, o) in zip(axs[0], items):
        bins = loc["bins"]
        mi = bins.index(loc["minority"]) if loc["minority"] in bins else 1
        m = np.array(o["mass_T1"])
        ph = np.array([o["phat"][str(t)][mi] for t in o["tokens"]])
        x = np.arange(len(m))
        ax.bar(x, m, color=cmap(ph), edgecolor="k", lw=0.3)
        ax.set_yscale("log")
        ax.set_ylim(max(1e-6, m[m > 0].min() / 3 if (m > 0).any() else 1e-6), 1.5)
        ax.axvline(9.5, color="k", ls="--", lw=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels([repr(s)[1:-1][:8] for s in o["token_strs"]], rotation=90, fontsize=5)
        ax.set_title(f"{u} {o['id']} d={o['d']}  H={o['H_bits']:.3f} bits", fontsize=8)
    axs[0][0].set_ylabel("T-1 probability at d (template mean)")
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, 1))
    fig.colorbar(sm, ax=axs[0].tolist(), fraction=0.02, label="Phat(minority | token)")
    fig.savefig(FIG_DIR / "F2_decision_token_probabilities.pdf")
    fig.savefig(FIG_DIR / "F2_decision_token_probabilities.png", dpi=160)
    plt.close(fig)


def f3(an: dict) -> None:
    us = [u for u, a in an["units"].items()]
    if not us:
        return
    n = len(us)
    fig, axs = plt.subplots(1, n, figsize=(2.9 * n, 2.8), squeeze=False)
    for ax, u in zip(axs[0], us):
        a = an["units"][u]
        bins = a["bins"]
        mino = a["minority"] or bins[0]
        j = bins.index(mino)
        for m in ("B0", "B1", "B2", "BH", "L"):
            ax.plot(TEMPS, [a["cells"][f"p1|{T}"]["pred"][m][j] for T in TEMPS], "-", color=MCOL[m],
                    lw=2 if m == "L" else 1, label=m)
        ob = [a["cells"][f"p1|{T}"]["shares"][j] for T in TEMPS]
        lo = [a["cells"][f"p1|{T}"]["wilson"][mino][0] for T in TEMPS]
        hi = [a["cells"][f"p1|{T}"]["wilson"][mino][1] for T in TEMPS]
        ax.errorbar(TEMPS, ob, yerr=[np.clip(np.array(ob) - lo, 0, None), np.clip(np.array(hi) - ob, 0, None)], fmt="ko",
                    ms=3, capsize=2, label="observed")
        ax.set_title(f"{u}: {mino[:14]}\nMAE L {a['mae']['p1']['L']:.3f} B0 {a['mae']['p1']['B0']:.3f}", fontsize=8)
        ax.set_xlabel("temperature")
        ax.set_ylim(0, max(0.6, max(hi) + 0.05))
    axs[0][0].set_ylabel("share of the T-1 minority algorithm")
    axs[0][-1].legend(fontsize=6)
    save(fig, "F3_pred_vs_obs")


def f4(an: dict) -> None:
    fig, ax = plt.subplots(figsize=(3.6, 3.4))
    for u, a in an["units"].items():
        fam = UNITS[u]["family"]
        for T in TEMPS:
            c = a["cells"][f"p1|{T}"]
            for j, b in enumerate(a["bins"]):
                p, o = c["pred"]["L"][j], c["shares"][j]
                if p < 0.005 and o == 0:
                    continue
                ax.plot(p, o, "o", ms=3, color=FAM_COL[fam], alpha=0.8, mec="none")
    ax.plot([0, 1], [0, 1], "k--", lw=0.8)
    for f, col in FAM_COL.items():
        ax.plot([], [], "o", color=col, label=f)
    ax.set_xlabel("predicted share (law L)")
    ax.set_ylabel("observed share (N = 100)")
    ax.legend(fontsize=7)
    save(fig, "F4_calibration")


def f5() -> None:
    p = RESULTS_DIR / "base_subarm.json"
    if not p.exists():
        return
    b = read_json(p)["tasks"]
    ts = list(b)
    fig, axs = plt.subplots(1, 2, figsize=(7, 2.8))
    x = np.arange(len(ts))
    axs[0].bar(x - 0.2, [np.mean(b[t]["margin_instr"]) for t in ts], 0.4, label="instruct", color="#0072B2")
    axs[0].bar(x + 0.2, [np.mean(b[t]["margin_base"]) for t in ts], 0.4, label="base", color="#E69F00")
    axs[0].set_xticks(x)
    axs[0].set_xticklabels(ts)
    axs[0].set_ylabel("decision margin (nats, T 1)")
    axs[0].legend(fontsize=7)
    axs[1].bar(x, [b[t]["phrasing_dH_mean"] or 0 for t in ts], color="#009E73")
    lo = [b[t]["phrasing_dH_ci"][0] for t in ts]
    hi = [b[t]["phrasing_dH_ci"][1] for t in ts]
    mid = [b[t]["phrasing_dH_mean"] or 0 for t in ts]
    axs[1].errorbar(x, mid, yerr=[np.clip(np.array(mid) - lo, 0, None), np.clip(np.array(hi) - mid, 0, None)],
                    fmt="none", ecolor="k", capsize=2)
    axs[1].axhline(0.5, color="k", ls="--", lw=0.7)
    axs[1].axhline(-0.5, color="k", ls="--", lw=0.7)
    axs[1].set_xticks(x)
    axs[1].set_xticklabels(ts)
    axs[1].set_ylabel("mean H_base - H_instr at\nphrasing positions (nats)")
    save(fig, "F5_base_vs_instruct")


def f6(an: dict) -> None:
    us = list(an["units"])
    if not us:
        return
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.8))
    w = 0.8 / len(TEMPS)
    for i, T in enumerate(TEMPS):
        acc = [an["units"][u]["replay"][f"p1|{T}"]["accuracy"] or 0 for u in us]
        axs[0].bar(np.arange(len(us)) + i * w, acc, w, label=f"T {T}", color=PAL[i])
    axs[0].set_xticks(np.arange(len(us)) + 0.3)
    axs[0].set_xticklabels(us, rotation=30, fontsize=7)
    axs[0].set_ylabel("per-slot replay accuracy\n(on-opening slots)")
    axs[0].set_ylim(0, 1.05)
    axs[0].legend(fontsize=6)
    for u in us:
        rg = [an["units"][u]["replay"][f"p1|{T}"]["realisation_gap_tvd"] for T in TEMPS]
        mg = [an["units"][u]["replay"][f"p1|{T}"]["mechanism_gap_tvd"] for T in TEMPS]
        axs[1].plot(mg, rg, "o", ms=4, color=FAM_COL[UNITS[u]["family"]], alpha=0.8)
    axs[1].plot([0, 0.3], [0, 0.3], "k--", lw=0.7)
    axs[1].set_xlabel("mechanism gap TVD (replay-implied vs law)")
    axs[1].set_ylabel("realisation gap TVD\n(observed vs replay-implied)")
    save(fig, "F6_replay")


def main() -> None:
    f1()
    f2()
    ap = RESULTS_DIR / "analysis_L.json"
    if ap.exists():
        an = read_json(ap)
        f3(an)
        f4(an)
        f6(an)
    f5()


if __name__ == "__main__":
    main()
