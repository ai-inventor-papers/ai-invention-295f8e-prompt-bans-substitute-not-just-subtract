#!/usr/bin/env python3
"""Figures F1-F6 (PDF + PNG) from data/samples.jsonl and results/*.json; house style of aii-data-fig-gen.

F1 discovery curves (distinct OOC programs and idea clusters against calls, every arm, 95% Poisson bands; S per island)
F2 MAP-Elites archive heatmaps per task (rows runtime label, columns DS-signature, colour elite novelty) + coverage
   and QD-score against S calls per island
F3 novelty (1 - nearest-known Jaccard) per arm with the s* band; novelty against runtime ratio coloured by final class
F4 adjudication: final classes per arm and task, judge-vs-judge confusion, control accuracy
F5 lineage tree of the most novel level-b (else level-a) S program per task
F6 program-space classical MDS of (1 - Jaccard) over correct OOC programs, catalogue references and their nearest
   known solutions (stress-1 reported), coloured by arm
"""

from __future__ import annotations

import sys
import warnings
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

from common import DATA, FIGS, PRED, RESULTS, read_json, read_jsonl

# optional house-style helpers (aii-data-fig-gen); set AII_DATA_FIG_GEN_SCRIPTS to its scripts/ folder, else plain matplotlib
import os  # noqa: E402
SKILL = Path(os.environ.get("AII_DATA_FIG_GEN_SCRIPTS", "")) if os.environ.get("AII_DATA_FIG_GEN_SCRIPTS") else None
if SKILL is not None and SKILL.exists():
    sys.path.insert(0, str(SKILL))
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

try:
    from chart_style import (PALETTE, apply_house_style, clear_legends_of_data, fit_legends,  # noqa: E402
                             fit_tick_labels, fit_titles, place_legend)
    HOUSE = True
except ImportError:  # the skill is not present on a reader's machine: plain matplotlib
    HOUSE = False
    PALETTE = ("#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#000000")

ARMS = ("S", "NE", "I0", "EAP", "BINT", "B0", "L")
ARM_COLOR = {a: PALETTE[i % len(PALETTE)] for i, a in enumerate(ARMS)}
CLASS_COLOR = {"NOVEL ALGORITHM": "#D55E00", "KNOWN OUTSIDE CATALOGUE": "#0072B2", "CATALOGUE VARIANT": "#999999",
               "DEGENERATE": "#000000", None: "#CCCCCC"}


def _style() -> None:
    if HOUSE:
        apply_house_style()
    plt.rcParams["pdf.fonttype"] = 42


def _legend(ax, **kw) -> None:
    if HOUSE:
        place_legend(ax, **kw)
    else:
        ax.legend(**kw)


def _save(fig, name: str) -> None:
    if HOUSE:
        for f in (fit_legends, clear_legends_of_data, fit_tick_labels, fit_titles, clear_legends_of_data):
            try:
                f(fig)
            except Exception as e:  # noqa: BLE001 - a fitter that cannot reflow must not lose the figure
                logger.debug(f"{name}: fitter {f.__name__} skipped: {e}")
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGS / f"{name}.pdf")
    fig.savefig(FIGS / f"{name}.png", dpi=200)
    plt.close(fig)
    logger.info(f"figure {name}")


def _poisson_band(c: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    from scipy import stats
    lo = np.where(c > 0, stats.chi2.ppf(0.025, 2 * c) / 2, 0.0)
    hi = stats.chi2.ppf(0.975, 2 * c + 2) / 2
    return lo, hi


def f1(samples, tasks) -> None:
    curves = read_json(RESULTS / "discovery_curves.json")
    fig, axes = plt.subplots(2, len(tasks), figsize=(4.2 * len(tasks), 6.4), layout="constrained", squeeze=False)
    for j, t in enumerate(tasks):
        for i, key in enumerate(("distinct", "clusters")):
            ax = axes[i][j]
            for a in ARMS:
                y = np.array(curves[key].get(t, {}).get(a) or [])
                if a == "L":
                    rs = sorted([r for r in samples if r["task"] == t and r["arm"] == "L"], key=lambda r: r["slot"])
                    seen: set = set()
                    y = []
                    for r in rs:
                        if r.get("correct") and r.get("ooc_screen") and r.get("distinct_id" if key == "distinct" else
                                                                             "cluster_id"):
                            seen.add(r["distinct_id" if key == "distinct" else "cluster_id"])
                        y.append(len(seen))
                    y = np.array(y)
                if len(y) == 0:
                    continue
                x = np.arange(1, len(y) + 1)
                lo, hi = _poisson_band(y.astype(float))
                ax.plot(x, y, color=ARM_COLOR[a], label=a, lw=1.6)
                ax.fill_between(x, lo, hi, color=ARM_COLOR[a], alpha=0.12, lw=0)
            if key == "distinct":
                isl = defaultdict(list)
                for r in sorted([r for r in samples if r["task"] == t and r["arm"] == "S"], key=lambda r: r["slot"]):
                    isl[r.get("island")].append(r)
                for k, rs in isl.items():
                    seen = set()
                    y = []
                    for r in rs:
                        if r.get("correct") and r.get("ooc_screen") and r.get("distinct_id"):
                            seen.add(r["distinct_id"])
                        y.append(len(seen))
                    ax.plot(np.arange(1, len(y) + 1), y, color=ARM_COLOR["S"], lw=0.7, ls=":", alpha=0.8)
            ax.set_xlabel("calls (children)")
            ax.set_ylabel("distinct OOC programs" if key == "distinct" else "OOC idea clusters")
            ax.set_title(f"{t}: {'distinct programs (dotted: S per island)' if key == 'distinct' else 'idea clusters'}")
            if j == 0 and i == 0:
                _legend(ax, loc="upper left", fontsize=7)
    _save(fig, "F1_discovery_curves")


def f2(tasks) -> None:
    fig, axes = plt.subplots(2, len(tasks), figsize=(5.0 * len(tasks), 8.0), layout="constrained", squeeze=False,
                             gridspec_kw={"height_ratios": [3, 1.4]})
    for j, t in enumerate(tasks):
        p = RESULTS / f"archive_{t}.json"
        if not p.exists():
            continue
        a = read_json(p)
        best: dict[tuple[str, str], float] = {}
        for isl in a["final"]["islands"]:
            for c, e in isl["cells"].items():
                lab, sig = c.split("|", 1)
                best[(lab, sig)] = max(best.get((lab, sig), 0.0), e["novelty"])
        labs = sorted({k[0] for k in best}, key=lambda x: (x == "other", x))
        sigs = sorted({k[1] for k in best}, key=lambda s: -sum(1 for k in best if k[1] == s))[:18]
        M = np.full((len(labs), len(sigs)), np.nan)
        for (l, s), v in best.items():
            if s in sigs:
                M[labs.index(l), sigs.index(s)] = v
        ax = axes[0][j]
        im = ax.imshow(M, aspect="auto", cmap="viridis", vmin=0, vmax=1)
        ax.set_yticks(range(len(labs)), labs, fontsize=7)
        ax.set_xticks(range(len(sigs)), sigs, rotation=70, ha="right", fontsize=6)
        ax.set_title(f"{t}: elite novelty per cell (all islands)")
        fig.colorbar(im, ax=ax, shrink=0.7, label="elite novelty 1 - s")
        ax2 = axes[1][j]
        hist = a.get("history") or []
        if hist:
            tt = [h["t"] for h in hist]
            for k in range(len(hist[0]["n_cells"])):
                ax2.plot(tt, [h["n_cells"][k] for h in hist], color=PALETTE[k % len(PALETTE)], lw=1.2,
                         label=f"island {k} cells")
                ax2.plot(tt, [h["qd_score"][k] for h in hist], color=PALETTE[k % len(PALETTE)], lw=1.0, ls="--")
            for h in hist:
                for rr in h.get("resets") or []:
                    ax2.axvline(rr["at_call"], color="0.5", lw=0.6, ls=":")
        ax2.set_xlabel("S calls")
        ax2.set_ylabel("cells (solid) / QD-score (dashed)")
        if j == 0:
            _legend(ax2, loc="upper left", fontsize=6)
    _save(fig, "F2_archive_heatmaps")


def f3(samples, tasks) -> None:
    plan = read_json(PRED / "commit1.json")
    fig, axes = plt.subplots(2, len(tasks), figsize=(4.4 * len(tasks), 7.0), layout="constrained", squeeze=False)
    for j, t in enumerate(tasks):
        ax = axes[0][j]
        data, names = [], []
        for a in ARMS:
            v = [r["novelty"] for r in samples if r["task"] == t and r["arm"] == a and r.get("correct") and
                 r.get("novelty") is not None]
            if v:
                data.append(v)
                names.append(f"{a}\n(n={len(v)})")
        if data:
            parts = ax.violinplot(data, showmedians=True)
            for k, b in enumerate(parts["bodies"]):
                b.set_alpha(0.5)
            ax.set_xticks(range(1, len(names) + 1), names, fontsize=7)
        ss = plan["s_star"][t]["s_star"]
        ax.axhspan(1 - ss, 1.0, color="#D55E00", alpha=0.08)
        ax.axhline(1 - ss, color="#D55E00", lw=1, ls="--")
        ax.set_ylabel("novelty 1 - s (correct programs)")
        ax.set_title(f"{t}: novelty by arm; shaded = beyond the variant band s* = {ss:.2f}")
        ax = axes[1][j]
        pts = [r for r in samples if r["task"] == t and r.get("correct") and r.get("novelty") is not None and
               r.get("runtime_ratio")]
        for cls in ("CATALOGUE VARIANT", "DEGENERATE", "KNOWN OUTSIDE CATALOGUE", "NOVEL ALGORITHM", None):
            xs = [r["runtime_ratio"] for r in pts if r.get("final_class") == cls]
            ys = [r["novelty"] for r in pts if r.get("final_class") == cls]
            if xs:
                ax.scatter(xs, ys, s=6 if cls is None else 14, color=CLASS_COLOR[cls], alpha=0.35 if cls is None else 0.8,
                           label=cls or "not adjudicated", lw=0)
        ax.set_xscale("log")
        ax.axhline(1 - ss, color="#D55E00", lw=1, ls="--")
        ax.set_xlabel("runtime ratio to fastest reference (stress inputs)")
        ax.set_ylabel("novelty 1 - s")
        if j == 0:
            _legend(ax, loc="lower right", fontsize=6)
    _save(fig, "F3_novelty")


def f4(samples, tasks) -> None:
    adj = read_json(RESULTS / "adjudication.json") if (RESULTS / "adjudication.json").exists() else None
    gate = read_json(RESULTS / "judge_gate.json") if (RESULTS / "judge_gate.json").exists() else None
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.2), layout="constrained")
    ax = axes[0]
    keys = [(t, a) for t in tasks for a in ARMS if any(r["task"] == t and r["arm"] == a for r in samples)]
    classes = ("NOVEL ALGORITHM", "KNOWN OUTSIDE CATALOGUE", "CATALOGUE VARIANT", "DEGENERATE")
    bottom = np.zeros(len(keys))
    for cls in classes:
        v = []
        for t, a in keys:
            ids = {r["distinct_id"] for r in samples if r["task"] == t and r["arm"] == a and r.get("ooc_screen")
                   and r.get("distinct_id") and r.get("final_class") == cls}
            v.append(len(ids))
        ax.bar(range(len(keys)), v, bottom=bottom, color=CLASS_COLOR[cls], label=cls)
        bottom += np.array(v)
    ax.set_xticks(range(len(keys)), [f"{t}\n{a}" for t, a in keys], fontsize=6)
    ax.set_ylabel("distinct OOC programs by final class")
    ax.set_title("adjudicated classes per task x arm")
    _legend(ax, loc="upper right", fontsize=6)
    ax = axes[1]
    pair = (adj.get("judges") or adj.get("advisory_pair") or []) if adj else []
    if adj and len(pair) == 2:
        ja, jb = pair
        vkey = "votes" if adj.get("judges") else "advisory_votes"
        cm = np.zeros((4, 4))
        for rec in adj["per_candidate"].values():
            va, vb = rec.get(vkey, {}).get(ja), rec.get(vkey, {}).get(jb)
            if va in classes and vb in classes:
                cm[classes.index(va), classes.index(vb)] += 1
        ax.imshow(cm, cmap="Blues")
        for i in range(4):
            for k in range(4):
                ax.text(k, i, int(cm[i, k]), ha="center", va="center", fontsize=8)
        short = ["NOVEL", "KNOWN-OUT", "VARIANT", "DEGEN"]
        ax.set_xticks(range(4), short, fontsize=7)
        ax.set_yticks(range(4), short, fontsize=7)
        ax.set_xlabel(jb.split("/")[-1])
        ax.set_ylabel(ja.split("/")[-1])
        k = adj.get("kappa") if adj.get("judges") else adj.get("advisory_kappa")
        tag = "" if adj.get("judges") else "advisory (ungated) "
        ax.set_title(f"{tag}judge agreement, kappa {k:.2f}" if k is not None else f"{tag}judge agreement")
    ax = axes[2]
    if gate:
        ms = list(gate["judges"])
        acc = [gate["judges"][m]["accuracy"] for m in ms]
        ax.bar(range(len(ms)), acc, color=[ARM_COLOR["S"] if gate["judges"][m]["passed"] else "#999999" for m in ms])
        ax.axhline(9, color="#D55E00", ls="--", lw=1)
        ax.set_xticks(range(len(ms)), [m.split("/")[-1] for m in ms], rotation=20, fontsize=7)
        ax.set_ylim(0, 10.5)
        ax.set_ylabel("controls correct (of 10)")
        ax.set_title("control gate (pass >= 9)")
    _save(fig, "F4_adjudication")


def f5(samples, tasks) -> None:
    byid = {r["id"]: r for r in samples}
    seeds = {}
    for t in tasks:
        p = DATA / f"seeds_{t}.json"
        if p.exists():
            for s in read_json(p):
                seeds[s["id"]] = s
    fig, axes = plt.subplots(1, len(tasks), figsize=(5.2 * len(tasks), 4.6), layout="constrained", squeeze=False)
    for j, t in enumerate(tasks):
        ax = axes[0][j]
        cand = [r for r in samples if r["task"] == t and r["arm"] == "S" and r.get("correct") and r.get("ooc_screen")]
        lb = [r for r in cand if r.get("final_class") in ("KNOWN OUTSIDE CATALOGUE", "NOVEL ALGORITHM")]
        pool = lb or cand
        if not pool:
            ax.set_axis_off()
            continue
        top = max(pool, key=lambda r: (r.get("depth") or 0, r.get("novelty") or 0))
        nodes, edges = {}, []

        def walk(nid: str, d: int) -> None:
            if nid in nodes or d > 12:
                return
            r = byid.get(nid) or seeds.get(nid)
            nodes[nid] = r
            for p in (r or {}).get("parent_ids") or []:
                edges.append((p, nid))
                walk(p, d + 1)
        walk(top["id"], 0)
        depth = {n: ((nodes[n] or {}).get("depth") or 0) for n in nodes}
        levels = defaultdict(list)
        for n, d in depth.items():
            levels[d].append(n)
        pos = {}
        for d, ns in levels.items():
            for k, n in enumerate(sorted(ns)):
                pos[n] = (d, k - (len(ns) - 1) / 2)
        for a, b in edges:
            if a in pos and b in pos:
                ax.annotate("", xy=pos[b], xytext=pos[a], arrowprops=dict(arrowstyle="->", color="0.5", lw=0.8))
        for n, (x, y) in pos.items():
            r = nodes[n] or {}
            col = CLASS_COLOR.get(r.get("final_class"), "#CCCCCC") if not n.startswith("seed:") else "#009E73"
            ax.scatter([x], [y], s=60, color=col, zorder=3)
            lab = n.split(":")[-1] if n.startswith("seed:") else n.split("|")[-1]
            nu = r.get("novelty")
            ax.text(x, y + 0.18, f"{lab}\nnu={nu:.2f}" if nu is not None else lab, ha="center", fontsize=6)
        ax.set_xlabel("generation depth (0 = catalogue seed)")
        ax.set_yticks([])
        ax.margins(x=0.06, y=0.3)
        ax.set_title(f"{t}: lineage of {top['id'].split('|')[-1]} ({top.get('final_class') or 'level a'})")
    _save(fig, "F5_lineage")


def classical_mds(D: np.ndarray, k: int = 2) -> tuple[np.ndarray, float]:
    n = D.shape[0]
    J = np.eye(n) - np.ones((n, n)) / n
    B = -0.5 * J @ (D ** 2) @ J
    w, V = np.linalg.eigh(B)
    idx = np.argsort(w)[::-1][:k]
    X = V[:, idx] * np.sqrt(np.maximum(w[idx], 0))
    Dh = np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(-1))
    stress = float(np.sqrt(((D - Dh) ** 2).sum() / max((D ** 2).sum(), 1e-12)))
    return X, stress


def f6(samples, tasks) -> None:
    from critic import Critic, shingle_ids, to_matrix
    from inputs import load_task
    C = Critic()
    fig, axes = plt.subplots(1, len(tasks), figsize=(5.0 * len(tasks), 4.8), layout="constrained", squeeze=False)
    rng = np.random.default_rng(3)
    out = {}
    for j, t in enumerate(tasks):
        ax = axes[0][j]
        progs = [r for r in samples if r["task"] == t and r.get("correct") and r.get("ooc_screen") and
                 r.get("is_first_of_distinct")]
        if len(progs) > 360:
            progs = [progs[i] for i in sorted(rng.choice(len(progs), 360, replace=False))]
        refs = load_task(t)["references"]
        id2idx = {m["id"]: k for k, m in enumerate(C.meta)}
        near = sorted({id2idx[r["nearest_known_id"]] for r in progs if r.get("nearest_known_id") in id2idx
                       and C.meta[id2idx[r["nearest_known_id"]]]["kind"] == "corpus"})[:120]
        codes = [r["code"] for r in progs] + list(refs.values()) + [C.code(i) for i in near]
        kinds = [r["arm"] for r in progs] + ["catalogue"] * len(refs) + ["known"] * len(near)
        if len(codes) < 4:
            ax.set_axis_off()
            continue
        M = to_matrix([shingle_ids(c) for c in codes])
        inter = (M @ M.T).toarray()
        sz = np.diag(inter)
        den = sz[:, None] + sz[None, :] - inter
        Jm = np.where(den > 0, inter / np.maximum(den, 1e-9), 1.0)
        X, stress = classical_mds(1 - Jm)
        for kind in ("known", "catalogue") + ARMS:
            ii = [i for i, k in enumerate(kinds) if k == kind]
            if not ii:
                continue
            if kind == "known":
                ax.scatter(X[ii, 0], X[ii, 1], s=10, marker="x", color="0.55", label="nearest known (corpus)")
            elif kind == "catalogue":
                ax.scatter(X[ii, 0], X[ii, 1], s=70, marker="*", color="#000000", label="catalogue reference")
            else:
                ax.scatter(X[ii, 0], X[ii, 1], s=12, color=ARM_COLOR[kind], alpha=0.7, label=kind, lw=0)
        ax.set_title(f"{t}: classical MDS of 1 - Jaccard (stress-1 {stress:.2f})")
        ax.set_xlabel("MDS 1")
        ax.set_ylabel("MDS 2")
        if j == 0:
            _legend(ax, loc="best", fontsize=6)
        out[t] = {"n_programs": len(progs), "n_refs": len(refs), "n_known": len(near), "stress1": stress}
    _save(fig, "F6_program_space_mds")
    from common import write_json
    write_json(RESULTS / "mds.json", out)


def make_all() -> None:
    _style()
    samples = read_jsonl(DATA / "samples.jsonl")
    tasks = [t for t in ("T03", "T2", "A3") if any(r["task"] == t and r["arm"] == "S" for r in samples)]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for name, fn, args in (("F1", f1, (samples, tasks)), ("F2", f2, (tasks,)), ("F3", f3, (samples, tasks)),
                               ("F4", f4, (samples, tasks)), ("F5", f5, (samples, tasks)), ("F6", f6, (samples, tasks))):
            try:
                fn(*args)
            except Exception as e:  # noqa: BLE001 - one failing figure must not stop the others; logged
                logger.error(f"figure {name} failed: {type(e).__name__}: {e}")
    _ = Counter
