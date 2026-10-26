"""Tabulate why DFS-labelled grid programs fail the hidden tests in the association experiment."""
from collections import Counter
from common import ART, rows, truthy

R = [r for r in rows(ART / "experiment-1/src/data/samples.jsonl") if r["task"] == "t1" and r["label"] == "dfs"]
fail = [r for r in R if not truthy(r["passed"])]
print("DFS t1 programs", len(R), "failed", len(fail))
print("test_error", Counter(str(r.get("test_error"))[:40] for r in fail).most_common(10))
print("fail_case", Counter(str(r.get("fail_case")).rsplit("_", 1)[0] for r in fail).most_common(10))
ex = [r for r in fail if str(r.get("test_error")).startswith("wrong")][:1]
for r in ex:
    print(r["condition"], r.get("test_error"), r.get("fail_case"))
    print(r["code"][:1500])
