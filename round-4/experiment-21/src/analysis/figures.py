#!/usr/bin/env python3
"""A10 figures (matplotlib, PDF + PNG, Type-42 fonts). Rendered directly from the analysis dictionaries so the drawing
cannot disagree with the numbers in results/*.json.
F1 coupling map per task; F2 Hill-1 vs PPI per condition; F3 changed-seed counts T vs PN; F4 thinking on per seed;
F5 theta sweep of the PPI slopes."""

from __future__ import annotations

from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

import core  # noqa: E402
from cfg import FIG_DIR  # noqa: E402
from cfg4 import PN_SEEDS, TEMPS, cond_nopn, cond_pn, fmt_t  # noqa: E402

plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False})
PALETTE = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3", "#937860", "#DA8BC3", "#8C8C8C", "#CCB974",
           "#64B5CD"]
TASKS = ("T2", "T03", "T1")
SEEDS = core.seeds_of()


def _save(fig: Any, name: str) -> None:
    FIG_DIR.mkdir(exist_ok=True)
    fig.savefig(FIG_DIR / f"{name}.png", dpi=180, bbox_inches="tight")
    fig.savefig(FIG_DIR / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def f1_coupling(idx: dict) -> None:
    arms = [cond_nopn(t) for t in TEMPS] + ["TOPK10_T0.7"] + [cond_pn(d, 1.0, 1.0) for d in PN_SEEDS] + \
        [cond_pn(d, 2.0, 1.0) for d in PN_SEEDS]
    short = [f"T{fmt_t(t)}" for t in TEMPS] + ["k10"] + [f"D{i + 1}a1" for i in range(6)] + [f"D{i + 1}a2" for i in range(6)]
    fig, axes = plt.subplots(1, 3, figsize=(14, 5.2))
    for ax, task in zip(axes, TASKS):
        labs = sorted({core.label_value(idx.get((task, s, a))) or "invalid/none" for s in SEEDS for a in arms})
        cmap = {l: PALETTE[i % len(PALETTE)] for i, l in enumerate(labs)}
        cmap["invalid/none"] = "#E5E5E5"
        for i, s in enumerate(SEEDS):
            for j, a in enumerate(arms):
                r = idx.get((task, s, a))
                l = core.label_value(r) or "invalid/none"
                ax.add_patch(plt.Rectangle((j, i), 1, 1, facecolor=cmap[l], edgecolor="white", lw=0.5,
                                           hatch="///" if (r and not r.get("passed")) else None))
        ax.set_xlim(0, len(arms))
        ax.set_ylim(0, len(SEEDS))
        ax.invert_yaxis()
        ax.set_xticks(np.arange(len(arms)) + 0.5, short, rotation=90, fontsize=7)
        ax.set_yticks(np.arange(len(SEEDS)) + 0.5, SEEDS, fontsize=6)
        ax.axvline(4, color="k", lw=1)
        ax.axvline(5, color="k", lw=1)
        ax.set_title(f"{task}: seeds x conditions (T = 1.0 for PN)")
        ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=cmap[l]) for l in labs], labels=labs, fontsize=6,
                  loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, frameon=False)
    fig.suptitle("F1 coupling map: one row = one token seed (same noise stream in every column); hatch = failed tests")
    _save(fig, "F1_coupling_map")


def f2_hill_ppi(tab: list[dict[str, Any]]) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    for ax, task in zip(axes, TASKS):
        rows = {r["condition"]: r for r in tab if r["task"] == task}

        def xy(c):
            r = rows.get(c)
            if not r:
                return None
            h = r.get("hill1_correct", r.get("hill1_correct_rarefied20"))
            if h is None:
                h = r.get("hill1_correct_rarefied20")
            pp = (r.get("ppi_rarefied20") or r["ppi"]).get("0.8")
            return (pp, h)
        pts = [(f"T{fmt_t(t)}", xy(cond_nopn(t))) for t in TEMPS]
        prev = None
        for name, p in pts:
            if p and p[0] is not None and p[1] is not None:
                ax.scatter(*p, color="#4C72B0")
                ax.annotate(name, p, fontsize=7, xytext=(3, 3), textcoords="offset points")
                if prev:
                    ax.annotate("", xy=p, xytext=prev, arrowprops=dict(arrowstyle="->", color="#4C72B0"))
                prev = p
        for a, col in ((1.0, "#C44E52"), (2.0, "#8172B3")):
            for t in (0.7, 1.0):
                p = xy(f"PN_a{a:.1f}_T{fmt_t(t)}")
                b = xy(cond_nopn(t))
                if p and b and None not in p and None not in b:
                    ax.scatter(*p, color=col, marker="s")
                    ax.annotate(f"PN a{a:g} T{t:g}", p, fontsize=7, xytext=(3, -8), textcoords="offset points")
                    ax.annotate("", xy=p, xytext=b, arrowprops=dict(arrowstyle="->", color=col, ls="--"))
        ax.set_xlabel("phrasings per idea (PPI, theta 0.8; PN rarefied to 20)")
        ax.set_ylabel("Hill-1 of correct ideas (depth 20)")
        ax.set_title(task)
    fig.suptitle("F2 ideas (Hill-1) vs phrasings (PPI): arrows along T (blue) and along plan noise (dashed)")
    _save(fig, "F2_hill_vs_ppi")


def f3_counts(res: dict[str, Any]) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8), sharey=True)
    for ax, task in zip(axes, TASKS):
        a1 = res["A1_C_T_off"][task]["primary"]
        names, vals, lo, hi = ["C_T (4 T)"], [a1["C_T"]], [0], [0]
        for key, v in res["A2_C_PN"][task].items():
            names.append(f"C_PN {key}")
            vals.append(v["C_PN"])
            lo.append(v["C_PN"] - (v["min"] or 0))
            hi.append((v["max"] or 0) - v["C_PN"])
        x = np.arange(len(names))
        ax.bar(x, vals, color=["#8C8C8C"] + ["#C44E52"] * (len(names) - 1))
        ax.errorbar(x, vals, yerr=[[max(0.0, v) for v in lo], [max(0.0, v) for v in hi]], fmt="none", ecolor="k",
                    capsize=3, lw=1)
        n = a1["n_countable"]
        cp = a1["cp95_rate"]["cp95"]
        ax.errorbar([0], [a1["C_T"]], yerr=[[0], [max(0.0, cp[1] * n - a1["C_T"])]], fmt="none", ecolor="#4C72B0",
                    capsize=5)
        ax.axhline(5, ls=":", color="k", lw=0.8)
        ax.set_xticks(x, names, rotation=60, ha="right", fontsize=7)
        ax.set_title(f"{task} (n = {n} seeds)")
        ax.set_ylabel("seeds whose idea changed (of 20)")
    fig.suptitle("F3 changed-seed counts: temperature (C_T, CP 95% upper bound) vs plan noise (C_PN, 20-subset range)")
    _save(fig, "F3_changed_seed_counts")


def f4_thinking(th: dict[str, Any], raw: list[dict[str, Any]]) -> None:
    if not th.get("available"):
        return
    arms = [f"THINK_T{fmt_t(t)}" for t in TEMPS] + ["THINK_REP_T0.7"]
    by = {(r["arm"], f"{r['template']}|{r['sample_id']}"): r for r in raw if r["task"] == "T2"}
    M = np.full((len(SEEDS), len(arms)), np.nan)
    fig, axes = plt.subplots(1, 2, figsize=(12, 6), gridspec_kw={"width_ratios": [2, 1]})
    ax = axes[0]
    for i, s in enumerate(SEEDS):
        for j, a in enumerate(arms):
            r = by.get((a, s))
            if r:
                M[i, j] = r["n_think_tokens"]
    im = ax.imshow(M, aspect="auto", cmap="viridis")
    for i, s in enumerate(SEEDS):
        for j, a in enumerate(arms):
            r = by.get((a, s))
            if r:
                txt = (r.get("first_approach") or "-")[:4] + ("" if r["completed"] else "*")
                ax.text(j, i, txt, ha="center", va="center", fontsize=6, color="w")
    ax.set_xticks(range(len(arms)), [a.replace("THINK_", "") for a in arms], fontsize=7)
    ax.set_yticks(range(len(SEEDS)), SEEDS, fontsize=6)
    fig.colorbar(im, ax=ax, label="thinking tokens")
    ax.set_title("thinking length per seed (text = first approach named; * = not completed)")
    ax2 = axes[1]
    pt = th["per_T"]
    xs = [a for a in arms if a in pt]
    ax2.bar(range(len(xs)), [pt[a]["completion_rate"] for a in xs], color="#55A868")
    for k, a in enumerate(xs):
        lo, hi = pt[a]["wilson95"]
        ax2.errorbar([k], [pt[a]["completion_rate"]], yerr=[[max(0.0, pt[a]["completion_rate"] - lo)],
                                                           [max(0.0, hi - pt[a]["completion_rate"])]], fmt="none",
                     ecolor="k")
    ax2.set_xticks(range(len(xs)), [a.replace("THINK_", "") for a in xs], fontsize=7, rotation=45)
    ax2.set_ylim(0, 1.05)
    ax2.set_title("completion within the 16k cap (Wilson 95%)")
    fig.suptitle("F4 thinking on (T2, vLLM, Gumbel-max coupling)")
    _save(fig, "F4_thinking_on")


def f5_theta(phr: dict[str, Any]) -> None:
    fig, ax = plt.subplots(figsize=(6, 3.8))
    th = [float(t) for t in phr["pooled"]]
    for k, task in enumerate(TASKS):
        v = phr["per_task"][task]["theta"]
        ys = [v[str(t)]["slope"] for t in th]
        lo = [max(0.0, v[str(t)]["slope"] - v[str(t)]["ci95"][0]) for t in th]   # percentile CIs need not
        hi = [max(0.0, v[str(t)]["ci95"][1] - v[str(t)]["slope"]) for t in th]   # contain the point estimate
        ax.errorbar(np.array(th) + (k - 1) * 0.008, ys, yerr=[lo, hi], marker="o", capsize=3, label=task)
    ys = [phr["pooled"][str(t)]["slope"] for t in th]
    ax.plot(th, ys, "k--", marker="D", label="pooled")
    ax.axhline(0, color="grey", lw=0.8)
    ax.set_xlabel("Jaccard threshold theta")
    ax.set_ylabel("slope of log PPI on T")
    ax.legend(frameon=False, fontsize=8)
    ax.set_title("F5 theta sweep: phrasings per idea grow with temperature")
    _save(fig, "F5_theta_sweep")


def make_figures(rows: list[dict[str, Any]], idx: dict, res: dict[str, Any], phr: dict[str, Any],
                 th: dict[str, Any], tab: list[dict[str, Any]]) -> None:
    from cfg import DATA_DIR, read_jsonl

    for name, fn in (("F1", lambda: f1_coupling(idx)), ("F2", lambda: f2_hill_ppi(tab)), ("F3", lambda: f3_counts(res)),
                     ("F4", lambda: f4_thinking(th, read_jsonl(DATA_DIR / "raw_thinking.jsonl"))),
                     ("F5", lambda: f5_theta(phr))):
        try:
            fn()
            logger.info(f"figure {name} written")
        except Exception as e:  # noqa: BLE001
            logger.exception(f"figure {name} failed: {e}")
