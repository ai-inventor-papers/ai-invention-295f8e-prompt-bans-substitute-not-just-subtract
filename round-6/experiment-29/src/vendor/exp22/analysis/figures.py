#!/usr/bin/env python3
"""Figures (PDF + PNG, Okabe-Ito palette, Type 42 fonts) from results/*.json only, so a figure cannot disagree with
the numbers: fig1 pi vs y per task; fig2 predictor comparison; fig3 decomposition R; fig4 C2c dose-response;
fig5 C2b knob projection vs share; fig6 geometry composites; fig7 E_t across 15 tasks vs ban avoidance; fig8 C3b."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "results"
F = ROOT / "figures"
F.mkdir(exist_ok=True)
plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 150})
OI = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#000000"]
MOV = ["T03", "T2", "T05", "T10", "T06", "T1"]


def load(name):
    p = R / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def save(fig, name):
    fig.savefig(F / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(F / f"{name}.png", bbox_inches="tight", dpi=200)
    plt.close(fig)


def fig1(c2a, commit):
    fig, axs = plt.subplots(2, 3, figsize=(10, 6))
    for ax, t in zip(axs.flat, MOV):
        r = c2a["per_task"].get(t)
        if not r:
            ax.set_axis_off()
            continue
        seeds = sorted(int(s) for s in r["direction_table"])
        x = np.array([commit["predictors"][t][str(s)]["pi"] for s in seeds]) * 1e3
        y = np.array(r["y"])
        esc = np.array(r["escape"])
        ax.scatter(x[esc == 0], y[esc == 0], s=18, c=OI[0], label="not confirmed")
        ax.scatter(x[esc == 1], y[esc == 1], s=26, c=OI[3], marker="D", label="confirmed escape")
        p = r["predictors"]["pi"]
        ax.set_title(f"{t}: rho={p['rho']:.2f}, p={p['p']:.3f} (null q95 {p['null_q95']:.2f})", fontsize=8.5)
        ax.set_xlabel("pi(u) x 1e3")
        ax.axhline(r["twin"]["share"], color="grey", lw=0.8, ls="--")
    for ax in axs[:, 0]:
        ax.set_ylabel("y: off-default share\n(first 10, mean of alpha 1, 2)")
    axs.flat[0].legend(fontsize=7, frameon=False)
    fig.suptitle("C2a: projection share pi(u) on the plan subspace (blocks 12-23) vs the effect of 40 fresh random "
                 "pushes per task")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    save(fig, "fig1_c2a_pi_vs_y")


def fig2(c2a):
    preds = ["pi", "pi_masked", "s", "s_runner_up", "pi_real", "pi_late", "pi_R", "pi_wrong", "pi_within",
             "pi_whitened", "pi_noOutlier", "gain"]
    fig, ax = plt.subplots(figsize=(10, 4))
    w = 0.8 / len(MOV)
    for i, t in enumerate(MOV):
        r = c2a["per_task"].get(t)
        if not r:
            continue
        vals = [r["predictors"].get(p, {}).get("rho", np.nan) for p in preds]
        q = [r["predictors"].get(p, {}).get("null_q95", np.nan) for p in preds]
        xs = np.arange(len(preds)) + i * w - 0.4 + w / 2
        ax.bar(xs, vals, width=w, color=OI[i % len(OI)], label=t)
        ax.scatter(xs, q, marker="_", color="k", s=30, zorder=3)
    ax.axhline(0.4, color="grey", ls="--", lw=0.8)
    ax.axhline(0, color="k", lw=0.5)
    ax.set_xticks(np.arange(len(preds)))
    ax.set_xticklabels(preds, rotation=35, ha="right")
    ax.set_ylabel("Spearman rho with y (black tick: permutation q95)")
    ax.legend(ncol=6, fontsize=7, frameon=False)
    ax.set_title("C2a predictors vs controls (dashed: committed rho threshold 0.4)")
    save(fig, "fig2_predictors")


def fig3(dec):
    if not dec or "per_task" not in dec:
        return
    labels, ru, up, cl, ci = [], [], [], [], []
    for t, v in dec["per_task"].items():
        for d in v["directions"]:
            labels.append(f"{t}\n{d['seed']}\nα={d['alpha']:g}")
            ru.append(d.get("R_uperp") if d.get("R_uperp") is not None else np.nan)
            up.append(d.get("R_up") if d.get("R_up") is not None else np.nan)
            cl.append(d.get("R_clamp") if d.get("R_clamp") is not None else np.nan)
            ci.append(d.get("R_uperp_ci") or [np.nan, np.nan])
    if not labels:
        return
    fig, ax = plt.subplots(figsize=(max(6, 0.5 * len(labels)), 3.8))
    x = np.arange(len(labels))
    ci = np.array(ci, float)
    ax.bar(x - 0.27, ru, 0.27, color=OI[0], label="u_perp (plan component removed)",
           yerr=[np.array(ru) - ci[:, 0], ci[:, 1] - np.array(ru)], capsize=2, error_kw={"lw": 0.6})
    ax.bar(x, up, 0.27, color=OI[1], label="u_P (plan component only, amplified)")
    ax.bar(x + 0.27, cl, 0.27, color=OI[2], label="CLAMP")
    ax.axhline(1, color="k", lw=0.6)
    ax.axhline(0, color="k", lw=0.6)
    ax.axhline(0.7, color="grey", ls="--", lw=0.6)
    ax.axhline(0.3, color="grey", ls=":", lw=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=6.5)
    ax.set_ylabel("R = (share_arm - twin) / (share_orig - twin)")
    ax.legend(fontsize=7, frameon=False)
    ax.set_title("Decomposition of confirmed escaping pushes (CRN slots k 0-3, N = 20)")
    save(fig, "fig3_decomposition")


def fig4(c2c):
    if not c2c or not c2c.get("per_task"):
        return
    fig, axs = plt.subplots(2, 3, figsize=(10, 6))
    for ax, t in zip(axs.flat, MOV):
        r = c2c["per_task"].get(t)
        if not r:
            ax.set_axis_off()
            continue
        a = r["arms"]
        ss, sh, ru, hl = [], [], [], []
        for s, k in ((0.0, "TWIN"), (0.25, "C2C_r_s0.25"), (0.5, "C2C_r_s0.5"), (1.0, "C2C_r_s1.0")):
            if k in a:
                ss.append(s)
                sh.append(a[k]["share"])
                ru.append(a[k]["runner_up_share"])
                hl.append(a[k]["pass"])
        ax.plot(ss, sh, "-o", color=OI[0], label="off-default share (r axis)")
        ax.plot(ss, ru, "-s", color=OI[2], label=f"runner-up share ({r['runner_up']})")
        ax.plot(ss, hl, ":", color="grey", label="pass rate")
        rk = [k for k in a if k.startswith("C2C_rand")]
        if rk:
            ax.scatter([0.5], [a[rk[0]]["share"]], marker="x", s=50, color=OI[3], zorder=4,
                       label="random, same M_s (s = 0.5)")
        if "C2C_rm_s0.5" in a:
            ax.scatter([0.5], [a["C2C_rm_s0.5"]["share"]], marker="^", s=40, color=OI[4], zorder=4,
                       label="masked axis (s = 0.5)")
        ax.axvline(0.5, color="k", lw=0.6, ls="--")
        spm = r["s_prime"]["r"]["mean"]
        if -0.5 < spm < 2:
            ax.axvline(spm, color=OI[1], lw=0.8, ls=":")
        ax.set_ylim(-0.03, 1.03)
        ax.set_title(f"{t}: nu(0.5) = {r['nu_0.5']:.2f} ban units; s' = {spm:.2f}", fontsize=8.5)
        ax.set_xlabel("dose s (x D; b_t = 0.5)")
    for ax in axs[:, 0]:
        ax.set_ylabel("share / pass rate")
    axs.flat[0].legend(fontsize=6.5, frameon=False)
    fig.suptitle("C2c: targeted pushes along default -> runner-up vs a random push of the same magnitude")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    save(fig, "fig4_c2c_dose")


def fig5(c2b):
    if not c2b or not c2b.get("table"):
        return
    fig, ax = plt.subplots(figsize=(6, 4.2))
    kn = sorted({r["knob"] for r in c2b["table"]})
    for i, k in enumerate(kn):
        rr = [r for r in c2b["table"] if r["knob"] == k]
        ax.scatter([r["pi"] for r in rr], [r["share"] for r in rr], s=14, color=OI[i % len(OI)], label=k, alpha=0.8)
    ax.set_xscale("log")
    ax.set_xlabel("pi(delta_knob): projection share of the knob displacement on P_t")
    ax.set_ylabel("recorded off-default share")
    p = c2b.get("pooled", {})
    ax.set_title(f"C2b: pooled within-task rho_pi = {p.get('rho_pi', float('nan')):.2f}, "
                 f"rho_norm = {p.get('rho_norm', float('nan')):.2f}", fontsize=9)
    ax.legend(fontsize=7, frameon=False)
    save(fig, "fig5_c2b_knobs")


def fig6(geo):
    if not geo:
        return
    for t, g in geo["tasks"].items():
        blk = "18"
        if blk not in g or "embedding_k10" not in g[blk]:
            continue
        e = g[blk]["embedding_k10"]
        P = np.array(e["points"])
        labs = e["labels"]
        modes = sorted(set(labs))
        col = {m: OI[i % len(OI)] for i, m in enumerate(modes)}
        fig, axs = plt.subplots(2, 2, figsize=(10, 8))
        ax = axs[0, 0]
        for m in modes:
            ii = [i for i, l in enumerate(labs) if l == m]
            kk = [e["kinds"][i] for i in ii]
            ax.scatter(P[ii, 0], P[ii, 1], s=[10 if k == "named" else 6 for k in kk], color=col[m], label=m,
                       marker="o", alpha=0.7)
        gp = np.array(e["geodesic_path"])
        ax.plot(gp[:, 0], gp[:, 1], "-", color="k", lw=1.0)
        ax.set_title(f"{t} block {blk}: Isomap (k = 10) of named (large) + masked (small) states")
        ax.legend(fontsize=6.5, frameon=False)
        o = e["oos"]
        ax = axs[0, 1]
        ax.scatter(P[:, 0], P[:, 1], s=4, color="#BBBBBB")
        if "twin" in o:
            T = np.array(o["twin"])
            ax.scatter(T[:, 0], T[:, 1], s=40, marker="*", color=OI[7], label="twins W1-W5")
        if "ban" in o:
            Bn = np.array(o["ban"])
            ax.scatter(Bn[:, 0], Bn[:, 1], s=30, marker="X", color=OI[3], label="iteration-3 modal bans")
        ax.legend(fontsize=7, frameon=False)
        ax.set_title("out-of-sample: twins and bans")
        ax = axs[1, 0]
        ax.scatter(P[:, 0], P[:, 1], s=4, color="#BBBBBB")
        if "population" in o:
            Q = np.array(o["population"]["points"])
            ll = o["population"]["landing"]
            for m in sorted(set(ll)):
                ii = [i for i, l in enumerate(ll) if l == m]
                ax.scatter(Q[ii, 0], Q[ii, 1], s=8, color=col.get(m, "#999999"), label=f"lands: {m}")
            ax.legend(fontsize=6.5, frameon=False)
        ax.set_title("population pushed states (twin + realised displacement)")
        ax = axs[1, 1]
        ax.scatter(P[:, 0], P[:, 1], s=4, color="#BBBBBB")
        if "targeted" in o:
            for i, (arm, pts) in enumerate(sorted(o["targeted"].items())):
                Q = np.array(pts)
                ax.scatter(Q[:, 0], Q[:, 1], s=18, color=OI[i % len(OI)], label=arm, marker="P")
            ax.legend(fontsize=6, frameon=False)
        ic = g.get("implemented_counts", {})
        ax.set_title("targeted arms (C2c doses, random control, sweep)")
        txt = "\n".join(f"{k}: " + ", ".join(f"{a} {n}" for a, n in sorted(v.items(), key=lambda x: -x[1])[:3])
                        for k, v in ic.items())
        ax.text(0.01, 0.01, "implemented counts\n" + txt, transform=ax.transAxes, fontsize=6, va="bottom",
                bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "#CCCCCC"})
        fig.tight_layout()
        save(fig, f"fig6_geometry_{t}")


def fig7(esc, screen):
    if not esc:
        return
    tasks = [t for t in ["T03", "T2", "T05", "T10", "T06", "T1", "T04", "T08", "T11", "T13", "T14", "R1", "R3", "R6",
                         "R2"] if t in esc]
    av = {}
    p13 = ROOT / "inputs/exp13/results/c1_events.jsonl"
    for l in p13.read_text().splitlines():
        e = json.loads(l)
        av[e["task"]] = e.get("avoidance")
    fig, ax = plt.subplots(figsize=(10, 3.6))
    x = np.arange(len(tasks))
    for j, a in enumerate(("1.0", "2.0")):
        v = [esc[t]["E_t"].get(a, {}).get("E_t") or 0 for t in tasks]
        ax.bar(x + (j - 0.5) * 0.35, v, 0.35, color=OI[j], label=f"E_t, alpha = {a[:-2]}")
    ax.scatter(x, [av.get(t) if av.get(t) is not None else np.nan for t in tasks], color=OI[3], marker="D", s=24,
               label="iteration-3 ban avoidance (exp13)", zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels(tasks)
    ax.set_ylabel("fraction")
    ax.legend(fontsize=7, frameon=False, ncol=3)
    ax.set_title("Escape fraction of fresh random plan-site pushes (confirmed at N = 30) across 15 tasks")
    save(fig, "fig7_escape_15_tasks")


def fig8(c3b):
    if not c3b:
        return
    fams = ["PUSH", "PUSH_SCREEN", "LADDER_OPEN", "ASSOCIATE", "PROXIMITY"]
    ev = c3b["gated_events"]
    M = np.array([[c3b["events"][t]["logscore"].get(f) if c3b["events"][t]["logscore"].get(f) is not None
                   else np.nan for f in fams] for t in ev], float)
    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    im = ax.imshow(M, cmap="viridis", aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            if np.isfinite(M[i, j]):
                ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", fontsize=7, color="w")
    ax.set_xticks(range(len(fams)))
    ax.set_xticklabels(fams, rotation=20)
    ax.set_yticks(range(len(ev)))
    ax.set_yticklabels(ev)
    fig.colorbar(im, ax=ax, label="mean ln p (higher is better)")
    ax.set_title("C3b: log score of landing forecasts on the 5 gated iteration-3 bans (descriptive)", fontsize=8.5)
    save(fig, "fig8_c3b_logscore")


def fig9(ex):
    if not ex or not ex.get("tasks"):
        return
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.4), sharey=True)
    for k, (nm, ttl) in enumerate((("proj_r", "signed progress toward the runner-up"),
                                   ("pi", "projection share on P_t"), ("norm", "displacement norm"))):
        ax = axs[k]
        for i, (t, v) in enumerate(ex["tasks"].items()):
            ax.plot(v["blocks"], v["profile"][nm], "-o", ms=2.5, color=OI[i % len(OI)], label=t)
        ax.axhline(0, color="k", lw=0.5)
        ax.axvspan(12, 23, color="#EEEEEE", zorder=0)
        ax.set_title(ttl, fontsize=9)
        ax.set_xlabel("block (shaded: edited blocks 12-23)")
    axs[0].set_ylabel("Spearman rho with y (40 directions)")
    axs[0].legend(fontsize=7, frameon=False)
    fig.suptitle("EXPLORATORY: which feature of the realised push displacement tracks its effect, by depth")
    fig.tight_layout()
    save(fig, "fig9_exploratory_blockwise")


def main():
    commit = json.loads((ROOT / "predictions/c2_commit.json").read_text())
    c2a = load("c2a")
    if c2a:
        fig1(c2a, commit)
        fig2(c2a)
    fig3(load("decomposition"))
    fig4(load("c2c"))
    fig5(load("c2b"))
    fig6(load("geometry"))
    fig7(load("escape"), load("screen"))
    fig8(load("c3b"))
    fig9(load("explore"))
    print("figures:", sorted(p.name for p in F.glob("*.png")))


if __name__ == "__main__":
    main()
