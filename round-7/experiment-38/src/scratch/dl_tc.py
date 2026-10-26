"""Download the circuit-tracer transcoder set (weights + config only, no feature-visualisation .bin files)."""
import time, sys
from huggingface_hub import snapshot_download
t0 = time.time()
p = snapshot_download("mwhanna/gemma-scope-2-4b-it", revision="61cb16ec74f348f4a8643fe3a0157be9dc8a851d",
                      allow_patterns=["transcoder_all/width_16k_l0_big_affine/*.safetensors",
                                      "transcoder_all/width_16k_l0_big_affine/config.yaml",
                                      "transcoder_all/width_16k_l0_big_affine/config_orig.yaml"], max_workers=8)
print("DONE", p, f"{time.time()-t0:.0f}s", flush=True)
