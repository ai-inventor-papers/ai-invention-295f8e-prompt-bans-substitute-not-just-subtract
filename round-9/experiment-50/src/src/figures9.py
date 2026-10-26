#!/usr/bin/env python3
"""S8 figures (PDF + PNG in figures/): F1 B1 margins, F2 JS controls, F3 single-component sweep by layer, F4 residual
swaps vs depth, F5 FSTACK vs matched random sets, F7 B3 held-out effects vs null, F8 activation geometry (PCA of the
actual block-30 output at the fork). F6 generation algorithm mix per arm (predicted vs observed)."""

from __future__ import annotations

import numpy as np
import torch
from loguru import logger

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from cfg9 import CACHE_DIR, FIG_DIR, FSTACK, N_HEADS, N_LAYERS, RESULTS_DIR, RS_LAYERS, read_json, read_jsonl, \
    setup_logging  # noqa: E402

plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42,
                     "ps.fonttype": 42, "savefig.dpi": 200})
C_I, C_B, C_F, C_R, C_S = "#1f77b4", "#d62728", "#2ca02c", "#7f7f7f", "#9467bd"


def save(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"{name}.pdf")
    fig.savefig(FIG_DIR / f"{name}.png")
    plt.close(fig)
    logger.info(f"figure {name}")


def f1_b1_margins(b1: dict) -> None:
    rows = []
    for u, r in b1["units"].items():
        for fid, fr in r["forks"].items():
            rows.append((fid + (" (descriptive)" if r.get("descriptive_only") else ""), fr))
    q8 = b1.get("qwen_iter8_carried", {})
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharey=False)
    for ax, mode in zip(axes, ("chat", "plain")):
        x = np.arange(len(rows))
        for i, (fid, fr) in enumerate(rows):
            mi, mb = np.array(fr[mode]["margin_instr"]), np.array(fr[mode]["margin_base"])
            ax.scatter(np.full(len(mi), i - 0.12), mi, s=10, color=C_I, alpha=0.7, label="instruct" if i == 0 else None)
            ax.scatter(np.full(len(mb), i + 0.12), mb, s=10, color=C_B, alpha=0.7, label="base" if i == 0 else None)
            ax.plot([i - 0.25, i + 0.0], [mi.mean()] * 2, color=C_I, lw=2)
            ax.plot([i + 0.0, i + 0.25], [mb.mean()] * 2, color=C_B, lw=2)
        ax.set_xticks(x)
        ax.set_xticklabels([f for f, _ in rows], rotation=30, ha="right")
        ax.axhline(0, color="k", lw=0.5)
        ax.set_ylabel("fork margin log P(D) - log P(A) (nats)")
        ax.set_title(f"B1 fork margins, {'chat template' if mode == 'chat' else 'template-free'}")
        if mode == "chat" and q8:
            txt = "Qwen3-8B iter-8 gains (carried): " + ", ".join(f"{t} {v['margin_gain_mean']:.2f}"
                                                                 for t, v in q8.items())
            ax.text(0.01, 0.98, txt, transform=ax.transAxes, fontsize=6.5, va="top")
        ax.legend(loc="lower right", fontsize=7)
    save(fig, "F1_b1_margins")


def f2_js(b1: dict) -> None:
    rows = [(fid, fr) for r in b1["units"].values() for fid, fr in r["forks"].items()]
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    w = 0.2
    labels = ("js_fork_mean", "js_entropy_matched_mean", "js_random_mean", "js_phrasing_mean")
    names = ("fork", "base-entropy-decile matched", "rate-matched random", "all phrasing positions")
    cols = (C_F, C_S, C_R, "#bcbd22")
    for j, (lab, nm, c) in enumerate(zip(labels, names, cols)):
        ax.bar(np.arange(len(rows)) + (j - 1.5) * w, [fr["phrasing"][lab] or 0 for _, fr in rows], w, color=c,
               label=nm)
    ax.set_xticks(np.arange(len(rows)))
    ax.set_xticklabels([f for f, _ in rows], rotation=20, ha="right")
    ax.set_ylabel("JS(instruct || base), nats\n(top-256 + tail bucket)")
    ax.set_title("B1: divergence at the fork vs Cantarero-style controls (chat template)")
    ax.legend(fontsize=7)
    save(fig, "F2_b1_js_controls")


def f3_singles(b2: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    for ax, (u, r) in zip(axes, b2["units"].items()):
        s = r["singles"]
        L = np.arange(N_LAYERS)
        mlp = [s.get(f"mlp|L{l}", np.nan) for l in L]
        ax.plot(L, mlp, "-o", ms=3, color=C_B, label="MLP (single)")
        hx, hy = [], []
        for l in L:
            for h in range(N_HEADS):
                k = f"head|L{l}|H{h}"
                if k in s:
                    hx.append(l + np.random.default_rng(l * 97 + h).uniform(-0.25, 0.25))
                    hy.append(s[k])
        ax.scatter(hx, hy, s=4, color=C_R, alpha=0.5, label="attention head (single)")
        lo, hi = np.percentile(hy, [2.5, 97.5])
        ax.axhspan(lo, hi, color=C_R, alpha=0.15, label="central 95% of single heads")
        for k in FSTACK:
            kind, l = k.split("|")[0], int(k.split("|")[1][1:])
            if k in s:
                ax.scatter([l], [s[k]], s=40, facecolor="none", edgecolor=C_F, lw=1.5,
                           label="FSTACK node" if k == FSTACK[0] else None)
        ax.axhline(0, color="k", lw=0.5)
        ax.set_xlabel("layer")
        ax.set_ylabel("share of the instruct-base gap closed")
        ax.set_title(f"{u}: single-component CMAP at the fork (N={r['n_prompts']} prompts)\nFSTACK set "
                     f"{r['arms']['FSTACK']['share']:.2f}; sum of its singles {r['sum_singles_FSTACK']:.2f}")
        ax.legend(fontsize=6.5, loc="upper left")
    save(fig, "F3_b2_singles_by_layer")


def f4_rs(b2: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    for ax, (u, r) in zip(axes, b2["units"].items()):
        rf = r["RS_fork"]
        ls = sorted(int(k) for k in rf)
        ax.plot(ls, [rf[str(l)] if str(l) in rf else rf[l] for l in ls], "-", color=C_I, label="RS-fork(l): fork only")
        for key, lab, mk in (("RS_prefix", "RS-prefix(l): positions before the fork", "s"),
                             ("RS_all", "RS-all(l): all positions", "^")):
            d = r[key]
            xs = sorted(int(k) for k in d)
            ax.plot(xs, [d[str(l)] if str(l) in d else d[l] for l in xs], mk + "--", ms=4, label=lab)
        ax.axhline(r["arms"]["FSTACK"]["share"], color=C_F, lw=1.5, label="FSTACK (10 nodes)")
        if "SPEC" in r["arms"]:
            ax.axhline(r["arms"]["SPEC"]["share"], color=C_S, lw=1.2, ls=":", label="SPEC set")
        ax.axhline(r["null_R"]["median"], color=C_R, lw=1, ls="-.", label="median matched random set")
        ax.axhline(1, color="k", lw=0.5)
        ax.axhline(0, color="k", lw=0.5)
        ax.set_xlabel("layer l (residual input of block l; 36 = final-norm input)")
        ax.set_ylabel("share of gap closed")
        ax.set_title(f"{u}: residual swaps (base -> instruct) vs depth")
        ax.legend(fontsize=6.5)
    save(fig, "F4_b2_residual_swaps")


def f5_null(b2: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.4))
    for ax, (u, r) in zip(axes, b2["units"].items()):
        ax.hist(r["null_R"]["shares"], bins=20, color=C_R, alpha=0.7, label="50 matched random sets (R)")
        if "null_Rpure" in r:
            ax.hist(r["null_Rpure"]["shares"], bins=20, color=C_S, alpha=0.4, label="R-pure (exp41 top-15 excluded)")
        ax.axvline(r["arms"]["FSTACK"]["share"], color=C_F, lw=2, label=f"FSTACK {r['arms']['FSTACK']['share']:.2f}")
        ax.axvline(r["null_R"]["p95"], color="k", ls="--", lw=1, label="R 95th percentile")
        ax.set_xlabel("share of gap closed")
        ax.set_ylabel("count")
        ax.set_title(f"{u}: FSTACK vs write-norm-matched random sets (p = {r['null_R']['empirical_p_upper']:.3f})")
        ax.legend(fontsize=6.5)
    save(fig, "F5_b2_random_null")


def f7_b3(b3: dict) -> None:
    pn = {k: v for k, v in b3["per_node"].items() if k.startswith("aligned|") and v["mode"] in ("ablate", "steer")}
    if not pn:
        return
    rows = read_jsonl(RESULTS_DIR / "b3_heldout_rows.jsonl")
    fig, ax = plt.subplots(figsize=(9, 3.6))
    keys = list(pn)
    for i, k in enumerate(keys):
        v = pn[k]
        d = np.array(v["d_per_prompt"])
        ax.scatter(np.full(len(d), i), d, s=12, color=C_F if v["mode"] == "ablate" else C_S, alpha=0.8)
        # random null spread: per prompt, random component values minus their mean
        tag = f"aligned|{v['mode']}|{v['node']}"
        spread = []
        for r in rows:
            rv = [r["res"][f"{tag}|r{j}"] for j in range(50) if f"{tag}|r{j}" in r["res"]]
            if rv:
                spread += list(np.asarray(rv) - np.mean(rv))
        if spread:
            lo, hi = np.percentile(spread, [2.5, 97.5])
            ax.plot([i, i], [lo, hi], color=C_R, lw=4, alpha=0.4)
        ax.text(i, ax.get_ylim()[1] if i == 0 else d.max(), f"p={v['p_sign_flip_heldout']:.3f}", fontsize=6,
                ha="center", va="bottom")
    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels([f"{pn[k]['mode']}\n{pn[k]['node'].replace('|H-1', '')}" for k in keys], fontsize=6.5,
                       rotation=30, ha="right")
    ax.axhline(0, color="k", lw=0.5)
    ax.set_ylabel("d = node effect - mean random effect (nats)")
    ax.set_title("B3: held-out C1forced prompts with interpolated condition means (grey: central 95% of random "
                 "components)")
    save(fig, "F7_b3_heldout")


def f8_geometry(b2: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    for ax, (u, r) in zip(axes, b2["units"].items()):
        tf = read_jsonl(RESULTS_DIR / f"b2_tf_{u}.jsonl")
        pids = []
        m = {}
        for row in tf:
            if row["pid"] not in pids:
                pids.append(row["pid"])
            m[(row["pid"], row["arm"])] = row["m"]
        rsh = r["null_R"]["shares"]
        med = int(np.argsort(rsh)[len(rsh) // 2])
        cb = torch.load(CACHE_DIR / f"base_{u}.pt")
        pts, cols, kinds = [], [], []
        for pi, p in enumerate(pids):
            gp = CACHE_DIR / f"geom_{u}_{pi:02d}.pt"
            if not gp.exists():
                continue
            g = torch.load(gp)
            base_state = (cb["caps"][pi].get("ot") or cb["caps"][pi])["resid"][31]
            for kind, vec, mm in (("instruct", g["none"], m[(p, "none")]), ("base", base_state, r["m_B"][pi]),
                                  ("FSTACK-patched", g["FSTACK"], m[(p, "FSTACK")]),
                                  ("median random-patched", g[f"R{med}"], m[(p, f"R{med}")]),
                                  ("RS-fork(23)-patched", g["RSfork23"], m[(p, "RSfork23")])):
                pts.append(vec.float().numpy())
                cols.append(mm)
                kinds.append(kind)
        X = np.stack(pts)
        fit = X[[i for i, k in enumerate(kinds) if k in ("instruct", "base")]]
        mu = fit.mean(0)
        U_, Sv, Vt = np.linalg.svd(fit - mu, full_matrices=False)
        ev = Sv ** 2 / (Sv ** 2).sum()
        Y = (X - mu) @ Vt[:2].T
        marks = {"instruct": "o", "base": "s", "FSTACK-patched": "^", "median random-patched": "x",
                 "RS-fork(23)-patched": "D"}
        sc = None
        for kind, mk in marks.items():
            ii = [i for i, k in enumerate(kinds) if k == kind]
            sc = ax.scatter(Y[ii, 0], Y[ii, 1], c=[cols[i] for i in ii], cmap="coolwarm", marker=mk, s=28,
                            vmin=min(cols), vmax=max(cols), label=kind, edgecolors="k", linewidths=0.3)
        fig.colorbar(sc, ax=ax, label="fork margin m (nats)")
        ax.set_xlabel(f"PC1 ({ev[0] * 100:.1f}% var)")
        ax.set_ylabel(f"PC2 ({ev[1] * 100:.1f}% var)")
        ax.set_title(f"{u}: block-30 output (residual into block 31) at the fork\nPCA fit on instruct + base states, "
                     f"N={len(pids)} prompts; other states projected", fontsize=8)
        ax.legend(fontsize=6, loc="best")
        del cb
    save(fig, "F8_b2_geometry_pca")


def f6_generation() -> None:
    p = RESULTS_DIR / "b2_generation.json"
    if not p.exists():
        return
    g = read_json(p)
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
    arms = ("TWIN", "FSTACK", "RAND", "FPD")
    for ax, u, minority in zip(axes, ("B3", "T10"), ("prim_heap", "dfs")):
        cells = g[u]["cells"]
        x = np.arange(len(arms))
        obs = [cells[a]["observed_shares"].get(minority) or 0 for a in arms]
        pre = [cells[a]["predicted_shares"].get(minority, 0) for a in arms]
        ci = [cells[a]["correct_minority_ci95"] for a in arms]
        rate = [cells[a]["correct_minority_rate"] for a in arms]
        ax.bar(x - 0.18, obs, 0.36, color=C_F, label=f"observed share labelled {minority}")
        ax.bar(x + 0.18, pre, 0.36, color=C_R, alpha=0.6, label="predicted (COMMIT #1, TF fork distribution x token map)")
        ax.errorbar(x - 0.18, rate, yerr=[[r - c[0] for r, c in zip(rate, ci)], [c[1] - r for r, c in zip(rate, ci)]],
                    fmt="none", ecolor="k", capsize=3, label="correct-minority rate, Wilson 95%")
        ax.set_xticks(x)
        ax.set_xticklabels(arms)
        ax.set_ylim(0, 1)
        t = g[u]["tests"]
        ax.set_title(f"{u}: minority algorithm in N=30 CRN programs per arm\nFSTACK vs TWIN "
                     f"{t['FSTACK_vs_TWIN']['b_first_only']}:{t['FSTACK_vs_TWIN']['c_second_only']} "
                     f"(p={t['FSTACK_vs_TWIN']['p_exact_two_sided']:.1e}); FSTACK vs RAND "
                     f"{t['FSTACK_vs_RAND']['b_first_only']}:{t['FSTACK_vs_RAND']['c_second_only']}; FSTACK vs FPD "
                     f"{t['FSTACK_vs_FPD']['b_first_only']}:{t['FSTACK_vs_FPD']['c_second_only']}", fontsize=8)
        ax.set_ylabel("share of programs")
        ax.legend(fontsize=6.5, loc="upper left")
    save(fig, "F6_b2_generation")


def main() -> None:
    b1p, b2p, b3p = (RESULTS_DIR / f"{n}.json" for n in ("b1_summary", "b2_summary", "b3_summary"))
    if b1p.exists():
        b1 = read_json(b1p)
        f1_b1_margins(b1)
        f2_js(b1)
    if b2p.exists():
        b2 = read_json(b2p)
        f3_singles(b2)
        f4_rs(b2)
        f5_null(b2)
        try:
            f8_geometry(b2)
        except (FileNotFoundError, KeyError, RuntimeError) as e:
            logger.error(f"F8 failed: {e}")
    if b3p.exists():
        f7_b3(read_json(b3p))
    f6_generation()


if __name__ == "__main__":
    setup_logging("figures9")
    main()
