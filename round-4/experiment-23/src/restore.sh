#!/usr/bin/env bash
# Recreate everything this artifact does not ship: the Python environment and the model weights.
# Run from this artifact's folder. Needs: uv, an NVIDIA driver (CUDA 12.8 wheels), HF_TOKEN with access to Gemma.
set -euo pipefail
cd "$(dirname "$0")"
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/huggingface-cli download google/gemma-3-4b-it --revision 093f9f388b31de276ce2de164bdc2081324b9767
.venv/bin/huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218
echo "restored: .venv and model weights (Hugging Face cache)"
