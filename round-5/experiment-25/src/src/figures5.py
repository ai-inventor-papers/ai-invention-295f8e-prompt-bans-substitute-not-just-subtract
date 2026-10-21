#!/usr/bin/env python3
"""Figures (PDF + PNG). fig1 is hand-written with the aii-data-fig-gen house style (scatter with two-way error bars
and point names); fig2-fig5 are rendered by chart_gen.py from JSON specs (figures/specs/*.json).
fig1  beta_u against E_u (Wilson bars on beta, row-bootstrap 90% bars on E), unit names; existing tasks (Step 1 beta)
      as a second series
fig2  per-direction escape outcomes (unit x seed x alpha): excess over the twin at stage 1, and the cell outcome
fig3  twin / base / PN alpha 2 / confirmed-escape compositions per unit (default, base runner-up r_u, other catalogue
      modes, 'other' / unknown, invalid)
fig4  Extra arm A: E_t under the ban-free unit (this run) against iteration 4 (exp22 bench unit, ban unit)
fig5  rival scatter: each pre-registered predictor against E_u
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg5 import (ALPHAS, ESC_SEEDS, EXISTING, FIGS, NEW_UNITS, PRED, RESERVE_UNITS, RESULTS, read_json,  # noqa: E402
                  write_json)
from escape_rule import cell_decision, twin_stats  # noqa: E402

# chart_gen.py / chart_style.py / chart_geometry.py of the aii-data-fig-gen skill (not part of this repository); point
# AII_DATA_FIG_GEN_SCRIPTS at its scripts/ folder. The rendered figures and their JSON specs ship in figures/.
SKILL = Path(os.environ.get("AII_DATA_FIG_GEN_SCRIPTS",
                            str(Path(__file__).resolve().parents[1] / "vendor" / "aii-data-fig-gen" / "scripts")))
GEN = SKILL / "chart_gen.py"
SPECS = FIGS / "specs"
SPECS.mkdir(parents=True, exist_ok=True)
UNITS = [u for u in NEW_UNITS + RESERVE_UNITS if (PRED / f"unit_{u}.json").exists()]


def preds() -> dict:
    return {u: read_json(PRED / f"unit_{u}.json") for u in UNITS}


def render(name: str, spec: dict) -> None:
    p = SPECS / f"{name}.json"
    write_json(p, spec)
    r = subprocess.run([sys.executable, str(GEN), "--spec", str(p), "--out", str(FIGS / name)], capture_output=True,
                       text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{name}: {r.stderr[-1500:]}")


def e_boot(u: str, d: str, cat: list[str], n_boot: int = 500, seed: int = 11) -> tuple[float, float]:
    """90% interval of E_u under resampling of rows within the twin and within each escape cell (stage-1 and top-up
    slots resampled separately) -- the measurement bootstrap of the frozen analysis, per unit."""
    from analysis_a1a2 import labels, rows_of

    rows = labels(u)
    tw = rows_of(rows, "TWIN", "instruct")
    esc = rows_of(rows, prefix="ESC_", model="instruct")
    cells = [[r for r in esc if int(r["direction_seed"]) == s and abs(float(r["alpha"]) - a) < 1e-9]
             for s in ESC_SEEDS for a in ALPHAS]
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n_boot):
        twb = [tw[i] for i in rng.integers(0, len(tw), len(tw))]
        ts = twin_stats(twb, set(cat), d)
        conf = 0
        for c in cells:
            f = [r for r in c if int(r["slot"]) in (0, 1)]
            t = [r for r in c if int(r["slot"]) in (2, 3, 4, 5)]
            fb = [f[i] for i in rng.integers(0, len(f), len(f))] if f else []
            tb = [t[i] for i in rng.integers(0, len(t), len(t))] if t else []
            conf += cell_decision(fb + tb, ts, set(cat), d)["confirmed"]
        out.append(conf / len(cells))
    return float(np.percentile(out, 5)), float(np.percentile(out, 95))


def fig1(P: dict, summ: dict) -> dict:
    import matplotlib.pyplot as plt

    sys.path.insert(0, str(SKILL))
    from chart_geometry import assert_text_is_legible, fit_point_labels
    from chart_style import (apply_house_style, assert_legends_clear_of_data, clear_legends_of_data, fit_legends,
                             fit_tick_labels, fit_titles, literal, place_legend, place_point_label)

    apply_house_style()
    fig, ax = plt.subplots(figsize=(6.5, 4.2), layout="constrained")
    data = {}
    for u in UNITS:
        p = P[u]
        if p.get("status") != "OK":
            continue
        oc = summ[u]["outcome"]
        lo, hi = e_boot(u, p["default"], p["catalogue"])
        data[u] = {"beta": p["beta"], "beta_ci": p["beta_ci"], "E": oc["E"], "E_ci90": [lo, hi]}
    hs = read_json(RESULTS / "half_screen.json")["primary"]
    ex = [r for r in hs.get("rows", []) if r["kind"] == "existing"]
    ax.scatter([r["beta"] for r in ex], [r["E"] for r in ex], s=22, marker="s", color="0.65", zorder=2,
               label="existing tasks (Step 1 beta, ban-free E)")
    for kind, marker, lab in (("primary", "o", "new units, pre-registered (A1-A7)"),
                              ("ext", "D", "new units, reserve extension (A8, A9)")):
        us = [u for u in data if (u in NEW_UNITS) == (kind == "primary")]
        if not us:
            continue
        x = np.array([data[u]["beta"] for u in us])
        y = np.array([data[u]["E"] for u in us])
        xe = np.array([[x[i] - data[u]["beta_ci"][0], data[u]["beta_ci"][1] - x[i]] for i, u in enumerate(us)]).T
        ye = np.array([[max(0.0, y[i] - data[u]["E_ci90"][0]), max(0.0, data[u]["E_ci90"][1] - y[i])]
                       for i, u in enumerate(us)]).T
        ax.errorbar(x, y, xerr=xe, yerr=ye, fmt=marker, ms=6, capsize=2, lw=1, zorder=3, label=lab)
        for u, xi, yi in zip(us, x, y):
            place_point_label(ax, literal(u), (xi, yi))
    for t in ("T03", "T10"):
        r = next((r for r in ex if r["unit"] == t), None)
        if r:
            place_point_label(ax, literal(t), (r["beta"], r["E"]))
    ax.axvline(0.05, color="0.4", lw=0.8, ls=":", zorder=1)
    ax.set_xlabel("Base off-default share among correct programs (beta)")
    ax.set_ylabel("Escape fraction E (16 cells)")
    ax.set_title("Base repertoire breadth against push escapes")
    ax.set_xlim(-0.05, 1.0)
    ax.set_ylim(-0.08, 0.75)
    place_legend(ax, loc="upper right")
    fit_legends(fig)
    clear_legends_of_data(fig)
    fit_tick_labels(fig)
    fit_titles(fig)
    clear_legends_of_data(fig)
    fit_point_labels(fig)
    assert_text_is_legible(fig)
    assert_legends_clear_of_data(fig)
    fig.savefig(FIGS / "fig1.pdf")
    fig.savefig(FIGS / "fig1.png", dpi=200)
    plt.close(fig)
    write_json(SPECS / "fig1_data.json", {"units": data, "existing": ex})
    return data


def fig2(P: dict, summ: dict, xa: dict) -> None:
    cols = [f"{s - 95100}a{int(a)}" for a in ALPHAS for s in ESC_SEEDS]
    rows, mat, cat = [], [], []
    order = [u for u in UNITS if P[u].get("status") == "OK"] + ["T03", "T10", "T2", "T1", "T05", "T06"]
    for t in order:
        cells = summ[t]["escape_cells"] if t in summ else xa[t]["cells"]
        by = {(c["seed"], c["alpha"]): c for c in cells}
        rows.append(t)
        mat.append([round(by[(s, a)]["excess10"], 2) if by[(s, a)]["excess10"] is not None else 0.0
                    for a in ALPHAS for s in ESC_SEEDS])
        cat.append([("confirmed" if by[(s, a)]["confirmed"] else "screen pass" if by[(s, a)]["screen_pass"] else
                     "no escape") for a in ALPHAS for s in ESC_SEEDS])
    spec = {"type": "panel", "title": "Per-direction escape outcomes (direction seed - 95100, alpha)", "ncols": 1,
            "panels": [
                {"type": "heatmap", "title": "Off-default excess over the twin, stage 1 (10 rows)",
                 "xlabel": "Direction and alpha", "ylabel": "Unit / task", "cbar_label": "Excess share",
                 "row_labels": rows, "col_labels": cols, "matrix": mat},
                {"type": "catmap", "title": "Cell outcome under the two-stage rule",
                 "xlabel": "Direction and alpha", "ylabel": "Unit / task", "row_labels": rows, "col_labels": cols,
                 "matrix": cat}]}
    try:
        render("fig2", spec)
    except RuntimeError:
        spec["panels"][0]["annotate"] = False
        render("fig2", spec)


def comp_rows(u: str, P: dict, summ: dict) -> dict:
    from analysis_a1a2 import labels, rows_of

    p = P[u]
    d, r, cat = p["default"], p.get("r"), set(p["catalogue"])
    rows = labels(u)

    def bucket(lab: str) -> str:
        if lab == d:
            return "default"
        if r and lab == r:
            return "runner-up r_u"
        if lab in cat:
            return "other catalogue"
        if lab in ("invalid", "disputed"):
            return "invalid"
        return "other/unknown"
    out = {}
    conf = [(c["seed"], c["alpha"]) for c in summ[u]["escape_cells"] if c["confirmed"]]
    for arm, sel in (("twin", rows_of(rows, "TWIN", "instruct")),
                     ("base (correct)", [x for x in rows_of(rows, "BASE", "base") if x.get("passed")]),
                     ("PN alpha 2", rows_of(rows, "PN_a2.0", "instruct")),
                     ("confirmed escape cells", [x for x in rows_of(rows, prefix="ESC_", model="instruct")
                                                 if (int(x["direction_seed"]), float(x["alpha"])) in conf])):
        out[arm] = Counter(bucket(x["label"]) for x in sel)
    return out


def fig3(P: dict, summ: dict) -> None:
    keys = ["default", "runner-up r_u", "other catalogue", "other/unknown", "invalid"]
    units = [u for u in UNITS if P[u].get("status") == "OK"]
    comps = {u: comp_rows(u, P, summ) for u in units}
    panels = []
    for arm in ("twin", "base (correct)", "PN alpha 2", "confirmed escape cells"):  # panel titles
        us = [u for u in units if sum(comps[u][arm].values()) > 0]
        if not us:
            continue
        series = []
        for k in keys:
            vals = [comps[u][arm].get(k, 0) for u in us]
            if sum(vals) > 0:
                series.append({"label": k, "values": vals})
        panels.append({"type": "stacked_pct", "title": arm, "categories": us, "series": series})
    write_json(SPECS / "fig3_counts.json", {u: {a: dict(c) for a, c in v.items()} for u, v in comps.items()})
    render("fig3", {"type": "panel", "title": "Program compositions per unit", "ncols": 1, "aspect": "1:2",
                    "panels": panels})


def fig4(xa: dict) -> None:
    tasks = [t for t in EXISTING if t in xa]
    it4 = [round(float(np.mean(xa[t]["iter4_E1_E2"])), 3) for t in tasks]
    now = [round(float(xa[t]["E"] or 0.0), 3) for t in tasks]
    render("fig4", {"type": "dumbbell", "title": "Existing tasks: escape fraction, iteration 4 vs ban-free unit",
                    "xlabel": "Escape fraction E (mean of alpha 1 and 2)", "aspect": "4:3", "annotate": False,
                    "categories": tasks,
                    "series": [{"label": "iteration 4 (ban unit, 40 or 8 directions)", "values": it4},
                               {"label": "this run (ban-free unit, 8 directions)", "values": now}]})


def fig5(P: dict, summ: dict) -> None:
    units = [u for u in UNITS if P[u].get("status") == "OK"]
    E = [summ[u]["outcome"]["E"] for u in units]
    preds_ = [("beta", lambda p: p["beta"]),
              ("opening margin", lambda p: p["rivals"].get("opening_margin")),
              ("merit (runtime)", lambda p: p["rivals"].get("merit_runtime_min")),
              ("merit (length)", lambda p: p["rivals"].get("merit_length_min")),
              ("twin modal share", lambda p: p["rivals"].get("twin_modal_share")),
              ("novelty share", lambda p: p["rivals"].get("novelty_share"))]
    panels = []
    for name, get in preds_:
        xs = [get(P[u]) for u in units]
        ok = [i for i, x in enumerate(xs) if x is not None]
        panels.append({"type": "scatter", "title": name, "xlabel": name, "ylabel": "E",
                       "series": [{"x": [round(float(xs[i]), 4) for i in ok], "values": [E[i] for i in ok]}]})
    render("fig5", {"type": "panel", "title": "Predictors against the escape fraction (8 units)",
                    "ncols": 2, "aspect": "4:5", "panels": panels})


def main() -> None:
    P = preds()
    summ = read_json(RESULTS / "unit_summaries_with_extension.json")
    xa = read_json(RESULTS / "extra_arm_a.json")
    only = set(sys.argv[1:])
    for name, f in (("fig1", lambda: fig1(P, summ)), ("fig2", lambda: fig2(P, summ, xa)),
                    ("fig3", lambda: fig3(P, summ)), ("fig4", lambda: fig4(xa)), ("fig5", lambda: fig5(P, summ))):
        if only and name not in only:
            continue
        try:
            f()
            print(f"{name}: ok")
        except Exception as e:  # noqa: BLE001 - report and continue with the other figures
            print(f"{name}: FAILED {type(e).__name__}: {str(e)[:1200]}")


if __name__ == "__main__":
    main()
