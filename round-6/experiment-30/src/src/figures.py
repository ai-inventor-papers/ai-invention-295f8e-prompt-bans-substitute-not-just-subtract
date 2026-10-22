#!/usr/bin/env python3
"""STEP 10 figures (figures/*.pdf + .png) in the aii-data-fig-gen house style (hand-written matplotlib with its
chart_style helpers). Every number is read from results/*.json, so a figure cannot disagree with the analysis."""

from __future__ import annotations

import os

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):  # 5-CPU cgroup: avoid BLAS oversubscription
    os.environ.setdefault(_v, "2")

import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

from cfg import FIG_DIR, PRED_DIR, RESULTS_DIR, read_json, setup_logging

SKILL = Path(os.environ.get("AII_DATA_FIG_GEN_SCRIPTS", str(Path.home() / ".claude/skills/aii-data-fig-gen/scripts")))
if SKILL.exists():
    sys.path.insert(0, str(SKILL))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

try:
    from chart_style import (PALETTE, apply_house_style, clear_legends_of_data, fit_legends,  # noqa: E402
                             fit_tick_labels, fit_titles, place_legend)
    HOUSE = True
except Exception:  # noqa: BLE001 - fall back to plain matplotlib
    HOUSE = False
    PALETTE = ["#0173b2", "#de8f05", "#029e73", "#d55e00", "#cc78bc", "#ca9161", "#fbafe4", "#949494"]

SITE_ORDER = ["S0", "S4", "S5", "S1", "S2", "S3", "S1E"]
SITE_NAME = {"S0": "S0 spec 12-23", "S4": "S4 spec 0-11", "S5": "S5 spec 24-35", "S1": "S1 read pos.",
             "S2": "S2 condition", "S3": "S3 gen. tokens", "S1E": "S1E read (energy)"}


def _style() -> None:
    if HOUSE:
        apply_house_style()


def _finish(fig, name: str) -> None:
    if HOUSE:
        for f in (fit_legends, clear_legends_of_data, fit_tick_labels, fit_titles, clear_legends_of_data):
            try:
                f(fig)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"{name}: {f.__name__} failed: {e}")
    for ext in ("pdf", "png"):
        fig.savefig(FIG_DIR / f"{name}.{ext}", dpi=200)
    plt.close(fig)
    logger.info(f"figure {name}")


def _legend(ax, **kw):
    if HOUSE:
        try:
            return place_legend(ax, **kw)
        except Exception:  # noqa: BLE001
            pass
    return ax.legend(**kw)


def fig1(cl: dict[str, Any]) -> None:
    tasks = ["T03", "T10", "T2"]
    fig, axes = plt.subplots(2, 3, figsize=(6.5, 4.6), layout="constrained", sharey="row")
    for j, t in enumerate(tasks):
        ax, ax2 = axes[0, j], axes[1, j]
        tw = cl.get(f"{t}|TWIN")
        alphas = [1.0, 2.0, 4.0] if t != "T2" else [2.0, 4.0]
        width = 0.8 / len(SITE_ORDER)
        for i, s in enumerate(SITE_ORDER):
            xs, ys, lo, hi, ps = [], [], [], [], []
            for ai, a in enumerate(alphas):
                c = cl.get(f"{t}|{s}_a{a:g}")
                if not c:
                    continue
                xs.append(ai + (i - len(SITE_ORDER) / 2 + 0.5) * width)
                ys.append(c["share_correct_off_default"])
                lo.append(c["share_correct_off_default"] - c["share_ci"][0])
                hi.append(c["share_ci"][1] - c["share_correct_off_default"])
                ps.append(c["pass"])
            if xs:
                lo = list(np.maximum(0.0, lo))
                hi = list(np.maximum(0.0, hi))
                ax.bar(xs, ys, width=width, yerr=[lo, hi], color=PALETTE[i % len(PALETTE)],
                       label=s if j == 0 else None, error_kw={"lw": 0.6, "capsize": 1.5})
                ax2.plot(xs, ps, "o", ms=3, color=PALETTE[i % len(PALETTE)])
        if tw:
            ax.axhline(tw["share_correct_off_default"], color="k", lw=0.8, ls="--")
            ax2.axhline(tw["pass"], color="k", lw=0.8, ls="--")
            ax2.axhline(0.8 * tw["pass"], color="grey", lw=0.6, ls=":")
        for a_ in (ax, ax2):
            a_.set_xticks(range(len(alphas)))
            a_.set_xticklabels([f"α {a:g}" for a in alphas])
        ax.set_title(t)
        ax2.set_ylim(-0.02, 1.05)
    axes[0, 0].set_ylabel("correct off-default share")
    axes[1, 0].set_ylabel("pass rate")
    fig.legend(*axes[0, 0].get_legend_handles_labels(), loc="outside lower center", ncols=7, fontsize=7)
    _finish(fig, "fig1_sites_share_pass")


def fig2(sa: dict[str, Any]) -> None:
    tasks = [t for t in ("T03", "T10") if sa["tasks"].get(t)]
    fig, axes = plt.subplots(1, len(tasks), figsize=(6.5, 2.8), layout="constrained", squeeze=False)
    for j, t in enumerate(tasks):
        ax = axes[0, j]
        tr = sa["tasks"][t]
        sel = tr.get("selected")
        if not sel:
            ax.text(0.5, 0.5, "no gated S0/S4 cell", ha="center", transform=ax.transAxes)
            ax.set_title(t)
            continue
        a = sel["alpha"]
        comps = ["S1", "S2", "S5"]
        b = [tr["all_bc"].get(f"{sel['site']}_a{a:g}_vs_{c}", {}).get("b", 0) for c in comps]
        c_ = [tr["all_bc"].get(f"{sel['site']}_a{a:g}_vs_{c}", {}).get("c", 0) for c in comps]
        x = np.arange(len(comps))
        ax.bar(x - 0.2, b, 0.4, color=PALETTE[0], label=f"{sel['site']} only")
        ax.bar(x + 0.2, c_, 0.4, color=PALETTE[1], label="comparator only")
        for xi, (bb, cc, cp) in enumerate(zip(b, c_, comps)):
            p = tr["contrasts"].get(cp, {}).get("p_holm")
            ax.text(xi, max(bb, cc) + 0.4, f"Holm p={p:.2g}" if p is not None else "", ha="center", fontsize=7)
        ax.set_xticks(x)
        ax.set_xticklabels(comps)
        ax.set_title(f"{t}: {sel['site']} α {a:g} (paired slots)")
        ax.set_ylabel("discordant slots")
        _legend(ax, loc="upper right", fontsize=7)
    _finish(fig, "fig2_paired_flips")


def fig3(sb: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    import decide as D

    pr = [r for r in rows if r["task"] in ("T03", "T10", "T2") and r["site"] in ("S0", "S4", "S5", "S1", "S1E", "S2")
          and r.get("realised_disp", {}).get("disp_R35")]
    if not pr:
        return
    disp = np.array([r["realised_disp"]["disp_R35"] for r in pr])
    edges = np.quantile(disp, np.linspace(0, 1, 11))
    fig, ax = plt.subplots(figsize=(6.5, 3.4), layout="constrained")
    for i, s in enumerate(["S0", "S4", "S5", "S1", "S1E", "S2"]):
        xs, ys = [], []
        for d in range(10):
            m = [r for r in pr if r["site"] == s and edges[d] <= r["realised_disp"]["disp_R35"] <=
                 edges[d + 1] + (1e-9 if d == 9 else 0)]
            if len(m) >= 5:
                xs.append(np.sqrt(edges[d] * edges[d + 1]))
                ys.append(np.mean([D.y_of(r) for r in m]))
        if xs:
            ax.plot(xs, ys, "-o", ms=3, color=PALETTE[i], label=s)
    ax.set_xscale("log")
    ax.set_xlabel("realised displacement at R, block 35 (decile midpoint)")
    ax.set_ylabel("correct off-default share")
    mh = sb["primary"].get("mh", {})
    ax.set_title(f"S-b: MH OR {mh.get('or', float('nan')):.2f} [{mh.get('ci', [np.nan])[0]:.2f}, "
                 f"{mh.get('ci', [np.nan, np.nan])[1]:.2f}]")
    _legend(ax, loc="upper left", fontsize=7)
    _finish(fig, "fig3_sb_transmission")


def fig4(f1r: dict[str, Any]) -> None:
    ch = [p["d"] for p in f1r.get("pairs_change", [])]
    if not ch:
        return
    fig, ax = plt.subplots(figsize=(6.5, 3.0), layout="constrained")
    bins = np.arange(min(-4, min(ch)), min(max(ch) + 4, 400), 4)
    ax.hist(np.clip(ch, bins[0], bins[-1]), bins=bins, color=PALETTE[0], alpha=0.85, label="label-changing pairs")
    ax.axvline(32, color="k", ls="--", lw=0.8)
    ax.set_xlabel("first divergent code token after the opening fence line (d)")
    ax.set_ylabel("CRN pairs")
    dec = f1r["decision"]
    ax.set_title(f"F1: share d < 32 = {dec['share']:.2f} (n = {dec['n_label_changing_pairs']})")
    _legend(ax, loc="upper right", fontsize=7)
    _finish(fig, "fig4_f1_first_divergence")


def fig5(f2r: dict[str, Any]) -> None:
    ts = [t for t, v in f2r.items() if isinstance(v, dict) and v.get("m") is not None and t[:1] in ("T", "R")
          and "thinking" not in t]
    if not ts:
        return
    ts = sorted(ts, key=lambda t: f2r[t]["m"])
    fig, ax = plt.subplots(figsize=(6.5, 3.2), layout="constrained")
    vals = [f2r[t]["m"] for t in ts]
    err = [2 * (f2r[t].get("scoring_sd") or 0) for t in ts]
    cols = [PALETTE[3] if t in ("T2", "T03", "T1") else PALETTE[0] for t in ts]
    ax.bar(range(len(ts)), vals, yerr=err, color=cols, error_kw={"lw": 0.6, "capsize": 2})
    fk = [f2r[t].get("m_fork_median") for t in ts]
    ax.plot([i for i, v in enumerate(fk) if v is not None], [v for v in fk if v is not None], "k_", ms=14, mew=2,
            label="m at the fork token")
    ax.axhline(5.70, color="k", ls="--", lw=0.8)
    ax.set_xticks(range(len(ts)))
    ax.set_xticklabels(ts)
    ax.set_ylabel("twin margin m (nats, LP48)")
    ax.set_title("F2: default minus runner-up teacher-forced log-prob (same-seed tasks highlighted)")
    _legend(ax, loc="upper left", fontsize=7)
    _finish(fig, "fig5_f2_margin")


def fig6(sd: dict[str, Any], cl: dict[str, Any]) -> None:
    import geometry as G

    for key, tag in (("T03|TOP5", "a"), ("T1|TOP5", "b"), ("T10|TOP5", "c"), ("T03|TOP3", "d")):
        r = sd.get(key)
        if not r:
            continue
        t, site = key.split("|")
        for blk in (18, 23):
            g = r["geometry"].get(f"block{blk}")
            if not g:
                continue
            Y = np.array(g["embedding"]["points"])
            algs = np.array(g["embedding"]["core_algs"])
            meta = g["embedding"]["extra_meta"]
            nc = len(algs)
            names = g["centroid_names"]
            counts = G.implemented_counts(t) if t != "T1" else None
            panels = [("twin", None), ("base model", None), ("plan noise", None), ("top-five push", None)]
            fig, axes = plt.subplots(1, 4, figsize=(6.5, 2.4), layout="constrained", sharex=True, sharey=True)
            for pi, (pname, _) in enumerate(panels):
                ax = axes[pi]
                for ai, a in enumerate(names):
                    m = algs == a
                    ax.scatter(Y[:nc][m, 0], Y[:nc][m, 1], s=3, color=PALETTE[ai % len(PALETTE)], alpha=0.35,
                               label=a if pi == 0 else None)
                    cxy = Y[:nc][m].mean(0)
                    if counts is not None:
                        src = {"twin": ["twin_exp19_fp8", "twin_exp27_bf16", "twin_exp24_bf16"],
                               "base model": ["base_exp24_bf16"],
                               "plan noise": ["plan_noise_exp19_fp8", "plan_noise_exp27_bf16"]}.get(pname)
                        if src:
                            n = sum(counts["by_source"].get(s_, {}).get(a, 0) for s_ in src)
                        else:
                            n = sum((cl.get(f"{t}|{site}_a{al:g}", {}).get("composition_correct") or {}).get(a, 0)
                                    for al in (1.0, 2.0, 4.0))
                    else:
                        n = sum((cl.get(f"{t}|{site}_a{al:g}", {}).get("composition_correct") or {}).get(
                            {"astar_gbfs": "astar"}.get(a, a), 0) for al in (1.0, 2.0, 4.0)) if pname == \
                            "top-five push" else 10
                    ax.scatter([cxy[0]], [cxy[1]], s=10 + 2 * np.sqrt(max(n, 0)) * 8, facecolor="none",
                               edgecolor=PALETTE[ai % len(PALETTE)], lw=1.0)
                tw = [i for i, mm in enumerate(meta) if mm["kind"] == "twin"]
                ax.scatter(Y[nc + np.array(tw), 0], Y[nc + np.array(tw), 1], marker="*", s=30, color="k")
                if pname == "top-five push":
                    rc = [i for i, mm in enumerate(meta) if mm["kind"] == "random_control"]
                    if rc:
                        ax.scatter(Y[nc + np.array(rc), 0], Y[nc + np.array(rc), 1], s=4, color="grey", alpha=0.5)
                    for w_i in tw:
                        w = meta[w_i]["w"]
                        pts = [i for i, mm in enumerate(meta) if mm["kind"] == "push" and mm["w"] == w]
                        prev = Y[nc + w_i]
                        for i in sorted(pts, key=lambda i: meta[i]["alpha"]):
                            cur = Y[nc + i]
                            ax.annotate("", xy=cur, xytext=prev, arrowprops={"arrowstyle": "->", "lw": 0.6,
                                                                             "color": "k"})
                            prev = cur
                ax.set_title(pname, fontsize=8)
                ax.set_xticks([])
                ax.set_yticks([])
            fig.suptitle(f"{t} {site} block {blk}: MDS stress-1 {g['mds_stress1']:.3f}, k {g['k_used']}",
                         fontsize=9)
            fig.legend(*axes[0].get_legend_handles_labels(), loc="outside lower center", ncols=min(6, len(names)),
                       fontsize=6, markerscale=3)
            _finish(fig, f"fig6{tag}_sd_manifold_{t}_{site}_b{blk}")


def fig7(da: dict[str, Any], cl: dict[str, Any]) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(6.5, 2.8), layout="constrained", sharey=True)
    for j, t in enumerate(("T03", "T10", "T2")):
        ax = axes[j]
        for i, s in enumerate(["S0", "S4", "S5", "S1", "S2", "S1E"]):
            xs, ys = [], []
            for a in (1.0, 2.0, 4.0, 8.0):
                c = cl.get(f"{t}|{s}_a{a:g}")
                if c and c.get("dose_disp_over_h_mean_of_ratios"):
                    xs.append(c["dose_disp_over_h_mean_of_ratios"])
                    ys.append(c["share_correct_off_default"])
            if xs:
                ax.plot(xs, ys, "-o", ms=3, color=PALETTE[i], label=s if j == 0 else None)
        for a, v in (da.get(t, {}).get("S0_residual_fraction") or {}).items():
            ax.axvline(v, color="grey", ls=":", lw=0.6)
        ax.set_xscale("log")
        ax.set_title(t)
        ax.set_xlabel("realised ||d||/||h|| at the site")
    axes[0].set_ylabel("correct off-default share")
    fig.legend(*axes[0].get_legend_handles_labels(), loc="outside lower center", ncols=6, fontsize=7)
    _finish(fig, "fig7_dose_axis")


def main() -> None:
    from cfg import DATA_DIR, read_jsonl

    setup_logging("figures")
    _style()
    cl = read_json(RESULTS_DIR / "cells.json")
    rows = [r for r in read_jsonl(DATA_DIR / "samples.jsonl") if not str(r["arm"]).startswith(("SMOKE_", "ENG",
                                                                                                "TWIN_X"))]
    for name, fn in (("fig1", lambda: fig1(cl)), ("fig2", lambda: fig2(read_json(RESULTS_DIR / "s_a.json"))),
                     ("fig3", lambda: fig3(read_json(RESULTS_DIR / "s_b.json"), rows)),
                     ("fig4", lambda: fig4(read_json(RESULTS_DIR / "f1.json"))),
                     ("fig5", lambda: fig5(read_json(RESULTS_DIR / "f2.json"))),
                     ("fig6", lambda: fig6(read_json(RESULTS_DIR / "s_d.json"), cl)),
                     ("fig7", lambda: fig7(read_json(RESULTS_DIR / "dose_axis.json"), cl))):
        try:
            fn()
        except Exception as e:  # noqa: BLE001 - one broken figure never blocks the others
            logger.exception(f"{name} failed: {e}")


if __name__ == "__main__":
    main()
