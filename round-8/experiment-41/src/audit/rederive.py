#!/usr/bin/env python3
"""Stdlib-only re-derivation of every K3 headline from raw rows (no numpy, no project imports), with placebos.

Re-derives: total effects and top-10 lists (results/circuit_*.json exact rows), kept edges, faithfulness means,
node pass flags with Holm over 20 (data/validation_rows_*.jsonl, exact sign-flip enumeration up to n = 22, else a
seeded 200,000-draw Monte Carlo), generation counts and exact McNemar (data/gen_raw_*.jsonl + gen_labels_*.jsonl),
motif shares for Gemma and Qwen. Placebos that must FAIL the thresholds: shuffled node labels in the validation rows
(node row swapped with one of its random draws), a random top-10 (node shares re-ranked at random), and shuffled arm
labels in generation. Writes results/rederive.json and prints mismatches against results/summary.json."""

from __future__ import annotations

import json
import math
import random
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "results"
D = ROOT / "data"


def jl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def mean(x: list[float]) -> float:
    return sum(x) / len(x) if x else float("nan")


def sign_flip(d: list[float], seed: int = 0) -> float:
    n = len(d)
    if n == 0:
        return 1.0
    obs = sum(d)
    tol = 1e-9 * max(1.0, sum(abs(v) for v in d))
    if n <= 22:
        h = n // 2
        a = [sum(s * v for s, v in zip(sg, d[:h])) for sg in product((-1, 1), repeat=h)]
        b = sorted(sum(s * v for s, v in zip(sg, d[h:])) for sg in product((-1, 1), repeat=n - h))
        import bisect
        ge = sum(len(b) - bisect.bisect_left(b, obs - x - tol) for x in a)
        return ge / 2 ** n
    rng = random.Random(seed)
    m = 200_000
    ge = sum(1 for _ in range(m) if sum(v if rng.random() < 0.5 else -v for v in d) >= obs - tol)
    return (ge + 1) / (m + 1)


def holm(ps: list[float]) -> list[float]:
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj = [0.0] * len(ps)
    run = 0.0
    for r, i in enumerate(order):
        run = max(run, (len(ps) - r) * ps[i])
        adj[i] = min(1.0, run)
    return adj


def binom_sf(k: int, n: int) -> float:
    return sum(math.comb(n, j) for j in range(k, n + 1)) / 2 ** n


def validation(name: str, placebo: bool = False) -> dict | None:
    rows = jl(D / f"validation_rows_{name}.jsonl")
    selp = R / f"selection_{name}.json"
    if not rows or not selp.exists():
        return None
    sel = json.loads(selp.read_text())
    rng = random.Random(7)
    ps = []
    for mode in ("ablate", "steer"):
        for k in sel["top10"]:
            d = []
            for r in rows:
                v = r["res"].get(f"{mode}|{k}|node")
                rv = [r["res"][f"{mode}|{k}|r{j}"] for j in range(50) if f"{mode}|{k}|r{j}" in r["res"]]
                if v is None or not rv:
                    continue
                if placebo:                       # node label shuffled into the random pool
                    j = rng.randrange(len(rv))
                    v, rv = rv[j], rv[:j] + [v] + rv[j + 1:]
                d.append(v - mean(rv))
            ps.append(sign_flip(d))
    adj = holm(ps)
    both = sum(1 for i in range(10) if adj[i] < 0.05 and adj[10 + i] < 0.05)
    return {"p": ps, "p_holm20": adj, "n_pass_both": both}


def generation(name: str, placebo: bool = False) -> dict | None:
    raw = {r["row_id"]: r for r in jl(D / f"gen_raw_{name}.jsonl")}
    lab = {r["sid"]: r for r in jl(D / f"gen_labels_{name}.jsonl")}
    if not raw:
        return None
    tg = ("prim_heap", "prim_array") if name.startswith("C1") else ("dfs",)
    out = {}
    for cond in ("PREFILL", "FREE"):
        cells: dict = {}
        for rid, r in raw.items():
            if r["condition"] != cond or rid not in lab:
                continue
            cells.setdefault((r["template"], r["slot"]), {})[r["arm"]] = (lab[rid]["label"] in tg and
                                                                          bool(lab[rid]["passed"]))
        if not cells:
            continue
        rng = random.Random(11)
        if placebo:
            for s, c in cells.items():
                vals = [c.get(a) for a in ("TWIN", "TOP5", "RAND5")]
                rng.shuffle(vals)
                cells[s] = dict(zip(("TWIN", "TOP5", "RAND5"), vals))
        cnt = {a: sum(1 for c in cells.values() if c.get(a)) for a in ("TWIN", "TOP5", "RAND5")}
        b = sum(1 for c in cells.values() if c.get("TOP5") and not c.get("RAND5"))
        cc = sum(1 for c in cells.values() if c.get("RAND5") and not c.get("TOP5"))
        out[cond] = {"correct_target": cnt, "b": b, "c": cc,
                     "mcnemar_p": min(1.0, 2 * binom_sf(max(b, cc), b + cc)) if b + cc else 1.0,
                     "mcnemar_p_one_sided": binom_sf(b, b + cc) if b + cc else 1.0,
                     "plus_vs_twin": cnt["TOP5"] - cnt["TWIN"]}
    return out


def circuit(name: str, placebo: bool = False) -> dict | None:
    p = R / f"circuit_{name}.json"
    if not p.exists():
        return None
    r = json.loads(p.read_text())
    te = mean([x["TE"] for x in r["pairs"]])
    pool = {e["node"]: mean(e["noise_per_pair"]) for e in r["exact"]}
    for e in r.get("reliability_rows", []):
        pool.setdefault(e["node"], mean(e["noise_per_pair"]))
    for e in r.get("exact_extended", []):
        pool.setdefault(e["node"], mean(e["noise_per_pair"]))
    keys = list(pool)
    if placebo:
        random.Random(3).shuffle(keys)
        top10 = keys[:10]
    else:
        top10 = sorted(keys, key=lambda k: -abs(pool[k]))[:10]
    thr = 0.05 * te
    kept = sorted((e["sender"], e["receiver"]) for e in r.get("edges_all", []) if abs(mean(e["per_pair"])) >= thr)
    return {"TE_mean": te, "top10": top10, "top10_match": top10 == r["top10"], "n_edges_kept": len(kept),
            "edges_match": kept == sorted((e["sender"], e["receiver"]) for e in r.get("edges_kept", []))}


def motif(rows: list[dict], idx: list[int], cmap: dict | None = None) -> dict:
    tot = {"COND": 0.0, "SPEC": 0.0, "OPEN": 0.0, "DEC": 0.0}
    for e in rows:
        cl = e["node"].split("|")[3]
        cl = (cmap or {}).get(cl, cl)
        tot[cl] += abs(mean([e["noise_per_pair"][i] for i in idx]))
    s = sum(tot.values()) or 1e-12
    return {k: v / s for k, v in tot.items()}


def verify_chain() -> dict:
    """Recompute each commit's sha256 from predictions/<name>.json and check the prev links against commitments.log;
    also check that no validation row predates commit1 and no steered program predates commit2."""
    import hashlib
    lines = [l.split() for l in (ROOT / "commitments.log").read_text().splitlines() if l.strip()]
    rows, prev = [], "0" * 64
    for utc, name, h, pv in lines:
        rec = json.loads((ROOT / "predictions" / f"{name}.json").read_text())
        body = json.dumps({"name": name, "utc": rec["utc"], "prev": rec["prev"], "payload": rec["payload"]},
                          sort_keys=True, default=str)
        rows.append({"name": name, "utc": utc, "prev_link_ok": pv == f"prev={prev}", "hash_recomputed_ok":
                     hashlib.sha256(body.encode()).hexdigest() == h})
        prev = h
    t = {r["name"]: r["utc"] for r in rows}
    first_val = min((r["utc"] for f in sorted(D.glob("validation_rows_*.jsonl")) for r in jl(f)), default=None)
    first_gen = min((r["utc"] for f in sorted(D.glob("gen_raw_*.jsonl")) for r in jl(f)), default=None)
    return {"commits": rows, "all_links_ok": all(r["prev_link_ok"] for r in rows),
            "all_hashes_ok": all(r["hash_recomputed_ok"] for r in rows),
            "first_validation_row_after_commit1": (first_val or "z") > t.get("commit1", ""),
            "first_program_after_commit2": (first_gen or "z") > t.get("commit2", ""),
            "first_validation_row_utc": first_val, "first_program_utc": first_gen}


def main() -> None:
    out: dict = {"circuits": {}, "validation": {}, "generation": {}, "placebos": {}}
    out["commit_chain"] = verify_chain()
    for n in ("C1forced", "C2a", "C1nat", "C1mix", "C1natB"):
        c = circuit(n)
        if c:
            out["circuits"][n] = c
            out["placebos"][f"random_top10_{n}"] = circuit(n, placebo=True)["top10_match"]
    for n in ("C1forced", "C2a", "C1nat"):
        v = validation(n)
        if v:
            out["validation"][n] = v
            pv = validation(n, placebo=True)
            out["placebos"][f"shuffled_node_labels_{n}"] = {"n_pass_both": pv["n_pass_both"],
                                                           "fails_threshold": pv["n_pass_both"] < 5}
    for n in ("C1forced", "C2a"):
        g = generation(n)
        if g:
            out["generation"][n] = g
            pg = generation(n, placebo=True)
            out["placebos"][f"shuffled_arms_{n}"] = {
                k: {"plus_vs_twin": v["plus_vs_twin"], "mcnemar_p": v["mcnemar_p"],
                    "fails_threshold": not (v["plus_vs_twin"] >= 6 and v["mcnemar_p"] < 0.05)} for k, v in pg.items()}
    g = json.loads((ROOT / "inputs" / "exp38" / "results" / "g1_pathpatch.json").read_text())
    gm = {"FORK": "DEC", "CSTAR": "OPEN", "SPEC": "SPEC", "COND": "COND"}
    out["motif_gemma"] = motif(g["exact"], list(range(15)), gm)
    for n in ("C1mix", "C1forced", "C1nat"):
        p = R / f"circuit_{n}.json"
        if p.exists():
            r = json.loads(p.read_text())
            out[f"motif_{n}"] = motif([e for e in r["exact"] if e["in_top40_atp"] or e["calibration"]],
                                      list(range(r["n_pairs"])))
    sp = R / "summary.json"
    mism = []
    if sp.exists():
        s = json.loads(sp.read_text())
        for n, v in out["validation"].items():
            ref = s.get("validation", {}).get(n, {}).get("n_pass_both_holm20")
            if ref is not None and ref != v["n_pass_both"]:
                mism.append(f"validation {n}: rederived {v['n_pass_both']} vs summary {ref}")
        for n, gg in out["generation"].items():
            for cond, v in gg.items():
                ref = s.get("generation", {}).get(n, {}).get(cond, {}).get("arms", {})
                for arm, k in v["correct_target"].items():
                    if arm in ref and ref[arm]["correct_target"] != k:
                        mism.append(f"generation {n} {cond} {arm}: {k} vs {ref[arm]['correct_target']}")
        mq = s.get("motif", {}).get("gemma_check", {}).get("shares", {})
        if mq and abs(mq.get("DEC", 0) - out["motif_gemma"]["DEC"]) > 1e-6:
            mism.append("gemma motif share differs")
        for n, c in out["circuits"].items():
            if not c["top10_match"]:
                mism.append(f"circuit {n}: top-10 differs")
            if not c["edges_match"]:
                mism.append(f"circuit {n}: kept edges differ")
    out["mismatches"] = mism
    (R / "rederive.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({"mismatches": mism, "placebos": out["placebos"]}, indent=1))


if __name__ == "__main__":
    main()
