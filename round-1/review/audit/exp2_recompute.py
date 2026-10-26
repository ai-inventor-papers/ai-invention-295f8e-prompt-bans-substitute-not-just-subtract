"""Recompute geometry experiment tables 11, 13 and 16 from data/samples_phase{A,C,D}.jsonl."""
from collections import defaultdict, Counter
from common import ART, rows, summ, truthy

base = ART / "experiment-2/src/data"
for ph in "ACD":
    R = list(rows(base / f"samples_phase{ph}.jsonl"))
    groups = defaultdict(list)
    for r in R:
        key = (r["task"], r["condition"], r.get("alpha"), r.get("arm"))
        groups[key].append(r)
    print("#### phase", ph, len(R))
    for k, sel in sorted(groups.items(), key=lambda x: str(x[0])):
        banned = None
        c = k[1]
        if c.startswith("ban:"):
            banned = c.split(":", 1)[1].split("+")
        s = summ(sel, banned)
        if ph == "A" and c.startswith("forced"):
            req = c.split(":")[-1]
            share = sum(1 for r in sel if r["label"] == req) / len(sel)
            s["share_as_asked"] = round(share, 3)
        print(k, s)
