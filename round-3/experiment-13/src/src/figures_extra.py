#!/usr/bin/env python3
"""Extra figures drawn from the committed analysis outputs (no new numbers):
(1) the log-score plot redrawn with the shading behind the points (the committed analyze.py draws it on top);
(2) a forecast-vs-realised table figure for the gated events;
(3) avoidance of every push vs the named ban per task (heatmap)."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from common import FIGS, RESULTS, TASK_ORDER, read_json, read_jsonl  # noqa: E402

FAMS = ["SUBTRACT", "LADDER", "ASSOCIATE", "PROXIMITY", "SUBTRACT_1SHOT", "UNIFORM"]


def logscores() -> None:
    ev = [e for e in read_jsonl(RESULTS / "c1_events.jsonl") if e["n_non_banned"] > 0]
    fig, ax = plt.subplots(figsize=(12, 4.8))
    for i, e in enumerate(ev):
        if e["disagreeing"] and e["gate_pass"]:
            ax.axvspan(i - 0.45, i + 0.45, color="#f3e6b3", alpha=0.6, lw=0, zorder=0)
    mk = {True: "o", False: "x"}
    for j, f in enumerate(FAMS):
        xs = np.arange(len(ev)) + (j - len(FAMS) / 2) * 0.12
        for x, e in zip(xs, ev):
            ax.scatter(x, e["logscore"][f], color=plt.get_cmap("tab10")(j), marker=mk[bool(e["defined"][f])],
                       s=30, zorder=3, label=f if e is ev[0] else None)
    ax.set_xticks(range(len(ev)))
    ax.set_xticklabels([e["task"] + ("" if e["gate_pass"] else "*") for e in ev])
    ax.set_ylabel("mean log score (nats)")
    ax.set_title("Forecast log scores on the ban's non-banned attempts (o = defined forecast, x = undefined, scored "
                 "uniform; shaded = gated disagreeing; * = gate failed)", fontsize=9)
    ax.legend(fontsize=7, ncol=3, loc="lower right")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIGS / f"logscores_by_family_v2.{ext}", dpi=150)
    plt.close(fig)


def forecast_table() -> None:
    ev = [e for e in read_jsonl(RESULTS / "c1_events.jsonl") if e["gate_pass"]]
    cols = ["task", "ban landing (top)", "SUBTRACT", "LADDER", "ASSOCIATE", "PROXIMITY"]
    cells = []
    for e in ev:
        land = sorted(e["landing_counts"].items(), key=lambda kv: -kv[1])
        top = ", ".join(f"{k} {v}" for k, v in land[:2])
        cells.append([e["task"], top] + [(e["top1"][f] or "undef") + (" *" if e["top1"][f] in e["realised_top1"]
                                                                        else "") for f in FAMS[:4]])
    fig, ax = plt.subplots(figsize=(12, 0.5 + 0.45 * len(cells)))
    ax.axis("off")
    t = ax.table(cellText=cells, colLabels=cols, loc="center", cellLoc="left")
    t.auto_set_font_size(False)
    t.set_fontsize(8)
    t.scale(1, 1.4)
    ax.set_title("Gated modal-ban events: committed top-1 per family (* = equals the realised modal label)",
                 fontsize=9)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIGS / f"forecast_table.{ext}", dpi=150)
    plt.close(fig)


def avoidance_heatmap() -> None:
    an = read_json(RESULTS / "analysis.json")
    arms = ["oneshot", "persistent", "iter1", "iter2", "iter3", "sham", "nonce", "novelty", "rand1", "rand2", "rand3",
            "bandpatch", "ban"]
    pt = an["descriptives"]["per_task_arm"]
    M = np.full((len(TASK_ORDER), len(arms)), np.nan)
    for i, t in enumerate(TASK_ORDER):
        for j, a in enumerate(arms):
            v = pt.get(t, {}).get(a)
            if v and v.get("avoidance") is not None:
                M[i, j] = v["avoidance"]
    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(M, cmap="magma", vmin=0, vmax=1, aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            if not np.isnan(M[i, j]):
                ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", fontsize=6.5,
                        color="white" if M[i, j] < 0.6 else "black")
    ax.set_xticks(range(len(arms)))
    ax.set_xticklabels(arms, rotation=45, ha="right")
    ax.set_yticks(range(len(TASK_ORDER)))
    ax.set_yticklabels(TASK_ORDER)
    fig.colorbar(im, ax=ax, label="avoidance of D among attempted programs")
    ax.set_title("How far each push moves the model off its default (blank = no attempted program)", fontsize=9)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIGS / f"avoidance_by_arm.{ext}", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    logscores()
    forecast_table()
    avoidance_heatmap()
    print("extra figures written")
