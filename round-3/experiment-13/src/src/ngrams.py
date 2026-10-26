#!/usr/bin/env python3
"""S0.5: the default's distinctive token n-gram (and the SHAM control n-gram) per task.

tokens(code) = tok.encode('```python\\n' + code.rstrip() + '\\n' + '```').  REF = token lists of the default's
programs (pilot rows labelled D, or the bf16 twin / round r-1 programs labelled D on re-derivation); OTHERS[m] =
forced programs with label == forced_mode == m for every m != D.

Rule (frozen): for n = 1..6 keep n-grams with coverage(REF) >= 0.8; collateral coll[g][m] = share of OTHERS[m]
containing g; choose argmin max_m coll (ties: smaller n, higher coverage, lexicographically smallest id tuple).
CO_VETO = {m : coll[g][m] >= 0.5}.  No candidate -> GREEDY COVER (flagged): repeatedly add, among n-grams that occur
in at least ceil(still-needed / slots-left) of the still-uncovered REF programs (coverage counted on them; 'needed' =
programs still missing to reach 0.8 of REF, 3 slots), the one with min max-collateral (same ties, coverage on the
uncovered programs), until >= 0.8 of REF contain at least one chosen n-gram; else 'no_small_token_set'.
SHAM: same n as g; among coverage >= 0.8 candidates maximise min_m coll (shared by every algorithm); ties: closest
coverage to g's, then closest median first-occurrence position to g's, then smallest id tuple.
"""

from __future__ import annotations

import math
import statistics
from collections import Counter
from typing import Any

from loguru import logger

from common import (DEFAULTS, FENCE_CLOSE, FENCE_OPEN, FROZEN_CONSTANTS, PRED, TASK_ORDER, catalogue, read_jsonl,
                    task_dir, write_json)

NG = FROZEN_CONSTANTS["ngram"]


def code_tokens(tok, code: str) -> list[int]:
    return tok.encode(FENCE_OPEN + code.rstrip() + "\n" + FENCE_CLOSE, add_special_tokens=False)


def all_ngrams(seq: list[int], n_max: int = 6) -> set[tuple[int, ...]]:
    out = set()
    L = len(seq)
    for n in range(1, n_max + 1):
        for i in range(L - n + 1):
            out.add(tuple(seq[i:i + n]))
    return out


def first_pos(seq: list[int], g: tuple[int, ...]) -> int | None:
    n = len(g)
    for i in range(len(seq) - n + 1):
        if tuple(seq[i:i + n]) == g:
            return i
    return None


def contains(seq: list[int], g: tuple[int, ...]) -> bool:
    return first_pos(seq, g) is not None


def _collateral(g: tuple[int, ...], other_sets: dict[str, list[set]]) -> dict[str, float]:
    return {m: sum(1 for s in sets if g in s) / len(sets) for m, sets in other_sets.items() if sets}


def derive(ref: list[list[int]], others: dict[str, list[list[int]]], exclude: set | None = None,
           n_max: int = NG["n_max"], cov: float = NG["coverage"], max_greedy: int = 3) -> dict[str, Any]:
    """Returns {'ngrams': [ids...], 'greedy': bool, 'coverage', 'coll', 'score', 'ok', 'reason'}."""
    exclude = exclude or set()
    if not ref:
        return {"ok": False, "reason": "empty_ref", "ngrams": [], "greedy": False}
    ref_sets = [all_ngrams(s, n_max) for s in ref]
    other_sets = {m: [all_ngrams(s, n_max) for s in progs] for m, progs in others.items() if progs}
    cnt: Counter = Counter()
    for s in ref_sets:
        cnt.update(s)
    nref = len(ref)

    def key(g: tuple[int, ...], coverage: float) -> tuple:
        coll = _collateral(g, other_sets)
        score = max(coll.values()) if coll else 0.0
        return (round(score, 12), len(g), -round(coverage, 12), g)

    cands = [g for g, c in cnt.items() if c / nref >= cov and g not in exclude]
    if cands:
        best = min(cands, key=lambda g: key(g, cnt[g] / nref))
        coll = _collateral(best, other_sets)
        return {"ok": True, "greedy": False, "ngrams": [list(best)], "coverage": cnt[best] / nref, "coll": coll,
                "score": max(coll.values()) if coll else 0.0, "n_candidates": len(cands), "reason": None}
    # greedy cover
    chosen: list[tuple[int, ...]] = []
    uncovered = list(range(nref))
    need_total = math.ceil(cov * nref - 1e-9)
    while len(chosen) < max_greedy and (nref - len(uncovered)) / nref < cov:
        sub: Counter = Counter()
        for i in uncovered:
            sub.update(ref_sets[i])
        nu = len(uncovered)
        # pace rule: each step must cover its share of the programs still needed to reach 0.8 with the slots left
        thr = math.ceil((need_total - (nref - nu)) / (max_greedy - len(chosen)))
        step = [g for g, c in sub.items() if c >= thr and g not in exclude and g not in chosen]
        if not step:
            break
        g = min(step, key=lambda g: key(g, sub[g] / nu))
        chosen.append(g)
        uncovered = [i for i in uncovered if g not in ref_sets[i]]
    covered = (nref - len(uncovered)) / nref
    colls = {m: sum(1 for s in sets if any(g in s for g in chosen)) / len(sets) for m, sets in other_sets.items()
             if sets}
    ok = covered >= cov
    return {"ok": ok, "greedy": True, "ngrams": [list(g) for g in chosen], "coverage": covered, "coll": colls,
            "score": max(colls.values()) if colls else 0.0, "reason": None if ok else "no_small_token_set"}


def sham(ref: list[list[int]], others: dict[str, list[list[int]]], g: list[int], n_max: int = NG["n_max"],
         cov: float = NG["coverage"]) -> dict[str, Any]:
    ref_sets = [all_ngrams(s, n_max) for s in ref]
    other_sets = {m: [all_ngrams(s, n_max) for s in progs] for m, progs in others.items() if progs}
    cnt: Counter = Counter()
    for s in ref_sets:
        cnt.update(s)
    nref = len(ref)
    gt = tuple(g)
    g_cov = sum(1 for s in ref_sets if gt in s) / nref
    g_pos = [first_pos(s, gt) for s in ref]
    g_med = statistics.median([p for p in g_pos if p is not None]) if any(p is not None for p in g_pos) else 0
    n = len(gt)
    cands = [h for h, c in cnt.items() if len(h) == n and c / nref >= cov and h != gt]
    relaxed = False
    if not cands:  # fall back to the nearest n with candidates (flagged)
        relaxed = True
        for dn in range(1, n_max):
            cands = [h for h, c in cnt.items() if len(h) in (n - dn, n + dn) and c / nref >= cov and h != gt]
            if cands:
                break
    if not cands:
        return {"ok": False, "reason": "no_sham_candidate"}

    def key(h):
        coll = _collateral(h, other_sets)
        mn = min(coll.values()) if coll else 0.0
        pos = [first_pos(s, h) for s in ref]
        med = statistics.median([p for p in pos if p is not None])
        return (-round(mn, 12), round(abs(cnt[h] / nref - g_cov), 12), abs(med - g_med), h)

    best = min(cands, key=key)
    coll = _collateral(best, other_sets)
    return {"ok": True, "ngram": list(best), "coverage": cnt[best] / nref, "coll": coll,
            "min_coll": min(coll.values()) if coll else 0.0, "relaxed_n": relaxed}


def load_ref_and_others(tok, task: str) -> tuple[list[list[int]], dict[str, list[list[int]]]]:
    D = DEFAULTS[task]
    pilot = read_jsonl(task_dir(task) / "pilot_rows.jsonl")
    ref = [code_tokens(tok, r["code"]) for r in pilot if r["label"] == D and r.get("code")]
    forced = read_jsonl(task_dir(task) / "forced_programs.jsonl")
    others = {m: [code_tokens(tok, r["code"]) for r in forced if r["forced_mode"] == m and r["label"] == m
                  and r.get("code")] for m in catalogue(task) if m != D}
    return ref, others


def others_for(tok, task: str) -> dict[str, list[list[int]]]:
    return load_ref_and_others(tok, task)[1]


def describe(tok, res: dict[str, Any]) -> dict[str, Any]:
    out = dict(res)
    out["texts"] = [tok.decode(g) for g in res.get("ngrams", [])]
    out["co_veto"] = sorted(m for m, v in (res.get("coll") or {}).items() if v >= NG["co_veto_collateral"])
    return out


def derive_all(tok) -> dict[str, Any]:
    out = {"rule": __doc__, "tasks": {}}
    for t in TASK_ORDER:
        ref, others = load_ref_and_others(tok, t)
        res = describe(tok, derive(ref, others))
        sh = sham(ref, others, res["ngrams"][0]) if res.get("ngrams") else {"ok": False}
        if sh.get("ok"):
            sh["text"] = tok.decode(sh["ngram"])
        out["tasks"][t] = {"D": DEFAULTS[t], "n_ref": len(ref), "n_others": {m: len(v) for m, v in others.items()},
                           "distinctive": res, "sham": sh, "source": "fp8_pilot"}
        logger.info(f"{t}: ngram {res.get('texts')} cov {res.get('coverage'):.2f} max-coll {res.get('score'):.2f} "
                    f"greedy={res.get('greedy')} co_veto={res.get('co_veto')} | sham {sh.get('text')!r} "
                    f"min-coll {sh.get('min_coll')}")
    return out


def unit_tests() -> dict[str, Any]:
    """T3: synthetic token lists with known answers (incl. ties and the greedy cover)."""
    res = {}
    ref = [[1, 2, 3, 9], [1, 2, 3, 8], [1, 2, 3, 7], [4, 2, 3, 6], [1, 2, 3, 5]]
    others = {"a": [[1, 2, 5], [2, 3, 4]], "b": [[1, 7], [9, 9]]}
    r = derive(ref, others, n_max=3)
    # coverage>=0.8: (2,), (3,), (2,3), (1,)?(4/5=0.8 yes), (1,2) 0.8, (1,2,3) 0.8; collateral max: (2,)->1.0 (a),
    # (3,)->0.5, (2,3)->0.5, (1,)->0.5 (a:1/2, b:1/2), (1,2)->0.5, (1,2,3)->0 -> choose (1,2,3)
    res["min_collateral"] = r["ngrams"] == [[1, 2, 3]] and not r["greedy"]
    others2 = {"a": [[1, 2, 3]], "b": [[1, 2, 3]]}
    r2 = derive(ref, others2, n_max=3)
    # every candidate has collateral 1.0 except (2,3)? (2,3) in a -> 1.0; tie on score -> smaller n -> (2,) or (3,)
    # (2,) coverage 1.0, (3,) coverage 1.0, (1,) 0.8 -> higher coverage then lexicographic -> (2,)
    res["tie_rules"] = r2["ngrams"] == [[2]]
    ref3 = [[1, 10], [1, 11], [2, 12], [2, 13], [3, 14]]
    r3 = derive(ref3, {"a": [[5]]}, n_max=2)
    res["greedy_cover"] = r3["greedy"] and r3["ok"] and r3["ngrams"][:2] == [[1], [2]] and r3["coverage"] >= 0.8
    r4 = derive([[1, 2], [1, 2]], {"a": [[3]]}, n_max=2)
    res["deterministic"] = r4 == derive([[1, 2], [1, 2]], {"a": [[3]]}, n_max=2)
    s = sham(ref, others, [1, 2, 3], n_max=3)
    # no other n=3 candidate reaches 0.8 -> relaxed to n=2: (1,2) and (2,3) tie on min collateral 0 -> closest coverage
    res["sham_relaxed_tie"] = s["ok"] and s["relaxed_n"] and s["ngram"] == [1, 2]
    s2 = sham([[7, 1, 2], [7, 1, 3], [7, 1, 4], [7, 1, 5]], {"a": [[7, 1]], "b": [[7, 9]]}, [1], n_max=2)
    # n=1 candidates with coverage >= 0.8 besides (1,): (7,) -> shared by a and b (min coll 1.0)
    res["sham_same_n_max_shared"] = s2["ok"] and s2["ngram"] == [7] and not s2["relaxed_n"]
    res["all_pass"] = all(res.values())
    return res


if __name__ == "__main__":
    from common import setup_logging
    from prompts import load_tokenizer

    setup_logging("s0_ngrams")
    ut = unit_tests()
    logger.info(f"n-gram unit tests: {ut}")
    assert ut["all_pass"], ut
    tok = load_tokenizer()
    out = derive_all(tok)
    out["unit_tests"] = ut
    out2 = derive_all(tok)
    assert [out["tasks"][t]["distinctive"]["ngrams"] for t in TASK_ORDER] == \
        [out2["tasks"][t]["distinctive"]["ngrams"] for t in TASK_ORDER], "n-gram derivation is not deterministic"
    write_json(PRED / "ngrams_fp8.json", out)
