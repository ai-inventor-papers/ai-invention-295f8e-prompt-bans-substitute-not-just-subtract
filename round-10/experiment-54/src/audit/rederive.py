#!/usr/bin/env python3
"""Independent re-derivation of every headline number (stdlib only; a separate code path that imports nothing from
src/). It reads the raw evaluator outputs (data/eval_rows.jsonl, data/decisions.jsonl), the committed probe file and
reference vectors, and the analysis outputs it checks (results/cells.json, p1.json, p2.json, p3.json), and writes
results/rederive.json.

Recomputed: agreement A_c with every catalogue rule, STOCHASTIC, the RF matcher, the mechanism class, the VALID rule's
probe-error part, an independent regex lexical check (L1 on the extracted program block), every cell's N / VALID /
L1 / mechanistic counts, the Jonckheere-Terpstra statistic (stdlib permutation + tie-corrected normal approximation),
both Newcombe intervals, and the P1/P2/P3 verdicts. Placebos that must FAIL: shuffled k labels, randomly swapped
lexical/mechanistic flags, random decision vectors, and a renamed best fit (which must still be classed BF).

Run: python3 audit/rederive.py
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import re
from bisect import bisect_right
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ERR = 65535
DET = ["BF", "FF", "WF", "AWF", "LF"]
CAT = DET + ["RF"]
T_CLASS = 0.95
Z = 1.959963984540054
NAME_CELLS = [f"NAME_{k}" for k in range(1, 6)]


# ------------------------------------------------------------------------------------------------ io
def jsonl(p: Path) -> list[dict]:
    out = []
    with p.open() as fh:
        for ln in fh:
            ln = ln.strip()
            if ln:
                try:
                    out.append(json.loads(ln))
                except json.JSONDecodeError:
                    pass
    return out


def load_rows() -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for r in jsonl(ROOT / "data" / "eval_rows.jsonl"):
        rows.setdefault(r["row_id"], {}).update(r)
    return rows


# ------------------------------------------------------------------------------------------------ instrument
def agree(a: list[int], b: list[int], idx: list[int] | None = None) -> float:
    ii = range(len(a)) if idx is None else idx
    n = ok = 0
    for i in ii:
        n += 1
        ok += (a[i] == b[i] and a[i] != ERR and b[i] != ERR)
    return ok / n if n else float("nan")


def A(prog: dict[int, list[int]], ref: dict[int, list[int]], ref_stoch: bool, idx=None) -> float:
    vals = []
    for s in sorted(prog):
        r = ref.get(s) if ref_stoch else ref.get(0)
        if r is None:
            r = ref[0]
        vals.append(agree(prog[s], r, idx))
    return sum(vals) / len(vals) if vals else float("nan")


def stochastic(prog: dict[int, list[int]]) -> bool:
    if 0 not in prog or 1 not in prog:
        return False
    a, b = prog[0], prog[1]
    return sum(x != y for x, y in zip(a, b)) / len(a) >= 0.01


def norm_rank(c: int, op: list[int]) -> float:
    below = sum(1 for o in op if o < c)
    eq = sum(1 for o in op if o == c)
    return (below + 0.5 * (eq - 1 if eq > 0 else 0)) / (len(op) - 1)


def ks(x: list[float], y: list[float]) -> float:
    xs, ys = sorted(x), sorted(y)
    best = 0.0
    for v in xs + ys:
        best = max(best, abs(bisect_right(xs, v) / len(xs) - bisect_right(ys, v) / len(ys)))
    return best


class Matcher:
    def __init__(self, states: list, meta: list, rf_ref: dict[int, list[int]]):
        self.idx = [i for i, m in enumerate(meta) if m["source"].startswith("uniform") and len(states[i][1]) >= 2]
        self.op = {i: states[i][1] for i in self.idx}
        self.cap = {i: states[i][3] for i in self.idx}
        self.ref_ranks = [norm_rank(rf_ref[s][i], self.op[i]) for s in sorted(rf_ref) for i in self.idx]
        self.ref_s2s = self.s2s(rf_ref)

    def s2s(self, v: dict[int, list[int]]) -> float:
        ks_ = sorted(v)
        vals = [sum(v[a][i] == v[b][i] for i in self.idx) / len(self.idx) for j, a in enumerate(ks_)
                for b in ks_[j + 1:]]
        return sum(vals) / len(vals) if vals else 1.0

    def match(self, v: dict[int, list[int]]) -> bool:
        seeds = sorted(v)
        used = [v[s][i] < self.cap[i] for s in seeds for i in self.idx]
        ranks = [norm_rank(v[s][i], self.op[i]) for s in seeds for i in self.idx]
        return (sum(used) / len(used) >= 0.95 and ks(ranks, self.ref_ranks) <= 0.10
                and self.s2s(v) <= self.ref_s2s + 0.15)


def classify(prog, refs, matcher, idx=None, t=T_CLASS) -> tuple[str, dict[str, float], bool, bool]:
    Ac = {c: A(prog, refs[c], False, idx) for c in DET}
    Ac["RF"] = A(prog, refs["RF"], True, idx)
    best = max(DET, key=lambda c: (Ac[c], -DET.index(c)))
    st = stochastic(prog)
    rfm = bool(st and matcher.match(prog))
    if Ac[best] >= t:
        return best, Ac, st, rfm
    if rfm:
        return "RF", Ac, st, rfm
    return "other", Ac, st, rfm


# ------------------------------------------------------------------------------------------------ lexical
NAMES = {"BF": ("best", "fit"), "FF": ("first", "fit"), "WF": ("worst", "fit"), "AWF": ("almost", "worst", "fit"),
         "LF": ("last", "fit"), "RF": ("random", "fit")}


def lex_hits(text: str) -> set[str]:
    """Names: case-insensitive, one optional separator (space, hyphen, underscore) between words. Abbreviations:
    case-sensitive standalone tokens. AWF spans are masked before the other rules are matched."""
    if not text:
        return set()
    hits = set()
    order = ["AWF"] + [r for r in NAMES if r != "AWF"]
    work = text
    for r in order:
        pats = [re.compile("[ _-]?".join(NAMES[r]), re.I), re.compile(r"(?<![0-9A-Za-z])" + r + r"(?![0-9A-Za-z])")]
        spans = [m.span() for p in pats for m in p.finditer(work)]
        if spans:
            hits.add(r)
        if r == "AWF":
            for a, b in spans:
                work = work[:a] + "\x00" * (b - a) + work[b:]
    return hits


# ------------------------------------------------------------------------------------------------ statistics
def wilson(k: int, n: int) -> tuple[float, float]:
    p = k / n
    den = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / den
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / den
    return max(0.0, c - h), min(1.0, c + h)


def newcombe_unpaired(k1, n1, k2, n2):
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    d = p1 - p2
    return d, d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)


def newcombe_paired(a, b, c, d):
    n = a + b + c + d
    p1, p2 = (a + b) / n, (a + c) / n
    l1, u1 = wilson(a + b, n)
    l2, u2 = wilson(a + c, n)
    den = (a + b) * (c + d) * (a + c) * (b + d)
    num = a * d - b * c
    if num > 0:
        num = max(num - n / 2, 0.0)
    phi = 0.0 if den == 0 else num / math.sqrt(den)
    g = p1 - p2
    lo = g - math.sqrt(max(0.0, (p1 - l1) ** 2 - 2 * phi * (p1 - l1) * (u2 - p2) + (u2 - p2) ** 2))
    hi = g + math.sqrt(max(0.0, (u1 - p1) ** 2 - 2 * phi * (u1 - p1) * (p2 - l2) + (p2 - l2) ** 2))
    return g, max(-1.0, lo), min(1.0, hi)


def jt_J(groups: list[list[int]]) -> float:
    J = 0.0
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            o_i, o_j = sum(groups[i]), sum(groups[j])
            z_i, z_j = len(groups[i]) - o_i, len(groups[j]) - o_j
            J += o_i * z_j + 0.5 * (o_i * o_j + z_i * z_j)
    return J


def jt_normal_p(groups: list[list[int]]) -> float | None:
    sizes = [len(g) for g in groups]
    y = [x for g in groups for x in g]
    N = len(y)
    if N < 3:
        return None
    t = list(Counter(y).values())
    EJ = (N * N - sum(s * s for s in sizes)) / 4
    v1 = (N * (N - 1) * (2 * N + 5) - sum(s * (s - 1) * (2 * s + 5) for s in sizes)
          - sum(u * (u - 1) * (2 * u + 5) for u in t)) / 72
    v2 = sum(s * (s - 1) * (s - 2) for s in sizes) * sum(u * (u - 1) * (u - 2) for u in t) / (36 * N * (N - 1) * (N - 2))
    v3 = sum(s * (s - 1) for s in sizes) * sum(u * (u - 1) for u in t) / (8 * N * (N - 1))
    var = v1 + v2 + v3
    if var <= 0:
        return None
    z = (jt_J(groups) - EJ) / math.sqrt(var)
    return 0.5 * math.erfc(z / math.sqrt(2))


def jt_perm_p(groups: list[list[int]], n_perm: int = 20_000, seed: int = 7) -> float | None:
    y = [x for g in groups for x in g]
    if not y or min(y) == max(y):
        return None
    sizes = [len(g) for g in groups]
    obs = jt_J(groups)
    rng = random.Random(seed)
    ge = 0
    for _ in range(n_perm):
        rng.shuffle(y)
        gs, p = [], 0
        for s in sizes:
            gs.append(y[p:p + s])
            p += s
        ge += jt_J(gs) >= obs - 1e-9
    return (ge + 1) / (n_perm + 1)


def clopper_upper(k: int, n: int, alpha: float = 0.05) -> float:
    """Upper limit of the two-sided Clopper-Pearson interval, by bisection on the binomial CDF."""
    if k >= n:
        return 1.0

    def cdf(p):
        return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))
    lo, hi = k / n, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if cdf(mid) > alpha / 2:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# ------------------------------------------------------------------------------------------------ main
def banned(cell: str, order: dict) -> list[str]:
    B = {int(k): v for k, v in order["B"].items()}
    if cell.startswith("NAME_"):
        return B[int(cell.split("_")[1])]
    if cell == "DESC_5":
        return list(order["S_desc"])
    return B[5]


def mech_flag(r: dict, Ac: dict, rfm: bool, B: list[str], t: float = T_CLASS) -> bool:
    if not r.get("valid"):
        return False
    for c in B:
        if c == "RF":
            if rfm:
                return False
        elif Ac[c] >= t:
            return False
    return True


def close(a, b, tol=1e-6) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(float(a) - float(b)) <= tol


def main() -> None:
    res: dict = {"mismatches": defaultdict(int), "examples": defaultdict(list)}

    def miss(kind: str, ex) -> None:
        res["mismatches"][kind] += 1
        if len(res["examples"][kind]) < 5:
            res["examples"][kind].append(ex)

    probe = json.loads((ROOT / "data" / "probes" / "P10.json").read_text())
    states, meta = probe["states"], probe["meta"]
    inf_idx = [i for i, m in enumerate(meta) if m["informative"]]
    gate = json.loads((ROOT / "results" / "instrument_gate.json").read_text())
    refs = {c: {int(s): v for s, v in sv.items()} for c, sv in gate["reference_vectors"].items()}
    matcher = Matcher(states, meta, refs["RF"])
    dec: dict[str, dict[int, list[int]]] = {}
    for d in jsonl(ROOT / "data" / "decisions.jsonl"):
        dec[d["row_id"]] = {int(s): v for s, v in d["vecs"].items()}
    rows = load_rows()
    orders = {json.loads(p.read_text())["model"]: json.loads(p.read_text())
              for p in sorted((ROOT / "predictions").glob("commit2_*.json"))}
    # ---- per-row instrument and lexical re-derivation
    re_rows: dict[str, dict] = {}
    for rid, r in rows.items():
        out = {"valid": bool(r.get("valid")), "class": "invalid", "A": None, "rfm": False, "lex": None}
        raw = r.get("raw_block") or ""
        out["lex"] = lex_hits(raw)
        if set(r.get("hits_program") or []) != out["lex"]:
            miss("lexical_hits", {"row_id": rid, "evaluator": r.get("hits_program"), "rederived": sorted(out["lex"])})
        v = dec.get(rid) or None
        if v is not None and r.get("error_type") == "ok":
            err = max(sum(1 for x in vv if x == ERR) / len(vv) for vv in v.values())
            valid_re = err <= 0.01
            if valid_re != bool(r.get("valid")):
                miss("valid_rule", {"row_id": rid, "evaluator": r.get("valid"), "rederived": valid_re})
            out["valid"] = valid_re
            cls, Ac, st, rfm = classify(v, refs, matcher)
            out.update(A=Ac, rfm=rfm, stoch=st)
            out["A_inf"] = {c: A(v, refs[c], c == "RF", inf_idx) for c in CAT}
            if valid_re:
                out["class"] = cls
                if cls != r.get("label"):
                    miss("class", {"row_id": rid, "evaluator": r.get("label"), "rederived": cls})
                for c in CAT:
                    if not close(Ac[c], (r.get("A") or {}).get(c), 2e-6):
                        miss("A_value", {"row_id": rid, "rule": c, "evaluator": (r.get("A") or {}).get(c),
                                         "rederived": Ac[c]})
                        break
        elif r.get("valid"):
            miss("valid_without_decisions", {"row_id": rid})
        re_rows[rid] = out
    res["n_rows"] = len(rows)
    res["n_rows_with_decisions"] = sum(1 for rid in rows if rid in dec)
    # ---- cell rates
    cells = json.loads((ROOT / "results" / "cells.json").read_text())
    by_mc: dict[tuple[str, str], list[str]] = defaultdict(list)
    for rid, r in rows.items():
        by_mc[(r["model"], r["cell"])].append(rid)
    rates = {}
    for (m, c), rids in sorted(by_mc.items()):
        B = banned(c, orders[m]) if m in orders else []
        vr = [x for x in rids if re_rows[x]["valid"]]
        lx = sum(1 for x in vr if not (re_rows[x]["lex"] & set(B)))
        mc = sum(1 for x in vr if mech_flag(re_rows[x], re_rows[x]["A"], re_rows[x]["rfm"], B))
        rates[f"{m}|{c}"] = {"N": len(rids), "VALID": len(vr), "L1": lx, "mech": mc, "banned": B}
        s = cells.get(f"{m}|{c}")
        if s is None:
            miss("cell_missing", f"{m}|{c}")
            continue
        for key, val in [("N", len(rids)), ("VALID", len(vr))]:
            if s[key] != val:
                miss("cell_count", {"cell": f"{m}|{c}", "field": key, "analysis": s[key], "rederived": val})
        if s["L1_valid"]["k"] != lx:
            miss("cell_L1", {"cell": f"{m}|{c}", "analysis": s["L1_valid"]["k"], "rederived": lx})
        if s["mech_valid"]["k"] != mc:
            miss("cell_mech", {"cell": f"{m}|{c}", "analysis": s["mech_valid"]["k"], "rederived": mc})
    res["cell_rates"] = rates
    # ---- P1 / P2 / P3
    p1 = json.loads((ROOT / "results" / "p1.json").read_text())
    p2 = json.loads((ROOT / "results" / "p2.json").read_text())
    p3 = json.loads((ROOT / "results" / "p3.json").read_text())
    p1_re, p2_re = {}, {}
    for m in sorted(orders):
        if not by_mc.get((m, "NAME_1")):
            continue

        def flags(cell, B):
            vr = [x for x in by_mc.get((m, cell), []) if re_rows[x]["valid"]]
            return [(not (re_rows[x]["lex"] & set(B)), mech_flag(re_rows[x], re_rows[x]["A"], re_rows[x]["rfm"], B))
                    for x in vr]
        out = {}
        f1 = flags("NAME_1", banned("NAME_1", orders[m]))
        out["a"] = bool(f1 and sum(a for a, _ in f1) / len(f1) >= 0.7 and sum(b for _, b in f1) / len(f1) >= 0.7)
        groups = [[int(b) for _, b in flags(c, banned(c, orders[m]))] for c in NAME_CELLS]
        J = jt_J(groups)
        pp = jt_perm_p(groups)
        pn = jt_normal_p(groups)
        jt_a = p1["per_model"][m]["b"]["jt"]
        if not close(J, jt_a.get("J"), 1e-9):
            miss("jt_J", {"model": m, "analysis": jt_a.get("J"), "rederived": J})
        if (pp is None) != (jt_a.get("p_perm") is None) or (pp is not None and abs(pp - jt_a["p_perm"]) > 0.01):
            miss("jt_p_perm", {"model": m, "analysis": jt_a.get("p_perm"), "rederived": pp})
        if pn is not None and jt_a.get("p_normal") is not None and abs(pn - jt_a["p_normal"]) > 1e-6:
            miss("jt_p_normal", {"model": m, "analysis": jt_a.get("p_normal"), "rederived": pn})
        out["b"] = bool(pp is not None and pp < 0.05)
        out["c"] = all(len(fl) > 0 and sum(a for a, _ in fl) / len(fl) >= 0.7
                       for fl in [flags(c, banned(c, orders[m])) for c in NAME_CELLS])
        absdiff = [abs(sum(a for a, _ in fl) - sum(b for _, b in fl)) / len(fl) if fl else None
                   for fl in [flags(c, banned(c, orders[m])) for c in NAME_CELLS]]
        out["disconfirm"] = all(x is not None and x <= 0.1 for x in absdiff)
        for part, cell in [("d", "NAME_5"), ("e", "HOLD_5")]:
            fl = flags(cell, banned(cell, orders[m]))
            if not fl:
                out[part] = False
                continue
            a = sum(1 for x, y in fl if x and y)
            b = sum(1 for x, y in fl if x and not y)
            c_ = sum(1 for x, y in fl if not x and y)
            d = sum(1 for x, y in fl if not x and not y)
            g, lo, hi = newcombe_paired(a, b, c_, d)
            _, ulo, uhi = newcombe_unpaired(a + b, len(fl), a + c_, len(fl))
            pa = p1["per_model"][m][part]
            for nm, mine, theirs in [("gap", g, pa.get("gap")), ("paired_lo", lo, (pa.get("paired_newcombe95") or
                                                                                    [None])[0]),
                                     ("paired_hi", hi, (pa.get("paired_newcombe95") or [None, None])[1]),
                                     ("unpaired_lo", ulo, (pa.get("unpaired_newcombe95") or [None])[0]),
                                     ("unpaired_hi", uhi, (pa.get("unpaired_newcombe95") or [None, None])[1])]:
                if not close(mine, theirs, 1e-9):
                    miss(f"p1_{part}_{nm}", {"model": m, "analysis": theirs, "rederived": mine})
            out[part] = bool(g >= 0.3 and lo > 0)
            out[f"{part}_values"] = {"abcd": [a, b, c_, d], "gap": g, "paired95": [lo, hi], "unpaired95": [ulo, uhi]}
        out["jt"] = {"J": J, "p_perm_20k": pp, "p_normal": pn}
        p1_re[m] = out
        # P2 (S_desc primary)
        Bd = list(orders[m].get("S_desc", []))
        fd = [y for _, y in flags("DESC_5", Bd)] if Bd else []
        fn = [y for _, y in flags("NAME_5", Bd)] if Bd else []
        if fd and fn:
            dd, lo, hi = newcombe_unpaired(sum(fd), len(fd), sum(fn), len(fn))
            pa = p2["per_model"][m]
            for nm, mine, theirs in [("diff", dd, pa.get("diff")), ("lo", lo, pa["newcombe95"][0]),
                                     ("hi", hi, pa["newcombe95"][1])]:
                if not close(mine, theirs, 1e-9):
                    miss(f"p2_{nm}", {"model": m, "analysis": theirs, "rederived": mine})
            p2_re[m] = {"diff": dd, "ci": [lo, hi], "holds": dd >= 0.2 and lo > 0, "disconfirms": dd <= 0}
    run = list(p1_re)
    cnt = {p: sum(p1_re[m][p] for m in run) for p in "bcde"}
    a_all = all(p1_re[m]["a"] for m in run)
    v1 = ("SUPPORTED" if a_all and all(cnt[p] >= 2 for p in "bcde") else
          ("DISCONFIRMED" if all(p1_re[m]["disconfirm"] for m in run) else "PARTIAL")) if run else "NOT_RUN"
    if v1 != p1["verdict"]["verdict"]:
        miss("p1_verdict", {"analysis": p1["verdict"]["verdict"], "rederived": v1})
    h2 = sum(v["holds"] for v in p2_re.values())
    z2 = sum(v["disconfirms"] for v in p2_re.values())
    v2 = "SUPPORTED" if h2 >= 2 else ("DISCONFIRMED" if z2 >= 2 else ("PARTIAL" if p2_re else "NOT_RUN"))
    if v2 != p2["verdict"]["verdict"]:
        miss("p2_verdict", {"analysis": p2["verdict"]["verdict"], "rederived": v2})
    audit = json.loads((ROOT / "results" / "p3_audit.json").read_text()) if (ROOT / "results" /
                                                                               "p3_audit.json").exists() else {}
    confirmed = set(audit.get("confirmed_novel_ids", []))
    p3_re = {}
    for (m, c), rids in sorted(by_mc.items()):
        k = sum(1 for x in rids if x in confirmed)
        cand = [x for x in rids if rows[x].get("valid") and rows[x].get("h_or3_excess") is not None and
                rows[x]["h_or3_excess"] <= 4.294 and rows[x].get("h_fsw5k_excess") is not None and
                rows[x]["h_fsw5k_excess"] <= 3.187 and (rows[x].get("corpus_max_agree") or 1.0) < 0.9]
        p3_re[f"{m}|{c}"] = {"N": len(rids), "candidates": len(cand), "confirmed": k, "share": k / len(rids),
                             "cp_upper95": clopper_upper(k, len(rids))}
        pc = p3["cells"].get(f"{m}|{c}", {})
        if pc.get("candidates") != len(cand) or pc.get("confirmed") != k:
            miss("p3_cell", {"cell": f"{m}|{c}", "analysis": [pc.get("candidates"), pc.get("confirmed")],
                             "rederived": [len(cand), k]})
    v3 = "SUPPORTED" if all(v["share"] <= 0.02 for v in p3_re.values()) else "NOT_SUPPORTED"
    if v3 != p3["verdict"]:
        miss("p3_verdict", {"analysis": p3["verdict"], "rederived": v3})
    res["verdicts_rederived"] = {"P1": v1, "P1_counts": cnt, "P1_a_all": a_all, "P2": v2, "P3": v3}
    res["p1_rederived"] = p1_re
    res["p2_rederived"] = p2_re
    res["p3_rederived"] = p3_re
    # ---- placebos (each must FAIL to show an effect)
    rng = random.Random(20261027)
    plac = {}
    sig = tot = 0
    for m in run:
        pool = []
        for c in NAME_CELLS:
            B = banned(c, orders[m])
            for x in by_mc.get((m, c), []):
                if re_rows[x]["valid"]:
                    pool.append(int(mech_flag(re_rows[x], re_rows[x]["A"], re_rows[x]["rfm"], B)))
        sizes = [sum(1 for x in by_mc.get((m, c), []) if re_rows[x]["valid"]) for c in NAME_CELLS]
        for _ in range(200):
            rng.shuffle(pool)
            gs, p = [], 0
            for s in sizes:
                gs.append(pool[p:p + s])
                p += s
            pv = jt_normal_p(gs)
            if pv is not None:
                tot += 1
                sig += pv < 0.05
    plac["shuffled_k_labels"] = {"n_tests": tot, "share_p_lt_0.05": sig / tot if tot else None,
                                 "fails_as_required": bool(tot and sig / tot <= 0.10)}
    gaps = []
    for m in run:
        B = banned("NAME_5", orders[m])
        fl = [(not (re_rows[x]["lex"] & set(B)), mech_flag(re_rows[x], re_rows[x]["A"], re_rows[x]["rfm"], B))
              for x in by_mc.get((m, "NAME_5"), []) if re_rows[x]["valid"]]
        for _ in range(200):
            sw = [(b, a) if rng.random() < 0.5 else (a, b) for a, b in fl]
            if sw:
                gaps.append(sum(a for a, _ in sw) / len(sw) - sum(b for _, b in sw) / len(sw))
    mg = sum(gaps) / len(gaps) if gaps else None
    plac["swapped_lex_mech_flags"] = {"mean_gap": mg, "fails_as_required": bool(mg is not None and abs(mg) < 0.05)}
    rand_cls = Counter()
    for j in range(50):
        v = {}
        for s in (0, 1, 2, 3):
            v[s] = [rng.choice(st[1] + [st[3]]) for st in states]
        rand_cls[classify(v, refs, matcher)[0]] += 1
    plac["random_decision_vectors"] = {"classes": dict(rand_cls), "fails_as_required": set(rand_cls) == {"other"}}
    bf_ren = {0: list(refs["BF"][0]), 1: list(refs["BF"][0])}
    code = "def priority(item, bins):\n    # tightest remaining room wins\n    return -(bins - item)\n"
    plac["renamed_best_fit"] = {"class": classify(bf_ren, refs, matcher)[0], "lexical_hits": sorted(lex_hits(code)),
                                "fails_as_required": classify(bf_ren, refs, matcher)[0] == "BF" and not lex_hits(code)}
    res["placebos"] = plac
    # ---- hash chain
    chain = []
    prev = hashlib.sha256(b"nov_r_iter10").hexdigest()
    for ln in (ROOT / "predictions" / "commitments.log").read_text().splitlines():
        e = json.loads(ln)
        payload = ROOT / e["payload_path"]
        ph = hashlib.sha256(payload.read_bytes()).hexdigest() if payload.exists() else None
        chain.append({"i": e["i"], "label": e["label"], "prev_ok": e["prev_line_sha256"] == prev,
                      "payload_ok": ph == e["payload_sha256"]})
        prev = hashlib.sha256(ln.encode()).hexdigest()
    res["hash_chain"] = chain
    res["mismatches"] = dict(res["mismatches"])
    res["examples"] = dict(res["examples"])
    res["n_mismatches_total"] = sum(res["mismatches"].values())
    res["placebos_all_fail_as_required"] = all(v["fails_as_required"] for v in plac.values())
    (ROOT / "results" / "rederive.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({"n_mismatches_total": res["n_mismatches_total"], "mismatches": res["mismatches"],
                      "verdicts": res["verdicts_rederived"], "placebos_ok": res["placebos_all_fail_as_required"],
                      "chain": [(c["label"], c["prev_ok"], c["payload_ok"]) for c in chain]}, default=str))


if __name__ == "__main__":
    main()
