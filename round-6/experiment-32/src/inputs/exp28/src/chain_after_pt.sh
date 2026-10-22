#!/bin/bash
# Hand-off after the pt stage: labels -> predictor draft -> (opening ladder on GPU || re-gate on CPU/API) -> commit #1
# -> stage 2 (pipelined push population + confirmation). Each step logs to logs/chain_after_pt.log.
set -u
cd "$(dirname "$0")/.."
PY=.venv/bin/python
log() { echo "$(date -u +%H:%M:%S) $*" >> logs/chain_after_pt.log; }
PT_PID=$1
while kill -0 "$PT_PID" 2>/dev/null; do sleep 5; done
log "pt stage ended"
$PY src/wait_labels.py raw_ptchat.jsonl raw_ptplain.jsonl raw_twin.jsonl raw_novelty.jsonl >> logs/chain_after_pt.log 2>&1 || log "label wait timed out"
$PY src/predictors.py draft > logs/predictors_draft.out 2>&1 || { log "draft failed"; exit 1; }
log "draft done"
$PY src/gen.py ladder > logs/gen_ladder.out 2>&1 &
LPID=$!
$PY src/regate.py > logs/regate.out 2>&1 || log "regate failed"
log "regate done"
wait $LPID || { log "ladder failed"; exit 1; }
log "ladder done"
$PY src/predictors.py commit1 > logs/predictors_commit1.out 2>&1 || { log "commit1 failed"; exit 1; }
log "commit1 done"
$PY src/gen.py stage2_pipelined > logs/gen_stage2.out 2>&1 || { log "stage2 failed"; exit 1; }
log "stage2 done"
