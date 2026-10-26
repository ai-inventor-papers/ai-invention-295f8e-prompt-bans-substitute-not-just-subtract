"""A5 runtime rules: tracer5 features on probe lcp40 (40 tagged strings sharing a 12-letter prefix)."""


def _f(tr, probe):
    p = tr["probes"].get(probe)
    if not p or p.get("error"):
        return None
    return p["features"]


def _runs(reads):
    runs, cur, L = [], None, 0
    for sid, i in reads:
        if cur is None or i != cur:
            if cur is not None:
                runs.append(L)
            cur, L = i, 1
        else:
            L += 1
    if cur is not None:
        runs.append(L)
    return runs


def _increases(seq):
    comp = [v for i, v in enumerate(seq) if i == 0 or v != seq[i - 1]]
    return sum(1 for a, b in zip(comp, comp[1:]) if b > a), len(set(comp))


def label(tr):
    f = _f(tr, "lcp40")
    if f is None:
        return "unknown"
    m = 40
    cc = f.get("c_calls", {})
    if sum(f.get("ospath", {}).values()) >= 1:
        return "library_commonprefix"
    calls = {k: v for k, v in f["calls"].items() if k not in ("solve", "<genexpr>", "<lambda>", "<listcomp>")}
    if (f["user_classes"] >= 1 and calls and max(calls.values()) >= 100) or cc.get("setdefault", 0) >= 100 or \
            f.get("ops", {}).get("BUILD_MAP", 0) >= 100:
        return "trie"
    if any(x >= 0.9 * m for x in f["sorted_lens"] + f["sort_lens"]) or (cc.get("min", 0) >= 1 and cc.get("max", 0) >= 1):
        return "sort_ends"
    if sum(f["selfrec"].values()) >= 5:
        return "divide_conquer"
    lens = list(f.get("cstr_sw", [])) + [s[2] for s in f.get("cstr_slices", []) if s[2] is not None and s[2] >= 0]
    inc, nd = _increases(f.get("cstr_sw", []))
    inc2, nd2 = _increases([s[2] for s in f.get("cstr_slices", []) if s[2] is not None and s[2] >= 0])
    if (inc >= 1 and nd >= 3) or (inc2 >= 1 and nd2 >= 3):
        return "binary_search_length"
    runs = _runs(f.get("cstr_reads", []))
    med = sorted(runs)[len(runs) // 2] if runs else 0
    if med >= 3 or (f["cstr"].get("iter", 0) >= 0.9 * m and not runs and f["cstr"].get("startswith", 0) == 0):
        return "vertical_scan"
    if f["cstr"].get("startswith", 0) >= m - 1 or runs or lens:
        return "horizontal_scan"
    return "unknown"
