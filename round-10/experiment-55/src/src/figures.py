#!/usr/bin/env python3
"""Stage 7 figures (house style of aii-data-fig-gen; PDF + PNG). Every geometry panel is drawn in actual activation
coordinates of the stated model / block / readout (PCA of the raw R1 states, Isomap k 15 on the same states,
classical MDS of the kNN geodesics) and states model, block, readout, N and projection.
F1/F2 factorial frame (8B / 32B); F3 full frame with implemented counts (baseline vs ban) and survivor families;
F4 container-held-fixed frames (HEAP, GRID2D) with F-UD / F-BF; F5 G1 bars; F6 per-family g distributions;
F7 G1 layer curve; F8 placement heatmap (family x nearest class)."""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import json
import sys
import warnings
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
if os.environ.get("AII_DATA_FIG_GEN_SCRIPTS"):        # optional house-style helpers (aii-data-fig-gen)
    sys.path.insert(0, os.environ["AII_DATA_FIG_GEN_SCRIPTS"])
import geometry  # noqa: E402
import g2  # noqa: E402
import v10  # noqa: E402

try:
    from chart_style import apply_house_style, PALETTE  # noqa: E402
    apply_house_style()
except ImportError:                              # outside the pipeline image: plain matplotlib
    PALETTE = ("#0173B2", "#DE8F05", "#029E73", "#D55E00", "#CC78BC", "#CA9161", "#FBAFE4", "#949494")

DISC_COL = {"BFSO": PALETTE[0], "DFSO": PALETTE[1], "HEUR": PALETTE[2], "COST": PALETTE[3], "RELAX": PALETTE[4],
            "RAND": PALETTE[5], "CAT": "#555555"}
CONT_MK = {"DEQUE": "o", "LIST": "s", "CALL": "^", "HEAP": "D", "GRID2D": "P", "SET": "X"}
FAM_MK = {"F-UD": ("*", "#000000"), "F-BF": ("v", "#7F0000"), "F-CK": ("<", "#004D40"), "F-RF": (">", "#4A148C"),
          "F-RS": ("h", "#BF360C"), "F-SF": ("p", "#1A237E"), "F-OTH": ("d", "#33691E"), "F-COV": (".", "#757575"),
          "F-COVX": (".", "#BDBDBD")}
FIG = v10.FIGS


def save(fig, name: str) -> None:
    FIG.mkdir(exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(FIG / f"{name}.{ext}", dpi=200 if ext == "png" else None)
    plt.close(fig)


def factorial_xy(tag: str):
    import analysis

    F = analysis.factorial(tag)
    bi = F["blocks"].index(v10.MODELS[tag]["primary_block"])
    X = F["R"][:, 0, bi].astype(np.float64)
    return F, X


def proj3(X: np.ndarray, k: int = 15):
    from sklearn.decomposition import PCA
    from sklearn.manifold import Isomap

    pca = PCA(n_components=2, random_state=0).fit(X)
    P = pca.transform(X)
    iso = Isomap(n_neighbors=k, n_components=2).fit(X)
    geo, _ = geometry.geodesics(X, k)
    M = geometry.classical_mds(geo)
    s1 = geometry.stress1(geo, M)
    return P, pca.explained_variance_ratio_, iso, iso.embedding_, M, s1


def fig_factorial(tag: str, name: str) -> None:
    F, X = factorial_xy(tag)
    P, evr, _iso, I, M, s1 = proj3(X)
    m = v10.MODELS[tag]
    fig, axs = plt.subplots(1, 3, figsize=(13, 4.6), layout="constrained")
    for ax, Y, ttl in ((axs[0], P, f"PCA (PC1 {evr[0]:.1%}, PC2 {evr[1]:.1%})"), (axs[1], I, "Isomap (k 15)"),
                       (axs[2], M, f"classical MDS of kNN geodesics (stress-1 {s1:.2f})")):
        for d in ("BFSO", "DFSO", "HEUR", "COST", "RELAX", "RAND"):
            for c, mk in CONT_MK.items():
                sel = np.array([(a == d and b == c) for a, b in zip(F["disc"], F["cont"])])
                if sel.any():
                    ax.scatter(Y[sel, 0], Y[sel, 1], s=14, marker=mk, color=DISC_COL[d], alpha=0.55, linewidths=0)
                    cx, cy = Y[sel].mean(0)
                    ax.scatter([cx], [cy], s=120, marker=mk, color=DISC_COL[d], edgecolors="black", linewidths=0.9)
        ax.set_title(ttl, fontsize=10)
        ax.set_xlabel("dim 1")
        ax.set_ylabel("dim 2")
    hd = [plt.Line2D([], [], color=DISC_COL[d], marker="o", ls="", label=d) for d in
          ("BFSO", "DFSO", "HEUR", "COST", "RELAX", "RAND")]
    hc = [plt.Line2D([], [], color="#444444", marker=mk, ls="", label=c) for c, mk in CONT_MK.items()]
    fig.legend(handles=hd + hc, loc="outside lower center", ncol=12, fontsize=8, frameon=False)
    fig.suptitle(f"Factorial frame, {m['engine']}, block {m['primary_block']}, readout R1 (mean over code tokens), "
                 f"N = {len(X)} programs; colour = discipline, marker = container, large = cell centroid",
                 fontsize=10)
    save(fig, name)


def counts_baseline_ban() -> tuple[Counter, Counter]:
    base = Counter(r.get("adj_label") for r in v10.read_jsonl(v10.IN44 / "data" / "labelled_C6_baseline.jsonl")
                   if r.get("passed"))
    ban = Counter()
    for f in ("labelled_C6_ban.jsonl", "labelled_C6_confirm.jsonl"):
        for r in v10.read_jsonl(v10.IN44 / "data" / f):
            if r.get("passed") and r.get("adj_label") not in ("other", "invalid", None):
                ban[r["adj_label"]] += 1
    for r in v10.read_jsonl(v10.IN45 / "data" / "survivors_for_tpg.jsonl"):
        if r.get("passed") and r.get("label") not in ("other", None) and r.get("cell", "").startswith("A_k5"):
            ban[r["label"]] += 1
    return base, ban


def fig_full_frame(tag: str, name: str) -> None:
    z = np.load(v10.STATES_V10 / f"g2frame_{tag}.npz", allow_pickle=False)
    X, labels, Xp, fam = z["X"].astype(np.float64), z["labels"], z["Xp"].astype(np.float64), z["fam"]
    res = v10.read_json(v10.RESULTS / f"g2_{tag}.json")
    from sklearn.manifold import Isomap

    iso = Isomap(n_neighbors=15, n_components=2).fit(X)
    Y = iso.embedding_
    Yp = iso.transform(Xp)
    base, ban = counts_baseline_ban()
    near = Counter(p["nearest_class"] for p in res["placements_full"] if p["family"] in
                   ("F-BF", "F-CK", "F-RF", "F-RS", "F-SF", "F-OTH"))
    classes = sorted(set(labels.tolist()))
    cent = {c: Y[labels == c].mean(0) for c in classes}
    fig, axs = plt.subplots(1, 2, figsize=(13, 5.6), layout="constrained")
    for ax, cnt, ttl in ((axs[0], base, "five-name-ban BASELINE (iteration-8 C6, no ban): implemented counts"),
                         (axs[1], ban + near, "under the five-name BAN: labelled survivors + nearest-class counts")):
        ax.scatter(Y[:, 0], Y[:, 1], s=5, color="#BBBBBB", alpha=0.5, linewidths=0)
        mx = max([cnt.get(c, 0) for c in classes] + [1])
        for c in classes:
            n = cnt.get(c, 0)
            col = DISC_COL.get(g2.disc_of(c), "#555555")
            ax.scatter([cent[c][0]], [cent[c][1]], s=30 + 900 * n / mx, color=col, alpha=0.75,
                       edgecolors="black" if g2.is_banned(c) else "white", linewidths=1.2)
            ax.annotate(f"{c} ({n})" if n else c, cent[c], fontsize=6, ha="center", va="bottom")
        if ax is axs[1]:
            for f_, (mk, col) in FAM_MK.items():
                sel = fam == f_
                if sel.any() and f_ not in ("F-COVX",):
                    ax.scatter(Yp[sel, 0], Yp[sel, 1], s=22 if mk != "." else 8, marker=mk, color=col,
                               label=f"{f_} (n {int(sel.sum())})", alpha=0.85)
            ax.legend(fontsize=7, loc="best", frameon=True)
        ax.set_title(ttl, fontsize=10)
        ax.set_xlabel("Isomap dim 1")
        ax.set_ylabel("Isomap dim 2")
    m = v10.MODELS[tag]
    fig.suptitle(f"Full frame (24 cells + catalogue), {m['engine']}, block {m['primary_block']}, R1, N = {len(X)} "
                 f"frame programs, Isomap k 15; centroid area = implemented count; black edge = banned class; "
                 f"placed programs projected out-of-sample", fontsize=9)
    save(fig, name)


def fig_heldfixed(tag: str, name: str) -> None:
    import analysis

    full = analysis.build_full_frame(tag, v10.MODELS[tag]["primary_block"], 0, 15)
    Xp, rows = analysis.placed(tag, v10.MODELS[tag]["primary_block"], 0)
    conts = np.array([m.get("container") for m in full.meta])
    fig, axs = plt.subplots(1, 2, figsize=(13, 5.2), layout="constrained")
    for ax, cont, fams in ((axs[0], "HEAP", ("F-UD", "F-CK")), (axs[1], "GRID2D", ("F-BF", "F-RS"))):
        sf = g2.subframe(full, conts == cont, cont)
        if sf is None:
            ax.set_title(f"{cont}: no subframe")
            continue
        M = geometry.classical_mds(sf.geo)
        for c in sf.classes:
            sel = sf.labels == c
            col = DISC_COL.get(g2.disc_of(c), "#555555")
            ax.scatter(M[sel, 0], M[sel, 1], s=10, color=col, alpha=0.5, linewidths=0)
            cx, cy = M[sel].mean(0)
            ax.scatter([cx], [cy], s=90, color=col, edgecolors="black" if g2.is_banned(c) else "white")
            ax.annotate(c, (cx, cy), fontsize=6, ha="center", va="bottom")
        # placed programs: MDS out-of-sample by Gower-style least squares on geodesics to the frame
        n = len(sf.X)
        D2 = sf.geo ** 2
        J = np.eye(n) - 1.0 / n
        B = -0.5 * J @ D2 @ J
        w, V = np.linalg.eigh(B)
        i2 = np.argsort(w)[::-1][:2]
        L = V[:, i2] / np.sqrt(np.maximum(w[i2], 1e-12))
        for f_ in fams:
            sel = [i for i, r in enumerate(rows) if r["family"] == f_]
            if not sel:
                continue
            pts = []
            for i in sel:
                dv = g2.oos(Xp[i], sf.X, sf.geo, sf.k)
                pts.append(-0.5 * (dv ** 2 - D2.mean(1)) @ L)
            pts = np.array(pts)
            mk, col = FAM_MK[f_]
            ax.scatter(pts[:, 0], pts[:, 1], marker=mk, s=40, color=col, label=f"{f_} (n {len(sel)})")
        ax.legend(fontsize=7, loc="best")
        ax.set_title(f"{cont}-held-fixed frame (N {n}), classical MDS of kNN geodesics", fontsize=10)
        ax.set_xlabel("MDS dim 1")
        ax.set_ylabel("MDS dim 2")
    m = v10.MODELS[tag]
    fig.suptitle(f"Container-held-fixed frames, {m['engine']}, block {m['primary_block']}, R1, k 15", fontsize=10)
    save(fig, name)


def fig_g1_bars(name: str) -> None:
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.4), layout="constrained")
    for ax, key, ttl in ((axs[0], "primary", "all 24 cells"), (axs[1], "S1_crossed_core", "crossed core 3 x 4")):
        labs, vals, lo, hi, cols = [], [], [], [], []
        for tag in ("8b", "32b"):
            p = v10.RESULTS / f"g1_{tag}.json"
            if not p.exists():
                continue
            d = v10.read_json(p)
            r = d[key]
            for stat, col in (("rho_dc", PALETTE[0]), ("rho_cd", PALETTE[1])):
                labs.append(f"{tag} {stat}")
                vals.append(r[stat])
                ci = r["bootstrap"][stat]["ci95"]
                lo.append(r[stat] - ci[0])
                hi.append(ci[1] - r[stat])
                cols.append(col)
            if key == "primary":
                for b, nm in (("S7_E0_bag_of_tokens", "E0"), ("S7_RANDNET_block17", "RANDNET")):
                    if b in d:
                        labs.append(f"{tag} {nm} rho_dc")
                        vals.append(d[b]["rho_dc"])
                        ci = d[b]["bootstrap"]["rho_dc"]["ci95"]
                        lo.append(d[b]["rho_dc"] - ci[0])
                        hi.append(ci[1] - d[b]["rho_dc"])
                        cols.append(PALETTE[7])
                nc = d.get("S9_noise_ceiling", {}).get("spearman_DS_ctx_v_vs_ctx_v+1")
                if nc:
                    ax.axhline(nc, color=PALETTE[3], ls="--", lw=1)
                    ax.annotate(f"{tag} noise ceiling {nc:.2f}", (0, nc), fontsize=7, va="bottom")
        x = np.arange(len(vals))
        ax.bar(x, vals, color=cols, yerr=[lo, hi], capsize=3)
        ax.set_xticks(x, labs, rotation=35, ha="right", fontsize=8)
        ax.axhline(0.30, color="black", lw=0.8, ls=":")
        ax.set_ylabel("partial Spearman (95% program-bootstrap CI)")
        ax.set_title(f"G1, {ttl}: rho_dc = discipline | container, rho_cd = container | discipline", fontsize=9)
    save(fig, name)


def fig_violins(tag: str, name: str) -> None:
    res = v10.read_json(v10.RESULTS / f"g2_{tag}.json")
    pl = res["placements_full"]
    fams = [f for f in ("F-UD", "F-BF", "F-CK", "F-RF", "F-RS", "F-SF", "F-OTH", "F-COV", "F-COVX")
            if any(p["family"] == f for p in pl)]
    data = [[p["g"] for p in pl if p["family"] == f] for f in fams]
    fig, ax = plt.subplots(figsize=(11, 4.4), layout="constrained")
    ax.violinplot(data, showmedians=True)
    med = res["frame"]["median_nonbanned_class_g"]
    ax.axhline(med, color=PALETTE[3], ls="--", lw=1)
    ax.annotate(f"median non-banned class g = {med:.2f}", (0.6, med), fontsize=8, va="bottom")
    labs = []
    for f in fams:
        st = res["families_full"].get(f, {})
        labs.append(f"{f}\nn {st.get('n')}, r_F {st.get('r_F', float('nan')):.2f}\n"
                    f"[{st.get('r_F_ci95', [np.nan, np.nan])[0]:.2f}, {st.get('r_F_ci95', [np.nan, np.nan])[1]:.2f}]")
    ax.set_xticks(np.arange(1, len(fams) + 1), labs, fontsize=7)
    ax.set_ylabel("g = min mean geodesic to a banned class")
    m = v10.MODELS[tag]
    ax.set_title(f"Per-family g on the full frame, {m['engine']}, block {m['primary_block']}, R1, k 15", fontsize=10)
    save(fig, name)


def fig_layer(name: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 4), layout="constrained")
    for tag, ls in (("8b", "-"), ("32b", "--")):
        p = v10.RESULTS / f"g1_{tag}.json"
        if not p.exists():
            continue
        lc = v10.read_json(p)["S6_layer_curve"]
        bs = sorted(int(b) for b in lc)
        n = v10.MODELS[tag]["n_layers"]
        ax.plot([(b + 1) / n for b in bs], [lc[str(b)]["rho_dc"] for b in bs], ls, color=PALETTE[0],
                label=f"{tag} rho_dc")
        ax.plot([(b + 1) / n for b in bs], [lc[str(b)]["rho_cd"] for b in bs], ls, color=PALETTE[1],
                label=f"{tag} rho_cd")
    ax.set_xlabel("relative depth (block + 1) / n_layers")
    ax.set_ylabel("partial Spearman")
    ax.set_title("G1 layer curve, R1 readout, factorial frame (N 287)", fontsize=10)
    ax.legend(fontsize=8)
    save(fig, name)


def fig_heatmap(tag: str, name: str) -> None:
    res = v10.read_json(v10.RESULTS / f"g2_{tag}.json")
    pl = res["placements_full"]
    fams = [f for f in ("F-UD", "F-BF", "F-CK", "F-RF", "F-RS", "F-SF", "F-OTH", "F-COV", "F-COVX")
            if any(p["family"] == f for p in pl)]
    cls = sorted({p["nearest_class"] for p in pl})
    M = np.array([[sum(1 for p in pl if p["family"] == f and p["nearest_class"] == c) /
                   max(1, sum(1 for p in pl if p["family"] == f)) for c in cls] for f in fams])
    fig, ax = plt.subplots(figsize=(12, 4.2), layout="constrained")
    im = ax.imshow(M, cmap="cividis", aspect="auto", vmin=0, vmax=1)
    ax.set_xticks(np.arange(len(cls)), cls, rotation=60, ha="right", fontsize=7)
    ax.set_yticks(np.arange(len(fams)), fams, fontsize=8)
    for i in range(len(fams)):
        for j in range(len(cls)):
            if M[i, j] >= 0.05:
                ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", fontsize=6,
                        color="black" if M[i, j] > 0.5 else "white")
    fig.colorbar(im, ax=ax, label="share of family")
    m = v10.MODELS[tag]
    ax.set_title(f"Placement: family x nearest class, {m['engine']}, block {m['primary_block']}, R1, k 15",
                 fontsize=10)
    save(fig, name)


def main() -> None:
    which = sys.argv[1:] or ["all"]
    jobs = {"F1": lambda: fig_factorial("8b", "F1_factorial_8b"), "F2": lambda: fig_factorial("32b", "F2_factorial_32b"),
            "F3": lambda: fig_full_frame("8b", "F3_full_frame_8b"), "F3b": lambda: fig_full_frame("32b", "F3_full_frame_32b"),
            "F4": lambda: fig_heldfixed("8b", "F4_heldfixed_8b"), "F5": lambda: fig_g1_bars("F5_g1_bars"),
            "F6": lambda: fig_violins("8b", "F6_family_g_8b"), "F6b": lambda: fig_violins("32b", "F6_family_g_32b"),
            "F7": lambda: fig_layer("F7_layer_curve"), "F8": lambda: fig_heatmap("8b", "F8_placement_heatmap_8b")}
    done = {}
    for k, fn in jobs.items():
        if "all" not in which and k not in which:
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fn()
            done[k] = "ok"
        except (FileNotFoundError, KeyError, ValueError, IndexError) as e:
            done[k] = f"{type(e).__name__}: {e}"
        print(k, done[k], flush=True)
    v10.write_json(v10.RESULTS / "figures_status.json", done)


if __name__ == "__main__":
    main()
