#!/bin/bash
# Restore every path that .aii/manifest.yaml marks for deletion (run from this folder).
set -e
cd "$(dirname "$0")"
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python scripts/download_models.py                 # model weights into the HF cache (needs HF_TOKEN for Gemma)
.venv/bin/python src/novelty8.py index                      # cache/known_index.pkl (needs ../art_j3Rm_lr2nzR6 or ART_J3RM_DIR)
.venv/bin/python -m compileall -q src inputs build          # **/__pycache__/
