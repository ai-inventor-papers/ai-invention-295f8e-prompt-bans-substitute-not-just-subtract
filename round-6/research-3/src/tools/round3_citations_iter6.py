"""Round 3 of the saturation search (inherited stop rule): forward citations (Semantic Scholar) of the closest new hits of
rounds 1-2, and backward references of the two closest arXiv-indexed hits per flag (Wohlin snowballing). The closest FLAG E
candidates that are ICLR 2027 submissions (OR:8iTqrW1sxY, OR:h57duZqLOr) have no arXiv/S2 record, so cannot be chased.
Usage: python -I tools/round3_citations_iter6.py"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sat_search_iter6 as S  # noqa: E402

FORWARD = {"PAHQ": "2510.23264", "GravitationalReversion": "2606.28525", "ReEmergentMisalignment": "2507.03662",
           "GreedyNotPrecisionInvariant": "2609.26621", "KVCacheAlignmentCollapse": "2606.09864",
           "ResistAlignment": "2406.06144"}
BACKWARD = {"FLAG_E": ["2510.23264", "2609.06473"], "FLAG_L": ["2507.03662", "2606.28525"]}
S.F.init_web_fetch()
for name, aid in FORWARD.items():
    S.s2_citations(name, aid)
    time.sleep(1.5)
for flag, ids in BACKWARD.items():
    for aid in ids:
        S.s2_citations(f"{flag}_{aid.replace('.', '_')}", aid, kind="references")
        time.sleep(1.5)
S.write_candidates()
