#!/usr/bin/env bash
# Recreate the removed .venv (the only deleted path besides __pycache__/); run from this folder.
set -euo pipefail
cd "$(dirname "$0")"
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python -c "import vllm, torch, transformers; print('vllm', vllm.__version__, 'torch', torch.__version__, 'transformers', transformers.__version__)"
