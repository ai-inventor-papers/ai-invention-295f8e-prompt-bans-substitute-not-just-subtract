#!/usr/bin/env python3
"""results/costs.json: OpenRouter spend by purpose (usage.cost) and GPU/wall time by stage."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg4 import LOG_DIR, RESULTS_DIR, read_jsonl, write_json  # noqa: E402


def rj(p):
    return json.loads(p.read_text()) if p.exists() else {}


bench = sum(r.get("cost", 0.0) or 0.0 for r in read_jsonl(LOG_DIR / "openrouter_spend.jsonl"))
out = {"openrouter_usd": {"masked_descriptions": rj(RESULTS_DIR / "openrouter_cost_describe.json").get("usd", 0.0),
                          "path_judge": rj(RESULTS_DIR / "openrouter_cost_paths.json").get("total_usd", 0.0),
                          "bench_judge": bench,
                          "novelty_audit": sum(r.get("cost", 0.0) or 0.0 for r in
                                               read_jsonl(RESULTS_DIR.parent / "data" / "novelty_cache.jsonl"))}}
out["openrouter_usd"]["total"] = sum(out["openrouter_usd"].values())
tim = read_jsonl(RESULTS_DIR / "timing.jsonl")
by = {}
for r in tim:
    by.setdefault(r["stage"], 0.0)
    by[r["stage"]] += r["seconds"]
out["sampling_seconds_by_stage"] = by
out["sampling_gpu_hours"] = sum(by.values()) / 3600
out["n_batches"] = len(tim)
write_json(RESULTS_DIR / "costs.json", out)
print(out)
