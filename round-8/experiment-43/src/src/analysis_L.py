#!/usr/bin/env python3
"""analysis_L (S7, frozen before any sweep sample; sha256 in COMMIT #2): scoring of claim L.

Per unit and cell: observed attempted-label distribution (Wilson CIs), correct shares and pass rate; MAE_u of the law
(L) and the baselines B0 (flat), B1 (algorithm-level tempering), B2 (single-decision law), BH (entropy-located rival);
the drop T 1.0 -> 0.3 of the T-1 minority with an exact one-sided McNemar test on paired slots; per-slot replay
accuracy, replay-implied shares, realisation gap (observed vs replay-implied) and mechanism gap (replay-implied vs
predicted); H(A | classes) committed and sweep-observed; the verdict; placebos (temperature permutation, token-map
shuffle, temperature-label shuffle for the drop); the B3 stream-lean test; diversity (correct-only Hill-1 rarefied at
depth 25, pass cost with Newcombe intervals, phrasing clusters by identifier-normalised AST 4-gram Jaccard 0.8).
Writes results/analysis_L.json and results/verdict.json.
"""

from __future__ import annotations

import ast
import itertools
import math
import sys
from collections import Counter
from typing import Any

import numpy as np
from loguru import logger
from scipy.stats import binomtest, fisher_exact

import predict8 as P8
from cfg8 import (LABELS, RESULTS_DIR, SAMPLES_RAW, SWEEP_SLOTS, TEMPLATES, TEMPS, THRESH, UNITS, BOOT_SEED,
                  read_json, read_jsonl, setup_logging, write_json)

Z95 = 1.959963984540054


def wilson(k: int, n: int) -> list[float]:
    if n == 0:
        return [float("nan"), float("nan")]
    p = k / n
    den = 1 + Z95 ** 2 / n
    c = (p + Z95 ** 2 / (2 * n)) / den
    h = Z95 * math.sqrt(p * (1 - p) / n + Z95 ** 2 / (4 * n * n)) / den
    return [max(0.0, c - h), min(1.0, c + h)]


def newcombe(k1: int, n1: int, k2: int, n2: int) -> list[float]:
    """Newcombe hybrid score interval for p1 - p2 (independent proportions)."""
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    d = p1 - p2
    return [d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)]


def to_bin(label: str | None, bins: list[str]) -> str:
    if label in bins:
        return label
    return "invalid" if label in ("invalid", "no_code") else "other"


def mcnemar_one_sided(b: int, c: int) -> float:
    return float(binomtest(b, b + c, 0.5, alternative="greater").pvalue) if b + c else 1.0


def hill1_rarefied(labels: list[str], depth: int = 25, n_rep: int = 200, seed: int = 0) -> dict[str, Any]:
    if len(labels) < depth:
        c = Counter(labels)
        p = np.array(list(c.values()), float) / max(len(labels), 1)
        return {"hill1": float(np.exp(-(p * np.log(p)).sum())) if len(labels) else None, "n": len(labels),
                "rarefied": False}
    rng = np.random.default_rng(seed)
    arr = np.array(labels)
    vals = []
    for _ in range(n_rep):
        sub = rng.choice(arr, depth, replace=False)
        c = Counter(sub)
        p = np.array(list(c.values()), float) / depth
        vals.append(float(np.exp(-(p * np.log(p)).sum())))
    return {"hill1": float(np.mean(vals)), "n": len(labels), "rarefied": True}


def ast_4grams(code: str) -> set[tuple[str, ...]] | None:
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return None
    seq = [type(n).__name__ for n in ast.walk(tree)]
    return set(zip(seq, seq[1:], seq[2:], seq[3:]))


def phrasing_clusters(codes: list[str], thr: float = 0.8) -> int:
    """Leader clustering of identifier-normalised AST node-type 4-gram sets at Jaccard >= thr."""
    leaders: list[set] = []
    for c in codes:
        g = ast_4grams(c)
        if g is None:
            continue
        for L in leaders:
            if len(g | L) and len(g & L) / len(g | L) >= thr:
                break
        else:
            leaders.append(g)
    return len(leaders)


def code_of(text: str) -> str:
    import oc8
    return oc8.code_part(text)


# ------------------------------------------------------------------------------------------------ per unit
def unit_analysis(unit: str, rows: list[dict[str, Any]], labs: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    pred_p = RESULTS_DIR / f"predict_{unit}.json"
    loc_p = RESULTS_DIR / f"locate_{unit}.json"
    if not pred_p.exists() or not loc_p.exists():
        return None
    pred = read_json(pred_p)
    loc = read_json(loc_p)
    bins = pred["bins"]
    nb = len(bins)
    sw = [r for r in rows if r["unit"] == unit and r["arm"] in ("sweep", "topk")]
    if not sw:
        return None
    obs: dict[str, dict[float, np.ndarray]] = {"p1": {}, "k10": {}}
    cells: dict[str, Any] = {}
    slot_lab: dict[tuple[str, float], dict[tuple[str, int], str]] = {}
    for sname, arm in (("p1", "sweep"), ("k10", "topk")):
        for T in TEMPS:
            rr = [r for r in sw if r["arm"] == arm and abs(r["T"] - T) < 1e-9]
            lb = [to_bin(labs.get(r["sid"], {}).get("label"), bins) for r in rr]
            ok = [bool(labs.get(r["sid"], {}).get("passed")) for r in rr]
            slot_lab[(sname, T)] = {(r["template"], r["slot"]): l for r, l in zip(rr, lb)}
            n = len(rr)
            c = Counter(lb)
            v = np.array([c.get(b, 0) for b in bins], float)
            obs[sname][T] = v / n if n else v
            corr = Counter(l for l, o in zip(lb, ok) if o)
            pk = f"{sname}|{T}"
            cells[pk] = {"N": n, "counts": {b: int(c.get(b, 0)) for b in bins},
                         "shares": (v / n).tolist() if n else None,
                         "wilson": {b: wilson(int(c.get(b, 0)), n) for b in bins},
                         "correct_shares": {b: corr.get(b, 0) / n for b in bins} if n else None,
                         "pass_rate": float(np.mean(ok)) if n else None, "n_pass": int(sum(ok)),
                         "pred": {m: pred["cells"][pk][m] for m in ("L", "B0", "B1", "B2", "BH")},
                         "replay_implied": pred["replay_implied"][pk], "on_opening_pred": pred["cells"][pk]["on_opening"],
                         "cap_hits": sum(r["finish_reason"] == "length" for r in rr),
                         "hill1_correct": hill1_rarefied([l for l, o in zip(lb, ok) if o])}
    maes = {}
    for sname in ("p1", "k10"):
        if len(obs[sname]) < 4 or any(cells[f"{sname}|{T}"]["N"] == 0 for T in TEMPS):
            continue
        maes[sname] = {m: P8.mae({T: np.asarray(pred["cells"][f"{sname}|{T}"][m]) for T in TEMPS}, obs[sname])
                       for m in ("L", "B0", "B1", "B2", "BH")}
        maes[sname]["replay_implied"] = P8.mae({T: np.asarray(pred["replay_implied"][f"{sname}|{T}"]) for T in TEMPS},
                                               obs[sname])
    minority = loc["minority"]
    j = bins.index(minority) if minority in bins else None
    min_mae = None
    if j is not None:
        min_mae = {m: float(np.mean([abs(pred["cells"][f"p1|{T}"][m][j] - obs["p1"][T][j]) for T in TEMPS]))
                   for m in ("L", "B0", "B1", "B2", "BH")}
    # 7.3 drop T 1.0 -> 0.3 with exact one-sided McNemar on paired slots
    drop = None
    if j is not None:
        a = slot_lab[("p1", 1.0)]
        b_ = slot_lab[("p1", 0.3)]
        keys = sorted(set(a) & set(b_))
        nb_ = sum(a[k] == minority and b_[k] != minority for k in keys)
        nc_ = sum(a[k] != minority and b_[k] == minority for k in keys)
        drop = {"minority": minority, "obs_T1": float(obs["p1"][1.0][j]), "obs_T03": float(obs["p1"][0.3][j]),
                "obs_drop": float(obs["p1"][1.0][j] - obs["p1"][0.3][j]),
                "pred_drop": pred["predicted_drop"]["pred_drop"] if pred.get("predicted_drop") else None,
                "mcnemar_b_c": [nb_, nc_], "p_one_sided": mcnemar_one_sided(nb_, nc_)}
        # placebo: temperature labels shuffled within slots (500 permutations)
        rng = np.random.default_rng(BOOT_SEED)
        allT = {T: slot_lab[("p1", T)] for T in TEMPS}
        hits = 0
        for _ in range(500):
            b2 = c2 = 0
            for k in keys:
                labsT = [allT[T].get(k) for T in TEMPS]
                perm = rng.permutation(4)
                x1, x03 = labsT[perm[2]], labsT[perm[0]]
                b2 += x1 == minority and x03 != minority
                c2 += x1 != minority and x03 == minority
            hits += mcnemar_one_sided(b2, c2) < 0.05
        drop["placebo_temp_shuffle_reject_rate"] = hits / 500
    # 7.4 replay accuracy
    rep = {}
    for sname in ("p1", "k10"):
        for T in TEMPS:
            n_on = acc = 0
            for (w, s), l in slot_lab[(sname, T)].items():
                r = pred["replay"].get(f"{w}|{s}|{sname}|{T}")
                if r and r["status"] == "on" and r["alg_idx"] is not None:
                    n_on += 1
                    acc += bins[r["alg_idx"]] == l
            pk = f"{sname}|{T}"
            rep[pk] = {"n_on_opening_replay": n_on, "accuracy": acc / n_on if n_on else None,
                       "realisation_gap_tvd": P8.tvd(obs[sname][T], pred["replay_implied"][pk]) if T in obs[sname]
                       else None,
                       "mechanism_gap_tvd": P8.tvd(pred["replay_implied"][pk], pred["cells"][pk]["L"])}
    # 7.5 H committed and sweep-observed at T 1.0 (on-opening programs grouped by their generated class at d)
    H_comm = loc.get("H_unit_bits")
    H_obs = None
    if loc["openings"]:
        groups: dict[str, Counter] = {}
        rr = [r for r in sw if r["arm"] == "sweep" and abs(r["T"] - 1.0) < 1e-9]
        for r in rr:
            g = r["token_ids"]
            for o in loc["openings"]:
                d = o["d"]
                if len(g) > d and g[:d] == o["O"]:
                    t1 = g[d]
                    key = o["classes"]["class_of"].get(str(t1), o["classes"]["class_of"]["resid"])
                    sec = o.get("second", {}).get(str(t1))
                    if sec and sec.get("found"):
                        d2 = sec["d2"]
                        if len(g) > d2 and g[d + 1:d2] == sec["O2"]:
                            p2 = sec["phat2"].get(str(g[d2]))
                            if p2 is not None:
                                jj = int(np.argmax(p2))
                                key += ">" + (bins[jj] if p2[jj] >= 0.7 else "UNDECIDED")
                            else:
                                key += ">resid2"
                        else:
                            key += ">off"
                    groups.setdefault(f"{o['id']}:{key}", Counter())[to_bin(labs.get(r["sid"], {}).get("label"),
                                                                               bins)] += 1
                    break
        tot = sum(sum(c.values()) for c in groups.values())
        if tot:
            H_obs = sum((sum(c.values()) / tot) * P8.entropy_bits(np.array(list(c.values()), float) / sum(c.values()))
                        for c in groups.values())
    # 7.6 slot bootstrap CIs of MAE differences (p1)
    boot = {}
    if "p1" in maes:
        keys = sorted(slot_lab[("p1", 1.0)])
        rng = np.random.default_rng(BOOT_SEED + 1)
        diffs = {"L-B0": [], "L-B1": [], "L-B2": [], "L-BH": []}
        for _ in range(1000):
            idx = rng.integers(0, len(keys), len(keys))
            ob = {}
            for T in TEMPS:
                c = Counter(slot_lab[("p1", T)].get(keys[i]) for i in idx)
                v = np.array([c.get(b, 0) for b in bins], float)
                ob[T] = v / v.sum()
            mL = P8.mae({T: np.asarray(pred["cells"][f"p1|{T}"]["L"]) for T in TEMPS}, ob)
            for m in ("B0", "B1", "B2", "BH"):
                diffs[f"L-{m}"].append(mL - P8.mae({T: np.asarray(pred["cells"][f"p1|{T}"][m]) for T in TEMPS}, ob))
        boot = {k: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] for k, v in diffs.items()}
    # 7.7 placebos: temperature permutation of the predictions
    perm = None
    if "p1" in maes:
        true = sum(P8.tvd(pred["cells"][f"p1|{T}"]["L"], obs["p1"][T]) for T in TEMPS)
        vals = []
        for pm in itertools.permutations(range(4)):
            if pm == (0, 1, 2, 3):
                continue
            vals.append(sum(P8.tvd(pred["cells"][f"p1|{TEMPS[pm[i]]}"]["L"], obs["p1"][T]) for i, T in enumerate(TEMPS)))
        perm = {"true_sum_tvd": true, "n_perm": len(vals), "n_perm_le_true": int(sum(v <= true + 1e-12 for v in vals)),
                "p5": float(np.percentile(vals, 5)), "below_p5": bool(true < np.percentile(vals, 5))}
    # token-map shuffle (Phat rows permuted across the first-decision tokens within each opening)
    tmap = token_map_placebo(pred, loc, obs["p1"]) if ("p1" in maes and loc["openings"]) else None
    # diversity and phrasing
    div = {}
    for sname, arm in (("p1", "sweep"), ("k10", "topk")):
        for T in TEMPS:
            rr = [r for r in sw if r["arm"] == arm and abs(r["T"] - T) < 1e-9]
            per_alg: dict[str, list[str]] = {}
            for r in rr:
                l = to_bin(labs.get(r["sid"], {}).get("label"), bins)
                if l in ("other", "invalid"):
                    continue
                per_alg.setdefault(l, []).append(code_of(r["text"]))
            div[f"{sname}|{T}"] = {a: {"n": len(cs), "phrasing_clusters_j08": phrasing_clusters(cs)}
                                   for a, cs in per_alg.items()}
    c1 = cells["p1|1.0"]
    pass_cost = {f"{T}": newcombe(cells[f"p1|{T}"]["n_pass"], cells[f"p1|{T}"]["N"], c1["n_pass"], c1["N"])
                 for T in TEMPS if T != 1.0}
    spec = UNITS[unit]
    boundary = loc["boundary"]
    mae_L = maes.get("p1", {}).get("L")
    H_u = H_comm
    passes = None if mae_L is None else bool(mae_L <= THRESH["unit_mae_pass"] and
                                             (boundary or (H_u is not None and H_u <= THRESH["unit_H_bits_pass"])))
    return {"unit": unit, "family": spec["family"], "held_out": spec["held_out"], "bins": bins,
            "default": loc["default"], "minority": minority, "boundary": boundary, "cells": cells, "mae": maes,
            "minority_mae": min_mae, "drop": drop, "replay": rep, "H_committed": H_comm, "H_sweep_T1": H_obs,
            "bootstrap_mae_diff_p1": boot, "placebo_temperature_permutation": perm, "placebo_token_map": tmap,
            "phrasing": div, "pass_cost_vs_T1_newcombe": pass_cost, "pass": passes,
            "decision_spread": any(o.get("decision_spread") for o in loc["openings"])}


def token_map_placebo(pred: dict[str, Any], loc: dict[str, Any], obs: dict[float, np.ndarray],
                      n: int = 200) -> dict[str, Any]:
    rng = np.random.default_rng(BOOT_SEED + 2)
    tfw = pred["tf_compact"]
    law0 = {"q_rest": loc["q_rest"], "openings": loc["openings"]}

    def mae_of(law: dict[str, Any]) -> float:
        P = {T: P8.cell_prediction(law, tfw, T, "p1")["P"] for T in TEMPS}
        return P8.mae(P, obs)
    true = mae_of(law0)
    vals = []
    for _ in range(n):
        ops = []
        for o in loc["openings"]:
            toks = [str(t) for t in o["tokens"]]
            perm = rng.permutation(len(toks))
            ph = {toks[i]: o["phat"][toks[perm[i]]] for i in range(len(toks))}
            ops.append({**o, "phat": ph, "second": {}})
        vals.append(mae_of({"q_rest": loc["q_rest"], "openings": ops}))
    return {"true_mae": true, "n": n, "placebo_mae_median": float(np.median(vals)),
            "p_le_true": float((1 + sum(v <= true for v in vals)) / (n + 1))}


# ------------------------------------------------------------------------------------------------ verdict
def verdict(units: dict[str, Any]) -> dict[str, Any]:
    scored = {u: a for u, a in units.items() if a and a["pass"] is not None}
    held = {u: a for u, a in scored.items() if a["held_out"]}
    n_pass = sum(a["pass"] for a in scored.values())
    n_held_pass = sum(a["pass"] for a in held.values())
    frac = n_pass / len(scored) if scored else 0.0
    claim_pass = frac >= THRESH["claim_frac_pass"] and n_held_pass >= THRESH["heldout_pass_min"] and \
        len(held) >= THRESH["heldout_scored_min"]
    n_bad_held = sum(a["mae"]["p1"]["L"] > THRESH["disconfirm_mae"] for a in held.values())
    disconf = n_bad_held >= THRESH["disconfirm_heldout_n"]
    status = "PASS" if claim_pass else ("DISCONFIRMED" if disconf else "PARTIAL")
    if not claim_pass and len(held) < THRESH["heldout_scored_min"]:
        status += " (held-out criterion underpowered: fewer than 4 held-out units scored)"
    wins = [a["mae"]["p1"]["L"] < a["mae"]["p1"]["B0"] for a in scored.values()
            if a["mae"]["p1"]["L"] != a["mae"]["p1"]["B0"]]
    p_sign = float(binomtest(sum(wins), len(wins), 0.5, alternative="greater").pvalue) if wins else None
    vs = {m: {"n_L_better": sum(a["mae"]["p1"]["L"] < a["mae"]["p1"][m] for a in scored.values()),
              "n": len(scored)} for m in ("B0", "B1", "B2", "BH")}
    return {"status": status, "n_scored": len(scored), "n_pass": n_pass, "frac_pass": frac,
            "n_heldout_scored": len(held), "n_heldout_pass": n_held_pass, "n_heldout_mae_gt_0.2": n_bad_held,
            "per_unit": {u: {"mae_L": a["mae"]["p1"]["L"], "H": a["H_committed"], "pass": a["pass"],
                             "held_out": a["held_out"], "boundary": a["boundary"]} for u, a in scored.items()},
            "holm_input_p_L_sign_test_vs_B0": p_sign, "L_vs_baselines": vs}


def b3_stream_lean(units: dict[str, Any]) -> dict[str, Any] | None:
    a = units.get("B3")
    if not a:
        return None
    j = a["bins"].index("prim_heap") if "prim_heap" in a["bins"] else None
    if j is None:
        return None
    c = a["cells"]["p1|1.0"]
    k, n = c["counts"]["prim_heap"], c["N"]
    p_pred = a["cells"]["p1|1.0"]["pred"]["L"][j]
    return {"fresh_T1_prim": f"{k}/{n}", "pred_L": p_pred,
            "binom_p_vs_pred": float(binomtest(k, n, p_pred).pvalue),
            "fisher_vs_iter7_sweep_T1_20of50": float(fisher_exact([[k, n - k], [20, 30]])[1]),
            "fisher_vs_iter7_twin_19of100": float(fisher_exact([[k, n - k], [19, 81]])[1])}


def main() -> None:
    setup_logging("analysis_L")
    rows = read_jsonl(SAMPLES_RAW)
    labs = {r["sid"]: r for r in read_jsonl(LABELS)}
    # S8: adjudicated labels (cells with > 20% 'other', or a unit whose style re-gate failed) are primary
    from cfg8 import DATA_DIR
    adj = {r["sid"]: r["label"] for r in read_jsonl(DATA_DIR / "adjudicated_labels.jsonl") if r.get("label")}
    for sid, lab in adj.items():
        if sid in labs:
            labs[sid] = {**labs[sid], "label_frozen": labs[sid]["label"], "label": lab}
    units = {}
    for u in UNITS:
        try:
            a = unit_analysis(u, rows, labs)
        except (KeyError, ValueError, IndexError, ZeroDivisionError) as e:
            logger.exception(f"analysis failed for {u}: {e}")
            a = None
        if a:
            units[u] = a
            logger.info(f"{u}: MAE {a['mae'].get('p1')} H {a['H_committed']} pass {a['pass']}")
    v = verdict(units)
    out = {"units": units, "verdict": v, "b3_stream_lean": b3_stream_lean(units)}
    write_json(RESULTS_DIR / "analysis_L.json", out)
    write_json(RESULTS_DIR / "verdict.json", v)
    logger.info(f"verdict: {v['status']} ({v['n_pass']}/{v['n_scored']}, held-out {v['n_heldout_pass']}/"
                f"{v['n_heldout_scored']})")


if __name__ == "__main__":
    main()
