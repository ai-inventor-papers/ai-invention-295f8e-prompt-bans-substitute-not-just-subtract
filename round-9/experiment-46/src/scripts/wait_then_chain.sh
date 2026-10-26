#!/usr/bin/env bash
# Waits for the pools stage (PID given) to end successfully, then starts run_chain.sh.
cd "$(dirname "$0")/.."
while kill -0 "$1" 2>/dev/null; do sleep 10; done
if grep -q "=== stage pools done ===" logs/run_pools_r1.out; then ./run_chain.sh 0; else echo "pools failed"; fi
