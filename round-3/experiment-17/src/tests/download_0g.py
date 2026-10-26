"""Download Qwen3-8B-Base and the three Qwen-Scope SAE files into the shared HF cache (0g)."""
import time
from huggingface_hub import hf_hub_download, snapshot_download
t = time.time()
for L in (15, 20, 27):
    p = hf_hub_download("Qwen/SAE-Res-Qwen3-8B-Base-W64K-L0_50", f"layer{L}.sae.pt")
    print("SAE", L, p, f"{time.time()-t:.0f}s", flush=True)
p = snapshot_download("Qwen/Qwen3-8B-Base", allow_patterns=["*.json", "*.safetensors", "*.txt", "merges.txt", "vocab.json"])
print("BASE", p, f"{time.time()-t:.0f}s", flush=True)
