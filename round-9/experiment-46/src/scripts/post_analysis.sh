#!/usr/bin/env bash
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
while kill -0 98137 2>/dev/null || kill -0 98493 2>/dev/null; do sleep 5; done
.venv/bin/python method.py analyse rsa > logs/analyse_rsa.out 2>&1 || echo "rsa failed"
.venv/bin/python method.py figures > logs/figures.out 2>&1 || echo "figures failed"
.venv/bin/python method.py outputs > logs/outputs.out 2>&1 || echo "outputs failed"
.venv/bin/python audit/rederive.py > logs/rederive.out 2>&1 || echo "rederive mismatches"
.venv/bin/python scripts/make_tests.py > logs/tests.out 2>&1 || echo "tests failed"
./scripts/finalize.sh > logs/finalize.out 2>&1 || echo "finalize failed"
echo "post done $(date -u +%H:%M:%S)"
