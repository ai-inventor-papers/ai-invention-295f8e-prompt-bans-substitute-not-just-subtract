#!/usr/bin/env bash
# Recreate what a fresh clone of the repository lacks:
#   .venv/           deleted after the round by .aii/manifest.yaml; the exact versions are pinned in pyproject.toml
#   temp/datasets/   excluded from the published repository; the 15 raw sources at the revisions/commits in data_sources.json
# Then rebuild full_data_out.json with `uv run data.py` (see reproducibility.md).
# Needs: uv (tested with 0.6.14), git, network access to huggingface.co and github.com.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
  uv venv .venv --python=3.12
  uv pip install --python=.venv/bin/python -r pyproject.toml
fi

.venv/bin/python scripts/download_all.py
echo "restored .venv/ and temp/datasets/; next: uv run data.py"
