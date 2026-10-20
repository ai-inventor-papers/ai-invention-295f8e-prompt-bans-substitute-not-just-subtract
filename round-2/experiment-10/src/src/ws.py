#!/usr/bin/env python3
"""Workspace bridge: puts the copied canonical suite (./canon) on sys.path and redirects every cache the canon code
writes (program evaluation cache, judge cache, OpenRouter cost ledger) into this workspace, so canon files are never
edited. Import this module before any canon module."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Iterable

WS = Path(__file__).resolve().parent.parent
CANON = WS / "canon"
DATA = WS / "data"
FRLP_DIR = WS / "frlp"
RESULTS = WS / "results"
FIGS = WS / "figures"
LOGS = WS / "logs"
for _d in (DATA, FRLP_DIR, RESULTS, FIGS, LOGS):
    _d.mkdir(parents=True, exist_ok=True)

if str(CANON) not in sys.path:
    sys.path.insert(0, str(CANON))

import common as C  # noqa: E402  (canon)

# Dataset artifact art_j3Rm_lr2nzR6 (neutral nouns, scrubber stress test): published as a sibling folder of this one.
# Override with AII_DEP_DATASET=<path to its full_data_out.json>.
DEP_DATASET_DEFAULT = WS.parent / "art_j3Rm_lr2nzR6" / "full_data_out.json"


def _find_up(pred) -> Path | None:
    for parent in [WS, *WS.parents]:
        if pred(parent):
            return parent
    return None


def dependency_dataset() -> Path:
    import os

    return Path(os.environ.get("AII_DEP_DATASET") or DEP_DATASET_DEFAULT)


def skills_dir() -> Path:
    """Directory holding the aii-* skills (override: AII_SKILLS_DIR)."""
    import os

    env = os.environ.get("AII_SKILLS_DIR")
    hit = Path(env) if env else _find_up(lambda d: (d / ".claude" / "skills" / "aii-data-fig-gen" / "scripts").is_dir())
    if hit is None:
        raise FileNotFoundError("set AII_SKILLS_DIR")
    return hit if env else hit / ".claude" / "skills"


MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct"
MODEL_TAG = "llama-3.1-8b-instruct"
DECODING = "T1.0_topp1.0_topk-off_minp0_max1024_vllm0.11_bf16"
DECODING_FREE = "T1.0_topp1.0_topk-off_minp0_max48_vllm0.11_bf16"
JUDGE_TOTAL_CAP_USD = 0.50


def model_path() -> str:
    """Local snapshot of the recorded repo id + commit in the shared HF cache (downloads if absent)."""
    from huggingface_hub import snapshot_download

    rec = json.loads((RESULTS / "model_download.json").read_text())
    try:
        return snapshot_download(rec["repo_id"], revision=rec["commit_sha"], local_files_only=True)
    except Exception:  # noqa: BLE001 - not cached yet: fetch the weights (safetensors + configs only)
        return snapshot_download(rec["repo_id"], revision=rec["commit_sha"],
                                 allow_patterns=["*.json", "*.safetensors", "tokenizer*"])


def patch_canon_caches() -> None:
    """Point canon's on-disk caches at this workspace (never write inside ./canon)."""
    import pipeline as P
    import labeller.judge as J

    P.EVAL_CACHE = DATA / "program_eval_cache.jsonl"
    J.CACHE = DATA / "judge_cache.jsonl"
    J.COST_FILE = RESULTS / "openrouter_cost.json"


def read_jsonl(p: Path) -> list[dict[str, Any]]:
    return C.read_jsonl(Path(p))


def append_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> int:
    n = 0
    with Path(p).open("a") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, default=C._json_default) + "\n")
            n += 1
    return n


def write_json(p: Path, obj: Any, indent: int | None = 1) -> None:
    C.write_json(Path(p), obj, indent=indent)


def setup_logging(name: str) -> None:
    from loguru import logger

    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(str(LOGS / f"{name}.log"), rotation="30 MB", level="DEBUG")
