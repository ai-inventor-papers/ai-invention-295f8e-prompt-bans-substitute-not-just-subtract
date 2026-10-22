#!/bin/bash
cd "$(dirname "$0")/.."
PID=$(cat logs/run.pid)
while kill -0 $PID 2>/dev/null; do sleep 5; done
.venv/bin/python src/amend_level2.py > logs/amend3.out 2>&1
.venv/bin/python method.py --stage run --plan predictions/amendment3.json --deadline-min 40 > logs/run_level2.out 2>&1
echo "level2 exit $?" >> logs/run_level2.out
