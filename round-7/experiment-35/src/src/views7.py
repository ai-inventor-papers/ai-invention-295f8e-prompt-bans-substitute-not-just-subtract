#!/usr/bin/env python3
"""Result views listed in the plan's Part H that are read straight from existing rows:
results/engine_check.json (B1: per-slot labels and token identity vs iteration 6 at the same slot keys),
results/calibration.json (C7 per unit), results/topk_report.json (top-k 10 truncation: minority fork tokens outside
the top 10, total mass outside the top 10 at every fork, and same-seed token identity of the top-k 10 sweep)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analysis_T import rows_with_labels  # noqa: E402
from cfg7 import CACHE_DIR, I6, RESULTS_DIR, TEMPLATES, read_json, read_jsonl, write_json  # noqa: E402


def engine_check() -> dict:
    lab6 = {r["sample_id"]: r for r in read_jsonl(I6 / "data" / "labels.jsonl")}
    six = {}
    for r in read_jsonl(I6 / "data" / "samples_raw.jsonl"):
        if r["arm"] == "TWIN":
            six[(r["task"], r["template"], r["slot"])] = r
    rows = [r for r in rows_with_labels() if r["arm"] == "TWIN6"]
    out = {}
    for t in ("T2", "T03", "T1", "T10"):
        rr = [r for r in rows if r["unit"] == t]
        n = ag = same = 0
        first_div = []
        for r in rr:
            o = six.get((t, r["template"], r["slot"]))
            if o is None:
                continue
            ids = json.loads(o["token_ids"]) if isinstance(o["token_ids"], str) else o["token_ids"]
            n += 1
            same += ids == r["token_ids"]
            ag += lab6[o["sample_id"]]["label"] == r["label"]
            first_div.append(next((i for i, (a, b) in enumerate(zip(ids, r["token_ids"])) if a != b), None))
        out[t] = {"n": n, "label_agreement": ag / n if n else None, "token_identical": same,
                  "first_divergence_index": first_div, "decisive": t in ("T2", "T03"),
                  "pass_0.95": (ag / n >= 0.95) if n else None}
    out["note"] = ("same prompts and stream keys as iteration 6 (RTX 2000 Ada, CPU-resident embedding); this engine: "
                   "RTX 4090, whole model on the GPU; batch sizes differ, so differences measure kernel sensitivity")
    write_json(RESULTS_DIR / "engine_check.json", out)
    return out


def calibration() -> dict:
    F = read_json(RESULTS_DIR / "forks.json")
    out = {u: v["calibration"] for u, v in F.items()}
    write_json(RESULTS_DIR / "calibration.json", out)
    return out


def topk_report() -> dict:
    pv = read_json(RESULTS_DIR / "predictions_view.json")
    rows = [r for r in rows_with_labels() if r["arm"] == "SWEEP"]
    tab = {(r["unit"], r["cell"], r["template"], r["slot"]): r for r in rows}
    out = {}
    for u, U in pv["units"].items():
        tail = {}
        for cid in U.get("margins", {}):
            p = CACHE_DIR / "tf" / f"{u}_{cid}.npz"
            if not p.exists():
                continue
            z = np.load(p)
            m = {}
            for w in TEMPLATES:
                x = z[f"zf_{w}"].astype(np.float64)
                q = np.exp(x - x.max())
                q /= q.sum()
                m[w] = float(1 - np.sort(q)[-10:].sum())
            tail[cid] = m
        same = n = 0
        for (uu, c, w, s), r in tab.items():
            if uu == u and c.endswith("_p1") and (u, c.replace("_p1", "_k10"), w, s) in tab:
                n += 1
                same += tab[(u, c.replace("_p1", "_k10"), w, s)]["token_ids"] == r["token_ids"]
        out[u] = {"minority_fork_tokens_by_template": U["topk_report"], "fork_mass_outside_top10": tail,
                  "sweep_topk10_token_identical_to_topp1": [same, n]}
    write_json(RESULTS_DIR / "topk_report.json", out)
    return out


if __name__ == "__main__":
    e = engine_check()
    print({k: (v.get("label_agreement"), v.get("token_identical")) for k, v in e.items() if isinstance(v, dict)})
    calibration()
    t = topk_report()
    print({u: v["sweep_topk10_token_identical_to_topp1"] for u, v in t.items()})
