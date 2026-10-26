#!/bin/bash
# GPU chain: each stage runs after the previous one; dependent stages are skipped when their input stage failed.
cd .
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
declare -A RC
run() { echo "=== $1 start $(date -u +%H:%M:%S)"; .venv/bin/python method.py --stage $1 > logs/run_$1.out 2>&1; RC[$1]=$?; echo "=== $1 rc=${RC[$1]} $(date -u +%H:%M:%S)"; }
for st in "$@"; do
  case $st in
    g1v|g1gen) [ "${RC[g1p]:-0}" != "0" ] && { echo "skip $st (g1p failed)"; continue; } ;;
    g2r|g2d) [ "${RC[g2]:-0}" != "0" ] && { echo "skip $st (g2 failed)"; continue; } ;;
  esac
  run $st
done
