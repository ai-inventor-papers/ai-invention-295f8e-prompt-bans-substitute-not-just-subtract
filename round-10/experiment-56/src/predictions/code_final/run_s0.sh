#!/usr/bin/env bash
# S0: instruct capture, then base capture (one model per process, never two on the GPU).
set -e
cd "$(dirname "$0")/../src"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
../.venv/bin/python capture10.py qwen all > ../logs/s0_qwen.log 2>&1
../.venv/bin/python capture10.py qwen_base all > ../logs/s0_qwen_base.log 2>&1
echo S0_DONE
