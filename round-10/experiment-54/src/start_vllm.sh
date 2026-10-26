#!/usr/bin/env bash
# Local vLLM server for Qwen3-8B-FP8 (rev 220b46e3), FP8 Marlin path (TSP9 settings; max-model-len 6144 = D1).
# Usage: bash start_vllm.sh [graphs|eager] [port]
MODE=${1:-graphs}
PORT=${2:-8754}
cd "$(dirname "$0")"
export VLLM_TEST_FORCE_FP8_MARLIN=1
export OMP_NUM_THREADS=1
export VLLM_CACHE_ROOT="$PWD/vllm_cache"
export PATH="$PWD/tools:$PATH"
export CC="$PWD/tools/cc"
SNAP="${HF_HUB_CACHE:-$HF_HOME/hub}/models--Qwen--Qwen3-8B-FP8/snapshots/220b46e3b2180893580a4454f21f22d3ebb187d3"
if [ "$MODE" = "eager" ]; then EXTRA="--enforce-eager"; else EXTRA="-O0 --compilation-config {\"cudagraph_mode\":\"FULL_DECODE_ONLY\"}"; fi
exec .venv/bin/vllm serve "$SNAP" \
  --served-model-name qwen3-8b --host 127.0.0.1 --port "$PORT" \
  --max-model-len 6144 --gpu-memory-utilization 0.93 --enable-prefix-caching \
  --max-logprobs 20 --generation-config vllm --max-num-seqs 64 $EXTRA
