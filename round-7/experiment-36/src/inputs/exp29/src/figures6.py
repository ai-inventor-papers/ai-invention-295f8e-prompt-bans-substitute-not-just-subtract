#!/usr/bin/env python3
"""Figures (PDF + PNG) drawn from results/*.json only, so a figure can never disagree with the numbers."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c6  # noqa: E402,F401
from c6 import FIGS, RESULTS, SEEDS_POP, read_json  # noqa: E402

COL = {"a": "#0072B2", "b": "#E69F00", "c": "#009E73", "d": "#555555", "exp19_fp8": "#56B4E9"}
NAME = {"a": "a W8A8", "b": "b W8A16", "c": "c W16A8", "d": "d BF16"}
plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42, "ps.fonttype": 42, "axes.spines.top": False,
                     "axes.spines.right": False})


def save(fig, name: str) -> None:
    fig.savefig(FIGS / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIGS / f"{name}.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def heatmaps(ESC, alpha: str = "2.0") -> None:
    for t in ("T10", "T2"):
        engs = [e for e in ("a", "b", "c", "d") if e in ESC and t in ESC[e] and alpha in ESC[e][t]["alpha"]]
        if len(engs) < (1 if alpha == "2.0" else 2):
            continue
        pa = ESC["a"][t]["alpha"][alpha]["per_direction"]
        order = sorted(SEEDS_POP, key=lambda s: -(pa[str(s)]["share10"] if pa.get(str(s)) else -1))
        M = np.full((len(engs), len(order)), np.nan)
        fig, ax = plt.subplots(figsize=(11, 1.1 + 0.42 * len(engs)))
        for i, e in enumerate(engs):
            pd = ESC[e][t]["alpha"][alpha]["per_direction"]
            for j, s in enumerate(order):
                c = pd.get(str(s))
                if c is None:
                    continue
                M[i, j] = c["share10"]
                if c["confirmed"]:
                    ax.plot(j, i, marker="o", ms=4.5, color="white", mec="black", mew=0.6)
                elif c["screen"]:
                    ax.plot(j, i, marker="o", ms=4.5, color="none", mec="white", mew=1.0)
        cm = plt.get_cmap("magma").copy()
        cm.set_bad("#dddddd")
        im = ax.imshow(np.ma.masked_invalid(M), aspect="auto", cmap=cm, vmin=0, vmax=1, zorder=0)
        ax.set_yticks(range(len(engs)), [NAME[e] for e in engs])
        ax.set_xticks(range(len(order)), [str(s)[-2:] for s in order], fontsize=6)
        ax.set_xlabel("direction seed 91xx (sorted by engine a's first-10 off-default share)")
        ax.set_title(f"{t}: off-default share of the first 10 samples per fixed random push (alpha {alpha}, absolute unit);"
                     f" filled dot = confirmed escape, ring = screen pass only", fontsize=8)
        fig.colorbar(im, ax=ax, fraction=0.02, pad=0.01, label="off-default share")
        save(fig, f"heatmap_directions_{t}" + ("" if alpha == "2.0" else f"_alpha{alpha}"))


def e_by_engine(ESC) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(8, 3), sharey=True)
    for ax, t in zip(axes, ("T10", "T2")):
        for i, e in enumerate(("a", "b", "c", "d")):
            v = ESC.get(e, {}).get(t, {}).get("alpha", {}).get("2.0")
            if not v:
                continue
            for off, key, wk, mk in ((-0.15, "E_t", "E_wilson", "o"), (0.15, "E_screen", "E_screen_wilson", "s")):
                if key == "E_t" and not v["confirmation_complete"]:
                    continue
                y = v[key]
                lo, hi = v[wk]
                ax.errorbar(i + off, y, yerr=[[y - lo], [hi - y]], fmt=mk, color=COL[e], capsize=3,
                            mfc=COL[e] if key == "E_t" else "white")
        ax.set_xticks(range(4), [NAME[e] for e in ("a", "b", "c", "d")], rotation=20)
        ax.set_title(f"{t} (alpha 2, 40 directions)")
        ax.set_ylim(-0.02, 1.0)
        ax.grid(axis="y", alpha=0.3)
    axes[0].set_ylabel("escape fraction E (Wilson 95%)\nfilled = confirmed, open = screen-level")
    save(fig, "E_by_engine")


def scatter(ESC) -> None:
    pairs = [("a", "c"), ("a", "d"), ("d", "b")]
    fig, axes = plt.subplots(2, 3, figsize=(9, 6))
    for r, t in enumerate(("T10", "T2")):
        for k, (x, y) in enumerate(pairs):
            ax = axes[r, k]
            if x not in ESC or y not in ESC or t not in ESC[x] or t not in ESC[y]:
                ax.set_axis_off()
                continue
            px = ESC[x][t]["alpha"]["2.0"]["per_direction"]
            py = ESC[y][t]["alpha"]["2.0"]["per_direction"]
            xs, ys = [], []
            for s in SEEDS_POP:
                if px.get(str(s)) and py.get(str(s)):
                    xs.append(px[str(s)]["share10"])
                    ys.append(py[str(s)]["share10"])
            rng = np.random.default_rng(0)
            ax.scatter(np.array(xs) + rng.uniform(-0.012, 0.012, len(xs)), np.array(ys) + rng.uniform(-0.012, 0.012, len(ys)),
                       s=14, color=COL[y], alpha=0.8)
            ax.plot([0, 1], [0, 1], ls="--", color="grey", lw=0.8)
            ax.set_xlim(-0.05, 1.05)
            ax.set_ylim(-0.05, 1.05)
            ax.set_xlabel(f"{NAME[x]} first-10 share")
            ax.set_ylabel(f"{NAME[y]} first-10 share")
            ax.set_title(f"{t}: {x} vs {y}", fontsize=9)
    fig.tight_layout()
    save(fig, "per_direction_scatter")


def induced() -> None:
    D = {}
    for ws in ("B", "Q"):
        p = RESULTS / f"diagnostics_{ws}.json"
        if p.exists():
            d = read_json(p)
            for k, v in d.items():
                if k.startswith("induced_") and isinstance(v, dict):
                    D[k.split("_")[1]] = v
    if not D:
        return
    fig, axes = plt.subplots(2, 3, figsize=(11, 5.5), sharex=True)
    for r, t in enumerate(("T10", "T2")):
        for k, (g, lab) in enumerate((("S", "task-spec positions S"), ("R", "last prompt position R"),
                                      ("G", "generated positions 1-32"))):
            ax = axes[r, k]
            for e, v in sorted(D.items()):
                if t not in v:
                    continue
                y = [np.nan if z is None else z for z in v[t]["induced_ban_units"][g]]
                ax.plot(range(len(y)), y, color=COL.get(e, "k"), label=NAME.get(e, e), lw=1.4)
            ax.axvspan(12, 23, color="orange", alpha=0.08)
            ax.set_yscale("log")
            ax.set_title(f"{t}: {lab}", fontsize=9)
            if r == 1:
                ax.set_xlabel("decoder block")
            if k == 0:
                ax.set_ylabel("median ||(h_push - h_twin) - nominal||\n(ban units)")
    axes[0, 0].legend(fontsize=7)
    fig.suptitle("Induced (non-nominal) perturbation of an alpha-2 push, teacher-forced on each engine's own twin "
                 "program (shaded: edited blocks 12-23)", fontsize=9)
    fig.tight_layout()
    save(fig, "induced_perturbation")


def rounding() -> None:
    D = {}
    for ws in ("B", "Q"):
        p = RESULTS / f"diagnostics_{ws}.json"
        if p.exists():
            d = read_json(p)
            for k, v in d.items():
                if k.startswith("induced_") and isinstance(v, dict):
                    D[k.split("_")[1]] = v
    if not D:
        return
    e0 = "a" if "a" in D else sorted(D)[0]
    fig, axes = plt.subplots(2, 3, figsize=(11, 5.5), sharex=True)
    for r, t in enumerate(("T10", "T2")):
        if t not in D[e0]:
            continue
        rd = D[e0][t]["rounding"]
        for k, (key, lab) in enumerate((("rel_rms", "RMS(x - dq(q(x))) / RMS(x)"),
                                        ("amp", "||r_push - r_twin|| / ||x_push - x_twin||"),
                                        ("scale_changed", "fraction of moved rows whose s_x changes"))):
            ax = axes[r, k]
            for s, col in zip(("qkv_in", "o_in", "gateup_in", "down_in"), ("#0072B2", "#D55E00", "#009E73", "#CC79A7")):
                y = [np.nan if z is None else z for z in rd[s][key]]
                ax.plot(range(len(y)), y, color=col, label=s, lw=1.3)
            ax.set_title(f"{t}: {lab}", fontsize=8)
            if r == 1:
                ax.set_xlabel("decoder block")
    axes[0, 0].legend(fontsize=7)
    fig.suptitle(f"Per-token e4m3 activation rounding at the four linear-input sites (engine {e0} passes, alpha 2)",
                 fontsize=9)
    fig.tight_layout()
    save(fig, "rounding_by_block")


def pn_fig(PN) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(8, 3), sharey=True)
    for ax, t in zip(axes, ("T10", "T2")):
        for j, a in enumerate(("PN_a1", "PN_a2")):
            cell = PN.get(t, {}).get(a, {})
            for i, e in enumerate(("exp19_fp8", "a", "b", "c", "d")):
                v = cell.get(e)
                if not v or not v.get("n_valid"):
                    continue
                y = v["share"]
                lo, hi = v.get("wilson") or (y, y)
                x = j * 6 + i
                ax.errorbar(x, y, yerr=[[y - lo], [hi - y]], fmt="o", color=COL[e], capsize=2,
                            label=(NAME.get(e, "exp19 FP8 (iteration 4)") if j == 0 else None))
        ax.set_xticks([2, 8], ["alpha 1", "alpha 2"])
        ax.set_title(f"{t}: per-sample plan noise (N = 50 per cell)")
        ax.grid(axis="y", alpha=0.3)
    axes[0].set_ylabel("off-default share (Wilson 95%)")
    axes[1].legend(fontsize=7, loc="upper left")
    save(fig, "pn_by_engine")


def landings_fig(L) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(8, 3))
    for ax, t in zip(axes, ("T10", "T2")):
        comp = L.get(t, {}).get("composition_correct_offdefault", {})
        labs = L.get(t, {}).get("labels", [])
        bottom = np.zeros(4)
        cols = plt.get_cmap("tab10")
        for k, lab in enumerate(labs):
            vals = np.array([comp.get(e, {}).get(lab, 0) for e in ("a", "b", "c", "d")], float)
            ax.bar(range(4), vals, bottom=bottom, color=cols(k % 10), label=lab)
            bottom += vals
        ax.set_xticks(range(4), [NAME[e] for e in ("a", "b", "c", "d")], rotation=20)
        ax.set_title(f"{t}: correct off-default programs (alpha 2, all POP rows)", fontsize=8)
        ax.legend(fontsize=6)
    axes[0].set_ylabel("count")
    save(fig, "landings")


def main() -> None:
    ESC = read_json(RESULTS / "escape_by_engine.json")
    heatmaps(ESC)
    heatmaps(ESC, "1.0")
    e_by_engine(ESC)
    scatter(ESC)
    induced()
    rounding()
    if (RESULTS / "pn.json").exists():
        pn_fig(read_json(RESULTS / "pn.json"))
    if (RESULTS / "landings.json").exists():
        landings_fig(read_json(RESULTS / "landings.json"))
    print(sorted(p.name for p in FIGS.glob("*.png")))


if __name__ == "__main__":
    main()
