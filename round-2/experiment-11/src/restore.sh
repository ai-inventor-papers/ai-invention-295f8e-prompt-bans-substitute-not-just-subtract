#!/bin/bash
# Recreate the deleted .venv (all 160 packages pinned in requirements.txt / pyproject.toml) and fetch the model weights.
set -euo pipefail
cd "$(dirname "$0")"
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r requirements.txt
# model weights go to the Hugging Face cache (HF_HOME), not into this folder
uvx --from huggingface_hub hf download Qwen/Qwen3-8B-FP8
uvx --from huggingface_hub hf download RedHatAI/Meta-Llama-3.1-8B-Instruct-FP8   # optional Llama pilot only
