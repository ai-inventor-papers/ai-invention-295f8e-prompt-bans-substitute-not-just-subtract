#!/usr/bin/env python3
"""Amendment commit: sha256 of the analysis code (and the independent re-derivation) before the final scoring run."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import ROOT, sha256_file
from commit6 import commit

FILES = ["src/analysis6.py", "src/stats6.py", "src/lcontest.py", "src/report6.py", "src/figures6.py",
         "src/outputs6.py", "src/novelty6.py", "audit/rederive.py"]
NAME = sys.argv[1] if len(sys.argv) > 1 else "amendment3_analysis_code"
NOTE = (" ".join(sys.argv[2:]) if len(sys.argv) > 2 else
        "interim Stage A tables were computed during collection for monitoring/debugging only; the final headlines "
        "are computed with the code hashed here")
rec = commit(NAME, {"code_sha256": {f: sha256_file(ROOT / f) for f in FILES}, "note": NOTE})
print(rec["sha256"])
