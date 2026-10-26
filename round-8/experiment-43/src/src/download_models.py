#!/usr/bin/env python3
"""Download the four model revisions used by this artifact into the shared HF cache (HF_HUB_CACHE)."""
import sys

from huggingface_hub import snapshot_download

MODELS = {
    "google/gemma-3-4b-it": "093f9f388b31de276ce2de164bdc2081324b9767",
    "meta-llama/Llama-3.1-8B-Instruct": "0e9e39f249a16976918f6564b8830bc894c89659",
    "Qwen/Qwen3-8B": "b968826d9c46dd6066d109eabc6255188de91218",
    "Qwen/Qwen3-8B-Base": "49e3418fbbbca6ecbdf9608b4d22e5a407081db4",
}
PATTERNS = ["*.json", "*.safetensors", "*.model", "*.txt", "tokenizer*"]

if __name__ == "__main__":
    wanted = sys.argv[1:] or list(MODELS)
    for mid in wanted:
        path = snapshot_download(mid, revision=MODELS[mid], allow_patterns=PATTERNS, max_workers=8)
        print(mid, MODELS[mid], path, flush=True)
