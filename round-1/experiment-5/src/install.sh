#!/bin/bash
# Recreate the exact Python environment (all 168 packages pinned in pyproject.toml) and, optionally, the two models.
#   ./install.sh            # venv only
#   ./install.sh --models   # venv + download Qwen/Qwen3-8B-Base and Qwen/Qwen3-8B at the revisions used here (~33 GB)
set -euo pipefail
cd "$(dirname "$0")"
command -v uv >/dev/null || { echo "install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python -c "import torch, vllm, transformers; print('torch', torch.__version__, 'vllm', vllm.__version__, 'transformers', transformers.__version__, 'cuda', torch.cuda.is_available())"
if [[ "${1:-}" == "--models" ]]; then
  # snapshot revisions used for the reported results (HF_HOME decides where they are stored)
  .venv/bin/hf download Qwen/Qwen3-8B-Base --revision 49e3418fbbbca6ecbdf9608b4d22e5a407081db4
  .venv/bin/hf download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218
fi
