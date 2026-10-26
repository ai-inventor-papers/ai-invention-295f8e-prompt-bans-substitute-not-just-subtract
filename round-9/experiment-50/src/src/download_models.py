#!/usr/bin/env python3
"""Download the six model revisions used by this artifact into the shared HF cache (HF_HUB_CACHE).

Usage: python src/download_models.py [model_id ...]   (default: all six, in the order the stages need them)
Writes predictions/model_revisions.json with the resolved snapshot commit of every model.
"""
import json
import sys
import time
from pathlib import Path

from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parents[1]
# pinned revisions: iteration-8 pins where they exist; the two models new in iteration 9 (gemma-3-4b-pt,
# Llama-3.1-8B) are resolved from 'main' at first download and the resolved commit is recorded and reused.
MODELS = {
    "Qwen/Qwen3-8B": "b968826d9c46dd6066d109eabc6255188de91218",
    "Qwen/Qwen3-8B-Base": "49e3418fbbbca6ecbdf9608b4d22e5a407081db4",
    "google/gemma-3-4b-it": "093f9f388b31de276ce2de164bdc2081324b9767",
    "google/gemma-3-4b-pt": None,
    "meta-llama/Llama-3.1-8B-Instruct": "0e9e39f249a16976918f6564b8830bc894c89659",
    "meta-llama/Llama-3.1-8B": None,
}
PATTERNS = ["*.json", "*.safetensors", "*.model", "*.txt", "tokenizer*"]
IGNORE = ["original/*"]


def main() -> None:
    out = ROOT / "predictions" / "model_revisions.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    rec = json.loads(out.read_text()) if out.exists() else {}
    wanted = sys.argv[1:] or list(MODELS)
    for mid in wanted:
        rev = MODELS[mid] or rec.get(mid, {}).get("snapshot") or "main"
        t0 = time.time()
        path = snapshot_download(mid, revision=rev, allow_patterns=PATTERNS, ignore_patterns=IGNORE, max_workers=8)
        rec[mid] = {"requested_revision": rev, "snapshot": Path(path).name, "seconds": round(time.time() - t0, 1)}
        out.write_text(json.dumps(rec, indent=1))
        print(mid, rev, path, f"{time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
