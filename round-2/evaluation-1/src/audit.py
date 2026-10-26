#!/usr/bin/env python3
"""Independent re-derivation of 20 headline numbers through separate code paths (pandas groupby on the raw JSONL,
sklearn pipelines for probe cells, networkx for geodesics, random.sample for rarefaction), plus placebos that must
fail. Compares against results/*.json and tables/*.csv written by the main scripts.

Usage: uv run audit.py
"""
from __future__ import annotations

import ast
import json
import math
import os
import random

os.environ.setdefault("OMP_NUM_THREADS", "4")

import networkx as nx
import numpy as np
import pandas as pd
from loguru import logger
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from common import EXP, HERE, RES, TAB, clean, jdump, setup_logging


def raw(e: str, rel: str) -> pd.DataFrame:
    return pd.read_json(EXP[e] / rel, lines=True, dtype=False)


def norm(s) -> str:
    return str(s).strip().lower()


def ok_pass(v) -> bool:
    return str(v).strip().lower() in ("true", "1")


T2_BF = {"bellman_ford_spfa", "bf_spfa"}
T1_DFS = {"dfs"}


def pooled_substitutes() -> dict:
    """Compliant (passed & label not banned) programs of the five modal-ban draws, by groupby."""
    out = {}
    specs = {"T2": [("exp1", "data/samples.jsonl", "condition", "ban:dijkstra", "t2", {"dijkstra"}),
                    ("exp2", "data/samples_phaseC.jsonl", "condition", "ban:dijkstra", "t2", {"dijkstra"}),
                    ("exp3", "generations/pools.jsonl", "arm", "G2", "T2", {"dijkstra"}),
                    ("exp4", "data/samples.jsonl", "condition", "ban:dijkstra", "T2", {"dijkstra"}),
                    ("exp5", "runs/samples.jsonl", "condition", "ban:Dijkstra", "t2", {"dijkstra"})],
             "T1": [("exp1", "data/samples.jsonl", "condition", "ban:bfs", "t1", {"bfs"}),
                    ("exp2", "data/samples_phaseC.jsonl", "condition", "ban:bfs", "t1", {"bfs"}),
                    ("exp3", "generations/pools.jsonl", "arm", "G2", "T1", {"bfs"}),
                    ("exp4", "data/samples.jsonl", "condition", "ban:bfs", "T1", {"bfs"}),
                    ("exp5", "runs/samples.jsonl", "condition", "ban:BFS", "t1", {"bfs"})]}
    for t, rows in specs.items():
        sub = T2_BF if t == "T2" else T1_DFS
        k = n = 0
        per = []
        for e, rel, col, val, task, banned in rows:
            d = raw(e, rel)
            d = d[(d["task"] == task) & (d[col] == val)]
            if e == "exp5":
                d = d[d["arm"] == "instruct_chat"]
            lab = d["label"].map(norm)
            comp = d[d["passed"].map(ok_pass) & ~lab.isin(banned) & ~lab.isin({"none", "no_code", "unparseable", "nan"})]
            kk = int(comp["label"].map(norm).isin(sub).sum())
            per.append(f"{kk}/{len(comp)}")
            k += kk
            n += len(comp)
        out[t] = {"substitute": k, "compliant": n, "per_draw": per}
    return out


def correct_label_count(e, rel, filt: dict, label_set: set, among: str = "correct") -> int:
    d = raw(e, rel)
    for c, v in filt.items():
        d = d[d[c] == v]
    if among == "correct":
        d = d[d["passed"].map(ok_pass)]
    return int(d["label"].map(norm).isin(label_set).sum())


def probe_cell_sklearn(task: str, pos: int, layer_idx: int, permute: bool = False, seed: int = 0) -> float:
    sd = EXP["exp3"] / "states"
    parts = sorted(sd.glob(f"{task}_part_*.npz"))
    X = np.concatenate([np.load(p)["X"][:, pos, layer_idx, :] for p in parts]).astype(np.float64)
    meta = json.loads((sd / f"{task}_meta.json").read_text())["rows"]
    sub, de = ("DFS", "BFS") if task == "T1" else ("bellman_ford_spfa", "dijkstra")
    idx = [i for i, r in enumerate(meta) if r["arm"] == "G2" and r["label"] in (sub, de)]
    y = np.array([int(meta[i]["label"] == sub) for i in idx])
    g = np.array([int(meta[i]["paraphrase_id"]) for i in idx])
    if permute:
        y = np.random.default_rng(seed).permutation(y)
    Xs = X[idx]
    pred = np.zeros(len(y))
    for gg in np.unique(g):
        tr, te = g != gg, g == gg
        # label-free scaler + PCA(64) fitted once on the outer-training rows (sklearn implementation)
        feat = make_pipeline(StandardScaler(), PCA(64, svd_solver="full")).fit(Xs[tr])
        Ztr, Zte = feat.transform(Xs[tr]), feat.transform(Xs[te])
        best, bestC = None, None
        for C in (0.01, 0.1, 1.0):
            oof = np.zeros(tr.sum())
            for itr, iva in GroupKFold(3).split(Ztr, y[tr], g[tr]):
                m = LogisticRegression(C=C, class_weight="balanced", max_iter=5000, tol=1e-8).fit(Ztr[itr], y[tr][itr])
                oof[iva] = m.predict_proba(Ztr[iva])[:, 1]
            ll = log_loss(y[tr], np.clip(oof, 1e-15, 1 - 1e-15), labels=[0, 1])
            if best is None or ll < best - 1e-12:
                best, bestC = ll, C
        m = LogisticRegression(C=bestC, class_weight="balanced", max_iter=5000, tol=1e-8).fit(Ztr, y[tr])
        pred[te] = m.predict_proba(Zte)[:, 1]
    return float(balanced_accuracy_score(y, pred >= 0.5))


def dim_auc(task: str, pos: int, layer_idx: int) -> float:
    sd = EXP["exp3"] / "states"
    X = np.concatenate([np.load(p)["X"][:, pos, layer_idx, :] for p in sorted(sd.glob(f"{task}_part_*.npz"))]).astype(np.float64)
    meta = json.loads((sd / f"{task}_meta.json").read_text())["rows"]
    sub, de = ("DFS", "BFS") if task == "T1" else ("bellman_ford_spfa", "dijkstra")
    df = pd.DataFrame([{"i": i, "y": int(r["label"] == sub), "g": r["paraphrase_id"]} for i, r in enumerate(meta)
                       if r["arm"] == "G2" and r["label"] in (sub, de)])
    s = pd.Series(0.0, index=df.index)
    for gg, te in df.groupby("g"):
        tr = df[df.g != gg]
        m1 = X[tr[tr.y == 1].i].mean(0)
        m0 = X[tr[tr.y == 0].i].mean(0)
        s[te.index] = (X[te.i] - (m1 + m0) / 2) @ (m1 - m0)
    return float(roc_auc_score(df.y, s))


def geodesic_nx(task: str, layer: int, mode_from: str, mode_to: str, permute: bool = False) -> float:
    index = [json.loads(l) for l in (EXP["exp2"] / "cache" / "hR_index.jsonl").read_text().splitlines() if l.strip()]
    H = np.load(EXP["exp2"] / "cache" / f"hR_layer{layer}.npy", mmap_mode="r")
    sel = [i for i, r in enumerate(index) if r["task"] == task and r["condition"].startswith("forced:")]
    X = np.asarray(H[sel], dtype=np.float64)
    lab = np.array([index[i]["condition"].split(":")[1] for i in sel])
    if permute:
        lab = np.random.default_rng(3).permutation(lab)
    mu = X.mean(0)
    pca = PCA(n_components=min(50, len(X) - 1), svd_solver="full").fit(X)
    kk = int(np.searchsorted(np.cumsum(pca.explained_variance_ratio_), 0.95) + 1)
    kk = max(2, min(kk, 50))
    P = (X - mu) @ pca.components_[:kk].T
    cats = sorted(set(lab))
    C = np.stack([X[lab == m].mean(0) for m in cats])
    Cp = (C - mu) @ pca.components_[:kk].T
    G = nx.Graph()
    dist, idx = NearestNeighbors(n_neighbors=11).fit(P).kneighbors(P)
    for i in range(len(P)):
        for d, j in zip(dist[i, 1:], idx[i, 1:]):
            G.add_edge(i, int(j), weight=float(d))
    dc, ic = NearestNeighbors(n_neighbors=10).fit(P).kneighbors(Cp)
    for a in range(len(cats)):
        for d, j in zip(dc[a], ic[a]):
            G.add_edge(("c", a), int(j), weight=float(d))
    sp = nx.single_source_dijkstra_path_length(G, ("c", cats.index(mode_from)), weight="weight")
    return float(sp[("c", cats.index(mode_to))])


def rarefied_hill_mc(labels: list[str], depth: int = 25, n: int = 4000, seed: int = 1) -> float:
    rnd = random.Random(seed)
    vals = []
    for _ in range(n):
        s = rnd.sample(labels, depth)
        c = pd.Series(s).value_counts().values / depth
        vals.append(math.exp(-(c * np.log(c)).sum()))
    return float(np.mean(vals))


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("audit")
    loc = json.loads((RES / "locus.json").read_text())
    geo = json.loads((RES / "geometry.json").read_text())
    tab = json.loads((RES / "tables.json").read_text())
    kt = pd.read_csv(TAB / "knob_table.csv")
    L = list(range(8, 29))
    rows = []

    def rec(name, main_val, audit_val, tol, source):
        ok = (main_val is not None and audit_val is not None and abs(float(main_val) - float(audit_val)) <= tol)
        rows.append({"name": name, "main": main_val, "audit": audit_val, "tol": tol, "match": bool(ok), "source": source})
        logger.info(f"{'OK ' if ok else 'XX '} {name}: main={main_val} audit={audit_val}")

    ps = pooled_substitutes()
    mb = tab["corrections"]["modal_ban_draws"]
    rec("T2 pooled BF_SPFA substitutes", mb["T2"]["pooled"]["substitute"], ps["T2"]["substitute"], 0, "groupby over 5 draws")
    rec("T2 pooled compliant", mb["T2"]["pooled"]["compliant"], ps["T2"]["compliant"], 0, "groupby over 5 draws")
    rec("T1 pooled DFS substitutes", mb["T1"]["pooled"]["substitute"], ps["T1"]["substitute"], 0, "groupby over 5 draws")
    rec("T1 pooled compliant", mb["T1"]["pooled"]["compliant"], ps["T1"]["compliant"], 0, "groupby over 5 draws")
    pt = pd.read_csv(TAB / "perturbation_table.csv")

    def ptc(e, t, c, lab, col="composition_correct"):
        r = pt[(pt.experiment == e) & (pt.task == t) & (pt.condition == c)]
        return json.loads(r[col].iloc[0]).get(lab, 0)

    rec("exp4 rand1 c=0.25 T2 correct BF_SPFA", ptc("exp4", "T2", "steer:rand1:c=0.25:L=18", "BF_SPFA"),
        correct_label_count("exp4", "data/samples.jsonl", {"task": "T2", "condition": "steer:rand1:c=0.25:L=18"}, T2_BF), 0, "exp4")
    rec("exp4 c=0 T2 correct BF_SPFA", ptc("exp4", "T2", "steer:dc:c=0:L=18", "BF_SPFA"),
        correct_label_count("exp4", "data/samples.jsonl", {"task": "T2", "condition": "steer:dc:c=0:L=18"}, T2_BF), 0, "exp4")
    rec("exp5 random2 T2 correct BF_SPFA", ptc("exp5", "T2", "steer:random2", "BF_SPFA"),
        correct_label_count("exp5", "runs/samples.jsonl", {"task": "t2", "arm": "steer:random2"}, T2_BF), 0, "exp5")
    rec("exp6 enumeration T2 BF_SPFA written", ptc("exp6", "T2", "A3|instr_enumerate", "BF_SPFA", "composition_attempted"),
        correct_label_count("exp6", "results/samples.jsonl", {"task": "T2", "condition": "instr_enumerate"}, T2_BF, "all"), 0, "exp6")
    rec("exp6 enumeration T2 BF_SPFA correct", ptc("exp6", "T2", "A3|instr_enumerate", "BF_SPFA"),
        correct_label_count("exp6", "results/samples.jsonl", {"task": "T2", "condition": "instr_enumerate"}, T2_BF), 0, "exp6")
    d1 = raw("exp1", "data/samples.jsonl")
    dfs = d1[(d1.task == "t1") & (d1.label.map(norm) == "dfs")]
    rec("exp1 failing DFS programs", tab["missing_outputs"]["exp1_dfs_failures"]["n_failing"], int((~dfs.passed.map(ok_pass)).sum()), 0, "exp1")
    fl = d1[(d1.task == "t2") & (d1.condition == "ban:floyd")]
    flc = fl[~fl.label.map(norm).isin({"none", "no_code", "nan"})]
    srow = next(x for x in tab["sham"]["rows"] if x["event"] == "ban:floyd" and x["survivor"] == "BF_SPFA")
    rec("sham ban:floyd -> BF_SPFA share", srow["share_ban"], float(flc.label.map(norm).isin({"bf_spfa"}).mean()), 0.005, "exp1")
    d6 = raw("exp6", "results/samples.jsonl")
    def share_correct(cond, arm, lab):
        x = d6[(d6.task == "T2") & (d6.condition == cond) & (d6.arm == arm) & d6.passed.map(ok_pass)]
        return float((x.label.map(norm) == lab).mean())
    shift = 100 * (share_correct("seed_semantic", "A2", "bellman_ford_spfa") - share_correct("baseline", "A0", "bellman_ford_spfa"))
    rec("T2 semantic seed BF_SPFA shift among correct (pts)", tab["seeds"]["behaviour"]["T2|seed_semantic"]["BF_SPFA"]["diff_pts_among_correct"], shift, 0.01, "exp6")
    # probe cells through sklearn pipelines (PCA refit inside inner folds: an independent path, tolerance 0.05)
    W2 = loc["tasks"]["T2"]["contrasts"]["W"]["positions"]
    W1 = loc["tasks"]["T1"]["contrasts"]["W"]["positions"]
    for task, W, p, pi in (("T2", W2, "k_pre", 6), ("T1", W1, "R", 0), ("T2", W2, "k8", 1)):
        Ls = W[p]["L_star"]
        rec(f"locus {task} W {p} L{Ls} BA (sklearn pipeline)", W[p]["BA"][L.index(Ls)], probe_cell_sklearn(task, pi, L.index(Ls)), 0.05,
            "exp3/states + sklearn StandardScaler/PCA(64) per outer fold + LogisticRegression(lbfgs) inner GroupKFold(3)")
    rec("DiM AUC T2 k8 at L*", W2["k8"]["DiM_AUC"][L.index(W2["k8"]["L_star"])], dim_auc("T2", 1, L.index(W2["k8"]["L_star"])), 0.005, "numpy/pandas path")
    t2row = geo["reproduce"]["t2"]["recomputed_row0"]
    rec("geodesic T2 L24 k10 DIJKSTRA->FW (networkx)", t2row[3], geodesic_nx("t2", 24, "dijkstra", "floyd_warshall"), 0.05, "exp2 cache")
    t1row = geo["reproduce"]["t1"]["recomputed_row0"]
    rec("geodesic T1 L27 k10 BFS->DFS (networkx)", t1row[1], geodesic_nx("t1", 27, "bfs", "dfs"), 0.05, "exp2 cache")
    r = kt[(kt.experiment == "exp6") & (kt.task == "T2") & (kt.condition == "A2|seed_semantic")].iloc[0]
    x = d6[(d6.task == "T2") & (d6.condition == "seed_semantic") & d6.passed.map(ok_pass)]
    labs = [l for l in x.label.map(norm)]
    rec("T2 semantic seed rarefied Hill-1 (random.sample MC)", r.hill1_rarefied, rarefied_hill_mc(labs), 0.02, "exp6")
    cv = loc["tasks"]["T2"]["text"]["curve"]["4"]["BA_text"]
    pools = raw("exp3", "generations/pools.jsonl")
    g2 = pools[(pools.task == "T2") & (pools.arm == "G2") & pools.label.isin(["bellman_ford_spfa", "dijkstra"])]
    tok3 = g2.gen_token_ids.map(lambda s: (ast.literal_eval(s) if isinstance(s, str) else s)[3])
    # the fourth generated token alone (rule: majority class per token value, LOPO by paraphrase)
    yy = (g2.label == "bellman_ford_spfa").astype(int).values
    gg = g2.paraphrase_id.astype(int).values
    pr = np.zeros(len(yy))
    for p_ in np.unique(gg):
        tr = gg != p_
        tab_ = pd.crosstab(tok3[tr].values, yy[tr])
        maj = {k: int(tab_.loc[k].idxmax()) if k in tab_.index else 1 for k in tok3[~tr].values}
        w1 = len(yy[tr]) / (2 * max(yy[tr].sum(), 1))
        w0 = len(yy[tr]) / (2 * max((1 - yy[tr]).sum(), 1))
        for i in np.where(~tr)[0]:
            k = tok3.values[i]
            if k in tab_.index:
                c0 = tab_.loc[k].get(0, 0) * w0
                c1 = tab_.loc[k].get(1, 0) * w1
                pr[i] = int(c1 > c0)
            else:
                pr[i] = 1
    rec("text-locus T2 k=4 BA (token-3 balanced rule)", cv, float(balanced_accuracy_score(yy, pr)), 0.03, "exp3/generations/pools.jsonl")
    # placebos (must fail)
    plc = []
    bp = probe_cell_sklearn("T2", 6, L.index(W2["k_pre"]["L_star"]), permute=True, seed=5)
    plc.append({"name": "locus T2 k_pre with permuted labels", "value": bp, "must_fail_rule": "BA < 0.65", "failed_as_expected": bool(bp < 0.65)})
    base = raw("exp1", "data/samples.jsonl")
    b = base[(base.task == "t2") & (base.condition == "baseline") & base.passed.map(ok_pass)]
    sh = float(b.label.map(norm).isin(T2_BF).mean())
    plc.append({"name": "BF_SPFA share among compliant T2 programs when the baseline condition stands in for the ban",
                "value": sh, "must_fail_rule": "share < 0.5 (vs 1.0 under the ban)", "failed_as_expected": bool(sh < 0.5)})
    gp = geodesic_nx("t2", 24, "dijkstra", "floyd_warshall", permute=True)
    plc.append({"name": "T2 L24 DIJKSTRA->FW geodesic with shuffled mode labels", "value": gp,
                "must_fail_rule": "not within 0.05 of the real 25.49", "failed_as_expected": bool(abs(gp - t2row[3]) > 0.05)})
    n_ok = sum(r_["match"] for r_ in rows)
    out = {"n_rederived": len(rows), "n_match": n_ok, "rederivations": rows, "placebos": plc,
           "all_placebos_failed": all(p["failed_as_expected"] for p in plc)}
    jdump(clean(out), RES / "audit.json")
    logger.info(f"audit: {n_ok}/{len(rows)} re-derived numbers match; placebos failed as expected: {out['all_placebos_failed']}")


if __name__ == "__main__":
    main()
