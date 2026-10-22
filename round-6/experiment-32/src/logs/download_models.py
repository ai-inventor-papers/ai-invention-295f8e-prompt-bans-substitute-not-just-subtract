"""Download the two pinned Qwen3-8B snapshots into the run's shared HF cache (HF_HUB_CACHE)."""
import sys, time
from huggingface_hub import snapshot_download
repo, rev = sys.argv[1], sys.argv[2]
t0 = time.time()
p = snapshot_download(repo_id=repo, revision=rev, allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model", "merges.txt", "vocab.json", "tokenizer*"], max_workers=8)
print(f"{repo}@{rev} -> {p} in {time.time()-t0:.0f}s", flush=True)
