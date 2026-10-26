#!/usr/bin/env bash
# Environment for GPU stages: keeps every cache the engines write inside this workspace.
WS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export HF_HUB_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export VLLM_CACHE_ROOT="$WS/.engine_cache/vllm"
export TRITON_CACHE_DIR="$WS/.engine_cache/triton"
export TORCHINDUCTOR_CACHE_DIR="$WS/.engine_cache/inductor"
export XDG_CACHE_HOME="$WS/.engine_cache/xdg"
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export PYTHONUNBUFFERED=1
