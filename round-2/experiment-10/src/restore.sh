#!/usr/bin/env bash
# Restore what .aii/manifest.yaml marks for deletion (run from this folder; every path is relative).
set -euo pipefail
cd "$(dirname "$0")"
# .venv/ (regenerable): exact pins from pyproject.toml (canon pins: vLLM 0.11.0, torch 2.8.0, transformers 4.57.6)
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
# __pycache__/ directories (src/, canon/ and its subfolders): recreated on import, or explicitly:
.venv/bin/python -m compileall -q src canon
# Model weights are NOT stored in this folder (they were read from the run's shared HF cache). Fetch them with:
if [ "${DOWNLOAD_MODEL:-0}" = "1" ]; then
  .venv/bin/huggingface-cli download meta-llama/Llama-3.1-8B-Instruct --revision 0e9e39f249a16976918f6564b8830bc894c89659 \
    --include "*.json" "*.safetensors" "tokenizer*"
fi
echo "restored .venv; see reproducibility.md for the run order"
