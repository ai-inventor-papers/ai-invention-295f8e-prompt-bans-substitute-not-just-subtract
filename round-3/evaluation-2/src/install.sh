#!/usr/bin/env bash
# Recreate the Python environment for eval.py (CPU only).
set -euo pipefail
cd "$(dirname "$0")"
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r requirements.lock.txt
