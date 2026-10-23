#!/usr/bin/env python3
"""Figures F1-F7 (PDF + PNG) in the aii-data-fig-gen house style (hand-written matplotlib with apply_house_style and
the layout fitters). Every number is read from results/*.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

from common import FIGS, RESULTS, read_json, read_jsonl  # noqa: E402

import os  # noqa: E402

def _find_skill() -> Path:
    """The aii-data-fig-gen scripts folder: $AII_DATA_FIG_GEN_SCRIPTS, else the first ancestor holding
    .claude/skills/aii-data-fig-gen/scripts (outside the pipeline the figures fall back to plain matplotlib)."""
    env = os.environ.get("AII_DATA_FIG_GEN_SCRIPTS")
    if env:
        return Path(env)
    for anc in Path(__file__).resolve().parents:
        cand = anc / ".claude" / "skills" / "aii-data-fig-gen" / "scripts"
        if cand.exists():
            return cand
    return Path("aii-data-fig-gen-not-found")


SKILL = _find_skill()
if SKILL.exists():
    sys.path.insert(0, str(SKILL))
try:
    from chart_style import PALETTE, apply_house_style, clear_legends_of_data, fit_legends, fit_tick_labels, fit_titles
    HAVE_STYLE = True
except ImportError:  # pragma: no cover - outside the pipeline image
    HAVE_STYLE = False
    PALETTE = ["#0173b2", "#de8f05", "#029e73", "#d55e00", "#cc78bc", "#ca9161", "#fbafe4", "#949494"]


def _style() -> None:
    if HAVE_STYLE:
        apply_house_style()
    plt.rcParams["pdf.fonttype"] = 42


def _save(fig: Any, name: str) -> None:
    if HAVE_STYLE:
        for fn in (fit_legends, clear_legends_of_data, fit_tick_labels, fit_titles, clear_legends_of_data):
            try:
                fn(fig)
            except Exception as e:  # noqa: BLE001 - a fitter failing must not lose the figure
                logger.warning(f"{name}: {fn.__name__} failed: {e}")
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGS / f"{name}.pdf")
    fig.savefig(FIGS / f"{name}.png", dpi=200)
    plt.close(fig)
    logger.info(f"figure {name} written")


def f1_forest() -> None:
    n1 = read_json(RESULTS / "n1.json")
    cfgs = list(n1["per_config"])
    _style()
    fig, ax = plt.subplots(figsize=(6.5, 4.2), layout="constrained")
    ys = np.arange(len(cfgs))[::-1] + 1
    for y, c in zip(ys, cfgs):
        t = n1["per_config"][c]
        if t["gap"] is None:
            continue
        lo, hi = t["gap_newcombe95"]
        ax.plot([lo, hi], [y, y], color=PALETTE[0], lw=1.6)
        ax.plot(t["gap"], y, "s", color=PALETTE[0], ms=6)
        ax.text(1.02, y, f"n={t['n']}", va="center", fontsize=8, transform=ax.get_yaxis_transform())
    p, (plo, phi) = n1["pooled_equal_weight"], n1["pooled_bootstrap95"]
    ax.fill([plo, p, phi, p], [0, 0.25, 0, -0.25], color=PALETTE[1])
    ax.axvline(0, color="0.4", lw=0.8, ls="--")
    ax.axvline(0.3, color=PALETTE[2], lw=0.8, ls=":")
    ax.set_yticks(list(ys) + [0])
    ax.set_yticklabels(cfgs + ["pooled"])
    ax.set_xlabel("gap = lexical L1 - mechanistic (runtime label), Newcombe paired 95% CI")
    ax.set_title("N1 (descriptive): lexical minus mechanistic compliance per configuration")
    ax.set_xlim(-0.2, 1.05)
    _save(fig, "F1_n1_forest")


def f2_mosaics() -> None:
    n1 = read_json(RESULTS / "n1.json")
    cfgs = list(n1["per_config"])
    _style()
    fig, ax = plt.subplots(figsize=(6.5, 3.6), layout="constrained")
    keys = [("a_lex_mech", "lexical & mechanistic"), ("b_lex_notmech", "lexical only (covert re-implementation)"),
            ("c_notlex_mech", "mechanistic only"), ("d_neither", "neither")]
    bottom = np.zeros(len(cfgs))
    for i, (k, lab) in enumerate(keys):
        vals = np.array([n1["per_config"][c][k] / max(1, n1["per_config"][c]["n"]) for c in cfgs])
        ax.bar(cfgs, vals, bottom=bottom, color=PALETTE[i], label=lab, width=0.7)
        bottom += vals
    ax.set_ylabel("share of traceable programs")
    ax.set_ylim(0, 1.0)
    ax.set_title("N1: 2x2 lexical x mechanistic compliance per configuration")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, fontsize=8, frameon=False)
    _save(fig, "F2_n1_mosaics")


def f3_k_curves() -> None:
    n3 = read_json(RESULTS / "n3.json")
    n3t = read_json(RESULTS / "n3_tracer.json") if (RESULTS / "n3_tracer.json").exists() else {}
    _style()
    fig, axes = plt.subplots(1, max(1, len(n3)), figsize=(6.5, 3.6), layout="constrained", sharey=True)
    axes = np.atleast_1d(axes)
    names = {"q32": "Qwen3-32B thinking", "q14": "Qwen3-14B thinking"}
    for ax, (mk, v) in zip(axes, n3.items()):
        ks = [int(k) for k in v["per_k"]]
        lex = [v["per_k"][str(k)]["lex_L1_completed"]["rate"] for k in ks]
        mech = [v["per_k"][str(k)]["mech_coarse_traceable"]["rate"] for k in ks]
        lex2 = [v["per_k"][str(k)]["lex_L2_completed"]["rate"] for k in ks]
        ax.plot(ks, lex, "-o", color=PALETTE[0], label="lexical L1")
        ax.plot(ks, lex2, ":", color=PALETTE[0], label="lexical L2")
        ax.plot(ks, mech, "-s", color=PALETTE[3], label="mechanistic, runtime label")
        if mk in n3t:
            mt = [n3t[mk]["per_k"][str(k)]["mech_coarse_traceable"]["rate"] for k in ks]
            ax.plot(ks, mt, "--^", color=PALETTE[2], label="mechanistic, tracer v9")
        if v.get("heldout_k5"):
            h = v["heldout_k5"]
            ax.plot([5.2], [h["lex_L1_completed"]["rate"]], "o", mfc="white", color=PALETTE[0])
            ax.plot([5.2], [h["mech_coarse_traceable"]["rate"]], "s", mfc="white", color=PALETTE[3])
        ax.set_xticks(ks)
        ax.set_title(names.get(mk, mk), fontsize=10)
        ax.set_ylim(-0.02, 1.02)
    axes[0].set_ylabel("compliance (completed programs)")
    axes[0].legend(loc="lower left", fontsize=7)
    fig.supxlabel("k = number of banned names (BFS, +DFS, +IDDFS, +A*, +greedy); open marks = held-out k=5",
                  fontsize=9)
    _save(fig, "F3_n3_k_curves")


def f4_n2() -> None:
    n2 = read_json(RESULTS / "n2.json")
    per = n2["per_survivor"]
    classes = ["BFS", "DFS", "ID", "HEUR", "BIDIR", "OTHER"]
    srcs = sorted({p["source"] for p in per})
    _style()
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 3.6), layout="constrained", sharey=True)
    for ax, key, title in ((axes[0], "runtime_class", "runtime label (committed fallback)"),
                           (axes[1], "tracer_class", "tracer v9 (second column)")):
        bottom = np.zeros(len(classes))
        for i, s_ in enumerate(srcs):
            cnt = np.array([sum(1 for p in per if p["source"] == s_ and p.get(key) == c) for c in classes], float)
            ax.bar(classes, cnt, bottom=bottom, color=PALETTE[i], label=s_)
            bottom += cnt
        k = sum(1 for p in per if p.get(key) in ("BFS", "DFS", "ID", "HEUR"))
        ax.set_title(f"{title}: {k}/{len(per)} banned", fontsize=9)
        ax.tick_params(axis="x", labelrotation=30)
    axes[0].set_ylabel("name-level correct survivors (Qwen3-32B)")
    axes[1].legend(fontsize=7, loc="upper left")
    fig.suptitle("N2: expansion class of the five-name-ban survivors under the two instruments (null 0.6)", fontsize=9)
    _save(fig, "F4_n2_survivor_classes")


def f5_n5() -> None:
    n5 = read_json(RESULTS / "n5.json")
    _style()
    fig, ax = plt.subplots(figsize=(5.5, 4.2), layout="constrained")
    for i, (name, v) in enumerate(n5["sets"].items()):
        if not v.get("defined") or v.get("Dm") is None or v.get("Dn") is None:
            continue
        ax.plot(v["Dm"], v["Dn"], "o", color=PALETTE[i % 8], ms=8)
        ax.annotate(f"{name} (n={v['n_survivors']})", (v["Dm"], v["Dn"]), textcoords="offset points",
                    xytext=(5, 5), fontsize=8)
    ax.axvline(0, color="0.4", lw=0.8)
    ax.axhline(0, color="0.4", lw=0.8)
    ax.set_xlabel("Dm (survivor mechanism distance to the banned set - catalogue mean)")
    ax.set_ylabel("Dn (survivor name distance - catalogue mean)")
    ax.set_title(f"N5: rename quadrant is Dm<0, Dn>0 ({n5['n_joint']}/{n5['n_defined']} sets)")
    _save(fig, "F5_n5_scatter")


def f6_traces(examples: list[tuple[str, dict[str, Any]]], probe_ids: list[int]) -> None:
    import orderclass

    pr = orderclass.probes()
    _style()
    nr, nc = len(examples), len(probe_ids)
    fig, axes = plt.subplots(nr, nc, figsize=(6.5, 1.25 * nr + 0.6), layout="constrained")
    axes = np.atleast_2d(axes)
    for i, (title, tr) in enumerate(examples):
        byi = {p["i"]: p for p in tr.get("probes", [])}
        for j, pi in enumerate(probe_ids):
            ax = axes[i, j]
            g = pr[pi]["grid"]
            R, C = len(g), len(g[0])
            img = np.full((R, C), np.nan)
            seq = (byi.get(pi) or {}).get("seq") or []
            seen = {}
            for k, c in enumerate(seq):
                t = (c[0], c[1])
                if t not in seen:
                    seen[t] = len(seen)
            for (r, c), k in seen.items():
                img[r, c] = k / max(1, len(seen) - 1)
            wall = np.array([[1.0 if ch == "#" else np.nan for ch in row] for row in g])
            ax.imshow(img, cmap="cividis", vmin=0, vmax=1, interpolation="nearest")
            ax.imshow(wall, cmap="Greys", vmin=0, vmax=1.2, interpolation="nearest")
            s, t = pr[pi]["start"], pr[pi]["goal"]
            ax.plot(s[1], s[0], "o", color="white", ms=3)
            ax.plot(t[1], t[0], "*", color="red", ms=4)
            ax.set_xticks([])
            ax.set_yticks([])
            if j == 0:
                ax.set_ylabel(title, fontsize=7, rotation=0, ha="right", va="center")
            if i == 0:
                ax.set_title(f"{pr[pi]['name']} ({pr[pi]['family']})", fontsize=8)
    fig.suptitle("F6: traced expansion order (colour = expansion rank, dark early -> light late; grey = wall)",
                 fontsize=9)
    _save(fig, "F6_expansion_orders")


def f7_gate(gate_file: str) -> None:
    g = read_json(RESULTS / gate_file)
    conf = g["gold_confusion"]
    rows = ["BFS", "DFS", "ID", "HEUR", "BIDIR"]
    cols = ["BFS", "DFS", "ID", "HEUR", "BIDIR", "OTHER", "UNTRACEABLE"]
    M = np.array([[conf.get(r, {}).get(c, 0) for c in cols] for r in rows], float)
    _style()
    fig, ax = plt.subplots(figsize=(6.5, 3.6), layout="constrained")
    Mn = M / np.maximum(1, M.sum(axis=1, keepdims=True))
    ax.imshow(Mn, cmap="cividis", vmin=0, vmax=1)
    for i in range(len(rows)):
        for j in range(len(cols)):
            ax.text(j, i, int(M[i, j]), ha="center", va="center", color="white" if Mn[i, j] < 0.5 else "black",
                    fontsize=9)
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels(cols, rotation=30, ha="right")
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(rows)
    ax.set_xlabel("tracer order class")
    ax.set_ylabel("gold class (prior label)")
    ax.set_title(f"F7: tracer gate ({g['round']}): gold agreement {g['gold_agree']}/{g['gold_in_scope']}")
    _save(fig, f"F7_gate_confusion_{g['round']}")


def f8_reads() -> None:
    mr = read_json(RESULTS / "manual_reads_summary.json")
    items = mr["items"]
    fams = ["UD", "BF", "CK", "RP", "RC", "SP", "FL", "MX"]
    names = {"UD": "unit Dijkstra", "BF": "grid Bellman-Ford", "CK": "coordinate-key heap", "RP": "random priority",
             "RC": "random choice", "SP": "set.pop order", "FL": "raster flood fill", "MX": "mixed deque"}
    _style()
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 3.4), layout="constrained", gridspec_kw={"width_ratios": [1.5, 1]})
    cnt = [sum(1 for i in items if i["family"] == f) for f in fams]
    axes[0].barh([names[f] for f in fams][::-1], cnt[::-1], color=PALETTE[0])
    axes[0].set_xlabel("k = 5 survivors read (Qwen3-32B + 14B)")
    axes[0].set_title("Executor reads: survivor families", fontsize=10)
    cb = {"BFS", "DFS", "ID", "HEUR"}
    n = len(items)
    shares = [sum(1 for i in items if i["read_class"] in cb) / n, sum(1 for i in items if i["tracer_class"] in cb) / n,
              sum(1 for i in items if i["runtime_class"] in cb) / n]
    axes[1].bar(["reads", "tracer v9", "runtime\nlabel"], shares, color=[PALETTE[2], PALETTE[0], PALETTE[3]])
    axes[1].set_ylim(0, 1)
    axes[1].set_ylabel("share in a banned expansion class")
    axes[1].set_title("Same programs, three readings", fontsize=10)
    _save(fig, "F8_survivor_reads")
