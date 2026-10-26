#!/bin/bash
# after base1b ends (PID-based), run the committed power extension (instr3)
cd "$(dirname "$0")/../src"
while [ ! -f ../logs/gpu_base1b.pid ]; do sleep 10; done
BPID=$(cat ../logs/gpu_base1b.pid)
while kill -0 "$BPID" 2>/dev/null; do sleep 10; done
../.venv/bin/python gpu5.py instr3 > ../logs/gpu_instr3.out 2>&1 &
echo $! > ../logs/gpu_instr3.pid
wait $!
echo "instr3 exit $?" >> ../logs/gpu_instr3.out
