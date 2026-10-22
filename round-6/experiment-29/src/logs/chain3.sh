#!/bin/bash
# After the first engine-b continuation exits, run it again with the fixed targeting until 10:07 UTC.
cd "$(dirname "$0")/.."
CP=$(cat logs/chain2.pid)
while kill -0 $CP 2>/dev/null; do sleep 5; done
echo "chain2 ended at $(date -u +%H:%M:%S)"
END=$(date -u -d "10:07" +%s); NOW=$(date -u +%s)
MIN=$(( (END - NOW) / 60 - 1 ))
if [ $MIN -ge 4 ]; then
  echo "launch q3b with deadline ${MIN} min"
  PYTHONUNBUFFERED=1 .venv/bin/python src/gpu_q3.py --deadline-min $MIN > logs/run_q3b.out 2>&1 &
  Q=$!; echo $Q > logs/q3b.pid; wait $Q; echo "q3b exit $? at $(date -u +%H:%M:%S)"
else
  echo "no time for q3b"
fi
