#!/usr/bin/env python3
"""Independent re-derivation of the headline numbers from the RAW files (stdlib only, no imports from src/).

Reads data/rows_<task>.jsonl (generation rows), data/labels_final.jsonl (label per id), predictions/commit1.json (s*),
results/manual_reads.jsonl + data/adjudication_candidates.json (classes, cluster membership) and results/program_classes.json
(distinct ids only). Recomputes the OOC screen, the class propagation, X_a / X_b per task x arm, and the S-vs-K test with
EXACT integer binomial sums (a third implementation, after scipy in src/analysis.py and lgamma in audit/rederive.py).
Placebos that must FAIL: permuted arm labels, random OOC flags at the pooled rate, a constant baseline (K given S's rate).
Also checks that every decisive row is timestamped after the commit that governs it."""
import json, math, random
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
J = lambda p: json.loads((ROOT / p).read_text())  # noqa: E731
L = lambda p: [json.loads(x) for x in (ROOT / p).read_text().splitlines() if x.strip()]  # noqa: E731
LEVEL_B = ("KNOWN OUTSIDE CATALOGUE", "NOVEL ALGORITHM")


def tail_ge(x, m, p):          # exact P(X >= x), X ~ Bin(m, p); p a Fraction
    return float(sum(Fraction(math.comb(m, k)) * p ** k * (1 - p) ** (m - k) for k in range(x, m + 1)))


def test(xs, ns, xk, nk, lb=True):
    m = xs + xk
    if m == 0:
        return {"R_hat": None, "LB95": None, "p": 1.0}
    lo, hi = 0.0, 1.0                                    # one-sided CP lower bound: P(X >= xs | p) = 0.05
    for _ in range(45 if lb else 0):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if xs > 0 and tail_ge(xs, m, Fraction(mid).limit_denominator(10 ** 9)) < 0.05 else (lo, mid)
    plo = lo if xs > 0 else 0.0
    return {"R_hat": (xs / ns) / (xk / nk) if xk else math.inf, "LB95": plo * nk / (ns * (1 - plo)) if plo < 1 else math.inf,
            "p": tail_ge(xs, m, Fraction(ns, ns + nk))}


def main():
    sstar = {t: v["s_star"] for t, v in J("predictions/commit1.json")["s_star"].items()}
    labs = {x["id"]: x["label"] for x in L("data/labels_final.jsonl")}
    prog = J("results/program_classes.json")
    manual = {x["id"]: x["class"] for x in L("results/manual_reads.jsonl")}
    cls = dict(manual)                                   # propagate medoid class to unshown members (re-implemented)
    for ct in J("data/adjudication_candidates.json")["tasks"].values():
        for c in ct["clusters"].values():
            for mem in c["members"]:
                cls.setdefault(mem, manual.get(c["medoid"]))
    rows = [r for t in ("T2", "T03", "A3") for r in L(f"data/rows_{t}.jsonl")]
    out, counts = {"checks": [], "mismatch": []}, {}
    for r in rows:
        ooc = bool(r["correct"]) and (labs.get(r["id"]) == "other" or (r["nearest_known_sim"] is not None and r["nearest_known_sim"] < sstar[r["task"]]))
        d = (prog.get(r["id"]) or {}).get("distinct_id")
        c = counts.setdefault((r["task"], r["arm"]), {"N": 0, "correct": 0, "A": set(), "B": set()})
        c["N"] += 1; c["correct"] += bool(r["correct"])
        if ooc and d:
            c["A"].add(d)
            if cls.get(d) in LEVEL_B:
                c["B"].add(d)
    rt = J("results/ratio_tests.json")["levels"]
    for lvl, key in (("a", "A"), ("b", "B")):
        for t, rec in rt[lvl]["per_task"].items():
            S, K = counts[(t, "S")], counts[(t, rec["K_arm"])]
            mine = test(len(S[key]), S["N"], len(K[key]), K["N"])
            out["checks"].append({"task": t, "level": lvl, "K": rec["K_arm"], "X_S": len(S[key]), "N_S": S["N"],
                                  "X_K": len(K[key]), "N_K": K["N"], "R_hat": mine["R_hat"], "LB95": mine["LB95"]})
            for f, a, b in (("X_S", rec["X_S"], len(S[key])), ("X_K", rec["X_K"], len(K[key])), ("N_S", rec["N_S"], S["N"]),
                            ("LB95", None if rec["LB95"] is None else round(rec["LB95"], 3), None if mine["LB95"] is None else round(mine["LB95"], 3))):
                if a != b:
                    out["mismatch"].append([t, lvl, f, a, b])
    # secondary contrasts (as quoted in README) and arm L vs S's first N_L calls on T03
    for lvl, key in (("a", "A"), ("b", "B")):
        for t, rec in rt[lvl]["per_task"].items():
            for name, sec in rec["secondary"].items():
                a, b = name.split("(")[0].split("_vs_")
                a, b = (rec["K_arm"] if a == "K" else a), (rec["K_arm"] if b == "K" else b)
                A, B = counts[(t, a)], counts[(t, b)]
                mine = test(len(A[key]), A["N"], len(B[key]), B["N"])
                ok = (sec["X_S"], sec["X_K"]) == (len(A[key]), len(B[key])) and \
                    (sec["LB95"] is None or abs(round(sec["LB95"], 3) - round(mine["LB95"], 3)) < 1e-9)
                out.setdefault("secondary", []).append([t, lvl, name, len(A[key]), A["N"], len(B[key]), B["N"],
                                                        mine["R_hat"], mine["LB95"], ok])
                if not ok:
                    out["mismatch"].append([t, lvl, name])
    lrows = L("data/rows_L.jsonl")
    lA = {(prog.get(r["id"]) or {}).get("distinct_id") for r in lrows if r["correct"] and (labs.get(r["id"]) == "other" or (r["nearest_known_sim"] is not None and r["nearest_known_sim"] < sstar["T03"]))} - {None}
    lB = {d for d in lA if cls.get(d) in LEVEL_B}
    sfirst = sorted([r for r in rows if r["task"] == "T03" and r["arm"] == "S"], key=lambda r: r["slot"])[:len(lrows)]
    sA = {(prog.get(r["id"]) or {}).get("distinct_id") for r in sfirst if r["correct"] and (labs.get(r["id"]) == "other" or (r["nearest_known_sim"] is not None and r["nearest_known_sim"] < sstar["T03"]))} - {None}
    sB = {d for d in sA if cls.get(d) in LEVEL_B}
    lv = J("results/L_vs_S.json")
    out["L_vs_S"] = {"L": [len(lA), len(lB), len(lrows)], "S_first": [len(sA), len(sB), len(sfirst)],
                     "test_b": test(len(lB), len(lrows), len(sB), len(sfirst)),
                     "matches_results": [lv["L"]["X_a"], lv["L"]["X_b"], lv["S_first_nl"]["X_a"], lv["S_first_nl"]["X_b"]] == [len(lA), len(lB), len(sA), len(sB)]}
    if not out["L_vs_S"]["matches_results"]:
        out["mismatch"].append(["L_vs_S"])
    # placebos on T03 level a (the strongest real signal): each must FAIL to be significant / give R ~ 1
    rng, t = random.Random(2026), "T03"
    S, K = counts[(t, "S")], counts[(t, "EAP")]
    flags = [1] * len(S["A"]) + [0] * (S["N"] - len(S["A"])) + [1] * len(K["A"]) + [0] * (K["N"] - len(K["A"]))
    perm_sig, rand_sig = 0, 0
    for _ in range(200):
        rng.shuffle(flags)
        perm_sig += test(sum(flags[:S["N"]]), S["N"], sum(flags[S["N"]:]), K["N"], lb=False)["p"] < 0.05
        q = sum(flags) / len(flags)
        rand_sig += test(sum(rng.random() < q for _ in range(S["N"])), S["N"], sum(rng.random() < q for _ in range(K["N"])), K["N"], lb=False)["p"] < 0.05
    const = test(len(S["A"]), S["N"], round(len(S["A"]) * K["N"] / S["N"]), K["N"])
    out["placebo_T03_a"] = {"permuted_frac_sig": perm_sig / 200, "random_flags_frac_sig": rand_sig / 200,
                            "constant_baseline_R": const["R_hat"], "constant_baseline_LB95": const["LB95"]}
    # timestamps: decisive rows after commit1; Level-2 T03 rows (S >= 1500, EAP/BINT >= 750) after amendment3
    cl = {json.loads(x)["tag"]: json.loads(x)["utc"] for x in (ROOT / "commitments.log").read_text().splitlines() if x.strip()}
    late = [r["id"] for r in rows if r["utc"] < (cl["amendment3"] if r["task"] == "T03" and ((r["arm"] == "S" and r["slot"] >= 1500) or (r["arm"] in ("EAP", "BINT") and r["slot"] >= 750)) else cl["commit1"])]
    out["rows_before_governing_commit"] = len(late)
    out["ok"] = not out["mismatch"] and not late
    (ROOT / "audit/rederive_raw_report.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({"ok": out["ok"], "mismatch": out["mismatch"], "placebo": out["placebo_T03_a"], "late_rows": len(late),
                      "secondary": [(x[0], x[1], x[2], x[3], x[5], None if x[8] in (None, math.inf) else round(x[8], 2), x[9]) for x in out.get("secondary", []) if x[3] or x[5]],
                      "L_vs_S": out["L_vs_S"],
                      "checks": [(c["task"], c["level"], c["X_S"], c["X_K"], c["R_hat"] if c["R_hat"] in (None, math.inf) else round(c["R_hat"], 2),
                                  c["LB95"] if c["LB95"] in (None, math.inf) else round(c["LB95"], 2)) for c in out["checks"]]}, default=str))


if __name__ == "__main__":
    main()
