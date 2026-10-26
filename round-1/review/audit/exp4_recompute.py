"""Recompute decommitment experiment Table 22 label counts and pass rates from data/samples.jsonl."""
from collections import defaultdict
from common import ART, rows, summ

R = list(rows(ART / "experiment-4/src/data/samples.jsonl"))
groups = defaultdict(list)
for r in R:
    groups[(r["task"], r["condition"], r.get("engine"))].append(r)
for k, sel in sorted(groups.items()):
    c = k[1]
    banned = None
    if c.startswith("ban:"):
        banned = c.split(":", 1)[1]
    s = summ(sel, banned)
    print(k, {x: s[x] for x in ("N", "pass", "correct_labels", "hill_cc")}, s.get("labels") if c.startswith(("ban", "succ")) else "")
