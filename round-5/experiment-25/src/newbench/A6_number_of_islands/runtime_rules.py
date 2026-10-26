"""A6 runtime rules (bench T10 logic): probes rand20 (20 x 20, 215 land cells) and block12 (12 x 12 all land)."""

LAND = 215


def _f(tr, probe):
    p = tr["probes"].get(probe)
    if not p or p.get("error"):
        return None
    return p["features"]


def _get(f, key, sub):
    return (f.get(key) or {}).get(sub, 0)


def label(tr):
    f, fb = _f(tr, "rand20"), _f(tr, "block12")
    if f is None:
        return "unknown"
    fifo = _get(f, "deque", "popleft") + f["pop_fifo"] + _get(f, "queue", "fifo_get")
    lifo = _get(f, "deque", "pop") + f["pop_lifo"] + _get(f, "queue", "lifo_get")
    calls = {k: v for k, v in f["calls"].items() if k not in ("solve", "<genexpr>", "<lambda>", "<listcomp>",
                                                             "<setcomp>", "<dictcomp>")}
    maxcalls = max(calls.values()) if calls else 0
    deep = fb is not None and fb["maxrec"] >= 60
    rec = sum(f["selfrec"].values())
    if maxcalls >= 1.5 * LAND and fifo < LAND / 2 and lifo < LAND / 2 and not deep:
        return "union_find"
    if fifo >= LAND / 2:
        return "bfs_flood"
    if lifo >= LAND / 2 or deep or rec >= LAND / 2:
        return "dfs_flood"
    return "unknown"
