#!/usr/bin/env bash
# Waits for the vLLM G1 process (PID in logs/vllm.pid) to exit, then runs the HF chain in one process.
cd "$(dirname "$0")"
export PYTHONDONTWRITEBYTECODE=1
VPID=$(cat logs/vllm.pid 2>/dev/null)
while [ -n "$VPID" ] && kill -0 "$VPID" 2>/dev/null; do sleep 20; done
echo "vLLM process ended at $(date -u +%FT%TZ); starting HF chain"
.venv_hf/bin/python method.py --stage hf_chain --tasks T2,T03,T1 --arms iii,iv,ii
echo "HF chain exit $? at $(date -u +%FT%TZ)"
