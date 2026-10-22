#!/usr/bin/env bash
# Recreate the deleted .venv with the exact pinned versions of pyproject.toml. Run from this folder.
set -euo pipefail
cd "$(dirname "$0")"
command -v uv >/dev/null || { echo "install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python -c "import numpy, scipy, yaml, pypdf, zss, loguru, aiohttp, jsonschema; print('environment ready')"
