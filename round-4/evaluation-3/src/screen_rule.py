#!/usr/bin/env python3
"""Push-movability screen rule (stdlib only), so parallel artifacts can recompute screen.json byte for byte.

Input JSON (path as argv[1], or stdin):
  {"direction_rows": [{"task", "alpha", "direction_id", "engine", "n", "n_attempted", "n_default", "n_passed",
                       "twin_n", "twin_n_attempted", "twin_n_default", "twin_n_passed",
                       "offdef_cat_counts": {label: count}}, ...],
   "ban_avoidance": {task: catalogue-only modal-ban avoidance},
   "tasks": [...], "c1_event_set": [...], "source_sha256": {cite: sha256}}
Output: canonical screen-core JSON on stdout (or argv[2]); its sha256 on stderr.

Rule (Claim 3a screen): ESCAPE(d, t, a) iff offdef(d) - offdef(twin) >= 0.20 and pass(d) >= 0.8 x pass(twin),
with offdef = 1 - n_default / n_attempted and pass = n_passed / n. E_t(a) = escaping / run at alpha a;
MOVABLE(t) = 1 iff E_t(a) > 0 for some a <= 2. Push landing over escaping directions:
w_X = sum_d e_d * share_d(X | off-default catalogue attempts) / sum_d e_d, e_d = offdef(d) - offdef(twin);
'other' is excluded. Screen prediction: movable implies catalogue-only ban avoidance >= 0.5.
"""

from __future__ import annotations

import hashlib
import json
import sys

ESCAPE_MARGIN = 0.20
PASS_RATIO = 0.8
ALPHAS = (1.0, 2.0)
RULE_TEXT = "movable(t) implies catalogue-only modal-ban avoidance(t) >= 0.5"
ESCAPE_TEXT = ("escape(d,t,a): offdef(d)-offdef(twin) >= 0.20 and pass(d) >= 0.8*pass(twin); "
               "offdef = 1 - n_default/n_attempted; pass = n_passed/n (no-code rows fail)")


def _r(x):
    if isinstance(x, float):
        return round(x, 4)
    if isinstance(x, dict):
        return {k: _r(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_r(v) for v in x]
    return x


def canonical_bytes(obj) -> bytes:
    return (json.dumps(_r(obj), sort_keys=True, ensure_ascii=True, separators=(",", ":")) + "\n").encode("ascii")


def offdef(n_default: int, n_attempted: int):
    return 1.0 - n_default / n_attempted if n_attempted else None


def escape_of(row: dict):
    od = offdef(row["n_default"], row["n_attempted"])
    tw = offdef(row["twin_n_default"], row["twin_n_attempted"])
    if od is None or tw is None or not row["n"] or not row["twin_n"]:
        return False, 0.0
    p, pt = row["n_passed"] / row["n"], row["twin_n_passed"] / row["twin_n"]
    excess = od - tw
    # 1e-9 guards float noise at the exact 0.20 boundary (e.g. 0.30 - 0.10)
    return bool(excess >= ESCAPE_MARGIN - 1e-9 and p >= PASS_RATIO * pt - 1e-12), excess


def build_core(inp: dict) -> dict:
    tasks = sorted(inp["tasks"])
    per = {}
    for t in tasks:
        rows = [r for r in inp["direction_rows"] if r["task"] == t]
        rec = {}
        movable = 0
        num: dict = {}
        den = 0.0
        for a in ALPHAS:
            ra = [r for r in rows if float(r["alpha"]) == a]
            n_esc = 0
            for r in ra:
                esc, e = escape_of(r)
                if esc:
                    n_esc += 1
                    cnt = {k: v for k, v in r["offdef_cat_counts"].items() if k != "other" and v > 0}
                    tot = sum(cnt.values())
                    if tot > 0:
                        den += e
                        for k, v in cnt.items():
                            num[k] = num.get(k, 0.0) + e * v / tot
            key = f"alpha_{int(a)}"
            rec[key] = {"n_directions_run": len(ra), "n_escape": n_esc,
                        "E_t": (n_esc / len(ra)) if ra else None}
            if ra and n_esc > 0:
                movable = 1
        land = {k: v / den for k, v in sorted(num.items())} if den > 0 else {}
        top1 = sorted(land.items(), key=lambda kv: (-round(kv[1], 12), kv[0]))[0][0] if land else None
        av = inp["ban_avoidance"].get(t)
        rec.update({"movable": movable, "push_landing": land, "push_top1": top1, "cat_only_ban_avoidance": av,
                    "ban_avoidance_ge_0_5": (None if av is None else bool(av >= 0.5))})
        per[t] = rec
    return {"screen_version": "iter4-step0", "tasks": per, "c1_event_set": sorted(inp["c1_event_set"]),
            "screen_rule": RULE_TEXT, "escape_rule": ESCAPE_TEXT,
            "movable_tasks": sorted(t for t in tasks if per[t]["movable"]),
            "source_sha256": dict(sorted(inp["source_sha256"].items()))}


def main() -> None:
    raw = open(sys.argv[1]).read() if len(sys.argv) > 1 and sys.argv[1] != "-" else sys.stdin.read()
    core = build_core(json.loads(raw))
    b = canonical_bytes(core)
    if len(sys.argv) > 2:
        open(sys.argv[2], "wb").write(b)
    else:
        sys.stdout.write(b.decode("ascii"))
    sys.stderr.write(hashlib.sha256(b).hexdigest() + "\n")


if __name__ == "__main__":
    main()
