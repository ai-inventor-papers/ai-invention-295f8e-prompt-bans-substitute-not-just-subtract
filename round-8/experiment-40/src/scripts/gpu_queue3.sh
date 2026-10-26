#!/bin/bash
# Reordered GPU queue (after the GRID label-control crash): finish the running band stage, then the GRID decision
# site (K2 core), then band generation, random-init band, mediation, the T10 p_c2 completion and the post-hoc
# block-24 sensitivity. Every stage skips work whose result file already exists.
cd "$(dirname "$0")/.."
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=.venv/bin/python
if [ -n "$1" ]; then while kill -0 "$1" 2>/dev/null; do sleep 10; done; fi
$PY src/run_dec.py --unit GRID > logs/run_dec_GRID2.out 2>&1
$PY src/run_gen.py --unit GRID --sites dec --minutes 20 --B 16 > logs/run_gen_GRID_dec.out 2>&1
$PY src/run_rinit.py --unit GRID > logs/run_rinit_GRID.out 2>&1
$PY src/run_gen.py --unit T10 --sites band --minutes 18 --B 16 > logs/run_gen_T10_band.out 2>&1
$PY src/run_rinit.py --unit T10 --band --band_minutes 8 > logs/run_rinit_T10_band.out 2>&1
$PY src/run_med.py --minutes 28 > logs/run_med_T10.out 2>&1
$PY src/run_post.py --unit T10 > logs/run_post_T10.out 2>&1
$PY src/run_dec.py --unit T10 --force_L 24 > logs/run_dec_T10_L24.out 2>&1
echo done > results/gpu_queue_done.flag
