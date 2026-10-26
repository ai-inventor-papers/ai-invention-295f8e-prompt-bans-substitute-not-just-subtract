"""Recompute instruction tuning experiment Table 24 (vLLM arms) and steering arms (Table 26) from runs/samples.jsonl."""
from collections import defaultdict, Counter
from common import ART, rows, summ, truthy, hill

R = list(rows(ART / "experiment-5/src/runs/samples.jsonl"))
print("engines", Counter(r.get("engine") for r in R))
groups = defaultdict(list)
for r in R:
    groups[(r["task"], r.get("arm"), r["condition"], r.get("engine"), str(r.get("steer"))[:60])].append(r)
for k, sel in sorted(groups.items(), key=lambda x: str(x[0])):
    n = len(sel)
    parse = sum(1 for r in sel if truthy(r.get("parse_ok"))) / n
    s = summ(sel)
    parseable = [r for r in sel if truthy(r.get("parse_ok"))]
    hall = hill(Counter(str(r.get("label")) for r in parseable if r.get("label") not in (None, "None")))
    print(k, "N", n, "parse", round(parse, 2), "pass", s["pass"], "correct", s["correct_labels"], "hill_cc", s["hill_cc"], "hill_all", round(hall, 2))
