#!/usr/bin/env python3
"""Download the two pinned checkpoints into the run's shared Hugging Face cache (HF_HOME is NOT overridden).

Only the safetensors shards that hold the embedding table and the blocks below n_keep are fetched (the truncated
decoder never builds the upper blocks): Qwen3-8B shards 1-3 (blocks 0-27), Qwen3-32B-bnb-4bit shards 1-3 (blocks 0-52).
"""
import sys
import time

from huggingface_hub import snapshot_download

PINS = [("Qwen/Qwen3-8B", "b968826d9c46dd6066d109eabc6255188de91218",
         ["model-00001-of-00005.safetensors", "model-00002-of-00005.safetensors", "model-00003-of-00005.safetensors"]),
        ("unsloth/Qwen3-32B-bnb-4bit", "7f721e74a6a8cc9ee352f7e49303a2c1705f9083",
         ["model-00001-of-00004.safetensors", "model-00002-of-00004.safetensors", "model-00003-of-00004.safetensors"])]
META = ["*.json", "*.txt", "*.model", "tokenizer*", "merges.txt", "vocab.json"]
for repo, rev, shards in PINS:
    if len(sys.argv) > 1 and sys.argv[1] not in repo:
        continue
    t0 = time.time()
    p = snapshot_download(repo, revision=rev, allow_patterns=META + shards, max_workers=8)
    print(f"DONE {repo}@{rev[:8]} -> {p} in {time.time() - t0:.0f}s", flush=True)
