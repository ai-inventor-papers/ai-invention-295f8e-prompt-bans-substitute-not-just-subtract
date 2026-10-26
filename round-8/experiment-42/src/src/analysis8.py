#!/usr/bin/env python3
"""Iteration-8 statistics (committed in #0 by sha256 before any sample): per-cell summaries, the headline 2x2
{prompt, dial} x {c* prefilled, free}, paired exact McNemar tests on CRN slots, Holm, Wilson and paired Newcombe
intervals, the slot bootstrap of the interaction, the free-dial decomposition by reach type, P1-P7 and the
dormancy verdicts. Inputs: data/labels.jsonl (one row per program), predictions/commit*.json, results/tf_stage.json
and results/dormancy.json. Pure Python + numpy/scipy; audit/rederive.py re-derives the headline numbers with the
standard library only."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any, Iterable

import numpy as np

from cfg8 import (DORMANT_FORWARD, DORMANT_RETENTION, DORMANT_REVERSE, FREE_CORE, FREE_OPTIONAL, HELD_W, MIN_DENOM_NAT,
                  N_BOOT_SLOTS, P1_MIN_CORRECT, P2_MIN_CORRECT, P3_REACH, P4_AGREE, P7_TOL, PASS_RATIO, Q_ID,
                  REV_GEN_MIN_DENOM, TARGET_OF, TRAIN_W)

INVALID = ("invalid",)
OTHER = ("other",)
DISPUTED = ("disputed",)


# ================================================================================================ basic statistics
def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def binom_tail_ge(k: int, n: int) -> float:
    """P(X >= k), X ~ Bin(n, 1/2)."""
    if n == 0:
        return 1.0
    return sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n


def mcnemar_exact(b: int, c: int, alternative: str = "two-sided") -> float:
    """Exact McNemar on discordant pairs. b = #(A yes, B no), c = #(A no, B yes).
    'greater' tests A > B (p = P(X >= b | n = b + c)); 'less' tests A < B; two-sided doubles the smaller tail."""
    n = b + c
    if n == 0:
        return 1.0
    if alternative == "greater":
        return binom_tail_ge(b, n)
    if alternative == "less":
        return binom_tail_ge(c, n)
    return min(1.0, 2 * min(binom_tail_ge(b, n), binom_tail_ge(c, n)))


def holm(pvals: dict[str, float]) -> dict[str, float]:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    out, run = {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        out[k] = run
    return out


def _wilson_interval(x: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    return wilson(x, n, z)


def newcombe_paired(a: int, b: int, c: int, d: int, z: float = 1.959963984540054) -> dict[str, float]:
    """Newcombe (1998) method 10 interval for the difference of paired proportions p1 - p2, where
    a = both yes, b = 1 yes / 2 no, c = 1 no / 2 yes, d = both no."""
    n = a + b + c + d
    if n == 0:
        return {"diff": float("nan"), "lo": float("nan"), "hi": float("nan")}
    p1, p2 = (a + b) / n, (a + c) / n
    l1, u1 = _wilson_interval(a + b, n, z)
    l2, u2 = _wilson_interval(a + c, n, z)
    diff = p1 - p2
    den = math.sqrt(max((a + b) * (c + d) * (a + c) * (b + d), 0))
    if den == 0:
        phi = 0.0
    else:
        num = a * d - b * c
        if num > 0:
            num = max(num - n / 2, 0)
        phi = num / den
    dl2 = (p1 - l1) ** 2 - 2 * phi * (p1 - l1) * (u2 - p2) + (u2 - p2) ** 2
    du2 = (p2 - l2) ** 2 - 2 * phi * (p2 - l2) * (u1 - p1) + (u1 - p1) ** 2
    return {"diff": diff, "lo": diff - math.sqrt(max(dl2, 0)), "hi": diff + math.sqrt(max(du2, 0))}


def hill1_rarefied(labels: list[str], depth: int = 25, n_rep: int = 1000, seed: int = 0) -> float | None:
    """Expected exp(Shannon entropy) of the label distribution in random subsamples of `depth` programs."""
    if not labels:
        return None
    rng = np.random.default_rng(seed)
    arr = np.array(labels)
    d = min(depth, len(arr))
    vals = []
    for _ in range(n_rep):
        s = rng.choice(arr, size=d, replace=False)
        _, cnt = np.unique(s, return_counts=True)
        p = cnt / cnt.sum()
        vals.append(float(np.exp(-(p * np.log(p)).sum())))
    return float(np.mean(vals))


# ================================================================================================ rows and cells
def slot_of(r: dict[str, Any]) -> tuple[str, int]:
    return (str(r["template"]), int(r["slot"]))


def cell_rows(labels: Iterable[dict[str, Any]], cell: str) -> dict[tuple[str, int], dict[str, Any]]:
    return {slot_of(r): r for r in labels if r.get("cell") == cell}


def is_correct(r: dict[str, Any], target: str) -> bool:
    return r.get("label") == target and bool(r.get("passed"))


def summarize_cell(rows: dict[tuple[str, int], dict[str, Any]], target: str,
                   slots: list[tuple[str, int]] | None = None) -> dict[str, Any]:
    rr = [rows[s] for s in (slots if slots is not None else sorted(rows)) if s in rows]
    n = len(rr)
    if n == 0:
        return {"n": 0}
    lab = Counter(r.get("label") for r in rr)
    corr = sum(is_correct(r, target) for r in rr)
    att = sum(r.get("label") == target for r in rr)
    pas = sum(bool(r.get("passed")) for r in rr)
    fork = Counter()
    for r in rr:
        t = r.get("fork_token")
        cls = "B" if t in (107, 584, 15204, 236809) else ("D" if t == 53227 else ("none" if t is None else "O"))
        fork[cls] += 1
    corr_labels = [r.get("label") for r in rr if r.get("passed") and r.get("label") not in INVALID + DISPUTED]
    trunc = sum(r.get("finish_reason") == "length" for r in rr)
    return {"n": n, "target": target, "correct_target": corr, "correct_share": corr / n,
            "correct_ci95": list(wilson(corr, n)), "attempted_target": att, "attempted_share": att / n,
            "attempted_ci95": list(wilson(att, n)), "pass": pas, "pass_rate": pas / n,
            "pass_ci95": list(wilson(pas, n)), "invalid": sum(lab[x] for x in INVALID),
            "other": sum(lab[x] for x in OTHER), "disputed": sum(lab[x] for x in DISPUTED),
            "other_share": sum(lab[x] for x in OTHER) / n, "labels": dict(lab),
            "queue_share": sum(r.get("fork_token") == Q_ID for r in rr) / n, "fork_class": dict(fork),
            "truncated_length": trunc, "truncation_rate": trunc / n,
            "correct_only_hill1_rarefied25": hill1_rarefied(corr_labels)}


def paired(rows_a: dict, rows_b: dict, fa, fb, slots: list[tuple[str, int]] | None = None) -> dict[str, Any]:
    """2x2 table of booleans fa(row of A), fb(row of B) over common slots."""
    common = sorted(set(rows_a) & set(rows_b)) if slots is None else [s for s in slots if s in rows_a and s in rows_b]
    a = b = c = d = 0
    for s in common:
        x, y = fa(rows_a[s]), fb(rows_b[s])
        if x and y:
            a += 1
        elif x and not y:
            b += 1
        elif y and not x:
            c += 1
        else:
            d += 1
    return {"n": len(common), "both": a, "a_only": b, "b_only": c, "neither": d,
            "p_two_sided": mcnemar_exact(b, c, "two-sided"), "p_a_greater": mcnemar_exact(b, c, "greater"),
            "p_a_less": mcnemar_exact(b, c, "less"), "newcombe_diff_a_minus_b": newcombe_paired(a, b, c, d)}


def slot_bootstrap_interaction(cells: dict[str, dict], target: str, slots: list[tuple[str, int]],
                               n_boot: int = N_BOOT_SLOTS, seed: int = 0) -> dict[str, Any]:
    """interaction = (dial - prompt | prefilled) - (dial - prompt | free) on correct-target shares; slots resampled
    with replacement (pairing kept across the four cells)."""
    keys = ("P-DAS-bfs", "G1a", "F-DAS-r4-bfs-1.0", "G1c")
    sl = [s for s in slots if all(s in cells[k] for k in keys)]
    if not sl:
        return {"n": 0}
    M = np.array([[float(is_correct(cells[k][s], target)) for k in keys] for s in sl])
    est = (M[:, 0].mean() - M[:, 1].mean()) - (M[:, 2].mean() - M[:, 3].mean())
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(sl), size=(n_boot, len(sl)))
    Mb = M[idx]                                            # [n_boot, n, 4]
    bs = (Mb[..., 0].mean(1) - Mb[..., 1].mean(1)) - (Mb[..., 2].mean(1) - Mb[..., 3].mean(1))
    return {"n": len(sl), "interaction": float(est), "ci95": [float(np.percentile(bs, 2.5)),
                                                              float(np.percentile(bs, 97.5))],
            "dial_minus_prompt_prefilled": float(M[:, 0].mean() - M[:, 1].mean()),
            "dial_minus_prompt_free": float(M[:, 2].mean() - M[:, 3].mean())}


def corr_fn(target: str):
    return lambda r: is_correct(r, target)


def att_fn(target: str):
    return lambda r: r.get("label") == target


# ================================================================================================ main analysis
def analyze(labels: list[dict[str, Any]], c1: dict[str, Any] | None, c2: dict[str, Any] | None,
            tf: dict[str, Any] | None, dorm: dict[str, Any] | None) -> dict[str, Any]:
    from cfg8 import HT30, S30, S50

    cells_all = sorted({r.get("cell") for r in labels if r.get("cell")})
    C = {c: cell_rows(labels, c) for c in cells_all}
    out: dict[str, Any] = {"cells": {}, "tests": {}, "scorecard": {}, "verdicts": {}}
    for c in cells_all:
        tgt = TARGET_OF.get(c, "bfs")
        sl = S30 if c in ("REV-DAS", "REV-FULL") else S50
        out["cells"][c] = summarize_cell(C[c], tgt, sl)
        out["cells"][c]["by_template_group"] = {
            "train_W1-W3": summarize_cell(C[c], tgt, [s for s in sl if s[0] in TRAIN_W]),
            "heldout_W4-W5": summarize_cell(C[c], tgt, [s for s in sl if s[0] in HELD_W])}
        if any(s in C[c] for s in HT30):
            out["cells"][c]["by_template_group"]["heldout_W4-W5_plus_HT30"] = summarize_cell(
                C[c], tgt, [s for s in sl if s[0] in HELD_W] + HT30)
            out["cells"][c]["HT30_only"] = summarize_cell(C[c], tgt, HT30)
        # vs P-twin (prefilled cells) or vs F-twin (free cells): toward BFS cells also report the other class
        if tgt == "dfs":
            out["cells"][c]["correct_bfs"] = sum(is_correct(r, "bfs") for s, r in C[c].items() if s in sl)
    get = C.get

    def cmp(a: str, b: str, target: str, alt: str = "two-sided", slots=S50) -> dict[str, Any] | None:
        if not get(a) or not get(b):
            return None
        t = paired(C[a], C[b], corr_fn(target), corr_fn(target), slots)
        t["attempted"] = paired(C[a], C[b], att_fn(target), att_fn(target), slots)
        t["pass"] = paired(C[a], C[b], lambda r: bool(r.get("passed")), lambda r: bool(r.get("passed")), slots)
        t["p_used"] = t["p_two_sided"] if alt == "two-sided" else t["p_a_greater"]
        t["alternative"] = alt
        t["a"], t["b"], t["target"] = a, b, target
        return t

    T = out["tests"]
    # ---------------- headline 2x2 toward BFS
    T["dial_vs_prompt_prefilled_P1b"] = cmp("P-DAS-bfs", "G1a", "bfs")
    T["dial_vs_prompt_free"] = cmp("F-DAS-r4-bfs-1.0", "G1c", "bfs")
    T["prefilled_vs_free_dial"] = cmp("P-DAS-bfs", "F-DAS-r4-bfs-1.0", "bfs")
    T["prefilled_vs_free_prompt"] = cmp("G1a", "G1c", "bfs")
    T["dial_prefilled_vs_twin"] = cmp("P-DAS-bfs", "P-twin", "bfs", "greater")
    T["prompt_prefilled_vs_twin"] = cmp("G1a", "P-twin", "bfs", "greater")
    T["prompt_free_vs_free_twin"] = cmp("G1c", "F-twin", "bfs", "greater")
    T["twin_prefilled_vs_free"] = cmp("P-twin", "F-twin", "bfs")
    if all(get(k) for k in ("P-DAS-bfs", "G1a", "F-DAS-r4-bfs-1.0", "G1c")):
        T["interaction_slot_bootstrap"] = slot_bootstrap_interaction(C, "bfs", S50)
    # pass cost of each cell against its own twin (paired Newcombe on pass)
    own_twin = {"P-DAS-bfs": "P-twin", "P-DAS-dfs": "P-twin", "G1a": "P-twin", "G1b": "P-twin", "G1d": "P-twin",
                "G1c": "F-twin"}
    own_twin.update({c: "F-twin" for c in FREE_CORE + FREE_OPTIONAL})
    pc = {}
    for c, tw in own_twin.items():
        if get(c) and get(tw):
            pc[c] = {"twin": tw, **paired(C[c], C[tw], lambda r: bool(r.get("passed")),
                                          lambda r: bool(r.get("passed")), S50)}
    T["pass_cost_vs_own_twin"] = pc
    # ---------------- toward DFS
    T["dfs_free_dial_vs_prefilled_dial"] = cmp("F-DAS-r4-dfs-1.0", "P-DAS-dfs", "dfs")
    T["dfs_prefilled_dial_vs_prompt"] = cmp("P-DAS-dfs", "G1b", "dfs")
    T["dfs_free_dial_vs_free_twin"] = cmp("F-DAS-r4-dfs-1.0", "F-twin", "dfs", "greater")
    T["dfs_prefilled_dial_vs_twin"] = cmp("P-DAS-dfs", "P-twin", "dfs", "greater")
    T["dfs_prompt_prefilled_vs_twin"] = cmp("G1b", "P-twin", "dfs", "greater")
    T["dfs_free_dim_vs_free_twin"] = cmp("F-DiM-dfs", "F-twin", "dfs", "greater")
    # ---------------- G2 Holm family: free DAS toward BFS vs F-twin (one-sided)
    fam = {}
    for c in ("F-DAS-r4-bfs-1.0", "F-DAS-r4-bfs-0.5", "F-DAS-r1-bfs-1.0", "F-DAS-r1-bfs-0.5"):
        t = cmp(c, "F-twin", "bfs", "greater")
        if t:
            fam[c] = t
    hp = holm({c: t["p_a_greater"] for c, t in fam.items()}) if fam else {}
    for c in fam:
        fam[c]["p_holm"] = hp[c]
    T["G2_holm_family"] = fam
    for c in ("F-DiM-bfs", "F-RAND-r4-1.0", "F-DAS-s2-r4-bfs-1.0"):
        T[f"{c}_vs_F-twin"] = cmp(c, "F-twin", "bfs", "greater")
    T["F-DiM-bfs_vs_F-DAS-r4-bfs-1.0"] = cmp("F-DAS-r4-bfs-1.0", "F-DiM-bfs", "bfs", "greater")
    # held-out extension (HT30 pooled with W4/W5 S50 slots) for the two key cells
    if get("F-twin") and get("F-DAS-r4-bfs-1.0"):
        hs = [s for s in S50 if s[0] in HELD_W] + HT30
        T["heldout_plus_HT30_free_dial_vs_free_twin"] = cmp("F-DAS-r4-bfs-1.0", "F-twin", "bfs", "greater", hs)
    # ---------------- decomposition by reach type (commit #2)
    dec = {}
    if c2:
        reach = {tuple(k.split("|")[:1]) + (int(k.split("|")[1]),): v for k, v in c2["slots"].items()}
        rt = Counter(v["reach_type"] for (w, k), v in reach.items() if (w, k) in S50)
        n50 = sum(rt.values())
        dec["reach_counts_S50"] = dict(rt)
        dec["reach_share_S50"] = (rt.get("R1", 0) + rt.get("R2", 0)) / max(n50, 1)
        dec["R1_share_S50"] = rt.get("R1", 0) / max(n50, 1)
        by = {}
        for c in ("F-twin",) + FREE_CORE + FREE_OPTIONAL:
            if not get(c):
                continue
            tgt = TARGET_OF[c]
            d = {}
            for typ in ("R1", "R2", "NOT_REACHED"):
                sl = [s for s in S50 if reach.get(s, {}).get("reach_type") == typ]
                d[typ] = summarize_cell(C[c], tgt, sl)
            pred = (c2.get("predictions") or {}).get(c)
            obs = out["cells"][c]["correct_target"] if out["cells"].get(c, {}).get("n") else None
            d["predicted_correct_target"] = pred.get("total") if pred else None
            d["observed_correct_target"] = obs
            by[c] = d
        dec["by_cell"] = by
        # P4: agreement on R1 slots between free and prefilled programs
        r1 = [s for s in S50 if reach.get(s, {}).get("reach_type") == "R1"]
        agr = {}
        for fcell, pcell in (("F-twin", "P-twin"), ("F-DAS-r4-bfs-1.0", "P-DAS-bfs"), ("F-DAS-r4-dfs-1.0", "P-DAS-dfs")):
            if get(fcell) and get(pcell):
                cm = [s for s in r1 if s in C[fcell] and s in C[pcell]]
                same_lab = sum(C[fcell][s].get("label") == C[pcell][s].get("label") for s in cm)
                same_lp = sum(C[fcell][s].get("label") == C[pcell][s].get("label") and
                              bool(C[fcell][s].get("passed")) == bool(C[pcell][s].get("passed")) for s in cm)
                same_code = sum((C[fcell][s].get("code_sha256") is not None) and
                                C[fcell][s].get("code_sha256") == C[pcell][s].get("code_sha256") for s in cm)
                agr[f"{fcell}~{pcell}"] = {"n_R1": len(cm), "label_agreement": same_lab / max(len(cm), 1),
                                           "label_pass_agreement": same_lp / max(len(cm), 1),
                                           "identical_code_share": same_code / max(len(cm), 1)}
        dec["R1_free_vs_prefilled_agreement"] = agr
        # prefix check
        pm = [r for c in FREE_CORE + FREE_OPTIONAL for r in (C.get(c) or {}).values() if r.get("prefix_match") is False]
        dec["prefix_mismatch_rows"] = len(pm)
    out["decomposition"] = dec
    # ---------------- restoration in generation (reverse, k = 4)
    rev = {}
    if get("REV-DAS") and get("REV-FULL") and get("G1a"):
        base = sum(is_correct(C["G1a"][s], "dfs") for s in S30 if s in C["G1a"])
        das = sum(is_correct(C["REV-DAS"][s], "dfs") for s in S30 if s in C["REV-DAS"])
        full = sum(is_correct(C["REV-FULL"][s], "dfs") for s in S30 if s in C["REV-FULL"])
        abase = sum(C["G1a"][s].get("label") == "dfs" for s in S30 if s in C["G1a"])
        adas = sum(C["REV-DAS"][s].get("label") == "dfs" for s in S30 if s in C["REV-DAS"])
        afull = sum(C["REV-FULL"][s].get("label") == "dfs" for s in S30 if s in C["REV-FULL"])
        den = full - base
        rev = {"correct_dfs": {"G1a_S30": base, "REV-DAS": das, "REV-FULL": full},
               "attempted_dfs": {"G1a_S30": abase, "REV-DAS": adas, "REV-FULL": afull},
               "restoration_gen": (das - base) / den if den > REV_GEN_MIN_DENOM else None,
               "restoration_gen_attempted": ((adas - abase) / (afull - abase)) if (afull - abase) > REV_GEN_MIN_DENOM
               else None,
               "defined": den > REV_GEN_MIN_DENOM,
               "REV-DAS_vs_G1a": cmp("REV-DAS", "G1a", "dfs", "greater", S30),
               "REV-FULL_vs_G1a": cmp("REV-FULL", "G1a", "dfs", "greater", S30)}
    out["reverse_generation"] = rev
    # ---------------- scorecard
    S = out["scorecard"]
    cg = out["cells"]
    if cg.get("G1a", {}).get("n"):
        S["P1"] = {"observed": cg["G1a"]["correct_target"], "threshold": P1_MIN_CORRECT,
                   "holds": cg["G1a"]["correct_target"] >= P1_MIN_CORRECT}
    t = T.get("dial_vs_prompt_prefilled_P1b")
    if t:
        if t["p_two_sided"] >= 0.05:
            name = "MATCHES (not distinguishable at N = 50)"
        elif t["a_only"] > t["b_only"]:
            name = "DIAL BEATS MATCHED PROMPTING"
        else:
            name = "DIAL LOSES TO MATCHED PROMPTING"
        S["P1b"] = {"p_two_sided": t["p_two_sided"], "discordant_dial_only": t["a_only"],
                    "discordant_prompt_only": t["b_only"], "outcome": name, "holds": t["p_two_sided"] >= 0.05}
    if cg.get("F-DAS-r4-bfs-1.0", {}).get("n") and cg.get("F-twin", {}).get("n"):
        f, tw = cg["F-DAS-r4-bfs-1.0"], cg["F-twin"]
        tt = T["G2_holm_family"].get("F-DAS-r4-bfs-1.0")
        c_ok = f["correct_target"] >= P2_MIN_CORRECT
        p_ok = f["pass_rate"] >= PASS_RATIO * tw["pass_rate"]
        m_ok = bool(tt and f["correct_target"] > tw["correct_target"] and tt["p_a_greater"] < 0.05)
        S["P2"] = {"correct": f["correct_target"], "pass": f["pass_rate"], "free_twin_pass": tw["pass_rate"],
                   "free_twin_correct": tw["correct_target"], "p_vs_free_twin": tt["p_a_greater"] if tt else None,
                   "correct_ok": c_ok, "pass_ok": p_ok, "beats_twin_ok": m_ok, "holds": c_ok and p_ok and m_ok}
    if dec:
        S["P3"] = {"reach_share": dec["reach_share_S50"], "R1_share": dec["R1_share_S50"], "threshold": P3_REACH,
                   "holds": dec["reach_share_S50"] >= P3_REACH}
        ag = dec.get("R1_free_vs_prefilled_agreement", {})
        need = [ag.get("F-twin~P-twin"), ag.get("F-DAS-r4-bfs-1.0~P-DAS-bfs")]
        if all(need):
            S["P4"] = {"twin_label_agreement": need[0]["label_agreement"],
                       "das_label_agreement": need[1]["label_agreement"], "threshold": P4_AGREE,
                       "holds": all(x["label_agreement"] >= P4_AGREE for x in need)}
    if cg.get("F-DiM-bfs", {}).get("n") and cg.get("F-twin", {}).get("n"):
        S["P6"] = {"dim_pass": cg["F-DiM-bfs"]["pass_rate"], "free_twin_pass": cg["F-twin"]["pass_rate"],
                   "holds": cg["F-DiM-bfs"]["pass_rate"] < PASS_RATIO * cg["F-twin"]["pass_rate"]}
    if tf:
        gaps = {}
        for c in ("P-twin", "P-DAS-bfs", "P-DAS-dfs", "G1a", "G1b", "G1d"):
            if cg.get(c, {}).get("n") and c in (tf.get("cell_predictions") or {}):
                pred = tf["cell_predictions"][c]["pred_attempted_bfs"]
                obs = cg[c]["labels"].get("bfs", 0) / cg[c]["n"]
                gaps[c] = {"pred_attempted_bfs": pred, "obs_attempted_bfs": obs, "abs_gap": abs(pred - obs)}
        if gaps:
            S["P7"] = {"by_cell": gaps, "max_abs_gap": max(g["abs_gap"] for g in gaps.values()), "tol": P7_TOL,
                       "holds": all(g["abs_gap"] <= P7_TOL for g in gaps.values())}
    if dorm:
        sm = dorm.get("summary_by_k") or {}
        k4 = sm.get("4") or {}
        S["P5"] = {"k4": k4, "prediction": "reverse recovery >= 0.5 and retention >= 0.5 at k = 4 (D5/K2); "
                                          "LOW_NATURAL_VARIANCE at k = 1, 2, 4 (iteration-7 numbers)"}
        if k4:
            S["P5"]["account_holds"] = bool((k4.get("reverse_recovery") is not None and k4["reverse_recovery"] >= 0.5)
                                            and (k4.get("retention") is not None and k4["retention"] >= 0.5))
            S["P5"]["low_variance_k124"] = {k: (sm.get(k) or {}).get("LOW_NATURAL_VARIANCE") for k in ("1", "2", "4")}
            S["P5"]["low_variance_prediction_holds"] = all(S["P5"]["low_variance_k124"].values())
    # ---------------- verdicts
    V = out["verdicts"]
    if "P1" in S and "P1b" in S:
        V["G-PROMPT"] = {"P1": S["P1"]["holds"], "outcome": S["P1b"]["outcome"]}
    if "P2" in S:
        V["G-FREE"] = "free-generation knob" if S["P2"]["holds"] else "the dial works only with a teacher-forced prefill"
    if dorm:
        V["G-DORMANCY"] = {k: v.get("verdict") for k, v in (dorm.get("summary_by_k") or {}).items()}
    _ = (MIN_DENOM_NAT, DORMANT_FORWARD, DORMANT_RETENTION, DORMANT_REVERSE, defaultdict)
    return out


# ================================================================================================ dormancy rule
def dormancy_verdict(forward_rec: float | None, reverse_rec: float | None, reverse_defined: bool,
                     retention: float | None, share: float, random_p95: float) -> dict[str, Any]:
    """Committed classification for one rank k (see cfg8.DECISION_RULES)."""
    low = bool(share <= random_p95)
    arm_ret = retention is not None and retention < DORMANT_RETENTION
    arm_rev = reverse_defined and reverse_rec is not None and reverse_rec < DORMANT_REVERSE
    fwd_ok = forward_rec is not None and forward_rec >= DORMANT_FORWARD
    flag = bool(fwd_ok and (arm_ret or arm_rev))
    if flag:
        v = "DORMANT/OFF-MANIFOLD HANDLE"
    elif not reverse_defined and (retention is None or retention >= DORMANT_RETENTION):
        v = "UNDETERMINED"
    elif low:
        v = "SUFFICIENT, LOW-VARIANCE"
    else:
        v = "USED VARIABLE"
    return {"DORMANT_FLAG": flag, "LOW_NATURAL_VARIANCE": low, "retention_arm": bool(arm_ret),
            "reverse_arm": bool(arm_rev), "forward_ok": bool(fwd_ok), "verdict": v}


# ================================================================================================ iteration-7 check
def iter7_reproduction(i7_labels: list[dict[str, Any]]) -> dict[str, Any]:
    """Re-derive iteration 7's dose-sweep record (twin 11, DAS lambda 1 42, forced F5 35, McNemar) from its rows."""
    def rows(prefix: str) -> dict[tuple[str, int], dict[str, Any]]:
        out = {}
        for r in i7_labels:
            rid = r.get("row_id", "")
            if rid.startswith(prefix + "|"):
                w, k = rid.split("|")[-2:]
                out[(w, int(k))] = r
        return out
    tw, das, f5 = rows("g2|twin"), rows("g2|DAS|bfs|1.0"), rows("g2|forced_bfs_F5")
    t1 = paired(das, tw, corr_fn("bfs"), corr_fn("bfs"))
    t2 = paired(f5, tw, corr_fn("bfs"), corr_fn("bfs"))
    t3 = paired(das, f5, corr_fn("bfs"), corr_fn("bfs"))
    return {"twin": summarize_cell(tw, "bfs"), "das_lam1": summarize_cell(das, "bfs"),
            "forced_f5_unprefilled": summarize_cell(f5, "bfs"),
            "mcnemar_das_vs_twin": {"b": t1["a_only"], "c": t1["b_only"], "p_one_sided": t1["p_a_greater"]},
            "mcnemar_f5_vs_twin": {"b": t2["a_only"], "c": t2["b_only"], "p_one_sided": t2["p_a_greater"]},
            "mcnemar_das_vs_f5": {"b": t3["a_only"], "c": t3["b_only"], "p_two_sided": t3["p_two_sided"]}}
