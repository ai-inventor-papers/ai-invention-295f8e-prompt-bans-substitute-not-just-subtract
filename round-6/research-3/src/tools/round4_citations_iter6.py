"""Round 4 (stop rule continuation): round 3 added one hit scoring 1.5 (2610.24346, E-deployment, adjacent), so the
inherited stop rule requires another round: forward citations (S2) of the round-3 hits closest to an iteration-6 claim and
backward references of 2610.24346. Usage: python -I tools/round4_citations_iter6.py"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sat_search_iter6 as S  # noqa: E402

S.F.init_web_fetch()
for name, aid in {"PrecisionUpgradeAgents": "2610.24346", "DivergenceFidelityQuant": "2609.07664",
                  "PersonaTransplantEM": "2607.04510"}.items():
    S.s2_citations(name, aid)
    time.sleep(1.5)
S.s2_citations("R4_2610_24346", "2610.24346", kind="references")
S.write_candidates()
