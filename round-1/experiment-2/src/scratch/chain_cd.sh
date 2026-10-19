#!/bin/bash
# Wait for the label_a -> succession -> phase_b chain, then run Phase C and Phase D if the commit exists.
cd "$(dirname "$0")/.."
while kill -0 "$(cat logs/chain_ab.pid)" 2>/dev/null; do sleep 15; done
if [ ! -s predictions/commit_log.jsonl ]; then echo "no commit log: not starting Phase C"; exit 1; fi
.venv/bin/python method.py --only phase_c && .venv/bin/python method.py --only phase_d
