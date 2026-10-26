#!/usr/bin/env bash
# Recreate everything .aii/manifest.yaml marks for deletion, and fetch the model weights.
# Run from this folder (a clone of the published repository, cd'ed into this artifact's folder).
set -euo pipefail
cd "$(dirname "$0")"
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r requirements.txt   # vllm 0.11.0, torch 2.8.0, transformers 4.57.1, zss 1.2.0 ...
# Model weights (bf16, the exact revision used) go to the Hugging Face cache (HF_HOME), not into this folder:
.venv/bin/python -c "from huggingface_hub import snapshot_download; snapshot_download('Qwen/Qwen3-8B', revision='b968826d9c46dd6066d109eabc6255188de91218')"
# __pycache__/ and .cache/ are recreated automatically on the next import / GPU job.
.venv/bin/python method.py --help > /dev/null
echo "restored .venv/ and the model snapshot"
