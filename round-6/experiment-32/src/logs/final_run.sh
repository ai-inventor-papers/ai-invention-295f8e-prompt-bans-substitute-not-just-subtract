#!/bin/bash
# Final sequence: wait for the GPU plan, stop the daemon (by PID), GPU tests, adjudication, novelty audit, final stage.
cd "$(dirname "$0")/.."
remaining() { .venv/bin/python -c "
import json
plan = json.load(open('data/gpu_plan_v3.json'))
done = {json.loads(l)['task'] for l in open('results/gpu_tasks.jsonl')}
print(sum(1 for i in plan if f'{i[0]}|{i[1]}|{i[2] if len(i)>2 else None}' not in done))"; }
until [ "$(remaining)" = "0" ]; do sleep 15; done
GP=$(cat logs/gpu6.pid); kill $GP; while kill -0 $GP 2>/dev/null; do sleep 2; done
echo "GPU plan done, daemon stopped $(date -u)"
.venv/bin/python src/gpu_tests6.py > logs/gpu_tests6.out 2>&1; echo "gpu tests done $(date -u)"
pending_all() { .venv/bin/python -c "
import json
lab = {json.loads(l)['key'] for l in open('data/labels.jsonl')}
n = 0
for l in open('data/samples_raw.jsonl'):
    r = json.loads(l)
    n += f\"{r['unit']}|{r['template']}|{r['arm']}|{r['slot']}|{r['model_tag']}\" not in lab
print(n)"; }
until [ "$(pending_all)" = "0" ]; do sleep 15; done
echo "labels complete $(date -u)"
.venv/bin/python -c "
import sys; sys.path.insert(0, 'src')
from cfg5 import setup_logging; setup_logging('adjudicate_final')
from labels_view import adjudicate_pending
n = 1
while n:
    n = adjudicate_pending(None, max_items=400)
    print('adjudicated', n)
" > logs/adjudicate_final.out 2>&1; echo "adjudication done $(date -u)"
.venv/bin/python src/novelty6.py > logs/novelty_final.out 2>&1; echo "novelty done $(date -u)"
.venv/bin/python method.py > logs/method_final.out 2>&1; echo "method done $(date -u) rc=$?"
