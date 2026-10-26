#!/usr/bin/env python3
"""Stages 4-6: G1 (factorial RSA) and G2 (placement) on one model, with every committed sensitivity, using the
frozen g1.py / g2.py (COMMIT1c). CLI: python src/analysis.py g1|g2 8b|32b [--quick]"""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_v] = "1"                 # one BLAS thread per process: the box has 6 CPUs

import csv
import json
import math
import multiprocessing as mp
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
import g1  # noqa: E402
import g2  # noqa: E402
import geometry  # noqa: E402
import v10  # noqa: E402


# ---------------------------------------------------------------------------------------------- loading
def load_states(tag: str, set_name: str) -> tuple[np.ndarray, np.ndarray, list[str], list[int], list[dict]]:
    z = np.load(v10.STATES_V10 / f"{tag}_{set_name}.npz")
    idx = v10.read_jsonl(v10.STATES_V10 / f"{tag}_{set_name}.jsonl")
    return z["R"], z["E0"], [str(u) for u in z["uids"]], [int(b) for b in z["blocks"]], idx


def factorial(tag: str) -> dict[str, Any]:
    rows = v10.read_jsonl(v10.DATA / "factorial_set.jsonl")
    R, E0, uids, blocks, idx = load_states(tag, "factorial")
    assert uids == [r["uid"] for r in rows]
    return {"rows": rows, "R": R, "E0": E0, "blocks": blocks, "idx": idx,
            "disc": [r["discipline"] for r in rows], "cont": [r["container"] for r in rows],
            "cell": np.array([r["cell"] for r in rows]), "hk": [r.get("heur_key") for r in rows],
            "ctx": [r["context_variant"] for r in rows], "ntok": [m["n_code_tokens"] for m in idx],
            "code": [r["scrubbed"] for r in rows]}


def idf_weights() -> dict[str, float]:
    """Document frequencies of Python NAME/OP/NUMBER tokens over every program-text dataset of the declared
    dependency (art_j3Rm_lr2nzR6 full_data_out.json; all datasets whose 'output' is Python code)."""
    cache = v10.DATA / "idf_weights.json"
    if cache.exists():
        return v10.read_json(cache)["idf"]
    d = json.loads((v10.DSET / "full_data_out.json").read_text())
    df: Counter = Counter()
    n_docs = 0
    used = {}
    for ds in d["datasets"]:
        k = 0
        for ex in ds["examples"]:
            txt = ex.get("output") or ""
            if not isinstance(txt, str) or ("def " not in txt and "import " not in txt):
                continue
            toks = g1.token_set(txt)
            if not toks:
                continue
            df.update(toks)
            n_docs += 1
            k += 1
        used[ds["dataset"]] = {"n_examples": len(ds["examples"]), "n_python_docs": k}
    idf = {t: math.log((1 + n_docs) / (1 + c)) + 1.0 for t, c in df.items()}
    v10.write_json(cache, {"n_docs": n_docs, "datasets": used, "idf": idf})
    del d
    return idf


# ---------------------------------------------------------------------------------------------- G1
def _variant(args: tuple) -> tuple[str, dict[str, Any]]:
    name, DS, DD, DC, n_boot, extra = args
    obs = g1.core_stats(DS, DD, DC)
    out = {**obs}
    if extra.get("covars") is not None:
        y, x, z = g1.upper(DS), g1.upper(DD), g1.upper(DC)
        cov = [g1.upper(c) for c in extra["covars"]]
        out["rho_dc_partial_surface"] = g1.partial_spearman(y, x, [z] + cov)
        out["rho_cd_partial_surface"] = g1.partial_spearman(y, z, [x] + cov)
    if n_boot:
        out["bootstrap"] = g1.bootstrap(DS, DD, DC, n_boot, seed=7, groups=extra.get("groups"))
    return name, out


def run_g1(tag: str, quick: bool = False) -> dict[str, Any]:
    t0 = time.time()
    F = factorial(tag)
    m = v10.MODELS[tag]
    bi = F["blocks"].index(m["primary_block"])
    S = F["R"][:, 0, bi].astype(np.float64)
    nb, npm = (200, 400) if quick else (1000, 2000)
    res: dict[str, Any] = {"model": tag, "block": m["primary_block"], "readout": "R1", "n_programs": len(S),
                           "cells": dict(Counter(F["cell"].tolist()))}
    res["primary"] = g1.full_g1(S, F["disc"], F["cont"], n_boot=nb, n_perm=npm, seed=0, cell_groups=F["cell"])
    logger.info(f"G1 {tag} primary: rho_dc {res['primary']['rho_dc']:.3f} rho_cd {res['primary']['rho_cd']:.3f} "
                f"delta CI {res['primary']['bootstrap']['delta']['ci95']}")
    DS = g1.d_state(S)
    DD, DC = g1.d_disc(F["disc"]), g1.d_cont(F["cont"])
    sets = [g1.token_set(c) for c in F["code"]]
    D_surf = g1.d_jaccard(sets)
    D_idf = g1.d_jaccard(sets, idf_weights())
    D_ast = g1.d_jaccard([g1.ast_ngrams(c) for c in F["code"]])
    D_len = g1.d_len(F["ntok"])
    D_ctx = g1.d_labels([str(c) for c in F["ctx"]])
    # ---- S1 crossed core (full inference)
    core = np.array([c.split("-")[0] in ("BFSO", "HEUR", "COST") and c.split("-")[1] in ("LIST", "HEAP", "GRID2D",
                                                                                        "SET") for c in F["cell"]])
    ci = np.where(core)[0]
    res["S1_crossed_core"] = g1.full_g1(S[ci], [F["disc"][i] for i in ci], [F["cont"][i] for i in ci], n_boot=nb,
                                        n_perm=npm, seed=11, cell_groups=F["cell"][ci])
    res["S1_crossed_core"]["cells"] = sorted(set(F["cell"][ci].tolist()))
    logger.info(f"G1 {tag} S1 core: rho_dc {res['S1_crossed_core']['rho_dc']:.3f} rho_cd "
                f"{res['S1_crossed_core']['rho_cd']:.3f}")
    # ---- S2 rank regression
    y = g1.upper(DS)
    res["S2_rank_regression"] = g1.rank_regression(y, {"D_disc": g1.upper(DD), "D_cont": g1.upper(DC),
                                                       "D_surf": g1.upper(D_surf), "D_len": g1.upper(D_len),
                                                       "D_ctx": g1.upper(D_ctx)})
    rng = np.random.default_rng(5)
    boots = []
    for _ in range(50 if quick else 100):
        idx = rng.choice(len(S), size=len(S), replace=True)
        iu = np.triu_indices(len(idx), 1)
        a, b = idx[iu[0]], idx[iu[1]]
        keep = a != b
        a, b = a[keep], b[keep]
        rr = g1.rank_regression(DS[a, b], {"D_disc": DD[a, b], "D_cont": DC[a, b], "D_surf": D_surf[a, b],
                                           "D_len": D_len[a, b], "D_ctx": D_ctx[a, b]})
        boots.append(rr["semi_partial"])
    res["S2_rank_regression"]["semi_partial_ci95"] = {
        k: [float(np.quantile([b[k] for b in boots], 0.025)), float(np.quantile([b[k] for b in boots], 0.975))]
        for k in boots[0]}
    # ---- variants (bootstrap CIs, parallel)
    nbv = 100 if quick else 200
    jobs = [("S3a_cost_merged_into_bfso", DS, g1.d_disc(F["disc"], merge_cost=True), DC, nbv, {}),
            ("S3b_heur_split_greedy_astar", DS, g1.d_disc(F["disc"], heur_split=F["hk"]), DC, nbv, {}),
            ("S4_graded_container_deque_list", DS, DD, g1.d_cont(F["cont"], graded=True), nbv, {}),
            ("S5_surface_jaccard_covariate", DS, DD, DC, 0, {"covars": [D_surf, D_len]}),
            ("S5_surface_idf_covariate", DS, DD, DC, 0, {"covars": [D_idf, D_len]}),
            ("S5_surface_ast4gram_covariate", DS, DD, DC, 0, {"covars": [D_ast, D_len]})]
    for ro_i, ro in ((1, "R1g"), (2, "R2"), (3, "R3")):
        jobs.append((f"S6_readout_{ro}", g1.d_state(F["R"][:, ro_i, bi].astype(np.float64)), DD, DC, nbv, {}))
    for k in (15,):
        geo, _ = geometry.geodesics(S, k)
        jobs.append((f"S6_knn_geodesic_k{k}", geo, DD, DC, nbv, {}))
    jobs.append(("S7_E0_bag_of_tokens", g1.d_state(F["E0"].astype(np.float64)), DD, DC, nbv, {}))
    rn = v10.STATES_V10 / "randnet_factorial.npz"
    if rn.exists() and tag == "8b":
        zr = np.load(rn)
        assert [str(u) for u in zr["uids"]] == [r["uid"] for r in F["rows"]]
        jobs.append(("S7_RANDNET_block17", g1.d_state(zr["R"][:, 0, 0].astype(np.float64)), DD, DC, nbv, {}))
    om = v10.DATA / "order_matrix_factorial.npz"
    if om.exists():
        zo = np.load(om)
        if [str(u) for u in zo["uids"]] == [r["uid"] for r in F["rows"]]:
            jobs.append(("S7_measured_order_as_Ddisc", DS, zo["D"], DC, nbv, {}))
            res["S7_order_matrix_vs_Ddisc_spearman"] = g1.spearman(g1.upper(zo["D"]), g1.upper(DD))
    rep = np.array([not bool(r.get("repair")) for r in F["rows"]])
    ri = np.where(rep)[0]
    jobs.append(("S10_without_repair_rows", DS[np.ix_(ri, ri)], DD[np.ix_(ri, ri)], DC[np.ix_(ri, ri)], nbv, {}))
    jobs.append(("S8_cell_cluster_bootstrap_only", DS, DD, DC, 0, {}))
    with ProcessPoolExecutor(max_workers=2, mp_context=mp.get_context("spawn")) as ex:
        for name, out in ex.map(_variant, jobs):
            res[name] = out
            logger.info(f"G1 {tag} {name}: rho_dc {out['rho_dc']:.3f} rho_cd {out['rho_cd']:.3f}")
    res["S10_without_repair_rows"]["n_programs"] = int(len(ri))
    res["S10_without_paraphrase_rows"] = {"note": "no paraphrase rows in the frozen factorial set (identical to "
                                                  "primary)", "n_paraphrase": sum(r.get("source") == "paraphrase"
                                                                                   for r in F["rows"])}
    res.pop("S8_cell_cluster_bootstrap_only", None)
    res["S8_cell_cluster_bootstrap"] = res["primary"].get("cell_cluster_bootstrap")
    # ---- S6 layer curve
    res["S6_layer_curve"] = {}
    for j, b in enumerate(F["blocks"]):
        st = g1.core_stats(g1.d_state(F["R"][:, 0, j].astype(np.float64)), DD, DC)
        res["S6_layer_curve"][str(b)] = st
    # ---- S9 noise ceiling (context reliability)
    c2 = v10.STATES_V10 / f"{tag}_factorial_ctx2.npz"
    if c2.exists():
        z2 = np.load(c2)
        assert [str(u) for u in z2["uids"]] == [r["uid"] for r in F["rows"]]
        S2 = z2["R"][:, 0, bi].astype(np.float64)
        DS2 = g1.d_state(S2)
        res["S9_noise_ceiling"] = {"spearman_DS_ctx_v_vs_ctx_v+1": g1.spearman(g1.upper(DS), g1.upper(DS2)),
                                   "ctx2_stats": g1.core_stats(DS2, DD, DC)}
    # ---- S11 Kendall tau-a single-model fits
    res["S11_kendall_tau_a"] = {k: g1.tau_a(g1.upper(DS), g1.upper(M)) for k, M in
                                (("D_disc", DD), ("D_cont", DC), ("D_surf", D_surf), ("D_len", D_len),
                                 ("D_ctx", D_ctx))}
    res["design"] = g1.corr_design(DD, DC)
    res["seconds"] = round(time.time() - t0, 1)
    # ---- pairs csv for the stdlib audit
    iu = np.triu_indices(len(S), 1)
    with (v10.RESULTS / f"pairs_{tag}.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["i", "j", "D_S", "D_disc", "D_cont", "D_surf", "D_len"])
        for i, j in zip(*iu):
            w.writerow([int(i), int(j), f"{DS[i, j]:.10g}", DD[i, j], DC[i, j], f"{D_surf[i, j]:.6g}", D_len[i, j]])
    v10.write_json(v10.RESULTS / f"g1_{tag}.json", res)
    return res


# ---------------------------------------------------------------------------------------------- G2 frame
def catalogue(tag: str, block: int, ro: int) -> tuple[np.ndarray, list[str], list[dict]]:
    """129 iteration-9 M-code PRIMARY programs (frozen states, read in place) + frozen top-ups (this round)."""
    import verify

    z = np.load(v10.E46_STATES / f"mcode_{tag}.npz")
    keys = [str(k) for k in z["keys"]]
    zb = [int(b) for b in z["blocks"]]
    ms = v10.read_json(v10.IN46 / "data" / "mcode_sets.json")
    X, lab, meta = [], [], []
    for a in v10.CANON:
        for p in ms["sets"]["PRIMARY"][a]:
            X.append(z["R"][keys.index(p["scrubbed_sha256"]), ro, zb.index(block)].astype(np.float64))
            lab.append(a)
            meta.append({"uid": p["uid"], "kind": "catalogue", "source": p.get("source"),
                         "container": ast_container(p["scrubbed"]), "code": p["scrubbed"]})
    tp = v10.STATES_V10 / f"{tag}_topups.npz"
    if tp.exists():
        zt = np.load(tp)
        rows = v10.read_jsonl(v10.DATA / "topups_set.jsonl")
        assert [str(u) for u in zt["uids"]] == [r["uid"] for r in rows]
        tb = [int(b) for b in zt["blocks"]]
        for i, r in enumerate(rows):
            X.append(zt["R"][i, ro, tb.index(block)].astype(np.float64))
            lab.append(r["cell"])
            meta.append({"uid": r["uid"], "kind": "topup", "source": r.get("source"),
                         "container": ast_container(r["scrubbed"]), "code": r["scrubbed"]})
    _ = verify
    return np.array(X), lab, meta


def ast_container(code: str) -> str:
    import verify

    f = verify.features(code)
    if f.get("syntax_error"):
        return "OTHER"
    if f["heap"]:
        return "HEAP"
    if f["deque"]:
        return "DEQUE"
    if f["set_remove"] or f["min_over_set"] or f["choice_tuple_set"] or f["pop_noarg_set"]:
        return "SET"
    if f["recursive_functions"] and not f["while_pop_loop"]:
        return "CALL"
    if f["pop0"] or f["pop_noarg"] or f["pop_arg"] or f["insort"] or f["head_index"]:
        return "LIST"
    if f["twod_alloc"] and f["nested_range_loops"]:
        return "GRID2D"
    if f["for_over_set"]:
        return "SET"
    return "OTHER"


def build_full_frame(tag: str, block: int, ro: int, k: int) -> g2.Frame:
    F = factorial(tag)
    bi = F["blocks"].index(block)
    Xf = F["R"][:, ro, bi].astype(np.float64)
    meta_f = [{"uid": r["uid"], "kind": "factorial", "container": r["container"], "source": r.get("source")}
              for r in F["rows"]]
    Xc, lab_c, meta_c = catalogue(tag, block, ro)
    lab = list(F["cell"]) + lab_c
    X = np.vstack([Xf, Xc])
    meta = meta_f + meta_c
    cnt = Counter(lab)
    keep = np.array([cnt[c] >= v10.CLASS_FLOOR for c in lab])
    labels = np.array(lab)[keep]
    fr = g2.Frame(X[keep], labels, [m for m, kk in zip(meta, keep) if kk], k, f"full|{tag}|b{block}|ro{ro}|k{k}")
    fr.dropped_classes = {c: n for c, n in cnt.items() if n < v10.CLASS_FLOOR}
    return fr


def placed(tag: str, block: int, ro: int) -> tuple[np.ndarray, list[dict]]:
    rows = v10.read_jsonl(v10.DATA / "placed_programs.jsonl")
    R, _E0, uids, blocks, _idx = load_states(tag, "placed")
    assert uids == [r["uid"] for r in rows]
    X = R[:, ro, blocks.index(block)].astype(np.float64)
    for r in rows:
        r["ast_container"] = ast_container(r["scrubbed"])
    return X, rows


FAMILIES = ["F-UD", "F-BF", "F-CK", "F-RF", "F-RS", "F-SF", "F-OTH", "F-COV", "F-COVX"]


def place_all(fr: g2.Frame, X: np.ndarray, rows: list[dict], fam_filter: Any = None) -> list[dict]:
    out = []
    for x, r in zip(X, rows):
        if fam_filter is not None and not fam_filter(r):
            continue
        p = fr.place(x)
        p.update({"uid": r["uid"], "family": r["family"], "config": r.get("config"), "author": r.get("author"),
                  "covert_kind": r.get("covert_kind"), "ast_container": r.get("ast_container")})
        out.append(p)
    return out


def families(fr: g2.Frame, pl: list[dict], n_boot: int = 1000) -> dict[str, Any]:
    out = {}
    for fam in FAMILIES:
        ps = [p for p in pl if p["family"] == fam]
        if ps:
            out[fam] = g2.family_stats(fr, ps, n_boot=n_boot, seed=hash(fam) % 1000)
    return out


def predictions(full: g2.Frame, pl_full: list[dict], sub: dict[str, Any]) -> dict[str, Any]:
    ud = [p for p in pl_full if p["family"] == "F-UD"]
    bf = [p for p in pl_full if p["family"] == "F-BF"]
    cov = [p for p in pl_full if p["family"] == "F-COV"]
    fs = families(full, pl_full, n_boot=1000)
    out: dict[str, Any] = {}
    heap = sub.get("HEAP", {})
    ud_heap = heap.get("families", {}).get("F-UD", {})
    ud_disc = sum(p["nearest_discipline"] in ("BFSO", "COST") for p in ud)
    out["P-UD"] = {"full_frame": {k: fs.get("F-UD", {}).get(k) for k in ("r_F", "r_F_ci95", "verdict", "robust")},
                   "heap_frame": {k: ud_heap.get(k) for k in ("r_F", "r_F_ci95", "verdict", "robust")},
                   "share_nearest_discipline_BFSO_or_COST": ud_disc / len(ud) if ud else None,
                   "contrast_BFSO_or_COST_HEAP_vs_HEUR_HEAP": g2.contrast(ud, ["BFSO-HEAP", "COST-HEAP"],
                                                                          ["HEUR-HEAP"])}
    v_full, v_heap = out["P-UD"]["full_frame"]["verdict"], out["P-UD"]["heap_frame"]["verdict"]
    c = out["P-UD"]["contrast_BFSO_or_COST_HEAP_vs_HEUR_HEAP"]
    out["P-UD"]["supported"] = bool(v_full == "EDGE" and v_heap == "EDGE" and (out["P-UD"][
        "share_nearest_discipline_BFSO_or_COST"] or 0) > 0.5 and c.get("share", 0) > 0.5)
    out["P-UD"]["disconfirmed"] = v_heap == "OPPOSITE"
    gr = sub.get("GRID2D", {})
    bf_grid = gr.get("families", {}).get("F-BF", {})
    bf_rel = sum(p["nearest_discipline"] == "RELAX" for p in bf)
    out["P-BF"] = {"full_frame": {k: fs.get("F-BF", {}).get(k) for k in ("r_F", "r_F_ci95", "verdict", "robust")},
                   "share_nearest_discipline_RELAX": bf_rel / len(bf) if bf else None,
                   "grid2d_frame_nearest_class_counts": bf_grid.get("nearest_class_counts"),
                   "grid2d_frame_share_nearest_RELAX-GRID2D": (bf_grid.get("nearest_class_counts", {}).get(
                       "RELAX-GRID2D", 0) / bf_grid["n"]) if bf_grid.get("n") else None,
                   "contrast_RELAX-GRID2D_vs_BFSO_COST_GRID2D": g2.contrast(bf, ["RELAX-GRID2D"],
                                                                            ["BFSO-GRID2D", "COST-GRID2D"])}
    out["P-BF"]["supported"] = bool(out["P-BF"]["full_frame"]["verdict"] == "OPPOSITE" and
                                    (out["P-BF"]["share_nearest_discipline_RELAX"] or 0) > 0.5 and
                                    (out["P-BF"]["grid2d_frame_share_nearest_RELAX-GRID2D"] or 0) > 0.5 and
                                    out["P-BF"]["contrast_RELAX-GRID2D_vs_BFSO_COST_GRID2D"].get("share", 0) > 0.5)
    kb = sum(p["nearest_is_banned"] for p in cov)
    bfs_c = [p for p in cov if p["covert_kind"] == "bfs"]
    dfs_c = [p for p in cov if p["covert_kind"] == "dfs"]
    out["P-COV"] = {"n": len(cov), "share_nearest_banned": kb / len(cov) if cov else None,
                    "wilson95": g2.wilson(kb, len(cov)),
                    "covert_bfs_share_nearest_BFSO": (sum(p["nearest_discipline"] == "BFSO" for p in bfs_c) /
                                                      len(bfs_c)) if bfs_c else None,
                    "covert_dfs_share_nearest_DFSO": (sum(p["nearest_discipline"] == "DFSO" for p in dfs_c) /
                                                      len(dfs_c)) if dfs_c else None,
                    "by_config": {c: {"n": sum(p["config"] == c for p in cov),
                                      "share_nearest_banned": float(np.mean([p["nearest_is_banned"] for p in cov
                                                                             if p["config"] == c]))}
                                  for c in sorted({p["config"] for p in cov})},
                    "by_author": {a: {"n": sum(p["author"] == a for p in cov),
                                      "share_nearest_banned": float(np.mean([p["nearest_is_banned"] for p in cov
                                                                             if p["author"] == a]))}
                                  for a in sorted({str(p["author"]) for p in cov})}}
    out["P-COV"]["supported"] = bool(cov and kb / len(cov) >= 0.8)
    return out


def subframes(full: g2.Frame, X: np.ndarray, rows: list[dict], with_disc: bool = True) -> dict[str, Any]:
    out: dict[str, Any] = {}
    conts = np.array([m.get("container") for m in full.meta])
    specs = {"HEAP": (conts == "HEAP", lambda r: r["family"] in ("F-UD", "F-CK") or
                      (r["family"] == "F-RF" and r["ast_container"] == "HEAP")),
             "GRID2D": (conts == "GRID2D", lambda r: r["family"] in ("F-BF", "F-RS")),
             "SET": (conts == "SET", lambda r: r["family"] == "F-SF"),
             "DEQUE+LIST": (np.isin(conts, ["DEQUE", "LIST"]), lambda r: r["family"] in ("F-COV", "F-COVX"))}
    if with_disc:
        discs = np.array([g2.disc_of(str(c)) if "-" in str(c) else "CAT" for c in full.labels])
        specs.update({
            "DISC_BFSO+COST": (np.isin(discs, ["BFSO", "COST"]), lambda r: r["family"] == "F-UD" or
                               (r["family"] == "F-COV" and r.get("covert_kind") == "bfs")),
            "DISC_RELAX": (discs == "RELAX", lambda r: r["family"] == "F-BF"),
            "DISC_DFSO": (discs == "DFSO", lambda r: r["family"] == "F-COV" and r.get("covert_kind") == "dfs")})
    for name, (keep, filt) in specs.items():
        sf = g2.subframe(full, keep, f"{name}|{full.name}")
        if sf is None:
            out[name] = {"skipped": "fewer than 2 classes with >= 10 programs"}
            continue
        pl = place_all(sf, X, rows, filt)
        out[name] = {"frame": sf.summary(), "families": families(sf, pl, n_boot=500), "_placed": pl}
    return out


def run_g2(tag: str, quick: bool = False) -> dict[str, Any]:
    t0 = time.time()
    m = v10.MODELS[tag]
    block = m["primary_block"]
    full = build_full_frame(tag, block, 0, v10.K_PRIMARY)
    X, rows = placed(tag, block, 0)
    pl = place_all(full, X, rows)
    res: dict[str, Any] = {"model": tag, "block": block, "readout": "R1", "k": v10.K_PRIMARY,
                           "frame": full.summary(), "dropped_classes": full.dropped_classes}
    res["families_full"] = families(full, pl, n_boot=200 if quick else 1000)
    sub = subframes(full, X, rows)
    res["held_fixed"] = {k: {kk: vv for kk, vv in v.items() if kk != "_placed"} for k, v in sub.items()}
    res["predictions"] = predictions(full, pl, sub)
    res["frame_loo"] = g2.loo(full, workers=2) if not quick else None
    # placebo: family membership shuffled -> P-UD verdict reproduced above chance?
    rng = np.random.default_rng(3)
    g_all = np.array([p["g"] for p in pl])
    n_ud = sum(p["family"] == "F-UD" for p in pl)
    edge = 0
    for _ in range(1000):
        pick = rng.choice(len(pl), size=n_ud, replace=False)
        edge += int(np.median(g_all[pick]) / full.median < 1)
    res["placebo_family_shuffle"] = {"n": 1000, "share_EDGE_full_frame": edge / 1000,
                                     "observed_verdict": res["families_full"].get("F-UD", {}).get("verdict")}
    # implemented counts for F3 (nearest class of the five-name-ban rows in the frame)
    res["seconds"] = round(time.time() - t0, 1)
    # per-program distances csv
    with (v10.RESULTS / f"geo_class_dist_{tag}.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["uid", "family", "frame", "class", "d", "frame_median", "is_banned"])
        for p in pl:
            for c, d in p["d"].items():
                w.writerow([p["uid"], p["family"], "full", c, f"{d:.10g}", f"{full.median:.10g}",
                            int(g2.is_banned(c))])
        for name, v in sub.items():
            for p in v.get("_placed", []):
                for c, d in p["d"].items():
                    med = v["frame"]["median_nonbanned_class_g"]
                    w.writerow([p["uid"], p["family"], name, c, f"{d:.10g}",
                                f"{med:.10g}" if med is not None else "", int(g2.is_banned(c))])
    res["placements_full"] = [{k: v for k, v in p.items() if k != "d"} | {"d_top5": dict(sorted(
        p["d"].items(), key=lambda kv: kv[1])[:5])} for p in pl]
    v10.write_json(v10.RESULTS / f"g2_{tag}.json", res)
    # coordinates for figures (frame + placed), raw activation space
    np.savez_compressed(v10.STATES_V10 / f"g2frame_{tag}.npz", X=full.X.astype(np.float32), labels=full.labels,
                        geo=full.geo.astype(np.float32), Xp=X.astype(np.float32),
                        fam=np.array([r["family"] for r in rows]), uids_p=np.array([r["uid"] for r in rows]))
    logger.info(f"G2 {tag}: {json.dumps({f: (v.get('r_F'), v.get('verdict')) for f, v in res['families_full'].items()})}"
                f" in {res['seconds']}s")
    return res


def robustness(tags: list[str]) -> dict[str, Any]:
    out = {"cells": []}
    for tag in tags:
        m = v10.MODELS[tag]
        for k in (15, 10):
            for ro_i, ro in ((0, "R1"), (1, "R1g"), (2, "R2")):
                try:
                    full = build_full_frame(tag, m["primary_block"], ro_i, k)
                    X, rows = placed(tag, m["primary_block"], ro_i)
                    pl = place_all(full, X, rows)
                    sub = subframes(full, X, rows, with_disc=False)
                    pr = predictions(full, pl, sub)
                    fs = families(full, pl, n_boot=200)
                    out["cells"].append({"model": tag, "k": k, "readout": ro,
                                         "components": full.info["components_before_join"],
                                         "P-UD": pr["P-UD"]["supported"], "P-UD_full": pr["P-UD"]["full_frame"]["verdict"],
                                         "P-UD_heap": pr["P-UD"]["heap_frame"]["verdict"],
                                         "P-BF": pr["P-BF"]["supported"], "P-BF_full": pr["P-BF"]["full_frame"]["verdict"],
                                         "P-COV": pr["P-COV"]["supported"],
                                         "P-COV_share": pr["P-COV"]["share_nearest_banned"],
                                         "family_rF": {f: v.get("r_F") for f, v in fs.items()}})
                    logger.info(f"robustness {tag} k{k} {ro}: {out['cells'][-1]['P-UD_full']} / "
                                f"{out['cells'][-1]['P-BF_full']} / cov {out['cells'][-1]['P-COV_share']:.2f}")
                except (FileNotFoundError, ValueError, KeyError) as e:
                    out["cells"].append({"model": tag, "k": k, "readout": ro, "error": f"{type(e).__name__}: {e}"})
    prim = [c for c in out["cells"] if c.get("k") == 15 and c.get("readout") == "R1" and c.get("model") == "8b"]
    if prim:
        p = prim[0]
        for key in ("P-UD_full", "P-BF_full", "P-COV"):
            out[f"agree_with_primary_{key}"] = sum(c.get(key) == p.get(key) for c in out["cells"] if "error" not in c)
        out["n_cells"] = sum("error" not in c for c in out["cells"])
    v10.write_json(v10.RESULTS / "robustness.json", out)
    return out


def main() -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(str(v10.LOGS / "analysis.log"), rotation="30 MB", level="DEBUG")
    what, rest = sys.argv[1], sys.argv[2:]
    quick = "--quick" in rest
    tags = [t for t in rest if t in v10.MODELS]
    if what == "g1":
        for t in tags:
            run_g1(t, quick)
    elif what == "g2":
        for t in tags:
            run_g2(t, quick)
    elif what == "robust":
        robustness(tags)


if __name__ == "__main__":
    main()
