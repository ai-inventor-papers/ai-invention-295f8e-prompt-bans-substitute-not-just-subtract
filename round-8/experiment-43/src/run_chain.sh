#!/usr/bin/env bash
# GPU chain after the Gemma family: Llama (held-out) -> Qwen -> base sub-arm (instruct side, then base model).
cd "$(dirname "$0")/src"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
while [ -n "$WAIT_PID" ] && kill -0 "$WAIT_PID" 2>/dev/null; do sleep 10; done
../.venv/bin/python gpu8.py llama locate,commit1,predict,commit2,sweep > ../logs/run_llama.out 2>&1
echo "llama exit $?" >> ../logs/chain.log
../.venv/bin/python gpu8.py qwen tests,fit,locate,commit1,predict,commit2,sweep > ../logs/run_qwen.out 2>&1
echo "qwen exit $?" >> ../logs/chain.log
if [ "$(date -u +%H%M)" \< "0625" ]; then
../.venv/bin/python base_arm.py gpu qwen > ../logs/base_qwen.out 2>&1
echo "base_instr exit $?" >> ../logs/chain.log
../.venv/bin/python base_arm.py gpu qwen_base > ../logs/base_qwen_base.out 2>&1
echo "base_base exit $?" >> ../logs/chain.log
else echo "base sub-arm skipped (time box)" >> ../logs/chain.log; fi
