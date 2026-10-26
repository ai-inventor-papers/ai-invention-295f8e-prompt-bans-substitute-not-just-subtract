#!/bin/bash
# Optional post-hoc: random-init control at the T10 block-24 sensitivity site, after the mediation rerun.
cd "$(dirname "$0")/.."
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
while [ ! -f results/gpu_queue5_done.flag ]; do sleep 10; done
.venv/bin/python src/run_rinit.py --unit T10 --force_L 24 > logs/run_rinit_T10_L24.out 2>&1
echo done > results/gpu_queue6_done.flag
