#!/usr/bin/env python3
"""Compact dump of Set B / B_TOP programs that need the manual pass: every judge disagreement, every NOVEL call and
every TOP program. Usage: dump_setB.py [max_lines]"""
import sys
from pathlib import Path

WS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WS))
from common.paths import sha256_text  # noqa: E402
from common.rows import iter_rows  # noqa: E402
from sections import s0c_novelty as N  # noqa: E402

maxl = int(sys.argv[1]) if len(sys.argv) > 1 else 22
sel = N.build_selection(list(iter_rows(include_exp12_extra=True)))
cache = N.load_cache()
n = 0
for i, it in enumerate(sel["B_TOP"] + sel["B"]):
    p = sha256_text(N.build_prompt(it["task"], it["code"]))
    r = {j: cache.get((j, it["item_id"], p), {}).get("parsed") or {} for j in "ABC"}
    fc, how = N.final_class({j: {"parsed": r[j]} for j in "ABC"})
    dis = r["A"].get("class") != r["B"].get("class")
    if not (dis or fc == "NOVEL_ALGORITHM" or it["set"] == "B_TOP"):
        continue
    n += 1
    lines = [l for l in it["code"].splitlines() if l.strip() and not l.strip().startswith("#")]
    print(f"##### [{i}] {it['item_id']} {it['task']} lab={it['label_fine']} exps={it['exps']} conds={it['conditions'][:2]} "
          f"m={[m.split('/')[-1][:10] for m in it['models']]} | A={r['A'].get('class')} B={r['B'].get('class')} "
          f"C={r['C'].get('class')} -> {fc} | closest A:{(r['A'].get('closest_known_algorithm') or '')[:40]} "
          f"B:{(r['B'].get('closest_known_algorithm') or '')[:40]}")
    print("\n".join(l[:110] for l in lines[:maxl]) + (f"\n   ... (+{len(lines) - maxl} lines)" if len(lines) > maxl else ""))
print("N_DUMPED", n, file=sys.stderr)
