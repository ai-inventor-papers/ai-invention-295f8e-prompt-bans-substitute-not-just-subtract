#!/usr/bin/env python3
"""Verify the commitments.log hash chain (exits 1 on a break). Also used by the CPU test that edits one byte."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commit5 import verify  # noqa: E402

if __name__ == "__main__":
    r = verify()
    print(json.dumps(r, indent=1))
    sys.exit(1 if r["chain_breaks"] else 0)
