#!/bin/bash
# Final GPU queue (after the GRID rerun crash on a null scan value): finish the running T10 band generation, then
# the GRID decision site, generation and random-init control (K2 core), then the band random-init control,
# mediation, the T10 p_c2 completion and the post-hoc block-24 sensitivity.
cd "$(dirname "$0")/.."
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=.venv/bin/python
if [ -n "$1" ]; then while kill -0 "$1" 2>/dev/null; do sleep 10; done; fi
$PY src/run_dec.py --unit GRID > logs/run_dec_GRID3.out 2>&1
$PY src/run_gen.py --unit GRID --sites dec --minutes 16 --B 16 > logs/run_gen_GRID_dec.out 2>&1
$PY src/run_rinit.py --unit GRID > logs/run_rinit_GRID.out 2>&1
$PY src/run_rinit.py --unit T10 --band --band_minutes 8 > logs/run_rinit_T10_band.out 2>&1
$PY src/run_med.py --minutes 26 > logs/run_med_T10.out 2>&1
$PY src/run_post.py --unit T10 > logs/run_post_T10.out 2>&1
$PY src/run_dec.py --unit T10 --force_L 24 > logs/run_dec_T10_L24.out 2>&1
echo done > results/gpu_queue_done.flag
