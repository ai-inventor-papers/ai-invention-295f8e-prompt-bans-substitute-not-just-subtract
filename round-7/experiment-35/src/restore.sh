#!/usr/bin/env bash
# Restore every path the manifest deletes (.venv/, cache/tf/, __pycache__/) and the model weights.
set -euo pipefail
cd "$(dirname "$0")"
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python src/download_models.py                          # Qwen/Qwen3-8B@b968826d (shared HF cache)
.venv/bin/python -m compileall -q src inputs                     # __pycache__/
.venv/bin/python src/gpu7.py predict,s4predict --units B3,A3,B6  # cache/tf/ (one CUDA GPU, >= 20 GB)
