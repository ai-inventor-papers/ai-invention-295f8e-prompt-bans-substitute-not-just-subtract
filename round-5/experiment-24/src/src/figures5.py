#!/usr/bin/env python3
"""Figures (matplotlib, deterministic, drawn only from results/*.json): PNG + PDF in figures/.

fig1_compositions   correct-program compositions per task: base chat, instruct twin (S1), T(lambda*) and the S2
                    controls (MR, XT) -- default vs the off-default catalogue modes vs non-catalogue.
fig2_dose           pass rate and correct off-default share against lambda for T and the norm-matched MR (S1).
fig3_d_norms        ||D|| / ||h_instr|| per block at S and at R (mean over 15 tasks), and the ban-free size.
fig4_forest         y-rate difference T - control on S2 (Newcombe 95% CI), Holm-adjusted p per decisive task.
fig5_geometry       metric-MDS panels (S27 and R23) of forced centroids, twins and hooked states.
fig6_claimA         beta_t against the iteration-4 escape fraction E_t (alpha 1).
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import FIG_DIR, LAMBDAS, PRED_DIR, RESULTS_DIR, catalogue, read_json, setup_logging  # noqa: E402

plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42,
                     "ps.fonttype": 42, "figure.dpi": 150})
DEF_C, OTH_C = "#4C72B0", "#BBBBBB"
PAL = ["#DD8452", "#55A868", "#C44E52", "#8172B3", "#937860", "#DA8BC3", "#8C8C8C", "#CCB974"]


def save(fig, name: str) -> None:
    fig.savefig(FIG_DIR / f"{name}.png", bbox_inches="tight")
    fig.savefig(FIG_DIR / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_compositions(c1, conf) -> None:
    tasks = list(conf["per_task"]) if conf else c1["strata"]["BASE-DIVERSE"]
    n = len(tasks)
    cols = 4
    rows = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(3.0 * cols, 2.3 * rows), squeeze=False)
    for ax, t in zip(axes.flat, tasks):
        per = c1["per_task"][t]
        d = per["default"]
        cat = catalogue(t)
        modes = [m for m in cat if m != d]
        bars = [("base", per["base_chat"]["composition_correct"]), ("twin S1", per["twin_S1"]["composition_correct"])]
        if conf and t in conf["per_task"]:
            r = conf["per_task"][t]
            bars.append(("twin S2", r["twin_S2"]["composition_correct"]))
            for a, c in r["arms"].items():
                bars.append((a, c["composition_correct"]))
        x = np.arange(len(bars))
        for i, (name, comp) in enumerate(bars):
            tot = max(sum(comp.values()), 1)
            bottom = 0.0
            seq = [(d, DEF_C)] + [(m, PAL[j % len(PAL)]) for j, m in enumerate(modes)]
            for m, colr in seq:
                v = comp.get(m, 0) / tot
                ax.bar(i, v, bottom=bottom, color=colr, width=0.75, label=m if i == 0 else None)
                bottom += v
            v = sum(k for m, k in comp.items() if m not in cat) / tot
            ax.bar(i, v, bottom=bottom, color=OTH_C, width=0.75, label="non-catalogue" if i == 0 else None)
            ax.text(i, 1.01, str(sum(comp.values())), ha="center", va="bottom", fontsize=6)
        ax.set_xticks(x)
        ax.set_xticklabels([b[0] for b in bars], rotation=45, ha="right", fontsize=6)
        ax.set_ylim(0, 1.12)
        ax.set_title(f"{t} ({per['stratum']}, beta={per['beta']:.2f})", fontsize=8)
        ax.legend(fontsize=5, frameon=False, loc="lower left", ncol=1)
    for ax in list(axes.flat)[n:]:
        ax.axis("off")
    fig.suptitle("Correct-program compositions (count above bar); default in blue", fontsize=9)
    fig.tight_layout()
    save(fig, "fig1_compositions")


def fig_dose(c1, selr) -> None:
    tasks = c1["strata"]["BASE-DIVERSE"] + c1["strata"]["INTERMEDIATE"]
    cols = 4
    rows = int(np.ceil(len(tasks) / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(3.0 * cols, 2.2 * rows), squeeze=False)
    for ax, t in zip(axes.flat, tasks):
        r = selr["per_task"][t]
        tw = r["twin_S1"]
        for kind, ls in (("T", "-"), ("MR", "--")):
            xs, ps, os_ = [0.0], [tw["pass"]], [tw["off_share"] or 0.0]
            for lam in LAMBDAS:
                c = r.get(f"{kind}{lam}")
                if c:
                    xs.append(lam)
                    ps.append(c["pass"])
                    os_.append(c["off_share"] if c["off_share"] is not None else np.nan)
            ax.plot(xs, ps, ls, color="#4C72B0", marker="o", ms=3, label=f"pass {kind}")
            ax.plot(xs, os_, ls, color="#DD8452", marker="s", ms=3, label=f"off-default {kind}")
        ax.axhline(0.8 * (tw["pass"] or 0), color="grey", lw=0.6, ls=":")
        ax.axhline(r["beta"] or 0, color="#55A868", lw=0.8, ls="-.", label="beta (base)")
        ax.set_title(f"{t} (lambda*={r.get('lambda_star')})", fontsize=8)
        ax.set_xlabel("lambda (T) / norm-matched dose (MR)")
        ax.set_ylim(-0.02, 1.05)
        ax.legend(fontsize=5, frameon=False)
    for ax in list(axes.flat)[len(tasks):]:
        ax.axis("off")
    fig.tight_layout()
    save(fig, "fig2_dose")


def fig_d_norms(dn) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(8, 2.6))
    b = np.arange(36)
    axes[0].plot(b, dn["mean_rel_norm_S"], "-o", ms=2, label="task-spec S (mean over positions)")
    axes[0].plot(b, dn["mean_rel_norm_R"], "-s", ms=2, label="read position R")
    axes[0].axvspan(11.5, 23.5, color="#DDDDDD", alpha=0.5, label="transplant band 12-23")
    axes[0].set_xlabel("block")
    axes[0].set_ylabel("||h_base - h_instr|| / ||h_instr||")
    axes[0].legend(fontsize=6, frameon=False)
    for t, v in dn["per_task"].items():
        axes[1].plot(range(12, 24), v["banfree_S_blocks12_23"], lw=0.8, alpha=0.7)
    axes[1].axhline(4, color="red", ls=":", lw=0.8, label="iteration-4 breakage dose (4 units)")
    axes[1].set_xlabel("block")
    axes[1].set_ylabel("||D|| in ban-free units (15 tasks)")
    axes[1].legend(fontsize=6, frameon=False)
    fig.tight_layout()
    save(fig, "fig3_d_norms")


def fig_forest(conf) -> None:
    rows = []
    for t, r in conf["per_task"].items():
        if not r["decisive"]:
            continue
        for a, c in r["arms"].items():
            if "y_diff_newcombe" in c:
                nd = c["y_diff_newcombe"]
                rows.append((f"{t}: T vs {a}", nd["diff"], nd["lo"], nd["hi"], r["holm"].get(c["control_class"])))
    if not rows:
        return
    fig, ax = plt.subplots(figsize=(5, 0.3 * len(rows) + 0.8))
    for i, (name, d, lo, hi, p) in enumerate(rows):
        ax.errorbar(d, i, xerr=[[d - lo], [hi - d]], fmt="o", color="#4C72B0", ms=4, capsize=2)
        ax.text(1.02, i, f"Holm p={p:.3g}" if p is not None else "", va="center", fontsize=6,
                transform=ax.get_yaxis_transform())
    ax.axvline(0, color="grey", lw=0.8)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows], fontsize=6)
    ax.set_xlabel("difference in correct off-default rate per slot (S2), Newcombe 95% CI")
    fig.tight_layout()
    save(fig, "fig4_forest")


def fig_geometry(geo) -> None:
    panels = list(geo["panels"])
    if not panels:
        return
    sites = ["S27", "R23"]
    fig, axes = plt.subplots(len(panels), len(sites), figsize=(3.2 * len(sites), 2.8 * len(panels)), squeeze=False)
    cmap = {"twin:instr": "#4C72B0", "twin:base": "#55A868"}
    for i, t in enumerate(panels):
        for j, s in enumerate(sites):
            ax = axes[i][j]
            g = geo["panels"][t].get(s)
            if not g:
                ax.axis("off")
                continue
            Y = np.array(g["mds_xy"])
            for k, lab in enumerate(g["labels"]):
                if lab.startswith("forced:"):
                    _, tag, alg = lab.split(":")
                    ax.scatter(*Y[k], marker="^" if tag == "instr" else "v", s=22,
                               color="#8172B3" if tag == "instr" else "#937860", alpha=0.8)
                    ax.annotate(alg, Y[k], fontsize=4.5, alpha=0.8)
                elif lab.startswith("twin:"):
                    ax.scatter(*Y[k], marker="o", s=12, color=cmap[lab], alpha=0.8)
                else:
                    arm = lab.split(":")[1]
                    ax.scatter(*Y[k], marker="x" if arm.startswith("ISO") else "s", s=10,
                               color="#C44E52" if arm.startswith("T") else ("#DA8BC3" if arm.startswith("READ")
                                                                            else "#8C8C8C"), alpha=0.7)
            ax.set_title(f"{t} {s} (stress-1 {g['mds_stress1']:.2f})", fontsize=7)
            ax.set_xticks([])
            ax.set_yticks([])
    fig.suptitle("MDS: forced centroids (^ instr, v base), twins (o blue instr, green base), T(lambda*) red squares, "
                 "READ pink, ISO(1) grey x", fontsize=7, y=0.999)
    fig.tight_layout(rect=(0, 0, 1, 0.985))
    save(fig, "fig5_geometry")


def fig_claim_a(c1, sc) -> None:
    ts = sc["tasks"]
    b = [c1["per_task"][t]["beta"] for t in ts]
    e = [sc["alpha_1.0"]["E_t"][t] for t in ts]
    fig, ax = plt.subplots(figsize=(3.4, 2.8))
    ax.scatter(b, e, s=14, color="#4C72B0")
    for t, x, y in zip(ts, b, e):
        ax.annotate(t, (x, y), fontsize=6)
    ax.set_xlabel("beta_t (base off-default share, this artifact)")
    ax.set_ylabel("E_t, alpha 1 (iteration-4 escape fraction)")
    ax.set_title(f"Claim A screen check: Spearman {sc['alpha_1.0']['spearman']:.2f} "
                 f"(one-sided perm p {sc['alpha_1.0']['perm_p_one_sided']:.1g})", fontsize=7)
    fig.tight_layout()
    save(fig, "fig6_claimA")


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("figures5")
    c1 = read_json(PRED_DIR / "commit1.json")
    selr = read_json(RESULTS_DIR / "selection.json")
    conf = read_json(RESULTS_DIR / "confirmation.json") if (RESULTS_DIR / "confirmation.json").exists() else None
    fig_compositions(c1, conf)
    fig_dose(c1, selr)
    fig_d_norms(read_json(RESULTS_DIR / "d_norms.json"))
    if conf:
        fig_forest(conf)
    if (RESULTS_DIR / "geometry.json").exists():
        fig_geometry(read_json(RESULTS_DIR / "geometry.json"))
    fig_claim_a(c1, read_json(RESULTS_DIR / "screen_check.json"))
    logger.info("figures written")


if __name__ == "__main__":
    main()
