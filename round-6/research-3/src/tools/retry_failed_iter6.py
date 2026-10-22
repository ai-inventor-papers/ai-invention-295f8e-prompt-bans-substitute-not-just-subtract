"""Retry the round-1 call that returned HTTP 429 (E5, query q20 of FK1); logged again with its status; raw file overwritten.
Usage: python -I tools/retry_failed_iter6.py"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sat_search_iter6 as S  # noqa: E402

S.F.init_web_fetch()
time.sleep(8)
f, q, _ = S.QUERIES[20]
S.e5_openreview("q20", f, q)
S.write_candidates()
