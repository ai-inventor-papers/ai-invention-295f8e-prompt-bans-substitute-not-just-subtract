#!/bin/bash
# waits for the main search PID to exit, then starts the NS run (no database; fixed FF/BF parents)
cd "."
while kill -0 2414 2>/dev/null; do sleep 10; done
echo "main ended $(date -u +%FT%TZ); launching NS" >> logs/launch_ns.log
HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 nohup uv run --no-sync python -I src/search.py --run ns --seeds 0,1 --rounds 40 --calls-per-round 25 --arms NS --workers 10 --deadline 1792880400.0 > logs/search_ns_stdout.log 2>&1 &
echo "NS_PID=$!" > logs/ns_pid.txt
