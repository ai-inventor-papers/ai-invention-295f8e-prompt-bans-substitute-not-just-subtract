#!/bin/bash
# after.sh <pid> <job>...: wait for a PID to exit, then run GPU jobs via run_gpu.sh
cd "$(dirname "$0")/.."
while kill -0 "$1" 2>/dev/null; do sleep 5; done
shift
exec scripts/run_gpu.sh "$@"
