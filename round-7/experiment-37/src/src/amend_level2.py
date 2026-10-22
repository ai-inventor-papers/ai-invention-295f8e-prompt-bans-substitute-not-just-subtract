#!/usr/bin/env python3
"""amendment3: Level 2 (partial) - raise S on T03 by +1,000 (1,500 -> 2,500) and keep the K arms >= S/2
(EAP, BINT 750 -> 1,250). Committed before the samples it governs; the run resumes T03's saved search state."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PRED, commit, read_json, setup_logging, utc_now, write_json  # noqa: E402

setup_logging("amend3")
c1 = read_json(PRED / "commit1.json")
N = dict(c1["N"]["T03"])
N.update({"S": 2500, "EAP": 1250, "BINT": 1250})
plan = {"utc": utc_now(), "level": "2 (partial: T03 +1,000 S)", "N": {"T03": N}, "task_order": ["T03"],
        "base": "commit1.json", "reason": "GPU time remained after Levels 0-1 (~1 GPU-hour used of 2.3); Level 2 raises S "
        "on T03 first; the K arms are raised to S/2 so matched-effort extrapolation stays within 2x; T2 is not raised "
        "because the binding constraint is the wall-clock needed for adjudication and manual reads",
        "s_star": c1["s_star"]}
write_json(PRED / "amendment3.json", plan)
commit([PRED / "amendment3.json"], "amendment3", "Level 2 (T03) before its samples")
