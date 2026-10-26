#!/usr/bin/env python3
"""Independent re-derivation from data/samples.jsonl alone (no import of analysis/ or src/ code).

Recomputes C_T (4 cells), C_PN (alpha 1/2 x T 0.7/1.0), the pooled x_s mean and its sign-flip p (own RNG: Python's
random), the PPI slopes (own AST normaliser, BFS components, numpy.polyfit), thinking completion rates and the FP8
cross-check JS, and compares them with results/c1seed.json, results/phrasing.json, results/thinking.json and
results/fp8_crosscheck.json. Integers and point estimates must match exactly (p within Monte Carlo error). Placebos:
condition labels permuted within seed must give p ~ uniform; the hash chain must verify and commit #0 must precede
the first decisive row. Writes results/rederive.json.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import random
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EXCL = {"invalid", "unresolved", "disputed", "unknown", "inconsistent", None, ""}
TEMPS = ["0.3", "0.7", "1.0", "1.3"]
DIRS = [46001, 46002, 46003, 46004, 46005, 46006]
SEEDS = [f"{w}|{k}" for w in ("W1", "W2", "W3", "W4", "W5") for k in range(4)]


def load(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def lab(r):
    if r is None:
        return None
    l = r.get("label")
    return None if l in EXCL else l


def changed(vals):
    v = [x for x in vals if x is not None]
    if len(v) < 2:
        return None
    return 1 if len(set(v)) > 1 else 0


def table(rows):
    t = {}
    for r in rows:
        t.setdefault((r["task"], f"{r['template']}|{int(r['sample_id'])}", r["arm"]), r)
    return t


def c_t(t, task, arms):
    vals = [changed([lab(t.get((task, s, a))) for a in arms]) for s in SEEDS]
    return sum(v for v in vals if v), {s: v for s, v in zip(SEEDS, vals)}


def c_pn(t, task, alpha, T):
    sums, per = [], {s: [] for s in SEEDS}
    for mask in range(64):
        if bin(mask).count("1") != 3:
            continue
        ds = [DIRS[i] for i in range(6) if mask >> i & 1]
        tot = 0
        for s in SEEDS:
            v = changed([lab(t.get((task, s, f"NOPN_T{T}")))] +
                        [lab(t.get((task, s, f"PN_D{d}_a{alpha}_T{T}"))) for d in ds])
            if v is not None:
                tot += v
                per[s].append(v)
        sums.append(tot)
    return sum(sums) / len(sums), {s: (sum(v) / len(v) if v else None) for s, v in per.items()}


def signflip(x, draws=20000, seed=97):
    rnd = random.Random(seed)
    obs = sum(x) / len(x)
    if all(v == 0 for v in x):
        return 1.0
    ge = 0
    for _ in range(draws):
        m = sum(v if rnd.random() < 0.5 else -v for v in x) / len(x)
        ge += m >= obs - 1e-12
    return (1 + ge) / (1 + draws)


# ---- independent AST normaliser (same written spec as the committed one)
def toks(code):
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, RecursionError):
        return None
    names, out = {}, []

    def nm(s):
        if s not in names:
            names[s] = "v%d" % len(names)
        return names[s]

    def walk(n):
        if isinstance(n, ast.Constant):
            out.append("Const:" + type(n.value).__name__)
            return
        out.append(n.__class__.__name__)
        for f in n._fields:
            if not hasattr(n, f):
                continue
            v = getattr(n, f)
            if isinstance(v, list):
                items = v
                if (f == "body" and items and isinstance(items[0], ast.Expr) and isinstance(items[0].value, ast.Constant)
                        and isinstance(items[0].value.value, str)):
                    items = items[1:]
                for it in items:
                    if isinstance(it, ast.AST):
                        walk(it)
            elif isinstance(v, ast.AST):
                walk(v)
            elif f in ("id", "arg", "name", "asname") and isinstance(v, str):
                out.append(nm(v))
            elif f == "attr" and isinstance(v, str):
                out.append("." + v)
            elif f == "module" and isinstance(v, str):
                out.append("mod:" + v)
    try:
        walk(tree)
    except RecursionError:
        return None
    return out


def sh4(code):
    t = toks(code) if code else None
    if t is None:
        return None
    return set(tuple(t[i:i + 4]) for i in range(len(t) - 3)) if len(t) >= 4 else {tuple(t)}


def comps(items, theta):
    n = len(items)
    adj = [[j for j in range(n) if j != i and len(items[i] & items[j]) / max(len(items[i] | items[j]), 1) >= theta - 1e-12]
           for i in range(n)]
    seen, c = set(), 0
    for i in range(n):
        if i in seen:
            continue
        c += 1
        st = [i]
        while st:
            x = st.pop()
            if x in seen:
                continue
            seen.add(x)
            st.extend(adj[x])
    return c


def ppi_slope(t, task, theta):
    ys = []
    for T in TEMPS:
        by = {}
        for s in SEEDS:
            r = t.get((task, s, f"NOPN_T{T}"))
            l = lab(r)
            g = sh4(r.get("code")) if (r and l) else None
            if l and g is not None:
                by.setdefault(l, []).append(g)
        ppi = sum(comps(v, theta) for v in by.values()) / len(by) if by else float("nan")
        ys.append(math.log(ppi) if ppi and ppi > 0 else float("nan"))
    xs = [float(x) for x in TEMPS]
    ok = [i for i, y in enumerate(ys) if y == y]
    return float(np.polyfit([xs[i] for i in ok], [ys[i] for i in ok], 1)[0]) if len(ok) >= 2 else float("nan")


def js(c1, c2):
    keys = set(c1) | set(c2)
    n1, n2 = sum(c1.values()), sum(c2.values())
    tot = 0.0
    for k in keys:
        p, q = c1.get(k, 0) / n1, c2.get(k, 0) / n2
        m = (p + q) / 2
        if p > 0:
            tot += 0.5 * p * math.log2(p / m)
        if q > 0:
            tot += 0.5 * q * math.log2(q / m)
    return tot


def chain_ok():
    prev, bad, first0 = "0" * 64, 0, None
    for line in (ROOT / "commitments.log").read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r["prev_chain"] != prev or hashlib.sha256((prev + r["sha256"]).encode()).hexdigest() != r["chain"]:
            bad += 1
        if r["tag"] == "commit0" and first0 is None:
            first0 = r["utc"]
        prev = r["chain"]
    return bad, first0


def main():
    rows = load(ROOT / "data/samples.jsonl")
    t = table(rows)
    c1 = json.loads((ROOT / "results/c1seed.json").read_text())
    phr = json.loads((ROOT / "results/phrasing.json").read_text())
    th = json.loads((ROOT / "results/thinking.json").read_text()) if (ROOT / "results/thinking.json").exists() else {}
    fp = json.loads((ROOT / "results/fp8_crosscheck.json").read_text()) if (ROOT / "results/fp8_crosscheck.json").exists() else {}
    checks, mism = [], 0

    def chk(name, mine, theirs, tol=0.0):
        nonlocal mism
        ok = (mine is None and theirs is None) or (mine is not None and theirs is not None and (
            abs(float(mine) - float(theirs)) <= tol or (mine != mine and theirs != theirs)))
        mism += not ok
        checks.append({"check": name, "rederived": mine, "reported": theirs, "ok": ok})
    xs = []
    for task in ("T2", "T03", "T1"):
        ct, per_t = c_t(t, task, [f"NOPN_T{T}" for T in TEMPS])
        chk(f"C_T {task}", ct, c1["A1_C_T_off"][task]["primary"]["C_T"])
        for alpha in ("1.0", "2.0"):
            for T in ("0.7", "1.0"):
                key = f"a{alpha}_T{T}"
                if key in c1["A2_C_PN"][task]:
                    v, per = c_pn(t, task, alpha, T)
                    chk(f"C_PN {task} {key}", v, c1["A2_C_PN"][task][key]["C_PN"], 1e-9)
                    if alpha == "1.0" and T == "1.0" and task in ("T2", "T03"):
                        xs += [per[s] - per_t[s] for s in SEEDS if per[s] is not None and per_t[s] is not None]
        for theta in ("0.7", "0.8", "0.9"):
            chk(f"PPI slope {task} theta {theta}", ppi_slope(t, task, float(theta)),
                phr["per_task"][task]["theta"][theta]["slope"], 1e-9)
    pooled = c1["A3_x_contrast"]["pooled"]
    if xs:
        chk("x_s pooled mean", sum(xs) / len(xs), pooled["mean_x"], 1e-12)
        p = signflip(xs)
        se = math.sqrt(max(p * (1 - p), 1e-6) / 20000) + math.sqrt(max(p * (1 - p), 1e-6) / 100000)
        chk("x_s sign-flip p (MC)", p, pooled["sign_flip"]["p"], max(0.01, 4 * se))
    # thinking completion
    for arm, v in (th.get("per_T") or {}).items():
        rr = [r for r in rows if r["task"] == "T2" and r["arm"] == arm]
        if rr:
            chk(f"completion {arm}", sum(bool(r.get("completed")) for r in rr) / len(rr), v["completion_rate"], 1e-12)
    if th.get("C_T_completed_all_4"):
        arms = [f"THINK_T{T}" for T in TEMPS]
        cs = [s for s in SEEDS if all((t.get(("T2", s, a)) or {}).get("completed") for a in arms)]
        vals = [changed([lab(t.get(("T2", s, a))) for a in arms]) for s in cs]
        chk("C_T T2 thinking on (complete seeds)", sum(v for v in vals if v), th["C_T_completed_all_4"]["C_T"])
    if fp.get("available"):
        v = Counter(lab(r) for r in rows if r["task"] == "T2" and r["arm"] == "FP8X_T1.0")
        h = Counter(lab(r) for r in rows if r["task"] == "T2" and r["arm"] == "EC_NEUTRAL_T1.0")
        v.pop(None, None)
        h.pop(None, None)
        chk("FP8 JS bits", js(v, h), fp["js_bits"], 1e-9)
    # placebo: condition labels permuted within seed -> p should be ~uniform
    rnd = random.Random(5)
    ps = []
    arms10 = [f"NOPN_T{T}" for T in TEMPS] + [f"PN_D{d}_a1.0_T1.0" for d in DIRS]
    pmeans = []
    for rep in range(200):
        xx = []
        for task in ("T2", "T03"):
            for s in SEEDS:
                labs_ = [lab(t.get((task, s, a))) for a in arms10]
                rnd.shuffle(labs_)
                ctv = changed(labs_[:4])
                pn = []
                for mask in range(64):
                    if bin(mask).count("1") == 3:
                        v = changed([labs_[2]] + [labs_[4 + i] for i in range(6) if mask >> i & 1])
                        if v is not None:
                            pn.append(v)
                if ctv is not None and pn:
                    xx.append(sum(pn) / len(pn) - ctv)
        if xx:
            ps.append(signflip(xx, draws=1000, seed=rep))
            pmeans.append(sum(xx) / len(xx))
    bad, first0 = chain_ok()
    decisive = [r.get("utc") for r in rows if r.get("utc") and not str(r["arm"]).startswith(("SMOKE",))]
    first_row = min(decisive) if decisive else None
    out = {"n_rows": len(rows), "checks": checks, "mismatches": mism,
           "placebo_share_p_lt_0.05": (sum(p < 0.05 for p in ps) / len(ps)) if ps else None,
           "placebo_median_p": float(np.median(ps)) if ps else None,
           "placebo_reps": len(ps),
           "within_seed_permutation_test_mean_x": {
               "observed": (sum(xs) / len(xs)) if xs else None, "placebo_max": max(pmeans) if pmeans else None,
               "p": ((1 + sum(m >= (sum(xs) / len(xs)) - 1e-12 for m in pmeans)) / (1 + len(pmeans))) if (xs and pmeans) else None},
           "hash_chain_breaks": bad, "commit0_utc": first0, "first_decisive_row_utc": first_row,
           "commit0_precedes_first_row": bool(first0 and first_row and first0 < first_row)}
    (ROOT / "results/rederive.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "checks"}, indent=1))


if __name__ == "__main__":
    main()
