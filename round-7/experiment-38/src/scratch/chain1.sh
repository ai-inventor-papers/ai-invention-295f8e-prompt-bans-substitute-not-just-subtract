#!/bin/bash
cd .
while kill -0 $1 2>/dev/null; do sleep 5; done
for st in yv g2smoke g3a g3b; do
  echo "=== $st $(date -u +%H:%M:%S)"; .venv/bin/python method.py --stage $st > logs/run_$st.out 2>&1; rc=$?; echo "=== $st rc=$rc $(date -u +%H:%M:%S)"
  if [ $rc -ne 0 ] && [ "$st" != "g2smoke" ]; then exit $rc; fi
done
