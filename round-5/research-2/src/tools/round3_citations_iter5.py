"""Round 3 of the saturation search (stop rule, protocol 2g): forward citations (Semantic Scholar) of the closest new
hits found in rounds 1-2, and backward references of the two closest hits per flag (Wohlin snowballing).
Usage: python -I tools/round3_citations_iter5.py"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sat_search_iter5 as S  # noqa: E402

FORWARD = {"CrossPatching": "2605.07284", "SLR": "2602.06665", "PASTA": "2605.30526",
           "FrankenMerging": "2610.22999", "DuanPerProblem": "2610.04978", "OozeerTransfer": "2503.04429"}
BACKWARD = {"FLAG_A": ["2605.07284", "2602.06665"], "FLAG_B": ["2607.20543", "2610.04978"],
            "FLAG_C": ["2503.00691", "2605.28022"]}
S.F.init_web_fetch()
for name, aid in FORWARD.items():
    S.s2_citations(name, aid)
    time.sleep(1.5)
for flag, ids in BACKWARD.items():
    for aid in ids:
        S.s2_citations(f"{flag}_{aid.replace('.', '_')}", aid, kind="references")
        time.sleep(1.5)
S.write_candidates()
