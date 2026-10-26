#!/usr/bin/env bash
# B2 v2 (primary): fixed batch shapes + one-token-path fork caches. Waits for queue2 (B3, B1), archives the v1
# (variable batch shape) outputs, then reruns s1 -> s2 -> s3.
cd "$(dirname "$0")"
QPID=$(cat logs/run_queue2.pid)
while kill -0 $QPID 2>/dev/null; do sleep 5; done
mkdir -p results/v1_variable_batch
for f in results/b2_tf_B3.jsonl results/b2_tf_T10.jsonl results/b2_rev_B3.jsonl results/b2_rev_T10.jsonl \
         results/random_sets.json results/gpu_tests_b2.json results/capture_instr.json results/capture_base.json; do
  [ -f "$f" ] && mv "$f" results/v1_variable_batch/
done
cd src
../.venv/bin/python cmap9.py s1 all && ../.venv/bin/python cmap9.py s2 all && ../.venv/bin/python cmap9.py s3 all
echo QWEN_V2_DONE
