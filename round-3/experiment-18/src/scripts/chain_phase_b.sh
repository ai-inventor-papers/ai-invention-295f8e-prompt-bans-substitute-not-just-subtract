#!/usr/bin/env bash
# GPU chain actually used for phase B: wait for the bf16 long-form job (PID-based), swap the bf16 server for the
# FP8 server, run the FP8 veto unit tests, then the bench walk (+LOS/two-step) and the FP8 thinking-off long-form
# concurrently.  Only PIDs written by this artifact are signalled.
set -u
cd "$(dirname "$0")/.."
export PYTHONDONTWRITEBYTECODE=1
PY=.venv/bin/python
LF_PID=$(cat logs/longform_bf16.pid)
while kill -0 "$LF_PID" 2>/dev/null; do sleep 15; done
echo "$(date +%T) bf16 long-form done" >> logs/chain_phase_b.log
$PY src/server.py bf16 stop >> logs/chain_phase_b.log 2>&1
sleep 5
$PY src/server.py fp8 start 20480 96 >> logs/chain_phase_b.log 2>&1 || { echo "fp8 server failed" >> logs/chain_phase_b.log; exit 1; }
echo "$(date +%T) fp8 server up" >> logs/chain_phase_b.log
$PY src/phases.py unit_fp8 > logs/unit_fp8.out 2>&1
echo "$(date +%T) fp8 unit tests exit $?" >> logs/chain_phase_b.log
$PY src/phases.py B > logs/phase_B.out 2>&1 &
echo $! > logs/phase_B.pid
$PY src/longform.py fp8_off 50 > logs/longform_fp8_off.out 2>&1 &
echo $! > logs/longform_fp8_off.pid
echo "$(date +%T) phase B and fp8_off launched" >> logs/chain_phase_b.log
