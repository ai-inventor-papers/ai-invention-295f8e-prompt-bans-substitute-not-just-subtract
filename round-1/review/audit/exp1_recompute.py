"""Recompute Table 6 (every condition of the association experiment) from data/samples.jsonl."""
from collections import defaultdict
from common import ART, rows, summ

R = list(rows(ART / "experiment-1/src/data/samples.jsonl"))
groups = defaultdict(list)
for r in R:
    groups[(r["task"], r["condition"])].append(r)
for (t, c), sel in sorted(groups.items()):
    banned = None
    if c.startswith("ban:"):
        banned = c.split(":", 1)[1]
    print(t, c, summ(sel, banned))
print("stages:", sorted({r.get("stage") for r in R}))
