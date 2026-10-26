#!/usr/bin/env python3
"""Stage 1 analysis (blind locator): per base path, the label distribution of the 8 continuations at each prefix
length j (opening-classifier labels for 'decided' continuations, frozen-labeller labels otherwise); change points by
exp35 forks.change_points (Bayesian Dirichlet-multinomial single change point, P >= 0.9, own-share jump >= 0.4,
recursive) with a 1,000-shuffle permutation null (forks.perm_stat). The located decision index is j_tau - 1 (the
first prefix that contains the decision token starts the second segment). Success: within 1 token of index 10 or 11
(T10) / of |O|+1 (B3 cluster openings) on >= 4 of 6 paths (B3: of the paths following c0 or c1).
Writes results/locator.json; the classifier's agreement with full labels on 'decided' rows that were later completed
is not available (they stop early), so OC validity is re-checked on 200 completed Stage 2 programs.
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg8 import CONT_LABELS, CONTS, E35, RESULTS_DIR, SAMPLES, UNITS, read_jsonl, utc_now, write_json  # noqa: E402
import units8 as U8  # noqa: E402

if str(E35 / "src") not in sys.path:
    sys.path.append(str(E35 / "src"))
import forks as FK  # noqa: E402


def run() -> dict:
    labels = {r["sid"]: r for r in read_jsonl(CONT_LABELS)}
    rows = [r for r in read_jsonl(CONTS) if r.get("arm") == "LOC"]
    twin = {(r["unit"], r["slot"]): r for r in read_jsonl(SAMPLES) if r["arm"] == "A0"}
    out = {"utc": utc_now(), "units": {}}
    for unit in ("T10", "B3"):
        C = list(UNITS[unit]["catalogue"]) + ["other", "invalid", "undecided"]
        per = defaultdict(lambda: defaultdict(list))
        for r in rows:
            if r["unit"] != unit:
                continue
            L = labels.get(r["sid"])
            if L is None:
                continue
            lab = L.get("label")
            lab = lab if lab in C else ("invalid" if lab in ("invalid", "no_code", "label_error") else "other")
            per[r["base_slot"]][r["j"]].append(lab)
        known = [10, 11] if unit == "T10" else [n["pos"] for n in U8.nodes(unit)]
        res = {}
        n_ok = n_elig = 0
        cost = sum(len(v2) for v in per.values() for v2 in v.values())
        for p, series_d in sorted(per.items()):
            js = sorted(series_d)
            S = np.array([[Counter(series_d[j]).get(c, 0) for c in C] for j in js], dtype=float)
            tw = twin.get((unit, p), {})
            own = U8.classify_partial(unit, tw.get("text", "")) if tw else "undecided"
            own_i = C.index(own) if own in C else int(np.argmax(S.sum(0)))
            cps = FK.change_points(S, own_i)
            perm = FK.perm_stat(S, own_i, n_perm=1000, seed=p)
            located = [js[c["tau_idx"]] - 1 for c in cps]
            on_canon = bool(tw.get("reached_decision"))
            ok = any(min(abs(x - k) for k in known) <= 1 for x in located)
            if unit == "T10" or on_canon:
                n_elig += 1
                n_ok += int(ok)
            res[str(p)] = {"own_class": C[own_i], "js": js, "series": S.tolist(), "change_points":
                           [{k: v for k, v in c.items() if k != "post"} for c in cps], "located_index": located,
                           "perm": perm, "on_canonical_opening": on_canon, "within_1_of_known": ok,
                           "twin_decision_pos": tw.get("decision_pos")}
        out["units"][unit] = {"paths": res, "n_paths_ok": n_ok, "n_paths_eligible": n_elig,
                              "success": n_ok >= 4, "known_indices": known, "cost_continuations": cost,
                              "note": ("T10's twin is 100% union-find: T = 1 resampling has no outcome variance, so "
                                       "no change point can be located from twin base paths" if unit == "T10" else "")}
    # OC validity on completed Stage 2 programs (the OC label of the full text vs the frozen label)
    agree = Counter()
    for r in read_jsonl(CONTS):
        if r.get("arm") != "MAP" or r["unit"] not in ("T10", "B3") or r.get("finish_reason") == "decided":
            continue
        L = labels.get(r["sid"])
        if not L or L.get("label") not in UNITS[r["unit"]]["catalogue"]:
            continue
        oc = U8.classify_partial(r["unit"], r["text"])
        if oc == "undecided":
            agree[(r["unit"], "undecided")] += 1
        else:
            agree[(r["unit"], "agree" if oc == L["label"] else "disagree")] += 1
        if sum(v for k, v in agree.items() if k[0] == r["unit"]) >= 200 and r["unit"] == "B3":
            continue
    out["oc_validity"] = {f"{u}|{k}": v for (u, k), v in agree.items()}
    for u in ("T10", "B3"):
        a, d = agree.get((u, "agree"), 0), agree.get((u, "disagree"), 0)
        out["oc_validity"][f"{u}|agreement"] = a / (a + d) if a + d else None
    write_json(RESULTS_DIR / "locator.json", out)
    return out


if __name__ == "__main__":
    r = run()
    for u, v in r["units"].items():
        print(u, {k: v[k] for k in ("n_paths_ok", "n_paths_eligible", "success", "cost_continuations")},
              {p: x["located_index"] for p, x in v["paths"].items()})
    print(r["oc_validity"])
