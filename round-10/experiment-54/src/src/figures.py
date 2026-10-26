#!/usr/bin/env python3
"""S10 figures (PDF + PNG): F1 compliance vs k, F2 class composition, F3 MDS behaviour map (decision space),
F4 instrument agreement heatmap, F5 held-out excess, F6 maximum agreement with banned rules by k."""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

import analysis  # noqa: E402
import stats  # noqa: E402
from common import DATA, FIGS, RESULTS, read_json, read_jsonl, write_json  # noqa: E402

plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.size": 9})
MODEL_NAME = {"q8": "Qwen3-8B (no thinking)", "q14": "Qwen3-14B (thinking)", "q32": "Qwen3-32B (thinking)"}
CLASS_COL = {"BF": "#1f77b4", "FF": "#ff7f0e", "WF": "#2ca02c", "AWF": "#d62728", "LF": "#9467bd", "RF": "#8c564b",
             "other": "#7f7f7f", "invalid": "#dddddd"}
CELLS = ["BASE", "NAME_1", "NAME_2", "NAME_3", "NAME_4", "NAME_5", "DESC_5", "HOLD_5", "INSTR_NEW", "INSTR_LONG"]


def save(fig, name: str) -> None:
    fig.savefig(FIGS / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIGS / f"{name}.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def f1(cells: dict[str, Any], models: list[str]) -> None:
    fig, axes = plt.subplots(1, len(models), figsize=(4.2 * len(models), 3.4), squeeze=False)
    for ax, m in zip(axes[0], models):
        for key, lab, col, off in [("L1_valid", "lexical L1", "#1f77b4", -0.06), ("mech_valid", "mechanistic", "#d62728",
                                                                                 0.06)]:
            ks, ys, lo, hi = [], [], [], []
            for k in range(1, 6):
                c = cells.get(f"{m}|NAME_{k}")
                if not c or not c[key]["n"]:
                    continue
                ks.append(k + off)
                ys.append(c[key]["rate"])
                lo.append(max(0.0, c[key]["rate"] - c[key]["wilson95"][0]))
                hi.append(max(0.0, c[key]["wilson95"][1] - c[key]["rate"]))
            if ks:
                ax.errorbar(ks, ys, yerr=[lo, hi], marker="o", color=col, label=lab, capsize=2)
            for cell, mk, dx in [("DESC_5", "s", 0.25), ("HOLD_5", "^", 0.4)]:
                c = cells.get(f"{m}|{cell}")
                if c and c[key]["n"]:
                    r = c[key]
                    ax.errorbar([5 + dx + off], [r["rate"]], yerr=[[max(0.0, r["rate"] - r["wilson95"][0])],
                                                                     [max(0.0, r["wilson95"][1] - r["rate"])]],
                                marker=mk, color=col, alpha=0.6, capsize=2, linestyle="none")
        ax.set_title(MODEL_NAME.get(m, m))
        ax.set_xlabel("number of banned rule names k (s = DESC_5, ^ = HOLD_5 at k = 5)")
        ax.set_ylabel("compliance among VALID programs")
        ax.set_ylim(-0.03, 1.03)
        ax.set_xticks([1, 2, 3, 4, 5])
        ax.legend(fontsize=7, loc="lower left")
    save(fig, "F1_compliance_vs_k")


def f2(cells: dict[str, Any], models: list[str]) -> None:
    fig, axes = plt.subplots(1, len(models), figsize=(4.6 * len(models), 3.6), squeeze=False)
    order = ["BF", "FF", "WF", "AWF", "LF", "RF", "other", "invalid"]
    for ax, m in zip(axes[0], models):
        present = [c for c in CELLS if f"{m}|{c}" in cells]
        bottom = np.zeros(len(present))
        for cl in order:
            v = np.array([cells[f"{m}|{c}"]["class_composition"].get(cl, 0) / max(1, cells[f"{m}|{c}"]["N"])
                          for c in present])
            ax.bar(range(len(present)), v, bottom=bottom, color=CLASS_COL[cl], label=cl)
            bottom += v
        ax.set_xticks(range(len(present)))
        ax.set_xticklabels(present, rotation=60, fontsize=7)
        ax.set_ylabel("share of all samples")
        ax.set_title(MODEL_NAME.get(m, m))
    axes[0][-1].legend(fontsize=7, bbox_to_anchor=(1.02, 1), loc="upper left")
    save(fig, "F2_class_composition")


def _agree_matrix(V: np.ndarray) -> np.ndarray:
    n = V.shape[0]
    D = np.zeros((n, n))
    for i in range(n):
        D[i] = 1.0 - (V == V[i]).mean(axis=1)
    return D


def f3(rows: list[dict[str, Any]], models: list[str]) -> dict[str, Any]:
    from sklearn.manifold import MDS
    dec = {r["row_id"]: r["vecs"] for r in read_jsonl(DATA / "decisions.jsonl")}
    corpus = read_json(RESULTS / "corpus.json")
    cvec = read_json(DATA / "corpus_decisions.json")
    gate = read_json(RESULTS / "instrument_gate.json")
    info: dict[str, Any] = {}
    panels = models + ["pooled"]
    fig, axes = plt.subplots(1, len(panels), figsize=(4.6 * len(panels), 4.4), squeeze=False)
    cell_col = {c: plt.cm.tab10(i) for i, c in enumerate(CELLS)}
    marker = {"q8": "o", "q14": "s", "q32": "^"}
    for ax, panel in zip(axes[0], panels):
        prog = [r for r in rows if r.get("valid") and r["row_id"] in dec and (panel == "pooled" or r["model"] == panel)]
        uniq: dict[bytes, dict[str, Any]] = {}
        for r in prog:
            v = np.array(dec[r["row_id"]]["0"], dtype=np.uint16)
            key = v.tobytes()
            if key not in uniq:
                uniq[key] = {"v": v, "n": 0, "cells": Counter(), "models": Counter()}
            uniq[key]["n"] += 1
            uniq[key]["cells"][r["cell"]] += 1
            uniq[key]["models"][r["model"]] += 1
        refs = [(f"catalogue:{c}", np.array(gate["reference_vectors"][c]["0"], dtype=np.uint16)) for c in
                ["BF", "FF", "WF", "AWF", "LF", "RF"]]
        has0 = {m["name"] for m in corpus["members"] if "0" in (cvec.get(m["name"]) or {})}
        pubs = [(m["name"], np.array(cvec[m["name"]]["0"], dtype=np.uint16)) for m in corpus["members"]
                if m["name"] in has0 and (m["family"] != "ab" or m["name"].startswith("published") or m.get("tuned"))]
        grid = [(m["name"], np.array(cvec[m["name"]]["0"], dtype=np.uint16)) for m in corpus["members"]
                if m["name"] in has0 and m["family"] == "ab" and m["name"].startswith("grid")
                and not m.get("tuned")][::3]
        pts = list(uniq.values())
        V = np.stack([p["v"] for p in pts] + [v for _, v in refs] + [v for _, v in pubs] + [v for _, v in grid]) \
            if pts else np.stack([v for _, v in refs] + [v for _, v in pubs] + [v for _, v in grid])
        D = _agree_matrix(V)
        mds = MDS(n_components=2, dissimilarity="precomputed", n_init=4, random_state=0, normalized_stress=False)
        X = mds.fit_transform(D)
        dhat = np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(-1))
        iu = np.triu_indices(len(D), 1)
        stress1 = float(np.sqrt(((D[iu] - dhat[iu]) ** 2).sum() / max((D[iu] ** 2).sum(), 1e-12)))
        n0 = len(pts)
        n1 = n0 + len(refs)
        n2 = n1 + len(pubs)
        ax.scatter(X[n2:, 0], X[n2:, 1], s=6, color="#bbbbbb", label="ab grid (every 3rd)", zorder=1)
        for j, (name, _) in enumerate(pubs):
            tuned = "tuned" in name or any(m["name"] == name and m.get("tuned") for m in corpus["members"])
            ax.scatter(X[n1 + j, 0], X[n1 + j, 1], s=40 if tuned else 10, marker="*" if tuned else "x",
                       color="black", zorder=2)
        for j, (name, _) in enumerate(refs):
            ax.scatter(X[n0 + j, 0], X[n0 + j, 1], s=90, marker="P", color=CLASS_COL[name.split(":")[1]],
                       edgecolor="k", zorder=4)
            ax.annotate(name.split(":")[1], X[n0 + j], fontsize=8, weight="bold")
        for j, p in enumerate(pts):
            cell = p["cells"].most_common(1)[0][0]
            mk = p["models"].most_common(1)[0][0]
            ax.scatter(X[j, 0], X[j, 1], s=12 + 10 * p["n"], color=cell_col.get(cell, "k"), marker=marker.get(mk, "o"),
                       alpha=0.6, edgecolor="none", zorder=3)
        ax.set_title(f"{MODEL_NAME.get(panel, panel)}\n{n0} unique programs, Kruskal stress-1 {stress1:.2f}",
                     fontsize=8)
        ax.set_xlabel("MDS 1 (decision space, distance = 1 - agreement)")
        ax.set_ylabel("MDS 2")
        info[panel] = {"n_unique_programs": n0, "n_programs": len(prog), "stress1": stress1}
    handles = [plt.Line2D([], [], marker="o", linestyle="none", color=cell_col[c], label=c) for c in CELLS]
    axes[0][-1].legend(handles=handles, fontsize=6, bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.suptitle("F3: behaviour map in DECISION space (exact bin choices on 2,000 probe states), not activation space",
                 fontsize=9)
    save(fig, "F3_mds_behaviour_map")
    return info


def f4() -> None:
    g = read_json(RESULTS / "instrument_gate.json")
    import instr
    R = {c: {int(s): np.array(v, dtype=np.uint16) for s, v in sv.items()} for c, sv in g["reference_vectors"].items()}
    cv = read_json(DATA / "corpus_decisions.json")
    extra = {n: {int(s): np.array(v, dtype=np.uint16) for s, v in cv[n].items()} for n in
             ["funsearch:c12_vec", "funsearch:c14", "published:ab-FF(5,24)", "published:ab-WF(1,21)"]}
    names = ["BF", "FF", "WF", "AWF", "LF", "RF"] + list(extra)
    allv = {**R, **extra}
    M = np.array([[instr.A(allv[a], allv[b], b == "RF") for b in names] for a in names])
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(M, vmin=0, vmax=1, cmap="viridis")
    ax.set_xticks(range(len(names)))
    ax.set_yticks(range(len(names)))
    lab = [n.split(":")[-1] for n in names]
    ax.set_xticklabels(lab, rotation=60, fontsize=7)
    ax.set_yticklabels(lab, fontsize=7)
    for i in range(len(names)):
        for j in range(len(names)):
            ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", fontsize=6, color="w" if M[i, j] < 0.6 else "k")
    fig.colorbar(im, ax=ax, label="exact-decision agreement A (2,000 probe states)")
    ax.set_title(f"F4: instrument agreement (min margin {g['min_margin']:.2f} below the 0.95 class threshold)",
                 fontsize=8)
    save(fig, "F4_instrument_heatmap")


def f5(rows: list[dict[str, Any]]) -> None:
    fig, ax = plt.subplots(figsize=(5.4, 4.2))
    pts = [r for r in rows if r.get("valid") and r.get("h_or3_excess") is not None]
    for m, mk in [("q8", "o"), ("q14", "s"), ("q32", "^")]:
        xs = [r["h_or3_excess"] for r in pts if r["model"] == m]
        ys = [r.get("h_fsw5k_excess") if r.get("h_fsw5k_excess") is not None else np.nan for r in pts if
              r["model"] == m]
        ax.scatter(xs, [y if np.isfinite(y) else 12.0 for y in ys], marker=mk, s=12, alpha=0.5,
                   label=f"{m} (H-FSW5k run only if H-OR3 <= 4.294%; else plotted at 12)")
    for name, x, y in [("BF", 5.368, 3.984), ("c12", 3.106, None), ("c14", None, 0.684)]:
        if x is not None and y is not None:
            ax.scatter([x], [y], marker="P", s=80, color="k")
            ax.annotate(name, (x, y))
    ax.axvline(4.294, color="r", ls="--", lw=0.8)
    ax.axhline(3.187, color="r", ls="--", lw=0.8)
    ax.set_xlabel("H-OR3 excess over L1 (%)")
    ax.set_ylabel("H-FSW5k excess over L1 (%)")
    ax.set_xlim(0, 30)
    ax.set_ylim(0, 13)
    ax.set_title("F5: held-out excess; dashed = 0.8 x best fit (better-than-BF region bottom-left)", fontsize=8)
    ax.legend(fontsize=6)
    save(fig, "F5_heldout_excess")


def f6(rows: list[dict[str, Any]], orders: dict[str, Any], models: list[str]) -> None:
    fig, axes = plt.subplots(1, len(models), figsize=(4.2 * len(models), 3.2), squeeze=False)
    for ax, m in zip(axes[0], models):
        data, labels = [], []
        for cell in ["NAME_1", "NAME_2", "NAME_3", "NAME_4", "NAME_5", "DESC_5", "HOLD_5"]:
            if m not in orders:
                continue
            B = analysis.banned_for(cell, orders[m])
            v = [analysis.max_agree_banned(r, B) for r in rows if r["model"] == m and r["cell"] == cell and
                 r.get("valid")]
            v = [x for x in v if x is not None]
            if v:
                data.append(v)
                labels.append(cell.replace("NAME_", "k="))
        if data:
            ax.boxplot(data, showfliers=True)
            ax.set_xticks(range(1, len(labels) + 1))
            ax.set_xticklabels(labels, fontsize=7)
        ax.axhline(0.95, color="r", ls="--", lw=0.8)
        ax.set_ylabel("max agreement with a banned rule")
        ax.set_title(MODEL_NAME.get(m, m))
    save(fig, "F6_max_agree_banned")


def run_all() -> dict[str, Any]:
    rows = analysis.load_rows()
    cells = read_json(RESULTS / "cells.json")
    orders = analysis.load_orders()
    models = [m for m in ["q8", "q14", "q32"] if any(r["model"] == m for r in rows)]
    out: dict[str, Any] = {}
    for name, fn in [("F1", lambda: f1(cells, models)), ("F2", lambda: f2(cells, models)),
                     ("F3", lambda: f3(rows, models)), ("F4", f4), ("F5", lambda: f5(rows)),
                     ("F6", lambda: f6(rows, orders, models))]:
        try:
            out[name] = fn() or "ok"
        except Exception as e:  # noqa: BLE001 - one figure must not block the others
            logger.exception(f"figure {name} failed: {e!r}")
            out[name] = f"failed: {e!r}"[:300]
    write_json(RESULTS / "figures.json", out)
    return out
