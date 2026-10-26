#!/bin/bash
# Top-up states after the factorial chain (one model on the GPU at a time).
cd "$(dirname "$0")/.."
while [ ! -f logs/run_states.done ]; do sleep 10; done
.venv/bin/python src/extract.py 32b topups > logs/extract_32b_topups.out 2>&1
.venv/bin/python src/extract.py 8b topups > logs/extract_8b_topups.out 2>&1
echo "TOPUPS DONE $(date -u +%FT%TZ)" > logs/run_states_topups.done
