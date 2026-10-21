#!/bin/bash
# waits for GPU phase 1 (PID 1693) and the S5 labels, then commit #2, then GPU phase 2
cd "$(dirname "$0")/.."
while kill -0 1693 2>/dev/null; do sleep 5; done
until [ "$(wc -l < data/labels.jsonl)" -ge "$(wc -l < data/samples_raw.jsonl)" ]; do sleep 5; done
.venv/bin/python method.py commit2 > logs/commit2.out 2>&1 || { echo "commit2 failed"; exit 1; }
.venv/bin/python method.py gpu2 --minutes 45 --optional-minutes 40 > logs/gpu2.out 2>&1
