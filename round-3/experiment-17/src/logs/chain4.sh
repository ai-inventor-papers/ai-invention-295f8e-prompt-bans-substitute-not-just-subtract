#!/bin/bash
# after the first gpu3 run: U1b + batch-1 S8 re-extraction (gpu3 again), C2e re-run on batch-1 states, then 0g
cd "$(dirname "$0")/.."
until [ -f results/gpu3_done.json ]; do sleep 10; done
mv results/gpu3_done.json results/gpu3_done_run1.json
.venv/bin/python method.py gpu3 --minutes 20 > logs/gpu3b.out 2>&1
[ -f results/c2e.json ] && mv results/c2e.json results/c2e_batch20_sensitivity.json
.venv/bin/python method.py c2e --minutes 40 > logs/c2e_b1.out 2>&1
.venv/bin/python method.py zerog --minutes 60 > logs/zerog.out 2>&1
echo done > logs/chain4.done
