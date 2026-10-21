"""Tiny bridge so newbench/common/label5 can rebuild the plain-completion prompt text without importing torch."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_P: dict[str, str] = {}


def plainc_text(unit: str) -> str:
    if not _P:
        for l in (ROOT / "data" / "prompts_new.jsonl").read_text().splitlines():
            r = json.loads(l)
            if r["kind"] == "plainc":
                _P[r["task"]] = r["user_text"]
    return _P[unit]
