#!/usr/bin/env bash
# GPU chain after S2: prereg -> tests (gate) -> S4 -> {S5 on GPU || S4 labelling on CPU} -> S6 -> S7 -> S8 -> S9
set -u
cd "$(dirname "$0")"
PY=.venv/bin/python
run() { echo "[chain] $(date +%T) start $*"; timeout "$1" $PY method.py "${@:2}"; rc=$?; echo "[chain] $(date +%T) end $* rc=$rc"; return $rc; }
[ -f results/prereg_commit.txt ] || run 600 prereg || exit 1
run 1800 tests || exit 1
run 3600 s4 || exit 1
( run 2400 s4label > logs/s4label.out 2>&1 ) &
LPID=$!
run 5400 s5
wait $LPID
run 2400 s6
run 1800 s7
run 1800 s8
echo "[chain] done"
