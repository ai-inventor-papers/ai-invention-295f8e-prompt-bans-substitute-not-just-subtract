"""A2 runtime rules: tracer5 features on probe rand200 (tainted ints)."""


def _f(tr, probe):
    p = tr["probes"].get(probe)
    if not p or p.get("error"):
        return None
    return p["features"]


def label(tr):
    f = _f(tr, "rand200")
    if f is None:
        return "unknown"
    n = 200
    t = f.get("tint", {})
    calls = {k: v for k, v in f["calls"].items() if k not in ("solve", "<genexpr>", "<lambda>", "<listcomp>")}
    if f.get("max_list_len", 0) >= 1.8 * n or (f["user_classes"] >= 1 and calls and max(calls.values()) >= n / 2):
        return "segment_tree"
    if f["maxrec"] >= 4 and sum(f["selfrec"].values()) >= n / 4:
        return "divide_conquer"
    if t.get("add", 0) >= n * n / 8:
        return "other"
    if t.get("sub", 0) >= 0.5 * n:
        return "prefix_min"
    if t.get("add", 0) >= 0.5 * n:
        return "kadane"
    return "unknown"
