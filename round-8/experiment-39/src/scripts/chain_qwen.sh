#!/bin/bash
# Qwen GPU chain: stage 0 (resumes from data/samples.jsonl), then stage 2 (token maps)
cd "$(dirname "$0")/.."
.venv/bin/python src/gpu8.py qwen s0 > logs/gpu_qwen_s0b.out 2>&1
echo "s0 exit $?" >> logs/gpu_qwen_s0b.out
.venv/bin/python src/gpu8.py qwen s2 --units T10,B3,T1,A3,B6 > logs/gpu_qwen_s2.out 2>&1
echo "s2 exit $?" >> logs/gpu_qwen_s2.out
