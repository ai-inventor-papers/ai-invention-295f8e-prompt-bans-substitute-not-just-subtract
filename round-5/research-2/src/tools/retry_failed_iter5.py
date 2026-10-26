"""Retry the round-1 calls that failed with HTTP 429 / rate limits (logged again with status; raw files overwritten).
Usage: python -I tools/retry_failed_iter5.py"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sat_search_iter5 as S  # noqa: E402

S.F.init_web_fetch()
for i in (20, 21, 22, 23, 24):
    f, q, _ = S.QUERIES[i]
    time.sleep(8)
    S.e5_openreview(f"q{i}", f, q)
f, q, _ = S.QUERIES[17]
S.e4_s2("q17", f, q)
time.sleep(5)
S.s2_citations("BACo", "2511.05650")
time.sleep(5)
S.s2_citations("ConformativeDecoding", "2507.20956")
S.write_candidates()
