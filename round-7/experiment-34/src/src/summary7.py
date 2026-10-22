#!/usr/bin/env python3
"""Timing, sample counts and spend summary -> results/timing_summary.json, results/costs.json (merged)."""
import sys
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from c7 import DATA, RESULTS, read_json, read_jsonl, utc_now, write_json  # noqa: E402

t = read_jsonl(RESULTS / "timing.jsonl")
by = defaultdict(float)
for r in t:
    by[r["stage"]] += r["seconds"]
counts = {}
for name in ("samples_raw", "samples_raw_s0b", "samples_raw_clamp", "samples_raw_force"):
    rows = read_jsonl(DATA / f"{name}.jsonl")
    counts[name] = {"n": len(rows), "by_task": dict(Counter(r["task"] for r in rows))}
fork = read_jsonl(DATA / "fork_continuations.jsonl")
counts["fork_continuations"] = {"n": len(fork), "by_task": dict(Counter(r["task"] for r in fork)),
                                "by_stage": dict(Counter(r["stage"] for r in fork))}
gen_total = sum(v["n"] for k, v in counts.items() if k.startswith("samples_raw"))
write_json(RESULTS / "timing_summary.json", {"utc": utc_now(), "gpu_seconds_by_stage": dict(by),
                                             "gpu_seconds_total_logged": sum(by.values()), "counts": counts,
                                             "generated_programs_total": gen_total})
judge = 0.0
for p in (RESULTS / "openrouter_cost_paths.json",):
    if p.exists():
        try:
            judge += float(read_json(p).get("total_usd", read_json(p).get("usd", 0.0)) or 0.0)
        except (AttributeError, TypeError, ValueError):
            pass
calls = read_jsonl(DATA / "judge_calls.jsonl")
nov = sum(float(c.get("cost") or 0) for c in calls)
write_json(RESULTS / "costs.json", {"utc": utc_now(), "openrouter_usd_labeller_judges": judge,
                                    "openrouter_usd_novelty": nov, "openrouter_usd_total": judge + nov,
                                    "cap_usd": 0.5})
print(gen_total, dict(by))
