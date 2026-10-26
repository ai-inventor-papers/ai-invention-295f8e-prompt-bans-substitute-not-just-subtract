#!/usr/bin/env bash
# Restore everything that .aii/manifest.yaml marks `delete`, plus the model weights (kept in the shared HF cache, not here).
set -euo pipefail
cd "$(dirname "$0")"
# 1. Python environment (pinned versions in pyproject.toml; uv only)
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
# 2. model weights at the pinned revisions (into $HF_HUB_CACHE; Gemma needs an HF token with Gemma access)
bash scripts/download_models.sh
# 3. bytecode caches are rebuilt on import; to prebuild:
.venv/bin/python -m compileall -q src inputs/iter9/src || true
# 4. (optional) recompute cache/ (GPU, ~5 min on one 24 GB GPU) -- results/ already holds every number
# .venv/bin/python method.py --stages s0,w3
