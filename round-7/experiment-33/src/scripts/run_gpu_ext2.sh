#!/bin/bash
# Matched Sutter control for the amended map: random-init network fitted with the LME_Y objective (T2)
cd "$(dirname "$0")/.."
while [ ! -f results/stage_seed2_T2_done.json ]; do sleep 15; done
.venv/bin/python src/run_gpu7.py randinitly --tasks T2 > logs/gpu_randinit_ly.out 2>&1
touch results/gpu_ext2_done.flag
