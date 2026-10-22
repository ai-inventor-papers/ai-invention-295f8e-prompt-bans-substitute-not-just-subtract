#!/bin/bash
# Hand-off chain actually used after the it session: forced top-up (it) -> q_lik program selection (CPU, background)
# -> few-shot pt repertoire (pt) -> q_lik scoring + fp32 subsample (it). Usage: src/chain6.sh <it_session_pid>
set -u
cd "$(dirname "$0")/.."
PY=.venv/bin/python
if [ -n "${1:-}" ]; then
  while kill -0 "$1" 2>/dev/null; do sleep 10; done
fi
echo "$(date -u +%FT%TZ) forced_topup start" >> logs/chain6.log
$PY src/gen6.py forced_topup > logs/gen6_forced_topup.out 2>&1
echo "$(date -u +%FT%TZ) forced_topup exit $?" >> logs/chain6.log
# wait until every forced row is labelled, then select + scrub (CPU) in the background
$PY - << 'PYEOF'
import sys, time
sys.path.insert(0, "src")
from gen6 import RAW, wait_labels
from cfg import read_jsonl
wait_labels({r["row_id"] for r in read_jsonl(RAW["forced6"])}, timeout_s=1800)
PYEOF
($PY src/qlik6.py select > logs/qlik6_select.out 2>&1; echo "$(date -u +%FT%TZ) select exit $?" >> logs/chain6.log; touch data/QLIK_SELECT_DONE) &
echo "$(date -u +%FT%TZ) ptfs start" >> logs/chain6.log
$PY src/gen6.py ptfs > logs/gen6_ptfs.out 2>&1
echo "$(date -u +%FT%TZ) ptfs exit $?" >> logs/chain6.log
while [ ! -f data/QLIK_SELECT_DONE ]; do sleep 10; done
echo "$(date -u +%FT%TZ) qlik score start" >> logs/chain6.log
$PY src/qlik6.py score > logs/qlik6_score.out 2>&1
echo "$(date -u +%FT%TZ) qlik score exit $?" >> logs/chain6.log
