#!/bin/bash
# Restore the regenerable bulk removed after the round (see .aii/manifest.yaml).
set -e
cd "$(dirname "$0")"
uv sync
uv venv .venv_vllm --python 3.12
uv pip install --python .venv_vllm/bin/python vllm==0.11.0 transformers==4.57.6 tokenizers==0.22.2
# model weights live in the shared Hugging Face cache (HF_HUB_CACHE), never in this folder:
.venv/bin/python -c "from huggingface_hub import snapshot_download as s; s('Qwen/Qwen3-8B', revision='b968826d9c46dd6066d109eabc6255188de91218'); s('Qwen/Qwen3-8B-Base', revision='49e3418fbbbca6ecbdf9608b4d22e5a407081db4')"
