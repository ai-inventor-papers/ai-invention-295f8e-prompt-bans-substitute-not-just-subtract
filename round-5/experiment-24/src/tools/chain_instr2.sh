#!/bin/bash
# waits for the base1 GPU stage to finish (PID-based), then launches instr2 (one 8B model on the GPU at a time)
cd "$(dirname "$0")/../src"
BPID=$(cat ../logs/gpu_base1.pid)
while kill -0 "$BPID" 2>/dev/null; do sleep 10; done
../.venv/bin/python gpu5.py instr2 --wait-min 40 > ../logs/gpu_instr2.out 2>&1 &
echo $! > ../logs/gpu_instr2.pid
wait $!
echo "instr2 exit $?" >> ../logs/gpu_instr2.out
