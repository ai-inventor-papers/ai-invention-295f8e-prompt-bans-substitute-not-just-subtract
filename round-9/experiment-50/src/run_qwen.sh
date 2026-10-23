#!/usr/bin/env bash
# B2 chain: instruct capture (s1) -> base capture + random sets + REV arm (s2) -> instruct patching (s3)
set -e
cd "$(dirname "$0")/src"
[ -f ../cache/instr_T10.pt ] && [ "${REDO_S1:-0}" = "0" ] || ../.venv/bin/python cmap9.py s1 all
../.venv/bin/python cmap9.py s2 all
../.venv/bin/python cmap9.py s3 all
