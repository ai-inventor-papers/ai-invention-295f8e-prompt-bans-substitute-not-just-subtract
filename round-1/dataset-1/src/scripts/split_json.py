#!/usr/bin/env python3
"""Split an oversized top-level-array JSON file into numbered parts under a byte limit (aii-file-size-limit).

full_<stem>.json  ->  full_<stem>/full_<stem>_1.json, full_<stem>_2.json, ...
plus mini_<stem>_<k>.json (first 3 rows) and preview_<stem>_<k>.json (first 3 rows, strings cut
to 200 chars) for every part. The original is deleted only after every part has been written and
re-read with the same total row count. Readers load the parts with:
    for f in sorted(glob.glob('full_<stem>/full_<stem>_*.json'), key=natural): rows.extend(json.load(open(f)))
"""

import argparse
import json
import sys
from pathlib import Path

from loguru import logger

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(Path(__file__).resolve().parent.parent / "logs" / "split_json.log", rotation="30 MB", level="DEBUG")


def truncate(obj: object, n: int = 200) -> object:
    if isinstance(obj, str):
        return obj if len(obj) <= n else obj[:n] + "..."
    if isinstance(obj, dict):
        return {k: truncate(v, n) for k, v in obj.items()}
    if isinstance(obj, list):
        return [truncate(v, n) for v in obj]
    return obj


def split_file(path: Path, max_bytes: int) -> list[Path]:
    rows = json.loads(path.read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path} is not a top-level JSON array")
    stem = path.stem.removeprefix("full_")
    out_dir = path.parent / f"full_{stem}"
    out_dir.mkdir(exist_ok=True)
    parts: list[list] = [[]]
    size = 2
    for row in rows:
        b = len(json.dumps(row, ensure_ascii=False).encode()) + 1
        if parts[-1] and size + b > max_bytes:
            parts.append([])
            size = 2
        parts[-1].append(row)
        size += b
    written = []
    for k, part in enumerate(parts, start=1):
        p = out_dir / f"full_{stem}_{k}.json"
        p.write_text(json.dumps(part, ensure_ascii=False))
        (out_dir / f"mini_{stem}_{k}.json").write_text(json.dumps(part[:3], ensure_ascii=False, indent=1))
        (out_dir / f"preview_{stem}_{k}.json").write_text(json.dumps(truncate(part[:3]), ensure_ascii=False, indent=1))
        written.append(p)
        logger.info(f"{p} rows={len(part)} size={p.stat().st_size / 1e6:.1f} MB")
    n_back = sum(len(json.loads(p.read_text())) for p in written)
    if n_back != len(rows):
        raise RuntimeError(f"row count mismatch after split: {n_back} != {len(rows)}; original kept")
    path.unlink()
    logger.info(f"split {path.name}: {len(rows)} rows into {len(written)} parts; original deleted")
    return written


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--max-mb", type=float, default=90.0)
    args = ap.parse_args()
    for f in args.files:
        split_file(f, int(args.max_mb * 1e6))


if __name__ == "__main__":
    main()
