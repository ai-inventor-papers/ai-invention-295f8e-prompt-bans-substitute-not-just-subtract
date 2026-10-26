#!/bin/bash
# GPU queue (one model on the GPU at a time). Each stage is resumable: it skips work whose result file exists.
cd "$(dirname "$0")/.."
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=.venv/bin/python
if [ -n "$1" ]; then while kill -0 "$1" 2>/dev/null; do sleep 10; done; fi
$PY src/run_gen.py --unit T10 --sites dec --minutes 30 --B 16 > logs/run_gen_T10_dec.out 2>&1
$PY src/run_rinit.py --unit T10 > logs/run_rinit_T10.out 2>&1
$PY src/run_dec.py --unit GRID > logs/run_dec_GRID.out 2>&1
$PY src/run_gen.py --unit GRID --sites dec --minutes 25 --B 16 > logs/run_gen_GRID_dec.out 2>&1
$PY src/run_rinit.py --unit GRID > logs/run_rinit_GRID.out 2>&1
$PY src/run_band.py --minutes 35 > logs/run_band_T10.out 2>&1
$PY src/run_gen.py --unit T10 --sites band --minutes 20 --B 16 > logs/run_gen_T10_band.out 2>&1
$PY src/run_rinit.py --unit T10 --band --band_minutes 10 > logs/run_rinit_T10_band.out 2>&1
$PY src/run_med.py --minutes 30 > logs/run_med_T10.out 2>&1
echo done > results/gpu_queue_done.flag
