#!/bin/bash
# after GPU phase 2 (gpu2_done.json), run the C2e decoders and then 0g on the GPU
cd "$(dirname "$0")/.."
until [ -f results/gpu2_done.json ]; do sleep 10; done
.venv/bin/python method.py c2e --minutes 40 > logs/c2e.out 2>&1
.venv/bin/python method.py zerog --minutes 60 > logs/zerog.out 2>&1
echo done > logs/chain_c2e_zerog.done
