#!/usr/bin/env python3
"""S1 engine check: this run's bf16 rows against exp19's FP8 W8A8 rows at the same CRN keys.

Cells: T03|NEUTRAL, T03|RAND9002_a1.0, T2|NEUTRAL, T2|RAND9004_a1.0 (W1-W5 x k 0-9, exp17 ban unit, max_new 1024)
and the decoding-path rows T1.3 / TOPK10 on W1 (k 0-9) of T03 and T2 (exp19's 20-row batch shape). Reported:
byte-identical token sequences, per-slot label agreement, the JSD between the label compositions against a
template-resampling null (2,000 draws, threshold = null p95; exp19/exp21 method) and code_sha256 identity with the
exp19 rows. reuse_allowed[arm] = all of that arm's check rows byte-identical."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import DATA_DIR, INPUTS, RESULTS_DIR, read_jsonl, utc_now, write_json  # noqa: E402

CELLS = (("T03", "NEUTRAL"), ("T03", "RAND9002_a1.0"), ("T2", "NEUTRAL"), ("T2", "RAND9004_a1.0"),
         ("T03", "T1.3"), ("T03", "TOPK10"), ("T2", "T1.3"), ("T2", "TOPK10"))


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
    e19raw = {(r["task"], r["arm"], r["template"], int(r["slot"])): r
              for r in read_jsonl(INPUTS / "exp19" / "data" / "engine_check_raw.jsonl")}
    e19lab = {(r["task"], r["arm"], r["template"], int(r["slot"])): r
              for r in read_jsonl(INPUTS / "exp19" / "data" / "engine_check_labels.jsonl")}
    # exp19 decoding-path rows (T1.3 / TOPK10) from its merged samples
    for r in read_jsonl(INPUTS / "exp19" / "data" / "samples.jsonl"):
        if r.get("arm") in ("T1.3", "TOPK10") and r.get("template") == "W1" and r.get("task") in ("T03", "T2"):
            key = (r["task"], r["arm"], r["template"], int(r["slot"]))
            e19lab[key] = r
            e19raw.setdefault(key, r)
    ours_raw = {(r["task"], r["arm"], r["template"], int(r["slot"])): r for r in read_jsonl(DATA_DIR / "engine_check_raw.jsonl")}
    ours_lab = {(r["task"], r["arm"], r["template"], int(r["slot"])): r for r in read_jsonl(DATA_DIR / "engine_check_labels.jsonl")}
    rng = np.random.default_rng(20261021)
    out: dict[str, Any] = {"cells": {}, "utc": utc_now(),
                           "engines": {"this_run": "HF bf16 (RTX 4090)", "exp19": "HF FP8 W8A8 (RTX 2000 Ada)"}}
    reuse = {}
    for t, arm in CELLS:
        keys = sorted(k for k in ours_raw if k[0] == t and k[1] == arm)
        if not keys:
            continue
        both = [k for k in keys if k in e19raw]
        ident = sum(1 for k in both if e19raw[k].get("token_ids") is not None
                    and list(e19raw[k]["token_ids"]) == list(ours_raw[k]["token_ids"]))
        code_same = sum(1 for k in both if k in ours_lab and k in e19lab and ours_lab[k].get("code_sha256")
                        and ours_lab[k].get("code_sha256") == e19lab[k].get("code_sha256"))
        lab_both = [k for k in both if k in ours_lab and k in e19lab]
        agree = sum(1 for k in lab_both if ours_lab[k]["label"] == e19lab[k]["label"])
        a = Counter(e19lab[k]["label"] for k in lab_both)
        b = Counter(ours_lab[k]["label"] for k in lab_both)
        j = jsd(a, b)
        by_w: dict[str, list[str]] = {}
        for k in lab_both:
            by_w.setdefault(k[2], []).append(e19lab[k]["label"])
        ws = sorted(by_w)
        null = []
        if len(ws) > 1:
            for _ in range(2000):
                d1 = Counter(x for w in rng.choice(ws, size=len(ws)) for x in by_w[w])
                d2 = Counter(x for w in rng.choice(ws, size=len(ws)) for x in by_w[w])
                null.append(jsd(d1, d2))
        thr = float(np.nanpercentile(null, 95)) if null else None
        out["cells"][f"{t}|{arm}"] = {
            "n": len(keys), "n_paired": len(both), "byte_identical": ident, "code_sha256_identical": code_same,
            "per_slot_label_agreement": agree / len(lab_both) if lab_both else None,
            "exp19_composition": dict(a.most_common()), "this_run_composition": dict(b.most_common()),
            "exp19_pass": float(np.mean([bool(e19lab[k].get("passed")) for k in lab_both])) if lab_both else None,
            "this_run_pass": float(np.mean([bool(ours_lab[k].get("passed")) for k in lab_both])) if lab_both else None,
            "jsd": j, "null_p95": thr, "jsd_within_null": (j <= thr + 1e-12) if (thr is not None and np.isfinite(j)) else None,
            "first_divergence_median": float(np.median([next((i for i, (x, y) in enumerate(zip(e19raw[k]["token_ids"],
                                                       ours_raw[k]["token_ids"])) if x != y), len(ours_raw[k]["token_ids"]))
                                                       for k in both if e19raw[k].get("token_ids") is not None]))
            if any(e19raw[k].get("token_ids") is not None for k in both) else None}
        reuse[arm] = reuse.get(arm, True) and (ident == len(both) and len(both) == len(keys))
    out["reuse_allowed"] = reuse
    agr = [v["per_slot_label_agreement"] for v in out["cells"].values() if v["per_slot_label_agreement"] is not None]
    out["verdict"] = ("BYTE-IDENTICAL" if all(reuse.values()) else
                      ("LABEL-REPRODUCED (precision sensitivity small)" if agr and min(agr) >= 0.9 and
                       all(v.get("jsd_within_null") in (True, None) for v in out["cells"].values())
                       else "PRECISION-SENSITIVE"))
    write_json(RESULTS_DIR / "engine_check.json", out)
    return out


if __name__ == "__main__":
    import json
    r = run()
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk in ("n", "byte_identical", "per_slot_label_agreement", "jsd", "null_p95")}
                      for k, v in r["cells"].items()}, indent=1), r["verdict"], r["reuse_allowed"])
