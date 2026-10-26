#!/bin/bash
cd "$(dirname "$0")/.."
while kill -0 "$(cat logs/chain_ext.pid)" 2>/dev/null; do sleep 15; done
.venv/bin/python method.py --only phase_d_ext
