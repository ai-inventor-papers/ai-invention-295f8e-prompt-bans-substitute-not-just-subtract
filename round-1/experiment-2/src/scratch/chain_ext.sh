#!/bin/bash
# After the C->D chain finishes, run the Phase C extension.
cd "$(dirname "$0")/.."
while kill -0 "$(cat logs/chain_cd.pid)" 2>/dev/null; do sleep 15; done
.venv/bin/python method.py --only phase_c_ext
