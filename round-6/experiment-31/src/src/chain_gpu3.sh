#!/usr/bin/env bash
# Third GPU chain: after chain 2 (PID $1) -> the matched-pass extra DiM cells (clamps stage, extra_cells.json), then DAS.
cd "$(dirname "$0")/.."
while kill -0 "$1" 2>/dev/null; do sleep 5; done
for st in clamps das; do
  if [ -f "logs/STOP_CHAIN" ]; then echo "chain3 stopped before $st"; exit 0; fi
  echo "$(date -u +%FT%TZ) start $st"
  .venv/bin/python method.py --stage "$st" > "logs/${st}_chain3.out" 2>&1 || echo "$(date -u +%FT%TZ) FAILED $st"
  echo "$(date -u +%FT%TZ) done $st"
done
