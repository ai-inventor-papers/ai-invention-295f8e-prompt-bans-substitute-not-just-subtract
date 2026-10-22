"""A3 runtime rules: tracer5 features on probe center200 (unique maximum at index 100)."""


def _f(tr, probe):
    p = tr["probes"].get(probe)
    if not p or p.get("error"):
        return None
    return p["features"]


def label(tr):
    f = _f(tr, "center200")
    if f is None:
        return "unknown"
    n = 200
    t = f.get("tint", {})
    if t.get("cmp", 0) >= n * n / 4:
        return "other"
    pops = f["pop_lifo"] + f["deque"].get("pop", 0)
    if pops >= n / 8:
        return "monotonic_stack"
    lens = {int(k): v for k, v in f.get("list_lens", {}).items()}
    big = sum(v for L, v in lens.items() if n - 1 <= L <= n + 2)
    if big >= 1:
        return "prefix_suffix_max"
    idx = f["clist_idx"]
    jumps = [(min(a, b), max(a, b)) for a, b in zip(idx, idx[1:]) if abs(a - b) > n / 2]
    if len(jumps) >= n / 8 and len({lo for lo, _ in jumps}) >= 3 and len({hi for _, hi in jumps}) >= 3:
        return "two_pointers"
    if idx or f["clist_iter"] >= 1:
        return "peak_split"
    return "unknown"
