#!/usr/bin/env python3
"""Figures F1-F6 (PDF + PNG) from the result files, via the aii-data-fig-gen generator where a type fits and the
skill's house style + legibility gates where a labelled scatter is needed.
F1 beta_u vs E_u (marker = unit kind, colour = K_u, parent-variant pairs joined)   [hand-written, house style]
F2 per-direction stage-1 excess heatmap (rows = units, cols = direction x alpha)    [heatmap]
F3 base composition vs push landing over survivors, per movable new unit             [panel of bar]
F4 rival predictors vs E_u, small multiples                                          [panel of scatter]
F5 within-parent delta-beta vs delta-E                                               [hand-written, house style]
F6 base Hill-1 vs PN Hill-1 per new unit                                             [dumbbell]
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg5 import FIG_DIR, RESULTS_DIR, read_json  # noqa: E402

SKILL = Path(os.environ.get("AII_DATA_FIG_GEN_SCRIPTS", str(Path.home() / ".claude" / "skills" / "aii-data-fig-gen" / "scripts")))
GEN = SKILL / "chart_gen.py"
SPECS = FIG_DIR / "specs"
SPECS.mkdir(parents=True, exist_ok=True)


def gen(name: str, spec: dict) -> None:
    p = SPECS / f"{name}.json"
    p.write_text(json.dumps(spec, indent=1))
    r = subprocess.run([sys.executable, str(GEN), "--spec", str(p), "--out", str(FIG_DIR / name)],
                       capture_output=True, text=True)
    print(name, "OK" if r.returncode == 0 else f"FAILED: {r.stderr[-800:]}")


def hand_scatter(name: str, pts: list[dict], xlabel: str, ylabel: str, title: str, lines: list[tuple] = ()) -> None:
    sys.path.insert(0, str(SKILL))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from chart_geometry import assert_text_is_legible, fit_point_labels
    from chart_style import (PALETTE, apply_house_style, assert_legends_clear_of_data, clear_legends_of_data,
                             fit_legends, fit_tick_labels, fit_titles, literal, place_legend, place_point_label)
    apply_house_style()
    fig, ax = plt.subplots(figsize=(6.5, 4.6), layout="constrained")
    kinds = {"new": ("o", "new unit"), "P_": ("s", "parent re-measure"), "V_": ("^", "disguised variant")}
    for (x0, y0, x1, y1) in lines:
        ax.plot([x0, x1], [y0, y1], color="0.6", linewidth=1, zorder=1)
    for ki, (k, (mk, lab)) in enumerate(kinds.items()):
        pp = [p for p in pts if p["kind"] == k]
        if not pp:
            continue
        ax.scatter([p["x"] for p in pp], [p["y"] for p in pp], marker=mk, s=46, color=PALETTE[ki],
                   label=literal(lab), zorder=3, edgecolors="black", linewidths=0.4)
    for p in pts:
        if p.get("label", True):
            place_point_label(ax, literal(p["name"]), (p["x"], p["y"]))
    ax.set_xlabel(literal(xlabel))
    ax.set_ylabel(literal(ylabel))
    ax.set_title(literal(title))
    place_legend(ax, loc="best")
    fit_legends(fig)
    clear_legends_of_data(fig)
    fit_tick_labels(fig)
    fit_titles(fig)
    clear_legends_of_data(fig)
    fit_point_labels(fig)
    assert_text_is_legible(fig)
    assert_legends_clear_of_data(fig)
    fig.savefig(FIG_DIR / f"{name}.pdf")
    fig.savefig(FIG_DIR / f"{name}.png", dpi=200)
    plt.close(fig)
    print(name, "OK")


def main() -> None:
    uo = {x["unit"]: x for x in read_json(RESULTS_DIR / "unit_outcomes.json")["units"]}
    ex = {}
    if (RESULTS_DIR / "unit_outcomes_extra.json").exists():
        ex = {x["unit"]: x for x in read_json(RESULTS_DIR / "unit_outcomes_extra.json")["units"]}
    preds = {p.stem: read_json(p) for p in (RESULTS_DIR.parent / "predictions" / "units").glob("*.json")}
    # F1
    pts, lines = [], []
    for u, pr in sorted(preds.items()):
        o = uo.get(u) or ex.get(u)
        if o is None or pr["base"]["beta_u"] is None:
            continue
        kind = u[:2] if u[:2] in ("P_", "V_") else "new"
        pts.append({"name": f"{u} K{pr['K_u']}" if kind == "new" else u, "x": pr["base"]["beta_u"], "y": o["E_u"],
                    "kind": kind, "label": kind == "new" or o["E_u"] > 0})
    for t in sorted({u[2:] for u in preds if u[:2] in ("P_", "V_")}):
        a = next((p for p in pts if p["name"].split()[0] == f"P_{t}"), None)
        b = next((p for p in pts if p["name"].split()[0] == f"V_{t}"), None)
        if a and b:
            lines.append((a["x"], a["y"], b["x"], b["y"]))
    hand_scatter("F1_beta_vs_E", pts, "base-model off-default share beta_u (correct programs)",
                 "escape fraction E_u (confirmed / 8, mean over alpha)",
                 "Base repertoire breadth vs push movability", lines)
    # F2
    rows, mat, cols = [], [], None
    for u in [k for k in sorted(uo) if k in preds]:
        cells = sorted(uo[u]["per_direction"], key=lambda c: (c["alpha"], c["seed"]))
        cols = cols or [f"a{int(c['alpha'])}-d{i % 8}" for i, c in enumerate(cells)]
        rows.append(u)
        mat.append([round(c["excess_stage1"], 2) if c["excess_stage1"] is not None else 0.0 for c in cells])
    gen("F2_escape_heatmap", {"type": "heatmap", "title": "Stage-1 excess off-default share per direction",
                              "xlabel": "alpha and direction index", "ylabel": "unit", "aspect": "16:9",
                              "cbar_label": "share minus twin share", "row_labels": rows, "col_labels": cols,
                              "matrix": mat})
    # F3
    panels = []
    for u in sorted(uo):
        o, pr = uo[u], preds.get(u)
        if not pr or not o["movable"] or not o["push_landing_composition"]:
            continue
        d = pr["default"]
        surv = [m for m in pr["catalogue"] if m != d]
        bc = {k: v for k, v in pr["base"]["correct_composition"].items() if k in surv}
        lc = o["push_landing_composition"]
        tb, tl = max(sum(bc.values()), 1), max(sum(lc.values()), 1)
        panels.append({"type": "bar", "title": f"{u} (default {d})", "ylabel": "share of off-default programs",
                       "categories": [s.replace("_", " ")[:24] for s in surv],
                       "series": [{"label": "base repertoire", "values": [bc.get(s, 0) / tb for s in surv]},
                                  {"label": "push landing", "values": [lc.get(s, 0) / tl for s in surv]}]})
    if panels:
        gen("F3_base_vs_landing", {"type": "panel", "title": "Base composition vs push landing (movable units)",
                                   "ncols": 2, "panels": panels})
    # F4
    a1 = read_json(RESULTS_DIR / "a1_panel.json")
    panels = []
    for name in ("R_modal", "R_margin", "R_merit_runtime", "R_novel"):
        vals = a1["rivals"].get(name, {}).get("values", {})
        us = [u for u in vals if u in uo]
        if len(us) < 3:
            continue
        panels.append({"type": "scatter", "title": f"rho {a1['rivals'][name]['rho_rival_E']:.2f}",
                       "xlabel": name, "ylabel": "E_u",
                       "series": [{"x": [vals[u] for u in us], "values": [uo[u]["E_u"] for u in us]}]})
    bu = [u for u in uo if preds.get(u) and preds[u]["base"]["beta_u"] is not None]
    panels.insert(0, {"type": "scatter", "title": f"rho {a1['primary']['rho']:.2f}", "xlabel": "beta_u",
                      "ylabel": "E_u", "series": [{"x": [preds[u]["base"]["beta_u"] for u in bu],
                                                   "values": [uo[u]["E_u"] for u in bu]}]})
    gen("F4_rivals_vs_E", {"type": "panel", "title": "Predictors of the escape fraction", "ncols": 3,
                           "panels": panels})
    # F5
    if (RESULTS_DIR / "variants.json").exists():
        v = read_json(RESULTS_DIR / "variants.json")
        pts = [{"name": p["parent"] + (" (default shift)" if p["default_shift"] else ""), "x": p["delta_beta"],
                "y": p["delta_E"], "kind": "V_"}
               for p in v["pairs"] if p["delta_beta"] is not None]
        if pts:
            hand_scatter("F5_within_parent", pts, "delta beta (variant minus parent)",
                         "delta E (variant minus parent)", "Within-parent wording change")
    # F6
    us = [u for u in sorted(uo) if uo[u]["repertoire"]["base_hill1_rarefied"] is not None
          and uo[u]["repertoire"]["pn_hill1_rarefied"] is not None]
    gen("F6_hill_base_vs_pn", {"type": "dumbbell", "title": "Correct-only Hill-1 (depth 25): base vs plan noise",
                               "xlabel": "rarefied Hill-1 (effective number of mechanisms)", "aspect": "16:9",
                               "categories": us,
                               "series": [{"label": "base repertoire",
                                           "values": [uo[u]["repertoire"]["base_hill1_rarefied"] for u in us]},
                                          {"label": "plan noise (PN)",
                                           "values": [uo[u]["repertoire"]["pn_hill1_rarefied"] for u in us]}]})


if __name__ == "__main__":
    main()
