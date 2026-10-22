#!/usr/bin/env python3
"""Independent re-derivation of every headline from data/samples.jsonl with the Python standard library only (no
numpy/scipy, no import of src/escape.py or src/analysis.py), plus placebos that must lose the effect.

Re-derived: per engine x task the twin share/pass, per-direction screen and confirmation at alpha 2 (exact binomial
tail by math.comb), E and the screen-level E, the direction-paired discordance counts for a-d, c-d, b-d, a-c, a-b,
the literal verdict, the PN off-default shares. Compared field by field with results/escape_by_engine.json,
results/mcnemar.json, results/verdict.json and results/pn.json.
Placebos (10,000 draws each, seed 7):
  P1 engine labels shuffled within direction (each direction's two escape indicators swapped with prob 1/2):
     the a-d difference in E must fall inside the placebo's central 95% (i.e. the observed difference must be
     extreme relative to it) -- reported as the placebo two-sided p.
  P2 direction pairing permuted (engine x's direction i paired with engine y's direction pi(i)): the per-direction
     agreement (kappa) between a and c / a and d must drop to ~0 -- reported as the placebo distribution of kappa.
"""

from __future__ import annotations

import json
import math
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAT = {"T10": {"bfs", "dfs", "label_propagation", "union_find"}, "T2": {"bf_spfa", "bidijkstra", "dial", "dijkstra",
                                                                       "floyd"}}
DEFAULT = {"T10": "union_find", "T2": "dijkstra"}
SEEDS = list(range(9101, 9141))
ENGS = ("a", "b", "c", "d")


def load(p: Path) -> list[dict]:
    out = []
    with open(p) as f:
        for line in f:
            if line.strip():
                out.append(json.loads(line))
    return out


def share(rows, task):
    valid = [r for r in rows if r["label"] not in ("invalid", "disputed")]
    off = sum(1 for r in valid if r["label"] in CAT[task] and r["label"] != DEFAULT[task])
    npass = sum(1 for r in rows if r["passed"])
    return off, len(valid), (off / len(valid) if valid else float("nan")), (npass / len(rows) if rows else float("nan"))


def binom_sf(k: int, n: int, p: float) -> float:
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def derive(rows_e_t, task):
    tw = [r for r in rows_e_t if r["arm"] == "TWIN" and int(r["sample_id"]) < 10]
    k_t, n_t, s_t, pass_t = share(tw, task)
    p0 = (k_t + 0.5) / (n_t + 1)
    cells = defaultdict(list)
    for r in rows_e_t:
        if r["family"] == "POP" and r.get("alpha") == 2.0 and r.get("direction_seed") in SEEDS:
            cells[r["direction_seed"]].append(r)
    per = {}
    for s in SEEDS:
        rr = cells.get(s, [])
        first = [r for r in rr if int(r["sample_id"]) in (0, 1)]
        if not first:
            continue
        pooled = [r for r in rr if 0 <= int(r["sample_id"]) <= 5]
        k1, n1, s1, ps1 = share(first, task)
        k3, n3, s3, ps3 = share(pooled, task)
        scr = n1 > 0 and s1 - s_t >= 0.2 - 1e-12 and ps1 >= 0.8 * pass_t - 1e-12
        conf = False
        if scr and len(pooled) > len(first):
            conf = (s3 - s_t >= 0.2 - 1e-12 and binom_sf(k3, n3, p0) < 0.05 and ps3 >= 0.8 * pass_t - 1e-12)
        per[s] = {"screen": scr, "confirmed": conf, "topped": len(pooled) >= 30, "share10": s1}
    n = len(per)
    return {"twin": {"k_off": k_t, "n_valid": n_t, "share": s_t, "pass": pass_t}, "per": per, "n_run": n,
            "E": sum(v["confirmed"] for v in per.values()) / n if n else None,
            "E_screen": sum(v["screen"] for v in per.values()) / n if n else None,
            "complete": all(v["topped"] for v in per.values() if v["screen"])}


def kappa(x, y):
    n = len(x)
    po = sum(a == b for a, b in zip(x, y)) / n
    px, py = sum(x) / n, sum(y) / n
    pe = px * py + (1 - px) * (1 - py)
    return float("nan") if pe == 1 else (po - pe) / (1 - pe)


def main() -> None:
    rows = load(ROOT / "data" / "samples.jsonl")
    by = defaultdict(list)
    for r in rows:
        by[(r["engine"], r["task"])].append(r)
    D = {(e, t): derive(by[(e, t)], t) for e in ENGS for t in CAT if by.get((e, t))}
    esc = json.loads((ROOT / "results" / "escape_by_engine.json").read_text())
    pair = json.loads((ROOT / "results" / "mcnemar.json").read_text())
    ver = json.loads((ROOT / "results" / "verdict.json").read_text())
    checks, mism = {}, []
    for (e, t), d in D.items():
        ref = esc[e][t]["alpha"]["2.0"]
        ok = (d["n_run"] == ref["n_run"] and abs((d["E"] or 0) * d["n_run"] - ref["n_confirmed"]) < 1e-9
              and abs((d["E_screen"] or 0) * d["n_run"] - ref["n_screen_pass"]) < 1e-9
              and d["twin"]["k_off"] == esc[e][t]["twin"]["k_off"] and d["twin"]["n_valid"] == esc[e][t]["twin"]["n_valid"])
        checks[f"{e}|{t}|E"] = {"rederived_E": d["E"], "rederived_E_screen": d["E_screen"], "analysis_n_confirmed":
                                ref["n_confirmed"], "analysis_n_screen": ref["n_screen_pass"], "match": ok}
        if not ok:
            mism.append(f"{e}|{t}|E")
    for (x, y) in (("a", "d"), ("c", "d"), ("b", "d"), ("a", "c"), ("a", "b")):
        for t in CAT:
            if (x, t) not in D or (y, t) not in D:
                continue
            px, py = D[(x, t)]["per"], D[(y, t)]["per"]
            common = sorted(set(px) & set(py))
            n10 = sum(1 for s in common if px[s]["confirmed"] and not py[s]["confirmed"])
            n01 = sum(1 for s in common if py[s]["confirmed"] and not px[s]["confirmed"])
            ref = pair.get(f"{t}|{x}-{y}|confirmed", {})
            if "n10" not in ref:      # analysis skipped the confirmed level (an engine's confirmation incomplete)
                ref = pair.get(f"{t}|{x}-{y}|screen", {})
                n10 = sum(1 for s in common if px[s]["screen"] and not py[s]["screen"])
                n01 = sum(1 for s in common if py[s]["screen"] and not px[s]["screen"])
            ok = ref.get("n10") == n10 and ref.get("n01") == n01
            checks[f"{t}|{x}-{y}|mcnemar"] = {"n10": n10, "n01": n01, "match": ok}
            if not ok:
                mism.append(f"{t}|{x}-{y}|mcnemar")
    # verdict re-derivation (literal, alpha 2)
    e4 = {t: ver[t]["E_iter4_relabelled_a"] for t in CAT}
    for t in CAT:
        E = {e: (D[(e, t)]["E"] if (e, t) in D and D[(e, t)]["complete"] else None) for e in ENGS}
        Ea, Eb, Ec, Ed = E["a"], E["b"], E["c"], E["d"]
        if None in (Ea, Ec, Ed):
            v = "UNDECIDABLE (missing engine)"
        elif Ec - Ed >= 0.2 - 1e-12 and abs(Ea - Ec) <= 0.1 + 1e-12 and Eb is not None and abs(Eb - Ed) <= 0.1 + 1e-12:
            v = "ACTIVATION_ROUNDING"
        elif Eb is not None and Eb - Ed >= 0.2 - 1e-12:
            v = "WEIGHT"
        elif Eb is not None and Ea - Ed >= 0.2 - 1e-12 and Eb - Ed < 0.1 and Ec - Ed < 0.1:
            v = "INTERACTION"
        elif Ea - Ed < 0.1 and Ea < e4[t] - 0.15:
            v = "NOT_REPRODUCED_LOW"
        elif Ea - Ed < 0.1 and Ed >= e4[t] - 0.15:
            v = "NOT_REPRODUCED_HIGH"
        elif Eb is None:
            v = "MIXED_OR_UNDECIDABLE (b missing)"
        else:
            v = "MIXED"
        ok = v == ver[t]["literal_verdict"]
        checks[f"{t}|verdict"] = {"rederived": v, "analysis": ver[t]["literal_verdict"], "match": ok}
        if not ok:
            mism.append(f"{t}|verdict")
    # placebos
    rng = random.Random(7)
    plc = {}
    for t in CAT:
        for (x, y) in (("a", "d"), ("c", "d"), ("a", "c")):
            if (x, t) not in D or (y, t) not in D:
                continue
            level = "confirmed" if D[(x, t)]["complete"] and D[(y, t)]["complete"] else "screen"
            px, py = D[(x, t)]["per"], D[(y, t)]["per"]
            common = sorted(set(px) & set(py))
            xs = [int(px[s][level]) for s in common]
            ys = [int(py[s][level]) for s in common]
            obs = (sum(xs) - sum(ys)) / len(common)
            null = []
            for _ in range(10000):
                d = 0
                for a, b in zip(xs, ys):
                    d += (a - b) if rng.random() < 0.5 else (b - a)
                null.append(d / len(common))
            p1 = (sum(1 for v in null if abs(v) >= abs(obs) - 1e-12) + 1) / (len(null) + 1)
            k_obs = kappa(xs, ys)
            kn = []
            for _ in range(2000):
                perm = ys[:]
                rng.shuffle(perm)
                kn.append(kappa(xs, perm))
            kn = [k for k in kn if k == k]
            kn.sort()
            plc[f"{t}|{x}-{y}|{level}"] = {
                "observed_diff": obs, "P1_shuffled_engine_labels_p": p1,
                "P1_null_central95": [sorted(null)[250], sorted(null)[9749]],
                "observed_kappa": k_obs,
                "P2_permuted_pairing_kappa_median": kn[len(kn) // 2] if kn else None,
                "P2_permuted_pairing_kappa_central95": [kn[int(0.025 * len(kn))], kn[int(0.975 * len(kn)) - 1]] if kn else None}
    out = {"n_rows": len(rows), "checks": checks, "mismatches": mism, "all_match": not mism, "placebos": plc}
    (ROOT / "results" / "rederive.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({"all_match": not mism, "mismatches": mism}, indent=1))


if __name__ == "__main__":
    main()
