#!/usr/bin/env python3
"""Decision profiles of candidate priority programs on synthetic states (restricted exec, rlimited process).
For item s and capacity cap: (1) accept set = residuals r for which the rule uses an opened bin of capacity s+r rather
than a new bin (state [s+r, cap]); (2) preferred residual among all opened residuals 0..cap-s-1 plus one new bin;
(3) order dependence: the same multiset reversed."""
import json, resource, sys, warnings
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
import numpy as np
import sandbox
warnings.simplefilter("ignore"); np.seterr(all="ignore")

def ranges(rs):
    out, start, prev = [], None, None
    for r in rs:
        if start is None: start = prev = r
        elif r == prev + 1: prev = r
        else: out.append((start, prev)); start = prev = r
    if start is not None: out.append((start, prev))
    return ",".join(f"{a}" if a == b else f"{a}-{b}" for a, b in out) or "none"

def profile(code):
    fn, et, msg = sandbox.compile_program(code)
    if fn is None: return {"error": et}
    res = {}
    for cap, s in [(100, 20), (100, 40), (100, 60), (150, 30), (150, 75)]:
        acc = []
        for r in range(0, cap - s):
            arr = np.array([s + r, cap])
            try:
                p = np.asarray(fn(s, arr.copy()), dtype=float); acc.append(r) if int(np.argmax(p)) == 0 else None
            except Exception: pass
        arr = np.array([s + r for r in range(0, cap - s)] + [cap])
        try:
            p = np.asarray(fn(s, arr.copy()), dtype=float); pick = int(arr[int(np.argmax(p))]) - s
            p2 = np.asarray(fn(s, arr[::-1].copy()), dtype=float); pick2 = int(arr[::-1][int(np.argmax(p2))]) - s
        except Exception as e: pick = pick2 = repr(e)[:40]
        # preference among accepted residuals only (no new bin): pairwise via full array of accepted
        if len(acc) >= 2:
            arr3 = np.array([s + r for r in acc])
            p3 = np.asarray(fn(s, arr3.copy()), dtype=float); best_acc = int(arr3[int(np.argmax(p3))]) - s
            order = [int(arr3[i]) - s for i in np.argsort(-p3, kind="stable")[:6]]
        else: best_acc, order = None, []
        res[f"cap{cap}_s{s}"] = {"accept_residuals": ranges(acc), "pick_all": pick, "pick_reversed": pick2,
                                 "best_among_accept": best_acc, "top6_accept_order": order}
    return res

blind = json.loads(Path(sys.argv[1]).read_text())
out = {b["oid"]: profile(b["code"]) for b in blind}
Path(sys.argv[2]).write_text(json.dumps(out, indent=1))
for oid, p in out.items():
    print(oid, " | ".join(f"{k}: acc[{v['accept_residuals']}] pick={v['pick_all']}/{v['pick_reversed']} bestacc={v['best_among_accept']} top={v['top6_accept_order']}" for k, v in p.items() if isinstance(v, dict) and k in ("cap100_s20", "cap100_s40", "cap150_s30")))
