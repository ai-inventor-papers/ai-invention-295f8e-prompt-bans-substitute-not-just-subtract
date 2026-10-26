#!/usr/bin/env bash
# Restore every path the manifest deletes: the uv environment, bytecode caches and the model weights (HF cache).
set -e
cd "$(dirname "$0")"
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python -m compileall -q src inputs
.venv/bin/python src/download_models.py
