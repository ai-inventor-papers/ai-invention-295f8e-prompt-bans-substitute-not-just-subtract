#!/bin/bash
# Run GPU jobs in sequence; each job's python PID is written to logs/gpu_current.pid.
# usage: run_gpu.sh "<model> <stages> [--units ...]" ["<model> <stages> ..."] ...
cd "$(dirname "$0")/.."
for job in "$@"; do
  tag=$(echo "$job" | tr ' ,' '__' | tr -d '-')
  .venv/bin/python src/gpu8.py $job > "logs/gpu_${tag}.out" 2>&1 &
  pid=$!
  echo "$pid" > logs/gpu_current.pid
  echo "$(date -u +%FT%TZ) start $job pid $pid" >> logs/gpu_jobs.log
  wait "$pid"
  echo "$(date -u +%FT%TZ) end $job exit $?" >> logs/gpu_jobs.log
done
