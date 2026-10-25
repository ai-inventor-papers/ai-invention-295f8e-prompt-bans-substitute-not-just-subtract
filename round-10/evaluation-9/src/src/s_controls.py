#!/usr/bin/env python3
"""S-1 positive controls: before any new number, reproduce the stored primaries with the vendored code.

(i)   results/n3.json per_k and heldout_k5 (MECH_FIELD='runtime_class', the gate fallback)
(ii)  results/n3_tracer.json incl. mech_fine_traceable and gap_fine (MECH_FIELD='order_class', fine=True)
(iii) pooled gaps of results/n1.json (0.697) and results/n1_tracer.json (0.608)
(iv)  every rho in results/rsa.json to 1e-9 (vendored model_rdms + mantel_exact over the symmetrised k15 class
      geodesic matrix restricted to 'present'), and every p_exact (exactly; all n! relabelings)
(v)   results/b2_summary.json null medians from their shares lists
(vi)  results/b3_summary.json mean_d_heldout from results/b3_heldout_rows.jsonl
(vii) results/placement.json udij_survivors n_edge on every frame
A mismatch stops only that item: status MISMATCH with both values.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
from loguru import logger

import rows as RW
from io_util import A_BASE, A_GEO, A_REN, dep_path, read_json, read_jsonl, ref, save_stage
from vend import A, geo

CELL_KEYS = ["lex_L1_completed", "mech_coarse_traceable", "mech_fine_traceable"]
GAP_KEYS = ["a_lex_mech", "b_lex_notmech", "c_notlex_mech", "d_neither", "n"]


def _cmp_cell(got: dict[str, Any], want: dict[str, Any], keys_gap: tuple[str, ...]) -> list[str]:
    bad = []
    for k in CELL_KEYS:
        for f in ("k", "n"):
            if got[k][f] != want[k][f]:
                bad.append(f"{k}.{f}: got {got[k][f]} want {want[k][f]}")
    for g in keys_gap:
        for f in GAP_KEYS:
            if got[g][f] != want[g][f]:
                bad.append(f"{g}.{f}: got {got[g][f]} want {want[g][f]}")
        for i in range(2):
            if abs(got[g]["gap_newcombe95"][i] - want[g]["gap_newcombe95"][i]) > 1e-12:
                bad.append(f"{g}.gap_newcombe95[{i}]")
    return bad


def control_n3(field: str, stored_rel: str, fine_keys: bool) -> dict[str, Any]:
    stored = read_json(dep_path(A_REN, stored_rel))
    A.MECH_FIELD = field
    res: dict[str, Any] = {"field": field, "stored": ref(A_REN, stored_rel), "cells_checked": 0, "mismatches": []}
    keys_gap = ("gap_L1", "gap_fine") if fine_keys else ("gap_L1",)
    for mk in ("q32", "q14"):
        cells, ho = RW.cells_for(mk)
        for k in range(1, 6):
            banned = sorted(A.K_ORDER[:k], key=A.CANON_ORDER.index)
            got = A.cell_summary(cells[k], banned)
            want = stored[mk]["per_k"][str(k)]
            if "gap_fine" not in want:
                keys = ("gap_L1",)
            else:
                keys = keys_gap
            bad = _cmp_cell(got, want, keys)
            res["cells_checked"] += 1
            res["mismatches"] += [f"{mk} k{k} {b}" for b in bad]
        got = A.cell_summary(ho, list(A.LITERAL5))
        bad = _cmp_cell(got, stored[mk]["heldout_k5"], keys_gap if "gap_fine" in stored[mk]["heldout_k5"]
                        else ("gap_L1",))
        res["cells_checked"] += 1
        res["mismatches"] += [f"{mk} ho {b}" for b in bad]
    A.MECH_FIELD = "runtime_class"
    res["status"] = "MATCH" if not res["mismatches"] else "MISMATCH"
    return res


def control_n1() -> dict[str, Any]:
    out = {}
    for field, rel in (("runtime_class", "results/n1.json"), ("order_class", "results/n1_tracer.json")):
        A.MECH_FIELD = field
        n1 = A.n1(RW.retrace_by_config())
        st = read_json(dep_path(A_REN, rel))
        ok = (abs(n1["pooled_equal_weight"] - st["pooled_equal_weight"]) < 1e-12 and
              all(abs(a - b) < 1e-12 for a, b in zip(n1["pooled_bootstrap95"], st["pooled_bootstrap95"])) and
              abs(n1["pooled_program_weighted"] - st["pooled_program_weighted"]) < 1e-12)
        out[field] = {"recomputed": n1["pooled_equal_weight"], "recorded": st["pooled_equal_weight"],
                      "ci_recomputed": n1["pooled_bootstrap95"], "ci_recorded": st["pooled_bootstrap95"],
                      "program_weighted": n1["pooled_program_weighted"], "source": ref(A_REN, rel,
                                                                                         "pooled_equal_weight"),
                      "status": "MATCH" if ok else "MISMATCH"}
    A.MECH_FIELD = "runtime_class"
    return out


def class_matrix(model_tag: str, name: str) -> tuple[np.ndarray, list[str], dict[str, Any]]:
    g = read_json(dep_path(A_GEO, f"results/geometry_{model_tag}_{name}.json"))
    d = g["L_star"]["describe"]
    M = np.array(d["k15"]["class_geodesic_matrix"], dtype=float)
    M = (M + M.T) / 2
    present = [i for i, a in enumerate(A.CANON_ORDER) if a in d["present"]]
    return M[np.ix_(present, present)], [A.CANON_ORDER[i] for i in present], g


def control_rsa() -> dict[str, Any]:
    G = geo()
    rsa = read_json(dep_path(A_GEO, "results/rsa.json"))
    out: dict[str, Any] = {"per_key": {}, "n_rho": 0, "n_rho_match": 0, "n_p": 0, "n_p_match": 0}
    for key, st in rsa.items():
        if key == "name_evocation":
            continue
        model_tag, name = key.split("|")
        Mn, present, _ = class_matrix(model_tag, name)
        assert present == st["present"], key
        idx = [A.CANON_ORDER.index(a) for a in present]
        mr = G.model_rdms("mcode" if name.startswith("mcode") else name)
        rec = {}
        for mn, s in st["models"].items():
            R = mr[mn][np.ix_(idx, idx)]
            t0 = time.time()
            m = G.mantel_exact(Mn, R)
            rec[mn] = {"rho_recorded": s["rho"], "rho_recomputed": m["rho"], "p_recorded": s["p_exact"],
                       "p_recomputed": m["p_exact"], "n_perms": m["n_perms"],
                       "rho_ok": abs(m["rho"] - s["rho"]) < 1e-9, "p_ok": abs(m["p_exact"] - s["p_exact"]) < 1e-12,
                       "secs": round(time.time() - t0, 2)}
            out["n_rho"] += 1
            out["n_rho_match"] += int(rec[mn]["rho_ok"])
            out["n_p"] += 1
            out["n_p_match"] += int(rec[mn]["p_ok"])
        out["per_key"][key] = rec
        logger.info(f"RSA control {key}: " + ", ".join(f"{k} {v['rho_recomputed']:.3f}/{v['p_recomputed']:.4f}"
                                                       for k, v in rec.items()))
    out["status"] = "MATCH" if out["n_rho"] == out["n_rho_match"] and out["n_p"] == out["n_p_match"] else "MISMATCH"
    return out


def control_b2() -> dict[str, Any]:
    b2 = read_json(dep_path(A_BASE, "results/b2_summary.json"))
    out: dict[str, Any] = {}
    allok = True
    for unit, u in b2["units"].items():
        for fam in ("null_R", "null_Rpure", "null_Rscaled", "null_SPECR"):
            if fam not in u:
                continue
            sh = np.asarray(u[fam]["shares"], float)
            med = float(np.median(sh))
            ok = abs(med - u[fam]["median"]) < 1e-12
            allok &= ok
            out[f"{unit}.{fam}"] = {"recorded": u[fam]["median"], "recomputed": med, "n": int(len(sh)),
                                    "status": "MATCH" if ok else "MISMATCH"}
    out["status"] = "MATCH" if allok else "MISMATCH"
    return out


def b3_d(rows: list[dict[str, Any]], key: str, n_rand: int = 50) -> list[float]:
    d = []
    for r in rows:
        v = r["res"].get(f"{key}|node")
        rv = [r["res"][f"{key}|r{j}"] for j in range(n_rand) if f"{key}|r{j}" in r["res"]]
        if v is None or not rv:
            continue
        d.append(v - float(np.mean(rv)))
    return d


def control_b3() -> dict[str, Any]:
    st = read_json(dep_path(A_BASE, "results/b3_summary.json"))
    rows = read_jsonl(dep_path(A_BASE, "results/b3_heldout_rows.jsonl"))
    out: dict[str, Any] = {}
    allok = True
    for key, v in st["per_node"].items():
        d = b3_d(rows, key)
        ok = len(d) == v["n"] and abs(float(np.mean(d)) - v["mean_d_heldout"]) < 1e-9 and all(
            abs(a - b) < 1e-9 for a, b in zip(d, v["d_per_prompt"]))
        allok &= ok
        out[key] = {"recorded": v["mean_d_heldout"], "recomputed": float(np.mean(d)),
                    "status": "MATCH" if ok else "MISMATCH"}
    out["status"] = "MATCH" if allok else "MISMATCH"
    return out


def control_placement() -> dict[str, Any]:
    pl = read_json(dep_path(A_GEO, "results/placement.json"))
    out: dict[str, Any] = {}
    allok = True
    for fk, fv in pl.items():
        ud = [r for r in fv["rows"] if r["set"] == "SURV" and r["label"] == "dijkstra_unit"]
        n_edge = sum(1 for r in ud if r["class"] == "EDGE")
        ok = len(ud) == fv["udij_survivors"]["n"] and n_edge == fv["udij_survivors"]["n_edge"]
        allok &= ok
        out[fk] = {"recorded": [fv["udij_survivors"]["n_edge"], fv["udij_survivors"]["n"]],
                   "recomputed": [n_edge, len(ud)], "status": "MATCH" if ok else "MISMATCH"}
    out["status"] = "MATCH" if allok else "MISMATCH"
    return out


def run() -> dict[str, Any]:
    res: dict[str, Any] = {}
    for name, fn in (("i_n3_runtime", lambda: control_n3("runtime_class", "results/n3.json", False)),
                     ("ii_n3_tracer", lambda: control_n3("order_class", "results/n3_tracer.json", True)),
                     ("iii_n1", control_n1), ("v_b2_null_medians", control_b2), ("vi_b3_heldout", control_b3),
                     ("vii_placement", control_placement), ("iv_rsa", control_rsa)):
        t0 = time.time()
        try:
            res[name] = fn()
        except Exception as e:  # a failed control stops only its own item
            logger.exception(f"control {name} failed")
            res[name] = {"status": "ERROR", "error": repr(e)}
        res[name]["secs"] = round(time.time() - t0, 1)
        logger.info(f"control {name}: {res[name].get('status')}")
        save_stage("s1_controls", {"status": "PARTIAL", "controls": res})
    st = {k: v.get("status") for k, v in res.items()}
    if "iii_n1" in res and isinstance(res["iii_n1"], dict) and "status" not in res["iii_n1"]:
        pass
    n1s = res.get("iii_n1", {})
    if "runtime_class" in n1s:
        st["iii_n1"] = "MATCH" if all(n1s[f]["status"] == "MATCH" for f in ("runtime_class", "order_class")) \
            else "MISMATCH"
    metrics = {"n_controls": len(st), "n_controls_match": sum(1 for v in st.values() if v == "MATCH"),
               "rsa_rho_checked": res.get("iv_rsa", {}).get("n_rho", 0),
               "rsa_rho_matched": res.get("iv_rsa", {}).get("n_rho_match", 0),
               "rsa_p_matched": res.get("iv_rsa", {}).get("n_p_match", 0),
               "n3_cells_checked": res.get("i_n3_runtime", {}).get("cells_checked", 0)
               + res.get("ii_n3_tracer", {}).get("cells_checked", 0)}
    examples = {"positive_controls": [
        {"input": f"positive control {k}", "output": str(v), "metadata_control": k,
         "eval_match": float(v == "MATCH")} for k, v in st.items()]}
    save_stage("s1_controls", {"status": "DONE" if all(v == "MATCH" for v in st.values()) else "SOME MISMATCH",
                               "summary": st, "controls": res, "metrics": metrics, "examples": examples})
    return res
