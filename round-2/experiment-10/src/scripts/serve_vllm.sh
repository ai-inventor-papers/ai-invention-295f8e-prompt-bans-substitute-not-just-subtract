#!/usr/bin/env bash
# vLLM session (S1/S4): one long-lived server; prompts are sent as token ids; every SamplingParams field is set per request.
# --generation-config vllm stops vLLM importing generation_config.json defaults (T=0.6, top_p=0.9).
# --enforce-eager: this container has no C compiler (Triton/Inductor cannot build); only speed is affected.
set -euo pipefail
cd "$(dirname "$0")/.."
MP=${MODEL_PATH:-$(.venv/bin/python -c "import sys; sys.path.insert(0, '.'); from src.ws import model_path; print(model_path())" 2>/dev/null | tail -1)}
PORT=${PORT:-$(cat logs/vllm_port.txt)}
# TORCHDYNAMO_DISABLE=1: vLLM V1 torch.compile-s a logprob helper (batched_count_greater_than); without a C compiler
# Triton cannot build, so dynamo is disabled and the helper runs eagerly (numerically identical).
export TORCHDYNAMO_DISABLE=1
exec .venv/bin/vllm serve "$MP" --served-model-name llama31 --dtype bfloat16 --gpu-memory-utilization 0.90 \
  --max-model-len 2048 --max-num-seqs 24 --enable-prefix-caching --enforce-eager --seed 0 \
  --generation-config vllm --max-logprobs 5 --port "$PORT" --host 127.0.0.1 --disable-log-stats
