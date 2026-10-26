#!/usr/bin/env python3
"""S1 / S2 analysis of step K (hashed in COMMIT #1 before the first S1/S2 sample): anchors, the unit x seeds 2x2
(+ U_bf*), the profile split, descriptive mediation and the D* rule of COMMIT #2.

Outcomes per program (labels: data/labels.jsonl, one labeller version for every row):
  Y      (primary)  passed AND label in the task catalogue minus the default (correct named off-default algorithm)
  Y_any             passed AND label not in {default, invalid, disputed, unknown} (adds correct 'other')
  A      (attempt)  valid AND label not in {default, invalid, disputed, unknown} over all N (attempted change of idea)
Invalid and failing programs count as not-target; disputed rows count as not-target and are reported.

Contrasts on CRN slots s = (template, k) where all four designs ran (paired):
  RD_unit = mean_s [P(U_abs, s) - P(U_bf, s)] = ((D1 - D3) + (D2 - D4)) / 2
  RD_seed = mean_u [P(u, S4) - P(u, S5)]     = ((D1 - D2) + (D3 - D4)) / 2
  INT     = (D1 - D2) - (D3 - D4)
95% CIs by slot-cluster bootstrap (2,000 replicates; a slot's four outcomes resampled together); exact sign-flip
permutation p over slots (exact enumeration of the non-zero slot contributions when <= 20, else 1e5 random flips);
conditional logit Y ~ unit + seed + unit:seed with slot strata (statsmodels ConditionalLogit), Firth-penalised logit
with slot dummies when a design cell is all-0/all-1 (separation). DECISION on T10 alpha 2, Holm over {unit, seed, INT}.

usage: .venv/bin/python src/analysis_k.py [s1|s2|anchors|dstar|all]
"""

from __future__ import annotations

import itertools
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

import k_cfg as K  # noqa: E402
from k_cfg import DEFAULTS, E29, LABELS, RAW, RESULTS, read_jsonl, row_key, wilson, write_json  # noqa: E402

N_BOOT = 2000
N_FLIP = 100_000
BOOT_SEED = 20261022
NOT_TARGET = {"invalid", "disputed", "unknown"}
EXP29_D1 = {"T10": {"attempts": 25, "N": 50, "pass": 0.98}, "T2": {"attempts": 22, "N": 50, "pass": 0.62,
                                                                 "correct_off_default": 9}}
EXP27_D4_T10 = {"correct_off_default": 1, "N": 50}
A1_MIN_K = 15
FISHER_P = 0.05
MOVABLE_EXCESS = 0.20
PASS_FRAC = 0.8
TIE_BAND = 0.10
# AMENDMENT 3 (after the exploratory E3 rows added T10 slots k 10-19 to the same arms): every committed S1 analysis
# reads only its committed slots, so exploratory rows never enter it (reproduces the pre-E3 numbers exactly).
COMMITTED_KS = {("T10", 1.0): list(range(10)), ("T10", 2.0): list(range(10)), ("T2", 1.0): list(range(10)),
                ("T2", 2.0): list(range(20))}


# ------------------------------------------------------------------------------------------------ catalogue
def catalogue(task: str) -> set[str]:
    if task in ("T1", "T2"):
        import cfg4  # vendored exp22 (PATH_CATALOGUE)
        return set(cfg4.PATH_CATALOGUE[task])
    sys.path.insert(0, str(K.V22 / "inputs" / "exp11"))
    from bench.common.catalogue import TASKS
    return set(TASKS[task]["modes"])


_CAT: dict[str, set[str]] = {}


def outcomes(task: str, lab: dict[str, Any] | None) -> dict[str, Any]:
    if task not in _CAT:
        _CAT[task] = catalogue(task)
    if lab is None:
        return {"labelled": False}
    label = lab["label"]
    d = DEFAULTS[task]
    passed = bool(lab.get("passed"))
    valid = bool(lab.get("valid"))
    off = label not in NOT_TARGET and label != d
    return {"labelled": True, "label": label, "passed": passed, "valid": valid,
            "Y": int(passed and label in _CAT[task] and label != d),
            "Y_any": int(passed and off), "A": int(valid and off), "disputed": int(label == "disputed")}


def load_joined(raw_path: Path = RAW, labels_path: Path = LABELS) -> list[dict[str, Any]]:
    labs = {l["key"]: l for l in read_jsonl(labels_path)}
    out = []
    for r in read_jsonl(raw_path):
        o = outcomes(r["task"], labs.get(row_key(r)))
        out.append({"key": row_key(r), "task": r["task"], "template": r["template"], "arm": r["arm"],
                    "k": int(r["sample_id"]), "design": r.get("design"), "alpha": r.get("alpha"),
                    "stage": r.get("stage"), "unit_id": r.get("unit_id"), "seed_scheme": r.get("seed_scheme"),
                    "direction_seed": r.get("direction_seed"), "realised_disp": r.get("realised_disp"),
                    "unit_mean_b12": r.get("unit_mean_b12"), "finish_reason": r.get("finish_reason"),
                    "n_tokens": r.get("n_tokens"), **o})
    return out


def cell(rows: list[dict[str, Any]], task: str, arm: str, ks: list[int] | None = None) -> dict[tuple, dict]:
    sel = {}
    for r in rows:
        if r["task"] == task and r["arm"] == arm and r.get("labelled") and (ks is None or r["k"] in ks):
            sel[(r["template"], r["k"])] = r
    return sel


def share(sel: dict[tuple, dict], key: str) -> dict[str, Any]:
    n = len(sel)
    k = sum(r[key] for r in sel.values())
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "share": k / n if n else None, "wilson95": [lo, hi]}


def describe(sel: dict[tuple, dict]) -> dict[str, Any]:
    n = len(sel)
    comp = Counter(r["label"] for r in sel.values())
    comp_correct = Counter(r["label"] for r in sel.values() if r["passed"])
    return {"N": n, "Y": share(sel, "Y"), "Y_any": share(sel, "Y_any"), "A": share(sel, "A"),
            "pass_rate": (sum(r["passed"] for r in sel.values()) / n) if n else None,
            "disputed": sum(r["disputed"] for r in sel.values()), "composition": dict(comp),
            "composition_correct": dict(comp_correct),
            "length_finish": sum(r.get("finish_reason") == "length" for r in sel.values())}


# ------------------------------------------------------------------------------------------------ exact tests
def fisher_two_sided(a: int, n1: int, c: int, n2: int) -> float:
    """Two-sided Fisher exact test for k1/n1 vs k2/n2 (sum of tables at most as likely as the observed one)."""
    from scipy.stats import fisher_exact
    return float(fisher_exact([[a, n1 - a], [c, n2 - c]], alternative="two-sided")[1])


def mcnemar_exact(x: list[int], y: list[int]) -> dict[str, Any]:
    n10 = sum(1 for a, b in zip(x, y) if a == 1 and b == 0)
    n01 = sum(1 for a, b in zip(x, y) if a == 0 and b == 1)
    n = n10 + n01
    if n == 0:
        return {"n10": 0, "n01": 0, "p": 1.0}
    from scipy.stats import binomtest
    return {"n10": n10, "n01": n01, "p": float(binomtest(n10, n, 0.5).pvalue)}


def sign_flip_p(contrib: np.ndarray, seed: int = BOOT_SEED) -> float:
    """Exact (or Monte-Carlo) sign-flip permutation p for the mean of per-slot contributions (two-sided)."""
    nz = contrib[np.abs(contrib) > 1e-12]
    obs = abs(contrib.sum())
    if len(nz) == 0:
        return 1.0
    if len(nz) <= 20:
        tot, hit = 0, 0
        for signs in itertools.product((1, -1), repeat=len(nz)):
            tot += 1
            hit += abs(float(np.dot(signs, nz))) >= obs - 1e-12
        return hit / tot
    rng = np.random.default_rng(seed)
    s = rng.choice((-1.0, 1.0), size=(N_FLIP, len(nz)))
    hits = int((np.abs(s @ nz) >= obs - 1e-12).sum())
    return (hits + 1) / (N_FLIP + 1)     # AMENDMENT 2a: Monte-Carlo p never reported as 0


def holm(ps: dict[str, float]) -> dict[str, float]:
    items = sorted(ps.items(), key=lambda kv: kv[1])
    m = len(items)
    out, running = {}, 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = running
    return out


# ------------------------------------------------------------------------------------------------ 2x2
def paired_matrix(rows: list[dict[str, Any]], task: str, alpha: float, designs: list[str], key: str = "Y",
                  ks: list[int] | None = None) -> tuple[list[tuple], np.ndarray]:
    a = "a1" if alpha == 1.0 else "a2"
    cells = [cell(rows, task, f"{d}_{a}", ks) for d in designs]
    slots = sorted(set.intersection(*[set(c) for c in cells])) if cells else []
    M = np.array([[c[s][key] for c in cells] for s in slots], dtype=float).reshape(len(slots), len(designs))
    return slots, M


def contrasts(M: np.ndarray) -> dict[str, np.ndarray]:
    """Per-slot contributions (columns D1, D2, D3, D4)."""
    d1, d2, d3, d4 = M[:, 0], M[:, 1], M[:, 2], M[:, 3]
    return {"unit": ((d1 - d3) + (d2 - d4)) / 2, "seed": ((d1 - d2) + (d3 - d4)) / 2, "int": (d1 - d2) - (d3 - d4)}


def boot_ci(M: np.ndarray, fn, n_boot: int = N_BOOT, seed: int = BOOT_SEED) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    n = M.shape[0]
    vals = np.array([fn(M[rng.integers(0, n, n)]) for _ in range(n_boot)])
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def firth_logit(X: np.ndarray, y: np.ndarray, max_iter: int = 200, tol: float = 1e-8) -> tuple[np.ndarray, np.ndarray]:
    """Firth-penalised logistic regression (Jeffreys prior); returns coefficients and Wald SEs."""
    beta = np.zeros(X.shape[1])
    for _ in range(max_iter):
        eta = np.clip(X @ beta, -30, 30)
        p = 1 / (1 + np.exp(-eta))
        W = p * (1 - p)
        XtWX = X.T @ (X * W[:, None]) + 1e-9 * np.eye(X.shape[1])
        inv = np.linalg.inv(XtWX)
        h = np.einsum("ij,jk,ik->i", X * np.sqrt(W)[:, None], inv, X * np.sqrt(W)[:, None])
        score = X.T @ (y - p + h * (0.5 - p))
        step = inv @ score
        beta = beta + step
        if np.max(np.abs(step)) < tol:
            break
    eta = np.clip(X @ beta, -30, 30)
    p = 1 / (1 + np.exp(-eta))
    inv = np.linalg.inv(X.T @ (X * (p * (1 - p))[:, None]) + 1e-9 * np.eye(X.shape[1]))
    return beta, np.sqrt(np.diag(inv))


def clogit(slots: list[tuple], M: np.ndarray, strata_extra: list[str] | None = None) -> dict[str, Any]:
    """Y ~ unit + seed + unit:seed with slot strata. Designs: D1 (unit 1, seed 1), D2 (1, 0), D3 (0, 1), D4 (0, 0)."""
    unit = np.array([1, 1, 0, 0])
    seed = np.array([1, 0, 1, 0])
    y = M.reshape(-1)
    g = np.repeat(np.arange(M.shape[0]), 4)
    X = np.column_stack([np.tile(unit, M.shape[0]), np.tile(seed, M.shape[0]), np.tile(unit * seed, M.shape[0])])
    names = ["unit", "seed", "unit:seed"]
    sep = any(M[:, j].sum() in (0, M.shape[0]) for j in range(4))
    out: dict[str, Any] = {"n_slots": int(M.shape[0]), "separation": bool(sep)}
    if not sep:
        try:
            from statsmodels.discrete.conditional_models import ConditionalLogit
            res = ConditionalLogit(y, X, groups=g).fit(disp=0)
            out.update({"method": "ConditionalLogit", "coef": dict(zip(names, map(float, res.params))),
                        "se": dict(zip(names, map(float, res.bse))), "p": dict(zip(names, map(float, res.pvalues)))})
            return out
        except (ValueError, np.linalg.LinAlgError) as e:
            out["clogit_error"] = str(e)
    # Firth with slot dummies (only informative slots; constant slots carry no conditional information)
    inf = [i for i in range(M.shape[0]) if 0 < M[i].sum() < 4]
    if not inf:
        out.update({"method": "none (no informative slot)", "coef": None})
        return out
    Mi = M[inf]
    yi = Mi.reshape(-1)
    D = np.kron(np.eye(len(inf)), np.ones((4, 1)))
    Xi = np.column_stack([np.tile(unit, len(inf)), np.tile(seed, len(inf)), np.tile(unit * seed, len(inf)), D])
    b, se = firth_logit(Xi, yi)
    from scipy.stats import norm
    out.update({"method": "Firth logit with slot dummies (informative slots)", "n_informative": len(inf),
                "coef": dict(zip(names, map(float, b[:3]))), "se": dict(zip(names, map(float, se[:3]))),
                "p": {n: float(2 * norm.sf(abs(b[i] / se[i]))) for i, n in enumerate(names)}})
    return out


def s1_table(rows: list[dict[str, Any]], task: str, alpha: float, key: str = "Y",
             ks: list[int] | None = None) -> dict[str, Any]:
    slots, M = paired_matrix(rows, task, alpha, ["D1", "D2", "D3", "D4"], key, ks)
    if len(slots) < 5:
        return {"n_slots": len(slots), "incomplete": True}
    C = contrasts(M)
    res: dict[str, Any] = {"n_slots": len(slots), "outcome": key,
                           "shares": {d: float(M[:, j].mean()) for j, d in enumerate(("D1", "D2", "D3", "D4"))}}
    fns = {"unit": lambda m: contrasts(m)["unit"].mean(), "seed": lambda m: contrasts(m)["seed"].mean(),
           "int": lambda m: contrasts(m)["int"].mean()}
    for name, fn in fns.items():
        res[f"RD_{name}"] = float(C[name].mean())
        res[f"RD_{name}_ci95"] = boot_ci(M, fn)
        res[f"RD_{name}_signflip_p"] = sign_flip_p(C[name])
    res["holm"] = holm({"unit": res["RD_unit_signflip_p"], "seed": res["RD_seed_signflip_p"],
                        "int": res["RD_int_signflip_p"]})
    res["clogit"] = clogit(slots, M)
    return res


def decision(t: dict[str, Any]) -> str:
    if t.get("incomplete"):
        return "INCOMPLETE"
    ex = lambda ci: ci[0] > 0 or ci[1] < 0  # noqa: E731
    u, s = t["RD_unit_ci95"], t["RD_seed_ci95"]
    unit_sig = u[0] > 0 and t["holm"]["unit"] < 0.05
    seed_sig = ex(s) and t["holm"]["seed"] < 0.05
    if unit_sig and not ex(s):
        return "UNIT"
    if seed_sig and not ex(u):
        return "SEEDS"
    if unit_sig and seed_sig:
        return "BOTH"
    sh = t["shares"]
    if min(sh.values()) >= 0.2:
        return "NEITHER-ALL-MOVE"
    if max(sh.values()) < 0.1:
        return "NEITHER-NONE-MOVE"
    return "NEITHER (no contrast significant after Holm)"


# ------------------------------------------------------------------------------------------------ anchors
def exp29_labels_d(task: str, arm: str) -> dict[tuple, dict]:
    out = {}
    for l in read_jsonl(E29 / "data" / "labels.jsonl"):
        if l.get("engine") == "d" and l["task"] == task and l["arm"] == arm:
            out[(l["template"], int(l["sample_id"]))] = l
    return out


def anchors(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    d1 = cell(rows, "T10", "D1_a2", K.K10)
    d4 = cell(rows, "T10", "D4_a2", K.K10)
    if len(d1) >= 50:
        a = sum(r["A"] for r in d1.values())
        p = fisher_two_sided(a, len(d1), EXP29_D1["T10"]["attempts"], 50)
        out["A1"] = {"attempted_off_default": a, "N": len(d1), "exp29": "25/50", "fisher_p": p,
                     "pass_rate": describe(d1)["pass_rate"], "pass": bool(p >= FISHER_P and a >= A1_MIN_K),
                     "correct_off_default_Y_any": sum(r["Y_any"] for r in d1.values())}
    if len(d4) >= 50:
        c = sum(r["Y_any"] for r in d4.values())
        p = fisher_two_sided(c, len(d4), EXP27_D4_T10["correct_off_default"], 50)
        out["A2"] = {"correct_off_default": c, "N": len(d4), "exp27": "1/50", "fisher_p": p,
                     "attempted": sum(r["A"] for r in d4.values()), "pass_rate": describe(d4)["pass_rate"],
                     "pass": bool(p >= FISHER_P)}
    t2 = cell(rows, "T2", "D1_a2", K.K10)
    if t2:
        e29 = exp29_labels_d("T2", "PN_a2")
        agree = [t2[s]["label"] == e29[s]["label"] for s in t2 if s in e29]
        out["A3"] = {"attempted_off_default": sum(r["A"] for r in t2.values()), "N": len(t2),
                     "correct_off_default": sum(r["Y_any"] for r in t2.values()),
                     "pass_rate": describe(t2)["pass_rate"], "exp29": "22/50 attempts, pass 0.62, 9/50 correct",
                     "fisher_p_attempts": fisher_two_sided(sum(r["A"] for r in t2.values()), len(t2), 22, 50),
                     "per_slot_label_agreement_vs_exp29": (sum(agree) / len(agree)) if agree else None,
                     "n_paired": len(agree)}
    e29t10 = exp29_labels_d("T10", "PN_a2")
    if d1:
        agree = [d1[s]["label"] == e29t10[s]["label"] for s in d1 if s in e29t10]
        out["D1_T10_per_slot_agreement_vs_exp29"] = {"agreement": (sum(agree) / len(agree)) if agree else None,
                                                     "n": len(agree)}
    out["both_pass"] = bool(out.get("A1", {}).get("pass") and out.get("A2", {}).get("pass"))
    write_json(RESULTS / "anchors.json", out)
    return out


# ------------------------------------------------------------------------------------------------ S1 / S2 / D5
def twin_pass(rows: list[dict[str, Any]], task: str) -> float | None:
    tw = cell(rows, task, "TWIN", K.K20 if task == "T2" else K.K10)
    return describe(tw)["pass_rate"] if tw else None


def s1(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {"cells": {}, "tables": {}}
    for task in K.S1_TASKS:
        out["cells"][f"{task}|TWIN"] = describe(cell(rows, task, "TWIN", K.K20 if task == "T2" else K.K10))
        for alpha in (1.0, 2.0):
            a = "a1" if alpha == 1.0 else "a2"
            ks = COMMITTED_KS[(task, alpha)]
            for d in ("D1", "D2", "D3", "D4", "D5"):
                c = cell(rows, task, f"{d}_{a}", ks)
                if c:
                    out["cells"][f"{task}|{d}_{a}"] = describe(c)
            for key in ("Y", "Y_any", "A"):
                out["tables"][f"{task}|a{int(alpha)}|{key}"] = s1_table(rows, task, alpha, key, ks)
    t = out["tables"].get("T10|a2|Y", {})
    out["decision_T10_a2"] = decision(t)
    out["decision_T2_a2"] = decision(out["tables"].get("T2|a2|Y", {}))
    # T2 alpha 2 on k 0-9 only (the N-50 sensitivity) and the D5 split
    out["tables"]["T2|a2|Y|k0-9"] = s1_table(rows, "T2", 2.0, "Y", K.K10)
    out["D5_split"] = d5_split(rows)
    out["mediation"] = mediation(rows)
    write_json(RESULTS / "s1_2x2.json", out)
    return out


def d5_split(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out = {}
    for task in K.S1_TASKS:
        for key in ("Y", "Y_any", "A"):
            slots, M = paired_matrix(rows, task, 2.0, ["D1", "D5", "D3"], key, COMMITTED_KS[(task, 2.0)])
            if len(slots) < 5:
                continue
            res = {"n_slots": len(slots), "shares": {"D1": float(M[:, 0].mean()), "D5": float(M[:, 1].mean()),
                                                     "D3": float(M[:, 2].mean())}}
            for name, (i, j) in {"profile_at_matched_energy (D1 - D5)": (0, 1),
                                 "energy_at_banfree_shape (D5 - D3)": (1, 2)}.items():
                diff = M[:, i] - M[:, j]
                res[name] = {"RD": float(diff.mean()),
                             "ci95": boot_ci(M, lambda m, i=i, j=j: (m[:, i] - m[:, j]).mean()),
                             "mcnemar": mcnemar_exact(list(M[:, i].astype(int)), list(M[:, j].astype(int)))}
            out[f"{task}|{key}"] = res
    return out


def mediation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Descriptive: per-sample logit Y ~ design + log||disp spec-mean b35|| + log||disp R b35||; CV AUC of A from the
    two downstream norms (pushed S1 rows at alpha 1 and 2)."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import StratifiedKFold, cross_val_predict

    out = {}
    for task in K.S1_TASKS:
        sel = [r for r in rows if r["task"] == task and r.get("labelled") and r.get("realised_disp")
               and r["design"] in ("D1", "D2", "D3", "D4", "D5") and r["alpha"] in (1.0, 2.0)   # AMENDMENT 2b
               and r["k"] in COMMITTED_KS[(task, r["alpha"])]]                                   # AMENDMENT 3
        if len(sel) < 40:
            continue
        des = sorted({r["design"] for r in sel})
        Xd = np.array([[1.0 if r["design"] == d else 0.0 for d in des[1:]] + [1.0 if r["alpha"] == 2.0 else 0.0]
                       for r in sel])
        Xm = np.array([[math.log(max(r["realised_disp"]["S_b35"], 1e-6)), math.log(max(r["realised_disp"]["R_b35"],
                                                                                        1e-6))] for r in sel])
        res: dict[str, Any] = {"n": len(sel), "designs_ref": des[0]}
        for key in ("Y", "A"):
            y = np.array([r[key] for r in sel])
            if y.sum() < 5 or y.sum() > len(y) - 5:
                res[key] = {"skipped": "too few events"}
                continue
            m0 = LogisticRegression(C=1e6, max_iter=5000).fit(Xd, y)
            m1 = LogisticRegression(C=1e6, max_iter=5000).fit(np.column_stack([Xd, Xm]), y)
            cv = StratifiedKFold(5, shuffle=True, random_state=0)
            pr = cross_val_predict(LogisticRegression(C=1e6, max_iter=5000), Xm, y, cv=cv,
                                   method="predict_proba")[:, 1]
            res[key] = {"design_coef_without_mediators": dict(zip(des[1:] + ["alpha2"], map(float, m0.coef_[0]))),
                        "design_coef_with_mediators": dict(zip(des[1:] + ["alpha2", "log_S_b35", "log_R_b35"],
                                                               map(float, m1.coef_[0]))),
                        "cv_auc_downstream_norms": float(roc_auc_score(y, pr))}
        out[task] = res
    return out


def s2(rows: list[dict[str, Any]]) -> dict[str, Any]:
    import k_units as KU

    out: dict[str, Any] = {}
    for task in K.S1_TASKS:
        res: dict[str, Any] = {"cells": {}}
        n = KU.u_abs(task)
        prof = KU.profile_masks(n, task)
        res["energy_share_Q4"] = prof["P_top"]["energy_share"]
        res["q75"] = prof["P_top"]["q75"]
        res["scales"] = {k: v["scale"] for k, v in prof.items()}
        arms = {"D1": "D1_a2", "PTOP": "PTOP_a2", "PREST": "PREST_a2", "PSHUF": "PSHUF_a2"}
        cells = {k: cell(rows, task, a, K.K10) for k, a in arms.items()}
        for k, c in cells.items():
            if c:
                d = describe(c)
                disp = [r["realised_disp"] for r in c.values() if r.get("realised_disp")]
                d["realised_mean"] = {f: float(np.mean([x[f] for x in disp])) for f in ("S_b12", "S_b23", "S_b35",
                                                                                         "R_b35")} if disp else None
                res["cells"][k] = d
        tests = {}
        for name, (x, y) in {"PTOP_vs_PREST": ("PTOP", "PREST"), "D1_vs_PSHUF": ("D1", "PSHUF"),
                             "D1_vs_PTOP": ("D1", "PTOP")}.items():
            cx, cy = cells[x], cells[y]
            common = sorted(set(cx) & set(cy))
            if len(common) < 10:
                continue
            for key in ("Y", "Y_any", "A"):
                t = mcnemar_exact([cx[s][key] for s in common], [cy[s][key] for s in common])
                t.update({"n": len(common), "share_x": float(np.mean([cx[s][key] for s in common])),
                          "share_y": float(np.mean([cy[s][key] for s in common]))})
                tests[f"{name}|{key}"] = t
        prim = {k.split("|")[0]: v["p"] for k, v in tests.items() if k.endswith("|Y")}
        res["tests"] = tests
        res["holm_Y"] = holm(prim) if prim else {}
        out[task] = res
    t = out.get("T10", {})
    tt = t.get("tests", {})
    a = tt.get("PTOP_vs_PREST|Y")
    b = tt.get("D1_vs_PSHUF|Y")
    out["reading_T10"] = None if not (a and b) else (
        "PUSHES ACT WHERE BANS WRITE" if (a["share_x"] > a["share_y"] and t["holm_Y"].get("PTOP_vs_PREST", 1) < 0.05
                                          and b["share_x"] > b["share_y"] and t["holm_Y"].get("D1_vs_PSHUF", 1) < 0.05)
        else "NOT SUPPORTED")
    write_json(RESULTS / "s2_profile.json", out)
    return out


# ------------------------------------------------------------------------------------------------ D* (COMMIT #2 rule)
def d_star(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """D* = argmax over D1-D4 of the pooled (T10 + T2) alpha-2 correct named off-default share (Y) among designs
    with T10 pass >= 0.8 x twin pass; ties within 0.10 go to D1 (anchored)."""
    tp = twin_pass(rows, "T10") or 1.0
    cand = {}
    for d in ("D1", "D2", "D3", "D4"):
        c10 = cell(rows, "T10", f"{d}_a2", COMMITTED_KS[("T10", 2.0)])
        c2 = cell(rows, "T2", f"{d}_a2", COMMITTED_KS[("T2", 2.0)])
        if not c10 or not c2:
            continue
        p10 = describe(c10)["pass_rate"]
        ys = [r["Y"] for r in list(c10.values()) + list(c2.values())]
        cand[d] = {"pooled_Y": float(np.mean(ys)), "n": len(ys), "T10_pass": p10, "eligible": p10 >= PASS_FRAC * tp}
    elig = {d: v for d, v in cand.items() if v["eligible"]}
    if not elig:
        best = "D1"
    else:
        best = max(elig, key=lambda d: elig[d]["pooled_Y"])
        if "D1" in elig and elig[best]["pooled_Y"] - elig["D1"]["pooled_Y"] <= TIE_BAND:
            best = "D1"
    return {"D_star": best, "candidates": cand, "twin_pass_T10": tp}


def e1_sweep(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """AMENDMENT 2c (exploratory, not pre-registered): ban-free unit dose sweep D3 at alpha 1, 2, 3, 4, 6 next to D1 at
    alpha 1, 2 and the twin: shares, pass rates and mean realised displacement (spec-mean and R at block 35), paired
    McNemar of each D3 dose against D1 alpha 2 on the same slots."""
    out: dict[str, Any] = {}
    for task in K.S1_TASKS:
        res: dict[str, Any] = {}
        ref = cell(rows, task, "D1_a2", K.K10)
        for arm in ("TWIN", "D1_a1", "D1_a2", "D3_a1", "D3_a2", "D3_a3", "D3_a4", "D3_a6", "D5_a2"):
            c = cell(rows, task, arm, K.K10)
            if not c:
                continue
            d = describe(c)
            disp = [r["realised_disp"] for r in c.values() if r.get("realised_disp")]
            d["realised_mean"] = {f: float(np.mean([x[f] for x in disp])) for f in ("S_b12", "S_b35", "R_b35")} \
                if disp else None
            common = sorted(set(c) & set(ref))
            if arm != "D1_a2" and len(common) >= 10:
                d["vs_D1_a2_Y"] = mcnemar_exact([c[s]["Y"] for s in common], [ref[s]["Y"] for s in common])
            res[arm] = d
        out[task] = res
    write_json(RESULTS / "e1_sweep.json", out)
    return out


@logger.catch(reraise=True)
def main() -> None:
    rows = load_joined()
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("anchors", "all"):
        print(anchors(rows))
    if what in ("s1", "all"):
        r = s1(rows)
        print({"decision_T10_a2": r["decision_T10_a2"], "decision_T2_a2": r["decision_T2_a2"]})
    if what in ("s2", "all"):
        print(s2(rows).get("reading_T10"))
    if what in ("dstar", "all"):
        print(d_star(rows))
    if what in ("e1", "all"):
        e1_sweep(rows)


if __name__ == "__main__":
    main()
