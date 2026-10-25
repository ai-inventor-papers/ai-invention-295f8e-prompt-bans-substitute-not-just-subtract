#!/usr/bin/env python3
"""Figures F1-F8 (figures/*.pdf and *.png), drawn from the result files and cached fork states.

F1 closed share by arm with the RAND_ISO, DELTA_SWAP and RAND_RESID null histograms (T10, B3)
F2 per-prompt shares, point size = prompt gap
F3 dose-response of the share vs lambda for the base-row delta and for RAND_ISO at matched lambda
F4 generation counts by arm, stacked by label (correct vs failing), McNemar annotated
F5 actual activation coordinates: instruct and base final-normed fork states (20 + 20) on the plane spanned by the
   instruct readout difference direction u1 and the orthogonalised base readout direction u2, with margin isolines
   under the instruct and the swapped (base-row) readouts
F6 PCA of the block-35 outputs (final-norm inputs) at the fork, instruct vs base, with the readout difference
   directions overlaid
F7 W2 singles vs matched early swaps vs same-layer random deltas, and the weight-level decomposition
F8 W3 Gemma shares with the null histograms
"""

from __future__ import annotations

import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402
from loguru import logger  # noqa: E402

from cfg10 import CACHE_DIR, FIG_DIR, I9_RES, LATE, RESULTS_DIR, UNITS_TF, read_json, setup_logging  # noqa: E402

plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42, "ps.fonttype": 42, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 150})
C = {"ROWS_ALL": "#c0392b", "ROWS_D": "#e67e22", "ROWS_A": "#8e44ad", "NORM": "#7f8c8d", "ROWS_NORM": "#2c3e50",
     "SIGN": "#16a085", "RAND_ISO": "#3498db", "DELTA_SWAP": "#27ae60", "RAND_RESID": "#f1c40f", "instr": "#c0392b",
     "base": "#2980b9"}
NAMES = {"T10": "CC (T10): ' find' vs ' dfs'/' bfs'", "B3": "MST (B3): Kruskal vs Prim class"}


def save(fig: plt.Figure, name: str) -> None:
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"{name}.pdf")
    fig.savefig(FIG_DIR / f"{name}.png", dpi=200)
    plt.close(fig)
    logger.info(f"saved {name}")


def f1(w1: dict) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(10, 6.5))
    arms = ["ROWS_ALL", "ROWS_D", "ROWS_A", "NORM", "ROWS_NORM", "SIGN"]
    for r, u in enumerate(UNITS_TF):
        U = w1["units"][u]
        ax = axes[r, 0]
        sh = [U["arms"][a]["share"] for a in arms]
        ci = [U["arms"][a]["ci95"] for a in arms]
        y = np.arange(len(arms))
        ax.barh(y, sh, color=[C[a] for a in arms], alpha=0.85)
        ax.errorbar(sh, y, xerr=[[s - c[0] for s, c in zip(sh, ci)], [c[1] - s for s, c in zip(sh, ci)]], fmt="none",
                    ecolor="k", capsize=3, lw=1)
        ax.set_yticks(y, arms)
        ax.axvline(0, color="k", lw=0.8)
        ax.axvline(1, color="k", lw=0.8, ls=":")
        ax.set_xlabel("share of the gap closed (ratio of sums, 95% CI)")
        ax.set_title(f"{NAMES[u]}: readout arms on the instruct residual (gap {U['gap_mean']:.2f} nats)", fontsize=8.5)
        ax = axes[r, 1]
        allv = np.concatenate([U["nulls"][nt]["shares"] for nt in ("RAND_ISO", "DELTA_SWAP", "RAND_RESID")])
        lo, hi = np.percentile(allv, 1), np.percentile(allv, 99)
        lo, hi = min(lo, -0.3), max(hi, U["arms"]["ROWS_ALL"]["share"] + 0.2)
        bins = np.linspace(lo, hi, 40)
        for nt in ("RAND_ISO", "DELTA_SWAP", "RAND_RESID"):
            v = np.clip(U["nulls"][nt]["shares"], lo, hi)
            ax.hist(v, bins=bins, alpha=0.55, color=C[nt],
                    label=f"{nt} (median {U['nulls'][nt]['median']:.2f}, p95 {U['nulls'][nt]['p95']:.2f})")
        ax.axvline(U["arms"]["ROWS_ALL"]["share"], color=C["ROWS_ALL"], lw=2,
                   label=f"ROWS_ALL {U['arms']['ROWS_ALL']['share']:.2f} (p vs RAND_ISO = "
                         f"{U['nulls']['RAND_ISO']['empirical_p_rows_all']:.3f})")
        ax.set_xlabel("share closed by 50 null row edits (1-99% range shown)")
        ax.set_ylabel("draws")
        ax.legend(fontsize=6.5, frameon=False)
        ax.set_title(f"{u}: nulls (every S row moved by ||Delta_t||)", fontsize=8.5)
    save(fig, "F1_w1_shares_nulls")


def f2(w1: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
    for ax, u in zip(axes, UNITS_TF):
        U = w1["units"][u]
        gap = np.array(U["gap"])
        x = np.arange(len(gap))
        for a, off in (("ROWS_ALL", -0.15), ("ROWS_NORM", 0.0), ("ROWS_A", 0.15)):
            ax.scatter(x + off, U["arms"][a]["per_prompt_share"], s=12 + 18 * np.abs(gap), color=C[a], alpha=0.75,
                       label=a, edgecolor="k", lw=0.3)
        for i in np.nonzero(np.abs(gap) < 0.5)[0]:
            ax.annotate("gap<0.5", (i, U["arms"]["ROWS_ALL"]["per_prompt_share"][i]), fontsize=6)
        ax.axhline(0, color="k", lw=0.8)
        ax.axhline(1, color="k", lw=0.8, ls=":")
        ax.set_xticks(x, U["pids"], rotation=90, fontsize=5.5)
        ax.set_ylabel("per-prompt share closed")
        ax.set_title(f"{u}: per-prompt shares (point area ~ gap in nats)", fontsize=8.5)
        ax.legend(fontsize=7, frameon=False)
    save(fig, "F2_per_prompt_shares")


def f3(w1: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4))
    for ax, u in zip(axes, UNITS_TF):
        U = w1["units"][u]
        lams = [-1.0, 0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5]
        rows = [U["arms"]["SIGN"]["share"], 0.0] + [U["arms"][f"DOSE_{l:g}"]["share"] for l in lams[2:]]
        cur = U["nulls"]["RAND_ISO"]["dose_curve"]
        iso_med = [cur["-1"]["median_draw_share"], 0.0] + [cur[f"{l:g}"]["median_draw_share"] for l in lams[2:]]
        iso_all = [cur["-1"]["all_draws_median_share"], 0.0] + [cur[f"{l:g}"]["all_draws_median_share"]
                                                                for l in lams[2:]]
        ax.plot(lams, rows, "o-", color=C["ROWS_ALL"], label="base-row delta  w_I + lambda * Delta")
        ax.plot(lams, iso_med, "s--", color=C["RAND_ISO"], label="RAND_ISO median-share draw at lambda")
        ax.plot(lams, iso_all, "^:", color="#1a5276", label="median over the 50 RAND_ISO draws")
        ax.axhline(0, color="k", lw=0.8)
        ax.axhline(1, color="k", lw=0.8, ls=":")
        ax.set_xlabel("lambda (dose of the row edit)")
        ax.set_ylabel("share closed")
        ax.set_title(f"{u}: dose-response", fontsize=8.5)
        ax.legend(fontsize=6.5, frameon=False)
    save(fig, "F3_dose_response")


def f4(gen: dict) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(11, 7.6))
    for ax, u in zip(axes, ("T10", "B3")):
        G = gen["units"][u]
        arms = list(G["cells"])
        corr_lab = {"T10": "correct DFS", "B3": "correct Prim"}[u]
        corr = np.array([G["cells"][a]["n_correct"] for a in arms])
        n = np.array([G["cells"][a]["n"] for a in arms])
        fails = np.array([G["cells"][a]["n"] - G["cells"][a]["n_pass"] for a in arms])
        other = n - corr - fails
        x = np.arange(len(arms))
        ax.bar(x, corr, color="#c0392b", label=corr_lab)
        ax.bar(x, other, bottom=corr, color="#95a5a6", label="default class / other (passing)")
        ax.bar(x, fails, bottom=corr + other, color="#2c3e50", label="failing hidden tests")
        pred = [G["cells"][a]["predicted_correct_count"] for a in arms]
        ax.scatter(x, pred, marker="_", s=300, color="k", zorder=5, label="committed prediction (count)")
        for i, a in enumerate(arms):
            t = G["tests"].get(f"{a}_vs_TWIN")
            if t and a != "TWIN":
                ax.annotate(f"{t['b_first_only']}:{t['c_second_only']}\np={t['p_exact_two_sided']:.2g}", (i, 31),
                            ha="center", fontsize=6)
        ax.set_xticks(x, arms, rotation=25, fontsize=7)
        ax.set_ylim(0, 36)
        ax.set_ylabel("programs (30 CRN slots per arm)")
        ax.set_title(f"{u}: generation by fork arm (McNemar vs TWIN above bars)", fontsize=8.5)
        ax.legend(fontsize=6.5, frameon=False, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    save(fig, "F4_generation")


def f5_f6() -> None:
    from w1_tf import UnitData, load_readout
    units = read_json(I9_RES / "units.json")
    WI, gI = load_readout("qwen")
    WB, gB = load_readout("qwen_base")
    fig5, ax5 = plt.subplots(1, 2, figsize=(11, 4.6))
    fig6, ax6 = plt.subplots(1, 2, figsize=(10, 4.3))
    for k, u in enumerate(UNITS_TF):
        d = UnitData(u, units, WI, WB, gI, gB, need_logits=False)
        WI_S, WB_S = d.WI_S.double(), d.WB_S.double()
        dI = WI_S[:d.nD].mean(0) - WI_S[d.nD:].mean(0)
        dB = WB_S[:d.nD].mean(0) - WB_S[d.nD:].mean(0)
        u1 = dI / dI.norm()
        v = dB - (dB @ u1) * u1
        u2 = v / v.norm()
        H = torch.cat([d.hfI, d.hfB]).double()
        a, b = (H @ u1).numpy(), (H @ u2).numpy()
        off = H - torch.outer(H @ u1, u1) - torch.outer(H @ u2, u2)
        off_mean = off.mean(0)
        ga = np.linspace(a.min() - 0.15 * np.ptp(a), a.max() + 0.15 * np.ptp(a), 120)
        gb = np.linspace(b.min() - 0.25 * np.ptp(b), b.max() + 0.25 * np.ptp(b), 120)
        A_, B_ = np.meshgrid(ga, gb)
        G = (off_mean[None, None, :] + torch.from_numpy(A_)[..., None] * u1 + torch.from_numpy(B_)[..., None] * u2)
        G = G.reshape(-1, G.shape[-1])

        def mgrid(rows: torch.Tensor) -> np.ndarray:
            z = G @ rows.T
            return (torch.logsumexp(z[:, :d.nD], -1) - torch.logsumexp(z[:, d.nD:], -1)).numpy().reshape(A_.shape)
        MI, MB = mgrid(WI_S), mgrid(WB_S)
        ax = ax5[k]
        cs1 = ax.contour(A_, B_, MI, levels=7, colors=C["instr"], linewidths=0.8, alpha=0.8)
        ax.clabel(cs1, fontsize=5.5, fmt="%.1f")
        cs2 = ax.contour(A_, B_, MB, levels=7, colors=C["base"], linewidths=0.8, linestyles="--", alpha=0.8)
        ax.clabel(cs2, fontsize=5.5, fmt="%.1f")
        n = len(d.pids)
        ax.scatter(a[:n], b[:n], color=C["instr"], s=22, edgecolor="k", lw=0.3, label="instruct fork state h_fin")
        ax.scatter(a[n:], b[n:], color=C["base"], s=22, marker="s", edgecolor="k", lw=0.3,
                   label="base fork state h_fin")
        ax.plot([], [], color=C["instr"], lw=0.8, label="margin isolines, instruct S rows")
        ax.plot([], [], color=C["base"], lw=0.8, ls="--", label="margin isolines, base S rows (ROWS_ALL readout)")
        ax.set_xlabel("u1 = instruct readout direction (mean w_D - mean w_A), units of h")
        ax.set_ylabel("u2 = base readout direction, orthogonalised")
        ax.set_title(f"{u}: final-normed fork states on the readout plane\n(isolines through the mean off-plane "
                     f"component; cos(dI, dB) = {float(dI @ dB / dI.norm() / dB.norm()):.3f})", fontsize=8)
        ax.legend(fontsize=6, frameon=False, loc="best")
        # F6 PCA of block-35 outputs (final-norm inputs) at the fork
        P = torch.cat([d.hpI.float(), d.hpB.float()]).double()
        mu = P.mean(0)
        Uu, Ss, Vt = torch.linalg.svd(P - mu, full_matrices=False)
        pcs = Vt[:2]
        Y = ((P - mu) @ pcs.T).numpy()
        ev = (Ss ** 2 / (Ss ** 2).sum()).numpy()
        ax = ax6[k]
        ax.scatter(Y[:n, 0], Y[:n, 1], color=C["instr"], s=22, edgecolor="k", lw=0.3, label="instruct h_pre (fork)")
        ax.scatter(Y[n:, 0], Y[n:, 1], color=C["base"], s=22, marker="s", edgecolor="k", lw=0.3,
                   label="base h_pre (fork)")
        sc = 0.35 * np.abs(Y).max()
        for vec, col, lab in ((dI, C["instr"], "instruct readout direction"), (dB, C["base"], "base readout direction")):
            p2 = (pcs @ (vec / vec.norm())).numpy()
            ax.annotate("", xy=(sc * p2[0] / max(1e-9, np.linalg.norm(p2)) * min(1, 3 * np.linalg.norm(p2)),
                                sc * p2[1] / max(1e-9, np.linalg.norm(p2)) * min(1, 3 * np.linalg.norm(p2))),
                        xytext=(0, 0), arrowprops=dict(arrowstyle="->", color=col, lw=1.5))
            ax.plot([], [], color=col, label=f"{lab} (|proj| {np.linalg.norm(p2):.2f})")
        ax.set_xlabel(f"PC1 ({100 * ev[0]:.1f}% of variance)")
        ax.set_ylabel(f"PC2 ({100 * ev[1]:.1f}%)")
        ax.set_title(f"{u}: PCA of block-35 outputs at the fork (20 + 20 prompts)", fontsize=8.5)
        ax.legend(fontsize=6, frameon=False)
    fig5.tight_layout()
    save(fig5, "F5_readout_plane")
    save(fig6, "F6_pca_block35")


def f7(w2: dict) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(11, 6.5), gridspec_kw={"width_ratios": [2.2, 1]})
    for r, u in enumerate(UNITS_TF):
        W = w2["units"][u]
        A = W["scope_A_all_position"]
        ax = axes[r, 0]
        pairs = {int(k): int(v) for k, v in w2["matching"]["pairs_late_to_early"].items()}
        x = np.arange(len(LATE))
        late = [A[f"W{l}"]["share"] for l in LATE]
        early = [A.get(f"E_match{l}_L{pairs[l]}", {}).get("share", np.nan) for l in LATE]
        fork = [W["scope_B_fork_only"].get(f"Wf{l}", {}).get("share", np.nan) for l in LATE]
        ax.bar(x - 0.2, late, 0.4, color="#c0392b", label="late MLP l -> base (all positions)")
        ax.bar(x + 0.2, early, 0.4, color="#7f8c8d", label="matched early MLP -> base")
        ax.scatter(x - 0.2, fork, marker="D", color="k", s=14, zorder=5, label="late MLP l, fork-only (iter-9 W arm)")
        for j in range(3):
            rd = [A.get(f"RANDDELTA{l}_{j}", {}).get("share", np.nan) for l in LATE]
            ax.scatter(x - 0.2 + 0.08 * (j - 1), rd, marker="x", color="#3498db", s=16, zorder=6,
                       label="same-layer random delta (matched ||dW||)" if j == 0 else None)
        ax.set_xticks(x, [f"L{l}\n(E{pairs[l]})" for l in LATE], fontsize=7)
        ax.axhline(0, color="k", lw=0.8)
        ax.set_ylabel("share closed")
        ax.set_title(f"{u}: single-layer weight swaps (W2)", fontsize=8.5)
        ax.legend(fontsize=6, frameon=False)
        ax = axes[r, 1]
        dec = W["decomposition"]
        keys = [("readout_rows_norm", "readout (rows + norm)"), ("late_mlps_all_position", "late MLPs 26-35"),
                ("joint_late_mlps_plus_readout", "joint: late MLPs + readout"),
                ("late_attention_all_position", "late attention 26-35"),
                ("late_blocks_all_position", "late blocks (attn + MLP)"),
                ("joint_late_blocks_plus_readout", "joint: late blocks + readout")]
        vals = [dec.get(k) for k, _ in keys]
        rj = W["rule"].get("randdelta_joint_shares", [])
        ax.barh(np.arange(len(keys)), [v if v is not None else 0 for v in vals],
                color=["#2c3e50", "#c0392b", "#8e44ad", "#e67e22", "#d35400", "#6c3483"])
        ax.set_yticks(np.arange(len(keys)), [lbl for _, lbl in keys], fontsize=7)
        ax.axvline(0, color="k", lw=0.8)
        ax.axvline(1, color="k", lw=0.8, ls=":")
        ax.set_xlabel("share closed")
        ax.set_title(f"{u}: decomposition\n(E_joint {W['rule']['early_joint']:.2f}; random joint "
                     f"{', '.join(f'{v:.2f}' for v in rj)})", fontsize=7.5)
    save(fig, "F7_w2_swaps")


def f8(w3: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.4))
    arms = ["ROWS_ALL", "ROWS_D", "ROWS_A", "NORM", "ROWS_NORM", "SIGN"]
    ax = axes[0]
    sh = [w3["arms"][a]["share"] for a in arms]
    ci = [w3["arms"][a]["ci95"] for a in arms]
    y = np.arange(len(arms))
    ax.barh(y, sh, color=[C[a] for a in arms])
    ax.errorbar(sh, y, xerr=[[s - c[0] for s, c in zip(sh, ci)], [c[1] - s for s, c in zip(sh, ci)]], fmt="none",
                ecolor="k", capsize=3, lw=1)
    ax.set_yticks(y, arms)
    ax.axvline(0, color="k", lw=0.8)
    ax.set_xlabel("share closed")
    ax.set_title(f"Gemma-3-4b G-GRID@32 (gap {w3['gap_mean']:.2f} nats; output-only untying)", fontsize=8)
    ax = axes[1]
    for nt in ("RAND_ISO", "DELTA_SWAP"):
        ax.hist(w3["nulls"][nt]["shares"], bins=25, alpha=0.6, color=C[nt],
                label=f"{nt} (median {w3['nulls'][nt]['median']:.2f})")
    ax.axvline(w3["arms"]["ROWS_ALL"]["share"], color=C["ROWS_ALL"], lw=2, label="ROWS_ALL")
    ax.set_xlabel("share closed by 50 null row edits")
    ax.legend(fontsize=6.5, frameon=False)
    save(fig, "F8_w3_gemma")


def main() -> None:
    w1 = read_json(RESULTS_DIR / "w1_tf_summary.json")
    f1(w1)
    f2(w1)
    f3(w1)
    f4(read_json(RESULTS_DIR / "w1_generation.json"))
    if (RESULTS_DIR / "w2_summary.json").exists():
        f7(read_json(RESULTS_DIR / "w2_summary.json"))
    if (RESULTS_DIR / "w3_summary.json").exists():
        f8(read_json(RESULTS_DIR / "w3_summary.json"))
    f5_f6()


if __name__ == "__main__":
    setup_logging("figures10")
    main()
