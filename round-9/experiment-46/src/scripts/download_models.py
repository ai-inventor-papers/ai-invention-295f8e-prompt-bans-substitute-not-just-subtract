#!/usr/bin/env python3
"""Download the two pinned checkpoints into the run's shared Hugging Face cache (HF_HOME is NOT overridden)."""
import sys
import time

from huggingface_hub import snapshot_download

PINS = [("unsloth/Qwen3-32B-bnb-4bit", "7f721e74a6a8cc9ee352f7e49303a2c1705f9083"),
        ("Qwen/Qwen3-8B", "b968826d9c46dd6066d109eabc6255188de91218")]
for repo, rev in PINS:
    if len(sys.argv) > 1 and sys.argv[1] not in repo:
        continue
    t0 = time.time()
    p = snapshot_download(repo, revision=rev, max_workers=8)
    print(f"DONE {repo}@{rev[:8]} -> {p} in {time.time() - t0:.0f}s", flush=True)
