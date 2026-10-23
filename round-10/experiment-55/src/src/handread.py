#!/usr/bin/env python3
"""Hand-read support: compact views of scrubbed programs (the lines that decide discipline and container) and an
append-only record data/hand_reads.jsonl {uid, set, read_disc, read_cont, read_class, rationale, reader, utc}.

  python src/handread.py show <jsonl> <uid-substring or field=value,...> [max_lines]
  python src/handread.py record <json list of reads>
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import append_jsonl, read_jsonl, utc_now  # noqa: E402
from tpg2 import DATA  # noqa: E402

KEY = re.compile(r"pop|push|append|insort|sort|choice|random|shuffle|while|deque|heap|min\(|max\(|limit|depth|bound|"
                 r"for .* in .*range|return|def |visited|dist|<|>|jump|parent|\bset\(|\.add\(|remove|discard|"
                 r"changed|frontier|queue|stack|open|closed", re.IGNORECASE)
HAND = DATA / "hand_reads.jsonl"


def compact(code: str, max_lines: int = 26) -> str:
    out = []
    for ln in code.splitlines():
        s = ln.rstrip()
        if not s.strip():
            continue
        if KEY.search(s) and not s.strip().startswith(("if not grid", "rows =", "cols =")):
            out.append(s if len(s) <= 110 else s[:107] + "...")
    if len(out) > max_lines:
        out = out[:max_lines] + [f"   ... (+{len(out) - max_lines} lines)"]
    return "\n".join(out)


def show(path: str, sel: str, max_lines: int = 26) -> None:
    rows = read_jsonl(Path(path))
    conds = [c.split("=", 1) for c in sel.split(",") if "=" in c]
    for r in rows:
        if not r.get("valid"):
            continue
        if conds:
            if not all(str(r.get(k)) == v for k, v in conds):
                continue
        elif sel not in r["uid"]:
            continue
        print(f"### {r['uid']} | measured {r.get('disc')}/{r.get('cont')} ({r.get('fine')}) | "
              f"req {r.get('requested_cell') or r.get('algorithm') or r.get('family_v9')}")
        print(compact(r["scrubbed"], max_lines))


def record(reads: list[dict]) -> None:
    for x in reads:
        append_jsonl(HAND, {**x, "reader": "executor (Claude, hand read of the scrubbed code)", "utc": utc_now()})
    print(f"recorded {len(reads)}")


if __name__ == "__main__":
    if sys.argv[1] == "show":
        show(sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 26)
    elif sys.argv[1] == "record":
        record(json.loads(Path(sys.argv[2]).read_text()))
