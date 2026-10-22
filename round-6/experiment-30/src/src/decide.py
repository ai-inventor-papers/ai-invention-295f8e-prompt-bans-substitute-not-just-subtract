#!/usr/bin/env python3
"""Committed decision code (commit #1): the S-a, S-b, S-c, F1 and F2 rules as functions of labelled rows.

Row fields used: task, template, k, arm, site, alpha, passed (bool), label (str), realised_disp.disp_R35 (prefill
rows). Outcome y = passed AND label in the task catalogue AND label != the twin default ('other', 'invalid' and
'unresolved' are never y = 1). Pairing = the CRN slot (template, k).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np

from stats import holm, mantel_haenszel, mcnemar_exact, mcnemar_one_sided, wilson_ci

DEFAULTS = {"T03": "full_sort", "T10": "union_find", "T2": "dijkstra", "T1": "bfs"}
CATALOGUE = {
    "T03": ["full_sort", "size_k_heap", "heapify_pop", "quickselect", "median_of_medians", "counting_sort"],
    "T10": ["bfs", "dfs", "union_find", "label_propagation"],
    "T2": ["dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"],          # exp8 suite t2 modes
    "T1": ["bfs", "dfs", "bibfs", "iddfs", "astar_gbfs", "dijkstra"],      # exp8 suite t1 modes (K7: label_k7)
}
ALPHAS = (1.0, 2.0, 4.0)
GATE = 0.8          # pass >= 0.8 x twin pass
SA_MARGIN = 0.15    # S-a effect size
SA_DISCONF = 0.05   # S-a disconfirmation margin
SC_MARGIN = 0.10    # S-c effect size
F1_THRESHOLD = 0.80
F1_TOKENS = 32
F2_BOUND = 5.70     # nats: exp(-m / 1.3) < 1/80  <=>  m > 1.3 * ln 80 = 5.697
N_SA_CONTRASTS = 6
N_SA_SELECTION = 6  # 2 sites x 3 doses


def y_of(r: dict[str, Any]) -> int:
    t = r["task"]
    lab = r.get("label")
    return int(bool(r.get("passed")) and lab in CATALOGUE.get(t, []) and lab != DEFAULTS[t])


def slot(r: dict[str, Any]) -> tuple[str, int]:
    return (r["template"], int(r["k"]))


def cell_index(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[tuple[str, int], dict[str, Any]]]:
    idx: dict[tuple[str, str], dict[tuple[str, int], dict[str, Any]]] = defaultdict(dict)
    for r in rows:
        idx[(r["task"], r["arm"])][slot(r)] = r
    return idx


def cell_stats(cell: dict[tuple[str, int], dict[str, Any]], slots: list[tuple[str, int]] | None = None
               ) -> dict[str, Any]:
    rs = [cell[s] for s in (slots or sorted(cell)) if s in cell]
    n = len(rs)
    if n == 0:
        return {"n": 0}
    k_y = sum(y_of(r) for r in rs)
    k_p = sum(bool(r.get("passed")) for r in rs)
    k_inv = sum(r.get("label") == "invalid" for r in rs)
    k_oth = sum(r.get("label") == "other" for r in rs)
    return {"n": n, "y": k_y, "share": k_y / n, "share_ci": list(wilson_ci(k_y, n)), "pass": k_p / n,
            "pass_ci": list(wilson_ci(k_p, n)), "invalid": k_inv / n, "other": k_oth / n}


def paired(cell_a: dict, cell_b: dict, slots: list[tuple[str, int]] | None = None) -> dict[str, Any]:
    """b = slots where A is y=1 and B is y=0; c = the reverse (shared slots only)."""
    sh = sorted(set(cell_a) & set(cell_b)) if slots is None else [s for s in slots if s in cell_a and s in cell_b]
    b = sum(1 for s in sh if y_of(cell_a[s]) == 1 and y_of(cell_b[s]) == 0)
    c = sum(1 for s in sh if y_of(cell_a[s]) == 0 and y_of(cell_b[s]) == 1)
    return {"n_shared": len(sh), "b": b, "c": c, "p_two_sided": mcnemar_exact(b, c),
            "p_one_sided": mcnemar_one_sided(b, c), "slots": sh}


def arm(site: str, a: float) -> str:
    return f"{site}_a{a:g}"


# ------------------------------------------------------------------------------------------------ S-a
def s_a(rows: list[dict[str, Any]], tasks: tuple[str, ...] = ("T03", "T10")) -> dict[str, Any]:
    idx = cell_index(rows)
    out: dict[str, Any] = {"tasks": {}}
    contrasts = []
    for t in tasks:
        twin = idx.get((t, "TWIN"), {})
        tw = cell_stats(twin)
        gate = GATE * tw.get("pass", 0.0)
        cand = []
        for a in ALPHAS:
            for s in ("S0", "S4"):
                c = idx.get((t, arm(s, a)), {})
                st = cell_stats(c, sorted(c))
                if st.get("n", 0) == 0:
                    continue
                st.update({"site": s, "alpha": a, "gated": st["pass"] >= gate})
                cand.append(st)
        gated = [c for c in cand if c["gated"]]
        sel = None
        if gated:
            sel = sorted(gated, key=lambda c: (-c["share"], c["alpha"], 0 if c["site"] == "S0" else 1))[0]
        tres: dict[str, Any] = {"twin": tw, "gate_pass": gate, "candidates": cand,
                                "selected": {"site": sel["site"], "alpha": sel["alpha"], "share": sel["share"],
                                             "pass": sel["pass"]} if sel else None, "contrasts": {}}
        if sel is not None:
            A = idx[(t, arm(sel["site"], sel["alpha"]))]
            for comp in ("S1", "S2", "S5"):
                B = idx.get((t, arm(comp, sel["alpha"])), {})
                pr = paired(A, B)
                shA = cell_stats(A, pr["slots"])
                shB = cell_stats(B, pr["slots"])
                diff = shA.get("share", 0.0) - shB.get("share", 0.0)
                rec = {"comparator": comp, "alpha": sel["alpha"], "b": pr["b"], "c": pr["c"],
                       "n_shared": pr["n_shared"], "p": pr["p_two_sided"], "diff": diff,
                       "share_selected_shared": shA.get("share"), "share_comparator_shared": shB.get("share"),
                       "p_selection_aware": min(1.0, N_SA_SELECTION * pr["p_two_sided"])}
                tres["contrasts"][comp] = rec
                contrasts.append((t, comp, rec))
        # every b:c beside the selected one (no best-cell-only reporting)
        allbc = {}
        for a in ALPHAS:
            for s in ("S0", "S4"):
                for comp in ("S1", "S2", "S5"):
                    A = idx.get((t, arm(s, a)), {})
                    B = idx.get((t, arm(comp, a)), {})
                    if A and B:
                        pr = paired(A, B)
                        allbc[f"{s}_a{a:g}_vs_{comp}"] = {"b": pr["b"], "c": pr["c"], "p": pr["p_two_sided"],
                                                          "n_shared": pr["n_shared"]}
        tres["all_bc"] = allbc
        # disconfirmation check at every gated dose
        dis = []
        for a in ALPHAS:
            ts = [c for c in cand if c["alpha"] == a and c["gated"]]
            if not ts:
                continue
            m_ts = max(c["share"] for c in ts)
            comp_sh = [cell_stats(idx.get((t, arm(s, a)), {})).get("share") for s in ("S1", "S5")]
            comp_sh = [x for x in comp_sh if x is not None]
            if comp_sh:
                dis.append({"alpha": a, "diff": m_ts - max(comp_sh)})
        tres["disconfirm_by_dose"] = dis
        tres["disconfirm"] = bool(dis) and all(d["diff"] < SA_DISCONF for d in dis)
        out["tasks"][t] = tres
    if contrasts:
        adj = holm([c[2]["p"] for c in contrasts])
        adj_sel = holm([c[2]["p_selection_aware"] for c in contrasts])
        for (t, comp, rec), a1, a2 in zip(contrasts, adj, adj_sel):
            rec["p_holm"] = a1
            rec["p_holm_selection_aware"] = a2
    task_pass = {}
    task_pass_robust = {}
    for t in tasks:
        tr = out["tasks"][t]
        cs = tr["contrasts"]
        ok = tr["selected"] is not None and len(cs) == 3 and all(
            c["diff"] >= SA_MARGIN and c["p_holm"] < 0.05 for c in cs.values())
        task_pass[t] = bool(ok)
        task_pass_robust[t] = bool(ok and all(c["p_holm_selection_aware"] < 0.05 for c in cs.values()))
    if all(task_pass.values()):
        verdict = "PASS" + (" (robust to selection)" if all(task_pass_robust.values()) else
                            " (not robust to selection)")
    elif task_pass.get("T03") and not task_pass.get("T10"):
        verdict = "ONE TASK ONLY (T03)"
    elif all(out["tasks"][t]["disconfirm"] for t in tasks):
        verdict = "DISCONFIRMED"
    else:
        verdict = "NOT SUPPORTED (neither pass nor disconfirmation)"
    out.update({"task_pass": task_pass, "task_pass_robust": task_pass_robust, "verdict": verdict,
                "rule": "per task, among S0/S4 x alpha 1/2/4 cells with pass >= 0.8 x twin, the largest correct "
                        "off-default share (ties: lower alpha, then S0); comparators S1, S2, S5 at the same alpha; "
                        "exact McNemar on shared slots; Holm over 6; PASS iff on both tasks every diff >= 0.15 and "
                        "Holm p < 0.05; robust iff the selection-aware Holm (6p) also passes; DISCONFIRMED iff on "
                        "both tasks at every gated dose max(S0,S4) - max(S1,S5) < 0.05"})
    return out


# ------------------------------------------------------------------------------------------------ S-b
def s_b(rows: list[dict[str, Any]], tasks: tuple[str, ...] = ("T03", "T10", "T2"),
        sites: tuple[str, ...] = ("S0", "S4", "S5", "S1", "S1E", "S2"), indicator: tuple[str, ...] = ("S0", "S4"),
        n_q: int = 10, shuffle_seed: int | None = None) -> dict[str, Any]:
    pr = [r for r in rows if r["task"] in tasks and r["site"] in sites and r.get("realised_disp") and
          r["realised_disp"].get("disp_R35") is not None]
    if not pr:
        return {"n": 0}
    disp = np.array([float(r["realised_disp"]["disp_R35"]) for r in pr])
    qs = np.quantile(disp, np.linspace(0, 1, n_q + 1)[1:-1])
    dec = np.searchsorted(qs, disp, side="right")
    ts = np.array([r["site"] in indicator for r in pr], dtype=int)
    y = np.array([y_of(r) for r in pr])
    task = np.array([r["task"] for r in pr])
    if shuffle_seed is not None:
        rng = np.random.default_rng(shuffle_seed)
        for t in tasks:
            m = task == t
            ts[m] = rng.permutation(ts[m])
    tables = []
    strata = []
    for t in tasks:
        for d in range(n_q):
            m = (task == t) & (dec == d)
            if not m.any():
                continue
            a = int(((ts == 1) & (y == 1) & m).sum())
            b = int(((ts == 1) & (y == 0) & m).sum())
            c = int(((ts == 0) & (y == 1) & m).sum())
            dd = int(((ts == 0) & (y == 0) & m).sum())
            tables.append((a, b, c, dd))
            strata.append({"task": t, "decile": d, "a": a, "b": b, "c": c, "d": dd})
    mh = mantel_haenszel(tables)
    return {"n": len(pr), "mh": mh, "pass": bool(np.isfinite(mh["ci"][0]) and mh["ci"][0] > 1.0),
            "strata": strata, "decile_edges": qs.tolist(), "indicator": list(indicator)}


# ------------------------------------------------------------------------------------------------ S-c
def s_c(rows: list[dict[str, Any]], tasks: tuple[str, ...] = ("T03", "T10", "T2")) -> dict[str, Any]:
    idx = cell_index(rows)
    out: dict[str, Any] = {}
    for t in tasks:
        twin = idx.get((t, "TWIN"), {})
        tw = cell_stats(twin)
        res = []
        for a in ALPHAS:
            S3 = idx.get((t, arm("S3", a)), {})
            if not S3:
                continue
            pr = paired(S3, twin)
            st3 = cell_stats(S3, pr["slots"])
            stt = cell_stats(twin, pr["slots"])
            excess = st3["share"] - stt["share"]
            gated = st3["pass"] >= GATE * stt["pass"]
            res.append({"alpha": a, "b": pr["b"], "c": pr["c"], "n_shared": pr["n_shared"],
                        "p_one_sided": pr["p_one_sided"], "excess": excess, "pass_S3": st3["pass"],
                        "pass_twin_shared": stt["pass"], "gated": gated,
                        "hit": bool(gated and excess >= SC_MARGIN and pr["p_one_sided"] < 0.05)})
        out[t] = {"twin": tw, "by_dose": res, "pass": any(r["hit"] for r in res)}
    return out


# ------------------------------------------------------------------------------------------------ F1 / F2 rules
def f1_decision(n_change: int, n_early: int) -> dict[str, Any]:
    share = n_early / n_change if n_change else float("nan")
    return {"n_label_changing_pairs": n_change, "n_first_div_lt_32": n_early, "share": share,
            "share_ci": list(wilson_ci(n_early, n_change)) if n_change else [None, None],
            "pass": bool(n_change and share >= F1_THRESHOLD)}


def f2_decision(m: float | None, sd: float | None) -> dict[str, Any]:
    if m is None or not np.isfinite(m):
        return {"m": m, "verdict": "NOT COMPUTABLE"}
    if sd is not None and np.isfinite(sd) and abs(m - F2_BOUND) < 2 * sd:
        v = "UNRESOLVED"
    else:
        v = "EXPLAINS NULL (m > 5.70)" if m > F2_BOUND else "DOES NOT EXPLAIN NULL (m <= 5.70)"
    return {"m": m, "scoring_sd": sd, "bound": F2_BOUND, "p_alt_T": {str(T): float(np.exp(-m / T))
                                                                   for T in (0.3, 0.7, 1.0, 1.3)},
            "verdict": v}
