"""(0e) Geometry figure markers: captioned figure-ready copies, a g16 label-independent check, and a regenerated
2x2 composite in activation coordinates (layer 24, position 'pre', Isomap k=10 fitted on forced-program states)."""

from __future__ import annotations

import gc
import glob
import json
from collections import Counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402
from sklearn.decomposition import PCA  # noqa: E402
from sklearn.manifold import MDS, Isomap  # noqa: E402

from src.paths import WS, cite, p  # noqa: E402

FIG, RES = WS / "figures", WS / "results"
CAVEAT = ("States are read at the token before the commit token, whose position depends on the program's own label, "
          "so separation can partly reflect position.")
plt.rcParams.update({"font.size": 8, "pdf.fonttype": 42, "ps.fonttype": 42})


def _load_states(task: str, context: str, layer: int, pos: str) -> tuple[np.ndarray, list[dict]]:
    xs, metas = [], []
    for f in sorted(glob.glob(str(p("exp9", f"states/{task}/{context}")) + "/part_*.npz")):
        z = np.load(f, allow_pickle=False)
        li = int(np.where(z["layers"] == layer)[0][0])
        pi = int(np.where(z["positions"] == pos)[0][0])
        xs.append(z["X"][:, li, pi, :].astype(np.float32))
        metas.extend(json.loads(str(z["meta"])))
        del z
        gc.collect()
    return np.concatenate(xs), metas


def stress1(D: np.ndarray, seed: int = 0) -> float:
    D = np.asarray(D, float)
    D = 0.5 * (D + D.T)
    np.fill_diagonal(D, 0.0)
    emb = MDS(n_components=2, dissimilarity="precomputed", random_state=seed, n_init=4, normalized_stress="auto").fit_transform(D)
    d = np.sqrt(((emb[:, None, :] - emb[None, :, :]) ** 2).sum(-1))
    iu = np.triu_indices(len(D), 1)
    return float(np.sqrt(((d[iu] - D[iu]) ** 2).sum() / (D[iu] ** 2).sum()))


def copies(landing: dict, los: dict) -> list[dict]:
    items = [
        ("M1", "exp9", "figures/fig_manifold_t1_baseline.png", "t1|baseline", None),
        ("M2", "exp9", "figures/fig_manifold_t1_single_bfs.png", "t1|single:bfs", ["bfs"]),
        ("M3", "exp9", "figures/fig_manifold_t1_multi_TOP5.png", "t1|multi:TOP5", ["bfs", "dfs", "gbfs", "iddfs", "astar"]),
        ("M4", "exp9", "figures/fig_manifold_t2_los_bf_spfa.png", "t2|los:bf_spfa", None),
        ("M5", "exp17", "figures/fig7_manifold.png", None, None),
    ]
    out = []
    for mid, exp, rel, cond, banned in items:
        src = p(exp, rel)
        if not src.exists():
            out.append({"marker_id": mid, "status": "not_computable_from_declared_inputs", "source": cite(exp, rel)})
            continue
        img = mpimg.imread(str(src))
        h, w = img.shape[:2]
        fig = plt.figure(figsize=(w / 150, h / 150), dpi=150)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.imshow(img)
        ax.axis("off")
        ax.text(0.01, 0.99, mid, transform=ax.transAxes, va="top", ha="left", fontsize=14, fontweight="bold",
                bbox={"facecolor": "white", "edgecolor": "black", "pad": 2})
        name = f"marker_{mid}_{src.stem}"
        fig.savefig(FIG / f"{name}.png", dpi=150)
        fig.savefig(FIG / f"{name}.pdf")
        plt.close(fig)
        counts = None
        if cond and cond in landing.get("conditions", {}):
            counts = landing["conditions"][cond].get("counts")
        elif cond and cond.startswith("t2|los:"):
            key = cond.split(":")[1]
            counts = {"will_attempted_share": los.get(key, {}).get("will_attempted_share"),
                      "banned_share_by_mechanism": los.get(key, {}).get("banned_share_by_mechanism")}
        cap = f"[{mid}] {src.stem} ({cite(exp, rel)}). {CAVEAT}"
        if counts:
            cap += f" Implemented counts / shares under this condition: {json.dumps(counts)}."
        if banned:
            cap += f" Banned: {', '.join(banned)}."
        if cond == "t1|multi:TOP5":
            cap += " Under TOP5 the implemented programs sit on the banned BFS and DFS centroids (avoidance 0.00)."
        out.append({"marker_id": mid, "file_png": f"figures/{name}.png", "file_pdf": f"figures/{name}.pdf",
                    "source": cite(exp, rel), "caption": cap, "implemented_counts": counts})
    return out


def g16_check() -> dict:
    res = {"status": "computed"}
    out = {}
    for pos in ("pre", "g16"):
        X, meta = _load_states("t1", "base", 24, pos)
        labs = np.array([m.get("label") for m in meta])
        cats = sorted(set(labs))
        C = np.stack([X[labs == c].mean(0) for c in cats])
        D = np.sqrt(((C[:, None, :] - C[None, :, :]) ** 2).sum(-1))
        i = cats.index("bfs")
        order = [cats[j] for j in np.argsort(D[i]) if j != i]
        # label-permutation null for 'BFS nearest neighbour is BiBFS'
        rng = np.random.default_rng(20261021)
        obs = D[i, cats.index("bibfs")] if "bibfs" in cats else np.nan
        null_rank = []
        for _ in range(500):
            perm = rng.permutation(labs)
            Cp = np.stack([X[perm == c].mean(0) for c in cats])
            dp = np.sqrt(((Cp[i] - Cp) ** 2).sum(-1))
            dp[i] = np.inf
            null_rank.append(int(np.argmin(dp) == cats.index("bibfs")))
        out[pos] = {"bfs_neighbour_order": order, "bfs_nn": order[0], "n_programs": int(len(labs)),
                    "label_counts": dict(Counter(labs.tolist())),
                    "perm_share_nn_is_bibfs": float(np.mean(null_rank)), "d_bfs_bibfs": float(obs)}
        del X
        gc.collect()
    res["t1_forced_states_layer24"] = out
    res["note"] = ("g16 states exist in exp9 states/ (positions g8, g16, g32, pre). Label-independent check: centroids of "
                   "the T1 forced programs (baseline-prompt context) at layer 24, BFS nearest-neighbour order at the "
                   "fixed generated-token position g16 versus the label-dependent 'pre' position, with a 500-draw label "
                   "permutation null. The iteration-3 audit's N1 p 0.19 and exchangeability p 0.48 are cited, not "
                   "re-derived (source not a declared dependency).")
    return res


def composite(manifold: dict) -> dict:
    panels = [("t1", "baseline", None, "T1 baseline"), ("t1", "single:bfs", ["bfs"], "T1 single BFS ban"),
              ("t1", "multi:TOP5", ["bfs", "dfs", "gbfs", "iddfs", "astar"], "T1 TOP5 ban"),
              ("t2", "los:bf_spfa", ["dijkstra", "bidijkstra", "floyd", "dial"], "T2 LOS (BF/SPFA left)")]
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 6.4))
    info = {}
    fitted: dict = {}
    for ax, (task, cond, banned, title) in zip(axes.ravel(), panels):
        if task not in fitted:
            Xf, mf = _load_states(task, "base", 24, "pre")
            pca = PCA(n_components=50, random_state=0).fit(Xf)
            iso = Isomap(n_neighbors=10, n_components=2).fit(pca.transform(Xf))
            Xo, mo = _load_states(task, "own", 24, "pre")
            fitted[task] = (pca, iso, iso.embedding_, np.array([m.get("label") for m in mf]), Xo, mo)
            del Xf
            gc.collect()
        pca, iso, emb, flabs, Xo, mo = fitted[task]
        conds = np.array([m.get("condition") for m in mo])
        sel = conds == cond
        info[title] = {"n_sampled_states": int(sel.sum()), "conditions_available": sorted(set(conds.tolist()))}
        ax.scatter(emb[:, 0], emb[:, 1], s=4, c="#cfcfcf", lw=0, label="forced programs")
        cats = sorted(set(flabs))
        cent = {c: emb[flabs == c].mean(0) for c in cats}
        if sel.sum():
            pe = iso.transform(pca.transform(Xo[sel]))
            ax.scatter(pe[:, 0], pe[:, 1], s=5, c="#333333", lw=0, alpha=0.6, label="sampled programs")
            slabs = [m.get("label") for m, s in zip(mo, sel) if s]
            cnt = Counter(slabs)
        else:
            cnt = Counter()
        mx = max(cnt.values()) if cnt else 1
        cmap = plt.get_cmap("viridis")
        for c in cats:
            n = cnt.get(c, 0)
            ax.scatter(*cent[c], s=30 + 400 * n / mx, color=cmap(n / mx if mx else 0), edgecolor="black", zorder=3)
            ax.annotate(f"{c} ({n})", cent[c], fontsize=6, xytext=(3, 3), textcoords="offset points")
            if banned and c in banned:
                ax.scatter(*cent[c], marker="x", s=120, color="red", zorder=4)
        D = manifold["tasks"][task]["primary_centroid_D"]
        st = stress1(np.array(D))
        info[title]["mds_stress1_primary_centroid_D"] = st
        info[title]["implemented_counts"] = dict(cnt)
        ax.set_title(f"{title}  (MDS stress-1 {st:.3f})", fontsize=8)
        ax.set_xticks([])
        ax.set_yticks([])
    fig.suptitle("exp9 states, layer 24, position 'pre', Isomap k=10 on forced programs; marker area = implemented "
                 "count, red x = banned", fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / "composite_2x2_activation.png", dpi=200)
    fig.savefig(FIG / "composite_2x2_activation.pdf")
    plt.close(fig)
    return info


def run_figures_stage() -> None:
    landing = json.loads(p("exp9", "results/landing.json").read_text())
    los = json.loads(p("exp9", "results/los.json").read_text())
    manifold = json.loads(p("exp9", "results/manifold.json").read_text())
    caps = copies(landing, los)
    out = {"markers": caps}
    try:
        out["g16"] = g16_check()
    except (FileNotFoundError, KeyError, ValueError, IndexError) as e:
        logger.error(f"g16 check failed: {e}")
        out["g16"] = {"status": "not re-derived; source not a declared dependency", "error": str(e)[:200],
                      "cited": "iteration-3 audit: N1 p 0.19, exchangeability p 0.48"}
    try:
        info = composite(manifold)
        out["composite"] = {"file_png": "figures/composite_2x2_activation.png",
                            "file_pdf": "figures/composite_2x2_activation.pdf", "panels": info, "mode": "activation coordinates",
                            "caption": ("Regenerated 2x2 composite (T1 baseline, T1 single BFS ban, T1 TOP5, T2 leave-one-"
                                        "survivor with BF/SPFA left) in actual activation coordinates: exp9 states at layer 24, "
                                        "position 'pre', Isomap (k = 10) fitted on forced-program states with the sampled "
                                        "states projected onto it. Centroid marker area and colour scale with the implemented "
                                        "count; banned centroids are crossed out; each panel prints the MDS stress-1 of the "
                                        "primary centroid geodesic matrix. " + CAVEAT)}
    except (FileNotFoundError, KeyError, ValueError, MemoryError) as e:
        logger.error(f"composite failed: {e}")
        out["composite"] = {"status": "failed", "error": str(e)[:200]}
    (FIG / "captions.json").write_text(json.dumps(out, indent=1, default=str))
    (RES / "figures.json").write_text(json.dumps(out, indent=1, default=str))
    logger.info(f"figures: {len(caps)} markers; g16 {out['g16'].get('status')}; composite {out['composite'].get('mode', out['composite'].get('status'))}")
