#!/usr/bin/env bash
# Second GPU chain: waits for the first chain (PID $1), then runs the optional S9 DAS and the S10 fallback.
cd "$(dirname "$0")/.."
while kill -0 "$1" 2>/dev/null; do sleep 10; done
grep -q "done clamps" logs/chain_gpu.out || { echo "first chain did not finish clamps"; exit 1; }
for st in das attrib; do
  if [ -f "logs/STOP_CHAIN" ]; then echo "chain2 stopped before $st"; exit 0; fi
  echo "$(date -u +%FT%TZ) start $st"
  .venv/bin/python method.py --stage "$st" > "logs/${st}.out" 2>&1 || echo "$(date -u +%FT%TZ) FAILED $st"
  echo "$(date -u +%FT%TZ) done $st"
done
