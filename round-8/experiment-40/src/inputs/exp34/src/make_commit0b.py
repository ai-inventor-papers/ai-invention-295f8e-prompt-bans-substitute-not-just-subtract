#!/usr/bin/env python3
"""Amendment commit0b: sha256 of the analysis drivers and statistics code, frozen before commit #3 (no POP outcome row
of exp29 is readable before commit #3; c7.guarded_e29_rows)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from c7 import PRED, SRC, ROOT, commit, sha256_file, utc_now, write_json, pop_rows_released  # noqa: E402

files = ["analysis7.py", "analysis_push.py", "top5geo.py", "stats7.py", "predict7.py", "pushrun.py", "forkrun.py",
         "fork7.py", "axis7.py"]
assert not pop_rows_released(), "commit0b must precede commit #3"
obj = {"name": "commit0b_analysis_code", "utc": utc_now(),
       "code_sha256": {f"src/{f}": sha256_file(SRC / f) for f in files},
       "note": "analysis drivers frozen before any POP outcome row is opened; later fixes are logged as amendments"}
p = PRED / "commit0b_analysis_code.json"
write_json(p, obj)
print(commit("commit0b_analysis_code", p))
