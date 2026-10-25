#!/usr/bin/env python3
"""Items 0a, 0b, 0c and 0h (rename artifact art_8nXdw3_lDAll): every reading of the exhaustion cells, the runtime
fine classes the executed code never applied, the described ban under every reading, and the sensitivity in which
unit-weight Dijkstra, IDA* and jump point search count as compliant.

Readings (all on completed programs; the gap is lexical L1 minus mechanistic compliance on the same programs):
  runtime coarse  : vendored analysis_v9.runtime_class (the committed fallback; primary)
  runtime fine    : MECH_FINE[runtime_label]; banned = {MECH_FINE[b] for b in the row's banned names} (0b)
  tracer coarse   : order_class (results/n3_tracer.json)
  tracer fine     : order_class_fine against analysis_v9.fine_banned (stored in results/n3_tracer.json)
  hand reads      : read class where the program was read (Table 429 map), runtime coarse class otherwise (0a)
  UD/IDA*/JPS     : runtime coarse, but runtime labels dijkstra_unit, idastar, jps count as compliant (0h)
"""

from __future__ import annotations

import csv
from collections import Counter
from typing import Any, Callable

from loguru import logger

import rows as RW
from io_util import A_REN, TABLES, dep_path, r2, read_json, ref, save_stage
from vend import A, S

FAMILY_CLASS = {"UD": "BFS", "BF": "OTHER", "CK": "OTHER", "RP": "OTHER", "FL": "OTHER", "SP": "OTHER",
                "RC": "OTHER", "MX": "OTHER"}
FAMILY_NAME = {"UD": "unit-weight Dijkstra", "BF": "grid Bellman-Ford", "CK": "coordinate-key heap",
               "RP": "random-priority frontier", "FL": "raster flood-fill", "SP": "set frontier",
               "RC": "random choice", "MX": "mixed deque"}
UD_SET = {"dijkstra_unit", "idastar", "jps"}
READINGS = ["runtime_coarse", "runtime_fine", "tracer_coarse", "tracer_fine", "hand_reads", "ud_compliant"]
READING_LABEL = {"runtime_coarse": "runtime label, coarse (primary)", "runtime_fine": "runtime label, fine",
                 "tracer_coarse": "tracer, coarse", "tracer_fine": "tracer, fine",
                 "hand_reads": "hand reads substituted", "ud_compliant": "UD/IDA*/JPS compliant"}
SCRIPT = "src/s_rename.py"


def banned_k(k: int) -> list[str]:
    return sorted(A.K_ORDER[:k], key=A.CANON_ORDER.index)


def completed(r: dict[str, Any]) -> bool:
    return A._completed(r)


def rt_class(r: dict[str, Any]) -> str:
    return A.runtime_class(r)


def rt_traceable(r: dict[str, Any]) -> bool:
    return rt_class(r) != "UNTRACEABLE"


def tr_traceable(r: dict[str, Any]) -> bool:
    return r.get("order_class") not in (None, "UNTRACEABLE")


def rt_fine(r: dict[str, Any]) -> str:
    if not rt_traceable(r):
        return "UNTRACEABLE"
    return A.MECH_FINE.get(r.get("runtime_label"), "OTHER")


_READ: dict[str, str] | None = None


def read_map() -> dict[str, str]:
    """uid -> read class (BFS / OTHER); aborts on an unknown family code."""
    global _READ
    if _READ is None:
        m = {}
        for rd in RW.manual_reads():
            fam = rd.get("family")
            if fam not in FAMILY_CLASS:
                raise ValueError(f"unknown family code {fam!r} in manual reads (uid {rd.get('uid')}); item aborts")
            m[rd["uid"]] = FAMILY_CLASS[fam]
        _READ = m
    return _READ


def ok_fn(reading: str) -> tuple[Callable[[dict, list[str]], bool], Callable[[dict], bool]]:
    """(compliance function, traceability function) for a reading."""
    if reading == "runtime_coarse":
        return (lambda r, b: rt_class(r) not in A.coarse_banned(b)), rt_traceable
    if reading == "runtime_fine":
        return (lambda r, b: rt_fine(r) not in {A.MECH_FINE[x] for x in b}), rt_traceable
    if reading == "tracer_coarse":
        return (lambda r, b: r.get("order_class") not in A.coarse_banned(b)), tr_traceable
    if reading == "tracer_fine":
        return (lambda r, b: r.get("order_class_fine") not in A.fine_banned(b)), tr_traceable
    if reading == "hand_reads":
        rm = read_map()
        return (lambda r, b: (rm[r["uid"]] not in A.coarse_banned(b)) if r["uid"] in rm
                else (rt_class(r) not in A.coarse_banned(b))), rt_traceable
    if reading == "ud_compliant":
        return (lambda r, b: True if r.get("runtime_label") in UD_SET
                else (rt_class(r) not in A.coarse_banned(b))), rt_traceable
    raise KeyError(reading)


def paired(rows: list[dict[str, Any]], banned: list[str], reading: str, completed_only: bool = True
           ) -> dict[str, Any]:
    f, tr = ok_fn(reading)
    a = b = c = d = 0
    for r in rows:
        if not r.get("has_code") or (completed_only and r.get("truncated")) or not tr(r):
            continue
        m = f(r, banned)
        lx = bool(r.get("lexical_L1"))
        if lx and m:
            a += 1
        elif lx:
            b += 1
        elif m:
            c += 1
        else:
            d += 1
    n = a + b + c + d
    D, lo, hi = S.newcombe_paired(a, b, c, d)
    return {"a": a, "b": b, "c": c, "d": d, "n": n, "mech_k": a + c, "lex_k": a + b,
            "mech": (a + c) / n if n else None, "lex": (a + b) / n if n else None, "gap": D if n else None,
            "ci": [lo, hi] if n else None, "mcnemar_p": S.mcnemar_exact(b, c),
            "mech_wilson": list(S.wilson_ci(a + c, n)) if n else None}


def bars(k5: dict[str, Any], ho: dict[str, Any]) -> dict[str, Any]:
    b1 = bool(k5["gap"] is not None and k5["gap"] >= 0.4)
    b2 = bool(ho["gap"] is not None and ho["gap"] >= 0.4 and ho["ci"][0] > 0)
    return {"k5_gap_ge_0.4": b1, "heldout_gap_ge_0.4_lb_gt_0": b2, "both": b1 and b2}


def write_csv(name: str, header: list[str], rows_: list[list[Any]]) -> None:
    p = TABLES / name
    with open(p, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows_)
    logger.info(f"wrote tables/{name} ({len(rows_)} rows)")


def config_check() -> dict[str, Any]:
    out = {}
    for cid in ("A_k5", "A_k5_ho", "E_k5", "E_k5_ho"):
        rs = RW.cell(cid)
        out[cid] = {"models": dict(Counter(r.get("model") for r in rs)),
                    "share_with_reasoning_tokens": sum(1 for r in rs if (r.get("reasoning_tokens") or 0) > 0) / len(rs)}
    return out


# ------------------------------------------------------------------------------------------------ 0a + 0b + 0h cells
def all_cells() -> dict[str, Any]:
    """Every reading for every model x cell (k = 1..5 and held out)."""
    out: dict[str, Any] = {}
    for mk in ("q32", "q14"):
        cells, ho = RW.cells_for(mk)
        per: dict[str, Any] = {}
        for k in range(1, 6):
            per[str(k)] = {rd: paired(cells[k], banned_k(k), rd) for rd in READINGS if rd != "hand_reads"}
            per[str(k)]["n_completed"] = sum(1 for r in cells[k] if completed(r))
        per["ho"] = {rd: paired(ho, list(A.LITERAL5), rd) for rd in READINGS if rd != "hand_reads"}
        per["ho"]["n_completed"] = sum(1 for r in ho if completed(r))
        per["5"]["hand_reads"] = paired(cells[5], banned_k(5), "hand_reads")
        per["ho"]["hand_reads"] = paired(ho, list(A.LITERAL5), "hand_reads")
        out[mk] = per
    return out


def run_0a() -> dict[str, Any]:
    reads = list(RW.manual_reads())
    fam_counts = dict(Counter(r.get("family") for r in reads))
    logger.info(f"family codes before any computation: {fam_counts}")
    unknown = [f for f in fam_counts if f not in FAMILY_CLASS]
    if unknown:
        save_stage("s0a", {"status": "ABORTED", "reason": f"unknown family codes {unknown}"})
        raise ValueError(f"unknown family codes {unknown}")
    rm = read_map()
    # join to the k = 5 cells
    cell_of = {}
    for cid in ("A_k5", "A_k5_ho", "E_k5", "E_k5_ho"):
        for r in RW.cell(cid):
            cell_of[r["uid"]] = cid
    joined = Counter(cell_of.get(u, "UNJOINED") for u in rm)
    cfg = config_check()
    cells = all_cells()
    st3 = read_json(dep_path(A_REN, "results/n3.json"))
    st3t = read_json(dep_path(A_REN, "results/n3_tracer.json"))
    # consistency of every reading with the stored files (positive control inside the item)
    checks = []
    for mk in ("q32", "q14"):
        for kk in ("1", "2", "3", "4", "5", "ho"):
            s = st3[mk]["heldout_k5"] if kk == "ho" else st3[mk]["per_k"][kk]
            t = st3t[mk]["heldout_k5"] if kk == "ho" else st3t[mk]["per_k"][kk]
            c = cells[mk][kk]
            checks.append((f"{mk}|{kk}|runtime_coarse", c["runtime_coarse"]["mech_k"], s["mech_coarse_traceable"]["k"]))
            checks.append((f"{mk}|{kk}|tracer_coarse", c["tracer_coarse"]["mech_k"], t["mech_coarse_traceable"]["k"]))
            checks.append((f"{mk}|{kk}|tracer_fine", c["tracer_fine"]["mech_k"], t["mech_fine_traceable"]["k"]))
            checks.append((f"{mk}|{kk}|tracer_fine_gap_n", c["tracer_fine"]["n"], t["gap_fine"]["n"]))
    mism = [c for c in checks if c[1] != c[2]]
    # Table 431b (k = 5 cells under every reading)
    t431b = []
    restate: dict[str, Any] = {}
    for mk in ("q32", "q14"):
        restate[mk] = {}
        for rd in READINGS:
            restate[mk][rd] = bars(cells[mk]["5"][rd], cells[mk]["ho"][rd])
        for kk, lab in (("5", "committed templates"), ("ho", "held-out templates")):
            c = cells[mk][kk]
            row = [RW.MODEL_NAME[mk], lab, c["n_completed"], r2(c["runtime_coarse"]["lex"])]
            for rd in READINGS:
                x = c[rd]
                row += [f"{x['mech_k']}/{x['n']}", r2(x["mech"]), r2(x["gap"]), r2(x["ci"][0]), r2(x["ci"][1])]
            row.append("; ".join(f"{rd}: {'meets' if (restate[mk][rd]['k5_gap_ge_0.4'] if kk == '5' else restate[mk][rd]['heldout_gap_ge_0.4_lb_gt_0']) else 'misses'}"
                                 for rd in READINGS))
            t431b.append(row)
    hdr = ["model", "templates", "completed", "lexical"]
    for rd in READINGS:
        hdr += [f"{rd}_k_of_n", f"{rd}_rate", f"{rd}_gap", f"{rd}_ci_lo", f"{rd}_ci_hi"]
    hdr.append("meets_committed_bar")
    write_csv("table431b_k5_every_reading.csv", hdr, t431b)
    # exact counts table (audit target)
    exact = []
    for mk in ("q32", "q14"):
        for kk in ("1", "2", "3", "4", "5", "ho"):
            for rd in READINGS:
                if rd not in cells[mk][kk]:
                    continue
                x = cells[mk][kk][rd]
                exact.append([mk, kk, rd, x["a"], x["b"], x["c"], x["d"], x["n"], x["mech_k"], x["lex_k"],
                              f"{x['gap']:.10f}", f"{x['ci'][0]:.10f}", f"{x['ci'][1]:.10f}", f"{x['mcnemar_p']:.10g}"])
    write_csv("exhaustion_readings_exact.csv", ["model", "cell", "reading", "a", "b", "c", "d", "n", "mech_k",
                                                "lex_k", "gap", "ci_lo", "ci_hi", "mcnemar_p"], exact)
    # survivors by hand reads: family shares
    fam_rows = [[f, FAMILY_NAME[f], n, FAMILY_CLASS[f]] for f, n in sorted(fam_counts.items(), key=lambda kv: -kv[1])]
    write_csv("manual_read_families.csv", ["family_code", "family", "programs", "read_class"], fam_rows)
    ex = []
    for row in t431b:
        ex.append({"input": f"k = 5 exhaustion cell: {row[0]}, {row[1]} (completed {row[2]}); lexical {row[3]}",
                   "output": "; ".join(f"{READING_LABEL[rd]} {row[4 + 5 * i]} = {row[5 + 5 * i]} (gap {row[6 + 5 * i]}, "
                                       f"{row[7 + 5 * i]} to {row[8 + 5 * i]})" for i, rd in enumerate(READINGS)),
                   "metadata_model": row[0], "metadata_templates": row[1], "metadata_bar": row[-1],
                   "eval_gap_runtime_coarse": float(row[6]), "eval_gap_hand_reads": float(row[6 + 5 * 4]),
                   "eval_gap_tracer_fine": float(row[6 + 5 * 3])})
    q32 = cells["q32"]
    q14 = cells["q14"]
    metrics = {
        "q32_k5_hand_k": q32["5"]["hand_reads"]["mech_k"], "q32_k5_hand_n": q32["5"]["hand_reads"]["n"],
        "q32_k5_hand_rate": q32["5"]["hand_reads"]["mech"], "q32_k5_hand_gap": q32["5"]["hand_reads"]["gap"],
        "q32_ho_hand_rate": q32["ho"]["hand_reads"]["mech"], "q32_ho_hand_gap": q32["ho"]["hand_reads"]["gap"],
        "q14_k5_hand_rate": q14["5"]["hand_reads"]["mech"], "q14_k5_hand_gap": q14["5"]["hand_reads"]["gap"],
        "q14_ho_hand_rate": q14["ho"]["hand_reads"]["mech"], "q14_ho_hand_gap": q14["ho"]["hand_reads"]["gap"],
        "q14_ho_tracer_fine_gap": q14["ho"]["tracer_fine"]["gap"],
        "q14_ho_tracer_fine_meets_bar": float(restate["q14"]["tracer_fine"]["heldout_gap_ge_0.4_lb_gt_0"]),
        "q32_k5_tracer_fine_gap": q32["5"]["tracer_fine"]["gap"],
        "n_reads": len(reads), "n_reads_joined": sum(v for k, v in joined.items() if k != "UNJOINED"),
        "reading_consistency_mismatches": len(mism),
    }
    section = {
        "inputs": [ref(A_REN, "data/manual_reads_v9.jsonl"), ref(A_REN, "data/labelled_v9_{A,E}_k5{,_ho}.jsonl"),
                   ref(A_REN, "results/n3.json"), ref(A_REN, "results/n3_tracer.json")],
        "computation": "family codes printed and mapped before computing (UD -> BFS order, banned; all other codes -> "
                       "other, compliant; unknown code aborts); substituted compliance = read class if read else "
                       "runtime coarse class, over the runtime-traceable completed set; paired Newcombe (vendored "
                       "stats_v9.newcombe_paired) and exact McNemar; Table 431b every reading; bars quoted from "
                       "commit1a",
        "results": {"family_counts": fam_counts, "joined_cells": dict(joined), "config_check": cfg,
                    "restatement": restate, "consistency_mismatches": mism},
        "edits": ["E-9.3-exhaustion", "E-T431", "E-T444", "E-T443", "E-9.8-established", "E-closing-ban"],
        "status": "DONE" if not mism else "MISMATCH",
    }
    save_stage("s0a", {"status": section["status"], "cells": cells, "restatement": restate,
                       "family_counts": fam_counts, "joined": dict(joined), "config_check": cfg,
                       "consistency_checks": checks, "metrics": metrics, "section": section,
                       "examples": {"exhaustion_readings": ex}})
    return cells


def run_0b() -> dict[str, Any]:
    a0 = None
    from io_util import load_stage
    a0 = load_stage("s0a")
    cells = a0["cells"] if a0 else all_cells()
    st3 = read_json(dep_path(A_REN, "results/n3.json"))
    st3t = read_json(dep_path(A_REN, "results/n3_tracer.json"))
    # proof of the no-op
    eq = tot = 0
    differ = 0
    for mk in ("q32", "q14"):
        for kk in ("1", "2", "3", "4", "5", "ho"):
            s = st3[mk]["heldout_k5"] if kk == "ho" else st3[mk]["per_k"][kk]
            t = st3t[mk]["heldout_k5"] if kk == "ho" else st3t[mk]["per_k"][kk]
            tot += 1
            eq += int(s["mech_fine_traceable"]["k"] == s["mech_coarse_traceable"]["k"]
                      and s["mech_fine_traceable"]["n"] == s["mech_coarse_traceable"]["n"])
            differ += int(t["mech_fine_traceable"]["k"] != t["mech_coarse_traceable"]["k"])
    noop = {"n3_json_fine_equals_coarse_cells": eq, "cells": tot, "n3_tracer_cells_differ": differ,
            "jt_fine_equals_jt_coarse_runtime": all(st3[mk]["jt_mech_fine"]["J"] == st3[mk]["jt_mech_coarse"]["J"]
                                                    for mk in ("q32", "q14")),
            "code": "vendor/art_8nXdw3_lDAll/analysis_v9.py line 41 (MECH_FIELD) and lines 60-63 (mech_ok: fine "
                    "classes are used only when MECH_FIELD == 'order_class')",
            "proved": eq == tot and differ >= 1}
    # JT over k for the runtime fine reading (record's n_perm 100,000; fine used seed 1)
    jt = {}
    for mk in ("q32", "q14"):
        cs, _ = RW.cells_for(mk)
        f, tr = ok_fn("runtime_fine")
        groups = [[int(f(r, banned_k(k))) for r in cs[k] if completed(r) and tr(r)] for k in range(1, 6)]
        jt[mk] = S.jt_test_decreasing(groups, n_perm=100_000, seed=1)
    # k = 4 coarse violations that are greedy best-first
    cs32, _ = RW.cells_for("q32")
    v4 = [r for r in cs32[4] if completed(r) and rt_traceable(r) and rt_class(r) in A.coarse_banned(banned_k(4))]
    g4 = sum(1 for r in v4 if r.get("runtime_label") == "gbfs")
    cs14, _ = RW.cells_for("q14")
    v4_14 = [r for r in cs14[4] if completed(r) and rt_traceable(r) and rt_class(r) in A.coarse_banned(banned_k(4))]
    g4_14 = sum(1 for r in v4_14 if r.get("runtime_label") == "gbfs")
    t431 = []
    for mk in ("q32", "q14"):
        for kk in ("1", "2", "3", "4", "5", "ho"):
            c = cells[mk][kk]
            t431.append([RW.MODEL_NAME[mk], "5, held out" if kk == "ho" else kk, c["n_completed"],
                         r2(c["runtime_coarse"]["lex"]), r2(c["runtime_coarse"]["mech"]),
                         f"{c['runtime_fine']['mech_k']}/{c['runtime_fine']['n']}", r2(c["runtime_fine"]["mech"]),
                         r2(c["runtime_fine"]["gap"]), f"{r2(c['runtime_fine']['ci'][0])} to {r2(c['runtime_fine']['ci'][1])}",
                         r2(c["tracer_coarse"]["mech"]),
                         f"{c['tracer_fine']['mech_k']}/{c['tracer_fine']['n']}", r2(c["tracer_fine"]["mech"]),
                         r2(c["ud_compliant"]["mech"]),
                         r2(c["hand_reads"]["mech"]) if "hand_reads" in c else "n/a (no reads)"])
    write_csv("table431_all_k_fine_columns.csv",
              ["model", "k", "completed", "lexical", "runtime_coarse", "runtime_fine_k_of_n", "runtime_fine",
               "runtime_fine_gap", "runtime_fine_ci", "tracer_coarse", "tracer_fine_k_of_n", "tracer_fine",
               "ud_compliant", "hand_reads"], t431)
    ex = [{"input": f"{r[0]} k = {r[1]}: runtime fine classes", "output": f"runtime fine {r[5]} = {r[6]} (gap {r[7]}, {r[8]}); "
           f"coarse {r[4]}; tracer coarse {r[9]}; tracer fine {r[10]} = {r[11]}", "metadata_model": r[0],
           "metadata_k": r[1], "eval_runtime_fine": float(r[6]), "eval_runtime_coarse": float(r[4])} for r in t431]
    q = cells["q32"]
    metrics = {"q32_k4_runtime_fine_k": q["4"]["runtime_fine"]["mech_k"], "q32_k4_runtime_fine_n": q["4"]["runtime_fine"]["n"],
               "q32_k4_runtime_fine": q["4"]["runtime_fine"]["mech"], "q32_k5_runtime_fine": q["5"]["runtime_fine"]["mech"],
               "q32_k4_coarse_violations": len(v4), "q32_k4_coarse_violations_greedy": g4,
               "q14_k4_coarse_violations": len(v4_14), "q14_k4_coarse_violations_greedy": g4_14,
               "noop_equal_cells": eq, "noop_cells": tot, "tracer_cells_differ": differ,
               "jt_runtime_fine_q32_p": jt["q32"]["p_mc"], "jt_runtime_fine_q14_p": jt["q14"]["p_mc"]}
    section = {"inputs": [ref(A_REN, "results/n3.json"), ref(A_REN, "results/n3_tracer.json"),
                          ref(A_REN, "data/labelled_v9_*.jsonl#runtime_label")],
               "computation": "runtime_fine = MECH_FINE[runtime_label]; banned per row = {MECH_FINE[b] for b in the "
                              "names banned at that k}; compliance, paired Newcombe gap, exact McNemar and "
                              "Jonckheere-Terpstra (100,000 permutations, seed 1, as the record's jt_mech_fine)",
               "results": {"noop_proof": noop, "jt_runtime_fine": jt, "k4_greedy_violations_q32": [g4, len(v4)],
                           "k4_greedy_violations_q14": [g4_14, len(v4_14)]},
               "edits": ["E-9.3-exhaustion"], "status": "DONE" if noop["proved"] else "NO-OP NOT PROVED"}
    save_stage("s0b", {"status": section["status"], "noop": noop, "jt": jt, "k4": {"q32": [g4, len(v4)],
                                                                                    "q14": [g4_14, len(v4_14)]},
                       "metrics": metrics, "section": section, "examples": {"runtime_fine_classes": ex}})
    return noop


def run_0c() -> dict[str, Any]:
    from io_util import load_stage
    desc = list(RW.cell("C_desc"))
    named = list(RW.cell("A_k5"))
    b = list(A.LITERAL5)
    st = read_json(dep_path(A_REN, "results/n3d.json"))
    stt = read_json(dep_path(A_REN, "results/n3d_tracer.json"))

    def comp(rows_: list[dict], reading: str) -> tuple[int, int]:
        f, tr = ok_fn(reading)
        ct = [r for r in rows_ if completed(r) and tr(r)]
        return sum(1 for r in ct if f(r, b)), len(ct)

    rd = {}
    for reading in ("runtime_coarse", "tracer_coarse", "tracer_fine", "runtime_fine", "ud_compliant"):
        kd, nd = comp(desc, reading)
        kn, nn = comp(named, reading)
        u = S.unpaired_diff(kd, nd, kn, nn)
        rd[reading] = {"described": [kd, nd], "named": [kn, nn], "diff": u["diff"], "ci": u["newcombe95"]}
    kh, nh = comp(named, "hand_reads")
    kd, nd = rd["runtime_coarse"]["described"]
    u = S.unpaired_diff(kd, nd, kh, nh)
    rd["per_cell_argued"] = {"described": [kd, nd], "named": [kh, nh], "diff": u["diff"], "ci": u["newcombe95"],
                             "note": "runtime label for the described cell, hand reads substituted for the named cell"}
    reads_in_desc = sum(1 for r in desc if r["uid"] in read_map())
    # reproduction of the stored values
    rep = {"runtime": [rd["runtime_coarse"]["described"] == [st["described"]["mech_compliance"]["k"],
                                                            st["described"]["mech_compliance"]["n"]],
                       rd["runtime_coarse"]["named"] == [st["named_k5"]["mech_compliance"]["k"],
                                                         st["named_k5"]["mech_compliance"]["n"]],
                       abs(rd["runtime_coarse"]["diff"] - st["diffs"]["mech_compliance"]["diff"]) < 1e-12],
           "tracer": [rd["tracer_coarse"]["described"] == [stt["described"]["mech_compliance"]["k"],
                                                          stt["described"]["mech_compliance"]["n"]],
                      rd["tracer_coarse"]["named"] == [stt["named_k5"]["mech_compliance"]["k"],
                                                       stt["named_k5"]["mech_compliance"]["n"]],
                      abs(rd["tracer_coarse"]["diff"] - stt["diffs"]["mech_compliance"]["diff"]) < 1e-12]}
    untr = {"described_completed": sum(1 for r in desc if completed(r)),
            "described_runtime_traceable": comp(desc, "runtime_coarse")[1],
            "described_tracer_traceable": comp(desc, "tracer_coarse")[1],
            "described_tracer_untraceable_uids": [r["uid"] for r in desc if completed(r) and not tr_traceable(r)]}
    t433 = []
    for reading, lab in (("runtime_coarse", "Mechanistic compliance, runtime label (primary)"),
                         ("tracer_coarse", "Mechanistic compliance, tracer"),
                         ("tracer_fine", "Mechanistic compliance, tracer fine classes (computed from rows; not stored)"),
                         ("runtime_fine", "Mechanistic compliance, runtime fine classes"),
                         ("per_cell_argued", "Described (runtime label) against named with hand reads substituted")):
        x = rd[reading]
        t433.append([lab, f"{x['described'][0]}/{x['described'][1]}", r2(x['described'][0] / x['described'][1]),
                     f"{x['named'][0]}/{x['named'][1]}", r2(x['named'][0] / x['named'][1]), r2(x["diff"]),
                     r2(x["ci"][0]), r2(x["ci"][1]), f"{x['diff']:.10f}", f"{x['ci'][0]:.10f}", f"{x['ci'][1]:.10f}"])
    write_csv("table433b_described_vs_named.csv", ["measure", "described_k_of_n", "described", "named_k_of_n",
                                                   "named", "diff", "ci_lo", "ci_hi", "diff_exact", "ci_lo_exact",
                                                   "ci_hi_exact"], t433)
    ex = [{"input": f"described against named five-name ban (Qwen3-32B k = 5): {r[0]}",
           "output": f"{r[1]} = {r[2]} against {r[3]} = {r[4]}; difference {r[5]} ({r[6]} to {r[7]})",
           "metadata_reading": r[0], "eval_diff": float(r[8])} for r in t433]
    metrics = {"runtime_diff": rd["runtime_coarse"]["diff"], "tracer_diff": rd["tracer_coarse"]["diff"],
               "tracer_fine_diff": rd["tracer_fine"]["diff"], "per_cell_argued_diff": rd["per_cell_argued"]["diff"],
               "per_cell_argued_ci_lo": rd["per_cell_argued"]["ci"][0],
               "per_cell_argued_ci_hi": rd["per_cell_argued"]["ci"][1],
               "reads_in_described_cell": reads_in_desc, "reproduced": float(all(all(v) for v in rep.values()))}
    section = {"inputs": [ref(A_REN, "results/n3d.json"), ref(A_REN, "results/n3d_tracer.json"),
                          ref(A_REN, "data/labelled_v9_C_desc.jsonl"), ref(A_REN, "data/labelled_v9_A_k5.jsonl")],
               "computation": "described against named mechanistic compliance under every reading; unpaired Newcombe "
                              "method 10 (vendored stats_v9.unpaired_diff); denominators are the reading's "
                              "traceable completed programs",
               "results": {"readings": rd, "reproduction": rep, "traceability": untr,
                           "reads_in_described_cell": reads_in_desc},
               "edits": ["E-9.3-described", "E-T433", "E-9.8-established", "E-closing-ban"],
               "status": "DONE" if all(all(v) for v in rep.values()) else "MISMATCH"}
    save_stage("s0c", {"status": section["status"], "readings": rd, "reproduction": rep, "traceability": untr,
                       "reads_in_described_cell": reads_in_desc, "metrics": metrics, "section": section,
                       "examples": {"described_vs_named": ex}})
    return rd


def run_0h() -> dict[str, Any]:
    from io_util import load_stage
    by_cfg = RW.retrace_by_config()
    per = {}
    gaps_ud, gaps_rt = [], []
    covert = covert_bd = 0
    t427 = []
    for cfg, rs in by_cfg.items():
        x = paired(rs, list(A.LITERAL5), "ud_compliant", completed_only=False)
        y = paired(rs, list(A.LITERAL5), "runtime_coarse", completed_only=False)
        per[cfg] = {"ud": x, "runtime": y}
        gaps_ud.append(x["gap"])
        gaps_rt.append(y["gap"])
        cv = [r for r in rs if r.get("has_code") and rt_traceable(r) and r.get("lexical_L1")
              and rt_class(r) in A.coarse_banned(list(A.LITERAL5))]
        covert += len(cv)
        covert_bd += sum(1 for r in cv if r.get("runtime_label") in ("bfs", "dfs"))
        t427.append([cfg, x["n"], r2(y["gap"]), r2(x["mech"]), r2(x["gap"]), r2(x["ci"][0]), r2(x["ci"][1]),
                     f"{x['gap']:.10f}", len(cv), sum(1 for r in cv if r.get("runtime_label") in ("bfs", "dfs"))])
    pooled_ud = S.cluster_bootstrap_mean(gaps_ud, B=10_000, seed=0)
    pooled_rt = S.cluster_bootstrap_mean(gaps_rt, B=10_000, seed=0)
    n_prog = sum(per[c]["ud"]["n"] for c in per)
    write_csv("table427_ud_compliant.csv", ["config", "programs", "gap_runtime", "mech_ud_compliant", "gap_ud",
                                            "ci_lo", "ci_hi", "gap_ud_exact", "covert", "covert_bfs_or_dfs"], t427)
    a0 = load_stage("s0a")
    cells = a0["cells"] if a0 else all_cells()
    n1 = read_json(dep_path(A_REN, "results/n1.json"))
    n1t = read_json(dep_path(A_REN, "results/n1_tracer.json"))
    ib = read_json(dep_path(A_REN, "results/instrument_bounds.json"))
    c6 = {"runtime_gap": n1["per_config"]["C6"]["gap"], "tracer_gap": n1t["per_config"]["C6"]["gap"],
          "bounds": [ib["N1"]["C6"]["gap_lower"], ib["N1"]["C6"]["gap_upper"]],
          "source": [ref(A_REN, "results/n1.json", "per_config.C6.gap"), ref(A_REN, "results/n1_tracer.json",
                                                                              "per_config.C6.gap"),
                     ref(A_REN, "results/instrument_bounds.json", "N1.C6.gap_lower/gap_upper")]}
    metrics = {"pooled_gap_ud_compliant": pooled_ud[0], "pooled_gap_ud_ci_lo": pooled_ud[1],
               "pooled_gap_ud_ci_hi": pooled_ud[2], "pooled_gap_runtime_recomputed": pooled_rt[0],
               "programs": n_prog, "covert": covert, "covert_bfs_or_dfs": covert_bd,
               "q32_k4_ud": cells["q32"]["4"]["ud_compliant"]["mech"], "q32_k5_ud": cells["q32"]["5"]["ud_compliant"]["mech"],
               "q14_k5_ud": cells["q14"]["5"]["ud_compliant"]["mech"], "c6_runtime_gap": c6["runtime_gap"],
               "c6_tracer_gap": c6["tracer_gap"], "c6_bound_lo": c6["bounds"][0], "c6_bound_hi": c6["bounds"][1]}
    ex = [{"input": f"retraced configuration {r[0]} ({r[1]} programs): unit-weight Dijkstra, IDA* and JPS compliant",
           "output": f"gap {r[4]} ({r[5]} to {r[6]}) against runtime-label gap {r[2]}; covert {r[8]}, of which BFS/DFS "
                     f"runtime label {r[9]}", "metadata_config": r[0], "eval_gap_ud": float(r[7])} for r in t427]
    section = {"inputs": [ref(A_REN, "results/retrace.jsonl"), ref(A_REN, "results/n1.json"),
                          ref(A_REN, "results/n1_tracer.json"), ref(A_REN, "results/instrument_bounds.json")],
               "computation": "runtime labels dijkstra_unit, idastar and jps counted as compliant; per-configuration "
                              "paired gaps; equal-weight pooled gap with the record's configuration bootstrap "
                              "(cluster_bootstrap_mean, B 10,000, seed 0); covert programs by runtime label",
               "results": {"pooled_ud": pooled_ud, "pooled_runtime": pooled_rt, "covert": [covert_bd, covert],
                           "c6_range": c6},
               "edits": ["E-T427", "E-9.3-positioning", "E-closing-ban", "E-closing-open"], "status": "DONE"}
    save_stage("s0h", {"status": "DONE", "per_config": per, "pooled_ud": pooled_ud, "pooled_runtime": pooled_rt,
                       "covert": [covert_bd, covert], "c6": c6, "metrics": metrics, "section": section,
                       "examples": {"ud_sensitivity": ex}})
    return per
