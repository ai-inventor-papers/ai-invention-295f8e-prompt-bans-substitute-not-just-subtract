#!/usr/bin/env bash
# Restore what .aii/manifest.yaml marks for deletion (run from this folder; every path is relative).
set -euo pipefail
cd "$(dirname "$0")"
# .venv/ (regenerable): exact pins from pyproject.toml (uv.lock is the matching lock)
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
# __pycache__/ directories are recreated automatically on import.
# Model weights are not stored in this folder; vllm serve downloads them, or fetch ahead of time with:
if [ "${DOWNLOAD_MODEL:-0}" = "1" ]; then
  .venv/bin/huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218
fi
echo "restored .venv; see reproducibility.md for the run order"
