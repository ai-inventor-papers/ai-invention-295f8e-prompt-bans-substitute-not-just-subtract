#!/bin/bash
# GPU chain 7: the descriptive C1-nat validation in a fresh process (large edit tensors held on the CPU).
cd "$(dirname "$0")"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
.venv/bin/python method.py --stages validate:C1nat > logs/run_s7.log 2>&1
echo "CHAIN7_EXIT $?" >> logs/run_s7.log
