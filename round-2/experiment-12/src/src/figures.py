#!/usr/bin/env python3
"""Figures (matplotlib, Agg; PNG + PDF in figures/) drawn only from the results/*.json files."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

from core import FIGS, RESULTS, TASKS, read_json  # noqa: E402

plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42, "ps.fonttype": 42, "axes.spines.top": False,
                     "axes.spines.right": False})
C = ["#3b6ea8", "#d1495b", "#66a182", "#edae49", "#7d5ba6", "#8d6a4f", "#4f4f4f"]


def _save(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(FIGS / f"{name}.png", dpi=170)
    fig.savefig(FIGS / f"{name}.pdf")
    plt.close(fig)


def fig_layer_probe() -> None:
    LP = read_json(RESULTS / "layer_probe.json")
    fig, axes = plt.subplots(1, 2, figsize=(8, 3), sharey=True)
    for ax, t in zip(axes, TASKS):
        for k, pos in enumerate(["k_pre", "k16", "k_fork", "k_post", "R"]):
            v = [LP["tasks"][t][f"{pos}|L{L}"]["raw_dim"]["auc_within"] for L in range(8, 29)]
            if all(x is None for x in v):
                continue
            ax.plot(range(8, 29), [np.nan if x is None else x for x in v], marker="o", ms=2.5, color=C[k], label=pos)
        ax.axhline(0.5, color="grey", lw=0.6, ls="--")
        for L in LP["choice"]["chosen"]:
            ax.axvline(L, color="grey", lw=0.5, alpha=0.5)
        ax.set_title(f"{t}: within-paraphrase DiM AUC (exp3 ban rows)")
        ax.set_xlabel("layer")
    axes[0].set_ylabel("held-out AUC (LOPO)")
    axes[1].legend(fontsize=7, frameon=False)
    _save(fig, "fig_layer_probe")


def fig_transfer() -> None:
    T = read_json(RESULTS / "transfer_summary.json")
    Ls = sorted(T["layers"], key=int)
    fig, axes = plt.subplots(1, 2, figsize=(7, 2.8))
    x = np.arange(len(Ls))
    axes[0].bar(x - 0.18, [T["layers"][L]["dce_inst"] for L in Ls], 0.36, color=C[0], label="instruct")
    axes[0].bar(x + 0.18, [T["layers"][L]["dce_base"] for L in Ls], 0.36, color=C[2], label="base")
    axes[0].set_xticks(x, [f"L{L}" for L in Ls])
    axes[0].set_ylabel("spliced-in dCE (nats/token)")
    axes[0].legend(frameon=False, fontsize=7)
    r = [T["layers"][L]["ratio"] for L in Ls]
    ci = [T["layers"][L]["ratio_ci95"] or [np.nan, np.nan] for L in Ls]
    axes[1].errorbar(x, r, yerr=[[a - c[0] for a, c in zip(r, ci)], [c[1] - a for a, c in zip(r, ci)]], fmt="o",
                     color=C[1], capsize=3)
    axes[1].axhline(1.5, color="grey", ls="--", lw=0.8)
    axes[1].set_xticks(x, [f"L{L}" for L in Ls])
    axes[1].set_ylabel("dCE_inst / dCE_base")
    axes[1].set_title("pass if <= 1.5", fontsize=8)
    _save(fig, "fig_transfer")


def fig_latent_vs_dim() -> None:
    D = read_json(RESULTS / "readout_i_discovery.json")
    R = read_json(RESULTS / "readout_i_replication.json", {})
    meths = ["sae_top1", "sae_top20_lr", "sae_code_dim", "raw_dim", "raw_lr", "neuron_top1", "neuron_top20_lr"]
    keys = [k for k, v in D["configs"].items() if "methods" in v and k.endswith("k_pre")] + \
           [k for k, v in D["configs"].items() if "methods" in v and k.endswith("k16")]
    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharey=True)
    w = 0.11
    for ax, title, src in ((axes[0], "discovery (exp3, nested LOPO): within-paraphrase AUC", "disc"),
                           (axes[1], "replication (exp3-fitted objects on the fresh pool): within-template AUC",
                            "rep")):
        x = np.arange(len(keys))
        for j, m in enumerate(meths):
            if src == "disc":
                v = [D["configs"][k]["methods"][m]["auc_within"] for k in keys]
                q = [D["configs"][k]["methods"][m].get("null_within_q95") for k in keys]
                ax.scatter(x + (j - 3) * w, [np.nan if a is None else a for a in q], marker="_", color="grey", s=30)
            else:
                v = [R.get("configs", {}).get(k, {}).get("transfer_from_exp3", {}).get(m, {}).get(
                    "auc_within_template") for k in keys]
            ax.bar(x + (j - 3) * w, [np.nan if a is None else a for a in v], w, color=C[j % len(C)], label=m)
        ax.axhline(0.5, color="grey", lw=0.6, ls="--")
        ax.set_xticks(x, [k.replace("|", " ") for k in keys], rotation=30, fontsize=7)
        ax.set_title(title, fontsize=9)
        ax.set_ylim(0, 1)
    axes[1].legend(ncol=7, fontsize=6, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.32))
    _save(fig, "fig_latent_vs_dim")


def fig_attention() -> None:
    A = read_json(RESULTS / "readout_ii_attention.json")
    ts = [t for t in TASKS if "heatmap_ban_minus_neutral_total" in A["tasks"].get(t, {})]
    if not ts:
        return
    fig, axes = plt.subplots(1, len(ts), figsize=(4.2 * len(ts), 3.6))
    axes = np.atleast_1d(axes)
    for ax, t in zip(axes, ts):
        M = np.array(A["tasks"][t]["heatmap_ban_minus_neutral_total"])
        v = np.nanmax(np.abs(M))
        im = ax.imshow(M.T, aspect="auto", cmap="RdBu_r", vmin=-v, vmax=v, origin="lower")
        ax.set_xlabel("layer")
        ax.set_ylabel("head")
        ax.set_title(f"{t}: attention mass k_pre -> segment, ban - neutral", fontsize=8)
        fig.colorbar(im, ax=ax, fraction=0.04)
    _save(fig, "fig_attention")


def fig_prime_veto() -> None:
    P = read_json(RESULTS / "readout_iii_prime_veto.json")
    keys = sorted(P["configs"])
    fig, axes = plt.subplots(1, 2, figsize=(9, 3))
    for ax, s in zip(axes, ("NAME_X", "IMPL_X")):
        x = np.arange(len(keys))
        for j, c in enumerate(("ban", "mention", "neutral")):
            v = [P["configs"][k]["positions"]["k_pre"][s]["means"][c] for k in keys]
            ax.bar(x + (j - 1) * 0.27, v, 0.27, color=C[j], label=c)
        ax.set_xticks(x, [k.replace("|", " ") for k in keys], rotation=30, fontsize=7)
        ax.set_title(f"{s}: summed latent activation at k_pre (same continuation)", fontsize=8)
    axes[0].legend(frameon=False, fontsize=7)
    _save(fig, "fig_prime_veto")


def fig_thought_anchors() -> None:
    TA = read_json(RESULTS / "thought_anchors.json")
    tr = TA.get("traces", {})
    if not tr:
        return
    n = len(tr)
    fig, axes = plt.subplots(n, 1, figsize=(7, 1.4 * n), sharex=True)
    axes = np.atleast_1d(axes)
    cat_col = {"BAN_RESTATEMENT": C[1], "SUBSTITUTE_NAMING": C[2], "ALTERNATIVE_LISTING": C[3],
               "PROBLEM_RESTATEMENT": C[0], "OTHER": C[6], "OTHER_MECHANISM": C[4]}
    for ax, (tid, r) in zip(axes, sorted(tr.items(), key=lambda kv: int(kv[0]))):
        k = np.arange(1, len(r["tvd"]) + 1)
        ax.bar(k, r["tvd"], color=[cat_col.get(c, C[6]) for c in r["sentence_categories"][:len(k)]])
        ax.plot(k, r["noise_floor_q95"], "k_", ms=10)
        ax.set_ylabel(f"tr {tid}\n{r['task']}", fontsize=7)
        ax.set_ylim(0, 1)
    axes[-1].set_xlabel("sentence k (TVD between D_k and D_k-1; black: 95% multinomial floor)")
    handles = [plt.Rectangle((0, 0), 1, 1, color=v) for v in cat_col.values()]
    axes[0].legend(handles, list(cat_col), ncol=3, fontsize=6, frameon=False)
    _save(fig, "fig_thought_anchors")


def fig_same_seed() -> None:
    S = read_json(RESULTS / "same_seed.json")
    fig, axes = plt.subplots(2, 2, figsize=(8, 5.2), sharex=True)
    Ts = [0.7, 1.0, 1.3]
    for col, t in enumerate(TASKS):
        for row, (metric, ylab) in enumerate((("idea_change_rate", "P(label_T != label_0.3)"),
                                              ("phrasing_change_rate_theta0.8", "P(Jaccard < 0.8 | same label)"))):
            ax = axes[row, col]
            for j, cond in enumerate(("baseline", "ban")):
                for kind, ls in (("same_seed", "-"), ("different_seed", ":")):
                    v = [S["cells"].get(f"{t}|{cond}|T{T}", {}).get(kind, {}).get(metric) for T in Ts]
                    ax.plot(Ts, [np.nan if a is None else a for a in v], ls, marker="o", color=C[j],
                            label=f"{cond} {kind.replace('_', '-')}")
            ax.set_ylim(-0.03, 1.03)
            if col == 0:
                ax.set_ylabel(ylab, fontsize=8)
            if row == 0:
                ax.set_title(f"{t}: change vs the same seed's T=0.3 program (CRN)", fontsize=8)
            else:
                ax.set_xlabel("temperature T")
    axes[0, 1].legend(fontsize=6, frameon=False)
    _save(fig, "fig_same_seed")


def fig_jlens() -> None:
    J = read_json(RESULTS / "jlens.json", {})
    if not J:
        return
    g = J["gate"]
    Ls = sorted(g["layers"], key=int)
    o = g["orientation"]
    fig, ax = plt.subplots(figsize=(4.5, 2.8))
    ax.plot([int(L) for L in Ls], [g["layers"][L]["logit_lens"]["top1"] for L in Ls], "o-", color=C[0],
            label="logit lens")
    ax.plot([int(L) for L in Ls], [g["layers"][L][f"jlens_{o}"]["top1"] for L in Ls], "o-", color=C[1],
            label=f"J-lens ({o})")
    ax.set_xlabel("source layer")
    ax.set_ylabel("top-1 agreement with model")
    ax.legend(frameon=False, fontsize=7)
    ax.set_title(f"J-lens gate: pass={g['gate_pass']}", fontsize=8)
    _save(fig, "fig_jlens")


def run_figures() -> None:
    for fn in (fig_layer_probe, fig_transfer, fig_latent_vs_dim, fig_attention, fig_prime_veto, fig_thought_anchors,
               fig_same_seed, fig_jlens):
        try:
            fn()
            logger.info(f"figure {fn.__name__} written")
        except Exception as e:  # noqa: BLE001 - a missing input skips that figure only
            logger.warning(f"figure {fn.__name__} skipped: {e!r}")
