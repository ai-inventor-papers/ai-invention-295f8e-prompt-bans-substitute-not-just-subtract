#!/usr/bin/env python3
"""Analysis of the targeted push (T.2-T.3), the mediator clamp (P2-N), the T1 top-five push landings (G.4-G.5,
geometry in top5geo.py) and the sealed same-engine re-measurement of the 40 directions (fallback 1).
Frozen by hash in amendment commit0b before commit #3."""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

import c7 as common  # noqa: E402
from c7 import (CATALOGUE, DATA, DEFAULTS, LABELS, PRED, RESULTS, RUNNER_UP, SEEDS40, SEEDS_T03, read_json,  # noqa: E402
                read_jsonl, write_json)
import stats7 as S  # noqa: E402

T1_SURV = ["bibfs", "dijkstra_unit", "idastar", "jps", "biastar"]
T1_TOP5 = ["bfs", "dfs", "iddfs", "astar", "gbfs"]


def load(path: Path) -> dict[tuple[str, str], list[dict[str, Any]]]:
    out = defaultdict(list)
    for r in read_jsonl(path):
        out[(r["task"], r["arm"])].append(r)
    return out


def ind_off(r: dict[str, Any], task: str) -> int:
    return int(r["label"] in CATALOGUE[task] and r["label"] != DEFAULTS[task] and bool(r["passed"]))


def targeted() -> dict[str, Any]:
    L = load(LABELS)
    c3 = read_json(common.c3_path())["cells"]
    spec = read_json(PRED / "commit4_push_spec.json")["targeted"]
    th = read_json(PRED / "commit0.json")["thresholds"]["targeted"]
    import analysis7 as A
    pop = A.e29_rows(allow_pop=True)
    res: dict[str, Any] = {}
    for task, sp in spec.items():
        tw = [r for r in L.get((task, "TWIN"), []) if int(r["sample_id"]) <= 5]
        if not tw:
            continue
        ru = RUNNER_UP[task]
        n_tw = len(tw)
        tw_off = sum(r["label"] in CATALOGUE[task] and r["label"] != DEFAULTS[task] for r in tw)
        tw_ru = sum(r["label"] == ru and r["passed"] for r in tw)
        tw_pass = np.mean([bool(r["passed"]) for r in tw])
        p0 = (tw_off + 0.5) / (n_tw + 1)
        # escape-norm reference: confirmed engine-d escapers (T10/T2) or screen escapers of the T03 confirmation
        if task in ("T10", "T2"):
            esc = A.escape_flags(task, pop)
            ref = [s for s, v in esc.items() if v["confirmed"]]
        else:
            ref = screen_escapers_t03(L)
        rms = [c3[f"{task}|POP_d{s}_a2.0"]["rms_pos_Lax"] for s in ref if f"{task}|POP_d{s}_a2.0" in c3]
        flagged = False
        if not rms:
            rms = [c3[k]["rms_pos_Lax"] for k in c3 if k.startswith(f"{task}|POP_") and "rms_pos_Lax" in c3[k]]
            flagged = True
        ref_rms = float(np.median(rms)) if rms else float("nan")
        rows = {}
        tw_by_slot = {(r["template"], int(r["sample_id"])): r for r in tw}
        s_all = list(sp["s"]) + [2.0, 4.0, 8.0]      # committed doses + fallback-8 descriptive doses
        for kind in ("AX", "RX"):
            for s in s_all:
                arm = f"{kind}_s{s:g}"
                rr = [r for r in L.get((task, arm), []) if int(r["sample_id"]) <= 5]
                if not rr:
                    continue
                n = len(rr)
                k_off = sum(ind_off(r, task) for r in rr)
                k_ru = sum(r["label"] == ru and r["passed"] for r in rr)
                k_att = sum(r["label"] in CATALOGUE[task] and r["label"] != DEFAULTS[task] for r in rr)
                pas = float(np.mean([bool(r["passed"]) for r in rr]))
                excess = k_ru / n - tw_ru / n_tw
                pb = S.binom_greater(k_ru, n, p0)
                esc_ok = bool(excess >= th["excess"] and pb < th["binom_p"] and pas >= th["pass_frac"] * tw_pass)
                rows[arm] = {"kind": kind, "s": s, "n": n, "y_runner_up": k_ru / n, "y_off": k_off / n,
                             "att": k_att / n, "pass": pas, "excess_runner_up": excess, "binom_p": pb,
                             "escape": esc_ok, "ru_share_of_correct_off": (k_ru / k_off) if k_off else None,
                             "labels": dict(sorted(((l, sum(1 for r in rr if r["label"] == l))
                                                    for l in {r["label"] for r in rr}), key=lambda kv: -kv[1])),
                             "rho_s": s * sp["D_rms"] / ref_rms if ref_rms == ref_rms else None}
                # flips vs the twin on the same CRN slots
                fl = [(ind_off(tw_by_slot[(r["template"], int(r["sample_id"]))], task), ind_off(r, task))
                      for r in rr if (r["template"], int(r["sample_id"])) in tw_by_slot]
                rows[arm]["flips_vs_twin"] = {"to_off": sum(1 for a, b in fl if a == 0 and b == 1),
                                              "to_default": sum(1 for a, b in fl if a == 1 and b == 0)}
        mcn = {}
        for s in s_all:
            ax = {(r["template"], int(r["sample_id"])): r for r in L.get((task, f"AX_s{s:g}"), [])}
            rx = {(r["template"], int(r["sample_id"])): r for r in L.get((task, f"RX_s{s:g}"), [])}
            keys = sorted(set(ax) & set(rx))
            b_ = sum(1 for k in keys if ind_off(ax[k], task) and not ind_off(rx[k], task))
            c_ = sum(1 for k in keys if not ind_off(ax[k], task) and ind_off(rx[k], task))
            mcn[f"s{s:g}"] = {"n": len(keys), "axis_only": b_, "random_only": c_, "p_exact": S.mcnemar_exact(b_, c_)}
        esc_s = [rows[f"AX_s{s:g}"]["s"] for s in sp["s"] if rows.get(f"AX_s{s:g}", {}).get("escape")]
        esc_ext = [s for s in s_all if rows.get(f"AX_s{s:g}", {}).get("escape")]
        esc_ext_r = [s for s in s_all if rows.get(f"RX_s{s:g}", {}).get("escape")]
        smin = min(esc_s) if esc_s else None
        passes = False
        if smin is not None:
            r0 = rows[f"AX_s{smin:g}"]
            passes = bool(r0["rho_s"] is not None and r0["rho_s"] <= th["rho_s_max"]
                          and (r0["ru_share_of_correct_off"] or 0) >= 0.5)
        res[task] = {"L_ax": sp["L_ax"], "twin": {"n": n_tw, "k_off_att": tw_off, "k_runner_up_correct": tw_ru,
                                                  "pass": tw_pass, "p0": p0},
                     "escape_norm_reference": {"directions": ref, "median_rms": ref_rms, "flagged_all_dirs": flagged,
                                               "D_rms": sp["D_rms"]},
                     "arms": rows, "mcnemar_axis_vs_random": mcn, "smallest_escaping_s": smin,
                     "descriptive_crossing": {"axis_escaping_s_incl_2_4_8": esc_ext,
                                              "random_escaping_s_incl_2_4_8": esc_ext_r,
                                              "note": "fallback 8: s in {2,4,8} descriptive; the claim is judged on "
                                                      "s <= 1 as committed"},
                     "task_pass": passes}
    n_pass = sum(1 for v in res.values() if v.get("task_pass"))
    res["verdict"] = {"tasks_passing": n_pass, "claim": "SUPPORTED" if n_pass >= 2 else "NOT SUPPORTED"}
    return res


def screen_escapers_t03(L: dict) -> list[int]:
    """C.3: exp29 escape.py screen rule on the T03 fresh directions (twin = this run's T03 TWIN k 0-9 rows)."""
    import escape as ESC
    cat = set(CATALOGUE["T03"])
    tw = ESC.share([r for r in L.get(("T03", "TWIN"), []) if int(r["sample_id"]) < 10], cat, "full_sort")
    out = []
    for s in SEEDS_T03:
        rr = [r for r in L.get(("T03", f"POP_d{s}_a2.0"), []) if int(r["sample_id"]) < 2]
        if rr and ESC.cell_eval(rr, tw, cat, "full_sort")["screen_pass"]:
            out.append(s)
    return out


def clamp() -> dict[str, Any]:
    p = DATA / "labels_clamp.jsonl"
    if not p.exists():
        return {"status": "not run"}
    L = load(p)
    th = read_json(PRED / "commit0.json")["thresholds"]["clamp"]
    sel = read_json(RESULTS / "clamp_selection.json")
    res: dict[str, Any] = {"selection": sel}
    tot = {"CLU": 0, "CLA": 0, "CLR": 0}
    pairs = {"CLA": [0, 0], "CLR": [0, 0]}
    for task, seeds in sel["seeds"].items():
        for s in seeds:
            cu = {(r["template"], int(r["sample_id"])): r for r in L.get((task, f"CLU_d{s}"), [])}
            for nm in ("CLU", "CLA", "CLR"):
                tot[nm] += sum(ind_off(r, task) for r in L.get((task, f"{nm}_d{s}"), []))
            for nm in ("CLA", "CLR"):
                cc = {(r["template"], int(r["sample_id"])): r for r in L.get((task, f"{nm}_d{s}"), [])}
                for k in set(cu) & set(cc):
                    a, b = ind_off(cu[k], task), ind_off(cc[k], task)
                    if a and not b:
                        pairs[nm][0] += 1
                    if b and not a:
                        pairs[nm][1] += 1
            res[f"{task}|{s}"] = {nm: {"n": len(L.get((task, f"{nm}_d{s}"), [])),
                                       "y": float(np.mean([ind_off(r, task) for r in L.get((task, f"{nm}_d{s}"), [])]))
                                       if L.get((task, f"{nm}_d{s}")) else None} for nm in ("CLU", "CLA", "CLR")}
    rem = {nm: (1 - tot[nm] / tot["CLU"]) if tot["CLU"] else None for nm in ("CLA", "CLR")}
    res["pooled"] = {"escapes": tot, "removed_share": rem,
                     "mcnemar": {nm: {"removed": pairs[nm][0], "added": pairs[nm][1],
                                      "p_exact": S.mcnemar_exact(*pairs[nm])} for nm in pairs}}
    res["verdict"] = ("SUPPORTED" if rem["CLA"] is not None and rem["CLA"] >= th["axis_removed_min"]
                      and rem["CLR"] is not None and rem["CLR"] <= th["random_removed_max"] else "NOT SUPPORTED")
    return res


def remeasure() -> dict[str, Any]:
    """Fallback 1 robustness row: F and P2 against this engine's own N = 10 outcomes of the 40 directions."""
    p = DATA / "labels_s0b.jsonl"
    if not p.exists():
        return {"status": "not run"}
    L = load(p)
    c3 = read_json(common.c3_path())["cells"]
    import analysis7 as A
    res = {}
    for task in ("T10", "T2"):
        m, b, y, ye = [], [], [], []
        Y = A.outcomes()
        for s in SEEDS40:
            rr = L.get((task, f"POP_d{s}_a2.0"), [])
            c = c3.get(f"{task}|POP_d{s}_a2.0")
            if not rr or not c:
                continue
            m.append(c["m"])
            b.append(c["b"])
            y.append(A.cell_stats(rr, task)["y"])
            ye.append(Y.get(f"{task}|POP_d{s}_a2.0", {}).get("y", float("nan")))
        res[task] = {"n": len(y), "F_rho": S.spearman(m, y), "F_p": S.perm_p(m, y, 10000, seed=41),
                     "P2_rho": S.spearman(b, y), "P2_p": S.perm_p(b, y, 10000, seed=42),
                     "y_this_vs_exp29d_rho": S.spearman(y, ye), "rho_max_ties": S.tie_ceiling(y),
                     "mean_y_this": float(np.mean(y)) if y else None, "mean_y_exp29d": float(np.nanmean(ye))
                     if ye else None}
    return res


def top5_landing() -> dict[str, Any]:
    """G.4: label shares per arm (10-algorithm labeller), correct non-TOP5 share, edge-landing share (edge set from
    top5geo geometry), RSURV null comparison (Fisher) and the prompt TOP5 ban (exp30 rows)."""
    L = load(LABELS)
    geo_p = RESULTS / "top5_geometry.json"
    geo = read_json(geo_p) if geo_p.exists() else {}
    edge = set(geo.get("edge_survivors", []))
    gnorm = geo.get("g_rank_norm", {})
    res: dict[str, Any] = {"edge_survivors": sorted(edge)}
    arms = sorted({a for (t, a) in L if t == "T1" and a != "TWIN"})
    for arm in ["TWIN"] + arms:
        rr = [r for r in L.get(("T1", arm), []) if int(r["sample_id"]) <= 5]
        if not rr:
            continue
        lab = [r.get("label10") or r["label"] for r in rr]
        corr_non = [l for l, r in zip(lab, rr) if l in T1_SURV and r["passed"]]
        att_non = [l for l in lab if l in T1_SURV]
        res[arm] = {"n": len(rr), "pass": float(np.mean([bool(r["passed"]) for r in rr])),
                    "labels10": dict(sorted(((l, lab.count(l)) for l in set(lab)), key=lambda kv: -kv[1])),
                    "correct_nonTOP5": len(corr_non), "attempted_nonTOP5": len(att_non),
                    "correct_nonTOP5_on_edge": sum(1 for l in corr_non if l in edge),
                    "attempted_nonTOP5_on_edge": sum(1 for l in att_non if l in edge),
                    "mean_rank_norm_g_correct": float(np.mean([gnorm[l] for l in corr_non])) if corr_non and gnorm
                    else None,
                    "mean_rank_norm_g_attempted": float(np.mean([gnorm[l] for l in att_non])) if att_non and gnorm
                    else None,
                    "label6_frozen": dict(sorted(((l, sum(1 for r in rr if r["label"] == l))
                                                  for l in {r["label"] for r in rr}), key=lambda kv: -kv[1]))}
    l30 = [r for r in read_jsonl(common.IN30 / "labels.jsonl") if r["task"] == "T1" and r["arm"] == "TOP5BAN"]
    if l30:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from label7 import label10
        lab = [label10(r.get("code"))[0] for r in l30]
        res["TOP5BAN_exp30"] = {"n": len(l30), "labels10": dict(sorted(((l, lab.count(l)) for l in set(lab)),
                                                                      key=lambda kv: -kv[1])),
                                "correct_nonTOP5": sum(1 for l, r in zip(lab, l30) if l in T1_SURV and r["passed"]),
                                "attempted_nonTOP5": sum(1 for l in lab if l in T1_SURV),
                                "pass": float(np.mean([bool(r["passed"]) for r in l30]))}
    # SURV vs RSURV at each s (edge landings among attempted non-TOP5, Fisher one-sided)
    cmp_ = {}
    for s in ("0.25", "0.5", "1"):
        a, b = res.get(f"SURV_s{s}"), res.get(f"RSURV_s{s}")
        if a and b:
            use = "correct" if min(a["correct_nonTOP5"], b["correct_nonTOP5"]) >= 5 else "attempted"
            ea, na = a[f"{use}_nonTOP5_on_edge"], a[f"{use}_nonTOP5"]
            eb, nb = b[f"{use}_nonTOP5_on_edge"], b[f"{use}_nonTOP5"]
            cmp_[f"s{s}"] = {"basis": use, "SURV_edge": ea, "SURV_n": na, "RSURV_edge": eb, "RSURV_n": nb,
                             "fisher_p_greater": S.fisher_exact(ea, na - ea, eb, nb - eb) if na and nb else None}
    res["SURV_vs_RSURV"] = cmp_
    return res


def main() -> None:
    out = {"targeted": targeted(), "clamp": clamp(), "remeasure": remeasure(), "top5": top5_landing()}
    write_json(RESULTS / "targeted_push.json", out["targeted"])
    write_json(RESULTS / "clamp.json", out["clamp"])
    write_json(RESULTS / "remeasure.json", out["remeasure"])
    write_json(RESULTS / "top5_landing.json", out["top5"])
    print({k: (v.get("verdict") if isinstance(v, dict) else None) for k, v in out.items()})


if __name__ == "__main__":
    main()
