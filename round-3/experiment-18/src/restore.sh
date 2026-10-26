#!/usr/bin/env bash
# Recreate the deleted virtual environment and fetch the model weights into the Hugging Face cache.
set -euo pipefail
cd "$(dirname "$0")"
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218
.venv/bin/huggingface-cli download Qwen/Qwen3-8B-FP8
