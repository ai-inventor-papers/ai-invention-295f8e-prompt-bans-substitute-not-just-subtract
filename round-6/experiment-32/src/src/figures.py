#!/usr/bin/env python3
"""Figures (PDF + PNG in figures/), all drawn from the committed result files:
F0 behaviour (twin / ban / forced compositions), F1 gate (FVE_ref and cosine per position class, 0.6-0.8 band,
0.752 marked), F2 naming rates per condition x position (NLA, text-only NAME / PREDICT, swap, random; Wilson CIs),
F3 the NLA 'planned' distribution per task and condition, F4 generated-token naming curves, F5 causal dose-response
(Y-share and pass rate per cell), F6 geometry in actual layer-20 activation coordinates (READ states projected on
PC1/PC2 of the forced-prompt states, arrows twin->ban, twin->twin+delta_edit x1/x2/x4, DIM direction), F7 judge
agreement."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import CACHE_DIR, FIG_DIR, PRED_DIR, RESULTS_DIR, TASKS, TEMPLATE_IDS, read_json, read_jsonl

plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42,
                     "ps.fonttype": 42, "figure.dpi": 150})
PAL = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#999999", "#000000"]


def save(fig: Any, name: str) -> None:
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"{name}.pdf")
    fig.savefig(FIG_DIR / f"{name}.png", dpi=170)
    plt.close(fig)


def f0_behaviour() -> None:
    b = read_json(RESULTS_DIR / "behaviour.json")
    fig, axes = plt.subplots(2, 4, figsize=(13, 5.6))
    for ax, t in zip(axes.flat, TASKS):
        R = b["tasks"][t]
        conds = [("twin", R["twin"])] + ([("ban", R["ban"])] if R.get("ban") else []) + \
                ([("seed", R["seed"])] if R.get("seed") else [])
        labs = sorted({l for _, c in conds for l in c["attempted"]})
        x = np.arange(len(conds))
        bottom = np.zeros(len(conds))
        for i, l in enumerate(labs):
            vals = np.array([c["attempted"].get(l, 0) / c["n"] for _, c in conds])
            ax.bar(x, vals, bottom=bottom, color=PAL[i % len(PAL)], label=l, width=0.6)
            bottom += vals
        for j, (_, c) in enumerate(conds):
            ax.text(j, 1.02, f"pass {c['pass_rate']:.2f}", ha="center", fontsize=7)
        ax.set_xticks(x, [c for c, _ in conds])
        ax.set_ylim(0, 1.12)
        ax.set_title(f"{t}: default={R['default']}, Y*={R.get('Ystar')}", fontsize=8)
        ax.legend(fontsize=6, frameon=False, loc="lower right")
    fig.suptitle("Behaviour of Qwen2.5-7B-Instruct: attempted algorithm shares (N=50 per condition)")
    save(fig, "F0_behaviour")


def f1_gate() -> None:
    g = read_json(RESULTS_DIR / "gate.json")
    lc = read_json(RESULTS_DIR / "layer_convention.json")
    cls = [c for c in ("READ", "SPEC", "g1", "g2", "g4", "g8", "g16", "ALL") if c in g["classes"]]
    conv = lc["chosen"]
    refc = lc["conventions"][conv]
    names = ["ref:gate set"] + [f"ref:{k}" for k in ("fineweb", "leetcode", "general", "clrs_trace", "humanevalplus", "enamel")
                                if k in refc] + [f"task:{c}" for c in cls]
    fve = [refc["gate_set"]["fve_ref"]] + [refc[k]["fve_ref"] for k in ("fineweb", "leetcode", "general", "clrs_trace",
                                                                       "humanevalplus", "enamel") if k in refc] + \
          [g["classes"][c]["fve_ref"] for c in cls]
    cos = [refc["gate_set"]["cos_mean"]] + [refc[k]["cos_mean"] for k in ("fineweb", "leetcode", "general", "clrs_trace",
                                                                         "humanevalplus", "enamel") if k in refc] + \
          [g["classes"][c]["cos_mean"] for c in cls]
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
    x = np.arange(len(names))
    ax[0].axhspan(0.6, 0.8, color="#cfe8cf", alpha=0.6, label="paper's 0.6-0.8")
    ax[0].axhline(0.752, color="k", ls="--", lw=0.8, label="released 0.752")
    ax[0].axhline(0.5, color="#D55E00", ls=":", lw=0.8, label="FAIL < 0.50")
    ax[0].bar(x, fve, color=[PAL[0]] * (len(names) - len(cls)) + [PAL[1]] * len(cls))
    ax[0].set_xticks(x, names, rotation=60, ha="right", fontsize=7)
    ax[0].set_ylabel("FVE_ref (reference-set denominator)")
    ax[0].set_title(f"Instrument gate ({conv}); task verdict {g['verdict']}")
    ax[0].legend(fontsize=6, frameon=False)
    ax[1].bar(x, cos, color=[PAL[0]] * (len(names) - len(cls)) + [PAL[1]] * len(cls))
    ax[1].set_xticks(x, names, rotation=60, ha="right", fontsize=7)
    ax[1].set_ylabel("mean cos(AR(explanation), state)")
    ax[1].set_ylim(0, 1)
    ax[1].set_title(f"FVE_ref hs20 {lc['fve_ref_hs20']:.3f} vs hs21 {lc['fve_ref_hs21']:.3f}")
    save(fig, "F1_gate")


def f2_naming() -> None:
    r = read_json(RESULTS_DIR / "readout.json")
    tab = r["naming_table"]
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
    conds = [c for c in ("twin", "ban", "forced", "seed", "rand") if c in tab]
    pos = ["SPEC-3", "SPEC-2", "SPEC-1", "READ"]
    w = 0.8 / max(1, len(conds))
    for i, c in enumerate(conds):
        xs, ys, lo, hi = [], [], [], []
        for j, p in enumerate(pos):
            if p in tab[c] and tab[c][p]["n"]:
                v = tab[c][p]
                xs.append(j + i * w)
                ys.append(v["rate"])
                lo.append(v["rate"] - v["wilson95"][0])
                hi.append(v["wilson95"][1] - v["rate"])
        ax[0].bar(xs, ys, width=w, yerr=[lo, hi], capsize=2, color=PAL[i], label=c)
    ax[0].set_xticks(np.arange(len(pos)) + 0.4 - w / 2, pos)
    ax[0].set_ylabel("NLA names its target (majority of 3)")
    ax[0].set_title("Targets: twin->default, ban/rand->Y*, forced->forced Y")
    ax[0].legend(fontsize=7, frameon=False)
    blocks = [("N1 ban: NLA", r["N1"]["x_rate"]), ("N1 ban: text NAME", r["N1"]["y_rate"]),
              ("ban: PREDICT", r["N1_predict"]["y_rate"]), ("twin (swap)", r["N1_swap"]["y_rate"]),
              ("random state", r["N1_rand"]["y_rate"]), ("N2 twin: NLA", r["N2_default"]["x_rate"]),
              ("N2 twin: text NAME", r["N2_default"]["y_rate"])]
    xs = np.arange(len(blocks))
    ys = [b["rate"] or 0 for _, b in blocks]
    err = [[(b["rate"] or 0) - (b["wilson95"][0] or 0) for _, b in blocks],
           [(b["wilson95"][1] or 0) - (b["rate"] or 0) for _, b in blocks]]
    ax[1].bar(xs, ys, yerr=err, capsize=3, color=[PAL[1], PAL[7], PAL[7], PAL[5], PAL[3], PAL[0], PAL[7]])
    ax[1].set_xticks(xs, [n for n, _ in blocks], rotation=40, ha="right", fontsize=7)
    ax[1].set_ylabel("rate (Wilson 95% CI)")
    ax[1].set_title(f"N1 effect {r['N1']['effect']:.2f} (b={r['N1']['b']}, c={r['N1']['c']}, p={r['N1']['p']:.3g})")
    save(fig, "F2_naming")


def f3_distribution() -> None:
    r = read_json(RESULTS_DIR / "readout.json")
    dist = r["planned_distribution"]
    keys = sorted(dist)
    labs = sorted({l for k in keys for l in dist[k]}, key=lambda s: (s in ("none_named", "other", "unresolved"), s))
    M = np.array([[dist[k].get(l, 0) / max(1, sum(dist[k].values())) for l in labs] for k in keys])
    fig, ax = plt.subplots(figsize=(max(6, 0.45 * len(labs) + 3), 0.28 * len(keys) + 1.5))
    im = ax.imshow(M, aspect="auto", cmap="viridis", vmin=0, vmax=1)
    ax.set_yticks(range(len(keys)), keys, fontsize=6)
    ax.set_xticks(range(len(labs)), labs, rotation=60, ha="right", fontsize=6)
    fig.colorbar(im, ax=ax, label="share of explanations")
    ax.set_title("What the NLA says is planned (resolved judge label), per task | condition")
    save(fig, "F3_planned_distribution")


def f4_gen() -> None:
    r = read_json(RESULTS_DIR / "readout.json")
    cur = {c: v for c, v in r["N5_gen"]["curves_pre_identifying"].items()
           if any(v[f"g{g}"]["nla"]["n"] for g in (1, 2, 4, 8, 16))}  # forced: no pre-identifying position exists
    fig, axes = plt.subplots(1, max(1, len(cur)), figsize=(4 * max(1, len(cur)), 3.2), squeeze=False)
    for ax, (cond, c) in zip(axes[0], cur.items()):
        gs = [1, 2, 4, 8, 16]
        for i, (k, lab) in enumerate((("nla", "NLA"), ("text_name", "text NAME"), ("text_predict", "PREDICT"))):
            ys = [c[f"g{g}"][k]["rate"] if c[f"g{g}"][k]["n"] else np.nan for g in gs]
            ns = [c[f"g{g}"][k]["n"] for g in gs]
            ax.plot(gs, ys, marker="o", color=PAL[i], label=lab)
            for g, y, n in zip(gs, ys, ns):
                if n and k == "nla":
                    ax.text(g, (y if np.isfinite(y) else 0) + 0.03, str(n), fontsize=6, ha="center")
        ax.set_xscale("log", base=2)
        ax.set_xticks(gs, [f"g{g}" for g in gs])
        ax.set_ylim(0, 1.05)
        ax.set_title(f"{cond}: names the realised label (pre-identifying positions; n on NLA points)", fontsize=8)
        ax.legend(fontsize=6, frameon=False)
    save(fig, "F4_generated_curves")


def f5_causal() -> None:
    p = RESULTS_DIR / "causal.json"
    if not p.exists():
        return
    c = read_json(p)
    tasks = list(c["tasks"])
    if not tasks:
        return
    fig, axes = plt.subplots(len(tasks), 2, figsize=(11, 3 * len(tasks)), squeeze=False)
    for i, t in enumerate(tasks):
        T = c["tasks"][t]
        for kind, col in (("EDIT", PAL[3]), ("RT", PAL[7]), ("UNREL", PAL[5]), ("RAND", PAL[0]), ("DIM", PAL[2])):
            xs, ys, ps = [], [], []
            for d in (1, 2, 4):
                cell = T["cells"].get(f"PRE_{kind}_x{d}")
                if cell:
                    xs.append(d)
                    ys.append(cell["Y_share"]["rate"])
                    ps.append(cell["pass_rate"]["rate"])
            if xs:
                axes[i][0].plot(xs, ys, marker="o", color=col, label=kind)
                axes[i][1].plot(xs, ps, marker="o", color=col, label=kind)
        y0 = T["C0"]["Y_share"]["rate"]
        axes[i][0].axhline(y0, color="k", ls=":", lw=0.8, label="C0 (twin)")
        axes[i][1].axhline(T["C0"]["pass_rate"]["rate"], color="k", ls=":", lw=0.8)
        ceil = T.get("prompting_ceiling_forced_adherence")
        if ceil is not None:
            axes[i][0].axhline(ceil, color=PAL[4], ls="--", lw=0.8, label="prompting ceiling")
        for ax in axes[i]:
            ax.set_xscale("log", base=2)
            ax.set_xticks([1, 2, 4], ["x1", "x2", "x4"])
            ax.set_ylim(-0.02, 1.02)
        axes[i][0].set_ylabel(f"{t}: Y-share ({T['Y']})")
        axes[i][1].set_ylabel("pass rate")
        axes[i][0].legend(fontsize=6, frameon=False, ncol=2)
        axes[i][0].set_title(f"{t}: default {T['default']} -> Y {T['Y']}; PASS={T['pass']}", fontsize=8)
    save(fig, "F5_causal_dose_response")


def f6_geometry() -> None:
    idx = read_jsonl(CACHE_DIR / "states_index.jsonl")
    z = np.load(CACHE_DIR / "states_L20.npz")
    conv = read_json(RESULTS_DIR / "layer_convention.json")["chosen"]
    H = z["H20"] if conv == "hs20" else z["H21"]
    c1 = read_json(PRED_DIR / "commit1_defaults.json")
    beh = read_json(RESULTS_DIR / "behaviour.json")
    deltas = {}
    dp = CACHE_DIR / "deltas.npz"
    if dp.exists():
        dz = np.load(dp)
        deltas = {k.replace("__", "|"): dz[k] for k in dz.files}
    fig, axes = plt.subplots(2, 4, figsize=(15, 7.4))
    for ax, t in zip(axes.flat, TASKS):
        rows = [r for r in idx if r.get("task") == t and r["kind"] == "PREFILL" and r["position"] == "READ"]
        forced = [r for r in rows if r["condition"] == "forced"]
        if len(forced) < 3:
            ax.set_visible(False)
            continue
        F = H[[r["row"] for r in forced]]
        mu = F.mean(0)
        U, S, Vt = np.linalg.svd(F - mu, full_matrices=False)
        pcs = Vt[:2]
        ve = (S[:2] ** 2) / (S ** 2).sum()
        proj = lambda X: (np.atleast_2d(X) - mu) @ pcs.T
        modes = sorted({r["mode"] for r in forced})
        for i, m in enumerate(modes):
            P = proj(H[[r["row"] for r in forced if r["mode"] == m]])
            adh = beh["tasks"][t]["forced"].get(m, {}).get("adherence")
            ax.scatter(P[:, 0], P[:, 1], s=16, color=PAL[i % len(PAL)], alpha=0.8,
                       label=f"forced {m} (adh {adh:.2f})" if adh is not None else f"forced {m}")
            ax.scatter(*P.mean(0), s=70, color=PAL[i % len(PAL)], marker="*", edgecolor="k", lw=0.4)
        tw = {r["template"]: r for r in rows if r["condition"] == "twin"}
        bn = {r["template"]: r for r in rows if r["condition"] == "ban"}
        Pt = proj(H[[tw[w]["row"] for w in TEMPLATE_IDS if w in tw]])
        ax.scatter(Pt[:, 0], Pt[:, 1], s=34, color="k", marker="o", label="twin")
        if bn:
            Pb = proj(H[[bn[w]["row"] for w in TEMPLATE_IDS if w in bn]])
            ax.scatter(Pb[:, 0], Pb[:, 1], s=34, color="k", marker="x", label=f"ban {c1['tasks'][t]['default']}")
            for a, b in zip(Pt, Pb):
                ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="->", color="#555555", lw=0.7))
        sd = [r for r in rows if r["condition"] == "seed"]
        if sd:
            Ps = proj(H[[r["row"] for r in sd]])
            ax.scatter(Ps[:, 0], Ps[:, 1], s=30, color=PAL[6], marker="D", edgecolor="k", lw=0.3, label="seed")
        rd = [r for r in idx if r.get("task") == t and r["kind"] == "RAND" and r["position"] == "READ"]
        if rd:
            Pr = proj(H[[r["row"] for r in rd]])
            ax.scatter(Pr[:, 0], Pr[:, 1], s=22, color=PAL[3], marker="+", label="twin+eps")
        for j, w in enumerate(TEMPLATE_IDS):
            k = f"EDIT|{t}|TWIN|{w}|READ"
            if k in deltas and w in tw:
                h = H[tw[w]["row"]]
                for d, ls in ((1, ":"), (2, "--"), (4, "-")):
                    a, b = proj(h)[0], proj(h + d * deltas[k])[0]
                    ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="->", color=PAL[4], lw=0.9, ls=ls))
            kd = f"DIM|{t}|TWIN|{w}|READ"
            if kd in deltas and w in tw and j == 0:
                h = H[tw[w]["row"]]
                a, b = proj(h)[0], proj(h + 4 * deltas[kd])[0]
                ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="-|>", color=PAL[2], lw=1.2))
        ax.set_xlabel(f"PC1 ({ve[0] * 100:.0f}% of forced-state var.; residual units)")
        ax.set_ylabel(f"PC2 ({ve[1] * 100:.0f}%)")
        ax.set_title(f"{t} layer-20 READ states ({conv})", fontsize=8)
        ax.legend(fontsize=5, frameon=False, loc="best")
    fig.suptitle("Activation-space geometry: READ states projected on the forced-prompt PCs; purple arrows = NLA edit "
                 "deltas x1 (dotted) / x2 (dashed) / x4 (solid); green = DIM x4; grey = twin -> ban", fontsize=9)
    save(fig, "F6_geometry")


def f7_judges() -> None:
    r = read_json(RESULTS_DIR / "readout.json")
    ag = r.get("judge_agreement", {})
    if not ag:
        return
    fig, ax = plt.subplots(figsize=(5, 3))
    modes = list(ag)
    ax.bar(np.arange(len(modes)) - 0.2, [ag[m]["raw_agreement"] for m in modes], width=0.4, label="raw agreement")
    ax.bar(np.arange(len(modes)) + 0.2, [ag[m]["kappa_J1_J2"] or 0 for m in modes], width=0.4, label="Cohen's kappa")
    ax.set_xticks(range(len(modes)), [f"{m}\n(n={ag[m]['n']})" for m in modes])
    ax.set_ylim(0, 1)
    ax.legend(fontsize=7, frameon=False)
    ax.set_title("J1 vs J2 agreement on 'planned' / 'predicted'")
    save(fig, "F7_judges")


def f8_mds() -> None:
    """Classical MDS of the layer-20 READ centroids: forced 'Implement m' centroids (marker area = how many twin
    programs implemented m; outline = how many ban programs did), the twin and the ban centroids."""
    g = read_json(RESULTS_DIR / "geometry.json")
    fig, axes = plt.subplots(2, 4, figsize=(15, 7))
    for ax, t in zip(axes.flat, TASKS):
        T = g["tasks"].get(t)
        if not T or "mds" not in T.get("READ", {}):
            ax.set_visible(False)
            continue
        M = T["READ"]["mds"]
        it, ib = T["implemented_twin"], T["implemented_ban"]
        for i, (n, (x, y)) in enumerate(M.items()):
            if n in ("twin", "ban"):
                ax.scatter(x, y, s=90, marker="o" if n == "twin" else "X", color="k", zorder=3)
                ax.annotate(n, (x, y), textcoords="offset points", xytext=(5, 5), fontsize=8, weight="bold")
                continue
            a = it.get(n, 0)
            b = ib.get(n, 0)
            ax.scatter(x, y, s=40 + 18 * a, color=PAL[i % len(PAL)], alpha=0.75, edgecolor="none")
            if b:
                ax.scatter(x, y, s=40 + 18 * b, facecolor="none", edgecolor="k", lw=1.2, ls="--")
            ax.annotate(f"{n}\ntwin {a} / ban {b}", (x, y), textcoords="offset points", xytext=(6, -10), fontsize=6)
        if "ban" in M and "twin" in M:
            ax.annotate("", xy=M["ban"], xytext=M["twin"], arrowprops=dict(arrowstyle="->", color="#555555", lw=1.2))
        ax.set_title(f"{t} (default {T['default']}); ban contrast -> {T['READ'].get('ban_contrast_mode')}", fontsize=8)
        ax.set_xlabel("MDS 1 (residual units)")
        ax.set_ylabel("MDS 2")
    fig.suptitle("Layer-20 READ geometry: classical MDS of forced-algorithm centroids; filled area = twin implemented "
                 "count, dashed ring = implemented count under the ban; arrow = twin -> ban centroid", fontsize=9)
    save(fig, "F8_mds_centroids")


def f9_gen_dose() -> None:
    """EXPLORATORY: Y-share vs dose at the generated-token site (READ + generated positions 1-64), CRN slots 0-5
    (x8 pooled with the replication on slots 6-9 where available)."""
    c = read_json(RESULTS_DIR / "causal.json")
    f = read_json(RESULTS_DIR / "causal_exploratory_followup.json")
    tasks = list(f["tasks"])
    fig, axes = plt.subplots(1, len(tasks), figsize=(4.2 * len(tasks), 3.6), squeeze=False)
    for ax, t in zip(axes[0], tasks):
        F = f["tasks"][t]["cells"]
        C = c["tasks"][t]["cells"]
        def ys(kind):
            xs, vals, pr = [], [], []
            for d in (1, 2, 4, 8, 16):
                cell = None
                if d in (1, 2) and f"GEN_{kind}_x{d}" in C:
                    v = C[f"GEN_{kind}_x{d}"]
                    cell = (v["Y_share"]["rate"], v["pass_rate"]["rate"])
                for nm in (f"EXP2_GEN_{kind}_x{d}", f"EXP_GEN_{kind}_x{d}"):
                    if cell is None and nm in F:
                        cell = (F[nm]["Y_share"], F[nm]["pass_rate"])
                if d == 8 and kind in ("EDIT", "RAND") and f"pooled_GEN_{kind}_x8_vs_C0" in f["tasks"][t]:
                    cell = (f["tasks"][t][f"pooled_GEN_{kind}_x8_vs_C0"]["Y_share"], cell[1] if cell else None)
                if cell is not None:
                    xs.append(d); vals.append(cell[0]); pr.append(cell[1])
            return xs, vals, pr
        for kind, col in (("EDIT", PAL[3]), ("RAND", PAL[0]), ("DIM", PAL[2])):
            xs, vals, pr = ys(kind)
            if xs:
                ax.plot(xs, vals, marker="o", color=col, label=f"GEN {kind}")
                for x_, y_, p_ in zip(xs, vals, pr):
                    if p_ is not None and p_ < 0.8:
                        ax.annotate(f"pass {p_:.2f}", (x_, y_), textcoords="offset points", xytext=(4, 4), fontsize=6, color=col)
        for nm, mk, lab in (("EXP2_GEN_UNREL_x8", "s", "unrelated edit x8"), ("EXP2_GEN_RTM_x8", "^", "round trip (matched) x8")):
            if nm in F:
                ax.scatter([8], [F[nm]["Y_share"]], marker=mk, color=PAL[5] if mk == "s" else PAL[7], zorder=3, label=lab)
        ax.axhline(c["tasks"][t]["C0"]["Y_share"]["rate"], color="k", ls=":", lw=0.8, label="C0 (twin)")
        ax.set_xscale("log", base=2)
        ax.set_xticks([1, 2, 4, 8, 16], ["x1", "x2", "x4", "x8", "x16"])
        ax.set_ylim(-0.02, 1.02)
        ax.set_title(f"{t}: {c['tasks'][t]['default']} -> {c['tasks'][t]['Y']}", fontsize=8)
        ax.set_ylabel("Y-share (correct and labelled Y)")
        ax.legend(fontsize=5.5, frameon=False)
    fig.suptitle("EXPLORATORY: steering at READ + generated tokens 1-64 (x1/x2 pre-registered; x4-x16 exploratory; "
                 "x8 EDIT/RAND pooled over 50 CRN slots)", fontsize=9)
    save(fig, "F9_gen_site_dose_exploratory")


def main() -> None:
    for f in (f0_behaviour, f1_gate, f2_naming, f3_distribution, f4_gen, f5_causal, f6_geometry, f7_judges,
              f8_mds, f9_gen_dose):
        try:
            f()
            print("ok", f.__name__)
        except (FileNotFoundError, KeyError, ValueError, TypeError, IndexError) as e:
            print("skip", f.__name__, repr(e)[:200])


if __name__ == "__main__":
    main()
