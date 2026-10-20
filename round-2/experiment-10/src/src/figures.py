#!/usr/bin/env python3
"""S6.13 figures (aii-data-fig-gen house style). Generator specs where a catalogue type fits (stacked_pct, heatmap,
hist, bar); hand-written matplotlib with the skill's fitters where the figure needs a masked diagonal, asymmetric
bootstrap intervals or reference lines. Every figure is drawn from results/*.json (PDF + PNG in figures/)."""

from __future__ import annotations

import json
import subprocess
import sys
import warnings
from pathlib import Path

import numpy as np
from loguru import logger

from src.ws import FIGS, RESULTS, setup_logging, skills_dir

SKILL = skills_dir() / "aii-data-fig-gen" / "scripts"
sys.path.insert(0, str(SKILL))
LABEL_ORDER = {"t1": ["bfs", "dfs", "bibfs", "iddfs", "astar_gbfs", "dijkstra", "other"],
               "t2": ["dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial", "other"]}
TNAME = {"t1": "T1 grid path", "t2": "T2 weighted shortest path"}


def load(name: str):
    return json.loads((RESULTS / name).read_text())


def gen(spec: dict, name: str) -> None:
    p = FIGS / f"{name}.json"
    p.write_text(json.dumps(spec, indent=1))
    r = subprocess.run([sys.executable, str(SKILL / "chart_gen.py"), "--spec", str(p), "--out", str(FIGS / name)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{name}: {r.stderr[-800:]}")
    logger.info(f"figure {name} written")


def hand(name: str, draw) -> None:
    import matplotlib.pyplot as plt
    from chart_geometry import assert_text_is_legible
    from chart_style import apply_house_style, clear_legends_of_data, fit_legends, fit_tick_labels, fit_titles

    apply_house_style()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fig = draw(plt)
        fit_legends(fig)
        clear_legends_of_data(fig)
        fit_tick_labels(fig)
        fit_titles(fig)
        clear_legends_of_data(fig)
        try:
            assert_text_is_legible(fig)
        except AssertionError as e:  # report, still save (layout was already constrained)
            logger.warning(f"{name}: legibility check: {e}")
        fig.savefig(FIGS / f"{name}.pdf")
        fig.savefig(FIGS / f"{name}.png", dpi=200)
        plt.close(fig)
    logger.info(f"figure {name} written")


SHORT = {"bfs": "BFS", "dfs": "DFS", "bibfs": "biBFS", "iddfs": "IDDFS", "astar_gbfs": "A*", "dijkstra": "Dijkstra",
         "bf_spfa": "BF/SPFA", "bidijkstra": "biDijkstra", "floyd": "Floyd", "dial": "Dial", "other": "other"}


def short_event(name: str) -> str:
    base = name.split(" (")[0]
    if base == "baseline" or base == "listall":
        return base
    kind, x = base.split(":", 1)
    xs = "+".join(SHORT[p] for p in x.split("+"))
    return {"ban": "ban ", "mention": "mention ", "twostep": "ban "}[kind] + xs + ("*" if "(modal)" in name else "")


def fig_landing() -> None:
    ev = load("events.json")
    for t, tag in (("t1", "fig1a_landing_t1"), ("t2", "fig1b_landing_t2")):
        cats = [short_event(e["name"]) for e in ev[t]]
        labs = [l for l in LABEL_ORDER[t] if any(e["attempted_counts"].get(l, 0) for e in ev[t])]
        series = [{"label": SHORT[l], "values": [float(e["attempted_counts"].get(l, 0)) for e in ev[t]]} for l in labs]
        gen({"type": "stacked_pct", "title": f"{TNAME[t]}: mechanism labels of attempted programs per sampled event",
             "xlabel": "Sampled event (* = modal ban)", "ylabel": "Share of attempted programs (%)", "categories": cats,
             "series": series, "aspect": "16:9"}, tag)


def fig_landing_wilson() -> None:
    """Landing bars per event with Wilson 95% intervals (share of attempted programs), the main labels per task."""
    ev = load("events.json")
    for t, tag, labs in (("t1", "fig1c_landing_wilson_t1", ["bfs", "dfs", "other"]),
                         ("t2", "fig1d_landing_wilson_t2", ["dijkstra", "bf_spfa", "other"])):
        es = ev[t]

        def draw(plt, es=es, labs=labs, t=t):
            fig, ax = plt.subplots(figsize=(6.5, 3.6), layout="constrained")
            n_ev = len(es)
            width = 0.8 / len(labs)
            for k, l in enumerate(labs):
                x = np.arange(n_ev) + (k - (len(labs) - 1) / 2) * width
                att = [sum(e["attempted_counts"].values()) for e in es]
                p_ = [e["attempted_counts"].get(l, 0) / max(1, a) for e, a in zip(es, att)]
                lo = [e["landing_wilson"].get(l, [0.0, 0.0])[0] if l in e["landing_wilson"] else 0.0 for e in es]
                hi = [e["landing_wilson"].get(l, [0.0, 0.0])[1] if l in e["landing_wilson"] else 0.0 for e in es]
                err = np.clip(np.array([np.array(p_) - lo, np.array(hi) - p_]), 0, None)
                ax.bar(x, p_, width=width * 0.95, yerr=err, capsize=2, label=SHORT[l])
            ax.set_xticks(range(n_ev), [short_event(e["name"]) for e in es])
            ax.set_ylabel("share of attempted programs")
            ax.set_ylim(0, 1.05)
            ax.set_title(f"{TNAME[t]}: landing per sampled event (Wilson 95% CI)")
            from chart_style import place_legend
            place_legend(ax, loc="upper right")
            return fig

        hand(tag, draw)


def fig_gbar() -> None:
    c1 = load("c1.json")
    rows = c1["c1"]["neutral"]["per_task"]["t1"]["rows"]
    if not rows:
        return
    algs = [r["X"] for r in rows]
    allj = sorted({j for r in rows for j in r["survivors"]} | set(algs), key=lambda j: LABEL_ORDER["t1"].index(j))
    M = np.full((len(rows), len(allj)), np.nan)
    for i, r in enumerate(rows):
        for j, g in zip(r["survivors"], r["gbar"]):
            M[i, allj.index(j)] = g

    from src import analysis_c1 as A
    from src import run_analysis as RA

    td = RA.load_task("t1")
    u = A.View(td, RA.variant_cells(td, "full")).u()
    uvec = np.array([u[td.algs.index(j)] for j in allj])

    def draw(plt):
        fig, (ax, ax2) = plt.subplots(2, 1, figsize=(6.5, 4.8), layout="constrained", height_ratios=[6, 1.25])
        vmax = np.nanmax(np.abs(M))
        im = ax.imshow(np.ma.masked_invalid(M), cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")
        for i in range(M.shape[0]):
            for j in range(M.shape[1]):
                if not np.isnan(M[i, j]):
                    ax.text(j, i, f"{M[i, j]:.1f}", ha="center", va="center", fontsize=8,
                            color="white" if abs(M[i, j]) > 0.6 * vmax else "black")
        ax.set_xticks(range(len(allj)), allj)
        ax.set_yticks(range(len(rows)), [f"ban {a}" for a in algs])
        ax.set_xlabel("Survivor algorithm j")
        ax.set_title("T1: centred, ESS-weighted mean gain vs neutral twin (nats)")
        fig.colorbar(im, ax=ax, label="centred gain (nats)")
        um = np.max(np.abs(uvec))
        im2 = ax2.imshow(uvec[None, :], cmap="RdBu_r", vmin=-um, vmax=um, aspect="auto")
        for j in range(len(allj)):
            ax2.text(j, 0, f"{uvec[j]:.2f}", ha="center", va="center", fontsize=8,
                     color="white" if abs(uvec[j]) > 0.6 * um else "black")
        ax2.set_xticks(range(len(allj)), allj)
        ax2.set_yticks([0], ["u (ladder)"])
        fig.colorbar(im2, ax=ax2, label="u (unit-free)")
        return fig

    hand("fig2_gain_heatmap_t1", draw)


def fig_components() -> None:
    c1 = load("c1.json")
    br = c1["branches"]

    def draw(plt):
        fig, ax = plt.subplots(figsize=(6.5, 3.4), layout="constrained")
        comps = ["V_u", "V_s", "V_tot"]
        for k, ref in enumerate(("neutral", "mention")):
            b = br[ref]["pooled"]
            if "V_u" not in b:
                continue
            vals = [b["V_u"], b["V_s"], b["V_tot"]]
            cis = [b["V_u_ci95"], b["V_s_ci95"], b["V_tot_ci95"]]
            x = np.arange(3) + (k - 0.5) * 0.36
            ax.bar(x, vals, width=0.34, label=f"{ref} reference", alpha=0.85)
            # percentile interval drawn as its own segment: for these quadratic statistics it can lie above the point
            ax.vlines(x, [c[0] for c in cis], [c[1] for c in cis], color="black", lw=1.6)
            ax.hlines([c[0] for c in cis] + [c[1] for c in cis], np.r_[x, x] - 0.06, np.r_[x, x] + 0.06, color="black", lw=1.6)
        ax.axhline(0, color="black", lw=0.8)
        ax.set_xticks(range(3), ["V_u (ladder)", "V_s (X-specific)", "V_tot"])
        ax.set_ylabel("noise-corrected variance (nats²)")
        ax.set_title("C1 components, pooled (bars: point; segments: 95% percentile bootstrap CI)")
        from chart_style import place_legend
        place_legend(ax, loc="upper left")
        return fig

    hand("fig3_c1_components", draw)


def fig_aim_null() -> None:
    nl = load("aim_null_pooled.json")
    if not nl.get("support"):
        return
    sup, pmf = np.array(nl["support"]), np.array(nl["pmf"])

    def draw(plt):
        fig, ax = plt.subplots(figsize=(6.5, 3.2), layout="constrained")
        ax.bar(sup, pmf, width=(sup[1] - sup[0]) if len(sup) > 1 else 0.01, color="0.6", label="exact permutation null")
        ax.axvline(nl["observed"], color="C3", lw=2, label=f"observed AIM = {nl['observed']:.3f}")
        ax.axvline(nl["q95"], color="black", ls="--", lw=1, label=f"null 95th pct = {nl['q95']:.3f}")
        ax.set_xlabel("mean split-half Spearman (s vs prime-and-veto)")
        ax.set_ylabel("probability")
        ax.set_title("AIM against its exact within-row survivor-permutation null")
        from chart_style import place_legend
        place_legend(ax, loc="best")
        return fig

    hand("fig4_aim_null", draw)


def fig_implied_vs_sampled() -> None:
    g = load("frlp_gate.json")
    ev = {(e["task"], e["name"]): e for t, es in load("events.json").items() for e in es}
    xs, ys, lab = [], [], []
    for c in g["c_events"]:
        if "template_mean_L" not in c:
            continue
        e = ev[(c["task"], c["event"])]
        L = np.array(list(c["template_mean_L"].values()))
        sm = np.exp(L - L.max())
        sm /= sm.sum()
        nb = sum(e["nonbanned_counts"].values())
        for j, q in zip(c["template_mean_L"], sm):
            xs.append(e["nonbanned_counts"].get(j, 0) / max(1, nb))
            ys.append(float(q))
            lab.append(f"{c['task']}:{c['event']}:{j}")

    def draw(plt):
        fig, ax = plt.subplots(figsize=(5.0, 4.4), layout="constrained")
        ax.plot([0, 1], [0, 1], color="0.5", ls="--", lw=1, label="y = x")
        ax.scatter(xs, ys, s=22, alpha=0.8, label="(event, algorithm)")
        ax.set_xlabel("sampled share among attempted non-banned")
        ax.set_ylabel("FRLP-implied share (template mean)")
        ax.set_title("FRLP-implied vs sampled landing (clear-mode events)")
        from chart_style import place_legend
        place_legend(ax, loc="upper left")
        return fig

    hand("fig5_frlp_implied_vs_sampled", draw)


def fig_cosine() -> None:
    c1 = load("c1.json")
    cos = c1["cosine"]["t1"]["pairwise"]
    if not cos:
        return
    names = sorted({k.split("|")[0] for k in cos} | {k.split("|")[1] for k in cos}, key=lambda j: LABEL_ORDER["t1"].index(j))
    M = [[1.0 if a == b else float(cos.get(f"{a}|{b}", cos.get(f"{b}|{a}"))) for b in names] for a in names]
    gen({"type": "heatmap", "title": "T1: cosine between ban gain profiles (shared survivors)", "xlabel": "ban",
         "ylabel": "ban", "cbar_label": "cosine", "row_labels": names, "col_labels": names, "matrix": M,
         "vmin": -1.0, "vmax": 1.0, "aspect": "4:3"}, "fig6_ban_cosine_t1")


def fig_ess() -> None:
    from src.ws import FRLP_DIR, read_jsonl

    cl = [r["ess"] for r in read_jsonl(FRLP_DIR / "cells.jsonl") if r["variant"] == "full"]
    gen({"type": "hist", "title": "Importance-weight ESS per FRLP cell (primary variant)", "xlabel": "ESS",
         "ylabel": "cells", "bins": 30, "aspect": "16:9", "series": [{"values": [float(x) for x in cl]}]}, "fig7_ess_hist")


def fig_route() -> None:
    c1 = load("c1.json")
    rt = c1.get("route")
    if not rt:
        return
    gen({"type": "bar", "title": "Route test (FRLP-only): own-drop of the modal ban by arm", "xlabel": "arm",
         "ylabel": "sum of D_X over templates x halves (nats)", "aspect": "16:9",
         "categories": ["a: full ban", "c: prompt route", "d: direct route"],
         "series": [{"values": [rt["sum_D_a"], rt["sum_D_c"], rt["sum_D_d"]]}]}, "fig8_route")


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("figures")
    FIGS.mkdir(exist_ok=True)
    for f in (fig_landing, fig_landing_wilson, fig_gbar, fig_components, fig_aim_null, fig_implied_vs_sampled, fig_cosine, fig_ess, fig_route):
        try:
            f()
        except (RuntimeError, KeyError, ValueError, TypeError, IndexError, FileNotFoundError) as e:
            logger.error(f"{f.__name__} failed: {e}")


if __name__ == "__main__":
    main()
