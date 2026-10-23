#!/bin/bash
# Recreate the deleted, regenerable bulk of this folder (see README.md, "Restoring removed files").
set -euo pipefail
cd "$(dirname "$0")"
uv sync
uv run eval.py --stages all
