#!/bin/bash
# Restore everything the manifest marks `delete` (and the model weights, which live in the shared Hugging Face cache).
set -euo pipefail
cd "$(dirname "$0")"
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python -m compileall -q src audit inputs/exp11/bench inputs/exp8/suite || true
# model weights (gated: accept the Gemma licence on huggingface.co and export HF_TOKEN first)
.venv/bin/python src/download_models.py
