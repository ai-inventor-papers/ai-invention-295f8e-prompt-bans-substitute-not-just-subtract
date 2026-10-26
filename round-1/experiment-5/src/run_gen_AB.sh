#!/bin/bash
# Phase A (Qwen3-8B-Base) then Phase B (Qwen3-8B); each in its own process so VRAM is freed in between.
cd "$(dirname "$0")"
export MAX_NUM_SEQS=${MAX_NUM_SEQS:-48}
export VLLM_LOGGING_LEVEL=WARNING
.venv/bin/python src/gen_vllm.py --phase A > logs/gen_A.out 2>&1; echo "A_EXIT=$?" >> logs/gen_AB_status.txt
.venv/bin/python src/gen_vllm.py --phase B > logs/gen_B.out 2>&1; echo "B_EXIT=$?" >> logs/gen_AB_status.txt
