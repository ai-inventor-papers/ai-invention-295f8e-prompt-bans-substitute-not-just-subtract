#!/usr/bin/env python3
"""Fingerprint the downloaded sources so a fresh download can be checked against the one used here.

For every full_*.json stem (split parts concatenated in natural order): row count and the SHA-256 of
the rows serialised canonically (sort_keys, ensure_ascii=False, no whitespace). For every git
repository: the checked-out commit and the SHA-256 over (relative path, file SHA-256) of all tracked
working-tree files except .git.

    .venv/bin/python scripts/source_fingerprints.py                      # write logs/source_fingerprints.json
    .venv/bin/python scripts/source_fingerprints.py --check              # compare temp/datasets with it
    .venv/bin/python scripts/source_fingerprints.py --check --data-dir X # compare another download
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent.parent
RECORD = ROOT / "logs" / "source_fingerprints.json"

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")


def natural(p: Path) -> list:
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", p.as_posix())]


def fingerprint(data_dir: Path) -> dict:
    out: dict[str, dict] = {}
    stems: dict[str, list[Path]] = defaultdict(list)
    for f in data_dir.rglob("full_*.json"):
        if "github" in f.relative_to(data_dir).parts:
            continue
        stem = re.sub(r"_\d+$", "", f.stem) if f.parent.name == re.sub(r"_\d+$", "", f.stem) else f.stem
        key = f.parent.relative_to(data_dir).as_posix() if f.parent.name == stem else f.relative_to(data_dir).with_suffix("").as_posix()
        stems[key].append(f)
    for key, files in sorted(stems.items()):
        h, n = hashlib.sha256(), 0
        for f in sorted(files, key=natural):
            for row in json.loads(f.read_text()):
                h.update(json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode())
                n += 1
        out[key] = {"rows": n, "sha256": h.hexdigest()}
    gh = data_dir / "github"
    for repo in sorted(p for p in gh.iterdir() if p.is_dir()) if gh.exists() else []:
        commit = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        files = subprocess.run(["git", "-C", str(repo), "ls-files"], capture_output=True, text=True, check=True).stdout.splitlines()
        h = hashlib.sha256()
        for rel in sorted(files):
            h.update(rel.encode() + b"\0" + hashlib.sha256((repo / rel).read_bytes()).hexdigest().encode())
        out[f"github/{repo.name}"] = {"commit": commit, "n_files": len(files), "tree_sha256": h.hexdigest()}
    return out


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=ROOT / "temp" / "datasets")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    fp = fingerprint(args.data_dir.resolve())
    if not args.check:
        RECORD.write_text(json.dumps(fp, indent=1))
        logger.info(f"wrote {RECORD.relative_to(ROOT)} ({len(fp)} entries)")
        return
    ref = json.loads(RECORD.read_text())
    bad = sorted(k for k in set(ref) | set(fp) if ref.get(k) != fp.get(k))
    for k in bad:
        logger.error(f"mismatch {k}: recorded={ref.get(k)} found={fp.get(k)}")
    logger.info(f"{len(ref) - len(bad)}/{len(ref)} recorded entries match")
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
