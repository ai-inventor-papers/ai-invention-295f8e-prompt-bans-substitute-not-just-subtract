#!/bin/bash
# GPU chain 3: waits for chain 2 (PID given), then F4b re-ranking -> commit #1 -> validation -> commit #2 ->
# generation -> engine check -> descriptive C1-nat (F4b, commit #1b, validation) -> stability on pair set B.
cd "$(dirname "$0")"
while kill -0 "$1" 2>/dev/null; do sleep 5; done
.venv/bin/python method.py --stages f4b:C1forced,f4b:C2a,commit1:C1forced+C2a,validate:C1forced,validate:C2a,commit2:C1forced+C2a,gen:C1forced,gen:C2a,enginecheck,f4b:C1nat,commit1b:C1nat,validate:C1nat,circuitlite:C1natB,f4b:C1natB > logs/run_s3.log 2>&1
echo "CHAIN3_EXIT $?" >> logs/run_s3.log
