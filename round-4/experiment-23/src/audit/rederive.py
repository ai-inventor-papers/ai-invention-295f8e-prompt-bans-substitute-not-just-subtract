#!/usr/bin/env python3
"""Independent re-derivation of the headline numbers (no import from src/; its own code path).

Reads only raw per-sample rows (data/samples.jsonl), the pre-ban commitment (predictions/commit_preban.json: D,
survivors and the committed forecast distributions) and the post-hoc judge cache (data/judge_cache_paths_posthoc.jsonl).
Recomputes E_t (escape rule from the escape rows), A_t, BA, Fisher, Spearman, Kendall, the rival Spearmans, the C3b log
scores and the post-hoc T2 relabel, and compares them with results/*.json. Placebos: the same Fisher and Spearman tests on
shuffled task outcomes, on a random predictor and on a constant predictor must FAIL (reject at about the nominal 5% or
less). Writes results/rederive.json.
"""

from __future__ import annotations

import collections
import json
import math
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
BAD = ("invalid", "disputed")


def jl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def rj(name: str) -> dict:
    return json.loads((ROOT / "results" / name).read_text())


def off(rows: list[dict], D: str) -> float:
    return sum(r["label"] not in (D,) + BAD for r in rows) / len(rows)


def passr(rows: list[dict]) -> float:
    return sum(bool(r["passed"]) for r in rows) / len(rows)


def escape_E(S: list[dict], t: str, D: str) -> float:
    tw = [r for r in S if r["task"] == t and r["stage"] == "A" and r["arm"] == "twin"]
    p0, pt = off(tw, D), passr(tw)
    n_conf = collections.Counter()
    for seed in range(9001, 9009):
        for a in (1, 2):
            arm = f"esc{seed}_a{a}"
            s1 = [r for r in S if r["task"] == t and r["stage"] == "A" and r["arm"] == arm]
            if not s1 or off(s1, D) - p0 < 0.2 or passr(s1) < 0.8 * pt:
                continue
            rr = s1 + [r for r in S if r["task"] == t and r["stage"] == "B" and r["arm"] == arm]
            k = sum(r["label"] not in (D,) + BAD for r in rr)
            if (len(rr) >= 30 and k / len(rr) - p0 >= 0.2 and passr(rr) >= 0.8 * pt
                    and stats.binom.sf(k - 1, len(rr), max(p0, 0.01)) < 0.05):
                n_conf[a] += 1
    return max(n_conf[1], n_conf[2]) / 8


def ba_fisher(pred: np.ndarray, obs: np.ndarray) -> tuple[float | None, float]:
    if obs.min() == obs.max():
        return None, 1.0
    ba = ((pred[obs == 1] == 1).mean() + (pred[obs == 0] == 0).mean()) / 2
    tab = [[int(((pred == 1) & (obs == 1)).sum()), int(((pred == 1) & (obs == 0)).sum())],
           [int(((pred == 0) & (obs == 1)).sum()), int(((pred == 0) & (obs == 0)).sum())]]
    p = 1.0 if pred.min() == pred.max() else float(stats.fisher_exact(tab).pvalue)
    return float(ba), p


def perm_p(x: np.ndarray, y: np.ndarray, n: int = 20000, seed: int = 1) -> tuple[float | None, float | None]:
    """Spearman rho and one-sided permutation p, via my own rank-correlation loop."""
    if np.std(x) == 0 or np.std(y) == 0:
        return None, None
    rx, ry = stats.rankdata(x), stats.rankdata(y)
    rho = float(np.corrcoef(rx, ry)[0, 1])
    rng = np.random.default_rng(seed)
    hits = sum(np.corrcoef(rx, ry[rng.permutation(len(ry))])[0, 1] >= rho - 1e-12 for _ in range(n))
    return rho, (hits + 1) / (n + 1)


def main() -> None:
    S = jl(ROOT / "data" / "samples.jsonl")
    pre = json.loads((ROOT / "predictions" / "commit_preban.json").read_text())
    c3a = rj("c3a.json")["primary"]
    tasks = c3a["tasks"]
    out: dict = {"mismatches": []}

    def check(name: str, mine, ref, tol: float = 1e-9) -> None:
        bad = (mine is None) != (ref is None) or (mine is not None and abs(mine - ref) > tol)
        if bad:
            out["mismatches"].append(f"{name}: rederived {mine} vs reported {ref}")

    E = {t: escape_E(S, t, pre["tasks"][t]["D"]) for t in tasks}
    A = {}
    for t in tasks:
        bans = [r for r in S if r["task"] == t and r["stage"] == "BAN" and r["arm"] == "ban"]
        A[t] = sum(r["label"] in set(pre["tasks"][t]["survivors"]) for r in bans) / len(bans)
        check(f"E_t[{t}]", E[t], pre["tasks"][t]["E_t"])
        check(f"A_t[{t}]", A[t], c3a["A_t"][t])
    e = np.array([E[t] for t in tasks])
    a = np.array([A[t] for t in tasks])
    pred, obs = (e > 0).astype(int), (a >= 0.5).astype(int)
    ba, fp = ba_fisher(pred, obs)
    rho, rho_p = perm_p(e, a)
    tau = float(stats.kendalltau(e, a, variant="b").statistic)
    check("BA", ba, c3a["balanced_accuracy"]["BA"])
    check("Fisher p (two-sided)", fp, c3a["fisher"]["p_two_sided"])
    check("Spearman rho", rho, c3a["spearman"]["rho"])
    check("Spearman one-sided perm p", rho_p, c3a["spearman"]["p_one_sided"], tol=0.01)
    check("Kendall tau-b", tau, c3a["kendall_tau_b"])
    out["headline"] = {"BA": ba, "fisher_p": fp, "rho": rho, "rho_p_one_sided": rho_p, "kendall_tau_b": tau,
                       "E_t": E, "A_t": A}
    # rivals from raw rows (sign-oriented Spearman with A_t)
    rv = rj("rivals.json")
    for name, stage, arm, sign in (("novelty_off", "C", "novelty", 1), ("pn_a1_off", "A", "pn_a1", 1),
                                   ("pn_a2_off", "A", "pn_a2", 1), ("t13_off", "A", "t13", 1)):
        x = np.array([off([r for r in S if r["task"] == t and r["stage"] == stage and r["arm"] == arm],
                          pre["tasks"][t]["D"]) for t in tasks])
        r_ = float(stats.spearmanr(sign * x, a).statistic)
        check(f"rival rho {name}", r_, rv[name]["rho_rival_sign_oriented"])
        out.setdefault("rivals", {})[name] = r_
    tms = []
    for t in tasks:
        c = collections.Counter(r["label"] for r in S if r["task"] == t and r["stage"] == "A" and r["arm"] == "twin")
        tms.append(max(c.values()) / sum(c.values()))
    r_ = float(stats.spearmanr(-np.array(tms), a).statistic)
    check("rival rho twin_modal_share", r_, rv["twin_modal_share"]["rho_rival_sign_oriented"])
    out["rivals"]["twin_modal_share"] = r_
    # C3b log scores on the gated events, from the committed distributions and the raw ban labels
    c3b = rj("c3b.json")
    for t, ev in c3b.get("per_event", {}).items():
        D, Sv = pre["tasks"][t]["D"], pre["tasks"][t]["survivors"]
        labs = [r["label"] for r in S if r["task"] == t and r["stage"] == "BAN" and r["arm"] == "ban"
                and r["label"] not in (D,) + BAD]
        for nm in ("push_landing", "opening_ladder", "association", "proximity"):
            f = pre["tasks"][t]["forecasts"][nm]
            dist = f["distribution"] if f.get("defined") else {m: 1 / len(Sv) for m in Sv}
            q = {m: 0.93 * dist.get(m, 0.0) + 0.05 / len(Sv) for m in Sv}
            ls = float(np.mean([math.log(q.get(l, 0.02) if l in Sv else 0.02) for l in labs]))
            check(f"C3b {t}/{nm}", ls, ev[nm]["log_score"])
    # post-hoc T2 relabel straight from the judge cache (join on code sha256)
    cache = {r["key"].split("|")[-1]: r["label"] for r in jl(ROOT / "data" / "judge_cache_paths_posthoc.jsonl")}
    S2 = [({**r, "label": cache.get(r["code_sha256"], r["label"])} if (r["task"] == "T2" and r["label"] == "bf_spfa")
           else r) for r in S]
    E2, A2 = dict(E), dict(A)
    E2["T2"] = escape_E(S2, "T2", pre["tasks"]["T2"]["D"])
    b2 = [r for r in S2 if r["task"] == "T2" and r["stage"] == "BAN" and r["arm"] == "ban"]
    A2["T2"] = sum(r["label"] in set(pre["tasks"]["T2"]["survivors"]) for r in b2) / len(b2)
    e2, a2 = np.array([E2[t] for t in tasks]), np.array([A2[t] for t in tasks])
    ba2, fp2 = ba_fisher((e2 > 0).astype(int), (a2 >= 0.5).astype(int))
    rho2 = float(stats.spearmanr(e2, a2).statistic)
    ph = rj("posthoc_t2_relabel.json")["variants"]["judge"]
    for nm, mine, ref in (("posthoc T2 A_t", A2["T2"], ph["T2_A_t"]), ("posthoc T2 E_t", E2["T2"], ph["T2_E_t"]),
                          ("posthoc BA", ba2, ph["BA"]), ("posthoc Fisher p", fp2, ph["fisher_p"]),
                          ("posthoc rho", rho2, ph["rho"])):
        check(nm, mine, ref)
    out["posthoc_judge"] = {"T2_A_t": A2["T2"], "T2_E_t": E2["T2"], "BA": ba2, "fisher_p": fp2, "rho": rho2}
    # placebos: the same tests must fail on shuffled outcomes, a random predictor and a constant predictor
    rng = np.random.default_rng(7)
    rej_f, rej_s, rhos = 0, 0, []
    n_sh = 1000
    for _ in range(n_sh):
        ash = a[rng.permutation(len(a))]
        _, pf = ba_fisher(pred, (ash >= 0.5).astype(int))
        rej_f += pf < 0.05
        r_, p_ = perm_p(e, ash, n=300, seed=int(rng.integers(1e9)))
        rhos.append(r_)
        rej_s += (p_ is not None and p_ < 0.05)
    rand_rej = 0
    for _ in range(300):
        er = rng.random(len(a))
        r_, p_ = perm_p(er, a, n=300, seed=int(rng.integers(1e9)))
        rand_rej += p_ < 0.05
    ba_c, fp_c = ba_fisher(np.ones(len(a), int), obs)
    out["placebos"] = {
        "shuffled_outcomes": {"n": n_sh, "fisher_reject_rate": rej_f / n_sh, "spearman_reject_rate": rej_s / n_sh,
                              "mean_rho": float(np.mean(rhos))},
        "random_predictor": {"n": 300, "spearman_reject_rate": rand_rej / 300},
        "constant_predictor_all_movable": {"BA": ba_c, "fisher_p": fp_c},
        "fail_as_required": bool(rej_f / n_sh <= 0.06 and rej_s / n_sh <= 0.07 and rand_rej / 300 <= 0.08
                                 and ba_c == 0.5 and fp_c == 1.0)}
    out["n_mismatches"] = len(out["mismatches"])
    (ROOT / "results" / "rederive.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: v for k, v in out.items() if k not in ("headline",)}, default=float)[:2000])


if __name__ == "__main__":
    main()
