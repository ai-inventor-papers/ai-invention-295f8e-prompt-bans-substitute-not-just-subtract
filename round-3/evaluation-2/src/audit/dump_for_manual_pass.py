#!/usr/bin/env python3
"""Print selected programs with their blind-judge outputs, for the executor's manual pass (audit/manual_pass.jsonl)."""
import json
import sys
from collections import Counter
from pathlib import Path

WS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WS))
from common.paths import read_jsonl, sha256_text  # noqa: E402
from common.rows import iter_rows  # noqa: E402
from sections import s0c_novelty as N  # noqa: E402

which = sys.argv[1] if len(sys.argv) > 1 else "A"
lo, hi = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (0, 10**9)
rows = list(iter_rows(include_exp12_extra=True))
sel = N.build_selection(rows)
cache = N.load_cache()
items = sel["A"] if which == "A" else sel["B_TOP"] + sel["B"]
cls = Counter()
for i, it in enumerate(items):
    p = sha256_text(N.build_prompt(it["task"], it["code"]))
    r = {j: cache.get((j, it["item_id"], p), {}).get("parsed") or {} for j in "ABC"}
    fc, how = N.final_class({j: {"parsed": r[j]} for j in "ABC"})
    cls[fc] += 1
    dis = r["A"].get("class") != r["B"].get("class")
    if which != "A" and not dis:
        continue
    if not (lo <= i < hi):
        continue
    code = "\n".join(l for l in it["code"].splitlines() if l.strip())
    print(f"##### [{i}] {it['item_id']} task={it['task']} label={it['label_fine']} passed={it['passed']} "
          f"exps={it['exps']} conds={it['conditions'][:4]} models={[m.split('/')[-1] for m in it['models']]}")
    for j in "ABC":
        if r[j]:
            print(f"  {j}: {r[j].get('class')} | {r[j].get('catalogue_match')} | {r[j].get('closest_known_algorithm')} | "
                  f"{(r[j].get('mechanism_summary') or '')[:160]}")
    print(f"  FINAL: {fc} ({how})")
    print(code)
print("CLASS COUNTS", dict(cls), file=sys.stderr)
