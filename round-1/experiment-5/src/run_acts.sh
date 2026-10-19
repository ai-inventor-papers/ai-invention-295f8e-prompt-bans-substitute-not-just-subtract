#!/bin/bash
# Waits for Phase B (vLLM) to exit, then extracts base and instruct activations (one HF process per model).
cd "$(dirname "$0")"
while ! grep -q "B_EXIT" logs/gen_AB_status.txt 2>/dev/null; do sleep 10; done
.venv/bin/python src/acts_hf.py --model base > logs/acts_base.out 2>&1; echo "ACTS_BASE_EXIT=$?" >> logs/acts_status.txt
.venv/bin/python src/acts_hf.py --model instruct > logs/acts_instruct.out 2>&1; echo "ACTS_INSTRUCT_EXIT=$?" >> logs/acts_status.txt
