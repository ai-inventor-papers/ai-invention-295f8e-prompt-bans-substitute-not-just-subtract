#!/usr/bin/env bash
# Recreate what the run's cleanup removes (.venv, __pycache__) and, optionally, pre-fetch the two models.
# Run from this artifact's folder:  bash restore.sh            (environment only)
#                                   bash restore.sh --models   (also download the pinned model snapshots)
set -euo pipefail
cd "$(dirname "$0")"
command -v uv >/dev/null || { echo "install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r requirements.lock.txt      # identical pins to pyproject.toml
.venv/bin/python -c "import torch, transformers, bitsandbytes; print(torch.__version__, transformers.__version__, bitsandbytes.__version__, torch.cuda.is_available())"
if [[ "${1:-}" == "--models" ]]; then
  .venv/bin/python - <<'EOF'
from huggingface_hub import snapshot_download
snapshot_download("Qwen/Qwen3-8B", revision="b968826d9c46dd6066d109eabc6255188de91218")
snapshot_download("unsloth/Qwen3-32B-bnb-4bit", revision="7f721e74a6a8cc9ee352f7e49303a2c1705f9083")
print("models cached under HF_HOME (default ~/.cache/huggingface)")
EOF
fi
