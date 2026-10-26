"""Figures F1-F6 (PDF + PNG) from results/*.json; every number plotted is read from those files."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FIGS, RESULTS  # noqa: E402

plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 150})
COL = {"T1.0": "#0072B2", "T1.6": "#E69F00", "DTB": "#D55E00", "RPB": "#009E73", "IDEA": "#CC79A7",
       "NOSEL": "#56B4E9"}
ARMS = ["T1.0", "T1.6", "DTB", "RPB", "IDEA"]


def save(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(FIGS / f"{name}.pdf")
    fig.savefig(FIGS / f"{name}.png", dpi=200)
    plt.close(fig)


def f1(cl: dict) -> None:
    fig, ax = plt.subplots(2, 2, figsize=(9, 6.4), sharex=True)
    for j, s in enumerate((0, 1)):
        for i, kind in enumerate(("discovery_primary", "discovery_secondary")):
            a = ax[i, j]
            for arm in ARMS:
                d = cl["per_arm_seed"].get(f"{arm}|{s}")
                if d:
                    a.plot(np.arange(1, len(d[kind]) + 1), d[kind], color=COL[arm], lw=1.5,
                           label=f"{arm} ({d['primary_clusters' if i == 0 else 'secondary_clusters']})")
            if i == 0:
                for arm in ARMS:
                    r = cl.get("rarefaction", {}).get(f"{arm}|{s}")
                    d = cl["per_arm_seed"].get(f"{arm}|{s}")
                    if r and d:
                        a.errorbar(d["calls"] * 1.02, r["mean"], yerr=[[r["mean"] - r["lo"]], [r["hi"] - r["mean"]]],
                                   fmt="o", ms=3, color=COL[arm], capsize=2)
            a.set_title(f"seed {s}: {'primary (probe-valid)' if i == 0 else 'secondary (probe-valid, F < 1)'}")
            a.set_ylabel("distinct behaviour clusters")
            a.legend(fontsize=7, frameon=False)
            if i == 1:
                a.set_xlabel("calls")
    fig.suptitle("F1. Discovery curves (complete linkage, agreement >= 0.95; dots: rarefied to equal probe-valid N, 95% band)",
                 fontsize=9)
    save(fig, "F1_discovery_curves")


def f2(ss: dict) -> None:
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.4), sharey=True)
    for j, s in enumerate((0, 1)):
        for arm in ARMS + ["NOSEL"]:
            d = ss["per_arm_seed"].get(f"{arm}|{s}")
            if d:
                y = [np.nan if v is None else v for v in d["best_so_far_F"]]
                ax[j].plot(np.arange(1, len(y) + 1), y, color=COL[arm], lw=1.5, label=f"{arm} (N={d['calls']})")
        ax[j].axhline(1.0, color="grey", ls=":", lw=1)
        ax[j].set_title(f"seed {s}")
        ax[j].set_xlabel("calls")
        ax[j].legend(fontsize=7, frameon=False)
    ax[0].set_ylabel("best-so-far F (NN = 1, lower is better)")
    fig.suptitle("F2. Best-so-far selection fitness F of probe-valid programs", fontsize=9)
    save(fig, "F2_best_so_far")


def f3(held: dict, base: dict) -> None:
    items = []
    for k, v in held.get("arm_best", {}).items():
        if v.get("G200") is not None and "_first" not in k:
            items.append((k, v.get("G200"), v.get("G200_ext"), v.get("tsplib_mean"), v.get("ci_vs_NN"),
                          COL.get(k.split("|")[0], "k")))
    for k, v in held.get("others", {}).items():
        if v.get("G200") is not None:
            items.append((k, v["G200"], v.get("G200_ext"), v.get("tsplib_mean"), v.get("ci_vs_NN"), "#777777"))
    items.sort(key=lambda t: t[1])
    fig, ax = plt.subplots(1, 3, figsize=(12, 0.28 * len(items) + 1.5), sharey=True)
    y = np.arange(len(items))
    nn = base["NN"]
    for p, (idx, title, ref) in enumerate(((1, "held-out n=200 (32 inst.)", nn["G200"]),
                                           (2, "extended n=200 (96 inst.)", nn["G200_ext"]),
                                           (3, "TSPLIB (13 inst., EUC_2D)", nn["tsplib"]["mean_gap"]))):
        vals = [t[idx] if t[idx] is not None else np.nan for t in items]
        ax[p].barh(y, vals, color=[t[5] for t in items], alpha=0.85)
        if p == 0:
            for yy, t in zip(y, items):
                ci = t[4]
                if ci:
                    ax[p].errorbar(nn["G200"] + ci["mean_diff"], yy, xerr=[[ci["mean_diff"] - ci["lo"]],
                                                                         [ci["hi"] - ci["mean_diff"]]],
                                   fmt="none", ecolor="k", capsize=2, lw=0.8)
        xmax = 60.0  # outliers (LLM4AD placeholder, angle sweep, look-ahead) are clipped and labelled
        ax[p].set_xlim(0, xmax)
        for yy, vv in zip(y, vals):
            if np.isfinite(vv) and vv > xmax:
                ax[p].text(xmax * 0.98, yy, f"{vv:.0f} >", ha="right", va="center", fontsize=6, color="w")
        ax[p].axvline(ref, color="k", ls="--", lw=1, label="NN")
        if p == 0:
            ax[p].axvline(0.8 * ref, color="r", ls=":", lw=1, label="V1 bar 0.8 x NN")
        ax[p].set_title(title)
        ax[p].set_xlabel("mean optimality gap (%)")
        ax[p].legend(fontsize=7, frameon=False)
    ax[0].set_yticks(y)
    ax[0].set_yticklabels([t[0] for t in items], fontsize=7)
    fig.suptitle("F3. Held-out gaps of each arm-seed's selection-best program vs NN, P1 and the corpus "
                 "(whiskers: paired 95% bootstrap CI of the difference to NN, drawn at NN + diff)", fontsize=9)
    save(fig, "F3_heldout")


def f4(ss: dict, rows: list[dict]) -> None:
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
    keys = [f"{a}|{s}" for a in ARMS for s in (0, 1) if f"{a}|{s}" in ss["per_arm_seed"]]
    v = [ss["per_arm_seed"][k]["validity"] for k in keys]
    lo = [ss["per_arm_seed"][k]["validity_wilson95"][0] for k in keys]
    hi = [ss["per_arm_seed"][k]["validity_wilson95"][1] for k in keys]
    x = np.arange(len(keys))
    ax[0].bar(x, v, color=[COL[k.split("|")[0]] for k in keys])
    ax[0].errorbar(x, v, yerr=[np.array(v) - lo, np.array(hi) - v], fmt="none", ecolor="k", capsize=2)
    ax[0].set_xticks(x)
    ax[0].set_xticklabels(keys, rotation=60, fontsize=7)
    ax[0].set_ylabel("validity (Wilson 95%)")
    data = [[r["F"] for r in rows if f"{r['arm']}|{r['seed']}" == k and r.get("F") is not None] for k in keys]
    bp = ax[1].boxplot(data, showfliers=False, patch_artist=True)
    for patch, k in zip(bp["boxes"], keys):
        patch.set_facecolor(COL[k.split("|")[0]])
    ax[1].axhline(1.0, color="grey", ls=":")
    ax[1].set_xticks(np.arange(1, len(keys) + 1))
    ax[1].set_xticklabels(keys, rotation=60, fontsize=7)
    ax[1].set_ylabel("F of valid programs (NN = 1)")
    fig.suptitle("F4. Validity and fitness distributions per arm and seed", fontsize=9)
    save(fig, "F4_validity_F")


def f5(ss: dict) -> None:
    dg = ss["dtb_rpb_diagnostics"]
    fig, ax = plt.subplots(1, 4, figsize=(13, 3.2))
    for arm in ("DTB", "RPB"):
        H = sum((dg.get(f"{arm}|{s}", {}).get("H_j_star_values", []) for s in (0, 1)), [])
        ax[0].hist(H, bins=30, alpha=0.6, color=COL[arm], label=f"{arm} (n={len(H)})")
        pos = sum(([p for p in dg.get(f"{arm}|{s}", {}).get("position_frac", []) if p is not None] for s in (0, 1)), [])
        ax[1].hist(pos, bins=24, alpha=0.6, color=COL[arm], label=arm)
        rk = {}
        for s in (0, 1):
            for k, c in dg.get(f"{arm}|{s}", {}).get("forced_rank_hist", {}).items():
                rk[int(k)] = rk.get(int(k), 0) + c
        vb = {}
        for s in (0, 1):
            for k, c in dg.get(f"{arm}|{s}", {}).get("validity_by_forced_rank", {}).items():
                vb.setdefault(int(k), []).append(c)
        ks = sorted(vb)
        ax[2].plot(ks, [np.mean(vb[k]) for k in ks], "o-", color=COL[arm], label=arm)
        cls = {}
        for s in (0, 1):
            for k, c in dg.get(f"{arm}|{s}", {}).get("forced_class_shares", {}).items():
                cls[k] = cls.get(k, 0) + c / 2
        order = ["identifier", "keyword", "operator", "number", "comment-opener", "string-opener"]
        off = -0.2 if arm == "DTB" else 0.2
        ax[3].bar(np.arange(len(order)) + off, [cls.get(o, 0) for o in order], width=0.4, color=COL[arm], label=arm)
        ax[3].set_xticks(np.arange(len(order)))
        ax[3].set_xticklabels(order, rotation=45, fontsize=7)
    ax[0].set_title("entropy H at j* (nats)")
    ax[1].set_title("j* / m (position in request 1)")
    ax[2].set_title("validity by forced rank")
    ax[3].set_title("lexical class of the forced token")
    for a in ax:
        a.legend(fontsize=7, frameon=False)
    fig.suptitle("F5. DTB vs RPB branching diagnostics (both seeds)", fontsize=9)
    save(fig, "F5_dtb_diagnostics")


def f6(held: dict) -> None:
    from probes import nn_tour
    from tsp_task import load_tsplib

    best_key, best = None, None
    for k, v in held.get("arm_best", {}).items():
        if v.get("G200") is not None and "_first" not in k and (best is None or v["G200"] < best["G200"]):
            best_key, best = k, v
    if not best or not best.get("tsplib_tours"):
        return
    ts = {t["name"]: t for t in load_tsplib()}
    fig, ax = plt.subplots(2, 2, figsize=(9, 8.5))
    for i, nm in enumerate(("kroA100", "ch150")):
        t = ts[nm]
        C, Di = t["coords"], t["D_int"]
        for j, (lab, tour) in enumerate((("NN", nn_tour(t["D_norm"])), (best_key, best["tsplib_tours"].get(nm)))):
            if tour is None:
                continue
            tr = np.asarray(tour + [tour[0]])
            cost = int(Di[np.asarray(tour), np.roll(np.asarray(tour), -1)].sum())
            g = 100 * (cost - t["opt"]) / t["opt"]
            a = ax[i, j]
            a.plot(C[tr, 0], C[tr, 1], "-", lw=0.8, color=COL.get(lab.split("|")[0], "k"))
            a.plot(C[:, 0], C[:, 1], "o", ms=2.5, color="k")
            a.plot(C[0, 0], C[0, 1], "s", ms=6, color="r")
            a.set_title(f"{nm}: {lab}  cost {cost}, gap {g:.2f}% (opt {t['opt']})", fontsize=8)
            a.set_xticks([])
            a.set_yticks([])
    fig.suptitle(f"F6. Tours of the overall best program ({best_key}) beside NN (start city in red)", fontsize=9)
    save(fig, "F6_tours")


def main() -> None:
    FIGS.mkdir(exist_ok=True)
    cl = json.loads((RESULTS / "clusters.json").read_text())
    ss = json.loads((RESULTS / "search_summary.json").read_text())
    base = json.loads((RESULTS / "baselines.json").read_text())
    from common import DATA, read_jsonl

    rows = read_jsonl(DATA / "calls.jsonl")
    f1(cl)
    f2(ss)
    f4(ss, rows)
    f5(ss)
    hp = RESULTS / "heldout.json"
    if hp.exists():
        held = json.loads(hp.read_text())
        f3(held, base)
        f6(held)
    print("figures written:", sorted(p.name for p in FIGS.glob("*.png")))


if __name__ == "__main__":
    main()
