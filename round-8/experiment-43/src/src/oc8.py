#!/usr/bin/env python3
"""OC_u: opening classifiers over PARTIAL programs (regex rules on code with comments and string literals removed).

Qwen units B3/A3/B6 reuse the iteration-7 rules unchanged (opening_cls.py). New units get keyword rules written from the
source artifacts' stored programs (exp31 Gemma rows, exp10 Llama T1 rows, exp11 Llama pilot rows); they are validated
on the new fit twins' W4-W5 programs at every prefix length (gate: decided-label agreement >= 0.95 and full-program
agreement 1.00). A rule returns a label only once its structural evidence is present, else 'undecided'. A unit whose
classifier fails its gate labels each continuation by completing it and running the frozen labeller.
"""

from __future__ import annotations

import re
from typing import Any

import opening_cls as OC7

code_part = OC7.code_part
strip_comments = OC7.strip_comments


def _has(p: str, c: str) -> bool:
    return re.search(p, c) is not None


def _t04(c: str) -> str:
    if _has(r"\blps\b|\bpi\s*=\s*\[|\bfailure\w*|\bprefix_function|\bfail\s*=|\bcompute_\w*prefix|\bnxt\s*=\s*\[|"
            r"\bnext_?arr\w*\s*=|\bpartial\w*\s*=\s*\[|\blongest_prefix", c):
        return "kmp"
    if _has(r"\bz\s*=\s*\[\s*0\s*\]|\bz_?(array|arr|func)\b", c):
        return "z_algorithm"
    if _has(r"\bbad_?char|\bshift\w*\s*=\s*\{|\bskip\s*=\s*\{|\blast_?occ", c):
        return "bmh"
    if _has(r"\b(hash_?\w*|h_?needle|needle_hash|window_hash|base|mod|prime)\s*=\s*\d|\bpow\s*\(\s*\w+\s*,", c) and \
            _has(r"\bord\s*\(|\bhash\w*\b", c):
        return "rabin_karp"
    if _has(r"\.find\s*\(|\.index\s*\(|\bneedle\s+in\s+haystack|\bnot\s+in\s+haystack|\.count\s*\(\s*needle", c):
        return "builtin"
    if _has(r"haystack\s*\[\s*\w+\s*:\s*\w+\s*\+|haystack\s*\[\s*\w+\s*\+\s*\w+\s*\]\s*[!=]=|\.startswith\s*\(|"
            r"haystack\s*\[\s*\w+\s*:\s*\w+\s*\]\s*==|needle\s*\[\s*\w+\s*\]\s*[!=]=\s*haystack", c):
        return "naive"
    return "undecided"


def _r6(c: str) -> str:
    if _has(r"\bbisect", c):
        return "bisect_module"
    if _has(r"\*=\s*2|<<=\s*1|\bbound\s*=\s*1\b|\bexponential", c):
        return "exponential_search"
    if _has(r"\bmid\s*=|//\s*2", c) and _has(r"\b(lo|low|left|l|start|s)\b\s*<=?\s*\b(hi|high|right|r|end|e)\b", c):
        return "binary_search"
    if _has(r"for\s+\w+(\s*,\s*\w+)?\s+in\s+(enumerate|range)\s*\(", c) and _has(r"==\s*target|target\s*==", c):
        return "linear_scan"
    if _has(r"\.index\s*\(\s*target", c):
        return "linear_scan"
    return "undecided"


def _t1(c: str) -> str:
    heap = _has(r"heapq|heappush|heappop|PriorityQueue", c)
    if heap:
        return "astar_gbfs" if _has(r"heuristic|manhattan|abs\s*\(", c) else "dijkstra"
    if _has(r"\b(forward|backward|front_?\w*|back_?\w*|start_queue|goal_queue|from_start|from_goal)\s*=", c) and \
            _has(r"deque|popleft", c) and _has(r"\b(backward|back_?\w*|goal_queue|from_goal)\b", c):
        return "bibfs"
    if _has(r"popleft|\.pop\s*\(\s*0\s*\)|\bqueue\.get\s*\(", c):
        return "bfs"
    if _has(r"\bdef\s+(dfs|_dfs|backtrack|explore|search|helper|recurse|_search|find_path|visit)\s*\(", c) or \
            (_has(r"\bstack\s*=\s*\[", c) and _has(r"\.pop\s*\(\s*\)", c)):
        return "dfs"
    if _has(r"\bdepth_limit|\bmax_depth|\biddfs|\bdls\b", c):
        return "iddfs"
    return "undecided"


def _t03(c: str) -> str:
    if _has(r"nsmallest|nlargest", c):
        return "size_k_heap"
    if _has(r"\bpivot|\bpartition", c):
        return "median_of_medians" if _has(r"median", c) else "quickselect"
    if _has(r"heappush|heappop|heapify", c):
        if _has(r"len\s*\(\s*\w+\s*\)\s*>=?\s*k|len\s*\(\s*\w+\s*\)\s*<\s*k|heappushpop|heapreplace|\[\s*:\s*k\s*\]", c):
            return "size_k_heap"
        if _has(r"\bheapify\s*\(|for\s+_?\w*\s+in\s+range\s*\(\s*k", c):
            return "heapify_pop"
        return "undecided"
    if _has(r"\[\s*0\s*\]\s*\*\s*\(?\s*\d{4,}|\[\s*0\s*\]\s*\*\s*\(\s*\w+\s*-\s*\w+|\b20001\b|"
            r"for\s+\w+\s+in\s+sorted\s*\(\s*count\w*|for\s+\w+\s+in\s+range\s*\(\s*-\s*10000", c):
        return "counting_sort"
    if _has(r"\bsorted\s*\(|\.sort\s*\(", c):
        return "full_sort"
    return "undecided"


def _t06(c: str) -> str:
    if _has(r"\bslow\b|\bfast\b|tortoise|\bhare\b", c):
        return "floyd"
    if _has(r"abs\s*\(\s*nums\s*\[|nums\s*\[\s*abs|nums\s*\[\s*\w+\s*\]\s*\*=\s*-1|nums\s*\[[^\]]+\]\s*=\s*-\s*nums", c):
        return "index_marking"
    if _has(r"\bsorted\s*\(|\.sort\s*\(", c):
        return "sort_adjacent"
    if _has(r"\bmid\s*=", c) and _has(r"\b(lo|low|left|l)\b\s*<=?\s*\b(hi|high|right|r)\b", c):
        return "value_binary_search"
    if _has(r"\bset\s*\(\s*\)|\bseen\b|\bvisited\b|\[\s*False\s*\]\s*\*|\bCounter\s*\(|\{\s*\}", c):
        return "hash_set"
    return "undecided"


def _r1(c: str) -> str:
    if _has(r"lru_cache|@cache\b|\bmemo\b", c):
        return "memo_recursion"
    if _has(r"\bbisect|\bdp\s*=\s*\[", c):
        return "dp_bisect"
    if _has(r"\bgraph\b|\badj\w*\s*=|\bindegree", c):
        return "dag_longest_path"
    if _has(r"key\s*=\s*lambda\s+\w+\s*:\s*\(?\s*\w+\s*\[\s*1\s*\]|itemgetter\s*\(\s*1\s*\)", c):
        return "greedy_end"
    return "undecided"


def _t14(c: str) -> str:
    if _has(r"heapq|heappush|nlargest|heapify", c):
        return "heap"
    if _has(r"\bbucket|\[\s*\[\s*\]\s*for\s+_?\w*\s+in\s+range", c):
        return "bucket_sort"
    if _has(r"\bpivot|\bpartition", c):
        return "quickselect_counts"
    if _has(r"most_common|\bsorted\s*\(|\.sort\s*\(", c):
        return "sort_by_count"
    return "undecided"


def _t10(c: str) -> str:
    if _has(r"\bparent\b|\bfind\s*\(|\bunion\s*\(|\brank\b", c):
        return "union_find"
    if _has(r"\bdeque\b|popleft|\.pop\s*\(\s*0\s*\)", c):
        return "bfs"
    if _has(r"\bdef\s+(dfs|_dfs|explore|visit|traverse)\s*\(", c) or \
            (_has(r"\bstack\s*=\s*\[", c) and _has(r"\.pop\s*\(\s*\)", c)):
        return "dfs"
    if _has(r"\blabel\w*\s*=\s*(list|\[)", c):
        return "label_propagation"
    return "undecided"


def _t08(c: str) -> str:
    if _has(r"lru_cache|@cache\b|\bmemo\b", c):
        return "memo_recursion"
    if _has(r"\bmatrix|\bmat\w*\s*=\s*\[\s*\[|\[\s*\[\s*1\s*,\s*1\s*\]\s*,\s*\[\s*1\s*,\s*0\s*\]\s*\]|\bmat_?mul|"
            r"\bmultiply\s*\(", c):
        return "matrix_power"
    if _has(r"doubling|\bfib_pair|\bn\s*>>\s*1|>>=\s*1|\bbin\s*\(\s*n", c):
        return "fast_doubling"
    if _has(r"for\s+\w+\s+in\s+range", c) and _has(r"\w+\s*,\s*\w+\s*=\s*\w+\s*,\s*\w+\s*\+\s*\w+|"
                                                   r"\w+\s*\[\s*\w+\s*\]\s*=\s*\w+\s*\[\s*\w+\s*-\s*1\s*\]", c):
        return "iteration"
    return "undecided"


RULES = {"T04": _t04, "R6": _r6, "T1": _t1, "T03": _t03, "T06": _t06, "R1": _r1, "T14": _t14, "T10": _t10,
         "T08": _t08}


def classify(unit: str, task: str, text: str) -> str:
    if unit in ("B3", "A3", "B6"):
        return OC7.classify(unit, text)
    c = strip_comments(code_part(text))
    c = re.sub(r"[ \t]*([.,()\[\]{}:=+\-*/<>!%])[ \t]*", r"\1", c)   # tokenize() spacing -> source spacing
    return RULES[task](c)


def validate(unit: str, task: str, progs: list[dict[str, Any]], tok: Any) -> dict[str, Any]:
    """progs: [{'gen_ids', 'label'}]; OC run on the decoded prefix at every 4th token and at the end."""
    n_dec = n_agree = 0
    full_ok = 0
    first_dec: list[int] = []
    for p in progs:
        ids = p["gen_ids"]
        lab = p["label"]
        dec_at = None
        for k in list(range(4, len(ids), 4)) + [len(ids)]:
            o = classify(unit, task, tok.decode(ids[:k], skip_special_tokens=True))
            if o != "undecided":
                n_dec += 1
                n_agree += o == lab
                if dec_at is None:
                    dec_at = k
        if dec_at is not None:
            first_dec.append(dec_at)
        full_ok += classify(unit, task, tok.decode(ids, skip_special_tokens=True)) == lab
    n = len(progs)
    agree = n_agree / n_dec if n_dec else 0.0
    return {"unit": unit, "n_programs": n, "decided_prefixes": n_dec, "decided_agreement": agree,
            "full_agreement": full_ok / n if n else 0.0, "coverage_full": full_ok / n if n else 0.0,
            "first_decision_p90": float(sorted(first_dec)[int(0.9 * (len(first_dec) - 1))]) if first_dec else None}
