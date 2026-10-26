#!/usr/bin/env python3
"""Append hand-read rows: hand_record.py '<uid>|ACCEPT|<reason>' ... (uid itself contains '|'; split from the right)."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
rows = {json.loads(l)["uid"]: json.loads(l) for l in (ROOT / "data/programs_v10.jsonl").read_text().splitlines() if l.strip()}
with (ROOT / "data/hand_reads_v10.jsonl").open("a") as fh:
    for arg in sys.argv[1:]:
        uid, verdict, reason = arg.rsplit("|", 2)
        assert verdict in ("ACCEPT", "REJECT"), verdict
        assert uid in rows, f"unknown uid {uid}"
        fh.write(json.dumps({"uid": uid, "cell": rows[uid]["cell"], "verdict": verdict, "reason": reason,
                             "reader": "executor (Claude, hand read of the raw program)",
                             "utc": datetime.now(timezone.utc).isoformat()}) + "\n")
print(f"recorded {len(sys.argv) - 1}")
