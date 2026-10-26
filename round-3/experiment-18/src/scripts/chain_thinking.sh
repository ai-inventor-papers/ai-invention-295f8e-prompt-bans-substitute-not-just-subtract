#!/usr/bin/env bash
# After the phase-B short arms finish (PID-based wait), run the thinking-on long-form floor (T1/T2, N=10 per prompt).
set -u
cd "$(dirname "$0")/.."
export PYTHONDONTWRITEBYTECODE=1
while [ ! -f logs/phase_B.pid ]; do sleep 10; done
B_PID=$(cat logs/phase_B.pid)
while kill -0 "$B_PID" 2>/dev/null; do sleep 15; done
echo "$(date +%T) phase B short arms done; thinking-on starts" >> logs/chain_phase_b.log
.venv/bin/python src/longform.py fp8_on T1:10,T2:10 > logs/longform_fp8_on.out 2>&1
echo "$(date +%T) thinking-on floor done (exit $?)" >> logs/chain_phase_b.log
