import sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "labeller")); sys.path.insert(0, str(ROOT / "tasks"))
from common import read_jsonl, setup_logger
from label import label_rows, spent_usd
logger = setup_logger("test_label_mini")
rows = read_jsonl(ROOT / "data" / "raw_phaseA.jsonl")[:24]
label_rows(rows, logger, workers=6)
for r in rows:
    print(r["task"], r["condition"], "| label", r["label"], "| src", r["labeller_source"], "| rt", r["rt_label"], r["rt_conf"], "| ast", r["ast_label"], r["ast_conf"], "| passed", r["passed"], r.get("fail_kind"), "| judge", r.get("judge_label"))
print("spent", spent_usd())
