"""Independent re-derivation of the headline numbers from the raw per-sample files (data/*.jsonl), the committed
predictions and the exp9 LOS file, without importing analysis.py; plus placebo runs (labels permuted within task)
that must break the C3 and homogeneity results.  Writes results/rederive.json."""

from __future__ import annotations

import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def rj(p: Path) -> list[dict]:
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def chi2(groups: dict[str, list[str]]) -> float:
    cats = sorted({x for v in groups.values() for x in v})
    tab = [[v.count(c) for c in cats] for v in groups.values()]
    rows = [sum(r) for r in tab]
    cols = [sum(c) for c in zip(*tab)]
    n = sum(rows)
    s = 0.0
    for i, r in enumerate(tab):
        for j, o in enumerate(r):
            e = rows[i] * cols[j] / n if n else 0
            if e > 0:
                s += (o - e) ** 2 / e
    return s


def perm_p(groups: dict[str, list[str]], n_perm: int = 10000, seed: int = 0) -> float:
    obs = chi2(groups)
    pooled = [x for v in groups.values() for x in v]
    sizes = [len(v) for v in groups.values()]
    rng = random.Random(seed)
    ge = 0
    for _ in range(n_perm):
        rng.shuffle(pooled)
        i, gs = 0, {}
        for k, s in zip(groups, sizes):
            gs[k] = pooled[i:i + s]
            i += s
        ge += chi2(gs) >= obs - 1e-12
    return (ge + 1) / (n_perm + 1)


def c3_from(los: list[dict], cells: list[dict], exp9: dict, permute_seed: int | None = None) -> dict:
    rows = los
    if permute_seed is not None:
        rng = random.Random(permute_seed)
        by_t: dict[str, list[int]] = {}
        for i, r in enumerate(rows):
            by_t.setdefault(r["task"], []).append(i)
        rows = [dict(r) for r in rows]
        for t, idx in by_t.items():
            labs = [rows[i]["label"] for i in idx]
            rng.shuffle(labs)
            for i, l in zip(idx, labs):
                rows[i]["label"] = l
    out = []
    for c in cells:
        if not c["qualifies"]:
            continue
        if c["task"] == "T2":
            will = exp9.get(c["S"], {}).get("will_attempted_share")
        else:
            att = [r for r in rows if r["task"] == c["task"] and r["condition"] == f"los:LOS({c['S']})"
                   and r["label"] != "invalid"]
            will = (sum(r["label"] == c["S"] for r in att) / len(att)) if att else None
        out.append({"task": c["task"], "S": c["S"], "will": will})
    ws = [o["will"] for o in out if o["will"] is not None]
    verdict = "UNTESTABLE" if not ws else ("DISCONFIRMED" if any(w >= 0.30 for w in ws) else
                                           ("CONFIRMED" if all(w <= 0.10 for w in ws) else "MIXED"))
    return {"cells": out, "verdict": verdict}


def main() -> None:
    res: dict = {}
    walk = rj(ROOT / "data" / "samples_walk.jsonl")
    # walk: per (task, step, round) modal non-vetoed label and default re-emergence from raw rows + committed masks
    wk = {}
    for p in sorted((ROOT / "predictions").glob("walk_*_s*_r*.json")):
        m = json.loads(p.read_text())
        t, s, r = m["task"], m["step"], m["round"]
        rows = [x for x in walk if x["task"] == t and x["step"] == s and x["round"] == r]
        if not rows:
            continue
        vet = m["vetoed"]
        att = [x for x in rows if x["label"] != "invalid"]
        nv = Counter(x["label"] for x in rows if x["label"] not in vet).most_common(1)
        wk[f"{t}|s{s}r{r}"] = {"n": len(rows), "modal_nonvetoed": nv[0][0] if nv else None,
                               "reemergence": {a: (sum(x["label"] == a for x in att) / len(att)) if att else None
                                               for a in vet},
                               "veto_occurrences": sum(x.get("veto_occurrences", 0) for x in rows)}
    res["walk_rounds"] = wk
    an = json.loads((ROOT / "results" / "walk.json").read_text()) if (ROOT / "results" / "walk.json").exists() else {}
    mism = []
    for key, v in wk.items():
        t, sr = key.split("|")
        s, r = int(sr[1:sr.index("r")]), int(sr[sr.index("r") + 1:])
        for st in (an.get(t) or {}).get("steps", []):
            if st["step"] == s and st["round"] == r:
                if st["modal_nonvetoed"] != v["modal_nonvetoed"]:
                    mism.append({"key": key, "analysis": st["modal_nonvetoed"], "rederived": v["modal_nonvetoed"]})
    res["walk_mismatches"] = mism
    # C3
    cells = []
    for g in ("path", "bench"):
        p = ROOT / "predictions" / f"reach_forecasts_{g}.json"
        if p.exists():
            for t, v in json.loads(p.read_text())["tasks"].items():
                cells += v["c3_cells"]
    exp9 = json.loads((ROOT / "inputs" / "exp9" / "results" / "los.json").read_text())
    los = rj(ROOT / "data" / "samples_los.jsonl")
    res["c3"] = c3_from(los, cells, exp9)
    res["c3_placebo"] = [c3_from(los, cells, exp9, permute_seed=s)["verdict"] for s in range(5)]
    c3a = json.loads((ROOT / "results" / "c3.json").read_text()) if (ROOT / "results" / "c3.json").exists() else {}
    res["c3_matches_analysis"] = c3a.get("overall") == res["c3"]["verdict"]
    # list independence
    two = rj(ROOT / "data" / "samples_two_step.jsonl")
    li = json.loads((ROOT / "results" / "list_independence.json").read_text()) if (
        ROOT / "results" / "list_independence.json").exists() else {}
    lr = {}
    for t, v in li.items():
        D, R2 = v["D"], v["R2"]
        groups = {}
        for g in v["groups"]:
            src = two if g.startswith("TWO") else los
            cond = f"two_step:{g}" if g.startswith("TWO") else f"los:{g}"
            labs = ["D" if r["label"] == D else "R2" for r in src if r["task"] == t and r["condition"] == cond
                    and r["label"] in (D, R2)]
            if labs:
                groups[g] = labs
        p = perm_p(groups, 10000, 0) if len(groups) >= 2 else None
        # placebo: shuffle group membership of the same programs -> p should look uniform
        pl = []
        for s in range(3):
            pooled = [x for vv in groups.values() for x in vv]
            random.Random(100 + s).shuffle(pooled)
            i, gs = 0, {}
            for k, vv in groups.items():
                gs[k] = pooled[i:i + len(vv)]
                i += len(vv)
            pl.append(perm_p(gs, 2000, s) if len(gs) >= 2 else None)
        lr[t] = {"p_perm": p, "analysis_p": (v.get("test") or {}).get("p_perm"), "placebo_p": pl}
    res["list_independence"] = lr
    # novelty counts
    na = json.loads((ROOT / "results" / "novelty_audit.json").read_text()) if (
        ROOT / "results" / "novelty_audit.json").exists() else {}
    res["novel_count"] = sum(1 for r in na.get("records", []) if r.get("final_class") == "NOVEL ALGORITHM")
    # cross-check JS
    lf = rj(ROOT / "data" / "samples_longform.jsonl")
    a = Counter(r["label"] for r in lf if r["task"] == "T2" and r["prompt_id"] == "LF1" and not r["thinking"]
                and r["engine_dtype"] == "bf16")
    b = Counter(r["label"] for r in lf if r["task"] == "T2" and r["prompt_id"] == "LF1" and not r["thinking"]
                and r["engine_dtype"] == "fp8")
    import math

    def js(c1, c2):
        n1, n2 = sum(c1.values()), sum(c2.values())
        if not n1 or not n2:
            return None
        s = 0.0
        for k in set(c1) | set(c2):
            p, q = c1.get(k, 0) / n1, c2.get(k, 0) / n2
            m = (p + q) / 2
            s += (0.5 * p * math.log2(p / m) if p else 0) + (0.5 * q * math.log2(q / m) if q else 0)
        return s

    res["crosscheck_js_bits"] = js(a, b)
    xc = json.loads((ROOT / "results" / "fp8_crosscheck.json").read_text()) if (
        ROOT / "results" / "fp8_crosscheck.json").exists() else {}
    jsa = (xc.get("js") or {}).get("js_bits")
    res["crosscheck_matches"] = (jsa is None and res["crosscheck_js_bits"] is None) or (
        jsa is not None and res["crosscheck_js_bits"] is not None and abs(jsa - res["crosscheck_js_bits"]) < 1e-9)
    res["n_mismatches"] = len(mism) + (0 if res["c3_matches_analysis"] else 1) + (0 if res["crosscheck_matches"] else 1) \
        + sum(1 for v in lr.values() if v["p_perm"] is not None and v["analysis_p"] is not None and
              abs(v["p_perm"] - v["analysis_p"]) > 1e-9)
    (ROOT / "results" / "rederive.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({"n_mismatches": res["n_mismatches"], "c3": res["c3"]["verdict"], "c3_placebo": res["c3_placebo"],
                      "novel_count": res["novel_count"]}))
    sys.exit(0)


if __name__ == "__main__":
    main()
