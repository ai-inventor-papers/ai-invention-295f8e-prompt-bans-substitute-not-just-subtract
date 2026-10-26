#!/usr/bin/env bash
# Recreate the environment (and optionally the model weights) for this artifact.
set -euo pipefail
cd "$(dirname "$0")"
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
if [ "${DOWNLOAD_MODEL:-0}" = "1" ]; then
  .venv/bin/python -c "from huggingface_hub import snapshot_download as s; print(s('meta-llama/Llama-3.1-8B-Instruct', revision='0e9e39f249a16976918f6564b8830bc894c89659', allow_patterns=['*.json','*.safetensors','tokenizer*']))"
fi
