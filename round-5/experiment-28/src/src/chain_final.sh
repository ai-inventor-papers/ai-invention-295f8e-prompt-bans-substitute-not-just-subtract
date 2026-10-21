#!/bin/bash
# After stage 3 and its labels: novelty audit -> frozen analysis -> bookkeeping -> outputs -> re-derivation -> figures ->
# report -> CPU tests (grep audit over every fed prompt) -> mini/preview variants of method_out.json.
set -u
cd "$(dirname "$0")/.."
PY=.venv/bin/python
log() { echo "$(date -u +%H:%M:%S) $*" >> logs/chain_final.log; }
PREV_PID=$1
while kill -0 "$PREV_PID" 2>/dev/null; do sleep 5; done
grep -q "all labelled\|label wait timed out" logs/chain_stage3.log || log "stage-3 chain did not finish cleanly; continuing with the data present"
$PY src/novelty_audit.py > logs/novelty_audit.out 2>&1 || log "novelty audit failed"
log "novelty done"
$PY src/final_analysis.py > logs/final_analysis.out 2>&1 || { log "analysis failed"; exit 1; }
log "analysis done"
$PY src/bookkeeping.py > logs/bookkeeping.out 2>&1 || log "bookkeeping failed"
$PY src/outputs.py > logs/outputs.out 2>&1 || { log "outputs failed"; exit 1; }
log "outputs done"
$PY audit/rederive.py > logs/rederive.out 2>&1 || log "rederive failed"
log "rederive done"
$PY src/outputs.py > logs/outputs2.out 2>&1 || log "outputs (2nd, with rederive) failed"
$PY src/figures.py > logs/figures.out 2>&1 || log "figures failed"
$PY src/report.py > logs/report.out 2>&1 || log "report failed"
$PY src/tests_cpu.py > logs/tests_cpu_final.out 2>&1 || log "tests failed"
log "final chain done"
