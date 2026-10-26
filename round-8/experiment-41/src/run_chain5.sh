#!/bin/bash
# GPU chain 5: waits for chain 3b, then the labelled post-hoc dose sensitivity for both contrasts.
cd "$(dirname "$0")"
while kill -0 "$1" 2>/dev/null; do sleep 5; done
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
.venv/bin/python method.py --stages dose:C1forced,dose:C2a > logs/run_s5.log 2>&1
echo "CHAIN5_EXIT $?" >> logs/run_s5.log
