#!/usr/bin/env python3
"""Full snapshots of the two pinned checkpoints (the truncated loader still opens every shard listed in the index)."""
import time
from huggingface_hub import snapshot_download
for repo, rev in (("Qwen/Qwen3-8B", "b968826d9c46dd6066d109eabc6255188de91218"),
                  ("unsloth/Qwen3-32B-bnb-4bit", "7f721e74a6a8cc9ee352f7e49303a2c1705f9083")):
    t0 = time.time()
    p = snapshot_download(repo, revision=rev, max_workers=8)
    print(f"DONE {repo}@{rev[:8]} -> {p} in {time.time() - t0:.0f}s", flush=True)
