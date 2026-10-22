"""Re-run round-1 calls that ended in HTTP 429 (logged as a retry with status 'rerun-after-429'). Usage: python -I tools/rerun_failed_iter6.py"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sat_search_iter6 as S  # noqa: E402

S.F.init_web_fetch()
failed = [json.loads(l) for l in S.LOG.read_text().splitlines()]
failed = [r for r in failed if r["round"] == "R1" and not r["status"].startswith("ok")]
qs = {q["id"]: q for q in S.QUERIES}
for r in failed:
    time.sleep(8)
    q = qs[r["query_id"]]
    if r["engine"].startswith("E4"):
        S.e4(q, "R1")
    elif r["engine"].startswith("E5"):
        S.e5(q, "R1")
S.aggregate()
