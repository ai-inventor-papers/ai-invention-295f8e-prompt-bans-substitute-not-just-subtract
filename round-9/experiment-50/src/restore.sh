#!/usr/bin/env bash
# Restore every path .aii/manifest.yaml marks `delete`: the uv environment, the model weights (HF cache) and the
# regenerable activation caches (cache/). Run from this folder.
set -e
cd "$(dirname "$0")"
# 1) environment (Python 3.12, pinned packages)
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
# 2) model weights at the pinned revisions (needs HF_TOKEN with access to the gated Gemma and Llama repos)
.venv/bin/python src/download_models.py
# 3) activation caches (cache/*.pt, ~11 GB) and B2 rows: instruct capture -> base capture (+ random sets, REV arm)
#    -> instruct patching (about 15 GPU-minutes on one 24 GB GPU)
if [ "${REGENERATE_CACHE:-0}" = "1" ]; then
  (cd src && ../.venv/bin/python cmap9.py s1 all && ../.venv/bin/python cmap9.py s2 all)
fi
