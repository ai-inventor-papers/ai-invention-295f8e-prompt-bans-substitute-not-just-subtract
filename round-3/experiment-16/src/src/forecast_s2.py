#!/usr/bin/env python3
"""S2 frozen forecast objects (CPU; the signature-prefill tie-break by log-probability runs on GPU in S3.2).

2.1 DISTINCTIVE N-GRAM (frozen protocol rule): candidates = token n-grams (n = 1..6) of resp(code) present in >= 0.8
    of the default's baseline programs; collateral(A') = share of A''s forced programs containing it; choose
    argmin_c max_A' collateral(A'); ties -> smaller n -> higher baseline frequency -> lexicographically smallest ids.
2.2 SIGNATURE PREFILL: baseline resp ids cut after the n-gram's first occurrence; the most frequent exact prefix if it
    covers >= 5 programs (ties -> shorter), else the highest mean teacher-forced log-prob under the 5 twin_A prompts.
    NEUTRAL PREFILL: '```python\\ndef ' + signature + ':\\n'.
2.3 PATH OPENING-VETO VARIANT: the import line's tokens when the rule n-gram is not inside that line.
2.4 ASSOCIATE (modal mapped association answer) and PROXIMITY (median identifier-normalised Zhang-Shasha AST edit
    distance between correct forced programs of each survivor and the default's baseline programs, 20 x 20 pairs,
    seed 0).
"""

from __future__ import annotations

import ast
import collections
import keyword
import multiprocessing as mp
import random
import re
from concurrent.futures import ProcessPoolExecutor
from typing import Any

import numpy as np
from loguru import logger

from cfg import (BENCH, E7, E8, PATH_DEFAULT, PATH_TASKS, PRED_DIR, STAGE_A, TASK_DIR, THRESHOLDS, default_of,
                 read_json, read_jsonl, resp_ids, write_json)

MAX_N = 6


# ------------------------------------------------------------------------------------------------ sets
def catalogue(task: str) -> list[str]:
    if task == "t1":
        return ["bfs", "dfs", "bibfs", "iddfs", "astar_gbfs", "dijkstra"]
    if task == "t2":
        return ["dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"]
    return [c["mode"] for c in read_json(BENCH / TASK_DIR[task] / "spec.json")["catalogue"]]


def baseline_codes(task: str) -> tuple[list[str], str]:
    if task in PATH_TASKS:
        rows = read_jsonl(E8 / "data" / "samples.jsonl")
        codes = [r["code"] for r in rows if r["task"] == task and r["condition"] == "b"
                 and r["label"] == PATH_DEFAULT[task] and r.get("code")]
        return codes, "exp8 data/samples.jsonl arm b, label == default"
    rows = read_jsonl(BENCH / TASK_DIR[task] / "pilot_rows.jsonl")
    return [r["code"] for r in rows if r["label"] == default_of(task) and r.get("code")], "bench pilot_rows, label == default"


def forced_sets(task: str) -> tuple[dict[str, list[dict]], str]:
    D = default_of(task)
    out: dict[str, list[dict]] = {m: [] for m in catalogue(task) if m != D}
    if task in PATH_TASKS:
        for r in read_jsonl(E7 / "data" / "forced_labelled.jsonl"):
            if r["task"] == task and r.get("j") in out and r["label"] == r["j"] and r.get("code"):
                out[r["j"]].append({"code": r["code"], "passed": bool(r.get("passed"))})
        return out, "exp7 data/forced_labelled.jsonl (unscrubbed), label == forced mode"
    for r in read_jsonl(BENCH / TASK_DIR[task] / "forced_programs.jsonl"):
        m = r.get("forced_mode")
        if m in out and r["label"] == m and r.get("code"):
            out[m].append({"code": r["code"], "passed": bool(r.get("passed"))})
    return out, "bench forced_programs.jsonl code field (unscrubbed: identical to exp11 samples_forced extract)"


def ngrams_of(ids: list[int], max_n: int = MAX_N) -> set[tuple[int, ...]]:
    s = set()
    L = len(ids)
    for n in range(1, max_n + 1):
        for i in range(L - n + 1):
            s.add(tuple(ids[i:i + n]))
    return s


def first_occurrence(ids: list[int], g: tuple[int, ...]) -> int | None:
    n = len(g)
    for i in range(len(ids) - n + 1):
        if tuple(ids[i:i + n]) == g:
            return i
    return None


def token_class(text: str) -> str:
    s = text.strip()
    if re.search(r"\b(import|from)\b", text):
        return "import"
    if s and all(not ch.isalnum() and ch != "_" for ch in s):
        return "structural"
    words = re.findall(r"[A-Za-z_][A-Za-z_0-9]*", text)
    if "(" in text or "." in text and words:
        return "API call"
    if words and all(keyword.iskeyword(w) for w in words):
        return "keyword"
    import builtins

    if words and any(w in dir(builtins) for w in words):
        return "API call"
    return "identifier" if words else "structural"


def choose_ngram(base_ids: list[list[int]], forced_ids: dict[str, list[list[int]]],
                 exclude: set[tuple[int, ...]] | None = None) -> dict[str, Any]:
    """Pure rule (unit-tested on synthetic data in tests/test_cpu.py). exclude: n-grams already masked (screen)."""
    nb = len(base_ids)
    pres: collections.Counter = collections.Counter()
    for ids in base_ids:
        pres.update(ngrams_of(ids))
    cands = [g for g, c in pres.items() if c >= THRESHOLDS["ngram_presence"] * nb and not (exclude and g in exclude)]
    if not cands:
        return {"defined": False, "reason": "no n-gram reaches 0.8 presence", "n_candidates": 0}
    fsets = {m: [ngrams_of(ids) for ids in lst] for m, lst in forced_ids.items()}
    best = None
    for g in cands:
        col = {m: (float(np.mean([g in s for s in ss])) if ss else 0.0) for m, ss in fsets.items()}
        mx = max(col.values()) if col else 0.0
        key = (mx, len(g), -pres[g], g)
        if best is None or key < best[0]:
            best = (key, g, col)
    (mx, n, negf, g), g, col = best
    firsts = [first_occurrence(ids, g) for ids in base_ids]
    firsts = [f for f in firsts if f is not None]
    return {"defined": True, "ids": list(g), "n": n, "baseline_frequency": -negf / nb, "max_collateral": mx,
            "collateral": col, "co_vetoed": sorted(m for m, c in col.items() if c >= THRESHOLDS["coveto"]),
            "median_first_occurrence": float(np.median(firsts)) if firsts else None,
            "n_candidates": len(cands), "n_baseline": nb,
            "n_forced": {m: len(v) for m, v in forced_ids.items()}}


def choose_prefill(base_ids: list[list[int]], g: list[int]) -> dict[str, Any]:
    prefixes = []
    for ids in base_ids:
        f = first_occurrence(ids, tuple(g))
        if f is not None:
            prefixes.append(tuple(ids[:f + len(g)]))
    cnt = collections.Counter(prefixes)
    if not cnt:
        return {"rule": "none", "ids": None}
    top = max(cnt.values())
    if top >= 5:
        best = sorted([p for p, c in cnt.items() if c == top], key=lambda p: (len(p), p))[0]
        return {"rule": "most_frequent_exact_prefix", "ids": list(best), "coverage": top, "n_prefixes": len(cnt)}
    return {"rule": "needs_lp_scoring", "candidates": [list(p) for p in cnt], "coverage": top, "n_prefixes": len(cnt)}


# ------------------------------------------------------------------------------------------------ proximity
def _zss_tree(code: str):
    from zss import Node

    tree = ast.parse(code)

    def lab(n: ast.AST) -> str:
        t = type(n).__name__
        if isinstance(n, ast.Constant):
            return f"Constant:{type(n.value).__name__}"
        if isinstance(n, ast.Attribute):
            return f"Attribute:{n.attr}"  # API surface kept; user identifiers (Name/arg/def names) normalised
        if isinstance(n, (ast.BinOp, ast.UnaryOp, ast.BoolOp)):
            return f"{t}:{type(n.op).__name__}"
        if isinstance(n, ast.Compare):
            return "Compare:" + ",".join(type(o).__name__ for o in n.ops)
        if isinstance(n, ast.AugAssign):
            return f"AugAssign:{type(n.op).__name__}"
        return t

    def build(n: ast.AST):
        node = Node(lab(n))
        for c in ast.iter_child_nodes(n):
            if isinstance(c, (ast.Load, ast.Store, ast.Del, ast.operator, ast.cmpop, ast.boolop, ast.unaryop)):
                continue
            node.addkid(build(c))
        return node

    return build(tree)


def _zss_pair(args: tuple[str, str]) -> float | None:
    from zss import simple_distance

    a, b = args
    try:
        return float(simple_distance(_zss_tree(a), _zss_tree(b)))
    except (SyntaxError, ValueError, RecursionError):
        return None


def proximity(task: str, base: list[str], forced: dict[str, list[dict]], pool: ProcessPoolExecutor) -> dict[str, Any]:
    rng = random.Random(0)
    uniq_base = list(dict.fromkeys(base))
    out = {}
    for m, lst in forced.items():
        corr = [r["code"] for r in lst if r["passed"]]
        if not corr:
            out[m] = {"median": None, "n_pairs": 0}
            continue
        A = [rng.choice(uniq_base) for _ in range(20)] if len(uniq_base) < 20 else rng.sample(uniq_base, 20)
        Bs = [rng.choice(corr) for _ in range(20)] if len(corr) < 20 else rng.sample(corr, 20)
        pairs = [(a, b) for a in A for b in Bs]
        uniq = list(dict.fromkeys(pairs))
        dmap = dict(zip(uniq, pool.map(_zss_pair, uniq, chunksize=8)))
        d = [dmap[p] for p in pairs if dmap[p] is not None]
        out[m] = {"median": float(np.median(d)) if d else None, "n_pairs": len(d), "n_correct_forced": len(corr),
                  "n_unique_baseline": len(uniq_base)}
    valid = {m: v["median"] for m, v in out.items() if v["median"] is not None}
    return {"distances": out, "proximity": min(valid, key=lambda m: (valid[m], m)) if valid else None}


def associate(task: str) -> dict[str, Any]:
    D = default_of(task)
    rows = [r for r in read_jsonl(BENCH / TASK_DIR[task] / "association.jsonl") if r["X"] == D]
    c = collections.Counter(r["mapped"] for r in rows if r.get("category") == "survivor" and r["mapped"] != D)
    allc = collections.Counter(r["mapped"] for r in rows)
    return {"associate": c.most_common(1)[0][0] if c else None, "counts_survivor": dict(c), "counts_all": dict(allc),
            "n": len(rows)}


# ------------------------------------------------------------------------------------------------ stage
def stage_s2(tok: Any) -> dict[str, Any]:
    ngrams, prefills, assoc = {}, {}, {}
    pool = ProcessPoolExecutor(max_workers=4, mp_context=mp.get_context("spawn"))
    try:
        for t in STAGE_A + list(PATH_TASKS):
            base, bsrc = baseline_codes(t)
            forced, fsrc = forced_sets(t)
            bids = [resp_ids(tok, c) for c in base]
            fids = {m: [resp_ids(tok, r["code"]) for r in lst] for m, lst in forced.items()}
            rec = choose_ngram(bids, fids)
            rec.update({"task": t, "default": default_of(t), "baseline_source": bsrc, "forced_source": fsrc})
            if rec["defined"]:
                rec["text"] = tok.decode(rec["ids"])
                rec["token_class"] = token_class(rec["text"])
                rec["tokens"] = [tok.decode([i]) for i in rec["ids"]]
            ngrams[t] = rec
            pf = choose_prefill(bids, rec["ids"]) if rec["defined"] else {"rule": "none", "ids": None}
            sig = (read_json(BENCH / TASK_DIR[t] / "spec.json")["signature"] if t not in PATH_TASKS
                   else re.search(r"solve\([^)]*\)", read_json(E8 / "prompts" / "frozen_prompts.json")["spec"][t]).group(0))
            neu = "```python\ndef " + sig + ":\n"
            prefills[t] = {"signature": pf, "signature_text": tok.decode(pf["ids"]) if pf.get("ids") else None,
                           "neutral_text": neu, "neutral_ids": list(tok(neu, add_special_tokens=False).input_ids)}
            if t in PATH_TASKS:
                line = "import heapq" if t == "t2" else "from collections import deque"
                line_ids = None
                for ids in bids:
                    txt = [tok.decode(ids[:i + 1]) for i in range(len(ids))]
                    for i, s in enumerate(txt):
                        if s.endswith(line):
                            # smallest token span ending at i whose decoded text contains the line
                            for j in range(i, -1, -1):
                                if line in tok.decode(ids[j:i + 1]):
                                    line_ids = ids[j:i + 1]
                                    break
                            break
                    if line_ids:
                        break
                inside = bool(rec["defined"] and line_ids and any(
                    tuple(line_ids[k:k + rec["n"]]) == tuple(rec["ids"]) for k in range(len(line_ids) - rec["n"] + 1)))
                prefills[t]["opening_veto"] = {"line": line, "line_ids": line_ids,
                                               "line_tokens": [tok.decode([i]) for i in (line_ids or [])],
                                               "rule_ngram_inside_line": inside, "defined": bool(line_ids) and not inside}
                if t == "t2":
                    heap = "```python\nimport heapq"
                    prefills[t]["heapq_prefill_text"] = heap
                    prefills[t]["heapq_prefill_ids"] = list(tok(heap, add_special_tokens=False).input_ids)
            else:
                a = associate(t)
                pr = proximity(t, base, forced, pool)
                assoc[t] = {**a, **pr}
            logger.info(f"S2 {t}: n-gram {rec.get('text')!r} n={rec.get('n')} freq={rec.get('baseline_frequency')} "
                        f"maxcol={rec.get('max_collateral')} coveto={rec.get('co_vetoed')} class={rec.get('token_class')}"
                        f" | prefill {prefills[t]['signature'].get('rule')} {prefills[t]['signature_text']!r}"
                        + (f" | assoc {assoc[t]['associate']} prox {assoc[t]['proximity']}" if t in assoc else ""))
    finally:
        pool.shutdown()
    write_json(PRED_DIR / "ngrams.json", ngrams)
    write_json(PRED_DIR / "prefills.json", prefills)
    write_json(PRED_DIR / "associate_proximity.json", assoc)
    return {"ngrams": ngrams, "prefills": prefills, "assoc": assoc}
