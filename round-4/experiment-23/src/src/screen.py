#!/usr/bin/env python3
"""STEP 1 (screen file, shared protocol): recompute the iteration-3 Qwen3-8B push screen from exp17
data/labels.jsonl (random-direction arms RAND90xx at alpha 1 and 2 vs NEUTRAL) and exp13 data/samples.jsonl
(rand1-3 at alpha 1 vs twin), with this artifact's escape rule at N as run there (no top-up): a direction-alpha
escapes iff off-default share - p0 >= 0.20, pass >= 0.8 x twin pass, and P(X >= k | N, max(p0, 0.01)) < 0.05.
Writes results/screen.json (+ sha256) and the T5 reproduction check against the hypothesis's stated counts."""

from __future__ import annotations

import collections
import sys
from pathlib import Path
from typing import Any

from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (BINOM_ALPHA, E13, E17, ESCAPE_EXCESS, ESCAPE_PASS_FRAC, P0_FLOOR, QWEN_DEFAULT, RESULTS_DIR,
                 read_jsonl, sha256_file, write_json)

STATED = {"T03": {"a1": (7, 15)}, "T2": {"a1": (3, 15)}, "T05": {"a1": (0, 3), "a2": (2, 3)}, "T06": {"a2": (1, 3)},
          "T04": {"all": (0, 6)}}
C1_EVENTS = ["T03", "T05", "T06", "T10", "T1", "T2"]
NOT_OFF = ("invalid", "disputed")


def escape_cell(rr: list[dict[str, Any]], D: str, p0: float, pt: float) -> dict[str, Any]:
    n = len(rr)
    k = sum(1 for r in rr if r["label"] not in (D,) + NOT_OFF)
    pr = sum(1 for r in rr if str(r.get("passed")) in ("True", "true", "1") or r.get("passed") is True) / max(n, 1)
    sh = k / max(n, 1)
    pb = float(stats.binom.sf(k - 1, n, max(p0, P0_FLOOR))) if n else 1.0
    esc = n > 0 and sh - p0 >= ESCAPE_EXCESS and pr >= ESCAPE_PASS_FRAC * pt and pb < BINOM_ALPHA
    land = collections.Counter(r["label"] for r in rr if r["label"] not in (D,) + NOT_OFF)
    return {"n": n, "k_off": k, "off_share": sh, "excess": sh - p0, "pass": pr, "binom_p": pb, "escape": bool(esc),
            "landings": dict(land)}


def _passed(r: dict[str, Any]) -> bool:
    return r.get("passed") is True or str(r.get("passed")) == "True"


def screen() -> dict[str, Any]:
    out: dict[str, Any] = {"rule": {"excess": ESCAPE_EXCESS, "pass_frac": ESCAPE_PASS_FRAC, "binom_alpha": BINOM_ALPHA,
                                    "p0_floor": P0_FLOOR, "top_up": False}, "tasks": {}}
    e17 = read_jsonl(E17 / "data" / "labels.jsonl")
    e13 = read_jsonl(E13 / "data" / "samples.jsonl")
    tasks = sorted({r["task"] for r in e17} | {r["task"] for r in e13})
    for t in tasks:
        D = QWEN_DEFAULT.get(t)
        if D is None:
            continue
        rec: dict[str, Any] = {"D": D, "sources": {}}
        # exp17 (RAND arms)
        tw = [r for r in e17 if r["task"] == t and r["arm"] == "NEUTRAL"]
        if tw:
            p0 = sum(1 for r in tw if r["label"] not in (D,) + NOT_OFF) / len(tw)
            pt = sum(1 for r in tw if _passed(r)) / len(tw)
            cells = {}
            arms = sorted({r["arm"] for r in e17 if r["task"] == t and r["arm"].startswith("RAND")})
            for a in arms:
                cells[a] = escape_cell([r for r in e17 if r["task"] == t and r["arm"] == a], D, p0, pt)
            rec["sources"]["exp17"] = {"p0": p0, "twin_pass": pt, "n_twin": len(tw), "cells": cells}
        # exp13 (rand1-3, alpha 1)
        tw = [r for r in e13 if r["task"] == t and r.get("condition") == "twin"]
        if tw:
            p0 = sum(1 for r in tw if r["label"] not in (D,) + NOT_OFF) / len(tw)
            pt = sum(1 for r in tw if _passed(r)) / len(tw)
            cells = {}
            for a in ("rand1", "rand2", "rand3"):
                rr = [r for r in e13 if r["task"] == t and r.get("condition") == a]
                if rr:
                    cells[f"{a}_a1.0"] = escape_cell(rr, D, p0, pt)
            rec["sources"]["exp13"] = {"p0": p0, "twin_pass": pt, "n_twin": len(tw), "cells": cells}
        E: dict[str, list[int]] = {"a1": [0, 0], "a2": [0, 0]}
        land = collections.Counter()
        for src in rec["sources"].values():
            for a, c in src["cells"].items():
                key = "a2" if a.endswith("a2.0") else "a1"
                E[key][1] += 1
                E[key][0] += int(c["escape"])
                if c["escape"]:
                    for m, k in c["landings"].items():
                        land[m] += c["excess"] * k
        rec["escapes"] = {k: {"n_escape": v[0], "n_run": v[1]} for k, v in E.items()}
        rec["E_t_1"] = E["a1"][0] / E["a1"][1] if E["a1"][1] else None
        rec["E_t_2"] = E["a2"][0] / E["a2"][1] if E["a2"][1] else None
        rec["E_t"] = max(x for x in (rec["E_t_1"], rec["E_t_2"]) if x is not None) if (E["a1"][1] or E["a2"][1]) else None
        rec["movable"] = bool(rec["E_t"]) if rec["E_t"] is not None else None
        tot = sum(land.values())
        rec["push_landing"] = {m: v / tot for m, v in land.items()} if tot else {}
        out["tasks"][t] = rec
    # T5 reproduction of the hypothesis's stated counts (exp17 source)
    chk = {}
    for t, st in STATED.items():
        cells = out["tasks"].get(t, {}).get("sources", {}).get("exp17", {}).get("cells", {})
        for key, (k, n) in st.items():
            sel = [c for a, c in cells.items() if key == "all" or a.endswith("a1.0" if key == "a1" else "a2.0")]
            got = (sum(int(c["escape"]) for c in sel), len(sel))
            chk[f"{t}_{key}"] = {"stated": [k, n], "recomputed": list(got), "match": got == (k, n)}
    out["t5_reproduction"] = chk
    out["c1_event_set_frozen"] = C1_EVENTS
    out["movable_tasks_recomputed"] = sorted(t for t, v in out["tasks"].items() if v.get("movable"))
    return out


def main() -> None:
    res = screen()
    p = RESULTS_DIR / "screen.json"
    write_json(p, res)
    (RESULTS_DIR / "screen.json.sha256").write_text(sha256_file(p) + "\n")
    print({k: v["match"] for k, v in res["t5_reproduction"].items()}, res["movable_tasks_recomputed"])


if __name__ == "__main__":
    main()
