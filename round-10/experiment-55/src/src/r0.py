#!/usr/bin/env python3
"""Stage 0.3 reproduction gate R0 (CPU): rebuild iteration 9's PRIMARY_R1 M-code frame from the frozen states
(exp46 cache/states/mcode_<m>.npz, read in place) with the copied geometry.py, at k 15 and k 10, and check
  * class-level g, rank and g/median of unit-weight Dijkstra equal results/geometry_<m>_mcode_PRIMARY_R1.json;
  * the placement of the 15 iteration-8 unit-weight Dijkstra survivors (15/15 EDGE) and every placement row of
    results/placement.json reproduce (out-of-sample attachment through the fixed frame graph).
On failure nothing is modified: the delta is reported (plan F4)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
import geometry  # noqa: E402
import v10  # noqa: E402

B5 = v10.BANNED_ALGS
NB5 = v10.NONBANNED_ALGS


def load_frame(tag: str, block: int, readout: str = "R1") -> dict:
    z = np.load(v10.E46_STATES / f"mcode_{tag}.npz")
    keys = [str(k) for k in z["keys"]]
    ri = [str(r) for r in z["readouts"]].index(readout)
    bi = [int(b) for b in z["blocks"]].index(block)
    ms = v10.read_json(v10.IN46 / "data" / "mcode_sets.json")
    rows = []
    for a in v10.CANON:
        prog = ms["sets"]["PRIMARY"][a]
        if len(prog) < 10:
            continue
        for p in prog:
            rows.append((keys.index(p["scrubbed_sha256"]), a, p["uid"], p["scrubbed_sha256"]))
    idx = np.array([r[0] for r in rows])
    X = z["R"][idx, ri, bi].astype(np.float64)
    out = {"X": X, "labels": np.array([r[1] for r in rows]), "uids": [r[2] for r in rows],
           "keys": [r[3] for r in rows], "all_keys": keys, "R": z["R"], "ri": ri, "bi": bi,
           "blocks": [int(b) for b in z["blocks"]], "readouts": [str(r) for r in z["readouts"]],
           "placement": ms["placement"]}
    return out


def oos(x: np.ndarray, F: np.ndarray, geo: np.ndarray, k: int) -> np.ndarray:
    """exp46 stage_analysis.oos (copied verbatim)."""
    d = np.linalg.norm(F - x, axis=1)
    nn = np.argsort(d)[:k]
    return np.min(d[nn][:, None] + geo[nn], axis=0)


def describe_k(X: np.ndarray, labels: np.ndarray, k: int) -> dict:
    present = set(labels.tolist())
    nb = [a for a in NB5 if a in present]
    bp = [b for b in B5 if b in present]
    geo, info = geometry.geodesics(X, k)
    g, near = geometry.g_values(geo, labels, bp, nb)
    cls, med = geometry.classify(g)
    rank = sorted(nb, key=lambda a: g[a]).index("dijkstra_unit") + 1 if "dijkstra_unit" in nb else None
    return {"geo": geo, "info": info, "g": g, "near": near, "classes": cls, "median": med, "udij_rank": rank,
            "udij_ratio": g["dijkstra_unit"] / med if med > 0 else None}


def run() -> dict:
    out: dict = {"utc": v10.utc_now(), "models": {}}
    plc = v10.read_json(v10.IN46 / "results" / "placement.json")
    for tag, block in (("8b", 17), ("32b", 33)):
        ref = v10.read_json(v10.IN46 / "results" / f"geometry_{tag}_mcode_PRIMARY_R1.json")
        assert ref["L_star"]["block"] == block
        fr = load_frame(tag, block)
        rec: dict = {"block": block, "n_points": int(len(fr["X"])), "n_points_iter9": ref["n_points"]}
        for k in (15, 10):
            d = describe_k(fr["X"], fr["labels"], k)
            want = ref["L_star"]["describe"][f"k{k}"]
            dg = max(abs(d["g"][a] - want["g"][a]) for a in want["g"])
            rec[f"k{k}"] = {"g": d["g"], "g_iter9": want["g"], "max_abs_g_diff": dg, "udij_ratio": d["udij_ratio"],
                            "udij_ratio_iter9": want["udij_ratio"], "udij_rank": d["udij_rank"],
                            "udij_rank_iter9": want["udij_rank"], "classes": d["classes"],
                            "classes_iter9": want["classes"], "components": d["info"]["components_before_join"],
                            "pass": dg <= 1e-6 and d["udij_rank"] == want["udij_rank"] and
                            d["classes"] == want["classes"]}
            if k == 15:
                pref = plc[f"{tag}|mcode_PRIMARY_R1"]
                geo = d["geo"]
                labels = fr["labels"]
                med = d["median"]
                n_rows, n_match, ud_edge, ud_n = 0, 0, 0, 0
                maxdiff = 0.0
                prow = {r["uid"]: r for r in pref["rows"]}
                for p in fr["placement"]:
                    if p["scrubbed_sha256"] not in fr["all_keys"] or p["uid"] not in prow:
                        continue
                    x = fr["R"][fr["all_keys"].index(p["scrubbed_sha256"]), fr["ri"], fr["bi"]].astype(np.float64)
                    dv = oos(x, fr["X"], geo, k)
                    means = {a: float(dv[labels == a].mean()) for a in sorted(set(labels.tolist()))}
                    gb = {b: means[b] for b in B5 if b in means}
                    gx = min(gb.values())
                    cls = "EDGE" if gx < med - 1e-12 else ("OPPOSITE" if gx > med + 1e-12 else "MIDDLE")
                    w = prow[p["uid"]]
                    n_rows += 1
                    maxdiff = max(maxdiff, abs(gx - w["g_x"]))
                    n_match += int(cls == w["class"] and min(means, key=means.get) == w["nearest_algorithm"])
                    if p["set"] == "SURV" and p["algorithm"] == "dijkstra_unit":
                        ud_n += 1
                        ud_edge += int(cls == "EDGE")
                rec["placement"] = {"n_rows": n_rows, "n_rows_iter9": len(pref["rows"]), "n_match": n_match,
                                    "max_abs_g_diff": maxdiff, "udij_survivors_edge": f"{ud_edge}/{ud_n}",
                                    "iter9": f"{pref['udij_survivors']['n_edge']}/{pref['udij_survivors']['n']}",
                                    "pass": n_match == n_rows and maxdiff <= 1e-6 and
                                    ud_edge == pref["udij_survivors"]["n_edge"]}
        rec["pass"] = rec["k15"]["pass"] and rec["k10"]["pass"] and rec["placement"]["pass"]
        out["models"][tag] = rec
        logger.info(f"R0 {tag}: k15 udij_ratio {rec['k15']['udij_ratio']:.4f} (iter9 {rec['k15']['udij_ratio_iter9']:.4f})"
                    f" max|dg| {rec['k15']['max_abs_g_diff']:.2e}; placement {rec['placement']}")
    out["pass"] = all(m["pass"] for m in out["models"].values())
    v10.write_json(v10.RESULTS / "r0_reproduction.json", out)
    return out


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    r = run()
    print("R0 pass:", r["pass"])
