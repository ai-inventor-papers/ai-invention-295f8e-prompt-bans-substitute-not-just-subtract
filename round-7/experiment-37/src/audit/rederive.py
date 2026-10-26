#!/usr/bin/env python3
"""Independent re-derivation (stdlib only, no imports from src/) of every headline count, rate, ratio, CI and verdict
from data/samples.jsonl, compared with results/ratio_tests.json and results/arm_rates.json; plus the two placebos
(arm labels shuffled within task; seeds scored as children). Writes audit/rederive_report.json; exit 1 on mismatch."""

import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMS = ("S", "NE", "I0", "EAP", "BINT", "B0")


def load(p):
    return json.loads((ROOT / p).read_text())


def rows():
    out = []
    with (ROOT / "data/samples.jsonl").open() as f:
        for ln in f:
            if ln.strip():
                out.append(json.loads(ln))
    return out


def _logpmf(k, n, p):
    if p <= 0:
        return 0.0 if k == 0 else -math.inf
    if p >= 1:
        return 0.0 if k == n else -math.inf
    return (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * math.log(p)
            + (n - k) * math.log1p(-p))


def binom_sf(x, n, p):
    """P(X >= x)."""
    if x <= 0:
        return 1.0
    return min(1.0, sum(math.exp(_logpmf(k, n, p)) for k in range(x, n + 1)))


def binom_cdf(x, n, p):
    if x < 0:
        return 0.0
    return min(1.0, sum(math.exp(_logpmf(k, n, p)) for k in range(0, x + 1)))


def cp_lower(x, m, a):
    """p with P(X >= x | p) = a (bisection)."""
    if x == 0:
        return 0.0
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if binom_sf(x, m, mid) < a:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def cp_upper(x, m, a):
    """p with P(X <= x | p) = a."""
    if x == m:
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if binom_cdf(x, m, mid) > a:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def test(xs, ns, xk, nk):
    m = xs + xk
    if m == 0 or ns == 0 or nk == 0:
        return {"R_hat": None, "LB95": None, "estimable": False, "p": 1.0}
    to_r = lambda p: p * nk / (ns * (1 - p)) if p < 1 else math.inf  # noqa: E731
    r = (xs / ns) / (xk / nk) if xk > 0 else math.inf
    return {"R_hat": r, "LB95": to_r(cp_lower(xs, m, 0.05)), "CI95": [to_r(cp_lower(xs, m, 0.025)),
                                                                       to_r(cp_upper(xs, m, 0.025))],
            "estimable": True, "p": binom_sf(xs, m, ns / (ns + nk))}


def verdict(t):
    if not t["estimable"]:
        return "NOT ESTIMABLE"
    if t["LB95"] >= 10:
        return "STRONG"
    if t["R_hat"] >= 10:
        return "MET" if t["LB95"] > 1 else "UNRESOLVED"
    return "NOT MET"


def counts(rs, task, arm):
    sel = [r for r in rs if r["task"] == task and r["arm"] == arm]
    ooc = [r for r in sel if r.get("correct") and r.get("ooc_screen")]
    xa = len({r["distinct_id"] for r in ooc if r.get("distinct_id")})
    xb = len({r["distinct_id"] for r in ooc if r.get("distinct_id") and
              r.get("final_class") in ("KNOWN OUTSIDE CATALOGUE", "NOVEL ALGORITHM")})
    return {"N": len(sel), "correct": sum(1 for r in sel if r.get("correct")), "X_a": xa, "X_b": xb}


def main():
    rs = rows()
    tests = load("results/ratio_tests.json")
    rates = load("results/arm_rates.json")
    report = {"mismatches": [], "checks": 0, "per_task": {}}
    for level in ("a", "b"):
        for t, rec in tests["levels"][level]["per_task"].items():
            c = {a: counts(rs, t, a) for a in ARMS}
            k = rec["K_arm"]
            mine = test(c["S"]["X_" + level], c["S"]["N"], c[k]["X_" + level], c[k]["N"])
            v = verdict(mine)
            report["per_task"][f"{t}|{level}"] = {"counts": c, "K": k, "R_hat": mine["R_hat"], "LB95": mine["LB95"],
                                                   "verdict": v}
            checks = [("X_S", rec["X_S"], c["S"]["X_" + level]), ("X_K", rec["X_K"], c[k]["X_" + level]),
                      ("N_S", rec["N_S"], c["S"]["N"]), ("N_K", rec["N_K"], c[k]["N"]), ("verdict", rec["verdict"], v)]
            if mine["estimable"] and rec.get("R_hat") is not None and mine["R_hat"] != math.inf:
                checks.append(("R_hat", round(rec["R_hat"], 9), round(mine["R_hat"], 9)))
            if mine["estimable"] and rec.get("LB95") is not None:
                checks.append(("LB95", round(rec["LB95"], 4), round(mine["LB95"], 4)))
            for name, a, b in checks:
                report["checks"] += 1
                if a != b:
                    report["mismatches"].append({"task": t, "level": level, "field": name, "results": a,
                                                 "rederived": b})
            for a in ARMS:
                ra = rates["level_a"][t][a]
                report["checks"] += 2
                if ra["N"] != c[a]["N"] or ra["X_a"] != c[a]["X_a"]:
                    report["mismatches"].append({"task": t, "arm": a, "field": "arm_rates", "results": [ra["N"], ra["X_a"]],
                                                 "rederived": [c[a]["N"], c[a]["X_a"]]})
    # placebo 1: arm labels shuffled within task (S vs K): significance should vanish
    rng = random.Random(123)
    plac = {}
    for t, rec in tests["levels"]["a"]["per_task"].items():
        k = rec["K_arm"]
        pool = [r for r in rs if r["task"] == t and r["arm"] in ("S", k)]
        flags = [1 if (r.get("correct") and r.get("ooc_screen") and r.get("is_first_of_distinct")) else 0 for r in pool]
        ns = sum(1 for r in pool if r["arm"] == "S")
        sig = 0
        for _ in range(100):
            idx = list(range(len(pool)))
            rng.shuffle(idx)
            xs = sum(flags[i] for i in idx[:ns])
            xk = sum(flags[i] for i in idx[ns:])
            if test(xs, ns, xk, len(pool) - ns)["p"] < 0.05:
                sig += 1
        plac[t] = {"frac_significant_of_100": sig / 100}
    report["placebo_arm_shuffle"] = plac
    # placebo 2: seeds scored as children leave level-b counts unchanged (no sample row equals a seed)
    import hashlib
    seeds = {}
    for p in (ROOT / "data").glob("seeds_*.json"):
        for s in json.loads(p.read_text()):
            seeds[hashlib.sha256(s["code"].encode()).hexdigest()] = s["id"]
    hits = [r["id"] for r in rs if r.get("code_sha256") in seeds and r.get("final_class") in
            ("KNOWN OUTSIDE CATALOGUE", "NOVEL ALGORITHM")]
    report["placebo_seeds_as_children"] = {"levelb_rows_identical_to_seed": len(hits), "unchanged": len(hits) == 0}
    # hash chain
    lines = [ln for ln in (ROOT / "commitments.log").read_text().splitlines() if ln.strip()]
    prev = "0" * 64
    ok = True
    for ln in lines:
        rec = json.loads(ln)
        ok &= rec["prev"] == prev
        prev = hashlib.sha256(ln.encode()).hexdigest()
    report["hash_chain_ok"] = ok
    report["ok"] = not report["mismatches"] and ok
    (ROOT / "audit/rederive_report.json").write_text(json.dumps(report, indent=1, default=str))
    print(json.dumps({"ok": report["ok"], "checks": report["checks"], "mismatches": report["mismatches"][:5],
                      "placebo": plac, "seeds": report["placebo_seeds_as_children"], "chain": ok}, default=str))
    sys.exit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
