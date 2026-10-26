#!/usr/bin/env python3
"""Manual-read aid (arm-blind): for each anonymised representative, the gap it chooses from a full menu of open
bins (one per possible gap) plus an empty bin, per item size; and whether it opens a new bin against a single open
bin of each gap. Writes audit/profiles.json and prints a compact text summary per candidate."""
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import sandbox

def menu_choice(fn, item, cap):
    bins = np.array([item + g for g in range(0, cap - item)] + [cap])
    try:
        p = np.asarray(fn(item, bins.copy()), dtype=float)
        if p.shape != bins.shape: return "ERR"
        return int(bins[int(np.argmax(p))] - item)   # chosen gap (cap - item = new bin)
    except Exception:
        return "ERR"

def opens_new(fn, item, g, cap):
    bins = np.array([item + g, cap])
    try:
        p = np.asarray(fn(item, bins.copy()), dtype=float)
        return int(np.argmax(p)) == 1
    except Exception:
        return None

out = {}
sheet = json.loads((ROOT / "audit" / "blind_read_sheet.json").read_text())
for x in sheet:
    fn, et, msg = sandbox.compile_program(x["code"])
    prof = {}
    for cap in (100, 150):
        items = [5, 10, 20, 30, 40, 50, 60, 70, 80] if cap == 100 else [20, 35, 50, 65, 80, 95]
        prof[cap] = {"menu_gap": {it: menu_choice(fn, it, cap) for it in items},
                     "opens_new_vs_gap": {it: [g for g in range(0, cap - it, 1) if opens_new(fn, it, g, cap)] for it in items}}
    out[x["anon_id"]] = prof
    def rng(l):
        if not l: return "never"
        runs, s, p = [], l[0], l[0]
        for v in l[1:]:
            if v != p + 1: runs.append((s, p)); s = v
            p = v
        runs.append((s, p))
        return ",".join(f"{a}-{b}" if a != b else f"{a}" for a, b in runs)
    print(f"== {x['anon_id']}")
    for cap in (100, 150):
        mg = prof[cap]["menu_gap"]
        print(f"  cap{cap} menu gap chosen per item: " + " ".join(f"{it}:{g}" for it, g in mg.items()))
        print(f"  cap{cap} opens NEW bin when the only open bin leaves gap in: " + " | ".join(f"{it}:[{rng(v)}]" for it, v in prof[cap]["opens_new_vs_gap"].items()))
(ROOT / "audit" / "profiles.json").write_text(json.dumps(out, indent=1))

# second probe: base rule among large gaps. Menu = open bins leaving gaps in [lo, cap-item-1] (shuffled index order)
# plus one new bin; report the chosen gap (cap - item = the new bin).
rng = np.random.default_rng(0)
base = {}
for x in sheet:
    fn, et, msg = sandbox.compile_program(x["code"])
    row = {}
    for cap, items in ((100, [10, 20, 30, 40]), (150, [20, 35, 50, 65])):
        for it in items:
            gaps = list(range(it, cap - it))
            if not gaps:
                continue
            order = rng.permutation(len(gaps))
            bins = np.array([it + gaps[i] for i in order] + [cap])
            try:
                p = np.asarray(fn(it, bins.copy()), dtype=float)
                row[f"{cap}:{it}"] = int(bins[int(np.argmax(p))] - it)
            except Exception:
                row[f"{cap}:{it}"] = "ERR"
    base[x["anon_id"]] = row
    print("BASE", x["anon_id"], row)
(ROOT / "audit" / "profiles_base.json").write_text(json.dumps(base, indent=1))
