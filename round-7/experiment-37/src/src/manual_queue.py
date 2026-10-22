#!/usr/bin/env python3
"""Print the manual-read queue (results/adjudication.json 'manual_queue') for the executor's reads: each program with
its judge votes, named algorithms and core ideas, nearest known solution and empirical complexity. The reads are
recorded by hand in results/manual_reads.jsonl ({id, class, named_algorithm, rationale, reader, utc})."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, RESULTS, read_json, read_jsonl  # noqa: E402
from prompts import strip_code  # noqa: E402


def main(start: int = 0, n: int = 10, max_lines: int = 40) -> None:
    adj = read_json(RESULTS / "adjudication.json")
    cx = read_json(DATA / "complexity.json") if (DATA / "complexity.json").exists() else {}
    rows = {}
    for t in ("T2", "T03", "A3"):
        for r in read_jsonl(DATA / f"rows_{t}.jsonl"):
            rows[r["id"]] = r
    for r in read_jsonl(DATA / "rows_L.jsonl"):
        rows[r["id"]] = r
    done = {m["id"] for m in read_jsonl(RESULTS / "manual_reads.jsonl")}
    q = [x for x in adj["manual_queue"] if x["id"] not in done]
    print(f"queue {len(adj['manual_queue'])}, remaining {len(q)}")
    for item in q[start:start + n]:
        i = item["id"]
        rec = adj["per_candidate"][i]
        r = rows.get(i, {})
        c = cx.get(i, {})
        slope = c.get("loglog_slope")
        print("=" * 100)
        print(f"{i} | reason {item['reason']} | votes {rec['votes']} | named {rec['named']}")
        print(f"ideas: {rec['core_ideas']}")
        print(f"label {r.get('runtime_label')}/{r.get('ast_label')} | s {r.get('nearest_known_sim')} nearest "
              f"{r.get('nearest_known_id')} | slope {slope if slope is None else round(slope, 2)} | "
              f"stress {[p.get('status') for p in c.get('points', [])]}")
        print("\n".join(strip_code(r.get("code") or "").splitlines()[:max_lines]))


if __name__ == "__main__":
    a = [int(x) for x in sys.argv[1:]]
    main(*a)
