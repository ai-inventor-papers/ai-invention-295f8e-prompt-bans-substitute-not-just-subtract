#!/bin/bash
# Third hand-off chain: after chain6b (few-shot A/B + q_lik scoring) -> few-shot stage C for the push units still below
# 20 correct (cap 300 draws) -> wait for every pt label -> pt label audit (+ revision round) -> commit #1 -> fresh pushes.
# Time-based drop rule (protocol): if the pushes cannot start before 00:45 UTC, fresh FD on T1 and T2 is dropped first.
set -u
cd "$(dirname "$0")/.."
PY=.venv/bin/python
PUSH=R6,T04,T05,T10,T03,T11,T1,T2
if [ -n "${1:-}" ]; then
  while kill -0 "$1" 2>/dev/null; do sleep 10; done
fi
echo "$(date -u +%FT%TZ) ptfs stage C start" >> logs/chain6.log
$PY src/gen6.py ptfs --tasks $PUSH --bc-tasks $PUSH --max-stage C > logs/gen6_ptfs_c.out 2>&1
echo "$(date -u +%FT%TZ) ptfs stage C exit $?" >> logs/chain6.log
$PY - << 'PYEOF'
import sys
sys.path.insert(0, "src")
from gen6 import RAW, wait_labels
from cfg import read_jsonl
wait_labels({r["row_id"] for r in read_jsonl(RAW["ptfs6"])}, timeout_s=1800)
PYEOF
echo "$(date -u +%FT%TZ) audit pt start" >> logs/chain6.log
$PY src/audit6.py pt > logs/audit6_pt.out 2>&1
echo "$(date -u +%FT%TZ) audit pt exit $?" >> logs/chain6.log
$PY src/forecasts6.py commit1 > logs/forecasts6_commit1.out 2>&1
RC=$?
echo "$(date -u +%FT%TZ) commit1 exit $RC" >> logs/chain6.log
if [ $RC -ne 0 ]; then exit $RC; fi
HHMM=$(date -u +%H%M)
DROP=""
if [ "$HHMM" -ge "0045" ] && [ "$HHMM" -lt "1200" ]; then DROP="--drop-fd T1,T2"; fi
echo "$(date -u +%FT%TZ) push6 start $DROP" >> logs/chain6.log
$PY src/gen6.py push6 $DROP > logs/gen6_push6.out 2>&1
echo "$(date -u +%FT%TZ) push6 exit $?" >> logs/chain6.log
