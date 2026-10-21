#!/usr/bin/env bash
# POST-HOC (not pre-registered): after the frozen queue and the readouts finish, replicate iteration 5's PN cells
# (exp27's PN5 seeds + per-template ban-free unit) under W16A16 and W8A8, then label the new rows.
cd "$(dirname "$0")"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
while [ ! -f results/readouts_done.flag ]; do sleep 20; done
.venv/bin/python src/run_e.py --stage gen --tags posthoc_it5 --deadline-min "${PH_MIN:-25}" > logs/stage_posthoc.out 2>&1
echo "posthoc gen exit $?" >> logs/pipeline.log
.venv/bin/python src/label_e.py > logs/label_posthoc.out 2>&1
echo "posthoc label exit $?" >> logs/pipeline.log
date -u +%FT%TZ > results/posthoc_done.flag
