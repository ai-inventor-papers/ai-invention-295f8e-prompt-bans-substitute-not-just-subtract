#!/usr/bin/env python3
"""Independent re-derivation of the headlines from the raw files (stdlib + numpy; shares no code with src/).

Recomputes from data/samples.jsonl: every cell's n / pass / correct off-default count; the S-a selection, b:c and
exact McNemar p of every contrast; the S-b Mantel-Haenszel OR (hand-coded RBG); S-c b:c and one-sided p; the F1 share
(own code-start rule on decoded tokens); m from results/q_lik_raw.json. Placebos that must fail: site labels shuffled
within (task, alpha) (S-a pass rate over 200 shuffles); pair members swapped at random (McNemar rejection rate);
the MH indicator shuffled within task (share of CIs excluding 1).
Writes results/rederive.json with mismatches against results/*.json.
"""

from __future__ import annotations

import os

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):  # 5-CPU cgroup: avoid BLAS oversubscription
    os.environ.setdefault(_v, "2")

import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEF = {"T03": "full_sort", "T10": "union_find", "T2": "dijkstra", "T1": "bfs"}
CAT = {"T03": {"full_sort", "size_k_heap", "heapify_pop", "quickselect", "median_of_medians", "counting_sort"},
       "T10": {"bfs", "dfs", "union_find", "label_propagation"},
       "T2": {"dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"},
       "T1": {"bfs", "dfs", "bibfs", "iddfs", "astar_gbfs", "dijkstra"}}


def load(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def yv(r: dict) -> int:
    return int(bool(r["passed"]) and r["label"] in CAT[r["task"]] and r["label"] != DEF[r["task"]])


def binom_cdf(k: int, n: int) -> float:
    return sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n


def mcn2(b: int, c: int) -> float:
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * binom_cdf(min(b, c), n))


def mcn1(b: int, c: int) -> float:
    n = b + c
    return 1.0 if n == 0 else sum(math.comb(n, i) for i in range(b, n + 1)) / 2 ** n


def holm(ps: list[float]) -> list[float]:
    o = sorted(range(len(ps)), key=lambda i: ps[i])
    out = [0.0] * len(ps)
    run = 0.0
    for r, i in enumerate(o):
        run = max(run, min(1.0, (len(ps) - r) * ps[i]))
        out[i] = run
    return out


def mh(tables: list[tuple[int, int, int, int]]) -> tuple[float, float, float]:
    R = S = A = Bq = C = 0.0
    for a, b, c, d in tables:
        n = a + b + c + d
        if n < 2 or a + b == 0 or c + d == 0:
            continue
        r, s = a * d / n, b * c / n
        p, q = (a + d) / n, (b + c) / n
        R += r
        S += s
        A += p * r
        Bq += p * s + q * r
        C += q * s
    if R == 0 or S == 0:
        return float("nan"), float("nan"), float("nan")
    lor = math.log(R / S)
    se = math.sqrt(A / (2 * R * R) + Bq / (2 * R * S) + C / (2 * S * S))
    return math.exp(lor), math.exp(lor - 1.96 * se), math.exp(lor + 1.96 * se)


def main() -> None:
    rows = [r for r in load(ROOT / "data" / "samples.jsonl") if not str(r["arm"]).startswith(("SMOKE_", "ENG",
                                                                                              "TWIN_X"))]
    res: dict = {"n_rows": len(rows), "mismatches": []}
    cells = defaultdict(dict)
    for r in rows:
        cells[(r["task"], r["arm"])][(r["template"], int(r["k"]))] = r
    # cells
    cl = json.loads((ROOT / "results" / "cells.json").read_text())
    nck = 0
    for (t, arm), c in cells.items():
        k = f"{t}|{arm}"
        n = len(c)
        y = sum(yv(r) for r in c.values())
        p = sum(bool(r["passed"]) for r in c.values()) / n
        nck += 1
        if k not in cl or cl[k]["n"] != n or cl[k]["y"] != y or abs(cl[k]["pass"] - p) > 1e-9:
            res["mismatches"].append(f"cell {k}")
    res["cells_checked"] = nck

    # S-a
    def share(c, slots=None):
        v = [c[s] for s in (slots or c) if s in c]
        return (sum(yv(r) for r in v) / len(v)) if v else 0.0

    def passr(c):
        return sum(bool(r["passed"]) for r in c.values()) / len(c) if c else 0.0

    def s_a(cells_: dict) -> dict:
        out = {}
        allp = []
        for t in ("T03", "T10"):
            tw = cells_.get((t, "TWIN"), {})
            gate = 0.8 * passr(tw)
            cand = []
            for a in (1.0, 2.0, 4.0):
                for s in ("S0", "S4"):
                    c = cells_.get((t, f"{s}_a{a:g}"), {})
                    if c and passr(c) >= gate:
                        cand.append((-share(c), a, 0 if s == "S0" else 1, s))
            if not cand:
                out[t] = None
                continue
            cand.sort()
            _, a, _, s = cand[0]
            A = cells_[(t, f"{s}_a{a:g}")]
            con = {}
            for comp in ("S1", "S2", "S5"):
                B = cells_.get((t, f"{comp}_a{a:g}"), {})
                sh = sorted(set(A) & set(B))
                b = sum(1 for x in sh if yv(A[x]) == 1 and yv(B[x]) == 0)
                c_ = sum(1 for x in sh if yv(A[x]) == 0 and yv(B[x]) == 1)
                con[comp] = {"b": b, "c": c_, "p": mcn2(b, c_), "diff": share(A, sh) - share(B, sh)}
                allp.append((t, comp))
            out[t] = {"site": s, "alpha": a, "contrasts": con}
        ps = [out[t]["contrasts"][c]["p"] for t, c in allp]
        hp = holm(ps) if ps else []
        for (t, c), h in zip(allp, hp):
            out[t]["contrasts"][c]["p_holm"] = h
        passed = all(out.get(t) and all(v["diff"] >= 0.15 and v["p_holm"] < 0.05 for v in out[t]["contrasts"].values())
                     for t in ("T03", "T10"))
        return {"tasks": out, "pass": passed}

    sa = s_a(cells)
    sa_ref = json.loads((ROOT / "results" / "s_a.json").read_text())
    for t in ("T03", "T10"):
        mine = sa["tasks"].get(t)
        ref = sa_ref["tasks"].get(t, {}).get("selected")
        if (mine is None) != (ref is None) or (mine and (mine["site"] != ref["site"] or mine["alpha"] != ref["alpha"])):
            res["mismatches"].append(f"S-a selection {t}")
        if mine:
            for comp, v in mine["contrasts"].items():
                rv = sa_ref["tasks"][t]["contrasts"].get(comp, {})
                if rv.get("b") != v["b"] or rv.get("c") != v["c"] or abs(rv.get("p", -1) - v["p"]) > 1e-9:
                    res["mismatches"].append(f"S-a contrast {t}/{comp}")
    res["S_a"] = sa
    # S-a placebo: site labels shuffled within (task, alpha)
    rng = random.Random(0)
    n_pass = 0
    for rep in range(200):
        sh_cells = defaultdict(dict)
        groups = defaultdict(list)
        for (t, arm), c in cells.items():
            if arm == "TWIN" or "_a" not in arm:
                sh_cells[(t, arm)] = c
                continue
            site, a = arm.rsplit("_a", 1)
            if site in ("S0", "S4", "S1", "S2", "S5"):
                groups[(t, a)].append(arm)
            else:
                sh_cells[(t, arm)] = c
        for (t, a), arms in groups.items():
            for slot in {s for arm in arms for s in cells[(t, arm)]}:
                present = [arm for arm in arms if slot in cells[(t, arm)]]
                perm = present[:]
                rng.shuffle(perm)
                for src, dst in zip(present, perm):
                    sh_cells[(t, dst)][slot] = cells[(t, src)][slot]
        n_pass += s_a(sh_cells)["pass"]
    res["placebo_site_shuffle_S_a_pass_rate"] = n_pass / 200

    # S-b
    pr = [r for r in rows if r["task"] in ("T03", "T10", "T2") and r["site"] in ("S0", "S4", "S5", "S1", "S1E", "S2")
          and (r.get("realised_disp") or {}).get("disp_R35") is not None]
    disp = np.array([float(r["realised_disp"]["disp_R35"]) for r in pr])
    edges = np.quantile(disp, np.linspace(0, 1, 11)[1:-1])
    dec = np.searchsorted(edges, disp, side="right")

    def tables(ind):
        tb = []
        for t in ("T03", "T10", "T2"):
            for d in range(10):
                a = b = c = dd = 0
                for r, de, e in zip(pr, dec, ind):
                    if r["task"] != t or de != d:
                        continue
                    y = yv(r)
                    if e and y:
                        a += 1
                    elif e:
                        b += 1
                    elif y:
                        c += 1
                    else:
                        dd += 1
                tb.append((a, b, c, dd))
        return tb
    ind = [r["site"] in ("S0", "S4") for r in pr]
    orr, lo, hi = mh(tables(ind))
    sb_ref = json.loads((ROOT / "results" / "s_b.json").read_text())["primary"]["mh"]
    if not (abs(orr - sb_ref["or"]) < 1e-6 * max(1, orr)):
        res["mismatches"].append("S-b OR")
    res["S_b"] = {"or": orr, "ci": [lo, hi]}
    exc = 0
    for rep in range(200):
        ind2 = ind[:]
        for t in ("T03", "T10", "T2"):
            ii = [i for i, r in enumerate(pr) if r["task"] == t]
            vals = [ind2[i] for i in ii]
            rng.shuffle(vals)
            for i, v in zip(ii, vals):
                ind2[i] = v
        _, l2, _ = mh(tables(ind2))
        exc += (l2 == l2 and l2 > 1)
    res["placebo_mh_indicator_shuffle_ci_excludes_1"] = exc / 200

    # pair-swap placebo: S0 vs S1 at every alpha, members swapped at random per slot
    rej = tot = 0
    for rep in range(100):
        for t in ("T03", "T10"):
            for a in (1.0, 2.0, 4.0):
                A = cells.get((t, f"S0_a{a:g}"), {})
                B = cells.get((t, f"S1_a{a:g}"), {})
                sh = sorted(set(A) & set(B))
                b = c = 0
                for s in sh:
                    x, z = (A[s], B[s]) if rng.random() < 0.5 else (B[s], A[s])
                    b += yv(x) == 1 and yv(z) == 0
                    c += yv(x) == 0 and yv(z) == 1
                tot += 1
                rej += mcn2(b, c) < 0.05
    res["placebo_pair_swap_rejection_rate"] = rej / max(1, tot)

    # S-c
    sc_ref = json.loads((ROOT / "results" / "s_c.json").read_text())
    for t in ("T03", "T10", "T2"):
        tw = cells.get((t, "TWIN"), {})
        for a in (1.0, 2.0, 4.0):
            S3 = cells.get((t, f"S3_a{a:g}"), {})
            if not S3:
                continue
            sh = sorted(set(S3) & set(tw))
            b = sum(1 for s in sh if yv(S3[s]) == 1 and yv(tw[s]) == 0)
            c = sum(1 for s in sh if yv(S3[s]) == 0 and yv(tw[s]) == 1)
            ref = next((x for x in sc_ref.get(t, {}).get("by_dose", []) if x["alpha"] == a), {})
            if ref.get("b") != b or ref.get("c") != c or abs(ref.get("p_one_sided", -1) - mcn1(b, c)) > 1e-9:
                res["mismatches"].append(f"S-c {t}/{a}")
    # F1 (own code-start rule)
    try:
        from transformers import AutoTokenizer

        snap = next((Path(__import__("os").environ.get("HF_HUB_CACHE", "")) / "models--Qwen--Qwen3-8B" /
                     "snapshots").glob("b968826d*"))
        tok = AutoTokenizer.from_pretrained(str(snap))
        twin = {(r["task"], r["template"], int(r["k"])): r for r in rows if r["arm"] == "TWIN"}
        n = e = 0
        for r in rows:
            if r["arm"] == "TWIN" or r["site"] in ("TOP5", "TOP3"):
                continue
            tw = twin.get((r["task"], r["template"], int(r["k"])))
            if tw is None or r["label"] in ("invalid", "unresolved") or tw["label"] in ("invalid", "unresolved") or \
                    r["label"] == tw["label"] or not r.get("valid", True) or not tw.get("valid", True):
                continue
            text = ""
            cs = None
            seen = False
            for i, tid in enumerate(tw["token_ids"][:64]):
                s = tok.decode([tid])
                text += s
                if not seen and "```" in s:
                    seen = True
                    if "\n" in s[s.find("```"):]:
                        cs = i + 1
                        break
                    continue
                if seen and "\n" in s:
                    cs = i + 1
                    break
            if cs is None:
                continue
            a_, b_ = tw["token_ids"], r["token_ids"]
            fd = next((i for i in range(min(len(a_), len(b_))) if a_[i] != b_[i]), min(len(a_), len(b_)))
            n += 1
            e += (fd - cs) < 32
        f1_ref = json.loads((ROOT / "results" / "f1.json").read_text())["decision"]
        res["F1"] = {"n": n, "early": e, "share": e / n if n else None}
        if f1_ref["n_label_changing_pairs"] != n or f1_ref["n_first_div_lt_32"] != e:
            res["mismatches"].append("F1")
    except Exception as ex:  # noqa: BLE001
        res["F1_error"] = str(ex)
    # F2 m
    qp = ROOT / "results" / "q_lik_raw.json"
    if qp.exists():
        q = json.loads(qp.read_text())["rows"]
        f2r = json.loads((ROOT / "results" / "f2.json").read_text())
        mm = {}
        for t in ("T2", "T03", "T1"):
            d, ru = f2r.get(t, {}).get("default"), f2r.get(t, {}).get("r_u")
            if not d or not ru:
                continue
            per = []
            for w in ("W1", "W2", "W3", "W4", "W5"):
                a = [x["lp48"] for x in q if x["task"] == t and x["alg"] == d and x["w"] == w]
                b = [x["lp48"] for x in q if x["task"] == t and x["alg"] == ru and x["w"] == w]
                if a and b:
                    per.append(sum(a) / len(a) - sum(b) / len(b))
            mm[t] = sum(per) / len(per) if per else None
            if mm[t] is not None and abs(mm[t] - f2r[t]["m"]) > 1e-6:
                res["mismatches"].append(f"F2 {t}")
        res["F2_m"] = mm
    res["n_mismatches"] = len(res["mismatches"])
    (ROOT / "results" / "rederive.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: v for k, v in res.items() if k not in ("S_a",)}, indent=1, default=str)[:3000])


if __name__ == "__main__":
    sys.exit(main())
