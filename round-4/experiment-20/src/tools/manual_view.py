#!/usr/bin/env python3
"""Print every stress-passing audit program beside its 3 nearest known solutions and the judges' verdicts, for the
executor's manual pass (verdicts are written to audit/manual_pass.jsonl as {"id", "verdict", "reason"})."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from audit import KNOWN, nearest_known  # noqa: E402
from cfg import read_jsonl  # noqa: E402

pool = json.loads((ROOT / "audit" / "novelty_audit_pool.json").read_text())
known = read_jsonl(KNOWN)
by = {}
for k in known:
    by.setdefault(k["task"], []).append(k)
done = {r["id"] for r in read_jsonl(ROOT / "audit" / "manual_pass.jsonl")}
for x in pool["records"]:
    if x["id"] in done and "--all" not in sys.argv:
        continue
    print("=" * 100)
    print(x["id"], "arms:", x["arms"], "stress:", x["stress"])
    if x["stress"]["passed"]:
        print("judge A:", (x.get("judge_A") or {}).get("class"), "| B:", (x.get("judge_B") or {}).get("class"),
              "| tie:", (x.get("tiebreak") or {}).get("class") if x.get("tiebreak") else None, "| resolved:",
              x.get("resolved_class"))
        print("A says:", (x.get("judge_A") or {}).get("rationale"))
    print("--- program")
    print(x["code"])
    if "--neigh" in sys.argv:
        for n in nearest_known(x["code"], by.get(x["task"], []), 3):
            print(f"--- nearest known [{n['source']} | {n['mode_hint']} | J={n['similarity']}]")
            print(n["code"][:700])
