#!/usr/bin/env bash
# Runs the GPU stages back to back after the fork stage (PID passed as $1) has exited; stops at the first failure.
cd "$(dirname "$0")/.."
FORK_PID="$1"
while kill -0 "$FORK_PID" 2>/dev/null; do sleep 10; done
for st in tfgate variants select clamps; do
  if [ -f "logs/STOP_CHAIN" ]; then echo "chain stopped before $st"; exit 0; fi
  echo "$(date -u +%FT%TZ) start $st"
  .venv/bin/python method.py --stage "$st" ${CHAIN_ARGS} > "logs/${st}.out" 2>&1 || { echo "$(date -u +%FT%TZ) FAILED $st"; exit 1; }
  echo "$(date -u +%FT%TZ) done $st"
done
