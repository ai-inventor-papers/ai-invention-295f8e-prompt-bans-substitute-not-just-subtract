#!/bin/bash
# After stage 2: transplant validity run -> lambda decision -> full transplant -> wait for every label.
set -u
cd "$(dirname "$0")/.."
PY=.venv/bin/python
log() { echo "$(date -u +%H:%M:%S) $*" >> logs/chain_stage3.log; }
PREV_PID=$1
while kill -0 "$PREV_PID" 2>/dev/null; do sleep 5; done
grep -q "stage2 done" logs/chain_after_pt.log || { log "stage 2 did not finish; not starting stage 3"; exit 1; }
log "stage 2 chain ended"
$PY src/gen.py stage3_valid > logs/gen_stage3_valid.out 2>&1 || { log "stage3_valid failed"; exit 1; }
log "stage3_valid done"
$PY src/wait_labels.py raw_transplant_valid.jsonl >> logs/chain_stage3.log 2>&1 || log "label wait timed out"
$PY src/transplant_decide.py > logs/transplant_decide.out 2>&1 || { log "decide failed"; exit 1; }
log "decide done: $(cat results/transplant_lambda.json | head -c 120)"
$PY src/gen.py stage3 > logs/gen_stage3.out 2>&1 || { log "stage3 failed"; exit 1; }
log "stage3 done"
$PY src/wait_labels.py raw_transplant.jsonl raw_push.jsonl raw_confirm.jsonl >> logs/chain_stage3.log 2>&1 || log "label wait timed out"
log "all labelled"
