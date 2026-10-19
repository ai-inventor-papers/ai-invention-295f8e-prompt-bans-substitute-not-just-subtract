#!/bin/bash
# Waits for the GPU chain (C, R, X) to finish, then runs the base-model power extension (A1, A2 -> N=300 per task).
cd "$(dirname "$0")"
while ! grep -q "X_EXIT" logs/chain_status.txt 2>/dev/null; do sleep 15; done
.venv/bin/python src/gen_vllm.py --phase A_EXT > logs/gen_A_EXT.out 2>&1; echo "A_EXT_EXIT=$?" >> logs/chain_status.txt
