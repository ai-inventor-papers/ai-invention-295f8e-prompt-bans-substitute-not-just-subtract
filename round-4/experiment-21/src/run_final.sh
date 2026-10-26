#!/usr/bin/env bash
# Final CPU pipeline: waits for optional arm (i) and the label backlog, then audits, analysis, export, re-derivation.
cd "$(dirname "$0")"
export PYTHONDONTWRITEBYTECODE=1
TPID=$(cat logs/t1chain.pid 2>/dev/null)
while [ -n "$TPID" ] && kill -0 "$TPID" 2>/dev/null; do sleep 10; done
sleep 45   # label worker polls every 15 s
echo "== audits $(date -u +%T)"; .venv_hf/bin/python analysis/llm_audits.py
echo "== analyse $(date -u +%T)"; .venv_hf/bin/python method.py --stage analyse
echo "== export $(date -u +%T)"; .venv_hf/bin/python method.py --stage export
echo "== rederive $(date -u +%T)"; .venv_hf/bin/python audit/rederive.py
echo "== done $(date -u +%T)"
