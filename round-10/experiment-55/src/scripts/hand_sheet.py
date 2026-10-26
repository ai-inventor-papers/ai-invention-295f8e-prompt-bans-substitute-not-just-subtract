#!/usr/bin/env python3
"""Print programs awaiting a hand read (verdict HAND, no row in data/hand_reads_v10.jsonl yet), compactly:
usage: hand_sheet.py <cell-or-class> [max]"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
rows = [json.loads(l) for l in (ROOT / "data/programs_v10.jsonl").read_text().splitlines() if l.strip()]
done = set()
hp = ROOT / "data/hand_reads_v10.jsonl"
if hp.exists():
    done = {json.loads(l)["uid"] for l in hp.read_text().splitlines() if l.strip()}
cell = sys.argv[1]
mx = int(sys.argv[2]) if len(sys.argv) > 2 else 6
n = 0
for r in rows:
    if r["cell"] != cell or r["verdict"] != "HAND" or r["uid"] in done or r.get("pilot"):
        continue
    dc = r.get("discipline_check") or r.get("topup_check") or {}
    print(f"##### {r['uid']}  tracer={(r.get('tracer') or {}).get('order_class_fine')} ast={dc.get('ast_signature')} "
          f"reasons={r['reasons']} hk={r.get('heur_key')}")
    code = r["raw_code"] or ""
    print("\n".join(l for l in code.splitlines() if l.strip() and not l.strip().startswith("#") and l.strip() not in ("return []", "return [start]")))
    n += 1
    if n >= mx:
        break
print(f"[{n} shown]")
