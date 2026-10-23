#!/usr/bin/env bash
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
(TPG_WORKERS=6 .venv/bin/python method.py analyse rsa > logs/analyse_rsa.out 2>&1; .venv/bin/python method.py figures > logs/figures.out 2>&1) &
RF=$!
deadline=$(( $(date +%s) + 420 ))
while kill -0 98493 2>/dev/null && [ "$(date +%s)" -lt "$deadline" ]; do sleep 5; done
if kill -0 98493 2>/dev/null; then kill 98493; for c in $(ps --ppid 98493 -o pid= 2>/dev/null); do kill $c; done; echo "placement stopped at deadline"; fi
wait $RF
.venv/bin/python method.py outputs > logs/outputs.out 2>&1 || echo "outputs failed"
.venv/bin/python audit/rederive.py > logs/rederive.out 2>&1 || echo "rederive mismatches"
.venv/bin/python scripts/make_tests.py > logs/tests.out 2>&1 || echo "tests failed"
./scripts/finalize.sh > logs/finalize.out 2>&1 || echo "finalize failed"
echo "post2 done $(date -u +%H:%M:%S)"
