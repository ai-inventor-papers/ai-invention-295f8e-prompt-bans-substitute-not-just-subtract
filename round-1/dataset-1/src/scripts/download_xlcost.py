#!/usr/bin/env python3
"""Download the XLCoST Python program-level text-to-code subset (codeparrot/xlcost-text-to-code).

The Hub repo ships a loading script, which datasets>=4 no longer executes, so this reads the
Hub's auto-converted parquet branch (refs/convert/parquet) at a pinned commit of that branch
and writes the same full_/mini_/preview_ JSON files as the aii-hf-datasets download script.
"""

import argparse
import json
import sys
from pathlib import Path

from datasets import load_dataset
from huggingface_hub import HfApi
from loguru import logger

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
ROOT = Path(__file__).resolve().parent.parent
logger.add(ROOT / "logs" / "download" / "xlcost.log", rotation="30 MB", level="DEBUG")

REPO = "codeparrot/xlcost-text-to-code"
CONFIG = "Python-program-level"
DEFAULT_OUT_DIR = ROOT / "temp" / "datasets" / "xlcost_python_program_level"


def truncate(obj: object, n: int = 200) -> object:
    """Recursively truncate strings, mirroring the preview files of aii-hf-datasets."""
    if isinstance(obj, str):
        return obj if len(obj) <= n else obj[:n] + "..."
    if isinstance(obj, dict):
        return {k: truncate(v, n) for k, v in obj.items()}
    if isinstance(obj, list):
        return [truncate(v, n) for v in obj]
    return obj


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    out_dir = ap.parse_args().out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    refs = HfApi().list_repo_refs(REPO, repo_type="dataset")
    parquet_sha = next(c.target_commit for c in refs.converts if c.name == "parquet")
    logger.info(f"{REPO} refs/convert/parquet commit: {parquet_sha}")
    for split in ("train", "validation", "test"):
        files = f"hf://datasets/{REPO}@{parquet_sha}/{CONFIG}/{split}/*.parquet"
        try:
            ds = load_dataset("parquet", split="train", data_files=files)
        except FileNotFoundError:
            logger.error(f"No parquet files for split {split}: {files}")
            raise
        rows = [dict(r) | {"config": CONFIG, "split": split} for r in ds]
        stem = f"codeparrot_xlcost-text-to-code_{CONFIG}_{split}"
        (out_dir / f"full_{stem}.json").write_text(json.dumps(rows, ensure_ascii=False))
        (out_dir / f"mini_{stem}.json").write_text(json.dumps(rows[:3], ensure_ascii=False, indent=1))
        (out_dir / f"preview_{stem}.json").write_text(json.dumps(truncate(rows[:3]), ensure_ascii=False, indent=1))
        full = out_dir / f"full_{stem}.json"
        logger.info(f"{split}: {len(rows)} rows -> {full.relative_to(ROOT).as_posix() if full.is_relative_to(ROOT) else full.name}")
    (out_dir / "SOURCE.json").write_text(json.dumps({"repo": REPO, "config": CONFIG, "parquet_branch_commit": parquet_sha}, indent=1))


if __name__ == "__main__":
    main()
