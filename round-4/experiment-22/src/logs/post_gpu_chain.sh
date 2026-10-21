#!/usr/bin/env bash
# GPU work after phase 2: phase 3 (opening ladder + C2c vectors), (an exploratory alpha-2 top-up extension was planned here and skipped for time).
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
.venv/bin/python src/gpu_phase3.py > logs/gpu_phase3.out 2>&1
: # exploratory alpha-2 top-up extension (src/gpu_phase2b.py) skipped for time
echo POST_GPU_DONE >> logs/gpu_phase3.out
