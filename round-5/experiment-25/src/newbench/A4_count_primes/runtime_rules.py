"""A4 runtime rules: opcode counts (sys.monitoring) on probe n5k (n = 5000) and the largest list on n50k."""


def _f(tr, probe):
    p = tr["probes"].get(probe)
    if not p or p.get("error"):
        return None
    return p["features"]


def label(tr):
    a, b = _f(tr, "n5k"), _f(tr, "n50k")
    if a is None:
        return "unknown"
    n = 5000
    ops = a.get("ops", {})
    mod = ops.get("BINOP%", 0)
    mul = ops.get("BINOP*", 0)
    store = ops.get("STORE_SUBSCR", 0) + ops.get("STORE_SLICE", 0)
    ml = a.get("max_list_len", 0)
    ml50 = b.get("max_list_len", 0) if b else None
    if ml >= 0.8 * n:
        if mul >= 6 * n and mod >= 0.5 * n:
            return "atkin"
        if mod >= 0.4 * n:
            return "linear_sieve"
        if ml50 is not None and ml50 < 0.8 * 50000:
            return "segmented_sieve"
        return "eratosthenes"
    if ml >= 0.4 * n:
        if mul >= 2 * n:
            return "sundaram"
        return "eratosthenes"
    if mod >= 1.5 * n:
        return "trial_division"
    if store >= 0.5 * n:
        return "segmented_sieve"
    return "unknown"
