#!/usr/bin/env python3
"""Figures F1-F8 (PDF + PNG, matplotlib, colourblind-safe palette, Type 42 fonts) from results/*.json only."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)
plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 150})
COL = {"W16A16": "#0072B2", "W16A8": "#56B4E9", "W8A16": "#E69F00", "W8A8": "#D55E00", "W8A8REAL": "#CC79A7",
       "W16A16mm": "#999999"}
PRECS = ["W16A16", "W16A8", "W8A16", "W8A8", "W8A8REAL"]


def rj(name: str) -> dict:
    p = RES / name
    return json.loads(p.read_text()) if p.exists() else {}


def save(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(FIG / f"{name}.pdf")
    fig.savefig(FIG / f"{name}.png", dpi=200)
    plt.close(fig)


def f1_factorial() -> None:
    fac, it4 = rj("factorial.json"), rj("iter4_reference.json")
    it5 = it4.get("iter5_bf16_reference", {})
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.4), sharey=True)
    arms = ["TWIN", "PN_a1", "PN_a2"]
    for ax, t in zip(axes, ("T10", "T2", "T03")):
        x = np.arange(len(arms))
        w = 0.16
        for i, p in enumerate(PRECS):
            ys, lo, hi = [], [], []
            for a in arms:
                c = fac.get(f"{t}|{p}|{a}", {})
                y = c.get("Y_correct")
                ci = c.get("Y_correct_wilson95") or [None, None]
                ys.append(np.nan if y is None else y)
                lo.append(0 if y is None or ci[0] is None else y - ci[0])
                hi.append(0 if y is None or ci[1] is None else ci[1] - y)
            ax.bar(x + (i - 2) * w, ys, w, yerr=[lo, hi], color=COL[p], label=p, capsize=1.5, linewidth=0)
        for j, a in enumerate(arms):
            r4 = it4.get("tasks", {}).get(t, {}).get(a, {}).get("Y_correct")
            if r4 is not None:
                ax.plot([j - 0.42, j + 0.42], [r4, r4], color="k", lw=1.2, ls="--",
                        label="iteration 4 (exp19, FP8)" if j == 0 and t == "T10" else None)
            r5 = it5.get(t, {}).get(a, {}).get("correct_only_off_default_share")
            if r5 is not None:
                ax.plot([j - 0.42, j + 0.42], [r5, r5], color="k", lw=1.2, ls=":",
                        label="iteration 5 (exp27, bf16)" if j == 0 and t == "T10" else None)
        ax.set_xticks(x)
        ax.set_xticklabels(["twin", "PN alpha 1", "PN alpha 2"])
        ax.set_title(t)
        ax.set_ylim(0, 1)
    axes[0].set_ylabel("correct off-default share")
    axes[0].legend(fontsize=6.5, frameon=False, loc="upper left")
    save(fig, "F1_factorial")


def f2_flips() -> None:
    prim = rj("primary_E.json")
    fig, axes = plt.subplots(1, 2, figsize=(6.2, 2.8))
    for ax, t in zip(axes, ("T10", "T2")):
        tb = prim.get("tasks", {}).get(t, {}).get("table")
        if not tb:
            ax.axis("off")
            continue
        m = np.array([[tb["11"], tb["10"]], [tb["01"], tb["00"]]])
        ax.imshow(m, cmap="Oranges")
        for i in range(2):
            for j in range(2):
                ax.text(j, i, str(m[i, j]), ha="center", va="center", fontsize=11)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["W16A16 off", "W16A16 default"])
        ax.set_yticks([0, 1])
        ax.set_yticklabels(["W8A8 off", "W8A8 default"])
        p = prim["tasks"][t]["mcnemar"]["p_two_sided"]
        ax.set_title(f"{t} PN alpha 2 (McNemar p={p:.2g})", fontsize=8)
    save(fig, "F2_flip_matrices")


def f3_divergence() -> None:
    mech = rj("mechanism.json").get("precisions", {})
    fig, axes = plt.subplots(2, 2, figsize=(9, 5.4), sharex=True)
    for row, t in enumerate(("T10", "T2")):
        for col, cls in enumerate(("spec", "R")):
            ax = axes[row, col]
            for p in PRECS + ["W16A16mm"]:
                d = mech.get(f"{t}|{p}", {}).get(f"divergence_{cls}", {})
                if d:
                    ls = sorted(d, key=int)
                    ax.plot([int(l) for l in ls], [d[l] for l in ls], color=COL[p], label=p, lw=1.2)
            fl = rj("mechanism.json").get("clean_vs_clean_rel_divergence", {}).get(f"{t}|W16A16mm_vs_W16A16")
            if fl and cls == "R":
                pass
            ax.set_title(f"{t}: pushed vs clean, {cls} positions", fontsize=8)
            ax.set_yscale("log")
            if row == 1:
                ax.set_xlabel("block")
            if col == 0:
                ax.set_ylabel("||dh|| / (alpha * mean n)")
    axes[0, 0].legend(fontsize=6, frameon=False)
    save(fig, "F3_divergence_travel")


def f4_population() -> None:
    pop = rj("population40.json").get("tasks", {})
    fig, axes = plt.subplots(1, 2, figsize=(7.5, 3.4))
    for ax, t in zip(axes, ("T10", "T2")):
        pd = pop.get(t, {}).get("per_direction", {})
        if "W8A8" not in pd or "W16A16" not in pd:
            ax.axis("off")
            continue
        dirs = sorted(set(pd["W8A8"]) & set(pd["W16A16"]))
        x = [pd["W16A16"][d]["share"] for d in dirs]
        for p, mk in (("W8A8", "o"), ("W8A16", "s"), ("W16A8", "^"), ("W8A8REAL", "x")):
            if p in pd:
                y = [pd[p].get(d, {}).get("share", np.nan) for d in dirs]
                ax.scatter(np.array(x) + np.random.default_rng(1).uniform(-0.012, 0.012, len(x)), y, s=14,
                           marker=mk, color=COL[p], label=p, alpha=0.8)
        ax.plot([0, 1], [0, 1], color="k", lw=0.6)
        ax.set_xlabel("W16A16 per-direction share")
        ax.set_ylabel("per-direction share")
        ax.set_title(f"{t}: 40 fixed directions, alpha 2", fontsize=8)
        ax.set_xlim(-0.05, 1.05)
        ax.set_ylim(-0.05, 1.05)
    axes[0].legend(fontsize=6, frameon=False)
    save(fig, "F4_population40")


def f5_attribution() -> None:
    att = rj("attribution.json").get("tasks", {})
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.8), sharey=True)
    for ax, t in zip(axes, ("T10", "T2")):
        e = att.get(t, {}).get("effects")
        if not e:
            ax.axis("off")
            continue
        ax.plot([0, 1], [e["share_W16A16"], e["share_W8A16"]], "-o", color="#0072B2", label="activations bf16")
        ax.plot([0, 1], [e["share_W16A8"], e["share_W8A8"]], "-o", color="#D55E00", label="activations e4m3")
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["weights bf16", "weights e4m3"])
        ax.set_title(f"{t}: AME {e['AME']:.2f}, WME {e['WME']:.2f}, INT {e['INT']:.2f}", fontsize=8)
        ax.set_ylim(0, 1)
    axes[0].set_ylabel("PN alpha 2 correct off-default share")
    axes[0].legend(fontsize=7, frameon=False)
    save(fig, "F5_attribution")


def f6_dither() -> None:
    fac = rj("factorial.json")
    fig, axes = plt.subplots(1, 2, figsize=(7.5, 2.9), sharey=True)
    for ax, t in zip(axes, ("T10", "T2")):
        cells = [("W16A16 twin", f"{t}|W16A16|TWIN"), ("dither(i) twin", f"{t}|W16A16|DITHER_TWIN_v1"),
                 ("dither(ii) twin", f"{t}|W16A16|DITHER_TWIN_v2"), ("W16A16 PN2", f"{t}|W16A16|PN_a2"),
                 ("dither(i) PN2", f"{t}|W16A16|DITHER_PN2_v1"), ("dither(ii) PN2", f"{t}|W16A16|DITHER_PN2_v2"),
                 ("W8A8 PN2", f"{t}|W8A8|PN_a2")]
        ys = [fac.get(k, {}).get("Y_correct", np.nan) for _, k in cells]
        cols = ["#0072B2", "#999999", "#666666", "#0072B2", "#999999", "#666666", "#D55E00"]
        ax.bar(range(len(cells)), ys, color=cols)
        ax.set_xticks(range(len(cells)))
        ax.set_xticklabels([c for c, _ in cells], rotation=45, ha="right", fontsize=7)
        ax.set_title(t)
        ax.set_ylim(0, 1)
    axes[0].set_ylabel("correct off-default share")
    save(fig, "F6_dither")


def f7_landing() -> None:
    fac = rj("factorial.json")
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.2))
    for ax, t in zip(axes, ("T10", "T2", "T03")):
        labs = sorted({l for p in PRECS for l in fac.get(f"{t}|{p}|PN_a2", {}).get("correct_composition", {})})
        bottom = np.zeros(len(PRECS))
        cmap = plt.get_cmap("tab10")
        for i, l in enumerate(labs):
            v = np.array([fac.get(f"{t}|{p}|PN_a2", {}).get("correct_composition", {}).get(l, 0) for p in PRECS],
                         dtype=float)
            ax.bar(range(len(PRECS)), v, bottom=bottom, label=l, color=cmap(i % 10))
            bottom += v
        ax.set_xticks(range(len(PRECS)))
        ax.set_xticklabels(PRECS, rotation=30, fontsize=7)
        ax.set_title(f"{t}: correct programs, PN alpha 2", fontsize=8)
        ax.legend(fontsize=6, frameon=False)
    axes[0].set_ylabel("count")
    save(fig, "F7_landing")


def f8_scale() -> None:
    mech = rj("mechanism.json").get("precisions", {})
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.0))
    for ax, key, title in zip(axes, ("scale_changed_share", "scale_change", "rerounding_gain"),
                              ("share of rows whose FP8 scale changes", "relative absmax change",
                               "re-rounding gain")):
        for p in ("W16A16", "W8A8"):
            for t, ls_ in (("T10", "-"), ("T2", "--")):
                d = mech.get(f"{t}|{p}", {}).get(key, {}).get("spec", {})
                if not d:
                    continue
                by_block: dict[int, list[float]] = {}
                for k, v in d.items():
                    if v is None:
                        continue
                    by_block.setdefault(int(k.split(":")[0]), []).append(v)
                bl = sorted(by_block)
                ax.plot(bl, [np.mean(by_block[b]) for b in bl], ls_, color=COL[p], label=f"{t} {p}", lw=1.1)
        ax.set_title(f"{title} (spec positions)", fontsize=8)
        ax.set_xlabel("block")
    axes[0].legend(fontsize=6, frameon=False)
    save(fig, "F8_scale_rerounding")


def f9_unit() -> None:
    """Unit cross + POST-HOC iteration-5 replication: ban unit (PN_a2) vs ban-free unit (PNF_a2) vs exp27's exact
    seeds and per-template ban-free unit (IT5_a2), under W16A16 and W8A8, with exp27's own share."""
    fac = rj("factorial.json")
    it5 = rj("iter4_reference.json").get("iter5_bf16_reference", {})
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.1), sharey=True)
    for ax, t in zip(axes, ("T10", "T2")):
        groups = [("ban unit\n(iter-4 seeds)", "PN_a2"), ("ban-free unit\n(iter-4 seeds)", "PNF_a2"),
                  ("iter-5 seeds +\nper-template ban-free", "IT5_a2")]
        x = np.arange(len(groups))
        for i, p in enumerate(("W16A16", "W8A8")):
            ys, lo, hi = [], [], []
            for _, arm in groups:
                c = fac.get(f"{t}|{p}|{arm}", {})
                y = c.get("Y_correct")
                ci = c.get("Y_correct_wilson95") or [None, None]
                ys.append(np.nan if y is None else y)
                lo.append(0 if y is None else y - ci[0])
                hi.append(0 if y is None else ci[1] - y)
            ax.bar(x + (i - 0.5) * 0.36, ys, 0.36, yerr=[lo, hi], color=COL[p], label=p, capsize=2)
        r5 = it5.get(t, {}).get("PN_a2", {}).get("correct_only_off_default_share")
        if r5 is not None:
            ax.plot([1.6, 2.4], [r5, r5], "k:", lw=1.3, label="exp27 (iteration 5) PN alpha 2")
        ax.set_xticks(x)
        ax.set_xticklabels([g for g, _ in groups], fontsize=7)
        ax.set_title(f"{t}: PN alpha 2 by dose unit", fontsize=9)
        ax.set_ylim(0, 1)
    axes[0].set_ylabel("correct off-default share")
    axes[0].legend(fontsize=7, frameon=False)
    save(fig, "F9_unit_decomposition")


def main() -> None:
    for f in (f1_factorial, f2_flips, f3_divergence, f4_population, f5_attribution, f6_dither, f7_landing, f8_scale,
              f9_unit):
        try:
            f()
        except (KeyError, ValueError, TypeError, IndexError) as e:
            print(f"figure {f.__name__} failed: {e}")
    print(sorted(p.name for p in FIG.glob("*.png")))


if __name__ == "__main__":
    main()
