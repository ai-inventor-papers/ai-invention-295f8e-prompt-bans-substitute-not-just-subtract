#!/bin/bash
# sequential vLLM jobs: wait for the running instruct job, then the base jobs
cd "$(dirname "$0")/.."
BASE_SNAP=$HF_HUB_CACHE/models--Qwen--Qwen3-8B-Base/snapshots/49e3418fbbbca6ecbdf9608b4d22e5a407081db4
while kill -0 $1 2>/dev/null; do sleep 5; done
.venv_vllm/bin/python src/vllm_gen.py --model $BASE_SNAP --requests data/vllm_req/base1.jsonl --out data/vllm_out/base1.jsonl --max-num-seqs 128 --chunk 1200 > logs/vllm_base1.log 2>&1
echo "base1 done $(date -u)"
