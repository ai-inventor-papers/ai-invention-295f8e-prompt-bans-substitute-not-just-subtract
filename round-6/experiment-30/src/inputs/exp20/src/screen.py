#!/usr/bin/env python3
"""STEP 6 - the screen file (CPU, literal rule, no top-up).

Sources: exp17 data/labels.jsonl (fixed random directions RAND9001-9015 at alpha 1 on T1/T2/T03 and RAND9001-9003 at
alpha 1 and 2 on T03/T04/T05/T06/T1/T2; twin = NEUTRAL, N = 100) and exp13 data/samples.jsonl (rand1-3 at alpha 1 on
12 tasks; twin = hf_twin, the HF-engine twin of the same engine as the rand arms).
Per task and alpha in {1, 2}, per direction: off-default share among parseable attempts and its excess over the twin,
pass ratio (pass rate / twin pass rate), escape = excess >= 0.20 and pass ratio >= 0.8 at the N run there, one-sided
exact binomial p of the off-default count against the twin's off-default rate (p0 = 0 handled literally: p = 0 if any
off-default program, else 1); E_t = number (and share) of escaping directions; push landing = modal non-default label
among the off-default attempts of escaping directions, weighted by the direction's excess.
Output: results/screen.json, canonical (sorted keys, floats rounded to 6 decimals) + results/screen.sha256.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from scipy.stats import binom

from cfg import DEFAULT, E13, E17, RESULTS_DIR, TASKS, canonical_json, read_jsonl, sha256_text

INVALID = {"invalid", "disputed", "unresolved", "no_code", None}


def _cell(rows: list[dict[str, Any]], default: str) -> dict[str, Any]:
    att = [r for r in rows if r.get("label") not in INVALID]
    off = [r for r in att if r["label"] != default]
    n = len(rows)
    return {"n": n, "n_attempted": len(att), "n_off": len(off), "off_share": len(off) / len(att) if att else None,
            "pass_rate": sum(bool(r.get("passed")) for r in rows) / n if n else None,
            "labels": dict(Counter(r["label"] for r in att))}


def binom_p(x: int, n: int, p0: float) -> float:
    if n == 0:
        return 1.0
    if p0 <= 0:
        return 0.0 if x > 0 else 1.0
    return float(binom.sf(x - 1, n, p0))


def build_screen() -> dict[str, Any]:
    src: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in read_jsonl(E17 / "data" / "labels.jsonl"):
        src[(r["task"], "exp17|" + r["arm"])].append(r)
    for r in read_jsonl(E13 / "data" / "samples.jsonl"):
        src[(r["task"], "exp13|" + str(r["condition"]))].append(r)
    out: dict[str, Any] = {"rule": __doc__.split("Per task")[1].strip(), "tasks": {}}
    for t in TASKS:
        d = DEFAULT[t]
        res: dict[str, Any] = {"default": d, "by_alpha": {}}
        twins = {"exp17": _cell(src.get((t, "exp17|NEUTRAL"), []), d),
                 "exp13": _cell(src.get((t, "exp13|hf_twin"), []), d)}
        res["twins"] = twins
        for alpha in ("1", "2"):
            dirs = []
            for (tt, arm), rows in sorted(src.items()):
                if tt != t:
                    continue
                srcn, a = arm.split("|", 1)
                if srcn == "exp17" and a.startswith("RAND") and a.endswith(f"_a{alpha}.0"):
                    name = a.split("_a")[0]
                elif srcn == "exp13" and alpha == "1" and a in ("rand1", "rand2", "rand3"):
                    name = a
                else:
                    continue
                tw = twins[srcn]
                if not tw["n"] or tw["off_share"] is None:
                    continue
                c = _cell(rows, d)
                if c["off_share"] is None:
                    continue
                exc = c["off_share"] - tw["off_share"]
                pr = c["pass_rate"] / tw["pass_rate"] if tw["pass_rate"] else None
                esc = bool(exc >= 0.20 and pr is not None and pr >= 0.8)
                dirs.append({"source": srcn, "direction": name, **c, "twin_off_share": tw["off_share"],
                             "excess": exc, "pass_ratio": pr, "escape": esc,
                             "binom_p": binom_p(c["n_off"], c["n_attempted"], tw["off_share"])})
            land: Counter = Counter()
            for x in dirs:
                if x["escape"]:
                    offs = {k: v for k, v in x["labels"].items() if k != d}
                    tot = sum(offs.values())
                    for k, v in offs.items():
                        land[k] += x["excess"] * v / tot if tot else 0.0
            n_esc = sum(x["escape"] for x in dirs)
            res["by_alpha"][alpha] = {"n_directions": len(dirs), "directions": dirs, "E_t": n_esc,
                                      "E_t_share": n_esc / len(dirs) if dirs else None,
                                      "landing_weighted": dict(land),
                                      "modal_landing": max(land, key=land.get) if land else None}
        out["tasks"][t] = res
    out["frozen_event_set"] = list(TASKS)
    out["note"] = "disagreements between this screen and the frozen event set are reported, not acted on"
    return out


def write_screen() -> str:
    s = canonical_json(build_screen())
    (RESULTS_DIR / "screen.json").write_text(s)
    h = sha256_text(s)
    (RESULTS_DIR / "screen.sha256").write_text(h + "\n")
    return h


if __name__ == "__main__":
    print(write_screen())
