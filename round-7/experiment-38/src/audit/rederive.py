#!/usr/bin/env python3
"""Standard library only. Re-derives the headline counts and tests from the raw rows (data/raw_*.jsonl +
data/labels.jsonl) and compares them with results/*.json; placebos must fail (shuffled slot labels for McNemar,
a temperature-shuffled sweep for G3, a shuffled node null for G1)."""

import json
import math
import random
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOSES = (0.1, 0.2, 0.35, 0.5, 0.75, 1.0)
TEMPS = (0.3, 0.7, 1.0, 1.3)


def jl(p: Path) -> list:
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def jread(name: str):
    p = ROOT / "results" / name
    return json.loads(p.read_text()) if p.exists() else None


def binom_sf(k: int, n: int) -> float:
    """P(X >= k), X ~ Bin(n, 1/2)."""
    return sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n


def mcnemar_one(b: int, c: int) -> float:
    return 1.0 if b + c == 0 else binom_sf(b, b + c)


def holm(ps: list) -> list:
    m = len(ps)
    order = sorted(range(m), key=lambda i: ps[i])
    adj, run = [0.0] * m, 0.0
    for r, i in enumerate(order):
        run = max(run, (m - r) * ps[i])
        adj[i] = min(1.0, run)
    return adj


def main() -> None:
    lab = {r["row_id"]: r for r in jl(ROOT / "data" / "labels.jsonl")}
    checks, mism = [], 0

    def check(name, mine, theirs, tol=1e-9):
        nonlocal mism
        ok = (mine == theirs) if not isinstance(mine, float) else (theirs is not None and abs(mine - theirs) <= tol)
        mism += not ok
        checks.append({"quantity": name, "rederived": mine, "reported": theirs, "match": ok})

    def rows(name):
        out = []
        for r in jl(ROOT / "data" / name):
            L = lab.get(r["row_id"])
            if L:
                out.append(dict(r, label=L["label"], passed=bool(L["passed"])))
        return out
    # ---------------- engine check
    eng = rows("raw_engine.jsonl")
    e_rep = jread("engine_check.json")
    if e_rep:
        check("engine_check_bfs", sum(r["label"] == "bfs" for r in eng), e_rep["bfs"])
        check("engine_check_n", len(eng), e_rep["n"])
    # ---------------- U6
    u6 = rows("raw_u6.jsonl")
    u_rep = jread("u6.json")
    a = {(r["template"], r["slot"]): r for r in u6 if r["row_id"].startswith("u6a|")}
    b = {(r["template"], r["slot"]): r for r in u6 if r["row_id"].startswith("u6b|")}
    if u_rep:
        check("u6a_bfs", sum(r["label"] == "bfs" for r in a.values()), u_rep["u6a"]["bfs_full"])
        check("u6b_bfs", sum(r["label"] == "bfs" for r in b.values()), u_rep["u6b"]["bfs_full"])
        com = set(a) & set(b)
        x = sum(a[s]["label"] == "bfs" and b[s]["label"] != "bfs" for s in com)
        y = sum(a[s]["label"] != "bfs" and b[s]["label"] == "bfs" for s in com)
        check("u6_discordant", [x, y], [u_rep["a_vs_b"]["a_bfs_b_not"], u_rep["a_vs_b"]["b_bfs_a_not"]])
        p2 = min(1.0, 2 * min(binom_sf(max(x, y), x + y), 1.0)) if x + y else 1.0
        check("u6_mcnemar_two_sided", p2, u_rep["a_vs_b"]["mcnemar_p_two_sided"], 1e-9)
    # ---------------- G3 sweep
    g3 = rows("raw_g3.jsonl")
    g_rep = jread("g3_sweep.json")
    pred = json.loads((ROOT / "predictions" / "commit1.json").read_text())["g3_predictions"]["cells"]
    if g_rep and g3:
        errs = []
        for cell in g_rep["cells"]:
            cr = [r for r in g3 if r["cell"] == cell]
            k = sum(r["label"] == "bfs" for r in cr)
            check(f"g3_{cell}_attempted_bfs", k, g_rep["cells"][cell]["attempted_bfs"])
            if cell.endswith("topp1"):
                errs.append(abs(k / len(cr) - pred[cell]["pred_bfs_primary"]))
        check("g3_MAE_topp1", sum(errs) / len(errs), g_rep["MAE_topp1"], 1e-9)
        # placebo: shuffle T labels across cells within each slot -> the law should fail (larger MAE)
        rng = random.Random(0)
        by_slot = {}
        for r in g3:
            if r["sampler"] == "topp1":
                by_slot.setdefault((r["template"], r["slot"]), []).append(r)
        shuffled = []
        for s, rs in by_slot.items():
            labels_ = [r["label"] for r in rs]
            rng.shuffle(labels_)
            shuffled += [dict(r, label=l) for r, l in zip(rs, labels_)]
        perr = []
        for T in TEMPS:
            cr = [r for r in shuffled if r["T"] == T]
            perr.append(abs(sum(r["label"] == "bfs" for r in cr) / max(len(cr), 1) - pred[f"T{T}|topp1"]["pred_bfs_primary"]))
        checks.append({"placebo": "g3_T_shuffled_MAE", "value": sum(perr) / len(perr),
                       "real_MAE": sum(errs) / len(errs), "placebo_fails_law": max(perr) > 0.10})
    # ---------------- G1 generation
    g1 = rows("raw_g1gen.jsonl")
    g1_rep = jread("g1_generation.json")
    if g1 and g1_rep:
        by = {}
        for r in g1:
            by.setdefault(r["cell"], {})[(r["template"], r["slot"])] = r
        tw = by.get("twin", {})
        for arm, d in by.items():
            tgt = "dfs" if arm.endswith("_dfs") else "bfs"
            check(f"g1_{arm}_attempted", sum(r["label"] == tgt for r in d.values()),
                  g1_rep["arms"][arm]["attempted_target"])
            if arm != "twin":
                com = set(d) & set(tw)
                x = sum(d[s]["label"] == tgt and d[s]["passed"] and not (tw[s]["label"] == tgt and tw[s]["passed"]) for s in com)
                y = sum(tw[s]["label"] == tgt and tw[s]["passed"] and not (d[s]["label"] == tgt and d[s]["passed"]) for s in com)
                check(f"g1_{arm}_p_correct", mcnemar_one(x, y), g1_rep["tests"][arm]["p_correct_one_sided"], 1e-9)
    # ---------------- G1 node null placebo (shuffled node/null assignment must not create claims)
    v = jread("g1_validation.json")
    if v:
        recs = v["per_node"]["ablate"]
        rng = random.Random(1)
        n_sig = 0
        for r in recs:
            d = list(r["d_per_prompt"])
            flips = [x * rng.choice((-1, 1)) for x in d]
            obs = sum(flips) / len(flips)
            # exact sign-flip p by enumeration for the placebo
            n = len(flips)
            cnt, M = 0, 20000                         # Monte Carlo sign-flip null for the placebo
            for _ in range(M):
                s_ = sum(x * rng.choice((-1, 1)) for x in flips) / n
                cnt += s_ >= obs - 1e-12
            n_sig += ((1 + cnt) / (1 + M)) < 0.05 / len(recs)
        checks.append({"placebo": "g1_random_sign_flipped_node_effects", "n_bonferroni_significant": n_sig,
                       "placebo_fails": n_sig == 0})
    # ---------------- G2 dose
    g2 = rows("raw_g2dose.jsonl")
    d_rep = jread("g2_dose.json")
    if g2 and d_rep:
        by = {}
        for r in g2:
            by.setdefault(r["cell"], {})[(r["template"], r["slot"])] = r
        tw = by.get("twin", {})
        for meth in ("DAS", "DiM"):
            names = [f"{meth}|bfs|{lam}" for lam in DOSES if f"{meth}|bfs|{lam}" in by]
            ps = []
            for nme in names:
                d = by[nme]
                com = set(d) & set(tw)
                x = sum(d[s]["label"] == "bfs" and d[s]["passed"] and not (tw[s]["label"] == "bfs" and tw[s]["passed"]) for s in com)
                y = sum(tw[s]["label"] == "bfs" and tw[s]["passed"] and not (d[s]["label"] == "bfs" and d[s]["passed"]) for s in com)
                ps.append(mcnemar_one(x, y))
                check(f"g2_{nme}_correct_bfs", sum(r["label"] == "bfs" and r["passed"] for r in d.values()),
                      d_rep["cells"][nme]["correct_target"])
            for nme, a_ in zip(names, holm(ps)):
                check(f"g2_{nme}_p_holm", a_, d_rep["cells"][nme].get("p_correct_holm"), 1e-9)
        # placebo: labels shuffled across slots inside each cell -> paired tests lose their pairing
        rng = random.Random(2)
        best = 1.0
        for nme in [n for n in by if n.startswith("DAS|bfs|")]:
            d = dict(by[nme])
            keys = list(d)
            vals = [d[k] for k in keys]
            rng.shuffle(vals)
            d = dict(zip(keys, vals))
            twk = list(tw)
            twv = [tw[k] for k in twk]
            rng.shuffle(twv)
            tws = dict(zip(twk, twv))
            com = set(d) & set(tws)
            x = sum(d[s]["label"] == "bfs" and d[s]["passed"] and not (tws[s]["label"] == "bfs" and tws[s]["passed"]) for s in com)
            y = sum(tws[s]["label"] == "bfs" and tws[s]["passed"] and not (d[s]["label"] == "bfs" and d[s]["passed"]) for s in com)
            best = min(best, mcnemar_one(x, y))
        checks.append({"placebo": "g2_slot_shuffled_mcnemar_min_p", "value": best,
                       "note": "unpaired after shuffling; reported for comparison with the paired tests"})
    res = {"n_checks": sum("quantity" in c for c in checks), "n_mismatch": mism, "checks": checks}
    (ROOT / "results" / "rederive.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({"n_checks": res["n_checks"], "n_mismatch": mism}))
    _ = Counter


if __name__ == "__main__":
    main()
