#!/usr/bin/env python3
"""STEP 10-11 analyses of iteration 7 (committed before any held-out generation was scored): P1 (generation
recovery of the full-state transfer by a rank-k DAS subspace, with random / permuted / random-init / read-position /
null controls), C (routing), c6 dormant-subspace checks, M (manifold placement in DAS coordinates) and R
(discreteness of the lambda sweep). Every count is computed from data/labels.jsonl; intervals: Clopper-Pearson for
shares, slot-cluster bootstrap (2,000 reps) for recovery ratios, exact McNemar for paired contrasts, Holm across tasks.

Definitions (plan STEP 'CONVENTIONS'):
  correct-Y(row)   = row passed the hidden tests AND its mechanism label is in Y(source) (invalid / failing = not-Y)
  TRANSFER(arm)    = (correct-Y count under arm - under the unedited base) / N, paired CRN slots 0-29
  RECOVERY_k       = sum over held-out sources of [count(DAS_k) - count(base)] / sum of [count(FULL) - count(base)]
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any

import numpy as np

from cfg import read_json, read_jsonl
from cfg7 import CATALOGUE7, DEFAULT7, LABELS7, RANKS, results7
from stats6 import clopper_pearson, holm, mcnemar_exact

N = 30
BOOT = 2000


# ------------------------------------------------------------------------------------------------ data
def arms_of(task: str) -> dict[str, dict[int, dict[str, Any]]]:
    out: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    for r in read_jsonl(LABELS7):
        if r["task"] == task:
            out[r["arm"]][int(r["slot_index"])] = r
    return out


def cy(r: dict[str, Any] | None, Y: list[str]) -> int:
    return int(bool(r) and bool(r.get("passed")) and r.get("label") in Y)


def off_default(r: dict[str, Any] | None, D: str) -> int:
    return int(bool(r) and bool(r.get("passed")) and r.get("label") not in (D, "invalid", None))


def vec(A: dict, arm: str, Y: list[str], n: int = N) -> np.ndarray | None:
    if arm not in A:
        return None
    return np.array([cy(A[arm].get(s), Y) for s in range(n)])


def pass_rate(A: dict, arm: str, n: int = N) -> float | None:
    if arm not in A:
        return None
    rs = [A[arm].get(s) for s in range(n) if A[arm].get(s)]
    return float(np.mean([bool(r.get("passed")) for r in rs])) if rs else None


def full_ban_arm(task: str) -> str:
    s = read_json(results7(f"site_{task}.json"))
    return "FULL_ban_band" if s["site"] == "band" else f"FULL_ban_L{s['L_star']}"


# ------------------------------------------------------------------------------------------------ sources
PREFIX = {"MAIN": ("DAS", "PERM", "PERM", "RPOS", "REV", "NULL"),
          "MAIN_LY": ("DASLY", "PERMLY", "PERM_LY", "RPOSLY", "REVLY", "NULLLY")}
FIT = {"name": "MAIN_LY"}


def sources(task: str) -> list[dict[str, Any]]:
    """Held-out sources with their arm names, base arm and Y set (map FIT['name'])."""
    P, PP = PREFIX[FIT["name"]][:2]
    T = read_json(results7(f"targets_{task}.json"))
    ks = read_json(results7(f"kstar_{task}.json"))
    landing = T["landing"] or T["kept_Y"][:1]
    out = [{"name": "ban", "Y": landing, "base": "BASE_W5", "full": full_ban_arm(task),
            "das": {k: f"{P}_ban_k{k}" for k in RANKS},
            "rand": {16: ["RAND_ban_k16_d1", "RAND_ban_k16_d2", "RAND_ban_k16_d3"],
                     ks["k_star"]: ([f"RAND_ban_k{ks['k_star']}"] if ks["k_star"] != 16 else
                                    ["RAND_ban_k16_d1", "RAND_ban_k16_d2", "RAND_ban_k16_d3"])},
            "perm": {16: f"{PP}_ban_k16", ks["k_star"]: f"{PP}_ban_k{ks['k_star']}"}}]
    for Y in ks["kept_Y_cells"]:
        out.append({"name": f"F_{Y}", "Y": [Y], "base": "BASE_PAD", "full": f"FULL_F_{Y}",
                    "das": {k: f"{P}_F_{Y}_k{k}" for k in (1, 4, 16)}, "rand": {16: [f"RAND_F_{Y}_k16"]},
                    "perm": {16: f"{PP}_F_{Y}_k16"}})
    return out


def counts_vec(A: dict, src: dict[str, Any], arm: str) -> np.ndarray | None:
    return vec(A, arm, src["Y"])


def pooled_recovery(A: dict, srcs: list[dict[str, Any]], k: int, slots: np.ndarray | None = None,
                    which: str = "das") -> tuple[float | None, float, float]:
    num = den = 0.0
    for s in srcs:
        b, f = counts_vec(A, s, s["base"]), counts_vec(A, s, s["full"])
        if which == "das":
            arms = [s["das"].get(k)] if s["das"].get(k) else []
        else:
            arms = s["rand"].get(k, [])
        vs = [counts_vec(A, s, a) for a in arms]
        vs = [v for v in vs if v is not None]
        if b is None or f is None or not vs:
            continue
        idx = slots if slots is not None else np.arange(N)
        x = float(np.mean([v[idx].sum() for v in vs]))
        num += x - b[idx].sum()
        den += f[idx].sum() - b[idx].sum()
    return (num / den if den > 0 else None), num, den


def boot_ci(A: dict, srcs: list[dict[str, Any]], k: int, which: str = "das", seed: int = 20261022
            ) -> list[float | None]:
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(BOOT):
        idx = rng.integers(0, N, N)
        r, _, _ = pooled_recovery(A, srcs, k, idx, which)
        if r is not None:
            vals.append(r)
    if len(vals) < 100:
        return [None, None]
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def mcnemar_das_rand(A: dict, srcs: list[dict[str, Any]], k: int) -> dict[str, Any]:
    b = c = 0
    for s in srcs:
        da = s["das"].get(k)
        ra = (s["rand"].get(k) or [None])[0]
        if not da or not ra or da not in A or ra not in A:
            continue
        v1, v2 = counts_vec(A, s, da), counts_vec(A, s, ra)
        b += int(((v1 == 1) & (v2 == 0)).sum())
        c += int(((v1 == 0) & (v2 == 1)).sum())
    return {"b_das_only": b, "c_rand_only": c, "p": mcnemar_exact(b, c)}


# ------------------------------------------------------------------------------------------------ P1
def p1_task(task: str) -> dict[str, Any]:
    A = arms_of(task)
    srcs = sources(task)
    ks = read_json(results7(f"kstar_{task}.json"))["k_star"]
    out: dict[str, Any] = {"task": task, "k_star": ks, "per_k": {}, "per_source": {}}
    for s in srcs:
        b, f = counts_vec(A, s, s["base"]), counts_vec(A, s, s["full"])
        if b is None or f is None:
            continue
        ps = {"Y": s["Y"], "base_count": int(b.sum()), "full_count": int(f.sum()),
              "full_transfer": float((f.sum() - b.sum()) / N), "base_pass": pass_rate(A, s["base"]),
              "full_pass": pass_rate(A, s["full"]), "das": {}, "rand": {}, "perm": {}}
        for k, a in s["das"].items():
            v = counts_vec(A, s, a)
            if v is not None:
                ps["das"][k] = {"count": int(v.sum()), "transfer": float((v.sum() - b.sum()) / N),
                                "recovery": float((v.sum() - b.sum()) / (f.sum() - b.sum())) if f.sum() > b.sum()
                                else None, "pass": pass_rate(A, a),
                                "share_ci": clopper_pearson(int(v.sum()), N)}
        for k, arms in s["rand"].items():
            for a in arms:
                v = counts_vec(A, s, a)
                if v is not None:
                    ps["rand"][a] = {"count": int(v.sum()), "transfer": float((v.sum() - b.sum()) / N),
                                     "pass": pass_rate(A, a)}
        for k, a in s["perm"].items():
            v = counts_vec(A, s, a)
            if v is not None:
                ps["perm"][a] = {"count": int(v.sum()), "transfer": float((v.sum() - b.sum()) / N),
                                 "pass": pass_rate(A, a)}
        out["per_source"][s["name"]] = ps
    cand_k = sorted({16, ks})
    for k in RANKS:
        r, num, den = pooled_recovery(A, srcs, k)
        rr, rnum, rden = pooled_recovery(A, srcs, k, which="rand") if k in cand_k else (None, 0, 0)
        e = {"recovery": r, "num": num, "den": den, "recovery_ci": boot_ci(A, srcs, k) if r is not None else None,
             "random_recovery": rr}
        if k in cand_k:
            e["mcnemar_das_vs_rand"] = mcnemar_das_rand(A, srcs, k)
            perm_tr = []
            for s in srcs:
                a = s["perm"].get(k)
                b = counts_vec(A, s, s["base"])
                v = counts_vec(A, s, a) if a else None
                if v is not None and b is not None:
                    perm_tr.append(float((v.sum() - b.sum()) / N))
            e["permuted_transfer_max"] = max(perm_tr) if perm_tr else None
            # pass clause on every DAS arm at k
            pr = []
            for s in srcs:
                a = s["das"].get(k)
                if a and a in A and pass_rate(A, s["base"]):
                    pr.append(pass_rate(A, a) / pass_rate(A, s["base"]))
            e["pass_ratio_min"] = min(pr) if pr else None
        out["per_k"][k] = e
    # slot IIA for the ban source (label equals the full ban prompt's label on the slot)
    ref = A.get("BAN_W5", {})
    iia = {}
    for k in RANKS:
        a = f"{PREFIX[FIT['name']][0]}_ban_k{k}"
        if a in A and ref:
            iia[k] = float(np.mean([A[a][s]["label"] == ref[s]["label"] for s in range(N) if s in A[a] and s in ref]))
    fa = full_ban_arm(task)
    if fa in A and ref:
        iia["full"] = float(np.mean([A[fa][s]["label"] == ref[s]["label"] for s in range(N) if s in A[fa] and s in ref]))
    out["slot_iia_ban"] = iia
    return out


def p1_all(tasks: list[str]) -> dict[str, Any]:
    res = {t: p1_task(t) for t in tasks}
    # choose per task the candidate k (16 or k*) that satisfies the most clauses (smallest p on ties)
    pv = {}
    for t, r in res.items():
        best = None
        for k in sorted({16, r["k_star"]}):
            e = r["per_k"][k]
            if e.get("mcnemar_das_vs_rand") is None:
                continue
            cl = {"recovery_ge_0.8": (e["recovery"] or 0) >= 0.8,
                  "margin_ge_0.4": (e["recovery"] or 0) - (e["random_recovery"] or 0) >= 0.4,
                  "permuted_le_0.1": e["permuted_transfer_max"] is not None and e["permuted_transfer_max"] <= 0.1,
                  "pass_ge_0.8x": e["pass_ratio_min"] is not None and e["pass_ratio_min"] >= 0.8}
            score = (sum(cl.values()), -e["mcnemar_das_vs_rand"]["p"])
            if best is None or score > best[0]:
                best = (score, k, cl)
        if best:
            r["P1_k"] = best[1]
            r["P1_clauses"] = best[2]
            pv[t] = r["per_k"][best[1]]["mcnemar_das_vs_rand"]["p"]
    ph = holm(pv)
    n_pass = 0
    for t, r in res.items():
        if "P1_k" not in r:
            r["P1"] = "NOT ESTIMABLE"
            continue
        r["P1_clauses"]["mcnemar_holm_lt_0.01"] = ph.get(t, 1.0) < 0.01
        r["mcnemar_p_holm"] = ph.get(t)
        # the Sutter control matched to the evaluated map: the LME_Y-objective random-network fit when present
        rp = results7(f"randinit_ly_{t}.json") if FIT["name"] == "MAIN_LY" else results7(f"randinit_{t}.json")
        ri = read_json(rp) if rp.exists() else None
        r["random_init_control"] = {"file": rp.name, "present": ri is not None,
                                    **({k: ri.get(k) for k in ("random_net_heldout_das16_gain",
                                                              "trained_heldout_das16_gain", "ratio",
                                                              "random_net_heldout_das16_lmeY_gain",
                                                              "trained_heldout_das16_lmeY_gain", "ratio_lmeY")}
                                       if ri else {})}
        if t == "T2":
            r["P1_clauses"]["random_init_lt_0.5"] = bool(ri and ri.get("c3_pass_lt_0.5"))
        ok = all(r["P1_clauses"].values())
        r["P1"] = "PASS" if ok else "FAIL"
        n_pass += ok
    rec16 = [r["per_k"][16]["recovery"] for r in res.values() if r["per_k"].get(16)]
    overall = ("PASS" if n_pass >= 2 else ("DISCONFIRMED" if rec16 and all((x or 0) < 0.5 for x in rec16)
                                            else "NOT SUPPORTED"))
    return {"tasks": res, "holm": ph, "n_pass": n_pass, "overall": overall}


# ------------------------------------------------------------------------------------------------ controls
def controls(task: str) -> dict[str, Any]:
    A = arms_of(task)
    T = read_json(results7(f"targets_{task}.json"))
    D = DEFAULT7[task]
    landing = T["landing"] or T["kept_Y"][:1]
    out = {}

    def tr(arm: str, base: str, Y: list[str]) -> dict[str, Any] | None:
        v, b = vec(A, arm, Y), vec(A, base, Y)
        if v is None or b is None:
            return None
        return {"count": int(v.sum()), "base": int(b.sum()), "transfer": float((v.sum() - b.sum()) / N),
                "pass": pass_rate(A, arm), "n": int(len(A[arm]))}
    for arm in ("RPOSLY_ban_k16", "RPOS_ban_k16", "RPOSFULL_ban", "DIM1_ban", "PCA16_ban"):
        out[arm] = tr(arm, "BASE_W5", landing)
    # null source: off-default transfer against the padding-twin base of the same prompts
    for arm in ("NULLLY_k16", "NULL_k16", "NULL_full"):
        if arm in A and "BASE_PAD" in A:
            v = np.array([off_default(A[arm].get(s), D) for s in range(N)])
            b = np.array([off_default(A["BASE_PAD"].get(s), D) for s in range(N)])
            out[arm] = {"off_default_count": int(v.sum()), "base_off_default": int(b.sum()),
                        "off_default_transfer": float((v.sum() - b.sum()) / N), "pass": pass_rate(A, arm),
                        "labels": dict(Counter(A[arm][s]["label"] for s in A[arm]))}
    # W4 reported separately (N = 10)
    ks = read_json(results7(f"kstar_{task}.json"))["k_star"]
    for arm in ("BASE_W4", "FULL_W4", f"{PREFIX[FIT['name']][0]}_W4_k{ks}"):
        if arm in A:
            v = np.array([cy(A[arm].get(s), landing) for s in range(10)])
            out[arm] = {"count": int(v.sum()), "n": 10, "pass": pass_rate(A, arm, 10)}
    return out


# ------------------------------------------------------------------------------------------------ C routing
def routing(task: str, p1k: int | None) -> dict[str, Any]:
    A = arms_of(task)
    D = DEFAULT7[task]
    ks = read_json(results7(f"kstar_{task}.json"))
    out = {"task": task, "per_Y": {}, "confusion": {}}
    labs = CATALOGUE7[task] + ["other"]
    for Y in ks["kept_Y_cells"]:
        e = {}
        for nm, arm in [("full", f"FULL_F_{Y}")] + [(f"k{k}", f"{PREFIX[FIT['name']][0]}_F_{Y}_k{k}")
                                                    for k in (1, 4, 16)]:
            if arm not in A:
                continue
            rs = [A[arm][s] for s in range(N) if s in A[arm]]
            corr = [r for r in rs if r.get("passed")]
            offd = [r for r in corr if r["label"] != D]
            ny = sum(r["label"] == Y for r in corr)
            rt = ny / len(offd) if offd else None
            e[nm] = {"n": len(rs), "correct_Y": ny, "correct_off_default": len(offd),
                     "routing": rt, "routing_ci": clopper_pearson(ny, len(offd)) if offd else None,
                     "off_default_transfer": len(offd) / N,
                     "landing": dict(Counter(r["label"] for r in corr)), "fail": len(rs) - len(corr)}
            out["confusion"].setdefault(nm, {})[Y] = {l: sum(r["label"] == l for r in corr) for l in labs}
            out["confusion"][nm][Y]["fail"] = len(rs) - len(corr)
        e["routable_at_site"] = (e.get("full", {}).get("routing") or 0) >= 0.6
        out["per_Y"][Y] = e
    kk = p1k if p1k in (1, 4, 16) else 16
    out["k_for_C"] = kk
    cat_Y = [Y for Y, e in out["per_Y"].items() if (e.get(f"k{kk}", {}).get("routing") or 0) >= 0.6]
    out["Y_routed_ge_0.6"] = cat_Y
    small = None
    for k in (1, 4, 16):
        if sum((e.get(f"k{k}", {}).get("routing") or 0) >= 0.6 for e in out["per_Y"].values()) >= 2:
            small = k
            break
    out["smallest_k_routing_2Y"] = small
    return out


def c_verdict(rt: dict[str, dict[str, Any]], landing: dict[str, list[str]]) -> dict[str, Any]:
    cat_tasks = [t for t, r in rt.items() if len(r["Y_routed_ge_0.6"]) >= 2]
    margin = {}
    for t, r in rt.items():
        kk = r["k_for_C"]
        run_up = (landing.get(t) or [None])[0]
        others = [Y for Y in r["per_Y"] if Y != run_up and r["per_Y"][Y].get("routable_at_site")]
        low = all((r["per_Y"][Y].get(f"k{kk}", {}).get("routing") or 0) <= 0.2 for Y in others) if others else False
        trans = all((r["per_Y"][Y].get(f"k{kk}", {}).get("off_default_transfer") or 0) >= 0.5 for Y in others) \
            if others else False
        margin[t] = bool(low and trans)
    if len(cat_tasks) >= 2:
        v = "CATEGORICAL"
    elif sum(margin.values()) >= 2 or (margin and all(margin.values())):
        v = "MARGIN-AND-LADDER"
    else:
        v = "MIXED"
    return {"verdict": v, "categorical_tasks": cat_tasks, "margin_and_ladder_by_task": margin}


# ------------------------------------------------------------------------------------------------ dormant
def dormant(task: str, p1: dict[str, Any]) -> dict[str, Any]:
    import torch

    from cfg7 import MAPS7
    from cfg import ROOT
    z = np.load(ROOT / "cache" / f"natural_states_{task}.npz")
    keys = list(z.keys())
    X = np.stack([z[k] for k in keys]).astype(np.float64)
    kinds = [k.split("__")[1] for k in keys]
    nat = np.array([kd in ("twin", "ban", "forced") for kd in kinds])
    tw = np.array([kd == "twin" for kd in kinds])
    W = torch.load(MAPS7 / f"{task}_{FIT['name']}.pt", map_location="cpu")["basis"].double().numpy()
    rng = np.random.default_rng(1)

    def share(Xs: np.ndarray, B: np.ndarray) -> float:
        Xc = Xs - Xs.mean(0)
        return float(((Xc @ B.T) ** 2).sum() / (Xc ** 2).sum())
    out = {"task": task, "by_k": {}, "note": "spec-mean states at the site's middle block (cache/natural_states)"}
    Xn = X[nat]
    U, S, Vt = np.linalg.svd(Xn - Xn.mean(0), full_matrices=False)
    for k in RANKS:
        s_k = share(Xn, W[:k])
        rnd = []
        for _ in range(1000):
            q, _ = np.linalg.qr(rng.standard_normal((X.shape[1], k)))
            rnd.append(share(Xn, q.T))
        pca = float((S[:k] ** 2).sum() / (S ** 2).sum())
        out["by_k"][k] = {"natural_share": s_k, "random_mean": float(np.mean(rnd)),
                          "percentile_vs_random": float((np.array(rnd) < s_k).mean() * 100), "pca_upper": pca,
                          "twin_only_share": share(X[tw], W[:k]) if tw.sum() > 2 else None}
    # displacement share over held-out pairs (spec means): ||R_k d||^2 / ||d||^2
    T = read_json(results7(f"targets_{task}.json"))
    from stages_b7 import held_pairs
    idx = {k: i for i, k in enumerate(keys)}
    disp = defaultdict(list)
    for (s, b, g, kind) in held_pairs(task, T):
        ks_, kb_ = s.replace("|", "__"), b.replace("|", "__")
        if ks_ in idx and kb_ in idx:
            d = X[idx[ks_]] - X[idx[kb_]]
            for k in RANKS:
                disp[k].append(float(((W[:k] @ d) ** 2).sum() / (d ** 2).sum()))
    for k in RANKS:
        out["by_k"][k]["displacement_share_heldout"] = float(np.mean(disp[k])) if disp[k] else None
        out["by_k"][k]["displacement_share_random_expect"] = k / X.shape[1]
    # projected-map TF retention (gain in the fitted objective's TF contrast)
    ly = FIT["name"] == "MAIN_LY"
    tf = read_json(results7(f"tf_eval_{task}_LY.json" if ly else f"tf_eval_{task}.json"))["summary"]
    dn, pn = ("DASLY", "PROJLY") if ly else ("DAS", "PROJ")
    for k in RANKS:
        ret = []
        for kind in ("ban", "forced"):
            if kind in tf and f"{pn}_k{k}" in tf[kind] and tf[kind][f"{dn}_k{k}"]["mean_gain"] > 1e-6:
                ret.append(tf[kind][f"{pn}_k{k}"]["mean_gain"] / tf[kind][f"{dn}_k{k}"]["mean_gain"])
        out["by_k"][k]["projected_tf_retention"] = float(np.mean(ret)) if ret else None
    # reverse interchange (generation)
    A = arms_of(task)
    D = DEFAULT7[task]
    ks = read_json(results7(f"kstar_{task}.json"))["k_star"]
    ref = vec(A, "BAN_W5", [D])
    rv = {}
    ra = f"{PREFIX[FIT['name']][4]}_k{ks}"
    for arm in (ra, "REV_full"):
        v = vec(A, arm, [D])
        if v is not None and ref is not None:
            rv[arm] = {"default_count": int(v.sum()), "ban_ref_default_count": int(ref.sum()),
                       "transfer": float((v.sum() - ref.sum()) / N), "pass": pass_rate(A, arm)}
    rec = None
    if ra in rv and "REV_full" in rv and rv["REV_full"]["transfer"] > 0:
        rec = rv[ra]["transfer"] / rv["REV_full"]["transfer"]
    out["reverse"] = rv
    out["reverse_recovery"] = rec
    fwd = (p1["per_k"].get(ks) or {}).get("recovery")
    proj = out["by_k"][ks]["projected_tf_retention"]
    out["DORMANT_FLAG"] = bool(fwd is not None and fwd >= 0.8 and ((proj is not None and proj < 0.5) or
                                                                  (rec is not None and rec < 0.5)))
    out["rule"] = "projected-map TF retention < 0.5 OR reverse recovery < 0.5 while forward recovery >= 0.8"
    return out


# ------------------------------------------------------------------------------------------------ R
def logistic_width(lams: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    from scipy.optimize import minimize

    def nll(th: np.ndarray) -> float:
        l0, ls = th
        s = math.exp(ls)
        p = 1 / (1 + np.exp(-(lams - l0) / s))
        p = np.clip(p, 1e-9, 1 - 1e-9)
        return float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).sum())
    best = None
    for l0 in (0.3, 0.6, 0.9, 1.2):
        for ls in (-3.0, -2.0, -1.0, 0.0):
            r = minimize(nll, np.array([l0, ls]), method="Nelder-Mead", options={"xatol": 1e-5, "fatol": 1e-7,
                                                                                  "maxiter": 4000})
            if best is None or r.fun < best.fun:
                best = r
    l0, ls = best.x
    s = math.exp(ls)
    return {"lam0": float(l0), "s": float(s), "width_10_90": float(2 * s * math.log(9)), "nll": float(best.fun)}


def r_discreteness(task: str) -> dict[str, Any] | None:
    A = arms_of(task)
    T = read_json(results7(f"targets_{task}.json"))
    landing = T["landing"] or T["kept_Y"][:1]
    D = DEFAULT7[task]
    rows = []
    for arm, d in A.items():
        if arm.startswith("LAM") and "_ban_" in arm:
            lam = float(arm[3:].split("_")[0])
            for s, r in d.items():
                rows.append((lam, cy(r, landing), r))
    if not rows:
        return None
    lams = np.array([x[0] for x in rows])
    y = np.array([x[1] for x in rows])
    fit = logistic_width(lams, y)
    curve = {}
    for lam in sorted(set(lams)):
        rs = [x[2] for x in rows if x[0] == lam]
        curve[lam] = {"n": len(rs), "correct_Y": int(sum(cy(r, landing) for r in rs)),
                      "correct_default": int(sum(cy(r, [D]) for r in rs)),
                      "pass": float(np.mean([bool(r.get("passed")) for r in rs])),
                      "labels": dict(Counter(r["label"] for r in rs))}
    cand = [x[2] for x in rows if 0.2 <= x[0] <= 1.0 and x[2].get("passed") and
            (x[2]["label"] == "other" or (x[2].get("runtime_label") not in (None, x[2].get("ast_label"))
                                          and x[2].get("ast_label") not in (None, "unknown")))]
    n_correct = int(sum(bool(x[2].get("passed")) for x in rows if 0.2 <= x[0] <= 1.0))
    return {"task": task, "fit": fit, "curve": curve, "hybrid_candidates": [r["sample_id"] for r in cand],
            "n_correct_0.2_1.0": n_correct}


def summarize_tf(task: str) -> dict[str, Any]:
    return read_json(results7(f"tf_eval_{task}.json"))


def pilot_main(task: str) -> dict[str, Any]:
    """The committed contrastive map (MAIN) on slots 0-9: correct-Y, pass rate, label mix, mean length per arm."""
    A = arms_of(task)
    T = read_json(results7(f"targets_{task}.json"))
    landing = T["landing"] or T["kept_Y"][:1]
    out = {}
    for arm in sorted(a for a in A if a.startswith("DAS_")):
        Y = landing if "_ban_" in arm else [arm.split("_F_")[1].rsplit("_k", 1)[0]]
        rs = [A[arm][s] for s in range(10) if s in A[arm]]
        base = "BASE_W5" if "_ban_" in arm else "BASE_PAD"
        b = [A[base][s] for s in range(10) if base in A and s in A[base]]
        out[arm] = {"n": len(rs), "correct_Y": sum(cy(r, Y) for r in rs), "base_correct_Y": sum(cy(r, Y) for r in b),
                    "pass": float(np.mean([bool(r.get("passed")) for r in rs])) if rs else None,
                    "base_pass": float(np.mean([bool(r.get("passed")) for r in b])) if b else None,
                    "labels": dict(Counter(r["label"] for r in rs)),
                    "mean_new_tokens": float(np.mean([r.get("n_new_tokens") or 0 for r in rs])) if rs else None,
                    "finish": dict(Counter(r.get("finish_reason") for r in rs))}
    return out


def mgen_summary(task: str = "T2") -> dict[str, Any] | None:
    """Behaviour of the prompts M places (extension): correct label composition per prompt kind, N = 30."""
    A = arms_of(task)
    D = DEFAULT7[task]
    out = {}
    for arm in sorted(a for a in A if a.startswith("MGEN_")):
        rs = [A[arm][s] for s in range(N) if s in A[arm]]
        corr = Counter(r["label"] for r in rs if r.get("passed"))
        off = sum(v for k, v in corr.items() if k not in (D,))
        out[arm[5:]] = {"n": len(rs), "pass": float(np.mean([bool(r.get("passed")) for r in rs])) if rs else None,
                        "correct_composition": dict(corr), "correct_off_default": off,
                        "off_default_ci": clopper_pearson(off, len(rs)) if rs else None,
                        "n_truncated": sum(r.get("finish_reason") == "length" for r in rs)}
    return out or None


def seed2_summary(task: str = "T2") -> dict[str, Any] | None:
    from cfg import read_json as rj
    p = results7(f"seed2_{task}.json")
    if not p.exists():
        return None
    s2 = rj(p)
    A = arms_of(task)
    T = read_json(results7(f"targets_{task}.json"))
    landing = T["landing"] or T["kept_Y"][:1]
    rows = {}
    for arm in sorted(a for a in A if a.startswith("DASLY2_")):
        Y = landing if "_ban_" in arm else [arm.split("_F_")[1].rsplit("_k", 1)[0]]
        a1 = arm.replace("DASLY2_", "DASLY_")
        v2, v1 = vec(A, arm, Y), vec(A, a1, Y)
        e = {"seed2_count": int(v2.sum()) if v2 is not None else None,
             "seed1_count": int(v1.sum()) if v1 is not None else None, "pass_seed2": pass_rate(A, arm)}
        if v1 is not None and v2 is not None:
            e["discordant_s1only_s2only"] = [int(((v1 == 1) & (v2 == 0)).sum()), int(((v1 == 0) & (v2 == 1)).sum())]
            e["mcnemar_p"] = mcnemar_exact(*e["discordant_s1only_s2only"])
        rows[arm] = e
    return {"task": task, "principal_angles_deg": s2["principal_angles_deg"], "cells": rows,
            "fit_best_val": s2["fit"].get("best_val")}
