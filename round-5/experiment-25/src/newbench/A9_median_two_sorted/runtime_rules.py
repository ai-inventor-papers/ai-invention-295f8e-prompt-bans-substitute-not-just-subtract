"""A9 runtime rules: tracer5 features on probe sorted270 (|nums1| = 120, |nums2| = 150)."""


def _f(tr, probe):
    p = tr["probes"].get(probe)
    if not p or p.get("error"):
        return None
    return p["features"]


def label(tr):
    f = _f(tr, "sorted270")
    if f is None:
        return "unknown"
    N = 270
    h = f["heap"]
    if h.get("merge", 0) >= 1 or h.get("heappush", 0) + h.get("heappop", 0) >= N / 4 or f["queue"].get("prio_get", 0):
        return "heap_merge"
    if any(x >= 0.9 * N for x in f["sorted_lens"] + f["sort_lens"]) or f.get("stat", {}).get("median", 0) >= 1:
        return "concat_sort"
    calls = {k: v for k, v in f["calls"].items() if k not in ("solve", "<genexpr>", "<lambda>", "<listcomp>")}
    if calls and sum(calls.values()) >= N / 2 and f["clist_get"] < N / 8:
        return "concat_sort"  # a hand-written sort of the concatenated lists
    reads = f["clist_get"]
    if reads >= N / 4:
        return "merge_two_pointers"
    if 1 <= reads < N / 4:
        return "partition_binary_search"
    return "unknown"
