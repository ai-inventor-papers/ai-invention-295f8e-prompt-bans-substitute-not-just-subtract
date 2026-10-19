import sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "labeller")); sys.path.insert(0, str(ROOT / "tasks"))
from common import read_jsonl
from tasklib import run_trace, run_hidden_tests
from rules import runtime_label, ast_label
rows = [r for r in read_jsonl(ROOT / "data" / "raw_phaseA.jsonl") if r["condition"] == "forced:iddfs"][:3]
for r in rows:
    print("=" * 80); print(r["code"][:1500])
    tr = run_trace(r["code"], "t1")
    print("RUNTIME", runtime_label("t1", tr)[:2], json.dumps(runtime_label("t1", tr)[2])[:400])
    print("AST", ast_label("t1", r["code"])[:2])
    print("TESTS", run_hidden_tests(r["code"], "t1"))
    for p in tr.get("probes", []): print(p["name"], p["error"], "start_calls", p["start_calls"], "max_depth", p["max_depth"], "lists", [(l["front"], l["back"]) for l in p["lists"]][:3])
