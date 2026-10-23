#!/bin/bash
# GPU chain 4: waits for chain 3 (PID given), then the labelled post-hoc head-null sensitivity.
cd "$(dirname "$0")"
while kill -0 "$1" 2>/dev/null; do sleep 5; done
.venv/bin/python method.py --stages valsens:C1forced,valsens:C2a > logs/run_s4.log 2>&1
echo "CHAIN4_EXIT $?" >> logs/run_s4.log
