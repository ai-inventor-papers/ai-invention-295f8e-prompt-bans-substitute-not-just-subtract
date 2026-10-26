#!/bin/bash
# GPU queue after the main T2/T10 pipeline: R + M on T2, the third task T03 (amended objective), Sutter random-init (T2)
cd "$(dirname "$0")/.."
while [ ! -f results/stage_genpilot_T2_T10_done.json ]; do sleep 20; done
.venv/bin/python src/run_gpu7.py r,m --tasks T2 > logs/gpu_rm.out 2>&1
.venv/bin/python src/run_gpu7.py profile,fitlight,fitly3,genred --tasks T03 > logs/gpu_t03.out 2>&1
.venv/bin/python src/run_gpu7.py randinit --tasks T2 > logs/gpu_randinit.out 2>&1
touch results/gpu_queue_after_done.flag
