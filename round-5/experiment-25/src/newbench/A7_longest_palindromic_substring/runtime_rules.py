"""A7 runtime rules: probes rand150 (150 random a/b/c letters with a planted 21-letter mirror run; opcode counts) and
uni80 ('a' * 80: expansion around centres is quadratic, Manacher stays linear)."""


def _f(tr, probe):
    p = tr["probes"].get(probe)
    if not p or p.get("error"):
        return None
    return p["features"]


def label(tr):
    f, fu = _f(tr, "rand150"), _f(tr, "uni80")
    if f is None:
        return "unknown"
    n, nu = 150, 80
    gets = f["cstr"].get("get", 0)
    slices = f["cstr"].get("slice", 0)
    if slices >= n * n / 4:
        return "brute_force"
    if gets >= n * n / 2:
        return "dp_table"
    ugets = fu["cstr"].get("get", 0) if fu else 0
    uslices = fu["cstr"].get("slice", 0) if fu else 0
    if f.get("c_calls", {}).get("join", 0) >= 1 or f.get("max_list_len", 0) >= 1.9 * n:
        return "manacher"
    if fu is not None and ugets + uslices < nu * nu / 4 and gets >= n:
        return "manacher"
    if gets >= 2 * n and fu is not None and ugets >= nu * nu / 4:
        return "expand_center"
    return "unknown"
