#!/usr/bin/env python3
"""S0.4 SCREEN FILE (CPU) from the iteration-3 rows: exp17 data/labels.jsonl (RAND9001..9015 at alpha 1, RAND9001..9003
at alpha 2, NEUTRAL, ADD) and exp13 data/samples.jsonl (rand1-3 at alpha 1, twin; bf16 RTX 4090 rows).

Per task and alpha: per-direction off-default share over VALID attempts (catalogue-only: 'other', 'invalid' and
'disputed' are never off-default; invalid/disputed are excluded from the denominator), pass rate, escape at the N run
(no top-up): excess >= 0.20 over the twin AND pass >= 0.8 x the twin's; E_t = escaping / run; the push-landing
distribution = off-default catalogue labels of escaping directions weighted by their excess.
The frozen C1 set is written as-is; disagreement with the recomputation is reported, not acted on.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any

from cfg4 import (BENCH13, DEFAULT4, E13, E17, ESC_EXCESS, ESC_PASS_FRAC, MOVABLE, PATH_CATALOGUE, PATH_TASKS,
                  RESULTS_DIR, TASKS15, read_json, read_jsonl, sha256_file, write_json)
from describe import bench_dir

EXCLUDE = ("invalid", "disputed")


def catalogue(task: str) -> list[str]:
    if task in PATH_TASKS:
        return list(PATH_CATALOGUE[task])
    return [c["mode"] for c in read_json(bench_dir(task) / "spec.json")["catalogue"]]


def summarise(rows: list[dict[str, Any]], task: str) -> dict[str, Any]:
    cat = set(catalogue(task))
    d = DEFAULT4[task]
    valid = [r for r in rows if r["label"] not in EXCLUDE]
    off = [r for r in valid if r["label"] in cat and r["label"] != d]
    n = len(valid)
    return {"n_rows": len(rows), "n_valid": n, "off_default": len(off), "share": len(off) / n if n else None,
            "pass": sum(1 for r in rows if r.get("passed")) / len(rows) if rows else None,
            "labels": dict(Counter(r["label"] for r in rows)), "landing": dict(Counter(r["label"] for r in off))}


def escapes(arm: dict[str, Any], twin: dict[str, Any]) -> bool:
    if arm["share"] is None or twin["share"] is None:
        return False
    return arm["share"] - twin["share"] >= ESC_EXCESS - 1e-12 and arm["pass"] >= ESC_PASS_FRAC * twin["pass"] - 1e-12


def build_screen() -> dict[str, Any]:
    by: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in read_jsonl(E17 / "data" / "labels.jsonl"):
        by[("exp17", r["task"], r["arm"])].append(r) if False else by[(r["task"], "exp17:" + r["arm"])].append(r)
    for r in read_jsonl(E13 / "data" / "samples.jsonl"):
        if r["condition"] in ("rand1", "rand2", "rand3", "twin"):
            rr = {"label": r["label"], "passed": r["passed"] in (True, "True")}
            by[(r["task"], "exp13:" + r["condition"])].append(rr)
    out: dict[str, Any] = {"rule": {"excess": ESC_EXCESS, "pass_frac": ESC_PASS_FRAC,
                                    "share": "catalogue off-default over valid attempts"},
                           "sources": {"exp17_labels_sha256": sha256_file(E17 / "data" / "labels.jsonl"),
                                       "exp13_samples_sha256": sha256_file(E13 / "data" / "samples.jsonl")},
                           "tasks": {}}
    for t in TASKS15:
        tasks_arms = {a: rows for (tt, a), rows in by.items() if tt == t}
        res: dict[str, Any] = {"default": DEFAULT4[t], "catalogue": catalogue(t), "by_alpha": {}}
        twins = {}
        if "exp17:NEUTRAL" in tasks_arms:
            twins["exp17"] = summarise(tasks_arms["exp17:NEUTRAL"], t)
        if "exp13:twin" in tasks_arms:
            twins["exp13"] = summarise(tasks_arms["exp13:twin"], t)
        res["twins"] = twins
        dirs: dict[float, dict[str, Any]] = defaultdict(dict)
        for a, rows in tasks_arms.items():
            m = re.fullmatch(r"exp17:RAND(\d+)_a([\d.]+)", a)
            if m and "exp17" in twins:
                dirs[float(m.group(2))][f"exp17:{m.group(1)}"] = (summarise(rows, t), twins["exp17"])
            m = re.fullmatch(r"exp13:rand(\d)", a)
            if m and "exp13" in twins:
                dirs[1.0][f"exp13:rand{m.group(1)}"] = (summarise(rows, t), twins["exp13"])
        land: Counter = Counter()
        for alpha, dd in sorted(dirs.items()):
            per = {}
            n_esc = 0
            for k, (s, tw) in sorted(dd.items()):
                e = escapes(s, tw)
                n_esc += int(e)
                per[k] = {"share": s["share"], "pass": s["pass"], "n_valid": s["n_valid"],
                          "excess": None if s["share"] is None else s["share"] - tw["share"], "escape": e,
                          "landing": s["landing"]}
                if e:
                    exc = s["share"] - tw["share"]
                    tot = sum(s["landing"].values())
                    for lab, c in s["landing"].items():
                        land[lab] += exc * c / max(tot, 1)
            res["by_alpha"][str(alpha)] = {"n_directions": len(dd), "n_escape": n_esc,
                                           "E_t": n_esc / len(dd) if dd else None, "directions": per}
        tot = sum(land.values())
        res["push_landing"] = {k: v / tot for k, v in land.most_common()} if tot else {}
        lr = [k for k, _ in land.most_common()]
        res["runner_up_screen"] = lr[0] if lr else None
        res["second_screen"] = lr[1] if len(lr) > 1 else None
        res["movable_recomputed"] = any(v["n_escape"] > 0 for v in res["by_alpha"].values())
        out["tasks"][t] = res
    out["frozen_C1_set"] = list(MOVABLE)
    out["recomputed_movable"] = [t for t in TASKS15 if out["tasks"][t]["movable_recomputed"]]
    out["disagreement_with_frozen"] = sorted(set(out["frozen_C1_set"]) ^ set(out["recomputed_movable"]))
    out["hypothesis_numbers_check"] = {
        "T03_alpha1": out["tasks"]["T03"]["by_alpha"].get("1.0", {}).get("n_escape"),
        "T2_alpha1": out["tasks"]["T2"]["by_alpha"].get("1.0", {}).get("n_escape"),
        "T05_alpha2": out["tasks"]["T05"]["by_alpha"].get("2.0", {}).get("n_escape"),
        "T06_alpha2": out["tasks"]["T06"]["by_alpha"].get("2.0", {}).get("n_escape"),
        "expected": {"T03_alpha1": "7/15", "T2_alpha1": "3/15", "T05_alpha2": "2/3", "T06_alpha2": "1/3"}}
    write_json(RESULTS_DIR / "screen.json", out)
    return out


if __name__ == "__main__":
    s = build_screen()
    for t, v in s["tasks"].items():
        print(t, {a: (x["n_escape"], x["n_directions"]) for a, x in v["by_alpha"].items()}, v["push_landing"],
              v["runner_up_screen"], v["second_screen"])
    print(s["hypothesis_numbers_check"], s["disagreement_with_frozen"])
