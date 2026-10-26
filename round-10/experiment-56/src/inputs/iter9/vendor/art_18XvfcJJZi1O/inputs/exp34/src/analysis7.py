#!/usr/bin/env python3
"""Pre-registered analysis of F and P2 (N.1-N.3), the T03 confirmation (C.2) and the Stage 0 engine check.
Frozen by hash in amendment commit0b before commit #3; reads POP outcome rows only after commit #3 exists.

Outcome of a cell: y = correct (passed) programs labelled a non-default catalogue algorithm / N rows; attempted =
non-default catalogue labels / N; pass = passed / N. exp29 engine-d rows (POP, TWIN, PN), exp30 bf16 rows (BAN,
Stage A exchange, FORCED*, PLACEBO, T03 TWIN), this run's rows (T03 fresh directions, Stage 0).
"""

from __future__ import annotations

import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

import c7 as common  # noqa: E402
from c7 import (CATALOGUE, DATA, DEFAULTS, IN29, IN30, LABELS, PRED, RESULTS, SEEDS40, SEEDS_T03, guarded_e29_rows,  # noqa: E402
                read_json, read_jsonl, write_json)
import stats7 as S  # noqa: E402

FAMILY = {"TWIN": "TWIN", "BAN": "BAN", "PN_a1": "PN", "PN_a2": "PN", "FORCED": "FORCED", "FORCEDPAD": "FORCED",
          "FORCEDX_0-35": "FORCED", "X_0-35": "STAGEA", "X_12-23": "STAGEA", "X_24-35": "STAGEA",
          "X_0-11": "STAGEA", "PLACEBO": "STAGEA"}


def cell_stats(rows: list[dict[str, Any]], task: str) -> dict[str, Any]:
    d = DEFAULTS[task]
    cat = set(CATALOGUE[task])
    n = len(rows)
    k_corr = sum(1 for r in rows if r["label"] in cat and r["label"] != d and r["passed"])
    k_att = sum(1 for r in rows if r["label"] in cat and r["label"] != d)
    k_pass = sum(1 for r in rows if r["passed"])
    return {"n": n, "k": k_corr, "y": k_corr / n if n else float("nan"), "k_att": k_att,
            "att": k_att / n if n else float("nan"), "pass": k_pass / n if n else float("nan"),
            "labels": dict(sorted(((l, sum(1 for r in rows if r["label"] == l)) for l in {r["label"] for r in rows}),
                                  key=lambda kv: -kv[1]))}


def e29_rows(allow_pop: bool) -> dict[tuple[str, str], list[dict[str, Any]]]:
    out = defaultdict(list)
    for r in guarded_e29_rows(IN29 / "labels.jsonl", allow_pop=allow_pop):
        if not r["key"].startswith("d|"):
            continue
        if int(r["sample_id"]) > 5 and r["arm"].startswith("POP_"):
            continue
        out[(r["task"], r["arm"])].append(r)
    return out


def e30_rows() -> dict[tuple[str, str], list[dict[str, Any]]]:
    out = defaultdict(list)
    for r in read_jsonl(IN30 / "labels.jsonl"):
        out[(r["task"], r["arm"])].append(r)
    return out


def escape_flags(task: str, pop: dict[tuple[str, str], list[dict[str, Any]]]) -> dict[int, dict[str, Any]]:
    """exp22/exp29 two-stage escape rule (vendored escape.cell_eval) on engine-d rows."""
    import escape as ESC
    cat = set(CATALOGUE[task])
    tw = ESC.share([r for r in pop[(task, "TWIN")] if int(r["sample_id"]) < 10], cat, DEFAULTS[task])
    out = {}
    for s in SEEDS40:
        rr = pop.get((task, f"POP_d{s}_a2.0"), [])
        if rr:
            c = ESC.cell_eval(rr, tw, cat, DEFAULTS[task])
            out[s] = {"screen": c["screen_pass"], "confirmed": c["confirmed"], "n": len(rr)}
    return out


def outcomes() -> dict[str, dict[str, Any]]:
    """N.1: y per (task, cell) for every cell with a margin (POP outcomes only after commit #3)."""
    pop = e29_rows(allow_pop=True)
    s30 = e30_rows()
    out: dict[str, dict[str, Any]] = {}
    for task in ("T10", "T2"):
        for s in SEEDS40:
            rr = pop.get((task, f"POP_d{s}_a2.0"), [])
            if rr:
                out[f"{task}|POP_d{s}_a2.0"] = {**cell_stats(rr, task), "source": "exp29 engine d"}
        out[f"{task}|TWIN"] = {**cell_stats(pop[(task, "TWIN")], task), "source": "exp29 engine d"}
        for arm in ("PN_a1", "PN_a2"):
            out[f"{task}|{arm}"] = {**cell_stats(pop[(task, arm)], task), "source": "exp29 engine d"}
        for arm in ("BAN", "FORCED", "FORCEDPAD", "FORCEDX_0-35", "X_0-35", "X_12-23", "X_24-35", "X_0-11",
                    "PLACEBO"):
            if s30.get((task, arm)):
                out[f"{task}|{arm}"] = {**cell_stats(s30[(task, arm)], task), "source": "exp30 bf16"}
    for arm in ("TWIN", "BAN", "X_0-35", "X_12-23", "X_24-35", "X_0-11", "PLACEBO"):
        if s30.get(("T03", arm)):
            out[f"T03|{arm}"] = {**cell_stats(s30[("T03", arm)], "T03"), "source": "exp30 bf16"}
    mine = defaultdict(list)
    for r in read_jsonl(LABELS):
        mine[(r["task"], r["arm"])].append(r)
    for s in SEEDS_T03:
        rr = [r for r in mine.get(("T03", f"POP_d{s}_a2.0"), []) if int(r["sample_id"]) < 2]
        if rr:
            out[f"T03|POP_d{s}_a2.0"] = {**cell_stats(rr, "T03"), "source": "this run (T03 confirmation)"}
    return out


def f_and_p2() -> dict[str, Any]:
    c3 = read_json(common.c3_path())
    cells = c3["cells"]
    Y = outcomes()
    pop = e29_rows(allow_pop=True)
    th = read_json(PRED / "commit0.json")["thresholds"]
    res: dict[str, Any] = {"F": {}, "P2": {}, "cells": {}}
    groups_F, groups_b = [], []
    for task in ("T10", "T2"):
        esc = escape_flags(task, pop)
        m, y, att, b, pit, nrm, ash, llr, conf, seeds, bL = [], [], [], [], [], [], [], [], [], [], []
        for s in SEEDS40:
            c = cells.get(f"{task}|POP_d{s}_a2.0")
            o = Y.get(f"{task}|POP_d{s}_a2.0")
            if not c or not o:
                continue
            seeds.append(s)
            m.append(c["m"])
            y.append(o["y"])
            att.append(o["att"])
            b.append(c.get("b", float("nan")))
            pit.append(c.get("pi_Pt", float("nan")))
            nrm.append(c.get("norm", float("nan")))
            ash.append(c.get("a_share", float("nan")))
            llr.append(c.get("llr48", float("nan")))
            bL.append(c.get("b_L"))
            conf.append(int(esc.get(s, {}).get("confirmed", False)))
        rho = S.spearman(m, y)
        F_t = {"n": len(y), "rho": rho, "p_perm": S.perm_p(m, y, 10000, seed=11), "ci": S.boot_ci(m, y),
               "kendall": S.kendall(m, y), "rho_max_ties": S.tie_ceiling(y),
               "rho_over_max": rho / S.tie_ceiling(y) if S.tie_ceiling(y) == S.tie_ceiling(y) else None,
               "n_y_pos": int(sum(v > 0 for v in y)), "auc_confirmed": S.auc(m, conf), "n_confirmed": sum(conf),
               "attempted": {"rho": S.spearman(m, att), "p_perm": S.perm_p(m, att, 10000, seed=12)},
               "llr48": {"rho": S.spearman(llr, y), "p_perm": S.perm_p(llr, y, 10000, seed=13)},
               "twin_m": cells.get(f"{task}|TWIN", {}).get("m"),
               "twin_collapsed_le_-4": (cells.get(f"{task}|TWIN", {}).get("m") or 0) <= -4}
        res["F"][task] = F_t
        groups_F.append((m, y))
        rb = S.spearman(b, y)
        P2_t = {"n": len(y), "rho_b": rb, "p_perm": S.perm_p(b, y, 10000, seed=21), "ci": S.boot_ci(b, y),
                "kendall": S.kendall(b, y), "rho_b_m": S.spearman(b, m),
                "competitors": {"pi_Pt": {"rho": S.spearman(pit, y), "diff": S.paired_boot_diff(b, pit, y)},
                                "norm": {"rho": S.spearman(nrm, y), "diff": S.paired_boot_diff(b, nrm, y)},
                                "a_share": {"rho": S.spearman(ash, y), "diff": S.paired_boot_diff(b, ash, y)}},
                "attempted": {"rho": S.spearman(b, att), "p_perm": S.perm_p(b, att, 10000, seed=22)},
                "auc_confirmed": S.auc(b, conf)}
        P2_t["ahead_all"] = all(v["diff"]["lo"] > 0 for v in P2_t["competitors"].values())
        prof = {}
        if bL and all(x is not None for x in bL):
            arr = np.array(bL)
            for j, L in enumerate(common.CAP_BLOCKS):
                prof[str(L)] = S.spearman(arr[:, j], y)
        P2_t["layer_profile"] = prof
        res["P2"][task] = P2_t
        groups_b.append((b, y))
        res["cells"][task] = [{"seed": s, "m": a1, "y": a2, "att": a3, "b": a4, "pi_Pt": a5, "norm": a6,
                               "a_share": a7, "llr48": a8, "confirmed": a9}
                              for s, a1, a2, a3, a4, a5, a6, a7, a8, a9 in zip(seeds, m, y, att, b, pit, nrm, ash,
                                                                              llr, conf)]
    res["F"]["pooled"] = {"rho": S.pooled_within(groups_F), "p_perm": S.pooled_perm_p(groups_F)}
    res["P2"]["pooled"] = {"rho": S.pooled_within(groups_b), "p_perm": S.pooled_perm_p(groups_b)}
    # logistic calibration over all cells of T10 + T2
    mm, kk, nn, st, names, Pb, yy, aa = [], [], [], [], [], [], [], []
    for key, c in cells.items():
        task, cell = key.split("|", 1)
        if task not in ("T10", "T2") or key not in Y or c.get("m") is None or c["m"] != c["m"]:
            continue
        o = Y[key]
        fam = "POP" if cell.startswith("POP_") else FAMILY.get(cell, "OTHER")
        mm.append(c["m"])
        kk.append(o["k"])
        nn.append(o["n"])
        st.append(f"{task}|{fam}")
        names.append(key)
        Pb.append(c["Pbar"])
        yy.append(o["y"])
        aa.append(o["att"])
    cal = S.calibration(mm, kk, nn, st, 10)
    cal["mae_param_free_correct"] = float(np.mean(np.abs(np.array(Pb) - np.array(yy))))
    cal["mae_param_free_attempted"] = float(np.mean(np.abs(np.array(Pb) - np.array(aa))))
    cal["all_cell_spearman"] = S.spearman(mm, yy)
    cal["all_cell_p_perm"] = S.perm_p(mm, yy, 10000, seed=14)
    cal["cells"] = [{"cell": a, "m": b_, "Pbar": c_, "y": d_, "att": e_, "n": f_}
                    for a, b_, c_, d_, e_, f_ in zip(names, mm, Pb, yy, aa, nn)]
    res["F"]["calibration"] = cal
    tF, tP = th["F"], th["P2"]
    f_ok = (all(res["F"][t]["rho"] >= tF["rho_each"] and res["F"][t]["p_perm"] < tF["p"] for t in ("T10", "T2"))
            and res["F"]["pooled"]["rho"] >= tF["rho_pooled"] and cal["mae_heldout_mean"] <= tF["mae"])
    f_dis = all(res["F"][t]["rho"] < tF["disconfirm_rho"] for t in ("T10", "T2"))
    p_ok = all(res["P2"][t]["rho_b"] >= tP["rho_b"] and res["P2"][t]["p_perm"] < tP["p"] and res["P2"][t]["ahead_all"]
               for t in ("T10", "T2"))
    p_dis = all(res["P2"][t]["rho_b"] < tP["disconfirm_rho"] for t in ("T10", "T2"))
    pF = max(res["F"][t]["p_perm"] for t in ("T10", "T2"))
    pP = max(res["P2"][t]["p_perm"] for t in ("T10", "T2"))
    res["verdicts"] = {"F": "SUPPORTED" if f_ok else ("DISCONFIRMED" if f_dis else "NOT SUPPORTED (inconclusive)"),
                       "P2": "SUPPORTED" if p_ok else ("DISCONFIRMED" if p_dis else "NOT SUPPORTED (inconclusive)"),
                       "raw_p": {"F": pF, "P2": pP}, "holm": S.holm({"F": pF, "P2": pP})}
    return res


def t03_confirmation() -> dict[str, Any]:
    c3 = read_json(common.c3_path())["cells"]
    Y = outcomes()
    b, m, y, att, seeds = [], [], [], [], []
    for s in SEEDS_T03:
        c, o = c3.get(f"T03|POP_d{s}_a2.0"), Y.get(f"T03|POP_d{s}_a2.0")
        if c and o:
            seeds.append(s)
            b.append(c.get("b"))
            m.append(c.get("m"))
            y.append(o["y"])
            att.append(o["att"])
    npos = int(sum(v > 0 for v in y))
    res = {"n_directions": len(y), "n_y_pos": npos, "informative": npos >= 3,
           "b": {"rho": S.spearman(b, y), "p_one_sided": S.perm_p(b, y, 10000, seed=31)},
           "m": {"rho": S.spearman(m, y), "p_one_sided": S.perm_p(m, y, 10000, seed=32)},
           "attempted": {"b_rho": S.spearman(b, att), "m_rho": S.spearman(m, att)},
           "rho_max_ties": S.tie_ceiling(y),
           "rows": [{"seed": s, "b": a, "m": c_, "y": d, "att": e} for s, a, c_, d, e in zip(seeds, b, m, y, att)]}
    if not res["informative"]:
        lab = [int(v > 0) for v in y]
        res["fallback"] = {"escape_count": npos, "auc_b": S.auc(b, lab), "auc_m": S.auc(m, lab)}
    return res


def engine_check() -> dict[str, Any]:
    """Stage 0a: per-slot twin label agreement (this run vs exp29 engine d, vs exp30); 0b: 5 POP directions vs exp29
    engine d (after commit #3)."""
    mine = {(r["task"], r["arm"], r["template"], int(r["sample_id"])): r for r in read_jsonl(LABELS)}
    res: dict[str, Any] = {}
    d29 = {(r["task"], r["arm"], r["template"], int(r["sample_id"])): r
           for r in guarded_e29_rows(IN29 / "labels.jsonl", allow_pop=common.pop_rows_released())
           if r["key"].startswith("d|")}
    for task in ("T10", "T2"):
        pairs = [(mine[k], d29[k]) for k in mine if k[0] == task and k[1] == "TWIN" and k[3] <= 5 and k in d29]
        res[f"0a_{task}_vs_exp29d"] = {"n": len(pairs), "label_agree": float(np.mean([a["label"] == b["label"]
                                                                                       for a, b in pairs]))
                                       if pairs else None}
    l30 = {}
    for r in read_jsonl(IN30 / "labels.jsonl"):
        if r["arm"] == "TWIN":
            ck = str(r.get("crn_key") or "")
            parts = ck.split("|")
            if len(parts) == 3:
                l30[(r["task"], parts[1], int(parts[2]))] = r
    for task in ("T2", "T03", "T10"):
        pairs = [(mine[k], l30[(task, k[2], k[3])]) for k in mine if k[0] == task and k[1] == "TWIN" and k[3] <= 3
                 and (task, k[2], k[3]) in l30]
        res[f"0a_{task}_vs_exp30"] = {"n": len(pairs), "label_agree": float(np.mean([a["label"] == b["label"]
                                                                                     for a, b in pairs]))
                                      if pairs else None,
                                      "note": "exp30 sampled with its own decoder (max_new 384/512) and B; slots "
                                              "share the CRN uniforms (task, template, k)"}
    s0b = DATA / "labels_s0b.jsonl"
    if common.pop_rows_released() and s0b.exists():
        mine_b = {(r["task"], r["arm"], r["template"], int(r["sample_id"])): r for r in read_jsonl(s0b)}
        for task in ("T10", "T2"):
            pairs = [(mine_b[k], d29[k]) for k in mine_b if k[0] == task and k[1].startswith("POP_") and k in d29]
            ys_m = defaultdict(list)
            ys_d = defaultdict(list)
            for a, b in pairs:
                ys_m[a["arm"]].append(a)
                ys_d[b["arm"]].append(b)
            res[f"0b_{task}_vs_exp29d"] = {
                "n": len(pairs), "label_agree": float(np.mean([a["label"] == b["label"] for a, b in pairs]))
                if pairs else None,
                "y_this": {k: cell_stats(v, task)["y"] for k, v in ys_m.items()},
                "y_exp29d": {k: cell_stats(v, task)["y"] for k, v in ys_d.items()}}
    nc = RESULTS / "engine_check_norms.json"
    if nc.exists():
        z = read_json(nc)
        res["0c_realised_norms"] = {k: z[k] for k in ("n", "max_rel_diff", "pass_2pct")}
    return res


def main() -> None:
    out = {"F_P2": f_and_p2(), "t03": t03_confirmation(), "engine_check": engine_check()}
    write_json(RESULTS / "f_analysis.json", {"F": out["F_P2"]["F"], "verdicts": out["F_P2"]["verdicts"],
                                             "cells": out["F_P2"]["cells"]})
    write_json(RESULTS / "p2_analysis.json", {"P2": out["F_P2"]["P2"], "verdicts": out["F_P2"]["verdicts"]})
    write_json(RESULTS / "t03_confirmation.json", out["t03"])
    write_json(RESULTS / "engine_check.json", out["engine_check"])
    print(out["F_P2"]["verdicts"])


if __name__ == "__main__":
    main()
