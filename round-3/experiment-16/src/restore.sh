#!/usr/bin/env bash
# Rebuild everything the manifest marks `delete`. The model weights live in the Hugging Face cache, not here.
set -euo pipefail
cd "$(dirname "$0")"
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r requirements.txt
# model (bf16, ~16.4 GB) at the pinned revision, into $HF_HOME / $HF_HUB_CACHE
.venv/bin/huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218
