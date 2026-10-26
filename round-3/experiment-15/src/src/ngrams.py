#!/usr/bin/env python3
"""D1: distinctive signature n-gram of an algorithm under Llama's tokenizer.

Reference set = the algorithm's programs (code inside its ```python fence, re-tokenised with add_special_tokens=False)
plus, where available, their generated id sequences.  Candidates = token n-grams (1 <= n <= 6) present in >= 0.8 of
the re-tokenised references AND >= 0.8 of the generated-id subset (when it has >= 5 programs).  Objective = minimise
the largest share, over the other catalogue algorithms j, of j's forced programs (labelled as requested,
re-tokenised) that contain the n-gram; j with < 5 such programs also use their bench reference (flagged).
Ties -> shorter n, then higher presence, then lexicographic ids."""

from __future__ import annotations

from collections import Counter
from typing import Any

from src import prompts_llama as P
from src.ws import BENCH

from bench.common.catalogue import TASKS  # noqa: E402

NMAX = 6


def tok_code(code: str) -> list[int]:
    return P.tokenizer()("```python\n" + code.strip("\n") + "\n```", add_special_tokens=False)["input_ids"]


def grams_of(ids: list[int], nmax: int = NMAX) -> set[tuple[int, ...]]:
    out = set()
    L = len(ids)
    for n in range(1, nmax + 1):
        for i in range(L - n + 1):
            out.add(tuple(ids[i:i + n]))
    return out


def reference_code(task: str, mode: str) -> str | None:
    if task not in TASKS:  # path-task screen (exp10 canon tasks): no bench reference
        return None
    f = BENCH / TASKS[task]["task_id"] / "references" / f"{mode}.py"
    return f.read_text() if f.exists() else None


def find_ngram(task: str, target: str, ref_codes: list[str], ref_gen_ids: list[list[int]],
               other_codes: dict[str, list[str]], presence_min: float = 0.8,
               exclude: list[tuple[int, ...]] | None = None) -> dict[str, Any]:
    ref_sets = [grams_of(tok_code(c)) for c in ref_codes if c]
    gen_sets = [grams_of(list(g)) for g in ref_gen_ids if g]
    use_gen = len(gen_sets) >= 5
    nref = len(ref_sets)
    if nref == 0:
        return {"defined": False, "reason": "empty reference set", "n_ref": 0}
    cnt = Counter()
    for s in ref_sets:
        cnt.update(s)
    excl = set(map(tuple, exclude or []))
    others = {}
    flags = {}
    for j, codes in other_codes.items():
        cs = list(codes)
        if len(cs) < 5:
            rc = reference_code(task, j)
            if rc:
                cs = cs + [rc]
            flags[j] = f"low_n({len(codes)})+reference"
        others[j] = [grams_of(tok_code(c)) for c in cs if c]

    def evaluate(pmin: float, gen_required: bool) -> list[dict[str, Any]]:
        cands = [g for g, c in cnt.items() if c / nref >= pmin and g not in excl]
        res = []
        for g in cands:
            gp = sum(1 for s in gen_sets if g in s) / len(gen_sets) if gen_sets else None
            if gen_required and use_gen and (gp is None or gp < pmin):
                continue
            coll = {j: (sum(1 for s in sets if g in s) / len(sets) if sets else 0.0) for j, sets in others.items()}
            res.append({"ids": list(g), "n": len(g), "presence": cnt[g] / nref, "gen_presence": gp,
                        "max_collateral": max(coll.values()) if coll else 0.0, "collateral": coll})
        res.sort(key=lambda r: (r["max_collateral"], r["n"], -r["presence"], r["ids"]))
        return res

    relax = "none"
    res = evaluate(presence_min, True)
    if not res:
        relax = "presence>=0.7"
        res = evaluate(0.7, True)
    if not res and use_gen:
        relax = "generated-id set only (>=0.7)"
        cnt_gen = Counter()
        for s in gen_sets:
            cnt_gen.update(s)
        cnt.clear()
        cnt.update(cnt_gen)
        nref = len(gen_sets)
        res = evaluate(0.7, False)
    if not res:
        return {"defined": False, "reason": "no candidate", "n_ref": len(ref_sets), "n_gen": len(gen_sets)}
    best = res[0]
    tok = P.tokenizer()
    best = dict(best)
    best.update({"defined": True, "decoded": tok.decode(best["ids"]), "n_ref": len(ref_sets), "n_gen": len(gen_sets),
                 "relaxation": relax, "co_vetoed": sorted(j for j, v in best["collateral"].items() if v >= 0.5),
                 "low_n_flags": flags, "n_candidates": len(res),
                 "runner_up": [{"ids": r["ids"], "decoded": tok.decode(r["ids"]), "max_collateral": r["max_collateral"],
                                "presence": r["presence"]} for r in res[1:4]]})
    return best


def share_containing(g: list[int], codes: list[str]) -> float | None:
    if not codes:
        return None
    gt = tuple(g)
    return sum(1 for c in codes if gt in grams_of(tok_code(c), nmax=len(gt))) / len(codes)
