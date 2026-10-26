#!/usr/bin/env bash
# Restore the files removed after the round (see README "Restoring removed files"). Run from this folder.
set -euo pipefail
cd "$(dirname "$0")"
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r pyproject.toml
# Qwen3-8B FP8 weights for the local vLLM engine (only needed to re-sample Qwen3-8B); goes to the HF cache.
.venv/bin/huggingface-cli download Qwen/Qwen3-8B-FP8 --revision 220b46e3b2180893580a4454f21f22d3ebb187d3
