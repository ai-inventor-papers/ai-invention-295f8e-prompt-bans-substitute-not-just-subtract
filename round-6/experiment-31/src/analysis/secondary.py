#!/usr/bin/env python3
"""Secondary analyses of panel I (plan S10), all descriptive within one panel:

L2  correct nudged off-default programs whose mode has 0 valid and 0 correct base programs; rule-of-three 3/N.
L3  per unit, over the non-default modes, forecasts of the nudged correct off-default programs (ESC + PN + GTN pooled):
    q_base^gamma (gamma by maximum likelihood on half A, grid 0..5 step 0.05), uniform, association (the 20 instruct
    answers naming an alternative to D_u, alias lexicon, add-one) and q_tail; held-out mean log score on half B over 10
    random splits; pooled Kendall tau between the base and tail orders with a sign test over units.
M   Spearman between each frozen candidate and E_u over the units, one-sided in the frozen direction, exact
    permutation p (all n! orderings), Holm correction; supported iff rho >= 0.5 and Holm p < 0.05.
K   correct-only rarefied Hill-1 (depth 25) vs pass cost for the knobs PN a2, PN a4 (+ BINT where run): H5 / P15 / P20 =
    the largest Hill-1 over the full-simplex randomisation hull of {twin, knob settings} (grid step 0.05) at a pass
    cost <= 5 / 15 / 20 points; edge-restricted hull (twin + one setting) as sensitivity; 2,000 slot-bootstrap
    replicates with the maximum taken inside each.
Writes results/l2.json, l3.json, m.json, k.json.
"""

from __future__ import annotations

import itertools
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cfg6 import EXCLUDE, PRED_DIR, RESULTS_DIR, read_json, write_json  # noqa: E402
from labels_view6 import load_final  # noqa: E402
from units_spec6 import map_answer  # noqa: E402

DIRS = {"beta": +1, "replacement": -1, "runtime_merit": -1, "twin_modal_share": -1, "K": +1, "m": -1}


def nudged_rows(labs, u):
    return [l for l in labs if l["unit"] == u and l.get("src") == "hf" and l["family"] in ("ESC", "PN", "GTN")]


def l2(units, labs) -> dict:
    out, tot_n, tot_novel = [], 0, 0
    for U in units:
        u, D, cat = U["unit"], U["default"], U["catalogue"]
        rec = read_json(PRED_DIR / "units" / f"{u}.json")
        sup = rec["base_support"]
        rows = [r for r in nudged_rows(labs, u) if r.get("passed") and r["final"] in cat and r["final"] != D]
        absent = {m for m in cat if m != D and sup[m]["total_valid"] == 0 and sup[m]["total_correct"] == 0}
        n_abs = sum(1 for r in rows if r["final"] in absent)
        out.append({"unit": u, "n_correct_off_default": len(rows), "modes_absent_in_base": sorted(absent),
                    "n_in_absent_modes": n_abs})
        tot_n += len(rows)
        tot_novel += n_abs
    return {"units": out, "N": tot_n, "count_in_base_absent_modes": tot_novel,
            "rule_of_three_upper": (3 / tot_n) if (tot_n and tot_novel == 0) else None}


def logscore(q: dict, labels: list[str]) -> float:
    return float(np.mean([math.log(max(q.get(x, 0.0), 1e-12)) for x in labels])) if labels else float("nan")


def l3(units, labs, n_splits: int = 10) -> dict:
    rng = np.random.default_rng(0)
    res, taus = [], []
    for U in units:
        u, D, cat = U["unit"], U["default"], U["catalogue"]
        nd = [m for m in cat if m != D]
        lab = [r["final"] for r in nudged_rows(labs, u) if r.get("passed") and r["final"] in nd]
        rec = read_json(PRED_DIR / "units" / f"{u}.json")
        qb = {m: rec["q_base"][m] for m in nd}
        z = sum(qb.values())
        qb = {m: v / z for m, v in qb.items()}
        qt = {m: rec["q_tail"][m] for m in nd}
        z = sum(qt.values())
        qt = {m: v / z for m, v in qt.items()}
        assoc = Counter(map_answer(u, l.get("assoc_answer", ""), modes=nd) for l in labs
                        if l["unit"] == u and l["arm"] == f"ASSOC_{D}")
        qa = {m: (assoc.get(m, 0) + 1) / (sum(assoc.get(x, 0) for x in nd) + len(nd)) for m in nd}
        uni = {m: 1 / len(nd) for m in nd}
        # Kendall tau between the base and the tail orders over the non-default modes
        from scipy.stats import kendalltau
        tau = kendalltau([qb[m] for m in nd], [qt[m] for m in nd]).statistic if len(nd) >= 2 else float("nan")
        taus.append(tau)
        row = {"unit": u, "n_programs": len(lab), "kendall_tau_base_tail": tau, "association_counts": dict(assoc)}
        if len(lab) >= 4:
            sc = {"q_base_gamma": [], "uniform": [], "association": [], "q_tail": [], "gamma": []}
            for _ in range(n_splits):
                idx = rng.permutation(len(lab))
                A = [lab[i] for i in idx[: len(lab) // 2]]
                Bh = [lab[i] for i in idx[len(lab) // 2:]]
                best_g, best_ll = 0.0, -1e18
                for g in np.arange(0, 5.0001, 0.05):
                    qg = {m: qb[m] ** g for m in nd}
                    zz = sum(qg.values())
                    ll = sum(math.log(max(qg[x] / zz, 1e-12)) for x in A)
                    if ll > best_ll:
                        best_g, best_ll = float(g), ll
                qg = {m: qb[m] ** best_g for m in nd}
                zz = sum(qg.values())
                qg = {m: v / zz for m, v in qg.items()}
                sc["gamma"].append(best_g)
                sc["q_base_gamma"].append(logscore(qg, Bh))
                sc["uniform"].append(logscore(uni, Bh))
                sc["association"].append(logscore(qa, Bh))
                sc["q_tail"].append(logscore(qt, Bh))
            row["heldout_log_score"] = {k: float(np.mean(v)) for k, v in sc.items()}
        res.append(row)
    vt = [t for t in taus if not math.isnan(t)]
    pos = sum(1 for t in vt if t > 0)
    neg = sum(1 for t in vt if t < 0)
    from scipy.stats import binomtest
    sign_p = binomtest(pos, pos + neg, 0.5, alternative="greater").pvalue if pos + neg else 1.0
    return {"units": res, "mean_tau": float(np.mean(vt)) if vt else None, "n_tau_pos": pos, "n_tau_neg": neg,
            "sign_test_p": float(sign_p)}


def spearman(x, y) -> float:
    from scipy.stats import rankdata
    rx, ry = rankdata(x), rankdata(y)
    if np.std(rx) == 0 or np.std(ry) == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def exact_perm_p(x, y, direction: int, max_exact: int = 9) -> tuple[float, str]:
    from scipy.stats import rankdata
    rx, ry = rankdata(x), rankdata(y)
    obs = direction * spearman(x, y)
    n = len(x)
    if n <= max_exact:
        perms = np.array(list(itertools.permutations(range(n))))
        ryp = ry[perms]
        rxc = rx - rx.mean()
        num = (ryp - ryp.mean(axis=1, keepdims=True)) @ rxc
        den = np.sqrt((rxc ** 2).sum() * ((ryp - ryp.mean(axis=1, keepdims=True)) ** 2).sum(axis=1))
        rho = direction * np.where(den > 0, num / np.where(den > 0, den, 1), 0)
        return float(np.mean(rho >= obs - 1e-12)), f"exact enumeration ({len(perms)} permutations)"
    rng = np.random.default_rng(0)
    cnt = 0
    R = 200000
    for _ in range(R):
        cnt += direction * spearman(x, rng.permutation(y)) >= obs - 1e-12
    return float((cnt + 1) / (R + 1)), f"Monte Carlo ({R} permutations)"


def m_tests(units) -> dict:
    out = {}
    E = [U["E_u"] for U in units]
    for cand, d in DIRS.items():
        pairs = [(float(U["M"][cand]), U["E_u"]) for U in units if U["M"].get(cand) is not None and
                 U.get("E_u") is not None]
        if len(pairs) < 4:
            out[cand] = {"n": len(pairs), "rho": None, "p": None}
            continue
        x, y = zip(*pairs)
        rho = spearman(np.array(x, float), np.array(y, float))
        p, how = exact_perm_p(np.array(x, float), np.array(y, float), d)
        out[cand] = {"n": len(pairs), "direction": "+" if d > 0 else "-", "rho": rho, "p_one_sided": p, "how": how}
    ps = sorted((v["p_one_sided"], k) for k, v in out.items() if v.get("p_one_sided") is not None)
    m = len(ps)
    running = 0.0
    for i, (p, k) in enumerate(ps):
        adj = min(1.0, max(running, (m - i) * p))
        running = adj
        out[k]["p_holm"] = adj
        rho = out[k]["rho"]
        sgn = 1 if out[k]["direction"] == "+" else -1
        out[k]["supported"] = bool(rho is not None and not math.isnan(rho) and sgn * rho >= 0.5 and adj < 0.05)
    return {"candidates": out, "E_u": dict(zip([U["unit"] for U in units], E)), "label": "descriptive (one panel)"}


def hill1_rarefied(comp: Counter, depth: int = 25, n_draw: int = 400, rng=None) -> float:
    rng = rng or np.random.default_rng(0)
    keys = [k for k in comp if comp[k] > 0]
    if not keys:
        return float("nan")
    p = np.array([comp[k] for k in keys], float)
    p /= p.sum()
    vals = []
    for _ in range(n_draw):
        c = rng.multinomial(depth, p)
        q = c[c > 0] / depth
        vals.append(math.exp(-(q * np.log(q)).sum()))
    return float(np.mean(vals))


def k_hull(units, labs, n_boot: int = 300) -> dict:
    """Hill-1 / pass-cost hull per unit for the PN knobs (and BINT where its rows exist)."""
    rng = np.random.default_rng(0)
    out = []
    for U in units:
        u, cat = U["unit"], U["catalogue"]
        R = [l for l in labs if l["unit"] == u and l.get("final") not in (None, "disputed")]
        groups = {"twin": [l for l in R if l["arm"] in ("TWINHF", "TWIN", "TWIN13")],
                  "PN_a2": [l for l in R if l["arm"] == "PN_a2"], "PN_a4": [l for l in R if l["arm"] == "PN_a4"],
                  "BINT": [l for l in R if l["arm"] == "BINT"]}
        groups = {k: v for k, v in groups.items() if v}

        def stats(gs):
            comp = {k: Counter(l["final"] for l in v if l.get("passed") and l["final"] not in EXCLUDE)
                    for k, v in gs.items()}
            pr = {k: (sum(1 for l in v if l.get("passed")) / len(v)) for k, v in gs.items()}
            return comp, pr

        def hull(comp, pr, edge: bool):
            names = list(comp)
            twin_pr = pr["twin"]
            best = {5: float("nan"), 15: float("nan"), 20: float("nan")}
            grid = np.arange(0, 1.0001, 0.05)
            others = [n for n in names if n != "twin"]
            combos = []
            if edge:
                for o in others:
                    for w in grid:
                        combos.append({"twin": 1 - w, o: w})
            else:
                for ws in itertools.product(grid, repeat=len(others)):
                    if sum(ws) <= 1 + 1e-9:
                        d = {"twin": 1 - sum(ws)}
                        d.update(dict(zip(others, ws)))
                        combos.append(d)
            for d in combos:
                mix = Counter()
                for n_, w in d.items():
                    tot = sum(comp[n_].values())
                    if tot:
                        for k, v in comp[n_].items():
                            mix[k] += w * v / tot
                cost = 100 * (twin_pr - sum(w * pr[n_] for n_, w in d.items()))
                h = hill1_rarefied(mix, n_draw=60, rng=rng)
                for c in best:
                    if cost <= c and (math.isnan(best[c]) or h > best[c]):
                        best[c] = h
            return best

        comp, pr = stats(groups)
        row = {"unit": u, "pass_rate": pr, "hill1_depth25": {k: hill1_rarefied(v, rng=rng) for k, v in comp.items()},
               "n_correct": {k: sum(v.values()) for k, v in comp.items()},
               "flag_lt25_correct": [k for k, v in comp.items() if sum(v.values()) < 25]}
        row["hull_full"] = hull(comp, pr, edge=False)
        row["hull_edge"] = hull(comp, pr, edge=True)
        boots = []
        for _ in range(n_boot):
            gs = {k: [v[i] for i in rng.integers(0, len(v), len(v))] for k, v in groups.items()}
            c2, p2 = stats(gs)
            boots.append(hull(c2, p2, edge=True))
        row["hull_edge_boot_ci"] = {str(c): [float(np.nanquantile([b[c] for b in boots], 0.025)),
                                             float(np.nanquantile([b[c] for b in boots], 0.975))] for c in (5, 15, 20)}
        out.append(row)
    return {"units": out, "note": "bootstrap on the edge-restricted hull (computational budget); full-simplex hull "
                                  "reported as the point estimate"}


def main() -> None:
    units = read_json(ROOT / "units.json")["units"]
    labs = load_final()
    write_json(RESULTS_DIR / "l2.json", l2(units, labs))
    write_json(RESULTS_DIR / "l3.json", l3(units, labs))
    write_json(RESULTS_DIR / "m.json", m_tests(units))
    write_json(RESULTS_DIR / "k.json", k_hull(units, labs))
    print("secondary analyses written")


if __name__ == "__main__":
    main()
