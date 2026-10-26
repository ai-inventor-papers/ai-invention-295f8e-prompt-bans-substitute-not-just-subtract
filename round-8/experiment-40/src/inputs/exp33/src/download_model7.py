#!/usr/bin/env python3
"""Download bf16 Qwen3-8B at the pinned revision into the run's shared HF cache (HF_HOME is NOT overridden)."""
import sys
from huggingface_hub import snapshot_download

REPO = "Qwen/Qwen3-8B"
REV = "b968826d9c46dd6066d109eabc6255188de91218"

if __name__ == "__main__":
    p = snapshot_download(repo_id=REPO, revision=REV, max_workers=16,
                          allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model", "merges.txt", "vocab.json"])
    print("DOWNLOADED", p)
    sys.exit(0)
