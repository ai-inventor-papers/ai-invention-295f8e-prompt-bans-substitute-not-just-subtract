#!/bin/bash
# Extensions after the random-init control: behaviour of M's prompts (T2) and a second DAS init seed (T2)
cd "$(dirname "$0")/.."
while [ ! -f results/stage_randinit_T2_done.json ]; do sleep 15; done
.venv/bin/python src/run_gpu7.py mgen,seed2 --tasks T2 > logs/gpu_ext.out 2>&1
touch results/gpu_all_done.flag
