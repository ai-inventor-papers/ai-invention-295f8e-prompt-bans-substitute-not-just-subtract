#!/bin/bash
# After the GPU chain (q2 -> skipped b2) ends, finish engine-b confirmations until 10:06 UTC.
cd "$(dirname "$0")/.."
CP=$(cat logs/chain.pid)
while kill -0 $CP 2>/dev/null; do sleep 10; done
echo "chain ended at $(date -u +%H:%M:%S)"
END=$(date -u -d "10:06" +%s); NOW=$(date -u +%s)
MIN=$(( (END - NOW) / 60 - 2 ))
if [ $MIN -ge 4 ]; then
  echo "launch q3 (engine-b confirmations) with deadline ${MIN} min"
  PYTHONUNBUFFERED=1 .venv/bin/python src/gpu_q3.py --deadline-min $MIN > logs/run_q3.out 2>&1 &
  Q3=$!; echo $Q3 > logs/q3.pid; wait $Q3; echo "q3 exit $? at $(date -u +%H:%M:%S)"
else
  echo "no time for q3"
fi
echo "chain2 done $(date -u +%H:%M:%S)"
