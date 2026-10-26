#!/usr/bin/env python3
"""S10 analysis (frozen in commit #1). Reads data/eval_rows.jsonl (one row per sample, written by evalq.py) and the
per-model orders (predictions/commit2_<model>.json) and writes results/{cells,p1,p2,p3,rename_table,reasoning,
sensitivities}.json.

Definitions (pre-registered):
- VALID: compiled, SEL-OR completed without exception or shape error, probe errors on <= 1% of states.
- class: argmax over {BF, FF, WF, AWF, LF} of A_c if >= 0.95; else RF if STOCHASTIC and RF-matched; else 'other'.
- mechanistic compliance under banned set B: VALID, A_c < 0.95 for every deterministic c in B, no RF match if RF in B.
- lexical compliance L1: no alias of a banned rule anywhere in the extracted program (code, comments, docstrings).
- banned set: NAME_k -> B_k (top k of the model's BASE frequency order); HOLD_5 -> B_5; DESC_5 -> S_desc (primary)
  and B_5 (sensitivity); BASE and INSTR cells are scored against B_5 descriptively.
- P1 (per model): (a) L1 >= 0.7 and mech >= 0.7 at k = 1; (b) one-sided Jonckheere-Terpstra (decreasing) on the
  mech flags of VALID NAME_1..NAME_5 programs, p_perm < 0.05; (c) L1 >= 0.7 at every k; (d) NAME_5 gap
  (L1 - mech, paired) >= 0.3 with paired Newcombe lower bound > 0; (e) the same on HOLD_5.
  SUPPORTED iff (a) in every run model and each of (b)-(e) in >= 2 run models; DISCONFIRMED iff |L1 - mech| <= 0.1
  at every k in every run model; otherwise PARTIAL (failing parts named).
- P2 (per model): DESC_5 minus NAME_5 mech compliance (both scored against S_desc), unpaired Newcombe interval.
  SUPPORTED iff diff >= 0.2 with lower bound > 0 in >= 2 run models; DISCONFIRMED iff diff <= 0 in >= 2 run
  models; otherwise PARTIAL.
- P3 (per cell): share (of all N) of samples VALID, better than 0.8 x BF on both H-OR3 (<= 4.294%) and H-FSW5k
  (<= 3.187%), novel (maximum corpus agreement < 0.9) and confirmed NOVEL by the S11 audit; SUPPORTED iff every run
  cell <= 0.02 (Clopper-Pearson bound beside it).
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any

import numpy as np
from loguru import logger

import stats
from common import DATA, PRED, RESULTS, read_json, read_jsonl, write_json

CLASS_T = 0.95
SENS_T = (0.90, 0.98)
NOVEL_T = 0.90
HO_OR3_T = 4.294
HO_W5K_T = 3.187
QUALITY_F = 1.1
P1A_T = 0.7
P1C_T = 0.7
P1D_GAP = 0.3
P1_DISC = 0.1
P2_DIFF = 0.2
P3_CAP = 0.02
JT_ALPHA = 0.05
DET = ["BF", "FF", "WF", "AWF", "LF"]
CAT = ["BF", "FF", "WF", "AWF", "LF", "RF"]
FALLBACK = ["BF", "FF", "WF", "AWF", "LF", "RF"]
NAME_CELLS = ["NAME_1", "NAME_2", "NAME_3", "NAME_4", "NAME_5"]
UNDERPOWERED_VALID = 20


# ---------------------------------------------------------------------------------------------- per-row helpers
def row_class(r: dict[str, Any], t: float = CLASS_T, informative: bool = False) -> str:
    if not r.get("valid"):
        return "invalid"
    A = r["A_inf"] if informative else r["A"]
    best = max(DET, key=lambda c: (A[c], -DET.index(c)))
    if A[best] >= t:
        return best
    if r.get("stochastic") and r.get("rf_match"):
        return "RF"
    return "other"


def mech(r: dict[str, Any], banned: list[str], t: float = CLASS_T, informative: bool = False) -> bool:
    if not r.get("valid"):
        return False
    A = r["A_inf"] if informative else r["A"]
    for c in banned:
        if c == "RF":
            if r.get("stochastic") and r.get("rf_match"):
                return False
        elif A[c] >= t:
            return False
    return True


def lex(r: dict[str, Any], banned: list[str], which: str = "L1") -> bool:
    key = {"L1": "hits_program", "L2": "hits_program_nonneg", "L_text": "hits_text", "L_reason": "hits_reason"}[which]
    return not (set(r.get(key) or []) & set(banned))


def max_agree_banned(r: dict[str, Any], banned: list[str]) -> float | None:
    vals = [r["A"][c] for c in banned if c != "RF"]
    return max(vals) if (vals and r.get("valid")) else None


def better(r: dict[str, Any]) -> bool:
    return bool(r.get("valid") and r.get("h_or3_excess") is not None and r["h_or3_excess"] <= HO_OR3_T and
                r.get("h_fsw5k_excess") is not None and r["h_fsw5k_excess"] <= HO_W5K_T)


def novel(r: dict[str, Any]) -> bool:
    return bool(r.get("valid") and r.get("corpus_max_agree") is not None and r["corpus_max_agree"] < NOVEL_T and
                row_class(r) == "other")


# ---------------------------------------------------------------------------------------------- orders
def frequency_order(base_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Order over {BF, FF, WF, AWF, LF, RF} among VALID BASE programs by count; ties and zero counts follow the
    fallback order BF, FF, WF, AWF, LF, RF."""
    cnt = Counter(row_class(r) for r in base_rows if r.get("valid"))
    order = sorted(CAT, key=lambda c: (-cnt.get(c, 0), FALLBACK.index(c)))
    return {"order": order, "counts": {c: cnt.get(c, 0) for c in CAT}, "other": cnt.get("other", 0),
            "n_valid": sum(1 for r in base_rows if r.get("valid")), "n": len(base_rows),
            "B": {k: order[:k] for k in range(1, 6)}, "all_fallback": all(cnt.get(c, 0) == 0 for c in CAT)}


def load_orders() -> dict[str, dict[str, Any]]:
    out = {}
    for p in sorted(PRED.glob("commit2_*.json")):
        d = read_json(p)
        out[d["model"]] = d
    return out


def banned_for(cell: str, order: dict[str, Any], sens_desc_b5: bool = False) -> list[str]:
    B = order["B"]
    if cell.startswith("NAME_"):
        return B[str(int(cell.split("_")[1]))] if isinstance(next(iter(B)), str) else B[int(cell.split("_")[1])]
    b5 = B["5"] if "5" in B else B[5]
    if cell == "DESC_5" and not sens_desc_b5:
        return list(order.get("S_desc", b5))
    return list(b5)


# ---------------------------------------------------------------------------------------------- cells
def cell_summary(rows: list[dict[str, Any]], banned: list[str], t: float = CLASS_T, informative: bool = False,
                 lexflag: str = "L1", denom: str = "valid") -> dict[str, Any]:
    n = len(rows)
    vrows = [r for r in rows if r.get("valid")]
    if denom == "valid_full":
        vrows = [r for r in vrows if r.get("valid_full")]
    nv = len(vrows)
    lx = sum(lex(r, banned, lexflag) for r in vrows)
    mc = sum(mech(r, banned, t, informative) for r in vrows)
    lx_all = sum(1 for r in rows if r.get("valid") and lex(r, banned, lexflag))
    mc_all = sum(1 for r in rows if mech(r, banned, t, informative))
    comp = Counter(row_class(r, t, informative) for r in rows)
    hist = Counter()
    for r in vrows:
        m = max_agree_banned(r, banned)
        if m is not None:
            hist[f"{min(19, int(m * 20)) / 20:.2f}"] += 1
    compliant = [r for r in vrows if mech(r, banned, t, informative)]
    q_eval = [r for r in compliant if r.get("quality") is not None]
    a, b, c, d = paired_cells(vrows, banned, t, informative, lexflag)
    return {"N": n, "VALID": nv, "truncated": sum(1 for r in rows if r.get("truncated")),
            "underpowered": nv < UNDERPOWERED_VALID, "banned": banned,
            "L1_valid": stats.rate(lx, nv), "mech_valid": stats.rate(mc, nv),
            "lex_all": stats.rate(lx_all, n), "mech_all": stats.rate(mc_all, n),
            "gap_valid": (lx - mc) / nv if nv else None, "paired_cells_abcd": [a, b, c, d],
            "class_composition": dict(comp), "max_agree_banned_hist": dict(sorted(hist.items())),
            "quality_among_mech_compliant": {"k": sum(1 for r in q_eval if r["quality"]), "n_evaluated": len(q_eval),
                                             "n_compliant": len(compliant)},
            "valid_rate": stats.rate(nv, n)}


def paired_cells(vrows: list[dict[str, Any]], banned: list[str], t: float = CLASS_T, informative: bool = False,
                 lexflag: str = "L1") -> tuple[int, int, int, int]:
    a = b = c = d = 0
    for r in vrows:
        lx, mc = lex(r, banned, lexflag), mech(r, banned, t, informative)
        if lx and mc:
            a += 1
        elif lx:
            b += 1
        elif mc:
            c += 1
        else:
            d += 1
    return a, b, c, d


def per_template(rows: list[dict[str, Any]], banned: list[str]) -> dict[str, Any]:
    by = defaultdict(list)
    for r in rows:
        if r.get("valid") and r.get("template"):
            by[r["template"]].append(r)
    out = {}
    tab_l, tab_m = [], []
    for w in sorted(by):
        rs = by[w]
        lx = sum(lex(r, banned) for r in rs)
        mc = sum(mech(r, banned) for r in rs)
        out[w] = {"n_valid": len(rs), "L1": stats.rate(lx, len(rs)), "mech": stats.rate(mc, len(rs))}
        tab_l.append([lx, len(rs) - lx])
        tab_m.append([mc, len(rs) - mc])
    return {"templates": out, "fisher_p_L1": stats.fisher_rxc_or_2x2(tab_l) if len(tab_l) >= 2 else None,
            "fisher_p_mech": stats.fisher_rxc_or_2x2(tab_m) if len(tab_m) >= 2 else None}


def gap_test(vrows: list[dict[str, Any]], banned: list[str], t: float = CLASS_T, informative: bool = False,
             lexflag: str = "L1") -> dict[str, Any]:
    a, b, c, d = paired_cells(vrows, banned, t, informative, lexflag)
    n = a + b + c + d
    if n == 0:
        return {"n": 0, "holds": False}
    gap, lo, hi = stats.newcombe_paired(a, b, c, d)
    _, ulo, uhi = stats.newcombe_unpaired(a + b, n, a + c, n)
    x1 = [1] * a + [1] * b + [0] * c + [0] * d
    x2 = [1] * a + [0] * b + [1] * c + [0] * d
    _, blo, bhi = stats.paired_bootstrap_gap(x1, x2, B=10_000)
    return {"n": n, "cells_abcd": [a, b, c, d], "L1": (a + b) / n, "mech": (a + c) / n, "gap": gap,
            "paired_newcombe95": [lo, hi], "unpaired_newcombe95": [ulo, uhi], "paired_bootstrap95": [blo, bhi],
            "holds": bool(gap >= P1D_GAP and lo > 0)}


# ---------------------------------------------------------------------------------------------- P1/P2/P3
def p1_model(rows_by_cell: dict[str, list[dict[str, Any]]], order: dict[str, Any], t: float = CLASS_T,
             informative: bool = False, lexflag: str = "L1", denom: str = "valid") -> dict[str, Any]:
    def vr(cell):
        rs = [r for r in rows_by_cell.get(cell, []) if r.get("valid")]
        return [r for r in rs if r.get("valid_full")] if denom == "valid_full" else rs
    out: dict[str, Any] = {}
    B1 = banned_for("NAME_1", order)
    v1 = vr("NAME_1")
    l1 = sum(lex(r, B1, lexflag) for r in v1) / len(v1) if v1 else None
    m1 = sum(mech(r, B1, t, informative) for r in v1) / len(v1) if v1 else None
    out["a"] = {"L1": l1, "mech": m1, "n_valid": len(v1),
                "holds": bool(l1 is not None and l1 >= P1A_T and m1 >= P1A_T)}
    groups = []
    per_k = {}
    for k, cell in enumerate(NAME_CELLS, 1):
        Bk = banned_for(cell, order)
        rs = vr(cell)
        g = [int(mech(r, Bk, t, informative)) for r in rs]
        groups.append(g)
        lx = sum(lex(r, Bk, lexflag) for r in rs)
        per_k[k] = {"n_valid": len(rs), "L1": lx / len(rs) if rs else None,
                    "mech": sum(g) / len(rs) if rs else None,
                    "abs_diff": abs(lx - sum(g)) / len(rs) if rs else None}
    present = [g for g in groups if len(g) > 0]
    jt = stats.jt_test(groups, n_perm=100_000, seed=20261026) if len(present) >= 2 else {"p_perm": None}
    out["b"] = {"jt": jt, "holds": bool(jt.get("p_perm") is not None and jt["p_perm"] < JT_ALPHA)}
    out["c"] = {"L1_by_k": {k: v["L1"] for k, v in per_k.items()},
                "holds": bool(all(v["L1"] is not None and v["L1"] >= P1C_T for v in per_k.values()))}
    out["d"] = gap_test(vr("NAME_5"), banned_for("NAME_5", order), t, informative, lexflag)
    out["e"] = gap_test(vr("HOLD_5"), banned_for("HOLD_5", order), t, informative, lexflag) \
        if rows_by_cell.get("HOLD_5") else {"n": 0, "holds": False, "not_run": True}
    out["per_k"] = per_k
    out["disconfirm_all_k_within_0.1"] = bool(all(v["abs_diff"] is not None and v["abs_diff"] <= P1_DISC
                                                  for v in per_k.values()))
    return out


def p1_verdict(per_model: dict[str, dict[str, Any]]) -> dict[str, Any]:
    run = [m for m, v in per_model.items() if v["a"]["n_valid"] > 0]
    if not run:
        return {"verdict": "NOT_RUN", "run_models": []}
    a_all = all(per_model[m]["a"]["holds"] for m in run)
    cnt = {p: sum(per_model[m][p]["holds"] for m in run) for p in "bcde"}
    if a_all and all(cnt[p] >= 2 for p in "bcde"):
        v = "SUPPORTED"
    elif all(per_model[m]["disconfirm_all_k_within_0.1"] for m in run):
        v = "DISCONFIRMED"
    else:
        v = "PARTIAL"
    failing = ([] if a_all else ["a (not in every run model)"]) + [f"{p} (holds in {cnt[p]} of {len(run)})"
                                                                     for p in "bcde" if cnt[p] < 2]
    return {"verdict": v, "run_models": run, "a_in_every_model": a_all, "count_holding": cnt,
            "failing_parts": failing, "reduced_panel": len(run) < 3}


def p2_model(rows_by_cell: dict[str, list[dict[str, Any]]], order: dict[str, Any], against: str = "S_desc",
             t: float = CLASS_T) -> dict[str, Any]:
    B = list(order.get("S_desc", [])) if against == "S_desc" else banned_for("HOLD_5", order)
    if not B:
        return {"n_desc": 0, "n_name": 0, "holds": False, "disconfirms": False, "note": "S_desc empty"}
    vd = [r for r in rows_by_cell.get("DESC_5", []) if r.get("valid")]
    vn = [r for r in rows_by_cell.get("NAME_5", []) if r.get("valid")]
    kd = sum(mech(r, B, t) for r in vd)
    kn = sum(mech(r, B, t) for r in vn)
    if not vd or not vn:
        return {"n_desc": len(vd), "n_name": len(vn), "holds": False, "disconfirms": False, "banned": B}
    d, lo, hi = stats.newcombe_unpaired(kd, len(vd), kn, len(vn))
    try:
        from statsmodels.stats.proportion import confint_proportions_2indep
        slo, shi = confint_proportions_2indep(kd, len(vd), kn, len(vn), method="newcomb", compare="diff")
        sm = [float(slo), float(shi)]
    except (ImportError, ValueError):
        sm = None
    return {"banned": B, "n_desc": len(vd), "n_name": len(vn), "mech_desc": kd / len(vd), "mech_name": kn / len(vn),
            "diff": d, "newcombe95": [lo, hi], "statsmodels_newcomb95": sm, "holds": bool(d >= P2_DIFF and lo > 0),
            "disconfirms": bool(d <= 0)}


def p2_verdict(per_model: dict[str, dict[str, Any]]) -> dict[str, Any]:
    run = [m for m, v in per_model.items() if v.get("n_desc", 0) > 0 and v.get("n_name", 0) > 0]
    h = sum(per_model[m]["holds"] for m in run)
    dz = sum(per_model[m]["disconfirms"] for m in run)
    v = "SUPPORTED" if h >= 2 else ("DISCONFIRMED" if dz >= 2 else ("PARTIAL" if run else "NOT_RUN"))
    return {"verdict": v, "run_models": run, "n_holding": h, "n_disconfirming": dz, "reduced_panel": len(run) < 3}


def p3_cells(rows_by_mc: dict[tuple[str, str], list[dict[str, Any]]], audit: dict[str, Any]) -> dict[str, Any]:
    confirmed = set(audit.get("confirmed_novel_ids", []))
    cells = {}
    for (m, c), rs in sorted(rows_by_mc.items()):
        n = len(rs)
        cand = [r for r in rs if better(r) and novel(r)]
        conf = [r for r in cand if r["row_id"] in confirmed]
        cp = stats.clopper_pearson(len(conf), n)
        cells[f"{m}|{c}"] = {"N": n, "candidates": len(cand), "confirmed": len(conf), "share": len(conf) / n if n
                             else None, "clopper_pearson": cp,
                             "share_better_regardless": sum(better(r) for r in rs) / n if n else None,
                             "share_novel_regardless": sum(novel(r) for r in rs) / n if n else None,
                             "n_heldout_or3_evaluated": sum(1 for r in rs if r.get("h_or3_excess") is not None),
                             "holds": bool(n and len(conf) / n <= P3_CAP), "candidate_ids": [r["row_id"] for r in
                                                                                             cand]}
    run = [k for k, v in cells.items() if v["N"] > 0]
    verdict = "SUPPORTED" if run and all(cells[k]["holds"] for k in run) else ("NOT_SUPPORTED" if run else "NOT_RUN")
    return {"verdict": verdict, "cells": cells, "rule": "SUPPORTED iff every run cell has a confirmed-novel-and-"
            "better share <= 0.02"}


# ---------------------------------------------------------------------------------------------- rename + reasoning
def rename_table(rows_by_mc: dict[tuple[str, str], list[dict[str, Any]]], orders: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for (m, c), rs in sorted(rows_by_mc.items()):
        if m not in orders:
            continue
        if c.startswith("NAME_") or c in ("HOLD_5", "DESC_5"):
            B = banned_for(c, orders[m])
            lexc = [r for r in rs if r.get("valid") and lex(r, B)]
            tab: dict[str, Counter] = defaultdict(Counter)
            for r in lexc:
                cls = row_class(r)
                grp = "banned_rule" if cls in B else ("RF" if cls == "RF" else ("non_banned_catalogue" if cls in CAT
                                                                                else "other"))
                tab[grp][r.get("syn_category") or "none"] += 1
            nonc = sum(1 for r in lexc if not mech(r, B))
            examples = [{"row_id": r["row_id"], "class": row_class(r), "syn": r.get("synonyms"),
                         "max_agree_banned": max_agree_banned(r, B)} for r in lexc if not mech(r, B)][:8]
            out[f"{m}|{c}"] = {"banned": B, "n_lex_compliant_valid": len(lexc), "n_mech_noncompliant": nonc,
                               "rename_rate": nonc / len(lexc) if lexc else None,
                               "rename_rate_wilson95": stats.wilson(nonc, len(lexc)) if lexc else None,
                               "table": {k: dict(v) for k, v in tab.items()}, "examples": examples}
        elif c.startswith("INSTR"):
            v = [r for r in rs if r.get("valid")]
            claim = [r for r in v if r.get("claims_novelty")]
            known = [r for r in claim if row_class(r) in CAT or (r.get("corpus_max_agree") or 0) >= NOVEL_T]
            out[f"{m}|{c}"] = {"n_valid": len(v), "n_claim_novelty": len(claim), "n_claim_but_known": len(known),
                               "share_claim_but_known": len(known) / len(claim) if claim else None,
                               "class_composition": dict(Counter(row_class(r) for r in v))}
    return out


def reasoning_table(rows_by_mc: dict[tuple[str, str], list[dict[str, Any]]], orders: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for (m, c), rs in sorted(rows_by_mc.items()):
        if m == "q8" or m not in orders:
            continue
        B = banned_for(c, orders[m]) if c != "BASE" else orders[m]["B"]["5"] if "5" in orders[m]["B"] else \
            orders[m]["B"][5]
        tr = [r for r in rs if r.get("reasoning_present")]
        men = sum(1 for r in tr if set(r.get("hits_reason") or []) & set(B))
        sid = sum(1 for r in tr if r.get("self_id_rules") and set(r["self_id_rules"]) & set(B))
        toks = [r.get("reasoning_tokens") or 0 for r in rs]
        out[f"{m}|{c}"] = {"n": len(rs), "n_traces": len(tr), "share_mention_banned": men / len(tr) if tr else None,
                           "share_self_identification": sid / len(tr) if tr else None,
                           "median_reasoning_tokens": float(np.median(toks)) if toks else None,
                           "truncation_rate": sum(1 for r in rs if r.get("truncated")) / len(rs) if rs else None,
                           "banned": B}
    return out


# ---------------------------------------------------------------------------------------------- driver
def load_rows() -> list[dict[str, Any]]:
    rows = read_jsonl(DATA / "eval_rows.jsonl")
    last: dict[str, dict[str, Any]] = {}
    for r in rows:                         # later rows (held-out / quality updates) supersede earlier ones
        last[r["row_id"]] = {**last.get(r["row_id"], {}), **r}
    return list(last.values())


def run_all() -> dict[str, Any]:
    rows = load_rows()
    orders = load_orders()
    audit = read_json(RESULTS / "p3_audit.json") if (RESULTS / "p3_audit.json").exists() else {}
    by_mc: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_mc[(r["model"], r["cell"])].append(r)
    models = sorted({m for m, _ in by_mc})
    cells = {}
    for (m, c), rs in sorted(by_mc.items()):
        if m in orders:
            B = banned_for(c, orders[m]) if c not in ("BASE",) and not c.startswith("INSTR") else \
                banned_for("HOLD_5", orders[m])
        else:
            B = []
        s = cell_summary(rs, B)
        s["per_template"] = per_template(rs, B)
        if c == "DESC_5" and m in orders:
            s["sensitivity_vs_B5"] = cell_summary(rs, banned_for("HOLD_5", orders[m]))
        cells[f"{m}|{c}"] = s
    write_json(RESULTS / "cells.json", cells)
    p1 = {}
    p2 = {}
    p2s = {}
    for m in models:
        if m not in orders:
            continue
        rbc = {c: rs for (mm, c), rs in by_mc.items() if mm == m}
        p1[m] = p1_model(rbc, orders[m])
        p2[m] = p2_model(rbc, orders[m], "S_desc")
        p2s[m] = p2_model(rbc, orders[m], "B5")
    holm = stats.holm({m: v["b"]["jt"].get("p_perm") for m, v in p1.items()})
    p1_out = {"per_model": p1, "verdict": p1_verdict(p1), "holm_jt": holm}
    write_json(RESULTS / "p1.json", p1_out)
    p2_out = {"per_model": p2, "verdict": p2_verdict(p2), "sensitivity_vs_B5": {"per_model": p2s,
                                                                               "verdict": p2_verdict(p2s)}}
    write_json(RESULTS / "p2.json", p2_out)
    p3 = p3_cells(by_mc, audit)
    write_json(RESULTS / "p3.json", p3)
    write_json(RESULTS / "rename_table.json", rename_table(by_mc, orders))
    write_json(RESULTS / "reasoning.json", reasoning_table(by_mc, orders))
    # sensitivities
    sens: dict[str, Any] = {}
    for m in models:
        if m not in orders:
            continue
        rbc = {c: rs for (mm, c), rs in by_mc.items() if mm == m}
        sens[m] = {f"t{t}": summarise_p1(p1_model(rbc, orders[m], t=t)) for t in SENS_T}
        sens[m]["informative_only"] = summarise_p1(p1_model(rbc, orders[m], informative=True))
        sens[m]["L2"] = summarise_p1(p1_model(rbc, orders[m], lexflag="L2"))
        sens[m]["valid_full_denominator"] = summarise_p1(p1_model(rbc, orders[m], denom="valid_full"))
        prov = Counter(r.get("provider") for rs in rbc.values() for r in rs)
        sens[m]["providers"] = dict(prov)
    sens["verdict_t0.90"] = p1_verdict({m: p1_model({c: rs for (mm, c), rs in by_mc.items() if mm == m}, orders[m],
                                                    t=0.90) for m in models if m in orders})
    sens["verdict_t0.98"] = p1_verdict({m: p1_model({c: rs for (mm, c), rs in by_mc.items() if mm == m}, orders[m],
                                                    t=0.98) for m in models if m in orders})
    sens["verdict_informative"] = p1_verdict({m: p1_model({c: rs for (mm, c), rs in by_mc.items() if mm == m},
                                                          orders[m], informative=True) for m in models if m in orders})
    write_json(RESULTS / "sensitivities.json", sens)
    logger.info(f"P1 {p1_out['verdict']['verdict']}  P2 {p2_out['verdict']['verdict']}  P3 {p3['verdict']}")
    return {"p1": p1_out["verdict"], "p2": p2_out["verdict"], "p3": p3["verdict"]}


def summarise_p1(p: dict[str, Any]) -> dict[str, Any]:
    return {"a": p["a"], "b_p": p["b"]["jt"].get("p_perm"), "b_holds": p["b"]["holds"], "c": p["c"],
            "d_gap": p["d"].get("gap"), "d_ci": p["d"].get("paired_newcombe95"), "d_holds": p["d"]["holds"],
            "e_gap": p["e"].get("gap"), "e_ci": p["e"].get("paired_newcombe95"), "e_holds": p["e"]["holds"],
            "per_k": p["per_k"]}


def _finite(x: Any) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(x)
