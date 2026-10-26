#!/bin/bash
# GPU chain: Phase A -> (labels) -> Phase B, association, ladder, novelty, 'can' -> (labels) -> commit #2 -> bans
cd "$(dirname "$0")/.."
PY=.venv/bin/python
while kill -0 32412 2>/dev/null; do sleep 10; done
$PY src/wait_labels.py raw_phaseA.jsonl raw_pilot.jsonl || exit 1
$PY src/banfree.py all_after_A > logs/banfree_after_A.out 2>&1 || { echo "after_A failed"; exit 1; }
$PY src/wait_labels.py raw_phaseA.jsonl raw_phaseB.jsonl raw_novelty.jsonl raw_can.jsonl || exit 1
$PY src/commit2.py > logs/commit2.out 2>&1 || { echo "commit2 failed"; exit 1; }
$PY src/bans.py > logs/bans.out 2>&1 || { echo "bans failed"; exit 1; }
$PY src/wait_labels.py raw_bans.jsonl || exit 1
echo CHAIN_DONE
