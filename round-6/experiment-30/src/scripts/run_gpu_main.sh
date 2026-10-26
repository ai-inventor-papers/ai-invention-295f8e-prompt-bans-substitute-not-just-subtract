#!/bin/bash
# Main GPU queue (one bf16 model load): twins + Stage A on six tasks, ST core grid, S3 extension + DMD,
# top-five push (+ prompt TOP5 ban), then the droppable ST extensions; a wall-clock deadline stops new batches.
cd "$(dirname "$0")/.." || exit 1
DEADLINE_MIN=${1:-180}
.venv/bin/python src/gpu6.py stageA,stcore,dmd,top5,stext --tasks T03,T10,T2,T05,T06,T1 --deadline-min "$DEADLINE_MIN"
echo "exit $?" > results/gpu_main_exit.txt
