def solve(strs):
    groups = {}
    for w in strs:
        groups.setdefault(len(w), []).append(w)
    return list(groups.values())
