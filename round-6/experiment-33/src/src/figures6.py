#!/usr/bin/env python3
"""Figures (PDF + PNG, house style of the aii-data-fig-gen skill):
fig1 pt support per task before (exp28) and after the few-shot top-up (correct, non-default correct, valid);
fig2 per push unit: q_base / q_tail / q_lik and the pooled landing composition;
fig3 per-event log-score differences (base - tail, base - lik) with the BCa 95% CI of the mean;
fig4 pt label-audit agreement per task, iteration 5 (exp28) vs iteration 6."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import ALL_TASKS, E28_RESULTS, FIG_DIR, PRED_DIR, PUSH_TASKS6, RESULTS_DIR, read_json

# house style of the aii-data-fig-gen skill when its scripts folder is given (optional; plain matplotlib otherwise)
SKILL = Path(os.environ.get("AII_DATA_FIG_GEN_SCRIPTS", "")) if os.environ.get("AII_DATA_FIG_GEN_SCRIPTS") else None
if SKILL is not None and SKILL.exists():
    sys.path.insert(0, str(SKILL))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    from chart_style import PALETTE, apply_house_style, clear_legends_of_data, fit_legends, fit_tick_labels, fit_titles
    apply_house_style()
    HOUSE = True
except Exception:  # noqa: BLE001 - the skill is optional at re-run time
    PALETTE = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#000000"]
    HOUSE = False


def finish(fig, name: str, titles: bool = True) -> None:
    if HOUSE:
        steps = (fit_legends, clear_legends_of_data, fit_tick_labels) + ((fit_titles,) if titles else ()) \
            + (clear_legends_of_data,)
        for f in steps:
            try:
                f(fig)
            except Exception:  # noqa: BLE001
                pass
    fig.savefig(FIG_DIR / f"{name}.pdf")
    fig.savefig(FIG_DIR / f"{name}.png", dpi=200)
    plt.close(fig)


def fig1() -> None:
    pr = read_json(RESULTS_DIR / "pt_repertoire.json")["units"]
    tasks = list(ALL_TASKS)
    old_c = [pr[t]["by_source"]["exp28_chat"]["correct"] + pr[t]["by_source"]["exp28_plain"]["correct"] for t in tasks]
    new_c = [pr[t]["n_correct_pooled"] for t in tasks]
    old_nd = [pr[t]["by_source"]["exp28_chat"]["correct_nondefault_catalogue"]
              + pr[t]["by_source"]["exp28_plain"]["correct_nondefault_catalogue"] for t in tasks]
    new_nd = [old_nd[i] + pr[t]["by_source"]["fewshot"]["correct_nondefault_catalogue"] for i, t in enumerate(tasks)]
    x = np.arange(len(tasks))
    fig, ax = plt.subplots(figsize=(7.0, 3.4), layout="constrained")
    w = 0.2
    ax.bar(x - 1.5 * w, old_c, w, label="correct, exp28 (chat + plain)", color=PALETTE[5])
    ax.bar(x - 0.5 * w, new_c, w, label="correct, + few-shot", color=PALETTE[0])
    ax.bar(x + 0.5 * w, old_nd, w, label="non-default correct, exp28", color=PALETTE[6])
    ax.bar(x + 1.5 * w, new_nd, w, label="non-default correct, + few-shot", color=PALETTE[1])
    ax.axhline(20, color="0.3", ls="--", lw=0.8)
    ax.set_xticks(x, tasks)
    ax.set_ylabel("pt programs")
    ax.set_title("Base-model support per task (dashed: the 20-correct floor)")
    ax.legend(fontsize=7, ncol=2)
    finish(fig, "fig1_pt_support")


def fig2() -> None:
    fc = read_json(PRED_DIR / "forecasts_G6.json")["units"]
    ev = read_json(RESULTS_DIR / "events_G6.json")["pooled"]
    units = [t for t in PUSH_TASKS6 if fc[t]["D"] is not None]
    fig, axes = plt.subplots(2, 4, figsize=(9.0, 4.6), layout="constrained")
    for ax, t in zip(axes.flat, units):
        u = fc[t]
        nd = u["nondef"] + ["other"]
        comp = {m: 0 for m in nd}
        for e in ev:
            if e["unit"] == t:
                for m, c in (e.get("composition") or {}).items():
                    comp[m] = comp.get(m, 0) + c
                comp["other"] += e.get("n_correct_other") or 0
        tot = sum(comp.values())
        rows = {"q_base": u["q_base"], "q_tail": u["q_tail"], "q_lik": u["q_lik"] or {m: 1 / len(nd) for m in nd},
                "landings": {m: comp[m] / tot for m in nd} if tot else {m: 0 for m in nd}}
        left = np.zeros(len(rows))
        for i, m in enumerate(nd):
            vals = [rows[k].get(m, 0.0) for k in rows]
            ax.barh(range(len(rows)), vals, left=left, color=PALETTE[i % len(PALETTE)], label=m)
            left += np.array(vals)
        ax.set_yticks(range(len(rows)), list(rows))
        ax.set_xlim(0, 1)
        ax.set_title(f"{t}: D={u['D']}, n={tot}", fontsize=7)
        ax.legend(fontsize=4.5, loc="lower right", framealpha=0.85)
    for ax in list(axes.flat)[len(units):]:
        ax.axis("off")
    fig.suptitle("Forecast distributions vs pooled landing composition (non-default algorithms + other)", fontsize=9)
    finish(fig, "fig2_compositions", titles=False)


def fig3() -> None:
    l1 = read_json(RESULTS_DIR / "l1_contest.json")["primary_pooled"]
    tab = l1.get("logscore_table") or []
    if not tab:
        return
    fig, ax = plt.subplots(figsize=(6.5, 3.4), layout="constrained")
    for j, (b, col, name) in enumerate((("q_tail", PALETTE[0], "base - tail"), ("q_lik", PALETTE[3], "base - lik (norm)"))):
        d = [r["q_base"] - r[b] for r in tab if r.get(b) is not None]
        lab = [f"{r['unit']}:{r['nudge']}" for r in tab if r.get(b) is not None]
        y = np.arange(len(d)) + j * 0.25
        ax.scatter(d, y, color=col, s=14, label=name, zorder=3)
        key = "base_vs_tail" if b == "q_tail" else "base_vs_lik_norm"
        c = l1["logscore_contests"][key]["bca95"]
        if c.get("lo") is not None:
            ax.axvspan(c["lo"], c["hi"], color=col, alpha=0.12)
            ax.axvline(c["mean"], color=col, lw=1)
        ax.set_yticks(np.arange(len(d)), lab, fontsize=7)
    ax.axvline(0, color="0.3", lw=0.8)
    ax.set_xlabel("per-event mean log-score difference (nats; > 0 favours q_base)")
    ax.set_title("Log-score contest per event (bands: BCa 95% CI of the mean)")
    ax.legend(fontsize=7)
    finish(fig, "fig3_logscore_diffs")


def fig4() -> None:
    a6 = read_json(RESULTS_DIR / "pt_label_audit6.json")
    a5 = read_json(E28_RESULTS / "pt_label_audit.json")
    tasks = list(ALL_TASKS)
    v6 = [(a6.get("round1", {}).get("per_task", {}).get(t) or {}).get("agree_raw") for t in tasks]
    v6b = [(a6.get("round2", {}).get("per_task", {}).get(t) or {}).get("agree_raw") if a6.get("round2") else None
           for t in tasks]
    v5 = [(a5.get("per_unit", {}).get(t) or {}).get("agree_adjudicated") for t in tasks]
    x = np.arange(len(tasks))
    fig, ax = plt.subplots(figsize=(7.0, 3.2), layout="constrained")
    ax.bar(x - 0.25, [v if v is not None else 0 for v in v5], 0.25, label="iteration 5 (exp28)", color=PALETTE[5])
    ax.bar(x, [v if v is not None else 0 for v in v6], 0.25, label="iteration 6, round 1", color=PALETTE[0])
    if any(v is not None for v in v6b):
        ax.bar(x + 0.25, [v if v is not None else 0 for v in v6b], 0.25, label="iteration 6, revision re-audit",
               color=PALETTE[2])
    ax.axhline(0.8, color="0.3", ls="--", lw=0.8)
    ax.set_xticks(x, tasks)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("labeller = adjudicated")
    ax.set_title("pt label audit: agreement with the two-family adjudication (dashed: 0.8 gate)")
    ax.legend(fontsize=7)
    finish(fig, "fig4_audit_agreement")


def main() -> None:
    FIG_DIR.mkdir(exist_ok=True)
    for f in (fig1, fig2, fig3, fig4):
        try:
            f()
            print(f"{f.__name__} ok")
        except Exception as e:  # noqa: BLE001 - one broken figure must not block the others
            print(f"{f.__name__} failed: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
