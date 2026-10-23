#!/usr/bin/env bash
# Post-screen pipeline (PID-managed; never kills by name). Usage: bash run_after_screen.sh
set -u
cd "$(dirname "$0")"
PY=.venv/bin/python
log() { echo "$(date -u +%H:%M:%S) $*" | tee -a logs/run_after_screen.log; }
# 1. wait for the C1 ban sampler, then stop the vLLM server by its recorded PID
while kill -0 "$(cat logs/screen_ban_local.pid)" 2>/dev/null; do sleep 10; done
log "C1 ban sampler ended"
VPID=$(cat logs/vllm_c1.pid)
if kill -0 "$VPID" 2>/dev/null; then kill "$VPID"; log "stopped vLLM $VPID"; fi
for i in $(seq 1 60); do kill -0 "$VPID" 2>/dev/null || break; sleep 2; done
$PY method.py adjudicate ban C1 >> logs/run_after_screen.log 2>&1 || { log "adjudicate C1 failed"; exit 1; }
$PY method.py select >> logs/run_after_screen.log 2>&1 || { log "select failed"; exit 1; }
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
