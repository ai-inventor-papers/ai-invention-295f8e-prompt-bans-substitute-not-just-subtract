"""Re-run the live QA pass (tools/qa_second_pass_iter6.check) only for quotes that are missing from, or NO-MATCH in,
evidence/qa_second_pass_iter6.jsonl (e.g. a quote added after the main pass, or a URL corrected), and merge the results.
Usage: python -I tools/qa_rerun_iter6.py"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import EVID  # noqa: E402
from qa_second_pass_iter6 import check  # noqa: E402

qs = [json.loads(l) for l in (EVID / "quotes_iter6.jsonl").read_text().splitlines()]
path = EVID / "qa_second_pass_iter6.jsonl"
done = {r["qid"]: r for r in (json.loads(l) for l in path.read_text().splitlines())}
todo = [q for q in qs if q["qid"] not in done or done[q["qid"]]["second_pass"] != "MATCH" or done[q["qid"]]["url"] != q["url"]]
for q in todo:
    r = check(q)
    r["note"] = "re-run after URL correction or late addition"
    done[q["qid"]] = r
    print(q["qid"], r["second_pass"], r["match_count"], r["error"])
order = [q["qid"] for q in qs]
path.write_text("".join(json.dumps(done[k], ensure_ascii=False) + "\n" for k in order))
ok = sum(done[k]["second_pass"] == "MATCH" for k in order)
print(f"second pass after re-run: {ok}/{len(order)}")
