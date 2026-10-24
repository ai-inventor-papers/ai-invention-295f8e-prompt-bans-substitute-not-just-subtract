#!/bin/bash
# vLLM launcher (flags restated from iteration-9 TSP9/start_vllm.sh in the NOV-B1 plan). Logs to logs/vllm.log.
# Usage: bash start_vllm.sh [extra vllm args...]   -> prints the server PID
W="$(cd "$(dirname "$0")" && pwd)"
export VLLM_TEST_FORCE_FP8_MARLIN=1 OMP_NUM_THREADS=1
export VLLM_CACHE_ROOT="$W/vllm_cache" TRITON_CACHE_DIR="$W/vllm_cache/triton" XDG_CACHE_HOME="$W/vllm_cache/xdg"
export CUDA_CACHE_PATH="$W/vllm_cache/nv" TORCHINDUCTOR_CACHE_DIR="$W/vllm_cache/inductor" FLASHINFER_WORKSPACE_BASE="$W/vllm_cache/flashinfer"
export CC="$W/tools/cc" PATH="$W/tools:$PATH" VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1
PORT="${VLLM_PORT:-8051}"
nohup "$W/.venv/bin/vllm" serve Qwen/Qwen3-8B-FP8 --revision 220b46e3b2180893580a4454f21f22d3ebb187d3 \
  --served-model-name qwen3-8b --host 127.0.0.1 --port "$PORT" --max-model-len 4096 \
  --gpu-memory-utilization "${VLLM_GPU_UTIL:-0.93}" --enable-prefix-caching --max-logprobs 20 --generation-config vllm \
  --max-num-seqs "${VLLM_MAX_SEQS:-64}" -O0 --compilation-config '{"cudagraph_mode": "FULL_DECODE_ONLY"}' \
  "$@" > "$W/logs/vllm.log" 2>&1 &
echo $!
