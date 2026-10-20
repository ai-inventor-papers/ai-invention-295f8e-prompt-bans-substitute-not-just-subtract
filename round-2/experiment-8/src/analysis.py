#!/usr/bin/env python3
"""S8 analysis (sha256 frozen in results/prereg.json before any arm was scored or sampled).

FRLP: lw(p, cell) = l(p | cell) - l(p | F_j), l(p | F_j) = log sum_k pi_k exp l(p | F_j^k) with pi_k the share of
generated samples drawn from forced prompt k (mixture proposal). L_j(cell) = log mean_m exp lw(p_m, cell) over the 30
programs of j, each scored under its own half's neutral noun. D_X(arm) = L_X(arm) - L_X(b), averaged over templates
with ESS down-weighting (weight min(1, ESS/5)). Two-level crossed bootstrap: templates, then programs within halves.
Route fractions F_direct = D(d)/D(a), F_prompt = D(c)/D(a), interaction I = D(a) - D(c) - D(d); pooled over tasks as
ratios of sums. Behaviour, matched flips, survivor gains, token localisation, knockouts, lens and C5 statistics.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from typing import Any

import numpy as np
from loguru import logger
from scipy import stats

from cfg import (ALGOS, DATA_DIR, KO_WINDOW, N_BOOT, N_PERM_C5, RESULTS_DIR, SIGNATURE_VOCAB, SURVIVORS, TASKS,
                 TEMPLATE_IDS, THRESHOLDS, TOKEN_LP_DIR, X_KEY, read_jsonl, wilson_ci, write_json)

ARMS_X = ("a", "b", "c", "d", "e", "f", "K0", "K1", "K2", "B1", "B2", "B3", "K0b", "mention")
RNG_SEED = 20261020


# ================================================================================================ helpers
def lme(x: np.ndarray, axis: int = -1) -> np.ndarray:
    """log-mean-exp along axis (NaN-free inputs)."""
    m = np.max(x, axis=axis, keepdims=True)
    return np.squeeze(m, axis) + np.log(np.mean(np.exp(x - m), axis=axis))


def ess_of(lw: np.ndarray, axis: int = -1) -> np.ndarray:
    m = np.max(lw, axis=axis, keepdims=True)
    w = np.exp(lw - m)
    return np.sum(w, axis=axis) ** 2 / np.sum(w ** 2, axis=axis)


def pct(x: np.ndarray, q: float) -> float:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    return float(np.percentile(x, q)) if len(x) else float("nan")


def ci(x: np.ndarray) -> list[float]:
    return [pct(x, 2.5), pct(x, 97.5)]


def safe_ratio(a: Any, b: Any) -> Any:
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(np.abs(b) > 1e-12, a / b, np.nan)


# ================================================================================================ FRLP tables
def load_frlp() -> dict[str, Any]:
    """Returns per task: program order, per-program denominators, and lw arrays per (condition, template)."""
    progs = read_jsonl(DATA_DIR / "frlp_programs.jsonl")
    summ = json.loads((RESULTS_DIR / "frlp_programs_summary.json").read_text())["per_algorithm"]
    scores = read_jsonl(DATA_DIR / "frlp_scores.jsonl")
    ll: dict[tuple[str, str, str, str], float] = {}
    for r in scores:
        ll[(r["condition"], r["template"], r["noun"], r["uid"])] = r["ll"]
    out: dict[str, Any] = {}
    for t in TASKS:
        tp = [p for p in progs if p["task"] == t]
        for p in tp:
            p["uid"] = f"{p['task']}:{p['algorithm']}:{p['prog_index']}"
        per_alg: dict[str, Any] = {}
        for j in ALGOS[t]:
            pj = sorted([p for p in tp if p["algorithm"] == j], key=lambda p: (p["half"], p["prog_index"]))
            if not pj:
                continue
            counts = summ[f"{t}:{j}"]["prompt_counts"]
            keys, wts = [], []
            for k, n in counts.items():
                kind, idx = k.split(":")
                keys.append(f"forced_{j}_{'p' if kind == 'paraphrase' else 'd'}{idx}")
                wts.append(n)
            wts_a = np.array(wts, dtype=float) / np.sum(wts)
            den, den_gen, ok = [], [], []
            for p in pj:
                vals = [ll.get((kk, "F", "-", p["uid"])) for kk in keys]
                if any(v is None for v in vals):
                    den.append(np.nan)
                    ok.append(False)
                else:
                    v = np.array(vals)
                    m = v.max()
                    den.append(m + math.log(np.sum(wts_a * np.exp(v - m))))
                    ok.append(True)
                gk = f"forced_{j}_{'p' if p['prompt_kind'] == 'paraphrase' else 'd'}{p['prompt_index']}"
                den_gen.append(ll.get((gk, "F", "-", p["uid"]), np.nan))
            per_alg[j] = {"uids": [p["uid"] for p in pj], "half": np.array([p["half"] for p in pj]),
                          "passed": np.array([bool(p["passed"]) for p in pj]), "den": np.array(den),
                          "den_gen": np.array(den_gen), "den_ok": all(ok), "n": len(pj)}
        out[t] = {"alg": per_alg, "ll": ll}
    return out


def _arm_ll(ll: dict, cond: str, w: str, uid: str, half: int) -> float:
    """l(p | arm) for program uid in template w, using the noun of the program's own half."""
    noun = "A" if half == 1 else "B"
    if cond in ("a", "K0", "K1", "K2", "B1", "B2", "B3", "mention"):
        return ll.get((cond, w, "-", uid), np.nan)
    if cond == "pl":
        return ll.get(("pl", w, "AB", uid), np.nan)
    if cond == "bB":  # neutral noun B for every program (placebo reference)
        return ll.get(("b", w, "B", uid), np.nan)
    return ll.get((cond, w, noun, uid), np.nan)


def lw_tensor(F: dict[str, Any], t: str, j: str, conds: tuple[str, ...], den_key: str = "den") -> np.ndarray:
    """lw[cond, template, program] for algorithm j."""
    A = F[t]["alg"][j]
    ll = F[t]["ll"]
    arr = np.full((len(conds), len(TEMPLATE_IDS), A["n"]), np.nan)
    for ci_, c in enumerate(conds):
        for wi, w in enumerate(TEMPLATE_IDS):
            for m, (uid, h) in enumerate(zip(A["uids"], A["half"])):
                arr[ci_, wi, m] = _arm_ll(ll, c, w, uid, int(h)) - A[den_key][m]
    return arr


def _boot_indices(halves: np.ndarray, n_boot: int, rng: np.random.Generator, n_templates: int) -> tuple:
    h1 = np.where(halves == 1)[0]
    h2 = np.where(halves == 2)[0]
    P = np.concatenate([rng.choice(h1, size=(n_boot, len(h1))), rng.choice(h2, size=(n_boot, len(h2)))], axis=1)
    W = rng.integers(0, n_templates, size=(n_boot, n_templates))
    return P, W


def d_stats(lw: np.ndarray, ref: int, P: np.ndarray | None = None, W: np.ndarray | None = None,
            ess_weight: bool = True) -> np.ndarray:
    """lw [C, W, M] -> D[C] (or [B, C] with bootstrap indices): template-averaged L(c) - L(ref), ESS-down-weighted."""
    if P is None:
        L = lme(lw, axis=-1)                     # [C, W]
        E = ess_of(lw, axis=-1)
        D = L - L[ref][None]
        if ess_weight:
            om = np.minimum(1.0, np.minimum(E, E[ref][None]) / THRESHOLDS["ess_flag"])
        else:
            om = np.ones_like(D)
        return np.nansum(om * D, axis=-1) / np.nansum(om, axis=-1)
    # bootstrap: lw[:, W[b], :][:, :, P[b]]
    sub = lw[:, W, :]                             # [C, B, W, M]
    sub = np.take_along_axis(sub, P[None, :, None, :].repeat(sub.shape[2], axis=2), axis=3)
    L = lme(sub, axis=-1)                         # [C, B, W]
    E = ess_of(sub, axis=-1)
    D = L - L[ref][None]
    if ess_weight:
        om = np.minimum(1.0, np.minimum(E, E[ref][None]) / THRESHOLDS["ess_flag"])
    else:
        om = np.ones_like(D)
    return (np.nansum(om * D, axis=-1) / np.nansum(om, axis=-1)).T   # [B, C]


def mean_ll_diff(llx: np.ndarray, ref: int, P: np.ndarray | None = None, W: np.ndarray | None = None) -> np.ndarray:
    """F6 robustness readout without weights: mean over programs and templates of l(p|arm) - l(p|ref)."""
    diff = llx - llx[ref][None]
    if P is None:
        return np.nanmean(diff, axis=(1, 2))
    sub = diff[:, W, :]
    sub = np.take_along_axis(sub, P[None, :, None, :].repeat(sub.shape[2], axis=2), axis=3)
    return np.nanmean(sub, axis=(2, 3)).T


def route_analysis(F: dict[str, Any], n_boot: int = N_BOOT, variant: str = "primary") -> dict[str, Any]:
    """variant: primary | correct_only | gen_paraphrase | no_ess_weight | mean_ll."""
    conds = ("a", "b", "c", "d", "e", "f", "K0", "K1", "K2", "B1", "B2", "B3", "K0b", "mention")
    rng = np.random.default_rng(RNG_SEED)
    res: dict[str, Any] = {"variant": variant, "per_task": {}}
    boots: dict[str, np.ndarray] = {}
    for t in TASKS:
        x = X_KEY[t]
        if x not in F[t]["alg"]:
            continue
        A = F[t]["alg"][x]
        den_key = "den_gen" if variant == "gen_paraphrase" else "den"
        lw = lw_tensor(F, t, x, conds, den_key)
        keep = np.ones(A["n"], dtype=bool)
        if variant == "correct_only":
            keep = A["passed"].copy()
            if not (keep & (A["half"] == 1)).any() or not (keep & (A["half"] == 2)).any():
                continue
        lw = lw[:, :, keep]
        halves = A["half"][keep]
        # templates where a condition is missing entirely are dropped for that condition (NaN-safe means)
        P, W = _boot_indices(halves, n_boot, rng, len(TEMPLATE_IDS))
        ref = conds.index("b")
        if variant == "mean_ll":
            llx = lw + A[den_key][keep][None, None, :]
            point = mean_ll_diff(llx, ref)
            bs = mean_ll_diff(llx, ref, P, W)
        else:
            ew = variant != "no_ess_weight"
            point = d_stats(np.nan_to_num(lw, nan=-1e9), ref, ess_weight=ew)
            bs = d_stats(np.nan_to_num(lw, nan=-1e9), ref, P, W, ess_weight=ew)
        avail = {c: bool(np.isfinite(lw[i]).all()) for i, c in enumerate(conds)}
        point = np.where([avail[c] for c in conds], point, np.nan)
        bs = np.where(np.array([avail[c] for c in conds])[None], bs, np.nan)
        D = {c: float(point[i]) for i, c in enumerate(conds)}
        Db = {c: bs[:, i] for i, c in enumerate(conds)}
        boots[t] = bs
        a_ci = ci(Db["a"])
        ent = {"D": D, "D_ci": {c: ci(Db[c]) for c in conds}, "n_programs": int(keep.sum()),
               "prerequisite_met": bool(D["a"] < 0 and a_ci[1] < 0),
               "F_direct": float(safe_ratio(D["d"], D["a"])), "F_prompt": float(safe_ratio(D["c"], D["a"])),
               "F_direct_ci": ci(safe_ratio(Db["d"], Db["a"])), "F_prompt_ci": ci(safe_ratio(Db["c"], Db["a"])),
               "I": D["a"] - D["c"] - D["d"], "I_ci": ci(Db["a"] - Db["c"] - Db["d"]),
               "F_R": float(safe_ratio(D["e"], D["a"])), "F_R_ci": ci(safe_ratio(Db["e"], Db["a"])),
               "F_spec": float(safe_ratio(D["f"], D["a"])), "F_spec_ci": ci(safe_ratio(Db["f"], Db["a"])),
               "F_direct_p2_5": pct(safe_ratio(Db["d"], Db["a"]), 2.5),
               "F_prompt_p2_5": pct(safe_ratio(Db["c"], Db["a"]), 2.5)}
        # knockout restoration: (L(K on a) - L(a)) / (L(b) - L(a)); D(K) - D(a) = L(K) - L(a) since both minus L(b)
        gap = -D["a"]
        gap_b = -Db["a"]
        ctrl = D["K0b"]
        ctrl_b = Db["K0b"]
        ko = {}
        for k in ("K0", "K1", "K2", "B1", "B2", "B3"):
            raw = safe_ratio(D[k] - D["a"], gap)
            rawb = safe_ratio(Db[k] - Db["a"], gap_b)
            net = safe_ratio(D[k] - D["a"] - ctrl, gap)
            netb = safe_ratio(Db[k] - Db["a"] - ctrl_b, gap_b)
            ko[k] = {"R_raw": float(raw), "R_raw_ci": ci(rawb), "R_net": float(net), "R_net_ci": ci(netb)}
        dk = safe_ratio(Db["K1"] - Db["K2"], gap_b)
        ko["K1_minus_K2"] = {"value": float(safe_ratio(D["K1"] - D["K2"], gap)), "ci": ci(dk)}
        lo, hi = ci(dk)
        ko["veto_timing"] = ("early" if lo > 0 else "late" if hi < 0 else "undetermined")
        ko["generic_damage_K0b"] = {"delta_L": ctrl, "ci": ci(ctrl_b),
                                    "smaller_than_ban_effect": bool(abs(ctrl) < abs(D["a"]))}
        ko["full_knockout_vs_prompt_route"] = {"R_K0_raw": ko["K0"]["R_raw"],
                                               "one_minus_F_prompt": 1 - ent["F_prompt"]}
        ent["knockouts"] = ko
        # placebo: L(pl) - L(b with noun B) over all X programs
        llx = F[t]["ll"]
        pl, bB = [], []
        for wi, w in enumerate(TEMPLATE_IDS):
            v1 = np.array([_arm_ll(llx, "pl", w, u, h) for u, h in zip(A["uids"], A["half"])])[keep] - \
                A[den_key][keep]
            v2 = np.array([_arm_ll(llx, "bB", w, u, h) for u, h in zip(A["uids"], A["half"])])[keep] - \
                A[den_key][keep]
            if np.isfinite(v1).all() and np.isfinite(v2).all():
                pl.append(lme(v1))
                bB.append(lme(v2))
        if pl:
            dpl = float(np.mean(np.array(pl) - np.array(bB)))
            ent["placebo"] = {"D_pl": dpl, "frac_of_D_a": float(abs(dpl) / max(abs(D["a"]), 1e-12)),
                              "passes": bool(abs(dpl) < THRESHOLDS["placebo_max_frac"] * abs(D["a"]))}
        # mention-twin decomposition: prime = mention - neutral, veto = ban - mention
        ent["mention"] = {"prime": D["mention"], "veto": D["a"] - D["mention"],
                          "prime_ci": ci(Db["mention"]), "veto_ci": ci(Db["a"] - Db["mention"])}
        # per-template breakdown and jackknife
        if variant == "primary":
            per_w = {}
            Lw = lme(np.nan_to_num(lw, nan=-1e9), axis=-1)
            Ew = ess_of(np.nan_to_num(lw, nan=-1e9), axis=-1)
            for wi, w in enumerate(TEMPLATE_IDS):
                dd = {c: float(Lw[i, wi] - Lw[ref, wi]) if avail[c] else None for i, c in enumerate(conds)}
                per_w[w] = {"D": dd, "ESS": {c: float(Ew[i, wi]) for i, c in enumerate(conds)},
                            "F_direct": float(safe_ratio(dd["d"], dd["a"])) if dd["a"] else None,
                            "F_prompt": float(safe_ratio(dd["c"], dd["a"])) if dd["a"] else None}
            ent["per_template"] = per_w
            jk = []
            for wi in range(len(TEMPLATE_IDS)):
                mask = [i for i in range(len(TEMPLATE_IDS)) if i != wi]
                pj = d_stats(np.nan_to_num(lw[:, mask], nan=-1e9), ref)
                jk.append({"left_out": TEMPLATE_IDS[wi], "F_direct": float(safe_ratio(pj[conds.index('d')],
                                                                                         pj[0])),
                           "F_prompt": float(safe_ratio(pj[conds.index('c')], pj[0]))})
            ent["template_jackknife"] = jk
            ent["branch"] = decide(ent["F_direct"], ent["F_direct_p2_5"], ent["F_prompt"], ent["F_prompt_p2_5"])
        res["per_task"][t] = ent
    # pooled (ratio of sums over tasks meeting the prerequisite)
    ok = [t for t in res["per_task"] if res["per_task"][t]["prerequisite_met"]]
    res["tasks_in_pool"] = ok
    if ok:
        def pooled(c: str) -> tuple[float, np.ndarray]:
            i = conds.index(c)
            return (sum(res["per_task"][t]["D"][c] for t in ok), sum(boots[t][:, i] for t in ok))

        Da, Dab = pooled("a")
        Dc, Dcb = pooled("c")
        Dd, Ddb = pooled("d")
        res["pooled"] = {
            "D_a": Da, "D_c": Dc, "D_d": Dd,
            "F_direct": float(safe_ratio(Dd, Da)), "F_direct_ci": ci(safe_ratio(Ddb, Dab)),
            "F_direct_p2_5": pct(safe_ratio(Ddb, Dab), 2.5),
            "F_prompt": float(safe_ratio(Dc, Da)), "F_prompt_ci": ci(safe_ratio(Dcb, Dab)),
            "F_prompt_p2_5": pct(safe_ratio(Dcb, Dab), 2.5),
            "I": Da - Dc - Dd, "I_ci": ci(Dab - Dcb - Ddb)}
        pr = res["pooled"]
        pr["branch"] = decide(pr["F_direct"], pr["F_direct_p2_5"], pr["F_prompt"], pr["F_prompt_p2_5"])
        branches = [res["per_task"][t]["branch"]["branch"] for t in ok if res["per_task"][t].get("branch")]
        pr["robust"] = bool(len(ok) == len(TASKS) and len(set(branches)) == 1)
    return res


def decide(f_direct: float, f_direct_lo: float, f_prompt: float, f_prompt_lo: float) -> dict[str, Any]:
    thr, lo = THRESHOLDS["F_confirm"], THRESHOLDS["F_ci_lower"]
    if np.isfinite(f_direct) and f_direct >= thr and f_direct_lo > lo:
        b = "CONFIRMED_direct_route"
    elif np.isfinite(f_prompt) and f_prompt >= thr:
        b = "DECIDED_BEFORE_WRITING_prompt_route"
    else:
        b = "MIXED"
    return {"branch": b, "F_prompt_lower_gt_half": bool(np.isfinite(f_prompt_lo) and f_prompt_lo > lo)}


def survivor_gains(F: dict[str, Any], n_boot: int = 1000) -> dict[str, Any]:
    rng = np.random.default_rng(RNG_SEED + 1)
    out = {}
    for t in TASKS:
        js = [j for j in SURVIVORS[t] if j in F[t]["alg"]]
        if len(js) < 2:
            continue
        G = {c: [] for c in ("a", "c", "d")}
        Gb = {c: [] for c in ("a", "c", "d")}
        ess_rows = {}
        for j in js:
            lw = lw_tensor(F, t, j, ("a", "b", "c", "d"))
            if not np.isfinite(lw).all():
                continue
            P, W = _boot_indices(F[t]["alg"][j]["half"], n_boot, rng, len(TEMPLATE_IDS))
            point = d_stats(lw, 1)
            bs = d_stats(lw, 1, P, W)
            ess_rows[j] = {c: float(np.median(ess_of(lw[i], axis=-1))) for i, c in enumerate(("a", "b", "c", "d"))}
            for i, c in ((0, "a"), (2, "c"), (3, "d")):
                G[c].append(point[i])
                Gb[c].append(bs[:, i])
        if len(G["a"]) < 2:
            continue
        ga, gc, gd = (np.array(G[c]) for c in ("a", "c", "d"))
        gab, gcb, gdb = (np.stack(Gb[c], axis=1) for c in ("a", "c", "d"))

        def cos(u, v, axis=-1):
            return np.sum(u * v, axis=axis) / (np.linalg.norm(u, axis=axis) * np.linalg.norm(v, axis=axis) + 1e-12)

        def cen(u):
            return u - u.mean(axis=-1, keepdims=True)

        out[t] = {"survivors": js, "G_a": ga.tolist(), "G_c": gc.tolist(), "G_d": gd.tolist(),
                  "median_ess": ess_rows,
                  "cos_c_a": float(cos(gc, ga)), "cos_c_a_ci": ci(cos(gcb, gab)),
                  "cos_d_a": float(cos(gd, ga)), "cos_d_a_ci": ci(cos(gdb, gab)),
                  "cos_c_a_centred": float(cos(cen(gc), cen(ga))), "cos_c_a_centred_ci": ci(cos(cen(gcb), cen(gab))),
                  "cos_d_a_centred": float(cos(cen(gd), cen(ga))), "cos_d_a_centred_ci": ci(cos(cen(gdb), cen(gab)))}
    return out


def frlp_cells(F: dict[str, Any]) -> list[dict[str, Any]]:
    """Per-cell FRLP rows {task, model, condition, template, algorithm, L, ess, n_programs, half}."""
    rows = []
    for t in TASKS:
        for j, A in F[t]["alg"].items():
            conds = ("a", "b", "c", "d", "mention") if j != X_KEY[t] else ARMS_X
            lw = lw_tensor(F, t, j, conds)
            for ci_, c in enumerate(conds):
                for wi, w in enumerate(TEMPLATE_IDS):
                    for half in (1, 2, "all"):
                        sel = np.ones(A["n"], bool) if half == "all" else (A["half"] == half)
                        v = lw[ci_, wi, sel]
                        if len(v) == 0 or not np.isfinite(v).all():
                            continue
                        e = float(ess_of(v))
                        rows.append({"task": t, "model": "Qwen/Qwen3-8B", "condition": c, "template": w,
                                     "algorithm": j, "L": float(lme(v)), "ess": e, "ess_flag": e < THRESHOLDS["ess_flag"],
                                     "n_programs": int(sel.sum()), "half": str(half)})
    return rows


# ================================================================================================ behaviour
def behaviour(samples: list[dict[str, Any]], floor: float | None, n_boot: int = 2000) -> dict[str, Any]:
    rng = np.random.default_rng(RNG_SEED + 2)
    out: dict[str, Any] = {"crn_self_agreement_floor": floor, "per_task": {}}
    for t in TASKS:
        S = [s for s in samples if s["task"] == t]
        x = X_KEY[t]
        ent: dict[str, Any] = {}
        for arm in ("a", "b", "c", "d", "K1", "K2"):
            A = [s for s in S if s["condition"] == arm]
            if not A:
                continue
            n = len(A)
            k = sum(s["label"] == x for s in A)
            att = [s for s in A if s["label"] != "no_code"]
            nonb = [s for s in att if s["label"] != x]
            comp = sum(1 for s in A if s["passed"] and s["label"] != x)
            gate = (1 - k / n >= THRESHOLDS["gate_avoidance"]) and len(nonb) >= THRESHOLDS["gate_min_nonbanned"]
            ent[arm] = {"n": n, "banned": k, "banned_share": k / n, "banned_ci": wilson_ci(k, n),
                        "avoidance": 1 - k / n, "n_attempted": len(att), "n_attempted_nonbanned": len(nonb),
                        "compliant_share": comp / n, "pass_rate": sum(s["passed"] for s in A) / n,
                        "gate_passed": bool(gate),
                        "landing": dict(Counter(s["label"] for s in att)) if gate else None,
                        "label_distribution": dict(Counter(s["label"] for s in A)),
                        "per_template": {w: {"n": sum(1 for s in A if s["template"] == w),
                                             "banned": sum(1 for s in A if s["template"] == w and s["label"] == x)}
                                         for w in TEMPLATE_IDS}}
        # matched (CRN) pairs keyed by (template, sample_id)
        key = {arm: {(s["template"], s["sample_id"]): s for s in S if s["condition"] == arm} for arm in ent}
        flips = {}
        for a1, a2 in (("a", "b"), ("c", "b"), ("d", "b"), ("c", "d"), ("K1", "a"), ("K2", "a")):
            if a1 not in key or a2 not in key:
                continue
            common = sorted(set(key[a1]) & set(key[a2]))
            tab = Counter((key[a1][k_]["label"] == x, key[a2][k_]["label"] == x) for k_ in common)
            n10, n01 = tab[(True, False)], tab[(False, True)]
            p = stats.binomtest(n10, n10 + n01, 0.5).pvalue if n10 + n01 > 0 else 1.0
            same_seq = sum(key[a1][k_]["code_sha256"] == key[a2][k_]["code_sha256"] for k_ in common)
            flips[f"{a1}_vs_{a2}"] = {"n_pairs": len(common), "both_banned": tab[(True, True)],
                                      f"{a1}_banned_only": n10, f"{a2}_banned_only": n01,
                                      "neither": tab[(False, False)], "mcnemar_exact_p": float(p),
                                      "identical_code_share": same_seq / max(1, len(common))}
        ent["matched_flips"] = flips
        # behavioural route fraction with a paired (CRN) bootstrap over (template, sample) units
        if all(a in key for a in ("a", "b", "c", "d")):
            units = sorted(set(key["a"]) & set(key["b"]) & set(key["c"]) & set(key["d"]))
            Y = np.array([[key[a][u]["label"] == x for a in ("a", "b", "c", "d")] for u in units], dtype=float)
            sh = Y.mean(0)
            fb = safe_ratio(sh[1] - sh[3], sh[1] - sh[0])
            fp_ = safe_ratio(sh[1] - sh[2], sh[1] - sh[0])
            idx = rng.integers(0, len(units), size=(n_boot, len(units)))
            shb = Y[idx].mean(1)
            ent["F_direct_beh"] = float(fb)
            ent["F_direct_beh_ci"] = ci(safe_ratio(shb[:, 1] - shb[:, 3], shb[:, 1] - shb[:, 0]))
            ent["F_prompt_beh"] = float(fp_)
            ent["F_prompt_beh_ci"] = ci(safe_ratio(shb[:, 1] - shb[:, 2], shb[:, 1] - shb[:, 0]))
            ent["share_diff_b_minus_a"] = float(sh[1] - sh[0])
            ent["share_diff_b_minus_a_ci"] = ci(shb[:, 1] - shb[:, 0])
        out["per_task"][t] = ent
    return out


# ================================================================================================ token localisation
def _signature_mask(tok: Any, text: str, ids: list[int], vocab: list[str]) -> np.ndarray:
    """Tokens whose character span overlaps an occurrence of a vocabulary word in the scored text."""
    words = [w.rstrip("()") if w != "range(n - 1)" else "range(n - 1)" for w in vocab]
    spans = []
    for w in words:
        for m in re.finditer(re.escape(w), text):
            spans.append((m.start(), m.end()))
    enc = tok(text, add_special_tokens=False, return_offsets_mapping=True)
    offs = enc["offset_mapping"]
    mask = np.zeros(len(ids), dtype=bool)
    if enc["input_ids"] != ids[:len(enc["input_ids"])]:
        return mask
    for i, (s, e) in enumerate(offs):
        mask[i] = any(s < b and e > a for a, b in spans)
    return mask


def _load_token_lp() -> dict[tuple[str, str, str, str], dict[str, np.ndarray]]:
    """(task, condition, template, half_tag) -> uid -> per-token log-probs."""
    out: dict[tuple[str, str, str, str], dict[str, np.ndarray]] = defaultdict(dict)
    for f in sorted(TOKEN_LP_DIR.glob("*.npz")):
        base = f.name.rsplit("__", 1)[0]
        parts = base.split("_")
        t, half = parts[0], parts[-1]
        w = parts[-2]
        cond = "_".join(parts[1:-2])
        z = np.load(f)
        offs = z["offsets"]
        for i, u in enumerate(z["uids"]):
            out[(t, cond, w, half)][str(u)] = z["lp"][offs[i]:offs[i + 1]]
    return out


def token_localisation(tok: Any) -> dict[str, Any]:
    progs = {f"{p['task']}:{p['algorithm']}:{p['prog_index']}": p for p in read_jsonl(DATA_DIR / "frlp_programs.jsonl")}
    TL = _load_token_lp()
    out = {}
    for t in TASKS:
        x = X_KEY[t]
        vocab = SIGNATURE_VOCAB[x]
        xs = [u for u, p in progs.items() if p["task"] == t and p["algorithm"] == x]
        masks = {u: _signature_mask(tok, progs[u]["scored_text"], progs[u]["score_ids"], vocab) for u in xs}
        ent = {}
        for arm in ("a", "c", "d", "K1", "K2", "K0"):
            tot = sig = first16 = 0.0
            ntok = nsig = 0
            per_prog_share = []
            for w in TEMPLATE_IDS:
                for u in xs:
                    h = progs[u]["half"]
                    half_tag = str(h)
                    ref = TL.get((t, "b", w, half_tag), {}).get(u)
                    src = (TL.get((t, arm, w, "all"), {}).get(u) if arm in ("a", "K1", "K2", "K0")
                           else TL.get((t, arm, w, half_tag), {}).get(u))
                    if ref is None or src is None or len(ref) != len(src):
                        continue
                    dlt = src.astype(np.float64) - ref.astype(np.float64)
                    m = masks[u][:len(dlt)]
                    tot += dlt.sum()
                    sig += dlt[m].sum()
                    first16 += dlt[:KO_WINDOW].sum()
                    ntok += len(dlt)
                    nsig += int(m.sum())
                    if abs(dlt.sum()) > 1e-6:
                        per_prog_share.append(dlt[m].sum() / dlt.sum())
            if ntok == 0:
                continue
            share = sig / tot if abs(tot) > 1e-12 else float("nan")
            tshare = nsig / ntok
            ent[arm] = {"sum_delta": tot, "signature_share_of_delta": share, "signature_share_of_tokens": tshare,
                        "enrichment": share / tshare if tshare > 0 else float("nan"),
                        "first16_share_of_delta": first16 / tot if abs(tot) > 1e-12 else float("nan"),
                        "median_per_program_signature_share": float(np.median(per_prog_share)) if per_prog_share else None,
                        "n_tokens": ntok, "n_signature_tokens": nsig}
        out[t] = ent
    return out


# ================================================================================================ coverage
def _shingles(code: str, n: int = 4) -> set[tuple[str, ...]]:
    """Identifier-normalised AST n-gram shingles: node-type sequence of a pre-order walk (names dropped)."""
    import ast

    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return set()
    seq: list[str] = []

    def walk(node: ast.AST) -> None:
        seq.append(type(node).__name__)
        for ch in ast.iter_child_nodes(node):
            walk(ch)

    walk(tree)
    return {tuple(seq[i:i + n]) for i in range(len(seq) - n + 1)}


def coverage(samples: list[dict[str, Any]]) -> dict[str, Any]:
    """Per algorithm: mean over natural S4 programs (arms a, b) with that label of their max Jaccard to the forced
    programs, next to the forced-vs-forced reference level."""
    progs = read_jsonl(DATA_DIR / "frlp_programs.jsonl")
    out: dict[str, Any] = {}
    for t in TASKS:
        for j in ALGOS[t]:
            forced = [_shingles(p["scrubbed_code"] or p["orig_code"]) for p in progs
                      if p["task"] == t and p["algorithm"] == j]
            forced = [f for f in forced if f]
            nat = [_shingles(s["code"]) for s in samples
                   if s["task"] == t and s["condition"] in ("a", "b") and s["label"] == j and s.get("code")]
            nat = [x for x in nat if x]
            if not forced:
                continue

            def jac(a: set, b: set) -> float:
                return len(a & b) / max(1, len(a | b))

            ref = [max(jac(f, g) for k, g in enumerate(forced) if k != i) for i, f in enumerate(forced)] \
                if len(forced) > 1 else []
            out[f"{t}:{j}"] = {"n_forced": len(forced), "n_natural": len(nat),
                               "natural_max_jaccard_mean": float(np.mean([max(jac(x, f) for f in forced) for x in nat]))
                               if nat else None,
                               "forced_vs_forced_max_jaccard_mean": float(np.mean(ref)) if ref else None}
    return out


# ================================================================================================ C5 statistics
def spearman(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 3 or np.std(x) == 0 or np.std(y) == 0:
        return float("nan")
    return float(stats.spearmanr(x, y).statistic)


def fisher_combine(rhos: list[float], ns: list[int]) -> float:
    z, wsum = 0.0, 0.0
    for r, n in zip(rhos, ns):
        if not np.isfinite(r) or n <= 3:
            continue
        r = float(np.clip(r, -0.999999, 0.999999))
        z += (n - 3) * np.arctanh(r)
        wsum += n - 3
    return float(np.tanh(z / wsum)) if wsum > 0 else float("nan")


def _centred_ranks(v: np.ndarray, axis: int = -1) -> np.ndarray:
    r = stats.rankdata(v, axis=axis)
    return r - r.mean(axis=axis, keepdims=True)


def c5_test(pi: np.ndarray, share: np.ndarray, cells: list[Any], n_perm: int = N_PERM_C5,
            n_boot: int = 2000, seed: int = RNG_SEED + 3) -> dict[str, Any]:
    """Combined within-cell Spearman (Fisher z, weights n-3), one-sided stratified permutation p (H1: rho < 0),
    bootstrap CI resampling wordings within cells. Vectorised: Spearman = Pearson of centred average ranks."""
    rng = np.random.default_rng(seed)
    pi = np.asarray(pi, dtype=float)
    share = np.asarray(share, dtype=float)
    cells = np.asarray(cells)
    groups = [np.where(cells == c)[0] for c in sorted(set(cells.tolist()))]
    ns = [len(g) for g in groups]
    obs_r, perm_r, boot_r = [], [], []
    for g in groups:
        rx, ry = _centred_ranks(pi[g]), _centred_ranks(share[g])
        den = np.linalg.norm(rx) * np.linalg.norm(ry)
        if den == 0 or len(g) < 3:
            obs_r.append(np.nan)
            perm_r.append(np.full(n_perm, np.nan))
            boot_r.append(np.full(n_boot, np.nan))
            continue
        obs_r.append(float(rx @ ry / den))
        perms = np.argsort(rng.random((n_perm, len(g))), axis=1)
        perm_r.append(ry[perms] @ rx / den)
        bi = rng.integers(0, len(g), size=(n_boot, len(g)))
        bx, by = _centred_ranks(pi[g][bi], axis=1), _centred_ranks(share[g][bi], axis=1)
        bden = np.linalg.norm(bx, axis=1) * np.linalg.norm(by, axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            boot_r.append(np.where(bden > 0, np.sum(bx * by, axis=1) / bden, np.nan))

    def combine(R: list[np.ndarray]) -> np.ndarray:
        num = np.zeros_like(np.asarray(R[0], dtype=float))
        wsum = np.zeros_like(num)
        for r, n in zip(R, ns):
            r = np.asarray(r, dtype=float)
            ok = np.isfinite(r) & (n > 3)
            num = num + np.where(ok, (n - 3) * np.arctanh(np.clip(np.nan_to_num(r), -0.999999, 0.999999)), 0.0)
            wsum = wsum + np.where(ok, n - 3, 0.0)
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where(wsum > 0, np.tanh(num / np.where(wsum > 0, wsum, 1)), np.nan)

    obs = float(combine([np.array(r) for r in obs_r]))
    perm = combine(perm_r)
    boot = combine(boot_r)
    pv = float((1 + np.sum(perm <= obs)) / (1 + n_perm)) if np.isfinite(obs) else float("nan")
    return {"rho": obs, "p_one_sided": pv, "ci": ci(boot), "per_cell_rho": [float(r) for r in obs_r],
            "per_cell_n": ns, "perm_null_mean": float(np.nanmean(perm)), "perm_null_2_5": pct(perm, 2.5)}


def c5_decision(rho: float, p: float) -> str:
    if np.isfinite(rho) and rho <= THRESHOLDS["c5_rho"] and p < THRESHOLDS["c5_alpha"]:
        return "CONFIRMED"
    if np.isfinite(rho) and rho < 0 and p < THRESHOLDS["c5_alpha"]:
        return "PARTIAL"
    return "NULL"


def holm(pvals: dict[str, float]) -> dict[str, float]:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    out, running = {}, 0.0
    for i, (k, p) in enumerate(items):
        adj = min(1.0, (m - i) * p)
        running = max(running, adj)
        out[k] = running
    return out


def split_half_ceiling(labels_by_wording: list[np.ndarray], cells: list[Any], n_rep: int = 1000,
                       seed: int = RNG_SEED + 4) -> dict[str, Any]:
    """Per cell: split-half reliability of per-wording banned share (Spearman across wordings between the two
    halves, Spearman-Brown corrected), averaged over random halvings; ceiling = sqrt(reliability)."""
    rng = np.random.default_rng(seed)
    cells = np.asarray(cells)
    out = {}
    for c in sorted(set(cells.tolist())):
        g = np.where(cells == c)[0]
        rs = []
        for _ in range(n_rep):
            h1, h2 = [], []
            for i in g:
                y = labels_by_wording[i]
                perm = rng.permutation(len(y))
                k = len(y) // 2
                h1.append(y[perm[:k]].mean() if k else np.nan)
                h2.append(y[perm[k:2 * k]].mean() if k else np.nan)
            r = spearman(np.array(h1), np.array(h2))
            if np.isfinite(r):
                rs.append(r)
        r = float(np.mean(rs)) if rs else float("nan")
        rel = 2 * r / (1 + r) if np.isfinite(r) and r > -1 else float("nan")
        out[str(c)] = {"split_half_r": r, "reliability": rel,
                       "ceiling_abs_rho": float(math.sqrt(rel)) if np.isfinite(rel) and rel > 0 else 0.0}
    vals = [v["ceiling_abs_rho"] for v in out.values()]
    return {"per_cell": out, "mean_ceiling": float(np.mean(vals)) if vals else float("nan")}


def veto_layer(lnr_ban: np.ndarray, lnr_neu: np.ndarray, thr: float = THRESHOLDS["veto_log_rank"]) -> int | None:
    """First layer l such that ln rank_ban(l') - ln rank_neu(l') >= thr for every l' >= l (None if never)."""
    d = np.asarray(lnr_ban) - np.asarray(lnr_neu)
    ok = d >= thr
    for l in range(len(d)):
        if ok[l:].all():
            return l
    return None


# ================================================================================================ U9 synthetic checks
def synthetic_checks() -> dict[str, Any]:
    rng = np.random.default_rng(7)
    conds = 4  # a, b, c, d
    M, Wn = 30, 5
    base = rng.normal(-5, 1.0, size=(Wn, M))
    lw = np.empty((conds, Wn, M))
    lw[1] = base                      # b
    lw[0] = base - 2.0 + rng.normal(0, 0.3, size=(Wn, M))   # a: ban effect -2
    lw[3] = base - 1.6 + rng.normal(0, 0.3, size=(Wn, M))   # d: 0.8 of the effect
    lw[2] = base - 0.4 + rng.normal(0, 0.3, size=(Wn, M))   # c
    halves = np.array([1, 2] * (M // 2))
    P, W = _boot_indices(halves, 1000, rng, Wn)
    pt = d_stats(lw, 1)
    bs = d_stats(lw, 1, P, W)
    f = float(pt[3] / pt[0])
    fci = ci(bs[:, 3] / bs[:, 0])
    # C5 planted correlation -0.6 and size check
    cells = np.repeat(np.arange(10), 10)
    z = rng.normal(size=100)
    share = np.clip(0.5 - 0.6 * 0.2 * z + rng.normal(0, 0.16, 100), 0, 1)
    planted = c5_test(z, share, cells.tolist(), n_perm=2000, n_boot=200)
    rej = 0
    for k in range(200):
        s2 = rng.permutation(share)
        r = c5_test(rng.normal(size=100), s2, cells.tolist(), n_perm=200, n_boot=2, seed=k)
        rej += r["p_one_sided"] < 0.05
    return {"F_direct_true": 0.8, "F_direct_hat": f, "F_direct_ci": fci, "recovered": bool(fci[0] <= 0.8 <= fci[1]),
            "c5_planted_rho": planted["rho"], "c5_planted_p": planted["p_one_sided"],
            "c5_planted_detected": bool(planted["p_one_sided"] < 0.05 and planted["rho"] < 0),
            "c5_size_rejections_of_200": int(rej), "c5_size_ok": bool(rej <= 20)}


# ================================================================================================ stage
def stage_analysis() -> dict[str, Any]:
    from transformers import AutoTokenizer

    from cfg import model_path

    out: dict[str, Any] = {}
    F = load_frlp()
    out["route_frlp"] = route_analysis(F)
    out["sensitivities"] = {v: route_analysis(F, n_boot=500, variant=v)
                            for v in ("correct_only", "gen_paraphrase", "no_ess_weight", "mean_ll")}
    out["survivor_gains"] = survivor_gains(F)
    cells = frlp_cells(F)
    from cfg import write_jsonl

    write_jsonl(DATA_DIR / "frlp_cells.jsonl", cells)
    out["frlp_cells_summary"] = {"n_cells": len(cells),
                                 "n_ess_flagged": sum(c["ess_flag"] for c in cells),
                                 "ess_flagged_by_algorithm": dict(Counter(c["algorithm"] for c in cells
                                                                          if c["ess_flag"]))}
    tests = json.loads((RESULTS_DIR / "tests.json").read_text()) if (RESULTS_DIR / "tests.json").exists() else {}
    floor = tests.get("U5", {}).get("self_agreement_identical_share")
    samples = read_jsonl(DATA_DIR / "samples.jsonl")
    out["behaviour"] = behaviour(samples, floor) if samples else None
    out["coverage_shingles"] = coverage(samples) if samples else None
    tok = AutoTokenizer.from_pretrained(model_path())
    out["token_localisation"] = token_localisation(tok)
    for name in ("lens", "c5", "coverage"):
        p = RESULTS_DIR / f"{name}.json"
        out[name] = json.loads(p.read_text()) if p.exists() else None
    if out["c5"]:
        c5 = out["c5"]
        pv = {k: c5[k]["test"]["p_one_sided"] for k in ("shared_ban_direction", "decommitment_axis")
              if c5.get(k) and c5[k].get("test")}
        adj = holm(pv)
        for k in pv:
            c5[k]["holm_p"] = adj[k]
            c5[k]["decision"] = c5_decision(c5[k]["test"]["rho"], c5[k]["test"]["p_one_sided"])
            c5[k]["decision_holm"] = c5_decision(c5[k]["test"]["rho"], adj[k])
    out["raw_p_values_for_cross_artifact_holm"] = {
        "C2_route": {t: out["route_frlp"]["per_task"].get(t, {}).get("D_ci") for t in TASKS},
        "C5": {k: v["test"]["p_one_sided"] for k, v in (out["c5"] or {}).items()
               if isinstance(v, dict) and v.get("test")}}
    write_json(RESULTS_DIR / "analysis.json", out)
    rp = out["route_frlp"]
    logger.info(f"route: pooled={rp.get('pooled')}")
    for t, e in rp["per_task"].items():
        logger.info(f"{t}: D={ {k: round(v, 3) for k, v in e['D'].items() if v == v} } F_direct={e['F_direct']:.3f} "
                    f"F_prompt={e['F_prompt']:.3f} branch={e.get('branch')}")
    return out


if __name__ == "__main__":
    from cfg import setup_logging

    setup_logging("analysis")
    stage_analysis()
