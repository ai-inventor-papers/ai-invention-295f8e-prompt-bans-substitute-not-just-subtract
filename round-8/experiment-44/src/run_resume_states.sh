#!/usr/bin/env bash
# Resume the post-screen pipeline from the states stage (after a fix). PID-managed.
set -u
cd "$(dirname "$0")"
PY=.venv/bin/python
log() { echo "$(date -u +%H:%M:%S) $*" | tee -a logs/run_after_screen.log; }
$PY method.py states >> logs/run_after_screen.log 2>&1 || { log "states failed"; exit 1; }
$PY method.py geometry >> logs/run_after_screen.log 2>&1 || { log "geometry failed"; exit 1; }
$PY method.py confirm >> logs/run_confirm.log 2>&1 &
CPID=$!
log "confirmation PID $CPID"
$PY method.py m2 >> logs/run_after_screen.log 2>&1 || log "m2 failed"
PREC=$($PY -c "import json;print(json.load(open('results/selection.json'))['m_star_checkpoint']['precision'])")
if [ "$PREC" != "bf16" ]; then
  $PY method.py quantcheck >> logs/run_after_screen.log 2>&1 || log "quantcheck failed"
fi
$PY method.py circle >> logs/run_after_screen.log 2>&1 || log "circle failed"
wait $CPID; log "confirmation exit $?"
log "post-screen pipeline done"
