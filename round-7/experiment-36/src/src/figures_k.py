#!/usr/bin/env python3
"""Figures of step K (PDF + PNG in figures/), drawn only from data/ and results/ files.

F1 s1_interaction      2x2 shares (Y, Wilson 95%) per task and alpha: unit on x, seeds as lines, D5 beside
F2 unit_heatmaps       dose units [block 12-23 x spec token] in activation-norm units (T10 W1): U_abs, U_bf, U_bf*,
                       P_top, P_rest, P_shuf, plus the twin's residual norm ||h_twin|| for scale
F3 displacement_blocks realised displacement ||delta h|| vs block 0-35 (spec-mean, read position R, generated pos. 1)
                       per design at alpha 2, mean over rows (log y)
F4 escape_vs_disp      per-sample outcome (escaped = Y) vs block-35 R displacement norm, by design (alpha 1, 2)
F5 pca_disp35          PCA of block-35 R displacement vectors (actual residual coordinates, fp16 logs) per task,
                       colour = realised algorithm, marker = design
F6 price_frontiers     pass cost vs best reachable correct-only Hill-1 per task for PN* and the knobs
E1 dose_response       exploratory: share Y and pass vs alpha for U_bf (D3) and U_abs (D1), x = alpha and x = block-35
                       spec-mean displacement

usage: .venv/bin/python src/figures_k.py
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

import k_cfg as K  # noqa: E402
from k_cfg import FIGS, RESULTS, read_json, read_jsonl, wilson  # noqa: E402

plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9, "legend.fontsize": 8,
                     "pdf.fonttype": 42, "ps.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False})
COL = {"D1": "#1b6ca8", "D2": "#5fa8d3", "D3": "#d1495b", "D4": "#edae49", "D5": "#66a182", "PTOP": "#2e294e",
       "PREST": "#8d6a9f", "PSHUF": "#999999", "TWIN": "#444444"}
NAME = {"D1": "D1 U_abs x S4", "D2": "D2 U_abs x S5", "D3": "D3 U_bf x S4", "D4": "D4 U_bf x S5",
        "D5": "D5 U_bf* x S4", "PTOP": "P_top", "PREST": "P_rest", "PSHUF": "P_shuf"}


def save(fig, name: str) -> None:
    fig.savefig(FIGS / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIGS / f"{name}.png", bbox_inches="tight", dpi=170)
    plt.close(fig)
    logger.info(f"figure {name}")


def f1(rows) -> None:
    import analysis_k as A

    fig, axes = plt.subplots(1, 4, figsize=(12, 3.2), sharey=True)
    for ax, (task, alpha) in zip(axes, [("T10", 1.0), ("T10", 2.0), ("T2", 1.0), ("T2", 2.0)]):
        a = "a1" if alpha == 1 else "a2"
        for seeds, (du, db), ls in (("S4", ("D1", "D3"), "-"), ("S5", ("D2", "D4"), "--")):
            ys, lo, hi = [], [], []
            for d in (du, db):
                c = A.cell(rows, task, f"{d}_{a}", A.COMMITTED_KS[(task, alpha)])
                k = sum(r["Y"] for r in c.values())
                n = len(c)
                ys.append(k / n if n else np.nan)
                l, h = wilson(k, n)
                lo.append(max(0.0, ys[-1] - l))
                hi.append(max(0.0, h - ys[-1]))
            x = np.array([0, 1]) + (-0.04 if seeds == "S4" else 0.04)
            ax.errorbar(x, ys, yerr=[lo, hi], fmt="o", ls=ls, color="#1b6ca8" if seeds == "S4" else "#d1495b",
                        capsize=3, label=f"seeds {seeds}")
        c5 = A.cell(rows, task, f"D5_{a}", A.COMMITTED_KS[(task, alpha)])
        if c5:
            k = sum(r["Y"] for r in c5.values())
            n = len(c5)
            l, h = wilson(k, n)
            ax.errorbar([1.45], [k / n], yerr=[[max(0.0, k / n - l)], [max(0.0, h - k / n)]], fmt="s", color=COL["D5"], capsize=3,
                        label="U_bf* x S4 (D5)")
        tw = A.cell(rows, task, "TWIN", K.K20 if task == "T2" else K.K10)
        ax.axhline(sum(r["Y"] for r in tw.values()) / max(len(tw), 1), color="#888", lw=0.8, ls=":", label="twin")
        ax.set_xticks([0, 1, 1.45])
        ax.set_xticklabels(["U_abs", "U_bf", "U_bf*"])
        ax.set_title(f"{task}, alpha {int(alpha)} (N {len(A.cell(rows, task, f'D1_{a}', A.COMMITTED_KS[(task, alpha)]))}/design)")
        ax.set_xlim(-0.3, 1.7)
    axes[0].set_ylabel("share correct named off-default (Y)")
    axes[0].legend(loc="upper right", frameon=False)
    fig.suptitle("S1: the dose unit, not the seeds, decides whether plan noise moves the algorithm", y=1.03)
    save(fig, "F1_s1_interaction")


def f2() -> None:
    p = K.CACHE / "units" / "T10.npz"
    if not p.exists():
        logger.warning("F2 skipped: cache/units/T10.npz missing (run src/dump_units.py)")
        return
    z = np.load(p, allow_pickle=False)
    toks = [t.replace("\n", "\\n") for t in z["tokens_W1"]]
    mats = [("||h_twin|| (residual norm)", z["h_norm_W1"]), ("U_abs (ban displacement n[l,p])", z["U_abs"]),
            ("U_bf = ||h_twin|| x r_Q(l)", z["U_bf_W1"]), ("U_bf* (U_abs per-block energy)", z["U_bf_star_W1"]),
            ("P_top (top-quartile cells)", z["P_top"]), ("P_rest (other cells)", z["P_rest"]),
            ("P_shuf (positions permuted)", z["P_shuf"])]
    fig, axes = plt.subplots(len(mats), 1, figsize=(13, 2.0 * len(mats)), sharex=True)
    vmax = max(float(np.percentile(m, 99.5)) for _, m in mats[1:])
    for ax, (title, m) in zip(axes, mats):
        im = ax.imshow(m, aspect="auto", cmap="magma", vmin=0, vmax=(None if title.startswith("||h") else vmax),
                       interpolation="nearest")
        ax.set_yticks(range(0, 12, 2))
        ax.set_yticklabels([str(12 + i) for i in range(0, 12, 2)])
        ax.set_ylabel("block")
        ax.set_title(title, loc="left")
        plt.colorbar(im, ax=ax, pad=0.01, fraction=0.02, label="norm")
    step = max(1, len(toks) // 60)
    axes[-1].set_xticks(range(0, len(toks), step))
    axes[-1].set_xticklabels([toks[i][:10] for i in range(0, len(toks), step)], rotation=90, fontsize=6)
    axes[-1].set_xlabel("task-spec token (T10, template W1)")
    fig.suptitle("F2: dose units at blocks 12-23 x task-spec positions, in residual-stream norm units (T10 W1)", y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.985))
    save(fig, "F2_unit_heatmaps")


def f3() -> None:
    rec = read_jsonl(K.REALISED)
    fig, axes = plt.subplots(2, 3, figsize=(12, 6), sharex=True)
    for i, task in enumerate(("T10", "T2")):
        for j, (fld, lab) in enumerate((("spec_mean", "spec-mean"), ("R", "read position R"),
                                        ("gen1", "generated position 1"))):
            ax = axes[i, j]
            by = defaultdict(list)
            for r in rec:
                if r["task"] == task and r.get("alpha") == 2.0 and r.get(fld):
                    by[r["design"]].append(r[fld])
            for d in ("D1", "D2", "D3", "D4", "D5", "PTOP", "PREST", "PSHUF"):
                if by.get(d):
                    m = np.mean(np.array(by[d]), axis=0)
                    ax.plot(range(12, 36), m[12:], color=COL[d], label=NAME[d],
                            ls="--" if d in ("D2", "D4") else "-")
            ax.set_yscale("log")
            ax.axvspan(12, 23, color="#eee", zorder=0)
            ax.set_title(f"{task}: {lab}")
            if j == 0:
                ax.set_ylabel("||delta h|| (residual units)")
            if i == 1:
                ax.set_xlabel("block")
    axes[0, 0].legend(frameon=False, ncol=2, fontsize=7)
    fig.suptitle("F3: realised displacement against the clean twin, alpha 2 (grey band = edited blocks; blocks 0-11 are exactly 0)", y=1.01)
    save(fig, "F3_displacement_blocks")


def f4(rows) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
    rng = np.random.default_rng(0)
    for ax, task in zip(axes, ("T10", "T2")):
        for i, d in enumerate(("D1", "D2", "D3", "D4", "D5")):
            sel = [r for r in rows if r["task"] == task and r["design"] == d and r.get("labelled")
                   and r.get("realised_disp") and r["alpha"] in (1.0, 2.0)]
            if not sel:
                continue
            x = np.array([r["realised_disp"]["R_b35"] for r in sel])
            y = np.array([r["Y"] for r in sel]) + rng.uniform(-0.12, 0.12, len(sel)) + (i - 2) * 0.03
            ax.scatter(x, y, s=8, alpha=0.6, color=COL[d], label=NAME[d])
        ax.set_yticks([0, 1])
        ax.set_yticklabels(["default / other", "escaped (Y=1)"])
        ax.set_xscale("log")
        ax.set_xlabel("||delta h|| at block 35, read position (log)")
        ax.set_title(f"{task}: outcome vs block-35 R displacement (alpha 1, 2)")
    axes[0].legend(frameon=False, fontsize=7, loc="center right")
    save(fig, "F4_escape_vs_disp")


def f5(rows) -> None:
    lab = {r["key"]: r for r in rows}
    vecs = defaultdict(dict)
    for p in sorted((K.CACHE / "disp").glob("*.npz")):
        z = np.load(p)
        for k in z.files:
            key, kind = k.split("::")
            if kind == "R35":
                vecs[key.split("|")[0]][key] = z[k].astype(np.float32)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    marks = {"D1": "o", "D2": "s", "D3": "^", "D4": "v", "D5": "D", "PTOP": "P", "PREST": "X", "PSHUF": "*"}
    cmap = {"union_find": "#888888", "dfs": "#1b6ca8", "bfs": "#d1495b", "dijkstra": "#888888", "bf_spfa": "#1b6ca8",
            "other": "#66a182", "invalid": "#edae49", "floyd": "#8d6a9f", "disputed": "#000000"}
    for ax, task in zip(axes, ("T10", "T2")):
        keys = [k for k in vecs.get(task, {}) if k in lab and lab[k].get("labelled") and lab[k]["alpha"] == 2.0
                and lab[k]["design"] != "PREST"]     # P_rest breaks T2 (pass 0) and would own PC1
        if len(keys) < 10:
            continue
        X = np.stack([vecs[task][k] for k in keys])
        Xc = X - X.mean(0)
        U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
        pcs = Xc @ Vt[:2].T
        ev = (S ** 2) / (S ** 2).sum()
        for d, mk in marks.items():
            for lb, c in cmap.items():
                idx = [i for i, k in enumerate(keys) if lab[k]["design"] == d and lab[k]["label"] == lb]
                if idx:
                    ax.scatter(pcs[idx, 0], pcs[idx, 1], marker=mk, s=18, color=c, alpha=0.75, edgecolor="none")
        from matplotlib.lines import Line2D
        h1 = [Line2D([], [], marker=mk, ls="", color="#333", label=NAME[d]) for d, mk in marks.items()
              if any(lab[k]["design"] == d for k in keys)]
        h2 = [Line2D([], [], marker="o", ls="", color=c, label=lb) for lb, c in cmap.items()
              if any(lab[k]["label"] == lb for k in keys)]
        ax.legend(handles=h1 + h2, frameon=False, fontsize=6.5, ncol=2, loc="best")
        ax.set_xlabel(f"PC1 ({100 * ev[0]:.1f}% var.) of delta h, block 35, read position")
        ax.set_ylabel(f"PC2 ({100 * ev[1]:.1f}% var.)")
        ax.set_title(f"{task}: block-35 displacement vectors at alpha 2 (n {len(keys)}; P_rest excluded)")
    save(fig, "F5_pca_disp35")


def f6() -> None:
    p = RESULTS / "s3_prices.json"
    if not p.exists():
        logger.warning("F6 skipped: results/s3_prices.json missing")
        return
    s3 = read_json(p)
    fig, axes = plt.subplots(1, 5, figsize=(16, 3.4), sharey=True)
    cc = {"PN*": "#1b6ca8", "BINT": "#d1495b", "EAP": "#edae49", "IFG": "#66a182", "TEMP": "#999999",
          "TOPK10": "#2e294e"}
    for ax, t in zip(axes, ("T03", "T10", "T2", "T05", "T1")):
        for cls, v in s3["per_task"].get(t, {}).items():
            fr = v.get("frontier") or []
            if fr:
                x = [max(f[0], -0.02) for f in fr]
                y = [f[1] for f in fr]
                ax.step(x, y, where="post", color=cc.get(cls, "#000"), label=f"{cls} (H5 {v['H5']:.2f})",
                        lw=2 if cls == "PN*" else 1.2)
        ax.axvline(0.05, color="#888", ls=":", lw=0.8)
        ax.set_xlim(-0.02, 0.6)
        ax.set_title(t)
        ax.set_xlabel("pass cost (twin pass - mixture pass)")
        ax.legend(frameon=False, fontsize=6.5, loc="lower right")
    axes[0].set_ylabel("best correct-only Hill-1 (depth 25)")
    fig.suptitle(f"F6: price frontiers, plan noise at D* = {s3['D_star']} vs iteration 5's knobs (dotted: 5-point budget)",
                 y=1.03)
    save(fig, "F6_price_frontiers")


def e1() -> None:
    p = RESULTS / "e1_sweep.json"
    if not p.exists():
        return
    r = read_json(p)
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.4))
    for task, mk in (("T10", "o"), ("T2", "s")):
        d = r.get(task, {})
        for unit, arms, c in (("U_bf (D3)", ["D3_a1", "D3_a2", "D3_a3", "D3_a4", "D3_a6"], "#d1495b"),
                              ("U_abs (D1)", ["D1_a1", "D1_a2"], "#1b6ca8")):
            xs = [float(a.split("_a")[1]) for a in arms if a in d]
            ys = [d[a]["Y"]["share"] for a in arms if a in d]
            ps = [d[a]["pass_rate"] for a in arms if a in d]
            dx = [d[a]["realised_mean"]["S_b35"] for a in arms if a in d and d[a].get("realised_mean")]
            axes[0].plot(xs, ys, marker=mk, color=c, label=f"{task} {unit} share Y")
            axes[0].plot(xs, ps, marker=mk, color=c, ls=":", alpha=0.6, label=f"{task} {unit} pass")
            if len(dx) == len(ys):
                axes[1].plot(dx, ys, marker=mk, color=c, label=f"{task} {unit}")
    axes[0].set_xlabel("alpha")
    axes[0].set_ylabel("share / pass rate")
    axes[0].legend(frameon=False, fontsize=6.5)
    axes[1].set_xlabel("mean ||spec-mean delta h|| at block 35")
    axes[1].set_ylabel("share Y")
    axes[1].set_xscale("log")
    axes[1].legend(frameon=False, fontsize=7)
    fig.suptitle("E1 (exploratory): ban-free unit dose response vs the absolute unit", y=1.03)
    save(fig, "E1_dose_response")


def e3() -> None:
    p = RESULTS / "e3_replicate.json"
    if not p.exists():
        return
    r = read_json(p)
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.3), sharey=True)
    for ax, (lab, title) in zip(axes, (("T10_k0_9", "T10, committed slots k 0-9 (S1/S2)"),
                                       ("T10_fresh_k10_19", "T10, fresh slots k 10-19 (E3)"),
                                       ("T03_k0_9", "T03, k 0-9 (E3 2x2)"))):
        if lab == "T10_k0_9":
            s1 = read_json(RESULTS / "s1_2x2.json")["cells"]
            s2 = read_json(RESULTS / "s2_profile.json")["T10"]["cells"]
            cells = {d: s1[f"T10|{d}_a2"] for d in ("D1", "D2", "D3", "D4", "D5")} | {
                {"PTOP": "PTOP", "PREST": "PREST", "PSHUF": "PSHUF"}[k]: v for k, v in s2.items() if k != "D1"}
        elif lab == "T03_k0_9":
            cells = r[lab]["cells"]
        else:
            cells = r[lab]["profiles"]["cells"] | {d: v for d, v in r[lab].get("cells", {}).items()}
            s1c = {}
            n_sl = r[lab]["2x2|Y"]["n_slots"]
            for d in ("D2", "D3", "D4"):
                t = r[lab]["2x2|Y"]["shares"][d]
                s1c[d] = {"Y": {"share": t, "wilson95": list(wilson(int(round(t * n_sl)), n_sl))}}
            cells = {**s1c, **cells}
        order = [d for d in ("D1", "D2", "D3", "D4", "D5", "PTOP", "PREST", "PSHUF") if d in cells]
        ys = [cells[d]["Y"]["share"] for d in order]
        lo = [max(0.0, cells[d]["Y"]["share"] - cells[d]["Y"]["wilson95"][0]) for d in order]
        hi = [max(0.0, cells[d]["Y"]["wilson95"][1] - cells[d]["Y"]["share"]) for d in order]
        ax.bar(range(len(order)), ys, yerr=[lo, hi], color=[COL[d] for d in order], capsize=2)
        ax.set_xticks(range(len(order)))
        ax.set_xticklabels(order, rotation=45, fontsize=7)
        ax.set_title(title)
    axes[0].set_ylabel("share Y at alpha 2 (Wilson 95%)")
    fig.suptitle("E3 (exploratory): the unit effect and the top-quartile effect replicate on fresh slots and on T03",
                 y=1.04)
    save(fig, "E3_replicate")


@logger.catch(reraise=True)
def main() -> None:
    import analysis_k as A

    K.setup_logging("figures_k")
    rows = A.load_joined()
    for fn in (lambda: f1(rows), f2, f3, lambda: f4(rows), lambda: f5(rows), f6, e1, e3):
        try:
            fn()
        except (KeyError, ValueError, IndexError, FileNotFoundError) as e:
            logger.exception(f"figure failed: {e}")


if __name__ == "__main__":
    main()
