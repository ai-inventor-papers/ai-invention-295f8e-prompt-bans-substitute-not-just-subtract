#!/usr/bin/env python3
"""Stages 4-5: G1 (RSA of the factorial cell map) and G2 (placement of survivors / covert / PROBE programs) per model,
using the frozen src/analysis_g2.py. Usage: python src/run_analysis.py <8b|32b> [--boot N] [--g1-only|--g2-only]"""

from __future__ import annotations

import ast
import io
import keyword
import multiprocessing as mp
import sys
import time
import tokenize
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

import analysis_g2 as A  # noqa: E402
import geometry  # noqa: E402
import landing  # noqa: E402
from accept import jaccard, shingles  # noqa: E402
from common import read_json, read_jsonl, utc_now  # noqa: E402
from tpg2 import (BANNED_DISC, DATA, E46_STATES, IN44, K_PRIMARY, K_SECOND, L_STAR, LOGS, RESULTS,  # noqa: E402
                  STATES, cell_dc, write_json)

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(LOGS / "analysis.log"), rotation="30 MB", level="DEBUG")
B5 = ["bfs", "dfs", "iddfs", "astar", "gbfs"]
NB5 = ["dijkstra_unit", "idastar", "bibfs", "jps", "biastar"]
BUILTINS = set(dir(__builtins__)) if isinstance(__builtins__, dict) is False else set(__builtins__)
MODS = {"heapq", "collections", "deque", "random", "bisect", "math", "itertools", "queue", "heappush", "heappop",
        "insort", "defaultdict"}


# ---------------------------------------------------------------------------------------------- loading
def load_all(tag: str) -> dict[str, Any]:
    fr = read_json(DATA / "frames.json")
    z = np.load(STATES / f"tpg2_{tag}.npz")
    ids = [str(x) for x in z["ids"]]
    pos = {u: i for i, u in enumerate(ids)}
    blocks = [int(b) for b in z["blocks"]]
    L = L_STAR[tag]
    meta = {m["id"]: m for m in read_json(RESULTS / f"states_{tag}.json")["meta"]}
    ze = np.load(E46_STATES / f"mcode_{tag}.npz")
    ekeys = {str(k): i for i, k in enumerate(ze["keys"])}
    eblocks = [int(b) for b in ze["blocks"]]
    eread = [str(r) for r in ze["readouts"]]
    return {"fr": fr, "R": z["R"], "pos": pos, "blocks": blocks, "L": L, "meta": meta, "ze": ze, "ekeys": ekeys,
            "eblocks": eblocks, "eread": eread, "readouts": [str(r) for r in z["readouts"]]}


def X_new(D: dict[str, Any], ids: list[str], readout: str = "R1", block: int | None = None) -> np.ndarray:
    b = D["blocks"].index(D["L"] if block is None else block)
    r = D["readouts"].index(readout)
    return np.stack([D["R"][D["pos"][u], r, b].astype(np.float64) for u in ids])


def X_e46(D: dict[str, Any], keys: list[str], readout: str = "R1", block: int | None = None) -> np.ndarray:
    b = D["eblocks"].index(D["L"] if block is None else block)
    r = D["eread"].index(readout)
    return np.stack([D["ze"]["R"][D["ekeys"][k], r, b].astype(np.float64) for k in keys])


# ---------------------------------------------------------------------------------------------- baselines
def norm_tokens(code: str) -> list[str]:
    out = []
    prev = None
    try:
        for t in tokenize.generate_tokens(io.StringIO(code).readline):
            if t.type == tokenize.NAME:
                s = t.string
                if keyword.iskeyword(s) or s in BUILTINS or s in MODS or prev == ".":
                    out.append(s)
                else:
                    out.append("ID")
            elif t.type == tokenize.NUMBER:
                out.append("NUM")
            elif t.type == tokenize.STRING:
                out.append("STR")
            elif t.type == tokenize.OP:
                out.append(t.string)
            prev = t.string
    except (tokenize.TokenError, IndentationError):
        pass
    return out


def baseline_reps(codes: list[str]) -> dict[str, np.ndarray]:
    from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
    from sklearn.preprocessing import normalize

    toks = [" ".join(norm_tokens(c)) for c in codes]
    tf = TfidfVectorizer(token_pattern=r"\S+", ngram_range=(1, 2), lowercase=False, min_df=2).fit_transform(toks)
    seqs = []
    for c in codes:
        s = [type(n).__name__ for n in ast.walk(ast.parse(c))]
        seqs.append(" ".join("_".join(s[i:i + 4]) for i in range(len(s) - 3)))
    cv = CountVectorizer(token_pattern=r"\S+", lowercase=False, min_df=2).fit_transform(seqs)
    return {"tfidf": tf.toarray().astype(np.float64), "astngram": normalize(cv.astype(np.float64)).toarray()}


def jaccard_matrix(codes: list[str]) -> np.ndarray:
    sh = [shingles(c) for c in codes]
    n = len(sh)
    J = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            J[i, j] = J[j, i] = 1 - jaccard(sh[i], sh[j])
    return J


# ---------------------------------------------------------------------------------------------- G1
def g1(tag: str, D: dict[str, Any], n_boot: int) -> dict[str, Any]:
    fr = D["fr"]
    cells = [c["cell"] for c in fr["g1_cells"]]
    disc = {c["cell"]: c["disc"] for c in fr["g1_cells"]}
    cont = {c["cell"]: c["cont"] for c in fr["g1_cells"]}
    fact = [f for f in fr["factorial"] if f["cell"] in cells]
    ids = [f["id"] for f in fact]
    labels = np.array([f["cell"] for f in fact])
    items = {it["id"]: it for it in read_json(DATA / "state_items.json")["items"]}
    codes = [items[u]["scrubbed"] for u in ids]
    lens = np.array([D["meta"][u]["n_code_tokens"] for u in ids], dtype=float)
    J = jaccard_matrix(codes)
    X = X_new(D, ids)
    reps = {"model": X, "block0": X_new(D, ids, block=0), **baseline_reps(codes)}
    out: dict[str, Any] = {"model": tag, "block": D["L"], "readout": "R1", "k": K_PRIMARY, "cells": cells,
                           "n_per_cell": dict(Counter(labels.tolist())), "n_programs": len(ids)}
    t0 = time.time()
    pt = {}
    for name, R in reps.items():
        p = A.g1_point(R, labels, cells, disc, cont, J, lens, K_PRIMARY)
        pt[name] = p
        out[f"point_{name}"] = {k: v for k, v in p.items() if k in ("rho_d", "rho_c", "rho_d_full", "rho_c_full",
                                                                 "rho_surf_partial", "tau_a", "graph")}
    P = pt["model"]
    out["cell_rdm"] = P["D"].tolist()
    out["model_rdms"] = {"D_disc": P["Dd"].tolist(), "D_cont": P["Dc"].tolist(), "D_surf": P["Ds"].tolist(),
                         "D_len": P["Dl"].tolist(), "D_disp": P["Dp"].tolist()}
    # restricted permutations
    y = A.upper(P["D"])
    perms_d, ex_d, tot_d = A.restricted_label_perms(cells, cont, disc)
    perms_c, ex_c, tot_c = A.restricted_label_perms(cells, disc, cont)
    out["perm"] = {}
    for name in reps:
        yy = A.upper(pt[name]["D"])
        nd = A.perm_partial(yy, perms_d, [A.upper(P["Dc"])], len(cells))
        nc = A.perm_partial(yy, perms_c, [A.upper(P["Dd"])], len(cells))
        ndf = A.perm_partial(yy, perms_d, [A.upper(P["Dc"]), A.upper(P["Ds"]), A.upper(P["Dl"]),
                                           A.upper(pt[name]["Dp"])], len(cells))
        out["perm"][name] = {"rho_d": A.perm_p(pt[name]["rho_d"], nd), "rho_c": A.perm_p(pt[name]["rho_c"], nc),
                             "rho_d_full": A.perm_p(pt[name]["rho_d_full"], ndf)}
    out["perm_scheme"] = {"rho_d": {"exact": ex_d, "n": int(len(perms_d)), "total": tot_d,
                                    "scheme": "discipline labels permuted among cells within each container"},
                          "rho_c": {"exact": ex_c, "n": int(len(perms_c)), "total": tot_c,
                                    "scheme": "container labels permuted among cells within each discipline"}}
    # naive full-matrix permutation (demonstration)
    rng = np.random.default_rng(0)
    base = np.array([sorted(set(disc.values())).index(disc[c]) for c in cells])
    naive = np.stack([base[rng.permutation(len(cells))] for _ in range(10000)]).astype(np.int16)
    out["perm_naive_full_matrix_rho_d"] = A.perm_p(P["rho_d"], A.perm_partial(y, naive, [A.upper(P["Dc"])], len(cells)))
    logger.info(f"[{tag}] G1 point rho_d {P['rho_d']:.3f} rho_c {P['rho_c']:.3f} full {P['rho_d_full']:.3f}; "
                f"perm p {out['perm']['model']['rho_d']['p_greater']:.4f} ({time.time() - t0:.0f}s)")
    # bootstrap (graph rebuilt in each resample, all representations on the same resample)
    seeds = list(range(n_boot))
    chunks = [seeds[i::6] for i in range(6)]
    with ProcessPoolExecutor(max_workers=6, mp_context=mp.get_context("spawn")) as ex:
        res = list(ex.map(A.g1_boot_chunk, [(reps, cells, disc, cont, labels, J, lens, K_PRIMARY, ch) for ch in chunks]))
    boot = [r for ch in res for r in ch]
    bs = {k: np.array([b[k] for b in boot], dtype=float) for k in boot[0] if k != "seed"}

    def ci(v: np.ndarray) -> list[float]:
        v = v[np.isfinite(v)]
        return np.percentile(v, [2.5, 97.5]).tolist() if len(v) else [float("nan")] * 2

    out["bootstrap"] = {"B": len(boot), "graph_rebuilt": True}
    for name in reps:
        out["bootstrap"][name] = {k.split(":")[1]: {"ci95": ci(v), "mean": float(np.nanmean(v))}
                                  for k, v in bs.items() if k.startswith(name + ":")}
    dd = bs["model:rho_d"] - bs["model:rho_c"]
    out["bootstrap"]["model_rho_d_minus_rho_c"] = {"ci95": ci(dd), "P_rho_d_gt_rho_c": float(np.mean(dd > 0))}
    out["selectivity"] = {}
    for name in ("block0", "tfidf", "astngram"):
        sd = bs["model:rho_d"] - bs[f"{name}:rho_d"]
        out["selectivity"][name] = {"point": P["rho_d"] - pt[name]["rho_d"], "ci95": ci(sd),
                                    "P_gt0": float(np.mean(sd > 0))}
    logger.info(f"[{tag}] bootstrap done ({len(boot)}): rho_d CI {out['bootstrap']['model']['rho_d']['ci95']}, "
                f"P(rho_d > rho_c) {out['bootstrap']['model_rho_d_minus_rho_c']['P_rho_d_gt_rho_c']:.3f}")
    # noise ceiling, commonality
    out["noise_ceiling"] = A.noise_ceiling(X, labels, cells, K_PRIMARY, n_split=100)
    out["commonality"] = A.commonality(P["D"], P["Dd"], P["Dc"], P["Ds"], P["Dl"])
    # sensitivities
    sens: dict[str, Any] = {}

    def run_var(name: str, Xv: np.ndarray, lab: np.ndarray, cl: list[str], k: int = K_PRIMARY,
                Dfun: Any = None) -> None:
        ds = {c: cell_dc(c)[0] if c != "PROBE" else "LEV" for c in cl}
        cs = {c: cell_dc(c)[1] if c != "PROBE" else "DEQ" for c in cl}
        idx = [np.where(lab == c)[0] for c in cl]
        if Dfun is None:
            Dm, diag, _ = A.geo_rdm(Xv, lab, cl, k)
        else:
            Dm, diag = Dfun(Xv, lab, cl), np.zeros(len(cl))
        Dd, Dc = A.cell_model_rdms(cl, ds, cs)
        sel = np.concatenate(idx)
        st = {"rho_d": A.partial_spearman(A.upper(Dm), A.upper(Dd), [A.upper(Dc)]),
              "rho_c": A.partial_spearman(A.upper(Dm), A.upper(Dc), [A.upper(Dd)])}
        pd_, _, _ = A.restricted_label_perms(cl, cs, ds)
        st["p_rho_d"] = A.perm_p(st["rho_d"], A.perm_partial(A.upper(Dm), pd_, [A.upper(Dc)], len(cl)))["p_greater"]
        st["n_cells"] = len(cl)
        st["n_programs"] = int(len(sel))
        sens[name] = st
        logger.info(f"[{tag}] sensitivity {name}: rho_d {st['rho_d']:.3f} rho_c {st['rho_c']:.3f} p {st['p_rho_d']:.4f}")

    run_var("k10", X, labels, cells, k=K_SECOND)
    run_var("euclid_centroid", X, labels, cells, Dfun=A.euclid_centroid_rdm)
    run_var("crossval_euclid_centroid", X, labels, cells, Dfun=lambda a, b, c: A.crossval_centroid_rdm(a, b, c, 100))
    for ro in ("R1g", "R2"):
        run_var(f"readout_{ro}", X_new(D, ids, readout=ro), labels, cells)
    for b in D["blocks"]:
        if b not in (0, D["L"]):
            run_var(f"block_{b}", X_new(D, ids, block=b), labels, cells)
    keep = np.array([not f["reassigned"] for f in fact])
    run_var("exclude_reassigned", X[keep], labels[keep], [c for c in cells if (labels[keep] == c).sum() >= 5])
    keep2 = np.array([not f.get("disputed") for f in fact])
    run_var("exclude_disputed", X[keep2], labels[keep2], [c for c in cells if (labels[keep2] == c).sum() >= 5])
    probe = [f for f in fr["factorial"] if f["cell"] == "PROBE"]
    if probe:
        Xp = np.concatenate([X, X_new(D, [f["id"] for f in probe])])
        lp = np.concatenate([labels, np.array(["PROBE"] * len(probe))])
        run_var("add_PROBE_cell", Xp, lp, cells + ["PROBE"])
    # frame F1 sensitivity: factorial cells' RDM inside the bigger graph (factorial + F0 catalogue)
    f0ids, f0X, _ = f0_frame(D)
    XF = np.concatenate([X, f0X])
    lF = np.concatenate([labels, np.array(["__f0__"] * len(f0X))])
    geoF, _ = geometry.geodesics(XF, K_PRIMARY)
    DmF = geometry.class_matrix(geoF, lF, cells)
    Dd, Dc = A.cell_model_rdms(cells, disc, cont)
    sens["frame_F1"] = {"rho_d": A.partial_spearman(A.upper(DmF), A.upper(Dd), [A.upper(Dc)]),
                        "rho_c": A.partial_spearman(A.upper(DmF), A.upper(Dc), [A.upper(Dd)])}
    sens["frame_F1"]["p_rho_d"] = A.perm_p(sens["frame_F1"]["rho_d"], A.perm_partial(A.upper(DmF), perms_d, [A.upper(Dc)],
                                                                                      len(cells)))["p_greater"]
    # program-level RDM (all program pairs; restricted cell-level permutation, 2,000 sampled)
    geoP = P["geo"]
    iu = np.triu_indices(len(labels), 1)
    yP = geoP[iu]
    ci_ = np.array([cells.index(c) for c in labels])
    dlab = np.array([sorted(set(disc.values())).index(disc[c]) for c in cells])
    clab = np.array([sorted(set(cont.values())).index(cont[c]) for c in cells])
    dP = (dlab[ci_][iu[0]] != dlab[ci_][iu[1]]).astype(float)
    cP = (clab[ci_][iu[0]] != clab[ci_][iu[1]]).astype(float)
    rpl = A.partial_spearman(yP, dP, [cP])
    rng = np.random.default_rng(1)
    sub = perms_d[rng.choice(len(perms_d), size=min(2000, len(perms_d)), replace=False)]
    null = []
    for prm in sub:
        dl = prm[ci_]
        null.append(A.partial_spearman(yP, (dl[iu[0]] != dl[iu[1]]).astype(float), [cP]))
    sens["program_level"] = {"rho_d": rpl, "rho_c": A.partial_spearman(yP, cP, [dP]),
                             "p_rho_d": A.perm_p(rpl, np.array(null))["p_greater"], "n_perm": len(null),
                             "n_pairs": int(len(yP))}
    out["sensitivities"] = sens
    out["seconds"] = round(time.time() - t0, 1)
    out["_reps_points"] = {k: {kk: vv for kk, vv in v.items() if kk in ("rho_d", "rho_c")} for k, v in pt.items()}
    return out


# ---------------------------------------------------------------------------------------------- frames for G2
def f0_frame(D: dict[str, Any]) -> tuple[list[str], np.ndarray, np.ndarray]:
    fr = D["fr"]
    classes = fr["f0_classes"]
    prim = [p for p in fr["primary"] if p["algorithm"] in classes]
    tops = [t for t in fr["topups"] if t["algorithm"] in classes]
    ids = [p["id"] for p in prim] + [t["id"] for t in tops]
    X = np.concatenate([X_e46(D, [p["e46_key"] for p in prim]), X_new(D, [t["id"] for t in tops])]) if tops else \
        X_e46(D, [p["e46_key"] for p in prim])
    lab = np.array([p["algorithm"] for p in prim] + [t["algorithm"] for t in tops])
    return ids, X, lab


def build_frames(D: dict[str, Any]) -> dict[str, Any]:
    fr = D["fr"]
    cells = [c["cell"] for c in fr["g1_cells"]]
    f0ids, f0X, f0lab = f0_frame(D)
    pm = {p["id"]: p for p in fr["primary"]}
    tp = {t["id"]: t for t in fr["topups"]}
    f0disc = np.array([(pm.get(u) or tp.get(u))["disc"] or "OTHER" for u in f0ids])
    f0cont = np.array([(pm.get(u) or tp.get(u))["cont"] or "NONE" for u in f0ids])
    fact = [f for f in fr["factorial"] if f["cell"] in cells]
    fids = [f["id"] for f in fact]
    fX = X_new(D, fids)
    alg_of_cell = {"LEV_DEQ": "bfs", "DFS_STK": "dfs", "LEV_HEAP": "dijkstra_unit", "HEU_HEAP": "astar_or_gbfs"}
    evc = {}
    for r in read_jsonl(DATA / "factorial.jsonl"):
        evc[r["uid"]] = r
    flab = []
    for f in fact:
        a = alg_of_cell.get(f["cell"], "factorial-other")
        if a == "astar_or_gbfs":
            sc = evc[f["id"]]["scrubbed"]
            a = "astar" if ("steps" in sc or "g_score" in sc or "+ 1 +" in sc or "cost" in sc or "g +" in sc) and \
                ("abs(" in sc or "manhattan" in sc) and _f_uses_g(sc) else "gbfs"
        flab.append(a)
    F1 = {"ids": f0ids + fids, "X": np.concatenate([f0X, fX]), "alg": np.concatenate([f0lab, np.array(flab)]),
          "disc": np.concatenate([f0disc, np.array([f["disc"] for f in fact])]),
          "cont": np.concatenate([f0cont, np.array([f["cont"] for f in fact])]),
          "cell": np.concatenate([np.array(["__f0__"] * len(f0ids)), np.array([f["cell"] for f in fact])])}
    F0 = {"ids": f0ids, "X": f0X, "alg": f0lab, "disc": f0disc, "cont": f0cont,
          "cell": np.array(["__f0__"] * len(f0ids))}
    return {"F0": F0, "F1": F1, "cells": cells}


def _f_uses_g(sc: str) -> bool:
    """HEU_HEAP heap key includes the steps so far (A*) -- a heappush whose first tuple element adds two terms."""
    import re

    for m in re.finditer(r"heappush\(\w+,\s*\(([^,]+),", sc):
        if "+" in m.group(1):
            return True
    return False


def subframe(F: dict[str, Any], mask: np.ndarray) -> dict[str, Any]:
    return {k: (v[mask] if isinstance(v, np.ndarray) else [x for x, m in zip(v, mask) if m]) for k, v in F.items()}


def placed_sets(D: dict[str, Any]) -> dict[str, Any]:
    fr = D["fr"]
    surv = fr["survivors"]
    cov = fr["covert"]
    probe = [f for f in fr["factorial"] if f["cell"] == "PROBE"]
    return {"survivors": surv, "covert": cov, "probe": probe}


def g2(tag: str, D: dict[str, Any], k: int = K_PRIMARY) -> dict[str, Any]:
    Fs = build_frames(D)
    F0, F1, cells = Fs["F0"], Fs["F1"], Fs["cells"]
    sets = placed_sets(D)
    out: dict[str, Any] = {"model": tag, "k": k, "block": D["L"], "readout": "R1"}
    geo0, gi0 = geometry.geodesics(F0["X"], k)
    geo1, gi1 = geometry.geodesics(F1["X"], k)
    out["graphs"] = {"F0": {kk: v for kk, v in gi0.items()}, "F1": {kk: v for kk, v in gi1.items()},
                     "F0_n": int(len(F0["X"])), "F1_n": int(len(F1["X"]))}
    # algorithm-level frame classes (F0 and F1)
    res_frames = {}
    for nm, F, geo in (("F0", F0, geo0), ("F1", F1, geo1)):
        present = set(F["alg"].tolist())
        B = [b for b in B5 if b in present]
        NB = [a for a in NB5 if a in present and (F["alg"] == a).sum() >= 10]
        g, near = geometry.g_values(geo, F["alg"], B, NB)
        cls, med = geometry.classify(g)
        res_frames[nm] = {"banned": B, "nonbanned": NB, "g": g, "nearest_banned": near, "classes": cls, "median": med}
    out["frames_algorithm_level"] = res_frames
    # mechanism references on F1: RLX / RND / CRD cells + non-banned catalogue classes
    def mech_refs(F: dict[str, Any], geo: np.ndarray, exclude_cell: str | None) -> tuple[dict[str, float], float, dict]:
        groups = {}
        for c in sorted(set(F["cell"].tolist()) - {"__f0__"}):
            if cell_dc(c)[0] in ("RLX", "RND", "CRD"):
                groups[c] = np.where(F["cell"] == c)[0]
        for a in NB5:
            ix = np.where((F["alg"] == a) & (F["cell"] == "__f0__"))[0]
            if len(ix) >= 10:
                groups["cat:" + a] = ix
        dsets = {}
        for d in BANNED_DISC:
            m = F["disc"] == d
            if exclude_cell:
                m &= F["cell"] != exclude_cell
            dsets[d] = np.where(m)[0]
        gref = A.g_mech_ref(geo, groups, dsets, list(groups))
        vals = [v for v in gref.values() if np.isfinite(v)]
        return gref, float(np.median(vals)) if vals else float("nan"), dsets

    def place(F: dict[str, Any], geo: np.ndarray, x: np.ndarray) -> np.ndarray:
        return A.oos(x, F["X"], geo, k)

    # placed programs' states
    surv = sets["survivors"]
    Xs = X_new(D, [s["id"] for s in surv]) if surv else np.zeros((0, 1))
    cov = sets["covert"]
    Xc = X_new(D, [c["id"] for c in cov]) if cov else np.zeros((0, 1))
    probe = sets["probe"]
    Xp = X_new(D, [p["id"] for p in probe]) if probe else np.zeros((0, 1))
    fams = sorted(set(s["family_split"] for s in surv))
    out["families"] = {}
    rows = []
    # pre-build S_disc / S_cont subframes per container
    sub_cache: dict[tuple[str, str], tuple[dict[str, Any], np.ndarray]] = {}

    def sub(kind: str, cont: str) -> tuple[dict[str, Any], np.ndarray]:
        key = (kind, cont)
        if key not in sub_cache:
            mask = (F1["cont"] != cont) if kind == "S_disc" else (F1["cont"] == cont)
            F = subframe(F1, mask)
            g_, _ = geometry.geodesics(F["X"], min(k, len(F["X"]) - 1))
            sub_cache[key] = (F, g_)
        return sub_cache[key]

    perms_cell_d, _, _ = A.restricted_label_perms(cells, {c: cell_dc(c)[1] for c in cells}, {c: cell_dc(c)[0] for c in cells})
    for fam in fams:
        idx = [i for i, s in enumerate(surv) if s["family_split"] == fam]
        d_f, c_f = surv[idx[0]]["disc"], surv[idx[0]]["cont"]
        own_cell = f"{d_f}_{c_f}" if f"{d_f}_{c_f}" in cells else None
        fr_res: dict[str, Any] = {"n": len(idx), "disc": d_f, "cont": c_f, "own_cell": own_cell}
        # (a) algorithm-level on F0 / F1
        for nm, F, geo in (("F0", F0, geo0), ("F1", F1, geo1)):
            rf = res_frames[nm]
            gx, nb, nearest_alg = [], [], []
            for i in idx:
                dv = place(F, geo, Xs[i])
                means = {a: float(dv[F["alg"] == a].mean()) for a in sorted(set(F["alg"].tolist()))}
                gb = {b: means[b] for b in rf["banned"]}
                gx.append(min(gb.values()))
                nb.append(min(gb, key=gb.get))
                nearest_alg.append(min(means, key=means.get))
            cls = [A.class_of(v, rf["median"]) for v in gx]
            cc = Counter(cls)
            fr_res[nm] = {"S": float(np.mean(gx)), "median": rf["median"], "class_counts": dict(cc),
                          "class": "EDGE" if cc["EDGE"] / len(idx) > 0.5 else ("OPPOSITE" if cc["OPPOSITE"] / len(idx) > 0.5
                                                                                else "MIXED"),
                          "nearest_banned_counts": dict(Counter(nb)), "nearest_algorithm_counts": dict(Counter(nearest_alg)),
                          "class_by_S": A.class_of(float(np.mean(gx)), rf["median"])}
            for j, i in enumerate(idx):
                rows.append({"id": surv[i]["id"], "family": fam, "frame": nm, "g": gx[j], "class": cls[j],
                             "nearest_banned": nb[j], "nearest_algorithm": nearest_alg[j]})
        # (b) mechanism on F1, (c) on S_disc
        for nm, (F, geo) in (("F1_mech", (F1, geo1)), ("S_disc", sub("S_disc", c_f))):
            gref, med, dsets = mech_refs(F, geo, own_cell)
            gm, nd = [], []
            for i in idx:
                dv = place(F, geo, Xs[i])
                per = {d: float(dv[ix].mean()) for d, ix in dsets.items() if len(ix)}
                gm.append(min(per.values()))
                nd.append(min(per, key=per.get))
            cls = [A.class_of(v, med) for v in gm]
            cc = Counter(cls)
            fr_res[nm] = {"g_mech_mean": float(np.mean(gm)), "median_ref": med, "refs": gref, "class_counts": dict(cc),
                          "class": "EDGE" if cc["EDGE"] / len(idx) > 0.5 else ("OPPOSITE" if cc["OPPOSITE"] / len(idx) > 0.5
                                                                                else "MIXED"),
                          "nearest_banned_discipline_counts": dict(Counter(nd)),
                          "n_frame": int(len(F["X"]))}
        # (d) S_cont: nearest discipline cell within the container
        Fc, geoc = sub("S_cont", c_f)
        ccells = sorted(set(Fc["cell"].tolist()) - {"__f0__"})
        if len(ccells) >= 2:
            near_c = []
            for i in idx:
                dv = place(Fc, geoc, Xs[i])
                means = {c: float(dv[Fc["cell"] == c].mean()) for c in ccells}
                near_c.append(min(means, key=means.get))
            share = float(np.mean([cell_dc(c)[0] == d_f for c in near_c]))
            # null: permute discipline labels among the container's cells
            import itertools
            dl = [cell_dc(c)[0] for c in ccells]
            null = []
            for perm in itertools.permutations(range(len(ccells))):
                mp_ = {ccells[j]: dl[perm[j]] for j in range(len(ccells))}
                null.append(float(np.mean([mp_[c] == d_f for c in near_c])))
            fr_res["S_cont"] = {"cells": ccells, "nearest_cell_counts": dict(Counter(near_c)), "share_own_discipline": share,
                                "p_perm": float(np.mean(np.array(null) >= share - 1e-12)), "n_perm": len(null)}
        else:
            fr_res["S_cont"] = {"cells": ccells, "note": "fewer than 2 factorial cells in this container"}
        # (e) Delta_f on F1 factorial programs, within-container discipline permutation
        fmask = F1["cell"] != "__f0__"
        fidx = np.where(fmask)[0]
        fcell = F1["cell"][fidx]
        dvs = np.stack([place(F1, geo1, Xs[i])[fidx] for i in idx])          # [n_f, n_fact]
        cell_means = {c: dvs[:, fcell == c].mean(1) for c in cells}           # per-program mean d to each cell

        def delta_for(dmap: dict[str, str]) -> float:
            same_c = [c for c in cells if cell_dc(c)[1] == c_f and dmap[c] != d_f and c != own_cell]
            same_d = [c for c in cells if dmap[c] == d_f and cell_dc(c)[1] != c_f and c != own_cell]
            if not same_c or not same_d:
                return float("nan")
            a = np.mean([cell_means[c] for c in same_c], axis=0)
            b = np.mean([cell_means[c] for c in same_d], axis=0)
            return float(np.mean(a - b))

        base_map = {c: cell_dc(c)[0] for c in cells}
        dobs = delta_for(base_map)
        dlabs = sorted(set(base_map.values()))
        nulls = []
        for prm in perms_cell_d[:: max(1, len(perms_cell_d) // 5000)]:
            nulls.append(delta_for({c: dlabs[prm[j]] for j, c in enumerate(cells)}))
        nulls = np.array([v for v in nulls if np.isfinite(v)])
        fr_res["Delta"] = {"value": dobs, "p_perm": float(np.mean(nulls >= dobs - 1e-12)) if len(nulls) and np.isfinite(dobs)
                           else None, "n_perm": int(len(nulls)),
                           "same_container_other_discipline": [c for c in cells if cell_dc(c)[1] == c_f and cell_dc(c)[0] != d_f],
                           "same_discipline_other_container": [c for c in cells if cell_dc(c)[0] == d_f and cell_dc(c)[1] != c_f]}
        out["families"][fam] = fr_res
        logger.info(f"[{tag} k{k}] {fam}: F0 {fr_res['F0']['class']} F1 {fr_res['F1']['class']} "
                    f"mech {fr_res['F1_mech']['class']} S_disc {fr_res['S_disc']['class']} Delta {dobs:.3f} "
                    f"(p {fr_res['Delta']['p_perm']})")
    # landing() for UD survivors on F0 / F1 (label-level, iteration 9's nulls)
    try:
        lj = read_json(IN44 / "results" / "landing.json")
        probs = lj["primary"]["null_C_probs"]
        forced = {a: max(0.0, float(p) - 0.0125) for a, p in probs.items()}
        base_counts = Counter(r.get("label") for r in read_jsonl(IN44 / "data" / "labelled_C6_baseline.jsonl"))
        n_ud = sum(1 for s in surv if s["family"] == "UD")
        out["landing_UD"] = {}
        for nm in ("F0", "F1"):
            rf = res_frames[nm]
            if "dijkstra_unit" in rf["g"]:
                out["landing_UD"][nm] = landing.strip(landing.landing(rf["g"], rf["classes"], ["dijkstra_unit"] * n_ud,
                                                                      dict(base_counts), forced))
    except (FileNotFoundError, KeyError) as e:
        out["landing_UD"] = {"error": f"{type(e).__name__}: {e}"}
    # (f) covert
    if len(cov):
        n_ban_alg = sum(int((F0["alg"] == b).sum()) for b in res_frames["F0"]["banned"])
        base0 = n_ban_alg / len(F0["alg"])
        fcells = [c for c in cells]
        base1 = sum(1 for c in fcells if cell_dc(c)[0] in BANNED_DISC) / len(fcells)
        nb0, nb1, cov_rows = 0, 0, []
        for i in range(len(cov)):
            dv0 = place(F0, geo0, Xc[i])
            m0 = {a: float(dv0[F0["alg"] == a].mean()) for a in sorted(set(F0["alg"].tolist()))}
            na = min(m0, key=m0.get)
            dv1 = place(F1, geo1, Xc[i])
            m1 = {c: float(dv1[F1["cell"] == c].mean()) for c in fcells}
            nc_ = min(m1, key=m1.get)
            nb0 += int(na in B5)
            nb1 += int(cell_dc(nc_)[0] in BANNED_DISC)
            cov_rows.append({"id": cov[i]["id"], "label_v9": cov[i]["label_v9"], "nearest_algorithm_F0": na,
                             "nearest_cell_F1": nc_})
        n = len(cov)
        out["covert"] = {"n": n, "share_nearest_banned_F0": nb0 / n, "wilson_F0": A.wilson(nb0, n), "base_F0": base0,
                         "binom_p_F0": A.binom_p(nb0, n, base0), "share_nearest_banned_disc_F1": nb1 / n,
                         "wilson_F1": A.wilson(nb1, n), "base_F1": base1, "binom_p_F1": A.binom_p(nb1, n, base1),
                         "nearest_algorithm_counts_F0": dict(Counter(r["nearest_algorithm_F0"] for r in cov_rows)),
                         "nearest_cell_counts_F1": dict(Counter(r["nearest_cell_F1"] for r in cov_rows)), "rows": cov_rows}
    # PROBE landing on F1
    if len(probe):
        pc = []
        for i in range(len(probe)):
            dv = place(F1, geo1, Xp[i])
            m1 = {c: float(dv[F1["cell"] == c].mean()) for c in cells}
            pc.append(min(m1, key=m1.get))
        disc_counts = Counter(cell_dc(c)[0] for c in pc)
        out["probe"] = {"n": len(probe), "nearest_cell_counts": dict(Counter(pc)), "nearest_discipline_counts": dict(disc_counts),
                        "reading": "mechanism (level order)" if disc_counts.get("LEV", 0) > disc_counts.get("RLX", 0)
                        else ("textbook-name (relaxation)" if disc_counts.get("RLX", 0) > disc_counts.get("LEV", 0) else "tie")}
    out["rows"] = rows
    return out


def verdict_g2(r: dict[str, Any]) -> dict[str, Any]:
    fam = r["families"]
    ud = fam.get("UD-LEV")
    bf = fam.get("BF-RLX")
    v: dict[str, Any] = {}
    if ud:
        v["UD"] = {"EDGE_F0": ud["F0"]["class"] == "EDGE", "EDGE_F1": ud["F1"]["class"] == "EDGE",
                   "nearest_banned_LEV": max(ud["F1_mech"]["nearest_banned_discipline_counts"].items(), key=lambda kv: kv[1])[0] == "LEV",
                   "EDGE_S_disc": ud["S_disc"]["class"] == "EDGE",
                   "Delta_pos_sig": bool(ud["Delta"]["value"] > 0 and (ud["Delta"]["p_perm"] or 1) < 0.05),
                   "OPPOSITE_S_disc": ud["S_disc"]["class"] == "OPPOSITE"}
        v["UD"]["all"] = all(v["UD"][k] for k in ("EDGE_F0", "EDGE_F1", "nearest_banned_LEV", "EDGE_S_disc", "Delta_pos_sig"))
    if bf:
        sc = bf.get("S_cont", {})
        nc = sc.get("nearest_cell_counts") or {}
        v["BF"] = {"OPPOSITE_F0": bf["F0"]["class"] == "OPPOSITE", "OPPOSITE_F1": bf["F1"]["class"] == "OPPOSITE",
                   "nearest_cell_RLX_ARR": bool(nc) and max(nc.items(), key=lambda kv: kv[1])[0] == "RLX_ARR",
                   "Delta_pos": bool(bf["Delta"]["value"] > 0)}
        v["BF"]["all"] = all(v["BF"].values())
    cv = r.get("covert")
    v["covert_ge_0.8"] = bool(cv and cv["share_nearest_banned_F0"] >= 0.8 and cv["share_nearest_banned_disc_F1"] >= 0.8)
    ud_ok, bf_ok = v.get("UD", {}).get("all", False), v.get("BF", {}).get("all", False)
    if v.get("UD", {}).get("OPPOSITE_S_disc"):
        verdict = "DISCONFIRMED"
    elif ud_ok and bf_ok and v["covert_ge_0.8"]:
        verdict = "SUPPORTED"
    elif ud_ok or bf_ok:
        verdict = "PARTIAL"
    else:
        verdict = "NOT SUPPORTED (no prediction set held)"
    v["verdict"] = verdict
    return v


def main() -> None:
    tag = sys.argv[1]
    n_boot = int(sys.argv[sys.argv.index("--boot") + 1]) if "--boot" in sys.argv else 1000
    D = load_all(tag)
    if "--g2-only" not in sys.argv:
        r1 = g1(tag, D, n_boot)
        write_json(RESULTS / f"g1_{tag}.json", r1)
    if "--g1-only" not in sys.argv:
        out = {}
        for k in (K_PRIMARY, K_SECOND):
            r = g2(tag, D, k)
            r["verdict"] = verdict_g2(r)
            out[f"k{k}"] = r
            logger.info(f"[{tag}] G2 k{k} verdict: {r['verdict']['verdict']}")
        write_json(RESULTS / f"g2_{tag}.json", out)


if __name__ == "__main__":
    main()
