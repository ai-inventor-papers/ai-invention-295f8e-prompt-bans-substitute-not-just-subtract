def solve(strs):
    groups = {}
    for w in strs:
        groups.setdefault("".join(sorted(set(w))), []).append(w)
    return list(groups.values())
