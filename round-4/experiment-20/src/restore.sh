#!/usr/bin/env bash
# Restore everything the manifest marks `delete` (run from this folder).
set -euo pipefail
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
# Model weights (read through HF_HUB_CACHE / HF_HOME; ~16 GB):
huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218
# Dataset dependency art_j3Rm_lr2nzR6 (only the novelty-audit index and dependency usage read it): the repository
# publishes it as the sibling folder ../art_j3Rm_lr2nzR6 (the default); otherwise set ART_J3RM_DIR to a folder holding
# its full_data_out.json (restore that file with the artifact's own restore.sh).
