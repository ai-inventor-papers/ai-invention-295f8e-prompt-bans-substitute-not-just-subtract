#!/bin/bash
# After GPU job C: (CPU) label the top-ups; (GPU) job B scores every new (program, prompt) pair, then job D runs the
# optional Llama-3.1-8B-Instruct (FP8) pilot.  One model on the GPU at a time.
cd "$(dirname "$0")/.."
until grep -q "job C exit" logs/chain.log 2>/dev/null; do sleep 10; done
nohup .venv/bin/python method.py label --workers 4 > logs/label_topup.out 2>&1 &
TORCH_COMPILE_DISABLE=1 .venv/bin/python method.py score --gpu-util 0.75 > logs/jobB_topup.out 2>&1
echo "job B (top-up scoring) exit $? at $(date)" >> logs/chain.log
TASKS=$(.venv/bin/python -c "import json;print(','.join(json.load(open('results/stageA_nominations.json'))['order']))")
TORCH_COMPILE_DISABLE=1 .venv/bin/python method.py gen --job D --model RedHatAI/Meta-Llama-3.1-8B-Instruct-FP8 \
  --max-num-seqs 48 --gpu-util 0.90 --tasks "$TASKS" --n-pilot 50 > logs/jobD.out 2>&1
echo "job D exit $? at $(date)" >> logs/chain.log
