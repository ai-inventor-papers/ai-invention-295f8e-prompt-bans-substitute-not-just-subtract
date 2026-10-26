#!/bin/bash
# Second GPU queue: waits for scripts/gpu_queue.sh to finish, then runs the post-hoc p_c2 completion for T10 and the
# post-hoc block-24 sensitivity of the T10 decision site (descriptive; never substituted for the rule-chosen L*).
cd "$(dirname "$0")/.."
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=.venv/bin/python
while [ ! -f results/gpu_queue_done.flag ]; do sleep 15; done
$PY src/run_post.py --unit T10 > logs/run_post_T10.out 2>&1
$PY src/run_dec.py --unit T10 --force_L 24 > logs/run_dec_T10_L24.out 2>&1
echo done > results/gpu_queue2_done.flag
