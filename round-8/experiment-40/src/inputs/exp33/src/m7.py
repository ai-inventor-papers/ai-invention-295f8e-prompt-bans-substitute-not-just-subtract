#!/usr/bin/env python3
"""STEP 11 M (T2, no generation): where prompts sit in the fitted plan subspace (R_16 coordinates, residual units).

z(prompt) = mean over spec positions of R_16 h at the site's middle block (cache/m_states_T2.npz, MAIN_LY map).
Points: 60 twins, 25 padding twins, P0, 25 forced (5 families x 5 modes), 5 bans + 20 sham bans, 10 leave-one-survivor
multi-name bans, 2 random seeds, the semantic seed, 2 instructions. Forced-Y centroids (5 family points each) are
sized and coloured by implemented count under the twin (this artifact's Stage 0 twin cell), under Qwen3-8B-Base on
identical ids (exp24 samples, correct programs) and under the knobs (all correct programs of this artifact's edit arms
+ iteration 4's random directions re-run in bf16, exp29 labels).
Mean-answer test: D = ||z - zbar_default|| against the paraphrase null (60 twins + 5 default padding twins + P0) and the
signed coordinate along unit(c_runner-up - c_default). Geometry: the DAS-1 x DAS-2 plane, metric MDS (stress-1) and
Isomap geodesics (kNN 5, 10, 15) of the 16-d points. Top-k placement: leave-one-survivor bans vs centroids.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from cfg import ROOT, read_json, read_jsonl
from cfg7 import CATALOGUE7, DEFAULT7, LABELS7, results7

# extracts copied into inputs/ at run time (T2 rows of exp24's Qwen3-8B-Base samples and exp29's random-direction
# labels; exp9's leave-one-survivor behaviour table)
EXP9_LOS = ROOT / "inputs" / "exp9_los.json"


def implemented_counts(task: str) -> dict[str, dict[str, int]]:
    cat = CATALOGUE7[task]
    out = {}
    tw = [r for r in read_jsonl(LABELS7) if r["task"] == task and r["arm"] == "TWIN" and r.get("passed")]
    out["twin"] = {a: sum(r["label"] == a for r in tw) for a in cat}
    inp = ROOT / "inputs" / "exp24_T2_base_samples.jsonl"
    rows = read_jsonl(inp) if inp.exists() else []
    b = [r for r in rows if r["task"] == task and r["arm"] == "BASE_CHAT" and r.get("passed")]
    out["base_model"] = {a: sum(r["label"] == a for r in b) for a in cat}
    knobs = [r for r in read_jsonl(LABELS7) if r["task"] == task and r.get("stage") in ("gen", "r") and r.get("passed")
             and not str(r["arm"]).startswith(("BASE", "PADBASE"))]
    inp29 = ROOT / "inputs" / "exp29_T2_labels.jsonl"
    k29 = [r for r in read_jsonl(inp29) if r["task"] == task and r.get("passed")] if inp29.exists() else []
    out["knobs"] = {a: sum(r["label"] == a for r in knobs) + sum(r["label"] == a for r in k29) for a in cat}
    out["knobs_this_artifact"] = {a: sum(r["label"] == a for r in knobs) for a in cat}
    out["knobs_exp29_random_directions"] = {a: sum(r["label"] == a for r in k29) for a in cat}
    return out


def load_points(task: str) -> tuple[list[str], np.ndarray, np.ndarray]:
    z = np.load(ROOT / "cache" / f"m_states_{task}.npz")
    return [str(k) for k in z["keys"]], z["z"].astype(np.float64), z["mean"].astype(np.float64)


def geodesic(Z: np.ndarray, k: int) -> np.ndarray:
    from scipy.sparse.csgraph import shortest_path
    from sklearn.neighbors import kneighbors_graph
    G = kneighbors_graph(Z, n_neighbors=k, mode="distance", include_self=False)
    G = G.maximum(G.T)
    return shortest_path(G, method="D", directed=False)


def analyse(task: str = "T2") -> dict[str, Any]:
    from sklearn.manifold import MDS, Isomap
    keys, Z, Mfull = load_points(task)
    kind = [k.split("|")[1] for k in keys]
    meta = {k: r for k, r in ((r["key"], r) for r in read_jsonl(ROOT / "prompts" / "prompts7.jsonl"))}
    D = DEFAULT7[task]
    cat = CATALOGUE7[task]
    idx = {k: i for i, k in enumerate(keys)}
    null_keys = [k for k in keys if meta[k]["kind"] == "twin"] + \
        [k for k in keys if meta[k]["kind"] == "padtwin" and meta[k]["Y"] == D] + \
        [k for k in keys if meta[k]["kind"] == "p0"]
    Zn = Z[[idx[k] for k in null_keys]]
    zbar = Zn.mean(0)
    dnull = np.linalg.norm(Zn - zbar, axis=1)
    cent = {}
    for Y in cat:
        ks = [k for k in keys if meta[k]["kind"] == "forced" and meta[k]["Y"] == Y]
        cent[Y] = Z[[idx[k] for k in ks]].mean(0)
    T = read_json(results7(f"targets_{task}.json"))
    runner = (T["landing"] or T["kept_Y"])[0]
    u = cent[runner] - cent[D]
    u = u / np.linalg.norm(u)
    probes = {}
    for k in keys:
        if meta[k]["kind"] in ("seed_rand1", "seed_rand2", "seed_sem", "instr_new", "instr_novel", "ban", "p0") or \
                (meta[k]["kind"] == "ban" and meta[k]["w"] == "W1"):
            d = float(np.linalg.norm(Z[idx[k]] - zbar))
            probes[k] = {"kind": meta[k]["kind"], "D": d, "null_percentile": float((dnull < d).mean() * 100),
                         "inside_null_95": bool(d <= np.percentile(dnull, 95)),
                         "coord_along_runnerup": float((Z[idx[k]] - zbar) @ u)}
    null_coord = (Zn - zbar) @ u
    # centroid geometry
    cent_coord = {Y: float((cent[Y] - zbar) @ u) for Y in cat}
    # MDS / Isomap of 16-d points
    mds = MDS(n_components=2, n_init=4, random_state=0, dissimilarity="euclidean", normalized_stress="auto")
    Y2 = mds.fit_transform(Z)
    from scipy.spatial.distance import pdist, squareform
    Dz = squareform(pdist(Z))
    D2 = squareform(pdist(Y2))
    stress1 = float(np.sqrt(((Dz - D2) ** 2).sum() / (Dz ** 2).sum()))
    iso = Isomap(n_neighbors=10, n_components=2).fit_transform(Z)
    geo = {}
    for kk in (5, 10, 15):
        G = geodesic(Z, kk)
        tab = {}
        for a in cat:
            ia = [idx[k] for k in keys if meta[k]["kind"] == "forced" and meta[k]["Y"] == a]
            row = {}
            for b in cat:
                ib = [idx[k] for k in keys if meta[k]["kind"] == "forced" and meta[k]["Y"] == b]
                vals = G[np.ix_(ia, ib)]
                row[b] = float(np.nanmean(np.where(np.isfinite(vals), vals, np.nan)))
            tab[a] = row
        # leave-one-survivor placement: rank of the survivor's mean geodesic distance among the 5 algorithms
        place = []
        for k in keys:
            if meta[k]["kind"] != "multiban":
                continue
            dist = {}
            for a in cat:
                ia = [idx[x] for x in keys if meta[x]["kind"] == "forced" and meta[x]["Y"] == a]
                v = G[idx[k], ia]
                dist[a] = float(np.mean(v[np.isfinite(v)])) if np.isfinite(v).any() else float("inf")
            order = sorted(cat, key=lambda a: dist[a])
            place.append({"key": k, "survivor": meta[k]["Y"], "w": meta[k]["w"],
                          "survivor_rank": order.index(meta[k]["Y"]) + 1, "nearest": order[0], "dist": dist})
        ranks = [p["survivor_rank"] for p in place]
        rng = np.random.default_rng(0)
        null = [np.mean(rng.integers(1, len(cat) + 1, len(ranks))) for _ in range(1000)]
        geo[kk] = {"centroid_geodesic_table": tab, "los_placement": place,
                   "mean_survivor_rank": float(np.mean(ranks)) if ranks else None,
                   "p_rank_le_observed": float(np.mean(np.array(null) <= np.mean(ranks))) if ranks else None,
                   "n_unreachable": int((~np.isfinite(G)).sum())}
    los = read_json(EXP9_LOS) if EXP9_LOS.exists() else {}
    beh = {s: {"compliant_share": v.get("compliant_share"), "will_attempted_share": v.get("will_attempted_share"),
               "banned_share_by_mechanism": v.get("banned_share_by_mechanism")} for s, v in los.items()}
    counts = implemented_counts(task)
    out = {"task": task, "n_points": len(keys), "zbar_default_norm": float(np.linalg.norm(zbar)),
           "paraphrase_null": {"n": len(null_keys), "D_median": float(np.median(dnull)),
                               "D_95": float(np.percentile(dnull, 95)), "coord_sd": float(np.std(null_coord))},
           "runner_up": runner, "probes": probes, "centroid_coord_along_runnerup": cent_coord,
           "mds_stress1": stress1, "geodesic": geo, "exp9_los_behaviour": beh, "implemented_counts": counts,
           "coords": {"keys": keys, "kind": [meta[k]["kind"] for k in keys], "Y": [meta[k]["Y"] for k in keys],
                      "das12": Z[:, :2].tolist(), "mds": Y2.tolist(), "isomap": iso.tolist(),
                      "centroids_das12": {Y: cent[Y][:2].tolist() for Y in cat}, "zbar_das12": zbar[:2].tolist()}}
    return out
