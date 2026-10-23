#!/usr/bin/env bash
# Runs the post-pool stages in order (each stage must succeed before the next starts).
# Usage: ./run_chain.sh [first_stage_index]   (0 = 32B states, 1 = 8B states, 2 = blocks, 3 = analyse, 4 = figures,
#                                              5 = outputs, 6 = audits)
set -euo pipefail
cd "$(dirname "$0")"
PY=.venv/bin/python
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
start=${1:-0}
steps=("$PY method.py states 32b mcode"
       "$PY method.py states 8b mcode"
       "$PY method.py blocks"
       "$PY method.py analyse"
       "$PY method.py figures"
       "$PY method.py outputs"
       "$PY audit/rederive.py")
for i in "${!steps[@]}"; do
  if [ "$i" -lt "$start" ]; then continue; fi
  echo "=== $(date -u +%H:%M:%S) step $i: ${steps[$i]}"
  if [ "$i" -ge 4 ]; then ${steps[$i]} > "logs/chain_step_$i.out" 2>&1 || echo "step $i FAILED (continuing)"; else ${steps[$i]} > "logs/chain_step_$i.out" 2>&1 || { echo "step $i FAILED"; exit 1; }; fi
done
echo "=== $(date -u +%H:%M:%S) chain done"
