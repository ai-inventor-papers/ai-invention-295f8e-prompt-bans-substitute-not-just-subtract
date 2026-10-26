#!/usr/bin/env python3
"""Stage 5 analyses (committed in commit #1b; plan 2.3-2.5 and 5.1-5.5). Pure functions over row dicts.

Row fields used: config, cell, k, banned_set, lexical_L1, lexical_L2, trace_alias_hits, order_class,
order_class_fine, fifo_flag, ds_signature, passed, label, label_other_name, truncated, has_code, source, cap.
"""

from __future__ import annotations

import itertools
import math
import re
from collections import Counter, defaultdict
from typing import Any, Iterable

import numpy as np

import stats_v9 as S
from common import CANON_ORDER, K_ORDER, LITERAL5, wilson_ci

MECH_COARSE = {"bfs": "BFS", "dfs": "DFS", "iddfs": "ID", "astar": "HEUR", "gbfs": "HEUR", "bibfs": "BIDIR",
               "biastar": "BIDIR", "idastar": "ID", "jps": "HEUR", "dijkstra_unit": "BFS"}
MECH_FINE = {"bfs": "BFS", "dfs": "DFS", "iddfs": "ID-depth", "astar": "HEUR-f", "gbfs": "HEUR-h",
             "bibfs": "BIDIR-BFS", "biastar": "BIDIR-heuristic", "idastar": "ID-f", "jps": "HEUR-jump",
             "dijkstra_unit": "BFS"}
UNKNOWN_NAMES = {"", "unknown", "none", "null", "n/a"}
BFS_BY_DEFINITION_RX = re.compile(r"spfa|wave[-_ ]?front|flood|\blee\b|uniform[-_ ]?cost", re.IGNORECASE)


def coarse_banned(banned: Iterable[str]) -> set[str]:
    return {MECH_COARSE[b] for b in banned}


def fine_banned(banned: Iterable[str]) -> set[str]:
    s = {MECH_FINE[b] for b in banned}
    if "DFS" in s:
        s.add("DFS-revisit")
    return s


MECH_FIELD = "order_class"     # the tracer v9 class; the gate-failure fallback switches this to "runtime_class"


def runtime_class(r: dict[str, Any]) -> str:
    """Fallback mechanism label (plan): the iteration-8 10-class runtime label mapped through the 1.11 coarse table."""
    lab = r.get("runtime_label")
    if not r.get("has_code") or lab in (None, "invalid"):
        return "UNTRACEABLE"
    return MECH_COARSE.get(lab, "OTHER")


def _mech(r: dict[str, Any]) -> str | None:
    return runtime_class(r) if MECH_FIELD == "runtime_class" else r.get("order_class")


def traceable(r: dict[str, Any]) -> bool:
    return _mech(r) not in (None, "UNTRACEABLE")


def mech_ok(r: dict[str, Any], banned: Iterable[str], fine: bool = False) -> bool:
    if fine and MECH_FIELD == "order_class":
        return r.get("order_class_fine") not in fine_banned(banned)
    return _mech(r) not in coarse_banned(banned)


def named_survivor(r: dict[str, Any], banned: Iterable[str]) -> bool:
    """Name-level correct survivor: passes the 48-case suite AND its adjudicated algorithm (catalogue, or a named
    known algorithm outside the catalogue) is not banned."""
    if not r.get("passed"):
        return False
    lab = r.get("label")
    if lab in (None, "invalid", "no_code"):
        return False
    if lab in banned:
        return False
    if lab == "other":
        return str(r.get("label_other_name") or "").strip().lower() not in UNKNOWN_NAMES
    return True


def mech_survivor(r: dict[str, Any], banned: Iterable[str]) -> bool:
    return bool(r.get("passed")) and traceable(r) and mech_ok(r, banned)


def table2x2(rows: list[dict[str, Any]], banned: list[str], lex_key: str = "lexical_L1", fine: bool = False,
             untraceable_as: bool | None = None) -> dict[str, Any]:
    """2x2 of lexical (L1/L2 compliant) x mechanistic compliance over traceable programs (untraceable_as: count
    untraceable programs WITH code as mechanistically compliant (True) / non-compliant (False))."""
    a = b = c = d = 0
    for r in rows:
        if not r.get("has_code"):
            continue
        if traceable(r):
            m = mech_ok(r, banned, fine)
        elif untraceable_as is None:
            continue
        else:
            m = untraceable_as
        lx = bool(r.get(lex_key))
        if lx and m:
            a += 1
        elif lx and not m:
            b += 1
        elif not lx and m:
            c += 1
        else:
            d += 1
    n = a + b + c + d
    D, lo, hi = S.newcombe_paired(a, b, c, d)
    return {"a_lex_mech": a, "b_lex_notmech": b, "c_notlex_mech": c, "d_neither": d, "n": n,
            "lex": (a + b) / n if n else None, "mech": (a + c) / n if n else None, "gap": D if n else None,
            "gap_newcombe95": [lo, hi] if n else None, "mcnemar_p": S.mcnemar_exact(b, c),
            "covert_reimpl_share": b / n if n else None}


# ---------------------------------------------------------------------------------------------- N1
def n1(rows_by_config: dict[str, list[dict[str, Any]]], with_reasoning: tuple[str, ...] = ("C1", "C4", "C6")
       ) -> dict[str, Any]:
    out: dict[str, Any] = {"per_config": {}}
    gaps = []
    for cfg, rows in rows_by_config.items():
        banned = list(LITERAL5)
        t = table2x2(rows, banned)
        t["n_rows"] = len(rows)
        t["n_with_code"] = sum(1 for r in rows if r.get("has_code"))
        t["n_untraceable"] = sum(1 for r in rows if r.get("has_code") and not traceable(r))
        t["untraceable_reasons"] = dict(Counter(str(r.get("trace_reason")) for r in rows
                                                if r.get("has_code") and not traceable(r)))
        t["order_classes"] = dict(Counter(r.get("order_class") for r in rows if r.get("has_code")))
        t["order_classes_fine"] = dict(Counter(r.get("order_class_fine") for r in rows if r.get("has_code")))
        if cfg in with_reasoning:
            cov = [r for r in rows if r.get("has_code") and traceable(r) and r.get("lexical_L1")
                   and not mech_ok(r, banned)]
            t["knowing_rename_share"] = (sum(1 for r in cov if (r.get("trace_alias_hits") or 0) > 0) / len(cov)
                                         if cov else None)
            t["knowing_rename_n"] = len(cov)
        t["sens_L2"] = table2x2(rows, banned, "lexical_L2")
        t["sens_fine"] = table2x2(rows, banned, fine=True)
        t["sens_untraceable_compliant"] = table2x2(rows, banned, untraceable_as=True)
        t["sens_untraceable_noncompliant"] = table2x2(rows, banned, untraceable_as=False)
        out["per_config"][cfg] = t
        if t["gap"] is not None:
            gaps.append(t["gap"])
    pooled, lo, hi = S.cluster_bootstrap_mean(gaps, B=10_000, seed=0)
    tot = [out["per_config"][c] for c in out["per_config"]]
    nb = sum(t["b_lex_notmech"] for t in tot)
    nc = sum(t["c_notlex_mech"] for t in tot)
    nn = sum(t["n"] for t in tot)
    out["pooled_equal_weight"] = pooled
    out["pooled_bootstrap95"] = [lo, hi]
    out["pooled_program_weighted"] = (nb - nc) / nn if nn else None
    out["n_configs"] = len(gaps)
    out["n_positive"] = sum(1 for g in gaps if g > 0)
    need = math.ceil(0.7 * len(gaps))
    out["positive_needed"] = need
    if pooled >= 0.3 and out["n_positive"] >= need:
        out["verdict"] = "SUPPORTED"
    elif pooled < 0.1:
        out["verdict"] = "DISCONFIRMED"
    else:
        out["verdict"] = "NOT SUPPORTED (between the bars)"
    for sk in ("sens_L2", "sens_fine", "sens_untraceable_compliant", "sens_untraceable_noncompliant"):
        g = [out["per_config"][c][sk]["gap"] for c in out["per_config"] if out["per_config"][c][sk]["gap"] is not None]
        out[f"pooled_{sk}"] = float(np.mean(g)) if g else None
    return out


# ---------------------------------------------------------------------------------------------- N2
def n2(survivors: list[dict[str, Any]]) -> dict[str, Any]:
    banned = list(LITERAL5)
    cb, fb = coarse_banned(banned), fine_banned(banned)
    tr = [r for r in survivors if traceable(r)]

    def share(rows: list[dict[str, Any]], fine: bool = False) -> dict[str, Any]:
        k = sum(1 for r in rows if (r.get("order_class_fine") in fb if fine else _mech(r) in cb))
        n = len(rows)
        lo, hi = wilson_ci(k, n) if n else (None, None)
        return {"k": k, "n": n, "share": k / n if n else None, "wilson95": [lo, hi]}

    def by_def(r: dict[str, Any]) -> bool:
        if r.get("label") == "dijkstra_unit":
            return True
        nm = str(r.get("label_other_name") or "")
        if BFS_BY_DEFINITION_RX.search(nm):
            return True
        if re.search(r"bellman", nm, re.IGNORECASE) and (r.get("ds_signature") or {}).get("container") == "FIFO":
            return True
        return False

    a = share(tr)
    sub_b = [r for r in tr if not by_def(r)]
    b = share(sub_b)
    fine_a = share(tr, fine=True)
    out = {"n_survivors": len(survivors), "n_traceable": len(tr),
           "untraceable": [r.get("uid") for r in survivors if not traceable(r)],
           "a_all": a, "b_not_bfs_by_definition": b, "fine_all": fine_a,
           "null_coarse": 0.6, "null_fine": 0.2,
           "adj_coarse": None if a["share"] is None else {"diff": a["share"] - 0.6,
                                                         "wilson95_shifted": [a["wilson95"][0] - 0.6,
                                                                              a["wilson95"][1] - 0.6]},
           "adj_fine": None if fine_a["share"] is None else {"diff": fine_a["share"] - 0.2,
                                                            "wilson95_shifted": [fine_a["wilson95"][0] - 0.2,
                                                                                 fine_a["wilson95"][1] - 0.2]}}
    out["by_source"] = {}
    for src in sorted({r.get("source") for r in tr}):
        rows = [r for r in tr if r.get("source") == src]
        out["by_source"][src] = {"coarse": share(rows), "b": share([r for r in rows if not by_def(r)]),
                                 "cap": sorted({r.get("cap") for r in rows})}
    out["classes"] = dict(Counter(r.get("order_class") for r in tr))
    out["classes_fine"] = dict(Counter(r.get("order_class_fine") for r in tr))
    out["exact_fifo_bfs_renamed"] = sum(1 for r in tr if _mech(r) == "BFS" and r.get("fifo_flag"))
    out["exact_fifo_bfs_share"] = out["exact_fifo_bfs_renamed"] / len(tr) if tr else None
    out["mech_field"] = MECH_FIELD
    out["per_survivor"] = [{"uid": r.get("uid"), "source": r.get("source"), "label": r.get("label"),
                            "other_name": r.get("label_other_name"), "order_class": _mech(r),
                            "tracer_class": r.get("order_class"), "runtime_class": runtime_class(r),
                            "fine": r.get("order_class_fine"), "fifo": r.get("fifo_flag"),
                            "container": (r.get("ds_signature") or {}).get("container"),
                            "key": (r.get("ds_signature") or {}).get("key"),
                            "relaxation": (r.get("ds_signature") or {}).get("relaxation"),
                            "bfs_by_definition": by_def(r)} for r in survivors]
    sh = a["share"]
    if sh is None:
        out["verdict"] = "UNDEFINED (no traceable survivors)"
    elif sh >= 0.6:
        out["verdict"] = "SUPPORTED"
    elif sh <= 0.3:
        out["verdict"] = "DISCONFIRMED"
    else:
        out["verdict"] = "NOT SUPPORTED (between the bars)"
    out["exceeds_null"] = bool(sh is not None and a["wilson95"][0] > 0.6)
    return out


# ---------------------------------------------------------------------------------------------- N3
def _completed(r: dict[str, Any]) -> bool:
    return bool(r.get("has_code")) and not r.get("truncated")


def cell_summary(rows: list[dict[str, Any]], banned: list[str]) -> dict[str, Any]:
    comp = [r for r in rows if _completed(r)]
    tr = [r for r in comp if traceable(r)]
    n_all = len(rows)
    lex_c = sum(1 for r in comp if r.get("lexical_L1"))
    lex2_c = sum(1 for r in comp if r.get("lexical_L2"))
    mech_c = sum(1 for r in tr if mech_ok(r, banned))
    mechf_c = sum(1 for r in tr if mech_ok(r, banned, fine=True))
    t = table2x2(comp, banned)
    t2 = table2x2(comp, banned, "lexical_L2")
    tf = table2x2(comp, banned, fine=True)
    return {"n": n_all, "n_completed": len(comp), "n_traceable": len(tr),
            "truncation_rate": sum(1 for r in rows if r.get("truncated")) / n_all if n_all else None,
            "pass_rate": sum(1 for r in rows if r.get("passed")) / n_all if n_all else None,
            "lex_L1_completed": S.rate(lex_c, len(comp)), "lex_L2_completed": S.rate(lex2_c, len(comp)),
            "mech_coarse_traceable": S.rate(mech_c, len(tr)), "mech_fine_traceable": S.rate(mechf_c, len(tr)),
            "lex_L1_all": S.rate(lex_c, n_all), "mech_coarse_all": S.rate(mech_c, n_all),
            "named_survivors": S.rate(sum(1 for r in rows if named_survivor(r, banned)), n_all),
            "mech_survivors": S.rate(sum(1 for r in rows if mech_survivor(r, banned)), n_all),
            "gap_L1": t, "gap_L2": t2, "gap_fine": tf,
            "order_classes": dict(Counter(r.get("order_class") for r in comp)),
            "labels": dict(Counter(r.get("label") for r in rows)),
            "templates": sorted({r.get("template") for r in rows})}


def n3(cells: dict[int, list[dict[str, Any]]], heldout: list[dict[str, Any]] | None) -> dict[str, Any]:
    out: dict[str, Any] = {"per_k": {}}
    groups, groups_f, groups_all = [], [], []
    for k in range(1, 6):
        rows = cells.get(k, [])
        banned = sorted(K_ORDER[:k], key=CANON_ORDER.index)
        cs = cell_summary(rows, banned)
        cs["banned"] = banned
        out["per_k"][k] = cs
        comp_tr = [r for r in rows if _completed(r) and traceable(r)]
        groups.append([int(mech_ok(r, banned)) for r in comp_tr])
        groups_f.append([int(mech_ok(r, banned, fine=True)) for r in comp_tr])
        groups_all.append([int(_completed(r) and traceable(r) and mech_ok(r, banned)) for r in rows])
    out["jt_mech_coarse"] = S.jt_test_decreasing(groups, n_perm=100_000, seed=0)
    out["ca_mech_coarse"] = S.cochran_armitage_decreasing(groups)
    out["jt_mech_fine"] = S.jt_test_decreasing(groups_f, n_perm=100_000, seed=1)
    out["jt_mech_all_samples"] = S.jt_test_decreasing(groups_all, n_perm=100_000, seed=2)
    pk = out["per_k"]

    def r_(k: int, key: str) -> float | None:
        return pk[k][key]["rate"] if pk.get(k) else None

    crit = {}
    crit["k1_lex_ge_0.7"] = (r_(1, "lex_L1_completed") or 0) >= 0.7
    crit["k1_mech_ge_0.7"] = (r_(1, "mech_coarse_traceable") or 0) >= 0.7
    jtp = out["jt_mech_coarse"].get("p_mc")
    crit["jt_p_lt_0.05"] = bool(jtp is not None and jtp < 0.05)
    crit["lex_ge_0.7_every_k"] = all((r_(k, "lex_L1_completed") or 0) >= 0.7 for k in range(1, 6))
    g5 = pk[5]["gap_L1"]["gap"] if pk.get(5) else None
    crit["k5_gap_ge_0.4"] = bool(g5 is not None and g5 >= 0.4)
    if heldout is not None:
        hs = cell_summary(heldout, list(LITERAL5))
        out["heldout_k5"] = hs
        gh = hs["gap_L1"]
        crit["heldout_gap_ge_0.4_lb_gt_0"] = bool(gh["gap"] is not None and gh["gap"] >= 0.4 and
                                                  gh["gap_newcombe95"][0] > 0)
    out["criteria"] = crit
    disc = all(pk[k]["gap_L1"]["gap"] is not None and abs(pk[k]["gap_L1"]["gap"]) <= 0.1 for k in range(1, 6))
    out["disconfirmed_flat"] = disc
    primary = ["k1_lex_ge_0.7", "k1_mech_ge_0.7", "jt_p_lt_0.05", "lex_ge_0.7_every_k", "k5_gap_ge_0.4"]
    if disc:
        out["verdict"] = "DISCONFIRMED"
    elif all(crit.get(c) for c in primary) and crit.get("heldout_gap_ge_0.4_lb_gt_0", False):
        out["verdict"] = "SUPPORTED + CONFIRMED"
    elif all(crit.get(c) for c in primary):
        out["verdict"] = "SUPPORTED (held-out confirmation failed)"
    else:
        out["verdict"] = "NOT SUPPORTED: " + ", ".join(c for c in primary if not crit.get(c))
    # sensitivities
    out["sens_L2_lex_every_k"] = {k: pk[k]["lex_L2_completed"]["rate"] for k in pk}
    out["sens_fine_mech_every_k"] = {k: pk[k]["mech_fine_traceable"]["rate"] for k in pk}
    out["sens_all_samples"] = {k: {"lex": pk[k]["lex_L1_all"]["rate"], "mech": pk[k]["mech_coarse_all"]["rate"]}
                               for k in pk}
    return out


# ---------------------------------------------------------------------------------------------- N3-D
def n3d(desc_rows: list[dict[str, Any]], named_rows: list[dict[str, Any]]) -> dict[str, Any]:
    banned = list(LITERAL5)
    out = {}
    for name, rows in (("described", desc_rows), ("named_k5", named_rows)):
        comp_tr = [r for r in rows if _completed(r) and traceable(r)]
        comp = [r for r in rows if _completed(r)]
        out[name] = {"n": len(rows), "n_completed": len(comp), "n_traceable": len(comp_tr),
                     "mech_compliance": S.rate(sum(1 for r in comp_tr if mech_ok(r, banned)), len(comp_tr)),
                     "violation": S.rate(sum(1 for r in comp_tr if not mech_ok(r, banned)), len(comp_tr)),
                     "lexical_any_banned_name": S.rate(sum(1 for r in comp if not r.get("lexical_L1")), len(comp)),
                     "named_survivors": S.rate(sum(1 for r in rows if named_survivor(r, banned)), len(rows)),
                     "mech_survivors": S.rate(sum(1 for r in rows if mech_survivor(r, banned)), len(rows)),
                     "truncation_rate": (sum(1 for r in rows if r.get("truncated")) / len(rows)) if rows else None,
                     "order_classes": dict(Counter(r.get("order_class") for r in comp))}
    d = out["described"]
    n = out["named_k5"]
    out["diffs"] = {m: S.unpaired_diff(d[m]["k"], d[m]["n"], n[m]["k"], n[m]["n"])
                    for m in ("mech_compliance", "violation", "lexical_any_banned_name", "named_survivors",
                              "mech_survivors")}
    md = out["diffs"]["mech_compliance"]["newcombe95"]
    vd = out["diffs"]["violation"]["newcombe95"]
    out["direction_committed"] = "under R6, mechanistic compliance OR violation rises (described vs named k=5)"
    out["mech_rises"] = bool(md[0] is not None and md[0] > 0)
    out["violation_rises"] = bool(vd[0] is not None and vd[0] > 0)
    return out


# ---------------------------------------------------------------------------------------------- N5
OTHER_TO_EXT = [(r"spfa|bellman|label[-_ ]?correct", "spfa"), (r"wave[-_ ]?front|flood|\blee\b", "wavefront"),
                (r"random[-_ ]?walk", "random_walk"), (r"\bbeam\b", "beam"),
                (r"random", "random_priority"), (r"uniform[-_ ]?cost|dijkstra", "ucs")]


def alg_key(r: dict[str, Any]) -> str | None:
    lab = r.get("label")
    if lab in CANON_ORDER:
        return lab
    nm = str(r.get("label_other_name") or "")
    for rx, k in OTHER_TO_EXT:
        if re.search(rx, nm, re.IGNORECASE):
            return k
    return None


def n5(set_rows: dict[str, tuple[list[str], list[dict[str, Any]]]], Dm_alg: dict[str, Any], ref_traces: dict[str, Any],
       program_traces: dict[str, dict[str, Any]]) -> dict[str, Any]:
    import mechdist

    algs = Dm_alg["algs"]
    M = np.array(Dm_alg["D_mech"])
    idx = {a: i for i, a in enumerate(algs)}
    out: dict[str, Any] = {"sets": {}}
    signs = []
    for name, (S_set, rows) in set_rows.items():
        surv = [r for r in rows if named_survivor(r, S_set)]
        res: dict[str, Any] = {"set": S_set, "n_rows": len(rows), "n_survivors": len(surv),
                               "survivor_algs": dict(Counter(alg_key(r) or "unknown" for r in surv))}
        if len(surv) < 3:
            res["defined"] = False
            out["sets"][name] = res
            continue
        nonb = [a for a in algs if a not in S_set]
        base_m = float(np.mean([min(M[idx[a], idx[b]] for b in S_set) for a in nonb]))
        base_n = float(np.mean([min(mechdist.d_name(a, b) for b in S_set) for a in nonb]))
        dms, dns, units = [], [], Counter()
        for r in surv:
            tr = program_traces.get(r.get("code_sha256"))
            if tr and tr.get("probes"):
                dm = min(float(np.mean([mechdist.program_distance(tr, ref_traces[x]) for x in mechdist.REFS_OF[b]]))
                         for b in S_set)
                dms.append(dm)
            ak = alg_key(r)
            if ak:
                dns.append(min(mechdist.d_name(ak, b) for b in S_set))
                units[ak] += 1
        Dm = (float(np.mean(dms)) - base_m) if dms else None
        Dn = (float(np.mean(dns)) - base_n) if dns else None
        res.update({"defined": True, "Dm": Dm, "Dn": Dn, "base_mech": base_m, "base_name": base_n,
                    "n_dm": len(dms), "n_dn": len(dns), "units": dict(units)})
        # exact algorithm-level permutation: units -> non-banned identities without replacement
        dm_alg = {a: min(M[idx[a], idx[b]] for b in S_set) for a in nonb}
        dn_alg = {a: min(mechdist.d_name(a, b) for b in S_set) for a in nonb}
        ulist = list(units.items())
        if ulist and len(ulist) <= len(nonb):
            vals_m, vals_n = [], []
            tot = sum(c for _, c in ulist)
            for perm in itertools.permutations(nonb, len(ulist)):
                vals_m.append(sum(c * dm_alg[a] for (_, c), a in zip(ulist, perm)) / tot - base_m)
                vals_n.append(sum(c * dn_alg[a] for (_, c), a in zip(ulist, perm)) / tot - base_n)
            # observed algorithm-level statistic (identities = the survivors' own algorithms where catalogue)
            res["perm_n"] = len(vals_m)
            res["p_Dm_le"] = (sum(1 for v in vals_m if Dm is not None and v <= Dm + 1e-12) / len(vals_m)) if Dm \
                is not None else None
            res["p_Dn_ge"] = (sum(1 for v in vals_n if Dn is not None and v >= Dn - 1e-12) / len(vals_n)) if Dn \
                is not None else None
        res["sign_joint"] = bool(Dm is not None and Dn is not None and Dm < 0 and Dn > 0)
        signs.append(res["sign_joint"])
        out["sets"][name] = res
    nd = sum(1 for v in out["sets"].values() if v.get("defined"))
    cnt = sum(signs)
    out["n_defined"] = nd
    out["n_joint"] = cnt
    out["binom_p_joint"] = S.binom_sf(cnt, nd, 0.25) if nd else None
    out["n_dm_neg"] = sum(1 for v in out["sets"].values() if v.get("defined") and (v.get("Dm") or 0) < 0)
    out["n_dn_pos"] = sum(1 for v in out["sets"].values() if v.get("defined") and (v.get("Dn") or 0) > 0)
    out["binom_p_dm"] = S.binom_sf(out["n_dm_neg"], nd, 0.5) if nd else None
    out["binom_p_dn"] = S.binom_sf(out["n_dn_pos"], nd, 0.5) if nd else None
    if nd < 4:
        out["verdict"] = f"DESCRIPTIVE (only {nd} defined sets)"
    elif cnt >= (5 if nd == 7 else math.ceil(5 / 7 * nd)):
        out["verdict"] = "SUPPORTED"
    elif cnt <= (3 if nd == 7 else math.floor(3 / 7 * nd)):
        out["verdict"] = "DISCONFIRMED"
    else:
        out["verdict"] = "NOT SUPPORTED (between the bars)"
    return out
