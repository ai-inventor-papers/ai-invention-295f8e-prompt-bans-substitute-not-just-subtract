#!/bin/bash
# Second hand-off chain (after chain6.sh was stopped at the first few-shot batches): few-shot pt top-up with
# single-prompt batches, push units first; stages B/C only for the 8 push units (time-based, outcome-blind);
# then q_lik scoring (bf16 + fp32 subsample). Usage: src/chain6b.sh
set -u
cd "$(dirname "$0")/.."
PY=.venv/bin/python
ORDER=R6,T04,T05,T10,T03,T11,T1,T2,T06,R1,T08,R3,T13,T14,R2
PUSH=R6,T04,T05,T10,T03,T11,T1,T2
echo "$(date -u +%FT%TZ) ptfs (chain6b) start" >> logs/chain6.log
$PY src/gen6.py ptfs --tasks $ORDER --bc-tasks $PUSH --max-stage B > logs/gen6_ptfs_b.out 2>&1
echo "$(date -u +%FT%TZ) ptfs exit $?" >> logs/chain6.log
$PY src/forecasts6.py draft > logs/forecasts6_draft.out 2>&1
echo "$(date -u +%FT%TZ) qlik score start" >> logs/chain6.log
$PY src/qlik6.py score > logs/qlik6_score.out 2>&1
echo "$(date -u +%FT%TZ) qlik score exit $?" >> logs/chain6.log
