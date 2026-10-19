#!/usr/bin/env python3
"""Write full_/mini_/preview_ versions of an exp_sel_data_out file.

Portable stand-in for the AI Inventor aii-json format script that was used in this step; it produces
byte-identical files:
  full_<stem>.json     the whole document, indent=2
  mini_<stem>.json     every dataset, first 3 examples each
  preview_<stem>.json  the mini document with every list cut to 3 items and every string to 200 characters + '...'

    .venv/bin/python scripts/format_mini_preview.py full_data_out.json
    # -> full_full_data_out.json, mini_full_data_out.json, preview_full_data_out.json (rename as in reproducibility.md)
"""

import argparse
import json
import sys
from pathlib import Path

from loguru import logger

MAX_ARRAY_ITEMS = 3
MAX_STRING_LENGTH = 200
TRUNCATE_MARKER = "..."

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")


def truncate_value(value: object) -> object:
    if isinstance(value, list):
        return [truncate_value(item) for item in value[:MAX_ARRAY_ITEMS]]
    if isinstance(value, str):
        return value[:MAX_STRING_LENGTH] + TRUNCATE_MARKER if len(value) > MAX_STRING_LENGTH else value
    if isinstance(value, dict):
        return {k: truncate_value(v) for k, v in value.items()}
    return value


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, default=None)
    args = ap.parse_args()
    data = json.loads(args.input.read_text())
    if not isinstance(data, dict) or not isinstance(data.get("datasets"), list):
        raise ValueError("expected an exp_sel_data_out document with a 'datasets' list")
    out_dir = args.output_dir or args.input.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = args.input.stem
    mini = {**data, "datasets": [{**ds, "examples": ds.get("examples", [])[:MAX_ARRAY_ITEMS]} for ds in data["datasets"]]}
    for prefix, doc in (("full", data), ("mini", mini), ("preview", truncate_value(mini))):
        path = out_dir / f"{prefix}_{stem}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)
        logger.info(f"wrote {path.name}")


if __name__ == "__main__":
    main()
