#!/usr/bin/env python3
"""Figures F1-F7 (PDF + PNG) from the result files (no recomputation of any test)."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg7 import CACHE_DIR, FIG_DIR, PRED_DIR, RESULTS_DIR, SAMPLERS, TEMPS, UNITS, read_json  # noqa: E402

plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42,
                     "ps.fonttype": 42, "figure.dpi": 150})
COL = {"B3": "#1b6ca8", "A3": "#c45a00", "B6": "#2e8b57", "T1": "#7a4f9a", "T2": "#a33b3b", "T10": "#556b2f",
       "T03": "#8b6914"}


def save(fig, name: str) -> None:
    fig.savefig(FIG_DIR / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIG_DIR / f"{name}.png", bbox_inches="tight", dpi=200)
    plt.close(fig)


def f1_outcome_curves() -> None:
    F = read_json(RESULTS_DIR / "forks.json")
    units = [u for u in ("B3", "A3", "B6") if u in F]
    nb = max(len(F[u]["base_paths"]) for u in units)
    fig, axes = plt.subplots(len(units), 1, figsize=(10, 3.0 * len(units)), squeeze=False)
    for i, u in enumerate(units):
        ax = axes[i, 0]
        L = F[u]["opening"]["len_O"]
        for b in F[u]["base_paths"]:
            ib = F[u]["per_base_path"][b["bid"]]
            ks = ib["ks"]
            col = COL[u] if b["cls"] == F[u]["A_min"] else "#888888"
            ls = "-" if b["on_O"] else ":"
            ax.plot(ks, ib["own_share"], ls, color=col, lw=1.1, alpha=0.85)
            if ib.get("f"):
                ax.plot([ib["f"]], [1.02], "v", color=col, ms=5 if ib.get("confirmed") else 3,
                        mfc=col if ib.get("confirmed") else "none")
            for c in ib["cps"]:
                if c.get("post"):
                    pass
        ax.axvline(L + 1, color="k", lw=0.8, ls="--")
        ax.text(L + 1.5, 0.05, "|O|+1", fontsize=8)
        ax.set_ylabel("own-class share of\n8 continuations")
        ax.set_title(f"{u}: base paths of {F[u]['A_min']} (colour) and {F[u]['D']} (grey); solid = on the canonical "
                     f"opening; triangles = refined fork (filled = confirmed)", fontsize=8)
        ax.set_ylim(-0.03, 1.08)
    axes[-1, 0].set_xlabel("prefix length k (generated tokens forced from the base path)")
    save(fig, "F1_outcome_curves")
    # change-point posteriors (second page)
    fig, axes = plt.subplots(len(units), 1, figsize=(10, 2.4 * len(units)), squeeze=False)
    for i, u in enumerate(units):
        ax = axes[i, 0]
        for b in F[u]["base_paths"]:
            ib = F[u]["per_base_path"][b["bid"]]
            arr = np.array(ib["series"])
            from forks import single_cp
            r = single_cp(arr)
            if r["post"]:
                col = COL[u] if b["cls"] == F[u]["A_min"] else "#888888"
                ax.plot(ib["ks"][1:], r["post"], color=col, lw=1, alpha=0.8)
        ax.axvline(F[u]["opening"]["len_O"] + 1, color="k", lw=0.8, ls="--")
        ax.set_ylabel("P(tau | data)")
        ax.set_title(f"{u}: change-point posteriors over the scanned prefix lengths", fontsize=8)
    axes[-1, 0].set_xlabel("prefix length k")
    save(fig, "F1b_changepoint_posteriors")


def f2_fork_tokens() -> None:
    R = read_json(PRED_DIR / "predictions_raw.json")
    units = [u for u in ("B3", "A3", "B6") if u in R]
    fig, axes = plt.subplots(1, len(units), figsize=(4.2 * len(units), 3.6), squeeze=False)
    for i, u in enumerate(units):
        ax = axes[0, i]
        cid = sorted(R[u]["clusters"])[0]
        cl = R[u]["clusters"][cid]
        C = R[u]["cats"]
        A = R[u]["A_min"]
        toks = sorted(cl["toks"], key=lambda t: -cl["pi1_avg"][str(t)])[:25]
        pis = [cl["pi1_avg"][str(t)] for t in toks]
        ph = []
        for t in toks:
            v = np.array(cl["counts"][str(t)], float)
            ph.append(v[C.index(A)] / v.sum() if v.sum() else np.nan)
        cmap = plt.get_cmap("coolwarm")
        ax.bar(range(len(toks)), pis, color=[cmap(p) if np.isfinite(p) else "#cccccc" for p in ph])
        ax.set_yscale("log")
        ax.axvline(9.5, color="k", ls="--", lw=0.8)
        ax.text(9.7, max(pis) * 0.5, "top-k 10 cut", fontsize=7)
        ax.set_xticks(range(len(toks)))
        ax.set_xticklabels([repr(cl["tok_text"][str(t)])[1:-1][:10] for t in toks], rotation=75, fontsize=6)
        ax.set_ylabel("pi_1(t | O) (template mean)")
        ax.set_title(f"{u} fork tokens; colour = Phat({A} | t)", fontsize=8)
    sm = plt.cm.ScalarMappable(cmap="coolwarm", norm=plt.Normalize(0, 1))
    fig.colorbar(sm, ax=axes.ravel().tolist(), shrink=0.8, label="Phat(A_min | fork token)")
    save(fig, "F2_fork_token_probabilities")


def f3_pred_vs_obs() -> None:
    pv = read_json(RESULTS_DIR / "predictions_view.json")
    t2 = read_json(RESULTS_DIR / "test2.json") if (RESULTS_DIR / "test2.json").exists() else {"per_unit": {}}
    units = [u for u in ("B3", "A3", "B6") if u in pv["units"]]
    fig, axes = plt.subplots(1, len(units), figsize=(4.0 * len(units), 3.3), squeeze=False)
    for i, u in enumerate(units):
        ax = axes[0, i]
        U = pv["units"][u]
        for sname, ls, mk in (("p1", "-", "o"), ("k10", "--", "s")):
            pred = [U["cells"][f"T{T}_{sname}"]["a_min"] for T in TEMPS]
            ax.plot(TEMPS, pred, ls, color=COL[u], lw=1.4, label=f"predicted ({'top-p 1' if sname == 'p1' else 'top-k 10'})")
            cells = t2["per_unit"].get(u, {}).get("cells", {})
            if cells:
                obs = [cells[f"T{T}_{sname}"]["a_min"] for T in TEMPS]
                lo = [cells[f"T{T}_{sname}"]["a_min_ci"][0] for T in TEMPS]
                hi = [cells[f"T{T}_{sname}"]["a_min_ci"][1] for T in TEMPS]
                xs = np.array(TEMPS) + (0.015 if sname == "k10" else -0.015)
                ax.errorbar(xs, obs, yerr=[np.array(obs) - lo, np.array(hi) - obs], fmt=mk, color="k",
                            mfc="white" if sname == "k10" else "k", ms=4, lw=0.8, capsize=2,
                            label=f"observed ({'top-p 1' if sname == 'p1' else 'top-k 10'}), Wilson 95%")
        ax.set_xlabel("temperature T")
        ax.set_ylabel(f"attempted {U['A_min']} share (N = 50)")
        ax.set_title(u, fontsize=9)
        ax.set_ylim(-0.02, max(0.6, ax.get_ylim()[1]))
        if i == 0:
            ax.legend(fontsize=6, frameon=False)
    save(fig, "F3_pred_vs_obs")


def f4_margins() -> None:
    pv = read_json(RESULTS_DIR / "predictions_view.json")
    names, ms, cols = [], [], []
    for u, U in pv["units"].items():
        for cid, m in U["margins"].items():
            names.append(f"{u}/{cid}")
            ms.append(m["mean"])
            cols.append(COL[u])
    for t, c in pv.get("collapsed", {}).items():
        if t.startswith("_"):
            continue
        names.append(t)
        ms.append(c["margin_nats"] if math.isfinite(c["margin_nats"]) else 15.0)
        cols.append(COL.get(t, "#444444"))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.5))
    a1.barh(range(len(ms)), ms, color=cols)
    a1.set_yticks(range(len(ms)))
    a1.set_yticklabels(names, fontsize=7)
    a1.axvline(4.0, color="k", ls="--", lw=0.8)
    a1.text(4.1, len(ms) - 0.6, "4 nats", fontsize=7)
    a1.set_xlabel("fork margin m = log P1(D) - log P1(non-D) (nats, T = 1)")
    Ts = np.linspace(0.2, 1.6, 100)
    for n_, m, c in zip(names, ms, cols):
        a2.plot(Ts, [1 / (1 + math.exp(min(700, m / T))) for T in Ts], color=c, lw=1.1, label=n_)
    a2.set_yscale("log")
    a2.set_ylim(1e-6, 1)
    a2.set_xlabel("temperature T")
    a2.set_ylabel("binary-fork off-default probability 1/(1+e^{m/T})")
    a2.legend(fontsize=6, frameon=False, ncol=2)
    save(fig, "F4_margins")


def f5_s4a() -> None:
    p = RESULTS_DIR / "s4a.json"
    if not p.exists():
        return
    S = read_json(p)
    fig, ax = plt.subplots(figsize=(4.6, 3.6))
    for u, r in S.items():
        dm = [v["d_margin"] for v in r["per_direction"].values()]
        ds = [v["d_s_obs"] for v in r["per_direction"].values()]
        ax.scatter(dm, ds, color=COL[u], s=18, label=f"{u} (rho {r['spearman_dmargin_dshare']:.2f})")
    ax.axhline(0, color="k", lw=0.5)
    ax.axvline(0, color="k", lw=0.5)
    ax.set_xlabel("pushed fork margin change Delta m_d (nats, teacher-forced)")
    ax.set_ylabel("observed minority share change vs twin")
    ax.legend(fontsize=7, frameon=False)
    save(fig, "F5_s4a_push")


def f6_s4b() -> None:
    p = RESULTS_DIR / "s4b.json"
    if not p.exists():
        return
    S = read_json(p)
    units = list(S)
    arms = ["FORCEDPAD", "MR", "EXCH", "FORCED"]
    fig, ax = plt.subplots(figsize=(6, 3.4))
    w = 0.8 / len(arms)
    for j, a in enumerate(arms):
        vals = [S[u]["arms"].get(a, {}).get("attempted_a_min", np.nan) for u in units]
        cor = [S[u]["arms"].get(a, {}).get("correct_a_min", np.nan) for u in units]
        x = np.arange(len(units)) + j * w
        ax.bar(x, vals, w, label=a, color=["#bbbbbb", "#888888", "#1b6ca8", "#0b2d4d"][j])
        ax.scatter(x, cor, color="k", s=8, zorder=3)
    ax.set_xticks(np.arange(len(units)) + 0.3)
    ax.set_xticklabels(units)
    ax.set_ylabel("attempted A_min share (dots: correct A_min)")
    ax.legend(fontsize=7, frameon=False, ncol=4)
    save(fig, "F6_s4b_exchange")


def f7_geometry() -> None:
    R = read_json(PRED_DIR / "predictions_raw.json")
    units = [u for u in ("B3", "A3", "B6") if (CACHE_DIR / f"geometry_{u}.npz").exists()]
    if not units:
        return
    fig, axes = plt.subplots(1, len(units), figsize=(4.6 * len(units), 4.2), squeeze=False)
    for i, u in enumerate(units):
        ax = axes[0, i]
        z = np.load(CACHE_DIR / f"geometry_{u}.npz", allow_pickle=True)
        X, toks = z["X"].astype(np.float64), [int(t) for t in z["toks"]]
        E, En = z["extra"].astype(np.float64), [str(s) for s in z["extra_names"]]
        cid = sorted(R[u]["clusters"])[0]
        cl = R[u]["clusters"][cid]
        C, A, D = R[u]["cats"], R[u]["A_min"], R[u]["D"]
        ph = np.array([np.array(cl["counts"][str(t)], float)[C.index(A)] / max(1, sum(cl["counts"][str(t)]))
                       for t in toks])
        pd_ = np.array([np.array(cl["counts"][str(t)], float)[C.index(D)] / max(1, sum(cl["counts"][str(t)]))
                        for t in toks])
        pi = np.array([cl["pi1_avg"][str(t)] for t in toks])
        isA, isD = ph >= 0.5, pd_ >= 0.5
        mu = X.mean(0)
        if isA.any() and isD.any():
            ax_x = X[isA].mean(0) - X[isD].mean(0)
        else:
            ax_x = X[np.argmax(ph)] - X[np.argmin(ph)]
        ax_x /= np.linalg.norm(ax_x)
        Xc = X - mu
        xs = Xc @ ax_x
        Rr = Xc - np.outer(xs, ax_x)
        _, _, Vt = np.linalg.svd(Rr, full_matrices=False)
        ax_y = Vt[0]
        ys = Xc @ ax_y
        sc = ax.scatter(xs, ys, c=ph, cmap="coolwarm", vmin=0, vmax=1, s=20 + 400 * np.sqrt(pi), edgecolor="k",
                        lw=0.4, alpha=0.9)
        for t, x0, y0, p0 in zip(toks, xs, ys, pi):
            if p0 > 0.01:
                ax.annotate(repr(cl["tok_text"][str(t)])[1:-1][:9], (x0, y0), fontsize=6, xytext=(3, 3),
                            textcoords="offset points")
        if len(E):
            Ec = E - mu
            ex, ey = Ec @ ax_x, Ec @ ax_y
            for n_, x0, y0 in zip(En, ex, ey):
                kind = n_.split("|")[0]
                mk = "x" if kind.startswith("push") else ("*" if kind in ("exchange", "forced") else "+")
                ax.scatter([x0], [y0], marker=mk, color="k" if kind != "MR" else "#777777", s=40)
                if not kind.startswith("push"):
                    ax.annotate(kind, (x0, y0), fontsize=6, xytext=(3, -8), textcoords="offset points")
        ax.set_xlabel("x: difference-in-means axis")
        ax.set_ylabel("y: PC1 of the residual after removing x")
        ax.set_title(f"{u}: x = mean({A}-class) - mean({D}-class) fork-token states", fontsize=7)
    fig.colorbar(sc, ax=axes.ravel().tolist(), shrink=0.8, label="Phat(A_min | fork token)")
    fig.text(0.02, -0.06, "Points: block-24 residual (HF hidden_states[25]) at the fork-token position for every expanded "
             "candidate fork token t under the W1 twin (prompt + canonical opening O + t), sized by pi_1(t), coloured by "
             "Phat(A_min | t).\nx: unit vector of the difference between the mean states of A_min-class and D-class "
             "tokens (Phat >= 0.5); y: first principal component of the states after projecting x out; origin = mean "
             "state. x markers: the 8 random task-state pushes (alpha 2, blocks 12-23); stars: the forced prompt and the "
             "forced-state exchange; plus: padding twin and matched-norm random exchange (MR), each at its argmax fork "
             "token.", fontsize=6.5, va="top", wrap=True)
    save(fig, "F7_fork_geometry")


def main() -> None:
    for f in (f1_outcome_curves, f2_fork_tokens, f3_pred_vs_obs, f4_margins, f5_s4a, f6_s4b, f7_geometry):
        try:
            f()
            print("ok", f.__name__)
        except Exception as e:  # noqa: BLE001 - one failing figure must not stop the others; reported
            print("FAILED", f.__name__, type(e).__name__, e)


if __name__ == "__main__":
    main()
