#!/usr/bin/env python3
"""COMMIT #0b (bug fix of the frozen analysis, before commit #1, before any push row and before any analysis output):
unit_clustered() built per-unit records without the 'nudge' key that hit_test()'s per-event listing reads (KeyError on
the first call). The fix adds 'nudge' = 'FD+PN' (the nudge types pooled into the unit); no rule, threshold or test
changes. Logged as deviation D10."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import PRED_DIR, add_deviation
import commit as C

rec = C.commit("commit#0b frozen-analysis bug fix (unit_clustered 'nudge' key)", [PRED_DIR / "analysis_L_gemma.py"],
               note="KeyError fix only; no rule changed; before commit #1 and before any push6 row")
add_deviation("D10", "Commit #0b: the frozen analysis's unit_clustered() lacked the 'nudge' key read by hit_test() "
                     "(KeyError on first use, found in a dry run on exp28 rows with the draft forecasts); fixed by adding "
                     "'nudge' = 'FD+PN' before commit #1 and before any fresh push row; no rule or threshold changed.")
print(rec["utc"], rec["hash"][:16])
