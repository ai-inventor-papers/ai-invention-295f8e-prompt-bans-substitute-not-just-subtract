#!/usr/bin/env python3
"""Phase E (CPU): summaries, association table, gate figure, manifold (geodesic MDS + PCA), forecast contest,
C3 shift decomposition, C2 removal analysis, BUY row, and method_out.json.

Every verdict is descriptive (about 4-7 ban events and 2 removal events; no p-values).
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "analysis"))
from common import (CACHE_LAYERS, CATALOGUE, DISPLAY, SPEC, TASK_DATASET, TASKS, hill1, js_div, read_jsonl,  # noqa: E402
                    setup_logger, wilson)
from geometry import attach, geodesic_between, knn_graph, pca95, twonn_id  # noqa: E402

logger = setup_logger("analyze")
RES = ROOT / "results"
FIG = ROOT / "figures"
CACHE = ROOT / "cache"
RNG = np.random.default_rng(2026)


def jdump(obj, name):
    (RES / name).write_text(json.dumps(obj, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)))


def unit(v):
    return v / (np.linalg.norm(v) + 1e-12)


def load_all():
    rows = {}
    for ph in ("A", "C", "D"):
        rows[ph] = read_jsonl(ROOT / "data" / f"samples_phase{ph}.jsonl")
    index = read_jsonl(CACHE / "hR_index.jsonl")
    # only the layers the analysis reads (both bands and l*); layers 8..20 are needed by Phase B alone and are not
    # published with the repository (they stay on the run volume)
    gate = json.loads((RES / "gate.json").read_text())
    need = sorted({l for t in TASKS for l in gate[t]["band"]} | {gate[t]["l_star"] for t in TASKS})
    H = {l: np.load(CACHE / f"hR_layer{l}.npy").astype(np.float32) for l in need}
    return rows, index, H


def cond_summary(rr: list[dict], cat: list[str], banned: list[str]) -> dict:
    n = len(rr)
    npass = sum(r["passed"] for r in rr)
    lc = Counter(r["label"] for r in rr)
    corr = Counter(r["label"] for r in rr if r["passed"])
    comp = sum(r["passed"] and r["label"] not in banned and r["label"] != "no_code" for r in rr)
    return {"n": n, "label_counts": dict(lc), "correct_label_counts": dict(corr), "pass_rate": npass / max(n, 1),
            "pass_wilson": wilson(npass, n), "hill_cc": hill1(corr), "compliance": comp / max(n, 1),
            "compliance_wilson": wilson(comp, n),
            "label_wilson": {m: wilson(lc.get(m, 0), n) for m in cat + ["other", "no_code"]}}


# ============================================================================================ E1 / summaries
def summaries(rows) -> dict:
    out = {}
    allrows = rows["A"] + rows["C"] + rows["D"]
    for t in TASKS:
        cat = CATALOGUE[t]
        conds = sorted({r["condition"] for r in allrows if r["task"] == t})
        out[t] = {}
        for c in conds:
            rr = [r for r in allrows if r["task"] == t and r["condition"] == c]
            banned = c.split(":", 1)[1].split("+") if c.startswith("ban:") else []
            if c.startswith("removal:"):
                banned = []
            out[t][c] = cond_summary(rr, cat, banned)
    return out


# ============================================================================================ E3 gate figure
def fig_gate(gate):
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), sharey=False)
    for ax, t in zip(axes, TASKS):
        pl = gate[t]["per_layer"]
        L = [p["layer"] for p in pl]
        ax.plot(L, [p["named_acc"] for p in pl], "-o", ms=3, label="named probe acc (leave-one-frame-out)", color="#1f77b4")
        ax.plot(L, [p["null_named_p95"] for p in pl], ":", color="#1f77b4", label="shuffled-label null p95 (named)")
        ax.plot(L, [p["transfer_acc"] for p in pl], "-s", ms=3, label="named->masked transfer acc", color="#d62728")
        ax.plot(L, [p["null_transfer_p95"] for p in pl], ":", color="#d62728", label="shuffled null p95 (transfer)")
        ax2 = ax.twinx()
        ax2.plot(L, [p["decoder_js"] for p in pl], "-^", ms=3, color="#2ca02c", label="decoder JS to baseline dist")
        ax2.plot(L, [p["null_js_p5"] for p in pl], ":", color="#2ca02c", label="shuffled null p5 (JS)")
        ax2.set_ylabel("JS divergence (lower = better)", color="#2ca02c")
        ax.axvspan(min(gate[t]["band"]) - 0.5, max(gate[t]["band"]) + 0.5, color="0.9", zorder=0)
        ax.axvline(gate[t]["l_star"], color="k", lw=0.8)
        ax.set_title(f"{t}: R-position probe gate (l*={gate[t]['l_star']}, pass={gate[t]['gate_pass']})")
        ax.set_xlabel("layer (output of decoder block l)")
        ax.set_ylabel("accuracy")
        ax.set_ylim(0, 1.05)
        if t == TASKS[0]:
            h1, l1 = ax.get_legend_handles_labels()
            h2, l2 = ax2.get_legend_handles_labels()
            ax.legend(h1 + h2, l1 + l2, fontsize=7, loc="lower left")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"gate_per_layer.{ext}", dpi=160)
    plt.close(fig)


# ============================================================================================ E4 manifold
def manifold(index, H, gate, summA, geoB, phaseC, rows=None) -> dict:
    import matplotlib.pyplot as plt
    from scipy.stats import spearmanr
    from sklearn.manifold import MDS

    out = {}
    for t in TASKS:
        cat = CATALOGUE[t]
        l = gate[t]["l_star"]
        iN = [i for i, r in enumerate(index) if r["task"] == t and r["condition"].startswith("forced:")]
        lab = [index[i]["condition"].split(":")[1] for i in iN]
        Xn = H[l][iN]
        mu, comps, ev = pca95(Xn)
        P = (Xn - mu) @ comps.T
        C = np.stack([Xn[[k for k, m in enumerate(lab) if m == mm]].mean(0) for mm in cat])
        G, ginfo = knn_graph(P, 10)
        # leaf points: centroids, baseline, ban:X, mention:X, listall, succession, ablated baseline
        leaf_names, leaf_vecs = [], []
        for j, m in enumerate(cat):
            leaf_names.append(f"centroid:{m}")
            leaf_vecs.append(C[j])

        def mean_cond(c):
            ii = [i for i, r in enumerate(index) if r["task"] == t and r["condition"] == c]
            return H[l][ii].mean(0) if ii else None

        conds = ["baseline", "listall"] + [f"ban:{m}" for m in cat] + [f"mention:{m}" for m in cat]
        chain = phaseC.get("succession", {}).get(t, {}).get("chain", [])
        for k in range(2, len(chain) + 1):
            conds.append("ban:" + "+".join(chain[:k]))
        for c in conds:
            v = mean_cond(c)
            if v is not None:
                leaf_names.append(c)
                leaf_vecs.append(v)
        abl = CACHE / f"hR_ablated_{t}.npz"
        if abl.exists():
            Z = np.load(abl)
            band = [int(x) for x in Z["band"]]
            if l in band:
                leaf_names.append("ablated_baseline")
                leaf_vecs.append(Z["h"][band.index(l)].astype(np.float32).mean(0))
        Q = (np.stack(leaf_vecs) - mu) @ comps.T
        GA = attach(G, P, Q, 10)
        from scipy.sparse.csgraph import shortest_path

        Dall = shortest_path(GA, directed=False)
        Dall = (Dall + Dall.T) / 2
        finite = np.isfinite(Dall).all()
        mds = MDS(n_components=2, dissimilarity="precomputed", n_init=4, random_state=0, normalized_stress="auto")
        Y = mds.fit_transform(np.where(np.isfinite(Dall), Dall, np.nanmax(Dall[np.isfinite(Dall)]) * 2))
        from scipy.spatial.distance import pdist, squareform

        Dy = squareform(pdist(Y))
        iu = np.triu_indices(len(Dall), 1)
        stress1 = float(np.sqrt(np.sum((Dall[iu] - Dy[iu]) ** 2) / np.sum(Dall[iu] ** 2)))
        # geodesic vs euclidean rank correlation (over points)
        from scipy.spatial.distance import cdist

        De = cdist(P, P)
        npnt = len(P)
        ii = np.triu_indices(npnt, 1)
        rho = float(spearmanr(Dall[:npnt, :npnt][ii], De[ii])[0])
        # testing plan 8: geodesic >= Euclidean for every pair, symmetric distance matrix
        Graw = shortest_path(GA, directed=False)
        geo_checks = {"geodesic_ge_euclidean_all_pairs": bool((Dall[:npnt, :npnt] + 1e-4 >= De).all()),
                      "symmetric_max_abs_diff": float(np.nanmax(np.abs(Graw - Graw.T)[np.isfinite(Graw)]))}
        # intrinsic dimension vs column-shuffled nulls
        idim = twonn_id(P)
        nulls = []
        for s in range(20):
            Ps = P.copy()
            for c in range(Ps.shape[1]):
                Ps[:, c] = RNG.permutation(Ps[:, c])
            nulls.append(twonn_id(Ps))
        counts = {m: summA[t]["baseline_label_counts"].get(m, 0) for m in cat}
        out[t] = {"layer": l, "pca_dims": int(comps.shape[0]), "pca_explained": float(ev.sum()), "graph": ginfo,
                  "mds_stress1": stress1, "geodesic_vs_euclidean_spearman": rho, "twonn_id": idim,
                  "twonn_null_mean": float(np.nanmean(nulls)), "twonn_null_p5_p95": [float(np.nanpercentile(nulls, 5)),
                                                                                       float(np.nanpercentile(nulls, 95))],
                  "leaf_names": leaf_names, "mds_xy_leaves": Y[npnt:].tolist(), "all_finite": bool(finite),
                  "centroid_geodesic": Dall[npnt:npnt + len(cat), npnt:npnt + len(cat)].tolist(),
                  "baseline_counts": counts, "checks": geo_checks}
        # ---------------------------------------------------------------- figure: MDS + PCA side by side
        cmap = plt.get_cmap("tab10")
        fig, axes = plt.subplots(1, 2, figsize=(15, 7.0))
        Ppca = P[:, :2]
        Qpca = Q[:, :2]
        for ax, (pts, lv, title) in zip(axes, [(Y[:npnt], Y[npnt:], f"geodesic MDS (kNN k=10, stress-1={stress1:.2f})"),
                                               (Ppca, Qpca, f"PCA-2D of the same states ({ev[:2].sum() * 100:.0f}% var of PCA95 space)")]):
            for j, m in enumerate(cat):
                sel = [k for k, mm in enumerate(lab) if mm == m]
                ax.scatter(pts[sel, 0], pts[sel, 1], s=10, alpha=0.35, color=cmap(j), label=f"forced:{m} (n={len(sel)})")
            vmax = max(np.log10(1 + max(counts.values())), 1e-6)
            for j, m in enumerate(cat):
                c = math.log10(1 + counts[m]) / vmax
                ax.scatter(lv[j, 0], lv[j, 1], s=380, marker="o", c=[plt.get_cmap("viridis")(c)], edgecolors=cmap(j),
                           linewidths=2.5, zorder=5)
                ax.annotate(f"{m}\n(base n={counts[m]})", lv[j], fontsize=8, ha="center", va="bottom",
                            xytext=(0, 12), textcoords="offset points", zorder=6)
            name_pos = {n: lv[k] for k, n in enumerate(leaf_names)}
            for n, p in name_pos.items():
                if n.startswith("centroid"):
                    continue
                if n == "baseline":
                    ax.scatter(*p, marker="*", s=300, c="k", zorder=7)
                    ax.annotate("baseline", p, fontsize=8, xytext=(5, -10), textcoords="offset points")
                elif n == "listall":
                    ax.scatter(*p, marker="P", s=120, c="0.3", zorder=7)
                    ax.annotate("list-all", p, fontsize=7, xytext=(5, 3), textcoords="offset points")
                elif n == "ablated_baseline":
                    ax.scatter(*p, marker="X", s=200, c="m", zorder=7)
                    ax.annotate("ablated baseline", p, fontsize=8, color="m", xytext=(5, 3), textcoords="offset points")
                elif n.startswith("ban:") and "+" not in n:
                    ax.scatter(*p, marker="v", s=60, c="r", zorder=6)
                    ax.annotate(n, p, fontsize=6, color="r", xytext=(3, -8), textcoords="offset points")
                elif n.startswith("ban:"):
                    ax.scatter(*p, marker="D", s=50, c="darkred", zorder=6)
                elif n.startswith("mention:"):
                    ax.scatter(*p, marker="^", s=50, c="tab:blue", zorder=6)
            for m in cat:
                a, b = name_pos.get(f"mention:{m}"), name_pos.get(f"ban:{m}")
                if a is not None and b is not None:
                    ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="->", color="0.4", lw=0.8))
            path = ["baseline"] + ["ban:" + "+".join(chain[:k]) for k in range(1, len(chain) + 1)]
            path = [name_pos[p] for p in path if p in name_pos]
            if len(path) >= 2:
                pa = np.array(path)
                ax.plot(pa[:, 0], pa[:, 1], "-", color="darkred", lw=1.5, alpha=0.8, zorder=6)
            ax.set_title(title, fontsize=10)
            ax.set_xticks([])
            ax.set_yticks([])
        axes[0].legend(fontsize=7, loc="best", markerscale=2)
        fig.suptitle(f"{t}: path-search manifold at read position R, layer {l} (Qwen3-8B, thinking off).\nBig circles = "
                     f"mode centroids coloured by log10(1+baseline implemented count); * baseline, v ban:X, ^ mention:X, "
                     f"arrows mention->ban, dark red = succession path, X = ablated baseline", fontsize=9)
        fig.tight_layout()
        for ext in ("png", "pdf"):
            fig.savefig(FIG / f"manifold_{t}.{ext}", dpi=160)
        plt.close(fig)
        # ---------------------------------------------------------------- figure: where do the bans send the model?
        if rows is not None:
            X1 = summA[t]["modal"]
            ban_conds = sorted({r["condition"] for r in rows["C"] if r["task"] == t and r["condition"].startswith("ban:")},
                               key=lambda c: (c.count("+"), c))
            panels = [("baseline", [r for r in rows["A"] if r["task"] == t and r["condition"] == "baseline"])]
            panels += [(c, [r for r in rows["C"] if r["task"] == t and r["condition"] == c]) for c in ban_conds]
            mcond = f"mention:{X1}"
            mr = [r for r in rows["C"] if r["task"] == t and r["condition"] == mcond]
            if mr:
                panels.append((mcond, mr))
            fig, axes = plt.subplots(1, len(panels), figsize=(4.6 * len(panels), 4.8), squeeze=False)
            for ax, (c, rr) in zip(axes[0], panels):
                cnt = Counter(r["label"] for r in rr)
                ax.scatter(Y[:npnt, 0], Y[:npnt, 1], s=6, c="0.85")
                for j, m in enumerate(cat):
                    k = cnt.get(m, 0)
                    ax.scatter(Y[npnt + j, 0], Y[npnt + j, 1], s=60 + 1500 * k / max(len(rr), 1), color=cmap(j),
                               alpha=0.85, edgecolors="k", zorder=5)
                    ax.annotate(f"{m}\n{k}/{len(rr)}", (Y[npnt + j, 0], Y[npnt + j, 1]), fontsize=7, ha="center",
                                va="bottom", xytext=(0, 9), textcoords="offset points", zorder=6)
                banned = c.split(":", 1)[1].split("+") if c.startswith("ban:") else []
                for b in banned:
                    jb = cat.index(b)
                    ax.scatter(Y[npnt + jb, 0], Y[npnt + jb, 1], marker="x", s=220, c="k", zorder=7)
                oth = cnt.get("other", 0) + cnt.get("no_code", 0)
                ax.set_title(f"{c} (n={len(rr)}; other/no_code={oth})", fontsize=8)
                ax.set_xticks([])
                ax.set_yticks([])
            fig.suptitle(f"{t}: implemented-count per mode placed at the mode centroids on the geodesic MDS map "
                         f"(layer {l}); x = banned mode(s). Bubble area = share of samples.", fontsize=9)
            fig.tight_layout()
            for ext in ("png", "pdf"):
                fig.savefig(FIG / f"ban_shift_on_manifold_{t}.{ext}", dpi=160)
            plt.close(fig)
    return out


def manip_sensitivity(index, H, gate, summA, rows, preds) -> dict:
    """Modes whose forced manipulation check is < 50%: recompute their centroid from the paraphrases whose forced
    sample was labelled X, recompute centroid geodesics on the SAME graph, and report whether the geodesic
    nominations of the committed events would change (sensitivity only; the commit is unchanged)."""
    out = {}
    for t in TASKS:
        cat = CATALOGUE[t]
        flagged = [m for m in cat if summA[t]["manipulation_check"][f"forced:{m}"]["share_labelled_X"] < 0.5]
        if not flagged:
            out[t] = {"flagged_modes": []}
            continue
        l = gate[t]["l_star"]
        iN = [i for i, r in enumerate(index) if r["task"] == t and r["condition"].startswith("forced:")]
        lab = [index[i]["condition"].split(":")[1] for i in iN]
        Xn = H[l][iN]
        mu, comps, _ = pca95(Xn)
        P = (Xn - mu) @ comps.T
        G, _ = knn_graph(P, 10)
        C = np.stack([Xn[[k for k, m in enumerate(lab) if m == mm]].mean(0) for mm in cat])
        lab_of = {(r["condition"], r["paraphrase_id"]): r["label"] for r in rows["A"] if r["task"] == t and r["condition"].startswith("forced:")}
        Cs = C.copy()
        kept = {}
        for m in flagged:
            sel = [i for i in iN if lab_of.get((index[i]["condition"], index[i]["paraphrase_id"])) == m and index[i]["condition"] == f"forced:{m}"]
            kept[m] = len(sel)
            if len(sel) >= 3:
                Cs[cat.index(m)] = H[l][sel].mean(0)
        D0 = geodesic_between(G, P, (C - mu) @ comps.T, 10)
        D1 = geodesic_between(G, P, (Cs - mu) @ comps.T, 10)
        changes = {}
        for eid, ev in preds["events"].items():
            if ev["task"] != t:
                continue
            S, Xk = ev["survivors"], ev["X_k"]
            n0 = S[int(np.argmin([D0[cat.index(Xk), cat.index(m)] for m in S]))]
            n1 = S[int(np.argmin([D1[cat.index(Xk), cat.index(m)] for m in S]))]
            changes[eid] = {"nearest_committed_centroids": n0, "nearest_sensitivity_centroids": n1, "changed": n0 != n1}
        out[t] = {"flagged_modes": flagged, "n_paraphrases_kept": kept, "centroid_geodesic_sensitivity": D1.tolist(),
                  "event_nearest_changes": changes,
                  "n_events_changed": int(sum(v["changed"] for v in changes.values()))}
    return out


# ============================================================================================ E5 contest
PREDS = ["association", "frequency", "geodesic", "decoder"]


def score_event(ev: dict, rr: list[dict], cat: list[str]) -> dict:
    S = ev["survivors"]
    bset = ev["banset"]
    comp = [r for r in rr if r["passed"] and r["label"] not in bset and r["label"] != "no_code"]
    cnt = Counter(r["label"] for r in comp)
    real = np.array([cnt.get(m, 0) for m in S], float)
    lead_ok = False
    ranked = cnt.most_common()
    if ranked:
        lead = (ranked[0][1] - (ranked[1][1] if len(ranked) > 1 else 0)) / max(len(comp), 1)
        lead_ok = lead >= 0.15
    realised = ranked[0][0] if (ranked and lead_ok) else None
    out = {"n": len(rr), "n_compliant": len(comp), "compliance": len(comp) / max(len(rr), 1),
           "realised_counts": dict(cnt), "realised_mode": realised or "no clear mode",
           "realised_in_survivors": realised in S if realised else None, "predictors": {}}
    scored = [r for r in rr if r["label"] in S or r["label"] == "other"]
    for p in PREDS + ["association_X1"]:
        q = np.array([ev["distributions"][p][m] for m in S])
        top1 = S[int(np.argmax(q))]
        qm = 0.98 * (0.95 * q + 0.05 / len(S))
        lp = [math.log(qm[S.index(r["label"])]) if r["label"] in S else math.log(0.02) for r in scored]
        rs = real + 0.5
        js = js_div(q, rs / rs.sum())
        from scipy.stats import spearmanr

        sp = float(spearmanr(q, real)[0]) if len(S) > 2 and real.std() > 0 and q.std() > 0 else float("nan")
        top2p = set(np.array(S)[np.argsort(-q)[:2]])
        top2r = set(np.array(S)[np.argsort(-real)[:2]])
        tied = bool(ev.get("top1_tied", {}).get(p, False))
        out["predictors"][p] = {"top1": top1, "tied": tied,
                                "hit": (None if tied else ((top1 == realised) if realised else False)),
                                "log_score_mean": float(np.mean(lp)) if lp else float("nan"), "n_scored": len(lp),
                                "js_to_realised": js, "spearman": sp, "top2_agreement": len(top2p & top2r) / 2}
    return out


def contest(rows, preds, phaseC) -> dict:
    events = {}
    for eid, ev in preds["events"].items():
        t = ev["task"]
        cat = CATALOGUE[t]
        if ev["kind"] == "ban":
            cond = "ban:" + "+".join(ev["banset"])
            rr = [r for r in rows["C"] if r["task"] == t and r["condition"] == cond]
        else:
            # removal event scored on the strongest successful d_X arm (filled in by c2)
            continue
        if not rr:
            continue
        sc = score_event(ev, rr, cat)
        per_para = {}
        for pid in sorted({r["paraphrase_id"] for r in rr}):
            rp = [r for r in rr if r["paraphrase_id"] == pid]
            per_para[pid] = {"n": len(rp), "compliant": sum(r["passed"] and r["label"] not in ev["banset"] and r["label"] != "no_code" for r in rp),
                             "labels": dict(Counter(r["label"] for r in rp))}
        sc["per_paraphrase"] = per_para
        sc["exploratory"] = bool(phaseC.get("events", {}).get(eid, {}).get("exploratory", False))
        sc["ban_failure"] = sc["compliance"] < 0.5
        sc.update({"event": eid, "task": t, "banset": ev["banset"], "survivors": ev["survivors"],
                   "committed_top1": ev["top1"], "concordance": ev["concordance"], "stability": ev["stability"],
                   "ambiguity_flag": ev["ambiguity_flag"]})
        events[eid] = sc
    return events


def contest_aggregate(events: dict, primary_only: bool = False) -> dict:
    agg = {}
    sc = [e for e in events.values() if not (primary_only and e.get("exploratory"))]
    for p in PREDS + ["association_X1"]:
        scored = [e for e in sc if e["predictors"][p]["hit"] is not None]
        hits = sum(bool(e["predictors"][p]["hit"]) for e in scored)
        n = len(scored)
        agg[p] = {"hits": hits, "events": n, "events_tied_excluded": len(sc) - n, "hit_rate": hits / max(n, 1),
                  "wilson": wilson(hits, n),
                  "mean_log_score": float(np.nanmean([e["predictors"][p]["log_score_mean"] for e in sc])) if sc else None,
                  "mean_js": float(np.nanmean([e["predictors"][p]["js_to_realised"] for e in sc])) if sc else None,
                  "mean_top2": float(np.nanmean([e["predictors"][p]["top2_agreement"] for e in sc])) if sc else None}
    trio = ["association", "frequency", "geodesic"]
    M = {a: {b: float(np.mean([e["committed_top1"][a] == e["committed_top1"][b] for e in sc])) if sc else None
             for b in trio} for a in trio}
    return {"per_predictor": agg, "agreement_matrix_top1": M, "n_events": len(sc),
            "note": "descriptive only: about 4-7 events, no p-values"}


# ============================================================================================ E6 C3 decomposition
def lexical_vectors(tok_ids: dict[str, list[int]]) -> tuple[dict, dict]:
    """Mean input embedding of each name's tokens and the unembedding row of its first token."""
    from huggingface_hub import snapshot_download
    from safetensors import safe_open

    snap = Path(snapshot_download("Qwen/Qwen3-8B", local_files_only=True))
    emb, unemb = {}, {}
    want = {"model.embed_tokens.weight": emb, "lm_head.weight": unemb}
    for f in sorted(snap.glob("*.safetensors")):
        with safe_open(str(f), framework="pt") as fh:
            for key, store in want.items():
                if key in fh.keys():
                    sl = fh.get_slice(key)
                    for name, ids in tok_ids.items():
                        if key.startswith("model.embed"):
                            store[name] = np.mean([sl[i:i + 1].float().numpy()[0] for i in ids], 0)
                        else:
                            store[name] = sl[ids[0]:ids[0] + 1].float().numpy()[0]
    return emb, unemb


def shares(shift: np.ndarray, Bgs: np.ndarray) -> dict:
    tot = float(shift @ shift)
    comps = {}
    acc = np.zeros_like(shift)
    for name, u in zip(("ren", "sub", "typ", "rel"), Bgs):
        if np.linalg.norm(u) < 1e-6:
            comps[name] = {"share": float("nan"), "proj": float("nan")}
            continue
        pr = float(shift @ u)
        comps[name] = {"share": pr * pr / max(tot, 1e-12), "proj": pr}
        acc += pr * u
    res = shift - acc
    comps["residual"] = {"share": float(res @ res) / max(tot, 1e-12)}
    comps["norm"] = math.sqrt(tot)
    return comps


def c3(index, H, gate, geoB) -> dict:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B")
    out = {"synthetic_test": None, "per_task": {}}
    # synthetic decomposition test (testing plan 8)
    D = 64
    q, _ = np.linalg.qr(RNG.standard_normal((D, 4)))
    s = shares(0.6 * q[:, 0] + 0.8 * q[:, 1], q.T)
    out["synthetic_test"] = {"ren": s["ren"]["share"], "sub": s["sub"]["share"], "pass":
                             abs(s["ren"]["share"] - 0.36) < 1e-6 and abs(s["sub"]["share"] - 0.64) < 1e-6}
    names = {}
    for t in TASKS:
        for m in CATALOGUE[t]:
            names[f"{t}:{m}"] = tok(" " + DISPLAY[t][m], add_special_tokens=False)["input_ids"]
    try:
        emb, unemb = lexical_vectors(names)
    except (OSError, KeyError, ValueError) as e:
        logger.error(f"lexical vectors unavailable: {e}")
        emb, unemb = {}, {}
    for t in TASKS:
        cat = CATALOGUE[t]
        Bz = np.load(CACHE / f"basis_{t}.npz")
        Bgs, Braw = Bz["Bgs"], Bz["B"]
        lstar, band = gate[t]["l_star"], gate[t]["band"]
        res_t = {}

        def per_para(cond, l):
            ii = sorted([i for i, r in enumerate(index) if r["task"] == t and r["condition"] == cond],
                        key=lambda i: index[i]["paraphrase_id"])
            return H[l][ii]

        for xi, X in enumerate(cat):
            meta = geoB[t]["basis_meta"][X]
            rx = {"meta": meta, "layers": {}}
            for l in band if lstar in band else [lstar]:
                li = CACHE_LAYERS.index(l)
                ban, men, lst = per_para(f"ban:{X}", l), per_para(f"mention:{X}", l), per_para("listall", l)
                rl = {}
                for ref_name, ref in (("mention", men), ("listall", lst)):
                    shift = ban.mean(0) - ref.mean(0)
                    sh = shares(shift, Bgs[xi, li])
                    boots = []
                    for _ in range(1000):
                        ib = RNG.integers(0, 10, 10)
                        ir = ib if ref_name == "mention" else RNG.integers(0, 10, 10)
                        sb = shares(ban[ib].mean(0) - ref[ir].mean(0), Bgs[xi, li])
                        boots.append([sb["ren"]["share"], sb["sub"]["share"], sb["typ"]["share"], sb["rel"]["share"],
                                      sb["sub"]["share"] - sb["ren"]["share"]])
                    boots = np.array(boots)
                    ci = {k: [float(np.nanpercentile(boots[:, j], 2.5)), float(np.nanpercentile(boots[:, j], 97.5))]
                          for j, k in enumerate(["ren", "sub", "typ", "rel", "sub_minus_ren"])}
                    # aimed test: u_ren-removed shift on u_sub vs u_typ (each orthogonal to u_ren only)
                    u_ren, u_sub, u_typ = Braw[xi, li, 0], Braw[xi, li, 1], Braw[xi, li, 2]
                    s_perp = shift - (shift @ u_ren) * u_ren
                    aimed = {"proj_sub": float(s_perp @ u_sub), "proj_typ": float(s_perp @ u_typ) if np.linalg.norm(u_typ) > 0 else None}
                    lex = {}
                    key = f"{t}:{X}"
                    if key in emb:
                        lex = {"cos_input_embedding_name": float(unit(shift) @ unit(emb[key])),
                               "cos_unembedding_first_token": float(unit(shift) @ unit(unemb[key]))}
                    # survivor-permutation rank of the associate among all survivors
                    Cl = np.stack([H[l][[i for i, r in enumerate(index) if r["task"] == t and r["condition"] == f"forced:{m}"]].mean(0) for m in cat])
                    sv = [m for m in cat if m != X]
                    sh_sv = {}
                    for m in sv:
                        mo = np.mean([Cl[cat.index(k)] for k in sv], 0)
                        u = Cl[cat.index(m)] - mo
                        u = unit(u - (u @ u_ren) * u_ren)
                        sh_sv[m] = float((s_perp @ u) ** 2 / max(shift @ shift, 1e-12)) * np.sign(s_perp @ u)
                    order = sorted(sv, key=lambda m: -sh_sv[m])
                    rl[ref_name] = {"shares": sh, "ci95": ci, "aimed": aimed, "lexical": lex,
                                    "survivor_signed_shares": sh_sv, "associate_rank": order.index(meta["alt"]) + 1,
                                    "n_survivors": len(sv)}
                # paraphrase null: split-half (5 vs 5) differences within ban:X and within mention:X
                null_ren = []
                for _ in range(500):
                    for arr in (ban, men):
                        perm = RNG.permutation(10)
                        d = arr[perm[:5]].mean(0) - arr[perm[5:]].mean(0)
                        null_ren.append(shares(d, Bgs[xi, li])["ren"]["share"])
                rl["null_ren_share_p95"] = float(np.nanpercentile(null_ren, 95))
                both_sub = all(rl[r]["ci95"]["sub_minus_ren"][0] > 0 for r in ("mention", "listall"))
                both_ren = all(rl[r]["ci95"]["sub_minus_ren"][1] < 0 for r in ("mention", "listall"))
                ren_reg = all(rl[r]["shares"]["ren"]["share"] > rl["null_ren_share_p95"] for r in ("mention", "listall"))
                rl["verdict"] = ("substitution > subtraction" if (both_sub and ren_reg) else
                                 "subtraction > substitution" if (both_ren and ren_reg) else "inconclusive")
                rx["layers"][str(l)] = rl
            res_t[X] = rx
        out["per_task"][t] = res_t
    return out


def fig_c3(c3o, gate):
    import matplotlib.pyplot as plt

    for t in TASKS:
        cat = CATALOGUE[t]
        l = str(gate[t]["l_star"])
        fig, axes = plt.subplots(1, 2, figsize=(13, 4.2), sharey=True)
        for ax, ref in zip(axes, ("mention", "listall")):
            comps = ["ren", "sub", "typ", "rel", "residual"]
            cols = ["#d62728", "#2ca02c", "#1f77b4", "#9467bd", "0.7"]
            bottom = np.zeros(len(cat))
            for c, col in zip(comps, cols):
                v = np.array([np.nan_to_num(c3o["per_task"][t][X]["layers"][l][ref]["shares"][c]["share"]) for X in cat])
                ax.bar(range(len(cat)), v, bottom=bottom, color=col, label=c if ref == "mention" else None)
                bottom += v
            for k, X in enumerate(cat):
                ci = c3o["per_task"][t][X]["layers"][l][ref]["ci95"]["sub_minus_ren"]
                ax.text(k, 1.02, f"sub-ren\n[{ci[0]:.2f},{ci[1]:.2f}]", ha="center", fontsize=6)
            ax.set_xticks(range(len(cat)))
            ax.set_xticklabels([f"ban:{X}" for X in cat], rotation=30, fontsize=7)
            ax.set_title(f"{t} layer {l}: squared-norm shares of shift(ban:X - {ref})", fontsize=9)
            ax.set_ylim(0, 1.15)
        axes[0].legend(fontsize=7, title="component", loc="center left")
        fig.tight_layout()
        for ext in ("png", "pdf"):
            fig.savefig(FIG / f"c3_shares_{t}.{ext}", dpi=160)
        plt.close(fig)


# ============================================================================================ E7 C2 removal
def c2(rows, preds, summA, index, H, gate, events_c) -> dict:
    out = {}
    for t in TASKS:
        cat = CATALOGUE[t]
        X = summA[t]["modal"]
        rr = [r for r in rows["D"] if r["task"] == t]
        if not rr:
            continue
        arms = sorted({r["arm"] for r in rr})
        a0 = sorted([r for r in rr if r["arm"] == "hooked_alpha0"], key=lambda r: r["sample_id"])
        pr0 = np.mean([r["passed"] for r in a0]) if a0 else float("nan")
        ev = preds["events"][f"{t}|removal:{X}"]
        S = ev["survivors"]
        base_counts = np.array([summA[t]["baseline_label_counts"].get(m, 0) for m in S], float)
        p_base = (base_counts + 1e-9) / max(base_counts.sum(), 1e-9)
        l = gate[t]["l_star"]
        Cl = np.stack([H[l][[i for i, r in enumerate(index) if r["task"] == t and r["condition"] == f"forced:{m}"]].mean(0) for m in cat])
        cbar = Cl.mean(0)
        cosx = {m: float(unit(Cl[cat.index(m)] - cbar) @ unit(Cl[cat.index(X)] - cbar)) for m in S}
        ban_rows = [r for r in rows["C"] if r["task"] == t and r["condition"] == f"ban:{X}"]
        ban_cnt = Counter(r["label"] for r in ban_rows if r["passed"] and r["label"] in S)
        # split-half noise floor of the prompt-ban distribution
        floor = []
        if len(ban_rows) >= 10:
            labs = [r["label"] for r in ban_rows if r["passed"] and r["label"] in S]
            for _ in range(500):
                perm = RNG.permutation(len(labs))
                h1 = Counter(labs[i] for i in perm[: len(labs) // 2])
                h2 = Counter(labs[i] for i in perm[len(labs) // 2:])
                floor.append(js_div({m: h1.get(m, 0) + 0.5 for m in S}, {m: h2.get(m, 0) + 0.5 for m in S}))
        res = {"modal": X, "survivors": S, "hooked_alpha0_pass_rate": pr0, "arms": {}}
        for arm in arms:
            ra = sorted([r for r in rr if r["arm"] == arm], key=lambda r: r["sample_id"])
            n = len(ra)
            pr = np.mean([r["passed"] for r in ra])
            moved = [r["label"] not in (X, "no_code") for r in ra]
            corr = Counter(r["label"] for r in ra if r["passed"])
            flips = [ra[i]["label"] != a0[i]["label"] for i in range(min(len(ra), len(a0)))]
            same_text = [ra[i]["raw_text"] == a0[i]["raw_text"] for i in range(min(len(ra), len(a0)))]
            x_to_other = sum(a0[i]["label"] == X and ra[i]["label"] not in (X, "no_code") for i in range(min(len(ra), len(a0))))
            success = (np.mean(moved) >= 0.5) and (pr >= 0.8 * pr0)
            p_rem = np.array([corr.get(m, 0) for m in S], float)
            p_rem_n = p_rem / p_rem.sum() if p_rem.sum() > 0 else p_rem
            from scipy.stats import spearmanr

            gain = [math.log((p_rem_n[k] + 0.01) / (p_base[k] / max(p_base.sum(), 1e-9) + 0.01)) for k in range(len(S))]
            cg = float(spearmanr([cosx[m] for m in S], gain)[0]) if p_rem.sum() > 0 and np.std(gain) > 0 else float("nan")
            js_ban = js_div({m: corr.get(m, 0) + 0.5 for m in S}, {m: ban_cnt.get(m, 0) + 0.5 for m in S}) if ban_rows else None
            # predictor scores on removal samples
            pscore = {}
            if p_rem.sum() > 0:
                top_real = S[int(np.argmax(p_rem))]
                for p in PREDS:
                    q = np.array([ev["distributions"][p][m] for m in S])
                    qm = 0.98 * (0.95 * q + 0.05 / len(S))
                    lp = [math.log(qm[S.index(r["label"])]) if r["label"] in S else math.log(0.02)
                          for r in ra if r["label"] in S or r["label"] == "other"]
                    tied = bool(ev.get("top1_tied", {}).get(p, False))
                    pscore[p] = {"top1": S[int(np.argmax(q))], "tied": tied,
                                 "hit": None if tied else S[int(np.argmax(q))] == top_real,
                                 "log_score_mean": float(np.mean(lp)) if lp else float("nan")}
            res["arms"][arm] = {
                "n": n, "alpha": ra[0]["alpha"], "exploratory": arm.startswith("full_"),
                "variant": ("full affine (prompt suffix + generated positions)" if arm.startswith("full_")
                            else "pre-declared run variant (see phaseD_tests.json)"), "pass_rate": float(pr), "pass_wilson": wilson(int(sum(r["passed"] for r in ra)), n),
                "moved_frac": float(np.mean(moved)), "moved_wilson": wilson(int(sum(moved)), n),
                "label_counts": dict(Counter(r["label"] for r in ra)), "correct_label_counts": dict(corr),
                "hill_cc": hill1(corr), "flips_vs_alpha0": int(sum(flips)), "flip_frac": float(np.mean(flips)) if flips else None,
                "X_to_other_flips": int(x_to_other), "success": bool(success),
                "identical_text_vs_alpha0_frac": float(np.mean(same_text)) if same_text else None,
                "modal_survivor": (S[int(np.argmax(p_rem))] if p_rem.sum() > 0 else None),
                "cosine_gain_spearman": cg, "js_to_prompt_ban": js_ban,
                "prompt_ban_split_half_floor_p95": float(np.percentile(floor, 95)) if floor else None,
                "predictor_scores": pscore}
        # verdict on the strongest successful d_X alpha
        dx = sorted([a for a in res["arms"] if a.startswith("dX_")], key=lambda a: -res["arms"][a]["alpha"])
        succ = [a for a in dx if res["arms"][a]["success"]]
        ban_eid = f"{t}|ban:{X}"
        ban_real = events_c.get(ban_eid, {}).get("realised_mode")
        if succ:
            a = succ[0]
            ms = res["arms"][a]["modal_survivor"]
            assoc = ev["top1"]["association"]
            if ms == ban_real == assoc:
                verdict = "routing"
            else:
                match = [p for p in PREDS if ev["top1"][p] == ms]
                verdict = f"dissociation ({', '.join(match) if match else 'none'})"
            res["verdict_arm"] = a
        else:
            collateral = any(res["arms"][a]["moved_frac"] >= 0.5 and not res["arms"][a]["success"] for a in dx)
            verdict = "collateral damage; C2 untestable" if collateral else "untestable (removal unsuccessful at the tested coefficients)"
        res["verdict"] = verdict
        res["prompt_ban_realised_mode"] = ban_real
        out[t] = res
    return out


def fig_c2(c2o):
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, len(c2o), figsize=(6.5 * len(c2o), 4.2))
    axes = np.atleast_1d(axes)
    for ax, (t, res) in zip(axes, c2o.items()):
        arms = sorted(res["arms"], key=lambda a: (a.split("_")[0] != "hooked", a.split("_")[0], res["arms"][a]["alpha"]))
        x = np.arange(len(arms))
        mv = [res["arms"][a]["moved_frac"] for a in arms]
        pr = [res["arms"][a]["pass_rate"] for a in arms]
        mvci = np.array([res["arms"][a]["moved_wilson"] for a in arms])
        prci = np.array([res["arms"][a]["pass_wilson"] for a in arms])
        nc = [res["arms"][a]["label_counts"].get("no_code", 0) / max(res["arms"][a]["n"], 1) for a in arms]
        ax.bar(x - 0.27, mv, 0.27, yerr=[np.array(mv) - mvci[:, 0], mvci[:, 1] - np.array(mv)], label="moved fraction",
               color="#d62728", capsize=2)
        ax.bar(x, pr, 0.27, yerr=[np.array(pr) - prci[:, 0], prci[:, 1] - np.array(pr)], label="pass rate",
               color="#1f77b4", capsize=2)
        ax.bar(x + 0.27, nc, 0.27, label="no code (degenerate output)", color="0.55")
        ax.axhline(0.5, color="#d62728", ls=":", lw=0.8)
        ax.axhline(0.8 * res["hooked_alpha0_pass_rate"], color="#1f77b4", ls=":", lw=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels([a + (" (expl.)" if res["arms"][a].get("exploratory") else "") for a in arms], rotation=35,
                           fontsize=7, ha="right")
        ax.set_ylim(0, 1.05)
        ax.set_title(f"{t}: removal of {res['modal']} (verdict: {res['verdict']})", fontsize=9)
    axes[0].legend(fontsize=7)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"removal_outcomes.{ext}", dpi=160)
    plt.close(fig)


# ============================================================================================ method_out
def method_out(rows, contest_events, removal_events, summaries_, deviations, summary_meta, prompts_by_id):
    datasets = []
    for t in TASKS:
        ex = []
        for ph in ("A", "C", "D"):
            for r in rows[ph]:
                if r["task"] != t:
                    continue
                p = prompts_by_id.get(r["prompt_id"])
                banned = r["condition"].split(":", 1)[1].split("+") if r["condition"].startswith("ban:") else []
                ex.append({"input": p["text"] if p else r["prompt_id"], "output": r.get("raw_text") or "",
                           "predict_mode_label": str(r["label"]), "predict_passed": str(bool(r["passed"])),
                           "predict_compliant": str(bool(r["compliant"]) if "compliant" in r else
                                                    bool(r["passed"] and r["label"] not in banned and r["label"] != "no_code")),
                           "metadata_phase": ph, "metadata_condition": r["condition"],
                           "metadata_paraphrase_id": r["paraphrase_id"], "metadata_sample_id": r["sample_id"],
                           "metadata_model": r["model"], "metadata_decoding": r["decoding"],
                           "metadata_labeller_source": r["labeller_source"], "metadata_wall_s": r.get("wall_s"),
                           "metadata_code_sha256": r.get("code_sha256"), "metadata_arm": r.get("arm"),
                           "metadata_alpha": r.get("alpha"), "metadata_fail_kind": r.get("fail_kind")})
        datasets.append({"dataset": TASK_DATASET[t], "examples": ex})
    ce = []
    for eid, e in list(contest_events.items()) + list(removal_events.items()):
        ce.append({"input": f"{eid} | banset={e['banset']} | survivors={e['survivors']}",
                   "output": json.dumps(e.get("realised_counts", {})),
                   "predict_association": json.dumps(e["distributions"]["association"]),
                   "predict_frequency": json.dumps(e["distributions"]["frequency"]),
                   "predict_geodesic": json.dumps(e["distributions"]["geodesic"]),
                   "predict_decoder": json.dumps(e["distributions"]["decoder"]),
                   "metadata_commit_sha256": e["commit_sha256"], "metadata_concordance": e["concordance"],
                   "metadata_stability": e["stability"], "metadata_realised_mode": e.get("realised_mode"),
                   "metadata_hits": e.get("hits")})
    if ce:
        datasets.append({"dataset": "contest_events", "examples": ce})
    return {"metadata": {"method_name": "path-search ban screen (Qwen3-8B)", "summary": summary_meta,
                         "deviations": deviations}, "datasets": datasets}


@logger.catch(reraise=True)
def main() -> None:
    FIG.mkdir(exist_ok=True)
    rows, index, H = load_all()
    gate = json.loads((RES / "gate.json").read_text())
    geoB = json.loads((RES / "geometry_b.json").read_text())
    summA = json.loads((RES / "phaseA_summary.json").read_text())
    preds = json.loads((ROOT / "predictions" / "predictions_v1.json").read_text())
    commit = read_jsonl(ROOT / "predictions" / "commit_log.jsonl")[-1]
    phaseC = json.loads((RES / "phaseC_events.json").read_text()) if (RES / "phaseC_events.json").exists() else {}
    prompts_by_id = {p["prompt_id"]: p for p in read_jsonl(ROOT / "prompts" / "prompts.jsonl")}
    summ = summaries(rows)
    jdump(summ, "summaries.json")
    jdump({t: summA[t]["association"] for t in TASKS}, "association.json")
    fig_gate(gate)
    man = manifold(index, H, gate, summA, geoB, phaseC, rows)
    jdump(man, "manifold.json")
    jdump(manip_sensitivity(index, H, gate, summA, rows, preds), "manipulation_sensitivity.json")
    # contest (ban events) -- timestamps after commit
    ce = contest(rows, preds, phaseC)
    for eid, e in ce.items():
        e["commit_sha256"] = commit["sha256"]
        e["distributions"] = preds["events"][eid]["distributions"]
        e["hits"] = {p: e["predictors"][p]["hit"] for p in PREDS}
        first = min(r["utc"] for r in rows["C"] if f"{e['task']}|ban:{'+'.join(e['banset'])}" == r.get("event_tag"))
        e["first_sample_after_commit"] = bool(first > commit["unix"])
    agg = contest_aggregate(ce)
    agg_primary = contest_aggregate(ce, primary_only=True)
    jdump({"events": ce, "aggregate_all": agg, "aggregate_primary": agg_primary, "commit": commit}, "contest.json")
    c3o = c3(index, H, gate, geoB)
    jdump(c3o, "c3_decomposition.json")
    fig_c3(c3o, gate)
    c2o = c2(rows, preds, summA, index, H, gate, ce)
    jdump(c2o, "c2_removal.json")
    if c2o:
        fig_c2(c2o)
    removal_events = {}
    for t, res in c2o.items():
        eid = f"{t}|removal:{res['modal']}"
        ev = preds["events"][eid]
        arm = res.get("verdict_arm") or max((a for a in res["arms"] if a.startswith("dX_")), key=lambda a: res["arms"][a]["alpha"])
        removal_events[eid] = {"banset": ev["banset"], "survivors": ev["survivors"], "distributions": ev["distributions"],
                               "commit_sha256": commit["sha256"], "concordance": ev["concordance"],
                               "stability": ev["stability"], "realised_counts": res["arms"][arm]["correct_label_counts"],
                               "realised_mode": res["arms"][arm]["modal_survivor"], "arm": arm,
                               "hits": {p: v["hit"] for p, v in res["arms"][arm]["predictor_scores"].items()}}
    # E8 BUY row
    buy = {}
    for t in TASKS:
        X = summA[t]["modal"]
        b = summ[t].get("baseline")
        pb = summ[t].get(f"ban:{X}")
        row = {}
        if b and pb:
            dp = (b["pass_rate"] - pb["pass_rate"]) * 100
            row["prompt_ban"] = {"hill_cc_base": b["hill_cc"], "hill_cc_ban": pb["hill_cc"], "pass_base": b["pass_rate"],
                                 "pass_ban": pb["pass_rate"], "d_hill_per_pass_point_lost": (pb["hill_cc"] - b["hill_cc"]) / dp if dp > 0 else None}
        if t in c2o:
            res = c2o[t]
            a = res.get("verdict_arm")
            if a and "hooked_alpha0" in res["arms"]:
                a0 = res["arms"]["hooked_alpha0"]
                dp = (a0["pass_rate"] - res["arms"][a]["pass_rate"]) * 100
                row["removal"] = {"arm": a, "hill_cc_a0": a0["hill_cc"], "hill_cc_rem": res["arms"][a]["hill_cc"],
                                  "pass_a0": a0["pass_rate"], "pass_rem": res["arms"][a]["pass_rate"],
                                  "d_hill_per_pass_point_lost": (res["arms"][a]["hill_cc"] - a0["hill_cc"]) / dp if dp > 0 else None}
        buy[t] = row
    jdump(buy, "buy.json")
    deviations = json.loads((RES / "deviations.json").read_text()) if (RES / "deviations.json").exists() else []
    summary_meta = {
        "baseline": {t: {"modal": summA[t]["modal"], "modal_share": summA[t]["modal_share_parseable"],
                         "counts": summA[t]["baseline_label_counts"], "pass_rate": summA[t]["pass_rate"],
                         "hill_cc": summA[t]["hill_cc"]} for t in TASKS},
        "gate": {t: {"l_star": gate[t]["l_star"], "band": gate[t]["band"], "pass": gate[t]["gate_pass"]} for t in TASKS},
        "contest_aggregate_all": agg, "contest_aggregate_primary": agg_primary,
        "contest_events": {eid: {"compliance": e["compliance"], "realised_mode": e["realised_mode"],
                                 "realised_counts": e["realised_counts"], "exploratory": e["exploratory"],
                                 "top1": {p: e["predictors"][p]["top1"] for p in PREDS},
                                 "hits": e["hits"]} for eid, e in ce.items()},
        "c2_verdicts": {t: c2o[t]["verdict"] for t in c2o},
        "c3_verdicts": {t: {X: c3o["per_task"][t][X]["layers"][str(gate[t]["l_star"])]["verdict"] for X in CATALOGUE[t]}
                        for t in TASKS},
        "buy": buy, "commit_sha256": commit["sha256"]}
    jdump(summary_meta, "run_summary.json")
    mo = method_out(rows, ce, removal_events, summ, deviations, summary_meta, prompts_by_id)
    (ROOT / "method_out.json").write_text(json.dumps(mo, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)))
    logger.info(f"method_out.json written: {[(d['dataset'], len(d['examples'])) for d in mo['datasets']]}")


if __name__ == "__main__":
    main()
