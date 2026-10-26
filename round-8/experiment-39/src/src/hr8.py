#!/usr/bin/env python3
"""Stage 4 analysis (HR, hidden repertoire): ideas reachable by forcing any of the top-64 tokens at each decision node
(5 T = 1 continuations each; ranks within the Stage 2 map reuse its first 5 continuations) vs ideas reached by the
sampling knobs (A0-A10; A11 is forcing), the global-T arms alone, the forced can-rates and iteration-7 search clusters.
An IDEA is a catalogue label, or for correct 'other' programs the novelty audit's adjudicated name.
Per HR-only idea: T = 1 reachability mass m = sum_c w_c sum_t pi_1(t | n_c) f(idea | n_c, t) over the saved top-64,
the expected number of T = 1 samples to see it once (1 / m), and the smallest fork dose (top-20) with m_T >= 0.05.
Writes results/hr.json.
"""

from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg8 import (CACHE_DIR, CONT_LABELS, CONTS, DOSE_GRID, E35, INPUTS, K_HR, RESULTS_DIR, TEMPLATES, UNITS,  # noqa
                  read_json, read_jsonl, utc_now, write_json)
import analysis_k1 as AK  # noqa: E402
import predict8 as PR  # noqa: E402
import units8 as U8  # noqa: E402

SAMPLING_ARMS = ["A0", "A1", "A2", "A3g", "A4", "A5", "A6", "A7", "A8", "A9", "A10"]
GLOBAL_T = ["A0", "A1", "A2", "A3g"]
NODES = {"T10": ["n10", "n11"], "B3": ["c0", "c1"], "A3": ["c0", "c1"], "B6": ["c0"], "G": ["cstar"], "T1": ["n3"]}


def idea_of(unit: str, label: str | None, sid: str, adjud: dict[str, str]) -> str:
    if sid in adjud:
        return adjud[sid]
    return AK.cls(unit, label)


def forced_ideas(unit: str) -> set[str]:
    out: set[str] = set()
    if unit in ("B3", "A3", "B6"):
        s4b = read_json(E35 / "results" / "s4b.json")
        u = s4b.get(unit) or s4b.get("units", {}).get(unit) or {}
        u = u.get("arms", u) if isinstance(u, dict) else {}
        for arm in ("FORCED", "EXCH"):
            d = u.get(arm) if isinstance(u, dict) else None
            if isinstance(d, dict):
                for k in ("labels", "counts", "label_counts"):
                    if isinstance(d.get(k), dict):
                        out |= {x for x in d[k] if x in UNITS[unit]["catalogue"]}
    if unit == "T10":
        for r in read_jsonl(INPUTS / "iter2_exp11" / "bench" / "T10_forced_programs.jsonl"):
            lab = r.get("label") or r.get("mode") or r.get("algorithm")
            if lab in UNITS[unit]["catalogue"]:
                out.add(lab)
    return out


def run(adjud: dict[str, str] | None = None) -> dict:
    adjud = adjud or {}
    labels = {r["sid"]: r for r in read_jsonl(CONT_LABELS)}
    cont = defaultdict(list)          # (unit, node) -> rows
    for r in read_jsonl(CONTS):
        if r.get("arm") == "MAP" and r.get("k", 99) < K_HR or r.get("arm") == "HR":
            L = labels.get(r["sid"])
            if L is None:
                continue
            r["idea"] = idea_of(r["unit"], L.get("label"), r["sid"], adjud)
            r["passed"] = bool(L.get("passed")) and r["idea"] != "invalid"
            cont[(r["unit"], r["node"])].append(r)
    data = AK.load_rows(adjud)
    out = {"utc": utc_now(), "units": {}}
    n_units_extra = 0
    for unit, nodes in NODES.items():
        rows = [r for n in nodes for r in cont.get((unit, n), [])]
        if not rows:
            continue
        has_hr = any(r["arm"] == "HR" for r in rows)
        ideas_hr = {r["idea"] for r in rows if r["passed"]}
        arms = data.get(unit, {})
        ideas_k = {a: sorted({idea_of(unit, r["label"], r["sid"], adjud) for r in arms[a].values() if r["passed"]}
                             - {"invalid"}) for a in SAMPLING_ARMS if a in arms}
        kstar = set().union(*[set(v) for v in ideas_k.values()]) if ideas_k else set()
        kglob = set().union(*[set(ideas_k[a]) for a in GLOBAL_T if a in ideas_k]) if ideas_k else set()
        hr_only = sorted(ideas_hr - kstar - {"invalid"})
        # reachability of every idea (T = 1 over the saved top-64, and fork doses over the top-20)
        reach = {}
        for idea in sorted(ideas_hr | kstar):
            m1, mT = 0.0, {}
            for n in nodes:
                p = CACHE_DIR / "nodes" / f"{unit}_{n}.json"
                if not p.exists():
                    continue
                info = read_json(p)
                f = defaultdict(list)
                for r in cont.get((unit, n), []):
                    f[int(r["token"])].append(r["idea"] == idea and r["passed"])
                freq = {t: float(np.mean(v)) for t, v in f.items()}
                if unit == "T10" and n == "n10" and "n11" in nodes:
                    freq.pop(U8.T10_DEF, None)          # ' def' is followed through n11 (no double count)
                parent = None
                if n == "n11":                      # reached through ' def' at n10: weight by its probability there
                    parent = read_json(CACHE_DIR / "nodes" / f"{unit}_n10.json")

                def via(w: str, T: float, k: int) -> float:
                    if parent is None:
                        return 1.0
                    tfp = parent["tf"][w]
                    ids_p, pr_p = PR.dist_top_from_saved(tfp["top_ids"], tfp["top_z"], T, k)
                    d = dict(zip(ids_p.tolist(), pr_p.tolist()))
                    return math.exp(tfp["path_logprob"]) * d.get(U8.T10_DEF, 0.0)
                wsum = []
                for w in TEMPLATES:
                    tf = info["tf"][w]
                    ids, pr = PR.dist_top_from_saved(tf["top_ids"], tf["top_z"], 1.0, 64)
                    wc = math.exp(tf["path_logprob"]) if parent is None else via(w, 1.0, 64)
                    wsum.append(wc * sum(pp * freq.get(int(t), 0.0) for t, pp in zip(ids, pr)))
                m1 += float(np.mean(wsum))
                for T in DOSE_GRID:
                    v = []
                    for w in TEMPLATES:
                        tf = info["tf"][w]
                        ids, pr = PR.dist_top_from_saved(tf["top_ids"], tf["top_z"], T, 20)
                        wc = math.exp(tf["path_logprob"]) if parent is None else via(w, T, 20)
                        v.append(wc * sum(pp * freq.get(int(t), 0.0) for t, pp in zip(ids, pr)))
                    mT[T] = mT.get(T, 0.0) + float(np.mean(v))
            dmin = next((T for T in DOSE_GRID if mT.get(T, 0) >= 0.05), None)
            reach[idea] = {"m_T1": m1, "expected_T1_samples": (1 / m1) if m1 > 0 else None,
                           "smallest_fork_dose_m_ge_0.05": dmin, "max_fork_dose_mass": max(mT.values()) if mT else 0}
        import arms8
        rank_of = {}
        for n in nodes:
            p = CACHE_DIR / "nodes" / f"{unit}_{n}.json"
            if p.exists():
                rank_of[n] = {t: rk for rk, t in arms8.hr_tokens(read_json(p))}
        for r in rows:
            if not r.get("rank"):
                r["rank"] = rank_of.get(r["node"], {}).get(int(r["token"]))
        hr_counts = Counter(r["idea"] for r in rows if r["passed"])
        out["units"][unit] = {"has_new_HR_branches": has_hr, "n_programs": len(rows),
                              "n_correct": sum(r["passed"] for r in rows), "ideas_HR": sorted(ideas_hr),
                              "ideas_HR_counts": dict(hr_counts), "ideas_K": ideas_k, "ideas_Kstar": sorted(kstar),
                              "ideas_global_T": sorted(kglob), "ideas_forced": sorted(forced_ideas(unit)),
                              "HR_only": hr_only, "reachability": reach,
                              "ranks_of_HR_only": {i: sorted({(r["node"], r.get("rank") or 0) for r in rows
                                                              if r["idea"] == i and r["passed"]}) for i in hr_only}}
        n_units_extra += int(len(hr_only) >= 1)
    out["n_units_HR_minus_Kstar_ge_1"] = n_units_extra
    write_json(RESULTS_DIR / "hr.json", out)
    return out


if __name__ == "__main__":
    import json
    adj_p = RESULTS_DIR / "adjudicated_labels.json"
    r = run(read_json(adj_p) if adj_p.exists() else None)
    print(json.dumps({u: {k: v[k] for k in ("ideas_HR", "ideas_Kstar", "HR_only", "n_programs")}
                      for u, v in r["units"].items()}, indent=1))
