#!/bin/bash
# Wait for GPU job B (scoring) to exit, then run GPU job C (forced top-ups). One model on the GPU at a time.
cd "$(dirname "$0")/.."
PID=$(cat logs/jobB.pid)
while kill -0 "$PID" 2>/dev/null; do sleep 10; done
echo "job B ended at $(date)" >> logs/chain.log
TORCH_COMPILE_DISABLE=1 .venv/bin/python method.py gen --job C --max-num-seqs 48 --gpu-util 0.90 > logs/jobC.out 2>&1
echo "job C exit $? at $(date)" >> logs/chain.log
