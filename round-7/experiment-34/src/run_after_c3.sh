#!/bin/bash
# Post-commit-#3 chain: sealed Stage 0b/remeasure labelling (CPU, follow mode), F/P2 analysis + clamp selection (CPU),
# and the GPU generation stages (T03 confirmation, targeted push, top-five, same-engine re-measurement, clamp).
cd "$(dirname "$0")"
test -f predictions/commit3b_predictors.json -o -f predictions/commit3_predictors.json || { echo "commit #3 missing"; exit 1; }
.venv/bin/python src/label7.py data/samples_raw_s0b.jsonl data/labels_s0b.jsonl > logs/label7_s0b.out 2>&1 &
echo $! > logs/label7_s0b.pid
.venv/bin/python src/pushrun.py t03,targeted,top5core,top5,remeasure,clamp --deadline-min 75 > logs/pushrun.out 2>&1 &
echo $! > logs/pushrun.pid
.venv/bin/python src/analysis7.py > logs/analysis7.out 2>&1 && .venv/bin/python src/select_clamp.py > logs/select_clamp.out 2>&1
