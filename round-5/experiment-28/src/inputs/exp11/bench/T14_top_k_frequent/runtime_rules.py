"""Frozen runtime rules for T14_top_k_frequent (snapshot of bench/common/rtrules.py; shared helpers included)."""

"""Runtime-signature rules: tracer feature lines per probe -> mode | 'other' | 'unknown'.

Each rule reads the probe features produced by tracer.py on the probes of probes.py (sizes noted inline).
"""

from __future__ import annotations

import math


def _f(tr, probe):
    p = tr["probes"].get(probe)
    if not p or p.get("error"):
        return None
    return p["features"]


def _get(f, key, sub=None, default=0):
    v = f.get(key, default)
    if sub is not None:
        return (v or {}).get(sub, 0)
    return v


def _maxcalls(f, exclude=("solve", "<genexpr>", "<lambda>", "<listcomp>")):
    c = {k: v for k, v in f["calls"].items() if k not in exclude}
    return max(c.values()) if c else 0


def _frontier(f):
    fifo = _get(f, "deque", "popleft") + f["pop_fifo"] + _get(f, "queue", "fifo_get")
    lifo = _get(f, "deque", "pop") + f["pop_lifo"] + _get(f, "queue", "lifo_get")
    return fifo, lifo


def _lens(f):
    return {int(k): v for k, v in f.get("list_lens", {}).items()}


def t03(tr):
    f = _f(tr, "rand300")
    if f is None:
        return "unknown"
    n, k = 300, 100
    h = f["heap"]
    if f["nsel_args"] or (h.get("heappush", 0) >= k and f["heap_max_size"] <= k + 2) or h.get("heappushpop") \
            or h.get("heapreplace"):
        return "size_k_heap"
    if (f["heapify_sizes"] and max(f["heapify_sizes"]) >= n * 0.9) or (f["heap_max_size"] >= n * 0.9 and h.get("heappop", 0) >= 1):
        return "heapify_pop"
    small_sorts = sum(1 for x in f["sorted_lens"] + f["sort_lens"] if x <= 5)
    if small_sorts >= 20 and f["maxrec"] >= 2:
        return "median_of_medians"
    lens = _lens(f)
    if any(L >= 1500 for L in lens):
        return "counting_sort"
    w = _f(tr, "wide100")
    if w is not None and any(L >= 15000 for L in _lens(w)):
        return "counting_sort"
    big = [x for x in f["sorted_lens"] + f["sort_lens"] if x >= n * 0.98]
    if big:
        return "full_sort"
    mid = [x for x in f["sorted_lens"] + f["sort_lens"] if 0.5 * n <= x < n * 0.98]
    if mid and _get(f, "cint", "hash") >= n * 0.5:
        return "other"  # count + sort of the distinct values
    if small_sorts >= 20:
        return "median_of_medians"
    if _get(f, "cint", "hash") >= n * 0.5:
        return "counting_sort"  # dict counts walked over the value range (no sort of the values)
    if _get(f, "cint", "cmp") >= n and not big:
        return "quickselect"
    return "unknown"


def t04(tr):
    f = _f(tr, "find300")
    if f is None:
        return "unknown"
    n, m = 300, 10
    cs = f["cstr"]
    reads = cs.get("get", 0) + cs.get("iter", 0) + cs.get("slice", 0)
    if (cs.get("find", 0) + cs.get("index", 0) + cs.get("contains", 0) + cs.get("count", 0) + cs.get("split", 0)) >= 1 \
            and reads < 30:
        return "builtin"
    lens = _lens(f)
    if cs.get("concat", 0) >= 1 and any(L in lens for L in (n + m + 1, n + m, n + m + 2)):
        return "z_algorithm"
    cc = f["c_calls"]
    if cc.get("ord", 0) >= n * 0.5 or cc.get("hash", 0) >= n * 0.5 or (cc.get("pow", 0) >= 1 and cc.get("ord", 0) >= m):
        return "rabin_karp"
    if any(L in lens for L in (256, 128, 26, 27)) or (f.get("dict_sizes") and cc.get("get", 0) >= 5):
        return "bmh"
    if m in lens or (m + 1) in lens:
        return "kmp"
    if cs.get("slice", 0) >= n * 0.5 or cs.get("startswith", 0) >= n * 0.5 or cs.get("get", 0) >= n:
        return "naive"
    if cs.get("find", 0) + cs.get("index", 0) + cs.get("contains", 0) >= 1:
        return "builtin"
    return "unknown"


def t05(tr):
    f = _f(tr, "end200")
    if f is None:
        return "unknown"
    n = 200
    ci = f["cint"]
    if ci.get("add", 0) >= n * n / 4:
        return "brute_force"
    sorted_big = any(x >= n * 0.9 for x in f["sorted_lens"] + f["sort_lens"])
    if sorted_big:
        if sum(f["bisect"].values()) >= 1 or ci.get("sub", 0) >= n * 0.3:
            return "sort_binary_search"
        return "sort_two_pointers"
    if ci.get("hash", 0) >= n * 0.3:
        return "hash_map"
    if ci.get("add", 0) >= n * 2:
        return "brute_force"
    return "unknown"


def t06(tr):
    f = _f(tr, "perm200")
    if f is None:
        return "unknown"
    n = 200
    if f["clist_set"] >= 5:
        return "index_marking"
    if f["clist_iter"] >= 4 or f["c_calls"].get("sum", 0) >= 4:
        if f["clist_iter"] >= 4:
            return "value_binary_search"
    if any(x >= n * 0.9 for x in f["sorted_lens"] + f["sort_lens"]):
        return "sort_adjacent"
    idx = f["clist_idx"]
    seq = sum(1 for a, b in zip(idx, idx[1:]) if abs(a - b) <= 1) / max(len(idx) - 1, 1)
    if f["clist_iter"] == 0 and f["clist_get"] >= 20 and _get(f, "cint", "hash") < 5 and f["clist_slice"] == 0 and seq < 0.5:
        return "floyd"
    if f["clist_iter"] == 0 and f["clist_get"] >= 20 and seq >= 0.5:
        return "sort_adjacent"  # neighbour comparison (attempted without the sort)
    if _get(f, "cint", "hash") >= 10:
        return "hash_set"
    lens = _lens(f)
    if any(L in lens for L in (n + 1, n + 2)) and f["clist_iter"] >= 1:
        return "hash_set"
    if f["c_calls"].get("sum", 0) >= 1 or f["c_calls"].get("len", 0) >= 1 and f["clist_iter"] <= 2:
        return "other"
    return "unknown"


def t08(tr):
    fs = [_f(tr, p) for p in ("n64", "n128", "n256")]
    if any(x is None for x in fs):
        return "other" if any(p.get("error") == "timeout" for p in tr["probes"].values()) or tr.get("error") else "unknown"
    l1, l2 = max(fs[1]["lines"], 1), max(fs[2]["lines"], 1)
    expo = math.log2(l2 / l1)
    f = fs[2]
    if expo > 1.6:
        return "other"
    if expo >= 0.6:
        if f["lru"] or f["maxrec"] >= 100 or sum(f["selfrec"].values()) >= 100:
            return "memo_recursion"
        return "iteration"
    lens = _lens(f)
    if lens.get(2, 0) >= 5 or lens.get(4, 0) >= 3:
        return "matrix_power"
    return "fast_doubling"


def t10(tr):
    f = _f(tr, "rand80")
    if f is None:
        return "unknown"
    n, E = 80, 120
    fifo, lifo = _frontier(f)
    fp = _f(tr, "path40")
    deep = fp is not None and fp["maxrec"] >= 20
    if _maxcalls(f) >= 1.5 * E and fifo < n / 2 and lifo < n / 2 and not deep:
        return "union_find"
    if fifo >= n / 2:
        return "bfs"
    if lifo >= n / 2 or sum(f["selfrec"].values()) >= n / 2:
        return "dfs"
    if (f["clist_iter"] >= 2 or f["c_calls"].get("min", 0) >= E) and fifo == 0 and lifo == 0:
        return "label_propagation"
    return "unknown"


def t11(tr):
    f = _f(tr, "rand150")
    if f is None:
        return "unknown"
    n = 150
    if sum(f["bisect"].values()) >= n * 0.5:
        return "patience_bisect"
    if _get(f, "cint", "cmp") >= n * n / 5:
        return "quadratic_dp"
    lens = _lens(f)
    if any(x >= 0.8 * n for x in f["sorted_lens"]) and any(L >= 0.8 * n for L in lens):
        return "fenwick"
    if _get(f, "cint", "cmp") >= n * 2:
        return "patience_bisect"
    return "unknown"


def t13(tr):
    f = _f(tr, "rand80")
    if f is None:
        return "unknown"
    n = 80
    if f["user_classes"] >= 1 and _maxcalls(f) >= n * 0.5:
        return "interval_tree"
    if _maxcalls(f) >= n and _get(f, "cint", "cmp") >= n * n / 4:
        return "union_find"
    if any(x >= n * 0.9 for x in f["sorted_lens"] + f["sort_lens"]):
        return "sort_sweep"
    if _get(f, "cint", "cmp") >= n * n / 4:
        return "union_find"
    return "unknown"


def t14(tr):
    f = _f(tr, "zipf25")
    if f is None:
        return "unknown"
    n, d, k = 325, 25, 4
    if f["most_common"].get("none"):
        return "sort_by_count"
    if f["most_common"].get("n") or f["heap"].get("nlargest") or f["heap"].get("heappush", 0) >= k or f["heap"].get("heapify"):
        return "heap"
    lens = _lens(f)
    if any(L in lens for L in (n + 1, n, n + 2)):
        return "bucket_sort"
    if any(x >= d * 0.9 for x in f["sorted_lens"] + f["sort_lens"]):
        return "sort_by_count"
    if _get(f, "cint", "hash") >= n * 0.5:
        return "quickselect_counts"
    return "unknown"


def r1(tr):
    f = _f(tr, "rand80")
    if f is None:
        return "unknown"
    n = 80
    if f["maxrec"] >= n / 2 or (f["lru"] and sum(f["selfrec"].values()) >= 10):
        return "memo_recursion"
    lens = _lens(f)
    if sum(f["bisect"].values()) >= n * 0.5:
        return "dp_bisect"
    if _get(f, "cint", "cmp") >= n * n / 4 or _get(f, "cint", "eq") >= n * n / 4:
        return "dag_longest_path"
    if (n + 1) in lens and _get(f, "cint", "cmp") >= 3 * n:
        return "dp_bisect"
    if any(x >= n * 0.9 for x in f["sorted_lens"] + f["sort_lens"]):
        return "greedy_end"
    return "unknown"


def r2(tr):
    fc, ff = _f(tr, "cyc_early60"), _f(tr, "forest60")
    if fc is None or ff is None:
        return "unknown"
    n, E = 60, len([1 for v in range(1, 60) if v % 15])
    fifo_f, lifo_f = _frontier(ff)
    fifo_c, lifo_c = _frontier(fc)
    rec_c = sum(fc["selfrec"].values())
    uf_like = _maxcalls(ff) >= 1.5 * E and fifo_f < n / 2 and lifo_f < n / 2 and sum(ff["selfrec"].values()) < n / 2
    if uf_like:
        return "edge_count" if _maxcalls(fc) >= 1.5 * (n - 1) else "union_find"
    visited_c = max(fifo_c, lifo_c, rec_c, fc["calls"].get("dfs", 0))
    if visited_c >= 0.8 * n and (fc["clist_iter"] >= 2 or fc["c_calls"].get("len", 0) >= 1):
        return "edge_count"
    if fifo_f >= n / 2:
        return "bfs_parent"
    if lifo_f >= n / 2 or sum(ff["selfrec"].values()) >= n / 2:
        return "dfs_parent"
    if ff["clist_iter"] >= 1 and fc["c_calls"].get("len", 0) >= 1:
        return "edge_count"
    return "unknown"


def r3(tr):
    fd, fc = _f(tr, "dag40"), _f(tr, "cyc30")
    if fd is None or fc is None:
        return "unknown"
    n = 40
    fifo_d, lifo_d = _frontier(fd)
    if fc["clist_iter"] >= 10:
        return "layering"
    rec_c = sum(fc["selfrec"].values())
    fifo_c, lifo_c = _frontier(fc)
    if rec_c >= 20 or (lifo_c >= 20 and fifo_d < n / 2):
        return "dfs_postorder"
    if sum(fd["selfrec"].values()) >= 5:
        return "dfs_postorder"
    if fifo_d >= n * 0.75 or lifo_d >= n * 0.75 or fd["heap"].get("heappop", 0) >= n * 0.75:
        return "kahn"
    cc = fd["c_calls"]
    if cc.get("next", 0) >= n / 2 or cc.get("remove", 0) + cc.get("discard", 0) >= n / 2 or \
            fd["calls"].get("<genexpr>", 0) >= n:
        return "source_removal"
    if fd["sorted_key"] and any(x >= n * 0.9 for x in fd["sorted_lens"]):
        return "layering"
    return "unknown"


def r6(tr):
    f = _f(tr, "run2000")
    if f is None:
        return "unknown"
    n = 2000
    if sum(f["bisect"].values()) >= 1:
        return "bisect_module"
    reads = f["clist_get"] + f["clist_iter"] * n
    if reads >= n * 0.5:
        return "linear_scan"
    idx = f["clist_idx"]
    dbl = 0
    best = 0
    for a, b in zip(idx, idx[1:]):
        if a > 0 and b in (2 * a, 2 * a + 1, 2 * a - 1):
            dbl += 1
            best = max(best, dbl)
        else:
            dbl = 0
    if best >= 3:
        return "exponential_search"
    run = 0
    best_run = 0
    for a, b in zip(idx, idx[1:]):
        if abs(b - a) == 1:
            run += 1
            best_run = max(best_run, run)
        else:
            run = 0
    if best_run >= 10:
        return "binary_expand"
    if f["clist_get"] >= 5:
        return "binary_search"
    return "unknown"


RULES = {"T03": t03, "T04": t04, "T05": t05, "T06": t06, "T08": t08, "T10": t10, "T11": t11, "T13": t13, "T14": t14,
         "R1": r1, "R2": r2, "R3": r3, "R6": r6}


def runtime_label(task: str, trace: dict) -> str:
    if trace.get("error") and not trace["probes"]:
        return "unknown"
    try:
        return RULES[task](trace)
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return "unknown"
