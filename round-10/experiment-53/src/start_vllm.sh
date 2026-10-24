#!/usr/bin/env bash
# Start the local vLLM server (Qwen3-8B-FP8 at a pinned revision; FP8-Marlin weight path; thinking off is set
# per request by the chat template). Adapted from TSP9's launcher (inputs/tsp9/start_vllm.sh).
# Usage: bash start_vllm.sh [compile|eager|o0]
MODE=${1:-compile}
cd "$(dirname "$0")"
export VLLM_TEST_FORCE_FP8_MARLIN=1
export OMP_NUM_THREADS=1
export PATH="$PWD/tools:$PATH"
export CC="$PWD/tools/cc"
export VLLM_CACHE_ROOT="$PWD/.cache/vllm"
export TRITON_CACHE_DIR="$PWD/.cache/triton"
export TORCHINDUCTOR_CACHE_DIR="$PWD/.cache/inductor"
export XDG_CACHE_HOME="$PWD/.cache"
export VLLM_NO_USAGE_STATS=1
export DO_NOT_TRACK=1
case "$MODE" in
  eager) EXTRA="--enforce-eager" ;;
  o0) EXTRA="-O0 --compilation-config {\"cudagraph_mode\":\"FULL_DECODE_ONLY\"}" ;;
  *) EXTRA="" ;;
esac
exec .venv/bin/vllm serve Qwen/Qwen3-8B-FP8 --revision 220b46e3b2180893580a4454f21f22d3ebb187d3 \
  --served-model-name qwen3-8b --host 127.0.0.1 --port 8000 \
  --max-model-len 4096 --gpu-memory-utilization 0.93 --enable-prefix-caching \
  --max-logprobs 20 --generation-config vllm --max-num-seqs 64 $EXTRA
