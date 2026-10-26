#!/usr/bin/env bash
# Post-stop pipeline (run from the workspace root after the search process has exited).
set -u
cd "$(dirname "$0")/.."
PY=.venv/bin/python
echo "analyze $(date -u +%T)"; nice -n 5 $PY src/analyze_run.py --workers 5 > logs/analyze.out 2>&1; echo "exit $?"
echo "judges $(date -u +%T)"; timeout 600 $PY src/judges.py > logs/judges.out 2>&1; echo "exit $?"
echo "figures $(date -u +%T)"; timeout 300 $PY src/figures.py > logs/figures.out 2>&1; echo "exit $?"
echo "rederive $(date -u +%T)"; timeout 900 $PY audit/rederive.py > logs/rederive.out 2>&1; echo "exit $?"
echo "done $(date -u +%T)"
