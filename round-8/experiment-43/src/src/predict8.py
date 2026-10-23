#!/usr/bin/env python3
"""predict8: iteration-7 predict.py (committed cell_prediction / fork_mix / seq_logprob, imported unchanged) plus ONE
composition level (a second decision token inside a first-decision branch), the committed baselines and the scoring
metric. Pure numpy; GPU-side teacher forcing reduces the logits to the compact inputs below.

The law (per template w, sampler kappa, temperature T):
  pi_{T,kappa}(t | prefix) = softmax(z / T) over all tokens, or renormalised over the 10 largest logits (top-k 10)
  w_T(O)        = prod_i pi_T(o_i | prefix, o_<i)
  G_T(t1, A)    = Phat(A | t1)                                                     (no second decision), else
                  w_T(O2 | t1) * [sum_{t2 in top10} pi_T(t2 | ..O2) Phat(A | t1, t2) + r2_T Phat(A | t1, resid2)]
                  + (1 - w_T(O2 | t1)) * Phat_off(A | t1)
  F_T(c, A)     = sum_{t1 in top20} pi_T(t1 | O_c) G_T(t1, A) + r_T(c) * Phat(A | resid_c)
  P_T(A | w)    = sum_c w_T(O_c) F_T(c, A) + (1 - sum_c w_T(O_c)) q_rest(A)
  cell(T, kappa) = mean over the 5 templates.
Baselines: B0 flat (fit-twin shares q at every T); B1 algorithm-level tempering q^(1/T) renormalised; B2 the
single-decision law (G_T(t1, A) = Phat(A | t1)); BH the same law at entropy-located positions.
Score: MAE_u = mean over temperatures of TVD(predicted, observed) over all label bins.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

import predict as P7
import replay

dist = replay.dist
seq_logprob = P7.seq_logprob


def tvd(p: np.ndarray, q: np.ndarray) -> float:
    return 0.5 * float(np.abs(np.asarray(p, float) - np.asarray(q, float)).sum())


def entropy_bits(p: np.ndarray) -> float:
    p = np.asarray(p, dtype=float)
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum()) if len(p) else 0.0


# ------------------------------------------------------------------------------------------------ the law
def g_value(t1: int, op: dict[str, Any], tw: dict[str, Any], key: str, single: bool) -> np.ndarray:
    """G_T(t1, .) for one first-decision token. op: committed opening (Phat tables); tw: this template's compact
    teacher-forced quantities at (T, kappa) = key."""
    ph = np.asarray(op["phat"][str(t1)], dtype=float)
    sec = op.get("second", {}).get(str(t1))
    if single or not sec or not sec.get("found", True):
        return ph
    st = tw["second"][str(t1)][key]
    w2 = math.exp(st["lp_O2"]) if st["lp_O2"] > -math.inf else 0.0
    inner = np.zeros_like(ph)
    for t2, p2 in zip(sec["tokens2"], st["p_top2"]):
        inner += p2 * np.asarray(sec["phat2"][str(t2)], dtype=float)
    inner += st["resid2"] * np.asarray(sec["resid2_phat"], dtype=float)
    return w2 * inner + (1.0 - w2) * np.asarray(sec["phat_off"], dtype=float)


def template_prediction(law: dict[str, Any], tf: dict[str, Any], key: str, single: bool = False) -> dict[str, Any]:
    """law: committed openings + q_rest; tf: {opening_id: compact TF quantities for ONE template}."""
    q_rest = np.asarray(law["q_rest"], dtype=float)
    tot = np.zeros_like(q_rest)
    w_sum = 0.0
    parts = []
    for op in law["openings"]:
        tw = tf[op["id"]]
        k = tw[key]
        w = math.exp(k["lp_open"]) if k["lp_open"] > -math.inf else 0.0
        F = np.zeros_like(q_rest)
        for t1, p1 in zip(op["tokens"], k["p_top"]):
            F += p1 * g_value(t1, op, tw, key, single)
        F += k["resid"] * np.asarray(op["resid_phat"], dtype=float)
        tot += w * F
        w_sum += w
        parts.append({"id": op["id"], "w": w, "residual_mass": k["resid"]})
    w_sum = min(w_sum, 1.0)
    tot += (1.0 - w_sum) * q_rest
    s = tot.sum()
    return {"P": tot / s if s > 0 else tot, "on_opening": w_sum, "parts": parts}


def cell_prediction(law: dict[str, Any], tf_by_w: dict[str, dict[str, Any]], T: float, sampler: str,
                    single: bool = False) -> dict[str, Any]:
    key = f"{sampler}|{T}"
    per = {w: template_prediction(law, tf, key, single) for w, tf in tf_by_w.items()}
    P = np.mean([v["P"] for v in per.values()], axis=0)
    on = float(np.mean([v["on_opening"] for v in per.values()]))
    return {"P": P, "on_opening": on, "by_template": {w: v["P"].tolist() for w, v in per.items()}}


def b0(q: np.ndarray, T: float) -> np.ndarray:
    return np.asarray(q, dtype=float)


def b1(q: np.ndarray, T: float) -> np.ndarray:
    q = np.asarray(q, dtype=float)
    x = np.where(q > 0, np.power(np.clip(q, 1e-300, None), 1.0 / T), 0.0)
    return x / x.sum()


def mae(pred: dict[float, np.ndarray], obs: dict[float, np.ndarray]) -> float:
    return float(np.mean([tvd(pred[T], obs[T]) for T in obs]))


# ------------------------------------------------------------------------------------------------ tests
def _synthetic_two_level() -> tuple[dict[str, Any], dict[str, Any], dict[float, float]]:
    """U9: an empty opening; first decision a (p_a) vs b; inside a, an intermediate token path O2 = [x] with
    probability w2 and then t2 in {c, d}; b -> algorithm 0. Analytic P(alg 1)."""
    V = 12
    za = np.full(V, -1e4)
    za[1], za[2] = 0.3, 0.0                     # t1 = 1 (a, goes to second decision) or 2 (b -> alg 0)
    zx = np.full(V, -1e4)
    zx[5], zx[6] = 1.0, 0.0                     # O2 = [5]; leaving it (token 6) -> phat_off
    zd = np.full(V, -1e4)
    zd[7], zd[8] = 0.4, 0.0                     # t2 = 7 -> alg 1, t2 = 8 -> alg 0
    law = {"q_rest": [0.5, 0.5], "openings": [{
        "id": "c0", "O": [], "tokens": [1, 2], "phat": {"1": [0.5, 0.5], "2": [1.0, 0.0]}, "resid_phat": [0.5, 0.5],
        "second": {"1": {"O2": [5], "tokens2": [7, 8], "phat2": {"7": [0.0, 1.0], "8": [1.0, 0.0]},
                         "resid2_phat": [0.5, 0.5], "phat_off": [1.0, 0.0]}}}]}
    tf: dict[str, Any] = {"c0": {"second": {"1": {}}}}
    want = {}
    for T in (0.3, 1.0, 1.3):
        key = f"p1|{T}"
        pa = dist(za, T, 0)
        px = dist(zx, T, 0)
        pd = dist(zd, T, 0)
        tf["c0"][key] = {"lp_open": 0.0, "p_top": [pa[1], pa[2]], "resid": 1.0 - pa[1] - pa[2]}
        tf["c0"]["second"]["1"][key] = {"lp_O2": math.log(px[5]), "p_top2": [pd[7], pd[8]],
                                        "resid2": 1.0 - pd[7] - pd[8]}
        want[T] = pa[1] * px[5] * pd[7]          # the only route to algorithm 1
    return law, {"W1": tf}, want


def u9_test() -> dict[str, Any]:
    law, tfw, want = _synthetic_two_level()
    got = {T: float(cell_prediction(law, tfw, T, "p1")["P"][1]) for T in want}
    single = {T: float(cell_prediction(law, tfw, T, "p1", single=True)["P"][1]) for T in want}
    ok = all(abs(got[T] - want[T]) < 1e-9 for T in want)
    return {"got": got, "want": want, "single_decision_law": single, "pass": ok}


def u10_test(n: int = 1000, seed: int = 7) -> dict[str, Any]:
    """U10: the top-k shadow construction equals direct top-k sampling on synthetic logit sequences with shared
    uniforms. A 'program' is a 12-step Markov chain whose logits depend on the previous token."""
    rng = np.random.default_rng(seed)
    V, L, k = 40, 12, 10
    Wt = rng.normal(0, 2.0, size=(V, V))
    ok = 0
    n_div = 0
    for _ in range(n):
        T = float(rng.choice([0.3, 0.7, 1.0, 1.3]))
        u = rng.random(L)
        z0 = rng.normal(0, 2.0, size=V)

        def run(top_k: int, prefix: list[int], start: int) -> list[int]:
            seq = list(prefix)
            for i in range(start, L):
                z = z0 if not seq else Wt[seq[-1]]
                seq.append(replay.pick(z, u[i], T, top_k))
            return seq
        direct = run(k, [], 0)
        # shadow: top-p run; at the first step where the top-k pick differs, switch to top-k from there on
        seq: list[int] = []
        div = None
        for i in range(L):
            z = z0 if not seq else Wt[seq[-1]]
            a, b = replay.pick(z, u[i], T, 0), replay.pick(z, u[i], T, k)
            if a != b:
                div = i
                seq.append(b)
                break
            seq.append(a)
        if div is not None:
            n_div += 1
            seq = run(k, seq, div + 1)
        ok += seq == direct
    return {"n": n, "identical": ok, "diverged": n_div, "pass": ok == n}


def u11_test(n_u: int = 10000, seed: int = 11) -> dict[str, Any]:
    """U11: the per-slot replay walk equals the analytic opening probability (Monte Carlo over uniforms)."""
    rng = np.random.default_rng(seed)
    V, L = 30, 6
    Z = rng.normal(0, 1.5, size=(L, V))
    O = [int(np.argmax(Z[i])) for i in range(L)]
    for i in range(L):
        Z[i, O[i]] += 4.0                          # a typical opening: each token likely, the path not certain
    out = {}
    ok = True
    for T in (0.7, 1.3):
        analytic = math.exp(sum(math.log(dist(Z[i], T, 0)[O[i]]) for i in range(L)))
        U = rng.random((n_u, L))
        hits = 0
        for s in range(n_u):
            on = True
            for i in range(L):
                if replay.pick(Z[i], U[s, i], T, 0) != O[i]:
                    on = False
                    break
            hits += on
        mc = hits / n_u
        se = math.sqrt(analytic * (1 - analytic) / n_u)
        out[str(T)] = {"analytic": analytic, "monte_carlo": mc, "se": se, "within_3se": abs(mc - analytic) <= 3 * se}
        ok &= abs(mc - analytic) <= 3 * se
    return {"by_T": out, "pass": bool(ok)}


def run_unit_tests() -> dict[str, Any]:
    res = {"U5": P7.u5_test(), "U8": P7.u8_test(), "U9": u9_test(), "U10": u10_test(), "U11": u11_test()}
    res["all_pass"] = all(v["pass"] for v in res.values() if isinstance(v, dict) and "pass" in v)
    return res


if __name__ == "__main__":
    import json
    print(json.dumps(run_unit_tests(), indent=1, default=float))
