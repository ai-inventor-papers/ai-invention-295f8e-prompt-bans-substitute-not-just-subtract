#!/usr/bin/env bash
# Recreate everything .aii/manifest.yaml marks for deletion, and fetch the model weights.
set -euo pipefail
cd "$(dirname "$0")"
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r requirements.txt
# bytecode caches are recreated on import; compile them eagerly:
.venv/bin/python -m compileall -q src inputs/bench
# model weights (kept in the Hugging Face cache, not in this folder):
.venv/bin/hf download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218
