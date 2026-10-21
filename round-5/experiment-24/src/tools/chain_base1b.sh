#!/bin/bash
# after instr2 ends (PID-based), resume base1 (Stage 6 rows still missing: T2, T1 after the u_stream-length fix)
cd "$(dirname "$0")/../src"
IPID=$(cat ../logs/gpu_instr2.pid)
while kill -0 "$IPID" 2>/dev/null; do sleep 10; done
../.venv/bin/python gpu5.py base1 --wait-min 5 > ../logs/gpu_base1b.out 2>&1 &
echo $! > ../logs/gpu_base1b.pid
wait $!
echo "base1b exit $?" >> ../logs/gpu_base1b.out
