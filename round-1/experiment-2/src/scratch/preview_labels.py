import sys, json
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "labeller")); sys.path.insert(0, str(ROOT / "tasks"))
from common import read_jsonl, setup_logger
from label import cpu_stage
logger = setup_logger("preview")
rows = read_jsonl(ROOT / "data" / "raw_phaseA.jsonl")
cpu_stage(rows, 4, logger)
for t in ("t1", "t2"):
    b = [r for r in rows if r["task"] == t and r["condition"] == "baseline"]
    print(t, "baseline n", len(b), "rt", Counter(r["rt_label"] for r in b), "ast", Counter(r["ast_label"] for r in b), "pass", sum(r["passed"] for r in b))
    agree = sum(r["rt_conf"] and r["ast_conf"] and r["rt_label"] == r["ast_label"] for r in rows if r["task"] == t)
    print(t, "runtime+ast agreement coverage", agree, "/", sum(1 for r in rows if r["task"] == t))
    for c in sorted({r["condition"] for r in rows if r["task"] == t and r["condition"] != "baseline"}):
        rr = [r for r in rows if r["task"] == t and r["condition"] == c]
        print("  ", c, len(rr), "pass", sum(r["passed"] for r in rr), "rt", dict(Counter(r["rt_label"] for r in rr)))
