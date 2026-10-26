#!/bin/bash
cd "$(dirname "$0")/.."
while pgrep -f "launch_level2.sh" > /dev/null || [ ! -f logs/run_level2.out ] || ! grep -q "level2 exit" logs/run_level2.out; do sleep 5; done
.venv/bin/python method.py --stage label > logs/label3.out 2>&1
echo "label exit $?" >> logs/label3.out
.venv/bin/python method.py --stage adjudicate --tasks T03,T2,A3 > logs/adjudicate.out 2>&1
echo "adjudicate exit $?" >> logs/adjudicate.out
