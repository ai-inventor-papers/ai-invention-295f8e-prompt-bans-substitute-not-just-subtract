#!/usr/bin/env python3
"""Engine check evaluation: iteration-6 regenerated exp28 slots (twin slots 0-1 x W1-W5 x 15 tasks; the exp28 R6
escaping direction at alpha 2, slots 0-1) vs exp28's rows: per-slot label agreement (target >= 0.9), token-byte
identity share, and JS(old, new) of the pooled label composition vs a template-resampling null p95."""
from __future__ import annotations

import collections
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import DATA_DIR, E28_DATA, RESULTS_DIR, read_jsonl, write_json
from analysis_E import js_divergence


def main() -> None:
    new_raw = {r["row_id"]: r for r in read_jsonl(DATA_DIR / "raw_engine6.jsonl")}
    labs = {r["row_id"]: r for r in read_jsonl(DATA_DIR / "labels.jsonl")}
    old_lab = {r["row_id"]: r for r in read_jsonl(E28_DATA / "labels.jsonl")}
    old_raw = {r["row_id"]: r for f in ("raw_twin.jsonl", "raw_push.jsonl") for r in read_jsonl(E28_DATA / f)}
    pairs = []
    for rid, r in new_raw.items():
        _, t, w, arm, k = rid.split("|")
        oid = f"twin|{t}|{w}|twin|{k}" if arm == "twin" else f"push|{t}|{w}|{arm}|{k}"
        if oid not in old_lab or rid not in labs:
            continue
        o, n = old_lab[oid], labs[rid]
        pairs.append({"task": t, "arm": arm, "slot": int(k), "template": w, "old": o["label"], "new": n["label"],
                      "old_pass": bool(o.get("passed")), "new_pass": bool(n.get("passed")),
                      "same_label": o["label"] == n["label"], "same_pass": bool(o.get("passed")) == bool(n.get("passed")),
                      "byte_identical": old_raw.get(oid, {}).get("token_ids") == r["token_ids"]})
    n = len(pairs)
    agree = sum(p["same_label"] for p in pairs) / max(n, 1)
    byte = sum(p["byte_identical"] for p in pairs) / max(n, 1)
    old_c = collections.Counter(p["old"] for p in pairs)
    new_c = collections.Counter(p["new"] for p in pairs)
    js = js_divergence(dict(old_c), dict(new_c))
    # template-resampling null: JS between two random halves of the exp28 twin labels (slots 0-9) per task pooled
    rng = np.random.default_rng(0)
    tw = [r for r in old_lab.values() if r.get("stage") == "twin"]
    by_t = collections.defaultdict(list)
    for r in tw:
        by_t[r["task"]].append(r["label"])
    null = []
    for _ in range(1000):
        a, b = collections.Counter(), collections.Counter()
        for t, labs_t in by_t.items():
            idx = rng.permutation(len(labs_t))
            a.update(labs_t[i] for i in idx[:10])
            b.update(labs_t[i] for i in idx[10:20])
        null.append(js_divergence(dict(a), dict(b)))
    res = {"n_pairs": n, "per_slot_label_agreement": agree, "pass_agreement": sum(p["same_pass"] for p in pairs) / max(n, 1),
           "byte_identity_share": byte, "js_old_new": js, "js_null_p95": float(np.quantile(null, 0.95)),
           "pass": agree >= 0.9 and js <= float(np.quantile(null, 0.95)),
           "by_arm": {a: sum(p["same_label"] for p in pairs if p["arm"] == a) / max(1, sum(1 for p in pairs if p["arm"] == a))
                      for a in sorted({p["arm"] for p in pairs})},
           "disagreements": [p for p in pairs if not p["same_label"]][:30]}
    write_json(RESULTS_DIR / "engine_check6.json", res)
    print({k: v for k, v in res.items() if k != "disagreements"})


if __name__ == "__main__":
    main()
