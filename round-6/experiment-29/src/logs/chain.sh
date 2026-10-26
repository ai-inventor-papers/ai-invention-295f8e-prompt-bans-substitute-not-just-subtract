#!/bin/bash
# GPU chain: wait for weight set B (gpu_b.py) to exit, then weight set Q2, then the weight-set-B alpha-1 follow-up.
cd "$(dirname "$0")/.."
BPID=$(cat logs/b.pid)
while kill -0 $BPID 2>/dev/null; do sleep 15; done
echo "gpu_b exited at $(date -u +%H:%M:%S)"
END_B2=$(date -u -d "09:55" +%s)
NOW=$(date -u +%s)
Q2MIN=$(( (END_B2 - NOW) / 60 - 5 ))
[ $Q2MIN -gt 70 ] && Q2MIN=70
[ $Q2MIN -lt 15 ] && Q2MIN=15
echo "launch q2 with deadline ${Q2MIN} min"
PYTHONUNBUFFERED=1 .venv/bin/python src/gpu_q.py --phase q2 --deadline-min $Q2MIN > logs/run_q2.out 2>&1 &
QPID=$!; echo $QPID > logs/q2.pid; wait $QPID; echo "q2 exit $? at $(date -u +%H:%M:%S)"
NOW=$(date -u +%s)
B2MIN=$(( (END_B2 - NOW) / 60 ))
if [ $B2MIN -ge 12 ]; then
  echo "launch b2 (engine d alpha 1) with deadline ${B2MIN} min"
  PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True PYTHONUNBUFFERED=1 .venv/bin/python src/gpu_b2.py --engines d --tasks T10,T2 --deadline-min $B2MIN > logs/run_b2.out 2>&1 &
  B2PID=$!; echo $B2PID > logs/b2.pid; wait $B2PID; echo "b2 exit $? at $(date -u +%H:%M:%S)"
else
  echo "no time for b2 (${B2MIN} min left before 09:55)"
fi
echo "chain done $(date -u +%H:%M:%S)"
