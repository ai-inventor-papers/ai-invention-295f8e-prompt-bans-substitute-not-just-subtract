#!/bin/bash
# GPU chain 6: waits for chain 5 (PID given); then stability on pair set B and the descriptive C1-nat validation,
# one process per stage (chain 3b ran out of GPU memory after many stages in one process).
cd "$(dirname "$0")"
while kill -0 "$1" 2>/dev/null; do sleep 5; done
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
for st in circuitlite:C1natB f4b:C1natB validate:C1nat; do
  .venv/bin/python method.py --stages "$st" >> logs/run_s6.log 2>&1
  echo "STAGE_EXIT $st $?" >> logs/run_s6.log
done
echo "CHAIN6_EXIT" >> logs/run_s6.log
