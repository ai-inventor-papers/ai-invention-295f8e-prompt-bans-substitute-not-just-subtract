#!/bin/bash
# After the main GPU queue: STEP 9 extensions (forced sources T2/T10, semantic seed T2, W4) with a deadline, then
# L's teacher-forced opening ranking (Qwen3-8B, then gemma-3-4b-it). Waits for the main queue's PID to exit.
cd "$(dirname "$0")/.." || exit 1
MAIN_PID=$1
EXT_DEADLINE_MIN=${2:-25}
while kill -0 "$MAIN_PID" 2>/dev/null; do sleep 20; done
.venv/bin/python src/gpu6.py ext --deadline-min "$EXT_DEADLINE_MIN" > logs/gpu_ext.out 2>&1
echo "ext exit $?" > results/gpu_ext_exit.txt
.venv/bin/python src/lcontest.py open > logs/lgpu.out 2>&1
echo "lgpu exit $?" > results/lgpu_exit.txt
touch results/gpu_all_done.flag
