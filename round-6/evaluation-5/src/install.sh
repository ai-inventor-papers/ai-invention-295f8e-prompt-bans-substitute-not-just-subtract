#!/usr/bin/env bash
# Recreate the Python environment (.venv is deleted after the round; it is fully regenerable).
# Pins: requirements.lock.txt (= every package of pyproject.toml), Python 3.12.
set -euo pipefail
cd "$(dirname "$0")"
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r requirements.lock.txt
.venv/bin/python -c "import numpy, scipy, pandas, matplotlib, yaml, loguru, requests; print('env ok')"
