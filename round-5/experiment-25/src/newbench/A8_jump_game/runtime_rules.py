"""A8 runtime rules: tracer5 features on probe rand300 (values 1-4, reachable)."""


def _f(tr, probe):
    p = tr["probes"].get(probe)
    if not p or p.get("error"):
        return None
    return p["features"]


def label(tr):
    f = _f(tr, "rand300")
    if f is None:
        return "unknown"
    n = 300
    fifo = f["deque"].get("popleft", 0) + f["pop_fifo"] + f["queue"].get("fifo_get", 0)
    if fifo >= n / 4:
        return "bfs_indices"
    lens = {int(k): v for k, v in f.get("list_lens", {}).items()}
    arr = sum(v for L, v in lens.items() if n - 1 <= L <= n + 2)
    if arr >= 1 or f.get("lru", 0) >= 1 or sum(f["selfrec"].values()) >= n / 4:
        return "dp"
    if f["clist_get"] >= n / 2 or f["clist_iter"] >= 1:
        return "greedy"
    return "unknown"
