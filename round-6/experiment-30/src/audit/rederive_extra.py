#!/usr/bin/env python3
"""Second independent re-derivation (stdlib only; shares no code with src/ or audit/rederive.py) of the headline
numbers that audit/rederive.py does not cover, read from the raw files:
  - F2 m_fork on T2/T03/T1 from results/q_lik_raw.json per-token arrays (own fork detection on the token ids'
    log-probs), with a placebo that pairs each default program with another DEFAULT program (median fork -> ~0);
  - S-d paired flips (push vs the S0 random control, banned-set avoidance among correct programs) for T03 top-3
    alpha 2/4 and T1 alpha 4, from data/samples_raw.jsonl + data/labels.jsonl + data/labels_k7.jsonl, with a
    placebo that swaps the two members of every pair at random (rejection rate must stay near or below 0.05);
  - T03 top-5 push composition at alpha 1 (quickselect share);
  - decisive row count, correct-program count, novelty count (audit pool + manual pass) and total OpenRouter spend.
Writes results/rederive_extra.json and compares with the analysis outputs.
"""

from __future__ import annotations

import json
import math
import random
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def jl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def p_two(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def main() -> None:
    out: dict = {"mismatches": []}
    # ---------------- F2 m_fork
    q = json.loads((ROOT / "results" / "q_lik_raw.json").read_text())["rows"]
    f2 = json.loads((ROOT / "results" / "f2.json").read_text())
    rng = random.Random(1)
    forks: dict = {}
    for t in ("T2", "T03", "T1"):
        d, ru = f2[t]["default"], f2[t]["r_u"]
        vals, plac = [], []
        for w in ("W1", "W2", "W3", "W4", "W5"):
            A = [x["lp_tokens"] for x in q if x["task"] == t and x["alg"] == d and x["w"] == w]
            B = [x["lp_tokens"] for x in q if x["task"] == t and x["alg"] == ru and x["w"] == w]
            for a in A:
                for b in B:
                    j = 0
                    while j < min(len(a), len(b)) and abs(a[j] - b[j]) <= 1e-4:
                        j += 1
                    if j < min(len(a), len(b)):
                        vals.append(a[j] - b[j])
            # placebo: default vs another default program (same algorithm): no systematic margin
            for i, a in enumerate(A):
                b = A[rng.randrange(len(A))]
                if b is a:
                    continue
                j = 0
                while j < min(len(a), len(b)) and abs(a[j] - b[j]) <= 1e-4:
                    j += 1
                if j < min(len(a), len(b)):
                    plac.append(a[j] - b[j])
        med = statistics.median(vals) if vals else None
        forks[t] = {"m_fork": med, "n_pairs": len(vals), "placebo_default_vs_default_median": statistics.median(plac)
                    if plac else None, "placebo_n": len(plac)}
        if med is None or abs(med - (f2[t].get("m_fork_median") or 1e9)) > 1e-6:
            out["mismatches"].append(f"m_fork {t}")
    out["F2_m_fork"] = forks
    # ---------------- S-d paired flips
    raw = {f"{r['task']}|{r['template']}|{r['arm']}|{r['k']}": r for r in jl(ROOT / "data" / "samples_raw.jsonl")}
    lab = {r["key"]: r for r in jl(ROOT / "data" / "labels.jsonl")}
    k7 = {r["key"]: r for r in jl(ROOT / "data" / "labels_k7.jsonl")}
    banned = json.loads((ROOT / "predictions" / "banned_sets.json").read_text())["sets"]

    def zmap(task: str, arm: str, setting: str) -> dict:
        outz = {}
        B = set(banned[setting]["banned"])
        for key, r in raw.items():
            if r["task"] != task or r["arm"] != arm:
                continue
            if task == "T1":
                L = k7.get(key)
                ok, lb = (bool(L["passed"]), L["label_k7"]) if L else (False, None)
            else:
                L = lab.get(key)
                ok, lb = (bool(L["passed"]), L["label"]) if L else (False, None)
            outz[(r["template"], int(r["k"]))] = int(ok and lb not in B)
        return outz

    sd_ref = json.loads((ROOT / "results" / "s_d.json").read_text())
    sd = {}
    for setting, task, site, a in (("T03|TOP3", "T03", "TOP3", "2"), ("T03|TOP3", "T03", "TOP3", "4"),
                                   ("T1|TOP5", "T1", "TOP5", "4")):
        P = zmap(task, f"{site}_a{a}", setting)
        R = zmap(task, f"S0_a{a}", setting)
        sh = sorted(set(P) & set(R))
        b = sum(1 for s in sh if P[s] == 1 and R[s] == 0)
        c = sum(1 for s in sh if P[s] == 0 and R[s] == 1)
        rej = 0
        for _ in range(500):
            bb = cc = 0
            for s in sh:
                x, y = (P[s], R[s]) if rng.random() < 0.5 else (R[s], P[s])
                bb += x == 1 and y == 0
                cc += x == 0 and y == 1
            rej += p_two(bb, cc) < 0.05
        ref = sd_ref[setting]["arms"][a]["push_vs_random_control"]
        sd[f"{setting}|a{a}"] = {"b": b, "c": c, "p": p_two(b, c), "n_shared": len(sh),
                                 "placebo_pair_swap_rejection_rate": rej / 500}
        if (ref["b"], ref["c"]) != (b, c):
            out["mismatches"].append(f"S-d {setting} a{a}")
    out["S_d_flips"] = sd
    # T03 top-5 at alpha 1: composition of correct programs
    comp = {}
    for key, r in raw.items():
        if r["task"] == "T03" and r["arm"] == "TOP5_a1" and lab.get(key, {}).get("passed"):
            comp[lab[key]["label"]] = comp.get(lab[key]["label"], 0) + 1
    out["T03_TOP5_a1_correct_composition"] = comp
    # ---------------- counts, novelty, spend
    dec = [r for r in raw.values() if not str(r["arm"]).startswith(("SMOKE_", "ENG", "TWIN_X"))]
    out["n_decisive_rows"] = len(dec)
    pool = json.loads((ROOT / "audit" / "novelty_audit_pool.json").read_text())["records"]
    manual = {r["id"]: r["verdict"] for r in jl(ROOT / "audit" / "manual_pass.jsonl")}
    out["novelty"] = {"n_unique_correct_other": len(pool),
                      "n_judge_and_manual_novel": sum(1 for x in pool if x.get("resolved_class") == "NOVEL ALGORITHM"
                                                      and manual.get(x["id"]) == "NOVEL ALGORITHM")}
    spend = 0.0
    for f in ("openrouter_cost_paths.json", "openrouter_cost_k7.json"):
        p = ROOT / "results" / f
        if p.exists():
            spend += json.loads(p.read_text()).get("total_usd", 0.0)
    for l in (ROOT / "logs" / "openrouter_spend.jsonl").read_text().splitlines() if \
            (ROOT / "logs" / "openrouter_spend.jsonl").exists() else []:
        if l.strip():
            spend += json.loads(l).get("cost", 0.0) or 0.0
    spend += json.loads((ROOT / "audit" / "novelty_audit_pool.json").read_text())["budget"]["total_usd"]
    out["total_openrouter_usd"] = round(spend, 4)
    out["n_mismatches"] = len(out["mismatches"])
    (ROOT / "results" / "rederive_extra.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
