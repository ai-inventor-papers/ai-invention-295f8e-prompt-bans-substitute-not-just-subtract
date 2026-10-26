#!/usr/bin/env python3
"""Part F scoring (committed in COMMIT #2 before the first sweep / S4 sample).

F1 Test (1): H(A | fork class) <= 0.3 bits on >= 2 mixed units (disconfirming: > 0.5 bits on >= 2 units).
F2 Test (2): per unit, Delta_obs(1.0 -> 0.3) >= 0.15 (exact one-sided McNemar on the 50 same-seed slot pairs, slot
   bootstrap CI), MAE <= 0.10 over the 8 cells against the committed predictions, |dObs(1.0->1.3) - dPred| <= 0.10;
   passes on >= 2 units (disconfirming: MAE > 0.2 on >= 2 units). Also JS divergence, on-opening shares, replay accuracy.
F3 Test (3): collapsed margins >= 4 nats on all 4 collapsed tasks (+ exact predicted movement, record view, the T 1.3
   check's binomial consistency).
F4 verdict; F5 S4(a); F6 S4(b); F7 the 1a-c table (ideas x phrasings, correct-only Hill-1 rarefied at depth 25,
   AST 4-gram Jaccard clusters at theta 0.7/0.8/0.9, per-slot idea changes, the literal 10-trajectory view).
"""

from __future__ import annotations

import ast
import itertools
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import binom, spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg7 import (COLLAPSED, COLLAPSED_INFO, DIRECTIONS, LABELS, RESULTS_DIR, SAMPLERS, SAMPLES_RAW,  # noqa: E402
                  SWEEP_SLOTS, TEMPLATES, TEMPS, THRESH, UNITS, read_json, read_jsonl, write_json)

SEED = 20261022


# ------------------------------------------------------------------------------------------------ data
def rows_with_labels() -> list[dict[str, Any]]:
    """Program rows with their frozen labels; a 'disputed' label (labeller disagreement) is replaced by the blind
    judges' majority label when one exists (data/judge_labels.jsonl), else it stays 'disputed' (counted, not A)."""
    L = {r["sid"]: r for r in read_jsonl(LABELS)}
    J = {r["sid"]: r for r in read_jsonl(LABELS.parent / "judge_labels.jsonl") if r.get("label")}
    out = []
    for r in read_jsonl(SAMPLES_RAW):
        lab = L.get(r["sid"])
        if lab is None:
            continue
        y = lab["label"]
        if y == "disputed" and r["sid"] in J:
            y = J[r["sid"]]["label"]
        out.append({**r, "label": y, "passed": bool(lab["passed"]), "code": lab.get("code")})
    return out


def exact_mcnemar_one_sided(b: int, c: int) -> float:
    """P(X >= b | n = b + c, 1/2): b = discordant pairs in the predicted direction."""
    n = b + c
    if n == 0:
        return 1.0
    return float(binom.sf(b - 1, n, 0.5))


def js_div(p: np.ndarray, q: np.ndarray) -> float:
    p = np.asarray(p, float) / max(np.sum(p), 1e-12)
    q = np.asarray(q, float) / max(np.sum(q), 1e-12)
    m = 0.5 * (p + q)

    def kl(a: np.ndarray, b: np.ndarray) -> float:
        msk = a > 0
        return float(np.sum(a[msk] * np.log2(a[msk] / b[msk])))
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


# ------------------------------------------------------------------------------------------------ tests
def test1(pv: dict[str, Any]) -> dict[str, Any]:
    per = {}
    for u, U in pv["units"].items():
        t = U["test1"]
        per[u] = {"H_bits": t["H_bits"], "H_ci95": t["H_boot_ci95"], "H_upper95": t["H_upper95"],
                  "undecided_mass": t["undecided_mass"], "class_mass": t["class_mass"],
                  "pass": t["H_bits"] <= THRESH["test1_H_bits_pass"],
                  "disconfirm": t["H_bits"] > THRESH["test1_H_bits_disconfirm"]}
    n_pass = sum(v["pass"] for v in per.values())
    n_dis = sum(v["disconfirm"] for v in per.values())
    return {"per_unit": per, "n_pass": n_pass, "pass": n_pass >= THRESH["test1_units_needed"],
            "disconfirming_branch": n_dis >= 2, "rule": "H(A | C) <= 0.3 bits on >= 2 mixed units; "
                                                        "disconfirming: > 0.5 bits on >= 2 units"}


def sweep_table(rows: list[dict[str, Any]], u: str) -> dict[tuple[str, str, int], dict[str, Any]]:
    return {(r["cell"], r["template"], r["slot"]): r for r in rows if r["unit"] == u and r["arm"] == "SWEEP"}


def on_opening(ids: list[int], clusters: dict[str, Any]) -> bool:
    return any(ids[:len(c["O"])] == c["O"] for c in clusters.values())


def test2(pv: dict[str, Any], rows: list[dict[str, Any]], F: dict[str, Any]) -> dict[str, Any]:
    per = {}
    rng = np.random.default_rng(SEED)
    pooled_b = pooled_c = 0
    for u, U in pv["units"].items():
        A, C = U["A_min"], U["cats"]
        tab = sweep_table(rows, u)
        if not tab:
            continue
        clusters = {c["id"]: c for c in F[u]["opening"]["clusters"]}
        slots = [(w, s) for w in TEMPLATES for s in SWEEP_SLOTS]
        cells = {}
        for T in TEMPS:
            for sname in SAMPLERS:
                cell = f"T{T}_{sname}"
                rr = [tab.get((cell, w, s)) for w, s in slots]
                rr = [r for r in rr if r is not None]
                n = len(rr)
                if n == 0:
                    continue
                kA = sum(r["label"] == A for r in rr)
                kAc = sum(r["label"] == A and r["passed"] for r in rr)
                obs = np.array([sum(r["label"] == c or (c == "other" and r["label"] not in C) for r in rr)
                                for c in C], float)
                pred = np.array(U["cells"][cell]["P"])
                rep_ok = rep_n = 0
                for r in rr:
                    pr = U["replay"].get(f"{r['template']}|{r['slot']}|{cell}")
                    if pr and not str(pr["pred"]).startswith("rest:"):
                        rep_n += 1
                        rep_ok += pr["pred"] == r["label"]
                cells[cell] = {"n": n, "a_min": kA / n, "a_min_ci": wilson(kA, n), "correct_a_min": kAc / n,
                               "pred_a_min": U["cells"][cell]["a_min"], "pred_correct_a_min":
                                   U["pred_correct_a_min"][cell], "abs_err": abs(kA / n - U["cells"][cell]["a_min"]),
                               "obs_dist": (obs / n).tolist(), "pred_dist": pred.tolist(), "js_bits": js_div(obs, pred),
                               "on_opening_obs": float(np.mean([on_opening(r["token_ids"], clusters) for r in rr])),
                               "on_opening_pred": U["cells"][cell]["on_opening"],
                               "replay_acc": rep_ok / rep_n if rep_n else None, "replay_n": rep_n,
                               "pass_rate": float(np.mean([r["passed"] for r in rr])),
                               "truncated": sum(r["finish_reason"] == "length" for r in rr)}
        if len(cells) < 8:
            per[u] = {"cells": cells, "complete": False}
            continue
        mae = float(np.mean([v["abs_err"] for v in cells.values()]))
        x10 = {(w, s): tab[("T1.0_p1", w, s)]["label"] == A for w, s in slots if ("T1.0_p1", w, s) in tab}
        x03 = {(w, s): tab[("T0.3_p1", w, s)]["label"] == A for w, s in slots if ("T0.3_p1", w, s) in tab}
        x13 = {(w, s): tab[("T1.3_p1", w, s)]["label"] == A for w, s in slots if ("T1.3_p1", w, s) in tab}
        keys = [k for k in x10 if k in x03]
        b = sum(x10[k] and not x03[k] for k in keys)
        c = sum(x03[k] and not x10[k] for k in keys)
        if u in ("B3", "A3"):
            pooled_b += b
            pooled_c += c
        d_obs = (sum(x10[k] for k in keys) - sum(x03[k] for k in keys)) / len(keys)
        boot = []
        arr10 = np.array([x10[k] for k in keys], float)
        arr03 = np.array([x03[k] for k in keys], float)
        for _ in range(2000):
            idx = rng.integers(0, len(keys), len(keys))
            boot.append(arr10[idx].mean() - arr03[idx].mean())
        k13 = [k for k in x10 if k in x13]
        d13_obs = (sum(x13[k] for k in k13) - sum(x10[k] for k in k13)) / len(k13)
        d13_pred = U["delta_pred_10_13_p1"]
        d_pred = U["delta_pred_10_03_p1"]
        ok = d_obs >= THRESH["test2_drop_min"] and mae <= THRESH["test2_mae_max"] and \
            abs(d13_obs - d13_pred) <= THRESH["test2_13_tol"]
        per[u] = {"cells": cells, "complete": True, "MAE": mae, "delta_obs_10_03": d_obs,
                  "delta_obs_ci95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
                  "delta_pred_10_03": d_pred, "mcnemar_b_10only": b, "mcnemar_c_03only": c,
                  "mcnemar_p_one_sided": exact_mcnemar_one_sided(b, c), "delta_obs_10_13": d13_obs,
                  "delta_pred_10_13": d13_pred, "abs_dev_10_13": abs(d13_obs - d13_pred), "pass": ok,
                  "disconfirm": mae > THRESH["test2_mae_disconfirm"],
                  "slot_flips_any_T_p1": sum(len({tab[(f"T{T}_p1", w, s)]["label"] for T in TEMPS
                                                  if (f"T{T}_p1", w, s) in tab}) > 1 for w, s in slots)}
    n_pass = sum(bool(v.get("pass")) for v in per.values())
    n_dis = sum(bool(v.get("disconfirm")) for v in per.values())
    pooled_p = exact_mcnemar_one_sided(pooled_b, pooled_c)
    return {"per_unit": per, "n_pass": n_pass, "pass": n_pass >= THRESH["test2_units_needed"],
            "disconfirming_branch": n_dis >= 2, "pooled_B3_A3": {"b": pooled_b, "c": pooled_c, "p": pooled_p,
                                                                  "bonferroni_0.05/7": pooled_p <
                                                                  THRESH["secondary_bonferroni"],
                                                                  "unadjusted_0.05": pooled_p < 0.05}}


def test3(pv: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    col = pv.get("collapsed", {})
    per = {}
    for t in COLLAPSED:
        if t not in col:
            continue
        c = col[t]
        rr = [r for r in rows if r["unit"] == t and r["arm"] == "T13CHK"]
        D = COLLAPSED_INFO[t]["default"]
        n_off = sum(r["label"] != D for r in rr)
        n_off_valid = sum(r["label"] not in (D, "invalid", "other", "disputed") for r in rr)
        p = c["pred_p_off"]["T1.3_p1"]
        per[t] = {"margin_nats": c["margin_nats"], "pass": bool(c["pass_4nats"]), "pred_p_off": c["pred_p_off"],
                  "delta_pred_13_03": c["delta_pred_13_03"], "bound_check": c["bound_check"], "llr48": c["llr48"],
                  "check_T13": {"n": len(rr), "n_off_any": n_off, "n_off_catalogue": n_off_valid,
                                "binom_p_ge_obs": float(binom.sf(n_off_valid - 1, len(rr), max(p, 1e-12)))
                                if rr else None},
                  "record_binom_p_le3_of_800_at_pred_T13": float(binom.cdf(3, 800, max(p, 1e-12)))}
    return {"per_task": per, "pass": len(per) == 4 and all(v["pass"] for v in per.values()),
            "record": col.get("_record"), "rule": "margin >= 4 nats on all 4 collapsed tasks"}


def verdict(t1: dict[str, Any], t2: dict[str, Any], t3: dict[str, Any]) -> dict[str, Any]:
    passes = {"test1": t1["pass"], "test2": t2["pass"], "test3": t3["pass"]}
    dis = {"test1": t1["disconfirming_branch"], "test2": t2["disconfirming_branch"]}
    if any(dis.values()):
        v = "DISCONFIRMED"
    elif all(passes.values()):
        v = "SUPPORTED"
    elif any(passes.values()):
        v = "PARTIAL"
    else:
        v = "NOT SUPPORTED"
    return {"verdict": v, "passes": passes, "disconfirming": dis,
            "secondary_raw_p_pooled_mcnemar": t2["pooled_B3_A3"]["p"],
            "secondary_unadjusted_0.05": t2["pooled_B3_A3"]["unadjusted_0.05"],
            "secondary_bonferroni_0.05_over_7": t2["pooled_B3_A3"]["bonferroni_0.05/7"]}


# ------------------------------------------------------------------------------------------------ S4
def exact_perm_spearman(x: list[float], y: list[float]) -> tuple[float, float, float]:
    """rho, the committed upper-tail exact permutation p P(rho_perm >= rho) and the lower-tail p P(rho_perm <= rho)
    (post-commit correction: the hypothesis predicts a NEGATIVE rho, so the lower tail is the one-sided test)."""
    rho = float(spearmanr(x, y)[0]) if len(set(x)) > 1 and len(set(y)) > 1 else float("nan")
    if not np.isfinite(rho):
        return rho, float("nan"), float("nan")
    ge = le = tot = 0
    for perm in itertools.permutations(range(len(y))):
        yy = [y[i] for i in perm]
        r = spearmanr(x, yy)[0] if len(set(yy)) > 1 else 0.0
        tot += 1
        ge += (r >= rho - 1e-12)
        le += (r <= rho + 1e-12)
    return rho, ge / tot, le / tot


def s4a(pv: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    out = {}
    for u, U in pv["units"].items():
        if "s4" not in U:
            continue
        A = U["A_min"]
        rr = [r for r in rows if r["unit"] == u and r["arm"] == "S4A"]
        if not rr:
            continue
        tw = [r for r in rr if r["cell"] == "twin0"]
        s_tw = float(np.mean([r["label"] == A for r in tw])) if tw else float("nan")
        pass_tw = float(np.mean([r["passed"] for r in tw])) if tw else float("nan")
        base = U["s4"]["twin"]
        dm, ds, per = [0.0], [0.0], {}
        lg_gain = []
        for d in DIRECTIONS:
            pr = U["s4"]["push"][str(d)]
            pd = [r for r in rr if r["cell"] == f"push{d}"]
            if not pd:
                continue
            s_obs = float(np.mean([r["label"] == A for r in pd]))
            per[str(d)] = {"n": len(pd), "s_obs": s_obs, "s_pred": pr["s_pred"], "d_margin": pr["d_margin"],
                           "d_s_obs": s_obs - s_tw, "pass_rate": float(np.mean([r["passed"] for r in pd])),
                           "labels": dict(Counter(r["label"] for r in pd))}
            dm.append(pr["d_margin"])
            ds.append(s_obs - s_tw)
            for r in pd:
                y = r["label"] == A
                p1 = min(max(pr["s_pred"], 0.01), 0.99)
                p0 = min(max(base["s_pred"], 0.01), 0.99)
                lg_gain.append(math.log(p1 if y else 1 - p1) - math.log(p0 if y else 1 - p0))
        rho, p, p_lo = exact_perm_spearman(dm, ds) if len(dm) >= 4 else (float("nan"),) * 3
        out[u] = {"twin_slots_0_1": {"n": len(tw), "s_obs": s_tw, "pass_rate": pass_tw, "s_pred": base["s_pred"]},
                  "per_direction": per, "spearman_dmargin_dshare": rho, "perm_p_one_sided": p,
                  "perm_p_one_sided_negative": p_lo,
                  "p_note": "perm_p_one_sided is the committed upper tail; perm_p_one_sided_negative is the lower tail "
                            "in the predicted (negative) direction (post-commit correction, results/deviations.json)",
                  "note": "Spearman over 8 directions plus the twin (0, 0); expected sign negative: a larger D margin "
                          "should lower the minority share",
                  "mae_s_pred": float(np.mean([abs(v["s_obs"] - v["s_pred"]) for v in per.values()])) if per else None,
                  "log_score_gain_per_sample": float(np.mean(lg_gain)) if lg_gain else None,
                  "pass_rate_vs_twin": float(np.mean([v["pass_rate"] for v in per.values()]) / pass_tw)
                  if per and pass_tw else None}
    return out


def s4b(pv: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    out = {}
    for u, U in pv["units"].items():
        A = U["A_min"]
        rr = [r for r in rows if r["unit"] == u and r["arm"] == "S4B"]
        if not rr:
            continue
        arms = defaultdict(dict)
        for r in rr:
            arms[r["cell"]][r["slot"]] = r
        res = {}
        for a, d in arms.items():
            n = len(d)
            res[a] = {"n": n, "attempted_a_min": sum(r["label"] == A for r in d.values()) / n,
                      "correct_a_min": sum(r["label"] == A and r["passed"] for r in d.values()) / n,
                      "pass_rate": sum(r["passed"] for r in d.values()) / n,
                      "labels": dict(Counter(r["label"] for r in d.values()))}
        def mcn(x: str, y: str) -> dict[str, Any]:
            if x not in arms or y not in arms:
                return {}
            ks = sorted(set(arms[x]) & set(arms[y]))
            b = sum(arms[x][k]["label"] == A and arms[y][k]["label"] != A for k in ks)
            c = sum(arms[y][k]["label"] == A and arms[x][k]["label"] != A for k in ks)
            return {"b": b, "c": c, "p_one_sided": exact_mcnemar_one_sided(b, c)}
        tf = U.get("s4", {}).get("exchange", {})
        out[u] = {"arms": res, "exchange_vs_pad": mcn("EXCH", "FORCEDPAD"), "exchange_vs_MR": mcn("EXCH", "MR"),
                  "forced_adherence": res.get("FORCED", {}).get("attempted_a_min"),
                  "forced_adherence_ok": (res.get("FORCED", {}).get("attempted_a_min") or 0) >= 0.7,
                  "d_margin_exchange": tf.get("exchange", {}).get("d_margin_vs_pad"),
                  "d_margin_MR": tf.get("MR", {}).get("d_margin_vs_pad"),
                  "s_pred_exchange": tf.get("exchange", {}).get("s_pred"),
                  "abs_err_exchange": abs(tf.get("exchange", {}).get("s_pred", float("nan")) -
                                          res.get("EXCH", {}).get("attempted_a_min", float("nan"))) if tf else None,
                  "exchange_pass_ratio_vs_pad": (res.get("EXCH", {}).get("pass_rate", 0) /
                                                 max(res.get("FORCEDPAD", {}).get("pass_rate", 0), 1e-9))
                  if "EXCH" in res and "FORCEDPAD" in res else None}
    return out


# ------------------------------------------------------------------------------------------------ 1a-c table
def ast_ngrams(code: str | None, n: int = 4) -> frozenset:
    if not code:
        return frozenset()
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return frozenset()
    seq = []
    for node in ast.walk(tree):
        t = type(node).__name__
        if isinstance(node, ast.Constant):
            t += ":" + type(node.value).__name__
        elif isinstance(node, (ast.BinOp, ast.AugAssign)):
            t += ":" + type(node.op).__name__
        elif isinstance(node, ast.Compare):
            t += ":" + ",".join(type(o).__name__ for o in node.ops)
        elif isinstance(node, ast.Attribute):
            t += ":" + node.attr                     # library/method names kept; identifiers (Name.id) dropped
        seq.append(t)
    return frozenset(tuple(seq[i:i + n]) for i in range(max(0, len(seq) - n + 1)))


def jaccard(a: frozenset, b: frozenset) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / max(len(a | b), 1)


def phrasing_clusters(codes: list[str | None], theta: float) -> dict[str, int]:
    from scipy.cluster.hierarchy import fcluster, linkage
    g = [ast_ngrams(c) for c in codes]
    n = len(g)
    if n == 0:
        return {"single": 0, "complete": 0}
    if n == 1:
        return {"single": 1, "complete": 1}
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    D = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            s = jaccard(g[i], g[j])
            D[i, j] = D[j, i] = 1 - s
            if s >= theta:
                parent[find(i)] = find(j)
    single = len({find(i) for i in range(n)})
    iu = np.triu_indices(n, 1)
    Z = linkage(D[iu], "complete")
    comp = len(set(fcluster(Z, t=1 - theta, criterion="distance")))
    return {"single": single, "complete": comp}


def hill1_rarefied(labels: list[str], depth: int = 25, reps: int = 300, seed: int = SEED) -> float | None:
    if len(labels) < depth:
        return None
    rng = np.random.default_rng(seed)
    vals = []
    arr = np.array(labels)
    for _ in range(reps):
        sub = rng.choice(arr, size=depth, replace=False)
        c = np.array(list(Counter(sub).values()), float) / depth
        vals.append(math.exp(-(c * np.log(c)).sum()))
    return float(np.mean(vals))


def table_1ac(pv: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    out = {}
    for u, U in pv["units"].items():
        tab = sweep_table(rows, u)
        if not tab:
            continue
        cats = U["cats"]
        res = {}
        for sname in SAMPLERS:
            for T in TEMPS:
                cell = f"T{T}_{sname}"
                rr = [r for (c, w, s), r in tab.items() if c == cell]
                corr = [r for r in rr if r["passed"] and r["label"] in cats]
                ideas_c = sorted({r["label"] for r in corr})
                ideas_a = sorted({r["label"] for r in rr if r["label"] in cats})
                ph = {}
                for idea in ideas_a:
                    codes = [r["code"] for r in rr if r["label"] == idea]
                    ph[idea] = {f"theta{th}": phrasing_clusters(codes, th) for th in (0.7, 0.8, 0.9)}
                    ph[idea]["n"] = len(codes)
                lit = [tab.get((cell, w, s)) for w in TEMPLATES for s in (20, 21)]
                lit = [r for r in lit if r is not None]
                lit_ideas = Counter(r["label"] for r in lit)
                lit_ph = {idea: phrasing_clusters([r["code"] for r in lit if r["label"] == idea], 0.8)["single"]
                          for idea in lit_ideas}
                res[cell] = {"n": len(rr), "ideas_correct": ideas_c, "ideas_attempted": ideas_a,
                             "hill1_correct_rarefied25": hill1_rarefied([r["label"] for r in corr]),
                             "phrasing_clusters": ph,
                             "ten_trajectories": {"ideas": dict(lit_ideas), "phrasing_clusters_theta0.8": lit_ph,
                                                  "n": len(lit)}}
        flips = {}
        for sname in SAMPLERS:
            ch = 0
            tot = 0
            for w in TEMPLATES:
                for s in SWEEP_SLOTS:
                    labs = [tab[(f"T{T}_{sname}", w, s)]["label"] for T in TEMPS if (f"T{T}_{sname}", w, s) in tab]
                    if len(labs) == len(TEMPS):
                        tot += 1
                        ch += len(set(labs)) > 1
            flips[sname] = {"slots_with_idea_change_across_T": ch, "n_slots": tot}
        out[u] = {"cells": res, "per_slot_idea_changes": flips}
    return out


def main() -> dict[str, Any]:
    pv = read_json(RESULTS_DIR / "predictions_view.json")
    F = read_json(RESULTS_DIR / "forks.json")
    rows = rows_with_labels()
    t1 = test1(pv)
    t2 = test2(pv, rows, F)
    t3 = test3(pv, rows)
    v = verdict(t1, t2, t3)
    write_json(RESULTS_DIR / "test1.json", t1)
    write_json(RESULTS_DIR / "test2.json", t2)
    write_json(RESULTS_DIR / "test3.json", t3)
    write_json(RESULTS_DIR / "verdict.json", v)
    write_json(RESULTS_DIR / "s4a.json", s4a(pv, rows))
    write_json(RESULTS_DIR / "s4b.json", s4b(pv, rows))
    write_json(RESULTS_DIR / "table_1ac.json", table_1ac(pv, rows))
    return v


if __name__ == "__main__":
    print(json.dumps(main(), indent=1))
