"""Recompute decoding experiment Tables 27 and 31 and the generate-then-select arm from results/samples.jsonl."""
import json
from collections import defaultdict, Counter
from common import ART, rows, summ

R = list(rows(ART / "experiment-6/src/results/samples.jsonl"))
print("arms", Counter(r["arm"] for r in R))
groups = defaultdict(list)
for r in R:
    d = r.get("decoding")
    if isinstance(d, str):
        try:
            d = json.loads(d.replace("'", '"'))
        except Exception:
            d = {"raw": d}
    key = (r["task"], r["arm"], r["condition"], d.get("T"), d.get("sampler"), str(r["key"]).split("|")[-1])
    groups[key].append(r)
for k, sel in sorted(groups.items(), key=lambda x: str(x[0])):
    s = summ(sel)
    print(k, "N", s["N"], "labels", s["labels"], "pass", s["pass"], "correct", s["correct_labels"], "hill_cc", s["hill_cc"])
