#!/usr/bin/env python3
"""Figures (PDF + PNG) from results/*.json. Spec-driven figures go through the aii-data-fig-gen generator
(chart_gen.py); the forest plot with asymmetric bootstrap intervals and the unit diagnostics are hand-written
matplotlib in the same house style (chart_style.apply_house_style)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import ALL_TASKS, FIG_DIR, PRED_DIR, RESULTS_DIR, ROOT, read_json, write_json

# aii-data-fig-gen renderer scripts (chart_gen.py, chart_style.py): AII_DATA_FIG_GEN_SCRIPTS, else the optional unpublished
# paths.local.json key 'fig_gen_scripts'. Without them the figure specs (figures/*.json) are still written.
_LOCAL = ROOT / "paths.local.json"
SKILL = Path(os.environ.get("AII_DATA_FIG_GEN_SCRIPTS") or
             (json.loads(_LOCAL.read_text()).get("fig_gen_scripts", "") if _LOCAL.exists() else "") or "missing")
GEN = SKILL / "chart_gen.py"


def render(spec: dict[str, Any], name: str) -> None:
    p = FIG_DIR / f"{name}.json"
    write_json(p, spec)
    if not GEN.exists():
        print(f"{name}: spec written; renderer not found (set AII_DATA_FIG_GEN_SCRIPTS)")
        return
    r = subprocess.run([sys.executable, str(GEN), "--spec", str(p), "--out", str(FIG_DIR / name)],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        print(f"{name} failed: {r.stderr[-800:]}")
    else:
        print(f"{name} ok")


def fig1(c3a: dict[str, Any]) -> None:
    pr = c3a["primary"]
    tasks = pr["tasks"]
    groups = {("movable", 1): [], ("movable", 0): [], ("immovable", 1): [], ("immovable", 0): []}
    for t in tasks:
        groups[("movable" if pr["movable"][t] else "immovable", pr["C_t"][t])].append(t)
    series = []
    for (m, c), ts in groups.items():
        if ts:
            series.append({"label": f"{'movable' if m == 'movable' else 'immovable'} / {'obeys' if c else 'fails'}",
                           "x": [pr["E_t"][t] for t in ts], "values": [pr["A_t"][t] for t in ts]})
    ba = pr["balanced_accuracy"]["BA"]
    title = (f"E_t vs ban avoidance (BA={ba if ba is None else round(ba, 2)}, "
             f"Fisher p={pr['fisher']['p_two_sided']:.3g}, rho={pr['spearman']['rho'] if pr['spearman']['rho'] is None else round(pr['spearman']['rho'], 2)})")
    write_json(FIG_DIR / "fig1_caption.json", {"caption": title})
    render({"type": "scatter", "title": "Escape share vs ban avoidance (15 tasks)", "xlabel": "E_t (escaping directions / 8)",
            "ylabel": "A_t (catalogue-only avoidance)", "aspect": "16:9", "width_in": 7.5, "series": series},
           "fig1_Et_vs_At")


def fig2(c3a: dict[str, Any], rivals: dict[str, Any]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    sys.path.insert(0, str(SKILL))
    import matplotlib.pyplot as plt
    from chart_style import apply_house_style

    apply_house_style()
    rows = [("E_t (primary)", c3a["primary"]["spearman"]["rho"], c3a["primary"]["bootstrap"]["rho_ci95"])]
    for nm, v in rivals.items():
        if v.get("rho_rival_sign_oriented") is None:
            continue
        rows.append((nm, v["rho_rival_sign_oriented"], None))
    fig, ax = plt.subplots(figsize=(6.5, 3.8), layout="constrained")
    for i, (nm, r, ci) in enumerate(rows):
        if r is None:
            continue
        ax.plot([r], [i], "o", color="#0072B2" if i == 0 else "#555555")
        if ci:
            ax.plot(ci, [i, i], "-", color="#0072B2")
    ax.axvline(0, color="#999999", ls="--", lw=1)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows])
    ax.set_xlabel("Spearman rho with A_t (sign-oriented)")
    ax.set_title("Ban-free predictors of ban compliance (E_t: 95% task-bootstrap CI)")
    fig.savefig(FIG_DIR / "fig2_rivals_forest.pdf")
    fig.savefig(FIG_DIR / "fig2_rivals_forest.png", dpi=200)
    plt.close(fig)
    print("fig2 ok")


def fig3(bans: dict[str, Any], c1: dict[str, Any]) -> None:
    tasks = [t for t in ALL_TASKS if t in bans]
    cats = []
    vals = {"default": [], "catalogue survivor": [], "other": [], "invalid/disputed": []}
    for t in tasks:
        arms = c1["per_task"].get(t, {}).get("arms", {})
        for arm in ("twin", "ban"):
            if arm == "ban":
                comp, n, D = bans[t]["composition"], bans[t]["n"], bans[t]["D"]
            elif arm in arms:
                comp = {}
                n = arms[arm]["n"]
                D = bans[t]["D"]
                comp = arms[arm].get("attempt_comp") or {}
                if not comp:
                    continue
            else:
                continue
            cats.append(f"{t}:{arm}")
            vals["default"].append(comp.get(D, 0) / n)
            vals["other"].append(comp.get("other", 0) / n)
            vals["invalid/disputed"].append((comp.get("invalid", 0) + comp.get("disputed", 0)) / n)
            vals["catalogue survivor"].append(1 - vals["default"][-1] - vals["other"][-1] - vals["invalid/disputed"][-1])
    render({"type": "bar", "stacked": True, "title": "Twin vs ban compositions per task",
            "xlabel": "task:arm", "ylabel": "share of attempts", "categories": cats,
            "series": [{"label": k, "values": v} for k, v in vals.items()], "aspect": "21:9", "width_in": 12.0},
           "fig3_compositions")


def fig4(c1: dict[str, Any]) -> None:
    series = []
    for t in c1["movable_tasks"]:
        arms = c1["per_task"][t]["arms"]
        for arm in ("pn_a1", "pn_a2", "t13", "novelty"):
            if arm in arms and arms[arm]["hill1_rarefied25"] is not None:
                pass
        pts = [(arms[a]["pass_cost_points"], arms[a]["hill1_rarefied25"]) for a in ("twin", "pn_a1", "pn_a2")
               if a in arms and arms[a]["hill1_rarefied25"] is not None]
        if len(pts) >= 2:
            series.append({"label": f"{t} PN", "x": [p[0] for p in pts], "values": [p[1] for p in pts]})
    if series:
        render({"type": "line", "title": "Correct-only Hill-1 (depth 25) vs pass cost, plan noise, movable tasks",
                "xlabel": "pass cost (points)", "ylabel": "Hill-1", "aspect": "16:9", "series": series},
               "fig4_hull_pn")


def fig5(c3b: dict[str, Any]) -> None:
    if "per_event" not in c3b:
        return
    cats, vals = [], []
    for t, v in c3b["per_event"].items():
        a = v["association"]["log_score"]
        for nm in ("push_landing", "opening_ladder"):
            if v[nm]["log_score"] is not None and a is not None:
                cats.append(f"{t}:{nm}")
                vals.append(v[nm]["log_score"] - a)
    if cats:
        render({"type": "diverging", "title": "C3b: log-score gain over the association forecast per gated event",
                "xlabel": "nats (ban-free forecast minus association)", "categories": cats,
                "series": [{"label": "gain", "values": vals}], "aspect": "4:3", "annotate": True, "fmt": "+.2f"},
               "fig5_c3b")


def fig6() -> None:
    q = read_json(RESULTS_DIR / "qwen_ratio.json")
    series = [{"label": "r_Q (plain, committed plan)", "x": [v["depth"] for v in q["r_Q"].values()],
               "values": [v["median"] for v in q["r_Q"].values()]},
              {"label": "r_Q,ox (outlier-excluded, primary)", "x": [v["depth"] for v in q["r_Q_ox"].values()],
               "values": [v["median"] for v in q["r_Q_ox"].values()]}]
    us = RESULTS_DIR / "unit_sensitivity.json"
    if us.exists():
        u = read_json(us)
        bb = u["by_block"]
        series.append({"label": "Gemma n_ban / n_banfree,ox (post-ban)", "x": [(int(l) + 1) / 34 for l in bb],
                       "values": [v["median_ratio_ban_over_ox"] for v in bb.values()]})
    render({"type": "line", "title": "Push-unit diagnostics by relative depth", "xlabel": "relative depth (l+1)/L",
            "ylabel": "ratio", "aspect": "16:9", "series": series}, "fig6_unit_diagnostics")


def main() -> None:
    c3a = read_json(RESULTS_DIR / "c3a.json")
    fig1(c3a)
    fig2(c3a, read_json(RESULTS_DIR / "rivals.json"))
    bans = read_json(RESULTS_DIR / "bans.json")
    c1 = read_json(RESULTS_DIR / "c1_prices.json")
    fig3(bans, c1)
    fig4(c1)
    fig5(read_json(RESULTS_DIR / "c3b.json"))
    fig6()


if __name__ == "__main__":
    main()
