#!/usr/bin/env python3
"""Pre-computes the sandbox evaluations of the iteration-2 forced programs and references (cache warm-up only)."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(1, str(ROOT / "vendor" / "exp9"))
from common import setup_logging
setup_logging("warm_cache")
import programs, stage_pools
codes = [p["code"] for p in stage_pools._s1() + stage_pools._s3() if p["code"]]
programs.evaluate(codes, workers=8)
print("warm done", len(codes))
