#!/bin/bash
# GPU tail: waits for the main push chain (PID in logs/pushrun.pid), then the descriptive dose extension of the
# targeted push (fallback 8) and the exploratory long-opening LLR.
cd "$(dirname "$0")"
P=$(cat logs/pushrun.pid)
while kill -0 "$P" 2>/dev/null; do sleep 10; done
.venv/bin/python src/pushrun.py targeted_ext --deadline-min 30 > logs/pushrun_ext.out 2>&1
.venv/bin/python src/explore_llr.py > logs/explore_llr.out 2>&1
echo done > logs/gpu_tail.done
