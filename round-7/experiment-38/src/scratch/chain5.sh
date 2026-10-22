#!/bin/bash
cd .
while kill -0 $1 2>/dev/null; do sleep 5; done
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
echo "=== g2pairs start $(date -u +%H:%M:%S)"; .venv/bin/python method.py --stage g2pairs > logs/run_g2pairs.out 2>&1; echo "=== g2pairs rc=$? $(date -u +%H:%M:%S)"
.venv/bin/python src/prep_ct.py scratch/ct_input.json > logs/prep_ct.out 2>&1
echo "=== ct start $(date -u +%H:%M:%S)"; timeout ${2:-1500} .venv_ct/bin/python src/ct_graph.py scratch/ct_input.json results/g1t_graphs.json > logs/run_ct.out 2>&1; echo "=== ct rc=$? $(date -u +%H:%M:%S)"
