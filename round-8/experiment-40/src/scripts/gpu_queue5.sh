#!/bin/bash
# Mediation rerun (after the clamp-row OOM fix), chained after the running post-hoc block-24 stage.
cd "$(dirname "$0")/.."
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=.venv/bin/python
if [ -n "$1" ]; then while kill -0 "$1" 2>/dev/null; do sleep 10; done; fi
$PY src/run_med.py --minutes 24 > logs/run_med_T10_rerun.out 2>&1
$PY src/label8.py --unit T10 > logs/label8_T10_final.out 2>&1
echo done > results/gpu_queue5_done.flag
