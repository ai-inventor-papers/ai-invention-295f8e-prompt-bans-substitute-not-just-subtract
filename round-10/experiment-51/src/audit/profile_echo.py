#!/usr/bin/env python3
"""Manual-read aid 2 (arm-blind): echo/multiple probes. ECHO: open bins leaving gaps {2, item} (+ new bin): BF/ab pick 2,
an echo rule picks item. MULT: gaps {item+1, item+2, 2*item} (+ new bin): best fit among large gaps picks item+1, a
multiple-of-item rule picks 2*item. Writes audit/profiles_echo.json."""
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import sandbox
def pick(fn, item, gaps, cap):
    bins = np.array([item + g for g in gaps] + [cap])
    try:
        p = np.asarray(fn(item, bins.copy()), dtype=float)
        return int(bins[int(np.argmax(p))] - item)
    except Exception:
        return "ERR"
out = {}
for x in json.loads((ROOT / "audit" / "blind_read_sheet.json").read_text()):
    fn, _, _ = sandbox.compile_program(x["code"])
    row = {"echo": {}, "mult": {}}
    for cap, items in ((100, [5, 10, 15, 20, 30]), (150, [20, 35, 45])):
        for it in items:
            row["echo"][f"{cap}:{it}"] = pick(fn, it, [2, it], cap)
            if 2 * it < cap - it:
                row["mult"][f"{cap}:{it}"] = pick(fn, it, [it + 1, it + 2, 2 * it], cap)
    out[x["anon_id"]] = row
    e = sum(1 for k, v in row["echo"].items() if v == int(k.split(":")[1]))
    m = sum(1 for k, v in row["mult"].items() if v == 2 * int(k.split(":")[1]))
    print(x["anon_id"], f"echo-over-tight {e}/{len(row['echo'])}", f"multiple-over-tighter {m}/{len(row['mult'])}", row["echo"], row["mult"])
(ROOT / "audit" / "profiles_echo.json").write_text(json.dumps(out, indent=1))
