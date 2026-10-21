#!/bin/bash
# after C2e and 0g: exploratory extra random directions (deadline 35 min)
cd "$(dirname "$0")/.."
until [ -f logs/chain_c2e_zerog.done ]; do sleep 10; done
.venv/bin/python method.py gpu3 --minutes 35 > logs/gpu3.out 2>&1
echo done > logs/chain_gpu3.done
