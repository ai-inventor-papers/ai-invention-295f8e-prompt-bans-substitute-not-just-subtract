#!/usr/bin/env bash
# Chain after the committed queue: restore dropped cells (GPU) and keep labelling until the restore finishes.
cd "$(dirname "$0")/.."
.venv/bin/python src/gen5_restore.py > logs/gen5_restore.out 2>&1 &
RPID=$!
while [ ! -f results/gpu_done.flag ]; do sleep 20; done
while kill -0 $(cat logs/label5.pid) 2>/dev/null; do sleep 10; done
.venv/bin/python -c "
import sys; sys.path.insert(0, 'src')
import label_worker_v4 as LW
from cfg import DATA_DIR, RESULTS_DIR, setup_logging
LW.PATH_JUDGE_CAP = 0.25; LW.BENCH_JUDGE_CAP = 0.15; LW.N_WORKERS = 8
setup_logging('label5_restore')
LW.run_worker(DATA_DIR / 'samples_raw.jsonl', DATA_DIR / 'labels.jsonl', RESULTS_DIR / 'restore_done.flag', chunk=40)
" > logs/label5_restore.out 2>&1
wait $RPID
