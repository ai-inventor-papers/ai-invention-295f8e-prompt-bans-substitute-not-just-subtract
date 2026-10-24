#!/usr/bin/env bash
# Start the local vLLM server (Qwen3-8B-FP8, Marlin FP8 path, no torch.compile because no C compiler).
# Usage: bash start_vllm.sh [eager|graphs]
MODE=${1:-graphs}
cd "$(dirname "$0")"
export VLLM_TEST_FORCE_FP8_MARLIN=1
export OMP_NUM_THREADS=1
if [ "$MODE" = "eager" ]; then EXTRA="--enforce-eager"; else EXTRA="-O0 --compilation-config {\"cudagraph_mode\":\"FULL_DECODE_ONLY\"}"; fi
exec .venv/bin/vllm serve Qwen/Qwen3-8B-FP8 --revision 220b46e3b2180893580a4454f21f22d3ebb187d3 \
  --served-model-name qwen3-8b --host 127.0.0.1 --port 8000 \
  --max-model-len 4096 --gpu-memory-utilization 0.80 --enable-prefix-caching \
  --max-logprobs 20 --generation-config vllm --max-num-seqs 64 $EXTRA
