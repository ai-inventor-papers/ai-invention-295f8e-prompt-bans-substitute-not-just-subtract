#!/usr/bin/env python3
"""Figures from results/*.json (matplotlib with the aii-data-fig-gen house style when available).

fig1 pass rate and correctness-conditioned Hill-1 against c per task, with random / placebo / breadth points;
fig2 label distributions per arm; fig3 TV to reference against delta Hill-1 per knob; fig4 commitment
coordinate kappa per condition with the ban-shift null band; fig5 layer profiles (AUC, d', cross-task cosine).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import FIGURES_DIR, RESULTS_DIR, TASKS  # noqa: E402

try:  # optional house style: point AII_DATA_FIG_GEN_SCRIPTS at the aii-data-fig-gen scripts directory
    import os
    sys.path.insert(0, os.environ["AII_DATA_FIG_GEN_SCRIPTS"])
    from chart_style import apply_house_style  # type: ignore
    apply_house_style()
except (KeyError, ImportError):
    plt.rcParams.update({"font.size": 10, "pdf.fonttype": 42})

C = ["#0173B2", "#DE8F05", "#029E73", "#D55E00", "#CC78BC", "#CA9161", "#949494", "#ECE133", "#56B4E9"]


def save(fig, name: str) -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES_DIR / f"{name}.pdf")
    fig.savefig(FIGURES_DIR / f"{name}.png", dpi=160)
    plt.close(fig)


def fig1(summ: dict, cst: dict) -> None:
    L = cst["layer"]
    fig, axes = plt.subplots(2, 2, figsize=(6.5, 5.2), layout="constrained", sharex="col")
    for j, t in enumerate(TASKS):
        cs = sorted(float(k) for k in cst[t]["pass_rates"])
        P, Plo, Phi, H, Hlo, Hhi, cx = [], [], [], [], [], [], []
        for c in cs:
            s = summ.get(f"{t}|steer:dc:c={c:g}:L={L}")
            if not s:
                continue
            cx.append(c)
            P.append(s["pass_rate"])
            Plo.append(s["pass_rate"] - s["wilson_ci"][0])
            Phi.append(s["wilson_ci"][1] - s["pass_rate"])
            h = s["hill_cc"]["hill1"]
            H.append(h if h is not None else float("nan"))
            ci = s.get("hill1_ci90_cluster") or [float("nan")] * 2
            Hlo.append((h - ci[0]) if h is not None else 0)
            Hhi.append((ci[1] - h) if h is not None else 0)
        ax = axes[0, j]
        ax.errorbar(cx, P, yerr=[Plo, Phi], marker="o", color=C[0], label="d_dc (list - implement)", capsize=2)
        ax.axhline(cst[t]["threshold"], ls=":", color="grey", lw=1)
        cstar = cst[t]["c_star"]
        for k, (nm, col, mk) in enumerate((("rand1", C[1], "s"), ("rand2", C[2], "D"), ("placebo", C[3], "^"),
                                           ("breadth", C[4], "v"))):
            s = summ.get(f"{t}|steer:{nm}:c={cstar:g}:L={L}")
            if s:
                ax.plot([cstar + 0.012 * (k + 1)], [s["pass_rate"]], mk, color=col, label=nm)
                h = s["hill_cc"]["hill1"]
                if h is not None:
                    axes[1, j].plot([cstar + 0.012 * (k + 1)], [h], mk, color=col)
        ax.set_title(f"{t}: pass rate (dotted: 0.8 x c=0)")
        ax.set_ylim(-0.03, 1.05)
        ax2 = axes[1, j]
        ax2.errorbar(cx, H, yerr=[Hlo, Hhi], marker="o", color=C[0], capsize=2)
        ax2.axvline(cstar, ls="--", color="grey", lw=0.8)
        ax2.set_title(f"{t}: Hill-1 of correct labels (90% CI)")
        ax2.set_xlabel("steering coefficient c")
        if j == 0:
            ax.set_ylabel("pass rate")
            ax2.set_ylabel("Hill-1 (correct only)")
    axes[0, 1].legend(fontsize=7, loc="upper right")
    save(fig, "fig1_dose_response")


def fig2(summ: dict, cst: dict, modes: dict) -> None:
    L = cst["layer"]
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 4.2), layout="constrained")
    for j, t in enumerate(TASKS):
        cs = cst[t]["c_star"]
        X = modes[t]["X"]
        arms = ["baseline", "enumerate", f"ban:{X}", f"mention:{X}", "succession:2"] + \
               [f"steer:dc:c={float(c):g}:L={L}" for c in sorted(float(k) for k in cst[t]["pass_rates"])] + \
               [f"steer:{n}:c={cs:g}:L={L}" for n in ("rand1", "rand2", "placebo", "breadth", "dcxfer")]
        arms = [a for a in arms if f"{t}|{a}" in summ]
        labs = sorted({k for a in arms for k in summ[f"{t}|{a}"]["label_counts_correct"]})
        ax = axes[j]
        left = [0.0] * len(arms)
        for i, lab in enumerate(labs + ["failed"]):
            vals = []
            for a in arms:
                s = summ[f"{t}|{a}"]
                vals.append((s["n"] - s["n_correct"]) / s["n"] if lab == "failed" else
                            s["label_counts_correct"].get(lab, 0) / s["n"])
            ax.barh(range(len(arms)), vals, left=left, color=("#DDDDDD" if lab == "failed" else C[i % len(C)]),
                    label=lab, edgecolor="white", lw=0.3)
            left = [l + v for l, v in zip(left, vals)]
        ax.set_yticks(range(len(arms)))
        ax.set_yticklabels([a.replace(f":L={L}", "").replace("steer:", "") for a in arms], fontsize=7)
        ax.invert_yaxis()
        ax.set_xlabel("share of samples")
        ax.set_title(t)
        ax.legend(fontsize=6, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=3, frameon=False)
    save(fig, "fig2_label_distributions")


def fig3(buy: dict, cst: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 3.6), layout="constrained", sharey=True)
    for j, t in enumerate(TASKS):
        ax = axes[j]
        cs = cst[t]["c_star"]
        quiet = []
        k_id = 0
        for k, v in buy[t].items():
            if k.startswith("_") or k in ("steer_vs_vllm_baseline", "enumerate@1024") or v.get("delta_hill_rarefied") is None:
                continue
            if k.startswith("steer:dc:") and f"c={cs:g}:" not in k:
                continue  # off-c* points of the dc curve are in fig1
            x, y = v.get("tv_to_reference"), v["delta_hill_rarefied"]
            ci = v.get("ci90_rarefied_cluster") or [y, y]
            name = k.replace("steer:", "").split(":L=")[0].replace(f":c={cs:g}", "")
            mk = "osD^vPX*h<>"[k_id % 11]
            ax.errorbar([x], [y], yerr=[[y - ci[0]], [ci[1] - y]], fmt=mk, color=C[k_id % len(C)], capsize=2, ms=5,
                        label=name)
            k_id += 1
            if abs(y) < 0.02 and x < 0.02:
                quiet.append(name)
        ax.axhline(0, color="grey", lw=0.8)
        ax.set_xlabel("TV distance to reference")
        ax.set_title(f"{t} (c* = {cs:g})")
        ax.legend(fontsize=6, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3, frameon=False)
    axes[0].set_ylabel("delta rarefied Hill-1 (90% cluster CI)")
    save(fig, "fig3_tv_vs_delta_hill")


def fig4(ct: dict, modes: dict) -> None:
    Ls = str(ct["layer_star"])
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 3.6), layout="constrained")
    for j, t in enumerate(TASKS):
        r = ct["per_task"][t][Ls]
        X = modes[t]["X"]
        keys = ["IMPLEMENT", "baseline", f"mention:{X}", f"ban:{X}", "enumerate", "ONE", "listall", "LIST"]
        vals = [r["kappa"][k] for k in keys]
        ax = axes[j]
        ax.barh(range(len(keys)), vals, color=[C[3] if k.startswith("ban") else C[0] for k in keys])
        b = r["ban"][X]
        lo, hi = b["null_band_95"]
        km = r["kappa"][f"mention:{X}"]
        ax.axvspan(km + lo, km + hi, color="grey", alpha=0.25, lw=0)
        ax.set_yticks(range(len(keys)))
        ax.set_yticklabels(keys, fontsize=7)
        ax.invert_yaxis()
        ax.set_xlabel("commitment coordinate kappa")
        ax.set_title(f"{t} (L={Ls}); grey: mention + null 95%", fontsize=8)
    save(fig, "fig4_commitment_kappa")


def fig5(sel: dict, diag: dict) -> None:
    ls = sorted(int(l) for l in sel["per_layer"])
    fig, axes = plt.subplots(1, 3, figsize=(6.5, 2.6), layout="constrained")
    for j, t in enumerate(TASKS):
        axes[0].plot(ls, [sel["per_layer"][str(l)][t]["auc"] for l in ls], marker=".", color=C[j], label=t)
        axes[1].plot(ls, [sel["per_layer"][str(l)][t]["dprime"] for l in ls], marker=".", color=C[j], label=t)
    axes[2].plot(ls, [diag["per_layer"][str(l)]["cross_task_cos"] for l in ls], marker=".", color=C[2])
    for ax, ttl in zip(axes, ("held-out AUC", "held-out d'", "cos(d_T1, d_T2)")):
        ax.set_title(ttl, fontsize=9)
        ax.set_xlabel("layer")
        ax.axvline(sel["L_star"], ls="--", color="grey", lw=0.8)
    axes[0].legend(fontsize=7)
    save(fig, "fig5_layer_profiles")


def main() -> None:
    summ = json.loads((RESULTS_DIR / "condition_summaries.json").read_text())
    cst = json.loads((RESULTS_DIR / "cstar.json").read_text())
    modes = json.loads((RESULTS_DIR / "modal_modes.json").read_text())
    buy = json.loads((RESULTS_DIR / "buy_table.json").read_text())
    ct = json.loads((RESULTS_DIR / "commitment_test.json").read_text())
    sel = json.loads((RESULTS_DIR / "layer_selection.json").read_text())
    diag = json.loads((RESULTS_DIR / "direction_diagnostics.json").read_text())
    for f, a in ((fig1, (summ, cst)), (fig2, (summ, cst, modes)), (fig3, (buy, cst)), (fig4, (ct, modes)),
                 (fig5, (sel, diag))):
        try:
            f(*a)
        except Exception as e:  # noqa: BLE001 - one failing figure must not block the others
            print(f"figure {f.__name__} failed: {e!r}")
    print("figures written")


if __name__ == "__main__":
    main()
