#!/usr/bin/env python3
"""Final labels and the escape rule.

final label = labeller label when runtime and AST agree (or one is untraceable), else the blind-judge adjudication
(two judges agree, else majority of three), else 'disputed'. Labels outside the unit's FROZEN catalogue
(units/<u>/catalogue_frozen.json, written at gate stage (ii)) are mapped to 'other'.
share  = catalogue off-default labels / valid attempts (invalid and disputed excluded from the denominator)
pass   = passed / all attempts.
Escape (frozen exp22 rule): stage 1 (k 0-1, N = 10) passes when share >= twin + 0.20 and pass >= 0.8 x twin pass;
CONFIRMED when the pooled k 0-5 (N = 30) keeps excess >= 0.20 with one-sided exact binomial p < 0.05 against
p0 = (k_twin + 0.5) / (n_twin + 1), and pass >= 0.8 x twin pass.
"""

from __future__ import annotations

import time
from collections import Counter, defaultdict
from typing import Any

from loguru import logger
from scipy.stats import binomtest

from cfg5 import (ALPHAS, DATA_DIR, ESC_EXCESS, ESC_PASS_FRAC, K, LABELS, N_DIRS, RAW, UNITS_DIR, append_jsonl,
                  direction_seed, read_json, read_jsonl)

JUDGED = DATA_DIR / "judge_labels.jsonl"
EXCLUDE = ("invalid", "disputed")


def frozen_catalogue(u: str) -> list[str]:
    p = UNITS_DIR / u / "catalogue_frozen.json"
    if p.exists():
        return read_json(p)["catalogue"]
    from units_spec import catalogue
    return catalogue(u)


def default_of(u: str) -> str | None:
    p = UNITS_DIR / u / "default.json"
    return read_json(p)["default"] if p.exists() else None


def raw_index() -> dict[str, dict[str, Any]]:
    out = {}
    for r in read_jsonl(RAW):
        if r.get("engine_check"):
            continue
        k = f"{r['unit']}|{r['template']}|{r['arm']}|{r['slot']}|{r['model_tag']}"
        out[k] = {kk: r.get(kk) for kk in ("unit", "template", "arm", "slot", "model_tag", "family", "alpha",
                                            "direction_seed", "temperature", "utc", "finish_reason", "n_tokens",
                                            "prompt_sha256", "stage")}
    return out


def adjudicate_pending(units: list[str] | None = None, max_items: int = 400) -> int:
    from judge5 import adjudicate_many
    done = {r["key"] for r in read_jsonl(JUDGED)}
    items = []
    for l in read_jsonl(LABELS):
        if l.get("labeller_source") == "disagree" and l["key"] not in done and (units is None or l["unit"] in units):
            items.append((l["key"], l["unit"], l["code"]))
    items = items[:max_items]
    if not items:
        return 0
    res = adjudicate_many(items, "disagreement")
    append_jsonl(JUDGED, [{"key": r["id"], "label": r["label"], "how": r["how"], "judge_a": r["judge_a"],
                           "judge_b": r["judge_b"], "judge_c": r["judge_c"]} for r in res])
    logger.info(f"adjudicated {len(res)} disagreements")
    return len(res)


def final_rows(u: str | None = None) -> list[dict[str, Any]]:
    meta = raw_index()
    judged = {r["key"]: r for r in read_jsonl(JUDGED)}
    cats: dict[str, set[str]] = {}
    out = []
    for l in read_jsonl(LABELS):
        if u is not None and l["unit"] != u:
            continue
        if l.get("family") == "ASSOC":
            continue
        m = meta.get(l["key"])
        if m is None:
            continue
        lab = l.get("label")
        src = l.get("labeller_source")
        if lab is None:
            j = judged.get(l["key"])
            if j is not None and j.get("label") is not None:
                lab, src = j["label"], "judge_" + j["how"]
            else:
                lab, src = "disputed", ("judge_pending" if j is None else "judge_no_majority")
        cat = cats.setdefault(l["unit"], set(frozen_catalogue(l["unit"])))
        if lab not in cat and lab not in ("other", "invalid", "disputed"):
            lab = "other"
        out.append({**m, "key": l["key"], "label": lab, "label_source": src, "passed": bool(l.get("passed")),
                    "valid": bool(l.get("valid")), "runtime_label": l.get("runtime_label"),
                    "ast_label": l.get("ast_label"), "sublabel": l.get("sublabel"), "code_sha256": l.get("code_sha256")})
    return out


def summarise(rows: list[dict[str, Any]], cat: set[str], d: str | None) -> dict[str, Any]:
    valid = [r for r in rows if r["label"] not in EXCLUDE]
    off = [r for r in valid if r["label"] in cat and r["label"] != d]
    corr = [r for r in rows if r["passed"]]
    n = len(valid)
    return {"n_rows": len(rows), "n_valid": n, "off_default": len(off), "share": len(off) / n if n else None,
            "pass": len(corr) / len(rows) if rows else None, "n_correct": len(corr),
            "labels_attempted": dict(Counter(r["label"] for r in rows)),
            "labels_correct": dict(Counter(r["label"] for r in corr)),
            "landing_correct": dict(Counter(r["label"] for r in corr if r["label"] in cat and r["label"] != d))}


def twin_summary(rows: list[dict[str, Any]], cat: set[str], d: str | None) -> dict[str, Any]:
    tw = [r for r in rows if r["arm"] == "TWIN" and r["model_tag"] == "instruct" and r["slot"] in K["twin"]]
    return summarise(tw, cat, d)


def direction_table(u: str, rows: list[dict[str, Any]] | None = None, seeds: list[int] | None = None,
                    d: str | None = None) -> dict[str, Any]:
    rows = rows if rows is not None else final_rows(u)
    d = d or default_of(u)
    cat = set(frozen_catalogue(u))
    tw = twin_summary(rows, cat, d)
    k_tw, n_tw = tw["off_default"], tw["n_valid"]
    p0 = (k_tw + 0.5) / (n_tw + 1)
    seeds = seeds or [direction_seed(u, k) for k in range(N_DIRS)]
    by: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        if r["family"] == "ESC":
            by[r["arm"]].append(r)
    tab: dict[str, Any] = {"twin": tw, "p0": p0, "cells": {}}
    for a in ALPHAS:
        for s in seeds:
            arm = f"ESC_d{s}_a{a}"
            rr = by.get(arm, [])
            s1 = [r for r in rr if r["slot"] in K["esc1"]]
            s30 = [r for r in rr if r["slot"] in K["esc1"] + K["conf"]]
            S1 = summarise(s1, cat, d)
            S30 = summarise(s30, cat, d)
            st1 = (S1["share"] is not None and tw["share"] is not None and len(s1) >= 10 and
                   S1["share"] - tw["share"] >= ESC_EXCESS - 1e-12 and S1["pass"] >= ESC_PASS_FRAC * tw["pass"] - 1e-12)
            conf, pval = False, None
            if st1 and len(s30) >= 30 and S30["n_valid"] > 0:
                pval = float(binomtest(S30["off_default"], S30["n_valid"], p0, alternative="greater").pvalue)
                conf = (S30["share"] - tw["share"] >= ESC_EXCESS - 1e-12 and pval < 0.05 and
                        S30["pass"] >= ESC_PASS_FRAC * tw["pass"] - 1e-12)
            tab["cells"][arm] = {"seed": s, "alpha": a, "stage1": S1, "stage1_pass": st1, "n_rows": len(rr),
                                 "pooled30": S30 if len(s30) >= 30 else None, "confirmed": conf, "p": pval,
                                 "excess_stage1": None if S1["share"] is None else S1["share"] - (tw["share"] or 0),
                                 "excess_pooled": None if len(s30) < 30 or S30["share"] is None else
                                 S30["share"] - (tw["share"] or 0),
                                 "needs_confirmation": st1 and len(s30) < 30}
    E = {}
    for a in ALPHAS:
        cells = [c for c in tab["cells"].values() if c["alpha"] == a]
        E[str(a)] = sum(c["confirmed"] for c in cells) / len(seeds)
    tab["E_by_alpha"] = E
    tab["E_u"] = sum(E.values()) / len(E)
    tab["movable"] = tab["E_u"] > 0
    land = Counter()
    for c in tab["cells"].values():
        if c["confirmed"]:
            for lab, n in c["pooled30"]["landing_correct"].items():
                land[lab] += n
    tab["push_landing_composition"] = dict(land)
    tab["push_landing"] = land.most_common(1)[0][0] if land else None
    if land and len(land) > 1:
        top = land.most_common(2)
        if top[0][1] == top[1][1]:
            tab["push_landing_tie"] = [k for k, v in land.items() if v == top[0][1]]
    return tab


def pending_labels(u: str, families: tuple[str, ...]) -> int:
    lab = {l["key"] for l in read_jsonl(LABELS)}
    n = 0
    for r in read_jsonl(RAW):
        if r["unit"] == u and r["family"] in families and not r.get("engine_check"):
            k = f"{r['unit']}|{r['template']}|{r['arm']}|{r['slot']}|{r['model_tag']}"
            n += k not in lab
    return n


def confirm_cells(u: str, wait_s: float = 600) -> list[str]:
    t0 = time.time()
    while time.time() - t0 < wait_s:
        n = pending_labels(u, ("ESC", "TWIN"))
        if n == 0:
            break
        logger.info(f"waiting for {n} ESC/TWIN labels of {u}")
        time.sleep(10)
    adjudicate_pending([u])
    tab = direction_table(u)
    cells = [arm for arm, c in tab["cells"].items() if c["needs_confirmation"]]
    logger.info(f"{u}: stage-1 passers needing confirmation: {cells}")
    return cells
