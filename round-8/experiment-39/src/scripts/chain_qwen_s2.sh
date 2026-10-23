#!/bin/bash
# wait for Qwen stage 0 (PID given) and start Qwen stage 2 (token maps)
cd "$(dirname "$0")/.."
while kill -0 "$1" 2>/dev/null; do sleep 5; done
.venv/bin/python src/gpu8.py qwen s2 --units T10,B3,T1,A3,B6 > logs/gpu_qwen_s2.out 2>&1
echo "exit $?" >> logs/gpu_qwen_s2.out
