#!/bin/bash
# After the base extension: cutoff-validation arm (R-only sharpening, no 512-token no-code stop, 20 samples/task).
cd "$(dirname "$0")"
while ! grep -q "A_EXT_EXIT" logs/chain_status.txt 2>/dev/null; do sleep 15; done
.venv/bin/python src/steer_hf.py --stage X --nocutoff --extra "sharpenR:1.0:None:2" > logs/steer_X_nocutoff.out 2>&1; echo "XNC_EXIT=$?" >> logs/chain_status.txt
