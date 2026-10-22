#!/usr/bin/env python3
"""Figures (matplotlib, PDF + PNG, Type-42 fonts, colour-blind-safe palette) from the result files only.

fig1 Hill vs pass cost per E6 task: each class's hull frontier, vertices with 90% CIs, the 5-point line, Hill 1.5 / 2
fig2 correct compositions per E6 task (TWIN, PN a1, PN a2, T1.6, NOVELTY) with fail and invalid shares
fig3 alpha dose-response (pass, off-default share, Hill) on E6
fig4 ideas vs phrasing clusters within the default idea, per knob
fig5 engine check: screen vs this run per cell, with per-slot agreement
fig6 forest plot of D_t with the pooled D_bar
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import DATA_DIR, DEFAULT, FIG_DIR, RESULTS_DIR, read_json, read_jsonl, setup_logging  # noqa: E402

plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.size": 9, "axes.titlesize": 10,
                     "axes.spines.top": False, "axes.spines.right": False, "savefig.bbox": "tight"})
OKABE = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#000000", "#999999",
         "#882255", "#44AA99", "#117733"]
E6 = ("T03", "T05", "T06", "T10", "T1", "T2")
CLASS_COL = {"PN": OKABE[3], "TEMP": OKABE[0], "TOPK10": OKABE[5], "NONCE": OKABE[1], "NOVELTY": OKABE[4],
             "SEMSEED": OKABE[2], "VETO_1SHOT": OKABE[8], "VETO_PERSIST": OKABE[9], "VETO_ITER": OKABE[10],
             "MINP": OKABE[7], "VS": OKABE[11]}


def save(fig, name: str) -> None:
    for ext in ("pdf", "png"):
        fig.savefig(FIG_DIR / f"{name}.{ext}", dpi=200)
    plt.close(fig)
    logger.info(f"figure {name}")


def fig1(samples, reused) -> None:
    from analysis.core import TaskData, class_vertices
    from analysis.hull import Hull, fixed_uniforms
    from analysis.run_all import load_other_map, task_rows

    U = fixed_uniforms(300)
    omap = load_other_map()
    kr = {(r["task"], r["arm"]): r for r in read_jsonl(RESULTS_DIR / "knob_rows.jsonl")}
    fig, axes = plt.subplots(2, 3, figsize=(11, 6.5), sharey=True)
    cs = np.linspace(-5, 40, 91)
    for ax, t in zip(axes.ravel(), E6):
        td = TaskData(t, task_rows(samples, reused, t), omap)
        for cls, col in CLASS_COL.items():
            arms = class_vertices(td, cls)
            if arms is None:
                continue
            R = np.array([td.vertex(a)[0] for a in arms])
            P = np.array([td.vertex(a)[1] for a in arms])
            h = Hull(R, P, U)
            ys = [h.best_at_cost(c, refine=False)["hill"] for c in cs]
            ys = [np.nan if y is None else y for y in ys]
            ls = "--" if cls in ("MINP", "VS") else "-"
            ax.plot(cs, ys, color=col, lw=1.6 if cls == "PN" else 1.0, ls=ls, label=cls)
            for a, c in zip(arms[1:], h.cost_v[1:]):
                k = kr.get((t, a))
                if k and k.get("hill25_step0") is not None:
                    lo, hi = k["ci90"] if k["ci90"] and k["ci90"][0] is not None else (None, None)
                    ax.plot([c], [k["hill25_step0"]], "o", color=col, ms=3)
                    if lo is not None:
                        ax.plot([c, c], [lo, hi], color=col, lw=0.6)
        ax.axvline(5, color="0.5", lw=0.7, ls=":")
        for y in (1.5, 2.0):
            ax.axhline(y, color="0.7", lw=0.6, ls=":")
        ax.set_xlim(-5, 45)
        ax.set_title(f"{t} (default {DEFAULT[t]})")
    for ax in axes[1]:
        ax.set_xlabel("pass cost (points; vertices above 45 not shown)")
    axes[0, 0].set_ylabel("correct-only Hill-1 (depth 25)")
    axes[1, 0].set_ylabel("correct-only Hill-1 (depth 25)")
    hl = {}
    for ax in axes.ravel():
        for h_, l_ in zip(*ax.get_legend_handles_labels()):
            hl.setdefault(l_, h_)
    fig.legend(list(hl.values()), list(hl.keys()), loc="lower center", ncol=6, frameon=False,
               bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("Fig. 1  Randomisation-hull frontier (max Hill at cost <= c) of every knob class; points: arm "
                 "vertices with 90% CIs (dashed: sensitivity knobs)")
    fig.tight_layout(rect=(0, 0.06, 1, 0.97))
    save(fig, "fig1_hill_vs_cost")


def fig2(T) -> None:
    arms = ["TWIN", "PN_a1", "PN_a2", "T1.6", "NOVELTY"]
    fig, axes = plt.subplots(2, 3, figsize=(13, 7.5))
    for ax, t in zip(axes.ravel(), E6):
        labs = sorted({r["label"] for a in arms for r in T[t].get(a, []) if r.get("passed") and r["label"] != "invalid"})
        cols = {l: OKABE[i % len(OKABE)] for i, l in enumerate(labs)}
        for i, a in enumerate(arms):
            rs = T[t].get(a, [])
            if not rs:
                continue
            n = len(rs)
            left = 0.0
            cc = Counter(r["label"] for r in rs if r.get("passed") and r["label"] != "invalid")
            for l in labs:
                w = cc.get(l, 0) / n
                ax.barh(i, w, left=left, color=cols[l], edgecolor="white", lw=0.3,
                        label=l if i == 0 or l not in [x.get_label() for x in ax.patches] else None)
                left += w
            inv = sum(r["label"] == "invalid" for r in rs) / n
            fail = 1 - left - inv
            ax.barh(i, fail, left=left, color="0.85", edgecolor="white", lw=0.3)
            ax.barh(i, inv, left=left + fail, color="0.55", edgecolor="white", lw=0.3)
        ax.set_yticks(range(len(arms)))
        ax.set_yticklabels(arms)
        ax.set_xlim(0, 1)
        ax.set_title(t)
        handles = [plt.Rectangle((0, 0), 1, 1, color=cols[l]) for l in labs] + \
            [plt.Rectangle((0, 0), 1, 1, color="0.85"), plt.Rectangle((0, 0), 1, 1, color="0.55")]
        ax.legend(handles, labs + ["failing", "invalid"], fontsize=6.5, frameon=False, loc="upper center",
                  bbox_to_anchor=(0.5, -0.08), ncol=4)
    fig.suptitle("Fig. 2  Correct compositions (share of N = 50), failing and invalid shares")
    fig.tight_layout(rect=(0, 0, 1, 0.96), h_pad=3.0, w_pad=2.0)
    save(fig, "fig2_compositions")


def fig3() -> None:
    sw = read_json(RESULTS_DIR / "alpha_sweep.json")
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.4))
    for i, t in enumerate(E6):
        if t not in sw:
            continue
        rows = sw[t]["sweep"]
        al = [r["alpha"] for r in rows]
        x = [a if a > 0 else 0.25 for a in al]
        axes[0].plot(x, [r["pass"] for r in rows], "o-", color=OKABE[i], label=t, ms=3)
        axes[1].plot(x, [r["off_default_share"] for r in rows], "o-", color=OKABE[i], ms=3)
        axes[2].plot(x, [r["hill25_step0"] for r in rows], "o-", color=OKABE[i], ms=3)
    for ax, yl in zip(axes, ("pass rate", "off-default share", "correct-only Hill-1")):
        ax.set_xscale("log", base=2)
        ax.set_xticks([0.25, 0.5, 1, 2, 4, 8])
        ax.set_xticklabels(["0", "0.5", "1", "2", "4", "8"])
        ax.set_xlabel("PN alpha (ban units)")
        ax.set_ylabel(yl)
    axes[0].legend(frameon=False, fontsize=7)
    fig.suptitle("Fig. 3  Dose-response of fresh per-sample plan noise (alpha 0 = TWIN)")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    save(fig, "fig3_alpha_dose_response")


def fig4() -> None:
    ip = read_json(RESULTS_DIR / "ideas_phrasings.json")["cells"]
    fig, axes = plt.subplots(2, 3, figsize=(11, 6))
    arms_c = {"TWIN": OKABE[8], "PN_a0.5": OKABE[3], "PN_a1": OKABE[3], "PN_a2": OKABE[3], "PN_a4": OKABE[3],
              "T1.3": OKABE[0], "T1.6": OKABE[0], "TOPK10": OKABE[5], "NONCE": OKABE[1], "NOVELTY": OKABE[4],
              "SEMSEED": OKABE[2], "MINP_T1.6": OKABE[7], "MINP_T2.0": OKABE[7], "VS": OKABE[11]}
    for ax, t in zip(axes.ravel(), E6):
        for a, col in arms_c.items():
            c = ip.get(f"{t}|{a}")
            if not c or "default_phrasings_theta0.8" not in c:
                continue
            ax.scatter(c["hill_ideas"], c["default_phrasings_theta0.8"], color=col, s=18)
            ax.annotate(a, (c["hill_ideas"], c["default_phrasings_theta0.8"]), fontsize=6)
        ax.set_title(t)
        ax.set_xlabel("ideas: correct-only Hill-1")
        ax.set_ylabel("phrasing clusters in the default idea\n(20 programs, Jaccard >= 0.8)")
    fig.suptitle("Fig. 4  Ideas vs phrasings per knob")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    save(fig, "fig4_ideas_vs_phrasings")


def fig5() -> None:
    ec = read_json(RESULTS_DIR / "engine_check.json")["cells"]
    fig, axes = plt.subplots(1, 4, figsize=(12, 3))
    for ax, (k, c) in zip(axes, ec.items()):
        labs = sorted(set(c["screen_composition"]) | set(c["this_run_composition"]))
        x = np.arange(len(labs))
        ax.bar(x - 0.2, [c["screen_composition"].get(l, 0) for l in labs], 0.4, color=OKABE[0], label="screen (exp17)")
        ax.bar(x + 0.2, [c["this_run_composition"].get(l, 0) for l in labs], 0.4, color=OKABE[1], label="this run")
        ax.set_xticks(x)
        ax.set_xticklabels(labs, rotation=30, ha="right", fontsize=7)
        ax.set_title(f"{k}\nper-slot agreement {c['per_slot_label_agreement']:.2f}, JSD {c['JSD']:.3f}", fontsize=8)
    axes[0].legend(frameon=False, fontsize=7)
    fig.suptitle("Fig. 5  Engine check: two screen rows reproduced with the screen's own CRN keys")
    save(fig, "fig5_engine_check")


def fig6() -> None:
    c1 = read_json(RESULTS_DIR / "c1.json")["primary"]
    per = c1["per_task"]
    ts = [t for t in E6 if t in per and per[t].get("D_t") is not None]
    fig, ax = plt.subplots(figsize=(6, 3.6))
    for i, t in enumerate(ts):
        d = per[t]
        lo, hi = d["D_t_boot_ci95"]
        ax.plot([lo, hi], [i, i], color=OKABE[0], lw=1.2)
        ax.plot([d["D_t"]], [i], "o", color=OKABE[0])
        ax.annotate(f"best NA: {d['best_na']}", (hi, i), fontsize=7, xytext=(4, -3), textcoords="offset points")
    lo, hi = c1["D_bar_ci95"]
    ax.plot([lo, hi], [len(ts), len(ts)], color=OKABE[3], lw=2)
    ax.plot([c1["D_bar"]], [len(ts)], "D", color=OKABE[3])
    ax.axvline(0, color="0.5", lw=0.7, ls=":")
    ax.set_yticks(range(len(ts) + 1))
    ax.set_yticklabels(ts + ["pooled D_bar"])
    ax.set_xlabel("D_t = H5(PN) - max over NA knobs of H5 (95% bootstrap CI)")
    ax.set_title(f"Fig. 6  C1: {c1['verdict']} (count1 {c1['count1']}, count2 {c1['count2']})")
    save(fig, "fig6_forest_Dt")


def main() -> None:
    setup_logging("figures")
    samples = read_jsonl(DATA_DIR / "samples.jsonl")
    reused = read_jsonl(DATA_DIR / "reused_rows.jsonl")
    T = defaultdict(lambda: defaultdict(list))
    for r in samples:
        T[r["task"]][r["arm"]].append(r)
    for f, args in ((fig1, (samples, reused)), (fig2, (T,)), (fig3, ()), (fig4, ()), (fig5, ()), (fig6, ())):
        try:
            f(*args)
        except Exception as e:  # noqa: BLE001 - one failing figure must not stop the others
            logger.exception(f"{f.__name__} failed: {e}")


if __name__ == "__main__":
    main()
