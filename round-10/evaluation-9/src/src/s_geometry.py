#!/usr/bin/env python3
"""Items 0d and 0e (geometry artifact art_VVA3P0ocZNA2).

0d  per-family placement of every survivor on every program frame. The family map is frozen (written to
    tables/placement_family_map.csv, sha256 logged) before any class is read.
0e  representational similarity: data-structure attributes (R_DS) against lexical distance (R_lex); the
    Spearman of the two model matrices with its exact relabeling p; partial Spearman (Pearson partial correlation of
    average-rank vectors) of each manifold with R_lex given R_DS and with R_DS given R_lex, with exact relabeling p
    under two schemes: A relabels the tested matrix (neural and control fixed; continuity with rsa.json), B
    (Freedman-Lane) residualises the neural ranks on the control ranks and relabels the residual matrix.
"""

from __future__ import annotations

import csv
import re
import time
from collections import Counter
from typing import Any

import numpy as np
from loguru import logger
from scipy.stats import rankdata

from io_util import A_GEO, TABLES, dep_path, r2, read_json, ref, save_stage, sha256_file
from s_controls import class_matrix
from vend import A, S, geo

FAMILIES = ["unit-weight Dijkstra", "Bellman-Ford/SPFA", "BFS variants", "other known"]
FRAME_LABEL = {"32b|mcode_PRIMARY_R1": "Qwen3-32B, primary readout (block 33)",
               "32b|mcode_PRIMARY_R2": "Qwen3-32B, second readout (block 21; gate fails)",
               "32b|mcode_M32_R1": "Qwen3-32B programs only (block 31)",
               "8b|mcode_PRIMARY_R1": "Qwen3-8B, primary readout (block 17)"}
RSA_LABEL = {"32b|mname": "Named, Qwen3-32B", "32b|mdesc": "Described, Qwen3-32B", "32b|mlex": "Name-only, Qwen3-32B",
             "32b|mcode_PRIMARY_R1": "Program, primary readout, Qwen3-32B",
             "32b|mcode_PRIMARY_R2": "Program, second readout, Qwen3-32B",
             "32b|mcode_M32_R1": "Program, Qwen3-32B programs only", "8b|mname": "Named, Qwen3-8B",
             "8b|mdesc": "Described, Qwen3-8B", "8b|mcode_PRIMARY_R1": "Program, primary readout, Qwen3-8B"}


def family_of(label: str, other_name: str | None) -> str:
    on = (other_name or "").lower()
    if label == "dijkstra_unit":
        return "unit-weight Dijkstra"
    if label == "other" and ("bellman" in on or "spfa" in on):
        return "Bellman-Ford/SPFA"
    if re.search(r"\bbfs\b", on):
        return "BFS variants"
    return "other known"


def run_0d() -> dict[str, Any]:
    pl = read_json(dep_path(A_GEO, "results/placement.json"))
    frames = list(pl.keys())
    # ---- freeze the family map from labels and other_names only (no class, g or nearest field is read here)
    first = pl[frames[0]]["rows"]
    fmap = {}
    for r in first:
        if r["set"] != "SURV":
            continue
        fmap[r["uid"]] = (r["label"], r.get("other_name") or "", family_of(r["label"], r.get("other_name")))
    p = TABLES / "placement_family_map.csv"
    with open(p, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["uid", "label", "other_name", "family"])
        for uid, (lab, on, fam) in sorted(fmap.items()):
            w.writerow([uid, lab, on, fam])
    map_sha = sha256_file(p)
    logger.info(f"family map frozen before reading any class: tables/placement_family_map.csv sha256 {map_sha}")
    sizes = dict(Counter(v[2] for v in fmap.values()))
    other_names = {f: sorted({v[1] for v in fmap.values() if v[2] == f}) for f in FAMILIES}
    # same programs and labels on every frame
    same = all({r["uid"]: (r["label"], r.get("other_name") or "") for r in pl[f]["rows"] if r["set"] == "SURV"}
               == {u: (v[0], v[1]) for u, v in fmap.items()} for f in frames)
    # ---- per family x frame
    out: dict[str, Any] = {}
    rows_csv = []
    for f in frames:
        fv = pl[f]
        fg = fv["frame_g"]
        far = max(fg.values())
        out[f] = {"frame_median": fv["frame_median"], "frame_g": fg, "loo": fv["G_place"], "block": fv["block"],
                  "families": {}}
        for fam in FAMILIES:
            rs = [r for r in fv["rows"] if r["set"] == "SURV" and fmap[r["uid"]][2] == fam]
            n = len(rs)
            n_opp = sum(1 for r in rs if r["class"] == "OPPOSITE")
            n_edge = sum(1 for r in rs if r["class"] == "EDGE")
            lo, hi = S.wilson_ci(n_opp, n) if n else (None, None)
            gx = [r["g_x"] for r in rs]
            beyond = sum(1 for r in rs if r["g_x"] > far)
            near = dict(Counter(r["nearest_algorithm"] for r in rs))
            rec = {"n": n, "edge": n_edge, "opposite": n_opp, "share_opposite": n_opp / n if n else None,
                   "wilson95": [lo, hi], "median_g": float(np.median(gx)) if gx else None,
                   "g_values": gx, "beyond_farther_reference": beyond, "nearest_algorithm": near}
            out[f]["families"][fam] = rec
            rows_csv.append([FRAME_LABEL[f], fam, n, n_edge, n_opp, r2(rec["share_opposite"]), r2(lo), r2(hi),
                             f"{rec['median_g']:.3f}", f"{fv['frame_median']:.3f}", f"{fg.get('dijkstra_unit'):.3f}",
                             f"{fg.get('idastar'):.3f}", beyond,
                             "; ".join(f"{k} {v}" for k, v in sorted(near.items(), key=lambda kv: -kv[1])),
                             f"{fv['G_place']['loo_accuracy']:.2f} ({'passes' if fv['G_place']['pass'] else 'fails'})"])
    with open(TABLES / "table438b_placement_families.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["frame", "family", "n", "edge", "opposite", "share_opposite", "wilson_lo", "wilson_hi",
                    "median_g", "frame_median", "g_unit_weight_dijkstra", "g_idastar", "beyond_farther_reference",
                    "nearest_algorithm", "loo_gate"])
        w.writerows(rows_csv)
    bf = {f: out[f]["families"]["Bellman-Ford/SPFA"] for f in frames}
    ud = {f: out[f]["families"]["unit-weight Dijkstra"] for f in frames}
    metrics = {"family_unit_weight_dijkstra": sizes.get("unit-weight Dijkstra", 0),
               "family_bellman_ford": sizes.get("Bellman-Ford/SPFA", 0), "family_bfs_variants": sizes.get("BFS variants", 0),
               "family_other_known": sizes.get("other known", 0),
               "bf_opposite_32b_primary": bf["32b|mcode_PRIMARY_R1"]["opposite"],
               "bf_opposite_32b_programs_only": bf["32b|mcode_M32_R1"]["opposite"],
               "bf_opposite_8b": bf["8b|mcode_PRIMARY_R1"]["opposite"],
               "bf_median_g_32b_primary": bf["32b|mcode_PRIMARY_R1"]["median_g"],
               "ud_edge_32b_primary": ud["32b|mcode_PRIMARY_R1"]["edge"], "ud_edge_32b_programs_only": ud["32b|mcode_M32_R1"]["edge"],
               "frames_same_programs": float(same)}
    ex = [{"input": f"placement of the {r[1]} survivors on the {r[0]} frame",
           "output": f"{r[2]} programs: edge {r[3]}, opposite {r[4]} (share opposite {r[5]}, Wilson {r[6]} to {r[7]}); "
                     f"median g {r[8]} against frame median {r[9]} (references: unit-weight Dijkstra {r[10]}, IDA* {r[11]}); "
                     f"beyond the farther reference {r[12]}; nearest {r[13]}; gate {r[14]}",
           "metadata_frame": r[0], "metadata_family": r[1], "eval_share_opposite": float(r[5]) if r[5] != "n/a" else 0.0,
           "eval_n": float(r[2])} for r in rows_csv]
    section = {"inputs": [ref(A_GEO, "results/placement.json")],
               "computation": "family map frozen from label/other_name before any class was read (sha256 logged); per "
                              "family x frame counts of edge/opposite, Wilson intervals, median g, the two reference g "
                              "values (unit-weight Dijkstra, IDA*), the count beyond the farther reference, nearest "
                              "algorithm counts and the frame's leave-one-out gate",
               "results": {"family_sizes": sizes, "other_names": other_names, "map_sha256": map_sha, "frames": out},
               "caveats": ["the per-family placement was not preregistered",
                           "with only two non-banned classes on the program frames, 'opposite' means farther than the "
                           "median of the unit-weight Dijkstra and IDA* frame g values",
                           "the class depends on that two-class reference"],
               "edits": ["E-T438", "E-9.8-established", "E-9.9", "E-closing-ban"], "status": "DONE"}
    save_stage("s0d", {"status": "DONE", "family_map_sha256": map_sha, "family_sizes": sizes,
                       "other_names": other_names, "frames": out, "metrics": metrics, "section": section,
                       "examples": {"placement_families": ex}})
    return out


# ------------------------------------------------------------------------------------------------ 0e
def _upper(M: np.ndarray) -> np.ndarray:
    iu = np.triu_indices(len(M), 1)
    return M[iu]


def _resid(y: np.ndarray, z: np.ndarray) -> np.ndarray:
    Z = np.c_[np.ones(len(z)), z]
    return y - Z @ np.linalg.lstsq(Z, y, rcond=None)[0]


def partial_corr(y: np.ndarray, x: np.ndarray, z: np.ndarray) -> float:
    ey, ex = _resid(y, z), _resid(x, z)
    den = np.sqrt((ey ** 2).sum() * (ex ** 2).sum())
    return float((ey * ex).sum() / den) if den > 0 else float("nan")


def exact_partial(neural: np.ndarray, tested: np.ndarray, control: np.ndarray) -> dict[str, Any]:
    """Partial Spearman of neural with tested given control, with exact relabeling p under scheme A (relabel the
    tested matrix) and scheme B (Freedman-Lane: relabel the matrix of neural-rank residuals on the control ranks).
    One-sided (>=), all n! relabelings, identity included (as mantel_exact)."""
    n = len(neural)
    iu = np.triu_indices(n, 1)
    y = rankdata(neural[iu])
    x = rankdata(tested[iu])
    z = rankdata(control[iu])
    obs = partial_corr(y, x, z)
    m = len(y)
    zc = z - z.mean()
    zz = (zc ** 2).sum()
    ey = _resid(y, z)
    ex = _resid(x, z)
    # matrices to relabel
    X = np.zeros((n, n))
    X[iu] = x
    X = X + X.T
    E = np.zeros((n, n))
    E[iu] = ey
    E = E + E.T
    fx, fe = X.ravel(), E.ravel()
    sx2, sxm = (x ** 2).sum(), x.mean()
    se2 = (ey ** 2).sum()
    P = geo()._perms(n)
    geA = geB = 0
    ey_n = np.sqrt((ey ** 2).sum())
    ex_n = np.sqrt((ex ** 2).sum())
    for s in range(0, len(P), 200_000):
        ch = P[s:s + 200_000].astype(np.int64)
        idx = ch[:, iu[0]] * n + ch[:, iu[1]]
        xp = fx[idx]
        # scheme A: corr(ey, (I-H) x_pi) = ey.x_pi / (|ey| sqrt(|x|^2 - m xbar^2 - (x_pi.zc)^2/|zc|^2))
        num = xp @ ey
        den = ey_n * np.sqrt(np.maximum(sx2 - m * sxm ** 2 - (xp @ zc) ** 2 / zz, 1e-300))
        geA += int(np.sum(num / den >= obs - 1e-12))
        # scheme B: corr((I-H) E_pi, ex) = ex.E_pi / (|ex| sqrt(|E|^2 - (E_pi.zc)^2/|zc|^2))   (mean(E) = 0)
        ep = fe[idx]
        numb = ep @ ex
        denb = ex_n * np.sqrt(np.maximum(se2 - (ep @ zc) ** 2 / zz, 1e-300))
        geB += int(np.sum(numb / denb >= obs - 1e-12))
    return {"partial": obs, "p_scheme_A": geA / len(P), "p_scheme_B": geB / len(P), "n_perms": int(len(P)),
            "n_pairs": int(m)}


def run_0e() -> dict[str, Any]:
    G = geo()
    rsa = read_json(dep_path(A_GEO, "results/rsa.json"))
    out: dict[str, Any] = {}
    rows_csv = []
    t437 = []
    for key, st in rsa.items():
        if key == "name_evocation":
            continue
        t0 = time.time()
        model_tag, name = key.split("|")
        Mn, present, _ = class_matrix(model_tag, name)
        idx = [A.CANON_ORDER.index(a) for a in present]
        mr = G.model_rdms("mcode" if name.startswith("mcode") else name)
        Rl = mr["R_lex"][np.ix_(idx, idx)]
        Rd = mr["R_DS"][np.ix_(idx, idx)]
        ld = G.mantel_exact(Rl, Rd)
        r = ld["rho"]
        vif = 1.0 / (1.0 - r ** 2)
        lex_given_ds = exact_partial(Mn, Rl, Rd)
        ds_given_lex = exact_partial(Mn, Rd, Rl)
        # check: the vendored partial_spearman gives the same statistic
        ps_v = G.partial_spearman(_upper(Mn), _upper(Rl), _upper(Rd))
        rec = {"present": present, "n_classes": len(present), "lex_ds_spearman": r, "lex_ds_p_exact": ld["p_exact"],
               "vif": vif, "lex_given_ds": lex_given_ds, "ds_given_lex": ds_given_lex,
               "vendored_partial_spearman_lex_given_ds": ps_v,
               "rho": {m: st["models"].get(m, {}).get("rho") for m in ("R_lex", "R_beh", "R_beh_order", "R_DS",
                                                                        "R_surface", "R_len", "R_desc_lex")},
               "p_exact": {m: st["models"].get(m, {}).get("p_exact") for m in ("R_lex", "R_beh", "R_beh_order",
                                                                                "R_DS", "R_surface", "R_len",
                                                                                "R_desc_lex")},
               "secs": round(time.time() - t0, 1)}
        out[key] = rec
        logger.info(f"0e {key}: lex-DS r {r:.3f}; lex|DS {lex_given_ds['partial']:.3f} (A {lex_given_ds['p_scheme_A']:.4f}, "
                    f"B {lex_given_ds['p_scheme_B']:.4f}); DS|lex {ds_given_lex['partial']:.3f} "
                    f"(A {ds_given_lex['p_scheme_A']:.4f}, B {ds_given_lex['p_scheme_B']:.4f}); {rec['secs']} s")
        rows_csv.append([RSA_LABEL[key], len(present), f"{r:.6f}", f"{ld['p_exact']:.6f}", f"{vif:.4f}",
                         f"{lex_given_ds['partial']:.6f}", f"{lex_given_ds['p_scheme_A']:.6f}",
                         f"{lex_given_ds['p_scheme_B']:.6f}", f"{ds_given_lex['partial']:.6f}",
                         f"{ds_given_lex['p_scheme_A']:.6f}", f"{ds_given_lex['p_scheme_B']:.6f}", ld["n_perms"]])
        t437.append([RSA_LABEL[key], len(present)] + [f"{rec['rho'][m]:.6f}" if rec['rho'][m] is not None else "n/a"
                                                      for m in ("R_lex", "R_beh", "R_beh_order", "R_DS", "R_desc_lex",
                                                                "R_surface", "R_len")]
                     + [f"{rec['p_exact'][m]:.6f}" if rec['p_exact'][m] is not None else "n/a"
                        for m in ("R_lex", "R_beh", "R_beh_order", "R_DS", "R_desc_lex", "R_surface", "R_len")])
        save_stage("s0e", {"status": "PARTIAL", "per_manifold": out})
    with open(TABLES / "table437b_partial_rsa.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["manifold", "classes", "lex_ds_spearman", "lex_ds_p_exact", "vif", "lex_given_ds",
                    "lex_given_ds_p_A", "lex_given_ds_p_B", "ds_given_lex", "ds_given_lex_p_A", "ds_given_lex_p_B",
                    "n_relabelings"])
        w.writerows(rows_csv)
    with open(TABLES / "table437_extended.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        ms = ("R_lex", "R_beh", "R_beh_order", "R_DS", "R_desc_lex", "R_surface", "R_len")
        w.writerow(["manifold", "classes"] + [f"rho_{m}" for m in ms] + [f"p_{m}" for m in ms])
        w.writerows(t437)
    nm = out["32b|mname"]
    beh_order = [v["rho"]["R_beh_order"] for v in out.values() if v["rho"]["R_beh_order"] is not None]
    lang = [k for k in out if not k.split("|")[1].startswith("mcode")]
    metrics = {"mname32_lex_ds_r": nm["lex_ds_spearman"], "mname32_lex_ds_p": nm["lex_ds_p_exact"],
               "mname32_vif": nm["vif"], "mname32_lex_given_ds": nm["lex_given_ds"]["partial"],
               "mname32_lex_given_ds_pA": nm["lex_given_ds"]["p_scheme_A"],
               "mname32_lex_given_ds_pB": nm["lex_given_ds"]["p_scheme_B"],
               "mname32_ds_given_lex": nm["ds_given_lex"]["partial"],
               "mname32_ds_given_lex_pA": nm["ds_given_lex"]["p_scheme_A"],
               "mname32_ds_given_lex_pB": nm["ds_given_lex"]["p_scheme_B"],
               "mname32_R_DS_rho": nm["rho"]["R_DS"], "mname32_R_DS_p": nm["p_exact"]["R_DS"],
               "R_beh_order_min_language": min(out[k]["rho"]["R_beh_order"] for k in lang),
               "R_beh_order_max_language": max(out[k]["rho"]["R_beh_order"] for k in lang),
               "R_beh_order_min_all": min(beh_order), "R_beh_order_max_all": max(beh_order)}
    ex = [{"input": f"partial RSA on the {r[0]} manifold ({r[1]} classes)",
           "output": f"Spearman(R_lex, R_DS) {float(r[2]):.2f} (exact p {float(r[3]):.4f}; VIF {float(r[4]):.2f}); "
                     f"lexical given data structure {float(r[5]):.2f} (p A {float(r[6]):.4f}, B {float(r[7]):.4f}); "
                     f"data structure given lexical {float(r[8]):.2f} (p A {float(r[9]):.4f}, B {float(r[10]):.4f})",
           "metadata_manifold": r[0], "eval_lex_given_ds": float(r[5]), "eval_ds_given_lex": float(r[8])}
          for r in rows_csv]
    section = {"inputs": [ref(A_GEO, "results/rsa.json"), ref(A_GEO, "results/geometry_<model>_<manifold>.json",
                                                              "L_star.describe.k15.class_geodesic_matrix"),
                          ref(A_GEO, "results/lexical.json", "R_lex"),
                          ref(A_GEO, "results/behavioural_distance.json", "d_DS"),
                          ref(A_GEO, "data/descriptions_v0.json", "R_desc_lex")],
               "computation": "vendored model_rdms and mantel_exact (compiled unmodified from stage_analysis.py); "
                              "partial Spearman = Pearson partial correlation of average-rank vectors; exact one-sided "
                              "relabeling p over all n! relabelings under scheme A (relabel the tested matrix) and "
                              "scheme B (Freedman-Lane residual relabeling); VIF = 1/(1 - r^2) of the two model "
                              "matrices; all p read descriptively (partial Mantel tests can be anticonservative for "
                              "structured matrices)",
               "results": out, "edits": ["E-9.4-rsa", "E-T437", "E-closing-ban"], "status": "DONE"}
    save_stage("s0e", {"status": "DONE", "per_manifold": out, "metrics": metrics, "section": section,
                       "examples": {"rsa_partials": ex}})
    return out
