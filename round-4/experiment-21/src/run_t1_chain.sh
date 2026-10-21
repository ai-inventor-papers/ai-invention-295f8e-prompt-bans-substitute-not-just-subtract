#!/usr/bin/env bash
# Waits for the HF chain (PID in logs/chain.pid) to end, then runs optional arm (i) if >= 1.5 h remain before the
# analysis guard (t0 + 4h45), per the plan's G4 rule.
cd "$(dirname "$0")"
export PYTHONDONTWRITEBYTECODE=1
CPID=$(cat logs/chain.pid 2>/dev/null)
while [ -n "$CPID" ] && kill -0 "$CPID" 2>/dev/null; do sleep 20; done
LEFT=$(.venv_hf/bin/python -c "import json,time; t0=json.load(open('results/t0.json'))['t0_unix']; print(int((t0 + 4.75*3600 - time.time())/60))")
echo "HF chain ended at $(date -u +%FT%TZ); minutes left before the analysis guard: $LEFT"
if [ "$LEFT" -ge 90 ]; then
  .venv_vllm/bin/python src/vllm_t1.py
  echo "arm (i) exit $? at $(date -u +%FT%TZ)"
else
  echo "{\"skipped\": \"optional (i)\", \"minutes_left\": $LEFT}" > results/drop_decisions_g4.json
  echo "arm (i) skipped (G4 rule)"
fi
