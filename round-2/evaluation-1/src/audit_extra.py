#!/usr/bin/env python3
"""Second independent audit of the headline TEST results (separate code paths, raw inputs only), each with a placebo
that must fail:
  1. T2 locus at k_pre, layer 8: within-paraphrase permutation test (sklearn path, 40 refits) + permuted-label placebo.
  2. T2 geometry L24 k=10: share of paraphrase subsamples with Floyd-Warshall nearest to Dijkstra (networkx path,
     100 draws) + shuffled-mode-label placebo.
  3. Sham-ban promotions (exp1): Fisher test >=10 points, pandas/scipy path + condition-shuffled placebo.
  4. PREDICT primary gate on informative forecast events: avoidance/attempted counts from raw rows.
Usage: uv run audit_extra.py
"""
from __future__ import annotations

import ast
import json
import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import networkx as nx
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from loguru import logger
from scipy.stats import fisher_exact
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, log_loss
from sklearn.model_selection import GroupKFold
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from common import EXP, RES, clean, jdump, setup_logging


def lopo_ba(Z: np.ndarray, y: np.ndarray, g: np.ndarray) -> float:
    pred = np.zeros(len(y))
    for gg in np.unique(g):
        tr, te = g != gg, g == gg
        feat = make_pipeline(StandardScaler(), PCA(64, svd_solver="full")).fit(Z[tr])
        A, At = feat.transform(Z[tr]), feat.transform(Z[te])
        best = None
        for C in (0.01, 0.1, 1.0):
            oof = np.zeros(tr.sum())
            for a, b in GroupKFold(3).split(A, y[tr], g[tr]):
                oof[b] = LogisticRegression(C=C, class_weight="balanced", max_iter=5000).fit(A[a], y[tr][a]).predict_proba(A[b])[:, 1]
            ll = log_loss(y[tr], np.clip(oof, 1e-15, 1 - 1e-15), labels=[0, 1])
            if best is None or ll < best[0] - 1e-12:
                best = (ll, C)
        pred[te] = LogisticRegression(C=best[1], class_weight="balanced", max_iter=5000).fit(A, y[tr]).predict_proba(At)[:, 1]
    return float(balanced_accuracy_score(y, pred >= 0.5))


def within_perm(y: np.ndarray, g: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    out = y.copy()
    for gg in np.unique(g):
        i = np.where(g == gg)[0]
        out[i] = rng.permutation(y[i])
    return out


def locus_test(n_perm: int = 40) -> dict:
    sd = EXP["exp3"] / "states"
    X = np.concatenate([np.load(p)["X"][:, 6, 0, :] for p in sorted(sd.glob("T2_part_*.npz"))]).astype(np.float64)  # k_pre, layer 8
    meta = json.loads((sd / "T2_meta.json").read_text())["rows"]
    idx = [i for i, r in enumerate(meta) if r["arm"] == "G2" and r["label"] in ("bellman_ford_spfa", "dijkstra")]
    y = np.array([int(meta[i]["label"] == "bellman_ford_spfa") for i in idx])
    g = np.array([int(meta[i]["paraphrase_id"]) for i in idx])
    Z = X[idx]
    rng = np.random.default_rng(123)
    obs = lopo_ba(Z, y, g)
    perms = [within_perm(y, g, rng) for _ in range(n_perm)]
    null = np.array(Parallel(n_jobs=6)(delayed(lopo_ba)(Z, yp, g) for yp in perms))
    p = float((1 + (null >= obs - 1e-12).sum()) / (1 + n_perm))
    # placebo: the same test on a within-paraphrase-permuted 'observed' label vector must not be significant
    yplc = within_perm(y, g, np.random.default_rng(999))
    obs_p = lopo_ba(Z, yplc, g)
    null_p = np.array(Parallel(n_jobs=6)(delayed(lopo_ba)(Z, within_perm(yplc, g, np.random.default_rng(500 + b)), g) for b in range(n_perm)))
    p_plc = float((1 + (null_p >= obs_p - 1e-12).sum()) / (1 + n_perm))
    return {"observed_BA": obs, "null_mean": float(null.mean()), "null_max": float(null.max()), "p_within": p,
            "placebo_BA": obs_p, "placebo_p_within": p_plc, "placebo_failed_as_expected": bool(p_plc > 0.05),
            "n_perm": n_perm}


def geodesic_order(X: np.ndarray, lab: np.ndarray, k: int = 10) -> list[str]:
    mu = X.mean(0)
    pca = PCA(n_components=min(50, len(X) - 1), svd_solver="full").fit(X)
    kk = max(2, min(int(np.searchsorted(np.cumsum(pca.explained_variance_ratio_), 0.95) + 1), 50))
    P = (X - mu) @ pca.components_[:kk].T
    cats = ["dijkstra", "bellman_ford_spfa", "bidir_dijkstra", "floyd_warshall", "dial"]
    Cp = (np.stack([X[lab == m].mean(0) for m in cats]) - mu) @ pca.components_[:kk].T
    G = nx.Graph()
    dist, ind = NearestNeighbors(n_neighbors=k + 1).fit(P).kneighbors(P)
    for i in range(len(P)):
        for d, j in zip(dist[i, 1:], ind[i, 1:]):
            G.add_edge(i, int(j), weight=float(d))
    if not nx.is_connected(G):  # MST patch, as in exp2 geometry.py
        T = nx.minimum_spanning_tree(nx.Graph([(i, j, {"weight": float(np.linalg.norm(P[i] - P[j]))})
                                               for i in range(len(P)) for j in range(i + 1, len(P))]))
        G.add_edges_from(T.edges(data=True))
    dc, ic = NearestNeighbors(n_neighbors=k).fit(P).kneighbors(Cp)
    for a in range(len(cats)):
        for d, j in zip(dc[a], ic[a]):
            G.add_edge(("c", a), int(j), weight=float(d))
    sp = nx.single_source_dijkstra_path_length(G, ("c", 0), weight="weight")
    return sorted(cats[1:], key=lambda m: sp[("c", cats.index(m))])


def geometry_test(n_draws: int = 100) -> dict:
    index = [json.loads(l) for l in (EXP["exp2"] / "cache" / "hR_index.jsonl").read_text().splitlines() if l.strip()]
    H = np.load(EXP["exp2"] / "cache" / "hR_layer24.npy", mmap_mode="r")
    sel = [i for i, r in enumerate(index) if r["task"] == "t2" and r["condition"].startswith("forced:")]
    X = np.asarray(H[sel], dtype=np.float64)
    lab = np.array([index[i]["condition"].split(":")[1] for i in sel])
    pid = np.array([int(index[i]["paraphrase_id"]) for i in sel])
    rng = np.random.default_rng(77)
    ids = np.unique(pid)
    draws = [rng.choice(ids, 24, replace=False) for _ in range(n_draws)]
    res = Parallel(n_jobs=6)(delayed(geodesic_order)(X[np.isin(pid, d)], lab[np.isin(pid, d)]) for d in draws)
    fw = float(np.mean([o[0] == "floyd_warshall" for o in res]))
    bf = float(np.mean([o[0] == "bellman_ford_spfa" for o in res]))
    labp = np.random.default_rng(5).permutation(lab)
    resp = Parallel(n_jobs=6)(delayed(geodesic_order)(X[np.isin(pid, d)], labp[np.isin(pid, d)]) for d in draws)
    fwp = float(np.mean([o[0] == "floyd_warshall" for o in resp]))
    return {"share_FW_nearest": fw, "share_BF_nearest": bf, "n_draws": n_draws, "full_order": geodesic_order(X, lab),
            "placebo_share_FW_nearest_shuffled_labels": fwp, "placebo_failed_as_expected": bool(fwp < 0.9)}


def sham_test() -> dict:
    d = pd.read_json(EXP["exp1"] / "data" / "samples.jsonl", lines=True, dtype=False)
    d["lab"] = d["label"].astype(str).str.lower()
    d = d[~d["lab"].isin(["none", "no_code", "nan"])]
    syn = {"t1": {"astar_gbfs": "astar", "bibfs": "bibfs", "dijkstra": "unit_dijkstra"}, "t2": {}}
    shams = {"t1": ["ban:astar_gbfs", "ban:bibfs", "ban:dfs", "ban:dijkstra", "ban:iddfs"],
             "t2": ["ban:bf_spfa", "ban:bidijkstra", "ban:dial", "ban:floyd"]}

    def promotions(frame: pd.DataFrame) -> list:
        out = []
        for t, conds in shams.items():
            base = frame[(frame.task == t) & (frame.condition == "baseline")]
            for c in conds:
                ev = frame[(frame.task == t) & (frame.condition == c)]
                banned = c.split(":")[1]
                for s in sorted(set(frame[frame.task == t].lab) - {banned, "other"}):
                    k1, n1 = int((ev.lab == s).sum()), len(ev)
                    k0, n0 = int((base.lab == s).sum()), len(base)
                    if n1 == 0 or n0 == 0:
                        continue
                    diff = k1 / n1 - k0 / n0
                    p = fisher_exact([[k1, n1 - k1], [k0, n0 - k0]])[1]
                    if diff >= 0.10 and p < 0.05:
                        out.append((t, c, s, round(diff, 3)))
        return out

    real = promotions(d)
    # placebo: shuffle condition labels between each sham ban and the baseline rows of its task
    plc = d.copy()
    rng = np.random.default_rng(11)
    for t, conds in shams.items():
        m = (plc.task == t) & plc.condition.isin(conds + ["baseline"])
        plc.loc[m, "condition"] = rng.permutation(plc.loc[m, "condition"].values)
    fake = promotions(plc)
    return {"promotions": real, "n_promotions": len(real), "placebo_n_promotions": len(fake),
            "placebo_failed_as_expected": bool(len(fake) < len(real) or len(fake) == 0)}


def gate_test() -> dict:
    """Primary gate (avoidance >= 0.5 and >= 20 attempted non-banned) on the informative forecast events."""
    ev = [("exp1", "data/samples.jsonl", {"task": "t1", "condition": "ban:bfs"}, {"bfs"}),
          ("exp1", "data/samples.jsonl", {"task": "t2", "condition": "ban:dijkstra"}, {"dijkstra"}),
          ("exp1", "data/samples.jsonl", {"task": "t1", "condition": "succession:2"}, {"bfs", "dfs"}),
          ("exp1", "data/samples.jsonl", {"task": "t2", "condition": "succession:2"}, {"dijkstra", "bf_spfa"}),
          ("exp2", "data/samples_phaseC.jsonl", {"task": "t1", "condition": "ban:bfs"}, {"bfs"}),
          ("exp2", "data/samples_phaseC.jsonl", {"task": "t2", "condition": "ban:dijkstra"}, {"dijkstra"}),
          ("exp2", "data/samples_phaseC.jsonl", {"task": "t1", "condition": "ban:bfs+dfs"}, {"bfs", "dfs"}),
          ("exp2", "data/samples_phaseC.jsonl", {"task": "t1", "condition": "ban:bfs+dijkstra_unit"}, {"bfs", "dijkstra_unit"}),
          ("exp2", "data/samples_phaseC.jsonl", {"task": "t2", "condition": "ban:dijkstra+bellman_ford_spfa"}, {"dijkstra", "bellman_ford_spfa"}),
          ("exp4", "data/samples.jsonl", {"task": "T1", "condition": "ban:bfs"}, {"bfs"}),
          ("exp4", "data/samples.jsonl", {"task": "T2", "condition": "ban:dijkstra"}, {"dijkstra"}),
          ("exp4", "data/samples.jsonl", {"task": "T1", "condition": "succession:2"}, {"bfs", "dfs"}),
          ("exp4", "data/samples.jsonl", {"task": "T2", "condition": "succession:2"}, {"dijkstra", "bellman_ford_spfa"}),
          ("exp5", "runs/samples.jsonl", {"task": "t1", "condition": "ban:BFS", "arm": "instruct_chat"}, {"bfs"}),
          ("exp5", "runs/samples.jsonl", {"task": "t2", "condition": "ban:Dijkstra", "arm": "instruct_chat"}, {"dijkstra"})]
    rows = []
    cache = {}
    for e, rel, filt, banned in ev:
        key = (e, rel)
        if key not in cache:
            cache[key] = pd.read_json(EXP[e] / rel, lines=True, dtype=False)
        d = cache[key]
        for c, v in filt.items():
            d = d[d[c] == v]
        lab = d["label"].astype(str).str.lower()
        att = lab[~lab.isin(["none", "no_code", "unparseable", "nan"])]
        nb = att[~att.isin(banned)]
        avoid = len(nb) / len(att) if len(att) else 0.0
        rows.append({"event": f"{e}:{filt}", "attempted": len(att), "nonbanned": len(nb), "avoidance": avoid,
                     "gated": bool(avoid >= 0.5 and len(nb) >= 20)})
    return {"events": rows, "n_gated": sum(r["gated"] for r in rows)}


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("audit_extra")
    out = {}
    out["geometry"] = geometry_test()
    logger.info(f"geometry: {out['geometry']}")
    out["sham"] = sham_test()
    logger.info(f"sham: {out['sham']}")
    out["gate"] = gate_test()
    logger.info(f"gate: n_gated={out['gate']['n_gated']}")
    out["locus"] = locus_test()
    logger.info(f"locus: {out['locus']}")
    main_loc = json.loads((RES / "locus.json").read_text())["tasks"]["T2"]["contrasts"]["W"]["positions"]["k_pre"]
    main_geo = next(c for c in json.loads((RES / "geometry.json").read_text())["grid"]
                    if c["task"] == "t2" and c["layer"] == 24 and c["k"] == 10 and c["kind"] == "forced")
    main_tab = json.loads((RES / "tables.json").read_text())
    out["comparison"] = {
        "locus_T2_kpre_L8_BA": {"main": main_loc["BA"][0], "audit": out["locus"]["observed_BA"],
                                "match": abs(main_loc["BA"][0] - out["locus"]["observed_BA"]) <= 0.005},
        "locus_T2_kpre_L8_within_significant": {"main_p_within_cell": main_loc["p_within"][0], "audit_p_within": out["locus"]["p_within"],
                                                "match": (main_loc["p_within"][0] < 0.05) == (out["locus"]["p_within"] < 0.05)},
        "geo_T2_P_FW_nearest_L24_k10": {"main": main_geo["P_FW_nearest"], "audit": out["geometry"]["share_FW_nearest"],
                                        "match": abs(main_geo["P_FW_nearest"] - out["geometry"]["share_FW_nearest"]) <= 0.05},
        "n_sham_promotions": {"main": main_tab["sham"]["n_promotions"], "audit": out["sham"]["n_promotions"],
                              "match": main_tab["sham"]["n_promotions"] == out["sham"]["n_promotions"]},
        "n_gated_events_informative": {"main": main_tab["predict_gated"]["n_gated_primary"], "audit_all_informative_events_listed": out["gate"]["n_gated"],
                                       "match": main_tab["predict_gated"]["n_gated_primary"] == out["gate"]["n_gated"]}}
    out["all_match"] = all(v["match"] for v in out["comparison"].values())
    out["all_placebos_failed"] = all(out[k]["placebo_failed_as_expected"] for k in ("locus", "geometry", "sham"))
    jdump(clean(out), RES / "audit_extra.json")
    logger.info(f"audit_extra: all_match={out['all_match']} placebos_failed={out['all_placebos_failed']}")


if __name__ == "__main__":
    main()
