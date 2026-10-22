#!/bin/bash
# Restore what the storage manifest deletes after the round: the virtual environment and the model weights.
# Run from this folder: bash restore.sh
set -euo pipefail
cd "$(dirname "$0")"
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python src/download_model7.py   # Qwen/Qwen3-8B @ b968826d9c46dd6066d109eabc6255188de91218 into the HF cache
