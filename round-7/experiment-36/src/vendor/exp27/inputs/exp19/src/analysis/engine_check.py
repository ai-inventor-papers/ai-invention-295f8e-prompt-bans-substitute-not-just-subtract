#!/usr/bin/env python3
"""Plan 3: engine check (positive control). This run's engine reproduces two exp17 screen rows with the screen's own
prompts, ban units (exp17 norms_T03/T2.npy), directions (rand_9002 on T03, rand_9004 on T2), CRN keys
u_stream(task, w, k) for k 0-9 of W1-W5 and the 20-row layout. Reports each composition against the screen, per-slot
label agreement, the JSD between the two compositions against a template-resampling null (2,000 draws: resample the
screen arm's 5 template blocks with replacement twice, JSD between the two resamples; threshold = the null's 95th
percentile) and the off-default excess over the twin. Verdict: REPRODUCED (JSD <= null p95 and excess >= 0.20 on both
rows), PARTIAL, or PRECISION-SENSITIVE (neither row reproduces)."""

from __future__ import annotations

from collections import Counter
from typing import Any

import numpy as np

from cfg import DATA_DIR, DEFAULT, E17, RESULTS_DIR, read_jsonl, utc_now, write_json

CELLS = (("T03", "NEUTRAL"), ("T03", "RAND9002_a1.0"), ("T2", "NEUTRAL"), ("T2", "RAND9004_a1.0"))


def _lab(r: dict[str, Any]) -> str:
    lab = r.get("label")
    if lab == "disputed":
        lab = r.get("fallback_label") or "other"
    return lab


def jsd(p: Counter, q: Counter) -> float:
    keys = sorted(set(p) | set(q))
    a = np.array([p.get(k, 0) for k in keys], float)
    b = np.array([q.get(k, 0) for k in keys], float)
    if a.sum() == 0 or b.sum() == 0:
        return float("nan")
    a /= a.sum()
    b /= b.sum()
    m = 0.5 * (a + b)

    def kl(x, y):
        nz = x > 0
        return float((x[nz] * np.log2(x[nz] / y[nz])).sum())

    return 0.5 * kl(a, m) + 0.5 * kl(b, m)


def run() -> dict[str, Any]:
    scr = {}
    for r in read_jsonl(E17 / "data" / "labels.jsonl"):
        if (r["task"], r["arm"]) in CELLS and int(r["sample_id"]) < 10:
            scr[(r["task"], r["arm"], r["template"], int(r["sample_id"]))] = {"label": _lab(r),
                                                                             "passed": bool(r.get("passed"))}
    ours = {}
    for r in read_jsonl(DATA_DIR / "engine_check_labels.jsonl"):
        ours[(r["task"], r["arm"], r["template"], int(r["slot"]))] = {"label": r["label"],
                                                                     "passed": bool(r.get("passed"))}
    rng = np.random.default_rng(20261021)
    out: dict[str, Any] = {"cells": {}, "utc": utc_now()}
    ok_rows = []
    for t, arm in CELLS:
        keys = sorted(k for k in scr if k[0] == t and k[1] == arm)
        a = Counter(scr[k]["label"] for k in keys)
        b = Counter(ours[k]["label"] for k in keys if k in ours)
        agree = sum(1 for k in keys if k in ours and ours[k]["label"] == scr[k]["label"])
        n_both = sum(1 for k in keys if k in ours)
        j = jsd(a, b)
        by_w: dict[str, list[str]] = {}
        for k in keys:
            by_w.setdefault(k[2], []).append(scr[k]["label"])
        ws = sorted(by_w)
        null = []
        for _ in range(2000):
            d1 = Counter(x for w in rng.choice(ws, size=len(ws)) for x in by_w[w])
            d2 = Counter(x for w in rng.choice(ws, size=len(ws)) for x in by_w[w])
            null.append(jsd(d1, d2))
        thr = float(np.nanpercentile(null, 95))
        out["cells"][f"{t}|{arm}"] = {"screen_composition": dict(a.most_common()),
                                       "this_run_composition": dict(b.most_common()),
                                       "screen_pass": float(np.mean([scr[k]["passed"] for k in keys])),
                                       "this_run_pass": float(np.mean([ours[k]["passed"] for k in keys if k in ours]))
                                       if n_both else None,
                                       "per_slot_label_agreement": agree / max(n_both, 1), "n": n_both,
                                       "JSD": j, "null_p95": thr, "JSD_within_null": bool(j <= thr)}
    for t, arm in CELLS:
        if arm == "NEUTRAL":
            continue
        c = out["cells"][f"{t}|{arm}"]
        tw = out["cells"][f"{t}|NEUTRAL"]
        D = DEFAULT[t]

        def offd(comp):
            n = sum(comp.values())
            return sum(v for k, v in comp.items() if k not in (D, "invalid")) / max(n, 1)
        c["excess_over_twin_this_run"] = offd(c["this_run_composition"]) - offd(tw["this_run_composition"])
        c["excess_over_twin_screen"] = offd(c["screen_composition"]) - offd(tw["screen_composition"])
        ok_rows.append(c["JSD_within_null"] and c["excess_over_twin_this_run"] >= 0.20)
    twin_ok = all(out["cells"][f"{t}|NEUTRAL"]["this_run_composition"].get(DEFAULT[t], 0) /
                  max(1, sum(out["cells"][f"{t}|NEUTRAL"]["this_run_composition"].values())) >= 0.9
                  for t in ("T03", "T2"))
    out["twin_modal_share_ge_0.9"] = bool(twin_ok)
    out["verdict"] = "REPRODUCED" if all(ok_rows) else ("PARTIAL" if any(ok_rows) else "PRECISION-SENSITIVE")
    out["note"] = ("This run uses the same FP8 W8A8 engine as the screen (16 GB RTX 2000 Ada; device table), so the "
                   "check measures engine reproduction, not an FP8-vs-bf16 gap.")
    write_json(RESULTS_DIR / "engine_check.json", out)
    return out


if __name__ == "__main__":
    import json

    r = run()
    print(json.dumps({k: v for k, v in r.items() if k != "cells"}, indent=1))
    for k, v in r["cells"].items():
        print(k, {x: v[x] for x in ("per_slot_label_agreement", "JSD", "null_p95", "this_run_pass", "screen_pass")},
              v["this_run_composition"], v["screen_composition"])
