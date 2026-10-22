#!/bin/bash
# waits for run_gpu_tail.sh, then the exploratory forced-token test, then labels its rows (frozen labeller)
cd "$(dirname "$0")"
while [ ! -f logs/gpu_tail.done ]; do sleep 10; done
.venv/bin/python src/force_token.py > logs/force_token.out 2>&1
.venv/bin/python src/label7.py --once data/samples_raw_force.jsonl data/labels_force.jsonl > logs/label7_force.out 2>&1
echo done > logs/gpu_tail2.done
