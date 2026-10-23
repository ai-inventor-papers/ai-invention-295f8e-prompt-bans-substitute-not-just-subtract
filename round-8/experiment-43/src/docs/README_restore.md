## Restoring removed files

The manifest (`.aii/manifest.yaml`) deletes only regenerable bulk after the round. Everything else (data, results,
commits, figures, inputs) is kept on the run's volume at the paths above and is under 100 MB per file, so it is also
published with the repository.

| removed path | restore with |
|---|---|
| `.venv/` (about 10 GB: torch, transformers and CUDA wheels) | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` |
| `**/__pycache__/` (bytecode caches under `src/` and `inputs/`) | `.venv/bin/python -m compileall -q src inputs` |
| model weights (shared HF cache, never in this folder) | `.venv/bin/python src/download_models.py` (google/gemma-3-4b-it@093f9f38, meta-llama/Llama-3.1-8B-Instruct@0e9e39f2, Qwen/Qwen3-8B@b968826d, Qwen/Qwen3-8B-Base@49e3418f; full hashes in `src/download_models.py`) |

`restore.sh` runs the first two commands and the model download.
