"""A1 runtime rules: tracer5 features on probe maj301 (n = 301, 151 copies of the answer after 100 other values)."""


def _f(tr, probe):
    p = tr["probes"].get(probe)
    if not p or p.get("error"):
        return None
    return p["features"]


def label(tr):
    f = _f(tr, "maj301")
    if f is None:
        return "unknown"
    n = 301
    t = f.get("tint", {})
    if sum(f.get("stat", {}).values()) >= 1:
        return "library_mode"
    if sum(f.get("rand", {}).values()) >= 1:
        return "randomized_verify"
    if t.get("bit", 0) >= 8 * n:
        return "bit_count"
    if f["maxrec"] >= 4 and sum(f["selfrec"].values()) >= n / 4:
        return "divide_conquer"
    if any(x >= 0.9 * n for x in f["sorted_lens"] + f["sort_lens"]):
        return "sort_middle"
    if t.get("hash", 0) >= 0.5 * n:
        return "hash_count"
    if t.get("eq", 0) >= 3 * n:
        return "other"
    if t.get("eq", 0) >= 0.5 * n:
        return "boyer_moore_vote"
    return "unknown"
