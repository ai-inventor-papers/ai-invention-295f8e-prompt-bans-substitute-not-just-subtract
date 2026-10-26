#!/usr/bin/env bash
# Waits for the B2 v1 chain, then B3 (instruct Qwen) and B1 (Gemma it/pt, Llama instruct/base), one model at a time.
cd "$(dirname "$0")/src"
QPID=$(cat ../logs/run_qwen.pid)
while kill -0 $QPID 2>/dev/null; do sleep 5; done
../.venv/bin/python b3_9.py gpu || echo "B3 FAILED"
for m in gemma gemma_pt llama llama_base; do ../.venv/bin/python b1_9.py gpu $m || echo "B1 $m FAILED"; done
echo QUEUE2_DONE
