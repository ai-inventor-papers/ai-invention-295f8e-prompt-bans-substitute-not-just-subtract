#!/bin/bash
cd "$(dirname "$0")/.."
PY=.venv/bin/python
$PY src/commit2.py > logs/commit2.out 2>&1 || { echo "commit2 failed"; exit 1; }
$PY src/bans.py > logs/bans.out 2>&1 || { echo "bans failed"; exit 1; }
$PY src/wait_labels.py raw_bans.jsonl || exit 1
$PY src/banfree.py t16 --tasks T2,T05,T04,T1,T10,T11 > logs/banfree_t16.out 2>&1 || { echo "t16 failed"; exit 1; }
$PY src/wait_labels.py raw_t16.jsonl || exit 1
echo CHAIN_DONE
