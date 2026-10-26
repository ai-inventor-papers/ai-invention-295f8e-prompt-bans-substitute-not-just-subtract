#!/usr/bin/env python3
"""Independent re-derivation of every headline number (STANDARD LIBRARY ONLY; a separate code path from src/).

Reads only results/*.jsonl, data/*.jsonl and the labels, recomputes from the per-prompt / per-program rows:
  W1-TF  ratio-of-sums shares of every arm, the 3 x 50 null shares, their median / p95 / max and empirical p
  W1-GEN correct counts per arm, exact McNemar discordant counts and two-sided p, Wilson intervals
  W2     all-position and fork-only shares, the late - early difference
  W3     Gemma shares and null ranks
and compares them with the summaries written by src/ (results/*summary.json, results/w1_generation.json).
Placebos (must FAIL to reproduce an effect):
  P1 m_arm replaced by m_I + N(0, 0.05): share ~ 0
  P2 arm labels randomly swapped within CRN pairs (ROWS vs TWIN): median McNemar p >= 0.3
  P3 shuffled D/A token identities among the S tokens (ROWS_ALL): the share distribution, reported with its centre
Usage: python audit/rederive.py [--synthetic]   (writes results/rederive.json)
"""

from __future__ import annotations

import json
import math
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
DATA = ROOT / "data"
TOL = 1e-6


def jl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def share(rows: list[dict], key: str = "m") -> float:
    num = sum(r["m_I"] - r[key] for r in rows)
    den = sum(r["m_I"] - r["m_B"] for r in rows)
    return num / den if abs(den) > 1e-12 else float("nan")


def pctl(v: list[float], q: float) -> float:
    """numpy-style linear-interpolation percentile."""
    s = sorted(v)
    k = (len(s) - 1) * q / 100.0
    f = math.floor(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def mcnemar(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def lse(v: list[float]) -> float:
    m = max(v)
    return m + math.log(sum(math.exp(x - m) for x in v))


class Checker:
    def __init__(self) -> None:
        self.n = 0
        self.mism: list[dict] = []

    def eq(self, name: str, mine: float, theirs: float, tol: float = TOL) -> None:
        self.n += 1
        if theirs is None or mine is None or (isinstance(mine, float) and math.isnan(mine)):
            if not (theirs is None and mine is None):
                self.mism.append({"check": name, "rederived": mine, "reported": theirs})
            return
        if abs(mine - theirs) > tol * max(1.0, abs(theirs)):
            self.mism.append({"check": name, "rederived": mine, "reported": theirs})


def w1_tf(ch: Checker, out: dict) -> None:
    rows = jl(RES / "w1_tf_rows.jsonl")
    summ = json.loads((RES / "w1_tf_summary.json").read_text())
    res: dict = {}
    for u in sorted({r["unit"] for r in rows}):
        ur = [r for r in rows if r["unit"] == u]
        arms = sorted({r["arm"] for r in ur if r["draw"] is None})
        us = {}
        for a in arms:
            s = share([r for r in ur if r["arm"] == a and r["draw"] is None])
            us[a] = s
            if a in summ["units"][u]["arms"]:
                ch.eq(f"W1 {u} {a} share", s, summ["units"][u]["arms"][a]["share"])
        nulls = {}
        for nt in ("RAND_ISO", "DELTA_SWAP", "RAND_RESID"):
            draws = sorted({r["draw"] for r in ur if r["arm"] == nt})
            shs = [share([r for r in ur if r["arm"] == nt and r["draw"] == k]) for k in draws]
            obs = us["ROWS_ALL"]
            p = (1 + sum(1 for x in shs if x >= obs)) / (1 + len(shs))
            rep = summ["units"][u]["nulls"][nt]
            ch.eq(f"W1 {u} {nt} median", statistics.median(shs), rep["median"])
            ch.eq(f"W1 {u} {nt} p95", pctl(shs, 95), rep["p95"])
            ch.eq(f"W1 {u} {nt} max", max(shs), rep["max"])
            ch.eq(f"W1 {u} {nt} empirical p", p, rep["empirical_p_rows_all"])
            nulls[nt] = {"median": statistics.median(shs), "p95": pctl(shs, 95), "max": max(shs), "p": p,
                         "n": len(shs)}
        # verdict re-derivation (T10 primary rule)
        iso = nulls["RAND_ISO"]
        v = ("SUPPORTED" if us["ROWS_ALL"] >= 0.5 and iso["median"] <= 0.15 and us["ROWS_ALL"] > iso["max"] else
             "DISCONFIRMED" if us["ROWS_ALL"] <= 0.2 else "PARTIAL")
        if v != summ["units"][u]["verdict"]:
            ch.mism.append({"check": f"W1 {u} verdict", "rederived": v, "reported": summ["units"][u]["verdict"]})
        ch.n += 1
        res[u] = {"shares": us, "nulls": nulls, "verdict": v}
    out["W1_TF"] = res


def w1_gen(ch: Checker, out: dict) -> None:
    raw = {r["sid"]: r for r in jl(DATA / "gen_samples.jsonl")}
    lab = {r["sid"]: r for r in jl(DATA / "gen_labels.jsonl")}
    rep = json.loads((RES / "w1_generation.json").read_text())
    correct = {"T10": {"dfs"}, "B3": {"prim_heap", "prim_array"}}
    res: dict = {}
    for u in ("T10", "B3"):
        if u not in rep["units"]:
            continue
        cells = {}
        ind: dict[str, dict] = {}
        for s, r in raw.items():
            if r["unit"] != u or s not in lab:
                continue
            ok = int(lab[s]["label"] in correct[u] and bool(lab[s]["passed"]))
            ind.setdefault(r["arm"], {})[(r["template"], r["slot"])] = ok
        for a, d in ind.items():
            k, n = sum(d.values()), len(d)
            cells[a] = {"n_correct": k, "n": n, "wilson": wilson(k, n)}
            if a not in rep["units"][u]["cells"]:
                continue
            ch.eq(f"GEN {u} {a} n_correct", k, rep["units"][u]["cells"][a]["n_correct"])
            lo, hi = wilson(k, n)
            ch.eq(f"GEN {u} {a} wilson lo", lo, rep["units"][u]["cells"][a]["correct_ci95"][0])
        # pooled 90-pair power extension (main 30 + EXTRA60) vs results/w1_generation_power.json
        pw_p = RES / "w1_generation_power.json"
        if pw_p.exists():
            pw = json.loads(pw_p.read_text())["units"].get(u, {})
            pooled = {}
            for a in ("TWIN", "ROWS", "RAND_MED"):
                d = dict(ind.get(a, {}))
                d.update(ind.get(a + "_EXTRA60", {}))
                pooled[a] = d
                if a in pw.get("cells", {}):
                    ch.eq(f"POWER {u} {a} n_correct", sum(d.values()), pw["cells"][a]["n_correct"])
            for a, b in (("ROWS", "TWIN"), ("ROWS", "RAND_MED")):
                ks = sorted(set(pooled[a]) & set(pooled[b]))
                bb = sum(1 for k in ks if pooled[a][k] == 1 and pooled[b][k] == 0)
                cc = sum(1 for k in ks if pooled[a][k] == 0 and pooled[b][k] == 1)
                t = pw.get("tests", {}).get(f"{a}_vs_{b}")
                if t:
                    ch.eq(f"POWER {u} {a}_vs_{b} b", bb, t["b_first_only"])
                    ch.eq(f"POWER {u} {a}_vs_{b} p", mcnemar(bb, cc), t["p_exact_two_sided"])
        tests = {}
        for key, t in rep["units"][u]["tests"].items():
            if "|" in key:
                continue
            a, b = key.split("_vs_")
            if a not in ind or b not in ind:
                continue
            ks = sorted(set(ind[a]) & set(ind[b]))
            bb = sum(1 for k in ks if ind[a][k] == 1 and ind[b][k] == 0)
            cc = sum(1 for k in ks if ind[a][k] == 0 and ind[b][k] == 1)
            p = mcnemar(bb, cc)
            ch.eq(f"GEN {u} {key} b", bb, t["b_first_only"])
            ch.eq(f"GEN {u} {key} c", cc, t["c_second_only"])
            ch.eq(f"GEN {u} {key} p", p, t["p_exact_two_sided"])
            tests[key] = {"b": bb, "c": cc, "p": p}
        res[u] = {"cells": cells, "tests": tests}
        # P2 placebo: random label swaps within CRN pairs (ROWS vs TWIN)
        if "ROWS" in ind and "TWIN" in ind:
            rng = random.Random(7)
            ks = sorted(set(ind["ROWS"]) & set(ind["TWIN"]))
            ps = []
            for _ in range(500):
                bb = cc = 0
                for k in ks:
                    x, y = ind["ROWS"][k], ind["TWIN"][k]
                    if rng.random() < 0.5:
                        x, y = y, x
                    bb += int(x == 1 and y == 0)
                    cc += int(x == 0 and y == 1)
                ps.append(mcnemar(bb, cc))
            res[u]["P2_swap_placebo_median_p"] = statistics.median(ps)
            res[u]["P2_pass"] = statistics.median(ps) >= 0.3
    out["W1_GEN"] = res


def w2(ch: Checker, out: dict) -> None:
    rows = jl(RES / "w2_rows.jsonl")
    if not rows:
        return
    summ = json.loads((RES / "w2_summary.json").read_text())
    res: dict = {}
    for u in sorted({r["unit"] for r in rows}):
        ur = [r for r in rows if r["unit"] == u]
        us = {}
        for scope, key in (("A", "scope_A_all_position"), ("B", "scope_B_fork_only")):
            for c in sorted({r["config"] for r in ur if r["scope"] == scope}):
                last = {}
                for r in ur:
                    if r["scope"] == scope and r["config"] == c:
                        last[r["pid"]] = r
                s = share(list(last.values()))
                us[f"{scope}:{c}"] = s
                if c in summ["units"][u][key]:
                    ch.eq(f"W2 {u} {scope} {c}", s, summ["units"][u][key][c]["share"])
        if "A:W_late_joint" in us and "A:E_joint" in us:
            d = us["A:W_late_joint"] - us["A:E_joint"]
            ch.eq(f"W2 {u} late-early diff", d, summ["units"][u]["rule"]["diff"])
            us["late_minus_early"] = d
        res[u] = us
    out["W2"] = res


def w3(ch: Checker, out: dict) -> None:
    rows = jl(RES / "w3_rows.jsonl")
    if not rows:
        return
    summ = json.loads((RES / "w3_summary.json").read_text())
    us = {}
    for a in sorted({r["arm"] for r in rows if r["draw"] is None}):
        s = share([r for r in rows if r["arm"] == a and r["draw"] is None])
        us[a] = s
        if a in summ["arms"]:
            ch.eq(f"W3 {a}", s, summ["arms"][a]["share"])
    for nt in ("RAND_ISO", "DELTA_SWAP"):
        draws = sorted({r["draw"] for r in rows if r["arm"] == nt})
        shs = [share([r for r in rows if r["arm"] == nt and r["draw"] == k]) for k in draws]
        ch.eq(f"W3 {nt} median", statistics.median(shs), summ["nulls"][nt]["median"])
        ch.eq(f"W3 {nt} max", max(shs), summ["nulls"][nt]["max"])
        us[f"{nt}_median"] = statistics.median(shs)
    out["W3"] = us


def placebos(out: dict) -> None:
    rows = jl(RES / "w1_tf_rows.jsonl")
    rng = random.Random(11)
    p1 = {}
    for u in sorted({r["unit"] for r in rows}):
        ur = [dict(r) for r in rows if r["unit"] == u and r["arm"] == "ROWS_ALL" and r["draw"] is None]
        vals = []
        for _ in range(200):
            for r in ur:
                r["m_fake"] = r["m_I"] + rng.gauss(0, 0.05)
            vals.append(share(ur, "m_fake"))
        p1[u] = {"mean_share": statistics.mean(vals), "max_abs_share": max(abs(v) for v in vals),
                 "pass": max(abs(v) for v in vals) < 0.1}
    out["P1_noise_placebo"] = p1
    # P3: shuffled D/A identities among the S tokens (keeping |D|), ROWS_ALL share under each shuffle
    zs = jl(RES / "w1_tf_zS.jsonl")
    p3 = {}
    for u in sorted({r["unit"] for r in zs}):
        ur = [r for r in zs if r["unit"] == u]
        nS, nD = len(ur[0]["S"]), ur[0]["nD"]
        idx = list(range(nS))
        vals = []
        for _ in range(200):
            rng.shuffle(idx)
            D, A = idx[:nD], idx[nD:]
            if sorted(D) == list(range(nD)):
                continue

            def m(z: list[float]) -> float:
                return lse([z[i] for i in D]) - lse([z[i] for i in A])
            rr = [{"m_I": m(r["z_TWIN"]), "m": m(r["z_ROWS_ALL"]), "m_B": m(r["z_BASE"])} for r in ur]
            vals.append(share(rr))
        true = share([{"m_I": lse([r["z_TWIN"][i] for i in range(nD)]) - lse([r["z_TWIN"][i] for i in range(nD, nS)]),
                       "m": lse([r["z_ROWS_ALL"][i] for i in range(nD)]) - lse([r["z_ROWS_ALL"][i]
                                                                                for i in range(nD, nS)]),
                       "m_B": lse([r["z_BASE"][i] for i in range(nD)]) - lse([r["z_BASE"][i] for i in range(nD, nS)])}
                      for r in ur])
        p3[u] = {"n_shuffles": len(vals), "median_share": statistics.median(vals) if vals else None,
                 "iqr": [pctl(vals, 25), pctl(vals, 75)] if vals else None, "true_assignment_share": true,
                 "note": "ROWS_ALL replaces every S row, so any contrast among S tokens is moved toward the base "
                         "readout; a share near the true one under shuffled identities means the closing is "
                         "readout-wide rather than specific to the default/alternative split"}
    out["P3_DA_shuffle_placebo"] = p3


def synthetic() -> dict:
    """Self-test on synthetic rows with known answers."""
    rows = [{"m_I": 3.0, "m_B": 1.0, "m": 2.0}, {"m_I": 5.0, "m_B": 1.0, "m": 3.0}]
    ok1 = abs(share(rows) - 0.5) < 1e-12
    ok2 = mcnemar(4, 0) == 0.125 and mcnemar(0, 0) == 1.0
    lo, hi = wilson(0, 30)
    ok3 = lo == 0.0 and abs(hi - 0.1135) < 1e-3
    ok4 = abs(pctl([1, 2, 3, 4, 5], 95) - 4.8) < 1e-12
    return {"share": ok1, "mcnemar": ok2, "wilson": ok3, "percentile": ok4, "all_pass": ok1 and ok2 and ok3 and ok4}


def main() -> None:
    out: dict = {"synthetic_self_test": synthetic()}
    if "--synthetic" in sys.argv:
        print(json.dumps(out, indent=1))
        return
    ch = Checker()
    for fn in (w1_tf, w1_gen, w2, w3):
        try:
            fn(ch, out)
        except (FileNotFoundError, KeyError) as e:
            out.setdefault("errors", []).append(f"{fn.__name__}: {e!r}")
    placebos(out)
    out["n_checks"] = ch.n
    out["n_mismatches"] = len(ch.mism)
    out["mismatches"] = ch.mism
    (RES / "rederive.json").write_text(json.dumps(out, indent=1))
    print(f"rederive: {ch.n} checks, {len(ch.mism)} mismatches; synthetic {out['synthetic_self_test']['all_pass']}")
    for m in ch.mism[:20]:
        print("  MISMATCH", m)


if __name__ == "__main__":
    main()
