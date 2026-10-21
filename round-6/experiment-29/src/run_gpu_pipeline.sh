#!/usr/bin/env bash
# Generation queue -> gen_done flag -> mechanism readouts -> readouts_done flag (all relative to this folder)
cd "$(dirname "$0")"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
GEN_MIN=${GEN_MIN:-150}
RO_MIN=${RO_MIN:-30}
.venv/bin/python src/run_e.py --stage gen --deadline-min "$GEN_MIN" > logs/stage_gen.out 2>&1
echo "gen exit $?" >> logs/pipeline.log
date -u +%FT%TZ > results/gen_done.flag
.venv/bin/python src/run_e.py --stage readouts --deadline-min "$RO_MIN" > logs/stage_readouts.out 2>&1
echo "readouts exit $?" >> logs/pipeline.log
date -u +%FT%TZ > results/readouts_done.flag
