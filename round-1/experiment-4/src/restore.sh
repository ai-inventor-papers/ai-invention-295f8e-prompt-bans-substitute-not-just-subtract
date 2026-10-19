#!/usr/bin/env bash
# Recreate the deleted environment and fetch the model weights into the HF cache.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/hf download Qwen/Qwen3-8B
