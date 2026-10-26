#!/bin/bash
# GPU chain 3b (restart after the OOM): resumes validation, then commit #2, generation, engine check, descriptive
# C1-nat, stability on pair set B, and the labelled head-null sensitivity.
cd "$(dirname "$0")"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
.venv/bin/python method.py --stages validate:C1forced,validate:C2a,commit2:C1forced+C2a,gen:C1forced,gen:C2a,enginecheck,valsens:C1forced,valsens:C2a,f4b:C1nat,commit1b:C1nat,validate:C1nat,circuitlite:C1natB,f4b:C1natB > logs/run_s3b.log 2>&1
echo "CHAIN3B_EXIT $?" >> logs/run_s3b.log
