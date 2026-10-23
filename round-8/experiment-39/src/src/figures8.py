#!/usr/bin/env python3
"""Figures F1-F8 (PDF + PNG, matplotlib, colour-blind palette) from the committed table and the observed rows.
F1 predicted vs observed off-default share vs log T; F2 quality-diversity (Hill-1 vs pass cost) with bootstrap
ellipses; F3 twin decision-token entropy vs q90_u; F4 token-map waterfalls; F5 HR branch maps; F6 locator profiles;
F7 CRN flip matrices; F8 activation geometry (PCA of the final-norm hidden states, mean of the 16 positions from the
decision token) with the nearest-centroid on-manifold check (centroids: class-forced A11 slots).
"""

from __future__ import annotations

import glob
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg8 import (CACHE_DIR, FIG_DIR, PRED_DIR, RESULTS_DIR, TEMPLATES, UNITS, read_json, read_jsonl,  # noqa: E402
                  write_json)
import analysis_k1 as AK  # noqa: E402
import predict8 as PR  # noqa: E402

plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42, "ps.fonttype": 42, "axes.spines.top": False,
                     "axes.spines.right": False})
PAL = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00", "#F0E442", "#000000", "#999999", "#882255",
       "#44AA99", "#117733"]
ARM_COL = {"A0": "#000000", "A1": "#56B4E9", "A2": "#0072B2", "A3g": "#003f6b", "A4": "#999999", "A5": "#009E73",
           "A6": "#44AA99", "A7": "#CC79A7", "A8": "#882255", "A9": "#E69F00", "A10": "#D55E00", "A11": "#F0E442",
           "B1": "#117733", "A9f": "#a65628", "A10f": "#7f2704"}


def save(fig, name: str) -> None:
    fig.savefig(FIG_DIR / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIG_DIR / f"{name}.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def f1(c1, cells):
    units = [u for u, e in c1["units"].items() if e.get("role") not in (None, "boundary") and u in cells]
    if not units:
        return
    fig, axs = plt.subplots(1, len(units), figsize=(3.2 * len(units), 2.9), squeeze=False)
    for ax, u in zip(axs[0], units):
        e = c1["units"][u]
        Ts = sorted(float(t) for t in e["share_curve"])
        ax.plot(Ts, [e["share_curve"][str(t) if str(t) in e["share_curve"] else t] for t in Ts], color="#333333",
                lw=1.2, label="committed prediction")
        for a, T in (("A9", e["dose"]["d1"]), ("A10", e["dose"]["d2"])):
            if a in cells[u]:
                c = cells[u][a]
                x = round(c["off_default_attempted"] * c["n"])
                lo, hi = PR.wilson(x, c["n"])
                ax.errorbar([T], [c["off_default_attempted"]], yerr=[[c["off_default_attempted"] - lo],
                                                                     [hi - c["off_default_attempted"]]],
                            fmt="o", color=ARM_COL[a], label=f"{a} fork dose T={T:g}")
        c3p = PRED_DIR / "commit3_amendment.json"
        if c3p.exists():
            e3 = read_json(c3p)["units"].get(u)
            for a in ("A9f", "A10f"):
                if e3 and a in cells[u]:
                    T = e3["arms"][a]["T"]
                    c = cells[u][a]
                    ax.plot([T], [c["off_default_attempted"]], "D", color=ARM_COL[a], ms=5,
                            label=f"{a} filtered fork dose T={T:g} (amendment)")
        for a, T in (("A0", 1.0), ("A1", 1.3), ("A2", 1.6), ("A3g", 2.0)):
            if a in cells[u]:
                ax.plot([T], [cells[u][a]["off_default_attempted"]], "s", color=ARM_COL[a], ms=5,
                        label=f"{a} global T={T:g}" if a != "A0" else "twin")
        ax.set_xscale("log")
        ax.set_title(u)
        ax.set_xlabel("T (fork arms: decision token only;\nglobal arms: every token), log scale", fontsize=7)
        ax.set_ylim(-0.02, 1.0)
        ax.legend(fontsize=5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=2)
    axs[0][0].set_ylabel("off-default attempted share")
    save(fig, "F1_dose_response")


def ellipse(ax, xs, ys, col):
    if len(xs) < 5:
        return
    cov = np.cov(xs, ys)
    if not np.all(np.isfinite(cov)):
        return
    vals, vecs = np.linalg.eigh(cov)
    t = np.linspace(0, 2 * np.pi, 80)
    circ = np.stack([np.cos(t), np.sin(t)])
    pts = vecs @ (np.sqrt(np.maximum(vals, 0))[:, None] * 2.0 * circ)
    ax.plot(np.mean(xs) + pts[0], np.mean(ys) + pts[1], color=col, lw=0.6, alpha=0.6)


def f2(data, cells):
    units = [u for u in cells if len(cells[u]) > 3]
    if not units:
        return
    fig, axs = plt.subplots(1, len(units), figsize=(3.2 * len(units), 3.0), squeeze=False)
    rng = np.random.default_rng(7)
    for ax, u in zip(axs[0], units):
        tw = data[u]["A0"]
        slots = sorted(tw)
        for a, c in cells[u].items():
            h = c["hill1_correct_r25"]
            if h is None:
                continue
            ax.scatter([c["pass_cost"]], [h], color=ARM_COL.get(a, "#777777"), s=22, zorder=3)
            ax.annotate(a, (c["pass_cost"], h), fontsize=6, xytext=(2, 2), textcoords="offset points")
            xs, ys = [], []
            for _ in range(200):
                idx = rng.integers(0, len(slots), len(slots))
                rr = [data[u][a].get(slots[i]) for i in idx]
                if any(r is None for r in rr):
                    break
                hh = PR.hill1_rarefied([r["cls"] for r in rr if r["passed"]], 25)
                if hh is None:
                    continue
                xs.append(np.mean([tw[slots[i]]["passed"] for i in idx]) - np.mean([r["passed"] for r in rr]))
                ys.append(hh)
            ellipse(ax, np.array(xs), np.array(ys), ARM_COL.get(a, "#777777"))
        ax.axhline(1.8, ls=":", color="#999999", lw=0.8)
        ax.axvline(0.05, ls=":", color="#999999", lw=0.8)
        ax.set_title(u)
        ax.set_xlabel("pass cost vs twin")
    axs[0][0].set_ylabel("correct-only Hill-1 (rarefied 25)")
    save(fig, "F2_quality_diversity")


def f3(c1, data):
    units = [u for u, e in c1["units"].items() if e.get("q90") is not None and u in data]
    if not units:
        return
    fig, axs = plt.subplots(1, len(units), figsize=(2.6 * len(units), 2.4), squeeze=False)
    for ax, u in zip(axs[0], units):
        H = [r["decision_H1"] for r in data[u]["A0"].values() if r.get("decision_H1") is not None]
        ax.hist(H, bins=20, color="#0072B2", alpha=0.8)
        ax.axvline(c1["units"][u]["q90"], color="#D55E00", ls="--", label="q90 (steps 1-64)")
        ax.set_title(u)
        ax.set_xlabel("T=1 entropy at decision (nats)")
    axs[0][0].legend(fontsize=6, frameon=False)
    save(fig, "F3_decision_entropy")


def f4(c1):
    items = []
    for u, e in c1["units"].items():
        for nd, tm in (e.get("token_map") or {}).items():
            items.append((u, nd, tm))
        if e.get("token_map_n11"):
            items.append((u, "n11", e["token_map_n11"]))
    if not items:
        return
    fig, axs = plt.subplots(len(items), 1, figsize=(8, 2.5 * len(items)), squeeze=False)
    fig.subplots_adjust(hspace=1.05)
    for ax, (u, nd, tm) in zip(axs[:, 0], items):
        info = read_json(CACHE_DIR / "nodes" / f"{u}_{nd}.json")
        toks = info["map_tokens"][:20]
        cats = UNITS[u]["catalogue"] + ["other", "invalid"]
        x = np.arange(len(toks))
        bottom = np.zeros(len(toks))
        for ci, cname in enumerate(cats):
            v = np.array([tm.get(str(t), {}).get("counts", {}).get(cname, 0) / max(tm.get(str(t), {}).get("n", 1), 1)
                          for t in toks])
            if v.sum() == 0:
                continue
            ax.bar(x, v, bottom=bottom, color=PAL[ci % len(PAL)], label=cname, width=0.8)
            bottom += v
        p1 = [info["pooled_p20"].get(str(t), 0) for t in toks]
        ax2 = ax.twinx()
        ax2.plot(x, np.log10(np.maximum(p1, 1e-12)), "k.-", lw=0.8, ms=3)
        ax2.set_ylabel("log10 T=1 mass", fontsize=6)
        ax.set_xticks(x)
        ax.set_xticklabels([repr(info["map_token_str"].get(str(t), "?"))[1:-1][:10] for t in toks], rotation=60,
                           fontsize=6)
        ax.set_ylabel(f"{u}/{nd}\nclass share", fontsize=7)
        ax.legend(fontsize=5, frameon=False, ncol=6, loc="upper right")
        pf = [tm.get(str(t), {}).get("pfail", 0) for t in toks]
        for xi, f in zip(x, pf):
            if f > 0:
                ax.text(xi, 1.02, f"{f:.1f}", ha="center", fontsize=5, color="#D55E00")
    save(fig, "F4_token_maps")


def f5(hr):
    units = list((hr or {}).get("units", {}))
    if not units:
        return
    from cfg8 import CONT_LABELS, CONTS
    labels = {r["sid"]: r for r in read_jsonl(CONT_LABELS)}
    fig, axs = plt.subplots(len(units), 1, figsize=(9, 1.8 * len(units)), squeeze=False)
    for ax, u in zip(axs[:, 0], units):
        rows = [r for r in read_jsonl(CONTS) if r["unit"] == u and (r.get("arm") == "HR" or
                                                                    (r.get("arm") == "MAP" and r.get("k", 9) < 5))]
        ideas = sorted({AK.cls(u, labels.get(r["sid"], {}).get("label")) for r in rows})
        nodes = sorted({r["node"] for r in rows})
        M = np.full((len(ideas), 64 * len(nodes)), np.nan)
        for ni, nd in enumerate(nodes):
            info = read_json(CACHE_DIR / "nodes" / f"{u}_{nd}.json")
            import arms8
            rank_of = {t: r for r, t in arms8.hr_tokens(info)}
            for r in rows:
                if r["node"] != nd:
                    continue
                rk = r.get("rank") or rank_of.get(int(r["token"]))
                if not rk or rk > 64:
                    continue
                L = labels.get(r["sid"], {})
                i = ideas.index(AK.cls(u, L.get("label")))
                j = ni * 64 + rk - 1
                M[i, j] = (0 if np.isnan(M[i, j]) else M[i, j]) + (1.0 if L.get("passed") else 0.25) / 5
        ax.imshow(M, aspect="auto", cmap="viridis", interpolation="nearest", vmin=0, vmax=1)
        ax.set_yticks(range(len(ideas)))
        ax.set_yticklabels(ideas, fontsize=6)
        ax.set_title(f"{u}: nodes {', '.join(nodes)} (rank 1-64 each); colour = correct share", fontsize=7)
    save(fig, "F5_hr_branch_maps")


def f6(loc):
    if not loc:
        return
    units = list(loc["units"])
    fig, axs = plt.subplots(1, len(units), figsize=(4 * len(units), 2.6), squeeze=False)
    for ax, u in zip(axs[0], units):
        for p, v in loc["units"][u]["paths"].items():
            S = np.array(v["series"])
            cats = list(UNITS[u]["catalogue"]) + ["other", "invalid", "undecided"]
            oi = cats.index(v["own_class"]) if v["own_class"] in cats else 0
            share = S[:, oi] / np.maximum(S.sum(1), 1)
            ax.plot(v["js"], share, marker=".", lw=0.8, label=f"path {p} ({v['own_class']})")
            for x in v["located_index"]:
                ax.axvline(x, color="#D55E00", lw=0.5, ls=":")
        for k in loc["units"][u]["known_indices"]:
            ax.axvline(k, color="#999999", lw=1.2, alpha=0.4)
        ax.set_title(u)
        ax.set_xlabel("prefix length j")
        ax.set_ylabel("own-class share of 8 continuations")
        ax.legend(fontsize=5, frameon=False)
    save(fig, "F6_locator_profiles")


def f7(data):
    units = [u for u in data if len(data[u]) > 3]
    if not units:
        return
    arms = ["A1", "A3g", "A5", "A6", "A7", "A8", "A9", "A10", "A11"]
    fig, axs = plt.subplots(len(units), len(arms), figsize=(1.5 * len(arms), 1.5 * len(units)), squeeze=False)
    for i, u in enumerate(units):
        cats = list(UNITS[u]["catalogue"]) + ["other", "invalid"]
        cats = [c for c in cats if any(r["cls"] == c for a in data[u] for r in data[u][a].values())]
        for j, a in enumerate(arms):
            ax = axs[i][j]
            ax.set_xticks([])
            ax.set_yticks([])
            if a not in data[u]:
                ax.axis("off")
                continue
            M = np.zeros((len(cats), len(cats)))
            for s, r in data[u][a].items():
                t = data[u]["A0"].get(s)
                if t and t["cls"] in cats and r["cls"] in cats:
                    M[cats.index(t["cls"]), cats.index(r["cls"])] += 1
            ax.imshow(M, cmap="Blues", vmin=0, vmax=max(M.max(), 1))
            for x in range(len(cats)):
                for y in range(len(cats)):
                    if M[y, x]:
                        ax.text(x, y, int(M[y, x]), ha="center", va="center", fontsize=5)
            if i == 0:
                ax.set_title(a, fontsize=7)
            if j == 0:
                ax.set_ylabel(u + "\n" + "/".join(c[:4] for c in cats), fontsize=5)
    save(fig, "F7_crn_flip_matrices")


def f8(data):
    """PCA of the mean final-norm hidden state over the 16 positions from the decision token."""
    H: dict[str, np.ndarray] = {}            # sid -> state (Qwen 4096-d, Gemma 2560-d: never mixed in one PCA)
    for f in sorted(glob.glob(str(CACHE_DIR / "hid" / "*.npz"))):
        z = np.load(f, allow_pickle=False)
        for s_, v in zip(z["sids"], z["H"]):
            H[str(s_)] = v.astype(np.float32)
    if not H:
        return {}
    idx = {s: s for s in H}
    out = {}
    units = [u for u in ("T10", "B3", "A3", "B6", "G", "T1") if u in data]
    fig, axs = plt.subplots(1, len(units), figsize=(3.3 * len(units), 3.1), squeeze=False)
    for ax, u in zip(axs[0], units):
        rows = [(a, r) for a in ("A0", "A9", "A10", "A11", "A1", "A3g") if a in data[u] for r in data[u][a].values()
                if r["sid"] in idx]
        if len(rows) < 10:
            ax.axis("off")
            continue
        X = np.stack([H[idx[r["sid"]]] for _, r in rows])
        mu = X.mean(0)
        U_, S_, Vt = np.linalg.svd(X - mu, full_matrices=False)
        ev = (S_ ** 2) / np.sum(S_ ** 2)
        P = (X - mu) @ Vt[:2].T
        cats = sorted({r["cls"] for _, r in rows})
        mk = {"A0": "o", "A9": "^", "A10": "v", "A11": "s", "A1": "x", "A3g": "+"}
        for (a, r), p in zip(rows, P):
            ax.scatter(p[0], p[1], marker=mk[a], s=12, color=PAL[cats.index(r["cls"]) % len(PAL)], alpha=0.75,
                       linewidths=0.6)
        for ci, c in enumerate(cats):
            ax.scatter([], [], color=PAL[ci % len(PAL)], label=c, s=12)
        for a, m in mk.items():
            ax.scatter([], [], marker=m, color="#555555", label=a, s=12)
        ax.set_title(f"{u}: PC1 {ev[0]:.0%} / PC2 {ev[1]:.0%}")
        ax.set_xlabel("PC1 (final-norm state, decision..+15)")
        ax.set_ylabel("PC2")
        ax.legend(fontsize=5, frameon=False, ncol=2)
        # nearest-centroid on-manifold check: centroids from class-forced (A11) slots by program label
        cent = {}
        for c in cats:
            pts = [H[idx[r["sid"]]] for a, r in rows if a == "A11" and r["cls"] == c]
            if len(pts) >= 2:
                cent[c] = np.mean(pts, 0)
        agree = n = 0
        for a, r in rows:
            if a in ("A9", "A10") and cent and r["cls"] in cent:
                d = {c: np.linalg.norm(H[idx[r["sid"]]] - v) for c, v in cent.items()}
                agree += int(min(d, key=d.get) == r["cls"])
                n += 1
        out[u] = {"explained_variance_pc1_pc2": ev[:2].tolist(), "n_states": len(rows),
                  "nearest_centroid_agreement_fork_dosed": agree / n if n else None, "n_fork_dosed_scored": n,
                  "centroid_classes": sorted(cent)}
    save(fig, "F8_activation_geometry")
    return out


def main() -> None:
    c1 = read_json(PRED_DIR / "commit1_dose_table.json")
    data = AK.load_rows()
    cells = read_json(RESULTS_DIR / "k1_cells.json") if (RESULTS_DIR / "k1_cells.json").exists() else {}
    hr = read_json(RESULTS_DIR / "hr.json") if (RESULTS_DIR / "hr.json").exists() else None
    loc = read_json(RESULTS_DIR / "locator.json") if (RESULTS_DIR / "locator.json").exists() else None
    geo = {}
    for name, fn in (("F1", lambda: f1(c1, cells)), ("F2", lambda: f2(data, cells)), ("F3", lambda: f3(c1, data)),
                     ("F4", lambda: f4(c1)), ("F5", lambda: f5(hr)), ("F6", lambda: f6(loc)), ("F7", lambda: f7(data)),
                     ("F8", lambda: f8(data))):
        try:
            r = fn()
            if name == "F8":
                geo = r or {}
            print(name, "ok", flush=True)
        except Exception as e:  # noqa: BLE001 - a failing figure is reported, the others still render
            import traceback
            traceback.print_exc()
            print(name, "FAILED", e, flush=True)
    write_json(RESULTS_DIR / "geometry_f8.json", geo)


if __name__ == "__main__":
    main()
