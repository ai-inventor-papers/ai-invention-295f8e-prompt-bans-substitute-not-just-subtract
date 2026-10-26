"""Distinctive token n-gram tool (S2), sham n-gram (matched control), mask expansion and string-leak detection.

Program text = the stored raw response when present, else '```python\\n' + code + '\\n```'; ids = Qwen3 tokenizer
(add_special_tokens=False); presence set per program for n = 1..6.

distinctive(A): candidates present in >= 0.8 of refs_A, minus format-unsafe ones (code fence, 'solve', the solve
signature, < 2 alphanumeric characters, any whitespace-only token - added after unit test u1 showed that an
indentation-tailed n-gram is bypassed by re-indenting); score(g) = max over other algorithms O of the share of O's programs
containing g; argmin score; ties -> smaller n, higher presence in refs_A, lexicographic ids.  CO-VETOED = {O: share
>= 0.5}.  sham(A): an algorithm-generic n-gram (>= 0.8 presence in refs_A and in every other algorithm's programs,
no 'def'/'solve'/'return'/'import'), same n as the distinctive n-gram (else nearest), presence in refs_A closest to
the distinctive n-gram's; it must contain an identifier and no Python keyword or the fence tag 'python' (a keyword
veto breaks syntax, which no matched control should do); fallback = maximise the minimum presence across algorithms
(reported).
"""

from __future__ import annotations

from collections import Counter
from typing import Any

NMAX = 6


def program_text(row: dict[str, Any]) -> str:
    t = row.get("text")
    if t:
        return t
    return "```python\n" + (row.get("code") or "") + "\n```"


def presence(ids: list[int], nmax: int = NMAX) -> set[tuple[int, ...]]:
    out: set[tuple[int, ...]] = set()
    L = len(ids)
    for n in range(1, nmax + 1):
        for i in range(L - n + 1):
            out.add(tuple(ids[i:i + n]))
    return out


def share_table(pres_list: list[set]) -> Counter:
    c: Counter = Counter()
    for p in pres_list:
        c.update(p)
    return c


def boundary_whitespace(g: tuple[int, ...] | list[int], decode) -> bool:
    """Some token of g is pure whitespace (indentation / newline): a layout veto, bypassed by re-indenting."""
    return any(not decode([t]).strip() for t in g)


def format_unsafe(s: str, signature: str, sham: bool = False) -> bool:
    st = s.strip()
    if not st or "`" in s or "solve" in s:
        return True
    if sum(ch.isalnum() for ch in s) < 2:
        return True
    if st in signature:
        return True
    if sham:
        import keyword

        if any(w in s for w in ("def", "return", "import", "python")):
            return True
        words = [w for w in __import__("re").findall(r"[A-Za-z_][A-Za-z0-9_]*", s)]
        if not words or any(w in keyword.kwlist for w in words):
            return True  # a sham must veto identifier text, never a keyword (a keyword veto breaks syntax)
    return False


def distinctive(refs_ids: list[list[int]], others_ids: dict[str, list[list[int]]], decode, signature: str,
                presence_min: float = 0.8, co_veto: float = 0.5) -> dict[str, Any]:
    if not refs_ids:
        raise ValueError("distinctive(): empty reference set")
    ref_p = [presence(x) for x in refs_ids]
    rc = share_table(ref_p)
    nref = len(ref_p)
    cands = [g for g, k in rc.items() if k / nref >= presence_min]
    oth_tables = {o: (share_table([presence(x) for x in progs]), len(progs)) for o, progs in others_ids.items()
                  if progs}
    n_unsafe = 0
    best = None
    for g in cands:
        s = decode(list(g))
        if format_unsafe(s, signature) or boundary_whitespace(g, decode):
            n_unsafe += 1
            continue
        coll = {o: (tab[g] / n if n else 0.0) for o, (tab, n) in oth_tables.items()}
        score = max(coll.values()) if coll else 0.0
        key = (round(score, 9), len(g), -rc[g] / nref, g)
        if best is None or key < best[0]:
            best = (key, g, coll)
    if best is None:
        raise ValueError("distinctive(): no format-safe candidate n-gram")
    _, g, coll = best
    return {"ids": list(g), "string": decode(list(g)), "n": len(g), "presence_refs": rc[g] / nref,
            "n_refs": nref, "score": max(coll.values()) if coll else 0.0, "collateral": coll,
            "n_others": {o: n for o, (_, n) in oth_tables.items()},
            "co_vetoed": sorted(o for o, v in coll.items() if v >= co_veto), "n_candidates": len(cands),
            "n_format_unsafe": n_unsafe}


def sham(refs_ids: list[list[int]], all_others_ids: dict[str, list[list[int]]], decode, signature: str,
         n_target: int, presence_target: float, presence_min: float = 0.8,
         exclude: list[list[int]] | None = None) -> dict[str, Any]:
    ref_p = [presence(x) for x in refs_ids]
    rc = share_table(ref_p)
    nref = len(ref_p)
    tabs = {o: (share_table([presence(x) for x in progs]), len(progs)) for o, progs in all_others_ids.items()
            if progs}
    rows = []
    for g, k in rc.items():
        if k / nref < presence_min:
            continue
        s = decode(list(g))
        if format_unsafe(s, signature, sham=True) or boundary_whitespace(g, decode):
            continue
        if exclude and any(list(g) == list(e) for e in exclude):
            continue  # never the distinctive n-gram itself
        mins = [tab[g] / n for tab, n in tabs.values()]
        rows.append((g, k / nref, min(mins) if mins else 1.0, {o: tab[g] / n for o, (tab, n) in tabs.items()}))
    generic = [r for r in rows if r[2] >= presence_min]
    rule = "generic(>=0.8 everywhere)"
    pool = generic
    if not pool:
        rule = "fallback: maximise the minimum presence across algorithms"
        if not rows:
            raise ValueError("sham(): no candidate")
        mx = max(r[2] for r in rows)
        pool = [r for r in rows if r[2] == mx]
        # ties at the max-min presence (often 0 on 3-line bench programs) -> most generic on average
        mean_of = lambda r: sum(r[3].values()) / max(1, len(r[3]))  # noqa: E731
        best_mean = max(mean_of(r) for r in pool)
        pool = [r for r in pool if mean_of(r) == best_mean]
        rule += f" (tie at min presence {mx:.2f} broken by max mean presence {best_mean:.2f})"
    ns = sorted({len(r[0]) for r in pool}, key=lambda n: (abs(n - n_target), n))
    n_use = ns[0]
    pool = [r for r in pool if len(r[0]) == n_use]
    pool.sort(key=lambda r: (abs(r[1] - presence_target), -r[2], r[0]))
    g, pr, mn, per = pool[0]
    return {"ids": list(g), "string": decode(list(g)), "n": len(g), "presence_refs": pr, "min_presence_others": mn,
            "presence_others": per, "rule": rule, "n_pool": len(pool), "n_target": n_target,
            "presence_target": presence_target}


def expand(g_ids: list[int], decode, encode) -> list[list[int]]:
    """g itself + the tokenisations of its decoded string with a leading space and with a leading newline (and
    without leading whitespace), when these differ (vLLM bad_words-style surface variants)."""
    s = decode(list(g_ids))
    core = s.lstrip(" \n\t")
    variants = [list(g_ids)]
    for v in (" " + core, "\n" + core, core):
        if not core:
            continue
        ids = encode(v)
        if ids and ids not in variants:
            variants.append(ids)
    return variants


def occurrences(out_ids: list[int], seqs: list[list[int]]) -> int:
    n = 0
    for s in seqs:
        L = len(s)
        for i in range(len(out_ids) - L + 1):
            if out_ids[i:i + L] == s:
                n += 1
    return n


def leak_spans(text_ids: list[int], core: str, decode) -> list[list[int]]:
    """Minimal contiguous output-token spans whose decoded text contains `core` (the vetoed string)."""
    spans = []
    L = len(text_ids)
    i = 0
    while i < L:
        found = None
        for j in range(i + 1, min(L, i + 12) + 1):
            if core in decode(text_ids[i:j]):
                found = j
                break
        if found is None:
            i += 1
            continue
        # shrink from the left
        k = i
        while k + 1 < found and core in decode(text_ids[k + 1:found]):
            k += 1
        spans.append(text_ids[k:found])
        i = found
    uniq = []
    for s in spans:
        if s not in uniq:
            uniq.append(s)
    return uniq


def string_leak(text: str, out_ids: list[int], mask_items: list[dict[str, Any]], decode) -> dict[str, Any]:
    """A leak: the decoded output contains a vetoed string's core although none of its banned id sequences
    occurs in the generated ids (non-canonical tokenisation).  Returns per-item flags and covering spans."""
    leaks = []
    for it in mask_items:
        core = it["string"].strip()
        if len(core) < 3:
            continue
        if core in text and occurrences(out_ids, it["seqs"]) == 0:
            leaks.append({"string": it["string"], "core": core, "spans": leak_spans(out_ids, core, decode)})
    return {"leak": bool(leaks), "items": leaks}


# ------------------------------------------------------------------------------------------------ unit tests
def unit_tests(decode, encode) -> dict[str, Any]:
    """Synthetic known-answer tests: a planted n-gram must be chosen; ties resolved by smaller n; the sham must be
    generic; expand() must include the leading-space variant; occurrences / leak spans behave."""
    import random

    rng = random.Random(0)
    base = list(range(1000, 1060))
    planted = [7001, 7002]

    def prog(extra):
        b = rng.sample(base, 30)
        return b[:10] + extra + b[10:] + [5000, 5001, 5002]  # 5000.. = generic tail present everywhere

    refs = [prog(planted) for _ in range(20)]
    others = {"o1": [prog([]) for _ in range(20)], "o2": [prog([7001]) for _ in range(20)]}
    dec = lambda ids: " ".join(f"tok{i}" for i in ids)  # noqa: E731 - synthetic decoder
    d = distinctive(refs, others, dec, signature="def solve(x):")
    ok1 = d["ids"] in ([7002], [7001, 7002]) and d["score"] == 0.0
    ok_tie = d["ids"] == [7002]  # 1-gram 7002 and 2-gram (7001, 7002) both score 0 -> smaller n wins
    sh = sham(refs, others, dec, signature="def solve(x):", n_target=1, presence_target=1.0)
    ok2 = sh["min_presence_others"] >= 0.8 and sh["ids"][0] in (5000, 5001, 5002)
    ex = expand(encode(" popleft"), decode, encode)
    ok3 = len(ex) >= 2
    occ = occurrences([1, 2, 3, 1, 2], [[1, 2], [3]])
    ok4 = occ == 3
    return {"planted_found": ok1, "tie_smaller_n": ok_tie, "sham_generic": ok2, "expand_variants": ok3,
            "occurrences": ok4, "distinctive": d, "sham": sh, "expand_example": ex,
            "all_pass": bool(ok1 and ok_tie and ok2 and ok3 and ok4)}
