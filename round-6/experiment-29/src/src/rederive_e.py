#!/usr/bin/env python3
"""Independent re-derivation (stdlib + numpy only; imports NOTHING from this artifact's code).

Reads the raw files directly -- data/samples_raw.jsonl (generation rows) joined with data/labels.jsonl (labeller
rows) by sample_id -- and recomputes through its own code path: every headline count (Y_correct per task x precision x
arm), the primary exact McNemar p-values (binomial tail via math.comb), the attribution main effects and the frozen
verdicts; then compares them with results/*.json (target: 0 mismatches). Placebos: (i) precision labels swapped at
random within each slot pair (200 shuffles) -> McNemar p roughly uniform, rejection rate near the nominal level;
(ii) TWIN used in place of PN_a2 -> difference ~0, McNemar not significant. Also verifies the commitments.log chain
and that no decisive row predates commit #0. Output: results/rederive.json.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = {"T10": "union_find", "T2": "dijkstra", "T03": "full_sort"}
PRECS = ("W8A8", "W8A16", "W16A8", "W16A16")


def jl(p: Path) -> list[dict]:
    out = []
    if p.exists():
        for line in p.read_text().splitlines():
            if line.strip():
                out.append(json.loads(line))
    return out


def load() -> dict[tuple, dict]:
    labs = {r["sample_id"]: r for r in jl(ROOT / "data" / "labels.jsonl")}
    cells: dict[tuple, dict] = {}
    for r in jl(ROOT / "data" / "samples_raw.jsonl"):
        l = labs.get(r["sample_id"])
        if l is None:
            continue
        good = bool(l["passed"]) and l["label"] not in (DEFAULT[r["task"]], "invalid")
        key = (r["task"], r["precision"], r["arm"])
        slot = (r["template"], int(r["slot"]))
        cells.setdefault(key, {})[slot] = (int(good), l["label"], r.get("utc"))
    return cells


def binom_two_sided(b: int, c: int) -> float:
    n = b + c
    if n == 0 or b == c:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def pair(cells: dict, task: str, arm_a: str, pa: str, pb: str, arm_b: str | None = None):
    A = cells.get((task, pa, arm_a), {})
    B = cells.get((task, pb, arm_b or arm_a), {})
    ks = sorted(set(A) & set(B))
    a = [A[k][0] for k in ks]
    bb = [B[k][0] for k in ks]
    return a, bb


def mcn(a: list[int], b: list[int]) -> tuple[int, int, float]:
    n10 = sum(1 for x, y in zip(a, b) if x == 1 and y == 0)
    n01 = sum(1 for x, y in zip(a, b) if x == 0 and y == 1)
    return n10, n01, binom_two_sided(n10, n01)


def main() -> None:
    cells = load()
    res: dict = {"counts": {}, "checks": [], "mismatches": 0}
    for (t, p, arm), d in sorted(cells.items()):
        if arm in ("TWIN", "PN_a0.5", "PN_a1", "PN_a2", "PNF_a2") or arm.startswith("DITHER"):
            res["counts"][f"{t}|{p}|{arm}"] = {"n": len(d), "k_correct_off": sum(v[0] for v in d.values())}
    fac = json.loads((ROOT / "results" / "factorial.json").read_text()) if (ROOT / "results" / "factorial.json").exists() else {}
    for k, v in res["counts"].items():
        if k in fac:
            ok = fac[k]["N"] == v["n"] and fac[k]["k_correct_off"] == v["k_correct_off"]
            res["checks"].append({"what": f"count {k}", "rederived": v, "reported": [fac[k]["N"], fac[k]["k_correct_off"]],
                                  "match": ok})
            res["mismatches"] += (not ok)
    prim = json.loads((ROOT / "results" / "primary_E.json").read_text()) if (ROOT / "results" / "primary_E.json").exists() else {}
    hits, nulls = [], []
    thr = {"T10": 0.25, "T2": 0.15}
    for t in ("T10", "T2"):
        a, b = pair(cells, t, "PN_a2", "W8A8", "W16A16")
        if not a:
            continue
        n10, n01, pv = mcn(a, b)
        diff = (sum(a) - sum(b)) / len(a)
        hits.append(diff >= thr[t] and pv < 0.01)
        nulls.append(abs(diff) <= 0.10)
        rep = prim.get("tasks", {}).get(t, {})
        ok = (rep.get("table", {}).get("10") == n10 and rep.get("table", {}).get("01") == n01 and
              abs(rep.get("mcnemar", {}).get("p_two_sided", -1) - pv) < 1e-9 and abs(rep.get("diff", -9) - diff) < 1e-9)
        res["checks"].append({"what": f"primary McNemar {t}", "rederived": {"n_pairs": len(a), "n10": n10, "n01": n01,
                                                                            "p": pv, "diff": diff}, "match": ok})
        res["mismatches"] += (not ok)
        # placebo (i): swap precision labels at random within each slot pair
        rng = random.Random(20261021)
        ps = []
        for _ in range(200):
            aa, bb = [], []
            for x, y in zip(a, b):
                if rng.random() < 0.5:
                    x, y = y, x
                aa.append(x)
                bb.append(y)
            ps.append(mcn(aa, bb)[2])
        res[f"placebo_swap_{t}"] = {"rejection_rate_p_lt_0.05": float(np.mean(np.array(ps) < 0.05)),
                                    "rejection_rate_p_lt_0.01": float(np.mean(np.array(ps) < 0.01)),
                                    "mean_p": float(np.mean(ps)), "median_p": float(np.median(ps)),
                                    "fails_to_reject": float(np.mean(np.array(ps) < 0.01)) <= 0.05}
        # placebo (ii): TWIN in place of PN_a2
        a2, b2 = pair(cells, t, "TWIN", "W8A8", "W16A16")
        if a2:
            n10, n01, pv2 = mcn(a2, b2)
            res[f"placebo_twin_as_pn_{t}"] = {"diff": (sum(a2) - sum(b2)) / len(a2), "p": pv2, "n10": n10, "n01": n01,
                                              "fails_to_reject": pv2 >= 0.01}
    if len(hits) == 2:
        v = ("PRECISION EFFECT" if all(hits) else "PARTIAL" if any(hits) else
             "NO PRECISION EFFECT" if all(nulls) else "AMBIGUOUS")
        ok = v == prim.get("verdict_EMU")
        res["checks"].append({"what": "verdict", "rederived": v, "reported": prim.get("verdict_EMU"), "match": ok})
        res["mismatches"] += (not ok)
    # attribution main effects on common slots
    att = json.loads((ROOT / "results" / "attribution.json").read_text()) if (ROOT / "results" / "attribution.json").exists() else {}
    for t in ("T10", "T2"):
        cs = [cells.get((t, p, "PN_a2"), {}) for p in PRECS]
        if not all(cs):
            continue
        ks = sorted(set.intersection(*[set(c) for c in cs]))
        m = {p: sum(c[k][0] for k in ks) / len(ks) for p, c in zip(PRECS, cs)}
        ame = 0.5 * ((m["W8A8"] - m["W8A16"]) + (m["W16A8"] - m["W16A16"]))
        wme = 0.5 * ((m["W8A8"] - m["W16A8"]) + (m["W8A16"] - m["W16A16"]))
        rep = att.get("tasks", {}).get(t, {}).get("effects", {})
        ok = abs(rep.get("AME", -9) - ame) < 1e-9 and abs(rep.get("WME", -9) - wme) < 1e-9
        res["checks"].append({"what": f"AME/WME {t}", "rederived": {"AME": ame, "WME": wme, "n": len(ks), **m},
                              "match": ok})
        res["mismatches"] += (not ok)
    # commit chain + no decisive row before commit #0
    log = (ROOT / "commitments.log").read_text().splitlines() if (ROOT / "commitments.log").exists() else []
    prev = hashlib.sha256(b"iter6_E").hexdigest()
    breaks = 0
    c0 = None
    for line in log:
        if not line.strip():
            continue
        utc, rp, h, chain, tag = line.split()[:5]
        breaks += hashlib.sha256((prev + h + utc).encode()).hexdigest() != chain
        prev = chain
        if tag == "commit0" and c0 is None:
            c0 = utc
    first_dec = min((v[2] for (t, p, a), d in cells.items() if p in PRECS for v in d.values() if v[2]), default=None)
    res["commit_chain"] = {"lines": len(log), "breaks": breaks, "commit0_utc": c0, "first_factorial_row_utc": first_dec,
                           "no_decisive_row_before_commit0": (first_dec is None or c0 is None or first_dec > c0)}
    # unit cross (ban unit PN_a2 vs ban-free unit PNF_a2, same PN seeds, same slots) + its placebo
    uc = json.loads((ROOT / "results" / "unit_cross.json").read_text()) if (ROOT / "results" / "unit_cross.json").exists() else {}
    for t in ("T10", "T2"):
        for p, key in (("W16A16", "unit_in_W16A16"), ("W8A8", "unit_in_W8A8")):
            a, b = pair(cells, t, "PN_a2", p, p, arm_b="PNF_a2")
            if not a:
                continue
            n10, n01, pv = mcn(a, b)
            rep = uc.get("tasks", {}).get(t, {}).get(key, {})
            ok = rep.get("table", {}).get("10") == n10 and rep.get("table", {}).get("01") == n01 and \
                abs(rep.get("mcnemar", {}).get("p_two_sided", -1) - pv) < 1e-9
            res["checks"].append({"what": f"unit cross {t} {p}", "rederived": {"n": len(a), "ban": sum(a) / len(a),
                                  "banfree": sum(b) / len(b), "n10": n10, "n01": n01, "p": pv}, "match": ok})
            res["mismatches"] += (not ok)
            rng = random.Random(7)
            ps = []
            for _ in range(200):
                aa, bb = [], []
                for x, y in zip(a, b):
                    if rng.random() < 0.5:
                        x, y = y, x
                    aa.append(x)
                    bb.append(y)
                ps.append(mcn(aa, bb)[2])
            res[f"placebo_swap_unit_{t}_{p}"] = {"rejection_rate_p_lt_0.01": float(np.mean(np.array(ps) < 0.01)),
                                                 "rejection_rate_p_lt_0.05": float(np.mean(np.array(ps) < 0.05)),
                                                 "real_p": pv, "fails_to_reject": float(np.mean(np.array(ps) < 0.01)) <= 0.05}
    # post-hoc replication of exp27 (iteration 5): my IT5 rows vs exp27's own label rows, read straight from inputs/
    e27 = {r["sample_id"]: r for r in jl(ROOT / "inputs" / "exp27" / "data" / "labels.jsonl")}
    for t in ("T10", "T2"):
        for p in ("W16A16", "W8A8"):
            c = cells.get((t, p, "IT5_a2"), {})
            n = agree = 0
            for (w, k), v in c.items():
                r27 = e27.get(f"{t}|PN_a2|{w}|{k}")
                if r27 is None:
                    continue
                n += 1
                agree += v[1] == r27.get("label")
            if n:
                res[f"posthoc_it5_{t}_{p}"] = {"n": n, "Y_correct": sum(v[0] for v in c.values()) / len(c),
                                               "label_agreement_with_exp27": agree / n}
    # prompt grep audit: every row used one of exp19's 15 twin prompts of T10/T2/T03; no ban prompt anywhere
    pr = jl(ROOT / "data" / "prompts.jsonl")
    twin_sha = {r["prompt_sha256"] for r in pr if r["kind"] == "twin" and r["task"] in ("T10", "T2", "T03")}
    used = {r.get("prompt_sha256") for r in jl(ROOT / "data" / "samples_raw.jsonl")}
    ban_kinds = sorted({r["kind"] for r in pr if "ban" in r["kind"]})
    res["prompt_audit"] = {"n_prompts_used": len(used), "all_twin_prompts": used <= twin_sha,
                           "ban_kinds_in_prompt_file": ban_kinds,
                           "ban_prompt_used": bool(used & {r["prompt_sha256"] for r in pr if "ban" in r["kind"]})}
    (ROOT / "results" / "rederive.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({"mismatches": res["mismatches"], "n_checks": len(res["checks"]),
                      "commit_chain": res["commit_chain"],
                      **{k: v for k, v in res.items() if k.startswith("placebo")}}, indent=1))


if __name__ == "__main__":
    main()
