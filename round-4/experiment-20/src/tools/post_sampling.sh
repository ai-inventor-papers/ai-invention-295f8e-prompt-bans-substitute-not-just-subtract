#!/usr/bin/env bash
# Post-sampling pipeline (run from the artifact root once results/sampling_done.json exists).
set -euo pipefail
PY=.venv/bin/python
# 1. wait for the label worker to drain the backlog and exit
while kill -0 "$(cat logs/label_worker.pid 2>/dev/null || echo 0)" 2>/dev/null; do sleep 10; done
# 2. K=7 labels (CPU) and the U4 follow-up diagnostic (GPU) in parallel
(cd src && ../$PY label_k7.py > ../logs/k7_final.out 2>&1) & K7=$!
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True $PY tests/u4_diagnostic.py > logs/u4_diag.out 2>&1 & U4=$!
wait $K7
# 3. commit #3: final analysis code, then the analysis (2,000 bootstrap replicates)
(cd src && ../$PY -c "
from commit import commit
from cfg import ROOT
fs=[ROOT/'src'/f for f in ('analysis.py','audit.py','finalize.py','label_k7.py','outputs.py','figures.py')]+[ROOT/'audit'/'rederive.py']
for r in commit(fs,'commit3'): print(r['utc'], r['path'])
")
(cd src && ../$PY analysis.py 2000 5) > logs/analysis_final.out 2>&1
# 4. audit (index exists; controls + pool judges + tie-break; cached calls are free)
(cd src && ../$PY audit.py run) > logs/audit_final.out 2>&1
wait $U4 || true
echo "post-sampling pipeline done"
