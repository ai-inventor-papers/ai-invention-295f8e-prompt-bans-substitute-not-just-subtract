#!/usr/bin/env python3
"""Stage 6 (committed at COMMIT #1, before any Stage 3 sample): K1 cells, measures, verdicts; HR counts.

Cell measures (per unit x arm, 50 CRN slots): attempted / correct shares per class (invalid = not target), correct-only
Hill-1 rarefied to depth 25 (exact hypergeometric expectation of the Shannon entropy, exponentiated; NA if < 25
correct), pass rate, pass cost vs the twin (Newcombe hybrid-score 95% CI, exact McNemar on paired pass flips),
reversion, breakage, phrasing clusters per idea (identifier-normalised token 4-gram Jaccard components at 0.7/0.8/0.9),
reached-decision share, flips vs the twin. K1 (a)-(f), the disconfirming branches, the IUT primary p, the secondary
McNemar (A10 vs A3g on correct off-default flips) and the HR counts, all from data/*.jsonl and the committed table.
Usage: analysis_k1.py  -> results/k1_cells.json, results/k1_verdict.json, results/hr.json
"""

from __future__ import annotations

import io
import keyword
import math
import re
import sys
import tokenize
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg8 import (BOOT_SEED, CONT_LABELS, CONTS, LABELS, N_BOOT, PRED_DIR, RESULTS_DIR, SAMPLES, THRESH, UNITS,  # noqa
                  read_json, read_jsonl, utc_now, write_json)
import predict8 as PR  # noqa: E402

COMP_FAMILIES = {"global_T": ["A1", "A2", "A3g"], "min_p": ["A4"], "EDT": ["A5"], "AdapT": ["A6"]}
FORK = ["A9", "A10"]
PLACEBOS = {"entropy_max": ["A7"], "random_window": ["A8"]}
BAD = {"invalid", "no_code", "label_error", "extraction"}


def cls(unit: str, label: str | None, adjud: dict[str, str] | None = None, sid: str | None = None) -> str:
    if adjud and sid in adjud:
        return adjud[sid]
    if label is None or label in BAD:
        return "invalid"
    if label in UNITS[unit]["catalogue"]:
        return label
    return "other"


def load_rows(adjud: dict[str, str] | None = None) -> dict[str, dict[str, dict[int, dict[str, Any]]]]:
    """unit -> arm -> slot -> row (with cls, passed)."""
    labels = {r["sid"]: r for r in read_jsonl(LABELS)}
    out: dict = defaultdict(lambda: defaultdict(dict))
    for r in read_jsonl(SAMPLES):
        if r.get("stage") not in ("S0", "S3") or r.get("slot") is None or r["arm"].endswith("_chk"):
            continue
        L = labels.get(r["sid"])
        if L is None:
            continue
        r["label"] = L.get("label")
        r["cls"] = cls(r["unit"], L.get("label"), adjud, r["sid"])
        r["passed"] = bool(L.get("passed")) and r["cls"] != "invalid"
        r["code"] = L.get("code")
        out[r["unit"]][r["arm"]][int(r["slot"])] = r
    return out


# ------------------------------------------------------------------------------------------------ phrasing
def norm_tokens(code: str | None) -> list[str]:
    if not code:
        return []
    out = []
    try:
        for tk in tokenize.generate_tokens(io.StringIO(code).readline):
            if tk.type == tokenize.NAME:
                out.append(tk.string if keyword.iskeyword(tk.string) else "ID")
            elif tk.type == tokenize.NUMBER:
                out.append("NUM")
            elif tk.type == tokenize.STRING:
                out.append("STR")
            elif tk.type in (tokenize.OP,):
                out.append(tk.string)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        out = re.findall(r"\w+|[^\w\s]", code)
    return out


def phrasing_clusters(codes: list[str], thr: float) -> int:
    grams = []
    for c in codes:
        t = norm_tokens(c)
        grams.append({tuple(t[i:i + 4]) for i in range(max(len(t) - 3, 0))} or {tuple(t)})
    n = len(grams)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for i in range(n):
        for j in range(i + 1, n):
            a, b = grams[i], grams[j]
            if len(a | b) and len(a & b) / len(a | b) >= thr:
                parent[find(i)] = find(j)
    return len({find(i) for i in range(n)})


# ------------------------------------------------------------------------------------------------ cell measures
def hill(rows: list[dict[str, Any]], depth: int = THRESH["hill_depth"]) -> float | None:
    return PR.hill1_rarefied([r["cls"] for r in rows if r["passed"]], depth)


def cell_measures(unit: str, arm_rows: dict[int, dict[str, Any]], twin: dict[int, dict[str, Any]],
                  tmap: dict[str, Any] | None, classes: list[str]) -> dict[str, Any]:
    slots = sorted(s for s in arm_rows if s in twin)
    rows = [arm_rows[s] for s in slots]
    n = len(rows)
    att = Counter(r["cls"] for r in rows)
    cor = Counter(r["cls"] for r in rows if r["passed"])
    default = UNITS[unit]["default"]
    p_arm = [arm_rows[s]["passed"] for s in slots]
    p_tw = [twin[s]["passed"] for s in slots]
    a = sum(1 for x, y in zip(p_tw, p_arm) if x and y)
    b = sum(1 for x, y in zip(p_tw, p_arm) if x and not y)
    c = sum(1 for x, y in zip(p_tw, p_arm) if not x and y)
    d = n - a - b - c
    nc = PR.newcombe_paired(a, b, c, d)
    # decision tokens: change, class, reversion, breakage
    tok_cls = {}
    for nd, m in (tmap or {}).items():
        for t, mm in m.items():
            tok_cls[(nd, int(t))] = mm.get("committal")
    changed, broke, offtok, reverted = 0, 0, 0, 0
    for s in slots:
        r, t = arm_rows[s], twin[s]
        if r.get("decision_token") is None or t.get("decision_token") is None:
            continue
        if r["decision_token"] != t["decision_token"]:
            changed += 1
            broke += int(not r["passed"])
        nd_ids = list((tmap or {}).keys())
        nd = nd_ids[r["decision_node"]] if 0 <= r.get("decision_node", -1) < len(nd_ids) else None
        cl = tok_cls.get((nd, int(r["decision_token"]))) if nd else None
        if cl is not None and cl != default and cl not in ("other", "invalid"):
            offtok += 1
            reverted += int(r["cls"] == default)
    flips = sum(1 for s in slots if arm_rows[s]["cls"] != twin[s]["cls"])
    ident = sum(1 for s in slots if arm_rows[s].get("token_ids") == twin[s].get("token_ids"))
    phr = {}
    for idea in sorted(cor):
        codes = [r.get("code") for r in rows if r["passed"] and r["cls"] == idea]
        phr[idea] = {str(th): phrasing_clusters(codes, th) for th in (0.7, 0.8, 0.9)}
    off_att = sum(v for k, v in att.items() if k not in (default, "other", "invalid")) / max(n, 1)
    off_cor = sum(v for k, v in cor.items() if k not in (default, "other", "invalid")) / max(n, 1)
    parseable = [r for r in rows if r["cls"] != "invalid"]
    off_att_parse = (sum(1 for r in parseable if r["cls"] not in (default, "other")) / len(parseable)) \
        if parseable else None
    return {"n": n, "attempted": {k: att.get(k, 0) / max(n, 1) for k in classes},
            "correct": {k: cor.get(k, 0) / max(n, 1) for k in classes}, "counts": dict(att),
            "correct_counts": dict(cor), "pass_rate": sum(p_arm) / max(n, 1), "hill1_correct_r25": hill(rows),
            "n_correct": sum(p_arm), "pass_cost": (sum(p_tw) - sum(p_arm)) / max(n, 1),
            "pass_cost_ci95": [-nc["hi"], -nc["lo"]], "mcnemar_pass": {"b_twin_only": b, "c_arm_only": c,
                                                                       "p": PR.mcnemar_exact(b, c)},
            "changed_decision": changed, "breakage": broke / changed if changed else None,
            "off_default_token": offtok, "reversion": reverted / offtok if offtok else None,
            "label_flips_vs_twin": flips, "byte_identical_to_twin": ident,
            "off_default_attempted": off_att, "off_default_correct": off_cor,
            "off_default_attempted_parseable": off_att_parse,
            "reached_decision": sum(1 for r in rows if r.get("reached_decision")) / max(n, 1),
            "phrasing_clusters": phr, "other_share": att.get("other", 0) / max(n, 1)}


# ------------------------------------------------------------------------------------------------ bootstrap
def boot_family_best(arms: dict[str, dict[int, dict[str, Any]]], twin: dict[int, dict[str, Any]], names: list[str],
                     idx: np.ndarray, slots: list[int]) -> float:
    """Best Hill among the family's settings whose pass cost <= 5 points on the resampled slots; twin Hill if none."""
    tw_rows = [twin[slots[i]] for i in idx]
    tw_pass = np.mean([r["passed"] for r in tw_rows])
    h_tw = PR.hill1_rarefied([r["cls"] for r in tw_rows if r["passed"]], THRESH["hill_depth"]) or 1.0
    best = None
    for a in names:
        if a not in arms:
            continue
        rr = [arms[a].get(slots[i]) for i in idx]
        if any(r is None for r in rr):
            continue
        cost = tw_pass - np.mean([r["passed"] for r in rr])
        if cost > THRESH["pass_cost_max"]:
            continue
        h = PR.hill1_rarefied([r["cls"] for r in rr if r["passed"]], THRESH["hill_depth"])
        if h is None:
            continue
        best = h if best is None else max(best, h)
    return best if best is not None else h_tw


def bootstrap_unit(unit: str, arms: dict[str, dict[int, dict[str, Any]]], n_boot: int = N_BOOT) -> dict[str, Any]:
    twin = arms["A0"]
    slots = sorted(s for s in twin if all(s in arms.get(a, {}) for a in FORK if a in arms))
    rng = np.random.default_rng(BOOT_SEED)
    fams = {**COMP_FAMILIES, **PLACEBOS}
    diffs = {f: [] for f in fams}
    diffs["best_comparator"] = []
    fork_best = []
    full = np.arange(len(slots))
    point = {"fork": boot_family_best(arms, twin, FORK, full, slots)}
    for f, names in fams.items():
        point[f] = boot_family_best(arms, twin, names, full, slots)
    for _ in range(n_boot):
        idx = rng.integers(0, len(slots), len(slots))
        fb = boot_family_best(arms, twin, FORK, idx, slots)
        fork_best.append(fb)
        cb = []
        for f, names in fams.items():
            v = boot_family_best(arms, twin, names, idx, slots)
            diffs[f].append(fb - v)
            if f in COMP_FAMILIES:
                cb.append(v)
        diffs["best_comparator"].append(fb - max(cb))
    out = {"point_best_hill": point, "n_slots": len(slots)}
    for f, v in diffs.items():
        v = np.array(v)
        out[f] = {"mean_diff": float(v.mean()), "lb_97_5": float(np.percentile(v, 2.5)),
                  "p_one_sided": float((np.sum(v <= 0) + 1) / (len(v) + 1))}
    return out


# ------------------------------------------------------------------------------------------------ verdicts
def mae(obs: dict[str, float], pred: dict[str, float], classes: list[str]) -> float:
    return float(np.mean([abs(obs.get(c, 0) - pred.get(c, 0)) for c in classes]))


def run(adjud: dict[str, str] | None = None, n_boot: int = N_BOOT) -> dict[str, Any]:
    c1 = read_json(PRED_DIR / "commit1_dose_table.json")
    data = load_rows(adjud)
    cells: dict = {}
    verdict: dict = {"utc": utc_now(), "units": {}}
    for unit, arms in data.items():
        if "A0" not in arms:
            continue
        e = c1["units"].get(unit, {})
        classes = e.get("classes") or (list(UNITS[unit]["catalogue"]) + ["other", "invalid"])
        tmap = e.get("token_map")
        cells[unit] = {a: cell_measures(unit, rows, arms["A0"], tmap, classes) for a, rows in arms.items()}
    verdict["cells"] = cells
    # (a) MAE per located unit, replay MAE
    a_res = {}
    for unit, e in c1["units"].items():
        if e.get("role") == "boundary" or unit not in cells:
            continue
        errs, rerrs = [], []
        for arm in ("A9", "A10"):
            if arm not in cells[unit]:
                continue
            obs = cells[unit][arm]["attempted"]
            errs.append(mae(obs, e["arms"][arm]["attempted"], e["classes"]))
            rerrs.append(mae(obs, e["arms"][arm]["replay"]["attempted"], e["classes"]))
        if errs:
            a_res[unit] = {"mae": float(np.mean(errs)), "mae_replay": float(np.mean(rerrs)),
                           "pass": float(np.mean(errs)) <= THRESH["mae_max"],
                           "noise_ceiling": c1["mae_noise_ceiling"]["per_unit"].get(unit)}
    frac = np.mean([v["pass"] for v in a_res.values()]) if a_res else 0.0
    verdict["K1a"] = {"per_unit": a_res, "frac_units_pass": float(frac), "pass": bool(frac >= THRESH["mae_units_frac"]),
                      "noise_ceiling_all": c1["mae_noise_ceiling"]["P_mae_le_0.10_if_true"]}
    # (b) collapsed: Hill bootstrap; mixed: d1 target + Hill >= 1.8 on >= 4 units
    b_res, iut_ps, mixed_hill_ok = {}, [], []
    for unit, e in c1["units"].items():
        if unit not in data or e.get("role") == "boundary":
            continue
        arms = data[unit]
        if not all(a in arms for a in FORK):
            continue
        bs = bootstrap_unit(unit, arms, n_boot)
        fork_cells = {a: cells[unit][a] for a in FORK}
        ok_fork = [a for a in FORK if (fork_cells[a]["hill1_correct_r25"] or 0) >= THRESH["hill_min"]
                   and fork_cells[a]["pass_cost"] <= THRESH["pass_cost_max"]]
        comp_max = {f: max([(cells[unit][a]["hill1_correct_r25"] or 0) for a in names if a in cells[unit]] or [0])
                    for f, names in COMP_FAMILIES.items()}
        res = {"bootstrap": bs, "fork_arms_meeting_hill_and_cost": ok_fork, "comparator_point_max_hill": comp_max}
        if e["role"] == "collapsed":
            res["pass"] = bool(ok_fork) and all(v <= THRESH["hill_comp_max"] for v in comp_max.values()) and \
                all(bs[f]["lb_97_5"] > 0 for f in COMP_FAMILIES)
            iut_ps.append(bs["best_comparator"]["p_one_sided"])
        else:
            tgt = e["dose"].get("target_share_d1")
            share_d1 = cells[unit]["A9"]["off_default_attempted"]
            res["d1_target"] = tgt
            res["d1_observed_minority"] = share_d1
            res["d1_within_0.10"] = (abs(share_d1 - tgt) <= THRESH["d1_target_tol"]) if tgt is not None else None
            hb = max((fork_cells[a]["hill1_correct_r25"] or 0) for a in FORK)
            res["best_fork_hill"] = hb
            mixed_hill_ok.append(hb >= THRESH["hill_min"])
        b_res[unit] = res
    verdict["K1b"] = {"per_unit": b_res, "mixed_units_hill_ok": int(sum(mixed_hill_ok)),
                      "collapsed_pass": [u for u, r in b_res.items() if r.get("pass")]}
    verdict["primary_p_IUT"] = max(iut_ps) if iut_ps else None
    # (c) twin decision-token entropy vs q90
    verdict["K1c"] = {u: e.get("entropy_check_c") for u, e in c1["units"].items() if e.get("role") != "boundary"}
    for u in list(verdict["K1c"]):
        if u in cells and "A7" in cells[u]:
            twin = data[u]["A0"]
            jst = c1["units"][u]["jstar"]
            hits = sum(1 for s, r in twin.items() if r.get("reached_decision") and
                       int(jst.get(str(s), -9)) == r["decision_pos"])
            verdict["K1c"][u] = {**(verdict["K1c"][u] or {}), "A7_hits_decision": hits}
    # (d) boundary window
    d_res = {}
    for unit in cells:
        if "B1" not in cells[unit]:
            continue
        tw, bw = cells[unit]["A0"], cells[unit]["B1"]
        dc = bw["off_default_correct"] - tw["off_default_correct"]
        da = (bw["off_default_attempted_parseable"] or 0) - (tw["off_default_attempted_parseable"] or 0)
        d_res[unit] = {"d_off_correct": dc, "d_off_attempted_parseable": da, "window_pass_rate": bw["pass_rate"],
                       "untestable_by_breakage": bw["pass_rate"] < THRESH["boundary_pass_min"],
                       "pass": abs(dc) <= THRESH["boundary_move_max"] and abs(da) <= THRESH["boundary_move_max"]}
    verdict["K1d"] = d_res
    # (e) reversion pooled
    num = den = 0
    for unit in cells:
        for a in FORK:
            cm = cells[unit].get(a)
            if cm and cm["off_default_token"]:
                den += cm["off_default_token"]
                num += round((cm["reversion"] or 0) * cm["off_default_token"])
    verdict["K1e"] = {"pooled_reversion": num / den if den else None, "n_off_tokens": den,
                      "pass": (num / den <= THRESH["reversion_max"]) if den else None}
    # (f) Gemma
    if "G" in cells and "A10" in cells["G"]:
        e = c1["units"]["G"]
        pred_cost = e["arms"]["A10"]["pass_cost"]
        obs_cost = cells["G"]["A10"]["pass_cost"]
        a11 = data["G"].get("A11", {})
        queue = sum(1 for r in a11.values() if r.get("decision_token") == 15204)
        verdict["K1f"] = {"pred_pass_cost": pred_cost, "obs_pass_cost": obs_cost,
                          "pred_fail_d2_sum_pi_Pfail": e.get("sum_pi_Pfail_d2"), "queue_term": e.get("queue_term"),
                          "obs_fail_A10": 1 - cells["G"]["A10"]["pass_rate"],
                          "within_0.10": abs(pred_cost - obs_cost) <= THRESH["g_pass_cost_tol"],
                          "A11_queue_slots": queue,
                          "A11_cost_le_A10": (cells["G"]["A11"]["pass_cost"] <= obs_cost) if "A11" in cells["G"]
                          else None}
    # disconfirming
    disc = {"share": [], "cost": [], "reversion": verdict["K1e"]["pooled_reversion"]}
    for unit, e in c1["units"].items():
        if e.get("role") != "collapsed" or unit not in cells:
            continue
        for a in FORK:
            if a in cells[unit]:
                disc["share"].append(cells[unit][a]["off_default_correct"] - cells[unit]["A0"]["off_default_correct"])
                disc["cost"].append(cells[unit][a]["pass_cost"])
    verdict["disconfirming"] = {
        "share_below_0.10_everywhere": bool(disc["share"]) and all(x < THRESH["disconfirm_share"] for x in disc["share"]),
        "cost_above_0.10": any(x > THRESH["disconfirm_cost"] for x in disc["cost"]),
        "reversion_above_0.30": (disc["reversion"] or 0) > THRESH["disconfirm_reversion"], "values": disc}
    # secondary: exact McNemar on correct off-default flips, A10 vs A3g (collapsed units)
    sec = {}
    for unit, e in c1["units"].items():
        if e.get("role") != "collapsed" or unit not in data:
            continue
        A, G = data[unit].get("A10", {}), data[unit].get("A3g", {})
        default = UNITS[unit]["default"]

        def cod(r):
            return bool(r["passed"]) and r["cls"] not in (default, "other", "invalid")
        sl = [s for s in A if s in G]
        b = sum(1 for s in sl if cod(A[s]) and not cod(G[s]))
        c = sum(1 for s in sl if cod(G[s]) and not cod(A[s]))
        sec[unit] = {"b_A10_only": b, "c_A3g_only": c, "p_one_sided": PR.mcnemar_exact(b, c, "greater")}
    verdict["secondary_mcnemar_A10_vs_A3g"] = sec
    return verdict


if __name__ == "__main__":
    import json
    adj_p = RESULTS_DIR / "adjudicated_labels.json"
    adj = read_json(adj_p) if adj_p.exists() else None
    v = run(adj)
    write_json(RESULTS_DIR / "k1_cells.json", v["cells"])
    write_json(RESULTS_DIR / "k1_verdict.json", {k: x for k, x in v.items() if k != "cells"})
    print(json.dumps({k: x for k, x in v.items() if k not in ("cells", "K1b")}, indent=1, default=str)[:3000])
