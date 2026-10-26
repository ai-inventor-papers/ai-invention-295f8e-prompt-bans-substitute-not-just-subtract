#!/usr/bin/env python3
"""Independent re-derivation of step K's headline numbers from the raw rows (standard library only; shares no code
with src/). Reads data/raw/raw_k.jsonl, data/raw/knobs_norm.jsonl, data/raw/reuse_exp27.jsonl, data/labels.jsonl and
the committed result files it checks; writes results/rederive.json.

Re-derived: anchor counts (A1, A2); 2x2 shares and RD_unit / RD_seed / INT on T10 and T2 alpha 2 (outcome Y =
passed and label not in {default, other, invalid, disputed, unknown}); the D5 split; S2 McNemar discordant counts on
T10 and T2; two H5 values (T10 BINT and T03 PN*) with an independent direct-simulation hull (grid 0.05, 400 draws);
pairing checks (identical direction seeds within a seed scheme per slot; one uniform stream per slot).
Placebos: (P1) design labels shuffled within slot -> RD_unit near 0 (200 shuffles); (P2) PN* rows relabelled as TWIN
-> the PN* hull collapses to the twin's Hill.

usage: python3 audit/rederive.py      (any Python >= 3.9; no third-party package)
"""

from __future__ import annotations

import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = {"T10": "union_find", "T2": "dijkstra", "T03": "full_sort", "T05": "hash_map", "T1": "bfs"}
SPECIAL = {"other", "invalid", "disputed", "unknown"}


def rj(p: Path) -> list[dict]:
    out = []
    if not p.exists():
        return out
    for line in p.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def key(r: dict) -> str:
    return f"{r['task']}|{r['template']}|{r['arm']}|{r['sample_id']}"


def load() -> tuple[dict, dict]:
    labs = {l["key"]: l for l in rj(ROOT / "data" / "labels.jsonl")}
    cells: dict = defaultdict(dict)
    meta: dict = {}
    for name in ("raw_k.jsonl", "knobs_norm.jsonl", "reuse_exp27.jsonl"):
        for r in rj(ROOT / "data" / "raw" / name):
            l = labs.get(key(r))
            if l is None:
                continue
            k = int(r["sample_id"])
            lab = l.get("label") or "invalid"
            passed = bool(l.get("passed"))
            valid = bool(l.get("valid"))
            d = DEFAULT[r["task"]]
            cells[(r["task"], r["arm"])][(r["template"], k)] = {
                "label": lab, "passed": passed,
                "Y": int(passed and lab != d and lab not in SPECIAL),
                "Y_any": int(passed and lab != d and lab not in {"invalid", "disputed", "unknown"}),
                "A": int(valid and lab != d and lab not in {"invalid", "disputed", "unknown"})}
            meta[(r["task"], r["arm"], r["template"], k)] = {"dseed": r.get("direction_seed"), "seed": r.get("seed"),
                                                             "utc": r.get("utc"), "stage": r.get("stage")}
    return cells, meta


KMAX = {("T10", "a1"): 9, ("T10", "a2"): 9, ("T2", "a1"): 9, ("T2", "a2"): 19}   # committed slots only


def two_by_two(cells: dict, task: str, a: str, out_key: str = "Y") -> dict:
    ds = [cells.get((task, f"D{i}_{a}"), {}) for i in (1, 2, 3, 4)]
    slots = sorted(s for s in set(ds[0]) & set(ds[1]) & set(ds[2]) & set(ds[3]) if s[1] <= KMAX[(task, a)])
    n = len(slots)
    if n == 0:
        return {"n": 0}
    m = [[d[s][out_key] for d in ds] for s in slots]
    sh = [sum(row[j] for row in m) / n for j in range(4)]
    unit = sum(((r[0] - r[2]) + (r[1] - r[3])) / 2 for r in m) / n
    seed = sum(((r[0] - r[1]) + (r[2] - r[3])) / 2 for r in m) / n
    inter = sum((r[0] - r[1]) - (r[2] - r[3]) for r in m) / n
    return {"n": n, "shares": dict(zip(("D1", "D2", "D3", "D4"), sh)), "RD_unit": unit, "RD_seed": seed, "INT": inter,
            "matrix": m, "slots": slots}


def mcnemar(cells: dict, task: str, x: str, y: str) -> dict:
    cx, cy = cells.get((task, x), {}), cells.get((task, y), {})
    common = [s for s in cx if s in cy and s[1] <= 9]
    n10 = sum(1 for s in common if cx[s]["Y"] == 1 and cy[s]["Y"] == 0)
    n01 = sum(1 for s in common if cx[s]["Y"] == 0 and cy[s]["Y"] == 1)
    n = n10 + n01
    p = 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(0, min(n10, n01) + 1)) / 2 ** n)
    return {"n": len(common), "n10": n10, "n01": n01, "p_exact": p}


def hull_h5(settings: list[dict], draws: int = 400, step: float = 0.05, seed: int = 1, depth: int = 25,
            bound: float = 0.05) -> float:
    """Direct simulation: for each mixture w on a simplex grid, draw `draws` samples of `depth` programs: each draw
    picks setting j with prob w_j pass_j / sum, then a correct program of j uniformly; Hill-1 of the label counts."""
    k = len(settings)
    m = int(round(1 / step))
    grid = []
    if k == 2:
        grid = [[i / m, 1 - i / m] for i in range(m + 1)]
    else:
        for i in range(m + 1):
            for j in range(m + 1 - i):
                grid.append([i / m, j / m, (m - i - j) / m])
    rng = random.Random(seed)
    best = float("nan")
    p0 = settings[0]["pass"]
    for w in grid:
        cost = p0 - sum(wi * s["pass"] for wi, s in zip(w, settings))
        if cost > bound + 1e-12:
            continue
        a = [wi * s["pass"] if s["labels"] else 0.0 for wi, s in zip(w, settings)]
        tot = sum(a)
        if tot <= 0:
            continue
        cum, c = [], 0.0
        for x in a:
            c += x / tot
            cum.append(c)
        hs = 0.0
        for _ in range(draws):
            cnt = Counter()
            for _ in range(depth):
                u = rng.random()
                j = next(i for i, cv in enumerate(cum) if u <= cv or i == len(cum) - 1)
                cnt[rng.choice(settings[j]["labels"])] += 1
            h = -sum((v / depth) * math.log(v / depth) for v in cnt.values())
            hs += math.exp(h)
        hv = hs / draws
        if not (hv <= best):
            best = hv
    return best


def settings_of(cells: dict, task: str, arms: list[str]) -> list[dict]:
    out = []
    for a in arms:
        c = {s: v for s, v in cells.get((task, a), {}).items() if s[1] <= 9}
        out.append({"arm": a, "labels": [v["label"] for v in c.values() if v["passed"]],
                    "pass": sum(v["passed"] for v in c.values()) / max(len(c), 1)})
    return out


def main() -> None:
    cells, meta = load()
    res: dict = {}
    d1 = cells.get(("T10", "D1_a2"), {})
    d4 = cells.get(("T10", "D4_a2"), {})
    res["A1_T10_D1_a2_attempted"] = sum(v["A"] for s, v in d1.items() if s[1] <= 9)
    res["A2_T10_D4_a2_correct_off_default"] = sum(v["Y_any"] for s, v in d4.items() if s[1] <= 9)
    for task in ("T10", "T2"):
        for a in ("a1", "a2"):
            t = two_by_two(cells, task, a)
            t.pop("matrix", None)
            t.pop("slots", None)
            res[f"2x2|{task}|{a}"] = t
    # D5 split
    for task in ("T10", "T2"):
        c1, c5, c3 = (cells.get((task, f"{d}_a2"), {}) for d in ("D1", "D5", "D3"))
        common = [s for s in c1 if s in c5 and s in c3 and s[1] <= KMAX[(task, "a2")]]
        if common:
            n = len(common)
            res[f"D5_split|{task}"] = {"n": n, "D1_minus_D5": sum(c1[s]["Y"] - c5[s]["Y"] for s in common) / n,
                                       "D5_minus_D3": sum(c5[s]["Y"] - c3[s]["Y"] for s in common) / n}
    for task in ("T10", "T2"):
        res[f"S2|{task}|PTOP_vs_PREST"] = mcnemar(cells, task, "PTOP_a2", "PREST_a2")
        res[f"S2|{task}|D1_vs_PSHUF"] = mcnemar(cells, task, "D1_a2", "PSHUF_a2")
    # pairing checks
    bad_s4, bad_s5, n_pairs = 0, 0, 0
    slots = {(t, w, k) for (t, a, w, k) in meta if a.startswith("D1_")}
    for (t, w, k) in slots:
        for a in ("a1", "a2"):
            s1 = meta.get((t, f"D1_{a}", w, k), {}).get("dseed")
            s3 = meta.get((t, f"D3_{a}", w, k), {}).get("dseed")
            s2 = meta.get((t, f"D2_{a}", w, k), {}).get("dseed")
            s4 = meta.get((t, f"D4_{a}", w, k), {}).get("dseed")
            if s1 is not None and s3 is not None:
                n_pairs += 1
                bad_s4 += s1 != s3
            if s2 is not None and s4 is not None:
                bad_s5 += s2 != s4
        for p in ("PTOP_a2", "PREST_a2", "PSHUF_a2", "D5_a2"):
            sp = meta.get((t, p, w, k), {}).get("dseed")
            s1 = meta.get((t, "D1_a2", w, k), {}).get("dseed")
            if sp is not None and s1 is not None:
                bad_s4 += sp != s1
    streams = defaultdict(set)
    for (t, a, w, k), m in meta.items():
        if m.get("seed") is not None and not a.startswith("E27:"):
            streams[(t, w, k)].add(m["seed"])
    res["pairing"] = {"slot_pairs_checked": n_pairs, "S4_seed_mismatch": bad_s4, "S5_seed_mismatch": bad_s5,
                      "slots_with_more_than_one_stream_seed": sum(1 for v in streams.values() if len(v) > 1)}
    # H5 (independent hull)
    s3 = json.loads((ROOT / "results" / "s3_prices.json").read_text()) if (ROOT / "results" / "s3_prices.json").exists() else None
    if s3:
        ds = s3["D_star"]
        src = s3["knob_sources"]
        h_bint = hull_h5(settings_of(cells, "T10", ["TWIN", src["T10"]["BINT"]]))
        h_pn = hull_h5(settings_of(cells, "T03", ["TWIN", f"{ds}_a1", f"{ds}_a2"]))
        ref_b = s3["per_task"]["T10"]["BINT"]["H5"]
        ref_p = s3["per_task"]["T03"]["PN*"]["H5"]
        res["H5_independent"] = {"T10|BINT": {"here": h_bint, "committed": ref_b, "abs_diff": abs(h_bint - ref_b)},
                                 "T03|PN*": {"here": h_pn, "committed": ref_p, "abs_diff": abs(h_pn - ref_p)}}
        # placebo P2: PN* rows relabelled as TWIN -> hull = twin's Hill
        tw = settings_of(cells, "T03", ["TWIN"])[0]
        h_tw = hull_h5([tw, dict(tw)])
        res["placebo_PNstar_as_TWIN"] = {"H5": h_tw, "twin_only_H5": hull_h5([tw, tw])}
    # placebo P1: shuffle the four design labels within each slot (T10 alpha 2)
    t = two_by_two(cells, "T10", "a2")
    if t["n"]:
        rng = random.Random(7)
        vals = []
        for _ in range(200):
            m2 = []
            for row in t["matrix"]:
                r2 = row[:]
                rng.shuffle(r2)
                m2.append(r2)
            vals.append(sum(((r[0] - r[2]) + (r[1] - r[3])) / 2 for r in m2) / len(m2))
        obs = t["RD_unit"]
        res["placebo_design_shuffle_T10_a2"] = {"mean_RD_unit": sum(vals) / len(vals),
                                                "frac_abs_ge_observed": sum(abs(v) >= abs(obs) - 1e-12 for v in vals) / len(vals),
                                                "observed": obs}
    # ---- extensions (TODO 5): every headline number of README / method_out through this separate code path
    rng2 = random.Random(11)
    t = two_by_two(cells, "T10", "a2")
    if t["n"]:
        m = t["matrix"]
        uc = [((r[0] - r[2]) + (r[1] - r[3])) / 2 for r in m]
        sc = [((r[0] - r[1]) + (r[2] - r[3])) / 2 for r in m]
        boots_u, boots_s = [], []
        for _ in range(1000):
            idx = [rng2.randrange(len(m)) for _ in range(len(m))]
            boots_u.append(sum(uc[i] for i in idx) / len(m))
            boots_s.append(sum(sc[i] for i in idx) / len(m))
        boots_u.sort(); boots_s.sort()
        obs = abs(sum(uc))
        hits = sum(1 for _ in range(20000) if abs(sum(c if rng2.random() < 0.5 else -c for c in uc)) >= obs - 1e-12)
        res["T10_a2_unit_bootstrap_ci95"] = [boots_u[24], boots_u[974]]
        res["T10_a2_seed_bootstrap_ci95"] = [boots_s[24], boots_s[974]]
        res["T10_a2_unit_signflip_p_mc"] = (hits + 1) / 20001
    # E1 counts and E3 contrasts (fresh slots k 10-19; T03 k 0-9)
    res["E1_T10_counts_Y"] = {f"D3_a{a}": sum(v["Y"] for s_, v in cells.get(("T10", f"D3_a{a}"), {}).items() if s_[1] <= 9)
                             for a in (1, 2, 3, 4, 6)}
    for label, task, lo, hi in (("E3_T10_fresh", "T10", 10, 19), ("E3_T03", "T03", 0, 9)):
        ds = [cells.get((task, f"D{i}_a2"), {}) for i in (1, 2, 3, 4)]
        sl = sorted(x for x in set(ds[0]) & set(ds[1]) & set(ds[2]) & set(ds[3]) if lo <= x[1] <= hi)
        if sl:
            m = [[d[x]["Y"] for d in ds] for x in sl]
            u = sum(((r[0] - r[2]) + (r[1] - r[3])) / 2 for r in m) / len(m)
            sd = sum(((r[0] - r[1]) + (r[2] - r[3])) / 2 for r in m) / len(m)
            sh = []
            for _ in range(200):
                m2 = [rng2.sample(r, 4) for r in m]
                sh.append(sum(((r[0] - r[2]) + (r[1] - r[3])) / 2 for r in m2) / len(m2))
            res[label] = {"n": len(sl), "shares": [sum(r[j] for r in m) / len(m) for j in range(4)], "RD_unit": u,
                          "RD_seed": sd, "placebo_shuffle_mean_RD_unit": sum(sh) / len(sh),
                          "placebo_frac_abs_ge_observed": sum(abs(v) >= abs(u) - 1e-12 for v in sh) / len(sh)}
    # S2 McNemar placebo: arm labels shuffled within slot (T10) -> no systematic discordance
    cx, cy = cells.get(("T10", "PTOP_a2"), {}), cells.get(("T10", "PREST_a2"), {})
    common = [x for x in cx if x in cy and x[1] <= 9]
    pv = []
    for _ in range(200):
        n10 = n01 = 0
        for x in common:
            a, b = cx[x]["Y"], cy[x]["Y"]
            if rng2.random() < 0.5:
                a, b = b, a
            n10 += a == 1 and b == 0
            n01 += a == 0 and b == 1
        n = n10 + n01
        pv.append(1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(min(n10, n01) + 1)) / 2 ** n))
    res["placebo_S2_T10_PTOP_vs_PREST_shuffled"] = {"median_p": sorted(pv)[len(pv) // 2],
                                                    "frac_p_lt_0.05": sum(q < 0.05 for q in pv) / len(pv)}
    # novelty count: correct 'other' programs among this artifact's rows and the reused exp27 rows in the hull
    labs = {l["key"]: l for l in rj(ROOT / "data" / "labels.jsonl")}
    n_other = 0
    for name in ("raw_k.jsonl", "knobs_norm.jsonl"):
        for r in rj(ROOT / "data" / "raw" / name):
            l = labs.get(key(r))
            n_other += bool(l and l.get("label") == "other" and l.get("passed"))
    res["correct_other_programs_generated_here"] = n_other
    # S3: PN* vs BINT point H5 on all five tasks with the independent hull
    if s3:
        ds = s3["D_star"]
        s3c = {}
        for task in ("T03", "T10", "T2", "T05", "T1"):
            hb = hull_h5(settings_of(cells, task, ["TWIN", s3["knob_sources"][task]["BINT"]]), draws=300)
            hp = hull_h5(settings_of(cells, task, ["TWIN", f"{ds}_a1", f"{ds}_a2"]), draws=300)
            cb, cp = s3["per_task"][task]["BINT"]["H5"], s3["per_task"][task]["PN*"]["H5"]
            s3c[task] = {"PN*": hp, "BINT": hb, "committed_PN*": cp, "committed_BINT": cb,
                         "same_ordering": (hp > hb) == (cp > cb)}
        res["S3_PN_vs_BINT_independent"] = s3c
        res["S3_PN_ge_BINT_count_independent"] = sum(v["PN*"] >= v["BINT"] for v in s3c.values())
    # compare with the committed analysis
    s1p = ROOT / "results" / "s1_2x2.json"
    mism = []
    if s1p.exists():
        s1 = json.loads(s1p.read_text())
        for task in ("T10", "T2"):
            for a, al in (("a1", "a1"), ("a2", "a2")):
                mine = res.get(f"2x2|{task}|{a}", {})
                ref = s1["tables"].get(f"{task}|{al}|Y", {})
                for k in ("RD_unit", "RD_seed"):
                    if mine.get(k) is not None and ref.get(k) is not None and abs(mine[k] - ref[k]) > 1e-9:
                        mism.append(f"{task}|{a}|{k}: {mine[k]} vs {ref[k]}")
                ref_int = ref.get("RD_int")
                if mine.get("INT") is not None and ref_int is not None and abs(mine["INT"] - ref_int) > 1e-9:
                    mism.append(f"{task}|{a}|INT")
    ap = ROOT / "results" / "anchors.json"
    if ap.exists():
        an = json.loads(ap.read_text())
        if an.get("A1", {}).get("attempted_off_default") != res["A1_T10_D1_a2_attempted"]:
            mism.append("A1")
        if an.get("A2", {}).get("correct_off_default") != res["A2_T10_D4_a2_correct_off_default"]:
            mism.append("A2")
    res["mismatches_vs_committed_analysis"] = mism
    res["n_mismatches"] = len(mism)
    (ROOT / "results" / "rederive.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if not k.startswith("2x2")}, indent=1)[:3000])


if __name__ == "__main__":
    main()
