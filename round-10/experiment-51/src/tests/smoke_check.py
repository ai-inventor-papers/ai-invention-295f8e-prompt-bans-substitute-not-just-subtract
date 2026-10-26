#!/usr/bin/env python3
"""S2 smoke diagnostics: validity, truncation, error types, j histograms, req2 id check, 5 bodies per arm."""
import collections, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
run = sys.argv[1] if len(sys.argv) > 1 else "smoke"
rows = [json.loads(l) for l in (ROOT / "data" / run / "programs.jsonl").read_text().splitlines()]
ids = {json.loads(l)["pid"]: json.loads(l)["ids"] for l in (ROOT / "data" / run / "completion_ids.jsonl").read_text().splitlines()}
out = {}
for arm in sorted({r["arm"] for r in rows}):
    rs = [r for r in rows if r["arm"] == arm]
    n = len(rs)
    d = {"n": n, "valid": sum(r["error_type"] == "ok" for r in rs) / n, "truncated": sum(r["truncated"] for r in rs) / n,
         "errors": dict(collections.Counter(r["error_type"] for r in rs)),
         "mean_tokens": sum(r["n_gen_tokens"] for r in rs) / n, "best_F": min([r["F"] for r in rs if r["F"] is not None] or [None]),
         "dup": sum(r["duplicate"] for r in rs)}
    forks = [r["fork"] for r in rs if r.get("fork")]
    if forks:
        js = [f.get("j") for f in forks if not f.get("unforced")]
        d["j_hist"] = dict(sorted(collections.Counter(js).items()))
        d["unforced"] = sum(bool(f.get("unforced")) for f in forks)
        d["nE_lt2"] = sum(f["n_E"] < 2 for f in forks)
        ok_ids = []
        for r in rs:
            f = r.get("fork")
            if f and not f.get("unforced"):
                cid = ids[r["pid"]]
                ok_ids.append(f["req2_prompt_len"] == r["prompt_len"] + f["j"] + 1 and len(cid) > f["j"] and cid[f["j"]] == f["forced_id"])
        d["req2_ids_ok"] = f"{sum(ok_ids)}/{len(ok_ids)}"
        d["forced_rank_hist"] = dict(collections.Counter(f.get("forced_rank") for f in forks if not f.get("unforced")))
        d["class_at_j"] = dict(collections.Counter(f.get("class_realised") for f in forks if not f.get("unforced")))
    out[arm] = d
print(json.dumps(out, indent=1))
for arm in sorted({r["arm"] for r in rows}):
    print("=" * 30, arm)
    for r in [r for r in rows if r["arm"] == arm][:5]:
        print(f"--- {r['pid']} k={r['k']} {r['error_type']} F={r['F']} trunc={r['truncated']}")
        print((r["code"] or "")[:500])
(ROOT / "results" / f"{run}_check.json").write_text(json.dumps(out, indent=1))
