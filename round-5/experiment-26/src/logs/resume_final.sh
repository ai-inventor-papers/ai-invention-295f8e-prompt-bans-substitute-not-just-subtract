set -e
cd .
for s in src/novelty_audit.py audit/rederive.py audit/commit_order.py tests/test_analysis.py tests/test_cpu.py tests/test_datasets.py src/vendor_check.py src/figures.py src/outputs.py; do
  echo "=== $s"; .venv/bin/python $s > logs/final_$(basename $s .py).out 2>&1 || { echo "FAILED $s"; tail -20 logs/final_$(basename $s .py).out; exit 1; }
done
echo ALL_DONE
