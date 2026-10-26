#!/usr/bin/env python3
"""Figures F1-F6 (matplotlib, Okabe-Ito palette, vector PDF + PNG) drawn only from results/*.json:
F1 Stage A transfer heat maps (task x cell; route class annotated; Wilson CIs in the cells)
F2 ST: correct off-default share against realised log D_R per site and task
F3 ST indicator-model coefficients with profile and cluster-bootstrap intervals
F4 S3 vs departure-matched decoding: paired discordant flips
F5 top-five plan push and prompt TOP5 ban on the forced-prompt geometry, in actual activation coordinates
F6 L: forecast top-1 hits and log scores per event"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import FIG_DIR, RESULTS_DIR, read_json, setup_logging  # noqa: E402

OI = ["#000000", "#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7", "#999999"]
SITE_COL = {"S0": OI[0], "S4": OI[7], "S5": OI[5], "S1": OI[1], "S2": OI[2], "S1E": OI[6], "S2E": OI[8], "S3": OI[3]}
plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42, "ps.fonttype": 42, "axes.spines.top": False,
                     "axes.spines.right": False})
CELLS = ["BAN", "X_0-11", "X_12-23", "X_24-35", "X_0-35", "COND", "RPOS", "MR_0-35", "MR_12-23", "PLACEBO"]


def save(fig: plt.Figure, name: str) -> None:
    FIG_DIR.mkdir(exist_ok=True)
    fig.savefig(FIG_DIR / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIG_DIR / f"{name}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"figure {name}")


def f1() -> None:
    p = RESULTS_DIR / "stage_a.json"
    if not p.exists():
        return
    a = read_json(p)["tasks"]
    tasks = [t for t in ("T2", "T03", "T10", "T1", "T05", "T06") if t in a]
    fig, axes = plt.subplots(1, 2, figsize=(16, 4.4), gridspec_kw={"wspace": 0.55})
    for ax, key, title in ((axes[0], "transfer", "Transfer on Y (share Y in cell minus twin; Wilson 95% CI)"),
                           (axes[1], "off_default_transfer", "Off-default transfer")):
        M = np.full((len(tasks), len(CELLS)), np.nan)
        for i, t in enumerate(tasks):
            for j, c in enumerate(CELLS):
                v = a[t]["cells"].get(c, {}).get(key)
                if v is not None:
                    M[i, j] = v
        im = ax.imshow(M, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
        for i, t in enumerate(tasks):
            for j, c in enumerate(CELLS):
                cc = a[t]["cells"].get(c)
                if cc is None:
                    continue
                txt = f"{M[i, j]:.2f}"
                if key == "transfer":
                    lo, hi = cc["Y_ci95_wilson"]
                    txt += f"\n[{lo - a[t]['TWIN']['Y_share']:.2f},{hi - a[t]['TWIN']['Y_share']:.2f}]"
                ax.text(j, i, txt, ha="center", va="center", fontsize=5.5,
                        color="white" if abs(M[i, j]) > 0.6 else "black")
        ax.set_xticks(range(len(CELLS)), CELLS, rotation=45, ha="right")
        ax.set_yticks(range(len(tasks)), [f"{t} ({a[t]['route_class_iter2_3']}; Y={a[t]['Y']})" if key == "transfer"
                                          else t for t in tasks])
        ax.set_title(title, fontsize=9)
        fig.colorbar(im, ax=ax, fraction=0.03)
    fig.suptitle("F1. Stage A: full-state exchange of the ban's residual states into the neutral twin (N = 30 per cell)",
                 fontsize=9)
    save(fig, "F1_stageA_transfer")


def f2_f3() -> None:
    p = RESULTS_DIR / "site_grid.json"
    if not p.exists():
        return
    g = read_json(p)["tasks"]
    fig, axes = plt.subplots(1, len(g), figsize=(5.2 * len(g), 3.6), squeeze=False)
    for ax, (t, res) in zip(axes[0], g.items()):
        for key, c in res["cells"].items():
            if c["site"] == "S3" or c["median_D_R"] is None:
                continue
            x = math.log(c["median_D_R"] + 1e-3)
            ax.scatter(x, c["correct_off_default"], color=SITE_COL.get(c["site"], "grey"), s=14 + 6 * c["alpha"],
                       label=c["site"])
            ax.annotate(f"{c['alpha']:g}", (x, c["correct_off_default"]), fontsize=6, xytext=(2, 2),
                        textcoords="offset points")
        h, lab = ax.get_legend_handles_labels()
        u = dict(zip(lab, h))
        ax.legend(u.values(), u.keys(), fontsize=6, frameon=False)
        ax.axhline(res["twin_correct_off_default"], color="grey", ls=":", lw=0.8)
        ax.set_xlabel("log realised displacement at R, block 35 (ban-free units; cell median)")
        ax.set_ylabel("correct off-default share")
        ax.set_title(f"{t} (marker size / label = alpha; dotted = twin)", fontsize=9)
    fig.suptitle("F2. Noise-site grid in bf16: outcome against realised downstream displacement", fontsize=9)
    save(fig, "F2_site_grid")
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    y = 0
    ticks = []
    for t, res in g.items():
        arms = res.get("rule_arms") or {}
        for key, off, col, lab in (("indicator", 0.0, OI[5], "committed rule model (all alpha)"),
                                   ("indicator_alpha_le4_posthoc", 0.32, OI[3], "post-hoc: alpha <= 4")):
            ind = res.get(key) or {}
            if "beta" not in ind:
                continue
            yy = y
            for nm in ("S4", "S5", "S1", "S2"):
                if nm not in ind["beta"]:
                    continue
                b_ = ind["beta"][nm]
                pci = ind["profile_ci95"].get(nm, [np.nan, np.nan])
                bci = (ind.get("cluster_bootstrap") or {}).get("ci95", {}).get(nm)
                ax.plot([max(pci[0], -12), min(pci[1], 12)], [yy + off, yy + off], color=col, lw=2, alpha=0.55,
                        label=lab if (t, key) == (list(g)[0], key) and nm == "S4" else None)
                if bci:
                    ax.plot(bci, [yy + off + 0.1] * 2, color=OI[6], lw=1.1,
                            label="slot-cluster bootstrap 95%" if (t, key, nm) == (list(g)[0], "indicator", "S1")
                            else None)
                ax.plot(b_, yy + off, "o", color="black", ms=3)
                if key == "indicator":
                    arm = {"S1": arms.get("S1"), "S2": arms.get("S2")}.get(nm) or nm
                    ticks.append((yy, f"{t}: {nm}" + (f" ({arm} arm)" if arm != nm else "")))
                yy += 1
        y = yy + 0.9
    ax.axvline(0, color="grey", lw=0.8)
    if ticks:
        ax.set_yticks([a_ for a_, _ in ticks], [b_ for _, b_ in ticks], fontsize=7)
    ax.set_xlabel("Firth logit coefficient vs S0 at matched log D_R and log D_g1 (bars: profile 95% CI)")
    ax.legend(fontsize=6.5, frameon=False, loc="lower right")
    ax.set_title("F3. Site indicator model (prefill sites): negative = moves the algorithm less than S0", fontsize=9)
    save(fig, "F3_indicator_coefficients")


def f4() -> None:
    p = RESULTS_DIR / "state_vs_token.json"
    if not p.exists():
        return
    d = {k: v for k, v in read_json(p).items() if isinstance(v, dict)}
    if not d:
        return
    fig, ax = plt.subplots(figsize=(5.5, 3))
    keys = sorted(d)
    xs = np.arange(len(keys))
    ax.bar(xs - 0.18, [d[k]["S3_only_flips"] for k in keys], 0.36, color=OI[3], label="S3 only (state noise)")
    ax.bar(xs + 0.18, [d[k]["DMD_only_flips"] for k in keys], 0.36, color=OI[1], label="DMD only (KL-matched T)")
    for x, k in zip(xs, keys):
        T = (d[k].get("calibration") or {}).get("T_dmd")
        ax.text(x, max(d[k]["S3_only_flips"], d[k]["DMD_only_flips"]) + 0.3,
                f"p={d[k]['p_exact_mcnemar']:.3g}\nT={T:.2f}" if T else f"p={d[k]['p_exact_mcnemar']:.3g}",
                ha="center", fontsize=6)
    ax.set_xticks(xs, keys)
    ax.set_ylabel("discordant correct off-default flips")
    ax.legend(fontsize=7, frameon=False)
    ax.set_title("F4. Generated-token state noise vs departure-matched temperature (N = 50 paired slots)",
                 fontsize=8)
    save(fig, "F4_state_vs_token")


def f5() -> None:
    p = RESULTS_DIR / "top5_push.json"
    if not p.exists():
        return
    d = read_json(p)
    geo = d.get("geometry")
    if not geo:
        return
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.0), gridspec_kw={"wspace": 0.3})
    C = np.array(geo["centroids_pc"])
    names = geo["centroid_names"]
    banned = {"bfs", "dfs", "gbfs", "iddfs", "astar"}
    pts = geo["points_pc"]
    sty = {"twin": (OI[8], "o", "neutral twin"), "ban1": (OI[0], "x", "BFS ban"),
           "top5ban": (OI[7], "^", "prompt TOP5 ban")}
    for ax, zoom in ((axes[0], False), (axes[1], True)):
        for (x, y), n in zip(C, names):
            ax.scatter(x, y, s=70, marker="s", color=OI[6] if n in banned else OI[3], edgecolor="black", zorder=3)
            ax.annotate(n, (x, y), fontsize=7, xytext=(3, 3), textcoords="offset points")
        done = set()
        for k, xy in pts.items():
            kind = k.split("__")[0]
            if kind.startswith("push"):
                a_ = float(kind[4:])
                if zoom and a_ > 1:
                    continue
                lab = f"push alpha {a_:g}"
                ax.scatter(*xy, s=10 + 8 * a_, color=OI[5], alpha=0.35 + 0.08 * a_, label=lab if lab not in done else None)
                done.add(lab)
                continue
            col, mk, lab = sty.get(kind, (OI[8], ".", kind))
            ax.scatter(*xy, color=col, marker=mk, s=36, label=lab if lab not in done else None, zorder=4)
            done.add(lab)
        e = geo["explained_by_pc1_pc2_of_centroids"]
        ax.set_xlabel(f"PC1 of the 10 forced-prompt centroids ({100 * e[0]:.0f}% of centroid variance)")
        ax.set_ylabel(f"PC2 ({100 * e[1]:.0f}%)")
        ax.legend(fontsize=6, frameon=False, loc="lower left" if not zoom else "best")
        ax.set_title(("(b) zoom on the centroid region (push alpha 1 only)" if zoom else
                      "(a) activation space: spec-mean block outputs 12-23 / median block norm") +
                     "\nred squares = banned five, green = survivors", fontsize=8)
    ax = axes[2]
    m = geo.get("mds_geodesic_knn")
    if m:
        XY = np.array(m["xy"])
        for (x, y), lab in zip(XY, m["labels"]):
            if lab in names:
                ax.scatter(x, y, s=60, marker="s", color=OI[6] if lab in banned else OI[3], edgecolor="black")
                ax.annotate(lab, (x, y), fontsize=6, xytext=(3, 3), textcoords="offset points")
            else:
                kind = lab.split("__")[0]
                col = OI[5] if kind.startswith("push") else sty.get(kind, (OI[8],))[0]
                ax.scatter(x, y, s=14, color=col, alpha=0.7)
        ax.set_title(f"(c) geodesic distances on a k = {m['k']} nearest-neighbour graph, classical MDS", fontsize=8)
        ax.set_xlabel("MDS 1")
        ax.set_ylabel("MDS 2")
    lt = d.get("landing_test", {})
    cells = d.get("cells", {})
    txt = "; ".join(f"{k}: {cells.get(k, {}).get('correct_non_bfs', 0)} correct non-BFS, "
                    f"{v.get('n_on_survivors', 0)} on survivors" for k, v in lt.items())
    fig.suptitle("F5. T1 top-five plan push (exp20 u_top5, bf16) and the prompt top-five ban on the forced-prompt "
                 "geometry. " + txt, fontsize=7.5)
    save(fig, "F5_top5_geometry")


def f6() -> None:
    p = RESULTS_DIR / "landing_forecast.json"
    if not p.exists():
        return
    d = read_json(p)
    ev = d["events"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    names = ("BASE", "TWINMIN", "OPEN", "OPEN_rank")
    cols = (OI[5], OI[1], OI[3], OI[8])
    x = np.arange(len(ev))
    for i, (nm, col) in enumerate(zip(names, cols)):
        hits = [1 if r.get(f"{nm}_hit") else (0 if r.get(f"{nm}_hit") is not None else np.nan) for r in ev]
        axes[0].scatter(x, np.array(hits) + 0.08 * (i - 1.5), color=col, s=12, label=nm)
        ls = [r.get(f"{nm}_logscore") if r.get(f"{nm}_logscore") is not None else np.nan for r in ev]
        axes[1].plot(x, ls, "o-", color=col, ms=3, lw=0.8, label=nm)
    for ax in axes:
        ax.set_xticks(x, [r["event"].replace("qwen_", "Q").replace("gemma|", "G|") for r in ev], rotation=70,
                      fontsize=6)
        ax.legend(fontsize=6, frameon=False)
    axes[0].set_ylabel("top-1 hit (1) / miss (0)")
    axes[1].set_ylabel("mean log score of the landing composition")
    st = d["primary_sign_test"]
    fig.suptitle(f"F6. Retrospective landing forecasts on {d['n_events']} recorded events. Sign test BASE > OPEN: "
                 f"{st['base_wins']}:{st['open_wins']} discordant, p = {st['p_one_sided_base_gt_open']:.3g}",
                 fontsize=8)
    save(fig, "F6_landing_forecasts")


def main() -> None:
    setup_logging("figures6")
    for f in (f1, f2_f3, f4, f5, f6):
        try:
            f()
        except (KeyError, ValueError, TypeError, IndexError) as e:
            logger.exception(f"{f.__name__} failed: {e}")


if __name__ == "__main__":
    main()
