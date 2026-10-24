#!/bin/bash
# Factorial states: Qwen3-8B (factorial + reliability context), RANDNET, then Qwen3-32B NF4. One model on the GPU at a time.
cd "$(dirname "$0")/.."
.venv/bin/python src/extract.py 8b factorial factorial_ctx2 > logs/extract_8b_factorial.out 2>&1
.venv/bin/python src/extract.py randnet factorial > logs/extract_randnet.out 2>&1
.venv/bin/python src/extract.py 32b factorial > logs/extract_32b_factorial.out 2>&1
echo "ALL DONE $(date -u +%FT%TZ)" > logs/run_states.done
