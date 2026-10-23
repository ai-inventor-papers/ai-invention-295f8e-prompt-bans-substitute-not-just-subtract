#!/usr/bin/env bash
# Restore the files removed after the round (see .aii/manifest.yaml): the Python environment, and the model weights
# used locally (cached by Hugging Face under $HF_HOME, outside this folder). Run from this artifact's folder.
set -euo pipefail
cd "$(dirname "$0")"
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r requirements.lock.txt
.venv/bin/hf download Qwen/Qwen3-8B-FP8 --revision 220b46e3b2180893580a4454f21f22d3ebb187d3
.venv/bin/hf download unsloth/Qwen3-32B-bnb-4bit --revision 7f721e74a6a8cc9ee352f7e49303a2c1705f9083
.venv/bin/hf download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218
# activation states (cache/states/, kept on the run volume, not in the repository) are rebuilt with:
#   .venv/bin/python method.py states && .venv/bin/python method.py quantcheck
